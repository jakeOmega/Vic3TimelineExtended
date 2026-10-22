"""Phase 2 step 1 changes no census number (docs/superpowers/archive/plans/2026-10-12-demographics-phase2-interfaces.md).

The golden (test_fixtures/demographics/phase2_step1_golden.json), recorded on the tree before step 1's first change
(TE_RECORD_GOLDEN=1), holds:
- every te_dg_* variable and modifier of five census cases (seed, step and, under Full, the census's own term) and the
  model's outputs on two scenarios, kept exactly under the interpreter's fixed point (truncate=True); a name the golden
  lacks must be one of step 1's (NEW_VARS, NEW_MODIFIERS);
- a digest of every block of the generated census files and #892's three line files, kept byte for byte (comments
  aside) except the life table's added threshold lines;
- the yearly walk's text, which runs in every game and which the interpreter can't iterate over pops: kept but for the
  three calls of Task 5's gated effects.

Phase 2 step 3b (the census reads the Family Policy measures) changes no number either while no measure is on and the
family laws are left out (the cases hold none): its new reads are exact identities at 0 (x 1, + 0, the constants), and
its edits to three existing blocks are named below (STEP3B_ADDED, STEP3B_REWRITE), so each block's old text must still
come back once they are taken out; te_demog_cause_inputs_store, which calibration step 3 changed too, is held to
STEP3_DIGESTS' digest with step 3b's line taken out. Its new variables are te_dg_in_mat (the maternal cause's input),
te_dg_policy and te_dg_urban_left (what the step used, for the tooltips).

Phase 2 step 2 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §2) changes the census under
Full by design: work deaths split by the census's own count of women and men at work (§2.5). Its invariant is that
nothing changes outside Full, which the Display-only, the lines' and the model's cases still pin. The two Full cases
(FULL_CASES) were re-recorded on step 2's tree (TE_RECORD_GOLDEN_FULL=1, which rewrites them alone), so a later change
under Full still shows; step 2's new names are STEP2_VARS.

Phase 2 step 4 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §4) changes two things here
on purpose, and nothing else: the war dead's sums, the 18-40 te_dg_f1840 and te_dg_m1840, become the conscription
pool's (te_dg_faw, te_dg_fam: calendar 20 and over, biological 39 and under), in the cases and in
te_demog_normalize_bands (STEP4_RENAMED); and its new names (STEP4_NEW_VARS). Its sex-balance terms leave these cases
alone: their balances (94-100 men per 100 women) are above the threshold.

The migrant booking (2026-10-12) rewrites te_demog_enter_class (BOOKING_DIGESTS) and changes no recorded number.

Adults' infection (#1045) changes the rich cases on purpose: medicine reaches infection at 15-64 a second time
(te_demog_enter_group, ADULT_INFECTION_DIGESTS) and the infection treatment's cap rises to 0.99. The farm cases hold no
medicine, so their factor is 1 and their numbers stay; the two rich cases, model_rich and rich_full, were re-recorded on
#1045's tree, so a later change to them still shows.

The participation rates in the game's units (2026-10-20: the old WORKFORCE_SCALE of 0.7 folded into the rates and the
carriers' participation lines) move two figures of the Full cases on purpose, each x 0.7 within the interpreter's last
place, and nothing else: te_dg_at_work (0.41443 to 0.2901, 0.53487 to 0.3744) and te_dg_wk_past (0.02866 to 0.02006).
Those three numbers alone were rewritten; te_dg_fws_wk, which splits the work deaths, and every death and birth stay.

The deaths added on top count under their causes (owner, 2026-10-22). The walk's Full-only sums gain the pops' own lines
by cause (CAUSES_ON_TOP_DIGESTS), the refresh stores each cause's start part and tag read (te_dg_sc_<c>, te_dg_st_<c>),
the panel each cause's deaths on top (te_dg_dc_<c>_top), and te_dg_dc_ontop and the hover's red threshold go. Of the
recorded numbers only rich_full's Causes of Death slices move: its window ran above the census's rate with no split by
cause, so what was its Added on Top slice now spreads over the four natural causes by the estimate (and the fit moves
in its last place). Its ring, births and deaths, which the scales reach, are as they were: with no split, one scale.
rich_full alone was re-recorded on this tree."""

