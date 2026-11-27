# Late-game performance: the USA of 2050

A working report, started 2026-11-26 and written as the session goes, so
that a session cut short still leaves its findings. Earlier saves (1931 to
2032) are in [`late_game_performance.md`](late_game_performance.md); this
file is the 2050 game alone.

**Goal (owner, 2026-11-26):** first, game speed in the late game (less wall
time per game year); second, a more responsive GUI (frame rate). The owner
notes the game "runs much slower when there is a lot in the construction
queue". Changes to vanilla systems are in scope where the time is spent in
vanilla code.

## Status

**2026-11-26 22:05 MST.** Two things take most of a 2050 week:

1. **The ship construction readout under the date**, about 6 s of a 32 s
   week, outside the tick work (finding 5). **Fixed on this branch** without
   changing gameplay: the box shows the total; the used figure is in its
   tooltip and the Ships tab.
2. **The investors' weekly construction pass**, 22 s of each weekly tick
   (two thirds of all tick work). It follows how many levels investors place
   a week, and the USA is at the engine's ceiling of 1,000. Nothing that
   keeps gameplay as it is has cut it: not a cheaper `ai_value`, not the
   `possible` blocks, not the update divisor (findings 2 and 3). A slower
   queue turnover halves the week's tick work (finding 4); that is the
   owner's call, with options under "Proposals that change gameplay".

## The save and the method

- **Save:** `te_qa_copy_iua2050_20261126.v3`, a byte-for-byte copy of the
  owner's exit save of 2026-11-26 (6 February 2050, the Imperial Union of
  America, tag `USA`), 1.15.2. The owner's own save is never loaded.
- **Session:** `python3 -m game_qa start --as USA --save <copy> --playset
  current --game-arg disable_renderframeifneeded --unresponsive-s 120`, then
  `profile start`, `advance 35`, `profile dump end`, `profile summary end`.
  Speed 5, no panel open, sub-tick rendering off (as the owner plays).
