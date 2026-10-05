"""The Bank Holiday's run freeze and reopening bounce (banking_cycle_simulation.md §19).

The holiday is a timed journal-entry modifier. While it is on, momentum cannot
fall below 0; if it runs its full ninety days, the banks reopen with a momentum
bounce. The bounce is owed through a country variable,
`banking_bank_holiday_reopening`, that every early ending must clear, or a
holiday ended early would still pay it. Nothing in the engine warns about any
of this going wrong, so these checks read the script.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLICY_EFFECTS = ROOT / "common/scripted_effects/banking_policy_effects.txt"
CYCLE_EFFECTS = ROOT / "common/scripted_effects/banking_cycle_effects.txt"
CLEANUP = ROOT / "common/scripted_effects/extra_effects.txt"
JE = ROOT / "common/journal_entries/je_banking.txt"
VALUES = ROOT / "common/script_values/extra_script_values.txt"
LOC = ROOT / "localization/english/te_miscellaneous_l_english.yml"
MARKER = "banking_bank_holiday_reopening"


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}") + 2]


class BankHolidayTests(unittest.TestCase):
    def test_declaring_sets_the_marker(self):
        on = _top_level_block(_text(POLICY_EFFECTS), "banking_effect_cb_bank_holiday = {")
        self.assertIn("set_variable = { name = %s value = 1 }" % MARKER, on)
        self.assertIn("add_modifier = { name = banking_bank_holiday days = 90 }", on)

    def test_every_early_ending_clears_the_marker(self):
        off = _top_level_block(_text(POLICY_EFFECTS), "banking_effect_cb_disable_bank_holiday = {")
        self.assertIn("remove_variable = %s" % MARKER, off)
        strip = _top_level_block(_text(CLEANUP), "remove_banking_market_modifiers_effect = {")
        self.assertIn("MODIFIER = banking_bank_holiday ", strip)
        self.assertIn("remove_variable = %s" % MARKER, strip)
        # a revolution's winner inherits the marker but not the modifier
        je = _text(JE)
        immediate = je[je.index("\timmediate = {"): je.index("\ton_monthly_pulse = {")]
        self.assertRegex(
            immediate,
            r"has_variable = %s\s+banking_tool_bank_holiday_active = no\s+\}\s+remove_variable = %s"
            % (MARKER, MARKER),
        )

    def test_reopening_runs_before_the_cycle_advances(self):
        je = _text(JE)
        pulse = je[je.index("\ton_monthly_pulse = {"):]
        self.assertLess(
            pulse.index("banking_cycle_bank_holiday_reopen = yes"),
            pulse.index("banking_cycle_advance_variables = yes"),
        )
        reopen = _top_level_block(_text(CYCLE_EFFECTS), "banking_cycle_bank_holiday_reopen = {")
        self.assertIn("banking_tool_bank_holiday_active = no", reopen)
        self.assertIn("remove_variable = %s" % MARKER, reopen)
        self.assertIn("add = banking_bank_holiday_reopen_momentum", reopen)

    def test_the_freeze_comes_before_momentum_is_applied(self):
        advance = _top_level_block(_text(CYCLE_EFFECTS), "banking_cycle_advance_variables = {")
        freeze = advance.index("banking_tool_bank_holiday_active = yes")
        applied = advance.index("add = var:finance_cycle_momentum")
        self.assertLess(freeze, applied)
        # and after every push, so nothing later in the month takes it back under
        self.assertLess(advance.index("random_list = {"), freeze)

    def test_tooltips_quote_the_bounce(self):
        body = _top_level_block(_text(VALUES), "banking_bank_holiday_reopen_momentum = {")
        value = float(re.search(r"value = (-?[\d.]+)", body).group(1))
        loc = _text(LOC)
        for key in ("banking_bank_holiday_reopen_tt", "banking_bank_holiday_forfeit_tt"):
            with self.subTest(key=key):
                line = re.search(r"(?m)^ %s:0 \"(.*)\"$" % key, loc).group(1)
                quoted = float(re.search(r"#G \+([\d.]+)#!", line).group(1))
                self.assertEqual(quoted, value)


if __name__ == "__main__":
    unittest.main()
