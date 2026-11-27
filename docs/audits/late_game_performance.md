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
   (on_actions) @ <file>:<line>` (a whole merged vanilla hook, such as the
   monthly country pulse, labelled with the last mod file by name that
   declares it, at the line where it does; `:1` only when the hook opens the
   file), and the callees of `on_actions (effect) @ <unknown>:0`
   (journal-entry pulses).
4. Compare two dumps per tick-equivalent. Use a per-tick vanilla entry as the
   clock: `common/pop_types/aristocrats.txt:33` calls, or
   `ai_strategies/00_default_strategy.txt:1401`. Raw seconds aren't
   comparable when the machine's load differs. Divide by vanilla's per-call
   cost ratio between the runs to correct for it.

Before reading a session's dump, check its startup log. A file the engine
drops at load leaves its entries out of the dump entirely (see "The doubled
BOM" below).

### Through the game QA harness (2026-11-12)

The harness (`python3 -m game_qa`, skill `game-qa`) runs all of the above
without anyone at the keyboard. Copy the save to a fixed name first (the next
exit autosave overwrites the original), then `start --save <copy> --playset
current`. Since 2026-11-13 (#1700) `profile start`, `profile dump [LABEL]` and
`profile summary` do what the list below describes: they clear and enable,
copy both dumps and `dedicated_server.log` into the run folder, and give the
wall time per day and frame type, the top tick tasks and the script time by
file. `start --game-arg` and `start --add-mod` (a variant mod folder, for an
A/B on the same save) go with them. The profile verbs, `--game-arg
no_notifications` and one `--add-mod` ran live on 2026-11-13 on the 1931
save, before the PR's review fixes
(`docs/testing/game-qa-results-2026-11-13.md`); the other flags and a run
without `--add-mod` have not. The `console` route below still works.
Copy every output out of the user-data folder before `stop`, because the
restore puts `logs/` back.

- **Engine tick tasks**: `clear_ticktask_timings`, play, then
  `dump_ticktask_timings`. It writes `ticktask_timings.csv` to the user-data
  root, with one row per engine task per frame (`frame,task,milliseconds,
  calls,longest_lock`). The frame is the game date in hours, four frames a
  day (hours 0, 6, 12 and 18), and every frame since the clear is kept. The
  restore puts back the owner's copy of the file, or removes one the run
  created (the snapshot set has held it since 2026-11-13). There is no task
  for on_actions or events: they run outside every task, and only the GUI
  profiler sees them.
- **Wall clock**: `logs/dedicated_server.log` stamps each frame with the
  second (`Processing Tick: 1931.9.1.6`). Read it per frame type: hour 0 on
  the 1st, hour 0 on the weekly day, other hour 0s, and the sub-ticks. The
  rotated `dedicated_server.N.log` files hold the owner's own play the same
  way, with no debugger or profiler attached. That is the cleanest wall clock
  there is.
- Check the speed dial on a `shot`. Whether wall time measures the work
  depends on it being at V.
- `log_ticktask_performance` claims to write `profiling.log` but wrote
  nothing (#1700; again on 2026-11-12, enabled for 28 game days, 5 August to
  2 September).

The scripts used on 2026-11-12 are in
`/mnt/d/vic3te-data/perf-2026-11-12/scripts/`, beside the dumps.

## Measurements, 2026-11-12: 1931, 1.15.1

The owner's save of 1 July 1931 (Singapore; copied as
`perf_bench_sgp_1931_08_12.v3`, a name whose date is wrong) was played to
2 September at speed V through the harness, with the script debugger
attached. The owner's own log runs on past it to 6 September 1931
(`dedicated_server.1.log`), so those frames are a wall clock for the same
dates: 1.9 s a game day over 3 July to 31 August, with no pause in that
span. It was the latest save that 1.15 could load: the 1940 and
2020 saves are 1.14.5. The world held 250–299 countries, 200 or more of them
UN members. Eras after 1931 (nuclear, space, warming at scale) are
unmeasured.

**Wall clock.** The session ran at 1.43–1.50 s per game day. The owner's own
play of this game ran at 1.33 s a day from 1916 to 1921 and at 1.6–1.9 s from
1921 to 1931. Split by frame type over 22,000 frames of the owner's play:

| Frame | Each | Share of wall time | Tick tasks in that frame (session CSV) |
|---|---|---|---|
| Hour 0, ordinary day | 0.77 s | 40% | 0.23 s, of which `RecalculateModifierNodes` 0.13 s |
| Hours 6, 12 and 18 | 0.15 s | 28% | 0.04 s |
| Hour 0, weekly day | 2.85 s (3.3 s in 1929–31) | 24% | 2.6 s: `HandleAutonomousInvestment` 1.1 s, `UpdateBuildingSpendingPriorities_Stage2` 0.31 s, `UpdateCivilWars` 0.30 s, `UpdateEmployment` 0.14 s, `WeeklyUpdateJournalEntries` 0.11 s |
| Hour 0 on the 1st | 3.8 s (5.2 s with the quarterly autosave) | 8.5% | 1.4 s: `MonthlyPulseJournalEntries` 1.06 s (one frame, 1 August) |

Two buckets of wall time are outside every tick task, and neither is
attributed yet:

- **A per-frame floor**: about 0.11 s on every frame, the sub-ticks included,
  where no pulse runs. That is about 27% of wall time: rendering, speed
  pacing, or work the interface does (#1700 has the test).
- **Day-boundary time**: on an ordinary day's hour 0, about 0.43 s beyond the
  tasks and the floor (22% of wall time). The task column is the profiled
  session's (0.23 s against 0.20 s unprofiled), so unprofiled the residual is
  nearer 0.46 s. On the 1st the figure is about
  2.3 s (3.8 − 1.4 − 0.11). Suspects:
  - The day-spread pulses and their events. Monthly country pulses are spread
    over the month, about 9 countries a day (`extra_on_actions.txt:2405` at
    `e1b025436`, a trigger in `decolonization_events_on_action`, fired 249
    times from 3 to 31 July with no 1st in the window), as are the yearly
    state and country pulses.
  - The engine's or the interface's own work at the day change.

  The GUI profiler's root list, sorted by total time, put the largest
  on_actions entry below `un_buttons.txt:1296`, which cost 3.95 s over that
  28-day capture. The call graph ("Which script holds up the day", below)
  splits the bucket.

**Script, 3 July → 5 August** (flat dump, CPU summed over threads, with the
GUI profiler off; line numbers are `main` at `e1b025436`): 0.98 s per game day,
46% of it in mod files. Building-trigger call volume differs between runs (see
the remeasure), so the company row is this run's.

| Mod file | 33 days | Per call | Note |
|---|---|---|---|
| `scripted_buttons/un_buttons.txt` | 4.48 s | 84 µs | AI-only propose buttons' `visible`. `:1296` (credentials) alone 3.07 s at 2.75 ms a call, `:506` (mandate) 0.56 s |
| `buildings/company_buildings.txt` | 3.02 s | 0.75 µs | 4.05 M calls over 810 entries. Spread, and per-call cost near the profiler's own, so an upper bound |
| `country_formation/te_formable_countries.txt` | 1.45 s | 93 µs | AFU `possible` (`:59`) 471 µs a call: three `any_country` walks |
| other mod buildings | 1.5 s | ~2 µs | `01_zz_te_industry`, `extra_buildings`, `te_construction_market_site`, `08_zz_te_wonders` |
| `diplomatic_actions/covert_operations.txt` | 0.46 s | 5 µs | |
| `parties/zz_te_party_join_weights.txt` | 0.39 s | 38 µs | |
| `scripted_progress_bars/extra_progress_bars.txt` | 0.32 s | `:96` 1.3 ms | the colonial stability bar's `monthly_progress` (`:117` on later `main`; open item 11) |

Vanilla script that the mod's content may enlarge:
`treaty_articles/20_law_commitment.txt:108` (1.21 s at 99 µs a call, an
`any_law` walk per law type), `ai_strategies/00_default_strategy.txt` (2.29 s),
`political_movements/00_ideological_movements.txt` (1.56 s).

**Other findings.**

- The mod defines 458 building types against vanilla's 118 (325 company
  flagships, 40 Strategic Reserve sites, 39 wonders). An A/B run added 325
  more types that are never buildable (open item 2):
  `HandleAutonomousInvestment` did not move.
- `RecalculateModifierNodes` is a flat ~130 ms at every day boundary, over
  half of an ordinary day's task time. A flat cost doesn't clear the mod's
  refreshes: remove-and-re-add pulses spread at about 9 countries a day would
  produce exactly that. It stays a suspect.
- On each 1st, `extra_script_values.txt:1587` logs about 5,700 errors in one
  burst (#1703).
- The GUI capture's largest root entry was a trigger in
  `un_mission_effects.txt`. It ranked above `un_buttons.txt` and the
  on_actions, while the UN event `un_events.4` sat open on screen. An open
  event window evaluates its options' effect tooltips every frame. That
  trigger was the contributor-flag mirror's `is_player` test, one walk of
  every country per flag (#1719); since 2026-11-27 the mirror collects the
  players once per rebuild and each flag walks that list. Not remeasured.

## Remeasure after #1713, 2026-11-12: 1931, 1.15.1

The same save and steps, `main` against `main` + #1713, through the harness
(snapshots `20261112T171606Z` and `20261112T183036Z`; data in
`/mnt/d/vic3te-data/perf-2026-11-12/perf2/`). Script time is the flat dump
from 3 July, per game day (CPU summed over threads), over windows of 33 and
37 days. The error counts are from each run's own log copy in the harness's
run folder.

| | `main` | #1713 |
|---|---|---|
| UN AI buttons' `visible` | 136.5 ms | 3.9 ms |
| All script | 877 ms | 741 ms |
| AFU formation `possible` (the external-pressure cache, reverted) | 25.0 ms | 24.9 ms |
| Tick tasks, 3–30 July | 690 ms | 694 ms |
| Wall time, 3–30 July | 1.33 s | 1.33 s |
| `extra_script_values.txt` errors, two month starts | 11,280 lines | 0 |

The UN buttons agree across two runs of `main` (4.48 s against 4.50 s per
33 days). Other entries don't: at the same tick count (`aristocrats.txt:33`
95,384 against 95,263 calls), company buildings took 4.05 M calls and 3.02 s
in the first run against 1.70 M and 1.45 s here, and all script 0.98 against
0.88 s a day. That is call volume (the interface's state, or `main` moving
between the runs), not per-call noise, so compare call counts before reading a
difference. The wall time is whole seconds from `dedicated_server.log`: 35 s
over the same 105 frames in all three runs, the first measurement included.
Had the 136 ms run serially on the main thread, it would have shown as about
3.7 s over those 27 days. It ran on worker threads instead (the bottleneck
column, below).

## Which script holds up the day: the call graph, 2026-11-12

**The profiler window, made readable.** The script profiler is a game `.gui`
window (`jomini/gui/script_profiler/script_profiler.gui`), not an ImGui one.
At its default size the Callees column is cut off. A copy of that file with a
larger `minimumsize` on its root `vbox` (and on the Callers/Current/Callees
row), deployed under the mod's own `gui/script_profiler/`, is picked up live.
`Script.Profiling.Gui` then reopens the window at the new size. Clicking an
entry makes it Current and lists its callees, each with two times. The copy
is a measuring aid only and is never committed (the one used is in
`/mnt/d/vic3te-data/perf-2026-11-12/callgraph/`).

**Bottleneck time is the column that predicts wall time.** Each entry shows
*Bottleneck time (worst thread)* and *Total time (sum all threads)*.
- **Parallel:** trigger and script-value work that the AI and the interface
  run on worker threads has a bottleneck far below its total. The UN
  credentials button's `visible` was 325 ms against 4,079 ms. That is why
  #1713's cut did not move wall time.
- **Serial:** effects have equal bottleneck and total: on_actions, journal
  entry pulses, events' `immediate`, and the progress bars' monthly values.
  They run on one thread at the day boundary, and they are where the mod's
  own wall time is.

**Serial script, 2 July → 1 August 1931** (GUI profiler, one month start,
`un_events.4` answered first; the profiler inflates every figure):

| Entry | 30 days | Largest parts |
|---|---|---|
| `te_construction_market_recalc_events.1` (152 calls: `on_revolution_start` 126, the yearly country pulse 21) | 3,027 ms | all in `te_construction_market_country_update_sites`: 20 ms a call |
| `on_monthly_pulse_country` (265 country pulses) | 2,801 ms | Cultural Hegemony 526, SoL expectations 443, monetary 363, monuments 244, `headlines_on_actions.txt` (vanilla) 121, culture merge 112, trade partner 88, space race 84, eight `extra_on_actions.txt` blocks 393 |
| Journal entry pulses | 2,939 ms | Strategic Reserve weekly 806, covert warfare monthly 791, Cultural Hegemony monthly 689, nuclear program weekly 160 and monthly 72, UN monthly 144, banking monthly 95 and weekly 15 |
| `on_yearly_pulse_state` (63 states) | 2,738 ms | Demographics `te_demog_state_yearly` 2,083 (33 ms a state: the census 1,178; the walks 892; inheritance and Wealth Concentration about 12), local climate 589 |
| `on_monthly_pulse_state` (871 calls; labelled `un_mission_on_actions.txt:25`) | about 600 ms (592–620 in three runs) | callees not opened in this run; in a later run the tourism refresh 302 and the Grand Monuments state pulse 161 |
| Colonial stability bar's `monthly_progress` (`extra_progress_bars.txt:117`, 237 calls) | 899 ms | |
| `on_monthly_pulse`, global (1 call) | 669 ms | journal map 177, power grid 151, UN 110, tax 92, launch windows 40 |

The harness's own read event, `event (immediate) @ te_qa_events.txt:4`
(`te_qa.1`, where the debugger's breakpoint sits), reads 487–504 ms per 30
days in every harness root list. It is not the mod's.

At least 13.7 s of serial script over 30 days (the root list stops at 27
entries), 0.46 s a game day under the profiler. **The profiler multiplies
serial work by about 2.6–3.5×**: `MonthlyPulseJournalEntries` on 1 September
took 1,012 ms unprofiled, 1,103 ms with the flat dump alone and 3,125 ms under
the GUI profiler; `WeeklyUpdateJournalEntries` on 7–28 August 79–85 ms against
236–286 ms; and the call graph's weekly journal-entry pulses, about 196 ms a
weekly day, against about 75 ms unprofiled. (That is measured for the two
journal-entry tasks and inferred for on_actions; `log_ticktask_performance`
was switched on with the profiler, on 5 August.) So the serial script is
about 0.13–0.18 s a game day unprofiled: about a tenth of wall time, 10–14% of
the harness's 1.25–1.33 s a day.

Not all of it is in the unattributed 0.43 s of an ordinary day. The
journal-entry pulses (2.9 s) run inside `MonthlyPulseJournalEntries` and
`WeeklyUpdateJournalEntries`, so the task column already holds them, and the
colonial bar and the global `on_monthly_pulse` run on the 1st. The day-spread
part is the monthly country pulse, the yearly and monthly state pulses and the
construction-market recalc: about 9 s profiled.

**Script per frame type** (flat dump, a dump after each step of one or two
days, 4 August → 3 September): a step of ordinary days ran 0.83–1.6 s of script
(summed over threads), mean 1.1 s a step; the 33-day windows, weekly days and a
1st included, average 0.88–0.98 s a day. The one weekly day stepped alone ran 1.1 s,
so the weekly frame's extra 2.1 s (2.85 s against 0.77 s in the owner's play;
3.4 s in this session's own frames) is engine work, not script
(`HandleAutonomousInvestment` 1.05 s, `UpdateCivilWars` 0.26 s, the economy
tasks about 0.6 s, 1.9 s in all; tick-task CSV of the same run). The month start added the colonial stability bar's 0.3 s and
little else in the flat dump. Its journal entry pulses are effects
(`MonthlyPulseJournalEntries`, 1.05 s in the tick tasks).

**The weekly frame grew most.** Over the owner's own play of this game
(rotated `dedicated_server` logs), five year-long samples put the weekly
frame at 2.06 s (1916–17), 2.47 s (1922), 2.74 s (1927), 3.06 s (1930) and
3.67 s (first half of 1931), though not steadily year by year (3.86 s in
1928). An ordinary hour 0 rose too, from 0.61–0.66 s in 1916–19 to
0.83–1.00 s in 1923–28, and the sub-ticks from 0.11 s to 0.16–0.21 s. The 1st
ranged from 3.4 to 5.5 s, autosave months included (the frame table's 3.8 s
leaves them out).

**The construction market's world walk (#1721).** The largest entry,
`te_construction_market_recalc_events.1`, spent its 20 ms a call in
`te_construction_market_country_update_sites`. That effect walked
`every_state`, the whole world, from a country scope. #1721 makes it
`every_scope_state`. The A/B on the same save compared `main` with `main` plus
#1721: answer `un_events.4`, play 60 days unprofiled, then 30 under the
profiler.
- **Serial script:** over 1 September to 1 October, `on_revolution_start`
  fell from 1,883 ms to under 404 ms, and the yearly country pulse's `events`
  list (`treaty_article_events_on_actions.txt:1`, which fires the recalc)
  from 643 ms to under 404 ms (both fell below the 27th root, 404 ms): at
  least 1.7 s. The other serial roots stayed within 5%.
- **Wall time:** 75 s against 74 s over 3 July to 1 September, and 74 s
  each over 3 July to 31 August; two runs of `main` over that span read 74 s
  and 73 s. The change is below the log's one-second resolution.

Data: `/mnt/d/vic3te-data/perf-2026-11-12/callgraph/`, which also holds the
profiler window file and the scripts.

## Merged `main` remeasured, and three more cuts: 2026-11-12, evening

The same save and steps on `main` at `e13d812b4` (#1713, #1721, #1724 and
#1726 merged; snapshot `20261113T011842Z`), then on `main` plus #1731
(`20261113T014004Z`): answer `un_events.4`, profile 2 July → 1 August, read
the root list and open callees. Both runs ran 119–120 ticks in 96–97 s of
capture. Data: `/mnt/d/vic3te-data/perf-2026-11-12/batch3/`.

**What is left on `main`.** The serial roots, profiled, 30 days:

| Entry | `main` | + #1731 | Largest parts on `main` |
|---|---|---|---|
| `on_monthly_pulse_country` (265 pulses) | 2,603 ms | 2,248 ms | Cultural Hegemony 528, monetary 364, SoL 235, Grand Monuments 177, `headlines_on_actions.txt` (vanilla) 126, culture merge 101, space race 84, trade partner 84, decolonization 81, law consistency 80 |
| `on_yearly_pulse_state` (63 states) | 2,594 ms | 2,528 ms | Demographics 2,106, local climate 430 |
| Journal-entry pulses | 1,698 ms | 1,566 ms | Strategic Reserve weekly 887 (#1730), nuclear programme weekly 181, UN monthly 142, covert warfare monthly 130, banking 97, nuclear monthly 69 |
| `on_monthly_pulse_state` (871 calls) | 584 ms | 496 ms | tourism 268, Grand Monuments 136, `extra_on_actions.txt:3874` 43, Demographics 33 |
| `on_monthly_pulse`, global | 560 ms | 605 ms | power grid 144, UN 108, tax 88, journal map 86, launch windows 39 |

`on_revolution_start` and the colonial stability bar are no longer among the
27 roots shown (#1721, #1726). The harness's read event (`te_qa_events.txt:4`)
read 500–502 ms in both, as before.

**The three cuts (#1731)**, each read once where it was read several times,
measured as callees. The rest of each root moved by 1% or less (monetary
364 → 364 ms, Grand Monuments 177 → 178, culture merge 101 → 101, trade
partner 84 → 84):

| Callee | `main` | + #1731 | What was read more than once |
|---|---|---|---|
| Cultural Hegemony's country pulse | 528 ms | 188 ms | the country's fine-art production (a walk over every country's GDP) 12 times a pulse, the world's (every market) 9 |
| Tourism's state refresh | 268 ms | 179 ms | the base appeal, a chain of some 670 `state_region` branches, twice |
| Local climate's yearly state refresh | 430 ms | 381 ms | the heat excess (the summer and humidity chains), twice in each of the six reads of the heat term |

That is 478 ms profiled over 30 days, about 0.14–0.18 s unprofiled at the
profiler's 2.6–3.5×, or 0.4% of wall time. In game, before and after the
profiled month, `cultural_pull_from_art` equalled min(production,
`country_art_share_pct_diminished`) × (1 + the art modifier) for Singapore,
France, Japan, Italy and Britain, `cultural_pull_total` equalled raw ÷
`ch_world_raw_live` × 100, and the stored-appeal output equalled
`total_tourism_output_bonus_percent` in each capital; the heat term matched
its curve (Singapore: (0.36 × 3.572 + 4.1) × 3.572 = 19.2385). No error
named the saved values. So `save_temporary_value_as` works in a named
script value read inside another value and inside an effect's
`set_variable`, not only at the top of a progress bar.

**A fourth, unmeasured (#1731).** The yearly leaderboard pass
(`ch_yearly_global_update`) read `cultural_pull_display`, the whole pull
chain, twice for every country with any pull (the change since the last
recount, then the stored share) and a third time for the ten board slots.
It now reads it once into `ch_board_share_now`. The pass runs at most once
per 180-day lock (`ch_ldr_lock`, also cleared at a war's end), and not in the
profiled month, so the saving was not measured; it is one to two pull
evaluations per ranked country per pass. The in-game check of
the recount was not run: the harness's `pick` of `te_debug_ch.1`'s recount
option was refused ("No matching pending event"), so it is a play-test row.

**What fires `on_revolution_start` (#1723).** A deploy-only on_action logged
each call in the `main` run: 126 starts and no ends in 30 days. 125 were 25
dynamic-tag countries, five times each on the weekly day (3, 10, 17, 24 and
31 July), with no `scope:target`. Each of the 25 has one state, and the one
read (F31, Zambezia) is recognized, at peace and in a civil war. A
revolution that cannot take a state is tried again at every weekly
`UpdateCivilWars`. The mod's handlers now cost little there (#1721; the
others skip when there is no `scope:target`). Whether these stuck civil
wars make `UpdateCivilWars` itself dearer is open (#1723).

**Does a refresh's re-add drive `RecalculateModifierNodes`? Not shown.** The
engine task that recalculates modifiers takes about 100–135 ms at each day
boundary, a tenth of wall time, more than any refresh's own script. A refresh
that takes a modifier off and puts it back at the same strength changes no
figure, so it was a suspect. Ten unprofiled runs tested it, 2 July → 1
September (62 days, 61 day boundaries), same save, tick-task timings and wall
clock. A, A3 and A4 ran #1731's final build (the three cuts); E and A2 ran
it with the tourism re-add skip it carried until `6192c64b3`; each other run
made one deploy-only change:

| Run | Build | `RecalculateModifierNodes` per day boundary, median | Wall time per day |
|---|---|---|---|
| A | the three cuts | 135 ms | 1.39 s |
| A3 | as A | 101 ms | 1.30 s |
| A4 | as A | 117 ms | 1.32 s |
| B | as A, the 325 flagships unbuildable (touches no refresh) | 121 ms | 1.33 s |
| E | as A, and tourism's refresh skips a modifier whose multiplier did not move | 117 ms | 1.37 s |
| A2 | as E | 104 ms | 1.31 s |
| D | as E, and SoL expectations' three country modifiers not refreshed | 114 ms | 1.34 s |
| F | as A, tourism's two state modifiers not refreshed | 119 ms | 1.34 s |
| C | as A, neither tourism's nor SoL's refreshed | 99 ms | 1.31 s |
| C2 | as C (an audit run shared the CPU for part of it) | 123 ms | 1.44 s |

Three runs of one build read 101, 117 and 135 ms, a spread of about 30%,
nearly all of the ten runs' range (99–135 ms). So the runs neither show the
link nor rule it out. The skip builds (E, A2: 117, 104) read below A, but no
lower than A3, and F, which drops every tourism re-add the skip drops and
more, read 119. The skip was taken out of #1731 for that reason. A test
that could settle it needs either many runs of each build, or a change much
larger than the noise: a deploy-only on_action that re-adds an unchanged
modifier on every state every day, read against the same build without it.

Snapshots: A `20261113T014825Z`, A2 `20261113T023851Z`, A3
`20261113T030656Z`, A4 `20261113T031140Z`, B `20261113T015413Z`, C
`20261113T020016Z`, C2 `20261113T024333Z`, D `20261113T021406Z`, E
`20261113T020847Z`, F `20261113T024839Z`. The CSVs and
logs are in `/mnt/d/vic3te-data/perf-2026-11-12/batch3/`. Open item 13
carries the lead.

## Where the day goes: engine knockouts, 2026-11-13: 1931, 1.15.1

The script cuts of 2026-11-12 each moved wall time by less than the spread
between runs, so this pass asked a different question: which large part of
the day is the mod's to change at all. Each run switched one thing off or
changed one engine setting and read the whole day.

**Method.** The same save and steps (`start --save
perf_bench_sgp_1931_08_12 --playset current`, one day, answer `un_events.4`
with its first option through `pick`, `clear_ticktask_timings`, 60 days,
`dump_ticktask_timings`), with `main` at `fd29ed9f2` deployed. Every change
was an add-on mod loaded with `start --add-mod` (a one-key defines file, or
same-path copies of files), so the deployed folder was never touched. Runs
named `_r` carried `--game-arg disable_renderframeifneeded` (below). Data,
variants and scripts: `/mnt/d/vic3te-data/perf-2026-11-13/` (`runs/<name>/`,
`variants/<name>/`, `scripts/run2.sh`, `wall2.py`, `tasks.py`, `seg2.py`).

**Reading the wall clock.** Wall time is seconds per game day over 3 July to
1 September, from the tick stamps of `dedicated_server.log`. `advance` pauses
the game every two weeks or so to read the date, and the tick being worked
out when the pause lands is a long weekly tick about half the time (53 of
the 90 gaps that span a pause in these runs; the first pause of every run
lands on one). The first reading of these runs dropped every gap that
spanned a pause, which dropped those ticks, and gave figures 0.4% to 12% too
low by how the pauses fell: a run that should have been slower then read as
the fastest of the day. `wall2.py` counts every tick and takes the paused
seconds off the gaps that span a pause; every figure below is read that way.
A single run is then good to about ±4% (13 runs with no change, or one that
left the tick tasks within a few milliseconds: 0.98 to 1.07 s a day). The
tick tasks' own figures come from the engine's CSV and repeat to a few
percent, with two exceptions. `RecalculateModifierNodes` sits near 96 or near
117 ms a day from one rendering-off session to the next. And the rendering
switch moves three tasks: with rendering on `UpdateAI` reads 10–15 ms a day
against 51–62 off, `RecalculateModifierNodes` about 12 ms more, and the
investment pass 182–202 against 160–166; the total is the same (600 against
593).

**The world measured** (a script count on 2 July 1931: 263 countries, 160 of
them with one state; 870 states; 90,231 pops; 13,770 buildings; and the
engine's `logging.popstats` dump of 21 August, which the pop figures below
are from: 89,646 pops holding 2.66 billion people). Singapore,
the played country, owns 7 states and 365 buildings, but its market holds 313
states and its power bloc 314. Its investment pool held £1.13 billion, took in
£54–59 million a week and paid out as much.

| Run | Change | Wall s/day | Tick tasks ms/day | Snapshot |
|---|---|---|---|---|
| B0a | none | 1.550 | 619 | `20261113T121758Z` |
| B0b | none | 1.417 | 569 | `20261113T124419Z` |
| guivan | every mod `gui/` file emptied, or vanilla's copy where vanilla has the file | 1.300 | 602 | `20261113T124926Z` |
| inv_off | `AUTONOMOUS_INVESTMENT_CONSTRUCTION_ENABLED = no` (a bound, not a proposal) | 1.133 | 404 | `20261113T122933Z` |
| inv_div10 | `AUTONOMOUS_INVESTMENT_UPDATE_COUNT_DIVISOR` 500,000 → 5,000,000 | 1.390 | 553 | `20261113T123413Z` |
| inv_refresh | `AUTONOMOUS_INVESTMENT_NUM_FAILED_INVESTMENTS_FOR_REFRESH_PLAYER` 20 → 175 | 1.483 | 631 | `20261113T123906Z` |
| render, R0b, R0c, R0d, R0e | sub-tick rendering off, nothing else (five runs) | 0.983, 1.050, 1.067, 1.067, 1.033 | 607, 590, 591, 582, 570 | `20261113T122318Z`, `…131434Z`, `…152700Z`, `…153603Z`, `…154941Z` |
| noact_r | every mod `common/on_actions/` file emptied | 0.950 | 604 | `20261113T131908Z` |
| nojes_r | every mod `common/journal_entries/` file emptied | 0.950 | 526 | `20261113T145724Z` |
| bsp4x_r | `MIN`/`MAX_TICKS_TO_UPDATE_BUILDING_SPENDING_STATE` 100/200 → 400/800 | 1.000 | 577 | `20261113T133005Z` |

The first six rows ran with sub-tick rendering on, the rest with it off. Two
longer unchanged runs with it off read the same over these dates (1.000 and
1.017; `runs/B120r`, `runs/B365r`).

**Sub-tick rendering.** The launch argument `-disable_renderframeifneeded`
("Sacrifice sub-tick rendering for tick speed" in the binary's own list) and
the console switch `gamestatetick.renderframeifneeded` stop the game
breaking into a tick to draw. With the switch on, frames keep coming through
a tick (`measure_frame_time` over 14 running days: about 10 ms a frame on
average, pauses included, and never more than about 40 ms between two), and
the tick gives way to each. With it off, frames come between a tick's steps
only, and the longest wait for one is 145–180 ms. The tick tasks' total is
the same either way, so the time saved is outside them: whole runs read 1.42
and 1.55 s
a day with rendering on against 0.98 to 1.07 with it off, about 30%. "Sub-tick
rendering, on and off in one session" below has pairs within one session and
what the switch costs on screen.

**With rendering off, a day is about 1.03 s**: 0.57–0.61 s of tick tasks,
about 0.08 s of the mod's on_actions, and about 0.35 s that neither names
(vanilla's own on_actions and events, the frames between ticks, and engine
work that is in no task). The mod's journal entries sit in the first and the
last ("Journal entries" below).

**The mod's on_actions are at most a tenth of the simulation.** Emptying all
77 on_action files (every monthly, yearly and event hook the mod adds) left
the tick tasks where they were and read 0.950 s a day against 1.03 for the
unchanged runs: 0.08 s, give or take the 0.04 of a single run. The call graph
of 2026-11-12 put the same script at about 6.3 s profiled over 30 days, which
at the profiler's 2.6- to 3.5-fold inflation is 0.06–0.08 s a day. That is
the ceiling for every remaining cut to pulse script together. By that profile
the Demographics yearly state step is a third of it and the monthly country
pulse another third.

**`HandleAutonomousInvestment` is the played country's investment pool.**
The pass took 160–202 ms a day, the largest task. Frame by frame it is a
burst on the weekly frame (0.4 to 1.6 s; 1.08 s on average over B0a's nine
weeks) and usually 0–2 ms on every other frame; in two of the nine weeks it
ran on into the following frames (769 ms, then 32–99 ms for 14 frames, after
the frame of 17 July). With the pass switched off a rendering-on day read
1.13 s against 1.42 and 1.55. What it does:

- Each tick a country makes up to `income ÷ AUTONOMOUS_INVESTMENT_UPDATE_COUNT_DIVISOR`
  investment decisions, at least one. Singapore's £54–59 million a week makes
  that 108–118; Britain's £0.7 million and Russia's £1.0 million make 1 and 2.
- A decision costs about 13 ms while the pool is still placing buildings, and
  almost nothing once it has stopped. With the divisor raised tenfold
  Singapore made 11 decisions a tick, and the pass ran at 103–199 ms a tick
  for 1 to 13 ticks after each weekly frame (a median of 5), then at 3–12 ms:
  22 to 154 costly decisions a week, at about 13 ms each. The week's total
  was the same within 18% (158 against 194 ms a day); the weekly frame was
  shorter and the ticks after it longer.
- The other 262 countries add little: at the tenfold divisor the weekly
  frame, where every country decides, read 120–193 ms, no more than the ticks
  after it, where Singapore alone still had decisions to make.
- The 13 ms is presumably the engine scoring every building type in every
  state the country may build in, and Singapore may build across its bloc's
  314 states. It is not the buildings' script: with every `ai_value` block
  taken out of all 36 building files (P1r against P0r, both at the tenfold
  divisor) a tick of 11 decisions still took 115–165 ms against 135–175. The
  runs of 2026-11-12 had already shown that building types failing
  `potential` cost nothing.
- The refresh threshold for a player's country (20 failed decisions) changed
  nothing (inv_refresh).

So the pass costs what a week's decisions cost, and a mod has no setting that
makes a decision cheaper. A larger divisor spreads the same work over the
week's ticks. It would cut the work only if set so high that the week's 28
ticks could not hold the decisions the pool has money for (in this pool's
busiest weeks, fewer than about 5 a tick: a divisor above about £10 million),
and the pool would then pile up unspent, which is the outcome the owner
warned of. A country's
cost follows its pool's income; an all-AI world was not measured.

**`RecalculateModifierNodes` is a per-country cost, and no refresh drives
it.** It ran 96–119 ms a day in every rendering-off run (107–136 with
rendering on), nearly all of it at the day boundary and much the same on
every day, whichever countries' pulses fell on it. The console switch
`gamestatetick.forcefullmodifiernoderecalc` showed that this is the engine's
incremental pass: forced to recalculate everything it took 1,230 ms a day
(18–25 July in session `20261113T130027Z`), so about a tenth of the graph is
redone daily. What does not cause that:

- The mod's on_actions: 115 ms a day with all of them emptied (noact_r).
  That closes open item 13: a refresh that re-adds a modifier at the same
  strength is not what this task spends its time on.
- Decaying modifiers, or modifiers as such: in one session
  (`20261113T135321Z`) every country was given a modifier, then the same one
  decaying, then a decaying one with state and building lines, then that one
  not decaying, and then every state a decaying one. The day-boundary frame's
  median read 112 (none), 105, 106, 110, 108, 105 and 105 (cleared) ms (the
  day's totals 122, 117, 115, 119, 117, 115 and 111). After the dump the
  wide modifier was applied once more and read back on the played country;
  the others were not read.

What does move it is the number of countries (next) and, by less, the mod's
scaling-modifier declarations ("Journal entries").

**Countries.** A setup had every one-state AI country that was at peace and
not in a revolution annexed by its overlord, or else by a neighbor: 119
countries went (144 left; 151 by the run's end), and with them 48 states
(870 → 822, where the annexer already held part of the region) and 6% of the
buildings (12,935 from 13,770); the pops stayed (90,087). Over the same
frames (24 July to 14 September, rendering off) the tick tasks took 452 ms a
day against 536 in the unchanged world, 16% less: `RecalculateModifierNodes`
80 against 114 (it reads 96–102 in its low sessions, so the fall is 16 to
34 ms), `UpdateAI` 35 against 52, the three journal-entry tasks 25 against
38, and the investment pass 101 against 122. That is about 0.7 ms a day of
task time for each country that went, 0.5–0.6 ms of it in the three tasks a
country plainly carries, before its share of the monthly and yearly pulses.
Wall time read 0.889 against 0.928 s a day, inside a single run's ±4%, and
two event windows (`decolonization_events.70`, `production_tech_events.401`)
stood open through the annexed run, which costs time on every frame; so the
task figures are the finding and the wall figure is not a clean one. The 160
one-state countries hold 7% of the world's people and 16% of its pops. They
are a mix of countries there since 1836 (Nepal, Wallachia, Oyo, Hawaii),
released ones (California, Formosa, Lithuania, Île-de-France) and six
revolts that never ended (#1723; seven by late August), which the setup left
alone.

**Pops.** 83% of the pops hold 4% of the people: 23,366 pops (26%) are under
100 people and 56,002 (62%) under 2,000. Singapore's own states hold the most
small pops (`print_states_with_most_small_pops`: Singapore 852, Kundur 469,
Goa 401, Shanghai 388). Of the pops under 100, 21,725 have a pop of their own
culture and religion with at least 100 people in the same state, which is what
the engine's micro-pop dissolution asks for, and 17,292 are employed. Raising
the consolidation defines far past anything shippable (eight keys: merge at
150 workforce under the moderate rule and where a building has two pops of a
profession, not four; the unemployment factor at 1; dissolve under 1,000
people) removed 5.5% of pops in
120 days (84,710 against 89,658) and 8.4% in a year (83,508 against 91,147),
and bought no speed: 1.017 s a day against 1.017 over the 120 days, and 1.044
against 1.000 over the year (`runs/pops_x_r`, `runs/pops_x365r` against
`runs/B120r`, `runs/B365r`), while the pops under 100 people grew from 24,235
to 27,798. The consolidation defines are not a lever here. Why the small pops
stay is in "Small pops" below.

**What showed nothing.** The mod's HUD (guivan: 1.30 s a day with only the
HUD on screen, against 1.42 and 1.55 unchanged and 1.32–1.38 for yesterday's
build; one rendering-on run cannot tell nothing from 0.1–0.2 s, so this is
not shown either way; the mod's own window is another matter, below); the
AI's building-priority interval (bsp4x_r: its task fell from 28 to 17 ms a
day and wall time read 1.000); the console's `gamestatetick.minlocktime` (1
by default; at 100 the days were no faster) and `graphics.capframerate` (30
and 10 left the frame rate at 106–108).

**Console lessons.**
- Typing a boolean engine switch toggles it and prints the new state
  ("Enabled", "Disabled"); there is no read without a write. A number switch
  prints its value when typed bare.
- `threading.enabletaskthreads`, toggled, hung the game at once (the session
  was stopped and restored).
- `optick_capture` answers "This build was compiled without an instrumented
  profiler", so there is no engine profile to be had from a release build.
- `logging.popstats` writes every pop (id, country, state, workplace, type,
  culture, religion, size, workforce and more) to
  `logs/<a folder>/pop_stats.csv`, appending to the same file each time, with
  one header. The harness's restore does not know that folder and leaves it
  (#1758).
- `measure_frame_time start` and `stop` give the average, shortest and
  longest frame between them. `ticktask.list` opens a window with the same
  figures as the CSV. `camera.settransform X Y Z Zoom Pitch Yaw` moves the
  view (X and Z are the province map's pixel column and its row counted from
  the bottom).

### Sub-tick rendering, on and off in one session

Two sessions typed the console switch between 14-day blocks, rendering on
then off, reading "Enabled" or "Disabled" each time and measuring the frame
time through each block: three pairs with the camera where the save opens,
over open ocean (`20261113T143905Z`), and two with it moved over Malaya and
Singapore at a playing zoom (`camera.settransform 6440 0 1560 300 55 0`;
`20261113T144931Z`). The weeks differ in how much the investment pass has to
do, so the column to compare is the time outside the tick tasks.

| Block | Dates | Wall s/day | Tick tasks s/day | Outside the tasks | Average frame | Longest frame |
|---|---|---|---|---|---|---|
| on | 3–17 July | 1.214 | 0.557 | 0.657 | 10.5 ms | 42 ms |
| off | 17 July–2 August | 1.250 | 0.810 | 0.440 | 13.1 ms | 180 ms |
| on | 2–16 August | 1.357 | 0.575 | 0.782 | 10.3 ms | 37 ms |
| off | 16–30 August | 0.929 | 0.520 | 0.409 | 11.8 ms | 145 ms |
| on | 30 August–13 September | 1.357 | 0.602 | 0.755 | 10.0 ms | 42 ms |
| off | 13–27 September | 0.929 | 0.569 | 0.360 | 12.1 ms | 160 ms |
| on, over Malaya | 3–17 July | 1.286 | 0.564 | 0.722 | 10.7 ms | 40 ms |
| off, over Malaya | 17 July–1 August | 1.267 | 0.762 | 0.505 | 13.0 ms | 167 ms |
| on, over Malaya | 1–15 August | 1.429 | 0.544 | 0.885 | 9.8 ms | 31 ms |
| off, over Malaya | 15–30 August | 0.933 | 0.535 | 0.398 | 11.0 ms | 160 ms |

- **Off is faster in every pair**: by 0.22, 0.37, 0.40, 0.22 and 0.49 s a
  day outside the tasks. Pooled over the five pairs that is 0.76 s a day
  outside the tasks with rendering on against 0.42 with it off, on a day of
  about 1.33 s: about a quarter. The whole runs say 30% (1.42 and 1.55 s a
  day on, 0.98 to 1.07 off).
- **What it costs on screen is small.** The game still draws between a
  tick's steps: the average frame went from 10 to 11–13 ms (97 to about 80 a
  second, pauses included) and the longest wait for a frame from about 40 ms
  to 145–180 ms. It is a brief hitch a few times a week of game time, not a
  frozen screen.
- **The view matters little.** Over Malaya, with land, cities, borders and
  names on screen, frames took what they took over open ocean (9.8–10.7 ms),
  and rendering cost 0.72 and 0.89 s a day outside the tasks against 0.66 to
  0.78 over ocean.
- **In the owner's own play the same two months ran at 1.9 s a day**
  (`dedicated_server.1.log`, "Measurements, 2026-11-12"), against 1.3–1.55
  here with rendering on and about 1.03 with it off. What makes real play
  slower than the harness is not known (panels, tooltips and notifications
  are candidates; the view is not), so what the switch saves there is for the
  owner to measure: type `gamestatetick.renderframeifneeded` in the console
  (it answers "Disabled"; typing it again turns it back on; it lasts until
  the game is closed), or add `-disable_renderframeifneeded` to the game's
  launch options.
- **A mod widget can run a console command, under `-debug_mode`.** A
  scripted widget whose state runs `[ExecuteConsoleCommand('popstat')]`
  twenty seconds after the HUD appears (`trigger_on_create = yes`) ran it:
  `debug.log` showed `Running console command: popstat` with nobody typing.
  An earlier widget that was to run the rendering switch itself from a
  `_show` state did nothing, so the switch has not been flipped from the
  interface yet. Whether the interface may run a console command without
  debug mode is not known, and no launch without it was made to find out. If
  it may, the mod could offer the switch as a button.

### The mod's own window

The one large cost found that is the mod's: the Timeline Extended window,
open on its Nation tab, with rendering on (the default).

A scripted widget in an add-on mod opened the window twenty seconds after the
HUD appeared (`GetVariableSystem.Set('com_open_window', 'te_systems_window')`
from a `trigger_on_create` state), on the tab it opens on, Nation. In one
session (`20261113T170446Z`) two blocks ran with it open; then `press esc`
closed it (a screenshot showed it gone) and two more ran.

| Block | Dates | Wall s/day | Tick tasks s/day | Outside the tasks | Average frame | Shortest frame |
|---|---|---|---|---|---|---|
| open | 3–16 July | 2.000 | 0.577 | 1.42 | 18.6 ms | 13.7 ms |
| open | 16–31 July | 2.467 | 0.630 | 1.84 | 19.1 ms | 14.9 ms |
| closed | 31 July–14 August | 1.286 | 0.476 | 0.81 | 10.1 ms | 8.2 ms |
| closed | 14–30 August | 1.438 | 0.633 | 0.80 | 10.1 ms | 8.3 ms |

- **Open, the day is about half again as long.** July (3–31) read 2.25 s a
  day in this session and 2.18 in an earlier one with the window open
  (`20261113T163222Z`, frames of 18.3 and 19.2 ms), against 1.39 and 1.50 in
  the day's two rendering-on runs with it closed: 45% to 62% more. The tick
  tasks do not change, task by task; the time is frames, each twice as dear,
  drawn while the tick waits.
- **A frame costs the same paused.** The shortest frame of an open block
  was 13.7–14.9 ms against 8.2–8.3 closed, the blocks' frame counts leave no
  room for paused frames at the closed rate, and the paused screenshots show
  about 60 frames a second with the window open and 105–120 after it closed.
  So the tab's bindings are read on every frame, whether or not anything
  changed, and the check needs no running game: open the window paused and
  read the frame rate.
- **It is the Nation tab's sections, not the window.** Three sessions each
  opened the window with part of the tab taken out (two blocks each of 7 to
  13 days; `variants/nat_*`): with no panels at all frames took 10.2 and
  9.7 ms (`20261113T173341Z`); with the overview and the five sections but
  not the two list panels, 18.0 and 18.9 ms (`…173803Z`); with only the two
  list panels, which open collapsed, 10.3 and 9.7 ms (`…174246Z`). Wall time
  over 3–17 July agrees: 1.36, 2.00 and 1.36 s a day.
- **What the sections read.** Every row is shown or hidden by a count
  (`te_nation_type_<modifier type>_count`, 83 of them, holding 340
  `has_modifier` tests, with a sum for each group and section: 964 tests in
  `te_nation_generated_values.txt`). And each row that shows is a line of
  text built with `Country.GetModifier.GetValueWithBreakdownFor('<type>')`
  (81 rows in `te_nation_generated_l_english.yml`), which has the engine
  assemble that modifier type's whole breakdown to draw the figure; vanilla
  uses the accessor 21 times in all its interface, one or two to a panel.
  Which of the six panels carries the cost, and whether it is the counts or
  the breakdowns, was not separated; the breakdowns are the likelier, since
  964 `has_modifier` tests should cost far less than 9 ms (#1760 has the
  test).
- **The owner's own play fits, month by month.** Their log of the same game
  (`dedicated_server.1.log`, read the same way) ran July at 2.07 s a day and
  August at 1.60: July beside the open sessions' 2.18–2.25, August beside the
  closed runs' 1.40–1.57. Whether the window stood open in July and not in
  August is for the owner to say.
- **Not measured**: any other tab. Two probes were meant to switch tabs. A
  `trigger_when` on a scripted GUI never opened the window. A chain of timed
  states opened it and was to step through five more tabs and then close
  it (`20261113T171317Z`): frames read 16–20 ms through all 22 blocks, the
  window never closed, and none of the steps' `popstat` stamps reached
  `debug.log`, the first step's included, so the log cannot say whether the
  tabs changed. Either the chain stopped at its first step or five other
  tabs cost what Nation does: not shown either way. Also unmeasured: the
  window full screen; National Info, which mounts the same sections; and
  the window with sub-tick rendering off, where a frame no longer holds up
  a tick.

### Journal entries

With all 29 of the mod's journal-entry files emptied (nojes_r) the three
journal-entry tasks fell from 36 ms a day to 6 (`UpdateJournalEntries` 16.0 →
2.8, the monthly pulses 11.0 → 3.1, the weekly 8.6 → 0.4),
`RecalculateModifierNodes` read 87, and the day read 0.950 s against 1.03.
So the mod's entries are about 30 ms of tick tasks a day, 3% of the
simulation; the one run's wall time puts them at 0.06–0.08 s a day, which is
inside a single run's error of the task figure. Where it goes:

- **The values of the scaling modifiers.** Since #1404 the systems declare
  their standing modifiers on their entries (389
  `scaling_modifiers_while_active` blocks on 18 entries), and the engine reads
  every block's value again for every holder at each update of an active
  entry, every 4 days. With the blocks taken out (noscale_r)
  `UpdateJournalEntries` fell from 16.0 to 4.2 ms a day. With the 18 entries
  updated every day it rose to 40.5; with the other 48 mod entries updated
  every day it stayed at 16.3 (`g_scaling1_r`, `g_rest1_r`). The Map Room,
  one entry with over a hundred map branches, costs nothing while its page is
  shut: the flat dump of 2026-11-12 holds no call of its selector, and the
  run without it read 1.017 s a day (maproom_off_r).
- **The declarations themselves.** `RecalculateModifierNodes` read 87 and 90
  ms a day in the two runs without the declarations (nojes_r, noscale_r) and
  96 to 119 in every other rendering-off run of the day: perhaps 10 to 25 ms a day for 389
  declarations, most of them at zero.
- **The pulses.** The weekly and monthly pulses are 16 ms a day of tasks;
  their parts are in "Merged `main` remeasured" (the Strategic Reserve's
  weekly pulse the largest).

**The update interval: under 1% by the task, and unresolved by the clock.**
An entry's active update can be set per entry (`active_update_frequency =
<days>`, with `inactive_update_frequency`: both keys are in the game binary,
vanilla uses neither, and the first was read in game: on the 18 entries at 12
days `UpdateJournalEntries` fell to 8.6) or for all entries (`NCountry`'s
`JOURNAL_ENTRY_UPDATE_ACTIVE`, 4 by default; at 12 it fell to 7.3, at 1 it
rose to 47.0; `JOURNAL_ENTRY_UPDATE_INACTIVE` at three times its 14 saved
1 ms). By the task that is 9 ms a day, under 1% of the day, for a modifier
that follows its value 12 days late instead of 4, past the 7-day windows that
keep a costly step from being clicked twice (`un_influence_pending`,
`ch_influence_pending`, `colonial_garrison_pending_levels`). The wall clock
does not settle it. Four runs at 12 days for all entries read 0.950, 0.933,
1.000 and 0.983 s a day, a mean of 0.967 against 1.031 for the seven
unchanged runs (6% less, and two of the four below every unchanged run), and
the per-entry key on all 67 mod entries read 0.983. But the run at 1 day,
with three times the task, read 1.000, where a cost that fell with the
interval should have shown as a slower day; the key on the 18 scaling
entries alone read 1.017 at 12 days and 1.000 at 1 day. Many variants were
tried that day and the lowest group looking low is weak evidence. If a gain
of that size is wanted, it needs five or more runs each way in alternation
before anything is built, and the pending windows would have to grow with
the interval.

Snapshots: nojes_r `20261113T145724Z`, noscale_r `…151725Z`, maproom_off_r
`…155600Z`; 12 days for all entries `…150426Z`, `…153143Z`, `…154045Z`, and
with the inactive interval tripled `…151301Z`; inactive alone `…150844Z`; 1
day for all `…161028Z`; the per-entry key at 12 days on the 18 `…152152Z`
and on all 67 `…154513Z`, at 1 day on the 18 `…161454Z` and on the other 48
`…161926Z`.

### Small pops

Two `logging.popstats` dumps of one session, 2 July and 2 August 1931,
matched by pop id (`runs/explore4/dump_A.csv`, `dump_B.csv`).

- **They are churn, not leftovers.** Of 24,183 pops under 100 people on 2
  July, 12,821 were gone a month later, and 12,281 new ones had appeared:
  about 410 a day. Across all sizes 15,446 of 90,420 pops went and 14,799
  came. The engine's merging and dissolving do work; what they remove is
  replaced as fast.
- **Where the new ones come from**: 7,357 were employed, in every kind of
  building (ports 880, urban centers 452, trade centers 422, railways 387),
  and 4,924 unemployed. For 5,502 of them a pop of the same state, workplace
  (or none), profession, culture and religion had existed a month before,
  under another id: 2,684 of those employed, a sliver let go and hired again,
  and 2,818 unemployed. Only 1,750 were assimilating or converting.
- **The ones that stay** (10,820 under 100 people on both dates) are mostly
  employed (9,024), and 7,033 of those work in a building that has fewer than
  four pops of their profession, where the moderate rule does not merge
  (`POP_MERGE_MIN_NUM_POPS_SAME_PROFESSION_MODERATE_CONSOLIDATION`; a
  building may always hire into three, `MIN_POPS_PER_PROFESSION`). That rule
  is not the whole reason, though: the consolidation run lowered it to two
  and the pops under 100 people still grew. What keeps them is not
  established.
- **It would not pay to chase them.** The tasks that walk pops
  (`ProcessEconomicMigration`, `UpdatePopGrowth`, `UpdateEmployment`) take
  about 70 ms of a 1.03 s day, and the year with 8.4% fewer pops ran no
  faster. Halving the pops would buy a few percent at most, at the price of
  changing who a building may hire.

## The USA of 1977, 2026-11-19: 1.15.1

The owner's game as the United States, which had spread through the New
World with heavy immigration, ran far slower than the 1931 bench. Their own
`dedicated_server.log` files (no harness attached) give the day at about 2 s
through 1974, 3.5–4 s from April 1975, and 8–10 s from 7 April 1976, a step
that shows in every frame type at once: the sub-ticks (hours 6, 12, 18) went
from about 0.15 s to about 1 s each and an ordinary day's hour 0 from 1 s to
4–5 s. Their save of 18 May 1977 holds 183 countries, 819 states and 153,538
pops (37,746 of them under 100 people); the United States owns 169 states and
66,208 pops holding 610 million people. That is 1.7 times the 1931 bench's
pops, with fewer countries. The harness on the save read the owner's figure:
8.1 s a day over its first 27 days. Data, scripts and the variant:
`/mnt/d/vic3te-data/perf-2026-11-19/` (`owner_logs/`, `scripts/owner_wall.py`,
`owner_frames.py`, `framecmp.py`, `sumw.py`, `variants/rsfix/`); sessions
`20261119T090040Z` (S1, the save as it is) and `20261119T092916Z` (S2, with
the fix below).

### Resettlement: one tick of 32 s a month

The owner runs 41 Settlement Authorities, each moving about 39,000 people a
month from the largest US states to South America. All of them walk in the
United States' monthly country pulse, inside one tick: 28 s of wall time in
the owner's own log on 12 March 1976 and 32 s in S1 on 5 June 1977 (the flat
script profiler on). The GUI profiler put the merged monthly country pulse at
58.8 s profiled over 20 days, 56.8 s of it `resettlement_on_actions.txt:14`.

Each Authority ran `ordered_scope_state` over its owner's states twice (drive
states, then the rest). The engine evaluates `limit` and `order_by` for every
candidate first, and both read `resettlement_state_eligible_pop`, a sum over
every pop of the state; the take's budget read it again, and the take walked
every pop of every source even after the destination's capacity was used,
which was the first source in nearly every case. So every Authority walked
all 66,000 pops four or five times: 41 × 5 × 66,000, about 13 million pop
tests a month in one tick.

The fix counts each source's eligible population once a month per program
(`rs_elig`) and counts again only after a take from it, the one step of the
pulse that changes a source's pops, and it stops visiting sources once the
capacity is used. In S2, with the fix loaded as an add-on mod over the same
save, the pulse of 5 June gave exactly what S1's did (83 `TE_RESETTLEMENT`
lines of 83 the same: the same sources, the same destinations, 1,569,901
people moved), the tick took 15 s against 32 s, and the next month's capture
put the whole monthly country pulse at 2.7 s profiled over 30 days against
58.8 over 20. Both of those ran with supply ship construction at Very High
(the next section), which slows every tick. With it at Very Low the tick of
5 June took about 23 s without the fix (session `20261119T164817Z`; the
resettlement lines run from its first second to its 23rd) and about 1 s with
it (`20261119T162248Z`): some 22 s a month, which is a lot once a day takes
1.5–2 s.

### The step of April 1976: supply ship construction at Very High

**Most of the day was the United States' supply ship construction, set to
Very High.** Setting it to Very Low took the same save from 6.3 s a day to
1.6–2.0 s.

- **The idle reload stayed fast.** The owner's autosave of 1 April 1976,
  loaded in the harness and left idle (session `20261119T160326Z`), ran at
  1–1.5 s a day to 28 April. The owner's own game had reached 7–8 s by
  15 April. So the step came from something the player did, not from the
  state the save held.
- **The saves show what.** Token 25536 in the binary gamestate is
  `supply_ship_construction_level`; its counts in the save of May 1977 match
  the plain-text save of September (79 `high`, 76 `very_low`, 18 `low`,
  one `very_high`, `medium` unwritten). No country had `very_high` on
  1 April 1976. The United States alone had it on 1 July 1976 and after. The
  save's `ship_construction_manager` grew from 0.17 MB to 1.31 MB in that
  quarter.
- **The backlog it built.** In 1977, 62,367 of the United States' 62,693
  ship construction points went to supply ships: 3,177 on maintenance and
  59,189 on 17,236 supply ships under construction, 11,753 of them part
  built. The pool held 373,732 supply ships. The save's
  `dead_supply_entries` lists 11,004 construction entries ended in one week.
  The next largest queue in the world was 182.
- **The test.** A variant `gui/timemanip.gui`, whose ship construction
  readout under the date runs `SetSupplyShipConstructionLevelVeryLow`, was
  clicked in session `20261119T162248Z`. The tooltip at once showed 0 points
  for the 17,236 under construction. The day fell from 6.3 s (session
  `20261119T161343Z`, the same save at Very High) to 1.6–2.0 s over the next
  26 days. The weekly tick went from 10–15 s to 5 s, an ordinary hour 0
  from 3.4–5 s to 0.6–0.9 s, and a sub-tick from about 1 s to 0.2 s.
- **The cost is outside the tick tasks.** The tick tasks summed to about 1 s
  a day in both settings (`ProgressSupplyShipConstructions` 11 ms a month).
  The time is spent elsewhere in the tick: the monthly resettlement tick
  with the fix took 15 s at Very High and 1 s at Very Low.
- **The tooltip makes it worse.** With the cursor left on that readout (its
  tooltip lists the supply ships under construction) the day was 17 s at
  Very High (one window of 12 days, the start of `20261119T162248Z`).
- **Script can't help.** No effect sets the level; it is the construction
  panel's buttons, `set_supply_ship_construction_level_command`, and no
  trigger reads the queue. The AI steps its own level down
  (`SUPPLY_SHIP_ALLOCATION_*`, `SUPPLY_SHIP_CONSTRUCTION_MAX_INCOME_FRACTION`
  in `00_ai.txt`); a player's stays where it was set.

| 1977 save, with the resettlement fix | Sub-tick rendering on | Off (`-disable_renderframeifneeded`) |
|---|---|---|
| Supply ships at Very High | 6.3 s a day (6.1–7.8 in S1 and S2) | 3.8 |
| Supply ships at Very Low | 1.6–2.0 | 1.3 |

Rendering off by launch argument (session `20261119T163959Z`) settles the
S1/S2 disagreement below: it halves a day that the backlog makes slow, and
saves about a third of what is left once the backlog is gone. Its cost is a
window that stops answering during a long tick. `GameStateTick.MinLockTime`
(console; default 1) at 50 and 200 made no difference beyond noise.

The tick tasks themselves, about 1 s a day (985 ms over S2's 129 days):
`HandleAutonomousInvestment` 254 ms (the United States' pool, in weekly
bursts of 3.5–9 s), `UpdateEmployment` 125, `RecalculateModifierNodes` 112,
`ProcessEconomicMigration` 76, `UpdatePopGrowth` 60, `UpdateStateTrades` 47,
`UpdateAI` 40. The tasks that walk pops (migration, growth, employment,
`MergeSmallPops`, `DissolveMicroPops`, the state pop caches) are about
300 ms, so a smaller pop count would buy little here. Paused, a frame takes
11.6 ms.

The night's knockouts, before the cause was known (S1 the save as it is, S2
with the resettlement fix; both at Very High):

| Window | Settings | s/day | Sub-tick s | Ordinary hour 0 s |
|---|---|---|---|---|
| S1 18 May – 13 Jun | as loaded | 7.76 | 1.05 | 5.1 |
| S1 28 Jun – 14 Jul | sub-tick rendering off | 7.94 | 1.17 | 2.0 |
| S1 22 Aug – 14 Oct | rendering off, `GUI.Draw` off | 5.33 | 0.65 | 2.7 |
| S2 18 May – 8 Jun | as loaded | 6.13 | 0.98 | 3.5 |
| S2 8 Jul – 23 Jul | `GUI.Draw`, `Draw.Map`, `Draw.MapObjects` off, rendering on | 11.68 | 2.23 | 5.8 |
| S2 23 Jul – 8 Aug | the same, rendering off | 2.82 | 0.51 | 1.2 |
| S2 8 Aug – 24 Aug | map back on | 3.28 | 0.57 | 1.3 |
| S2 24 Aug – 9 Sep | map objects back on | 4.07 | 0.72 | 1.2 |
| S2 9 Sep – 24 Sep | GUI back on: everything drawn, rendering off | 3.51 | 0.59 | 1.1 |

S1's rendering-off windows did not show the gain, probably because the
debug-mode map tooltip was up under the cursor there. With everything drawn
off and rendering on the tick was slowest of all: the tick gives way to every
frame, and frames with nothing to draw come fastest.

**Typing `gamestatetick.renderframeifneeded` to switch rendering back on in
a running session crashed the game** a minute later
(`EXCEPTION_ACCESS_VIOLATION` at RVA `0x3787360`, `crashes/victoria3_01261019_030122`),
after `GUI.Draw`, `Draw.Map` and `Draw.MapObjects` had been toggled off and on.
Switching it off once (S1) did not. Use `--game-arg disable_renderframeifneeded`
for an A/B, not the console twice. The crash left `CrashReporter.exe` up,
which kept the restore from finishing (#1905).

## The USA of 1992, 2026-11-20: 1.15.2

The owner's game of "The USA of 1977" above, played on through 15 years on
1.15.2 with `main` deployed, the Very High supply ship setting gone (no
country holds it in the save; a heuristic match of the token to its country
reads the United States at Very Low) and the resettlement fix (#1906) in.
Their own `dedicated_server.log` files, no harness attached, played at
speed 5 (the log's `Changing game speed to: 4` counts from 0): 6.5 s a day over 1977–1979, 3–4 s from late 1981, and 3.94 s over
1985.7–1992.2. Of that last stretch, by the frame each
gap starts at:

| Frame | Mean | Share of the day |
|---|---|---|
| Hour 0 of the weekly day | 9.3 s | 32% |
| Other hours 0 | 1.17 s | 25% |
| Sub-ticks (hours 6, 12, 18) | 0.52 s | 40% |
| Hour 0 of the 1st | 4.1 s | 3% |

The weekly day's hour 12, inside the sub-ticks, read 1–2.75 s a month over
1977–1982 and 3–4 s in most months from 1983 (1–2.75 s again over
1986.4–1987.11 and 1989.7–9, 5–6 s in a few); the other hours 12 read
0.35–1.15 s until mid-1981 and about 0.2 s after. The save
(`autosave_exit.v3`, 15 Feb 1992) holds 167 countries, 809 states and
196,550 pops (189, 826 and 168,657 in May 1977); the United States owns 178
states holding 565 million people, and its market 215 states and 80,732 pops
(204 and 76,617 in 1977).

The harness on the save, `--playset current`, two 30-day windows from
15 February (sessions `20261120T095304Z`, rendering on, and
`20261120T100803Z`, rendering off), read the owner's figure: 3.23 and 3.73 s a
day with sub-tick rendering on. Data, scripts and variants:
`/mnt/d/vic3te-data/perf-2026-11-20/` (`owner_logs/`, `runs/<name>/`,
`variants/<name>/`; `scripts/outside.py` splits each frame into its tick tasks
and the rest, `scripts/tasks_by_kind.py` the tasks by frame kind,
`scripts/wk12.py` the owner's weekly hour 12 by month).

### Where the day goes

| Per day | Rendering on | Off (`-disable_renderframeifneeded`) |
|---|---|---|
| Wall | 3.48 s | 2.27 s |
| Tick tasks | 1.43 s | 1.50 s |
| Outside the tasks | 2.05 s | 0.78 s |
| An ordinary hour 0: wall, of it tasks | 1.10 s, 0.29 | 0.54 s, 0.32 |
| A sub-tick other than the weekly hour 12 | 0.31 s, 0.04 | 0.17 s, 0.06 |
| The weekly hour 0 | 8.0 s, 4.0 | 5.6 s, 4.4 |
| The weekly hour 12 | 3.5 s, 3.4 | 3.7 s, 3.4 |

The first three rows are over both windows of each session. The per-frame
rows are `outside.py`'s means, which leave out every gap that spans a
harness pause; in S1 that dropped 4 of its 7 weekly hours 0, one of its two
1sts and one of its 9 weekly hours 12, so read those rows as means per frame,
not as a day's sum.

- **Sub-tick rendering is the largest single cost**: 3.2–3.7 s a day on,
  2.1–2.4 off, and the time it adds is all outside the tick tasks. It is the
  owner's launch option, as it was in 1931 and 1977; the mod can't set it.
- **The weekly economic migration pass**, `ProcessEconomicMigration` at hour
  12 of the weekly day, is the largest tick task: 3.2 s a week, about a
  fifth of a rendering-off day. Below.
- **The weekly hour 0** holds 4.1–4.7 s of tasks. Over every weekly hour 0
  of both windows (rendering off, 8 frames; the 1977 save, 6) the
  investment pass reads 1.42 s against 0.96 (the played country's pool, as
  in "Where the day goes"; 0.25–3.1 s from week to week) and
  `UpdateStateTrades` 1.20 s against 0.28, while `UpdateEmployment` (0.77
  against 0.74) and `UpdateWorldMarket` (0.27 against 0.29, alternating
  about 130 and 400 ms) held still. The two that grew are engine work that
  grows with the economy; nothing in script reaches them.
- **An ordinary hour 0** (rendering off): 0.32 s of tasks
  (`RecalculateModifierNodes` 0.145 s, `UpdatePopGrowth` 0.053) and 0.23 s
  outside them.
- **The mod's own script** is about 0.1 s a day. The call graph over 16 April
  to 1 May (15 days, 60 ticks, profiled) put the merged yearly state pulse
  (labelled `te_unemployment_on_actions.txt:8`) at 1,420 ms, the merged
  monthly country pulse (`wonder_events_on_actions.txt:1`) at 1,132 ms, the
  journal-entry pulses at 675 ms, the global monthly pulse
  (`un_on_actions.txt:40`) at 613 ms and the monthly state pulse
  (`un_mission_on_actions.txt:25`) at 249 ms; with the other mod roots in the
  top 27 (`zz_te_party_join_weights.txt:3915` 350 ms,
  `new_ideological_movements.txt:400` 281, `te_construction_market_site.txt:175`
  233) that is 4,953 ms, 330 ms a day profiled, 0.09–0.13 s unprofiled at
  the profiler's 2.6–3.5× (3–4% of the day). "Where the day goes" put all of
  it at most a tenth in 1931; pulse trimming can't move this save either.
- **The heaviest single script entry is vanilla's**: the alert
  `low_expected_sol_in_state` (`00_alert_types.txt:1034`), 446 µs a call over
  each of the player's states: 93 ms a day in the call graph and in the flat
  dump alike, about 85 ms unprofiled with rendering on and 46 with it off
  (12,460 calls in 60 days against 7,120 in 62.5: it follows drawn frames,
  not ticks). The player can switch that alert off.

### The weekly migration pass

`ProcessEconomicMigration` runs on one frame a week, hour 12 of the weekly
day, and costs almost nothing on the others. On the 1992 save it takes
3.2 s; on the 1977 save loaded with the same build
(`20261120T104423Z`) 250–300 ms. The first week after any load costs more
(2.3 s in 1977, 4.0 s in 1992), so every figure here is from second windows.

| Run (rendering off, second window: about a month, 21 days for the 1977 save) | Weekly frame | Snapshot |
|---|---|---|
| 1992 as saved | 3,179 ms (3,247 rendering on) | `20261120T100803Z` |
| `MIGRATION_MIN_STATE_POPS` 20,000 → 1e9 (no market emigration; a bound) | 64 ms | `20261120T101540Z` |
| `MIGRATION_MAX_PER_STATE_INFRASTRUCTURE` 5 → 0 and `…_UNEMPLOYMENT_ORIGIN_FRACTION` 0.05 → 0 (caps at the 500 base) | 1,763 ms | `20261120T102217Z` |
| `MARKET_MIGRATION_STATE_ATTRACTION_FRACTION` 0.75 → 0.9 (fewer states receive) | 989 ms | `20261120T113432Z` |
| California and Santa Cruz given `state_migration_pull_mult = -0.95` (a setup) | 3,993 ms | `20261120T111303Z` |
| The 1977 save, today's build | 271 ms | `20261120T104423Z` |

Wall time follows the pass but not cleanly, since the windows hold
different numbers of weekly days (the hub run's five, the others four):
2.41 s a day as saved, 2.13 with no market emigration, 2.27 with the caps at
base, 2.32 at 0.9.

So the cost is market migration (not mass migration: 7 mass-migration
targets in the save, 8 in 1977). It falls with fewer people moving (the caps
at base, −45%) and with fewer states receiving them (a receiver needing 90%
of the best state's pull instead of 75%, −69%). What changed between the
saves is not the market's size (5% more states and pops) nor unemployment,
which fell (the census's slack count across the United States' states: 26.9
million in 1977, 0.7 million in 1992). The save's per-state migration
statistics (`#21648`, inferred as `pop_migration_statistics`: two figures
and two lists of states) show the US market's week of flows 1.66 times
1977's and its pairs of states 1.59 times (world-wide 1.84 and 1.18), and
one state, California, taking migrants from 157 states (no state took them
from more than 21 in 1977) and sending its own to Santa Cruz, which takes
them from 42. Those two are not the cost: given −95% pull the pass got
dearer, 3.2 → 4.0 s (the pulls after the setup were not read, nor where the
flows went). Their pulls are not far ahead either (California 95, New York
97, Texas 92, Illinois 90, Santa Cruz 77, read in game before the setup).

