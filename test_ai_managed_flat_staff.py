"""AI-managed production methods with a flat crew.

A `pm_ai_managed_*` method that cancels its base method's per-level workforce and
hires a fixed crew in `unscaled` (docs/superpowers/archive/specs/2026-10-16-ai-managed-
flat-staff-design.md) asks for 1,000 engineers a building, and the game hires small
groups unevenly. Like the Grid Transfer Station (power_grid_pms.txt), the crew's job
is made very attractive (`building_job_attractiveness_mult`) so it fills and stays.
The engine logs nothing for a crew that never fills, so a method added or split later
has to carry the line too.

Run: python3 test_ai_managed_flat_staff.py
"""
import os
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
PMS = os.path.join(REPO, "common", "production_methods", "extra_pms.txt")
MIN_ATTRACTIVENESS = 5  # +500%, as pm_grid_transfer_base


def _unwrap(value):
    """The parser keeps each value as an (operator, value) pair."""
    while isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str):
        value = value[1]
    return value


def _flat_crew_methods():
    """{method: its unscaled block} for each pm_ai_managed_* that hires in unscaled."""
    parser = ParadoxFileParser()
    parser.parse_file(PMS)
    methods = {}
    for name, body in parser.data.items():
        body = _unwrap(body)
        if not name.startswith("pm_ai_managed_") or not isinstance(body, dict):
            continue
        modifiers = _unwrap(body.get("building_modifiers"))
        unscaled = _unwrap(modifiers.get("unscaled")) if isinstance(modifiers, dict) else None
        if isinstance(unscaled, dict) and any(
                key.startswith("building_employment_") for key in unscaled):
            methods[name] = {key: _unwrap(value) for key, value in unscaled.items()}
    return methods


class FlatCrewAttractivenessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.methods = _flat_crew_methods()

    def test_the_flat_crew_methods_are_found(self):
        # Fab, chemical, explosives, arms, artillery, munition x2, motor x2, tooling x2, power x4.
        self.assertGreaterEqual(len(self.methods), 15, sorted(self.methods))

    def test_every_flat_crew_is_a_very_attractive_job(self):
        for name, unscaled in sorted(self.methods.items()):
            value = unscaled.get("building_job_attractiveness_mult")
            self.assertIsNotNone(value, f"{name}: no building_job_attractiveness_mult in unscaled")
            self.assertGreaterEqual(float(value), MIN_ATTRACTIVENESS, name)


if __name__ == "__main__":
    unittest.main()