import functools
import hashlib
import json
import math
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model as M  # noqa: E402
import demographics_modifiers as DM  # noqa: E402
import demographics_params as P  # noqa: E402
from test_demographics_registry import (  # noqa: E402  (helpers and paths only: no TestCase)
    EFFECTS, GENERATED_EFFECTS, GENERATED_VALUES, LINE_EFFECTS, LINE_MODIFIERS, LINE_VALUES, _block, _Engine,
    _engine_for, _raw_blocks, _text)

GOLDEN = ROOT / "test_fixtures" / "demographics" / "phase2_step1_golden.json"
NEW_VARS = {"te_dg_wa_share", "te_dg_at_work", "te_dg_pensioners", "te_dg_need", "te_dg_old_age",
            "te_dg_low_share", "te_dg_wbase", "te_dg_wf_engine", "te_dg_ln_working_adults"}
NEW_MODIFIERS = {"te_demog_line_working_adults_up", "te_demog_line_working_adults_down"}
# phase 2 step 3b: the maternal cause's stored family-policy input, and the stored policy term and urban share left
NEW_VARS |= {"te_dg_in_mat", "te_dg_policy", "te_dg_urban_left"}
# phase 2 step 3b's lines in existing blocks: the maternal cause's laws factor (te_demog_mult_maternal) and its stored
# input (te_demog_cause_inputs_store), added; Sex Education's literacy in te_demog_means' access, rewritten back out
STEP3B_ADDED = re.compile(r"^multiply = te_demog_f_maternal_laws$|^set_variable = \{ name = te_dg_in_mat ")
STEP3B_REWRITE = (("var:te_dg_lit add = modifier:state_means_literacy_add max = 1 multiply", "var:te_dg_lit multiply"),)
# phase 2 step 2's figures (te_demog_work_finish_step2): workers past the end of the working ages, women's share of the
# workers at the work deaths' ages
STEP2_VARS = {"te_dg_wk_past", "te_dg_fws_wk"}
NEW_VARS |= STEP2_VARS
# the cases under Full, re-recorded on step 2's tree (the module's docstring)
FULL_CASES = ("farm_full_on_top", "rich_full")
# Phase 2 step 4: the war dead's 18-40 sums became the pool's (old name: new name); its new state variables
STEP4_RENAMED = {"te_dg_f1840": "te_dg_faw", "te_dg_m1840": "te_dg_fam"}
STEP4_NEW_VARS = {"te_dg_faw", "te_dg_fam", "te_dg_sxb", "te_dg_mc", "te_dg_yb"}
# Task 5's three calls in te_demog_walks; nothing else in the walk may change
WALK_CALLS = {"te_demog_work_walk_init = yes", "te_demog_work_walk_pop = yes", "te_demog_work_walk_store = yes"}
# Task 3's lines in te_demog_life_table (the old-age threshold); nothing else in the generated files may change
LIFE_TABLE_ADDED = re.compile(r"te_dg_oal\d|te_dg_oapy\d|^te_demog_old_age_pass = yes$")
# Calibration step 3 (docs/superpowers/archive/specs/2026-10-12-demographics-calibration-step3-design.md) changes these blocks on
# purpose: the country-scope absorbed lines join the absorbed deaths, the malaria factor joins infection's product and
# the store keeps its two inputs. Each is held to its new digest instead (a later change to one still fails), and no
# golden case has a farm pop, malaria or Malaria Prevention, so every recorded number stays as it was.
STEP3_DIGESTS = {
    ("generated_values", "te_demog_pop_absorbed_deaths"):
        "32dcf53c0aafe6bad0d2e137175dcdacf85ae4d2f0377f74aeb91ca4caa44ef0",
    ("generated_values", "te_demog_mult_infection"): "34badda0262f2a56d372f2c32520fb1819434b10b4272fdc44e27104f606c6df",
    ("generated_effects", "te_demog_cause_inputs_store"):
        "10a1a9f5fad0b5b475884d196e0ad597605b78ce05e48b30849d05431c3fa168",
}
STEP3_VARS = {"te_dg_in_mal", "te_dg_in_malc"}
# Phase 3, the late game (docs/superpowers/archive/specs/2026-10-11-demographics-late-game-design.md): a state with no ageing carrier
# and no treated people takes the plain sweep and changes no number (these cases have none); every census step now
# stores the mean age at childbirth (late-game §6.2), the one new name here. The walk's Full-only sums gain the bare
# deaths x wealth and the richest pop the wealth slope reads (call 14: two locals, read only in a late state's refresh,
# whose slope is 0 elsewhere), so the absorbed walk's two blocks are held to their new digests.
PHASE3_VARS = {"te_dg_mab"}
PHASE3_DIGESTS = {
    ("generated_effects", "te_demog_absorbed_walk_init"):
        "7c462c234d5672a8ea73e92287716b915166c61c8944b8284476ede476b0d936",
    ("generated_effects", "te_demog_absorbed_walk_pop"):
        "ff0c52f0f59476dcf0e3fda6eff86cc1aea107e7849840c9c091609d40ec6300",
}
# The migrant booking (2026-10-12; docs/testing/demographics-migrant-booking-2026-10-12.md) rewrites one block on
# purpose: te_demog_enter_class takes each class and sex's rate from te_demog_migrant_rates (the cap, then a flat rate
# for what it leaves) instead of the profile's share over the class's people. Below the cap the two are the same; the
# golden cases step with no flows (te_demog_no_flows), so every recorded number stays as it was, and
# test_demographics_registry's TestCohortScript holds the booking to the model. Held to its new digest, as
# STEP3_DIGESTS are.
BOOKING_DIGESTS = {
    ("generated_effects", "te_demog_enter_class"):
        "07f944c3f25667c54c199dea7cba21d956615a0f8fb065f1fd3e5d802f34ad7a",
}
# Modern safety (2026-10-16; demographics_params.SAFETY_TYPES) changes three blocks on purpose: work's and accidents'
# products gain the safety factor, and the store keeps its two shares. No golden case holds an era 7-9 safety carrier, so
# the factor reads 1 and every recorded number stays as it was; test_demographics_registry holds the factor to the model.
SAFETY_DIGESTS = {
    ("generated_effects", "te_demog_cause_inputs_store"):
        "ea5de18c153f5597a81fc108d6da4912c39eabc255620a4244193aa413746813",
    ("generated_values", "te_demog_mult_external"): "ffbb862bd4f3b5ff0e40cacb055afe81b71ea992e5373e2dfe67431980cae92b",
    ("generated_values", "te_demog_mult_work"): "20d60f152aa79ab820c226b8ddefd63053b58c552a68cc03b0f49d1899323155",
}
SAFETY_VARS = {"te_dg_in_saf_work", "te_dg_in_saf_ext"}
# Deaths by cause (issue #1029): every count stores last year's deaths split by cause for the Causes of Death section
# (te_demog_cause_deaths_store; a seed's are 0), from a new generated block (te_demog_cause_deaths_estimate) that reads the
# step's rates and changes none of them, so every recorded number stays as it was
CAUSE_DEATH_VARS = {f"te_dg_dc_{s}" for s in ("inf", "ext", "chr", "work", "mat", "war", "kill", "total", "fit", "lead")}
# The deaths on top by cause (owner, 2026-10-22; the docstring): each cause's on the panel, and the start's parts by cause
CAUSE_DEATH_VARS |= {f"te_dg_{k}_{c}" for k in ("sc", "st") for c in P.DEATH_CAUSES}
CAUSE_DEATH_VARS |= {f"te_dg_dc_{c}_top" for c in P.DEATH_CAUSES}
CAUSES_ON_TOP_GONE = {"te_dg_dc_ontop"}
CAUSES_ON_TOP_DIGESTS = {
    ("generated_effects", "te_demog_absorbed_walk_init"):
        "286e98235f792531c966d9df006e03b33dfcec1c15d0c53f4143a089b3474073",
    ("generated_effects", "te_demog_absorbed_walk_pop"):
        "d9dd290e45c61b673752ca82ed4eb631c8dbaf5301c591a25733273d2f6dfc32",
}
CAUSES_ON_TOP_REMOVED = {("generated_values", "te_demog_k_deaths_on_top_high")}
# and two of the panel's figures: net migration per 1,000 people and the month of the count
CAUSE_DEATH_VARS |= {"te_dg_mig_rate", "te_dg_count_mi"}
# The laws' terms as modifier lines (2026-10-17, so each law's tooltip says what the census does with it): Late
# Marriage's target reads Primogeniture's and Undivided Farm Succession's state_late_marriage_farms_add (0.15, the old
# constant) instead of testing the law and the amendment, and the land-tenure term moved to the hand-written
# te_demog_values.txt, reading the land laws' lines. No golden case holds Primogeniture, the amendment or a land law, so
# every recorded number stays as it was (the cases' Child Labor Allowed and Compulsory Primary School read the same
# 0.3 and 0 from their lines); test_demographics_registry holds both blocks to the laws' lines.
LAW_LINE_DIGESTS = {
    ("generated_values", "te_demog_pr_target_lm"): "de886021da9fd961f0cc501e1c2616e270e9a86705be20bcb4562ddb859593e0",
}
LAW_LINE_MOVED = {("generated_values", "te_demog_wc_land_term")}
# Working conditions read once (2026-10-17; the self-check working_conditions_read): a mine's read of its laborers' key
# held the table's 0.1 in 1836, so the walk's expected deaths drop the table's constants and keep the group reads,
# which carry it at the building's scale. The interpreter doesn't walk pops (the docstring), so no recorded number
# moves; test_gen_demographics holds the reads.
WORKING_CONDITIONS_DIGESTS = {
    ("generated_values", "te_demog_pop_death_mult"):
        "153898ca4dea6c88b75e1a376403de78d040eb99b27fe0d56a91b8d22698a469",
}
# Adults' infection (#1045; the docstring): the life table's rates take te_dg_inf_ad on infection at 15-64, and the
# infection treatment's target its new cap
ADULT_INFECTION_DIGESTS = {
    ("generated_effects", "te_demog_enter_group"): "ff843e90a65b32d61ead31fce28a9a48831e8c8e3fd4ef576c3145477de14930",
    ("generated_values", "te_demog_treatment_target_infection"):
        "769e4f31ff67c155a4ad351600e12595bdf5fa59f06f7dc76f9d1ce8390947f0",
}
# The migrant profile's inputs as modifier types (modifier-types stage 3, 2026-10-19): women's share of the workforce
# reads 0.1 + the women's-rights laws' state_female_work_share_add instead of testing the law, and the families'
# transport term the transport technologies' state_family_migration_add instead of testing the technology. Each line is
# the old table's value less the base, so the cases' No Women's Rights and Protected Class read the same 0.1 and 0.48
# (the interpreter takes the share as a fixture from the model, which reads the lines), and no case steps with flows,
# so the profile's new aviation lines move nothing here; test_demographics_registry holds both blocks to the carriers.
STAGE3_DIGESTS = {
    ("generated_values", "te_demog_female_work_share"):
        "729fa3c32536d25089000d845551a49f523310bfe0647648326433bac947d2d2",
    ("generated_values", "te_demog_family_transport"):
        "35e0649d63bd37d0d79808136ce9e150e43001f7238003f0f731cfb61ab29cb2",
}
# Uploaded minds (2026-10-19; the uploaded-minds spec §3, call 2): the inputs' store adds Mind Backups' restore x last
# step's longevity care, only in a state that has it (te_dg_elig, the late game's). No golden case is in the late game,
# so every recorded number stays as it was; test_demographics_uploads holds the restore to the model.
UPLOADS_DIGESTS = {
    ("generated_effects", "te_demog_cause_inputs_store"):
        "78de3129ee4b205c97a61f0fce47c32c250be87511c0d5183d7b3b4d3176f508",
}
# The census's rates down to the engine's floor (owner, 2026-10-20): the floor's constant is the engine's own -1 under a new
# name (te_demog_k_rate_total_floor, new and so free), M's and the step's scales' ceilings are gone, and the scales' floor
# is -1. Of the cases only rich_full moves: its births term, held at -0.85 by the old floor of -0.8, reaches its own
# rate at -0.90763, so its clamp flag goes to 0 and its next window's start births (te_dg_sr_b) from 71.25 to 43.876 a
# head; those four figures were re-recorded on this tree. The farm cases' terms never reached the floor.
RATE_FLOOR_REMOVED = {("generated_values", "te_demog_k_on_top_scale_max"),
                      ("generated_values", "te_demog_k_rate_total_min"),
                      ("generated_values", "te_demog_k_rate_term_max")}