- **Wall clock:** `wallday.py` over the run's `dedicated_server.log`, with
  pauses taken out. **Tick tasks and script:** the harness's `profile
  summary`. A variant is an `--add-mod` folder of the changed files.
- **Data:** `/mnt/d/vic3te-data/perf-2026-11-26/` (`run_variant3.sh NAME
  [--add-mod WINPATH]... [--setup S=FILE --run-setup S]`, which also reads
  the queue, the pool and the count of finished levels at the end;
  `runs/<name>/`, `variants/<name>/`, `setups/`; `weekest.py` and
  `ttsum.py` for the tick tasks, `wallday.py` for the wall clock,
  `sp_buildings.py` for the script profile by building; the samplers of
  2026-11-23 with `stacksample_deep.py` and `stackstrings_tick.py`, which
  follow the tick thread).
- The 60 s weekly tick outlasts the harness's 30 s wait for a pause to be
  acknowledged, so `advance` ends `left_running` (`no_ack`) once the 35 days
  are done. The timing is complete by then; the session can still `read`
  and must then `stop`.

## Baseline

**Reference numbers** (three runs that repeat tick for tick, `base2`,
`base3`, `base4`; finding 1):

| Measure | Value |
|---|---|
| Tick tasks, a steady week (mean of weekly ticks 2–5, plus 27 other frames) | **33.0–34.2 s**: the weekly tick 27.0–27.6 s, of it the investment pass 22.2–22.7 s; the other 27 frames 6.0–6.6 s |
| Wall time, 7 February to 12 March (33.2 days: the cheap first weekly tick and three full ones) | 148–154 s, **31.2–32.4 s a week** |
| Wall time outside the tick tasks | about 8–9 s a week (sub-tick 0.37 s against 0.24 s of tasks) |

A run is compared on these two: `weekest.py` (tick tasks) and `wallday.py
<log> 2050.2.7 2050.3.12` (wall over the same dates). A whole run's
seconds a week is not comparable between runs, because a run ends on a
different tick and the fifth weekly tick is 30 s by itself.

**The first run of the night**, below, was slower in every weekly tick than
the three that followed (the machine was busier) and is kept only for its
shape.

Session `20261127T025708Z`, 6 February to 13 March 2050 (35 days, 140
ticks), deployed `main` at `7d353f90a`.

| Measure | Value |
|---|---|
| Wall time | **6.30 s a game day, 44.1 s a week** (about 38 minutes a game year) |
| Tick tasks | 6.31 s a day: the week is all tick work now, nothing outside the tasks |
| Paused frame | 10.2 ms (98 FPS) |

| Frame kind | Tick tasks each | Largest tasks |
|---|---|---|
| Weekly day, hour 0 (5 frames) | **35.6 s** | `HandleAutonomousInvestment` 29.6 s, `UpdateStateTrades` 2.7 s, `UpdateEmployment` 0.8 s, `ProcessAutoExpandingBuildings` 0.5 s |
| Ordinary day, hour 0 | 0.52 s | `RecalculateModifierNodes` 0.25 s |
| Hours 6, 12, 18 | 0.26 s | `ProcessEconomicMigration` 0.18 s, `HandleAutonomousInvestment` 0.04 s |
| The 1st, hour 0 | 0.59 s | `RecalculateModifierNodes` 0.19 s, `MonthlyPulseJournalEntries` 0.15 s |

Share of all tick time over the 35 days: `HandleAutonomousInvestment` 69%,
`ProcessEconomicMigration` 8%, `UpdateStateTrades` 6%,
`RecalculateModifierNodes` 5%, everything else 12%.

**The investment pass has grown tenfold since 2030** (3.05 s a weekly tick
then, 29.6 s now), as the note of 2026-11-23 predicted for a queue that
turns over every week. The USA's figures on 13 March 2050:

| Read | Value |
|---|---|
| `investment_pool` | 15.5 trillion (GDP 23.7 trillion) |
| `investment_pool_gross_income` | 11.5 billion a week, so 22,980 investment updates a tick at vanilla's one per 500,000 (`AUTONOMOUS_INVESTMENT_UPDATE_COUNT_DIVISOR`) |
| `private_construction_used` | 3.03 million points a week |
| `var:too_much_private_construction_cached` | 2,374 (Excess Private Construction's raise of the per-project weekly cap) |

With the cap that high a level finishes in about a week, so the 1,000-element
private queue empties and refills weekly: about 1,000 placements at about
30 ms each is the 29.6 s.

**Script inside it.** The script profiler counted 83.7 s of script over the
35 days (CPU summed over threads), 62 s of it in building files, which the
investment pass asks. The two largest entries are vanilla `ai_value` blocks:

| Entry | Seconds | Calls | Each |
|---|---|---|---|
| `06_urban_center.txt:57`, the Arts Academy's `ai_value` | 11.5 | 2.47 million | 4.7 µs |
| `11_private_infrastructure.txt:68`, the Railway's `ai_value` | 11.2 | 0.79 million | 14.2 µs |
| `01_industry.txt:457` (trigger) | 4.4 | 3.21 million | 1.4 µs |
| `01_industry.txt:440` (value) | 3.6 | 2.53 million | 1.4 µs |
| `01_zz_te_industry.txt:484` (mod, trigger) | 2.7 | 2.23 million | 1.2 µs |

About 500,000 calls of each building's `ai_value` per weekly tick fits 1,000
placements each scoring some 500 states.

## Findings

### 1. The weekly investment pass is one thread re-scoring everything per placement

Runs `base2` (`20261127T030938Z`) and `base3` (`20261127T032733Z`), the
second with a counter of finished levels (`variants/count`).

- **The runs repeat.** The pass took 1.97, 25.2, 20.1, 14.4 and 31.1 s on
  the five weekly ticks of `base2` and 1.84, 24.9, 20.2, 14.8 and 29.0 s in
  `base3`: the same save plays the same weeks. A variant can therefore be
  compared tick for tick. The first weekly tick after the load is always
  cheap (1.8 s); leave it out. The baseline for comparisons is ticks 2 to 5:
  **88.6–90.7 s**, 22 s a tick.
- **One thread.** Per-thread CPU every 0.67 s (`threadcpu.py`): through the
  pass the game's tick thread runs at 0.99 of a core, the main thread waits
  at 0, and about ten workers run at 0.3–0.7 each (7.3 cores busy in all).
  The work is handed out in small pieces from a serial loop, so the pass is
  as long as that one thread's work.
- **What the thread runs.** Its instruction pointer and near stack every
  5 ms, named by the strings each function references (`stacksample.py`,
  `name_rvas.py`): `SetPotentialPrivateInvestmentPriorities`
  (`country_ai.cpp`), the building score routine ("Base AI Value",
  "Profitability", "Produced goods value"), the goods profit routine, and the
  script system. A script-system function is on the near stack in 26% of the
  weekly tick's samples, a lower bound (the scan sees the nearest twelve
  return addresses), taken with the script profiler on.
- **Which script.** Almost all of it is `ai_value` (41 s of 64 s in building
  files over the 35 days) and `possible` (20 s), and about fifteen building
  types take nearly all the calls: Arts Academy, Railway, Steel Mill and
  the mod's radio, components, automotive, motor, tooling, glass,
  explosives, electrics, synthetics and appliance industries, each asked
  0.5 to 3.2 million times. These are the city industries with no resource
  or land cap, which every state can take. Farms, mines and plantations are
  asked a hundredth as often.
- **Count.** 2,886 levels finished in the USA's own states in the 35 days
  (577 a week); its investors also build abroad. The private queue stood at
  1,000 at the end and `private_construction_used` at 3.05 million.

So the cost is (placements a week) × (candidate states × candidate types) ×
(cost of scoring one). The engine owns the loop. What the mod can reach:
the script each candidate runs (finding 3), how many levels are placed a
week (finding 4, gameplay), and which candidates exist (not yet tried).

### 2. The update divisor is not a clean lever

`NAI.AUTONOMOUS_INVESTMENT_UPDATE_COUNT_DIVISOR` (vanilla 500,000: one
investment update a tick per that much weekly pool income, so 22,980 a tick
for the USA) raised tenfold, session `20261127T031817Z`:

| Weekly tick | 2 | 3 | 4 | 5 | Ticks 2–5 | Tick tasks, steady week | Wall, same dates |
|---|---|---|---|---|---|---|---|
| Baseline (`base3`) | 24.9 | 20.2 | 14.8 | 29.0 | 88.8 s | 33.5 s | 32.0 s |
| Divisor × 10 | 33.6 | 11.9 | 12.0 | 16.7 | 74.2 s | 30.3 s | 32.0 s |

The first full tick is no cheaper with a tenth of the updates, so the cost
follows placements, not updates: an update that finds the queue full costs
nothing (the other 27 ticks of a week run 23,000 of them in 16–36 ms). The
later ticks are lower, which is a change in what gets built, not a saving
per placement. A higher divisor also caps a small pool at one placement a
tick, 28 a week, which a country with a few million of weekly pool income
would notice. Not recommended.

### 3. A cheaper `ai_value` buys nothing: that script runs on the workers

The two costliest script entries of the baseline are vanilla's `ai_value` for
the Railway (a chain of twelve journal-entry cases) and the Arts Academy.
Variant `aiv` (session `20261127T034239Z`) replaced both buildings with
copies whose `ai_value` sits behind one gate that every case needs, so the
result is the same. The Railway's call fell from 14.2 to 6.3 µs and the Arts
Academy's from 4.7 to 3.1 µs.

| Weekly tick | 2 | 3 | 4 | 5 | Ticks 2–5 | Tick tasks, steady week | Wall, same dates |
|---|---|---|---|---|---|---|---|
| Baseline (`base3`) | 24.9 | 20.2 | 14.8 | 29.0 | 88.8 s | 33.5 s | 32.0 s |
| `ai_value` gated | 24.1 | 19.7 | 14.3 | 30.9 | 89.0 s | 33.6 s | 31.8 s |

No change. `ai_value` is scored on the worker threads, which are not what
the pass waits for, so the script profiler's seconds (CPU summed over
threads) say nothing here about wall time. **Not shipped**: it would have
meant a `REPLACE` of two vanilla buildings for no gain. The lesson holds for
any script the scoring calls: only what runs on the tick thread counts.

**The `possible` blocks are not the cost either.** City industries carry
`possible = { owner = { NOT = { OR = { has_law_or_variant =
law_type:law_industry_banned  has_law_or_variant =
law_type:law_extraction_economy } } } }` (eight vanilla buildings; nineteen
of the mod's through `is_industrial_production_allowed`), asked 12.8 million
times in the 35 days. Three variants, the same save and steps:

| Variant | Pass, ticks 2–5 | Levels finished in the USA | Reading |
|---|---|---|---|
| Baseline | 88.6–90.7 s | 2,886 | |
| `pot`: the test moved to `potential` | 89.1 s | 2,886 | The pass asks `potential` per candidate as well (5.7 million calls of the Steel Mill's) |
| `flagmod`: the test read from a boolean modifier the two laws carry | 87.3 s | 2,886 | The call fell from 0.84 to 0.69 µs; the pass did not move |
| `noposs`: the blocks removed | 48.4 s | 1,963 | Not a saving in script: states under those laws became candidates, investors chose differently, and their levels finished more slowly |

A deep scan of the tick thread's stack had shown the trigger and
`has_law_or_variant` routines on a third of its samples; the three runs say
that was stale stack memory, not live frames. So **no script the scoring
calls is on the serial path**; what the tick thread spends is engine work
per scored candidate. The `noposs` run adds one fact: the first full tick
took 30.0 s against 24.9 with about a fifth more candidates passing their
triggers, so the pass grows with the candidates that reach scoring. A
trigger that turned away candidates no investor would pick would cut it in
proportion. None is proposed: which candidates those are is an AI design
question.

### 4. Queue turnover is the big lever: Excess Private Construction off halves the week's tick work

Session `20261127T033631Z` (`noexcess`): before the 35 days a setup removed
`too_much_private_construction` from the USA and set
`var:too_much_private_construction_cached` to 0, so its per-project weekly
cap fell from 3,064 to 690 (`modifier:country_max_weekly_construction_progress_add`).
Nothing else differs from the baseline.

| | Baseline (`base3`) | Excess off |
|---|---|---|
| Tick tasks, a steady week | 33.5 s | **17.5 s** (−48%) |
| Wall time, same dates | 32.0 s a week | 23.8 s a week (the first weeks still finish projects in flight) |
| Investment pass, weekly ticks 2–5 | 24.9, 20.2, 14.8, 29.0 = 88.8 s | 0.95, 1.08, 19.1, 6.3 = 27.4 s (−69%) |
| `private_construction_used` at the end | 3.05 million | 0.69 million (−78%) |
| Levels finished in the USA's states, 35 days | 2,886 | 1,372 (−52%) |
| Private queue at the end | 1,000 | 1,000 |

**A middle setting** (session `20261127T051832Z`): the raise set to 700, so
a cap of 1,390 against 690 and 3,064. The pass took 1.6, 19.0, 7.7 and
2.2 s on ticks 2 to 5 (30.5 s; tick tasks 18.5 s a steady week), 1,551
levels finished in the USA's states, and `private_construction_used` stood
at 1.38 million. Over five weeks that is no different from the raise at 0:
both windows are mostly the projects in flight at the switch finishing two
or three weeks late and in one batch. What the two runs do show is that a
typical level here costs well over 1,390 points, so the saving starts
somewhere between a cap of 1,390 and 3,064. A run of several months each
side would place it; it needs a grant of hours.

The pass follows the levels placed: with a level taking about three weeks
the queue turns over a quarter as often. (The two cheap ticks and the 19 s
one are the projects in flight at the switch finishing together; a longer
run would even out near 7 s a tick.)

**Why this matters for the design.** Construction progress is applied once a
week and the private queue holds 1,000 one-level elements, so investors can
never finish more than 1,000 levels a week. The USA is at that ceiling: its
cap of 3,064 a project is at or above what a level costs, and every further
year of the modifier's ×1.2 ramp (toward 9,000) adds efficiency penalty and
no levels. The pool it is meant to drain holds 15.5 trillion and takes in
11.5 billion a week, of which construction spends about 0.1 to 0.5 billion.
So in this game the modifier no longer does what it was built for, and the
1,000 placements a week it produces cost 22 s of every week.

**What the levels are worth.** A setup summed the USA's buildings on 13
March 2050 (`setups/occ.txt`; level × `occupancy` over every building that
is not subsistence, session `20261127T043633Z`): 180 states, 3,544,997
levels, 2,559,468 of them staffed (72%). 1,113,484 levels, 31%, stand in
buildings under half staffed, with a population of 467 million. Investors
add about 30,000 levels a year in the USA's own states to a stock of which a
quarter has nobody to work it. Occupancy is not only a shortage of people (a
building that cannot pay its wages empties too), so this bounds the loss
from a slower turnover; it does not prove there is none.

**This is the measurement the super-building note of 2026-11-23 asked for**
("measure an era-12/13 save first"): at a full weekly turnover the pass is
22 s a weekly tick, and it scales with placements, so levels ten times the
size would leave about 2 s of it.

This changes what investors build, so it is the owner's call; options are
under "Proposals that change gameplay".

### 5. The ship construction readout under the date still costs about 7 s a week

The 2030 audit found vanilla's readout under the date
(`gui/timemanip.gui:487`, `text = "SHIP_CONSTRUCTION_VALUE"`, which is
`#v [Country.GetShipConstructionUsage|0]#!/[Country.GetShipConstruction|0]`)
to be half of that year's week. The fix that shipped was fewer supply ships
in progress (Naval Convoy Defense's weekly cap); it was never timed. In 2050
the cost is still there. The 2030 knockout variant (the text replaced by a
constant), session `20261127T041226Z`:

| | Baseline | Readout a constant |
|---|---|---|
| Wall time, same dates | 31.2–32.4 s a week | **25.3 s a week** (−21%) |
| Tick tasks, a steady week | 33.0–34.2 s | 33.0 s (unchanged, as expected: it is GUI work) |
| A sub-tick, wall | 0.37 s | 0.22 s |
| An ordinary day's hour 0, wall | 1.03 s | 0.71 s |

About 0.15 s after every tick, which is one evaluation of the text each time
the tick changes what it reads. Paused, the frame is 10 ms either way.

**Which figure costs it.** A one-line `replace/` override of
`SHIP_CONSTRUCTION_VALUE_WITHOUT_ICON` showing the total alone
(`[Country.GetShipConstruction|0]`, variant `shipcap`, session
`20261127T042734Z`) ran 25.7 s a week, the constant's time. So
`GetShipConstructionUsage` is the cost and the total is free. The box's
tooltip names what the usage walks: on 13 March 2050 the USA had **15,955
supply ships under construction** (and 526,626 available), against 0
warships.

**Fixed on this branch.** The mod overrides
`SHIP_CONSTRUCTION_VALUE_WITHOUT_ICON` to the total alone. Vanilla's
`SHIP_CONSTRUCTION_VALUE` is read in two places: the box under the date
(`timemanip.gui`, not overridden, so it picks the new text up) and the
Construction panel's Ships tab (`production_methods.gui`, which the mod
already overrides and now points at `TE_SHIP_CONSTRUCTION_VALUE_PANEL`, the
old "used/total"). The tooltip is vanilla's and still gives the full
breakdown, worked out on hover. No GUI file of vanilla's is newly
overridden. With the branch's own files as a variant (session
`20261127T043633Z`): **26.1 s a week against 31.2–32.4** over the same
dates, the box reading "50544", the tooltip "35015/50544 being used", the
Ships tab "35015/50544". `test_ship_construction_readout.py` holds the three
texts and fails if any other always-shown text reads the usage.

