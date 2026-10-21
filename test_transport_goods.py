"""Transport goods (#1050): transportation is all movement inside a state,
merchant marine movement between markets.

The classification lives in scripts/generators/convert_transport_goods.py;
these tests read the same tables, so the construction fallback
(CONSTRUCTION_GOOD = "merchant_marine" plus a rerun) keeps them passing.
Design: docs/superpowers/specs/2026-10-21-transport-goods-design.md.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
import convert_transport_goods as ctg  # noqa: E402


def _pm(name, body):
    return f"{name} = {{\n\tbuilding_modifiers = {{\n\t\tworkforce_scaled = {{\n{body}\t\t}}\n\t}}\n}}\n"


INFRASTRUCTURE_PMS = ctg.RAILWAY_BASE_PMS | {
    "pm_bullet_trains", "pm_maglev_trains",
    "pm_basic_port", "pm_industrial_port", "pm_modern_port",
    "pm_container_ports", "pm_global_ports", "pm_magnetic_drive_ports",
}


def _sub(text, key):
    """The body of the first `key = { ... }` block in `text`, or "" if none."""
    m = re.search(r"\b" + key + r"\s*=\s*\{", text)
    if not m:
        return ""
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def _blocks(rel):
    text = (ROOT / rel).read_text(encoding="utf-8-sig")
    lines = text.split("\n")
    return {name: "\n".join(lines[lo:hi]) for name, (lo, hi) in ctg.pm_blocks(text).items()}


class TestConvert(unittest.TestCase):
    def test_bom_and_first_pm(self):
        text = "﻿﻿" + _pm("pm_a", "\t\t\tgoods_input_merchant_marine_add = 3   # Price: 50\n")
        out = ctg.convert(text)
        self.assertTrue(out.startswith("﻿"))
        self.assertFalse(out.startswith("﻿﻿"))
        self.assertIn("\t\t\tgoods_input_transportation_add = 5\n", out)
        self.assertNotIn("merchant_marine", out)

    def test_merges_into_existing_input(self):
        out = ctg.convert(_pm("pm_department_stores", "\t\t\tgoods_input_merchant_marine_add = 0.5\n"
                                                      "\t\t\tgoods_input_transportation_add = 3\n"))
        self.assertEqual(re.findall(r"goods_input_\w+_add = [0-9.]+", out), ["goods_input_transportation_add = 4"])

    def test_trade_keeps_merchant_marine(self):
        text = _pm("pm_trade_center_trade_quantity_advanced_1", "\t\t\tgoods_input_merchant_marine_add = 8\n")
        self.assertEqual(ctg.convert(text), text)

    def test_only_listed_producers_convert(self):
        rail = ctg.convert(_pm("pm_autonomous_trains", "\t\t\tgoods_output_merchant_marine_add = 80\n"))
        self.assertIn("goods_output_transportation_add = 133.5", rail)
        port = _pm("pm_global_ports", "\t\t\tgoods_output_merchant_marine_add = 95\n")
        self.assertEqual(ctg.convert(port), port)

    def test_construction_round_trip(self):
        for qty in ("0.5", "3", "10", "20", "25"):
            with self.subTest(qty=qty):
                text = _pm("pm_steel_frame_buildings", f"\t\t\tgoods_input_merchant_marine_add = {qty}\n")
                there = ctg.convert(text, "transportation")
                self.assertIn("goods_input_transportation_add", there)
                back = ctg.convert(there, "merchant_marine")
                self.assertEqual(float(re.search(r"merchant_marine_add = ([0-9.]+)", back).group(1)), float(qty))


class TestLiveFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blocks = {}
        for rel in ctg.FILES:
            cls.blocks.update(_blocks(rel))

    def test_single_bom(self):
        for rel in ctg.FILES:
            with self.subTest(file=rel):
                raw = (ROOT / rel).read_bytes()
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"))

    def test_no_stray_merchant_marine_consumers(self):
        allowed = set(ctg.KEEP_MM_INPUT)
        if ctg.CONSTRUCTION_GOOD == "merchant_marine":
            allowed |= ctg.CONSTRUCTION_PMS
        stray = sorted(n for n, b in self.blocks.items() if "goods_input_merchant_marine_add" in b and n not in allowed)
        self.assertEqual(stray, [])

    def test_no_merchant_marine_input_in_other_pm_files(self):
        # The converter and the test above only see FILES, and only blocks
        # pm_blocks parses; a raw scan catches a consumer anywhere else.
        for path in sorted((ROOT / "common" / "production_methods").glob("*.txt")):
            if path.relative_to(ROOT).as_posix() in ctg.FILES:
                continue
            with self.subTest(file=path.name):
                text = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))
                self.assertNotIn("goods_input_merchant_marine_add", text)

    def test_raw_count_matches_parsed_blocks(self):
        # Every merchant marine input line in FILES sits in a block pm_blocks
        # found, so none escaped the conversion unparsed.
        for rel in ctg.FILES:
            with self.subTest(file=rel):
                text = re.sub(r"#[^\n]*", "", (ROOT / rel).read_text(encoding="utf-8-sig"))
                raw = len(re.findall(r"\bgoods_input_merchant_marine_add\b", text))
                parsed = sum(re.sub(r"#[^\n]*", "", b).count("goods_input_merchant_marine_add") for b in _blocks(rel).values())
                self.assertEqual(raw, parsed)

    def test_construction_buys_the_configured_good(self):
        for name in sorted(ctg.CONSTRUCTION_PMS):
            with self.subTest(pm=name):
                self.assertIn(f"goods_input_{ctg.CONSTRUCTION_GOOD}_add", self.blocks[name])

    def test_infrastructure_per_level(self):
        # An unstaffed or loss-making railway or port still supplies its
        # network, so no AI subsidy is needed to keep infrastructure up.
        for name in sorted(INFRASTRUCTURE_PMS):
            with self.subTest(pm=name):
                state = _sub(self.blocks[name], "state_modifiers")
                self.assertNotIn("state_infrastructure_add", _sub(state, "workforce_scaled"))
                self.assertIn("state_infrastructure_add", _sub(state, "level_scaled"))

    def test_converted_producers(self):
        for name in sorted(ctg.MM_OUTPUT_TO_TRANSPORTATION):
            with self.subTest(pm=name):
                self.assertNotIn("goods_output_merchant_marine_add", self.blocks[name])
                self.assertIn("goods_output_transportation_add", self.blocks[name])


if __name__ == "__main__":
    unittest.main()
