"""Health and consumer-protection institutions shrink opium plantations
(drugs phase 2 § 3).

Values are the owner's (docs/testing/drugs-wealth-probe-results-2026-10-02.md,
"Decisions"), per investment level on building_opium_plantation_throughput_add,
the plantation-only lever: goods_output_opium_mult applies per good and would
cut Pharmaceutical Industries too. The health laws' INJECTs sum with vanilla's
institution_modifier; the Ministry of Consumer Protection is the mod's own.

Run: python3 -m unittest test_opium_plantation_penalties -v
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEALTH_LAWS = ROOT / "common/laws/modified_health_system.txt"
INSTITUTIONS = ROOT / "common/institutions/extra_institutions.txt"
MODIFIER = "building_opium_plantation_throughput_add"

EXPECTED_LAWS = {
    "INJECT:law_charitable_health_system": -0.02,
    "INJECT:law_private_health_insurance": -0.03,
    "INJECT:law_public_health_insurance": -0.05,
}
EXPECTED_MINISTRY = -0.1


def _block(text, opener):
    m = re.search(rf"^[ \t]*{re.escape(opener)}\s*=\s*\{{", text, re.M)
    if not m:
        return None
    depth, pos = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[pos], 0)
        pos += 1
    return text[m.end():pos]


def _values(block, key):
    return [float(v) for v in re.findall(rf"^\s*{key}\s*=\s*(-?[0-9.]+)", block, re.M)]


class HealthLaws(unittest.TestCase):
    def test_each_health_law_cuts_plantations(self):
        text = HEALTH_LAWS.read_text(encoding="utf-8-sig")
        for opener, value in EXPECTED_LAWS.items():
            law = _block(text, opener)
            self.assertIsNotNone(law, opener)
            inst = _block(law, "institution_modifier")
            self.assertIsNotNone(inst, f"{opener}: no institution_modifier")
            self.assertEqual(_values(inst, MODIFIER), [value], opener)


    def test_no_replace_drops_the_injects(self):
        # A REPLACE: of these laws anywhere would silently discard the INJECTs.
        laws = [opener.split(":", 1)[1] for opener in EXPECTED_LAWS]
        for path in sorted((ROOT / "common/laws").glob("*.txt")):
            text = path.read_text(encoding="utf-8-sig")
            for law in laws:
                self.assertNotRegex(text, rf"(?m)^\s*REPLACE(_OR_CREATE)?:{law}\b", path.name)


class MinistryOfConsumerProtection(unittest.TestCase):
    def test_ministry_cuts_plantations(self):
        text = INSTITUTIONS.read_text(encoding="utf-8-sig")
        inst = _block(text, "institution_ministry_of_consumer_protection")
        self.assertIsNotNone(inst)
        modifier = _block(inst, "modifier")
        self.assertIsNotNone(modifier)
        self.assertEqual(_values(modifier, MODIFIER), [EXPECTED_MINISTRY])


if __name__ == "__main__":
    unittest.main()