# The walk's per-pop death multiplier takes the state's wealth line x the pop's wealth, as the engine does (probe P6).
# The interpreter doesn't walk pops (the docstring) and no case holds the line, so no recorded number moves;
# test_demographics_rate_floor holds the multiplier to predict's.
RATE_FLOOR_DIGESTS = {
    ("generated_values", "te_demog_k_on_top_scale_min"):
        "a13018ac187c2198739d13d444ccf28b6fe9db49d14e6cb7ec08602c6915197c",
    ("generated_values", "te_demog_pop_death_mult"):
        "58ceeec452f3b205b3f49a8d5e0fd16300684cdb251c6aef4a3b852593a880ea",
}
# The safeguards pass (owner, 2026-10-20): chronic treatment's cap 0.85 to 0.99, no floor but 0 on a cause's laws factor
# (was 0.2), no ceiling on crowding's infection term (was +50%), the means' cap 1 (was 0.95), and the life table's open last
# interval (te_demog_life_table passes its last group's rates to te_demog_lt_finish, whose survivors at 150 live on at
# them). No case's chronic treatment, laws terms, crowding or means reach an old bound, and its survivors at 150 are a few
# in ten million, so the interpreter's cases keep every recorded figure; the model's rich case moved in the tenth digit
# (e0 +1.7e-10 years, births -1.1e-8) and was re-recorded alone.
SAFEGUARDS_DIGESTS = {
    ("generated_effects", "te_demog_life_table"): "292d244a05f14bdb1964f71de30c68710efc30d5e39bc0bbaa58910f32f016e8",
    ("generated_values", "te_demog_f_chronic_laws"): "a841c328bec91f6a32bf17b9674984a95339d2680b7d56e66a3f272a532b33f2",
    ("generated_values", "te_demog_f_external_laws"): "2d3f2d311f16527615bd8d7093c43f88c090c8d41b316ad96adffdd7bc3336e1",
    ("generated_values", "te_demog_f_infection_crowding"):
        "3d3738da66b1220a24167021345273a85d3a1c0ca07bfb33ac8741173b4e66ce",
    ("generated_values", "te_demog_f_work_laws"): "1b315c20ac4690af689b3826307479ebc9bfb1849a27c1c46fbcde126b98a600",
    ("generated_values", "te_demog_means"): "af0d55a0594f706deee6ed1b5fea95c6f5944ff8608761bebb695fb05823f78e",
    ("generated_values", "te_demog_treatment_target_chronic"):
        "41fdf5c92606c931702efb29e240f2e378966a156fd3c442ec4236c04ceaa310",
}
BLOCK_FILES = {"generated_effects": GENERATED_EFFECTS, "generated_values": GENERATED_VALUES,
               "line_effects": LINE_EFFECTS, "line_values": LINE_VALUES, "line_modifiers": LINE_MODIFIERS}
