"""The nuclear taboo: the tables and single-writer rules that must agree.

The taboo (docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md) is one
world score moved by a monthly step and by writers scattered across the
nuclear files. Nothing in the engine checks that the parts the step snapshots
are the parts the target sums, that only the writers touch the score, or that
every path that gives an arsenal up books the renunciation once. Each test
pins one of those rules.

Run: python3 -m unittest test_nuclear_taboo -v
"""

import re
import sys
import unittest
from pathlib import Path

from test_nuclear_deterrence import block, loc_keys, loc_value, read, sgui_ops, strip_comments

ROOT = Path(__file__).resolve().parent
TABOO_VALUES = ROOT / "common/script_values/nuclear_taboo_values.txt"
TABOO_EFFECTS = ROOT / "common/scripted_effects/nuclear_taboo_effects.txt"
TABOO_TRIGGERS = ROOT / "common/scripted_triggers/nuclear_taboo_triggers.txt"
TABOO_ON_ACTIONS = ROOT / "common/on_actions/nuclear_taboo_on_actions.txt"
WEAPON_EFFECTS = ROOT / "common/scripted_effects/nuclear_weapon_effects.txt"
JE = ROOT / "common/journal_entries/je_nuclear_program.txt"

# The target's parts, in the order nd_taboo_target_sum adds them.
PARTS = ["base", "tradition", "postures", "restraint", "ledger"]
NEW_FILES = [TABOO_VALUES, TABOO_EFFECTS, TABOO_TRIGGERS, TABOO_ON_ACTIONS]


def script_files():
    for folder in ("common", "events"):
        yield from (ROOT / folder).rglob("*.txt")


class TestScoreCore(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(TABOO_VALUES))
        self.effects = strip_comments(read(TABOO_EFFECTS))
        self.on_actions = strip_comments(read(TABOO_ON_ACTIONS))

    def test_new_files_start_with_a_bom(self):
        for path in NEW_FILES:
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"), path.name)

    def test_snapshot_writes_every_part(self):
        body = block(self.effects, "nd_taboo_snapshot")
        for part in PARTS:
            self.assertIn(f"name = nd_tb_{part} value", body, part)
        self.assertIn("name = nd_taboo_target value = nd_taboo_target_sum", body)

    def test_target_sums_exactly_the_parts(self):
        body = block(self.values, "nd_taboo_target_sum")
        self.assertEqual(re.findall(r"(?:value|add) = global_var:nd_tb_(\w+)", body), PARTS)
        self.assertIn("min = 0", body)
        self.assertIn("max = 100", body)

    def test_drift_alone_tops_out_at_55(self):
        base = float(re.search(r"(?m)^nd_taboo_base = ([\d.]+)", self.values).group(1))
        cap = float(re.search(r"(?m)^nd_taboo_tradition_cap = ([\d.]+)", self.values).group(1))
        self.assertEqual(base + cap, 55)

    def test_only_the_writers_touch_the_score(self):
        writes = re.compile(r"name = (?:nd_taboo|nd_taboo_ledger|nd_taboo_quiet_years|nd_tb_\w+)\b"
                            r"(?= (?:value|add|subtract|multiply))")
        for path in script_files():
            if path == TABOO_EFFECTS:
                continue
            text = strip_comments(read(path))
            self.assertNotRegex(text, writes, path.relative_to(ROOT).as_posix())

    def test_every_writer_waits_for_the_birth(self):
        for name in ("nd_taboo_ledger_add", "nd_taboo_ledger_add_weighted", "nd_taboo_shock"):
            body = block(self.effects, name)
            self.assertIn("has_global_variable = nd_taboo", body, name)

    def test_world_step_runs_from_the_global_pulse_under_the_rule(self):
        pulse = block(self.on_actions, "on_monthly_pulse")
        self.assertIn("nd_taboo_monthly_on_action", pulse)
        body = block(self.on_actions, "nd_taboo_monthly_on_action")
        self.assertIn("has_game_rule = nuclear_weapons_enabled", body)
        self.assertIn("nd_taboo_monthly_update = yes", body)
        self.assertNotIn("un_founded", self.on_actions)

    def test_world_step_applies_no_rooted_modifier(self):
        body = block(self.effects, "nd_taboo_monthly_update")
        self.assertNotIn("add_modifier", body)
        self.assertNotIn("root.var", body)

    def test_birth_is_called_at_the_first_warhead(self):
        text = strip_comments(read(WEAPON_EFFECTS))
        i = text.index("set_global_variable = { name = world_first_nuclear_weapon value = yes }")
        self.assertIn("nd_taboo_birth = yes", text[i:i + 200])

    def test_existing_world_is_seeded_from_the_first_device(self):
        body = block(self.effects, "nd_taboo_seed_existing_world")
        self.assertIn("has_global_variable = world_first_nuclear_weapon", body)
        self.assertIn("world_first_nuclear_weapon_used", body)
        self.assertIn("var:nuclear_program_first_device_year", body)
        self.assertIn("name = nd_taboo value = global_var:nd_taboo_target", body)
        update = block(self.effects, "nd_taboo_monthly_update")
        self.assertLess(update.index("nd_taboo_seed_existing_world = yes"), update.index("nd_taboo_snapshot = yes"))

    def test_leaderboard_runs_once_for_the_world(self):
        self.assertNotIn("update_nuclear_powers_ranking", strip_comments(read(JE)))
        self.assertIn("update_nuclear_powers_ranking = yes", block(self.effects, "nd_taboo_monthly_update"))

    def test_new_loc_family_is_filed_whole(self):
        sys.path.insert(0, str(ROOT))
        import organize_loc
        for key in ("nd_taboo_possession_cost", "nd_taboo_possession_cost_desc",
                    "nd_taboo_resume_programme_desc", "nd_taboo_tt_opt_cut", "nd_taboo_bd_ledger"):
            self.assertEqual(organize_loc.categorize_key(key, set()), "MISCELLANEOUS", key)


