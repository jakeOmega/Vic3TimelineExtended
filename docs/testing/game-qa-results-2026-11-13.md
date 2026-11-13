# In-game QA harness results: 2026-11-13, the Game QA PRs of the day

The first live runs of what PRs #1737 to #1742 add (#1736 changes tests only and has nothing to run). Everything
ran from one scratch branch (`scratch/qa-integration-2026-11-13`) that merges all seven after their review fixes,
so a result here belongs to the PR that added the verb, not to `main`.

**Game:** Victoria 3 1.15.1. **Build:** the deployed mod folder as it stood (the main checkout was at `9cca92222`;
not compared with the folder). **Launches:** five sessions and one unattended run, on the owner's go-ahead for
this session (2026-11-12 23:07 MST: "You will be able to run the game to test but I would like this to be as late
in the process as possible - do what you can first, please"), after the offline work. Before each start `doctor`
was clean, `gate --permission probe` answered ok, and the GPU load was 18 to 38%. Every stop restored the owner's
files (`outcome: restored`, nothing held) and left no overlay; `player/game_rules/presets.txt` was never touched.

**Run folders** (under the backup root): `runs/20261113T075605Z/` (session A), `…080833Z/` (B, refused at
start), `…081657Z/` (B), `…082316Z/` (B′), `…083721Z/` (the dated fixture's run) and `…084215Z/` (C). Each
session's `steps.jsonl` and `summary.md`, and the fixture run's `fixture.json`, are copied to
`docs/testing/game_qa_probe/captures/session_2026-11-13_qa_prs/` with the Windows user name replaced by `<user>`.

## Session A: the 1931 save (`runs/20261113T075605Z/`)

`start --save perf_bench_sgp_1931_08_12 --playset current --game-arg no_notifications --add-mod
'D:\vic3te-data\qa-addmod-test'`, with no `--as`, so the first read is the one #1702 lost. Started in about two
minutes. The playset's load order was the owner's three workshop mods, the deployed mod, the variant, then the
overlay. The launch arguments carried `-no_notifications`, and the overlay wrote the enlarged profiler window
(`profiler_window.enlarged: true`). The game was paused at 1 July 1931, playing Singapore.

| Check | PR | Result |
|---|---|---|
| The first read after `start --save` (#1702 item 1) | #1737 | **Not reproduced.** `read "game_date > 1931.1.1"` answered yes on its first typing (`arrived: true`). The retry for a lost first typing was not needed, so this run says nothing about it |
| A variant mod loads beside the deployed one (#1702 item 2) | #1742 | **OK.** The variant's one scripted value, `te_qa_addmod_loaded`, read 1; the deployed mod's `te_tax_obl_horizon` read 60, its value on `main` |
| `profile start`, `dump`, `summary` (#1700) | #1742 | **OK.** `profile start` answered `Discarded 0 recorded frames` and `Enabled`. After `advance 30`, `profile dump A` wrote 8,283 tick-task rows (the game said `Wrote 8283 rows`) and 9,163 script-profile entries. `profile summary A`: 1.781 s a day while running; tick tasks led by `HandleAutonomousInvestment` (32%) and `RecalculateModifierNodes` (14%); script time 66% vanilla, 33% this mod. `dump B` after 10 more days and `summary A B` worked (1.25 s a day over B). `summary A --run <id>` worked after the stop |
| A pick when an event's id is above 2^31 - 1 (#1722) | #1737 | **The signed-id idea is disproved.** With `un_events.4` (2684354595) and `te_debug_ch.1` (3456106516) pending, `pick 0 un_events.4` sent `select_event_option 0 2684354595`, then `select_event_option 0 -1610612701`: both answered `No matching pending event`. A `select_event_option 0` typed with the `console` verb, both still pending, answered `Selected option 0 of un_events.4`, the first listed and the lowest id. #1737 was reworked after this (the `oldest` form, and `id_unaddressable` for any other high id); the rework has not run live |
| A pick with one event pending (#1732) | #1737 | **OK.** `pick 5 te_debug_ch.1` went `form: no_id` and answered `Selected option 5 of te_debug_ch.1`. Option 5 is the Cultural Hegemony recount, so this also ran #1731's play-test row's event |
| The profiler window at a legible size (#1701) | #1738 | **OK.** The game loaded the overlay's copy of `script_profiler.gui` (no BOM, as the installed file has none). `profiler-roots` crops of the Current and Callees columns read in full at the window's own resolution. Opening the profiler did not take the keyboard: `events` worked straight after |
| A click into the profiler takes the keyboard (#1710, #1725 point 3) | #1738 | **OK.** A click on a root row answered `keyboard_away: true` and made it Current (the Current pane showed its whole call graph). The next `read` was refused `keyboard_away` with nothing typed. `click --console` answered `keyboard_away: false`, and the read after it worked (`c:SGP.gdp` 4.64e9) |
| `wheel` and `drag` in the profiler | #1738 | **OK.** `wheel 0.7 0.6 -3` moved the Callees list about 7.5 rows (about 2.5 a notch); `drag 0.854 0.45 0.854 0.36` on the scrollbar's thumb moved it. Both latched the keyboard away, and `click --console` gave it back |
| The stop with a profiler dump | #1742 | **OK.** `stop` restored. The root `ticktask_timings.csv` the dumps had written over was put back (609,230 bytes, its original time), no manual save had changed, the overlay was removed and the playset restored; `doctor` was clean after |

Side findings from the profile, over 32 game days:

- `te_unemployment_on_actions.txt:8`, the merged yearly state pulse, was called 70 times for 2,949 ms. Most of it
  was its callees: `te_demog_on_actions.txt:17` (2,444 ms) and `local_climate_on_actions.txt:36` (440 ms).
- The harness's own read event, `te_qa_events.txt:4`, cost 721 ms over the capture: a profile taken during a
  session counts the session's reads.

## Session B: a second rule switched, and Back (`runs/20261113T081657Z/`)

`start --as FRA --switch-rule global_warming_rule=global_warming_disabled`, under this mod alone. The first try
(`runs/20261113T080833Z/`) was refused at `console_ready` with `not_foreground` ("the game's window left the
front while typing"). Nothing had been typed into the game, and its stop restored. A fresh save was made first for
this build (`te_qa_fixture_c6498ca4f4c4`), and its run's ten `TE_SELF_CHECK` lines were kept: nine OK and one
`conscription_term_read` START whose verdict comes a week later, after the fixture's run had ended. The retry
started cleanly.

| Check | PR | Result |
|---|---|---|
| A second rule switched in the copy (#1599's note: other rules untried) | (#1631, on `main`) | **OK.** `has_game_rule = global_warming_disabled` yes, `global_warming_enabled` no, and the control `banking_system_enabled` yes. The mod's rule-off handling was not shown: `je_world_climate` opens only at an anomaly of 0.1, so its "no" after 35 days says nothing |
| `enter-game --via back` on an ordinary lobby (#1598) | #1741 | **OK.** One click at (144, 2119) of the 3840×2160 client. The `back_shot` taken straight after already shows the game as France on 2 January, paused, with the top bar, journal entries and outliner. The date went from 2 to 6 January; `is_player = yes` and `c:FRA = root` read yes |
| `advance` after entering through Back | #1741 | **OK.** `advance 35` reached 10 February |
| The stop | #1739 | **Restored**, 52 files put back, no `manual_saves` in the reply |

## Session B′: Back past a law window (`runs/20261113T082316Z/`)

`start --as FRA --setup heir=<file>` with `activate_law = law_type:law_state_universal_heir`, the case #1598 was
filed for.

| Check | PR | Result |
|---|---|---|
| The law window covers the country-select screen | — | `run-setup heir` raised "We now have State as Universal Heir!" in the middle of the screen. The side panel read "Click on a country to select it" |
| `enter-game --via back` with the window up (#1598) | #1741 | **OK.** One click at (144, 2119). The `back_shot` shows the game in play as France on 2 January, the law window still up over it. The date went from 2 to 6 January, and `is_player` and `c:FRA = root` read yes |
| Time passes under the window | #1741 | **OK.** `advance 10` reached 16 January with the window still up |
| The law itself | — | `has_law = law_type:law_state_universal_heir` read no afterwards: something puts it back at once, as on 2026-11-12. Not a harness question |
| The stop | #1739 | **Restored**, 52 files, no `manual_saves` |

After this session, #1741 gained a second commit: the default country click, when the side panel shows it
selected nothing, now clicks Back in Start's place instead of refusing `no_country_selected`. Its two halves each
ran live (the panel check on 2026-11-12, Back past the window here); the two together as one verb have not.

## Session C: a dated fixture (`runs/20261113T083721Z/`, `runs/20261113T084215Z/`)

| Check | PR | Result |
|---|---|---|
| `fixture --until 1836.3.29 --dry-run` | #1740 | **OK.** Key `c6498ca4f4c4_d18360329`, `run_until` 1836.3.31, `long_run: false`, no autosaves, 132 s estimated, a watch limit of 1,021 s. Its `next` text asked for a grant of the run, which a short run does not need; fixed on the branch afterwards |
| The run | #1740 | **OK.** `-handsoff -scripted_tests -run_until=1836.3.31`, 187 s from launch to exit. The game's timer: 90 days in 59.8 s, 0.664 s a day, slower than the 0.47 the estimate uses for these years |
| The save's name and date | #1740 | **OK.** Found as `TEST_FAIL_te_qa_fixture_29 March, 1836.v3`, renamed on the first try to `te_qa_fixture_c6498ca4f4c4_d18360329.v3`. Its own `game_date` 1836.3.29 (`date_matches: true`) |
| The log copy | #1740 | **OK.** 20 polls, no gaps, 4,632 `debug.log` lines; 140 lines kept with the save, 35 of them `TE_SELF_CHECK` |
| The run's restore | #1740 | **Restored**, 49 files; removed only the run's `tests.txt` and gametimer file |
| The game's own scripted tests | #1740 | **Unsettled.** No `TEST_FAIL_*` save of another test appeared (theirs fail from 1836.1.7 on), so they did not run or they passed. `tests.txt` would say, but the restore removes it without a copy |
| `start --fixture 1836.3.29 --as FRA` | #1740 | **OK.** `fixture_game_date` 1836.3.29, `date_matches: true`; `game_date >= 1836.3.29` and `game_date < 1836.3.30` read yes. `enter-game` by the country click went from 29 March to 1 April |
| An autosave written inside a session | (restore, on `main`) | **Restored.** Crossing 1 April the game wrote its quarterly `autosave.v3` (151 MB) and rotated the owner's five down a place, dropping the oldest. The stop restored 58 files, the five autosaves and `continue_game.json` among them; each autosave had the owner's size and time again, the dropped one included |
| `selfchecks` | (on `main`) | The dated fixture's lines: 30 OK, one START (`cm_census_yearly`, due at the next yearly census), one BROKEN: `delayed_state_event`, the known canary for "a delayed state event never runs" (`docs/guides/scripting_best_practices.md`) |

## What these settle

- **The console takes no event id above 2^31 - 1, in any typed form.** The listed id and its signed 32-bit form
  both answered `No matching pending event`; a select with no id picked the oldest pending event, the first
  listed and the lowest id. `pick` now uses no id for such an event when it is the oldest, and refuses
  `id_unaddressable` otherwise (#1737).
- **Back on the country-select screen enters the game as the tagged country**, with or without a law window over
  the screen, and the window blocks nothing in the entered game (#1741). The owner's lead of 2026-11-12 was right.
- **A second rule, Global Warming, switches in the copy as the Tax Code did** (#1631's `--switch-rule`).
- **A session's restore undoes an autosave rotation**, the first time one was seen inside a session.
- **The profiler verbs, the variant mod, the enlarged profiler window, the keyboard latch, `wheel` and `drag` work
  as built** (#1738, #1742).

## Not run live

The long dated fixtures (past 31 March 1836: they need `--long-run` and the owner's own grant), the
`not_the_runs_save` and `manual_save_changed` holds, `pick`'s `oldest` form as a verb (the same command ran by
hand), the read retry for a lost first typing (#1702 item 1 did not reproduce), and `enter-game`'s fallback to
Back as one verb.
