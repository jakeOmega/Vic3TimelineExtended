"""The Emergency Liquidity Program's crisis bounds (banking_cycle_simulation.md §25).

The program opens only in a downturn or panic, its +12 cycle value / +10 bubble
announcement lands once per crisis, and it closes itself (with the Disable
action's 1%-of-GDP refund) once the cycle has held at stable or above for
`banking_eliq_wind_down_months`. The engine warns about none of this going
wrong, so these checks read the script.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLICY_EFFECTS = ROOT / "common/scripted_effects/banking_policy_effects.txt"
POLICY_TRIGGERS = ROOT / "common/scripted_triggers/banking_policy_triggers.txt"
CYCLE_EFFECTS = ROOT / "common/scripted_effects/banking_cycle_effects.txt"
JE = ROOT / "common/journal_entries/je_banking.txt"
VALUES = ROOT / "common/script_values/extra_script_values.txt"
MESSAGES = ROOT / "common/messages/extra_messages.txt"
LOC = ROOT / "localization/english/te_miscellaneous_l_english.yml"
NOTIFICATION_LOC = ROOT / "localization/english/te_notifications_l_english.yml"
ANNOUNCED = "banking_eliq_announced"
COUNT = "banking_eliq_recovery_months"


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}") + 2]


def _loc(path, key):
    return re.search(r"(?m)^ %s:0 \"(.*)\"$" % re.escape(key), _text(path)).group(1)


class EmergencyLiquidityTests(unittest.TestCase):
    def test_opens_only_in_a_slump(self):
        possible = _top_level_block(
            _text(POLICY_TRIGGERS), "banking_possible_cb_emergency_liquidity_program = {"
        )
        self.assertRegex(
            possible,
            r"custom_tooltip = \{\s+text = banking_eliq_phase_tt\s+banking_cycle_is_recession = yes\s+\}",
        )

    def test_the_announcement_lands_once_per_crisis(self):
        on = _top_level_block(_text(POLICY_EFFECTS), "banking_effect_cb_emergency_liquidity_program = {")
        branch_start = on.index("limit = { NOT = { has_variable = %s } }" % ANNOUNCED)
        branch_end = on.index("else = {", branch_start)
        branch = on[branch_start:branch_end]
        self.assertIn("set_variable = { name = %s value = 1 }" % ANNOUNCED, branch)
        # both one-shots sit in that branch, and nowhere else in the effect
        for push in (
            "change_variable = { name = bubble_pressure add = 10 }",
            "change_variable = { name = finance_cycle_value add = 12 }",
        ):
            with self.subTest(push=push):
                self.assertIn(push, branch)
                self.assertEqual(on.count(push), 1)
        self.assertIn("custom_tooltip = banking_eliq_announcement_spent_tt", on[branch_end:])

    def test_wind_down_runs_after_the_crash_check(self):
        je = _text(JE)
        pulse = je[je.index("\ton_monthly_pulse = {"):]
        self.assertLess(
            pulse.index("banking_cycle_check_and_execute_crash = yes"),
            pulse.index("banking_cycle_eliq_wind_down = yes"),
        )
        # before the month's sample, so a wind-down's marker lands on its own bar
        self.assertLess(
            pulse.index("banking_cycle_eliq_wind_down = yes"),
            pulse.index("te_history_record_banking_samples = yes"),
        )

    def test_wind_down_closes_through_the_disable_action(self):
        wind = _top_level_block(_text(CYCLE_EFFECTS), "banking_cycle_eliq_wind_down = {")
        # counts while the program or the announcement is outstanding
        self.assertRegex(
            wind,
            r"OR = \{\s+has_variable = %s\s+banking_tool_eliq_active = yes\s+\}" % ANNOUNCED,
        )
        self.assertIn("limit = { var:finance_cycle_value >= 40 }", wind)
        self.assertIn("set_variable = { name = %s value = 0 }" % COUNT, wind)
        self.assertIn("limit = { var:%s >= banking_eliq_wind_down_months }" % COUNT, wind)
        # the Disable action's effect, so the refund and the history marker come with it
        self.assertIn("banking_effect_cb_disable_emergency_liquidity_program = yes", wind)
        self.assertIn("post_notification = banking_eliq_wound_down_notice", wind)
        self.assertIn("remove_variable = %s" % ANNOUNCED, wind)
        self.assertIn("remove_variable = %s" % COUNT, wind)
        off = _top_level_block(
            _text(POLICY_EFFECTS), "banking_effect_cb_disable_emergency_liquidity_program = {"
        )
        self.assertIn("add_treasury = emergency_liquidity_program_deactivation_refund", off)
        self.assertIn("banking_eliq_wound_down_notice = {", _text(MESSAGES))

    def test_tooltips_quote_the_wind_down_months(self):
        body = _top_level_block(_text(VALUES), "banking_eliq_wind_down_months = {")
        months = int(re.search(r"value = (\d+)", body).group(1))
        for path, key, pattern in (
            (LOC, "banking_eliq_wind_down_tt", r"#v (\d+)#! months"),
            (LOC, "banking_eliq_announcement_spent_tt", r"#v (\d+)#! months"),
            (NOTIFICATION_LOC, "notification_banking_eliq_wound_down_notice_desc", r"for (\d+) months"),
        ):
            with self.subTest(key=key):
                self.assertEqual(int(re.search(pattern, _loc(path, key)).group(1)), months)

    def test_dashboard_tooltip_quotes_the_announcement(self):
        line = _loc(LOC, "banking_dash_tt_cb_emergency_liquidity_program")
        self.assertIn("$banking_eliq_phase_tt$", line)
        self.assertIn("$banking_eliq_wind_down_tt$", line)
        self.assertIn("#P +12#!", line)
        self.assertIn("#N +10#!", line)


class SimulatorPortTests(unittest.TestCase):
    """scripts/analysis/banking_cycle_sim.py ports the same three bounds."""

    @classmethod
    def setUpClass(cls):
        from scripts.analysis import banking_cycle_sim as sim

        cls.S = sim

    def test_constants_match_the_script(self):
        on = _top_level_block(_text(POLICY_EFFECTS), "banking_effect_cb_emergency_liquidity_program = {")
        cycle = float(re.search(r"name = finance_cycle_value add = (\d+)", on).group(1))
        bubble = float(re.search(r"name = bubble_pressure add = (\d+)", on).group(1))
        self.assertEqual(self.S.ELIQ_ANNOUNCEMENT_CYCLE, cycle)
        self.assertEqual(self.S.ELIQ_ANNOUNCEMENT_BUBBLE, bubble)
        body = _top_level_block(_text(VALUES), "banking_eliq_wind_down_months = {")
        self.assertEqual(self.S.ELIQ_WIND_DOWN_MONTHS, float(re.search(r"value = (\d+)", body).group(1)))

    def test_one_crisis_one_announcement_then_wind_down(self):
        S = self.S
        cfg = S.Config(points=8)
        state = S.State(finance_cycle_value=5, bubble_pressure=0)
        self.assertTrue(S.tool_possible(cfg, state, "eliq"))
        state.tools.add("eliq")
        S.on_tool_enabled(state, "eliq")
        self.assertEqual((state.finance_cycle_value, state.bubble_pressure), (17, 10))
        # closed and reopened in the same crisis: no second announcement
        state.tools.discard("eliq")
        state.tools.add("eliq")
        S.on_tool_enabled(state, "eliq")
        self.assertEqual((state.finance_cycle_value, state.bubble_pressure), (17, 10))
        # a month back below stable restarts the count
        state.finance_cycle_value = 45
        for _ in range(int(S.ELIQ_WIND_DOWN_MONTHS) - 1):
            S.eliq_wind_down(cfg, state)
        state.finance_cycle_value = 35
        S.eliq_wind_down(cfg, state)
        self.assertIn("eliq", state.tools)
        state.finance_cycle_value = 45
        for _ in range(int(S.ELIQ_WIND_DOWN_MONTHS)):
            S.eliq_wind_down(cfg, state)
        self.assertNotIn("eliq", state.tools)
        self.assertFalse(state.eliq_announced)
        self.assertEqual(state.eliq_wind_downs, 1)
        # and outside a slump it cannot be opened at all
        self.assertFalse(S.tool_possible(cfg, state, "eliq"))


if __name__ == "__main__":
    unittest.main()