sys.path.insert(0, str(ROOT / "scripts" / "analysis"))


class TestSimulator(unittest.TestCase):
    def setUp(self):
        import nuclear_taboo_sim as sim
        self.sim = sim
        self.c = sim.load_constants(TABOO_VALUES)

    def test_constants_come_from_the_script_file(self):
        for name in ("nd_taboo_base", "nd_taboo_tradition_cap", "nd_taboo_approach_months",
                     "nd_taboo_ledger_decay", "nd_taboo_shock_strategic", "nd_taboo_ledger_strategic",
                     "nd_taboo_clock_keep_first_use", "nd_taboo_band_hysteresis"):
            self.assertIn(name, self.c, name)

    def test_quiet_world_plateaus_at_55(self):
        series = self.sim.simulate(self.sim.SCENARIOS["quiet"], self.c, years=100)
        score, target = series[-1]
        self.assertAlmostEqual(target, 55, delta=0.01)
        self.assertAlmostEqual(score, 55, delta=0.5)

    def test_one_use_roughly_halves_a_mature_taboo(self):
        series = self.sim.simulate(self.sim.SCENARIOS["use_year_40"], self.c, years=41)
        before = series[40 * 12 - 1][1]
        after = series[40 * 12 + 1][1]
        self.assertGreater(before - after, 20)
        self.assertLess(before - after, 35)

    def test_seeded_quiet_world_starts_near_its_target(self):
        scenario = self.sim.SCENARIOS["seeded_40_years"]
        score, target = self.sim.simulate(scenario, self.c, years=1)[0]
        self.assertAlmostEqual(score, target, delta=1.1)
        self.assertGreater(score, 50)

    def test_band_events_do_not_flap(self):
        flapping = [50 + (1 if m % 2 else -1) for m in range(240)]
        events = self.sim.band_events(flapping, self.c, cooldown_months=120)
        self.assertLessEqual(len(events), 1)


