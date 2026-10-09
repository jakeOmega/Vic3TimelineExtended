# Demographics, phases 0 and 1 (the age model, its harness, the census) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the demographics model (birth cohorts by age and sex, fertility, five causes of death, migration
profiles, per-state Wealth Concentration, Gini, the national urban pattern) as a census the player reads in a new
Demographics tab, with nothing yet applied to the engine.

**Architecture:** One Python model (`scripts/analysis/demographics_model.py`, parameters in `demographics_params.py`)
is the reference. The harness runs it offline against saves; a generator writes the script that mirrors it (the cohort
ring's sweeps, rate tables, engine curves, cause multipliers); hand-written script orchestrates the yearly step from
the state pulse; a full-file override of the vanilla Population panel adds the tab, and the state panel gets a fourth
Population subtab. A test pins committed generated script to a fresh generation, so a parameter change reaches the game
only through regeneration.

**Tech Stack:** Python 3.11/3.12 `unittest`, Paradox Clausewitz script (Victoria 3 1.14.5), `.gui`, YAML loc.

**Spec:** `docs/superpowers/specs/2026-10-08-demographics-design.md` (read it whole first; § numbers below are its
sections). Engine evidence: `docs/testing/demographics-probe-results-2026-10-08.md`. The probe's script is on the
local, unpushed branch `probe/demographics` in the main checkout (`git show probe/demographics:<path>`); the code this
plan reuses from it is copied into the tasks.

## Scope

This plan builds **phase 0's tooling** (PR 1, Tasks 0–4) and **phase 1, the census** (PR 2, Tasks 5–16). Open PR 2's
branch from PR 1's and give both `--base main` (CLAUDE.md, "Stacked PRs must target `main`").

Not in this plan, each to get its own plan once its gate passes:
- **Calibration to world history** (§2.3's targets: world multiples, regional shares, great-power ratios to 2020).
  It needs an observer run's yearly saves and tunes the retuned defines, which only phase 2 applies. PR 1 delivers
  the harness and its reader; the fit itself is phase 2's prerequisite, not PR 1's gate.
- **Phase 2, consequences** (§12): the retuned defines and the births and deaths modifiers, the workforce, pension,
  conscription and youth-bulge effects, the Family & Reproductive Policy laws and measures, the pension-age setting,
  §8.4's removals, Wealth Concentration's effects split by scope, AI weights. Also the pensions' money cost (§13, an
  owner decision) and the panel's Family Policy section with its measure buttons.
- **Phase 3, place and colour** (§12): the settlement pattern (§5.2), the national urban pattern's effects and the
  Planned Capital decision, sex-balance effects, the event wave, Ectogenesis and Immortality with biological age,
  Cultural Hegemony's fertility drift, Internal Resettlement's programme profiles, and the upward and event-driven
  Wealth Concentration shocks, and §2.6's young, male US frontier states at start (France's earlier transition is
  in phase 1, Task 8).
- **Map modes** (§10): blocked. The only map-mode mechanism is the `te_map_mode_*` hijack of Migration Attraction,
  switched off because vanilla's state-scope `migration_pull` returns the country's value
  (`common/decisions/extra_decisions.txt:96-108`, `docs/audits/open_issues.md:306`). Task 0 records it in the spec.

## Decisions this plan takes (the owner can overturn any)

| Decision | Choice | Why |
|---|---|---|
| Cohort width (§1, §13) | One-year cohorts, a ring of 150; `COHORT_WIDTH = 1` in `demographics_params.py` | The spec's decision rule picked them (§1 "Result"); the owner hasn't confirmed the save cost (§13). Only width 1 is built; the model asserts it |
| Cohort storage (§3 says "shares") | **People, not shares** | The engine stores values in units of 1e-5 (`scripting_best_practices.md` § five decimals). A one-year cohort of 90-year-olds is a share near 1e-5, so its deaths would round away. The probe benchmarked people counts (same save cost) |
| Equilibrium seed (§2.6) | The state's own life table times a growth factor read from a one-dimensional table by net reproduction rate | A lookup by fertility and life expectancy for 150 slots and both sexes runs to thousands of literals; the state's life table is computed anyway for the panel, so only the growth factor needs a table (39 knots) |
| Game rule (§11.4) | `demographics_rule`: `demographics_full` (default), `demographics_display_only`, `demographics_disabled`; wrappers `te_demog_cohorts_run` and `te_demog_effects_run` | The mod's convention is `X_disabled`, tested negatively (`scripting_best_practices.md:4626`); no rule anywhere ends in `_off`. In phase 1 Full and Display only behave the same: nothing is applied yet |
| What the rule gates | The cohort model, its walks' cohort inputs, the panel and the history. **Not** the pop and building walks or Wealth Concentration | Inheritance (#822) owns Wealth Concentration and its rural modifiers; it must keep working with the system off |
| Rate tables | Abridged age groups (0, 1–4, 5–9 … 145–149), constant inside a group; rates per 100,000 a year | Matches the harness exactly; every literal fits five decimals |
| Sweep order | The yearly step visits slots in age order (two passes over the ring, guarded by the open slot), so group rates, display bands and migrant classes change only at boundaries | One refresh per group or band instead of a lookup per slot |
| Scaling | Lazy: the ring is scaled to the engine's population by a stored factor applied at the next sweep; the bands and class sums are scaled at once | Avoids a second pass over 300 variables |
| Migration residual in phase 1 | The engine's own natural change is estimated from the pop walk (each pop's SoL on the defines' curves, times the state's birth and mortality modifiers); the residual is the population change less that, less war dead and known kills | The model's births and deaths aren't applied in phase 1, so its natural change can't stand for the engine's |
| War dead | The country's monthly pulse sums each war's `num_country_dead` and keeps the positive change; the yearly country pulse shares the year's dead among states by soldiers; each state's step consumes its share | State pulses fall between March and January and the country pulse on 31 December; a country counter consumed by the first state would lose the rest. A war ending while another runs loses at most that month of the other's dead |
| Known kills | Nuclear strikes and Violent Hostility record their dead on the state; Internal Resettlement's moves stay in the residual until phase 3 | The kill sites already compute their dead; resettlement's programme profiles belong with phase 3's settlement work |
| Seeding | Every state at game start (`on_game_started`, dispatched per country); any state without `te_dg_year` at its first yearly pulse (old saves, new and split states); and a state whose last step is more than a year old is re-seeded | One code path for all three; a missed year would leave a slot unfolded |
| Ownership term (§4.2 gives no coefficient) | `40 × (private share − 0.5)`, capped ±20, over capital buildings | A starting number; calibration may change it |
| Land tenure (§4.2 lists five laws; vanilla has nine) | Serfdom, Manorialism, Latifundias and Expanded Latifundias +15; Tenant Farmers +5; Commercialized Agriculture 0; Peasant Proprietorship and Homesteading −10; Collectivized Agriculture −20 | Great estates read like serfdom, smallholdings like homesteading |
| Taxes on wealth | Graduated Taxation −5; with the tax code on, −20 × the enacted dividend rate (`te_tax_view_en_div_rate`); total capped −10 | The tax code has no estate setting; dividends are its tax on fortunes |
| Urban population (§5.1 names a rate the engine lacks) | The pop walk's people whose workplace isn't in a rural building group (agriculture, plantations, ranching, extraction, both subsistence groups); pops with no workplace count rural if Peasants, else urban | No state-scope urbanisation share exists (`total_urbanization` is points) |
| Gini scale | Computed by the harness from the 1836 Britain save (Task 4) so Britain 1836 reads 0.52 | §4.1's anchor |
| History | Yearly samples on a per-country store of containers, for countries `te_history_country_is_tracked` accepts (player and major powers), at most 100 | The Cultural Hegemony annual store is the precedent; the monthly `te_hist` store would sample a yearly value twelve times |
| Sorted state lists | Built in script with `ordered_scope_state` into a variable list (`trade_partner_effects.txt:147-182` is the precedent); the spec's "as Grand Monuments does" is wrong, `gm_states` is unsorted | |
| Twenty-year outline (§10) | The player's country only (`is_ai = no`), a five-year band projection on the country's population-weighted rates | Running the cohort model forward for every country would cost more than the census itself |

## Global Constraints

- Script literals: **at most five decimals** (`test_engine_literal_forms.py` fails otherwise); rates are written per
  100,000; `multiply = 12 divide = 52`-style integer pairs for awkward ratios.
- Ring: **150 one-year slots**, slot = birth year mod 150; ages 150 and over in a pool with its mean age (§1).
- Sex ratio at birth **105 boys per 100 girls**: 48,780 girls and 51,220 boys per 100,000 births (§3).
- War dead: **95% men, ages 18–40** (§2.5). A residual under **0.3%** of the population is model error (§2.5).
- Wealth Concentration: **0–100**, **3% drift a year** to its target, the country figure kept in `te_inh_concentration`
  so #822's loc and modifiers keep working (§4.2). State property weight: **the country's state-owned levels × the
  state's share of its bureaucrats × 0.1** (Decisions table).
- Shocks (§4.2): a year at war −1 to every state, at most −10 until a year of peace; a lost war −5; devastation
  −10 × the state's devastation a year; a won left revolution −20; a banking crash −5.
- Display bands: **0–4 … 80–84, 85+** (§1). Urban labels: Primate ≥ 40%, Dominant 25–40%, Balanced 10–25%,
  Dispersed < 10% (§5.1).
- Rule checks never test `demographics_full`: `NOT = { has_game_rule = demographics_disabled }` and
  `NOT = { has_game_rule = demographics_display_only }` through the two wrappers, so an old save keeps the system.
- One refresh site per variable family; the GUI and loc read variables, never walk (§11.3).
- Every scripted GUI that changes state has `ai_is_valid = { always = no }`; this phase adds none that do.
- Brace files: tabs (`scripts/format_paradox_tabs.py --check`), exactly one UTF-8 BOM. Generated files must already
  pass the tab check.
- Every scripted-effect call passes exactly the `$X$` names its callee uses (`script_argument_audit --strict`).
- Loc: every new key starts `te_demog_` (routed to `te_miscellaneous_l_english.yml` by a new `organize_loc.py` rule,
  Task 5) except rule keys (`rule_`/`setting_`, which route to `te_game_rules_l_english.yml`) and debug event keys
  (`te_debug_demog.*`, routed to EVENTS). Run `python3 organize_loc.py` and commit what it moves.
- Variables: cohort and walk variables start `te_dg_` (short: there are 300 a state and each name is in the save);
  everything else `te_demog_`.
- Every division in `te_demog_*` and `te_dg_*` script divides by a guarded value block
  (`divide = { value = X min = 1 }` or `min = 0.00001` for shares); Task 5's registry test enforces it.

## Review Focus

