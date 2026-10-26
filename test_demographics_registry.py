"""Demographics phase 1 wiring (docs/superpowers/archive/plans/2026-10-08-demographics-phases-0-1.md).

Static checks on the script: the rule's settings and wrappers, guarded divisions, the
pulse wiring, the gates around every cohort entry point. Later tasks add tests here.
"""

import copy
import dataclasses
import json
import math
import random
import re
import sys
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import demographics_effects as DE  # noqa: E402
import demographics_model  # noqa: E402
import demographics_modifiers as DM  # noqa: E402
import demographics_params as P  # noqa: E402
import gen_demographics  # noqa: E402
import organize_loc  # noqa: E402

RULES = ROOT / "common" / "game_rules" / "extra_game_rules.txt"
TRIGGERS = ROOT / "common" / "scripted_triggers" / "te_demog_triggers.txt"
EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_effects.txt"
INH_EFFECTS = ROOT / "common" / "scripted_effects" / "te_inheritance_effects.txt"
INH_VALUES = ROOT / "common" / "script_values" / "te_inheritance_values.txt"
DISPLAY_VALUES = ROOT / "common" / "script_values" / "te_demog_display_values.txt"
INH_ON_ACTIONS = ROOT / "common" / "on_actions" / "te_inheritance_on_actions.txt"
DEMOG_ON_ACTIONS = ROOT / "common" / "on_actions" / "te_demog_on_actions.txt"
WEALTH_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_wealth_effects.txt"
GENERATED_VALUES = ROOT / "common" / "script_values" / "te_demog_generated_values.txt"
GENERATED_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_generated_effects.txt"
VALUES = ROOT / "common" / "script_values" / "te_demog_values.txt"
FAST_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_fast_effects.txt"
RATE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_rate_effects.txt"
# the engine's moved birth and mortality lines (the engine-lines plan, 2026-10-11; generated)
LINE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_line_effects_generated.txt"
LINE_VALUES = ROOT / "common" / "script_values" / "te_demog_line_values_generated.txt"
LINE_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_line_modifiers_generated.txt"
PRACTICE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_practice_effects.txt"
# phase 2 step 1's working-adult pair (generated, Task 6)
WORKFORCE_LINE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_workforce_line_effects_generated.txt"
WORKFORCE_LINE_VALUES = ROOT / "common" / "script_values" / "te_demog_workforce_line_values_generated.txt"
WORKFORCE_LINE_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_workforce_line_modifiers_generated.txt"
# phase 3's urban pattern and Planned Capital (te_demog_up_country runs inside the country census)
PLACE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_place_effects.txt"
PLACE_VALUES = ROOT / "common" / "script_values" / "te_demog_place_values.txt"
PLACE_TRIGGERS = ROOT / "common" / "scripted_triggers" / "te_demog_place_triggers.txt"
# phase 2 step 2: the workforce term, the pension setting and the bills
WORK_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_work_effects.txt"
WORK_VALUES = ROOT / "common" / "script_values" / "te_demog_work_values.txt"
DEMOG_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_modifiers.txt"
# phase 2 step 4: conscription, the youth bulge and sex balance (the consequences design §4)
CONSEQ_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_consequence_effects.txt"
CONSEQ_VALUES = ROOT / "common" / "script_values" / "te_demog_consequence_values.txt"
CONSEQ_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_consequence_modifiers.txt"
# phase 3, the late game (docs/superpowers/archive/specs/2026-10-11-demographics-late-game-design.md)
LX_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_lx_effects.txt"
LX_GEN_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_lx_generated_effects.txt"
LX_VALUES = ROOT / "common" / "script_values" / "te_demog_lx_values.txt"
LX_GEN_VALUES = ROOT / "common" / "script_values" / "te_demog_lx_generated_values.txt"
# phase 3: the spreading machinery (the practices' neighbour spread, Family Limitation, Cultural Hegemony's drift)
FL_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_fl_effects.txt"
SPREAD_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_spread_effects_generated.txt"
SPREAD_VALUES = ROOT / "common" / "script_values" / "te_demog_spread_values_generated.txt"
# The shared unemployment conversion (te_state_unemployment_share), which the census stores at its walk (2026-10-17)
UNEMP_VALUES = ROOT / "common" / "script_values" / "te_unemployment_values.txt"
# Internal Resettlement's known moves and the US frontier's 1836 seed (2026-10-19; test_demographics_resettle.py)
RESETTLE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_resettle_effects.txt"
RESETTLE_GEN_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_resettle_generated_effects.txt"
RESETTLE_GEN_VALUES = ROOT / "common" / "script_values" / "te_demog_resettle_generated_values.txt"
# uploaded minds (2026-10-19; docs/superpowers/archive/specs/2026-10-16-demographics-uploaded-minds-design.md)
UM_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_um_effects.txt"
UM_GEN_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_um_generated_effects.txt"
UM_VALUES = ROOT / "common" / "script_values" / "te_demog_um_values.txt"
UM_GEN_VALUES = ROOT / "common" / "script_values" / "te_demog_um_generated_values.txt"
DEMOG_FILES = sorted(p for d in ("common", "events") for p in (ROOT / d).rglob("te_demog*.txt"))


def _text(path):
    return Path(path).read_text(encoding="utf-8-sig")


def _block(text, name):
    """The body of the top-level `name = { ... }`, by brace counting."""
    m = re.search(rf"^{re.escape(name)} = \{{", text, re.M)
    if not m:
        raise AssertionError(f"{name} not found")
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class TestRule(unittest.TestCase):
    def test_three_settings_default_full(self):
        # On by default (owner, 2026-10-25); off from 2026-10-10 while the census was experimental
        body = _block(_text(RULES), "demographics_rule")
        self.assertIn("default = demographics_full", body)
        for setting in ("demographics_full", "demographics_display_only", "demographics_disabled"):
            self.assertIn(f"{setting} = {{", body)

    def test_wrappers_test_positively(self):
        # Positive on purpose, as the tax code's: a save from before the rule existed has
        # no value for it, and NOT = { has_game_rule = demographics_disabled } would start
        # the census in a running campaign.
        text = _text(TRIGGERS)
        cohorts = _block(text, "te_demog_cohorts_run")
        self.assertRegex(cohorts, r"OR = \{\s*has_game_rule = demographics_full\s*has_game_rule = demographics_display_only\s*\}")
        effects = _block(text, "te_demog_effects_run")
        self.assertRegex(effects, r"^\s*has_game_rule = demographics_full\s*$")

    def test_only_the_wrappers_read_the_rule(self):
        for path in [*ROOT.glob("common/**/*.txt"), *ROOT.glob("events/*.txt")]:
            if path == TRIGGERS:
                continue
            self.assertNotRegex(_text(path), r"has_game_rule = demographics_", str(path))
        self.assertNotRegex(_text(TRIGGERS), r"NOT = \{ has_game_rule = demographics_")


class TestDivisions(unittest.TestCase):
    def test_every_division_is_guarded(self):
        """A divide takes a literal or a value block with a floor (Review Focus 2)."""
        for path in DEMOG_FILES:
            text = _text(path)
            for m in re.finditer(r"divide = (\S+)", text):
                arg = m.group(1)
                if re.fullmatch(r"-?\d+(\.\d+)?", arg) or arg.startswith("$"):
                    continue
                self.assertEqual(arg, "{", f"{path.name}: unguarded divide = {arg}")
                body = text[m.end():text.index("}", m.end())]
                self.assertIn("min =", body, f"{path.name}: divide block without min near {m.start()}")


class TestLoc(unittest.TestCase):
    def test_demog_keys_file_together(self):
        for key in ("te_demog_tab", "te_demog_pyramid_tt", "te_demog_wc_desc", "te_demog_label_add"):
            self.assertEqual(organize_loc.categorize_key(key, set()), "MISCELLANEOUS", key)


class TestWalks(unittest.TestCase):
    def test_one_pop_walk_and_one_building_walk(self):
        body = _block(_text(EFFECTS), "te_demog_walks")
        self.assertEqual(body.count("every_scope_pop"), 1)
        self.assertEqual(body.count("every_scope_building"), 1)

    def test_the_walk_expects_each_pops_own_rates(self):
        """Each pop's curves x its own multiplier, floored per pop; no state-level 1 + modifier:state_*_mult,
        which missed literacy, starvation and every class, workplace and working-conditions term
        (docs/testing/demographics-growth-probe-results-2026-10-09.md)."""
        body = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_walks"))
        self.assertIn("set_local_variable = { name = te_dg_p_eb value = te_demog_pop_engine_births }", body)
        self.assertIn("set_local_variable = { name = te_dg_p_ed value = te_demog_pop_engine_deaths }", body)
        self.assertIn("set_local_variable = { name = te_dg_p_mb value = te_demog_pop_birth_mult }", body)
        self.assertIn("set_local_variable = { name = te_dg_p_md value = te_demog_pop_death_mult }", body)
        self.assertIn("add = { value = local_var:te_dg_p_eb multiply = local_var:te_dg_p_mb }", body)
        self.assertIn("add = { value = local_var:te_dg_p_ed multiply = local_var:te_dg_p_md }", body)
        self.assertNotIn("modifier:state_birth_rate_mult", body)
        self.assertNotIn("modifier:state_mortality_mult", body)

    def test_the_walk_expects_the_steps_months(self):
        """A month's curves x the months the step covers: 12 on the yearly pulse, the clock's window under
        fast mode (te_demog_step_months), never a literal 12."""
        body = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_walks"))
        for var in ("te_dg_eb", "te_dg_ed"):
            block = re.search(r"name = %s\s+value = \{([^{}]*)\}" % var, body)
            self.assertIsNotNone(block, var)
            self.assertIn("multiply = te_demog_step_months", block.group(1))
            self.assertNotIn("multiply = 12", block.group(1))

    def test_inheritance_reads_the_walk(self):
        self.assertNotIn("te_inh_agrarian_share_value", _text(INH_VALUES))
        self.assertIn("value = var:te_dg_agr_share", _block(_text(INH_EFFECTS), "te_inh_refresh_rural_effects"))
        self.assertNotIn("on_yearly_pulse_state", _text(INH_ON_ACTIONS))

    def test_orchestrator_walks_then_refreshes_inheritance(self):
        body = _block(_text(EFFECTS), "te_demog_state_yearly")
        self.assertLess(body.index("te_demog_walks = yes"), body.index("te_inh_refresh_rural_effects = yes"))

    def test_state_pulse_is_not_gated_by_the_rule(self):
        hook = _block(_text(DEMOG_ON_ACTIONS), "te_demog_state_yearly_on_action")
        self.assertNotIn("te_demog_cohorts_run", hook)

    def test_ownership_fractions_are_read_only_from_built_buildings(self):
        """Observer test of #830: a building whose first level is under construction
        logs "ownership_fraction requires the building to be built" three times a pulse."""
        body = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_walks"))
        limit = re.search(r"limit = \{([^{}]*)\}\s*change_local_variable = \{ name = te_dg_w_priv", body)
        self.assertIsNotNone(limit)
        self.assertIn("level > 0", limit.group(1))
        self.assertIn("te_demog_is_capital_building = yes", limit.group(1))

    def test_the_state_subtab_gate_needs_no_player(self):
        """Observer test of #830: an observer has no player, so a GetPlayer root logged an
        error every frame the state panel was open. The gate reads only the rule."""
        panel = _text(ROOT / "gui" / "states_panel.gui")
        reads = re.findall(r"GetScriptedGui\('te_pops_demog_tab_sgui'\)\.IsShown\( GuiScope\.SetRoot\( ([\w.]+) \)", panel)
        self.assertEqual(reads, ["State.GetOwner.MakeScope"] * 2)
        content = _text(ROOT / "gui" / "te_demographics_widgets.gui")
        content = content[content.index("type te_state_demog_overview"):]
        self.assertNotIn("GetPlayer", content, "the state's sections read only the state")


def _parse_script(text):
    """Paradox script as an ordered tree: a list of (key, operator, value), value a str or a list. A bare item in a
    list block (a decree's `unlocking_technologies = { medical_degrees }`) is (item, "", ""). It doesn't read `?=`: a
    block a test runs writes `exists = owner` and `owner = { }` instead (te_demog_um_effects.txt)."""
    text = re.sub(r"#[^\n]*", "", text)
    tokens = re.findall(r"[{}]|[<>]=?|=|[^\s{}=<>]+", text)
    pos = 0

    def block():
        nonlocal pos
        items = []
        while pos < len(tokens) and tokens[pos] != "}":
            if pos + 1 >= len(tokens) or tokens[pos + 1] not in ("=", "<", ">", "<=", ">="):
                items.append((tokens[pos], "", ""))
                pos += 1
                continue
            key, op = tokens[pos], tokens[pos + 1]
            pos += 2
            if tokens[pos] == "{":
                pos += 1
                value = block()
                pos += 1
            else:
                value = tokens[pos]
                pos += 1
            items.append((key, op, value))
        return items

    return block()


def _find(items, key):
    return next(v for k, _, v in items if k == key)


class TestStateGini(unittest.TestCase):
    """te_demog_state_gini (the state's wealth bands into the generated formula) against the model."""

    def shown(self, bands):
        eng = _Engine({})
        for k in range(1, P.GINI_BANDS + 1):
            n, y = bands.get(k, (0.0, 0.0))
            eng.vars[f"te_dg_gn{k}"], eng.vars[f"te_dg_gy{k}"] = float(n), float(y)
        eng.call("te_demog_state_gini")
        return eng.vars["te_dg_gini"]

    def test_matches_the_model_on_random_states(self):
        rng = random.Random(7)
        for _ in range(200):
            bands, per_head = {}, 0.0
            for k in range(1, P.GINI_BANDS + 1):
                per_head += rng.uniform(0.0, 40.0)
                n = rng.choice([0, rng.randint(1, 50000)])
                bands[k] = (n, n * per_head)
            expected = demographics_model.shown_gini(demographics_model.grouped_gini(list(bands.values())))
            self.assertAlmostEqual(self.shown(bands), expected, places=9, msg=str(bands))

    def test_no_people_or_no_income_shows_the_floor(self):
        self.assertAlmostEqual(self.shown({}), 1 - P.GINI_SHOWN_EQUALITY, places=9)
        self.assertAlmostEqual(self.shown({1: (10, 0), 4: (5, 0)}), 1 - P.GINI_SHOWN_EQUALITY, places=9)

    def test_state_and_country_share_one_generated_formula(self):
        text = _text(WEALTH_EFFECTS)
        for caller in ("te_demog_state_gini", "te_demog_wc_national"):
            self.assertIn("te_demog_gini_from_locals = yes", _block(text, caller), caller)
        self.assertNotIn("te_demog_gini_from_locals = {", text, "the formula is generated, not hand-written")
        self.assertIn("name = te_dg_gini", _block(_text(GENERATED_EFFECTS), "te_demog_gini_from_locals"))

    def test_the_walk_sums_wealth_bands_not_strata(self):
        walk = _block(_text(EFFECTS), "te_demog_walks")
        for call in ("te_demog_gini_band_init = yes", "te_demog_gini_band_add = yes", "te_demog_gini_band_store = yes"):
            self.assertIn(call, walk)
        self.assertNotIn("strata = upper", walk)
        start = walk.index("every_scope_pop = {") + len("every_scope_pop = {")
        depth, i = 1, start
        while depth:
            depth += {"{": 1, "}": -1}.get(walk[i], 0)
            i += 1
        pops = walk[start:i - 1]
        self.assertIn("te_demog_gini_band_add = yes", pops, "each pop adds itself, inside the pop loop")
        self.assertNotIn("te_demog_gini_band_store = yes", pops)


class TestStep(unittest.TestCase):
    def test_orchestrator_branches(self):
        """Seed when there is no census, a gap of more than a year or an emptied ring; step once a year, however far
        the people moved (owner, 2026-10-20); nothing on a second pulse in the same year (Review Focus 3)."""
        self.assertIn("te_demog_state_census = yes", _block(_text(EFFECTS), "te_demog_state_yearly"))
        body = _block(_text(EFFECTS), "te_demog_state_census")
        self.assertIn("te_demog_cohorts_run = yes", body)
        self.assertIn("te_demog_seed = yes", body)
        self.assertIn("te_demog_step = yes", body)
        self.assertIn("local_var:te_dg_gap > 1", body)
        self.assertIn("local_var:te_dg_gap = 1", body)
        # no size test: the move goes to the step's booking, the known moves with it
        code = re.sub(r"#[^\n]*", "", body)
        for gone in ("te_dg_pop_last", "te_dg_over", "te_dg_under", "te_demog_rs_known_change", "1.25", "0.75"):
            self.assertNotIn(gone, code)

    def test_the_branch_limits_compare_locals(self):
        """Observer tests of #830 and #833 (2026-10-09): state_population > { value =
        var:te_dg_pop_last multiply = 1.25 } held for every state with people, even 0.3% up, and its
        0.75 twin for none, so every state seeded at every pulse and none stepped. The size test went on
        2026-10-20 (owner); the limits left compare a local (the gap) and literals."""
        body = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_state_census"))
        self.assertNotRegex(body, r"state_population [<>]=? \{")
        self.assertIn("value = { value = te_demog_year subtract = var:te_dg_year }", body)
        self.assertIn("set_variable = { name = te_dg_year value = te_demog_year }", _block(_text(EFFECTS), "te_demog_set_scale"))

    def test_no_script_compares_state_population_with_a_block(self):
        """The form above misfired in game with no log line, so nothing in the mod's script uses it:
        compare state_population with a number, or take the difference into a local first."""
        hits = []
        for path in [*ROOT.glob("common/**/*.txt"), *ROOT.glob("events/**/*.txt")]:
            text = re.sub(r"#[^\n]*", "", _text(path))
            for m in re.finditer(r"\bstate_population\s*(?:[<>]=?|!=|=)\s*\{", text):
                line = text.count("\n", 0, m.start()) + 1
                hits.append(f"{path.relative_to(ROOT)}:{line}")
        self.assertEqual(hits, [])

    def test_every_cohort_entry_point_is_gated(self):
        """Review Focus 5: nothing writes a cohort without te_demog_cohorts_run."""
        text = _text(EFFECTS)
        for caller in ("te_demog_state_yearly", "te_demog_country_game_start", "te_demog_country_monthly"):
            body = _block(text, caller)
            for entry in ("te_demog_seed = yes", "te_demog_seed_off_pulse = yes", "te_demog_step = yes",
                          "te_demog_share_war_dead = yes"):
                if entry in body:
                    gate = body.rfind("te_demog_cohorts_run = yes", 0, body.index(entry))
                    self.assertNotEqual(gate, -1, f"{caller}: {entry} before the gate")

    def test_family_limitation_matches_the_params(self):
        modifiers = _text(ROOT / "common" / "static_modifiers" / "te_demog_modifiers.txt")
        body = _block(modifiers, "te_demog_family_limitation")
        self.assertIn(f"{P.MEANS_SHIFT_TYPE} = {P.FAMILY_LIMITATION_MEANS}", body)
        self.assertIn("name = te_demog_family_limitation", _text(ROOT / "common" / "history" / "extra_history.txt"))

    def test_fold_writes_the_births(self):
        body = _block(_text(EFFECTS), "te_demog_fold_slot")
        self.assertIn("name = te_dg_f$S$", body)
        self.assertIn("local_var:te_dg_births", body)

    def test_empty_ages_stay_empty(self):
        text = _text(EFFECTS)
        self.assertIn("remove_variable = te_dg_f$S$", _block(text, "te_demog_seed_slot"))
        self.assertIn("remove_variable = te_dg_f$S$", _block(text, "te_demog_age_slot"))

    def test_slot_skips_empty_slots_but_keeps_counting_ages(self):
        body = _block(_text(EFFECTS), "te_demog_slot")
        self.assertIn("has_variable = te_dg_f$S$", body)
        self.assertGreater(body.index("change_local_variable = { name = te_dg_age add = 1 }"),
                           body.index("has_variable = te_dg_f$S$"))


def _raw_blocks(paths):
    """name -> body text of every top-level `name = { ... }` in the files, comments removed."""
    out = {}
    for path in paths:
        text = re.sub(r"#[^\n]*", "", _text(path))
        for m in re.finditer(r"^([\w.]+) = \{", text, re.M):
            depth, i = 1, m.end()
            while depth:
                depth += {"{": 1, "}": -1}.get(text[i], 0)
                i += 1
            out[m.group(1)] = text[m.end():i - 1]
    return out


FIXED_MAX = (2 ** 63 - 1) / 1e5   # the largest value script holds: an i64 in units of 1e-5

# The owner's reads phase 2 step 1's census makes (te_demog_work_setup), for engines that don't give them (the 10-14s
# at work: an owner whose laws carry no line, 2026-10-17); and phase 2 step 4's engine read, the state's unemployment
# (te_demog_unemployment, the youth bulge).
WORK_DEFAULTS = {"te_demog_child_work": 0.0, "te_demog_pension_kind": 0.0,
                 "te_demog_pension_age": float(P.PENSION_AGE["standard"]), f"modifier:{P.WOMENS_WORK_TYPE}": 0.0,
                 **{f"modifier:{t}": 0.0 for t in P.PARTICIPATION_TYPES},
                 # phase 2 step 2: the workforce term's read of the state's working-adult field
                 f"modifier:{P.WORKING_ADULT_FIELD}": 0.0, "state_unemployment_rate": 0.0}
# Phase 2 step 3b: the Family Policy types' reads and the two owner reads (the prenatal-sexing technology's gate on the
# sex ratio at birth, Birth Limit's part of desired fertility), 0 unless a test gives them (_family_fixtures).
FAMILY_DEFAULTS = {**{f"modifier:{t}": 0.0 for t in P.MEASURE_TYPES}, "te_demog_srb_add": 0.0,
                   "te_demog_ms_birth_limit_part": 0.0}
# Phase 3's owner reads (Human Purity's ban, read from the owner's modifier; the owner's market threshold) and its types,
# the ageing pair and the laws' longevity care types (the cover, floor and reach the script reads in state scope), for
# engines that don't give them (_lx_fixtures and _mod_fixtures give them from the model's inputs).
LX_DEFAULTS = {"te_demog_lx_banned": 0.0, "te_demog_lx_owner_w": float(P.LX_MARKET_START),
               **{f"modifier:{t}": 0.0 for t in P.LATE_TYPES + P.LX_LAW_TYPES},
               # the country's carrier reads has_technology_researched (te_demog_lx_market_step, the yearly pulse); the
               # state's ectogenesis levels walk its buildings
               "te_demog_lx_country_carrier": 0.0, "te_demog_lx_ecto_levels": 0.0,
               # a pop's wealth, which the walk's Full-only sums read for the wealth slope (te_demog_absorbed_walk_pop)
               "wealth": 0.0}
# Phase 2 step 4's three effects (demographics_params' switches, generated as 0 or 1; on since the migrant booking,
# 2026-10-12): an engine takes the
# switches as the model reads them, so a test that patches them on (ALL_ON) runs the script with them on too.
SWITCHES = {"te_demog_k_conscription_effects": "CONSCRIPTION_EFFECTS", "te_demog_k_youth_effects": "YOUTH_BULGE_EFFECTS",
            "te_demog_k_sex_effects": "SEX_BALANCE_EFFECTS"}


def _switch_fixtures():
    return {k: 1.0 if getattr(P, attr) else 0.0 for k, attr in SWITCHES.items()}


def ALL_ON(f):
    """Patch the three switches on (as the migrant booking turned them, 2026-10-12) for one test."""
    for attr in SWITCHES.values():
        f = unittest.mock.patch.object(P, attr, True)(f)
    return f


def ALL_OFF(f):
    """Patch the three switches off (held back, as step 4 shipped them) for one test."""
    for attr in SWITCHES.values():
        f = unittest.mock.patch.object(P, attr, False)(f)
    return f


# Phase 2 step 4's once-a-game self-checks, which the census's refresh calls (te_demog_consequences_refresh): they set a
# global variable, log and fire an event, none of which the interpreter runs; TestConsequencesScript reads their text.
SELF_CHECK_STUBS = {"te_debug_demog_unemployment_selfcheck": "", "te_debug_demog_conscription_selfcheck_start": "",
                    # phase 3's (te_debug_demog_effects.txt): they read the capital, s:STATE_ULSTER and debug_log
                    "te_debug_demog_fl_selfcheck_start": "", "te_debug_demog_fl_neighbours_check": "",
                    "te_debug_demog_neighbours_selfcheck": "",
                    # issue #1029's (it reads debug_log and the state's name): TestCauseDeaths reads its text
                    "te_debug_demog_cause_deaths_selfcheck": "",
                    # Causes of Death's tags (owner, 2026-10-22): test_demographics_cause_tags reads its text
                    "te_debug_demog_cause_tags_selfcheck": "",
                    # the census's province line (2026-10-20): a debug_log line; TestProvinceLine runs its text
                    "te_debug_demog_province_change": ""}
# Phase 3: Cultural Hegemony's factor reads the owner (te_demog_tfr_hegemon): 1 unless a test gives it.
PHASE3_DEFAULTS = {"te_demog_tfr_hegemon": 1.0}
# 2026-10-20: the walk applies the state's wealth line per pop, and the refresh and the split read it beside te_dg_w_edw:
# none unless a test says (the census's pair is off, and Private Health Insurance's line outside Full).
WEALTH_LINE_DEFAULTS = {"modifier:state_mortality_wealth_mult": 0.0}
# Causes of Death's tags (owner, 2026-10-22): no tagged line on top unless a test says
CAUSE_TAG_DEFAULTS = {f"modifier:{t}": 0.0 for t in P.DEATH_CAUSE_TYPES.values()}
WALK_CAUSE_DEFAULTS = {"te_dg_w_odh": 0.0, "te_dg_w_odx": 0.0, "te_dg_w_odq": 0.0, "te_dg_w_odw": 0.0}
# the pop's own lines the walk reads by cause: non-homeland mortality and its class's line, none unless a test says (nor a
# state line on everyone); a pop's wealth (the wealth line's), 0
POP_LINE_DEFAULTS = {"modifier:state_non_homeland_mortality_mult": 0.0, "wealth": 0.0, "modifier:state_mortality_mult": 0.0,
                     **{f"modifier:state_{t}_mortality_mult": 0.0
                        for t in ("academics", "aristocrats", "farmers", "laborers", "machinists", "peasants", "slaves",
                                  "soldiers")}}
# Issue #1029: the month a state's count is taken (te_dg_count_mi, the subtab's next count), te_history_month_index, which
# reads the calendar's month: the start of 1836's year unless a test says.
PANEL_DEFAULTS = {"te_history_month_index": 1836.0 * 12}
# The territory counts (te_demog_territory_values.txt, 2026-10-20) iterate provinces and states, which _ops can't: a
# state's provinces and a country's states, constant unless a test says.
TERRITORY_DEFAULTS = {"te_demog_state_provinces": 10.0, "te_demog_wc_state_count": 5.0}


class _Engine:
    """Enough of the engine to run the census: value blocks applied in order (min and max clamp
    where they stand), variables and locals, if / else_if / else, while, triggers, and scripted
    effects with their $ARG$ substituted as text. A read of a variable or local that was never
    set fails, as does an argument the callee doesn't name (the script_argument_audit rule).
    `fixtures` stand in for engine reads and for script values that read the owner. With
    truncate=True every operation and every stored value is cut to five decimals, toward zero:
    the engine's fixed point (values are i64 x 1e-5), and a value past FIXED_MAX fails."""

    def __init__(self, fixtures, triggers=None, effects=None, truncate=False):
        self.truncate = truncate
        self.effects = _raw_blocks([EFFECTS, GENERATED_EFFECTS, WEALTH_EFFECTS, FAST_EFFECTS, RATE_EFFECTS, LINE_EFFECTS,
                                    PRACTICE_EFFECTS, WORKFORCE_LINE_EFFECTS, WORK_EFFECTS, CONSEQ_EFFECTS,
                                    LX_EFFECTS, LX_GEN_EFFECTS, FL_EFFECTS, SPREAD_EFFECTS, PLACE_EFFECTS,
                                    UM_EFFECTS, UM_GEN_EFFECTS])
        # Internal Resettlement's known moves (2026-10-19); its self-check reads globals and debug_log, which a test of
        # its text reads (test_demographics_resettle.py)
        self.effects.update(_raw_blocks([RESETTLE_EFFECTS, RESETTLE_GEN_EFFECTS]))
        self.effects["te_demog_rs_selfcheck"] = ""
        # the self-check rate_below_measured (2026-10-20) reads globals and writes debug_log lines:
        # test_demographics_rate_floor runs it
        self.effects.update({"te_demog_rbm_selfcheck_flows": "", "te_demog_rbm_selfcheck_arm": ""})
        # phase 2 step 2's workforce self-checks write debug_log lines and read is_capital, which the interpreter
        # doesn't know: TestWorkTermSelfChecks reads their text, and a test that runs them gives them as effects
        self.effects.update({"te_debug_demog_wf_term_checks": "", "te_debug_demog_wf_term_landing": ""})
        self.effects.update(SELF_CHECK_STUBS)
        self.effects.update(effects or {})
        self.values = _raw_blocks([VALUES, GENERATED_VALUES, DISPLAY_VALUES, LINE_VALUES, WORKFORCE_LINE_VALUES,
                                   WORK_VALUES, CONSEQ_VALUES, LX_VALUES, LX_GEN_VALUES, SPREAD_VALUES, PLACE_VALUES,
                                   UNEMP_VALUES, UM_VALUES, UM_GEN_VALUES])
        self.values.update(_raw_blocks([RESETTLE_GEN_VALUES]))
        self.triggers = _raw_blocks([TRIGGERS, PLACE_TRIGGERS])
        # the history store (te_history_country_is_tracked) has no containers here, and the console's
        # census log (te_demog_census_log_on) only writes debug_log lines: both off unless a test says;
        # so is fast mode's census clock (te_demog_clock_on), whose globals a test gives as fixtures
        # ("global_var:te_demog_clock" and the like), and the rule's Full (te_demog_effects_run): off unless a
        # test says (the real trigger reads has_game_rule, which _Engine doesn't know)
        # te_demog_has_pension_law (phase 2 step 1) reads has_law: off unless a test says, so an engine that runs the
        # country's game start or yearly census never evaluates it
        # a pop's is_employed (calibration step 3's country-scope absorbed lines read its workplace): not employed unless
        # a test says (_OwnerEngine's workplace)
        self.trigger_fixtures = {"te_history_country_is_tracked": False, "te_demog_census_log_on": False,
                                 "te_demog_clock_on": False, "te_demog_effects_run": False,
                                 "te_demog_has_pension_law": False, "is_employed": False,
                                 # a pop lives in its homeland unless a test says (the walk's non-homeland line)
                                 "is_homeland_of_country_cultures": True,
                                 # phase 2 step 2's AI pension pulse (te_demog_pension_ai) runs at every country's
                                 # yearly census: a player's unless a test says
                                 "is_ai": False, **(triggers or {})}
        self.fixtures = {**WORK_DEFAULTS, **FAMILY_DEFAULTS, **LX_DEFAULTS, **PHASE3_DEFAULTS, **PANEL_DEFAULTS,
                         **WEALTH_LINE_DEFAULTS, **CAUSE_TAG_DEFAULTS, **POP_LINE_DEFAULTS, **TERRITORY_DEFAULTS,
                         **fixtures}
        self.vars, self.locals, self._trees = {}, {}, {}
        # the walk's bare deaths x wealth (te_demog_absorbed_walk_init sets it in every walk, 0 outside Full): the refresh
        # and the split read it beside the wealth line since 2026-10-20, and a stubbed walk need not give it; nor the
        # pops' own lines by cause (owner, 2026-10-22), which the refresh and the split read beside severe starvation's
        self.locals["te_dg_w_edw"] = 0.0
        self.locals.update(WALK_CAUSE_DEFAULTS)
        self.modifiers = {}   # add_modifier's name -> its multiplier
        self.decrees = set()  # has_decree's decrees in force (the state's)
        self.removed = []     # remove_modifier's names, in order
        # the state's place, (state region, strategic region), for region = sr:… and state_region = s:… (the practices'
        # start ladders), and the other states of its state region, each a dict of its variables with its own
        # state_population (state_region = { every_scope_state = { … } }, the practices' seed)
        self.place = (None, None)
        self.siblings = []
        # the state region's own variables (state_region = { set_variable / has_variable / var: }): the practices'
        # copy of the shares, te_dg_pr_<P>_r (Stop B, I1)
        self.region_vars = {}
        # phase 3: its neighbouring states (every_neighbouring_state), each a dict of its variables with its own
        # state_population, as the siblings are (te_demog_practices_neighbours)
        self.neighbours = []

    def _tree(self, table, name, args=()):
        key = (id(table), name, args)
        if key not in self._trees:
            text = table[name]
            for k, v in args:
                assert isinstance(v, str), f"{name}: block argument {k}"
                assert f"${k}$" in text, f"{name}: unused argument {k}"
                text = text.replace(f"${k}$", v)
            assert "$" not in text, f"{name}: argument left unbound"
            self._trees[key] = _parse_script(text)
        return self._trees[key]

    def number(self, tok):
        if tok.startswith("local_var:"):
            assert tok[10:] in self.locals, f"read of unset local {tok}"
            return self.locals[tok[10:]]
        if tok.startswith("var:"):
            assert tok[4:] in self.vars, f"read of missing variable {tok}"
            return self.vars[tok[4:]]
        if tok in self.fixtures:
            return self.fixtures[tok]
        if tok in self.values:
            return self.value(self._tree(self.values, tok))
        if tok.startswith("state.modifier:"):
            # one state: a pop's state reads the state's own modifiers
            return self.number(tok[6:])
        return float(tok)

    def value(self, v):
        return self.number(v) if isinstance(v, str) else self._ops(v, 0.0)

    def _q(self, x):
        if not self.truncate:
            return x
        assert abs(x) <= FIXED_MAX, f"fixed-point overflow: {x:.4g}"
        return math.trunc(x * 1e5 + (1e-7 if x >= 0 else -1e-7)) / 1e5

    def _ops(self, items, acc):
        chain = None
        for key, _, arg in items:
            if key in ("if", "else_if", "else"):
                go, chain = self._branch(key, arg, chain)
                if go:
                    acc = self._ops([i for i in arg if i[0] != "limit"], acc)
                continue
            chain = None
            if key == "value":
                acc = self.value(arg)
            elif key == "add":
                acc += self.value(arg)
            elif key == "subtract":
                acc -= self.value(arg)
            elif key == "multiply":
                acc *= self.value(arg)
            elif key == "divide":
                d = self.value(arg)
                assert d != 0, "division by zero"
                acc /= d
            elif key == "min":
                acc = max(acc, self.value(arg))
            elif key == "max":
                acc = min(acc, self.value(arg))
            elif key == "floor":
                acc = float(math.floor(acc))
            elif key == "modulo":
                acc = math.fmod(acc, self.value(arg))
            else:
                raise AssertionError(f"value operator {key}")
            acc = self._q(acc)
        return acc

    def _branch(self, key, block, chain):
        """(run this branch, the chain after it); chain None = closed, True = a branch ran, False = open."""
        if key == "if":
            taken = self.holds(_find(block, "limit"))
            return taken, taken
        assert chain is not None, f"{key} without an if"
        if chain:
            return False, True
        if key == "else":
            return True, None
        taken = self.holds(_find(block, "limit"))
        return taken, taken

    def holds(self, items):
        return all(self._test(*item) for item in items)

    def _test(self, key, op, arg):
        if key == "NOT":
            assert len(arg) == 1, "NOT with several triggers"
            return not self.holds(arg)
        if key == "OR":
            return any(self._test(*item) for item in arg)
        if key == "AND":
            return self.holds(arg)
        if key == "custom_tooltip":
            # the text only labels the tooltip; the triggers inside decide, as an AND
            return self.holds([item for item in arg if item[0] != "text"])
        if key == "has_variable":
            return arg in self.vars
        if key in ("owner", "state") and isinstance(arg, list):
            # one state, one owner (_OwnerEngine reads their laws and institutions too)
            return self.holds(arg)
        if key == "is_pop_type":
            return arg == getattr(self, "pop_type", None)
        if key == "is_homeland_of_country_cultures":
            # its argument is a scope (owner), not yes or no: the fixture says whether it holds
            return self.trigger_fixtures["is_homeland_of_country_cultures"]
        if key == "has_local_variable":
            return arg in self.locals
        if key == "has_modifier":
            return arg in self.modifiers
        if key == "has_decree":
            return arg in self.decrees
        if key == "always":
            return arg == "yes"
        if key == "region":
            return arg == f"sr:{self.place[1]}"
        if key == "state_region" and isinstance(arg, str):
            return arg == f"s:{self.place[0]}"
        if key == "state_region":
            saved, self.vars = self.vars, self.region_vars
            try:
                return self.holds(arg)
            finally:
                self.vars = saved
        if key in self.trigger_fixtures:
            return self.trigger_fixtures[key] == (arg == "yes")
        if key in self.triggers:
            return self.holds(self._tree(self.triggers, key)) == (arg == "yes")
        a, b = self.value(key), self.value(arg)
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b, "=": a == b}[op]

    def run(self, items):
        chain = None
        for key, _, arg in items:
            if key in ("if", "else_if", "else"):
                go, chain = self._branch(key, arg, chain)
                if go:
                    self.run([i for i in arg if i[0] != "limit"])
                continue
            chain = None
            if key in ("set_local_variable", "set_variable"):
                store = self.locals if key == "set_local_variable" else self.vars
                got = self.value(_find(arg, "value"))
                # a scope (_CountryEngine's scope:X is the state's dict: te_dg_primate_state) is stored as it is
                store[_find(arg, "name")] = got if isinstance(got, dict) else self._q(got)
            elif key in ("change_local_variable", "change_variable"):
                store = self.locals if key == "change_local_variable" else self.vars
                name = _find(arg, "name")
                assert name in store, f"change of unset {name}"
                store[name] = self._ops([i for i in arg if i[0] != "name"], store[name])
            elif key == "clamp_variable":
                name = _find(arg, "name")
                assert name in self.vars, f"clamp of unset {name}"
                lo, hi = self.value(_find(arg, "min")), self.value(_find(arg, "max"))
                self.vars[name] = min(max(self.vars[name], lo), hi)
            elif key == "remove_variable":
                self.vars.pop(arg, None)
            elif key == "add_modifier":
                # a modifier with no multiplier (phase 2 step 2's pension positions) applies at 1
                mult = next((v for k, _, v in arg if k == "multiplier"), None)
                self.modifiers[_find(arg, "name")] = 1.0 if mult is None else self._q(self.value(mult))
            elif key == "remove_modifier":
                assert arg in self.modifiers, f"remove of absent modifier {arg}"
                del self.modifiers[arg]
                self.removed.append(arg)
            elif key == "while":
                for _ in range(int(self.value(_find(arg, "count")))):
                    self.run([i for i in arg if i[0] != "count"])
            elif key == "state_region" and isinstance(arg, list) and arg[0][0] != "every_scope_state":
                # state_region = { … }: the region's own variables (the practices' copy of the shares); locals are
                # the effect's, so they cross the scope change
                saved, self.vars = self.vars, self.region_vars
                try:
                    self.run(arg)
                finally:
                    self.vars = saved
            elif key == "every_neighbouring_state":
                # phase 3: the state's neighbouring states (te_demog_practices_neighbours), as the siblings below
                self._each_state(self.neighbours, arg)
            elif key == "state_region" and isinstance(arg, list):
                # state_region = { every_scope_state = { limit = { … } … } }: the other states in its state region,
                # each a dict of its variables with its own state_population (te_demog_practice_seed)
                (inner, _, body), = arg
                assert inner == "every_scope_state", inner
                self._each_state(self.siblings, body)
            elif key in self.effects:
                args = () if arg == "yes" else tuple((k, v) for k, _, v in arg)
                self.run(self._tree(self.effects, key, args))
            else:
                raise AssertionError(f"effect {key}")

    def _each_state(self, states, body):
        """An iterator's body over `states` (each a dict of its variables with its own state_population): its limit,
        then the rest, with the state's variables and population in place of the scope's; locals are the effect's."""
        limit = next((v for k, _, v in body if k == "limit"), [])
        rest = [i for i in body if i[0] != "limit"]
        for sib in states:
            saved_vars, saved_pop = self.vars, self.fixtures.get("state_population")
            self.vars, self.fixtures["state_population"] = sib, sib["state_population"]
            try:
                if self.holds(limit):
                    self.run(rest)
            finally:
                self.vars = saved_vars
                if saved_pop is None:
                    self.fixtures.pop("state_population", None)
                else:
                    self.fixtures["state_population"] = saved_pop

    def call(self, effect):
        self.run(_parse_script(f"{effect} = yes"))


def _stored(inp):
    """The variables a step stores for `inp`: te_demog_cause_inputs_store's, and the drifted medicine (inp.medicine,
    or the targets)."""
    med = inp.medicine if inp.medicine is not None else demographics_model.medicine_targets(inp)
    out = {"te_dg_sol": float(inp.sol), "te_dg_lit": float(inp.literacy), "te_dg_acc": med["access"],
           "te_dg_in_sol": float(inp.sol), "te_dg_in_lit": float(inp.literacy),
           "te_dg_in_turm": min(max(inp.turmoil, 0.0), 1.0), "te_dg_in_crowd": inp.crowding,
           "te_dg_in_mal": float(inp.malaria),
           "te_dg_in_malc": min(max(inp.mods.get(P.MALARIA_CONTROL_TYPE, 0.0), 0.0), 1.0)}
    for cause, st in P.SAFETY_TYPES.items():
        out[f"te_dg_in_saf_{P.CAUSE_SHORT[cause]}"] = min(max(inp.mods.get(st, 0.0), 0.0), P.SAFETY_MAX)
    for cause in P.MEDICINE_CAUSES:
        out[f"te_dg_trt_{P.CAUSE_SHORT[cause]}"] = med[cause]
    for cause, types in P.MORTALITY_TYPES.items():
        out[f"te_dg_in_{P.CAUSE_SHORT[cause]}"] = sum(inp.mods.get(t, 0.0) for t in types)
    return out


_MIGRANT_LINES = []


def _with_migrant_lines(inp):
    """inp with the migrant profile's two types (modifier-types stage 3, 2026-10-19: women's share at work and families
    among migrants) totalled from the game files' carriers for its laws and techs, as demographics_modifiers resolves
    them for a state."""
    if not _MIGRANT_LINES:
        _MIGRANT_LINES.extend(DM.load_carriers(types=P.MIGRANT_PROFILE_TYPES))
    return dataclasses.replace(inp, mods={**inp.mods, **DM.totals(_MIGRANT_LINES, inp.techs, inp.laws,
                                                                   types=P.MIGRANT_PROFILE_TYPES)})


def _mod_fixtures(inp):
    """The engine reads the step makes: every census type, turmoil."""
    out = {f"modifier:{t}": inp.mods.get(t, 0.0) for t in P.DEMOG_TYPES}
    for t in (P.WOMENS_WORK_TYPE, *P.PARTICIPATION_TYPES):
        out[f"modifier:{t}"] = inp.mods.get(t, 0.0)
    out["turmoil"] = inp.turmoil
    out["te_demog_malaria_level"] = float(inp.malaria)   # has_state_trait, which _Engine can't read (calibration step 3)
    out.update(_family_fixtures(inp))
    out.update(_lx_fixtures(inp))
    return out


def _lx_fixtures(inp):
    """Phase 3's owner reads from the model's inputs (demographics_model.lx_banned, lx_threshold): Human Purity's ban (the
    owner's modifier, which the interpreter can't read from a state) and the owner's market threshold. The laws' cover,
    floor and reach are state reads of their types (_mod_fixtures)."""
    return {"te_demog_lx_banned": 1.0 if demographics_model.lx_banned(inp) else 0.0,
            "te_demog_lx_owner_w": float(P.LX_MARKET_START if inp.lx_w is None else inp.lx_w),
            "te_demog_lx_ecto_levels": float(inp.ecto_levels)}


def _family_fixtures(inp):
    """Phase 2 step 3b's reads from the model's inputs: the Family Policy types, and the owner's reads the interpreter
    can't make (te_demog_srb_add: the type with prenatal sexing; te_demog_ms_birth_limit_part: Birth Limit's part)."""
    out = {f"modifier:{t}": inp.mods.get(t, 0.0) for t in P.MEASURE_TYPES}
    srb = inp.mods.get(P.SRB_TYPE, 0.0)
    out["te_demog_srb_add"] = max(0.0, srb) if P.PRENATAL_SEXING_TECH in inp.techs else 0.0
    out["te_demog_ms_birth_limit_part"] = inp.birth_limit
    return out


def _engine_for(inp, year, pop, effects=None, engine=None, real_multipliers=False, place=(None, None), targets=None,
                erosion=None):
    """A state with the census on, the walk's sums set from `inp`, and the owner's multipliers
    (script values that read the owner's techs and laws) taken from the model. The step's own reads (the census's
    types and turmoil) are fixtures too, for te_demog_cause_inputs_store and the drift; real_multipliers runs the
    generated te_demog_mult_* on them instead of taking the model's. place: (state region, strategic region), for the
    practices' start ladders; targets, erosion: {practice: value}, the practices' targets and erosions, which read
    the owner and the census's types (fixtures, 0 by default). At no place and 0 a state's shares are 0 and stay 0."""
    mult = demographics_model.cause_multipliers(inp)
    fixtures = {
        "year": float(year),
        "state_population": float(pop),
        "te_demog_means": demographics_model.means(inp),
        f"modifier:{P.NATURAL_FERTILITY_TYPE}": inp.mods.get(P.NATURAL_FERTILITY_TYPE, 0.0),
        # phase 2 step 1: the owner's reads te_demog_work_setup makes (WORK_DEFAULTS), from the model
        "te_demog_child_work": demographics_model.child_work_share(inp),
        "te_demog_pension_kind": float(demographics_model.pension_kind(inp)),
        "te_demog_pension_age": float(inp.pension_age if inp.pension_age is not None else P.PENSION_AGE["standard"]),
        **_mod_fixtures(inp),
    }
    if not real_multipliers:
        fixtures.update({
            "te_demog_mult_infection": mult["infection"],
            "te_demog_mult_external": mult["external"],
            "te_demog_mult_chronic": mult["chronic"],
            "te_demog_mult_work": mult["work"],
            "te_demog_mult_maternal": mult["maternal"] * P.MATERNAL_PER_100K_BIRTHS,
            "te_demog_infection_adult": demographics_model.infection_adult(inp),
        })
    for p in P.PRACTICES:
        fixtures[f"te_demog_pr_target_{p}"] = (targets or {}).get(p, 0.0)
        fixtures[f"te_demog_pr_erosion_{p}"] = (erosion or {}).get(p, 0.0)
    # the sex balance's switch as the model reads it (demographics_params.SEX_BALANCE_EFFECTS; generated as 0 or 1), so a
    # test that patches the switch on runs the script with it on too
    fixtures.update(_switch_fixtures())
    eng = (engine or _Engine)(fixtures, triggers={"te_demog_cohorts_run": True}, effects=effects)
    eng.place = place
    eng.vars.update(te_dg_lit=inp.literacy, te_dg_urban_share=inp.urban_share,
                    te_dg_wtfr=demographics_model.wealth_tfr(inp.sol), te_dg_sol=float(inp.sol))
    eng.vars.update(te_dg_low_share=inp.low_share)   # the walk's lower strata (phase 2 step 1)
    # phase 3: the walk's people by wealth band, eligibility's target reads them (te_demog_lx_access)
    for k, n in (inp.wealth_bands or {}).items():
        if n > 0:
            eng.vars[f"te_dg_gn{k}"] = float(n)
    if inp.crowding:
        eng.modifiers["migration_crowding"] = inp.crowding / P.MIGRATION_CROWDING_PULL_PER_MULT
        eng.vars["migration_crowding_mult_applied"] = inp.crowding / P.MIGRATION_CROWDING_PULL_PER_MULT
    return eng


BANDS = [range(a, a + 5) for a in range(0, 85, 5)] + [range(85, P.RING_YEARS + 1)]


class TestCohortScript(unittest.TestCase):
    """te_demog_seed and te_demog_step, run through _Engine, against demographics_model's seed and step."""

    INP = _with_migrant_lines(demographics_model.Inputs(sol=14, literacy=0.35, urban_share=0.2,
                                                        techs=frozenset({"medical_degrees"}),
                                                        laws=frozenset({"law_women_in_the_fields"})))
    YEAR, POP = 1836, 250000.0

    def close(self, got, want, rel=1e-9, what=""):
        self.assertLessEqual(abs(got - want), rel * max(abs(want), 1.0), f"{what}: {got} vs {want}")

    # -- the seed -------------------------------------------------------------------------------

    def seed_both(self, inp=None):
        base = inp or self.INP
        eng = _engine_for(base, self.YEAR, self.POP)
        eng.call("te_demog_seed")
        # the script reads the growth factor from a table of growth_factor; the model takes the same d
        with unittest.mock.patch.object(demographics_model, "growth_factor", lambda nrr: eng.locals["te_dg_d"]):
            ring = demographics_model.seed(base, self.YEAR, self.POP)
        return eng, ring

    def test_seed_rates_match_the_model(self):
        eng, _ring = self.seed_both()
        qf, qm, mmr = demographics_model.group_rates(self.INP)
        lt_f, lt_m = demographics_model.life_table(qf), demographics_model.life_table(qm)
        e0 = (lt_f["e0"] + lt_m["e0"]) / 2
        tfr = demographics_model.fertility(self.INP, e0)["tfr"]
        self.close(eng.vars["te_dg_e0f"], lt_f["e0"], what="e0 women")
        self.close(eng.vars["te_dg_e0m"], lt_m["e0"], what="e0 men")
        self.close(eng.vars["te_dg_e0"], e0, what="e0")
        self.close(eng.vars["te_dg_e65"], (lt_f["e65"] + lt_m["e65"]) / 2, what="e65")
        self.close(eng.vars["te_dg_imr"], (qf[0] + qm[0]) / 200, what="infant mortality")
        self.close(eng.vars["te_dg_tfr"], tfr, what="TFR")
        self.close(eng.locals["te_dg_mmr"], mmr, what="maternal deaths per 100,000 births")
        nrr = demographics_model.nrr(tfr, qf)
        self.close(eng.locals["te_dg_nrr"], nrr, what="NRR")
        self.close(eng.locals["te_dg_d"], demographics_model.growth_factor(nrr), rel=1e-4, what="growth factor")

    def test_seed_ring_matches_the_model(self):
        eng, ring = self.seed_both()
        self.close(eng.vars["te_dg_scale"], 1.0, what="scale")
        self.assertEqual(eng.vars["te_dg_raw"], self.POP)
        self.assertEqual(eng.vars["te_dg_people"], self.POP)
        self.assertEqual(eng.vars["te_dg_year"], self.YEAR)
        self.assertEqual((eng.vars["te_dg_pf"], eng.vars["te_dg_pm"], eng.vars["te_dg_births"]), (0, 0, 0))
        total = 0.0
        for a, f, m in ring.by_age()[:-1]:
            k = (self.YEAR - a) % P.RING_YEARS
            if f"te_dg_f{k}" not in eng.vars:   # fewer than 1 in 100,000 newborns reach this age
                self.assertLess(f + m, 1e-5 * self.POP, f"age {a} left empty")
                continue
            self.close(eng.vars[f"te_dg_f{k}"], f, rel=1e-4, what=f"women aged {a}")
            self.close(eng.vars[f"te_dg_m{k}"], m, rel=1e-4, what=f"men aged {a}")
            total += eng.vars[f"te_dg_f{k}"] + eng.vars[f"te_dg_m{k}"]
        self.close(total, self.POP, what="the ring's people")
        for c in range(len(P.MIGRANT_CLASSES)):
            self.close(eng.vars[f"te_dg_cf{c}"], ring.class_f[c], rel=1e-4, what=f"class {c} women")
            self.close(eng.vars[f"te_dg_cm{c}"], ring.class_m[c], rel=1e-4, what=f"class {c} men")
        self.close(eng.vars["te_dg_faw"], ring.faw, rel=1e-4, what="the pool's women")
        self.close(eng.vars["te_dg_fam"], ring.fam, rel=1e-4, what="the pool's men")
        rows = ring.by_age()
        for b, ages in enumerate(BANDS):
            self.close(eng.vars[f"te_dg_bf{b}"], sum(f for a, f, _m in rows if a in ages), rel=1e-4, what=f"band {b}")
            self.close(eng.vars[f"te_dg_bm{b}"], sum(m for a, _f, m in rows if a in ages), rel=1e-4, what=f"band {b}")

    def test_the_pyramid_scale_is_stored_with_the_figures(self):
        """Review on #830: the bars read te_dg_pyr_max, written once at the census, instead of a
        script value that reads all 36 bands in every bar's range each frame."""
        eng = _engine_for(self.INP, 1836, self.POP)
        eng.call("te_demog_seed")
        bands = [eng.vars[f"te_dg_b{s}{b}"] for s in "fm" for b in range(18)]
        self.assertAlmostEqual(eng.vars["te_dg_pyr_max"], max(bands))
        gui = _text(ROOT / "gui" / "te_demographics_widgets.gui")
        self.assertNotIn("ScriptValue('te_demog_pyramid_max')", gui)
        self.assertNotIn("ScriptValue('te_demog_state_pyramid_max')", gui)
        # 4 in the row type and 2 in each of the state's 18 rows; phase 3 adds the state's 18 biological rows (late-game §6.2)
        self.assertEqual(gui.count("Var('te_dg_pyr_max').GetValue"), 76)
        census = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertGreater(census.index("set_variable = { name = te_dg_pyr_max value = te_demog_pyramid_max }"),
                           census.index("te_demog_project = yes"), "after the outline, which shares the scale")

    def test_seed_figures_match_the_model(self):
        eng, ring = self.seed_both()
        s = demographics_model.structure(ring)
        self.close(eng.vars["te_dg_young_share"], s["young"], rel=1e-4, what="0-14")
        self.close(eng.vars["te_dg_working_share"], s["working"], rel=1e-4, what="15-64")
        self.close(eng.vars["te_dg_old_share"], s["old"], rel=1e-4, what="65+")
        self.close(eng.vars["te_dg_dependency"], (s["young"] + s["old"]) / s["working"], rel=1e-4, what="dependency")
        self.close(eng.vars["te_dg_sex_balance"], s["men_per_100_women"], rel=1e-4, what="men per 100 women")
        self.assertLess(abs(eng.vars["te_dg_median"] - s["median"]), 0.5, "median (bands vs single years)")
        women_15_49 = sum(f for a, f, _m in ring.by_age() if 15 <= a <= 49)
        self.close(eng.vars["te_dg_w1549"], women_15_49, rel=1e-4, what="women 15-49")
        self.assertFalse("te_dg_prev_median" in eng.vars, "a first census has no previous figures")
        eng.vars["te_dg_median"] = 99.0
        eng.call("te_demog_state_figures")
        self.assertFalse("te_dg_prev_median" in eng.vars, "a seed's figures are no year to compare with")
        eng.vars["te_dg_stepped"] = 1.0   # as after a step
        eng.vars["te_dg_median"] = 99.0
        eng.call("te_demog_state_figures")
        self.assertEqual(eng.vars["te_dg_prev_median"], 99.0)

    def test_reseed_clears_ages_nobody_reaches(self):
        eng = _engine_for(self.INP, self.YEAR, self.POP)
        for k in range(P.RING_YEARS):
            eng.vars[f"te_dg_f{k}"] = eng.vars[f"te_dg_m{k}"] = 1.0
        eng.call("te_demog_seed")
        oldest = (self.YEAR - 149) % P.RING_YEARS
        self.assertNotIn(f"te_dg_f{oldest}", eng.vars)
        self.assertNotIn(f"te_dg_m{oldest}", eng.vars)

    # -- the step -------------------------------------------------------------------------------

    def step_both(self, war_dead=0.0, kills=0.0, migration=0.0, stub_flows=True, scale=1.03, empty_from=None,
                  flows=None, entry="te_demog_step", engine=None, on_top=None, full=False, inp=None,
                  pool=(12.0, 7.0), men_factor=None, old_census=False, causes=None):
        """One step from the same state on both sides: the model's seed at a scale off 1, with
        people in the two oldest cohorts and in the pool. The flows reach the script one of two ways:
        stub_flows feeds war_dead, kills and migration through a te_demog_flows built from the
        model's own formulas (it tests the step alone); flows= runs the script's own te_demog_flows
        from the state's variables, against the same flows given to the model. flows is a dict:
          eb, ed (the engine's births and deaths), migration (the residual before the noise rule),
          crisis, fjob_share, techs (added to INP's), and the optional pending war (te_dg_war_in),
          kills (te_dg_kills_in) and inflow_years, left out = the variable doesn't exist.
        empty_from: nobody from that age up (the slots hold no variable; the pool keeps its people),
        the ring of the game's first decades, when the open slot is empty at the fold.
        on_top = (births, deaths): the share by which the engine's expected events over the window ran
        above the model's rates M aimed at (phase 2 step 4); full = the rule's Full setting, under which
        alone the step takes those as its on-top scales. inp: the inputs (default INP); pool: (women, men) in the pool
        (phase 2 step 1's figures count it). men_factor scales the men aged 20-59 (phase 2 step 4's sex balance: the
        census's te_dg_sex_balance is the ring's, as its last census stored it); old_census gives the script a census
        from before step 4, with the 18-40 sums' names (te_dg_m1840, te_dg_f1840) holding the pool's sums. causes (Causes
        of Death, owner 2026-10-22; with on_top under Full): {cause: its deaths on top over the window}, the walk's split
        (te_dg_ot_<c>), which the model takes as its shares of the target."""
        base = inp or self.INP
        ring = demographics_model.seed(base, self.YEAR, self.POP)
        ring.f = [x * ring.scale / scale for x in ring.f]
        ring.m = [x * ring.scale / scale for x in ring.m]
        ring.scale = scale
        folds = (self.YEAR + 1) % P.RING_YEARS          # aged 149 now, 150 at the step
        ring.f[folds], ring.m[folds] = 40.0, 25.0
        last = (self.YEAR + 2) % P.RING_YEARS           # aged 148 now: 149 after, out of the class sums
        ring.f[last], ring.m[last] = 30.0, 20.0
        if empty_from is not None:
            for a in range(empty_from, P.RING_YEARS):
                ring.f[(self.YEAR - a) % P.RING_YEARS] = ring.m[(self.YEAR - a) % P.RING_YEARS] = 0.0
        ring.pool_f, ring.pool_m, ring.pool_age = pool[0], pool[1], 152.5
        if men_factor is not None:
            for a in range(20, 60):
                ring.m[(self.YEAR - a) % P.RING_YEARS] *= men_factor
        demographics_model._refresh_denominators(ring)
        ring.total = ring.people()
        balance = demographics_model.structure(ring)["men_per_100_women"]
        before = (list(ring.f), list(ring.m))
        pop = ring.total * 1.004
        inp = base
        fixtures = {}
        if flows is not None:
            stub_flows = False
            inp = _with_migrant_lines(dataclasses.replace(
                base, techs=base.techs | flows.get("techs", frozenset()), crisis=flows["crisis"],
                inflow_years=flows.get("inflow_years") or 0, female_job_share=flows["fjob_share"]))
            war_dead, kills = flows.get("war") or 0.0, flows.get("kills") or 0.0
            # the residual the script reads, and what the model is told: a residual inside the noise band is none
            pop = ring.total + flows["eb"] - flows["ed"] - war_dead - kills + flows["migration"]
            migration = 0.0 if abs(flows["migration"]) < P.RESIDUAL_NOISE_SHARE * ring.total else flows["migration"]
            # the transport term is the script's own read of the techs' line (modifier:, from _mod_fixtures)
            fixtures = {"te_demog_crisis": flows["crisis"]}
        stub = None
        if stub_flows:
            # the profile as the model's step reads it: with the ring's last count of women among the workers
            prof = demographics_model.migrant_profile(
                inp if inp.work_female_share is not None else dataclasses.replace(inp, work_female_share=ring.fws_work))
            locals_ = {
                # the people, which the Causes of Death slices take (issue #1029), then the rates the sweep reads
                "te_dg_war": war_dead,
                "te_dg_kills": kills,
                "te_dg_war_ff": min(0.5, war_dead * (1 - P.WAR_DEAD_MALE_SHARE) / ring.faw),
                "te_dg_war_fm": min(0.5, war_dead * P.WAR_DEAD_MALE_SHARE / ring.fam),
                "te_dg_kill": min(0.9, kills / ring.total),
                "te_dg_mig_in": max(migration, 0.0),
                "te_dg_mig_out": max(-migration, 0.0),
            }
            for c in range(len(P.MIGRANT_CLASSES)):
                locals_[f"te_dg_pf{c}"], locals_[f"te_dg_pm{c}"] = prof[(c, "f")], prof[(c, "m")]
            # the booking's cap reads the profile and the class sums (te_demog_migrant_rates, 2026-10-12)
            stub = {"te_demog_flows": "\n".join([f"set_local_variable = {{ name = {k} value = {v!r} }}"
                                                 for k, v in locals_.items()] + ["te_demog_migrant_rates = yes"])}
        eng = _engine_for(inp, self.YEAR + 1, pop, effects=stub, engine=engine)
        eng.fixtures.update(fixtures)
        # the census's last sex balance and class sums, before the step rewrites them (the migrant booking reads both)
        eng.balance_before = balance
        eng.ring_before = copy.deepcopy(ring)
        bz = dz = 0.0
        shares = None
        if full:
            eng.trigger_fixtures["te_demog_effects_run"] = True
        if on_top is not None:
            assert flows is None, "the on-top scales and the script's own flows both write te_dg_eb"
            # the model's rates M aimed at, and the engine's expected events over the window at today's people
            want_b, want_d = 40.0 * pop / 1000, 30.0 * pop / 1000
            eng.vars.update(te_dg_cbr_model=40.0, te_dg_cdr_model=30.0,
                            te_dg_eb=want_b * (1 + on_top[0]), te_dg_ed=want_d * (1 + on_top[1]))
            if full:
                bz = demographics_model.on_top_scale(want_b * (1 + on_top[0]), want_b)
                dz = demographics_model.on_top_scale(want_d * (1 + on_top[1]), want_d)
            if causes is not None:
                assert full, "the split by cause is Full's"
                for c, v in causes.items():
                    eng.vars[f"te_dg_ot_{c}"] = v
                shares = demographics_model.on_top_shares(causes, want_d)
        for k in range(P.RING_YEARS):
            if before[0][k] or before[1][k]:
                eng.vars[f"te_dg_f{k}"], eng.vars[f"te_dg_m{k}"] = before[0][k], before[1][k]
        eng.vars.update(te_dg_pf=ring.pool_f, te_dg_pm=ring.pool_m, te_dg_pa=ring.pool_age, te_dg_scale=scale,
                        te_dg_year=self.YEAR, te_dg_people=ring.total, te_dg_raw=ring.total / scale,
                        te_dg_sex_balance=balance)
        if old_census:
            eng.vars.update(te_dg_f1840=ring.faw, te_dg_m1840=ring.fam)
        else:
            eng.vars.update(te_dg_faw=ring.faw, te_dg_fam=ring.fam)
        # the last count of women among the workers, which the step reads (te_demog_women_worker_share, 2026-10-25)
        if ring.fws_work is not None:
            eng.vars["te_dg_fws_wk"] = ring.fws_work
        for c in range(len(P.MIGRANT_CLASSES)):
            eng.vars[f"te_dg_cf{c}"], eng.vars[f"te_dg_cm{c}"] = ring.class_f[c], ring.class_m[c]
        # the last count's bands, which the deaths-by-cause estimate reads (issue #1029)
        for b, (bf, bm) in enumerate(zip(*demographics_model.band_sums(ring))):
            eng.vars[f"te_dg_bf{b}"], eng.vars[f"te_dg_bm{b}"] = bf, bm
        if flows is not None:
            eng.vars.update(te_dg_pop_last=ring.total, te_dg_eb=flows["eb"], te_dg_ed=flows["ed"],
                            te_dg_fjob_share=flows["fjob_share"])
            for name, key in (("te_dg_war_in", "war"), ("te_dg_kills_in", "kills"),
                              ("te_dg_inflow_years", "inflow_years")):
                if flows.get(key) is not None:
                    eng.vars[name] = float(flows[key])
        eng.call(entry)
        figures = demographics_model.step(ring, inp, self.YEAR + 1, engine_pop=pop, war_dead=war_dead,
                                          kills=kills, migration=migration, births_scale=bz, deaths_scale=dz,
                                          deaths_shares=shares)
        return eng, ring, figures, pop

    def check_step(self, eng, ring, figures, pop):
        self.close(eng.vars["te_dg_births"], figures["births"], what="births")
        self.close(eng.vars["te_dg_deaths"], figures["deaths"], what="deaths")
        # the script drops a cohort under half a person; the model keeps it
        kept = demographics_model.Ring(year=ring.year, scale=1.0)
        for k in range(P.RING_YEARS):
            a = ring.age_of_slot(k)
            if f"te_dg_f{k}" not in eng.vars:
                self.assertTrue(ring.f[k] < 0.5 and ring.m[k] < 0.5, f"age {a} dropped with people in it")
                continue
            self.close(eng.vars[f"te_dg_f{k}"], ring.f[k], what=f"women aged {a}")
            self.close(eng.vars[f"te_dg_m{k}"], ring.m[k], what=f"men aged {a}")
            kept.f[k], kept.m[k] = ring.f[k], ring.m[k]
        self.close(eng.vars["te_dg_pf"], ring.pool_f, what="pool women")
        self.close(eng.vars["te_dg_pm"], ring.pool_m, what="pool men")
        self.close(eng.vars["te_dg_pa"], ring.pool_age, what="pool's mean age")
        kept.pool_f, kept.pool_m = ring.pool_f, ring.pool_m
        raw = sum(kept.f) + sum(kept.m) + kept.pool_f + kept.pool_m
        self.close(eng.vars["te_dg_raw"], raw, what="raw ring")
        kept.scale = pop / raw
        self.close(eng.vars["te_dg_scale"], kept.scale, what="scale")
        self.close(eng.vars["te_dg_people"], pop, what="people")
        self.assertEqual(eng.vars["te_dg_year"], self.YEAR + 1)
        demographics_model._refresh_denominators(kept)
        for c in range(len(P.MIGRANT_CLASSES)):
            self.close(eng.vars[f"te_dg_cf{c}"], kept.class_f[c], what=f"class {c} women")
            self.close(eng.vars[f"te_dg_cm{c}"], kept.class_m[c], what=f"class {c} men")
        self.close(eng.vars["te_dg_faw"], kept.faw, what="the pool's women")
        self.close(eng.vars["te_dg_fam"], kept.fam, what="the pool's men")
        rows = kept.by_age()
        for b, ages in enumerate(BANDS):
            self.close(eng.vars[f"te_dg_bf{b}"], sum(f for a, f, _m in rows if a in ages), what=f"band {b} women")
            self.close(eng.vars[f"te_dg_bm{b}"], sum(m for a, _f, m in rows if a in ages), what=f"band {b} men")

    def test_step_without_flows(self):
        """The script's own te_demog_flows with nothing to flow: no pending dead, a residual of 0."""
        eng, *rest = self.step_both(flows=dict(eb=0.0, ed=0.0, crisis=0.0, fjob_share=0.3, migration=0.0))
        self.check_step(eng, *rest)
        self.assertEqual(eng.vars["te_dg_net_migration"], 0.0)
        self.assertEqual(eng.vars["te_dg_inflow_years"], 0.0)

    def test_step_with_war_kills_and_immigration(self):
        self.check_step(*self.step_both(war_dead=900.0, kills=1500.0, migration=4000.0))

    def test_step_with_war_kills_and_emigration(self):
        self.check_step(*self.step_both(war_dead=300.0, kills=200.0, migration=-6000.0))

    def test_console_replay_is_the_step_with_its_lines_between(self):
        """te_debug_demog.1 option a (te_debug_demog_replay) runs the step's two halves apart and logs
        between them. It must leave the state as te_demog_step does; log the head with the flows the
        sweep then used, and the ring before the sweep rewrote te_dg_people and te_dg_scale; and remove
        its te_dg_dbg_ copies. A wrong local name in its copies reads an unset local and fails here."""
        for migration, sign in ((-6000.0, " mig=-["), (5000.0, " mig=[")):
            with self.subTest(migration=migration):
                flows = dict(eb=1200.0, ed=900.0, crisis=0.05, fjob_share=0.3, migration=migration, war=400.0,
                             kills=30.0)
                ref, _ring, _figures, pop = self.step_both(flows=flows)
                eng, *_ = self.step_both(flows=flows, entry="te_debug_demog_replay", engine=_ConsoleEngine)
                self.assertEqual(set(eng.vars), set(ref.vars), "the console's copies are all removed")
                for name, want in ref.vars.items():
                    self.close(eng.vars[name], want, what=name)
                self.assertEqual([line[:20] for line, _ in eng.logs],
                                 ["TE_DEMOG_REPLAY head", "RING_BEFORE", "RING_AFTER"])
                head, at_head = eng.logs[0]
                self.assertIn(sign, head)
                self.close(at_head["te_dg_dbg_war"], 400.0, what="war dead")
                self.close(at_head["te_dg_dbg_kills"], 30.0, what="kills")
                self.close(at_head["te_dg_dbg_mig"], migration, what="migration")
                for mine, theirs in (("tfr", "te_dg_tfr"), ("mmr", "te_dg_m_mat"), ("m_inf", "te_dg_m_inf"),
                                     ("m_ext", "te_dg_m_ext"), ("m_chr", "te_dg_m_chr")):
                    self.close(at_head[f"te_dg_dbg_{mine}"], ref.vars[theirs], what=mine)
                self.close(sum(at_head[f"te_dg_dbg_p{s}{c}"] for s in "fm" for c in range(len(P.MIGRANT_CLASSES))),
                           1.0, rel=1e-6, what="profile")
                before, after = eng.logs[1][1], eng.logs[2][1]
                self.assertEqual(before["te_dg_scale"], 1.03, "the before ring is logged before the sweep")
                self.close(after["te_dg_people"], pop, what="people after")
                self.close(after["te_dg_scale"], ref.vars["te_dg_scale"], what="scale after")

    def test_step_with_an_empty_open_slot_and_old_ages(self):
        """Nobody aged 90 and over: empty slots are skipped while the trackers advance, and the
        pool ages and scales with nobody folding into it."""
        eng, ring, figures, pop = self.step_both(war_dead=500.0, kills=800.0, migration=2000.0, empty_from=90)
        self.check_step(eng, ring, figures, pop)
        for a in range(91, P.RING_YEARS):
            self.assertNotIn(f"te_dg_f{(self.YEAR + 1 - a) % P.RING_YEARS}", eng.vars, f"age {a}")
        self.assertIn(f"te_dg_f{(self.YEAR + 1) % P.RING_YEARS}", eng.vars, "the open slot takes the births")

    def test_step_with_emigration_at_the_cap(self):
        """Departures over half a cohort's survivors stop at half (demographics_model.step)."""
        eng, ring, figures, pop = self.step_both(migration=-0.45 * self.POP)
        self.check_step(eng, ring, figures, pop)

    # -- the script's own flows (te_demog_flows) ------------------------------------------------

    def check_flows(self, eng, flows, want_inflow_years):
        """The flow locals te_demog_flows set equal the model's war shares, kill share, migrant
        split and profile, and it consumed what was pending."""
        inp = _with_migrant_lines(dataclasses.replace(
            self.INP, techs=self.INP.techs | flows.get("techs", frozenset()), crisis=flows["crisis"],
            inflow_years=flows.get("inflow_years") or 0, female_job_share=flows["fjob_share"],
            work_female_share=eng.ring_before.fws_work))   # the last count the step read (2026-10-25)
        sign = 1 if eng.locals["te_dg_mig_in"] > 0 else -1 if eng.locals["te_dg_mig_out"] > 0 else 0
        prof = demographics_model.migrant_profile(inp, eng.balance_before, sign)
        # the booking's rates (te_demog_migrant_rates, 2026-10-12): each class and sex's, plus the flat one
        migration = eng.locals["te_dg_mig_in"] - eng.locals["te_dg_mig_out"]
        rates = demographics_model.migrant_rates(eng.ring_before, prof, migration)
        flat = eng.locals["te_dg_mig_flat"]
        for (c, sex), rate in rates.items():
            if abs(rate):
                self.close(eng.locals[f"te_dg_mr_{sex}{c}"] + flat, abs(rate), rel=1e-4,
                           what=f"booking rate, class {c} {sex}")
        for c in range(len(P.MIGRANT_CLASSES)):
            self.close(eng.locals[f"te_dg_pf{c}"], prof[(c, "f")], rel=1e-9, what=f"profile, class {c} women")
            self.close(eng.locals[f"te_dg_pm{c}"], prof[(c, "m")], rel=1e-9, what=f"profile, class {c} men")
        self.close(sum(eng.locals[f"te_dg_p{s}{c}"] for s in "fm" for c in range(len(P.MIGRANT_CLASSES))), 1.0,
                   what="the profile sums to 1")
        for name in ("te_dg_war_in", "te_dg_kills_in"):
            self.assertNotIn(name, eng.vars, f"{name} is taken once")
        self.assertEqual(eng.vars["te_dg_inflow_years"], want_inflow_years)

    def test_flows_for_immigration_with_war_dead_and_kills(self):
        flows = dict(eb=2500.0, ed=2100.0, migration=4000.0, crisis=0.2, fjob_share=0.4, war=900.0, kills=1500.0,
                     inflow_years=12, techs=frozenset({"railways", "paddle_steamer"}))   # past chain migration's cap
        eng, ring, figures, pop = self.step_both(flows=flows)
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=13)
        self.close(eng.vars["te_dg_net_migration"], 4000.0, what="net migration")
        self.assertGreater(eng.locals["te_dg_mig_in"], 0)
        self.assertEqual(eng.locals["te_dg_mig_out"], 0)

    def test_flows_for_emigration(self):
        flows = dict(eb=2500.0, ed=2100.0, migration=-6000.0, crisis=0.35, fjob_share=0.1, war=300.0, inflow_years=5)
        eng, ring, figures, pop = self.step_both(flows=flows)
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=0)
        self.close(eng.vars["te_dg_net_migration"], -6000.0, what="net migration")
        self.close(eng.vars["te_dg_mig_raw"], -6000.0, what="the residual before the noise band")
        self.assertEqual(eng.locals["te_dg_mig_in"], 0)
        self.assertGreater(eng.locals["te_dg_mig_out"], 0)

    def test_flows_ignore_a_residual_inside_the_noise_band(self):
        """0.2% of the people is model error: no migrants, and the inflow streak ends."""
        flows = dict(eb=2500.0, ed=2100.0, migration=0.002 * self.POP, crisis=0.0, fjob_share=0.3, inflow_years=4)
        eng, ring, figures, pop = self.step_both(flows=flows)
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=0)
        self.assertEqual(eng.vars["te_dg_net_migration"], 0.0)
        # the census log's gate check reads the residual before the band (te_debug_demog_census_line)
        self.close(eng.vars["te_dg_mig_raw"], 0.002 * self.POP, what="the residual before the noise band")
        flows["migration"] = 0.004 * self.POP
        eng, ring, figures, pop = self.step_both(flows=flows)
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=5)
        self.assertGreater(eng.vars["te_dg_net_migration"], 0)

    def test_flows_balance_the_labour_split_where_men_are_few(self):
        """The migrant booking (2026-10-12): departures from a state short of men take the labour kind's women and men
        alike (demographics_model.labour_balance_weight), and the step still matches the model."""
        flows = dict(eb=2500.0, ed=2100.0, migration=-6000.0, crisis=0.0, fjob_share=0.0)
        eng, ring, figures, pop = self.step_both(flows=flows, men_factor=0.85)
        self.assertLess(eng.balance_before, P.LABOUR_BALANCE_LOW[1])
        self.close(eng.locals["te_dg_lbw"], 1.0, what="the balance weight")
        self.close(eng.locals["te_dg_labour_f"], P.LABOUR_BALANCE_SHARE, what="labour's women's share")
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=0)
        # the same state gaining people keeps the jobs' split: the correction only stops a fall
        flows["migration"] = 6000.0
        eng, ring, figures, pop = self.step_both(flows=flows, men_factor=0.85)
        self.close(eng.locals["te_dg_lbw"], 0.0, what="no correction on arrivals")
        self.close(eng.locals["te_dg_labour_f"], P.LABOUR_FEMALE_SHARE_MIN, what="labour's women's share")
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=1)

    def test_flows_balance_the_labour_split_where_men_are_many(self):
        """Arrivals in a state with men to spare move toward the balanced split, part of the way inside the ramp."""
        flows = dict(eb=2500.0, ed=2100.0, migration=6000.0, crisis=0.0, fjob_share=0.0)
        eng, ring, figures, pop = self.step_both(flows=flows, men_factor=1.15)
        start, full = P.LABOUR_BALANCE_HIGH
        want = (eng.balance_before - start) / (full - start)
        self.assertTrue(0 < want < 1, eng.balance_before)
        self.close(eng.locals["te_dg_lbw"], want, rel=1e-4, what="the balance weight")
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=1)

    def test_flows_past_the_booking_cap(self):
        """A residual far past the cap: the classes stop at the cap and the rest is flat (te_demog_migrant_rates)."""
        for migration in (-0.2 * self.POP, 0.3 * self.POP):
            flows = dict(eb=2500.0, ed=2100.0, migration=migration, crisis=0.1, fjob_share=0.2)
            eng, ring, figures, pop = self.step_both(flows=flows)
            self.assertGreater(eng.locals["te_dg_mig_flat"], 0.05)
            cap = P.MIGRANT_CAP_IN if migration > 0 else P.MIGRANT_CAP_OUT
            self.close(eng.locals["te_dg_mr_m2"], cap, rel=1e-4, what="young men at the cap")
            self.check_step(eng, ring, figures, pop)
            self.check_flows(eng, flows, want_inflow_years=1 if migration > 0 else 0)

    def test_flows_with_a_first_year_state_and_a_full_crisis(self):
        """No pending dead or kills, no streak variable yet; refugees take the whole profile."""
        flows = dict(eb=2500.0, ed=2100.0, migration=3000.0, crisis=1.0, fjob_share=0.3)
        eng, ring, figures, pop = self.step_both(flows=flows)
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=1)
        self.close(eng.locals["te_dg_labour"], 0.0, what="labour migrants")
        self.close(eng.locals["te_dg_family"], 0.0, what="families")

    def test_flows_hit_the_caps(self):
        """The war share stops at half a cohort, the kill share at 0.9."""
        war, kills = 5.0 * self.POP, 0.95 * self.POP
        flows = dict(eb=0.0, ed=0.0, migration=war + kills, crisis=0.0, fjob_share=0.3, war=war, kills=kills)
        eng, *_rest = self.step_both(flows=flows)
        self.assertEqual(eng.locals["te_dg_war_fm"], 0.5)
        self.assertEqual(eng.locals["te_dg_war_ff"], 0.5)
        self.assertEqual(eng.locals["te_dg_kill"], 0.9)

    def test_a_seed_drops_the_flows_pending_before_it(self):
        eng = _engine_for(self.INP, self.YEAR, self.POP)
        eng.vars.update(te_dg_war_in=500.0, te_dg_kills_in=80.0)
        eng.call("te_demog_seed")
        self.assertNotIn("te_dg_war_in", eng.vars)
        self.assertNotIn("te_dg_kills_in", eng.vars)

    # -- the orchestrator -----------------------------------------------------------------------

    def test_orchestrator_dispatch(self):
        stubs = {"te_demog_walks": "", "te_inh_refresh_rural_effects": "", "te_demog_wc_state_yearly": "",
                 "te_inh_refresh_wc_state_effects": "",
                 "te_demog_seed": "set_variable = { name = did value = 1 }",
                 "te_demog_step": "set_variable = { name = did value = 2 }"}
        cases = [   # (census year, raw, people, people at the census, rule on) -> seed 1, step 2, nothing None
            ((None, None, 1000.0, None, True), 1),
            ((1836, 900.0, 1000.0, 1000.0, True), 2),
            ((1837, 900.0, 1000.0, 1000.0, True), None),
            ((1834, 900.0, 1000.0, 1000.0, True), 1),
            ((1836, 0.5, 1000.0, 1000.0, True), 1),
            ((1836, 0.5, 0.0, 0.0, True), 2),
            ((None, None, 1000.0, None, False), None),
            # people far off the last census's: a step all the same (owner, 2026-10-20), which books the move as
            # migration; until then a move of more than a quarter seeded again
            ((1836, 900.0, 1251.0, 1000.0, True), 2),
            ((1836, 900.0, 749.0, 1000.0, True), 2),
            ((1836, 900.0, 5740.0, 1000.0, True), 2),
            ((1836, 900.0, 250.0, 1000.0, True), 2),
            ((1837, 900.0, 1400.0, 1000.0, True), None),
        ]
        for (census, raw, pop, pop_last, rule), want in cases:
            eng = _Engine({"year": 1837.0, "state_population": pop}, triggers={"te_demog_cohorts_run": rule},
                          effects=stubs)
            if census is not None:
                eng.vars.update(te_dg_year=float(census), te_dg_raw=raw, te_dg_pop_last=pop_last)
            eng.call("te_demog_state_yearly")
            self.assertEqual(eng.vars.get("did"), want, (census, raw, pop, pop_last, rule))

    def test_a_big_move_is_stepped_and_booked_as_migration(self):
        """No size test (owner, 2026-10-20): the census pulse steps a state whose people grew 5.7 times (Kars in the
        owner's 2057 game) or fell by 70%, and the step books the move by the model's own rule (the profile up to
        MIGRANT_CAP_IN or _OUT of each class and sex, the rest flat), keeping the year's births and deaths."""
        for factor in (5.74, 0.3):
            with self.subTest(factor=factor):
                flows = dict(eb=1200.0, ed=900.0, crisis=0.0, fjob_share=0.3,
                             migration=(factor - 1.0) * self.POP)
                eng, ring, figures, pop = self.step_both(flows=flows, entry="te_demog_state_census")
                self.assertEqual(eng.vars["te_dg_stepped"], 1, "a step, not a seed")
                self.assertGreater(eng.vars["te_dg_births"], 0.0)
                self.check_step(eng, ring, figures, pop)
                self.close(eng.vars["te_dg_net_migration"], flows["migration"], what="net migration")

    # -- phase 2 step 4: the on-top scales (te_demog_on_top_scales) -----------------------------

    def test_step_with_on_top_scales_matches_the_model(self):
        eng, ring, figures, pop = self.step_both(on_top=(0.05, 0.12), full=True)
        self.check_step(eng, ring, figures, pop)
        self.assertAlmostEqual(eng.vars["te_dg_bz"], 0.05, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_dz"], 0.12, places=5)
        self.close(eng.vars["te_dg_cbr_model"], figures["births_model"] * 1000 / pop, what="cbr_model")
        self.close(eng.vars["te_dg_cdr_model"], figures["deaths_model"] * 1000 / pop, what="cdr_model")
        self.close(eng.vars["te_dg_tfr"], figures["tfr_shown"], what="tfr shown")
        self.close(eng.vars["te_dg_tfr_model"], figures["tfr"], what="tfr model")
        # the events the scales were measured against, kept for option n (bz = eb / eb_target - 1, clamped)
        self.close(eng.vars["te_dg_eb_target"], 40.0 * pop / 1000, what="eb target")
        self.close(eng.vars["te_dg_ed_target"], 30.0 * pop / 1000, what="ed target")

    def test_no_on_top_scales_outside_full(self):
        eng, ring, figures, pop = self.step_both(on_top=(0.05, 0.12), full=False)
        self.check_step(eng, ring, figures, pop)
        self.assertEqual((eng.vars["te_dg_bz"], eng.vars["te_dg_dz"]), (0.0, 0.0))

    def test_no_target_no_scales(self):
        """An old save, or the first step after phase 2 arrives: no te_dg_cbr_model yet."""
        eng, ring, figures, pop = self.step_both(full=True)
        self.check_step(eng, ring, figures, pop)
        self.assertEqual((eng.vars["te_dg_bz"], eng.vars["te_dg_dz"]), (0.0, 0.0))
        self.assertEqual((eng.vars["te_dg_eb_target"], eng.vars["te_dg_ed_target"]), (0.0, 0.0))

    def test_on_top_scales_have_only_their_natural_floor(self):
        """Owner, 2026-10-20: no ceiling (it was +4) and a floor of -1, no events (it was -0.9)."""
        eng, ring, figures, pop = self.step_both(on_top=(9.0, -0.99), full=True)
        self.check_step(eng, ring, figures, pop)
        self.assertAlmostEqual(eng.vars["te_dg_bz"], 9.0, places=4)
        self.assertAlmostEqual(eng.vars["te_dg_dz"], -0.99, places=4)
        self.close(eng.vars["te_dg_cbr_model"], figures["births_model"] * 1000 / pop, what="cbr_model")
        self.close(eng.vars["te_dg_cdr_model"], figures["deaths_model"] * 1000 / pop, what="cdr_model")

    def test_no_events_keep_the_models_own_rate(self):
        """1 + bz or 1 + dz under te_demog_k_on_top_factor_min (the engine gave no births or no deaths, a state line of
        -1 or below): the ring's events can't give the model's rate back, so the target M aims at stays the last one
        (demographics_model.step returns None), while the other kind's is read back as usual."""
        eng, ring, figures, pop = self.step_both(on_top=(-1.0, 0.1), full=True)
        self.check_step(eng, ring, figures, pop)
        self.assertEqual(eng.vars["te_dg_bz"], -1.0)
        self.assertEqual(eng.vars["te_dg_births"], 0.0)
        self.assertIsNone(figures["births_model"])
        self.assertEqual(eng.vars["te_dg_cbr_model"], 40.0, "the last step's own rate stays")
        self.close(eng.vars["te_dg_cdr_model"], figures["deaths_model"] * 1000 / pop, what="cdr_model")
        eng, ring, figures, pop = self.step_both(on_top=(0.1, -1.0), full=True)
        self.check_step(eng, ring, figures, pop)
        self.assertEqual(eng.vars["te_dg_dz"], -1.0)
        self.assertIsNone(figures["deaths_model"])
        self.assertEqual(eng.vars["te_dg_cdr_model"], 30.0, "the last step's own rate stays")
        self.close(eng.vars["te_dg_cbr_model"], figures["births_model"] * 1000 / pop, what="cbr_model")

    def test_a_seed_clears_the_target_and_the_scales(self):
        """A seed (a merge, a split, a census gap) starts the census's target over: the model's rates from before it
        are another state's or years stale, and would scale the next step's births and deaths by their ratio to
        today's. Without them that step takes no on-top scales (test_no_target_no_scales). The seed's children per
        woman is the model's own, so te_dg_tfr_model is set for the projection."""
        eng = _engine_for(self.INP, self.YEAR, self.POP)
        eng.vars.update(te_dg_cbr_model=25.0, te_dg_cdr_model=20.0, te_dg_bz=0.3, te_dg_dz=-0.2, te_dg_tfr_model=9.0,
                        te_dg_eb_target=900.0, te_dg_ed_target=800.0)
        eng.call("te_demog_seed")
        self.assertNotIn("te_dg_cbr_model", eng.vars)
        self.assertNotIn("te_dg_cdr_model", eng.vars)
        self.assertEqual((eng.vars["te_dg_bz"], eng.vars["te_dg_dz"]), (0.0, 0.0))
        self.assertEqual((eng.vars["te_dg_eb_target"], eng.vars["te_dg_ed_target"]), (0.0, 0.0))
        self.assertEqual(eng.vars["te_dg_tfr_model"], eng.vars["te_dg_tfr"])

    def test_step_with_a_large_deaths_scale_matches_the_model(self):
        """dz at +9 (no ceiling since 2026-10-20) pushes the old-age groups' rates past 100,000: the script scales the
        cause multipliers before its cap, and so does the twin (demographics_model.step)."""
        eng, ring, figures, pop = self.step_both(on_top=(0.0, 9.0), full=True)
        self.check_step(eng, ring, figures, pop)
        self.assertAlmostEqual(eng.vars["te_dg_dz"], 9.0, places=4)
        self.close(eng.vars["te_dg_cdr_model"], figures["deaths_model"] * 1000 / pop, what="cdr_model")
        qf, qm, _mmr = demographics_model.group_rates(self.INP)
        capped = sum(q * (1 + 9.0) >= 100000.0 for q in qf + qm)
        self.assertGreater(capped, 0, "the test must reach the cap")

    def test_the_replay_logs_the_scaled_rates(self):
        """te_debug_demog_replay logs the locals after te_demog_step_begin, so the scales are in the head's tfr
        and multipliers and the harness's replay needs no new field."""
        body = _block(_text(EFFECTS), "te_demog_step_begin")
        self.assertLess(body.index("te_demog_prepare = yes"), body.index("te_demog_on_top_scales = yes"))
        self.assertIn("te_demog_step_begin = yes", _block(_text(CONSOLE_EFFECTS), "te_debug_demog_replay"))

    # -- phase 2 step 1: the figures (demographics_model.work_figures) ---------------------------

    WORK = dict(laws=frozenset({"law_women_in_the_fields", "law_restricted_child_labor", "law_old_age_pension"}),
                low_share=0.7, pension_age=67.0)

    def _work_inp(self, **kw):
        inp = dataclasses.replace(self.INP, **{**self.WORK, **kw})
        inp.mods = {**inp.mods, P.WOMENS_WORK_TYPE: 0.15, P.MALE_PARTICIPATION_TYPE: 0.02,
                    P.PARTICIPATION_TYPE: 0.01, P.CAPACITY_TYPE: -0.05}   # call 3's inputs ride through the figures
        return inp

    def _work_figures(self, eng, ring, inp, rel=1e-4):
        qf, qm, _ = demographics_model.group_rates(dataclasses.replace(inp, medicine=ring.medicine))
        want = demographics_model.work_figures(ring, inp, demographics_model.old_age(qf, qm))
        for name in ("wa_share", "at_work", "pensioners", "need"):
            self.close(eng.vars[f"te_dg_{name}"], want[name], rel=rel, what=name)

    def test_seed_work_figures_match_the_model(self):
        inp = self._work_inp()
        eng, ring = self.seed_both(inp=inp)
        self._work_figures(eng, ring, inp)

    def test_step_work_figures_match_the_model(self):
        inp = self._work_inp()
        eng, ring, _figures, _pop = self.step_both(inp=inp, migration=0.0)
        self._work_figures(eng, ring, inp)

    def test_ubi_ends_the_working_ages_at_the_threshold(self):
        inp = self._work_inp(laws=frozenset({"law_universal_basic_income", "law_child_labor_allowed"}),
                             pension_age=None)
        eng, ring = self.seed_both(inp=inp)
        self._work_figures(eng, ring, inp)
        self.assertEqual(eng.vars["te_dg_pensioners"], 0)

    def test_with_no_pension_law_the_pool_is_of_working_age(self):
        """D10 (the ledger's Deviation 2): with no pension law the working ages have no end, so the pool (150+) counts
        in the working ages and works at its capacity, in the step as in the model. A pool of 5,000 makes the
        difference about 2%, well past the tolerance."""
        inp = self._work_inp(laws=frozenset({"law_child_labor_allowed"}), pension_age=None)
        eng, ring, _figures, _pop = self.step_both(inp=inp, migration=0.0, pool=(3000.0, 2000.0))
        self._work_figures(eng, ring, inp)
        self.assertEqual(eng.vars["te_dg_pensioners"], 0)

    def test_the_planned_and_unplanned_values_sum_to_the_tfr(self):
        eng, _ring = self.seed_both(inp=self._work_inp())
        planned = eng.value(eng._tree(eng.values, "te_demog_tfr_planned"))
        unplanned = eng.value(eng._tree(eng.values, "te_demog_tfr_unplanned"))
        self.close(planned + unplanned, eng.value(eng._tree(eng.values, "te_demog_tfr")), rel=1e-9, what="TFR")

    def test_a_census_from_before_step_1_steps_cleanly(self):
        """Review Focus 1: an old save's state has no te_dg_low_share and its owner no pension variable."""
        inp = self._work_inp()
        eng, ring = self.seed_both(inp=inp)
        del eng.vars["te_dg_low_share"]
        eng.fixtures["te_demog_pension_age"] = float(P.PENSION_AGE["standard"])
        eng.fixtures.update(year=float(self.YEAR + 1))
        eng.call("te_demog_prepare")           # every read guarded: no "read of missing variable"
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_low_share")), 0)


    # -- phase 2 step 4: the pool, the war dead's window and the sex balance in the step ---------------------------

    @ALL_ON
    def test_a_step_short_of_men_matches_the_model(self):
        """The design §4.4: a census of 85 men per 100 women aged 20-59 (war dead, emigration) stores the balance its
        step began with (te_dg_sxb), and its children per woman and women's rate take the terms the model gives; war
        dead come from the pool's ages."""
        inp = self._work_inp()
        eng, ring, figures, pop = self.step_both(inp=inp, war_dead=2000.0, migration=0.0, men_factor=0.85)
        self.check_step(eng, ring, figures, pop)
        balance = eng.vars["te_dg_sxb"]
        self.assertLess(balance, P.SEX_FEWER_FROM)
        self.close(figures["fertility"]["sex"], balance / P.SEX_FEWER_FROM, rel=1e-6, what="the births term")
        self.close(eng.vars["te_dg_tfr"], figures["tfr"], rel=1e-6, what="children per woman")
        self._work_figures(eng, ring, dataclasses.replace(inp, sex_balance=balance))

    @unittest.mock.patch.object(P, "SEX_BALANCE_EFFECTS", False)
    def test_held_back_a_step_short_of_men_takes_no_term(self):
        """demographics_params.SEX_BALANCE_EFFECTS off (held back, as step 4 shipped): the census still counts the
        balance but stores no te_dg_sxb, and its children per woman and work figures take no sex-balance term."""
        inp = self._work_inp()
        eng, ring, figures, pop = self.step_both(inp=inp, migration=0.0, men_factor=0.85)
        self.check_step(eng, ring, figures, pop)
        self.assertNotIn("te_dg_sxb", eng.vars)
        self.assertLess(eng.vars["te_dg_sex_balance"], P.SEX_FEWER_FROM)
        self.assertEqual(figures["fertility"]["sex"], 1.0)
        self.close(eng.vars["te_dg_tfr"], figures["tfr"], rel=1e-6, what="children per woman")
        self._work_figures(eng, ring, inp)

    def test_a_balanced_step_stores_no_balance(self):
        eng, *rest = self.step_both(migration=0.0)
        self.check_step(eng, *rest)
        self.assertNotIn("te_dg_sxb", eng.vars)

    def test_a_seed_takes_no_sex_balance_term(self):
        eng = _engine_for(self.INP, self.YEAR, self.POP)
        eng.vars.update(te_dg_sxb=70.0, te_dg_sex_balance=70.0)   # a re-seed of a census short of men
        eng.call("te_demog_seed")
        self.assertNotIn("te_dg_sxb", eng.vars)
        _eng, ring = self.seed_both()
        self.close(eng.vars["te_dg_tfr"], _eng.vars["te_dg_tfr"], what="the seed's children per woman")

    def test_a_census_from_before_step_4_takes_its_war_dead_once(self):
        """An old save's state holds the 18-40 sums' names: the step's flows divide by them once, and the census that
        follows writes the pool's and removes them."""
        flows = dict(eb=1200.0, ed=900.0, crisis=0.0, fjob_share=0.3, migration=0.0, war=900.0)
        eng, ring, figures, pop = self.step_both(flows=flows, old_census=True)
        self.check_step(eng, ring, figures, pop)
        self.assertNotIn("te_dg_m1840", eng.vars)
        self.assertNotIn("te_dg_f1840", eng.vars)


class TestWorkWalk(unittest.TestCase):
    """The walk's three sums (phase 2 step 1): under the cohorts only (D5), in three gated effects (D11)."""

    def test_the_walk_calls_the_three_effects_in_place(self):
        walk = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_walks"))
        pops = walk.index("every_scope_pop = {")
        self.assertLess(walk.index("te_demog_work_walk_init = yes"), pops)
        self.assertGreater(walk.index("te_demog_work_walk_pop = yes"), pops)
        self.assertGreater(walk.index("te_demog_work_walk_store = yes"), walk.index("te_demog_gini_band_store = yes"))
        self.assertIn("limit = { te_demog_cohorts_run = yes }", _block(_text(EFFECTS), "te_demog_work_walk_init"))
        pop = _block(_text(EFFECTS), "te_demog_work_walk_pop")
        for read in ("local_var:te_dg_w_on > 0", "add = workforce", "strata = lower",
                     "multiply = te_demog_pop_base_ratio"):
            self.assertIn(read, pop)

    def test_outside_the_census_the_walk_effects_set_nothing(self):
        """The walk runs under every rule (inheritance needs it): under Disabled the three effects set no variable and
        read no pop."""
        eng = _Engine({}, triggers={"te_demog_cohorts_run": False})
        eng.locals["te_dg_w_pop"] = 1000.0
        for effect in ("te_demog_work_walk_init", "te_demog_work_walk_pop", "te_demog_work_walk_store"):
            eng.call(effect)
        self.assertEqual(eng.vars, {})

    def test_under_the_census_the_store_divides_by_the_walks_people(self):
        # the engine's figure per person (unemployment_rate_read, 2026-10-17): 50 idle of 1,000 people
        eng = _Engine({"state_unemployment_rate": 0.05}, triggers={"te_demog_cohorts_run": True})
        eng.call("te_demog_work_walk_init")
        eng.locals.update(te_dg_w_pop=1000.0, te_dg_w_low=800.0, te_dg_w_wbase=260.0, te_dg_w_wf=250.0, te_dg_w_un=50.0)
        eng.call("te_demog_work_walk_store")
        self.assertEqual((eng.vars["te_dg_low_share"], eng.vars["te_dg_wbase"], eng.vars["te_dg_wf_engine"]),
                         (0.8, 0.26, 0.25))
        self.assertEqual(eng.vars["te_dg_unemp_walk"], 0.2)   # the walk's own count: over the workforce, not the people
        # the census's figure is the shared conversion (owner, 2026-10-17); a state its own walk hasn't reached takes
        # this walk's workforce share, so the conversion matches the count
        self.assertEqual(eng.vars["te_unemp_wf_share"], 0.25)
        self.assertEqual(eng.vars["te_dg_unemp"], 0.2)

    def test_the_census_stores_the_conversion_at_the_shared_workforce_share(self):
        """Where the conversion's own walk has stored the workforce share (te_unemp_share_refresh), the census leaves it
        and divides by it, as every other reader does: one source."""
        eng = _Engine({"state_unemployment_rate": 0.06}, triggers={"te_demog_cohorts_run": True})
        eng.call("te_demog_work_walk_init")
        eng.vars["te_unemp_wf_share"] = 0.3
        eng.locals.update(te_dg_w_pop=1000.0, te_dg_w_low=800.0, te_dg_w_wbase=260.0, te_dg_w_wf=250.0, te_dg_w_un=50.0)
        eng.call("te_demog_work_walk_store")
        self.assertEqual(eng.vars["te_unemp_wf_share"], 0.3)
        self.assertAlmostEqual(eng.vars["te_dg_unemp"], 0.2)
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_unemployment")), 0.2)
        self.assertEqual(eng.vars["te_dg_unemp_walk"], 0.2)

    def test_three_pops_through_the_walk_effects(self):
        """Each pop's sums as te_demog_walks makes them, one pop at a time (TestGini.walk's pattern; the review of #923):
        an aristocrat, a slave and a lower-strata worker. _OwnerEngine knows is_pop_type (te_demog_pop_base_ratio); the
        base _Engine doesn't know strata, so this test teaches it."""

        class _PopEngine(_OwnerEngine):
            strata = None

            def _test(self, key, op, arg):
                if key == "strata":
                    return arg == self.strata
                return super()._test(key, op, arg)

        eng = _PopEngine({}, triggers={"te_demog_cohorts_run": True})
        eng.call("te_demog_work_walk_init")
        # the laborers have no workplace: the walk's count (te_dg_unemp_walk, 2026-10-17) is their workforce over all;
        # the engine's figure is their workforce over all the people (unemployment_rate_read), which the census
        # stores over the workforce share (te_dg_unemp, te_state_unemployment_share)
        eng.fixtures["state_unemployment_rate"] = 130 / 1000
        pops = (("aristocrats", "upper", 100.0, 18.0, "bg_agriculture"), ("slaves", "lower", 400.0, 210.0, "bg_mining"),
                ("laborers", "lower", 500.0, 130.0, None))
        for pop_type, strata, size, workforce, workplace in pops:
            eng.pop_type, eng.strata, eng.workplace = pop_type, strata, workplace
            eng.fixtures.update(total_size=size, workforce=workforce)
            eng.call("te_demog_work_walk_pop")
        eng.locals["te_dg_w_pop"] = 1000.0          # the walk's own people sum (te_demog_walks keeps it)
        eng.call("te_demog_work_walk_store")
        self.assertAlmostEqual(eng.vars["te_dg_low_share"], (400 + 500) / 1000)
        self.assertAlmostEqual(eng.vars["te_dg_wbase"], (100 * 0.2 + 400 * 0.5 + 500 * 0.25) / 1000)
        self.assertAlmostEqual(eng.vars["te_dg_wf_engine"], (18 + 210 + 130) / 1000)
        self.assertAlmostEqual(eng.vars["te_dg_unemp_walk"], 130 / (18 + 210 + 130))
        self.assertAlmostEqual(eng.vars["te_dg_unemp"], 130 / (18 + 210 + 130), places=4)
        # what te_demog_unemployment, and so the youth bulge, the wave, the pension AI and the panel, read
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_unemployment")), 130 / (18 + 210 + 130),
                               places=4)

    def test_the_figures_are_stored_where_the_denominator_is_whole(self):
        """D4: in the seed straight after the accumulators close, in the step after the newborns join te_dg_raw."""
        effects = _text(EFFECTS)
        seed = _block(effects, "te_demog_seed")
        self.assertLess(seed.index("te_demog_close_accumulators = yes"), seed.index("te_demog_work_finish = yes"))
        self.assertLess(seed.index("te_demog_work_finish = yes"), seed.index("te_demog_normalize_slots = yes"))
        finish = _block(effects, "te_demog_step_finish")
        self.assertLess(finish.index("change_local_variable = { name = te_dg_raw add = local_var:te_dg_births }"),
                        finish.index("te_demog_work_finish = yes"))


class TestEngineLineTypes(unittest.TestCase):
    """Owner, 2026-10-11 (docs/superpowers/archive/plans/2026-10-11-demographics-engine-lines-script-only.md): every engine birth
    and mortality line on a law, tech or institution is carried on a script-only type, named like the vanilla field it
    replaces, with vanilla's format and ai_value."""

    TYPES = ROOT / "common" / "modifier_type_definitions" / "demographics_engine_line_types.txt"

    def _vanilla_types(self):
        import json
        data = json.loads((ROOT / "vanilla_parsed" / "common" / "modifier_types.json").read_text(encoding="utf-8"))
        return data.get("data", data)

    def test_each_type_is_script_only_with_vanillas_format(self):
        blocks = _raw_blocks([self.TYPES])
        vanilla = self._vanilla_types()
        self.assertEqual(set(blocks), set(P.ENGINE_LINE_TYPES.values()))
        for (family, field), name in P.ENGINE_LINE_TYPES.items():
            self.assertIn(family, ("absorbed", "ontop"))
            self.assertIn(field, P.ENGINE_LINE_FIELDS)
            body = blocks[name]
            self.assertIn("script_only = yes", body, name)
            for key in ("decimals", "color", "percent"):
                want = vanilla[field][1][key][1]
                self.assertRegex(body, rf"\b{key} = {re.escape(str(want))}\b", f"{name}: {key}")
            self.assertRegex(body, r"ai_value = 0\b", name)

    def test_every_field_has_a_short_name(self):
        self.assertEqual(set(P.ENGINE_LINE_SHORT), set(P.ENGINE_LINE_FIELDS))
        self.assertEqual(len(set(P.ENGINE_LINE_SHORT.values())), len(P.ENGINE_LINE_FIELDS))

    def test_names_splice_the_vanilla_fields(self):
        loc = _text(ROOT / "localization" / "english" / "te_modifiers_l_english.yml")
        for (family, field), name in P.ENGINE_LINE_TYPES.items():
            # the name ends in "(Demographics)" under Full only (te_demog_line_name; a release's gate never shows it)
            self.assertRegex(loc, rf'\n {name}:0 "\${field}\$\[GetPlayer\.GetCustom\(\'te_demog_line_name\'\)\]"', name)
            # vanilla's descriptions end without a full stop ("How many children are born each year"). A release ships
            # these types with no Demographics rule (final review m2), so the description names no rule or setting.
            desc = re.search(rf'\n {name}_desc:0 "(.*)"', loc).group(1)
            self.assertTrue(desc.startswith(f"${field}_desc$. Where the demographic census sets"), name)
            self.assertNotRegex(desc, r"\b(rule|Full|setting)\b", name)


class TestEngineLinesMoved(unittest.TestCase):
    """Owner, 2026-10-11: no law, technology or institution applies an engine birth or mortality line; each line the
    census read before sits on its family's type at its old value (the plan's table)."""

    MOVED = {
        ("institution", "institution_ministry_of_consumer_protection", "modifier", "state_mortality_mult"): ("absorbed", -0.01),
        ("law", "law_charitable_health_system", "institution_modifier", "state_mortality_mult"): ("absorbed", -0.03),
        ("law", "law_child_labor_allowed", "modifier", "state_farmers_mortality_mult"): ("absorbed", 0.05),
        ("law", "law_child_labor_allowed", "modifier", "state_laborers_mortality_mult"): ("absorbed", 0.05),
        ("law", "law_child_labor_allowed", "modifier", "state_machinists_mortality_mult"): ("absorbed", 0.05),
        ("law", "law_child_labor_allowed", "modifier", "state_peasants_mortality_mult"): ("absorbed", 0.05),
        ("law", "law_communal_child_rearing", "modifier", "state_birth_rate_mult"): ("ontop", -0.2),
        ("law", "law_full_equality_and_protection", "modifier", "state_birth_rate_mult"): ("ontop", -0.01),
        ("law", "law_mandatory_augmentation", "institution_modifier", "state_mortality_mult"): ("absorbed", -0.02),
        ("law", "law_medical_augmentation_only", "institution_modifier", "state_mortality_mult"): ("absorbed", -0.02),
        ("law", "law_no_womens_rights", "modifier", "state_birth_rate_mult"): ("absorbed", 0.05),
        # phase 2 step 3b (§3.2): the two family laws' lines are absorbed, so under Full M cancels them
        ("law", "law_population_control_measures", "modifier", "state_birth_rate_mult"): ("absorbed", -0.1),
        ("law", "law_private_health_insurance", "institution_modifier", "state_mortality_wealth_mult"): ("ontop", -0.002),
        ("law", "law_pro_natalist_subsidies", "modifier", "state_birth_rate_mult"): ("absorbed", 0.1),
        ("law", "law_protected_class", "modifier", "state_birth_rate_mult"): ("absorbed", -0.1),
        ("law", "law_public_health_insurance", "institution_modifier", "state_mortality_mult"): ("absorbed", -0.05),
        ("law", "law_regulated_augmentation_market", "institution_modifier", "state_mortality_mult"): ("absorbed", -0.02),
        ("law", "law_restricted_child_labor", "modifier", "state_farmers_mortality_mult"): ("absorbed", 0.02),
        ("law", "law_restricted_child_labor", "modifier", "state_laborers_mortality_mult"): ("absorbed", 0.02),
        ("law", "law_restricted_child_labor", "modifier", "state_peasants_mortality_mult"): ("absorbed", 0.02),
        ("law", "law_state_eugenics_program", "modifier", "state_birth_rate_mult"): ("ontop", -0.05),   # sterilisation (owner, 2026-10-24)
        ("law", "law_state_sponsored_family_planning", "modifier", "state_birth_rate_mult"): ("absorbed", -0.05),
        ("law", "law_unrestricted_augmentation", "modifier", "state_mortality_mult"): ("absorbed", -0.05),
        ("law", "law_women_in_the_fields", "modifier", "state_birth_rate_mult"): ("absorbed", -0.1),
        ("law", "law_women_in_the_workplace", "modifier", "state_birth_rate_mult"): ("absorbed", -0.05),
        ("law", "law_womens_suffrage", "modifier", "state_birth_rate_mult"): ("absorbed", -0.05),
        ("technology", "antibiotic_mass_production", "modifier", "state_birth_rate_mult"): ("absorbed", 0.05),
        ("technology", "antibiotic_mass_production", "modifier", "state_mortality_mult"): ("absorbed", -0.05),
        ("technology", "biological_immortality", "modifier", "state_mortality_mult"): ("absorbed", -0.2),   # phase 3 (§8.4)
        ("technology", "contraceptive_pill", "modifier", "state_birth_rate_mult"): ("absorbed", -0.1),
        ("technology", "mental_health_awareness", "modifier", "state_mortality_mult"): ("absorbed", -0.05),   # phase 3 (§8.4)
        ("technology", "mind_backups", "modifier", "state_mortality_mult"): ("absorbed", -0.05),   # phase 3 (§8.4)
        ("technology", "modern_vaccines", "modifier", "state_birth_rate_mult"): ("absorbed", 0.05),
        ("technology", "modern_vaccines", "modifier", "state_mortality_mult"): ("absorbed", -0.05),
        ("technology", "second_wave_feminism", "modifier", "state_birth_rate_mult"): ("ontop", -0.025),
        ("technology", "sexual_revolution", "modifier", "state_birth_rate_mult"): ("ontop", -0.025),
    }

    @classmethod
    def setUpClass(cls):
        cls.lines = DM.engine_rate_lines()

    def test_no_carrier_applies_an_engine_birth_or_mortality_line(self):
        live = {k: v for k, v in self.lines.items() if abs(v) > 1e-9 and DM.is_engine_rate_field(k[3])}
        self.assertEqual(live, {}, "move each to its type (docs/superpowers/archive/plans/2026-10-11-...)")

    def test_each_line_sits_on_its_familys_type_at_its_old_value(self):
        got = DM.engine_lines()
        self.assertEqual(set(got), set(self.MOVED))
        for k, (family, value) in self.MOVED.items():
            self.assertEqual(got[k][0], family, k)
            self.assertAlmostEqual(got[k][1], value, places=6, msg=k)

    def test_the_types_are_not_engine_fields(self):
        for name in P.ENGINE_LINE_TYPES.values():
            self.assertFalse(DM.is_engine_rate_field(name), name)


class TestLinesScript(unittest.TestCase):
    """te_demog_lines_refresh (owner, 2026-10-11; the engine-lines plan, Task 4): the moved lines reach a state while
    the census doesn't set its births and deaths, at the two families' sum, by a fixed-sign pair per field."""

    def _eng(self, sums, full=False, census_term=False, held=None):
        """census_term: a census step has set M (te_dg_mb, with this build's te_dg_q_b), its deaths pair in force;
        "stale" is a step from a save made before this build (no te_dg_q_b)."""
        fixtures = {f"modifier:{name}": sums.get(name, 0.0) for name in P.ENGINE_LINE_TYPES.values()}
        eng = _Engine(fixtures, triggers={"te_demog_effects_run": full, "te_demog_cohorts_run": full})
        if census_term:
            eng.vars.update(te_dg_mb=-0.3, te_dg_md=-0.3)
            eng.modifiers["te_demog_census_deaths_down"] = 0.3
            if census_term != "stale":
                eng.vars.update(te_dg_q_b=0.0, te_dg_q_d=0.0)
        for short, m in (held or {}).items():
            eng.vars[f"te_dg_ln_{short}"] = m
            eng.modifiers[f"te_demog_line_{short}_{'up' if m > 0 else 'down'}"] = abs(m)
        return eng

    def lines(self, eng):
        return {k: v for k, v in eng.modifiers.items() if k.startswith("te_demog_line_")}

    def test_off_applies_the_families_sum(self):
        eng = self._eng({"state_demog_absorbed_mortality_mult": -0.03, "state_demog_ontop_mortality_mult": -0.05,
                         "state_demog_absorbed_birth_rate_mult": 0.05, "state_demog_ontop_mortality_wealth_mult": -0.01,
                         "state_demog_absorbed_laborers_mortality_mult": 0.05})
        eng.call("te_demog_lines_refresh")
        got = self.lines(eng)
        self.assertEqual(set(got), {"te_demog_line_deaths_down", "te_demog_line_births_up",
                                    "te_demog_line_wealth_deaths_down", "te_demog_line_laborers_deaths_up"})
        for name, want in (("te_demog_line_deaths_down", 0.08), ("te_demog_line_births_up", 0.05),
                           ("te_demog_line_wealth_deaths_down", 0.01), ("te_demog_line_laborers_deaths_up", 0.05)):
            self.assertAlmostEqual(got[name], want, msg=name)
        self.assertAlmostEqual(eng.vars["te_dg_ln_deaths"], -0.08)
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_line_deaths_applied")), -0.08)

    def _primogeniture_line(self):
        body = re.sub(r"#[^\n]*", "", _block(_text(ROOT / "common" / "static_modifiers" / "te_inheritance_modifiers.txt"),
                                              "inh_primogeniture_rural"))
        m = re.search(r"\bstate_demog_absorbed_birth_rate_mult = (-?[\d.]+)", body)
        self.assertIsNotNone(m, "Primogeniture's birth line isn't on the absorbed family's type")
        return float(m.group(1)) * 0.62   # the modifier's multiplier, an agrarian share of 0.62

    def test_the_pair_carries_primogeniture_outside_full(self):
        """The late-marriage plan, Task 9 (Plan A): outside Full the pair re-applies the line at 0.1 x the agrarian
        share, as main's own line did (given that the engine sums the type scaled: TE_SELF_CHECK in debug.log)."""
        line = self._primogeniture_line()
        eng = self._eng({"state_demog_absorbed_birth_rate_mult": line})
        eng.call("te_demog_lines_refresh")
        self.assertEqual(self.lines(eng), {"te_demog_line_births_up": line})

    def test_under_full_the_census_term_replaces_primogeniture(self):
        line = self._primogeniture_line()
        eng = self._eng({"state_demog_absorbed_birth_rate_mult": line}, full=True, census_term=True,
                        held={"births": line})
        eng.call("te_demog_lines_refresh")
        self.assertEqual(self.lines(eng), {})

    def test_the_pairs_carry_the_engine_fields(self):
        mods = _raw_blocks([LINE_MODIFIERS])
        for field, short in P.ENGINE_LINE_SHORT.items():
            self.assertRegex(mods[f"te_demog_line_{short}_up"], rf"\b{field} = 1\b", short)
            self.assertRegex(mods[f"te_demog_line_{short}_down"], rf"\b{field} = -1\b", short)
        self.assertEqual(len(mods), 2 * len(P.ENGINE_LINE_FIELDS))
        # organize_loc files te_demog_* keys in te_miscellaneous_l_english.yml, beside the census's own pairs
        loc = "".join(_text(p) for p in sorted((ROOT / "localization" / "english").glob("*.yml")))
        for name in mods:
            self.assertIn(f" {name}:", loc, name)
            self.assertIn(f" {name}_desc:", loc, name)

    def test_pairs_follow_the_census_term(self):
        """Review Focus 1: the pairs and the census's term are never both in force, and the pairs come back whenever
        the census's term is gone (Display only or Disabled clear te_dg_mb; a rule switched mid-game)."""
        eng = self._eng({"state_demog_absorbed_mortality_mult": -0.03}, full=True)
        eng.call("te_demog_lines_refresh")
        self.assertIn("te_demog_line_deaths_down", eng.modifiers, "Full, no census step yet: vanilla's lines stay")
        eng = self._eng({"state_demog_absorbed_mortality_mult": -0.03}, full=True, census_term=True,
                        held={"deaths": -0.03})
        eng.call("te_demog_lines_refresh")
        self.assertEqual(self.lines(eng), {}, "Full with the census's term: the pairs come off")
        self.assertNotIn("te_dg_ln_deaths", eng.vars)
        # review I2: a rule switched off Full takes the census's term off at the next refresh, not the state's next
        # yearly step, so the pairs don't count the moved lines a second time on top of it
        eng = self._eng({"state_demog_absorbed_mortality_mult": -0.03}, full=False, census_term=True)
        eng.call("te_demog_lines_refresh")
        self.assertIn("te_demog_line_deaths_down", eng.modifiers, "Disabled after Full: the pairs apply")
        self.assertNotIn("te_demog_census_deaths_down", eng.modifiers, "Disabled after Full: the census's term is off")
        self.assertNotIn("te_dg_mb", eng.vars)

    def test_a_term_saved_before_this_build_comes_off(self):
        """Review M2: a Full save from before the moved lines has a census term built for vanilla's lines (no
        te_dg_q_b). The refresh takes it off so the pairs carry the state until its next step sets M afresh."""
        eng = self._eng({"state_demog_absorbed_mortality_mult": -0.03}, full=True, census_term="stale")
        eng.call("te_demog_lines_refresh")
        self.assertNotIn("te_demog_census_deaths_down", eng.modifiers)
        self.assertNotIn("te_dg_mb", eng.vars)
        self.assertIn("te_demog_line_deaths_down", eng.modifiers)

    def test_unchanged_sums_are_left_alone(self):
        eng = self._eng({"state_demog_absorbed_mortality_mult": -0.03}, held={"deaths": -0.03})
        eng.call("te_demog_lines_refresh")
        self.assertEqual(eng.removed, [], "a refresh with nothing changed removes no modifier")
        eng = self._eng({"state_demog_absorbed_mortality_mult": -0.05}, held={"deaths": -0.03})
        eng.call("te_demog_lines_refresh")
        self.assertEqual(eng.removed, ["te_demog_line_deaths_down"])
        self.assertAlmostEqual(eng.modifiers["te_demog_line_deaths_down"], 0.05)

    def test_a_lost_pair_comes_back(self):
        """Final review m6: a state holding the stored sum without its pair (a save quirk, a state that copied the
        variable but not the modifier) gets the pair back at the next refresh, not when the sum next changes."""
        eng = self._eng({"state_demog_absorbed_mortality_mult": -0.03})
        eng.vars["te_dg_ln_deaths"] = -0.03
        eng.call("te_demog_lines_refresh")
        self.assertAlmostEqual(eng.modifiers["te_demog_line_deaths_down"], 0.03)

    def test_a_sum_back_at_zero_leaves_no_pair(self):
        eng = self._eng({}, held={"births": 0.05})
        eng.call("te_demog_lines_refresh")
        self.assertEqual(self.lines(eng), {})
        self.assertEqual(eng.vars["te_dg_ln_births"], 0)

    def test_unincorporated_state_gets_no_institution_lines(self):
        """Review Focus 2: the engine reads an institution line as 0 in an unincorporated state, so the sum is the
        laws' and techs' alone, as vanilla applies them."""
        eng = self._eng({"state_demog_absorbed_birth_rate_mult": 0.05})
        eng.call("te_demog_lines_refresh")
        self.assertEqual(set(self.lines(eng)), {"te_demog_line_births_up"})

    def test_refresh_runs_where_the_inputs_change(self):
        """Owner, 2026-10-11: the pairs follow a new game, a law, a technology, a change of owner, incorporation and a
        new state at once, with the monthly pulse as the fallback. Every caller has ROOT = the state: the state
        on-actions call it directly, the others through the hidden state event te_demog_events.4."""
        on_actions = _text(ROOT / "common" / "on_actions" / "te_demog_on_actions.txt")
        hooks = {"on_monthly_pulse_state": "te_demog_lines_on_action", "on_state_owner_change": "te_demog_lines_on_action",
                 "on_state_incorporation": "te_demog_lines_on_action", "on_state_created": "te_demog_lines_on_action",
                 "on_law_activated": "te_demog_lines_law_on_action",
                 "on_acquired_technology": "te_demog_lines_country_on_action",
                 "on_game_started_after_lobby": "te_demog_lines_world_on_action"}
        for hook, name in hooks.items():
            self.assertRegex(on_actions, rf"\n{hook} = \{{\s*on_actions = \{{[^}}]*\b{name}\b", hook)
        # the review of step 1 (Minor 3): again a day later, in case the engine hasn't re-summed the families that day
        dispatch = (r"every_scope_state = \{\s*trigger_event = \{ id = te_demog_events\.4 \}\s*(#[^\n]*\s*)*"
                    r"trigger_event = \{ id = te_demog_events\.4 days = 1 \}\s*\}")
        # review I1: on_law_activated's ROOT is the law, so its states are the owner's; on_acquired_technology's
        # ROOT is the country. Both wait for the game to start: history's laws and techs are the world hook's.
        law = _block(on_actions, "te_demog_lines_law_on_action")
        self.assertRegex(law, r"owner = \{\s*" + dispatch)
        country = _block(on_actions, "te_demog_lines_country_on_action")
        self.assertRegex(country, r"limit = \{ has_game_started = yes \}\s*" + dispatch)
        self.assertIn("limit = { has_game_started = yes }", law)
        self.assertIn("trigger_event = { id = te_demog_events.4 }", _block(on_actions, "te_demog_lines_world_on_action"))
        event = _block(_text(ROOT / "events" / "te_demog_events.txt"), "te_demog_events.4")
        self.assertIn("type = state_event", event)
        self.assertIn("te_demog_lines_refresh = yes", event)
        callers = sorted(p.name for p in [*ROOT.glob("common/**/*.txt"), *ROOT.glob("events/*.txt")]
                         if "te_demog_lines_refresh = yes" in _text(p) and "generated" not in p.name)
        self.assertEqual(callers, ["te_demog_events.txt", "te_demog_on_actions.txt"])


class TestWorkforceLinesMoved(unittest.TestCase):
    """Phase 2 step 1 (the design §1.7): every working-adult line sits on its family's type at its old value, with call
    3's participation input beside it; the only live engine lines left are Rosen's."""

    # laws and technologies, read back by DM.engine_workforce_lines
    MOVED = {
        ("law", "law_women_in_the_fields", "modifier"): ("womens_work", 0.3),
        ("law", "law_women_own_property", "modifier"): ("womens_work", 0.05),
        ("law", "law_women_in_the_workplace", "modifier"): ("womens_work", 0.1),
        ("law", "law_womens_suffrage", "modifier"): ("womens_work", 0.15),
        ("law", "law_protected_class", "modifier"): ("womens_work", 0.2),
        ("law", "law_state_sponsored_family_planning", "modifier"): ("womens_work", 0.05),
        ("law", "law_communal_child_rearing", "modifier"): ("womens_work", 0.1),
        ("technology", "contraceptive_pill", "modifier"): ("womens_work", 0.05),
        ("technology", "second_wave_feminism", "modifier"): ("womens_work", 0.025),
        ("technology", "personal_appliances", "modifier"): ("womens_work", 0.025),
        ("law", "law_old_age_pension", "institution_modifier"): ("replaced", -0.01),
        ("law", "law_universal_basic_income", "institution_modifier"): ("replaced", -0.02),
        ("law", "law_pro_natalist_subsidies", "modifier"): ("replaced", -0.05),
        ("law", "law_restorative_justice", "modifier"): ("replaced", 0.025),
        ("law", "law_rehabilitation_focused_criminal_justice", "modifier"): ("replaced", 0.05),
        ("law", "law_pro_labor_ministry_of_labor", "institution_modifier"): ("replaced", 0.01),
        ("law", "law_pro_capital_ministry_of_labor", "institution_modifier"): ("replaced", 0.02),
    }
    # call 3's participation inputs on laws (the design §1.7's inventory; starting sizes, call 11), in the game's units
    # since 2026-10-20 as the rates they add to: the inventory's 0.02, 0.03, 0.005 and 0.01 x 0.7.
    PARTICIPATION = {
        ("law", "law_restorative_justice", "modifier", P.MALE_PARTICIPATION_TYPE): 0.014,
        ("law", "law_rehabilitation_focused_criminal_justice", "modifier", P.MALE_PARTICIPATION_TYPE): 0.021,
        ("law", "law_pro_labor_ministry_of_labor", "institution_modifier", P.PARTICIPATION_TYPE): 0.0035,
        ("law", "law_pro_capital_ministry_of_labor", "institution_modifier", P.PARTICIPATION_TYPE): 0.007,
    }
    # the carriers no reader walks: (file, block) -> the lines its block must hold
    BLOCKS = {
        ("common/amendments/extra_amendments.txt", "amendment_community_service"):
            (f"{P.REPLACED_TYPE} = 0.01", f"{P.MALE_PARTICIPATION_TYPE} = 0.007"),
        ("common/amendments/extra_amendments.txt", "amendment_mandatory_minimums"):
            (f"{P.REPLACED_TYPE} = -0.01", f"{P.MALE_PARTICIPATION_TYPE} = -0.007"),
        ("common/interest_group_traits/te_demog_workforce_injections.txt", "INJECT:ig_trait_solidarity"):
            ("state_working_adult_ratio_add = -0.05", f"{P.REPLACED_TYPE} = 0.05", f"{P.PARTICIPATION_TYPE} = 0.014"),
        ("common/interest_group_traits/te_demog_workforce_injections.txt", "INJECT:ig_trait_bourse_du_travail"):
            ("state_working_adult_ratio_add = -0.05", f"{P.REPLACED_TYPE} = 0.05", f"{P.PARTICIPATION_TYPE} = 0.014"),
        ("common/static_modifiers/te_demog_workforce_injections.txt", "INJECT:modifier_woman_soldiers"):
            ("state_working_adult_ratio_add = -0.05", f"{P.WOMENS_WORK_TYPE} = 0.05"),
        ("common/static_modifiers/extra_modifiers.txt", "INJECT:state_region_pollution_health"):
            (f"{P.REPLACED_TYPE} = -0.05", f"{P.CAPACITY_TYPE} = -0.1"),
    }

    def test_each_line_sits_on_its_familys_type_at_its_old_value(self):
        got = {k[:3]: v for k, v in DM.engine_workforce_lines().items()}
        self.assertEqual(set(got), set(self.MOVED))
        for k, (family, value) in self.MOVED.items():
            self.assertEqual(got[k][0], family, k)
            self.assertAlmostEqual(got[k][1], value, places=6, msg=k)

    def test_each_law_carries_its_participation_input(self):
        names = set(P.PARTICIPATION_TYPES)
        got = {k: v for k, v in DM.engine_rate_lines(keep=lambda f: f in names).items() if abs(v) > 1e-9}
        self.assertEqual(set(got), set(self.PARTICIPATION))
        for k, value in self.PARTICIPATION.items():
            self.assertAlmostEqual(got[k], value, places=6, msg=k)

    def test_the_other_carriers_blocks(self):
        for (rel, block), lines in self.BLOCKS.items():
            body = re.sub(r"#[^\n]*", "", _block(_text(ROOT / rel), block))
            for line in lines:
                self.assertIn(line, body, (block, line))
            if "INJECT:" not in block:
                self.assertNotIn("state_working_adult_ratio_add", body, block)

    def test_no_live_line_but_rosens(self):
        """A working-adult line added anywhere in common/ fails here until it is given a family or listed (the design
        §1.7: the census treats an unlisted line as the remainder on top, and this keeps the list honest)."""
        live = set()
        skip = {"te_demog_engine_line_injections.txt", "te_demog_workforce_injections.txt",
                "te_demog_workforce_line_modifiers_generated.txt", "te_debug_demog_modifiers.txt",
                "mod_entity_modifier_types.txt"}
        # phase 2 step 2's workforce term: the census's own pair, as the moved lines' pair is
        census_pair = {("te_demog_modifiers.txt", "te_demog_census_workforce_up"),
                       ("te_demog_modifiers.txt", "te_demog_census_workforce_down")}
        for path in sorted((ROOT / "common").rglob("*.txt")):
            if path.name in skip:
                continue
            text = re.sub(r"#[^\n]*", "", _text(path))
            if not re.search(r"\bstate_working_adult_ratio_add\s*=\s*-?\d", text):
                continue
            for m in re.finditer(r"^([\w.:-]+) = \{", text, re.M):
                if re.search(r"\bstate_working_adult_ratio_add\s*=\s*-?\d", _block(text, m.group(1))):
                    live.add((path.name, m.group(1)))
        self.assertEqual(live - census_pair, set(P.LIVE_WORKFORCE_LINES))
        self.assertEqual(live & census_pair, census_pair)

    def test_each_cancel_matches_its_familys_line(self):
        """The injection files' cancels (vanilla's carriers): each block's working-adult cancel is minus its family's
        line, so the engine field nets to 0 and the family carries vanilla's value."""
        families = (P.WOMENS_WORK_TYPE, P.REPLACED_TYPE)
        for rel in ("common/laws/te_demog_engine_line_injections.txt",
                    "common/interest_group_traits/te_demog_workforce_injections.txt",
                    "common/static_modifiers/te_demog_workforce_injections.txt"):
            text = re.sub(r"#[^\n]*", "", _text(ROOT / rel))
            for m in re.finditer(r"^(INJECT:[\w-]+) = \{", text, re.M):
                body = _block(text, m.group(1))
                cancel = re.search(r"\bstate_working_adult_ratio_add\s*=\s*(-?[\d.]+)", body)
                if not cancel:
                    continue
                carried = sum(float(v) for f in families
                              for v in re.findall(rf"\b{f}\s*=\s*(-?[\d.]+)", body))
                self.assertAlmostEqual(float(cancel.group(1)), -carried, msg=m.group(1))

    # vanilla's working-adult carriers (vanilla_parsed/common/<file>.json, top-level key), every one moved by an INJECT
    VANILLA_CARRIERS = {
        ("laws", "law_women_in_the_fields"), ("laws", "law_women_own_property"),
        ("laws", "law_women_in_the_workplace"), ("laws", "law_womens_suffrage"), ("laws", "law_old_age_pension"),
        ("interest_group_traits", "ig_trait_solidarity"), ("interest_group_traits", "ig_trait_bourse_du_travail"),
        ("modifiers", "modifier_woman_soldiers"),
    }

    def test_every_vanilla_carrier_is_moved(self):
        """A vanilla patch that adds a working-adult line fails here until it is classified, as #892's
        test_every_vanilla_line_is_cancelled_and_carried does for births and deaths (the second review of #923)."""
        found = set()

        def walk(node, where):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == P.WORKING_ADULT_FIELD:
                        found.add(where[:2])
                    walk(value, where + (key,))
            elif isinstance(node, list):
                for value in node:
                    walk(value, where)

        for path in sorted((ROOT / "vanilla_parsed" / "common").glob("*.json")):
            if path.name == "modifier_types.json":   # the field's own definition
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            walk(data.get("data", data), (path.stem,))
        self.assertEqual(found, self.VANILLA_CARRIERS)

    def test_a_release_keeps_the_families_and_drops_the_inputs(self):
        """Review Focus 5: the release script comments out demographics_modifier_types.txt's types only."""
        census_types = _text(ROOT / "common" / "modifier_type_definitions" / "demographics_modifier_types.txt")
        for t in P.WORKFORCE_LINE_TYPES.values():
            self.assertNotIn(t, census_types)
            self.assertNotIn(t, P.DEMOG_TYPES)
        for t in P.PARTICIPATION_TYPES:
            self.assertIn(f"{t} = {{", census_types)

    def test_the_types_copy_the_fields_format(self):
        blocks = _raw_blocks([ROOT / "common" / "modifier_type_definitions" /
                              "demographics_workforce_line_types.txt"])
        self.assertEqual(set(blocks), set(P.WORKFORCE_LINE_TYPES.values()))
        for name, body in blocks.items():
            for line in ("decimals = 1", "percent = yes", "ai_value = 0", "script_only = yes"):
                self.assertIn(line, body, name)


class TestWorkforceLinesScript(unittest.TestCase):
    """te_demog_workforce_lines_refresh: the pair at both families' sum while no workforce term is in force."""

    def _eng(self, womens=0.25, replaced=-0.03, full=False, census_term=False, workforce_term=False):
        fixtures = {f"modifier:{P.WOMENS_WORK_TYPE}": womens, f"modifier:{P.REPLACED_TYPE}": replaced}
        eng = _Engine(fixtures, triggers={"te_demog_effects_run": full, "te_demog_cohorts_run": full})
        if census_term:
            eng.vars.update(te_dg_mb=-0.3, te_dg_md=-0.3, te_dg_q_b=0.0, te_dg_q_d=0.0)
        if workforce_term:
            eng.vars["te_dg_mw"] = 0.1
        return eng

    def test_outside_full_the_pair_carries_the_sum(self):
        eng = self._eng()
        eng.call("te_demog_workforce_lines_refresh")
        self.assertAlmostEqual(eng.modifiers["te_demog_line_working_adults_up"], 0.22)
        self.assertAlmostEqual(eng.vars["te_dg_ln_working_adults"], 0.22)

    def test_the_workforce_pair_survives_the_census_term(self):
        """Review Focus 2 (D3): under Full with M in force the births and deaths pairs go, this one stays."""
        eng = self._eng(full=True, census_term=True)
        eng.call("te_demog_workforce_lines_refresh")
        eng.call("te_demog_lines_clear")
        self.assertAlmostEqual(eng.modifiers["te_demog_line_working_adults_up"], 0.22)

    def test_step_twos_term_takes_it_off(self):
        eng = self._eng(full=True, workforce_term=True)
        eng.modifiers["te_demog_line_working_adults_up"] = 0.22
        eng.vars["te_dg_ln_working_adults"] = 0.22
        eng.call("te_demog_workforce_lines_refresh")
        self.assertNotIn("te_demog_line_working_adults_up", eng.modifiers)
        self.assertNotIn("te_dg_ln_working_adults", eng.vars)

    def test_a_negative_sum_takes_the_down_pair(self):
        eng = self._eng(womens=0.0, replaced=-0.05)
        eng.call("te_demog_workforce_lines_refresh")
        self.assertAlmostEqual(eng.modifiers["te_demog_line_working_adults_down"], 0.05)

    def test_it_refreshes_where_the_lines_do(self):
        for path in (DEMOG_ON_ACTIONS, ROOT / "events" / "te_demog_events.txt"):
            text = _text(path)
            self.assertEqual(text.count("te_demog_lines_refresh = yes"),
                             text.count("te_demog_workforce_lines_refresh = yes"), path.name)

    def test_an_amendments_repeal_or_timeout_refreshes_that_day(self):
        """The design §1.9: an amendment attached waits for the monthly refresh (no on-action); its repeal and timeout
        (ROOT the country) take the existing country refresh, as a technology does."""
        on_actions = _text(DEMOG_ON_ACTIONS)
        for hook in ("on_amendment_repealed", "on_amendment_timeout"):
            self.assertIn("te_demog_lines_country_on_action", _block(on_actions, hook), hook)

    def test_the_pair_is_hidden_and_named(self):
        hidden = _block(_text(ROOT / "common" / "script_values" / "gui_chart_script_values.txt"),
                        "gui_state_hidden_modifier_count")
        loc = "".join(_text(p) for p in sorted((ROOT / "localization" / "english").glob("*.yml")))
        for name in ("te_demog_line_working_adults_up", "te_demog_line_working_adults_down"):
            self.assertIn(f"has_modifier = {name}", hidden)
            self.assertIn(f' {name}:0 "Laws and Institutions"', loc)


class TestWorkforceSelfChecks(unittest.TestCase):
    """Phase 2 step 1's once-a-game self-checks (owner, 2026-10-12: a self-check, not an in-game gate): whether the
    engine sums a script-only type from an amendment and from an IG trait into a state's read, and whether a pop's
    workforce reads as a value. Each compares the participation input its carrier holds with that carrier's size."""

    VALUES = ROOT / "common" / "script_values" / "te_debug_demog_values.txt"
    TRIGGERS = ROOT / "common" / "scripted_triggers" / "te_debug_demog_triggers.txt"

    def _adds(self, body):
        """{law or amendment named in a limit: the literal its branch adds}."""
        out = {}
        for m in re.finditer(r"if = \{\s*limit = \{(.*?)\}\s*\}\s*add = (-?[\d.]+)", body, re.S):
            name = re.search(r"(law_type|amendment_type):(\w+)", m.group(1)).group(2)
            out[name] = float(m.group(2))
        return out

    def test_the_sizes_are_the_carriers(self):
        values = _text(self.VALUES)
        moved = TestWorkforceLinesMoved
        laws = self._adds(_block(values, "te_debug_demog_wf_amend_laws_only"))
        self.assertEqual(laws, {key: v for (_kind, key, _block_name, t), v in moved.PARTICIPATION.items()
                                if t == P.MALE_PARTICIPATION_TYPE})
        amends = self._adds(_block(values, "te_debug_demog_wf_amend_expected"))
        for amendment in ("amendment_community_service", "amendment_mandatory_minimums"):
            line = next(line for line in moved.BLOCKS[("common/amendments/extra_amendments.txt", amendment)]
                        if line.startswith(P.MALE_PARTICIPATION_TYPE))
            self.assertAlmostEqual(amends[amendment], float(line.split("=")[1]), msg=amendment)
        trait = next(line for line in moved.BLOCKS[("common/interest_group_traits/te_demog_workforce_injections.txt",
                                                     "INJECT:ig_trait_solidarity")]
                     if line.startswith(P.PARTICIPATION_TYPE))
        self.assertIn(f"value = {trait.split('= ')[1]}", _block(values, "te_debug_demog_wf_ig_expected"))
        self.assertIn(f"value = modifier:{P.MALE_PARTICIPATION_TYPE}", _block(values, "te_debug_demog_wf_part_m_read"))
        self.assertIn(f"value = modifier:{P.PARTICIPATION_TYPE}", _block(values, "te_debug_demog_wf_part_read"))

    def test_the_ig_check_arms_only_at_the_traits_plain_size(self):
        """A marginal IG's traits are halved and a powerful one's doubled (the defines), and the Ministries of Labour
        carry the same input: the check's expected 0.014 holds only without all three."""
        trig = _block(_text(self.TRIGGERS), "te_debug_demog_wf_ig_trait_plain")
        for line in ("ig_approval >= define:NPolitics|APPROVAL_THRESHOLD_LOYAL",
                     "ig_clout > define:NPolitics|MARGINAL_IG_THRESHOLD",
                     "ig_clout < define:NPolitics|POWERFUL_IG_CUTOFF",
                     "NOT = { has_law = law_type:law_pro_labor_ministry_of_labor }",
                     "NOT = { has_law = law_type:law_pro_capital_ministry_of_labor }"):
            self.assertIn(line, trig)
        carriers = {k[1] for k in TestWorkforceLinesMoved.PARTICIPATION if k[3] == P.PARTICIPATION_TYPE}
        self.assertEqual(carriers, {"law_pro_labor_ministry_of_labor", "law_pro_capital_ministry_of_labor"})

    def test_the_checks_are_wired_once_a_game_where_the_census_runs(self):
        monthly = _block(_text(DEMOG_ON_ACTIONS), "te_demog_country_monthly_on_action")
        self.assertIn("te_debug_demog_wf_selfchecks = yes", monthly)
        start = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_wf_selfchecks")
        # the review of step 1 (Important 2): every development build under any rule, Disabled included; a release
        # turns the gate off (it comments the inputs out, which would read 0)
        self.assertIn("te_debug_demog_selfchecks_run = yes", start, "a release comments the inputs out: no false BROKEN")
        self.assertNotIn("te_demog_cohorts_run", start.split("te_dg_wf_engine")[0])
        release = _text(ROOT / "scripts" / "release" / "comment_out_census_inputs.py")
        self.assertRegex(release, r'GATES = \([^)]*"te_debug_demog_selfchecks_run"')
        triggers = _block(_text(TRIGGERS), "te_debug_demog_selfchecks_run")
        self.assertIn("always = yes", triggers)
        for flag, event in (("te_demog_selfcheck_amend_done", "te_debug_demog.6"),
                            ("te_demog_selfcheck_ig_done", "te_debug_demog.7")):
            self.assertIn(f"NOT = {{ has_global_variable = {flag} }}", start)
            self.assertIn(f"set_global_variable = {{ name = {flag} value = yes }}", start)
            self.assertIn(f"trigger_event = {{ id = {event} days = 7 }}", start)
        self.assertIn("TE_SELF_CHECK OK pop_workforce_read", start)
        self.assertIn("TE_SELF_CHECK BROKEN pop_workforce_read", start)
        self.assertIn("trigger_event = { id = te_debug_demog.8 days = 7 }", start)
        events = _text(DEBUG_EVENTS)
        net = _block(events, "te_debug_demog.8")
        for needle in ("TE_SELF_CHECK OK workforce_lines_net", "TE_SELF_CHECK BROKEN workforce_lines_net",
                       "te_debug_demog_wf_remainder > -0.01", "te_debug_demog_wf_remainder < 0.01"):
            self.assertIn(needle, net)
        # the review of step 1 (Important 1): an INJECT that replaced vanilla's trait block reads 0.02 and leaves the
        # cancel alone, so .7 also needs the remainder
        self.assertIn("te_debug_demog_wf_remainder > -0.01", _block(events, "te_debug_demog.7"))
        for event, name, flag in (("te_debug_demog.6", "workforce_amendment_type", "te_demog_selfcheck_amend_done"),
                                  ("te_debug_demog.7", "workforce_ig_trait_type", "te_demog_selfcheck_ig_done")):
            self.assertEqual(len(re.findall(rf"^{re.escape(event)} = \{{", events, re.M)), 1, event)
            body = _block(events, event)
            self.assertIn(f"TE_SELF_CHECK OK {name}", body)
            self.assertIn(f"TE_SELF_CHECK BROKEN {name}", body)
            self.assertIn(f"remove_global_variable = {flag}", body, "a carrier gone in the week re-arms")


class TestPrimogenitureUnderFull(unittest.TestCase):
    """Call 4 (the late-marriage spec 4.5; plan D3, Plan A): Primogeniture's +10% farm births ride the absorbed family,
    so under Full the census's Late Marriage replaces them and nothing changes outside Full. The engine fact Plan A
    rests on is unverified; a self-check logs it once a game (owner, 2026-10-12: log it instead of a probe gate)."""

    MODS = ROOT / "common" / "static_modifiers" / "te_inheritance_modifiers.txt"
    DEBUG = ROOT / "events" / "te_debug_demog_events.txt"
    DEBUG_EFFECTS = ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"
    DEBUG_VALUES = ROOT / "common" / "script_values" / "te_debug_demog_values.txt"

    def test_the_line_sits_on_the_absorbed_family(self):
        body = _block(_text(self.MODS), "inh_primogeniture_rural")
        code = re.sub(r"#[^\n]*", "", body)
        self.assertNotRegex(code, r"\bstate_birth_rate_mult\b")
        self.assertRegex(code, rf"\b{P.ENGINE_LINE_TYPES[('absorbed', 'state_birth_rate_mult')]} = 0\.1\b")
        self.assertRegex(code, r"\bstate_migration_quota_mult = 0\.2\b", "the migration line stays")
        # phase 3 (parent spec 13): Forced Heirship's -0.15 moved the same way; under Full Family Limitation takes it
        fh = re.sub(r"#[^\n]*", "", _block(_text(self.MODS), "inh_forced_heirship_rural"))
        self.assertNotRegex(fh, r"\bstate_birth_rate_mult\b")
        self.assertRegex(fh, rf"\b{P.ENGINE_LINE_TYPES[('absorbed', 'state_birth_rate_mult')]} = -0\.15\b")
        self.assertRegex(fh, r"\bstate_migration_quota_mult = -0\.2\b", "its migration line stays")

    def test_the_rural_refresh_fires_the_lines_refresh_for_forced_heirship_too(self):
        """Phase 3: Forced Heirship's farm births ride the pair too, so its refresh fires the same day as
        Primogeniture's; and the Primogeniture self-check skips a state whose owner just left Forced Heirship (the
        removed line still reads that week)."""
        body = re.sub(r"#[^\n]*", "", _block(_text(INH_EFFECTS), "te_inh_refresh_rural_effects"))
        self.assertIn("set_local_variable = { name = te_inh_fh_was value = 1 }", body)
        fire = body[body.rindex("trigger_event = { id = te_demog_events.4 }") - 400:]
        for needle in ("has_local_variable = te_inh_fh_was", "has_law = law_type:law_equal_inheritance"):
            self.assertIn(needle, fire)
        self.assertIn("NOT = { has_local_variable = te_inh_fh_was }",
                      _block(_text(self.DEBUG_EFFECTS), "te_debug_demog_pr_selfcheck_start"))

    def test_the_rural_refresh_fires_the_lines_refresh(self):
        """No month's lag (#892's owner decision 2): the pair follows the yearly rural refresh the same day, from a
        state event, where the modifier just added is visible."""
        body = re.sub(r"#[^\n]*", "", _block(_text(INH_EFFECTS), "te_inh_refresh_rural_effects"))
        self.assertIn("trigger_event = { id = te_demog_events.4 }", body)
        self.assertGreater(body.rindex("trigger_event = { id = te_demog_events.4 }"),
                           body.rindex("name = inh_primogeniture_rural"))
        self.assertIn("set_local_variable = { name = te_inh_pr_was value = 1 }", body)

    def test_the_self_check_reads_before_the_add(self):
        body = re.sub(r"#[^\n]*", "", _block(_text(INH_EFFECTS), "te_inh_refresh_rural_effects"))
        call = body.index("te_debug_demog_pr_selfcheck_start = yes")
        self.assertLess(call, body.index("name = inh_primogeniture_rural", call))
        start = _block(_text(self.DEBUG_EFFECTS), "te_debug_demog_pr_selfcheck_start")
        for needle in ("NOT = { has_global_variable = te_inh_pr_selfcheck_done }",
                       "NOT = { has_local_variable = te_inh_pr_was }",
                       "value = modifier:state_demog_absorbed_birth_rate_mult",
                       "trigger_event = { id = te_debug_demog.5 days = 7 }",
                       # the review's I1: near 0 or 1 an unsummed or unscaled line reads like the scaled one
                       "var:te_inh_agrarian_share > 0.1", "var:te_inh_agrarian_share < 0.9",
                       "TE_SELF_CHECK START primogeniture_scaled"):
            self.assertIn(needle, start)

    def test_the_self_check_expects_the_modifiers_value(self):
        line = re.search(r"\bstate_demog_absorbed_birth_rate_mult = ([\d.]+)",
                         _block(_text(self.MODS), "inh_primogeniture_rural")).group(1)
        expected = _block(_text(self.DEBUG_VALUES), "te_debug_demog_pr_chk_expected")
        self.assertRegex(expected, rf"value = {re.escape(line)}\b")
        verdict = _block(_text(self.DEBUG), "te_debug_demog.5")
        self.assertIn("TE_SELF_CHECK OK primogeniture_scaled", verdict)
        self.assertIn("TE_SELF_CHECK BROKEN primogeniture_scaled", verdict)
        self.assertIn("remove_variable = te_inh_pr_chk_before", verdict)


class TestPollutionLine(unittest.TestCase):
    """predict's Pollution Impact line (owner, 2026-10-11): vanilla's code static modifier plus the mod's INJECT."""

    def test_the_parameter_is_vanillas_line_plus_the_mods(self):
        import json
        vanilla = json.loads((ROOT / "vanilla_parsed" / "common" / "modifiers.json").read_text(encoding="utf-8"))
        data = vanilla.get("data", vanilla)
        line = float(data["state_region_pollution_health"][1]["state_mortality_mult"][1])
        text = _text(ROOT / "common" / "static_modifiers" / "extra_modifiers.txt")
        inject = re.search(r"^INJECT:state_region_pollution_health = \{(.*?)^\}", text, re.M | re.S).group(1)
        mod = float(re.search(r"state_mortality_mult\s*=\s*(-?[0-9.]+)", inject).group(1))
        self.assertAlmostEqual(P.POLLUTION_HEALTH_MORTALITY, line + mod)


class TestRatesScript(unittest.TestCase):
    """te_demog_rates_refresh (te_demog_rate_effects.txt) against demographics_model.rate_term."""

    POP = 1_000_000.0
    # the walk's replaced births: literacy's -0.1 at a bare-weighted literacy of 0.2, and nothing else absorbed
    EBR = P.LITERACY_BIRTH_PENALTY * 0.2 * 475e6

    def _eng(self, full=True, stepped=1.0, cbr=38.0, cdr=31.0, eb0=475.0 * 1_000_000, ed0=430.0 * 1_000_000,
             ebr=EBR, edr=0.0, read_b=0.05, read_d=0.04, ontop=None):
        # the moved lines' families (the engine-lines plan): 0 unless a test says
        families = {f"modifier:{name}": (ontop or {}).get(name, 0.0) for name in P.ENGINE_LINE_TYPES.values()}
        eng = _Engine({"state_population": self.POP, "modifier:state_birth_rate_mult": read_b,
                       "modifier:state_mortality_mult": read_d, **families},
                      triggers={"te_demog_effects_run": full, "te_demog_cohorts_run": True})
        eng.locals.update(te_dg_w_eb0=eb0, te_dg_w_ed0=ed0, te_dg_w_ebr=ebr, te_dg_w_edr=edr, te_dg_w_eb=eb0,
                          te_dg_w_ed=ed0, te_dg_w_eb0m=eb0, te_dg_w_ed0m=ed0, te_dg_w_sev=0.0, te_dg_w_sevd=0.0)
        eng.vars.update(te_dg_stepped=stepped, te_dg_cbr_model=cbr, te_dg_cdr_model=cdr)
        return eng

    def _want(self, cbr, cdr, eb0, ed0, ebr, other_b, other_d, edr=0.0, added_b=0.0, added_d=0.0):
        """rate_term's M for the script's inputs: the state-level lines on top are the read without the census's and
        fast mode's terms and the moved lines' pairs (other); the on-top family is what the census adds (added)."""
        mb, _ = demographics_model.rate_term(cbr * self.POP * 100 / 12, eb0, absorbed=ebr, other=other_b,
                                             on_top=other_b, added=added_b)
        md, _ = demographics_model.rate_term(cdr * self.POP * 100 / 12, ed0, absorbed=edr, other=other_d,
                                             on_top=other_d, added=added_d)
        return mb, md

    def test_state_level_lines_on_top_act_on_the_census_rate(self):
        """Owner, 2026-10-11: West Bengal's Pollution Impact (+0.32) and the Midlands' Cadet Sons (+0.046 births) with
        last step's M (-0.3) and fast mode's term (+2.0) in the read. The engine's deaths come to the census's x 1.32
        and its births to the census's x 1.046."""
        ed0, eb0 = 430e6, 475e6
        eng = self._eng(read_d=-0.3 + 2.0 + 0.32, read_b=2.0 + 0.046)
        eng.modifiers.update(te_demog_census_deaths_down=0.3, te_demog_fast_deaths=1.0, te_demog_fast_births=1.0)
        eng.vars.update(te_dg_md=-0.3, te_dg_fast_fd=2.0, te_dg_fast_fb=2.0)
        eng.call("te_demog_rates_refresh")
        mb, md = self._want(38.0, 31.0, eb0, ed0, self.EBR, 0.046, 0.32)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        target_d, target_b = 31.0 * self.POP * 100 / 12, 38.0 * self.POP * 100 / 12
        self.assertAlmostEqual(ed0 * (1 + eng.vars["te_dg_md"] + 0.32), target_d * 1.32, delta=target_d * 1e-5)
        self.assertAlmostEqual(eb0 * (1 + eng.vars["te_dg_mb"] + 0.046) + self.EBR, target_b * 1.046, delta=target_b * 1e-5)
        # kept for console option n, whose line then checks the term: M = tb - 1 - rep - os x (1 - tb) + q x tb
        self.assertAlmostEqual(eng.vars["te_dg_os_d"], 0.32, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_os_b"], 0.046, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_tb_d"], target_d / ed0, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_tb_b"], target_b / eb0, places=5)

    def test_full_applies_the_on_top_family_and_clears_the_pairs(self):
        """The engine-lines plan, Task 5: on the first Full step the moved lines' pairs are in the read and are cleared
        in the same effect; M carries the on-top family at the census's rate, and Private Health Insurance's wealth
        line goes on the census's own pair at its share of the bare curve, floored (owner, option b)."""
        ed0 = 430e6
        eng = self._eng(read_d=-0.08 + 0.32, ontop={"state_demog_ontop_mortality_mult": -0.05,
                                                     "state_demog_absorbed_mortality_mult": -0.03,
                                                     "state_demog_ontop_mortality_wealth_mult": -0.01})
        eng.modifiers["te_demog_line_deaths_down"] = 0.08
        eng.vars["te_dg_ln_deaths"] = -0.08
        eng.call("te_demog_rates_refresh")
        target = 31.0 * self.POP * 100 / 12
        _, md = self._want(38.0, 31.0, 475e6, ed0, self.EBR, 0.05, 0.32, added_d=-0.05)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)
        self.assertAlmostEqual(ed0 * (1 + md + 0.32), target * (1 + 0.32 - 0.05), delta=target * 1e-5)
        self.assertNotIn("te_demog_line_deaths_down", eng.modifiers)
        self.assertNotIn("te_dg_ln_deaths", eng.vars)
        self.assertAlmostEqual(eng.vars["te_dg_q_d"], -0.05, places=5)
        tb = target / ed0
        self.assertAlmostEqual(eng.vars["te_dg_w"], P.WEALTH_LINE_FLOOR * tb, places=5)
        self.assertAlmostEqual(eng.modifiers["te_demog_census_wealth_down"], -P.WEALTH_LINE_FLOOR * tb, places=5)
        # above the floor it is the line itself, at the census's share
        eng = self._eng(ontop={"state_demog_ontop_mortality_wealth_mult": -0.002})
        eng.call("te_demog_rates_refresh")
        self.assertAlmostEqual(eng.vars["te_dg_w"], -0.002 * tb, places=5)

    def test_outside_full_the_wealth_pair_goes(self):
        eng = self._eng(full=False)
        eng.modifiers["te_demog_census_wealth_down"] = 0.003
        eng.vars.update(te_dg_mb=-0.2, te_dg_md=-0.3, te_dg_w=-0.003, te_dg_q_b=0.0, te_dg_q_d=-0.05)
        eng.call("te_demog_rates_refresh")
        self.assertNotIn("te_demog_census_wealth_down", eng.modifiers)
        for var in ("te_dg_w", "te_dg_q_b", "te_dg_q_d"):
            self.assertNotIn(var, eng.vars)

    def test_script_matches_the_model(self):
        eng = self._eng()
        eng.call("te_demog_rates_refresh")
        mb, md = self._want(38.0, 31.0, 475e6, 430e6, self.EBR, 0.05, 0.04)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)
        # births down, deaths down: one modifier of each pair, multiplier |M|
        self.assertAlmostEqual(eng.modifiers["te_demog_census_births_down"], -mb, places=5)
        self.assertAlmostEqual(eng.modifiers["te_demog_census_deaths_down"], -md, places=5)
        self.assertNotIn("te_demog_census_births_up", eng.modifiers)

    def test_m_nets_the_replaced_terms(self):
        """Owner amendment A and B (2026-10-10): under Full, M takes out every absorbed line's contribution in the
        state, the walk's replaced sums (te_dg_w_ebr, te_dg_w_edr: each pop's bare curve x its absorbed terms), so
        the engine's events are the model's plus the terms on top. A health law at level 3 (-0.15) and mild
        starvation (+0.11 on a fifth of the deaths) here; the shares replaced are kept for console option n."""
        ebr = self.EBR - 0.13 * 0.2 * 475e6
        edr = -0.15 * 430e6 + 0.1125 * 0.2 * 430e6
        eng = self._eng(ebr=ebr, edr=edr)
        eng.call("te_demog_rates_refresh")
        mb, md = self._want(38.0, 31.0, 475e6, 430e6, ebr, 0.05, 0.04, edr=edr)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)
        plain_b, plain_d = self._want(38.0, 31.0, 475e6, 430e6, 0.0, 0.05, 0.04)
        self.assertAlmostEqual(mb, plain_b - ebr / 475e6)
        self.assertAlmostEqual(md, plain_d - edr / 430e6)
        self.assertAlmostEqual(eng.vars["te_dg_rep_b"], ebr / 475e6, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_rep_d"], edr / 430e6, places=5)

    # mild hunger's deaths on half the bare deaths (absorbed: M nets them), enough to pass a low census rate alone
    EDR_HUNGER = 0.1125 * 0.5 * 430e6

    def test_script_clamps_like_the_model(self):
        """The floor is the engine's own -1 (owner, 2026-10-20): it binds where mild hunger's deaths, which M nets, alone
        pass the census's rate, and the read then sits at -1. A births read of -0.5 no longer binds (it did at -0.8)."""
        eng = self._eng(cbr=2.0, cdr=0.5, read_b=-0.5, edr=self.EDR_HUNGER)
        eng.call("te_demog_rates_refresh")
        mb, md = self._want(2.0, 0.5, 475e6, 430e6, self.EBR, -0.5, 0.04, edr=self.EDR_HUNGER)
        self.assertGreater(mb, P.RATE_TOTAL_FLOOR + 0.5, "births unclamped")
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertAlmostEqual(md, P.RATE_TOTAL_FLOOR - 0.04)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)
        self.assertEqual(eng.vars["te_dg_rate_clamped"], 1)

    def test_script_never_pushes_past_the_terms_on_top(self):
        """Review Focus 5: the terms on top in the state read alone already past -1 (a plague event, a decree, an
        event modifier; starvation is per pop and never enters the read). The lines cut the census's rate to nothing;
        M nets only literacy's -0.1, so the read stays past -1 and no plain pop's births come back. Deaths: M would net
        mild hunger and can't, so it stays at 0, as demographics_model.rate_term's does, and an M of 0 takes neither
        modifier of the pair."""
        eng = self._eng(cbr=2.0, read_b=-1.2, read_d=-1.2, edr=self.EDR_HUNGER)
        eng.call("te_demog_rates_refresh")
        mb, md = self._want(2.0, 31.0, 475e6, 430e6, self.EBR, -1.2, -1.2, edr=self.EDR_HUNGER)
        self.assertAlmostEqual(mb, -self.EBR / 475e6)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertLess(-1.2 + eng.vars["te_dg_mb"], P.RATE_TOTAL_FLOOR)
        self.assertEqual(md, 0.0)
        self.assertEqual(eng.vars["te_dg_md"], 0.0)
        self.assertEqual(eng.vars["te_dg_rate_clamped"], 1)
        self.assertNotIn("te_demog_census_deaths_up", eng.modifiers)
        self.assertNotIn("te_demog_census_deaths_down", eng.modifiers)

    def test_the_prior_term_comes_off_the_read(self):
        """The state read holds last step's M: the clamp's 'other' takes it off."""
        eng = self._eng(cbr=2.0, read_b=-0.5)
        eng.modifiers["te_demog_census_births_down"] = 0.3
        eng.vars["te_dg_mb"] = -0.3
        eng.call("te_demog_rates_refresh")
        mb, _ = self._want(2.0, 31.0, 475e6, 430e6, self.EBR, -0.2, 0.04)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertAlmostEqual(eng.locals["te_dg_rate_prev_b"], -0.3)

    def test_the_refresh_leaves_its_terms_in_locals(self):
        """Fast mode runs next in the same effect, where has_modifier can't see this refresh's add or remove:
        the refresh leaves the terms in force as locals (the M it set, 0 when it clears, the prior when it skips)."""
        eng = self._eng()
        eng.call("te_demog_rates_refresh")
        self.assertEqual((eng.locals["te_dg_rate_new_b"], eng.locals["te_dg_rate_new_d"]),
                         (eng.vars["te_dg_mb"], eng.vars["te_dg_md"]))
        eng = self._eng(full=False)
        eng.modifiers["te_demog_census_births_down"] = 0.2
        eng.vars["te_dg_mb"] = -0.2
        eng.call("te_demog_rates_refresh")
        self.assertEqual((eng.locals["te_dg_rate_new_b"], eng.locals["te_dg_rate_new_d"]), (0, 0))
        eng = self._eng(stepped=0.0)
        eng.modifiers.update(te_demog_census_births_down=0.2, te_demog_census_deaths_up=0.1)
        eng.vars.update(te_dg_mb=-0.2, te_dg_md=0.1)
        eng.call("te_demog_rates_refresh")
        self.assertEqual((eng.locals["te_dg_rate_new_b"], eng.locals["te_dg_rate_new_d"]), (-0.2, 0.1))

    def test_the_prior_term_needs_the_modifier(self):
        """A state that lost its modifier (a change of owner, an old save) keeps te_dg_mb: no phantom term."""
        eng = self._eng()
        eng.vars.update(te_dg_mb=-0.3, te_dg_md=0.2)
        eng.call("te_demog_rates_refresh")
        self.assertEqual((eng.locals["te_dg_rate_prev_b"], eng.locals["te_dg_rate_prev_d"]), (0.0, 0.0))

    def test_a_seed_leaves_the_rates_alone(self):
        eng = self._eng(stepped=0.0, cbr=0.0, cdr=0.0)
        eng.modifiers["te_demog_census_births_down"] = 0.2
        eng.vars["te_dg_mb"] = -0.2
        eng.call("te_demog_rates_refresh")
        self.assertEqual(eng.vars["te_dg_mb"], -0.2)
        self.assertEqual(eng.modifiers, {"te_demog_census_births_down": 0.2})

    def test_a_fresh_seed_gets_no_term(self):
        eng = self._eng(stepped=0.0, cbr=0.0, cdr=0.0)
        eng.call("te_demog_rates_refresh")
        self.assertNotIn("te_dg_mb", eng.vars)
        self.assertEqual(eng.modifiers, {})

    def test_nobody_gets_no_term(self):
        eng = self._eng(eb0=0.0, ed0=0.0, ebr=0.0)
        eng.call("te_demog_rates_refresh")
        self.assertNotIn("te_dg_mb", eng.vars)

    def test_display_only_clears_the_rates(self):
        eng = self._eng(full=False)
        eng.modifiers.update(te_demog_census_births_down=0.2, te_demog_census_deaths_up=0.1)
        eng.vars.update(te_dg_mb=-0.2, te_dg_md=0.1, te_dg_rate_clamped=1.0, te_dg_os_b=0.1, te_dg_os_d=0.2,
                        te_dg_tb_b=0.8, te_dg_tb_d=0.6)
        eng.call("te_demog_rates_refresh")
        self.assertEqual(eng.modifiers, {})
        for var in ("te_dg_os_b", "te_dg_os_d", "te_dg_tb_b", "te_dg_tb_d"):
            self.assertNotIn(var, eng.vars)
        self.assertNotIn("te_dg_mb", eng.vars)
        self.assertNotIn("te_dg_md", eng.vars)
        self.assertNotIn("te_dg_rate_clamped", eng.vars, "the census line counts clamped states (Task 9)")
        self.assertNotIn("te_dg_rep_b", eng.vars)
        self.assertNotIn("te_dg_rep_d", eng.vars)

    def test_one_refresh_site(self):
        """Only te_demog_rates_apply adds or removes the census's modifiers, and only the two state-ROOT
        orchestrators call the refresh: the multiplier resolves against ROOT."""
        texts = {p: _text(p) for p in DEMOG_FILES}
        for name in ("te_demog_census_births_up", "te_demog_census_births_down", "te_demog_census_deaths_up",
                     "te_demog_census_deaths_down"):
            adders = [p.name for p, t in texts.items() if f"name = {name}" in t]
            self.assertEqual(adders, ["te_demog_rate_effects.txt"], name)
        callers = sorted(p.name for p, t in texts.items() if "te_demog_rates_refresh = yes" in t)
        self.assertEqual(callers, ["te_demog_effects.txt", "te_demog_fast_effects.txt"])
        self.assertIn("te_demog_rates_refresh = yes", _block(_text(EFFECTS), "te_demog_state_yearly"))
        self.assertIn("te_demog_rates_refresh = yes", _block(_text(FAST_EFFECTS), "te_demog_state_clock_step"))
        self.assertNotIn("te_demog_rates_refresh", _text(CONSOLE_EFFECTS))

    def test_the_refresh_comes_after_the_census_and_before_fast_mode(self):
        body = _block(_text(FAST_EFFECTS), "te_demog_state_clock_step")
        self.assertLess(body.index("te_demog_state_census = yes"), body.index("te_demog_rates_refresh = yes"))
        self.assertLess(body.index("te_demog_rates_refresh = yes"), body.index("te_demog_fast_refresh_rates = yes"))
        yearly = _block(_text(EFFECTS), "te_demog_state_yearly")
        self.assertLess(yearly.index("te_demog_state_census = yes"), yearly.index("te_demog_rates_refresh = yes"))

    def test_the_walk_sums_the_replaced_terms(self):
        """The generated init before the pop loop, the generated per-pop sums after each pop's bare curves."""
        body = _block(_text(EFFECTS), "te_demog_walks")
        self.assertLess(body.index("te_demog_absorbed_walk_init = yes"), body.index("every_scope_pop = {"))
        loop = body[body.index("every_scope_pop = {"):]
        self.assertLess(loop.index("set_local_variable = { name = te_dg_p_ed value = te_demog_pop_engine_deaths }"),
                        loop.index("te_demog_absorbed_walk_pop = yes"))
        self.assertNotIn("te_dg_w_ebl", body)

    # -- batch 2 review (I1): the deaths half, fast mode, the up side, a change of sign ----------

    def test_the_deaths_floor_matches_the_model(self):
        """The deaths half of the floor: the state read alone past -1 leaves M_d at 0 with no modifier; a prior deaths
        term comes off the read before the floor is set."""
        eng = self._eng(cdr=2.0, read_d=-1.2, edr=self.EDR_HUNGER)
        eng.call("te_demog_rates_refresh")
        _, md = self._want(38.0, 2.0, 475e6, 430e6, self.EBR, 0.05, -1.2, edr=self.EDR_HUNGER)
        self.assertEqual(md, 0.0)
        self.assertEqual(eng.vars["te_dg_md"], 0.0)
        self.assertEqual(eng.vars["te_dg_rate_clamped"], 1)
        self.assertFalse({"te_demog_census_deaths_up", "te_demog_census_deaths_down"} & set(eng.modifiers))
        eng = self._eng(cdr=2.0, read_d=-0.5, edr=self.EDR_HUNGER)
        eng.modifiers["te_demog_census_deaths_down"] = 0.3
        eng.vars["te_dg_md"] = -0.3
        eng.call("te_demog_rates_refresh")
        _, md = self._want(38.0, 2.0, 475e6, 430e6, self.EBR, 0.05, -0.2, edr=self.EDR_HUNGER)
        self.assertAlmostEqual(md, P.RATE_TOTAL_FLOOR + 0.2)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)
        self.assertAlmostEqual(eng.locals["te_dg_rate_prev_d"], -0.3)

    def test_fast_modes_terms_come_off_the_read(self):
        """Fast mode's +1 modifiers sit in the state read at (K - 1) x the average: the floors and the lines on top take
        them off, so 'other' is the read less the census's and fast mode's own terms. The deaths floor binds here (mild
        hunger's deaths pass the census's rate), so its -1 less 'other' shows it; births show it through the lines."""
        eng = self._eng(cbr=2.0, cdr=2.0, read_b=2.5, read_d=2.5, edr=self.EDR_HUNGER)
        eng.modifiers.update(te_demog_fast_births=3.0, te_demog_fast_deaths=3.0)
        eng.vars.update(te_dg_fast_fb=3.0, te_dg_fast_fd=3.0)
        eng.call("te_demog_rates_refresh")
        mb, md = self._want(2.0, 2.0, 475e6, 430e6, self.EBR, -0.5, -0.5, edr=self.EDR_HUNGER)
        self.assertAlmostEqual(mb, demographics_model.rate_term(2.0 * self.POP * 100 / 12, 475e6, absorbed=self.EBR,
                                                                other=-0.5, on_top=-0.5)[0])
        self.assertGreater(mb, P.RATE_TOTAL_FLOOR + 0.5)
        self.assertAlmostEqual(md, P.RATE_TOTAL_FLOOR + 0.5)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)

    def test_a_change_of_sign_swaps_the_pair(self):
        """M moving across 0 takes the old modifier off and puts the other side on at |M|, both kinds and both ways."""
        eng = self._eng(cbr=80.0, cdr=31.0, read_b=-0.25, read_d=0.24)
        eng.modifiers.update(te_demog_census_births_down=0.3, te_demog_census_deaths_up=0.2)
        eng.vars.update(te_dg_mb=-0.3, te_dg_md=0.2)
        eng.call("te_demog_rates_refresh")
        mb, md = self._want(80.0, 31.0, 475e6, 430e6, self.EBR, 0.05, 0.04)
        self.assertTrue(mb > 0 > md, (mb, md))
        self.assertEqual(set(eng.modifiers), {"te_demog_census_births_up", "te_demog_census_deaths_down"})
        self.assertAlmostEqual(eng.modifiers["te_demog_census_births_up"], mb, places=5)
        self.assertAlmostEqual(eng.modifiers["te_demog_census_deaths_down"], -md, places=5)
        eng = self._eng(cbr=38.0, cdr=80.0, read_b=0.35, read_d=-0.26)
        eng.modifiers.update(te_demog_census_births_up=0.3, te_demog_census_deaths_down=0.3)
        eng.vars.update(te_dg_mb=0.3, te_dg_md=-0.3)
        eng.call("te_demog_rates_refresh")
        mb, md = self._want(38.0, 80.0, 475e6, 430e6, self.EBR, 0.05, 0.04)
        self.assertTrue(mb < 0 < md, (mb, md))
        self.assertEqual(set(eng.modifiers), {"te_demog_census_births_down", "te_demog_census_deaths_up"})
        self.assertAlmostEqual(eng.modifiers["te_demog_census_births_down"], -mb, places=5)
        self.assertAlmostEqual(eng.modifiers["te_demog_census_deaths_up"], md, places=5)

    def test_an_m_of_zero_takes_no_modifier(self):
        # cdr 51.6 at a million people is 4.3e8 a month x 100,000: the bare deaths exactly
        eng = self._eng(cdr=51.6)
        eng.call("te_demog_rates_refresh")
        self.assertEqual(eng.vars["te_dg_md"], 0.0)
        self.assertFalse({"te_demog_census_deaths_up", "te_demog_census_deaths_down"} & set(eng.modifiers))

    def test_no_ceiling(self):
        """No ceiling (owner, 2026-10-20; it was +3): a target past seven times the bare curve is met, unflagged."""
        eng = self._eng(cdr=400.0)
        eng.call("te_demog_rates_refresh")
        _, md = self._want(38.0, 400.0, 475e6, 430e6, self.EBR, 0.05, 0.04)
        self.assertGreater(md, 3.0)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)
        self.assertEqual(eng.vars["te_dg_rate_clamped"], 0)
        self.assertEqual(eng.vars["te_dg_rate_clamp_d"], 0)

    def test_a_walk_under_one_person_leaves_the_terms(self):
        """The class-C guard that replaces the ceiling's one job: a walk under te_demog_k_rate_bare_min (less than one
        person at the curves' lowest, in the walk's units: people x the curve per 100,000 a month) has nothing to fit
        M to, so the terms stay as they were and no start rate is stored, as for a seed."""
        for eb0, ed0 in ((79.0, 430e6), (475e6, 79.0)):
            with self.subTest(eb0=eb0, ed0=ed0):
                eng = self._eng(eb0=eb0, ed0=ed0)
                eng.modifiers["te_demog_census_deaths_down"] = 0.3
                eng.vars.update(te_dg_md=-0.3, te_dg_sr_d=1.0)
                eng.call("te_demog_rates_refresh")
                self.assertEqual(eng.vars["te_dg_md"], -0.3)
                self.assertEqual(eng.modifiers, {"te_demog_census_deaths_down": 0.3})
                self.assertNotIn("te_dg_sr_d", eng.vars)
                self.assertAlmostEqual(eng.locals["te_dg_rate_new_d"], -0.3)
        self.assertEqual(P.RATE_BARE_MIN, 80.0)   # the births curve's lowest, 80 a month per 100,000 (SoL 35 and above)

    # -- batch 2 review (m1, m5): the real seed path, and who calls the orchestrators ------------

    def _pulse(self, refresh=None):
        """A state through te_demog_state_yearly under Full, its walks stubbed with fixed sums (TestCohortScript's
        inputs); refresh replaces te_demog_rates_refresh's text (for the guards' checks)."""
        pop = TestCohortScript.POP
        eb0, ed0 = 475.0 * pop, 400.0 * pop
        walk = "\n".join(f"set_local_variable = {{ name = {k} value = {v!r} }}" for k, v in (
            ("te_dg_w_eb0", eb0), ("te_dg_w_ed0", ed0), ("te_dg_w_ebr", P.LITERACY_BIRTH_PENALTY * 0.35 * eb0), ("te_dg_w_edr", 0.0), ("te_dg_w_eb", eb0),
            ("te_dg_w_ed", ed0), ("te_dg_w_eb0m", eb0), ("te_dg_w_ed0m", ed0), ("te_dg_w_sev", 0.0), ("te_dg_w_sevd", 0.0)))
        walk += "\n" + "\n".join(f"set_variable = {{ name = {k} value = {v!r} }}" for k, v in (
            ("te_dg_eb", eb0 * 12 / 1e5), ("te_dg_ed", ed0 * 12 / 1e5), ("te_dg_walk_pop", pop)))
        stubs = {"te_demog_walks": walk, "te_inh_refresh_rural_effects": "", "te_demog_wc_state_yearly": "",
                 "te_inh_refresh_wc_state_effects": "", "te_demog_flows": "te_demog_no_flows = yes"}
        eng = _engine_for(TestCohortScript.INP, 1836, pop, effects=stubs)
        eng.trigger_fixtures["te_demog_effects_run"] = True
        eng.fixtures.update({"modifier:state_birth_rate_mult": 0.02, "modifier:state_mortality_mult": 0.01,
                             **{f"modifier:{name}": 0.0 for name in P.ENGINE_LINE_TYPES.values()}})
        if refresh is not None:
            eng.effects["te_demog_rates_refresh"] = refresh
        return eng

    def test_a_reseed_on_the_pulse_leaves_m_alone(self):
        """The real seed path (batch 2 review, m1): a step sets M; a re-seed on the pulse (te_dg_reseed) removes the
        model's rates (te_demog_seed), and the refresh then leaves M, its modifiers and the locals fast mode reads as
        they were. Either of its seed guards (te_dg_stepped above 0; the model's rates present) is enough alone; with
        neither it would read a target the seed removed or no step wrote (in game, 0: births at about a fifth for a
        year)."""
        body = _raw_blocks([RATE_EFFECTS])["te_demog_rates_refresh"]
        stepped = "limit = { var:te_dg_stepped > 0 }"
        cases = {"as written": body,
                 "no model-rate guards": re.sub(r"has_variable = te_dg_c[bd]r_model\s*", "", body),
                 "no stepped guard": body.replace(stepped, "limit = { always = yes }")}
        self.assertNotEqual(len(set(cases.values())), 1, "the guards' text moved")
        # M's modifiers only: phase 2 step 4's (te_demog_consequences_refresh) follow every census, a seed's too
        def m_mods(eng):
            return {k: v for k, v in eng.modifiers.items()
                    if k.startswith(("te_demog_census_births", "te_demog_census_deaths", "te_demog_census_wealth"))}
        for label, refresh in cases.items():
            with self.subTest(label):
                eng = self._pulse(refresh)
                eng.call("te_demog_state_yearly")            # 1836: no census, a seed
                self.assertEqual(eng.vars["te_dg_stepped"], 0)
                self.assertNotIn("te_dg_mb", eng.vars)
                self.assertEqual(m_mods(eng), {})
                eng.fixtures["year"] = 1837.0
                eng.call("te_demog_state_yearly")            # 1837: a step, and M
                mb, md, mods = eng.vars["te_dg_mb"], eng.vars["te_dg_md"], m_mods(eng)
                self.assertTrue(mods)
                eng.fixtures["year"] = 1838.0
                eng.vars["te_dg_reseed"] = 1.0
                eng.call("te_demog_state_yearly")            # 1838: a re-seed on the pulse
                self.assertEqual(eng.vars["te_dg_stepped"], 0)
                self.assertNotIn("te_dg_cbr_model", eng.vars)
                self.assertEqual((eng.vars["te_dg_mb"], eng.vars["te_dg_md"], m_mods(eng)), (mb, md, mods))
                self.assertEqual((eng.locals["te_dg_rate_new_b"], eng.locals["te_dg_rate_new_d"]), (mb, md))
        # with neither, the very first seed's refresh reads a target no step has written
        eng = self._pulse(cases["no model-rate guards"].replace(stepped, "limit = { always = yes }"))
        with self.assertRaisesRegex(AssertionError, "te_dg_cbr_model"):
            eng.call("te_demog_state_yearly")

    def test_the_orchestrators_run_with_root_the_state(self):
        """The census's multipliers resolve against ROOT (batch 2 review, m5): the two effects that call the refresh
        are reached only from the yearly state pulse and fast mode's state event, te_demog_events.2."""
        files = [*ROOT.glob("common/**/*.txt"), *ROOT.glob("events/*.txt")]
        texts = {p: _text(p) for p in files}
        for call, where in (("te_demog_state_yearly = yes", "te_demog_on_actions.txt"),
                            ("te_demog_state_clock_step = yes", "te_demog_events.txt")):
            sites = [(p.name, t.count(call)) for p, t in texts.items() if call in t]
            self.assertEqual(sites, [(where, 1)], call)
        on_actions = _text(ROOT / "common" / "on_actions" / "te_demog_on_actions.txt")
        self.assertIn("te_demog_state_yearly = yes", _block(on_actions, "te_demog_state_yearly_on_action"))
        self.assertIn("te_demog_state_yearly_on_action", _block(on_actions, "on_yearly_pulse_state"))
        clock = _block(_text(FAST_EVENTS), "te_demog_events.2")
        self.assertIn("type = state_event", clock)
        self.assertIn("te_demog_state_clock_step = yes", clock)

    def test_the_census_modifiers_are_hidden(self):
        """Owner, 2026-10-10: the census's modifiers don't show in a state's modifier list. They take the mod's
        invisible icon for bookkeeping modifiers (modifier_system.dds, 4x4 and transparent, as tourism and migration
        crowding do), which the list's filter (#872) keys on. Their names still head the birth and mortality
        breakdowns."""
        mods = _raw_blocks([ROOT / "common" / "static_modifiers" / "te_demog_modifiers.txt"])
        for name in ("te_demog_census_births_up", "te_demog_census_births_down", "te_demog_census_deaths_up",
                     "te_demog_census_deaths_down"):
            self.assertIn("icon = gfx/interface/icons/timed_modifier_icons/modifier_system.dds", mods[name], name)

    def test_the_census_modifiers_are_fixed_sign_unit_fields(self):
        mods = _raw_blocks([ROOT / "common" / "static_modifiers" / "te_demog_modifiers.txt"])
        for name, field, value in (("te_demog_census_births_up", "state_birth_rate_mult", "1"),
                                   ("te_demog_census_births_down", "state_birth_rate_mult", "-1"),
                                   ("te_demog_census_deaths_up", "state_mortality_mult", "1"),
                                   ("te_demog_census_deaths_down", "state_mortality_mult", "-1")):
            got = dict(re.findall(r"^\s*(\w+) = (\S+)", mods[name], re.M))
            got.pop("icon")
            self.assertEqual(got, {field: value}, name)


class _Pop(tuple):
    """One pop group for TestWindowEvents' engine: bare births and deaths a month x 100,000, the terms the census
    absorbs for it (literacy's, mild starvation's) and its own terms on top (severe starvation, workplace lines)."""
    __slots__ = ()

    def __new__(cls, bare_b, bare_d, abs_b=0.0, abs_d=0.0, top_b=0.0, top_d=0.0):
        return tuple.__new__(cls, (bare_b, bare_d, abs_b, abs_d, top_b, top_d))


def _mild(bare_b, bare_d, food=0.21):
    b, d = demographics_model.starvation_terms(food)
    return _Pop(bare_b, bare_d, abs_b=b, abs_d=d)


def _severe(bare_b, bare_d, food=0.13):
    """Severely starving: severe_starvation_penalty x the starvation value, on top (the famine probe, 2026-10-11).
    Food security 0.13 is Germany's severe pops in early 1898 (starvation value 0.68)."""
    b, d = demographics_model.starvation_terms(food)
    return _Pop(bare_b, bare_d, top_b=b, top_d=d)


class _ClockEngine(_Engine):
    """_Engine plus what fast mode's switch (te_demog_fast_set) needs, for one state that is also the country:
    every_state and every_country run their body here (their limit too), set_global_variable sets the global as a
    fixture, debug_log does nothing."""

    SPECIAL = ("every_state", "every_country", "set_global_variable", "debug_log")

    @classmethod
    def adopt(cls, eng):
        new = cls.__new__(cls)
        new.__dict__.update(eng.__dict__)
        return new

    def run(self, items):
        segment = []
        for item in items:
            key, _, arg = item
            if key not in self.SPECIAL:
                segment.append(item)
                continue
            super().run(segment)
            segment = []
            if key == "set_global_variable":
                self.fixtures[f"global_var:{_find(arg, 'name')}"] = self.value(_find(arg, "value"))
            elif key in ("every_state", "every_country"):
                limit = [i for i in arg if i[0] == "limit"]
                if not limit or self.holds(limit[0][2]):
                    self.run([i for i in arg if i[0] != "limit"])
        super().run(segment)


class TestWindowEvents(unittest.TestCase):
    """The trapezoid (owner, 2026-10-11; #894; the review of #907). The walk is a snapshot on the step's day and the
    step books the window that ends that day, so a famine starting in early December was booked for the whole year
    (Hannover, 1898). Under Full the walk's tail (te_demog_window_events) books the window at the mean of the
    engine's rate at its two ends: today's, and the rate per head the last step left in force (te_dg_sr_b / _d,
    stored by te_demog_rates_refresh after it set M, moved by fast mode's term). The residual and the step's scales
    read the result.

    Each case is checked against an engine built from pops, not against the script's arithmetic: each pop gives
    bare x max(0, 1 + the state read + its own terms), the read holds the census's term, fast mode's and the moved
    lines' pairs and the state-level lines, and the window's true events are the mean of the two ends' sums x the
    window's months."""

    POP = 1_000_000.0
    CBR, CDR = 38.0, 31.0

    def walk(self, pops, read_b, read_d):
        """The walk's sums for these pops under these reads (te_demog_walks)."""
        w = dict(te_dg_w_eb0=0.0, te_dg_w_ed0=0.0, te_dg_w_ebr=0.0, te_dg_w_edr=0.0, te_dg_w_eb=0.0, te_dg_w_ed=0.0,
                 te_dg_w_eb0m=0.0, te_dg_w_ed0m=0.0, te_dg_w_sev=0.0, te_dg_w_sevd=0.0)
        for bare_b, bare_d, abs_b, abs_d, top_b, top_d in pops:
            mult_b, mult_d = max(0.0, 1 + read_b + abs_b + top_b), max(0.0, 1 + read_d + abs_d + top_d)
            w["te_dg_w_eb0"] += bare_b
            w["te_dg_w_ed0"] += bare_d
            w["te_dg_w_ebr"] += bare_b * abs_b
            w["te_dg_w_edr"] += bare_d * abs_d
            w["te_dg_w_eb"] += bare_b * mult_b
            w["te_dg_w_ed"] += bare_d * mult_d
            w["te_dg_w_eb0m"] += bare_b if mult_b > 0 else 0.0
            w["te_dg_w_ed0m"] += bare_d if mult_d > 0 else 0.0
        return w

    def _engine(self, full=True):
        families = {f"modifier:{name}": 0.0 for name in P.ENGINE_LINE_TYPES.values()}
        eng = _Engine({"state_population": self.POP, **families},
                      triggers={"te_demog_effects_run": full, "te_demog_cohorts_run": True})
        return eng

    def _set_reads(self, eng, os_b, os_d, lines=(0.0, 0.0)):
        """The state reads as the engine sums them: the terms in force (modifiers) plus the state-level lines."""
        def applied(kind):
            return eng.value(eng._tree(eng.values, f"te_demog_rate_{kind}_applied")) + \
                eng.value(eng._tree(eng.values, f"te_demog_fast_{kind}_applied"))
        eng.fixtures["modifier:state_birth_rate_mult"] = applied("births") + lines[0] + os_b
        eng.fixtures["modifier:state_mortality_mult"] = applied("deaths") + lines[1] + os_d
        return eng.fixtures["modifier:state_birth_rate_mult"], eng.fixtures["modifier:state_mortality_mult"]

    def window(self, start_pops, end_pops, os_start=(0.02, 0.05), os_end=(0.02, 0.05), m_prev=(-0.3, -0.25),
               months=12, fast_k=None, fast_at_end=None, lines=(0.0, 0.0), full=True):
        """One window. At its start the state steps: the walk under the last window's terms, then
        te_demog_rates_refresh (M refitted to the model's rates) and, on fast mode's clock, te_demog_fast_refresh_rates
        (K = fast_k; None: no clock at that step). At its end the walk runs under the terms the start left in force
        and ends with te_demog_window_events; fast_at_end puts the clock on at the end (window of `months`) without
        a step between (a switch of speed). Returns the engine, the window's events (births, deaths) as the script books
        them, and as the pops' engine gave them: the mean of the two ends' rates x the window's months."""
        eng = self._engine(full)
        mb, md = m_prev
        eng.modifiers.update({"te_demog_census_births_down" if mb < 0 else "te_demog_census_births_up": abs(mb),
                              "te_demog_census_deaths_down" if md < 0 else "te_demog_census_deaths_up": abs(md)})
        eng.vars.update(te_dg_mb=mb, te_dg_md=md, te_dg_stepped=1.0, te_dg_cbr_model=self.CBR,
                        te_dg_cdr_model=self.CDR)
        if lines != (0.0, 0.0):
            eng.modifiers.update(te_demog_line_births_down=-lines[0], te_demog_line_deaths_down=-lines[1])
            eng.vars.update(te_dg_ln_births=lines[0], te_dg_ln_deaths=lines[1])
        if fast_k is not None:
            eng.trigger_fixtures["te_demog_clock_on"] = True
            eng.fixtures["global_var:te_demog_months_per_step"] = 12.0 / fast_k
            eng.fixtures["global_var:te_demog_window_months"] = 12.0 / fast_k
        # the window's start: the step
        read = self._set_reads(eng, *os_start, lines=lines)
        eng.locals.update(self.walk(start_pops, *read))
        eng.call("te_demog_rates_refresh")
        if fast_k is not None:
            eng.call("te_demog_fast_refresh_rates")
        # the terms the start left in force; the pops' engine at the start runs under them
        eng.locals.clear()
        if fast_at_end is not None:
            eng.trigger_fixtures["te_demog_clock_on"] = True
            eng.fixtures["global_var:te_demog_months_per_step"] = float(months)
            eng.fixtures["global_var:te_demog_window_months"] = float(months)
        elif fast_k is not None:
            eng.fixtures["global_var:te_demog_window_months"] = float(months)
        read_start = self._set_reads(eng, *os_start)
        true_start = self.walk(start_pops, *read_start)
        # the window's end: the walk, under the same terms, with today's pops and lines
        read_end = self._set_reads(eng, *os_end)
        end = self.walk(end_pops, *read_end)
        eng.locals.update(end)
        eng.vars.update(te_dg_eb=end["te_dg_w_eb"] * months / 1e5, te_dg_ed=end["te_dg_w_ed"] * months / 1e5)
        snap = (eng.vars["te_dg_eb"], eng.vars["te_dg_ed"])
        eng.call("te_demog_window_events")
        booked = (eng.vars["te_dg_eb"], eng.vars["te_dg_ed"])
        true = tuple((true_start[f"te_dg_w_{k}"] + end[f"te_dg_w_{k}"]) / 2 * months / 1e5 for k in ("eb", "ed"))
        return eng, booked, true, snap

    STEADY = [_Pop(300e6, 260e6), _Pop(175e6, 170e6, abs_b=-0.05)]

    def assert_books(self, booked, true, rel=1e-6):
        for got, want, kind in zip(booked, true, ("births", "deaths")):
            self.assertAlmostEqual(got, want, delta=rel * max(abs(want), 1.0), msg=kind)

    def test_mild_starvation_at_the_start_severe_at_the_end(self):
        """Hannover 1897-98: the unemployed laborers mildly starving when the window began (absorbed: M nets it) and
        severely on the step's day (on top). The window takes the mean, mild's netted line included."""
        start = [self.STEADY[0], _mild(175e6, 170e6)]
        end = [self.STEADY[0], _severe(175e6, 170e6)]
        eng, booked, true, snap = self.window(start, end)
        self.assert_books(booked, true)
        # the snapshot's famine year is cut by half the famine pop's line change (mild's absorbed +0.285 at food
        # security 0.21 to severe's +0.675 at 0.13, both x the starvation value) on its bare curve
        _b, bare_d, _ab, mild_d, _tb, _td = start[1]
        severe_d = end[1][5]
        self.assertGreater(severe_d, mild_d)
        self.assertAlmostEqual(snap[1] - booked[1], bare_d * (severe_d - mild_d) / 2 * 12 / 1e5, delta=1e-3)

    def test_a_famine_ending_in_the_window(self):
        start = [self.STEADY[0], _severe(175e6, 170e6)]
        end = [self.STEADY[0], _mild(175e6, 170e6, food=0.37)]
        _, booked, true, snap = self.window(start, end)
        self.assert_books(booked, true)
        self.assertGreater(booked[1], snap[1])

    def test_a_state_line_moving_counts_at_the_engines_weight(self):
        """Devastation from nothing to +0.3 inside the window: the engine adds it to every pop's bare curve, so the
        window books half of bare x 0.3, not half of the census's rate x 0.3."""
        _, booked, true, snap = self.window(self.STEADY, self.STEADY, os_start=(0.0, 0.0), os_end=(-0.1, 0.3))
        self.assert_books(booked, true)
        bare_d = sum(p[1] for p in self.STEADY)
        self.assertAlmostEqual(snap[1] - booked[1], bare_d * 0.3 / 2 * 12 / 1e5, delta=1e-3)

    def test_a_steady_window_keeps_the_snapshot(self):
        """Nothing moved inside the window: the mean of its ends is the snapshot, whatever M the step set."""
        for m_prev in ((-0.3, -0.25), (0.4, 0.6)):
            with self.subTest(m_prev=m_prev):
                _, booked, true, snap = self.window(self.STEADY, self.STEADY, m_prev=m_prev)
                self.assert_books(booked, true)
                self.assert_books(booked, snap)

    def test_the_start_holds_the_steps_m_and_not_the_moved_lines_pairs_it_cleared(self):
        """The first Full step clears the moved lines' pairs, which were in the walk's read: the window's start runs
        without them and with the M the refresh set."""
        _, booked, true, _snap = self.window(self.STEADY, self.STEADY, lines=(-0.02, -0.08))
        self.assert_books(booked, true)

    def test_fast_mode_books_the_clocks_window(self):
        """At K = 4 a window is three months, its term (K - 1 x the average) set at the start and held to the end:
        both ends carry it, so the window is the mean of the two ends x 3 months."""
        start = [self.STEADY[0], _mild(175e6, 170e6)]
        end = [self.STEADY[0], _severe(175e6, 170e6)]
        eng, booked, true, _snap = self.window(start, end, fast_k=4, months=3)
        self.assertIn("te_demog_fast_deaths", eng.modifiers)
        self.assert_books(booked, true)

    def test_back_to_fast_mode_inside_a_window_at_normal_speed(self):
        """Options k, then h: the clock's step at normal speed (K = 1) sets no term, and h puts the clock back at three
        months a step without one until the next step. The window is three months with no term at either end."""
        start = [self.STEADY[0], _mild(175e6, 170e6)]
        end = [self.STEADY[0], _severe(175e6, 170e6)]
        eng, booked, true, _snap = self.window(start, end, fast_k=1, fast_at_end=True, months=3)
        self.assertNotIn("te_demog_fast_deaths", eng.modifiers)
        self.assert_books(booked, true)

    def test_option_k_between_two_clock_steps_falls_back_to_the_snapshot(self):
        """Option k (te_demog_fast_set at 12 months a step) takes fast mode's term off every state at once, between two
        clock steps, so the rate the last step stored (with the term, about K times the engine's) no longer runs: it
        goes, and the next window takes the snapshot, as before the trapezoid. Here k comes straight after a step at
        K = 4 and the next step is 12 months later: the engine ran without the term all window."""
        eng, *_ = self.window(self.STEADY, self.STEADY, fast_k=4, months=3)
        self.assertIn("te_demog_fast_deaths", eng.modifiers)
        self.assertIn("te_dg_sr_d", eng.vars)
        clock = _ClockEngine.adopt(eng)
        switch = re.sub(r'debug_log = "[^"]*"', "", _block(_text(FAST_EFFECTS), "te_demog_fast_set"))
        clock.run(_parse_script(switch.replace("$MONTHS$", "12")))
        self.assertEqual(clock.fixtures["global_var:te_demog_months_per_step"], 12.0)
        self.assertFalse({"te_demog_fast_births", "te_demog_fast_deaths"} & set(clock.modifiers))
        self.assertFalse({"te_dg_sr_b", "te_dg_sr_d"} & set(clock.vars))
        # twelve months on, the clock's step: the walk under the census's terms alone
        clock.locals.clear()
        clock.fixtures["global_var:te_demog_window_months"] = 12.0
        read = self._set_reads(clock, 0.02, 0.05)
        end = self.walk(self.STEADY, *read)
        clock.locals.update(end)
        clock.vars.update(te_dg_eb=end["te_dg_w_eb"] * 12 / 1e5, te_dg_ed=end["te_dg_w_ed"] * 12 / 1e5)
        clock.call("te_demog_window_events")
        true = tuple(end[f"te_dg_w_{k}"] * 12 / 1e5 for k in ("eb", "ed"))   # a steady engine without the term
        self.assert_books((clock.vars["te_dg_eb"], clock.vars["te_dg_ed"]), true)

    def test_a_step_with_no_births_moves_the_terms(self):
        """A step that recorded no births is still a step (te_dg_stepped 1): the refresh moves M's births term toward the
        census's 0, to the floor, instead of keeping the term an earlier step left. The late game's births read 0 under
        a TFR of 2 before the fixed-point fix of 2026-10-16, and their states' terms froze for decades."""
        eng = self._engine()
        eng.vars.update(te_dg_mb=-0.3, te_dg_md=-0.25, te_dg_stepped=1.0, te_dg_cbr_model=0.0,
                        te_dg_cdr_model=self.CDR)
        eng.modifiers.update(te_demog_census_births_down=0.3, te_demog_census_deaths_down=0.25)
        eng.locals.update(self.walk(self.STEADY, *self._set_reads(eng, 0.02, 0.05)))
        eng.call("te_demog_rates_refresh")
        # the census's 0 births: the read goes to -1 plus literacy's netted -0.1, which then takes each pop to 0 itself
        want, clamped = demographics_model.rate_term(0.0, eng.locals["te_dg_w_eb0"], absorbed=eng.locals["te_dg_w_ebr"],
                                                     other=0.02, on_top=0.02)
        self.assertFalse(clamped)
        self.assertLess(eng.vars["te_dg_mb"], -0.3)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], want, places=5)
        self.assertEqual(eng.vars["te_dg_rate_clamped"], 0)
        self.assertAlmostEqual(eng.modifiers["te_demog_census_births_down"], -eng.vars["te_dg_mb"])

    def test_a_lost_term_comes_back_within_a_month(self):
        """#937: te_demog_rates_heal, beside the moved lines' refresh in the monthly and owner-change hooks and
        te_demog_events.4. A state holding M's variables without the modifiers they call for has them back; the pair's
        gate (te_demog_lines_apply) reads only te_dg_mb, so it would otherwise have neither M nor the pair."""
        terms = dict(te_dg_mb=-0.3, te_dg_md=0.2, te_dg_w=-0.1)
        want = {"te_demog_census_births_down": 0.3, "te_demog_census_deaths_up": 0.2, "te_demog_census_wealth_down": 0.1}
        for lost in (list(want), ["te_demog_census_deaths_up"]):
            with self.subTest(lost=lost):
                eng = self._engine()
                eng.vars.update(terms)
                eng.modifiers.update({k: v for k, v in want.items() if k not in lost})
                eng.call("te_demog_rates_heal")
                self.assertEqual(set(eng.modifiers), set(want))
                for name, mult in want.items():
                    self.assertAlmostEqual(eng.modifiers[name], mult, msg=name)
        eng = self._engine(full=False)
        eng.vars.update(terms)
        eng.call("te_demog_rates_heal")
        self.assertEqual(eng.modifiers, {}, "outside Full the census's next refresh clears M instead")
        eng = self._engine()
        eng.vars.update(te_dg_mb=0.0, te_dg_md=0.0, te_dg_w=0.0)
        eng.call("te_demog_rates_heal")
        self.assertEqual(eng.modifiers, {}, "terms of 0 call for no modifier")
        on_actions = _text(ROOT / "common" / "on_actions" / "te_demog_on_actions.txt")
        self.assertIn("te_demog_rates_heal = yes", _block(on_actions, "te_demog_lines_on_action"))
        self.assertIn("te_demog_rates_heal = yes", _block(_text(ROOT / "events" / "te_demog_events.txt"),
                                                         "te_demog_events.4"))

    def test_a_refresh_that_sets_no_term_drops_the_start_rate(self):
        """A seed (te_dg_stepped 0) sets no term: the rate stored a window earlier is not this window's
        start, so it goes and the next window takes the snapshot."""
        eng = self._engine()
        eng.vars.update(te_dg_mb=-0.3, te_dg_md=-0.25, te_dg_stepped=0.0, te_dg_cbr_model=self.CBR,
                        te_dg_cdr_model=self.CDR, te_dg_sr_b=400.0, te_dg_sr_d=300.0)
        eng.modifiers.update(te_demog_census_births_down=0.3, te_demog_census_deaths_down=0.25)
        eng.locals.update(self.walk(self.STEADY, *self._set_reads(eng, 0.02, 0.05)))
        eng.call("te_demog_rates_refresh")
        self.assertFalse({"te_dg_sr_b", "te_dg_sr_d"} & set(eng.vars))
        self.assertEqual(eng.vars["te_dg_md"], -0.25, "the terms stay as they were")

    def test_no_start_rate_or_not_full_is_the_snapshot(self):
        """The first step after a seed, a new state, an old save (no te_dg_sr_*); outside Full."""
        eng = self._engine()
        eng.locals.update(self.walk(self.STEADY, 0.0, 0.0))
        eng.vars.update(te_dg_eb=123.0, te_dg_ed=456.0)
        eng.call("te_demog_window_events")
        self.assertEqual((eng.vars["te_dg_eb"], eng.vars["te_dg_ed"]), (123.0, 456.0))
        eng = self._engine(full=False)
        eng.locals.update(self.walk(self.STEADY, 0.0, 0.0))
        eng.vars.update(te_dg_eb=123.0, te_dg_ed=456.0, te_dg_sr_b=1.0, te_dg_sr_d=1.0)
        eng.call("te_demog_window_events")
        self.assertEqual((eng.vars["te_dg_eb"], eng.vars["te_dg_ed"]), (123.0, 456.0))

    def test_the_window_never_expects_fewer_than_no_events(self):
        eng = self._engine()
        eng.locals.update(self.walk([_Pop(0.0, 0.0)], 0.0, 0.0))
        eng.vars.update(te_dg_eb=0.0, te_dg_ed=0.0, te_dg_sr_b=-5.0, te_dg_sr_d=-5.0)
        eng.call("te_demog_window_events")
        self.assertEqual((eng.vars["te_dg_eb"], eng.vars["te_dg_ed"]), (0.0, 0.0))

    def test_a_seed_or_leaving_full_drops_the_start_rate(self):
        """A seed starts the census over (te_demog_seed); Display only and Disabled clear the census's terms
        (te_demog_rates_clear). Either way the next window has no start rate."""
        eng = _engine_for(TestCohortScript.INP, 1836, TestCohortScript.POP)
        eng.vars.update(te_dg_sr_b=400.0, te_dg_sr_d=300.0)
        eng.call("te_demog_seed")
        self.assertFalse({"te_dg_sr_b", "te_dg_sr_d"} & set(eng.vars))
        eng = self._engine(full=False)
        eng.vars.update(te_dg_mb=-0.3, te_dg_md=-0.25, te_dg_stepped=1.0, te_dg_cbr_model=self.CBR,
                        te_dg_cdr_model=self.CDR, te_dg_sr_b=400.0, te_dg_sr_d=300.0)
        eng.locals.update(self.walk(self.STEADY, *self._set_reads(eng, 0.02, 0.05)))
        eng.call("te_demog_rates_refresh")
        self.assertFalse({"te_dg_sr_b", "te_dg_sr_d"} & set(eng.vars))

    def test_the_walk_books_its_window_before_anything_reads_it(self):
        """Its tail, once, after te_dg_eb and te_dg_ed; the census (te_demog_flows' residual, te_demog_on_top_scales)
        runs after the walk in both orchestrators. Nothing else calls it: the step and the console's replay read the
        stored events, never the walk's locals."""
        body = _block(_text(EFFECTS), "te_demog_walks")
        self.assertEqual(body.count("te_demog_window_events = yes"), 1)
        self.assertLess(body.index("name = te_dg_ed"), body.index("te_demog_window_events = yes"))
        callers = sorted(p.name for p in DEMOG_FILES if "te_demog_window_events = yes" in _text(p))
        self.assertEqual(callers, ["te_demog_effects.txt"])
        self.assertNotIn("te_dg_w_", _block(_text(RATE_EFFECTS), "te_demog_on_top_scales"))

    # -- through the state's pulses: the window's start is the last step's -----------------------------------------

    def test_through_the_pulses_a_famine_is_booked_where_it_fell(self):
        """te_demog_state_yearly under Full, 1836 (a seed) to 1843, the walk stubbed with sums from pops under the read
        in force (the census's terms plus the state lines), ending with the real te_demog_window_events. A third of the
        bare curves mildly starving until 1838, severe on the step days of 1839 and 1840, fed again by 1841, and
        severe on 1842's day alone. Each step's window, its dz and its migration residual follow the pops' engine:
        the mean of the rate the last step left in force and today's. The first step after the seed has no start
        rate and books its snapshot."""
        pop = TestCohortScript.POP
        steady, other = _Pop(300.0 * pop, 230.0 * pop), (175.0 * pop, 170.0 * pop)
        plan = ["mild", "mild", "mild", "severe", "severe", "fed", "severe", "fed"]
        pops_of = {"mild": [steady, _mild(*other)], "severe": [steady, _severe(*other)], "fed": [steady, _Pop(*other)]}
        pop = TestCohortScript.POP
        stubs = {"te_inh_refresh_rural_effects": "", "te_demog_wc_state_yearly": "", "te_inh_refresh_wc_state_effects": ""}
        eng = _engine_for(TestCohortScript.INP, 1836, pop, effects=stubs)
        eng.trigger_fixtures["te_demog_effects_run"] = True
        eng.fixtures.update(te_demog_crisis=0.0, te_demog_family_transport=0.0,
                            **{f"modifier:{name}": 0.0 for name in P.ENGINE_LINE_TYPES.values()})
        rows, last = [], None
        for i, state in enumerate(plan):
            year = 1836 + i
            eng.fixtures["year"] = float(year)
            read = self._set_reads(eng, 0.02, 0.05)
            w = self.walk(pops_of[state], *read)
            true_start = self.walk(pops_of[last], *read) if last else None
            eng.effects["te_demog_walks"] = "\n".join(
                [f"set_local_variable = {{ name = {k} value = {v!r} }}" for k, v in w.items()]
                + [f"set_variable = {{ name = {k} value = {v!r} }}" for k, v in (
                    ("te_dg_eb", w["te_dg_w_eb"] * 12 / 1e5), ("te_dg_ed", w["te_dg_w_ed"] * 12 / 1e5),
                    ("te_dg_walk_pop", pop), ("te_dg_fjob_share", 0.3))]
                + ["te_demog_window_events = yes"])
            eng._trees.clear()
            had_start = "te_dg_sr_d" in eng.vars
            pop_last = eng.vars.get("te_dg_pop_last")
            target = eng.vars.get("te_dg_cdr_model", 0.0) * pop / 1000
            eng.call("te_demog_state_yearly")
            rows.append(dict(state=state, had_start=had_start, snap=w["te_dg_w_ed"] * 12 / 1e5,
                             true=None if true_start is None else (
                                 (true_start["te_dg_w_eb"] + w["te_dg_w_eb"]) / 2 * 12 / 1e5,
                                 (true_start["te_dg_w_ed"] + w["te_dg_w_ed"]) / 2 * 12 / 1e5),
                             eb=eng.vars["te_dg_eb"], ed=eng.vars["te_dg_ed"], dz=eng.vars["te_dg_dz"], target=target,
                             mig=eng.vars.get("te_dg_mig_raw"), pop_last=pop_last, stepped=eng.vars["te_dg_stepped"]))
            last = state
        self.assertEqual([r["stepped"] for r in rows], [0.0] + [1.0] * 7)
        self.assertFalse(rows[1]["had_start"], "the first step after a seed has no start rate")
        self.assertEqual(rows[1]["ed"], rows[1]["snap"])
        for i in range(2, len(plan)):
            r = rows[i]
            with self.subTest(year=1836 + i, plan=r["state"]):
                self.assertTrue(r["had_start"])
                self.assert_books((r["eb"], r["ed"]), r["true"])
                self.assertAlmostEqual(r["dz"], demographics_model.on_top_scale(r["ed"], r["target"]), places=4)
                self.assertAlmostEqual(r["mig"], pop - r["pop_last"] - r["eb"] + r["ed"], delta=1e-2)
        # onset and end book between the two; a one-off on a step's day is booked half there, half in the next
        self.assertLess(rows[3]["ed"], rows[3]["snap"])
        self.assertGreater(rows[5]["ed"], rows[5]["snap"])
        self.assertAlmostEqual(rows[6]["ed"] - rows[6]["snap"], -(rows[7]["ed"] - rows[7]["snap"]), delta=1.0)


class _SPop(tuple):
    """One pop group for TestOnTopSplitScript: _Pop's fields, severe starvation's part of its own deaths terms (sev_d,
    inside top_d) and its people."""
    __slots__ = ()

    def __new__(cls, bare_b, bare_d, abs_b=0.0, abs_d=0.0, top_b=0.0, top_d=0.0, sev_d=0.0, people=0.0):
        return tuple.__new__(cls, (bare_b, bare_d, abs_b, abs_d, top_b, top_d, sev_d, people))


def _s_mild(bare_b, bare_d, people, food=0.21):
    b, d = demographics_model.starvation_terms(food)
    return _SPop(bare_b, bare_d, abs_b=b, abs_d=d, people=people)


def _s_severe(bare_b, bare_d, people, food=0.13, other_d=0.0):
    """Severely starving (on top, x the starvation value), with other_d of other own lines on its deaths."""
    b, d = demographics_model.starvation_terms(food)
    return _SPop(bare_b, bare_d, top_b=b, top_d=d + other_d, sev_d=d, people=people)


class TestOnTopSplitScript(unittest.TestCase):
    """The Causes of Death section's split of the deaths added on top (Task 6, re-planned on #907's window):
    te_demog_on_top_split, at the walk's tail after te_demog_window_events, with the start's parts the refresh stores
    beside te_dg_sr_d (te_dg_sp_d, te_dg_ss_d).

    Each case is checked against an engine built from pops, as TestWindowEvents is. Each pop gives bare x max(0, 1 +
    read + absorbed + own). At each end the whole state's part is the engine without any pop's own lines, unfloored
    (bare x (1 + read + absorbed)), and severe starvation's part is bare x its severe term over the pops the engine
    doesn't floor. The window is the mean of the two ends x the window's months; the start runs under the terms the
    refresh left in force."""

    POP = 1_000_000.0
    CBR, CDR = 38.0, 31.0
    _engine = TestWindowEvents._engine
    _set_reads = TestWindowEvents._set_reads
    SAFE = _SPop(300e6, 260e6, people=600e3)
    LABORERS = _SPop(175e6, 170e6, people=400e3)

    @staticmethod
    def walk(pops, read_b, read_d):
        """The walk's sums for these pops (te_demog_walks, te_demog_absorbed_walk_pop); no wealth line, so its bare deaths x
        wealth (te_dg_w_edw) are 0."""
        w = dict(te_dg_w_eb0=0.0, te_dg_w_ed0=0.0, te_dg_w_ebr=0.0, te_dg_w_edr=0.0, te_dg_w_eb=0.0, te_dg_w_ed=0.0,
                 te_dg_w_eb0m=0.0, te_dg_w_ed0m=0.0, te_dg_w_sev=0.0, te_dg_w_sevd=0.0, te_dg_w_pop=0.0,
                 te_dg_w_edw=0.0, **WALK_CAUSE_DEFAULTS)
        for bare_b, bare_d, abs_b, abs_d, top_b, top_d, sev_d, people in pops:
            # a pop's own lines but severe starvation's are its workplace's here (Causes of Death, owner 2026-10-22)
            w["te_dg_w_odw"] += bare_d * (top_d - sev_d) if 1 + read_d + abs_d + top_d > 0 else 0.0
            mult_b, mult_d = max(0.0, 1 + read_b + abs_b + top_b), max(0.0, 1 + read_d + abs_d + top_d)
            w["te_dg_w_eb0"] += bare_b
            w["te_dg_w_ed0"] += bare_d
            w["te_dg_w_ebr"] += bare_b * abs_b
            w["te_dg_w_edr"] += bare_d * abs_d
            w["te_dg_w_eb"] += bare_b * mult_b
            w["te_dg_w_ed"] += bare_d * mult_d
            w["te_dg_w_eb0m"] += bare_b if mult_b > 0 else 0.0
            w["te_dg_w_ed0m"] += bare_d if mult_d > 0 else 0.0
            w["te_dg_w_pop"] += people
            if sev_d:
                w["te_dg_w_sev"] += people
                w["te_dg_w_sevd"] += bare_d * sev_d if mult_d > 0 else 0.0
        return w

    @staticmethod
    def truth(pops, read_d):
        """(the engine's deaths, the whole state's part, severe starvation's part) at one end, a month x 100,000."""
        total = sum(p[1] * max(0.0, 1 + read_d + p[3] + p[5]) for p in pops)
        whole = sum(p[1] * (1 + read_d + p[3]) for p in pops)
        sev = sum(p[1] * p[6] for p in pops if p[6] and 1 + read_d + p[3] + p[5] > 0)
        return total, whole, sev

    def window(self, start_pops, end_pops, os_start=(0.02, 0.05), os_end=(0.02, 0.05), m_prev=(-0.3, -0.25),
               months=12, fast_k=None, lines=(0.0, 0.0), full=True, refresh=True, drop_start_parts=False,
               tags_start=None, tags_end=None):
        """TestWindowEvents.window, then the split and the step's scales. refresh False: no step at the start (the
        first step after a seed: the window takes the snapshot). tags_start, tags_end: {cause: the tagged state lines'
        sum} at each end (state_death_cause_<c>_mult; owner, 2026-10-22), each a part of that end's deaths read. Returns
        the engine and the window's truth: {ed, state, sev} in people and the end's severe share of people."""
        eng = self._engine(full)

        def tags(sums):
            for c, name in P.DEATH_CAUSE_TYPES.items():
                eng.fixtures[f"modifier:{name}"] = (sums or {}).get(c, 0.0)
        mb, md = m_prev
        eng.modifiers.update({"te_demog_census_births_down" if mb < 0 else "te_demog_census_births_up": abs(mb),
                              "te_demog_census_deaths_down" if md < 0 else "te_demog_census_deaths_up": abs(md)})
        eng.vars.update(te_dg_mb=mb, te_dg_md=md, te_dg_stepped=1.0, te_dg_cbr_model=self.CBR,
                        te_dg_cdr_model=self.CDR)
        if lines != (0.0, 0.0):
            eng.modifiers.update(te_demog_line_births_down=-lines[0], te_demog_line_deaths_down=-lines[1])
            eng.vars.update(te_dg_ln_births=lines[0], te_dg_ln_deaths=lines[1])
        if fast_k is not None:
            eng.trigger_fixtures["te_demog_clock_on"] = True
            eng.fixtures["global_var:te_demog_months_per_step"] = 12.0 / fast_k
            eng.fixtures["global_var:te_demog_window_months"] = 12.0 / fast_k
        if refresh:
            tags(tags_start)
            read = self._set_reads(eng, *os_start, lines=lines)
            eng.locals.update(self.walk(start_pops, *read))
            eng.call("te_demog_rates_refresh")
            if fast_k is not None:
                eng.call("te_demog_fast_refresh_rates")
            eng.locals.clear()
        if fast_k is not None:
            eng.fixtures["global_var:te_demog_window_months"] = float(months)
        if drop_start_parts:
            for name in ("te_dg_sp_d", "te_dg_ss_d", *(f"te_dg_s{k}_{c}" for k in "ct" for c in P.DEATH_CAUSES)):
                eng.vars.pop(name, None)
        read_start = self._set_reads(eng, *os_start)
        start = self.truth(start_pops, read_start[1])
        read_end = self._set_reads(eng, *os_end)
        tags(tags_end)
        end_sums = self.walk(end_pops, *read_end)
        end = self.truth(end_pops, read_end[1])
        eng.locals.update(end_sums)
        eng.vars.update(te_dg_eb=end_sums["te_dg_w_eb"] * months / 1e5, te_dg_ed=end_sums["te_dg_w_ed"] * months / 1e5)
        eng.call("te_demog_window_events")
        eng.call("te_demog_on_top_split")
        # te_dg_lx_on 1: no estimate to place the deaths on top by cause, so one scale (TestOnTopCauseScales has them)
        eng.locals.update(te_dg_tfr=1.0, te_dg_m_inf=1.0, te_dg_m_ext=1.0, te_dg_m_chr=1.0, te_dg_m_work_f=1.0,
                          te_dg_m_work_m=1.0, te_dg_lx_on=1.0)
        eng.call("te_demog_on_top_scales")
        if refresh and "te_dg_sr_d" in eng.vars:
            ends = [(a + b) / 2 * months / 1e5 for a, b in zip(start, end)]
        else:
            ends = [x * months / 1e5 for x in end]
        share = end_sums["te_dg_w_sev"] / end_sums["te_dg_w_pop"]
        return eng, dict(ed=ends[0], state=ends[1], sev=ends[2], share=share)

    def value(self, eng, name):
        if name == "te_demog_deaths_whole_state":
            return eng.vars["te_dg_ed_state"] / max(eng.vars["te_dg_ed_target"], 1.0)
        if name == "te_demog_deaths_severe":
            return (eng.vars["te_dg_ed_state"] + eng.vars["te_dg_ed_sev"]) / max(eng.vars["te_dg_ed_state"], 1.0)
        if name == "te_demog_deaths_other":
            return eng.vars["te_dg_ed"] / max(eng.vars["te_dg_ed_state"] + eng.vars["te_dg_ed_sev"], 1.0)
        return eng.value(eng._tree(eng.values, name))

    def assert_split(self, eng, true, rel=1e-6):
        """The split's variables against the truth. Its three factors (the whole state's, severe starvation's, the other
        lines on some people: the hover's until the deaths on top counted under their causes, owner 2026-10-22; the
        harness's ontop-fit reads the variables) multiply back to 1 + dz."""
        got = {"ed": eng.vars["te_dg_ed"], "state": eng.vars["te_dg_ed_state"], "sev": eng.vars["te_dg_ed_sev"],
               "share": eng.vars["te_dg_sev_share"]}
        for k, want in true.items():
            self.assertAlmostEqual(got[k], want, delta=rel * max(abs(want), 1.0), msg=k)
        product = (self.value(eng, "te_demog_deaths_whole_state") * self.value(eng, "te_demog_deaths_severe")
                   * self.value(eng, "te_demog_deaths_other"))
        self.assertAlmostEqual(product, self.value(eng, "te_demog_deaths_on_top"), delta=1e-6, msg="the product")
        return got

    def test_a_famine_inside_the_window_is_severe_starvations(self):
        """Hannover 1897-98: mildly starving when the window began (absorbed: M nets it, so the whole state's), severely
        on the step's day (on top, so some of its people's). Half the end's severe deaths are severe starvation's."""
        eng, true = self.window([self.SAFE, _s_mild(175e6, 170e6, 400e3)], [self.SAFE, _s_severe(175e6, 170e6, 400e3)])
        got = self.assert_split(eng, true)
        severe_d = demographics_model.starvation_terms(0.13)[1]
        self.assertAlmostEqual(got["sev"], 170e6 * severe_d / 2 * 12 / 1e5, delta=1e-3)
        self.assertAlmostEqual(got["share"], 0.4)
        self.assertGreater(self.value(eng, "te_demog_deaths_severe"), 1.05)
        self.assertAlmostEqual(self.value(eng, "te_demog_deaths_other"), 1.0, places=6)

    def test_a_famine_ending_in_the_window(self):
        eng, true = self.window([self.SAFE, _s_severe(175e6, 170e6, 400e3)],
                                [self.SAFE, _s_mild(175e6, 170e6, 400e3, food=0.37)])
        got = self.assert_split(eng, true)
        self.assertGreater(got["sev"], 0.0, "the start's famine still counts")
        self.assertEqual(got["share"], 0.0, "nobody severely starving at the count")

    def test_a_state_level_change_stays_with_the_whole_state(self):
        """Devastation from nothing to +0.3 inside the window: the whole state's, both factors on some of its people
        x1.00."""
        steady = [self.SAFE, self.LABORERS]
        eng, true = self.window(steady, steady, os_start=(0.0, 0.0), os_end=(-0.1, 0.3))
        self.assert_split(eng, true)
        self.assertAlmostEqual(self.value(eng, "te_demog_deaths_severe"), 1.0, places=6)
        self.assertAlmostEqual(self.value(eng, "te_demog_deaths_other"), 1.0, places=6)
        self.assertEqual(eng.vars["te_dg_ed_state"], eng.vars["te_dg_ed"])

    def test_other_lines_on_some_people(self):
        """A dangerous workplace (+0.2 on the laborers' deaths) at both ends: other effects above 1, severe x1.00."""
        pops = [self.SAFE, _SPop(175e6, 170e6, top_d=0.2, people=400e3)]
        eng, true = self.window(pops, pops)
        self.assert_split(eng, true)
        # the workplace line over the whole state's deaths: (whole + bare x 0.2) / whole, from the pops
        own = 170e6 * 0.2 * 12 / 1e5
        self.assertAlmostEqual(self.value(eng, "te_demog_deaths_other"), (true["state"] + own) / true["state"],
                               delta=1e-6)
        self.assertGreater(self.value(eng, "te_demog_deaths_other"), 1.05)
        self.assertAlmostEqual(self.value(eng, "te_demog_deaths_severe"), 1.0, places=6)

    def test_the_whole_state_part_is_the_window_without_the_pops_own_lines(self):
        """Review Focus 3: the same state with every pop's own lines taken away at both ends books, as its whole
        window, what the first books as its whole state's part."""
        start = [self.SAFE, _s_mild(175e6, 170e6, 400e3)]
        end = [_SPop(300e6, 260e6, top_d=0.15, people=600e3), _s_severe(175e6, 170e6, 400e3, other_d=0.1)]
        eng, _true = self.window(start, end)
        bare = [p[:4] + (0.0, 0.0, 0.0, p[7]) for p in end]
        plain, _ = self.window([p[:4] + (0.0, 0.0, 0.0, p[7]) for p in start], [_SPop(*p) for p in bare])
        self.assertAlmostEqual(eng.vars["te_dg_ed_state"], plain.vars["te_dg_ed"], delta=1e-3)

    def test_a_floored_pop_under_a_changing_m(self):
        """A pop whose own lines take its deaths to 0 (-3 on top), while the refresh moves M a long way (+0.6 to the
        fitted term): the change in M doesn't reach it, so its own lines absorb it at the window's start. Reading the
        change on every pop's bare curves (te_dg_w_ed0 for te_dg_w_ed0m) books the whole state's part wrong here and
        nowhere else."""
        pops = [self.SAFE, _SPop(175e6, 170e6, top_d=-3.0, people=400e3)]
        eng, true = self.window(pops, pops, m_prev=(0.4, 0.6))
        self.assert_split(eng, true)
        self.assertLess(self.value(eng, "te_demog_deaths_other"), 0.9)

    def test_fast_mode_moves_the_start_part(self):
        """K = 4: the clock's term moves the start's rate on the unfloored pops; the start's own lines move by it on
        the floored ones."""
        start = [self.SAFE, _SPop(175e6, 170e6, top_d=-3.0, people=400e3)]
        end = [self.SAFE, _SPop(175e6, 170e6, top_d=-3.0, people=400e3)]
        eng, true = self.window(start, end, fast_k=4, months=3)
        self.assertIn("te_demog_fast_deaths", eng.modifiers)
        self.assert_split(eng, true)

    # ---- by cause (owner, 2026-10-22): te_demog_on_top_causes, te_dg_ot_<c> --------------------------------------------

    def causes(self, eng):
        return {c: eng.vars[f"te_dg_ot_{c}"] for c in P.DEATH_CAUSES}

    def test_a_famine_counts_under_infection_and_hunger(self):
        """Severe starvation's part of the window is infection and hunger's, and nothing else is on top by cause."""
        eng, true = self.window([self.SAFE, _s_mild(175e6, 170e6, 400e3)], [self.SAFE, _s_severe(175e6, 170e6, 400e3)])
        got = self.causes(eng)
        self.assertAlmostEqual(got["inf"], true["sev"], delta=1e-3)
        for c in ("chr", "ext", "work", "war"):
            self.assertAlmostEqual(got[c], 0.0, delta=1e-3, msg=c)

    def test_a_dangerous_workplace_counts_under_work(self):
        pops = [self.SAFE, _SPop(175e6, 170e6, top_d=0.2, people=400e3)]
        eng, _true = self.window(pops, pops)
        got = self.causes(eng)
        self.assertAlmostEqual(got["work"], 170e6 * 0.2 * 12 / 1e5, delta=1e-3)
        self.assertAlmostEqual(got["inf"], 0.0, delta=1e-3)

    def test_a_tagged_line_through_the_window_acts_on_the_census_rate(self):
        """Pollution's +5% on the whole state at both ends, tagged chronic: M took (1 - target / bare) of it off, so its
        deaths are 5% of the census's own, the target's."""
        steady = [self.SAFE, self.LABORERS]
        eng, _true = self.window(steady, steady, os_start=(0.0, 0.05), os_end=(0.0, 0.05), tags_start={"chr": 0.05},
                                 tags_end={"chr": 0.05})
        got = self.causes(eng)
        self.assertAlmostEqual(got["chr"], 0.05 * eng.vars["te_dg_ed_target"], delta=1e-4 * eng.vars["te_dg_ed_target"])
        self.assertAlmostEqual(eng.vars["te_dg_st_chr"], 0.05, places=6)
        for c in ("inf", "ext", "work", "war"):
            self.assertAlmostEqual(got[c], 0.0, delta=1e-3, msg=c)

    def test_devastation_arriving_inside_the_window_kills_at_the_bare_curve(self):
        """Devastation from nothing to +0.3 after the refresh, tagged war: M took none of it off, so at the window's end
        it adds 0.3 of the bare deaths, half of that over the window."""
        steady = [self.SAFE, self.LABORERS]
        eng, _true = self.window(steady, steady, os_start=(0.0, 0.0), os_end=(-0.1, 0.3), tags_end={"war": 0.3})
        got = self.causes(eng)
        self.assertAlmostEqual(got["war"], 0.5 * 0.3 * (260e6 + 170e6) * 12 / 1e5, delta=1e-3)
        self.assertGreater(got["war"], 0.3 * eng.vars["te_dg_ed_target"] / 2, "more than at the census's rate")

    def test_no_split_by_cause_without_its_start_parts(self):
        """A save from before the split by cause: the window took a start with no parts by cause, so none (the step then
        spreads all of dz, as before)."""
        pops = [self.SAFE, _SPop(175e6, 170e6, top_d=0.2, people=400e3)]
        eng, _true = self.window(pops, pops, drop_start_parts=True)
        for c in P.DEATH_CAUSES:
            self.assertNotIn(f"te_dg_ot_{c}", eng.vars)
        eng, _true = self.window([], pops, refresh=False)
        self.assertNotIn("te_dg_ot_work", eng.vars, "nor on a snapshot")

    def test_the_refresh_stores_the_start_parts_by_cause(self):
        pops = [self.SAFE, self.LABORERS]
        eng, _true = self.window(pops, pops, tags_start={"inf": 0.02})
        self.assertAlmostEqual(eng.vars["te_dg_st_inf"], 0.02, places=6)
        for c in P.DEATH_CAUSES:
            self.assertIn(f"te_dg_sc_{c}", eng.vars)

    def test_no_start_rate_splits_the_snapshot(self):
        """The first step after a seed (or a new state, an old save): the window is the snapshot, and so is the split."""
        eng, true = self.window([], [self.SAFE, _s_severe(175e6, 170e6, 400e3)], refresh=False)
        self.assertNotIn("te_dg_sr_d", eng.vars)
        self.assert_split(eng, true)

    def test_the_walks_own_severe_sum_feeds_the_split(self):
        """The review of Task 6: the cases above sum severe starvation in Python; here the end's two severe sums come
        from the generated per-pop effect (te_demog_absorbed_walk_pop), pop by pop, so a floored severe pop's deaths
        counted there would show in the split. Food security at each step's middle, where the ladder is exact."""
        floored = _s_severe(175e6, 170e6, 300e3, food=0.075, other_d=-3.0)
        starving = _s_severe(100e6, 90e6, 100e3, food=0.125)
        end = [self.SAFE, floored, starving]
        eng, true = self.window([self.SAFE, self.LABORERS], end)
        read_d = eng.fixtures["modifier:state_mortality_mult"]
        eng.locals.update(te_dg_w_rep=1.0, te_dg_w_ebr=0.0, te_dg_w_edr=0.0, te_dg_w_eb0m=0.0, te_dg_w_ed0m=0.0,
                          te_dg_w_sev=0.0, te_dg_w_sevd=0.0, te_dg_w_edw=0.0, te_dg_w_wtop=0.0)
        for pop, food in ((self.SAFE, 1.0), (floored, 0.075), (starving, 0.125)):
            eng.fixtures.update(food_security=food, total_size=pop[7], literacy_rate=0.0)
            eng.trigger_fixtures.update(is_in_severe_starvation=food < 0.2, is_in_mild_starvation=0.2 <= food < 0.4)
            eng.locals.update(te_dg_p_eb=pop[0], te_dg_p_ed=pop[1], te_dg_p_mb=1.0,
                              te_dg_p_md=max(0.0, 1 + read_d + pop[3] + pop[5]))
            eng.call("te_demog_absorbed_walk_pop")
        self.assertEqual(eng.locals["te_dg_w_sev"], 400e3, "the floored pop's people count")
        self.assertAlmostEqual(eng.locals["te_dg_w_sevd"], 90e6 * 0.6875, delta=1e-3, msg="its deaths don't")
        python = self.walk(end, 0.0, read_d)
        self.assertAlmostEqual(eng.locals["te_dg_w_sevd"], python["te_dg_w_sevd"], delta=1e-3)
        eng.call("te_demog_on_top_split")
        self.assertAlmostEqual(eng.vars["te_dg_ed_sev"], true["sev"], delta=1e-6 * true["sev"])
        self.assertAlmostEqual(eng.vars["te_dg_sev_share"], true["share"])

    def test_a_start_from_before_this_build_waits(self):
        """A save from #907 but before this build has the start's rate and none of its parts: the window can't be
        split as it was booked, so the split's variables go and the row waits for the next count."""
        eng = self._engine()
        eng.vars.update(te_dg_ed_state=1.0, te_dg_ed_sev=1.0, te_dg_sev_share=0.1)
        eng, _true = self.window([self.SAFE, self.LABORERS], [self.SAFE, _s_severe(175e6, 170e6, 400e3)],
                                 drop_start_parts=True)
        self.assertIn("te_dg_sr_d", eng.vars)
        for name in ("te_dg_ed_state", "te_dg_ed_sev", "te_dg_sev_share"):
            self.assertNotIn(name, eng.vars, name)

    def test_outside_full_the_split_goes(self):
        eng = self._engine(full=False)
        eng.vars.update(te_dg_ed_state=1.0, te_dg_ed_sev=1.0, te_dg_sev_share=0.1)
        eng.call("te_demog_on_top_split")
        for name in ("te_dg_ed_state", "te_dg_ed_sev", "te_dg_sev_share"):
            self.assertNotIn(name, eng.vars, name)

    def test_far_above_the_census_the_product_is_the_row(self):
        """Deaths over five times the census's: dz has no ceiling since 2026-10-20 (it stopped at +4), so the row,
        1 + dz, and the split's product are both the window over the target."""
        pops = [self.SAFE, _SPop(175e6, 170e6, top_d=12.0, people=400e3)]
        eng, true = self.window(pops, pops)
        got = {k: eng.vars[v] for k, v in (("state", "te_dg_ed_state"), ("sev", "te_dg_ed_sev"))}
        self.assertAlmostEqual(got["state"], true["state"], delta=1e-6 * true["state"])
        product = (self.value(eng, "te_demog_deaths_whole_state") * self.value(eng, "te_demog_deaths_severe")
                   * self.value(eng, "te_demog_deaths_other"))
        self.assertAlmostEqual(product, eng.vars["te_dg_ed"] / eng.vars["te_dg_ed_target"], places=6)
        self.assertGreater(product, 5.0)
        self.assertAlmostEqual(self.value(eng, "te_demog_deaths_on_top"), product, places=4)

    def test_the_start_parts_go_with_the_start_rate(self):
        """Wherever te_dg_sr_d goes, the start's parts go too: the refresh outside Full (te_demog_rates_clear), a
        refresh that stores no start (a seed's), te_demog_seed, and fast mode's clear."""
        # and each cause's (owner, 2026-10-22)
        parts = dict(te_dg_sr_b=1.0, te_dg_sr_d=1.0, te_dg_sp_d=0.1, te_dg_ss_d=0.05,
                     **{f"te_dg_s{k}_{c}": 0.01 for k in "ct" for c in P.DEATH_CAUSES})
        cases = {}
        eng = TestRatesScript._eng(TestRatesScript(), full=False)
        eng.locals.update(te_dg_w_sev=0.0, te_dg_w_sevd=0.0)
        eng.vars.update(parts)
        eng.call("te_demog_rates_refresh")
        cases["not Full"] = eng
        eng = TestRatesScript._eng(TestRatesScript(), stepped=0.0)
        eng.locals.update(te_dg_w_sev=0.0, te_dg_w_sevd=0.0)
        eng.vars.update(parts)
        eng.call("te_demog_rates_refresh")
        cases["a seed's refresh"] = eng
        eng = _engine_for(TestCohortScript.INP, 1836, 250000.0)
        eng.vars.update(parts)
        eng.call("te_demog_seed")
        cases["te_demog_seed"] = eng
        eng = self._engine()
        eng.modifiers["te_demog_fast_deaths"] = 0.5
        eng.vars.update(parts)
        eng.call("te_demog_fast_clear_rates")
        cases["fast mode's clear"] = eng
        for label, eng in cases.items():
            for name in parts:
                with self.subTest(label, name=name):
                    self.assertNotIn(name, eng.vars)


class TestOnTopClampSide(unittest.TestCase):
    """Whether the floor bit the census's deaths term (te_dg_rate_clamp_d), and its copy for the window dz measured
    (te_dg_ed_clamp_d): the hover names it for the window it describes (Task 6; Review Focus 3). Since 2026-10-20 there
    is no cap, so the flag is 0 or 1."""

    def _eng(self, **kw):
        eng = TestRatesScript._eng(TestRatesScript(), **kw)
        eng.locals.update(te_dg_w_sev=0.0, te_dg_w_sevd=0.0)
        return eng

    def test_the_deaths_clamp_records_its_side(self):
        """1 at the floor, 0 when deaths weren't clamped (a target far above the bare curve too: no cap); births clamped
        alone (the moved lines' on-top family past the rest of the read) leave 0."""
        hunger = TestRatesScript.EDR_HUNGER
        for kw, side in ((dict(cdr=400.0), 0), (dict(cdr=0.5, read_d=-0.5, edr=hunger), 1),
                         (dict(cbr=2.0, ontop={"state_demog_ontop_birth_rate_mult": -2.0}), 0), ({}, 0)):
            eng = self._eng(**kw)
            eng.call("te_demog_rates_refresh")
            with self.subTest(kw=kw):
                self.assertEqual(eng.vars["te_dg_rate_clamp_d"], side)
                if kw.get("cbr"):
                    self.assertEqual(eng.vars["te_dg_rate_clamped"], 1, "births did clamp")

    def test_the_measured_window_keeps_its_clamp(self):
        """dz measures the window that ran on the last refresh's M: the step copies that refresh's flag before this
        step's refresh overwrites it; with none (the first Full step after Display only or a seed) the copy goes."""
        eng = _Engine({}, triggers={"te_demog_effects_run": True})
        eng.vars["te_dg_rate_clamp_d"] = 1.0
        eng.call("te_demog_on_top_clamp_copy")
        self.assertEqual(eng.vars["te_dg_ed_clamp_d"], 1.0)
        del eng.vars["te_dg_rate_clamp_d"]
        eng.call("te_demog_on_top_clamp_copy")
        self.assertNotIn("te_dg_ed_clamp_d", eng.vars)
        eng.vars["te_dg_rate_clamp_d"] = 1.0
        eng.trigger_fixtures["te_demog_effects_run"] = False
        eng.vars["te_dg_ed_clamp_d"] = 1.0
        eng.call("te_demog_on_top_clamp_copy")
        self.assertNotIn("te_dg_ed_clamp_d", eng.vars, "outside Full")
        scales = [k for k, _, _ in _parse_script(_raw_blocks([RATE_EFFECTS])["te_demog_on_top_scales"])]
        self.assertEqual(scales[0], "te_demog_on_top_clamp_copy")

    def test_rates_clear_takes_the_clamp_and_the_start_parts(self):
        eng = _Engine({}, triggers={"te_demog_effects_run": False})
        names = ("te_dg_rate_clamp_d", "te_dg_ed_clamp_d", "te_dg_sp_d", "te_dg_ss_d")
        eng.vars.update(dict.fromkeys(names, 1.0))
        eng.call("te_demog_rates_clear")
        for name in names:
            self.assertNotIn(name, eng.vars, name)


class _OwnerEngine(_Engine):
    """_Engine with an owner's laws, techs and institution levels and one pop's type: enough to run the generated
    absorbed terms. owner = { } and state = { } read the same facts (one state, one owner, one pop); the state's
    incorporation and the pop's starvation are trigger fixtures (is_incorporated, is_in_*_starvation)."""

    def __init__(self, fixtures, laws=(), techs=(), levels=None, pop_type=None, workplace=None, **kwargs):
        super().__init__(fixtures, **kwargs)
        self.laws, self.techs, self.levels, self.pop_type = set(laws), set(techs), dict(levels or {}), pop_type
        self.workplace = workplace   # the pop's workplace's building group; None: not employed (calibration step 3)

    def _test(self, key, op, arg):
        if key in ("owner", "state"):
            return self.holds(arg)
        if key == "is_employed":
            return (self.workplace is not None) == (arg == "yes")
        if key == "exists" and arg == "workplace":
            return self.workplace is not None
        if key == "workplace":
            return self.holds(arg)
        if key == "is_building_group":
            return arg == self.workplace
        if key == "has_law":
            assert arg.startswith("law_type:"), arg
            return arg[9:] in self.laws
        if key == "has_technology_researched":
            return arg in self.techs
        if key == "institution_investment_level":
            level = self.levels.get(_find(arg, "institution"), 0)
            _, vop, n = next(item for item in arg if item[0] == "value")
            return {">=": level >= float(n), ">": level > float(n), "=": level == float(n)}[vop]
        if key == "is_pop_type":
            return arg == self.pop_type
        return super()._test(key, op, arg)


class TestAbsorbedScript(unittest.TestCase):
    """The walk's replaced sums (te_dg_w_ebr / te_dg_w_edr), which M nets out under Full: each pop's bare curves x the
    terms the engine still applies per pop and the census models (literacy's -0.1, mild starvation's). Since 2026-10-11
    (the engine-lines plan) the laws', techs' and institutions' lines are script-only and need no netting."""

    P_EB, P_ED = 500.0, 400.0

    @classmethod
    def setUpClass(cls):
        cls.absorbed = DM.absorbed_carriers()

    def _run(self, laws=(), techs=(), levels=None, incorporated=True, pop_type="clerks", food=1.0, literacy=0.0,
             full=True, impact=0.0):
        eng = _OwnerEngine({"literacy_rate": literacy, "food_security": food, "total_size": 1000.0,
                            "modifier:state_institution_impact_add": impact}, laws=laws, techs=techs, levels=levels,
                           pop_type=pop_type,
                           triggers={"is_incorporated": incorporated, "is_in_severe_starvation": food < 0.2,
                                     "is_in_mild_starvation": 0.2 <= food < 0.4, "te_demog_effects_run": full})
        eng.call("te_demog_absorbed_walk_init")
        eng.locals.update(te_dg_p_eb=self.P_EB, te_dg_p_ed=self.P_ED, te_dg_p_mb=1.0, te_dg_p_md=1.0)
        eng.call("te_demog_absorbed_walk_pop")
        return eng.locals["te_dg_w_ebr"] / self.P_EB, eng.locals["te_dg_w_edr"] / self.P_ED

    def test_the_walk_sums_the_pops_own_lines_by_cause(self):
        """Causes of Death (owner, 2026-10-22): where the engine doesn't floor a pop, the walk sums its own lines by the
        cause they count under: non-homeland mortality (infection and hunger), its class's line (war for soldiers and
        officers, accidents and violence for the rest) and the rest of its multiplier less the state's read, what the
        census absorbs, the wealth line and severe starvation's term: its workplace's (work)."""
        def run(pop_type, md, homeland=True, cls=0.0, hom=0.0, read=0.0, food=1.0):
            eng = _OwnerEngine({"food_security": food, "total_size": 1000.0, "literacy_rate": 0.0,
                                "modifier:state_mortality_mult": read,
                                "modifier:state_non_homeland_mortality_mult": hom,
                                f"modifier:state_{pop_type}_mortality_mult": cls}, pop_type=pop_type,
                               triggers={"is_in_severe_starvation": food < 0.2, "is_in_mild_starvation": 0.2 <= food < 0.4,
                                         "te_demog_effects_run": True, "is_homeland_of_country_cultures": homeland})
            eng.call("te_demog_absorbed_walk_init")
            eng.locals.update(te_dg_p_eb=self.P_EB, te_dg_p_ed=self.P_ED, te_dg_p_mb=1.0, te_dg_p_md=md)
            eng.call("te_demog_absorbed_walk_pop")
            return {k: eng.locals[f"te_dg_w_od{k}"] / self.P_ED for k in "hxqw"}
        # a soldier abroad: the homeland line, his class's and his workplace's, over a state read of +0.05
        got = run("soldiers", md=1 + 0.05 + 0.3 + 0.15 + 0.1, homeland=False, cls=0.15, hom=0.3, read=0.05)
        for k, want in {"h": 0.3, "q": 0.15, "x": 0.0, "w": 0.1}.items():
            self.assertAlmostEqual(got[k], want, places=9, msg=k)
        got = run("laborers", md=1.2, cls=0.2)
        self.assertAlmostEqual(got["x"], 0.2, places=9)
        self.assertAlmostEqual(got["w"], 0.0, places=9)
        self.assertEqual(run("soldiers", md=1.3, homeland=True, hom=0.3, cls=0.0)["h"], 0.0, "at home, no homeland line")
        self.assertEqual(run("laborers", md=0.0, cls=-3.0), {"h": 0.0, "x": 0.0, "q": 0.0, "w": 0.0}, "floored: none")
        severe = demographics_model.starvation_terms(0.125)[1]
        self.assertAlmostEqual(run("clerks", md=1 + severe, food=0.125)["w"], 0.0, places=9, msg="severe isn't work's")

    def _want(self, laws=(), techs=(), levels=None, incorporated=True, pop_type="clerks", carriers=None):
        carriers = self.absorbed if carriers is None else carriers
        t = DM.totals(carriers, techs=techs, laws=laws, institutions=levels or {}, incorporated=incorporated,
                      types={c.type for c in self.absorbed})
        return (t.get("state_birth_rate_mult", 0.0),
                t.get("state_mortality_mult", 0.0) + t.get(f"state_{pop_type}_mortality_mult", 0.0))

    def _held(self, c, level=3):
        """What holding carrier c takes: its law or tech, and its institution at `level`."""
        laws = {c.key} if c.kind in ("law", "law_institution") else set()
        techs = {c.key} if c.kind == "technology" else set()
        levels = {c.institution: level} if c.institution else {}
        return laws, techs, levels

    def test_a_carrier_not_held_takes_nothing(self):
        self.assertEqual(self._run(), (0.0, 0.0))

    def test_outside_full_the_walk_sums_nothing(self):
        """The pop walk runs under every setting (inheritance owns it), but only Full's refresh reads the replaced
        sums: outside Full the walk skips them, so the default setting pays nothing per pop."""
        laws = {"law_child_labor_allowed", "law_women_in_the_fields"}
        self.assertNotEqual(self._run(laws, pop_type="laborers", food=0.3, literacy=0.5), (0.0, 0.0))
        self.assertEqual(self._run(laws, pop_type="laborers", food=0.3, literacy=0.5, full=False), (0.0, 0.0))
        pop = _block(_text(GENERATED_EFFECTS), "te_demog_absorbed_walk_pop")
        self.assertTrue(pop.lstrip().startswith("if = {\n\t\tlimit = { local_var:te_dg_w_rep > 0 }"), pop[:80])

    def test_the_walk_sums_the_bare_curves_the_census_term_reaches(self):
        """The trapezoid's start rate (te_demog_rates_refresh; the review of #907) moves by the change in M on the bare
        curves of the pops whose multiplier the engine doesn't floor at 0 (te_dg_w_eb0m, te_dg_w_ed0m): severe
        starvation's births (-0.9 x the starvation value) can floor a pop's births when M is low, and a change in M
        doesn't reach it. Full only."""
        for full, mult_b, mult_d, want in ((True, 0.4, 1.2, (500.0, 400.0)), (True, 0.0, 1.2, (0.0, 400.0)),
                                           (True, 0.0, 0.0, (0.0, 0.0)), (False, 0.4, 1.2, (0.0, 0.0))):
            with self.subTest(full=full, mult_b=mult_b, mult_d=mult_d):
                eng = _OwnerEngine({"literacy_rate": 0.0, "food_security": 1.0},
                                   triggers={"te_demog_effects_run": full, "is_in_severe_starvation": False,
                                             "is_in_mild_starvation": False})
                eng.call("te_demog_absorbed_walk_init")
                eng.locals.update(te_dg_p_eb=self.P_EB, te_dg_p_ed=self.P_ED, te_dg_p_mb=mult_b, te_dg_p_md=mult_d)
                eng.call("te_demog_absorbed_walk_pop")
                self.assertEqual((eng.locals["te_dg_w_eb0m"], eng.locals["te_dg_w_ed0m"]), want)
        body = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_walks"))
        loop = body[body.index("every_scope_pop = {"):]
        self.assertLess(loop.index("set_local_variable = { name = te_dg_p_mb value = te_demog_pop_birth_mult }"),
                        loop.index("te_demog_absorbed_walk_pop = yes"))
        self.assertLess(loop.index("set_local_variable = { name = te_dg_p_md value = te_demog_pop_death_mult }"),
                        loop.index("te_demog_absorbed_walk_pop = yes"))

    def test_the_walk_sums_severe_starvation(self):
        """The Causes of Death section's split (Task 6): a severe pop adds its people, and its bare deaths x the severe
        term te_demog_pop_death_mult gives it, read in the same food-security steps, unless the engine floors it at 0
        (people only). A mild pop adds nothing; outside Full nothing is summed."""
        def run(food, md=1.0, full=True, people=1000.0):
            eng = _OwnerEngine({"literacy_rate": 0.0, "food_security": food, "total_size": people},
                               pop_type="laborers",
                               triggers={"te_demog_effects_run": full, "is_in_severe_starvation": food < 0.2,
                                         "is_in_mild_starvation": 0.2 <= food < 0.4})
            eng.call("te_demog_absorbed_walk_init")
            eng.locals.update(te_dg_p_eb=self.P_EB, te_dg_p_ed=self.P_ED, te_dg_p_mb=1.0, te_dg_p_md=md)
            eng.call("te_demog_absorbed_walk_pop")
            return eng.locals["te_dg_w_sev"], eng.locals["te_dg_w_sevd"]

        for food in (0.199, 0.15, 0.12, 0.07, 0.0):
            with self.subTest(food=food):
                term = TestPopMultiplierScript()._term("te_demog_pop_death_mult", food)
                self.assertEqual(run(food), (1000.0, self.P_ED * term))
                self.assertAlmostEqual(term, P.STARVATION_SEVERE["deaths"] * demographics_model.starvation_value(food),
                                       delta=P.STARVATION_BUCKET * 2.5 / 2 + 1e-9)
        self.assertEqual(run(0.12, md=0.0), (1000.0, 0.0), "floored: its people, not its deaths")
        self.assertEqual(run(0.3), (0.0, 0.0), "mild starvation")
        self.assertEqual(run(1.0), (0.0, 0.0))
        self.assertEqual(run(0.12, full=False), (0.0, 0.0), "outside Full")

    def test_the_landowners_famine_reserves_are_absorbed_per_farm_pop(self):
        """Calibration step 3, call 1 (the spec's §2.1): a pop employed in an agriculture building (the group or a
        descendant, as the walk reads the key) absorbs its owner's read of the agriculture mortality key, the trait at
        the size its power gives it (a powerful group's -0.1 reads -0.2); a pop elsewhere, or with no workplace,
        absorbs none of it; outside Full nothing is summed. The walk's own read of the key at the farm is the
        self-check's other side."""
        def run(workplace, full=True, owner=-0.2, farm=-0.2):
            eng = _OwnerEngine({"literacy_rate": 0.0, "food_security": 1.0, "total_size": 1000.0,
                                f"owner.modifier:{key}": owner, f"workplace.modifier:{key}": farm},
                               pop_type="peasants", workplace=workplace,
                               triggers={"is_in_severe_starvation": False, "is_in_mild_starvation": False,
                                         "te_demog_effects_run": full})
            eng.call("te_demog_absorbed_walk_init")
            eng.locals.update(te_dg_p_eb=self.P_EB, te_dg_p_ed=self.P_ED, te_dg_p_mb=1.0, te_dg_p_md=1.0)
            eng.call("te_demog_absorbed_walk_pop")
            return eng.locals["te_dg_w_edr"] / self.P_ED, eng.value("te_demog_pop_country_line_walk_read")

        key = "building_group_bg_agriculture_mortality_mult"
        self.assertEqual(P.COUNTRY_ABSORBED_GROUPS, ("bg_agriculture",))
        for group in ("bg_subsistence_agriculture", "bg_agriculture", "bg_staple_crops"):
            with self.subTest(group=group):
                self.assertAlmostEqual(run(group)[0], -0.2 * P.COUNTRY_ABSORBED_SCALE)
                self.assertAlmostEqual(run(group, farm=-0.3)[1], -0.3, msg="the walk's read is the workplace's")
        self.assertEqual(run("bg_mining"), (0.0, 0.0))
        self.assertEqual(run(None), (0.0, 0.0))
        self.assertEqual(run("bg_subsistence_agriculture", full=False)[0], 0.0)

    def test_literacy_and_mild_starvation_are_absorbed_per_pop(self):
        """Mild starvation (starvation_penalty x (0.4 - food security) x 2.5, read in 0.05 steps) is absorbed;
        severe starvation stays on top (owner amendment B)."""
        b, d = self._run(food=1.0, literacy=0.6)
        self.assertAlmostEqual(b, P.LITERACY_BIRTH_PENALTY * 0.6)
        self.assertEqual(d, 0.0)
        for food, scale in ((0.37, 0.0625), (0.32, 0.1875), (0.27, 0.3125), (0.21, 0.4375)):
            b, d = self._run(food=food)
            self.assertAlmostEqual(b, P.STARVATION_MILD["births"] * scale, msg=food)
            self.assertAlmostEqual(d, P.STARVATION_MILD["deaths"] * scale, msg=food)
            ref_b, ref_d = demographics_model.starvation_terms(food)
            self.assertAlmostEqual(b, ref_b, delta=0.7 * 0.0625 * 1.01, msg=food)
        self.assertEqual(self._run(food=0.1), (0.0, 0.0))

    def test_the_walk_nets_only_the_per_pop_engine_terms(self):
        """Owner, 2026-10-11 (the engine-lines plan): the laws', techs' and institutions' lines are script-only, so
        under Full the engine no longer applies them and the walk has nothing of theirs to net. It nets what the engine
        still applies per pop: literacy's -0.1 and mild starvation's terms, at that pop's bare curves."""
        laws = {"law_child_labor_allowed", "law_women_in_the_fields", "law_charitable_health_system"}
        b, d = self._run(laws, levels={"institution_health_system": 3}, pop_type="laborers", food=0.32, literacy=0.5)
        self.assertAlmostEqual(b, P.LITERACY_BIRTH_PENALTY * 0.5 + P.STARVATION_MILD["births"] * 0.1875)
        self.assertAlmostEqual(d, P.STARVATION_MILD["deaths"] * 0.1875)
        eng = _OwnerEngine({"literacy_rate": 0.0, "food_security": 1.0}, triggers={"te_demog_effects_run": True})
        eng.call("te_demog_absorbed_walk_init")
        for gone in ("te_dg_w_sab", "te_dg_w_sad", "te_dg_w_ac_laborers"):
            self.assertNotIn(gone, eng.locals)

class TestPopMultiplierScript(unittest.TestCase):
    """te_demog_pop_birth_mult / _death_mult, the walk's per-pop engine multipliers, run by the interpreter: their
    starvation terms against the model's (demographics_model.starvation_terms, exact). The famine probe (2026-10-11):
    the engine applies both penalties x the pop's starvation value, clamp((0.4 - food security) x 2.5, 0, 1); the
    script reads it in 0.05 steps of food security, at each step's middle."""

    # (lowest food security of the step, the starvation value at its middle), top step first: the probe's table
    SEVERE_STEPS = ((0.15, 0.5625), (0.1, 0.6875), (0.05, 0.8125), (None, 0.9375))
    MILD_STEPS = ((0.35, 0.0625), (0.3, 0.1875), (0.25, 0.3125), (None, 0.4375))

    def _term(self, name, food, read=0.0, literacy=0.0):
        """The multiplier less 1, the state read and literacy's term: the starvation term, floored as the engine's."""
        text = _block(_text(GENERATED_VALUES), name)
        reads = dict.fromkeys(re.findall(r"(?:state|workplace)\.modifier:\w+", text), 0.0)
        field = "state_birth_rate_mult" if name == "te_demog_pop_birth_mult" else "state_mortality_mult"
        reads[f"state.modifier:{field}"] = read
        lo, hi = P.FOOD_SECURITY_SEVERE_STARVATION_THRESHOLD, P.FOOD_SECURITY_STARVATION_THRESHOLD
        eng = _OwnerEngine({"literacy_rate": literacy, "food_security": food, "wealth": 20.0, **reads}, pop_type="laborers",
                           triggers={"is_in_severe_starvation": food < lo, "is_in_mild_starvation": lo <= food < hi,
                                     "is_employed": False, "is_homeland_of_country_cultures": True})
        lit = P.LITERACY_BIRTH_PENALTY * literacy if field == "state_birth_rate_mult" else 0.0
        return eng.value(eng._tree(eng.values, name)) - 1 - read - lit

    @staticmethod
    def _step(food, steps):
        return next(s for lower, s in steps if lower is None or food >= lower)

    def test_severe_starvation_is_scaled_not_flat(self):
        for food in (0.199, 0.15, 0.149, 0.12, 0.1, 0.07, 0.05, 0.03, 0.0):
            with self.subTest(food=food):
                scale = self._step(food, self.SEVERE_STEPS)
                b = self._term("te_demog_pop_birth_mult", food)
                d = self._term("te_demog_pop_death_mult", food)
                self.assertAlmostEqual(b, P.STARVATION_SEVERE["births"] * scale, places=6)
                self.assertAlmostEqual(d, P.STARVATION_SEVERE["deaths"] * scale, places=6)
                ref_b, ref_d = demographics_model.starvation_terms(food)
                self.assertAlmostEqual(b, ref_b, delta=0.9 * P.STARVATION_BUCKET * 2.5 / 2 + 1e-9)
                self.assertAlmostEqual(d, ref_d, delta=1.0 * P.STARVATION_BUCKET * 2.5 / 2 + 1e-9)
                self.assertLessEqual(scale, P.STARVATION_VALUE_MAX)

    def test_mild_starvation_is_unchanged(self):
        for food in (0.37, 0.32, 0.27, 0.21, 0.2):
            with self.subTest(food=food):
                scale = self._step(food, self.MILD_STEPS)
                self.assertAlmostEqual(self._term("te_demog_pop_birth_mult", food),
                                       P.STARVATION_MILD["births"] * scale, places=6)
                self.assertAlmostEqual(self._term("te_demog_pop_death_mult", food),
                                       P.STARVATION_MILD["deaths"] * scale, places=6)
        self.assertEqual(self._term("te_demog_pop_death_mult", 0.6), 0.0)

    def test_a_severe_pops_births_floor_only_when_the_rest_runs_low(self):
        """Germany's famine (the probe): births read about -0.28 and literacy 0.5, so a severe pop at food security
        0.10 or more keeps a birth multiplier above 0 (1 - 0.28 - 0.05 - 0.61875 at worst: 97% of Germany's severe
        people); one below 0.10 is floored. The flat -0.9 floored them all, which kept them out of te_dg_w_eb0m."""
        for food, term in ((0.17, -0.50625), (0.12, -0.61875)):
            self.assertAlmostEqual(self._term("te_demog_pop_birth_mult", food, read=-0.28, literacy=0.5), term, places=6)
        for food in (0.07, 0.02):
            b = self._term("te_demog_pop_birth_mult", food, read=-0.28, literacy=0.5)
            self.assertAlmostEqual(b, -(1 - 0.28 - 0.05), places=6)   # floored: the multiplier is 0


class TestNaturalFertilityScript(unittest.TestCase):
    """te_demog_tfr with the natural-fertility read, against demographics_model.fertility."""

    def test_script_matches_the_model(self):
        for natural in (-5.0, -0.15, 0.0, 0.1):
            inp = demographics_model.Inputs(sol=9.0, literacy=0.3, urban_share=0.2,
                                            mods={P.NATURAL_FERTILITY_TYPE: natural})
            fert = demographics_model.fertility(inp, 35.0)
            eng = _Engine({f"modifier:{P.NATURAL_FERTILITY_TYPE}": natural})
            eng.vars.update(te_dg_wtfr=fert["wealth"], te_dg_means=fert["means"],
                            te_dg_desired=fert["education"] * fert["survival"] * fert["urban"],
                            te_dg_natural=eng.value(eng._tree(eng.values, "te_demog_tfr_natural")))
            with self.subTest(natural=natural):
                self.assertAlmostEqual(eng.vars["te_dg_natural"], fert["natural"], places=9)
                self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_tfr")), fert["tfr"], places=9)

    def test_the_natural_term_is_the_steps(self):
        """Batch 4 review m5: te_demog_prepare stores the natural term (te_dg_natural) beside the means, and
        te_demog_tfr and the tooltips read the stored figure. A women's-rights law change between two steps then
        moves neither the headline nor its terms until the next step, so the terms keep accounting for it."""
        inp = demographics_model.Inputs(sol=9.0, literacy=0.3, urban_share=0.2,
                                        mods={P.NATURAL_FERTILITY_TYPE: -0.1})
        eng = _engine_for(inp, 1837, 100000.0)
        eng.call("te_demog_prepare")
        self.assertAlmostEqual(eng.vars["te_dg_natural"], 0.9)
        tfr = eng.vars["te_dg_tfr"]
        eng.fixtures[f"modifier:{P.NATURAL_FERTILITY_TYPE}"] = 0.0   # the law changes before the next step
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_tfr")), tfr)
        # the tooltips' term is the stored one too (te_demog_natural_shown, the live term only before any step)
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_natural_shown")), 0.9)
        loc = _text(MISC_LOC)
        for key in ("te_demog_ov_tfr_capital", "te_demog_st_tfr_terms"):
            line = re.search(rf"(?m)^ {key}:0 \"(.*)\"$", loc).group(1)
            self.assertIn("ScriptValue('te_demog_natural_shown')", line, key)
            self.assertNotIn("te_demog_tfr_natural", line, key)

    def test_the_tfr_tooltips_list_natural_fertility_and_the_births_on_top(self):
        """The headline beside the terms is te_dg_tfr, the model's figure x (1 + bz): the terms list women's legal
        standing and the births added on top of the census (batch 1 review, I2), so they account for it."""
        loc = _text(MISC_LOC)
        for key in ("te_demog_ov_tfr_capital", "te_demog_st_tfr_terms"):
            line = re.search(rf"(?m)^ {key}:0 \"(.*)\"$", loc).group(1)
            self.assertIn("ScriptValue('te_demog_natural_shown')", line, key)
            self.assertNotIn("Var('te_dg_natural')", line, key)
            self.assertIn("ScriptValue('te_demog_tfr_on_top')", line, key)
        for bz, want in ((None, 1.0), (0.3, 1.3), (-0.2, 0.8)):
            eng = _Engine({})
            if bz is not None:
                eng.vars["te_dg_bz"] = bz
            self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_tfr_on_top")), want)

    def test_women_s_legal_standing_shows_the_live_term_until_a_step_stores_one(self):
        """Final review 2, m7: a census state from an older save has no te_dg_natural until its next step, and the
        tooltip read ×0.00 beside a headline that isn't 0. It shows the stored term the step used, else the live one."""
        live = {f"modifier:{P.NATURAL_FERTILITY_TYPE}": -0.1}
        eng = _Engine(live)
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_natural_shown")), 0.9)
        eng.vars["te_dg_natural"] = 0.85
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_natural_shown")), 0.85)


    def test_the_tfr_tooltips_list_the_practices(self):
        """Spec 5.3: the two practices beside wealth, women's legal standing, education, child survival, urban life
        and the means, with women's age at first marriage; the country tab adds the country's own means."""
        loc = _text(MISC_LOC)
        for key in ("te_demog_ov_tfr_capital", "te_demog_st_tfr_terms"):
            line = re.search(rf"(?m)^ {key}:0 \"(.*)\"$", loc).group(1)
            for sv in ("te_demog_pr_term_lm", "te_demog_pr_term_bs", "te_demog_marriage_age"):
                self.assertIn(f"ScriptValue('{sv}')", line, f"{key}: {sv}")
        capital = re.search(r"(?m)^ te_demog_ov_tfr_capital:0 \"(.*)\"$", loc).group(1)
        self.assertIn("GetPlayer.MakeScope.ScriptValue('te_demog_marriage_age')", capital)
        self.assertIn("GetPlayer.MakeScope.ScriptValue('te_demog_pr_share_bs')", capital)
        for key in ("te_demog_ov_tfr_tt", "te_demog_st_tfr_tt", "te_demog_how_fertility"):
            text = re.search(rf"(?m)^ {key}:0 \"(.*)\"$", loc).group(1)
            self.assertNotIn("who marries", text, "women's legal standing no longer claims marriage (plan D2)")
            self.assertIn("late marriage", text)
            self.assertIn("birth spacing", text)
        mods = _text(ROOT / "localization" / "english" / "te_modifiers_l_english.yml")
        desc = re.search(r"(?m)^ state_natural_fertility_mult_desc:0 \"(.*)\"$", mods).group(1)
        self.assertNotRegex(desc, r"\bmarr(?:y|ies)\b", "the type is women's standing inside marriage; who marries is "
                                                          "Late Marriage's")

    def test_the_terms_read_one_before_any_share(self):
        """Review Focus 5: an old save's state before its next step shows x1.00 for each, beside a headline that has
        no practice in it."""
        eng = _Engine({})
        for p in P.PRACTICES:
            self.assertEqual(eng.value(eng._tree(eng.values, f"te_demog_pr_term_{p}")), 1.0)
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_marriage_age")), P.MARRIAGE_AGE_AT_ZERO)
        eng.vars.update(te_dg_pr_lm=1.0, te_dg_pr_bs=0.5)
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_pr_term_lm")), 1 - P.PRACTICE_CUT["lm"])
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_marriage_age")),
                               P.MARRIAGE_AGE_AT_ZERO + P.MARRIAGE_AGE_SPAN)

    def test_option_l_logs_the_practices(self):
        line = _block(_text(ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"), "te_debug_demog_mods_line")
        for key, sv in (("lm", "te_debug_demog_pr_lm"), ("bs", "te_debug_demog_pr_bs"),
                        ("lm_target", "te_debug_demog_pr_target_lm"), ("bs_target", "te_debug_demog_pr_target_bs"),
                        ("absorbed_b", "te_debug_demog_line_absorbed_b")):
            self.assertIn(f" {key}=[THIS.ScriptValue('{sv}')|3]", line)
        # option l also logs a state with no census (an unincorporated one, or the rule off): the targets read the
        # walk's variables, so they show -1 there, as the cause multipliers do, instead of reading a missing variable
        eng = _Engine({})
        eng.values.update(_raw_blocks([ROOT / "common" / "script_values" / "te_debug_demog_values.txt"]))
        for p in P.PRACTICES:
            self.assertEqual(eng.value(eng._tree(eng.values, f"te_debug_demog_pr_target_{p}")), -1)

class TestPracticesScript(unittest.TestCase):
    """Late Marriage and Birth Spacing (te_demog_practice_effects.txt and the generated values) against the model:
    docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md, Task 8."""

    INP = demographics_model.Inputs(sol=9.0, literacy=0.3, urban_share=0.2, laws=frozenset({"law_no_womens_rights"}))

    def test_the_start_ladders_match_the_tables(self):
        import demographics_regions as R
        of = R.strategic_region_of()
        cases = [(s, of[s]) for p in P.PRACTICES for s in P.PRACTICE_START_STATE[p]]
        cases += [(None, r) for p in P.PRACTICES for r in P.PRACTICE_START_REGION[p]]
        cases += [("STATE_CAPE_VERDE", "region_southern_europe"), ("STATE_MOSCOW", "region_russia")]
        for state, region in cases:
            eng = _Engine({})
            eng.place = (state, region)
            for p in P.PRACTICES:
                with self.subTest(state=state, region=region, practice=p):
                    self.assertEqual(eng.value(eng._tree(eng.values, f"te_demog_pr_start_{p}")),
                                     demographics_model.practice_start(p, state, region))

    def test_the_targets_match_the_model(self):
        """Impartible inheritance is the laws' Late Marriage line since 2026-10-17: Primogeniture's, or Undivided Farm
        Succession's on Forced Heirship, from the game files; women's paid work reads women's share of the workers, the
        census's own count at the last count, since 2026-10-25 (the women's-rights laws' share before)."""
        types = (P.LM_FARMS_TYPE,)
        lines = DM.load_carriers(types=types)
        for laws, undivided, agr, fjob, lit, contra, access, women in (
                ({"law_no_womens_rights"}, False, 0.6, 0.1, 0.2, 0.0, 0.0, 0.06),
                ({"law_primogeniture", "law_women_in_the_workplace"}, False, 0.5, 0.3, 0.6, 0.2, 0.18, 0.3),
                ({"law_equal_inheritance", "law_protected_class"}, True, 0.4, 0.4, 0.9, 0.35, 0.5, 0.42),
                ({"law_protected_class"}, False, 0.1, 0.5, 1.0, 0.45, 1.0, 0.55)):
            got = DM.totals(lines, laws=laws, types=types,
                            amendments={"amendment_undivided_farm_succession"} if undivided else ())
            farms = got[P.LM_FARMS_TYPE]
            self.assertEqual(farms, 0.15 if undivided or "law_primogeniture" in laws else 0.0, sorted(laws))
            inp = demographics_model.Inputs(literacy=lit, laws=frozenset(laws), agrarian_share=agr,
                                            female_job_share=fjob, work_female_share=women,
                                            mods={P.CONTRACEPTION_TYPE: contra, P.ACCESS_TYPE: access,
                                                  P.LM_FARMS_TYPE: farms})
            eng = _OwnerEngine({f"modifier:{P.CONTRACEPTION_TYPE}": contra, f"modifier:{P.ACCESS_TYPE}": access,
                                f"modifier:{P.LM_FARMS_TYPE}": farms}, laws=laws)
            # the access medicine has reached, at its target here (a seed's): the model reads the same
            eng.vars.update(te_dg_lit=lit, te_dg_agr_share=agr, te_dg_fjob_share=fjob, te_dg_fws_wk=women,
                            te_dg_acc=demographics_model.medicine_targets(inp)["access"])
            for state, region in (("STATE_POSEN", "region_eastern_europe"), ("STATE_KANTO", "region_northeast_asia")):
                eng.place = (state, region)
                for p in P.PRACTICES:
                    start = demographics_model.practice_start(p, state, region)
                    with self.subTest(laws=sorted(laws), state=state, practice=p):
                        self.assertAlmostEqual(eng.value(eng._tree(eng.values, f"te_demog_pr_target_{p}")),
                                               demographics_model.practice_target(p, inp, start), places=9)
                        self.assertAlmostEqual(eng.value(eng._tree(eng.values, f"te_demog_pr_seed_{p}")),
                                               demographics_model.practice_seed(p, inp, start, []), places=9)

    def test_birth_spacing_erodes_with_the_access_medicine_has_reached(self):
        """Since #916 the census's access drifts toward its target (te_dg_acc); Birth Spacing's erosion reads it above
        the base (a default flagged for the owner, 2026-10-12), as demographics_model.practice_erosion does."""
        for drifted in (P.BASE_ACCESS, P.BASE_ACCESS + 0.1, 0.75, 1.0):
            inp = demographics_model.Inputs(literacy=0.5, mods={P.ACCESS_TYPE: 0.6},
                                            medicine={"access": drifted, "infection": 0.0, "maternal": 0.0,
                                                      "chronic": 0.0})
            eng = _Engine({f"modifier:{P.CONTRACEPTION_TYPE}": 0.0, f"modifier:{P.ACCESS_TYPE}": 0.6})
            eng.vars.update(te_dg_lit=0.5, te_dg_acc=drifted)
            with self.subTest(drifted=drifted):
                self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_pr_erosion_bs")),
                                       demographics_model.practice_erosion("bs", inp), places=9)

    def _seeded(self, place, siblings=(), targets=None, erosion=None, region=None):
        eng = _engine_for(self.INP, 1836, 250000.0, place=place, targets=targets, erosion=erosion)
        eng.siblings = [dict(s) for s in siblings]
        eng.region_vars = dict(region or {})
        eng.call("te_demog_seed")
        return eng

    def test_a_whole_region_changing_hands_takes_the_regions_copy(self):
        """Stop B, I1 (owner, 2026-10-12): a change of owner makes a new state object, which carries none of the old
        one's variables. With no sibling left in the region (a revolution's winner holding the whole state), the seed
        takes the region's copy of the shares (te_dg_pr_<P>_r, written at each step), not the eroded start."""
        eng = self._seeded(("STATE_RIGA", "region_eastern_europe"), erosion={"lm": 0.5},
                           region={"te_dg_pr_lm_r": 0.85, "te_dg_pr_bs_r": 0.3})
        self.assertEqual((eng.vars["te_dg_pr_lm"], eng.vars["te_dg_pr_bs"]), (0.85, 0.3))
        for p in P.PRACTICES:
            self.assertAlmostEqual(eng.vars[f"te_dg_pr_{p}"],
                                   demographics_model.practice_seed(p, self.INP, 0.0, [],
                                                                    region=eng.region_vars[f"te_dg_pr_{p}_r"]))

    def test_a_sibling_wins_over_the_regions_copy(self):
        eng = self._seeded(("STATE_POSEN", "region_eastern_europe"),
                           siblings=[{"te_dg_pr_lm": 0.5, "te_dg_pr_bs": 0.1, "state_population": 300000.0}],
                           region={"te_dg_pr_lm_r": 0.85, "te_dg_pr_bs_r": 0.3})
        self.assertEqual((eng.vars["te_dg_pr_lm"], eng.vars["te_dg_pr_bs"]), (0.5, 0.1))

    def test_the_step_writes_the_regions_copy(self):
        """Each step copies the state's shares to its state region; in a split region the last state to step wins,
        which is fine for a fallback."""
        eng = self._seeded(("STATE_KANTO", "region_northeast_asia"), targets={"lm": 0.12, "bs": 0.7})
        self.assertEqual(eng.region_vars, {}, "a seed writes no copy: a new game's regions hold none")
        eng.call("te_demog_practices_step")
        self.assertEqual(eng.region_vars, {f"te_dg_pr_{p}_r": eng.vars[f"te_dg_pr_{p}"] for p in P.PRACTICES})
        body = re.sub(r"#[^\n]*", "", _block(_text(PRACTICE_EFFECTS), "te_demog_practice_seed"))
        self.assertLess(body.index("every_scope_state"), body.index("te_dg_pr_$P$_r"), "siblings first, then the copy")

    def test_a_state_with_no_sibling_seeds_at_its_eroded_start(self):
        """Review I2 and Review Focus 1: with no sibling holding a share, the start less what the state's conditions
        have eroded (0 in an 1836 game, where it is the table)."""
        fresh = self._seeded(("STATE_RIGA", "region_eastern_europe"))
        self.assertEqual((fresh.vars["te_dg_pr_lm"], fresh.vars["te_dg_pr_bs"]), (0.8, 0.0))
        eroded = self._seeded(("STATE_KANTO", "region_northeast_asia"), erosion={"lm": 0.5, "bs": 0.6})
        self.assertAlmostEqual(eroded.vars["te_dg_pr_bs"], 0.4)
        self.assertEqual(eroded.vars["te_dg_pr_lm"], 0.0)

    def test_the_seed_reads_only_its_state_region(self):
        """Review Focus 1: an old save's states seed on their own days, so a neighbour across the Hajnal line (Pskov
        beside Riga) must play no part: the seed walks the other states of its own state region and nothing else."""
        body = re.sub(r"#[^\n]*", "", _block(_text(PRACTICE_EFFECTS), "te_demog_practice_seed"))
        self.assertIn("state_region = {", body)
        self.assertIn("every_scope_state = {", body)
        self.assertNotIn("neighbouring", body)
        # and the walk counts only siblings holding a share, weighted by their people
        eng = self._seeded(("STATE_RIGA", "region_eastern_europe"),
                           siblings=[{"state_population": 500000.0},
                                     {"te_dg_pr_lm": 0.3, "te_dg_pr_bs": 0.0, "state_population": 100000.0}])
        self.assertAlmostEqual(eng.vars["te_dg_pr_lm"], 0.3)

    def test_a_step_on_a_state_with_no_share_seeds_then_drifts(self):
        """Review I4: an old save's state has a census but no share; its next step seeds it, then drifts once."""
        eng = self._seeded(("STATE_KANTO", "region_northeast_asia"), targets={"lm": 0.3, "bs": 0.0},
                           erosion={"bs": 0.5})
        for p in P.PRACTICES:
            del eng.vars[f"te_dg_pr_{p}"]
        eng.call("te_demog_practices_step")
        self.assertAlmostEqual(eng.vars["te_dg_pr_lm"], demographics_model.practice_drift(0.0, 0.3), places=9)
        self.assertAlmostEqual(eng.vars["te_dg_pr_bs"], demographics_model.practice_drift(0.5, 0.0), places=9)

    def test_a_new_state_takes_its_siblings_shares(self):
        """Review Focus 3: a split mid-game is the same people, so it takes its siblings' drifted, people-weighted
        shares, not the 1836 table."""
        sibs = [{"te_dg_pr_lm": 0.5, "te_dg_pr_bs": 0.1, "state_population": 300000.0},
                {"te_dg_pr_lm": 0.9, "te_dg_pr_bs": 0.3, "state_population": 100000.0},
                {"state_population": 900000.0}]                          # a sibling with no share yet
        eng = self._seeded(("STATE_POSEN", "region_eastern_europe"), siblings=sibs)
        self.assertAlmostEqual(eng.vars["te_dg_pr_lm"],
                               demographics_model.practice_seed("lm", self.INP, 0.8, [(3e5, 0.5), (1e5, 0.9)]))
        self.assertAlmostEqual(eng.vars["te_dg_pr_bs"], 0.15)

    def test_a_census_reseed_keeps_the_shares(self):
        """Review Focus 2: a merge, a split, a gap or fast mode's first switch re-seeds the census; the shares stay."""
        eng = _engine_for(self.INP, 1850, 250000.0, place=("STATE_RIGA", "region_eastern_europe"))
        eng.vars.update(te_dg_pr_lm=0.55, te_dg_pr_bs=0.05)
        eng.call("te_demog_seed")
        self.assertEqual((eng.vars["te_dg_pr_lm"], eng.vars["te_dg_pr_bs"]), (0.55, 0.05))

    def test_the_step_drifts_like_the_model_and_prepare_reads_it(self):
        eng = self._seeded(("STATE_KANTO", "region_northeast_asia"), targets={"lm": 0.12, "bs": 0.7})
        plain = self._seeded((None, None))                 # the same state with no practice anywhere
        eng.call("te_demog_practices_step")
        lm = demographics_model.practice_drift(0.0, 0.12)   # Kanto starts at Late Marriage 0, Birth Spacing 1
        bs = demographics_model.practice_drift(1.0, 0.7)
        self.assertAlmostEqual(eng.vars["te_dg_pr_lm"], lm, places=9)
        self.assertAlmostEqual(eng.vars["te_dg_pr_bs"], bs, places=9)
        # each seed counted women among its own workers, which moves its life expectancy and so its children per woman
        # a little (te_demog_women_worker_share, 2026-10-25): the same count in both leaves only the practices
        eng.vars["te_dg_fws_wk"] = plain.vars["te_dg_fws_wk"]
        for e in (eng, plain):
            e.call("te_demog_prepare")
        terms = (1 - P.PRACTICE_CUT["lm"] * lm) * (1 - P.PRACTICE_CUT["bs"] * bs)
        self.assertAlmostEqual(eng.vars["te_dg_tfr"] / plain.vars["te_dg_tfr"], terms, places=9)
        body = _block(_text(EFFECTS), "te_demog_step_begin")
        self.assertLess(body.index("te_demog_practices_step = yes"), body.index("te_demog_prepare = yes"))

    def test_the_tfr_takes_both_terms(self):
        for lm, bs in ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.7, 0.38)):
            inp = dataclasses.replace(self.INP, practices={"lm": lm, "bs": bs})
            fert = demographics_model.fertility(inp, 35.0)
            eng = _Engine({f"modifier:{P.NATURAL_FERTILITY_TYPE}": 0.0})
            eng.vars.update(te_dg_wtfr=fert["wealth"], te_dg_means=fert["means"], te_dg_natural=fert["natural"],
                            te_dg_desired=fert["education"] * fert["survival"] * fert["urban"],
                            te_dg_pr_lm=lm, te_dg_pr_bs=bs)
            with self.subTest(lm=lm, bs=bs):
                self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_tfr")), fert["tfr"], places=9)

    def test_the_seed_runs_before_prepare(self):
        body = _block(_text(EFFECTS), "te_demog_seed")
        self.assertLess(body.index("te_demog_practices_seed = yes"), body.index("te_demog_prepare = yes"))

class _CountryEngine(_Engine):
    """_Engine plus the iterators and scope changes the country effects use. every_scope_war runs
    its body once per war in `wars` (the owner's dead in it, read through te_demog_war_dead_root);
    every_scope_state once per state in `states` (a dict of that state's variables, the locals
    staying shared); ordered_scope_state the best `max` of them by `order_by` (highest first,
    state_population read from the dict's own `state_population`); root = { } the country's
    variables, whatever scope is current. Variable
    lists live in `lists` (name -> the state dicts added), saved temporary scopes in `scopes` (a
    `scope:X` value is the state dict itself). A state's `owner = { }` trigger and `owner.X` read
    the country's variables (and fixtures); `any_scope_state` tests every state in `states`."""

    BLOCKS = ("every_scope_war", "every_scope_state", "ordered_scope_state", "root")

    def __init__(self, wars=(), states=(), **kwargs):
        super().__init__(**kwargs)
        self.wars, self.states = list(wars), list(states)
        self.root_vars = self.vars
        self.lists, self.scopes = {}, {}

    def number(self, tok):
        if tok.startswith("scope:"):
            return self.scopes[tok[6:]]
        if tok in ("root", "ROOT"):
            return self.root_vars   # the country, as a value (te_dg_primate_of = root)
        if tok.startswith("owner."):
            saved, self.vars = self.vars, self.root_vars
            try:
                return self.number(tok[6:])
            finally:
                self.vars = saved
        return super().number(tok)

    def holds_in(self, scope_vars, items):
        saved, self.vars = self.vars, scope_vars
        try:
            return self.holds(items)
        finally:
            self.vars = saved

    def value_in(self, scope_vars, name):
        saved, self.vars = self.vars, scope_vars
        try:
            return self.value(name)
        finally:
            self.vars = saved

    def run(self, items):
        batch = []
        for item in items:
            if item[0] in self.BLOCKS or item[0] in ("clear_variable_list", "add_to_variable_list"):
                super().run(batch)
                batch = []
                if item[0] in self.BLOCKS:
                    self._iterate(item[0], item[2])
                elif item[0] == "clear_variable_list":
                    self.lists[item[2]] = []
                else:
                    assert self.vars is self.root_vars, "a list is added to from the country"
                    target = _find(item[2], "target")
                    assert target.startswith("scope:"), target
                    self.lists.setdefault(_find(item[2], "name"), []).append(self.scopes[target[6:]])
            else:
                batch.append(item)
        super().run(batch)

    def _test(self, key, op, arg):
        if key == "any_scope_state":
            return any(self.holds_in(state_vars, arg) for state_vars in self.states)
        if key == "has_variable_list":
            assert self.vars is self.root_vars, "a list is kept on the country"
            return arg in self.lists
        if key == "owner":
            return self.holds_in(self.root_vars, arg)
        return super()._test(key, op, arg)

    def _in(self, scope_vars, body):
        saved, self.vars = self.vars, scope_vars
        try:
            self.run(body)
        finally:
            self.vars = saved

    def _iterate(self, key, arg):
        if key == "root":
            return self._in(self.root_vars, arg)
        body = [i for i in arg if i[0] not in ("limit", "order_by", "max", "check_range_bounds",
                                                "save_temporary_scope_as")]
        if key == "every_scope_war":
            for dead in self.wars:
                self.fixtures["te_demog_war_dead_root"] = float(dead)
                self.run(body)
            return
        limit = next((v for k, _, v in arg if k == "limit"), [])
        chosen = []
        for state_vars in self.states:
            self.vars = state_vars
            try:
                if self.holds(limit):
                    chosen.append(state_vars)
            finally:
                self.vars = self.root_vars
        if key == "ordered_scope_state":
            def rank(state_vars):
                self.fixtures["state_population"] = state_vars.get("state_population", 0.0)
                saved, self.vars = self.vars, state_vars
                try:
                    return self.value(_find(arg, "order_by"))
                finally:
                    self.vars = saved
            chosen = sorted(chosen, key=rank, reverse=True)[:int(float(_find(arg, "max")))]
        for state_vars in chosen:
            if key == "ordered_scope_state":
                self.scopes[_find(arg, "save_temporary_scope_as")] = state_vars
            self._in(state_vars, body)


# the war-dead tests run the yearly effect without its census and Wealth Concentration (TestWealth's)
NO_CENSUS = {"te_demog_country_census": "", "te_demog_wc_war_shock": "", "te_demog_wc_national": ""}


class TestConcentrationRows(unittest.TestCase):
    def test_the_rows_check_the_states_owner_exists(self):
        """A state the national refresh chose can lose its owner before the next refresh: 'Event target
        link owner returned an invalid object' at te_demog_sguis.txt, read every frame the panel is open."""
        text = _text(ROOT / "common" / "scripted_guis" / "te_demog_sguis.txt")
        for sgui, var in (("te_demog_wc_top_sgui", "te_dg_wc_top"), ("te_demog_wc_bottom_sgui", "te_dg_wc_bottom")):
            shown = _block(text, sgui)
            self.assertRegex(shown, rf"var:{var} = {{\s*exists = owner\s*owner = ROOT\s*}}", sgui)


class TestFlows(unittest.TestCase):
    def test_finished_war_never_returns_its_dead(self):
        """Review Focus 4: the monthly change in summed war dead is floored at zero."""
        body = _block(_text(EFFECTS), "te_demog_country_monthly")
        self.assertRegex(body, r"subtract = var:te_dg_war_seen\s+min = 0")

    def test_kill_sites_record_their_dead(self):
        effects = _text(ROOT / "common" / "scripted_effects" / "extra_effects.txt")
        for name in ("nuclear_industrial_strike", "nuclear_tactical_strike"):
            self.assertIn("te_demog_note_kills", _block(effects, name), name)
        on_actions = _text(ROOT / "common" / "on_actions" / "extra_on_actions.txt")
        self.assertEqual(on_actions.count("te_demog_note_kills"), 2)   # both Violent Hostility kills

    def test_crisis_adds_devastation_as_a_share(self):
        """A state's devastation reads as a 0-1 share, as turmoil does (vanilla compares
        devastation > 0.1, >= 0.5; add_devastation takes points), so both are added as they are."""
        body = _block(_text(VALUES), "te_demog_crisis")
        self.assertRegex(body, r"add = devastation\b")
        self.assertNotIn("divide = 100", body)
        self.assertIn("add = turmoil", body)

    def test_tactical_strike_tallies_its_soldiers_in_a_local(self):
        """Inside the pop walk change_variable writes the pop's own variable and total_population is a
        country trigger: the tally has to be a local, in total_size, added to the state's after the walk."""
        effects = _text(ROOT / "common" / "scripted_effects" / "extra_effects.txt")
        body = _block(effects, "nuclear_tactical_strike")
        start = body.index("every_scope_pop = {")
        depth, i = 1, body.index("{", start) + 1
        while depth:
            depth += {"{": 1, "}": -1}.get(body[i], 0)
            i += 1
        walk = body[start:i]
        self.assertIn("change_local_variable", walk)
        self.assertIn("total_size", walk)
        self.assertNotIn("change_variable", walk)
        self.assertNotIn("total_population", walk)
        after = body[i:]
        self.assertLess(body.index("set_local_variable = { name = te_dg_ts value = 0 }"), start)
        self.assertLess(after.index("add = local_var:te_dg_ts"), after.index("te_demog_note_kills"))
        self.assertLess(after.index("te_demog_note_kills"), after.index("kill_population_percent_in_state"))

    def test_residual_ignores_noise(self):
        body = _block(_text(EFFECTS), "te_demog_flows")
        self.assertIn("te_demog_k_residual_noise_share", body)

    def test_country_pulses_are_hooked(self):
        text = _text(DEMOG_ON_ACTIONS)
        self.assertRegex(_block(text, "on_monthly_pulse_country"), r"te_demog_country_monthly_on_action")
        self.assertRegex(_block(text, "on_yearly_pulse_country"), r"te_demog_country_yearly_on_action")
        monthly = _block(text, "te_demog_country_monthly_on_action")
        self.assertIn("te_demog_country_monthly = yes", monthly)
        self.assertNotIn("te_demog_cohorts_run", monthly)   # Task 11's war shock reads the same total
        self.assertIn("te_demog_country_yearly = yes", _block(text, "te_demog_country_yearly_on_action"))
        self.assertIn("te_demog_cohorts_run = yes", _block(_text(EFFECTS), "te_demog_country_yearly"))

    def test_flows_set_every_local_the_step_reads(self):
        """Whatever the branch, te_demog_flows leaves the locals te_demog_no_flows names: each is set
        at its top level (one tab), not inside an if."""
        flows = _block(_text(EFFECTS), "te_demog_flows")
        body = (flows + _block(_text(GENERATED_EFFECTS), "te_demog_set_profile")
                + _block(_text(GENERATED_EFFECTS), "te_demog_migrant_rates"))
        self.assertRegex(flows, r"(?m)^\tte_demog_set_profile = yes$", "the profile is set unconditionally")
        self.assertRegex(flows, r"(?m)^\tte_demog_migrant_rates = yes$", "the booking's rates are set unconditionally")
        names = re.findall(r"name = (te_dg_\w+) value", _block(_text(EFFECTS), "te_demog_no_flows"))
        # 16, and the war dead and the people killed the Causes of Death slices take (issue #1029)
        self.assertEqual(len(names), 18)
        for name in names:
            self.assertIsNotNone(re.search(rf"^\tset_local_variable = \{{\s+name = {name}\s+value", body, re.M), name)

    def test_each_war_adds_its_dead_to_the_year(self):
        eng = _CountryEngine(wars=[100, 50], fixtures={}, triggers={"te_demog_cohorts_run": False})
        for wars, want_seen, want_year in (
            ([100, 50], 150, 0),   # first run: starts from the dead already counted
            ([130, 80], 210, 60),
            ([130], 130, 60),      # a war ended: the sum fell, nothing is returned or subtracted
            ([140], 140, 70),
            ([], 0, 70),           # peace
        ):
            eng.wars = wars
            eng.call("te_demog_country_monthly")
            self.assertEqual((eng.vars["te_dg_war_seen"], eng.vars["te_dg_war_year"]), (want_seen, want_year), wars)

    def _states(self, *soldiers_people_census):
        out = []
        for soldiers, people, census in soldiers_people_census:
            state = {"te_dg_soldiers": float(soldiers), "te_dg_people": float(people)}
            if census:
                state["te_dg_year"] = 1836.0
            out.append(state)
        return out

    def month(self, eng, wars):
        eng.wars = wars
        eng.call("te_demog_country_monthly")

    def test_each_months_dead_go_to_states_by_their_soldiers(self):
        """Codex review on #830: the states take the dead month by month, so a state's step (on its
        own day) takes the dead of the same months as its population change; the yearly pulse only
        clears the year's total after the war shock reads it."""
        states = self._states((300, 10000, True), (100, 30000, True), (600, 5000, False))
        states[0]["te_dg_war_in"] = 5.0   # an earlier share not yet taken is kept
        eng = _CountryEngine(states=states, fixtures={}, triggers={"te_demog_cohorts_run": True},
                             effects=NO_CENSUS)
        self.month(eng, [0])          # first run: the starting count
        self.month(eng, [600])
        self.assertEqual((states[0]["te_dg_war_in"], states[1]["te_dg_war_in"]), (5.0 + 450.0, 150.0))
        states[0].pop("te_dg_war_in")  # state 0 steps on its pulse and takes its share
        self.month(eng, [1000])
        self.assertEqual((states[0]["te_dg_war_in"], states[1]["te_dg_war_in"]), (300.0, 250.0))
        self.assertNotIn("te_dg_war_in", states[2], "a state with no census is skipped")
        self.assertEqual(eng.vars["te_dg_war_year"], 1000.0)
        eng.call("te_demog_country_yearly")
        self.assertEqual(eng.vars["te_dg_war_year"], 0.0)
        self.assertEqual((states[0]["te_dg_war_in"], states[1]["te_dg_war_in"]), (300.0, 250.0),
                         "the yearly pulse shares nothing more")

    def test_a_country_without_soldiers_shares_by_people(self):
        states = self._states((0, 10000, True), (0, 30000, True))
        eng = _CountryEngine(states=states, fixtures={}, triggers={"te_demog_cohorts_run": True})
        self.month(eng, [0])
        self.month(eng, [400])
        self.assertEqual((states[0]["te_dg_war_in"], states[1]["te_dg_war_in"]), (100.0, 300.0))

    def test_no_dead_or_no_rule_shares_nothing(self):
        for rule, wars in ((True, [0, 0]), (False, [0, 500])):
            states = self._states((300, 10000, True))
            eng = _CountryEngine(states=states, fixtures={}, triggers={"te_demog_cohorts_run": rule},
                                 effects=NO_CENSUS)
            for dead in wars:
                self.month(eng, [dead])
            self.assertNotIn("te_dg_war_in", states[0], (rule, wars))
            self.assertEqual(eng.vars["te_dg_war_year"], float(wars[-1]), (rule, wars))
            # the year's dead are cleared after the shock, so they are never shared out later
            eng.call("te_demog_country_yearly")
            self.assertEqual(eng.vars["te_dg_war_year"], 0.0, (rule, wars))
            self.assertNotIn("te_dg_war_in", states[0], (rule, wars))

    def test_known_kills_add_up_and_only_where_the_census_runs(self):
        call = "te_demog_note_kills = { VALUE = var:struck }"
        for rule, census, want in ((True, True, 700.0), (True, False, None), (False, True, None)):
            eng = _Engine({}, triggers={"te_demog_cohorts_run": rule})
            eng.vars["struck"] = 300.0
            if census:
                eng.vars["te_dg_year"] = 1836.0
            eng.run(_parse_script(call))
            eng.vars["struck"] = 400.0
            eng.run(_parse_script(call))
            self.assertEqual(eng.vars.get("te_dg_kills_in"), want, (rule, census))


class TestTrend(unittest.TestCase):
    """The arrows (Task 10): a figure's last-year value is kept, and its trend drawn, only when both
    the figure and the one before it came from a step. A seed writes 0 births and deaths, so a
    seed's CBR and CDR are no year to compare with."""

    INP = TestCohortScript.INP
    POP = 250000.0

    def stepped_engine(self):
        """A state seeded in 1836, with what its walk gives the step's flows (no residual, no crisis)."""
        eng = _engine_for(self.INP, 1836, self.POP)
        eng.call("te_demog_seed")
        eng.fixtures.update(te_demog_crisis=0.0, te_demog_family_transport=0.0)
        eng.vars.update(te_dg_eb=0.0, te_dg_ed=0.0, te_dg_fjob_share=0.3)
        return eng

    def step(self, eng, year):
        eng.fixtures["year"] = float(year)
        eng.vars["te_dg_pop_last"] = eng.vars["te_dg_people"]
        eng.call("te_demog_step")

    def seen(self, eng):
        return {k: eng.vars.get(k) for k in ("te_dg_trend_ok", "te_dg_stepped")}, \
            {k: k in eng.vars for k in ("te_dg_prev_median", "te_dg_prev_cbr", "te_dg_prev_tfr", "te_dg_prev_e0")}

    def test_a_step_with_no_births_is_still_a_step(self):
        """te_dg_stepped says a step ran, not that it had births: a state with no women (here every woman taken out of
        the ring) steps, records 0 births and keeps its arrows. Read from the births, the step looked like a seed."""
        eng = self.stepped_engine()
        self.step(eng, 1837)
        for name in [n for n in eng.vars if re.fullmatch(r"te_dg_f\d+", n)] + ["te_dg_pf"]:
            eng.vars[name] = 0.0
        self.step(eng, 1838)
        self.assertEqual(eng.vars["te_dg_births"], 0.0)
        self.assertEqual(self.seen(eng)[0], {"te_dg_trend_ok": 1.0, "te_dg_stepped": 1.0})

    def test_state_arrows_come_from_the_second_step_on(self):
        eng = self.stepped_engine()
        flags, prev = self.seen(eng)
        self.assertEqual(flags, {"te_dg_trend_ok": 0.0, "te_dg_stepped": 0.0})
        self.assertFalse(any(prev.values()), "a seed has no last year")
        seed_tfr, seed_e0 = eng.vars["te_dg_tfr"], eng.vars["te_dg_e0"]
        self.step(eng, 1837)
        flags, prev = self.seen(eng)
        self.assertEqual(flags, {"te_dg_trend_ok": 0.0, "te_dg_stepped": 1.0}, "the year before it was a seed")
        self.assertFalse(any(prev.values()), "the seed's zero births are not kept as last year's CBR")
        self.assertGreater(eng.vars["te_dg_births"], 0)
        first_cbr, first_tfr, first_e0 = eng.vars["te_dg_cbr"], eng.vars["te_dg_tfr"], eng.vars["te_dg_e0"]
        self.step(eng, 1838)
        flags, prev = self.seen(eng)
        self.assertEqual(flags, {"te_dg_trend_ok": 1.0, "te_dg_stepped": 1.0})
        self.assertTrue(all(prev.values()))
        self.assertEqual(eng.vars["te_dg_prev_cbr"], first_cbr)
        self.assertEqual(eng.vars["te_dg_prev_tfr"], first_tfr)
        self.assertEqual(eng.vars["te_dg_prev_e0"], first_e0)
        self.assertGreater(first_cbr, 0, "the first step's CBR is real")
        # a re-seed (a census gap, an emptied ring) starts the sequence over
        eng.call("te_demog_seed")
        flags, _prev = self.seen(eng)
        self.assertEqual(flags, {"te_dg_trend_ok": 0.0, "te_dg_stepped": 0.0})
        self.step(eng, 1839)
        self.assertEqual(self.seen(eng)[0], {"te_dg_trend_ok": 0.0, "te_dg_stepped": 1.0})
        self.assertNotEqual(seed_tfr, 0)
        self.assertNotEqual(seed_e0, 0)

    def test_prepare_keeps_last_years_tfr_and_e0_only_after_a_step(self):
        """te_demog_prepare overwrites both, so the copy sits before it; Task 8 had none."""
        body = _block(_text(EFFECTS), "te_demog_prepare")
        self.assertLess(body.index("te_dg_prev_tfr"), body.index("te_demog_life_table"))
        self.assertLess(body.index("te_dg_prev_e0"), body.index("te_demog_life_table"))
        eng = _engine_for(self.INP, 1837, self.POP)
        eng.vars.update(te_dg_tfr=3.3, te_dg_e0=44.0, te_dg_stepped=0.0)
        eng.call("te_demog_prepare")
        self.assertFalse("te_dg_prev_tfr" in eng.vars)
        eng.vars.update(te_dg_tfr=3.3, te_dg_e0=44.0, te_dg_stepped=1.0)
        eng.call("te_demog_prepare")
        self.assertEqual((eng.vars["te_dg_prev_tfr"], eng.vars["te_dg_prev_e0"]), (3.3, 44.0))
        self.assertNotEqual(eng.vars["te_dg_tfr"], 3.3)

    def test_a_population_jump_steps_and_keeps_the_arrows(self):
        """No size test (owner, 2026-10-20): a state whose people moved far since the last census steps like any other,
        books the move as migration and keeps its arrows. Until then a move of more than 25% seeded again (no migrants,
        the arrows started over), on the premise that it was a state merged or split; in the 2057 game it fired only on
        migration."""
        stubs = {"te_demog_walks": "", "te_inh_refresh_rural_effects": "", "te_demog_wc_state_yearly": "",
                 "te_inh_refresh_wc_state_effects": ""}
        for growth in (1.4, 0.6, 1.03, 5.0, 0.3):
            with self.subTest(growth=growth):
                eng = _engine_for(self.INP, 1836, self.POP, effects=stubs)
                eng.call("te_demog_seed")
                eng.fixtures.update(te_demog_crisis=0.0, te_demog_family_transport=0.0)
                eng.vars.update(te_dg_eb=0.0, te_dg_ed=0.0, te_dg_fjob_share=0.3)
                self.step(eng, 1837)
                self.step(eng, 1838)
                self.assertEqual(self.seen(eng)[0], {"te_dg_trend_ok": 1.0, "te_dg_stepped": 1.0})
                people = eng.vars["te_dg_people"]
                eng.fixtures.update(year=1839.0, state_population=people * growth)
                eng.call("te_demog_state_yearly")
                self.assertEqual(eng.vars["te_dg_year"], 1839.0)
                self.assertEqual(self.seen(eng)[0], {"te_dg_trend_ok": 1.0, "te_dg_stepped": 1.0})
                self.assertGreater(eng.vars["te_dg_births"], 0)
                self.assertAlmostEqual(eng.vars["te_dg_net_migration"], (growth - 1) * people, delta=1.0)
                self.assertAlmostEqual(eng.vars["te_dg_people"], people * growth)
                self.assertAlmostEqual(eng.vars["te_dg_pop_last"], people * growth)

    def test_fast_mode_skips_wealth_concentration_for_a_state_not_yet_walked(self):
        """Fast mode moves the walk to the clock's steps, but the yearly pulse still updates Wealth
        Concentration and inheritance's rural modifiers, which read the walk's sums. A state that appears between steps (a colony, a
        split) had none: 'Value of wrong type' at te_demog_wealth_effects.txt:64 and te_demog_values.txt,
        a few lines a game year in the 2026-10-10 fast run. It waits for its first walk."""
        stubs = {"te_demog_walks": "", "te_inh_refresh_wc_state_effects": "", "te_demog_state_census": "",
                 "te_demog_wc_state_yearly": "set_variable = { name = wc_ran value = 1 }",
                 "te_inh_refresh_rural_effects": "set_variable = { name = rural_ran value = 1 }"}
        for walked in (False, True):
            with self.subTest(walked=walked):
                eng = _Engine({}, triggers={"te_demog_clock_on": True}, effects=stubs)
                if walked:
                    eng.vars["te_dg_walk_pop"] = 1000.0
                eng.call("te_demog_state_yearly")
                # inheritance's rural modifiers read the walk's agrarian share (te_inheritance_effects.txt:251/258)
                self.assertEqual(("wc_ran" in eng.vars, "rural_ran" in eng.vars), (walked, walked))

    def test_a_seed_off_the_pulse_is_made_again_at_the_pulse(self):
        """Codex review on #830: game start and the console seed on a day that is not the state's
        pulse, so a step at the next pulse a year on would compare 12 to 24 months of change with a
        year's natural change. The state is marked, its first pulse seeds again (same year or not),
        and the step comes a year after that; a seed made on the pulse is not marked."""
        stubs = {"te_demog_walks": "", "te_inh_refresh_rural_effects": "", "te_demog_wc_state_yearly": "",
                 "te_inh_refresh_wc_state_effects": ""}
        for pulse_year in (1836, 1837):
            with self.subTest(pulse_year=pulse_year):
                eng = _engine_for(self.INP, 1836, self.POP, effects=stubs)
                eng.call("te_demog_seed_off_pulse")
                self.assertEqual(eng.vars["te_dg_reseed"], 1.0)
                eng.fixtures.update(te_demog_crisis=0.0, te_demog_family_transport=0.0)
                eng.vars.update(te_dg_eb=0.0, te_dg_ed=0.0, te_dg_fjob_share=0.3)
                eng.fixtures.update(year=float(pulse_year), state_population=self.POP * 1.02)
                eng.call("te_demog_state_yearly")
                self.assertNotIn("te_dg_reseed", eng.vars)
                self.assertEqual(eng.vars["te_dg_year"], float(pulse_year))
                self.assertEqual(eng.vars["te_dg_births"], 0.0, "seeded again, not stepped")
                self.assertAlmostEqual(eng.vars["te_dg_pop_last"], self.POP * 1.02)
                eng.fixtures.update(year=float(pulse_year + 1))
                eng.call("te_demog_state_yearly")
                self.assertGreater(eng.vars["te_dg_births"], 0, "a year on: the first step")
        eng = _engine_for(self.INP, 1836, self.POP, effects=stubs)
        eng.call("te_demog_seed")
        self.assertNotIn("te_dg_reseed", eng.vars, "a seed on the pulse is not marked")

    def test_off_pulse_seeds_are_marked(self):
        """Every seed made away from the state's own pulse goes through te_demog_seed_off_pulse."""
        self.assertIn("te_demog_seed_off_pulse = yes", _block(_text(EFFECTS), "te_demog_country_game_start"))
        console = _text(ROOT / "events" / "te_debug_demog_events.txt")
        self.assertIn("te_demog_seed_off_pulse = yes", console)
        self.assertNotIn("te_demog_seed = yes", console)
        body = _block(_text(EFFECTS), "te_demog_state_census")
        self.assertIn("has_variable = te_dg_reseed", body)

    def test_a_seed_zeroes_net_migration(self):
        """Only a step's flows write it, and the country sums it over every state with a census."""
        eng = _engine_for(self.INP, 1836, self.POP)
        eng.vars["te_dg_net_migration"] = 4000.0
        eng.vars["te_dg_mig_raw"] = 4000.0
        eng.call("te_demog_seed")
        self.assertEqual(eng.vars["te_dg_net_migration"], 0.0)
        self.assertEqual(eng.vars["te_dg_mig_raw"], 0.0)


class TestCountry(unittest.TestCase):
    def test_country_sums_skip_states_without_a_census(self):
        """Review Focus 1."""
        body = _block(_text(EFFECTS), "te_demog_country_census")
        for m in re.finditer(r"every_scope_state = \{", body):
            self.assertIn("te_demog_has_census = yes", body[m.end():m.end() + 200])
        self.assertIn("te_demog_country_lists = yes", body)
        lists = _block(_text(EFFECTS), "te_demog_country_lists")
        for m in re.finditer(r"ordered_scope_state = \{", lists):
            self.assertIn("te_demog_has_census = yes", lists[m.end():m.end() + 200])

    def test_the_country_sums_the_residual_before_the_noise_band(self):
        """The census log's gate check: moves between a country's own states cancel in this sum, which
        the floored te_dg_net_migration can't promise (a state's small loss is zeroed, a city's gain kept).
        A state loaded from a save made before te_dg_mig_raw existed has none until its next step."""
        body = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertIn("set_local_variable = { name = te_dg_c_mig_raw value = 0 }", body)
        add = body.index("change_local_variable = { name = te_dg_c_mig_raw add = var:te_dg_mig_raw }")
        self.assertLess(body.rindex("has_variable = te_dg_mig_raw", 0, add), add)
        self.assertIn("set_variable = { name = te_dg_mig_raw value = local_var:te_dg_c_mig_raw }", body)

    def test_a_revolutions_winner_gets_its_lists_back(self):
        """Review on #830: the winner inherits te_dg_census_year but no variable list, so the
        civil-war repair draws the lists again (behind the rule and a census) instead of leaving the
        States table empty until its next yearly census."""
        body = _block(_text(INH_EFFECTS), "inh_repair_after_civil_war")
        call = body.index("te_demog_country_lists = yes")
        self.assertLess(body.rindex("te_demog_cohorts_run = yes", 0, call), call)
        self.assertLess(body.rindex("has_variable = te_dg_census_year", 0, call), call)

    def test_projection_for_players_only(self):
        body = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertIn("is_ai = no", body[:body.index("te_demog_project = yes")])

    def test_the_census_is_wired_where_the_brief_puts_it(self):
        yearly = _block(_text(EFFECTS), "te_demog_country_yearly")
        self.assertNotIn("te_demog_share_war_dead", yearly, "the states take the war dead monthly")
        self.assertLess(yearly.index("te_demog_cohorts_run = yes"), yearly.index("te_demog_country_census = yes"))
        monthly = _block(_text(EFFECTS), "te_demog_country_monthly")
        self.assertLess(monthly.index("te_demog_cohorts_run = yes"), monthly.index("te_demog_share_war_dead = yes"))
        start = _block(_text(EFFECTS), "te_demog_country_game_start")
        self.assertLess(start.rindex("te_demog_cohorts_run = yes"), start.index("te_demog_country_census = yes"))
        self.assertGreater(start.index("te_demog_country_census = yes"), start.rindex("te_demog_seed_off_pulse = yes"))

    def test_the_practices_are_people_weighted(self):
        """Spec 3.1: the country shows each practice's people-weighted mean (te_demog_practice_country_*)."""
        states = self.three()
        for s, (lm, bs) in zip(states, ((1.0, 0.0), (0.5, 0.2), (0.0, 1.0))):
            s.update(te_dg_pr_lm=lm, te_dg_pr_bs=bs)
        eng = self.country(states)
        eng.call("te_demog_country_census")
        people = sum(s["te_dg_people"] for s in states)
        for p in P.PRACTICES:
            want = sum(s[f"te_dg_pr_{p}"] * s["te_dg_people"] for s in states) / people
            self.assertAlmostEqual(eng.vars[f"te_dg_pr_{p}"], want, places=6, msg=p)

    def test_the_city_ranking_script_value_is_negated(self):
        body = _block(_text(VALUES), "te_demog_neg_city_rank")
        self.assertIn("var:state_city_size_rank", body)
        self.assertRegex(body, r"multiply = -1")

    def test_squares_are_taken_in_units_of_100_000_people(self):
        """Values are i64 x 1e-5: the square of 10 million people is past the limit, and in millions the
        square of a state under ~3,200 urban people is under one unit (0.0032 squared); 100,000 keeps both."""
        body = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertRegex(body, r"var:te_dg_urban\s+divide = 100000\s")
        self.assertNotRegex(body, r"var:te_dg_urban\s+divide = 1000000")
        self.assertNotRegex(body, r"var:te_dg_urban\s+multiply = var:te_dg_urban")

    # -- the numbers, through the interpreter ---------------------------------------------------

    INPUTS = (   # (people, urban people, SoL, literacy): a big, a middling, a small state
        (4_000_000, 1_600_000, 22, 0.55),
        (1_500_000, 300_000, 14, 0.3),
        (600_000, 90_000, 9, 0.1),
    )

    @classmethod
    def setUpClass(cls):
        cls._three = [cls.state(*args, rank=r, migration=m)
                      for args, r, m in zip(cls.INPUTS, (12, 3, 40), (5000.0, -1200.0, 300.0))]

    @classmethod
    def state(cls, pop, urban, sol, literacy, rank=None, births=None, deaths=None, migration=0.0):
        """A state as a seed leaves it, with the figures a step would have given it."""
        inp = demographics_model.Inputs(sol=sol, literacy=literacy, urban_share=urban / pop,
                                        techs=frozenset({"medical_degrees"}),
                                        laws=frozenset({"law_women_in_the_fields"}))
        eng = _engine_for(inp, 1836, pop)
        eng.vars["te_dg_urban"] = float(urban)
        eng.call("te_demog_seed")
        v = eng.vars
        v["state_population"] = float(pop)
        if rank is not None:
            v["state_city_size_rank"] = float(rank)
        v["te_dg_births"] = births if births is not None else pop * 0.038
        v["te_dg_deaths"] = deaths if deaths is not None else pop * 0.031
        v["te_dg_net_migration"] = float(migration)
        v["te_dg_stepped"] = 1.0
        return v

    def three(self):
        return [dict(s) for s in self._three]

    def country(self, states, ai=False, **kwargs):
        return _CountryEngine(states=states, fixtures={"year": 1900.0},
                              triggers={"is_ai": ai, "te_demog_cohorts_run": True}, **kwargs)

    def test_a_country_has_stepped_when_a_state_has(self):
        """The country's te_dg_stepped: 1 when any of its states' figures came from a step, births or none; 0 when
        every one came from a seed (game start, the console's re-seeds)."""
        for stepped, want in (((1.0, 0.0, 0.0), 1.0), ((0.0, 0.0, 0.0), 0.0)):
            with self.subTest(stepped=stepped):
                states = self.three()
                for st, flag in zip(states, stepped):
                    st.update(te_dg_stepped=flag, te_dg_births=0.0)
                eng = self.country(states)
                eng.call("te_demog_country_census")
                self.assertEqual(eng.vars["te_dg_stepped"], want)

    def test_figures_are_the_weighted_sums_of_the_census_states(self):
        states = self.three()
        nope = {"te_dg_people": 9e9, "te_dg_births": 9e9, "te_dg_urban": 9e9, "state_population": 9e9}   # no te_dg_year
        eng = self.country(states + [nope])
        eng.call("te_demog_country_census")
        v = eng.vars
        people = sum(s["te_dg_people"] for s in states)
        births, deaths = sum(s["te_dg_births"] for s in states), sum(s["te_dg_deaths"] for s in states)
        for b in range(18):
            for sex in "fm":
                self.assertAlmostEqual(v[f"te_dg_cb{sex}{b}"], sum(s[f"te_dg_b{sex}{b}"] for s in states), places=6)
        w = sum(s["te_dg_w1549"] for s in states)
        self.assertAlmostEqual(v["te_dg_w1549"], w, places=4)
        self.assertAlmostEqual(v["te_dg_tfr"], sum(s["te_dg_tfr"] * s["te_dg_w1549"] for s in states) / w, places=9)
        self.assertAlmostEqual(v["te_dg_e0"], sum(s["te_dg_e0"] * s["te_dg_people"] for s in states) / people, places=6)
        self.assertAlmostEqual(v["te_dg_e65"], sum(s["te_dg_e65"] * s["te_dg_people"] for s in states) / people,
                               places=6)
        for sex in "fm":    # issue #1029: the Life Expectancy hover's women and men, by the same weights
            self.assertAlmostEqual(v[f"te_dg_e0{sex}"],
                                   sum(s[f"te_dg_e0{sex}"] * s["te_dg_people"] for s in states) / people, places=6)
        self.assertAlmostEqual(v["te_dg_imr"], sum(s["te_dg_imr"] * s["te_dg_births"] for s in states) / births,
                               places=6)
        self.assertAlmostEqual(v["te_dg_cbr"], births * 1000 / people, places=9)
        self.assertAlmostEqual(v["te_dg_cdr"], deaths * 1000 / people, places=9)
        self.assertEqual(v["te_dg_net_migration"], 4100.0)
        self.assertEqual(v["te_dg_census_year"], 1900.0)
        # the shares and the median come from the country's bands, as a state's do
        total = sum(v[f"te_dg_cb{sex}{b}"] for sex in "fm" for b in range(18))
        young = sum(v[f"te_dg_cb{sex}{b}"] for sex in "fm" for b in range(3))
        old = sum(v[f"te_dg_cb{sex}{b}"] for sex in "fm" for b in range(13, 18))
        self.assertAlmostEqual(v["te_dg_young_share"], young / total, places=9)
        self.assertAlmostEqual(v["te_dg_old_share"], old / total, places=9)
        self.assertAlmostEqual(v["te_dg_working_share"], 1 - (young + old) / total, places=9)
        self.assertAlmostEqual(v["te_dg_dependency"], (young + old) / (total - young - old), places=9)
        self.assertTrue(15 < v["te_dg_median"] < 35)

    def test_urban_pattern(self):
        states = self.three()
        eng = self.country(states)
        eng.call("te_demog_country_census")
        v = eng.vars
        urban = [s["te_dg_urban"] / 1e5 for s in states]   # in units of 100,000 people
        people = sum(s["te_dg_people"] for s in states)
        self.assertAlmostEqual(v["te_dg_urban_share"], sum(urban) * 1e5 / people, places=9)
        self.assertAlmostEqual(v["te_dg_primacy"], max(urban) / sum(urban), places=9)
        self.assertAlmostEqual(v["te_dg_n_cities"], sum(urban) ** 2 / sum(u * u for u in urban), places=9)
        self.assertEqual(v["te_dg_urban_label"], 0.0, "1.6 of 1.99 million is Primate")
        self.assertAlmostEqual(v["te_dg_urban_share"], 1_990_000 / 6_100_000, places=9)
        self.assertFalse("te_dg_cities" in v, "te_dg_cities is the list of the three largest, not a number")

    def test_labels_by_primacy(self):
        """Primate from 40%, Dominant from 25%, Balanced from 10%, below it Dispersed (spec 5.1);
        the effective number of cities reads 1 for one state and n for n equal ones."""
        def pattern(urbans):
            states = []
            for u in urbans:
                s = dict(self._three[0])
                s["te_dg_urban"] = float(u) * 100_000
                states.append(s)
            eng = self.country(states)
            eng.call("te_demog_country_census")
            return eng.vars["te_dg_urban_label"], eng.vars["te_dg_primacy"], eng.vars["te_dg_n_cities"]
        for urbans, want in (((4, 6), 0.0), ((3, 3, 4), 0.0), ((3, 3, 3, 1), 1.0), ((1, 1, 1, 1), 1.0),
                             ((1,) * 8, 2.0), ((1,) * 10, 2.0), ((1,) * 11, 3.0), ((7,), 0.0)):
            self.assertEqual(pattern(urbans)[0], want, urbans)
        self.assertAlmostEqual(pattern((5,))[2], 1.0)
        self.assertAlmostEqual(pattern((2,) * 8)[2], 8.0)
        self.assertAlmostEqual(pattern((1, 3))[1], 0.75)
        self.assertEqual(pattern((0, 0))[0], 3.0, "no urban people: nothing to concentrate")

    def test_small_states_survive_the_engines_fixed_point(self):
        """Values are cut to five decimals after every operation. Ten states of 3,000 urban people are
        10 equal cities, 2,000 and 1,000 are 1.8 (3000^2 / (2000^2 + 1000^2)); in millions the squares
        were 9 and 4 and 1 units and the answers 90 and 0."""
        def pattern(urbans):
            states = []
            for u in urbans:
                s = dict(self._three[0])
                s["te_dg_urban"] = float(u)
                states.append(s)
            eng = self.country(states, ai=True, truncate=True)
            eng.call("te_demog_country_census")
            return eng.vars["te_dg_n_cities"], eng.vars["te_dg_primacy"]
        self.assertEqual(pattern((3000,) * 10)[0], 10.0)
        self.assertEqual(pattern((2000, 1000))[0], 1.8)
        self.assertAlmostEqual(pattern((2000, 1000))[1], 2 / 3, places=4)
        self.assertAlmostEqual(pattern((50_000_000, 30_000_000))[0], 80 ** 2 / (50 ** 2 + 30 ** 2), places=4)

    def test_the_lists(self):
        """te_dg_states: by the people the last census counted (the figure each row shows, not the
        live population), at most 40; te_dg_cities: the three largest cities by the global rank, a
        state with no rank or no census left out, a rank of 1 the largest. Each list is cleared
        only once it exists."""
        states = self.three()
        # the largest at its census, though fewer live today; no rank
        states.append(dict(states[0], te_dg_people=7e6, state_population=1e5))
        del states[3]["state_city_size_rank"]
        small = [dict(states[2], te_dg_people=float(1000 + i), state_population=float(1000 + i)) for i in range(45)]
        split = {"state_population": 9e6, "state_city_size_rank": 1.0}        # ranked, no walk or census yet
        eng = self.country(states + small + [split])
        self.assertNotIn("te_dg_cities", eng.lists, "the first census clears no list")
        eng.call("te_demog_country_census")
        listed = eng.lists["te_dg_states"]
        self.assertEqual(len(listed), 40)
        self.assertEqual([s["te_dg_people"] for s in listed[:4]], [7e6, 4e6, 1.5e6, 6e5])
        self.assertEqual([s["te_dg_people"] for s in listed[4:7]], [1044.0, 1043.0, 1042.0])
        cities = eng.lists["te_dg_cities"]
        self.assertEqual([s["state_city_size_rank"] for s in cities], [3.0, 12.0, 40.0])
        eng.call("te_demog_country_census")   # a refill, not an append
        self.assertEqual((len(eng.lists["te_dg_states"]), len(eng.lists["te_dg_cities"])), (40, 3))

    def test_projection_is_the_players(self):
        for ai in (False, True):
            states = self.three()
            eng = self.country(states, ai=ai)
            eng.call("te_demog_country_census")
            self.assertEqual("te_dg_pjf0" in eng.vars, not ai, f"ai={ai}")
            self.assertEqual("te_dg_pjm17" in eng.vars, not ai)
        v = eng.vars
        eng = self.country(self.three())
        eng.call("te_demog_country_census")
        v = eng.vars
        now = sum(v[f"te_dg_cb{sex}{b}"] for sex in "fm" for b in range(18))
        ahead = sum(v[f"te_dg_pj{sex}{b}"] for sex in "fm" for b in range(18))
        self.assertTrue(0.7 * now < ahead < 2.5 * now, (now, ahead))
        for sex in "fm":   # four five-year steps up: the children of now are the 20-year-olds of then
            ratio = v[f"te_dg_pj{sex}4"] / v[f"te_dg_cb{sex}0"]
            self.assertTrue(0.2 < ratio < 1.0, (sex, ratio))

    def test_projection_runs_on_the_models_own_tfr(self):
        """Phase 2 step 4: a state's te_dg_tfr is the realized figure (the model's x (1 + bz)) while the projection's
        mortality is the model's own (te_dg_m_*, unscaled), so the outline takes te_dg_tfr_model, weighted by
        women aged 15-49 as te_dg_tfr is. A state with none (an old save's, before its next step) gives its
        te_dg_tfr. The country's shown TFR stays the realized one."""
        states = self.three()
        for s, bz in zip(states, (0.3, -0.2)):
            s["te_dg_tfr_model"] = s["te_dg_tfr"]
            s["te_dg_tfr"] *= 1 + bz
        states[2].pop("te_dg_tfr_model", None)
        eng = self.country(states)
        eng.call("te_demog_country_census")
        w = sum(s["te_dg_w1549"] for s in states)
        shown = sum(s["te_dg_tfr"] * s["te_dg_w1549"] for s in states) / w
        model = sum(s.get("te_dg_tfr_model", s["te_dg_tfr"]) * s["te_dg_w1549"] for s in states) / w
        self.assertGreater(abs(shown - model), 0.1, "the case must tell the two apart")
        self.assertAlmostEqual(eng.vars["te_dg_tfr"], shown, places=6)
        self.assertAlmostEqual(eng.locals["te_dg_tfr"], model, places=6)

    def test_projection_reads_the_womens_work_share_from_the_states(self):
        """The outline splits the work multiplier as te_demog_prepare does, on the people-weighted averages of the
        states' multipliers and of their women's share of the workers (te_demog_women_worker_share: each state's own
        count; 2026-10-25, when it stopped reading the owner's law's share, which split it even under Full)."""
        states = self.three()
        pm = sum(s["te_dg_people"] for s in states)
        work = sum(s["te_dg_m_work"] * s["te_dg_people"] for s in states) / pm
        for shares in ((0.1, 0.2, 0.3), (0.45, 0.05, 0.4)):
            counted = [dict(s, te_dg_fws_wk=f) for s, f in zip(states, shares)]
            fws = sum(f * s["te_dg_people"] for s, f in zip(states, shares)) / pm
            eng = self.country(counted)
            eng.call("te_demog_country_census")
            self.assertAlmostEqual(eng.locals["te_dg_fws"], fws, places=6)
            self.assertAlmostEqual(eng.locals["te_dg_m_work_f"], work * fws * 2, places=6)
            self.assertAlmostEqual(eng.locals["te_dg_m_work_m"], (1 - fws) * work * 2, places=6)
        body = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertNotIn("capital", body)

    def test_a_country_with_no_census_stays_pending(self):
        states = [{"te_dg_people": 5e5, "state_population": 5e5}]
        eng = self.country(states)
        eng.call("te_demog_country_census")
        self.assertFalse("te_dg_census_year" in eng.vars)
        self.assertFalse("te_dg_median" in eng.vars)
        self.assertFalse("te_dg_pjf0" in eng.vars)

    def test_the_country_keeps_last_years_figures_after_a_step_only(self):
        names = ("median", "young_share", "working_share", "old_share", "dependency", "sex_balance", "cbr", "cdr",
                 "w1549", "tfr", "e0", "e65", "imr", "net_migration", "urban_share", "primacy", "n_cities",
                 "urban_label")
        eng = self.country(self.three())
        eng.call("te_demog_country_census")
        self.assertEqual((eng.vars["te_dg_trend_ok"], eng.vars["te_dg_stepped"]), (0.0, 1.0),
                         "the first census: nothing before it")
        self.assertFalse(any(f"te_dg_prev_{n}" in eng.vars for n in names))
        first = {n: eng.vars[f"te_dg_{n}"] for n in names}
        eng.call("te_demog_country_census")   # the same states a year later, say
        self.assertEqual((eng.vars["te_dg_trend_ok"], eng.vars["te_dg_stepped"]), (1.0, 1.0))
        self.assertEqual({n: eng.vars[f"te_dg_prev_{n}"] for n in names}, first)

    def test_the_country_census_after_seeds_has_no_arrows(self):
        """1836: the game-start census and the first yearly one both read seeded states (0 births), and
        the first stepped year's still has the seed's behind it."""
        seeds = self.three()
        for s in seeds:
            s["te_dg_births"] = s["te_dg_deaths"] = s["te_dg_net_migration"] = 0.0
            s["te_dg_stepped"] = 0.0
        eng = self.country(seeds)
        flags = []
        for rounds, born in ((2, False), (1, True), (1, True), (1, True)):
            for _ in range(rounds):
                if born:   # the states stepped: births, and the flag a step writes (te_demog_set_trend)
                    for s in seeds:
                        s["te_dg_births"], s["te_dg_deaths"] = s["te_dg_people"] * 0.038, s["te_dg_people"] * 0.031
                        s["te_dg_stepped"] = 1.0
                eng.call("te_demog_country_census")
                flags.append((eng.vars["te_dg_trend_ok"], eng.vars["te_dg_stepped"]))
                if not born:   # no births: infant mortality is the states' by people, not 0
                    people = sum(s["te_dg_people"] for s in seeds)
                    self.assertAlmostEqual(eng.vars["te_dg_imr"],
                                           sum(s["te_dg_imr"] * s["te_dg_people"] for s in seeds) / people, places=6)
                    self.assertGreater(eng.vars["te_dg_imr"], 50)
        self.assertEqual(flags, [(0.0, 0.0), (0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)])
        self.assertAlmostEqual(eng.vars["te_dg_cbr"], 38.0, places=9)
        self.assertAlmostEqual(eng.vars["te_dg_prev_cbr"], 38.0, places=9)

    def test_imr_after_seeds_is_weighted_by_people(self):
        """A seed writes no births, so the births-weighted infant mortality would read 0: with none
        in the census the states' are weighted by people; with births, by births. CBR and CDR are 0
        while te_dg_stepped is 0, and that is no figure."""
        seeds = self.three()
        for s in seeds:
            s["te_dg_births"] = s["te_dg_deaths"] = s["te_dg_net_migration"] = 0.0
            s["te_dg_stepped"] = 0.0
        eng = self.country(seeds)
        eng.call("te_demog_country_census")
        by_people = sum(s["te_dg_imr"] * s["te_dg_people"] for s in seeds) / sum(s["te_dg_people"] for s in seeds)
        self.assertGreater(by_people, 50)
        self.assertAlmostEqual(eng.vars["te_dg_imr"], by_people, places=6)
        self.assertEqual((eng.vars["te_dg_cbr"], eng.vars["te_dg_cdr"], eng.vars["te_dg_stepped"]), (0.0, 0.0, 0.0))
        for s, rate in zip(seeds, (0.05, 0.03, 0.01)):
            s["te_dg_births"] = s["te_dg_people"] * rate
        eng.call("te_demog_country_census")
        by_births = sum(s["te_dg_imr"] * s["te_dg_births"] for s in seeds) / sum(s["te_dg_births"] for s in seeds)
        self.assertAlmostEqual(eng.vars["te_dg_imr"], by_births, places=6)
        self.assertNotAlmostEqual(by_births, by_people, places=3)

    def test_rates_divide_before_they_multiply(self):
        """A birth rate is births over people times 1,000; the other order forms births x 1,000, which a
        large state's births can carry past the engine's limit."""
        text = _text(EFFECTS)
        for name in ("te_demog_state_figures", "te_demog_country_census"):
            body = _block(text, name)
            for var in ("cbr", "cdr"):
                line = next(l for l in body.splitlines() if f"name = te_dg_{var} " in l)
                self.assertRegex(line, r"divide = \{[^}]*\} multiply = 1000 \}", line)
        line = next(l for l in _block(text, "te_demog_store_figures").splitlines() if "te_dg_sex_balance" in l)
        self.assertRegex(line, r"divide = \{[^}]*\} multiply = 100 \}", line)

    def test_game_start_ends_with_the_census(self):
        stubs = {"te_demog_walks": "", "te_demog_seed": "set_variable = { name = te_dg_year value = 1836 }",
                 "te_demog_country_census": "set_variable = { name = census_ran value = 1 }"}
        for rule in (True, False):
            states = [{}, {}]
            eng = _CountryEngine(states=states, fixtures={}, triggers={"te_demog_cohorts_run": rule}, effects=stubs)
            eng.call("te_demog_country_game_start")
            self.assertEqual(eng.vars.get("census_ran"), 1.0 if rule else None, rule)
            self.assertEqual(["te_dg_year" in s for s in states], [rule, rule])


BANKING = ROOT / "common" / "scripted_effects" / "banking_cycle_effects.txt"
CIVIL_WAR_ON_ACTIONS = ROOT / "common" / "on_actions" / "te_civil_war_on_actions.txt"
APPLIED = {"te_inh_apply_concentration_modifiers": "set_variable = { name = applied value = var:te_inh_concentration }"}


class TestWealth(unittest.TestCase):
    """Wealth Concentration per state (Task 11; spec 4.2): each state's score drifts to its own
    target and takes the shocks; the country's figure, te_inh_concentration, is the states'
    average weighted by where property is held, and drives #822's two modifiers."""

    # -- the wiring ---------------------------------------------------------------------------------

    def test_national_figure_is_derived(self):
        """One effect at the yearly pulse: the national figure, then the census reads it."""
        yearly = _block(_text(EFFECTS), "te_demog_country_yearly")
        self.assertLess(yearly.index("te_demog_wc_national = yes"), yearly.index("te_demog_country_census = yes"))
        self.assertNotIn("te_demog_wc_national", _block(_text(INH_EFFECTS), "te_inh_yearly_update"))
        self.assertIn("te_demog_wc_national = yes", _block(_text(INH_EFFECTS), "te_inh_shift_concentration"))
        self.assertIn("te_demog_wc_national = yes", _block(_text(INH_EFFECTS), "inh_repair_after_civil_war"))

    def test_shifts_reach_every_state(self):
        self.assertIn("every_scope_state", _block(_text(INH_EFFECTS), "te_inh_shift_concentration"))

    def test_one_refresh_site_for_the_modifiers(self):
        text = _text(WEALTH_EFFECTS)
        self.assertEqual(text.count("te_inh_apply_concentration_modifiers = yes"), 1)

    def test_drift_three_percent(self):
        self.assertIn("multiply = 0.03", _block(_text(WEALTH_EFFECTS), "te_demog_wc_state_yearly"))

    def test_wealth_runs_whatever_the_rule(self):
        """The pulse refreshes Wealth Concentration ungated; only the census it calls after checks the rule."""
        body = _block(_text(EFFECTS), "te_demog_state_yearly")
        self.assertNotIn("te_demog_cohorts_run", body)
        self.assertLess(body.index("te_demog_wc_state_yearly = yes"), body.index("te_demog_state_census = yes"))
        self.assertIn("te_demog_cohorts_run = yes", _block(_text(EFFECTS), "te_demog_state_census"))

    def test_the_war_shock_and_the_war_dead_run_whatever_the_rule(self):
        yearly = _block(_text(EFFECTS), "te_demog_country_yearly")
        self.assertLess(yearly.index("te_demog_wc_war_shock = yes"), yearly.index("te_demog_cohorts_run = yes"))
        reset = yearly.index("set_variable = { name = te_dg_war_year value = 0 }")
        self.assertLess(yearly.index("te_demog_wc_war_shock = yes"), reset)
        self.assertNotIn("te_demog_cohorts_run", yearly[:reset], "the reset runs whatever the rule")

    def test_822s_drift_only_without_a_scored_state(self):
        body = _block(_text(INH_EFFECTS), "te_inh_yearly_update")
        guard = body.index("NOT = { any_scope_state = { has_variable = te_dg_wc } }")
        self.assertLess(guard, body.index("te_inh_concentration_next"))
        self.assertLess(guard, body.index("te_inh_apply_concentration_modifiers = yes"))
        for call in ("te_inh_tidy_amendments = yes", "te_inh_count_duty_years = yes"):
            self.assertRegex(body, rf"(?m)^\t{call}$", "every country, scored or not")

    def test_822s_target_follows_the_states(self):
        text = _text(INH_VALUES)
        body = _block(text, "te_inh_concentration_target")
        self.assertIn("value = te_inh_law_amendment_target", body)
        self.assertIn("value = var:te_dg_wc_target", body)
        laws = _block(text, "te_inh_law_amendment_target")
        self.assertIn("add = modifier:country_wealth_concentration_inheritance_add", laws)
        self.assertNotIn("te_inh_title_continuity", laws, "the pin is the states' and the display's, not the law's")

    def test_the_shown_target_follows_a_law_change_at_once(self):
        """Review on #830: the stored national target is summed at the yearly pulse, but a law or a tax
        on wealth moves every state's target alike, so the shown target moves by the change since
        then; continuity of title still pins it at the score."""
        cases = (
            # law now, tax now, pinned -> shown
            (75.0, -5.0, False, 60.0),   # nothing changed since the refresh
            (85.0, -5.0, False, 70.0),   # the law term rose by 10
            (75.0, 0.0, False, 65.0),    # Graduated Taxation repealed: +5
            (100.0, 0.0, False, 90.0),
            (40.0, -5.0, False, 25.0),
            (5.0, -10.0, False, 0.0),    # clamped at 0
            (85.0, -5.0, True, 33.0),    # continuity of title: the score
        )
        for law, tax, pinned, shown in cases:
            eng = _CountryEngine(fixtures={"te_inh_law_amendment_target": law, "te_demog_wc_tax_term": tax})
            eng.values.update(_raw_blocks([INH_VALUES]))
            eng.fixtures["te_inh_law_amendment_target"] = law
            eng.vars.update(te_dg_wc_target=60.0, te_dg_wc_t_law=25.0, te_dg_wc_t_tax=-5.0, te_inh_concentration=33.0)
            if pinned:
                eng.vars["te_inh_title_continuity"] = 1.0
            eng.run(_parse_script("set_variable = { name = shown value = te_inh_concentration_target }"))
            self.assertAlmostEqual(eng.vars["shown"], shown, msg=(law, tax, pinned))

    def test_game_start_seeds_every_state_then_the_national_figure(self):
        body = _block(_text(INH_EFFECTS), "te_inh_game_start")
        self.assertLess(body.index("te_demog_walks = yes"), body.index("te_demog_wc_seed_state = yes"))
        self.assertLess(body.index("te_demog_wc_seed_state = yes"), body.index("te_demog_wc_national = yes"))
        self.assertNotIn("name = te_inh_concentration", body)

    def test_every_change_to_a_score_ends_clamped(self):
        for path in (WEALTH_EFFECTS, INH_EFFECTS):
            for name, body in _raw_blocks([path]).items():
                ops = re.findall(r"(change|clamp)_variable = \{\s*name = te_dg_wc\b", body)
                if ops:
                    self.assertEqual(ops[-1], "clamp", name)

    def test_devastation_is_a_share(self):
        """A state's devastation reads as a 0-1 share: a fully devastated state (1) loses 10 points a year."""
        body = _block(_text(WEALTH_EFFECTS), "te_demog_wc_state_yearly")
        self.assertIn("add = { value = devastation multiply = -10 }", body)

    def test_the_shocks_are_wired(self):
        on_actions = _text(DEMOG_ON_ACTIONS)
        self.assertIn("te_demog_lost_war", _block(on_actions, "on_lost_war"))
        lost = _block(on_actions, "te_demog_lost_war")
        self.assertIn("te_demog_wc_shock = { AMOUNT = -5 }", lost)
        self.assertNotIn("te_demog_cohorts_run", lost)
        # owner's ruling on #830: only a loser a war goal was enforced against
        self.assertLess(lost.index("exists = scope:victim_of_wargoal"), lost.index("te_demog_wc_shock"))
        banking = _text(BANKING)
        # A reach turned away while the country's contagion event is open books that event's crash for the new
        # wave (banking_contagion_reach, 2026-10-17): no second crash, so no second shock.
        reach = _block(banking, "banking_contagion_reach")
        self.assertIn("banking_crisis_wave_crashed", reach)
        self.assertNotIn("te_demog_wc_shock", reach)
        crashes = banking.replace(reach, "")
        sites = re.findall(r"set_variable = \{ name = banking_crisis_wave_crashed value = 1 \}", crashes)
        self.assertEqual(len(sites), 2)
        # The two crashes: an origin's (the wave's start) and a contagion roll's. Each marks it, then shocks.
        for name in ("banking_crisis_wave_init", "banking_contagion_crash_check"):
            body = _block(banking, name)
            self.assertLess(body.index("set_variable = { name = banking_crisis_wave_crashed value = 1 }"),
                            body.index("te_demog_wc_shock = { AMOUNT = -5 }"), name)

    def test_a_won_left_revolution_reads_the_resolved_sides(self):
        """The repair runs between te_civil_war_resolve_sides and te_civil_war_clear (which removes
        te_cw_origin; a loyalist winner can carry the rebels' te_cw_origin), so it reads
        te_cw_rebels_won, and the national figure follows the shock."""
        civil = _block(_text(WEALTH_EFFECTS), "te_demog_wc_civil_war_won")
        self.assertIn("var:te_cw_rebels_won = 1", civil)
        self.assertIn("AMOUNT = -20", civil)
        self.assertNotIn("te_cw_origin", civil)
        repair = _block(_text(INH_EFFECTS), "inh_repair_after_civil_war")
        self.assertLess(repair.index("te_demog_wc_civil_war_won = yes"), repair.index("te_demog_wc_national = yes"))
        self.assertIn("inh_repair_after_civil_war = yes", _block(_text(CIVIL_WAR_ON_ACTIONS), "te_civil_war_on_won"))

    # -- a state's score and target, through the interpreter --------------------------------------------

    def state_year(self, state, owner=None, devastation=0.0, target=60.0):
        eng = _CountryEngine(states=[state], fixtures={"te_demog_wc_target": target, "devastation": devastation})
        eng.vars.update(owner or {})
        eng._in(state, _parse_script("te_demog_wc_state_yearly = yes"))
        return state

    def test_a_state_closes_three_percent_of_the_gap(self):
        self.assertAlmostEqual(self.state_year({"te_dg_wc": 40.0})["te_dg_wc"], 40.6)
        self.assertAlmostEqual(self.state_year({"te_dg_wc": 80.0}, target=20.0)["te_dg_wc"], 78.2)
        self.assertEqual(self.state_year({"te_dg_wc": 40.0})["te_dg_wc_target"], 60.0)

    def test_devastation_destroys_local_capital(self):
        self.assertAlmostEqual(self.state_year({"te_dg_wc": 40.0}, devastation=0.5)["te_dg_wc"], 35.6)
        self.assertEqual(self.state_year({"te_dg_wc": 3.0}, devastation=1.0, target=0.0)["te_dg_wc"], 0.0)

    def test_a_state_without_a_score_starts_at_its_owners_figure(self):
        self.assertEqual(self.state_year({}, owner={"te_inh_concentration": 72.0})["te_dg_wc"], 72.0)
        self.assertEqual(self.state_year({})["te_dg_wc"], 60.0, "an owner with no figure: the state's target")

    def test_the_seed_starts_a_state_at_its_target(self):
        state = {}
        eng = _CountryEngine(states=[state], fixtures={"te_demog_wc_target": 55.0})
        eng._in(state, _parse_script("te_demog_wc_seed_state = yes"))
        self.assertEqual((state["te_dg_wc"], state["te_dg_wc_target"]), (55.0, 55.0))

    def target(self, state, owner=None, law=80.0, land=6.0, tax=-5.0, econ=0.0, public=0.0, slavery=0.0):
        eng = _CountryEngine(states=[state], fixtures={"te_inh_law_amendment_target": law,
                                                       "te_demog_wc_land_term": land, "te_demog_wc_tax_term": tax,
                                                       "te_demog_wc_econ_term": econ,
                                                       "te_demog_wc_public_term": public,
                                                       "te_demog_wc_slavery_term": slavery})
        eng.vars.update(owner or {})
        return eng.value_in(state, "te_demog_wc_target")

    def test_the_target_sums_its_terms(self):
        state = {"te_dg_lv_priv": 30.0, "te_dg_lv_self": 10.0, "te_dg_lv_ctry": 0.0, "te_dg_gini": 0.5}
        # law 80, land 6, ownership (30/40 - 0.65) x 40 = 4, inequality (0.5 - 0.40) x 40 = 4, taxes -5
        self.assertAlmostEqual(self.target(state), 89.0)
        self.assertAlmostEqual(self.target(state, econ=-10.0), 79.0, msg="the economic laws add in")
        self.assertAlmostEqual(self.target(state, public=5.0), 94.0, msg="the public goods laws add in")
        self.assertAlmostEqual(self.target(state, public=-10.0), 79.0, msg="and take off")
        self.assertEqual(self.target(state, public=20.0), 100.0, msg="to the 100 cap")
        self.assertAlmostEqual(self.target(state, slavery=10.0), 99.0, msg="the slavery law adds in")
        self.assertEqual(self.target(state, law=100.0, land=15.0), 100.0)
        self.assertEqual(self.target(state, law=0.0, land=-20.0), 0.0)

    def test_the_inequality_term_is_four_points_a_tenth_above_040(self):
        # owner, 2026-10-10: on the shown Gini, +40 x (Gini - 0.40), at most +15 (from 0.775); the shown
        # figure is at least 0.30, so at least -4 (= 28 x (computed - 0.143), close to 30 x (computed - 0.15))
        for gini, term in ((0.4, 0.0), (0.5, 4.0), (0.6, 8.0), (0.775, 15.0), (0.9, 15.0), (0.3, -4.0)):
            state = {"te_dg_lv_priv": 0.4, "te_dg_lv_self": 0.0, "te_dg_lv_ctry": 0.0, "te_dg_gini": gini}
            self.assertAlmostEqual(self.target(state, law=50.0, land=0.0, tax=0.0), 50 + term, msg=str(gini))

    def test_the_ownership_and_inequality_terms_are_capped(self):
        private = {"te_dg_lv_priv": 50.0, "te_dg_lv_self": 0.0, "te_dg_lv_ctry": 0.0, "te_dg_gini": 0.9}
        # centred on 1836's measured 0.65 private: all private is +14, the most the term can add
        self.assertAlmostEqual(self.target(private, law=50.0, land=0.0, tax=0.0), 50 + 14 + 15)
        two_thirds = {"te_dg_lv_priv": 65.0, "te_dg_lv_self": 30.0, "te_dg_lv_ctry": 5.0, "te_dg_gini": 0.4}
        self.assertAlmostEqual(self.target(two_thirds, law=50.0, land=0.0, tax=0.0), 50.0, msg="1836's mix: no term")
        state_owned = {"te_dg_lv_priv": 0.0, "te_dg_lv_self": 5.0, "te_dg_lv_ctry": 45.0, "te_dg_gini": 0.3}
        # the shown Gini is at least 0.30, so the inequality term is at least -4 (owner: a shallow bottom)
        self.assertAlmostEqual(self.target(state_owned, law=50.0, land=0.0, tax=0.0), 50 - 20 - 4)
        no_capital = {"te_dg_lv_priv": 0.4, "te_dg_lv_self": 0.0, "te_dg_lv_ctry": 0.0, "te_dg_gini": 0.4}
        self.assertAlmostEqual(self.target(no_capital, law=50.0, land=0.0, tax=0.0), 50.0, msg="no capital: no term")

    def test_continuity_of_title_pins_the_target_at_the_score(self):
        state = {"te_dg_lv_priv": 30.0, "te_dg_lv_self": 10.0, "te_dg_lv_ctry": 0.0, "te_dg_gini": 0.5,
                 "te_dg_wc": 33.0}
        self.assertEqual(self.target(state, owner={"te_inh_title_continuity": 1.0}), 33.0)
        self.assertAlmostEqual(self.target(state), 89.0)

    # -- the national figure, through the interpreter ------------------------------------------------

    @staticmethod
    def scored(wc, target, own=0.0, coop=0.0, ctry=0.0, bur=0.0, pop=1e6, gini=0.4, priv=10.0,
               bands=None, layout=P.GINI_LAYOUT):
        """A scored state; its walk stored the bands it has people in, under `layout` (None: a state
        from a save before the layout marker, which has no te_dg_gini_layout)."""
        state = {"te_dg_wc": float(wc), "te_dg_wc_target": float(target), "te_dg_lv_own": float(own),
                 "te_dg_lv_self": float(coop), "te_dg_lv_ctry": float(ctry), "te_dg_lv_priv": float(priv),
                 "te_dg_bureaucrats": float(bur), "te_dg_walk_pop": float(pop), "te_dg_gini": float(gini)}
        bands = {1: (900, 1350), 5: (90, 270), 10: (10, 150)} if bands is None else bands
        for k, (n, y) in bands.items():
            state[f"te_dg_gn{k}"], state[f"te_dg_gy{k}"] = float(n), float(y)
        if layout is not None:
            state["te_dg_gini_layout"] = float(layout)
        return state

    @staticmethod
    def national(states, **country):
        eng = _CountryEngine(states=states, effects=APPLIED,
                             fixtures={"te_inh_law_amendment_target": 75.0, "te_demog_wc_land_term": 4.0,
                                       "te_demog_wc_tax_term": -5.0, "te_demog_wc_econ_term": 5.0,
                                       "te_demog_wc_public_term": -5.0, "te_demog_wc_slavery_term": 10.0})
        eng.vars.update(country)
        eng.call("te_demog_wc_national")
        return eng.vars

    def test_the_national_figure_weighs_states_by_property(self):
        a = self.scored(80, 70, own=30, ctry=40, bur=900, gini=0.5, priv=400,
                        bands={k: (1e5 / k + k, (1e5 / k + k) * 3 * k) for k in range(1, P.GINI_BANDS + 1)})
        b = self.scored(40, 50, coop=10, ctry=60, bur=100, gini=0.3, priv=200,
                        bands={k: (7e4 / k + 2 * k, (7e4 / k + 2 * k) * (2.5 * k + 1)) for k in range(1, P.GINI_BANDS + 1)})
        c = {"te_dg_walk_pop": 9e9, "te_dg_lv_own": 9e9}   # no score: left out
        v = self.national([a, b, c])
        # 100 state-owned levels where 1,000 bureaucrats work: a holds 900 of them, b 100
        wa, wb = 30 + 0.9 * 100 * 0.1, 10 + 0.1 * 100 * 0.1
        mean = lambda x, y: (x * wa + y * wb) / (wa + wb)   # noqa: E731
        self.assertAlmostEqual(v["te_inh_concentration"], mean(80, 40))
        # each state's target is rewritten from the law and taxes as they stand (the fixture's
        # 70 and 50 are stale), and the national target is their weighted mean
        self.assertNotEqual((a["te_dg_wc_target"], b["te_dg_wc_target"]), (70.0, 50.0))
        self.assertAlmostEqual(v["te_dg_wc_target"], mean(a["te_dg_wc_target"], b["te_dg_wc_target"]))
        self.assertEqual(v["applied"], v["te_inh_concentration"], "the modifiers read this year's figure")
        self.assertAlmostEqual(v["te_dg_wc_t_law"], 25.0)
        self.assertAlmostEqual(v["te_dg_wc_t_land"], 4.0)
        own_a, own_b = (400 / 440 - 0.65) * 40, (200 / 270 - 0.65) * 40   # +10.36 and +3.63: inside the caps
        self.assertTrue(-20 < own_b < own_a < 20)
        self.assertAlmostEqual(v["te_dg_wc_t_own"], mean(own_a, own_b))
        self.assertAlmostEqual(v["te_dg_wc_t_ineq"], mean(4, -4))
        self.assertAlmostEqual(v["te_dg_wc_t_tax"], -5.0)
        self.assertAlmostEqual(v["te_dg_wc_t_econ"], 5.0)
        self.assertAlmostEqual(v["te_dg_wc_t_public"], -5.0)
        self.assertAlmostEqual(v["te_dg_wc_t_slavery"], 10.0)
        # with no state clamped, the eight bars add up to the target above them
        bars = sum(v[f"te_dg_wc_t_{t}"] for t in ("law", "land", "own", "ineq", "tax", "econ", "public", "slavery"))
        self.assertAlmostEqual(v["te_dg_wc_target"], 50 + bars)
        self.assertIs(v["te_dg_wc_top"], a)
        self.assertIs(v["te_dg_wc_bottom"], b)
        bands = [(a.get(f"te_dg_gn{k}", 0) + b.get(f"te_dg_gn{k}", 0), a.get(f"te_dg_gy{k}", 0) + b.get(f"te_dg_gy{k}", 0))
                 for k in range(1, P.GINI_BANDS + 1)]
        expected = demographics_model.shown_gini(demographics_model.grouped_gini(bands))
        self.assertAlmostEqual(v["te_dg_gini"], expected, places=9, msg="the Gini of the summed bands")

    def test_a_state_from_an_old_save_adds_no_bands(self):
        # Review Focus 1: before its own pulse a state has only the old strata sums
        old = self.scored(60, 55, bands={}, layout=None)
        old.update(te_dg_n_lo=900.0, te_dg_y_lo=1350.0)
        new = self.scored(40, 50, bands={2: (900e3, 12.0), 9: (1e4, 2.0)})
        v = self.national([old, new])
        want = demographics_model.shown_gini(demographics_model.grouped_gini([(900e3, 12.0), (1e4, 2.0)]))
        self.assertAlmostEqual(v["te_dg_gini"], want, places=9)

    def test_a_state_with_the_old_fourteen_bands_adds_none(self):
        """A save from before the layout marker (2026-10-10): 14 bands, the last one 61 or more, income
        capped at 60 and summed in other units. Until its own pulse such a state adds nothing (its band 14
        is not the new band 14, and it has no 15th), so no sum mixes the two layouts."""
        fourteen = {k: (1e4 * k, 1e4 * k * 9.0 * k) for k in range(1, 15)}
        old = self.scored(60, 55, bands=fourteen, layout=None)
        new = self.scored(40, 50, bands={2: (900e3, 12.0), 30: (1e3, 9e3)})
        v = self.national([old, new])
        want = demographics_model.shown_gini(demographics_model.grouped_gini([(900e3, 12.0), (1e3, 9e3)]))
        self.assertAlmostEqual(v["te_dg_gini"], want, places=9)
        # a marker of another layout is skipped the same way
        self.assertNotIn("te_dg_gini", self.national([self.scored(60, 55, bands=fourteen, layout=1)]))

    def test_a_country_whose_states_have_no_bands_keeps_its_gini(self):
        # an old save, before any of its states' pulses: no band sums, so no new figure (not 0.00)
        old = self.scored(60, 55, bands={}, layout=None)
        v = self.national([old], te_dg_gini=0.42)
        self.assertEqual(v["te_dg_gini"], 0.42)
        old14 = self.scored(60, 55, bands={k: (10.0, 20.0 * k) for k in range(1, 15)}, layout=None)
        self.assertEqual(self.national([old14], te_dg_gini=0.42)["te_dg_gini"], 0.42)

    def test_scored_states_without_bands_give_a_target_but_no_gini(self):
        """The national figure writes the Gini only from states that have wealth bands, but the
        target (the panel's old gate) from any scored state. A country whose scored states have
        no bands yet (a save from before the bands, a state scored before its first walk) thus has
        the one and not the other, and a panel that reads the Gini under the target's gate
        shows 0.00 (a missing variable reads 0). The panel gates the Gini on te_dg_gini itself."""
        old = self.scored(60, 55, bands={}, layout=None)
        v = self.national([old])
        self.assertIn("te_dg_wc_target", v, "the target is written: the old gate is open")
        self.assertIn("te_inh_concentration", v)
        self.assertNotIn("te_dg_gini", v, "no state has bands, so there is no Gini to show")
        # once one state has bands the same call writes the Gini beside the target
        new = self.scored(40, 50, bands={2: (900e3, 12.0), 9: (1e4, 2.0)})
        self.assertIn("te_dg_gini", self.national([old, new]))

    def test_the_bureaucrat_share_multiplies_before_it_divides(self):
        """A state with a tiny share of the bureaucrats keeps its precision: values are i64 x 1e-5."""
        body = _block(_text(WEALTH_EFFECTS), "te_demog_wc_national")
        weight = body[body.index("value = var:te_dg_bureaucrats"):]
        self.assertLess(weight.index("multiply = local_var:te_dg_wc_ctry"),
                        weight.index("divide = { value = local_var:te_dg_wc_bur min = 1 }"))

    def test_without_property_the_states_weigh_by_people(self):
        v = self.national([self.scored(80, 70, pop=2e6), self.scored(40, 50, pop=1e6, ctry=30)])
        self.assertAlmostEqual(v["te_inh_concentration"], (80 * 2 + 40) / 3, msg="state-owned levels, no bureaucrats")
        v = self.national([self.scored(80, 70, pop=0), self.scored(40, 50, pop=0)])
        self.assertAlmostEqual(v["te_inh_concentration"], 60.0, msg="no people either: one each")

    def test_a_country_with_no_scored_state_keeps_its_own_figure(self):
        v = self.national([{"te_dg_walk_pop": 1e5}], te_inh_concentration=63.0)
        self.assertEqual((v["te_inh_concentration"], v["applied"]), (63.0, 63.0))
        for name in ("te_dg_wc_target", "te_dg_gini", "te_dg_wc_top", "te_dg_wc_t_law"):
            self.assertNotIn(name, v)
        self.assertNotIn("applied", self.national([]), "no figure: no modifiers")

    def test_a_shock_moves_every_score_then_the_national_figure(self):
        a, b = self.scored(80, 70, own=10), self.scored(3, 50, own=10)
        eng = _CountryEngine(states=[a, b, {}], effects=APPLIED,
                             fixtures={"te_inh_law_amendment_target": 75.0, "te_demog_wc_land_term": 4.0,
                                       "te_demog_wc_tax_term": -5.0, "te_demog_wc_econ_term": 5.0,
                                       "te_demog_wc_public_term": 0.0, "te_demog_wc_slavery_term": 0.0})
        eng.run(_parse_script("te_demog_wc_shock = { AMOUNT = -5 }"))
        self.assertEqual((a["te_dg_wc"], b["te_dg_wc"]), (75.0, 0.0))
        self.assertAlmostEqual(eng.vars["te_inh_concentration"], 37.5)

    def test_a_shock_reaches_a_country_with_no_scored_state(self):
        """An old save before its states' first pulse, or a landless country: the shock lands on its own
        figure, clamped, and the modifiers follow; with no figure yet it starts from #822's target."""
        for before, amount, after in ((63.0, -5, 58.0), (3.0, -5, 0.0), (98.0, 5, 100.0), (None, -20, 30.0)):
            states = [{"te_dg_walk_pop": 1e5}]
            eng = _CountryEngine(states=states, effects=APPLIED, fixtures={"te_inh_concentration_target": 50.0})
            if before is not None:
                eng.vars["te_inh_concentration"] = before
            eng.run(_parse_script(f"te_demog_wc_shock = {{ AMOUNT = {amount} }}"))
            self.assertEqual((eng.vars["te_inh_concentration"], eng.vars["applied"]), (after, after), before)
            self.assertNotIn("te_dg_wc", states[0])

    # -- the war shock at the yearly pulse -------------------------------------------------------------

    def war_year(self, states, at_war, dead, shocks=None, rule=False):
        eng = _CountryEngine(states=states, fixtures={"total_population": 1e6},
                             triggers={"te_demog_cohorts_run": rule, "is_at_war": at_war},
                             effects={"te_demog_wc_national": "", "te_demog_country_census": ""})
        eng.vars["te_dg_war_year"] = float(dead)
        if shocks is not None:
            eng.vars["te_dg_war_shock"] = float(shocks)
        eng.call("te_demog_country_yearly")
        return eng.vars

    def test_a_year_of_heavy_war_dead_lowers_every_score(self):
        states = [{"te_dg_wc": 50.0}, {"te_dg_wc": 0.5}, {}]
        v = self.war_year(states, True, 2500)   # 0.25% of a million
        self.assertEqual([s.get("te_dg_wc") for s in states], [49.0, 0.0, None])
        self.assertEqual(v["te_dg_war_shock"], 1.0)
        self.assertEqual(v["te_dg_war_year"], 0.0, "the census is off: the dead are cleared after the shock")

    def test_light_war_dead_or_ten_shocks_already_do_nothing(self):
        for dead, shocks in ((1500, None), (2500, 10)):
            states = [{"te_dg_wc": 50.0}]
            v = self.war_year(states, True, dead, shocks)
            self.assertEqual(states[0]["te_dg_wc"], 50.0, (dead, shocks))
            self.assertEqual(v["te_dg_war_shock"], 0.0 if shocks is None else 10.0)

    def test_peace_ends_the_count(self):
        states = [{"te_dg_wc": 50.0}]
        v = self.war_year(states, False, 9000, shocks=4)
        self.assertNotIn("te_dg_war_shock", v)
        self.assertEqual(states[0]["te_dg_wc"], 50.0)


INH_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_inheritance_modifiers.txt"
INH_EVENTS = ROOT / "events" / "inheritance_events.txt"
STATE_WC_MODIFIERS = ("inh_concentrated_property", "inh_dispersed_property", "inh_land_hunger")
STATE_WC_MULTS = ("te_inh_wc_high_mult", "te_inh_wc_low_mult", "te_inh_land_hunger_mult")


SGUIS = ROOT / "common" / "scripted_guis" / "te_demog_sguis.txt"
MISC_LOC = ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml"


class TestGiniGate(unittest.TestCase):
    """The panel reads the country's Gini (te_dg_gini) only under a gate on that variable. It used
    to read it under te_demog_wealth_ready_sgui, which asks for te_dg_wc_target, written under a
    wider condition (any scored state, not any state with wealth bands): with the target and no
    Gini, a .gui read of the missing variable showed 0.00, which reads as perfect equality."""

    def test_the_gini_gate_asks_for_the_gini(self):
        gate = _block(_text(SGUIS), "te_demog_gini_ready_sgui")
        self.assertRegex(gate, r"scope = country\b")
        shown = re.search(r"is_shown = \{([^{}]*)\}", gate)
        self.assertIsNotNone(shown)
        self.assertEqual(shown.group(1).split(), ["has_variable", "=", "te_dg_gini"])
        # the Wealth Concentration gate is unchanged: it still asks for the target
        wealth = re.search(r"is_shown = \{([^{}]*)\}", _block(_text(SGUIS), "te_demog_wealth_ready_sgui"))
        self.assertEqual(wealth.group(1).split(), ["has_variable", "=", "te_dg_wc_target"])

    def test_every_country_gini_the_gui_shows_is_picked_by_the_gini_gate(self):
        gui, loc = _text(DEMOG_GUI), _text(MISC_LOC)
        # the loc keys that read the country's Gini
        keys = re.findall(r'^ (\w+):0 "[^"\n]*GetPlayer\.MakeScope\.Var\(\'te_dg_gini\'\)', loc, re.M)
        self.assertEqual(sorted(keys), ["te_demog_gini_value", "te_demog_ov_gini_value"])
        gate = r"GetScriptedGui\('te_demog_gini_ready_sgui'\)\.IsShown\( GuiScope\.SetRoot\( GetPlayer\.MakeScope \)\.End \)"
        for key in keys:
            uses = [m.start() for m in re.finditer(rf"['\"]{key}['\"]", gui)]
            self.assertTrue(uses, f"{key} is not used")
            for at in uses:
                line = gui[gui.rfind("\n", 0, at) + 1:gui.index("\n", at)]
                self.assertRegex(line, rf"SelectLocalization\( {gate}, '{key}', '\w+' \)", f"{key} is shown bare: {line.strip()}")

    def test_the_gini_cell_has_a_pending_text(self):
        gui, loc = _text(DEMOG_GUI), _text(MISC_LOC)
        pending = re.search(r"GetScriptedGui\('te_demog_gini_ready_sgui'\)[^\n]*'te_demog_gini_value', '(\w+)'", gui)
        self.assertIsNotNone(pending)
        self.assertRegex(loc, rf"(?m)^ {pending.group(1)}:0 \"", "the pending key has a loc entry")


class _StateModifierEngine(_Engine):
    """A state's modifiers as {name: multiplier}, for the Wealth Concentration state modifiers."""

    def __init__(self, **kwargs):
        super().__init__(fixtures={}, **kwargs)
        self.effects.update(_raw_blocks([INH_EFFECTS]))
        self.values.update(_raw_blocks([INH_VALUES]))
        self.modifiers = {}

    def _test(self, key, op, arg):
        if key == "has_modifier":
            return arg in self.modifiers
        return super()._test(key, op, arg)

    def run(self, items):
        rest = []
        for item in items:
            key, _, arg = item
            if key == "remove_modifier":
                self._flush(rest)
                rest = []
                assert arg in self.modifiers, f"remove of absent modifier {arg}"
                del self.modifiers[arg]
            elif key == "add_modifier":
                self._flush(rest)
                rest = []
                name = _find(arg, "name")
                assert name not in self.modifiers, f"{name} added twice"
                self.modifiers[name] = self.value(_find(arg, "multiplier"))
            else:
                rest.append(item)
        self._flush(rest)

    def _flush(self, items):
        if items:
            super().run(items)


def _modifier_fields(path, name):
    """{field: value} of a static modifier, its icon left out."""
    body = _raw_blocks([path])[name]
    return {k: float(v) for k, v in re.findall(r"^\s*(\w+) = (-?[\d.]+)\s*$", body, re.M)}


class TestWealthSizes(unittest.TestCase):
    """The 2026-10-22 effects design's Wealth Concentration sizes: concentration grows faster and crashes more often,
    dispersal grows slower and steadier (demographics_effects.SIZES)."""

    NAMES = ("inh_great_fortunes", "inh_dispersed_wealth") + STATE_WC_MODIFIERS

    def test_each_modifier_is_the_spec(self):
        for name in self.NAMES:
            self.assertEqual(_modifier_fields(INH_MODIFIERS, name), DE.SIZES[name], name)

    def test_bubble_pressure_only_on_the_national_pair(self):
        """A country field on a state modifier would count once per state; the national pair is read by
        banking_cycle_advance_variables only while a country's cycle runs."""
        mods = _raw_blocks([INH_MODIFIERS])
        for name, body in mods.items():
            has = "country_bubble_pressure_monthly_add" in body
            self.assertEqual(has, name in ("inh_great_fortunes", "inh_dispersed_wealth"), name)

    def test_the_national_pair_follows_the_curve(self):
        for score in (80, 100, 65, 50, 20, 0, 35):
            eng = _StateModifierEngine()
            eng.vars.update(te_inh_concentration=float(score))
            eng.call("te_inh_apply_concentration_modifiers")
            for name, want in (("inh_great_fortunes", DE.wc_high(score)), ("inh_dispersed_wealth", DE.wc_low(score))):
                if want > 0.01:
                    self.assertAlmostEqual(eng.modifiers.get(name), want, places=4, msg=(name, score))
                else:
                    self.assertNotIn(name, eng.modifiers, (name, score))

    def test_dispersed_side_has_no_investment_line(self):
        self.assertFalse([f for f in _modifier_fields(INH_MODIFIERS, "inh_dispersed_property") if "investment" in f])

    def test_the_law_tooltips_describe_the_new_effects(self):
        """The inheritance laws' custom tooltips (extra_laws.txt) restate what the score does: the dispersed side has no
        Farmers' and Shopkeepers' investment line and weakens the Capitalists too, Concentrated Property's radicals
        moved to Land Hunger, and both sides move bubble pressure (review of #1101)."""
        loc = {}
        for line in (ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml").read_text(
                encoding="utf-8-sig").splitlines():
            m = re.match(r'\s+(LAW_\w+_INHERITANCE_TT):\d*\s*"(.*)"\s*$', line)
            if m:
                loc[m.group(1)] = m.group(2)
        lowering = ("LAW_EQUAL_INHERITANCE_INHERITANCE_TT", "LAW_NON_INHERITABLE_USAGE_RIGHTS_INHERITANCE_TT",
                    "LAW_STATE_UNIVERSAL_HEIR_INHERITANCE_TT")
        for key in lowering:
            self.assertNotIn("Farmers and Shopkeepers invest", loc[key], key)
            self.assertIn("Capitalists", loc[key], key)
            self.assertIn("bubble", loc[key], key)
        primo = loc["LAW_PRIMOGENITURE_INHERITANCE_TT"]
        self.assertNotIn("radicals gather", primo)
        self.assertIn("bubble", primo)
        self.assertIn("clout", primo)


class TestWealthStateModifiers(unittest.TestCase):
    """Spec 4.2's split (phase 2): two country modifiers from the national figure, three state
    modifiers from each state's own score, each with one refresh site."""

    def refresh(self, wc, agr, before=()):
        eng = _StateModifierEngine()
        eng.vars.update(te_dg_wc=float(wc), te_dg_agr_share=float(agr))
        eng.modifiers.update({name: 0.5 for name in before})
        eng.call("te_inh_refresh_wc_state_effects")
        return eng

    def test_the_state_modifiers_follow_the_states_own_score(self):
        cases = (
            # score, agrarian share -> concentrated, dispersed, land hunger (2026-10-22 effects design: full at 80
            # and 20, the high side straight to 5/3 at 100, the low side half the slope past 20 to 4/3 at 0)
            (80, 0.5, 1.0, None, 0.5),
            (100, 1.0, 5 / 3, None, 5 / 3),
            (100, 0.0, 5 / 3, None, None),   # a city: no land hunger
            (50, 0.8, None, None, None),
            (50.2, 0.8, None, None, None),  # under 0.01: not applied
            (20, 0.8, None, 1.0, None),
            (10, 0.8, None, 7 / 6, None),
            (0, 0.3, None, 4 / 3, None),
        )
        for wc, agr, high, low, hunger in cases:
            eng = self.refresh(wc, agr, before=STATE_WC_MODIFIERS)
            got = tuple(eng.modifiers.get(n) for n in STATE_WC_MODIFIERS)
            for g, want in zip(got, (high, low, hunger)):
                if want is None:
                    self.assertIsNone(g, (wc, agr))
                else:
                    self.assertAlmostEqual(g, want, places=4, msg=(wc, agr))
            if high is not None:
                self.assertAlmostEqual(high, DE.wc_high(wc), places=4)
            if low is not None:
                self.assertAlmostEqual(low, DE.wc_low(wc), places=4)
            for name in STATE_WC_MULTS:
                self.assertIn(name, eng.vars, "the multipliers stay set, even at 0")

    def test_a_state_with_no_score_yet_loses_stale_modifiers(self):
        eng = _StateModifierEngine()
        eng.modifiers.update({name: 0.5 for name in STATE_WC_MODIFIERS})
        eng.call("te_inh_refresh_wc_state_effects")
        self.assertEqual(eng.modifiers, {})

    def test_the_refresh_reads_this_years_score_whatever_the_rule(self):
        body = _block(_text(EFFECTS), "te_demog_state_yearly")
        refresh = body.index("te_inh_refresh_wc_state_effects = yes")
        self.assertLess(body.index("te_demog_wc_state_yearly = yes"), refresh)
        self.assertLess(refresh, body.index("te_demog_state_census = yes"))
        self.assertNotIn("te_demog_cohorts_run", body, "owner's ruling: every rule setting")

    def test_one_refresh_site_per_modifier(self):
        files = [p for d in ("common", "events") for p in (ROOT / d).rglob("*.txt")]
        adds = {}
        calls = []
        for path in files:
            for name, body in _raw_blocks([path]).items():
                for m in re.finditer(r"add_modifier = \{\s*name = (inh_\w+)", body):
                    adds.setdefault(m.group(1), set()).add(name)
                calls += [name] * body.count("te_inh_refresh_wc_state_effects = yes")
        for name in STATE_WC_MODIFIERS:
            self.assertEqual(adds.get(name), {"te_inh_refresh_wc_state_effects"}, name)
        for name in ("inh_great_fortunes", "inh_dispersed_wealth"):
            self.assertEqual(adds.get(name), {"te_inh_apply_concentration_modifiers"}, name)
        self.assertEqual(sorted(calls), ["inheritance_events.8", "te_demog_state_yearly"])

    def test_the_modifiers_split_by_scope(self):
        mods = _raw_blocks([INH_MODIFIERS])
        for name, prefixes in (("inh_great_fortunes", ("country_",)), ("inh_dispersed_wealth", ("country_",)),
                               *((n, ("state_",)) for n in STATE_WC_MODIFIERS)):
            fields = re.findall(r"^\s*(\w+) = ", mods[name], re.M)
            fields = [f for f in fields if f != "icon"]
            self.assertTrue(fields, name)
            for f in fields:
                self.assertTrue(f.startswith(prefixes), f"{name}: {f}")

    def test_the_multipliers_are_never_removed(self):
        """modifier_multiplier_var_audit's rule: a modifier's multiplier is re-read after it is applied."""
        for path in [p for d in ("common", "events") for p in (ROOT / d).rglob("*.txt")]:
            text = _text(path)
            for name in STATE_WC_MULTS:
                self.assertNotRegex(text, rf"remove_variable = (\{{ name = )?{name}\b", path.name)

    def test_game_start_refreshes_every_state_from_its_own_scope(self):
        events = _raw_blocks([INH_EVENTS])
        start = events["inheritance_events.1"]
        self.assertLess(start.index("te_inh_game_start = yes"), start.index("id = inheritance_events.8"))
        self.assertIn("every_scope_state", start)
        state = events["inheritance_events.8"]
        self.assertIn("type = state_event", state)
        self.assertIn("hidden = yes", state)
        self.assertIn("te_inh_refresh_wc_state_effects = yes", state)


EXTRA_LAWS = ROOT / "common" / "laws" / "extra_laws.txt"
DEMOG_GUI = ROOT / "gui" / "te_demographics_widgets.gui"


class _LawEngine(_Engine):
    """A country holding `laws`, for the values that read has_law."""

    def __init__(self, laws, **kwargs):
        super().__init__(**kwargs)
        self.values.update(_raw_blocks([INH_VALUES]))
        self.laws = set(laws)

    def _test(self, key, op, arg):
        if key == "has_law":
            assert arg.startswith("law_type:"), arg
            return arg[9:] in self.laws
        return super()._test(key, op, arg)


class TestInheritanceBalance(unittest.TestCase):
    """The 2026-10-09 balance pass (owner's table): the economic laws term, the re-centred
    ownership term, the amendments, the laws and The Great Estates for Sale."""

    @staticmethod
    def _wc_lines(laws, amendments=()):
        """The Wealth Concentration lines `laws` and `amendments` carry in the game files (on the laws since
        2026-10-17, the inheritance amendments since 2026-10-21), as the modifier: reads the interpreter takes."""
        lines = DM.load_carriers(types=P.WC_LAW_TYPES)
        totals = DM.totals(lines, laws=laws, amendments=amendments, types=P.WC_LAW_TYPES)
        return {f"modifier:{t}": v for t, v in totals.items()}

    def test_the_economic_laws_term(self):
        cases = (
            ((), 0),
            (("law_traditionalism", "law_guilds_chartered_monopolies"), 5),     # the 1836 baseline
            (("law_laissez_faire", "law_freedom_of_contract"), 15),             # the Gilded Age
            (("law_extraction_economy", "law_guilds_chartered_monopolies"), 10),
            (("law_interventionism", "law_trust_busting"), -10),
            (("law_command_economy", "law_command_cooperative_economy"), 0),    # counted in ownership
            (("law_interventionism", "law_regulated_utilities"), -10),
        )
        for laws, want in cases:
            eng = _LawEngine(laws, fixtures=self._wc_lines(laws))
            self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_wc_econ_term")), want, laws)

    def test_the_tax_and_land_terms_read_the_laws_lines(self):
        """Graduated Taxation's -5 and the land laws' terms x the agrarian share, each the law's own line, a variant at
        its parent's (2026-10-17)."""
        for laws, want in (((), 0.0), (("law_graduated_taxation",), -5.0), (("law_proportional_taxation",), 0.0)):
            eng = _LawEngine(laws, fixtures=self._wc_lines(laws), triggers={"te_tax_code_full": False})
            self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_wc_tax_term")), want, laws)
        for law, want in (("law_serfdom", 7.5), ("law_manorialism", 7.5), ("law_tenant_farmers", 2.5),
                          ("law_expanded_latifundias", 2.5), ("law_commercialized_agriculture", 0.0),
                          ("law_homesteading", -5.0), ("law_collectivized_agriculture", -10.0)):
            eng = _LawEngine((law,), fixtures=self._wc_lines({law}))
            eng.vars["te_dg_agr_share"] = 0.5
            self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_wc_land_term")), want, msg=law)
        for name in ("te_demog_wc_land_term", "te_demog_wc_tax_term", "te_demog_wc_econ_term"):
            self.assertNotIn("has_law", _block(_text(VALUES), name), name)

    def test_the_economic_laws_term_is_wired_like_the_tax_term(self):
        self.assertIn("add = owner.te_demog_wc_econ_term", _block(_text(VALUES), "te_demog_wc_target"))
        self.assertIn("set_variable = { name = te_dg_wc_t_econ value = te_demog_wc_econ_term }",
                      _block(_text(WEALTH_EFFECTS), "te_demog_wc_national"))
        self.assertIn("ScriptValue('te_demog_wc_econ_term')", _text(DEMOG_GUI))

    def test_the_shown_target_follows_an_economic_law_at_once(self):
        eng = _CountryEngine(fixtures={"te_inh_law_amendment_target": 75.0, "te_demog_wc_tax_term": -5.0,
                                       "te_demog_wc_econ_term": 15.0})
        eng.values.update(_raw_blocks([INH_VALUES]))
        eng.vars.update(te_dg_wc_target=60.0, te_dg_wc_t_law=25.0, te_dg_wc_t_tax=-5.0, te_dg_wc_t_econ=5.0,
                        te_inh_concentration=33.0)
        eng.run(_parse_script("set_variable = { name = shown value = te_inh_concentration_target }"))
        self.assertAlmostEqual(eng.vars["shown"], 70.0, msg="Laissez-Faire enacted since the refresh: +10")

    def test_the_public_goods_term_reads_the_laws_lines(self):
        """Owner, 2026-10-21: whether health care, schooling and ideas are provided or sold. Private provision and
        strict IP raise the target and public provision lowers it; the none and church laws and the other IP laws carry
        nothing, so 1836's defaults leave the start where it was."""
        cases = (
            ((), 0),
            (("law_no_health_system", "law_no_schools", "law_no_ip_protection"), 0),
            (("law_charitable_health_system", "law_religious_schools", "law_state_intellectual_property"), 0),
            (("law_private_health_insurance", "law_private_schools", "law_strict_ip_protection"), 20),   # the most
            (("law_private_health_insurance", "law_terakoya", "law_traditional_ip_protection"), 15),     # a variant at its parent's
            (("law_public_health_insurance", "law_public_schools", "law_creative_commons"), -10),         # the least
            (("law_public_health_insurance", "law_private_schools", "law_open_source_innovation"), 0),
        )
        for laws, want in cases:
            eng = _LawEngine(laws, fixtures=self._wc_lines(laws))
            self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_wc_public_term")), want, laws)
        self.assertNotIn("has_law", _block(_text(VALUES), "te_demog_wc_public_term"))

    def test_the_public_goods_term_is_wired_like_the_economic_term(self):
        self.assertIn("add = owner.te_demog_wc_public_term", _block(_text(VALUES), "te_demog_wc_target"))
        self.assertIn("set_variable = { name = te_dg_wc_t_public value = te_demog_wc_public_term }",
                      _block(_text(WEALTH_EFFECTS), "te_demog_wc_national"))
        for scope in ("GetPlayer", "State.GetOwner"):
            self.assertIn(f"{scope}.MakeScope.ScriptValue('te_demog_wc_public_term')", _text(DEMOG_GUI), scope)

    def test_the_shown_target_follows_a_public_goods_law_at_once(self):
        eng = _CountryEngine(fixtures={"te_inh_law_amendment_target": 75.0, "te_demog_wc_tax_term": -5.0,
                                       "te_demog_wc_public_term": 10.0})
        eng.values.update(_raw_blocks([INH_VALUES]))
        eng.vars.update(te_dg_wc_target=60.0, te_dg_wc_t_law=25.0, te_dg_wc_t_tax=-5.0, te_dg_wc_t_public=5.0,
                        te_inh_concentration=33.0)
        eng.run(_parse_script("set_variable = { name = shown value = te_inh_concentration_target }"))
        self.assertAlmostEqual(eng.vars["shown"], 65.0, msg="Strict IP enacted over Traditional since the refresh: +5")
        del eng.vars["te_dg_wc_t_public"]
        eng.run(_parse_script("set_variable = { name = shown value = te_inh_concentration_target }"))
        self.assertAlmostEqual(eng.vars["shown"], 60.0, msg="a save from before the term: nothing to compare with")

    def test_the_slavery_term_reads_the_laws_lines(self):
        """Owner, 2026-10-21: property in people. Colonial, Legacy and Debt Slavery +10; Slave Trade +5, since an open
        supply keeps slaves cheap and ownership wide; Slavery Banned, the usual law, carries nothing, and the term counts
        the law in force, not the enslaved."""
        for law, want in (("law_slavery_banned", 0), ("law_colonial_slavery", 10), ("law_legacy_slavery", 10),
                          ("law_debt_slavery", 10), ("law_slave_trade", 5)):
            eng = _LawEngine((law,), fixtures=self._wc_lines({law}))
            self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_wc_slavery_term")), want, law)
        self.assertNotIn("has_law", _block(_text(VALUES), "te_demog_wc_slavery_term"))

    def test_the_slavery_term_is_wired_like_the_public_goods_term(self):
        self.assertIn("add = owner.te_demog_wc_slavery_term", _block(_text(VALUES), "te_demog_wc_target"))
        self.assertIn("set_variable = { name = te_dg_wc_t_slavery value = te_demog_wc_slavery_term }",
                      _block(_text(WEALTH_EFFECTS), "te_demog_wc_national"))
        for scope in ("GetPlayer", "State.GetOwner"):
            self.assertIn(f"{scope}.MakeScope.ScriptValue('te_demog_wc_slavery_term')", _text(DEMOG_GUI), scope)

    def test_the_shown_target_follows_the_slavery_law_at_once(self):
        eng = _CountryEngine(fixtures={"te_inh_law_amendment_target": 75.0, "te_demog_wc_tax_term": -5.0,
                                       "te_demog_wc_slavery_term": 10.0})
        eng.values.update(_raw_blocks([INH_VALUES]))
        eng.vars.update(te_dg_wc_target=60.0, te_dg_wc_t_law=25.0, te_dg_wc_t_tax=-5.0, te_dg_wc_t_slavery=0.0,
                        te_inh_concentration=33.0)
        eng.run(_parse_script("set_variable = { name = shown value = te_inh_concentration_target }"))
        self.assertAlmostEqual(eng.vars["shown"], 70.0, msg="Debt Slavery enacted since the refresh: +10")
        del eng.vars["te_dg_wc_t_slavery"]
        eng.run(_parse_script("set_variable = { name = shown value = te_inh_concentration_target }"))
        self.assertAlmostEqual(eng.vars["shown"], 60.0, msg="a save from before the term: nothing to compare with")

    def test_the_ownership_term_is_centred_on_1836s_measured_share(self):
        body = _block(_text(VALUES), "te_demog_wc_ownership_term")
        self.assertIn("subtract = 0.65", body)

    def test_the_law_and_amendments_move_the_law_target(self):
        """#822's targets, read from the lines the inheritance laws and amendments carry since 2026-10-21 (has_law and
        has_amendment lookups until then), so the law's and the amendment's tooltips say what they do. The same
        figures as before: 50 plus the lines, held to 0-100."""
        cases = (
            ((), (), 50),                                                            # no inheritance law
            (("law_partible",), (), 50),
            (("law_primogeniture",), (), 80),
            (("law_free_testation",), (), 60),
            (("law_equal_inheritance",), (), 25),
            (("law_state_universal_heir",), (), 0),
            (("law_non_inheritable_usage_rights",), (), 0),
            (("law_primogeniture",), ("amendment_estate_duties",), 50),
            (("law_primogeniture",), ("amendment_birthright_endowment",), 60),
            (("law_free_testation",), ("amendment_perpetual_trusts",), 90),
            (("law_free_testation",), ("amendment_perpetual_trusts", "amendment_estate_duties"), 60),
            (("law_partible",), ("amendment_undivided_farm_succession",), 60),
            (("law_equal_inheritance",), ("amendment_undivided_farm_succession",), 35),
            (("law_equal_inheritance",), ("amendment_estate_duties",), 0),           # -5, held at 0
            (("law_equal_inheritance",), ("amendment_estate_duties", "amendment_undivided_farm_succession"), 5),
        )
        for laws, amendments, want in cases:
            eng = _LawEngine(laws, fixtures=self._wc_lines(laws, amendments))
            self.assertEqual(eng.value(eng._tree(eng.values, "te_inh_law_amendment_target")), want, (laws, amendments))
        body = _block(_text(INH_VALUES), "te_inh_law_amendment_target")
        for lookup in ("has_law", "has_amendment"):
            self.assertNotIn(lookup, body)
        endowment = _raw_blocks([ROOT / "common" / "amendments" / "extra_amendments.txt"])["amendment_birthright_endowment"]
        self.assertIn("country_bureaucracy_investment_cost_factor_mult = 0.05", endowment, "the stakes' cost")

    def test_no_inheritance_law_repeats_what_the_score_carries(self):
        """Radicals, qualifications and education access come from the state's score
        (inh_concentrated_property); a law carrying them too counts them twice."""
        laws = {name: body for name, body in _raw_blocks([EXTRA_LAWS]).items()
                if "group = lawgroup_inheritance" in body}
        self.assertEqual(len(laws), 6)
        for name, body in laws.items():
            modifier = body[body.index("modifier = {"):]
            for field in ("state_radicals_from_political_movements_mult", "state_pop_qualifications_mult",
                          "state_education_access_add"):
                self.assertNotIn(field, modifier, name)
            self.assertRegex(modifier, r"modifier = \{\s*\w", f"{name}: every law has an effect of its own")

    def test_the_great_estates_for_sale_trade_money_for_levelling(self):
        """Buying the estates for smallholders costs money and levels more; letting the market take
        them earns the duty and levels little (playtest: both used to level by 5)."""
        event = _raw_blocks([INH_EVENTS])["inheritance_events.5"]
        shifts = dict(re.findall(r"name = inheritance_events\.5\.(\w)\s.*?AMOUNT = (-?\d+)", event, re.S))
        self.assertEqual(shifts, {"a": "-10", "b": "-2", "c": "3"})


HISTORY_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_history_effects.txt"
BOM = b"\xef\xbb\xbf"


def _walk(items):
    """Every (key, operator, value) in a parsed script, depth first."""
    for item in items:
        yield item
        if isinstance(item[2], list):
            yield from _walk(item[2])


class TestHistory(unittest.TestCase):
    """Task 12: the yearly history store (te_demog_history_record), modelled on the Cultural
    Hegemony annual store. The interpreter has no containers, so these read the script."""

    @classmethod
    def setUpClass(cls):
        cls.text = _text(HISTORY_EFFECTS) if HISTORY_EFFECTS.exists() else ""

    def block(self, name):
        return _block(self.text, name)

    def test_file_has_one_bom_and_tabs(self):
        raw = HISTORY_EFFECTS.read_bytes()
        self.assertTrue(raw.startswith(BOM))
        self.assertFalse(raw[len(BOM):].startswith(BOM), "a doubled BOM drops the whole file")
        self.assertNotRegex(raw.decode("utf-8-sig"), r"(?m)^ +\S")

    def test_the_census_calls_the_record_for_tracked_countries_only(self):
        body = _block(_text(EFFECTS), "te_demog_country_census")
        calls = [i for i in _walk(_parse_script(body)) if i[0] == "te_demog_history_record"]
        self.assertEqual(len(calls), 1)
        gates = [v for k, _, v in _walk(_parse_script(body))
                 if k == "if" and any(i[0] == "te_demog_history_record" for i in v)]
        self.assertEqual(len(gates), 1)
        self.assertIn(("te_history_country_is_tracked", "=", "yes"), _find(gates[0], "limit"))
        # at the end of the effect, once the figures are written (inside the seeded branch)
        self.assertLess(body.index("te_demog_project = yes"), body.index("te_demog_history_record = yes"))
        self.assertGreater(body.index("te_demog_history_record = yes"), body.rindex("te_demog_set_trend = yes"))

    def census(self, tracked, states):
        stub = {"te_demog_history_record": "set_variable = { name = hist_median value = var:te_dg_median }"}
        eng = _CountryEngine(states=states, fixtures={"year": 1900.0},
                             triggers={"is_ai": True, "te_demog_cohorts_run": True,
                                       "te_history_country_is_tracked": tracked}, effects=stub)
        eng.call("te_demog_country_census")
        return eng.vars

    def test_the_record_runs_after_the_figures_are_written(self):
        states = [TestCountry.state(4_000_000, 1_600_000, 22, 0.55, rank=1),
                  TestCountry.state(1_500_000, 300_000, 14, 0.3, rank=2)]
        v = self.census(True, [dict(s) for s in states])
        self.assertGreater(v["hist_median"], 15)
        self.assertEqual(v["hist_median"], v["te_dg_median"])
        self.assertNotIn("hist_median", self.census(False, [dict(s) for s in states]))
        pending = [{"te_dg_people": 5e5, "state_population": 5e5}]   # no state seeded: no census, no sample
        self.assertNotIn("hist_median", self.census(True, pending))

    def test_one_sample_a_year(self):
        """The census can run twice in a year (game start, the first yearly pulse): the year is checked before a
        container is created, and set only once the sample is stored."""
        body = self.block("te_demog_history_record")
        self.assertLess(body.index("te_dg_hist_year"), body.index("create_container"))
        guard = body[:body.index("create_container")]
        self.assertIn("var:te_dg_hist_year = te_demog_year", guard)
        self.assertIn("NOT = { has_variable = te_dg_hist_year }", guard)

    def test_a_revolutions_winner_starts_a_list_in_the_year_it_wins(self):
        """The winner inherits te_dg_hist_year but not the list (best practices, container rule 4):
        a country with no list creates a container whatever its year says, and the refill reads the
        list only once it exists. The interpreter has no containers or lists, so this pins the text."""
        body = self.block("te_demog_history_record")
        guard = _find(_find(_parse_script(body), "hidden_effect"), "if")
        either = _find(_find(guard, "limit"), "OR")
        self.assertIn(("NOT", "=", [("has_variable_list", "=", "te_dg_hist")]), either)
        self.assertEqual(len(either), 3)
        refills = [v for k, _, v in _walk(_parse_script(body))
                   if k == "if" and any(i[0] == "every_in_list" for i in v)]
        self.assertEqual(len(refills), 1)
        self.assertEqual(_find(refills[0], "limit"), [("has_variable_list", "=", "te_dg_hist")])
        self.assertEqual(body.count("every_in_list"), 1)
        self.assertEqual(body.count("create_container"), 1)
        self.assertRegex(body, r"set_variable = \{ name = te_dg_hist_year value = te_demog_year \}")
        self.assertLess(body.index("add_to_variable_list"),
                        body.index("set_variable = { name = te_dg_hist_year value = te_demog_year }"))
        self.assertIn("limit = { exists = scope:te_dg_hist_new }", body)

    def test_the_sample_is_a_country_owned_container_keyed_by_year(self):
        body = self.block("te_demog_history_record")
        self.assertIn("parent = scope:te_dg_hist_owner", body)
        self.assertIn("save_scope_as = te_dg_hist_owner", body)
        self.assertRegex(body, r"set_variable = \{ name = te_hist_i value = te_demog_year \}")
        self.assertRegex(body, r"add_to_variable_list = \{ name = te_dg_hist target = scope:te_dg_hist_new \}")
        self.assertTrue(body.lstrip().startswith("hidden_effect"), "hidden: a store, not a tooltip")

    def test_this_years_container_is_refilled_every_run(self):
        """The yearly pulse's run overwrites the game-start sample's values. The game-start sample may
        lack the Gini and Wealth Concentration: te_demog_wc_national runs on the yearly pulse and from
        te_inh_game_start, and the two game-start events run in either order."""
        body = self.block("te_demog_history_record")
        self.assertRegex(body, r"every_in_list = \{\s+variable = te_dg_hist\s+limit = \{ var:te_hist_i = te_demog_year \}")
        self.assertGreater(body.index("every_in_list"), body.index("te_dg_hist_year value"))
        copies = dict(re.findall(r"te_demog_history_copy = \{ FROM = (\w+) TO = (\w+) \}", body))
        self.assertEqual(copies, {"te_dg_median": "te_dg_h_median", "te_dg_tfr": "te_dg_h_tfr",
                                  "te_dg_e0": "te_dg_h_e0", "te_dg_gini": "te_dg_h_gini",
                                  "te_inh_concentration": "te_dg_h_wc",
                                  # issue #1029: the rates, from a stepped census only
                                  "te_dg_cbr": "te_dg_h_cbr", "te_dg_cdr": "te_dg_h_cdr",
                                  "te_dg_mig_rate": "te_dg_h_mig"})
        rates = body[body.index("FROM = te_dg_cbr") - 400:body.index("FROM = te_dg_cbr")]
        self.assertIn("var:te_dg_stepped > 0", rates, "a seed's births and deaths are 0, so a seed's rates aren't kept")

    def test_each_read_is_guarded_by_has_variable(self):
        body = self.block("te_demog_history_copy")
        self.assertRegex(body, r"limit = \{ scope:te_dg_hist_owner = \{ has_variable = \$FROM\$ \} \}")
        self.assertIn("value = scope:te_dg_hist_owner.var:$FROM$", body)
        self.assertIn("name = $TO$", body)

    def test_the_store_holds_100_and_each_eviction_sorts_again(self):
        prune = self.block("te_demog_history_prune")
        self.assertRegex(prune, r"any_in_list = \{ variable = te_dg_hist count >= 101 has_tag = te_dg_hist_sample \}")
        self.assertIn("cap 100", prune)
        self.assertIn("order_by = te_history_sample_order", prune)
        self.assertLess(prune.index("remove_list_variable"), prune.index("destroy_container = yes"))
        self.assertLess(prune.index("destroy_container = yes"), prune.index("te_demog_history_sort = yes"))
        self.assertIn("fills the hole", re.sub(r"\n#\s*", " ", self.text))   # the eviction comment (CH's)
        self.assertIn("te_demog_history_prune = yes", self.block("te_demog_history_record"))

    def test_the_sort_builds_the_copy_before_clearing_the_list(self):
        sort = self.block("te_demog_history_sort")
        self.assertEqual(sort.count("max = 100"), 2)
        self.assertRegex(sort, r"any_in_list = \{ variable = te_dg_hist_tmp count >= 100 has_tag = te_dg_hist_sample \}")
        self.assertEqual(sort.count("check_range_bounds = no"), 2)
        self.assertLess(sort.index("add_to_variable_list = { name = te_dg_hist_tmp"),
                        sort.index("clear_variable_list = te_dg_hist\n"))
        self.assertEqual(sort.count("order_by = te_history_sample_order"), 2)
        self.assertGreater(sort.rindex("clear_variable_list = te_dg_hist_tmp"), sort.rindex("add_to_variable_list"))

    def test_the_order_value_is_negated_so_the_oldest_comes_first(self):
        order = _block(_text(ROOT / "common" / "script_values" / "te_history_values.txt"), "te_history_sample_order")
        self.assertRegex(order, r"subtract = var:te_hist_i")

    def test_no_name_is_shared_with_the_other_stores(self):
        """The Cultural Hegemony and monthly stores run in the same pulses: their lists, scratch
        lists, saved scopes and tags must stay theirs."""
        for stale in (r"variable = te_hist\b", r"te_hist_tmp", r"te_hist_sorter", r"te_hist_evicted", r"te_hist_moved",
                      r"te_hist_sample\b", r"ch_model", r">= 241", r">= 240", r"max = 240"):
            self.assertNotRegex(self.text, stale)


# -- the console (te_debug_demog.1, Task 15) -------------------------------------------------------

CONSOLE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"


def _console_blocks():
    """te_debug_demog_effects.txt's effects as _raw_blocks gives them, each debug_log string swapped
    for a token (_parse_script splits on spaces and `=`): (blocks, {token: the string})."""
    strings = {}

    def token(m):
        key = f"LOG{len(strings)}"
        strings[key] = m.group(1)
        return f"debug_log = {key}"

    text = re.sub(r"#[^\n]*", "", re.sub(r'debug_log = "([^"]*)"', token, _text(CONSOLE_EFFECTS)))
    blocks = {}
    for m in re.finditer(r"^([\w.]+) = \{", text, re.M):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        blocks[m.group(1)] = text[m.end():i - 1]
    return blocks, strings


class _ConsoleEngine(_Engine):
    """_Engine plus the console's effects. A debug_log is a no-op that records (its string, the
    variables as they stood); the generated ring lines are one debug_log each, RING_BEFORE and
    RING_AFTER."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        blocks, self.strings = _console_blocks()
        self.effects.update(blocks)
        self.effects["te_demog_debug_log_ring_before"] = "debug_log = RING_BEFORE"
        self.effects["te_demog_debug_log_ring_after"] = "debug_log = RING_AFTER"
        # the step's own once-a-game self-check (issue #1029) reads a global variable the interpreter doesn't know
        self.effects["te_debug_demog_cause_deaths_selfcheck"] = ""
        self.logs = []

    def run(self, items):
        segment = []
        for item in items:
            if item[0] != "debug_log":
                segment.append(item)
                continue
            super().run(segment)
            segment = []
            self.logs.append((self.strings.get(item[2], item[2]), dict(self.vars)))
        super().run(segment)


class TestConsole(unittest.TestCase):
    def test_step_is_its_two_halves(self):
        """Option a logs between te_demog_step_begin and te_demog_step_run, so the step must be exactly
        the two, with the rates and flows in the first half and none of them in the second."""
        text = _text(EFFECTS)
        self.assertEqual(_block(text, "te_demog_step").split(),
                         ["te_demog_step_begin", "=", "yes", "te_demog_step_run", "=", "yes"])
        begin = _block(text, "te_demog_step_begin")
        self.assertLess(begin.index("te_demog_prepare = yes"), begin.index("te_demog_flows = yes"))
        run = _block(text, "te_demog_step_run")
        for name in ("te_demog_prepare", "te_demog_flows"):
            self.assertNotIn(name, run)
        self.assertIn("te_demog_sweep = yes", run)

    def test_the_census_log_hooks_are_gated(self):
        text = _text(EFFECTS)
        for caller, line in (("te_demog_state_yearly", "te_debug_demog_pulse_line"),
                             ("te_demog_country_census", "te_debug_demog_census_line")):
            self.assertRegex(_block(text, caller),
                             rf"if = \{{\s*limit = \{{ te_demog_census_log_on = yes \}}\s*{line} = yes\s*\}}", caller)
        self.assertIn("has_global_variable = te_demog_census_log", _block(_text(TRIGGERS), "te_demog_census_log_on"))

    def test_only_the_console_sets_the_census_log(self):
        setters = [p for p in [*ROOT.glob("common/**/*.txt"), *ROOT.glob("events/*.txt")]
                   if "set_global_variable = te_demog_census_log" in _text(p)]
        self.assertEqual([p.name for p in setters], ["te_debug_demog_events.txt"])

    def test_every_debug_copy_is_removed(self):
        """A line renders when it runs; the te_dg_dbg_ variables only carry its numbers and must not
        stay in the save."""
        blocks, _ = _console_blocks()
        for name, body in blocks.items():
            for var in set(re.findall(r"set_variable = \{ name = (te_dg_dbg_\w+)", body)):
                self.assertIn(f"remove_variable = {var}", body, f"{name}: {var}")

    def test_the_benchmark_leaves_a_census_behind(self):
        """Its timed passes step every census a second time in one year; after the last BENCH line it
        seeds every state with a census again, and nothing follows the seed loop."""
        body = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_benchmark")
        last_pass = body.index("TE_DEMOG_BENCH pass=3 end")
        reseed = body.index('debug_log = "TE_DEMOG_BENCH reseed"')
        self.assertGreater(reseed, last_pass)
        tail = body[reseed + len('debug_log = "TE_DEMOG_BENCH reseed"'):]
        self.assertRegex(tail, r"^\s*every_state = \{\s*limit = \{ te_demog_has_census = yes \}\s*(#[^\n]*\s*)*"
                               r"te_demog_seed_off_pulse = yes\s*\}\s*$")
        self.assertEqual(body.count("TE_DEMOG_BENCH"), 14, "start, three walk and three step begin/end pairs, reseed")

    def test_the_benchmark_times_the_walk_under_its_setting(self):
        """The walk is where Full adds work (the absorbed sums, phase 2 step 4), so option d times three passes of it
        before the step's, and its start line says whether the absorbed sums ran (full=1): run it under Display
        only, switch the rule to Full mid-game, and run it again (owner, 2026-10-11)."""
        body = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_benchmark")
        start = re.search(r'debug_log = "TE_DEMOG_BENCH start[^"]*"', body).group(0)
        self.assertIn("full=[THIS.Var('te_dg_dbg_full').GetValue|0]", start)
        self.assertIn("te_demog_effects_run = yes", body[:body.index(start)])
        for n in (1, 2, 3):
            self.assertLess(body.index(f"TE_DEMOG_BENCH walk={n} begin"), body.index(f"TE_DEMOG_BENCH walk={n} end"))
            self.assertLess(body.index(f"TE_DEMOG_BENCH walk={n} end"), body.index("TE_DEMOG_BENCH pass=1 begin"))
        walk = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_bench_walk")
        self.assertRegex(walk, r"every_state = \{\s*limit = \{ te_demog_has_census = yes \}\s*te_demog_walks = yes\s*\}")

    def test_the_census_line_waits_for_a_million_people(self):
        body = _console_blocks()[0]["te_debug_demog_census_line"]
        self.assertIn("local_var:te_dg_c_people >= 1000000", body)
        self.assertIn("name = te_dg_c_people", _block(_text(EFFECTS), "te_demog_country_census"))

    def test_census_line_carries_the_phase2_fields(self):
        """Phase 2 step 4, Task 9: both variants of the census line carry the census's terms in force and the
        on-top scales (people-weighted over the country's census states), the clamped share and the war flag,
        each read from a te_dg_dbg_ copy the line removes after it."""
        body = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_census_line")
        lines = re.findall(r'debug_log = "(TE_DEMOG_CENSUS:[^"]*)"', body)
        self.assertEqual(len(lines), 2)
        for line in lines:
            for field in ("m_b", "m_d", "bz", "dz", "clamped", "war"):
                self.assertRegex(line, rf"; {field}=\[THIS\.Var\('te_dg_dbg_\w+'\)\.GetValue\|\d\]", field)
        for var in set(re.findall(r"set_variable = \{ name = (te_dg_dbg_\w+)", body)):
            self.assertIn(f"remove_variable = {var}", body, var)
        self.assertIn("te_demog_rate_births_applied", body)
        self.assertIn("te_demog_rate_deaths_applied", body)

    def test_census_line_weights_the_phase2_fields_by_people(self):
        """Final review I4: the census line's terms in force and on-top scales are people-weighted means over the
        country's census states, and clamped is the share of its people in clamped states (the in-game gate's
        instrument). Runs the line's own phase-2 lines, from its first local to the war flag, at country scope."""
        body = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_census_line")
        part = body[body.index("set_local_variable = { name = te_dg_dbg_w value = 0 }"):
                    body.index("set_variable = { name = te_dg_dbg_mig")]
        states = [{"te_dg_year": 1850.0, "te_dg_people": 3e6, "te_dg_mb": -0.4, "te_dg_md": 0.2, "test_census_on": 1.0,
                   "te_dg_bz": 0.1, "te_dg_dz": 0.3, "te_dg_rate_clamped": 1.0},
                  {"te_dg_year": 1850.0, "te_dg_people": 1e6, "te_dg_mb": -0.2, "te_dg_md": -0.1,   # modifier lost
                   "te_dg_bz": 0.5, "te_dg_dz": -0.1, "te_dg_rate_clamped": 0.0},
                  {"te_dg_people": 9e6, "te_dg_mb": 9.0, "te_dg_bz": 9.0}]                          # no census
        eng = _CountryEngine(states=states, fixtures={}, triggers={"is_at_war": True}, effects={"te_test_line": part})
        # the applied terms read has_modifier, which the test engine keeps per engine: a state flag stands in for it
        applied = "value = 0 if = {{ limit = {{ has_variable = test_census_on }} value = var:{} }}"
        eng.values["te_demog_rate_births_applied"] = applied.format("te_dg_mb")
        eng.values["te_demog_rate_deaths_applied"] = applied.format("te_dg_md")
        eng.call("te_test_line")
        v = eng.vars
        self.assertAlmostEqual(v["te_dg_dbg_mb"], -0.4 * 3 / 4)
        self.assertAlmostEqual(v["te_dg_dbg_md"], 0.2 * 3 / 4)
        self.assertAlmostEqual(v["te_dg_dbg_bz"], (0.1 * 3 + 0.5 * 1) / 4)
        self.assertAlmostEqual(v["te_dg_dbg_dz"], (0.3 * 3 - 0.1 * 1) / 4)
        self.assertAlmostEqual(v["te_dg_dbg_cl"], 3 / 4)
        self.assertEqual(v["te_dg_dbg_war"], 1.0)

    def test_option_m_logs_the_shock_terms_click_only(self):
        console = _text(DEBUG_EVENTS)
        call = "te_debug_demog_shock_lines = yes"
        self.assertEqual(console.count(call), 1)
        guard = console[console.rindex("limit = { has_variable = te_dg_dbg_click }", 0, console.index(call)):
                        console.index(call)]
        self.assertIn("remove_variable = te_dg_dbg_click", guard)
        body = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_shock_lines")
        for read in ("modifier:state_mortality_mult", "modifier:state_birth_rate_mult", "value = devastation",
                     "value = turmoil", "value = state_region.pollution_amount", "debug_log_scopes = yes"):
            self.assertIn(read, body)
        for name in ("te_dg_dbg_read_d", "te_dg_dbg_read_b", "te_dg_dbg_dev", "te_dg_dbg_turmoil", "te_dg_dbg_poll"):
            self.assertIn(f"remove_variable = {name}", body)

    def test_option_n_logs_the_rates_click_only(self):
        console = _text(DEBUG_EVENTS)
        call = "te_debug_demog_rate_lines = yes"
        self.assertEqual(console.count(call), 1)
        guard = console[console.rindex("limit = { has_variable = te_dg_dbg_click }", 0, console.index(call)):
                        console.index(call)]
        self.assertIn("remove_variable = te_dg_dbg_click", guard)
        body = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_rate_lines")
        copies = set(re.findall(r"(?:set_variable = \{ name = |TO = )(te_dg_dbg_\w+)", body))
        self.assertTrue(copies)
        for var in copies:
            self.assertIn(f"remove_variable = {var}", body, var)
        line = re.search(r'debug_log = "(TE_DEMOG_RATES:[^"]*)"', body).group(1)
        read = re.findall(r"Var\('(\w+)'\)", line)
        self.assertTrue(read)
        self.assertEqual([v for v in read if not v.startswith("te_dg_dbg_")], [], "raw census variables in the line")
        # what re-derives bz and dz from the line: the events the step's scales compared eb and ed against
        # and the absorbed lines' share M took out (owner amendment A, B): mb = target / bare - 1 - rep_b
        for field, var in (("people", "state_population"), ("eb_target", "te_dg_eb_target"),
                           ("ed_target", "te_dg_ed_target"), ("rep_b", "te_dg_rep_b"), ("rep_d", "te_dg_rep_d"),
                           ("tb_b", "te_dg_tb_b"), ("tb_d", "te_dg_tb_d"), ("os_b", "te_dg_os_b"), ("os_d", "te_dg_os_d"),
                           ("q_b", "te_dg_q_b"), ("q_d", "te_dg_q_d"), ("w", "te_dg_w"),
                           # the trapezoid's start rate for the next window (te_demog_window_events)
                           ("sr_b", "te_dg_sr_b"), ("sr_d", "te_dg_sr_d"),
                           # the Causes of Death section's split (te_demog_on_top_split) and the start's parts
                           ("ed_state", "te_dg_ed_state"), ("ed_sev", "te_dg_ed_sev"), ("sev", "te_dg_sev_share"),
                           ("clamp_d", "te_dg_ed_clamp_d"), ("sp_d", "te_dg_sp_d"), ("ss_d", "te_dg_ss_d")):
            self.assertIn(f"{field}=[THIS.Var('te_dg_dbg_", line, field)
            self.assertIn(var, body, var)
        self.assertIn("te_demog_cohorts_run = yes", console[console.rindex("option = {", 0, console.index(call)):
                                                              console.index(call)])


    def test_option_q_probes_what_an_owner_change_carries(self):
        """Stop B's I1 (owner, 2026-10-12): does on_state_owner_change's ROOT still hold the old state's variables, and
        do they survive the hook? Option q stamps a state alone in its region, gives it to a neighbour, and logs it
        before, in the hook and a day after (te_debug_demog.4)."""
        console = _text(DEBUG_EVENTS)
        call = "te_debug_demog_probe_owner_start = yes"
        self.assertEqual(console.count(call), 1)
        guard = console[console.rindex("limit = { has_variable = te_dg_dbg_click }", 0, console.index(call)):
                        console.index(call)]
        self.assertIn("remove_variable = te_dg_dbg_click", guard)
        start = re.sub(r"#[^\n]*", "", _block(_text(CONSOLE_EFFECTS), "te_debug_demog_probe_owner_start"))
        for piece in ("set_variable = te_probe_owner_var", "set_global_variable = te_probe_owner_on",
                      "set_state_owner = scope:te_probe_owner_to", "trigger_event = { id = te_debug_demog.4 days = 1 }",
                      "TE_DEMOG_PROBE_OWNER before"):
            self.assertIn(piece, start)
        self.assertLess(start.index("TE_DEMOG_PROBE_OWNER before"), start.index("set_state_owner"))
        after = _block(console, "te_debug_demog.4")
        for piece in ("TE_DEMOG_PROBE_OWNER after", "remove_global_variable = te_probe_owner_on",
                      "remove_global_variable = te_probe_owner_to"):
            self.assertIn(piece, after)
        self.assertIn("TE_DEMOG_PROBE_OWNER hook", _block(_text(CONSOLE_EFFECTS), "te_debug_demog_probe_owner_hook"))
        loc = _text(ROOT / "localization" / "english" / "te_events_l_english.yml")
        for key in ("te_debug_demog.1.q", "te_debug_demog.1.q.tt"):
            self.assertRegex(loc, rf"(?m)^ {re.escape(key)}:0 \"", key)

    def test_the_owner_change_hook_logs_only_while_the_probe_runs(self):
        """The hook's probe branch costs nothing in play: it runs only under the global flag option q sets and
        te_debug_demog.4 clears."""
        hook = _block(_text(ROOT / "common" / "on_actions" / "extra_on_actions.txt"), "te_on_state_owner_change")
        call = hook.index("te_debug_demog_probe_owner_hook = yes")
        opener = hook.rindex("if = {", 0, call)
        self.assertIn("limit = { has_global_variable = te_probe_owner_on }", hook[opener:call])
        self.assertEqual(hook.count("te_debug_demog_probe_owner_hook"), 1)

    def test_option_o_probes_a_scaled_script_only_type_on_a_state(self):
        """The late-marriage plan, Task 9 (review C2): Primogeniture's farm births would ride a script-only type on a
        state modifier with a multiplier; the probe adds one at 0.62 and logs the state's sum before and a day after."""
        console = _text(DEBUG_EVENTS)
        call = "te_debug_demog_probe_start = yes"
        self.assertEqual(console.count(call), 1)
        guard = console[console.rindex("limit = { has_variable = te_dg_dbg_click }", 0, console.index(call)):
                        console.index(call)]
        self.assertIn("remove_variable = te_dg_dbg_click", guard)
        self.assertRegex(_block(_text(DEBUG_MODIFIERS), "te_debug_demog_scaled_probe"),
                         r"state_demog_absorbed_birth_rate_mult = 0\.1\b")
        start = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_probe_start")
        self.assertIn("add_modifier = { name = te_debug_demog_scaled_probe multiplier = 0.62 }", start)
        self.assertIn("trigger_event = { id = te_debug_demog.2 days = 7 }", start)
        after = _block(console, "te_debug_demog.2")
        self.assertIn("remove_modifier = te_debug_demog_scaled_probe", after)
        values = _text(ROOT / "common" / "script_values" / "te_debug_demog_values.txt")
        self.assertIn("value = modifier:state_demog_absorbed_birth_rate_mult",
                      _block(values, "te_debug_demog_line_absorbed_b"))
        # its name and description (loc_coverage_audit; organize_loc files the _desc in te_concepts)
        loc = _text(MISC_LOC) + _text(ROOT / "localization" / "english" / "te_concepts_l_english.yml")
        for key in ("te_debug_demog_scaled_probe", "te_debug_demog_scaled_probe_desc"):
            self.assertRegex(loc, rf"(?m)^ {key}:0 \"", key)

FAST_EVENTS = ROOT / "events" / "te_demog_events.txt"
DEBUG_EVENTS = ROOT / "events" / "te_debug_demog_events.txt"
DEBUG_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_debug_demog_modifiers.txt"


class TestFastMode(unittest.TestCase):
    """Fast mode (te_demog_fast_effects.txt; te_debug_demog.1 options h-k, console only): the census on its own
    clock, a step every N months for every state from the global monthly pulse, and the engine's births, deaths,
    research and construction at K = 12 / N times."""

    CLOCK = {"global_var:te_demog_clock": 1900.0, "global_var:te_demog_months_per_step": 3.0,
             "global_var:te_demog_window_months": 3.0}

    def _eng(self, clock_on, fixtures=None, effects=None, triggers=None):
        return _Engine({"year": 1837.0, **(self.CLOCK if clock_on else {}), **(fixtures or {})},
                       triggers={"te_demog_clock_on": clock_on, "te_demog_cohorts_run": True, **(triggers or {})},
                       effects=effects)

    def test_the_census_year_is_the_clocks_while_it_runs(self):
        self.assertEqual(self._eng(False).value("te_demog_year"), 1837.0)
        self.assertEqual(self._eng(True).value("te_demog_year"), 1900.0)

    def test_a_step_covers_a_year_or_the_clocks_window(self):
        self.assertEqual(self._eng(False).value("te_demog_step_months"), 12.0)
        self.assertEqual(self._eng(True, {"global_var:te_demog_window_months": 5.0}).value("te_demog_step_months"), 5.0)

    def test_k_is_twelve_months_over_the_months_a_step(self):
        self.assertEqual(self._eng(False).value("te_demog_fast_k"), 1.0)
        for months, k in ((3, 4.0), (2, 6.0), (1, 12.0), (12, 1.0)):
            eng = self._eng(True, {"global_var:te_demog_months_per_step": float(months)})
            self.assertEqual(eng.value("te_demog_fast_k"), k, months)
            self.assertEqual(eng.value("te_demog_fast_k_minus_1"), k - 1, months)

    def _refresh(self, eng, eb, eb0, ed, ed0):
        # fast mode's refresh alone: the census refresh before it left no census terms (Display only, no M yet)
        eng.locals.update(te_dg_w_eb=eb, te_dg_w_eb0=eb0, te_dg_w_ed=ed, te_dg_w_ed0=ed0, te_dg_w_eb0m=eb0,
                          te_dg_w_ed0m=ed0, te_dg_w_sev=0.0, te_dg_w_sevd=0.0, te_dg_rate_prev_b=0.0,
                          te_dg_rate_prev_d=0.0, te_dg_rate_new_b=0.0, te_dg_rate_new_d=0.0,
                          te_dg_rate_lines_b=0.0, te_dg_rate_lines_d=0.0)
        eng.call("te_demog_fast_refresh_rates")

    # -- phase 2 step 4: fast mode composes with the census's term M -------------------------------

    def _both(self, eng, eb, eb0, ed, ed0):
        """A clock step's two refreshes, as te_demog_state_clock_step runs them."""
        eng.locals.update(te_dg_w_eb=eb, te_dg_w_eb0=eb0, te_dg_w_ed=ed, te_dg_w_ed0=ed0, te_dg_w_ebr=0.0,
                          te_dg_w_edr=0.0, te_dg_w_eb0m=eb0, te_dg_w_ed0m=ed0, te_dg_w_sev=0.0,
                          te_dg_w_sevd=0.0)
        eng.call("te_demog_rates_refresh")
        eng.call("te_demog_fast_refresh_rates")

    def _eng_full(self):
        eng = self._eng(True, {"state_population": 1000.0, "modifier:state_birth_rate_mult": 0.0,
                               "modifier:state_mortality_mult": 0.0},
                        triggers={"te_demog_effects_run": True})
        eng.vars.update(te_dg_stepped=1.0, te_dg_cbr_model=36.0, te_dg_cdr_model=24.0)
        eng.fixtures.update({f"modifier:{name}": 0.0 for name in P.ENGINE_LINE_TYPES.values()})
        return eng

    def test_fast_mode_scales_the_census_target(self):
        """K = 4: the engine runs 4 x (1 + on top + M) on average, M being the census's term."""
        eng = self._eng_full()
        # bare 475 a month per person; the walk's average multiplier 1.05 (terms on top +0.05)
        self._both(eng, eb=1.05 * 475e3, eb0=475e3, ed=0.98 * 430e3, ed0=430e3)
        mb, md = eng.vars["te_dg_mb"], eng.vars["te_dg_md"]
        self.assertAlmostEqual(eng.vars["te_dg_fast_fb"], 3 * (1.05 + mb), places=5)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fd"], 3 * (0.98 + md), places=5)

    def test_fast_mode_reads_the_new_term_from_the_refresh(self):
        """In game, has_modifier can't see the census modifier the refresh just added in the same effect.
        Hide it from the fast refresh and the term must still come through, from the refresh's locals."""
        eng = self._eng_full()
        eng.locals.update(te_dg_w_eb=1.05 * 475e3, te_dg_w_eb0=475e3, te_dg_w_ed=0.98 * 430e3, te_dg_w_ed0=430e3,
                          te_dg_w_ebr=0.0, te_dg_w_edr=0.0, te_dg_w_eb0m=475e3, te_dg_w_ed0m=430e3,
                          te_dg_w_sev=0.0, te_dg_w_sevd=0.0)
        eng.call("te_demog_rates_refresh")
        self.assertIn("te_dg_mb", eng.vars)   # the applied branch ran (Full, a step's figures)
        mb, md = eng.vars["te_dg_mb"], eng.vars["te_dg_md"]
        eng.modifiers.clear()
        eng.call("te_demog_fast_refresh_rates")
        self.assertAlmostEqual(eng.vars["te_dg_fast_fb"], 3 * (1.05 + mb), places=5)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fd"], 3 * (0.98 + md), places=5)
        body = _block(_text(FAST_EFFECTS), "te_demog_fast_refresh_rates")
        for kind, short in (("births", "b"), ("deaths", "d")):
            self.assertIn(f"add = local_var:te_dg_rate_new_{short}", body)
            self.assertNotIn(f"te_demog_rate_{kind}_applied", body)

    def test_fast_modes_term_is_clipped_at_zero(self):
        """The walk's average can sit below the census's term's reach: per-pop terms (severe starvation on much of a
        state's births) are outside the refresh's clamp. Fast mode's term is clipped at 0 after the census's terms are
        in, so it is never applied with a negative multiplier (Global Constraints)."""
        eng = self._eng_full()
        # the model's births and deaths half of bare: M = -0.5 each, against a walk average of 0.3
        eng.vars.update(te_dg_cbr_model=28.5, te_dg_cdr_model=25.8)
        self._both(eng, eb=0.3 * 475e3, eb0=475e3, ed=0.3 * 430e3, ed0=430e3)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], -0.5, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_md"], -0.5, places=5)
        for var, mod in (("te_dg_fast_fb", "te_demog_fast_births"), ("te_dg_fast_fd", "te_demog_fast_deaths")):
            self.assertEqual(eng.vars[var], 0.0)
            self.assertEqual(eng.modifiers[mod], 0.0)

    def test_fast_and_census_terms_reach_a_joint_fixed_point(self):
        eng = self._eng_full()
        # the walk's averages (1.05, 0.98) hold terms on top of +0.05 and -0.02: state-level ones, so the read has them
        eng.fixtures.update({"modifier:state_birth_rate_mult": 0.05, "modifier:state_mortality_mult": -0.02})
        self._both(eng, eb=1.05 * 475e3, eb0=475e3, ed=0.98 * 430e3, ed0=430e3)
        mb, fb = eng.vars["te_dg_mb"], eng.vars["te_dg_fast_fb"]
        md, fd = eng.vars["te_dg_md"], eng.vars["te_dg_fast_fd"]
        # the next walk sees both terms applied, and so does the state read; nothing else changed
        eng.fixtures.update({"modifier:state_birth_rate_mult": 0.05 + mb + fb,
                             "modifier:state_mortality_mult": -0.02 + md + fd})
        self._both(eng, eb=(1.05 + mb + fb) * 475e3, eb0=475e3, ed=(0.98 + md + fd) * 430e3, ed0=430e3)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fb"], fb, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fd"], fd, places=5)

    def test_first_full_step_takes_the_pairs_off_fast_modes_average(self):
        """The engine-lines plan, Review Focus 5: on the first Full step the walk's average still holds the moved lines'
        pairs, which the refresh clears; fast mode's term subtracts them, so the engine runs K x the census's rate."""
        eng = self._eng_full()
        eng.modifiers["te_demog_line_deaths_down"] = 0.08
        eng.vars["te_dg_ln_deaths"] = -0.08
        eng.fixtures["modifier:state_mortality_mult"] = -0.08
        self._both(eng, eb=475e3, eb0=475e3, ed=0.92 * 430e3, ed0=430e3)
        td = 24.0 * 1000.0 * 100 / 12 / 430e3
        self.assertAlmostEqual(eng.vars["te_dg_fast_fd"], 3 * td, places=5)
        self.assertNotIn("te_demog_line_deaths_down", eng.modifiers)

    def test_fast_mode_composes_with_the_absorbed_lines(self):
        """Owner amendment A (final review 2, m5): a state carrying absorbed per-pop terms A (literacy, mild
        starvation: in the walk's average and the replaced sums, not the state read) and state-level terms on top O. Since 2026-10-11 (owner) O acts on the census's
        rate: at K = 4, M = T/B - 1 - A - O x (1 - T/B), F = 3 x T/B x (1 + O), so the engine runs
        1 + M + F + O + A = 4 x T/B x (1 + O): fast mode scales the census and what's on top, never what M cancels.
        The next clock step, with both terms applied, returns the same M and F."""
        eng = self._eng_full()
        eb0, ed0 = 475e3, 430e3
        a_b, a_d, o_b, o_d = -0.12, -0.20, 0.05, -0.02
        tb, td = 36.0 * 1000.0 * 100 / 12 / eb0, 24.0 * 1000.0 * 100 / 12 / ed0

        def step(mb, fb, md, fd):
            eng.fixtures.update({"modifier:state_birth_rate_mult": o_b + mb + fb,
                                 "modifier:state_mortality_mult": o_d + md + fd})
            eng.locals.update(te_dg_w_eb=(1 + o_b + a_b + mb + fb) * eb0, te_dg_w_eb0=eb0,
                              te_dg_w_ed=(1 + o_d + a_d + md + fd) * ed0, te_dg_w_ed0=ed0,
                              te_dg_w_ebr=a_b * eb0, te_dg_w_edr=a_d * ed0, te_dg_w_eb0m=eb0, te_dg_w_ed0m=ed0,
                              te_dg_w_sev=0.0, te_dg_w_sevd=0.0)
            eng.call("te_demog_rates_refresh")
            eng.call("te_demog_fast_refresh_rates")
            return eng.vars["te_dg_mb"], eng.vars["te_dg_fast_fb"], eng.vars["te_dg_md"], eng.vars["te_dg_fast_fd"]

        mb, fb, md, fd = step(0.0, 0.0, 0.0, 0.0)
        self.assertAlmostEqual(mb, tb - 1 - a_b - o_b * (1 - tb), places=5)
        self.assertAlmostEqual(md, td - 1 - a_d - o_d * (1 - td), places=5)
        self.assertAlmostEqual(fb, 3 * tb * (1 + o_b), places=5)
        self.assertAlmostEqual(fd, 3 * td * (1 + o_d), places=5)
        self.assertAlmostEqual(1 + mb + fb + o_b + a_b, 4 * tb * (1 + o_b), places=5)
        self.assertAlmostEqual(1 + md + fd + o_d + a_d, 4 * td * (1 + o_d), places=5)
        again = step(mb, fb, md, fd)
        for got, want in zip(again, (mb, fb, md, fd)):
            self.assertAlmostEqual(got, want, places=5)

    def test_the_rate_term_is_k_minus_1_times_the_states_own_average(self):
        """A flat +(K - 1) would dilute the state's other terms, which the engine adds into the same (1 + total):
        the term scales with the state's average multiplier instead, so its births and deaths run K times."""
        eng = self._eng(True)   # K = 4
        self._refresh(eng, eb=105.0, eb0=100.0, ed=96.0, ed0=100.0)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fb"], 3 * 1.05)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fd"], 3 * 0.96)
        self.assertAlmostEqual(eng.modifiers["te_demog_fast_births"], 3 * 1.05)
        self.assertAlmostEqual(eng.modifiers["te_demog_fast_deaths"], 3 * 0.96)
        # births at the state's (1 + total) with the term: 1.05 + 3.15 = 4.2 = 4 x 1.05
        self.assertAlmostEqual(1.05 + eng.vars["te_dg_fast_fb"], 4 * 1.05)

    def test_the_term_is_a_fixed_point_once_applied(self):
        """The next walk's multipliers hold the term already applied, which comes off before it is scaled."""
        eng = self._eng(True)
        self._refresh(eng, eb=105.0, eb0=100.0, ed=96.0, ed0=100.0)
        fb, fd = eng.vars["te_dg_fast_fb"], eng.vars["te_dg_fast_fd"]
        self._refresh(eng, eb=100.0 * (1.05 + fb), eb0=100.0, ed=100.0 * (0.96 + fd), ed0=100.0)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fb"], fb)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fd"], fd)

    def test_a_state_with_nobody_gets_no_term(self):
        eng = self._eng(True)
        self._refresh(eng, eb=0.0, eb0=0.0, ed=0.0, ed0=0.0)
        self.assertEqual(eng.vars["te_dg_fast_fb"], 0.0)
        self.assertEqual(eng.modifiers["te_demog_fast_births"], 0.0)

    def test_normal_speed_takes_the_modifiers_and_their_terms_off(self):
        eng = self._eng(True)
        self._refresh(eng, eb=105.0, eb0=100.0, ed=96.0, ed0=100.0)
        eng.fixtures["global_var:te_demog_months_per_step"] = 12.0   # K = 1
        self._refresh(eng, eb=420.0, eb0=100.0, ed=384.0, ed0=100.0)
        self.assertEqual(eng.modifiers, {})
        self.assertNotIn("te_dg_fast_fb", eng.vars)
        self.assertNotIn("te_dg_fast_fd", eng.vars)

    STUBS = {"te_demog_walks": "set_variable = { name = walked value = 1 }",
             "te_inh_refresh_rural_effects": "set_variable = { name = rural value = 1 }",
             "te_demog_wc_state_yearly": "set_variable = { name = wc value = 1 }",
             "te_inh_refresh_wc_state_effects": "set_variable = { name = wc_mods value = 1 }",
             "te_demog_fast_refresh_rates": "set_variable = { name = rates value = 1 }",
             "te_demog_rates_refresh": "set_variable = { name = census_rates value = 1 }",
             "te_demog_seed": "set_variable = { name = did value = 1 }",
             "te_demog_step": "set_variable = { name = did value = 2 }"}

    def test_under_the_clock_the_yearly_pulse_keeps_inheritance_and_wealth_only(self):
        eng = self._eng(True, {"state_population": 1000.0}, effects=self.STUBS)
        # a state with a census was walked at a clock step (te_dg_walk_pop)
        eng.vars.update(te_dg_year=1899.0, te_dg_raw=900.0, te_dg_pop_last=1000.0, te_dg_walk_pop=1000.0)
        eng.call("te_demog_state_yearly")
        self.assertEqual({k: eng.vars.get(k) for k in ("walked", "rural", "wc", "wc_mods", "did")},
                         {"walked": None, "rural": 1.0, "wc": 1.0, "wc_mods": 1.0, "did": None})

    def test_a_clock_step_walks_steps_and_refreshes_the_rates(self):
        cases = [((1899.0, 1000.0), 2),   # a step on: the census steps
                 ((1898.0, 1000.0), 1),   # a step missed (no owner at it): seed again
                 ((1899.0, 1300.0), 2)]   # people 30% up: a step all the same (owner, 2026-10-20)
        for (census, pop), want in cases:
            eng = self._eng(True, {"state_population": pop}, effects=self.STUBS)
            eng.vars.update(te_dg_year=census, te_dg_raw=900.0, te_dg_pop_last=1000.0)
            eng.call("te_demog_state_clock_step")
            self.assertEqual((eng.vars.get("walked"), eng.vars.get("did"), eng.vars.get("rates")), (1.0, want, 1.0),
                             (census, pop))
            self.assertEqual(eng.vars.get("census_rates"), 1.0, "the census's terms are refreshed at each clock step")
            self.assertIsNone(eng.vars.get("wc"), "Wealth Concentration stays on the yearly pulse")

    def test_the_tick_steps_every_state_before_the_census_a_day_later(self):
        """The clock advances before the step events, which fire at once; the census events wait a day, so every
        state has stepped when a country sums them (the census line's lag counts any that had not)."""
        body = re.sub(r"#[^\n]*", "", _block(_text(FAST_EFFECTS), "te_demog_clock_tick"))
        advance = body.index("change_global_variable = { name = te_demog_clock add = 1 }")
        steps = body.index("trigger_event = { id = te_demog_events.2 }")
        census = body.index("trigger_event = { id = te_demog_events.3 days = 1 }")
        self.assertLess(advance, steps)
        self.assertLess(steps, census)
        self.assertIn("set_global_variable = { name = te_demog_window_months value = global_var:te_demog_clock_month }",
                      body[:advance])
        events = _text(FAST_EVENTS)
        self.assertIn("te_demog_state_clock_step = yes", _block(events, "te_demog_events.2"))
        self.assertIn("type = state_event", _block(events, "te_demog_events.2"))
        self.assertIn("te_demog_country_clock_census = yes", _block(events, "te_demog_events.3"))
        hook = _block(_text(DEMOG_ON_ACTIONS), "te_demog_clock_on_action")
        self.assertIn("te_demog_clock_on = yes", hook)
        self.assertIn("te_demog_clock_tick = yes", hook)

    def test_the_yearly_census_waits_for_no_clock(self):
        body = _block(_text(EFFECTS), "te_demog_country_yearly")
        gate = body[body.index("limit = {", body.index("te_demog_wc_national = yes")):body.index("te_demog_country_census = yes")]
        self.assertIn("NOT = { te_demog_clock_on = yes }", gate)

    def test_the_first_switch_re_seeds_and_every_switch_is_click_only(self):
        body = _block(_text(FAST_EFFECTS), "te_demog_fast_set")
        first = body[body.index("NOT = { te_demog_clock_on = yes }"):body.index("set_global_variable = { name = te_demog_months_per_step")]
        self.assertIn("set_variable = { name = te_dg_reseed value = 1 }", first)
        console = _text(DEBUG_EVENTS)
        for months in ("3", "2", "1", "12"):
            call = f"te_demog_fast_set = {{ MONTHS = {months} }}"
            self.assertEqual(console.count(call), 1, months)
            guard = console[console.rindex("limit = { has_variable = te_dg_dbg_click }", 0, console.index(call)):
                            console.index(call)]
            self.assertIn("remove_variable = te_dg_dbg_click", guard, months)

    def test_the_fast_modifiers_are_plus_one_fields(self):
        mods = _raw_blocks([DEBUG_MODIFIERS])
        for name, fields in (("te_demog_fast_births", {"state_birth_rate_mult"}),
                             ("te_demog_fast_deaths", {"state_mortality_mult"}),
                             ("te_demog_fast_speed", {"country_tech_research_speed_mult", "country_tech_spread_mult",
                                                      "state_construction_mult"})):
            got = dict(re.findall(r"^\s*(\w+) = (\S+)", mods[name], re.M))
            got.pop("icon")
            self.assertEqual(got, dict.fromkeys(fields, "1"), name)


TYPES_FILE = ROOT / "common" / "modifier_type_definitions" / "demographics_modifier_types.txt"
MODIFIERS_LOC = ROOT / "localization" / "english" / "te_modifiers_l_english.yml"
ENGINE_MODIFIERS = ROOT / "docs" / "engine" / "modifiers_summary.txt"


class TestModifierTypes(unittest.TestCase):
    """Stage 1 of the modifier-types design: every mortality input is a registered, named type."""

    def test_every_type_is_registered_script_only(self):
        text = _text(TYPES_FILE)
        for name in P.DEMOG_MORTALITY_TYPES:
            body = _block(text, name)
            self.assertIn("script_only = yes", body, name)
            self.assertRegex(body, r"decimals = \d", name)

    def test_every_type_has_a_name_and_a_description(self):
        loc = _text(MODIFIERS_LOC)
        for name in P.DEMOG_MORTALITY_TYPES:
            self.assertRegex(loc, rf"(?m)^ {name}:0 \"", name)
            self.assertRegex(loc, rf"(?m)^ {name}_desc:0 \"", name)

    def test_no_type_is_an_engine_modifier(self):
        engine = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        self.assertIn("state_mortality_mult", engine)   # the list is the one this reads
        for name in P.DEMOG_MORTALITY_TYPES:
            self.assertNotIn(name, engine, name)

    def test_fertility_types_are_registered_named_and_new(self):
        text, loc = _text(TYPES_FILE), _text(MODIFIERS_LOC)
        engine = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        for name in P.DEMOG_FERTILITY_TYPES:
            self.assertTrue(name.startswith("state_"), name)
            body = _block(text, name)
            self.assertIn("script_only = yes", body, name)
            self.assertRegex(body, r"decimals = \d", name)
            # with decimals = 0 and no percent, 0.05 to 0.15 would render as 0 on every carrier's tooltip
            self.assertIn("percent = yes", body, name)
            self.assertRegex(loc, rf"(?m)^ {name}:0 \"", name)
            self.assertRegex(loc, rf"(?m)^ {name}_desc:0 \"", name)
            self.assertNotIn(name, engine, name)

    def test_the_spread_of_medicine_is_registered_named_and_new(self):
        text, loc = _text(TYPES_FILE), _text(MODIFIERS_LOC)
        engine = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        body = _block(text, P.DIFFUSION_TYPE)
        for line in ("script_only = yes", "percent = yes", "color = good"):
            self.assertIn(line, body)
        self.assertRegex(loc, rf"(?m)^ {P.DIFFUSION_TYPE}:0 \"")
        self.assertRegex(loc, rf"(?m)^ {P.DIFFUSION_TYPE}_desc:0 \"")
        self.assertNotIn(P.DIFFUSION_TYPE, engine)

    def test_the_migrant_profiles_types_are_registered_named_and_read(self):
        """Stage 3 (2026-10-19): families among migrants is a census-only state type, and the generated values read it as
        the model does (the techs' line), never the techs. Its other type, the women's-rights laws' women's share of the
        workforce, went on 2026-10-25 (the census's own count of women among its workers took its place)."""
        text, loc = _text(TYPES_FILE), _text(MODIFIERS_LOC)
        engine = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        for name in P.MIGRANT_PROFILE_TYPES:
            self.assertTrue(name.startswith("state_"), name)
            body = _block(text, name)
            for line in ("script_only = yes", "percent = yes", "decimals = 0"):
                self.assertIn(line, body, name)
            self.assertRegex(loc, rf"(?m)^ {name}:0 \"", name)
            # each census type's text ends in the census-off call (te_demog_custom_loc.txt, test_demographics_modifiers)
            self.assertRegex(loc, rf"(?m)^ {name}_desc:0 \".*Used by the census on the Demographics tab\."
                                  r"\[GetPlayer\.GetCustom\('te_demog_census_off_desc'\)\]\"$", name)
            self.assertNotIn(name, engine, name)
        self.assertNotRegex(text, r"(?m)^state_female_work_share_add\s*=")
        self.assertNotRegex(loc, r"(?m)^ state_female_work_share_add(_desc)?:")
        lines = DM.load_carriers(types=P.MIGRANT_PROFILE_TYPES)
        everything = frozenset({"paddle_steamer", "railways", "combustion_engine", "commercial_aviation",
                                "jet_engine_technology"})
        for laws, techs in ((frozenset(), frozenset()),
                            (frozenset({"law_women_in_the_fields"}), frozenset({"railways"})),
                            (frozenset({"law_protected_class"}), everything)):
            with self.subTest(laws=sorted(laws), techs=sorted(techs)):
                inp = demographics_model.Inputs(laws=laws, techs=techs, mods=DM.totals(
                    lines, techs, laws, types=P.MIGRANT_PROFILE_TYPES))
                eng = _Engine({f"modifier:{name}": inp.mods[name] for name in P.MIGRANT_PROFILE_TYPES})
                self.assertAlmostEqual(eng.number("te_demog_family_transport"), inp.mods[P.FAMILY_MIGRATION_TYPE])

    def test_health_care_access_is_a_concept(self):
        self.assertIn("concept_health_care_access = {}",
                      _text(ROOT / "common" / "game_concepts" / "extra_concepts.txt"))

    def test_the_old_country_means_type_is_gone(self):
        # Review Focus 5: the rename leaves no reader, carrier, loc key or param behind
        old = "country_fertility_means_add"
        for sub in ("common", "localization", "scripts", "events", "gui"):
            for path in (ROOT / sub).rglob("*"):
                if path.is_file() and path.suffix in (".txt", ".yml", ".py", ".gui"):
                    self.assertNotIn(old, path.read_text(encoding="utf-8-sig", errors="ignore"), str(path))

    def test_option_l_logs_the_fertility_types(self):
        # the stage-2 in-game check: what each state reads for contraception and fertility control
        values = _text(ROOT / "common" / "script_values" / "te_debug_demog_values.txt")
        self.assertIn(f"value = modifier:{P.CONTRACEPTION_TYPE}", _block(values, "te_debug_demog_mod_contra"))
        self.assertIn(f"value = modifier:{P.MEANS_SHIFT_TYPE}", _block(values, "te_debug_demog_mod_fmeans"))
        self.assertIn("value = te_demog_means", _block(values, "te_debug_demog_means"))
        line = _block(_text(ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"), "te_debug_demog_mods_line")
        for key, sv in (("contra", "te_debug_demog_mod_contra"), ("fmeans", "te_debug_demog_mod_fmeans"),
                        ("means", "te_debug_demog_means")):
            self.assertIn(f" {key}=[THIS.ScriptValue('{sv}')|3]", line)

    def test_option_l_logs_the_work_figures(self):
        """Phase 2 step 1: option l's second line, TE_DEMOG_WORK, logs the census's new figures and the reads no test
        runs (the owner's pension variable, the pension kind, the 10-14s' share, the families and inputs)."""
        line = _block(_text(ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"),
                      "te_debug_demog_mods_line")
        self.assertIn("TE_DEMOG_WORK", line)
        for name in ("wa_share", "at_work", "pensioners", "need", "old_age", "low_share", "wbase", "wf_engine"):
            self.assertIn(f"te_debug_demog_work_{name}", line, name)
        self.assertIn("te_debug_demog_work_wf_target", line)
        # the migrant profile's women's share of the workers (2026-10-25) and families (modifier-types stage 3)
        for read in ("te_debug_demog_pension_var", "te_demog_pension_kind", "te_demog_child_work",
                     "te_demog_women_worker_share", "te_demog_family_transport",
                     "te_debug_demog_womens_mod", "te_debug_demog_replaced_mod", "te_debug_demog_part_m_mod",
                     "te_debug_demog_part_mod", "te_debug_demog_cap_mod", "te_demog_line_working_adults_applied"):
            self.assertIn(read, line)
        values = _text(ROOT / "common" / "script_values" / "te_debug_demog_values.txt")
        for name, var in (("wa_share", "te_dg_wa_share"), ("at_work", "te_dg_at_work"),
                          ("pensioners", "te_dg_pensioners"), ("need", "te_dg_need"), ("old_age", "te_dg_old_age"),
                          ("low_share", "te_dg_low_share"), ("wbase", "te_dg_wbase"),
                          ("wf_engine", "te_dg_wf_engine")):
            body = _block(values, f"te_debug_demog_work_{name}")
            self.assertIn(f"has_variable = {var}", body, name)
            self.assertIn("value = -1", body, name)
        self.assertIn("owner ?= { has_variable = te_dg_pension_age }", _block(values, "te_debug_demog_pension_var"))

    def test_option_p_sets_up_call_3s_carriers(self):
        console = _text(DEBUG_EVENTS)
        call = "te_debug_demog_call3_setup = yes"
        self.assertEqual(console.count(call), 1)
        guard = console[console.rindex("limit = { has_variable = te_dg_dbg_click }", 0, console.index(call)):
                        console.index(call)]
        self.assertIn("remove_variable = te_dg_dbg_click", guard)
        setup = _block(_text(ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"),
                       "te_debug_demog_call3_setup")
        for line in ("activate_law = law_type:law_punishment_focused_criminal_justice",
                     "type = amendment_community_service",
                     "add_modifier = { name = modifier_woman_soldiers multiplier = 0.5 days = 60 }",
                     "add_modifier = { name = te_demog_debug_ig_loyal days = 60 }",
                     "trigger_event = { id = te_debug_demog.3 days = 1 }",
                     "trigger_event = { id = te_debug_demog.3 days = 31 }"):
            self.assertIn(line, setup)
        self.assertLess(setup.index("te_debug_demog_mods_line = yes"), setup.index("activate_law"),
                        "the before line comes first")
        self.assertIn("te_debug_demog_mods_line = yes", _block(console, "te_debug_demog.3"))
        self.assertIn("interest_group_approval_add = 30", _block(_text(DEBUG_MODIFIERS), "te_demog_debug_ig_loyal"))
        loc = _text(ROOT / "localization" / "english" / "te_events_l_english.yml")
        for key in ("te_debug_demog.1.p", "te_debug_demog.1.p.tt"):
            self.assertRegex(loc, rf"(?m)^ {re.escape(key)}:0 \"", key)

    def test_option_l_logs_the_institution_impact(self):
        # the in-game check of #889: the Midlands read "A multiplier of 0.94" on its Ministry of Health, so its line
        # should log impact=0.940 (Local Vernacular's -0.05, obstinance's share)
        line = _block(_text(ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"), "te_debug_demog_mods_line")
        self.assertIn(" impact=[THIS.ScriptValue('te_demog_institution_impact')|3]", line)
        # the spread of medicine's rate (the Causes of Death plan)
        self.assertIn(" diff=[THIS.ScriptValue('te_demog_medical_diffusion')|3]", line)

    def test_seven_state_types(self):
        # one type per term, read in state scope; a tech's or law's line reaches the state because
        # states inherit country modifiers (owner, 2026-10-10)
        self.assertEqual(len(set(P.DEMOG_MORTALITY_TYPES)), 7)
        for name in P.DEMOG_MORTALITY_TYPES:
            self.assertTrue(name.startswith("state_"), name)


class TestCausesInTheStep(unittest.TestCase):
    """The Causes of Death plan: a seed starts medicine at its targets, a step drifts it before the year's rates, and
    both store the inputs the factors read."""

    INP0 = TestCohortScript.INP
    INP1 = dataclasses.replace(TestCohortScript.INP, turmoil=0.4, mods={
        **TestCohortScript.INP.mods,   # Women in the Fields' share at work (modifier-types stage 3)
        P.ACCESS_TYPE: 0.3, P.TREATMENT_TYPE["infection"]: 0.4, P.TREATMENT_TYPE["maternal"]: 0.35,
        "state_external_mortality_mult": -0.1, P.DIFFUSION_TYPE: 0.15})

    def test_a_seed_starts_at_its_targets_and_stores_its_inputs(self):
        eng = _engine_for(self.INP1, 1836, 250000.0, real_multipliers=True)
        eng.call("te_demog_seed")
        targets = demographics_model.medicine_targets(self.INP1)
        self.assertAlmostEqual(eng.vars["te_dg_acc"], targets["access"], places=9)
        self.assertAlmostEqual(eng.vars["te_dg_in_turm"], 0.4, places=9)
        self.assertAlmostEqual(eng.vars["te_dg_m_inf"], demographics_model.cause_multipliers(self.INP1)["infection"],
                               places=9)

    def test_the_step_drifts_medicine_before_its_rates(self):
        eng = _engine_for(self.INP0, 1836, 250000.0, real_multipliers=True)
        eng.call("te_demog_seed")
        eng.fixtures.update(_mod_fixtures(self.INP1))
        eng.call("te_demog_medicine_drift")
        eng.call("te_demog_prepare")
        med = demographics_model.medicine_drift(demographics_model.medicine_targets(self.INP0), self.INP1)
        # and the seed's count of women among the workers, which splits the year's work deaths (2026-10-25)
        drifted = dataclasses.replace(self.INP1, medicine=med, work_female_share=eng.vars["te_dg_fws_wk"])
        want = demographics_model.cause_multipliers(drifted)
        for cause, var in (("infection", "te_dg_m_inf"), ("external", "te_dg_m_ext"), ("chronic", "te_dg_m_chr")):
            self.assertAlmostEqual(eng.vars[var], want[cause], places=9, msg=cause)
        self.assertAlmostEqual(eng.vars["te_dg_m_mat"], want["maternal"] * P.MATERNAL_PER_100K_BIRTHS, places=6)
        # #1045: the adults' infection factor reads the same drifted medicine
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_infection_adult")),
                               demographics_model.infection_adult(drifted), places=9)
        self.assertLess(demographics_model.infection_adult(drifted), 0.97, "a factor that moves the life table")
        qf, qm, _ = demographics_model.group_rates(drifted)
        e0 = (demographics_model.life_table(qf)["e0"] + demographics_model.life_table(qm)["e0"]) / 2
        self.assertAlmostEqual(eng.vars["te_dg_e0"], e0, places=6)

    def stepped(self, effects=None):
        """A state seeded on INP0's inputs in 1836, then one whole te_demog_step on INP1's (TestTrend's setup)."""
        eng = _engine_for(self.INP0, 1836, 250000.0, effects=effects, real_multipliers=True)
        eng.call("te_demog_seed")
        eng.fixtures.update(te_demog_crisis=0.0, te_demog_family_transport=0.0, **_mod_fixtures(self.INP1))
        eng.vars.update(te_dg_eb=0.0, te_dg_ed=0.0, te_dg_fjob_share=0.3)
        eng.fixtures["year"] = 1837.0
        eng.vars["te_dg_pop_last"] = eng.vars["te_dg_people"]
        eng.call("te_demog_step")
        return eng

    def test_one_step_drifts_once(self):
        # the whole step, not its halves: a second drift anywhere in te_demog_step would move medicine twice a year
        # (review of Tasks 4-5, minor 3)
        eng = self.stepped()
        want = demographics_model.medicine_drift(demographics_model.medicine_targets(self.INP0), self.INP1)
        for key, var in (("access", "te_dg_acc"), ("infection", "te_dg_trt_inf"), ("maternal", "te_dg_trt_mat")):
            self.assertAlmostEqual(eng.vars[var], want[key], places=9, msg=key)
        self.assertNotEqual(want["access"], demographics_model.medicine_targets(self.INP1)["access"], "a real gap")

    GATE_VARS = ("te_dg_acc", "te_dg_trt_inf", "te_dg_trt_mat", "te_dg_trt_chr", "te_dg_in_ext", "te_dg_in_work",
                 "te_dg_in_chr", "te_dg_in_turm", "te_dg_in_crowd", "te_dg_in_sol", "te_dg_in_lit")

    def test_an_old_census_starts_at_its_targets(self):
        """Review Focus 1: a census state from before this build has none of the eleven variables
        te_demog_state_causes_sgui asks for. Its first step starts medicine at the targets and leaves all eleven."""
        eng = _engine_for(self.INP1, 1837, 250000.0, real_multipliers=True)
        for name in self.GATE_VARS:
            self.assertNotIn(name, eng.vars)
        eng.call("te_demog_medicine_drift")
        eng.call("te_demog_prepare")
        for name in self.GATE_VARS:
            self.assertIn(name, eng.vars, name)
        targets = demographics_model.medicine_targets(self.INP1)
        self.assertAlmostEqual(eng.vars["te_dg_acc"], targets["access"], places=9)
        self.assertAlmostEqual(eng.vars["te_dg_trt_inf"], targets["infection"], places=9)

    def test_the_entry_points_run_in_order(self):
        effects = _raw_blocks([EFFECTS])
        begin = [k for k, _, _ in _parse_script(effects["te_demog_step_begin"])]
        # relative order only: #906 puts te_demog_practices_step before te_demog_prepare as well
        self.assertLess(begin.index("te_demog_medicine_drift"), begin.index("te_demog_prepare"))
        seed = [k for k, _, _ in _parse_script(effects["te_demog_seed"])]
        self.assertLess(seed.index("te_demog_medicine_at_target"), seed.index("te_demog_prepare"))
        prepare = [k for k, _, _ in _parse_script(effects["te_demog_prepare"])]
        first_mult = next(i for i, (k, _, v) in enumerate(_parse_script(effects["te_demog_prepare"]))
                          if k == "set_local_variable" and _find(v, "name") == "te_dg_m_inf")
        self.assertLess(prepare.index("te_demog_cause_inputs_store"), first_mult)


class TestMedicalOutreach(unittest.TestCase):
    """The Causes of Death plan: a decree that speeds the spread of medicine in one state, under Full only."""

    DECREES = ROOT / "common" / "decrees" / "extra_decrees.txt"

    def test_the_decree_carries_the_spread_of_medicine(self):
        body = _block(_text(self.DECREES), "decree_medical_outreach")
        modifier = _parse_script(body)
        lines = _find(modifier, "modifier")
        self.assertEqual([(k, float(v)) for k, _, v in lines], [(P.DIFFUSION_TYPE, P.MEDICAL_OUTREACH_DIFFUSION)])
        self.assertEqual(_find(modifier, "cost"), "100")

    def test_it_exists_only_under_full(self):
        # vanilla 00_decree.txt: country_trigger decides whether a decree is shown; the rule's wrapper, never the rule
        trig = _find(_parse_script(_block(_text(self.DECREES), "decree_medical_outreach")), "country_trigger")
        self.assertEqual(trig, [("te_demog_effects_run", "=", "yes")])

    def test_it_is_offered_where_medicine_is_behind(self):
        fixtures = {f"modifier:{t}": 0.0 for t in P.DEMOG_TYPES}
        fixtures[f"modifier:{P.ACCESS_TYPE}"] = 0.3
        eng = _Engine(fixtures)
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_medicine_gap")), 0.0, "no census medicine yet")
        eng.vars.update(te_dg_acc=0.4, te_dg_trt_inf=0.0, te_dg_trt_mat=0.0, te_dg_trt_chr=0.0)
        self.assertTrue(eng.holds(_parse_script("te_demog_medicine_behind = yes")))
        eng.vars["te_dg_acc"] = 0.7
        self.assertFalse(eng.holds(_parse_script("te_demog_medicine_behind = yes")))

    def _issuable(self, issued, acc=0.7, trt_inf=0.0, inf_target=0.0, spread=0.0):
        """The decree's state_trigger for a state whose access target is 0.7 and infection's treatment target
        `inf_target`, at drifted access `acc` and infection's treatment `trt_inf` (the other treatments 0, on target),
        and `spread` from the types other than the decree's own; a held decree adds its line to the state's spread, as
        the engine's modifier read does."""
        trig = _find(_parse_script(_block(_text(self.DECREES), "decree_medical_outreach")), "state_trigger")
        fixtures = {f"modifier:{t}": 0.0 for t in P.DEMOG_TYPES}
        fixtures[f"modifier:{P.ACCESS_TYPE}"] = 0.3
        fixtures[f"modifier:{P.TREATMENT_TYPE['infection']}"] = inf_target
        fixtures[f"modifier:{P.DIFFUSION_TYPE}"] = spread + (P.MEDICAL_OUTREACH_DIFFUSION if issued else 0.0)
        eng = _Engine(fixtures)
        if issued:
            eng.decrees.add("decree_medical_outreach")
        eng.vars.update(te_dg_acc=acc, te_dg_trt_inf=trt_inf, te_dg_trt_mat=0.0, te_dg_trt_chr=0.0)
        return eng.holds(trig)

    def test_it_is_offered_only_where_it_changes_the_next_count(self):
        """Only where it does something (owner, 2026-10-23): the next count, which closes the state's share of each
        gap and puts a value within the snap on its target, comes out different with the decree's line than without
        it (demographics_model.medicine_drift). Not for the last few thousandths the count closes anyway, nor where
        the share of the gap is at its cap; and the shortfalls are judged one by one, not summed."""
        targets = {"infection": 0.4, "maternal": 0.0, "chronic": 0.0}
        for spread in (0.0, 0.25, 0.6, 0.9):
            for short in (0.0, 0.004, 0.0054, 0.0058, 0.0072, 0.0078, 0.01, 0.05, 0.3):
                for trt_short in (0.0, 0.004, 0.02):
                    mods = {P.ACCESS_TYPE: 0.3, **{P.TREATMENT_TYPE[c]: v for c, v in targets.items()}}
                    prev = {"access": 0.7 - short, "infection": 0.4 - trt_short, "maternal": 0.0, "chronic": 0.0}
                    without = demographics_model.medicine_drift(prev, SimpleNamespace(mods={**mods,
                                                                                       P.DIFFUSION_TYPE: spread}))
                    with_it = demographics_model.medicine_drift(prev, SimpleNamespace(mods={
                        **mods, P.DIFFUSION_TYPE: spread + P.MEDICAL_OUTREACH_DIFFUSION}))
                    changes = any(abs(without[k] - with_it[k]) > 1e-9 for k in without)
                    trig = _find(_parse_script(_block(_text(self.DECREES), "decree_medical_outreach")),
                                 "state_trigger")
                    fixtures = {f"modifier:{t}": 0.0 for t in P.DEMOG_TYPES}
                    fixtures.update({f"modifier:{t}": v for t, v in mods.items()})
                    fixtures[f"modifier:{P.DIFFUSION_TYPE}"] = spread
                    eng = _Engine(fixtures)
                    eng.vars.update(te_dg_acc=prev["access"], te_dg_trt_inf=prev["infection"], te_dg_trt_mat=0.0,
                                    te_dg_trt_chr=0.0)
                    with self.subTest(spread=spread, short=short, trt_short=trt_short):
                        self.assertEqual(eng.holds(trig), changes)
        # what the old rule (the summed shortfalls above the snap) offered: two values 0.004 short, each of which the
        # count puts on its target
        self.assertFalse(self._issuable(False, acc=0.696, trt_inf=0.396, inf_target=0.4))
        self.assertTrue(self._issuable(False, acc=0.696, trt_inf=0.39, inf_target=0.4))
        # a share of the gap at its cap closes every gap at the count: nothing for the decree to add
        self.assertTrue(self._issuable(False, acc=0.4))
        self.assertFalse(self._issuable(False, acc=0.4, spread=0.9))

    def test_the_ai_weighs_it_by_the_gap(self):
        # the shared-mechanics rule: the AI issues it where medicine is behind, with lower thresholds once issued
        # (Road Maintenance's pattern), and never once the state caught up; and, as vanilla weighs decrees, by the
        # state's people (the review of #916, logic M1): x1 at 250,000, from x0.2 to x2
        weight = _find(_parse_script(_block(_text(self.DECREES), "decree_medical_outreach")), "ai_weight")
        fixtures = {f"modifier:{t}": 0.0 for t in P.DEMOG_TYPES}
        fixtures[f"modifier:{P.ACCESS_TYPE}"] = 0.6          # access heading for 1.0
        for acc, issued, people, want in ((1.0, False, 250e3, 0.0), (0.95, False, 250e3, 0.0),
                                          (0.85, False, 250e3, 100.0), (0.6, False, 250e3, 200.0),
                                          (0.93, True, 250e3, 100.0), (0.75, True, 250e3, 200.0),
                                          (0.995, True, 250e3, 0.0),
                                          (0.6, False, 2e6, 400.0), (0.6, False, 10e3, 40.0)):
            eng = _Engine({**fixtures, "state_population": people})
            if issued:
                eng.decrees.add("decree_medical_outreach")
            eng.vars.update(te_dg_acc=acc, te_dg_trt_inf=0.0, te_dg_trt_mat=0.0, te_dg_trt_chr=0.0)
            with self.subTest(acc=acc, issued=issued, people=people):
                self.assertAlmostEqual(eng._ops(weight, 0.0), want, places=6)

    def test_an_issued_decree_lapses_once_the_state_catches_up(self):
        """state_trigger: valid only while medicine is behind, issued or not, so the engine's weekly check ends the
        decree once the state has caught up (vanilla Emergency Relief's and Violent Suppression's pattern). It is the
        AI's only way to give it up: the AI never revokes a decree itself, and an ai_weight of 0 only stops it issuing
        one (#894's observer run, 2026-10-12: with a has_decree escape, every AI decree stood until the state changed
        hands)."""
        for acc, issued, want in ((0.5, False, True), (0.7, False, False), (0.5, True, True), (0.697, True, False),
                                  (0.7, True, False)):
            with self.subTest(acc=acc, issued=issued):
                self.assertEqual(self._issuable(issued, acc=acc), want)

    def test_a_held_decree_lasts_exactly_where_it_could_be_issued(self):
        """A held decree is judged at the state's spread without its own line: judged with it, a decree issued 0.0065
        short (0.00585 left at the count without it, 0.00455 with it) would end at the next weekly check, its authority
        spent on a decree the state couldn't keep."""
        self.assertTrue(self._issuable(False, acc=0.6935))
        self.assertTrue(self._issuable(True, acc=0.6935))
        for spread in (0.0, 0.15, 0.35, 0.6, 0.85):
            for short in (0.0, 0.003, 0.0055, 0.006, 0.0075, 0.009, 0.02, 0.2):
                with self.subTest(spread=spread, short=short):
                    self.assertEqual(self._issuable(True, acc=0.7 - short, spread=spread),
                                     self._issuable(False, acc=0.7 - short, spread=spread))


class TestCausesDisplay(unittest.TestCase):
    """The Causes of Death section's reads (the plan's Task 8)."""

    def _shown(self, sgui, eng):
        body = _parse_script(_block(_text(SGUIS), sgui))
        return eng.holds(_find(body, "is_shown"))

    def test_the_on_top_gate_needs_a_measured_window(self):
        # Review Focus 2: the first Full step after a seed writes dz 0 against no target; the first after Display only
        # has a target but its window ran with no M, so no refresh's clamp flag was there to copy (te_dg_ed_clamp_d),
        # which the deaths row's floor note reads (since the deaths on top count under their causes, owner 2026-10-22)
        base = dict(te_dg_ed_target=1000.0, te_dg_dz=0.0, te_dg_cdr_model=12.0, te_dg_ed_clamp_d=0.0)
        for full, change, shown in ((True, {}, True), (True, {"te_dg_ed_target": 0.0}, False),
                                    (True, {"te_dg_ed_clamp_d": None}, False), (True, {"te_dg_cdr_model": None}, False),
                                    (False, {}, False)):
            eng = _Engine({}, triggers={"te_demog_effects_run": full})
            eng.vars.update(base)
            for k, v in change.items():
                if v is None:
                    del eng.vars[k]
                else:
                    eng.vars[k] = v
            with self.subTest(full=full, change=change):
                self.assertEqual(self._shown("te_demog_state_on_top_sgui", eng), shown)

    def test_the_causes_gate_needs_the_steps_inputs(self):
        eng = _Engine({})
        self.assertFalse(self._shown("te_demog_state_causes_sgui", eng))
        eng.vars.update(_stored(demographics_model.Inputs()))
        self.assertTrue(self._shown("te_demog_state_causes_sgui", eng))

    def test_each_causes_deaths_on_top_read_as_added_or_spared(self):
        """Owner, 2026-10-22: each cause's legend hover says how many of its deaths the game's effects added on top of
        the census (or spared): the signed figure, its size and a code, 1 added and 2 spared from one death, 0 without
        a figure (not Full, a first count, an old save)."""
        for top, code in ((None, 0), (0.4, 0), (1.0, 1), (5200.0, 1), (-0.9, 0), (-1.0, 2), (-300.0, 2)):
            eng = _Engine({})
            if top is not None:
                eng.vars["te_dg_dc_chr_top"] = top
            with self.subTest(top=top):
                self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_dc_top_code_chr")), code)
                self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_dc_top_abs_chr")), abs(top or 0.0))

    def test_the_arrow_shows_while_medicine_moves(self):
        inp = demographics_model.Inputs(mods={P.ACCESS_TYPE: 0.3})
        eng = _Engine(_mod_fixtures(inp))
        eng.vars.update(_stored(dataclasses.replace(inp, medicine={"access": 0.5, "infection": 0.0,
                                                                   "maternal": 0.0, "chronic": 0.0})))
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_access_moving")), 1)
        eng.vars["te_dg_acc"] = demographics_model.medicine_targets(inp)["access"]
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_access_moving")), 0)
        # each cause's medicine: moving while its treatment is off its target, still once it arrived
        eng.vars["te_dg_trt_inf"] = 0.3
        inp_t = demographics_model.Inputs(mods={P.ACCESS_TYPE: 0.3, P.TREATMENT_TYPE["infection"]: 0.4})
        eng.fixtures.update(_mod_fixtures(inp_t))
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_medicine_moving_infection")), 1)
        eng.vars["te_dg_trt_inf"] = 0.4
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_medicine_moving_infection")), 0)
        # the review of #916 (panel M3): past the snap but under the shown figures' 0.01, the arrow would read
        # "62% -> 62%" or "x0.75 -> x0.75": it waits until the rounded figures differ
        eng.vars["te_dg_acc"] = demographics_model.medicine_targets(inp)["access"] - 0.008
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_access_moving")), 0)
        eng.vars["te_dg_acc"] = demographics_model.medicine_targets(inp)["access"] - 0.012
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_access_moving")), 1)
        eng.vars["te_dg_acc"] = demographics_model.medicine_targets(inp)["access"]
        eng.vars["te_dg_trt_inf"] = 0.4 - 0.008 / eng.vars["te_dg_acc"]
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_medicine_moving_infection")), 0)

    def test_every_key_the_section_names_exists(self):
        # in any English file: organize_loc files a key no .gui names yet (until Task 9) in te_unused_l_english.yml
        loc = "\n".join(_text(p) for p in sorted((ROOT / "localization" / "english").glob("*_l_english.yml")))
        # issue #1029: the pie's legend rows, a name a slice (shared with the country tab) and a hover each
        slices = ("inf", "ext", "chr", "work", "mat", "kill", "war")
        keys = ["te_demog_sec_causes", "te_demog_st_dc_pending", "te_demog_st_acc", "te_demog_st_acc_value",
                "te_demog_st_acc_tt", "te_demog_st_pie_tt", "te_demog_st_cdr_tt", "te_demog_st_cdr_value",
                "te_demog_st_ontop_rate", "te_demog_st_ontop_floor"]
        keys += [f"te_demog_dc_{r}" for r in slices] + [f"te_demog_st_dc_{r}_tt" for r in slices]
        # each cause's deaths on top (owner, 2026-10-22): added or spared, and what adds them
        keys += [f"te_demog_{s}_dc_{c}_top_{k}" for s in ("st", "cd") for c in P.DEATH_CAUSES for k in ("more", "less")]
        keys += [f"te_demog_dc_top_{c}_what" for c in P.DEATH_CAUSES]
        for key in keys:
            self.assertRegex(loc, rf"(?m)^ {key}:0 \"", key)


WIDGETS = ROOT / "gui" / "te_demographics_widgets.gui"
MISC_LOC = ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml"


def _gui_type(text, name):
    start = text.index(f"type {name} = ")
    depth, i = 0, text.index("{", start)
    while True:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
        if depth == 0:
            return text[start:i]


class TestCausesSection(unittest.TestCase):
    """The Causes of Death section on the state subtab (the plan's Task 9)."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _text(WIDGETS)
        cls.section = _gui_type(cls.gui, "te_state_demog_causes")
        cls.loc = dict(re.findall(r'(?m)^ ([\w.]+):0 "(.*)"$', _text(MISC_LOC)))

    def test_it_sits_after_the_overview(self):
        # issue #1029: the subtab takes the country tab's order (te_demographics_layout.gui), the pyramid after Causes
        # of Death, then Work and Retirement and phase 3's Longevity (late-game §6.2), and the state's own Modifiers
        # after Wealth (owner, 2026-10-21)
        content = _gui_type(_text(ROOT / "gui" / "te_demographics_layout.gui"), "te_state_demog_content")
        order = re.findall(r"(te_state_demog_\w+) = \{\}", content)
        self.assertEqual(order, ["te_state_demog_overview", "te_state_demog_causes", "te_state_demog_pyramid",
                                 "te_state_demog_work", "te_state_demog_longevity", "te_state_demog_wealth",
                                 "te_state_demog_modifiers", "te_state_demog_how"])

    def test_open_by_default(self):
        # rule 7: a section that starts open names its flag _closed
        self.assertIn("te_demog_st_causes_closed", self.section)
        self.assertNotIn("_open'", self.section)

    def test_every_read_sits_under_its_gate(self):
        """Review Focus 1: the legend's rows, whose hovers read the step's inputs and its deaths by cause, sit only
        inside the deaths-by-cause gate's container (a step since issue #1029, which stores both), Health Care Access
        under the causes gate, and the measured split is reached only through a SelectLocalization on the on-top gate."""
        inner = self.section.split("te_demog_state_dc_sgui').IsShown", 2)[2]   # past the pending line's Not(...)
        inner = inner[:inner.index("te_demog_state_causes_sgui")]
        outer = self.section.replace(inner, "")
        for key in re.findall(r'tooltip = "(te_demog_st_dc_\w+)"', self.section):
            self.assertIn(key, inner, key)
            self.assertNotIn(key, outer, key)
        acc = self.section[self.section.index("te_demog_state_causes_sgui"):]
        self.assertIn('tooltip = "te_demog_st_acc_tt"', acc)
        # the measured window's figures only through the deaths row's SelectLocalization on the on-top gate
        split = re.compile(r"te_dg_ed_state|te_dg_ed_sev|te_dg_sev_share|te_dg_ed_clamp_d|te_demog_deaths_")
        self.assertIsNone(split.search(self.loc["te_demog_st_cdr_tt"]))
        self.assertIn("GetScriptedGui('te_demog_state_on_top_sgui').IsShown( GuiScope.SetRoot( State.MakeScope ).End ), "
                      "'te_demog_st_ontop_rate', 'te_tt_blank'", self.loc["te_demog_st_cdr_tt"])
        self.assertIsNotNone(split.search(self.loc["te_demog_st_ontop_rate"]))

    def test_the_deaths_on_top_count_under_their_causes(self):
        """Owner, 2026-10-22: no slice of their own, so every legend row shows in every setting, and each cause's row
        says how many of its deaths the game added on top (or spared) through its own code."""
        self.assertNotIn("te_demog_dc_ontop", self.section)
        self.assertNotIn("te_demog_state_full_sgui", self.section)
        for c in P.DEATH_CAUSES:
            deaths = self.loc[f"te_demog_st_dc_{c}_deaths"]
            self.assertIn(f"ScriptValue('te_demog_dc_top_code_{c}')", deaths)
            self.assertIn(f"'te_demog_st_dc_{c}_top_more'", deaths)
            self.assertIn(f"'te_demog_st_dc_{c}_top_less'", deaths)
            self.assertIn(f"te_demog_dc_top_abs_{c}", self.loc[f"te_demog_st_dc_{c}_top_more"])

    def test_names_are_spliced(self):
        """The review of #916 (panel I1): laws, institutions and techs by their loc keys, never typed (the game says
        "Workers' Protections"; the mod renames the Health System "Ministry of Health")."""
        for key, names in (("te_demog_st_dc_work_tt", ("$law_regulatory_bodies$", "$law_worker_protections$")),
                           ("te_demog_st_acc_tt", ("$institution_health_system$",)),
                           ("te_demog_st_dc_ext_tt", ("$institution_ministry_of_consumer_protection$", "$combustion_engine$",
                                                   "$institution_police$", "$autonomous_vehicles$"))):
            for name in names:
                self.assertIn(name, self.loc[key], key)
        typed = re.compile(r"Worker Protections|Regulatory Bodies|Ministry of Health|Consumer Protection|Combustion Engine|"
                           r"Public Safety|Restorative Justice|Penal Labor")
        for key, value in self.loc.items():
            if key.startswith("te_demog_st_"):
                self.assertIsNone(typed.search(value), key)
        concepts = dict(re.findall(r'(?m)^ ([\w.]+):0 "(.*)"$', _text(ROOT / "localization" / "english" /
                                                                      "te_concepts_l_english.yml")))
        self.assertIn("$institution_health_system$", concepts["concept_health_care_access_desc"])
        # the access hover's two lines sum to where access is heading, not the row (panel M2)
        self.assertIn("Where it is heading:", self.loc["te_demog_st_acc_tt"])

    def test_the_country_tab_has_its_own(self):
        """Issue #1029 built the country tab's section where #894's TODO stood, straight after the overview."""
        tab = _gui_type(_text(ROOT / "gui" / "te_demographics_layout.gui"), "te_demog_tab_sections")
        self.assertNotIn("TODO", tab)
        order = re.findall(r"(te_demog_\w+) = \{\}", tab)
        self.assertEqual(order[:2], ["te_demog_overview", "te_demog_sec_causes"])


class TestCauseFactorsScript(unittest.TestCase):
    """te_demog_f_<cause>_<factor> and te_demog_mult_<cause> (generated) against demographics_model.cause_factors,
    on the step's stored inputs (the Causes of Death plan)."""

    CASES = [
        {},
        {P.TREATMENT_TYPE["infection"]: 0.81, P.TREATMENT_TYPE["maternal"]: 0.9, P.TREATMENT_TYPE["chronic"]: 0.59},
        {P.ACCESS_TYPE: 0.6, P.TREATMENT_TYPE["infection"]: 0.81, P.TREATMENT_TYPE["maternal"]: 2.0,
         P.TREATMENT_TYPE["chronic"]: 0.3, "state_chronic_mortality_mult": -0.05},
        {P.ACCESS_TYPE: 1.5, P.TREATMENT_TYPE["infection"]: 0.3},
        {"state_work_mortality_mult": -0.9, "state_external_mortality_mult": -0.1},
        {"state_work_mortality_mult": 0.1, "state_external_mortality_mult": 0.3, "state_chronic_mortality_mult": -0.9},
        # modern safety (2026-10-16): today's carriers on Workplace Safety's level 5, and a sum past the cap
        {"state_work_mortality_mult": -0.5, P.SAFETY_TYPES["work"]: 0.9, P.SAFETY_TYPES["external"]: 0.4,
         "state_external_mortality_mult": -0.12},
        {"state_work_mortality_mult": -0.9, P.SAFETY_TYPES["work"]: 1.3, P.SAFETY_TYPES["external"]: 0.2},
    ]
    STATES = ((3, 0.1, 0.0, 0.0), (6.5, 0.2, 0.4, 0.05), (8, 0.0, 1.0, 0.0), (20, 0.5, 0.2, 0.6), (40, 1.0, 0.0, 0.0))

    def _eng(self, inp):
        eng = _Engine({})
        eng.vars.update(_stored(inp))
        return eng

    def test_each_factor_matches_the_model(self):
        for mods in self.CASES:
            for sol, lit, turm, crowd in self.STATES:
                inp = demographics_model.Inputs(sol=sol, literacy=lit, turmoil=turm, crowding=crowd, mods=dict(mods))
                eng = self._eng(inp)
                for cause, factors in demographics_model.cause_factors(inp).items():
                    for f, want in factors.items():
                        with self.subTest(mods=mods, sol=sol, cause=cause, factor=f):
                            got = eng.value(eng._tree(eng.values, f"te_demog_f_{cause}_{f}"))
                            self.assertAlmostEqual(got, want, places=9)

    def test_each_multiplier_matches_the_model(self):
        for mods in self.CASES:
            for sol, lit, turm, crowd in self.STATES:
                inp = demographics_model.Inputs(sol=sol, literacy=lit, turmoil=turm, crowding=crowd, mods=dict(mods))
                eng, want = self._eng(inp), demographics_model.cause_multipliers(inp)
                for cause in P.CAUSE_FACTORS:
                    scale = P.MATERNAL_PER_100K_BIRTHS if cause == "maternal" else 1.0
                    with self.subTest(mods=mods, sol=sol, cause=cause):
                        got = eng.value(eng._tree(eng.values, f"te_demog_mult_{cause}"))
                        self.assertAlmostEqual(got, want[cause] * scale, places=6)

    def test_the_factors_read_the_drifted_medicine(self):
        inp = demographics_model.Inputs(sol=12, literacy=0.3, mods=dict(self.CASES[2]),
                                        medicine={"access": 0.45, "infection": 0.2, "maternal": 0.3, "chronic": 0.05})
        eng = self._eng(inp)
        for cause in P.MEDICINE_CAUSES:
            got = eng.value(eng._tree(eng.values, f"te_demog_f_{cause}_medicine"))
            self.assertAlmostEqual(got, demographics_model.medicine(inp, cause), places=9)
        # the target is today's, read live
        eng.fixtures.update(_mod_fixtures(inp))
        target = demographics_model.medicine(dataclasses.replace(inp, medicine=None), "infection")
        got = eng.value(eng._tree(eng.values, "te_demog_f_infection_medicine_target"))
        self.assertAlmostEqual(got, target, places=9)

    def test_the_inputs_store_takes_the_steps_reads(self):
        inp = demographics_model.Inputs(sol=12, literacy=0.3, turmoil=1.4, mods=dict(self.CASES[5]))
        eng = _Engine(_mod_fixtures(inp))
        eng.vars.update(te_dg_sol=12.0, te_dg_lit=0.3)   # the walk's, which the store copies
        eng.call("te_demog_cause_inputs_store")
        want = _stored(inp)
        for name in ("te_dg_in_ext", "te_dg_in_work", "te_dg_in_chr", "te_dg_in_turm", "te_dg_in_crowd", "te_dg_in_sol",
                     "te_dg_in_lit"):
            self.assertAlmostEqual(eng.vars[name], want[name], places=9, msg=name)
        self.assertEqual(eng.vars["te_dg_in_turm"], 1.0, "turmoil is a 0-1 share")

    def test_the_malaria_factor_matches_the_model(self):
        """Calibration step 3 (the spec's §2.2): each trait level, with and without Malaria Prevention's control, and a
        part control; the factor multiplies into infection's multiplier."""
        for level in (0, 1, 2):
            for control in (0.0, 0.4, 1.0, 1.5):
                inp = demographics_model.Inputs(sol=7, literacy=0.1, malaria=level,
                                                mods={P.MALARIA_CONTROL_TYPE: control})
                eng = self._eng(inp)
                want = demographics_model.cause_factors(inp)["infection"]["malaria"]
                with self.subTest(level=level, control=control):
                    self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_f_infection_malaria")), want,
                                           places=9)
                    self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_mult_infection")),
                                           demographics_model.cause_multipliers(inp)["infection"], places=6)
        self.assertAlmostEqual(demographics_model.cause_factors(demographics_model.Inputs(malaria=2))["infection"]
                               ["malaria"], 1 + P.MALARIA_INFECTION[2])

    def test_a_step_from_before_step_3_reads_no_malaria(self):
        """A census whose last step predates calibration step 3 holds no te_dg_in_mal: the factor reads 1 until its next
        step, so the hover still multiplies to the row."""
        inp = demographics_model.Inputs(sol=7, literacy=0.1, malaria=2)
        eng = self._eng(inp)
        del eng.vars["te_dg_in_mal"], eng.vars["te_dg_in_malc"]
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_f_infection_malaria")), 1.0)

    def test_the_store_takes_the_malaria_level_and_its_control(self):
        inp = demographics_model.Inputs(sol=7, literacy=0.1, malaria=1, mods={P.MALARIA_CONTROL_TYPE: 1.5})
        eng = _Engine(_mod_fixtures(inp))
        eng.vars.update(te_dg_sol=7.0, te_dg_lit=0.1)
        eng.call("te_demog_cause_inputs_store")
        self.assertEqual((eng.vars["te_dg_in_mal"], eng.vars["te_dg_in_malc"]), (1.0, 1.0), "the control is 0 to 1")

    def test_the_safety_factor_cuts_work_and_accidents_past_the_laws_factor(self):
        """Modern safety (2026-10-16): 1 - the stored share, at most SAFETY_MAX, multiplying the laws factor, which since
        2026-10-20 has no floor but 0 (it was 0.2: the case's -0.9 read 0.2); a step from before it stored no share and
        reads 1, so the hover still multiplies to the row."""
        inp = demographics_model.Inputs(sol=40, literacy=1.0, mods=dict(self.CASES[-1]))
        eng = self._eng(inp)
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_f_work_laws")), 0.1)
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_f_work_safety")), 1 - P.SAFETY_MAX)
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_mult_work")), 0.1 * (1 - P.SAFETY_MAX),
                               places=9)
        del eng.vars["te_dg_in_saf_work"], eng.vars["te_dg_in_saf_ext"]
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_f_work_safety")), 1.0)
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_f_external_safety")), 1.0)

    def test_a_laws_factor_stops_at_zero(self):
        """The natural bound (owner, 2026-10-20): lines summing below -1 give a factor of 0, never a negative rate, in the
        script as in the model."""
        inp = demographics_model.Inputs(sol=40, literacy=1.0, mods={"state_work_mortality_mult": -1.4,
                                                                    "state_external_mortality_mult": -0.95})
        eng = self._eng(inp)
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_f_work_laws")), 0.0)
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_f_external_laws")), 0.05)
        factors = demographics_model.cause_factors(inp)
        self.assertEqual(factors["work"]["laws"], 0.0)
        self.assertAlmostEqual(factors["external"]["laws"], 0.05)

    def test_the_store_takes_the_safety_shares(self):
        inp = demographics_model.Inputs(sol=40, literacy=1.0, mods=dict(self.CASES[-1]))
        eng = _Engine(_mod_fixtures(inp))
        eng.vars.update(te_dg_sol=40.0, te_dg_lit=1.0)
        eng.call("te_demog_cause_inputs_store")
        self.assertEqual((eng.vars["te_dg_in_saf_work"], eng.vars["te_dg_in_saf_ext"]), (P.SAFETY_MAX, 0.2),
                         "each share is 0 to SAFETY_MAX")

    def test_a_walk_between_steps_moves_no_factor(self):
        """The reviews of #916 (logic M2, panel M4): a walk without a step (a second pulse in a year, the console's
        benchmark, option c) rewrites te_dg_sol and te_dg_lit while te_dg_m_* stays; the hover's factors read the
        step's own copies, so they still multiply to the row."""
        inp = demographics_model.Inputs(sol=6.5, literacy=0.2, mods=dict(self.CASES[2]))
        eng = self._eng(inp)
        before = {f: eng.value(eng._tree(eng.values, f"te_demog_f_infection_{f}")) for f in ("sol", "poverty",
                                                                                               "literacy")}
        before["chronic_sol"] = eng.value(eng._tree(eng.values, "te_demog_f_chronic_sol"))
        eng.vars.update(te_dg_sol=30.0, te_dg_lit=0.9)
        after = {f: eng.value(eng._tree(eng.values, f"te_demog_f_infection_{f}")) for f in ("sol", "poverty",
                                                                                             "literacy")}
        after["chronic_sol"] = eng.value(eng._tree(eng.values, "te_demog_f_chronic_sol"))
        self.assertEqual(after, before)

    def test_crowding_needs_both_the_modifier_and_the_stored_multiplier(self):
        # a save from before the stored multiplier (the modifier alone), and a variable outliving its modifier,
        # store no crowding (review I1 of the crowding term)
        for label, modifier, variable in (("both", True, True), ("modifier only", True, False),
                                          ("variable only", False, True)):
            eng = _Engine(_mod_fixtures(demographics_model.Inputs()))
            eng.vars.update(te_dg_sol=8.0, te_dg_lit=0.0)
            if modifier:
                eng.modifiers["migration_crowding"] = 1.5
            if variable:
                eng.vars["migration_crowding_mult_applied"] = 1.5
            eng.call("te_demog_cause_inputs_store")
            want = 1.5 * P.MIGRATION_CROWDING_PULL_PER_MULT if label == "both" else 0.0
            with self.subTest(label):
                self.assertAlmostEqual(eng.vars["te_dg_in_crowd"], want, places=9)

    def test_crowding_matches_the_model(self):
        # the census stores the multiplier the crowding refresh applied (migration_crowding_mult_applied), the
        # harness reads the modifier's multiplier in the save: the same yearly figure. Slight (-3.8% attraction), 10x
        # density (-45%), past the cap, and a state the refresh has not reached (no modifier, no variable)
        for mult in (0.378, 4.5, 14.5, None):
            crowding = 0.0 if mult is None else P.MIGRATION_CROWDING_PULL_PER_MULT * mult
            inp = demographics_model.Inputs(sol=12, literacy=0.3, crowding=crowding)
            eng = _Engine(_mod_fixtures(inp))
            eng.vars.update(te_dg_sol=12.0, te_dg_lit=0.3)
            if mult is not None:
                eng.modifiers["migration_crowding"] = mult
                eng.vars["migration_crowding_mult_applied"] = mult
            eng.call("te_demog_cause_inputs_store")
            eng.call("te_demog_medicine_at_target")
            with self.subTest(mult=mult):
                got = eng.value(eng._tree(eng.values, "te_demog_mult_infection"))
                self.assertAlmostEqual(got, demographics_model.cause_multipliers(inp)["infection"], places=9)

    def test_crowdings_pull_per_multiplier_is_the_modifiers(self):
        # "infection rises by the share attraction falls" holds only while the two agree: a retuned
        # migration_crowding would otherwise leave the census reading the old figure
        body = _raw_blocks([ROOT / "common" / "static_modifiers" / "extra_modifiers.txt"])["migration_crowding"]
        pull = float(re.search(r"state_migration_pull_mult = (-?[0-9.]+)", body).group(1))
        self.assertAlmostEqual(P.MIGRATION_CROWDING_PULL_PER_MULT, -pull)

    def test_the_crowding_refresh_stores_the_multiplier_it_applies(self):
        refresh = _raw_blocks([ROOT / "common" / "scripted_effects" / "extra_effects.txt"])
        refresh = {"te_update_migration_crowding_modifier": refresh["te_update_migration_crowding_modifier"]}
        eng = _Engine({"migration_crowding_mult": 0.378}, effects=refresh)
        eng.modifiers["migration_crowding"] = 0.2
        eng.vars["migration_crowding_mult_applied"] = 0.2
        eng.call("te_update_migration_crowding_modifier")
        self.assertEqual(eng.modifiers, {"migration_crowding": 0.378})
        self.assertEqual(eng.vars["migration_crowding_mult_applied"], 0.378)
        eng.fixtures["migration_crowding_mult"] = 0.0
        eng.call("te_update_migration_crowding_modifier")
        self.assertEqual(eng.modifiers, {})
        self.assertNotIn("migration_crowding_mult_applied", eng.vars)


class TestMedicineDriftScript(unittest.TestCase):
    """te_demog_medicine_drift and te_demog_medicine_at_target (generated) against demographics_model.medicine_drift."""

    INP = demographics_model.Inputs(mods={P.ACCESS_TYPE: 0.3, P.TREATMENT_TYPE["infection"]: 0.4,
                                          P.TREATMENT_TYPE["maternal"]: 0.35, P.TREATMENT_TYPE["chronic"]: 0.1})
    VARS = {"access": "te_dg_acc", **{c: f"te_dg_trt_{P.CAUSE_SHORT[c]}" for c in P.MEDICINE_CAUSES}}

    def _read(self, eng):
        return {k: eng.vars[v] for k, v in self.VARS.items()}

    def test_a_state_without_medicine_starts_at_its_targets(self):
        eng = _Engine(_mod_fixtures(self.INP))
        eng.call("te_demog_medicine_drift")
        for k, v in self._read(eng).items():
            self.assertAlmostEqual(v, demographics_model.medicine_targets(self.INP)[k], places=9, msg=k)

    def test_a_seed_sets_the_targets(self):
        eng = _Engine(_mod_fixtures(self.INP))
        eng.vars.update(te_dg_acc=0.9, te_dg_trt_inf=0.9, te_dg_trt_mat=0.9, te_dg_trt_chr=0.9)
        eng.call("te_demog_medicine_at_target")
        self.assertEqual(self._read(eng), demographics_model.medicine_targets(self.INP))

    def test_each_step_closes_its_share_of_the_gap(self):
        prev = {"access": 0.4, "infection": 0.0, "maternal": 0.6, "chronic": 0.1}
        for spread in (0.0, 0.15, 0.3, 5.0):
            inp = dataclasses.replace(self.INP, mods={**self.INP.mods, P.DIFFUSION_TYPE: spread})
            eng = _Engine(_mod_fixtures(inp))
            eng.vars.update({self.VARS[k]: v for k, v in prev.items()})
            eng.call("te_demog_medicine_drift")
            want = demographics_model.medicine_drift(prev, inp)
            for k, v in self._read(eng).items():
                with self.subTest(spread=spread, value=k):
                    self.assertAlmostEqual(v, want[k], places=9)
                    lo, hi = sorted((prev[k], demographics_model.medicine_targets(inp)[k]))
                    self.assertTrue(lo - 1e-9 <= v <= hi + 1e-9, "never overshoots")

    def test_near_its_target_a_value_takes_it(self):
        target = demographics_model.medicine_targets(self.INP)["access"]
        eng = _Engine(_mod_fixtures(self.INP))
        eng.vars.update(te_dg_acc=target - 0.005, te_dg_trt_inf=0.4, te_dg_trt_mat=0.35, te_dg_trt_chr=0.1)
        eng.call("te_demog_medicine_drift")
        self.assertAlmostEqual(eng.vars["te_dg_acc"], target, places=12)


class TestMeansScript(unittest.TestCase):
    """te_demog_means (generated) against demographics_model.means, with the fertility types' reads as
    fixtures: the tier's clamp before literacy, the shift after it, the cap and the floor (stage 2's
    Review Focus 1, 3 and 4). In game the one read of state_fertility_means_add carries both the laws'
    lines (mods) and static modifiers such as Family Limitation (means_add)."""

    def test_script_matches_the_model(self):
        for contra in (-1.0, 0.0, 0.2, 0.45, 0.65, 2.0):
            for shift in (-2.0, -0.2, 0.0, 0.1, 1.0):
                for static in (0.0, P.FAMILY_LIMITATION_MEANS):
                    for lit in (0.0, 0.35, 1.0):
                        inp = demographics_model.Inputs(
                            literacy=lit, mods={P.CONTRACEPTION_TYPE: contra, P.MEANS_SHIFT_TYPE: shift},
                            means_add=static)
                        eng = _Engine({f"modifier:{P.CONTRACEPTION_TYPE}": contra,
                                       f"modifier:{P.MEANS_SHIFT_TYPE}": shift + static})
                        eng.vars["te_dg_lit"] = lit
                        with self.subTest(contra=contra, shift=shift, static=static, lit=lit):
                            got = eng.value(eng._tree(eng.values, "te_demog_means"))
                            self.assertAlmostEqual(got, demographics_model.means(inp), places=9)


class TestGiniBands(unittest.TestCase):
    """The generated wealth-band effects (§4.1, wealth bands): each pop's band and income, the
    store, and the formula. Since 2026-10-10 (high wealth) the bands run five levels wide to the top
    level, income is uncapped and summed in units of P.GINI_INCOME_UNIT, and a state stores only the
    bands it has people in, beside its layout (te_dg_gini_layout)."""

    @classmethod
    def setUpClass(cls):
        import demographics_harness
        cls.costs = demographics_harness.buy_package_costs()

    def walk(self, pops, truncate=False):
        """[(people, wealth)] through the walk's sums: {band: (people, income)} for the bands hit."""
        eng = _Engine({}, truncate=truncate)
        eng.call("te_demog_gini_band_init")
        for size, wealth in pops:
            eng.fixtures.update(total_size=float(size), wealth=float(wealth))
            eng.call("te_demog_gini_band_add")
        return {k: (eng.locals[f"te_dg_w_gn{k}"], eng.locals[f"te_dg_w_gy{k}"])
                for k in range(1, P.GINI_BANDS + 1) if eng.locals[f"te_dg_w_gn{k}"]}

    def income(self, size, wealth):
        """the stand-in's income for a pop, in the census's units"""
        return size * demographics_model.stand_in_income(wealth, self.costs) / P.GINI_INCOME_UNIT

    def test_every_wealth_lands_in_the_models_band(self):
        # Review Focus 2, over every level the mod's packages have (NUM_WEALTH_LEVELS = 200)
        for wealth in range(0, P.GINI_TOP_WEALTH + 1):
            hit = self.walk([(10, wealth)])
            self.assertEqual(list(hit), [demographics_model.wealth_band(wealth)], wealth)

    def test_each_pop_adds_the_stand_in_income_in_its_units(self):
        for wealth in range(0, P.GINI_TOP_WEALTH + 1):
            (n, y), = self.walk([(37, wealth)]).values()
            self.assertEqual(n, 37.0)
            self.assertAlmostEqual(y / self.income(37, wealth), 1.0, places=6, msg=str(wealth))

    def test_income_is_not_capped_at_60(self):
        # the cap counted a wealth-109 pop as wealth 60, a 400th of its spending
        per_head = {w: self.walk([(1e5, w)])[demographics_model.wealth_band(w)][1] for w in (60, 61, 100, 150, 200)}
        self.assertGreater(per_head[61], per_head[60])
        self.assertAlmostEqual(per_head[100] / per_head[60], self.costs[100] / self.costs[60], places=4)
        self.assertAlmostEqual(per_head[200] * P.GINI_INCOME_UNIT / 1e5, self.costs[200] / 100, places=2)
        # a wealth above the top level (none exists) is held at the top level's spending
        self.assertEqual(self.walk([(1e5, 260)])[P.GINI_BANDS][1], per_head[200])

    def test_the_old_income_value_is_gone(self):
        # the leaf of the band tree computes the income: no second chain of wealth tests per pop
        for path in DEMOG_FILES:
            self.assertNotIn("te_demog_pop_income", _text(path), path.name)

    def gini(self, bands, truncate=False):
        eng = _Engine({}, truncate=truncate)
        for k in range(1, P.GINI_BANDS + 1):
            n, y = bands.get(k, (0.0, 0.0))
            eng.locals[f"te_dg_g_n{k}"], eng.locals[f"te_dg_g_y{k}"] = float(n), float(y)
        eng.call("te_demog_gini_from_locals")
        return eng.vars["te_dg_gini"]

    def test_the_formula_matches_the_model(self):
        rng = random.Random(11)
        for _ in range(200):
            bands, per_head = {}, 0.0
            for k in range(1, P.GINI_BANDS + 1):
                per_head += rng.uniform(0.0, 30.0)          # bands follow income
                n = rng.choice([0, rng.randint(1, 200000)])
                bands[k] = (n, n * per_head)
            want = demographics_model.shown_gini(demographics_model.grouped_gini(list(bands.values())))
            self.assertAlmostEqual(self.gini(bands), want, places=9)

    def test_nobody_or_no_income_or_one_band_shows_the_floor(self):
        # Review Focus 3 and 4: a computed Gini of 0, shown as 1 - X
        floor = 1 - P.GINI_SHOWN_EQUALITY
        self.assertAlmostEqual(self.gini({}), floor, places=9)
        self.assertAlmostEqual(self.gini({1: (500, 0), 2: (20, 0)}), floor, places=9)
        self.assertAlmostEqual(self.gini({7: (1000, 4321)}), floor, places=9)

    def through_the_script(self, pops, truncate):
        """[(people, wealth)] walked, then the formula over the bands it filled: the shown Gini"""
        return self.gini(self.walk(pops, truncate=truncate), truncate=truncate)

    def by_the_model(self, pops):
        bands = {}
        for size, wealth in pops:
            k = demographics_model.wealth_band(wealth)
            n, y = bands.get(k, (0.0, 0.0))
            bands[k] = (n + size, y + self.income(size, wealth))
        return demographics_model.shown_gini(demographics_model.grouped_gini(list(bands.values())))

    def test_a_china_sized_country_keeps_its_precision(self):
        # Review Focus 5: 4e8 people, most of them poor, with the engine's fixed point
        pops = [(3.2e8, 3), (6e7, 9), (2e7, 45), (1e6, 60), (2e5, 90)]
        self.assertAlmostEqual(self.through_the_script(pops, True), self.by_the_model(pops), places=4)

    def test_the_largest_country_at_the_top_level_fits_the_fixed_point(self):
        """Values are i64 x 1e-5, at most about 9.2e13 (_Engine asserts it under truncate). The fast run's
        whole world, 6.9e9 people, at wealth 200 (9.5e8 a head) in one country sums to 6.6e13 units. Each
        pop's people divide by the unit before they multiply: 1e9 x 9.5e8 would be 9.5e17."""
        pops = [(1.16e9, 200)] * 5 + [(1.1e9, 1)]
        got = self.through_the_script(pops, True)
        self.assertAlmostEqual(got, self.by_the_model(pops), places=4)
        y = self.walk([(6.9e9, 200)], truncate=True)[P.GINI_BANDS][1]
        self.assertAlmostEqual(y / self.income(6.9e9, 200), 1.0, places=6)
        self.assertLess(y, (2 ** 63 - 1) / 1e5)

    def test_a_small_poor_state_keeps_its_precision(self):
        """The census's smallest step of income is 1 a pop (1e-5 of the unit), cut toward zero: a pop of
        one person at wealth 3 (1.86) keeps 1, 46% less, and no pop is cut to 0 (wealth 1 is 1.51 a head).
        The cut takes more from poorer pops, so a small state usually reads slightly high: this one by
        0.0002. Across the 3,903 states of the 1836, 1887, 1953 and fast-run saves the largest miss is
        0.0021; only a state made of one-person pops goes further, 0.02-0.045 high (review of #867)."""
        pops = [(3 + 7 * i, i % 9) for i in range(40)] + [(12, 30), (2, 55)]
        self.assertAlmostEqual(self.through_the_script(pops, True), self.by_the_model(pops), delta=0.002)

    def test_an_1836_state_reads_as_before(self):
        """Below wealth 60 the bands and the stand-in's pieces are the old ones: only the units change,
        and a share does not depend on them."""
        pops = [(250_000, 2), (120_000, 4), (40_000, 7), (9_000, 13), (3_000, 22), (800, 38), (120, 47)]
        old = {}
        for n, w in pops:
            k = demographics_model.wealth_band(w)
            a, b = old.get(k, (0.0, 0.0))
            old[k] = (a + n, b + n * demographics_model.stand_in_income(w, self.costs))   # old units
        want = demographics_model.shown_gini(demographics_model.grouped_gini(list(old.values())))
        self.assertAlmostEqual(self.through_the_script(pops, True), want, delta=0.0005)

    def test_the_store_keeps_the_bands_with_people_and_marks_the_layout(self):
        eng = _Engine({})
        bands = {2: (9e5, 1.4), 3: (2e5, 0.5), 13: (4e3, 0.37), 30: (12.0, 0.5)}
        eng.call("te_demog_gini_band_init")
        for k, (n, y) in bands.items():
            eng.locals[f"te_dg_w_gn{k}"], eng.locals[f"te_dg_w_gy{k}"] = n, y
        # a save from before: 14 bands, every one stored, and the strata sums before them
        old = ("te_dg_n_lo", "te_dg_n_mi", "te_dg_n_up", "te_dg_y_lo", "te_dg_y_mi", "te_dg_y_up")
        eng.vars.update({name: 1.0 for name in old})
        eng.vars.update({f"te_dg_g{s}{k}": 5.0 for k in range(1, 15) for s in "ny"})
        eng.call("te_demog_gini_band_store")
        self.assertEqual(eng.vars["te_dg_gini_layout"], P.GINI_LAYOUT)
        for k in range(1, P.GINI_BANDS + 1):
            if k in bands:
                self.assertEqual((eng.vars[f"te_dg_gn{k}"], eng.vars[f"te_dg_gy{k}"]), bands[k], k)
            else:
                self.assertNotIn(f"te_dg_gn{k}", eng.vars, "an empty band is not stored: save size")
                self.assertNotIn(f"te_dg_gy{k}", eng.vars)
        for name in old:
            self.assertNotIn(name, eng.vars)
        eng.locals.clear()
        eng.call("te_demog_state_gini")
        want = demographics_model.shown_gini(demographics_model.grouped_gini(list(bands.values())))
        self.assertAlmostEqual(eng.vars["te_dg_gini"], want, places=9)

    def test_the_layout_marker_is_the_params(self):
        store = _block(_text(GENERATED_EFFECTS), "te_demog_gini_band_store")
        self.assertIn(f"set_variable = {{ name = te_dg_gini_layout value = {P.GINI_LAYOUT} }}", store)
        add = _block(_text(GENERATED_EFFECTS), "te_demog_gini_band_add_state")
        self.assertIn(f"var:te_dg_gini_layout = {P.GINI_LAYOUT}", add)

    def test_every_band_read_is_guarded_by_has_variable(self):
        """A state stores only the bands it has people in, so every read of one sits inside an if or
        else_if whose limit asks has_variable for that band (an else, or a guard on another band, is
        no guard). Walks every scripted effect and script value of the census, not only the two readers."""
        band = re.compile(r"var:te_dg_g([ny])(\d+)")

        def reads(items, guards):
            for key, _, arg in items:
                if band.fullmatch(key):
                    yield key, guards
                if isinstance(arg, str):
                    if band.fullmatch(arg):
                        yield arg, guards
                    continue
                inner = guards
                if key in ("if", "else_if"):
                    inner = guards | {v for k, _, v in _find_all(arg, "limit") if k == "has_variable"}
                    yield from reads(_find_all(arg, "limit"), guards)
                    arg = [i for i in arg if i[0] != "limit"]
                yield from reads(arg, inner)

        def _find_all(items, key):
            return [x for k, _, v in items if k == key for x in v]

        found = {}
        for path in DEMOG_FILES:
            for name, _, body in _parse_script(_text(path)):
                if not isinstance(body, list):
                    continue
                for read, guards in reads(body, frozenset()):
                    want = "te_dg_gn" + band.fullmatch(read).group(2)
                    self.assertIn(want, guards, f"{path.name}: {name} reads {read} outside has_variable = {want}")
                    found.setdefault(name, set()).add(read)
        every = {f"var:te_dg_g{s}{k}" for k in range(1, P.GINI_BANDS + 1) for s in "ny"}
        self.assertEqual(found.get("te_demog_gini_band_load"), every)
        self.assertEqual(found.get("te_demog_gini_band_add_state"), every)
        # phase 3: longevity care's access and the wealth slope read the people by band (te_demog_lx_access,
        # te_demog_lx_wealth_slope, generated)
        for name in ("te_demog_lx_access", "te_demog_lx_wealth_slope"):
            self.assertEqual(found.get(name), {f"var:te_dg_gn{k}" for k in range(1, P.GINI_BANDS + 1)}, name)
        self.assertEqual(set(found), {"te_demog_gini_band_load", "te_demog_gini_band_add_state", "te_demog_lx_access",
                                      "te_demog_lx_wealth_slope"}, "no other reader of the stored bands")

    def test_a_near_total_inequality_shows_near_1_without_a_cap(self):
        bands = {1: (99, 0.0001), P.GINI_BANDS: (1, 1000)}
        want = demographics_model.shown_gini(demographics_model.grouped_gini(list(bands.values())))
        self.assertGreater(want, 0.98)
        self.assertAlmostEqual(self.gini(bands), want, places=9)

    def test_the_constants_of_the_old_map_are_gone(self):
        self.assertNotIn("te_demog_k_gini", _text(GENERATED_VALUES))


class TestOldAgeScript(unittest.TestCase):
    """te_demog_old_age_pass against demographics_model.old_age (phase 2 step 1)."""

    def test_seed_stores_the_models_threshold(self):
        inp = demographics_model.Inputs(sol=14, literacy=0.35, urban_share=0.2,
                                        techs=frozenset({"medical_degrees"}))
        eng = _engine_for(inp, 1836, 250000.0)
        eng.call("te_demog_seed")
        qf, qm, _ = demographics_model.group_rates(inp)
        self.assertAlmostEqual(eng.vars["te_dg_old_age"], demographics_model.old_age(qf, qm), delta=0.01)


class TestSlotBirthsScript(unittest.TestCase):
    """te_demog_slot_births against demographics_model.slot_births, with two schedules (not shipped)."""

    def test_two_schedules_in_script_match_the_model(self):
        other = {15: 10000, 20: 30000, 25: 30000, 30: 20000, 35: 7000, 40: 2500, 45: 500}
        with unittest.mock.patch.object(P, "ASFR_UNPLANNED_SHAPE", other):
            text = re.sub(r"#[^\n]*", "", gen_demographics.render_effects())
            g = P.group_of(27)
            eng = _Engine({}, effects={n: _block(text, n) for n in ("te_demog_slot_births", "te_demog_enter_group")})
            eng.locals.update(te_dg_g=float(g), te_dg_f=1000.0, te_dg_tfr=4.0, te_dg_sh_pl=0.25, te_dg_sh_un=0.75,
                              te_dg_m_inf=1.0, te_dg_inf_ad=1.0, te_dg_m_work_f=1.0, te_dg_m_work_m=1.0,
                              te_dg_m_ext=1.0, te_dg_m_chr=1.0)
            eng.call("te_demog_enter_group")
            eng.call("te_demog_slot_births")
            want = demographics_model.slot_births(1000.0, 27, 27, 4.0, 0.25)
        self.assertAlmostEqual(eng.locals["te_dg_b"], want)


class TestPensionAge(unittest.TestCase):
    """The pension age (phase 2 step 1; the design §1.2): one country variable, the Standard position's age under Old
    Age Pension, none otherwise; every reader goes through te_demog_pension_age."""

    def _country(self, oap, held=None):
        eng = _Engine({}, triggers={"te_demog_has_pension_law": oap})
        if held is not None:
            eng.vars["te_dg_pension_age"] = held
        eng.call("te_demog_pension_age_refresh")
        return eng

    def test_the_variable_follows_the_law(self):
        self.assertEqual(self._country(True).vars["te_dg_pension_age"], P.PENSION_AGE["standard"])
        self.assertNotIn("te_dg_pension_age", self._country(False, held=65.0).vars)
        self.assertNotIn("te_dg_pension_age", self._country(False).vars)

    def test_the_hooks(self):
        effects = _text(EFFECTS)
        for caller in ("te_demog_country_game_start", "te_demog_country_yearly"):
            self.assertIn("te_demog_pension_age_refresh = yes", _block(effects, caller), caller)
        on_actions = _text(DEMOG_ON_ACTIONS)
        self.assertIn("te_demog_pension_law_on_action", _block(on_actions, "on_law_activated"))
        self.assertIn("te_demog_pension_age_refresh = yes", _block(on_actions, "te_demog_pension_law_on_action"))

    def test_no_age_is_compared_with_a_pension_age_literal(self):
        """The design §1.2: nothing compares an age with 60, 65 or 70; the sweep reads te_dg_wa_end. (The Gini's
        `wealth > 65` and the war window's 18-40 are other numbers.)"""
        for path in DEMOG_FILES:
            code = re.sub(r"#[^\n]*", "", _text(path))
            self.assertIsNone(re.search(r"local_var:te_dg_(age|ab|r)\s*(>=|<=|<|>|=)\s*(60|65|70)\b", code), path.name)


class TestConsequencesScript(unittest.TestCase):
    """Phase 2 step 4 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §4): the four state
    modifiers' refresh (te_demog_consequence_effects.txt) against demographics_model, under Full and outside it."""

    def _state(self, fam=11000.0, people=100000.0, balance=94.0, youth=(8000.0, 8100.0, 7900.0, 7950.0),
               unemployment=0.0, full=True):
        # the unemployment the census stored (te_dg_unemp, te_demog_work_walk_store: te_state_unemployment_share at the
        # walk), the share of the workforce the model takes; the engine's state_unemployment_rate, a quarter of it in
        # 1836 (unemployment_rate_read), is read by nothing here
        eng = _Engine({"state_unemployment_rate": unemployment / 4, **_switch_fixtures()},
                      triggers={"te_demog_effects_run": full})
        eng.vars.update(te_dg_fam=fam, te_dg_faw=fam * 1.02, te_dg_people=people, te_dg_sex_balance=balance,
                        te_dg_bf4=youth[0], te_dg_bm4=youth[1], te_dg_bf5=youth[2], te_dg_bm5=youth[3],
                        te_dg_unemp=unemployment)
        return eng

    def test_full_applies_the_models_terms(self):
        """With the three effects held back (the switches off) and as if on."""
        for on in (False, True):
            with unittest.mock.patch.object(P, "SEX_BALANCE_EFFECTS", on), \
                    unittest.mock.patch.object(P, "CONSCRIPTION_EFFECTS", on), \
                    unittest.mock.patch.object(P, "YOUTH_BULGE_EFFECTS", on):
                self._full_cases(on)

    def _full_cases(self, on):
        cases = [dict(), dict(fam=7000.0, balance=82.0, unemployment=0.12),
                 dict(fam=16000.0, balance=135.0, youth=(11000.0, 11500.0, 11000.0, 11200.0), unemployment=0.25),
                 dict(fam=0.0, balance=150.0), dict(fam=50000.0, balance=60.0), dict(balance=72.0),
                 dict(balance=180.0, youth=(7500.0, 7500.0, 7500.0, 7500.0), unemployment=0.3)]
        for kw in cases:
            with self.subTest(on=on, **{k: v for k, v in kw.items() if k != "youth"}):
                eng = self._state(**kw)
                eng.call("te_demog_consequences_refresh")
                v = eng.vars
                term = demographics_model.conscription_term(v["te_dg_fam"], v["te_dg_people"])
                share = sum(kw.get("youth", (8000.0, 8100.0, 7900.0, 7950.0))) / v["te_dg_people"]
                y = demographics_model.youth_bulge(share, kw.get("unemployment", 0.0))
                self.assertAlmostEqual(v["te_dg_mc"], term, places=9)
                self.assertAlmostEqual(v["te_dg_yb"], y, places=9)
                want = {}
                applied, bulge = demographics_model.conscription_applied(term), demographics_model.youth_applied(y)
                if applied > 0:
                    want["te_demog_census_conscription_up"] = applied
                elif applied < 0:
                    want["te_demog_census_conscription_down"] = -applied
                if bulge > 0:
                    want["te_demog_census_youth_bulge"] = bulge
                # the modifiers' strengths: the extended curve past the reference (the 2026-10-22 effects design)
                fewer = demographics_model.sex_fewer_men_strength(v["te_dg_sex_balance"])
                more = demographics_model.sex_more_men_strength(v["te_dg_sex_balance"])
                if on:
                    self.assertAlmostEqual(fewer, DE.fewer_men(v["te_dg_sex_balance"]), places=9)
                    self.assertAlmostEqual(more, DE.more_men(v["te_dg_sex_balance"]), places=9)
                    self.assertAlmostEqual(y, DE.youth(share, kw.get("unemployment", 0.0)), places=9)
                if fewer > 0:
                    want["te_demog_census_fewer_men"] = fewer
                if more > 0:
                    want["te_demog_census_more_men"] = more
                self.assertEqual(set(eng.modifiers), set(want))
                for name, mult in want.items():
                    self.assertAlmostEqual(eng.modifiers[name], mult, places=9, msg=name)
                if not on:
                    # held back: T and y stored, nothing applied
                    self.assertEqual(eng.modifiers, {})

    @ALL_ON
    def test_the_conscription_term_has_no_ceiling(self):
        """Owner, 2026-10-16: the +0.25 cap is gone. A pool of half the people (T about 2.6) is stored and applied
        whole, by the script as by the model; only the -1 floor remains."""
        eng = self._state(fam=50000.0)
        eng.call("te_demog_consequences_refresh")
        want = demographics_model.conscription_term(50000.0, 100000.0)
        self.assertGreater(want, 2.0)
        self.assertAlmostEqual(eng.vars["te_dg_mc"], want, places=4)
        self.assertAlmostEqual(eng.modifiers["te_demog_census_conscription_up"], want, places=4)
        self.assertNotIn("te_demog_conscription_down", eng.modifiers)
        eng = self._state(fam=0.0)
        eng.call("te_demog_consequences_refresh")
        self.assertAlmostEqual(eng.vars["te_dg_mc"], -1.0)
        for text in (_text(CONSEQ_VALUES), _text(GENERATED_VALUES)):
            self.assertNotIn("te_demog_k_conscription_max", text)

    def test_the_conscription_pair_is_hidden(self):
        """Owner, 2026-10-16: like the census's births and deaths terms, the pair takes the mod's invisible icon, so
        the state panel's name filter and gui_state_hidden_modifier_count hide it (test_hidden_state_modifiers.py
        keeps those in step); its name still heads the conscription breakdown."""
        mods = _raw_blocks([CONSEQ_MODIFIERS])
        for name in ("te_demog_census_conscription_up", "te_demog_census_conscription_down"):
            self.assertIn("icon = gfx/interface/icons/timed_modifier_icons/modifier_system.dds", mods[name], name)
        for name in ("te_demog_census_youth_bulge", "te_demog_census_fewer_men", "te_demog_census_more_men"):
            self.assertNotIn("modifier_system.dds", mods[name], name)
        panel = _text(ROOT / "gui" / "states_panel.gui")
        hidden = _block(_text(ROOT / "common" / "script_values" / "gui_chart_script_values.txt"),
                        "gui_state_hidden_modifier_count")
        loc = "".join(_text(p) for p in sorted((ROOT / "localization" / "english").glob("*.yml")))
        for name in ("te_demog_census_conscription_up", "te_demog_census_conscription_down"):
            self.assertEqual(panel.count(f"Localize('{name}')"), 2, name)
            self.assertIn(f"has_modifier = {name}", hidden)
            self.assertIn(f' {name}:0 "Census: Fighting-Age Men"', loc)

    @ALL_ON
    def test_a_change_of_sign_swaps_the_pair(self):
        eng = self._state(fam=7000.0)
        eng.call("te_demog_consequences_refresh")
        self.assertIn("te_demog_census_conscription_down", eng.modifiers)
        eng.vars["te_dg_fam"] = 15500.0
        eng.call("te_demog_consequences_refresh")
        self.assertIn("te_demog_census_conscription_up", eng.modifiers)
        self.assertNotIn("te_demog_census_conscription_down", eng.modifiers)

    @ALL_ON
    def test_outside_full_everything_goes(self):
        eng = self._state(fam=7000.0, balance=70.0, youth=(11000.0, 11500.0, 11000.0, 11200.0), unemployment=0.3)
        eng.call("te_demog_consequences_refresh")
        self.assertEqual(len(eng.modifiers), 3)
        eng.trigger_fixtures["te_demog_effects_run"] = False
        eng.call("te_demog_consequences_refresh")
        self.assertEqual(eng.modifiers, {})
        self.assertNotIn("te_dg_mc", eng.vars)
        self.assertNotIn("te_dg_yb", eng.vars)
        # the panel still shows what Full would do: the term and the bulge from the census and the unemployment it read
        self.assertLess(eng.value(eng._tree(eng.values, "te_demog_conscription_term")), 0)
        self.assertGreater(eng.value(eng._tree(eng.values, "te_demog_youth_bulge_shown")), 0)
        self.assertAlmostEqual(eng.vars["te_dg_unemp"], 0.3)

    def test_the_panel_never_reads_unemployment_live(self):
        """2026-10-16: read from a scripted GUI, state_unemployment_rate is none. The state subtab's Youth row gate
        (te_demog_state_youth_sgui) read it through te_demog_youth_bulge_shown, logged 'Got value of type none'
        thousands of times a session and never showed. The census stores its read (te_dg_unemp) under both settings,
        and everything the row reads goes through that."""
        values = _raw_blocks([CONSEQ_VALUES, GENERATED_VALUES])

        def live(name, seen):
            if name in seen or name not in values:
                return False
            seen.add(name)
            body = values[name]
            return "state_unemployment_rate" in body or any(live(n, seen) for n in re.findall(r"\b\w+\b", body))

        loc = "".join(_text(p) for p in sorted((ROOT / "localization" / "english").glob("*.yml")))
        row = "".join(re.search(rf"^ {key}:0 .*$", loc, re.M).group(0)
                      for key in ("te_demog_st_youth_tt", "te_demog_st_youth_effects", "te_demog_st_youth_value"))
        gate = _raw_blocks([SGUIS])["te_demog_state_youth_sgui"]
        names = set(re.findall(r"\bte_demog_\w+", gate)) | set(re.findall(r"ScriptValue\('(\w+)'\)", row))
        self.assertIn("te_demog_youth_bulge_shown", names)
        for name in sorted(names):
            self.assertFalse(live(name, set()), name)
        # the walk stores it under the cohorts, both settings (2026-10-17: the shared conversion from an effect, beside
        # the walk's own count), and the refresh doesn't write it
        refresh = _raw_blocks([CONSEQ_EFFECTS])["te_demog_consequences_refresh"]
        self.assertNotIn("name = te_dg_unemp", refresh)
        store = _raw_blocks([EFFECTS])["te_demog_work_walk_store"]
        self.assertIn("set_variable = { name = te_dg_unemp value = te_state_unemployment_share }", store)
        self.assertIn("set_variable = { name = te_dg_unemp_walk value = { value = local_var:te_dg_w_un divide = "
                      "{ value = local_var:te_dg_w_wf min = 1 } } }", store)

    def test_nothing_in_the_census_reads_the_engines_unemployment(self):
        """unemployment_rate_read (2026-10-17): state_unemployment_rate read 0.048 where the pops' share was 0.195, the
        idle workforce over all the people. The youth bulge, the wave, the pension AI and the panel read the shared
        conversion the census stores (te_state_unemployment_share, owner 2026-10-17); only the self-check reads the
        engine's figure here, through its wrapper."""
        readers = []
        for folder in ("script_values", "scripted_effects", "scripted_triggers"):
            for path in sorted((ROOT / "common" / folder).glob("te_demog*.txt")):
                if "state_unemployment_rate" in re.sub(r"#[^\n]*", "", _text(path)):
                    readers.append(path.name)
        self.assertEqual(readers, [])
        debug = re.sub(r"#[^\n]*", "", _text(ROOT / "common" / "script_values" / "te_debug_demog_values.txt"))
        self.assertEqual(re.findall(r"^(\w+) = \{[^\n]*state_unemployment_rate", debug, re.M),
                         ["te_debug_demog_unemp_engine_read"])

    def test_a_census_from_before_step_4_takes_nothing(self):
        eng = self._state()
        del eng.vars["te_dg_fam"]
        eng.vars["te_dg_mc"] = -0.2
        eng.modifiers["te_demog_census_conscription_down"] = 0.2
        eng.call("te_demog_consequences_refresh")
        self.assertEqual(eng.modifiers, {})
        self.assertNotIn("te_dg_mc", eng.vars)
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_fam_share")), 0)

    def test_the_1836_reference_state_takes_no_modifier(self):
        """A state at the 1836 world's pool, its young adults and balance: no modifier at all."""
        eng = self._state(fam=P.CONSCRIPTION_REF * 100000.0, balance=94.0)
        eng.call("te_demog_consequences_refresh")
        self.assertEqual(eng.modifiers, {})
        self.assertEqual((eng.vars["te_dg_mc"], eng.vars["te_dg_yb"]), (0, 0))

    @ALL_ON
    def test_no_modifier_below_the_cut_offs(self):
        """The review's Minor 2: when the effects apply, no conscription pair below |T| 0.01 and no youth modifier below
        y 0.02; the figures are still stored."""
        fam = P.CONSCRIPTION_REF * 100000.0 * (1 - P.CONSCRIPTION_CUT / 2)   # T = -0.005
        youth = 100000.0 * (P.YOUTH_FROM + P.YOUTH_SPAN * P.YOUTH_CUT / 2) / 4   # y = 0.01 at full unemployment
        # exactly full unemployment: past it the factor keeps rising (the 2026-10-22 effects design)
        eng = self._state(fam=fam, youth=(youth,) * 4, unemployment=P.YOUTH_UNEMPLOYMENT_FULL)
        eng.call("te_demog_consequences_refresh")
        self.assertAlmostEqual(eng.vars["te_dg_mc"], -P.CONSCRIPTION_CUT / 2, places=4)
        self.assertAlmostEqual(eng.vars["te_dg_yb"], P.YOUTH_CUT / 2, places=4)
        self.assertEqual(eng.modifiers, {})
        eng.vars["te_dg_fam"] = P.CONSCRIPTION_REF * 100000.0 * (1 - 2 * P.CONSCRIPTION_CUT)
        eng.call("te_demog_consequences_refresh")
        self.assertIn("te_demog_census_conscription_down", eng.modifiers)

    def test_the_switches_are_on(self):
        """The migrant booking (2026-10-12) turned the three effects on: the generated switches are 1."""
        self.assertEqual(_switch_fixtures(), {k: 1.0 for k in SWITCHES})
        for key in SWITCHES:
            self.assertEqual(_raw_blocks([GENERATED_VALUES])[key].strip(), "value = 1", key)

    @ALL_OFF
    def test_held_back_the_census_stores_the_figures_and_applies_nothing(self):
        """The three switches off (held back, as step 4 shipped): under Full T and y are stored for the panel."""
        self.assertEqual(_switch_fixtures(), {k: 0.0 for k in SWITCHES})
        eng = self._state(fam=7000.0, balance=60.0, youth=(11000.0, 11500.0, 11000.0, 11200.0), unemployment=0.3)
        eng.call("te_demog_consequences_refresh")
        self.assertEqual(eng.modifiers, {})
        self.assertLess(eng.vars["te_dg_mc"], -0.4)
        self.assertGreater(eng.vars["te_dg_yb"], 0.5)

    def test_the_sizes_are_the_params(self):
        mods = _raw_blocks([CONSEQ_MODIFIERS])
        want = {"te_demog_census_conscription_up": {"state_conscription_rate_mult": 1.0},
                "te_demog_census_conscription_down": {"state_conscription_rate_mult": -1.0},
                "te_demog_census_youth_bulge": {"state_radicals_from_political_movements_mult": P.YOUTH_RADICALS,
                                                "state_turmoil_effects_mult": P.YOUTH_TURMOIL},
                "te_demog_census_fewer_men": {"state_pop_support_movement_feminist_mult": P.SEX_FEMINIST},
                "te_demog_census_more_men": {"state_radicals_from_political_movements_mult": P.SEX_RADICALS,
                                             "state_turmoil_effects_mult": P.SEX_MORE_TURMOIL}}
        self.assertEqual(set(mods), set(want))
        for name, fields in want.items():
            got = {k: float(v) for k, v in re.findall(r"(state_\w+) = (-?[\d.]+)", mods[name])}
            self.assertEqual(got, fields, name)
            if name in DE.SIZES:
                self.assertEqual(got, DE.SIZES[name], name)
        values = _raw_blocks([CONSEQ_VALUES])
        for name, size in (("te_demog_sex_feminist_shown", P.SEX_FEMINIST), ("te_demog_sex_radicals_shown",
                           P.SEX_RADICALS), ("te_demog_sex_turmoil_shown", P.SEX_MORE_TURMOIL),
                           ("te_demog_youth_radicals_shown", P.YOUTH_RADICALS),
                           ("te_demog_youth_turmoil_shown", P.YOUTH_TURMOIL)):
            self.assertEqual(float(re.search(r"multiply = ([\d.]+)", values[name]).group(1)), size, name)

    def test_the_model_ramps_stay_on_0_1(self):
        """The women's rate and the panel read te_demog_sex_fewer_men: a model term, so it keeps its 0-1 clamp; only the
        modifiers read the extended strengths."""
        self.assertIn("max = 1", _raw_blocks([CONSEQ_VALUES])["te_demog_sex_fewer_men"])
        with unittest.mock.patch.object(P, "SEX_BALANCE_EFFECTS", True):
            self.assertAlmostEqual(demographics_model.sex_women_add(60.0), P.SEX_WOMEN_RATE)
            self.assertAlmostEqual(demographics_model.sex_fewer_men_strength(60.0), 2.0)

    def test_one_refresh_site_after_the_births_and_deaths_terms(self):
        effects = _raw_blocks([EFFECTS, FAST_EFFECTS, CONSEQ_EFFECTS])
        for caller, before in (("te_demog_state_yearly", "te_demog_rates_refresh = yes"),
                               ("te_demog_state_clock_step", "te_demog_fast_refresh_rates = yes")):
            body = effects[caller]
            self.assertLess(body.index(before), body.index("te_demog_consequences_refresh = yes"), caller)
        users = [name for name, body in effects.items() if "te_demog_consequences_apply = yes" in body]
        self.assertEqual(users, ["te_demog_consequences_refresh"])
        for path in DEMOG_FILES:
            if path != CONSEQ_EFFECTS:
                self.assertIsNone(re.search(r"add_modifier = \{ name = te_demog_census_(conscription|youth|fewer|more)",
                                            _text(path)), path.name)
        # the step stores the balance before its rates; a seed drops it before its own
        begin = effects["te_demog_step_begin"]
        self.assertLess(begin.index("te_demog_sex_births_store = yes"), begin.index("te_demog_prepare = yes"))
        seed = effects["te_demog_seed"]
        self.assertLess(seed.index("remove_variable = te_dg_sxb"), seed.index("te_demog_prepare = yes"))

    def test_a_country_with_no_pool_yet_shows_none(self):
        """The review's Minor 3: a country whose census states all come from before this build gets no pool figures
        (the row's pending text), not 0% (x0.00)."""
        states = [TestCountry.state(*args) for args in TestCountry.INPUTS]
        for st in states:
            del st["te_dg_fam"]
        eng = TestCountry().country(states)
        eng.vars.update(te_dg_fam_share=0.2, te_dg_fam_men=0.3)   # last year's, from a census since replaced
        eng.call("te_demog_country_census")
        self.assertNotIn("te_dg_fam_share", eng.vars)
        self.assertNotIn("te_dg_fam_men", eng.vars)

    def test_the_hovers_read_the_reference_and_mark_the_held_back(self):
        """The review's Minor 4 and 5: the 1836 reference is read from its constant, not written out; each effect's
        hover has its held-back line; none of this step's loc lines starts with a newline."""
        loc = {}
        for path in sorted((ROOT / "localization" / "english").glob("*_l_english.yml")):
            for m in re.finditer(r'^ (te_demog_[\w.]+):\d* "(.*)"$', _text(path), re.M):
                loc[m.group(1)] = m.group(2)
        self.assertIn("ScriptValue('te_demog_k_conscription_ref')", loc["te_demog_fam_rule"])
        self.assertNotIn("13.9", loc["te_demog_fam_rule"])
        for key, switch in (("te_demog_ov_fam_figures", "conscription"), ("te_demog_st_fam_figures", "conscription"),
                            ("te_demog_ov_youth_tt", "youth"), ("te_demog_st_youth_tt", "youth"),
                            ("te_demog_ov_sex_tt", "sex"), ("te_demog_st_sex_tt", "sex")):
            self.assertIn(f"ScriptValue('te_demog_k_{switch}_effects')", loc[key], key)
        step4 = re.compile(r"fam|youth|sex|conscription|fewer_men|more_men")   # this step's keys (other steps' aren't checked)
        for key, text in loc.items():
            if step4.search(key):
                self.assertFalse(text.startswith("\\n"), key)

    def test_the_country_figures(self):
        states = [TestCountry.state(*args) for args in TestCountry.INPUTS]
        states[0]["te_dg_yb"] = 0.3
        del states[2]["te_dg_fam"]                    # a census from before step 4
        eng = TestCountry().country(states)
        eng.call("te_demog_country_census")
        fam = states[0]["te_dg_fam"] + states[1]["te_dg_fam"]
        people = states[0]["te_dg_people"] + states[1]["te_dg_people"]
        men = sum(eng.vars[f"te_dg_cbm{b}"] for b in range(18))
        self.assertAlmostEqual(eng.vars["te_dg_fam_share"], fam / people, places=9)
        self.assertAlmostEqual(eng.vars["te_dg_fam_men"], fam / men, places=9)
        self.assertEqual(eng.vars["te_dg_yb_n"], 1)

    def test_the_self_checks_are_wired(self):
        """Owner, 2026-10-12: once a game each (a global flag), the conscription check reading before the add and
        judged a week later (te_debug_demog.30), the unemployment check where the census runs."""
        refresh = _raw_blocks([CONSEQ_EFFECTS])["te_demog_consequences_refresh"]
        self.assertLess(refresh.index("te_debug_demog_conscription_selfcheck_start = yes"),
                        refresh.index("te_demog_consequences_apply = yes"))
        self.assertIn("te_debug_demog_unemployment_selfcheck = yes", refresh)
        debug = _raw_blocks([ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"])
        start = debug["te_debug_demog_conscription_selfcheck_start"]
        for line in ("te_demog_k_conscription_effects > 0",   # held back, it never arms (no false BROKEN)
                     "te_demog_conscription_size >= te_demog_k_conscription_cut",
                     "NOT = { has_global_variable = te_demog_selfcheck_consc_done }",
                     "set_global_variable = { name = te_demog_selfcheck_consc_done value = yes }",
                     "NOT = { has_modifier = te_demog_census_conscription_up }",
                     "NOT = { has_modifier = te_demog_census_conscription_down }",
                     "trigger_event = { id = te_debug_demog.30 days = 7 }"):
            self.assertIn(line, start)
        unemp = debug["te_debug_demog_unemployment_selfcheck"]
        for line in ("te_demog_cohorts_run = yes", "NOT = { has_global_variable = te_demog_selfcheck_unemp_done }",
                     "TE_SELF_CHECK OK unemployment_rate_read", "TE_SELF_CHECK BROKEN unemployment_rate_read"):
            self.assertIn(line, unemp)
        events = _text(ROOT / "events" / "te_debug_demog_events.txt")
        check = _block(events, "te_debug_demog.30")
        self.assertIn("TE_SELF_CHECK OK conscription_term_read", check)
        self.assertIn("TE_SELF_CHECK BROKEN conscription_term_read", check)
        self.assertIn("name = te_debug_demog.1.t_opt", _block(events, "te_debug_demog.1"))


if __name__ == "__main__":
    unittest.main()