EXTRA_EFFECTS = ROOT / "common/scripted_effects/extra_effects.txt"
DETERRENCE_EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
CRISIS_EFFECTS = ROOT / "common/scripted_effects/nuclear_crisis_effects.txt"
LOOSE_EFFECTS = ROOT / "common/scripted_effects/nuclear_loose_effects.txt"


class TestActs(unittest.TestCase):
    def setUp(self):
        self.taboo = strip_comments(read(TABOO_EFFECTS))
        self.extra = strip_comments(read(EXTRA_EFFECTS))
        self.det = strip_comments(read(DETERRENCE_EFFECTS))
        self.crisis = strip_comments(read(CRISIS_EFFECTS))
        self.loose = strip_comments(read(LOOSE_EFFECTS))

    def test_note_use_scales_and_cuts_the_clock(self):
        body = block(self.taboo, "nd_taboo_note_use")
        for needle in ("value = nd_taboo_shock_$KIND$", "value = nd_taboo_ledger_$KIND$",
                       "always = $RETALIATION$", "multiply = nd_taboo_clock_keep_retaliation",
                       "multiply = nd_taboo_clock_keep_first_use",
                       "nd_taboo_shock = { POINTS = global_var:nd_tb_use_shock }",
                       "nd_taboo_ledger_add = { POINTS = global_var:nd_tb_use_ledger }",
                       "name = nd_taboo_last_use_year value = year"):
            self.assertIn(needle, body)

    def test_response_strikes_are_retaliation_by_construction(self):
        for name in ("nuclear_response_strike", "nuclear_response_response_strike"):
            body = block(self.extra, name)
            self.assertIn("nd_taboo_note_use = { KIND = strategic RETALIATION = yes }", body, name)
            self.assertNotIn("RETALIATION = no", body, name)
            self.assertNotIn("nd_was_struck_by", body, name)

    def test_first_strikes_ask_whether_they_answer_a_strike(self):
        for text, name, kind in ((self.extra, "nuclear_first_strike", "strategic"),
                                 (self.det, "nd_tactical_strike_resolve", "tactical")):
            body = block(text, name)
            self.assertIn("nd_was_struck_by = { ENEMY = scope:target_country }", body, name)
            self.assertIn(f"nd_taboo_note_use = {{ KIND = {kind} RETALIATION = yes }}", body, name)
            self.assertIn(f"nd_taboo_note_use = {{ KIND = {kind} RETALIATION = no }}", body, name)

    def test_dispatch_is_always_at_war(self):
        # nd_was_struck_by opens with has_war_with; every detonation site is
        # reached inside a war, or the retaliation branch could never be taken.
        for name in ("nd_dispatch_strategic_strike", "nd_dispatch_tactical_strike"):
            self.assertIn("has_war_with = scope:nd_strike_victim", block(self.det, name), name)

    def test_terror_is_not_a_use(self):
        self.assertIn("nd_taboo_ledger_add = { POINTS = nd_taboo_ledger_terror }", self.loose)
        self.assertNotIn("nd_taboo_note_use", self.loose)

    def test_threats_wear_it_down(self):
        body = block(self.crisis, "nd_crisis_open")
        self.assertIn("nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_ultimatum }", body)
        self.assertIn("nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_warning }", body)
        self.assertIn("nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_go_public }",
                      block(self.crisis, "nd_crisis_act_go_public"))

    def test_doctrine_credit_is_the_governments_not_the_laws(self):
        weekly = block(self.det, "nd_weekly_update")
        self.assertIn("nd_bind_doctrine_1 = yes", weekly)
        self.assertNotIn("nd_set_doctrine_1 = yes", weekly)
        shared = "nd_set_doctrine = { D = 1 OFFENSIVE = no LEAVES_NFU = no }"
        self.assertIn(shared, block(self.det, "nd_set_doctrine_1"))
        self.assertIn(shared, block(self.det, "nd_bind_doctrine_1"))
        self.assertIn("POINTS = nd_taboo_ledger_nfu", block(self.det, "nd_set_doctrine_1"))
        self.assertNotIn("nd_taboo_ledger", block(self.det, "nd_bind_doctrine_1"))
        self.assertIn("POINTS = nd_taboo_ledger_offensive_doctrine", block(self.det, "nd_set_doctrine"))
        self.assertIn("POINTS = nd_taboo_ledger_repudiation", block(self.det, "nd_break_pledge_effects"))

    def test_reciprocal_standdown_strengthens_it(self):
        body = block(self.crisis, "nd_crisis_close")
        self.assertIn("var:nd_crisis_outcome_now = 3", body)
        self.assertIn("nd_taboo_ledger_add = { POINTS = nd_taboo_ledger_standdown }", body)

    def test_every_ledger_constant_is_defined(self):
        values = strip_comments(read(TABOO_VALUES))
        used = set()
        for path in script_files():
            used |= set(re.findall(r"POINTS = (nd_taboo_\w+)", strip_comments(read(path))))
        self.assertTrue(used)
        for name in used:
            self.assertRegex(values, rf"(?m)^{name} = ", name)


