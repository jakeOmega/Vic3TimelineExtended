# In-game QA harness, part 2: the overlay, the fixture, the session and its verbs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Claude session can run `python3 -m game_qa start … / read … / pick … / try-event … / stop` and get a game on the deployed build, played as a chosen country, with reads, option picks and a report, the owner's files protected by part 1's verbs throughout.

**Architecture:** A long-lived session server (one process, localhost HTTP) owns the Windows helper, the log followers, the console and the debugger for the life of one game; the command-line verbs are thin clients of it. The server never touches the owner's files itself: it runs part 1's `snapshot`, `launch`, `watch` and `restore` as subprocesses, so there is one implementation of the protective flow. The harness's own script lives in a generated overlay mod that `launch` adds to the playset.

**Tech Stack:** Python 3.11/3.12 stdlib (`http.server`, `subprocess`, `ctypes` on the Windows side), `unittest` under pytest, everything testable against `game_qa/fakes.py` and temp folders.

**Spec:** [docs/superpowers/specs/2026-11-10-in-game-qa-harness-design.md](../specs/2026-11-10-in-game-qa-harness-design.md), §§ 5.4–5.9 as amended by § 12.3. Part 1's plan and what its reviews changed: [2026-11-10-in-game-qa-harness-part1.md](2026-11-10-in-game-qa-harness-part1.md) and `docs/guides/python_tools.md` § "Driving the game from a session". Probe files and live captures: `docs/testing/game_qa_probe/`.

**Decided by the owner (2026-11-10, after part 1):** exactly two fixed-position clicks to enter the game (the country, then Start); "someone is at the machine" is judged by the cursor having moved or the foreground window having changed since the helper last looked, not by Windows idle time; build part 2 straight through and leave its PRs open; launches for the live tasks are granted for after the owner has left (Tasks 8–9 say how that is established).

## Global Constraints