CARRIERS = DM.load_carriers()


def _inp(**kw):
    inp = M.Inputs(**kw)
    inp.mods = DM.totals(CARRIERS, inp.techs, inp.laws, inp.institutions)
    return inp


FARM = _inp(sol=8, literacy=0.1, urban_share=0.05,
            laws=frozenset({"law_no_womens_rights", "law_child_labor_allowed"}))
RICH = _inp(sol=40, literacy=0.98, urban_share=0.8,
            techs=frozenset({"medical_degrees", "modern_nursing", "antibiotics", "modern_vaccines",
                             "antibiotic_mass_production", "contraceptive_pill", "modern_pharmaceuticals",
                             "vulcanization", "feminism"}),
            laws=frozenset({"law_protected_class", "law_compulsory_primary_school", "law_old_age_pension",
                            "law_public_health_insurance"}),
            institutions={"institution_health_system": 5, "institution_social_security": 5})
# the moved lines' families as a state reads them; the two workforce types are read only after Task 6
LINE_SUMS = {"state_demog_absorbed_mortality_mult": -0.03, "state_demog_ontop_mortality_mult": -0.05,
             "state_demog_absorbed_birth_rate_mult": 0.05, "state_demog_ontop_birth_rate_mult": 0.1,
             "state_demog_absorbed_laborers_mortality_mult": 0.05, "state_demog_ontop_mortality_wealth_mult": -0.01,
             "state_demog_womens_work_ratio_add": 0.25, "state_demog_replaced_ratio_add": -0.03}


