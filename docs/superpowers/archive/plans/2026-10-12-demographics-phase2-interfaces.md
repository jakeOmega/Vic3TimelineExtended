# Demographics phase 2, step 1: the interfaces, changing no number (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the census gains the interfaces phase 2's workforce, pension, health and conscription work reads (two age
indexes, a pension-age variable, participation and need tables, the old-age threshold, planned and unplanned births,
the workforce lines on two script-only families, the workforce target as a total), and no birth, death or workforce
number moves in any game.

**Architecture:**
- **Prove "no number moves" first.** Task 1 records every census output of four fixture cases (seed and step, Display
  only and Full, an 1836 farming state and a rich aged one, and the moved lines' refresh) and the model's outputs on
  two scenarios, on the tree before any change. Every later task keeps them equal, under the interpreter's fixed-point
  mode; only step 1's new names may appear.
- **The model first, then the script.** Each new figure is a function in `demographics_model.py`; the generator and the
  hand-written script mirror it, and the registry tests run the script against the model.
- **New sums ride on the sweep's existing accumulation** (`te_demog_accumulate_slot`, ages after the step, in both the
  seed and the step), with two pointers in `te_demog_age_boundaries`: a calendar band (the working-age start) and a
  biological band (capacity and need), the biological age being the calendar one until phase 3.
- **The birth line moves into a generated effect** (`te_demog_slot_births`) that is today's line while the planned and
  unplanned schedules are the same object, and a two-term form when they differ (tested, not shipped).
- **Every workforce line moves like #892's** (the owner's call 3: the ones once left on top too, each with a
  participation input beside it), but in their own generated files with their own refresh and gate, so the
  census's births and deaths term never takes them off and #892's generated files and tests are untouched.

**Tech Stack:** Paradox script (Victoria 3 1.14.5); Python 3.11/3.12 (`unittest`); `demographics_model.py` as the
script's twin; the `_Engine` script interpreter in `test_demographics_registry.py` (with `truncate=True`, the engine's
fixed point); `gen_demographics.py` for generated script; `demographics_harness.py`.

**Spec:** `docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md` §1 (step 1), §12 and §13 call 1.
It argues from the approved late-game design (`2026-10-11-demographics-late-game-design.md` §0, §2.1, §2.2, §3.1,
§8.1) and #894's rulings. Read `docs/systems/mod_systems.md` § Demographics first ("The census", "The moved lines").

## Dependencies and shared edits

- **This plan lands after the base-law PR** (spec §3.1: every game, built separately from calls 1, 6, 8 and 9). It
  drops Post-Scarcity's working-adult line, which Task 6 would otherwise have to move, and changes the family laws' loc
  (Communal Child-Rearing's numbers stay; its women's-work line moves in Task 6).
