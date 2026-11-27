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

**2026-11-26 20:45 MST.** The week is 38.5–39.2 s (two matching runs; the
first run of the night, 44.1 s, was slower in every weekly tick and is
treated as disturbed). The investors' construction pass is 22 s of each
weekly tick, runs on one thread, and re-scores every candidate building
after each placement. Script is at least a quarter of that thread's time.
Measured so far: the update divisor (no clean gain). Running: Excess
Private Construction off, to price a slower queue turnover. Next: a cheaper
`ai_value` for the Railway and the Arts Academy.

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
- **Data:** `/mnt/d/vic3te-data/perf-2026-11-26/` (`run_variant.sh NAME
  [--add-mod WINPATH]`, `runs/<name>/`, `variants/<name>/`).
- The 60 s weekly tick outlasts the harness's 30 s wait for a pause to be
  acknowledged, so `advance` ends `left_running` (`no_ack`) once the 35 days
  are done. The timing is complete by then; the session can still `read`
  and must then `stop`.

## Baseline

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
  **88.8–90.7 s**, 22 s a tick, and 38.5–39.2 s a week.
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

| Weekly tick | 2 | 3 | 4 | 5 | Ticks 2–5 | Week |
|---|---|---|---|---|---|---|
| Baseline (`base3`) | 24.9 | 20.2 | 14.8 | 29.0 | 88.8 s | 38.5 s |
| Divisor × 10 | 33.6 | 11.9 | 12.0 | 16.7 | 74.2 s | 36.3 s |

The first full tick is no cheaper with a tenth of the updates, so the cost
follows placements, not updates: an update that finds the queue full costs
nothing (the other 27 ticks of a week run 23,000 of them in 16–36 ms). The
later ticks are lower, which is a change in what gets built, not a saving
per placement. A higher divisor also caps a small pool at one placement a
tick, 28 a week, which a country with a few million of weekly pool income
would notice. Not recommended.

### 4. Queue turnover is the big lever: Excess Private Construction off takes the week from 38.5 to 23.8 s

Session `20261127T033631Z` (`noexcess`): before the 35 days a setup removed
`too_much_private_construction` from the USA and set
`var:too_much_private_construction_cached` to 0, so its per-project weekly
cap fell from 3,064 to 690 (`modifier:country_max_weekly_construction_progress_add`).
Nothing else differs from the baseline.

| | Baseline (`base3`) | Excess off |
|---|---|---|
| Wall time a week | 38.5 s | **23.8 s** (−38%) |
| Investment pass, weekly ticks 2–5 | 24.9, 20.2, 14.8, 29.0 = 88.8 s | 0.95, 1.08, 19.1, 6.3 = 27.4 s (−69%) |
| `private_construction_used` at the end | 3.05 million | 0.69 million (−78%) |
| Levels finished in the USA's states, 35 days | 2,886 | 1,372 (−52%) |
| Private queue at the end | 1,000 | 1,000 |

The pass follows the levels placed: with a level taking four or five weeks
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

This changes what investors build, so it is the owner's call; options are
under "Proposals that change gameplay".

## Changes made on this branch

None yet.

## Proposals that change gameplay (owner's call)

Each of these trades investor building rate for speed; none is built.

1. **Stop Excess Private Construction's ramp where it stops adding levels.**
   Hold the raise at the point where a level takes one week (the cap equal
   to a typical level's cost), not 9,000. Free in levels and in time, and it
   takes back the efficiency penalty beyond that point. It does not make the
   week faster by itself; it stops paying for nothing.
2. **Hold the cap lower, so a level takes N weeks.** The pass is about 22 s ÷
   N. At the base cap (N of four or five) the week is 23.8 s against 38.5.
   Investors then finish that much less. A middle setting is measured below
   when run.
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

None yet.