def _census(inp, full, on_top):
    """te_demog_seed, te_demog_step a year later (no flows) and, under Full, the census's own term
    (te_demog_rates_refresh), as te_demog_state_yearly runs them. The generated cause multipliers run
    (real_multipliers); the owner's means and work share stay _engine_for's fixtures (the interpreter can't read laws)."""
    eng = _engine_for(inp, 1836, 250000.0, engine=functools.partial(_Engine, truncate=True), real_multipliers=True,
                      effects={"te_demog_flows": "te_demog_no_flows = yes"})
    eng.call("te_demog_seed")
    pop = 251000.0
    eng.fixtures.update(year=1837.0, state_population=pop)
    eng.trigger_fixtures["te_demog_effects_run"] = full
    eng.vars.update(te_dg_eb=40.0 * pop / 1000, te_dg_ed=30.0 * pop / 1000, te_dg_fjob_share=0.3)
    if on_top is not None:
        eng.vars.update(te_dg_cbr_model=40.0, te_dg_cdr_model=30.0,
                        te_dg_eb=40.0 * pop / 1000 * (1 + on_top[0]), te_dg_ed=30.0 * pop / 1000 * (1 + on_top[1]))
    eng.call("te_demog_step")
    if full:
        # the walk's sums and the state's reads as TestRatesScript._eng gives them
        eng.fixtures.update({"modifier:state_birth_rate_mult": 0.05, "modifier:state_mortality_mult": 0.04,
                             **{f"modifier:{n}": 0.0 for n in P.ENGINE_LINE_TYPES.values()}})
        eb0, ed0 = 475.0 * pop, 430.0 * pop
        eng.locals.update(te_dg_w_eb0=eb0, te_dg_w_ed0=ed0, te_dg_w_ebr=P.LITERACY_BIRTH_PENALTY * 0.2 * eb0,
                          te_dg_w_edr=0.0, te_dg_w_eb=eb0, te_dg_w_ed=ed0, te_dg_w_eb0m=eb0, te_dg_w_ed0m=ed0,
                          te_dg_w_sev=0.0, te_dg_w_sevd=0.0)
        eng.call("te_demog_rates_refresh")
    return eng