What is lost: the used figure at a glance. It is one hover away. If the
owner wants it back on the box, the cost comes back with it unless the
supply ships in progress are fewer (the rescale of
`docs/superpowers/plans/2026-11-24-supply-ship-scale.md` would cut the walk
tenfold).

## Changes made on this branch

| Change | Files | Measured |
|---|---|---|
| The ship construction box under the date shows the total, not "used/total" (finding 5) | `localization/english/replace/timeline_extended_override_l_english.yml`, `localization/english/te_miscellaneous_l_english.yml`, `gui/production_methods.gui`, `test_ship_construction_readout.py` | Wall time 31.2–32.4 → 26.1 s a week on the 2050 save (−18%); tick work unchanged |

Play-test rows: `docs/testing/perf-fixes-playtest.md`, "The ship
construction box under the date shows the total".

Tried and not shipped: a gated `ai_value` for the Railway and Arts Academy
(finding 3), the industry-ban test moved to `potential` or to a law
modifier (finding 3), a higher update divisor (finding 2).

## Proposals that change gameplay (owner's call)

Each of these trades investor building rate for speed; none is built.

1. **Stop Excess Private Construction's ramp where it stops adding levels.**
   Hold the raise at the point where a level takes one week (the cap equal
   to a typical level's cost), not 9,000. Free in levels and in time, and it
   takes back the efficiency penalty beyond that point. It does not make the
   week faster by itself; it stops paying for nothing.
2. **Hold the cap lower, so a level takes N weeks.** The pass is about 22 s ÷
   N. At the base cap (N of about three) the week's tick work is 17.5 s
   against 33.5, and investors finish about half as many levels in the
   USA's states, a quarter of whose existing levels are unstaffed. Where
   between a cap of 1,390 and 3,064 the saving starts needs longer runs
   (finding 4).
3. **Larger levels in the late eras, with a lower cap.** The owner's
   super-building idea, or a modifier form of it: the engine has
   `building_group_<group>_employee_mult` and `building_throughput_add`, so
   an era technology could make each level of the city industries (the
   uncapped groups, which are the ones investors place by the thousand)
   employ and produce more, while the cap is held so fewer levels finish.
   Growth is kept and placements fall. It needs a design: existing levels
   grow at once, construction cost per level cannot be raised by a modifier,
   and economy of scale and company thresholds count levels.

## Open

1. **The turnover decision** (finding 4 and the proposals above) is the
   owner's. A months-long pair of runs would say what a given cap costs in
   levels and saves in time once the transient is over.
2. **Which candidates the pass scores.** The Steel Mill's `possible` is asked
   about 760,000 times on a heavy weekly tick, and the USA owns 180 states,
   so most of what its investors score each placement looks to be foreign
   states. Two bounding runs that narrowed or widened the candidates
   (`noposs`, and `domonly`, city industries in the USA's own states only:
   pass 23.5 s over ticks 2–5) both changed what investors built and how
   fast it finished, so neither separates the cost of a placement from the
   number of placements. The engine's own weight on foreign candidates is
   `foreign_investment_ai_factor` on each building group; whether 0 there
   skips the scoring is not measured, and it would end foreign investment in
   that group.
3. **15,955 supply ships under construction.** The box no longer pays for
   them every tick, but the figure is the rescale plan's case
   (`docs/superpowers/plans/2026-11-24-supply-ship-scale.md`); nothing else
   in the tick tasks was traced to them.
4. **The rest of the week's tick work**, about 11 s: `UpdateStateTrades`
   2.7–3.5 s and `ProcessEconomicMigration` about 3.7 s a week (both engine
   passes; the migration defines were measured on the 1992 save and left to
   the owner), `RecalculateModifierNodes` 1.8 s. Not looked at again here.
5. **Wall clocks after 22:00 on 2026-11-26 are not usable.** The first try
   of the middle setting ended `not_foreground` (the game's window lost the
   front, #1963), and the two runs after it (`domonly`, the repeat of the
   middle setting) show 1.3–1.4 s a sub-tick outside the tick tasks against
   0.37 s before, with their tick tasks normal. Their tick-task figures are
   quoted above; their wall times are not. Every wall time in this report is
   from before that.
6. Side finding, filed as #2093: in the Ships tab the "used/total" figure
   runs into the cost beside it at five digits (it did before this branch).

## Lessons

- **The same save replays the same weeks.** Three unchanged runs agreed on
  each weekly tick to 2–7%, so a variant that leaves the game's choices
  alone is compared tick for tick, and one that changes them shows it in
  the pattern at once (finding 1).
- **Count a week on fixed dates.** `advance 35` ends on a different tick
  each run and one weekly tick is 30 s; a whole run's seconds a week moved
  by 20% for that reason alone (Baseline).
- **The script profiler's seconds are not the pass's seconds.** They are CPU
  summed over threads. 23 s of profiled `ai_value` and 12.5 s of `possible`
  were cut or moved with no change in the pass (finding 3).
- **A deep stack scan lists stale frames.** Thirty-two kilobytes of stack
  put `has_law_or_variant` on a third of the samples of a thread that was
  not running it. The nearest dozen return addresses are callers; the rest
  are history.
- **A knockout that changes what the AI may build measures the AI, not the
  code removed.** `noposs` and `domonly` each cut the pass by half or more
  by changing where investors built.
- **Split an always-shown text one data call at a time, in `replace/`.** A
  one-line loc override in a variant showed which of two calls cost 6 s a
  week, with no GUI file touched, and was the fix.