NUKE_ACTIONS = ROOT / "common/diplomatic_actions/nuke.txt"
DETERRENCE_VALUES = ROOT / "common/script_values/nuclear_deterrence_values.txt"


def constant(text, name):
    return float(re.search(rf"(?m)^{name} = (-?[\d.]+)", text).group(1))


class TestCosts(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(TABOO_VALUES))
        self.extra = strip_comments(read(EXTRA_EFFECTS))
        self.det = strip_comments(read(DETERRENCE_EFFECTS))
        self.crisis = strip_comments(read(CRISIS_EFFECTS))

    def test_old_costs_are_the_value_at_taboo_25(self):
        self.assertEqual(25 * constant(self.values, "nd_taboo_infamy_strategic_per_point"), 25)
        self.assertEqual(25 * constant(self.values, "nd_taboo_infamy_tactical_per_point"), 10)
        self.assertAlmostEqual(50 * constant(self.values, "nd_taboo_infamy_threat_per_point"), 5)

    def test_first_use_pays_before_the_taboo_falls(self):
        for text, name, kind in ((self.extra, "nuclear_first_strike", "strategic"),
                                 (self.det, "nd_tactical_strike_resolve", "tactical")):
            body = block(text, name)
            self.assertNotRegex(body, r"change_infamy = (25|10)\b", name)
            pay = body.index(f"change_infamy = nd_taboo_infamy_{kind}")
            relations = body.index(f"value = nd_taboo_world_relations_{kind}")
            shock = body.index(f"nd_taboo_note_use = {{ KIND = {kind} RETALIATION = no }}")
            self.assertLess(pay, shock, name)
            self.assertLess(relations, shock, name)
            answer = body.index(f"nd_taboo_note_use = {{ KIND = {kind} RETALIATION = yes }}")
            self.assertNotIn("change_infamy", body[answer - 200:answer], name)

    def test_threats_and_doctrines_pay_by_the_taboo(self):
        for text, name in ((self.crisis, "nd_crisis_preview"), (self.crisis, "nd_crisis_act_go_public"),
                           (self.det, "nd_set_doctrine")):
            body = block(text, name)
            self.assertIn("change_infamy = nd_taboo_infamy_threat", body, name)
            self.assertNotIn("change_infamy = 5", body, name)

    def test_strike_confirmations_name_the_cost(self):
        text = strip_comments(read(NUKE_ACTIONS))
        effects = re.findall(r"accept_effect = \{", text)
        self.assertEqual(len(effects), 2)
        self.assertIn("custom_tooltip = nd_taboo_tt_strike_first_use", text)
        self.assertIn("custom_tooltip = nd_taboo_tt_tactical_first_use", text)
        self.assertEqual(text.count("custom_tooltip = nd_taboo_tt_strike_answer"), 2)

    def test_pressure_part_reads_the_taboo(self):
        body = block(strip_comments(read(DETERRENCE_VALUES)), "nd_yp_taboo_value")
        for needle in ("value = nd_taboo_yp_midpoint", "subtract = nd_taboo_value",
                       "multiply = nd_taboo_yp_per_point", "var:nd_crisis_public = 1",
                       "multiply = nd_taboo_yp_public_discount"):
            self.assertIn(needle, body)

    def test_cost_keys_have_loc(self):
        keys = loc_keys()
        for key in ("nd_taboo_tt_strike_first_use", "nd_taboo_tt_tactical_first_use",
                    "nd_taboo_tt_strike_answer", "nd_yp_taboo_line"):
            self.assertIn(key, keys, key)