- Everything in part 1's Global Constraints still binds: stdlib only; `win_helper.py` imports nothing from the package and runs on Windows Python 3.11; Python 3.11 syntax; root-level `test_game_qa_<part>.py` files ending in their single `unittest.main()` block; no test starts a Windows program or needs the game; commits staged by path; `scripts/preflight.py --quick` before each push; `--base main`; a "Player guide: no player-facing change" line in each PR body; the owner merges.
- **The owner's files are touched only by part 1's verbs.** No code in this plan copies, restores or deletes anything under the user-data folder except: the overlay mod folder `mod/te_qa_overlay/` (created and removed by exact path, and only if its `.metadata/metadata.json` carries the harness's marker), and saves named `te_qa_fixture_*` (renamed from the `TEST_FAIL_te_qa_fixture_*` save a fixture run made). `content_load.json` is written only by `launch`.
- **The game is started only by `launch`, followed only by `watch`, restored only by `restore`.** The session runs them as subprocesses (`python3 -m game_qa …`) and reads their JSON; it branches on the exit code, and a refusal or hold from any of them ends the session's start or is reported from its stop, never worked around.
- **`watch` starts within seconds of `launch`** (part 1 holds a run whose first look came more than 120 s late).
- **Keys and clicks go out only while the game's window is in front**, through the helper; text is never typed twice (`ConsoleError.entered` of `None` or `True` is never retried).
- **Protective changes get a break-it review before use**: Task 2 (`launch` writes the playset) and the session's stop path (Task 5) are reviewed by an independent reviewer told to break them with concrete scenarios.
- **Values:** country click at 0.492, 0.656 of the client area and Start at 0.9216, 0.975 (measured on 3840x2160, spec § 12.1 A2); presence readings 3 s apart; foreground wait up to 120 s; fixture run `-gdpr-compliant -debug_mode -handsoff -scripted_tests -run_until=1836.1.4`; session launch `-gdpr-compliant -debug_mode -script_debugger -loadsave=<name>`; debugger port 6111; session server on `127.0.0.1:8951`; two fixtures kept; overlay folder name `te_qa_overlay`; carrier namespace `te_qa`.

## Review Focus

1. **The session server dies, or is killed, while the game is up.** Expected: `watch` (its own process) still records the exit; `restore`/`recover` then judge as part 1 specifies; a new `start` refuses until that is resolved; nothing of the owner's changes. Pinned in Task 6 (`test_a_dead_server_leaves_the_run_to_recover`).
2. **`launch` writes the playset and then the start fails.** Expected: `restore`/`recover` put `content_load.json` back; the next launcher start sees the owner's playset. Pinned in Task 2 (`test_a_failed_start_after_the_playset_write_is_put_back`).
3. **The click lands while another window has come to the front** (the game pops Notepad). Expected: refused before the mouse moves; nothing clicked elsewhere. Pinned in Task 1 (`test_click_refused_when_the_game_is_not_in_front`).
4. **Two events of the same id are pending, or none is.** Expected: `pick` by name takes the oldest and says so; `pick` with nothing pending is an error, never a pass. Pinned in Task 5 (`test_pick_by_name_with_two_pending_takes_the_oldest_and_says_so`, `test_pick_with_nothing_pending_is_an_error`).
5. **A setup effect with unbalanced braces or a second top-level key.** Expected: refused when the overlay is built, before any launch. Pinned in Task 3 (`test_a_setup_with_unbalanced_braces_is_refused`).

---

## File structure

| File | Responsibility |
|---|---|
| `game_qa/win_helper.py`, `helper.py`, `fakes.py` (modify) | New ops `click` and `presence` |
| `game_qa/console.py` (modify) | Presence rule instead of idle time; `send`, `arrived`, `close`, `hotkey` |
| `game_qa/__main__.py`, `gate.py` (modify) | `launch --playset`, `--add-mod`; the session verbs as clients |
| `game_qa/overlay.py` | Generate and remove the overlay mod |
| `game_qa/fixture.py` | Fixture key, make, find, prune |
| `game_qa/session.py` | One game's life: start, the steps, stop |
| `game_qa/server.py` | The localhost server around a `Session`; the client call |
| `game_qa/report.py` | The run folder and its summary |
| `test_game_qa_click_presence.py`, `_playset.py`, `_overlay.py`, `_fixture.py`, `_session.py`, `_server.py`, `_report.py` | Tests |
| `.claude/skills/game-qa/SKILL.md`, `CLAUDE.md`, `docs/guides/python_tools.md` | The procedure and its pointers |

---

### Task 1: Click, presence, and the console's new calls

**Files:** Modify `game_qa/win_helper.py`, `game_qa/helper.py`, `game_qa/fakes.py`, `game_qa/console.py`; tests `test_game_qa_click_presence.py` and additions to `test_game_qa_console.py`.

**Interfaces (produces):**

```python
# win_helper ops
# click    {pid, x, y}  client pixels -> ok | not_foreground | bad_point (outside the client area)
# presence {}           -> {cursor: [x, y], foreground: <hwnd int>, helper_cursor: [x, y] | null}
# helper.py
@dataclass
class Presence: cursor: tuple[int, int]; foreground: int; helper_cursor: tuple[int, int] | None
class Helper(Protocol):                      # added
    def click(self, pid: int, x: int, y: int) -> None: ...
    def presence(self) -> Presence: ...
# console.py
PRESENCE_GAP_S = 3.0
class Console:                               # added
    def send(self, text: str) -> None        # front check, type text + Enter, no wait for arrival
    def arrived(self, text: str) -> bool     # did the history gain `text` since the last send/run
    def close(self) -> None                  # press the console key once; only after a proven-open console
    def hotkey(self, scan: int) -> None      # one key to the game itself; refuses unless the console is closed
```

- `click` checks the foreground exactly as `keys` does, converts client to screen coordinates, moves the cursor, presses and releases the left button (`SendInput`, button up in a `finally`), and remembers where it put the cursor (`helper_cursor`).
- **Presence rule** (replaces the idle-time rule in `Console._front`): when the game is not in front, take a presence reading, wait `PRESENCE_GAP_S`, take another. If the foreground window changed, or the cursor moved and is not where the helper last put it, someone is at the machine: keep waiting and reading, up to `FOREGROUND_WAIT_S`, then `not_foreground`. If nothing changed between two readings, take the foreground back. `idle_ms` is no longer used by `Console`.
- `Console` tracks whether the console is open (`True` after a round trip, `False` after `close`, unknown at the start). `run`, `send` and `ensure_open` open it when it is not known to be open. `hotkey` raises `ConsoleError("console_open")` unless it is known closed.

- [ ] **Step 1: failing tests**, among them: `test_click_refused_when_the_game_is_not_in_front` (nothing moved, nothing clicked), `test_click_outside_the_client_area_is_bad_point`, `test_click_releases_the_button_when_the_press_raises`, `test_presence_reports_cursor_foreground_and_the_helpers_own_cursor`, `test_a_moving_cursor_keeps_the_console_waiting_and_never_focuses` (fake clock reaches 120 s, `focus_calls == 0`, no steps), `test_a_still_machine_gets_the_foreground_back_after_one_gap` (one `focus`, clock about 3 s), `test_the_helpers_own_cursor_move_is_not_a_person`, `test_send_types_once_and_does_not_wait`, `test_hotkey_refuses_while_the_console_is_open`, `test_close_then_hotkey_then_run_reopens_the_console`.
- [ ] **Step 2–4:** run red, implement, run green with `test_game_qa_console.py` and `test_game_qa_win_helper.py`.
- [ ] **Step 5: commit** "Game QA: clicks, a presence reading, and console calls for the session".

### Task 2: `launch` adds the overlay to the playset

**Files:** Modify `game_qa/__main__.py`; test `test_game_qa_playset.py`.

**Interfaces (produces):** `launch <id> --permission … [--playset current|mod_only] [--add-mod WINDOWS_PATH]… -- <args>`; default `current`. Journal entry `playset` (`enabled`: the list written). New refusals: `mod_not_in_playset` (`mod_only`, and the deployed mod's folder is not among the enabled mods), `playset_unwritable`.

- The write happens inside `launch`, under the lock, after the claim and before the start: read `content_load.json` (the stale check has just proved it equals the snapshot's copy), keep the entry for the deployed mod only when `mod_only` (matched on the folder path, case-insensitively, against `path_constants.mod_deploy_target` in Windows form), append each `--add-mod` path not already present, write the file by temp name and rename. With neither option the file is not touched. A failure to write refuses before the game starts (the claim stays, as for a failed start).
- `content_load.json` is in part 1's snapshot set, so `restore` puts it back; nothing else is needed.

- [ ] **Step 1: failing tests:** `test_add_mod_appends_and_keeps_the_owners_entries`, `test_mod_only_keeps_this_mod_and_the_added_ones`, `test_mod_only_without_this_mod_in_the_playset_refuses_before_any_write`, `test_no_option_leaves_the_file_untouched` (bytes and time), `test_the_journal_records_what_was_enabled`, `test_restore_puts_the_owners_playset_back` (snapshot, launch with `--add-mod`, watch, restore: bytes identical), `test_a_failed_start_after_the_playset_write_is_put_back` (`start_game` raises: `recover` after the claim has aged restores the file), `test_an_unwritable_playset_refuses_and_starts_nothing`.
- [ ] **Step 2–4:** red, implement, green with `test_game_qa_gate.py`.
- [ ] **Step 5: commit** "Game QA: launch writes the run's playset, and restore puts the owner's back". This task then gets a break-it review before Task 5 uses it.

### Task 3: The overlay

**Files:** Create `game_qa/overlay.py`; test `test_game_qa_overlay.py`.

**Interfaces (produces):**

```python
OVERLAY_NAME = "te_qa_overlay"; MARKER = "te_qa_overlay generated by game_qa"
READ_EVENT = "te_qa.1"; PAD_EVENT = "te_qa.2"; FIXTURE_TEST = "te_qa_fixture"
class OverlayError(Exception): ...
@dataclass
class Overlay:
    dir: Path; events_file: Path; read_line: int          # line of te_qa.1's debug_log: the breakpoint
    setup_events: dict[str, str]                          # setup name -> event id ("te_qa.10", "te_qa.11", …)
def build(dest: Path, setups: Mapping[str, str], game_version: str) -> Overlay
def remove(dest: Path) -> bool                            # only a folder named OVERLAY_NAME whose metadata has MARKER
def parse_date(line_text: str) -> tuple[int, int, int] | None    # "… date=January 11, 1836" -> (1836, 1, 11)
```

- Files written (one UTF-8 BOM, tabs): `.metadata/metadata.json` (shape of `docs/testing/game_qa_probe/overlay/.metadata/metadata.json`, `short_description` holding `MARKER`, `supported_game_version` from `game_version`); `events/te_qa_events.txt` with `te_qa.1` (hidden; `immediate` is one `debug_log = "TE_QA read country=[THIS.GetCountry.GetTagName] date=[TimeKeeper.GetCurrentDate.GetString]"` then `te_qa_pad = yes`), `te_qa.2` (hidden; `te_qa_pad = yes` only), and one hidden event per setup that logs `TE_QA setup <name> start`, calls `te_qa_setup_<name> = yes`, logs `TE_QA setup <name> done`, then `te_qa_pad = yes`; `common/scripted_effects/te_qa_effects.txt` with `te_qa_pad` (sixty padding `debug_log` lines through `while = { count = 60 … }`, as the probe's `te_qa_probe_pad`) and `te_qa_setup_<name> = { <the session's script> }`; `tools/scripted_tests/te_qa_fixture.txt` (as `docs/testing/game_qa_probe/overlay/tools/scripted_tests/te_qa_probe.txt`, test name `te_qa_fixture`).
- A setup name must match `[a-z][a-z0-9_]{0,40}`. A setup body is refused (`OverlayError`) when its braces do not balance outside quotes and comments, or when it is empty. `build` replaces an existing overlay only through `remove`, and refuses a `dest` that exists and is not a marked overlay.

- [ ] **Step 1: failing tests:** `test_build_writes_the_files_with_one_bom_and_tabs`, `test_read_line_is_the_debug_log_line_of_the_read_event`, `test_each_setup_gets_its_own_event_and_effect`, `test_a_setup_with_unbalanced_braces_is_refused` (also: a brace inside a quoted string or a `#` comment does not count), `test_a_bad_setup_name_is_refused`, `test_remove_refuses_a_folder_without_the_marker` (a folder named `te_qa_overlay` holding other files is left alone), `test_build_refuses_to_overwrite_a_folder_that_is_not_an_overlay`, `test_parse_date` (the twelve month names, a line without a date).
- [ ] **Step 2–5:** red, implement, green, commit "Game QA: the generated overlay mod".

### Task 4: The fixture

**Files:** Create `game_qa/fixture.py`; test `test_game_qa_fixture.py`.

**Interfaces (produces):**

```python
FIXTURE_ARGS = ("-gdpr-compliant", "-debug_mode", "-handsoff", "-scripted_tests", "-run_until=1836.1.4")
RunCli = Callable[[Sequence[str]], tuple[dict, int]]      # runs `python3 -m game_qa <argv>`, returns (reply, exit code)
class FixtureError(Exception): ...
def key(game_version: str, enabled_mods: Sequence[str], deploy_dir: Path) -> str     # 12 hex digits
def find(user_data: Path, key: str) -> Path | None        # save games/te_qa_fixture_<key>.v3
def make(run_cli: RunCli, user_data: Path, key: str, overlay_windows_path: str, permission: str,
         playset: str, owner_confirmed_busy: bool = False, sleep=time.sleep) -> Path
def prune(user_data: Path, keep: int = 2) -> list[str]
```

- `key` hashes the game version, the enabled mod paths in order, and, for every file under the deploy folder's `common/`, `events/` and `map_data/`, its relative path, size and modification time.
- `make`: `snapshot`; `launch <id> --permission … --playset … --add-mod <overlay> -- FIXTURE_ARGS`; `watch <id>` (blocks until the game has quit by itself); then, **before** `restore`, find exactly one `save games/TEST_FAIL_te_qa_fixture_*.v3` and rename it `te_qa_fixture_<key>.v3`; then `restore <id>` (retrying `watch_still_recording` for up to 30 s). Any refusal or hold from a verb raises `FixtureError` carrying the reply, after still calling `restore` if a launch happened. No save, or more than one, is a `FixtureError`.
- `prune` keeps the `keep` newest `te_qa_fixture_*.v3` by modification time and removes the rest; it touches no other file.

- [ ] **Step 1: failing tests** with a scripted fake `run_cli` that also creates the `TEST_FAIL_…` save when "the game runs": `test_key_changes_with_the_version_the_playset_and_a_script_file`, `test_make_renames_the_save_before_restore_and_returns_it`, `test_make_calls_the_verbs_in_order_with_the_fixture_arguments`, `test_a_refused_launch_is_a_fixture_error_and_nothing_is_renamed`, `test_restore_is_still_called_when_no_save_appeared`, `test_a_held_restore_is_a_fixture_error_that_names_the_snapshot`, `test_prune_keeps_two_and_only_touches_fixtures`.
- [ ] **Step 2–5:** red, implement, green, commit "Game QA: a fresh save made without clicks, kept by build".

### Task 5: The session

**Files:** Create `game_qa/session.py`, `game_qa/report.py`; tests `test_game_qa_session.py`, `test_game_qa_report.py`.

**Interfaces (produces):**

```python
COUNTRY_CLICK = (0.492, 0.656); START_CLICK = (0.9216, 0.975)
class SessionError(Exception): code: str; detail: str
@dataclass
class Read: expr: str; ok: bool; raw: str; value: bool | float | None
class Session:
    def __init__(self, helper: Helper, run_cli: RunCli, spawn_watch: Callable[[str], Any], paths: Paths,
                 sleep=time.sleep, clock=time.monotonic): ...
    def start(self, permission: str, as_tag: str | None = None, setups: Mapping[str, str] | None = None,
              save: str | None = None, playset: str = "mod_only", owner_confirmed_busy: bool = False) -> dict
    def console(self, text: str) -> Reply
    def run_setup(self, name: str) -> list[str]            # the setup's log lines between its start and done markers
    def events(self) -> list[Pending]
    def pick(self, index: int, event: str | None = None) -> dict
    def read(self, exprs: Sequence[str]) -> list[Read]
    def tag(self, tag: str) -> None
    def enter_game(self) -> dict                            # the two clicks; proves it by the date moving
    def advance(self, days: int) -> tuple[int, int, int]    # at least that many days; the date reached
    def shot(self) -> Path
    def stop(self) -> dict                                  # always safe to call; returns restore's reply
# report.py
class Report:
    def __init__(self, run_dir: Path): ...
    def step(self, verb: str, **fields) -> None             # appends one JSON line with a time
    def close(self, summary: dict) -> Path                  # writes summary.md beside steps.jsonl; returns its path
```

- `Paths` carries `user_data`, `backup_root`, `deploy_dir`, `base_game`, and the Windows forms the helper needs; tests build it over temp folders.
- **`start`**, in order: `overlay.build` into `<user_data>/mod/te_qa_overlay`; unless `save` is given, `fixture.find` or `fixture.make`; `snapshot --save <name>`; `launch … --playset … --add-mod <overlay> -- -gdpr-compliant -debug_mode -script_debugger -loadsave=<name>`; `spawn_watch(id)` at once; `helper.adopt` the process `launch` reported; wait for a responding window (up to 300 s); follow `debug.log` and `error.log`; `Console.ensure_open`; `tag` when `as_tag` is given; open the helper's relay to port 6111 and `Debugger.attach` with the breakpoint at the overlay's `read_line`. A refusal or hold from `snapshot` or `launch` raises `SessionError` with the verb's reply and starts nothing further. Any failure after `launch` calls `stop` before raising.
- **`read`**: `Console.send(READ_EVENT's console command)`, `wait_stopped` (15 s, else `SessionError("no_stop")` after a `resume` attempt), evaluate each expression, `resume`, drain `Debugger.errors()`. The command's arrival is checked after the resume.
- **`events` / `pick`**: `select_event_option list` parsed by `logtail.pending_events`; `pick` always passes the numeric id; by name, it takes the oldest pending instance and returns `ambiguous: True` when there was more than one; nothing pending, or an index beyond the option count, is `SessionError("nothing_pending" | "bad_index")` before any key.
- **`enter_game`**: `click` at `COUNTRY_CLICK` then `START_CLICK` (fractions of the helper's client rectangle), then prove it: read the date (`READ_EVENT`'s log line, flushed by its own padding), `close` the console, `hotkey(space)`, wait 3 s, `hotkey(space)`, reopen, read the date again. Later date: entered. Same date: `SessionError("not_entered")` with a screenshot path. Called by `advance` when the game has not been entered.
- **`advance`**: with the console closed, unpause, wait, pause, read the date; repeat until at least `days` have passed; the wait is sized from the days still missing and the rate seen so far (first guess 1.5 days a second). Gives up after 20 rounds (`SessionError("stalled")`).
- **`stop`**: `helper.kill` the adopted process (already gone is fine), wait for the `watch` subprocess to return (up to 60 s), `restore <id>` (retrying `watch_still_recording` up to 30 s), `overlay.remove`, close the helper, close the report. It never raises for a hold: it returns the reply, and the report's summary leads with it.

- [ ] **Step 1: failing tests** over `FakeHelper`, a scripted `run_cli`, and a fake debugger transport: the start order (`test_start_runs_the_verbs_in_order_and_watch_at_once`), `test_a_refused_launch_starts_nothing_else`, `test_a_failure_after_launch_still_stops_and_restores`, `test_read_evaluates_at_the_breakpoint_and_resumes`, `test_read_without_a_stop_resumes_and_raises`, `test_pick_always_passes_the_numeric_id`, `test_pick_by_name_with_two_pending_takes_the_oldest_and_says_so`, `test_pick_with_nothing_pending_is_an_error`, `test_enter_game_clicks_the_two_points_of_the_client_area` (a 3840x2160 and a 1920x1080 client), `test_enter_game_that_does_not_move_the_date_raises_with_a_screenshot`, `test_advance_reaches_at_least_the_days_asked`, `test_stop_kills_waits_for_watch_restores_and_removes_the_overlay_in_that_order`, `test_stop_reports_a_hold_and_does_not_raise`, `test_stop_twice_is_harmless`; and for the report, `test_steps_are_appended_and_the_summary_leads_with_the_restore`.
- [ ] **Step 2–5:** red, implement, green, commit "Game QA: one game's session, from start to restore". The stop path then gets a break-it review.

### Task 6: The server and the verbs

**Files:** Create `game_qa/server.py`; modify `game_qa/__main__.py`; test `test_game_qa_server.py`.

**Interfaces (produces):** `python3 -m game_qa start --permission … [--as TAG] [--save NAME] [--setup NAME=FILE]… [--playset …] [--owner-confirmed-busy]`, `console "<text>"`, `run-setup NAME`, `events`, `pick INDEX [EVENT]`, `read "<expr>"…`, `tag TAG`, `enter-game`, `advance DAYS`, `shot`, `stop`, `status`, `doctor`. Each prints one JSON object; exit 0, or 2 for a refusal, a hold or an error.

- `start` spawns `python3 -m game_qa session-serve` detached (its own process group; its output to a log in the run folder), waits for `<backup_root>/session.json` (`port`, `pid`, `snapshot`), then posts `start` to it. Every other verb posts to the port in that file; no file, or no answer, is `{"refused": "no_session"}`. `stop` posts `stop`, and the server exits after answering.
- The server answers one request at a time, `POST /<verb>` with a JSON body, on `127.0.0.1` only; a `SessionError`, `ConsoleError`, `DebuggerError` or `HelperError` becomes `{"refused": <code>, "detail": …}`; on any error during `start` it runs `stop` itself. It removes `session.json` when it exits. A `start` while `session.json` names a live server is refused (`session_running`).
- `doctor` launches nothing: paths resolve, the Windows `python.exe` answers the helper's `ping`, `nvidia-smi` reads, the backup root is usable, no unfinished or held snapshot, no leftover overlay folder or stale `session.json`.

- [ ] **Step 1: failing tests** with a `Session` double behind a real server on an ephemeral port: `test_a_verb_round_trips_json`, `test_no_session_is_refused`, `test_an_error_inside_a_verb_is_a_refusal_not_a_crash`, `test_stop_answers_then_the_server_exits_and_removes_its_file`, `test_a_second_start_is_refused_while_one_runs`, `test_a_failed_start_runs_stop`, `test_a_dead_server_leaves_the_run_to_recover` (the server process is killed after `launch`: `session.json` is stale, a new `start` is refused by `snapshot`'s `unfinished_run`, and nothing under the fake user-data folder changed), `test_doctor_names_what_is_missing`.
- [ ] **Step 2–5:** red, implement, green, commit "Game QA: the session server and its verbs".

### Task 7: `try-event`

**Files:** Modify `game_qa/session.py`, `game_qa/__main__.py`, `game_qa/report.py`; tests in `test_game_qa_session.py`.

**Interfaces (produces):** `Session.try_event(event: str, setup: str | None, reads: Sequence[str]) -> dict` and the verb `try-event EVENT [--setup NAME] --read "<expr>"…`. The reply and the report hold one row per option: `fired`, `options`, `before` and `after` (the reads), `picked`, `new_errors` (error-log lines seen during that option, without the debugger's own validator burst), and `did_not_fire` when the event was not pending after firing.

- For each option index from 0: run the setup when given; fire with console `event <event>` unless the setup's own log shows it triggered the event; `events`; if the event is not pending, record `did_not_fire` and stop the loop; read; `pick`; read. The number of options comes from the first `events` reply. State is shared between options and the report says so (spec § 5.8; console `event` ignores trigger and cooldown, § 12.1 A6).

- [ ] **Step 1: failing tests:** `test_each_option_is_fired_read_picked_and_read_again`, `test_the_setup_runs_before_each_option`, `test_an_event_that_does_not_fire_is_reported_and_never_a_pass`, `test_new_errors_leave_out_the_debuggers_own_burst`.
- [ ] **Step 2–5:** red, implement, green, commit "Game QA: try-event, the owner's first check".

### Task 8: Live session 1 — prove what has never run live

Needs the game, an unlocked desktop and the owner's launch grant. **Establishing the grant:** the owner granted launches for after they have left. Either they have said in the conversation that they have left, or the session posts a notice that it is about to launch, waits ten minutes, and proceeds only if the owner has not answered that they are still on. `launch`'s own gate (GPU, running game) applies as always.

- [ ] `doctor`; `selftest-restore`.
- [ ] `start --as FRA` on a fresh fixture: proves the overlay through `launch`, the fixture through the tool, `Console` and `LogFollower` live, the debugger attach.
- [ ] `read` three expressions; `events`; fire the probe-style visible event through a setup and `pick`; `enter-game`; `advance 10`; `shot`.
- [ ] Presence: with the game behind another window and nobody at the machine, a command takes the foreground back after one gap.
- [ ] `stop`: restored, not held; compare an independent copy of the owner's files.
- [ ] Fix what the session shows; each fix with a test; record the results in the spec (a § 13) and `docs/testing/game_qa_probe/`.

### Task 9: The acceptance check, the skill, the docs

- [ ] `try-event` on one real mod event with at least two options, chosen for a setup of a few lines (the report is the evidence; attach its summary to the PR).
- [ ] `.claude/skills/game-qa/SKILL.md`: when to use it; the permission rule (ask unless granted for the session; even then the gate decides); the order of verbs; what a hold means and that only the owner resolves one; never start the game any other way; what to do after a refusal. A row in `CLAUDE.md`'s rules table. `docs/guides/python_tools.md`: the session verbs, replacing the "library with no command yet" bullet. `docs/superpowers/README.md` rows.
- [ ] Three PRs, `--base main`, left open: A (Tasks 1–2), B (Tasks 3–7), C (Tasks 8–9's results, skill and docs).
