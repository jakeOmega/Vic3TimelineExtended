# Demographics: Late Marriage and Birth Spacing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two customs, Late Marriage and Birth Spacing, each a share of a state's people from 0 to 1, multiply the
census's children per woman by 1 − cut × share. They start from history by region, drift with conditions, and are fitted
with the wealth curve's raise and step 1's mortality against the history anchors before any script is written.

**Architecture:**
- **Harness first** (spec §5.1). The Python twin gets the two terms and the practices' arithmetic (start tables, targets,
  yearly drift, seed). The harness gains a drift replay over a run's saves, a joint fit and a regional growth table. The
  fitted values, rounded to neat figures, go into `demographics_params.py`; the owner sees them before any script.
- **One machinery** (call 7). A hand-written effect file, parameterised by the practice's short name (`P = lm`,
  `P = bs`), seeds, steps and sums each practice per state. Generated values hold each practice's start ladder, target
  and term. Phase 3 adds Family Limitation as a third practice and the neighbour spread to the same file.
- **The census's fertility:** children per woman = wealth × natural × marriage × spacing × (1 − means × (1 − desired)).
  The practices are census inputs: they run wherever the census runs and reach the engine only through M, under Full.
- **Call 4** (drop Primogeniture's +10% births under Full): the line moves to the absorbed family of #892's moved
  lines, so the monthly pairs re-apply it outside Full and the census's Late Marriage takes its place under Full.

**Tech Stack:** Paradox script (Victoria 3 1.14.5); Python 3.11/3.12 (`unittest`); `demographics_model.py` as the
script's twin; the `_Engine` script interpreter in `test_demographics_registry.py`; `demographics_harness.py` for
offline checks; `gen_demographics.py` for generated script.

**Spec:** `docs/superpowers/specs/2026-10-10-demographics-late-marriage-design.md` (#862; approved by the owner
2026-10-11, all nine §7 calls, Birth Spacing's cut at 0.35). Read it whole. Also read:
- `docs/systems/mod_systems.md` § Demographics (the census's terms, "The moved lines", "Absorbed by the census", "Added
  on top", Family Limitation, generator and harness);
- `docs/superpowers/plans/2026-10-10-demographics-phase2-calibration.md` (this is its step 2);
- `docs/superpowers/archive/plans/2026-10-11-demographics-engine-lines-script-only.md` (#892: the absorbed and on-top families);
- `docs/testing/demographics-phase2-engine-rates-2026-10-10.md`, "The normal-speed Full run" (#900) and issue #894.

**Base:** `main` at a8d2b9fc (#900). The other agent's branch `demog-gate-from-saves` edits
`scripts/analysis/demographics_observer_report.py`; this plan never touches that file.
- **Re-based 2026-10-12** onto `main` at 4002821a (#904, #907, #913, #914, #916 merged since). The places below that
  name code were re-checked against it; where it moved, the text says so ("since #916").

---

## What the code says that the spec doesn't (read before Task 1)

These come from comparing the spec with `main`. Each is settled here, or listed under Owner questions.

**D1. The wealth curve's baseline moved after the fit.** The spec's §2.2 says `WEALTH_TFR_LOW` is 6.2. It has been 6.0
since #869 (merged seventeen minutes after the spec, the owner's step-4 gate decision). The spec's s = 1.15, its §2.3
tables, its §2.4 growth table and §5.2's "today" figures (5.96 / 5.74 children per woman; +1.08 / +0.98% a year) were
all computed on 6.2, on the old gate run's saves, without the natural-fertility term (also #869).
- **Starting values:** s = 1.15 on today's curve (`WEALTH_TFR_LOW` 6.0 → 6.9, `WEALTH_TFR_HIGH` 3.5 → 4.0), cuts 0.30
  and 0.35. The held share is 0.37: (1 − 1/1.15) ÷ 0.35, the spec's rule at the approved cut (its 0.38 was the same rule
  at 0.34). At these, China and India hold where `main` puts them: 1.15 × (1 − 0.35 × 0.37) = 1.001. India stays there;
  China, Korea and Manchuria may go above it (D13).
- The early-marrying group then reaches about 6.6–6.7, not the spec's 6.7–7.0. The spec's reach on today's curve takes
  s ≈ 1.19 (1.15 × 6.2 ÷ 6.0), and a held share near 0.46 to keep China and India where they are.
- These are starting values only. The owner's ruling (D12) makes the raise the smallest neat value the regional growth
  gate passes, possibly none, and the high group's level a reported figure. Task 6 re-measures "today" on the current
  build. Nothing in this plan uses the spec's 6.2-era numbers as a gate.

**D2. The practices join the natural-fertility term.** The spec writes children per woman as wealth × factor. On `main`
it is wealth × natural × factor, where natural is women's legal standing (`state_natural_fertility_mult`, #869).
- The practices multiply beside natural, outside the means.
- The tooltips and the guide say that women's legal standing works "through who marries and how young". That is now
  Late Marriage's mechanism, so Task 10 and Task 11 drop the phrase.
- The women's-rights laws then reach children per woman twice:
  - through natural, up to −15%;
  - through Late Marriage's women's-work driver: target +0.3 × women's job share × the law's women's work share ÷ 0.48,
    up to about +0.15 of share in a modern economy (spec §4.1), so about −4.5% of births.

  Both were approved separately. Owner question 1.

**D3. Call 4 goes through the absorbed family, not a cancel inside M.** `inh_primogeniture_rural` is a state
`add_modifier` with multiplier = the agrarian share, refreshed yearly by `te_inh_refresh_rural_effects`. Its
`state_birth_rate_mult = 0.1` sits in the state read today, so under Full M scales it to the census's rate as an
on-top line. Nothing cancels it.
- **The fix (Task 9):** `state_birth_rate_mult = 0.1` becomes `state_demog_absorbed_birth_rate_mult = 0.1`, #892's
  absorbed family. `te_demog_line_births` already sums that type per state.
  - Outside Full (and under Full before a state's first census step), the moved lines' pair re-applies it as "Laws and
    Institutions". Gameplay is unchanged; only the line's name in the breakdown differs, as for #892's 36 lines.
  - Under Full the pairs come off when M first lands, and Late Marriage's inheritance driver stands in for it.
- The rural refresh fires `te_demog_events.4` after it touches the modifier, so the pair follows that day rather than
  at the next monthly pulse (owner decision 2 of #892: no month's lag).
- **Rejected:**
  - A cancel inside M would leave the +10% on the tooltip while the census cancels it, against #892's rule (owner,
    2026-10-11: under Full the tooltips stop listing lines the census cancels).
  - Swapping between two static modifiers in the yearly rural refresh would leave M a year late. The refresh and
    `te_demog_rates_refresh` run in the same effect, so `modifier:state_birth_rate_mult` there can't see the swap
    (CLAUDE.md, `add_modifier` visibility).
- Forced Heirship's −0.15 (`inh_forced_heirship_rural`) is unchanged: call 4 names Primogeniture only. It stays an
  engine field, so under Full it stays on top of the census, which applies it at its rate as it does today. Spec §4.5
  and parent §13 put Forced Heirship with Family Limitation in phase 3.
- **Unverified (review C2):** that the engine sums a script-only type on a *state* `add_modifier` scaled by its
  multiplier. If it doesn't, the move changes Primogeniture's farm births outside Full, under the default rule.
  - Task 9 Step 1 builds a console probe, which the owner runs before the move lands.
  - If the probe fails, Task 9 takes Plan B: the swap above, rejected only for its one-year transition.
  - Task 12's in-game check (Disabled, a farming state, the line at 0.1 × its agrarian share) blocks the merge either
    way.

**D4. The practices run wherever the census runs.** The census's cohorts run under Full and Display only, and the panel
shows its children per woman under both. Were the practices Full-only, Display only would show the raised wealth curve
with nothing holding it back (Britain 1836 at about 6.3). So the shares seed and drift with the census
(`te_demog_cohorts_run`), and change gameplay only through M (`te_demog_effects_run`). Under Disabled nothing runs and
the shares wait. This plan reads "every new effect acts only under Full" as "every change to births and deaths": the
census's term and call 4's line are the only two, and both are Full-only. If the owner meant the shares too, Task 8's
two call sites gain a `te_demog_effects_run` limit and Display only shows the census without the practices. Owner
question 2.

**D5. A state with no share takes its siblings' mean, not its neighbours'.** Spec §3.4 says a state with no share takes
"the people-weighted mean of its neighbours that have one, else its table value".
- **The problem:** states seed one at a time. On an old save, or a rule switched on mid-game, every state lacks a
  share, and they seed on their own pulse days. A Russian core state seeding after a Baltic neighbour would take 0.8,
  not 0, and a Baltic state seeding after Russian ones would take about 0. Drift at 2.5% a year would take decades to
  undo it.
- **This plan's rule:** the people-weighted mean of the *other states in its state region* that hold a share (a split
  state's siblings: "a split state is the same people as its sibling", §3.4's own reason). With no sibling holding one,
  its start less what its conditions have already eroded, start × (1 − erosion) (review I2). The drivers stay out, so
  Japan's Late Marriage starts at 0 (call 3).
- **In a new game this is the table.** Nothing has eroded where a practice starts in 1836:
  - no contraception carrier is before era 3 (vulcanization and feminism are era 3);
  - of the 1836 countries with a health law (Britain, Portugal, Spain, Carlist Spain, the Papal States), none starts
    with Birth Spacing.

  Siblings share a start, so mass seeding gives every state its table value in any order. Spec §3.4's 1836 rule is
  the same.
- **An old save or a mid-game switch** seeds near where the drift would have taken each state, not at the 1836 custom.
  A 1950 save would otherwise give Japan's births ×0.65 and the West's ×0.70 for a generation.
- One order effect remains: siblings under different owners erode differently, and the second takes the first's
  share. It is the same people, which is the rule's reason.
- The start is a generated script value read every year inside the target and the seed, so it stores no third variable
  a state.

**D6. The neighbour spread stays in phase 3**, as spec §4.2 ("the neighbour term arrives in phase 3") and §5.3 place it.
Call 7 approved one machinery with one neighbour spread for both practices and, later, Family Limitation. This plan
builds that machinery per state and parameterised by practice, so phase 3 adds the spread once for all practices.
- The harness has no state adjacency (no save field, no `vanilla_parsed/` entity), so phase 2 couldn't replay a spread
  it shipped.
- Note for phase 3, from the spec's own formula: with the start inside the target, the 0.5% spread is damped about
  5:1 against the 2.5% drift.
- Owner question 3 confirms this reading.

**D7. The terms are read live from the shares; no stored term.** `te_dg_natural` is stored at the step because the
law's modifier can change between steps. A practice's share changes only at a census seed or step, and `te_demog_prepare`
recomputes `te_dg_tfr` right after either. So `te_demog_pr_term_<P>` reads `var:te_dg_pr_<P>` live, as 1 with no share
(an old save's state before its next step, whose `te_dg_tfr` has no practice in it either). That keeps the spec's "two
variables a state".

**D8. Which build reads the normal-speed run's saves** (`/mnt/d/vic3te-data/vic3te-demog-p2-normal-2026-10-11/saves/`,
65 plain-text autosaves, 1837–1901, about 265 MB each, made by ec304526).
- `scripts/analysis/demographics_save_inputs.py` is byte-identical between ec304526 and `main` (Task 6 Step 1 checks
  it again). Its changes in this plan only add fields, and #904's (open) only widen its read buffer.
- So these run from this branch on those saves: `history`, `fertility`, `practices-replay` and `practices-fit`. They
  read pops, states (owner, incorporation, region), laws, techs, institutions, timed modifiers, and a state's walk and
  census variables (its women's job share, its census bands).
- The regional gate reads #904's state-years: its `analyze.py` and per-save extracts in the run's archive
  (`session-notes-2026-10-11/regional-rates/`), with #904's peacetime filter (no war at either save, devastation under
  5, radicals under a quarter of the people, no famine and under 10% in severe starvation). Task 6 Step 2 writes them
  again with its defaults and checks they reproduce #904's table.
- Since #916 `history` and `fidelity` run the model on the census's stored inputs (`census_inputs`: medicine as it
  had spread, turmoil, crowding) where a save holds all of `CENSUS_INPUT_VARS`. The ec304526 saves hold none, so they
  read the save's techs, laws and modifiers, with turmoil 0 and medicine at its targets: ec304526's census, which had
  neither term. The model is otherwise unchanged since ec304526 (re-checked 2026-10-12), so these commands still run
  from this branch.
- `predict` and `fidelity` do not run from this branch on those saves. #892's `predict` treats the moved lines as
  script-only, but at ec304526 they were live engine fields. `fidelity`'s cause multipliers differ by build.
  - #900's baseline (×1.77 from the saves) came from a detached worktree at ec304526.
  - Any `predict` on these saves runs there too:
    `git -C /home/jakef/src/Vic3TimelineExtended worktree add --detach /home/jakef/src/vic3te-ec304526 ec304526`.
- The fit reads Gapminder's and Clio Infra's anchors from `/mnt/d/vic3te-data/history-anchors-2026-10-10/anchors.csv`,
  not the nine-line test fixture.
- Saves are chosen by `save_year` (it reads the first 40 lines): every tenth year from 1837, plus 1901. The children
  per woman fit reads 1837 and 1887; the projection reads all eight.

**D9. Strategic regions need a committed snapshot.**
- The start tables are by strategic region, and the script reads them with `region = sr:<name>`
  (`colonial_empire_triggers.txt` does the same).
- The harness must map a save's states to strategic regions. A save names only the state region (`region="STATE_X"`,
  already in `SECTIONS["states"]`, so spec §5.1 item 2's "one more field" is done).
- The base game keeps the map in `game/common/strategic_regions/`, which CI doesn't have, and `vanilla_parsed/` has no
  strategic regions.
- So Task 1 commits `scripts/analysis/demographics_strategic_regions.json`, written once from the game files with the
  mod's two `REPLACE`s applied (`common/strategic_regions/zzz_modified_strategic_regions.txt`). It has 36 land
  regions, and each of the 675 land state regions in `map_data/state_regions/` sits in exactly one of them (checked
  2026-10-11).
- Task 11 adds the refresh to the vanilla patch runbook. Task 1 files an issue for strategic regions in
  `vanilla_parsed/` and the mod state server (CLAUDE.md, capability gaps).

**D10. The start tables' edges the spec left open.** These are geography, as the spec asks, and they are starting
proposals:
- The vanilla file's "# Italy" group includes **Malta** and **Corsica**: both take Italy's 0.5 (the Mediterranean
  between the two patterns).
- Its "# Iberia" group includes **Cape Verde**, an African archipelago, which stays at 0. The **Canary Islands** take
  the rest of Iberia's 0.6.
- `region_north_china` includes Mongolia's four state regions and `region_south_china` includes Formosa. They take
  East Asia's share by strategic region, as §3.3's table says (D13).
- Japan is the ten state regions Hokkaido to Kyushu: Hokkaido, Tohoku, Kanto, Hokushinetsu, Tokai, Kyoto, Kansai,
  Chugoku, Shikoku and Kyushu (Ryukyu excepted).

**D11. No new script-only modifier type.** The later lever, `state_late_marriage_target_add` (§6), is phase 3. So
`scripts/release/comment_out_census_inputs.py` needs no change.
- Call 4's line moves to an existing moved-lines type, which a release keeps: a release has no rule, so
  `te_demog_lines_apply` holds everywhere and the pair re-applies the +10%.
- Task 9 adds a test that pins this.
- In a release the census never runs, so the practices' values and effects are never called.

**D12. The gate is regional growth (owner, 2026-10-11).** The spec's gate held children per woman to the anchors, and
growth only as a world line within ±0.1% a year of step 1's (review C1). That line passes a world that is regionally
worse than today's:
- the raise adds about +6 per 1,000 a year wherever no practice holds;
- Late Marriage takes about −7 off western, northern and central Europe;
- the Middle East and Africa go from +8.8 to about +15 against history's +3 to +8, while the world's births move only
  ×1.005;
- and it accepts the ×1.77 world #894 calls hot.

**The owner's ruling (2026-10-11):** growth matters more than the exact children-per-woman figure.
- The regional growth gate is the gate:
  - each of #904's regions' projected peacetime births less deaths inside its "normal years" band;
  - the world at or below today's minus about 1 per 1,000 (what ×1.65 over 1836–1900 needs);
  - China inside +3 to +6 (not ±0.1% of today's);
  - no country of 20M people or more with projected peacetime births below deaths.
- The wealth-curve raise is the **smallest neat value that passes it, possibly none** (s = 1.00).
- **The high-fertility group's children per woman may stay below history's ~7.** Task 6 reports it, and requires
  nothing of it.
- **Calibration step 3, the geographic mortality term, is a separate step after this work, not inside it.**
  - Should no point pass, Task 6 takes the smallest raise with the fewest failures and names the regions only a
    geographic term could fix.
  - Those regions are step 3's.
- Task 5 builds the projection, the gate and the selection; Task 6 runs them.

**D13. China's Birth Spacing may sit above the cancel share (owner, 2026-10-11).** Spec §2.2 held China and India at the
share that only cancels the raise, and put "China at history's 5.5" (a share near 0.63 at the spec's fit) off until a
mortality refit. The owner allows that variant for China, Korea and Manchuria now:
- their Birth Spacing share may sit above the cancel share, so Birth Spacing lowers their births toward history's ~5.5
  children per woman;
- the fit chooses it as the smallest share on a 0.01 grid at which China's projected peacetime births less deaths
  lands in its +3 to +6 band (`east_for_china`, Task 5), never below the cancel share;
- the results doc reports China's children per woman at it, and flags it below about 5;
- **India stays as planned**, at the cancel share: its excess is early mortality, calibration step 3's.

So the start tables carry two held values: `BS_EAST_ASIA_START` (China's strategic regions, Manchuria's and Korea's
state regions) and `BS_HELD_START` (India's). `M.bs_held_group` says which by membership, not by value, since both
start at 0.37.

## Owner questions (all answered by the owner, 2026-10-11)

1. **Women's rights twice** (D2). **Answered: keep both**, the natural term (women's standing inside marriage) and Late
   Marriage's women's-work driver (jobs delaying marriage). The overlap is at most about 4.5% of births.
2. **The shares under Display only** (D4). **Answered: they run under Display only too**, with the census, so Display
   only shows the same children per woman as Full.
3. **The spread** (D6). **Answered: it waits for phase 3**, as the spec has it.

## Global Constraints

- **Nothing changes outside Full (owner, 2026-10-10), in gameplay** (owner, 2026-10-11, #892's framing: same values, on
  the same pops, scaled the same way).
  - Call 4's line changes name in a state's breakdown outside Full ("Laws and Institutions"), not size, and only if
    Task 9's probe shows the engine scales it (D3); otherwise Plan B keeps it on its engine field.
  - `demographics_rule` defaults to Disabled, and every read of it goes through `te_demog_cohorts_run` (Full or
    Display only) and `te_demog_effects_run` (Full), written positively.
- **Game version:** Victoria 3 1.14.5. Vanilla facts come from `vanilla_parsed/` and the 1.14.5 install at
  `/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game`.
- **Every number is a starting proposal the harness fits** (spec header), except what the owner fixed: the practices'
  structure and drivers (calls 1–3, 5–9) and Birth Spacing's cut starting at 0.35. Fitted values are rounded to neat
  figures (owner, 2026-10-11): s and the cuts to 0.05, the held share to 0.01, the mortality knobs to 0.05 (the SoL
  threshold to a whole number), and the means pair to 0.05.
- **No targeting:** no mechanic names a culture or religion, and no loc names a country. Start values by region are
  start conditions (spec, owner rulings).
- **Generated files** (`te_demog_generated_values.txt`, `te_demog_generated_effects.txt`) come from
  `scripts/generators/gen_demographics.py`. Never hand-edit them; `test_gen_demographics.py` fails when they are stale.
- **Paradox files:** tab indentation; exactly one UTF-8 BOM on every `.txt` and `.yml`. Run
  `python3 scripts/format_paradox_tabs.py <files>` after edits.
- **Script literals:** at most five decimals.
- **Every `divide =`** in a `te_demog*` file takes a literal or a `{ value = … min = … }` block
  (`TestDivisions.test_every_division_is_guarded`).
- **One refresh site per modifier:** this plan adds no modifier. The moved lines' pairs stay
  `te_demog_lines_refresh`'s; Task 9 only fires it.
- **Scripted effect calls pass exactly the `$X$` the callee names** (`script_argument_audit --strict`).
- **Localization:** add keys to an existing `*_l_english.yml`, run `python3 organize_loc.py`, and commit everything it
  rewrites. Player-facing text follows `docs/player_guide/STYLE.md`; loc uses `#b X#!`, never `[b]`.
- **Python:** 3.11-compatible (no PEP 701 f-strings). Check with
  `grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" <files>`.
- **Running Python in this sparse worktree:**
  `V=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python` and
  `export VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent`
  for the suite. Task 1's `--refresh` is the one command that needs the real game path (it reads
  `path_constants.base_game_path`; run it without the dummy variables).
- **Commits:** by path, never `git commit -a`. End each message with the session's `Co-Authored-By` and
  `Claude-Session` lines.
- **No `/reload`, no deploy** from a worktree (CLAUDE.md). The owner's in-game checks deploy per CLAUDE.md "Play-testing
  unmerged work".
- **Never deploy the branch between Task 6's commit and Task 8's.** Task 6 raises the wealth curve in the generated
  values before Task 8 puts the practices in the script.
- **The gate is regional growth** (owner, 2026-10-11; D12). The raise is the smallest neat value it passes, possibly
  none. Children per woman is fitted, and the high group's level is reported only. Calibration step 3 is a separate
  step after this work. China's, Korea's and Manchuria's Birth Spacing may sit above the cancel share to bring China into
  its band; India's stays at it (D13).

## Review Focus

1. **An old save, or a rule switched on mid-game.** Every state lacks a share, and they seed on their own pulse days.
   - Expect: every state gets its own table value less what its conditions have eroded (the table in a new game),
     and a neighbour across a border plays no part.
   - Pinned by Task 8's `test_the_seed_reads_only_its_state_region` and
     `test_a_state_with_no_sibling_seeds_at_its_eroded_start`; the twin by Task 2's
     `test_a_seed_takes_its_siblings_people_weighted_mean_else_its_eroded_start` and Task 4's
     `test_states_seed_from_the_table_in_any_order`.
2. **A census re-seed** (a merge, a split, a gap, fast mode's first switch) **keeps the state's shares.** Customs belong
   to the people, and a re-seed only re-counts them.
   - Pinned by Task 8's `test_a_census_reseed_keeps_the_shares`.
3. **A state split mid-game** takes its sibling's drifted shares, not the 1836 table.
   - Pinned by Task 8's `test_a_new_state_takes_its_siblings_shares`. A census step on a state with no share at all
     (an old save's) seeds it first: `test_a_step_on_a_state_with_no_share_seeds_then_drifts`.
4. **Under Disabled, Primogeniture's farm births are what `main` gives**, through the pair, and the pair follows the
   yearly rural refresh that day.
   - The engine half (a script-only type on a state modifier, scaled by its multiplier) is unverified. Task 9's probe
     decides Plan A or B, and Task 12's in-game check blocks the merge.
   - Pinned (Plan A) by Task 9's `test_the_pair_carries_primogeniture_outside_full`, which reads the line from the
     modifier file, and `test_the_rural_refresh_fires_the_lines_refresh`.
   - Under Full, once M lands, the line is in no pair and no read: Task 9's
     `test_under_full_the_census_term_replaces_primogeniture`.
5. **A tooltip before the state's next step** (an old save on load) shows ×1.00 for both practices beside a headline
   with no practice in it.
   - Pinned by Task 10's `test_the_terms_read_one_before_any_share`.
   - The headline matches the terms after a step: Task 8's `test_the_tfr_takes_both_terms`.

## Scope

| In | Out (where it goes) |
|---|---|
| The two terms in the census's fertility, the twin and the harness | The neighbour spread (phase 3; D6) |
| The start tables, seeding (D5), the yearly drift, the drivers of calls 5 and 6 | The blended age schedule and generation length (§2.5; phase 3) |
| The joint refit: s, the cuts, the held share, the era-3 means pair, step 1's poverty term and base infection (calls 4, 8) | Family Limitation on the machinery (phase 3; call 7) |
| Call 4's line under Full (D3) | Forced Heirship's −0.15 (phase 3, parent §13) |
| The tooltips' two terms, the marriage age, the country's means (§5.3) | `state_late_marriage_target_add` and the "Later, Longer, Fewer" measure (§6; phase 3; call 9) |
| The regional growth gate: #904's peacetime rates projected to the fit (owner, 2026-10-11) | Calibration step 3's geographic mortality term (a separate step after this work; D12) |
| Two 20th-century scenarios outside the West (review I3) | Changing the in-game gate's world measure (#904's item) |
| Docs, the player guide, the owner's in-game list | The census log's fields (`demographics_observer_report.py`, another branch's file) |

## File structure

| File | Change | Responsibility |
|---|---|---|
| `scripts/analysis/demographics_regions.py` | create | the strategic-region snapshot: parse, refresh, load; #904's regional groups and their history bands |
| `scripts/analysis/demographics_strategic_regions.json` | create (written by `--refresh`) | `{strategic region: [state regions]}`, land regions only |
| `scripts/analysis/demographics_params.py` | modify | `PRACTICES`, `PRACTICE_CUT`, the start tables, the drift's constants; Task 6's fitted values |
| `scripts/analysis/demographics_model.py` | modify | `Inputs.practices`, `.agrarian_share`, `.impartible`; the terms in `fertility`; `practice_start`, `contraception_beyond`, `practice_erosion`, `practice_target`, `practice_drift`, `practice_seed`, `marriage_age` |
| `scripts/analysis/demographics_save_inputs.py` | modify | `CountryInputs.agrarian` and `agrarian_share`; `state_regions(sections)` |
| `scripts/analysis/demographics_practices.py` | create | a save's states for the practices (with their census bands), the drift replay, the fit, the projection of #904's peacetime rates, the regional gate |
| `scripts/analysis/demographics_harness.py` | modify | `practices-replay`, `practices-fit`; `history --shares --incorporated-only --no-practices`; `PRACTICE_SCENARIOS` (Task 5), the fertility command's from Task 6 |
| `scripts/generators/gen_demographics.py` | modify | the start ladders, erosions, seeds, targets, terms, the marriage age, the practice loops, `te_demog_k_practice_rate` |
| `common/scripted_effects/te_demog_practice_effects.txt` | create | the one machinery: `te_demog_practice_seed`, `_step`, `_country_init`, `_country_add`, `_country_store` (`$P$`) |
| `common/scripted_effects/te_demog_effects.txt` | modify | `te_demog_seed`, `te_demog_step_begin` and `te_demog_country_census` call it; the header's variable list |
| `common/script_values/te_demog_values.txt` | modify | `te_demog_tfr` × `te_demog_pr_terms` |
| `common/static_modifiers/te_inheritance_modifiers.txt` | modify | Plan A: Primogeniture's birth line on the absorbed family's type. Plan B: a migration-only twin |
| `common/scripted_effects/te_inheritance_effects.txt` | modify | Plan A: the rural refresh fires `te_demog_events.4`. Plan B: it applies the twin where the census sets births |
| `common/scripted_effects/te_debug_demog_effects.txt`, `common/script_values/te_debug_demog_values.txt`, `common/static_modifiers/te_debug_demog_modifiers.txt`, `events/te_debug_demog_events.txt` | modify | option o, the engine-scaling probe (Task 9); option l logs the shares, their targets and the absorbed births sum (Task 10) |
| `common/technology/technologies/te_demog_tech_injections.txt` | modify only if Task 6's fit moves them | vulcanization's and feminism's contraception |
| `localization/english/te_miscellaneous_l_english.yml`, `te_concepts_l_english.yml`, `te_events_l_english.yml` | modify | the two tooltips' terms and text; `inh_primogeniture_rural_desc`; option o |
| Tests | create: `test_demographics_regions.py`, `test_demographics_practices.py`; modify: `test_demographics_model.py`, `test_demographics_save_inputs.py`, `test_demographics_harness.py`, `test_gen_demographics.py`, `test_demographics_registry.py`, `test_release_census_inputs.py` | |
| Docs | modify | `docs/systems/mod_systems.md` § Demographics; the spec's §2.2 note and §5.2; `docs/guides/python_tools.md`; `docs/auto_generated_files.md`; `docs/guides/vanilla_patch_runbook.md`; `docs/player_guide/08-states.md`, `06-politics.md`; the PDF |
| `docs/testing/demographics-late-marriage-<date>.md` | create (Task 6), extend (Tasks 9 and 12) | the baseline, the replay, the fit, the regional gate, the probe, the in-game checks |

---

### Task 1: The strategic-region snapshot

**Files:**
- Create: `scripts/analysis/demographics_regions.py`
- Create: `scripts/analysis/demographics_strategic_regions.json` (written by Step 3's `--refresh`)
- Test: `test_demographics_regions.py` (create)

**Interfaces:**
- Produces: `R.parse(text) -> {region: [state regions]}`; `R.load_table(path=SNAPSHOT) -> {region: [states]}`;
  `R.strategic_region_of(path=SNAPSHOT) -> {state region: strategic region}`; `R.REPORT_REGIONS: tuple[(label,
  tuple[strategic region], (low, high) per 1,000 a year or None)]`, #904's groups and its history bands (the gate's,
  Task 5); `R.report_row_of() -> {strategic region: label}`.

- [x] **Step 1: Write the failing test**

```python
"""scripts/analysis/demographics_regions.py: the strategic-region snapshot the practices' start tables and the
regional report read (docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md, Task 1)."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_regions as R  # noqa: E402


def _land_state_regions():
    out = set()
    for path in (ROOT / "map_data" / "state_regions").glob("*.txt"):
        if path.name == "99_seas.txt":
            continue
        out |= set(re.findall(r"^(STATE_[A-Z0-9_]+)\s*=\s*\{", path.read_text(encoding="utf-8-sig"), re.M))
    return out


class TestSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = R.load_table()
        cls.of = R.strategic_region_of()

    def test_every_land_state_region_is_in_exactly_one(self):
        self.assertEqual(set(self.of), _land_state_regions())
        named = [s for states in self.table.values() for s in states]
        self.assertEqual(len(named), len(set(named)))

    def test_the_mods_replacements_are_applied(self):
        mod = R.parse(R.MOD_OVERRIDE.read_text(encoding="utf-8-sig"))
        for region, states in mod.items():
            for state in states:
                self.assertEqual(self.of[state], region, state)

    def test_parse_reads_replace_and_skips_comments(self):
        text = ("region_a = {\n\tstates = { STATE_X # STATE_COMMENTED\n STATE_Y }\n}\n"
                "REPLACE:region_b = {\n\tcapital_province = x1\n\tstates = { STATE_Z }\n}\n")
        self.assertEqual(R.parse(text), {"region_a": ["STATE_X", "STATE_Y"], "region_b": ["STATE_Z"]})

    def test_report_regions_cover_every_land_strategic_region_once(self):
        named = [r for _label, regions, _hist in R.REPORT_REGIONS for r in regions]
        self.assertEqual(len(named), len(set(named)))
        self.assertEqual(set(named), set(self.table))


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run it to see it fail**

Run: `$V -m unittest test_demographics_regions`
Expected: FAIL, `ModuleNotFoundError: No module named 'demographics_regions'`.

- [x] **Step 3: Write the module**

```python
#!/usr/bin/env python3
"""Strategic regions for the demographics harness: which strategic region each state region is in.

The practices' start tables (demographics_params.PRACTICE_START_REGION) are keyed by strategic region, and the script
reads them with `region = sr:<name>`. The harness needs the same map for a save's states, which name only their state
region (`region="STATE_X"`). The base game keeps it in game/common/strategic_regions/, which CI doesn't have, and
vanilla_parsed/ has no strategic regions, so a snapshot sits beside this file (land regions only):

    demographics_regions.py --refresh [--game-dir DIR]   # rewrite demographics_strategic_regions.json
    demographics_regions.py --check   [--game-dir DIR]   # exit 1 if a fresh build would differ

Re-run --refresh after a vanilla patch that moves a state region (docs/guides/vanilla_patch_runbook.md).
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = Path(__file__).resolve().parent / "demographics_strategic_regions.json"
MOD_OVERRIDE = ROOT / "common" / "strategic_regions" / "zzz_modified_strategic_regions.txt"
STATE_REGIONS = ROOT / "map_data" / "state_regions"

_HEADER = re.compile(r"^(?:REPLACE:)?(region_\w+)\s*=\s*\{", re.M)
_STATES = re.compile(r"\bstates\s*=\s*\{([^{}]*)\}")
_STATE = re.compile(r"\bSTATE_[A-Z0-9_]+\b")

# #904's regional groups (its analyze.py's GROUPS and labels, which its state-years carry) with history's peacetime births
# less deaths in normal years, per 1,000 a year (PR #904's results doc, "Peacetime births less deaths, by region"): the
# late-marriage plan's gate (review C1). China's is the pace without its collapse; Africa's and the Middle East's are
# conjectures. Oceania has no band.
REPORT_REGIONS = (
    ("China", ("region_north_china", "region_south_china"), (3, 6)),
    ("India", ("region_north_india", "region_south_india", "region_himalayas"), (6, 9)),
    ("W/N/C/S Europe",
     ("region_western_europe", "region_northern_europe", "region_central_europe", "region_southern_europe"), (8, 10)),
    ("Africa", ("region_nile_basin", "region_north_africa", "region_west_africa", "region_equatorial_africa",
                "region_southern_africa", "region_east_africa"), (3, 8)),
    ("USA, Canada", ("region_canada", "region_pacific_coast", "region_great_plains", "region_atlantic_coast"),
     (17, 21)),
    ("E Europe, Balkans", ("region_eastern_europe", "region_balkans"), (8, 12)),
    ("Japan, Korea, Manchuria", ("region_northeast_asia",), (2, 6)),
    ("Russia, Siberia", ("region_russia", "region_siberia"), (10, 13)),
    ("Middle East, C Asia", ("region_near_east", "region_arabia", "region_greater_persia", "region_central_asia"),
     (4, 8)),
    ("South America", ("region_brazil", "region_andes", "region_la_plata", "region_gran_colombia"), (12, 16)),
    ("SE Asia", ("region_indochina", "region_indonesia"), (9, 13)),
    ("Mexico, C America", ("region_central_america",), (10, 13)),
    ("Oceania", ("region_oceania",), None),
)


def parse(text):
    """{region: [state regions]} from a strategic_regions file; a mod's REPLACE:region_x counts as region_x."""
    code = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
    out, pos = {}, 0
    while True:
        m = _HEADER.search(code, pos)
        if not m:
            return out
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(code[i], 0)
            i += 1
        states = _STATES.search(code[m.end():i - 1])
        if states:
            out[m.group(1)] = _STATE.findall(states.group(1))
        pos = i


def land_state_regions():
    """Every state region in map_data/state_regions/ outside the seas file."""
    out = set()
    for path in STATE_REGIONS.glob("*.txt"):
        if path.name != "99_seas.txt":
            out |= set(re.findall(r"^(STATE_[A-Z0-9_]+)\s*=\s*\{", path.read_text(encoding="utf-8-sig"), re.M))
    return out


def build(game_dir):
    """The table from the base game's files, the mod's REPLACEs on top, land regions only."""
    table = {}
    for path in sorted(Path(game_dir).glob("*.txt")):
        table.update(parse(path.read_text(encoding="utf-8-sig")))
    table.update(parse(MOD_OVERRIDE.read_text(encoding="utf-8-sig")))
    land = land_state_regions()
    return {r: sorted(s) for r, s in sorted(table.items()) if set(s) & land}


def load_table(path=SNAPSHOT):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def strategic_region_of(path=SNAPSHOT):
    return {state: region for region, states in load_table(path).items() for state in states}


def report_row_of():
    """{strategic region: its REPORT_REGIONS label}."""
    return {r: label for label, regions, _hist in REPORT_REGIONS for r in regions}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--game-dir")
    args = ap.parse_args(argv)
    game_dir = args.game_dir
    if game_dir is None:
        sys.path.insert(0, str(ROOT))
        import path_constants
        game_dir = Path(path_constants.base_game_path) / "game" / "common" / "strategic_regions"
    table = build(game_dir)
    text = json.dumps(table, indent=1, sort_keys=True) + "\n"
    if args.check:
        same = SNAPSHOT.exists() and SNAPSHOT.read_text(encoding="utf-8") == text
        print("current" if same else f"stale: {SNAPSHOT}")
        return 0 if same else 1
    if args.refresh:
        SNAPSHOT.write_text(text, encoding="utf-8")
        print(f"wrote {SNAPSHOT}: {len(table)} regions, {sum(len(s) for s in table.values())} state regions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [x] **Step 4: Write the snapshot from the game** (the one command in this plan that needs the real game path)

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python scripts/analysis/demographics_regions.py --refresh`
Expected: `wrote …/demographics_strategic_regions.json: 36 regions, 675 state regions`.

- [x] **Step 5: Run the tests**

Run: `$V -m unittest test_demographics_regions`
Expected: 4 tests, `OK`.

- [x] **Step 6: File the capability issue** (CLAUDE.md, "File issues for mod-state-server capability gaps")

```bash
gh issue create --label enhancement --label tooling \
  --title "vanilla_parsed / mod_state_server: strategic regions (state region -> strategic region)" \
  --body "The demographics practices (docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md) key their start tables by strategic region, and the harness needs each save state's strategic region. vanilla_parsed/ has no strategic_regions entity and the server no endpoint, so the plan commits scripts/analysis/demographics_strategic_regions.json, built from game/common/strategic_regions/ plus the mod's REPLACEs. Proposed: add strategic_regions to mod_state.VANILLA_COMMON_DIRS and GET /strategic-regions/<name> -> {\"states\": [...]}, GET /state-region/<STATE_X> -> {\"strategic_region\": ...}. gen_formable_regions.py reads the same files from the game install today."
```

- [x] **Step 7: Commit**

```bash
git add scripts/analysis/demographics_regions.py scripts/analysis/demographics_strategic_regions.json test_demographics_regions.py
git commit -m "Demographics: the strategic-region snapshot for the practices' start tables and the regional report"
```

---

### Task 2: The model's two terms and the practices' arithmetic

**Files:**
- Modify: `scripts/analysis/demographics_params.py` (a new section after "Fertility inputs as modifier types")
- Modify: `scripts/analysis/demographics_model.py` (`Inputs`; `fertility`; new functions after `fertility`)
- Test: `test_demographics_model.py` (new class `TestPractices`; add `import dataclasses` at the top)

**Interfaces:**
- Produces (params): `PRACTICES = ("lm", "bs")`, `PRACTICE_CUT`, `BS_HELD_START` (India), `BS_EAST_ASIA_START`,
  `BS_EAST_ASIA_REGIONS`, `BS_EAST_ASIA_STATES`, `BS_INDIA_REGIONS`, `PRACTICE_START_REGION`,
  `PRACTICE_START_STATE`, `PRACTICE_RATE`, `PRACTICE_EROSION_CONTRACEPTION`, `PRACTICE_EROSION_FROM`,
  `PRACTICE_EROSION_SPAN`, `PRACTICE_EROSION_ACCESS`, `PRACTICE_ACCESS_SPAN`, `LM_INHERITANCE`, `LM_WOMENS_WORK`,
  `IMPARTIBLE_LAWS`, `MARRIAGE_AGE_AT_ZERO`, `MARRIAGE_AGE_SPAN`.
- Produces (model): `Inputs.practices: dict` (`{"lm": share, "bs": share}`), `Inputs.agrarian_share: float`,
  `Inputs.impartible: bool`. `fertility()` gains the keys `"lm"` and `"bs"` (the terms). `practice_start(practice,
  state_region, strategic_region) -> float`; `bs_held_group(state_region, strategic_region) -> "east_asia" | "india" |
  None`; `contraception_beyond(inp) -> float`; `practice_erosion(practice, inp) ->
  float`; `practice_target(practice, inp, start) -> float`; `practice_drift(share, target) -> float`;
  `practice_seed(practice, inp, start, siblings) -> float` (siblings `[(people, share)]`); `marriage_age(share) ->
  float`.

Nothing changes in any figure yet: every `Inputs` has no practice until a caller sets one, and the raise waits for Task 6.

- [x] **Step 1: Write the failing tests** (append to `test_demographics_model.py`)

```python
class TestPractices(unittest.TestCase):
    """Late Marriage (lm) and Birth Spacing (bs): docs/superpowers/specs/2026-10-10-demographics-late-marriage-design.md
    §2-§4; the plan's D5 for the seed."""

    def test_the_terms_multiply_outside_the_means(self):
        inp = M.Inputs(sol=8, literacy=0.2, urban_share=0.1)
        base = M.fertility(inp, 35.0)
        both = M.fertility(dataclasses.replace(inp, practices={"lm": 1.0, "bs": 0.5}), 35.0)
        want = base["tfr"] * (1 - P.PRACTICE_CUT["lm"]) * (1 - P.PRACTICE_CUT["bs"] * 0.5)
        self.assertAlmostEqual(both["tfr"], want, places=9)
        self.assertAlmostEqual(both["lm"], 1 - P.PRACTICE_CUT["lm"])
        self.assertAlmostEqual(both["bs"], 1 - P.PRACTICE_CUT["bs"] * 0.5)
        self.assertEqual(both["means"], base["means"], "the practices act outside the means")

    def test_no_share_is_no_term(self):
        terms = M.fertility(M.Inputs(sol=8), 35.0)
        self.assertEqual((terms["lm"], terms["bs"]), (1.0, 1.0))

    def test_the_start_tables(self):
        for practice, state, region, want in (
                ("lm", "STATE_HOME_COUNTIES", "region_western_europe", 1.0),
                ("lm", "STATE_KOLA", "region_northern_europe", 0.2),
                ("lm", "STATE_GALICIA", "region_southern_europe", 0.9),
                ("lm", "STATE_NEW_CASTILE", "region_southern_europe", 0.6),
                ("lm", "STATE_CAPE_VERDE", "region_southern_europe", 0.0),
                ("lm", "STATE_LAZIO", "region_southern_europe", 0.5),
                ("lm", "STATE_PROVENCE", "region_southern_europe", 1.0),
                ("lm", "STATE_POSEN", "region_eastern_europe", 0.8),
                ("lm", "STATE_MAZOVIA", "region_eastern_europe", 0.4),
                ("lm", "STATE_MOSCOW", "region_russia", 0.0),
                ("lm", "STATE_KANTO", "region_northeast_asia", 0.0),
                ("bs", "STATE_KANTO", "region_northeast_asia", 1.0),
                ("bs", "STATE_RYUKYU_ISLANDS", "region_northeast_asia", 0.0),
                ("bs", "STATE_SEOUL", "region_northeast_asia", P.BS_EAST_ASIA_START),
                ("bs", "STATE_JIANGSU", "region_north_china", P.BS_EAST_ASIA_START),
                ("bs", "STATE_BOMBAY", "region_south_india", P.BS_HELD_START),
                ("bs", "STATE_HOME_COUNTIES", "region_western_europe", 0.0)):
            with self.subTest(practice=practice, state=state):
                self.assertEqual(M.practice_start(practice, state, region), want)

    def test_the_held_groups(self):
        """Owner, 2026-10-11 (plan D13): China, Manchuria and Korea take one Birth Spacing share, India another."""
        for state, region, want in (("STATE_JIANGSU", "region_north_china", "east_asia"),
                                    ("STATE_SEOUL", "region_northeast_asia", "east_asia"),
                                    ("STATE_BOMBAY", "region_south_india", "india"),
                                    ("STATE_KANTO", "region_northeast_asia", None),
                                    ("STATE_MOSCOW", "region_russia", None)):
            self.assertEqual(M.bs_held_group(state, region), want, state)

    def test_the_start_tables_name_only_real_places(self):
        import demographics_regions as R
        table = R.load_table()
        for practice in P.PRACTICES:
            self.assertLessEqual(set(P.PRACTICE_START_REGION[practice]), set(table), practice)
            self.assertLessEqual(set(P.PRACTICE_START_STATE[practice]), set(R.strategic_region_of()), practice)

    def test_late_marriage_target(self):
        # 1836: nothing beyond traditional methods, No Women's Rights, Primogeniture on half-farming land
        inp = M.Inputs(literacy=0.4, laws=frozenset({"law_no_womens_rights"}), agrarian_share=0.5,
                       female_job_share=0.2, impartible=True)
        work = P.LM_WOMENS_WORK * 0.2 * 0.1 / P.FULL_FEMALE_WORK_SHARE
        self.assertAlmostEqual(M.practice_target("lm", inp, 0.0), P.LM_INHERITANCE * 0.5 + work)
        self.assertEqual(M.practice_target("lm", inp, 1.0), 1.0, "clamped at 1")
        # era 3's pair at literacy 0.75: the means beyond traditional methods are 0.35 x 0.825 = 0.289
        late = dataclasses.replace(inp, literacy=0.75, impartible=False, female_job_share=0.0,
                                   mods={P.CONTRACEPTION_TYPE: 0.35})
        erosion = P.PRACTICE_EROSION_CONTRACEPTION * min(1.0, (0.35 * 0.825 - P.PRACTICE_EROSION_FROM)
                                                         / P.PRACTICE_EROSION_SPAN)
        self.assertAlmostEqual(M.practice_target("lm", late, 1.0), 1 - erosion)
        self.assertAlmostEqual(M.practice_target("lm", dataclasses.replace(late, mods={P.ACCESS_TYPE: 1.0}), 1.0),
                               1.0, msg="health care doesn't erode Late Marriage")

    def test_birth_spacing_target_erodes_with_contraception_and_health_access(self):
        inp = M.Inputs(literacy=0.3, mods={P.ACCESS_TYPE: 0.25})
        self.assertAlmostEqual(M.practice_target("bs", inp, 1.0),
                               1 - P.PRACTICE_EROSION_ACCESS["bs"] * 0.25 / P.PRACTICE_ACCESS_SPAN)
        full = dataclasses.replace(inp, literacy=1.0, mods={P.ACCESS_TYPE: 1.0, P.CONTRACEPTION_TYPE: 0.5})
        self.assertEqual(M.practice_target("bs", full, 1.0), 0.0, "the erosion is at most 1")
        self.assertEqual(M.practice_target("bs", M.Inputs(agrarian_share=1.0, impartible=True), 0.0), 0.0,
                         "nothing builds Birth Spacing up")

    def test_drift_closes_its_rate_of_the_gap(self):
        self.assertAlmostEqual(M.practice_drift(1.0, 0.45), 1.0 - P.PRACTICE_RATE * 0.55)
        self.assertEqual(M.practice_drift(0.0, 0.0), 0.0)

    def test_a_seed_takes_its_siblings_people_weighted_mean_else_its_eroded_start(self):
        inp = M.Inputs()
        self.assertAlmostEqual(M.practice_seed("lm", inp, 0.0, [(300.0, 0.8), (100.0, 0.4)]), 0.7)
        self.assertEqual(M.practice_seed("lm", inp, 0.4, []), 0.4, "nothing eroded: the start")
        self.assertEqual(M.practice_seed("lm", inp, 0.4, [(0.0, 0.9)]), 0.4, "siblings with no people don't count")
        # review I2: an old save's or a mid-game switch's state seeds at its start less what its conditions eroded
        late = M.Inputs(literacy=1.0, mods={P.CONTRACEPTION_TYPE: 1.0, P.ACCESS_TYPE: 1.0})
        self.assertEqual(M.practice_seed("bs", late, 1.0, []), 0.0, "a 1950 Japan seeds with its spacing gone")
        self.assertAlmostEqual(M.practice_seed("bs", M.Inputs(mods={P.ACCESS_TYPE: 0.25}), 1.0, []),
                               1 - P.PRACTICE_EROSION_ACCESS["bs"] * 0.5)
        drivers = M.Inputs(female_job_share=1.0, laws=frozenset({"law_protected_class"}), agrarian_share=1.0,
                           impartible=True)
        self.assertEqual(M.practice_seed("lm", drivers, 0.0, []), 0.0,
                         "the drivers stay out of the seed: Japan's Late Marriage starts at 0 (call 3)")

    def test_marriage_age(self):
        self.assertEqual(M.marriage_age(1.0), 26)
        self.assertEqual(M.marriage_age(0.0), 19)
```

- [x] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_model.TestPractices`
Expected: FAIL, `AttributeError: module 'demographics_params' has no attribute 'PRACTICE_CUT'` (and `practices` an
unexpected keyword for `Inputs`).

- [x] **Step 3: The parameters** (insert after `DEMOG_TYPES = …` and `MEANS_ACCESS_BASE = 0.3`, before "Cause multipliers
  from state inputs")

```python
# ---- Late Marriage and Birth Spacing ---------------------------------------------------------------------------
# docs/superpowers/specs/2026-10-10-demographics-late-marriage-design.md (approved by the owner 2026-10-11, all nine of
# its section 7 calls; Birth Spacing's cut at 0.35); plan docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md.
# Two customs, each a share of a state's people (0-1): children per woman x (1 - cut x share) for each, outside the
# means. Every value is a starting proposal the harness fits (plan Task 6), rounded to neat figures. The short names
# key the script (te_dg_pr_<P>, te_demog_pr_*_<P>); phase 3 adds Family Limitation to the same machinery.
PRACTICES = ("lm", "bs")
PRACTICE_CUT = {"lm": 0.30, "bs": 0.35}
# Birth Spacing's start for India: the share that cancels the wealth curve's raise, (1 - 1/s) / cut (spec 2.2, "held,
# not history"): 0.37 at s 1.15 and the approved cut of 0.35 (the spec's 0.38 is the same rule at its 0.34). India's
# excess is early mortality, calibration step 3's (owner, 2026-10-11). Task 6 sets it from the fitted s and cut.
BS_HELD_START = 0.37
# Birth Spacing's start for China, Manchuria and Korea (owner, 2026-10-11; plan D13): at least the share that cancels the
# raise, and above it as far as China's peacetime births less deaths needs to land in history's +3 to +6, which lowers
# their births toward history's ~5.5 children per woman (spec 2.2's second variant). Starts at the cancel share; Task 6
# sets it. Membership, not the value, says which states take it (demographics_model.bs_held_group).
BS_EAST_ASIA_START = 0.37
BS_EAST_ASIA_REGIONS = ("region_north_china", "region_south_china")
BS_INDIA_REGIONS = ("region_north_india", "region_south_india")
_OCCITANIA = ("STATE_PROVENCE", "STATE_GUYENNE", "STATE_LANGUEDOC", "STATE_AQUITAINE", "STATE_RHONE", "STATE_SAVOY",
              "STATE_AUVERGNE_LIMOUSIN")
_NW_IBERIA = ("STATE_GALICIA", "STATE_ASTURIAS", "STATE_BASQUE_COUNTRY", "STATE_LEON", "STATE_OLD_CASTILE",
              "STATE_ENTRE_DOURO_E_MINHO", "STATE_BEIRA", "STATE_ESTREMADURA", "STATE_AZORES", "STATE_MADEIRA")
_IBERIA = ("STATE_CATALONIA", "STATE_BALEARIC_ISLANDS", "STATE_ARAGON", "STATE_LOWER_ANDALUSIA", "STATE_ALENTEJO",
           "STATE_EXTREMADURA", "STATE_NEW_CASTILE", "STATE_UPPER_ANDALUSIA", "STATE_VALENCIA", "STATE_MURCIA",
           "STATE_CANARY_ISLANDS")
_ITALY = ("STATE_PIEDMONT", "STATE_EMILIA", "STATE_TUSCANY", "STATE_LAZIO", "STATE_CAMPANIA", "STATE_CALABRIA",
          "STATE_SICILY", "STATE_SARDINIA", "STATE_MALTA", "STATE_CORSICA", "STATE_UMBRIA", "STATE_APULIA",
          "STATE_ABRUZZO", "STATE_ROMAGNA", "STATE_VENETIA", "STATE_ISTRIA", "STATE_LOMBARDY", "STATE_SOUTH_TYROL")
_WEST_OF_THE_LINE = ("STATE_COURLAND", "STATE_TARTU", "STATE_RIGA", "STATE_TALINN", "STATE_EAST_PRUSSIA",
                     "STATE_WEST_PRUSSIA", "STATE_POSEN", "STATE_GREATER_POLAND", "STATE_SLOVENIA")
_THE_GRADIENT = ("STATE_MAZOVIA", "STATE_LESSER_POLAND", "STATE_WEST_GALICIA", "STATE_KAUNAS", "STATE_VILNIUS",
                 "STATE_CROATIA", "STATE_TRANSDANUBIA", "STATE_SLOVAKIA")
_JAPAN = ("STATE_HOKKAIDO", "STATE_TOHOKU", "STATE_KANTO", "STATE_HOKUSHINETSU", "STATE_TOKAI", "STATE_KYOTO",
          "STATE_KANSAI", "STATE_CHUGOKU", "STATE_SHIKOKU", "STATE_KYUSHU")
BS_EAST_ASIA_STATES = ("STATE_SOUTHERN_MANCHURIA", "STATE_NORTHERN_MANCHURIA", "STATE_SHENGJING", "STATE_SEOUL",
                       "STATE_BUSAN", "STATE_SARIWON", "STATE_PYONGYANG", "STATE_YANGHO")   # Manchuria and Korea
# Start shares (spec 3.2, 3.3): by strategic region, then by state region, which wins. Geography, not culture. Malta and
# Corsica take Italy's (the vanilla file's Italy group); Cape Verde, an African archipelago, stays at 0 (plan D10).
PRACTICE_START_REGION = {
    "lm": {"region_western_europe": 1.0, "region_northern_europe": 1.0, "region_central_europe": 1.0},
    "bs": {**dict.fromkeys(BS_EAST_ASIA_REGIONS, BS_EAST_ASIA_START), **dict.fromkeys(BS_INDIA_REGIONS, BS_HELD_START)},
}
PRACTICE_START_STATE = {
    "lm": {**dict.fromkeys(("STATE_KOLA", "STATE_EAST_KARELIA"), 0.2), **dict.fromkeys(_OCCITANIA, 1.0),
           **dict.fromkeys(_NW_IBERIA, 0.9), **dict.fromkeys(_IBERIA, 0.6), **dict.fromkeys(_ITALY, 0.5),
           **dict.fromkeys(_WEST_OF_THE_LINE, 0.8), **dict.fromkeys(_THE_GRADIENT, 0.4)},
    "bs": {**dict.fromkeys(_JAPAN, 1.0), **dict.fromkeys(BS_EAST_ASIA_STATES, BS_EAST_ASIA_START)},
}
# The yearly drift (spec 4.2, 4.3): share += PRACTICE_RATE x (target - share), a generation's half-life. The neighbour
# spread is phase 3's (plan D6). target = start x (1 - erosion), plus Late Marriage's drivers, within 0-1.
PRACTICE_RATE = 0.025
# Erosion by contraception (calls 5, 6): the means beyond traditional methods, state_contraception_add x (0.3 + 0.7 x
# literacy), from 0 at 0.1 to full at 0.3.
PRACTICE_EROSION_CONTRACEPTION = 0.7
PRACTICE_EROSION_FROM = 0.1
PRACTICE_EROSION_SPAN = 0.2
# Erosion by health care (call 5, Birth Spacing only): state_health_care_access_add, full at 0.5, standing in for the
# state that registers births and licenses midwives (the Meiji rise).
PRACTICE_EROSION_ACCESS = {"lm": 0.0, "bs": 0.3}
PRACTICE_ACCESS_SPAN = 0.5
# Late Marriage's drivers (call 6): impartible inheritance x the agrarian share; women's paid work before marriage,
# x the women's job share x the law's women's work share / FULL_FEMALE_WORK_SHARE.
LM_INHERITANCE = 0.15
LM_WOMENS_WORK = 0.3
IMPARTIBLE_LAWS = ("law_primogeniture",)   # and Undivided Farm Succession (te_inh_has_undivided_farms), script only
# The panel (spec 5.3): women's mean age at first marriage, about 19 + 7 x the Late Marriage share.
MARRIAGE_AGE_AT_ZERO, MARRIAGE_AGE_SPAN = 19, 7
```

`FULL_FEMALE_WORK_SHARE` is defined further down the file; `LM_WOMENS_WORK` doesn't read it at import, so the order is
fine.

- [x] **Step 4: The model** (`demographics_model.py`)

Add to `Inputs`, after `medicine` (its last field since #916; every caller builds `Inputs` by keyword):

```python
    practices: dict = field(default_factory=dict)   # {practice: share 0-1}: lm Late Marriage, bs Birth Spacing
    agrarian_share: float = 0.0          # Peasants and Farmers over the state's people (the walk's te_dg_agr_share)
    impartible: bool = False             # the owner holds Primogeniture or Undivided Farm Succession
```

Replace `fertility`'s docstring and its last two statements:

```python
def fertility(inp, e0):
    """Children per woman and its terms (§2.3): wealth x natural x the practices x (1 - means x (1 - desired)).
    Natural fertility is women's legal standing (phase 2 step 4, Task 7), 1 + its type, at least
    NATURAL_FERTILITY_FLOOR. Each practice (the late-marriage spec §2.1) multiplies by 1 - its cut x its share, outside
    the means; a practice with no share is 1."""
    wealth = inp.wealth_tfr if inp.wealth_tfr is not None else wealth_tfr(inp.sol)
    natural = max(P.NATURAL_FERTILITY_FLOOR, 1 + inp.mods.get(P.NATURAL_FERTILITY_TYPE, 0.0))
    education = 1 - P.EDUCATION_WEIGHT * inp.literacy
    survival = 1 - P.SURVIVAL_WEIGHT * clamp((e0 - 30) / 50, 0.0, 1.0)
    urban = 1 - P.URBAN_WEIGHT * inp.urban_share
    desired = education * survival * urban
    mn = means(inp)
    factor = 1 - mn * (1 - desired)
    practices = {p: 1 - cut * inp.practices.get(p, 0.0) for p, cut in P.PRACTICE_CUT.items()}
    tfr = wealth * natural * factor
    for term in practices.values():
        tfr *= term
    return {"tfr": tfr, "wealth": wealth, "natural": natural, "education": education,
            "survival": survival, "urban": urban, "means": mn, "factor": factor, **practices}
```

Add after `fertility`:

```python
# ---- Late Marriage and Birth Spacing (the late-marriage spec §3-§4; te_demog_practice_effects.txt) --------------

def practice_start(practice, state_region, strategic_region):
    """A state's start share (§3.2, §3.3): its state region's entry, else its strategic region's, else 0
    (te_demog_pr_start_<P>, generated)."""
    by_state = P.PRACTICE_START_STATE[practice]
    if state_region in by_state:
        return by_state[state_region]
    return P.PRACTICE_START_REGION[practice].get(strategic_region, 0.0)


def bs_held_group(state_region, strategic_region):
    """Which held Birth Spacing share a state takes (the plan's D13): "east_asia" (China, Manchuria, Korea), "india", or
    None (Japan's full share, or none)."""
    if strategic_region in P.BS_EAST_ASIA_REGIONS or state_region in P.BS_EAST_ASIA_STATES:
        return "east_asia"
    if strategic_region in P.BS_INDIA_REGIONS:
        return "india"
    return None


def contraception_beyond(inp):
    """The means beyond traditional methods: the techs' contraception x access by literacy (§4.2)."""
    return inp.mods.get(P.CONTRACEPTION_TYPE, 0.0) * (P.MEANS_ACCESS_BASE + (1 - P.MEANS_ACCESS_BASE) * inp.literacy)


def practice_erosion(practice, inp):
    """How much of the start the state's conditions take away, 0-1 (§4.2, §4.3)."""
    contra = P.PRACTICE_EROSION_CONTRACEPTION * clamp(
        (contraception_beyond(inp) - P.PRACTICE_EROSION_FROM) / P.PRACTICE_EROSION_SPAN, 0.0, 1.0)
    access = P.PRACTICE_EROSION_ACCESS[practice] * clamp(inp.mods.get(P.ACCESS_TYPE, 0.0) / P.PRACTICE_ACCESS_SPAN,
                                                          0.0, 1.0)
    return clamp(contra + access, 0.0, 1.0)


def practice_target(practice, inp, start):
    """Where a practice's share drifts (§4.2, §4.3; te_demog_pr_target_<P>): the start less its erosion, plus Late
    Marriage's drivers, impartible inheritance on the farms and women's paid work, within 0-1."""
    target = start * (1 - practice_erosion(practice, inp))
    if practice == "lm":
        if inp.impartible:
            target += P.LM_INHERITANCE * inp.agrarian_share
        target += P.LM_WOMENS_WORK * inp.female_job_share * female_work_share(inp) / P.FULL_FEMALE_WORK_SHARE
    return clamp(target, 0.0, 1.0)


def practice_drift(share, target):
    """One year's drift (§4.2): PRACTICE_RATE of the gap. The neighbour spread is phase 3's (the plan's D6)."""
    return clamp(share + P.PRACTICE_RATE * (target - share), 0.0, 1.0)


def practice_seed(practice, inp, start, siblings=()):
    """A state with no share (§3.4; the plan's D5): the people-weighted mean of the other states in its state region
    that hold one, else its start less what its conditions have already eroded, start x (1 - erosion) (te_demog_pr_seed
    _<P>). In 1836 nothing has eroded anywhere a practice starts (no contraception before era 3; no health law in Japan,
    China, Korea or India), so a new game seeds the table. An old save or a rule switched on mid-game seeds near where
    the drift would have taken it, not at the 1836 custom (review I2). The drivers stay out, so Japan's Late Marriage
    starts at 0 (call 3). siblings: [(people, share)]."""
    held = [(p, s) for p, s in siblings if p > 0]
    people = sum(p for p, _s in held)
    if people > 0:
        return sum(p * s for p, s in held) / people
    return start * (1 - practice_erosion(practice, inp))


def marriage_age(share):
    """Women's mean age at first marriage the panel shows (§5.3): 19 with no Late Marriage, 26 at a full share."""
    return P.MARRIAGE_AGE_AT_ZERO + P.MARRIAGE_AGE_SPAN * share
```

- [x] **Step 5: Run the model's tests and the suites that call `fertility`**

Run:
```bash
$V -m unittest test_demographics_model test_demographics_harness test_demographics_registry > /tmp/claude-1000/t2.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t2.txt
```
Expected: `OK`. No `Inputs` sets a practice yet, so every existing figure is unchanged.

- [x] **Step 6: Commit**

```bash
git add scripts/analysis/demographics_params.py scripts/analysis/demographics_model.py test_demographics_model.py
git commit -m "Demographics model: Late Marriage and Birth Spacing, the terms and the practices' arithmetic"
```

---

### Task 3: The harness reads the practices' inputs from a save

**Files:**
- Modify: `scripts/analysis/demographics_save_inputs.py` (`CountryInputs`, `_add_pop`, a new `state_regions`)
- Create: `scripts/analysis/demographics_practices.py`
- Modify: `scripts/analysis/demographics_harness.py` (`inputs_for`, `country_figures`, `history_rows`, `cmd_history`,
  the `history` parser)
- Test: `test_demographics_save_inputs.py`, `test_demographics_practices.py` (create), `test_demographics_harness.py`

**Interfaces:**
- Consumes: Task 1's `R.strategic_region_of()`; Task 2's `M.practice_start`, `Inputs.practices`, `.agrarian_share`,
  `.impartible`.
- Produces: `CountryInputs.agrarian: float`, `CountryInputs.agrarian_share` (property);
  `S.state_regions(sections) -> {state id: "STATE_X"}`; `DP.PracticeState(sid, tag, state_region, strategic_region,
  people, incorporated, inp)`; `DP.read_save(path) -> (sections, state variables)` (the parse, which the fit
  caches); `DP.practice_states(path, carriers, regions=None, save=None) -> [PracticeState]`;
  `DP.table_shares(states) -> {sid: {practice: share}}`; `DP.read_shares(path) -> {year: {sid: {practice: share}}}`;
  `H.inputs_for(c, carriers=None, incorporated=True, practices=None)`; `H.country_figures(states, carriers,
  stored=None, shares=None, incorporated_only=False)`; `H.history_rows(sections, year, anchors, carriers=None,
  stored=None, shares=None, incorporated_only=False, practices=True)` where `shares` is `{sid: {practice: share}}`
  (`stored` is #916's, kept).
  Every state the shares don't hold takes its seed (its start less what its conditions eroded); `practices=False` is
  today's model.

- [x] **Step 1: Write the failing tests**

In `test_demographics_save_inputs.py` (beside `test_state_inputs_split_the_country_by_state`):

```python
    def test_agrarian_share_counts_peasants_and_farmers(self):
        # the walk's te_dg_agr_share (Late Marriage's inheritance driver): Peasants and Farmers, not Slaves
        c = S.CountryInputs("TST")
        for kind, size in (("peasants", 300.0), ("farmers", 100.0), ("slaves", 200.0), ("laborers", 400.0)):
            S._add_pop(c, {"type": kind}, size, True)
        self.assertAlmostEqual(c.agrarian_share, 0.4)
        self.assertEqual(S.CountryInputs("EMPTY").agrarian_share, 0.0)

    def test_state_regions(self):
        sections = {"states": {"1": {"region": '"STATE_TEST"'}, "2": {}}}
        self.assertEqual(S.state_regions(sections), {"1": "STATE_TEST"})
```

Create `test_demographics_practices.py`:

```python
"""scripts/analysis/demographics_practices.py: Late Marriage and Birth Spacing in the harness
(docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md, Tasks 3-5)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_practices as DP  # noqa: E402


def _state(sid, state_region, strategic_region, people=1000.0, tag="TST", incorporated=True, **inp):
    return DP.PracticeState(sid, tag, state_region, strategic_region, people, incorporated, M.Inputs(**inp))


class TestInputs(unittest.TestCase):
    def test_table_shares_are_each_states_start(self):
        states = [_state("1", "STATE_POSEN", "region_eastern_europe"), _state("2", "STATE_KANTO", "region_northeast_asia"),
                  _state("3", "STATE_UNKNOWN", "")]
        got = DP.table_shares(states)
        self.assertEqual(got["1"], {"lm": 0.8, "bs": 0.0})
        self.assertEqual(got["2"], {"lm": 0.0, "bs": 1.0})
        self.assertEqual(got["3"], {"lm": 0.0, "bs": 0.0})

    def test_read_shares_round_trips_the_replays_file(self):
        data = {"1837": {"1": {"lm": 1.0, "bs": 0.0, "people": 5.0, "state_region": "STATE_X",
                               "strategic_region": "region_x", "target_lm": 1.0, "target_bs": 0.0}}}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(data, fh)
        try:
            self.assertEqual(DP.read_shares(fh.name), {1837: {"1": {"lm": 1.0, "bs": 0.0}}})
        finally:
            Path(fh.name).unlink()
```

In `test_demographics_harness.py` (beside `test_history_takes_each_states_own_rates`):

```python
    def test_history_takes_each_states_practices(self):
        """The late-marriage plan, Task 3: a state's shares multiply its children per woman, and a country's figure
        can leave its colonies out (spec 5.1 item 3: Denmark's West African states)."""
        carriers = DM.load_carriers()

        def state(people):
            c = S.CountryInputs("TST")
            c.population, c.sol_x_size, c.wealth_tfr_x_size = people, 8.0 * people, M.wealth_tfr(8.0) * people
            c.workforce, c.literate = people / 2, people / 10
            return c

        states = [("1", state(1000.0), True), ("2", state(1000.0), False)]
        plain = H.country_figures(states, carriers)
        late = H.country_figures(states, carriers, shares={"1": {"lm": 1.0}, "2": {"lm": 1.0}})
        self.assertAlmostEqual(late["tfr"], plain["tfr"] * (1 - P.PRACTICE_CUT["lm"]), places=6)
        home = H.country_figures(states, carriers, shares={"1": {"lm": 1.0}}, incorporated_only=True)
        self.assertAlmostEqual(home["tfr"], H.model_figures(H.inputs_for(states[0][1], carriers,
                                                                         practices={"lm": 1.0}))["tfr"], places=6)
```

Add `import demographics_params as P` to the harness test's imports if it isn't there.

- [x] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_save_inputs test_demographics_practices test_demographics_harness`
Expected: FAIL (`agrarian_share`, `state_regions`, `demographics_practices`, `country_figures(shares=…)` missing).

- [x] **Step 3: The save reader**

In `CountryInputs`, after `rural`:

```python
    agrarian: float = 0.0    # Peasants and Farmers (the walk's te_dg_agr_share; Late Marriage's inheritance driver)
```

and a property beside `urban_share`:

```python
    @property
    def agrarian_share(self):
        return self.agrarian / self.population if self.population else 0.0
```

In `_add_pop`, after the `RURAL_TYPES` line:

```python
    if rec.get("type") in AGRARIAN_TYPES:
        c.agrarian += size
```

with `AGRARIAN_TYPES = {"peasants", "farmers"}` beside `RURAL_TYPES`. After `state_pollution`:

```python
def state_regions(sections):
    """{state id: its state region's key} for the states whose record names one (`region="STATE_X"`)."""
    out = {}
    for sid, rec in sections.get("states", {}).items():
        region = rec.get("region", "").strip('"')
        if region:
            out[sid] = region
    return out
```

- [x] **Step 4: `demographics_practices.py`, its first part**

```python
#!/usr/bin/env python3
"""Late Marriage and Birth Spacing in the harness (docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md).

A save's states with what the practices read (their state and strategic regions, people, incorporation and the model's
inputs, with the walk's women's job share where the save holds one), the drift replay over a run's saves (Task 4), the
regional growth table (Task 4) and the fit of the wealth curve's raise, the cuts and step 1's mortality against the
history anchors (Task 5). The subcommands are demographics_harness.py's: practices-replay, practices-fit, regions.
"""

import json
from dataclasses import dataclass, replace

import demographics_harness as H
import demographics_model as M
import demographics_params as P
import demographics_regions as R
import demographics_save_inputs as S


@dataclass
class PracticeState:
    sid: str
    tag: str
    state_region: str
    strategic_region: str
    people: float
    incorporated: bool
    inp: M.Inputs          # the model's inputs with no practice set; the shares come from a replay or the table
    bands: tuple = ()      # its census's people by five-year band, ((women, men), ...), 85+ last; empty with no census


# the census's bands a save holds per state (te_dg_bf<b>, te_dg_bm<b>): the fit's expected deaths (Task 5)
BAND_VARS = tuple(f"te_dg_b{x}{b}" for x in "fm" for b in range(P.BANDS))


def read_save(path):
    """(sections, {state id: {"vars": ...}}) of a plain-text save: the parse (265 MB a save in the normal-speed run),
    which the fit caches by path and re-uses at every grid point."""
    sections = S.read_sections(path)
    _countries, svars = S.read_variables(path, (), ("te_dg_fjob_share", *BAND_VARS, *H.CENSUS_INPUT_VARS))
    return sections, svars


def practice_states(path, carriers, regions=None, save=None):
    """[PracticeState] for every state of a plain-text save that has people (save: read_save's result, if cached).
    The model's inputs are the census's stored ones where the save holds them all (H.census_inputs, as `history`
    reads them since #916), else the save's techs, laws and modifiers. The women's job share is the walk's
    te_dg_fjob_share where the save holds it (a game with the census running), else 0; Undivided Farm Succession
    isn't read from saves, so only Primogeniture counts as impartible here (the script reads both)."""
    regions = R.strategic_region_of() if regions is None else regions
    sections, svars = read_save(path) if save is None else save
    state_region = S.state_regions(sections)
    out = []
    for tag, sts in S.state_inputs(sections).items():
        for sid, st, inc in sts:
            v = svars.get(sid, {}).get("vars", {})
            inp = replace(H.census_inputs(H.inputs_for(st, carriers, incorporated=inc), v),
                          agrarian_share=st.agrarian_share, female_job_share=v.get("te_dg_fjob_share", 0.0),
                          impartible=bool(set(P.IMPARTIBLE_LAWS) & st.laws))
            bands = tuple((v.get(f"te_dg_bf{b}", 0.0), v.get(f"te_dg_bm{b}", 0.0)) for b in range(P.BANDS))
            sr = state_region.get(sid, "")
            out.append(PracticeState(sid, tag, sr, regions.get(sr, ""), st.population, inc, inp, bands))
    return out


def table_shares(states):
    """{sid: {practice: share}}: what the census's seed gives each state with no sibling holding a share, its start
    less what its conditions have eroded (the 1836 table in a new game)."""
    return {s.sid: {p: M.practice_seed(p, s.inp, M.practice_start(p, s.state_region, s.strategic_region), [])
                    for p in P.PRACTICES} for s in states}


def read_shares(path):
    """{year: {sid: {practice: share}}} from practices-replay's --out file."""
    data = json.loads(open(path, encoding="utf-8").read())
    return {int(year): {sid: {p: rec[p] for p in P.PRACTICES} for sid, rec in by_sid.items()}
            for year, by_sid in data.items()}
```

- [x] **Step 5: The harness takes shares** (`demographics_harness.py`)

`inputs_for` gains `practices=None` and passes `practices=dict(practices or {})` into `M.Inputs`.
`country_figures` keeps #916's `stored` (the census's stored inputs, `census_inputs`) and becomes:

```python
def country_figures(states, carriers, stored=None, shares=None, incorporated_only=False):
    """A country's model figures as the census builds them: each state's own rates (its SoL, literacy,
    urban share and incorporation; with `stored`, {state id: {variable: value}}, the census's own inputs from the
    save, so medicine as it had spread), weighted by its people. The poverty term bends at SoL 9, so the
    rates at the country's mean SoL would hide what its poor and rich states do (#855's review). shares:
    {state id: {practice: share}} (the late-marriage plan); incorporated_only leaves a country's colonies out
    (spec 5.1 item 3)."""
    stored, shares = stored or {}, shares or {}
    figs = [(st.population, model_figures(census_inputs(inputs_for(st, carriers, incorporated=inc,
                                                                   practices=shares.get(sid)),
                                                        stored.get(sid, {}))))
            for sid, st, inc in states if st.population > 0 and (inc or not incorporated_only)]
    tot = sum(p for p, _ in figs) or 1
    return {k: sum(p * f[k] for p, f in figs) / tot for k in ("e0", "imr", "tfr", "r")}
```

Add `import demographics_regions as R  # noqa: E402` to the harness's imports (it imports nothing of the harness's).
`history_rows(sections, year, anchors, carriers=None, stored=None, shares=None, incorporated_only=False,
practices=True)` (`stored` as since #916): every
state takes its seed, as the census gives it with no sibling holding a share, and `shares` overrides the states it
holds (a replay's year). So a state the file lacks still gets its practices (review minor):

```python
    if not practices:
        shares = {}
    else:
        regions, sr = R.strategic_region_of(), S.state_regions(sections)

        def seed(sid, st, inc):
            reg = sr.get(sid, "")
            inp = inputs_for(st, carriers, incorporated=inc)
            return {p: M.practice_seed(p, inp, M.practice_start(p, reg, regions.get(reg, "")), [])
                    for p in P.PRACTICES}

        shares = {**{sid: seed(sid, st, inc) for sts in states.values() for sid, st, inc in sts}, **(shares or {})}
```

Pass `stored` and `shares` to every `country_figures` call, and `incorporated_only` to the countries' (the world line
keeps every state). In `cmd_history` (which keeps reading `CENSUS_INPUT_VARS` into `stored`), add three options to the
`history` subparser:
- `--shares FILE`: practices-replay's output; the save's year selects its shares, and a state or a year the file
  doesn't hold falls back to the seed;
- `--incorporated-only`: print `(incorporated states only)` on the `==` line when it is set;
- `--no-practices`: pass `practices=False`, for today's model (Task 6's "before").

- [x] **Step 6: Run the tests**

Run:
```bash
$V -m unittest test_demographics_save_inputs test_demographics_practices test_demographics_harness > /tmp/claude-1000/t3.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t3.txt
```
Expected: `OK`. `test_history_on_the_slice` still passes: the slice names no region, so every state takes 0.

- [x] **Step 7: Commit**

```bash
git add scripts/analysis/demographics_save_inputs.py scripts/analysis/demographics_practices.py scripts/analysis/demographics_harness.py test_demographics_save_inputs.py test_demographics_practices.py test_demographics_harness.py
git commit -m "Demographics harness: each state's practices from a save; history takes shares and an incorporated filter"
```

---

### Task 4: The drift replay

**Files:**
- Modify: `scripts/analysis/demographics_practices.py` (`replay`, `replay_gate`, `replay_moves`)
- Modify: `scripts/analysis/demographics_harness.py` (subcommand `practices-replay`)
- Test: `test_demographics_practices.py`

**Interfaces:**
- Consumes: Task 3's `practice_states` and `PracticeState`; Task 2's `M.practice_seed(practice, inp, start, siblings)`.
- Produces:
  - `DP.replay(loaded) -> {year: {sid: record}}`, where `loaded` is `[(year, [PracticeState])]` sorted by year and
    `record` is `{"lm", "bs", "target_lm", "target_bs", "people", "state_region", "strategic_region"}`;
  - `DP.replay_gate(result, upto=1887) -> [str]`, the failures;
  - `DP.replay_moves(result, top=10) -> [(move, practice, sid, state region, start, share, target)]`.

The regional growth table is Task 5's: it projects #904's peacetime rates, so it needs the fit's per-state figures.

- [x] **Step 1: Write the failing tests** (append to `test_demographics_practices.py`)

```python
class TestReplay(unittest.TestCase):
    """The drift replay (spec 5.1 item 5): both shares stepped a year at a time through a run's saves."""

    def test_states_seed_from_the_table_in_any_order(self):
        # a Baltic state beside a Russian one: no cascade (the plan's D5), whatever order the states come in
        for order in ((0, 1), (1, 0)):
            states = [_state("1", "STATE_RIGA", "region_eastern_europe"), _state("2", "STATE_PSKOV", "region_russia")]
            got = DP.replay([(1837, [states[i] for i in order])])
            self.assertEqual((got[1837]["1"]["lm"], got[1837]["2"]["lm"]), (0.8, 0.0), order)

    def test_a_new_state_takes_its_siblings_share(self):
        first = [_state("1", "STATE_POSEN", "region_eastern_europe", people=3000.0,
                        mods={P.CONTRACEPTION_TYPE: 1.0}, literacy=1.0)]
        later = first + [_state("2", "STATE_POSEN", "region_eastern_europe", people=1000.0)]
        got = DP.replay([(1837, first), (1897, later)])
        sibling, split = got[1897]["1"]["lm"], got[1897]["2"]["lm"]
        self.assertLess(sibling, 0.5, "Posen drifted down with contraception")
        # the split seeds from its sibling's drifted share, then takes one step at its own conditions (no contraception)
        self.assertAlmostEqual(split, sibling, delta=0.05)
        self.assertLess(split, 0.8, "not the 1836 table")

    def test_a_state_seeded_late_with_no_sibling_starts_eroded(self):
        """Review I2: a state that first appears in a late save, with no sibling holding a share, seeds at its start
        less what its conditions have eroded, not at the 1836 custom."""
        late = _state("1", "STATE_KANTO", "region_northeast_asia", literacy=1.0,
                      mods={P.CONTRACEPTION_TYPE: 1.0, P.ACCESS_TYPE: 1.0})
        got = DP.replay([(1950, [late])])
        self.assertEqual(got[1950]["1"]["bs"], 0.0)

    def test_years_between_saves_take_the_earlier_saves_conditions(self):
        before = _state("1", "STATE_KANTO", "region_northeast_asia")
        after = replace(before, inp=replace(before.inp, mods={P.ACCESS_TYPE: 0.5}))
        got = DP.replay([(1837, [before]), (1847, [after])])
        target = M.practice_target("bs", after.inp, 1.0)
        # nine steps at 1837's conditions (target 1: no move), then the 1847 step at 1847's
        self.assertAlmostEqual(got[1847]["1"]["bs"], M.practice_drift(1.0, target), places=9)
        self.assertAlmostEqual(got[1847]["1"]["target_bs"], target, places=9)

    def test_the_gate(self):
        west = _state("1", "STATE_HOME_COUNTIES", "region_western_europe", people=5e6)
        japan = _state("2", "STATE_KANTO", "region_northeast_asia", people=5e6)
        ok = DP.replay([(1837, [west, japan]), (1887, [west, japan])])
        self.assertEqual(DP.replay_gate(ok), [])
        # Japan's spacing eroding from 1837 on (contraception and health care held from the first save): the 1887 save
        # reads it well below its start. Seeded with the conditions already in place it would start eroded, so the
        # first save holds Japan as it was and the eroding conditions come in at the second.
        eroded = replace(japan, inp=replace(japan.inp, mods={P.ACCESS_TYPE: 0.5, P.CONTRACEPTION_TYPE: 1.0},
                                            literacy=1.0))
        bad = DP.replay([(1837, [west, japan]), (1838, [west, eroded]), (1887, [west, eroded])])
        self.assertTrue(any("East Asia" in line for line in DP.replay_gate(bad)))
```

Add `from dataclasses import replace` to the test file's imports.

- [x] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_practices.TestReplay`
Expected: FAIL (`DP.replay` missing).

- [x] **Step 3: Write the replay** (append to `demographics_practices.py`)

```python
# ---- the drift replay (spec 5.1 item 5) ---------------------------------------------------------------------

def _seed(shares, states):
    """te_demog_practice_seed: a state with no share takes its siblings' people-weighted mean (the states in its state
    region that hold one), else its start less what its conditions have eroded. Siblings share a start, so in a new
    game the order doesn't matter (the plan's D5)."""
    by_region = {}
    for s in states:
        by_region.setdefault(s.state_region, []).append(s)
    for s in states:
        if s.sid in shares:
            continue
        sibs = [x for x in by_region[s.state_region] if x.sid in shares]
        shares[s.sid] = {p: M.practice_seed(p, s.inp, M.practice_start(p, s.state_region, s.strategic_region),
                                            [(x.people, shares[x.sid][p]) for x in sibs]) for p in P.PRACTICES}


def _step(shares, states):
    """te_demog_practice_step for every state: a year's drift toward its target at these conditions."""
    for s in states:
        for p in P.PRACTICES:
            start = M.practice_start(p, s.state_region, s.strategic_region)
            shares[s.sid][p] = M.practice_drift(shares[s.sid][p], M.practice_target(p, s.inp, start))


def replay(loaded):
    """{year: {sid: record}} for each save in `loaded` ([(year, [PracticeState])], sorted): every state seeds at the
    first save that holds it, then the census steps once a year, each year with the conditions of the latest save at
    or before it (so the years between two saves take the earlier one's, and a save's own year takes its own). A
    record holds the shares, their targets at that save's conditions, the state's people and its regions."""
    shares, out, prev = {}, {}, None
    for year, states in loaded:
        if prev is not None:
            prev_year, prev_states = prev
            for _ in range(year - prev_year - 1):
                _step(shares, prev_states)
        _seed(shares, states)
        if prev is not None:
            _step(shares, states)
        out[year] = {}
        for s in states:
            rec = {p: shares[s.sid][p] for p in P.PRACTICES}
            for p in P.PRACTICES:
                rec[f"target_{p}"] = M.practice_target(p, s.inp, M.practice_start(p, s.state_region,
                                                                                    s.strategic_region))
            rec.update(people=s.people, state_region=s.state_region, strategic_region=s.strategic_region)
            out[year][s.sid] = rec
        prev = (year, states)
    return out


WEST = frozenset({"region_western_europe", "region_northern_europe", "region_central_europe"})
EAST_ASIA_BS = (("Japan", lambda r: P.PRACTICE_START_STATE["bs"].get(r["state_region"]) == 1.0),
                ("China, Manchuria, Korea", lambda r: M.bs_held_group(r["state_region"], r["strategic_region"])
                 == "east_asia"))


def _mean(records, key, keep):
    held = [(r["people"], r[key]) for r in records if keep(r) and r["people"] > 0]
    people = sum(p for p, _v in held)
    return sum(p * v for p, v in held) / people if people else None


def replay_gate(result, upto=1887):
    """Spec 5.2's replay items: the West's Late Marriage at 0.8 or more, and East Asia's Birth Spacing within 0.1 of
    its start, at every save up to `upto`. Returns the failures as lines."""
    fails = []
    for year, recs in sorted(result.items()):
        if year > upto:
            continue
        west = _mean(recs.values(), "lm", lambda r: r["strategic_region"] in WEST)
        if west is not None and west < 0.8:
            fails.append(f"{year}: the West's Late Marriage {west:.2f} (at least 0.8)")
        for label, keep in EAST_ASIA_BS:
            got = _mean(recs.values(), "bs", keep)
            start = _mean([dict(r, start=M.practice_start("bs", r["state_region"], r["strategic_region"]))
                           for r in recs.values()], "start", keep)
            if got is not None and abs(got - start) > 0.1:
                fails.append(f"{year}: East Asia's Birth Spacing, {label}, {got:.2f} against its start {start:.2f}")
    return fails


def replay_moves(result, top=10):
    """The states whose shares moved most from their start by the last save: [(move, practice, sid, state region,
    start, share, target)], largest first. Phase 2 has no spread, so every move is the state's own conditions."""
    year = max(result)
    rows = []
    for sid, r in result[year].items():
        for p in P.PRACTICES:
            start = M.practice_start(p, r["state_region"], r["strategic_region"])
            rows.append((abs(r[p] - start), p, sid, r["state_region"], start, r[p], r[f"target_{p}"]))
    return sorted(rows, reverse=True)[:top]
```

- [x] **Step 4: The subcommand** (`demographics_harness.py`; it imports `demographics_practices as DP` inside the
  function, since that module imports this one)

```python
def cmd_practices_replay(args):
    import demographics_practices as DP
    carriers = DM.load_carriers()
    loaded = sorted(((save_year(p) or args.year, DP.practice_states(p, carriers)) for p in args.save),
                    key=lambda pair: pair[0])
    result = DP.replay(loaded)
    for year, recs in sorted(result.items()):
        west = DP._mean(recs.values(), "lm", lambda r: r["strategic_region"] in DP.WEST)
        parts = [f"West's Late Marriage {west:.2f}" if west is not None else "no Western state"]
        for label, keep in DP.EAST_ASIA_BS:
            got = DP._mean(recs.values(), "bs", keep)
            parts.append(f"{label}'s Birth Spacing {got:.2f}" if got is not None else f"no {label}")
        print(f"{year}: " + "; ".join(parts))
    print("largest moves from the start (practice, state region, start -> share, target):")
    for move, p, _sid, sr, start, share, target in DP.replay_moves(result):
        print(f"  {move:.2f}  {p} {sr:28s} {start:.2f} -> {share:.2f}  target {target:.2f}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({str(y): r for y, r in result.items()}, fh, indent=1, sort_keys=True)
    fails = DP.replay_gate(result)
    for line in fails:
        print("GATE " + line)
    return 1 if fails else 0
```

Parser: `practices-replay SAVE... [--out FILE] [--year Y]`.

- [x] **Step 5: Run the tests**

Run: `$V -m unittest test_demographics_practices test_demographics_harness`
Expected: `OK`.

- [x] **Step 6: Commit**

```bash
git add scripts/analysis/demographics_practices.py scripts/analysis/demographics_harness.py test_demographics_practices.py
git commit -m "Demographics harness: the practices' drift replay"
```

---

### Task 5: The joint fit, the regional projection and the gate

**Files:**
- Modify: `scripts/analysis/demographics_practices.py`:
  - `FitState`, `fit_states`, `tfr_at`, `band_deaths`;
  - `evaluate`, `fit_table`;
  - `project_regions`, `region_gate`;
  - `patch_params`, `mortality_report`.
- Modify: `scripts/analysis/demographics_harness.py` (`PRACTICE_SCENARIOS`; `fertility_rows(carriers=None,
  scenarios=None)`; subcommand `practices-fit`)
- Test: `test_demographics_practices.py`, `test_demographics_harness.py`

**Interfaces:**
- Consumes:
  - Task 1's `R.REPORT_REGIONS` (#904's groups and their "normal years" bands);
  - Task 3's `practice_states`, `read_save`, `PracticeState.bands`, `read_shares`;
  - `H.HISTORY_TAGS`, `H.read_anchors`, `H.nearest`, `H.medicine_rows`.
- Produces:
  - `DP.FitState(sid, country, tag, people, incorporated, base_tfr, nrr_per_tfr, e0, deaths, lm, bs, held)`, `held`
    being `M.bs_held_group`'s answer;
  - `DP.fit_states(path, carriers, shares, save=None) -> [FitState]`;
  - `DP.tfr_at(state, s, cut_lm, cut_bs, held, east) -> float`;
  - `DP.band_deaths(qf, qm, bands) -> float`;
  - `DP.cancel_share(s, cut_bs) -> float`;
  - `DP.evaluate(fit_by_year, anchors, s, cut_lm, cut_bs, held=None, east=None, years=None) -> dict` with keys
    `error`, `world_tfr`, `countries`, `high`, `held`, `east`;
  - `DP.fit_table(fit_by_year, anchors, s_grid, lm_grid, bs_grid, years=None) -> [(s, cut_lm, cut_bs, result)]`;
  - `DP.project_regions(rows, today, point, s, cut_lm, cut_bs, held=None, east=None) -> {"groups", "world", "tags"}`;
  - `DP.east_for_china(rows, today, point, s, cut_lm, cut_bs, held=None, top=0.9) -> (east, China's projected rate)`;
  - `DP.region_gate(projection, world_margin=1.0, big=2e7) -> [str]`;
  - `DP.patch_params(infection_scale=1.0, **values)` (a context manager);
  - `DP.mortality_report(fit_by_year) -> {country: e0}` (the three Western countries in the first year);
  - `H.PRACTICE_SCENARIOS` (the scenarios with their shares, and two new ones).

**What the gate protects (review C1).** The spec's gate held children per woman to the anchors, and growth only as a
world line within ±0.1% of step 1's. That line passes a world that is regionally worse than today's:
- the raise adds about +6 per 1,000 a year wherever no practice holds (a crude birth rate near 41 × 0.15);
- Late Marriage takes about −7 off western, northern and central Europe;
- so the Middle East and Africa go from +8.8 to about +15 against history's +3 to +8, while the world's births move
  only ×1.005.

So the gate here is regional (owner, 2026-10-11; D12), on #904's measured peacetime births less deaths ("#894's analysis", PR #904's results
doc). A projected rate is #904's measured rate on the same peacetime state-years, with:
- each state-year's births × its children per woman at the fit's point over today's;
- its deaths × the point's expected deaths at the state's own census bands over today's (unchanged unless the
  mortality knobs move).

The gate:
- each of #904's groups inside its band;
- the world at or below today's (+8.8) less about 1 per 1,000: ×1.65 over 1836–1900 needs about that;
- China inside its +3 to +6;
- no country of 20M people or more with projected peacetime births below deaths.

The fit takes the smallest neat raise s for which a neat mortality point passes. Children per woman stays fitted
(the cuts minimise its error at each s, spec §2.3), and the high-fertility group's level is reported, not required.

**The method for the cuts** (spec §2.3, kept):
- For each s, the cuts minimise the root-mean-square error of children per woman over the anchor countries, in the
  fit years (1837 and 1887).
- A country's figure is its incorporated states', weighted by people. The anchor is Gapminder's within 5 years.
- Gapminder's flat guesses (China, Iran, Turkey, Mexico, Peru, Korea) carry half weight (spec §5.2).
- The USA and Chile in 1887 are dropped as fertility transitions (spec §2.3). The Netherlands is no longer dropped: the
  incorporated filter now leaves out the colonies that put it there.
- Two held Birth Spacing shares, each scaling its states' replayed share ÷ their start (`M.bs_held_group`):
  - **India** takes h = (1 − 1/s) ÷ cut_bs, the share that cancels the raise (spec §2.2), and the cuts are fitted with
    China at that share too.
  - **China, Manchuria and Korea** take e, at least h (owner, 2026-10-11; D13). At each point `east_for_china` picks the
    smallest e on a 0.01 grid at which China's projected peacetime births less deaths is at most +6. That lowers their
    births toward history's ~5.5 children per woman.
  - The fit reports China's children per woman at e, flagged below about 5.
  - `--at` can set h and e by hand.

- [x] **Step 1: Write the failing tests** (append to `test_demographics_practices.py`)

```python
def _fit(country, base, lm=0.0, bs=0.0, held=None, people=1e7, e0=35.0, tag="TST", sid="1", deaths=300.0):
    return DP.FitState(sid, country, tag, people, True, base, 0.4, e0, deaths, lm, bs, held)


class TestFit(unittest.TestCase):
    ANCHORS = {"tfr": {"Sweden": {1837: 4.4}, "Iran": {1837: 7.0}, "China": {1837: 5.5}}}

    def test_a_point_scales_the_curve_and_applies_the_cuts(self):
        states = {1837: [_fit("Sweden", 5.5, lm=1.0), _fit("Iran", 6.0)]}
        got = DP.evaluate(states, self.ANCHORS, s=1.15, cut_lm=0.3, cut_bs=0.35)
        self.assertAlmostEqual(got["countries"][("Sweden", 1837)][0], 5.5 * 1.15 * 0.7, places=9)
        self.assertAlmostEqual(got["countries"][("Iran", 1837)][0], 6.0 * 1.15, places=9)
        want = ((5.5 * 1.15 * 0.7 - 4.4) ** 2 + 0.5 * (6.0 * 1.15 - 7.0) ** 2) / 1.5
        self.assertAlmostEqual(got["error"], want ** 0.5, places=9)

    def test_the_held_share_cancels_the_raise(self):
        china = _fit("China", 6.0, bs=P.BS_EAST_ASIA_START, held="east_asia")
        india = _fit("India", 6.0, bs=P.BS_HELD_START, held="india", sid="2", tag="BIC")
        got = DP.evaluate({1837: [china, india]}, self.ANCHORS, s=1.2, cut_lm=0.3, cut_bs=0.4)
        self.assertAlmostEqual(got["held"], (1 - 1 / 1.2) / 0.4, places=9)
        self.assertAlmostEqual(got["east"], got["held"], places=9, msg="East Asia defaults to the cancel share")
        self.assertAlmostEqual(got["countries"][("China", 1837)][0], 6.0, places=9)
        # owner, 2026-10-11 (D13): East Asia's share may sit above it; India's stays
        above = DP.evaluate({1837: [china, india]}, self.ANCHORS, s=1.2, cut_lm=0.3, cut_bs=0.4, east=0.6)
        self.assertAlmostEqual(above["countries"][("China", 1837)][0], 6.0 * 1.2 * (1 - 0.4 * 0.6), places=9)
        self.assertAlmostEqual(above["countries"][("India", 1837)][0], 6.0, places=9)

    def test_the_table_finds_each_raises_best_cuts(self):
        states = {1837: [_fit("Sweden", 5.5, lm=1.0), _fit("Iran", 6.0)]}
        rows = DP.fit_table(states, self.ANCHORS, [1.15], [0.2, 0.3, 0.4], [0.35])
        self.assertEqual(len(rows), 1)
        s, cut_lm, _cut_bs, _res = rows[0]
        # Sweden's 4.4 at 5.5 x 1.15 wants 1 - cut = 0.696: 0.3 is the grid's nearest
        self.assertEqual((s, cut_lm), (1.15, 0.3))

    def test_patch_params_restores(self):
        before = (P.POVERTY_INFECTION_AT_FLOOR, P.INFECTION["f"][0], dict(P.PRACTICE_CUT))
        with DP.patch_params(infection_scale=1.2, POVERTY_INFECTION_AT_FLOOR=2.0, PRACTICE_CUT={"lm": 0.2, "bs": 0.3}):
            self.assertEqual(P.POVERTY_INFECTION_AT_FLOOR, 2.0)
            self.assertAlmostEqual(P.INFECTION["f"][0], before[1] * 1.2)
            self.assertEqual(P.PRACTICE_CUT, {"lm": 0.2, "bs": 0.3})
        self.assertEqual((P.POVERTY_INFECTION_AT_FLOOR, P.INFECTION["f"][0], P.PRACTICE_CUT), before)

    def test_band_deaths(self):
        q = [1000.0] * len(P.GROUPS)
        bands = [(100.0, 50.0)] * P.BANDS
        self.assertAlmostEqual(DP.band_deaths(q, q, bands), P.BANDS * 150.0 * 1000 / 100000)


class TestProjection(unittest.TestCase):
    """Review C1: #904's peacetime births less deaths, projected to a point of the fit, and the regional gate."""

    ROWS = [
        # step year, group, peace, reasons, births, deaths, people, migration, tag, state id
        [1836, "China", True, [], 42.5, 36.0, 1000.0, 0.0, "CHI", "1"],
        [1836, "Middle East, C Asia", True, [], 41.5, 32.7, 1000.0, 0.0, "PER", "2"],
        [1836, "Middle East, C Asia", False, ["war"], 90.0, 10.0, 1000.0, 0.0, "PER", "2"],   # not peacetime
        [1836, "W/N/C/S Europe", True, [], 37.9, 26.8, 1000.0, 0.0, "GBR", "3"],
    ]

    def states(self, deaths=300.0):
        return {1837: [_fit("China", 6.0, bs=P.BS_EAST_ASIA_START, held="east_asia", sid="1", tag="CHI",
                            deaths=deaths),
                       _fit("Iran", 6.0, sid="2", tag="PER", deaths=deaths),
                       _fit("United Kingdom", 5.5, lm=1.0, sid="3", tag="GBR", deaths=deaths)]}

    def test_today_is_the_measured_rate(self):
        today = self.states()
        proj = DP.project_regions(self.ROWS, today, today, s=1.0, cut_lm=0.0, cut_bs=0.35)
        self.assertAlmostEqual(proj["groups"]["China"][1], 6.5, places=9)
        self.assertAlmostEqual(proj["groups"]["Middle East, C Asia"][0], 8.8, places=9, msg="war rows left out")
        self.assertAlmostEqual(proj["world"][0], (6.5 + 8.8 + 11.1) / 3, places=9)

    def test_births_take_the_points_children_per_woman_and_deaths_its_mortality(self):
        today = self.states()
        point = self.states(deaths=330.0)                     # the mortality knobs raised deaths 10% everywhere
        proj = DP.project_regions(self.ROWS, today, point, s=1.15, cut_lm=0.3, cut_bs=0.35)
        self.assertAlmostEqual(proj["groups"]["China"][1], 42.5 * 1.0 - 36.0 * 1.1, places=6, msg="held")
        self.assertAlmostEqual(proj["groups"]["Middle East, C Asia"][1], 41.5 * 1.15 - 32.7 * 1.1, places=6)
        self.assertAlmostEqual(proj["groups"]["W/N/C/S Europe"][1], 37.9 * 1.15 * 0.7 - 26.8 * 1.1, places=6)

    def test_east_asias_share_brings_china_into_its_band(self):
        """Owner, 2026-10-11 (D13): the smallest share on a 0.01 grid, at least the cancel share, at which China's projected
        peacetime births less deaths is at most +6. Here +6.5 at the cancel share; 42.5 x 1.15 x (1 - 0.35 e) - 36 <= 6
        needs e >= 0.402, so 0.41."""
        today = self.states()
        e, rate = DP.east_for_china(self.ROWS, today, today, s=1.15, cut_lm=0.3, cut_bs=0.35)
        self.assertAlmostEqual(e, 0.41, places=9)
        self.assertLessEqual(rate, 6.0)
        # already in band at the cancel share: the cancel share (rounded up to the grid)
        low = [[1836, "China", True, [], 40.0, 36.0, 1000.0, 0.0, "CHI", "1"]]
        e, rate = DP.east_for_china(low, today, today, s=1.15, cut_lm=0.3, cut_bs=0.35)
        self.assertAlmostEqual(e, 0.38, places=9)

    def test_the_gate(self):
        today = self.states()
        proj = DP.project_regions(self.ROWS, today, today, s=1.15, cut_lm=0.3, cut_bs=0.35)
        fails = DP.region_gate(proj)
        self.assertTrue(any(line.startswith("China:") for line in fails), "+6.5 is above China's +3 to +6")
        self.assertTrue(any(line.startswith("Middle East, C Asia:") for line in fails))
        self.assertTrue(any(line.startswith("World:") for line in fails))
        quiet = {"groups": {"China": (6.5, 5.0)}, "world": (8.8, 7.0), "tags": {"CHI": (4e8, 6.5, 5.0)}}
        self.assertEqual(DP.region_gate(quiet), [])
        shrinking = dict(quiet, tags={"CHI": (4e8, 6.5, -0.1)})
        self.assertEqual(len(DP.region_gate(shrinking)), 1)
```

In `test_demographics_harness.py`:

```python
    def test_the_practice_scenarios(self):
        """Spec 5.1 item 4's shares on every fertility scenario, and review I3's two: the 20th century where Birth
        Spacing has eroded and the raise is all that's left."""
        labels = [label for label, _kw, _band in H.PRACTICE_SCENARIOS]
        self.assertEqual(len(labels), len(H.FERTILITY_SCENARIOS) + 2)
        self.assertIn("East Asia 1990", labels)
        self.assertIn("Latin America 1970", labels)
        rows = dict((r[0], r[1]) for r in H.fertility_rows(scenarios=H.PRACTICE_SCENARIOS))
        self.assertAlmostEqual(rows["1836 agrarian, No Women's Rights"], rows["1836 agrarian (reference)"], places=9)
```

- [x] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_practices.TestFit test_demographics_practices.TestProjection`
Expected: FAIL (`DP.FitState` missing).

- [x] **Step 3: Write the fit and the projection** (append to `demographics_practices.py`; add `import contextlib` and
  `import math`)

```python
# ---- the fit (spec 2.3, 5.1 item 6) and the regional projection (review C1) ---------------------------------
FLAT_GUESSES = frozenset({"China", "Iran", "Turkey", "Mexico", "Peru", "Korea"})   # half weight (spec 5.2)
DROPPED = frozenset({("United States", 1887), ("Chile", 1887)})   # fertility transitions (spec 2.3)
HIGH_GROUP = ("Iran", "Turkey", "Russia", "Mexico", "Argentina")  # history's early-marrying, about 7: reported only
WESTERN_E0 = (("United Kingdom", 41.0), ("Sweden", 41.0), ("Denmark", 41.0))   # spec 5.2: within 3 years, 1837


@dataclass
class FitState:
    sid: str
    country: str           # its HISTORY_TAGS name when its owner is the tag history uses, else ""
    tag: str
    people: float
    incorporated: bool
    base_tfr: float        # the model's children per woman with no practice, on the curve as it stands
    nrr_per_tfr: float     # daughters per woman per child per woman: survival to each childbearing age
    e0: float
    deaths: float | None   # expected deaths a year at its census bands (None: the save holds no census here)
    lm: float
    bs: float
    held: str | None       # its held Birth Spacing share: "east_asia" (China, Manchuria, Korea), "india", or None


def band_deaths(qf, qm, bands):
    """Expected deaths a year at a state's census bands (te_dg_bf<b>, te_dg_bm<b>: people by five-year band, 85+
    last) under the model's group rates (per 100,000 a year), each band at the mean of its ages' group rates."""
    total = 0.0
    for b, (women, men) in enumerate(bands):
        ages = range(5 * b, 5 * b + 5) if b < P.BANDS - 1 else range(85, 100)
        rf = sum(qf[P.group_of(a)] for a in ages) / len(ages)
        rm = sum(qm[P.group_of(a)] for a in ages) / len(ages)
        total += (women * rf + men * rm) / 100000
    return total


def fit_states(path, carriers, shares, save=None):
    """[FitState] for one save. shares: {sid: {practice: share}} (a replay's year, or table_shares); save: read_save's
    result, so a grid re-runs the model without re-reading the file. The model reads demographics_params at call time,
    so patch_params and patched carriers reach it."""
    states = practice_states(path, carriers, save=save)
    people = {}
    for s in states:
        people[s.tag] = people.get(s.tag, 0.0) + s.people
    chosen = {}
    for country, tags in H.HISTORY_TAGS.items():
        tag = next((t for t in tags if people.get(t, 0) > 0), None)
        if tag:
            chosen[tag] = country
    out = []
    for s in states:
        if s.people <= 0:
            continue
        qf, qm, _mmr = M.group_rates(s.inp)
        e0 = (M.life_table(qf)["e0"] + M.life_table(qm)["e0"]) / 2
        base = M.fertility(s.inp, e0)["tfr"]
        sh = shares.get(s.sid, {})
        held = M.bs_held_group(s.state_region, s.strategic_region)
        deaths = band_deaths(qf, qm, s.bands) if any(w or m for w, m in s.bands) else None
        out.append(FitState(s.sid, chosen.get(s.tag, ""), s.tag, s.people, s.incorporated, base, M.nrr(1.0, qf), e0,
                            deaths, sh.get("lm", 0.0), sh.get("bs", 0.0), held))
    return out


def tfr_at(st, s, cut_lm, cut_bs, held, east):
    """A state's children per woman at one point: the curve x s, its shares' terms, India's held share (held) or East
    Asia's (east) in place of its start, each scaling its replayed share."""
    bs = st.bs
    if st.held == "india":
        bs = st.bs * held / P.BS_HELD_START
    elif st.held == "east_asia":
        bs = st.bs * east / P.BS_EAST_ASIA_START
    return s * st.base_tfr * (1 - cut_lm * st.lm) * (1 - cut_bs * bs)


def cancel_share(s, cut_bs):
    """The Birth Spacing share that cancels the raise s (spec 2.2): (1 - 1/s) / cut_bs; 0 with no cut."""
    return (1 - 1 / s) / cut_bs if cut_bs else 0.0


def evaluate(fit_by_year, anchors, s, cut_lm, cut_bs, held=None, east=None, years=None):
    """One grid point over {year: [FitState]}: the error over the anchor countries in `years` (default every year), the
    world's children per woman (states of tags with 1M people or more), each anchor country's (model, history), and
    the high group's range in the first year (reported, not judged). held: India's Birth Spacing share, default the
    cancel share (spec 2.2); east: China's, Manchuria's and Korea's, default the same (D13)."""
    h = cancel_share(s, cut_bs) if held is None else held
    e = h if east is None else east
    countries, sq, weights, world_tfr = {}, 0.0, 0.0, {}
    for year, states in sorted(fit_by_year.items()):
        tag_people = {}
        for st in states:
            tag_people[st.tag] = tag_people.get(st.tag, 0.0) + st.people
        acc, wp, wt = {}, 0.0, 0.0
        for st in states:
            tfr = tfr_at(st, s, cut_lm, cut_bs, h, e)
            if tag_people[st.tag] >= 1e6:
                wp, wt = wp + st.people, wt + st.people * tfr
            if st.country and st.incorporated:
                a = acc.setdefault(st.country, [0.0, 0.0])
                a[0], a[1] = a[0] + st.people, a[1] + st.people * tfr
        world_tfr[year] = wt / wp if wp else None
        for country, (p, t) in acc.items():
            hist = H.nearest(anchors.get("tfr", {}).get(country, {}), year, 5)
            countries[(country, year)] = (t / p, hist[1] if hist else None)
            if hist and (country, year) not in DROPPED and (years is None or year in years):
                w = 0.5 if country in FLAT_GUESSES else 1.0
                sq, weights = sq + w * (t / p - hist[1]) ** 2, weights + w
    first = min(fit_by_year)
    high = [countries[(c, first)][0] for c in HIGH_GROUP if (c, first) in countries]
    return {"error": (sq / weights) ** 0.5 if weights else None, "world_tfr": world_tfr, "countries": countries,
            "high": (min(high), max(high)) if high else None, "held": h, "east": e}


def fit_table(fit_by_year, anchors, s_grid, lm_grid, bs_grid, years=None):
    """[(s, cut_lm, cut_bs, result)]: for each raise, the cuts with the least error (spec 2.3's method)."""
    rows = []
    for s in s_grid:
        best = None
        for cut_lm in lm_grid:
            for cut_bs in bs_grid:
                res = evaluate(fit_by_year, anchors, s, cut_lm, cut_bs, years=years)
                if res["error"] is not None and (best is None or res["error"] < best[3]["error"]):
                    best = (s, cut_lm, cut_bs, res)
        if best:
            rows.append(best)
    return rows


def project_regions(rows, today, point, s, cut_lm, cut_bs, held=None, east=None):
    """#904's peacetime births less deaths, projected to one point of the fit (review C1).

    rows: #904's state-years ([step year, group, peace, reasons, births, deaths, people, migration, tag, state id],
    from its analyze.py --json; its peacetime filter is the `peace` flag). today, point: {save year: [FitState]} with
    today's parameters and with the point's (the mortality knobs patched, or the same lists). Each peacetime state-year
    takes the fit save at or before the one that closes it (the step year + 1): births x the point's children per woman
    over today's (no practice, s = 1), deaths x the point's expected deaths at the state's census bands over today's. A
    state the fit saves don't hold keeps its measured rates. Returns, per 1,000 a year, {"groups": {label: (measured,
    projected)}, "world": (measured, projected), "tags": {tag: (people, measured, projected)}}; a tag's people are its
    largest year's peacetime people. held, east: the two held Birth Spacing shares, as evaluate takes them."""
    h = cancel_share(s, cut_bs) if held is None else held
    e = h if east is None else east
    years = sorted(today)
    by_today = {y: {st.sid: st for st in today[y]} for y in years}
    by_point = {y: {st.sid: st for st in point[y]} for y in years}
    acc, tag_year = {}, {}
    for year, group, peace, _why, b, d, p, _mig, tag, sid in rows:
        if not peace or p <= 0:
            continue
        y = max([x for x in years if x <= year + 1] or years[:1])
        t, q = by_today[y].get(sid), by_point[y].get(sid)
        br = dr = 1.0
        if t and q:
            br = tfr_at(q, s, cut_lm, cut_bs, h, e) / t.base_tfr if t.base_tfr else 1.0
            dr = q.deaths / t.deaths if t.deaths and q.deaths else 1.0
        for key in (group, "World", "tag:" + tag):
            a = acc.setdefault(key, [0.0, 0.0, 0.0])
            a[0] += b - d
            a[1] += b * br - d * dr
            a[2] += p
        tag_year[(tag, year)] = tag_year.get((tag, year), 0.0) + p
    size = {}
    for (tag, _y), p in tag_year.items():
        size[tag] = max(size.get(tag, 0.0), p)

    def rate(a):
        return 1000 * a[0] / a[2], 1000 * a[1] / a[2]

    return {"groups": {k: rate(a) for k, a in acc.items() if k != "World" and not k.startswith("tag:")},
            "world": rate(acc["World"]) if "World" in acc else (0.0, 0.0),
            "tags": {k[4:]: (size[k[4:]], *rate(a)) for k, a in acc.items() if k.startswith("tag:")}}


def east_for_china(rows, today, point, s, cut_lm, cut_bs, held=None, top=0.9):
    """Owner, 2026-10-11 (D13): East Asia's Birth Spacing share at this point, the smallest on a 0.01 grid from the cancel
    share up to `top` at which China's projected peacetime births less deaths is at most the top of its band (+6), and
    China's rate there. Never below the cancel share: if China is below +3 even there, it fails the gate on mortality."""
    hi = dict((label, band) for label, _r, band in R.REPORT_REGIONS)["China"][1]
    h = cancel_share(s, cut_bs) if held is None else held
    e = math.ceil(h * 100 - 1e-9) / 100
    while True:
        rate = project_regions(rows, today, point, s, cut_lm, cut_bs, held, e)["groups"].get("China", (0.0, 0.0))[1]
        if rate <= hi or e >= top:
            return e, rate
        e = round(e + 0.01, 2)


def region_gate(proj, world_margin=1.0, big=2e7):
    """Review C1's gate on a projection: every #904 group with a band (R.REPORT_REGIONS) inside it; the world at or
    below today's measured rate less world_margin per 1,000 (x1.65 over 1836-1900 needs about 1 less than the run's
    +8.8); no country of `big` people or more with projected peacetime births below deaths. Returns the failures."""
    fails = []
    for label, _regions, band in R.REPORT_REGIONS:
        if band and label in proj["groups"]:
            lo, hi = band
            got = proj["groups"][label][1]
            if not lo <= got <= hi:
                fails.append(f"{label}: {got:+.1f} per 1,000 (history {lo:+g} to {hi:+g})")
    measured, projected = proj["world"]
    if projected > measured - world_margin:
        fails.append(f"World: {projected:+.1f} per 1,000 (at most {measured - world_margin:+.1f})")
    for tag, (people, _measured, got) in sorted(proj["tags"].items()):
        if people >= big and got < 0:
            fails.append(f"{tag}: {got:+.1f} per 1,000 with {people / 1e6:.0f}M people")
    return fails


@contextlib.contextmanager
def patch_params(infection_scale=1.0, **values):
    """demographics_params' values for one grid point, restored after; infection_scale multiplies the base infection
    schedule (both sexes, every age group). The model reads P at call time, so the next fit_states sees them."""
    saved = {k: getattr(P, k) for k in values}
    saved_infection = P.INFECTION
    try:
        for k, v in values.items():
            setattr(P, k, v)
        P.INFECTION = {sex: [x * infection_scale for x in rates] for sex, rates in saved_infection.items()}
        yield
    finally:
        for k, v in saved.items():
            setattr(P, k, v)
        P.INFECTION = saved_infection


def mortality_report(fit_by_year):
    """Spec 5.2's Western item: the United Kingdom's, Sweden's and Denmark's life expectancy in the first year (their
    incorporated states, by people), against 41."""
    first = min(fit_by_year)
    acc = {}
    for st in fit_by_year[first]:
        if st.country in dict(WESTERN_E0) and st.incorporated:
            a = acc.setdefault(st.country, [0.0, 0.0])
            a[0], a[1] = a[0] + st.people, a[1] + st.people * st.e0
    return {c: e / p for c, (p, e) in acc.items() if p}
```

`practice_states` walks a parsed save's pops once (`_state_inputs`, cached by the parse: no grid point changes the
walk; `test_a_parsed_save_walks_its_pops_once`), so the 60-point mortality grid re-runs only the model. It must carry
each state's census bands: `read_save` reads `BAND_VARS = tuple(f"te_dg_b{x}{b}"
for x in "fm" for b in range(P.BANDS))` beside `te_dg_fjob_share`, and `PracticeState` gains
`bands: tuple = ()`, filled with `tuple((v.get(f"te_dg_bf{b}", 0.0), v.get(f"te_dg_bm{b}", 0.0)) for b in
range(P.BANDS))`. Task 3's code already has it.

- [x] **Step 4: The scenarios with their shares** (`demographics_harness.py`, after `FERTILITY_SCENARIOS`)

`fertility_rows` takes `scenarios=None` and iterates `scenarios or FERTILITY_SCENARIOS`. Then:

```python
# The children-per-woman scenarios with the practices' shares (the late-marriage spec 5.1 item 4: the shares the drift
# gives each), and review I3's two for the 20th century where Birth Spacing has eroded and only the raise is left
# (bands from Gapminder in the anchors: East Asia 1990 Japan 1.56, Korea 1.58, Taiwan 1.81, China 2.35; Latin America
# 1970 Chile 4.02 to Mexico 6.83, Argentina's 3.07 left out). practices-fit judges candidates against them; Task 6
# makes them the fertility command's once the raise is applied.
_SCENARIO_PRACTICES = {
    "1836 agrarian (reference)": {"lm": 0.5}, "1836 agrarian, No Women's Rights": {"lm": 0.5},
    "Britain 1836": {"lm": 1.0}, "France 1836 (Family Limitation)": {"lm": 1.0},
    "Britain 1900": {"lm": 0.75}, "Britain 1900, Women Own Property": {"lm": 0.75},
    "West 1950": {"lm": 0.5}, "West 1950, Women's Suffrage": {"lm": 0.5},
    "West 1990": {"lm": 0.45}, "West 1990, Women's Suffrage": {"lm": 0.45},
    "India 1975": {"bs": 0.2},   # the drift's equilibrium from the held start at its contraception and health care
}
_SCENARIO_BANDS = {"Britain 1836": (4.3, 5.5)}   # re-centred on history's 4.8-5.0 (spec 5.1)
PRACTICE_SCENARIOS = [(label, dict(kw, practices=_SCENARIO_PRACTICES[label]), _SCENARIO_BANDS.get(label, band))
                      for label, kw, band in FERTILITY_SCENARIOS] + [
    ("East Asia 1990", dict(sol=28, literacy=0.97, urban_share=0.7,
                            techs=MED_1990 | MEANS_TECHS | {"contraceptive_pill"}, laws={PHI},
                            institutions={HEALTH: 5}, practices={"lm": 0.1, "bs": 0.05}), (1.4, 2.4)),
    ("Latin America 1970", dict(sol=12, literacy=0.72, urban_share=0.55, techs=MED_1950 | MEANS_TECHS, laws={CHS},
                                institutions={HEALTH: 2}), (4.0, 6.8)),
]
```

`_SCENARIO_PRACTICES[label]` raises a `KeyError` if a scenario's label changes, which is the intent. The two new
scenarios' inputs are starting proposals; check them against the medicine scenarios' inputs for the same decades
(`MED_1950`, `MED_1990`) when you write them.

- [x] **Step 5: The subcommand** (`demographics_harness.py`)

`practices-fit SAVE... --anchors CSV --peacetime ROWS [--shares FILE] [--s 1.00,1.05,1.10,1.15,1.20]
[--lm 0.20,0.25,0.30,0.35,0.40] [--bs 0.25,0.30,0.35,0.40,0.45] [--fit-years 1837,1887] [--at S,LM,BS[,HELD[,EAST]]]
[--mortality] [--means] [--year Y]`.

`ROWS` is #904's state-years (`analyze.py --json`; Task 6 Step 2 writes it). The saves are the run's eight (Task 6
Step 1); the TFR error reads `--fit-years` only, and the projection reads them all.

```python
def cmd_practices_fit(args):
    import demographics_practices as DP
    try:
        anchors = read_anchors(args.anchors)
    except OSError as e:
        print(f"cannot read the anchors {args.anchors}: {e}", file=sys.stderr)
        return 1
    rows = json.loads(Path(args.peacetime).read_text(encoding="utf-8"))["rows"]
    carriers = DM.load_carriers()
    shares_by_year = DP.read_shares(args.shares) if args.shares else {}
    saves = {path: DP.read_save(path) for path in args.save}   # parse each save once
    fit_years = {int(y) for y in args.fit_years.split(",")}

    def load(carriers):
        out = {}
        for path in args.save:
            year = save_year(path) or args.year
            table = DP.table_shares(DP.practice_states(path, carriers, save=saves[path]))
            shares = {**table, **shares_by_year.get(year, {})}   # a state the replay lacks takes its start
            out[year] = DP.fit_states(path, carriers, shares, save=saves[path])
        return out

    def scenarios_out(carriers, s, cl, cb):
        """PRACTICE_SCENARIOS and the medicine scenarios out of band at this point (review I1): the curve x s and the
        cuts patched, since the scenarios read them from P."""
        with DP.patch_params(WEALTH_TFR_LOW=P.WEALTH_TFR_LOW * s, WEALTH_TFR_HIGH=P.WEALTH_TFR_HIGH * s,
                             PRACTICE_CUT={"lm": cl, "bs": cb}):
            fert = [r[0] for r in fertility_rows(carriers=carriers, scenarios=PRACTICE_SCENARIOS)
                    if not r[2] <= r[1] <= r[3]]
        med = [f"{label} {k}" for label, figures in medicine_rows(carriers=carriers)
               for k, (v, lo, hi) in figures.items() if not lo <= v <= hi]
        return fert, med

    def show(proj, fails):
        for label, (measured, projected) in sorted(proj["groups"].items()):
            band = dict((l, b) for l, _r, b in R.REPORT_REGIONS).get(label)
            b = f"{band[0]:+g} to {band[1]:+g}" if band else "-"
            print(f"  {label:28s} measured {measured:+5.1f}  projected {projected:+5.1f}  history {b}")
        print(f"  {'World':28s} measured {proj['world'][0]:+5.1f}  projected {proj['world'][1]:+5.1f}")
        for line in fails:
            print("  GATE " + line)

    today = load(carriers)
    grid = ([float(x) for x in args.s.split(",")], [float(x) for x in args.lm.split(",")],
            [float(x) for x in args.bs.split(",")])
    def china(res):
        """China's children per woman in the fit years, flagged below about 5 (owner, 2026-10-11; D13)."""
        got = {y: m for (c, y), (m, _h) in res["countries"].items() if c == "China" and y in fit_years}
        return " / ".join(f"{v:.2f}{' LOW' if v < 5.0 else ''}" for _y, v in sorted(got.items()))

    print("s     cut_lm cut_bs error  world tfr        india east  China tfr     high group  gate (today's mortality)")
    for s, cl, cb, res in DP.fit_table(today, anchors, *grid, years=fit_years):
        east, _rate = DP.east_for_china(rows, today, today, s, cl, cb)
        res = DP.evaluate(today, anchors, s, cl, cb, east=east, years=fit_years)
        tfr = " / ".join(f"{v:.2f}" for _y, v in sorted(res["world_tfr"].items()) if v)
        hi = f"{res['high'][0]:.2f}-{res['high'][1]:.2f}" if res["high"] else "-"
        fails = DP.region_gate(DP.project_regions(rows, today, today, s, cl, cb, east=east))
        print(f"{s:.2f}  {cl:.2f}   {cb:.2f}   {res['error']:.3f}  {tfr:16s} {res['held']:.2f}  {east:.2f}  "
              f"{china(res):12s}  {hi:10s}  {len(fails)} failing")
    if not args.at:
        return 0
    s, cl, cb, *rest = (float(x) for x in args.at.split(","))
    held = rest[0] if rest else None
    east = rest[1] if len(rest) > 1 else DP.east_for_china(rows, today, today, s, cl, cb, held)[0]
    res = DP.evaluate(today, anchors, s, cl, cb, held=held, east=east, years=fit_years)
    print(f"held shares: India {res['held']:.2f}, China, Manchuria and Korea {east:.2f}; China's children per woman "
          f"{china(res)}")
    for (country, year), (model, hist) in sorted(res["countries"].items()):
        if year not in fit_years:
            continue
        tag = " (half)" if country in DP.FLAT_GUESSES else ""
        tag += " (dropped)" if (country, year) in DP.DROPPED else ""
        off = " OFF" if hist is not None and abs(model - hist) > 0.5 else ""
        h = f"{hist:.2f}" if hist is not None else "-"
        print(f"{country:15s} {year}  model {model:.2f}  history {h}{tag}{off}")
    proj = DP.project_regions(rows, today, today, s, cl, cb, held, east)
    show(proj, DP.region_gate(proj))
    print(f"Western life expectancy: {DP.mortality_report(today)}; scenarios out of band: "
          f"{scenarios_out(carriers, s, cl, cb)}")
    if args.mortality:
        for floor in (1.5, 1.75, 2.0, 2.25):
            for sol in (8, 9, 10):
                for scale in (0.9, 1.0, 1.1, 1.2, 1.3):
                    with DP.patch_params(infection_scale=scale, POVERTY_INFECTION_AT_FLOOR=floor,
                                         POVERTY_INFECTION_SOL=sol):
                        point = load(carriers)
                        out = scenarios_out(carriers, s, cl, cb)
                    e_pt = rest[1] if len(rest) > 1 else DP.east_for_china(rows, today, point, s, cl, cb, held)[0]
                    proj = DP.project_regions(rows, today, point, s, cl, cb, held, e_pt)
                    fails = DP.region_gate(proj)
                    e0 = DP.mortality_report(point)
                    cn = china(DP.evaluate(point, anchors, s, cl, cb, held=held, east=e_pt, years=fit_years))
                    print(f"floor {floor:.2f} sol {sol} infection x{scale:.2f}: {len(fails)} failing; East Asia's "
                          f"share {e_pt:.2f}, China {cn}; Western e0 {e0}; scenarios out of band {out}")
                    show(proj, fails)
    if args.means:
        for vulc in (0.10, 0.15, 0.20, 0.25, 0.30):
            for fem in (0.10, 0.15, 0.20, 0.25, 0.30):
                patched = [dataclasses.replace(c, value=vulc) if c.key == "vulcanization"
                           and c.type == P.CONTRACEPTION_TYPE else
                           dataclasses.replace(c, value=fem) if c.key == "feminism"
                           and c.type == P.CONTRACEPTION_TYPE else c for c in carriers]
                res = DP.evaluate(load(patched), anchors, s, cl, cb, held=held, east=east, years=fit_years)
                gb = {y: m for (c, y), (m, _h) in res["countries"].items() if c == "United Kingdom"}
                print(f"vulcanization {vulc:.2f} feminism {fem:.2f}: Britain {gb}; scenarios out of band "
                      f"{scenarios_out(patched, s, cl, cb)}")
    return 0
```

Notes:
- `R` is the harness's `demographics_regions` import (Task 3).
- `medicine_rows` returns `(label, {figure: (value, low, high)})`, with the gap rows as `gap`.
- The replayed shares stay fixed while the means pair varies. The pair also feeds Late Marriage's erosion, but by 1887
  that is negligible, and Task 6 Step 8 replays again at the applied values.
- The mortality grid has 60 points. Each re-runs the model over every state of eight saves from the cached parse, so it
  takes tens of minutes, not hours.

- [x] **Step 6: Run the tests**

Run: `$V -m unittest test_demographics_practices test_demographics_harness`
Expected: `OK`.

- [x] **Step 7: Commit**

```bash
git add scripts/analysis/demographics_practices.py scripts/analysis/demographics_harness.py test_demographics_practices.py test_demographics_harness.py
git commit -m "Demographics harness: practices-fit, the regional projection of #904's peacetime rates, and the gate"
```

---

### Task 6: Run the fit, round, apply — then Stop A

The harness fit comes first (spec §5.1). This task runs it on the normal-speed run's saves, picks the neat point the
gate passes, applies it, and stops for the owner before any script.

**Don't deploy this branch between this task's commit and Task 8's.** Task 6 raises the wealth curve in the generated
values, and the script gets the practices only in Task 8, so a game in between would run every state's births about
×1.15 high.

**Files:**
- Create: `docs/testing/demographics-late-marriage-<date>.md`
- Modify: `scripts/analysis/demographics_params.py`. The fitted values:
  - `WEALTH_TFR_LOW`, `WEALTH_TFR_HIGH`, `PRACTICE_CUT`, `BS_HELD_START`, `BS_EAST_ASIA_START`;
  - if the mortality point moves them, `POVERTY_INFECTION_AT_FLOOR`, `POVERTY_INFECTION_SOL` and the `INFECTION`
    breakpoints.
- Modify, only if the means fit moves them: `common/technology/technologies/te_demog_tech_injections.txt`
- Modify: `scripts/analysis/demographics_harness.py` (`FERTILITY_SCENARIOS = PRACTICE_SCENARIOS`)
- Modify the tests that pin today's figures:
  - `test_demographics_model.py` (`TestFertility.test_sketch_cases`, `test_wealth_term_endpoints`);
  - `test_demographics_save_inputs.py` (`test_wealth_tfr_is_the_pop_weighted_curve`'s 4.889);
  - `test_demographics_harness.py`, as the suite shows.
- Regenerate: `te_demog_generated_values.txt` (the wealth curve)

- [x] **Step 1: Check the build question and pick the saves**

```bash
F=scripts/analysis/demographics_save_inputs.py
git show origin/main:$F | sed 's/, buffering=READ_BUFFER//' | grep -v 'READ_BUFFER\|16 MB buffer\|8 KB reads' | diff -q - <(git show ec304526:$F) >/dev/null && echo "main's reader is ec304526's but for #904's buffer"
git diff origin/main -- scripts/analysis/demographics_save_inputs.py | grep '^-[^-]' || echo "this branch only adds to it"
D=/mnt/d/vic3te-data/vic3te-demog-p2-normal-2026-10-11/saves
for f in $D/*.v3; do printf '%s %s\n' "$($V -c "import sys; sys.path.insert(0,'scripts/analysis'); import demographics_harness as H; print(H.save_year(sys.argv[1]))" "$f")" "$f"; done | sort -n > /tmp/claude-1000/lm-saves.txt
awk '$1==1837||$1==1847||$1==1857||$1==1867||$1==1877||$1==1887||$1==1897||$1==1901' /tmp/claude-1000/lm-saves.txt
```

Expected:
- Both lines print. #904 (merged) only widened the reader's buffer, which the first command filters out; Task 3's
  changes to the reader only add lines.
- One save for each of the eight years. Keep the eight paths as `S1837 … S1901` and `SAVES="$S1837 … $S1901"`.

`predict` does not run from this branch on these saves (D8).

- [x] **Step 2: Today, before anything changes** (no practices, the 6.0 curve)

#904's state-years with its peacetime filter, written again with its defaults so the file is known:

```bash
RR=/mnt/d/vic3te-data/vic3te-demog-p2-normal-2026-10-11/session-notes-2026-10-11/regional-rates
python3 $RR/analyze.py $RR/data --json /tmp/claude-1000/lm-peacetime-rows.json > /tmp/claude-1000/lm-peacetime-today.txt
ROWS=/tmp/claude-1000/lm-peacetime-rows.json; A=/mnt/d/vic3te-data/history-anchors-2026-10-10/anchors.csv
$V scripts/analysis/demographics_harness.py practices-fit $SAVES --anchors $A --peacetime $ROWS --s 1.0 --lm 0 --bs 0 --at 1,0,0,0,0 > /tmp/claude-1000/lm-today-fit.txt
$V scripts/analysis/demographics_harness.py history $S1837 $S1887 --anchors $A --incorporated-only --no-practices > /tmp/claude-1000/lm-today-history.txt
$V scripts/analysis/demographics_harness.py medicine; $V scripts/analysis/demographics_harness.py fertility
```

(`--at`'s fifth value gives East Asia's share: with no cut the search can't move China and would walk to its cap.)

Expected: the `--at 1,0,0,0,0` (no raise, no cut) regional table's "projected" equals its "measured", and both equal #904's peacetime
column to 0.1: China +6.5, India +11.7, Europe +11.1, …, World +8.8. A mismatch means the rows or the grouping differ
from #904's; stop and find out why. Record "today" in the results doc:
- the world's children per woman for 1837 and 1887 and each anchor country;
- the regional table;
- the Western life expectancies.

(Spec §5.2's 5.96 / 5.74 and +1.08 / +0.98 were 6.2-era figures, D1.)

- [x] **Step 3: The drift replay at the starting values**

```bash
$V scripts/analysis/demographics_harness.py practices-replay $SAVES --out /tmp/claude-1000/lm-replay.json
```

Expected: no `GATE` line up to 1887. If one prints, it names the region and figure; read the largest moves list and the
targets. A Western state far below 0.8 by 1887 means era-3 contraception reached it early. That is a finding for the
results doc and Stop A, not a retune here.

- [x] **Step 4: The fertility fit, each raise**

```bash
$V scripts/analysis/demographics_harness.py practices-fit $SAVES --anchors $A --peacetime $ROWS --shares /tmp/claude-1000/lm-replay.json \
  --s 1.00,1.05,1.10,1.15,1.20 --lm 0.20,0.25,0.30,0.35,0.40 --bs 0.25,0.30,0.35,0.40,0.45
```

Each row is a raise s, with:
- the cuts that fit children per woman best, already on the 0.05 grid;
- the error;
- India's held share (the cancel share), rounded to 0.01 when applied (`--at`'s fourth value);
- East Asia's share (D13): the smallest on the 0.01 grid, from the cancel share up, that brings China's peacetime
  births less deaths to +6 or less. `--at` picks it again at every mortality point unless given as a fifth value;
- China's children per woman at it, marked `LOW` below about 5;
- the high group's range, reported only;
- how many gate items fail with today's mortality.

If a row's best cut sits on the grid's floor (as at s 1.00 and 1.05 on 2026-10-12), run that raise again with the grid
extended down (`--lm 0.05,…,0.25 --bs 0.10,…,0.30`): an edge is not the fit's answer. Same knobs, wider range.

- [x] **Step 5: Mortality and the means pair, from the smallest raise up** (call 8)

For each s in ascending order, at that row's cuts and India's rounded held share (East Asia's share is chosen at each
point):

```bash
$V scripts/analysis/demographics_harness.py practices-fit $SAVES --anchors $A --peacetime $ROWS --shares /tmp/claude-1000/lm-replay.json \
  --s S --lm LM --bs BS --at S,LM,BS,HELD --mortality > /tmp/claude-1000/lm-mortality-S.txt
```

A point passes when all of these hold:
- the regional gate prints no `GATE` line: every group inside its band, the world at or below +7.8, China inside +3 to
  +6, no country of 20M shrinking;
- Britain's, Sweden's and Denmark's life expectancy are within 3 years of 41;
- no fertility or medicine scenario is out of band;
Children per woman isn't a pass condition (owner, 2026-10-11: growth matters more than the exact figure). The cuts
still minimise its error at each s, and the results doc reports, without judging:
- the error against the spec's 0.5;
- each country more than 0.5 off, with its reason;
- the high group's level against history's ~7.

**Take the smallest s with a passing mortality point, possibly 1.00 (no raise).** Within that s:
- ties go to the point nearest today's (POVERTY_INFECTION_AT_FLOOR 1.75, POVERTY_INFECTION_SOL 9, infection ×1);
- if the mortality point moved, re-run Step 4's row for that s at it (`--at` under the point's values is the check),
  since the survival term moves children per woman, and keep the second answer if the cuts differ.

Then, at the chosen point:

```bash
$V scripts/analysis/demographics_harness.py practices-fit $SAVES --anchors $A --peacetime $ROWS --shares /tmp/claude-1000/lm-replay.json \
  --s S --lm LM --bs BS --at S,LM,BS,HELD --means
```

Keep vulcanization 0.20 and feminism 0.15 unless another neat pair puts every scenario in band with a smaller error on
Britain 1887.

**If no s up to 1.20 has a passing point,** take the smallest s whose best point fails fewest regional items, and name
each failing region in the results doc:
- the regions only a geographic mortality term could fix, which go to calibration step 3, a separate step after this
  work (owner, 2026-10-11);
- any other failure, which goes to Stop A as a finding.

Expect some of this:
- the mortality knobs read standard of living alone, which doesn't separate the Middle East's and Mexico's deaths (too
  few) from the West's (too many) (spec §2.4, §1.4);
- matching growth may leave the high-fertility group's children per woman below history's ~7. The owner accepts that.

Don't widen the grid beyond the spec's knobs.

- [x] **Step 6: Apply the chosen values**

In `demographics_params.py`:
- `WEALTH_TFR_LOW` = 6.0 × s and `WEALTH_TFR_HIGH` = round(3.5 × s, 2). Keep the comment's history line and add:
  "× s (the late-marriage plan's fit, <date>; spec 2.2), the smallest raise the regional gate passes".
- `PRACTICE_CUT`.
- `BS_HELD_START` = India's held share used at the chosen point (the cancel share, rounded to 0.01);
- `BS_EAST_ASIA_START` = East Asia's share chosen at that point (D13), on the 0.01 grid.
- If the mortality point moved: `POVERTY_INFECTION_AT_FLOOR`, `POVERTY_INFECTION_SOL`, and each `INFECTION` breakpoint
  × the scale, rounded to the nearest 10.

If the means pair moved, change `te_demog_tech_injections.txt`'s two lines.

In `demographics_harness.py`, after `PRACTICE_SCENARIOS`, add `FERTILITY_SCENARIOS = PRACTICE_SCENARIOS`, so the
`fertility` command judges the scenarios with their shares.

```bash
$V scripts/generators/gen_demographics.py
```

- [x] **Step 7: Update the tests that pin today's figures, and run the suite**

- `test_wealth_term_endpoints`: the new `WEALTH_TFR_LOW` and `WEALTH_TFR_HIGH`.
- `test_sketch_cases`: give each scenario its shares from `_SCENARIO_PRACTICES` (Britain 1836 and France 1836
  `{"lm": 1.0}`, Britain 1900 `{"lm": 0.75}`, the West 1950 `{"lm": 0.5}`, 1990 `{"lm": 0.45}`, India 1975
  `{"bs": 0.2}`). Set each expected value to the model's figure rounded to 0.05, printed by:
  `$V -c "import sys; sys.path.insert(0,'scripts/analysis'); sys.path.insert(0,'.'); import test_demographics_model as T, demographics_model as M; [print(n, round(M.run_constant(i, years=200)[1]['tfr'], 2)) for n, i in (('GB1836', T.BRITAIN_1836), ('FR1836', T.FRANCE_1836), ('GB1900', T.BRITAIN_1900), ('W1950', T.WEST_1950), ('W1990', T.WEST_1990), ('IN1975', T.INDIA_1975))]"`.
  Keep `delta=0.3`. Each must lie inside its band in `PRACTICE_SCENARIOS`, or stop: a scenario out of band is a fit
  failure, not a test to loosen.
- `test_wealth_tfr_is_the_pop_weighted_curve`: its 4.889 scales by s; recompute it the way the test's comment does.

```bash
$V -m unittest discover -s . -p 'test_*.py' > /tmp/claude-1000/t6.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t6.txt
$V scripts/analysis/demographics_harness.py fertility; $V scripts/analysis/demographics_harness.py medicine
```

Expected: `OK`; neither command prints `OUT`.

- [x] **Step 8: After, on the same saves**

```bash
$V scripts/analysis/demographics_harness.py practices-replay $SAVES --out /tmp/claude-1000/lm-replay-fitted.json
$V scripts/analysis/demographics_harness.py history $S1837 $S1887 --anchors $A --incorporated-only --shares /tmp/claude-1000/lm-replay-fitted.json
```

The projection compares a point with today's parameters, so it was taken at the chosen point in Step 5 and isn't
re-run on the applied build: with the raise in the curve, "today" would be the new curve. The applied build's
children per woman (this `history`) must match Step 5's `--at` table to 0.02, since the applied values are the same
point.

- [x] **Step 9: Write the results doc** (`docs/testing/demographics-late-marriage-<date>.md`)

Its sections:
- **The build and the data:** this branch's commit; the saves (D8: the reader is unchanged since ec304526 but for
  #904's buffer); the anchors' path; #904's rows and the filter's defaults.
- **Today:** Step 2's tables (world, anchor countries, regions, Western life expectancy). The regional table must
  reproduce #904's peacetime column.
- **The replay:** Step 3's and Step 8's per-year lines, the largest moves, and the gate lines.
- **The fit:** Step 4's table, one row per raise; the chosen point and why (the smallest passing s); the
  country-by-country table, naming every country more than 0.5 off with its reason (spec §2.3's "What is left, and
  why" as the model).
- **The high-fertility group:** its children per woman at the chosen point against history's ~7, said plainly if it
  stays below.
- **The regional table** at the chosen point: measured, projected and history's band for each of #904's groups and the
  world. This answers #894's "Births less deaths outside Europe" for the census's side.
- **Mortality and the means pair:** the chosen point, its Western life expectancies, and the scenarios.
- **China, Manchuria and Korea (D13):**
  - East Asia's chosen share against the cancel share;
  - China's children per woman at it in 1837 and 1887, against history's ~5.5, said plainly if below about 5;
  - Korea's, which has no data-based anchor.
- **The gate**, item by item, each pass or fail with its figure.

- [x] **Step 10: Commit**

```bash
git add scripts/analysis/demographics_params.py scripts/analysis/demographics_harness.py common/script_values/te_demog_generated_values.txt docs/testing/demographics-late-marriage-<date>.md test_demographics_model.py test_demographics_save_inputs.py test_demographics_harness.py
git commit -m "Demographics: the practices' fit on the normal-speed run's saves; the smallest raise the regional gate passes"
```

Add `te_demog_tech_injections.txt` to the `git add` if Step 6 changed it.

- [x] **Stop A (owner). Decided 2026-10-12: option 2.** The owner kept the fit's fertility (s 1.00, cuts 0.10 and 0.20,
  India's held share 0, East Asia's 0.06 by D13's rule at today's mortality) with step 1's mortality unchanged; the
  fallback's poverty refit (×2.25 from SoL 8) was not taken. The gate fails (India, Africa, the USA and Canada, the
  Middle East, South America, Southeast Asia; Europe and the world by rounding), and those regions are calibration
  step 3's. Owner questions 1–3 were answered on 2026-10-11 (above). The original instruction follows.

  Post the results doc's chosen point, regional table and gate to the owner, with Owner
  questions 1–3. Continue to Task 7 on the owner's word.
  - If Step 5 found no passing point, the post names the regions left for calibration step 3 (a separate step after
    this work) and any other failure.
  - Marital fertility for the Low Countries (§2.3) stays a later term.

---

### Task 7: The generator writes the practices' values and loops

**Files:**
- Modify: `scripts/generators/gen_demographics.py` (`practices(o)` in `render_values` after `multipliers(o)`;
  `practice_loops(o)` in `render_effects` after `medicine_effects(o)` (since #916 it runs `absorbed_walk`,
  `medicine_effects`, `debug_ring`); `"practice_rate"` in `constants`; the
  module docstring's list)
- Regenerate: `te_demog_generated_values.txt`, `te_demog_generated_effects.txt`
- Test: `test_gen_demographics.py`

**Interfaces:**
- Consumes: Task 2's params.
- Produces (state scope unless noted):
  - `te_demog_pr_start_<P>` (the start ladder);
  - `te_demog_pr_erosion_contraception`, `te_demog_pr_erosion_<P>`;
  - `te_demog_pr_seed_<P>` (start × (1 − erosion): the seed with no sibling holding a share);
  - `te_demog_pr_target_<P>` (the seed value plus Late Marriage's drivers, within 0–1);
  - `te_demog_pr_term_<P>` (state or country: 1 − cut × `var:te_dg_pr_<P>`, 1 with no share);
  - `te_demog_pr_terms` (their product);
  - `te_demog_marriage_age` (state or country) and `te_demog_pr_share_bs` (state or country, 0 with no share);
  - `te_demog_k_practice_rate`;
  - effects `te_demog_practices_seed`, `_step`, `_country_init`, `_country_add`, `_country_store`, each calling
    `te_demog_practice_<name> = { P = <p> }` for p in `P.PRACTICES`.

- [x] **Step 1: Write the failing tests** (append to `TestGenerated` in `test_gen_demographics.py`)

```python
    def test_the_practices_values(self):
        for p in P.PRACTICES:
            start = self.values.split(f"te_demog_pr_start_{p} = {{", 1)[1].split("\n}\n", 1)[0]
            for region in P.PRACTICE_START_REGION[p]:
                self.assertIn(f"region = sr:{region}", start)
            for state in P.PRACTICE_START_STATE[p]:
                self.assertIn(f"state_region = s:{state}", start)
            # the state regions come after the strategic regions, so they win
            if P.PRACTICE_START_REGION[p] and P.PRACTICE_START_STATE[p]:
                self.assertLess(start.rindex("region = sr:"), start.index("state_region = s:"))
            term = self.values.split(f"te_demog_pr_term_{p} = {{", 1)[1].split("\n}\n", 1)[0]
            self.assertIn(f"limit = {{ has_variable = te_dg_pr_{p} }}", term)
            self.assertIn(f"multiply = {gen.lit(P.PRACTICE_CUT[p])}", term)
            self.assertIn(f"te_demog_pr_target_{p} = {{", self.values)
            seed = self.values.split(f"te_demog_pr_seed_{p} = {{", 1)[1].split("\n}\n", 1)[0]
            self.assertIn(f"value = te_demog_pr_erosion_{p}", seed)
            self.assertIn(f"multiply = te_demog_pr_start_{p}", seed)
            self.assertIn(f"value = te_demog_pr_seed_{p}", self.values.split(f"te_demog_pr_target_{p} = {{", 1)[1])
            self.assertIn(f"multiply = te_demog_pr_term_{p}", self.values.split("te_demog_pr_terms = {", 1)[1])
        lm = self.values.split("te_demog_pr_target_lm = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("te_inh_has_undivided_farms = yes", lm)
        self.assertIn("has_law = law_type:law_primogeniture", lm)
        erosion_lm = self.values.split("te_demog_pr_erosion_lm = {", 1)[1].split("\n}\n", 1)[0]
        self.assertNotIn(f"modifier:{P.ACCESS_TYPE}", erosion_lm, "health care erodes Birth Spacing only")
        erosion_bs = self.values.split("te_demog_pr_erosion_bs = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn(f"modifier:{P.ACCESS_TYPE}", erosion_bs)
        self.assertIn(f"te_demog_k_practice_rate = {{ value = {gen.lit(P.PRACTICE_RATE)} }}", self.values)

    def test_the_practice_loops_call_every_practice(self):
        for name in ("seed", "step", "country_init", "country_add", "country_store"):
            body = self.effects.split(f"te_demog_practices_{name} = {{", 1)[1].split("\n}\n", 1)[0]
            self.assertEqual(re.findall(rf"te_demog_practice_{name} = \{{ P = (\w+) \}}", body), list(P.PRACTICES))
```

- [x] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_gen_demographics`
Expected: FAIL (`te_demog_pr_start_lm` not found).

- [x] **Step 3: Write the generator functions**

```python
def _by_value(table):
    """[(value, [keys])] for a {key: value} table, by value then key: one if per value."""
    out = {}
    for key, value in table.items():
        out.setdefault(value, []).append(key)
    return [(v, sorted(keys)) for v, keys in sorted(out.items())]


def practices(o):
    """Late Marriage and Birth Spacing (docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md): each
    practice's start ladder, target and term, from demographics_params.py. The machinery that reads them is
    te_demog_practice_effects.txt."""
    o("# State scope: each practice's start share (the late-marriage spec 3.2, 3.3; demographics_model.practice_start):")
    o("# its strategic region's value, then its state region's, which wins. Geography, not culture.")
    for p in P.PRACTICES:
        o(f"te_demog_pr_start_{p} = {{")
        o("value = 0")
        for key, table in (("region = sr:", P.PRACTICE_START_REGION[p]), ("state_region = s:", P.PRACTICE_START_STATE[p])):
            for value, names in _by_value(table):
                o("if = {")
                o("limit = {")
                o("OR = {")
                for name in names:
                    o(f"{key}{name}")
                o("}")
                o("}")
                o(f"value = {lit(value)}")
                o("}")
        o("}")
        o("")
    o("# State scope: the means beyond traditional methods as erosion (demographics_model.practice_erosion): the techs'")
    o("# contraception x access by literacy, from 0 at PRACTICE_EROSION_FROM to its weight at FROM + SPAN.")
    o("te_demog_pr_erosion_contraception = {")
    o(f"value = modifier:{P.CONTRACEPTION_TYPE}")
    o(f"multiply = {{ value = var:te_dg_lit multiply = {lit(1 - P.MEANS_ACCESS_BASE)} add = {lit(P.MEANS_ACCESS_BASE)} }}")
    o(f"subtract = {lit(P.PRACTICE_EROSION_FROM)}")
    o(f"divide = {lit(P.PRACTICE_EROSION_SPAN)}")
    o("min = 0")
    o("max = 1")
    o(f"multiply = {lit(P.PRACTICE_EROSION_CONTRACEPTION)}")
    o("}")
    o("")
    o("# State scope: how much of each practice's start its conditions have eroded, 0-1 (demographics_model.")
    o("# practice_erosion): contraception, and for Birth Spacing health care. The seed with no sibling holding a share")
    o("# is the start less it (practice_seed; review I2), and the target adds Late Marriage's drivers to that")
    o("# (practice_target): impartible inheritance on the farms and women's paid work. Read after the walk.")
    for p in P.PRACTICES:
        o(f"te_demog_pr_erosion_{p} = {{")
        o("value = te_demog_pr_erosion_contraception")
        if P.PRACTICE_EROSION_ACCESS[p]:
            o(f"add = {{ value = var:te_dg_acc subtract = te_demog_k_base_access divide = {lit(P.PRACTICE_ACCESS_SPAN)} "
              f"min = 0 max = 1 multiply = {lit(P.PRACTICE_EROSION_ACCESS[p])} }}")
        o("max = 1")
        o("}")
        o(f"te_demog_pr_seed_{p} = {{")
        o(f"value = te_demog_pr_erosion_{p}")
        o("multiply = -1")
        o("add = 1")
        o(f"multiply = te_demog_pr_start_{p}")
        o("}")
        o(f"te_demog_pr_target_{p} = {{")
        o(f"value = te_demog_pr_seed_{p}")
        if p == "lm":
            o("if = {")
            o("limit = {")
            o("owner = {")
            o("OR = {")
            for law in P.IMPARTIBLE_LAWS:
                o(f"has_law = law_type:{law}")
            o("te_inh_has_undivided_farms = yes")
            o("}")
            o("}")
            o("}")
            o(f"add = {{ value = var:te_dg_agr_share multiply = {lit(P.LM_INHERITANCE)} }}")
            o("}")
            o(f"add = {{ value = var:te_dg_fjob_share multiply = te_demog_female_work_share "
              f"multiply = {lit(P.LM_WOMENS_WORK / P.FULL_FEMALE_WORK_SHARE)} }}")
        o("min = 0")
        o("max = 1")
        o("}")
        o("")
    o("# State or country scope: each practice's term in children per woman, 1 - cut x share; 1 with no share yet")
    o("# (an old save's state before its next census step, whose te_dg_tfr has no practice in it either: plan D7).")
    for p in P.PRACTICES:
        o(f"te_demog_pr_term_{p} = {{")
        o("value = 1")
        o("if = {")
        o(f"limit = {{ has_variable = te_dg_pr_{p} }}")
        o(f"subtract = {{ value = var:te_dg_pr_{p} multiply = {lit(P.PRACTICE_CUT[p])} }}")
        o("}")
        o("}")
    o("te_demog_pr_terms = {")
    o("value = 1")
    for p in P.PRACTICES:
        o(f"multiply = te_demog_pr_term_{p}")
    o("}")
    o("# State or country scope, the panel (spec 5.3): women's mean age at first marriage from the Late Marriage share,")
    o("# and the Birth Spacing share (0 with none).")
    o("te_demog_marriage_age = {")
    o(f"value = {lit(P.MARRIAGE_AGE_AT_ZERO)}")
    o("if = {")
    o("limit = { has_variable = te_dg_pr_lm }")
    o(f"add = {{ value = var:te_dg_pr_lm multiply = {lit(P.MARRIAGE_AGE_SPAN)} }}")
    o("}")
    o("}")
    o("te_demog_pr_share_bs = {")
    o("value = 0")
    o("if = {")
    o("limit = { has_variable = te_dg_pr_bs }")
    o("value = var:te_dg_pr_bs")
    o("}")
    o("}")
    o("")


def practice_loops(o):
    o("# The practices' machinery (te_demog_practice_effects.txt) for each practice in P.PRACTICES: phase 3 adds")
    o("# Family Limitation there and here.")
    for name in ("seed", "step", "country_init", "country_add", "country_store"):
        o(f"te_demog_practices_{name} = {{")
        for p in P.PRACTICES:
            o(f"te_demog_practice_{name} = {{ P = {p} }}")
        o("}")
    o("")
```

Add `"practice_rate": P.PRACTICE_RATE` to `constants`' dict.

**Amended at the build (2026-10-12):**
- **Birth Spacing's health-care erosion reads the access medicine has reached**, `var:te_dg_acc` less
  `te_demog_k_base_access`, not `modifier:state_health_care_access_add`. Since #916 the census's access drifts toward
  its target, and the owner approved the drift. It is a default flagged for the owner. `te_dg_acc` is set before any
  practice reads it: by `te_demog_medicine_at_target` at a seed and `te_demog_medicine_drift` at a step. The model
  reads the stored `te_dg_acc` where a save holds it (`census_inputs`), else the target, which is the modifier, so the
  fit on the pre-#916 saves is unchanged.
- **The ladder leaves out entries that change nothing** (`_start_entries`): a strategic region at 0, and a state region
  at its strategic region's value. The fit set India's and East Asia's held shares to 0, which would otherwise write
  dead tests. `test_the_start_ladders_give_every_state_its_start` reads each ladder as the engine does and checks
  every land state region against `demographics_model.practice_start`. The plan's per-entry `assertIn` loops gave way
  to that check.

`practices` hard-codes `te_dg_pr_lm` and `te_dg_pr_bs` in the panel's two values: they are Late Marriage's and Birth
Spacing's, not every practice's.

- [x] **Step 4: Regenerate and run the tests**

```bash
$V scripts/generators/gen_demographics.py
$V -m unittest test_gen_demographics test_demographics_registry > /tmp/claude-1000/t7.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t7.txt
```
Expected: `OK`. Nothing calls the new values yet.

- [x] **Step 5: Commit**

```bash
git add scripts/generators/gen_demographics.py common/script_values/te_demog_generated_values.txt common/scripted_effects/te_demog_generated_effects.txt test_gen_demographics.py
git commit -m "Demographics generator: the practices' start ladders, targets, terms and loops"
```

---

### Task 8: The census runs the practices

**Files:**
- Create: `common/scripted_effects/te_demog_practice_effects.txt`
- Modify: `common/scripted_effects/te_demog_effects.txt`:
  - `te_demog_seed`: `te_demog_practices_seed = yes` after `te_demog_medicine_at_target = yes` (#916), before
    `te_demog_prepare = yes`;
  - `te_demog_step_begin`: `te_demog_practices_step = yes` after `te_demog_medicine_drift = yes` (#916), before
    `te_demog_prepare = yes`; its header comment names the practices. #916's
    `test_the_entry_points_run_in_order` checks relative order only and already expects this;
  - console option a's comment (`te_debug_demog_effects.txt`, "drifts the census's medicine one more step"): each
    replay drifts the practices one more step too;
  - `te_demog_country_census`: `te_demog_practices_country_init = yes` after its other locals,
    `te_demog_practices_country_add = yes` inside `every_scope_state` after `te_dg_c_s_pm` is set, and
    `te_demog_practices_country_store = yes` after `te_demog_store_figures = yes`;
  - the header lists `te_dg_pr_<P>`.
- Modify: `common/script_values/te_demog_values.txt`: `te_demog_tfr` gains `multiply = te_demog_pr_terms`, and its
  comment names the practices.
- Test: `test_demographics_registry.py`:
  - `PRACTICE_EFFECTS` constant;
  - `_Engine` loads it and learns `region`, `state_region` and siblings;
  - `_engine_for` gives the targets and erosions as fixtures;
  - new class `TestPracticesScript`.

**Interfaces:**
- Consumes: Task 7's generated values and loops; Task 2's model functions.
- Produces: state variables `te_dg_pr_lm`, `te_dg_pr_bs`; the same names on the country (people-weighted means).

- [x] **Step 1: Teach the interpreter what the machinery uses**

In `test_demographics_registry.py`:
- add `PRACTICE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_practice_effects.txt"`;
- add it to `_Engine.__init__`'s effects list;
- set `self.place = (None, None)` and `self.siblings = []` in `__init__`.

In `_Engine._test`, before the trigger-fixture branch:

```python
        if key == "region":
            return arg == f"sr:{self.place[1]}"
        if key == "state_region" and isinstance(arg, str):
            return arg == f"s:{self.place[0]}"
```

In `_Engine.run`, before the `elif key in self.effects` branch:

```python
            elif key == "state_region" and isinstance(arg, list):
                # state_region = { every_scope_state = { limit = { … } … } }: the other states in its state region,
                # each a dict of its variables with its own state_population (te_demog_practice_seed)
                (inner, _, body), = arg
                assert inner == "every_scope_state", inner
                limit = next((v for k, _, v in body if k == "limit"), [])
                rest = [i for i in body if i[0] != "limit"]
                for sib in self.siblings:
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
```

`_engine_for` gains `place=(None, None), targets=None, erosion=None`. It sets `eng.place = place` and adds two fixtures
per practice: `f"te_demog_pr_target_{p}": (targets or {}).get(p, 0.0)` and
`f"te_demog_pr_erosion_{p}": (erosion or {}).get(p, 0.0)`.
- The targets read the owner, and the erosions modifier types, which `_Engine` doesn't know, so they are fixtures, as
  the owner's multipliers are.
- The seed value `te_demog_pr_seed_<P>` stays the generated one, so it is computed from the start ladder at `place`
  and the erosion fixture.
- At no place and 0 a state's shares are 0 and stay there, so every existing twin comparison (`TestCohortScript`) is
  unchanged.

- [x] **Step 2: Write the failing tests** (a new class after `TestNaturalFertilityScript`)

```python
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
        for laws, undivided, agr, fjob, lit, contra, access in (
                ({"law_no_womens_rights"}, False, 0.6, 0.1, 0.2, 0.0, 0.0),
                ({"law_primogeniture", "law_women_in_the_workplace"}, False, 0.5, 0.3, 0.6, 0.2, 0.18),
                ({"law_equal_inheritance", "law_protected_class"}, True, 0.4, 0.4, 0.9, 0.35, 0.5),
                ({"law_protected_class"}, False, 0.1, 0.5, 1.0, 0.45, 1.0)):
            inp = demographics_model.Inputs(literacy=lit, laws=frozenset(laws), agrarian_share=agr,
                                            female_job_share=fjob, impartible=undivided or "law_primogeniture" in laws,
                                            mods={P.CONTRACEPTION_TYPE: contra, P.ACCESS_TYPE: access})
            eng = _OwnerEngine({f"modifier:{P.CONTRACEPTION_TYPE}": contra, f"modifier:{P.ACCESS_TYPE}": access},
                               laws=laws, triggers={"te_inh_has_undivided_farms": undivided})
            eng.vars.update(te_dg_lit=lit, te_dg_agr_share=agr, te_dg_fjob_share=fjob)
            for state, region in (("STATE_POSEN", "region_eastern_europe"), ("STATE_KANTO", "region_northeast_asia")):
                eng.place = (state, region)
                for p in P.PRACTICES:
                    start = demographics_model.practice_start(p, state, region)
                    with self.subTest(laws=sorted(laws), state=state, practice=p):
                        self.assertAlmostEqual(eng.value(eng._tree(eng.values, f"te_demog_pr_target_{p}")),
                                               demographics_model.practice_target(p, inp, start), places=9)
                        self.assertAlmostEqual(eng.value(eng._tree(eng.values, f"te_demog_pr_seed_{p}")),
                                               demographics_model.practice_seed(p, inp, start, []), places=9)

    def _seeded(self, place, siblings=(), targets=None, erosion=None):
        eng = _engine_for(self.INP, 1836, 250000.0, place=place, targets=targets, erosion=erosion)
        eng.siblings = [dict(s) for s in siblings]
        eng.call("te_demog_seed")
        return eng

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

```

And in `TestCountry` (its `setUpClass` builds the three seeded states the test reuses):

```python
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
```

**Amended at Stop B (2026-10-12), the region's copy:** each step also writes the shares to the state region
(`te_dg_pr_<P>_r`), and the seed reads it after the siblings and before the eroded start. A whole state region taken
at once keeps its shares that way. `_Engine` gains `region_vars` and a `state_region = { … }` scope.
- Tests: `test_a_whole_region_changing_hands_takes_the_regions_copy`, `test_a_sibling_wins_over_the_regions_copy`
  and `test_the_step_writes_the_regions_copy`.
- `demographics_model.practice_seed(…, region=)` and the replay mirror it.

**Amended at the build (2026-10-12):** `test_the_targets_match_the_model` sets `te_dg_acc` at the model's target, since
Birth Spacing's erosion reads the access medicine has reached (Task 7's amendment). A new test,
`test_birth_spacing_erodes_with_the_access_medicine_has_reached`, checks the script's erosion against the model's at
four drifted values.

- [x] **Step 3: Run them to see them fail**

Run: `$V -m unittest test_demographics_registry.TestPracticesScript`
Expected: FAIL (`effect te_demog_practices_seed` unknown, or `te_dg_pr_lm` missing).

- [x] **Step 4: Write the machinery** (`common/scripted_effects/te_demog_practice_effects.txt`, with a UTF-8 BOM)

```
# ============================================================================
# DEMOGRAPHICS — the practices: Late Marriage (lm) and Birth Spacing (bs)
# docs/superpowers/specs/2026-10-10-demographics-late-marriage-design.md (approved by the owner 2026-10-11);
# docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md
# ============================================================================
# One machinery for every practice, parameterised by its short name $P$ (demographics_params.PRACTICES; the generated
# te_demog_practices_* call each). Phase 3 adds Family Limitation and the neighbour spread here. Each practice is a
# share of the state's people, 0-1, and multiplies the census's children per woman by 1 - cut x share
# (te_demog_pr_term_$P$, generated), outside the means. They run wherever the census runs (Full and Display only):
# they are the census's inputs, and they reach the engine only through the census's term M, under Full.
#
# State variable:   te_dg_pr_$P$   the share, 0-1
# Country variable: te_dg_pr_$P$   its census states' people-weighted mean (te_demog_country_census)
# ============================================================================

# THIS = a state whose census is being seeded or stepped. A state with no share takes the people-weighted mean of the
# other states in its state region that hold one (a split state is the same people as its sibling), else its start less
# what its conditions have eroded (te_demog_pr_seed_$P$). In 1836 nothing has eroded where a practice starts, so a new
# game seeds the table whatever order the states' pulses come in; an old save or a rule switched on mid-game seeds near
# where the drift would have taken it. A neighbour across a border plays no part. A share already held stays: a census
# re-seed re-counts the people, it doesn't change their customs.
te_demog_practice_seed = {
	if = {
		limit = { NOT = { has_variable = te_dg_pr_$P$ } }
		set_local_variable = { name = te_dg_pr_np value = 0 }
		set_local_variable = { name = te_dg_pr_ns value = 0 }
		state_region = {
			every_scope_state = {
				limit = { has_variable = te_dg_pr_$P$ }
				change_local_variable = { name = te_dg_pr_np add = state_population }
				change_local_variable = { name = te_dg_pr_ns add = { value = var:te_dg_pr_$P$ multiply = state_population } }
			}
		}
		if = {
			limit = { local_var:te_dg_pr_np > 0 }
			set_variable = { name = te_dg_pr_$P$ value = { value = local_var:te_dg_pr_ns divide = { value = local_var:te_dg_pr_np min = 1 } } }
		}
		else = {
			set_variable = { name = te_dg_pr_$P$ value = te_demog_pr_seed_$P$ }
		}
	}
}

# THIS = a state at its census step (te_demog_step_begin, after the walk and te_demog_medicine_drift, before
# te_demog_prepare reads the term):
# seed if it has no share (an old save's state), then drift te_demog_k_practice_rate of the gap to its target
# (te_demog_pr_target_$P$: the start less what contraception and, for Birth Spacing, health care have eroded, plus
# Late Marriage's inheritance and women's work). Once a census year: fast mode's clock steps it once a clock year.
te_demog_practice_step = {
	te_demog_practice_seed = { P = $P$ }
	set_variable = {
		name = te_dg_pr_$P$
		value = {
			value = te_demog_pr_target_$P$
			subtract = var:te_dg_pr_$P$
			multiply = te_demog_k_practice_rate
			add = var:te_dg_pr_$P$
			min = 0
			max = 1
		}
	}
}

# THIS = a country at its census (te_demog_country_census): the people-weighted mean of its census states' shares,
# for the panel (spec 3.1). Init before the walk over the states, add inside it (after local te_dg_c_s_pm, the
# state's people in millions), store after it.
te_demog_practice_country_init = {
	set_local_variable = { name = te_dg_c_pr_$P$_w value = 0 }
	set_local_variable = { name = te_dg_c_pr_$P$_p value = 0 }
}

te_demog_practice_country_add = {
	if = {
		limit = { has_variable = te_dg_pr_$P$ }
		change_local_variable = { name = te_dg_c_pr_$P$_w add = { value = var:te_dg_pr_$P$ multiply = local_var:te_dg_c_s_pm } }
		change_local_variable = { name = te_dg_c_pr_$P$_p add = local_var:te_dg_c_s_pm }
	}
}

te_demog_practice_country_store = {
	if = {
		limit = { local_var:te_dg_c_pr_$P$_p > 0 }
		set_variable = { name = te_dg_pr_$P$ value = { value = local_var:te_dg_c_pr_$P$_w divide = { value = local_var:te_dg_c_pr_$P$_p min = 0.00001 } } }
	}
}
```

Wire the call sites in `te_demog_effects.txt` and `te_demog_values.txt` as the Files list says. `te_demog_tfr`'s comment
becomes "children per woman = wealth x natural x the practices x (1 - means x (1 - desired)) (spec §2.3;
demographics_model.fertility; the practices, te_demog_practice_effects.txt)". In the header's variable list, beside
`te_dg_natural`, add:

```
#   te_dg_pr_lm, te_dg_pr_bs  the practices' shares, Late Marriage and Birth Spacing, 0-1 (te_demog_practice_effects.txt;
#                       a country's: its states' people-weighted mean)
```

- [x] **Step 5: Run the tests, the formatter and the audits**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/te_demog_practice_effects.txt common/scripted_effects/te_demog_effects.txt common/script_values/te_demog_values.txt
$V -m unittest test_demographics_registry test_gen_demographics test_demographics_model > /tmp/claude-1000/t8.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t8.txt
for a in script_argument_audit empty_effect_audit duplicate_key_audit silent_variable_audit; do $V $a.py --strict || echo "FAIL $a"; done
head -c 3 common/scripted_effects/te_demog_practice_effects.txt | od -An -tx1
```
Expected:
- `OK` and no `FAIL`;
- the BOM bytes `ef bb bf`, exactly once (`head -c 6` must not show them twice).

- [x] **Step 6: Commit**

```bash
git add common/scripted_effects/te_demog_practice_effects.txt common/scripted_effects/te_demog_effects.txt common/script_values/te_demog_values.txt test_demographics_registry.py
git commit -m "Demographics: the census seeds and drifts Late Marriage and Birth Spacing, and its children per woman takes them"
```

---

### Task 9: Primogeniture's farm births under Full (call 4)

> **Built 2026-10-12: Plan A, without the probe.** The owner dropped the probe as a gate the same day: the build ships
> Plan A with a self-check (`te_debug_demog_pr_selfcheck_start`, `te_debug_demog.5`) that logs `TE_SELF_CHECK OK` or
> `BROKEN` once a game; BROKEN means swap in Plan B. Task 12's in-game list moved to `docs/testing/demographics-playtest.md`
> and no longer blocks the merge.

**The engine question first (review C2).** Plan A moves Primogeniture's line onto a script-only type on a *state*
`add_modifier` with a multiplier (the agrarian share). Whether the engine sums that type scaled by the multiplier is
unverified:
- #892 checked script-only types on laws, technologies and institutions;
- the only scaled script-only types the mod adds today are at country scope (`un_vote_cast_effects.txt:119`,
  `un_regime_effects.txt:164`);
- if the engine doesn't scale it, Plan A changes Primogeniture's farm births **outside Full**, under the default rule,
  against owner rule 1.

So Step 1 builds a console probe. The owner runs it on this branch after Task 8, before Plan A lands. Plan A is built
only if the probe reads the scaled value; otherwise Plan B, the fallback. Either way, the in-game check in Task 12
(Disabled, a farming state, the line at 0.1 × its agrarian share) **blocks the merge**.

**Files:**
- Step 1 (the probe):
  - modify `common/static_modifiers/te_debug_demog_modifiers.txt`, `events/te_debug_demog_events.txt` (option o and
    the hidden `te_debug_demog.2`), `common/scripted_effects/te_debug_demog_effects.txt`,
    `common/script_values/te_debug_demog_values.txt` (`te_debug_demog_line_absorbed_b`, which Task 10's option l also
    reads) and `localization/english/te_events_l_english.yml`;
  - test: `test_demographics_registry.py` (`TestConsole`).
- Plan A:
  - modify `common/static_modifiers/te_inheritance_modifiers.txt`, `common/scripted_effects/te_inheritance_effects.txt`
    and `localization/english/te_concepts_l_english.yml`;
  - test: `test_demographics_registry.py`, `test_release_census_inputs.py`.
- Plan B: the same three files and tests, differently.

**Interfaces:**
- Consumes: #892's `te_demog_line_births` (it sums `state_demog_absorbed_birth_rate_mult`), `te_demog_lines_refresh`,
  `te_demog_events.4`, `te_demog_lines_apply`.
- Produces: the console's option o and `TE_DEMOG_PROBE` lines; `te_debug_demog_line_absorbed_b`.

- [x] **Step 1: The probe** (console option o)

The test, in `TestConsole`, beside option m's:

```python
    def test_option_o_probes_a_scaled_script_only_type_on_a_state(self):
        """The late-marriage plan, Task 9 (review C2): Primogeniture's farm births would ride a script-only type on a
        state modifier with a multiplier; the probe adds one at 0.62 and logs the state's sum before and a day after."""
        console = _text(DEBUG_EVENTS)
        call = "te_debug_demog_probe_start = yes"
        self.assertEqual(console.count(call), 1)
        guard = console[console.rindex("limit = { has_variable = te_dg_dbg_click }", 0, console.index(call)):
                        console.index(call)]
        self.assertIn("remove_variable = te_dg_dbg_click", guard)
        mods = _text(ROOT / "common" / "static_modifiers" / "te_debug_demog_modifiers.txt")
        self.assertRegex(_block(mods, "te_debug_demog_scaled_probe"), r"state_demog_absorbed_birth_rate_mult = 0\.1\b")
        start = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_probe_start")
        self.assertIn("add_modifier = { name = te_debug_demog_scaled_probe multiplier = 0.62 }", start)
        self.assertIn("trigger_event = { id = te_debug_demog.2 days = 1 }", start)
        after = _block(console, "te_debug_demog.2")
        self.assertIn("remove_modifier = te_debug_demog_scaled_probe", after)
        values = _text(ROOT / "common" / "script_values" / "te_debug_demog_values.txt")
        self.assertIn("value = modifier:state_demog_absorbed_birth_rate_mult",
                      _block(values, "te_debug_demog_line_absorbed_b"))
```

The static modifier (`te_debug_demog_modifiers.txt`):

```
# The engine-scaling probe (te_debug_demog.1 option o; docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md,
# Task 9): does a script-only type on a state's add_modifier sum scaled by its multiplier? Primogeniture's farm births
# would ride one. Console only; the probe removes it a day later.
te_debug_demog_scaled_probe = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
	state_demog_absorbed_birth_rate_mult = 0.1
}
```

Its name and description go beside `te_demog_debug_working_adults` in `te_miscellaneous_l_english.yml`
(`loc_coverage_audit --strict` requires both for a static modifier): `te_debug_demog_scaled_probe:0 "Test: Engine
Scaling Probe"` and a `_desc` that says it is the console's one-day probe.

The effect (`te_debug_demog_effects.txt`, appended; add a `TE_DEMOG_PROBE` line to the header's list):

```
# ---- o: the engine-scaling probe (the late-marriage plan, Task 9) ----------------------------
# THIS = the capital: log its absorbed births sum, add te_debug_demog_scaled_probe (+0.1 on the type) at multiplier
# 0.62, and log the sum again a day later (te_debug_demog.2), when the engine has summed it. after - before reads
# 0.062 if the engine scales the type by the multiplier, 0.1 if it doesn't, 0 if it doesn't sum it at all.
te_debug_demog_probe_start = {
	debug_log = "TE_DEMOG_PROBE before absorbed_b=[THIS.ScriptValue('te_debug_demog_line_absorbed_b')|5] date=[TimeKeeper.GetCurrentDate.GetString]"
	debug_log_scopes = yes
	add_modifier = { name = te_debug_demog_scaled_probe multiplier = 0.62 }
	trigger_event = { id = te_debug_demog.2 days = 1 }
}
```

The value (`te_debug_demog_values.txt`):

```
te_debug_demog_line_absorbed_b = {
	value = modifier:state_demog_absorbed_birth_rate_mult
}
```

In `events/te_debug_demog_events.txt`:
- option o, after option n, built as option n is (without its `te_demog_cohorts_run` trigger): `name = te_debug_demog.1.o`, trigger `exists = capital`, and the
  `te_dg_dbg_click` guard around `capital = { te_debug_demog_probe_start = yes }`;
- the hidden state event, after `te_debug_demog.1`:

```
# The probe's second half (option o): a day after the add, the state's sum and the probe off again.
te_debug_demog.2 = {
	type = state_event
	hidden = yes

	immediate = {
		debug_log = "TE_DEMOG_PROBE after absorbed_b=[THIS.ScriptValue('te_debug_demog_line_absorbed_b')|5] date=[TimeKeeper.GetCurrentDate.GetString]"
		debug_log_scopes = yes
		if = {
			limit = { has_modifier = te_debug_demog_scaled_probe }
			remove_modifier = te_debug_demog_scaled_probe
		}
	}
}
```

Add option o to the header's list: "o  the engine-scaling probe (Task 9 of the late-marriage plan): a script-only type on
the capital's state modifier at multiplier 0.62 (TE_DEMOG_PROBE)". Add the loc keys `te_debug_demog.1.o` ("Probe: a
scaled script-only type on the capital") and `te_debug_demog.1.o.tt`. Run the test, `orphaned_event_audit.py --strict`
and `event_image_audit.py --strict`, then commit:

```bash
git add common/static_modifiers/te_debug_demog_modifiers.txt events/te_debug_demog_events.txt common/scripted_effects/te_debug_demog_effects.txt common/script_values/te_debug_demog_values.txt localization/english/ test_demographics_registry.py
git commit -m "Demographics console: option o probes a scaled script-only type on a state modifier"
```

**The owner runs it** (deploy per CLAUDE.md "Play-testing unmerged work"; the branch now holds Tasks 1–8, so it is
whole):
- start a throwaway new game, rule Disabled, and play a few days;
- fire `event te_debug_demog.1`, option o;
- unpause for two days;
- copy the two `TE_DEMOG_PROBE` lines from `debug.log`.

`after − before` decides:
- **0.062 (within 0.001): Plan A.**
- **0.1 or 0: Plan B.** Write which into the results doc and into `docs/guides/scripting_best_practices.md` (the engine
  fact), and record it in §1-style "verified" form in this plan's D3.

- [ ] **Step 2, Plan A: write the failing tests**

```python
class TestPrimogenitureUnderFull(unittest.TestCase):
    """Call 4 (the late-marriage spec 4.5; plan D3, Plan A): Primogeniture's +10% farm births ride the absorbed family,
    so under Full the census's Late Marriage replaces them and nothing changes outside Full."""

    MODS = ROOT / "common" / "static_modifiers" / "te_inheritance_modifiers.txt"

    def test_the_line_sits_on_the_absorbed_family(self):
        body = _block(_text(self.MODS), "inh_primogeniture_rural")
        code = re.sub(r"#[^\n]*", "", body)
        self.assertNotRegex(code, r"\bstate_birth_rate_mult\b")
        self.assertRegex(code, rf"\b{P.ENGINE_LINE_TYPES[('absorbed', 'state_birth_rate_mult')]} = 0\.1\b")
        self.assertRegex(code, r"\bstate_migration_quota_mult = 0\.2\b", "the migration line stays")
        # Forced Heirship's -0.15 stays on its engine field: on top under Full (spec 4.5, parent 13: phase 3)
        self.assertRegex(_block(_text(self.MODS), "inh_forced_heirship_rural"), r"state_birth_rate_mult = -0\.15")

    def test_the_rural_refresh_fires_the_lines_refresh(self):
        """No month's lag (#892's owner decision 2): the pair follows the yearly rural refresh the same day, from a
        state event, where the modifier just added is visible."""
        body = re.sub(r"#[^\n]*", "", _block(_text(INH_EFFECTS), "te_inh_refresh_rural_effects"))
        self.assertIn("trigger_event = { id = te_demog_events.4 }", body)
        self.assertGreater(body.rindex("trigger_event = { id = te_demog_events.4 }"),
                           body.rindex("name = inh_primogeniture_rural"))
```

And in `TestLinesScript`, which drives `te_demog_lines_refresh` with the families' sums as fixtures (`self._eng`). The
fixture comes from the modifier file, so the tests fail until the line moves (review I4):

```python
    def _primogeniture_line(self):
        body = re.sub(r"#[^\n]*", "", _block(_text(ROOT / "common" / "static_modifiers" / "te_inheritance_modifiers.txt"),
                                              "inh_primogeniture_rural"))
        m = re.search(r"\bstate_demog_absorbed_birth_rate_mult = (-?[\d.]+)", body)
        self.assertIsNotNone(m, "Primogeniture's birth line isn't on the absorbed family's type")
        return float(m.group(1)) * 0.62   # the modifier's multiplier, an agrarian share of 0.62

    def test_the_pair_carries_primogeniture_outside_full(self):
        """Review Focus 4: outside Full the pair re-applies the line at 0.1 x the agrarian share, as main's own line
        did (given that the engine sums the type scaled, which the probe and Task 12's blocking check confirm)."""
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
```

In `test_release_census_inputs.py`'s `test_the_moved_engine_lines_ship`, add:

```python
        mods = self._text("common/static_modifiers/te_inheritance_modifiers.txt")
        self.assertRegex(mods, r"(?m)^\tstate_demog_absorbed_birth_rate_mult = 0\.1$",
                         "a release keeps Primogeniture's farm births: the pair re-applies them")
```

Run: `$V -m unittest test_demographics_registry.TestPrimogenitureUnderFull test_demographics_registry.TestLinesScript test_release_census_inputs`
Expected: FAIL (the field is still `state_birth_rate_mult`; no `trigger_event`).

- [ ] **Step 3, Plan A: move the line**

```
# Primogeniture & Entail: large families, and the younger sons leave the
# land. The birth line sits on the moved lines' absorbed family
# (docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md, Task 9;
# the late-marriage spec 4.5, call 4): outside the Demographics rule's Full
# setting the moved lines' pair re-applies it (Laws and Institutions in a
# state's birth rates), and under Full the census's Late Marriage takes its
# place, since impartible inheritance raises it. Forced Heirship's line
# stays an engine field, on top of the census under Full (phase 3).
inh_primogeniture_rural = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds
	state_demog_absorbed_birth_rate_mult = 0.1
	state_migration_quota_mult = 0.2
}
```

In `te_inh_refresh_rural_effects`, record whether Primogeniture's modifier was on before the removals: add
`set_local_variable = { name = te_inh_pr_was value = 1 }` inside the existing
`if = { limit = { has_modifier = inh_primogeniture_rural } … }`. Then, at the end of the effect:

```
	# the moved lines' pair carries Primogeniture's farm births: refresh it now, from a state event, where the
	# modifier just added or removed is visible (add_modifier isn't, inside this effect)
	if = {
		limit = {
			OR = {
				has_local_variable = te_inh_pr_was
				owner ?= { has_law = law_type:law_primogeniture }
			}
		}
		trigger_event = { id = te_demog_events.4 }
	}
```

`has_local_variable` exists in 1.14.5 (`docs/engine/triggers_summary.txt:1198`). If `trigger_event` without `days`
turns out to run before the add is visible, the pair follows at the next monthly pulse, a month or less (Risks).

- [ ] **Step 4, Plan A: the text** (`te_concepts_l_english.yml`)

`inh_primogeniture_rural_desc` becomes the following. It is worded as the absorbed type's own description is, without
naming the rule, which a release removes (review I5):

`"Families are large, and the younger sons leave to make their own way. Scaled by the state's share of Peasants and Farmers. Where the demographic census sets a state's births and deaths, its late marriage takes the place of the larger families."`

Run `python3 organize_loc.py` and keep what it moves.

- [ ] **Steps 2–4, Plan B instead** (the probe read 0.1 or 0)

D3's rejected swap, now the fallback:
- `inh_primogeniture_rural` keeps `state_birth_rate_mult = 0.1`.
- A twin, `inh_primogeniture_rural_census`, carries only `state_migration_quota_mult = 0.2`. It has the same icon and
  the name `$inh_primogeniture_rural$`, and its `_desc` is Step 4's text without the birth clause, plus "Its late
  marriage takes the place of the larger families here."
- In `te_inh_refresh_rural_effects` (still the one refresh site of both), remove the twin with the others. In the
  Primogeniture branch, apply the twin where the census sets the state's births, and the original elsewhere:

```
		else_if = {
			limit = { owner = { has_law = law_type:law_primogeniture } }
			if = {
				limit = {
					te_demog_effects_run = yes
					has_variable = te_dg_mb
				}
				add_modifier = {
					name = inh_primogeniture_rural_census
					multiplier = var:te_inh_agrarian_share
				}
			}
			else = {
				add_modifier = {
					name = inh_primogeniture_rural
					multiplier = var:te_inh_agrarian_share
				}
			}
		}
```

- Accept a one-year transition: the census's refresh runs in the same effect as the swap, so its read of the state's
  birth rate still holds the +10% for one step, and M takes it off a year late. Since #907 the refresh also stores
  the next window's start rate (`te_dg_sr_b`, from the walk's `te_dg_w_eb`), which the walk read before the swap, so
  the old +10% rides one window, start rate included.
- Tests:
  - the twin carries no `state_birth_rate_mult`, and the original keeps its 0.1;
  - the rural refresh applies the twin only inside a limit holding both `te_demog_effects_run = yes` and
    `has_variable = te_dg_mb` (static, since `_Engine` can't parse `owner ?=`);
  - `test_only_the_wrappers_read_the_rule` still passes (the swap calls the wrapper);
  - the release test: a release has no rule, so the original always applies.
- No `trigger_event`: nothing re-applies through the pair.

- [ ] **Step 5: Run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/static_modifiers/te_inheritance_modifiers.txt common/scripted_effects/te_inheritance_effects.txt
$V -m unittest test_demographics_registry test_release_census_inputs > /tmp/claude-1000/t9.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t9.txt
$V organize_loc.py --check; $V loc_coverage_audit.py --strict
```
Expected: `OK`; `--check` exits 0.

- [ ] **Step 6: Commit**

```bash
git add common/static_modifiers/te_inheritance_modifiers.txt common/scripted_effects/te_inheritance_effects.txt localization/english/ test_demographics_registry.py test_release_census_inputs.py
git commit -m "Demographics: under Full, Late Marriage replaces Primogeniture's farm births (call 4)"
```

`git add localization/english/` stages everything `organize_loc.py` rewrote there. Check `git status` first, and stage
only the files it touched.

- [ ] **Stop B (fresh review).** A fresh reviewer, on the most capable model, reads Tasks 7–9's diff against this plan,
  the Global Constraints and Review Focus 1–4. What to check:
  - the seed's sibling rule and its eroded fallback;
  - that a re-seed keeps the shares;
  - the step's order before `te_demog_prepare`;
  - fast mode's clock (`te_demog_events.2` → the census → `te_demog_step_begin`), which must step the practices once a
    clock year;
  - every `divide`;
  - the plan Task 9 took, against the probe's reading;
  - that nothing new reads the rule except through its wrappers.

  Fix what it finds before Task 10. Batch reviews of the earlier tasks aren't needed: Tasks 1–6 are Python with their
  own tests, and Stop A reviewed the numbers.

---

### Task 10: The panel, the console and the loc

**Files:**
- Modify: `localization/english/te_miscellaneous_l_english.yml`: `te_demog_st_tfr_terms`, `te_demog_ov_tfr_capital`,
  `te_demog_st_tfr_tt`, `te_demog_ov_tfr_tt`, and the "How Demographics Works" text, `te_demog_how_fertility`, which
  carries the same "who marries and how young" phrase (D2)
- Modify: `localization/english/te_modifiers_l_english.yml`: `state_natural_fertility_mult_desc` ("through who marries
  and how young… they marry later"; D2 drops the phrase)
- Modify: `common/scripted_effects/te_debug_demog_effects.txt` (`te_debug_demog_mods_line`),
  `common/script_values/te_debug_demog_values.txt`
- Test: `test_demographics_registry.py`

- [x] **Step 1: Write the failing tests** (in `TestNaturalFertilityScript`, beside the tooltip tests)

```python
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
```

- [x] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_registry.TestNaturalFertilityScript`
Expected: FAIL.

- [x] **Step 3: The loc.** Keep each key's existing lines and splice in the new ones.

`te_demog_st_tfr_terms`: after the `Women's legal standing` line, add

` Late marriage: ×#v [State.MakeScope.ScriptValue('te_demog_pr_term_lm')|2]#! (women marry at about #v [State.MakeScope.ScriptValue('te_demog_marriage_age')|0]#!)\n Birth spacing: ×#v [State.MakeScope.ScriptValue('te_demog_pr_term_bs')|2]#!\n`

`te_demog_ov_tfr_capital`:
- at its start, add
  `Across [GetPlayer.GetName]: women marry at about #v [GetPlayer.MakeScope.ScriptValue('te_demog_marriage_age')|0]#!, and #v [GetPlayer.MakeScope.ScriptValue('te_demog_pr_share_bs')|%0]#! of families space births by custom.\n`
- after its `Women's legal standing` line, the same two lines as the state's, with `GetPlayer.GetCapital.MakeScope` for
  `State.MakeScope`.

In `te_demog_st_tfr_tt` and `te_demog_ov_tfr_tt`, replace

"Wealth sets how many children couples would have with nothing holding them back, and women's legal standing moves that
through who marries and how young."

with

"Wealth sets how many children couples would have with nothing holding them back. Women's legal standing moves that, and
two customs lower it: late marriage, where women marry in their mid-twenties and many never marry, and birth spacing,
where couples space and stop births by custom. Both fade as modern contraception spreads, and birth spacing fades with
health care too; women's paid work and farms that pass whole to one heir make late marriage more common."

The country tooltip keeps its "the states' figures, weighted by their women aged 15 to 49" clause.

- [x] **Step 4: The console's line** (`te_debug_demog_values.txt`)

```
te_debug_demog_pr_lm = { value = 0 if = { limit = { has_variable = te_dg_pr_lm } value = var:te_dg_pr_lm } }
te_debug_demog_pr_bs = { value = 0 if = { limit = { has_variable = te_dg_pr_bs } value = var:te_dg_pr_bs } }
te_debug_demog_pr_target_lm = { value = te_demog_pr_target_lm }
te_debug_demog_pr_target_bs = { value = te_demog_pr_target_bs }
```

Format them as the file's other blocks (one field a line). `te_debug_demog_line_absorbed_b` is Task 9's probe's. Append to `te_debug_demog_mods_line`'s `debug_log` string:

` lm=[THIS.ScriptValue('te_debug_demog_pr_lm')|3] bs=[THIS.ScriptValue('te_debug_demog_pr_bs')|3] lm_target=[THIS.ScriptValue('te_debug_demog_pr_target_lm')|3] bs_target=[THIS.ScriptValue('te_debug_demog_pr_target_bs')|3] absorbed_b=[THIS.ScriptValue('te_debug_demog_line_absorbed_b')|3]`

Add `lm=`, `bs=`, `lm_target=`, `bs_target=` and `absorbed_b=` to the header comment's description of option l's line.

- [x] **Step 5: Run the tests and the loc checks**

```bash
python3 organize_loc.py
$V -m unittest test_demographics_registry > /tmp/claude-1000/t10.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t10.txt
$V organize_loc.py --check; $V scripts/analysis/check_localization_files.py; $V loc_render_audit.py --strict; $V script_loc_reference_audit.py --strict
python3 scripts/analysis/check_gui_lint.py
```
Expected: `OK`; every check exits 0.

**Amended at the build (2026-10-12):**
- `state_natural_fertility_mult_desc` now reads "through their standing inside marriage … they have more say over how
  many children they have" (the owner's wording for the natural term), and the test checks it no longer claims who
  marries.
- The console's two targets read -1 on a state with no census, as option l's cause multipliers do. Option l also logs
  an unincorporated state, where the walk's variables the targets read don't exist.

- [x] **Step 6: Commit**

```bash
git add localization/english/ common/scripted_effects/te_debug_demog_effects.txt common/script_values/te_debug_demog_values.txt test_demographics_registry.py
git commit -m "Demographics panel: Late Marriage and Birth Spacing in the children-per-woman tooltips; option l logs them"
```

Stage only the loc files `git status` shows changed.

---

### Task 11: Docs and the player guide

**Files:**
- Modify: `docs/systems/mod_systems.md` § Demographics:
  - the opening paragraph and "Not built yet" (the pointer this plan's PR added becomes "built");
  - the file table (`te_demog_practice_effects.txt`, `demographics_regions.py`, `demographics_practices.py`,
    `demographics_strategic_regions.json`);
  - Variable families (`te_dg_pr_<P>`);
  - a new subsection "Late Marriage and Birth Spacing" after "Family Limitation": the formula, the start tables in one
    sentence each, the drift and its drivers, the seed rule (D5), the panel, Call 4's line;
  - "Absorbed by the census" (Primogeniture's farm births);
  - "Generator and harness" (`practices-replay`, `practices-fit`; the regional gate on #904's peacetime rates);
  - the console's option o (Task 9's probe) in the Files table's "Test console" row (beside "options m and n are
    phase 2's probes");
  - "Owner checks in game" (point to this plan's list).
- Modify: `docs/superpowers/specs/2026-10-10-demographics-late-marriage-design.md`:
  - a note under §2.2 that the curve's base is 6.0 since #869 and the fit's values are the plan's (D1);
  - §3.4's seed rule as built (D5);
  - §5.2's gate as the owner ruled it on 2026-10-11 (D12): regional growth is the gate; the raise is the smallest neat
    value that passes it; the high group's ~7 is reported only; calibration step 3 follows separately.
- Modify: `docs/superpowers/plans/2026-10-10-demographics-phase2-calibration.md` step 2 (built: the fitted values and
  the results doc).
- Modify: `docs/guides/python_tools.md` (the harness's row: "Fourteen commands" becomes "Sixteen", with
  `practices-replay`, `practices-fit` and `history`'s three options; a row for `demographics_regions.py`; option o in the console's row).
- Modify: `docs/auto_generated_files.md` (a row for `demographics_strategic_regions.json`: written by
  `demographics_regions.py --refresh` from the base game's strategic regions and the mod's REPLACEs; one-shot).
- Modify: `docs/guides/vanilla_patch_runbook.md` (beside `gen_formable_regions.py`: "`demographics_regions.py --check`;
  `--refresh` when it says stale").
- Modify: `docs/player_guide/08-states.md` § Demographics, "Reading the figures" and the Full paragraph;
  `docs/player_guide/06-politics.md` (one sentence).
- Rebuild: `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`.

**Amended at the build (2026-10-12):** call 4's text waits for Task 9's Plan A or B (the probe). That covers
mod_systems' "Absorbed by the census" bullet and call 4's line in the new subsection, the Full paragraph's Primogeniture
item in `08-states.md`, and both edits to `06-politics.md`. It lands with Task 9's Steps 2–6. Until then
mod_systems' "Not built yet" names call 4. "Reading the figures" says birth spacing is "strongest in Japan and slight
in China and Korea", since the fit set India's start to 0 and East Asia's to 0.06.

- [x] **Step 1: The player guide** (match the depth already there: one change in each place)

In `08-states.md`, "Reading the figures", replace

"Children per woman follows wealth and women's legal standing (where women work the fields, own property, hold jobs or
vote, they marry later and have fewer children), then falls with literacy, child survival and city life."

with

"Children per woman follows wealth and women's legal standing, and two customs lower it. Under late marriage, strongest
at the start in north-western and central Europe, women marry in their mid-twenties and many never marry; under birth
spacing, strongest in Japan and found in China, Korea and India, couples space and stop births by custom. Modern
contraception wears both away, and health care wears away birth spacing; women's paid work and farms that pass whole to
one heir make late marriage more common. The figure then falls with literacy, child survival and city life."

In the Full paragraph, the list of effects the census models gains "Primogeniture & Entail's larger farm families (its
late marriage stands in for them)" after the women's rights laws.

In `06-politics.md`:
- after "under Primogeniture & Entail families are large and the younger sons leave the land.", add: "Under the
  Demographics rule's Full setting, the census's late marriage takes the place of the larger families.";
- in the Who inherits table (line 294), Primogeniture & Entail's "In farming states, birth rate and migration up"
  becomes "In farming states, birth rate (not under the Demographics rule's Full setting) and migration up".

- [x] **Step 2: The other docs** as listed above. Two of them need care:
  - `docs/guides/python_tools.md` is long and LF; edit it with the Edit tool.
  - Check the three CRLF docs aren't touched:
    `grep -c $'\r$' docs/systems/journal_entry_systems.md docs/guides/gui_modding_guide.md docs/vanilla/treaty_articles_reference.md`
    should give the same counts before and after.

- [x] **Step 3: Run the docs checks**

```bash
$V scripts/analysis/check_player_guide_style.py --strict
$V scripts/build_player_guide.py
$V scripts/build_player_guide.py --check
$V scripts/analysis/check_post_load_rosters.py
```
Expected: the lint is clean and `--check` exits 0.

- [x] **Step 4: Commit**

```bash
git add docs/systems/mod_systems.md docs/superpowers/specs/2026-10-10-demographics-late-marriage-design.md docs/superpowers/plans/2026-10-10-demographics-phase2-calibration.md docs/guides/python_tools.md docs/auto_generated_files.md docs/guides/vanilla_patch_runbook.md docs/player_guide/08-states.md docs/player_guide/06-politics.md docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf
git commit -m "Demographics: docs and the player guide for Late Marriage and Birth Spacing"
```

---

### Task 12: The offline gate, the whole-branch review and the owner's list

**Files:**
- Modify: `docs/testing/demographics-late-marriage-<date>.md` (the gate's results, the in-game list as "Still to run")

- [ ] **Step 1: The offline checks**

```bash
$V -m unittest discover -s . -p 'test_*.py' > /tmp/claude-1000/suite.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/suite.txt
/home/jakef/src/Vic3TimelineExtended/.venv/bin/ruff check .
python3 scripts/format_paradox_tabs.py --check $(git diff --name-only origin/main -- '*.txt')
$V organize_loc.py --check
$V scripts/generators/gen_demographics.py --check
for a in script_argument_audit loc_coverage_audit empty_effect_audit modifier_multiplier_var_audit duplicate_key_audit silent_variable_audit iterator_limit_audit prev_scope_audit; do $V $a.py --strict || echo "FAIL $a"; done
grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" scripts/analysis/demographics_*.py scripts/generators/gen_demographics.py test_demographics_*.py
$V scripts/analysis/demographics_harness.py fertility; $V scripts/analysis/demographics_harness.py medicine
```

Expected:
- the suite prints `OK`;
- ruff finds nothing, and no audit prints `FAIL`;
- the f-string grep prints nothing;
- neither scenario command prints `OUT`.

- [ ] **Step 2: The gate's offline half on the normal-speed run's saves**

Task 6 Step 5's run at the chosen point is the gate's record (the projection compares with today's parameters, so it
isn't re-run on the applied build; Task 6 Step 8 checked that the applied values reproduce the point). Copy into the
results doc, each with its figure:
- **the regional growth gate** (owner, 2026-10-11; D12): each of #904's groups inside its band; the world at or below
  today's less about 1 per 1,000; China inside +3 to +6; no country of 20M or more shrinking. A failure that only a
  geographic mortality term could fix is named for calibration step 3, a separate step after this work;
- Britain's, Sweden's and Denmark's life expectancy within 3 years of 41 in 1837;
- every `fertility` and `medicine` scenario in band (this branch's commands, Step 1);
- the replay: no `GATE` line up to 1887;
- reported, not judged: the children-per-woman error over the anchor countries (the spec's 0.5) and each country more
  than 0.5 off, the world's children per woman against today's, and the high-fertility group against history's ~7.

**The game's own shares against the model's (Stop B, M2; build it here).** The harness reads a save's `te_dg_pr_*`
(`practice_states`' `stored`, `saved_shares`, `history`, `practices-fit`). The check that steps them is still to
build: a `practices-check SAVE_A SAVE_B` on two yearly plain-text saves from a game on this branch.
- For each state holding shares in both saves that stepped once between them (`te_dg_stepped`, `te_dg_year`), predict
  B's share as `M.practice_drift(A's share, target)`.
- Take the target at the inputs the step used: the walk's `te_dg_lit`, `te_dg_agr_share` and `te_dg_fjob_share`,
  the stored `te_dg_acc`, and B's owner laws and techs.
- Compare with B's share. The tolerance is a few × 1e-5 (five-decimal storage; the drift stalls once 0.025 × the gap
  is under 1e-5), and a law or tech changed between the step and the save excuses a state.
- Run it on the first two yearly saves of the in-game list's Full game (Step 4).

- [ ] **Step 3: Stop C (fresh whole-branch review).** A fresh reviewer on the most capable model reads the whole branch
  against the spec and this plan. Fix what it finds, re-run Step 1, and commit.

- [ ] **Step 4: The owner's in-game list** (write it into the results doc's "Still to run"; the owner deploys per
  CLAUDE.md "Play-testing unmerged work")

  1. **A new 1836 game under Full, Britain.**
     - The Population panel's children-per-woman tooltip shows "Late marriage ×0.70" (or the fitted cut) and "women
       marry at about 26", with "Birth spacing ×1.00".
     - The country line reads about 26 and 0%.
     - Open a Japanese state's Demographics subtab: "Birth spacing" ×0.65 (or 1 − the fitted cut), "Late marriage"
       ×1.00, women marry at about 19.
     - A state in Posen: ×0.76 at 0.8 and about 25.
  2. **Option l** (`event te_debug_demog.1`) on the capital after its first census step: `lm=1.000`, `bs=0.000`, and
     `lm_target` near 1. Under Plan A, `absorbed_b` holds 0.1 × the capital's agrarian share on top of the laws' own
     absorbed birth lines (No Women's Rights' +0.05), as Task 9's probe found.
  3. **Blocks the merge (review C2): Disabled, a new game, a farming state in Britain** (Primogeniture). After its first
     yearly pulse, its birth-rate breakdown shows Primogeniture's farm births at +10% × its Peasants' and Farmers'
     share, as on `main`:
     - under Plan A, as a Laws and Institutions line that day, and no "Cadet Sons Leave the Land" birth line;
     - under Plan B, as "Cadet Sons Leave the Land" itself.

     The modifier still shows its migration line. Any other figure, under either plan, stops the merge.
  4. **Full, the same state after its first census step:** no Laws and Institutions birth line, Census: Births present,
     and option n's `q_b` at 0.
  5. **A split state.** Release or annex part of a state region (debug). At its next census, the new state's option l
     shows its sibling's `lm` and `bs`, not the table's.
  5b. **A whole state region changing hands** (Stop B, I1). Give a whole state region to another country by debug, or
     let a revolution win. At the new state's first census option l shows the region's copy: the old state's last
     `lm` and `bs`, not its start less what its conditions have eroded. Its ring and medicine re-seed, as before.
  6. **An old save.** Load a Full save made before this build. Before each state's next yearly pulse its tooltip shows
     ×1.00 for both practices; after it, its seed: the table less what its conditions have eroded (a late save's Japan
     well below ×0.65's spacing).
  7. **Fast mode** (option h) for a few clock years: the capital's `lm` moves once a clock year, toward `lm_target`.
  8. **`debug.log`:** no error from `te_demog_practice_effects.txt`, the generated `te_demog_pr_*` values, `region =
     sr:` or `state_region = s:` lookups (an unknown key logs "Invalid strategic region"), or `te_demog_events.4` fired
     from the rural refresh.
  9. **Optional, for phase 3** (spec §4.4): in the console, does `every_neighbouring_state` from a British state include
     a French one? Log `any_neighbouring_state = { owner = c:FRA }` from STATE_HOME_COUNTIES.

- [ ] **Step 5: Commit**

```bash
git add docs/testing/demographics-late-marriage-<date>.md
git commit -m "Demographics: Late Marriage and Birth Spacing, the offline gate and the in-game list"
```

## Review stops

| Stop | After | Who | What |
|---|---|---|---|
| A | Task 6 | the owner | The chosen point (the smallest raise the regional gate passes), the regional table and the gate, with Owner questions 1–3. No script before the owner's word. **Decided 2026-10-12: option 2, the fit's fertility at today's mortality** |
| The probe | Task 9 Step 1 | the owner, in a throwaway game | Option o's two lines: Plan A or Plan B |
| B | Task 9 | a fresh reviewer (most capable model) | Tasks 7–9: the risky script (seed, step, Primogeniture's line), per Review Focus 1–4 |
| C | Task 12 Step 3 | a fresh reviewer (most capable model) | The whole branch against the spec and this plan |

Then the owner's in-game list (Task 12 Step 4). Its item 3 blocks the merge.

## Risks

- **The raise lifts growth where neither practice holds** (D12). The Middle East, Russia, Africa and the Americas get
  every point of the raise in births. So the gate takes the smallest raise it passes, possibly none.
  - Matching growth may leave the high-fertility group's children per woman below history's ~7 unless their mortality
    rises. The owner accepts that (2026-10-11).
- **Two knobs may not move mortality the right ways.** Step 1's poverty term and base infection read SoL, which doesn't
  separate Britain (needs fewer deaths) from Mexico (needs more), as §1.4 found for fertility.
  - If no neat point passes, Task 6 takes the smallest raise with the fewest failures and names the regions only a
    geographic term could fix.
  - Calibration step 3, that term, is a separate step after this work (owner, 2026-10-11).
- **The projection is first-order.** It holds each state-year's age structure and its own measured rates, and scales
  births by the change in children per woman and deaths by the change in expected deaths at its census bands. It
  doesn't follow the extra people the raise would add over decades, so it understates a raise's compounding. The
  normal-speed run after this work is the check.
- **The era-3 timing** (spec §4.2). Contraception starts the West's erosion a generation before history's marriage
  boom. Britain 1900 reads about 0.2 low. The fit's means pair and the spec's later trigger (0.35, after the Pill)
  are the comparison; the results doc reports both.
- **The women's-rights overlap** (D2) is at most about 4.5% of births. Owner question 1.
- **Old saves.**
  - States seed at their next census step, at their start less what their conditions have eroded (D5, review I2).
    Seeding at the full target would have put Japan's Late Marriage at about 0.1 in a new game too (its inheritance
    driver), against call 3.
  - Under Plan A, an old Full save's Primogeniture farm states run their births low until each state's next census
    step, up to a year:
    - the modifier's birth line becomes script-only at load, while M was set the year before with that line on top;
    - the next step's M corrects it;
    - the census is experimental and off by default.
- **Performance.**
  - Per state a year: two ladders of about 30 triggers each, two targets, and one sibling walk only when a share is
    missing.
  - Per country census: two sums.
  - No new pop or building walk, no neighbour walk.
  - Saves gain two variables a state (about 0.1 MB) and two a state region (the copy).
- **Fast mode.** The practices step once a clock year, with the census. Literacy, laws and contraception keep the
  calendar, so a fast run's practices erode on 19th-century conditions for longer, as everything else does there.
- **Revolutions and changes of owner** (corrected at Stop B, I1; the region copy built at the owner's word,
  2026-10-12). A change of owner moves the people to a new state object, which carries none of the old one's variables
  (the normal-speed run's saves: Istria through four objects in 20 years, Uruguay's whole state to a revolution's
  winner in 1887).
  - **The shares survive through the siblings or the region's copy.** The seed takes the shares of another piece of
    the state region that still holds them (a region taken piece by piece). Failing that, it takes the copy every step
    writes on the state region (`te_dg_pr_<P>_r`, the last state to step; a state region holds variables,
    scripting_best_practices.md, "Region-Level Data"). That covers a whole region taken at once, typically by a
    revolution's winner. Only a region with neither falls back to its start less what its conditions have eroded, and
    in a new game that is the table.
  - **The census's ring and #916's medicine still re-seed** on a whole-region transfer, as before. A state object with
    no census is seeded (`te_demog_state_census` → `te_demog_seed`): its ring at the stable structure of its own rates,
    and its medicine at its targets (`te_demog_medicine_at_target`).
  - No `on_state_owner_change` hook: the new state object has nothing of the old one's to copy, and the region's copy
    works whatever the hook's timing.
  - A new owner's laws reach the target at the next step.
- **The engine scaling a script-only type on a state modifier** (review C2) is unverified: Task 9's probe decides Plan
  A or B, and Task 12's item 3 blocks the merge.
- **The rural refresh's event (Plan A).** `trigger_event` without `days` is assumed to run after the current effect, so
  the lines refresh sees the modifier just added. #892's hooks assume the same. At worst the pair reads the modifier
  stale until the next monthly pulse, a month or less. The in-game list's item 3 is the check, and `days = 1` the fix
  (#894 carries the same note for the hooks).
- **The release.** A release has no rule, so the census and the practices never run.
  - Under Plan A, Primogeniture's line ships on its moved-lines type, and the pair re-applies it (Task 9's release
    test). Its description doesn't name the rule (review I5).
  - Under Plan B, the original modifier always applies.
