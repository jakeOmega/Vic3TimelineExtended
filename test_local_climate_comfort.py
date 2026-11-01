"""Local Climate: comfort (docs/superpowers/specs/2026-11-01-local-climate-design.md § 5, § 6).

The four relief types and the technologies that carry them, the comfort formula and its
calibration, and the modifier that applies the penalty.

    python3 test_local_climate_comfort.py
"""
import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TECH = ROOT / "common" / "technology" / "technologies"
TYPES = ROOT / "common" / "modifier_type_definitions" / "local_climate_modifier_types.txt"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cal = load("local_climate_calibration", "scripts/analysis/local_climate_calibration.py")

KINDS = ("heat", "cold", "water", "disease")
# Spec § 5.2 as the owner left it on 2026-11-01: the historical eras' stage by era 7, the modern by
# era 10, everything by era 13; malaria gone by era 4.
STAGES = {"cold": {7: 0.6, 10: 0.8, 13: 1.0}, "heat": {7: 0.8, 10: 0.9, 13: 1.0},
          "water": {7: 0.7, 10: 0.85, 13: 1.0}, "disease": {4: 1.0, 13: 1.0}}


def loc_value(key):
    for path in (ROOT / "localization" / "english").glob("*.yml"):
        m = re.search(rf'(?m)^ {re.escape(key)}:\d* "(.*)"\s*$', path.read_text(encoding="utf-8-sig"))
        if m:
            return m.group(1)
    return None


def top_block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
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


class Relief(unittest.TestCase):
    def test_relief_types_registered(self):
        text = TYPES.read_text(encoding="utf-8-sig")
        for kind in KINDS:
            name = f"state_climate_{kind}_relief_add"
            body = top_block(text, name)
            self.assertIsNotNone(body, name)
            for field in ("percent = yes", "script_only = yes", "color = good"):
                self.assertIn(field, body, (name, field))
            self.assertIsNotNone(loc_value(name), name)
            self.assertIn("[concept_local_climate]", loc_value(f"{name}_desc") or "", name)

    def test_relief_schedule(self):
        schedule = cal.relief_schedule()
        for kind, stages in STAGES.items():
            for era, target in stages.items():
                got = cal.relief_at(schedule, kind, era)
                if target == 1.0:
                    self.assertAlmostEqual(got, 1.0, places=6, msg=(kind, era))
                else:
                    self.assertAlmostEqual(got, target, delta=0.05, msg=(kind, era))

    def test_relief_at_1836_is_zero(self):
        schedule = cal.relief_schedule()
        for kind in KINDS:
            self.assertEqual(cal.relief_at(schedule, kind, 1), 0.0, kind)

    def test_one_inject_per_carrier(self):
        """A carrier keeps one INJECT: a second INJECT of `modifier` on one technology is unread in game.
        (Some technologies outside Local Climate already carry two; this guards the carriers only.)"""
        carriers = {key for kind in KINDS for _, key, _ in cal.relief_schedule()[kind]}
        seen = {}
        for path in sorted(TECH.glob("*.txt")):
            for key in re.findall(r"(?m)^INJECT:(\w+) = \{", path.read_text(encoding="utf-8-sig")):
                if key in carriers:
                    self.assertNotIn(key, seen, f"{key}: INJECTed in {seen.get(key)} and {path.name}")
                    seen[key] = path.name

    def test_carrier_comments(self):
        """Each carrier line says why the technology eases that discomfort."""
        for path in sorted(TECH.glob("*.txt")):
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                if re.search(r"state_climate_\w+_relief_add\s*=", line):
                    self.assertIn("#", line, f"{path.name}: {line.strip()}")


if __name__ == "__main__":
    unittest.main()
