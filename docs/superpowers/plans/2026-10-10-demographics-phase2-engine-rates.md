# Demographics Phase 2, Step 4: The Census Sets the Engine's Births and Deaths — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each state's census sets the engine's births and deaths through one births modifier and one deaths modifier. The engine's events become the model's, plus the terms added on top of the census, and the census's ring follows what the engine did.

**Architecture:**
- **The engine's arithmetic.** It gives every pop `bare × max(0, 1 + total)` births and deaths, where `bare` is the SoL curve and `total` adds every term (the growth probe).
- **The census's term M** is set so the engine's events become the model's events plus the terms added on top, at the bare curve's weight.
- **What M nets out.** The lines the census absorbs come off their carriers (§8.4's removals, inverse INJECTs on vanilla laws), so M has only the bare curve and one absorbed per-pop term (literacy) to net out.
- **How M is applied:** a fixed-sign pair of static modifiers refreshed at each census step. Fast mode's ×K composes with it.
- **The census's own accounting.** Its next step scales its own births and deaths to the engine's, so the pyramid places by age the events added on top.

**Tech Stack:** Victoria 3 1.14.5 Paradox script; Python 3.11/3.12 (`unittest`); the `_Engine` script interpreter in `test_demographics_registry.py`; `demographics_model.py` as the script's twin; `demographics_harness.py` for offline checks.

**Spec:** `docs/superpowers/specs/2026-10-08-demographics-design.md` (§2.3–§2.5, §8.4, §11.3–§11.4, §12, §13–§14) and the calibration plan's step 4 (`docs/superpowers/plans/2026-10-10-demographics-phase2-calibration.md`). Evidence:
- `docs/testing/demographics-probe-results-2026-10-08.md` (Q5, Q7);
- `docs/testing/demographics-growth-probe-results-2026-10-09.md`;
- `docs/testing/demographics-fast-run-2026-10-09.md`;
- `docs/testing/demographics-history-check-2026-10-10.md`.

**Base:** `main` after #855–#860 (merged into this branch, ee3e29d6).
- Tasks 10 and 12 call #857's `state_inputs`, `history`, `save_year` and timed-modifier reader.
- #855 and #857 edited `te_demog_state_yearly` (the walk-pop guard) next to Task 4's edit: re-read that block before editing it.
- `te_demog_generated_values.txt` is regenerated, never merged by hand.

**Words.** A term is either:
- **absorbed (by the census):** its line comes off its carrier or is netted out of M, and the census's own term carries the effect; or
- **added on top (of the census):** the engine still applies it, on top of the census's rates.

## Global Constraints

- **Game version:** Victoria 3 1.14.5. Vanilla facts are from `vanilla_parsed/` and the 1.14.5 install at `/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game`.
- **Paradox files:** tab indentation, exactly one UTF-8 BOM on every `.txt` and `.yml` (`bom_normalizer`). Run `python3 scripts/format_paradox_tabs.py <files>` after edits.
- **Script literals:** at most five decimal places; a sixth reads as 0 with `Badly read script value` (probe 2026-10-08, Finding 1).
- **No negative `add_modifier` multiplier.** Its behaviour is unread in this repo: monetary design §17 check 8 is still open, and `te_fx_weak`/`te_fx_strong` use fixed-sign pairs. M is applied as a +1 modifier and a −1 modifier, each with a multiplier of 0 or more.
- **A modifier's `multiplier` script value resolves against ROOT** (CLAUDE.md, #500). The census's modifiers are refreshed only where ROOT is the state: the yearly state pulse and fast mode's `te_demog_events.2`. Never from the console, the benchmark or game start.
- **One refresh site per modifier:** `te_demog_rates_apply` is the only effect that adds or removes `te_demog_census_*`.
- **`add_modifier`/`remove_modifier` are invisible inside the same effect** (`scripting_best_practices.md`; CLAUDE.md "Top gotchas"). A read in the same effect as the refresh decides from locals the refresh wrote, never from `has_modifier`.
- **The rule's checks are written negatively:** `te_demog_effects_run` (Full only), `te_demog_cohorts_run`.
- **Generated files:** `te_demog_generated_values.txt` and `te_demog_generated_effects.txt` come from `scripts/generators/gen_demographics.py`. Run it; never edit them.
- **Localization:** add keys to an existing `*_l_english.yml`, run `python3 organize_loc.py`, and commit everything it rewrites. Player-facing text follows `docs/player_guide/STYLE.md`; loc uses `#b X#!`, never `[b]`.
- **Python:** 3.11-compatible, so no PEP 701 f-strings. Check with `grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" <files>` before pushing.
- **Running Python in a worktree:** use `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python` with `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent`.
- **Commits:** by path, never `git commit -a`. End each message with the session's `Co-Authored-By` and `Claude-Session` lines.
- **The gate's figures, verbatim from the calibration plan:**
  - world population 1836–1900 within ×1.3–×1.7;
  - no country of 20M or more losing people for ten years running outside wars;
  - the census's replay (`demographics_harness.py replay`) exact.
- **Release precondition (owner, 2026-10-10): steps 4 and 5 ship together.**
  - **Why:** Task 6's and Task 8's removals and INJECTs apply under every setting of the Demographics rule. Display only and Disabled get their equilibrium rates only in step 5 (spec §11.4).
  - **The rule:** no public release may contain step 4 without step 5.
  - **The fallback if step 5 slips:** §2's rule-gated restore.

## Review Focus

1. **A freshly seeded state** (game start, a re-seed after a merge). Its census writes 0 births, so a refresh from it would set M = −1 and stop births at the clamp.
   - Expect: M left as it was, which is none on a new 1836 state.
   - Pinned by Task 4's `test_a_seed_leaves_the_rates_alone`.
2. **A state that lost its modifier but still has `te_dg_mb`** (a change of owner, secession, a save another mod edited). The prior term is read only while the modifier is on, so nothing phantom comes off the walk's average.
   - Pinned by Task 4's `test_the_prior_term_needs_the_modifier`.
3. **Fast mode reading the census's new term in the same effect that set it.** It must take the term from the refresh's locals, not from `has_modifier`, which can't see this effect's add or remove.
   - Pinned by Task 5's `test_fast_mode_reads_the_new_term_from_the_refresh`.
   - Task 5's `test_fast_and_census_terms_reach_a_joint_fixed_point` pins the fixed point.
4. **The rule switched from Full to Display only mid-game.** The modifiers and terms come off at the state's next step, and that step takes no on-top scales.
   - Pinned by Task 4's `test_display_only_clears_the_rates` and Task 3's `test_no_on_top_scales_outside_full`.
5. **Terms added on top that already push a state's read past −0.8** (a plague event, a decree or another state modifier; starvation is per pop and never enters the state read): M never pushes further down, and never above `RATE_TERM_MAX`.
   - Pinned by Task 2's `test_the_clamp_never_pushes_past_the_terms_on_top` and Task 4's `test_script_clamps_like_the_model`.

## 1. The engine's arithmetic, from evidence

Each claim is **verified**, with its source, or **needs an in-game probe** (§4 designs the probe).

| # | Claim | Status | Evidence |
|---|---|---|---|
| E1 | A pop's births are `curve_b(SoL) × size × max(0, 1 + total_b)` and its deaths `curve_d(SoL) × size × max(0, 1 + total_d)`. One total per pop, with every term **added** inside it | verified | growth probe 2026-10-09: 945 death windows, steps −0.9 to +1.0, deaths at 1.00–1.04 of the additive candidate. The multiplicative census formula drifted to 1.31 at −0.9 |
| E2 | Growth lands 12 times a year, a month's curve each | verified | growth probe: each 28-day window ran at 0.98–1.03 of the curve's month |
| E3 | The curves. Births: 475 per 100,000 a month to SoL 11, falling to 80 at SoL 35. Deaths: 600 at SoL 0, 475 at SoL 4, 143.9 at 18, 100 at 35 | verified | `common/defines/extra_defines.txt:79-88` and `:101-147`; `te_demog_pop_engine_births`/`_deaths` (generated, `te_demog_generated_values.txt:5-47`); `test_gen_demographics.test_engine_curves_match_the_defines` |
| E4 | The starving slope: deaths climb from 475 to 600 per 100,000 a month as SoL falls from 4 to 0 (`POP_GROWTH_MORTALITY_STARVING_SLOPE`). Births are flat there | verified | `extra_defines.txt:85,104-105,131` |
| E5 | A state's `modifier:state_birth_rate_mult` / `state_mortality_mult` holds the country's and the state's modifiers, including a state `add_modifier` | verified | Q5: a modifier on the country, and one added to the capital, each raised the read. Q7: a state −1 birth modifier with a positive multiplier (the "down" shape, `te_dp_q7_phase_a` on branch `probe/demographics`) cut Qing's births as the read said |
| E6 | The same holds for fast mode's own +1 modifiers at 4× and 12× | verified | fast run 2026-10-09: Closed Borders `mig_raw` median −0.41 per 1,000. Were the read blind to them, every country would show about +7 per 1,000 of phantom immigration |
| E7 | Per-pop terms the read leaves out. **Births:** `literacy_penalty` −0.1 × literacy (fitted −0.101); starvation −0.7 × scale (mild) or −0.9 (severe). **Deaths:** the class's `state_<type>_mortality_mult`; the workplace's `building_<type>_` and `building_group_<group>[_<type>]_mortality_mult`; `working_conditions` by workplace group; starvation +0.6 × scale or +1.0; `state_non_homeland_mortality_mult` | verified | growth probe ("Births = …", "Deaths = …"); vanilla `common/static_modifiers/00_code_static_modifiers.txt:119-182`; generated `te_demog_pop_birth_mult`/`_death_mult` |
| E8 | Their sizes in 1949: class +4.1% of curve deaths (the child-labour laws), working conditions +1.0%, building-group reads +0.7%, production methods +0.5%, starvation +0.1–0.3% | verified (one save) | growth probe's table |
| E9 | The floor: births at −0.9 run at a tenth, and stop at −3; never negative. Per pop the floor is 0 at a total of −1 | verified at state level; the per-pop floor inferred | Q7 (Qing, −0.9 then −3); growth probe ("bends at the floor in 1836, where literate and starving pops reach 0"); deaths at −5 stopped (the probe's control) |
| E10 | Totals stay linear from −0.9 to well above +1.0 | verified | growth probe's steps: +0.5, +1.0, −0.5, −0.9. The fast run's 12× put per-pop totals near +11, with the walk's linear prediction still matching (E6) |
| E11 | A change of rate shows within a month, not at once | verified | Q7: phase A showed in full in its first month; phase B and the removal showed only partly in theirs |
| E12 | Vanilla's laws: | verified | `game/common/laws/01_health_system.txt:41,90,117`, `02_childrens_rights.txt:13-16,50-52`, `02_rights_of_women.txt:22,62,143,194`; `vanilla_parsed/common/laws.json` |
|  | · Charitable Health System −0.03 mortality a level of its institution, Public Health Insurance −0.05 a level (`institution_modifier`); Private Health Insurance −0.002 `state_mortality_wealth_mult` a level | | |
|  | · Child Labor Allowed +0.05 for laborers, machinists, farmers and peasants; Restricted Child Labor +0.02 for laborers, farmers and peasants (`modifier`) | | |
|  | · women's rights' births: No Women's Rights +0.05, Women in the Fields −0.10 (a variant of No Women's Rights with its own block), Women Own Property none, Women in the Workplace −0.05, Women's Suffrage −0.05 | | |
| E13 | An `INJECT` into a vanilla law's `modifier` or `institution_modifier` **sums** with vanilla's lines, an institution line applying per level. Several INJECT blocks on one law in different files all apply | verified | `docs/guides/scripting_best_practices.md` § "CONFIRMED: an `INJECT:` block sums" (2026-09-20 laws; 2026-10-10 `institution_modifier`, Public Health Insurance read in game). Several blocks: `law_women_in_the_fields` is INJECTed in `extra_laws.txt:89` and in `sol_expectations_vanilla_injections.txt:17` (an inverse INJECT already); `law_no_womens_rights` in `extra_laws.txt:94` and `common/ideologies/modified.txt`. On the health laws, `modified_health_system.txt` already cancels vanilla's `state_pollution_reduction_health_mult` (drugs phase 2) |
| E14 | Devastation: `state_region_devastation` carries `state_mortality_mult = 1.0`, scaled by the devastation level (vanilla's comment). Script reads `devastation` as a 0–1 share | the line and the read: verified (`00_code_static_modifiers.txt:731-740`; `te_debug_demog_census_line` prints it). **Whether it is in `modifier:state_mortality_mult`, and how it scales: needs P1** | |
| E15 | Pollution: `state_region_pollution_health` carries `state_mortality_mult = 0.5` × the pollution impact, less `state_pollution_reduction_health_mult`. The mod INJECTs another +0.05 | the lines: verified (`00_code_static_modifiers.txt:742-748`; `extra_modifiers.txt:341-347`). The INJECTed +0.05 **sums** with vanilla's line inside the code-scaled modifier: verified (owner, 2026-10-10). **Whether it is in the read: needs P1** | |
| E16 | Turmoil: the `state_turmoil*` modifiers carry no mortality. Turmoil's deaths come from `state_mortality_turmoil_mult` "per Turmoil" (Militarized Police +0.004 a level, events) | the lines: verified (`00_code_static_modifiers.txt:776-798`; `docs/engine/modifiers_summary.txt:7411`). Its scaling is **unknown**, measured at about 0 (growth probe "Open"). It is added on top by construction; a probe only if the gate run shows an unexplained residual in turmoil states (P5) | |
| E17 | `low_pop_state` (+0.5 births, scaled by how far the state is under `LOW_POP_THRESHOLD`, 5,000 per arable land) and `unemployment_birth_penalty_state` (mod −0.1 × unemployment, vanilla −0.4) are state modifiers | the lines: verified (`00_code_static_modifiers.txt:695-705`, `00_defines.txt:1549`; the mod's `REPLACE`s in `extra_modifiers.txt:291,323`). In the read: assumed as for every state modifier (E5); P1 logs the birth read beside them | |
| E18 | `working_conditions` is scaled by `building_working_conditions_mult` (Workplace Safety −0.2 a level) | the line: verified (`vanilla_parsed` institutions). The census adds the table's value unscaled (`gen_demographics.engine_rate_terms`): a known gap in the residual, not in M | |
| E19 | About 2% of deaths stay unexplained by every read | verified (open) | growth probe "What is left" |
| E20 | A permanent `add_modifier` is saved in the state's `timed_modifiers` block with its multiplier | verified | `demographics_save_inputs` reads `migration_crowding` there |
| E21 | Whether a state's modifiers survive a change of owner (conquest, secession, a civil war's transfer) | **needs a check** (P4, offline from a save, no console probe) | state variables stay with the state (spec §2.6); modifiers unread |
| E22 | Whether `has_modifier` sees an `add_modifier` or `remove_modifier` made earlier in the same effect | **unverified, and treated as no** | `scripting_best_practices.md` ("results are invisible inside the same effect block"; line 608 "unverified"). The plan never relies on it (Task 5) |

**Measured from the gate run's saves for this plan.** The saves are a normal-speed observer game in `/mnt/d/vic3te-data/vic3te-demog-gate-data/saves/`. They were read with `demographics_save_inputs.read_sections` and `pop_growth`'s curves, and Task 10's `predict --slope` reproduces the figures. An independent review re-ran them on 2026-10-10 and got the same figures.

| Save | People below SoL 4 (below SoL 2) | The slope's extra deaths | Their cost to growth | No Women's Rights | Child Labor Allowed | A health law |
|---|---|---|---|---|---|---|
| 1837.1.1 | 4.2% (2.3%: laborers 1.5%, slaves 0.7%) | 0.76% of bare deaths | 0.04 points a year (China 0.02, India 0.06, Britain 0.05) | 83% of people | 100% | 5% |
| 1887.1.1 | 16.2% (14.7%: laborers 12.0%, slaves 2.1%) | 3.7% | 0.17 points (China 0.24, India 0.21, Russia 0.20, Japan 0.19) | 82% | 97% | 15% |

- **Bare births and deaths:** 5.6% and 4.7% a year, world-wide, in both saves.
- **Child labour's classes:** laborers, machinists, farmers and peasants hold 90.9% of people and 92.4% of bare deaths in 1837. So vanilla's +0.05 is worth about 0.22 points of world growth a year, in 1837 and in 1887 alike (the review's `classes.py`).

## 2. M per state

### The formula

Write a pop's total as the census's own terms plus everything else:

```
total_p = M + F + O_s + O_p + A_s + A_p
```

- M is the census's term (this plan); F is fast mode's term.
- O are the terms **added on top**: `_s` in the state read, `_p` per pop.
- A are the terms **absorbed**.
- After Tasks 6 and 8, A_s = 0: every absorbed state-level line is off its carrier. A_p is literacy only (births).

With no pop at the floor, a state's events a month are `Σ bare_p × (1 + M + F + O_s + O_p + A_p)`. The census wants, at K = 1 (no fast mode), `T + Σ bare_p × (O_s + O_p)`, where T is the model's events. So

```
M = T / B − 1 − Σ bare_p × A_p / B,        B = Σ bare_p
```

- **Births:** `M_b = T_b / B_b − 1 − literacy_penalty × Σ(bare_b × literacy) / B_b`. The generator reads literacy_penalty (−0.1) from the static modifier.
- **Deaths:** `M_d = T_d / B_d − 1`.
- **Units:** the walk's.
  - B is `te_dg_w_eb0` / `te_dg_w_ed0`: events a month × 100,000.
  - `T = te_dg_cbr_model × state_population × 100 / 12`: the model's rate per 1,000 a year, at today's population.
  - `Σ(bare_b × literacy)` is a new walk local, `te_dg_w_ebl`.
- **Why not the spec's ratio, or a plain netting:**
  - The spec's `M = model ÷ E_T − 1` (E_T being the engine's events before M) gives `E_T + (model/E_T − 1) × B`. That equals the model only when no other term applies.
  - Netting everything, `M = (model − E_T) / B`, gives exactly the model and cancels the terms added on top.
  - This formula keeps them, at the weight the engine itself gives them: a famine adds the deaths vanilla's famine adds.
  - It is the calibration plan's `M = (model − Σ bare × (1 + T − K)) / B` once A_s = 0.
- **Terms on top add at the bare curve's weight, not the model's.** The alternative, `T × (1 + Ō)`, scales them by the model's rate. The two differ by the ratio B/T, and agree once step 5 retunes the curves to the census's medians. Additive is what the engine does natively, and needs no reading of O.
- **Until step 5, that weight changes their size against realized events.**
  - **1836:** bare births are 57 per 1,000 against the model's 38–44, so a term on top is about 1.5 times as strong against realized births as in vanilla.
    - The Natalism decree's +0.5 is about +75% of births.
    - A famine's +1.0 is about +157% of deaths.
    - Pro-Natalist Subsidies' +0.10 is about +15%.
  - **Late game it reverses:** at SoL 35 bare births are 9.6 per 1,000.
  - Step 5's retune removes the distortion.

### One births term and one deaths term per state

- **No per-age-band M.** The engine's pops carry no age, so a modifier can only scale a pop's whole births or deaths. The census places the year's events by age itself.
- **No per-pop-type M.** Births have no type to carry it (`state_birth_rate_mult` is the only registered birth type), and for deaths it buys nothing, since the census has no strata dimension.

### How the terms on top are read: they aren't, for M

M never reads a term added on top. The engine applies O whatever its scaling, devastation, pollution and turmoil included, so E14–E16's unknowns don't block M. O is read only in two places:
- **The clamp's "other":** the state read less the census's and fast mode's prior terms.
- **The residual and the on-top scales,** through `te_dg_eb`/`te_dg_ed`, the walk's expected events.
  - These already read the state read and the per-pop starvation, class, workplace and non-homeland terms (E7; 1.024 of deaths explained).
  - Unreadable terms on top still reach the engine: turmoil's scaling, wealth mortality, the 2% of E19. They show up only in the migration residual, as in phase 1.

### The clamp

- **The floor:** `other + M ≥ RATE_TOTAL_MIN = −0.8`, where other = the state read − M_prev − F_prev. Q7 and the growth probe measured linearity down to −0.9; less literacy's −0.1 at full literacy, that keeps a literate, fed pop inside the measured range (E9–E10).
- **When the terms on top alone are past −0.8** (a plague event, a decree or another state modifier), the floor is 0: M never pushes a state further down than they do. Starvation is per pop (E7), so it never enters the state read: a starving pop under a negative M floors at 0, the per-pop floor below.
- **The ceiling:** `M ≤ RATE_TERM_MAX = +3.0`.
  - Linearity holds far above +1.0 (E10), so this only guards a nonsense target.
  - A state whose model deaths are four times its bare curve's is past anything the census produces in normal play.
- **The per-pop floor.** A starving pop still floors at 0, as intended. The formula assumes no pop at the floor; a floored pop's events are 0, not the negative figure the sum gives, so the state's events run above M's aim by the floored pops' share.
  - The walk floors each pop as the engine does, so `te_dg_eb`/`te_dg_ed`, the residual and the on-top scales all see it. Only M's aim is off.
  - Documented, not corrected: solving for M exactly would need a second walk.
- **The flag:** a clamped state sets `te_dg_rate_clamped = 1`, and the census line counts the clamped share of people.

### Applied as

- **Four static modifiers** in `common/static_modifiers/te_demog_modifiers.txt`:
  - `te_demog_census_births_up` (`state_birth_rate_mult = 1`) and `te_demog_census_births_down` (`= -1`);
  - `te_demog_census_deaths_up` (`state_mortality_mult = 1`) and `te_demog_census_deaths_down` (`= -1`).
- **Multipliers:** `max(M, 0)` for the up modifier and `max(−M, 0)` for the down one, read from `var:te_dg_mb` / `var:te_dg_md`. At most one of each pair is on.
- **One refresh site:** `te_demog_rates_apply` removes and re-adds them (the dynamic-modifier scaling pattern in CLAUDE.md).
- **Cadence:** each census step, from the yearly state pulse or, under fast mode's clock, from `te_demog_events.2`. Both have ROOT = the state.
- **A year's lag is fine:** rates follow a change within a month (E11).
- **The refresh leaves the terms it set in locals** (`te_dg_rate_new_b`/`_d`) for any later read in the same effect (E22). `has_modifier`-based values (`te_demog_rate_*_applied`) are only for reads a tick later: the clamp's prior term, and the census line.
- **Seeds:** a seed writes 0 births (`te_dg_stepped = 0`), so the refresh skips it and M stays as it was.
  - An 1836 state runs on the curves until its first step, its second yearly pulse (the first re-seeds, `te_dg_reseed`). So does a re-seeded state with no M yet.
  - Storing an equilibrium rate at the seed would start M a pulse earlier. Step 5 needs that figure for Display only and Disabled, and builds it there.
  - **A seed clears the target** (batch 1 review, Q1; built with Task 3's fixes): it removes `te_dg_cbr_model` / `te_dg_cdr_model`, zeroes `te_dg_bz` / `te_dg_dz` and sets `te_dg_tfr_model` to the seed's TFR. The old target is another state's (a merge or split) or years stale (a census gap). Kept, it would scale the first step after the seed by the ratio of the old rate to today's: about ±25% of births across SoL 5↔15, and −37% after years under Disabled. That step takes no on-top scales instead. Pinned by `test_a_seed_clears_the_target_and_the_scales`.
- **Old saves:** M arrives at each state's next step. That step takes no on-top scales, since `te_dg_cbr_model` is absent.
- **Rule switches:** `te_demog_rates_clear` leaves `te_dg_cbr_model`. After a switch from Display only back to Full, M applies at once from the last step's rate, which is harmless.

### Fast mode's ×K

At a clock step the engine must run `K × (T + Σ bare × O)`, so F scales the state's whole average with the new M in it:

```
avg = te_dg_w_eb / te_dg_w_eb0 − F_prev − M_prev,     F = (K − 1) × (avg + M_new)
```

- `te_demog_fast_refresh_rates` already does this without M. Task 5 takes M_prev off, puts M_new in, and reads both from the refresh's locals.
- M itself is computed for K = 1: T is the model's events per census year, over 12.

### The census's own accounting: the ring follows the engine

With M on, the engine's events over a step are the model's plus the terms on top, plus whatever the clamp and the floors leave. Phase 1 lets the scale absorb any gap, which spreads it over every age. Births added on top (`low_pop_state`, the Natalism decree, a famine's −0.9) are newborns by definition, so the step now scales its own rates to the engine's totals before the sweep:

```
bz = te_dg_eb / (te_dg_cbr_model × state_population / 1000) − 1        (−0.9 … +4)
dz = te_dg_ed / (te_dg_cdr_model × state_population / 1000) − 1        (−0.9 … +4)
```

- **The year's rates:** tfr × (1 + bz), and the five cause multipliers × (1 + dz).
- **Deaths fall by the model's age pattern** (owner, 2026-10-10: decided (c), §3): on infants, small children and the old in a high-mortality year.
- **The replay:** its head logs the scaled locals, so `demographics_harness.py replay` stays exact with no format change.
- **The model's own events** (M's next target) come back out as `births / (1 + bz)` and `(deaths − maternal) / (1 + dz) + maternal / (1 + bz)`, stored as `te_dg_cbr_model` / `te_dg_cdr_model`.
- **What the panel shows:**
  - CBR, CDR and children per woman are the realized ones. That answers §13's question: "the panel should show what actually happens".
  - Life expectancy, e65 and infant mortality stay the census's life table at its own rates ("before famine, war and disasters", which the tab's explanation says).
  - **The player's twenty-year projection** runs on the model's own rates too (batch 1 review, I1). Its mortality is the states' unscaled `te_dg_m_*`. Its children per woman is `te_dg_tfr_model`, weighted by women aged 15–49 as `te_dg_tfr` is, falling back to `te_dg_tfr` for a state with none. On the realized TFR it ran about 30% hot before M existed, and after M a famine year would skew it for twenty years. Pinned by `test_projection_runs_on_the_models_own_tfr`.
- **The ring follows the engine only up to the model's year-on-year change.**
  - bz is this window's engine events over the *last* step's model rate, applied to *this* step's rate. So the ring's births differ from the engine's by how much the model moved in a year.
  - The scale pass absorbs that as it does today.
- **A bias in famines.** With dz near its cap, the oldest groups' rates hit the 100,000 cap, so `(deaths − maternal) / (1 + dz)` understates the model's own deaths and M_d aims a little low the next year.
  - Bounded, and confined to capped old-age groups.
  - Not corrected: the fix would move dz out of the logged multipliers and change the replay format.

### The game rule

- **Full:** M and the on-top scales.
- **Display only and Disabled:** no M and no on-top scales. The refresh clears them, so a mid-game switch takes effect at each state's next step.
- **The removals and INJECTs of Tasks 6 and 8 are static and apply under every setting.** Until step 5 gives Display only and Disabled their equilibrium rates (§11.4), those settings lose the absorbed lines with nothing in their place:
  - vanilla's health-law mortality cuts;
  - child labour's class deaths;
  - women's rights' birth lines (after Task 8);
  - the mod's flat lines.
- **The default is accepted with a precondition** (owner, 2026-10-10): the census is unreleased and ships only when the owner judges it ready, and **steps 4 and 5 ship together**. This is recorded in the Global Constraints, Task 11 (`mod_systems.md` § Demographics and the calibration plan) and Task 12's gate. The repo has no release checklist doc; `git grep -il 'release checklist\|before release' docs` finds none.
- **The fallback if step 5 slips: a rule-gated restore.**
  - One static modifier per absorbed vanilla carrier, about eight: the three health laws, the two child-labour laws, and the women's-rights laws after Task 8. Each carries vanilla's line and is applied only outside Full.
  - It is refreshed from the country's yearly pulse (ROOT = the country, `owner = { has_law }`), with `multiplier` = the institution level for the per-level health lines, and re-applied on a law change through `on_law_activated`.
  - **Against:** each restore shows as its own modifier rather than on its law, and step 5 deletes it all.
- **Also weighed:**
  - Cancelling inside M under Full only, with no INJECTs. M would read the absorbed state lines and the per-pop class terms, and the law tooltips would list effects the census silently cancels.
  - A Full-only cancel by modifier. This keeps Display only and Disabled vanilla for good, but the default setting's tooltips still list the cancelled lines.

  Both are rejected (memory: loc promises the code doesn't deliver).

## 3. Owner rulings and owner calls

### (a) Which terms the census absorbs and which are added on top

- **The rule:**
  - standing law and technology lines the census models at matching size are **absorbed**;
  - shocks, local conditions and player actions are **added on top**;
  - a line the census has no term for, or none of matching size, stays **on top** until it has one.

  The census is fitted to history with laws and techs as inputs (#855, #857), so a standing line on top shifts every country it covers, permanently.
- **The exception:** child labour, absorbed by owner ruling at a smaller size.

| Term | Kind | Size (evidence) | The census's own term | Ruling or recommendation |
|---|---|---|---|---|
| The SoL curves | engine | the base | the wealth term, poverty, nutrition | absorbed: M nets out the bare curve by construction |
| `literacy_penalty`, −0.1 × literacy (per pop) | engine code | fitted −0.101 (E7) | education's term | **absorbed**, netted in M |
| The health laws: Charitable −0.03 a level, Public −0.05 a level, Private −0.002 wealth mortality a level | vanilla laws (E12) | 5% of people under one in 1837, 15% in 1887 | access × treatment, fitted to the medicine anchors | **absorbed**, by inverse INJECT (E13) |
| Child labour's class lines, +0.05 / +0.02 | vanilla laws (E12) | Child Labor Allowed covers 97–100% of people. Its +0.05 falls on classes holding 91% of people: about 0.22 points of world growth a year, and +4.1% of curve deaths in 1949 (E8) | work +0.1 under Child Labor Allowed, on ages 15–64 only: +0.09 deaths per 1,000 at 1836 inputs (+0.28% of deaths), **about a twenty-fifth of vanilla's** | **absorbed: owner ruling, 2026-10-10.** Vanilla's lines are probably far too high, so the census's smaller term is the intended size. `predict` and the gate report what absorbing them adds to world growth (Tasks 10, 12) |
| Women's rights' birth lines: No Women's Rights +0.05, Women in the Fields −0.10, Women in the Workplace −0.05, Women's Suffrage −0.05, the mod's Protected Class −0.10 | vanilla laws (E12); `extra_laws.txt:4138` | No Women's Rights covers 83% of people in 1837 | **none yet**: `demographics_model.fertility` reads no women's-rights law | **added on top until Task 7 builds the census's term, then absorbed in Task 8** (owner ruling, 2026-10-10). The term's size: owner call (d), decided |
| The mod's flat lines that already have a census term: the Pill −0.10 births (contraception +0.05); State-Sponsored Family Planning −0.05 births (Fertility Control +0.1); `modern_vaccines` and `antibiotic_mass_production` −0.05 deaths and +0.05 births each (infection treatment 0.25 and 0.11); the Ministry of Consumer Protection −0.01 a level (external −0.08 a level) | mod | — | yes | **absorbed**, removed at source (§8.4) |
| The augmentation laws: Unrestricted −0.05 flat; Medical Only, Regulated Market and Mandatory −0.02 a level of their institutions | mod | −0.02 a level is −10% at level 5 and −16% at level 8 | chronic treatment (modifier-types design, "Not decided here") | **absorbed**, as flat chronic-treatment lines that match the design note's totals: Medical Only +0.10, Unrestricted and Regulated Market +0.05, chronic cap 0.80 → 0.85. Mandatory has no value in the note: +0.05 (owner, 2026-10-10). Task 6's medicine scenarios bound them |
| The other family-policy laws: Pro-Natalist Subsidies +0.10, Population Control Measures −0.10, Communal Child Rearing −0.20 births | mod | — | none yet: §8.1's desired-fertility terms and measures aren't built | **added on top until §8.1** gives them census terms (owner-approved) |
| `second_wave_feminism` −0.025 and `sexual_revolution` −0.025 births | mod techs | small; eras 7–8 | none: neither is a means carrier | **added on top** for now |
| The LGBTQ rights laws (Legal Limbo −0.05; Basic Protections, Comprehensive Rights, Full Equality −0.10 births); State Eugenics +0.10 births; `mental_health_awareness` −0.05, `biological_immortality` −0.20, `mind_backups` −0.05 deaths | mod | era 6 and later, outside the 1836–1900 gate | none (immortality is phase 3's) | **added on top**; revisit with step 6's post-1900 schedules |
| The Natalism Initiative decree, +0.5 births | mod decree | large, temporary | §8.1's measures replace it later | **added on top** (a player action) |
| Starvation: births −0.7 × scale / −0.9; deaths +0.6 × scale / +1.0 (per pop) | engine code | +0.1–0.3% of deaths in 1949 | none | **added on top**; its deaths by the model's age pattern (c) |
| Devastation, +1.0 × level | engine code | E14 | none | **added on top** |
| Pollution, +0.5 × impact (+0.05 mod) | engine code | E15 | none (spec: read through) | **added on top** |
| Turmoil (`state_mortality_turmoil_mult` per turmoil); wealth mortality | engine | ≈ 0 (E16) | none | **added on top** by construction (unreadable) |
| `working_conditions`, production methods' and building groups' mortality, character traits | engine and vanilla | +1.0%, +0.5%, +0.7% (E8) | none: the work cause sees laws, not workplaces | **added on top**: the player's and the AI's choice of method matters |
| Non-homeland mortality | engine | ≈ 0 | none | **added on top** |
| `low_pop_state` +0.5 births; `unemployment_birth_penalty_state` −0.1 × rate | engine code | unmeasured (P1 logs the birth read) | none: vanilla's frontier filling and the slump's | **added on top** |
| Event, journal, company, principle (Food Standardization −0.1), amendment and decree modifiers; Forced Heirship's rural cut (−0.15 × the agrarian share) | vanilla and mod | various | none (spec §2.3: read through) | **added on top** |
| Pro-Natalist's −0.05 working-adult (§8.4) | mod | — | not births or deaths | out of step 4: it goes with the workforce effects |

**The alternative to absorbing before the census has a term of matching size: build the term first.** That would mean child-labour mortality on ages 5–14 for child labour, and the means or a fertility term for women's rights. The owner chose it for women's rights (Tasks 7–8) and declined it for child labour.

### (b) The starving slope below SoL 4: decided (owner, 2026-10-10)

**The census's poverty term replaces the slope.** M nets out the bare curve, so the slope's extra deaths disappear, and nothing adds them back.

The evidence (gate run's saves, §1):
- **The cost:** the slope costs world growth 0.04 points a year in 1837 and 0.17 in 1887. In 1887 that is China 0.24, India 0.21, Russia 0.20 and Japan 0.19.
- **The poverty term was fitted without it** (#855): ×1.75 at SoL 5, chosen because it gives China +0.3% a year in 1887. ×2 was rejected because China shrinks (−0.1%).
- **Keeping the slope would take China to about +0.06%.** That is arithmetic (the history check's rounded +0.3% less 0.244, good to about ±0.05), not a model run.
- **Who sits below SoL 4:** laborers (12% of the world's people in 1887) and slaves.

The slope acts per pop and the poverty term on the state's mean SoL, so a destitute pop in a middling state loses the slope's deaths. The history check found pop-by-pop poverty no better (5.9 years of error against 5.6). `predict --slope` keeps printing the slope's cost, so the gate run shows it.

### (c) Deaths added on top, by age: decided (owner, 2026-10-10)

**They fall by the model's age pattern** (young and old): one dz on every cause multiplier.
- Spec §2.4 says "starvation and disease fall on the young and old", and the famine literature agrees (e.g. Ó Gráda, *Famine: A Short History*, 2009).
- Devastation ("everyone" in §2.4) and pollution ("the old") are approximated by the model's own pattern, which in the 19th century is young and old.
- A per-term split would need three walk sums: starvation and disease by the pattern, devastation through the kills channel, pollution on chronic causes. It waits until the panel shows an artefact.
- Births added on top have no choice to make: they are newborns.

### (d) The size of the census's women's-rights fertility term (Task 7; decided)

**Owner, 2026-10-10: the recommendation below, vanilla's lines re-centred on No Women's Rights.**


- **The carrier.** A new script-only type, `state_natural_fertility_mult`, on the women's-rights laws. It multiplies the wealth term, natural fertility, before the means: `tfr = wealth × (1 + natural) × (1 − means × (1 − desired))`.
- **Why natural fertility and not the means.** The means term is the share of the gap to desired fertility a population can close. In 1836 that is about 0.4 × (0.3 + 0.7 × 0.2) ≈ 0.18, and the gap is small, so a means shift barely moves 1836 births. +0.1 changes children per woman by about 1.5%. Vanilla's lines move births by 5–15% in any year.
- **Why natural fertility fits historically.** It is the channel women's legal status works through before contraception: who marries and when. That is step 2's marriage-regime question in the calibration plan.
- **The floor reference: vanilla's own lines, re-centred on No Women's Rights**, so that step 2's fertility fit (83% of the world under No Women's Rights) is unchanged:

| Law | Vanilla's line | Re-centred | Recommended term |
|---|---|---|---|
| No Women's Rights | +0.05 | 0 | 0 |
| Women in the Fields | −0.10 | −0.15 | −0.15 |
| Women Own Property | none | −0.05 | −0.05 |
| Women in the Workplace | −0.05 | −0.10 | −0.10 |
| Women's Suffrage | −0.05 | −0.10 | −0.10 |
| Protected Class (mod) | −0.10 | −0.15 | −0.15 |

- **History bounds it but doesn't pin it.** Gapminder's children per woman (the `tfr` anchors `history` reads, file of 2026-10-10) give the West's range:
  - 1900: UK 3.53, France 2.80 … Germany 4.93.
  - 1950: Austria 1.87, UK and Germany 2.08, Sweden 2.28 … Netherlands 3.10, US 3.02.
  - 1990: Italy 1.30, Germany 1.36 … Sweden 2.14, US 2.07.

  The harness's Western scenarios, with the women's-rights law their countries held (`demographics_harness.py fertility`, 2026-10-10):

  | Scenario | Without | Recommended size | Half size | Gapminder |
  |---|---|---|---|---|
  | Britain 1900, Women Own Property | 3.85 | 3.66 | 3.76 | UK 3.53 |
  | West 1950, Women's Suffrage | 2.55 | 2.29 | 2.42 | median of nine Western countries 2.31 |
  | West 1990, Women's Suffrage | 1.59 | 1.43 | 1.51 | median of the same nine 1.62 |

  The nine: Austria, Belgium, France, Germany, Italy, the Netherlands, Sweden, the UK and the US.

  - **Range:** both sizes stay inside the West's range each year.
  - **Direction:** the recommended size moves Britain 1900 and the West 1950 toward history, and the West 1990 slightly away. By 1990 the Pill and other terms dominate.
  - **Bands:** the existing West 1950 row's band (2.3–3.5) predates any women's-rights term. The new rows take Gapminder's range, so both sizes pass.
  - **Literacy:** nothing in the repo's evidence separates a law's effect from literacy's, which the census already counts.
- **Recommendation:** the re-centred sizes above, so absorbing vanilla's lines in Task 8 removes nothing a player could feel.
- **The alternative:** half of each. History doesn't favour it except in 1990, and the lever would then be about half of vanilla's.

## 4. Probes

| Probe | Question | Design | Blocks |
|---|---|---|---|
| **P1** | Are devastation's and pollution's mortality lines in `modifier:state_mortality_mult`, and as what share? (The mod's INJECTed +0.05 on pollution sums: owner, 2026-10-10, E15.) | Console option m (Task 1), on today's build with no M and fast mode off. Every state in the world with devastation or a polluted region logs its mortality and birth reads, devastation, turmoil and pollution, with `debug_log_scopes = yes` to name it. Load the 1887 gate save (5 devastated states), fire option m, and hover each logged state's mortality in game. If the tooltip's total is the logged `mort`, the lines are in the read | Nothing in M. It decides whether the residual and the clamp's "other" see these deaths. If they don't, a follow-up adds `devastation` per pop to `te_demog_pop_death_mult` |
| **P2** | Do the absorptions leave no line behind? | After Tasks 6 and 8, read in the law and tech panels: Charitable Health System, Private Health Insurance, Public Health Insurance, Child Labor Allowed, Restricted Child Labor, No Women's Rights, Women in the Fields (a variant: its own block must net to nothing), Women in the Workplace, Women's Suffrage, Protected Class, the Contraceptive Pill, Modern Vaccines, Antibiotic Mass Production, State-Sponsored Family Planning, the Ministry of Consumer Protection and the four augmentation laws. None should list a mortality or birth-rate line; a cancelled line disappears from its tooltip, the monetary precedent. Option l's log of the capital's reads should drop by the old lines | Confirms Tasks 6 and 8 (shape verified, E13) |
| **P3** | Does the engine hit the target in game? Is M's fixed point stable? | Option n (Task 4) logs the capital's M, F, targets, on-top scales and reads. The census line (Task 9) carries `m_b`, `m_d`, `bz`, `dz` and `clamped`. In the gate's fast-mode run, `bz` and `dz` measure each country's gap between the engine and the target. They should sit at the share of the terms on top (a few per cent) and not drift | The gate (Task 12) |
| **P4** | Does a state keep its census modifiers through a change of owner? | Offline: `demographics_harness.py predict SAVE --check-modifiers` (Task 10) lists states whose `te_dg_mb` is not 0 but whose `timed_modifiers` lack the matching census modifier. Run it on a fast-run save taken after a war or a civil war | Nothing: the `has_modifier` guard (Review Focus 2) and the next step's refresh cover a loss. The answer goes in the results doc |
| **P5** (conditional) | Turmoil's scaling | The growth probe on high-turmoil states, with a test `state_mortality_turmoil_mult` | Run only if the gate run shows a residual tied to turmoil |

- **Verified already, no probe needed:** E1, E2, E5, E6, E9, E10, E11, E12, E13, E20.
- **No longer a probe:** linearity above +1.0 is answered by the fast run (E10).

## 5. File structure

| File | Change | Responsibility |
|---|---|---|
| `scripts/analysis/demographics_params.py` | modify | the clamp, the on-top scales' bounds, `LITERACY_BIRTH_PENALTY`, the natural-fertility type, the table of carriers on top |
| `scripts/analysis/demographics_model.py` | modify | `rate_term`, `on_top_scale`, `step(..., births_scale, deaths_scale)` and its model totals, `model_crude_rates`, `starvation_terms`, the natural-fertility term in `fertility` |
| `scripts/generators/gen_demographics.py` | modify | the new `te_demog_k_*` constants (generated values) |
| `common/scripted_effects/te_demog_rate_effects.txt` | **create** | `te_demog_on_top_scales`, `te_demog_rates_refresh`, `te_demog_rate_clamp`, `te_demog_rates_apply`, `te_demog_rates_remove`, `te_demog_rates_clear` |
| `common/scripted_effects/te_demog_effects.txt` | modify | the walk's `te_dg_w_ebl`; `te_demog_step_begin` calls the on-top scales; the maternal accumulator; `te_demog_step_finish` stores the model's rates; the orchestrator calls the refresh |
| `common/scripted_effects/te_demog_fast_effects.txt` | modify | the clock step calls the refresh; F takes M off and puts it back, from the refresh's locals |
| `common/script_values/te_demog_values.txt` | modify | `te_demog_rate_*` and `te_demog_fast_*_applied`; `te_demog_tfr` takes natural fertility |
| `common/static_modifiers/te_demog_modifiers.txt` | modify | the four census modifiers |
| `common/modifier_type_definitions/demographics_modifier_types.txt` | modify | `state_natural_fertility_mult` |
| `common/laws/modified_health_system.txt`, `common/laws/te_demog_law_injections.txt` | modify | the inverse INJECTs on the health and child-labour laws |
| `common/laws/extra_laws.txt` | modify | §8.4's removals, augmentation's chronic lines, the women's-rights terms (Task 7) and the inverse INJECTs of their birth lines (Task 8, in the existing blocks at `extra_laws.txt:78-98`) |
| `common/technology/technologies/era_6.txt`, `era_7.txt`, `common/institutions/extra_institutions.txt` | modify | §8.4's removals |
| `scripts/analysis/demographics_modifiers.py` | modify | `engine_rate_lines()`: every birth and mortality line on a law, tech or institution, vanilla's and the mod's summed |
| `common/scripted_effects/te_debug_demog_effects.txt`, `events/te_debug_demog_events.txt` | modify | options m and n; the census line's new fields |
| `scripts/analysis/demographics_observer_report.py` | modify | `--phase2` |
| `scripts/analysis/demographics_save_inputs.py`, `scripts/analysis/demographics_harness.py` | modify | food security and devastation from saves; `predict`; the augmentation and women's-rights scenarios |
| `localization/english/te_miscellaneous_l_english.yml`, `te_events_l_english.yml`, `te_modifiers_l_english.yml` | modify | the modifiers', the new type's and the console's keys; the augmentation tooltips |
| Tests | modify | `test_demographics_model.py`, `test_demographics_registry.py`, `test_gen_demographics.py`, `test_demographics_modifiers.py`, `test_demographics_observer_report.py`, `test_demographics_save_inputs.py`, `test_demographics_harness.py` |
| Docs | modify | `docs/systems/mod_systems.md` § Demographics; the spec's §2.3/§2.4 "Applied as", §8.4 and §13; the calibration plan's step 4; `docs/guides/vanilla_patch_runbook.md` (the new cancels); `docs/guides/python_tools.md` (`predict`); `docs/player_guide/08-states.md` and `06-politics.md`; the PDF |
| `docs/testing/demographics-phase2-engine-rates-<date>.md` | **create** (Task 12) | the probes' and the gate's results |

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

- [ ] **Step 4: Add option m** (after option l in `te_debug_demog_events.txt`). The header's option list lacks l today. Add both:
"l    the census's mortality and fertility modifier types as the capital and an unincorporated state read them (TE_DEMOG_MODS)" and
"m    the shock terms (probe P1): every devastated or polluted state's reads (TE_DEMOG_SHOCK)".

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
- Test: `test_demographics_model.py` (new classes `TestRateTerm`, `TestOnTopScales`)

**Interfaces:**
- Produces:
  - `P.RATE_TOTAL_MIN = -0.8`, `P.RATE_TERM_MAX = 3.0`, `P.ON_TOP_SCALE_MIN = -0.9`, `P.ON_TOP_SCALE_MAX = 4.0`, `P.LITERACY_BIRTH_PENALTY = -0.1`.
  - `M.rate_term(target: float, bare: float, absorbed: float = 0.0, other: float = 0.0) -> tuple[float, bool]`.
  - `M.on_top_scale(engine: float, target: float) -> float`.
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

    def test_terms_on_top_add_at_the_bare_curves_weight(self):
        """The engine adds every term (growth probe): with M on, a pop's events are bare x (1 + M + O).
        The state's then come to the model's plus bare x O."""
        m, _ = M.rate_term(target=80.0, bare=100.0)
        on_top = 0.3
        self.assertAlmostEqual(100.0 * (1 + m + on_top), 80.0 + 100.0 * on_top)

    def test_absorbed_terms_are_netted(self):
        # literacy's -0.1 x a bare-weighted literacy of 0.4: the absorbed sum is -0.1 x 40 over bare 100
        m, _ = M.rate_term(target=80.0, bare=100.0, absorbed=P.LITERACY_BIRTH_PENALTY * 40.0)
        self.assertAlmostEqual(100.0 * (1 + m) + P.LITERACY_BIRTH_PENALTY * 40.0, 80.0)

    def test_the_clamp_keeps_the_state_total_in_the_measured_range(self):
        m, clamped = M.rate_term(target=5.0, bare=100.0, other=0.1)
        self.assertAlmostEqual(m, P.RATE_TOTAL_MIN - 0.1)
        self.assertTrue(clamped)
        m, clamped = M.rate_term(target=600.0, bare=100.0)
        self.assertEqual(m, P.RATE_TERM_MAX)
        self.assertTrue(clamped)

    def test_the_clamp_never_pushes_past_the_terms_on_top(self):
        """A plague event or a decree already past -0.8 in the state read (starvation is per pop, outside it): M may
        not push further down."""
        m, clamped = M.rate_term(target=5.0, bare=100.0, other=-1.2)
        self.assertEqual(m, 0.0)
        self.assertTrue(clamped)

    def test_nobody_gets_no_term(self):
        self.assertEqual(M.rate_term(target=0.0, bare=0.0), (0.0, False))

    def test_the_bounds(self):
        self.assertEqual(P.RATE_TOTAL_MIN, -0.8)   # -0.9 measured, less literacy's -0.1
        self.assertEqual(P.RATE_TERM_MAX, 3.0)     # a guard: linearity holds far above (the 12x fast run)


class TestOnTopScales(unittest.TestCase):
    """The census's ring follows the engine: the step scales its rates by how far the engine ran from the target."""

    def test_scale_is_engine_over_target(self):
        self.assertAlmostEqual(M.on_top_scale(engine=105.0, target=100.0), 0.05)
        self.assertEqual(M.on_top_scale(engine=50.0, target=0.0), 0.0)
        self.assertEqual(M.on_top_scale(engine=1.0, target=100.0), P.ON_TOP_SCALE_MIN)
        self.assertEqual(M.on_top_scale(engine=1000.0, target=100.0), P.ON_TOP_SCALE_MAX)

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

Run: `.venv/bin/python -m unittest test_demographics_model.TestRateTerm test_demographics_model.TestOnTopScales`
Expected: FAIL, `AttributeError: module 'demographics_model' has no attribute 'rate_term'`.

- [ ] **Step 3: Add the parameters** (`demographics_params.py`, after `STARVATION_BUCKET`)

```python
# ---- phase 2 step 4: the census sets the engine's births and deaths --------------------------
# docs/superpowers/plans/2026-10-10-demographics-phase2-engine-rates.md §2. The engine adds every term
# into one (1 + total) per pop, linear from -0.9 (growth probe) to far above +1.0 (the 12x fast run), floored
# at 0. Owner, 2026-10-10: the poverty term replaces the curve's starving slope below SoL 4, and deaths added
# on top fall by the model's age pattern (the step's deaths scale).
RATE_TOTAL_MIN = -0.8         # the state read with M in it stays at or above this (-0.9 less literacy's -0.1)
RATE_TERM_MAX = 3.0           # a guard against a nonsense target, not a measured limit
ON_TOP_SCALE_MIN = -0.9       # the step's births and deaths scales (the engine's events over the model's target)
ON_TOP_SCALE_MAX = 4.0
LITERACY_BIRTH_PENALTY = -0.1 # literacy_penalty's state_birth_rate_mult (the mod's REPLACE keeps vanilla's)
STARVATION_MILD = {"births": -0.7, "deaths": 0.6}     # starvation_penalty (vanilla code static modifier)
STARVATION_SEVERE = {"births": -0.9, "deaths": 1.0}   # severe_starvation_penalty
STARVATION_MILD_CAP = 0.5     # (threshold - severe threshold) x scaling factor: vanilla's comment
```

- [ ] **Step 4: Add the functions and the step's scales** (`demographics_model.py`)

```python
def rate_term(target, bare, absorbed=0.0, other=0.0):
    """The census's births or deaths modifier for one state (phase 2 step 4). Returns (M, clamped).

    The engine gives each pop bare x max(0, 1 + its terms + M) (growth probe), so over a state M adds
    M x bare. M = target / bare - 1 - absorbed / bare makes the engine's events the model's (target)
    plus every term added on top, at the bare curve's weight. All three are in the same units (the walk's:
    events a month x 100,000). `other` is the state read without the census's and fast mode's
    terms: other + M stays at or above RATE_TOTAL_MIN, M never goes below 0 when other alone is
    past it, and M stays at or below RATE_TERM_MAX.
    """
    if bare <= 0:
        return 0.0, False
    m = target / bare - 1 - absorbed / bare
    lo = min(0.0, P.RATE_TOTAL_MIN - other)
    if m < lo:
        return lo, True
    if m > P.RATE_TERM_MAX:
        return P.RATE_TERM_MAX, True
    return m, False


def on_top_scale(engine, target):
    """How far the engine's births or deaths over a step ran from the model's target, as a scale for the
    step's rates: engine / target - 1, clamped to ON_TOP_SCALE_MIN..ON_TOP_SCALE_MAX; 0 with no target."""
    if target <= 0:
        return 0.0
    return clamp(engine / target - 1, P.ON_TOP_SCALE_MIN, P.ON_TOP_SCALE_MAX)


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
git commit -m "Demographics phase 2 step 4: the model's rate term, on-top scales and model totals (Python twin)"
```

---

### Task 3: The step takes the terms on top (script)

**Files:**
- Create: `common/scripted_effects/te_demog_rate_effects.txt` (with `te_demog_on_top_scales` only; Task 4 adds the rest)
- Modify: `common/scripted_effects/te_demog_effects.txt` (`te_demog_step_begin`, `te_demog_reset_accumulators`, `te_demog_age_slot`, `te_demog_step_finish`, the header's variable list)
- Modify: `scripts/generators/gen_demographics.py` (`constants`: the bounds; `engine_rate_terms`: the literacy constant) and regenerate
- Test: `test_demographics_registry.py` (`_Engine` loads the new file; new tests in `TestCohortScript`), `test_gen_demographics.py`

**Interfaces:**
- Consumes: `M.step(..., births_scale, deaths_scale)`, `M.on_top_scale` (Task 2).
- Produces:
  - **State variables:** `te_dg_bz`, `te_dg_dz` (the last step's scales); `te_dg_cbr_model`, `te_dg_cdr_model` (per 1,000 a year: the model's own, M's next target); `te_dg_tfr_model`.
  - **Constants:** `te_demog_k_on_top_scale_min`, `te_demog_k_on_top_scale_max`, `te_demog_k_rate_total_min`, `te_demog_k_rate_term_max`, `te_demog_k_literacy_birth_penalty`.

- [ ] **Step 1: Write the failing tests**

In `test_demographics_registry.py`:
- Add `RATE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_rate_effects.txt"` beside `FAST_EFFECTS`.
- Add `RATE_EFFECTS` to the list in `_Engine.__init__`: `_raw_blocks([EFFECTS, GENERATED_EFFECTS, WEALTH_EFFECTS, FAST_EFFECTS, RATE_EFFECTS])`.
- Extend `TestCohortScript.step_both` with two keyword arguments, `on_top=None` and `full=False`. It already builds the before-state on both sides and stubs `te_demog_flows`, so the step's own residual and flows stay out of the comparison. Right after `eng.fixtures.update(fixtures)`:

```python
        bz = dz = 0.0
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
```

  Then pass `births_scale=bz, deaths_scale=dz` to its `demographics_model.step(...)` call.
- Add to `TestCohortScript`:

```python
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

    def test_no_on_top_scales_outside_full(self):
        eng, ring, figures, pop = self.step_both(on_top=(0.05, 0.12), full=False)
        self.check_step(eng, ring, figures, pop)
        self.assertEqual((eng.vars["te_dg_bz"], eng.vars["te_dg_dz"]), (0.0, 0.0))

    def test_no_target_no_scales(self):
        """An old save, or the first step after phase 2 arrives: no te_dg_cbr_model yet."""
        eng, ring, figures, pop = self.step_both(full=True)
        self.check_step(eng, ring, figures, pop)
        self.assertEqual((eng.vars["te_dg_bz"], eng.vars["te_dg_dz"]), (0.0, 0.0))

    def test_on_top_scales_are_clamped(self):
        eng, ring, figures, pop = self.step_both(on_top=(9.0, -0.99), full=True)
        self.check_step(eng, ring, figures, pop)
        self.assertEqual(eng.vars["te_dg_bz"], P.ON_TOP_SCALE_MAX)
        self.assertEqual(eng.vars["te_dg_dz"], P.ON_TOP_SCALE_MIN)

    def test_the_replay_logs_the_scaled_rates(self):
        """te_debug_demog_replay logs the locals after te_demog_step_begin, so the scales are in the head's tfr
        and multipliers and the harness's replay needs no new field."""
        body = _block(_text(EFFECTS), "te_demog_step_begin")
        self.assertLess(body.index("te_demog_prepare = yes"), body.index("te_demog_on_top_scales = yes"))
        self.assertIn("te_demog_step_begin = yes", _block(_text(CONSOLE_EFFECTS), "te_debug_demog_replay"))
```

In `test_gen_demographics.py`, in `TestGenerated` (its `setUpClass` holds the generated values as `cls.values`; the generator is imported as `gen`):

```python
    def test_phase2_constants_match_the_params(self):
        for name, value in (("on_top_scale_min", P.ON_TOP_SCALE_MIN), ("on_top_scale_max", P.ON_TOP_SCALE_MAX),
                            ("rate_total_min", P.RATE_TOTAL_MIN),
                            ("rate_term_max", P.RATE_TERM_MAX),
                            ("literacy_birth_penalty", P.LITERACY_BIRTH_PENALTY)):
            self.assertIn(f"te_demog_k_{name} = {{ value = {gen.lit(value)} }}", self.values, name)
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestCohortScript test_gen_demographics`
Expected: FAIL. The new file is missing (`_raw_blocks` raises on the path), then `KeyError: 'te_dg_bz'`; the generator test fails on `te_demog_k_on_top_scale_min`.

- [ ] **Step 3: Generate the constants**

In `gen_demographics.constants`, add to `k`:

```python
        "on_top_scale_min": P.ON_TOP_SCALE_MIN, "on_top_scale_max": P.ON_TOP_SCALE_MAX,
        "rate_total_min": P.RATE_TOTAL_MIN,
        "rate_term_max": P.RATE_TERM_MAX,
```

In `engine_rate_terms`, after reading `literacy`, emit the constant from the static modifier itself, so the census nets exactly what the engine applies. Then assert the params agree:

```python
    o(f"te_demog_k_literacy_birth_penalty = {{ value = {lit(literacy)} }}")
    assert literacy == P.LITERACY_BIRTH_PENALTY, "literacy_penalty changed: update LITERACY_BIRTH_PENALTY"
```

Run: `.venv/bin/python scripts/generators/gen_demographics.py`. The generator writes formatted tabs itself (`test_tabs_already_formatted`).

- [ ] **Step 4: Write the on-top scales** (create `common/scripted_effects/te_demog_rate_effects.txt` with a BOM)

```
# ============================================================================
# DEMOGRAPHICS — the census sets the engine's births and deaths (phase 2 step 4)
# docs/superpowers/plans/2026-10-10-demographics-phase2-engine-rates.md §2
# ============================================================================
# The engine gives every pop curve x max(0, 1 + total) births and deaths, adding every
# term (docs/testing/demographics-growth-probe-results-2026-10-09.md). The census's term M
# (te_demog_rates_refresh) makes a state's events the model's plus the terms added on top of
# the census, and the census's next step scales its own rates to what the engine did
# (te_demog_on_top_scales), so the ring places the births and deaths added on top by age:
# newborns, and deaths by the model's own age pattern (owner, 2026-10-10).
#
# State variables:
#   te_dg_mb, te_dg_md  M for births and deaths (signed), behind the te_demog_census_* pair
#   te_dg_rate_clamped  1 when the last refresh clamped either term
#   te_dg_bz, te_dg_dz  the scales the last step used (te_dg_eb or te_dg_ed over the target,
#                       less 1)
#   te_dg_cbr_model, te_dg_cdr_model, te_dg_tfr_model  the model's own rates (per 1,000 a year;
#                       children per woman): the step's events without the on-top scales
# ============================================================================

# THIS = a state at the start of its step, straight after te_demog_prepare and te_demog_flows:
# the year's rates scaled by how far the engine's expected births and deaths over the window
# (te_dg_eb, te_dg_ed, from this step's walk) ran from the model's rates that M aimed at, at
# today's population. Under Full only, and only once a step has stored the model's rates.
te_demog_on_top_scales = {
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
					min = te_demog_k_on_top_scale_min
					max = te_demog_k_on_top_scale_max
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
					min = te_demog_k_on_top_scale_min
					max = te_demog_k_on_top_scale_max
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
	te_demog_on_top_scales = yes
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
	# the model's own rates without the on-top scales: what the census's births and deaths modifiers aim at
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
                                             absorbed=P.LITERACY_BIRTH_PENALTY * ebl, other=other_b)
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
        eng.modifiers["te_demog_census_births_down"] = 0.2
        eng.vars["te_dg_mb"] = -0.2
        eng.call("te_demog_rates_refresh")
        self.assertEqual(eng.locals["te_dg_rate_new_b"], -0.2)

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
		# bare births by literacy: the absorbed literacy_penalty, which the census's births term nets out
		change_local_variable = { name = te_dg_w_ebl add = { value = local_var:te_dg_p_eb multiply = literacy_rate } }
```

- [ ] **Step 4: The values** (`te_demog_values.txt`, after the fast-mode terms)

```
# State scope: the census's births and deaths terms in force (phase 2 step 4,
# te_demog_rate_effects.txt): M while its modifier is on, else 0. Read through has_modifier,
# so a state that lost its modifier (a change of owner, an old save) but still has te_dg_mb
# subtracts nothing that isn't there. Only for reads a tick or more after the refresh (the next
# refresh's prior term, the census line): inside the refresh's own effect has_modifier can't see
# its add or remove, so fast mode reads the refresh's locals instead.
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
# Always leaves two pairs of locals for fast mode, which runs next in the same effect:
#   te_dg_rate_prev_b/_d  the terms the walk's window ran with (read through has_modifier
#                         before anything here touches the modifiers)
#   te_dg_rate_new_b/_d   the terms in force after this refresh: the M it set, 0 when it
#                         clears, the prior terms when it skips. A later read in this effect
#                         takes these, never has_modifier: add_modifier and remove_modifier are
#                         invisible inside the effect that made them (scripting_best_practices.md)
# A seed (te_dg_stepped 0) leaves the terms as they are.
te_demog_rates_refresh = {
	set_local_variable = { name = te_dg_rate_prev_b value = te_demog_rate_births_applied }
	set_local_variable = { name = te_dg_rate_prev_d value = te_demog_rate_deaths_applied }
	set_local_variable = { name = te_dg_rate_new_b value = local_var:te_dg_rate_prev_b }
	set_local_variable = { name = te_dg_rate_new_d value = local_var:te_dg_rate_prev_d }
	if = {
		limit = { NOT = { te_demog_effects_run = yes } }
		te_demog_rates_clear = yes
		set_local_variable = { name = te_dg_rate_new_b value = 0 }
		set_local_variable = { name = te_dg_rate_new_d value = 0 }
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
			set_local_variable = { name = te_dg_rate_new_b value = var:te_dg_mb }
			set_local_variable = { name = te_dg_rate_new_d value = var:te_dg_md }
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
# next walk takes nothing off its average and the next step no on-top scale.
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

- [ ] **Step 8: Option n, the census's rates for the capital** (probe P3)

In `te_debug_demog_effects.txt`, add `te_debug_demog_rate_lines` (THIS = the capital; copy then log then remove, as the census line does):

```
# ---- n: the census's rates (phase 2 step 4, probe P3) -----------------------------
# THIS = the capital: its census terms, the terms in force, the on-top scales of its last step,
# the model's rates and the engine's expected events over the last window, the reads. Every
# variable is copied through a guard: a capital that hasn't stepped under Full has none of them.
te_debug_demog_rate_lines = {
	te_debug_demog_rate_copy = { FROM = te_dg_mb TO = te_dg_dbg_mb }
	te_debug_demog_rate_copy = { FROM = te_dg_md TO = te_dg_dbg_md }
	te_debug_demog_rate_copy = { FROM = te_dg_bz TO = te_dg_dbg_bz }
	te_debug_demog_rate_copy = { FROM = te_dg_dz TO = te_dg_dbg_dz }
	te_debug_demog_rate_copy = { FROM = te_dg_cbr_model TO = te_dg_dbg_cbrm }
	te_debug_demog_rate_copy = { FROM = te_dg_cdr_model TO = te_dg_dbg_cdrm }
	te_debug_demog_rate_copy = { FROM = te_dg_eb TO = te_dg_dbg_eb }
	te_debug_demog_rate_copy = { FROM = te_dg_ed TO = te_dg_dbg_ed }
	te_debug_demog_rate_copy = { FROM = te_dg_rate_clamped TO = te_dg_dbg_cl }
	set_variable = { name = te_dg_dbg_ab value = te_demog_rate_births_applied }
	set_variable = { name = te_dg_dbg_ad value = te_demog_rate_deaths_applied }
	set_variable = { name = te_dg_dbg_fb value = te_demog_fast_births_applied }
	set_variable = { name = te_dg_dbg_fd value = te_demog_fast_deaths_applied }
	set_variable = { name = te_dg_dbg_read_b value = modifier:state_birth_rate_mult }
	set_variable = { name = te_dg_dbg_read_d value = modifier:state_mortality_mult }
	debug_log = "TE_DEMOG_RATES: mb=[THIS.Var('te_dg_dbg_mb').GetValue|4]; md=[THIS.Var('te_dg_dbg_md').GetValue|4]; applied_b=[THIS.Var('te_dg_dbg_ab').GetValue|4]; applied_d=[THIS.Var('te_dg_dbg_ad').GetValue|4]; fast_b=[THIS.Var('te_dg_dbg_fb').GetValue|4]; fast_d=[THIS.Var('te_dg_dbg_fd').GetValue|4]; read_b=[THIS.Var('te_dg_dbg_read_b').GetValue|4]; read_d=[THIS.Var('te_dg_dbg_read_d').GetValue|4]; bz=[THIS.Var('te_dg_dbg_bz').GetValue|4]; dz=[THIS.Var('te_dg_dbg_dz').GetValue|4]; cbr_model=[THIS.Var('te_dg_dbg_cbrm').GetValue|3]; cdr_model=[THIS.Var('te_dg_dbg_cdrm').GetValue|3]; eb=[THIS.Var('te_dg_dbg_eb').GetValue|0]; ed=[THIS.Var('te_dg_dbg_ed').GetValue|0]; clamped=[THIS.Var('te_dg_dbg_cl').GetValue|0]; date=[TimeKeeper.GetCurrentDate.GetString]"
	remove_variable = te_dg_dbg_mb
	remove_variable = te_dg_dbg_md
	remove_variable = te_dg_dbg_bz
	remove_variable = te_dg_dbg_dz
	remove_variable = te_dg_dbg_cbrm
	remove_variable = te_dg_dbg_cdrm
	remove_variable = te_dg_dbg_eb
	remove_variable = te_dg_dbg_ed
	remove_variable = te_dg_dbg_cl
	remove_variable = te_dg_dbg_ab
	remove_variable = te_dg_dbg_ad
	remove_variable = te_dg_dbg_fb
	remove_variable = te_dg_dbg_fd
	remove_variable = te_dg_dbg_read_b
	remove_variable = te_dg_dbg_read_d
}

# THIS = the capital: $TO$ = $FROM$, or 0 when the census never wrote it (option n).
te_debug_demog_rate_copy = {
	set_variable = { name = $TO$ value = 0 }
	if = {
		limit = { has_variable = $FROM$ }
		set_variable = { name = $TO$ value = var:$FROM$ }
	}
}
```

- **Option n in `te_debug_demog_events.txt`:** the click-guard pattern of option m, with `trigger = { exists = capital }` and `capital = { te_debug_demog_rate_lines = yes }` inside the guard.
- **Loc keys** (`te_events_l_english.yml`, beside option m's):

```yaml
 te_debug_demog.1.n:0 "Census rates: log our capital's births and deaths terms"
 te_debug_demog.1.n.tt:0 "Writes a TE_DEMOG_RATES line to debug.log for our capital. mb and md are the census's births and deaths terms; applied_b and applied_d are the ones in force (0 when the modifier is off); fast_b and fast_d are fast mode's. read_b and read_d are the state's whole birth and mortality totals: read less applied less fast is what the base game and events add on top. cbr_model and cdr_model are the census's own rates per 1,000 people; eb and ed are the births and deaths the engine was expected to produce over the last year. eb against cbr_model × people / 1,000 gives bz, the scale the census applied to its own births at its last step, and dz the same for deaths. clamped is 1 when a term hit its limit."
```

- **Test** (`TestConsole`): `test_option_n_logs_the_rates_click_only`, the same shape as option m's. It asserts:
  - the call is click-guarded;
  - every `te_dg_dbg_*` the effect sets is removed;
  - the log line reads no census variable raw, only `te_dg_dbg_*` copies (`re.findall(r"Var\('(\w+)'\)", line)` all start with `te_dg_dbg_`).

- [ ] **Step 9: Run everything and the audits**

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

- [ ] **Step 10: Commit**

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
        """K = 4: the engine runs 4 x (1 + on top + M) on average, M being the census's term."""
        eng = self._eng_full()
        # bare 475 a month per person; the walk's average multiplier 1.05 (terms on top +0.05)
        self._both(eng, eb=1.05 * 475e3, eb0=475e3, ed=0.98 * 430e3, ed0=430e3)
        mb = eng.vars["te_dg_mb"]
        self.assertAlmostEqual(eng.vars["te_dg_fast_fb"], 3 * (1.05 + mb), places=5)

    def test_fast_mode_reads_the_new_term_from_the_refresh(self):
        """In game, has_modifier can't see the census modifier the refresh just added in the same effect.
        Hide it from the fast refresh and the term must still come through, from the refresh's locals."""
        eng = self._eng_full()
        eng.locals.update(te_dg_w_eb=1.05 * 475e3, te_dg_w_eb0=475e3, te_dg_w_ed=0.98 * 430e3, te_dg_w_ed0=430e3,
                          te_dg_w_ebl=0.0)
        eng.call("te_demog_rates_refresh")
        self.assertIn("te_dg_mb", eng.vars)   # the applied branch ran (Full, a step's figures)
        mb = eng.vars["te_dg_mb"]
        eng.modifiers.clear()
        eng.call("te_demog_fast_refresh_rates")
        self.assertAlmostEqual(eng.vars["te_dg_fast_fb"], 3 * (1.05 + mb), places=5)
        body = _block(_text(FAST_EFFECTS), "te_demog_fast_refresh_rates")
        self.assertIn("add = local_var:te_dg_rate_new_b", body)
        self.assertNotIn("te_demog_rate_births_applied", body)

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

Existing fast-mode tests call `te_demog_fast_refresh_rates` alone. Their fixtures must now set the four locals the census refresh leaves (0.0) in `_refresh`: `eng.locals.update(te_dg_rate_prev_b=0.0, te_dg_rate_prev_d=0.0, te_dg_rate_new_b=0.0, te_dg_rate_new_d=0.0, …)`. Their figures are unchanged.

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestFastMode`
Expected: FAIL. `fast_fb` comes out as 3 × 1.05, not 3 × (1.05 + mb): the current refresh adds no census term.

- [ ] **Step 3: Implement** (`te_demog_fast_refresh_rates`; the births block, deaths the same with `_d`/`ed`)

```
		set_variable = {
			name = te_dg_fast_fb
			value = {
				value = local_var:te_dg_w_eb
				divide = { value = local_var:te_dg_w_eb0 min = 0.00001 }
				subtract = local_var:te_dg_fast_prev_b
				subtract = local_var:te_dg_rate_prev_b
				add = local_var:te_dg_rate_new_b
				min = 0
				multiply = te_demog_fast_k_minus_1
			}
		}
```

Extend the effect's comment:
- The walk's average holds last step's census term (`te_dg_rate_prev_b`, which `te_demog_rates_refresh` leaves) and fast mode's own. Both come off, and the census's new term goes in.
- So the engine runs K × (the census's target plus the terms on top) (plan §2, "Fast mode's ×K").
- Both census terms come from `te_demog_rates_refresh`'s locals. `has_modifier` can't see the refresh's add or remove in this same effect (plan E22).
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

### Task 6: The census absorbs the lines it already models

Health, child labour (owner ruling), §8.4's mod lines that have a census term, and the augmentation laws. Women's rights wait for Tasks 7–8.

**Files:**
- Modify: `common/laws/modified_health_system.txt` (inverse lines inside the three existing `institution_modifier` INJECTs)
- Modify: `common/laws/te_demog_law_injections.txt` (child labour's class lines, inside the existing `INJECT:law_child_labor_allowed`; a new `INJECT:law_restricted_child_labor`, which no mod file INJECTs today)
- Modify: `common/laws/extra_laws.txt`
  - remove State-Sponsored Family Planning's birth line;
  - the augmentation laws' mortality lines become flat chronic-treatment lines.
- Modify: `common/technology/technologies/era_6.txt`, `era_7.txt` (remove `modern_vaccines`', `antibiotic_mass_production`'s and `contraceptive_pill`'s lines)
- Modify: `common/institutions/extra_institutions.txt` (Consumer Protection's −0.01)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (the three augmentation laws' institution tooltips, which state the old −2% a level)
- Modify: `scripts/analysis/demographics_params.py` (`TREATMENT_CAP["chronic"] = 0.85`; `ENGINE_LINES_ON_TOP`), `scripts/analysis/demographics_modifiers.py` (`engine_rate_lines`), `scripts/analysis/demographics_harness.py` (the augmentation scenarios)
- Test: `test_demographics_modifiers.py` (new class `TestEngineRateLines`), `test_demographics_harness.py` (the medicine scenarios, new augmentation rows included, stay in band)

**Interfaces:**
- Produces:
  - `DM.engine_rate_lines(root=ROOT, mod=True) -> dict[tuple[str, str, str, str], float]`: (kind, key, block, field) → the net value the engine applies, vanilla's and (with `mod`) the mod's lines summed per entity as the engine sums an INJECT. `mod=False` gives vanilla's alone (Task 10 reports what absorbing them costs).
  - `P.ENGINE_LINES_ON_TOP: frozenset[str]`: the carriers whose birth or mortality lines stay on top.

- [ ] **Step 1: Write the failing tests**

`test_demographics_modifiers.py`:

```python
RATE_FIELDS = re.compile(r"^state_(birth_rate|mortality|mortality_wealth|\w+_mortality)_mult$")


class TestEngineRateLines(unittest.TestCase):
    """Phase 2 step 4: every birth or mortality line a law, technology or institution carries either nets to
    nothing (absorbed by the census: §8.4, the inverse INJECTs) or belongs to a carrier added on top."""

    @classmethod
    def setUpClass(cls):
        cls.lines = DM.engine_rate_lines()
        cls.vanilla = DM.engine_rate_lines(mod=False)

    def test_every_line_is_absorbed_or_on_top(self):
        # the census's own script-only types (state_work_mortality_mult and the like) are inputs, not engine lines
        live = {k: v for k, v in self.lines.items()
                if abs(v) > 1e-9 and RATE_FIELDS.match(k[3]) and k[3] not in P.DEMOG_TYPES}
        unexpected = sorted(k for k in live if k[1] not in P.ENGINE_LINES_ON_TOP)
        self.assertEqual(unexpected, [], "a birth or mortality line the census neither absorbs nor adds on top")

    def test_the_vanilla_lines_the_census_absorbs_net_to_zero(self):
        for law, block, field in (("law_charitable_health_system", "institution_modifier", "state_mortality_mult"),
                                  ("law_public_health_insurance", "institution_modifier", "state_mortality_mult"),
                                  ("law_private_health_insurance", "institution_modifier", "state_mortality_wealth_mult"),
                                  ("law_child_labor_allowed", "modifier", "state_laborers_mortality_mult"),
                                  ("law_child_labor_allowed", "modifier", "state_machinists_mortality_mult"),
                                  ("law_child_labor_allowed", "modifier", "state_farmers_mortality_mult"),
                                  ("law_child_labor_allowed", "modifier", "state_peasants_mortality_mult"),
                                  ("law_restricted_child_labor", "modifier", "state_laborers_mortality_mult"),
                                  ("law_restricted_child_labor", "modifier", "state_farmers_mortality_mult"),
                                  ("law_restricted_child_labor", "modifier", "state_peasants_mortality_mult")):
            self.assertNotEqual(self.vanilla.get(("law", law, block, field), 0.0), 0.0, msg=(law, field))
            self.assertAlmostEqual(self.lines.get(("law", law, block, field), 0.0), 0.0, msg=(law, field))

    def test_the_on_top_carriers_exist(self):
        carriers = {k[1] for k in self.lines}
        self.assertEqual(sorted(P.ENGINE_LINES_ON_TOP - carriers), [])

    def test_augmentation_moves_to_flat_chronic_treatment(self):
        """The design note's values as totals: flat lines (kind 'law'), not per level (an institution_modifier
        line at +0.10 would give +0.50 at level 5)."""
        chronic = {(c.key, c.kind): c.value for c in DM.load_carriers() if c.type == "state_chronic_treatment_add"}
        self.assertEqual(chronic.get(("law_medical_augmentation_only", "law")), 0.10)
        self.assertEqual(chronic.get(("law_unrestricted_augmentation", "law")), 0.05)
        self.assertEqual(chronic.get(("law_regulated_augmentation_market", "law")), 0.05)
        self.assertEqual(chronic.get(("law_mandatory_augmentation", "law")), 0.05)   # owner, 2026-10-10
        self.assertFalse(any(kind == "law_institution" and "augmentation" in key for key, kind in chronic))
        self.assertEqual(P.TREATMENT_CAP["chronic"], 0.85)
```

In `demographics_harness.py`, add to `MEDICINE_GAPS` (after the Public Health Insurance row). `RICH_TODAY` is the "Rich today" scenario's inputs, lifted to a constant that both lists use:

```python
    # Augmentation as chronic treatment (phase 2 step 4). The old engine lines on Rich today's inputs: Medical
    # Only's -2% a level at Ministry of Health level 8 gave about +2.8 years, Unrestricted's flat -5% about +0.8,
    # Regulated Market's -2% a level at Consumer Protection level 4 about +1.4 (model, every cause scaled). The
    # bands keep the new lines near those sizes and catch a per-level line (+0.10 a level is +14 years).
    ("Medical Augmentation Only, Rich today", dict(RICH_TODAY, laws=RICH_TODAY["laws"] | {"law_medical_augmentation_only"}),
     RICH_TODAY, (1.5, 3.5)),
    ("Unrestricted Augmentation, Rich today", dict(RICH_TODAY, laws=RICH_TODAY["laws"] | {"law_unrestricted_augmentation"}),
     RICH_TODAY, (0.5, 2.0)),
    ("Regulated Augmentation Market, Rich today",
     dict(RICH_TODAY, laws=RICH_TODAY["laws"] | {"law_regulated_augmentation_market"}), RICH_TODAY, (0.5, 2.0)),
```

Measured with the model on 2026-10-10 (Rich today's inputs, chronic cap 0.85): +0.05 chronic treatment gives +1.1 years of life expectancy, +0.10 gives +2.4, +0.50 gives +14.5. `test_medicine_anchors_hold` runs these rows.

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_modifiers.TestEngineRateLines test_demographics_harness.TestHarness.test_medicine_anchors_hold`

Expected: FAIL. `AttributeError: module 'demographics_modifiers' has no attribute 'engine_rate_lines'`; the augmentation rows read a gain of 0.

- [ ] **Step 3: The table and the reader**

In `demographics_params.py`:

```python
# Phase 2 step 4 (plan §3 (a)): carriers whose birth or mortality lines stay on top of the census's term.
# Every other law, technology or institution line nets to zero (Tasks 6 and 8). The women's-rights laws leave
# this list in Task 8, once Task 7's natural-fertility term carries their effect.
ENGINE_LINES_ON_TOP = frozenset({
    # women's rights: on top until the census's term exists (owner, 2026-10-10)
    "law_no_womens_rights", "law_women_in_the_fields", "law_women_in_the_workplace", "law_womens_suffrage",
    "law_protected_class",
    # the family-policy laws §8.1 has yet to re-express as census terms
    "law_pro_natalist_subsidies", "law_population_control_measures", "law_communal_child_rearing",
    # late-era lines with no census term; revisit with step 6
    "law_legal_limbo", "law_basic_protections", "law_comprehensive_rights", "law_full_equality_and_protection",
    "law_state_eugenics_program", "second_wave_feminism", "sexual_revolution", "mental_health_awareness",
    "biological_immortality", "mind_backups",
})
```

The test's `RATE_FIELDS` doesn't match `state_mortality_turmoil_mult` (Militarized Police, on top by construction). The decree and the static modifiers aren't laws, techs or institutions, so the test doesn't see them.

In `demographics_modifiers.py`. ModState's parser keeps the last of two scalar keys, where the engine sums an INJECT, so read vanilla and the mod apart:

```python
def engine_rate_lines(root=ROOT, mod=True):
    """{(kind, key, block, field): net value} for every `*_mult` line in a law's `modifier` or
    `institution_modifier`, a technology's or an institution's `modifier`. Vanilla's and (with mod) the
    mod's are summed as the engine sums an INJECT (scripting_best_practices.md § INJECT); a mod REPLACE
    drops vanilla's. kind: law, technology, institution."""
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
        if not mod:
            continue
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

Add one header line: "state_mortality_mult / state_mortality_wealth_mult: vanilla's lines cancelled; the census's access × treatment absorbs them (demographics phase 2 step 4)". These are the same three blocks that already cancel vanilla's `state_pollution_reduction_health_mult` (drugs phase 2), so the cancel shape is live on these exact entities (E13).

In `te_demog_law_injections.txt`:

```
INJECT:law_child_labor_allowed = {
	modifier = {
		state_work_mortality_mult = 0.1
		# vanilla's class lines cancelled: the census's work term absorbs them (owner, 2026-10-10: vanilla's
		# lines are probably far too high; the census's term, about a twenty-fifth of them, is the intended size)
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
```

The first block is the existing one with four lines added. Several INJECT blocks on one law in different files all apply (E13), so a second file's block would also work. The lines go here because this file holds the census's own child-labour line.

- [ ] **Step 5: §8.4's removals and augmentation's chronic lines**

Delete these lines (each with its comment, if it has one of its own):
- `extra_laws.txt:2708` (State-Sponsored Family Planning's `state_birth_rate_mult`; its Fertility Control +0.1 stays);
- `era_6.txt:430-431` (`modern_vaccines`) and `era_7.txt:485-486` (`antibiotic_mass_production`): `state_mortality_mult` and `state_birth_rate_mult`;
- `era_7.txt:505` (`contraceptive_pill`);
- `extra_institutions.txt:159` (Consumer Protection).

These keep their lines (`ENGINE_LINES_ON_TOP`):
- Pro-Natalist Subsidies, Population Control Measures and Communal Child Rearing, until §8.1 gives them census terms;
- the women's-rights laws, until Task 8.

**The augmentation laws** (`extra_laws.txt:1669` ff.):
- **Remove** each law's `state_mortality_mult`:
  - Unrestricted's is a flat −0.05 in `modifier`.
  - Medical Only's, Regulated Market's and Mandatory's are −0.02 a level in `institution_modifier`.
- **Add** to each law's `modifier` block (create the block where a law has none) a flat `state_chronic_treatment_add`:
  - Medical Only +0.10;
  - Unrestricted and Regulated Market +0.05;
  - Mandatory +0.05, the owner's to confirm.
- **Why flat:** these are the design note's starting values read as totals.
  - Per level, Medical Only's +0.10 would reach +0.50 at Ministry of Health level 5. Chronic treatment would then be at its cap, and the census's best choice "without anyone deciding so" (the note's own warning).
  - The flat values put each law near its old lines' effect on Rich today's inputs (Step 1's scenario rows).
  - Chronic treatment still reaches only as far as access does, so a country with no health system gets little from it.
- **The cap:** set `TREATMENT_CAP["chronic"] = 0.85` in `demographics_params.py` and regenerate (`gen_demographics.py`).

Before deleting, re-read each line number against the file (`sed -n '<n>p'`). The numbers were checked against `main` ee3e29d6.

**Prose that states the removed figures** (memory: loc promises the code doesn't deliver):
- `LAW_MEDICAL_AUGMENTATION_ONLY_INSTITUTION_MODIFIER_TT`, `LAW_REGULATED_AUGMENTATION_MARKET_INSTITUTION_MODIFIER_TT` and `LAW_MANDATORY_AUGMENTATION_INSTITUTION_MODIFIER_TT` (`te_miscellaneous_l_english.yml:460-465`) each list `#g -2%#! $state_mortality_mult$` a level. Delete that line from each: the chronic-treatment line now sits in the law's own modifiers, which the law's tooltip lists.
- Then sweep for the rest:

```bash
git grep -n -i "birth\|mortality" -- localization/english/ | grep -i "pill\|family_planning\|vaccine\|antibiotic_mass\|consumer_protection\|augmentation\|health_system\|health_insurance\|child_labor"
grep -n -i "pill\|family planning\|vaccin\|antibiotic\|consumer protection\|health insurance\|child labo" docs/player_guide/*.md | grep -i "birth\|mortal\|death\|%"
```

- Every hit that states an absorbed line is fixed in this task. 2026-10-10's sweep found only the three tooltips, plus two player-guide lines that stay true:
  - `06-politics.md:25`: the family-policy laws move birth rates. They still do: three keep their lines, and State-Sponsored Family Planning works through Fertility Control.
  - `06-politics.md:428`: Consumer Protection lowers mortality. It still does, through the census's external causes.

- [ ] **Step 6: Run the carriers, medicine and fertility checks**

Run:
```bash
.venv/bin/python -m unittest test_demographics_modifiers test_demographics_model test_gen_demographics test_demographics_registry test_demographics_harness
.venv/bin/python scripts/analysis/demographics_harness.py medicine
.venv/bin/python scripts/analysis/demographics_harness.py fertility
```
Expected:
- The tests pass.
- `medicine` and `fertility` exit 0: every scenario, the augmentation rows included, is in band.
- If a scenario leaves its band, report the figures and stop for the owner; don't retune here.

- [ ] **Step 7: Commit**

```bash
git add common/laws/modified_health_system.txt common/laws/te_demog_law_injections.txt common/laws/extra_laws.txt common/technology/technologies/era_6.txt common/technology/technologies/era_7.txt common/institutions/extra_institutions.txt localization/english/te_miscellaneous_l_english.yml common/script_values/te_demog_generated_values.txt scripts/analysis/demographics_params.py scripts/analysis/demographics_modifiers.py scripts/analysis/demographics_harness.py test_demographics_modifiers.py test_demographics_harness.py
git commit -m "Demographics phase 2 step 4: the census absorbs the health, child-labour and spec 8.4 lines; augmentation as chronic treatment"
```

---

### Task 7: The census's women's-rights fertility term

The census gets a term of the vanilla lines' size before Task 8 absorbs them (owner, 2026-10-10). Its size is owner call (d) (§3), decided: the recommendation.

**Files:**
- Modify: `common/modifier_type_definitions/demographics_modifier_types.txt` (`state_natural_fertility_mult`)
- Modify: `localization/english/te_modifiers_l_english.yml` (its name and description)
- Modify: `common/laws/extra_laws.txt`:
  - the carriers' lines, inside the existing women's-rights INJECT blocks at `extra_laws.txt:78-98`;
  - a new block for `law_women_own_property`, which today is "deliberate neutral";
  - Protected Class's own `modifier`.
- Modify: `common/script_values/te_demog_values.txt` (`te_demog_tfr` takes the term; a named `te_demog_tfr_natural` for the tooltips)
- Modify: `scripts/analysis/demographics_params.py`, `scripts/analysis/demographics_model.py`, `scripts/generators/gen_demographics.py` (the floor constant), `scripts/analysis/demographics_harness.py` (the fertility scenarios)
- Test: `test_demographics_model.py`, `test_demographics_registry.py` (new class `TestNaturalFertilityScript`; `TestModifierTypes`), `test_demographics_modifiers.py`, `test_demographics_harness.py`

**Interfaces:**
- Produces:
  - `P.NATURAL_FERTILITY_TYPE = "state_natural_fertility_mult"`, `P.NATURAL_FERTILITY_FLOOR = 0.2`, `P.NATURAL_FERTILITY_BY_LAW` (the carriers' values: the owner's ruling on (d));
  - `M.fertility(inp, e0)["natural"]`, with `tfr = wealth × natural × factor`;
  - the generated constant `te_demog_k_natural_fertility_floor`.

- [ ] **Step 1: Write the failing tests**

`test_demographics_model.py`:

```python
class TestNaturalFertility(unittest.TestCase):
    """The women's-rights term (phase 2 step 4, Task 7): natural fertility before the means."""

    def test_it_scales_children_per_woman_before_the_means(self):
        base = M.Inputs(sol=9.0, literacy=0.3)
        lower = M.Inputs(sol=9.0, literacy=0.3, mods={P.NATURAL_FERTILITY_TYPE: -0.1})
        a, b = M.fertility(base, 35.0), M.fertility(lower, 35.0)
        self.assertAlmostEqual(b["tfr"], a["tfr"] * 0.9)
        self.assertAlmostEqual(b["natural"], 0.9)
        self.assertEqual((a["means"], a["factor"]), (b["means"], b["factor"]))

    def test_it_is_floored(self):
        inp = M.Inputs(sol=9.0, mods={P.NATURAL_FERTILITY_TYPE: -5.0})
        self.assertEqual(M.fertility(inp, 35.0)["natural"], P.NATURAL_FERTILITY_FLOOR)

    def test_no_womens_rights_is_the_reference(self):
        """Re-centred on No Women's Rights, where 83% of the 1837 world sat, so step 2's fit is unchanged."""
        self.assertEqual(P.NATURAL_FERTILITY_BY_LAW.get("law_no_womens_rights", 0.0), 0.0)
```

`test_demographics_registry.py`:

```python
class TestNaturalFertilityScript(unittest.TestCase):
    """te_demog_tfr with the natural-fertility read, against demographics_model.fertility."""

    def test_script_matches_the_model(self):
        for natural in (-5.0, -0.15, 0.0, 0.1):
            inp = demographics_model.Inputs(sol=9.0, literacy=0.3, urban_share=0.2,
                                            mods={P.NATURAL_FERTILITY_TYPE: natural})
            fert = demographics_model.fertility(inp, 35.0)
            eng = _Engine({f"modifier:{P.NATURAL_FERTILITY_TYPE}": natural})
            eng.vars.update(te_dg_wtfr=fert["wealth"], te_dg_means=fert["means"],
                            te_dg_desired=fert["education"] * fert["survival"] * fert["urban"])
            with self.subTest(natural=natural):
                self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_tfr")), fert["tfr"], places=9)
```

Add `P.NATURAL_FERTILITY_TYPE` to the types `TestModifierTypes.test_fertility_types_are_registered_named_and_new` expects.

`test_demographics_modifiers.py`:

```python
    def test_womens_rights_carry_the_natural_fertility_term(self):
        lines = {c.key: c.value for c in DM.load_carriers() if c.type == P.NATURAL_FERTILITY_TYPE}
        self.assertEqual(lines, {k: v for k, v in P.NATURAL_FERTILITY_BY_LAW.items() if v})
```

`demographics_harness.py`, new rows in `FERTILITY_SCENARIOS` (the existing rows stay as they are). Each row is a Western scenario with the women's-rights law its countries held; the bands are Gapminder's Western range that year (`fetch_history_anchors.py`'s `tfr` measure; anchors file 2026-10-10):
- 1900: UK 3.53, France 2.80 … Germany 4.93;
- 1950: Austria 1.87, UK and Germany 2.08 … Netherlands 3.10;
- 1990: Italy 1.30 … Sweden 2.14.

```python
    ("1836 agrarian, No Women's Rights", dict(sol=8, literacy=0.2, urban_share=0.1,
                                              laws={"law_no_womens_rights"}), (4.8, 6.2)),
    ("Britain 1900, Women Own Property", dict(sol=16, literacy=0.75, urban_share=0.6, techs=MED_1900 | MEANS_TECHS,
                                              laws={CHS, "law_women_own_property"}, institutions={HEALTH: 4}),
     (2.8, 4.9)),
    ("West 1950, Women's Suffrage", dict(sol=25, literacy=0.95, urban_share=0.65, techs=MED_1950 | MEANS_TECHS,
                                         laws={PHI, "law_womens_suffrage"}, institutions={HEALTH: 5}), (1.9, 3.1)),
    ("West 1990, Women's Suffrage", dict(sol=38, literacy=0.98, urban_share=0.75,
                                         techs=MED_1990 | MEANS_TECHS | {"contraceptive_pill"},
                                         laws={PHI, "law_womens_suffrage"}, institutions={HEALTH: 6}), (1.3, 2.2)),
```

And in `test_demographics_harness.py`:

```python
    def test_no_womens_rights_leaves_the_reference_alone(self):
        rows = {r[0]: r[1] for r in H.fertility_rows()}
        self.assertAlmostEqual(rows["1836 agrarian, No Women's Rights"], rows["1836 agrarian (reference)"], places=9)
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_model.TestNaturalFertility test_demographics_registry.TestNaturalFertilityScript test_demographics_modifiers test_demographics_harness`
Expected: FAIL, `AttributeError: … has no attribute 'NATURAL_FERTILITY_TYPE'`.

- [ ] **Step 3: The parameters, the type and the model**

`demographics_params.py`, after `MEANS_SHIFT_TYPE`:

```python
# Natural fertility (phase 2 step 4, Task 7): women's legal status before modern contraception, through who
# marries and when. Multiplies the wealth term before the means. Its carriers are the women's-rights laws,
# re-centred on No Women's Rights so step 2's fit (83% of the 1837 world) is unchanged (owner call (d), 2026-10-10).
NATURAL_FERTILITY_TYPE = "state_natural_fertility_mult"
NATURAL_FERTILITY_FLOOR = 0.2
NATURAL_FERTILITY_BY_LAW = {
    "law_no_womens_rights": 0.0, "law_women_in_the_fields": -0.15, "law_women_own_property": -0.05,
    "law_women_in_the_workplace": -0.10, "law_womens_suffrage": -0.10, "law_protected_class": -0.15,
}
DEMOG_FERTILITY_TYPES = (CONTRACEPTION_TYPE, MEANS_SHIFT_TYPE, NATURAL_FERTILITY_TYPE)
```

(Replace the existing `DEMOG_FERTILITY_TYPES` line.) `demographics_model.fertility`:

```python
    natural = max(P.NATURAL_FERTILITY_FLOOR, 1 + inp.mods.get(P.NATURAL_FERTILITY_TYPE, 0.0))
    ...
    return {"tfr": wealth * natural * factor, "wealth": wealth, "natural": natural, "education": education,
            "survival": survival, "urban": urban, "means": mn, "factor": factor}
```

In `gen_demographics.constants`, add `"natural_fertility_floor": P.NATURAL_FERTILITY_FLOOR`, then regenerate.

The type (`demographics_modifier_types.txt`, with the fertility types):

```
state_natural_fertility_mult = {
	color = neutral
	percent = yes
	decimals = 0
	script_only = yes
}
```

Loc (`te_modifiers_l_english.yml`, beside `state_fertility_means_add`):

```yaml
 state_natural_fertility_mult:0 "Natural Fertility"
 state_natural_fertility_mult_desc:0 "How many children women have before any family planning, through who marries and how young. Women's legal standing moves it: where they can own property, work and vote, marriage comes later. Read by the Demographics census."
```

- [ ] **Step 4: The census reads it** (`te_demog_values.txt`)

Beside the other named terms:

```
# Natural fertility, from women's legal standing (state_natural_fertility_mult on the women's-rights laws;
# phase 2 step 4): 1 + the read, at least the floor.
te_demog_tfr_natural = {
	value = modifier:state_natural_fertility_mult
	add = 1
	min = te_demog_k_natural_fertility_floor
}
```

`te_demog_tfr` gains one line after `multiply = var:te_dg_wtfr`: `multiply = te_demog_tfr_natural`. Update its comment: "children per woman = wealth × natural × (1 − means × (1 − desired))".

Two loc keys in `te_miscellaneous_l_english.yml` list the terms of children per woman: `te_demog_ov_tfr_capital` (the capital's, on the Population panel's tab) and `te_demog_st_tfr_terms` (a state's). Each gets a "Women's legal standing" line reading `te_demog_tfr_natural` (`ScriptValue('te_demog_tfr_natural')`), written the way their education line is.

- [ ] **Step 5: The carriers** (`extra_laws.txt`)

Add to the existing women's-rights INJECT blocks (lines 78–98):
- `law_womens_suffrage`: `state_natural_fertility_mult = -0.1`;
- `law_women_in_the_workplace`: `state_natural_fertility_mult = -0.1`;
- `law_women_in_the_fields`: `state_natural_fertility_mult = -0.15`.

`extra_laws.txt:88`'s comment, `# law_women_own_property: deliberate neutral (no modifier)`, records a decision about cultural pull. The census's natural fertility is a separate axis, and on vanilla's own ladder Own Property sits 0.05 below No Women's Rights, which is where the re-centred term puts it. So reword the comment and add a block after it:

```
# law_women_own_property: neutral for cultural pull; the census's natural fertility is a separate axis
INJECT:law_women_own_property = {
	modifier = {
		state_natural_fertility_mult = -0.05	# the census's natural fertility (demographics phase 2 step 4)
	}
}
```

- **Cultural pull:** Women Own Property stays neutral, since the block carries no cultural-pull line.
- **Protected Class:** add `state_natural_fertility_mult = -0.15` to its own `modifier`.
- **No Women's Rights** carries none.
- **The values:** from `P.NATURAL_FERTILITY_BY_LAW`, which the carriers test holds them to.

- [ ] **Step 6: Run the tests and the anchors**

Run:
```bash
.venv/bin/python -m unittest test_demographics_model test_demographics_registry test_demographics_modifiers test_demographics_harness test_gen_demographics
.venv/bin/python scripts/analysis/demographics_harness.py fertility
.venv/bin/python loc_coverage_audit.py --strict
```
Expected:
- All pass, and `fertility` exits 0.
- At the recommended sizes, measured 2026-10-10:
  - Britain 1900 with Women Own Property: 3.66 (Gapminder UK 3.53);
  - West 1950 with Suffrage: 2.29;
  - West 1990 with Suffrage: 1.43.
- The original rows are unchanged.

- [ ] **Step 7: Commit**

```bash
git add common/modifier_type_definitions/demographics_modifier_types.txt localization/english/ common/laws/extra_laws.txt common/script_values/te_demog_values.txt common/script_values/te_demog_generated_values.txt scripts/analysis/demographics_params.py scripts/analysis/demographics_model.py scripts/generators/gen_demographics.py scripts/analysis/demographics_harness.py test_demographics_model.py test_demographics_registry.py test_demographics_modifiers.py test_demographics_harness.py
git commit -m "Demographics phase 2 step 4: a natural-fertility term on the women's-rights laws, read by the census"
```


---

### Task 8: The census absorbs the women's-rights birth lines

Only after Task 7: the census's term now carries what the lines did.

**Files:**
- Modify: `common/laws/extra_laws.txt` (vanilla's four birth lines cancelled inside the same INJECT blocks; Protected Class's own `state_birth_rate_mult` removed)
- Modify: `scripts/analysis/demographics_params.py` (the women's-rights laws leave `ENGINE_LINES_ON_TOP`)
- Test: `test_demographics_modifiers.py`

- [ ] **Step 1: Write the failing test** (in `TestEngineRateLines`)

```python
    def test_womens_rights_birth_lines_are_absorbed(self):
        """Task 8: vanilla's women's-rights birth lines (and Protected Class's) net to zero, now that the census's
        natural-fertility term carries them (Task 7)."""
        for law in ("law_no_womens_rights", "law_women_in_the_fields", "law_women_in_the_workplace",
                    "law_womens_suffrage", "law_protected_class"):
            self.assertAlmostEqual(self.lines.get(("law", law, "modifier", "state_birth_rate_mult"), 0.0), 0.0, msg=law)
            self.assertNotIn(law, P.ENGINE_LINES_ON_TOP)
```

- [ ] **Step 2: Run it to see it fail**

Run: `.venv/bin/python -m unittest test_demographics_modifiers.TestEngineRateLines`
Expected: FAIL on `law_no_womens_rights` (0.05 ≠ 0).

- [ ] **Step 3: Implement**

In the INJECT blocks at `extra_laws.txt:78-98`, beside Task 7's lines:
- `law_no_womens_rights`: `state_birth_rate_mult = -0.05`;
- `law_women_in_the_fields`: `state_birth_rate_mult = 0.1`;
- `law_women_in_the_workplace`: `state_birth_rate_mult = 0.05`;
- `law_womens_suffrage`: `state_birth_rate_mult = 0.05`.

Each carries the comment "vanilla's birth line cancelled: the census's natural fertility absorbs it (demographics phase 2 step 4)".

- **Women in the Fields** is a variant of No Women's Rights with its own `modifier`, so it takes its own cancel. P2 confirms in game that its block nets to nothing.
- **Protected Class:** delete its `state_birth_rate_mult = -0.1` (`extra_laws.txt:4138` at ee3e29d6).
- **The list:** remove the five laws from `ENGINE_LINES_ON_TOP`.

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m unittest test_demographics_modifiers test_demographics_harness`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add common/laws/extra_laws.txt scripts/analysis/demographics_params.py test_demographics_modifiers.py
git commit -m "Demographics phase 2 step 4: the census absorbs the women's-rights birth lines"
```

---

### Task 9: The census line and the observer report's phase-2 check

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
    """The calibration plan's in-game gate for phase 2 (plan 2026-10-10 engine rates, Task 12):
    the world's people from the first census year to `to_year` (within x1.3-x1.7), countries of `big`
    people or more that lost people `run` census years running with no war year among them, and the
    share of the world's people in clamped states (above 1%, the clamp is holding M back: the results doc
    names where)."""
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

Add `--phase2` to `main`. It prints the multiple and its verdict, each shrinking run, and the clamped share, flagged above 1%. It exits 1 on a failed gate.

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

### Task 10: The harness predicts the engine's growth from a save (`predict`)

Uses #857's `state_inputs`, `save_year` and timed-modifier reader.

**Files:**
- Modify: `scripts/analysis/demographics_save_inputs.py` (pops' `food_security` value; states' `devastation`)
- Modify: `scripts/analysis/demographics_modifiers.py` (`engine_line_totals`)
- Modify: `scripts/analysis/demographics_harness.py` (`Pop`, `predict_state`, `predicted_multiple`, `cmd_predict`)
- Test: `test_demographics_save_inputs.py`, `test_demographics_modifiers.py`, `test_demographics_harness.py`
- Docs: `docs/guides/python_tools.md` (the command)

**Interfaces:**
- Consumes:
  - from Task 2: `M.rate_term`, `M.starvation_terms`, `M.model_crude_rates`, `P.LITERACY_BIRTH_PENALTY`;
  - from Task 6: `DM.engine_rate_lines(mod=…)`;
  - from `pop_growth`: `monthly_birthrate`, `monthly_mortality`, `read_defines`.
- Produces:
  - `Pop(size, sol, literacy, food_security, on_top_d=0.0, absorbed_d=0.0)`, a namedtuple:
    - `on_top_d` is the pop's class line still on top;
    - `absorbed_d` is vanilla's class line the census absorbed (child labour), carried only for the report.
  - `DM.engine_line_totals(lines, laws, techs) -> dict[str, float]`: the flat `modifier` lines of a country's laws and techs, by field.
  - `predict_state(pops, cbr, cdr, d, on_top_b=0.0, on_top_d=0.0) -> dict`. Its keys: `people`, `births`, `deaths`, `target_births`, `target_deaths`, `on_top_births`, `on_top_deaths`, `m_b`, `m_d`, `clamped`, `slope_deaths`, `absorbed_child_labour_deaths`.
  - `predicted_multiple(points, to_year) -> float`.
  - CLI: `demographics_harness.py predict SAVE... [--census-rates] [--slope] [--to-year 1900] [--check-modifiers] [--json]`.

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

`SAVE_HEAD` and `read` stand for the module's existing fixture helpers (the plain-text header and a temp-file read); use whatever names it has.

`test_demographics_modifiers.py`:

```python
    def test_line_totals_take_a_countrys_flat_lines(self):
        lines = {("law", "law_a", "modifier", "state_birth_rate_mult"): 0.05,
                 ("law", "law_b", "modifier", "state_birth_rate_mult"): -0.1,
                 ("technology", "tech_a", "modifier", "state_mortality_mult"): -0.05,
                 ("law", "law_a", "institution_modifier", "state_mortality_mult"): 0.5}   # per level: left out
        self.assertEqual(DM.engine_line_totals(lines, laws={"law_a"}, techs={"tech_a"}),
                         {"state_birth_rate_mult": 0.05, "state_mortality_mult": -0.05})
```

`test_demographics_harness.py`:

```python
class TestPredict(unittest.TestCase):
    D = H.G.read_defines()

    def test_a_fed_state_runs_at_the_census_rates_plus_nothing(self):
        out = H.predict_state([H.Pop(1e6, 9.0, 0.0, 0.8)], cbr=40.0, cdr=30.0, d=self.D)
        self.assertAlmostEqual(out["births"] / 1e3, 40.0, places=6)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0, places=6)

    def test_literacy_is_netted(self):
        out = H.predict_state([H.Pop(1e6, 9.0, 0.5, 0.8)], cbr=40.0, cdr=30.0, d=self.D)
        self.assertAlmostEqual(out["births"] / 1e3, 40.0, places=6)

    def test_terms_on_top_add_at_the_bare_curves_weight(self):
        # severe starvation (births -0.9, deaths +1.0), devastation 0.2 and a law's -0.1 births, all on top
        out = H.predict_state([H.Pop(1e6, 9.0, 0.0, 0.1)], cbr=40.0, cdr=30.0, d=self.D, on_top_b=-0.1, on_top_d=0.2)
        bare_b = 1e6 * H.G.monthly_birthrate(9.0, self.D) * 12
        bare_d = 1e6 * H.G.monthly_mortality(9.0, self.D) * 12
        self.assertAlmostEqual(out["deaths"], 30.0 * 1e3 + bare_d * (1.0 + 0.2), delta=1.0)
        self.assertAlmostEqual(out["births"], max(0.0, 40.0 * 1e3 + bare_b * (-0.9 - 0.1)), delta=1.0)

    def test_the_slope_is_reported_not_applied(self):
        pops = [H.Pop(1e6, 1.0, 0.0, 0.8)]
        out = H.predict_state(pops, 40.0, 30.0, self.D)
        slope = 1e6 * (H.G.monthly_mortality(1.0, self.D) - H.G.monthly_mortality(4.0, self.D)) * 12
        self.assertAlmostEqual(out["slope_deaths"], slope, delta=1.0)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0, places=6)

    def test_absorbed_child_labour_is_reported_not_applied(self):
        pops = [H.Pop(1e6, 9.0, 0.0, 0.8, on_top_d=0.0, absorbed_d=0.05)]
        out = H.predict_state(pops, 40.0, 30.0, self.D)
        self.assertAlmostEqual(out["absorbed_child_labour_deaths"],
                               1e6 * H.G.monthly_mortality(9.0, self.D) * 12 * 0.05, delta=1.0)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0, places=6)

    def test_multiple_chains_the_saves_rates(self):
        # 1% a year from 1837 to 1887, then 0.5% to 1900
        self.assertAlmostEqual(H.predicted_multiple([(1837, 1.0), (1887, 0.5)], 1900),
                               math.exp(0.01 * 50 + 0.005 * 13), places=9)
```

The second case of the third test floors births at 0 (severe starvation and the law sum to −1.0 on top of M). If `max(0.0, …)` there reads as a test fitted to the code, replace the law's −0.1 with 0 and assert the unfloored figure. Keep the devastation half either way.

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_save_inputs test_demographics_modifiers test_demographics_harness.TestPredict`
Expected: FAIL: no `food_security` key, no `engine_line_totals`, no `Pop`.

- [ ] **Step 3: The reader**

In `demographics_save_inputs.py`:
- Add `"devastation"` to `SECTIONS["states"]`.
- For pops, track the nested block: at depth 3, `line.startswith("\tfood_security={")` sets `in_food = True`.
- At depth 4 with `in_food`, `^\t\tvalue=([-0-9.]+)$` stores `record["food_security"]`.
- `in_food` clears when the depth returns to 3. Write it beside #857's `in_timed` tracking, which has the same shape.

- [ ] **Step 4: The prediction**

In `demographics_modifiers.py`:

```python
def engine_line_totals(lines, laws=(), techs=()):
    """{field: total} of the flat `modifier` lines (engine_rate_lines' keys) a country's laws and techs carry.
    Per-level law lines are left out: after phase 2 step 4 none of the birth or mortality ones is live
    (the health laws' are absorbed), and predict says so if one ever is."""
    laws, techs = set(laws), set(techs)
    out = {}
    for (kind, key, block, field), value in lines.items():
        if block == "modifier" and ((kind == "law" and key in laws) or (kind == "technology" and key in techs)):
            out[field] = out.get(field, 0.0) + value
    return {k: v for k, v in out.items() if v}
```

In `demographics_harness.py`:

```python
Pop = collections.namedtuple(  # import collections at the top of the module
    "Pop", "size sol literacy food_security on_top_d absorbed_d", defaults=(0.0, 0.0))


def predict_state(pops, cbr, cdr, d, on_top_b=0.0, on_top_d=0.0):
    """The engine's births and deaths a year in one state once the census sets them (phase 2 step 4, plan §2).

    pops: [Pop]; cbr, cdr: the census's own rates per 1,000 a year; on_top_b, on_top_d: the state-level terms
    on top (its owner's law and tech lines, devastation's +1.0 x share pending probe P1). Each pop gets
    bare x max(0, 1 + M + its terms): literacy's -0.1 (absorbed, netted in M), starvation (on top, from its food
    security), its class line still on top. Terms on top a save doesn't hold are left out: pollution, turmoil,
    events, low_pop_state, unemployment, workplace mortality (about +2% of deaths in 1949, growth probe).
    Reported, not applied: the starving slope below SoL 4 (absorbed: owner, 2026-10-10) and vanilla's
    child-labour class lines (absorbed: owner, 2026-10-10), so the gate shows what absorbing them does."""
    people = sum(p.size for p in pops)
    bare_b = sum(p.size * G.monthly_birthrate(p.sol, d) for p in pops) * 12
    bare_d = sum(p.size * G.monthly_mortality(p.sol, d) for p in pops) * 12
    lit_b = sum(p.size * G.monthly_birthrate(p.sol, d) * p.literacy for p in pops) * 12
    slope = sum(p.size * (G.monthly_mortality(p.sol, d) - G.monthly_mortality(max(p.sol, d.equilibrium_sol), d))
                for p in pops) * 12
    child = sum(p.size * G.monthly_mortality(p.sol, d) * p.absorbed_d for p in pops) * 12
    target_b, target_d = cbr / 1000 * people, cdr / 1000 * people
    m_b, cb = M.rate_term(target_b, bare_b, absorbed=P.LITERACY_BIRTH_PENALTY * lit_b, other=on_top_b)
    m_d, cd = M.rate_term(target_d, bare_d, other=on_top_d)
    births = deaths = 0.0
    for p in pops:
        sb, sd = M.starvation_terms(p.food_security)
        births += p.size * G.monthly_birthrate(p.sol, d) * 12 * max(
            0.0, 1 + m_b + on_top_b + P.LITERACY_BIRTH_PENALTY * p.literacy + sb)
        deaths += p.size * G.monthly_mortality(p.sol, d) * 12 * max(0.0, 1 + m_d + on_top_d + p.on_top_d + sd)
    return {"people": people, "births": births, "deaths": deaths, "target_births": target_b,
            "target_deaths": target_d, "on_top_births": births - target_b, "on_top_deaths": deaths - target_d,
            "m_b": m_b, "m_d": m_d, "clamped": cb or cd, "slope_deaths": slope,
            "absorbed_child_labour_deaths": child}


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
1. **Read** `S.read_sections(path)` and `save_year`, plus `S.read_variables(path, (), ("te_dg_cbr_model", "te_dg_cdr_model", "te_dg_cbr", "te_dg_cdr", "te_dg_mb", "te_dg_md"))`.
   - `lines = DM.engine_rate_lines()` for what the engine applies now; `vanilla = DM.engine_rate_lines(mod=False)` for what it did before the census absorbed it.
2. **Group the pops** by state. Each is a `Pop`:
   - `num_literate / size` as literacy, and `food_security`, or 1.0 when absent;
   - `on_top_d` = the owner's net `state_<type>_mortality_mult` for the pop's type, from `engine_line_totals(lines, …)`;
   - `absorbed_d` = vanilla's `state_<type>_mortality_mult` on the owner's child-labour law, from `engine_line_totals(vanilla, …)` filtered to the two child-labour laws.
3. **Take each state's census rates from the current model:** `M.model_crude_rates(inputs_for(st, carriers, incorporated=inc))`, with #857's `state_inputs` (each state's own SoL, literacy, urban share, crowding and incorporation).
   - These are the stable-population rates of the model as it now stands. #857's `history` reasons from the same rates, so the two commands agree.
   - **Not the save's own census rates by default.** A save's `te_dg_cbr`/`te_dg_cdr` were written by the build that made it. The gate saves predate #855, so their rates are the old ×1.15-switch model without the poverty term, and the offline gate would run against stale calibration.
   - `--census-rates` reads the save's stored rates instead (`te_dg_cbr_model`/`te_dg_cdr_model`, else `te_dg_cbr`/`te_dg_cdr`), for a save from the build under test. It takes the ring's real age structure where the default takes the stable one.
4. **The state's terms on top:**
   - `on_top_b` = the owner's net `state_birth_rate_mult` (`engine_line_totals(lines, …)`);
   - `on_top_d` = its net `state_mortality_mult` + `devastation / 100`.
   - If `lines` holds a non-zero per-level (`institution_modifier`) birth or mortality line on any law, print it to stderr as unread.
5. **Sum by owner tag;** print the world line:
   - people;
   - the census's own growth, and the predicted growth;
   - the terms on top per 1,000;
   - the clamped share;
   - **"absorbing child labour's class lines: +X points of world growth a year"** (`absorbed_child_labour_deaths` over people). Owner, 2026-10-10: the gate run shows this.
6. **Print each country of 20M or more**, with the same figures. Flag those whose predicted growth is below 0.
7. **`--slope`** also prints the slope's cost per country (the reproducible version of §1's table).

After the loop:
- Print `predicted_multiple` from the saves' world growth to `--to-year`, with a ×1.3–×1.7 verdict.
- Exit 1 if the multiple is outside the band, or if any 20M+ country is predicted to shrink.

`--check-modifiers` (probe P4) lists states whose `te_dg_mb` or `te_dg_md` is not 0 but whose `timed_modifiers` hold no `te_demog_census_*` of the matching sign.

Register the subcommand beside `history`.

- [ ] **Step 5: Run the tests and the command on the gate saves**

Run:
```bash
.venv/bin/python -m unittest test_demographics_save_inputs test_demographics_modifiers test_demographics_harness
D=/mnt/d/vic3te-data/vic3te-demog-gate-data/saves
.venv/bin/python scripts/analysis/demographics_harness.py predict $D/autosave.1791572508.v3 $D/autosave.1791583167.v3 --slope
```
Expected:
- The tests pass.
- The command prints the slope's cost as §1's table has it: world 0.036 and 0.174 points, China 0.023 and 0.244, give or take rounding.
- It prints absorbing child labour as about +0.22 points of world growth in both saves (§1).

Record the prediction's world multiple in the results doc (Task 12).

- [ ] **Step 6: Document and commit**

Add a `predict` paragraph to `docs/guides/python_tools.md` beside `history`. It covers:
- what the command reads;
- what it leaves out: the terms on top a save doesn't hold;
- what it reports without applying: the slope, and child labour's absorbed lines;
- that it exits 1 on the gate.

```bash
git add scripts/analysis/demographics_save_inputs.py scripts/analysis/demographics_modifiers.py scripts/analysis/demographics_harness.py test_demographics_save_inputs.py test_demographics_modifiers.py test_demographics_harness.py docs/guides/python_tools.md
git commit -m "Demographics harness: predict, the engine's growth once the census sets it, from a save"
```

---

### Task 11: Docs and the player guide

**Files:**
- Modify: `docs/systems/mod_systems.md` § Demographics:
  - "Phase 1 applies nothing" becomes the phase-2 step 4 paragraph.
  - Add a subsection, "The census's births and deaths": the formula, the clamp, the refresh sites, fast mode, the lists of absorbed terms and of terms added on top (with the owner's rulings), the rule and old saves.
  - Add the release precondition to its "Not built yet" paragraph: "steps 4 and 5 ship together; no public release may contain step 4 alone (Display only and Disabled lose the absorbed lines until step 5's equilibrium rates)".
  - Update the file index.
- Modify: `docs/superpowers/specs/2026-10-08-demographics-design.md`:
  - §2.3's and §2.4's "Applied as": replace "the model's births ÷ the engine's births before the modifier − 1" with this plan's additive form, citing the growth probe.
  - §2.4: "multiply on top" becomes "add on top, at the bare curve's weight". Starvation's and the other terms' deaths fall by the model's age pattern (owner, 2026-10-10).
  - **§8.4,** where it conflicts with the owner's rulings:
    - The family-policy laws' birth lines come off only once §8.1 gives them census terms. State-Sponsored Family Planning's comes off now: Fertility Control carries it.
    - "Vanilla's modifiers stay as inputs" gains three exceptions:
      - the health laws' mortality, absorbed by access × treatment;
      - child labour's class lines, absorbed at the census's smaller work term (owner, 2026-10-10: vanilla's are probably far too high);
      - the women's-rights birth lines, absorbed once the census's natural-fertility term carries them.
    - The mod's women's-work lines stay inputs.
    - The augmentation laws become flat chronic-treatment lines.
    - Pro-Natalist's −0.05 working-adult goes with the workforce effects, not step 4.
  - §13: the shown TFR is the realized one.
  - §12's phase-2 row: step 4 built, with the release precondition.
- Modify: `docs/superpowers/specs/2026-10-09-demographics-modifier-types-design.md` § "Not decided here":
  - the augmentation laws: decided as flat lines at the note's values (Mandatory +0.05 pending the owner);
  - "Phase 2's double counting": decided (inverse INJECT).
- Modify: `docs/superpowers/plans/2026-10-10-demographics-phase2-calibration.md`:
  - step 4 points to this plan, with the owner's rulings ((b), (c), child labour, women's rights);
  - the release line ("tested before the next public release") gains "and steps 4 and 5 ship together".
- Modify: `docs/guides/vanilla_patch_runbook.md` § the values the mod copies or cancels: new rows for the three health laws, the two child-labour laws and the four women's-rights laws. Each row gives the vanilla `file:line`, the cancel's file, and the failure if vanilla changes.
- Modify: `docs/player_guide/08-states.md` § Demographics:
  - "The census changes nothing about your population yet" becomes what it does: births and deaths follow the census; the "Demographic Profile" line in a state's birth and death rates; what Display only and Disabled do now.
  - Children per woman is the realized figure, and women's legal standing is one of its terms.
- Modify: `docs/player_guide/06-politics.md`, if it states a figure Tasks 6–8 changed. Check with `grep -n -i "mortality\|birth" docs/player_guide/06-politics.md`; on 2026-10-10 only the two lines Task 6 names, which stay true.
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

Expected:
- The lint is clean, and `--check` exits 0.
- The three CRLF docs are untouched: their CR counts don't change.

- [ ] **Step 3: Commit**

```bash
git add docs/systems/mod_systems.md docs/superpowers/specs/2026-10-08-demographics-design.md docs/superpowers/specs/2026-10-09-demographics-modifier-types-design.md docs/superpowers/plans/2026-10-10-demographics-phase2-calibration.md docs/guides/vanilla_patch_runbook.md docs/player_guide/08-states.md docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf
git commit -m "Demographics phase 2 step 4: docs, the player guide and the release precondition"
```

Add `docs/player_guide/06-politics.md` to the `git add` if Step 1 changed it.

---

### Task 12: The gate

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
.venv/bin/python scripts/analysis/demographics_harness.py predict $D/*.v3 --slope
.venv/bin/python scripts/analysis/demographics_harness.py medicine
.venv/bin/python scripts/analysis/demographics_harness.py fertility
```
Expected:
- The suite prints `OK`, ruff finds nothing, and no audit fails.
- `predict` on the six gate saves gives a world multiple 1837–1900 inside ×1.3–×1.7, with no 20M+ country predicted to shrink.
- It prints what absorbing child labour's lines adds to world growth; copy that figure into the results doc for the owner.

If `predict` fails the gate, stop and report. The fix is calibration (steps 1–3, 5–6), not this step's arithmetic.

- [ ] **Step 2: The in-game probes** (owner, on a throwaway save; deploy per CLAUDE.md "Play-testing unmerged work")
  - **P1:** on the 1887 gate save, fire `event te_debug_demog.1`, option m. Hover each logged state's mortality and compare the totals.
  - **P2:** in a new 1836 game, read the tooltips of the laws, techs and institution §4 lists, and option l's line.
  - **P3:** option n on the capital, after its second yearly pulse. M is set; the read less the applied terms is the terms on top; `bz` and `dz` are small.

- [ ] **Step 3: The fast-mode gate run** (owner)
  - **Start:** a new 1836 game, observed. Census log on (option b), fast mode at 4× (option h) on day 1.
  - **Run** to census year 1950 or later. Archive every `debug.log` generation (`scripts/analysis/archive_probe_logs.sh` on the probe branch). Keep yearly autosaves on D:, not C: (memory: WSL's disk lives on C:).
  - **Then:**

```bash
.venv/bin/python scripts/analysis/demographics_observer_report.py LOGS... --phase2
.venv/bin/python scripts/analysis/demographics_observer_report.py LOGS... --closed-borders SAVES...
.venv/bin/python scripts/analysis/demographics_harness.py replay LOG_WITH_OPTION_A_BLOCKS
.venv/bin/python scripts/analysis/demographics_harness.py predict SAVE_AFTER_A_WAR --check-modifiers
.venv/bin/python scripts/analysis/demographics_harness.py predict --census-rates FAST_RUN_SAVES...
```

**The gate:**
- world population from census year 1836 to 1900 within ×1.3–×1.7;
- no country of 20M or more losing people for ten census years running outside wars;
- the replay exact, on option a's blocks taken in three states at different SoL;
- the Closed Borders `mig_raw` median within ±1 per 1,000. A miss means the walk's expected events don't hold the census's term;
- the clamped share under 1% of the world's people, or the states named;
- regional shares moving the right way: Europe up to 1900, Asia's share falling.

**The release precondition:** this gate passing does not make step 4 releasable alone. Steps 4 and 5 ship together (Global Constraints).

- [ ] **Step 4: Write the results doc** (`docs/testing/demographics-phase2-engine-rates-<date>.md`)
  - the build, and the saves' and logs' location;
  - P1–P4's answers. Write each into §1's table in this plan, turning its "needs" rows to verified or refuted;
  - the gate's figures against each threshold;
  - what absorbing child labour's lines added to world growth;
  - what the census line's `dz` says about the size of the deaths added on top, by country and decade.

  Record any engine fact learned in `docs/guides/scripting_best_practices.md` in the same session.

- [ ] **Step 5: Commit**

```bash
git add docs/testing/demographics-phase2-engine-rates-<date>.md docs/superpowers/plans/2026-10-10-demographics-phase2-engine-rates.md
git commit -m "Demographics phase 2 step 4: probes and gate results"
```

## Risks

- **Performance.** The census runs per state per step: yearly, or for every state at each clock step under fast mode.
  - Step 4 adds one `change_local_variable` per pop in the walk, one per occupied slot in the sweep (the maternal sum), about thirty operations per state in the refresh, and ten in the on-top scales.
  - The sweep already costs 0.75–1.0 s per world-year at about 40 operations a slot (§11.3, Q9), so the additions are a few per cent.
  - No new walk or iterator. Saves gain about eight variables a state, about 0.4 MB.
  - **Check:** option d's benchmark before and after, on the 1887 gate save.
- **Old saves.**
  - **What arrives when:** the absorptions load with the save. M arrives at each state's next step, and the on-top scales a step after that, once `te_dg_cbr_model` exists. So for up to a year a state runs on the curves without the absorbed lines, much as a fresh 1836 state does.
  - **A one-time residual artefact.** The window up to the state's next pulse ran partly at the old rates (before load), but the walk's snapshot (`te_dg_eb`/`te_dg_ed`) reads the new ones. So each state misreads that gap as migration once. Public Health Insurance at level 5 (−0.25 mortality) makes it about 0.25 × bare deaths × the share of the window before the load. This is the same shape as fast mode's documented switch artefact.
  - No migration code. A save from before the census itself seeds as today.
- **The game rule.**
  - M applies under Full only; Display only and Disabled clear the terms at each state's next step.
  - The static absorptions change those two settings until step 5 gives them equilibrium rates. Hence the release precondition: steps 4 and 5 ship together. §2's rule-gated restore is the fallback.
  - Every check is written negatively, so a save from before the rule keeps Full.
- **Migration.**
  - **The residual stays consistent.** The walk's expected events read the state read with M in it (E5, E6), so the residual is still the population change less the engine's natural change.
  - **Indirect effects only.** M changes how many people the engine adds, and so crowding, unemployment and migration pull, but only through the population.
  - **No other reader:** nothing else in the mod reads `modifier:state_birth_rate_mult` or `state_mortality_mult`.
  - **The check:** the gate's Closed Borders median.
  - **Unchanged:** Resettlement's transit deaths and the space race's kills still read as emigrants (growth probe "Open").
- **Civil-war new countries and changes of owner.**
  - **Variables:** the census's variables sit on the state and follow it (spec §2.6).
  - **Modifiers:** whether they follow is unread (E21, probe P4). The `has_modifier` guard keeps a lost modifier from being subtracted as if it were on, and the next step re-applies it.
  - **The new owner's laws** change the walk's literacy term and the INJECTs automatically.
  - **The revolution rule:** "the winner continues the nation" concerns country state, and the census keeps none in modifiers.
- **Fast mode.**
  - **The formula:** F scales the average with the census's new term in it (Task 5), read from the refresh's locals and not from `has_modifier` (E22). The joint fixed point is tested.
  - **Had F read `has_modifier`** and missed the new term, the gate run's first census year would run births about 37% and deaths about 43% high in every state at once (K = 4, M_b = −0.35). That would contaminate P3's first reading.
  - **What fast mode doesn't speed:** literacy, SoL and laws keep the calendar, so a fast run's census sets 20th-century medicine on a 19th-century society (fast run 2026-10-09). The gate's 1836–1900 window counts fast mode's census years, as the calibration plan's gate reads it.
  - **Switching back to normal speed** takes F off at once, as today; the census's term stays.
- **The 1836 start.** Every state runs on the curves until its first step, its second yearly pulse. Until step 5 retunes the curves, that first year's growth is the engine's, about 1% a year (spec §2.3's probe).
- **Terms on top, weighted by the bare curve until step 5** (§2). In 1836 they are about 1.5 times as strong against realized events as in vanilla, and late in the game weaker. Pro-Natalist Subsidies, the Natalism decree and famines are the visible cases.
- **A modifier tooltip line per state.** "Demographic Profile" shows in every state's birth and death rates.
  - The number is often −20% to −50% against the curves, which may alarm a player until step 5 brings the curves to the census's medians.
  - The loc says what sets it.
