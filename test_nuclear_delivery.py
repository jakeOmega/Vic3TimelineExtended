"""Delivery legs (2026-11-20 delivery spec §4; phase 1 plan Task 1, D2 and D3).

Two country triggers stand for the hardware: nd_fields_icbms and
nd_fields_missile_submarines. In phase 1 they read the technologies, and the
submarine leg also needs a coastal state to sail from. Phase 2 swaps their
bodies for the fielded variables and touches nothing else. So every read of
the two technologies is a delivery read and goes through the triggers, unless
it is about knowledge rather than hardware, which ALLOWED lists with its
reason."""

import math
import re
import unittest

from scripts.analysis.nuclear_incident_rates import Posture, RiskModel
from scripts.analysis.nuclear_survivors import accuracy_mult, exposed, survivability_target
from test_nuclear_deterrence import ROOT, block, read, squash, strip_comments

TRIGGERS = ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"
VALUES = ROOT / "common/script_values/nuclear_deterrence_values.txt"
EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
INCIDENT_EVENTS = ROOT / "events/nuclear_incident_events.txt"
EXTRA_CUSTOM_LOC = ROOT / "common/customizable_localization/zzz_extra_custom_loc.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/nuclear_deterrence_custom_loc.txt"
LOC = ROOT / "localization/english"
EXTRA_VALUES = ROOT / "common/script_values/extra_script_values.txt"
MODIFIER_TYPES = ROOT / "common/modifier_type_definitions/nuclear_program_modifier_types.txt"
STATICS = ROOT / "common/static_modifiers/nuclear_deterrence_modifiers.txt"
JOURNAL = ROOT / "common/journal_entries/je_nuclear_program.txt"
TECH = ROOT / "common/technology/technologies"
PLAYTEST = ROOT / "docs/testing/nuclear-playtest.md"


def constant(text, name):
    """A top-level `name = <number>` script value."""
    m = re.search(r"(?m)^" + re.escape(name) + r"\s*=\s*(-?[\d.]+)\s*$", text)
    if not m:
        raise AssertionError(f"{name} not found")
    return float(m.group(1))


def figure(body, field):
    m = re.search(r"\b" + re.escape(field) + r"\s*=\s*(-?[\d.]+)", body)
    if not m:
        raise AssertionError(f"{field} not found")
    return float(m.group(1))

TECH_READ = re.compile(r"\bhas_technology_researched\s*=\s*(ICBMs|advanced_submarine_technology)\b")
TOP_LEVEL = re.compile(r"^([A-Za-z_][\w:]*)\s*=\s*\{", re.M)

# (file, top-level block) -> why it reads the technology itself. A whole file
# is listed under block None.
ALLOWED = {
    ("common/scripted_triggers/nuclear_deterrence_triggers.txt", "nd_fields_icbms"):
        "the trigger itself",
    ("common/scripted_triggers/nuclear_deterrence_triggers.txt", "nd_fields_missile_submarines"):
        "the trigger itself",
    ("common/scripted_triggers/nuclear_taboo_triggers.txt", "nd_taboo_has_programme_standing"):
        "a Major Power's standing to run a programme comes from the technology: a project can't "
        "stand in for it, since only a country with a programme can run one (spec §4.2)",
    ("common/script_values/extra_script_values.txt", "global_tech_spread_script_value"):
        "the world's technology spread counts research",
    ("common/script_values/te_ai_probe_values.txt", "te_aip_tc_military_7"):
        "the AI probe counts researched technologies",
    ("common/ship_types/extra_ship_types.txt", "INJECT:ship_type_submarine"):
        "the old submarine's obsolescence is about the ship, not the missile",
    ("common/ai_strategies/edited_default_strategy.txt", "INJECT:ai_strategy_default"):
        "the naval AI's supply stance is about the ship, not the missile",
    ("common/scripted_effects/covert_tech_theft_generated.txt", None):
        "generated: covert theft grants the technology (scripts/generators)",
    ("common/scripted_triggers/covert_tech_theft_generated.txt", None):
        "generated: covert theft grants the technology (scripts/generators)",
    ("common/scripted_effects/te_research_commons_sync_generated.txt", None):
        "generated: the research commons shares the technology",
}