NUKE_TRIGGERS = ROOT / "common/scripted_triggers/nuke_triggers.txt"
PROGRAM_CUSTOM_LOC = ROOT / "common/customizable_localization/nuclear_program_custom_loc.txt"


def enclosing_block(text, index):
    """Name of the top-level `name = {` block that contains index."""
    names = list(re.finditer(r"(?m)^(\w+) = \{", text[:index]))
    return names[-1].group(1) if names else None


class TestEveryoneActive(unittest.TestCase):
    def setUp(self):
        self.det = strip_comments(read(DETERRENCE_EFFECTS))

    def test_entry_applies_to_everyone_once_the_taboo_exists(self):
        body = block(strip_comments(read(NUKE_TRIGGERS)), "nuclear_program_entry_applies")
        self.assertIn("has_global_variable = nd_taboo", body)
        self.assertIn("NOT = { is_country_type = decentralized }", body)

    def test_unarmed_cleanup_runs_from_the_entrys_own_pulses(self):
        monthly = block(self.det, "nd_monthly_update")
        unarmed = monthly[monthly.index("else = {"):]
        self.assertIn("nd_apply_posture_modifiers = yes", unarmed)
        self.assertIn("nd_clear_domestic_stance = yes", unarmed)
        self.assertIn("remove_modifier = nd_upkeep_cost", block(self.det, "nd_apply_posture_modifiers"))
        weekly = block(strip_comments(read(JE)), "on_weekly_pulse")
        self.assertIn("has_variable = nd_arsenal_record", weekly)
        # A disarmed country now keeps the entry, so its weekly clean-up runs
        # every week: taking off a modifier it no longer has would log each time.
        self.assertRegex(weekly, r"limit = \{ has_modifier = nuclear_power \}\s*remove_modifier = nuclear_power")
        self.assertNotRegex(weekly, r"value = 0\s*\}\s*remove_modifier = nuclear_power")

    def test_nothing_else_waits_for_the_entry_to_close(self):
        # With the entry active for every country, a branch that acts only
        # once the entry is gone never runs for a disarmed country. These are
        # the known ones: the two clean-up fallbacks for a world where the
        # entry never activated (the rule off, before the first warhead), and
        # custody adding a missing entry.
        allowed = {("nuclear_deterrence_effects.txt", "nd_country_monthly_cleanup"),
                   ("nuclear_custody_effects.txt", "nd_custody_after_arrival")}
        found = set()
        for path in (ROOT / "common").rglob("nuclear_*.txt"):
            text = strip_comments(read(path))
            for m in re.finditer(r"NOT = \{ has_journal_entry = je_nuclear_program \}", text):
                found.add((path.name, enclosing_block(text, m.start())))
        self.assertEqual(found, allowed)

    def test_status_line_opens_with_the_taboo(self):
        self.assertTrue(loc_value("je_nuclear_program_status_line").startswith(
            "[ROOT.GetCountry.GetCustom('nd_taboo_status_line')]"))

    def test_status_line_targets_are_accessor_free(self):
        body = block(strip_comments(read(PROGRAM_CUSTOM_LOC)), "nd_taboo_status_line")
        keys = re.findall(r"localization_key = (\w+)", body)
        self.assertEqual(keys, ["nuke_line_empty"] + [f"nd_taboo_status_{n}" for n in range(1, 6)])
        for key in keys[1:]:
            value = loc_value(key)
            for accessor in ("GetCountry", "ROOT", "JournalEntry", "GetPlayer"):
                self.assertNotIn(accessor, value, key)

    def test_band_names_exist(self):
        keys = loc_keys()
        for n in range(1, 6):
            self.assertIn(f"nd_taboo_band_{n}", keys)


