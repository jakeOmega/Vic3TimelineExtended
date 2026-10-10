# Demographics Phase 2, Step 4: The Census Sets the Engine's Births and Deaths — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each state's census sets the engine's births and deaths through one births modifier and one deaths modifier, so that the engine's events are the model's plus the terms the owner keeps on top, and the census's ring follows what the engine did.

**Architecture:** The engine gives every pop `bare × max(0, 1 + total)` births and deaths, where `bare` is the SoL curve and `total` adds every term (the growth probe). The census's term M is set so the engine's events become the model's events plus the kept terms at the bare curve's weight. The lines the census replaces come off their carriers (§8.4, inverse INJECTs on vanilla laws), so M only has to net out the bare curve and the one replaced per-pop term (literacy). M is applied as a fixed-sign pair of static modifiers refreshed at each census step, fast mode's ×K composes with it, and the census's next step scales its own births and deaths to the engine's so the pyramid places the kept events by age.

**Tech Stack:** Victoria 3 1.14.5 Paradox script; Python 3.11/3.12 (`unittest`); the `_Engine` script interpreter in `test_demographics_registry.py`; `demographics_model.py` as the script's twin; `demographics_harness.py` for offline checks.

**Spec:** `docs/superpowers/specs/2026-10-08-demographics-design.md` (§2.3–§2.5, §8.4, §11.3–§11.4, §12, §13–§14) and the calibration plan's step 4 (`docs/superpowers/plans/2026-10-10-demographics-phase2-calibration.md`, PR #857). Evidence: `docs/testing/demographics-probe-results-2026-10-08.md` (Q5, Q7), `docs/testing/demographics-growth-probe-results-2026-10-09.md`, `docs/testing/demographics-fast-run-2026-10-09.md`, `docs/testing/demographics-history-check-2026-10-10.md` (#857's branch).

**Depends on:** #855 (the poverty term) and #857 (the `history` and `fidelity` harness, `state_inputs`, the timed-modifier reader) merged first. Tasks 8 and 10 call #857's functions; every other task is against `main` 85a23d47 and rebases cleanly over both, which touch none of the blocks below except `te_demog_generated_values.txt` (regenerate, never merge by hand).

## Global Constraints

- **Game version:** Victoria 3 1.14.5. Vanilla facts are from `vanilla_parsed/` and the 1.14.5 install at `/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game`.
- **Paradox files:** tab indentation, exactly one UTF-8 BOM on every `.txt` and `.yml` (`bom_normalizer`), `python3 scripts/format_paradox_tabs.py <files>` after edits.
- **Script literals:** at most five decimal places; a sixth reads as 0 with `Badly read script value` (probe 2026-10-08, Finding 1).
- **No negative `add_modifier` multiplier.** Its behaviour is unread in this repo (monetary design §17 check 8 is still open; `te_fx_weak`/`te_fx_strong` use fixed-sign pairs). M is applied as a +1 modifier and a −1 modifier, each with a multiplier of 0 or more.
- **A modifier's `multiplier` script value resolves against ROOT** (CLAUDE.md, #500). The census's modifiers are refreshed only where ROOT is the state: the yearly state pulse and fast mode's `te_demog_events.2`. Never from the console, the benchmark or game start.
- **One refresh site per modifier:** `te_demog_rates_apply` is the only effect that adds or removes `te_demog_census_*`.
- **The rule's checks are written negatively:** `te_demog_effects_run` (Full only), `te_demog_cohorts_run`.
- **Generated files:** `te_demog_generated_values.txt` and `te_demog_generated_effects.txt` come from `scripts/generators/gen_demographics.py`; run it, never edit them.
- **Localization:** add keys to an existing `*_l_english.yml`, run `python3 organize_loc.py`, commit everything it rewrites. House style per `docs/player_guide/STYLE.md` for player-facing text; loc uses `#b X#!`, never `[b]`.
- **Python:** 3.11-compatible (no PEP 701 f-strings: `grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" <files>` before pushing). Run Python through `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python` with `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent` in a worktree.
- **Commits:** by path, never `git commit -a`; end each message with the session's `Co-Authored-By` and `Claude-Session` lines.
- **The gate's figures, verbatim from the calibration plan:** world population 1836–1900 within ×1.3–×1.7; no country of 20M or more losing people for ten years running outside wars; the census's replay (`demographics_harness.py replay`) exact.

## Review Focus

1. **A freshly seeded state** (game start, a re-seed after a merge): its census writes 0 births, so a refresh from it would set M = −1 and stop births at the clamp. Expect M left as it was (none on a new 1836 state). Pinned by Task 4's `test_a_seed_leaves_the_rates_alone`.
2. **A state that lost its modifier but kept `te_dg_mb`** (a change of owner, secession, a save another mod edited): the prior term is read only while the modifier is on, so nothing phantom comes off the walk's average. Pinned by Task 4's `test_the_prior_term_needs_the_modifier`.
3. **The rule switched from Full to Display only mid-game:** the modifiers and terms come off at the state's next step, and that step takes no kept scales. Pinned by Task 4's `test_display_only_clears_the_rates` and Task 3's `test_no_kept_scales_outside_full`.
4. **Fast mode with the census's term on:** the engine must run K × (model + kept), not K × the curves. Pinned by Task 5's `test_fast_and_census_terms_reach_a_joint_fixed_point`.
5. **Kept terms that already push a state past −0.8** (a famine, a plague event) or a model that wants more than +100%: M never pushes further down and never above +1.0. Pinned by Task 2's `test_the_clamp_never_pushes_past_the_kept_terms` and Task 4's `test_script_clamps_like_the_model`.

## 1. The engine's arithmetic, from evidence

Each claim is **verified** (with its source) or **needs an in-game probe** (§4 designs the probe).

| # | Claim | Status | Evidence |
|---|---|---|---|
| E1 | A pop's births are `curve_b(SoL) × size × max(0, 1 + total_b)` and its deaths `curve_d(SoL) × size × max(0, 1 + total_d)`, one total per pop, every term **added** inside it | verified | growth probe 2026-10-09: 945 death windows, steps −0.9 to +1.0, deaths at 1.00–1.04 of the additive candidate; the multiplicative census formula drifted to 1.31 at −0.9 |
| E2 | Growth lands 12 times a year, a month's curve each | verified | growth probe: each 28-day window 0.98–1.03 of the curve's month |
| E3 | The curves: births 475 per 100,000 a month to SoL 11, falling to 80 at SoL 35; deaths 600 at SoL 0, 475 at SoL 4, 143.9 at 18, 100 at 35 | verified | `common/defines/extra_defines.txt:79-88` and `:101-147`; `te_demog_pop_engine_births`/`_deaths` (generated, `te_demog_generated_values.txt:5-47`), `test_gen_demographics.test_engine_curves_match_the_defines` |
| E4 | The starving slope: deaths climb from 475 to 600 per 100,000 a month as SoL falls from 4 to 0 (`POP_GROWTH_MORTALITY_STARVING_SLOPE`); births are flat there | verified | `extra_defines.txt:85,104-105,131` |
| E5 | A state's `modifier:state_birth_rate_mult` / `state_mortality_mult` holds the country's and the state's modifiers | verified | probe 2026-10-08 Q5 |
| E6 | A state modifier added with `add_modifier` enters that read | verified (indirectly) | fast mode's own +1 modifiers: under 4× and 12× the Closed Borders `mig_raw` median was −0.41 per 1,000 (fast run 2026-10-09). Were the read blind to them, every country would show about +7 per 1,000 of phantom immigration |
| E7 | Per-pop terms the read leaves out — births: `literacy_penalty` −0.1 × literacy (fitted −0.101), starvation −0.7 × scale (mild) or −0.9 (severe); deaths: the class's `state_<type>_mortality_mult`, the workplace's `building_<type>_` and `building_group_<group>[_<type>]_mortality_mult`, `working_conditions` by workplace group, starvation +0.6 × scale or +1.0, `state_non_homeland_mortality_mult` | verified | growth probe ("Births = …", "Deaths = …"); vanilla `common/static_modifiers/00_code_static_modifiers.txt:119-182`; generated `te_demog_pop_birth_mult`/`_death_mult` |
| E8 | Their sizes in 1949: class +4.1% of curve deaths (child-labour laws), working conditions +1.0%, building-group reads +0.7%, production methods +0.5%, starvation +0.1–0.3% | verified (one save) | growth probe's table |
| E9 | The floor: births at −0.9 run at a tenth and stop at −3; never negative. Per pop the floor is 0 at a total of −1 | verified | Q7 (Qing, −0.9 then −3); growth probe ("bends at the floor in 1836, where literate and starving pops reach 0"); deaths at −5 stopped (the probe's control) |
| E10 | The linear range measured: −0.9 to +1.0, both rates | verified | growth probe's step design (+0.5, +1.0; −0.5, −0.9) |
| E11 | Above +1.0 a total stays linear | **needs a probe** (P5, only if the clamp binds) | unmeasured; severe starvation's +1.0 sat inside the 1949 fit |
| E12 | A change of rate shows in full within a month | verified | Q7: phase A in full in its first month |
| E13 | Vanilla's laws: Charitable Health System −0.03 mortality a level of its institution, Public Health Insurance −0.05 a level (`institution_modifier`), Private Health Insurance −0.002 `state_mortality_wealth_mult` a level; Child Labor Allowed +0.05 for laborers, machinists, farmers, peasants, Restricted Child Labor +0.02 for laborers, farmers, peasants (`modifier`); women's rights births: No Women's Rights +0.05, Women in the Fields −0.10, Women in the Workplace −0.05, Women's Suffrage −0.05 | verified | `game/common/laws/01_health_system.txt:41,90,117`, `02_childrens_rights.txt:13-16,50-52`, `02_rights_of_women.txt:22,62,143,194`; `vanilla_parsed/common/laws.json` |
| E14 | An `INJECT` into a vanilla law's `modifier` or `institution_modifier` **sums** with vanilla's lines (and an institution line applies per level) | verified | `docs/guides/scripting_best_practices.md` § "CONFIRMED: an `INJECT:` block sums" (2026-09-20 laws; 2026-10-10 `institution_modifier`, Public Health Insurance read in game) |
| E15 | Devastation: `state_region_devastation` carries `state_mortality_mult = 1.0`, scaled by the devastation level (vanilla's comment); script reads `devastation` as a 0–1 share | the line and the read: verified (`00_code_static_modifiers.txt:731-740`; `te_debug_demog_census_line` prints it). **Whether it is in `modifier:state_mortality_mult` and how it scales: needs P1** |
| E16 | Pollution: `state_region_pollution_health` carries `state_mortality_mult = 0.5` × the pollution impact, less `state_pollution_reduction_health_mult`; the mod INJECTs another +0.05 | the lines: verified (`00_code_static_modifiers.txt:742-748`; `extra_modifiers.txt:341-347`). **In the read, and whether the INJECTed +0.05 sums inside a code-scaled modifier: needs P1** |
| E17 | Turmoil: the `state_turmoil*` modifiers carry no mortality; turmoil's deaths come from `state_mortality_turmoil_mult` "per Turmoil" (Militarized Police +0.004 a level, events) | the lines: verified (`00_code_static_modifiers.txt:776-798`; `docs/engine/modifiers_summary.txt:7411`). Its scaling: **unknown**, measured about 0 (growth probe "Open"); kept by construction, a probe only if the gate run shows an unexplained residual in turmoil states (P6) |
| E18 | `low_pop_state` +0.5 births (scaled by how far the state is under `LOW_POP_THRESHOLD`, 5,000 per arable land) and `unemployment_birth_penalty_state` (mod: −0.1 × unemployment, vanilla −0.4) are state modifiers | the lines: verified (`00_code_static_modifiers.txt:695-705`, `00_defines.txt:1549`; mod `REPLACE`s in `extra_modifiers.txt:291,323`). In the read: assumed as for every state modifier (E5); P1 logs the birth read beside them |
| E19 | `working_conditions` is scaled by `building_working_conditions_mult` (Workplace Safety −0.2 a level) | the line: verified (`vanilla_parsed` institutions). The census adds the table's value unscaled (`gen_demographics.engine_rate_terms`): a known gap in the residual, not in M |
| E20 | About 2% of deaths stay unexplained by every read | verified (open) | growth probe "What is left" |
| E21 | A permanent `add_modifier` is saved in the state's `timed_modifiers` block with its multiplier | verified | #857's `demographics_save_inputs` reads `migration_crowding` there |
| E22 | Whether a state's modifiers survive a change of owner (conquest, secession, a civil war's transfer) | **needs a check** (P4, offline from a save, no console probe) | state variables stay with the state (spec §2.6); modifiers unread |

**Measured from the gate run's saves for this plan** (normal-speed observer game, `/mnt/d/vic3te-data/vic3te-demog-gate-data/saves/`, read with `demographics_save_inputs.read_sections` and `pop_growth`'s curves; the scripts are reproduced in Task 8 as `predict`'s `--slope` report):

| Save | People below SoL 4 (below SoL 2) | The slope's extra deaths | Their cost to growth | No Women's Rights | Child Labor Allowed | A health law |
|---|---|---|---|---|---|---|
| 1837.1.1 | 4.2% (2.3%: laborers 1.5%, slaves 0.7%) | 0.76% of bare deaths | 0.04 points a year (China 0.02, India 0.06, Britain 0.05) | 83% of people | 100% | 5% |
| 1887.1.1 | 16.2% (14.7%: laborers 12.0%, slaves 2.1%) | 3.7% | 0.17 points (China 0.24, India 0.21, Russia 0.20, Japan 0.19) | 82% | 97% | 16% |

Bare births ran 5.6% a year and bare deaths 4.7% a year, world-wide, in both saves.

## 2. M per state

### The formula

Write a pop's total as the census's own terms plus everything else: `total_p = M + F + K_s + K_p + R_s + R_p`.
- M: the census's term (this plan), F: fast mode's term.
- K: the terms kept on top (owner call (a)), `_s` in the state read, `_p` per pop.
- R: the terms the census replaces.

After Task 6, R_s = 0: every replaced state-level line is off its carrier. R_p is literacy (births) only.

With no pop at the floor, a state's events a month are `Σ bare_p × (1 + M + F + K_s + K_p + R_p)`. The census wants, at K = 1 (no fast mode), `T + Σ bare_p × (K_s + K_p)`, T being the model's events. So

```
M = T / B − 1 − Σ bare_p × R_p / B,        B = Σ bare_p
```

- **Births:** `M_b = T_b / B_b − 1 − literacy_penalty × Σ(bare_b × literacy) / B_b`, with literacy_penalty = −0.1 read from the static modifier by the generator.
- **Deaths:** `M_d = T_d / B_d − 1` (plus the slope term if owner call (b) keeps it, §3).
- **Units:** the walk's. B is `te_dg_w_eb0` / `te_dg_w_ed0` (events a month × 100,000), and `T = te_dg_cbr_model × state_population × 100 / 12` (the model's rate per 1,000 a year, at today's population). Σ(bare_b × literacy) is a new walk local, `te_dg_w_ebl`.
- **Why not the spec's ratio or a plain netting.** The spec's `M = model ÷ E_T − 1` (E_T the engine's events before M) gives `E_T + (model/E_T − 1) × B`. That equals the model only when no other term applies. Netting everything, `M = (model − E_T) / B`, gives the model exactly and cancels the kept terms. This formula keeps them, at the weight the engine itself gives them: a famine adds the deaths vanilla's famine adds.
- **Kept terms add at the bare curve's weight, not the model's.** The alternative, `T × (1 + K̄)`, scales them by the model's rate. The two differ by the ratio B/T and agree once step 5 retunes the curves to the census's medians. Additive is what the engine does natively, and needs no reading of K.

### Per state, one births term and one deaths term

The engine's pops carry no age, so a modifier can only scale a pop's whole births or deaths. The census places the year's events by age itself. Per pop type is out for births (`state_birth_rate_mult` is the only registered birth type) and buys nothing for deaths, since the census has no strata dimension. So M is per state, one for births and one for deaths.

### How K is read: it isn't, for M

M never reads a kept term. The engine applies K whatever its scaling (devastation, pollution, turmoil included), so E15–E17's unknowns don't block M. K is read only in two places:
- **The clamp's "other":** the state read less the census's and fast mode's prior terms.
- **The residual and the kept scales:** through `te_dg_eb`/`te_dg_ed`, the walk's expected events. They already read the state read and the per-pop starvation, class, workplace and non-homeland terms (E7; 1.024 of deaths explained). Unreadable kept terms (turmoil's scaling, wealth mortality, the 2% of E20) still reach the engine. They show up only in the migration residual, as in phase 1.

### The clamp

- **The floor:** `other + M ≥ RATE_TOTAL_MIN = −0.8`, where other = the state read − M_prev − F_prev. The −0.9 that Q7 and the growth probe measured, less literacy's −0.1 at full literacy, keeps a literate, fed pop inside the measured linear range (E9–E10).
- **When the kept terms alone are past −0.8** (a famine, a plague event), the floor is 0: M never pushes a state further down than its kept terms do.
- **The ceiling:** `M ≤ RATE_TERM_MAX = +1.0`, the largest step measured (E10).
- A starving pop still floors at 0, as intended.
- **The floor and the formula.** The formula assumes no pop at the floor. A floored pop's events are 0, not the negative figure the sum would give, so the state's events run above M's aim by the floored pops' share. The walk floors each pop as the engine does, so `te_dg_eb`/`te_dg_ed`, the residual and the kept scales all see it; only M's aim is off. Documented, not corrected: a second walk to solve for M exactly would double the walk's cost.
- **The flag:** a clamped state sets `te_dg_rate_clamped = 1`. The census line counts clamped people, and P5 extends the range if the gate run shows it binding.

### Applied as

- **Four static modifiers** in `common/static_modifiers/te_demog_modifiers.txt`: `te_demog_census_births_up` (`state_birth_rate_mult = 1`), `te_demog_census_births_down` (`= -1`), `te_demog_census_deaths_up` (`state_mortality_mult = 1`) and `te_demog_census_deaths_down` (`= -1`).
- **Multipliers:** `max(M, 0)` for an up modifier and `max(−M, 0)` for a down one, read from `var:te_dg_mb` / `var:te_dg_md`. At most one of each pair is on.
- **One refresh site:** `te_demog_rates_apply` removes and re-adds them: the dynamic-modifier scaling pattern (CLAUDE.md), with one refresh site.
- **Cadence:** each census step, from the yearly state pulse, or from `te_demog_events.2` under fast mode's clock. Both have ROOT = the state. Rates follow within a month (E12), so a year's lag is fine.
- **Seeds:** a seed writes 0 births (`te_dg_stepped = 0`), so the refresh skips it and M stays as it was.
  - An 1836 state runs on the curves until its first step: its second yearly pulse, since the first re-seeds (`te_dg_reseed`).
  - So does a re-seeded state with no M yet.
- **Old saves:** M arrives at each state's next step. That step takes no kept scales, since `te_dg_cbr_model` is absent.

### Fast mode's ×K

At a clock step the engine must run `K × (T + Σ bare × K_terms)`, so F scales the state's whole average with the new M in it:

```
avg = te_dg_w_eb / te_dg_w_eb0 − F_prev − M_prev,     F = (K − 1) × (avg + M_new)
```

`te_demog_fast_refresh_rates` already does this without M; Task 5 takes M_prev off and puts M_new in. M itself is computed for K = 1: T is the model's events per census year over 12.

### The census's own accounting: the ring follows the engine

With M on, the engine's events over a step are the model's plus the kept terms (and whatever the clamp and the floors leave). Phase 1 lets the scale absorb any gap, which spreads it over every age. Kept births (`low_pop_state`, the Natalism decree, a famine's −0.9) are newborns by definition, so the step now scales its own rates to the engine's totals before the sweep:

```
bz = te_dg_eb / (te_dg_cbr_model × state_population / 1000) − 1        (−0.9 … +4)
dz = (te_dg_ed / (te_dg_cdr_model × state_population / 1000) − 1) × KEPT_DEATHS_BY_AGE
```

- **Applied to the year's rates:** tfr × (1 + bz), and the five cause multipliers × (1 + dz).
- **Logged as they are:** the replay head logs the scaled locals, so `demographics_harness.py replay` stays exact with no format change.
- **The model's own events** (M's next target) come back out exactly: `births / (1 + bz)` and `(deaths − maternal) / (1 + dz) + maternal / (1 + bz)`, as `te_dg_cbr_model` / `te_dg_cdr_model`.
- **What the panel shows:**
  - CBR, CDR and children per woman are the realized ones. That answers §13's question: "the panel should show what actually happens".
  - Life expectancy, e65 and infant mortality stay the census's life table at its own rates ("before famine, war and disasters", which the tab's explanation says).