def tech_reads():
    """Every read of the two technologies in common/, events/ and gui/, as
    (repo path, line, enclosing top-level block)."""
    for top in ("common", "events", "gui"):
        for path in sorted((ROOT / top).rglob("*")):
            if path.suffix not in (".txt", ".gui"):
                continue
            text = read(path).lstrip("﻿")
            code = strip_comments(text)
            if not TECH_READ.search(code):
                continue
            heads = [(m.start(), m.group(1)) for m in TOP_LEVEL.finditer(code)]
            rel = path.relative_to(ROOT).as_posix()
            for m in TECH_READ.finditer(code):
                owner = None
                for start, name in heads:
                    if start > m.start():
                        break
                    owner = name
                yield rel, code.count("\n", 0, m.start()) + 1, owner


class TestDeliveryTriggers(unittest.TestCase):

    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))

    def test_icbm_trigger(self):
        body = squash(block(self.triggers, "nd_fields_icbms"))
        self.assertIn("custom_tooltip = { text = nd_tt_fields_icbms has_technology_researched = ICBMs }", body)

    def test_submarine_trigger_needs_a_coast(self):
        body = squash(block(self.triggers, "nd_fields_missile_submarines"))
        self.assertIn("custom_tooltip = { text = nd_tt_fields_missile_submarines "
                      "has_technology_researched = advanced_submarine_technology "
                      "any_scope_state = { is_coastal = yes } }", body)

    def test_tooltips_have_loc(self):
        loc = "\n".join(read(p) for p in LOC.glob("*.yml"))
        for key in ("nd_tt_fields_icbms", "nd_tt_fields_missile_submarines"):
            self.assertRegex(loc, rf"(?m)^ {key}:0 \"")


class TestTechnologyReads(unittest.TestCase):
    """Every delivery read goes through the triggers (plan D3)."""

    def test_every_read_is_allowed(self):
        stray = [f"{path}:{line} ({owner})" for path, line, owner in tech_reads()
                 if (path, owner) not in ALLOWED and (path, None) not in ALLOWED]
        self.assertEqual(stray, [], "read nd_fields_icbms / nd_fields_missile_submarines instead, "
                                    "or add the site to ALLOWED with its reason")

    def test_allowlist_is_live(self):
        found = {(path, owner) for path, _, owner in tech_reads()} | {(path, None) for path, _, _ in tech_reads()}
        self.assertEqual([key for key in ALLOWED if key not in found], [], "an allowed site no longer reads it")


class TestIcbmReaders(unittest.TestCase):

    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))
        self.values = strip_comments(read(VALUES))

    def test_reach(self):
        self.assertIn("$COUNTRY$ = { nd_fields_icbms = yes }", squash(block(self.triggers, "nd_state_in_reach_of")))
        self.assertIn("OR = { nd_fields_icbms = yes", squash(block(self.triggers, "nd_reaches_country")))
        self.assertIn("NOT = { nd_fields_icbms = yes }", squash(block(self.triggers, "nd_reach_limited")))
        refresh = squash(block(strip_comments(read(EFFECTS)), "nd_reach_refresh"))
        self.assertIn("nd_is_armed = yes NOT = { nd_fields_icbms = yes }", refresh)

    def test_launch_authorities(self):
        for name in ("nd_can_adopt_launch_on_warning", "nd_can_adopt_automatic_retaliation"):
            self.assertIn("nd_fields_icbms = yes", squash(block(self.triggers, name)), name)

    def test_values(self):
        self.assertIn("limit = { nd_fields_icbms = yes } value = 0.70", squash(block(self.values, "nd_exposure_factor_icbms")))
        # The counterforce ratio's +0.5 comes through the declared force (Task 3).
        self.assertIn("limit = { nd_fields_icbms = yes } value = 1", squash(block(self.values, "nd_icbm_force_value")))

    def test_incidents_and_the_attack_line(self):
        events = squash(strip_comments(read(INCIDENT_EVENTS)))
        self.assertIn("limit = { nd_fields_icbms = yes } set_variable = { name = nd_ic_unit value = 3 }", events)
        self.assertIn("limit = { nd_fields_icbms = yes } add = 20 } } set_variable = { name = nd_accident_kind value = 2 }",
                      events)
        attack = squash(block(strip_comments(read(EXTRA_CUSTOM_LOC)), "te_nuke_attack_icbms"))
        self.assertIn("trigger = { nd_fields_icbms = yes } localization_key = nuke_attack_line_icbms", attack)