1. **A state with no census yet** (an old save before its first yearly pulse, a new or split state). Expected: country
   sums, the States list and the panel skip it; the tab shows "census pending" for a country with none seeded, never
   zeros or a division by zero. Test: Task 10's registry test that every country sum limits on `has_variable =
   te_dg_year`.
2. **A state whose people all leave or die.** Expected: the step finishes with a zero population, no division by
   zero, and the state re-seeds if people return. Test: Task 2's `test_empty_state_steps_without_error` and Task 5's
   guarded-division scan.
3. **A skipped or doubled yearly pulse.** Expected: a second pulse in the same calendar year does nothing; a gap of
   more than one year re-seeds the state. Test: Task 8's registry test of the orchestrator's three branches.
4. **A war ending while another goes on.** Expected: the month's change in the summed dead is floored at zero, so a
   finished war never brings people back. Test: Task 9's registry test for the `min = 0` floor on the snapshot.
5. **The rule set to Disabled.** Expected: no `te_dg_` cohort variable is ever written, the tab and subtab are hidden,
   Wealth Concentration and inheritance's rural modifiers still run. Test: Task 8's registry test that every cohort
   entry point sits behind `te_demog_cohorts_run`.

---

## File map

| File | Responsibility | Task |
|---|---|---|
| `docs/superpowers/specs/2026-10-08-demographics-design.md` | corrections this plan's research found | 0 |
| `scripts/analysis/pop_growth.py`, `test_pop_growth.py` (new) | the engine's growth curves, read from `extra_defines.txt` | 1 |
| `scripts/analysis/demographics_params.py`, `scripts/analysis/demographics_model.py` (new), `test_demographics_model.py` (new) | the model and its anchors | 2 |
| `scripts/analysis/demographics_save_inputs.py` (new), `test_fixtures/demographics/gb_1836_slice.v3` (new), `test_demographics_save_inputs.py` (new) | plain-text save reader | 3 |
| `scripts/analysis/demographics_harness.py` (new), `test_demographics_harness.py` (new), `docs/testing/demographics-harness-2026-10-08.md` (new), `docs/guides/python_tools.md` | harness CLI, first results | 4 |
| `common/game_rules/extra_game_rules.txt`, `common/scripted_triggers/te_demog_triggers.txt` (new), `organize_loc.py`, `common/on_actions/te_demog_on_actions.txt` (new), `test_demographics_registry.py` (new) | rule, gates, hooks, loc routing | 5 |
| `scripts/generators/gen_demographics.py` (new), `common/scripted_effects/te_demog_generated_effects.txt` (new, generated), `common/script_values/te_demog_generated_values.txt` (new, generated), `test_gen_demographics.py` (new) | generated sweeps, tables, curves, multipliers | 6 |
| `common/scripted_effects/te_demog_effects.txt` (new), `common/script_values/te_demog_values.txt` (new) | walks, step, seed, flows, figures, aggregation | 7–10 |
| `common/scripted_effects/te_inheritance_effects.txt`, `common/script_values/te_inheritance_values.txt`, `common/on_actions/te_inheritance_on_actions.txt`, `common/scripted_effects/te_demog_wealth_effects.txt` (new) | per-state Wealth Concentration, Gini | 7, 11 |
| `common/scripted_effects/extra_effects.txt`, `common/on_actions/extra_on_actions.txt`, `common/scripted_effects/banking_cycle_effects.txt`, `common/on_actions/te_civil_war_on_actions.txt` | known kills, shocks | 9, 11 |
| `common/scripted_effects/te_demog_history_effects.txt` (new) | yearly history store | 12 |
| `gui/pops_overview.gui` (new full override), `gui/te_demographics_widgets.gui` (new), `common/scripted_guis/te_system_tab_sguis.txt` | Demographics tab | 13 |
| `gui/states_panel.gui` | fourth Population subtab | 14 |
| `events/te_debug_demog_events.txt` (new), `common/scripted_effects/te_debug_demog_effects.txt` (new), `scripts/analysis/demographics_observer_report.py` (new) | debug console, replay and census logs | 15 |
| `localization/english/*.yml` | every new key | 5–15 |
| `docs/systems/mod_systems.md`, `docs/player_guide/08-states.md`, `docs/player_guide/06-politics.md`, PDF, `docs/auto_generated_files.md`, `docs/guides/gui_modding_guide.md` (CRLF), `docs/guides/scripting_best_practices.md` | docs | 4, 16 |

---

# Part A — PR 1: the model, its harness and the spec corrections

### Task 0: Correct the spec

**Files:** Modify `docs/superpowers/specs/2026-10-08-demographics-design.md`.

The research behind this plan found six places where the spec assumes something the code doesn't have. Fix each in
place, in the spec's own style (short sentences, no "we"); add a line to the status block naming this plan.

- [ ] **Step 1: Game rule names.** §11.4's last paragraph (line ~945): replace `` `NOT = { has_game_rule = …_off }` ``
  with `` `NOT = { has_game_rule = demographics_disabled }` `` and name the three settings: `demographics_full`
  (default), `demographics_display_only`, `demographics_disabled`.
- [ ] **Step 2: Map modes.** In Context ("A map mode can paint any per-state script value", line ~79), §10's "Map
  modes" paragraph and §12's phase 1 row, say that the map-mode hijack is switched off
  (`common/decisions/extra_decisions.txt:96-108`: state-scope `migration_pull` returns the country's value) and that
  the six map modes wait for a working per-state source. Move "map modes" out of phase 1 in §12.
- [ ] **Step 3: Sorted lists.** §10 "States": replace "as Grand Monuments does" with "as the trade-partner lists do
  (`common/scripted_effects/trade_partner_effects.txt:147-182`); `gm_states` is unsorted".
- [ ] **Step 4: Cohorts in people.** §3's first sentence: each cohort stores its women and its men **as numbers of
  people**; one sentence on why (values in units of 1e-5; a one-year cohort of the very old is a share near that).
- [ ] **Step 5: Urban population.** §5.1's first bullet: there is no per-state urbanisation rate
  (`total_urbanization` is points); urban population is the pop walk's people whose workplace isn't in a rural
  building group, with workless Peasants rural.
- [ ] **Step 6: Phase 1 list.** §12's phase 1 row: drop map modes; add "Internal Resettlement moves stay in the
  migration residual until phase 3". §13: add the plan's three owner calls (cohort width; the ownership coefficient;
  the land-tenure mapping for vanilla's nine laws).
- [ ] **Step 7: Commit.**

```bash
git add docs/superpowers/specs/2026-10-08-demographics-design.md
git commit -m "docs: demographics spec — rule names, map modes blocked, cohorts in people, urban population"
```

### Task 1: The engine's growth curves from the defines

`scripts/analysis/pop_growth.py` hard-codes the define values (`:15-25`) and has no test. The harness and the
generator both need the engine's curves, so read them from `common/defines/extra_defines.txt` and keep the module's
API (`calculate_birthrate`, `calculate_mortality`, `calculate_growth_rate`, `rates_at_sol`, the CLI).

**Files:**
- Modify: `scripts/analysis/pop_growth.py:1-70`
- Create: `test_pop_growth.py`

**Interfaces:**
- Produces: `GrowthDefines` (frozen dataclass: `min_birthrate`, `max_birthrate`, `min_mortality`, `max_mortality`
  per **month**; `equilibrium_sol`, `transition_sol`, `max_sol`, `stable_sol`, `transition_birthrate_mult`,
  `max_growth_mortality_mult`), `read_defines(path=DEFINES) -> GrowthDefines`,
  `monthly_birthrate(sol, d, malnourishment=False) -> float`, `monthly_mortality(sol, d) -> float`. The existing
  yearly functions keep their signatures and outputs: they call these with `read_defines()`, × 12, and
  `calculate_birthrate` passes `malnourishment=True` (the module's existing ×(1 − 0.1 × (4 − SoL)) below the
  equilibrium SoL, its approximation of starvation; the generator in Task 6 uses the define curve alone, since the
  engine's starvation modifiers are read through `modifier:state_birth_rate_mult`).

- [ ] **Step 1: Write the failing test**

```python
"""scripts/analysis/pop_growth.py reads the mod's growth defines (#demographics Task 1)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import pop_growth as G  # noqa: E402


class TestDefines(unittest.TestCase):
    def setUp(self):
        self.d = G.read_defines()

    def test_reads_the_file(self):
        self.assertEqual(self.d.max_birthrate, 0.00475)
        self.assertEqual(self.d.min_birthrate, 0.00080)
        self.assertEqual(self.d.max_mortality, 0.00600)
        self.assertEqual(self.d.min_mortality, 0.00100)
        self.assertEqual((self.d.equilibrium_sol, self.d.transition_sol, self.d.max_sol, self.d.stable_sol),
                         (4, 11, 18, 35))

    def test_curve_endpoints(self):
        self.assertAlmostEqual(G.monthly_birthrate(0, self.d), 0.00475)
        self.assertAlmostEqual(G.monthly_birthrate(11, self.d), 0.00475)
        self.assertAlmostEqual(G.monthly_birthrate(35, self.d), 0.00080)
        self.assertAlmostEqual(G.monthly_birthrate(50, self.d), 0.00080)
        self.assertAlmostEqual(G.monthly_mortality(0, self.d), 0.00600)
        self.assertAlmostEqual(G.monthly_mortality(35, self.d), 0.00100)
        self.assertAlmostEqual(G.monthly_mortality(4, self.d), G.monthly_birthrate(4, self.d))
        self.assertAlmostEqual(G.monthly_birthrate(0, self.d, malnourishment=True), 0.00475 * 0.6)

    def test_yearly_api_unchanged(self):
        self.assertAlmostEqual(G.calculate_birthrate(35), 0.00080 * 12)

    def test_stable_sol_shrinks(self):
        # spec Context: absent modifiers a state at SoL 35 shrinks by 0.24% a year
        self.assertAlmostEqual(G.calculate_growth_rate(35), -0.0024, places=6)
```

- [ ] **Step 2: Run it to see it fail**

Run: `python3 -m unittest test_pop_growth -v`
Expected: FAIL, `AttributeError: module 'pop_growth' has no attribute 'read_defines'`.

- [ ] **Step 3: Implement.** Replace the hard-coded block (`MIN_BIRTHRATE = …` through the derived values) with a
  reader. The derived slopes and intercepts are the define file's own formulas (`extra_defines.txt:100-122`); compute
  them inside the two monthly functions from a `GrowthDefines`.

```python
import re
from dataclasses import dataclass
from pathlib import Path

DEFINES = Path(__file__).resolve().parents[2] / "common" / "defines" / "extra_defines.txt"
_NAMES = {
    "min_birthrate": "min_birthrate", "max_birthrate": "max_birthrate",
    "min_mortality": "min_mortality", "max_mortality": "max_mortality",
    "equilibrium_sol": "pop_growth_equilibrium_sol", "transition_sol": "pop_growth_transition_sol",
    "max_sol": "pop_growth_max_sol", "stable_sol": "pop_growth_stable_sol",
    "transition_birthrate_mult": "transition_birthrate_mult",
    "max_growth_mortality_mult": "max_growth_mortality_mult",
}


@dataclass(frozen=True)
class GrowthDefines:
    min_birthrate: float
    max_birthrate: float
    min_mortality: float
    max_mortality: float
    equilibrium_sol: float
    transition_sol: float
    max_sol: float
    stable_sol: float
    transition_birthrate_mult: float
    max_growth_mortality_mult: float


def read_defines(path=DEFINES):
    """The @-variables of the pop growth block, monthly rates as written."""
    text = Path(path).read_text(encoding="utf-8-sig")
    values = {}
    for field_name, var in _NAMES.items():
        m = re.search(rf"^@{var}\s*=\s*([-0-9.]+)", text, re.MULTILINE)
        if not m:
            raise KeyError(f"@{var} not found in {path}")
        values[field_name] = float(m.group(1))
    return GrowthDefines(**values)


def monthly_birthrate(sol, d, malnourishment=False):
    at_transition = d.max_birthrate * d.transition_birthrate_mult
    if sol <= d.transition_sol:
        pre_slope = (at_transition - d.max_birthrate) / d.transition_sol
        rate = d.max_birthrate + pre_slope * sol
        if malnourishment and sol < d.equilibrium_sol:
            rate *= 1 - 0.1 * (d.equilibrium_sol - sol)
        return rate
    if sol >= d.stable_sol:
        return d.min_birthrate
    slope = (d.min_birthrate - at_transition) / (d.stable_sol - d.transition_sol)
    return d.min_birthrate + slope * (sol - d.stable_sol)


def monthly_mortality(sol, d):
    at_transition = d.max_birthrate * d.transition_birthrate_mult
    at_eq = d.equilibrium_sol * ((at_transition - d.max_birthrate) / d.transition_sol) + d.max_birthrate
    birth_at_max = (d.max_sol - d.transition_sol) * (
        (d.min_birthrate - at_transition) / (d.stable_sol - d.transition_sol)) + at_transition
    mort_at_max = birth_at_max * d.max_growth_mortality_mult
    if sol <= d.equilibrium_sol:
        return d.max_mortality + (at_eq - d.max_mortality) / d.equilibrium_sol * sol
    if sol <= d.max_sol:
        return at_eq + (mort_at_max - at_eq) / (d.max_sol - d.equilibrium_sol) * (sol - d.equilibrium_sol)
    if sol < d.stable_sol:
        return mort_at_max + (d.min_mortality - mort_at_max) / (d.stable_sol - d.max_sol) * (sol - d.max_sol)
    return d.min_mortality
```

  Then make `calculate_birthrate(sol)` return `monthly_birthrate(sol, _DEFAULT, malnourishment=True) * 12` and
  `calculate_mortality(sol)` return `monthly_mortality(sol, _DEFAULT) * 12`, with `_DEFAULT = read_defines()` at
  import (this was checked before the plan was written: the new functions match the old module to 1e-17 for SoL
  0–50); replace the module-level `POP_GROWTH_*_SOL` names `print_key_thresholds` reads with `_DEFAULT`'s fields; keep `calculate_growth_rate`, `rates_at_sol` and the CLI
  unchanged. Check `subsistence_capacity_projection.py` (its only importer) still runs:
  `python3 scripts/analysis/subsistence_capacity_projection.py --help`.

- [ ] **Step 4: Run the test**

Run: `python3 -m unittest test_pop_growth -v && ruff check scripts/analysis/pop_growth.py test_pop_growth.py`
Expected: 4 tests OK; ruff clean. `python3 scripts/analysis/pop_growth.py --sol 15` prints the same row as before the change.

- [ ] **Step 5: Commit**

```bash
git add scripts/analysis/pop_growth.py test_pop_growth.py
git commit -m "pop_growth: read the growth curves from extra_defines.txt"
```

### Task 2: The parameters and the cohort model

The model is the reference for everything after it. Its tests pin §2.2–§2.4's anchors with the starting parameters
below; the numbers were run before this plan was written and all 23 tests pass with them.

**Files:**
- Create: `scripts/analysis/demographics_params.py`, `scripts/analysis/demographics_model.py`
- Create: `test_demographics_model.py`

**Interfaces:**
- Produces (used by Tasks 4, 6 and 15):
  - `demographics_params`: `RING_YEARS`, `COHORT_WIDTH`, `FEMALE_BIRTH_PER_100K`, `MALE_BIRTH_PER_100K`, `GROUPS`
    (31 `(start, width)`), `group_of(age) -> int`, `INFECTION`/`EXTERNAL`/`CHRONIC` (`{"f": [31], "m": [31]}`),
    `WORK_BASE` (`[31]`), `MATERNAL_PER_100K_BIRTHS`, `ASFR_SHAPE_BY_GROUP`, `WEALTH_TFR_*`, `EDUCATION_WEIGHT`,
    `SURVIVAL_WEIGHT`, `URBAN_WEIGHT`, `MEANS_TIERS`, `MEANS_LAW_SHIFT`, `MEANS_CAP`, `TECH_MULT`, `LAW_MULT`,
    `INSTITUTION_MULT`, `SOL_INFECTION_AT_HIGH`, `SOL_CHRONIC_AT_HIGH`, `LITERACY_INFECTION_WEIGHT`,
    `CROWDING_INFECTION_MULT`, `FEMALE_WORK_SHARE`, `FEMALE_WORK_SHARE_DEFAULT`, `WAR_DEAD_MALE_SHARE`,
    `WAR_DEAD_AGES`, `RESIDUAL_NOISE_SHARE`, `MIGRANT_CLASSES`, `MIGRANT_PROFILE`, `LABOUR_FEMALE_SHARE_MIN/MAX`,
    `FAMILY_TRANSPORT_TECHS`, `FAMILY_BASE`, `FAMILY_RIGHTS_WEIGHT`, `FULL_FEMALE_WORK_SHARE`, `CHAIN_STEP`,
    `CHAIN_CAP`, `CRISIS_AT_WAR`, `INCOME_WEALTH_CAP`, `GINI_FLOOR`, `GINI_SCALE` (0.85, from the 1836 save; Task 4
    re-runs it), `BAND_WIDTH`, `BANDS`.
  - `demographics_model`: `Inputs`, `Ring` (`f`, `m`, `pool_f`, `pool_m`, `pool_age`, `scale`, `year`, `class_f`,
    `class_m`, `men_18_40`, `women_18_40`, `total`; `age_of_slot(k)`, `people()`, `by_age()`), `wealth_tfr(sol)`,
    `female_work_share(inp)`, `cause_multipliers(inp) -> dict`, `rates_from_multipliers(mult, work_f, work_m) ->
    (qf, qm)`, `work_split(inp, work_mult) -> (f, m)`, `group_rates(inp) -> (qf, qm, mmr)`,
    `life_table(q) -> {"e0", "e65", "q0_per_1000"}`, `means(inp)`, `fertility(inp, e0) -> dict`,
    `asfr_shape(rate_age)`, `migrant_profile(inp) -> {(class, "f"|"m"): share}`, `class_of(age)`,
    `growth_factor(nrr)`, `nrr(tfr, qf)`, `seed(inp, year, engine_pop) -> Ring`,
    `step(ring, inp, year, engine_pop=None, war_dead=0, kills=0, migration=0, rates=None) -> dict`,
    `grouped_gini(groups) -> float`, `shown_gini(grouped) -> float`, `structure(ring) -> dict`,
    `run_constant(inp, years, year0) -> (Ring, dict)`, `_refresh_denominators(ring)`.

- [ ] **Step 1: Write the failing test** — `test_demographics_model.py`:

```python
"""The demographics cohort model (scripts/analysis/demographics_model.py).

Pins the model's behaviour to the design's anchors
(docs/superpowers/specs/2026-10-08-demographics-design.md §1, §2.2-§2.4, §3) so a
parameter change that breaks a real-world anchor fails here, before it is generated
into script.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402

MODERN = frozenset({
    "medical_degrees", "pharmaceuticals", "modern_nursing", "antibiotics", "modern_vaccines",
    "antibiotic_mass_production", "vulcanization", "contraceptive_pill", "modern_pharmaceuticals",
    "combustion_engine",
})
EARLY_MEDICINE = frozenset({"medical_degrees", "pharmaceuticals", "modern_nursing", "antibiotics", "vulcanization"})

AGRARIAN_1836 = M.Inputs(sol=8, literacy=0.2, urban_share=0.1)
BRITAIN_1836 = M.Inputs(sol=11, literacy=0.35, urban_share=0.3, laws=frozenset({"law_no_womens_rights"}))
FRANCE_1836 = M.Inputs(sol=11, literacy=0.3, urban_share=0.15, means_override=0.8)
WEST_1950 = M.Inputs(sol=25, literacy=0.9, urban_share=0.6, techs=EARLY_MEDICINE,
                     laws=frozenset({"law_private_health_insurance", "law_women_in_the_workplace"}),
                     institutions={"institution_health_system": 2, "institution_workplace_safety": 2})
WEST_1990 = M.Inputs(sol=38, literacy=0.98, urban_share=0.75, techs=MODERN,
                     laws=frozenset({"law_public_health_insurance", "law_womens_suffrage",
                                     "law_old_age_pension", "law_dedicated_police"}),
                     institutions={"institution_health_system": 4, "institution_workplace_safety": 4,
                                   "institution_ministry_of_consumer_protection": 3})
INDIA_1975 = M.Inputs(sol=9, literacy=0.35, urban_share=0.2,
                      techs=EARLY_MEDICINE | {"modern_vaccines", "contraceptive_pill"},
                      laws=frozenset({"law_charitable_health_system"}))


class TestFertility(unittest.TestCase):
    """§2.3's sketch table: the formula with plausible inputs."""

    def tfr(self, inp):
        _ring, last = M.run_constant(inp, years=200)
        return last["tfr"]

    def test_sketch_cases(self):
        for inp, expected, label in [
            (BRITAIN_1836, 5.5, "Britain 1836"),
            (FRANCE_1836, 4.9, "France 1836 (means 0.8)"),
            (WEST_1950, 3.1, "the West 1950"),
            (WEST_1990, 1.4, "the West 1990"),
            (INDIA_1975, 5.1, "India 1975"),
        ]:
            with self.subTest(label):
                self.assertAlmostEqual(self.tfr(inp), expected, delta=0.3)

    def test_wealth_term_endpoints(self):
        self.assertAlmostEqual(M.wealth_tfr(0), 6.2)
        self.assertAlmostEqual(M.wealth_tfr(8), 6.2)
        self.assertAlmostEqual(M.wealth_tfr(35), 3.5)
        self.assertAlmostEqual(M.wealth_tfr(60), 3.5)

    def test_means_capped(self):
        rich = M.Inputs(literacy=1.0, techs=MODERN, laws=frozenset({"law_state_sponsored_family_planning"}))
        self.assertLessEqual(M.means(rich), P.MEANS_CAP)

    def test_asfr_shape_sums_to_one(self):
        self.assertAlmostEqual(sum(M.asfr_shape(r) for r in range(100)), 100000.0)


class TestMortality(unittest.TestCase):
    """§2.4's anchors: infant mortality, life expectancy at birth and at 65."""

    def table(self, inp):
        qf, qm, _ = M.group_rates(inp)
        f, m = M.life_table(qf), M.life_table(qm)
        return {k: (f[k] + m[k]) / 2 for k in f}

    def test_1836_europe(self):
        t = self.table(BRITAIN_1836)
        self.assertTrue(150 <= t["q0_per_1000"] <= 250, t)
        self.assertTrue(35 <= t["e0"] <= 43, t)
        self.assertTrue(10 <= t["e65"] <= 14, t)

    def test_rich_country_today(self):
        t = self.table(WEST_1990)
        self.assertLess(t["q0_per_1000"], 15)
        self.assertTrue(72 <= t["e0"] <= 80, t)
        self.assertTrue(17 <= t["e65"] <= 23, t)

    def test_women_outlive_men(self):
        for inp in (BRITAIN_1836, WEST_1990):
            qf, qm, _ = M.group_rates(inp)
            gap = M.life_table(qf)["e0"] - M.life_table(qm)["e0"]
            self.assertTrue(1.0 <= gap <= 8.0, gap)

    def test_no_deaths_lives_to_the_end_of_the_ring(self):
        self.assertAlmostEqual(M.life_table([0.0] * len(P.GROUPS))["e0"], 150.0)

    def test_work_deaths_follow_the_workforce(self):
        before = M.group_rates(M.Inputs(laws=frozenset({"law_no_womens_rights"})))[0]
        after = M.group_rates(M.Inputs(laws=frozenset({"law_women_in_the_workplace"})))[0]
        g = P.group_of(30)
        self.assertGreater(after[g], before[g])


class TestStructure(unittest.TestCase):
    """§2.2's equilibrium table and the demographic dividend."""

    def test_agrarian_reference(self):
        ring, last = M.run_constant(AGRARIAN_1836, years=300)
        s = M.structure(ring)
        self.assertTrue(0.33 <= s["young"] <= 0.43, s)
        self.assertTrue(0.03 <= s["old"] <= 0.07, s)
        self.assertTrue(0.008 <= last["growth"] <= 0.02, last["growth"])

    def test_aged(self):
        ring, last = M.run_constant(WEST_1990, years=300)
        s = M.structure(ring)
        self.assertTrue(0.09 <= s["young"] <= 0.14, s)
        self.assertTrue(0.28 <= s["old"] <= 0.38, s)
        self.assertTrue(-0.015 <= last["growth"] <= -0.008, last["growth"])

    def test_dividend_window(self):
        ring, _ = M.run_constant(AGRARIAN_1836, years=300)
        start = M.structure(ring)["working"]
        factor = M.fertility(AGRARIAN_1836, 40)["factor"]
        low = M.Inputs(sol=8, literacy=0.2, urban_share=0.1, wealth_tfr=2.2 / factor)
        year = ring.year
        peak = start
        for _ in range(30):
            year += 1
            M.step(ring, low, year)
            peak = max(peak, M.structure(ring)["working"])
        self.assertGreaterEqual(peak - start, 0.08)

    def test_sex_balance(self):
        ring, _ = M.run_constant(BRITAIN_1836, years=200)
        self.assertTrue(90 <= M.structure(ring)["men_per_100_women"] <= 102)


class TestRing(unittest.TestCase):
    """§1: birth cohorts age exactly; the ring wraps; scaling matches the engine."""

    def test_seed_is_steady(self):
        ring = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        before = M.structure(ring)
        for year in range(1837, 1857):
            M.step(ring, AGRARIAN_1836, year)
        after = M.structure(ring)
        self.assertLess(abs(after["young"] - before["young"]), 0.015)
        self.assertLess(abs(after["old"] - before["old"]), 0.01)

    def test_a_birth_cohort_does_not_spread(self):
        """Extra men born in 1800 stay in one slot for 120 years, then fold into the pool."""
        ring = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        twin = M.seed(AGRARIAN_1836, 1836, 1_000_000)
        marked = 1800 % P.RING_YEARS
        ring.m[marked] += 777.0
        for year in range(1837, 1921):
            M.step(ring, AGRARIAN_1836, year)
            M.step(twin, AGRARIAN_1836, year)
        diffs = [a - b for a, b in zip(ring.m, twin.m)]
        self.assertEqual(ring.age_of_slot(marked), 120)
        self.assertGreater(diffs[marked], 0.0)
        self.assertLess(sum(abs(d) for i, d in enumerate(diffs) if i != marked), 1e-6)
        for year in range(1921, 1951):
            M.step(ring, AGRARIAN_1836, year)
            M.step(twin, AGRARIAN_1836, year)
        self.assertEqual(ring.age_of_slot(marked), 0)
        self.assertGreater(ring.pool_m, twin.pool_m)

    def test_scaled_to_engine_population(self):
        ring = M.seed(BRITAIN_1836, 1836, 2_500_000)
        self.assertAlmostEqual(ring.people(), 2_500_000, delta=1)
        M.step(ring, BRITAIN_1836, 1837, engine_pop=2_510_000)
        self.assertAlmostEqual(ring.people(), 2_510_000, delta=1)

    def test_births_minus_deaths_balance(self):
        ring = M.seed(BRITAIN_1836, 1836, 1_000_000)
        before = ring.people()
        out = M.step(ring, BRITAIN_1836, 1837)
        self.assertAlmostEqual(ring.people(), before + out["births"] - out["deaths"], delta=0.01)

    def test_empty_state_steps_without_error(self):
        ring = M.seed(BRITAIN_1836, 1836, 0)
        self.assertEqual(ring.people(), 0)
        M.step(ring, BRITAIN_1836, 1837, engine_pop=0, war_dead=50, kills=10, migration=-200)
        self.assertEqual(ring.people(), 0)
        M.step(ring, BRITAIN_1836, 1838, engine_pop=1000, migration=1000)
        self.assertAlmostEqual(ring.people(), 1000, delta=0.01)

    def test_war_dead_are_young_men(self):
        ring = M.seed(BRITAIN_1836, 1836, 1_000_000)
        twin = M.seed(BRITAIN_1836, 1836, 1_000_000)
        M.step(ring, BRITAIN_1836, 1837, war_dead=10_000)
        M.step(twin, BRITAIN_1836, 1837)
        lost_m = sum(t[2] - r[2] for r, t in zip(ring.by_age(), twin.by_age()))
        lost_f = sum(t[1] - r[1] for r, t in zip(ring.by_age(), twin.by_age()))
        self.assertAlmostEqual(lost_m, 9_500, delta=250)  # last year's denominators
        self.assertAlmostEqual(lost_f, 500, delta=50)
        old_m = sum(t[2] - r[2] for r, t in zip(ring.by_age(), twin.by_age()) if r[0] > 41)
        self.assertAlmostEqual(old_m, 0.0, delta=1.0)

    def test_labour_migrants_are_young_adults(self):
        ring = M.seed(BRITAIN_1836, 1836, 1_000_000)
        twin = M.seed(BRITAIN_1836, 1836, 1_000_000)
        M.step(ring, BRITAIN_1836, 1837, migration=20_000)
        M.step(twin, BRITAIN_1836, 1837)
        gained = {a: (r[1] + r[2]) - (t[1] + t[2]) for r, t in zip(ring.by_age(), twin.by_age()) for a in [r[0]]}
        prime = sum(v for a, v in gained.items() if 18 <= a <= 35)
        self.assertGreater(prime / 20_000, 0.5)


class TestInequality(unittest.TestCase):
    """§4.1: the grouped Gini and its map to the panel's figure."""

    def test_equal_groups(self):
        self.assertAlmostEqual(M.grouped_gini([(10, 100), (10, 100)]), 0.0)

    def test_one_group_owns_everything(self):
        self.assertGreater(M.grouped_gini([(99, 0.0001), (1, 1000)]), 0.98)

    def test_britain_1836_anchor(self):
        # Britain's strata in the 1836 save (people, spending per head at capped wealth)
        groups = [(23.65e6, 23.65e6 * 314), (2.08e6, 2.08e6 * 685), (0.22e6, 0.22e6 * 9759)]
        self.assertAlmostEqual(M.shown_gini(M.grouped_gini(groups)), 0.52, delta=0.02)
```

- [ ] **Step 2: Run it to see it fail**

Run: `python3 -m unittest test_demographics_model -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'demographics_model'`.

- [ ] **Step 3: Write the parameters** — `scripts/analysis/demographics_params.py`:

```python
"""Demographics model parameters: the one source for the harness and the generator.

Spec: docs/superpowers/specs/2026-10-08-demographics-design.md. Every number here is a
starting proposal (the spec's header); calibration edits this file, then
`python3 scripts/generators/gen_demographics.py` rewrites the script that mirrors it.

Units. Death rates are yearly probabilities per 100,000 people, fertility shapes per
100,000, so every literal the generator writes stays within the engine's five decimals
(scripting_best_practices.md: values are stored in units of 1e-5).
"""

RING_YEARS = 150            # spec §1: slots reach about age 150; 150+ folds into a pool
COHORT_WIDTH = 1            # spec §1 decision rule; owner to confirm (§13). Only 1 is built.
FEMALE_BIRTH_PER_100K = 48780   # 100 girls per 205 births (§3)
MALE_BIRTH_PER_100K = 51220

# Abridged age groups (start, width). Rates are constant inside a group.
GROUPS = [(0, 1), (1, 4)] + [(a, 5) for a in range(5, 150, 5)]
GROUP_STARTS = [g[0] for g in GROUPS]


def group_of(age):
    """Index into GROUPS for a rate age 0..149 (150+ uses the last group)."""
    age = min(age, 149)
    for i in range(len(GROUPS) - 1, -1, -1):
        if age >= GROUPS[i][0]:
            return i
    return 0


# ---- Mortality: five causes (§2.4), base schedules per 100k a year ----------------
# The base is a population with literacy 0, SoL 8 or below and no medical technology,
# law or institution; every multiplier is 1 there. Values are per group, in GROUPS order
# (31 entries). The women's and men's lists differ where §2.4 says they do.
def _by_group(points):
    """Expand {start_age: rate} breakpoints to one value per group (step function)."""
    out, cur = [], 0
    for start, _w in GROUPS:
        if start in points:
            cur = points[start]
        out.append(cur)
    return out


# Infection and malnutrition: mostly under 5; also 5-14 and the old.
INFECTION = {
    "f": _by_group({0: 19000, 1: 4200, 5: 1000, 10: 550, 15: 750, 45: 900, 65: 1500, 80: 2800}),
    "m": _by_group({0: 21000, 1: 4300, 5: 1000, 10: 550, 15: 750, 45: 950, 65: 1600, 80: 2900}),
}
# Work accidents per 100k people aged 15-64, before the split between the sexes (§2.4).
WORK_BASE = _by_group({0: 0, 15: 160, 65: 0})
# Other external causes: violence, traffic, accidents; 15-44 men three times women.
EXTERNAL = {
    "f": _by_group({0: 60, 5: 40, 15: 60, 45: 50, 65: 80}),
    "m": _by_group({0: 70, 5: 50, 15: 180, 45: 110, 65: 110}),
}
# Chronic and old age: rising from 40, doubling about every 8 years; men higher.
_CHRONIC_F = {0: 0, 5: 60, 20: 120, 30: 180, 40: 320, 45: 480, 50: 720, 55: 1100, 60: 1700,
              65: 2600, 70: 4000, 75: 6200, 80: 9600, 85: 14800, 90: 22000, 95: 32000,
              100: 42000, 105: 50000, 110: 56000}
CHRONIC = {
    "f": _by_group(_CHRONIC_F),
    "m": _by_group({a: (v * 13) // 10 for a, v in _CHRONIC_F.items()}),
}
# Maternal deaths per 100k births (one in 150 at the base).
MATERNAL_PER_100K_BIRTHS = 670

# ---- Fertility (§2.3) -------------------------------------------------------------
# Age-specific shape over rate ages 15-49 by five-year group, per 100k, summing to
# 100,000 over the 35 single years (each single year takes its group's value / 5).
ASFR_SHAPE_BY_GROUP = {15: 6000, 20: 22000, 25: 25000, 30: 21000, 35: 15000, 40: 8500, 45: 2500}
WEALTH_TFR_LOW, WEALTH_TFR_LOW_SOL = 6.2, 8      # children per woman at SoL 8 or below
WEALTH_TFR_HIGH, WEALTH_TFR_HIGH_SOL = 3.5, 35   # what wealth alone does at SoL 35+
EDUCATION_WEIGHT = 0.4        # desired x (1 - 0.4 x literacy)
SURVIVAL_WEIGHT = 0.4         # desired x (1 - 0.4 x (e0 - 30) / 50), clamped 0..1
URBAN_WEIGHT = 0.2            # desired x (1 - 0.2 x urban share)
MEANS_TIERS = [               # (technology, means); the highest held applies
    (None, 0.4), ("vulcanization", 0.55), ("contraceptive_pill", 0.8), ("modern_pharmaceuticals", 0.9),
]
MEANS_LAW_SHIFT = {"law_state_sponsored_family_planning": 0.1}
MEANS_CAP = 0.95

# ---- Cause multipliers from state inputs (§2.4) -----------------------------------
TECH_MULT = {
    "infection": {"medical_degrees": 0.9, "pharmaceuticals": 0.85, "modern_nursing": 0.85,
                  "antibiotics": 0.6, "modern_vaccines": 0.6, "antibiotic_mass_production": 0.8},
    "external": {"combustion_engine": 1.3},
    "maternal": {"modern_nursing": 0.5, "antibiotics": 0.4, "modern_pharmaceuticals": 0.5},
    "chronic": {"modern_pharmaceuticals": 0.75, "telemedicine": 0.9, "personalized_medicine": 0.6},
    "work": {},
}
LAW_MULT = {
    "infection": {"law_charitable_health_system": 0.95, "law_private_health_insurance": 0.85,
                  "law_public_health_insurance": 0.75},
    "maternal": {"law_charitable_health_system": 0.85, "law_private_health_insurance": 0.6,
                 "law_public_health_insurance": 0.5},
    "chronic": {"law_private_health_insurance": 0.85, "law_public_health_insurance": 0.75,
                "law_old_age_pension": 0.95},
    "external": {"law_local_police": 0.95, "law_dedicated_police": 0.9, "law_militarized_police": 0.9},
    "work": {"law_child_labor_allowed": 1.1},
}
# Per institution level (0-5), compounding: mult ** level.
INSTITUTION_MULT = {
    "infection": {"institution_health_system": 0.95},
    "work": {"institution_workplace_safety": 0.85},
    "external": {"institution_ministry_of_consumer_protection": 0.9},
}
# Nutrition: SoL lowers infection from x1 at SoL 8 to x0.6 at SoL 35; chronic x1 to x0.85.
SOL_INFECTION_AT_HIGH = 0.6
SOL_CHRONIC_AT_HIGH = 0.85
LITERACY_INFECTION_WEIGHT = 0.3   # mothers' literacy: infection x (1 - 0.3 x literacy)
CROWDING_INFECTION_MULT = 1.15    # migration_crowding active and no urban planning institution

# Women's share of the workforce by women's-rights law, for splitting work deaths (§2.4).
FEMALE_WORK_SHARE = {
    "law_no_womens_rights": 0.1, "law_women_in_the_fields": 0.25, "law_women_own_property": 0.3,
    "law_women_in_the_workplace": 0.45, "law_womens_suffrage": 0.47, "law_protected_class": 0.48,
}
FEMALE_WORK_SHARE_DEFAULT = 0.1

# ---- War dead and migrants (§2.5) -------------------------------------------------
WAR_DEAD_MALE_SHARE = 0.95
WAR_DEAD_AGES = (18, 40)
RESIDUAL_NOISE_SHARE = 0.003   # a residual under 0.3% of the population is model error
# Age classes for migrant profiles: (first age, last age) by step age.
MIGRANT_CLASSES = [(0, 14), (15, 17), (18, 35), (36, 59), (60, 150)]
# Density per class for each kind; women's share separately.
MIGRANT_PROFILE = {
    "labour": {"weights": [0.0, 0.05, 0.9, 0.05, 0.0]},
    "family": {"weights": [0.35, 0.05, 0.35, 0.22, 0.03], "female_share": 0.5},
    "refugee": {"weights": [0.27, 0.05, 0.3, 0.25, 0.13], "female_share": 0.5},
}
LABOUR_FEMALE_SHARE_MIN, LABOUR_FEMALE_SHARE_MAX = 0.1, 0.6
FAMILY_TRANSPORT_TECHS = {"paddle_steamer": 0.1, "railways": 0.1, "combustion_engine": 0.15}
FAMILY_BASE = 0.2                 # families' weight before transport, rights and chain migration
FAMILY_RIGHTS_WEIGHT = 0.2        # x women's work share / FULL_FEMALE_WORK_SHARE
FULL_FEMALE_WORK_SHARE = 0.48     # Protected Class's share: women's rights at their fullest
CHAIN_STEP, CHAIN_CAP = 0.02, 0.2  # per consecutive year of net inflow, at most
CRISIS_AT_WAR = 0.3               # refugees' weight while the owner is at war, before devastation and turmoil

# ---- Income inequality (§4.1) -----------------------------------------------------
# Spending per head stands in for income: the buy package cost at the pop's wealth,
# capped at INCOME_WEALTH_CAP (the mod's packages grow exponentially past it). The
# panel shows GINI_FLOOR + GINI_SCALE x the grouped Gini over the three strata; the
# harness's `gini` command sets GINI_SCALE so Britain 1836 reads 0.52.
INCOME_WEALTH_CAP = 60
GINI_FLOOR = 0.30
GINI_SCALE = 0.85

# ---- Display ----------------------------------------------------------------------
BAND_WIDTH = 5
BANDS = 18          # 0-4 ... 80-84, then 85+
```

- [ ] **Step 4: Write the model** — `scripts/analysis/demographics_model.py`:

```python
"""The demographics cohort model in Python: the reference the generated script mirrors.

Spec: docs/superpowers/specs/2026-10-08-demographics-design.md §1-§3, §2.6. Every
function here has a script twin; the order of operations in `step` and `seed` is the
order of the script's sweep (common/scripted_effects/te_demog_effects.txt), so a state
logged before and after one in-game step replays here to within rounding
(`demographics_harness.py replay`).

The ring: RING_YEARS slots, one per birth year, slot = birth year mod RING_YEARS. After
the step of year Y, slot Y mod RING_YEARS holds that year's births (age 0) and the slot
for age a holds the people born in Y - a. Ages 150 and over live in a pool.
"""

from dataclasses import dataclass, field

try:  # repo layout: scripts/analysis/ on sys.path, or imported as a namespace package
    import demographics_params as P
except ImportError:  # pragma: no cover
    from scripts.analysis import demographics_params as P

N = P.RING_YEARS
assert P.COHORT_WIDTH == 1, "only one-year cohorts are built (spec §1, §13)"


@dataclass
class Inputs:
    """What one state's yearly walk and its owner's laws and technology give the model."""
    sol: float = 8.0
    literacy: float = 0.0
    urban_share: float = 0.0
    techs: frozenset = frozenset()
    laws: frozenset = frozenset()
    institutions: dict = field(default_factory=dict)
    crowding: bool = False
    wealth_tfr: float | None = None      # pop-weighted SoL curve from the walk
    means_override: float | None = None  # a floor on the means (France 1836, §2.6; te_dg_means_floor)
    female_job_share: float = 0.3        # light industry + services share of the employed
    crisis: float = 0.0                  # 0..1: war, devastation, turmoil at the origin
    inflow_years: int = 0                # consecutive years of net inflow (chain migration)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp_sol(sol, at_low, at_high, lo_sol=P.WEALTH_TFR_LOW_SOL, hi_sol=P.WEALTH_TFR_HIGH_SOL):
    t = clamp((sol - lo_sol) / (hi_sol - lo_sol), 0.0, 1.0)
    return at_low + (at_high - at_low) * t


def wealth_tfr(sol):
    """Children per woman from wealth alone: the retuned SoL curve as a TFR (§2.3)."""
    return lerp_sol(sol, P.WEALTH_TFR_LOW, P.WEALTH_TFR_HIGH)


def female_work_share(inp):
    for law, share in P.FEMALE_WORK_SHARE.items():
        if law in inp.laws:
            return share
    return P.FEMALE_WORK_SHARE_DEFAULT


def cause_multipliers(inp):
    """One multiplier per cause from the state's inputs; 1.0 at the base (§2.4)."""
    mult = {c: 1.0 for c in ("infection", "work", "external", "maternal", "chronic")}
    for cause, techs in P.TECH_MULT.items():
        for tech, m in techs.items():
            if tech in inp.techs:
                mult[cause] *= m
    for cause, laws in P.LAW_MULT.items():
        for law, m in laws.items():
            if law in inp.laws:
                mult[cause] *= m
    for cause, insts in P.INSTITUTION_MULT.items():
        for inst, m in insts.items():
            mult[cause] *= m ** inp.institutions.get(inst, 0)
    mult["infection"] *= lerp_sol(inp.sol, 1.0, P.SOL_INFECTION_AT_HIGH)
    mult["infection"] *= 1 - P.LITERACY_INFECTION_WEIGHT * inp.literacy
    if inp.crowding and inp.institutions.get("institution_ministry_of_urban_planning", 0) == 0:
        mult["infection"] *= P.CROWDING_INFECTION_MULT
    mult["chronic"] *= lerp_sol(inp.sol, 1.0, P.SOL_CHRONIC_AT_HIGH)
    return mult


def rates_from_multipliers(mult, work_f, work_m):
    """Yearly death probability per 100k for each age group, women and men.

    mult: cause -> multiplier (infection, external, chronic; work is folded into
    work_f / work_m, which already carry the split between the sexes). The script's
    te_demog_enter_group computes the same sum.
    """
    qf, qm = [], []
    for g in range(len(P.GROUPS)):
        qf.append(min(100000.0, P.INFECTION["f"][g] * mult["infection"] + P.WORK_BASE[g] * work_f
                      + P.EXTERNAL["f"][g] * mult["external"] + P.CHRONIC["f"][g] * mult["chronic"]))
        qm.append(min(100000.0, P.INFECTION["m"][g] * mult["infection"] + P.WORK_BASE[g] * work_m
                      + P.EXTERNAL["m"][g] * mult["external"] + P.CHRONIC["m"][g] * mult["chronic"]))
    return qf, qm


def work_split(inp, work_mult):
    """(women's, men's) work-death multipliers: the cause multiplier x 2 x each sex's share."""
    fw = female_work_share(inp)
    return work_mult * 2 * fw, work_mult * 2 * (1 - fw)


def group_rates(inp):
    """Group rates for women and men, and maternal deaths per 100k births."""
    m = cause_multipliers(inp)
    work_f, work_m = work_split(inp, m["work"])
    qf, qm = rates_from_multipliers(m, work_f, work_m)
    return qf, qm, m["maternal"] * P.MATERNAL_PER_100K_BIRTHS


def life_table(q):
    """e0, e65 and infant mortality from group rates, closed form per group.

    In a group of width n with constant yearly probability q, survivors fall by (1-q)
    a year, and person-years are counted at mid-year. The script computes the same.
    """
    l, e_total, l65, py_from_65 = 1.0, 0.0, None, 0.0
    for g, (start, n) in enumerate(P.GROUPS):
        qq = q[g] / 100000.0
        p = 1.0 - qq
        pn = p ** n
        person_years = l * n if qq == 0 else l * (1 - qq / 2) * (1 - pn) / qq
        if start == 65:
            l65 = l
        if start >= 65:
            py_from_65 += person_years
        e_total += person_years
        l *= pn
    return {"e0": e_total, "e65": py_from_65 / l65 if l65 else 0.0, "q0_per_1000": q[0] / 100.0}


def means(inp):
    tier = 0.0
    for tech, value in P.MEANS_TIERS:
        if tech is None or tech in inp.techs:
            tier = max(tier, value)
    access = 0.3 + 0.7 * inp.literacy
    shift = sum(v for law, v in P.MEANS_LAW_SHIFT.items() if law in inp.laws)
    value = clamp(tier * access + shift, 0.0, P.MEANS_CAP)
    if inp.means_override is not None:   # a floor: France's early transition (§2.6)
        value = max(value, inp.means_override)
    return value


def fertility(inp, e0):
    """Children per woman and its terms (§2.3)."""
    wealth = inp.wealth_tfr if inp.wealth_tfr is not None else wealth_tfr(inp.sol)
    education = 1 - P.EDUCATION_WEIGHT * inp.literacy
    survival = 1 - P.SURVIVAL_WEIGHT * clamp((e0 - 30) / 50, 0.0, 1.0)
    urban = 1 - P.URBAN_WEIGHT * inp.urban_share
    desired = education * survival * urban
    mn = means(inp)
    factor = 1 - mn * (1 - desired)
    return {"tfr": wealth * factor, "wealth": wealth, "education": education,
            "survival": survival, "urban": urban, "means": mn, "factor": factor}


def asfr_shape(rate_age):
    """Share of a woman's lifetime births at this rate age, per 100k (15-49)."""
    if rate_age < 15 or rate_age > 49:
        return 0.0
    return P.ASFR_SHAPE_BY_GROUP[rate_age - rate_age % 5] / 5.0


def migrant_profile(inp):
    """Per (class, sex) share of a net migration, summing to 1 (§2.5)."""
    refugee = clamp(inp.crisis, 0.0, 1.0)
    rights = female_work_share(inp) / P.FULL_FEMALE_WORK_SHARE
    family = P.FAMILY_BASE + sum(v for t, v in P.FAMILY_TRANSPORT_TECHS.items() if t in inp.techs)
    family += P.FAMILY_RIGHTS_WEIGHT * rights + min(P.CHAIN_CAP, P.CHAIN_STEP * inp.inflow_years)
    family = clamp(family, 0.0, 1.0 - refugee)
    labour = max(0.0, 1.0 - family - refugee)
    labour_f = clamp(P.LABOUR_FEMALE_SHARE_MIN + inp.female_job_share * rights
                     * (P.LABOUR_FEMALE_SHARE_MAX - P.LABOUR_FEMALE_SHARE_MIN),
                     P.LABOUR_FEMALE_SHARE_MIN, P.LABOUR_FEMALE_SHARE_MAX)
    out = {}
    for c in range(len(P.MIGRANT_CLASSES)):
        lw = labour * P.MIGRANT_PROFILE["labour"]["weights"][c]
        fw = family * P.MIGRANT_PROFILE["family"]["weights"][c]
        rw = refugee * P.MIGRANT_PROFILE["refugee"]["weights"][c]
        out[(c, "f")] = lw * labour_f + (fw + rw) * 0.5
        out[(c, "m")] = lw * (1 - labour_f) + (fw + rw) * 0.5
    total = sum(out.values()) or 1.0
    return {k: v / total for k, v in out.items()}


def class_of(age):
    for c, (lo, hi) in enumerate(P.MIGRANT_CLASSES):
        if lo <= age <= hi:
            return c
    return len(P.MIGRANT_CLASSES) - 1


@dataclass
class Ring:
    f: list = field(default_factory=lambda: [0.0] * N)
    m: list = field(default_factory=lambda: [0.0] * N)
    pool_f: float = 0.0
    pool_m: float = 0.0
    pool_age: float = 150.0
    scale: float = 1.0                  # applied lazily at the next sweep
    year: int | None = None
    class_f: list = field(default_factory=lambda: [0.0] * len(P.MIGRANT_CLASSES))
    class_m: list = field(default_factory=lambda: [0.0] * len(P.MIGRANT_CLASSES))
    men_18_40: float = 0.0
    women_18_40: float = 0.0
    total: float = 0.0

    def age_of_slot(self, k):
        """Age of slot k's people after the step of self.year."""
        return (self.year - k) % N

    def people(self):
        return self.scale * (sum(self.f) + sum(self.m) + self.pool_f + self.pool_m)

    def by_age(self):
        """[(age, women, men)] for ages 0..149, scaled, then the pool as age 150."""
        rows = []
        for a in range(N):
            k = (self.year - a) % N
            rows.append((a, self.f[k] * self.scale, self.m[k] * self.scale))
        rows.append((150, self.pool_f * self.scale, self.pool_m * self.scale))
        return rows


def grouped_gini(groups):
    """Gini of [(people, income), ...] treating each group as equal inside (§4.1)."""
    groups = sorted((g for g in groups if g[0] > 0), key=lambda g: g[1] / g[0])
    people = sum(g[0] for g in groups)
    income = sum(g[1] for g in groups)
    if people <= 0 or income <= 0:
        return 0.0
    gini, below = 1.0, 0.0
    for n, y in groups:
        share = below + y / income
        gini -= n / people * (share + below)
        below = share
    return gini


def shown_gini(grouped):
    """The panel's Gini: an affine map of the grouped Gini (§4.1's anchors)."""
    return clamp(P.GINI_FLOOR + P.GINI_SCALE * grouped, 0.0, 0.9)


def growth_factor(nrr):
    """d = e^-r from the net reproduction rate, via r = ln(NRR) / T (T = 29 years).

    The script reads d from a generated table of this function (gen_demographics.py).
    """
    return nrr ** (-1.0 / 29.0)


def nrr(tfr, qf):
    """Daughters per woman: TFR x female share x survival to each childbearing age."""
    l, total = 1.0, 0.0
    for r in range(50):
        if r >= 15:
            total += l * asfr_shape(r) / 100000.0
        l *= 1 - qf[P.group_of(r)] / 100000.0
    return tfr * P.FEMALE_BIRTH_PER_100K / 100000.0 * total


def seed(inp, year, engine_pop):
    """A ring at the stable structure of the state's own rates (§2.6, rule 5)."""
    qf, qm, _mmr = group_rates(inp)
    e0 = life_table(qf)["e0"] * 0.5 + life_table(qm)["e0"] * 0.5
    tfr = fertility(inp, e0)["tfr"]
    d = growth_factor(nrr(tfr, qf))
    ring = Ring(year=year)
    lf = lm = 100000.0
    dpow = 1.0
    for a in range(N):
        k = (year - a) % N
        ring.f[k] = P.FEMALE_BIRTH_PER_100K / 100000.0 * lf * dpow
        ring.m[k] = P.MALE_BIRTH_PER_100K / 100000.0 * lm * dpow
        g = P.group_of(a)
        lf *= 1 - qf[g] / 100000.0
        lm *= 1 - qm[g] / 100000.0
        dpow *= d
    raw = sum(ring.f) + sum(ring.m)
    ring.scale = engine_pop / raw if raw > 0 else 1.0
    _refresh_denominators(ring)
    ring.total = engine_pop
    return ring


def _refresh_denominators(ring):
    ring.class_f = [0.0] * len(P.MIGRANT_CLASSES)
    ring.class_m = [0.0] * len(P.MIGRANT_CLASSES)
    ring.men_18_40 = ring.women_18_40 = 0.0
    for a, f, m in ring.by_age():
        c = class_of(a)
        ring.class_f[c] += f
        ring.class_m[c] += m
        if P.WAR_DEAD_AGES[0] <= a <= P.WAR_DEAD_AGES[1]:
            ring.men_18_40 += m
            ring.women_18_40 += f


def step(ring, inp, year, engine_pop=None, war_dead=0.0, kills=0.0, migration=0.0, rates=None):
    """One yearly step (§2.1), in the script's order. Returns the year's figures.

    engine_pop None = no scaling (a pure model run). war_dead, kills and migration are
    people this year (migration net, signed); the residual noise rule is the caller's.
    rates = (qf, qm, mmr, tfr, profile) replays an in-game step with the rates the game
    logged instead of recomputing them from inputs.
    """
    assert ring.year is not None and year == ring.year + 1, "one step per year"
    if rates is None:
        qf, qm, mmr = group_rates(inp)
        lt_f, lt_m = life_table(qf), life_table(qm)
        e0 = (lt_f["e0"] + lt_m["e0"]) / 2
        fert = fertility(inp, e0)
        tfr = fert["tfr"]
        prof = migrant_profile(inp)
    else:
        qf, qm, mmr, tfr, prof = rates
        lt_f, lt_m = life_table(qf), life_table(qm)
        e0 = (lt_f["e0"] + lt_m["e0"]) / 2
        fert = {"tfr": tfr}
    s = ring.scale
    war_m = clamp(war_dead * P.WAR_DEAD_MALE_SHARE / ring.men_18_40, 0, 0.5) if ring.men_18_40 else 0.0
    war_f = clamp(war_dead * (1 - P.WAR_DEAD_MALE_SHARE) / ring.women_18_40, 0, 0.5) if ring.women_18_40 else 0.0
    kill = clamp(kills / ring.total, 0, 0.9) if ring.total else 0.0
    births = deaths = 0.0
    open_k = year % N
    # ages 1..150 at this step; the slot at 150 is the open slot, folded then refilled
    for a in range(1, N + 1):
        k = (year - a) % N
        f, m = ring.f[k] * s, ring.m[k] * s
        if a == N:
            ring.pool_age = ((ring.pool_f + ring.pool_m) * s * (ring.pool_age + 1) + (f + m) * N) / max(
                (ring.pool_f + ring.pool_m) * s + f + m, 1e-9)
            ring.pool_f, ring.pool_m = ring.pool_f * s + f, ring.pool_m * s + m
            ring.f[k] = ring.m[k] = 0.0
            continue
        r = a - 1
        g = P.group_of(r)
        b = f * asfr_shape(r) / 100000.0 * tfr
        births += b
        f2 = f * (1 - qf[g] / 100000.0) - b * mmr / 100000.0
        m2 = m * (1 - qm[g] / 100000.0)
        deaths += (f - f2) + (m - m2)
        if P.WAR_DEAD_AGES[0] <= a <= P.WAR_DEAD_AGES[1]:
            f2 -= f2 * war_f
            m2 -= m2 * war_m
        f2 *= 1 - kill
        m2 *= 1 - kill
        c = class_of(a)
        if migration > 0:
            width = P.MIGRANT_CLASSES[c][1] - P.MIGRANT_CLASSES[c][0] + 1
            f2 += migration * prof[(c, "f")] / width
            m2 += migration * prof[(c, "m")] / width
        elif migration < 0:
            if ring.class_f[c]:
                f2 -= min(f2 * 0.5, -migration * prof[(c, "f")] * f / ring.class_f[c])
            if ring.class_m[c]:
                m2 -= min(m2 * 0.5, -migration * prof[(c, "m")] * m / ring.class_m[c])
        ring.f[k], ring.m[k] = max(f2, 0.0), max(m2, 0.0)
    # the pool: last group's rates, ages a year
    pq_f, pq_m = qf[-1] / 100000.0, qm[-1] / 100000.0
    deaths += ring.pool_f * pq_f + ring.pool_m * pq_m
    ring.pool_f *= 1 - pq_f
    ring.pool_m *= 1 - pq_m
    ring.f[open_k] = births * P.FEMALE_BIRTH_PER_100K / 100000.0
    ring.m[open_k] = births * P.MALE_BIRTH_PER_100K / 100000.0
    ring.year = year
    raw = sum(ring.f) + sum(ring.m) + ring.pool_f + ring.pool_m
    ring.scale = (engine_pop / raw) if (engine_pop is not None and raw > 0) else 1.0
    _refresh_denominators(ring)
    ring.total = ring.people()
    return {"births": births, "deaths": deaths, "tfr": tfr, "e0": e0, "e0_f": lt_f["e0"], "e0_m": lt_m["e0"],
            "e65": (lt_f["e65"] + lt_m["e65"]) / 2, "q0_per_1000": (qf[0] + qm[0]) / 200.0,
            "fertility": fert, "raw": raw}


def structure(ring):
    """Shares 0-14, 15-64, 65+, median age, men per 100 women (20-59)."""
    rows = ring.by_age()
    tot = sum(f + m for _a, f, m in rows) or 1.0
    young = sum(f + m for a, f, m in rows if a <= 14) / tot
    old = sum(f + m for a, f, m in rows if a >= 65) / tot
    half, run, median = tot / 2, 0.0, 0.0
    for a, f, m in rows:
        if run + f + m >= half:
            median = a + (half - run) / max(f + m, 1e-9)
            break
        run += f + m
    w = sum(f for a, f, _m in rows if 20 <= a <= 59) or 1.0
    men = sum(m for a, _f, m in rows if 20 <= a <= 59)
    return {"young": young, "working": 1 - young - old, "old": old, "median": median,
            "men_per_100_women": 100 * men / w}


def run_constant(inp, years=400, year0=1836):
    """Seed, then step with fixed inputs and no engine scaling; return the last step."""
    ring = seed(inp, year0, 1_000_000)
    ring.scale = 1.0
    raw = sum(ring.f) + sum(ring.m)
    ring.f = [x * 1_000_000 / raw for x in ring.f]
    ring.m = [x * 1_000_000 / raw for x in ring.m]
    _refresh_denominators(ring)
    ring.total = ring.people()
    last, prev = None, ring.people()
    for y in range(year0 + 1, year0 + years + 1):
        last = step(ring, inp, y)
        cur = ring.people()
        last["growth"] = cur / prev - 1
        prev = cur
    return ring, last
```

- [ ] **Step 5: Run the tests**

Run: `python3 -m unittest test_demographics_model -v && ruff check scripts/analysis/demographics_*.py test_demographics_model.py`
Expected: 23 tests OK in about a second; ruff clean.

- [ ] **Step 6: Commit**

```bash
git add scripts/analysis/demographics_params.py scripts/analysis/demographics_model.py test_demographics_model.py
git commit -m "Demographics model: birth cohorts, five causes of death, fertility terms, migrant profiles"
```

### Task 3: Read the harness's inputs from a plain-text save

`save_country_probe.py` reads binary saves but not pops. A plain-text save (the game writes these in debug mode) holds
every pop's size, SoL, literacy, wealth and social class, and each country's laws and technology. The layout below was
checked on the owner's 1836 save before this plan was written (`great britain_temptst.v3`, 197 MB, read in about 6 s).

**Files:**
- Create: `scripts/analysis/demographics_save_inputs.py`
- Create: `test_fixtures/demographics/gb_1836_slice.v3` (written by the reader's `slice` command, Step 4)
- Create: `test_demographics_save_inputs.py`

**Interfaces:**
- Produces: `read_sections(path, wanted) -> {section: {id: {field: str}}}`, `country_inputs(sections) ->
  {tag: CountryInputs}` (`population`, `sol`, `literacy` (literate ÷ workforce), `urban_share`, `strata_people`,
  `strata_wealth`, `sol_bins`, `laws`, `techs`, `states`), `STRATA_OF_CLASS`, `_num(raw, default)`,
  `write_slice(sections, tags, max_pops, out_path)`, `main(argv)` with `summary` and `slice`.

- [ ] **Step 1: Write the failing test** — `test_demographics_save_inputs.py`:

```python
"""scripts/analysis/demographics_save_inputs.py reads pops, owners, laws and technology."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_save_inputs as S  # noqa: E402

SLICE = ROOT / "test_fixtures" / "demographics" / "gb_1836_slice.v3"

TINY = """SAV0100tiny
meta_data={
\tversion="1.14.5"
}
pops={
\tdatabase={
7={
\ttype=aristocrats
\tworkforce=100
\tdependents=300
\tlocation=1
\tnum_literate=50
\twealth=30
\tprevious_quality_of_life=28
\tweekly_budget={ 0 0 1 }
\tfood_security={
\t\ttype=not_a_pop_type
\t}
\tsocial_class={
\t\tsocial_class=upper_class
\t}
}
8={
\ttype=peasants
\tlocation=1
\twealth=5
}
\t}
}
country_manager={
\tdatabase={
3={
\tdefinition="TST"
\tbudget={
\t\tweekly_expenses={ 0 0 }
\t}
}
\t}
}
states={
\tdatabase={
1={
\tcountry=3
}
\t}
}
laws={
\tdatabase={
0={
\tlaw=law_serfdom
\tcountry=3
\tactive=yes
}
1={
\tlaw=law_homesteading
\tcountry=3
}
\t}
}
technology={
\tdatabase={
0={
\tcountry=3
\tacquired_technologies={ enclosure railways }
}
\t}
}
"""


class TestTinySave(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile("w", suffix=".v3", delete=False, encoding="utf-8")
        self.tmp.write(TINY)
        self.tmp.close()
        self.sections = S.read_sections(self.tmp.name)

    def tearDown(self):
        Path(self.tmp.name).unlink()

    def test_fields_one_tab_in_only(self):
        pop = self.sections["pops"]["7"]
        self.assertEqual(pop["type"], "aristocrats")
        self.assertEqual(pop["social_class"], "upper_class")

    def test_country_inputs(self):
        c = S.country_inputs(self.sections)["TST"]
        self.assertEqual(c.population, 400)
        self.assertAlmostEqual(c.sol, 28)
        self.assertAlmostEqual(c.literacy, 0.5)
        self.assertEqual(c.laws, {"law_serfdom"})
        self.assertEqual(c.techs, {"enclosure", "railways"})
        self.assertEqual(dict(c.strata_people), {"upper": 400})

    def test_empty_pop_is_skipped(self):
        c = S.country_inputs(self.sections)["TST"]
        self.assertEqual(c.rural, 0)


@unittest.skipUnless(SLICE.exists(), "fixture written in Task 3 Step 4")
class TestSlice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = S.country_inputs(S.read_sections(SLICE))

    def test_britain_and_portugal(self):
        self.assertEqual(set(self.inputs), {"GBR", "POR"})
        gbr = self.inputs["GBR"]
        self.assertEqual(gbr.states, 26)
        self.assertGreater(gbr.population, 1_000_000)
        self.assertTrue({"law_women_own_property", "law_tenant_farmers", "law_charitable_health_system"} <= gbr.laws)
        self.assertIn("law_no_womens_rights", self.inputs["POR"].laws)
        self.assertIn("enclosure", gbr.techs)
        self.assertLessEqual(set(gbr.strata_people), {"lower", "middle", "upper"})
        self.assertTrue(0 < gbr.literacy < 1 and 0 < gbr.urban_share < 1)
```

- [ ] **Step 2: Run it to see it fail**

Run: `python3 -m unittest test_demographics_save_inputs -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'demographics_save_inputs'`.

- [ ] **Step 3: Write the reader** — `scripts/analysis/demographics_save_inputs.py`:

```python
#!/usr/bin/env python3
"""Read what the demographics harness needs from a plain-text Victoria 3 save.

Usage:
    demographics_save_inputs.py summary SAVE [--tag GBR ...]
    demographics_save_inputs.py slice SAVE --tag GBR [--tag POR] [--max-pops 300] -o OUT

A plain-text save is what the game writes in debug mode (it starts `SAV0…` and then
`meta_data={`). Binary saves aren't read here; `save_country_probe.py` covers those for
variables and laws but not pops. Spec: docs/superpowers/specs/2026-10-08-demographics-design.md
§11.1 (the harness is driven by SoL, literacy, technology and law read from saves).

Layout, as written by 1.14.5 (checked on an 1836 save, 2026-10-08): top-level sections
`pops={ database={ <id>={ … } … } }`, `states=`, `country_manager=`, `laws=`, `technology=`,
each record's own fields one tab in. The fields read:
    pops             type, location (state id), workforce, dependents, num_literate, wealth,
                     previous_quality_of_life (the pop's standard of living last week)
    states           country (owner id)
    country_manager  definition (the tag, quoted)
    laws             law, country, active (yes on the law in force)
    technology       country, acquired_technologies={ … }
A pop with no workforce or dependents field is empty (size 0).
"""

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

SECTIONS = {
    "pops": ("type", "location", "workforce", "dependents", "num_literate", "wealth", "previous_quality_of_life",
             "social_class"),
    "states": ("country",),
    "country_manager": ("definition",),
    "laws": ("law", "country", "active"),
    "technology": ("country", "acquired_technologies"),
}
_FIELD = re.compile(r"^\t([a-z_]+)=(.*)$")
_SOCIAL_CLASS = re.compile(r"^\t\tsocial_class=([a-z_]+)$")
# social class -> strata, from game/common/social_classes/*.txt (1.14.5). Not in the
# vanilla_parsed/ snapshot; an unknown class counts as lower.
STRATA_OF_CLASS = {
    "upper_class": "upper", "middle_class": "middle", "lower_class": "lower",
    "brahmins": "upper", "kshatriyas": "middle", "vaishyas": "middle", "shudras": "lower", "dalit": "lower",
    "strata_samurai_high": "upper", "strata_samurai_low": "middle", "strata_religious": "middle",
    "strata_commoners_peasants": "lower", "strata_commoners_townspeople": "lower", "strata_outcastes": "lower",
}
_RECORD = re.compile(r"^(\d+)=\{\s*$")


def read_sections(path, wanted=tuple(SECTIONS)):
    """{section: {record_id: {field: raw string}}} for the wanted sections."""
    out = {name: {} for name in wanted}
    section = None
    depth = 0
    record_id = None
    record = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if section is None:
                if depth == 0 and line.endswith("={\n") and not line.startswith("\t"):
                    name = line[:-3]
                    if name in out:
                        section, depth = name, 1
                        continue
                depth += line.count("{") - line.count("}")
                continue
            opened, closed = line.count("{"), line.count("}")
            if record is None:
                m = _RECORD.match(line)
                if m and depth == 2:
                    record_id, record = m.group(1), {}
                    depth += 1
                    continue
                depth += opened - closed
                if depth == 0:
                    section = None
                continue
            if depth == 3:
                m = _FIELD.match(line.rstrip("\n"))
                if m and m.group(1) in SECTIONS[section]:
                    record[m.group(1)] = m.group(2).strip()
            elif depth == 4 and section == "pops":
                m = _SOCIAL_CLASS.match(line.rstrip("\n"))
                if m:
                    record["social_class"] = m.group(1)
            depth += opened - closed
            if depth == 2:
                out[section][record_id] = record
                record = None
    return out


def _num(raw, default=0.0):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


@dataclass
class CountryInputs:
    tag: str
    population: float = 0.0
    sol_x_size: float = 0.0
    literate: float = 0.0
    workforce: float = 0.0
    wealth_x_size: float = 0.0
    rural: float = 0.0
    strata_people: dict = field(default_factory=lambda: defaultdict(float))
    strata_wealth: dict = field(default_factory=lambda: defaultdict(float))
    sol_bins: dict = field(default_factory=lambda: defaultdict(float))
    laws: set = field(default_factory=set)
    techs: set = field(default_factory=set)
    states: int = 0

    @property
    def sol(self):
        return self.sol_x_size / self.population if self.population else 0.0

    @property
    def literacy(self):
        return self.literate / self.workforce if self.workforce else 0.0

    @property
    def urban_share(self):
        return 1 - self.rural / self.population if self.population else 0.0


RURAL_TYPES = {"peasants", "farmers", "slaves"}


def country_inputs(sections):
    """{tag: CountryInputs} from read_sections()'s output."""
    tags = {cid: rec.get("definition", "").strip('"') for cid, rec in sections["country_manager"].items()}
    owner_of_state = {sid: rec.get("country") for sid, rec in sections["states"].items()}
    out = {}

    def get(cid):
        tag = tags.get(cid)
        if not tag:
            return None
        if tag not in out:
            out[tag] = CountryInputs(tag)
        return out[tag]

    for sid, cid in owner_of_state.items():
        c = get(cid)
        if c:
            c.states += 1
    for rec in sections["pops"].values():
        size = _num(rec.get("workforce")) + _num(rec.get("dependents"))
        if size <= 0:
            continue
        c = get(owner_of_state.get(rec.get("location")))
        if not c:
            continue
        sol = _num(rec.get("previous_quality_of_life"))
        wealth = _num(rec.get("wealth"))
        c.population += size
        c.sol_x_size += sol * size
        c.literate += _num(rec.get("num_literate"))
        c.workforce += _num(rec.get("workforce"))
        c.wealth_x_size += wealth * size
        if rec.get("type") in RURAL_TYPES:
            c.rural += size
        s = STRATA_OF_CLASS.get(rec.get("social_class"), "lower")
        c.strata_people[s] += size
        c.strata_wealth[s] += wealth * size
        c.sol_bins[min(int(sol // 5) * 5, 40)] += size
    for rec in sections["laws"].values():
        if rec.get("active") == "yes":
            c = get(rec.get("country"))
            if c:
                c.laws.add(rec.get("law"))
    for rec in sections["technology"].values():
        c = get(rec.get("country"))
        if c:
            c.techs.update(rec.get("acquired_technologies", "").strip("{} ").split())
    return out


def write_slice(sections, tags, max_pops, out_path):
    """A small save holding only the read fields of the named countries' first pops."""
    ids = {cid for cid, rec in sections["country_manager"].items() if rec.get("definition", "").strip('"') in tags}
    states = {sid for sid, rec in sections["states"].items() if rec.get("country") in ids}
    keep = {
        "country_manager": {cid: rec for cid, rec in sections["country_manager"].items() if cid in ids},
        "states": {sid: rec for sid, rec in sections["states"].items() if sid in states},
        "laws": {i: r for i, r in sections["laws"].items() if r.get("country") in ids and r.get("active") == "yes"},
        "technology": {i: r for i, r in sections["technology"].items() if r.get("country") in ids},
        "pops": {},
    }
    candidates = [(pid, rec) for pid, rec in sections["pops"].items()
                  if rec.get("location") in states and rec.get("workforce")]
    stride = max(1, len(candidates) // max_pops)
    keep["pops"] = dict(candidates[::stride][:max_pops])
    lines = ["SAV0100demographics-test-slice", "meta_data={", '\tversion="1.14.5"', "}"]
    for name in ("pops", "country_manager", "states", "laws", "technology"):
        lines += [f"{name}={{", "\tdatabase={"]
        for rid, rec in keep[name].items():
            lines.append(f"{rid}={{")
            lines += [f"\t{k}={v}" for k, v in rec.items()]
            lines.append("}")
        lines += ["\t}", "}"]
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {k: len(v) for k, v in keep.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summary")
    s.add_argument("save")
    s.add_argument("--tag", action="append", default=[])
    sl = sub.add_parser("slice")
    sl.add_argument("save")
    sl.add_argument("--tag", action="append", required=True)
    sl.add_argument("--max-pops", type=int, default=300)
    sl.add_argument("-o", "--out", required=True)
    args = ap.parse_args(argv)
    sections = read_sections(args.save)
    if args.cmd == "slice":
        print(write_slice(sections, set(args.tag), args.max_pops, args.out))
        return 0
    inputs = country_inputs(sections)
    for tag in (args.tag or sorted(inputs, key=lambda t: -inputs[t].population)[:15]):
        c = inputs.get(tag)
        if c:
            print(f"{tag} pop={c.population:,.0f} states={c.states} sol={c.sol:.1f} literacy={c.literacy:.2f} "
                  f"urban={c.urban_share:.2f} laws={len(c.laws)} techs={len(c.techs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Write the fixture.** From the owner's plain-text 1836 save (any debug-mode save from 1836 works if
  this one has gone):

```bash
python3 scripts/analysis/demographics_save_inputs.py slice \
  "/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/save games/great britain_temptst.v3" \
  --tag GBR --tag POR --max-pops 300 -o test_fixtures/demographics/gb_1836_slice.v3
```

  Expected: `{'country_manager': 2, 'states': 45, 'laws': 118, 'technology': 2, 'pops': 300}` and a file of about
  56 KB. Then `python3 scripts/analysis/demographics_save_inputs.py summary test_fixtures/demographics/gb_1836_slice.v3`
  prints a GBR line (26 states, about 7.1 million people in the slice) and a POR line.

- [ ] **Step 5: Run the tests**

Run: `python3 -m unittest test_demographics_save_inputs -v && ruff check scripts/analysis/demographics_save_inputs.py test_demographics_save_inputs.py`
Expected: 4 tests OK (none skipped); ruff clean.

- [ ] **Step 6: Commit**

```bash
git add scripts/analysis/demographics_save_inputs.py test_demographics_save_inputs.py test_fixtures/demographics/gb_1836_slice.v3
git commit -m "Demographics harness: read pops, owners, laws and technology from a plain-text save"
```

### Task 4: The harness CLI, its first results and the replay format

The harness gives phase 0 its checks today: §2.2/§2.3's sketch, Britain 1836's Gini anchor (which sets `GINI_SCALE`),
a seeded country from a save, §14 Q10's world natural-change check from two saves a month apart, and `replay`, which
runs an in-game step logged by Task 15's debug option against the model. The replay log format is defined here, in
`format_replay`, and Task 15's script writes exactly these lines.

**Files:**
- Create: `scripts/analysis/demographics_harness.py`, `test_demographics_harness.py`
- Create: `docs/testing/demographics-harness-2026-10-08.md`
- Modify: `docs/guides/python_tools.md` (a row in the analysis-scripts table; find it with
  `grep -n "save_country_probe" docs/guides/python_tools.md`)

**Interfaces:**
- Consumes: Task 1 (`pop_growth.read_defines`, `monthly_birthrate`, `monthly_mortality`), Task 2 (the whole model,
  `rates_from_multipliers`, `work_split`, `grouped_gini`, `shown_gini`), Task 3 (`read_sections`, `country_inputs`,
  `STRATA_OF_CLASS`, `_num`).
- Produces: `buy_package_costs(path) -> {wealth: cost}`, `income_proxy(wealth, costs)`, `format_replay(state, year,
  ring_before, head, ring_after) -> [str]`, `parse_replay(lines)`, `replay_block(block) -> float`, `main(argv)`.

The model's Task 2 file already holds `rates_from_multipliers`, `work_split`, `grouped_gini` and `shown_gini` (they
are in the code block above), and `demographics_params.py` holds `INCOME_WEALTH_CAP = 60`, `GINI_FLOOR = 0.30` and
`GINI_SCALE = 0.85`, computed from the 1836 save before this plan was written. This task re-runs that computation.

- [ ] **Step 1: Write the failing test** — `test_demographics_harness.py`:

```python
"""scripts/analysis/demographics_harness.py: the sketch, the Gini anchor and the replay round trip."""

import copy
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_harness as H  # noqa: E402
import demographics_model as M  # noqa: E402

SLICE = ROOT / "test_fixtures" / "demographics" / "gb_1836_slice.v3"


class TestHarness(unittest.TestCase):
    def test_sketch_runs(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["sketch"]), 0)
        self.assertIn("Britain 1836", out.getvalue())

    def test_buy_package_costs_rise_with_wealth(self):
        costs = H.buy_package_costs()
        self.assertEqual(len(costs), 200)
        self.assertLess(costs[1], costs[20])
        self.assertEqual(H.income_proxy(150, costs), costs[60])

    def test_replay_round_trip(self):
        inp = M.Inputs(sol=11, literacy=0.35, urban_share=0.3)
        before = M.seed(inp, 1836, 2_000_000)
        after = copy.deepcopy(before)
        qf, qm, mmr = M.group_rates(inp)
        mult = M.cause_multipliers(inp)
        work_f, work_m = M.work_split(inp, mult["work"])
        tfr = M.fertility(inp, 40)["tfr"]
        prof = M.migrant_profile(inp)
        M.step(after, inp, 1837, engine_pop=2_010_000, war_dead=500, migration=-3000,
               rates=(qf, qm, mmr, tfr, prof))
        head = {"pop": 2_010_000, "war": 500, "kills": 0, "mig": -3000, "tfr": tfr, "mmr": mmr,
                "m_inf": mult["infection"], "m_ext": mult["external"], "m_chr": mult["chronic"],
                "m_work_f": work_f, "m_work_m": work_m, "profile": prof}
        lines = H.format_replay("TEST", 1837, before, head, after)
        self.assertEqual(len(lines), 31)
        self.assertIn("pop=2_10_0", lines[0])
        blocks = H.parse_replay(lines)
        self.assertEqual(len(blocks), 1)
        self.assertLess(H.replay_block(blocks[0]), 0.001)

    def test_replay_catches_a_wrong_step(self):
        inp = M.Inputs()
        before = M.seed(inp, 1836, 1_000_000)
        after = copy.deepcopy(before)
        M.step(after, inp, 1837, engine_pop=1_000_000)
        after.f[(1837 - 30) % 150] *= 1.5   # the script got one cohort wrong
        qf, qm, mmr = M.group_rates(inp)
        mult = M.cause_multipliers(inp)
        work_f, work_m = M.work_split(inp, mult["work"])
        head = {"pop": 1_000_000, "war": 0, "kills": 0, "mig": 0, "tfr": M.fertility(inp, 40)["tfr"],
                "mmr": mmr, "m_inf": mult["infection"], "m_ext": mult["external"], "m_chr": mult["chronic"],
                "m_work_f": work_f, "m_work_m": work_m, "profile": M.migrant_profile(inp)}
        blocks = H.parse_replay(H.format_replay("TEST", 1837, before, head, after))
        self.assertGreater(H.replay_block(blocks[0]), 0.2)

    def test_grouped_numbers(self):
        self.assertEqual(H._grouped(2_803_898), "2_803_898")
        self.assertEqual(H._ungroup("0_490_84"), 490_084)
        self.assertEqual(H._ungroup("-0_3_0"), -3000)

    @unittest.skipUnless(SLICE.exists(), "fixture written in Task 3")
    def test_gini_on_the_slice(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["gini", str(SLICE), "--tag", "GBR"]), 0)
        self.assertIn("GBR grouped", out.getvalue())
```

- [ ] **Step 2: Run it to see it fail**

Run: `python3 -m unittest test_demographics_harness -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'demographics_harness'`.

- [ ] **Step 3: Write the harness** — `scripts/analysis/demographics_harness.py`:

```python
#!/usr/bin/env python3
"""Offline harness for the demographics model (spec §11.1, §12 phase 0).

Usage:
    demographics_harness.py sketch                      # §2.2/§2.3's cases from the model
    demographics_harness.py inputs SAVE [--tag GBR]     # per-country inputs read from a save
    demographics_harness.py gini SAVE [--anchor-tag GBR --anchor 0.52]
    demographics_harness.py seed SAVE --tag GBR         # the seeded structure and life figures
    demographics_harness.py natural-change OLD NEW      # §14 Q10: world change vs the SoL curves
    demographics_harness.py replay DEBUG_LOG            # an in-game step against the model

SAVE is a plain-text save (debug mode). The model is demographics_model.py with
demographics_params.py; the generator writes the script from the same two files, so a
parameter tuned here reaches the game by `python3 scripts/generators/gen_demographics.py`.

Calibration to world history (§2.3's targets) is not here yet: it needs an observer
run's yearly saves and belongs to phase 2's plan.
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_save_inputs as S  # noqa: E402
import pop_growth as G  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BUY_PACKAGES = ROOT / "common" / "buy_packages" / "00_buy_packages.txt"

SKETCH = {
    "1836 agrarian (reference)": M.Inputs(sol=8, literacy=0.2, urban_share=0.1),
    "Britain 1836": M.Inputs(sol=11, literacy=0.35, urban_share=0.3, laws=frozenset({"law_no_womens_rights"})),
    "France 1836 (means 0.8)": M.Inputs(sol=11, literacy=0.3, urban_share=0.15, means_override=0.8),
}


def buy_package_costs(path=BUY_PACKAGES):
    """{wealth: weekly spending per 10,000 working adults} from the committed buy packages."""
    text = Path(path).read_text(encoding="utf-8-sig")
    out = {}
    for m in re.finditer(r"^wealth_(\d+) = \{(.*?)^\}", text, re.S | re.M):
        goods = re.search(r"goods = \{[^\n]*\n(.*?)\n\t\}", m.group(2), re.S)
        out[int(m.group(1))] = sum(float(v) for v in re.findall(r"= ([0-9.]+)", goods.group(1)))
    return out


def income_proxy(wealth, costs):
    w = min(max(int(wealth), 1), P.INCOME_WEALTH_CAP)
    return costs[w]


def inputs_for(c):
    """Model inputs for a save's country (no institutions: the reader doesn't read them)."""
    return M.Inputs(sol=c.sol, literacy=c.literacy, urban_share=c.urban_share,
                    techs=frozenset(c.techs), laws=frozenset(c.laws))


def cmd_sketch(_args):
    for label, inp in SKETCH.items():
        ring, last = M.run_constant(inp, years=300)
        s = M.structure(ring)
        print(f"{label:28s} TFR {last['tfr']:.2f}  e0 {last['e0']:.1f}  e65 {last['e65']:.1f}  "
              f"IMR {last['q0_per_1000']:.0f}  0-14 {s['young']:.0%}  15-64 {s['working']:.0%}  "
              f"65+ {s['old']:.1%}  growth {last['growth']:+.2%}")
    return 0


def country_groups(sections, tag, costs):
    """[(people, income)] by strata for one country, from raw pop records."""
    tags = {cid: r.get("definition", "").strip('"') for cid, r in sections["country_manager"].items()}
    owner = {sid: r.get("country") for sid, r in sections["states"].items()}
    acc = {}
    for r in sections["pops"].values():
        if tags.get(owner.get(r.get("location"))) != tag:
            continue
        size = S._num(r.get("workforce")) + S._num(r.get("dependents"))
        if size <= 0:
            continue
        strata = S.STRATA_OF_CLASS.get(r.get("social_class"), "lower")
        n, y = acc.get(strata, (0.0, 0.0))
        acc[strata] = (n + size, y + size * income_proxy(S._num(r.get("wealth"), 1), costs))
    return list(acc.values())


def cmd_gini(args):
    sections = S.read_sections(args.save)
    costs = buy_package_costs()
    inputs = S.country_inputs(sections)
    tags = args.tag or sorted(inputs, key=lambda t: -inputs[t].population)[:15]
    grouped = {t: M.grouped_gini(country_groups(sections, t, costs)) for t in set(tags) | {args.anchor_tag}}
    anchor = grouped[args.anchor_tag]
    scale = (args.anchor - P.GINI_FLOOR) / anchor if anchor else 0.0
    print(f"GINI_SCALE for {args.anchor_tag} = {args.anchor}: {scale:.2f} (params: {P.GINI_SCALE})")
    for t in tags:
        shown = M.clamp(P.GINI_FLOOR + scale * grouped[t], 0, 0.9)
        print(f"{t} grouped {grouped[t]:.3f} shown {shown:.2f}")
    return 0


def cmd_inputs(args):
    return S.main(["summary", args.save] + [x for t in args.tag for x in ("--tag", t)])


def cmd_seed(args):
    c = S.country_inputs(S.read_sections(args.save)).get(args.tag)
    if c is None:
        print(f"no country {args.tag}", file=sys.stderr)
        return 1
    inp = inputs_for(c)
    ring = M.seed(inp, 1836, c.population)
    qf, qm, _ = M.group_rates(inp)
    f, m = M.life_table(qf), M.life_table(qm)
    fert = M.fertility(inp, (f["e0"] + m["e0"]) / 2)
    s = M.structure(ring)
    print(f"{args.tag}: pop {c.population:,.0f} SoL {c.sol:.1f} literacy {c.literacy:.2f} urban {c.urban_share:.2f}")
    print(f"  TFR {fert['tfr']:.2f} (wealth {fert['wealth']:.2f} x factor {fert['factor']:.2f}; means {fert['means']:.2f})")
    print(f"  e0 women {f['e0']:.1f} men {m['e0']:.1f}; IMR {(qf[0] + qm[0]) / 200:.0f} per 1000")
    print(f"  0-14 {s['young']:.0%} 15-64 {s['working']:.0%} 65+ {s['old']:.1%} median {s['median']:.1f}")
    return 0


def cmd_natural_change(args):
    """World population change between two saves against the defines' curves (no modifiers)."""
    d = G.read_defines()
    old, new = S.read_sections(args.old, ("pops",)), S.read_sections(args.new, ("pops",))
    total_old = total_new = expected = 0.0
    for r in old["pops"].values():
        size = S._num(r.get("workforce")) + S._num(r.get("dependents"))
        sol = S._num(r.get("previous_quality_of_life"))
        total_old += size
        expected += size * (G.monthly_birthrate(sol, d) - G.monthly_mortality(sol, d))
    for r in new["pops"].values():
        total_new += S._num(r.get("workforce")) + S._num(r.get("dependents"))
    months = args.months
    print(f"world {total_old:,.0f} -> {total_new:,.0f}: change {total_new - total_old:+,.0f} over {months} month(s)")
    print(f"expected from the curves without modifiers: {expected * months:+,.0f} "
          f"(ratio {((total_new - total_old) / (expected * months)) if expected else 0:.2f})")
    return 0


_REPLAY = re.compile(r"TE_DEMOG_REPLAY (\w+) (.*)$")
HEAD_PEOPLE = ("pop_last", "pop", "war", "kills", "mig")
HEAD_RATES = ("tfr", "mmr", "m_inf", "m_ext", "m_chr", "m_work_f", "m_work_m")


def _fmt(x):
    return f"{x:.5f}".rstrip("0").rstrip(".") if x else "0"


def _grouped(x):
    """millions_thousands_units, as the debug log prints a large number (the probe's form)."""
    sign = "-" if x < 0 else ""
    n = int(round(abs(x)))
    return f"{sign}{n // 1_000_000}_{n // 1000 % 1000}_{n % 1000}"


def _ungroup(text):
    sign = -1 if text.startswith("-") else 1
    parts = [int(p or 0) for p in text.lstrip("-").split("_")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return sign * (parts[0] * 1_000_000 + parts[1] * 1000 + parts[2])


def _per_mille(ring):
    total = ring.people() or 1.0
    k = 1000.0 * ring.scale / total
    return [x * k for x in ring.f], [x * k for x in ring.m], (ring.pool_f * k, ring.pool_m * k)


def format_replay(state, year, ring_before, head, ring_after):
    """The TE_DEMOG_REPLAY lines one in-game step logs (te_debug_demog.1 option a).

    The debug log abbreviates numbers of 1,000 and more, so people counts print as
    millions_thousands_units groups and every slot as per mille of the state's people.
    head: pop (engine, now), war, kills, mig (signed), tfr, mmr, m_inf, m_ext, m_chr,
    m_work_f, m_work_m, profile (10 shares: classes 0-4 women, then men). pop_last is the
    ring's people before the step. Then fifteen `before` and fifteen `after` lines of ten
    slots each; the slot-0 line also carries the pool and its mean age.
    """
    n = len(P.MIGRANT_CLASSES)
    h = dict(head, pop_last=ring_before.people())
    prof = ",".join(_fmt(head["profile"][(c, s)]) for s in ("f", "m") for c in range(n))
    lines = [f"TE_DEMOG_REPLAY head state={state} year={year} "
             + " ".join(f"{k}={_grouped(h[k])}" for k in HEAD_PEOPLE) + " "
             + " ".join(f"{k}={_fmt(h[k])}" for k in HEAD_RATES) + f" profile={prof}"]
    for when, ring in (("before", ring_before), ("after", ring_after)):
        f, m, (pf, pm) = _per_mille(ring)
        for first in range(0, P.RING_YEARS, 10):
            extra = f" pool_f={_fmt(pf)} pool_m={_fmt(pm)} pool_age={_fmt(ring.pool_age)}" if first == 0 else ""
            lines.append(f"TE_DEMOG_REPLAY {when} from={first} f={','.join(_fmt(x) for x in f[first:first + 10])}"
                         f" m={','.join(_fmt(x) for x in m[first:first + 10])}{extra}")
    return lines


def parse_replay(lines):
    """[{'head': {...}, 'before': {...}, 'after': {...}}] from TE_DEMOG_REPLAY lines."""
    blocks, cur = [], None
    for line in lines:
        hit = _REPLAY.search(line)
        if not hit:
            continue
        kind, rest = hit.group(1), hit.group(2)
        fields = dict(kv.split("=", 1) for kv in rest.split() if "=" in kv)
        if kind == "head":
            cur = {"head": fields, "before": {"f": {}, "m": {}}, "after": {"f": {}, "m": {}}}
            blocks.append(cur)
        elif cur is not None and kind in ("before", "after"):
            first = int(fields["from"])
            for sex in ("f", "m"):
                for i, v in enumerate(fields[sex].split(",")):
                    cur[kind][sex][first + i] = float(v or 0)
            if "pool_f" in fields:
                cur[kind]["pool"] = (float(fields["pool_f"] or 0), float(fields["pool_m"] or 0),
                                     float(fields["pool_age"] or 150))
    return blocks


def replay_block(b):
    """Step the model from a logged before-state; the worst relative error over slots above 0.05 per mille."""
    h = b["head"]
    year = int(h["year"])
    pop_last = _ungroup(h["pop_last"])
    ring = M.Ring(year=year - 1)
    for k in range(P.RING_YEARS):
        ring.f[k] = b["before"]["f"].get(k, 0.0) * pop_last / 1000.0
        ring.m[k] = b["before"]["m"].get(k, 0.0) * pop_last / 1000.0
    pf, pm, page = b["before"].get("pool", (0.0, 0.0, 150.0))
    ring.pool_f, ring.pool_m, ring.pool_age = pf * pop_last / 1000.0, pm * pop_last / 1000.0, page
    M._refresh_denominators(ring)
    ring.total = ring.people()
    mult = {"infection": float(h["m_inf"]), "external": float(h["m_ext"]), "chronic": float(h["m_chr"])}
    qf, qm = M.rates_from_multipliers(mult, float(h["m_work_f"]), float(h["m_work_m"]))
    shares = [float(x) for x in h["profile"].split(",")]
    n = len(P.MIGRANT_CLASSES)
    prof = {(c, "f"): shares[c] for c in range(n)} | {(c, "m"): shares[n + c] for c in range(n)}
    M.step(ring, M.Inputs(), year, engine_pop=_ungroup(h["pop"]), war_dead=_ungroup(h["war"]),
           kills=_ungroup(h["kills"]), migration=_ungroup(h["mig"]),
           rates=(qf, qm, float(h["mmr"]), float(h["tfr"]), prof))
    mine_f, mine_m, _pool = _per_mille(ring)
    worst = 0.0
    for sex, mine in (("f", mine_f), ("m", mine_m)):
        for k, logged in b["after"][sex].items():
            if max(mine[k], logged) > 0.05:
                worst = max(worst, abs(mine[k] - logged) / max(mine[k], logged))
    return worst


def cmd_replay(args):
    lines = Path(args.log).read_text(encoding="utf-8", errors="replace").splitlines()
    blocks = parse_replay(lines)
    if not blocks:
        print("no TE_DEMOG_REPLAY blocks", file=sys.stderr)
        return 1
    bad = 0
    for b in blocks:
        worst = replay_block(b)
        flag = "OK" if worst <= args.tolerance else "MISMATCH"
        bad += flag != "OK"
        print(f"{b['head'].get('state', '?')} {b['head']['year']}: worst slot error {worst:.2%} {flag}")
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sketch").set_defaults(fn=cmd_sketch)
    p = sub.add_parser("inputs")
    p.add_argument("save")
    p.add_argument("--tag", action="append", default=[])
    p.set_defaults(fn=cmd_inputs)
    p = sub.add_parser("gini")
    p.add_argument("save")
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--anchor-tag", default="GBR")
    p.add_argument("--anchor", type=float, default=0.52)
    p.set_defaults(fn=cmd_gini)
    p = sub.add_parser("seed")
    p.add_argument("save")
    p.add_argument("--tag", required=True)
    p.set_defaults(fn=cmd_seed)
    p = sub.add_parser("natural-change")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--months", type=int, default=1)
    p.set_defaults(fn=cmd_natural_change)
    p = sub.add_parser("replay")
    p.add_argument("log")
    p.add_argument("--tolerance", type=float, default=0.01)
    p.set_defaults(fn=cmd_replay)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest test_demographics_harness test_demographics_model test_demographics_save_inputs test_pop_growth -v && ruff check scripts/analysis/ test_demographics_*.py test_pop_growth.py`
Expected: all OK, none skipped; ruff clean.

- [ ] **Step 5: Run it on the 1836 save and record the results.** Run each and paste the output into
  `docs/testing/demographics-harness-2026-10-08.md` under a heading per command, with one paragraph saying what each
  number checks against (§2.2, §2.3, §4.1):

```bash
S="/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/save games/great britain_temptst.v3"
python3 scripts/analysis/demographics_harness.py sketch
python3 scripts/analysis/demographics_harness.py gini "$S" --tag GBR --tag FRA --tag PRU --tag USA --tag CHI
python3 scripts/analysis/demographics_harness.py seed "$S" --tag GBR
python3 scripts/analysis/demographics_harness.py seed "$S" --tag CHI
```

  Expected (run before this plan was written): the sketch rows of Task 2's tests; `GINI_SCALE for GBR = 0.52: 0.85`
  with France 0.40, Prussia 0.43, the US 0.46 and China 0.40 shown; Britain seeded at about 5.9 children per woman,
  e0 about 43 for women and 39 for men, infant mortality about 160 per 1,000, 0–14 at 41%; China at about 6.1, 39/35,
  190 per 1,000. If `gini` prints a scale other than `params: 0.85`, put the new value in `demographics_params.py`
  and re-run Task 2's tests. The doc also says: the Q10 natural-change check (`natural-change OLD NEW`) waits for two
  plain-text saves a month apart, which the owner makes (Owner checks, item 1); calibration to world history is
  phase 2's prerequisite (Scope).

- [ ] **Step 6: Document the tools.** In `docs/guides/python_tools.md`, add rows for `demographics_harness.py`
  (the six commands, one line each) and `demographics_save_inputs.py` (plain-text saves only; `slice` writes test
  fixtures), next to `save_country_probe.py`'s row.

- [ ] **Step 7: Commit, then open PR 1**

```bash
git add scripts/analysis/demographics_harness.py test_demographics_harness.py docs/testing/demographics-harness-2026-10-08.md docs/guides/python_tools.md scripts/analysis/demographics_params.py
git commit -m "Demographics harness: sketch, Gini anchor, seeded countries, natural change, replay"
```

  Run the CI checks that touch Python before pushing: `python3 -m compileall -q scripts test_*.py`,
  `python3 -m unittest discover -s . -p 'test_*.py'` (with the dummy `VIC3_*` variables from CLAUDE.md), `ruff check .`.
  PR 1's body: the scope paragraph above, what the harness printed, "Player guide: no player-facing change".

---

# Part B — PR 2: the census

Branch PR 2 from PR 1's branch; `--base main`. Every task below ends with a `POST /reload` on a server started from
this worktree on another port (CLAUDE.md, worktrees) or, at the end, from the main checkout, and the reload's
`warnings` array checked. The game is needed only for the owner checks at the end.

**Where the yearly work runs (read before Tasks 5–12).**

| Pulse | Scope | Runs |
|---|---|---|
| `on_game_started` | none → a hidden country event per country (`te_demog_events.1`, the #822 dispatch pattern) | walk + Wealth Concentration seed for every state; if `te_demog_cohorts_run`: seed every state's ring, then the country's figures |
| `on_yearly_pulse_state` (spread over the year, a different day per state) | state | `te_demog_state_yearly`: walks → inheritance's rural modifiers → Wealth Concentration drift → (cohorts run) seed, skip or step → the state's figures |
| `on_monthly_pulse_country` | country | war-dead snapshot, whatever the rule (Wealth Concentration's war shock reads it) |
| `on_yearly_pulse_country` (31 December) | country | war shock; national Wealth Concentration, the national Gini and #822's modifiers (through `te_inh_yearly_update`); (cohorts run) war dead shared out to states, country sums, lists, urban pattern, projection, history sample |

`te_inheritance_on_actions.txt:50-60`'s own `on_yearly_pulse_state` hook is removed in Task 7; the demographics
orchestrator calls `te_inh_refresh_rural_effects` after its walk, so the agrarian share it reads is this year's.

### Task 5: The game rule, the gates, loc routing and the registry test

**Files:**
- Modify: `common/game_rules/extra_game_rules.txt` (after `grand_monuments_rule`, `:376-391`),
  `localization/english/te_game_rules_l_english.yml`, `organize_loc.py:585` (beside the `gm_` rule)
- Create: `common/scripted_triggers/te_demog_triggers.txt`, `test_demographics_registry.py`

**Interfaces:**
- Produces: rule `demographics_rule`; triggers `te_demog_cohorts_run`, `te_demog_effects_run` (no scope),
  `te_demog_has_census` (state), `te_demog_is_capital_building`, `te_demog_is_ownership_building`,
  `te_demog_rural_workplace`, `te_demog_female_job_workplace` (building); `organize_loc` files every `te_demog_*`
  key under MISCELLANEOUS; `test_demographics_registry.py` with the helpers `_text(path)`, `_block(text, name)` and
  `DEMOG_FILES` that later tasks extend.

- [ ] **Step 1: Write the failing registry test** — `test_demographics_registry.py`:

```python
"""Demographics phase 1 wiring (docs/superpowers/plans/2026-10-08-demographics-phases-0-1.md).

Static checks on the script: the rule's settings and wrappers, guarded divisions, the
pulse wiring, the gates around every cohort entry point. Later tasks add tests here.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import organize_loc  # noqa: E402

RULES = ROOT / "common" / "game_rules" / "extra_game_rules.txt"
TRIGGERS = ROOT / "common" / "scripted_triggers" / "te_demog_triggers.txt"
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
        body = _block(_text(RULES), "demographics_rule")
        self.assertIn("default = demographics_full", body)
        for setting in ("demographics_full", "demographics_display_only", "demographics_disabled"):
            self.assertIn(f"{setting} = {{", body)

    def test_wrappers_test_negatively(self):
        text = _text(TRIGGERS)
        self.assertIn("NOT = { has_game_rule = demographics_disabled }", _block(text, "te_demog_cohorts_run"))
        effects = _block(text, "te_demog_effects_run")
        self.assertIn("te_demog_cohorts_run = yes", effects)
        self.assertIn("NOT = { has_game_rule = demographics_display_only }", effects)

    def test_nothing_tests_full(self):
        for path in [*ROOT.glob("common/**/*.txt"), *ROOT.glob("events/*.txt")]:
            self.assertNotIn("has_game_rule = demographics_full", _text(path), str(path))


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
```

- [ ] **Step 2: Run it to see it fail**

Run: `python3 -m unittest test_demographics_registry -v`
Expected: FAIL/ERROR — `demographics_rule not found`, no trigger file, `te_demog_label_add` filed under MODIFIERS.

- [ ] **Step 3: The rule.** Append after `grand_monuments_rule` in `common/game_rules/extra_game_rules.txt`:

```
# Demographics (docs/superpowers/specs/2026-10-08-demographics-design.md §11.4).
# Full runs the cohort model and, from phase 2, applies its effects; Display only
# runs the cohorts and the panel but applies only the equilibrium's births and
# deaths; Disabled runs neither. In phase 1 nothing is applied, so Full and Display
# only behave the same. Every check is written negatively (te_demog_cohorts_run,
# te_demog_effects_run) so a save from before the rule keeps the system.
demographics_rule = {
	default = demographics_full

	demographics_full = {
		flag = demographics_full
	}

	demographics_display_only = {
		flag = demographics_display_only
	}

	demographics_disabled = {
		flag = demographics_disabled
	}
}
```

  Loc in `te_game_rules_l_english.yml`, beside `rule_grand_monuments_rule` (`:13`) and the settings (`:59-62`):
  `rule_demographics_rule: "Demographics"`, `setting_demographics_full: "Full"`,
  `setting_demographics_full_desc: "Every state keeps a census of its people by age and sex. From a later version it also shapes births, deaths and the workforce."`,
  `setting_demographics_display_only: "Display only"`,
  `setting_demographics_display_only_desc: "The census and its panel, without its effects on the population."`,
  `setting_demographics_disabled: "Disabled"`,
  `setting_demographics_disabled_desc: "No census and no Demographics panel. Wealth Concentration still works."`.

- [ ] **Step 4: The triggers** — `common/scripted_triggers/te_demog_triggers.txt` (UTF-8 BOM, tabs):

```
# ============================================================================
# DEMOGRAPHICS — gates and building classes
# (docs/superpowers/specs/2026-10-08-demographics-design.md; plan Task 5)
# ============================================================================

# The cohort model, the panel and the history run unless the rule is Disabled.
te_demog_cohorts_run = {
	NOT = { has_game_rule = demographics_disabled }
}

# The model's effects (phase 2) apply only under Full.
te_demog_effects_run = {
	te_demog_cohorts_run = yes
	NOT = { has_game_rule = demographics_display_only }
}

# State scope: the state has a census (a seeded ring).
te_demog_has_census = {
	has_variable = te_dg_year
}

# Building scope: capital in §4.2's sense. The ownership buildings own themselves,
# Subsistence Farms read private and government buildings read state-owned, so all
# three are left out (docs/testing/demographics-probe-results-2026-10-08.md, Q2).
te_demog_is_capital_building = {
	NOR = {
		te_demog_is_ownership_building = yes
		is_building_group = bg_subsistence_agriculture
		is_building_group = bg_subsistence_ranching
		is_government_funded = yes
	}
}

# Building scope: where great fortunes are held (§4.2's weights).
te_demog_is_ownership_building = {
	OR = {
		is_building_type = building_manor_house
		is_building_type = building_financial_district
		is_building_type = building_company_headquarter
		is_building_type = building_company_regional_headquarter
	}
}

# Building scope: a rural workplace, for urban population (§5.1; plan Decisions).
te_demog_rural_workplace = {
	OR = {
		is_building_group = bg_agriculture
		is_building_group = bg_plantations
		is_building_group = bg_ranching
		is_building_group = bg_extraction
		is_building_group = bg_subsistence_agriculture
		is_building_group = bg_subsistence_ranching
	}
}

# Building scope: work that drew women as labour migrants (§2.5).
te_demog_female_job_workplace = {
	OR = {
		is_building_group = bg_light_industry
		is_building_group = bg_service
		is_building_group = bg_urban_facilities
	}
}
```

- [ ] **Step 5: Loc routing.** In `organize_loc.py`'s `categorize_key`, directly after the `gm_` rule (`:585-586`):

```python
    # Demographics (docs/superpowers/specs/2026-10-08-demographics-design.md). Every
    # loc key the system adds starts te_demog_, so its panel, tooltips and figures stay
    # in one file even when a key ends in _add or _desc. Rule keys (rule_/setting_)
    # and te_debug_demog.* event keys keep their own routing.
    if key.startswith("te_demog_"):
        return "MISCELLANEOUS"
```

- [ ] **Step 6: Run the tests and a reload**

Run: `python3 -m unittest test_demographics_registry -v && python3 scripts/format_paradox_tabs.py --check common/scripted_triggers/te_demog_triggers.txt common/game_rules/extra_game_rules.txt && python3 organize_loc.py --check`
Expected: OK; tabs clean; `organize_loc --check` exit 0. Then a `POST /reload` on this worktree's server: no new
`warnings` entry naming `te_demog`.

- [ ] **Step 7: Commit**

```bash
git add common/game_rules/extra_game_rules.txt localization/english/te_game_rules_l_english.yml organize_loc.py common/scripted_triggers/te_demog_triggers.txt test_demographics_registry.py
git commit -m "Demographics: game rule, gates, building classes, loc routing"
```

### Task 6: The generator

Everything the script repeats per slot, per age group or per band, and every number from the model, is written by
`gen_demographics.py` from `demographics_params.py`. The hand-written script (Tasks 7–10) calls what it writes; until
then the generated effects are defined but unused.

**Files:**
- Create: `scripts/generators/gen_demographics.py`, `test_gen_demographics.py`
- Create (generated): `common/scripted_effects/te_demog_generated_effects.txt`,
  `common/script_values/te_demog_generated_values.txt`
- Modify: `docs/auto_generated_files.md` (a row in the table at `:15-16`, beside `te_region_area_generated.txt`'s
  row `:29`, Notes starting "One-shot, not a post-load generator")

**Interfaces:**
- Consumes: Task 1 (`pop_growth.read_defines`, `monthly_*`), Task 2 (`demographics_params`, `demographics_model.
  asfr_shape`, `growth_factor`, `group_of`).
- Produces (names the hand-written script calls; locals it reads and writes):

| Generated | Scope | Reads | Writes / calls |
|---|---|---|---|
| `te_demog_sweep` | state | `local_var:te_dg_open` | `te_demog_slot_p1/_p2 = { S = k }`, k = 149…0 twice |
| `te_demog_seed_sweep` | state | `te_dg_open` | `te_demog_seed_p1/_p2 = { S = k }` |
| `te_demog_enter_group` | state | `te_dg_g`, `te_dg_m_inf`, `te_dg_m_work_f`, `te_dg_m_work_m`, `te_dg_m_ext`, `te_dg_m_chr` | `te_dg_qf`, `te_dg_qm` (per 100k a year), `te_dg_asfr` (per 100k a single year), `te_dg_next_group` |
| `te_demog_flush_band` | state | `te_dg_band`, `te_dg_acc_bf/_bm` | `var:te_dg_bf<b>`, `te_dg_bm<b>` |
| `te_demog_flush_class` | state | `te_dg_cls`, `te_dg_acc_cf/_cm` | `var:te_dg_cf<c>`, `te_dg_cm<c>` |
| `te_demog_enter_class` | state | `te_dg_cls`, `te_dg_mig_in`, `te_dg_mig_out`, `te_dg_pf<c>`, `te_dg_pm<c>`, `var:te_dg_cf<c>/cm<c>` | `te_dg_mig_add_f/_m`, `te_dg_mig_frac_f/_m` |
| `te_demog_life_table` | state | `te_dg_m_*` | calls `te_demog_lt_group = { N FERTILE }` per group and `te_demog_lt_finish`; sets `var:te_dg_imr` |
| `te_demog_set_growth_factor` | state | `te_dg_nrr` | `te_dg_d` |
| `te_demog_add_bands_to_root` | state, ROOT = owner | `var:te_dg_bf<b>/bm<b>` | ROOT's `te_dg_cbf<b>/cbm<b>` |
| `te_demog_reset_country_bands` | country | | `te_dg_cbf<b>/cbm<b>` = 0 |
| `te_demog_scale_bands` | state | `te_dg_new_scale` | multiplies bands and class sums |
| `te_demog_set_profile` | state | `te_dg_labour`, `te_dg_family`, `te_dg_refugee`, `te_dg_labour_f` | `te_dg_pf<c>`, `te_dg_pm<c>` |
| `te_demog_band_figures = { B }` | state or country | `var:$B$f<b>/$B$m<b>` | `te_dg_total/young/working/old/w1549/w2059/m2059/median` |
| `te_demog_project` | country | `var:te_dg_cbf<b>/cbm<b>`, `te_dg_m_*`, `te_dg_tfr` | `var:te_dg_pjf<b>/pjm<b>` |
| `te_demog_debug_log_ring_before/_after` | state | `te_demog_dbg_*` | `TE_DEMOG_REPLAY` lines |
| `te_demog_pop_engine_births/_deaths`, `te_demog_pop_wealth_tfr`, `te_demog_pop_income` | pop | | size × the curve |
| `te_demog_mult_<cause>` (5), `te_demog_female_work_share`, `te_demog_means`, `te_demog_family_transport` | state | owner's techs, laws, institutions; `var:te_dg_sol`, `var:te_dg_lit` | |
| `te_demog_k_*` | any | | constants from the params |

- [ ] **Step 1: Write the failing test** — `test_gen_demographics.py`:

```python
"""scripts/generators/gen_demographics.py: the committed script is a fresh generation, and its shape."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts"))

import gen_demographics as gen  # noqa: E402
import demographics_params as P  # noqa: E402
from format_paradox_tabs import format_text  # noqa: E402


class TestGenerated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = gen.plan_outputs()
        cls.effects = cls.outputs[gen.EFFECTS]
        cls.values = cls.outputs[gen.VALUES]

    def test_committed_outputs_are_current(self):
        for rel, text in self.outputs.items():
            self.assertEqual((ROOT / rel).read_text(encoding="utf-8-sig"), text, str(rel))

    def test_tabs_already_formatted(self):
        for rel, text in self.outputs.items():
            self.assertEqual(format_text(text), text, str(rel))

    def test_five_decimals_at_most(self):
        for rel, text in self.outputs.items():
            self.assertIsNone(re.search(r"\d\.\d{6,}", text), str(rel))

    def test_sweeps_visit_every_slot_twice_in_descending_order(self):
        for name, p1, p2 in (("te_demog_sweep", "te_demog_slot_p1", "te_demog_slot_p2"),
                             ("te_demog_seed_sweep", "te_demog_seed_p1", "te_demog_seed_p2")):
            body = self.effects.split(f"{name} = {{", 1)[1].split("\n}\n", 1)[0]
            calls = re.findall(r"(te_demog_\w+_p[12]) = \{ S = (\d+) \}", body)
            expected = [(p1, str(k)) for k in range(P.RING_YEARS - 1, -1, -1)]
            expected += [(p2, str(k)) for k in range(P.RING_YEARS - 1, -1, -1)]
            self.assertEqual(calls, expected, name)

    def test_one_leaf_per_age_group(self):
        body = self.effects.split("te_demog_enter_group = {", 1)[1].split("\n}\n", 1)[0]
        self.assertEqual(body.count("name = te_dg_next_group"), len(P.GROUPS))

    def test_life_table_calls_pass_both_arguments(self):
        calls = re.findall(r"te_demog_lt_group = \{ (.*?) \}", self.effects)
        self.assertEqual(len(calls), len(P.GROUPS))
        for call in calls:
            self.assertRegex(call, r"^N = \d FERTILE = (yes|no)$")

    def test_engine_curves_match_the_defines(self):
        self.assertIn("te_demog_pop_engine_births = {", self.values)
        self.assertIn("value = 475", self.values)      # 0.00475 a month x 100,000
        self.assertIn("value = 80", self.values)       # 0.00080 at SoL 35+

    def test_every_cause_has_a_multiplier(self):
        for cause in gen.CAUSES:
            self.assertIn(f"te_demog_mult_{cause} = {{", self.values)
```

- [ ] **Step 2: Run it to see it fail**

Run: `python3 -m unittest test_gen_demographics -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'gen_demographics'`.

- [ ] **Step 3: Write the generator** — `scripts/generators/gen_demographics.py`:

```python
#!/usr/bin/env python3
"""Write the demographics script that mirrors scripts/analysis/demographics_model.py.

Usage:
    python3 scripts/generators/gen_demographics.py            # write the two files
    python3 scripts/generators/gen_demographics.py --check    # exit 1 if either is stale

Spec: docs/superpowers/specs/2026-10-08-demographics-design.md; plan:
docs/superpowers/plans/2026-10-08-demographics-phases-0-1.md (Task 6). Inputs:
scripts/analysis/demographics_params.py (every rate, weight and table),
common/defines/extra_defines.txt (the engine's growth curves, through pop_growth.py) and
common/buy_packages/00_buy_packages.txt (spending per head by wealth). Not a post-load
regenerator: run it after changing any of those; test_gen_demographics.py fails CI when
the committed files are stale.

What it writes (the hand-written logic is in te_demog_effects.txt / te_demog_values.txt):
    common/scripted_effects/te_demog_generated_effects.txt
        te_demog_sweep, te_demog_seed_sweep     the ring in age order, two guarded passes
        te_demog_enter_group                    a group's death rates, fertility, next start
        te_demog_flush_band, te_demog_enter_class, te_demog_flush_class
        te_demog_life_table, te_demog_set_growth_factor
        te_demog_add_bands_to_root, te_demog_reset_country_bands, te_demog_scale_bands
        te_demog_debug_log_ring_before / _after  (Task 15's replay lines)
    common/script_values/te_demog_generated_values.txt
        per-pop engine curves, wealth TFR and income; per-state cause multipliers,
        women's work share and the means; te_demog_k_* constants; per-slot debug shares
"""

import argparse
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
import pop_growth as G  # noqa: E402

EFFECTS = Path("common/scripted_effects/te_demog_generated_effects.txt")
VALUES = Path("common/script_values/te_demog_generated_values.txt")
BUY_PACKAGES = Path("common/buy_packages/00_buy_packages.txt")
HEADER = ("# AUTO-GENERATED by scripts/generators/gen_demographics.py - do not edit manually.\n"
          "# docs/superpowers/specs/2026-10-08-demographics-design.md; parameters in\n"
          "# scripts/analysis/demographics_params.py.\n")
N = P.RING_YEARS
INCOME_KNOTS = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
NRR_KNOTS = [round(0.2 + 0.1 * i, 1) for i in range(39)]          # 0.2 .. 4.0
CAUSES = ("infection", "work", "external", "maternal", "chronic")


def lit(x):
    """A script literal: at most five decimals, no trailing zeros."""
    d = Decimal(repr(float(x))).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)
    text = format(d.normalize(), "f")
    return "0" if text in ("-0", "") else text


class Out:
    """Tab-indented text that matches scripts/format_paradox_tabs.py."""

    def __init__(self):
        self.lines = []
        self.depth = 0

    def __call__(self, text=""):
        for raw in text.split("\n"):
            line = raw.strip()
            if not line:
                self.lines.append("")
                continue
            if line.startswith("}"):
                self.depth -= 1
            self.lines.append("\t" * self.depth + line)
            self.depth += line.count("{") - line.count("}") + (1 if line.startswith("}") else 0)

    def text(self):
        assert self.depth == 0, self.depth
        return "\n".join(self.lines).rstrip("\n") + "\n"


def tree(o, var, lo, hi, leaf):
    """A balanced if/else tree on local_var:<var> over lo..hi; leaf(o, i) writes branch i."""
    if lo == hi:
        leaf(o, lo)
        return
    mid = (lo + hi) // 2
    o("if = {")
    o(f"limit = {{ local_var:{var} <= {mid} }}")
    tree(o, var, lo, mid, leaf)
    o("}")
    o("else = {")
    tree(o, var, mid + 1, hi, leaf)
    o("}")


# ---- effects ------------------------------------------------------------------------

def sweeps(o):
    o("# The yearly step's sweep: pass 1 visits slots open-1 .. 0 (ages 1 .. open), pass 2")
    o("# slots 149 .. open (ages open+1 .. 150), so te_demog_slot sees ages in order.")
    o("te_demog_sweep = {")
    for k in range(N - 1, -1, -1):
        o(f"te_demog_slot_p1 = {{ S = {k} }}")
    for k in range(N - 1, -1, -1):
        o(f"te_demog_slot_p2 = {{ S = {k} }}")
    o("}")
    o("")
    o("# The seed's sweep: ages 0 .. open, then open+1 .. 149.")
    o("te_demog_seed_sweep = {")
    for k in range(N - 1, -1, -1):
        o(f"te_demog_seed_p1 = {{ S = {k} }}")
    for k in range(N - 1, -1, -1):
        o(f"te_demog_seed_p2 = {{ S = {k} }}")
    o("}")
    o("")


def _rate(o, name, terms):
    terms = [(m, v) for m, v in terms if v]
    o("set_local_variable = {")
    o(f"name = {name}")
    if not terms:
        o("value = 0")
    else:
        o("value = {")
        (m0, v0), rest = terms[0], terms[1:]
        o(f"value = local_var:{m0}")
        o(f"multiply = {lit(v0)}")
        for m, v in rest:
            o("add = {")
            o(f"value = local_var:{m}")
            o(f"multiply = {lit(v)}")
            o("}")
        o("max = 100000")
        o("}")
    o("}")


def enter_group(o):
    o("# THIS = a state. local_var:te_dg_g = the age group (demographics_params.GROUPS); sets")
    o("# te_dg_qf / te_dg_qm (death probability a year per 100,000), te_dg_asfr (share of a")
    o("# lifetime's births at each single age, per 100,000) and te_dg_next_group (the next")
    o("# group's first age) from the cause multipliers te_dg_m_inf, te_dg_m_work_f,")
    o("# te_dg_m_work_m, te_dg_m_ext and te_dg_m_chr (te_demog_prepare).")
    o("te_demog_enter_group = {")

    def leaf(o, g):
        _rate(o, "te_dg_qf", [("te_dg_m_inf", P.INFECTION["f"][g]), ("te_dg_m_work_f", P.WORK_BASE[g]),
                              ("te_dg_m_ext", P.EXTERNAL["f"][g]), ("te_dg_m_chr", P.CHRONIC["f"][g])])
        _rate(o, "te_dg_qm", [("te_dg_m_inf", P.INFECTION["m"][g]), ("te_dg_m_work_m", P.WORK_BASE[g]),
                              ("te_dg_m_ext", P.EXTERNAL["m"][g]), ("te_dg_m_chr", P.CHRONIC["m"][g])])
        start = P.GROUPS[g][0]
        o(f"set_local_variable = {{ name = te_dg_asfr value = {lit(M.asfr_shape(start))} }}")
        nxt = P.GROUPS[g + 1][0] if g + 1 < len(P.GROUPS) else 999
        o(f"set_local_variable = {{ name = te_dg_next_group value = {nxt} }}")

    tree(o, "te_dg_g", 0, len(P.GROUPS) - 1, leaf)
    o("}")
    o("")


def bands_and_classes(o):
    o("# THIS = a state. Writes the running band sums into band local_var:te_dg_band.")
    o("te_demog_flush_band = {")
    tree(o, "te_dg_band", 0, P.BANDS - 1, lambda o, b: (
        o(f"set_variable = {{ name = te_dg_bf{b} value = local_var:te_dg_acc_bf }}"),
        o(f"set_variable = {{ name = te_dg_bm{b} value = local_var:te_dg_acc_bm }}")))
    o("}")
    o("")
    o("# THIS = a state. Writes the running class sums into class local_var:te_dg_cls.")
    o("te_demog_flush_class = {")
    tree(o, "te_dg_cls", 0, len(P.MIGRANT_CLASSES) - 1, lambda o, c: (
        o(f"set_variable = {{ name = te_dg_cf{c} value = local_var:te_dg_acc_cf }}"),
        o(f"set_variable = {{ name = te_dg_cm{c} value = local_var:te_dg_acc_cm }}")))
    o("}")
    o("")
    o("# THIS = a state. On entering migrant class local_var:te_dg_cls: arrivals per single year")
    o("# (te_dg_mig_add_f / _m) and the share of each cohort that leaves (te_dg_mig_frac_f / _m),")
    o("# from the profile (te_dg_pf<c> / te_dg_pm<c>) and last year's class sums.")
    o("te_demog_enter_class = {")

    def leaf(o, c):
        lo, hi = P.MIGRANT_CLASSES[c]
        width = hi - lo + 1
        for sex, prof, last in (("f", f"te_dg_pf{c}", f"te_dg_cf{c}"), ("m", f"te_dg_pm{c}", f"te_dg_cm{c}")):
            o("set_local_variable = {")
            o(f"name = te_dg_mig_add_{sex}")
            o(f"value = {{ value = local_var:te_dg_mig_in multiply = local_var:{prof} divide = {width} }}")
            o("}")
            o(f"set_local_variable = {{ name = te_dg_mig_frac_{sex} value = 0 }}")
            o("if = {")
            o("limit = { local_var:te_dg_mig_out > 0 }")
            o("set_local_variable = {")
            o(f"name = te_dg_mig_frac_{sex}")
            o(f"value = {{ value = local_var:te_dg_mig_out multiply = local_var:{prof} "
              f"divide = {{ value = var:{last} min = 1 }} }}")
            o("}")
            o("}")
    tree(o, "te_dg_cls", 0, len(P.MIGRANT_CLASSES) - 1, leaf)
    o("}")
    o("")


def life_table(o):
    o("# THIS = a state. The life table over the age groups in order (demographics_model.life_table),")
    o("# plus the NRR's survival-weighted fertility sum. Needs te_dg_m_* (te_demog_prepare).")
    o("te_demog_life_table = {")
    o("set_local_variable = { name = te_dg_lf value = 100000 }")
    o("set_local_variable = { name = te_dg_lm value = 100000 }")
    o("set_local_variable = { name = te_dg_pyf value = 0 }")
    o("set_local_variable = { name = te_dg_pym value = 0 }")
    o("set_local_variable = { name = te_dg_nrr_sum value = 0 }")
    for g, (start, width) in enumerate(P.GROUPS):
        o(f"set_local_variable = {{ name = te_dg_g value = {g} }}")
        o("te_demog_enter_group = yes")
        if start == 65:
            o("set_local_variable = { name = te_dg_l65f value = local_var:te_dg_lf }")
            o("set_local_variable = { name = te_dg_l65m value = local_var:te_dg_lm }")
            o("set_local_variable = { name = te_dg_py65f value = local_var:te_dg_pyf }")
            o("set_local_variable = { name = te_dg_py65m value = local_var:te_dg_pym }")
        if g == 0:
            o("set_variable = { name = te_dg_imr value = { value = local_var:te_dg_qf add = local_var:te_dg_qm "
              "divide = 200 } }")
        fertile = 15 <= start <= 45
        o(f"te_demog_lt_group = {{ N = {width} FERTILE = {'yes' if fertile else 'no'} }}")
    o("te_demog_lt_finish = yes")
    o("}")
    o("")


def growth_factor(o):
    o("# THIS = a state. local_var:te_dg_nrr -> local_var:te_dg_d = NRR^(-1/29), the stable")
    o("# population's yearly factor (demographics_model.growth_factor), linear between knots.")
    o("te_demog_set_growth_factor = {")
    o("if = {")
    o(f"limit = {{ local_var:te_dg_nrr <= {NRR_KNOTS[0]} }}")
    o(f"set_local_variable = {{ name = te_dg_d value = {lit(M.growth_factor(NRR_KNOTS[0]))} }}")
    o("}")
    o("else_if = {")
    o(f"limit = {{ local_var:te_dg_nrr >= {NRR_KNOTS[-1]} }}")
    o(f"set_local_variable = {{ name = te_dg_d value = {lit(M.growth_factor(NRR_KNOTS[-1]))} }}")
    o("}")
    o("else = {")
    o("set_local_variable = {")
    o("name = te_dg_knot")
    o(f"value = {{ value = local_var:te_dg_nrr subtract = {NRR_KNOTS[0]} multiply = 10 floor = yes }}")
    o("}")

    def leaf(o, i):
        x0, x1 = NRR_KNOTS[i], NRR_KNOTS[i + 1]
        d0, d1 = M.growth_factor(x0), M.growth_factor(x1)
        o("set_local_variable = {")
        o("name = te_dg_d")
        o(f"value = {{ value = local_var:te_dg_nrr subtract = {x0} multiply = {lit((d1 - d0) / (x1 - x0))} "
          f"add = {lit(d0)} }}")
        o("}")
    tree(o, "te_dg_knot", 0, len(NRR_KNOTS) - 2, leaf)
    o("}")
    o("}")
    o("")


def country_bands(o):
    o("# THIS = a state, ROOT = its owner on the yearly country pulse: add the state's bands.")
    o("te_demog_add_bands_to_root = {")
    for b in range(P.BANDS):
        for s in ("f", "m"):
            o(f"set_local_variable = {{ name = te_dg_t value = var:te_dg_b{s}{b} }}")
            o(f"root = {{ change_variable = {{ name = te_dg_cb{s}{b} add = local_var:te_dg_t }} }}")
    o("}")
    o("")
    o("# THIS = a country: zero its band sums before the states add theirs.")
    o("te_demog_reset_country_bands = {")
    for b in range(P.BANDS):
        o(f"set_variable = {{ name = te_dg_cbf{b} value = 0 }}")
        o(f"set_variable = {{ name = te_dg_cbm{b} value = 0 }}")
    o("}")
    o("")
    o("# THIS = a state: multiply the bands and class sums by local_var:te_dg_new_scale.")
    o("te_demog_scale_bands = {")
    for b in range(P.BANDS):
        for s in ("f", "m"):
            o(f"change_variable = {{ name = te_dg_b{s}{b} multiply = local_var:te_dg_new_scale }}")
    for c in range(len(P.MIGRANT_CLASSES)):
        for s in ("f", "m"):
            o(f"change_variable = {{ name = te_dg_c{s}{c} multiply = local_var:te_dg_new_scale }}")
    o("}")
    o("")


def debug_ring(o):
    for when in ("before", "after"):
        o(f"# THIS = a state: the ring as TE_DEMOG_REPLAY {when} lines (demographics_harness.format_replay).")
        o(f"te_demog_debug_log_ring_{when} = {{")
        for first in range(0, N, 10):
            f = ",".join(f"[THIS.ScriptValue('te_demog_dbg_f{k}')|5]" for k in range(first, first + 10))
            m = ",".join(f"[THIS.ScriptValue('te_demog_dbg_m{k}')|5]" for k in range(first, first + 10))
            extra = ""
            if first == 0:
                extra = (" pool_f=[THIS.ScriptValue('te_demog_dbg_pool_f')|5]"
                         " pool_m=[THIS.ScriptValue('te_demog_dbg_pool_m')|5]"
                         " pool_age=[THIS.Var('te_dg_pa').GetValue|5]")
            o(f'debug_log = "TE_DEMOG_REPLAY {when} from={first} f={f} m={m}{extra}"')
        o("}")
        o("")


def profile(o):
    o("# THIS = a state. The migrant profile (demographics_model.migrant_profile): from the kinds'")
    o("# weights te_dg_labour, te_dg_family, te_dg_refugee and labour's women's share")
    o("# te_dg_labour_f, each class's share for women (te_dg_pf<c>) and men (te_dg_pm<c>).")
    o("te_demog_set_profile = {")
    for c in range(len(P.MIGRANT_CLASSES)):
        lw = P.MIGRANT_PROFILE["labour"]["weights"][c]
        fw = P.MIGRANT_PROFILE["family"]["weights"][c]
        rw = P.MIGRANT_PROFILE["refugee"]["weights"][c]
        both = (f"add = {{ value = local_var:te_dg_family multiply = {lit(fw * 0.5)} }} "
                f"add = {{ value = local_var:te_dg_refugee multiply = {lit(rw * 0.5)} }}")
        o(f"set_local_variable = {{ name = te_dg_pf{c} value = {{ value = local_var:te_dg_labour "
          f"multiply = {lit(lw)} multiply = local_var:te_dg_labour_f {both} }} }}")
        o(f"set_local_variable = {{ name = te_dg_pm{c} value = {{ value = 1 subtract = local_var:te_dg_labour_f "
          f"multiply = local_var:te_dg_labour multiply = {lit(lw)} {both} }} }}")
    o("}")
    o("")


def band_figures(o):
    young = range(0, 3)
    working = range(3, 13)
    o("# THIS = a state or a country; $B$ = the band variables' prefix (te_dg_b or te_dg_cb).")
    o("# Sets locals te_dg_total, te_dg_young, te_dg_working, te_dg_old (0-14, 15-64, 65+),")
    o("# te_dg_w1549 (women 15-49), te_dg_w2059 and te_dg_m2059 (20-59), then te_dg_median.")
    o("te_demog_band_figures = {")
    for name in ("total", "young", "working", "old", "w1549", "w2059", "m2059"):
        o(f"set_local_variable = {{ name = te_dg_{name} value = 0 }}")
    for b in range(P.BANDS):
        o(f"set_local_variable = {{ name = te_dg_t value = {{ value = var:$B$f{b} add = var:$B$m{b} }} }}")
        o("change_local_variable = { name = te_dg_total add = local_var:te_dg_t }")
        group = "young" if b in young else "working" if b in working else "old"
        o(f"change_local_variable = {{ name = te_dg_{group} add = local_var:te_dg_t }}")
        if 3 <= b <= 9:
            o(f"change_local_variable = {{ name = te_dg_w1549 add = var:$B$f{b} }}")
        if 4 <= b <= 11:
            o(f"change_local_variable = {{ name = te_dg_w2059 add = var:$B$f{b} }}")
            o(f"change_local_variable = {{ name = te_dg_m2059 add = var:$B$m{b} }}")
    o("# the median: the band where the running sum passes half, interpolated inside it")
    o("set_local_variable = { name = te_dg_half value = { value = local_var:te_dg_total multiply = 0.5 } }")
    o("set_local_variable = { name = te_dg_run value = 0 }")
    o("set_local_variable = { name = te_dg_median value = -1 }")
    for b in range(P.BANDS):
        width = P.BAND_WIDTH if b < P.BANDS - 1 else 15
        o("if = {")
        o("limit = { local_var:te_dg_median < 0 }")
        o(f"set_local_variable = {{ name = te_dg_t value = {{ value = var:$B$f{b} add = var:$B$m{b} }} }}")
        o("set_local_variable = { name = te_dg_run2 value = { value = local_var:te_dg_run add = local_var:te_dg_t } }")
        o("if = {")
        o("limit = { local_var:te_dg_run2 >= local_var:te_dg_half }")
        o(f"set_local_variable = {{ name = te_dg_median value = {{ value = local_var:te_dg_half "
          f"subtract = local_var:te_dg_run divide = {{ value = local_var:te_dg_t min = 0.00001 }} "
          f"multiply = {width} add = {b * P.BAND_WIDTH} }} }}")
        o("}")
        o("change_local_variable = { name = te_dg_run add = local_var:te_dg_t }")
        o("}")
    o("}")
    o("")


def projection(o):
    """Twenty years ahead in four five-year steps on the bands (spec 10's outline)."""
    o("# THIS = a country (the player's). From the country's band sums te_dg_cb* and its average")
    o("# rates (te_dg_m_* locals, local_var:te_dg_tfr): te_dg_pjf<b> / te_dg_pjm<b>, the bands")
    o("# twenty years ahead. Five-year survival per band from its age group; births from women")
    o("# 15-49 at their group's fertility. A display outline, not the model's step.")
    o("te_demog_project = {")
    for b in range(P.BANDS):
        start = b * P.BAND_WIDTH
        g = P.group_of(start) if b > 0 else 1
        o(f"set_local_variable = {{ name = te_dg_g value = {g} }}")
        o("te_demog_enter_group = yes")
        for s in ("f", "m"):
            o(f"set_local_variable = {{ name = te_dg_s{s}{b} value = {{ value = 1 subtract = "
              f"{{ value = local_var:te_dg_q{s} divide = 100000 }} }} }}")
            o(f"set_local_variable = {{ name = te_dg_t value = local_var:te_dg_s{s}{b} }}")
            o(f"while = {{ count = 4 change_local_variable = {{ name = te_dg_s{s}{b} multiply = local_var:te_dg_t }} }}")
        o(f"set_local_variable = {{ name = te_dg_fert{b} value = {{ value = local_var:te_dg_asfr multiply = 5 "
          f"divide = 100000 multiply = local_var:te_dg_tfr }} }}")
        o(f"set_local_variable = {{ name = te_dg_xf{b} value = var:te_dg_cbf{b} }}")
        o(f"set_local_variable = {{ name = te_dg_xm{b} value = var:te_dg_cbm{b} }}")
    last = P.BANDS - 1
    for _step in range(4):
        o("set_local_variable = { name = te_dg_births value = 0 }")
        for b in range(P.BANDS):
            o(f"change_local_variable = {{ name = te_dg_births add = {{ value = local_var:te_dg_xf{b} "
              f"multiply = local_var:te_dg_fert{b} }} }}")
        for s in ("f", "m"):
            o(f"set_local_variable = {{ name = te_dg_x{s}{last} value = {{ value = local_var:te_dg_x{s}{last} "
              f"multiply = local_var:te_dg_s{s}{last} add = {{ value = local_var:te_dg_x{s}{last - 1} "
              f"multiply = local_var:te_dg_s{s}{last - 1} }} }} }}")
            for b in range(last - 1, 0, -1):
                o(f"set_local_variable = {{ name = te_dg_x{s}{b} value = {{ value = local_var:te_dg_x{s}{b - 1} "
                  f"multiply = local_var:te_dg_s{s}{b - 1} }} }}")
        o(f"set_local_variable = {{ name = te_dg_xf0 value = {{ value = local_var:te_dg_births "
          f"multiply = {lit(P.FEMALE_BIRTH_PER_100K / 100000)} multiply = local_var:te_dg_sf0 }} }}")
        o(f"set_local_variable = {{ name = te_dg_xm0 value = {{ value = local_var:te_dg_births "
          f"multiply = {lit(P.MALE_BIRTH_PER_100K / 100000)} multiply = local_var:te_dg_sm0 }} }}")
    for b in range(P.BANDS):
        o(f"set_variable = {{ name = te_dg_pjf{b} value = local_var:te_dg_xf{b} }}")
        o(f"set_variable = {{ name = te_dg_pjm{b} value = local_var:te_dg_xm{b} }}")
    o("}")
    o("")


def render_effects():
    o = Out()
    o(HEADER.rstrip("\n"))
    o("")
    sweeps(o)
    enter_group(o)
    bands_and_classes(o)
    life_table(o)
    growth_factor(o)
    country_bands(o)
    profile(o)
    band_figures(o)
    projection(o)
    debug_ring(o)
    return o.text()


# ---- values -------------------------------------------------------------------------

def _piecewise_sol(o, name, comment, points, scale=1.0):
    """A per-pop value: total_size x a piecewise-linear function of standard_of_living."""
    o(f"# {comment}")
    o(f"{name} = {{")
    o("value = total_size")
    o("multiply = {")
    o(f"value = {lit(points[0][1] * scale)}")
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        slope = (y1 - y0) / (x1 - x0) * scale
        o("if = {")
        o(f"limit = {{ standard_of_living > {lit(x0)} }}")
        o(f"value = {{ value = standard_of_living subtract = {lit(x0)} multiply = {lit(slope)} "
          f"add = {lit(y0 * scale)} }}")
        o("}")
    o("if = {")
    o(f"limit = {{ standard_of_living >= {lit(points[-1][0])} }}")
    o(f"value = {lit(points[-1][1] * scale)}")
    o("}")
    o("}")
    o("}")
    o("")


def engine_curves(o, d):
    b = [(0, G.monthly_birthrate(0, d)), (d.transition_sol, G.monthly_birthrate(d.transition_sol, d)),
         (d.stable_sol, G.monthly_birthrate(d.stable_sol, d))]
    m = [(0, G.monthly_mortality(0, d)), (d.equilibrium_sol, G.monthly_mortality(d.equilibrium_sol, d)),
         (d.max_sol, G.monthly_mortality(d.max_sol, d)), (d.stable_sol, G.monthly_mortality(d.stable_sol, d))]
    _piecewise_sol(o, "te_demog_pop_engine_births",
                   "Pop scope: the engine's births a month x 100,000 at this pop's SoL (extra_defines.txt), x size.",
                   b, 100000)
    _piecewise_sol(o, "te_demog_pop_engine_deaths",
                   "Pop scope: the engine's deaths a month x 100,000 at this pop's SoL, x size.", m, 100000)
    _piecewise_sol(o, "te_demog_pop_wealth_tfr",
                   "Pop scope: children per woman from wealth alone at this pop's SoL (spec 2.3), x size.",
                   [(0, P.WEALTH_TFR_LOW), (P.WEALTH_TFR_LOW_SOL, P.WEALTH_TFR_LOW),
                    (P.WEALTH_TFR_HIGH_SOL, P.WEALTH_TFR_HIGH)])


def buy_package_costs(root):
    import re
    text = (root / BUY_PACKAGES).read_text(encoding="utf-8-sig")
    out = {}
    for m in re.finditer(r"^wealth_(\d+) = \{(.*?)^\}", text, re.S | re.M):
        goods = re.search(r"goods = \{[^\n]*\n(.*?)\n\t\}", m.group(2), re.S)
        out[int(m.group(1))] = sum(float(v) for v in re.findall(r"= ([0-9.]+)", goods.group(1)))
    return out


def income(o, costs):
    o("# Pop scope: spending per head at this pop's wealth (buy packages / 100, capped at wealth")
    o(f"# {P.INCOME_WEALTH_CAP}), the stand-in for income in the Gini (spec 4.1), x size.")
    o("te_demog_pop_income = {")
    o("value = total_size")
    o("multiply = {")
    o(f"value = {lit(costs[INCOME_KNOTS[0]] / 100)}")
    for x0, x1 in zip(INCOME_KNOTS, INCOME_KNOTS[1:]):
        y0, y1 = costs[x0] / 100, costs[x1] / 100
        o("if = {")
        o(f"limit = {{ wealth > {x0} }}")
        o(f"value = {{ value = wealth subtract = {x0} multiply = {lit((y1 - y0) / (x1 - x0))} add = {lit(y0)} }}")
        o("}")
    o("if = {")
    o(f"limit = {{ wealth >= {INCOME_KNOTS[-1]} }}")
    o(f"value = {lit(costs[INCOME_KNOTS[-1]] / 100)}")
    o("}")
    o("}")
    o("}")
    o("")


def multipliers(o):
    for cause in CAUSES:
        o(f"# State scope: the {cause} cause's multiplier (demographics_model.cause_multipliers).")
        o(f"te_demog_mult_{cause} = {{")
        o("value = 1")
        for tech, m in P.TECH_MULT.get(cause, {}).items():
            o(f"if = {{ limit = {{ owner = {{ has_technology_researched = {tech} }} }} multiply = {lit(m)} }}")
        for law, m in P.LAW_MULT.get(cause, {}).items():
            o(f"if = {{ limit = {{ owner = {{ has_law = law_type:{law} }} }} multiply = {lit(m)} }}")
        for inst, m in P.INSTITUTION_MULT.get(cause, {}).items():
            for level in range(5, 0, -1):
                kw = "if" if level == 5 else "else_if"
                o(f"{kw} = {{")
                o(f"limit = {{ owner = {{ institution_investment_level = {{ institution = {inst} value >= {level} }} }} }}")
                o(f"multiply = {lit(m ** level)}")
                o("}")
        if cause == "infection":
            o("multiply = {")
            o(f"value = var:te_dg_sol subtract = {P.WEALTH_TFR_LOW_SOL} "
              f"divide = {P.WEALTH_TFR_HIGH_SOL - P.WEALTH_TFR_LOW_SOL} min = 0 max = 1")
            o(f"multiply = {lit(P.SOL_INFECTION_AT_HIGH - 1)} add = 1")
            o("}")
            o(f"multiply = {{ value = var:te_dg_lit multiply = {lit(-P.LITERACY_INFECTION_WEIGHT)} add = 1 }}")
            o("if = {")
            o("limit = {")
            o("has_modifier = migration_crowding")
            o("owner = { NOT = { institution_investment_level = { institution = institution_ministry_of_urban_planning "
              "value >= 1 } } }")
            o("}")
            o(f"multiply = {lit(P.CROWDING_INFECTION_MULT)}")
            o("}")
        if cause == "chronic":
            o("multiply = {")
            o(f"value = var:te_dg_sol subtract = {P.WEALTH_TFR_LOW_SOL} "
              f"divide = {P.WEALTH_TFR_HIGH_SOL - P.WEALTH_TFR_LOW_SOL} min = 0 max = 1")
            o(f"multiply = {lit(P.SOL_CHRONIC_AT_HIGH - 1)} add = 1")
            o("}")
        if cause == "maternal":
            o(f"multiply = {P.MATERNAL_PER_100K_BIRTHS}")
        o("}")
        o("")
    o("# State scope: women's share of the workforce by the owner's women's-rights law.")
    o("te_demog_female_work_share = {")
    o(f"value = {lit(P.FEMALE_WORK_SHARE_DEFAULT)}")
    for law, share in P.FEMALE_WORK_SHARE.items():
        o(f"if = {{ limit = {{ owner = {{ has_law = law_type:{law} }} }} value = {lit(share)} }}")
    o("}")
    o("")
    o("# State scope: the share of the gap to desired fertility a population can close (spec 2.3).")
    o("te_demog_means = {")
    tiers = sorted(P.MEANS_TIERS, key=lambda t: t[1])
    o(f"value = {lit(tiers[0][1])}")
    for tech, value in tiers[1:]:
        o(f"if = {{ limit = {{ owner = {{ has_technology_researched = {tech} }} }} value = {lit(value)} }}")
    o("multiply = { value = var:te_dg_lit multiply = 0.7 add = 0.3 }")
    for law, shift in P.MEANS_LAW_SHIFT.items():
        o(f"if = {{ limit = {{ owner = {{ has_law = law_type:{law} }} }} add = {lit(shift)} }}")
    o(f"max = {lit(P.MEANS_CAP)}")
    o("# a floor set in history: France's early transition (spec 2.6)")
    o("if = {")
    o("limit = { owner = { has_variable = te_dg_means_floor } }")
    o("min = owner.var:te_dg_means_floor")
    o("}")
    o("}")
    o("")


def constants(o):
    o("# Constants the hand-written script reads (demographics_params.py).")
    k = {
        "female_births_per_100k": P.FEMALE_BIRTH_PER_100K, "male_births_per_100k": P.MALE_BIRTH_PER_100K,
        "education_weight": P.EDUCATION_WEIGHT, "survival_weight": P.SURVIVAL_WEIGHT,
        "urban_weight": P.URBAN_WEIGHT, "war_male_share": P.WAR_DEAD_MALE_SHARE,
        "residual_noise_share": P.RESIDUAL_NOISE_SHARE, "gini_floor": P.GINI_FLOOR, "gini_scale": P.GINI_SCALE,
        "labour_female_min": P.LABOUR_FEMALE_SHARE_MIN, "labour_female_max": P.LABOUR_FEMALE_SHARE_MAX,
        "family_base": P.FAMILY_BASE, "family_rights_weight": P.FAMILY_RIGHTS_WEIGHT,
        "full_female_work_share": P.FULL_FEMALE_WORK_SHARE, "chain_step": P.CHAIN_STEP, "chain_cap": P.CHAIN_CAP,
        "crisis_at_war": P.CRISIS_AT_WAR,
    }
    for name, value in k.items():
        o(f"te_demog_k_{name} = {{ value = {lit(value)} }}")
    for kind, spec in P.MIGRANT_PROFILE.items():
        for c, w in enumerate(spec["weights"]):
            o(f"te_demog_k_{kind}_{c} = {{ value = {lit(w)} }}")
    o("# State scope: the family share's transport term (owner technology).")
    o("te_demog_family_transport = {")
    o("value = 0")
    for tech, v in P.FAMILY_TRANSPORT_TECHS.items():
        o(f"if = {{ limit = {{ owner = {{ has_technology_researched = {tech} }} }} add = {lit(v)} }}")
    o("}")
    o("")


def debug_values(o):
    o("# State scope: each slot as per mille of the state's people, for the replay lines (Task 15).")
    for s in ("f", "m"):
        for k in range(N):
            o(f"te_demog_dbg_{s}{k} = {{ value = 0 if = {{ limit = {{ has_variable = te_dg_{s}{k} }} "
              f"value = var:te_dg_{s}{k} multiply = te_demog_dbg_unit }} }}")
    o("te_demog_dbg_pool_f = { value = var:te_dg_pf multiply = te_demog_dbg_unit }")
    o("te_demog_dbg_pool_m = { value = var:te_dg_pm multiply = te_demog_dbg_unit }")
    o("te_demog_dbg_unit = { value = var:te_dg_scale multiply = 1000 divide = { value = var:te_dg_people min = 1 } }")
    o("")


def render_values(root):
    o = Out()
    o(HEADER.rstrip("\n"))
    o("")
    engine_curves(o, G.read_defines(root / "common" / "defines" / "extra_defines.txt"))
    income(o, buy_package_costs(root))
    multipliers(o)
    constants(o)
    debug_values(o)
    return o.text()


def plan_outputs(root=ROOT):
    return {EFFECTS: render_effects(), VALUES: render_values(root)}


def regenerate(root=ROOT, dry_run=False):
    changed = []
    for rel, text in plan_outputs(root).items():
        target = root / rel
        expected = text.encode("utf-8-sig")
        if not target.exists() or target.read_bytes() != expected:
            changed.append(str(rel))
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(expected)
    return {"changed": bool(changed), "changed_files": changed}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if a committed file is stale")
    args = ap.parse_args(argv)
    result = regenerate(dry_run=args.check)
    for rel in result["changed_files"]:
        print(("stale: " if args.check else "wrote: ") + rel)
    return 1 if (args.check and result["changed"]) else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Generate and run the tests**

Run: `python3 scripts/generators/gen_demographics.py && python3 -m unittest test_gen_demographics test_engine_literal_forms -v && python3 scripts/format_paradox_tabs.py --check common/scripted_effects/te_demog_generated_effects.txt common/script_values/te_demog_generated_values.txt && ruff check scripts/generators/gen_demographics.py test_gen_demographics.py`
Expected: `wrote:` both files (about 3,560 and 620 lines); 8 tests OK plus the literal-form test; tabs clean;
ruff clean. `python3 scripts/generators/gen_demographics.py --check` then exits 0.

- [ ] **Step 5: Register it.** `docs/auto_generated_files.md` row: `common/scripted_effects/te_demog_generated_effects.txt`,
  `common/script_values/te_demog_generated_values.txt` | `scripts/generators/gen_demographics.py` |
  `scripts/analysis/demographics_params.py`, `common/defines/extra_defines.txt`, `common/buy_packages/00_buy_packages.txt` |
  "One-shot, not a post-load generator: run it after changing any input. The ring's sweeps, the age-group rate
  tables, the engine's growth curves, the cause multipliers and the debug replay lines; `test_gen_demographics.py`
  fails CI when the committed files are stale."

- [ ] **Step 6: Commit**

```bash
git add scripts/generators/gen_demographics.py test_gen_demographics.py common/scripted_effects/te_demog_generated_effects.txt common/script_values/te_demog_generated_values.txt docs/auto_generated_files.md
git commit -m "Demographics: generator for the cohort sweeps, rate tables, curves and multipliers"
```

### Task 7: The yearly walks and inheritance's handover

One pop walk and one building walk per state a year (§11.3), whatever the rule: inheritance needs the agrarian share
and Wealth Concentration needs the ownership levels. It replaces `te_inh_agrarian_share_value`'s walk.

**Files:**
- Create: `common/scripted_effects/te_demog_effects.txt`, `common/script_values/te_demog_values.txt`,
  `common/on_actions/te_demog_on_actions.txt`
- Modify: `common/scripted_effects/te_inheritance_effects.txt:198`, `common/script_values/te_inheritance_values.txt:135-152`,
  `common/on_actions/te_inheritance_on_actions.txt:50-60`, `test_demographics_registry.py`

**Interfaces:**
- Consumes: Task 5's building triggers; Task 6's `te_demog_pop_*` values.
- Produces: `te_demog_walks` (state). State variables, all written every year: `te_dg_walk_pop`, `te_dg_lit`
  (pop-weighted literacy 0–1), `te_dg_sol`, `te_dg_wtfr` (mean wealth TFR), `te_dg_eb` / `te_dg_ed` (the engine's
  expected births and deaths over a year, people), `te_dg_agr_share`, `te_dg_soldiers`, `te_dg_bureaucrats`,
  `te_dg_urban` (people), `te_dg_urban_share`, `te_dg_fjob_share`, `te_dg_n_lo/_mi/_up` and `te_dg_y_lo/_mi/_up`
  (people and income by strata), `te_dg_gini`, `te_dg_lv_priv`, `te_dg_lv_self`, `te_dg_lv_ctry`, `te_dg_lv_own`.
  `te_demog_state_yearly` (state), the orchestrator the next tasks extend.

- [ ] **Step 1: Failing tests.** Add to `test_demographics_registry.py`:

```python
EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_effects.txt"
INH_EFFECTS = ROOT / "common" / "scripted_effects" / "te_inheritance_effects.txt"
INH_VALUES = ROOT / "common" / "script_values" / "te_inheritance_values.txt"
INH_ON_ACTIONS = ROOT / "common" / "on_actions" / "te_inheritance_on_actions.txt"
DEMOG_ON_ACTIONS = ROOT / "common" / "on_actions" / "te_demog_on_actions.txt"


class TestWalks(unittest.TestCase):
    def test_one_pop_walk_and_one_building_walk(self):
        body = _block(_text(EFFECTS), "te_demog_walks")
        self.assertEqual(body.count("every_scope_pop"), 1)
        self.assertEqual(body.count("every_scope_building"), 1)

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
```

  Run `python3 -m unittest test_demographics_registry -v`: the four new tests fail.

- [ ] **Step 2: Pop-scope and building-scope values** — start `common/script_values/te_demog_values.txt` (BOM,
  header naming the spec and this plan):

```
# Pop scope: literacy x size, SoL x size (the walk's sums).
te_demog_pop_literate = {
	value = literacy_rate
	multiply = total_size
}

te_demog_pop_sol = {
	value = standard_of_living
	multiply = total_size
}

# Building scope: levels in private, cooperative (self-owned) and state hands
# (bareword fractions read as values: docs/testing/demographics-probe-results-2026-10-08.md Q2).
te_demog_building_private_levels = {
	value = level
	multiply = private_ownership_fraction
}

te_demog_building_self_levels = {
	value = level
	multiply = self_ownership_fraction
}

te_demog_building_country_levels = {
	value = level
	multiply = country_ownership_fraction
}

# The current year as a value (probe: add = year gives 1836).
te_demog_year = {
	value = 0
	add = year
}
```

- [ ] **Step 3: The walks** — start `common/scripted_effects/te_demog_effects.txt` with a header that lists every
  `te_dg_` state variable and its meaning (copy the Interfaces list above; Tasks 8–11 add theirs), then:

```
# THIS = a state, on its yearly pulse. One pop walk and one building walk fill
# every sum the census, Wealth Concentration and inheritance need (spec §11.3).
te_demog_walks = {
	set_local_variable = { name = te_dg_w_pop value = 0 }
	set_local_variable = { name = te_dg_w_lit value = 0 }
	set_local_variable = { name = te_dg_w_sol value = 0 }
	set_local_variable = { name = te_dg_w_wtfr value = 0 }
	set_local_variable = { name = te_dg_w_eb value = 0 }
	set_local_variable = { name = te_dg_w_ed value = 0 }
	set_local_variable = { name = te_dg_w_agr value = 0 }
	set_local_variable = { name = te_dg_w_sold value = 0 }
	set_local_variable = { name = te_dg_w_bur value = 0 }
	set_local_variable = { name = te_dg_w_rural value = 0 }
	set_local_variable = { name = te_dg_w_fjob value = 0 }
	set_local_variable = { name = te_dg_w_emp value = 0 }
	set_local_variable = { name = te_dg_w_nlo value = 0 }
	set_local_variable = { name = te_dg_w_nmi value = 0 }
	set_local_variable = { name = te_dg_w_nup value = 0 }
	set_local_variable = { name = te_dg_w_ylo value = 0 }
	set_local_variable = { name = te_dg_w_ymi value = 0 }
	set_local_variable = { name = te_dg_w_yup value = 0 }
	every_scope_pop = {
		change_local_variable = { name = te_dg_w_pop add = total_size }
		change_local_variable = { name = te_dg_w_lit add = te_demog_pop_literate }
		change_local_variable = { name = te_dg_w_sol add = te_demog_pop_sol }
		change_local_variable = { name = te_dg_w_wtfr add = te_demog_pop_wealth_tfr }
		change_local_variable = { name = te_dg_w_eb add = te_demog_pop_engine_births }
		change_local_variable = { name = te_dg_w_ed add = te_demog_pop_engine_deaths }
		if = {
			limit = { strata = upper }
			change_local_variable = { name = te_dg_w_nup add = total_size }
			change_local_variable = { name = te_dg_w_yup add = te_demog_pop_income }
		}
		else_if = {
			limit = { strata = middle }
			change_local_variable = { name = te_dg_w_nmi add = total_size }
			change_local_variable = { name = te_dg_w_ymi add = te_demog_pop_income }
		}
		else = {
			change_local_variable = { name = te_dg_w_nlo add = total_size }
			change_local_variable = { name = te_dg_w_ylo add = te_demog_pop_income }
		}
		if = {
			limit = {
				OR = {
					is_pop_type = peasants
					is_pop_type = farmers
				}
			}
			change_local_variable = { name = te_dg_w_agr add = total_size }
		}
		if = {
			limit = {
				OR = {
					is_pop_type = soldiers
					is_pop_type = officers
				}
			}
			change_local_variable = { name = te_dg_w_sold add = total_size }
		}
		if = {
			limit = { is_pop_type = bureaucrats }
			change_local_variable = { name = te_dg_w_bur add = total_size }
		}
		if = {
			limit = { exists = workplace }
			change_local_variable = { name = te_dg_w_emp add = total_size }
			if = {
				limit = { workplace = { te_demog_rural_workplace = yes } }
				change_local_variable = { name = te_dg_w_rural add = total_size }
			}
			if = {
				limit = { workplace = { te_demog_female_job_workplace = yes } }
				change_local_variable = { name = te_dg_w_fjob add = total_size }
			}
		}
		else_if = {
			limit = { is_pop_type = peasants }
			change_local_variable = { name = te_dg_w_rural add = total_size }
		}
	}
	set_variable = { name = te_dg_walk_pop value = local_var:te_dg_w_pop }
	set_variable = { name = te_dg_lit value = { value = local_var:te_dg_w_lit divide = { value = local_var:te_dg_w_pop min = 1 } } }
	set_variable = { name = te_dg_sol value = { value = local_var:te_dg_w_sol divide = { value = local_var:te_dg_w_pop min = 1 } } }
	set_variable = { name = te_dg_wtfr value = { value = local_var:te_dg_w_wtfr divide = { value = local_var:te_dg_w_pop min = 1 } } }
	# the engine's births and deaths over a year: the curves are x 100,000 a month
	set_variable = {
		name = te_dg_eb
		value = {
			value = local_var:te_dg_w_eb
			multiply = 12
			divide = 100000
			multiply = { value = 1 add = modifier:state_birth_rate_mult min = 0 }
		}
	}
	set_variable = {
		name = te_dg_ed
		value = {
			value = local_var:te_dg_w_ed
			multiply = 12
			divide = 100000
			multiply = { value = 1 add = modifier:state_mortality_mult min = 0 }
		}
	}
	set_variable = { name = te_dg_agr_share value = { value = local_var:te_dg_w_agr divide = { value = local_var:te_dg_w_pop min = 1 } max = 1 } }
	set_variable = { name = te_dg_soldiers value = local_var:te_dg_w_sold }
	set_variable = { name = te_dg_bureaucrats value = local_var:te_dg_w_bur }
	set_variable = { name = te_dg_urban value = { value = local_var:te_dg_w_pop subtract = local_var:te_dg_w_rural min = 0 } }
	set_variable = { name = te_dg_urban_share value = { value = var:te_dg_urban divide = { value = local_var:te_dg_w_pop min = 1 } } }
	set_variable = { name = te_dg_fjob_share value = { value = local_var:te_dg_w_fjob divide = { value = local_var:te_dg_w_emp min = 1 } } }
	set_variable = { name = te_dg_n_lo value = local_var:te_dg_w_nlo }
	set_variable = { name = te_dg_n_mi value = local_var:te_dg_w_nmi }
	set_variable = { name = te_dg_n_up value = local_var:te_dg_w_nup }
	set_variable = { name = te_dg_y_lo value = local_var:te_dg_w_ylo }
	set_variable = { name = te_dg_y_mi value = local_var:te_dg_w_ymi }
	set_variable = { name = te_dg_y_up value = local_var:te_dg_w_yup }
	# buildings: capital in private, cooperative and state hands; ownership levels
	set_local_variable = { name = te_dg_w_priv value = 0 }
	set_local_variable = { name = te_dg_w_self value = 0 }
	set_local_variable = { name = te_dg_w_ctry value = 0 }
	set_local_variable = { name = te_dg_w_own value = 0 }
	every_scope_building = {
		if = {
			limit = { te_demog_is_capital_building = yes }
			change_local_variable = { name = te_dg_w_priv add = te_demog_building_private_levels }
			change_local_variable = { name = te_dg_w_self add = te_demog_building_self_levels }
			change_local_variable = { name = te_dg_w_ctry add = te_demog_building_country_levels }
		}
		else_if = {
			limit = { te_demog_is_ownership_building = yes }
			change_local_variable = { name = te_dg_w_own add = level }
		}
	}
	set_variable = { name = te_dg_lv_priv value = local_var:te_dg_w_priv }
	set_variable = { name = te_dg_lv_self value = local_var:te_dg_w_self }
	set_variable = { name = te_dg_lv_ctry value = local_var:te_dg_w_ctry }
	set_variable = { name = te_dg_lv_own value = local_var:te_dg_w_own }
	te_demog_state_gini = yes
}
```

  The state's Gini (§4.1) from the three strata groups, sorted by income per head (lower < middle < upper is not
  guaranteed, so sort in script: compare per-head incomes and order the three before the formula). Put it in
  `te_demog_wealth_effects.txt` (created here, extended in Task 11) as `te_demog_state_gini`, writing
  `var:te_dg_gini` = `te_demog_k_gini_floor + te_demog_k_gini_scale × G`, clamped 0–0.9, where with groups ordered
  1, 2, 3 by income per head, shares p and cumulative income shares S, G = 1 − Σ p_k (S_k + S_{k−1})
  (`demographics_model.grouped_gini`). Write the three orderings that can occur (lower lowest, middle lowest, upper
  lowest) as an `if`/`else_if` chain on the per-head incomes, each computing G with its order; a group of no people
  contributes nothing (p = 0).

- [ ] **Step 4: Inheritance's handover.**
  - `te_inheritance_effects.txt:198`: `value = te_inh_agrarian_share_value` → `value = var:te_dg_agr_share`.
  - Delete `te_inh_agrarian_share_value` (`te_inheritance_values.txt:135-152`); its comment block moves to the walk's
    header ("Peasants + Farmers over the state's population; probe-checked, London 0.174").
  - Delete the `on_yearly_pulse_state` declaration and `te_inh_state_yearly_on_action` from
    `te_inheritance_on_actions.txt:50-60`; leave a one-line comment pointing to `te_demog_state_yearly`.

- [ ] **Step 5: The orchestrator and its hook.** In `te_demog_effects.txt`:

```
# THIS = a state, on its yearly pulse (a different day per state, spec §11.3).
# The walks and Wealth Concentration run whatever the rule; the census only
# when te_demog_cohorts_run. Tasks 8 and 11 add their calls here.
te_demog_state_yearly = {
	te_demog_walks = yes
	te_inh_refresh_rural_effects = yes
}
```

  `common/on_actions/te_demog_on_actions.txt` (BOM; same header style as `te_inheritance_on_actions.txt`):

```
on_yearly_pulse_state = {
	on_actions = {
		te_demog_state_yearly_on_action
	}
}

te_demog_state_yearly_on_action = {
	effect = {
		te_demog_state_yearly = yes
	}
}
```

- [ ] **Step 6: Run the tests and reload**

Run: `python3 -m unittest test_demographics_registry -v && python3 scripts/format_paradox_tabs.py --check common/scripted_effects/te_demog_*.txt common/script_values/te_demog_values.txt common/on_actions/te_demog_on_actions.txt`
Expected: OK. `POST /reload`: no `warnings` naming `te_demog`, `te_inh` or `script_argument`; the
`effect_trigger_validity_audit` accepts `workplace`, `strata`, `is_government_funded`.

- [ ] **Step 7: Commit**

```bash
git add common/scripted_effects/te_demog_effects.txt common/scripted_effects/te_demog_wealth_effects.txt common/script_values/te_demog_values.txt common/on_actions/te_demog_on_actions.txt common/scripted_effects/te_inheritance_effects.txt common/script_values/te_inheritance_values.txt common/on_actions/te_inheritance_on_actions.txt test_demographics_registry.py
git commit -m "Demographics: the yearly pop and building walks; inheritance reads their agrarian share"
```

### Task 8: The cohort step and the seed

The script twin of `demographics_model.seed` and `step`. Read Task 2's `step` and `seed` first: the order of
operations below is theirs, so `demographics_harness.py replay` can check an in-game step (Task 15).

**Files:**
- Modify: `common/scripted_effects/te_demog_effects.txt`, `common/script_values/te_demog_values.txt`,
  `common/on_actions/te_demog_on_actions.txt`, `test_demographics_registry.py`
- Create: `events/te_demog_events.txt` (one hidden dispatch event)

**Interfaces:**
- Consumes: Task 6's generated effects and values; Task 7's walk variables.
- Produces: `te_demog_prepare`, `te_demog_seed`, `te_demog_step`, `te_demog_slot_p1/_p2`, `te_demog_slot`,
  `te_demog_age_slot`, `te_demog_fold_slot`, `te_demog_seed_p1/_p2`, `te_demog_seed_slot`, `te_demog_age_boundaries`,
  `te_demog_lt_group`, `te_demog_lt_sex`, `te_demog_lt_finish`, `te_demog_step_finish`, `te_demog_state_figures`.
  State variables: `te_dg_f<k>`, `te_dg_m<k>` (k 0–149; people, unscaled), `te_dg_pf`, `te_dg_pm`, `te_dg_pa` (pool
  and its mean age), `te_dg_scale`, `te_dg_people`, `te_dg_raw`, `te_dg_year`, `te_dg_pop_last`, `te_dg_bf<b>`,
  `te_dg_bm<b>` (b 0–17, scaled people), `te_dg_cf<c>`, `te_dg_cm<c>` (c 0–4), `te_dg_m1840`, `te_dg_f1840`,
  `te_dg_births`, `te_dg_deaths`, `te_dg_e0`, `te_dg_e0f`, `te_dg_e0m`, `te_dg_e65`, `te_dg_imr`, `te_dg_tfr`,
  `te_dg_means`, `te_dg_desired`, `te_dg_m_inf`, `te_dg_m_ext`, `te_dg_m_chr`, `te_dg_m_mat`, `te_dg_m_work`
  (the multipliers, for the panel and the country average). Task 9 fills the flow locals (`te_dg_war_ff`,
  `te_dg_war_fm`, `te_dg_kill`, `te_dg_mig_in`, `te_dg_mig_out`, `te_dg_pf<c>`, `te_dg_pm<c>`); this task sets them
  to zero so the step runs without flows.

- [ ] **Step 1: Failing tests.** Add to `test_demographics_registry.py`:

```python
class TestStep(unittest.TestCase):
    def test_orchestrator_branches(self):
        """Seed when there is no census, a gap of more than a year or an emptied ring;
        step once a year; nothing on a second pulse in the same year (Review Focus 3)."""
        body = _block(_text(EFFECTS), "te_demog_state_yearly")
        self.assertIn("te_demog_cohorts_run = yes", body)
        self.assertIn("te_demog_seed = yes", body)
        self.assertIn("te_demog_step = yes", body)
        self.assertIn("te_demog_year_gap > 1", body)
        self.assertIn("te_demog_year_gap = 1", body)

    def test_every_cohort_entry_point_is_gated(self):
        """Review Focus 5: nothing writes a cohort without te_demog_cohorts_run."""
        text = _text(EFFECTS)
        for caller in ("te_demog_state_yearly", "te_demog_country_game_start"):
            body = _block(text, caller)
            for entry in ("te_demog_seed = yes", "te_demog_step = yes"):
                if entry in body:
                    gate = body.rfind("te_demog_cohorts_run = yes", 0, body.index(entry))
                    self.assertNotEqual(gate, -1, f"{caller}: {entry} before the gate")

    def test_fold_writes_the_births(self):
        body = _block(_text(EFFECTS), "te_demog_fold_slot")
        self.assertIn("name = te_dg_f$S$", body)
        self.assertIn("local_var:te_dg_births", body)

    def test_slot_skips_empty_slots_but_keeps_counting_ages(self):
        body = _block(_text(EFFECTS), "te_demog_slot")
        self.assertIn("has_variable = te_dg_f$S$", body)
        self.assertGreater(body.index("change_local_variable = { name = te_dg_age add = 1 }"),
                           body.index("has_variable = te_dg_f$S$"))
```

  Run them: FAIL.

- [ ] **Step 2: The values** (append to `te_demog_values.txt`):

```
# State scope: years since the last step (te_dg_year), 0 before the first.
te_demog_year_gap = {
	value = 0
	if = {
		limit = { has_variable = te_dg_year }
		value = te_demog_year
		subtract = var:te_dg_year
	}
}

# The open slot this year: year mod 150 (spec §1).
te_demog_open_slot = {
	value = te_demog_year
	modulo = 150
}

# State scope: desired fertility as a factor (spec §2.3): education x child survival x urban life.
te_demog_desired = {
	value = 1
	multiply = {
		value = var:te_dg_lit
		multiply = te_demog_k_education_weight
		multiply = -1
		add = 1
	}
	multiply = {
		value = var:te_dg_e0
		subtract = 30
		divide = 50
		min = 0
		max = 1
		multiply = te_demog_k_survival_weight
		multiply = -1
		add = 1
	}
	multiply = {
		value = var:te_dg_urban_share
		multiply = te_demog_k_urban_weight
		multiply = -1
		add = 1
	}
}

# State scope: children per woman = wealth x (1 - means x (1 - desired)) (spec §2.3).
te_demog_tfr = {
	value = 1
	subtract = var:te_dg_desired
	multiply = var:te_dg_means
	multiply = -1
	add = 1
	multiply = var:te_dg_wtfr
}
```

- [ ] **Step 3: Prepare, the life table's bodies, the seed.** In `te_demog_effects.txt`:

```
# THIS = a state. The year's rates: cause multipliers into locals (generated
# values), the life table, then fertility (it reads this year's e0).
te_demog_prepare = {
	set_local_variable = { name = te_dg_m_inf value = te_demog_mult_infection }
	set_local_variable = { name = te_dg_m_ext value = te_demog_mult_external }
	set_local_variable = { name = te_dg_m_chr value = te_demog_mult_chronic }
	set_local_variable = { name = te_dg_mmr value = te_demog_mult_maternal }
	set_local_variable = { name = te_dg_fws value = te_demog_female_work_share }
	set_local_variable = { name = te_dg_m_work_f value = { value = te_demog_mult_work multiply = local_var:te_dg_fws multiply = 2 } }
	set_local_variable = { name = te_dg_m_work_m value = { value = 1 subtract = local_var:te_dg_fws multiply = te_demog_mult_work multiply = 2 } }
	set_variable = { name = te_dg_m_inf value = local_var:te_dg_m_inf }
	set_variable = { name = te_dg_m_ext value = local_var:te_dg_m_ext }
	set_variable = { name = te_dg_m_chr value = local_var:te_dg_m_chr }
	set_variable = { name = te_dg_m_mat value = local_var:te_dg_mmr }
	set_variable = { name = te_dg_m_work value = te_demog_mult_work }
	te_demog_life_table = yes
	set_variable = { name = te_dg_means value = te_demog_means }
	set_variable = { name = te_dg_desired value = te_demog_desired }
	set_variable = { name = te_dg_tfr value = te_demog_tfr }
	set_local_variable = { name = te_dg_tfr value = var:te_dg_tfr }
}

# One age group of the life table for both sexes ($N$ years wide; $FERTILE$ adds
# the group to the net reproduction rate's sum). demographics_model.life_table.
te_demog_lt_group = {
	te_demog_lt_sex = { SEX = f N = $N$ FERTILE = $FERTILE$ }
	te_demog_lt_sex = { SEX = m N = $N$ FERTILE = no }
}

# te_dg_l<SEX> = survivors (radix 100,000), te_dg_py<SEX> = person-years so far.
te_demog_lt_sex = {
	set_local_variable = { name = te_dg_q value = { value = local_var:te_dg_q$SEX$ divide = 100000 } }
	set_local_variable = { name = te_dg_p value = { value = 1 subtract = local_var:te_dg_q } }
	set_local_variable = { name = te_dg_pn value = 1 }
	while = {
		count = $N$
		change_local_variable = { name = te_dg_pn multiply = local_var:te_dg_p }
	}
	# survivors summed over the group's single years: l x (1 - p^n) / q, or l x n
	set_local_variable = { name = te_dg_lsum value = { value = local_var:te_dg_l$SEX$ multiply = $N$ } }
	if = {
		limit = { local_var:te_dg_q > 0 }
		set_local_variable = {
			name = te_dg_lsum
			value = {
				value = 1
				subtract = local_var:te_dg_pn
				divide = { value = local_var:te_dg_q min = 0.00001 }
				multiply = local_var:te_dg_l$SEX$
			}
		}
	}
	# person-years count each year at mid-year: the sum x (1 - q / 2)
	change_local_variable = {
		name = te_dg_py$SEX$
		add = { value = local_var:te_dg_q multiply = -0.5 add = 1 multiply = local_var:te_dg_lsum }
	}
	if = {
		limit = { always = $FERTILE$ }
		change_local_variable = { name = te_dg_nrr_sum add = { value = local_var:te_dg_lsum multiply = local_var:te_dg_asfr } }
	}
	change_local_variable = { name = te_dg_l$SEX$ multiply = local_var:te_dg_pn }
}

# After the last group: e0, e65 (radix 100,000), and the panel's figures.
te_demog_lt_finish = {
	set_variable = { name = te_dg_e0f value = { value = local_var:te_dg_pyf divide = 100000 } }
	set_variable = { name = te_dg_e0m value = { value = local_var:te_dg_pym divide = 100000 } }
	set_variable = { name = te_dg_e0 value = { value = var:te_dg_e0f add = var:te_dg_e0m multiply = 0.5 } }
	set_variable = {
		name = te_dg_e65
		value = {
			value = {
				value = local_var:te_dg_pyf
				subtract = local_var:te_dg_py65f
				divide = { value = local_var:te_dg_l65f min = 1 }
			}
			add = {
				value = local_var:te_dg_pym
				subtract = local_var:te_dg_py65m
				divide = { value = local_var:te_dg_l65m min = 1 }
			}
			multiply = 0.5
		}
	}
}
```

  Check `te_demog_lt_sex` against `demographics_model.life_table` and `nrr` before going on: survivors start at
  100,000 (`te_demog_life_table` sets them), person-years per group are `l × (1 − q/2) × (1 − pⁿ)/q`, and the NRR
  sum per group is the survivors summed over its single years times the group's per-year fertility share; the seed
  then takes `NRR = sum ÷ 10¹⁰ × TFR × female births per 100,000 ÷ 100,000`.

```
# THIS = a state. A ring at the stable structure of the state's own rates
# (demographics_model.seed; spec §2.6 and design rule 5).
te_demog_seed = {
	te_demog_prepare = yes
	set_local_variable = {
		name = te_dg_nrr
		value = {
			value = local_var:te_dg_nrr_sum
			divide = 100000
			divide = 100000
			multiply = local_var:te_dg_tfr
			multiply = te_demog_k_female_births_per_100k
			divide = 100000
		}
	}
	te_demog_set_growth_factor = yes
	set_local_variable = { name = te_dg_open value = te_demog_open_slot }
	set_local_variable = { name = te_dg_age value = 0 }
	set_local_variable = { name = te_dg_g value = 0 }
	te_demog_enter_group = yes
	set_local_variable = { name = te_dg_lsf value = 100000 }
	set_local_variable = { name = te_dg_lsm value = 100000 }
	set_local_variable = { name = te_dg_dpow value = 1 }
	te_demog_reset_accumulators = yes
	te_demog_no_flows = yes
	set_variable = { name = te_dg_pf value = 0 }
	set_variable = { name = te_dg_pm value = 0 }
	set_variable = { name = te_dg_pa value = 150 }
	te_demog_seed_sweep = yes
	te_demog_close_accumulators = yes
	set_variable = { name = te_dg_births value = 0 }
	set_variable = { name = te_dg_deaths value = 0 }
	te_demog_set_scale = yes
}

te_demog_seed_p1 = {
	if = {
		limit = { NOT = { local_var:te_dg_open < $S$ } }
		te_demog_seed_slot = { S = $S$ }
	}
}

te_demog_seed_p2 = {
	if = {
		limit = { local_var:te_dg_open < $S$ }
		te_demog_seed_slot = { S = $S$ }
	}
}

# Age local_var:te_dg_age (0-149) in slot $S$: survivors x growth factor^age.
te_demog_seed_slot = {
	te_demog_age_boundaries = yes
	set_variable = {
		name = te_dg_f$S$
		value = { value = local_var:te_dg_lsf multiply = local_var:te_dg_dpow multiply = te_demog_k_female_births_per_100k divide = 100000 }
	}
	set_variable = {
		name = te_dg_m$S$
		value = { value = local_var:te_dg_lsm multiply = local_var:te_dg_dpow multiply = te_demog_k_male_births_per_100k divide = 100000 }
	}
	te_demog_accumulate_slot = { S = $S$ }
	if = {
		limit = { local_var:te_dg_age = local_var:te_dg_next_group }
		change_local_variable = { name = te_dg_g add = 1 }
		te_demog_enter_group = yes
	}
	change_local_variable = { name = te_dg_lsf multiply = { value = local_var:te_dg_qf divide = 100000 multiply = -1 add = 1 } }
	change_local_variable = { name = te_dg_lsm multiply = { value = local_var:te_dg_qm divide = 100000 multiply = -1 add = 1 } }
	change_local_variable = { name = te_dg_dpow multiply = local_var:te_dg_d }
	change_local_variable = { name = te_dg_age add = 1 }
}
```

  Note the seed's group check uses the **age**, and the step's (below) the **rate age** (age − 1): in the seed the
  people of age a are written before the year at age a is survived; in the step the people now aged a lived through
  age a − 1 this year. Both are `demographics_model`'s order.

- [ ] **Step 4: The shared accumulators.** Bands are 0–4 … 80–84 and 85+; classes start at 15, 18, 36 and 60.

```
# Zero the running sums before a sweep.
te_demog_reset_accumulators = {
	set_local_variable = { name = te_dg_band value = 0 }
	set_local_variable = { name = te_dg_next_band value = 5 }
	set_local_variable = { name = te_dg_acc_bf value = 0 }
	set_local_variable = { name = te_dg_acc_bm value = 0 }
	set_local_variable = { name = te_dg_cls value = 0 }
	set_local_variable = { name = te_dg_next_class value = 15 }
	set_local_variable = { name = te_dg_acc_cf value = 0 }
	set_local_variable = { name = te_dg_acc_cm value = 0 }
	set_local_variable = { name = te_dg_acc_f1840 value = 0 }
	set_local_variable = { name = te_dg_acc_m1840 value = 0 }
	set_local_variable = { name = te_dg_raw value = 0 }
	set_local_variable = { name = te_dg_births value = 0 }
	set_local_variable = { name = te_dg_deaths value = 0 }
}

# Before the people of local_var:te_dg_age are added: close the band or class
# that ended at the previous age.
te_demog_age_boundaries = {
	if = {
		limit = { local_var:te_dg_age = local_var:te_dg_next_band }
		te_demog_flush_band = yes
		change_local_variable = { name = te_dg_band add = 1 }
		set_local_variable = { name = te_dg_acc_bf value = 0 }
		set_local_variable = { name = te_dg_acc_bm value = 0 }
		change_local_variable = { name = te_dg_next_band add = 5 }
		if = {
			limit = { local_var:te_dg_band >= 17 }
			set_local_variable = { name = te_dg_next_band value = 999 }
		}
	}
	if = {
		limit = { local_var:te_dg_age = local_var:te_dg_next_class }
		te_demog_flush_class = yes
		change_local_variable = { name = te_dg_cls add = 1 }
		set_local_variable = { name = te_dg_acc_cf value = 0 }
		set_local_variable = { name = te_dg_acc_cm value = 0 }
		if = {
			limit = { local_var:te_dg_cls = 1 }
			set_local_variable = { name = te_dg_next_class value = 18 }
		}
		else_if = {
			limit = { local_var:te_dg_cls = 2 }
			set_local_variable = { name = te_dg_next_class value = 36 }
		}
		else_if = {
			limit = { local_var:te_dg_cls = 3 }
			set_local_variable = { name = te_dg_next_class value = 60 }
		}
		else = {
			set_local_variable = { name = te_dg_next_class value = 999 }
		}
		te_demog_enter_class = yes
	}
}

# Slot $S$'s stored people into the running sums.
te_demog_accumulate_slot = {
	change_local_variable = { name = te_dg_raw add = { value = var:te_dg_f$S$ add = var:te_dg_m$S$ } }
	change_local_variable = { name = te_dg_acc_bf add = var:te_dg_f$S$ }
	change_local_variable = { name = te_dg_acc_bm add = var:te_dg_m$S$ }
	change_local_variable = { name = te_dg_acc_cf add = var:te_dg_f$S$ }
	change_local_variable = { name = te_dg_acc_cm add = var:te_dg_m$S$ }
	if = {
		limit = {
			local_var:te_dg_age >= 18
			local_var:te_dg_age <= 40
		}
		change_local_variable = { name = te_dg_acc_f1840 add = var:te_dg_f$S$ }
		change_local_variable = { name = te_dg_acc_m1840 add = var:te_dg_m$S$ }
	}
}

# After a sweep: the pool goes to 85+ and the oldest class, then both close.
te_demog_close_accumulators = {
	change_local_variable = { name = te_dg_acc_bf add = var:te_dg_pf }
	change_local_variable = { name = te_dg_acc_bm add = var:te_dg_pm }
	change_local_variable = { name = te_dg_acc_cf add = var:te_dg_pf }
	change_local_variable = { name = te_dg_acc_cm add = var:te_dg_pm }
	change_local_variable = { name = te_dg_raw add = { value = var:te_dg_pf add = var:te_dg_pm } }
	te_demog_flush_band = yes
	te_demog_flush_class = yes
	set_variable = { name = te_dg_f1840 value = local_var:te_dg_acc_f1840 }
	set_variable = { name = te_dg_m1840 value = local_var:te_dg_acc_m1840 }
}

# The ring to the engine's population: the factor applies to the cohorts at the
# next sweep (lazily) and to the bands, classes and 18-40 sums now.
te_demog_set_scale = {
	set_variable = { name = te_dg_raw value = local_var:te_dg_raw }
	set_local_variable = { name = te_dg_new_scale value = { value = state_population divide = { value = local_var:te_dg_raw min = 1 } } }
	set_variable = { name = te_dg_scale value = local_var:te_dg_new_scale }
	te_demog_scale_bands = yes
	change_variable = { name = te_dg_f1840 multiply = local_var:te_dg_new_scale }
	change_variable = { name = te_dg_m1840 multiply = local_var:te_dg_new_scale }
	set_variable = { name = te_dg_people value = state_population }
	set_variable = { name = te_dg_pop_last value = state_population }
	set_variable = { name = te_dg_year value = te_demog_year }
	te_demog_state_figures = yes
}
```

  The seed empties the pool before `te_demog_close_accumulators` reads it, and calls `te_demog_no_flows` because
  `te_demog_age_boundaries` runs `te_demog_enter_class`, which reads the flow locals:

```
# No war dead, kills or migrants this sweep (the seed; Task 8's step until Task 9).
te_demog_no_flows = {
	set_local_variable = { name = te_dg_war_ff value = 0 }
	set_local_variable = { name = te_dg_war_fm value = 0 }
	set_local_variable = { name = te_dg_kill value = 0 }
	set_local_variable = { name = te_dg_mig_in value = 0 }
	set_local_variable = { name = te_dg_mig_out value = 0 }
	set_local_variable = { name = te_dg_pf0 value = 0 }
	set_local_variable = { name = te_dg_pf1 value = 0 }
	set_local_variable = { name = te_dg_pf2 value = 0 }
	set_local_variable = { name = te_dg_pf3 value = 0 }
	set_local_variable = { name = te_dg_pf4 value = 0 }
	set_local_variable = { name = te_dg_pm0 value = 0 }
	set_local_variable = { name = te_dg_pm1 value = 0 }
	set_local_variable = { name = te_dg_pm2 value = 0 }
	set_local_variable = { name = te_dg_pm3 value = 0 }
	set_local_variable = { name = te_dg_pm4 value = 0 }
}
```

- [ ] **Step 5: The step.** Mirror of `demographics_model.step`:

```
# THIS = a state, once a year. Ages the ring one year (spec §2.1).
te_demog_step = {
	te_demog_prepare = yes
	te_demog_flows = yes
	set_local_variable = { name = te_dg_open value = te_demog_open_slot }
	set_local_variable = { name = te_dg_s value = var:te_dg_scale }
	set_local_variable = { name = te_dg_age value = 1 }
	set_local_variable = { name = te_dg_r value = 0 }
	set_local_variable = { name = te_dg_g value = 0 }
	te_demog_enter_group = yes
	te_demog_reset_accumulators = yes
	te_demog_enter_class = yes
	te_demog_sweep = yes
	te_demog_step_finish = yes
}

te_demog_slot_p1 = {
	if = {
		limit = { local_var:te_dg_open > $S$ }
		te_demog_slot = { S = $S$ }
	}
}

te_demog_slot_p2 = {
	if = {
		limit = { NOT = { local_var:te_dg_open > $S$ } }
		te_demog_slot = { S = $S$ }
	}
}

# The people now aged local_var:te_dg_age lived through rate age te_dg_r this year.
te_demog_slot = {
	te_demog_age_boundaries = yes
	if = {
		limit = { local_var:te_dg_r = local_var:te_dg_next_group }
		change_local_variable = { name = te_dg_g add = 1 }
		te_demog_enter_group = yes
	}
	if = {
		limit = { local_var:te_dg_age = 150 }
		te_demog_fold_slot = { S = $S$ }
	}
	else_if = {
		limit = { has_variable = te_dg_f$S$ }
		te_demog_age_slot = { S = $S$ }
	}
	change_local_variable = { name = te_dg_age add = 1 }
	change_local_variable = { name = te_dg_r add = 1 }
}

te_demog_age_slot = {
	set_local_variable = { name = te_dg_f value = { value = var:te_dg_f$S$ multiply = local_var:te_dg_s } }
	set_local_variable = { name = te_dg_m value = { value = var:te_dg_m$S$ multiply = local_var:te_dg_s } }
	# births from these women (rate ages 15-49 carry a non-zero te_dg_asfr)
	set_local_variable = {
		name = te_dg_b
		value = { value = local_var:te_dg_f multiply = local_var:te_dg_asfr divide = 100000 multiply = local_var:te_dg_tfr }
	}
	change_local_variable = { name = te_dg_births add = local_var:te_dg_b }
	# deaths, and maternal deaths per birth
	set_local_variable = {
		name = te_dg_f2
		value = {
			value = local_var:te_dg_qf
			divide = 100000
			multiply = -1
			add = 1
			multiply = local_var:te_dg_f
			subtract = { value = local_var:te_dg_b multiply = local_var:te_dg_mmr divide = 100000 }
		}
	}
	set_local_variable = {
		name = te_dg_m2
		value = { value = local_var:te_dg_qm divide = 100000 multiply = -1 add = 1 multiply = local_var:te_dg_m }
	}
	change_local_variable = {
		name = te_dg_deaths
		add = { value = local_var:te_dg_f add = local_var:te_dg_m subtract = local_var:te_dg_f2 subtract = local_var:te_dg_m2 }
	}
	# war dead: men and women aged 18-40
	if = {
		limit = {
			local_var:te_dg_age >= 18
			local_var:te_dg_age <= 40
		}
		change_local_variable = { name = te_dg_f2 multiply = { value = 1 subtract = local_var:te_dg_war_ff } }
		change_local_variable = { name = te_dg_m2 multiply = { value = 1 subtract = local_var:te_dg_war_fm } }
	}
	# known kills: every age
	change_local_variable = { name = te_dg_f2 multiply = { value = 1 subtract = local_var:te_dg_kill } }
	change_local_variable = { name = te_dg_m2 multiply = { value = 1 subtract = local_var:te_dg_kill } }
	# migration: arrivals by the profile, departures in proportion to the cohort
	change_local_variable = { name = te_dg_f2 add = local_var:te_dg_mig_add_f }
	change_local_variable = { name = te_dg_m2 add = local_var:te_dg_mig_add_m }
	if = {
		limit = { local_var:te_dg_mig_frac_f > 0 }
		change_local_variable = {
			name = te_dg_f2
			subtract = { value = local_var:te_dg_f multiply = local_var:te_dg_mig_frac_f max = { value = local_var:te_dg_f2 multiply = 0.5 } }
		}
	}
	if = {
		limit = { local_var:te_dg_mig_frac_m > 0 }
		change_local_variable = {
			name = te_dg_m2
			subtract = { value = local_var:te_dg_m multiply = local_var:te_dg_mig_frac_m max = { value = local_var:te_dg_m2 multiply = 0.5 } }
		}
	}
	set_variable = { name = te_dg_f$S$ value = { value = local_var:te_dg_f2 min = 0 } }
	set_variable = { name = te_dg_m$S$ value = { value = local_var:te_dg_m2 min = 0 } }
	te_demog_accumulate_slot = { S = $S$ }
}

# Age 150: the slot's people join the pool, which ages and dies at the last
# group's rates, and the slot takes this year's births (it is the sweep's last).
te_demog_fold_slot = {
	set_local_variable = { name = te_dg_pool value = { value = var:te_dg_pf add = var:te_dg_pm multiply = local_var:te_dg_s } }
	set_local_variable = { name = te_dg_old value = 0 }
	if = {
		limit = { has_variable = te_dg_f$S$ }
		set_local_variable = { name = te_dg_old value = { value = var:te_dg_f$S$ add = var:te_dg_m$S$ multiply = local_var:te_dg_s } }
		change_variable = { name = te_dg_pf multiply = local_var:te_dg_s }
		change_variable = { name = te_dg_pf add = { value = var:te_dg_f$S$ multiply = local_var:te_dg_s } }
		change_variable = { name = te_dg_pm multiply = local_var:te_dg_s }
		change_variable = { name = te_dg_pm add = { value = var:te_dg_m$S$ multiply = local_var:te_dg_s } }
	}
	else = {
		change_variable = { name = te_dg_pf multiply = local_var:te_dg_s }
		change_variable = { name = te_dg_pm multiply = local_var:te_dg_s }
	}
	set_variable = {
		name = te_dg_pa
		value = {
			value = var:te_dg_pa
			add = 1
			multiply = local_var:te_dg_pool
			add = { value = local_var:te_dg_old multiply = 150 }
			divide = { value = local_var:te_dg_pool add = local_var:te_dg_old min = 0.00001 }
		}
	}
	change_local_variable = {
		name = te_dg_deaths
		add = {
			value = var:te_dg_pf
			multiply = local_var:te_dg_qf
			add = { value = var:te_dg_pm multiply = local_var:te_dg_qm }
			divide = 100000
		}
	}
	change_variable = { name = te_dg_pf multiply = { value = local_var:te_dg_qf divide = 100000 multiply = -1 add = 1 } }
	change_variable = { name = te_dg_pm multiply = { value = local_var:te_dg_qm divide = 100000 multiply = -1 add = 1 } }
	set_variable = { name = te_dg_f$S$ value = { value = local_var:te_dg_births multiply = te_demog_k_female_births_per_100k divide = 100000 } }
	set_variable = { name = te_dg_m$S$ value = { value = local_var:te_dg_births multiply = te_demog_k_male_births_per_100k divide = 100000 } }
}

# After the sweep: newborns into band 0 and class 0, then the scale.
te_demog_step_finish = {
	te_demog_close_accumulators = yes
	set_local_variable = { name = te_dg_bf_new value = { value = local_var:te_dg_births multiply = te_demog_k_female_births_per_100k divide = 100000 } }
	set_local_variable = { name = te_dg_bm_new value = { value = local_var:te_dg_births multiply = te_demog_k_male_births_per_100k divide = 100000 } }
	change_variable = { name = te_dg_bf0 add = local_var:te_dg_bf_new }
	change_variable = { name = te_dg_bm0 add = local_var:te_dg_bm_new }
	change_variable = { name = te_dg_cf0 add = local_var:te_dg_bf_new }
	change_variable = { name = te_dg_cm0 add = local_var:te_dg_bm_new }
	change_local_variable = { name = te_dg_raw add = local_var:te_dg_births }
	set_variable = { name = te_dg_births value = local_var:te_dg_births }
	set_variable = { name = te_dg_deaths value = local_var:te_dg_deaths }
	te_demog_set_scale = yes
}
```

  `te_dg_births` and `te_dg_deaths` are people this year (the cohorts were scaled to last year's population before
  aging). Until Task 9, `te_demog_flows = { te_demog_no_flows = yes }`; Task 9 replaces its body. In the step,
  `te_demog_flows` runs **before** `te_demog_reset_accumulators` and the reset leaves the flow locals alone.

- [ ] **Step 6: The orchestrator's census branch, the figures and the game start.** Extend `te_demog_state_yearly`:

```
te_demog_state_yearly = {
	te_demog_walks = yes
	te_inh_refresh_rural_effects = yes
	if = {
		limit = { te_demog_cohorts_run = yes }
		if = {
			limit = {
				OR = {
					NOT = { te_demog_has_census = yes }
					te_demog_year_gap > 1
					AND = {
						var:te_dg_raw < 1
						state_population > 0
					}
				}
			}
			te_demog_seed = yes
		}
		else_if = {
			limit = { te_demog_year_gap = 1 }
			te_demog_step = yes
		}
	}
}
```

  `te_demog_state_figures` (state) runs `te_demog_band_figures = { B = te_dg_b }` and stores, keeping last year's
  value of each in a `te_dg_prev_<name>` first (the panel's trend arrows): `te_dg_median` (the local),
  `te_dg_young_share`, `te_dg_working_share`, `te_dg_old_share` (each ÷ total, floored divisor),
  `te_dg_dependency` ((young + old) ÷ working), `te_dg_sex_balance` (men per 100 women 20–59),
  `te_dg_cbr` and `te_dg_cdr` (births and deaths per 1,000), `te_dg_w1549` (women 15–49, for the country's TFR
  weights).

  Game start: in `te_demog_on_actions.txt` add `on_game_started = { on_actions = { te_demog_on_game_started } }` and
  `te_demog_on_game_started = { effect = { every_country = { trigger_event = { id = te_demog_events.1 } } } }` (the
  dispatch `te_inh_on_game_started` uses, `te_inheritance_on_actions.txt:13-27`: `on_game_started` has no ROOT).
  `events/te_demog_events.txt`: `namespace = te_demog_events`, event `.1` a hidden country event shaped like
  `inheritance_events.1` (`events/inheritance_events.txt:33-44`) whose `immediate` is `te_demog_country_game_start
  = yes`:

```
# THIS = a country at game start: walk and seed every state, so 1836 opens with a census.
te_demog_country_game_start = {
	every_scope_state = {
		te_demog_walks = yes
		if = {
			limit = { te_demog_cohorts_run = yes }
			te_demog_seed = yes
		}
	}
}
```

  Task 10 appends the country's figures to it.

  France's early fertility transition (§2.6): in `common/history/extra_history.txt`'s `GLOBAL = {` block, add
  `c:FRA ?= { set_variable = { name = te_dg_means_floor value = 0.8 } }` with a comment naming §2.6. The generated
  `te_demog_means` reads it as a floor (`min = owner.var:te_dg_means_floor`), so France's means start at 0.8 and
  later technology can raise them; `demographics_model.means` treats `means_override` the same way.

- [ ] **Step 7: Tests, generator check and reload**

Run: `python3 -m unittest test_demographics_registry test_gen_demographics -v && python3 scripts/format_paradox_tabs.py --check common/scripted_effects/te_demog_effects.txt common/script_values/te_demog_values.txt events/te_demog_events.txt`
Expected: OK. `POST /reload`: no `script_argument_audit`, `empty_effect_audit`, `orphaned_event_audit` or
`event_image_audit` finding for `te_demog`; if `event_image_audit` flags the hidden event, copy
`inheritance_events.1`'s exemption.

- [ ] **Step 8: Commit**

```bash
git add common/scripted_effects/te_demog_effects.txt common/script_values/te_demog_values.txt common/on_actions/te_demog_on_actions.txt events/te_demog_events.txt test_demographics_registry.py
git commit -m "Demographics: the yearly cohort step, the stable-population seed and the life table"
```

### Task 9: Flows — war dead, known kills, the migration residual and its profile

**Files:**
- Modify: `common/scripted_effects/te_demog_effects.txt` (replace `te_demog_flows`; add the country effects),
  `common/script_values/te_demog_values.txt`, `common/on_actions/te_demog_on_actions.txt`,
  `common/scripted_effects/extra_effects.txt` (`nuclear_industrial_strike` `:491`, `nuclear_tactical_strike` `:758`),
  `common/on_actions/extra_on_actions.txt` (the two Violent Hostility kills, `:1616` and `:1672`),
  `test_demographics_registry.py`

**Interfaces:**
- Consumes: Task 7's `te_dg_eb`, `te_dg_ed`, `te_dg_soldiers`, `te_dg_fjob_share`; Task 8's `te_dg_pop_last`,
  `te_dg_people`, `te_dg_m1840`, `te_dg_f1840`, local `te_dg_fws`; Task 6's `te_demog_set_profile`,
  `te_demog_family_transport`, `te_demog_k_*`.
- Produces: `te_demog_flows` (state), `te_demog_note_kills = { VALUE }` (state), `te_demog_country_monthly`,
  `te_demog_country_yearly`, `te_demog_share_war_dead` (country), values `te_demog_war_dead_root` (war scope),
  `te_demog_crisis` (state). Variables: country `te_dg_war_seen`, `te_dg_war_year`; state `te_dg_war_in`,
  `te_dg_kills_in`, `te_dg_net_migration`, `te_dg_inflow_years`.

- [ ] **Step 1: Failing tests** (add to `test_demographics_registry.py`):

```python
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

    def test_residual_ignores_noise(self):
        body = _block(_text(EFFECTS), "te_demog_flows")
        self.assertIn("te_demog_k_residual_noise_share", body)
```

- [ ] **Step 2: Values.** Append to `te_demog_values.txt`:

```
# War scope, on the owner's pulse: the owner's dead in this war so far (probe Q4).
te_demog_war_dead_root = {
	value = "num_country_dead(root)"
}

# State scope: how much of a migration is refugees (spec §2.5): devastation,
# turmoil and the owner being at war. The bareword reads are checked in game by
# te_debug_demog.1 option b's census line (Owner checks).
te_demog_crisis = {
	value = 0
	add = devastation
	add = turmoil
	if = {
		limit = { owner = { is_at_war = yes } }
		add = te_demog_k_crisis_at_war
	}
	min = 0
	max = 1
}
```

- [ ] **Step 3: The state's flows.** Replace `te_demog_flows`:

```
# THIS = a state, at the start of its step. Sets the step's flow locals
# (demographics_model.step's war_dead, kills, migration and profile).
te_demog_flows = {
	# war dead the owner shared out on 31 December
	set_local_variable = { name = te_dg_war value = 0 }
	if = {
		limit = { has_variable = te_dg_war_in }
		set_local_variable = { name = te_dg_war value = var:te_dg_war_in }
		remove_variable = te_dg_war_in
	}
	set_local_variable = {
		name = te_dg_war_fm
		value = { value = local_var:te_dg_war multiply = te_demog_k_war_male_share divide = { value = var:te_dg_m1840 min = 1 } max = 0.5 }
	}
	set_local_variable = {
		name = te_dg_war_ff
		value = {
			value = 1
			subtract = te_demog_k_war_male_share
			multiply = local_var:te_dg_war
			divide = { value = var:te_dg_f1840 min = 1 }
			max = 0.5
		}
	}
	# the mod's own kills since the last step (te_demog_note_kills)
	set_local_variable = { name = te_dg_kills value = 0 }
	if = {
		limit = { has_variable = te_dg_kills_in }
		set_local_variable = { name = te_dg_kills value = var:te_dg_kills_in }
		remove_variable = te_dg_kills_in
	}
	set_local_variable = { name = te_dg_kill value = { value = local_var:te_dg_kills divide = { value = var:te_dg_people min = 1 } max = 0.9 } }
	# the residual: the change less the engine's own births and deaths, war dead and kills
	set_local_variable = {
		name = te_dg_mig
		value = {
			value = state_population
			subtract = var:te_dg_pop_last
			subtract = var:te_dg_eb
			add = var:te_dg_ed
			add = local_var:te_dg_war
			add = local_var:te_dg_kills
		}
	}
	set_local_variable = { name = te_dg_noise value = { value = var:te_dg_people multiply = te_demog_k_residual_noise_share } }
	set_local_variable = { name = te_dg_neg_noise value = { value = local_var:te_dg_noise multiply = -1 } }
	if = {
		limit = {
			local_var:te_dg_mig < local_var:te_dg_noise
			local_var:te_dg_mig > local_var:te_dg_neg_noise
		}
		set_local_variable = { name = te_dg_mig value = 0 }
	}
	set_variable = { name = te_dg_net_migration value = local_var:te_dg_mig }
	set_local_variable = { name = te_dg_mig_in value = { value = local_var:te_dg_mig min = 0 } }
	set_local_variable = { name = te_dg_mig_out value = { value = local_var:te_dg_mig multiply = -1 min = 0 } }
	if = {
		limit = { NOT = { has_variable = te_dg_inflow_years } }
		set_variable = { name = te_dg_inflow_years value = 0 }
	}
	# the profile (demographics_model.migrant_profile)
	set_local_variable = { name = te_dg_refugee value = te_demog_crisis }
	set_local_variable = { name = te_dg_rights value = { value = local_var:te_dg_fws divide = { value = te_demog_k_full_female_work_share min = 0.01 } } }
	set_local_variable = {
		name = te_dg_family
		value = {
			value = te_demog_k_family_base
			add = te_demog_family_transport
			add = { value = local_var:te_dg_rights multiply = te_demog_k_family_rights_weight }
			add = { value = var:te_dg_inflow_years multiply = te_demog_k_chain_step max = te_demog_k_chain_cap }
			max = { value = 1 subtract = local_var:te_dg_refugee }
			min = 0
		}
	}
	set_local_variable = { name = te_dg_labour value = { value = 1 subtract = local_var:te_dg_family subtract = local_var:te_dg_refugee min = 0 } }
	set_local_variable = {
		name = te_dg_labour_f
		value = {
			value = te_demog_k_labour_female_max
			subtract = te_demog_k_labour_female_min
			multiply = var:te_dg_fjob_share
			multiply = local_var:te_dg_rights
			add = te_demog_k_labour_female_min
			min = te_demog_k_labour_female_min
			max = te_demog_k_labour_female_max
		}
	}
	te_demog_set_profile = yes
	# chain migration: consecutive years of net inflow, counted after the profile
	# read last year's count (the model's inp.inflow_years)
	if = {
		limit = { local_var:te_dg_mig > 0 }
		change_variable = { name = te_dg_inflow_years add = 1 }
	}
	else = {
		set_variable = { name = te_dg_inflow_years value = 0 }
	}
}
```

  `te_dg_fws` is set by `te_demog_prepare`, which runs before `te_demog_flows` in `te_demog_step`.

- [ ] **Step 4: Known kills.** In `te_demog_effects.txt`:

```
# THIS = a state: people the mod's own script killed here, of every age and both
# sexes (spec §2.5 "Known kills"); the next step takes them out of the cohorts
# instead of reading them as emigrants.
te_demog_note_kills = {
	if = {
		limit = { NOT = { has_variable = te_dg_kills_in } }
		set_variable = { name = te_dg_kills_in value = 0 }
	}
	change_variable = { name = te_dg_kills_in add = $VALUE$ }
}
```

  Call sites:
  - `nuclear_industrial_strike` (`extra_effects.txt:491`), after its `set_variable = { name =
    nuclear_strike_killed_population … }`: `te_demog_note_kills = { VALUE = var:nuclear_strike_killed_population }`.
  - `nuclear_tactical_strike` (`:758`), after the `every_scope_pop` that adds the soldiers to
    `tactical_nuclear_strike_killed_population` and before the first `kill_population_percent_in_state`:
    `te_demog_note_kills = { VALUE = var:tactical_nuclear_strike_killed_population }`.
  - Violent Hostility, both kills (`extra_on_actions.txt:1616`, percent 0.1, and `:1672`, percent 0.02). Inside
    `scope:curr_state = {`, before `kill_population_percent_in_state`, with the same percent as the kill below it:

```
							set_local_variable = { name = te_dg_vh value = 0 }
							every_scope_pop = {
								limit = { culture = scope:curr_culture }
								change_local_variable = { name = te_dg_vh add = total_size }
							}
							te_demog_note_kills = { VALUE = { value = local_var:te_dg_vh multiply = 0.1 } }
```

- [ ] **Step 5: The country's war dead.** In `te_demog_effects.txt`:

```
# THIS = a country, monthly. The dead of every war it is in, summed; the year's
# total gains the rise. A war that ends drops out of the sum, so the change is
# floored at zero and loses at most that month of any other war's dead.
te_demog_country_monthly = {
	set_local_variable = { name = te_dg_dead value = 0 }
	every_scope_war = {
		change_local_variable = { name = te_dg_dead add = te_demog_war_dead_root }
	}
	if = {
		limit = { NOT = { has_variable = te_dg_war_seen } }
		set_variable = { name = te_dg_war_seen value = 0 }
		set_variable = { name = te_dg_war_year value = 0 }
	}
	change_variable = {
		name = te_dg_war_year
		add = {
			value = local_var:te_dg_dead
			subtract = var:te_dg_war_seen
			min = 0
		}
	}
	set_variable = { name = te_dg_war_seen value = local_var:te_dg_dead }
}

# THIS = a country on 31 December: the year's war dead go to its states by their
# share of its soldiers (by people when it has none); each state's next step takes
# its share out of its men and women aged 18-40.
te_demog_share_war_dead = {
	if = {
		limit = {
			has_variable = te_dg_war_year
			var:te_dg_war_year > 0
		}
		set_local_variable = { name = te_dg_dead value = var:te_dg_war_year }
		set_local_variable = { name = te_dg_sold value = 0 }
		set_local_variable = { name = te_dg_ppl value = 0 }
		every_scope_state = {
			limit = { te_demog_has_census = yes }
			change_local_variable = { name = te_dg_sold add = var:te_dg_soldiers }
			change_local_variable = { name = te_dg_ppl add = var:te_dg_people }
		}
		every_scope_state = {
			limit = { te_demog_has_census = yes }
			if = {
				limit = { NOT = { has_variable = te_dg_war_in } }
				set_variable = { name = te_dg_war_in value = 0 }
			}
			if = {
				limit = { local_var:te_dg_sold >= 1 }
				change_variable = { name = te_dg_war_in add = { value = var:te_dg_soldiers divide = { value = local_var:te_dg_sold min = 1 } multiply = local_var:te_dg_dead } }
			}
			else = {
				change_variable = { name = te_dg_war_in add = { value = var:te_dg_people divide = { value = local_var:te_dg_ppl min = 1 } multiply = local_var:te_dg_dead } }
			}
		}
		set_variable = { name = te_dg_war_year value = 0 }
	}
}

# THIS = a country on 31 December. Tasks 10-12 add to it.
te_demog_country_yearly = {
	if = {
		limit = { te_demog_cohorts_run = yes }
		te_demog_share_war_dead = yes
	}
}
```

  Hooks in `te_demog_on_actions.txt`: `on_monthly_pulse_country = { on_actions = { te_demog_country_monthly_on_action } }`
  with `effect = { te_demog_country_monthly = yes }` — **not** gated by the rule, because Task 11's war shock reads
  the same total; and `on_yearly_pulse_country = { on_actions = { te_demog_country_yearly_on_action } }` with
  `effect = { te_demog_country_yearly = yes }`.

- [ ] **Step 6: Tests and reload**

Run: `python3 -m unittest test_demographics_registry -v && python3 scripts/format_paradox_tabs.py --check common/scripted_effects/te_demog_effects.txt common/scripted_effects/extra_effects.txt common/on_actions/extra_on_actions.txt common/on_actions/te_demog_on_actions.txt`
Expected: OK. `POST /reload`: no `script_argument_audit` finding for `te_demog_note_kills` (it names `$VALUE$`
and every call passes `VALUE`), no `prev_scope_audit` finding at the Violent Hostility sites.

- [ ] **Step 7: Commit**

```bash
git add common/scripted_effects/te_demog_effects.txt common/script_values/te_demog_values.txt common/on_actions/te_demog_on_actions.txt common/scripted_effects/extra_effects.txt common/on_actions/extra_on_actions.txt test_demographics_registry.py
git commit -m "Demographics: war dead by soldiers, the mod's own kills, the migration residual and its profile"
```

### Task 10: Figures, the country's census, lists and the national urban pattern

**Files:**
- Modify: `common/scripted_effects/te_demog_effects.txt`, `common/script_values/te_demog_values.txt`,
  `test_demographics_registry.py`

**Interfaces:**
- Consumes: Task 8's state figures and bands; Task 6's `te_demog_add_bands_to_root`,
  `te_demog_reset_country_bands`, `te_demog_band_figures`, `te_demog_project`.
- Produces: `te_demog_country_census` (country). Country variables: `te_dg_census_year`, `te_dg_cbf<b>`/`te_dg_cbm<b>`,
  `te_dg_median`, `te_dg_young_share`, `te_dg_working_share`, `te_dg_old_share`, `te_dg_dependency`,
  `te_dg_sex_balance`, `te_dg_tfr`, `te_dg_e0`, `te_dg_e65`, `te_dg_imr`, `te_dg_cbr`, `te_dg_cdr`,
  `te_dg_net_migration`, `te_dg_primacy`, `te_dg_cities`, `te_dg_urban_share`, `te_dg_urban_label` (0 Primate,
  1 Dominant, 2 Balanced, 3 Dispersed), and each figure's `te_dg_prev_<name>`; lists `te_dg_states` (by people,
  at most 40) and `te_dg_cities` (the three largest by `state_city_size_rank`); `te_dg_pjf<b>`/`te_dg_pjm<b>` for
  the player.

- [ ] **Step 1: Failing test** (add to the registry test):

```python
class TestCountry(unittest.TestCase):
    def test_country_sums_skip_states_without_a_census(self):
        """Review Focus 1."""
        body = _block(_text(EFFECTS), "te_demog_country_census")
        for m in re.finditer(r"every_scope_state = \{", body):
            self.assertIn("te_demog_has_census = yes", body[m.end():m.end() + 200])
        self.assertIn("ordered_scope_state", body)

    def test_projection_for_players_only(self):
        body = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertIn("is_ai = no", body[:body.index("te_demog_project = yes")])
```

- [ ] **Step 2: Write `te_demog_country_census`.** In one `every_scope_state = { limit = { te_demog_has_census = yes }
  … }` walk over the country's states, after `te_demog_reset_country_bands = yes`, call `te_demog_add_bands_to_root
  = yes` and add to locals: the count of states (`te_dg_seeded`), people (`var:te_dg_people`), births, deaths, net
  migration, `var:te_dg_tfr × var:te_dg_w1549` and `var:te_dg_w1549`, `var:te_dg_e0 × people`,
  `var:te_dg_e65 × people`, `var:te_dg_imr × births`, the urban sum (`var:te_dg_urban` ÷ 1,000,000, so the squares
  can't overflow: values are i64 × 1e-5), the sum of squared urban millions, the largest urban millions, and
  people × each of `te_dg_m_inf`, `te_dg_m_ext`, `te_dg_m_chr`, `te_dg_m_work`, `te_dg_m_mat` (for the projection).
  Then, only when `local_var:te_dg_seeded > 0`:
  - copy every figure to `te_dg_prev_<name>` before overwriting it;
  - `te_demog_band_figures = { B = te_dg_cb }`, then the shares, dependency and sex balance as in
    `te_demog_state_figures` (share the arithmetic: make `te_demog_state_figures`'s body a `te_demog_store_figures`
    effect that reads the locals `te_demog_band_figures` leaves, and call it from both);
  - `te_dg_tfr` = Σ TFR × women 15–49 ÷ Σ women 15–49; `te_dg_e0`, `te_dg_e65` people-weighted; `te_dg_imr`
    births-weighted; `te_dg_cbr`, `te_dg_cdr` per 1,000; `te_dg_net_migration` the sum;
  - urban: `te_dg_urban_share` = urban ÷ people; `te_dg_primacy` = largest ÷ total; `te_dg_cities` = total² ÷ Σ
    squares (the effective number of cities, 1 ÷ Σ share²); `te_dg_urban_label` by §5.1's thresholds 0.40, 0.25,
    0.10;
  - `clear_variable_list = te_dg_states`, then `ordered_scope_state = { limit = { te_demog_has_census = yes }
    order_by = state_population max = 40 check_range_bounds = no save_temporary_scope_as = te_dg_it root = {
    add_to_variable_list = { name = te_dg_states target = scope:te_dg_it } } }` (the trade-partner pattern,
    `trade_partner_effects.txt:147-182`); and `te_dg_cities` the same with `limit = { has_variable =
    state_city_size_rank }`, `order_by = te_demog_neg_city_rank`, `max = 3` (`te_demog_neg_city_rank = { value =
    var:state_city_size_rank multiply = -1 }`: `ordered_*` takes the highest first);
  - `set_variable = { name = te_dg_census_year value = te_demog_year }`;
  - for the player only (`if = { limit = { is_ai = no } … }`): set the locals `te_dg_m_inf`, `te_dg_m_ext`,
    `te_dg_m_chr` to the people-weighted averages, `te_dg_fws` from `capital = { … te_demog_female_work_share }`,
    `te_dg_m_work_f`/`_m` from the averaged work multiplier as `te_demog_prepare` does, `te_dg_tfr` from the
    country's figure, then `te_demog_project = yes`.

- [ ] **Step 3: Wire it.** `te_demog_country_yearly` calls `te_demog_country_census = yes` after
  `te_demog_share_war_dead` inside the gate; `te_demog_country_game_start` ends with `te_demog_country_census = yes`
  inside its gate, so 1836 opens with figures.

- [ ] **Step 4: Tests and reload**

Run: `python3 -m unittest test_demographics_registry -v`
Expected: OK. `POST /reload` clean for `te_demog`.

- [ ] **Step 5: Commit**

```bash
git add common/scripted_effects/te_demog_effects.txt common/script_values/te_demog_values.txt test_demographics_registry.py
git commit -m "Demographics: country census, state and city lists, national urban pattern, 20-year outline"
```

### Task 11: Wealth — Gini and Wealth Concentration per state

Wealth Concentration becomes a per-state stock (§4.2); `te_inh_concentration` becomes the ownership-weighted
average and keeps driving #822's two modifiers unchanged. Nothing here depends on the demographics rule.

**Files:**
- Modify: `common/scripted_effects/te_demog_wealth_effects.txt`, `common/script_values/te_demog_values.txt`,
  `common/scripted_effects/te_inheritance_effects.txt` (`te_inh_yearly_update` `:38-49`, `te_inh_game_start` `:53-56`,
  `te_inh_shift_concentration` `:98-110`, `te_inh_refresh_rural_effects` `:175-221`, `inh_repair_after_civil_war`
  `:226-247`), `common/script_values/te_inheritance_values.txt` (`te_inh_concentration_target` `:46-89`),
  `common/scripted_effects/te_demog_effects.txt` (`te_demog_state_yearly`, `te_demog_country_yearly`),
  `common/on_actions/te_demog_on_actions.txt`, `common/scripted_effects/banking_cycle_effects.txt` (`:1630`, `:1799`),
  `test_demographics_registry.py` (no test pins #822's drift today: checked when this plan was written)

**Interfaces:**
- Produces: state `te_dg_wc`, `te_dg_wc_target`; country `te_inh_concentration` (now derived), `te_dg_wc_target`,
  `te_dg_wc_top`, `te_dg_wc_bottom` (state scopes), `te_dg_gini` (country), the target terms as country variables
  for the panel (`te_dg_wc_t_law`, `_land`, `_own`, `_ineq`, `_tax`, people-weighted); effects
  `te_demog_wc_state_yearly`, `te_demog_wc_seed_state`, `te_demog_wc_national`, `te_demog_wc_shock = { AMOUNT }`;
  values `te_inh_law_amendment_target`, `te_demog_wc_target`, `te_demog_wc_land_term`, `te_demog_wc_ownership_term`,
  `te_demog_wc_inequality_term`, `te_demog_wc_tax_term`.

- [ ] **Step 1: Failing tests** (add to the registry test):

```python
INH = ROOT / "common" / "scripted_effects" / "te_inheritance_effects.txt"
WEALTH = ROOT / "common" / "scripted_effects" / "te_demog_wealth_effects.txt"


class TestWealth(unittest.TestCase):
    def test_national_figure_is_derived(self):
        self.assertIn("te_demog_wc_national = yes", _block(_text(INH), "te_inh_yearly_update"))
        self.assertIn("te_demog_wc_national = yes", _block(_text(INH), "te_inh_shift_concentration"))
        self.assertIn("te_demog_wc_national = yes", _block(_text(INH), "inh_repair_after_civil_war"))

    def test_shifts_reach_every_state(self):
        self.assertIn("every_scope_state", _block(_text(INH), "te_inh_shift_concentration"))

    def test_one_refresh_site_for_the_modifiers(self):
        text = _text(WEALTH)
        self.assertEqual(text.count("te_inh_apply_concentration_modifiers = yes"), 1)

    def test_drift_three_percent(self):
        self.assertIn("multiply = 0.03", _block(_text(WEALTH), "te_demog_wc_state_yearly"))

    def test_wealth_runs_whatever_the_rule(self):
        body = _block(_text(EFFECTS), "te_demog_state_yearly")
        self.assertLess(body.index("te_demog_wc_state_yearly = yes"), body.index("te_demog_cohorts_run = yes"))
```

- [ ] **Step 2: The terms** (`te_demog_values.txt`), each a starting proposal from the Decisions table:

```
# Country scope: #822's law and amendment target (te_inh_concentration_target's
# old body, without the title-continuity pin), centred on 50.
te_inh_law_amendment_target = { … }
```

  Move the body of `te_inh_concentration_target` (`te_inheritance_values.txt:46-81`, law target plus the four
  amendment terms, clamped 0–100) into `te_inh_law_amendment_target`, and redefine:

```
# Country scope: the target the law tooltip and the concept show. The states'
# ownership-weighted target once they have scores; until then #822's own.
te_inh_concentration_target = {
	value = te_inh_law_amendment_target
	if = {
		limit = { has_variable = te_dg_wc_target }
		value = var:te_dg_wc_target
	}
	if = {
		limit = {
			has_variable = te_inh_title_continuity
			has_variable = te_inh_concentration
		}
		value = var:te_inh_concentration
	}
}
```

  State-scope terms:
  - `te_demog_wc_land_term`: `value = 0`, then one `if` per law on `owner`: `law_serfdom`, `law_manorialism`,
    `law_latifundias`, `law_expanded_latifundias` +15; `law_tenant_farmers` +5; `law_peasant_proprietorship`,
    `law_homesteading` −10; `law_collectivized_agriculture` −20; then `multiply = var:te_dg_agr_share`.
  - `te_demog_wc_ownership_term`: `value = var:te_dg_lv_priv`, divide by `{ value = var:te_dg_lv_priv add =
    var:te_dg_lv_self add = var:te_dg_lv_ctry min = 1 }`, `subtract = 0.5`, `multiply = 40`, `min = -20`, `max = 20`;
    0 when the three sum to under 1 (`if` around it).
  - `te_demog_wc_inequality_term`: `value = var:te_dg_gini subtract = 0.4 multiply = 50 min = -15 max = 15`.
  - `te_demog_wc_tax_term` (country): `value = 0`; `law_graduated_taxation` −5; `if = { limit = { te_tax_code_on =
    yes } subtract = { value = te_tax_view_en_div_rate multiply = 20 } }`; `min = -10`.
  - `te_demog_wc_target`: `value = owner.te_inh_law_amendment_target`, `add = te_demog_wc_land_term`,
    `add = te_demog_wc_ownership_term`, `add = te_demog_wc_inequality_term`, `add = owner.te_demog_wc_tax_term`,
    `min = 0 max = 100`; then the pin: `if = { limit = { owner = { has_variable = te_inh_title_continuity }
    has_variable = te_dg_wc } value = var:te_dg_wc }`.

- [ ] **Step 3: The effects** (`te_demog_wealth_effects.txt`):

```
# THIS = a state at game start: the score starts at its own target (rule 5).
te_demog_wc_seed_state = {
	set_variable = { name = te_dg_wc value = te_demog_wc_target }
	set_variable = { name = te_dg_wc_target value = var:te_dg_wc }
}

# THIS = a state, yearly. A state without a score (an old save, a new state)
# starts at its owner's current figure; otherwise it drifts 3% of the way to its
# target. Devastation destroys local capital (Scheidel's levellers, §4.2).
te_demog_wc_state_yearly = {
	set_variable = { name = te_dg_wc_target value = te_demog_wc_target }
	if = {
		limit = { NOT = { has_variable = te_dg_wc } }
		if = {
			limit = { owner = { has_variable = te_inh_concentration } }
			set_variable = { name = te_dg_wc value = owner.var:te_inh_concentration }
		}
		else = {
			set_variable = { name = te_dg_wc value = var:te_dg_wc_target }
		}
	}
	else = {
		change_variable = {
			name = te_dg_wc
			add = { value = var:te_dg_wc_target subtract = var:te_dg_wc multiply = 0.03 }
		}
	}
	if = {
		limit = { devastation > 0 }
		change_variable = { name = te_dg_wc add = { value = 0 add = devastation multiply = -10 } }
	}
	clamp_variable = { name = te_dg_wc min = 0 max = 100 }
}

# THIS = a country: every state's score jumps by $AMOUNT$ (a shock, §4.2), then
# the national figure follows.
te_demog_wc_shock = {
	every_scope_state = {
		limit = { has_variable = te_dg_wc }
		change_variable = { name = te_dg_wc add = $AMOUNT$ }
		clamp_variable = { name = te_dg_wc min = 0 max = 100 }
	}
	te_demog_wc_national = yes
}
```

  `te_demog_wc_national` (country): two walks over the owned states with `has_variable = te_dg_wc`. The first sums
  `var:te_dg_lv_ctry` and `var:te_dg_bureaucrats`. The second weights each state by
  `var:te_dg_lv_own + var:te_dg_lv_self + (country state-owned levels × the state's bureaucrats ÷ the country's,
  floored divisor) × 0.1` and sums weight, weight × `te_dg_wc`, weight × `te_dg_wc_target`, weight × each target
  term (for the panel's term bars), people × Gini groups for the national Gini (sum the six `te_dg_n_*`/`te_dg_y_*`
  and compute the country's `te_dg_gini` with `te_demog_state_gini`'s formula: make that formula a
  `te_demog_gini_from_locals` effect both call). If the total weight is under 1, weight by `var:te_dg_walk_pop`
  instead. Then `set_variable` `te_inh_concentration` and `te_dg_wc_target` to the weighted means, the
  `te_dg_wc_t_*` terms, `te_dg_wc_top` and `te_dg_wc_bottom` (`ordered_scope_state` by `te_dg_wc`, and by
  `te_demog_neg_wc`), and end with **the one** `te_inh_apply_concentration_modifiers = yes`.

- [ ] **Step 4: #822's effects.**
  - `te_inh_yearly_update` (`:38-49`): when any owned state has `te_dg_wc`, `te_demog_wc_national = yes` replaces
    the drift (and its `te_inh_apply_concentration_modifiers` call, since the national effect makes it); a
    country with no scored state keeps the old branch. `te_inh_tidy_amendments` and `te_inh_count_duty_years` stay.
  - `te_inh_game_start` (`:53-56`): `every_scope_state = { te_demog_walks = yes te_demog_wc_seed_state = yes }`, then
    `te_demog_wc_national = yes` in place of its own set-and-apply.
  - `te_inh_shift_concentration` (`:98-110`): keep the guard, then `every_scope_state = { limit = { has_variable =
    te_dg_wc } change_variable = { name = te_dg_wc add = $AMOUNT$ } clamp_variable = { name = te_dg_wc min = 0 max =
    100 } }` and `te_demog_wc_national = yes`; keep the country-variable change only for a country with no scored
    state. Its comment changes to "The modifiers follow at once" (the national effect applies them).
  - `inh_repair_after_civil_war` (`:226-247`): after it copies the loser's variables, `te_demog_wc_national = yes`
    (the winner's states carry their scores).

- [ ] **Step 5: Shocks** (§4.2; the Global Constraints' numbers):
  - **War:** in `te_demog_country_yearly`, before `te_demog_share_war_dead`: if `is_at_war = yes` and
    `var:te_dg_war_year` exceeds 0.2% of the country's people (the walk's `te_dg_walk_pop` summed, or
    `total_population`), `te_demog_wc_shock = { AMOUNT = -1 }` and `change_variable te_dg_war_shock add = 1`, unless
    `te_dg_war_shock >= 10`; if `is_at_war = no`, `set_variable te_dg_war_shock = 0`. The war-dead total must exist
    whatever the rule, which is why Task 9 left the monthly snapshot ungated; move `te_demog_share_war_dead`'s reset
    of `te_dg_war_year` so it runs whatever the rule too (zero it after the shock when cohorts don't run).
  - **A lost war:** `on_lost_war = { on_actions = { te_demog_lost_war } }` with `effect = { te_demog_wc_shock =
    { AMOUNT = -5 } }` (ROOT is the loser; Grand Monuments' war commissions use the same hook).
  - **A won left revolution:** `on_civil_war_won = { on_actions = { te_demog_civil_war_won } }` (ROOT = the winner,
    `te_civil_war_on_actions.txt:14`): if ROOT has `te_cw_origin` (the rebels carry it) and `any_interest_group = {
    is_in_government = yes is_interest_group_type = ig_trade_unions }` or `has_law = law_type:law_council_republic`,
    `te_demog_wc_shock = { AMOUNT = -20 }`.
  - **A banking crash:** after each `set_variable = { name = banking_crisis_wave_crashed value = 1 }`
    (`banking_cycle_effects.txt:1630` and `:1799`, country scope): `te_demog_wc_shock = { AMOUNT = -5 }`.
  - **Devastation:** in `te_demog_wc_state_yearly` (above).

- [ ] **Step 6: Wire the state side.** `te_demog_state_yearly`: after `te_inh_refresh_rural_effects = yes`, add
  `te_demog_wc_state_yearly = yes` (before the census branch). The national figure is computed on 31 December by
  `te_inh_yearly_update`, which already runs then.

- [ ] **Step 7: Tests and reload**

Run: `python3 -m unittest test_demographics_registry test_je_immediate_reset_audit -v`
Expected: OK. `POST /reload`: no `change_variable_clamp_audit` finding (every `change_variable` on `te_dg_wc` is
followed by `clamp_variable`), no `silent_variable_audit` finding in `inheritance_events` (the option tooltips
already describe the shift; check that their loc still reads true now the shift reaches every state).

- [ ] **Step 8: Commit**

```bash
git add common/scripted_effects/te_demog_wealth_effects.txt common/script_values/te_demog_values.txt common/scripted_effects/te_inheritance_effects.txt common/script_values/te_inheritance_values.txt common/scripted_effects/te_demog_effects.txt common/on_actions/te_demog_on_actions.txt common/scripted_effects/banking_cycle_effects.txt test_demographics_registry.py
git commit -m "Wealth Concentration per state: targets, drift, shocks; the national figure drives #822's modifiers"
```

### Task 12: The yearly history store

**Files:**
- Create: `common/scripted_effects/te_demog_history_effects.txt`
- Modify: `common/scripted_effects/te_demog_effects.txt` (`te_demog_country_census`), `test_demographics_registry.py`

**Interfaces:**
- Consumes: `te_history_country_is_tracked` (`common/scripted_triggers/te_history_triggers.txt:17`), the Cultural
  Hegemony annual store as the pattern (`common/scripted_effects/te_history_cultural_hegemony_effects.txt`: record
  `:16`, prune `:108`, sort `:128`).
- Produces: `te_demog_history_record` (country): a container per year in the country's list `te_dg_hist`, at most
  100, each holding `te_hist_i` (the year), `te_dg_h_median`, `te_dg_h_tfr`, `te_dg_h_e0`, `te_dg_h_gini`,
  `te_dg_h_wc`; sorted oldest first.

- [ ] **Step 1: Failing test:** the registry test asserts `te_demog_history_record` exists, is called from
  `te_demog_country_census` behind `te_history_country_is_tracked = yes`, and caps at 100 (`te_dg_hist` and `100`
  in its prune).
- [ ] **Step 2: Write it** by copying the Cultural Hegemony store's three helpers and changing: the store is the
  country (not a global container), the list `te_dg_hist`, five variables, the cap 100. Keep CH's sort (it negates
  the order value because `ordered_*` sorts descending) and its eviction comment (`remove_list_variable` fills the
  hole with the last element, so every eviction re-sorts).
- [ ] **Step 3:** Call it at the end of `te_demog_country_census` inside `if = { limit = { te_history_country_is_tracked
  = yes } … }`, once a year (the yearly country pulse).
- [ ] **Step 4:** Run the registry test; reload; commit `"Demographics: yearly history samples for tracked countries"`.

### Task 13: The Demographics tab in the Population panel

**Files:**
- Create: `gui/pops_overview.gui` — a copy of the installed 1.14.5 file
  (`/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/gui/pops_overview.gui`, 2,820 lines, with its
  BOM; `~/src/vic3`'s copy is identical for this file)
- Create: `gui/te_demographics_widgets.gui` (the section types; the override holds only instances, as
  `states_panel.gui` does)
- Modify: `common/scripted_guis/te_system_tab_sguis.txt`, `localization/english/te_miscellaneous_l_english.yml`,
  `docs/guides/gui_modding_guide.md` (**CRLF**: edit with the Edit tool, confirm with `grep -c $'\r$'` against `wc -l`)

**Interfaces:**
- Consumes: every country variable of Tasks 10–12, `te_dg_states`, `te_dg_cities`, `te_dg_hist`, the state figures.
- Produces: tab id `te_demog`; scripted GUIs `te_pops_demog_tab_sgui` (shown when `te_demog_cohorts_run = yes`) and
  `te_pops_demog_tab_unlock_sgui` (valid when the player has `te_dg_census_year`; its `IsValidTooltip` says "The
  first census is taken in January"), each with `ai_is_valid = { always = no }` though neither changes state.

- [ ] **Step 1: Copy and wire the fifth slot.** Copy the vanilla file. In `tab_buttons = {` (`:51-159`), after the
  fourth button's blockoverrides, add the fifth slot exactly as `gui/culture_panel.gui:138-164` wires Cultural
  Hegemony, with `te_pops_tab_demog` as the text, `InformationPanel.SelectTab('te_demog')`, the two scripted GUIs
  above, and `te_system_tab_met_tt` in the locked tooltip. Run `python3 scripts/analysis/check_gui_lint.py` now: the
  copy plus five blockoverrides must lint clean before any content goes in.
- [ ] **Step 2: The content block.** In `blockoverride "scrollarea_content"` (`:192-567`), after the `national_cast`
  block (`:550`), add a block `name = "te_pops_demog_tab"` with `visible = "[InformationPanel.IsTabSelected('te_demog')]"`
  whose child is gated on `te_pops_demog_tab_sgui` and holds, in order (style guide rules 1, 5, 7, 8, 9):
  1. `te_demog_overview` — eight "Label: value" lines with a trend arrow from the `te_dg_prev_*` value: median age,
     children per woman, life expectancy, dependency ratio, sex balance, Gini, Wealth Concentration, urban pattern.
     Children per woman's tooltip lists its terms (`te_dg_wtfr`, education, survival, urban, `te_dg_means`) from the
     capital's state variables; life expectancy's lists the five cause multipliers. Read country figures with
     `GetPlayer.MakeScope.Var('te_dg_x').GetValue` (THIS-form accessors only: `scripting_best_practices.md`'s
     accessor table from #825).
  2. `te_demog_pyramid` (open) — 18 rows, 85+ at the top. Each row: the men's bar, the band label, the women's bar.
     The men's bar uses vanilla's reverse hack (`gui/shared/progressbars.gui:243-271`): `min = -1 max = 0`, the
     progress and no-progress textures swapped, value = −(band ÷ the largest band). The women's bar is a normal
     `progressbar` on 0..1. Behind each, a translucent bar (alpha 0.35) for `te_dg_pjf<b>`/`te_dg_pjm<b>` on the same
     scale: the outline twenty years ahead. The largest band is a script value `te_demog_pyramid_max` (country: the
     max over the 36 band and 36 projection values). Write the row as a type taking the band index through
     blockoverrides; 18 instances.
  3. `te_demog_wealth` (open) — Gini beside `PopsOverviewPanel.GetAverageIncomePoor/Middle/Rich`; the national
     Wealth Concentration as a bar with its target as the translucent segment (rule 5); the five target terms as
     signed bars (`te_dg_wc_t_*`); the most and least concentrated states (`te_dg_wc_top`, `te_dg_wc_bottom`).
  4. `te_demog_places` (open) — urban share, primacy, the effective number of cities, the label, and the three
     largest cities from `GetList('te_dg_cities')`.
  5. `te_demog_states` (open) — a row per state from `GetPlayer.MakeScope.GetList('te_dg_states')` with
     `datacontext = "[Scope.GetState]"` (the Grand Monuments row form, `grand_monuments_widget.gui:1105-1113`):
     name, people, median age, children per woman, sex balance, Gini, Wealth Concentration, read with
     `State.MakeScope.Var(...)`.
  6. `te_demog_history` (open) — a `te_history_chart` instance with `te_history_bar_unsigned` series for median
     age, fertility and life expectancy; override `sample_datamodel` to
     `"[GetPlayer.MakeScope.GetList('te_dg_hist')]"`, and `sample_visible` and `empty_visible` as the Cultural
     Hegemony instance does (`cultural_hegemony_widget.gui:2216-2466`; gotcha #37: override on the instance).
  7. `te_demog_how_it_works` (collapsed, rule 1) — what the census is, that it applies nothing yet, the sources.
- [ ] **Step 3: Loc.** Every key `te_demog_*` (Global Constraints). Style: "Label: value", game terms as concepts,
  no trailing "…", `#b X#!` not `[b]` (memory), explanatory tooltips name the mechanism.
- [ ] **Step 4: Lint and audits.**

Run: `python3 scripts/analysis/check_gui_lint.py && python3 gui_reference_audit.py --strict && python3 organize_loc.py && python3 organize_loc.py --check`
Expected: no errors (warnings for unproven markup are listed in the PR body as in-game checks). `POST /reload`:
`loc_coverage_audit`, `localization_accessor_audit`, `concept_reference_audit` clean for `te_demog`.

- [ ] **Step 5: The override list.** `gui_modding_guide.md` "This Mod's GUI Files" (`:1736-1811`, CRLF): add
  `pops_overview.gui` as a full replacement re-merged every vanilla patch, holding only instances, its types in
  `te_demographics_widgets.gui`; and note in `docs/guides/vanilla_patch_runbook.md` §5's override list if it keeps
  one.
- [ ] **Step 6: Commit** `"Demographics tab in the Population panel"` (the override, the widgets, the scripted GUIs,
  the loc, the two docs).

### Task 14: The state panel's Demographics subtab

**Files:** Modify `gui/states_panel.gui` (the subtab strip, mod lines `:2509-2605`; content blocks from `:2607`),
`gui/te_demographics_widgets.gui`, loc.

- [ ] **Step 1:** In `state_panel_population_content`'s strip, change the three `size = { 170 40 }` widgets to
  `{ 135 40 }` and add a fourth, a copy of the Characters subtab (`:2576` in the mod's file) with text
  `te_demog_subtab`, `onclick = "[GetVariableSystem.Set('population_subtab', 'te_demog')]"` and the same selection
  highlight test on `'te_demog'`; `visible` on the rule (`GetScriptedGui('te_pops_demog_tab_sgui').IsShown(...)`).
  When it is hidden, the three others keep 135 each: accept the gap (no layout swap) and say so in the PR.
- [ ] **Step 2:** A content block `visible = "[GetVariableSystem.HasValue('population_subtab', 'te_demog')]"`
  instancing `te_state_demog_content` from `te_demographics_widgets.gui`: the state's pyramid (the same row type
  reading `State.MakeScope.Var('te_dg_bf<b>')`), its figures with trends, net migration, Gini, Wealth
  Concentration with its target, and "Census pending" when the state has no `te_dg_year`.
- [ ] **Step 3:** Lint, audits and reload as Task 13 Step 4; commit `"Demographics subtab on the state panel"`.

### Task 15: The debug console and the observer report

**Files:**
- Create: `events/te_debug_demog_events.txt`, `common/scripted_effects/te_debug_demog_effects.txt`,
  `scripts/analysis/demographics_observer_report.py`, `test_demographics_observer_report.py`
- Modify: `localization/english/te_events_l_english.yml` (a `# TE_DEBUG_DEMOG` subsection), `docs/guides/python_tools.md`

**Interfaces:**
- Consumes: the harness's replay format (Task 4 `format_replay`), the generated `te_demog_debug_log_ring_before/_after`
  and `te_demog_dbg_*` values.
- Produces: `te_debug_demog.1` (console-only, `# REVIEWED 2026-10-08: console-only test event (`event
  te_debug_demog.1`); never fired by script on purpose` on its opening line), options:
  - **a — replay**: in the player's capital, log a `TE_DEMOG_REPLAY head …` line (people counts through the
    `millions_thousands_units` form of the probe: three script values per number, `[THIS.ScriptValue('x_g1')|0]_…`),
    `te_demog_debug_log_ring_before = yes`, then `te_demog_step = yes` with the flows the head line printed, then
    `te_demog_debug_log_ring_after = yes`. Re-running it in the same year steps the state again: the option sets
    `te_dg_year` back by one first, and says so in its tooltip.
  - **b — census log on/off**: toggles `global_var:te_demog_census_log`; while set, `te_demog_country_census` logs
    one `TE_DEMOG_CENSUS` line per country with at least a million people: tag, year, people, median, TFR, e0,
    e65, IMR, CBR, CDR, net migration, young/working/old shares, sex balance, Gini, Wealth Concentration, primacy,
    the capital's `te_demog_crisis` (checks the bareword `devastation`/`turmoil` reads), key=value pairs separated
    by `;` (the `TE_NUCLEAR:` format `nuclear_observer_report.py` parses).
  - **c — re-seed this country**: `every_scope_state = { te_demog_seed = yes }` then the census.
  - **d — benchmark** (§14 Q9's late-game re-run): run `te_demog_step` in every state of the world three times,
    logging a `TE_DEMOG_BENCH` line before and after each pass (debug.log's one-second timestamps time it), each
    state's `te_dg_year` set back first.
  - **e — war dead** (§14 Q4): one line per war of the player with `num_country_dead`, `te_dg_war_seen`,
    `te_dg_war_year`, and each state's pending `te_dg_war_in`.
  - **f/g — skew check** (§14 Q11): f logs each capital pop's workforce and dependents and adds a 60-day test
    modifier `te_demog_debug_working_adults` (`state_working_adult_ratio_add = 0.05`, in a new
    `common/static_modifiers/te_debug_demog_modifiers.txt`) to the capital; g logs the same lines a month later.

- [ ] **Step 1: Failing test** — `test_demographics_observer_report.py`: feed it three `TE_DEMOG_CENSUS` lines (two
  years for one tag, one for another) and assert the per-tag series, the world totals per year, and that a line
  with an unresolved `[` template is reported and skipped.
- [ ] **Step 2: The report.** `demographics_observer_report.py` (the `nuclear_observer_report.py` shape): read
  `TE_DEMOG_CENSUS` lines, print per-tag rows every 25 years (§11.1's observer check), world population and
  people-weighted TFR and e0 per 25 years, and the anchors from §2.2–§2.4 beside them; `--json`.
- [ ] **Step 3: The event and its effects**, the loc (`te_debug_demog.1.t`, `.desc`, `.flavor`, `.a`–`.g` and tooltips),
  the static modifier and its loc. The `millions_thousands_units` script values: three per printed number
  (`value = X divide = 1000000 floor = yes`, `value = X divide = 1000 floor = yes modulo = 1000`,
  `value = X modulo = 1000 floor = yes`), as the probe's register values did.
- [ ] **Step 4:** Tests, reload (`orphaned_event_audit` accepts the REVIEWED line; `event_image_audit` needs an
  `event_image`), python_tools.md rows for the report and the console, commit
  `"Demographics: debug console (replay, census log, benchmark, war dead, skew) and observer report"`.

### Task 16: Docs, the player guide, the full checks and PR 2

**Files:** `docs/systems/mod_systems.md` (a new "## Demographics" section after "## Inheritance: Who Inherits"
`:1313-1338`, and that section's concentration bullet `:1330` updated), `docs/player_guide/08-states.md` (a section
on the census and the state subtab), `docs/player_guide/06-politics.md` ("### Who inherits" `:252`: Wealth
Concentration is now per state), the guide PDF, `docs/guides/scripting_best_practices.md` (lessons below),
`docs/superpowers/specs/2026-10-08-demographics-design.md` (status line: phase 1 built in PR 2).

- [ ] **Step 1: `mod_systems.md`.** Spec path, file list, the pulse table from Part B's preamble, the variable
  families, the generator and the harness, what phase 1 applies (nothing) and what it doesn't do yet (phases 2–3,
  map modes), the owner checks, and compatibility (§11.5): the Demography mod applies its own age corrections and
  replaces `states_panel.gui`, and any mod that replaces `pops_overview.gui` now collides with this one.
- [ ] **Step 2: Player guide.** Match the depth of the chapters' peers (CLAUDE.md "Current means accurate"): in
  `08-states.md`, a section "Demographics" — what the tab and the subtab show, how to read the pyramid and the
  outline, that the census changes nothing yet; in `06-politics.md`, one sentence that Wealth Concentration is kept
  per state and the national figure is their average weighted by where property is held. Run
  `python3 scripts/analysis/check_player_guide_style.py --strict`, then `.venv/bin/python scripts/build_player_guide.py`.
- [ ] **Step 3: Lessons** for `scripting_best_practices.md`, one bullet each, only for what this build found true:
  the age-ordered two-pass sweep over a ring with static variable names; the per-mille and
  `millions_thousands_units` logging forms for numbers over 1,000; `while = { count = $N$ }` for powers;
  whichever of the bareword reads (`devastation`, `turmoil`, `workplace` in a pop walk) the census line confirmed.
- [ ] **Step 4: Every CI check, locally**, with the dummy `VIC3_*` variables: `python3 -m compileall -q .`,
  `python3 -m unittest discover -s . -p 'test_*.py'`, `ruff check .`, `python3 scripts/format_paradox_tabs.py --check`
  on every changed `.txt`, `python3 scripts/analysis/check_localization_files.py`, `python3 organize_loc.py --check`,
  `python3 scripts/analysis/check_post_load_rosters.py`, the player guide's two checks, and the `--strict` audits
  CLAUDE.md lists (at least `script_argument`, `empty_effect`, `change_variable_clamp`, `silent_variable`,
  `loc_coverage`, `gui_reference`, `script_loc_reference`, `iterator_limit`, `prev_scope`, `duplicate_key`). Check
  the BOM on every new `.txt` and `.gui` (exactly one). Run the f-string scan from CLAUDE.md on the new Python.
- [ ] **Step 5: A `POST /reload` from the main checkout** on the integration branch (or a second server from this
  worktree), and read the whole `warnings` array; then the owner's deploy (CLAUDE.md "Play-testing unmerged work").
- [ ] **Step 6: PR 2.** Body: what the census shows; the Decisions table's owner calls (cohort width, ownership
  coefficient, land-tenure mapping, the rule's three settings); the Owner checks below; "Player guide: 08-states,
  06-politics updated and rebuilt"; `Closes` lines only for issues this closes.

---

## Owner checks (in game, after PR 2 is deployed)

1. **Q10, natural change** (phase 0): two plain-text saves one month apart in a new 1836 game (debug mode), then
   `demographics_harness.py natural-change OLD NEW`; the ratio should be near 1 before modifiers.
2. **Replay**: `event te_debug_demog.1`, option a, in a running game; `demographics_harness.py replay debug.log`
   prints `OK` for the capital (worst slot error under 1%).
3. **The 1836 census**: the tab and the subtab show a pyramid on day one; Britain's median about 20, children per
   woman about 5.5–6, life expectancy about 40; China's lower.
4. **Observer run to 2100** with the census log on (option b): `demographics_observer_report.py debug.log` shows
   fertility falling with SoL, literacy and the Pill; life expectancy rising with medicine; Gini about 0.5 in 1836
   Britain. This is phase 1's gate (§12).
5. **Benchmark** in a late-game save (option d): the yearly cost stays near the 1836 figure per occupied slot.
6. **War dead** (option e) during a war; then whether battle dead come out of home-state pops (§14 Q4, a save
   comparison around a battle).
7. **Skew** (options f, g): how fast a working-adult modifier changes a pop's workforce share (§14 Q11).
8. **The bareword reads**: the census line's crisis figure moves with devastation and turmoil.
9. **Wealth Concentration**: #822's law tooltip and concept still show the score and its target; the inheritance
   events still move it; a banking crash lowers it.
10. **Save size**: a 1900 save with the census against one with the rule Disabled (the owner's §13 cohort-width call).

## After this plan

- **Calibration** (phase 2's prerequisite): an observer run's yearly plain-text saves (or the census log) fed to a
  new `calibrate` command that runs the model per country against §2.3's world multiples, regional shares and
  great-power ratios, tuning `demographics_params.py` and the retuned defines.
- **Phase 2's plan**, after Owner check 4 passes: the births and deaths modifiers (with the Off mode's equilibrium
  from the same life table and growth factor), the workforce rule, the pension and health bill (and the owner's call
  on its money cost), conscription, the youth bulge, the Family & Reproductive Policy laws and measure buttons, the
  pension-age setting, §8.4's removals, Wealth Concentration's effects split by scope, AI weights, and the tab's
  Family Policy section.
- **Phase 3's plan**: settlement pattern, the urban pattern's effects and Planned Capital, sex-balance effects, the
  event wave, biological age (the global rate tables become per-state, and the sweep's group lookups read biological
  age), Cultural Hegemony's fertility drift, resettlement profiles, the remaining Wealth Concentration shocks, and map
  modes if a per-state source appears.
- If the owner chooses five-year cohorts (§13): the generator's ring becomes 30 slots, the open slot advances every
  five years and is aged first, not folded, in the years between; the model and its tests change with it.