A reading that fits every run, not tested directly: the pass's work goes as
the pops of the emitting states times the states that receive. With jobs
everywhere in 1992 the pulls bunch near the top, so many states sit within
three quarters of the best and receive; the 0.9 threshold cuts that number;
the hubs, at −95%, would turn from receivers to emitters. Nothing the
mod adds explains it: the same build runs the 1977 save's pass at a twelfth
of the cost, and the mod's migration terms on the hubs are small
(California's climate amenity +7% and crowding −17%; Santa Cruz's +100% is
vanilla's `amazon_migration`, from the Exploiting the Amazon entry the
United States runs).

What a mod can do is change the defines, which changes who moves where: the
0.9 threshold saves about 0.31 s a day of a 2.4 s day (rendering off) and
sends migrants only to the very best states; the caps at their base save
0.20 s and slow every state's migration. Both are gameplay changes, the
owner's to weigh against the migration they want; nothing is proposed here.

### The Timeline Extended window, again (#1760)

Paused, vsync off (console `vsync`), `measure_frame_time` over 8 s, the
window opened by a probe widget (`variants/openwin`, `openwide`):

| Window | Docked | Full-screen layout |
|---|---|---|
| Shut | 6.0–6.6 ms | 5.8–6.5 ms |
| Open on Nation, as on `main` | 20.5–20.7 ms | 19.7–19.9 ms |
| Rows' text on `GetFormattedValueFor` (`nat_fmt`; full-screen: the fix branch's text and tooltips, `fix_wide`) | 13.9 ms | 11.9–12.1 ms |
| `nat_fmt`, and all 136 generated counts a constant 1 (every row shown) | 14.9–15.1 ms | |
| The fix's rows, the overview panel taken out (`nat_noov`) | 13.8–14.1 ms | |
| The fix's rows, the five sections taken out, the overview kept (`nat_nosec`) | 8.05–8.45 ms | |
| The fix's rows, every timed-modifier list emptied (`nat_nolists`) | 10.9–11.0 ms | |