TABOO_MODIFIERS = ROOT / "common/static_modifiers/nuclear_taboo_modifiers.txt"
NEW_FILES.append(TABOO_MODIFIERS)


class TestPossession(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(TABOO_VALUES))
        self.effects = strip_comments(read(TABOO_EFFECTS))

    def test_modifier_matches_its_display_constants(self):
        body = block(strip_comments(read(TABOO_MODIFIERS)), "nd_taboo_possession_cost")
        prestige = constant(self.values, "nd_taboo_possession_prestige_pct") / 100
        leverage = constant(self.values, "nd_taboo_possession_leverage_pct") / 100
        self.assertIn(f"country_prestige_mult = {prestige:g}", body)
        self.assertIn(f"country_leverage_generation_mult = {leverage:g}", body)

    def test_burden_is_a_product_zero_below_the_floor(self):
        burden = block(self.values, "nd_taboo_burden_value")
        self.assertIn("value = nd_taboo_factor_value", burden)
        self.assertIn("multiply = nd_taboo_arsenal_factor_value", burden)
        self.assertIn("nd_is_armed = yes", burden)
        factor = block(self.values, "nd_taboo_factor_value")
        self.assertIn("subtract = nd_taboo_burden_floor", factor)
        self.assertIn("min = 0", factor)

    def test_refresh_runs_with_the_country_as_root(self):
        body = block(self.effects, "nd_taboo_refresh_possession")
        self.assertIn("multiplier = root.var:nd_taboo_burden_cached", body)
        self.assertIn("je:je_nuclear_program ?=", body)
        self.assertNotIn("remove_variable = nd_taboo_burden_cached", self.effects)
        self.assertEqual(block(self.effects, "nd_taboo_country_monthly").count("nd_taboo_refresh_possession = yes"), 1)
        self.assertNotIn("nd_taboo_refresh_possession", block(self.effects, "nd_taboo_monthly_update"))
        self.assertIn("nd_taboo_country_monthly = yes", block(strip_comments(read(JE)), "on_monthly_pulse"))

    def test_restraint_groups_weigh_the_arsenal(self):
        dv = strip_comments(read(DETERRENCE_VALUES))
        term = block(dv, "nd_ig_term_possession_value")
        for needle in ("nd_ig_class_restraint = yes", "nd_taboo_burden_value >= nd_taboo_burden_step_full",
                       "nd_taboo_burden_value >= nd_taboo_burden_step_mild"):
            self.assertIn(needle, term)
        self.assertNotIn("nd_ig_posture_judged", term)
        self.assertIn("add = nd_ig_term_possession_value", block(dv, "nd_ig_stance_value"))
        self.assertIn("THIS.Var('nd_ig_term_possession').GetValue", loc_value("nd_home_terms_restraint"))

    def test_modifier_has_loc(self):
        keys = loc_keys()
        self.assertIn("nd_taboo_possession_cost", keys)
        self.assertIn("nd_taboo_possession_cost_desc", keys)


TABOO_EVENTS = ROOT / "events/nuclear_taboo_events.txt"
NEW_FILES.append(TABOO_EVENTS)
DETERRENCE_TRIGGERS = ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"
DETERRENCE_SGUIS = ROOT / "common/scripted_guis/nuclear_deterrence_sguis.txt"
CUSTODY_EFFECTS = ROOT / "common/scripted_effects/nuclear_custody_effects.txt"
TREATY_ARTICLES = ROOT / "common/treaty_articles/extra_treaty_articles.txt"
DECISIONS = ROOT / "common/decisions/extra_decisions.txt"

