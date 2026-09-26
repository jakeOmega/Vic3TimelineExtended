"""Peacetime ammunition is half vanilla's; mobilized, it is four times that.

The mod halves every combat unit's ammunition upkeep. Mod-owned units carry the
halved value, while vanilla units take an INJECT diff of minus half vanilla's
value, summed with vanilla's own
(common/combat_unit_types/extra_combat_units.txt). Basic supplies then
multiplies ammunition by 4 while mobilized, and extra and luxurious supplies
stop adding theirs (common/mobilization_options/te_wartime_munitions_injections.txt).

The diffs are hard-coded against vanilla's numbers, so a vanilla patch that
changes a unit's ammunition, or gives ammunition to a new unit, would leave the
diff wrong without any error from the engine. These tests read vanilla from
the committed vanilla_parsed/ snapshot and fail on that drift.
"""

import unittest
from pathlib import Path

import vanilla_parsed
from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
UNITS = ROOT / "common/combat_unit_types/extra_combat_units.txt"
MOBILIZATION = ROOT / "common/mobilization_options/te_wartime_munitions_injections.txt"

AMMO_ADD = "goods_input_ammunition_add"
AMMO_MULT = "goods_input_ammunition_mult"

# Wartime ammunition as a multiple of peacetime: 1 + basic supplies' mult.
WAR_MULTIPLE = 4.0
# The effective ammunition mult of each vanilla supplies option after the mod.
SUPPLIES_TARGET = {
    "mobilization_option_basic_supplies": WAR_MULTIPLE - 1,
    "mobilization_option_extra_supplies": 0.0,
    "mobilization_option_luxurious_supplies": 0.0,
}


def _body(entry):
    """The block of a parsed `key = { ... }` entry, an (op, value) pair."""
    return entry[1]


def _num(block, key):
    """A number from a parsed block; 0 when the key is absent."""
    if not block or key not in block:
        return 0.0
    return float(block[key][1])


def _parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(str(path), apply_directives=False)
    return parser.data


class WartimeMunitionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        snapshot = vanilla_parsed.load()
        cls.vanilla_units = snapshot.data["Combat Unit Types"]
        cls.vanilla_options = snapshot.data["Mobilization Options"]
        cls.mod_units = _parse(UNITS)
        cls.mod_options = _parse(MOBILIZATION)

    def _vanilla_ammo(self, unit):
        upkeep = _body(self.vanilla_units[unit]).get("upkeep_modifier")
        return _num(upkeep and _body(upkeep), AMMO_ADD)

    def _mod_upkeep(self, key):
        entry = self.mod_units.get(key)
        if entry is None:
            return None
        upkeep = _body(entry).get("upkeep_modifier")
        return _body(upkeep) if upkeep else {}

    def test_every_vanilla_unit_using_ammunition_is_halved(self):
        units = [u for u in self.vanilla_units if self._vanilla_ammo(u) > 0]
        self.assertTrue(units, "no vanilla unit uses ammunition: snapshot shape changed?")
        for unit in units:
            vanilla = self._vanilla_ammo(unit)
            with self.subTest(unit=unit, vanilla=vanilla):
                replaced = self._mod_upkeep("REPLACE:" + unit)
                injected = self._mod_upkeep("INJECT:" + unit)
                if replaced is not None:
                    self.assertAlmostEqual(
                        _num(replaced, AMMO_ADD), vanilla / 2,
                        msg=f"REPLACE:{unit} should carry half of vanilla's {vanilla}",
                    )
                else:
                    self.assertIsNotNone(
                        injected,
                        f"{unit} uses {vanilla} ammunition in vanilla but has no INJECT "
                        f"diff in {UNITS.name}; add upkeep_modifier = "
                        f"{{ {AMMO_ADD} = {-vanilla / 2:g} }}",
                    )
                    self.assertAlmostEqual(
                        _num(injected, AMMO_ADD), -vanilla / 2,
                        msg=f"INJECT:{unit} should subtract half of vanilla's {vanilla}",
                    )

    def test_no_ammunition_diff_without_vanilla_ammunition(self):
        for key in self.mod_units:
            if not key.startswith("INJECT:"):
                continue
            unit = key.split(":", 1)[1]
            upkeep = self._mod_upkeep(key)
            if AMMO_ADD not in upkeep:
                continue
            with self.subTest(unit=unit):
                self.assertIn(unit, self.vanilla_units)
                self.assertGreater(
                    self._vanilla_ammo(unit), 0,
                    f"INJECT:{unit} cuts ammunition vanilla no longer charges",
                )

    def test_injected_unit_upkeep_touches_only_ammunition(self):
        # A diff on another good would not survive a vanilla change the way
        # the INJECT is meant to.
        for key in self.mod_units:
            if key.startswith("INJECT:"):
                upkeep = self._mod_upkeep(key)
                with self.subTest(unit=key):
                    self.assertLessEqual(set(upkeep), {AMMO_ADD})

    def test_supplies_ammunition_multipliers(self):
        for option, target in SUPPLIES_TARGET.items():
            with self.subTest(option=option):
                vanilla_block = _body(self.vanilla_options[option]).get("upkeep_modifier_unscaled")
                vanilla = _num(vanilla_block and _body(vanilla_block), AMMO_MULT)
                entry = self.mod_options.get("INJECT:" + option)
                self.assertIsNotNone(entry, f"no INJECT:{option} in {MOBILIZATION.name}")
                diff_block = _body(_body(entry)["upkeep_modifier_unscaled"])
                self.assertEqual(set(diff_block), {AMMO_MULT}, "the diff touches only ammunition")
                self.assertAlmostEqual(
                    vanilla + _num(diff_block, AMMO_MULT), target,
                    msg=f"{option}: vanilla {vanilla:+g} plus the diff should total {target:+g}",
                )


if __name__ == "__main__":
    unittest.main()
