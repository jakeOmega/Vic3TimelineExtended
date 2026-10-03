# Late-game script performance

A living tracker for making late-game Victoria 3 runs faster with this mod
loaded. It records how to measure, the measurements so far, what was changed,
and what is still open. Profiler mechanics and the hot patterns found belong
in `docs/guides/scripting_best_practices.md` § "Script Performance: the
Profiler and Hot Patterns". This file covers what was found in this mod.

## How to measure

1. Load the same save each time. On 2026-10-03 that was `autosave_exit.v3`,
   7 Nov 2072, a late game with about 160 countries. Note the in-game date.
2. In the console, run `ScriptProfiling.Enable`. Play unpaused, with the mod's
   panels closed, across at least one month boundary. Note the date, then run
   `ScriptProfiling.Dump`. It writes `logs/script_profiling.txt`. Copy it at
   once: the next dump overwrites it, and it is cumulative since `Enable`.
3. For journal-entry pulses, on_actions and events, which the dump doesn't
   record, use `Script.Profiling.Gui` with "Average time per tick
   (inclusive)". Then screenshot the top list, the callees of `on_actions
   (on_actions) @ <first mod file>:1` (the whole merged monthly country pulse),
   and the callees of `on_actions (effect) @ <unknown>:0` (journal-entry
   pulses).
4. Compare two dumps per tick-equivalent. Use a per-tick vanilla entry as the
   clock: `common/pop_types/aristocrats.txt:33` calls, or
   `ai_strategies/00_default_strategy.txt:1401`. Raw seconds aren't
   comparable when the machine's load differs. Divide by vanilla's per-call
   cost ratio between the runs to correct for it.

Before reading a session's dump, check its startup log. A file the engine
drops at load leaves its entries out of the dump entirely (see "The doubled
BOM" below).

## Measurements

The same save, 7 Nov 2072 → Jan 2073, measured with the flat dump.

| | run 3 (before) | run 5 (this PR) | change | speed-adjusted |
|---|---|---|---|---|
| All script, per tick-equivalent | 40.8 s | 30.5 s | −25% | −11% |
| Mod script (incl. interest-group overrides) | 17.4 s | 12.4 s | −29% | −15% |
| Company-building `potential`/`possible` | 5.2 s | 1.8 s | −66% | −60% |
| Covert actions' `possible` (share of all) | 2.9% | 0.3% | | |
| Wonders' `potential` (share) | 3.1% | 1.3% | | |
| UN propose buttons' `visible` (share) | 4.4% | 2.9% | | |

Run 5's machine ran vanilla script about 16% faster per call; "speed-adjusted"
divides that out.

The GUI profiler, the same save and one month boundary each time:

| Monthly country pulse (worst thread) | before | this PR |
|---|---|---|
| Whole merged `on_monthly_pulse_country` | ~1.5 s / month | ~1.25 s / month |
| `remove_invalid_buildings` (company cleanup) | 985 ms | gone from the top callees |

## What this PR changed

All are exact: they change no result unless a line says otherwise.

- **Company buildings (312).** `potential` keeps only an `any_scope_state =
  { has_building }` test, and the exact scan, which also sees a queued site,
  moved to `possible` with a tooltip. That changes behaviour in two ways,
  both owner-approved. The rule is written as one site per country; the old
  `any_state` was documented as global, i.e. one site in the world. And a
  second state shows the building greyed out instead of hidden.
- **Company cleanup.** Monthly, it now runs only in countries and states with
  a `bg_company_buildings` level.
- **Wonder roll.** One building scan as the on_action's `trigger`.
- **Cultural pull from monuments.** It skips countries and states with no
  `bg_monuments` level.
- **Covert operations.** `covert_operations_active` makes one pass instead of
  ten, and the funding test comes first in all 14 actions' `possible`
  (owner-approved: the tooltip line order changed).
- **UN cases.** Cheapest-first ordering, and an `is_at_war` gate in front of
  the arms-embargo world walk.
- **Continent tests** use `is_in_geographic_region`.
- **Antimatter / solar slot `possible`.** The cheap tests run first.
- **Formable gating.** `count >= 1` is dropped and the top-3 test comes first
  (owner-approved).
- **Colonial stability terms.** Each count is computed once, and the pressure
  terms are gated on a condemner existing (owner-approved).
- **Suit portraits.** The character tests run before the culture triggers.
- **UN bulk lobbying.** The `has_variable` guard stops 72 error lines per
  tooltip build.

## Lessons

- **The doubled BOM.** A rewrite script decoded a file as `utf-8`, keeping
  its BOM, and wrote another BOM in front. The engine dropped the whole file:
  all 323 company buildings were gone, with `Duplicated key = will not be
  created` at load. `test_bom_normalizer` now fails CI on this, and
  `bom_normalizer` repairs it.
- **Merged on_actions in the GUI.** "`on_actions (on_actions) @
  wonder_events_on_actions.txt:1` 516 ms" was the whole monthly country
  pulse, not the wonder roll.
- **Not this branch.** A crash at `victoria3.exe` offset `0x4223fd0` on
  2026-10-03 matched one on 2026-09-30, on the same build. It followed
  loading a different save, and `autosave_exit` ran cleanly.

## Open (ranked by measured cost)

1. **AI construction planning volume.** Since the merge of #679 into this
   branch, the AI asks buildings' `possible`, `can_build_private` and
   `ai_value` about 7× more often. Vanilla buildings are affected too:
   `01_industry.txt` went from 62k to 459k calls per tick-equivalent. That
   took most of the company-building saving. The owner expects it to be
   temporary, as the AI re-plans after #679 changed budgets. Check that it
   settles in a longer run; if not, compare against plain `main`.
2. **Monthly country pulse, ~1.25 s per month.** Cultural Hegemony
   `ch_monthly_pulse_on_action` 303 ms, monetary 191 ms, combined arms 118 ms,
   `sol_expectations_on_actions.txt:9` 117 ms.
3. **Journal-entry monthly pulses, 889 ms.** Cultural Hegemony 319 ms, covert
   warfare 262 ms, UN 86 ms, banking 72 ms, Strategic Reserve 42 ms, nuclear
   62 ms. In the CH pulse, `cultural_hegemony_benchmark_mult` (two
   `cultural_pull_raw`s each) is evaluated three times. In the covert pulse,
   `covert_ops_sync_all` runs 14 pact scans; gate it on the country having
   any covert pact or `iw_ops`.
4. **Interest-group overrides** (`common/interest_groups/00_*.txt`,
   regenerated): 8% of script time. Diff the hot lines against vanilla to see
   whether the mod added cost.
5. **UN propose buttons.** Still 2.9%. Mandate and court-referral cases walk
   every state in the world. The exact pre-gates (`number_of_claims`,
   `has_claim`) are unproven, so the only clear option is a monthly cache,
   which is an owner call.
6. **The Cultural Hegemony panel** reads live `cultural_pull_total` on every
   frame while open. A monthly snapshot would be cheaper, and is an owner
   call.
7. **The colonial stability bar** still evaluates its 21 terms three times
   per read (the bar's lines, `drift_total` and `drift_uncapped` in the cap
   term).