ZEROING = "name = nuclear_weapon_stockpile value = 0"


class TestExits(unittest.TestCase):
    def setUp(self):
        self.taboo = strip_comments(read(TABOO_EFFECTS))
        self.triggers = strip_comments(read(TABOO_TRIGGERS))
        self.custody = strip_comments(read(CUSTODY_EFFECTS))
        self.det = strip_comments(read(DETERRENCE_EFFECTS))

    def test_renunciation_is_idempotent_and_read_before_zeroing(self):
        body = block(self.taboo, "nd_taboo_note_renunciation")
        self.assertRegex(body, r"NOT = \{\s*AND = \{\s*has_variable = nd_renounced\s*nd_is_armed = no\s*\}\s*\}")
        self.assertIn("$WARHEADS$ > 0", body)
        self.assertIn("name = nd_renounced value = year", body)
        call = "nd_taboo_note_renunciation = { WARHEADS = nd_stockpile }"
        for name in ("nd_bp_accept", "nd_cw_dismantle_as"):
            b = block(self.custody, name)
            self.assertLess(b.index(call), b.index(ZEROING), name)
        on_entry = block(block(strip_comments(read(TREATY_ARTICLES)), "nuclear_disarmament"), "on_entry_into_force")
        self.assertLess(on_entry.index(call), on_entry.index(ZEROING))
        complete = block(self.taboo, "nd_taboo_dismantle_complete")
        self.assertLess(complete.index("nd_taboo_note_renunciation = { WARHEADS = var:nd_dismantle_start_stock }"),
                        complete.index(ZEROING))

    def test_every_ceiling_change_refreshes_the_hold(self):
        for name in ("nd_taboo_ceiling_lower", "nd_taboo_ceiling_raise", "nd_taboo_ceiling_lift",
                     "nd_taboo_dismantle_start", "nd_taboo_dismantle_halt"):
            self.assertIn("nd_taboo_refresh_held = yes", block(self.taboo, name), name)
        refresh = block(self.taboo, "nd_taboo_refresh_held")
        self.assertIn("nd_taboo_programme_should_be_held = yes", refresh)
        self.assertIn("remove_modifier = nd_taboo_programme_held", refresh)
        monthly = block(self.taboo, "nd_taboo_country_monthly")
        self.assertEqual(monthly.count("nd_taboo_refresh_held = yes"), 1)
        self.assertNotIn("nd_taboo_refresh_held", block(self.taboo, "nd_taboo_dismantle_complete"))
        self.assertNotIn("nd_taboo_refresh_possession", block(self.taboo, "nd_taboo_dismantle_complete"))

    def test_exits_go_through_the_custody_ledger(self):
        for name in ("nd_taboo_dismantle_step", "nd_taboo_retire_step", "nd_taboo_dismantle_complete"):
            body = block(self.taboo, name)
            self.assertIn("nd_ledger_refresh = yes", body, name)
            self.assertNotIn("loose", body, name)

    def test_panel_ops(self):
        sguis = strip_comments(read(DETERRENCE_SGUIS))
        for part in ("is_valid", "effect"):
            ops = sgui_ops(sguis, "nd_posture_sgui", part)
            for op in range(60, 65):
                self.assertIn(op, ops, f"{part} lacks op {op}")

    def test_readiness_stays_in_storage_while_dismantling(self):
        gate = block(strip_comments(read(DETERRENCE_TRIGGERS)), "nd_can_set_readiness")
        self.assertRegex(gate, r"OR = \{\s*nd_taboo_is_dismantling = no\s*var:nd_readiness_target > \$R\$\s*\}")
        self.assertIn("nd_taboo_is_dismantling = yes", block(self.det, "nd_weekly_update"))

    def test_renounced_state_is_rebuilt_from_its_variable(self):
        monthly = block(self.taboo, "nd_taboo_country_monthly")
        self.assertIn("has_variable = nd_renounced_locked", monthly)
        self.assertIn("add_modifier = { name = nd_taboo_renounced }", monthly)
        mods = strip_comments(read(TABOO_MODIFIERS))
        self.assertIn("country_nuclear_disarmament_bool = yes", block(mods, "nd_taboo_renounced"))
        self.assertIn("country_nuclear_program_pause_bool = yes", block(mods, "nd_taboo_programme_held"))

    def test_breakout_is_booked_once(self):
        monthly = block(self.taboo, "nd_taboo_country_monthly")
        self.assertIn("POINTS = nd_taboo_ledger_breakout", monthly)
        self.assertIn("remove_variable = nd_renounced", monthly)

    def test_resume_decision(self):
        body = block(strip_comments(read(DECISIONS)), "nd_taboo_resume_programme")
        self.assertIn("has_modifier = nd_taboo_renounced", body)
        self.assertIn("nd_taboo_resume = yes", body)
        self.assertIn("nd_taboo_ai_would_resume = yes", body)

    def test_programme_status_reports_the_hold(self):
        body = block(strip_comments(read(WEAPON_EFFECTS)), "nuclear_program_refresh_state_effect")
        five = body.index("name = nuclear_program_last_status value = 5")
        four = body.index("name = nuclear_program_last_status value = 4")
        three = body.index("name = nuclear_program_last_status value = 3")
        self.assertLess(five, four)
        self.assertLess(four, three)

    def test_last_warhead_event(self):
        events = strip_comments(read(TABOO_EVENTS))
        body = block(events, "nuclear_taboo.20")
        self.assertIn("nd_taboo_renunciation_rewards = yes", body)
        self.assertIn("name = nd_taboo_renounce_mult value = nd_taboo_renounce_mult_value", block(body, "immediate"))
        self.assertIn("trigger_event = { id = nuclear_taboo.20 }", block(self.taboo, "nd_taboo_dismantle_complete"))

    def test_exit_keys_have_loc(self):
        keys = loc_keys()
        for key in ("nd_taboo_renounced", "nd_taboo_renounced_desc", "nd_taboo_programme_held",
                    "nd_taboo_programme_held_desc", "nd_taboo_renunciation_prestige",
                    "nd_taboo_renunciation_prestige_desc", "nd_taboo_resume_programme",
                    "nd_taboo_resume_programme_desc", "nuclear_taboo.20.t", "nuclear_taboo.20.d",
                    "nuclear_taboo.20.f", "nuclear_taboo.20.a", "nuclear_program_status_held",
                    "nuclear_program_status_dismantling", "nuclear_program_rate_note_held"):
            self.assertIn(key, keys, key)
        for text in (read(TABOO_EFFECTS), read(TABOO_TRIGGERS)):
            for key in re.findall(r"text = (nd_taboo_tt_\w+)", text):
                self.assertIn(key, keys, key)

    def test_dismantling_runs_its_full_length(self):
        values = strip_comments(read(TABOO_VALUES))
        this_month = block(values, "nd_taboo_dismantle_this_month_value")
        self.assertIn("divide = var:nd_dismantle_months_left", this_month)
        self.assertIn("floor = yes", this_month)
        self.assertNotRegex(values, r"(?m)^nd_taboo_dismantle_per_month_value = ")
        step = block(self.taboo, "nd_taboo_dismantle_step")
        complete_at = step.index("nd_taboo_dismantle_complete = yes")
        guard = step[step.rfind("limit", 0, complete_at):complete_at]
        self.assertIn("var:nd_dismantle_months_left <= 0", guard)
        self.assertNotIn("nd_stockpile", guard)
        leftover = re.compile(r"(?<![\w])nd_dismantle_per_month\b")
        for path in script_files():
            self.assertNotRegex(strip_comments(read(path)), leftover, path.name)


if __name__ == "__main__":
    unittest.main()
