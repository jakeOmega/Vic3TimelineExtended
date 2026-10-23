"""Tourism heritage (docs/superpowers/specs/2026-10-23-tourism-heritage-design.md).

Monuments give tourism as an output bonus, as base appeal does (§ 5), and the
heritage a monument stands for comes off base appeal through a gated term (§ 6).

    python3 test_tourism_heritage.py
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOURISM = ROOT / "common" / "script_values" / "tourism.txt"
PANEL_WIDGETS = ROOT / "gui" / "te_state_panel_widgets.gui"


def read(path):
    return Path(path).read_text(encoding="utf-8-sig")


def squash(text):
    """Comments dropped, every whitespace run one space."""
    return re.sub(r"\s+", " ", re.sub(r"#[^\n]*", "", text)).strip()


def block(text, name):
    """The body of the block `name = {` or `name = <type> {` (a .gui `type X = flowcontainer {`), braces
    balanced, or None."""
    m = re.search(rf"(?m)^[ \t]*{re.escape(name)} = (?:\w+ )?\{{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        if c == "#":
            i = text.index("\n", i)
            continue
        depth += {"{": 1, "}": -1}.get(c, 0)
        i += 1
    return text[m.end():i - 1]


# Spec § 5.2: each wonder's output figure is the appeal its state's heritage took.
WONDERS = {"building_taj_mahal": 0.40, "building_angkor_wat": 0.30, "building_hagia_sophia": 0.20,
           "building_vatican_city": 0.20, "building_forbidden_city": 0.20,
           "building_saint_basils_cathedral": 0.20, "building_white_house": 0.20,
           "building_mosque_of_djenne": 0.20}


class MonumentsAreOutput(unittest.TestCase):
    def test_each_wonder_has_its_figure(self):
        body = squash(block(read(TOURISM), "tourism_bonus_from_monuments"))
        for b, v in WONDERS.items():
            self.assertRegex(body, rf"is_building_type = {b} \}} add = {v:g} \}}", b)

    def test_other_monuments_get_the_default(self):
        body = squash(block(read(TOURISM), "tourism_bonus_from_monuments"))
        self.assertIn("every_scope_building = { limit = { is_building_group = bg_monuments }", body)
        self.assertRegex(body, r"else = \{ add = 0\.1 \}")

    def test_totals(self):
        t = read(TOURISM)
        self.assertIn("add = tourism_bonus_from_monuments", block(t, "total_tourism_output_bonus_percent"))
        thr = block(t, "total_tourism_throughput_bonus_percent")
        self.assertIn("add = tourism_throughput_from_skyscraper", thr)
        self.assertNotIn("monuments", thr)

    def test_old_value_is_gone(self):
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "gui").rglob("*.gui")):
            self.assertFalse("tourism_throughput_from_monuments" in path.read_text(encoding="utf-8-sig"), path)

    def test_card_shows_monuments_with_output(self):
        card = block(read(PANEL_WIDGETS), "type te_state_tourism_card")
        out_col, thr_col = card.split("te_state_tourism_throughput_tt", 1)
        self.assertTrue("tourism_bonus_from_monuments" in out_col, "Monuments not in the output column")
        self.assertTrue("tourism_throughput_from_skyscraper" in thr_col, "no Skyscraper row in throughput")


if __name__ == "__main__":
    unittest.main()
