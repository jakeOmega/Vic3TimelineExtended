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
- `docs/superpowers/plans/2026-10-11-demographics-engine-lines-script-only.md` (#892: the absorbed and on-top families);
- `docs/testing/demographics-phase2-engine-rates-2026-10-10.md`, "The normal-speed Full run" (#900) and issue #894.

**Base:** `main` at a8d2b9fc (#900). The other agent's branch `demog-gate-from-saves` edits
`scripts/analysis/demographics_observer_report.py`; this plan never touches that file.

---

## What the code says that the spec doesn't (read before Task 1)

These come from comparing the spec with `main`. Each is settled here, or listed under Owner questions.

**D1. The wealth curve's baseline moved after the fit.** The spec's §2.2 says `WEALTH_TFR_LOW` is 6.2. It has been 6.0
since #869 (merged seventeen minutes after the spec, the owner's step-4 gate decision). The spec's s = 1.15, its §2.3
tables, its §2.4 growth table and §5.2's "today" figures (5.96 / 5.74 children per woman; +1.08 / +0.98% a year) were
all computed on 6.2, on the old gate run's saves, without the natural-fertility term (also #869).
- **Starting values:** s = 1.15 on today's curve (`WEALTH_TFR_LOW` 6.0 → 6.9, `WEALTH_TFR_HIGH` 3.5 → 4.0), cuts 0.30
  and 0.35, the held share 0.38. At these, China and India hold where `main` puts them: 1.15 × (1 − 0.35 × 0.38) =
  0.997.
- The early-marrying group then reaches about 6.6–6.7, not the spec's 6.7–7.0. The spec's reach on today's curve takes
  s ≈ 1.19 (1.15 × 6.2 ÷ 6.0), and a held share near 0.46 to keep China and India where they are.
- Task 6 re-measures "today" on the current build and refits s, the cuts and the held share together. Nothing in this
  plan uses the spec's 6.2-era numbers as a gate.

**D2. The practices join the natural-fertility term.** The spec writes children per woman as wealth × factor. On `main`
it is wealth × natural × factor, where natural is women's legal standing (`state_natural_fertility_mult`, #869).
- The practices multiply beside natural, outside the means.
- The tooltips and the guide say that women's legal standing works "through who marries and how young". That is now
  Late Marriage's mechanism, so Task 10 and Task 11 drop the phrase.
- The women's-rights laws then reach children per woman twice: through natural (up to −15%), and through Late
  Marriage's women's-work driver (target +0.3 × women's job share × the law's women's work share ÷ 0.48, so at most
  about −3% of births at a full job share). Both were approved separately. Owner question 2.

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
- Forced Heirship's −0.15 (`inh_forced_heirship_rural`) is unchanged: call 4 names Primogeniture only. Spec §4.5 and
  parent §13 put Forced Heirship with Family Limitation in phase 3.

**D4. The practices run wherever the census runs.** The census's cohorts run under Full and Display only, and the panel
shows its children per woman under both. Were the practices Full-only, Display only would show the raised wealth curve
with nothing holding it back (Britain 1836 at about 6.3). So the shares seed and drift with the census
(`te_demog_cohorts_run`), and change gameplay only through M (`te_demog_effects_run`). Under Disabled nothing runs and
the shares wait. This plan reads "every new effect acts only under Full" as "every change to births and deaths": the
census's term and call 4's line are the only two, and both are Full-only. If the owner meant the shares too, Task 8's
two call sites gain a `te_demog_effects_run` limit and Display only shows the census without the practices. Owner
question 3.

**D5. A state with no share takes its siblings' mean, not its neighbours'.** Spec §3.4 says a state with no share takes
"the people-weighted mean of its neighbours that have one, else its table value".
- **The problem:** states seed one at a time. On an old save, or a rule switched on mid-game, every state lacks a
  share, and they seed on their own pulse days. A Russian core state seeding after a Baltic neighbour would take 0.8,
  not 0, and a Baltic state seeding after Russian ones would take about 0. Drift at 2.5% a year would take decades to
  undo it.
- **This plan's rule:** the people-weighted mean of the *other states in its state region* that hold a share (a split
  state's siblings: "a split state is the same people as its sibling", §3.4's own reason), else its start.
  Siblings share a start, so mass seeding gives every state its table value in any order.
- Spec §3.4's 1836 rule (table values) is the same rule.
- The start is a generated script value read every year inside the target, so it stores no third variable a state.

**D6. The neighbour spread stays in phase 3**, as spec §4.2 ("the neighbour term arrives in phase 3") and §5.3 place it.
Call 7 approved one machinery with one neighbour spread for both practices and, later, Family Limitation. This plan
builds that machinery per state and parameterised by practice, so phase 3 adds the spread once for all practices.
- The harness has no state adjacency (no save field, no `vanilla_parsed/` entity), so phase 2 couldn't replay a spread
  it shipped.
- Note for phase 3, from the spec's own formula: with the start inside the target, the 0.5% spread is damped about
  5:1 against the 2.5% drift.
- Owner question 4 confirms this reading.

**D7. The terms are read live from the shares; no stored term.** `te_dg_natural` is stored at the step because the
law's modifier can change between steps. A practice's share changes only at a census seed or step, and `te_demog_prepare`
recomputes `te_dg_tfr` right after either. So `te_demog_pr_term_<P>` reads `var:te_dg_pr_<P>` live, as 1 with no share
(an old save's state before its next step, whose `te_dg_tfr` has no practice in it either). That keeps the spec's "two
variables a state".

**D8. Which build reads the normal-speed run's saves** (`/mnt/d/vic3te-data/vic3te-demog-p2-normal-2026-10-11/saves/`,
65 plain-text autosaves, 1837–1901, about 265 MB each, made by ec304526).
- `scripts/analysis/demographics_save_inputs.py` is byte-identical between ec304526 and `main` (Task 6 Step 1 checks
  it again). Its changes in this plan only add fields.
- So these run from this branch on those saves: `history`, `fertility`, `practices-replay`, `practices-fit` and
  `regions`. They read pops, states (owner, incorporation, region), laws, techs, institutions, timed modifiers and a
  state's walk variables.
- `predict` and `fidelity` do not run from this branch on those saves. #892's `predict` treats the moved lines as
  script-only, but at ec304526 they were live engine fields. `fidelity`'s cause multipliers differ by build.
  - #900's baseline (×1.77 from the saves) came from a detached worktree at ec304526.
  - Any `predict` on these saves runs there too:
    `git -C /home/jakef/src/Vic3TimelineExtended worktree add --detach /home/jakef/src/vic3te-ec304526 ec304526`.
- The fit reads Gapminder's and Clio Infra's anchors from `/mnt/d/vic3te-data/history-anchors-2026-10-10/anchors.csv`,
  not the nine-line test fixture.
- Saves are chosen by `save_year` (it reads the first 40 lines): every tenth year from 1837, plus 1887 and 1901.

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
  0.38 by strategic region, as §3.3's table says.
- Japan is the ten state regions Hokkaido to Kyushu: Hokkaido, Tohoku, Kanto, Hokushinetsu, Tokai, Kyoto, Kansai,
  Chugoku, Shikoku and Kyushu (Ryukyu excepted).

**D11. No new script-only modifier type.** The later lever, `state_late_marriage_target_add` (§6), is phase 3. So
`scripts/release/comment_out_census_inputs.py` needs no change.
- Call 4's line moves to an existing moved-lines type, which a release keeps: a release has no rule, so
  `te_demog_lines_apply` holds everywhere and the pair re-applies the +10%.
- Task 9 adds a test that pins this.
- In a release the census never runs, so the practices' values and effects are never called.

## Owner questions (none blocks Tasks 1–5)

1. **The gate's world-growth line (§5.2).**
   - The spec gates "world growth within ±0.1% a year of step 1's (+1.08 / +0.98)", on 6.2-era saves.
   - #894 says the world already runs hot: ×1.77 against a fair ×1.6 by the saves.
   - The raise lifts births wherever neither practice holds: the Middle East, Russia, Africa and the Americas. China,
     India, Korea and Manchuria hold by construction, and Japan and the West fall. So world growth rises unless call 8's
     mortality refit does the work (Mexico's life expectancy reads 40 against history's 23).
   - This plan's gate: world model growth no more than 0.1% a year above today's, re-measured on the normal-speed run's
     saves (Task 6), with each region's growth reported against #894's fair targets.
   - The owner decides at Stop A whether that is the right line, or whether the fit should also bring the world down
     toward ×1.6.
2. **Women's rights twice** (D2). Keep both the natural term and Late Marriage's women's-work driver (proposed: yes,
   since the overlap is at most about 3% of births), or drop the driver?
3. **The shares under Display only** (D4). Proposed: they run with the census, so Display only shows the same children
   per woman as Full.
4. **The spread** (D6). Proposed: phase 3, as the spec has it.

## Global Constraints

- **Nothing changes outside Full (owner, 2026-10-10), in gameplay** (owner, 2026-10-11, #892's framing: same values, on
  the same pops, scaled the same way).
  - Call 4's line changes name in a state's breakdown outside Full ("Laws and Institutions"), not size.
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

## Review Focus

1. **An old save, or a rule switched on mid-game.** Every state lacks a share, and they seed on their own pulse days.
   - Expect: every state gets its own table value, whatever the order.
   - Pinned by Task 8's `test_seeding_order_does_not_matter`; the twin by Task 2's
     `test_a_seed_takes_its_siblings_people_weighted_mean_else_its_start`.
2. **A census re-seed** (a merge, a split, a gap, fast mode's first switch) **keeps the state's shares.** Customs belong
   to the people, and a re-seed only re-counts them.
   - Pinned by Task 8's `test_a_census_reseed_keeps_the_shares`.
3. **A state split mid-game** takes its sibling's drifted shares, not the 1836 table.
   - Pinned by Task 8's `test_a_new_state_takes_its_siblings_shares`.
4. **Under Disabled, Primogeniture's farm births are what `main` gives**, through the pair, and the pair follows the
   yearly rural refresh that day.
   - Pinned by Task 9's `test_the_pair_carries_primogeniture_outside_full` and
     `test_the_rural_refresh_fires_the_lines_refresh`.
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
| The regional growth table on the normal-speed run's saves (#894) | Changing the in-game gate's world measure (#894's own item) |
| Docs, the player guide, the owner's in-game list | The census log's fields (`demographics_observer_report.py`, another branch's file) |

## File structure

| File | Change | Responsibility |
|---|---|---|
| `scripts/analysis/demographics_regions.py` | create | the strategic-region snapshot: parse, refresh, load; the regional report's rows |
| `scripts/analysis/demographics_strategic_regions.json` | create (written by `--refresh`) | `{strategic region: [state regions]}`, land regions only |
| `scripts/analysis/demographics_params.py` | modify | `PRACTICES`, `PRACTICE_CUT`, the start tables, the drift's constants; Task 6's fitted values |
| `scripts/analysis/demographics_model.py` | modify | `Inputs.practices`, `.agrarian_share`, `.impartible`; the terms in `fertility`; `practice_start`, `contraception_beyond`, `practice_erosion`, `practice_target`, `practice_drift`, `practice_seed`, `marriage_age` |
| `scripts/analysis/demographics_save_inputs.py` | modify | `CountryInputs.agrarian` and `agrarian_share`; `state_regions(sections)` |
| `scripts/analysis/demographics_practices.py` | create | a save's states for the practices, the drift replay, the fit, the regional table |
| `scripts/analysis/demographics_harness.py` | modify | `practices-replay`, `practices-fit`, `regions`; `history --shares --incorporated-only`; the scenarios' shares (Task 6) |
| `scripts/generators/gen_demographics.py` | modify | the start ladders, targets, terms, the marriage age, the practice loops, `te_demog_k_practice_rate` |
| `common/scripted_effects/te_demog_practice_effects.txt` | create | the one machinery: `te_demog_practice_seed`, `_step`, `_country_init`, `_country_add`, `_country_store` (`$P$`) |
| `common/scripted_effects/te_demog_effects.txt` | modify | `te_demog_seed`, `te_demog_step_begin` and `te_demog_country_census` call it; the header's variable list |
| `common/script_values/te_demog_values.txt` | modify | `te_demog_tfr` × `te_demog_pr_terms` |
| `common/static_modifiers/te_inheritance_modifiers.txt` | modify | Primogeniture's birth line on the absorbed family's type |
| `common/scripted_effects/te_inheritance_effects.txt` | modify | the rural refresh fires `te_demog_events.4` |
| `common/scripted_effects/te_debug_demog_effects.txt`, `common/script_values/te_debug_demog_values.txt` | modify | option l logs the shares, their targets and the absorbed births sum |
| `common/technology/technologies/te_demog_tech_injections.txt` | modify only if Task 6's fit moves them | vulcanization's and feminism's contraception |
| `localization/english/te_miscellaneous_l_english.yml`, `te_concepts_l_english.yml` | modify | the two tooltips' terms and text; `inh_primogeniture_rural_desc` |
| Tests | create: `test_demographics_regions.py`, `test_demographics_practices.py`; modify: `test_demographics_model.py`, `test_demographics_save_inputs.py`, `test_demographics_harness.py`, `test_gen_demographics.py`, `test_demographics_registry.py`, `test_release_census_inputs.py` | |
| Docs | modify | `docs/systems/mod_systems.md` § Demographics; the spec's §2.2 note and §5.2; `docs/guides/python_tools.md`; `docs/auto_generated_files.md`; `docs/guides/vanilla_patch_runbook.md`; `docs/player_guide/08-states.md`, `06-politics.md`; the PDF |
| `docs/testing/demographics-late-marriage-<date>.md` | create (Task 6), extend (Task 12) | the baseline, the replay, the fit, the regional table, the gate |

---

### Task 1: The strategic-region snapshot

**Files:**
- Create: `scripts/analysis/demographics_regions.py`
- Create: `scripts/analysis/demographics_strategic_regions.json` (written by Step 3's `--refresh`)
- Test: `test_demographics_regions.py` (create)

**Interfaces:**
- Produces: `R.parse(text) -> {region: [state regions]}`; `R.load_table(path=SNAPSHOT) -> {region: [states]}`;
  `R.strategic_region_of(path=SNAPSHOT) -> {state region: strategic region}`; `R.REPORT_REGIONS: tuple[(label,
  tuple[strategic region], history multiple 1836–1900 or None)]`; `R.report_row_of() -> {strategic region: label}`.

- [ ] **Step 1: Write the failing test**

```python
"""scripts/analysis/demographics_regions.py: the strategic-region snapshot the practices' start tables and the
regional report read (docs/superpowers/plans/2026-10-11-demographics-late-marriage.md, Task 1)."""

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

- [ ] **Step 2: Run it to see it fail**

Run: `$V -m unittest test_demographics_regions`
Expected: FAIL, `ModuleNotFoundError: No module named 'demographics_regions'`.

- [ ] **Step 3: Write the module**

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

# The regional growth report's rows (docs/testing/demographics-phase2-engine-rates-2026-10-10.md, "Where the growth
# comes from"), with history's rough multiple for 1836-1900 from that doc's table (Maddison, interpolated) where it
# gives one. China's is the no-collapse pace the owner set as fair (about x1.3-1.4; the real one was about x1.0).
REPORT_REGIONS = (
    ("China", ("region_north_china", "region_south_china"), 1.35),
    ("India", ("region_north_india", "region_south_india"), 1.3),
    ("Himalayas", ("region_himalayas",), None),
    ("Western, northern, central, southern Europe",
     ("region_western_europe", "region_northern_europe", "region_central_europe", "region_southern_europe"), 1.6),
    ("Eastern Europe, Balkans", ("region_eastern_europe", "region_balkans"), 1.7),
    ("Russia, Siberia", ("region_russia", "region_siberia"), 2.1),
    ("Japan, Korea, Manchuria", ("region_northeast_asia",), 1.4),
    ("Southeast Asia", ("region_indochina", "region_indonesia"), None),
    ("Middle East, Central Asia", ("region_near_east", "region_arabia", "region_greater_persia", "region_central_asia"),
     None),
    ("Africa", ("region_nile_basin", "region_north_africa", "region_west_africa", "region_equatorial_africa",
                "region_southern_africa", "region_east_africa"), 1.45),
    ("USA, Canada", ("region_canada", "region_pacific_coast", "region_great_plains", "region_atlantic_coast"), 4.8),
    ("Mexico, Central America", ("region_central_america",), 2.5),
    ("South America", ("region_brazil", "region_andes", "region_la_plata", "region_gran_colombia"), 2.5),
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

- [ ] **Step 4: Write the snapshot from the game** (the one command in this plan that needs the real game path)

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python scripts/analysis/demographics_regions.py --refresh`
Expected: `wrote …/demographics_strategic_regions.json: 36 regions, 675 state regions`.

- [ ] **Step 5: Run the tests**

Run: `$V -m unittest test_demographics_regions`
Expected: 4 tests, `OK`.

- [ ] **Step 6: File the capability issue** (CLAUDE.md, "File issues for mod-state-server capability gaps")

```bash
gh issue create --label enhancement --label tooling \
  --title "vanilla_parsed / mod_state_server: strategic regions (state region -> strategic region)" \
  --body "The demographics practices (docs/superpowers/plans/2026-10-11-demographics-late-marriage.md) key their start tables by strategic region, and the harness needs each save state's strategic region. vanilla_parsed/ has no strategic_regions entity and the server no endpoint, so the plan commits scripts/analysis/demographics_strategic_regions.json, built from game/common/strategic_regions/ plus the mod's REPLACEs. Proposed: add strategic_regions to mod_state.VANILLA_COMMON_DIRS and GET /strategic-regions/<name> -> {\"states\": [...]}, GET /state-region/<STATE_X> -> {\"strategic_region\": ...}. gen_formable_regions.py reads the same files from the game install today."
```

- [ ] **Step 7: Commit**

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
- Produces (params): `PRACTICES = ("lm", "bs")`, `PRACTICE_CUT`, `BS_HELD_START`, `PRACTICE_START_REGION`,
  `PRACTICE_START_STATE`, `PRACTICE_RATE`, `PRACTICE_EROSION_CONTRACEPTION`, `PRACTICE_EROSION_FROM`,
  `PRACTICE_EROSION_SPAN`, `PRACTICE_EROSION_ACCESS`, `PRACTICE_ACCESS_SPAN`, `LM_INHERITANCE`, `LM_WOMENS_WORK`,
  `IMPARTIBLE_LAWS`, `MARRIAGE_AGE_AT_ZERO`, `MARRIAGE_AGE_SPAN`.
- Produces (model): `Inputs.practices: dict` (`{"lm": share, "bs": share}`), `Inputs.agrarian_share: float`,
  `Inputs.impartible: bool`. `fertility()` gains the keys `"lm"` and `"bs"` (the terms). `practice_start(practice,
  state_region, strategic_region) -> float`; `contraception_beyond(inp) -> float`; `practice_erosion(practice, inp) ->
  float`; `practice_target(practice, inp, start) -> float`; `practice_drift(share, target) -> float`;
  `practice_seed(start, siblings) -> float` (siblings `[(people, share)]`); `marriage_age(share) -> float`.

Nothing changes in any figure yet: every `Inputs` has no practice until a caller sets one, and the raise waits for Task 6.

- [ ] **Step 1: Write the failing tests** (append to `test_demographics_model.py`)

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
                ("bs", "STATE_SEOUL", "region_northeast_asia", P.BS_HELD_START),
                ("bs", "STATE_JIANGSU", "region_north_china", P.BS_HELD_START),
                ("bs", "STATE_BOMBAY", "region_south_india", P.BS_HELD_START),
                ("bs", "STATE_HOME_COUNTIES", "region_western_europe", 0.0)):
            with self.subTest(practice=practice, state=state):
                self.assertEqual(M.practice_start(practice, state, region), want)

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

    def test_a_seed_takes_its_siblings_people_weighted_mean_else_its_start(self):
        self.assertAlmostEqual(M.practice_seed(0.0, [(300.0, 0.8), (100.0, 0.4)]), 0.7)
        self.assertEqual(M.practice_seed(0.4, []), 0.4)
        self.assertEqual(M.practice_seed(0.4, [(0.0, 0.9)]), 0.4, "siblings with no people don't count")

    def test_marriage_age(self):
        self.assertEqual(M.marriage_age(1.0), 26)
        self.assertEqual(M.marriage_age(0.0), 19)
```

- [ ] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_model.TestPractices`
Expected: FAIL, `AttributeError: module 'demographics_params' has no attribute 'PRACTICE_CUT'` (and `practices` an
unexpected keyword for `Inputs`).

- [ ] **Step 3: The parameters** (insert after `DEMOG_TYPES = …` and `MEANS_ACCESS_BASE = 0.3`, before "Cause multipliers
  from state inputs")

```python
# ---- Late Marriage and Birth Spacing ---------------------------------------------------------------------------
# docs/superpowers/specs/2026-10-10-demographics-late-marriage-design.md (approved by the owner 2026-10-11, all nine of
# its section 7 calls; Birth Spacing's cut at 0.35); plan docs/superpowers/plans/2026-10-11-demographics-late-marriage.md.
# Two customs, each a share of a state's people (0-1): children per woman x (1 - cut x share) for each, outside the
# means. Every value is a starting proposal the harness fits (plan Task 6), rounded to neat figures. The short names
# key the script (te_dg_pr_<P>, te_demog_pr_*_<P>); phase 3 adds Family Limitation to the same machinery.
PRACTICES = ("lm", "bs")
PRACTICE_CUT = {"lm": 0.30, "bs": 0.35}
# Birth Spacing's start for China, Manchuria, Korea and India: the share that cancels the wealth curve's raise,
# (1 - 1/s) / cut (spec 2.2, "held, not history"): 0.38 at s 1.15 and a cut of 0.34-0.35.
BS_HELD_START = 0.38
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
_MANCHURIA_KOREA = ("STATE_SOUTHERN_MANCHURIA", "STATE_NORTHERN_MANCHURIA", "STATE_SHENGJING", "STATE_SEOUL",
                    "STATE_BUSAN", "STATE_SARIWON", "STATE_PYONGYANG", "STATE_YANGHO")
# Start shares (spec 3.2, 3.3): by strategic region, then by state region, which wins. Geography, not culture. Malta and
# Corsica take Italy's (the vanilla file's Italy group); Cape Verde, an African archipelago, stays at 0 (plan D10).
PRACTICE_START_REGION = {
    "lm": {"region_western_europe": 1.0, "region_northern_europe": 1.0, "region_central_europe": 1.0},
    "bs": {r: BS_HELD_START for r in ("region_north_china", "region_south_china", "region_north_india",
                                      "region_south_india")},
}
PRACTICE_START_STATE = {
    "lm": {**dict.fromkeys(("STATE_KOLA", "STATE_EAST_KARELIA"), 0.2), **dict.fromkeys(_OCCITANIA, 1.0),
           **dict.fromkeys(_NW_IBERIA, 0.9), **dict.fromkeys(_IBERIA, 0.6), **dict.fromkeys(_ITALY, 0.5),
           **dict.fromkeys(_WEST_OF_THE_LINE, 0.8), **dict.fromkeys(_THE_GRADIENT, 0.4)},
    "bs": {**dict.fromkeys(_JAPAN, 1.0), **dict.fromkeys(_MANCHURIA_KOREA, BS_HELD_START)},
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

- [ ] **Step 4: The model** (`demographics_model.py`)

Add to `Inputs`, after `mods`:

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


def practice_seed(start, siblings=()):
    """A state with no share (§3.4; the plan's D5): the people-weighted mean of the other states in its state region
    that hold one, else its start. siblings: [(people, share)]."""
    held = [(p, s) for p, s in siblings if p > 0]
    people = sum(p for p, _s in held)
    return sum(p * s for p, s in held) / people if people > 0 else start


def marriage_age(share):
    """Women's mean age at first marriage the panel shows (§5.3): 19 with no Late Marriage, 26 at a full share."""
    return P.MARRIAGE_AGE_AT_ZERO + P.MARRIAGE_AGE_SPAN * share
```

- [ ] **Step 5: Run the model's tests and the suites that call `fertility`**

Run:
```bash
$V -m unittest test_demographics_model test_demographics_harness test_demographics_registry > /tmp/claude-1000/t2.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t2.txt
```
Expected: `OK`. No `Inputs` sets a practice yet, so every existing figure is unchanged.

- [ ] **Step 6: Commit**

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
  `H.inputs_for(c, carriers=None, incorporated=True, practices=None)`; `H.history_rows(sections, year, anchors,
  carriers=None, shares=None, incorporated_only=False)` where `shares` is `{sid: {practice: share}}`, and with no
  `shares` each state takes its start (the 1836 seed).

- [ ] **Step 1: Write the failing tests**

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
(docs/superpowers/plans/2026-10-11-demographics-late-marriage.md, Tasks 3-5)."""

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

- [ ] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_save_inputs test_demographics_practices test_demographics_harness`
Expected: FAIL (`agrarian_share`, `state_regions`, `demographics_practices`, `country_figures(shares=…)` missing).

- [ ] **Step 3: The save reader**

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

- [ ] **Step 4: `demographics_practices.py`, its first part**

```python
#!/usr/bin/env python3
"""Late Marriage and Birth Spacing in the harness (docs/superpowers/plans/2026-10-11-demographics-late-marriage.md).

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


def read_save(path):
    """(sections, {state id: {"vars": ...}}) of a plain-text save: the parse (265 MB a save in the normal-speed run),
    which the fit caches by path and re-uses at every grid point."""
    sections = S.read_sections(path)
    _countries, svars = S.read_variables(path, (), ("te_dg_fjob_share",))
    return sections, svars


def practice_states(path, carriers, regions=None, save=None):
    """[PracticeState] for every state of a plain-text save that has people (save: read_save's result, if cached).
    The women's job share is the walk's te_dg_fjob_share where the save holds it (a game with the census running),
    else 0; Undivided Farm Succession isn't read from saves, so only Primogeniture counts as impartible here (the
    script reads both)."""
    regions = R.strategic_region_of() if regions is None else regions
    sections, svars = read_save(path) if save is None else save
    state_region = S.state_regions(sections)
    out = []
    for tag, sts in S.state_inputs(sections).items():
        for sid, st, inc in sts:
            fjob = svars.get(sid, {}).get("vars", {}).get("te_dg_fjob_share", 0.0)
            inp = replace(H.inputs_for(st, carriers, incorporated=inc), agrarian_share=st.agrarian_share,
                          female_job_share=fjob, impartible=bool(set(P.IMPARTIBLE_LAWS) & st.laws))
            sr = state_region.get(sid, "")
            out.append(PracticeState(sid, tag, sr, regions.get(sr, ""), st.population, inc, inp))
    return out


def table_shares(states):
    """{sid: {practice: its start}}: what the census's 1836 seed gives every state."""
    return {s.sid: {p: M.practice_start(p, s.state_region, s.strategic_region) for p in P.PRACTICES} for s in states}


def read_shares(path):
    """{year: {sid: {practice: share}}} from practices-replay's --out file."""
    data = json.loads(open(path, encoding="utf-8").read())
    return {int(year): {sid: {p: rec[p] for p in P.PRACTICES} for sid, rec in by_sid.items()}
            for year, by_sid in data.items()}
```

- [ ] **Step 5: The harness takes shares** (`demographics_harness.py`)

`inputs_for` gains `practices=None` and passes `practices=dict(practices or {})` into `M.Inputs`.
`country_figures` becomes:

```python
def country_figures(states, carriers, shares=None, incorporated_only=False):
    """A country's model figures as the census builds them: each state's own rates (its SoL, literacy,
    urban share and incorporation), weighted by its people. The poverty term bends at SoL 9, so the
    rates at the country's mean SoL would hide what its poor and rich states do (#855's review). shares:
    {state id: {practice: share}} (the late-marriage plan); incorporated_only leaves a country's colonies out
    (spec 5.1 item 3)."""
    shares = shares or {}
    figs = [(st.population, model_figures(inputs_for(st, carriers, incorporated=inc, practices=shares.get(sid))))
            for sid, st, inc in states if st.population > 0 and (inc or not incorporated_only)]
    tot = sum(p for p, _ in figs) or 1
    return {k: sum(p * f[k] for p, f in figs) / tot for k in ("e0", "imr", "tfr", "r")}
```

Add `import demographics_regions as R  # noqa: E402` to the harness's imports (it imports nothing of the harness's).
`history_rows(sections, year, anchors, carriers=None, shares=None, incorporated_only=False)`: when `shares` is None,
every state takes its start, as the census's 1836 seed gives it:

```python
    if shares is None:
        regions, sr = R.strategic_region_of(), S.state_regions(sections)
        shares = {sid: {p: M.practice_start(p, sr.get(sid, ""), regions.get(sr.get(sid, ""), "")) for p in P.PRACTICES}
                  for sts in states.values() for sid, _st, _inc in sts}
```

Pass `shares` to every `country_figures` call, and `incorporated_only` to the countries' (the world line keeps every
state). In `cmd_history`, add three options to the `history` subparser:
- `--shares FILE`: practices-replay's output; the save's year selects its shares, and a year the file doesn't hold
  falls back to the table;
- `--incorporated-only`: print `(incorporated states only)` on the `==` line when it is set;
- `--no-practices`: pass `shares={}`, for today's model (Task 6's "before").

- [ ] **Step 6: Run the tests**

Run:
```bash
$V -m unittest test_demographics_save_inputs test_demographics_practices test_demographics_harness > /tmp/claude-1000/t3.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t3.txt
```
Expected: `OK`. `test_history_on_the_slice` still passes: the slice names no region, so every state takes 0.

- [ ] **Step 7: Commit**

```bash
git add scripts/analysis/demographics_save_inputs.py scripts/analysis/demographics_practices.py scripts/analysis/demographics_harness.py test_demographics_save_inputs.py test_demographics_practices.py test_demographics_harness.py
git commit -m "Demographics harness: each state's practices from a save; history takes shares and an incorporated filter"
```

---

### Task 4: The drift replay and the regional table

**Files:**
- Modify: `scripts/analysis/demographics_practices.py` (`replay`, `replay_gate`, `region_rows`)
- Modify: `scripts/analysis/demographics_harness.py` (subcommands `practices-replay`, `regions`)
- Test: `test_demographics_practices.py`

**Interfaces:**
- Consumes: Task 3's `practice_states`, `table_shares`.
- Produces:
  - `DP.replay(loaded) -> {year: {sid: record}}`, where `loaded` is `[(year, [PracticeState])]` sorted by year and
    `record` is `{"lm", "bs", "target_lm", "target_bs", "people", "state_region", "strategic_region"}`;
  - `DP.replay_gate(result, upto=1887) -> [str]`, the failures;
  - `DP.model_r(state, practices) -> float` (% a year);
  - `DP.region_rows(states, shares, observed=None) -> [(label, people, model r, observed r or None, history r or
    None)]`;
  - `DP.observed_growth(path) -> {sid: % a year}`.

- [ ] **Step 1: Write the failing tests** (append to `test_demographics_practices.py`)

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

    def test_years_between_saves_take_the_earlier_saves_conditions(self):
        a = [_state("1", "STATE_KANTO", "region_northeast_asia", mods={P.ACCESS_TYPE: 0.5})]
        got = DP.replay([(1837, a), (1847, a)])
        share = 1.0
        target = M.practice_target("bs", a[0].inp, 1.0)
        for _ in range(10):
            share = M.practice_drift(share, target)
        self.assertAlmostEqual(got[1847]["1"]["bs"], share, places=9)
        self.assertAlmostEqual(got[1847]["1"]["target_bs"], target, places=9)

    def test_the_gate(self):
        west = _state("1", "STATE_HOME_COUNTIES", "region_western_europe", people=5e6)
        japan = _state("2", "STATE_KANTO", "region_northeast_asia", people=5e6)
        ok = DP.replay([(1837, [west, japan]), (1887, [west, japan])])
        self.assertEqual(DP.replay_gate(ok), [])
        # the eroding conditions from the first save, so the 49 years between take them too
        eroded = replace(japan, inp=replace(japan.inp, mods={P.ACCESS_TYPE: 0.5, P.CONTRACEPTION_TYPE: 1.0},
                                            literacy=1.0))
        bad = DP.replay([(1837, [west, eroded]), (1887, [west, eroded])])
        self.assertTrue(any("East Asia" in line for line in DP.replay_gate(bad)))


class TestRegions(unittest.TestCase):
    def test_rows_weight_states_by_people_and_name_history(self):
        states = [_state("1", "STATE_HOME_COUNTIES", "region_western_europe", people=3e6, sol=8.0),
                  _state("2", "STATE_LAZIO", "region_southern_europe", people=1e6, sol=8.0)]
        rows = {r[0]: r for r in DP.region_rows(states, DP.table_shares(states))}
        label = "Western, northern, central, southern Europe"
        _label, people, model_r, observed_r, history_r = rows[label]
        self.assertEqual(people, 4e6)
        each = (DP.model_r(states[0], {"lm": 1.0, "bs": 0.0}), DP.model_r(states[1], {"lm": 0.5, "bs": 0.0}))
        self.assertAlmostEqual(model_r, (3 * each[0] + each[1]) / 4, places=9)
        self.assertIsNone(observed_r)
        self.assertAlmostEqual(history_r, 100 * math.log(1.6) / 64, places=9)
```

Add `import math` and `from dataclasses import replace` to the test file's imports.

- [ ] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_practices`
Expected: FAIL (`DP.replay`, `DP.replay_gate`, `DP.region_rows`, `DP.model_r` missing).

- [ ] **Step 3: Write the replay and the table** (append to `demographics_practices.py`; add `import math`)

```python
# ---- the drift replay (spec 5.1 item 5) ---------------------------------------------------------------------

def _seed(shares, states):
    """te_demog_practice_seed: a state with no share takes its siblings' people-weighted mean (the states in its state
    region that hold one), else its start. Siblings share a start, so the order doesn't matter (the plan's D5)."""
    by_region = {}
    for s in states:
        by_region.setdefault(s.state_region, []).append(s)
    for s in states:
        if s.sid in shares:
            continue
        sibs = [x for x in by_region[s.state_region] if x.sid in shares]
        shares[s.sid] = {p: M.practice_seed(M.practice_start(p, s.state_region, s.strategic_region),
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
EAST_ASIA_BS = (("Japan", lambda r: r["state_region"] in P.PRACTICE_START_STATE["bs"]
                 and P.PRACTICE_START_STATE["bs"][r["state_region"]] == 1.0),
                ("China, Manchuria, Korea", lambda r: M.practice_start("bs", r["state_region"], r["strategic_region"])
                 == P.BS_HELD_START and r["strategic_region"] in ("region_north_china", "region_south_china",
                                                                  "region_northeast_asia")))


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


# ---- the regional table (#894: births less deaths outside Europe) -----------------------------------------

def model_r(state, practices):
    """The model's steady growth for one state with these shares, % a year (H.model_figures' r)."""
    return H.model_figures(replace(state.inp, practices=dict(practices)))["r"]


def region_rows(states, shares, observed=None):
    """[(label, people, model r, observed r, history r)] by R.REPORT_REGIONS: the model's steady growth (births less
    deaths at the state's own rates, % a year, people-weighted), the run's own births less deaths where `observed`
    ({sid: % a year}, from the census's te_dg_births/_deaths/_people) has the state, and history's pace 1836-1900
    from the row's multiple."""
    row_of = R.report_row_of()
    sums = {}
    for s in states:
        label = row_of.get(s.strategic_region)
        if label is None or s.people <= 0:
            continue
        acc = sums.setdefault(label, [0.0, 0.0, 0.0, 0.0])
        acc[0] += s.people
        acc[1] += s.people * model_r(s, shares.get(s.sid, {}))
        if observed and s.sid in observed:
            acc[2] += s.people
            acc[3] += s.people * observed[s.sid]
    out = []
    for label, _regions, hist in R.REPORT_REGIONS:
        if label not in sums:
            continue
        people, mr, op, orr = sums[label]
        out.append((label, people, mr / people, orr / op if op else None,
                    100 * math.log(hist) / 64 if hist else None))
    return out


def observed_growth(path):
    """{sid: births less deaths, % a year} from the census's last step in a save (te_dg_births, _deaths, _people;
    a game with the census running). A state with none is left out."""
    _c, svars = S.read_variables(path, (), ("te_dg_births", "te_dg_deaths", "te_dg_people"))
    out = {}
    for sid, rec in svars.items():
        v = rec["vars"]
        if v.get("te_dg_people", 0) > 0 and "te_dg_births" in v and "te_dg_deaths" in v:
            out[sid] = 100 * (v["te_dg_births"] - v["te_dg_deaths"]) / v["te_dg_people"]
    return out
```

`model_r` uses `H.model_figures`, whose `r` is ln(daughters per woman) ÷ 29: the steady growth of the state's own rates,
what the census aims the engine at.

- [ ] **Step 4: The subcommands** (`demographics_harness.py`; each imports `demographics_practices as DP` inside the
  function)

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


def cmd_regions(args):
    import demographics_practices as DP
    carriers = DM.load_carriers()
    shares_by_year = DP.read_shares(args.shares) if args.shares else {}
    for path in args.save:
        year = save_year(path) or args.year
        states = DP.practice_states(path, carriers)
        shares = {} if args.no_practices else shares_by_year.get(year) or DP.table_shares(states)
        observed = DP.observed_growth(path)
        print(f"== {Path(path).name} ({year}){' with no practices' if args.no_practices else ''}: "
              "model growth (steady, % a year), the run's births less deaths, history's pace 1836-1900")
        for label, people, mr, orr, hr in DP.region_rows(states, shares, observed):
            o = f"{orr:+.2f}" if orr is not None else "  -  "
            h = f"{hr:+.2f}" if hr is not None else "  -  "
            print(f"{label:45s} {people / 1e6:7.1f}M  model {mr:+.2f}  run {o}  history {h}")
    return 0
```

Parsers: `practices-replay SAVE... [--out FILE] [--year Y]`; `regions SAVE... [--shares FILE] [--no-practices]
[--year Y]`. `--no-practices` gives today's model, for Task 6's "before" column.

- [ ] **Step 5: Run the tests**

Run: `$V -m unittest test_demographics_practices test_demographics_harness`
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add scripts/analysis/demographics_practices.py scripts/analysis/demographics_harness.py test_demographics_practices.py
git commit -m "Demographics harness: the practices' drift replay and the regional growth table"
```

---

### Task 5: The joint fit

**Files:**
- Modify: `scripts/analysis/demographics_practices.py` (`FitState`, `fit_states`, `evaluate`, `fit_table`,
  `patch_params`, `mortality_report`)
- Modify: `scripts/analysis/demographics_harness.py` (subcommand `practices-fit`)
- Test: `test_demographics_practices.py`

**Interfaces:**
- Consumes: Task 3's `practice_states`; Task 4's `read_shares` output shape; `H.HISTORY_TAGS`, `H.read_anchors`,
  `H.nearest`, `H.growth_around`.
- Produces:
  - `DP.FitState(country, tag, people, incorporated, base_tfr, nrr_per_tfr, e0, lm, bs, held)`;
  - `DP.fit_states(path, carriers, shares, save=None) -> [FitState]` (`save`: `DP.read_save`'s cached result);
  - `DP.evaluate(fit_by_year, anchors, s, cut_lm, cut_bs, held=None) -> dict` with keys `error`, `world_tfr`,
    `world_r`, `countries`, `high`, `held`;
  - `DP.fit_table(fit_by_year, anchors, s_grid, lm_grid, bs_grid) -> [(s, cut_lm, cut_bs, result)]`;
  - `DP.patch_params(infection_scale=1.0, **values)` (a context manager);
  - `DP.mortality_report(fit_by_year, anchors, s, cut_lm, cut_bs, held=None) -> dict` with keys `e0`, `shrinking`,
    `growth`, `world_r`, `china_r`, `error` (spec §5.2's mortality items at one point).

**The method** (spec §2.3, kept):
- For each s, the cuts minimise the root-mean-square error of children per woman over the anchor countries.
- A country's figure is its incorporated states', weighted by people.
- The anchor is Gapminder's within 5 years of the save.
- Gapminder's flat guesses (China, Iran, Turkey, Mexico, Peru, Korea) carry half weight (spec §5.2).
- The USA and Chile in 1887 are dropped as fertility transitions (spec §2.3). The Netherlands is no longer dropped:
  the incorporated filter now leaves out the colonies that put it there.
- Every state whose Birth Spacing start is `BS_HELD_START` takes the held share h = (1 − 1/s) ÷ cut_bs, scaled by its
  replayed share ÷ its start. That holds China and India (spec §2.2), with Manchuria and Korea at the same value as
  geography (§3.3).
- Each grid point is cheap: a state's children per woman is s × base × (1 − cut_lm × lm) × (1 − cut_bs × bs), and its
  growth is ln(nrr_per_tfr × that) ÷ 29. Only the mortality knobs need the model re-run.

- [ ] **Step 1: Write the failing tests** (append to `test_demographics_practices.py`)

```python
def _fit(country, base, lm=0.0, bs=0.0, held=False, people=1e7, e0=35.0, tag="TST"):
    return DP.FitState(country, tag, people, True, base, 0.4, e0, lm, bs, held)


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
        china = _fit("China", 6.0, bs=P.BS_HELD_START, held=True)
        got = DP.evaluate({1837: [china]}, self.ANCHORS, s=1.2, cut_lm=0.3, cut_bs=0.4)
        self.assertAlmostEqual(got["held"], (1 - 1 / 1.2) / 0.4, places=9)
        self.assertAlmostEqual(got["countries"][("China", 1837)][0], 6.0, places=9)

    def test_the_table_finds_each_raises_best_cuts(self):
        states = {1837: [_fit("Sweden", 5.5, lm=1.0), _fit("Iran", 6.0)]}
        rows = DP.fit_table(states, self.ANCHORS, [1.15], [0.2, 0.3, 0.4], [0.35])
        self.assertEqual(len(rows), 1)
        s, cut_lm, _cut_bs, _res = rows[0]
        # Sweden's 4.4 at 5.5 x 1.15 wants 1 - cut = 0.696: 0.3 is the grid's nearest
        self.assertEqual((s, cut_lm), (1.15, 0.3))

    def test_patch_params_restores(self):
        before = (P.POVERTY_INFECTION_AT_FLOOR, P.INFECTION["f"][0])
        with DP.patch_params(infection_scale=1.2, POVERTY_INFECTION_AT_FLOOR=2.0):
            self.assertEqual(P.POVERTY_INFECTION_AT_FLOOR, 2.0)
            self.assertAlmostEqual(P.INFECTION["f"][0], before[1] * 1.2)
        self.assertEqual((P.POVERTY_INFECTION_AT_FLOOR, P.INFECTION["f"][0]), before)
```

- [ ] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_practices.TestFit`
Expected: FAIL (`DP.FitState` missing).

- [ ] **Step 3: Write the fit** (append to `demographics_practices.py`; add `import contextlib`)

```python
# ---- the fit (spec 2.3, 5.1 item 6) -----------------------------------------------------------------------------
FLAT_GUESSES = frozenset({"China", "Iran", "Turkey", "Mexico", "Peru", "Korea"})   # half weight (spec 5.2)
DROPPED = frozenset({("United States", 1887), ("Chile", 1887)})   # fertility transitions (spec 2.3)
HIGH_GROUP = ("Iran", "Turkey", "Russia", "Mexico", "Argentina")  # history's early-marrying, about 7 (spec 1.2)


@dataclass
class FitState:
    country: str           # its HISTORY_TAGS name when its owner is the tag history uses, else ""
    tag: str
    people: float
    incorporated: bool
    base_tfr: float        # the model's children per woman with no practice, on the curve as it stands
    nrr_per_tfr: float     # daughters per woman per child per woman: survival to each childbearing age
    e0: float
    lm: float
    bs: float
    held: bool             # its Birth Spacing start is BS_HELD_START (China, Manchuria, Korea, India)


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
        held = M.practice_start("bs", s.state_region, s.strategic_region) == P.BS_HELD_START
        out.append(FitState(chosen.get(s.tag, ""), s.tag, s.people, s.incorporated, base, M.nrr(1.0, qf), e0,
                            sh.get("lm", 0.0), sh.get("bs", 0.0), held))
    return out


def evaluate(fit_by_year, anchors, s, cut_lm, cut_bs, held=None):
    """One grid point over {year: [FitState]}: the error over the anchor countries, the world's children per woman
    and growth (states of tags with 1M people or more), each anchor country's (model, history), and the high group's
    1837-or-first-year range. held: the held Birth Spacing share; default (1 - 1/s) / cut_bs (spec 2.2)."""
    h = (1 - 1 / s) / cut_bs if held is None else held
    countries, sq, weights = {}, 0.0, 0.0
    world_tfr, world_r = {}, {}
    for year, states in sorted(fit_by_year.items()):
        tag_people = {}
        for st in states:
            tag_people[st.tag] = tag_people.get(st.tag, 0.0) + st.people
        acc, wp, wt, wr = {}, 0.0, 0.0, 0.0
        for st in states:
            bs = st.bs * h / P.BS_HELD_START if st.held else st.bs
            tfr = s * st.base_tfr * (1 - cut_lm * st.lm) * (1 - cut_bs * bs)
            r = 100 * math.log(max(st.nrr_per_tfr * tfr, 1e-9)) / 29
            if tag_people[st.tag] >= 1e6:
                wp, wt, wr = wp + st.people, wt + st.people * tfr, wr + st.people * r
            if st.country and st.incorporated:
                a = acc.setdefault(st.country, [0.0, 0.0])
                a[0], a[1] = a[0] + st.people, a[1] + st.people * tfr
        world_tfr[year], world_r[year] = (wt / wp, wr / wp) if wp else (None, None)
        for country, (p, t) in acc.items():
            hist = H.nearest(anchors.get("tfr", {}).get(country, {}), year, 5)
            countries[(country, year)] = (t / p, hist[1] if hist else None)
            if hist and (country, year) not in DROPPED:
                w = 0.5 if country in FLAT_GUESSES else 1.0
                sq, weights = sq + w * (t / p - hist[1]) ** 2, weights + w
    first = min(fit_by_year)
    high = [countries[(c, first)][0] for c in HIGH_GROUP if (c, first) in countries]
    return {"error": (sq / weights) ** 0.5 if weights else None, "world_tfr": world_tfr, "world_r": world_r,
            "countries": countries, "high": (min(high), max(high)) if high else None, "held": h}


def fit_table(fit_by_year, anchors, s_grid, lm_grid, bs_grid):
    """[(s, cut_lm, cut_bs, result)]: for each raise, the cuts with the least error (spec 2.3's method)."""
    rows = []
    for s in s_grid:
        best = None
        for cut_lm in lm_grid:
            for cut_bs in bs_grid:
                res = evaluate(fit_by_year, anchors, s, cut_lm, cut_bs)
                if res["error"] is not None and (best is None or res["error"] < best[3]["error"]):
                    best = (s, cut_lm, cut_bs, res)
        if best:
            rows.append(best)
    return rows


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


MORTALITY_E0 = (("United Kingdom", 41.0), ("Sweden", 41.0), ("Denmark", 41.0))   # spec 5.2: within 3 years, 1837


def mortality_report(fit_by_year, anchors, s, cut_lm, cut_bs, held=None):
    """Spec 5.2's mortality items at one point: the three Western countries' life expectancy against 41 (the first
    year), anchor countries of 20M or more that shrink, Iran's and Mexico's growth against history's, world growth
    and China's in the last year."""
    res = evaluate(fit_by_year, anchors, s, cut_lm, cut_bs, held)
    first, last = min(fit_by_year), max(fit_by_year)
    by = {}
    for year, states in fit_by_year.items():
        h = res["held"]
        for st in states:
            if not (st.country and st.incorporated):
                continue
            bs = st.bs * h / P.BS_HELD_START if st.held else st.bs
            tfr = s * st.base_tfr * (1 - cut_lm * st.lm) * (1 - cut_bs * bs)
            a = by.setdefault((st.country, year), [0.0, 0.0, 0.0])
            a[0] += st.people
            a[1] += st.people * st.e0
            a[2] += st.people * 100 * math.log(max(st.nrr_per_tfr * tfr, 1e-9)) / 29
    fig = {k: (p, e / p, r / p) for k, (p, e, r) in by.items() if p}
    e0 = {c: fig[(c, first)][1] for c, _want in MORTALITY_E0 if (c, first) in fig}
    shrinking = sorted(f"{c} {y}" for (c, y), (p, _e, r) in fig.items() if p >= 2e7 and r < 0)
    growth = {}
    for c in ("Iran", "Mexico"):
        for y in (first, last):
            if (c, y) in fig:
                growth[(c, y)] = (fig[(c, y)][2], H.growth_around(anchors.get("population", {}).get(c, {}), y))
    china = fig.get(("China", last), (0, 0, None))[2]
    return {"e0": e0, "shrinking": shrinking, "growth": growth, "world_r": res["world_r"], "china_r": china,
            "error": res["error"]}
```

- [ ] **Step 4: The subcommand** (`demographics_harness.py`)

`practices-fit SAVE... --anchors CSV [--shares FILE] [--s 1.10,1.15,1.20] [--lm 0.20,0.25,0.30,0.35,0.40]
[--bs 0.25,0.30,0.35,0.40,0.45] [--at S,LM,BS] [--mortality] [--means]`. What it does:

1. Load the anchors (exit 1 with the same message as `history` if the file can't be read), the carriers, and each
   save's `fit_states` with its year's shares from `--shares`, or the table's.
2. Print the spec's §2.3 table, one row per s: the cuts, the error, the world's children per woman per save year, the
   world's growth per save year, the held share, and the high group's range in the first year.
3. With `--at S,LM,BS`, print the country-by-country table at that point: model against history per save year,
   flat-guess countries marked `(half)`, dropped ones `(dropped)`, and every country more than 0.5 off flagged `OFF`.
4. With `--mortality`, re-run `fit_states` for every point of this grid inside `DP.patch_params`, and print
   `DP.mortality_report` at `--at` for each:
   - `POVERTY_INFECTION_AT_FLOOR` in 1.5, 1.75, 2.0;
   - `POVERTY_INFECTION_SOL` in 8, 9, 10;
   - `infection_scale` in 0.9, 1.0, 1.1, 1.2.
5. With `--means`, re-run `fit_states` with the carriers' `state_contraception_add` lines for `vulcanization` and
   `feminism` replaced by each pair in {0.10, 0.15, 0.20, 0.25, 0.30}². Use
   `dataclasses.replace(c, value=v) if c.key == tech and c.type == P.CONTRACEPTION_TYPE else c`. Print, per pair:
   - Britain's children per woman in the last save against its anchor;
   - each `fertility` scenario's figure and band (`H.fertility_rows(carriers=patched)`).

   The replayed shares stay fixed while the pair varies. The pair also feeds Late Marriage's erosion, but by 1887 that
   is negligible, and Task 6 Step 8 replays again at the applied values.

Exit 0 unless the anchors can't be read.

```python
def cmd_practices_fit(args):
    import demographics_practices as DP
    try:
        anchors = read_anchors(args.anchors)
    except OSError as e:
        print(f"cannot read the anchors {args.anchors}: {e}", file=sys.stderr)
        return 1
    carriers = DM.load_carriers()
    shares_by_year = DP.read_shares(args.shares) if args.shares else {}
    saves = {path: DP.read_save(path) for path in args.save}   # parse each save once

    def load(carriers):
        out = {}
        for path in args.save:
            year = save_year(path) or args.year
            shares = shares_by_year.get(year)
            if shares is None:
                shares = DP.table_shares(DP.practice_states(path, carriers, save=saves[path]))
            out[year] = DP.fit_states(path, carriers, shares, save=saves[path])
        return out

    grid = [float(x) for x in args.s.split(",")], [float(x) for x in args.lm.split(",")], \
        [float(x) for x in args.bs.split(",")]
    fit_by_year = load(carriers)
    print("s     cut_lm cut_bs error  world tfr        world growth      held  high group (first year)")
    for s, cl, cb, res in DP.fit_table(fit_by_year, anchors, *grid):
        tfr = " / ".join(f"{v:.2f}" for _y, v in sorted(res["world_tfr"].items()))
        r = " / ".join(f"{v:+.2f}" for _y, v in sorted(res["world_r"].items()))
        hi = f"{res['high'][0]:.2f}-{res['high'][1]:.2f}" if res["high"] else "-"
        print(f"{s:.2f}  {cl:.2f}   {cb:.2f}   {res['error']:.3f}  {tfr:16s} {r:17s} {res['held']:.2f}  {hi}")
    if args.at:
        s, cl, cb = (float(x) for x in args.at.split(","))
        res = DP.evaluate(fit_by_year, anchors, s, cl, cb)
        for (country, year), (model, hist) in sorted(res["countries"].items()):
            tag = " (half)" if country in DP.FLAT_GUESSES else ""
            tag += " (dropped)" if (country, year) in DP.DROPPED else ""
            off = " OFF" if hist is not None and abs(model - hist) > 0.5 else ""
            h = f"{hist:.2f}" if hist is not None else "-"
            print(f"{country:15s} {year}  model {model:.2f}  history {h}{tag}{off}")
        if args.mortality:
            for floor in (1.5, 1.75, 2.0):
                for sol in (8, 9, 10):
                    for scale in (0.9, 1.0, 1.1, 1.2):
                        with DP.patch_params(infection_scale=scale, POVERTY_INFECTION_AT_FLOOR=floor,
                                             POVERTY_INFECTION_SOL=sol):
                            rep = DP.mortality_report(load(carriers), anchors, s, cl, cb)
                        print(f"floor {floor:.2f} sol {sol} infection x{scale:.2f}: {rep}")
        if args.means:
            for vulc in (0.10, 0.15, 0.20, 0.25, 0.30):
                for fem in (0.10, 0.15, 0.20, 0.25, 0.30):
                    patched = [dataclasses.replace(c, value=vulc) if c.key == "vulcanization"
                               and c.type == P.CONTRACEPTION_TYPE else
                               dataclasses.replace(c, value=fem) if c.key == "feminism"
                               and c.type == P.CONTRACEPTION_TYPE else c for c in carriers]
                    res = DP.evaluate(load(patched), anchors, s, cl, cb)
                    gb = {y: m for (c, y), (m, _h) in res["countries"].items() if c == "United Kingdom"}
                    rows = fertility_rows(carriers=patched)
                    out = sum(1 for _l, t, lo, hi in rows if not lo <= t <= hi)
                    print(f"vulcanization {vulc:.2f} feminism {fem:.2f}: Britain {gb}  scenarios out of band {out}")
    return 0
```

The harness already imports `dataclasses` and `json`. The mortality grid has 36 points; each re-runs the model over
every state of two saves (about 2,700 states each), from the parse `saves` holds, so the grid takes minutes, not hours.
Add the parser: `practices-fit SAVE... --anchors CSV [--shares FILE] [--s …] [--lm …] [--bs …] [--at S,LM,BS]
[--mortality] [--means] [--year Y]`, with the defaults above.

- [ ] **Step 5: Run the tests**

Run: `$V -m unittest test_demographics_practices test_demographics_harness`
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add scripts/analysis/demographics_practices.py scripts/analysis/demographics_harness.py test_demographics_practices.py
git commit -m "Demographics harness: practices-fit, the raise, the cuts, the held share, the means pair and step 1's mortality"
```

---

### Task 6: Run the fit, round, apply — then Stop A

The harness fit comes first (spec §5.1). This task runs it on the normal-speed run's saves, applies the rounded
values, and stops for the owner before any script.

**Files:**
- Create: `docs/testing/demographics-late-marriage-<date>.md`
- Modify: `scripts/analysis/demographics_params.py` (the fitted values: `WEALTH_TFR_LOW`, `WEALTH_TFR_HIGH`,
  `PRACTICE_CUT`, `BS_HELD_START`; and only if the mortality fit moves them, `POVERTY_INFECTION_AT_FLOOR`,
  `POVERTY_INFECTION_SOL` and the `INFECTION` breakpoints)
- Modify, only if the means fit moves them: `common/technology/technologies/te_demog_tech_injections.txt`
- Modify: `scripts/analysis/demographics_harness.py` (`FERTILITY_SCENARIOS` take their shares)
- Modify: `test_demographics_model.py` (`TestFertility.test_sketch_cases`, `test_wealth_term_endpoints`),
  `test_demographics_save_inputs.py` (`test_wealth_tfr_is_the_pop_weighted_curve`'s 4.889),
  `test_demographics_harness.py` (as the suite shows)
- Regenerate: `te_demog_generated_values.txt` (the wealth curve)

- [ ] **Step 1: Check the build question and pick the saves**

```bash
git diff --quiet ec304526 origin/main -- scripts/analysis/demographics_save_inputs.py && echo "main's reader is ec304526's"
git diff origin/main -- scripts/analysis/demographics_save_inputs.py | grep '^-[^-]' || echo "this branch only adds to it"
D=/mnt/d/vic3te-data/vic3te-demog-p2-normal-2026-10-11/saves
for f in $D/*.v3; do printf '%s %s\n' "$($V -c "import sys; sys.path.insert(0,'scripts/analysis'); import demographics_harness as H; print(H.save_year(sys.argv[1]))" "$f")" "$f"; done | sort -n > /tmp/claude-1000/lm-saves.txt
awk '$1==1837||$1==1847||$1==1857||$1==1867||$1==1877||$1==1887||$1==1897||$1==1901' /tmp/claude-1000/lm-saves.txt
```

Expected: both lines print (Task 3's changes to the reader only add lines), then one save for each of the eight years.
Keep the eight paths as `S1837 … S1901`. `predict` does not run from this branch on these saves (D8).

- [ ] **Step 2: Today, before anything changes** (no practices, the 6.0 curve)

```bash
A=/mnt/d/vic3te-data/history-anchors-2026-10-10/anchors.csv
$V scripts/analysis/demographics_harness.py history $S1837 $S1887 --anchors $A --incorporated-only --no-practices > /tmp/claude-1000/lm-today-history.txt
$V scripts/analysis/demographics_harness.py regions $S1837 $S1887 $S1901 --no-practices > /tmp/claude-1000/lm-today-regions.txt
$V scripts/analysis/demographics_harness.py medicine; $V scripts/analysis/demographics_harness.py fertility
```

Record in the results doc: the world's children per woman and growth for 1837 and 1887, each anchor country, and the
regional table. These are the gate's "today" (spec §5.2's 5.96 / 5.74 and +1.08 / +0.98 were 6.2-era figures, D1).

- [ ] **Step 3: The drift replay at the starting values**

```bash
$V scripts/analysis/demographics_harness.py practices-replay $S1837 $S1847 $S1857 $S1867 $S1877 $S1887 $S1897 $S1901 --out /tmp/claude-1000/lm-replay.json
```

Expected: no `GATE` line up to 1887. If one prints, it names the region and figure; read the largest moves list and the
targets. A Western state far below 0.8 by 1887 means era-3 contraception reached it early. That is a finding for the
results doc and Stop A, not a retune here.

- [ ] **Step 4: The fertility fit**

```bash
$V scripts/analysis/demographics_harness.py practices-fit $S1837 $S1887 --anchors $A --shares /tmp/claude-1000/lm-replay.json \
  --s 1.10,1.15,1.17,1.20 --lm 0.20,0.25,0.30,0.35,0.40 --bs 0.25,0.30,0.35,0.40,0.45
```

Choose the neat point:
- s from {1.15, 1.20};
- the cuts on the 0.05 grid;
- the least error with the high group's range reaching 6.7 or more;
- ties go to the approved proposal (1.15, 0.30, 0.35).

Then print it country by country with `--at S,LM,BS` and copy the table into the results doc.

- [ ] **Step 5: The means pair and the mortality refit** (call 8)

```bash
$V scripts/analysis/demographics_harness.py practices-fit $S1837 $S1887 --anchors $A --shares /tmp/claude-1000/lm-replay.json --at S,LM,BS --means
$V scripts/analysis/demographics_harness.py practices-fit $S1837 $S1887 --anchors $A --shares /tmp/claude-1000/lm-replay.json --at S,LM,BS --mortality
```

- **The means pair:** keep vulcanization 0.20 and feminism 0.15 unless another neat pair puts every scenario in band
  with a smaller error on Britain 1887.
- **The mortality point:** the neat one that passes the most of spec §5.2's mortality items:
  - Britain, Sweden and Denmark within 3 years of 41 in 1837;
  - no anchor country of 20M or more shrinking;
  - Iran's and Mexico's growth within 0.5% a year of history's;
  - world growth no more than 0.1% a year above today's (Step 2);
  - China's growth in 1887 within 0.1% of today's.
- Ties go to today's values (POVERTY_INFECTION_AT_FLOOR 1.75, POVERTY_INFECTION_SOL 9, infection ×1).
- If the mortality point moves, re-run Step 4 at it: the survival term moves children per woman. Keep the second
  answer if it differs.

- [ ] **Step 6: Apply the rounded values**

In `demographics_params.py`:
- `WEALTH_TFR_LOW` and `WEALTH_TFR_HIGH` become 6.0 × s and 3.5 × s, rounded to 0.1. Keep the comment's history line and
  add: "× s (the late-marriage plan's fit, <date>; spec 2.2), with the practices holding the West and East Asia back".
- `PRACTICE_CUT`.
- `BS_HELD_START` = round((1 − 1/s) ÷ cut_bs, 2).
- If the mortality point moved: `POVERTY_INFECTION_AT_FLOOR`, `POVERTY_INFECTION_SOL`, and each `INFECTION`
  breakpoint × the scale, rounded to the nearest 10.

If the means pair moved, change `te_demog_tech_injections.txt`'s two lines.

The scenarios take their shares (spec §5.1 item 4). In `FERTILITY_SCENARIOS`, add `practices={…}` to each scenario's
dict:

| Scenario | `practices` | Band |
|---|---|---|
| 1836 agrarian (reference), and its No Women's Rights twin | `{"lm": 0.5}` | 4.8–6.2 |
| Britain 1836 | `{"lm": 1.0}` | **4.3–5.5** (re-centred on history's 4.8–5.0, spec §5.1) |
| France 1836 (Family Limitation) | `{"lm": 1.0}` | 3.4–5.0 |
| Britain 1900, and its Women Own Property twin | `{"lm": 0.75}` | as now |
| West 1950, and its Women's Suffrage twin | `{"lm": 0.5}` | as now |
| West 1990, and its Women's Suffrage twin | `{"lm": 0.45}` | as now |
| India 1975 | `{"bs": 0.2}` (the drift's equilibrium from 0.38 at its contraception and health access) | 4.7–5.8 |

`scenario_inputs` passes `practices` through to `M.Inputs` (it takes `**kw`, so it does already).

Regenerate:

```bash
$V scripts/generators/gen_demographics.py
```

- [ ] **Step 7: Update the tests that pin today's figures, and run the suite**

- `test_wealth_term_endpoints`: the new `WEALTH_TFR_LOW` and `WEALTH_TFR_HIGH`.
- `test_sketch_cases`: give each scenario the same shares as the table above. Set each expected value to the model's
  figure rounded to 0.05, printed by:
  `$V -c "import sys; sys.path.insert(0,'scripts/analysis'); sys.path.insert(0,'.'); import test_demographics_model as T, demographics_model as M; [print(n, round(M.run_constant(i, years=200)[1]['tfr'], 2)) for n, i in (('GB1836', T.BRITAIN_1836), ('FR1836', T.FRANCE_1836), ('GB1900', T.BRITAIN_1900), ('W1950', T.WEST_1950), ('W1990', T.WEST_1990), ('IN1975', T.INDIA_1975))]"`.
  Keep `delta=0.3`. Each must lie inside its band in the table above, or stop: a scenario out of band is a fit failure,
  not a test to loosen.
- `test_wealth_tfr_is_the_pop_weighted_curve`: its 4.889 scales by s; recompute it the same way the test's comment
  does.

```bash
$V -m unittest discover -s . -p 'test_*.py' > /tmp/claude-1000/t6.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t6.txt
$V scripts/analysis/demographics_harness.py fertility; $V scripts/analysis/demographics_harness.py medicine
```

Expected: `OK`; neither command prints `OUT`.

- [ ] **Step 8: After, on the same saves**

```bash
$V scripts/analysis/demographics_harness.py practices-replay $S1837 $S1847 $S1857 $S1867 $S1877 $S1887 $S1897 $S1901 --out /tmp/claude-1000/lm-replay-fitted.json
$V scripts/analysis/demographics_harness.py history $S1837 $S1887 --anchors $A --incorporated-only --shares /tmp/claude-1000/lm-replay-fitted.json
$V scripts/analysis/demographics_harness.py regions $S1837 $S1887 $S1901 --shares /tmp/claude-1000/lm-replay-fitted.json
```

- [ ] **Step 9: Write the results doc** (`docs/testing/demographics-late-marriage-<date>.md`)

Its sections:
- **The build and the data:** this branch's commit; the saves (D8: the reader is unchanged since ec304526); the anchors'
  path.
- **Today:** Step 2's table: world, anchor countries, regions.
- **The replay:** Step 3's and Step 8's per-year lines, the largest moves, and the gate lines.
- **The fit:** Step 4's table as spec §2.3's; the chosen point and why; the country-by-country table, with every
  country more than 0.5 off named, each with its reason (spec §2.3's "What is left, and why" as the model).
- **Mortality and the means pair:** Step 5's chosen points, and the §5.2 mortality items at them.
- **The regional table** for 1837, 1887 and 1901, before and after: the model's steady growth, the run's own births
  less deaths, and history's pace. This answers #894's "Births less deaths outside Europe" for the census's
  side:
  - China, India, Korea and Manchuria hold by construction;
  - Japan and the West fall;
  - the Middle East, Russia, Africa and the Americas rise with the raise unless the mortality refit lowers them.
  Write which happened, region by region, with the numbers.
- **China at history's 5.5:** the BS share it would need at the fitted point ((1 − 5.5 ÷ today's China ÷ s) ÷ cut_bs),
  and China's growth in 1887 at that share (spec §2.2's second variant), so the owner can weigh it.
- **The gate**, item by item: spec §5.2 as restated in Global Constraints and Owner question 1, each pass or fail with
  its figure.

- [ ] **Step 10: Commit**

```bash
git add scripts/analysis/demographics_params.py scripts/analysis/demographics_harness.py common/script_values/te_demog_generated_values.txt docs/testing/demographics-late-marriage-<date>.md test_demographics_model.py test_demographics_save_inputs.py test_demographics_harness.py
git commit -m "Demographics: the practices' fit on the normal-speed run's saves; the wealth curve, cuts and held share"
```

Add `te_demog_tech_injections.txt` to the `git add` if Step 6 changed it.

- [ ] **Stop A (owner).** Post the results doc's fit, regional table and gate to the owner, with Owner questions 1–4.
  Continue to Task 7 on the owner's word.
  - If a gate item fails at every neat point of the grid, say which, with the candidates, and don't widen the grid
    beyond the spec's knobs. The spec's other levers are phase 3's or new owner calls: a geographic disease term
    (calibration step 3), and marital fertility for the Low Countries (§2.3).

---

### Task 7: The generator writes the practices' values and loops

**Files:**
- Modify: `scripts/generators/gen_demographics.py` (`practices(o)` in `render_values` after `multipliers(o)`;
  `practice_loops(o)` in `render_effects` after `absorbed_walk(o, root)`; `"practice_rate"` in `constants`; the
  module docstring's list)
- Regenerate: `te_demog_generated_values.txt`, `te_demog_generated_effects.txt`
- Test: `test_gen_demographics.py`

**Interfaces:**
- Consumes: Task 2's params.
- Produces (state scope unless noted):
  - `te_demog_pr_start_<P>` (the start ladder);
  - `te_demog_pr_erosion_contraception`;
  - `te_demog_pr_target_<P>`;
  - `te_demog_pr_term_<P>` (state or country: 1 − cut × `var:te_dg_pr_<P>`, 1 with no share);
  - `te_demog_pr_terms` (their product);
  - `te_demog_marriage_age` (state or country) and `te_demog_pr_share_bs` (state or country, 0 with no share);
  - `te_demog_k_practice_rate`;
  - effects `te_demog_practices_seed`, `_step`, `_country_init`, `_country_add`, `_country_store`, each calling
    `te_demog_practice_<name> = { P = <p> }` for p in `P.PRACTICES`.

- [ ] **Step 1: Write the failing tests** (append to `TestGenerated` in `test_gen_demographics.py`)

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
            self.assertIn(f"multiply = te_demog_pr_term_{p}", self.values.split("te_demog_pr_terms = {", 1)[1])
        lm = self.values.split("te_demog_pr_target_lm = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("te_inh_has_undivided_farms = yes", lm)
        self.assertIn("has_law = law_type:law_primogeniture", lm)
        self.assertNotIn(f"modifier:{P.ACCESS_TYPE}", lm, "health care erodes Birth Spacing only")
        bs = self.values.split("te_demog_pr_target_bs = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn(f"modifier:{P.ACCESS_TYPE}", bs)
        self.assertIn(f"te_demog_k_practice_rate = {{ value = {gen.lit(P.PRACTICE_RATE)} }}", self.values)

    def test_the_practice_loops_call_every_practice(self):
        for name in ("seed", "step", "country_init", "country_add", "country_store"):
            body = self.effects.split(f"te_demog_practices_{name} = {{", 1)[1].split("\n}\n", 1)[0]
            self.assertEqual(re.findall(rf"te_demog_practice_{name} = \{{ P = (\w+) \}}", body), list(P.PRACTICES))
```

- [ ] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_gen_demographics`
Expected: FAIL (`te_demog_pr_start_lm` not found).

- [ ] **Step 3: Write the generator functions**

```python
def _by_value(table):
    """[(value, [keys])] for a {key: value} table, by value then key: one if per value."""
    out = {}
    for key, value in table.items():
        out.setdefault(value, []).append(key)
    return [(v, sorted(keys)) for v, keys in sorted(out.items())]


def practices(o):
    """Late Marriage and Birth Spacing (docs/superpowers/plans/2026-10-11-demographics-late-marriage.md): each
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
    o("# State scope: where each practice's share drifts (demographics_model.practice_target): its start less what")
    o("# contraception (and for Birth Spacing, health care) erodes; Late Marriage adds impartible inheritance on the")
    o("# farms and women's paid work. Read by te_demog_practice_step after the walk.")
    for p in P.PRACTICES:
        o(f"te_demog_pr_target_{p} = {{")
        o(f"value = te_demog_pr_start_{p}")
        o("multiply = {")
        o("value = te_demog_pr_erosion_contraception")
        if P.PRACTICE_EROSION_ACCESS[p]:
            o(f"add = {{ value = modifier:{P.ACCESS_TYPE} divide = {lit(P.PRACTICE_ACCESS_SPAN)} min = 0 max = 1 "
              f"multiply = {lit(P.PRACTICE_EROSION_ACCESS[p])} }}")
        o("max = 1")
        o("multiply = -1")
        o("add = 1")
        o("}")
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

`practices` hard-codes `te_dg_pr_lm` and `te_dg_pr_bs` in the panel's two values: they are Late Marriage's and Birth
Spacing's, not every practice's.

- [ ] **Step 4: Regenerate and run the tests**

```bash
$V scripts/generators/gen_demographics.py
$V -m unittest test_gen_demographics test_demographics_registry > /tmp/claude-1000/t7.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t7.txt
```
Expected: `OK`. Nothing calls the new values yet.

- [ ] **Step 5: Commit**

```bash
git add scripts/generators/gen_demographics.py common/script_values/te_demog_generated_values.txt common/scripted_effects/te_demog_generated_effects.txt test_gen_demographics.py
git commit -m "Demographics generator: the practices' start ladders, targets, terms and loops"
```

---

### Task 8: The census runs the practices

**Files:**
- Create: `common/scripted_effects/te_demog_practice_effects.txt`
- Modify: `common/scripted_effects/te_demog_effects.txt`:
  - `te_demog_seed`: `te_demog_practices_seed = yes` before `te_demog_prepare = yes`;
  - `te_demog_step_begin`: `te_demog_practices_step = yes` before `te_demog_prepare = yes`;
  - `te_demog_country_census`: `te_demog_practices_country_init = yes` after its other locals,
    `te_demog_practices_country_add = yes` inside `every_scope_state` after `te_dg_c_s_pm` is set, and
    `te_demog_practices_country_store = yes` after `te_demog_store_figures = yes`;
  - the header lists `te_dg_pr_<P>`.
- Modify: `common/script_values/te_demog_values.txt`: `te_demog_tfr` gains `multiply = te_demog_pr_terms`, and its
  comment names the practices.
- Test: `test_demographics_registry.py`:
  - `PRACTICE_EFFECTS` constant;
  - `_Engine` loads it and learns `region`, `state_region` and siblings;
  - `_engine_for` gives the targets as fixtures;
  - new class `TestPracticesScript`.

**Interfaces:**
- Consumes: Task 7's generated values and loops; Task 2's model functions.
- Produces: state variables `te_dg_pr_lm`, `te_dg_pr_bs`; the same names on the country (people-weighted means).

- [ ] **Step 1: Teach the interpreter what the machinery uses**

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

`_engine_for` gains `place=(None, None), targets=None`. It sets `eng.place = place` and adds one fixture per practice,
`f"te_demog_pr_target_{p}": (targets or {}).get(p, 0.0)`.
- The targets read the owner, which `_Engine` doesn't know, so they are fixtures, as the owner's multipliers are.
- At 0 a state with no share stays at 0, so every existing twin comparison (`TestCohortScript`) is unchanged.

- [ ] **Step 2: Write the failing tests** (a new class after `TestNaturalFertilityScript`)

```python
class TestPracticesScript(unittest.TestCase):
    """Late Marriage and Birth Spacing (te_demog_practice_effects.txt and the generated values) against the model:
    docs/superpowers/plans/2026-10-11-demographics-late-marriage.md, Task 8."""

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

    def _seeded(self, place, siblings=(), targets=None):
        eng = _engine_for(self.INP, 1836, 250000.0, place=place, targets=targets)
        eng.siblings = [dict(s) for s in siblings]
        eng.call("te_demog_seed")
        return eng

    def test_the_seed_takes_the_start_with_no_siblings(self):
        eng = self._seeded(("STATE_RIGA", "region_eastern_europe"))
        self.assertEqual((eng.vars["te_dg_pr_lm"], eng.vars["te_dg_pr_bs"]), (0.8, 0.0))

    def test_seeding_order_does_not_matter(self):
        """Review Focus 1: an old save's states seed on their own days. Siblings share a start, so the second state of
        a split region takes the same table value, and a neighbour across the Hajnal line plays no part."""
        first = self._seeded(("STATE_RIGA", "region_eastern_europe"))
        second = self._seeded(("STATE_RIGA", "region_eastern_europe"),
                              siblings=[{"te_dg_pr_lm": first.vars["te_dg_pr_lm"], "te_dg_pr_bs": 0.0,
                                         "state_population": 400000.0}])
        self.assertEqual(second.vars["te_dg_pr_lm"], 0.8)

    def test_a_new_state_takes_its_siblings_shares(self):
        """Review Focus 3: a split mid-game is the same people, so it takes its siblings' drifted, people-weighted
        shares, not the 1836 table."""
        sibs = [{"te_dg_pr_lm": 0.5, "te_dg_pr_bs": 0.1, "state_population": 300000.0},
                {"te_dg_pr_lm": 0.9, "te_dg_pr_bs": 0.3, "state_population": 100000.0},
                {"state_population": 900000.0}]                          # a sibling with no share yet
        eng = self._seeded(("STATE_POSEN", "region_eastern_europe"), siblings=sibs)
        self.assertAlmostEqual(eng.vars["te_dg_pr_lm"], demographics_model.practice_seed(0.8, [(3e5, 0.5), (1e5, 0.9)]))
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

- [ ] **Step 3: Run them to see them fail**

Run: `$V -m unittest test_demographics_registry.TestPracticesScript`
Expected: FAIL (`effect te_demog_practices_seed` unknown, or `te_dg_pr_lm` missing).

- [ ] **Step 4: Write the machinery** (`common/scripted_effects/te_demog_practice_effects.txt`, with a UTF-8 BOM)

```
# ============================================================================
# DEMOGRAPHICS — the practices: Late Marriage (lm) and Birth Spacing (bs)
# docs/superpowers/specs/2026-10-10-demographics-late-marriage-design.md (approved by the owner 2026-10-11);
# docs/superpowers/plans/2026-10-11-demographics-late-marriage.md
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
# other states in its state region that hold one (a split state is the same people as its sibling), else its start
# (te_demog_pr_start_$P$). Siblings share a start, so an 1836 game, an old save or a rule switched on mid-game seeds
# every state at its own table value, whatever order the states' pulses come in. A share already held stays: a census
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
			set_variable = { name = te_dg_pr_$P$ value = te_demog_pr_start_$P$ }
		}
	}
}

# THIS = a state at its census step (te_demog_step_begin, after the walk and before te_demog_prepare reads the term):
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

- [ ] **Step 5: Run the tests, the formatter and the audits**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/te_demog_practice_effects.txt common/scripted_effects/te_demog_effects.txt common/script_values/te_demog_values.txt
$V -m unittest test_demographics_registry test_gen_demographics test_demographics_model > /tmp/claude-1000/t8.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t8.txt
for a in script_argument_audit empty_effect_audit duplicate_key_audit silent_variable_audit; do $V $a.py --strict || echo "FAIL $a"; done
head -c 3 common/scripted_effects/te_demog_practice_effects.txt | od -An -tx1
```
Expected:
- `OK` and no `FAIL`;
- the BOM bytes `ef bb bf`, exactly once (`head -c 6` must not show them twice).

- [ ] **Step 6: Commit**

```bash
git add common/scripted_effects/te_demog_practice_effects.txt common/scripted_effects/te_demog_effects.txt common/script_values/te_demog_values.txt test_demographics_registry.py
git commit -m "Demographics: the census seeds and drifts Late Marriage and Birth Spacing, and its children per woman takes them"
```

---

### Task 9: Primogeniture's farm births under Full (call 4)

**Files:**
- Modify: `common/static_modifiers/te_inheritance_modifiers.txt` (`inh_primogeniture_rural`)
- Modify: `common/scripted_effects/te_inheritance_effects.txt` (`te_inh_refresh_rural_effects`)
- Modify: `localization/english/te_concepts_l_english.yml` (`inh_primogeniture_rural_desc`)
- Test: `test_demographics_registry.py` (new class `TestPrimogenitureUnderFull`), `test_release_census_inputs.py`

**Interfaces:**
- Consumes: #892's `te_demog_line_births` (it sums `state_demog_absorbed_birth_rate_mult`), `te_demog_lines_refresh`,
  `te_demog_events.4`, `te_demog_lines_apply`.
- Produces: nothing new; the line rides an existing family.

- [ ] **Step 1: Write the failing tests**

```python
class TestPrimogenitureUnderFull(unittest.TestCase):
    """Call 4 (the late-marriage spec 4.5; plan D3): Primogeniture's +10% farm births come off under Full, where the
    census's Late Marriage stands in for them, and nothing changes outside Full."""

    MODS = ROOT / "common" / "static_modifiers" / "te_inheritance_modifiers.txt"

    def test_the_line_sits_on_the_absorbed_family(self):
        body = _block(_text(self.MODS), "inh_primogeniture_rural")
        code = re.sub(r"#[^\n]*", "", body)
        self.assertNotRegex(code, r"\bstate_birth_rate_mult\b")
        self.assertRegex(code, rf"\b{P.ENGINE_LINE_TYPES[('absorbed', 'state_birth_rate_mult')]} = 0\.1\b")
        self.assertRegex(code, r"\bstate_migration_quota_mult = 0\.2\b", "the migration line stays")
        # Forced Heirship's -0.15 is phase 3's (spec 4.5, parent 13)
        self.assertRegex(_block(_text(self.MODS), "inh_forced_heirship_rural"), r"state_birth_rate_mult = -0\.15")

    def test_the_rural_refresh_fires_the_lines_refresh(self):
        """No month's lag (#892's owner decision 2): the pair follows the yearly rural refresh the same day, from a
        state event, where the modifier just added is visible."""
        body = re.sub(r"#[^\n]*", "", _block(_text(INH_EFFECTS), "te_inh_refresh_rural_effects"))
        self.assertIn("trigger_event = { id = te_demog_events.4 }", body)
        self.assertGreater(body.rindex("trigger_event = { id = te_demog_events.4 }"),
                           body.rindex("name = inh_primogeniture_rural"))
```

And in `TestLinesScript`, which drives `te_demog_lines_refresh` with the families' sums as fixtures (`self._eng`):

```python
    def test_the_pair_carries_primogeniture_outside_full(self):
        """The late-marriage plan, Task 9 (Review Focus 4): Primogeniture's farm births sit on the absorbed family's
        type on a state modifier (0.1 x an agrarian share of 0.62 here); the engine sums it as it sums a law's, so
        outside Full the pair re-applies it, as main's own line did."""
        eng = self._eng({"state_demog_absorbed_birth_rate_mult": 0.062})
        eng.call("te_demog_lines_refresh")
        self.assertEqual(self.lines(eng), {"te_demog_line_births_up": 0.062})

    def test_under_full_the_census_term_replaces_primogeniture(self):
        eng = self._eng({"state_demog_absorbed_birth_rate_mult": 0.062}, full=True, census_term=True,
                        held={"births": 0.062})
        eng.call("te_demog_lines_refresh")
        self.assertEqual(self.lines(eng), {})
```

In `test_release_census_inputs.py`'s `test_the_moved_engine_lines_ship`, add:

```python
        mods = self._text("common/static_modifiers/te_inheritance_modifiers.txt")
        self.assertRegex(mods, r"(?m)^\tstate_demog_absorbed_birth_rate_mult = 0\.1$",
                         "a release keeps Primogeniture's farm births: the pair re-applies them")
```

- [ ] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_registry.TestPrimogenitureUnderFull test_release_census_inputs`
Expected: FAIL (the field is still `state_birth_rate_mult`; no `trigger_event`).

- [ ] **Step 3: Move the line**

```
# Primogeniture & Entail: large families, and the younger sons leave the
# land. The birth line sits on the moved lines' absorbed family
# (docs/superpowers/plans/2026-10-11-demographics-late-marriage.md, Task 9;
# the late-marriage spec 4.5, call 4): outside the Demographics rule's Full
# setting the moved lines' pair re-applies it (Laws and Institutions in a
# state's birth rates), and under Full the census's Late Marriage takes its
# place, since impartible inheritance raises it.
inh_primogeniture_rural = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds
	state_demog_absorbed_birth_rate_mult = 0.1
	state_migration_quota_mult = 0.2
}
```

- [ ] **Step 4: Fire the lines refresh from the rural refresh**

In `te_inh_refresh_rural_effects`:
- record before the removals whether the Primogeniture modifier was on, as
  `set_local_variable = { name = te_inh_pr_was value = 1 }` inside the existing
  `if = { limit = { has_modifier = inh_primogeniture_rural } … }`;
- at the end of the effect, add:

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

`has_local_variable` exists in 1.14.5 (check `docs/engine/triggers_summary.txt`). If it doesn't, set the local to 0 at
the top of the effect and test `local_var:te_inh_pr_was > 0`.

- [ ] **Step 5: The modifier's text**

`inh_primogeniture_rural_desc` becomes:

`"Families are large, and the younger sons leave to make their own way. Scaled by the state's share of Peasants and Farmers. Under the Demographics rule's Full setting, the census's late marriage takes the place of the larger families."`

Run `python3 organize_loc.py` and keep what it moves.

- [ ] **Step 6: Run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/static_modifiers/te_inheritance_modifiers.txt common/scripted_effects/te_inheritance_effects.txt
$V -m unittest test_demographics_registry test_release_census_inputs > /tmp/claude-1000/t9.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t9.txt
$V organize_loc.py --check; $V loc_coverage_audit.py --strict
```
Expected: `OK`; `--check` exits 0.

- [ ] **Step 7: Commit**

```bash
git add common/static_modifiers/te_inheritance_modifiers.txt common/scripted_effects/te_inheritance_effects.txt localization/english/ test_demographics_registry.py test_release_census_inputs.py
git commit -m "Demographics: Primogeniture's farm births ride the absorbed family; under Full, Late Marriage replaces them"
```

`git add localization/english/` stages everything `organize_loc.py` rewrote there. Check `git status` first, and stage
only the files it touched.

- [ ] **Stop B (fresh review).** A fresh reviewer, on the most capable model, reads Tasks 7–9's diff against this plan,
  the Global Constraints and Review Focus 1–4. What to check:
  - the seed's sibling rule;
  - that a re-seed keeps the shares;
  - the step's order before `te_demog_prepare`;
  - fast mode's clock (`te_demog_events.2` → the census → `te_demog_step_begin`), which must step the practices once a
    clock year;
  - every `divide`;
  - the rural refresh's event;
  - that nothing new reads the rule.

  Fix what it finds before Task 10. Batch reviews of the earlier tasks aren't needed: Tasks 1–6 are Python with their
  own tests, and Stop A reviewed the numbers.

---

### Task 10: The panel, the console and the loc

**Files:**
- Modify: `localization/english/te_miscellaneous_l_english.yml`: `te_demog_st_tfr_terms`, `te_demog_ov_tfr_capital`,
  `te_demog_st_tfr_tt`, `te_demog_ov_tfr_tt`, and the "How Demographics Works" text if it describes fertility (grep for
  `marry` and `legal standing`)
- Modify: `common/scripted_effects/te_debug_demog_effects.txt` (`te_debug_demog_mods_line`),
  `common/script_values/te_debug_demog_values.txt`
- Test: `test_demographics_registry.py`

- [ ] **Step 1: Write the failing tests** (in `TestNaturalFertilityScript`, beside the tooltip tests)

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
        for key in ("te_demog_ov_tfr_tt", "te_demog_st_tfr_tt"):
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

- [ ] **Step 2: Run them to see them fail**

Run: `$V -m unittest test_demographics_registry.TestNaturalFertilityScript`
Expected: FAIL.

- [ ] **Step 3: The loc.** Keep each key's existing lines and splice in the new ones.

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

- [ ] **Step 4: The console's line** (`te_debug_demog_values.txt`)

```
te_debug_demog_pr_lm = { value = 0 if = { limit = { has_variable = te_dg_pr_lm } value = var:te_dg_pr_lm } }
te_debug_demog_pr_bs = { value = 0 if = { limit = { has_variable = te_dg_pr_bs } value = var:te_dg_pr_bs } }
te_debug_demog_pr_target_lm = { value = te_demog_pr_target_lm }
te_debug_demog_pr_target_bs = { value = te_demog_pr_target_bs }
te_debug_demog_line_absorbed_b = { value = modifier:state_demog_absorbed_birth_rate_mult }
```

Format them as the file's other blocks (one field a line). Append to `te_debug_demog_mods_line`'s `debug_log` string:

` lm=[THIS.ScriptValue('te_debug_demog_pr_lm')|3] bs=[THIS.ScriptValue('te_debug_demog_pr_bs')|3] lm_target=[THIS.ScriptValue('te_debug_demog_pr_target_lm')|3] bs_target=[THIS.ScriptValue('te_debug_demog_pr_target_bs')|3] absorbed_b=[THIS.ScriptValue('te_debug_demog_line_absorbed_b')|3]`

Add `lm=`, `bs=`, `lm_target=`, `bs_target=` and `absorbed_b=` to the header comment's description of option l's line.

- [ ] **Step 5: Run the tests and the loc checks**

```bash
python3 organize_loc.py
$V -m unittest test_demographics_registry > /tmp/claude-1000/t10.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/t10.txt
$V organize_loc.py --check; $V scripts/analysis/check_localization_files.py; $V loc_render_audit.py --strict; $V script_loc_reference_audit.py --strict
python3 scripts/analysis/check_gui_lint.py
```
Expected: `OK`; every check exits 0.

- [ ] **Step 6: Commit**

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
  - "Generator and harness" (`practices-replay`, `practices-fit`, `regions`);
  - "Owner checks in game" (point to this plan's list).
- Modify: `docs/superpowers/specs/2026-10-10-demographics-late-marriage-design.md`:
  - a note under §2.2 that the curve's base is 6.0 since #869 and the fit's values are the plan's (D1);
  - §3.4's seed rule as built (D5);
  - §5.2's gate as restated, with the owner's answer to question 1.
- Modify: `docs/superpowers/plans/2026-10-10-demographics-phase2-calibration.md` step 2 (built: the fitted values and
  the results doc).
- Modify: `docs/guides/python_tools.md` (the harness's row: the three subcommands and `history`'s two options; a row
  for `demographics_regions.py`).
- Modify: `docs/auto_generated_files.md` (a row for `demographics_strategic_regions.json`: written by
  `demographics_regions.py --refresh` from the base game's strategic regions and the mod's REPLACEs; one-shot).
- Modify: `docs/guides/vanilla_patch_runbook.md` (beside `gen_formable_regions.py`: "`demographics_regions.py --check`;
  `--refresh` when it says stale").
- Modify: `docs/player_guide/08-states.md` § Demographics, "Reading the figures" and the Full paragraph;
  `docs/player_guide/06-politics.md` (one sentence).
- Rebuild: `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`.

- [ ] **Step 1: The player guide** (match the depth already there: one change in each place)

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

In `06-politics.md`, after "under Primogeniture & Entail families are large and the younger sons leave the land.", add:
"Under the Demographics rule's Full setting, the census's late marriage takes the place of the larger families."

- [ ] **Step 2: The other docs** as listed above. Two of them need care:
  - `docs/guides/python_tools.md` is long and LF; edit it with the Edit tool.
  - Check the three CRLF docs aren't touched:
    `grep -c $'\r$' docs/systems/journal_entry_systems.md docs/guides/gui_modding_guide.md docs/vanilla/treaty_articles_reference.md`
    should give the same counts before and after.

- [ ] **Step 3: Run the docs checks**

```bash
$V scripts/analysis/check_player_guide_style.py --strict
$V scripts/build_player_guide.py
$V scripts/build_player_guide.py --check
$V scripts/analysis/check_post_load_rosters.py
```
Expected: the lint is clean and `--check` exits 0.

- [ ] **Step 4: Commit**

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

- [ ] **Step 2: The gate's offline half on the normal-speed run's saves** (Task 6's commands at the applied values)

The gate, against Task 6 Step 2's "today" (Global Constraints; Owner question 1 as the owner answered it):
- every anchor country within ±0.5 children per woman, except those the results doc names with a reason: marital
  fertility (the Low Countries), and Gapminder's flat guesses at half weight;
- the error over the anchor countries 0.5 or less;
- the world's children per woman within ±0.15 of today's;
- world growth as the owner set at Stop A, and China's in 1887 within ±0.1% a year of today's;
- Britain, Sweden and Denmark within 3 years of history's life expectancy in 1837;
- no anchor country of 20M or more shrinking;
- Iran's and Mexico's growth within 0.5% a year of history's;
- every `fertility` and `medicine` scenario in band;
- the replay: no `GATE` line up to 1887.

Write each item's figure in the results doc.

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
  2. **Option l** (`event te_debug_demog.1`) on the capital after its first census step: `lm=1.000`, `bs=0.000`,
     `lm_target` near 1, and `absorbed_b` = 0.1 × the capital's agrarian share under Primogeniture. The last also
     checks that the engine scales a script-only type on a state modifier by its multiplier, which #892 checked only
     for laws and institutions.
  3. **Disabled, a new game, a farming state in Britain** (Primogeniture). After its first yearly pulse, its birth-rate
     breakdown shows the Laws and Institutions line that day, at +10% × its Peasants' and Farmers' share, and no "Cadet
     Sons Leave the Land" birth line. The modifier still shows its migration line.
  4. **Full, the same state after its first census step:** no Laws and Institutions birth line, Census: Births present,
     and option n's `q_b` at 0.
  5. **A split state.** Release or annex part of a state region (debug). At its next census, the new state's option l
     shows its sibling's `lm` and `bs`, not the table's.
  6. **An old save.** Load a Full save made before this build. Before each state's next yearly pulse its tooltip shows
     ×1.00 for both practices; after it, its table values.
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
| A | Task 6 | the owner | The fitted, rounded values, the regional table and the gate, with Owner questions 1–4. No script before the owner's word |
| B | Task 9 | a fresh reviewer (most capable model) | Tasks 7–9: the risky script (seed, step, Primogeniture's line), per Review Focus 1–4 |
| C | Task 12 Step 3 | a fresh reviewer (most capable model) | The whole branch against the spec and this plan |

Then the owner's in-game list (Task 12 Step 4).

## Risks

- **The raise lifts growth where neither practice holds** (D1, Owner question 1). The Middle East, Russia, Africa and
  the Americas get ×1.15 births. #894's excess outside Europe grows unless call 8's mortality refit raises deaths
  there. Task 6's regional table measures it, and Stop A decides.
- **Two knobs may not move mortality the right ways.** Step 1's poverty term and base infection read SoL, which doesn't
  separate Britain (needs fewer deaths) from Mexico (needs more), as §1.4 found for fertility. If no neat point passes,
  Stop A names it and the lever is the owner's: calibration step 3's geographic term.
- **The era-3 timing** (spec §4.2). Contraception starts the West's erosion a generation before history's marriage
  boom. Britain 1900 reads about 0.2 low. The fit's means pair and the spec's later trigger (0.35, after the Pill)
  are the comparison; the results doc reports both.
- **The women's-rights overlap** (D2) is at most about 3% of births. Owner question 2.
- **Old saves.** States seed at their next census step, on the table (D5), whatever the drift since 1836 would have
  given. A state in 1950 starts at its 1836 custom and drifts to its target over a generation. The census is
  experimental and off by default, so this is acceptable. The alternative, seeding at the target, would have put
  Japan's Late Marriage at about 0.1 in a new game too (its inheritance driver), against call 3.
- **Performance.**
  - Per state a year: two ladders of about 30 triggers each, two targets, and one sibling walk only when a share is
    missing.
  - Per country census: two sums.
  - No new pop or building walk, no neighbour walk.
  - Saves gain two variables a state (about 0.1 MB).
- **Fast mode.** The practices step once a clock year, with the census. Literacy, laws and contraception keep the
  calendar, so a fast run's practices erode on 19th-century conditions for longer, as everything else does there.
- **Revolutions and changes of owner.** The shares are state variables, so they stay ("the winner continues the
  nation"). A new owner's laws reach the target at the next step.
- **The rural refresh's event.** `trigger_event` without `days` is assumed to run after the current effect, so the
  lines refresh sees the modifier just added. #892's hooks assume the same. The in-game list's item 3 is the check, and
  `days = 1` the fix (#894 carries the same note for the hooks).
- **The release.** A release has no rule, so the census and the practices never run. Primogeniture's line ships on its
  moved-lines type, and the pair re-applies it (Task 9's release test).