class TestSubmarineReaders(unittest.TestCase):
    """A landlocked country has no submarine reach, factor or incident unit."""

    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))

    def test_reach(self):
        state = squash(block(self.triggers, "nd_state_in_reach_of"))
        self.assertIn("AND = { is_coastal = yes $COUNTRY$ = { nd_fields_missile_submarines = yes } }", state)
        country = squash(block(self.triggers, "nd_reaches_country"))
        self.assertIn("AND = { nd_fields_missile_submarines = yes $TARGET$ = { any_scope_state = { is_coastal = yes } } }",
                      country)

    def test_survivability_incident_and_reach_row(self):
        factor = squash(block(strip_comments(read(VALUES)), "nd_exposure_factor_submarines"))
        self.assertIn("limit = { nd_fields_missile_submarines = yes } value = 0.50", factor)
        events = squash(strip_comments(read(INCIDENT_EVENTS)))
        self.assertIn("limit = { nd_fields_missile_submarines = yes } set_variable = { name = nd_ic_unit value = 1 }",
                      events)
        reach = squash(block(strip_comments(read(CUSTOM_LOC)), "nd_reach_value"))
        self.assertIn("trigger = { nd_fields_missile_submarines = yes } localization_key = nd_w_reach_value_subs", reach)


class TestPrecisionWeapons(unittest.TestCase):
    """Precision weapons and the ICBM force (spec §3.4, §4.2; owner calls 1, 7
    and 10; plan D5 to D7)."""

    # Every exposure value that compares us with an enemy, and its scope.
    VS_EXPOSURE = {
        "nd_exposed_warheads_vs_saved": "saved",
        "nd_exposed_warheads_r2_vs_saved": "saved",
        "nd_exposed_warheads_target_r2_vs_saved": "saved",
        "nd_exposed_warheads_vs_issuer": "issuer",
        "nd_exposed_warheads_vs_target": "target",
    }
    SCOPES = {"saved": "scope:nd_sv_enemy", "issuer": "scope:nd_issuer", "target": "scope:nd_target"}

    @classmethod
    def setUpClass(cls):
        cls.values = strip_comments(read(VALUES))
        cls.extra = strip_comments(read(EXTRA_VALUES))
        cls.triggers = strip_comments(read(TRIGGERS))
        cls.pgm = squash(block(strip_comments(read(TECH / "era_8.txt")), "precision_guided_munitions"))
        cls.force = squash(block(strip_comments(read(STATICS)), "nd_icbm_force"))
        cls.model = RiskModel()

    def test_two_script_read_number_types(self):
        types = strip_comments(read(MODIFIER_TYPES))
        k = squash(block(types, "country_nd_k_ratio_add"))
        penetration = squash(block(types, "country_nd_silo_penetration_add"))
        for body in (k, penetration):
            self.assertIn("script_only = yes", body)
            self.assertNotIn("boolean", body)
        self.assertIn("decimals = 1", k)
        self.assertIn("percent = yes", penetration)

    def test_k_ratio_is_one_and_the_modifier(self):
        body = squash(block(self.values, "nd_k_ratio"))
        self.assertTrue(body.startswith("value = 1 add = modifier:country_nd_k_ratio_add"), body)
        self.assertNotIn("has_technology_researched", body)

    def test_technologies(self):
        self.assertEqual(figure(self.pgm, "country_nd_k_ratio_add"), 0.5)
        self.assertEqual(figure(self.pgm, "country_nd_silo_penetration_add"), 0.15)
        icbms = squash(block(strip_comments(read(TECH / "era_7.txt")), "ICBMs"))
        self.assertNotIn("country_nuclear_weapon_attack_success_add", icbms)

    def test_force_and_its_declaration(self):
        self.assertEqual(figure(self.force, "country_nuclear_weapon_attack_success_add"),
                         constant(self.values, "nd_icbm_force_attack_success"))
        self.assertEqual(figure(self.force, "country_nd_k_ratio_add"), constant(self.values, "nd_icbm_force_k_ratio"))
        self.assertEqual(constant(self.values, "nd_icbm_force_k_ratio"), 0.5)
        self.assertEqual(constant(self.values, "nd_icbm_force_attack_success"), 0.5)
        journal = squash(strip_comments(read(JOURNAL)))
        self.assertIn("scaling_modifiers_while_active = { modifier = nd_icbm_force "
                      "value = { value = nd_icbm_force_value } }", journal)
        self.assertEqual(squash(block(self.values, "nd_icbm_force_value")),
                         "value = 0 if = { limit = { nd_fields_icbms = yes } value = 1 }")

    def test_fallback_is_one_switch(self):
        self.assertEqual(squash(block(self.triggers, "nd_icbm_force_declared_reads")), "always = yes")
        guard = "if = { limit = { NOT = { nd_icbm_force_declared_reads = yes } nd_fields_icbms = yes } add = %s }"
        for text, name, value in ((self.values, "nd_k_ratio", "nd_icbm_force_k_ratio"),
                                  (self.extra, "nuclear_strike_attack_rating", "nd_icbm_force_attack_success"),
                                  (self.extra, "nuclear_program_display_attack_rating", "nd_icbm_force_attack_success")):
            self.assertIn(guard % value, squash(block(text, name)), name)

    def test_every_vs_exposure_takes_its_enemys_accuracy(self):
        found = set(re.findall(r"(?m)^(nd_exposed_warheads\w*_vs_\w+)\s*=\s*\{", self.values))
        self.assertEqual(found, set(self.VS_EXPOSURE), "a new _vs_ exposure value needs its accuracy factor")
        for name, scope in self.VS_EXPOSURE.items():
            body = squash(block(self.values, name))
            penalty = body.index(f"subtract = nd_warning_penalty_{scope}")
            accuracy = body.index(f"divide = 100 multiply = nd_accuracy_mult_{scope} max = 1 multiply = nd_stockpile")
            self.assertLess(penalty, accuracy, name)

    def test_accuracy_factor_per_enemy(self):
        for scope, saved in self.SCOPES.items():
            body = squash(block(self.values, f"nd_accuracy_mult_{scope}"))
            self.assertEqual(body, "value = 1 if = { limit = { nd_fields_icbms = yes "
                                   f"{saved} = {{ modifier:country_nd_silo_penetration_add > 0 }} }} "
                                   f"value = nd_exposure_factor_icbms {saved} = {{ "
                                   "add = modifier:country_nd_silo_penetration_add } "
                                   "divide = nd_exposure_factor_icbms }", scope)

    def test_mirror_gives_the_spec_figures(self):
        # Spec §3.4: a full triad with missile defense goes from 17.9% to
        # 21.7% exposed, a silo force without submarines from 35.7% to 43.4%.
        silo = accuracy_mult(figure(self.pgm, "country_nd_silo_penetration_add"))
        for kwargs, before, after in ((dict(), 17.9, 21.7), (dict(submarines=False), 35.7, 43.4)):
            share = 100 - survivability_target(**kwargs)
            self.assertAlmostEqual(share, before, delta=0.06)
            self.assertAlmostEqual(share * silo, after, delta=0.06)
        self.assertEqual(accuracy_mult(0.15, fields_icbms=False), 1)
        self.assertEqual(accuracy_mult(0), 1)

    def test_script_matches_mirror(self):
        target = survivability_target()
        for enemy_pgm in (False, True):
            for icbms in (False, True):
                for survivability in (0, 50, target):
                    enemy = Posture(believed_stockpile=40, icbms=True, pgm=enemy_pgm)
                    p = Posture(readiness=3, authority=1, survivability=survivability, stockpile=10, icbms=icbms,
                                enemy=enemy)
                    accuracy = accuracy_mult(0.15 if enemy_pgm else 0, icbms)
                    case = (enemy_pgm, icbms, survivability)
                    self.assertTrue(math.isclose(self.model.number("nd_accuracy_mult_saved", p), accuracy), case)
                    script = self.model.number("nd_exposed_warheads_vs_saved", p)
                    self.assertTrue(math.isclose(script, exposed(10, survivability, 1.0, accuracy=accuracy)), case)
                    self.assertLessEqual(script, p.stockpile)

    def test_k_ratio_from_its_sources(self):
        k = self.model.number
        self.assertEqual(k("nd_k_ratio", Posture(icbms=False, pgm=False)), 1)
        self.assertEqual(k("nd_k_ratio", Posture(icbms=True, pgm=False)), 1.5)
        self.assertEqual(k("nd_k_ratio", Posture(icbms=False, pgm=True)), 1.5)
        self.assertEqual(k("nd_k_ratio", Posture(icbms=True, pgm=True)), 2)

    def test_loc(self):
        loc = "\n".join(read(p) for p in LOC.glob("*.yml"))
        for key in ("country_nd_k_ratio_add", "country_nd_k_ratio_add_desc", "country_nd_silo_penetration_add",
                    "country_nd_silo_penetration_add_desc", "nd_icbm_force", "nd_icbm_force_desc"):
            self.assertRegex(loc, rf"(?m)^ {key}:0 \"", key)


