"""Balance and safety regressions for the shipped crisis risk and exchange paths."""

import re
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

    def test_two_week_acute_crisis_has_about_a_quarter_incidence(self):
        # Was about half until the 2026-10-28 calibration to the rework
        # spec's §2.3 launch bands (TestSpecBands), which set the surcharge.
        p = Posture(readiness=3, danger=75, stage=3)
        chance = 1 - (1 - self.model.probability(p)) ** 4
        self.assertGreater(chance, .20)
        self.assertLess(chance, .35)

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

    def test_crisis_exposure_never_draws_a_weapons_accident(self):
        # A Routine or Recessed force in a crisis has no misreading family to
        # draw, so the crisis adds nothing; at High Alert it draws only those.
        for readiness in (0, 1):
            p = Posture(readiness=readiness, danger=100, stage=3)
            self.assertEqual(self.model.number("nd_incident_crisis_share", p), 0)
            self.assertAlmostEqual(self.model.probability(p), self.model.probability(Posture(readiness=readiness)), 4)
        acute = Posture(readiness=3, danger=100, stage=3)
        self.assertEqual(self.model.family_weights(acute, True)["weapons_accident"], 0)
        self.assertGreater(self.model.family_weights(acute, False)["weapons_accident"], 0)
        self.assertLess(self.model.weights(acute)["weapons_accident"], .01)

    def test_hold_chance_reads_the_moment(self):
        # Low reliability, so no ceiling clips the context terms.
        hold = {stage: self.model.number("nd_hold_chance", Posture(readiness=3, authority=3, stage=stage, reliability=20))
                for stage in (0, 2, 3)}
        self.assertEqual(hold[0] - hold[3], 25)
        self.assertEqual(hold[2] - hold[3], 10)
        self.assertEqual(self.model.number("nd_hold_chance", Posture(readiness=3, authority=3, war=True, reliability=20)),
                         hold[3])

    def test_delegation_leaves_warnings_to_the_government_outside_war(self):
        p = Posture(readiness=3, danger=100, stage=3, authority=2)
        warning_only = self.model.unheld_share(p) - self.model.weights(p)["isolated_commander"] * (
            1 - self.model.number("nd_hold_chance", p) / 100)
        self.assertAlmostEqual(warning_only, 0)
        effects = strip_comments(read(ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"))
        chain = block(effects, "nd_start_unconfirmed_warning")
        self.assertNotIn("nd_crisis_stage_at_least = { STAGE = 3 }", chain)

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
        self.assertIn("action=exchange_end_mutual_standdown;", choose)
        self.assertIn("create_bidirectional_truce", choose)
        self.assertIn("var:nd_exchange_answer = 2", choose)
        self.assertIn("scope:nd_exchange_refusing", choose)

    def test_a_war_that_has_not_begun_keeps_the_exchange_open(self):
        request = block(self.effects, "nd_exchange_request_war")
        started, pending = request.split("else = {", 1)
        self.assertIn("has_war_with = scope:nd_exchange_enemy", started)
        self.assertIn("nd_exchange_close = yes", started)
        self.assertNotIn("nd_exchange_close", pending)
        self.assertIn("name = nd_exchange_war_pending value = 1", pending)
        self.assertIn("name = nd_exchange_war_pending value = 2", pending)
        weekly = block(self.effects, "nd_exchange_weekly_update")
        self.assertIn("nd_exchange_war_pending_days >= 14", weekly)
        self.assertIn("post_notification = nd_exchange_war_failed", weekly)
        self.assertIn("nd_exchange_start_war = yes", weekly)
        valid = block(self.triggers, "nd_exchange_offer_valid")
        self.assertIn("NOT = { has_variable = nd_exchange_war_pending }", valid)
        cleared = block(self.effects, "nd_exchange_clear_own_record")
        self.assertIn("remove_variable = nd_exchange_war_pending", cleared)

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


class TestObserverRecords(unittest.TestCase):
    FILES = (
        "common/scripted_effects/nuclear_observer_effects.txt",
        "common/scripted_effects/nuclear_exchange_effects.txt",
        "common/scripted_effects/nuclear_deterrence_effects.txt",
        "common/scripted_effects/nuclear_crisis_effects.txt",
        "common/scripted_effects/extra_effects.txt",
        "events/nuclear_crisis_events.txt",
        "events/nuclear_incident_events.txt",
    )

    def records(self):
        for name in self.FILES:
            for line in strip_comments(read(ROOT / name)).splitlines():
                for record in re.findall(r'debug_log = "(TE_NUCLEAR: [^"]*)"', line):
                    yield name, record

    def test_no_parameter_inside_a_record(self):
        # A $PARAM$ inside a debug_log string logs garbled
        # (scripting_best_practices.md, "Runtime Debugging with debug_log").
        records = list(self.records())
        self.assertGreater(len(records), 100)
        for name, record in records:
            self.assertNotIn("$", record, f"{name}: {record[:80]}")

    def test_every_record_parses_with_a_name(self):
        for name, record in self.records():
            fields = next(read_records([record]))
            kind = fields["type"]
            if kind == "action":
                self.assertRegex(fields.get("action", ""), r"^[a-z_0-9.]+$", f"{name}: {record[:80]}")
            elif kind == "incident":
                self.assertIn(fields.get("family"), {"routine_mishap", "weapons_accident", "unconfirmed_warning",
                                                     "exercise_misread", "isolated_commander"})
            elif kind == "crisis_end":
                self.assertRegex(fields.get("outcome", ""), r"^\d+$")

    def test_weekly_samples_need_the_observer_switch(self):
        effects = strip_comments(read(ROOT / "common/scripted_effects/nuclear_observer_effects.txt"))
        for name in ("nd_log_risk_sample", "nd_log_crisis_sample"):
            self.assertIn("has_global_variable = nd_observer_logging", block(effects, name))


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


class TestObserverRework(unittest.TestCase):
    """The observer report counts uses per Acute crisis, near misses and
    launches nobody meant (rework spec §2.4)."""

    def test_uses_per_acute_crisis_and_near_misses(self):
        lines = [
            "TE_NUCLEAR: type=crisis_acute; country=United States; crisis=12; exchange=0\n",
            "TE_NUCLEAR: type=crisis_acute; country=Russia; crisis=13; exchange=0\n",
            "TE_NUCLEAR: type=crisis_end; outcome=7; country=United States; crisis=12; exchange=0\n",
            "TE_NUCLEAR: type=crisis_end; outcome=8; country=Russia; crisis=13; exchange=0\n",
            "TE_NUCLEAR: type=action; action=launch_held; country=Russia; crisis=13; exchange=0\n",
            "TE_NUCLEAR: type=action; action=launch_held; country=Russia; crisis=13; exchange=0\n",
            "TE_NUCLEAR: type=action; action=incident_launch_warning; country=United States; crisis=12; exchange=0\n",
        ]
        report = summarize(read_records(lines))
        self.assertEqual(report["acute_crises"], 2)
        self.assertEqual(report["uses_per_acute_crisis"], 0.5)
        self.assertEqual(report["near_misses"], 2)
        self.assertEqual(report["unordered_or_mistaken_launches"], 1)

    def test_acute_record_written_once_per_crisis(self):
        effects = strip_comments(read(ROOT / "common/scripted_effects/nuclear_observer_effects.txt"))
        body = block(effects, "nd_log_crisis_acute_once")
        self.assertIn("type=crisis_acute", body)
        self.assertNotIn("$", body)
        crisis = strip_comments(read(ROOT / "common/scripted_effects/nuclear_crisis_effects.txt"))
        self.assertIn("nd_log_crisis_acute_once = yes", block(crisis, "nd_crisis_weekly_tick"))
        self.assertIn("nd_crisis_acute_logged", crisis[crisis.index("nd_crisis_clear_vars = {"):])


class TestCrisisAndWarModel(unittest.TestCase):
    """The rework spec's §2.3 Acute-crisis table, the war-year and the
    peacetime pair-year (2026-10-28 rework spec §2, §11)."""

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()

    def test_acute_table_has_five_rows(self):
        import contextlib
        import io
        import sys
        from unittest import mock
        from scripts.analysis import nuclear_incident_rates
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["nuclear_incident_rates.py"]), contextlib.redirect_stdout(out):
            nuclear_incident_rates.main()
        for row in ("Central, safeguards 3", "Central, safeguards 0", "Delegation, safeguards 3",
                    "Launch on Warning, safeguards 3", "Launch on Warning, safeguards 0"):
            self.assertIn(row, out.getvalue())

    def test_acute_crisis_is_symmetric(self):
        p = Posture(readiness=3, authority=3, safeguards=0, danger=80, stage=3)
        side_week = self.model.launch_chance_week(p)
        self.assertGreater(side_week, 0)
        self.assertAlmostEqual(self.model.acute_crisis(p, p), 1 - (1 - side_week) ** 16)

    def test_order_chance_zero_outside_war_or_acute(self):
        self.assertEqual(self.model.order_chance(Posture(readiness=3, stage=2, danger=60)), 0.0)
        self.assertEqual(self.model.order_chance(Posture(readiness=3, stage=0, war=False)), 0.0)

    def test_unknown_trigger_raises(self):
        with self.assertRaises(ValueError):
            self.model.condition([("no_such_trigger", "=", "yes")], Posture())


class TestLaunchUnderAttack(unittest.TestCase):
    """The government may order a launch under attack in a war or an Acute
    crisis with the suspect, under every doctrine but No First Use (rework
    spec §5.3; owner, 2026-10-28)."""

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()
        cls.events = strip_comments(read(ROOT / "events/nuclear_incident_events.txt"))

    def test_order_needs_war_or_acute(self):
        acute = Posture(readiness=3, stage=3, danger=80, doctrine=2)
        self.assertGreater(self.model.order_chance(acute), 0)
        self.assertGreater(self.model.order_chance(Posture(readiness=3, war=True, doctrine=2)), 0)
        self.assertEqual(self.model.order_chance(Posture(readiness=3, stage=2, danger=60, doctrine=2)), 0)

    def test_order_blocked_only_by_nfu(self):
        self.assertEqual(self.model.order_chance(Posture(readiness=3, stage=3, danger=80, doctrine=1)), 0)
        for doctrine in (2, 3, 4, 5):
            self.assertGreater(self.model.order_chance(Posture(readiness=3, stage=3, danger=80, doctrine=doctrine)), 0)
        body = block(self.events, "nuclear_incident.1")
        order = body[body.index("name = nuclear_incident.1.c"):]
        trigger = block(order, "trigger")
        self.assertNotIn("nd_doctrine_permits_strike", trigger)
        self.assertIn("nd_launch_under_attack_context = { SUSPECT = scope:nd_warning_suspect }", trigger)
        self.assertIn("nd_launch_under_attack_doctrine = { SUSPECT = scope:nd_warning_suspect }", trigger)
        for gate in ("nd_pledge_permits_strike", "nd_war_law_permits_strategic_strike", "nd_forces_assembled"):
            self.assertIn(gate, trigger)

    def test_order_outside_war_records_first_use(self):
        # The order dispatches through nd_launch_or_intercept as a warning
        # launch, which a peacetime exchange accepts; the recorder prices it
        # as every use is priced. Its only incident-only branch is No First
        # Use's breach follow-up, and No First Use cannot give this order.
        body = block(self.events, "nuclear_incident.1")
        order = body[body.index("name = nuclear_incident.1.c"):]
        self.assertIn("nd_launch_or_intercept = { VICTIM = scope:nd_warning_suspect NARRATE = yes KIND = warning }", order)
        effects = strip_comments(read(ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"))
        recorder = block(effects, "nd_record_nuclear_use")
        self.assertEqual(recorder.count("nd_incident_launch_warning"), 1)
        nfu = recorder[recorder.index("nd_doctrine_nfu = yes"):]
        self.assertLess(nfu.index("nd_incident_launch_warning"), nfu.index("set_variable = nd_nfu_unordered_breach"))
        self.assertIn("set_variable = { name = nd_has_used value = 1 }", recorder)

    def test_ai_order_weights(self):
        body = block(self.events, "nuclear_incident.1")
        chance = block(body[body.index("name = nuclear_incident.1.c"):], "ai_chance")
        for needle in ("var:nd_survivors_vs_suspect < 3", "ruler_is_aggressive = yes",
                       "var:nd_strain >= 50", "ruler_is_cautious = yes", "recon_satellites",
                       "satellite_communications", "nd_crisis_talks_open_either = yes"):
            self.assertIn(needle, chance)


class TestSpecBands(unittest.TestCase):
    """The rework spec's calibration targets (§2.1, §2.3): no posture is safe,
    and recklessness is not free."""

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()

    def acute(self, authority, safeguards):
        side = self.model.acute_posture(authority, safeguards)
        return self.model.acute_crisis(side, side)

    def assertBand(self, value, low, high):
        self.assertGreaterEqual(value, low)
        self.assertLessEqual(value, high)

    def test_acute_bands(self):
        self.assertBand(self.acute(1, 3), 0.02, 0.03)
        self.assertBand(self.acute(1, 0), 0.04, 0.06)
        self.assertBand(self.acute(2, 3), 0.03, 0.05)
        self.assertBand(self.acute(3, 3), 0.08, 0.12)
        self.assertBand(self.acute(3, 0), 0.20, 0.30)

    def test_delegation_beats_central_none(self):
        # Owner call 6: Delegation with safeguards is comparable in risk to
        # Central with none, and pays better deterrence.
        self.assertLessEqual(self.acute(2, 3), self.acute(1, 0) * 1.25)

    def war_side(self):
        return self.model.at_reliability_target(Posture(readiness=3, authority=1, safeguards=1))

    def test_war_year_band2(self):
        self.assertBand(self.model.war_year(self.war_side(), self.war_side(), 2), 0.08, 0.15)

    def test_war_year_band3(self):
        self.assertBand(self.model.war_year(self.war_side(), self.war_side(), 3), 0.15, 0.30)

    def test_peace_pair_year(self):
        side = self.model.at_reliability_target(Posture(readiness=2, authority=2, safeguards=2))
        self.assertBand(self.model.peace_pair_year(side, side), 0.0005, 0.0015)

    def test_near_misses_several_times_unheld(self):
        self.assertGreaterEqual(self.model.near_miss_ratio(self.model.acute_posture(3, 3)), 3)


class TestHoldAndExposure(unittest.TestCase):
    """The chance of a halt has a ceiling by context and reads the suspect, the
    hotline and our own vulnerability (rework spec §4.3); a war with an armed
    enemy adds the crisis surcharge (§5.1)."""

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()

    def hold(self, **kw):
        return self.model.number("nd_hold_chance", Posture(**kw))

    def test_hold_ceiling_by_context(self):
        high = dict(readiness=3, reliability=98, safeguards=3)
        self.assertEqual(self.hold(**high), 97)
        self.assertEqual(self.hold(stage=2, danger=50, **high), 92)
        self.assertEqual(self.hold(stage=3, danger=80, **high), 85)
        self.assertEqual(self.hold(war=True, **high), 85)

    def test_hold_chance_suspect_terms(self):
        low = dict(readiness=3, reliability=0, safeguards=0, stage=3, danger=80)
        base = self.hold(suspect_readiness=1, **low)
        # Room above and below for every term: no clamp interferes.
        self.assertLessEqual(base + 20, 85)
        self.assertGreaterEqual(base - 10, 20)
        self.assertEqual(self.hold(suspect_readiness=0, **low), base + 20)
        self.assertEqual(self.hold(suspect_readiness=3, **low), base - 5)
        self.assertEqual(self.hold(suspect_readiness=1, talks=True, **low), base + 10)
        self.assertEqual(self.hold(suspect_readiness=1, survivability=0, **low), base - 10)
        self.assertEqual(self.hold(suspect_readiness=1, survivability=25, **low), base - 5)

    def test_hold_chance_suspect_optional(self):
        values = strip_comments(read(ROOT / "common/script_values/nuclear_deterrence_values.txt"))
        body = block(values, "nd_hold_chance")
        self.assertIn("exists = scope:nd_hold_suspect", body)
        self.assertEqual(body.count("scope:nd_hold_suspect = {"), 1)
        effects = strip_comments(read(ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"))
        events = strip_comments(read(ROOT / "events/nuclear_incident_events.txt"))
        for text, name in ((effects, "nd_start_unconfirmed_warning"), (effects, "nd_system_reads_attack"),
                           (events, "nuclear_incident.20")):
            self.assertIn("save_scope_as = nd_hold_suspect", block(text, name), name)

    def test_war_exposure_band(self):
        crisis = self.model.number
        band = {b: crisis("nd_incident_crisis_weekly_permille", Posture(readiness=3, danger=25 * b, stage=3 if b == 3 else 2))
                for b in (1, 2, 3)}
        at_war = Posture(readiness=3, war=True, war_band=2)
        self.assertEqual(crisis("nd_incident_crisis_weekly_permille", at_war), band[2])
        self.assertEqual(crisis("nd_incident_crisis_weekly_permille", Posture(readiness=3, war=True, war_band=3)), band[3])
        both = Posture(readiness=3, war=True, war_band=2, danger=25, stage=2)
        self.assertEqual(crisis("nd_incident_crisis_weekly_permille", both), band[2])
        self.assertEqual(crisis("nd_incident_crisis_weekly_permille", Posture(readiness=3, war=True)), 0)

    def test_war_band_triggers(self):
        triggers = strip_comments(read(ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"))
        body = block(triggers, "nd_war_band_3_against_any")
        for needle in ("any_enemy_in_war", "nd_believed_armed = yes", "nd_core_threatened_by",
                       "nd_is_losing_war_to", "nuclear_strike_aftermath", "tactical_nuke_aftermath"):
            self.assertIn(needle, body)


if __name__ == "__main__":
    unittest.main()
