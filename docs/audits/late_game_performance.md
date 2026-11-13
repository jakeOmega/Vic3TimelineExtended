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
current`, and use `console` for each command below. Copy every output out of
the user-data folder before `stop`, because the restore puts `logs/` back.

- **Engine tick tasks**: `clear_ticktask_timings`, play, then
  `dump_ticktask_timings`. It writes `ticktask_timings.csv` to the user-data
  root, with one row per engine task per frame (`frame,task,milliseconds,
  calls,longest_lock`). The frame is the game date in hours, four frames a
  day (hours 0, 6, 12 and 18), and every frame since the clear is kept. Remove
  the file after copying it, since restore doesn't know it. There is no task
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
  event window evaluates its options' effect tooltips every frame.

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

## Open (2026-11-12)

Numbered as first listed, so references from other files hold, not by size:
the per-frame floor (item 7, 27% of wall time) is the largest after item 1.
Items 3 and 6 were addressed by #1713.

1. **Unattributed day-boundary time: about 0.43 s of each ordinary day's
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
2. **The weekly investment pass**: `HandleAutonomousInvestment` takes 1.1 s of
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
7. **The per-frame floor**: about 0.11 s on every frame beyond its tasks,
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
13. **Refreshes that re-add a modifier at the same strength** (see "Does a
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
