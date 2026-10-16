"""Guards the sign of `state_pollution_reduction_health_mult` where the mod means to protect.

The modifier is declared `color = bad` with `percent = yes`: a positive value
adds to pollution's harm to health and a negative one cuts it. Vanilla's good
sources carry it negative (the health laws -0.1 / -0.15, a technology -0.1), and
its one positive source is a steel company's prosperity modifier. The mod's
Environmental Sustainability principles and the Green Movement boon shipped it
positive, which made them worsen pollution's health effects (tooltip: red).

The three health-law INJECTs in `common/laws/modified_health_system.txt` are the
opposite case on purpose: they cancel vanilla's negative lines so the census
can do the work, and so carry the same magnitude, positive.
"""
import re
import unittest
from pathlib import Path

MOD_ROOT = Path(__file__).resolve().parent
MODIFIER = "state_pollution_reduction_health_mult"
LINE = re.compile(rf"^\s*{MODIFIER}\s*=\s*(-?[\d.]+)", re.M)

# Files whose uses are meant to protect: every value must be negative.
PROTECTIVE = (
    "common/power_bloc_principles/extra_power_bloc_principles.txt",
    "common/static_modifiers/gm_modifiers.txt",
)


class PollutionHealthPolarityTests(unittest.TestCase):
    def test_protective_sources_are_negative(self):
        found = 0
        for rel in PROTECTIVE:
            text = (MOD_ROOT / rel).read_text(encoding="utf-8-sig")
            for m in LINE.finditer(text):
                found += 1
                self.assertLess(float(m.group(1)), 0, f"{rel}: {m.group(0).strip()}")
        self.assertGreaterEqual(found, 4, "expected 3 principle tiers and the Green Movement boon")

    def test_health_law_injects_cancel_vanillas_negative_lines(self):
        text = (MOD_ROOT / "common/laws/modified_health_system.txt").read_text(encoding="utf-8-sig")
        values = [float(v) for v in LINE.findall(text)]
        self.assertEqual(values, [0.1, 0.1, 0.15])


if __name__ == "__main__":
    unittest.main()