- **This plan lands after Late Marriage and Birth Spacing** (#906, branch `feat/demog-late-marriage`, being built in
  `/home/jakef/src/vic3te-demog-lm-build`). Start only once #906 has merged; branch from `main` then. #906 edits:
  - `te_demog_seed` and `te_demog_step_begin` (its `te_demog_practices_seed` / `_step` before `te_demog_prepare`);
    this plan appends to the end of `te_demog_prepare` and edits `te_demog_reset_accumulators`,
    `te_demog_age_boundaries`, `te_demog_accumulate_slot`, `te_demog_age_slot` and `te_demog_step_finish`;
  - `te_demog_country_census` (its practices' sums); this plan doesn't touch it;
  - `te_demog_tfr` (`multiply = te_demog_pr_terms`); this plan's planned and unplanned values read `te_demog_tfr`
    itself, so they carry the practices with no edit;
  - `demographics_model.Inputs` and `fertility` (its practices); this plan appends two `Inputs` fields with defaults
    and two keys to `fertility`'s result, computed from the result's own `tfr` and `factor`;
  - `demographics_params` (a "practices" section) and `gen_demographics.render_values` (`practices(o)`);
  - `_engine_for` in `test_demographics_registry.py` (`place=`, `targets=`); this plan adds fixtures inside it;
  - `demographics_harness.py` (`practices-replay`, `practices-fit`, `PRACTICE_SCENARIOS`); this plan adds one
    subcommand, `workforce`.
- **Re-check every anchor below against the merged tree before Task 1** (the CoD plan's "re-planned" note): the line
  numbers here are `main` at fc38b65b (2026-10-12), before #906.
- **Generated files** (`te_demog_generated_effects.txt`, `te_demog_generated_values.txt` and this plan's three new
  ones) are regenerated after each task and after any merge, never merged by hand.
- **Causes of Death (#916)** is on `main`; nothing here reads it.

## What the code says that the spec doesn't (read before Task 1)

**D1. The birth line is hand-written.** The spec says the generator writes the sweep's birth line. Today it is in
`te_demog_age_slot` (`te_demog_effects.txt:1182`): `te_dg_b = f × te_dg_asfr ÷ 100000 × te_dg_tfr`, with `te_dg_asfr`
from the generated `te_demog_enter_group`. Task 3 moves the block, unchanged, into a generated `te_demog_slot_births`
and calls it from `te_demog_age_slot`. The arithmetic is the same text, so the golden holds.

**D2. The working-adult field has no reader.** `demographics_modifiers.engine_rate_lines` keeps only `*_mult` fields,
and `engine_lines`, `line_carriers` and their tests assume the births and deaths families (`TestEngineRateLines`
asserts `set(P.ENGINE_LINE_SHORT) == set(P.ENGINE_LINE_FIELDS)` and that the types file holds exactly
`P.ENGINE_LINE_TYPES`). Task 6 adds a `keep` argument to `engine_rate_lines` and two new readers, and keeps the
workforce types, pairs and refresh in their own files and parameters (`P.WORKFORCE_LINE_*`), so no #892 test changes.

**D3. The pair needs its own gate and its own refresh.** `te_demog_lines_refresh` applies every field under
`te_demog_lines_apply` (not Full, or no `te_dg_mb`), and `te_demog_rates_refresh` calls `te_demog_lines_clear` when it
first sets M. A working-adult pair there would come off at a state's first Full step with nothing in its place. Task 6
writes `te_demog_workforce_lines_refresh` / `_clear` under `te_demog_workforce_lines_apply` (not Full, or no
`te_dg_mw`, which step 2 sets), called beside `te_demog_lines_refresh` at its two call sites
(`te_demog_on_actions.txt:153`, `events/te_demog_events.txt:74`).

**D4. The figures' denominator.** In the seed the accumulators are in the raw ring's units (before
`te_demog_normalize_bands`), and `te_dg_raw` becomes `state_population` after it; in the step the newborns join
`te_dg_raw` only in `te_demog_step_finish`. So the figures are shares computed from the accumulators against
`te_dg_raw` at the right moment: in the seed straight after `te_demog_close_accumulators`, in the step straight after
`change_local_variable = { name = te_dg_raw add = local_var:te_dg_births }`.

**D5. The walk runs under every rule** (inheritance needs it). The new walk sums (the lower strata, the pops' base
ratios, the engine's workforce) run only while the census's cohorts run: one local set before `every_scope_pop`, one
test per pop.

**D6. Pop reads.** `workforce` and `strata` are pop triggers with comparison traits (`triggers.log:16012`, `:15628`),
so `value = workforce` and `strata = lower` work in a walk; option f's probe (`te_debug_demog_values.txt`) already reads
`workforce`. A pop's base ratio is a type property, not a read: aristocrats 0.2, slaves 0.5 (vanilla `pop_types`), the
rest the define's 0.25.

**D7. Post-Scarcity's line is gone before step 1.** The owner dropped it in every game (spec §13 call 1), and the
base-law PR removes it; Task 6 checks that it has.

**D12. Some of call 3's carriers are no reader's, and two of their kinds are unproven.** `demographics_modifiers`
walks laws, technologies and institutions, so the two amendments, the two IG traits, Woman Soldiers and Pollution
Impact are pinned by reading their blocks (Task 6). Whether the engine sums a script-only type from each into a state's
read:
- Woman Soldiers, a country modifier at ×0.5: proven kind (a country modifier's `state_*` lines reach every state's
  read, `scripting_best_practices.md:4918`; a multiplier scales every field).
- Pollution Impact: proven (probe P1, `scripting_best_practices.md:4932`: the mod's INJECTed line sums with vanilla's ×
  the region's impact).
- Amendments: strongly plausible (vanilla `common/amendments/amendments.md:8`: an amendment's modifier is "added to the
  modifiers of the law it is attached to", the law path #892 proved).
- IG traits: open. The mod already INJECTs one (`common/interest_group_traits/sol_expectations_vanilla_injections.txt:8`),
  with no recorded check of a script-only type or of the cancel netting the trait's tooltip.
- Task 7's console option p sets up the amendment, the traits and Woman Soldiers in one go, and Task 8's item 9 reads
  the result. A failed kind would lose its line in every game (the pair can't put back what the state doesn't read), so
  it blocks the merge: revert that block to its engine field and list it in `P.LIVE_WORKFORCE_LINES`.

**D8. The war dead's window stays 18–40.** The spec moves it to the conscription pool in step 4; doing it here would
move the ring.

**D10. With no pension law the working ages have no end.** Late-game §2.1 runs them "to capacity's end", and capacity
never reaches 0, so `te_dg_wa_end` is 999 without a pension law (not the Standard 65, which let "at work" pass 100% in
an old country with no pension). "At work" can still pass 1 under a pension law when those past the end far outnumber
the working ages; the stored figure stays uncapped, and step 2's panel caps what it shows (spec §1.3).

**D11. The interpreter can't iterate pops**, so `te_demog_walks` never runs in a test (`TestWalks` reads its text).
Task 5 puts its additions in three effects called by one line each, and Task 1's golden pins the walk's text less
those three lines; Task 5 runs the three effects outside the census and checks they set nothing.

**D9. The seed's NRR keeps the one schedule.** `te_demog_life_table`'s NRR sum and the model's `nrr` read `te_dg_asfr`;
phase 3, which parts the schedules, revisits them.

## Owner decisions

**The owner answered spec §13's ten calls on 2026-10-12**; the ones this plan rests on:
1. Call 1: Post-Scarcity's line is dropped in every game by the base-law PR, not moved here (D7).
2. Call 2: step 1's every-game changes are accepted (one "Laws and Institutions" workforce line instead of one per
   carrier; an institution level's line up to a month late).
3. Call 3: every line once left on top moves to the replaced family at its old value, with a participation input
   beside it (spec §1.7's inventory; Task 6).
4. Call 4: step 2's term nets the define's 0.25; step 1 stores `te_dg_wbase` for the hover.

**Also answered:** call 11 (realistic sizes for the participation inputs; step 1 ships the starting sizes, and step 2's
fit may scale them) and call 12 (Rosen's two lines stay flat on top, listed in `P.LIVE_WORKFORCE_LINES`). Call 9
(Communal Child-Rearing keeps main's numbers) is the base-law PR's. No call is open.

Execution: subagent-driven, with review stops after Tasks 3, 5 and 6 and a whole-branch review at the end.

## Global Constraints

- **No birth, death or workforce number changes in any game.** Task 1's golden test pins it; every task runs it.
- **Nothing reads the rule but the two wrappers** (`te_demog_cohorts_run`, `te_demog_effects_run`;
  `test_only_the_wrappers_read_the_rule`).
- **Game version:** Victoria 3 1.14.5. Vanilla facts from `vanilla_parsed/`.
- **Generated files are never hand-edited.** `python3 scripts/generators/gen_demographics.py --check` stays clean.
- **Paradox files:** tab indentation; exactly one UTF-8 BOM on every `.txt` and `.yml`; run
  `python3 scripts/format_paradox_tabs.py <files>` after edits.
- **Script literals:** at most five decimals. **Every `divide =`** in a `te_demog*` file takes a literal or a
  `{ value = … min = … }` block (`TestDivisions.test_every_division_is_guarded`).
- **One refresh site per modifier;** the workforce pair's is `te_demog_workforce_lines_refresh`.
- **Scripted effect calls pass exactly the `$X$` the callee names** (`script_argument_audit --strict`).
- **Localization:** add keys to the existing files named, run `python3 organize_loc.py`, commit what it moves; loc
  uses `#b X#!`, never `[b]`.
- **Python:** 3.11-compatible; check with `grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" <files>`.
- **Running Python in the sparse worktree:** `V=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python` and
  `export VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent
  VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent`. Read a test run's result with
  `grep -E '^(Ran |OK|FAILED)'`.
- **Commits:** by path, never `git commit -a`; end each message with the session's `Co-Authored-By` and
  `Claude-Session` lines. **No `/reload`, no deploy** from a worktree.

## Review Focus

1. **A census from before this build** (an old save, or a state seeded before the update): no `te_dg_low_share`, no
   `te_dg_old_age`, no country pension variable.
   - Expect: its next step computes every figure from guarded reads, with no read of a missing variable.
   - Pinned by Task 5's `test_a_census_from_before_step_1_steps_cleanly`.
2. **Under Full, once a state's census term M is in force**, the women's-work and replaced lines still reach it.
   - Expect: the workforce pair holds the families' sum; only the births and deaths pairs come off.
   - Pinned by Task 6's `test_the_workforce_pair_survives_the_census_term`.
3. **The welfare law changes** (Old Age Pension to UBI, or none to Old Age Pension).
   - Expect: the country's pension variable follows that day; under UBI the working ages end at the state's old-age
     threshold and no one counts as a pensioner.
   - Pinned by Task 4's `test_the_variable_follows_the_law` and Task 5's `test_ubi_ends_the_working_ages_at_the_threshold`.
4. **Every census output stays the same**: the five golden cases (with the census's own term under Full), the model's
   scenarios, every existing generated block and the walk's text.
   - Pinned by Task 1's `TestStepOneChangesNoNumber`, run after every task.
5. **A release build** (`scripts/release/comment_out_census_inputs.py`): the moved workforce lines must survive it,
   since the pair re-applies them in every game.
   - Expect: the two families are not census inputs and the release leaves their lines alone; the three
     participation inputs are, and it comments them out.
   - Pinned by Task 6's `test_a_release_keeps_the_families_and_drops_the_inputs`.

---

## File structure

| File | Change | Responsibility |
|---|---|---|
| `test_demographics_golden.py`, `test_fixtures/demographics/phase2_step1_golden.json` | create (Task 1) | the golden: census and model outputs before step 1 |
| `scripts/analysis/demographics_params.py` | modify | a "Phase 2 step 1" section (Task 2); the workforce lines' section (Task 6) |
| `scripts/analysis/demographics_model.py` | modify | `Inputs.low_share`, `.pension_age`; `band_value`, `child_work_share`, `start_factor`, `women_rate_law`, `women_rate`, `pension_kind`, `working_ages_end`, `work_figures`, `wf_target`, `old_age_threshold`, `old_age`, `asfr_planned`, `asfr_unplanned`, `slot_births`; `fertility`'s two parts; `step` calls `slot_births` |
| `scripts/generators/gen_demographics.py` | modify | `work_bands`, `old_age_pass`, `slot_births`; the life table's stores; `enter_group`'s unplanned schedule; constants and values (Task 3); the workforce lines' three files (Task 6) |
| `common/scripted_effects/te_demog_generated_effects.txt`, `common/script_values/te_demog_generated_values.txt` | regenerated | — |
| `common/scripted_effects/te_demog_workforce_line_effects_generated.txt`, `common/script_values/te_demog_workforce_line_values_generated.txt`, `common/static_modifiers/te_demog_workforce_line_modifiers_generated.txt` | create (generated, Task 6) | the workforce pair, its sum and refresh |
| `common/scripted_effects/te_demog_effects.txt` | modify | `te_demog_prepare` → `te_demog_work_setup`; `te_demog_reset_accumulators`, `te_demog_age_boundaries`, `te_demog_accumulate_slot` → `te_demog_work_slot`; `te_demog_seed` and `te_demog_step_finish` → `te_demog_work_finish`; `te_demog_age_slot` → `te_demog_slot_births`; the walk's three sums; `te_demog_pension_age_refresh`; the header inventory |
| `common/script_values/te_demog_values.txt` | modify | `te_demog_women_rate_law`, `te_demog_women_rate`, `te_demog_low_share`, `te_demog_pension_kind`, `te_demog_pension_age`, `te_demog_tfr_factor`, `te_demog_tfr_planned`, `te_demog_tfr_unplanned`, `te_demog_tfr_planned_share`, `te_demog_wf_target`, `te_demog_old_age_average`, `te_demog_old_age_common` |
| `common/scripted_triggers/te_demog_triggers.txt` | modify | `te_demog_has_pension_law`, `te_demog_workforce_lines_apply` |
| `common/on_actions/te_demog_on_actions.txt`, `events/te_demog_events.txt` | modify | the pension hook; the workforce refresh beside the lines refresh |
| `common/modifier_type_definitions/demographics_workforce_line_types.txt` | create | the two families' types |
| `common/modifier_type_definitions/demographics_modifier_types.txt` | modify (Task 5) | call 3's three participation inputs |
| `common/laws/te_demog_engine_line_injections.txt`, `common/laws/extra_laws.txt`, `common/technology/technologies/era_6.txt`, `era_7.txt`, `common/amendments/extra_amendments.txt`, `common/static_modifiers/extra_modifiers.txt` | modify | the moved working-adult lines and their participation inputs |
| `common/interest_group_traits/te_demog_workforce_injections.txt`, `common/static_modifiers/te_demog_workforce_injections.txt` | create | vanilla's two IG traits and Woman Soldiers, moved |
| `common/script_values/gui_chart_script_values.txt` | modify | the hidden-modifier count gains the pair |
| `scripts/analysis/demographics_modifiers.py` | modify | `engine_rate_lines(keep=)`, `engine_workforce_lines`, `workforce_line_carriers` |
| `scripts/analysis/demographics_harness.py` | modify | `workforce` subcommand (Task 7) |
| `common/scripted_effects/te_debug_demog_effects.txt`, `common/script_values/te_debug_demog_values.txt` | modify | option l's `TE_DEMOG_WORK` line (Task 7) |
| `localization/english/te_modifiers_l_english.yml`, `te_miscellaneous_l_english.yml` | modify | the types and the pair |
| tests: `test_demographics_model.py`, `test_gen_demographics.py`, `test_demographics_registry.py`, `test_demographics_modifiers.py`, `test_demographics_harness.py` | modify | below |
| docs: `docs/systems/mod_systems.md`, `docs/guides/python_tools.md`, `docs/auto_generated_files.md`, `docs/player_guide/08-states.md` (+ PDF) | modify | Task 8 |

---

### Task 1: The golden, recorded before any change

**Files:**
- Create: `test_demographics_golden.py`
- Create: `test_fixtures/demographics/phase2_step1_golden.json` (written by Step 2)

**Interfaces:**
- Consumes: `_Engine`, `_engine_for`, `_raw_blocks`, `_block`, `_text` and the file paths from
  `test_demographics_registry.py` (no `TestCase` is imported, so discovery doesn't run the registry's tests twice);
  `demographics_model`, `demographics_modifiers`, `demographics_params`.
- Produces: `TestStepOneChangesNoNumber`, which every later task runs. `NEW_VARS`, `NEW_MODIFIERS`: the names step 1
  may add.

- [ ] **Step 1: Write the golden test**

```python
"""Phase 2 step 1 changes no census number (docs/superpowers/archive/plans/2026-10-12-demographics-phase2-interfaces.md).

The golden (test_fixtures/demographics/phase2_step1_golden.json), recorded on the tree before step 1's first change
(TE_RECORD_GOLDEN=1), holds:
- every te_dg_* variable and modifier of five census cases (seed, step and, under Full, the census's own term) and the
  model's outputs on two scenarios, kept exactly under the interpreter's fixed point (truncate=True); a name the golden
  lacks must be one of step 1's (NEW_VARS, NEW_MODIFIERS);
- a digest of every block of the generated census files and #892's three line files, kept byte for byte (comments
  aside) except the life table's added threshold lines;
- the yearly walk's text, which runs in every game and which the interpreter can't iterate over pops: kept but for the
  three calls of Task 5's gated effects."""

import functools
import hashlib
import json
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
# Task 5's three calls in te_demog_walks; nothing else in the walk may change
WALK_CALLS = {"te_demog_work_walk_init = yes", "te_demog_work_walk_pop = yes", "te_demog_work_walk_store = yes"}
# Task 3's lines in te_demog_life_table (the old-age threshold); nothing else in the generated files may change
LIFE_TABLE_ADDED = re.compile(r"te_dg_oal\d|te_dg_oapy\d|^te_demog_old_age_pass = yes$")
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
    return "\n".join(line for line in lines if not (drop and drop(line)))


def blocks():
    out = {}
    for key, path in BLOCK_FILES.items():
        out[key] = {}
        for name, body in _raw_blocks([path]).items():
            drop = (lambda line: bool(LIFE_TABLE_ADDED.search(line))) if name == "te_demog_life_table" else None
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
        cls.golden = json.loads(GOLDEN.read_text(encoding="utf-8"))

    def test_every_recorded_output_is_unchanged(self):
        for case, rec in self.golden["cases"].items():
            for kind in ("vars", "modifiers"):
                for name, value in rec[kind].items():
                    self.assertIn(name, self.now["cases"][case][kind], f"{case}: {name} is gone")
                    self.assertEqual(self.now["cases"][case][kind][name], value, f"{case}: {name}")

    def test_only_step_ones_names_are_new(self):
        for case, rec in self.golden["cases"].items():
            now = self.now["cases"][case]
            self.assertEqual(set(now["vars"]) - set(rec["vars"]) - NEW_VARS, set(), case)
            self.assertEqual(set(now["modifiers"]) - set(rec["modifiers"]) - NEW_MODIFIERS, set(), case)

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
                self.assertIn(name, self.now["blocks"][key], f"{key}: {name} is gone")
                self.assertEqual(self.now["blocks"][key][name], digest, f"{key}: {name} changed")

    def test_the_walk_changes_only_by_its_three_calls(self):
        self.assertEqual(self.now["walk"], self.golden["walk"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Record the golden on the unchanged tree**

Run: `mkdir -p test_fixtures/demographics && TE_RECORD_GOLDEN=1 $V -m unittest test_demographics_golden -v`
Expected: OK, and `test_fixtures/demographics/phase2_step1_golden.json` written.
- If the seed or step fails under `truncate=True` with a fixed-point assertion unrelated to this work, record with
  `truncate=False` (drop the `functools.partial`) and say so in the commit message: float equality still pins an
  unchanged arithmetic path.
- If the step reads a variable the walk would set that the case lacks, add it to the `eng.vars.update` in `_census`
  from `TestCohortScript.step_both`'s list; if `te_demog_rates_refresh` reads a name the case lacks, take it from
  `TestRatesScript._eng`. Record again.
- Check the recording holds what it should: the two Full cases carry `te_demog_census_*` modifiers
  (`test_the_census_term_is_recorded`), and `blocks` lists `te_demog_life_table`, `te_demog_enter_group` and
  `te_demog_lines_refresh`.

- [ ] **Step 3: Check it holds without recording**

Run: `$V -m unittest test_demographics_golden -v`
Expected: OK. Then `git diff --stat` shows only the two new files.

- [ ] **Step 4: Commit**: "Demographics phase 2 step 1: the golden every census output must keep".

---

### Task 2: The model: the tables, the figures, the threshold, two birth parts

**Files:**
- Modify: `scripts/analysis/demographics_params.py` (a new section after "Fertility inputs as modifier types")
- Modify: `scripts/analysis/demographics_model.py` (`Inputs`; `fertility`; `step`'s birth line; new functions after
  `asfr_shape`)
- Test: `test_demographics_model.py` (new class `TestPhase2Interfaces`)

**Interfaces:**
- Produces:
  - `P.CHILD_WORK_AGE = 10`, `P.WORKING_AGE = 15`, `P.CHILD_WORK_SHARE: dict[str, float]`,
    `P.CHILD_WORK_SHARE_DEFAULT`, `P.CAPACITY: dict[int, float]`, `P.AFTER_PENSION_SHARE`, `P.MEN_RATE`,
    `P.WOMEN_BASE`, `P.WOMEN_LOWER`, `P.WOMENS_WORK_FULL`, `P.WORKFORCE_SCALE`, `P.HEALTH_NEED: dict[int, float]`,
    `P.HEALTH_NEED_1836`, `P.BIO_BANDS: tuple[int, ...]`, `P.PENSION_AGE: dict[str, int]`, `P.PENSION_LAW`,
    `P.NO_PENSION_AGE_LAWS`, `P.NO_WORKING_AGE_END`, `P.OLD_AGE_REMAINING`, `P.OLD_AGE_FROM`, `P.ASFR_PLANNED_SHAPE`,
    `P.ASFR_UNPLANNED_SHAPE`, `P.POP_BASE_RATIO`, `P.POP_BASE_RATIO_DEFAULT`, `P.WOMENS_WORK_TYPE`,
    `P.REPLACED_TYPE`, `P.MALE_PARTICIPATION_TYPE`, `P.PARTICIPATION_TYPE`, `P.CAPACITY_TYPE`,
    `P.PARTICIPATION_TYPES`.
  - `M.Inputs.low_share: float = 0.0`, `M.Inputs.pension_age: float | None = None`.
  - `M.band_value(table, age) -> float`, `M.child_work_share(inp) -> float`, `M.start_factor(inp, age) -> float`,
    `M.women_rate_law(inp) -> float`, `M.women_rate(inp) -> float`, `M.pension_kind(inp) -> int` (0, 1, 2),
    `M.sex_rates(inp) -> (float, float)` (women's, men's), `M.capacity_at(inp, age) -> float`,
    `M.working_ages_end(inp, old_age) -> (float, bool, bool)`, `M.work_figures(ring, inp, old_age) -> dict`
    (`wa_share`, `at_work`, `pensioners`, `need`), `M.wf_target(figures) -> float`,
    `M.old_age_threshold(q) -> float`, `M.old_age(qf, qm) -> float`, `M.asfr_planned(r)`, `M.asfr_unplanned(r)`,
    `M.slot_births(f, r, rb, tfr, planned_share) -> float`; `fertility(...)["planned"]`, `["unplanned"]`.

- [ ] **Step 1: Write the failing tests** (`test_demographics_model.py`)

```python
class TestPhase2Interfaces(unittest.TestCase):
    """Phase 2 step 1 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §1): the figures
    the census stores and applies nowhere yet."""

    FARM = dict(sol=8, literacy=0.1, urban_share=0.05, laws=frozenset({"law_no_womens_rights",
                                                                        "law_child_labor_allowed"}))

    def test_the_bands_cover_both_tables(self):
        self.assertEqual(P.BIO_BANDS, tuple(sorted(set(P.CAPACITY) | set(P.HEALTH_NEED))))
        self.assertEqual(M.band_value(P.CAPACITY, 59), 1.0)
        self.assertEqual(M.band_value(P.CAPACITY, 64), 0.95)
        self.assertEqual(M.band_value(P.CAPACITY, 150), 0.1)
        self.assertEqual(M.band_value(P.HEALTH_NEED, 4), 1.0)
        self.assertEqual(M.band_value(P.HEALTH_NEED, 14), 0.5)

    def test_the_working_age_start_follows_the_childrens_rights_law(self):
        for law, share in (("law_child_labor_allowed", 0.3), ("law_restricted_child_labor", 0.1),
                           ("law_compulsory_primary_school", 0.0)):
            inp = M.Inputs(laws=frozenset({law}))
            self.assertEqual([M.start_factor(inp, a) for a in (9, 10, 14, 15)], [0.0, share, share, 1.0], law)
        self.assertEqual(M.child_work_share(M.Inputs()), P.CHILD_WORK_SHARE_DEFAULT)

    def test_womens_rate_rises_with_the_family_and_the_lower_strata(self):
        none = M.Inputs()
        full = M.Inputs(mods={P.WOMENS_WORK_TYPE: P.WOMENS_WORK_FULL})
        self.assertAlmostEqual(M.women_rate(none), P.WOMEN_BASE)
        self.assertAlmostEqual(M.women_rate(full), P.MEN_RATE)
        self.assertAlmostEqual(M.women_rate(M.Inputs(mods={P.WOMENS_WORK_TYPE: 9.0})), P.MEN_RATE, msg="capped")
        lower = M.Inputs(low_share=0.8)
        self.assertAlmostEqual(M.women_rate(lower), 0.8 * P.WOMEN_LOWER + 0.2 * P.WOMEN_BASE)
        self.assertAlmostEqual(M.women_rate(dataclasses.replace(full, low_share=0.8)), P.MEN_RATE,
                               msg="the floor never lowers a law's rate")

    def test_call_3s_inputs_move_the_rates_and_capacity_within_bounds(self):
        inp = M.Inputs(mods={P.MALE_PARTICIPATION_TYPE: 0.03, P.PARTICIPATION_TYPE: 0.01, P.CAPACITY_TYPE: -0.1})
        rf, rm = M.sex_rates(inp)
        self.assertAlmostEqual(rm, P.MEN_RATE + 0.04)
        self.assertAlmostEqual(rf, P.WOMEN_BASE + 0.01)
        self.assertAlmostEqual(M.capacity_at(inp, 30), 0.9)
        self.assertAlmostEqual(M.capacity_at(inp, 62), 0.95 * 0.9)
        big = M.Inputs(mods={P.MALE_PARTICIPATION_TYPE: 0.5, P.CAPACITY_TYPE: 0.5})
        self.assertEqual(M.sex_rates(big)[1], 1.0)
        self.assertEqual(M.capacity_at(big, 30), 1.0)
        self.assertAlmostEqual(M.capacity_at(big, 82), 0.45)

    def test_the_working_ages_end_by_the_welfare_law(self):
        self.assertEqual(M.working_ages_end(M.Inputs(), 61.0), (999.0, False, False), "no pension: no end (D10)")
        oap = M.Inputs(laws=frozenset({"law_old_age_pension"}))
        self.assertEqual(M.working_ages_end(oap, 61.0), (65, True, True))
        self.assertEqual(M.working_ages_end(dataclasses.replace(oap, pension_age=70.0), 61.0), (70.0, True, True))
        for law in P.NO_PENSION_AGE_LAWS:
            self.assertEqual(M.working_ages_end(M.Inputs(laws=frozenset({law})), 61.0), (61.0, True, False), law)

    def test_figures_of_a_hand_built_ring(self):
        ring = M.Ring(year=1900)
        for a, f, m in ((5, 100, 100), (12, 50, 50), (30, 200, 200), (66, 40, 30)):
            k = (1900 - a) % M.N
            ring.f[k], ring.m[k] = float(f), float(m)
        ring.pool_f, ring.pool_m = 1.0, 1.0
        inp = M.Inputs(laws=frozenset({"law_child_labor_allowed", "law_old_age_pension"}), low_share=0.5)
        rf = M.women_rate(inp)
        got = M.work_figures(ring, inp, 60.0)
        total = 200 + 100 + 400 + 70 + 2
        wa = 100 + 400                                   # 12-year-olds at 0.3, 30-year-olds; 66 is past 65
        workers = (50 * rf + 50 * 0.92) * 0.3 + (200 * rf + 200 * 0.92) \
            + (40 * rf + 30 * 0.92) * 0.85 * P.AFTER_PENSION_SHARE + (rf + 0.92) * 0.1 * P.AFTER_PENSION_SHARE
        need = 200 * 0.5 + 100 * 0.5 + 400 * 0.8 + 70 * 2.4 + 2 * 4.5
        self.assertAlmostEqual(got["wa_share"], wa / total)
        self.assertAlmostEqual(got["at_work"], workers / wa)
        self.assertAlmostEqual(got["pensioners"], 72 / total)
        self.assertAlmostEqual(got["need"], need / total / P.HEALTH_NEED_1836)
        self.assertAlmostEqual(M.wf_target(got), P.WORKFORCE_SCALE * workers / total)

    def test_the_targets_at_the_starting_values(self):
        """The spec's §1.8 sketch: 1836 farming about 0.25 on the engine's scale, a rich aged state about 0.40."""
        farm = scenario(low_share=0.85, **self.FARM)
        ring, _last = M.run_constant(farm, years=300)
        qf, qm, _ = M.group_rates(farm)
        self.assertAlmostEqual(M.wf_target(M.work_figures(ring, farm, M.old_age(qf, qm))), 0.25, delta=0.02)
        self.assertAlmostEqual(M.old_age(qf, qm), 59.3, delta=1.0)

    def test_the_old_age_threshold_has_fifteen_years_left(self):
        qf, qm, _ = M.group_rates(scenario(**self.FARM))
        for q in (qf, qm):
            age = M.old_age_threshold(q)
            self.assertGreater(age, 50)
            self.assertLess(age, 70)
        flat = [100000.0] * len(P.GROUPS)                 # everyone dies in their first year
        self.assertEqual(M.old_age_threshold(flat), float(P.OLD_AGE_FROM))

    def test_planned_and_unplanned_sum_to_the_children_per_woman(self):
        for kw in (self.FARM, dict(sol=35, literacy=0.95, urban_share=0.8,
                                   techs=frozenset({"vulcanization", "feminism", "contraceptive_pill"}))):
            fert = M.fertility(scenario(**kw), 60.0)
            self.assertAlmostEqual(fert["planned"] + fert["unplanned"], fert["tfr"], places=12)
            self.assertAlmostEqual(fert["unplanned"], fert["tfr"] / fert["factor"] * (1 - fert["means"]), places=12)

    def test_one_schedule_keeps_todays_birth_line(self):
        self.assertIs(P.ASFR_PLANNED_SHAPE, P.ASFR_UNPLANNED_SHAPE)
        for r in (14, 15, 27, 49, 50):
            self.assertEqual(M.slot_births(1234.5, r, r + 3, 4.2, 0.3), 1234.5 * M.asfr_shape(r) / 100000.0 * 4.2)

    def test_two_schedules_split_by_the_planned_share(self):
        other = {15: 10000, 20: 30000, 25: 30000, 30: 20000, 35: 7000, 40: 2500, 45: 500}
        with unittest.mock.patch.object(P, "ASFR_UNPLANNED_SHAPE", other):
            got = M.slot_births(1000.0, 27, 32, 4.0, 0.25)
        want = (P.ASFR_SHAPE_BY_GROUP[25] / 5 * 0.25 + other[30] / 5 * 0.75) * 1000.0 / 100000.0 * 4.0
        self.assertAlmostEqual(got, want)
```

Add `import unittest.mock` at the top of the file.

- [ ] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_model.TestPhase2Interfaces -v`
Expected: FAIL (`AttributeError: module 'demographics_params' has no attribute 'BIO_BANDS'` and the like).

- [ ] **Step 3: The parameters** (`demographics_params.py`, a new section after "Fertility inputs as modifier types")

```python
# ---- Phase 2 step 1: the interfaces -----------------------------------------------------------------------------
# docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §1. The census computes these figures
# at every seed and step and applies none of them until step 2, whose harness fits the numbers (owner, 2026-10-12).
# Participation (late-game §2.1; #894): people x start(calendar age) x [below the end of the working ages ? 1 : the
# after-pension share] x capacity(biological age) x the sex's rate.
CHILD_WORK_AGE = 10            # calendar: the 10-14s work at the childrens'-rights law's share (parent §7)
WORKING_AGE = 15               # calendar: everyone from here
CHILD_WORK_SHARE = {"law_child_labor_allowed": 0.3, "law_restricted_child_labor": 0.1,
                    "law_compulsory_primary_school": 0.0}
CHILD_WORK_SHARE_DEFAULT = 0.3  # a country with none of the three (vanilla gives every country one)
CAPACITY = {0: 1.0, 60: 0.95, 65: 0.85, 70: 0.7, 75: 0.5, 80: 0.3, 85: 0.1}   # by biological band start
AFTER_PENSION_SHARE = 0.15     # the share of the eligible who keep working, x capacity
MEN_RATE = 0.92
WOMEN_BASE = 0.05              # the middle and upper strata's women under No Women's Rights
WOMEN_LOWER = 0.2              # the lower strata's women under any law (Goldin's U-shape)
WOMENS_WORK_FULL = 0.30        # the women's-work family's sum at which women work at the men's rate
WORKFORCE_SCALE = 0.74         # participation to the engine's ratio (the spec's §1.8 sketch: 1836 0.25, rich 0.40)
# Health need by biological band start (late-game §5.2), and 1836's people-weighted need (the figure's 1.0).
HEALTH_NEED = {0: 1.0, 5: 0.5, 15: 0.8, 45: 1.4, 65: 2.4, 75: 3.4, 85: 4.5}
HEALTH_NEED_1836 = 0.95
BIO_BANDS = tuple(sorted(set(CAPACITY) | set(HEALTH_NEED)))
# The pension positions' ages (late-game §2.2). Step 1 sets a country's pension age to the Standard one under Old Age
# Pension; step 2 adds the setting.
PENSION_AGE = {"early": 60, "standard": 65, "raised": 70}
PENSION_LAW = "law_old_age_pension"
NO_PENSION_AGE_LAWS = ("law_universal_basic_income", "law_post-scarcity")  # the threshold ends the working ages
NO_WORKING_AGE_END = 999       # no pension law: the working ages run to capacity's end, which never comes (D10)
OLD_AGE_REMAINING = 15         # the old-age threshold: years of life left (Sanderson and Scherbov)
OLD_AGE_FROM = 40              # its search's first group start
# Planned and unplanned births (late-game §3.1): one schedule each, the same object until phase 3. While they are,
# the generator writes the sweep's birth line as today's single term.
ASFR_PLANNED_SHAPE = ASFR_SHAPE_BY_GROUP
ASFR_UNPLANNED_SHAPE = ASFR_SHAPE_BY_GROUP
# The pops' own working-adult ratios (vanilla pop_types; the rest take the define WORKING_ADULT_RATIO_BASE).
POP_BASE_RATIO = {"aristocrats": 0.2, "slaves": 0.5}
POP_BASE_RATIO_DEFAULT = 0.25
# The working-adult lines' two script-only families (Task 6; demographics_workforce_line_types.txt).
WOMENS_WORK_TYPE = "state_demog_womens_work_ratio_add"
REPLACED_TYPE = "state_demog_replaced_ratio_add"   # lines a census term replaces under Full (the design §1.7)
# Call 3's participation inputs (owner, 2026-10-12; the design §1.7): census-only types, defined in Task 5 and joining
# DEMOG_TYPES with their carriers in Task 6.
MALE_PARTICIPATION_TYPE = "state_male_labor_participation_add"   # the men's rate in the working ages
PARTICIPATION_TYPE = "state_labor_participation_add"             # both sexes' rates in the working ages
CAPACITY_TYPE = "state_work_capacity_mult"                       # capacity x (1 + it), at every age
PARTICIPATION_TYPES = (MALE_PARTICIPATION_TYPE, PARTICIPATION_TYPE, CAPACITY_TYPE)
```

- [ ] **Step 4: The model** (`demographics_model.py`)

`Inputs` gains, at the end (after #906's fields):

```python
    low_share: float = 0.0               # the lower strata's share of people (te_dg_low_share, from the walk)
    pension_age: float | None = None     # the owner's pension age under Old Age Pension; None = the Standard position
```

`fertility` keeps its arithmetic. Assign the dict it returns to a name (`out` here; #906 may already have one), add
the two parts, then return it:

```python
    # planned and unplanned births (late-game §3.1): the families who choose their number, and the births the means
    # don't reach. Computed from the result's own tfr and factor, so every term multiplying the factor (wealth,
    # natural, #906's practices) scales both parts alike.
    out["planned"] = out["tfr"] / out["factor"] * out["means"] * desired
    out["unplanned"] = out["tfr"] / out["factor"] * (1 - out["means"])
```

New functions after `asfr_shape`:

```python
def asfr_planned(rate_age):
    """Planned births' share at a calendar rate age, per 100k (P.ASFR_PLANNED_SHAPE)."""
    if rate_age < 15 or rate_age > 49:
        return 0.0
    return P.ASFR_PLANNED_SHAPE[rate_age - rate_age % 5] / 5.0


def asfr_unplanned(rate_age):
    """Unplanned births' share at a biological rate age, per 100k (P.ASFR_UNPLANNED_SHAPE)."""
    if rate_age < 15 or rate_age > 49:
        return 0.0
    return P.ASFR_UNPLANNED_SHAPE[rate_age - rate_age % 5] / 5.0


def slot_births(f, r, rb, tfr, planned_share):
    """One cohort's births (te_demog_slot_births). While the two schedules are the same object, today's line exactly;
    otherwise planned by the calendar rate age r and unplanned by the biological rate age rb."""
    if P.ASFR_PLANNED_SHAPE is P.ASFR_UNPLANNED_SHAPE:
        return f * asfr_shape(r) / 100000.0 * tfr
    mix = asfr_planned(r) * planned_share + asfr_unplanned(rb) * (1 - planned_share)
    return mix * f / 100000.0 * tfr


def band_value(table, age):
    """A {first age: value} table's value at an age (P.CAPACITY, P.HEALTH_NEED)."""
    return table[max(k for k in table if k <= age)]


def child_work_share(inp):
    """The 10-14s' participation by the childrens'-rights law (te_demog_child_work)."""
    for law, share in P.CHILD_WORK_SHARE.items():
        if law in inp.laws:
            return share
    return P.CHILD_WORK_SHARE_DEFAULT


def start_factor(inp, age):
    """The working-age start by calendar age (te_demog_enter_cal_band)."""
    if age < P.CHILD_WORK_AGE:
        return 0.0
    if age < P.WORKING_AGE:
        return child_work_share(inp)
    return 1.0


def women_rate_law(inp):
    """Women's participation by the women's-work family (#894): WOMEN_BASE up to MEN_RATE as its sum reaches
    WOMENS_WORK_FULL (te_demog_women_rate_law)."""
    s = min(max(inp.mods.get(P.WOMENS_WORK_TYPE, 0.0), 0.0) / P.WOMENS_WORK_FULL, 1.0)
    return s * (P.MEN_RATE - P.WOMEN_BASE) + P.WOMEN_BASE


def women_rate(inp):
    """The state's women's rate: its lower strata's women work at least WOMEN_LOWER (te_demog_women_rate)."""
    w = women_rate_law(inp)
    return (max(w, P.WOMEN_LOWER) - w) * inp.low_share + w


def sex_rates(inp):
    """(women's, men's) rates in the working ages with call 3's participation inputs, each 0 to 1 (te_dg_wk_rf,
    te_dg_wk_rm in te_demog_work_setup)."""
    both = inp.mods.get(P.PARTICIPATION_TYPE, 0.0)
    rf = min(max(women_rate(inp) + both, 0.0), 1.0)
    rm = min(max(P.MEN_RATE + inp.mods.get(P.MALE_PARTICIPATION_TYPE, 0.0) + both, 0.0), 1.0)
    return rf, rm


def capacity_at(inp, age):
    """Capacity at a biological age with call 3's input: the table x (1 + it), 0 to 1 (te_demog_enter_bio_band)."""
    return min(band_value(P.CAPACITY, age) * max(1 + inp.mods.get(P.CAPACITY_TYPE, 0.0), 0.0), 1.0)


def pension_kind(inp):
    """1 under Old Age Pension; 2 under UBI or Post-Scarcity (no pension age); else 0 (te_demog_pension_kind)."""
    if P.PENSION_LAW in inp.laws:
        return 1
    if any(law in inp.laws for law in P.NO_PENSION_AGE_LAWS):
        return 2
    return 0


def working_ages_end(inp, old_age):
    """(the end of the working ages, whether the after-pension share applies past it, whether those past it are
    pensioners): te_demog_work_setup. With no pension law the working ages run to capacity's end (late-game §2.1), which
    never comes: NO_WORKING_AGE_END."""
    kind = pension_kind(inp)
    if kind == 1:
        return (P.PENSION_AGE["standard"] if inp.pension_age is None else inp.pension_age), True, True
    if kind == 2:
        return old_age, True, False
    return float(P.NO_WORKING_AGE_END), False, False


def work_figures(ring, inp, old_age):
    """Phase 2 step 1's figures over ring.by_age() (ages after the step; the pool at 150): te_demog_work_slot and
    te_demog_work_finish. The biological age is the calendar one until phase 3."""
    end, after_on, bill_on = working_ages_end(inp, old_age)
    rate_f, rate_m = sex_rates(inp)
    total = wa = workers = pens = need = 0.0
    for a, f, m in ring.by_age():
        ab = a                                  # the biological index (phase 3: less the band's deficit)
        p = f + m
        total += p
        need += p * band_value(P.HEALTH_NEED, ab)
        start = start_factor(inp, a)
        share = 1.0
        if a >= end:
            if after_on:
                share = P.AFTER_PENSION_SHARE
            if bill_on:
                pens += p
        elif start > 0:
            wa += p
        workers += (f * rate_f + m * rate_m) * start * capacity_at(inp, ab) * share
    return {"wa_share": wa / max(total, 1.0), "at_work": workers / max(wa, 1.0),
            "pensioners": pens / max(total, 1.0), "need": need / max(total, 1.0) / P.HEALTH_NEED_1836}


def wf_target(figures):
    """The workforce share on the engine's scale (te_demog_wf_target; step 2's target less the pops' bases)."""
    return P.WORKFORCE_SCALE * figures["wa_share"] * figures["at_work"]


def old_age_threshold(q):
    """The age with OLD_AGE_REMAINING years of life left (late-game §1.5) from one sex's group rates: remaining life at
    each group start from OLD_AGE_FROM, linear between starts. Radix 100,000, as te_demog_old_age_pass."""
    l, py, at = 100000.0, 0.0, []
    for g, (start, n) in enumerate(P.GROUPS):
        if start >= P.OLD_AGE_FROM:
            at.append((start, l, py))
        qq = q[g] / 100000.0
        pn = (1.0 - qq) ** n
        py += l * n if qq == 0 else l * (1 - qq / 2) * (1 - pn) / qq
        l *= pn
    prev = None
    for start, l_s, py_s in at:
        e = (py - py_s) / max(l_s, 0.00001)
        if e <= P.OLD_AGE_REMAINING:
            if prev is None:
                return float(start)
            s0, e0 = prev
            return (e0 - P.OLD_AGE_REMAINING) / max(e0 - e, 0.00001) * (start - s0) + s0
        prev = (start, e)
    return float(at[-1][0])


def old_age(qf, qm):
    """The state's old-age threshold: women's and men's averaged (te_dg_old_age)."""
    return (old_age_threshold(qf) + old_age_threshold(qm)) * 0.5
```

In `step`, the birth line `b = f * asfr_shape(r) / 100000.0 * tfr` becomes:

```python
        b = slot_births(f, r, r, tfr, planned_share)
```

with, after `fert` is set in both branches (`rates` given: one schedule only):

```python
    if rates is None:
        planned_share = fert["planned"] / fert["tfr"] if fert["tfr"] else 1.0
    else:
        assert P.ASFR_PLANNED_SHAPE is P.ASFR_UNPLANNED_SHAPE, "a replay logs one schedule"
        planned_share = 1.0
```

- [ ] **Step 5: Run the model's tests and the golden**

Run: `$V -m unittest test_demographics_model test_demographics_golden -v 2>&1 | grep -E '^(Ran |OK|FAILED)'`
Expected: OK. `test_the_targets_at_the_starting_values` checks the spec's sketch (0.25 ± 0.02; old age 59.3 ± 1).

- [ ] **Step 6: Commit**: "Demographics phase 2 step 1: the model's participation, need, threshold and birth parts".

---

### Task 3: The generator: bands, the threshold pass, the birth line, constants and values (review stop)

**Files:**
- Modify: `scripts/generators/gen_demographics.py` (`enter_group`, `life_table`, `render_effects`, `constants`,
  `render_values`; new `work_bands`, `old_age_pass`, `slot_births`, `work_values`)
- Modify: `common/scripted_effects/te_demog_effects.txt` (`te_demog_age_slot`'s birth block)
- Regenerate: `te_demog_generated_effects.txt`, `te_demog_generated_values.txt`
- Test: `test_gen_demographics.py` (new class `TestPhase2Generated`); `test_demographics_registry.py` (new class
  `TestOldAgeScript`, `TestSlotBirthsScript`)

**Interfaces:**
- Consumes: Task 2's parameters and model functions.
- Produces (script):
  - `te_demog_enter_cal_band` (reads `local_var:te_dg_cal`; sets `te_dg_start`, `te_dg_next_cal`; band 1 reads
    `local_var:te_dg_child_work`);
  - `te_demog_enter_bio_band` (reads `local_var:te_dg_bio`; sets `te_dg_cap`, `te_dg_needw`, `te_dg_next_bio`);
  - `te_demog_old_age_pass` (called at the end of `te_demog_life_table`; sets `var:te_dg_old_age`);
  - `te_demog_slot_births` (sets `local_var:te_dg_b`);
  - values `te_demog_child_work` (state), `te_demog_pop_base_ratio` (pop), constants `te_demog_k_child_work_age`,
    `_working_age`, `_after_pension_share`, `_men_rate`, `_women_base`, `_women_lower`, `_womens_work_full`,
    `_workforce_scale`, `_health_need_1836`, `_need_newborn`, `_pension_age_standard`.

- [ ] **Step 1: Write the failing tests** (`test_gen_demographics.py`)

```python
class TestPhase2Generated(unittest.TestCase):
    """Phase 2 step 1 (the interfaces plan, Task 3)."""

    @classmethod
    def setUpClass(cls):
        cls.effects = gen.render_effects()
        cls.values = gen.render_values(ROOT)

    def test_the_birth_line_is_todays_while_the_schedules_are_one(self):
        body = re.search(r"^te_demog_slot_births = \{\n(.*?)^\}", self.effects, re.M | re.S).group(1)
        self.assertIn("value = { value = local_var:te_dg_f multiply = local_var:te_dg_asfr divide = 100000 "
                      "multiply = local_var:te_dg_tfr }", body)
        self.assertNotIn("te_dg_asfr_un", self.effects)

    def test_two_schedules_write_two_terms(self):
        other = {15: 10000, 20: 30000, 25: 30000, 30: 20000, 35: 7000, 40: 2500, 45: 500}
        with unittest.mock.patch.object(P, "ASFR_UNPLANNED_SHAPE", other):
            text = gen.render_effects()
        self.assertIn("te_dg_asfr_un", text)
        self.assertIn("multiply = local_var:te_dg_sh_pl", text)

    def test_the_bands_are_the_tables(self):
        for a in P.BIO_BANDS:
            self.assertIn(f"value = {{ value = {gen.lit(M.band_value(P.CAPACITY, a))} multiply = local_var:te_dg_wk_capm "
                          "max = 1 }", self.effects)
        self.assertRegex(self.effects, r"te_demog_enter_cal_band = \{")
        self.assertRegex(self.effects, r"te_demog_enter_bio_band = \{")

    def test_the_life_table_ends_with_the_threshold(self):
        lt = re.search(r"^te_demog_life_table = \{\n(.*?)^\}", self.effects, re.M | re.S).group(1)
        self.assertTrue(lt.rstrip().endswith("te_demog_old_age_pass = yes"))
        for start, _w in P.GROUPS:
            stored = f"name = te_dg_oal{start}f" in lt
            self.assertEqual(stored, start >= P.OLD_AGE_FROM, start)

    def test_the_constants(self):
        for name, v in (("men_rate", P.MEN_RATE), ("workforce_scale", P.WORKFORCE_SCALE),
                        ("pension_age_standard", P.PENSION_AGE["standard"]),
                        ("health_need_1836", P.HEALTH_NEED_1836)):
            self.assertIn(f"te_demog_k_{name} = {{ value = {gen.lit(v)} }}", self.values)
```

Add `import unittest.mock` and `import demographics_model as M  # noqa: E402` at the top.

In `test_demographics_registry.py`:

```python
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
                              te_dg_m_inf=1.0, te_dg_m_work_f=1.0, te_dg_m_work_m=1.0, te_dg_m_ext=1.0,
                              te_dg_m_chr=1.0)
            eng.call("te_demog_enter_group")
            eng.call("te_demog_slot_births")
            want = demographics_model.slot_births(1000.0, 27, 27, 4.0, 0.25)
        self.assertAlmostEqual(eng.locals["te_dg_b"], want)
```

At the top of `test_demographics_registry.py`, beside the other imports: `import gen_demographics  # noqa: E402`
(with `sys.path.insert(0, str(ROOT / "scripts" / "generators"))` if it isn't already on the path).

- [ ] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_gen_demographics.TestPhase2Generated test_demographics_registry.TestOldAgeScript test_demographics_registry.TestSlotBirthsScript -v`
Expected: FAIL (no `te_demog_slot_births`, no `te_dg_old_age`).

- [ ] **Step 3: The generator** (`gen_demographics.py`)

`enter_group`'s leaf, after the `te_dg_asfr` line:

```python
        if P.ASFR_PLANNED_SHAPE is not P.ASFR_UNPLANNED_SHAPE:
            # the unplanned schedule (late-game §3.1); its rate age is the calendar one until phase 3's per-slot lookup
            o(f"set_local_variable = {{ name = te_dg_asfr_un value = {lit(M.asfr_unplanned(start))} }}")
```

and `te_dg_asfr` uses `M.asfr_planned(start)` in place of `M.asfr_shape(start)` (the same value while the two are one).

`life_table`, inside the loop, after `te_demog_enter_group = yes` and before the `start == 65` block:

```python
        if start >= P.OLD_AGE_FROM:
            # survivors and person-years at the group's start, for the old-age threshold (te_demog_old_age_pass)
            for s in "fm":
                o(f"set_local_variable = {{ name = te_dg_oal{start}{s} value = local_var:te_dg_l{s} }}")
                o(f"set_local_variable = {{ name = te_dg_oapy{start}{s} value = local_var:te_dg_py{s} }}")
```

and after `o("te_demog_lt_finish = yes")`: `o("te_demog_old_age_pass = yes")`.

New functions:

```python
def old_age_pass(o):
    starts = [s for s, _w in P.GROUPS if s >= P.OLD_AGE_FROM]
    rem = P.OLD_AGE_REMAINING
    o("# THIS = a state, after te_demog_life_table's forward pass (phase 2 step 1; late-game §1.5): the age with")
    o(f"# {rem} years of life left (demographics_model.old_age_threshold), women's and men's averaged, into")
    o("# te_dg_old_age. Remaining life at each group start from OLD_AGE_FROM; linear between starts.")
    o("te_demog_old_age_pass = {")
    for s in "fm":
        for st in starts:
            o(f"set_local_variable = {{ name = te_dg_oae{st}{s} value = {{ value = local_var:te_dg_py{s} "
              f"subtract = local_var:te_dg_oapy{st}{s} divide = {{ value = local_var:te_dg_oal{st}{s} "
              f"min = 0.00001 }} }} }}")
        prev = None
        for st in starts:
            o(f"{'if' if prev is None else 'else_if'} = {{")
            o(f"limit = {{ local_var:te_dg_oae{st}{s} <= {rem} }}")
            if prev is None:
                o(f"set_local_variable = {{ name = te_dg_oa{s} value = {st} }}")
            else:
                o(f"set_local_variable = {{ name = te_dg_oa{s} value = {{ value = local_var:te_dg_oae{prev}{s} "
                  f"subtract = {rem} divide = {{ value = local_var:te_dg_oae{prev}{s} "
                  f"subtract = local_var:te_dg_oae{st}{s} min = 0.00001 }} multiply = {st - prev} add = {prev} }} }}")
            o("}")
            prev = st
        o("else = {")
        o(f"set_local_variable = {{ name = te_dg_oa{s} value = {starts[-1]} }}")
        o("}")
    o("set_variable = { name = te_dg_old_age value = { value = local_var:te_dg_oaf add = local_var:te_dg_oam "
      "multiply = 0.5 } }")
    o("}")
    o("")


def work_bands(o):
    cal = (0, P.CHILD_WORK_AGE, P.WORKING_AGE)
    o("# THIS = a state, in the sweep's age order (phase 2 step 1): the calendar band local_var:te_dg_cal sets")
    o("# te_dg_start, the working-age start's factor (demographics_model.start_factor), and te_dg_next_cal.")
    o("te_demog_enter_cal_band = {")

    def cal_leaf(o, i):
        start = {0: "0", 1: "local_var:te_dg_child_work", 2: "1"}[i]
        o(f"set_local_variable = {{ name = te_dg_start value = {start} }}")
        o(f"set_local_variable = {{ name = te_dg_next_cal value = {cal[i + 1] if i + 1 < len(cal) else 999} }}")

    tree(o, "te_dg_cal", 0, len(cal) - 1, cal_leaf)
    o("}")
    o("")
    o("# THIS = a state: the biological band local_var:te_dg_bio (P.BIO_BANDS) sets te_dg_cap (capacity), te_dg_needw")
    o("# (health need) and te_dg_next_bio. Its age is te_dg_ab, the calendar one until phase 3.")
    o("te_demog_enter_bio_band = {")
    bio = P.BIO_BANDS

    def bio_leaf(o, i):
        a = bio[i]
        # call 3's capacity input (te_dg_wk_capm, te_demog_work_setup) x the table, at most 1 (demographics_model.capacity_at)
        o(f"set_local_variable = {{ name = te_dg_cap value = {{ value = {lit(M.band_value(P.CAPACITY, a))} "
          "multiply = local_var:te_dg_wk_capm max = 1 } }")
        o(f"set_local_variable = {{ name = te_dg_needw value = {lit(M.band_value(P.HEALTH_NEED, a))} }}")
        o(f"set_local_variable = {{ name = te_dg_next_bio value = {bio[i + 1] if i + 1 < len(bio) else 999} }}")

    tree(o, "te_dg_bio", 0, len(bio) - 1, bio_leaf)
    o("}")
    o("")


def slot_births(o):
    o("# THIS = a state, in te_demog_age_slot: births from the cohort's women local_var:te_dg_f")
    o("# (demographics_model.slot_births). Planned births follow P.ASFR_PLANNED_SHAPE by calendar age and unplanned")
    o("# P.ASFR_UNPLANNED_SHAPE by biological age (late-game §3.1). While they are one schedule this is one term.")
    o("te_demog_slot_births = {")
    o("set_local_variable = {")
    o("name = te_dg_b")
    if P.ASFR_PLANNED_SHAPE is P.ASFR_UNPLANNED_SHAPE:
        o("value = { value = local_var:te_dg_f multiply = local_var:te_dg_asfr divide = 100000 "
          "multiply = local_var:te_dg_tfr }")
    else:
        o("value = {")
        o("value = local_var:te_dg_asfr")
        o("multiply = local_var:te_dg_sh_pl")
        o("add = { value = local_var:te_dg_asfr_un multiply = local_var:te_dg_sh_un }")
        o("multiply = local_var:te_dg_f")
        o("divide = 100000")
        o("multiply = local_var:te_dg_tfr")
        o("}")
    o("}")
    o("}")
    o("")


def work_values(o):
    o("# State scope (phase 2 step 1): the 10-14s' participation by the owner's childrens'-rights law")
    o("# (demographics_model.child_work_share).")
    o("te_demog_child_work = {")
    o(f"value = {lit(P.CHILD_WORK_SHARE_DEFAULT)}")
    for law, share in P.CHILD_WORK_SHARE.items():
        o(f"if = {{ limit = {{ owner = {{ has_law = law_type:{law} }} }} value = {lit(share)} }}")
    o("}")
    o("# Pop scope: the pop's own working-adult ratio (vanilla pop_types; the define for the rest).")
    o("te_demog_pop_base_ratio = {")
    o(f"value = {lit(P.POP_BASE_RATIO_DEFAULT)}")
    for pop_type, ratio in P.POP_BASE_RATIO.items():
        o(f"if = {{ limit = {{ is_pop_type = {pop_type} }} value = {lit(ratio)} }}")
    o("}")
    o("")
```

`render_effects`: after `life_table(o)` add `old_age_pass(o)`, `work_bands(o)` and `slot_births(o)`.
`render_values`: after `constants(o)` add `work_values(o)`. `constants`' dict gains:

```python
        "child_work_age": P.CHILD_WORK_AGE, "working_age": P.WORKING_AGE,
        "after_pension_share": P.AFTER_PENSION_SHARE, "men_rate": P.MEN_RATE, "women_base": P.WOMEN_BASE,
        "women_lower": P.WOMEN_LOWER, "womens_work_full": P.WOMENS_WORK_FULL,
        "workforce_scale": P.WORKFORCE_SCALE, "health_need_1836": P.HEALTH_NEED_1836,
        "need_newborn": M.band_value(P.HEALTH_NEED, 0), "pension_age_standard": P.PENSION_AGE["standard"],
```

- [ ] **Step 4: The birth line moves** (`te_demog_effects.txt`, `te_demog_age_slot`)

Replace

```
	# births from these women (rate ages 15-49 carry a non-zero te_dg_asfr)
	set_local_variable = {
		name = te_dg_b
		value = { value = local_var:te_dg_f multiply = local_var:te_dg_asfr divide = 100000 multiply = local_var:te_dg_tfr }
	}
```

with

```
	# births from these women (rate ages 15-49 carry a non-zero te_dg_asfr); generated: planned and unplanned
	te_demog_slot_births = yes
```

- [ ] **Step 5: Regenerate, then run the generator's tests, the registry and the golden**

Run: `$V scripts/generators/gen_demographics.py && $V -m unittest test_gen_demographics test_demographics_registry test_demographics_golden 2>&1 | grep -E '^(Ran |OK|FAILED)'`
Expected: OK. The golden now sees `te_dg_old_age` (allowed) and nothing else new.

- [ ] **Step 6: Commit**: "Demographics phase 2 step 1: the generator's bands, threshold and birth line".

- [ ] **Review stop:** a fresh reviewer reads Tasks 2–3 against the spec's §1.1, §1.3–§1.6 and D1, D9, and checks that
  `te_demog_slot_births` is today's line byte for byte.

---

### Task 4: The pension age

**Files:**
- Modify: `common/scripted_effects/te_demog_effects.txt` (new `te_demog_pension_age_refresh`; calls in
  `te_demog_country_game_start` and `te_demog_country_yearly`)
- Modify: `common/scripted_triggers/te_demog_triggers.txt` (`te_demog_has_pension_law`)
- Modify: `common/on_actions/te_demog_on_actions.txt` (`te_demog_pension_law_on_action` under `on_law_activated`)
- Modify: `common/script_values/te_demog_values.txt` (`te_demog_pension_kind`, `te_demog_pension_age`)
- Test: `test_demographics_registry.py` (new class `TestPensionAge`)

**Interfaces:**
- Produces: country variable `te_dg_pension_age` (Old Age Pension only); state values `te_demog_pension_kind`
  (0, 1, 2) and `te_demog_pension_age`; trigger `te_demog_has_pension_law` (country).

- [ ] **Step 1: Write the failing tests**

First, in `_Engine.__init__`, the default `self.trigger_fixtures` gains `"te_demog_has_pension_law": False`, so an
engine that runs `te_demog_country_game_start` or `te_demog_country_yearly` without saying (`TestCountry`'s
`test_game_start_ends_with_the_census` and the like) never evaluates `has_law`, which `_Engine` doesn't know.

```python
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
```

- [ ] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_registry.TestPensionAge -v`
Expected: FAIL (`te_demog_pension_age_refresh` not found).

- [ ] **Step 3: The script**

`te_demog_triggers.txt`:

```
# THIS = a country: it pays an old-age pension (phase 2 step 1). UBI and Post-Scarcity replace it and have no pension age.
te_demog_has_pension_law = {
	has_law = law_type:law_old_age_pension
}
```

`te_demog_effects.txt`, beside `te_demog_country_yearly`:

```
# THIS = a country (phase 2 step 1; docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §1.2):
# its pension age, the one number every reader takes through te_demog_pension_age. Under Old Age Pension the Standard
# position's age (step 2 adds the setting); otherwise none. A revolution's winner inherits it.
te_demog_pension_age_refresh = {
	if = {
		limit = { te_demog_has_pension_law = yes }
		set_variable = { name = te_dg_pension_age value = te_demog_k_pension_age_standard }
	}
	else_if = {
		limit = { has_variable = te_dg_pension_age }
		remove_variable = te_dg_pension_age
	}
}
```

Call `te_demog_pension_age_refresh = yes` first in `te_demog_country_game_start` (before any state is seeded) and first
in `te_demog_country_yearly`.

`te_demog_on_actions.txt`: add `te_demog_pension_law_on_action` to `on_law_activated`'s list, and

```
# ROOT = the law just activated: its owner's pension age, that day (phase 2 step 1).
te_demog_pension_law_on_action = {
	effect = {
		owner = {
			te_demog_pension_age_refresh = yes
		}
	}
}
```

`te_demog_values.txt`:

```
# State scope (phase 2 step 1): 1 under Old Age Pension, 2 under UBI or Post-Scarcity (no pension age: the old-age
# threshold ends the working ages), else 0 (demographics_model.pension_kind). The welfare group holds one of them.
te_demog_pension_kind = {
	value = 0
	if = {
		limit = { owner = { OR = { has_law = law_type:law_universal_basic_income has_law = law_type:law_post-scarcity } } }
		value = 2
	}
	if = {
		limit = { owner = { te_demog_has_pension_law = yes } }
		value = 1
	}
}
# State scope: the owner's pension age, or the Standard position's where it has none yet (a save from before step 1).
# The owner.var read follows te_tax_est_regrel_keep_now (te_tax_display_values.txt:639), guarded the same way.
te_demog_pension_age = {
	value = te_demog_k_pension_age_standard
	if = {
		limit = { owner ?= { has_variable = te_dg_pension_age } }
		value = owner.var:te_dg_pension_age
	}
}
```

The interpreter replaces `te_demog_pension_age` with a fixture (`_engine_for`, `WORK_DEFAULTS`), and in step 1 it reads
65 whether the variable is there or not, so the chain read is checked in game: Task 7's `pension_var=` and Task 8's
item 5.

- [ ] **Step 4: Run the tests and the golden**

Run: `$V -m unittest test_demographics_registry test_demographics_golden 2>&1 | grep -E '^(Ran |OK|FAILED)'`
Expected: OK.

- [ ] **Step 5: Commit**: "Demographics phase 2 step 1: the pension age, one country variable".

---

### Task 5: The census computes the figures (review stop)

**Files:**
- Modify: `common/scripted_effects/te_demog_effects.txt`:
  - `te_demog_walks`: three sums under the cohorts;
  - `te_demog_prepare`: `te_demog_work_setup = yes` last;
  - `te_demog_reset_accumulators`, `te_demog_age_boundaries`, `te_demog_accumulate_slot`;
  - `te_demog_seed` (after `te_demog_close_accumulators = yes`) and `te_demog_step_finish` (after the newborns join
    `te_dg_raw`): `te_demog_work_finish`;
  - new `te_demog_work_setup`, `te_demog_work_walk_init`, `_walk_pop`, `_walk_store`, `te_demog_work_slot`,
    `te_demog_work_finish`;
  - the header inventory lists `te_dg_wa_share`, `_at_work`, `_pensioners`, `_need`, `_old_age`, `_low_share`,
    `_wbase`, `_wf_engine`.
- Modify: `common/modifier_type_definitions/demographics_modifier_types.txt`, `localization/english/te_modifiers_l_english.yml`
  (call 3's three participation inputs)
- Modify: `common/script_values/te_demog_values.txt` (`te_demog_women_rate_law`, `te_demog_women_rate`,
  `te_demog_low_share`, `te_demog_tfr_factor`, `te_demog_tfr_planned`, `te_demog_tfr_unplanned`,
  `te_demog_tfr_planned_share`, `te_demog_wf_target`, `te_demog_old_age_average`, `te_demog_old_age_common`)
- Test: `test_demographics_registry.py` (`_mod_fixtures`, `_engine_for`, `TestCohortScript.seed_both` /
  `step_both` gain an optional `inp`; new tests in `TestCohortScript`; new class `TestWorkWalk`)

**Interfaces:**
- Consumes: Task 3's generated bands, constants and values; Task 4's `te_demog_pension_kind`, `te_demog_pension_age`.
- Produces: the eight state variables of the golden's `NEW_VARS` (all but the pair's sum), at every seed and step
  wherever the cohorts run (the walk's three at every walk under the cohorts); the script values above.

- [ ] **Step 1: Give the interpreter the new reads** (`test_demographics_registry.py`)

Every engine that runs `te_demog_prepare` now reads four owner values; most tests build through `_engine_for`, but some
(`TestFastMode`'s `_eng`, `_CountryEngine`'s states) don't. So `_Engine` gets defaults, which any fixture overrides:

```python
# The owner's reads phase 2 step 1's census makes (te_demog_work_setup), for engines that don't give them.
WORK_DEFAULTS = {"te_demog_child_work": P.CHILD_WORK_SHARE_DEFAULT, "te_demog_pension_kind": 0.0,
                 "te_demog_pension_age": float(P.PENSION_AGE["standard"]), f"modifier:{P.WOMENS_WORK_TYPE}": 0.0,
                 **{f"modifier:{t}": 0.0 for t in P.PARTICIPATION_TYPES}}
```

and in `_Engine.__init__`, `self.fixtures = dict(fixtures)` becomes `self.fixtures = {**WORK_DEFAULTS, **fixtures}`.

`_mod_fixtures` adds the women's-work family:

```python
    for t in (P.WOMENS_WORK_TYPE, *P.PARTICIPATION_TYPES):
        out[f"modifier:{t}"] = inp.mods.get(t, 0.0)
```

`_engine_for`'s fixtures add the owner's reads, and its `eng.vars.update` the walk's lower strata:

```python
        "te_demog_child_work": demographics_model.child_work_share(inp),
        "te_demog_pension_kind": float(demographics_model.pension_kind(inp)),
        "te_demog_pension_age": float(inp.pension_age if inp.pension_age is not None else P.PENSION_AGE["standard"]),
```

```python
    eng.vars.update(te_dg_low_share=inp.low_share)
```

`TestCohortScript.seed_both(self, inp=None)` and `step_both(self, ..., inp=None)`: each uses `base = inp or self.INP`
wherever it now reads `self.INP` (default unchanged, so every existing test runs as before).

- [ ] **Step 2: Write the failing tests** (in `TestCohortScript`, and a new `TestWorkWalk`)

```python
    WORK = dict(laws=frozenset({"law_women_in_the_fields", "law_restricted_child_labor", "law_old_age_pension"}),
                low_share=0.7, pension_age=67.0)

    def _work_inp(self, **kw):
        inp = dataclasses.replace(self.INP, **{**self.WORK, **kw})
        inp.mods = {**inp.mods, P.WOMENS_WORK_TYPE: 0.15, P.MALE_PARTICIPATION_TYPE: 0.02,
                    P.PARTICIPATION_TYPE: 0.01, P.CAPACITY_TYPE: -0.05}   # call 3's inputs ride through the figures
        return inp

    def _work_figures(self, eng, ring, inp):
        qf, qm, _ = demographics_model.group_rates(dataclasses.replace(inp, medicine=ring.medicine))
        want = demographics_model.work_figures(ring, inp, demographics_model.old_age(qf, qm))
        for name in ("wa_share", "at_work", "pensioners", "need"):
            self.close(eng.vars[f"te_dg_{name}"], want[name], rel=1e-4, what=name)

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
```

```python
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
        eng = _Engine({}, triggers={"te_demog_cohorts_run": True})
        eng.call("te_demog_work_walk_init")
        eng.locals.update(te_dg_w_pop=1000.0, te_dg_w_low=800.0, te_dg_w_wbase=260.0, te_dg_w_wf=250.0)
        eng.call("te_demog_work_walk_store")
        self.assertEqual((eng.vars["te_dg_low_share"], eng.vars["te_dg_wbase"], eng.vars["te_dg_wf_engine"]),
                         (0.8, 0.26, 0.25))

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
        pops = (("aristocrats", "upper", 100.0, 18.0), ("slaves", "lower", 400.0, 210.0),
                ("laborers", "lower", 500.0, 130.0))
        for pop_type, strata, size, workforce in pops:
            eng.pop_type, eng.strata = pop_type, strata
            eng.fixtures.update(total_size=size, workforce=workforce)
            eng.call("te_demog_work_walk_pop")
        eng.locals["te_dg_w_pop"] = 1000.0          # the walk's own people sum (te_demog_walks keeps it)
        eng.call("te_demog_work_walk_store")
        self.assertAlmostEqual(eng.vars["te_dg_low_share"], (400 + 500) / 1000)
        self.assertAlmostEqual(eng.vars["te_dg_wbase"], (100 * 0.2 + 400 * 0.5 + 500 * 0.25) / 1000)
        self.assertAlmostEqual(eng.vars["te_dg_wf_engine"], (18 + 210 + 130) / 1000)

    def test_the_figures_are_stored_where_the_denominator_is_whole(self):
        """D4: in the seed straight after the accumulators close, in the step after the newborns join te_dg_raw."""
        effects = _text(EFFECTS)
        seed = _block(effects, "te_demog_seed")
        self.assertLess(seed.index("te_demog_close_accumulators = yes"), seed.index("te_demog_work_finish = yes"))
        self.assertLess(seed.index("te_demog_work_finish = yes"), seed.index("te_demog_normalize_slots = yes"))
        finish = _block(effects, "te_demog_step_finish")
        self.assertLess(finish.index("change_local_variable = { name = te_dg_raw add = local_var:te_dg_births }"),
                        finish.index("te_demog_work_finish = yes"))
```

- [ ] **Step 3: Run them to see them fail**

Run: `$V -m unittest test_demographics_registry.TestCohortScript test_demographics_registry.TestWorkWalk -v 2>&1 | grep -E '^(Ran |OK|FAILED)|Error'`
Expected: FAIL (`te_dg_wa_share` missing; `te_demog_work_walk_pop` not found).

- [ ] **Step 4: The participation inputs' types** (call 3; `demographics_modifier_types.txt`, at its end, and
  `te_modifiers_l_english.yml` beside `state_work_mortality_mult`). Their carriers come in Task 6. The names start
  "Census:" so a carrier's tooltip doesn't read them as adding to its "Workforce Ratio" line, which they replace under
  Full (spec §1.7).

```
# Phase 2 step 1 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §1.7; the owner's call 3):
# the census's participation inputs, carried beside the replaced family's flat lines. Census-only: a release comments
# their lines out.
state_male_labor_participation_add = {
	color = good
	percent = yes
	decimals = 1
	script_only = yes
}
state_labor_participation_add = {
	color = good
	percent = yes
	decimals = 1
	script_only = yes
}
state_work_capacity_mult = {
	color = good
	percent = yes
	decimals = 0
	script_only = yes
}
```

```
 state_male_labor_participation_add:0 "Census: Men at Work"
 state_male_labor_participation_add_desc:0 "The share of working-age men who work. Used by the census on the Demographics tab."
 state_labor_participation_add:0 "Census: People at Work"
 state_labor_participation_add_desc:0 "The share of working-age women and men who work. Used by the census on the Demographics tab."
 state_work_capacity_mult:0 "Census: Fitness for Work"
 state_work_capacity_mult_desc:0 "How fit people are to work at each age, most of all past 60. Used by the census on the Demographics tab."
```

- [ ] **Step 4b: The values** (`te_demog_values.txt`, after `te_demog_tfr`)

```
# Phase 2 step 1 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §1). State scope.
# Planned and unplanned births (late-game §3.1): te_demog_tfr's parts, from the stored terms, so whatever multiplies
# the factor (wealth, natural, the practices) scales both. No variable: the tooltips read them.
te_demog_tfr_factor = {
	value = 1
	subtract = var:te_dg_desired
	multiply = var:te_dg_means
	multiply = -1
	add = 1
}
te_demog_tfr_unplanned = {
	value = 1
	subtract = var:te_dg_means
	multiply = te_demog_tfr
	divide = { value = te_demog_tfr_factor min = 0.01 }
}
te_demog_tfr_planned = {
	value = te_demog_tfr
	subtract = te_demog_tfr_unplanned
}
te_demog_tfr_planned_share = {
	value = te_demog_tfr_planned
	divide = { value = te_demog_tfr min = 0.00001 }
}
# The lower strata's share of the state's people (the walk), 0 before a walk under this build.
te_demog_low_share = {
	value = 0
	if = {
		limit = { has_variable = te_dg_low_share }
		value = var:te_dg_low_share
	}
}
# Women's participation (#894; demographics_model.women_rate_law and women_rate): the women's-work family's sum
# takes it from the base to the men's rate; the lower strata's women work at least te_demog_k_women_lower.
te_demog_women_rate_law = {
	value = modifier:state_demog_womens_work_ratio_add
	min = 0
	divide = { value = te_demog_k_womens_work_full min = 0.01 }
	max = 1
	multiply = { value = te_demog_k_men_rate subtract = te_demog_k_women_base }
	add = te_demog_k_women_base
}
te_demog_women_rate = {
	value = te_demog_women_rate_law
	min = { value = te_demog_k_women_lower }
	subtract = te_demog_women_rate_law
	multiply = te_demog_low_share
	add = te_demog_women_rate_law
}
# The workforce share on the engine's scale: step 2's target, less the pops' own bases (the design §1.8).
te_demog_wf_target = {
	value = var:te_dg_wa_share
	multiply = var:te_dg_at_work
	multiply = te_demog_k_workforce_scale
}
# The old-age threshold the two linked pension positions follow (late-game §2.2): one figure until phase 3 gives
# the untreated their own.
te_demog_old_age_average = {
	value = var:te_dg_old_age
}
te_demog_old_age_common = {
	value = var:te_dg_old_age
}
```

- [ ] **Step 5: The census** (`te_demog_effects.txt`)

At the end of `te_demog_prepare`:

```
	# phase 2 step 1: participation's inputs for the sweep's new sums (te_demog_work_slot)
	te_demog_work_setup = yes
```

New effects (after `te_demog_close_accumulators`):

```
# THIS = a state, at the end of te_demog_prepare (phase 2 step 1; demographics_model.working_ages_end and women_rate):
# the end of the working ages, whether the after-pension share applies past it and whether those past it are
# pensioners, the 10-14s' share, the sexes' rates and planned births' share.
te_demog_work_setup = {
	set_local_variable = { name = te_dg_child_work value = te_demog_child_work }
	# the sexes' rates and capacity with call 3's participation inputs, each 0 to 1 (demographics_model.sex_rates,
	# capacity_at); te_demog_enter_bio_band multiplies its capacity by te_dg_wk_capm
	set_local_variable = {
		name = te_dg_wk_rm
		value = {
			value = te_demog_k_men_rate
			add = modifier:state_male_labor_participation_add
			add = modifier:state_labor_participation_add
			max = 1
			min = 0
		}
	}
	set_local_variable = {
		name = te_dg_wk_rf
		value = { value = te_demog_women_rate add = modifier:state_labor_participation_add max = 1 min = 0 }
	}
	set_local_variable = { name = te_dg_wk_capm value = { value = 1 add = modifier:state_work_capacity_mult min = 0 } }
	# no pension law: the working ages run to capacity's end, which never comes (D10)
	set_local_variable = { name = te_dg_wa_end value = 999 }
	set_local_variable = { name = te_dg_pens_on value = 0 }
	set_local_variable = { name = te_dg_bill_on value = 0 }
	set_local_variable = { name = te_dg_pkind value = te_demog_pension_kind }
	if = {
		limit = { local_var:te_dg_pkind = 1 }
		set_local_variable = { name = te_dg_wa_end value = te_demog_pension_age }
		set_local_variable = { name = te_dg_pens_on value = 1 }
		set_local_variable = { name = te_dg_bill_on value = 1 }
	}
	else_if = {
		limit = { local_var:te_dg_pkind = 2 }
		set_local_variable = { name = te_dg_wa_end value = var:te_dg_old_age }
		set_local_variable = { name = te_dg_pens_on value = 1 }
	}
	# te_demog_slot_births's two-term form reads these (not while the schedules are one)
	set_local_variable = { name = te_dg_sh_pl value = te_demog_tfr_planned_share }
	set_local_variable = { name = te_dg_sh_un value = { value = 1 subtract = local_var:te_dg_sh_pl } }
}

# THIS = a state, in te_demog_walks before its pop loop (phase 2 step 1): the walk runs under every rule, for
# inheritance; these sums only while the census's cohorts run (D5, D11).
te_demog_work_walk_init = {
	set_local_variable = { name = te_dg_w_on value = 0 }
	if = {
		limit = { te_demog_cohorts_run = yes }
		set_local_variable = { name = te_dg_w_on value = 1 }
	}
	set_local_variable = { name = te_dg_w_low value = 0 }
	set_local_variable = { name = te_dg_w_wbase value = 0 }
	set_local_variable = { name = te_dg_w_wf value = 0 }
}

# Pop scope, the walk's last line per pop: the lower strata, the pop's own working-adult ratio and the engine's
# workforce (triggers.log: workforce, strata), under the cohorts only.
te_demog_work_walk_pop = {
	if = {
		limit = { local_var:te_dg_w_on > 0 }
		change_local_variable = { name = te_dg_w_wf add = workforce }
		change_local_variable = { name = te_dg_w_wbase add = { value = total_size multiply = te_demog_pop_base_ratio } }
		if = {
			limit = { strata = lower }
			change_local_variable = { name = te_dg_w_low add = total_size }
		}
	}
}

# THIS = a state, after the walk's Gini store: the three shares, under the cohorts only.
te_demog_work_walk_store = {
	if = {
		limit = { local_var:te_dg_w_on > 0 }
		set_variable = { name = te_dg_low_share value = { value = local_var:te_dg_w_low divide = { value = local_var:te_dg_w_pop min = 1 } } }
		set_variable = { name = te_dg_wbase value = { value = local_var:te_dg_w_wbase divide = { value = local_var:te_dg_w_pop min = 1 } } }
		set_variable = { name = te_dg_wf_engine value = { value = local_var:te_dg_w_wf divide = { value = local_var:te_dg_w_pop min = 1 } } }
	}
}

# Slot $S$'s people after the step into the working ages, the workers, the pensioners and the health need
# (demographics_model.work_figures). te_dg_start, te_dg_cap and te_dg_needw are the bands' (te_demog_age_boundaries).
te_demog_work_slot = {
	set_local_variable = { name = te_dg_wk_p value = { value = var:te_dg_f$S$ add = var:te_dg_m$S$ } }
	change_local_variable = { name = te_dg_acc_need add = { value = local_var:te_dg_wk_p multiply = local_var:te_dg_needw } }
	set_local_variable = { name = te_dg_wk_sh value = 1 }
	if = {
		limit = { local_var:te_dg_age >= local_var:te_dg_wa_end }
		if = {
			limit = { local_var:te_dg_pens_on > 0 }
			set_local_variable = { name = te_dg_wk_sh value = te_demog_k_after_pension_share }
		}
		if = {
			limit = { local_var:te_dg_bill_on > 0 }
			change_local_variable = { name = te_dg_acc_pens add = local_var:te_dg_wk_p }
		}
	}
	else_if = {
		limit = { local_var:te_dg_start > 0 }
		change_local_variable = { name = te_dg_acc_wa add = local_var:te_dg_wk_p }
	}
	change_local_variable = {
		name = te_dg_acc_wk
		add = {
			value = var:te_dg_f$S$
			multiply = local_var:te_dg_wk_rf
			add = { value = var:te_dg_m$S$ multiply = local_var:te_dg_wk_rm }
			multiply = local_var:te_dg_start
			multiply = local_var:te_dg_cap
			multiply = local_var:te_dg_wk_sh
		}
	}
}

# After the sweep and the step's newborns (local_var:te_dg_wk_born: a step's births, 0 in a seed), with local_var:te_dg_raw
# whole (D4): the pool (150+, past the end of the working ages, at the last biological band) and the newborns (health
# need only) join the sums, then the figures.
te_demog_work_finish = {
	set_local_variable = { name = te_dg_wk_p value = { value = var:te_dg_pf add = var:te_dg_pm } }
	change_local_variable = { name = te_dg_acc_need add = { value = local_var:te_dg_wk_p multiply = local_var:te_dg_needw } }
	set_local_variable = { name = te_dg_wk_sh value = 1 }
	if = {
		limit = { local_var:te_dg_pens_on > 0 }
		set_local_variable = { name = te_dg_wk_sh value = te_demog_k_after_pension_share }
	}
	if = {
		limit = { local_var:te_dg_bill_on > 0 }
		change_local_variable = { name = te_dg_acc_pens add = local_var:te_dg_wk_p }
	}
	change_local_variable = {
		name = te_dg_acc_wk
		add = {
			value = var:te_dg_pf
			multiply = local_var:te_dg_wk_rf
			add = { value = var:te_dg_pm multiply = local_var:te_dg_wk_rm }
			multiply = local_var:te_dg_cap
			multiply = local_var:te_dg_wk_sh
		}
	}
	change_local_variable = { name = te_dg_acc_need add = { value = local_var:te_dg_wk_born multiply = te_demog_k_need_newborn } }
	set_variable = { name = te_dg_wa_share value = { value = local_var:te_dg_acc_wa divide = { value = local_var:te_dg_raw min = 1 } } }
	set_variable = { name = te_dg_at_work value = { value = local_var:te_dg_acc_wk divide = { value = local_var:te_dg_acc_wa min = 1 } } }
	set_variable = { name = te_dg_pensioners value = { value = local_var:te_dg_acc_pens divide = { value = local_var:te_dg_raw min = 1 } } }
	set_variable = {
		name = te_dg_need
		value = {
			value = local_var:te_dg_acc_need
			divide = { value = local_var:te_dg_raw min = 1 }
			divide = { value = te_demog_k_health_need_1836 min = 0.01 }
		}
	}
}
```

`te_demog_reset_accumulators` gains, at its end:

```
	# phase 2 step 1: the working ages, workers, pensioners and need, and the two bands' pointers
	set_local_variable = { name = te_dg_acc_wa value = 0 }
	set_local_variable = { name = te_dg_acc_wk value = 0 }
	set_local_variable = { name = te_dg_acc_pens value = 0 }
	set_local_variable = { name = te_dg_acc_need value = 0 }
	set_local_variable = { name = te_dg_cal value = 0 }
	te_demog_enter_cal_band = yes
	set_local_variable = { name = te_dg_bio value = 0 }
	te_demog_enter_bio_band = yes
```

`te_demog_age_boundaries` gains, at its end:

```
	# phase 2 step 1: the calendar band (the working-age start) and the biological band (capacity, need), whose age
	# te_dg_ab is the calendar one until phase 3 subtracts the band's deficit
	if = {
		limit = { local_var:te_dg_age = local_var:te_dg_next_cal }
		change_local_variable = { name = te_dg_cal add = 1 }
		te_demog_enter_cal_band = yes
	}
	set_local_variable = { name = te_dg_ab value = local_var:te_dg_age }
	if = {
		limit = { local_var:te_dg_ab = local_var:te_dg_next_bio }
		change_local_variable = { name = te_dg_bio add = 1 }
		te_demog_enter_bio_band = yes
	}
```

`te_demog_accumulate_slot` gains, at its end (outside its `age <= 148` limit): `te_demog_work_slot = { S = $S$ }`.

`te_demog_seed`, straight after `te_demog_close_accumulators = yes`:

```
	set_local_variable = { name = te_dg_wk_born value = 0 }
	te_demog_work_finish = yes
```

`te_demog_step_finish`, straight after `change_local_variable = { name = te_dg_raw add = local_var:te_dg_births }`:

```
	set_local_variable = { name = te_dg_wk_born value = local_var:te_dg_births }
	te_demog_work_finish = yes
```

`te_demog_walks` gains exactly three lines, one call each (Task 1's golden pins the rest of its text, D11):
`te_demog_work_walk_init = yes` before `every_scope_pop`, `te_demog_work_walk_pop = yes` as the pop loop's last line,
and `te_demog_work_walk_store = yes` after `te_demog_gini_band_store = yes`.

Add the eight names to the header's inventory comment.

- [ ] **Step 6: Run the registry, the golden and the model**

Run: `$V -m unittest test_demographics_registry test_demographics_golden test_demographics_model 2>&1 | grep -E '^(Ran |OK|FAILED)'`
Expected: OK. The golden now holds `te_dg_wa_share`, `_at_work`, `_pensioners`, `_need` and `_old_age` as new names
and every recorded value unchanged.

- [ ] **Step 7: Format, check the tabs and the divisions**

Run: `python3 scripts/format_paradox_tabs.py common/scripted_effects/te_demog_effects.txt common/script_values/te_demog_values.txt common/scripted_triggers/te_demog_triggers.txt common/on_actions/te_demog_on_actions.txt && $V -m unittest test_demographics_registry.TestDivisions -v`
Expected: OK.

- [ ] **Step 8: Commit**: "Demographics phase 2 step 1: the census counts who works, the pensioners and health need".

- [ ] **Review stop:** a fresh reviewer reads Tasks 4–5 (the denominators, D4; the bands' pointers in the seed and the
  step; the guarded reads of an old save; that nothing new is applied). It names what no test runs, because
  `WORK_DEFAULTS` and `_engine_for` replace them with fixtures and `_Engine` can't read laws or another scope's
  variable: `te_demog_child_work`, `te_demog_pension_kind`, `te_demog_pension_age`'s `owner.var:` read and
  `te_demog_pop_base_ratio`. Task 7's `TE_DEMOG_WORK` line logs each, and Task 8's list checks them in game.

---

### Task 6: Every workforce line moves to two script-only families, with call 3's participation inputs (review stop)

**Files:**
- Create: `common/modifier_type_definitions/demographics_workforce_line_types.txt`
- Create: `common/interest_group_traits/te_demog_workforce_injections.txt` (vanilla's `ig_trait_solidarity`,
  `ig_trait_bourse_du_travail`; the mod already INJECTs IG traits: `sol_expectations_vanilla_injections.txt:8`)
- Create: `common/static_modifiers/te_demog_workforce_injections.txt` (vanilla's `modifier_woman_soldiers`)
- Modify: `common/laws/te_demog_engine_line_injections.txt` (vanilla's laws: Women in the Fields, Women in the
  Workplace and Women's Suffrage inside their existing blocks; new blocks for Women Own Property and Old Age Pension)
- Modify: `common/laws/extra_laws.txt` (in place: Protected Class `:4146`, State-Sponsored Family Planning `:2718`,
  Communal Child-Rearing `:2746`, Pro-Natalist Subsidies `:2704`, Universal Basic Income `:311`, Restorative Justice
  `:1551`, Rehabilitation-Focused `:1570`, State Eugenics `:3087`, the Pro-Labor and Pro-Capital Ministries of Labour
  `:3673`, `:3696`), `era_6.txt:65`, `era_7.txt:502`, `era_7.txt:527`
- Modify: `common/amendments/extra_amendments.txt` (Mandatory Minimums `:270`, Community Service `:317`)
- Modify: `common/static_modifiers/extra_modifiers.txt:345` (the mod's line on Pollution Impact)
- Modify: `scripts/analysis/demographics_params.py` (the workforce lines' section; `DEMOG_TYPES` gains the
  participation types)
- Modify: `scripts/analysis/demographics_modifiers.py` (`engine_rate_lines(keep=)`, `engine_workforce_lines`,
  `workforce_line_carriers`)
- Modify: `scripts/generators/gen_demographics.py` (`_workforce_line_fields`, the shared renderers, `plan_outputs`)
- Create (generated): `te_demog_workforce_line_effects_generated.txt`, `te_demog_workforce_line_values_generated.txt`,
  `te_demog_workforce_line_modifiers_generated.txt`
- Modify: `common/scripted_triggers/te_demog_triggers.txt` (`te_demog_workforce_lines_apply`),
  `common/on_actions/te_demog_on_actions.txt:153`, `events/te_demog_events.txt:74`,
  `common/script_values/gui_chart_script_values.txt` (`gui_state_hidden_modifier_count`)
- Modify: `localization/english/te_modifiers_l_english.yml`, `te_miscellaneous_l_english.yml`
- Test: `test_demographics_registry.py` (`_Engine` loads the two new generated files; new classes
  `TestWorkforceLinesMoved`, `TestWorkforceLinesScript`), `test_demographics_modifiers.py`

**Interfaces:**
- Consumes: Task 2's `P.WOMENS_WORK_TYPE`, `P.REPLACED_TYPE`, `P.PARTICIPATION_TYPES` and its three names; Task 5's
  type definitions.
- Produces: `P.WORKING_ADULT_FIELD`, `P.WORKFORCE_LINE_FIELDS`, `P.WORKFORCE_LINE_SHORT`, `P.WORKFORCE_LINE_TYPES`,
  `P.LIVE_WORKFORCE_LINES`; `DM.engine_workforce_lines(root=ROOT) -> {(kind, key, block, field): (family, value)}`,
  `DM.workforce_line_carriers(root=ROOT) -> [Carrier]`; script `te_demog_workforce_lines_refresh`,
  `te_demog_workforce_lines_clear`, `te_demog_line_working_adults_up`/`_down`, `te_demog_line_working_adults`
  (both families' sum), `te_demog_line_working_adults_applied`; state variable `te_dg_ln_working_adults`.

**Before you start:** the base-law PR must be on `main` (it drops Post-Scarcity's line, spec §3.1). If
`git grep -n "state_working_adult_ratio_add" common/laws/extra_laws.txt` still shows `law_post-scarcity`, stop.

- [ ] **Step 1: The parameters** (`demographics_params.py`, after `ENGINE_FIELDS_ON_TOP`)

```python
# Phase 2 step 1 (the design §1.7; late-game call 11; the owner's call 3, 2026-10-12): every working-adult line on two
# script-only families (demographics_workforce_line_types.txt), each at its old flat value, re-applied by their own pair
# while no workforce term is in force (te_demog_workforce_lines_apply: not Full, or no te_dg_mw, step 2's term). Their
# own files and parameters, so the births and deaths term never takes them off (D3).
WORKING_ADULT_FIELD = "state_working_adult_ratio_add"
WORKFORCE_LINE_FIELDS = (WORKING_ADULT_FIELD,)
WORKFORCE_LINE_SHORT = {WORKING_ADULT_FIELD: "working_adults"}
WORKFORCE_LINE_TYPES = {("womens_work", WORKING_ADULT_FIELD): WOMENS_WORK_TYPE,
                        ("replaced", WORKING_ADULT_FIELD): REPLACED_TYPE}
# The only engine working-adult lines left in common/ (file, top-level block): Rosen's androids (call 12), the pairs and
# the console's probe; the cancels in the injection files are checked against their families' lines by the MOVED tests.
LIVE_WORKFORCE_LINES = frozenset({
    ("extra_companies_flavored.txt", "company_rosen_association"),
    ("unique_pms.txt", "pm_rosen_association_hq"),
})
```

and `DEMOG_TYPES` gains the participation types (their carriers arrive in this task):
`DEMOG_TYPES = DEMOG_MORTALITY_TYPES + DEMOG_FERTILITY_TYPES + (DIFFUSION_TYPE,) + PARTICIPATION_TYPES`.

- [ ] **Step 2: Write the failing tests**

`test_demographics_registry.py`: add `import json` to its imports, and `WORKFORCE_LINE_EFFECTS`, `WORKFORCE_LINE_VALUES`, `WORKFORCE_LINE_MODIFIERS`
paths beside `LINE_EFFECTS`, and add the first two to `_Engine.__init__`'s lists. Then:

```python
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
        ("law", "law_state_eugenics_program", "modifier"): ("replaced", 0.05),
    }
    # call 3's participation inputs on laws (the design §1.7's inventory; starting sizes, call 11)
    PARTICIPATION = {
        ("law", "law_restorative_justice", "modifier", P.MALE_PARTICIPATION_TYPE): 0.02,
        ("law", "law_rehabilitation_focused_criminal_justice", "modifier", P.MALE_PARTICIPATION_TYPE): 0.03,
        ("law", "law_pro_labor_ministry_of_labor", "institution_modifier", P.PARTICIPATION_TYPE): 0.005,
        ("law", "law_pro_capital_ministry_of_labor", "institution_modifier", P.PARTICIPATION_TYPE): 0.01,
        ("law", "law_state_eugenics_program", "modifier", P.CAPACITY_TYPE): 0.1,
    }
    # the carriers no reader walks: (file, block) -> the lines its block must hold
    BLOCKS = {
        ("common/amendments/extra_amendments.txt", "amendment_community_service"):
            (f"{P.REPLACED_TYPE} = 0.01", f"{P.MALE_PARTICIPATION_TYPE} = 0.01"),
        ("common/amendments/extra_amendments.txt", "amendment_mandatory_minimums"):
            (f"{P.REPLACED_TYPE} = -0.01", f"{P.MALE_PARTICIPATION_TYPE} = -0.01"),
        ("common/interest_group_traits/te_demog_workforce_injections.txt", "INJECT:ig_trait_solidarity"):
            ("state_working_adult_ratio_add = -0.05", f"{P.REPLACED_TYPE} = 0.05", f"{P.PARTICIPATION_TYPE} = 0.02"),
        ("common/interest_group_traits/te_demog_workforce_injections.txt", "INJECT:ig_trait_bourse_du_travail"):
            ("state_working_adult_ratio_add = -0.05", f"{P.REPLACED_TYPE} = 0.05", f"{P.PARTICIPATION_TYPE} = 0.02"),
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
        for path in sorted((ROOT / "common").rglob("*.txt")):
            if path.name in skip:
                continue
            text = re.sub(r"#[^\n]*", "", _text(path))
            if not re.search(r"\bstate_working_adult_ratio_add\s*=\s*-?\d", text):
                continue
            for m in re.finditer(r"^([\w.:-]+) = \{", text, re.M):
                if re.search(r"\bstate_working_adult_ratio_add\s*=\s*-?\d", _block(text, m.group(1))):
                    live.add((path.name, m.group(1)))
        self.assertEqual(live, set(P.LIVE_WORKFORCE_LINES))

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
```

`test_demographics_modifiers.py`: in `test_each_type_sits_where_its_design_puts_it`, `allowed` gains
`P.MALE_PARTICIPATION_TYPE: {"law"}, P.PARTICIPATION_TYPE: {"law_institution"}, P.CAPACITY_TYPE: {"law"}`
(`test_every_type_has_a_carrier` then holds: each has a law carrier). And:

```python
class TestWorkforceReaders(unittest.TestCase):
    def test_the_readers_keep_only_the_working_adult_field(self):
        lines = DM.engine_workforce_lines()
        self.assertTrue(lines)
        for (kind, key, block, field), (family, value) in lines.items():
            self.assertEqual(field, P.WORKING_ADULT_FIELD)
            self.assertIn(family, ("womens_work", "replaced"))

    def test_carriers_keep_the_engines_scaling(self):
        by_key = {c.key: c for c in DM.workforce_line_carriers()}
        self.assertEqual(by_key["law_old_age_pension"].kind, "law_institution")
        self.assertEqual(by_key["law_pro_capital_ministry_of_labor"].kind, "law_institution")
        self.assertEqual(by_key["law_womens_suffrage"].kind, "law")
        self.assertEqual(by_key["contraceptive_pill"].kind, "technology")
```

- [ ] **Step 3: Run them to see them fail**

Run: `$V -m unittest test_demographics_registry.TestWorkforceLinesMoved test_demographics_registry.TestWorkforceLinesScript test_demographics_modifiers.TestWorkforceReaders -v 2>&1 | grep -E '^(Ran |OK|FAILED)|Error'`
Expected: FAIL.

- [ ] **Step 4: The readers** (`demographics_modifiers.py`)

`engine_rate_lines(root=ROOT, mod=True, keep=None)`: in `add`, the test `if field.endswith("_mult"):` becomes
`if (keep or (lambda f: f.endswith("_mult")))(field):`; the docstring says `keep` picks the fields (default: every
`*_mult`). Then:

```python
def engine_workforce_lines(root=ROOT):
    """{(kind, key, block, field): (family, value)}: the working-adult lines moved to the women's-work and replaced
    types (phase 2 step 1), read back from the laws and technologies as engine_lines() reads the births and deaths
    ones. The amendments, IG traits and static modifiers are no reader's: TestWorkforceLinesMoved reads their blocks."""
    names = set(P.WORKFORCE_LINE_TYPES.values())
    back = {name: fam_field for fam_field, name in P.WORKFORCE_LINE_TYPES.items()}
    out = {}
    for (kind, key, block, field), value in engine_rate_lines(root, keep=lambda f: f in names).items():
        if abs(value) > 1e-9:
            family, engine_field = back[field]
            out[(kind, key, block, engine_field)] = (family, value)
    return out


def workforce_line_carriers(root=ROOT):
    """engine_workforce_lines() as Carriers typed by their family's type, with the engine's scaling kinds (as
    line_carriers)."""
    institution = {key: _u(_u(entry).get("institution")) for key, entry in _state(root).get_data("Laws").items()}
    out = []
    for (kind, key, block, field), (family, value) in sorted(engine_workforce_lines(root).items()):
        name = P.WORKFORCE_LINE_TYPES[(family, field)]
        if kind == "law" and block == "institution_modifier":
            out.append(Carrier("law_institution", key, name, value, institution.get(key)))
        elif kind == "institution":
            out.append(Carrier("institution", key, name, value, key))
        else:
            out.append(Carrier(kind, key, name, value))
    return out
```

(`load_carriers`, which reads `P.DEMOG_TYPES` from laws, technologies and institutions, now also finds the
participation inputs on the laws; the model's scenarios take them through `DM.totals`.)

- [ ] **Step 5: The types and the carriers**

`demographics_workforce_line_types.txt` (UTF-8 with BOM, tabs):

```
# demographics_workforce_line_types.txt
#
# Phase 2 step 1 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §1.7; late-game call
# 11; the owner's call 3): every engine working-adult line, as script-only types the engine sums but doesn't apply.
# The mod re-applies both at their old flat values while no workforce term is in force
# (te_demog_workforce_lines_refresh). From step 2, under Full, the participation model reads the women's-work family,
# and census terms replace the other (the pension age; call 3's participation inputs). Each copies
# state_working_adult_ratio_add's format (mod_entity_modifier_types.txt) with ai_value 0, so AI choices don't move. A
# release keeps these.
state_demog_womens_work_ratio_add = {
	decimals = 1
	color = good
	percent = yes
	game_data = {
		ai_value = 0
	}
	script_only = yes
}
state_demog_replaced_ratio_add = {
	decimals = 1
	color = good
	percent = yes
	game_data = {
		ai_value = 0
	}
	script_only = yes
}
```

`te_demog_engine_line_injections.txt` (vanilla's laws): inside the existing `INJECT:law_women_in_the_fields`,
`_in_the_workplace` and `INJECT:law_womens_suffrage` modifier blocks add the cancel and the type (Fields −0.3 / +0.3,
Workplace −0.1 / +0.1, Suffrage −0.15 / +0.15), for example:

```
INJECT:law_women_in_the_fields = {
	modifier = {
		state_birth_rate_mult = 0.1
		state_demog_absorbed_birth_rate_mult = -0.1
		state_working_adult_ratio_add = -0.3
		state_demog_womens_work_ratio_add = 0.3
	}
}
```

and new blocks:

```
INJECT:law_women_own_property = {
	modifier = {
		state_working_adult_ratio_add = -0.05
		state_demog_womens_work_ratio_add = 0.05
	}
}
INJECT:law_old_age_pension = {
	institution_modifier = {
		state_working_adult_ratio_add = 0.01
		state_demog_replaced_ratio_add = -0.01
	}
}
```

The file's header comment gains "and, since phase 2 step 1, the working-adult lines' women's-work and replaced
families".

`common/interest_group_traits/te_demog_workforce_injections.txt` (UTF-8 with BOM, tabs):

```
# Phase 2 step 1 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §1.7, the owner's call 3):
# the Trade Unions' two loyal traits' working-adult line, cancelled and carried on the replaced family at its old value
# (te_demog_workforce_lines_refresh re-applies it while no workforce term is in force), with its participation input
# for the census beside it. That the engine sums a script-only type from an IG trait into a state's read is step 1's
# in-game check.
INJECT:ig_trait_solidarity = {
	modifier = {
		state_working_adult_ratio_add = -0.05
		state_demog_replaced_ratio_add = 0.05
		state_labor_participation_add = 0.02	# unions' mutual aid keeps the sick and jobless attached to work
	}
}
INJECT:ig_trait_bourse_du_travail = {
	modifier = {
		state_working_adult_ratio_add = -0.05
		state_demog_replaced_ratio_add = 0.05
		state_labor_participation_add = 0.02	# labour exchanges place workers
	}
}
```

`common/static_modifiers/te_demog_workforce_injections.txt` (UTF-8 with BOM, tabs):

```
# Phase 2 step 1 (the design §1.7, the owner's call 3): the Paris Commune's Woman Soldiers (vanilla; applied to the
# country at x0.5): its working-adult line moves to the women's-work family at its old value. Women at arms go on to
# work (the owner's example). That the engine scales the type with the modifier's multiplier is step 1's in-game check.
INJECT:modifier_woman_soldiers = {
	state_working_adult_ratio_add = -0.05
	state_demog_womens_work_ratio_add = 0.05
}
```

`extra_modifiers.txt`, the mod's own line on Pollution Impact (vanilla's `state_region_pollution_health` has none, so
nothing is cancelled): `state_working_adult_ratio_add = -0.05` becomes

```
	state_demog_replaced_ratio_add = -0.05	# phase 2 step 1: re-applied by te_demog_workforce_lines_refresh
	state_work_capacity_mult = -0.1	# the census's participation input (the design §1.7): ill health keeps people from work
```

The mod's own laws, technologies and amendments change in place:
- the women's-work family (the field's name only): Protected Class, State-Sponsored Family Planning, Communal
  Child-Rearing; `personal_appliances`, `contraceptive_pill`, `second_wave_feminism`;
- the replaced family (the field's name only): Pro-Natalist Subsidies, Universal Basic Income;
- the replaced family plus the participation input (§1.7's inventory, starting sizes):

  | Carrier | Replaced line | Participation input |
  |---|---|---|
  | `law_restorative_justice` | `state_demog_replaced_ratio_add = 0.025` | `state_male_labor_participation_add = 0.02` |
  | `law_rehabilitation_focused_criminal_justice` | `= 0.05` | `state_male_labor_participation_add = 0.03` |
  | `law_pro_labor_ministry_of_labor` (institution_modifier) | `= 0.01` | `state_labor_participation_add = 0.005` |
  | `law_pro_capital_ministry_of_labor` (institution_modifier) | `= 0.02` | `state_labor_participation_add = 0.01` |
  | `law_state_eugenics_program` | `= 0.05` | `state_work_capacity_mult = 0.1` |
  | `amendment_community_service` | `= 0.01` | `state_male_labor_participation_add = 0.01` |
  | `amendment_mandatory_minimums` | `= -0.01` | `state_male_labor_participation_add = -0.01` |

  each replaced line with the trailing comment `# phase 2 step 1: re-applied by te_demog_workforce_lines_refresh`.

Rosen's two lines (`company_rosen_association`'s prosperity modifier, `pm_rosen_association_hq`) stay engine fields
(spec §13 call 12): `P.LIVE_WORKFORCE_LINES` lists them.

- [ ] **Step 6: The generator** (`gen_demographics.py`)

```python
WORKFORCE_LINE_MODIFIERS = Path("common/static_modifiers/te_demog_workforce_line_modifiers_generated.txt")
WORKFORCE_LINE_VALUES = Path("common/script_values/te_demog_workforce_line_values_generated.txt")
WORKFORCE_LINE_EFFECTS = Path("common/scripted_effects/te_demog_workforce_line_effects_generated.txt")
WORKFORCE_LINE_HEADER = (
    "# Phase 2 step 1 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §1.7): the\n"
    "# working-adult lines' women's-work and replaced families, re-applied by a fixed-sign pair while\n"
    "# te_demog_workforce_lines_apply holds (not Full, or no te_dg_mw: step 2's term). Their own files, gate and\n"
    "# refresh, so the census's births and deaths term never takes them off. A release keeps them.")


def _workforce_line_fields():
    return [(f, P.WORKFORCE_LINE_SHORT[f], [P.WORKFORCE_LINE_TYPES[(fam, f)] for fam in ("womens_work", "replaced")
                                             if (fam, f) in P.WORKFORCE_LINE_TYPES])
            for f in P.WORKFORCE_LINE_FIELDS]
```

The three renderers become one parameterised function each, which #892's files and the new ones both call. #892's
output must stay byte for byte (`test_gen_demographics.TestGenerated.test_committed_outputs_are_current` and the review
stop's `git diff` check it):

```python
def _render_line_modifiers(fields, header):
    o = Out()
    o(HEADER.rstrip("\n"))
    o(header)
    for field, short, _types in fields:
        for sign, unit in (("up", "1"), ("down", "-1")):
            o(f"te_demog_line_{short}_{sign} = {{")
            o("icon = gfx/interface/icons/timed_modifier_icons/modifier_system.dds")
            o(f"{field} = {unit}")
            o("}")
    return o.text()


def _render_line_values(fields, header):
    o = Out()
    o(HEADER.rstrip("\n"))
    o(header)
    o("# State scope. te_demog_line_<short>: the families' sum the engine reads; _applied: the pair in force, signed")
    o("# (0 with neither held), which te_demog_rates_refresh takes off the state read; _up_mult / _down_mult: the")
    o("# multipliers, from the stored sum (te_dg_ln_<short>), ROOT being the state.")
    for field, short, types in fields:
        o(f"te_demog_line_{short} = {{")
        o(f"value = modifier:{types[0]}")
        for t in types[1:]:
            o(f"add = modifier:{t}")
        o("}")
        o(f"te_demog_line_{short}_applied = {{")
        o("value = 0")
        o("if = {")
        o("limit = {")
        o("OR = {")
        o(f"has_modifier = te_demog_line_{short}_up")
        o(f"has_modifier = te_demog_line_{short}_down")
        o("}")
        o("}")
        o(f"value = var:te_dg_ln_{short}")
        o("}")
        o("}")
        o(f"te_demog_line_{short}_up_mult = {{")
        o(f"value = var:te_dg_ln_{short}")
        o("}")
        o(f"te_demog_line_{short}_down_mult = {{")
        o(f"value = var:te_dg_ln_{short}")
        o("multiply = -1")
        o("}")
    return o.text()


def _line_pair_block(o, short):
    """One field's pair at the families' sum, touched only when the sum changed (or a pair was lost)."""
    o(f"set_local_variable = {{ name = te_dg_ln_new value = te_demog_line_{short} }}")
    o("if = {")
    o("limit = {")
    o("OR = {")
    o(f"NOT = {{ has_variable = te_dg_ln_{short} }}")
    o(f"NOT = {{ var:te_dg_ln_{short} = local_var:te_dg_ln_new }}")
    o("# a pair lost while its sum stayed (a save quirk, a state that copied the variable): put it back")
    o("AND = {")
    o(f"NOT = {{ var:te_dg_ln_{short} = 0 }}")
    o(f"NOT = {{ has_modifier = te_demog_line_{short}_up }}")
    o(f"NOT = {{ has_modifier = te_demog_line_{short}_down }}")
    o("}")
    o("}")
    o("}")
    o(f"te_demog_line_{short}_remove = yes")
    o(f"set_variable = {{ name = te_dg_ln_{short} value = local_var:te_dg_ln_new }}")
    o("if = {")
    o(f"limit = {{ var:te_dg_ln_{short} > 0 }}")
    o(f"add_modifier = {{ name = te_demog_line_{short}_up multiplier = te_demog_line_{short}_up_mult }}")
    o("}")
    o("else_if = {")
    o(f"limit = {{ var:te_dg_ln_{short} < 0 }}")
    o(f"add_modifier = {{ name = te_demog_line_{short}_down multiplier = te_demog_line_{short}_down_mult }}")
    o("}")
    o("}")


def _render_line_effects(fields, header, intro, refresh, gate, clear, clear_note, stale_m):
    o = Out()
    o(HEADER.rstrip("\n"))
    o(header)
    for line in intro:
        o(line)
    o(f"{refresh} = {{")
    if stale_m:
        o("if = {")
        o("limit = {")
        o("has_variable = te_dg_mb")
        o("OR = {")
        o("NOT = { te_demog_effects_run = yes }")
        o("NOT = { has_variable = te_dg_q_b }")
        o("}")
        o("}")
        o("te_demog_rates_clear = yes")
        o("}")
    o("if = {")
    o(f"limit = {{ {gate} = yes }}")
    for field, short, _types in fields:
        _line_pair_block(o, short)
    o("}")
    o("else = {")
    o(f"{clear} = yes")
    o("}")
    o("}")
    o("")
    o(clear_note)
    o(f"{clear} = {{")
    for field, short, _types in fields:
        o(f"te_demog_line_{short}_remove = yes")
        o("if = {")
        o(f"limit = {{ has_variable = te_dg_ln_{short} }}")
        o(f"remove_variable = te_dg_ln_{short}")
        o("}")
    o("}")
    o("")
    for field, short, _types in fields:
        o(f"te_demog_line_{short}_remove = {{")
        for sign in ("up", "down"):
            o("if = {")
            o(f"limit = {{ has_modifier = te_demog_line_{short}_{sign} }}")
            o(f"remove_modifier = te_demog_line_{short}_{sign}")
            o("}")
        o("}")
    return o.text()


def render_line_modifiers():
    return _render_line_modifiers(_line_fields(), LINE_HEADER)


def render_line_values():
    return _render_line_values(_line_fields(), LINE_HEADER)


def render_line_effects():
    return _render_line_effects(
        _line_fields(), LINE_HEADER,
        ["# THIS = ROOT = a state (its monthly pulse, owner change, incorporation and creation; te_demog_events.4 for a new",
         "# game, a law's activation and a technology): each field's pair at the families' sum while te_demog_lines_apply",
         "# holds, touched only when the sum changed; otherwise (the census sets the state's births and deaths) every pair off.",
         "# First, a census term that is no longer the census's comes off now, not at the state's next yearly step, so it and",
         "# the pairs are never both in force: one a rule switched off Full left, or one from a save made before the moved",
         "# lines (no te_dg_q_b, which this build's step always sets with it)."],
        "te_demog_lines_refresh", "te_demog_lines_apply", "te_demog_lines_clear",
        "# THIS = a state: every pair off, with its stored sum (the census's refresh calls it when it first sets M).",
        stale_m=True)


def render_workforce_line_modifiers():
    return _render_line_modifiers(_workforce_line_fields(), WORKFORCE_LINE_HEADER)


def render_workforce_line_values():
    return _render_line_values(_workforce_line_fields(), WORKFORCE_LINE_HEADER)


def render_workforce_line_effects():
    return _render_line_effects(
        _workforce_line_fields(), WORKFORCE_LINE_HEADER,
        ["# THIS = ROOT = a state, beside te_demog_lines_refresh at both its call sites: the working-adult pair at the",
         "# families' sum while te_demog_workforce_lines_apply holds; otherwise (step 2's workforce term in force) off."],
        "te_demog_workforce_lines_refresh", "te_demog_workforce_lines_apply", "te_demog_workforce_lines_clear",
        "# THIS = a state: the working-adult pair off, with its stored sum (step 2's term calls it when it first lands).",
        stale_m=False)
```

Before replacing `render_line_effects`, diff the comments above against the function on the merged tree and copy any
line that changed since fc38b65b. Run `$V -m unittest test_gen_demographics.TestGenerated` straight after the refactor
and before adding the workforce files: it must pass with #892's files untouched.

`plan_outputs`' dict gains `WORKFORCE_LINE_MODIFIERS: render_workforce_line_modifiers()`,
`WORKFORCE_LINE_VALUES: render_workforce_line_values()` and `WORKFORCE_LINE_EFFECTS: render_workforce_line_effects()`.
Regenerate: `$V scripts/generators/gen_demographics.py`.

- [ ] **Step 7: The gate, the hooks, the panel and the loc**

`te_demog_triggers.txt`:

```
# THIS = a state: the working-adult lines' pair applies (phase 2 step 1) unless the census sets this state's
# workforce: Full, and step 2's term in force (te_dg_mw). In step 1 nothing sets te_dg_mw, so it always applies.
te_demog_workforce_lines_apply = {
	OR = {
		NOT = { te_demog_effects_run = yes }
		NOT = { has_variable = te_dg_mw }
	}
}
```

`te_demog_on_actions.txt`, after `on_acquired_technology`'s block (additive `on_actions` lists, as
`amendment_on_actions.txt` and three files' `on_law_activated` already are):

```
# ROOT = the country (vanilla's comments on both hooks): an amendment repealed or timed out (the timeout's is already off
# its law) changes its law's working-adult lines, so the country's states refresh that day, as for a technology. An
# amendment attached has no hook; the monthly refresh takes it within a month (the design §1.9).
on_amendment_repealed = {
	on_actions = {
		te_demog_lines_country_on_action
	}
}
on_amendment_timeout = {
	on_actions = {
		te_demog_lines_country_on_action
	}
}
```

`te_demog_on_actions.txt:153` and `events/te_demog_events.txt:74`: `te_demog_workforce_lines_refresh = yes` on the line
after `te_demog_lines_refresh = yes`.

`gui_chart_script_values.txt`, `gui_state_hidden_modifier_count`, after the `te_demog_line_wealth_deaths_up` block:

```
	if = {
		limit = { has_modifier = te_demog_line_working_adults_down }
		add = 1
	}
	if = {
		limit = { has_modifier = te_demog_line_working_adults_up }
		add = 1
	}
```

(`states_panel.gui` hides the pairs by their localized name, "Laws and Institutions", which this pair shares, so it
needs no edit.)

Loc: `te_miscellaneous_l_english.yml` (beside `te_demog_line_births_up`):

```
 te_demog_line_working_adults_up:0 "Laws and Institutions"
 te_demog_line_working_adults_up_desc:0 "The workforce effects of this state's laws, technologies and institutions."
 te_demog_line_working_adults_down:0 "Laws and Institutions"
 te_demog_line_working_adults_down_desc:0 "The workforce effects of this state's laws, technologies and institutions."
```

`te_modifiers_l_english.yml` (beside `state_demog_absorbed_birth_rate_mult`):

```
 state_demog_womens_work_ratio_add:0 "$state_working_adult_ratio_add$"
 state_demog_womens_work_ratio_add_desc:0 "$state_working_adult_ratio_add_desc$. Where the demographic census sets a state's workforce, it reads this effect as women's work instead."
 state_demog_replaced_ratio_add:0 "$state_working_adult_ratio_add$"
 state_demog_replaced_ratio_add_desc:0 "$state_working_adult_ratio_add_desc$. Where the demographic census sets a state's workforce, it carries this effect its own way instead: through its ages (who is old, when they retire, how many children there are) or through who works."
```

Run `python3 organize_loc.py` and keep what it moves.

- [ ] **Step 8: Run everything the change touches**

Run: `$V -m unittest test_demographics_registry test_demographics_modifiers test_gen_demographics test_demographics_golden test_release_census_inputs test_demographics_harness 2>&1 | grep -E '^(Ran |OK|FAILED)'`
Expected: OK. The golden's line cases now hold `te_dg_ln_working_adults` and the working-adult pair (allowed) and every
recorded value unchanged.

- [ ] **Step 9: The audits** (`ci.yml`'s list; the ones this touches)

Run: `$V duplicate_key_audit.py --strict && $V loc_coverage_audit.py --strict && $V script_argument_audit.py --strict && python3 organize_loc.py --check && python3 scripts/analysis/check_localization_files.py`
Expected: exit 0 each.

- [ ] **Step 10: Commit**: "Demographics phase 2 step 1: every workforce line on its own family, with call 3's participation inputs".

- [ ] **Review stop:** a fresh reviewer reads Task 6 against D2, D3, D7, D12, spec §1.7's inventory (every carrier's
  family, flat value and participation input) and #892's plan
  (`docs/superpowers/archive/plans/2026-10-11-demographics-engine-lines-script-only.md`), and checks that #892's three
  generated files are byte-identical to `main`'s (`git diff main -- common/*/te_demog_line_*_generated.txt` empty).

---

### Task 7: The harness and the console show the figures, and option p sets up call 3's carriers

**Files:**
- Modify: `scripts/analysis/demographics_harness.py` (subcommand `workforce`; `WORKFORCE_SCENARIOS`)
- Modify: `common/scripted_effects/te_debug_demog_effects.txt` (`te_debug_demog_mods_line` gains a second line;
  new `te_debug_demog_call3_setup`), `common/script_values/te_debug_demog_values.txt` (guarded reads),
  `common/static_modifiers/te_debug_demog_modifiers.txt` (`te_demog_debug_ig_loyal`),
  `events/te_debug_demog_events.txt` (option p; the hidden `te_debug_demog.3`: #906 takes `.2` and option o)
- Modify: `localization/english/te_events_l_english.yml` (option p), `te_miscellaneous_l_english.yml` (the modifier)
- Test: `test_demographics_harness.py` (new test), `test_demographics_registry.py` (options l and p)

**Interfaces:**
- Consumes: Task 2's model, Task 6's `DM.workforce_line_carriers` and moved carriers.
- Produces: `H.WORKFORCE_SCENARIOS: list[tuple[str, dict, float]]`, `H.workforce_rows() -> list[dict]`;
  `TE_DEMOG_WORK` console line; option p and `te_debug_demog.3`.

- [ ] **Step 1: Write the failing tests**

`test_demographics_harness.py`:

```python
class TestWorkforceCommand(unittest.TestCase):
    def test_rows_cover_the_scenarios_and_the_1836_target(self):
        rows = H.workforce_rows()
        self.assertEqual([r["name"] for r in rows], [s[0] for s in H.WORKFORCE_SCENARIOS])
        farm = rows[0]
        self.assertAlmostEqual(farm["target"], 0.25, delta=0.02)
        for r in rows:
            self.assertAlmostEqual(r["target"], P.WORKFORCE_SCALE * r["wa_share"] * r["at_work"], places=9)

    def test_call_3s_laws_add_their_participation_inputs(self):
        """A Pro-Capital Ministry at level 5 and Rehabilitation add about +0.027 on the engine's scale to the rich row
        (the design §1.7's inventory, on its stable structure), against +0.15 as flat lines."""
        rows = {r["name"]: r for r in H.workforce_rows()}
        gain = rows["Rich, plus call 3's laws"]["target"] - rows["Rich, Protected Class, pension at 65"]["target"]
        self.assertGreater(gain, 0.015)
        self.assertLess(gain, 0.04)
```

`test_demographics_registry.py` (beside `test_option_l_logs_the_fertility_types`):

```python
    def test_option_l_logs_the_work_figures(self):
        line = _block(_text(ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"),
                      "te_debug_demog_mods_line")
        self.assertIn("TE_DEMOG_WORK", line)
        for name in ("wa_share", "at_work", "pensioners", "need", "old_age", "low_share", "wbase", "wf_engine"):
            self.assertIn(f"te_debug_demog_work_{name}", line, name)
        self.assertIn("te_debug_demog_work_wf_target", line)
        for read in ("te_debug_demog_pension_var", "te_demog_pension_kind", "te_demog_child_work",
                     "te_debug_demog_womens_mod", "te_debug_demog_replaced_mod", "te_debug_demog_part_m_mod",
                     "te_debug_demog_part_mod", "te_debug_demog_cap_mod", "te_demog_line_working_adults_applied"):
            self.assertIn(read, line)
```

- [ ] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_harness.TestWorkforceCommand -v`
Expected: FAIL (`AttributeError: ... 'workforce_rows'`).

- [ ] **Step 3: The harness**

```python
# Phase 2 step 1: the participation figures at the starting values, on the census's own stable structures
# (the design §1.8's sketch). (name, Inputs keywords, the lower strata's share)
_RICH_TECHS = frozenset({"medical_degrees", "modern_nursing", "antibiotics", "modern_vaccines",
                         "antibiotic_mass_production", "contraceptive_pill", "modern_pharmaceuticals",
                         "vulcanization", "feminism", "second_wave_feminism", "personal_appliances"})
WORKFORCE_SCENARIOS = [
    ("1836 farming", dict(sol=8, literacy=0.1, urban_share=0.05,
                          laws=frozenset({"law_no_womens_rights", "law_child_labor_allowed"})), 0.85),
    ("1836 Women in the Fields", dict(sol=8, literacy=0.1, urban_share=0.05,
                                      laws=frozenset({"law_women_in_the_fields", "law_child_labor_allowed"})), 0.85),
    ("Rich, Protected Class, pension at 65", dict(
        sol=40, literacy=0.98, urban_share=0.8, techs=_RICH_TECHS,
        laws=frozenset({"law_protected_class", "law_compulsory_primary_school", "law_old_age_pension",
                        "law_public_health_insurance"}),
        institutions={"institution_health_system": 5, "institution_social_security": 5}), 0.4),
    ("Rich, plus call 3's laws", dict(
        sol=40, literacy=0.98, urban_share=0.8, techs=_RICH_TECHS,
        laws=frozenset({"law_protected_class", "law_compulsory_primary_school", "law_old_age_pension",
                        "law_public_health_insurance", "law_pro_capital_ministry_of_labor",
                        "law_rehabilitation_focused_criminal_justice"}),
        institutions={"institution_health_system": 5, "institution_social_security": 5,
                      "institution_ministry_of_labor": 5}), 0.4),
]


def workforce_rows():
    carriers, lines = DM.load_carriers(), DM.workforce_line_carriers()
    rows = []
    for name, kw, low in WORKFORCE_SCENARIOS:
        inp = M.Inputs(low_share=low, **kw)
        inp.mods = {**DM.totals(carriers, inp.techs, inp.laws, inp.institutions),
                    **DM.totals(lines, inp.techs, inp.laws, inp.institutions,
                                types=tuple(P.WORKFORCE_LINE_TYPES.values()))}
        ring, last = M.run_constant(inp, years=300)
        qf, qm, _ = M.group_rates(inp)
        old = M.old_age(qf, qm)
        fig = M.work_figures(ring, inp, old)
        rows.append({"name": name, "tfr": last["tfr"], "women": M.women_rate(inp), **fig,
                     "target": M.wf_target(fig), "old_age": old})
    return rows


def cmd_workforce(args):
    print(f"{'scenario':40s} {'tfr':>5s} {'women':>6s} {'wa':>6s} {'at work':>8s} {'target':>7s} "
          f"{'pens':>6s} {'need':>6s} {'old age':>8s}")
    for r in workforce_rows():
        print(f"{r['name']:40s} {r['tfr']:5.2f} {r['women']:6.2f} {r['wa_share']:6.3f} {r['at_work']:8.3f} "
              f"{r['target']:7.3f} {r['pensioners']:6.3f} {r['need']:6.3f} {r['old_age']:8.1f}")
    return 0
```

Register `workforce` in the argument parser beside the other subcommands, with help "phase 2 step 1: the
participation figures at the starting values (the design §1.8)".

- [ ] **Step 4: The console line**

`te_debug_demog_values.txt`, one guarded read per figure (−1 without it):

```
te_debug_demog_work_wa_share = { value = -1 if = { limit = { has_variable = te_dg_wa_share } value = var:te_dg_wa_share } }
te_debug_demog_work_at_work = { value = -1 if = { limit = { has_variable = te_dg_at_work } value = var:te_dg_at_work } }
te_debug_demog_work_pensioners = { value = -1 if = { limit = { has_variable = te_dg_pensioners } value = var:te_dg_pensioners } }
te_debug_demog_work_need = { value = -1 if = { limit = { has_variable = te_dg_need } value = var:te_dg_need } }
te_debug_demog_work_old_age = { value = -1 if = { limit = { has_variable = te_dg_old_age } value = var:te_dg_old_age } }
te_debug_demog_work_low_share = { value = -1 if = { limit = { has_variable = te_dg_low_share } value = var:te_dg_low_share } }
te_debug_demog_work_wbase = { value = -1 if = { limit = { has_variable = te_dg_wbase } value = var:te_dg_wbase } }
te_debug_demog_work_wf_engine = { value = -1 if = { limit = { has_variable = te_dg_wf_engine } value = var:te_dg_wf_engine } }
te_debug_demog_work_wf_target = { value = -1 if = { limit = { has_variable = te_dg_at_work } value = te_demog_wf_target } }
# the owner's own variable, -1 where it holds none: tells a working owner.var read from the Standard fallback
te_debug_demog_pension_var = { value = -1 if = { limit = { owner ?= { has_variable = te_dg_pension_age } } value = owner.var:te_dg_pension_age } }
# the two families and call 3's three inputs as the state reads them: Task 8's scope checks compare these with the field
te_debug_demog_womens_mod = { value = modifier:state_demog_womens_work_ratio_add }
te_debug_demog_replaced_mod = { value = modifier:state_demog_replaced_ratio_add }
te_debug_demog_part_m_mod = { value = modifier:state_male_labor_participation_add }
te_debug_demog_part_mod = { value = modifier:state_labor_participation_add }
te_debug_demog_cap_mod = { value = modifier:state_work_capacity_mult }
```

`te_debug_demog_mods_line` gains a second `debug_log`:

```
	debug_log = "TE_DEMOG_WORK wa_share=[THIS.ScriptValue('te_debug_demog_work_wa_share')|3] at_work=[THIS.ScriptValue('te_debug_demog_work_at_work')|3] wf_target=[THIS.ScriptValue('te_debug_demog_work_wf_target')|3] wf_engine=[THIS.ScriptValue('te_debug_demog_work_wf_engine')|3] wbase=[THIS.ScriptValue('te_debug_demog_work_wbase')|3] low_share=[THIS.ScriptValue('te_debug_demog_work_low_share')|3] pensioners=[THIS.ScriptValue('te_debug_demog_work_pensioners')|3] need=[THIS.ScriptValue('te_debug_demog_work_need')|3] old_age=[THIS.ScriptValue('te_debug_demog_work_old_age')|1] pension_age=[THIS.ScriptValue('te_demog_pension_age')|0] pension_var=[THIS.ScriptValue('te_debug_demog_pension_var')|0] pension_kind=[THIS.ScriptValue('te_demog_pension_kind')|0] child_work=[THIS.ScriptValue('te_demog_child_work')|2] ww_mod=[THIS.ScriptValue('te_demog_line_working_adults')|3] pair=[THIS.ScriptValue('te_demog_line_working_adults_applied')|3] wa_mod=[THIS.ScriptValue('te_debug_demog_working_ratio_mod')|3] womens=[THIS.ScriptValue('te_debug_demog_womens_mod')|3] replaced=[THIS.ScriptValue('te_debug_demog_replaced_mod')|3] part_m=[THIS.ScriptValue('te_debug_demog_part_m_mod')|3] part=[THIS.ScriptValue('te_debug_demog_part_mod')|3] cap=[THIS.ScriptValue('te_debug_demog_cap_mod')|3] date=[TimeKeeper.GetCurrentDate.GetString]"
```


- [ ] **Step 4b: Option p, call 3's carriers in one go** (D12; the second review of #923)

The kinds nothing has verified are the amendments and the IG traits, and the console has no effect command, so option
p sets each up in the player's country and logs the capital before, a day after and a month after. Test first
(`test_demographics_registry.py`, beside the option l tests):

```python
    def test_option_p_sets_up_call_3s_carriers(self):
        console = _text(ROOT / "events" / "te_debug_demog_events.txt")
        self.assertIn("te_debug_demog_call3_setup = yes", console)
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
```

`events/te_debug_demog_events.txt`, before option z:

```
	# ---- p: call 3's carriers (phase 2 step 1; spec §1.7, plan D12) --------------------------------
	option = {
		name = te_debug_demog.1.p
		trigger = { exists = capital }
		custom_tooltip = {
			text = te_debug_demog.1.p.tt
			set_variable = te_dg_dbg_click
			if = {
				limit = { has_variable = te_dg_dbg_click }
				remove_variable = te_dg_dbg_click
				te_debug_demog_call3_setup = yes
			}
		}
	}
```

and after `te_debug_demog.1`'s block:

```
# Option p's later reads (phase 2 step 1): the capital's TE_DEMOG_MODS and TE_DEMOG_WORK lines a day after the setup
# (the engine has summed the new modifiers; the pair waits for its refresh) and a month after (the monthly refresh has
# run). Fired only by te_debug_demog_call3_setup.
te_debug_demog.3 = {
	type = country_event
	hidden = yes
	immediate = {
		capital ?= { te_debug_demog_mods_line = yes }
	}
}
```

`te_debug_demog_effects.txt`:

```
# ---- p: call 3's carriers (phase 2 step 1; spec §1.7, plan D12) ------------------------------------
# THIS = ROOT = the player. The carrier kinds no test can read, set up in one go: Community Service (an amendment, on
# Punishment-Focused Criminal Justice, its only allowed law), Woman Soldiers at x0.5 for 60 days (a country modifier)
# and Trade Unions pushed past loyal (its Solidarity or Bourse du Travail trait). Logs the capital now, then a day and
# a month later (te_debug_demog.3). If the law was enacted here and the amendment didn't attach, run p again.
te_debug_demog_call3_setup = {
	capital = { te_debug_demog_mods_line = yes }
	if = {
		limit = { NOT = { has_law = law_type:law_punishment_focused_criminal_justice } }
		activate_law = law_type:law_punishment_focused_criminal_justice
	}
	active_law:lawgroup_criminal_justice ?= {
		add_amendment = {
			type = amendment_community_service
			sponsor = PREV.ig:ig_intelligentsia
		}
	}
	add_modifier = { name = modifier_woman_soldiers multiplier = 0.5 days = 60 }
	ig:ig_trade_unions ?= {
		add_modifier = { name = te_demog_debug_ig_loyal days = 60 }
	}
	trigger_event = { id = te_debug_demog.3 days = 1 }
	trigger_event = { id = te_debug_demog.3 days = 31 }
}
```

`te_debug_demog_modifiers.txt`:

```
# Option p (phase 2 step 1): Trade Unions' approval pushed past loyal for sixty days, so its loyal trait (Solidarity
# or the Bourse du Travail) comes on.
te_demog_debug_ig_loyal = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
	interest_group_approval_add = 30
}
```

Loc (`te_events_l_english.yml` beside `te_debug_demog.1.n`; `te_miscellaneous_l_english.yml` beside
`te_demog_debug_working_adults`):

```
 te_debug_demog.1.p:0 "Call 3's carriers: set them up and log our capital"
 te_debug_demog.1.p.tt:0 "Enacts Punishment-Focused Criminal Justice if needed and attaches Community Service, adds Woman Soldiers at half strength for 60 days and makes the Trade Unions loyal for 60 days. Writes TE_DEMOG_MODS and TE_DEMOG_WORK lines for our capital now, a day later and a month later: womens and replaced are the two families, ww_mod their sum, pair the pair in force, part_m, part and cap the census's inputs, and wa_mod the engine's own field."
 te_demog_debug_ig_loyal:0 "Test: Loyal"
 te_demog_debug_ig_loyal_desc:0 "The demographics test console's 60-day push of an interest group past loyal."
```

- [ ] **Step 5: Run the tests and the harness**

Run: `$V -m unittest test_demographics_harness test_demographics_registry 2>&1 | grep -E '^(Ran |OK|FAILED)' && $V scripts/analysis/demographics_harness.py workforce`
Expected: OK; the table's 1836 farming row reads a target of about 0.25 and old age about 59, the rich row about 0.40.

- [ ] **Step 6: Commit**: "Demographics phase 2 step 1: the harness's workforce table and option l's work line".

---

### Task 8: Docs, the player guide and the owner's in-game list

**Files:**
- Modify: `docs/systems/mod_systems.md` § Demographics
- Modify: `docs/guides/python_tools.md` (the harness's `workforce`; option l's `TE_DEMOG_WORK`)
- Modify: `docs/auto_generated_files.md` (the three new generated files)
- Modify: `docs/player_guide/08-states.md` (State panel additions), then rebuild the PDF
- Modify: `docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md` (status: step 1 built)

- [ ] **Step 1: mod_systems.md.** In § Demographics:
  - **Files table:** a row "Phase 2 step 1 (2026-10-12)": the plan; `te_demog_work_setup`, `_walk_pop`, `_slot`,
    `_finish`, `te_demog_pension_age_refresh`; the generated `te_demog_enter_cal_band`, `_bio_band`,
    `te_demog_old_age_pass`, `te_demog_slot_births`; the values; the workforce lines' type file, injections and three
    generated files; `test_demographics_golden.py`.
  - **Variable families:** a row "Phase 2 step 1": state `te_dg_wa_share`, `_at_work`, `_pensioners`, `_need`,
    `_old_age`, `_low_share`, `_wbase`, `_wf_engine`, `te_dg_ln_working_adults`; country `te_dg_pension_age`.
  - **A subsection "Phase 2 step 1: the interfaces"** after "Causes of Death" (it also lists call 3's inventory, the
    carriers no reader walks and Rosen's lines left on top): the two indexes and where each rule
    reads; the pension age; participation, need and the threshold, computed and stored, applied nowhere; planned and
    unplanned births; the workforce lines' families, their own gate and why; the golden test; what changes in a game
    (the breakdown's name, an institution level within a month).
  - **"Not built yet":** phase 2's remaining steps 2–4, pointing to the spec.
  - **"Owner checks in game":** item 14 (Step 4's list, short).

- [ ] **Step 2: The player guide.** `08-states.md`, State panel additions: "the birth and death effects of laws,
  technologies and institutions appear in the birth rate and mortality tooltips" becomes "the birth, death and
  workforce effects of laws, technologies and institutions appear in the birth rate, mortality and workforce
  tooltips". Run `python3 scripts/analysis/check_player_guide_style.py --strict`, rebuild with
  `$V scripts/build_player_guide.py`, check `python3 scripts/build_player_guide.py --check`.

- [ ] **Step 3: python_tools.md, auto_generated_files.md, the spec's status.** The harness list gains `workforce`
  ("phase 2 step 1: participation, need and the old-age threshold at the starting values"); the console's row notes
  option l's second line; `auto_generated_files.md` lists the three workforce-line files under `gen_demographics.py`;
  the spec's status block names the PR that built step 1.

- [ ] **Step 4: The in-game checklist** (for the owner; the PR body carries it; `mod_systems.md` keeps it short).
  Deploy per CLAUDE.md "Play-testing unmerged work" (never during an observer run).
  1. **Nothing moves.** A Disabled game: a Women's Suffrage country's state shows the same working-adult ratio as a
     game on `main` (option l's `wa_mod=`); its workforce tooltip shows one "Laws and Institutions" line; the law's own
     tooltip still reads "Workforce Ratio +15%".
  2. **Laws refresh that day.** Enact Women's Suffrage by the console: the pair (`ww_mod=`) follows the same day.
     Raise Old Age Pension's institution level: the line follows within a month.
  3. **Under Full the pair stays.** After a state's first census step (M in force), `ww_mod=` still holds the families'
     sum and the workforce tooltip still shows the line.
  4. **The figures in 1836.** Option l in Britain's capital: `wa_share` about 0.7, `at_work` about 0.45–0.5,
     `wf_target` about 0.25, `wbase` about 0.25, `old_age` about 58–62, `need` about 1.0, `pensioners` 0,
     `pension_kind` 0, `child_work` 0.3 (Child Labor Allowed).
     - **Stop rule for step 2: `wf_engine`** (the engine's workforce ÷ people). About 0.25 confirms the census's
       reading; about 0.20 means the engine's ratio is workforce ÷ dependents (as the define's and the modifier's
       descriptions read), and step 2 re-derives the scale and its term on that scale before any fit (spec §1.8).
       Check it in a few states, and in one with aristocrats or slaves (`wbase` away from 0.25).
  5. **A pension country.** A country with Old Age Pension: `pension_var=65` (the owner's variable, read through the
     `owner.var:` chain) and `pensioners` above 0; a country without one: `pension_var=-1`. Switching the welfare law to
     UBI makes `pension_var=-1` that day and `pensioners` reads 0 at the state's next count.
  6. **The skew probe** (options f and g; unrun since #828): how fast a working-adult modifier moves a pop's workforce
     share. Step 2's plan is written after this result (spec §2.1): an instant pull needs a ramp, a slow one a lag on
     the panel.
  7. **The benchmark** (option d): the step's cost within 25% of `main`'s.
  8. **`debug.log`:** no "Failed to fetch variable" or script errors from `te_demog_work_*`, `te_demog_women_rate`,
     `te_demog_old_age_pass`, `te_demog_slot_births` or `te_demog_workforce_lines_refresh`; no load error from the
     two new INJECT files.
  9. **Call 3's unproven carrier kinds reach a state** (D12; spec §1.7). The amendments and the IG traits are the
     two kinds nothing has verified; Woman Soldiers (a country modifier at ×0.5, `scripting_best_practices.md:4918`)
     and Pollution Impact (× impact, probe P1, `:4932`) are proven kinds and ride along. In a new game under Disabled,
     run option p once. Its log gives three pairs of `TE_DEMOG_MODS` / `TE_DEMOG_WORK` lines (before, a day later, a
     month later):
     - **a day later:** `replaced=` up 0.01 (Community Service) and, once Trade Unions are loyal, 0.05 more (the trait);
       `part_m=` up 0.01; `part=` up 0.02 with the trait; `womens=` up 0.025 (Woman Soldiers at ×0.5); `ww_mod=` (the
       families' sum) up by their total. `pair=` (the pair in force) and `wa_mod=` (the engine's own field) haven't
       moved yet, unless option p enacted the law, which refreshes the pair that day: this is the month's lag of
       spec §1.9;
     - **a month later:** `pair=` equal to `ww_mod=`, and `wa_mod=` up by the old flat lines, as on `main`: +0.01,
       +0.05 and +0.025;
     - **the tooltips:** the Trade Unions' trait shows one "Workforce Ratio +5%" line and one "Census: People at
       Work +2%" line, not a +5% and a −5%; Woman Soldiers in the country's modifiers shows one "Workforce Ratio" line;
       Community Service shows "Workforce Ratio +1%" and "Census: Men at Work +1%";
     - **if a kind fails** (its type stays at 0 a month later, or its tooltip shows the cancel): revert that carrier's
       block to its engine field, list it in `P.LIVE_WORKFORCE_LINES` and say so in the PR. The merge waits for this
       item, since a failed kind would lose its line in every game.
  10. **Pollution Impact, in passing:** in a polluted state of the same game, option l's `cap=` reads −0.1 × the
      impact and `replaced=` −0.05 × the same.

- [ ] **Step 5: Run the whole suite and the checks**
  - `$V -m unittest discover -s . -p 'test_*.py' > /tmp/suite.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/suite.txt`;
  - `/home/jakef/src/Vic3TimelineExtended/.venv/bin/ruff check .`;
  - `python3 scripts/format_paradox_tabs.py --check` on the changed `.txt`;
  - `python3 organize_loc.py --check`; `python3 scripts/analysis/check_localization_files.py`;
  - `$V scripts/generators/gen_demographics.py --check`;
  - `python3 scripts/build_player_guide.py --check`;
  - the CI audits (`.github/workflows/ci.yml`'s list), and `python3 scripts/analysis/check_post_load_rosters.py`;
  - the PEP 701 grep on the changed `.py` files.

- [ ] **Step 6: Commit**: "Demographics phase 2 step 1: docs, guide and the in-game list".

- [ ] **Whole-branch review:** a fresh reviewer on the most capable model reads the branch against the spec's §1 and
  this plan's Review Focus, then the owner runs Step 4's list before the merge.

---

## Review stops

| After | Who | Reads |
|---|---|---|
| Task 3 | a fresh reviewer | Tasks 2–3: the model's figures, the generated bands and threshold, the birth line byte for byte |
| Task 5 | a fresh reviewer | Tasks 4–5: the denominators (D4), the pointers, the old save's guarded reads, nothing applied |
| Task 6 | a fresh reviewer | Task 6: the moved lines' values, the own gate (D3), #892's files unchanged, the release |
| Task 8 | a fresh reviewer (most capable model), then the owner in game | the whole branch |

## Self-review notes (for the executor)

- **The golden is recorded once, in Task 1, on the merged tree.** Never re-record it to make a later task pass: a
  changed recorded value is the bug this plan exists to catch. If a later task must change a recorded value, stop and
  ask.
- **`te_dg_low_share`, `te_dg_wbase` and `te_dg_wf_engine` come from the walk**, so the golden's census cases (which
  don't walk) never see them; Task 5's `TestWorkWalk` and the in-game list cover them.
- **The model's `work_figures` takes ages after the step** (the bands' ages), and the script's pointers run on
  `te_dg_age`, not the rate age `te_dg_r`. The death and birth rates keep the rate age.
- **Names reserved for later steps and phase 3:** `te_dg_mw` (step 2's workforce term), `te_dg_d<j>`, `te_dg_s<j>`,
  `te_dg_elig`, `te_dg_cover`, `te_dg_age_rate`, `state_ageing_rate_add`, `state_rejuvenation_add`. Don't use them.
- **The generated files change in Tasks 3 and 6.** Regenerate after each task and after any merge; never merge them
  by hand.
- **`test_no_live_line_but_rosens` will need step 2's census pair** (`te_demog_census_workforce_up`/`_down` in
  `te_demog_modifiers.txt`) in its skip list when step 2 adds it.
- **Call 3's sizes are the owner-approved starting values** (spec §13 call 11): write them as the inventory gives
  them, and don't tune them here; step 2's fit may scale them.
- **Step 2's late-save fit needs the amendments' and IG traits' inputs** (spec §1.8): `DM.load_carriers` walks laws,
  technologies and institutions only, so step 2 reads which amendments are attached and which traits are active from
  the save, or reports the gap beside each scenario. Task 7's `workforce` rows have none of those carriers.
