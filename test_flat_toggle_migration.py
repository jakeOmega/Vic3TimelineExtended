"""A 1.3.x save's flat Global Warming policies and colonial bands come off the entries once (#1466).

Mod releases 1.3.0 and 1.3.1, on vanilla 1.15.0, added the nine policies to
je_global_warming and swapped the five bands on je_colonial_empire with
add_modifier. Since #1466 both entries declare them, so a save's added copy
would stack with the new state and never come off. The migration, from each
entry's weekly pulse, removes every copy and carries a policy over to the
variable its declaration reads. PENDING REMOVAL at the next save-breaking
vanilla patch, with te_flat_toggle_migration_effects.txt.
"""

import re
import unittest
from pathlib import Path

from test_country_climate_policies import PolicyDeclarationTest
from test_colonial_scaling_modifiers import BANDS
from test_tax_code_rule import load

ROOT = Path(__file__).resolve().parent
MIGRATION = "common/scripted_effects/te_flat_toggle_migration_effects.txt"


def _blocks(value):
    return value if isinstance(value, list) else [value]


class PolicyMigrationTest(unittest.TestCase):
    def setUp(self):
        self.effect = load(MIGRATION)["gw_migrate_flat_policies"]

    def test_each_of_the_nine_moves_to_its_variable(self):
        moved = {}
        for block in _blocks(self.effect["if"]):
            (modifier,) = [block["limit"]["je:je_global_warming"]["has_modifier"]]
            self.assertEqual(block["je:je_global_warming"], {"remove_modifier": modifier})
            if modifier == "fossil_fuel_tariffs_modifier":
                # Only for a country that still leads its market.
                self.assertEqual(block["if"]["limit"], {"te_tax_owns_market": "yes"})
                moved[modifier] = block["if"]["set_variable"]["name"]
            else:
                moved[modifier] = block["set_variable"]["name"]
        self.assertEqual(moved, {m: v for m, (v, _, _) in PolicyDeclarationTest.NINE.items()})

    def test_the_copy_comes_off_before_the_variable_is_set(self):
        """On an untouched save the declared value is still 0 when the remove runs."""
        text = (ROOT / MIGRATION).read_text(encoding="utf-8-sig")
        body = text[text.index("gw_migrate_flat_policies = {"):text.index("ce_migrate_flat_bands = {")]
        for modifier, (variable, _, _) in PolicyDeclarationTest.NINE.items():
            with self.subTest(modifier=modifier):
                self.assertLess(body.index("remove_modifier = " + modifier),
                                body.index("name = " + variable))

    def test_the_entry_runs_it_weekly(self):
        entry = load("common/journal_entries/je_global_warming.txt")["je_global_warming"]
        self.assertEqual(entry["on_weekly_pulse"]["effect"]["gw_migrate_flat_policies"], "yes")


class BandMigrationTest(unittest.TestCase):
    def test_each_of_the_five_comes_off_the_entry(self):
        effect = load(MIGRATION)["ce_migrate_flat_bands"]["je:je_colonial_empire"]
        removed = {}
        for block in _blocks(effect["if"]):
            removed[block["limit"]["has_modifier"]] = block["remove_modifier"]
        self.assertEqual(removed, {band: band for band in BANDS})

    def test_the_entry_runs_it_weekly_and_nothing_else_adds(self):
        entry = load("common/journal_entries/je_colonial_empire.txt")["je_colonial_empire"]
        self.assertEqual(entry["on_weekly_pulse"]["effect"]["ce_migrate_flat_bands"], "yes")
        text = (ROOT / MIGRATION).read_text(encoding="utf-8-sig")
        self.assertNotRegex(re.sub(r"#[^\n]*", "", text), r"add_modifier")


if __name__ == "__main__":
    unittest.main()
