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

**2026-11-26 20:15 MST.** Baseline taken. A game week takes 44 s, and one
engine task is two thirds of it: the investors' construction pass
(`HandleAutonomousInvestment`), 29.6 s on every weekly tick. Next: whether
that pass runs on one thread or many, and what one placement costs.

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

None yet. Each finding gets a heading, the measurement behind it, and what
was or could be done.

## Changes made on this branch

None yet.

## Proposals that change gameplay (owner's call)

None yet.

## Open

None yet.
