"""Balance and safety regressions for the shipped crisis risk and exchange paths."""

import unittest
from pathlib import Path

from scripts.analysis.nuclear_incident_rates import Posture, RiskModel
from scripts.analysis.nuclear_observer_report import read_records, summarize
from test_nuclear_deterrence import block, read, strip_comments

ROOT = Path(__file__).resolve().parent


class TestRiskBalance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()

    def test_two_week_acute_crisis_has_about_fifty_percent_incidence(self):
        p = Posture(readiness=3, danger=75, stage=3)
        chance = 1 - (1 - self.model.probability(p)) ** 4
        self.assertGreater(chance, .48)
        self.assertLess(chance, .52)

    def test_peace_is_nonzero_and_offensive_doctrine_increases_exposure(self):
        for readiness in range(4):
            p = Posture(readiness=readiness)
            self.assertGreater(self.model.probability(p), 0)
            self.assertGreater(self.model.probability(Posture(readiness=readiness, doctrine=5)),
                               self.model.probability(p))

    def test_routine_mishaps_do_not_dilute_the_meaningful_draw(self):
        for p in (Posture(), Posture(readiness=3, danger=100, stage=3, authority=3)):
            self.assertNotIn("routine_mishap", self.model.weights(p))
            self.assertGreater(self.model.weights(p)["weapons_accident"], 0)

    def test_central_control_cannot_launch_without_a_government_order(self):
        self.assertEqual(self.model.unheld_share(Posture(readiness=3, danger=100, stage=3)), 0)

    def test_delegated_commanders_have_residual_peacetime_launch_risk(self):
        self.assertGreater(self.model.unheld_share(Posture(readiness=2, authority=2)), 0)
        self.assertEqual(self.model.unheld_share(Posture(readiness=2, authority=2, plausible_attacker=False)), 0)

    def test_strain_reliability_and_weekly_cap(self):
        p = Posture(readiness=3, danger=100, strain=100, reliability=0, doctrine=5)
        self.assertEqual(self.model.probability(p), .35)
        self.assertLess(self.model.probability(Posture(readiness=3, reliability=95)),
                        self.model.probability(Posture(readiness=3, reliability=20)))

    def test_low_postures_do_not_inherit_a_monthly_crisis_roll(self):
        effects = strip_comments(read(ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"))
        self.assertNotIn("nd_roll_incident", block(effects, "nd_monthly_update"))
        self.assertEqual(block(effects, "nd_weekly_update").count("nd_roll_incident = yes"), 1)


class TestPeacetimeExchangeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = strip_comments(read(ROOT / "common/scripted_effects/nuclear_exchange_effects.txt"))
        cls.triggers = strip_comments(read(ROOT / "common/scripted_triggers/nuclear_exchange_triggers.txt"))
        cls.dispatch = strip_comments(read(ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"))

    def test_initial_launch_does_not_start_a_conventional_war(self):
        launch = block(self.dispatch, "nd_launch_or_intercept")
        self.assertIn("nd_exchange_open", launch)
        self.assertNotIn("create_diplomatic_play", launch)
        self.assertNotIn("set_war", launch)
        opened = block(self.effects, "nd_exchange_open")
        self.assertNotIn("nd_exchange_start_war", opened)
        self.assertNotIn("create_diplomatic_play", opened)

    def test_peacetime_dispatch_requires_an_incident_or_actual_retaliation(self):
        gate = block(self.triggers, "nd_peacetime_incident_dispatch")
        self.assertIn("nd_in_peacetime_exchange_with", gate)
        self.assertIn("nd_was_struck_by", gate)
        for name in ("nd_dispatch_strategic_strike", "nd_dispatch_tactical_strike"):
            self.assertIn("nd_peacetime_incident_dispatch = yes", block(self.dispatch, name))

    def test_renewed_launch_invalidates_both_votes_and_popups(self):
        renewed = block(self.effects, "nd_exchange_note_launch")
        self.assertEqual(renewed.count("name = nd_exchange_answer value = 0"), 2)
        self.assertIn("name = nd_exchange_revision add = 1", renewed)
        valid = block(self.triggers, "nd_exchange_offer_valid")
        self.assertIn("var:nd_exchange_id = scope:nd_exchange_offer_id", valid)
        self.assertIn("var:nd_exchange_revision = scope:nd_exchange_offer_revision", valid)
        self.assertIn("nd_exchange_quiet_days >= 7", valid)

    def test_both_answers_are_required_and_mutual_acceptance_cannot_start_war(self):
        choose = block(self.effects, "nd_exchange_choose")
        self.assertIn("scope:nd_exchange_enemy = { var:nd_exchange_answer > 0 }", choose)
        self.assertIn("var:nd_exchange_answer = 1 scope:nd_exchange_enemy = { var:nd_exchange_answer = 1 }", choose)
        self.assertIn("RESULT = mutual_standdown", choose)
        self.assertIn("var:nd_exchange_answer = 2", choose)
        self.assertIn("scope:nd_exchange_refusing", choose)

    def test_standdown_clears_licence_and_exchange_records(self):
        cleared = block(self.effects, "nd_exchange_clear_own_record")
        for key in ("nd_exchange_id", "nd_exchange_opponent", "nd_exchange_revision", "nd_exchange_answer", "nuked_by_country"):
            self.assertIn(f"remove_variable = {key}", cleared)
        close = block(self.effects, "nd_exchange_close")
        self.assertEqual(close.count("nd_exchange_clear_own_record = yes"), 2)

    def test_last_warhead_does_not_deactivate_the_settlement_clock(self):
        triggers = strip_comments(read(ROOT / "common/scripted_triggers/nuke_triggers.txt"))
        self.assertIn("has_variable = nd_exchange_id", block(triggers, "nuclear_program_entry_applies"))

    def test_response_strike_attributes_damage_to_the_retaliator(self):
        effects = strip_comments(read(ROOT / "common/scripted_effects/extra_effects.txt"))
        response = block(effects, "nuclear_response_strike")
        self.assertIn("scope:target_country = { save_scope_as = nd_current_strike_launcher }", response)
        damage = block(effects, "nuclear_industrial_strike")
        self.assertIn("value = scope:nd_current_strike_launcher", damage)


class TestObserverReport(unittest.TestCase):
    def test_engine_prefixes_partial_logs_and_numeric_templates(self):
        lines = [
            "[debug.cpp:1] TE_NUCLEAR: type=risk; country=United States; crisis=12; exchange=0; danger=75; incident_weekly_permille=159.58\n",
            "[debug.cpp:1] TE_NUCLEAR: type=incident; country=United States; crisis=12; exchange=0; family=unconfirmed_warning\n",
            "TE_NUCLEAR: type=incident; country=Russia; crisis=12; exchange=0; family=routine_mishap\n",
            "TE_NUCLEAR: type=action; country=Russia; crisis=0; exchange=7; action=exchange_answer_1\n",
            "TE_NUCLEAR: type=crisis_end; country=United States; crisis=12; exchange=7; outcome=7\n",
            "TE_NUCLEAR: type=risk; country=Russia; crisis=0; exchange=0; danger=0; incident_weekly_permille=[raw template]\n",
            "unrelated log line\n",
        ]
        report = summarize(read_records(lines))
        self.assertEqual(report["observed_crisis_ids"], 1)
        self.assertEqual(report["observed_exchange_ids"], 1)
        self.assertEqual(report["meaningful_incidents"], 1)
        self.assertEqual(report["routine_mishaps"], 1)
        self.assertAlmostEqual(report["exposure_by_danger_band"]["3"]["expected_incidents"], .16)
        self.assertEqual(report["unresolved_risk_records"], 1)
        self.assertEqual(report["crisis_outcomes"], {"7": 1})


if __name__ == "__main__":
    unittest.main()