def _lines(full):
    """te_demog_lines_refresh (and, from Task 6, te_demog_workforce_lines_refresh) on a state; under Full with the
    census's term in force."""
    names = set(P.ENGINE_LINE_TYPES.values()) | set(LINE_SUMS)
    eng = _Engine({f"modifier:{n}": LINE_SUMS.get(n, 0.0) for n in names},
                  triggers={"te_demog_effects_run": full, "te_demog_cohorts_run": full}, truncate=True)
    if full:
        eng.vars.update(te_dg_mb=-0.3, te_dg_md=-0.3, te_dg_q_b=0.0, te_dg_q_d=0.0)
    eng.call("te_demog_lines_refresh")
    if "te_demog_workforce_lines_refresh" in eng.effects:
        eng.call("te_demog_workforce_lines_refresh")
    return eng


def _norm(body, drop=None):
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    for was, now in STEP3B_REWRITE:
        lines = [line.replace(was, now) for line in lines]
    return "\n".join(line for line in lines if not (drop and drop(line)) and not STEP3B_ADDED.search(line))


def blocks():
    out = {}
    for key, path in BLOCK_FILES.items():
        out[key] = {}
        for name, body in _raw_blocks([path]).items():
            drop = (lambda line: bool(LIFE_TABLE_ADDED.search(line))) if name == "te_demog_life_table" else None
            if name == "te_demog_normalize_bands":
                # phase 2 step 4's rename, back to the names the golden was recorded with
                for old, new in STEP4_RENAMED.items():
                    body = re.sub(rf"\b{new}\b", old, body)
            out[key][name] = hashlib.sha256(_norm(body, drop).encode("utf-8")).hexdigest()
    return out