class TestIcbmForceSelfCheck(unittest.TestCase):
    """TE_SELF_CHECK nd_icbm_force_sum (plan D6): once a game, past the
    declaration's lag, with the scaling_live control named."""

    @classmethod
    def setUpClass(cls):
        cls.raw = block(read(EFFECTS), "nd_icbm_force_selfcheck")
        cls.body = squash(strip_comments(cls.raw))
        cls.values = strip_comments(read(VALUES))

    def test_once_a_game(self):
        self.assertTrue(self.body.startswith("if = { limit = { NOT = { has_global_variable = nd_icbm_force_sum_done } }"))
        self.assertIn("set_global_variable = nd_icbm_force_sum_done", self.body)

    def test_fourteen_days_with_the_inputs_unchanged(self):
        self.assertIn("limit = { nd_fields_icbms = yes has_variable = nd_sc_icbm_pgm "
                      "var:nd_sc_icbm_pgm = nd_sc_icbm_pgm_now } "
                      "change_variable = { name = nd_sc_icbm_weeks add = 1 } } "
                      "else = { set_variable = { name = nd_sc_icbm_weeks value = 0 } }", self.body)
        # Three weekly pulses in a row: at least 14 days since the first.
        self.assertIn("limit = { var:nd_sc_icbm_weeks >= 3 }", self.body)

    def test_no_zero_can_pass(self):
        # The expected counterforce sum starts at the force's figure, above 0.
        self.assertTrue(squash(block(self.values, "nd_sc_icbm_k_expected")).startswith("value = nd_icbm_force_k_ratio"))
        self.assertGreater(constant(self.values, "nd_icbm_force_k_ratio"), 0)
        self.assertIn("nd_sc_icbm_k_gap > -0.01 nd_sc_icbm_k_gap < 0.01 nd_sc_icbm_attack_gap > -0.01", self.body)

    def test_expected_figures_are_the_technologies(self):
        pgm = squash(block(strip_comments(read(TECH / "era_8.txt")), "precision_guided_munitions"))
        expected = squash(block(self.values, "nd_sc_icbm_k_expected"))
        self.assertIn("has_technology_researched = precision_guided_munitions } add = "
                      f"{figure(pgm, 'country_nd_k_ratio_add')}", expected)
        weapons = squash(block(strip_comments(read(TECH / "era_6.txt")), "nuclear_weapons"))
        floor = squash(block(self.values, "nd_sc_icbm_attack_floor"))
        self.assertIn("has_technology_researched = nuclear_weapons } add = "
                      f"{figure(weapons, 'country_nuclear_weapon_attack_success_add'):g}", floor)

    def test_ok_and_broken_lines(self):
        for verdict in ("OK", "BROKEN"):
            line = re.search(r'debug_log = "(TE_SELF_CHECK ' + verdict + r' nd_icbm_force_sum:[^"]*)"', self.raw)
            self.assertIsNotNone(line, verdict)
            self.assertIn("scaling_live", line.group(1))
            for var in ("nd_sc_icbm_k", "nd_sc_icbm_k_expected", "nd_sc_icbm_attack", "nd_sc_icbm_attack_floor"):
                self.assertIn(f"THIS.Var('{var}')", line.group(1))
        self.assertIn("nd_icbm_force_declared_reads", re.search(r'BROKEN nd_icbm_force_sum:[^"]*', self.raw).group(0))

    def test_called_from_the_weekly_pulse_and_listed(self):
        pulse = squash(block(strip_comments(read(JOURNAL)), "on_weekly_pulse"))
        self.assertIn("nd_icbm_force_selfcheck = yes", pulse)
        self.assertIn("nd_icbm_force_sum", read(PLAYTEST))


if __name__ == "__main__":
    unittest.main()