- **(c) is the deaths half:** with `KEPT_DEATHS_BY_AGE = 0`, dz = 0 and the scale spreads kept deaths flat, as today.

### The game rule

- **Full:** M and the kept scales.
- **Display only and Disabled:** no M and no kept scales. The refresh clears them, so a mid-game switch takes effect at each state's next step.
- **The removals of Task 6 are static and apply under every setting.** Until step 5 gives Display only and Disabled their equilibrium rates (§11.4), those two settings lose the replaced lines with nothing in their place:
  - the health laws' mortality cut;
  - child labour's class deaths;
  - women's rights' birth lines, if (a) removes them;
  - the mod's flat lines.
- So steps 4 and 5 should reach players together. The system is unreleased (owner, 2026-10-10), so that costs nothing.
- **The alternative** keeps the lines and cancels them inside M under Full only. It keeps Display only and Disabled vanilla until step 5, at the price of law and tech tooltips listing effects the census silently cancels. Not recommended (memory: loc promises the code doesn't deliver).

## 3. The owner calls

### (a) Which terms stay on top (K)

The principle recommended: **standing law and technology lines that model what the census models are replaced; shocks, local conditions and player actions are kept.** The census is fitted to history with laws and techs as inputs (#855, #857); a standing line on top shifts every country it covers, permanently.

| Term | Kind | Size (evidence) | The census models it? | Recommendation |
|---|---|---|---|---|
| The SoL curves | engine | the base | yes: the wealth term, poverty, nutrition | replaced: M nets out the bare curve by construction |
| `literacy_penalty` −0.1 × literacy (per pop) | engine code | fitted −0.101 (E7) | yes: education's term | **replaced**, netted in M (R_p) |
| Health laws: Charitable −0.03 a level, Public −0.05 a level, Private −0.002 wealth mortality a level | vanilla laws (E13) | 5% of people under one in 1837, 16% in 1887 | yes: access × treatment | **replaced**, inverse INJECT (the calibration plan's route; shape verified, E14) |
| Child-labour class lines +0.05 / +0.02 | vanilla laws (E13) | +4.1% of curve deaths in 1949 (E8); Child Labor Allowed over 97–100% of people | yes: work +0.1 under Child Labor Allowed | **replaced**, inverse INJECT |
| Women's rights' birth lines +0.05 / −0.10 / −0.05 / −0.05 | vanilla laws (E13) | No Women's Rights over 83% of people in 1837: kept, +0.05 × bare births 5.6% a year ≈ +0.28 points of births a year on a census that already runs world growth +1.0% against history's 0.4–0.8% | no term; the fertility fit (#857) is against history without it | **owner call; recommend replaced** (inverse INJECT) |
| The mod's flat lines §8.4 names: the Pill −0.10 births; the family-policy laws (Pro-Natalist Subsidies +0.10, State-Sponsored Family Planning −0.05, Population Control Measures −0.10, Communal Child Rearing −0.20); `modern_vaccines` and `antibiotic_mass_production` −0.05 deaths and +0.05 births each; the Ministry of Consumer Protection −0.01 a level | mod | — | yes (means tiers, desired fertility, medicine, external causes) | **replaced**, removed at source (§8.4) |
| The augmentation laws (Unrestricted −0.05; Medical Only, Regulated Market, Mandatory −0.02 a level) | mod | — | becomes chronic treatment (modifier-types design, "Not decided here") | **replaced**: Medical Only +0.10, Unrestricted and Regulated Market +0.05 chronic treatment, cap 0.80 → 0.85 (that note's starting point). Mandatory has no starting value there: recommend +0.05, owner to confirm |
| `second_wave_feminism` −0.025 and `sexual_revolution` −0.025 births | mod techs | small | the means tiers carry the transition | owner call; recommend replaced (removed) |
| The rights laws (Legal Limbo −0.05; Basic Protections, Comprehensive Rights, Full Equality, Protected Class −0.10 births), State Eugenics +0.10 births, `mental_health_awareness` −0.05, `biological_immortality` −0.20, `mind_backups` −0.05 deaths | mod | era 6 and later, outside the 1836–1900 gate | no (immortality is phase 3's) | **kept for now**; revisit with step 6's post-1900 schedules |
| The Natalism Initiative decree +0.5 births | mod decree | large, temporary | §8.1's measures replace it later | **kept** (a player action) |
| Starvation (births −0.7 × scale / −0.9; deaths +0.6 × scale / +1.0), per pop | engine code | +0.1–0.3% of deaths in 1949 | no | **kept**; its age pattern is call (c) |
| Devastation +1.0 × level | engine code | E15 | no | **kept** |
| Pollution +0.5 × impact (+0.05 mod) | engine code | E16 | no (spec: read through) | **kept** |
| Turmoil (`state_mortality_turmoil_mult` per turmoil), wealth mortality | engine | ≈ 0 (E17) | no | **kept** by construction (unreadable) |
| `working_conditions`, production methods' and building groups' mortality, character traits | engine and vanilla | +1.0%, +0.5%, +0.7% (E8) | no: the work cause sees laws, not workplaces | **kept** (the player's and the AI's choice of method matters) |
| Non-homeland mortality | engine | ≈ 0 | no | **kept** |
| `low_pop_state` +0.5 births, `unemployment_birth_penalty_state` −0.1 × rate | engine code | unmeasured (P1 logs the birth read) | no: vanilla's frontier filling and the slump's | **kept** |
| Event, journal, company, principle (Food Standardization −0.1), amendment and decree modifiers; Forced Heirship's rural cut (−0.15 × the agrarian share) | vanilla and mod | various | no (spec §2.3: read through) | **kept** |
| Pro-Natalist's −0.05 working-adult (§8.4) | mod | — | not births or deaths | out of step 4: it goes with the workforce effects |

### (b) The starving slope below SoL 4

M nets out the bare curve, so the slope disappears unless it is kept.
- **To keep it,** add its extra deaths to M's target: `T_d += Σ size × (curve_d(SoL) − curve_d(max(SoL, 4)))`. That is one more generated pop value (`te_demog_pop_engine_deaths_fed`, the curve at SoL 4 or above) and one walk local.

**Evidence** (gate run's saves, above):
- **Cost:** the slope costs world growth 0.04 points a year in 1837 and 0.17 in 1887. In 1887 it costs China 0.24 and India 0.21, Russia 0.20 and Japan 0.19.
- **The poverty term was fitted without it** (#855): ×1.75 at SoL 5, chosen because it gives China +0.3% a year in 1887. ×2 was rejected because China shrinks (−0.1%).
- **Keeping the slope takes China to about +0.06%** in that save, the same failure.
- **Who sits below SoL 4:** laborers (12% of the world's people in 1887) and slaves.
- **The two act on different SoL:** the slope per pop, the poverty term on the state's mean SoL. The history check found pop-by-pop poverty no better (5.9 years of error against 5.6).

**Recommendation: replace** (the poverty term stands in for the slope).
- **The caveat:** a destitute pop in an otherwise middling state loses the slope's deaths, and the census sees it only through the state's mean.
- **The switch:** `KEEP_STARVING_SLOPE` in `demographics_params.py`, read by the generator (Task 4, step 8). Ruling the other way is a one-line change.

### (c) Starvation's deaths by age

- **Flat:** costs nothing. It is today's behaviour: the scale spreads any gap over every age in proportion to its people.
- **The model's age pattern:** dz on every cause multiplier, which in a high-mortality year puts the deaths on infants, small children and the old.

**Evidence:**
- Spec §2.4: "starvation and disease fall on the young and old, devastation on everyone, pollution on chronic causes."
- The famine literature finds famine deaths concentrated among young children and the old (e.g. Ó Gráda, *Famine: A Short History*, 2009).
- The kept deaths are small in normal years (+0.1–0.3% of deaths, E8). dz measures them: the census line carries it (Task 7).

**Recommendation: the model's age pattern for all kept deaths**, one dz (`KEPT_DEATHS_BY_AGE = 1`).
- **It approximates devastation** (everyone) **and pollution** (the old) with the model's own pattern: young and old, in the 19th century.
- **A per-term split** (starvation and disease by the pattern, devastation through the kills channel, pollution on chronic) needs three walk sums. Leave it until the panel shows an artefact.
- **Births have no choice to make:** kept births are newborns.

## 4. Probes

| Probe | Question | Design | Blocks |
|---|---|---|---|
| **P1** | Are devastation's and pollution's mortality lines in `modifier:state_mortality_mult`, and as what share? Does the mod's INJECTed +0.05 on pollution sum? | Console option m (Task 1). It runs on today's build: no M, fast mode off. Every state in the world with devastation or a polluted region logs its mortality and birth reads, devastation, turmoil and pollution, with `debug_log_scopes = yes` to name it. Load the 1887 gate save (5 devastated states), fire it, then hover each logged state's mortality in game. If the tooltip's total is the logged `mort`, the lines are in the read. | Nothing in M. It decides whether the residual and the clamp's "other" see these deaths. If not, a follow-up adds `devastation` per pop to `te_demog_pop_death_mult` |
| **P2** | Do the inverse INJECTs net the vanilla lines to nothing? | After Task 6, open Public Health Insurance, Charitable Health System, Child Labor Allowed and No Women's Rights in the law panel. None should list a mortality or birth-rate line (the monetary precedent: a cancelled rank line disappears from its tooltip). Option l's log of the capital's `modifier:state_mortality_mult` should drop by the old line. | Confirms Task 6 (shape verified, E14) |
| **P3** | Does the engine hit the target in game? Is M's fixed point stable? | Option n (Task 4) logs the capital's M, F, targets, kept scales and reads. The census line (Task 7) carries `m_b`, `m_d`, `bz`, `dz`, `clamped`. In the gate's fast-mode run, `bz` and `dz` measure each country's engine-against-target gap. They should sit at the kept terms' share (a few per cent) and not drift. | The gate (Task 10) |
| **P4** | Does a state keep its census modifiers through a change of owner? | Offline: `demographics_harness.py predict SAVE --check-modifiers` (Task 8) lists states whose `te_dg_mb` is not 0 but whose `timed_modifiers` lack the matching census modifier. Run it on a fast-run save taken after a war or a civil war. | Nothing: the `has_modifier` guard (Review Focus 2) and the next step's refresh cover a loss. The answer goes into the results doc. |
| **P5** (conditional) | Is a total linear above +1.0? | The growth probe's Latin square with steps +1.5 and +2.0 (branch `probe/demographics-growth`, `te_debug_growth.1`) | Run only if the gate run's census lines show `clamped` above 1% of the world's people |
| **P6** (conditional) | Turmoil's scaling | The growth probe on high-turmoil states with a test `state_mortality_turmoil_mult` | Run only if the gate run shows a residual tied to turmoil |

Verified already, no probe needed: E1, E2, E5, E6, E9, E10, E12, E13, E14, E21.

## 5. File structure

| File | Change | Responsibility |
|---|---|---|
| `scripts/analysis/demographics_params.py` | modify | the clamp, the kept scales' bounds, `KEEP_STARVING_SLOPE`, `KEPT_DEATHS_BY_AGE`, `LITERACY_BIRTH_PENALTY`, the replaced and kept carrier tables |
| `scripts/analysis/demographics_model.py` | modify | `rate_term`, `kept_scale`, `step(..., births_scale, deaths_scale)` and its model totals, `model_crude_rates`, `starvation_terms` |
| `scripts/generators/gen_demographics.py` | modify | the new `te_demog_k_*` constants (generated values) |
| `common/scripted_effects/te_demog_rate_effects.txt` | **create** | `te_demog_kept_scales`, `te_demog_rates_refresh`, `te_demog_rates_apply`, `te_demog_rates_clear` |
| `common/scripted_effects/te_demog_effects.txt` | modify | the walk's `te_dg_w_ebl`; `te_demog_step_begin` calls the kept scales; the maternal accumulator; `te_demog_step_finish` stores the model's rates; the orchestrator calls the refresh |
| `common/scripted_effects/te_demog_fast_effects.txt` | modify | the clock step calls the refresh; F takes M off and puts it back |
| `common/script_values/te_demog_values.txt` | modify | `te_demog_rate_*` and `te_demog_fast_*_applied` values |
| `common/static_modifiers/te_demog_modifiers.txt` | modify | the four census modifiers |
| `common/laws/te_demog_law_injections.txt`, `common/laws/modified_health_system.txt` | modify | inverse INJECTs on vanilla's laws |
| `common/laws/extra_laws.txt`, `common/technology/technologies/era_6.txt`, `era_7.txt`, `common/institutions/extra_institutions.txt` | modify | §8.4's removals; augmentation's chronic lines |
| `scripts/analysis/demographics_modifiers.py` | modify | `engine_rate_lines()`: every birth and mortality line on a law, tech or institution, vanilla and mod |
| `common/scripted_effects/te_debug_demog_effects.txt`, `events/te_debug_demog_events.txt` | modify | options m and n; the census line's new fields |
| `scripts/analysis/demographics_observer_report.py` | modify | `--phase2` |
| `scripts/analysis/demographics_save_inputs.py`, `scripts/analysis/demographics_harness.py` | modify | food security and devastation from saves; `predict` |
| `localization/english/te_miscellaneous_l_english.yml`, `te_events_l_english.yml` | modify | the modifiers' and the console's keys |
| Tests | modify | `test_demographics_model.py`, `test_demographics_registry.py`, `test_gen_demographics.py`, `test_demographics_modifiers.py`, `test_demographics_observer_report.py`, `test_demographics_save_inputs.py`, `test_demographics_harness.py` |
| Docs | modify | `docs/systems/mod_systems.md` § Demographics, the spec's §2.3/§2.4 "Applied as" and §13, `docs/guides/vanilla_patch_runbook.md` (the new cancels), `docs/guides/python_tools.md` (`predict`), `docs/player_guide/08-states.md` and `06-politics.md`, the PDF |
| `docs/testing/demographics-phase2-engine-rates-<date>.md` | **create** (Task 10) | the probes' and the gate's results |

---

### Task 1: Probe P1, console option m (the shock terms)

Runs on today's build, so the owner can take P1 while the rest is built.

**Files:**
- Modify: `common/scripted_effects/te_debug_demog_effects.txt` (header list; new effect at the end)
- Modify: `events/te_debug_demog_events.txt` (header list; option m after l)
- Modify: `localization/english/te_events_l_english.yml` (`te_debug_demog.1.m`, `.m.tt`)
- Test: `test_demographics_registry.py` (`TestConsole`)

**Interfaces:**
- Produces: `te_debug_demog_shock_lines` (no scope needed; iterates `every_state`), log tag `TE_DEMOG_SHOCK:`.

- [ ] **Step 1: Write the failing test** (in `TestConsole`)

```python
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
```

- [ ] **Step 2: Run it to see it fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestConsole.test_option_m_logs_the_shock_terms_click_only`
Expected: FAIL, `ValueError: substring not found` (no call yet).

- [ ] **Step 3: Write the effect** (append to `te_debug_demog_effects.txt`; add a `TE_DEMOG_SHOCK` line to the header's list of lines)

```
# ---- m: the shock terms (phase 2 step 4, probe P1) ------------------------------
# Every state in the world with devastation, or in a state region with pollution: its
# mortality and birth reads beside devastation and turmoil (0-1 shares) and its region's
# pollution, then the scope (state names don't render in debug_log). Run it with fast mode
# off and before phase 2, so no term of the census's own is in the reads. Hover a logged
# state's mortality in game: if the tooltip's total is the logged mort, devastation's and
# pollution's lines are in modifier:state_mortality_mult.
te_debug_demog_shock_lines = {
	every_state = {
		limit = {
			OR = {
				devastation > 0.01
				state_region = { pollution_amount > 10 }
			}
		}
		set_variable = { name = te_dg_dbg_read_d value = modifier:state_mortality_mult }
		set_variable = { name = te_dg_dbg_read_b value = modifier:state_birth_rate_mult }
		set_variable = { name = te_dg_dbg_dev value = devastation }
		set_variable = { name = te_dg_dbg_turmoil value = turmoil }
		set_variable = { name = te_dg_dbg_poll value = state_region.pollution_amount }
		debug_log = "TE_DEMOG_SHOCK: mort=[THIS.Var('te_dg_dbg_read_d').GetValue|3]; birth=[THIS.Var('te_dg_dbg_read_b').GetValue|3]; devastation=[THIS.Var('te_dg_dbg_dev').GetValue|3]; turmoil=[THIS.Var('te_dg_dbg_turmoil').GetValue|3]; pollution=[THIS.Var('te_dg_dbg_poll').GetValue|1]; date=[TimeKeeper.GetCurrentDate.GetString]"
		debug_log_scopes = yes
		remove_variable = te_dg_dbg_read_d
		remove_variable = te_dg_dbg_read_b
		remove_variable = te_dg_dbg_dev
		remove_variable = te_dg_dbg_turmoil
		remove_variable = te_dg_dbg_poll
	}
}
```

The `set_variable = { name = te_dg_dbg_poll value = state_region.pollution_amount }` form matches `common/political_movements/new_ideological_movements.txt:73`'s `value = state.state_region.pollution_amount`. The test asserts `value = state_region.pollution_amount` against this line.

- [ ] **Step 4: Add option m** (after option l in `te_debug_demog_events.txt`; add `m` to the header's option list: "m  the shock terms (probe P1): every devastated or polluted state's reads, TE_DEMOG_SHOCK")

```
	# ---- m: the shock terms (probe P1) -------------------------------------
	option = {
		name = te_debug_demog.1.m
		custom_tooltip = {
			text = te_debug_demog.1.m.tt
			set_variable = te_dg_dbg_click
			if = {
				limit = { has_variable = te_dg_dbg_click }
				remove_variable = te_dg_dbg_click
				te_debug_demog_shock_lines = yes
			}
		}
	}
```

Loc (`te_events_l_english.yml`, beside `te_debug_demog.1.l`):

```yaml
 te_debug_demog.1.m:0 "Shock terms: log every devastated or polluted state's birth and death reads"
 te_debug_demog.1.m.tt:0 "Writes a TE_DEMOG_SHOCK line to debug.log for every state in the world with devastation or a polluted region: its birth and mortality modifier totals, devastation, turmoil and pollution, followed by the state's scope. Hover one of those states' mortality in game: if the tooltip's total matches the logged figure, devastation's and pollution's deaths are in the total the census reads."
```

- [ ] **Step 5: Run the test, the console tests and the loc checks**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestConsole && .venv/bin/python organize_loc.py --check && .venv/bin/python scripts/analysis/check_localization_files.py`
Expected: OK; `organize_loc --check` exits 0 (run `organize_loc.py` and stage its output if not).

- [ ] **Step 6: Commit**

```bash
git add common/scripted_effects/te_debug_demog_effects.txt events/te_debug_demog_events.txt localization/english/te_events_l_english.yml test_demographics_registry.py
git commit -m "Demographics phase 2 step 4: console option m logs devastated and polluted states' reads (probe P1)"
```

---

### Task 2: The model's arithmetic (Python twin)

**Files:**
- Modify: `scripts/analysis/demographics_params.py` (new block after `STARVATION_BUCKET`)
- Modify: `scripts/analysis/demographics_model.py`
- Test: `test_demographics_model.py` (new classes `TestRateTerm`, `TestKeptScales`)

**Interfaces:**
- Produces:
  - `P.RATE_TOTAL_MIN = -0.8`, `P.RATE_TERM_MAX = 1.0`, `P.KEPT_SCALE_MIN = -0.9`, `P.KEPT_SCALE_MAX = 4.0`, `P.KEPT_DEATHS_BY_AGE = 1`, `P.KEEP_STARVING_SLOPE = False`, `P.LITERACY_BIRTH_PENALTY = -0.1`.
  - `M.rate_term(target: float, bare: float, replaced: float = 0.0, other: float = 0.0) -> tuple[float, bool]`.
  - `M.kept_scale(engine: float, target: float) -> float`.
  - `M.step(..., births_scale: float = 0.0, deaths_scale: float = 0.0)`, whose result also carries `births_model`, `deaths_model` and `maternal`.
  - `M.model_crude_rates(inp, year=1836) -> tuple[float, float]` (per 1,000 a year).
  - `M.starvation_terms(food_security: float) -> tuple[float, float]` (births, deaths).

- [ ] **Step 1: Write the failing tests**

```python
class TestRateTerm(unittest.TestCase):
    """demographics_model.rate_term: the census's births or deaths modifier for one state (phase 2 step 4)."""

    def test_no_other_term_gives_the_model(self):
        m, clamped = M.rate_term(target=80.0, bare=100.0)
        self.assertAlmostEqual(m, -0.2)
        self.assertFalse(clamped)
        self.assertAlmostEqual(100.0 * (1 + m), 80.0)

    def test_kept_terms_stay_on_top_at_the_bare_curves_weight(self):
        """The engine adds every term (growth probe): with M on, a pop's events are bare x (1 + M + K).
        The state's then come to the model's plus bare x K."""
        m, _ = M.rate_term(target=80.0, bare=100.0)
        kept = 0.3
        self.assertAlmostEqual(100.0 * (1 + m + kept), 80.0 + 100.0 * kept)

    def test_replaced_terms_are_netted(self):
        # literacy's -0.1 x a bare-weighted literacy of 0.4: the replaced sum is -0.1 x 40 over bare 100
        m, _ = M.rate_term(target=80.0, bare=100.0, replaced=P.LITERACY_BIRTH_PENALTY * 40.0)
        self.assertAlmostEqual(100.0 * (1 + m) + P.LITERACY_BIRTH_PENALTY * 40.0, 80.0)

    def test_the_clamp_keeps_the_state_total_in_the_measured_range(self):
        m, clamped = M.rate_term(target=5.0, bare=100.0, other=0.1)
        self.assertAlmostEqual(m, P.RATE_TOTAL_MIN - 0.1)
        self.assertTrue(clamped)
        m, clamped = M.rate_term(target=400.0, bare=100.0)
        self.assertEqual(m, P.RATE_TERM_MAX)
        self.assertTrue(clamped)

    def test_the_clamp_never_pushes_past_the_kept_terms(self):
        """A famine or a plague already past -0.8: M may not push further down."""
        m, clamped = M.rate_term(target=5.0, bare=100.0, other=-1.2)
        self.assertEqual(m, 0.0)
        self.assertTrue(clamped)

    def test_nobody_gets_no_term(self):
        self.assertEqual(M.rate_term(target=0.0, bare=0.0), (0.0, False))

    def test_the_bounds_are_the_measured_ones(self):
        self.assertEqual(P.RATE_TOTAL_MIN, -0.8)
        self.assertEqual(P.RATE_TERM_MAX, 1.0)


class TestKeptScales(unittest.TestCase):
    """The census's ring follows the engine: the step scales its rates by how far the engine ran from the target."""

    def test_scale_is_engine_over_target(self):
        self.assertAlmostEqual(M.kept_scale(engine=105.0, target=100.0), 0.05)
        self.assertEqual(M.kept_scale(engine=50.0, target=0.0), 0.0)
        self.assertEqual(M.kept_scale(engine=1.0, target=100.0), P.KEPT_SCALE_MIN)
        self.assertEqual(M.kept_scale(engine=1000.0, target=100.0), P.KEPT_SCALE_MAX)

    def test_scaled_step_gives_back_the_models_own_events(self):
        inp = M.Inputs(sol=9.0, literacy=0.2)
        plain, scaled = M.seed(inp, 1836, 1e6), M.seed(inp, 1836, 1e6)
        a = M.step(plain, inp, 1837)
        b = M.step(scaled, inp, 1837, births_scale=0.1, deaths_scale=0.2)
        self.assertAlmostEqual(b["births"], a["births"] * 1.1, places=6)
        self.assertAlmostEqual(b["births_model"], a["births"], places=6)
        self.assertAlmostEqual(b["deaths_model"], a["deaths"], delta=a["deaths"] * 1e-9)
        self.assertGreater(b["deaths"], a["deaths"] * 1.19)

    def test_no_scale_is_the_old_step(self):
        inp = M.Inputs(sol=9.0, literacy=0.2)
        ring = M.seed(inp, 1836, 1e6)
        out = M.step(ring, inp, 1837)
        self.assertEqual(out["births_model"], out["births"])
        self.assertEqual(out["deaths_model"], out["deaths"])

    def test_life_table_and_tfr_stay_the_models(self):
        inp = M.Inputs(sol=9.0, literacy=0.2)
        a = M.step(M.seed(inp, 1836, 1e6), inp, 1837)
        b = M.step(M.seed(inp, 1836, 1e6), inp, 1837, births_scale=0.3, deaths_scale=0.5)
        self.assertEqual((a["e0"], a["tfr"]), (b["e0"], b["tfr"]))
        self.assertAlmostEqual(b["tfr_shown"], a["tfr"] * 1.3)

    def test_crude_rates_of_the_stable_population(self):
        cbr, cdr = M.model_crude_rates(M.Inputs(sol=9.0, literacy=0.2))
        self.assertTrue(20 < cbr < 60 and 15 < cdr < 50, (cbr, cdr))

    def test_starvation_terms_follow_the_engine(self):
        self.assertEqual(M.starvation_terms(0.5), (0.0, 0.0))
        self.assertEqual(M.starvation_terms(0.1), (-0.9, 1.0))
        b, d = M.starvation_terms(0.3)   # (0.4 - 0.3) x 2.5 = 0.25 of the mild penalty
        self.assertAlmostEqual(b, -0.7 * 0.25)
        self.assertAlmostEqual(d, 0.6 * 0.25)
```

`test_scaled_step_gives_back_the_models_own_events` holds deaths_model to the unscaled step only where no group's rate reaches the 100,000 cap. At SoL 9 none does; if a later parameter change makes one cap, loosen that line to a relative 1e-4.

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_model.TestRateTerm test_demographics_model.TestKeptScales`
Expected: FAIL, `AttributeError: module 'demographics_model' has no attribute 'rate_term'`.

- [ ] **Step 3: Add the parameters** (`demographics_params.py`, after `STARVATION_BUCKET`)

```python
# ---- phase 2 step 4: the census sets the engine's births and deaths --------------------------
# docs/superpowers/plans/2026-10-10-demographics-phase2-engine-rates.md §2. The engine adds every term
# into one (1 + total) per pop, linear from -0.9 to +1.0 (growth probe) and floored at 0.
RATE_TOTAL_MIN = -0.8         # the state read with M in it stays at or above this (-0.9 less literacy's -0.1)
RATE_TERM_MAX = 1.0           # M at most +100%: the largest step measured
KEPT_SCALE_MIN = -0.9         # the step's births and deaths scales (the engine's events over the model's target)
KEPT_SCALE_MAX = 4.0
KEPT_DEATHS_BY_AGE = 1        # owner call (c): 1 = the kept deaths by the model's age pattern; 0 = flat (the scale)
KEEP_STARVING_SLOPE = False   # owner call (b): True keeps the curve's extra deaths below SoL 4 on top
LITERACY_BIRTH_PENALTY = -0.1 # literacy_penalty's state_birth_rate_mult (the mod's REPLACE keeps vanilla's)
STARVATION_MILD = {"births": -0.7, "deaths": 0.6}     # starvation_penalty (vanilla code static modifier)
STARVATION_SEVERE = {"births": -0.9, "deaths": 1.0}   # severe_starvation_penalty
STARVATION_MILD_CAP = 0.5     # (threshold - severe threshold) x scaling factor: vanilla's comment
```

- [ ] **Step 4: Add the functions and the step's scales** (`demographics_model.py`)

```python
def rate_term(target, bare, replaced=0.0, other=0.0):
    """The census's births or deaths modifier for one state (phase 2 step 4). Returns (M, clamped).

    The engine gives each pop bare x max(0, 1 + its terms + M) (growth probe), so over a state M adds
    M x bare. M = target / bare - 1 - replaced / bare makes the engine's events the model's (target)
    plus every kept term at the bare curve's weight. All three are in the same units (the walk's:
    events a month x 100,000). `other` is the state read without the census's and fast mode's
    terms: other + M stays at or above RATE_TOTAL_MIN, M never goes below 0 when other alone is
    past it, and M stays at or below RATE_TERM_MAX.
    """
    if bare <= 0:
        return 0.0, False
    m = target / bare - 1 - replaced / bare
    lo = min(0.0, P.RATE_TOTAL_MIN - other)
    if m < lo:
        return lo, True
    if m > P.RATE_TERM_MAX:
        return P.RATE_TERM_MAX, True
    return m, False


def kept_scale(engine, target):
    """How far the engine's births or deaths over a step ran from the model's target, as a scale for the
    step's rates: engine / target - 1, clamped to KEPT_SCALE_MIN..KEPT_SCALE_MAX; 0 with no target."""
    if target <= 0:
        return 0.0
    return clamp(engine / target - 1, P.KEPT_SCALE_MIN, P.KEPT_SCALE_MAX)


def starvation_terms(food_security):
    """(births, deaths) the engine adds for a pop at this food security (vanilla code static modifiers)."""
    if food_security < P.FOOD_SECURITY_SEVERE_STARVATION_THRESHOLD:
        return P.STARVATION_SEVERE["births"], P.STARVATION_SEVERE["deaths"]
    if food_security < P.FOOD_SECURITY_STARVATION_THRESHOLD:
        s = min((P.FOOD_SECURITY_STARVATION_THRESHOLD - food_security) * P.STARVATION_EFFECTS_SCALING_FACTOR,
                P.STARVATION_MILD_CAP)
        return P.STARVATION_MILD["births"] * s, P.STARVATION_MILD["deaths"] * s
    return 0.0, 0.0


def model_crude_rates(inp, year=1836):
    """(births, deaths) per 1,000 a year of the stable population of the state's inputs: the census's
    own rates for a state with no census in the save (demographics_harness.py predict)."""
    ring = seed(inp, year, 100000.0)
    out = step(ring, inp, year + 1)
    return out["births_model"] / 100.0, out["deaths_model"] / 100.0
```

In `step`, add the two keyword arguments and these lines:
- After the `if rates is None: … else: …` block, which leaves `qf, qm, mmr, tfr` and the life tables computed from the model's own rates:

```python
    tfr_model = tfr
    tfr = tfr * (1 + births_scale)
    if deaths_scale:
        if rates is None:
            mult = cause_multipliers(inp)
            work_f, work_m = work_split(inp, mult["work"])
            k = 1 + deaths_scale
            qf, qm = rates_from_multipliers({c: v * k for c, v in mult.items()}, work_f * k, work_m * k)
        else:
            qf = [min(100000.0, q * (1 + deaths_scale)) for q in qf]
            qm = [min(100000.0, q * (1 + deaths_scale)) for q in qm]
    maternal = 0.0
```

  The script scales the cause multipliers before its 100,000 cap, so the twin does too. The replay passes rates already scaled, with both scales 0.
- In the loop, after `births += b`: `maternal += b * mmr / 100000.0`.
- In the returned dict, change `"tfr": tfr` to `"tfr": tfr_model` and add:

```python
            "tfr_shown": tfr, "maternal": maternal,
            "births_model": births / (1 + births_scale),
            "deaths_model": (deaths - maternal) / (1 + deaths_scale) + maternal / (1 + births_scale),
```

- [ ] **Step 5: Run the model tests and the harness tests**

Run: `.venv/bin/python -m unittest test_demographics_model test_demographics_harness`
Expected: OK. `replay_block` calls `step` with the default scales, so every existing replay test is unchanged.

- [ ] **Step 6: Commit**

```bash
git add scripts/analysis/demographics_params.py scripts/analysis/demographics_model.py test_demographics_model.py
git commit -m "Demographics phase 2 step 4: the model's rate term, kept scales and model totals (Python twin)"
```

---

### Task 3: The step takes the kept terms (script)

**Files:**
- Create: `common/scripted_effects/te_demog_rate_effects.txt` (with `te_demog_kept_scales` only; Task 4 adds the rest)
- Modify: `common/scripted_effects/te_demog_effects.txt` (`te_demog_step_begin`, `te_demog_reset_accumulators`, `te_demog_age_slot`, `te_demog_step_finish`, the header's variable list)
- Modify: `scripts/generators/gen_demographics.py` (`constants`: the bounds; `engine_rate_terms`: the literacy constant) and regenerate
- Test: `test_demographics_registry.py` (`_Engine` loads the new file; new class `TestKeptScalesScript`), `test_gen_demographics.py`

**Interfaces:**
- Consumes: `M.step(..., births_scale, deaths_scale)`, `M.kept_scale` (Task 2).
- Produces:
  - **State variables:** `te_dg_bz`, `te_dg_dz` (the last step's scales); `te_dg_cbr_model`, `te_dg_cdr_model` (per 1,000 a year: the model's own, M's next target); `te_dg_tfr_model`.
  - **Constants:** `te_demog_k_kept_scale_min`, `te_demog_k_kept_scale_max`, `te_demog_k_kept_deaths_by_age`, `te_demog_k_rate_total_min`, `te_demog_k_rate_term_max`, `te_demog_k_literacy_birth_penalty`.

- [ ] **Step 1: Write the failing tests**

In `test_demographics_registry.py`:
- Add `RATE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_rate_effects.txt"` beside `FAST_EFFECTS`.
- Add `RATE_EFFECTS` to the list in `_Engine.__init__`: `_raw_blocks([EFFECTS, GENERATED_EFFECTS, WEALTH_EFFECTS, FAST_EFFECTS, RATE_EFFECTS])`.
- Then add, after `TestCohortScript`:

```python
class TestKeptScalesScript(TestCohortScript):
    """te_demog_kept_scales and the step's model totals (phase 2 step 4) against demographics_model.step."""

    def _stepped(self, bz_target, dz_target, full=True):
        eng, ring = self.seed_both()
        pop = self.POP
        # the model's own rates M aimed at, and the engine's expected events over the window
        eng.vars.update(te_dg_cbr_model=40.0, te_dg_cdr_model=30.0,
                        te_dg_eb=40.0 * pop / 1000 * (1 + bz_target), te_dg_ed=30.0 * pop / 1000 * (1 + dz_target))
        eng.trigger_fixtures["te_demog_effects_run"] = full
        return eng, ring

    def test_scales_are_the_engines_events_over_the_target(self):
        eng, _ = self._stepped(0.05, 0.12)
        eng.call("te_demog_step")
        self.assertAlmostEqual(eng.vars["te_dg_bz"], 0.05, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_dz"], 0.12 * P.KEPT_DEATHS_BY_AGE, places=5)

    def test_step_with_kept_scales_matches_the_model(self):
        eng, ring = self._stepped(0.05, 0.12)
        eng.call("te_demog_step")
        out = demographics_model.step(ring, self.INP, self.YEAR + 1, engine_pop=self.POP,
                                      births_scale=0.05, deaths_scale=0.12 * P.KEPT_DEATHS_BY_AGE)
        self.close(eng.vars["te_dg_births"], out["births"], what="births")
        self.close(eng.vars["te_dg_deaths"], out["deaths"], what="deaths")
        self.close(eng.vars["te_dg_cbr_model"], out["births_model"] * 1000 / self.POP, what="cbr_model")
        self.close(eng.vars["te_dg_cdr_model"], out["deaths_model"] * 1000 / self.POP, what="cdr_model")
        self.close(eng.vars["te_dg_tfr"], out["tfr_shown"], what="tfr shown")
        self.close(eng.vars["te_dg_tfr_model"], out["tfr"], what="tfr model")

    def test_no_kept_scales_outside_full(self):
        eng, _ = self._stepped(0.05, 0.12, full=False)
        eng.call("te_demog_step")
        self.assertEqual((eng.vars["te_dg_bz"], eng.vars["te_dg_dz"]), (0.0, 0.0))

    def test_no_target_no_scales(self):
        """An old save or the first step after phase 2 arrives: no te_dg_cbr_model yet."""
        eng, _ = self.seed_both()
        eng.vars.update(te_dg_eb=1.0, te_dg_ed=1.0)
        eng.trigger_fixtures["te_demog_effects_run"] = True
        eng.call("te_demog_step")
        self.assertEqual((eng.vars["te_dg_bz"], eng.vars["te_dg_dz"]), (0.0, 0.0))

    def test_scales_are_clamped(self):
        eng, _ = self._stepped(9.0, -0.99)
        eng.call("te_demog_step")
        self.assertEqual(eng.vars["te_dg_bz"], P.KEPT_SCALE_MAX)
        self.assertEqual(eng.vars["te_dg_dz"], P.KEPT_SCALE_MIN * P.KEPT_DEATHS_BY_AGE)

    def test_the_replay_logs_the_scaled_rates(self):
        """te_debug_demog_replay logs the locals after te_demog_step_begin, so the scales are in the head's tfr
        and multipliers and the harness's replay needs no new field."""
        body = _block(_text(EFFECTS), "te_demog_step_begin")
        self.assertLess(body.index("te_demog_prepare = yes"), body.index("te_demog_kept_scales = yes"))
        self.assertIn("te_demog_step_begin = yes", _block(_text(CONSOLE_EFFECTS), "te_debug_demog_replay"))
```

`seed_both` and `close` are `TestCohortScript`'s. The subclass inherits its tests too; to avoid running them twice, take the two helpers into a mixin (`_CohortHelpers`) that both classes use. The diff is mechanical: move `INP`, `YEAR`, `POP`, `close` and `seed_both` into the mixin.

In `test_gen_demographics.py`, in `TestGenerated` (its `setUpClass` holds the generated values as `cls.values`; the generator is imported as `gen`):

```python
    def test_phase2_constants_match_the_params(self):
        for name, value in (("kept_scale_min", P.KEPT_SCALE_MIN), ("kept_scale_max", P.KEPT_SCALE_MAX),
                            ("kept_deaths_by_age", P.KEPT_DEATHS_BY_AGE), ("rate_total_min", P.RATE_TOTAL_MIN),
                            ("rate_term_max", P.RATE_TERM_MAX),
                            ("literacy_birth_penalty", P.LITERACY_BIRTH_PENALTY)):
            self.assertIn(f"te_demog_k_{name} = {{ value = {gen.lit(value)} }}", self.values, name)
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestKeptScalesScript test_gen_demographics`
Expected: FAIL. The `_raw_blocks` file is missing, then `KeyError: 'te_dg_bz'`; the generator test fails on `te_demog_k_kept_scale_min`.

- [ ] **Step 3: Generate the constants**

In `gen_demographics.constants`, add to `k`:

```python
        "kept_scale_min": P.KEPT_SCALE_MIN, "kept_scale_max": P.KEPT_SCALE_MAX,
        "kept_deaths_by_age": P.KEPT_DEATHS_BY_AGE, "rate_total_min": P.RATE_TOTAL_MIN,
        "rate_term_max": P.RATE_TERM_MAX,
```

In `engine_rate_terms`, after reading `literacy`, emit the constant from the static modifier itself, so the census nets exactly what the engine applies. Then assert the params agree:

```python
    o(f"te_demog_k_literacy_birth_penalty = {{ value = {lit(literacy)} }}")
    assert literacy == P.LITERACY_BIRTH_PENALTY, "literacy_penalty changed: update LITERACY_BIRTH_PENALTY"
```

Run: `.venv/bin/python scripts/generators/gen_demographics.py`. The generator writes formatted tabs itself (`test_tabs_already_formatted`).

- [ ] **Step 4: Write the kept scales** (create `common/scripted_effects/te_demog_rate_effects.txt` with a BOM)

```
# ============================================================================
# DEMOGRAPHICS — the census sets the engine's births and deaths (phase 2 step 4)
# docs/superpowers/plans/2026-10-10-demographics-phase2-engine-rates.md §2
# ============================================================================
# The engine gives every pop curve x max(0, 1 + total) births and deaths, adding every
# term (docs/testing/demographics-growth-probe-results-2026-10-09.md). The census's term M
# (te_demog_rates_refresh) makes a state's events the model's plus the terms kept on top,
# and the census's next step scales its own rates to what the engine did
# (te_demog_kept_scales), so the ring places the kept births and deaths by age.
#
# State variables:
#   te_dg_mb, te_dg_md  M for births and deaths (signed), behind the te_demog_census_* pair
#   te_dg_rate_clamped  1 when the last refresh clamped either term
#   te_dg_bz, te_dg_dz  the scales the last step used (te_dg_eb or te_dg_ed over the target,
#                       less 1); te_dg_dz is 0 under KEPT_DEATHS_BY_AGE = 0
#   te_dg_cbr_model, te_dg_cdr_model, te_dg_tfr_model  the model's own rates (per 1,000 a year;
#                       children per woman): the step's events without the kept scales
# ============================================================================

# THIS = a state at the start of its step, straight after te_demog_prepare and te_demog_flows:
# the year's rates scaled by how far the engine's expected births and deaths over the window
# (te_dg_eb, te_dg_ed, from this step's walk) ran from the model's rates that M aimed at, at
# today's population. Under Full only, and only once a step has stored the model's rates.
te_demog_kept_scales = {
	set_local_variable = { name = te_dg_bz value = 0 }
	set_local_variable = { name = te_dg_dz value = 0 }
	if = {
		limit = {
			te_demog_effects_run = yes
			has_variable = te_dg_cbr_model
			has_variable = te_dg_cdr_model
		}
		if = {
			limit = { var:te_dg_cbr_model > 0 }
			set_local_variable = {
				name = te_dg_bz
				value = {
					value = var:te_dg_eb
					multiply = 1000
					divide = { value = var:te_dg_cbr_model multiply = state_population min = 1 }
					subtract = 1
					min = te_demog_k_kept_scale_min
					max = te_demog_k_kept_scale_max
				}
			}
		}
		if = {
			limit = { var:te_dg_cdr_model > 0 }
			set_local_variable = {
				name = te_dg_dz
				value = {
					value = var:te_dg_ed
					multiply = 1000
					divide = { value = var:te_dg_cdr_model multiply = state_population min = 1 }
					subtract = 1
					min = te_demog_k_kept_scale_min
					max = te_demog_k_kept_scale_max
					multiply = te_demog_k_kept_deaths_by_age
				}
			}
		}
	}
	set_variable = { name = te_dg_bz value = local_var:te_dg_bz }
	set_variable = { name = te_dg_dz value = local_var:te_dg_dz }
	# the model's children per woman before the scale, then the year's rates with it
	set_variable = { name = te_dg_tfr_model value = local_var:te_dg_tfr }
	change_local_variable = { name = te_dg_tfr multiply = { value = local_var:te_dg_bz add = 1 } }
	set_variable = { name = te_dg_tfr value = local_var:te_dg_tfr }
	change_local_variable = { name = te_dg_m_inf multiply = { value = local_var:te_dg_dz add = 1 } }
	change_local_variable = { name = te_dg_m_ext multiply = { value = local_var:te_dg_dz add = 1 } }
	change_local_variable = { name = te_dg_m_chr multiply = { value = local_var:te_dg_dz add = 1 } }
	change_local_variable = { name = te_dg_m_work_f multiply = { value = local_var:te_dg_dz add = 1 } }
	change_local_variable = { name = te_dg_m_work_m multiply = { value = local_var:te_dg_dz add = 1 } }
}
```

`te_dg_eb` sits on the state (the walk's `set_variable`). Precision: `te_dg_cbr_model × state_population` for a 60M state is 3×10⁹, well inside the engine's i64 × 1e-5 range.

- [ ] **Step 5: Wire it into the step** (`te_demog_effects.txt`)

`te_demog_step_begin` becomes:

```
te_demog_step_begin = {
	te_demog_prepare = yes
	te_demog_flows = yes
	te_demog_kept_scales = yes
}
```

In `te_demog_reset_accumulators`, beside `te_dg_births` and `te_dg_deaths`:

```
	set_local_variable = { name = te_dg_mat value = 0 }
```

In `te_demog_age_slot`, after `change_local_variable = { name = te_dg_births add = local_var:te_dg_b }`:

```
	change_local_variable = { name = te_dg_mat add = { value = local_var:te_dg_b multiply = local_var:te_dg_mmr divide = 100000 } }
```

In `te_demog_step_finish`, after `set_variable = { name = te_dg_deaths value = local_var:te_dg_deaths }`:

```
	# the model's own rates without the kept scales: what the census's births and deaths modifiers aim at
	# next (te_demog_rates_refresh). Births: / (1 + bz). Deaths: the cause deaths / (1 + dz), the maternal
	# deaths (which follow the births) / (1 + bz).
	set_variable = {
		name = te_dg_cbr_model
		value = {
			value = local_var:te_dg_births
			divide = { value = local_var:te_dg_bz add = 1 min = 0.1 }
			multiply = 1000
			divide = { value = state_population min = 1 }
		}
	}
	set_variable = {
		name = te_dg_cdr_model
		value = {
			value = local_var:te_dg_deaths
			subtract = local_var:te_dg_mat
			divide = { value = local_var:te_dg_dz add = 1 min = 0.1 }
			add = { value = local_var:te_dg_mat divide = { value = local_var:te_dg_bz add = 1 min = 0.1 } }
			multiply = 1000
			divide = { value = state_population min = 1 }
		}
	}
```

`te_demog_step_finish` runs before `te_demog_set_scale`, whose `te_dg_people` is `state_population`, so the model's rates share the shown CBR's denominator. Add the new variables to the file header's list ("The census … te_dg_cbr_model, te_dg_cdr_model, te_dg_tfr_model, te_dg_bz, te_dg_dz: phase 2 step 4, te_demog_rate_effects.txt").

- [ ] **Step 6: Run the tests**

First make the rule's Full check a default fixture of `_Engine`, as the census log and the clock already are. In `_Engine.__init__`'s `trigger_fixtures`:

```python
        self.trigger_fixtures = {"te_history_country_is_tracked": False, "te_demog_census_log_on": False,
                                 "te_demog_clock_on": False, "te_demog_effects_run": False, **(triggers or {})}
```

Add "and the rule's Full (te_demog_effects_run): off unless a test says" to the comment above it. Every existing step and orchestrator test then runs the phase-1 step as before. The real trigger reads `has_game_rule`, which `_Engine` doesn't know.

Run: `.venv/bin/python -m unittest test_demographics_registry test_gen_demographics test_demographics_harness`
Expected: OK.

- [ ] **Step 7: Commit**

```bash
git add common/scripted_effects/te_demog_rate_effects.txt common/scripted_effects/te_demog_effects.txt common/script_values/te_demog_generated_values.txt scripts/generators/gen_demographics.py test_demographics_registry.py test_gen_demographics.py
git commit -m "Demographics phase 2 step 4: the step scales its births and deaths to the engine's and keeps the model's own rates"
```

---

### Task 4: The census's term M (script), its modifiers and its refresh

**Files:**
- Modify: `common/scripted_effects/te_demog_rate_effects.txt` (`te_demog_rates_refresh`, `te_demog_rates_apply`, `te_demog_rates_clear`)
- Modify: `common/scripted_effects/te_demog_effects.txt` (the walk's `te_dg_w_ebl`; `te_demog_state_yearly` calls the refresh)
- Modify: `common/scripted_effects/te_demog_fast_effects.txt` (`te_demog_state_clock_step` calls the refresh before fast mode's)
- Modify: `common/script_values/te_demog_values.txt` (the applied and multiplier values)
- Modify: `common/static_modifiers/te_demog_modifiers.txt` (four modifiers)
- Modify: `common/scripted_effects/te_debug_demog_effects.txt`, `events/te_debug_demog_events.txt` (option n, probe P3)
- Modify: `localization/english/te_miscellaneous_l_english.yml`, `te_events_l_english.yml`
- Test: `test_demographics_registry.py` (new class `TestRatesScript`)

**Interfaces:**
- Consumes: Task 2's `M.rate_term`; Task 3's `te_dg_cbr_model`, `te_dg_cdr_model`, `te_demog_k_rate_*`, `te_demog_k_literacy_birth_penalty`.
- Produces:
  - **Effects:** `te_demog_rates_refresh` (THIS = ROOT = state, after the census, in the walk's effect). It always sets the locals `te_dg_rate_prev_b`/`_d` (the terms the walk's window ran with) for fast mode.
  - **Script values:** `te_demog_rate_births_applied`, `te_demog_rate_deaths_applied` (state: M while its modifier is on, else 0); `te_demog_fast_births_applied`, `te_demog_fast_deaths_applied`.
  - **Static modifiers:** `te_demog_census_births_up/_down`, `te_demog_census_deaths_up/_down`.

- [ ] **Step 1: Write the failing tests**

```python
class TestRatesScript(unittest.TestCase):
    """te_demog_rates_refresh (te_demog_rate_effects.txt) against demographics_model.rate_term."""

    POP = 1_000_000.0

    def _eng(self, full=True, stepped=1.0, cbr=38.0, cdr=31.0, eb0=475.0 * 1_000_000, ed0=430.0 * 1_000_000,
             ebl=0.2 * 475.0 * 1_000_000, read_b=0.05, read_d=0.04):
        eng = _Engine({"state_population": self.POP, "modifier:state_birth_rate_mult": read_b,
                       "modifier:state_mortality_mult": read_d},
                      triggers={"te_demog_effects_run": full, "te_demog_cohorts_run": True})
        eng.locals.update(te_dg_w_eb0=eb0, te_dg_w_ed0=ed0, te_dg_w_ebl=ebl, te_dg_w_eb=eb0, te_dg_w_ed=ed0)
        eng.vars.update(te_dg_stepped=stepped, te_dg_cbr_model=cbr, te_dg_cdr_model=cdr)
        return eng

    def _want(self, cbr, cdr, eb0, ed0, ebl, other_b, other_d):
        mb, _ = demographics_model.rate_term(cbr * self.POP * 100 / 12, eb0,
                                             replaced=P.LITERACY_BIRTH_PENALTY * ebl, other=other_b)
        md, _ = demographics_model.rate_term(cdr * self.POP * 100 / 12, ed0, other=other_d)
        return mb, md

    def test_script_matches_the_model(self):
        eng = self._eng()
        eng.call("te_demog_rates_refresh")
        mb, md = self._want(38.0, 31.0, 475e6, 430e6, 0.2 * 475e6, 0.05, 0.04)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)
        # births down, deaths down: one modifier of each pair, multiplier |M|
        self.assertAlmostEqual(eng.modifiers["te_demog_census_births_down"], -mb, places=5)
        self.assertAlmostEqual(eng.modifiers["te_demog_census_deaths_down"], -md, places=5)
        self.assertNotIn("te_demog_census_births_up", eng.modifiers)

    def test_script_clamps_like_the_model(self):
        eng = self._eng(cbr=2.0, cdr=400.0, read_b=-0.5)
        eng.call("te_demog_rates_refresh")
        mb, md = self._want(2.0, 400.0, 475e6, 430e6, 0.2 * 475e6, -0.5, 0.04)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertEqual(eng.vars["te_dg_md"], P.RATE_TERM_MAX)
        self.assertEqual(eng.vars["te_dg_rate_clamped"], 1)

    def test_the_prior_term_comes_off_the_read(self):
        """The state read holds last step's M: the clamp's 'other' takes it off."""
        eng = self._eng(cbr=2.0, read_b=-0.5)
        eng.modifiers["te_demog_census_births_down"] = 0.3
        eng.vars["te_dg_mb"] = -0.3
        eng.call("te_demog_rates_refresh")
        mb, _ = self._want(2.0, 31.0, 475e6, 430e6, 0.2 * 475e6, -0.2, 0.04)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertAlmostEqual(eng.locals["te_dg_rate_prev_b"], -0.3)

    def test_the_prior_term_needs_the_modifier(self):
        """A state that lost its modifier (a change of owner, an old save) keeps te_dg_mb: no phantom term."""
        eng = self._eng()
        eng.vars["te_dg_mb"] = -0.3
        eng.call("te_demog_rates_refresh")
        self.assertEqual(eng.locals["te_dg_rate_prev_b"], 0.0)

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
        eng = self._eng(eb0=0.0, ed0=0.0, ebl=0.0)
        eng.call("te_demog_rates_refresh")
        self.assertNotIn("te_dg_mb", eng.vars)

    def test_display_only_clears_the_rates(self):
        eng = self._eng(full=False)
        eng.modifiers.update(te_demog_census_births_down=0.2, te_demog_census_deaths_up=0.1)
        eng.vars.update(te_dg_mb=-0.2, te_dg_md=0.1)
        eng.call("te_demog_rates_refresh")
        self.assertEqual(eng.modifiers, {})
        self.assertNotIn("te_dg_mb", eng.vars)
        self.assertNotIn("te_dg_md", eng.vars)

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

    def test_the_walk_sums_bare_births_by_literacy(self):
        body = _block(_text(EFFECTS), "te_demog_walks")
        self.assertIn("set_local_variable = { name = te_dg_w_ebl value = 0 }", body)
        self.assertIn("change_local_variable = { name = te_dg_w_ebl add = { value = local_var:te_dg_p_eb "
                      "multiply = literacy_rate } }", body)

    def test_the_census_modifiers_are_fixed_sign_unit_fields(self):
        mods = _raw_blocks([ROOT / "common" / "static_modifiers" / "te_demog_modifiers.txt"])
        for name, field, value in (("te_demog_census_births_up", "state_birth_rate_mult", "1"),
                                   ("te_demog_census_births_down", "state_birth_rate_mult", "-1"),
                                   ("te_demog_census_deaths_up", "state_mortality_mult", "1"),
                                   ("te_demog_census_deaths_down", "state_mortality_mult", "-1")):
            got = dict(re.findall(r"^\s*(\w+) = (\S+)", mods[name], re.M))
            got.pop("icon")
            self.assertEqual(got, {field: value}, name)
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestRatesScript`
Expected: FAIL, `AssertionError: effect te_demog_rates_refresh`.

- [ ] **Step 3: The walk's new sum** (`te_demog_walks`)

Beside the other `te_dg_w_*` initialisations: `set_local_variable = { name = te_dg_w_ebl value = 0 }`. After `change_local_variable = { name = te_dg_w_eb0 add = local_var:te_dg_p_eb }`:

```
		# bare births by literacy: the replaced literacy_penalty, which the census's births term nets out
		change_local_variable = { name = te_dg_w_ebl add = { value = local_var:te_dg_p_eb multiply = literacy_rate } }
```

- [ ] **Step 4: The values** (`te_demog_values.txt`, after the fast-mode terms)

```
# State scope: the census's births and deaths terms in force (phase 2 step 4,
# te_demog_rate_effects.txt): M while its modifier is on, else 0. Read through has_modifier,
# so a state that lost its modifier (a change of owner, an old save) but kept te_dg_mb
# subtracts nothing that isn't there.
te_demog_rate_births_applied = {
	value = 0
	if = {
		limit = {
			OR = {
				has_modifier = te_demog_census_births_up
				has_modifier = te_demog_census_births_down
			}
		}
		value = var:te_dg_mb
	}
}

te_demog_rate_deaths_applied = {
	value = 0
	if = {
		limit = {
			OR = {
				has_modifier = te_demog_census_deaths_up
				has_modifier = te_demog_census_deaths_down
			}
		}
		value = var:te_dg_md
	}
}

# The multipliers of the fixed-sign pairs: |M| on the side M is on.
te_demog_rate_births_up = { value = var:te_dg_mb min = 0 }
te_demog_rate_births_down = { value = var:te_dg_mb multiply = -1 min = 0 }
te_demog_rate_deaths_up = { value = var:te_dg_md min = 0 }
te_demog_rate_deaths_down = { value = var:te_dg_md multiply = -1 min = 0 }

# Fast mode's terms in force, the same way (te_demog_fast_effects.txt).
te_demog_fast_births_applied = {
	value = 0
	if = {
		limit = { has_modifier = te_demog_fast_births }
		value = var:te_dg_fast_fb
	}
}

te_demog_fast_deaths_applied = {
	value = 0
	if = {
		limit = { has_modifier = te_demog_fast_deaths }
		value = var:te_dg_fast_fd
	}
}
```

- [ ] **Step 5: The refresh** (append to `te_demog_rate_effects.txt`; add `te_dg_w_ebl` to the header's notes)

```
# THIS = ROOT = a state, straight after te_demog_state_census in the effect that ran its walks (its
# yearly pulse, or a step of fast mode's clock): the census's births and deaths terms.
#   M_b = target_b / bare_b - 1 - literacy_penalty x bare_b-by-literacy / bare_b
#   M_d = target_d / bare_d - 1
# target = the model's rate (te_dg_cbr_model, per 1,000 a year) x today's people, a month x 100,000,
# the walk's units (te_dg_w_eb0, te_dg_w_ed0). Clamped: the state read without the census's and
# fast mode's own terms ("other") plus M stays at or above te_demog_k_rate_total_min, M is never
# below 0 when other alone is past that, and M is at most te_demog_k_rate_term_max.
# Always leaves te_dg_rate_prev_b/_d, the terms the walk's window ran with, for fast mode.
# A seed (te_dg_stepped 0) leaves the terms as they are.
te_demog_rates_refresh = {
	set_local_variable = { name = te_dg_rate_prev_b value = te_demog_rate_births_applied }
	set_local_variable = { name = te_dg_rate_prev_d value = te_demog_rate_deaths_applied }
	if = {
		limit = { NOT = { te_demog_effects_run = yes } }
		te_demog_rates_clear = yes
	}
	else_if = {
		limit = {
			has_variable = te_dg_stepped
			has_variable = te_dg_cbr_model
			has_variable = te_dg_cdr_model
			local_var:te_dg_w_eb0 > 0
			local_var:te_dg_w_ed0 > 0
		}
		if = {
			limit = { var:te_dg_stepped > 0 }
			set_local_variable = { name = te_dg_rate_clamped value = 0 }
			# births
			set_local_variable = {
				name = te_dg_rate_m
				value = {
					value = var:te_dg_cbr_model
					multiply = state_population
					multiply = 100
					divide = 12
					divide = local_var:te_dg_w_eb0
					subtract = 1
					subtract = {
						value = local_var:te_dg_w_ebl
						multiply = te_demog_k_literacy_birth_penalty
						divide = local_var:te_dg_w_eb0
					}
				}
			}
			set_local_variable = {
				name = te_dg_rate_lo
				value = {
					value = te_demog_k_rate_total_min
					subtract = modifier:state_birth_rate_mult
					add = local_var:te_dg_rate_prev_b
					add = te_demog_fast_births_applied
					max = 0
				}
			}
			te_demog_rate_clamp = yes
			set_variable = { name = te_dg_mb value = local_var:te_dg_rate_m }
			# deaths
			set_local_variable = {
				name = te_dg_rate_m
				value = {
					value = var:te_dg_cdr_model
					multiply = state_population
					multiply = 100
					divide = 12
					divide = local_var:te_dg_w_ed0
					subtract = 1
				}
			}
			set_local_variable = {
				name = te_dg_rate_lo
				value = {
					value = te_demog_k_rate_total_min
					subtract = modifier:state_mortality_mult
					add = local_var:te_dg_rate_prev_d
					add = te_demog_fast_deaths_applied
					max = 0
				}
			}
			te_demog_rate_clamp = yes
			set_variable = { name = te_dg_md value = local_var:te_dg_rate_m }
			set_variable = { name = te_dg_rate_clamped value = local_var:te_dg_rate_clamped }
			te_demog_rates_apply = yes
		}
	}
}

# local te_dg_rate_m into local_var:te_dg_rate_lo .. te_demog_k_rate_term_max, noting a clamp.
te_demog_rate_clamp = {
	if = {
		limit = { local_var:te_dg_rate_m < local_var:te_dg_rate_lo }
		set_local_variable = { name = te_dg_rate_m value = local_var:te_dg_rate_lo }
		set_local_variable = { name = te_dg_rate_clamped value = 1 }
	}
	else_if = {
		limit = { local_var:te_dg_rate_m > te_demog_k_rate_term_max }
		set_local_variable = { name = te_dg_rate_m value = te_demog_k_rate_term_max }
		set_local_variable = { name = te_dg_rate_clamped value = 1 }
	}
}

# THIS = ROOT = a state: the one refresh site of te_demog_census_*. Removed and re-applied
# (docs/systems/mod_systems.md, the dynamic-modifier scaling pattern); one of each pair at most.
te_demog_rates_apply = {
	te_demog_rates_remove = yes
	if = {
		limit = { var:te_dg_mb > 0 }
		add_modifier = { name = te_demog_census_births_up multiplier = te_demog_rate_births_up }
	}
	else_if = {
		limit = { var:te_dg_mb < 0 }
		add_modifier = { name = te_demog_census_births_down multiplier = te_demog_rate_births_down }
	}
	if = {
		limit = { var:te_dg_md > 0 }
		add_modifier = { name = te_demog_census_deaths_up multiplier = te_demog_rate_deaths_up }
	}
	else_if = {
		limit = { var:te_dg_md < 0 }
		add_modifier = { name = te_demog_census_deaths_down multiplier = te_demog_rate_deaths_down }
	}
}

te_demog_rates_remove = {
	if = {
		limit = { has_modifier = te_demog_census_births_up }
		remove_modifier = te_demog_census_births_up
	}
	if = {
		limit = { has_modifier = te_demog_census_births_down }
		remove_modifier = te_demog_census_births_down
	}
	if = {
		limit = { has_modifier = te_demog_census_deaths_up }
		remove_modifier = te_demog_census_deaths_up
	}
	if = {
		limit = { has_modifier = te_demog_census_deaths_down }
		remove_modifier = te_demog_census_deaths_down
	}
}

# THIS = a state: the census's terms off (Display only, Disabled), with their variables, so the
# next walk takes nothing off its average and the next step no kept scale.
te_demog_rates_clear = {
	te_demog_rates_remove = yes
	if = {
		limit = { has_variable = te_dg_mb }
		remove_variable = te_dg_mb
	}
	if = {
		limit = { has_variable = te_dg_md }
		remove_variable = te_dg_md
	}
	if = {
		limit = { has_variable = te_dg_rate_clamped }
		remove_variable = te_dg_rate_clamped
	}
}
```

The test file's `te_demog_rates_apply` only adds or removes in `te_demog_rate_effects.txt` (`te_demog_rates_remove` is in the same file). `test_one_refresh_site` checks the file, not the block, so the helper is allowed.

`modifier:state_birth_rate_mult` in an effect's value block, in state scope, is the read `te_demog_mult_*` already uses (`modifier:<type>`).

- [ ] **Step 6: Call it** (the orchestrators)

`te_demog_state_yearly`'s last `if` becomes:

```
	if = {
		limit = { NOT = { te_demog_clock_on = yes } }
		te_demog_state_census = yes
		te_demog_rates_refresh = yes
	}
```

`te_demog_state_clock_step` becomes:

```
te_demog_state_clock_step = {
	if = {
		limit = { te_demog_census_log_on = yes }
		te_debug_demog_pulse_line = yes
	}
	te_demog_walks = yes
	te_demog_state_census = yes
	te_demog_rates_refresh = yes
	te_demog_fast_refresh_rates = yes
}
```

Update `TestFastMode.STUBS` with `"te_demog_rates_refresh": "set_variable = { name = census_rates value = 1 }"`. In `test_a_clock_step_walks_steps_and_refreshes_the_rates`, assert `eng.vars.get("census_rates") == 1.0`.

The other tests that run `te_demog_state_yearly` (`TestStep.test_orchestrator_dispatch`, `TestTrend`'s re-seed tests) need no stub. With `te_demog_effects_run` off by default (Task 3), the real refresh takes its clear branch, which reads no walk local.

- [ ] **Step 7: The modifiers and their loc**

Append to `common/static_modifiers/te_demog_modifiers.txt`:

```
# Phase 2 step 4 (te_demog_rate_effects.txt): the census sets each state's births and deaths.
# One of each pair at a time, multiplier |M| (no negative multiplier: fixed-sign pairs).
te_demog_census_births_up = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
	state_birth_rate_mult = 1
}

te_demog_census_births_down = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	state_birth_rate_mult = -1
}

te_demog_census_deaths_up = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	state_mortality_mult = 1
}

te_demog_census_deaths_down = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
	state_mortality_mult = -1
}
```

Loc (`te_miscellaneous_l_english.yml`, beside `te_demog_family_limitation`; owner may rename):

```yaml
 te_demog_census_births_up:0 "Demographic Profile"
 te_demog_census_births_up_desc:0 "Births here follow the state's census: how many of its women are of childbearing age, how many children families want, and the means they have to plan them. Standard of living alone no longer sets the rate."
 te_demog_census_births_down:0 "Demographic Profile"
 te_demog_census_births_down_desc:0 "Births here follow the state's census: how many of its women are of childbearing age, how many children families want, and the means they have to plan them. Standard of living alone no longer sets the rate."
 te_demog_census_deaths_up:0 "Demographic Profile"
 te_demog_census_deaths_up_desc:0 "Deaths here follow the state's census: the ages of its people and what each age dies of, from infection in childhood to chronic illness in old age. Standard of living alone no longer sets the rate."
 te_demog_census_deaths_down:0 "Demographic Profile"
 te_demog_census_deaths_down_desc:0 "Deaths here follow the state's census: the ages of its people and what each age dies of, from infection in childhood to chronic illness in old age. Standard of living alone no longer sets the rate."
```

- [ ] **Step 8: Owner call (b), only if the owner keeps the slope** (skip under the recommendation)

In `gen_demographics.engine_curves`, emit the curve at SoL 4 or above:

```python
    if P.KEEP_STARVING_SLOPE:
        fed = [(0, G.monthly_mortality(d.equilibrium_sol, d)), (d.equilibrium_sol, G.monthly_mortality(d.equilibrium_sol, d)),
               (d.max_sol, G.monthly_mortality(d.max_sol, d)), (d.stable_sol, G.monthly_mortality(d.stable_sol, d))]
        _piecewise_sol(o, "te_demog_pop_engine_deaths_fed",
                       "Pop scope: the engine's deaths at this pop's SoL or 4, whichever is higher (owner call (b)).",
                       fed, 100000)
```

Then:
- **In the walk,** sum `change_local_variable = { name = te_dg_w_ed4 add = te_demog_pop_engine_deaths_fed }` (initialised to 0).
- **In the refresh's deaths target,** after `divide = 12`, add `add = { value = local_var:te_dg_w_ed0 subtract = local_var:te_dg_w_ed4 }`. This is the slope's extra deaths, kept on top.
- **In the model,** pass the same sum to `rate_term`'s target.
- **The test:** `test_script_matches_the_model` with `te_dg_w_ed4` set and the target raised by the same amount.

- [ ] **Step 9: Option n, the census's rates for the capital** (probe P3)

In `te_debug_demog_effects.txt`, add `te_debug_demog_rate_lines` (THIS = the capital; copy then log then remove, as the census line does):

```
# ---- n: the census's rates (phase 2 step 4, probe P3) -----------------------------
# THIS = the capital: its census terms, the terms in force, the kept scales of its last step,
# the model's rates and the engine's expected events over the last window, the reads.
te_debug_demog_rate_lines = {
	set_variable = { name = te_dg_dbg_mb value = 0 }
	set_variable = { name = te_dg_dbg_md value = 0 }
	if = {
		limit = { has_variable = te_dg_mb }
		set_variable = { name = te_dg_dbg_mb value = var:te_dg_mb }
	}
	if = {
		limit = { has_variable = te_dg_md }
		set_variable = { name = te_dg_dbg_md value = var:te_dg_md }
	}
	set_variable = { name = te_dg_dbg_ab value = te_demog_rate_births_applied }
	set_variable = { name = te_dg_dbg_ad value = te_demog_rate_deaths_applied }
	set_variable = { name = te_dg_dbg_fb value = te_demog_fast_births_applied }
	set_variable = { name = te_dg_dbg_fd value = te_demog_fast_deaths_applied }
	set_variable = { name = te_dg_dbg_read_b value = modifier:state_birth_rate_mult }
	set_variable = { name = te_dg_dbg_read_d value = modifier:state_mortality_mult }
	debug_log = "TE_DEMOG_RATES: mb=[THIS.Var('te_dg_dbg_mb').GetValue|4]; md=[THIS.Var('te_dg_dbg_md').GetValue|4]; applied_b=[THIS.Var('te_dg_dbg_ab').GetValue|4]; applied_d=[THIS.Var('te_dg_dbg_ad').GetValue|4]; fast_b=[THIS.Var('te_dg_dbg_fb').GetValue|4]; fast_d=[THIS.Var('te_dg_dbg_fd').GetValue|4]; read_b=[THIS.Var('te_dg_dbg_read_b').GetValue|4]; read_d=[THIS.Var('te_dg_dbg_read_d').GetValue|4]; bz=[THIS.Var('te_dg_bz').GetValue|4]; dz=[THIS.Var('te_dg_dz').GetValue|4]; cbr_model=[THIS.Var('te_dg_cbr_model').GetValue|3]; cdr_model=[THIS.Var('te_dg_cdr_model').GetValue|3]; eb=[THIS.Var('te_dg_eb').GetValue|0]; ed=[THIS.Var('te_dg_ed').GetValue|0]; clamped=[THIS.Var('te_dg_rate_clamped').GetValue|0]; date=[TimeKeeper.GetCurrentDate.GetString]"
	remove_variable = te_dg_dbg_mb
	remove_variable = te_dg_dbg_md
	remove_variable = te_dg_dbg_ab
	remove_variable = te_dg_dbg_ad
	remove_variable = te_dg_dbg_fb
	remove_variable = te_dg_dbg_fd
	remove_variable = te_dg_dbg_read_b
	remove_variable = te_dg_dbg_read_d
}
```

- **Option n in `te_debug_demog_events.txt`:** the click-guard pattern of option m, with `trigger = { exists = capital }` and `capital = { te_debug_demog_rate_lines = yes }` inside the guard.
- **Loc keys:** `te_debug_demog.1.n` = "Census rates: log our capital's births and deaths terms" and `.n.tt`, in option l's register:
  - what each field is;
  - that read_b less applied_b less fast_b is the kept state-level terms;
  - that eb against cbr_model × people / 1,000 is the step's births scale.
- **Test** (`TestConsole`): `test_option_n_logs_the_rates_click_only`, the same shape as option m's. It asserts the call is click-guarded and that every `te_dg_dbg_*` the effect sets is removed.

- [ ] **Step 10: Run everything and the audits**

Run:
```bash
.venv/bin/python -m unittest test_demographics_registry test_demographics_model test_gen_demographics
.venv/bin/python organize_loc.py --check
.venv/bin/python scripts/analysis/check_localization_files.py
python3 scripts/format_paradox_tabs.py --check common/scripted_effects/te_demog_rate_effects.txt common/scripted_effects/te_demog_effects.txt common/scripted_effects/te_demog_fast_effects.txt common/script_values/te_demog_values.txt common/static_modifiers/te_demog_modifiers.txt common/scripted_effects/te_debug_demog_effects.txt events/te_debug_demog_events.txt
.venv/bin/python script_argument_audit.py --strict
.venv/bin/python loc_coverage_audit.py --strict
.venv/bin/python empty_effect_audit.py --strict
.venv/bin/python modifier_multiplier_var_audit.py --strict
```
Expected: all OK. `loc_coverage_audit` needs the four modifiers' names and descriptions, and `modifier_multiplier_var_audit` passes the script-value multipliers as it passes fast mode's.

- [ ] **Step 11: Commit**

```bash
git add common/scripted_effects/te_demog_rate_effects.txt common/scripted_effects/te_demog_effects.txt common/scripted_effects/te_demog_fast_effects.txt common/script_values/te_demog_values.txt common/static_modifiers/te_demog_modifiers.txt common/scripted_effects/te_debug_demog_effects.txt events/te_debug_demog_events.txt localization/english/ test_demographics_registry.py
git commit -m "Demographics phase 2 step 4: the census's births and deaths terms, refreshed at each step (Full only)"
```

---

### Task 5: Fast mode composes with M

**Files:**
- Modify: `common/scripted_effects/te_demog_fast_effects.txt` (`te_demog_fast_refresh_rates`, its comment)
- Test: `test_demographics_registry.py` (`TestFastMode`)

**Interfaces:**
- Consumes: the locals `te_dg_rate_prev_b`/`_d` and `te_demog_rate_births_applied`/`_deaths_applied` (Task 4).

- [ ] **Step 1: Write the failing tests** (in `TestFastMode`)

```python
    def _both(self, eng, eb, eb0, ed, ed0):
        """A clock step's two refreshes, as te_demog_state_clock_step runs them."""
        eng.locals.update(te_dg_w_eb=eb, te_dg_w_eb0=eb0, te_dg_w_ed=ed, te_dg_w_ed0=ed0, te_dg_w_ebl=0.0)
        eng.call("te_demog_rates_refresh")
        eng.call("te_demog_fast_refresh_rates")

    def _eng_full(self):
        eng = self._eng(True, {"state_population": 1000.0, "modifier:state_birth_rate_mult": 0.0,
                               "modifier:state_mortality_mult": 0.0},
                        triggers={"te_demog_effects_run": True})
        eng.vars.update(te_dg_stepped=1.0, te_dg_cbr_model=36.0, te_dg_cdr_model=24.0)
        return eng

    def test_fast_mode_scales_the_census_target(self):
        """K = 4: the engine runs 4 x (1 + kept + M) on average, M being the census's term."""
        eng = self._eng_full()
        # bare 475 a month per person; the walk's average multiplier 1.05 (kept terms +0.05)
        self._both(eng, eb=1.05 * 475e3, eb0=475e3, ed=0.98 * 430e3, ed0=430e3)
        mb = eng.vars["te_dg_mb"]
        self.assertAlmostEqual(eng.vars["te_dg_fast_fb"], 3 * (1.05 + mb), places=5)

    def test_fast_and_census_terms_reach_a_joint_fixed_point(self):
        eng = self._eng_full()
        self._both(eng, eb=1.05 * 475e3, eb0=475e3, ed=0.98 * 430e3, ed0=430e3)
        mb, fb = eng.vars["te_dg_mb"], eng.vars["te_dg_fast_fb"]
        md, fd = eng.vars["te_dg_md"], eng.vars["te_dg_fast_fd"]
        # the next walk sees both terms applied, and so does the state read; nothing else changed
        eng.fixtures.update({"modifier:state_birth_rate_mult": mb + fb, "modifier:state_mortality_mult": md + fd})
        self._both(eng, eb=(1.05 + mb + fb) * 475e3, eb0=475e3, ed=(0.98 + md + fd) * 430e3, ed0=430e3)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fb"], fb, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fd"], fd, places=5)
```

Existing fast-mode tests call `te_demog_fast_refresh_rates` alone. Their fixtures must now set `te_dg_rate_prev_b`/`_d` (0.0) in `_refresh`: `eng.locals.update(te_dg_rate_prev_b=0.0, te_dg_rate_prev_d=0.0, …)`. Without a census term, `te_demog_rate_births_applied` reads 0, so their figures are unchanged.

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestFastMode`
Expected: FAIL. `fast_fb` comes out as 3 × 1.05 + 3 × M_prev-less, not 3 × (1.05 + mb).

- [ ] **Step 3: Implement** (`te_demog_fast_refresh_rates`; the births block, deaths the same with `_d`/`ed`)

```
		set_variable = {
			name = te_dg_fast_fb
			value = {
				value = local_var:te_dg_w_eb
				divide = { value = local_var:te_dg_w_eb0 min = 0.00001 }
				subtract = local_var:te_dg_fast_prev_b
				subtract = local_var:te_dg_rate_prev_b
				add = te_demog_rate_births_applied
				min = 0
				multiply = te_demog_fast_k_minus_1
			}
		}
```

Extend the effect's comment:
- The walk's average holds last step's census term (`te_dg_rate_prev_b`, which `te_demog_rates_refresh` leaves) and fast mode's own. Both come off, and the census's new term goes in.
- So the engine runs K × (the census's target plus the kept terms) (plan §2, "Fast mode's ×K").
- `te_demog_rates_refresh` must run first, in the same effect.

- [ ] **Step 4: Run the fast-mode and rates tests**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestFastMode test_demographics_registry.TestRatesScript`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add common/scripted_effects/te_demog_fast_effects.txt test_demographics_registry.py
git commit -m "Demographics phase 2 step 4: fast mode scales the census's target, not the curves"
```

---

### Task 6: The replaced lines come off (§8.4 and the inverse INJECTs)

Built to the recommendations in §3 (a). Each owner ruling changes one row of `P.ENGINE_LINES_KEPT` and the matching file line.

**Files:**
- Modify: `common/laws/modified_health_system.txt` (inverse lines inside the three existing `institution_modifier` INJECTs)
- Modify: `common/laws/te_demog_law_injections.txt` (child labour inside the existing `INJECT:law_child_labor_allowed`; new INJECTs for `law_restricted_child_labor` and the four women's-rights laws)
- Modify: `common/laws/extra_laws.txt` (remove the family-policy laws' birth lines; the augmentation laws' mortality lines become chronic treatment)
- Modify: `common/technology/technologies/era_6.txt`, `era_7.txt` (remove `modern_vaccines`', `antibiotic_mass_production`'s, `contraceptive_pill`'s and `second_wave_feminism`'s lines), `era_8.txt` (`sexual_revolution`)
- Modify: `common/institutions/extra_institutions.txt` (Consumer Protection's −0.01)
- Modify: `scripts/analysis/demographics_params.py` (`TREATMENT_CAP["chronic"] = 0.85`; the line tables), `scripts/analysis/demographics_modifiers.py` (`engine_rate_lines`)
- Test: `test_demographics_modifiers.py` (new class `TestEngineRateLines`), `test_demographics_harness.py` (the medicine scenarios stay in band)

**Interfaces:**
- Produces:
  - `DM.engine_rate_lines(root=ROOT) -> dict[tuple[str, str, str, str], float]`: (kind, key, block, field) → the net value the engine applies, with vanilla's and the mod's lines summed per entity as the engine sums an INJECT.
  - `P.ENGINE_LINES_KEPT: frozenset[str]`: the carriers whose lines stay on top.

- [ ] **Step 1: Write the failing test**

```python
RATE_FIELDS = re.compile(r"^state_(birth_rate|mortality|mortality_wealth|\w+_mortality)_mult$")


class TestEngineRateLines(unittest.TestCase):
    """Phase 2 step 4: every birth or mortality line a law, technology or institution carries either nets to
    nothing (the census replaces it: §8.4, the inverse INJECTs) or belongs to a carrier the owner keeps on top."""

    @classmethod
    def setUpClass(cls):
        cls.lines = DM.engine_rate_lines()

    def test_every_line_is_replaced_or_kept(self):
        # the census's own script-only types (state_work_mortality_mult and the like) are inputs, not engine lines
        live = {k: v for k, v in self.lines.items()
                if abs(v) > 1e-9 and RATE_FIELDS.match(k[3]) and k[3] not in P.DEMOG_TYPES}
        unexpected = sorted(k for k in live if k[1] not in P.ENGINE_LINES_KEPT)
        self.assertEqual(unexpected, [], "a birth or mortality line the census neither replaces nor keeps")

    def test_the_vanilla_lines_the_census_replaces_net_to_zero(self):
        for law, block, field in (("law_charitable_health_system", "institution_modifier", "state_mortality_mult"),
                                  ("law_public_health_insurance", "institution_modifier", "state_mortality_mult"),
                                  ("law_private_health_insurance", "institution_modifier", "state_mortality_wealth_mult"),
                                  ("law_child_labor_allowed", "modifier", "state_peasants_mortality_mult"),
                                  ("law_restricted_child_labor", "modifier", "state_laborers_mortality_mult"),
                                  ("law_no_womens_rights", "modifier", "state_birth_rate_mult"),
                                  ("law_women_in_the_fields", "modifier", "state_birth_rate_mult")):
            self.assertAlmostEqual(self.lines.get(("law", law, block, field), 0.0), 0.0, msg=(law, field))

    def test_the_kept_carriers_exist(self):
        carriers = {k[1] for k in self.lines}
        self.assertEqual(sorted(P.ENGINE_LINES_KEPT - carriers), [])

    def test_augmentation_moves_to_chronic_treatment(self):
        carriers = DM.load_carriers()
        chronic = {c.key: c.value for c in carriers if c.type == "state_chronic_treatment_add"}
        self.assertEqual(chronic.get("law_medical_augmentation_only"), 0.10)
        self.assertEqual(chronic.get("law_unrestricted_augmentation"), 0.05)
        self.assertEqual(chronic.get("law_regulated_augmentation_market"), 0.05)
        self.assertEqual(chronic.get("law_mandatory_augmentation"), 0.05)   # owner to confirm (§3 (a))
        self.assertEqual(P.TREATMENT_CAP["chronic"], 0.85)
```

`DM`, `P` and `re` are imported as the module's existing tests do.

- [ ] **Step 2: Run it to see it fail**

Run: `.venv/bin/python -m unittest test_demographics_modifiers.TestEngineRateLines`
Expected: FAIL, `AttributeError: module 'demographics_modifiers' has no attribute 'engine_rate_lines'`.

- [ ] **Step 3: The table and the reader**

In `demographics_params.py`:

```python
# Phase 2 step 4, owner call (a): carriers whose birth or mortality lines stay on top of the census's term
# (plan §3). Every other law, technology or institution line nets to zero (Task 6's removals and INJECTs).
ENGINE_LINES_KEPT = frozenset({
    "law_legal_limbo", "law_basic_protections", "law_comprehensive_rights", "law_full_equality_and_protection",
    "law_protected_class", "law_state_eugenics_program", "mental_health_awareness", "biological_immortality",
    "mind_backups",
})
```

The test's `RATE_FIELDS` doesn't match `state_mortality_turmoil_mult` (Militarized Police, kept by construction). The decree and the static modifiers aren't laws, techs or institutions, so the test doesn't see them.

In `demographics_modifiers.py`. ModState's parser keeps the last of two scalar keys, where the engine sums an INJECT, so read vanilla and the mod apart:

```python
def engine_rate_lines(root=ROOT):
    """{(kind, key, block, field): net value} for every `*_mult` line in a law's `modifier` or
    `institution_modifier`, a technology's or an institution's `modifier`, vanilla's and the mod's summed
    as the engine sums an INJECT (scripting_best_practices.md § INJECT). kind: law, technology, institution."""
    from paradox_file_parser import ParadoxFileParser

    files = {"law": ("laws", "laws"), "technology": ("technologies", "technology/technologies"),
             "institution": ("institutions", "institutions")}
    out = {}

    def w(v):
        """A value without its ("=", …) wrapper: a tuple from the parser, a list from vanilla_parsed's JSON."""
        return v[1] if isinstance(v, (list, tuple)) and len(v) == 2 and v[0] == "=" else v

    def add(kind, key, body):
        body = w(body)
        if not isinstance(body, dict):
            return
        for block in ("modifier", "institution_modifier"):
            for field, value in (w(body.get(block)) or {}).items():
                if field.endswith("_mult"):
                    k = (kind, key, block, field)
                    out[k] = out.get(k, 0.0) + float(w(value))

    for kind, (snap, sub) in files.items():
        vanilla = json.loads((Path(root) / "vanilla_parsed" / "common" / f"{snap}.json").read_text(encoding="utf-8"))
        for key, body in vanilla.get("data", vanilla).items():
            add(kind, key, body)
        for path in sorted((Path(root) / "common" / sub).glob("*.txt")):
            parser = ParadoxFileParser()
            parser.parse_file(str(path), apply_directives=False)
            for name, body in parser.data.items():
                directive, _, key = name.rpartition(":")
                if directive == "REPLACE":
                    for k in [k for k in out if k[0] == kind and k[1] == key]:
                        del out[k]
                add(kind, key, body)
    return out
```

A key that appears twice in one parsed block (one file, two lines) is a list in the parser's output. If `float(w(value))` raises on one, sum the list's items instead. The test's real data will tell; keep the first version simple and fix it there.

- [ ] **Step 4: The inverse INJECTs**

In `modified_health_system.txt`, inside each existing `institution_modifier`:
- `law_charitable_health_system`: `state_mortality_mult = 0.03`;
- `law_private_health_insurance`: `state_mortality_wealth_mult = 0.002`;
- `law_public_health_insurance`: `state_mortality_mult = 0.05`.

Add one header line: "state_mortality_mult / state_mortality_wealth_mult: vanilla's lines cancelled; the census's access × treatment replaces them (demographics phase 2 step 4)".

In `te_demog_law_injections.txt`:

```
INJECT:law_child_labor_allowed = {
	modifier = {
		state_work_mortality_mult = 0.1
		# vanilla's class lines cancelled: the census's work term replaces them (phase 2 step 4)
		state_laborers_mortality_mult = -0.05
		state_machinists_mortality_mult = -0.05
		state_farmers_mortality_mult = -0.05
		state_peasants_mortality_mult = -0.05
	}
}

INJECT:law_restricted_child_labor = {
	modifier = {
		state_laborers_mortality_mult = -0.02
		state_farmers_mortality_mult = -0.02
		state_peasants_mortality_mult = -0.02
	}
}

# Women's rights' birth lines cancelled (owner call (a), plan §3): the census's fertility is fitted
# to history without them.
INJECT:law_no_womens_rights = {
	modifier = {
		state_birth_rate_mult = -0.05
	}
}

INJECT:law_women_in_the_fields = {
	modifier = {
		state_birth_rate_mult = 0.1
	}
}

INJECT:law_women_in_the_workplace = {
	modifier = {
		state_birth_rate_mult = 0.05
	}
}

INJECT:law_womens_suffrage = {
	modifier = {
		state_birth_rate_mult = 0.05
	}
}
```

Before adding a new `INJECT:` for a law, check that no other mod file INJECTs it (`git grep -n "INJECT:law_women_in_the_fields"`). Two INJECT blocks on one law in different files are unread in this repo; if one exists, add the lines there instead.

- [ ] **Step 5: §8.4's removals and augmentation's chronic lines**

Delete these lines (each with its comment, if it has one of its own):
- `extra_laws.txt:2693, 2708, 2722, 2736` (the family-policy laws' `state_birth_rate_mult`);
- `era_6.txt:430-431` (`modern_vaccines`) and `era_7.txt:485-486` (`antibiotic_mass_production`): `state_mortality_mult` and `state_birth_rate_mult`;
- `era_7.txt:505` (`contraceptive_pill`), `era_7.txt:530` (`second_wave_feminism`) and `era_8.txt:283` (`sexual_revolution`);
- `extra_institutions.txt:159` (Consumer Protection).

In the four augmentation laws (`extra_laws.txt:1684, 1727, 1766, 1802`):
- Replace `state_mortality_mult` with `state_chronic_treatment_add`: +0.10 for Medical Only, +0.05 for the other three.
- Keep each line in the block it was in: `modifier` for Unrestricted, `institution_modifier` for the three per-level laws.

Set `TREATMENT_CAP["chronic"] = 0.85` in `demographics_params.py` and regenerate (`gen_demographics.py`).

Before deleting, re-read each line number against the file (`sed -n '<n>p'`): the numbers are main 85a23d47's.

- [ ] **Step 6: Run the carriers, medicine and fertility checks**

Run:
```bash
.venv/bin/python -m unittest test_demographics_modifiers test_demographics_model test_gen_demographics test_demographics_registry
.venv/bin/python scripts/analysis/demographics_harness.py medicine
.venv/bin/python scripts/analysis/demographics_harness.py fertility
.venv/bin/python -m unittest test_apply_ideologies
```
Expected:
- the tests pass;
- `medicine` and `fertility` exit 0: every scenario in band. The cap change touches only era-8+ scenarios, which must stay in band.
- If a scenario leaves its band, report the figures and stop for the owner; don't retune here.

- [ ] **Step 7: Commit**

```bash
git add common/laws/modified_health_system.txt common/laws/te_demog_law_injections.txt common/laws/extra_laws.txt common/technology/technologies/era_6.txt common/technology/technologies/era_7.txt common/technology/technologies/era_8.txt common/institutions/extra_institutions.txt common/script_values/te_demog_generated_values.txt scripts/analysis/demographics_params.py scripts/analysis/demographics_modifiers.py test_demographics_modifiers.py
git commit -m "Demographics phase 2 step 4: the lines the census replaces come off (spec 8.4, vanilla's health, child-labour and women's-rights lines)"
```

---

### Task 7: The census line and the observer report's phase-2 check

**Files:**
- Modify: `common/scripted_effects/te_debug_demog_effects.txt` (`te_debug_demog_census_line`: the new fields)
- Modify: `scripts/analysis/demographics_observer_report.py` (`OPTIONAL`, `phase2_check`, `--phase2`)
- Test: `test_demographics_observer_report.py`, `test_demographics_registry.py` (`TestConsole`)

**Interfaces:**
- Produces:
  - **The census line's new fields:** `m_b`, `m_d`, `bz`, `dz` (people-weighted means over the country's census states), `clamped` (the share of its people in clamped states) and `war` (1 at war).
  - **The checker:** `phase2_check(records, to_year=1900, big=20e6, run=10) -> dict`.

- [ ] **Step 1: Write the failing tests** (`test_demographics_observer_report.py`)

```python
class TestPhase2(unittest.TestCase):
    def rec(self, tag, year, people, war=0.0, clamped=0.0):
        return {"tag": tag, "year": year, "people": people, "war": war, "clamped": clamped}

    def test_world_multiple(self):
        recs = [self.rec("AAA", 1836, 100e6), self.rec("AAA", 1900, 150e6)]
        out = R.phase2_check(recs)
        self.assertAlmostEqual(out["world_multiple"], 1.5)
        self.assertTrue(out["world_in_band"])

    def test_ten_years_of_peacetime_loss_fails(self):
        recs = [self.rec("BIG", 1836 + i, 30e6 - i * 0.1e6) for i in range(12)]
        out = R.phase2_check(recs)
        # twelve censuses, eleven losses: the tenth loss in a row (1837-1846) is reported once
        self.assertEqual(out["shrinking"], [("BIG", 1837, 1846)])

    def test_a_war_year_breaks_the_run(self):
        recs = [self.rec("BIG", 1836 + i, 30e6 - i * 0.1e6, war=1.0 if i == 5 else 0.0) for i in range(12)]
        self.assertEqual(R.phase2_check(recs)["shrinking"], [])

    def test_small_countries_are_not_checked(self):
        recs = [self.rec("SML", 1836 + i, 10e6 - i * 0.1e6) for i in range(12)]
        self.assertEqual(R.phase2_check(recs)["shrinking"], [])

    def test_clamped_share_is_weighted_by_people(self):
        recs = [self.rec("AAA", 1850, 100e6, clamped=0.02), self.rec("BBB", 1850, 300e6, clamped=0.0)]
        self.assertAlmostEqual(R.phase2_check(recs)["clamped_share"], 0.005)

    def test_the_new_fields_parse_when_present(self):
        line = ("TE_DEMOG_CENSUS: tag=AAA; year=1850; people=1_0_0; median=20; tfr=5; e0=35; e65=10; imr=150; cbr=40; "
                "cdr=30; mig=0_0_0; young=0.35; working=0.6; old=0.05; sex_balance=100; gini=0.5; wc=50; primacy=0.2; "
                "crisis=0; devastation=0; turmoil=0; m_b=-0.120; m_d=-0.300; bz=0.020; dz=0.010; clamped=0; war=1")
        recs, bad = R.read_records([line])
        self.assertEqual(bad, [])
        self.assertEqual((recs[0]["m_b"], recs[0]["dz"], recs[0]["war"]), (-0.12, 0.01, 1.0))
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_observer_report.TestPhase2`
Expected: FAIL, `AttributeError: … has no attribute 'phase2_check'`.

- [ ] **Step 3: Implement the report**

```python
OPTIONAL = ("mig_raw", "lag", "m_b", "m_d", "bz", "dz", "clamped", "war")


def phase2_check(records, to_year=1900, big=20e6, run=10):
    """The calibration plan's in-game gate for phase 2 (plan 2026-10-10 engine rates, Task 10):
    the world's people from the first census year to `to_year` (within x1.3-x1.7), countries of `big`
    people or more that lost people `run` census years running with no war year among them, and the
    share of the world's people in clamped states (above 1% calls probe P5)."""
    tags = {}
    for r in records:
        tags.setdefault(r["tag"], {})[r["year"]] = r
    world = {}
    for series in tags.values():
        for y, r in series.items():
            world[y] = world.get(y, 0.0) + r["people"]
    years = sorted(world)
    first = years[0] if years else None
    multiple = world[to_year] / world[first] if first is not None and to_year in world and world[first] else None
    shrinking = []
    for tag, series in sorted(tags.items()):
        ys = sorted(series)
        streak = []
        for a, b in zip(ys, ys[1:]):
            r0, r1 = series[a], series[b]
            losing = (b == a + 1 and r1["people"] < r0["people"] and r0["people"] >= big
                      and not r1.get("war", 0) and not r0.get("war", 0))
            streak = streak + [b] if losing else []
            if len(streak) == run:
                shrinking.append((tag, streak[0], streak[-1]))
    people = sum(r["people"] for r in records) or 1.0
    clamped = sum(r["people"] * r.get("clamped", 0.0) for r in records) / people
    return {"world_multiple": multiple, "world_in_band": multiple is not None and 1.3 <= multiple <= 1.7,
            "shrinking": shrinking, "clamped_share": clamped}
```

Add `--phase2` to `main`. It prints the multiple and its verdict, each shrinking run, and the clamped share with "probe P5" above 1%, and exits 1 on a failed gate.

- [ ] **Step 4: The line's fields** (`te_debug_demog_census_line`, after its lag loop: a second walk over the country's states with a census, console-only)

```
		set_local_variable = { name = te_dg_dbg_w value = 0 }
		set_local_variable = { name = te_dg_dbg_mb value = 0 }
		set_local_variable = { name = te_dg_dbg_md value = 0 }
		set_local_variable = { name = te_dg_dbg_bz value = 0 }
		set_local_variable = { name = te_dg_dbg_dz value = 0 }
		set_local_variable = { name = te_dg_dbg_cl value = 0 }
		every_scope_state = {
			limit = { te_demog_has_census = yes }
			change_local_variable = { name = te_dg_dbg_w add = var:te_dg_people }
			change_local_variable = { name = te_dg_dbg_mb add = { value = te_demog_rate_births_applied multiply = var:te_dg_people } }
			change_local_variable = { name = te_dg_dbg_md add = { value = te_demog_rate_deaths_applied multiply = var:te_dg_people } }
			if = {
				limit = { has_variable = te_dg_bz }
				change_local_variable = { name = te_dg_dbg_bz add = { value = var:te_dg_bz multiply = var:te_dg_people } }
				change_local_variable = { name = te_dg_dbg_dz add = { value = var:te_dg_dz multiply = var:te_dg_people } }
			}
			if = {
				limit = {
					has_variable = te_dg_rate_clamped
					var:te_dg_rate_clamped > 0
				}
				change_local_variable = { name = te_dg_dbg_cl add = var:te_dg_people }
			}
		}
```

Divide each sum by `te_dg_dbg_w` (`min = 1`) into a `te_dg_dbg_*` variable. Add `te_dg_dbg_war` (1 if `is_at_war = yes`). Append `; m_b=[…|3]; m_d=[…|3]; bz=[…|3]; dz=[…|3]; clamped=[…|3]; war=[…|0]` to both variants of the line, and remove the six variables after it.

**People counts in the products:** a 50M state × M is fine in i64 × 1e-5, but the country's sum of `people × M` for China (500M × 0.5) is 2.5 × 10⁸, also fine.

Registry test `test_census_line_carries_the_phase2_fields`: both variants carry the six fields, and every `te_dg_dbg_*` the line sets is removed.

- [ ] **Step 5: Run the tests**

Run: `.venv/bin/python -m unittest test_demographics_observer_report test_demographics_registry.TestConsole`
Expected: OK.

- [ ] **Step 6: Commit**

```bash
git add common/scripted_effects/te_debug_demog_effects.txt scripts/analysis/demographics_observer_report.py test_demographics_observer_report.py test_demographics_registry.py
git commit -m "Demographics phase 2 step 4: the census line carries the census's terms and the report checks the gate"
```

---

### Task 8: The harness predicts the engine's growth from a save (`predict`)

Uses #857's `state_inputs`, `save_year` and timed-modifier reader.

**Files:**
- Modify: `scripts/analysis/demographics_save_inputs.py` (pops' `food_security` value; states' `devastation`)
- Modify: `scripts/analysis/demographics_harness.py` (`predict_state`, `predict_rows`, `predicted_multiple`, `cmd_predict`)
- Test: `test_demographics_save_inputs.py`, `test_demographics_harness.py`
- Docs: `docs/guides/python_tools.md` (the command)

**Interfaces:**
- Consumes: `M.rate_term`, `M.starvation_terms`, `M.model_crude_rates`, `P.LITERACY_BIRTH_PENALTY`, `P.KEEP_STARVING_SLOPE` (Task 2); `pop_growth.monthly_birthrate` / `monthly_mortality`, `read_defines`.
- Produces:
  - `predict_state(pops, cbr, cdr, devastation, d, keep_slope=False) -> dict` with `people`, `births`, `deaths`, `target_births`, `target_deaths`, `kept_deaths`, `m_b`, `m_d`, `clamped`, `slope_deaths`. `pops` is a list of `(size, sol, literacy, food_security)`; the rates are per 1,000.
  - `predicted_multiple(points, to_year) -> float`.
  - CLI: `demographics_harness.py predict SAVE... [--keep-slope] [--to-year 1900] [--check-modifiers] [--json]`.

- [ ] **Step 1: Write the failing tests**

`test_demographics_save_inputs.py`:

```python
    def test_food_security_and_devastation_are_read(self):
        text = (SAVE_HEAD + "pops={\n\tdatabase={\n1={\n\ttype=laborers\n\tworkforce=100\n\tdependents=300\n"
                "\tlocation=5\n\tprevious_quality_of_life=3\n\tacceptance_data={\n\t\tacceptance_value=40\n\t}\n"
                "\tfood_security={\n\t\tvalue=0.31\n\t\tstarvation=0\n\t\tstate=moderate\n\t}\n}\n\t}\n}\n"
                "states={\n\tdatabase={\n5={\n\tcountry=1\n\tdevastation=19.5\n}\n\t}\n}\n")
        sections = self.read(text)
        self.assertEqual(sections["pops"]["1"]["food_security"], "0.31")
        self.assertEqual(sections["states"]["5"]["devastation"], "19.5")
```

`SAVE_HEAD` and `read` follow the module's existing fixture helpers: the plain-text header and a temp-file read. Use whatever names it has.

`test_demographics_harness.py`:

```python
class TestPredict(unittest.TestCase):
    D = H.G.read_defines()

    def test_a_fed_state_runs_at_the_census_rates_plus_nothing(self):
        pops = [(1e6, 9.0, 0.0, 0.8)]
        out = H.predict_state(pops, cbr=40.0, cdr=30.0, devastation=0.0, d=self.D)
        self.assertAlmostEqual(out["births"] / 1e3, 40.0, places=6)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0, places=6)

    def test_literacy_is_netted(self):
        out = H.predict_state([(1e6, 9.0, 0.5, 0.8)], cbr=40.0, cdr=30.0, devastation=0.0, d=self.D)
        self.assertAlmostEqual(out["births"] / 1e3, 40.0, places=6)

    def test_starvation_and_devastation_stay_on_top(self):
        pops = [(1e6, 9.0, 0.0, 0.1)]   # severe: births -0.9, deaths +1.0 at the bare curve's weight
        out = H.predict_state(pops, cbr=40.0, cdr=30.0, devastation=0.2, d=self.D)
        bare_d = 1e6 * H.G.monthly_mortality(9.0, self.D) * 12
        self.assertAlmostEqual(out["deaths"], 30.0 * 1e3 + bare_d * (1.0 + 0.2), delta=1.0)
        self.assertLess(out["births"], 40.0 * 1e3)

    def test_the_slope_is_kept_only_when_asked(self):
        pops = [(1e6, 1.0, 0.0, 0.8)]
        plain = H.predict_state(pops, 40.0, 30.0, 0.0, self.D)
        kept = H.predict_state(pops, 40.0, 30.0, 0.0, self.D, keep_slope=True)
        slope = 1e6 * (H.G.monthly_mortality(1.0, self.D) - H.G.monthly_mortality(4.0, self.D)) * 12
        self.assertAlmostEqual(kept["deaths"] - plain["deaths"], slope, delta=1.0)

    def test_multiple_chains_the_saves_rates(self):
        # 1% a year from 1837 to 1887, then 0.5% to 1900
        self.assertAlmostEqual(H.predicted_multiple([(1837, 1.0), (1887, 0.5)], 1900),
                               math.exp(0.01 * 50 + 0.005 * 13), places=9)
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_save_inputs test_demographics_harness.TestPredict`
Expected: FAIL (no `food_security` key; no `predict_state`).

- [ ] **Step 3: The reader**

In `demographics_save_inputs.py`:
- Add `"devastation"` to `SECTIONS["states"]`.
- For pops, track the nested block: at depth 3, `line.startswith("\tfood_security={")` sets `in_food = True`.
- At depth 4 with `in_food`, `^\t\tvalue=([-0-9.]+)$` stores `record["food_security"]`.
- `in_food` clears when the depth returns to 3. Write it beside #857's `in_timed` tracking, which has the same shape.

- [ ] **Step 4: The prediction**

In `demographics_harness.py`:

```python
def predict_state(pops, cbr, cdr, devastation, d, keep_slope=False):
    """The engine's births and deaths a year in one state once the census sets them (phase 2 step 4, plan §2).

    pops: [(size, sol, literacy, food_security)]; cbr, cdr: the census's own rates per 1,000 a year;
    devastation: the state's 0-1 share. Each pop gets bare x max(0, 1 + M + its kept and replaced terms):
    literacy's -0.1 (replaced, netted in M), starvation (kept, from its food security), devastation
    (kept, as +1.0 x the share, pending probe P1). Kept terms a save doesn't hold are left out:
    pollution, turmoil, events, low_pop_state, unemployment, workplace mortality (about +2% of deaths
    in 1949, growth probe)."""
    people = sum(p[0] for p in pops)
    bare_b = sum(s * G.monthly_birthrate(sol, d) for s, sol, _l, _f in pops) * 12
    bare_d = sum(s * G.monthly_mortality(sol, d) for s, sol, _l, _f in pops) * 12
    lit_b = sum(s * G.monthly_birthrate(sol, d) * lit for s, sol, lit, _f in pops) * 12
    slope = sum(s * (G.monthly_mortality(sol, d) - G.monthly_mortality(max(sol, d.equilibrium_sol), d))
                for s, sol, _l, _f in pops) * 12
    target_b, target_d = cbr / 1000 * people, cdr / 1000 * people
    m_b, cb = M.rate_term(target_b, bare_b, replaced=P.LITERACY_BIRTH_PENALTY * lit_b)
    m_d, cd = M.rate_term(target_d + (slope if keep_slope else 0.0), bare_d, other=devastation)
    births = deaths = 0.0
    for s, sol, lit, fs in pops:
        sb, sd = M.starvation_terms(fs)
        births += s * G.monthly_birthrate(sol, d) * 12 * max(0.0, 1 + m_b + P.LITERACY_BIRTH_PENALTY * lit + sb)
        deaths += s * G.monthly_mortality(sol, d) * 12 * max(0.0, 1 + m_d + sd + devastation)
    return {"people": people, "births": births, "deaths": deaths, "target_births": target_b,
            "target_deaths": target_d, "kept_deaths": deaths - target_d, "m_b": m_b, "m_d": m_d,
            "clamped": cb or cd, "slope_deaths": slope}


def predicted_multiple(points, to_year):
    """[(year, growth % a year)] → the multiple from the first year to to_year, each save's rate held until
    the next save's year (the last one's after it)."""
    points = sorted(points)
    total = 0.0
    for (y0, g), nxt in zip(points, points[1:] + [(to_year, None)]):
        total += g / 100 * (min(nxt[0], to_year) - y0)
    return math.exp(total)
```

`cmd_predict`, for each save:
1. **Read** `S.read_sections(path)`, `S.read_variables(path, (), ("te_dg_cbr_model", "te_dg_cdr_model", "te_dg_cbr", "te_dg_cdr", "te_dg_mb", "te_dg_md"))` and `save_year`.
2. **Group the pops** by state, as `(size, SoL, num_literate / size, food_security or 1.0)`.
3. **Take each state's census rates:**
   - `te_dg_cbr_model`/`te_dg_cdr_model` where present (a phase-2 save);
   - else `te_dg_cbr`/`te_dg_cdr` (a phase-1 save: the census's figures are the model's);
   - else `M.model_crude_rates(inputs_for(st, carriers, incorporated=inc))` (#857's `state_inputs`).
4. **Sum by owner tag;** print the world line.
5. **Print each country of 20M or more:** people, census growth, predicted growth, kept deaths per 1,000, clamped. Flag those whose predicted growth is below 0.
6. **`--keep-slope`:** also prints the slope's cost. This is the reproducible version of §1's table.

After the loop, print `predicted_multiple` from the saves' world growth to `--to-year`, with a ×1.3–×1.7 verdict. Exit 1 if it is outside, or if any 20M+ country is predicted to shrink.

`--check-modifiers` (probe P4) lists states whose `te_dg_mb` or `te_dg_md` is not 0 but whose `timed_modifiers` hold no `te_demog_census_*` of the matching sign.

Register the subcommand beside `history`.

- [ ] **Step 5: Run the tests and the command on the gate saves**

Run:
```bash
.venv/bin/python -m unittest test_demographics_save_inputs test_demographics_harness
D=/mnt/d/vic3te-data/vic3te-demog-gate-data/saves
.venv/bin/python scripts/analysis/demographics_harness.py predict $D/autosave.1791572508.v3 $D/autosave.1791583167.v3 --keep-slope
```
Expected: the tests pass. The command prints the slope's cost as §1's table has it: world 0.036 and 0.174 points, China 0.023 and 0.244, give or take rounding. Record the prediction's world multiple in the results doc (Task 10).

- [ ] **Step 6: Document and commit**

Add a `predict` paragraph to `docs/guides/python_tools.md` beside `history`: what it reads, what it leaves out (the kept terms a save doesn't hold), and that it exits 1 on the gate.

```bash
git add scripts/analysis/demographics_save_inputs.py scripts/analysis/demographics_harness.py test_demographics_save_inputs.py test_demographics_harness.py docs/guides/python_tools.md
git commit -m "Demographics harness: predict, the engine's growth once the census sets it, from a save"
```

---

### Task 9: Docs and the player guide

**Files:**
- Modify: `docs/systems/mod_systems.md` § Demographics: "Phase 1 applies nothing" becomes the phase-2 step 4 paragraph. Add a "The census's births and deaths" subsection with the formula, the clamp, the refresh sites, fast mode, the kept list, the rule and old saves, and update the file index.
- Modify: `docs/superpowers/specs/2026-10-08-demographics-design.md`:
  - §2.3's and §2.4's "Applied as": replace "the model's births ÷ the engine's births before the modifier − 1" with this plan's additive form, citing the growth probe;
  - §2.4's "multiply on top" becomes "add on top, at the bare curve's weight";
  - §13: the shown TFR is the realized one;
  - §12's phase-2 row: step 4 built.
- Modify: `docs/superpowers/plans/2026-10-10-demographics-phase2-calibration.md` (#857's file, once merged): step 4 points to this plan.
- Modify: `docs/guides/vanilla_patch_runbook.md` § the values the mod copies or cancels: new rows for the health laws, child labour and women's rights, each with its vanilla `file:line`, the cancel's file and the failure if vanilla changes.
- Modify: `docs/player_guide/08-states.md` § Demographics:
  - "The census changes nothing about your population yet" becomes what it does: births and deaths follow the census; the "Demographic Profile" line in a state's birth and death rates; what Display only and Disabled do now;
  - children per woman is the realized figure.
- Modify: `docs/player_guide/06-politics.md`, only if it states the health laws' or child-labour laws' mortality figures (`grep -n -i "mortality" docs/player_guide/06-politics.md`).
- Rebuild: `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`.

- [ ] **Step 1: Write the docs above.** House style per `docs/player_guide/STYLE.md`; match the depth of the section's neighbours.
- [ ] **Step 2: Run the docs checks**

Run:
```bash
.venv/bin/python scripts/analysis/check_player_guide_style.py --strict
.venv/bin/python scripts/build_player_guide.py
.venv/bin/python scripts/build_player_guide.py --check
.venv/bin/python scripts/analysis/check_post_load_rosters.py
grep -c $'\r$' docs/systems/journal_entry_systems.md docs/guides/gui_modding_guide.md docs/vanilla/treaty_articles_reference.md
```
Expected: the lint is clean and `--check` exits 0. The three CRLF docs are untouched (their CR counts unchanged).

- [ ] **Step 3: Commit**

```bash
git add docs/systems/mod_systems.md docs/superpowers/specs/2026-10-08-demographics-design.md docs/guides/vanilla_patch_runbook.md docs/player_guide/08-states.md docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf
git commit -m "Demographics phase 2 step 4: docs and the player guide"
```

Add `docs/player_guide/06-politics.md` and the calibration plan to the `git add` if Step 1 changed them.

---

### Task 10: The gate

**Files:**
- Create: `docs/testing/demographics-phase2-engine-rates-<date>.md` (the results)

- [ ] **Step 1: The offline checks**

Run:
```bash
.venv/bin/python -m unittest discover -s . -p 'test_*.py' > /tmp/claude-1000/suite.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/suite.txt
.venv/bin/ruff check .
python3 scripts/format_paradox_tabs.py --check $(git diff --name-only origin/main -- '*.txt')
.venv/bin/python organize_loc.py --check
.venv/bin/python scripts/generators/gen_demographics.py --check
for a in script_argument_audit loc_coverage_audit empty_effect_audit modifier_multiplier_var_audit duplicate_key_audit silent_variable_audit; do .venv/bin/python $a.py --strict || echo "FAIL $a"; done
D=/mnt/d/vic3te-data/vic3te-demog-gate-data/saves
.venv/bin/python scripts/analysis/demographics_harness.py predict $D/*.v3
.venv/bin/python scripts/analysis/demographics_harness.py medicine
.venv/bin/python scripts/analysis/demographics_harness.py fertility
```
Expected: `OK`, no ruff findings, no audit failures. `predict` on the six gate saves gives a world multiple 1837–1900 inside ×1.3–×1.7, with no 20M+ country predicted to shrink.

**If `predict` fails the gate,** stop and report. The fix is calibration (steps 1–3, 5–6), not this step's arithmetic.

- [ ] **Step 2: The in-game probes** (owner, a throwaway save; deploy per CLAUDE.md "Play-testing unmerged work")
  - **P1:** the 1887 gate save. Fire `event te_debug_demog.1`, option m, then hover each logged state's mortality and compare the totals.
  - **P2:** in a new 1836 game, read the four laws' tooltips and option l's line.
  - **P3:** option n on the capital after its second yearly pulse. M is set, the read less the applied terms is the kept terms, and `bz`/`dz` are small.

- [ ] **Step 3: The fast-mode gate run** (owner)
  - **Start:** a new 1836 game, observed. Census log on (option b), fast mode at 4× (option h) on day 1.
  - **Run** to census year 1950 or later. Archive every `debug.log` generation (`scripts/analysis/archive_probe_logs.sh` on the probe branch). Keep yearly autosaves on D:, not C: (memory: WSL's disk lives on C:).
  - **Then:**

```bash
.venv/bin/python scripts/analysis/demographics_observer_report.py LOGS... --phase2
.venv/bin/python scripts/analysis/demographics_observer_report.py LOGS... --closed-borders SAVES...
.venv/bin/python scripts/analysis/demographics_harness.py replay LOG_WITH_OPTION_A_BLOCKS
.venv/bin/python scripts/analysis/demographics_harness.py predict SAVE_AFTER_A_WAR --check-modifiers
```

**The gate:**
- world population from census year 1836 to 1900 within ×1.3–×1.7;
- no country of 20M or more losing people for ten census years running outside wars;
- the replay exact on option a's blocks, taken in three states at different SoL;
- Closed Borders `mig_raw` median within ±1 per 1,000. A miss means the walk's expected events don't hold the census's term;
- the clamped share under 1% of the world's people (else P5);
- regional shares moving the right way: Europe up to 1900, Asia's share falling.

- [ ] **Step 4: Write the results doc** (`docs/testing/demographics-phase2-engine-rates-<date>.md`)
  - the build, the saves' and logs' location;
  - P1–P4's answers. Write each into §1's table in this plan, turning the "needs" rows to verified or refuted;
  - the gate's figures against each threshold;
  - what the census line's `dz` says about the kept deaths' size by country and decade.

  Record any engine fact learned in `docs/guides/scripting_best_practices.md` the same session.

- [ ] **Step 5: Commit**

```bash
git add docs/testing/demographics-phase2-engine-rates-<date>.md docs/superpowers/plans/2026-10-10-demographics-phase2-engine-rates.md
git commit -m "Demographics phase 2 step 4: probes and gate results"
```

## Risks

- **Performance.** The census runs per state per step: yearly, or for every state each clock step under fast mode.
  - Step 4 adds one `change_local_variable` per pop in the walk, one per occupied slot in the sweep (the maternal sum), about thirty operations per state in the refresh, and ten in the kept scales.
  - The sweep already costs 0.75–1.0 s per world-year at about 40 operations a slot (§11.3, Q9), so the additions are a few per cent.
  - No new walk or iterator.
  - **Check:** option d's benchmark before and after, on the 1887 gate save.
- **Old saves.**
  - **What loads at once:** the inverse INJECTs and §8.4's removals, with the next pulse's figures.
  - **What waits:** M arrives at each state's next step. The kept scales start a step later, once `te_dg_cbr_model` exists.
  - **So:** for up to a year a state runs on the curves without the replaced lines, much as a fresh 1836 state does.
  - No migration code. A save from before the census itself seeds as today.
- **The game rule.**
  - Under Full only. Display only and Disabled clear the terms at each state's next step.
  - The static removals change those two settings until step 5 gives them the equilibrium rates. Ship steps 4 and 5 together (§2, "The game rule").
  - Every check is written negatively, so a save from before the rule keeps Full.
- **Migration.**
  - **The residual stays right:** the walk's expected events read the state read with M in it (E6, verified by fast mode's Closed Borders result), so the residual is still the population change less the engine's natural change.
  - **Indirect effects:** M changes how many people the engine adds, and so crowding, unemployment and migration pull, but only by way of the population.
  - **The check:** the gate's Closed Borders median is the consistency check.
  - **One change:** the Resettlement transit deaths and space-race kills still read as emigrants (growth probe "Open"); unchanged.
- **Civil-war new countries and changes of owner.**
  - **Variables:** the census's variables sit on the state and follow it (spec §2.6).
  - **Modifiers:** whether its modifiers follow is unread (E22, probe P4). The `has_modifier` guard keeps a lost modifier from being subtracted as if it were on, and the next step re-applies it.
  - **The laws:** the new owner's laws change the walk's literacy term and the inverse INJECTs automatically.
  - **The revolution rule:** "the winner continues the nation" concerns country state, and the census keeps none in modifiers.
- **Fast mode.**
  - **The formula:** F now scales the average with the census's new term in it (Task 5), and the joint fixed point is tested.
  - **What fast mode doesn't speed:** literacy, SoL and laws keep the calendar, so a fast run's census sets 20th-century medicine on a 19th-century society (fast run 2026-10-09). The gate's 1836–1900 window is fast mode's census years, as the calibration plan's gate reads it.
  - **Switching back to normal speed** takes F off at once, as today. The census's term stays.
- **The 1836 start.** Every state runs on the curves until its first step, its second yearly pulse. The first year's growth is the engine's, about 1% a year (spec §2.3's probe), until step 5 retunes the curves.
- **A modifier tooltip line per state.** "Demographic Profile" shows in every state's birth and death rates. The size of the number (often −20% to −50% against the curves) may alarm a player until step 5 brings the curves to the census's medians. The loc says what sets it.