def walk_text():
    body = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_walks"))
    return _norm(body, lambda line: line in WALK_CALLS)


def outputs():
    engines = {"farm_display_only": _census(FARM, False, None), "farm_full_on_top": _census(FARM, True, (0.1, 0.2)),
               "rich_full": _census(RICH, True, (0.0, 0.05)), "lines_outside_full": _lines(False),
               "lines_full": _lines(True)}
    cases = {name: {"vars": dict(sorted(eng.vars.items())), "modifiers": dict(sorted(eng.modifiers.items()))}
             for name, eng in engines.items()}
    for name, inp in (("model_farm", FARM), ("model_rich", RICH)):
        ring, last = M.run_constant(inp, years=60)
        cases[name] = {"vars": {k: last[k] for k in ("births", "deaths", "tfr", "e0", "e65", "q0_per_1000")}
                       | {f"structure_{k}": v for k, v in M.structure(ring).items()}, "modifiers": {}}
    return {"cases": cases, "blocks": blocks(), "walk": walk_text()}


class TestStepOneChangesNoNumber(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.now = outputs()
        if os.environ.get("TE_RECORD_GOLDEN") == "1":
            GOLDEN.write_text(json.dumps(cls.now, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        if os.environ.get("TE_RECORD_GOLDEN_FULL") == "1":
            golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
            for case in FULL_CASES:
                golden["cases"][case] = cls.now["cases"][case]
            GOLDEN.write_text(json.dumps(golden, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        cls.golden = json.loads(GOLDEN.read_text(encoding="utf-8"))

    def test_every_recorded_output_is_unchanged(self):
        for case, rec in self.golden["cases"].items():
            for kind in ("vars", "modifiers"):
                for name, value in rec[kind].items():
                    if name in STEP4_RENAMED:
                        # phase 2 step 4: the pool's sums replaced the 18-40 sums (other ages: other values)
                        self.assertNotIn(name, self.now["cases"][case][kind], f"{case}: {name} is still there")
                        self.assertIn(STEP4_RENAMED[name], self.now["cases"][case][kind], case)
                        continue
                    if name in CAUSES_ON_TOP_GONE:
                        self.assertNotIn(name, self.now["cases"][case][kind], f"{case}: {name} is back")
                        continue
                    self.assertIn(name, self.now["cases"][case][kind], f"{case}: {name} is gone")
                    now = self.now["cases"][case][kind][name]
                    if isinstance(value, float) and isinstance(now, float):
                        # Python 3.12's sum() rounds floats differently from 3.11's (compensated summation): CI runs
                        # both, so a float may differ in its last place; any real change is far larger
                        self.assertTrue(math.isclose(now, value, rel_tol=1e-12, abs_tol=1e-12),
                                        f"{case}: {name}: {now!r} != {value!r}")
                    else:
                        self.assertEqual(now, value, f"{case}: {name}")

    def test_only_step_ones_names_are_new(self):
        for case, rec in self.golden["cases"].items():
            now = self.now["cases"][case]
            self.assertEqual(set(now["vars"]) - set(rec["vars"]) - NEW_VARS - STEP3_VARS - STEP4_NEW_VARS - PHASE3_VARS
                             - SAFETY_VARS - CAUSE_DEATH_VARS,
                             set(), case)
            self.assertEqual(set(now["modifiers"]) - set(rec["modifiers"]) - NEW_MODIFIERS, set(), case)

    def test_the_full_cases_hold_step_twos_split(self):
        """The re-recorded Full cases hold step 2's figures (te_dg_fws_wk splits their work deaths); the Display-only
        case holds none of them, so a golden recorded before step 2 would fail here."""
        for case in FULL_CASES:
            self.assertTrue(STEP2_VARS <= set(self.golden["cases"][case]["vars"]), case)
        self.assertFalse(STEP2_VARS & set(self.golden["cases"]["farm_display_only"]["vars"]))

    def test_the_census_term_is_recorded(self):
        """The Full cases hold the census's own modifiers, so a change to M would show."""
        for case in ("farm_full_on_top", "rich_full"):
            mods = self.golden["cases"][case]["modifiers"]
            self.assertTrue(any(name.startswith("te_demog_census_") for name in mods), case)

    def test_every_generated_block_is_unchanged(self):
        """Existing blocks byte for byte (comments aside), the life table less Task 3's threshold lines; new blocks are
        free. Task 6's refactor of #892's renderers must leave its three files' blocks as they were."""
        for key, rec in self.golden["blocks"].items():
            for name, digest in rec.items():
                if (key, name) in LAW_LINE_MOVED:
                    self.assertNotIn(name, self.now["blocks"][key], f"{key}: {name} is back")
                    continue
                if (key, name) in RATE_FLOOR_REMOVED | CAUSES_ON_TOP_REMOVED:
                    self.assertNotIn(name, self.now["blocks"][key], f"{key}: {name} is back")
                    continue
                self.assertIn(name, self.now["blocks"][key], f"{key}: {name} is gone")
                want = LAW_LINE_DIGESTS.get((key, name), SAFETY_DIGESTS.get((key, name), PHASE3_DIGESTS.get(
                    (key, name), BOOKING_DIGESTS.get((key, name), STEP3_DIGESTS.get((key, name), digest)))))
                want = WORKING_CONDITIONS_DIGESTS.get((key, name), want)
                want = ADULT_INFECTION_DIGESTS.get((key, name), want)
                want = STAGE3_DIGESTS.get((key, name), want)
                want = UPLOADS_DIGESTS.get((key, name), want)
                want = RATE_FLOOR_DIGESTS.get((key, name), want)
                want = SAFEGUARDS_DIGESTS.get((key, name), want)
                want = CAUSES_ON_TOP_DIGESTS.get((key, name), want)
                self.assertEqual(self.now["blocks"][key][name], want, f"{key}: {name} changed")

    def test_the_walk_changes_only_by_its_three_calls(self):
        self.assertEqual(self.now["walk"], self.golden["walk"])


if __name__ == "__main__":
    unittest.main()