So the rows' breakdown accessor is about half the tab's cost (47% docked,
57% full-screen). The fix (the figure in the text, the breakdown in the
row's tooltip) is #1760's pull request. Of the 7.7 ms left docked:

- **The overview** costs nothing measurable, and the window with only the
  overview in it is about 2 ms over shut.
- **The five sections** are the other 5.5–6 ms.
- **About 3 ms of that is their six timed-modifier lists** (`te_nation_list`,
  the modifiers behind Judicial Independence, the Algorithmic Mandate,
  Wealth Concentration, construction cost, private construction and global
  tech). Each walks every timed modifier the country holds, 61 for the
  United States in 1992, and runs its name filter (one to four `Localize`
  and string compares, gotchas #40 and #42) on each, every frame: about 370
  items. A count gate, the pattern Where These Come From's lists use,
  would save little here: five of the six rows hold one of their modifiers
  on this save. What would save it changes what the rows show, so it is the
  owner's call (open item 16).
- **The rest, about 2.7 ms,** is the sections' own rows, bars and generated
  rows. The constant counts did not bring the frame down, but they also
  showed every row, so the 107 counts the rows', groups' and sections'
  `visible` checks read (84 of them the rows') are not ruled out.

The last three rows used the fix branch's text and tooltip keys, docked;
the console covered the docked window in their screenshots, so what drew is
inferred from the frame times (open above shut in each) and from their
error logs, the same 1,156 lines each. Each row is one session
(`20261120T102929Z`, `20261120T103400Z`, `20261120T103950Z`,
`20261120T110308Z`, `20261120T110737Z`, `20261120T114406Z`,
`20261120T114842Z`, `20261120T115423Z`).

## The history charts, 2026-11-24: 1.15.2

The owner's save of December 2032, 20 years of monthly history stored, the
Timeline Extended window's Full Screen frame at 3840x2160, the engine's own
frame counter, the Banking tab open:

| Banking's History section | Frames a second |
|---|---|
| Closed | 75 |
| Open, 20 Years (the default: every stored sample) | 16 |
| Open, 5 Years | 18 |
| Open, 1 Year | 23 |

The script profiler, paused, put little script on the tab (its top root 78 ms
in 13.7 s), so the cost was the GUI's own (`gui_modding_guide.md` gotcha #42).
The same section in the window's side panel, scrolled out of sight, cost the
same; Demographics' eight charts drew 28.

**Why the short ranges cost nearly as much.** Every plot read the whole
store, up to 240 containers, and cut the range per item: at 1 Year each of
the seven charts drawn built 240 items to show 12, and each evaluated its
datacontext and an age test. From the three figures, a rough split (frame
time over the closed section's 13.3 ms, against items and bindings) gives
about 13 µs an item, shown or not, and 2 µs a binding: 1 Year was 30 ms of
1,680 items and about 3,900 bindings, 20 Years 49 ms of the same items and
about 13,700.

**The change** (`gui/charts-perf`). A shorter range's plot reads only the
store's newest samples, `DataModelLast( <list>, '(int32)12' )` or 60, and
keeps the age test on each; the 20-year plot reads the whole store and tests
nothing; Banking's pips are one test a month instead of two
(`history_charts.md`, "The chart"). Bindings a shown bar evaluates, before
and after on the 20-year plot (the short ranges add the age test back):

| Bar | Before | After |
|---|---|---|
| Banking's cycle value (`te_history_bar_cycle_phase`, six band tests, with pips) | 13 | 11 |
| Banking's momentum (`te_history_bar_signed`, with pips) | 9 | 7 |
| Banking's other five (`te_history_bar_unsigned`, with pips) | 7 | 5 |
| A chart with no pips (`te_history_bar_unsigned`) | 5 | 4 |
| Colonial drift (`te_history_bar_signed`, no pips) | 7 | 6 |

On the split above the Banking tab would draw about 60 frames a second at 1
Year (84 items), about 40 at 5 Years (420) and about 18 at 20 Years (still
1,680 items); the 20-year view stays costly because its cost is the items.

**Seen in game, 2026-11-24** (a copy of the same save, the same frame and
counter, the branch loaded with that night's other branches): `DataModelLast`
over a script list draws, 12 bars to the right edge at 1 Year, 60 at 5
Years, every month at 20, the pips on the same charts.

**A store shorter than the range** (2026-11-24, the same evening, a fresh
game as Great Britain). `DataModelLast` asked for more than a list holds
logs `Trying to reshape data model with negative offset -60` every frame for
every chart: 300 to 430 error lines a second with Banking's History open in
January 1836, and the tab took over ten seconds to open under the QA harness
(with History collapsed it opened at once). Each shorter range now has a
second plot that reads the whole store, shown while the store holds less
than the range (`history_charts.md`, "The chart"); a store that short costs
little to read whole. Seen in March 1836 with two samples: two bars at the
right edge at each range, and no error line.

| Banking's History section | Before | After |
|---|---|---|
| Open, 1 Year | 23 | 74 |
| Open, 5 Years | 18 | 47 |
| Open, 20 Years | 16 | 24 |

The 1-year and 5-year figures are this change's. Part of the 20-year gain
is another branch's, loaded in the same session: the International
Arrangements rows stopped evaluating a custom loc per member each frame.
**The default became 5 years** (`DEFAULT_RANGE` in
`gen_te_history_charts.py`, branch `gui/charts-default-5y`, the owner's to
take or leave): a History section is open by default and costs the same
scrolled out of sight, so the view it opens on is what every visit pays.

## The USA of 2024: the Deep-Sea Mine gate, 2026-11-22: 1.15.2

The owner's game of "The USA of 1992" above, played on to 2024 with `main`
deployed (143596dff). Their report: the game got much slower once the
Deep-Sea Mine came in and started building. Their own `dedicated_server.log`,
no harness attached: the weekly day's hour 0 took 9 s on 27 May 2024, at
least 343 s on 3 June (they paused then; the next hour ran at 459 s) and
564 s on 10 June. The save (`autosave_exit.v3`, 11 June 2024) holds the
reason. The USA had 83 seabed licences to spare, its first unused claims,
from the sharing at the start of June. Its government queue held 2,269
Deep-Sea Mine levels in three states (New York 1,000, Hawaii 850, Nunavut
419), none built and all recorded. No other country had a mine queued, and
no private queue held one.

**What took the week.** The harness on the save (`--playset current`, 11 to
19 June, the script profiler on; each variant an `--add-mod` folder of the
changed files at the mod's paths, kept in `D:\vic3te-data\perf-2026-11-22\variants`).
The 17 June weekly day was one frame of 781 s, and 777 s of it was the
engine's private investment pass, `HandleAutonomousInvestment`. In the
script profiler that week, the mine's `possible` (`03_zz_te_mines.txt:438`)
was read 306,315 times for 779 s, 2.54 ms a read. The next-costliest script
took 2.6 s. The pass reads every unlocked building's `possible` in every
state, many times a week: the Chemical Plant's 91,532 times. Until the
USA held unused claims, the gate's first test (a sum of five variables)
failed. From June it went on to the room, `te_seabed_room`, which walked
every building of every coastal state of the owner, twice a read, and more
under Build only on local claims. The profiler adds to the cost: the
owner's own 10 June ran 564 s.

| Variant | Session | Weekly-day frame | `HandleAutonomousInvestment` | Mine `possible`: reads, time |
|---|---|---|---|---|
| `main` | `20261122T235340Z` | 780.9 s | 777.2 s | 306,315, 778.8 s |
| The room by `b:`, walking only states with a mine | `20261123T001911Z` | 123.2 s | 119.6 s | 306,317, 116.7 s |
| That, and `can_build_private` false | `20261123T003209Z` | 124.8 s | 121.2 s | 306,316, 118.1 s |
| That, with the gate in `can_build_government` (shipped) | `20261123T004937Z` | 7.9 s | 4.2 s | 306,316, 0.04 s |

The `b:` lookup makes each read cheaper (0.38 ms) but leaves 306,000
of them. Forbidding private building changed nothing: the pass reads
`possible` before `can_build_private`. With the gate in
`can_build_government`, which the pass doesn't read, the gate was read
once in the eight days, for 1.2 ms. The week is back to the 8 s a weekly
day took in 1992. The `b:` forms read the same as the walks they replace,
in game on the save (session `20261122T232347Z`, with the old forms
renamed beside them): room 83 both ways, every basin's local room equal,
New York's mine 1,000 levels after queued and 0 built.

**What changed.** `building_ocean_mine`'s `possible` is `is_coastal = yes`
alone. The licence gate is its `can_build_government`, as vanilla's
Skyscraper keeps its site rule. With the Global Commons rule on,
`can_build_private` is false, so investors, who never read the gate, can't
build past the licences (the owner's suggestion). `te_seabed_state_levels`,
`te_seabed_state_built_levels` and the gate's under-construction tests read
the state's mine by `b:building_ocean_mine`. The room walks read only
coastal states that have one: the national walk by `exists`, the basin walks
by `te_seabed_state_counts_locally`, which also keeps a state holding records
but no mine. `test_seabed_script.py`'s `GateTest` holds all of it.

**Harness notes.** A `read` sent while the weekly day's tick ran hung the
game ("Random should not be acquired by any other thread", then no answer),
and the session had to be stopped. The runs above waited for the tick to end before
sending any verb.

**Left open.** At room 0 the production lens hides the mine, since it hides
any building whose `can_build_government` fails. Whether the state's own
building list still shows it grey, with the licence lines, is on the
play-test list (`docs/testing/global-commons-playtest.md`, item 2). So is
whether AI governments still build mines; in this save no AI country had one
queued.

**The other building gates, 2026-11-22.** A review of every mod building's
`potential`, `possible`, `can_build_private` and `ai_value`, against the 51
profiles on the backup drive, found no other one costly yet, and several
that would be once a game reached them. Their walks of a state's buildings
became `b:` lookups: the Solar Power Receiver's and the antimatter
buildings' slot counts, the Extraplanetary Base's and Resort Colony's
queued levels (read from their `can_build_private`), the Grid Transfer
Station's test, the wonders' uniqueness tests, and the company flagships'
one-site rule, now two shared triggers in place of 942 inline walks. The
slot counts still walk the owner's states, one lookup a state, from a
private type's `possible`: moving them to `can_build_government`, as the
Deep-Sea Mine's gate was, is #1964. `building_gate_walk_audit.py` now flags
any walk these blocks reach. Done 2026-11-23: each `possible` keeps one
read of the slot modifier, which the count implies, and the count is in
`can_build_government`, so the receivers and antimatter buildings leave
the lens only while every free slot is queued.

## The USA of 2030: the ship construction readout, 2026-11-23: 1.15.2

The owner's game of "The USA of 2024" above, played on to 2030. Their own
play of September 2029 to March 2030 (speed 5, `-disable_renderframeifneeded`,
no panels open) took 21–30 s a week, about half of it outside the tick
tasks, and neither zooming in nor lowering the graphics quality moved it
much.

**The harness reproduces it.** Every session loaded the owner's
`autosave_exit.v3` of 9 April 2030 as the USA (`--playset current`,
`--game-arg disable_renderframeifneeded`, `--unresponsive-s 120`), ran
`advance 35` at speed 5 and was timed from 10 April to 13 May (34 days) with
pauses taken out (`wallday.py`). Runs vary by about ±1 s a week. Each variant
was an `--add-mod` folder of the changed files at their paths.

| Run | Session | Seconds a week |
|---|---|---|
| Baseline | `20261124T013318Z` | 23.4 |
| Script profiler never enabled | `20261124T014525Z` | 23.4 |
| `GUI.Draw`, `Draw.Map`, `Draw.MapObjects` off (second half of the baseline session) | `20261124T013318Z` | no change in any frame kind |
| `AUTONOMOUS_INVESTMENT_CONSTRUCTION_ENABLED = no` | `20261124T015209Z` | 23.2 |
| Every mod `gui/` file replaced by vanilla's, or emptied | `20261124T015802Z` | 24.2 |
| Every mod `common/on_actions/` file emptied | `20261124T020443Z` | 24.4 |
| The top bar's three supply ship calls replaced by constants | `20261124T045427Z` | 25.1 |
| `ingame_hud` emptied except `timemanip` (no top bar, outliner, lens bar, side bar) | `20261124T052206Z` | 24.2 |
| **`timemanip.gui`'s `text = "SHIP_CONSTRUCTION_VALUE"` replaced by `raw_text = "#v 0#!/0"`** | `20261124T053316Z` | **12.4** |

A first try of the last row (`20261124T052829Z`) read 12.8, but lost the
window's focus partway (#1963). `ingame_hud` emptied whole stalled at once:
the harness pauses with Space, which only `timemanip`'s speed buttons bind.

| Frame kind | Baseline runs | Readout replaced |
|---|---|---|
| Sub-tick | 0.26–0.45 s | 0.11 s |
| Hour 0 of an ordinary day | 0.93–1.48 s | 0.39 s |
| Hour 0 of the weekly day | 7–9.3 s | 6.7 s (tasks 6.6) |
| Weekly hour 12 | 1.5–3.0 s | 2.0 s |
| Time outside the tick tasks, a day | about 1.9 s | about 0.35 s |

**What the time was.** The tick tasks were 1.4 of the 3.3 s a day. The rest
was serial work on the main thread, found by sampling the game process from
the Windows side (read-only; tools below):

- Per-thread CPU (`threadcpu.py`): the main thread, the process's oldest,
  ran at 50–90% of a core between weekly bursts while every other thread
  idled; in the weekly burst 13–20 cores ran and the main thread waited.
- Its instruction pointer (`stacksample.py`, the thread suspended for
  microseconds every 4 ms): 80% of sub-tick samples in `victoria3.exe`.
  Functions are named by the `.pdata` table and the strings the code
  references (`name_rvas.py`, using `crash_stack_strings.exe_strings_near`).
  About 60% of sub-tick and 40–46% of hour-0 samples sat under the GUI's
  data-call evaluator (`pdx_data_callstack.cpp`), in a country routine that
  calls the code holding `SHIP_CONSTRUCTION_MAINTENANCE_DEMAND_DESC` and
  `SUPPLY_SHIP_CONSTRUCTION_MAINTENANCE_DEMAND_DESC`.
- The text its stack points at (`stackstrings.py`, 32 KB of stack read while
  suspended, each slot followed to text and through one more pointer): on
  100% of those samples, `[Country.GetShipConstruction|0]`,
  `GetShipConstructionUsage` and `SHIP_CONSTRUCTION_VALUE_WITHOUT_ICON`. That
  is the readout under the date: `SHIP_CONSTRUCTION_VALUE` in vanilla
  `gui/timemanip.gui` (line 487, inside the construction widget with
  `max_update_rate = 8`), `#v [Country.GetShipConstructionUsage|0]#!/[Country.GetShipConstruction|0]`.
  The mod doesn't override the file.

Earlier knockouts missed it because drawing off leaves the GUI's updates
running, and the vanilla-GUI swap keeps vanilla's `timemanip.gui`. Paused, a
frame took 8.4 ms; running, 27–31 ms on average. This is the readout whose
tooltip made the 1977 Very High backlog worse ("The step of April 1976"
above); here the readout alone costs about 1.5 s of every game day. Not yet
split: which of the two calls costs it, and whether it scales with the
supply ships (the owner's guess) or the fleet.

**The week once it is gone:** 12.4 s, of which the weekly hour 0 is 6.7 s
(`HandleAutonomousInvestment` 3.05 s, `UpdateStateTrades` 2.1 s,
`UpdateEmployment` 0.6 s), the weekly hour 12 2.0 s
(`ProcessEconomicMigration` 1.7 s), and every other frame about 3.7 s
together.

**The fix is open (#1984).** The owner's two ideas: supply ships that cost
ten times as much while every requirement for them is a tenth (always, from
the start of a game), which shrinks whatever the routine walks and has other
effects they want; or a readout that doesn't run live (cached, or moved to
the tooltip). Either way the mod overrides `timemanip.gui` or changes the
supply ship defines. The weekly cap per ship, not the cost, sets how many
supply ships are in progress, so a quick fix went first (2026-11-24): Naval
Convoy Defense (era 6) raises the cap from 5 to the cost, 25, so a ship is
built in a week and a fifth as many are in progress. It is not timed yet
(`docs/testing/perf-fixes-playtest.md`). The rescale, if that isn't enough, is
`docs/superpowers/plans/2026-11-24-supply-ship-scale.md`.

Data: `/mnt/d/vic3te-data/perf-2026-11-23/` (`variants/<name>/`,
`runs/<name>/` with each session's split and samples, `run_variant.sh` for
one session, `wallday.py`, `runsplit.py`; the samplers, run with the Windows
`python.exe`, and their readers in `tools/`). The write-up for the owner,
with the super-building question it began from: claude.ai artifact
`VZ94FSnuTPtDo1kPJB2nCK`.

## The Budget Breakdown tab, 2026-11-24: 1.15.2

The owner's game of December 2032 as the Imperial Union of America,
3840x2160. With the Budget Breakdown tab open the game drew 16 frames a
second in the Timeline Extended window's Full Screen frame; in the side panel
under the script profiler (the game paused, so every sample is a binding's
script) 137 frames in 13.9 s, 10 a second, against 47 for the Nation tab
under the same profiler. Inclusive times, lines of the deployed build
(`8d5f81bca`):

| Root | ms | What it was |
|---|---|---|
| `te_budget_values.txt:119`, `:17`, `:111`, `:57` | 642, 436, 349, 336 | The four building sums (naval support, Government Administration, army support, the Space Program): an `every_scope_building` over every building of the country, once a frame each |
| `te_budget_generated_values.txt:1832` | 187 | General Administration's `allocated_institutions` (thirty institutions), recomputed by each value that read Administration |
| `te_budget_generated_values.txt:4902`, `:2011` | 112, 81 | Other Expenses (the total less every category), recomputed by its positive, active, visible, share and amount values |
| `te_budget_generated_values.txt:4940`, `:4953`, `:3234`, `:2134` | 42 to 64 each | the positive total and the Administration group's positives, re-summing the same |

The section bound every amount once a frame already (`row_<key>`), but each
row's positive, active, share and amount values computed it again from the
getters, so Other Expenses and Administration ran about seven times a frame.

**What changed** (branch `gui/budget-perf`; no figure, row, slice, hover or
button changes):

- **The building sums look up, not walk.** Each walks the country's states
  and reads the one building of its type with `b:<type>`
  (`te_budget_values.txt`); a state has at most one, so the sum is the
  walk's. `test_budget_breakdown.BuildingLookupTest` holds each list of
  types to every member of the building group the walk selected.
- **Each amount is computed once a frame.** A leaf's positive and active
  values, every share and every row's amount read the bound `row_<key>` or
  `positive_<side>_<key>`; `PerFrameWorkTest` fails on a per-row value that
  names an amount.
- **A row tests one value per slot** (`_in_slot`), where the GUI read three
  script values (visibility, rank, slot); a row under a closed group gets no
  rank.
- **A pie's cumulative value** adds its preceding siblings' bound positives
  at each level, where it re-summed every slice before it (a quadratic
  2,556 slices a frame on the expense side).
- **What a closed group hides is not read.** A group's pies and rows sit
  under one container shown only while it is open (`gui_modding_guide.md`
  gotcha #42), and the slots past the top-level rows wait behind one test.

Counted offline on the test fixture's expense side with every group closed
(`count_frame.py` in the data folder below): 1,808 script values the GUI asks
a frame became 463, and about 56,800 script operations about 6,000, before
the building sums, which went from one step per building of the country to
one per state and type. Left: the amounts themselves (Other Expenses re-sums
every category, Administration its thirty institutions) are still computed
in full once a frame in the section's list context; binding the leaves in a
context of their own and the groups and Other from them would cut that too.
Nothing is stored at a pulse: the panel's figures stay live.

**Measured again in the running game, the same day** (the same save, this
branch loaded from a side mod at launch). Every figure and both pies read as
before. The script profiler, the tab open in the Full Screen frame: 6,274
samples and 246 frames in 13.5 s, against 16,139 samples and 137 frames in
13.9 s; the four building walks are gone from the roots, the heaviest root is
65 ms (`te_budget_values.txt:28`), and the first fourteen sum to about 1.5 ms
a frame, from about 17.

**The frame counter moved much less than the script: 19 frames a second,
from 16, and what is left is the engine's, not the mod's.** A side mod's copy
of the generated file with a client-side switch on each part showed where the
frame goes (the Full Screen frame; the Nation tab in the same window draws at
76):

| Shown | frames a second |
|---|---|
| Both pies and both lists | 18 to 19 |
| The pies only | 20 |
| The lists only | 19 |
| Neither (the two headers and their totals) | 20 |
| Nothing under the headers, the sections' root contexts still bound | 23 |
| Vanilla's own Budget panel, Overview tab | 16 |

So the pies and lists together cost about 9 ms of the tab's 53 ms a frame,
and about 30 ms is spent with nothing drawn at all: the two sections' root
`datacontext`, which reads the engine's budget figures once a frame (twelve
getters for income, about thirty for expenses: `PredictWeeklyIncome`,
`PredictConsumptionTaxes`, `PredictDividendsTaxes`, `PredictTariffs`,
`PredictGovernmentWagesExpenses`, `PredictMilitaryWagesExpenses`,
`PredictTotalArmyExpenses` and the rest). Vanilla's Budget overview reads the
same kind of figure a line and pays 49 ms a frame for it on this economy. The
tab cannot read them less often (a binding is evaluated every frame) and
script cannot read them at all, so a weekly copy in variables is not
available. What could still help, not tried: finding which getters carry the
cost (a switch on each, as above; the `Predict…` ones are the likely ones)
and showing those figures on a hover or behind a "Show" button instead of
in the open tab.

Data: `/mnt/d/vic3te-data/gui-eval-2026-11-24/` (`perf/side_roots_budget_breakdown.png`, `perf/after_roots_budget_breakdown.png`, `perf/bud_experiment.png`,
`shots/before/fs_budget_breakdown.png`, `agents/budget-perf/count_frame.py`).

## The Grand Monuments tab, 2026-11-24: 1.15.2

The owner's game of December 2032 as the Imperial Union of America: 27
monuments of its own and 24 trophies, 3840x2160. With the Grand Monuments
tab open the game drew 16 frames a second in the Timeline Extended window's
Full Screen frame and about 10 in its side panel with the script profiler
on, against 120 for a light tab and 47 for the Nation tab under the same
profiler. The profiler (`Script.Profiling.Start` / `Stop`, the game paused,
so every sample is a binding's script) over 14.7 s and 116 frames, inclusive
times:

| Root | ms | What it was |
|---|---|---|
| `gm_values.txt:322`, `:321` | 511, 82 | `gm_disp_picture_code`: a has_variable, asked by each of `gm_picture`'s 238 icons (one per picture code) in each row |
| `gm_trophy_values.txt:328`, `:327` | 505, 161 | `gm_tr_disp_picture_code`, the same in `gm_tr_picture`, for the trophies and the monuments beside another |
| `gm_monument_values.txt:199`, `:200` | 479, 105 | `gm_state_primary_grandeur`, from each row's detail line and the frame |
| `gm_values.txt:311`–`:315` | about 150 each | `gm_disp_frame_tier`: five ifs on `gm_state_grandeur`, asked by each of the five frame icons |
| `gm_monument_values.txt:54`, `:55` | 259, 51 | `gm_state_primary_levels`' `value = gm_state_built_levels`, the fallback computed (with the secondaries' list) before the record overrode it |
| `gm_trophy_values.txt:339`, `:338` | 240, 73 | `gm_tr_disp_trophy_picture_code`, asked by each of `gm_tr_trophy_picture`'s 158 icons in each trophy row |
| `gm_trophy_sguis.txt:19`, `gm_monument_sguis.txt:15` | 181, 112 | Carry It Off's `is_shown`, twice a row, which read every trophy in the world before the route |
| `gm_values.txt:2017`, `:1813`, `:1864`, `:1872`, `:1935` | 51 to 113 each | the overview's counts, each an `every_scope_state`, about sixteen reads a frame |

**What changed** (branch `gui/gm-perf`; no figure, picture or button
changes):

- **The pictures are grouped.** The three picture types put their icons in
  group widgets by code range (a hundred codes a group below 1,000,000,
  twenty from there: `picture_group` in `test_grand_monument_registry.py`),
  each group shown on the stored variable's range, inside one wrapper shown
  while the display value is above its floor, so the variable is read only
  once it is set. A row reads its display value twice and the variable about
  forty times, where it asked a script value 238 times (a trophy's row 396).
  This rests on a widget in a hidden container not being evaluated
  (`gui_modding_guide.md` gotcha #42, seen in game 2026-10-18).
- **The fallbacks are lazy.** `gm_state_primary_levels`,
  `gm_state_primary_start` and `gm_mon_start` compute their fallback in an
  `else`, only without the record, where `value = <fallback>` before the
  `if` computed it on every call.
- **The frame tier reads the grandeur once** and saves it
  (`save_temporary_value_as`, vanilla's form in `command_values.txt`).
- **The cheap test first.** `gm_state_tr_can_take` tests the route before
  `gm_state_tr_takeable`, and `gm_mon_tr_can_take` the occupation before the
  rest, so a monument in our own incorporated state is ruled out at a line or
  two; `gm_mon_disp_clearable` counts the state's monuments before comparing
  them.

What each view of Our Monuments and Trophies costs now: Full draws each row's
picture (two display values, about forty variable reads), its frame (five
frame tiers, one grandeur each), its status (`gm_status_code` about eight
times a row with the sections' own `visible`s) and its controls' values;
Short draws no picture and no frame, only the line's values and Carry It
Off's now cheap `is_shown`; Collapsed draws no rows. Full still draws every
row; the Demographics tab's Show All (`te_demog_town_rows`) would cap it, and
which view opens is the owner's call.

**Left:** the overview's counts walk every state of the country, about
sixteen walks a frame (roughly 400 ms of the 14.7 s). Iterating `gm_states`
instead would agree with the rows but lag a conquest or a new site by up to a
month, as the rows do; storing them in the country refresh would lag a site
finishing. Neither is done. Not yet remeasured in game.

**Stored descriptive figures, branch `gui/gm-overview-perf` (from #2016; PR
#2033):** the Monuments cell and Our Monuments' count and grandeur read
country variables `gm_ov_store` writes at the end of every
`gm_country_refresh` and at the moments listed in `gm_values.txt`'s header to
them, so they lag only what none of those moments catches, and a month's
ageing of the grandeur (`TE_SELF_CHECK gm_overview_stored` reads whether
anything does). The calls to action stay as they were, every state walked
each frame: the owner's rule (2026-11-24) is that they should not be stale,
and a first version that counted the rows' own list instead lagged a site
queued or gained until a hook or the month listed it. So the tab walks every
state up to 19 times a frame with every line drawn (37 before; the In-game
check after the merge of #2003 put `gm_values.txt:2023`, `:1819`, `:1870`,
`:1878`, `:1942`, `:1941` at the top, 231 to 106 ms each in 13.3 s).

## Measurements, 2026-10-03: 2072

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

The GUI profiler gives no clean before/after for the monthly pulse. The
"before" capture with the most detail came from the session where the
company buildings failed to load (see the doubled BOM below). Its
`remove_invalid_buildings` cost 985 ms, inflated by about 1,800
`remove_building` errors a minute. In this PR's capture that callee is gone
from the top of the merged monthly pulse. The first capture of the original
code and this PR's capture also disagree in ways nothing here explains; see
open item 2.

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
- **Cultural Hegemony modifiers.** The CH effect and the foreign benchmark use
  a variable set in the monthly pulse as their `multiplier`
  (`root.var:ch_effect_mult_cached`, `var:ch_benchmark_applied`), not
  script values that compute the world's cultural pull. That's one fewer
  benchmark computation per pulse, and no exposure if the engine
  re-evaluates multipliers later.
- **Suit portraits.** The character tests run before the culture triggers,
  through `scope:character ?=`. The first version used `=`, and pop portraits,
  which have no character, logged two errors each (caught in the startup-log
  check).
- **UN bulk lobbying.** The `has_variable` guard stops the button's tooltip
  logging 3 errors for each of 24 rows: 1,584 lines in nine minutes with the
  chamber open.

## Lessons

- **Count the tick a pause lands on.** The harness pauses the game to read
  the date, and the pause lands inside a weekly tick about half the time,
  because that tick is a third of the week's wall time and the first pause
  of a run always meets one. A wall clock that leaves out the gaps spanning
  a pause leaves out those ticks, and reads a run up to 12% fast by luck: on
  2026-11-13 a run with a setting pushed the harmful way read as the
  fastest of the day. Take the paused seconds off such a gap and keep it
  (`wall2.py`).
- **Push a setting the harmful way before believing a small gain.** Four
  runs with the journal-entry update interval at three times its default
  read 6% faster than seven unchanged runs. Set to a quarter of its default,
  the task tripled and wall time did not move. One run the other way said
  more than four replicates of the gain, and what it said is that the gain
  is not explained.
- **Empty a thing to learn its share before trimming it.** All the mod's
  on_actions emptied is about 0.08 s of a 1.03 s day, and all its journal
  entries about 30 ms of tick tasks. Both were knowable in one run each, and
  both bound what any cut inside them can give.
- **A cut in script CPU need not move wall time.** #1713 took 136 ms a day
  off the flat dump's script time (15% of it) and left wall time per day
  where it was. The flat dump sums CPU over threads; judge a speed fix by
  wall time per frame type, and say which one it is.
- **Read the bottleneck column.** The GUI profiler gives each entry its
  worst thread's time beside the sum over threads. Where the two are equal
  the work is serial and holds up the day; where the bottleneck is a tenth
  of the total, as for the UN buttons, cutting it frees CPU but not time.
  Choose fixes by the bottleneck.
- **Count lines before reading a label.** The call graph labels a callee
  with `file:line`. In a journal entry, on_action or event file that is the
  real line. Inside a scripted effect the body is renumbered: the
  definition's line plus the count of lines since it that hold code
  (closing braces included), with comment lines and blank lines not counted.
  And a callee's times are its totals over all its callers, not its share
  under the entry selected. Reading a label as the file's
  own line put Demographics' census on the inheritance refresh (file line
  421), and counting comment lines but not blank lines made aeroplanes look
  like the Strategic Reserve's costly good.
- **Measure which walk costs before caching one.** The formables'
  external-pressure walk was cached monthly on the reasoning that it was
  one of three `any_country` walks per call; AFU's `possible` did not move.
  The two ROOT-dependent walks are the cost (#1720).
- **Sample the main thread when the time is outside the tick tasks.**
  Knockouts of whole areas (drawing, the mod's GUI, its pulses, the
  investment pass) moved nothing in 2030, while a read-only sampler named
  the cost in one run: per-thread CPU, the main thread's instruction pointer
  mapped to functions by `.pdata` and their strings, and the text its stack
  points at. `GUI.Draw` off doesn't stop the GUI's data updates, so a costly
  readout survives every drawing knockout ("The USA of 2030" above).
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

## Open (2026-11-12, with the answers of 2026-11-13)

Numbered as first listed, so references from other files hold, not by size.
Items 3 and 6 were addressed by #1713. The knockout runs of 2026-11-13
("Where the day goes") answered items 1, 2 and 13, half answered 7 and added
14 to 17; each of the first four now opens with its answer.

1. **Answered, 2026-11-13.** The time outside the tick tasks is three
   things: frames drawn while the tick is worked out (gone with sub-tick
   rendering off), the mod's on_actions (about 0.08 s a day by one run with
   them emptied, 0.06–0.08 by the call graph), and about 0.35 s a day that is
   vanilla's pulses, the frames between ticks, engine work in no task, and
   what the mod's journal entries do outside their tasks. `RecalculateModifierNodes` is not driven
   by the pulses' refreshes. As first written:
   **Unattributed day-boundary time: about 0.43 s of each ordinary day's
   hour 0**, 22% of wall time in 1931, beyond the tick tasks and the
   per-frame floor. The day-spread serial script in "Which script holds up
   the day" is part of it, about 9 s profiled in 30 days, so roughly 0.1 s a
   day unprofiled; #1721 removes the construction market's share. Suspects:
   - The day-spread pulses. Monthly country pulses come about 9 countries a
     day, and yearly state and country pulses are spread over the year. The
     merged `on_monthly_pulse_country` has 22 on_actions in
     `extra_on_actions.txt` alone, the Demographics census steps about 2–3
     states a day, and then there are the events those pulses fire.
   - The engine's or the interface's own day-change work.
   - `RecalculateModifierNodes` (0.13 s a day with the debugger and flat dump
     attached, about 0.10 s unprofiled; in tasks), driven by the pulses'
     modifier refreshes.

   The flat dump records none of the effect work; the call graph (above)
   reads it. In 2072 the merged monthly country pulse
   read about 1.25 s per month on the worst thread, and it and the
   journal-entry pulses read higher than in the first capture of the original
   code (merged pulse 516 → 1,249 ms, CH 179 → 319 ms, covert 175 → 262 ms).
   Those captures differ in date, open panels and machine load. Other 2072
   items: Cultural Hegemony `ch_monthly_pulse_on_action` 303 ms, monetary
   191 ms, combined arms 118 ms, `sol_expectations_on_actions.txt:9` 117 ms.
2. **Answered, 2026-11-13: the pass is the played country's investment
   pool.** Singapore's pool makes 22 to 154 costly decisions a week at about
   13 ms each, presumably scored across its bloc's 314 states; the other 262
   countries add little. No define makes a decision cheaper, and the buildings' script
   is not the cost ("Where the day goes"). As first written:
   **The weekly investment pass**: `HandleAutonomousInvestment` takes 1.1 s of
   each weekly tick (about 10% of wall time in 1931). Building triggers are
   23% of script time, 64% of it in mod files; this pass and the construction
   AI are the likely askers, though the dump doesn't say which. The mod
   defines 458 building types to vanilla's 118. (Those shares are the first
   run's; building-trigger call volume differed 2.4× in the remeasure.)
   **A/B, 2026-11-12:** a local
   build added a copy of each of the 325 company buildings with `always = no`
   first in its `potential` (783 types in all; same save and steps, 60
   unprofiled days). `HandleAutonomousInvestment` per weekly frame went from
   1,014 ms to 1,028 ms, and wall time from 73 s to 75 s, both within noise.
   So the pass does not scale with types that fail `potential` at once. The
   real flagships fail theirs at a first cheap check too (`owner = {
   has_company = … }`) for every country but the company's own, so they are
   probably not the pass's cost either. What the run leaves open is the deeper
   path for each company's own country; the reverse run (the real flagships
   made unbuildable) would settle it. The one cost the copies did show:
   `RecalculateModifierNodes` rose from about 100 ms to 120 ms at every hour
   0, about 0.06 ms a day per building type, so the flagships cost about
   20 ms a day (1.5% of wall time). That was one run each way, and three runs
   of one build later read 101, 117 and 135 ms for that task (open item 13),
   so the 20 ms is within run-to-run spread and unproven. Earlier (2026-10-03),
   after #679 the AI asked buildings' `possible`, `can_build_private` and
   `ai_value` about 7× more often (`01_industry.txt` 62k → 459k calls per
   tick-equivalent). The owner expected that to settle.
   **The reverse run, 2026-11-12 (#1731's build, deploy-only change):** every
   one of the 325 real flagships got `always = no` first in its
   `potential`, same save and steps, 62 unprofiled days (snapshots
   `20261113T014825Z` against `20261113T015413Z`, tick-task CSVs in
   `/mnt/d/vic3te-data/perf-2026-11-12/batch3/`).
   `HandleAutonomousInvestment` over the nine weekly frames was 9,144 ms
   against 9,185 ms. So the flagships are not this pass's cost either way:
   not as extra types, not through the company's own country. What the pass
   spends its second on is still unknown. A clue: it ran 1,016 ms a weekly
   frame and also 15 ms on each other frame. The pass's own figures agree to
   0.5% between the runs; the day-boundary task `RecalculateModifierNodes`
   and wall time do not (9,206 against 8,240 ms; 1.39 against 1.33 s a day),
   which is run-to-run spread (open item 13).
3. **UN AI propose buttons** (#1713 took them from 136 to 4 ms of
   script a day, with wall time unchanged; the rest of this item is the
   record): 4.48 s per 33 days in 1931 (14% of all script; 2.9% in 2072). `un_propose_credentials_button`'s `visible` costs 2.75 ms a
   call: `un_credentials_case_exists` walks every country. Its comment orders
   the breach-or-defiance test first because most countries fail it, but
   120+ of the 250–299 countries pass it in 1931 (outlawed dissent and the
   like), so the dossier test runs for each of them. In order:
   - **Exact, given one engine assumption:** put each button's own cheap
     tabling gates from its `possible` in its AI-only `visible`, ahead of the
     case scan. For most buttons these are `un_propose_own_motion_gates`: no
     vote under way, no cooldown, not in recess, dues paid, represented. The
     observer request has its own list. The scan then stops running while a
     vote is under way or the Assembly is in recess. The assumption, not yet
     verified, is that the AI presses a button only when it is both visible
     and possible; if so, no decision changes.
   - **Exact:** in `un_credentials_candidate`, move the cheaper target-side
     tests ahead of the breach test, after measuring what each costs.
   - **Owner call:** a monthly list of candidate targets per topic, read by
     the scan. The AI would then react up to a month late. Mandate and
     court-referral cases still walk every state in the world.
4. **The 1st of the month**: 3.8 s against 1.4 s of tasks in 1931, so about
   2.3 s is unattributed (3.8 − 1.4 − 0.11). The call graph puts the global
   `on_monthly_pulse` at 669 ms and the colonial bar at 899 ms, both
   profiled; the rest is open. The journal-entry monthly pulses take 1.06 s,
   inside a task (`MonthlyPulseJournalEntries`).
   In 2072 those were Cultural Hegemony 319 ms, covert warfare 262 ms, UN
   86 ms, banking 72 ms, Strategic Reserve 42 ms and nuclear 62 ms. In the CH
   pulse, `cultural_hegemony_benchmark_mult` (two `cultural_pull_raw`s each)
   is evaluated three times. In the covert pulse, `covert_ops_sync_all` runs
   14 pact scans; gate it on the country having any covert pact or `iw_ops`.
5. **Formables' `possible`** (`te_formable_countries.txt`): 1.45 s per 33
   days; the AFU block costs 471 µs a call, for three `any_country` walks.
   `afu_formation_external_pressure` (and its siblings for the other
   formables) doesn't depend on ROOT, so a global flag set by the monthly
   pulse would replace one walk per call. The formation would then lag by up
   to a month, which is an owner call. Built and measured in #1713: no change
   (25.0 → 24.9 ms a day), so reverted. The two ROOT-dependent walks are the
   cost; EUN's block, with the same shape, costs about 30 µs a call (#1720).
6. **The month-start error burst**: about 5,700 errors from
   `extra_script_values.txt:1587` on every 1st (#1703; #1713 fixed it:
   none in its after-run).
7. **Half answered, 2026-11-13: sub-tick rendering**, frames drawn while a
   tick is worked out, which `-disable_renderframeifneeded` or the console's
   `gamestatetick.renderframeifneeded` switches off ("Where the day goes").
   With it off a sub-tick still takes 0.044 s beyond its tasks (0.079 with it
   on), and an ordinary day's hour 0 0.27 s (0.50), so about half the floor
   is something else. The mod's HUD was not shown to matter (one run); the
   mod's own window, open, does ("The mod's own window"). As first written:
   **The per-frame floor**: about 0.11 s on every frame beyond its tasks,
   27% of wall time (a sub-tick takes 0.15 s against 0.04 s of tasks). It is
   probably rendering or speed pacing, not script. Test with
   `-disable_renderframeifneeded` (#1700). Script the interface evaluates
   lands here: an open event window evaluates its options' effect tooltips
   every frame (`un_events.4`'s mission effects were the GUI capture's top
   root entry).
8. **Interest-group overrides** (`common/interest_groups/00_*.txt`,
   regenerated): 8% of script time in 2072. Diff the hot lines against
   vanilla to see whether the mod added cost. (Since 2026-10-10 the mod no
   longer copies these files: `zz_te_ig_female_chance.txt` INJECTs only the
   three `female_*_chance` fields, so the rest of that cost is vanilla's
   own.)
9. **The Cultural Hegemony panel** reads live `cultural_pull_total` on every
   frame while open. A monthly snapshot would be cheaper, and is an owner
   call.
10. **Expensive `add_modifier` multipliers.** A quick scan (multipliers whose
   script-value closure reaches an iterator) found 11 that remain:
   - `sol_expectations_{upper,middle,lower}_shift_value` (`every_country`;
     #1724 applies them from a variable)
   - `global_tech_spread_script_value` (`every_country`)
   - `un_peacekeeping_benefit_scale` and `un_aid_benefit_scale`
     (`every_country`)
   - `total_tourism_throughput_bonus_percent` (buildings)
   - `migration_crowding_mult` (states)
   - the covert slot and cost multipliers (pacts)
   They cost one evaluation per application. They'd cost one per tick if
   the engine re-evaluated multipliers every tick, which our logs
   contradict for JE modifiers (see `scripting_best_practices.md`).
   Settle that with an in-game test, then turn the scan into an audit
   next to `je_multiplier_scope_audit` (it walks the same graph).
11. **The colonial stability bar** (1.3 ms a read in 1931; 899 ms in 30 days
    in the call graph) evaluated its 22 terms three times per read: the
    bar's lines, then `drift_total` and `drift_uncapped` in the cap term,
    which took 641 ms of the bar's 1,035 ms in a later run (snapshot
    `20261112T232122Z`, `callgraph/sr_colonial/pc_cb0.png`). Done in #1726:
    the bar saves its sum (`save_temporary_value_as`) and the cap line is
    clamp(sum) − sum, with a block-level clamp after it. A profiled run of
    a block-clamp-only version put the bar below 442 ms, out of the root
    list's 27.
12. **The other serial script** (call graph, 2 July → 1 August 1931; see
    "Which script holds up the day"), by size. The callees were opened in a
    second profiled run over the same dates (snapshot `20261112T215918Z`),
    so some totals here differ from the table's first run by up to 4%.
    - **Demographics' yearly state step:** `te_demog_state_yearly`, 2,083 ms,
      33 ms a state. The census block took 1,178 ms (1,206 in the second
      run, of which `te_demog_state_census` 1,157, about 18 ms a state), the
      walks 892 ms, inheritance and Wealth Concentration about 12 ms. The
      census is Demographics Full's core, so this is a lead for the owner,
      not a fix.
    - **The Strategic Reserve's weekly pulse:** 820 ms, 278 calls, about
      3 ms a country a week, on the weekly frame, which is already the
      longest. It is spread over about 40 small calls: the shared refresh
      tail 224 ms (the hub's flow modifiers 110), each good's policy tick
      20–37 ms, each good's preset magnitudes about 14 ms. No world walk and
      no single fix. Narrowed instead by who holds one, in #1730: the AI's
      founding tier needs 100 million GDP from a minor inside another
      country's market, ten times the 10 million a market leader or a major
      needs (`st_res_ai_hub_gdp_tier`). Of this game's 55 holders, 34 were
      such minors and 30 of them below 100 million, so a new game would
      carry no fewer than about 25 by 1931's measure: at most about 55%
      less of this pulse, or 0.25–0.3% of wall time. More stay in practice,
      since a country that qualified at any time since Logistics (as a
      market leader, a major, or above the bar) keeps its hub. Hubs already
      built stay.
    - **Covert warfare's monthly pulse:** 776 ms, of which 653 ms was one
      `ordered_country` that every holder ran to store the world's best
      intelligence capacity in `global_max_ic`, which only the panel reads.
      Done in #1724: one census each 1st, behind a 25-day global lock.
    - **Cultural Hegemony's monthly pulse:** 661 ms, of which 654 ms was
      `trigger_event` for the milestone events `cultural_hegemony.8` and
      `.9`, whose triggers read the live `cultural_pull_total`. Done in
      #1724: `.9` is tried only by the leaderboard's #1 (a condition its
      trigger holds), `.8` once the cache `var:ch_total` reaches 5.
    - **Cultural Hegemony's country pulse:** 526 ms, in
      `ch_monthly_country_update`: `ch_total = cultural_pull_total` 341 ms,
      `ch_art` 143 ms. `cultural_pull_total` evaluates `cultural_pull_raw`
      twice (the share and `ch_world_raw_live`), and `cultural_pull_from_art`
      evaluates `country_fine_art_production`, an `every_country` GDP sum,
      about four times. Done in #1731: both read once and saved
      (`save_temporary_value_as`), 528 → 188 ms (see "Merged `main`
      remeasured").
    - **SoL expectations:** 446 ms, of which 437 ms was
      `sol_expectations_apply_strata_shifts`. Each class's shift value adds
      `global_average_sol`, an `every_country` pass, and the limit read it
      twice and the multiplier once: nine world passes per country a month.
      The `add_modifier` swaps themselves cost little. Done in #1724: each
      class's value is read once into a variable.
    - **Monetary:** 359 ms, spread over a dozen steps, the FX and inflation
      block the largest at 114 ms. No hotspot.
    - **Local climate's yearly state pulse:** 612 ms (the refresh effect's
      624 ms includes one call from `local_climate_first_on_action`), three
      script values at 180–252 ms each. `te_climate_bonus` is the penalty
      times −1, so the refresh computed the penalty twice. Done in #1724: the
      bonus is written from the stored penalty. In #1731 the heat term reads
      its excess once (430 → 381 ms). What is left is the six raw terms,
      computed once for the penalty and again for its base
      (`te_climate_penalty_raw`); sharing them needs the effect to compute
      them once, a parallel of the two values' formulas.
    - **Tourism's state refresh** (on `main` after #1724): 268 ms, 871 calls:
      the output modifier 151 ms and the stored base appeal 102 ms, each the
      base appeal's chain of some 670 `state_region` branches. Done in #1731:
      the appeal is stored first and the output reads it back (268 →
      179 ms). The rest is the monuments' walk over every building in the
      state.
    - **Smaller, spread, no single fix (on `main` after #1724):** the
      nuclear programme's weekly pulse 181 ms over 1,274 calls
      (`nd_weekly_update` 108, its reach and basing refreshes 49 of that);
      monetary 364 ms over a dozen steps; the global monthly pulse's power
      grid 144, UN 108, tax 88 and journal map 86 ms; the Grand Monuments
      state pulse 136 ms, all inside `gm_state_monthly`.

    **#1724, measured** (same save, same steps, 2 July → 1 August under the
    profiler): the Cultural Hegemony entry's pulse 661 → 8 ms, covert
    warfare's 777 → 132 ms, local climate's 612 → 427 ms, SoL's 447 →
    234 ms; 1.7 s of serial script in all, with the untouched entries within
    6%. At the profiler's 2.6–3.5× (above) that is about 0.5–0.65 s over 30
    days unprofiled, about 1.5% of wall time.

    `on_revolution_start` fired 126 times in those 30 days (#1723): 125 of
    them were 25 one-state countries whose revolution is tried again each
    week (see "Merged `main` remeasured").
13. **Closed, 2026-11-13: they do not drive it.** With every mod on_action
    emptied, refreshes included, `RecalculateModifierNodes` read 115 ms a day
    against 96 to 119 in unchanged runs; and giving every country and state
    one more modifier, decaying or not, left its day-boundary frame at
    105–112 ms. No skip-when-unchanged
    refresh or dead band is worth building for this task's sake. As first
    written:
    **Refreshes that re-add a modifier at the same strength** (see "Does a
    refresh's re-add drive `RecalculateModifierNodes`?"). The engine's
    modifier recalculation takes about a tenth of wall time. Whether the
    mod's monthly remove-and-re-add refreshes are much of it is unproven:
    ten runs could not separate it from a 30% spread between runs of one
    build. If a
    larger test shows that they are, the exact fix is to keep the applied
    multiplier in a variable and re-add only when it moved, with the
    self-healing ROOT marker of `scripting_best_practices.md`. It would save
    only where values hold still: tourism's output (appeal, city rank,
    monuments) mostly does; its throughput and SoL's shifts move a little
    every month, so a dead band or a rounded multiplier would be the
    owner's call. The pollution refresh re-adds on every owned state each
    month (871 a month).
14. **The number of countries** (2026-11-13). Each one-state country costs
    about 0.7 ms of tick-task time a day (0.5–0.6 of it in
    `RecalculateModifierNodes`, `UpdateAI` and the journal-entry tasks),
    before its share of the monthly and yearly pulses, and 160 of the 263 countries of 1931 have one state. With
    119 of them annexed (and 48 states and 6% of the buildings merged away
    with them) the tick tasks took 16% less. Whether the world
    should hold fewer of them (fewer releases, unions of small neighbors, the
    revolts of #1723 ended) is a design question for the owner. Not measured:
    the wall-time gain without an event window open, and what the six
    unfinished revolts cost.
15. **Small pops** (2026-11-13). A quarter of the pops are under 100 people
    and hold 0.02% of the population; far higher consolidation defines removed
    5.5% of pops in 120 days. See "Small pops" for why they stay and what, if
    anything, a define can do.
16. **The Timeline Extended window's Nation tab** (2026-11-13). Open, it
    makes every frame twice as dear, paused or running, and a rendering-on
    day about half again as long ("The mod's own window"). The cost is in
    the overview and the five sections. Their rows are shown or hidden by 83
    generated counts of `has_modifier` tests and drawn with the engine's
    breakdown accessor, up to 81 at once, on every frame; which of the two
    it is has not been separated. To fix (#1760): test whether the
    breakdowns are the cost (a variant whose rows read `GetValueFor`; the
    probe that opens the window is beside the runs), and if so keep the plain
    figure in the row and move the breakdown to its tooltip; otherwise gate
    the rows behind collapsed sections, as the two list panels are, or have
    the generator write the counts into variables once a month. Other
    tabs, the full-screen layout and National Info are unmeasured.
    **Half done, 2026-11-20** ("The USA of 1992"): the breakdowns are about
    half the cost (paused, vsync off: open 19.8–20.6 ms, rows on
    `GetFormattedValueFor` 12.0–13.9, shut about 6). The fix moves each row's
    breakdown to its tooltip (#1760's pull request). Of the other 6–8 ms,
    about 3 are the sections' six timed-modifier lists, each walking the
    country's 61 timed modifiers with its name filter every frame; a count
    gate saves little, since five of the six rows hold a modifier. Ways
    out, for the owner: draw each row's one to four modifiers as fixed
    widgets shown on `has_modifier` (loses the timed modifier's own tooltip
    and expiry date), or fold the lists behind a toggle like All Modifiers'.
    The last 2.7 ms are the sections' rows and bars.
17. **The journal-entry update interval** (2026-11-13). Under 1% of the day
    by its task; four runs at three times the default read 6% faster and a
    run at a quarter of it read no slower, which is unresolved ("Journal
    entries"). Not worth building on without five or more runs each way.
18. **The weekly economic migration pass** (2026-11-20). 3.2 s a week on
    the USA of 1992 against 0.27 on its 1977 save with the same build: a
    fifth of a rendering-off day. It is market migration, cheaper with fewer
    movers and with fewer receiving states; not the market's size,
    unemployment, mass migration or the two hub states ("The weekly
    migration pass"). The only levers are vanilla's migration defines, a
    gameplay change: `MARKET_MIGRATION_STATE_ATTRACTION_FRACTION` at 0.9
    cuts it by 69%, the weekly caps at their 500 base by 45%. The owner's
    call.
