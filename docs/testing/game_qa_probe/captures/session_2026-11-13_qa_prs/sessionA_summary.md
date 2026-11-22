Restore: restored (54 files put back, 0 removed).

- Permission: owner in this session, 2026-11-12 23:07 MST: 'You will be able to run the game to test but I would like this to be as late in the process as possible - do what you can first, please.' Offline work done first.
- Snapshot: 20261113T075605Z
- Save: perf_bench_sgp_1931_08_12
- Country: (none)
- Overlay removed: True

## Self-checks

1 OK.

- Session: 1 TE_SELF_CHECK lines in /mnt/d/vic3_qa_backups/runs/20261113T075605Z/debug.log. The game writes its log in blocks, so a line logged after the last verb may be missing.
- The run that made the fixture: no lines (the game ran on a save of the owner's, not on the fixture).

| Check | Verdict | From | Line |
|---|---|---|---|
| row_standing_on_creation | OK | session | common/scripted_effects/rules_of_war_effects.txt:88: TE_SELF_CHECK OK row_standing_on_creation path=other country=F61 standing=0 (a country made mid-game ran its first Rules of War law's on_activate with no standing, and was charged nothing for it) date=July 10, 1931 |

| # | Verb | Outcome |
|---|---|---|
| 1 | held | none |
| 2 | overlay | built |
| 3 | fixture | not_used |
| 4 | snapshot | ok |
| 5 | launch | ok |
| 6 | window | ok |
| 7 | console_ready | ok |
| 8 | debugger | ok |
| 9 | start | ok |
| 10 | read | ok |
| 11 | read | ok |
| 12 | profile_start | ok |
| 13 | console | ok |
| 14 | advance | ok |
| 15 | events | ok |
| 16 | console | ok |
| 17 | events | ok |
| 18 | pick | not_selected |
| 19 | console | ok |
| 20 | events | ok |
| 21 | pick | ok |
| 22 | events | ok |
| 23 | advance | ok |
| 24 | console | ok |
| 25 | profile_dump | ok |
| 26 | profiler_roots | ok |
| 27 | events | ok |
| 28 | shot | ok |
| 29 | click | ok |
| 30 | profiler_roots | ok |
| 31 | click | ok |
| 32 | read | ok |
| 33 | wheel | ok |
| 34 | profiler_roots | ok |
| 35 | drag | ok |
| 36 | profiler_roots | ok |
| 37 | click | ok |
| 38 | advance | ok |
| 39 | profile_dump | ok |
| 40 | kill | ok |
| 41 | restore | restored |
| 42 | stop | restored |
