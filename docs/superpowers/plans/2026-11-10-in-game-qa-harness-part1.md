# In-game QA harness, part 1: protection, the Windows helper and the I/O layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the parts of the harness that no open assumption can change (snapshot and restore of the owner's files, the launch gate, the Windows-side helper, log following, the console round trip, the debugger client), then use them in one permitted live session that settles the spec's six assumptions.

**Architecture:** A stdlib-only Python package `game_qa/` at the repo root, run as `python3 -m game_qa <verb>`. Everything that touches Windows goes through one self-contained file, `game_qa/win_helper.py`, run by the Windows Python and spoken to in JSON lines; every other module takes that helper, the clock and the filesystem as arguments, so the whole suite runs on CI with fakes and temp folders.

**Tech Stack:** Python 3.11/3.12 stdlib (`ctypes` on the Windows side), `unittest` classes run by pytest, PowerShell only for listing game processes before the helper is up.

**Spec:** [docs/superpowers/specs/2026-11-10-in-game-qa-harness-design.md](../specs/2026-11-10-in-game-qa-harness-design.md) (§ numbers below are its sections). Probe scripts and captures: `docs/testing/game_qa_probe/`.

**What this plan leaves out, on purpose.** The overlay mod, the fixture, the session service, the verbs `doctor` and `start` to `try-event`, the report and the skill depend on assumptions A1–A6 (§ 7). They get their tasks in a second plan, written after Task 9. The table at the end says which answer decides which part.

**One change from the spec.** § 7 calls the assumptions session "the plan's first task". Here it is the last task of part 1: the launches of 2026-11-10 lost two of the owner's autosaves and rotated their logs (§ 3.7), so no further launch happens before snapshot, restore and the gate exist and have passed a dry run on the real folder.

## Global Constraints

- **Stdlib only** in `game_qa/`. `game_qa/win_helper.py` imports nothing from the package: it runs under the Windows `python.exe` (3.11) from a `\\wsl.localhost\` path. Find `python.exe` on `PATH`, never by a profile path.
- **Python 3.11 syntax**: no f-string that reuses its own quote inside the braces. `scripts/preflight.py`'s `py311` check scans for it.
- **Tests** are root-level `test_game_qa_<part>.py` files of `unittest.TestCase` classes, each ending with the `if __name__ == "__main__": unittest.main()` block (`test_test_files_main_block.py` fails otherwise). No test starts a Windows program, reads `path_constants`' per-machine paths, or needs the game: each builds its folders with `tempfile` and passes fakes.
- **Run a test file:** `~/src/Vic3TimelineExtended/.venv/bin/python -m pytest test_game_qa_snapshot.py -q` from the worktree (a worktree has no venv of its own).
- **Never, anywhere in this code:** end a process by image name; send a key without checking the foreground window first; delete a snapshot in the run that made it; pass `-handsoff` without `-run_until`.
- **Values fixed by the spec:** keep the last **5** snapshots; default backup root `/mnt/d/vic3_qa_backups`; GPU busy at mean utilization **≥ 50%** or memory in use **> half**, from **5** samples **1 s** apart; someone is at the machine if there was input the helper did not send within **30 s**; wait for the foreground up to **120 s**; console key scancode **0x29**, Enter **0x1C**; debugger on `127.0.0.1:6111`; a log flush needs **≥ 4 KB** of output and the verified way is the console command `help ndefines.ngui`.
- **The owner's launch rule** (§ 2): no launch without the owner's go-ahead for this session. Only Task 9 launches anything, and it opens by asking.
- **Branches and PRs:** a sparse worktree per PR (`docs/guides/git_workflow.md` § "Parallel checkouts"), `--base main` always, `scripts/preflight.py --quick` before each push, a "Player guide: no player-facing change" line in each body, and the owner merges. PR 1 is Tasks 1–4, PR 2 is Tasks 5–8 (branched from PR 1's tip), PR 3 is Task 9's results.
- **Commits** are thematic and staged by path, never `git commit -a`.

## Review Focus

1. **The game crashes, or shows a crash dialog, in the middle of a command.** Expected: the console raises `game_gone` at once instead of waiting out its timeouts, and the restore still runs. Pinned in Task 7 (`test_game_exit_mid_command_raises_game_gone`).
2. **The driver dies while its game is still up.** Expected: the next invocation recognizes that process as its own by process id and creation time, does not restore under a running game, and never ends a different process that reuses the id. Pinned in Task 3 (`test_recover_leaves_a_run_whose_game_is_still_up`), Task 4 (`test_orphan_of_an_unfinished_run_is_ours`) and Task 5 (`test_kill_refuses_a_reused_pid`).
3. **The log rotates past all six generations between two reads.** Expected: no crash, no line reported twice, one marker line saying lines were lost. Pinned in Task 6 (`test_flood_past_six_generations_reports_the_gap`).
4. **Console text with a newline, quotes or non-ASCII letters.** Expected: a newline is refused before any key is sent; the rest is typed as given. Pinned in Task 7 (`test_newline_is_refused_before_any_key`, `test_quotes_and_non_ascii_are_typed_verbatim`).
5. **Save names with spaces and commas** (`TEST_FAIL_te_qa_fixture_2 January, 1836.v3`, `new york_1940_07_29.v3`). Expected: snapshotted, restored and removed like any other. Pinned in Task 2 (`test_names_with_spaces_and_commas`) and Task 3 (`test_removes_only_what_the_run_created`).

---

## File structure

| File | Responsibility |
|---|---|
| `path_constants.py` (modify) | Two new lazy paths: `game_user_data_path`, `game_qa_backup_path` |
| `game_qa/__init__.py` | Empty but for a one-line docstring |
| `game_qa/snapshot.py` | Take a snapshot of the owner's files into a content store; the run journal |
| `game_qa/restore.py` | Compare, restore, hold, recover unfinished runs, prune |
| `game_qa/gate.py` | GPU reading, process identity, the launch gate's decision |
| `game_qa/__main__.py` | The command line for part 1: `snapshot`, `restore`, `recover`, `held`, `gate`, `selftest-restore` |
| `game_qa/win_helper.py` | Windows side: launch, window, focus, keys, screenshot, kill, TCP relay. One pure `handle()` over a backend object |
| `game_qa/helper.py` | WSL side: the `Helper` protocol and `ProcessHelper`, which runs `win_helper.py` |
| `game_qa/logtail.py` | Follow a log across rotation; parse console and `debug_log` lines |
| `game_qa/console.py` | One console command as a confirmed round trip |
| `game_qa/dap.py` | Debug Adapter Protocol framing and a small client |
| `game_qa/fakes.py` | `FakeHelper` and `FakeBackend`, shared by the tests |
| `test_game_qa_snapshot.py`, `_restore.py`, `_gate.py`, `_win_helper.py`, `_logtail.py`, `_console.py`, `_dap.py` | One test file per module |
| `test_fixtures/game_qa/` | Recorded log lines and debugger messages, copied from `docs/testing/game_qa_probe/captures/` |

---

### Task 1: The two path constants

**Files:**
- Modify: `path_constants.py` (`_LAZY_SPECS` and the derived-path block below it)
- Test: `test_path_constants.py`

**Interfaces:**
- Produces: `path_constants.game_user_data_path: str` (key `game_user_data_path`, env `VIC3_USER_DATA`; when neither is set, the parent folder of `game_logs_path`) and `path_constants.game_qa_backup_path: str` (key `game_qa_backup_path`, env `VIC3_QA_BACKUPS`; when neither is set, `/mnt/d/vic3_qa_backups`).

- [ ] **Step 1: Write the failing tests** in `test_path_constants.py`, inside its `isolated()` helper, and add both names to `LAZY_NAMES`:

```python
def test_user_data_defaults_to_the_logs_parent(self):
    with isolated({"VIC3_GAME_LOGS": "/x/Victoria 3/logs"}):
        self.assertEqual(pc.game_user_data_path, "/x/Victoria 3")

def test_user_data_env_wins(self):
    with isolated({"VIC3_GAME_LOGS": "/x/Victoria 3/logs", "VIC3_USER_DATA": "/y"}):
        self.assertEqual(pc.game_user_data_path, "/y")

def test_backup_root_default_and_env(self):
    with isolated({}):
        self.assertEqual(pc.game_qa_backup_path, "/mnt/d/vic3_qa_backups")
    with isolated({"VIC3_QA_BACKUPS": "/b"}):
        self.assertEqual(pc.game_qa_backup_path, "/b")
```

- [ ] **Step 2: Run** `…/python -m pytest test_path_constants.py -q`. Expected: the three new tests fail with `AttributeError`.
- [ ] **Step 3: Implement.** Both resolve lazily like their neighbours; neither may raise when only CI's five dummy variables are set (the existing `isolated` tests show the pattern for a derived default).
- [ ] **Step 4: Run** the file again. Expected: all pass.
- [ ] **Step 5: Commit** `path_constants.py test_path_constants.py`: "Path constants for the game's user-data folder and the QA backup root".

---

### Task 2: Snapshot

**Files:**
- Create: `game_qa/__init__.py`, `game_qa/snapshot.py`
- Test: `test_game_qa_snapshot.py`

**Interfaces:**
- Produces:

```python
SNAPSHOT_SET = ("save games/autosave*.v3", "continue_game.json", "console_history.txt",
                "pdx_settings.json", "content_load.json", "logs/*")   # files only, never recursive

@dataclass(frozen=True)
class Entry: size: int; mtime_ns: int; sha256: str

@dataclass
class Snapshot:
    id: str                      # UTC, "20261110T204035Z"; a second snapshot in the same second gets "-2"
    dir: Path                    # <backup_root>/snapshots/<id>
    files: dict[str, Entry]      # user-data-relative POSIX path -> entry
    listing: frozenset[str]      # every file directly in user_data, save games/ and logs/ when taken

class BackupRootError(Exception): ...

def take(user_data: Path, backup_root: Path, extra: Sequence[str] = (), now: datetime | None = None) -> Snapshot
def load(snapshot_dir: Path) -> Snapshot
def record(snap: Snapshot, event: str, now: datetime | None = None, **fields) -> None
def journal(snap: Snapshot) -> list[dict]        # [{"event": "started", "at": "<iso>", ...}, ...]
def all_snapshots(backup_root: Path) -> list[Snapshot]   # oldest first
```

- Layout: file contents live once in `<backup_root>/store/<sha256[:2]>/<sha256>`; a snapshot is `manifest.json` (files and listing) plus `journal.jsonl`. `extra` holds user-data-relative paths of saves the run will load.
- Journal events used by later tasks: `started` (`pid`, `created`), `heartbeat`, `game_exited`, `restored`, `held` (`reason`).

- [ ] **Step 1: Write the failing tests.** Each builds a user-data folder in a temp dir with a helper `make_user_data(root)` that writes `save games/autosave.v3`, `autosave_1.v3`, `continue_game.json`, `console_history.txt`, `pdx_settings.json`, `content_load.json`, `logs/debug.log`, `logs/error.log`, and `save games/mine.v3` (not in the set).

```python
def test_takes_the_set_and_nothing_else(self):
    snap = snapshot.take(self.user, self.backups)
    self.assertIn("save games/autosave_1.v3", snap.files)
    self.assertIn("logs/debug.log", snap.files)
    self.assertNotIn("save games/mine.v3", snap.files)
    self.assertIn("save games/mine.v3", snap.listing)

def test_extra_saves_are_taken(self):
    snap = snapshot.take(self.user, self.backups, extra=["save games/mine.v3"])
    self.assertIn("save games/mine.v3", snap.files)

def test_names_with_spaces_and_commas(self):
    name = "save games/TEST_FAIL_te_qa_fixture_2 January, 1836.v3"
    (self.user / name).write_bytes(b"x" * 10)
    snap = snapshot.take(self.user, self.backups, extra=[name])
    self.assertEqual(snap.files[name].size, 10)

def test_unchanged_file_is_not_copied_again(self):
    first = snapshot.take(self.user, self.backups)
    stored = sorted(p.name for p in (self.backups / "store").rglob("*") if p.is_file())
    second = snapshot.take(self.user, self.backups)
    self.assertEqual(stored, sorted(p.name for p in (self.backups / "store").rglob("*") if p.is_file()))
    self.assertEqual(first.files, second.files)

def test_manifest_records_the_content_hash(self):
    # size and time only decide whether take() may skip a copy; Task 3 decides overwrites by this hash
    snap = snapshot.take(self.user, self.backups)
    entry = snap.files["continue_game.json"]
    self.assertEqual(entry.sha256, hashlib.sha256((self.user / "continue_game.json").read_bytes()).hexdigest())

def test_load_round_trips(self):
    snap = snapshot.take(self.user, self.backups)
    self.assertEqual(snapshot.load(snap.dir).files, snap.files)

def test_journal_appends_in_order(self):
    snap = snapshot.take(self.user, self.backups)
    snapshot.record(snap, "started", pid=7, created="2026-11-10T12:00:00Z")
    snapshot.record(snap, "heartbeat")
    self.assertEqual([e["event"] for e in snapshot.journal(snap)], ["started", "heartbeat"])
    self.assertEqual(snapshot.journal(snap)[0]["pid"], 7)

def test_missing_backup_parent_refuses(self):
    with self.assertRaises(snapshot.BackupRootError):
        snapshot.take(self.user, Path("/nonexistent/drive/backups"))

def test_too_little_free_space_refuses(self):
    with mock.patch("shutil.disk_usage", return_value=(10**12, 10**12, 5)):
        with self.assertRaises(snapshot.BackupRootError):
            snapshot.take(self.user, self.backups)
```

- [ ] **Step 2: Run** the file. Expected: every test fails on `ModuleNotFoundError: game_qa`.
- [ ] **Step 3: Implement `take`, `load`, `record`, `journal`, `all_snapshots`.** `take` may reuse the previous snapshot's hash for a file whose size and `mtime_ns` both match, and must hash everything else. It creates `backup_root` itself but refuses when its parent is missing, and refuses when free space is less than the bytes it has to copy plus 1 GB. Write `manifest.json` last, by rename from a temp name, so a half-written snapshot never loads.
- [ ] **Step 4: Run** the file. Expected: all pass.
- [ ] **Step 5: Commit** `game_qa/__init__.py game_qa/snapshot.py test_game_qa_snapshot.py`: "Game QA: snapshot the owner's saves, settings and logs into a content store".

---

### Task 3: Compare, restore, hold, recover, prune

**Files:**
- Create: `game_qa/restore.py`
- Test: `test_game_qa_restore.py`

**Interfaces:**
- Consumes: Task 2's `Snapshot`, `take`, `record`, `journal`, `all_snapshots`, `SNAPSHOT_SET`.
- Produces:

```python
HARNESS_CREATED = ("save games/TEST_FAIL_*.v3", "save games/te_qa_*.v3", "tests.txt")
HARNESS_KEPT = ("save games/te_qa_fixture_*.v3",)
SLACK_SECONDS = 2.0

@dataclass
class Diff: changed: list[str]; missing: list[str]; added_in_set: list[str]; created: list[str]

@dataclass
class Outcome: restored: list[str]; removed: list[str]; held: bool; reason: str
# reason: "" | "other_game_running" | "modified_after_exit" | "game_still_up"

def compare(snap: Snapshot, user_data: Path) -> Diff
def restore(snap: Snapshot, user_data: Path, other_game_running: bool,
            run_logs_dir: Path | None = None, now: datetime | None = None) -> Outcome
def unfinished(backup_root: Path) -> list[Snapshot]      # "started", and neither "restored" nor "held"
def recover(backup_root: Path, user_data: Path, other_game_running: bool,
            own_game_up: Callable[[dict], bool]) -> list[tuple[str, Outcome]]
def held(backup_root: Path) -> list[Snapshot]
def prune(backup_root: Path, keep: int = 5, current: str | None = None) -> list[str]   # ids removed
```

- Rules (spec § 5.3):
  - `changed` is decided by the live file's SHA-256 against the manifest. Size and time are never enough to call a file unchanged here.
  - `added_in_set` is a file that matches `SNAPSHOT_SET` now and is not in the manifest (an autosave the run pushed in, a log the run created).
  - `created` is a file that matches `HARNESS_CREATED`, does not match `HARNESS_KEPT`, and is not in `snap.listing`.
  - The reference time is the journal's `game_exited`, else its last `heartbeat`, else `started`. If `other_game_running`, or any file in `changed`, `added_in_set` or `created` was modified more than `SLACK_SECONDS` after the reference time, `restore` changes nothing, records `held` with the reason, and returns `held=True`.
  - Otherwise it copies `changed` and `missing` back from the store with their recorded `mtime_ns`, removes `added_in_set` and `created`, records `restored`, and returns what it did. With `run_logs_dir` it first copies the live `logs/*` there.
  - `recover` runs `restore` for each unfinished snapshot, oldest first, except one whose `started` entry `own_game_up` says is still running: that one is left untouched and reported with reason `game_still_up`.
  - `prune` removes the oldest snapshots beyond `keep` among those whose journal ends in `restored`; it never removes `current`, a held one or an unfinished one; then it deletes store files no remaining manifest names.

- [ ] **Step 1: Write the failing tests** (same `make_user_data` helper; `finish(snap)` records `started` then `game_exited` at the current time):

```python
def test_untouched_folder_restores_nothing(self):
    snap = self.run_started(); finish(snap)
    out = restore.restore(snap, self.user, other_game_running=False)
    self.assertEqual((out.restored, out.removed, out.held), ([], [], False))
    self.assertEqual(snapshot.journal(snap)[-1]["event"], "restored")

def test_rotation_is_put_back_as_a_set(self):
    snap = self.run_started()
    old = (self.user / "save games/autosave.v3").read_bytes()
    os.replace(self.user / "save games/autosave.v3", self.user / "save games/autosave_2.v3")
    (self.user / "save games/autosave.v3").write_bytes(b"the run's autosave")
    finish(snap)
    out = restore.restore(snap, self.user, other_game_running=False)
    self.assertEqual((self.user / "save games/autosave.v3").read_bytes(), old)
    self.assertFalse((self.user / "save games/autosave_2.v3").exists())
    self.assertIn("save games/autosave_2.v3", out.removed)

def test_same_size_and_time_different_bytes_is_restored(self):
    snap = self.run_started()
    p = self.user / "continue_game.json"; st = p.stat(); before = p.read_bytes()
    p.write_bytes(bytes(b ^ 1 for b in before)); os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
    finish(snap)
    restore.restore(snap, self.user, other_game_running=False)
    self.assertEqual(p.read_bytes(), before)

def test_restored_file_keeps_its_recorded_time(self):
    snap = self.run_started(); p = self.user / "console_history.txt"
    p.write_text("event x\n"); finish(snap)
    restore.restore(snap, self.user, other_game_running=False)
    self.assertEqual(p.stat().st_mtime_ns, snap.files["console_history.txt"].mtime_ns)

def test_removes_only_what_the_run_created(self):
    (self.user / "save games/te_qa_old.v3").write_bytes(b"before the run")
    snap = self.run_started()
    for name in ("TEST_FAIL_te_qa_fixture_2 January, 1836.v3", "te_qa_scratch.v3", "te_qa_fixture_abc.v3"):
        (self.user / "save games" / name).write_bytes(b"x")
    (self.user / "tests.txt").write_text("Tests:\n")
    finish(snap)
    out = restore.restore(snap, self.user, other_game_running=False)
    self.assertEqual(sorted(out.removed), ["save games/TEST_FAIL_te_qa_fixture_2 January, 1836.v3",
                                           "save games/te_qa_scratch.v3", "tests.txt"])
    self.assertTrue((self.user / "save games/te_qa_fixture_abc.v3").exists())
    self.assertTrue((self.user / "save games/te_qa_old.v3").exists())
    self.assertTrue((self.user / "save games/mine.v3").exists())

def test_run_logs_are_copied_out_before_the_put_back(self):
    snap = self.run_started(); (self.user / "logs/debug.log").write_text("the run's log\n"); finish(snap)
    restore.restore(snap, self.user, other_game_running=False, run_logs_dir=self.tmp / "runlogs")
    self.assertEqual((self.tmp / "runlogs/debug.log").read_text(), "the run's log\n")
    self.assertNotEqual((self.user / "logs/debug.log").read_text(), "the run's log\n")

def test_other_game_running_holds(self):
    snap = self.run_started(); (self.user / "continue_game.json").write_text("{}"); finish(snap)
    out = restore.restore(snap, self.user, other_game_running=True)
    self.assertEqual((out.held, out.reason, out.restored), (True, "other_game_running", []))
    self.assertEqual((self.user / "continue_game.json").read_text(), "{}")

def test_file_modified_after_exit_holds(self):
    snap = self.run_started(); finish(snap, at=NOW)
    p = self.user / "save games/autosave.v3"; p.write_bytes(b"the owner played since")
    os.utime(p, (NOW.timestamp() + 600, NOW.timestamp() + 600))
    out = restore.restore(snap, self.user, other_game_running=False)
    self.assertEqual((out.held, out.reason), (True, "modified_after_exit"))
    self.assertEqual(p.read_bytes(), b"the owner played since")

def test_dead_run_uses_its_last_heartbeat(self):
    snap = self.run_started(at=NOW); snapshot.record(snap, "heartbeat", now=NOW + timedelta(minutes=5))
    p = self.user / "continue_game.json"; p.write_text("{}")
    os.utime(p, ((NOW + timedelta(minutes=4)).timestamp(),) * 2)
    out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: False)
    self.assertEqual(out[0][1].held, False)

def test_recover_leaves_a_run_whose_game_is_still_up(self):
    snap = self.run_started(); (self.user / "continue_game.json").write_text("{}")
    out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: True)
    self.assertEqual(out[0][1].reason, "game_still_up")
    self.assertEqual((self.user / "continue_game.json").read_text(), "{}")
    self.assertEqual([s.id for s in restore.unfinished(self.backups)], [snap.id])

def test_prune_keeps_five_and_never_held_unfinished_or_current(self):
    done = [self.finished_run() for _ in range(7)]
    held_one = self.held_run(); open_one = self.run_started(); current = self.finished_run()
    removed = restore.prune(self.backups, keep=5, current=current.id)
    self.assertEqual(removed, [s.id for s in done[:3]])   # 7 done + current = 8 restored; keep 5 incl. current
    for s in (held_one, open_one, current):
        self.assertTrue(s.dir.exists())

def test_every_kept_snapshot_still_restores_after_a_prune(self):
    first = self.finished_run(); (self.user / "continue_game.json").write_text("v2")
    for _ in range(6): self.finished_run()
    restore.prune(self.backups, keep=5)
    for snap in snapshot.all_snapshots(self.backups):
        for entry in snap.files.values():
            self.assertTrue((self.backups / "store" / entry.sha256[:2] / entry.sha256).is_file())
```

- [ ] **Step 2: Run** the file. Expected: all fail on the missing module.
- [ ] **Step 3: Implement** `compare`, `restore`, `unfinished`, `recover`, `held`, `prune`.
- [ ] **Step 4: Run** `test_game_qa_restore.py` and `test_game_qa_snapshot.py`. Expected: all pass.
- [ ] **Step 5: Commit** `game_qa/restore.py test_game_qa_restore.py`: "Game QA: put the owner's files back after a run, or hold when they have changed since".

---

### Task 4: The launch gate and the part 1 command line

**Files:**
- Create: `game_qa/gate.py`, `game_qa/__main__.py`
- Test: `test_game_qa_gate.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces:

```python
@dataclass(frozen=True)
class GpuSample: util_pct: float; mem_used_mib: int; mem_total_mib: int
@dataclass(frozen=True)
class ProcId: pid: int; created: str          # creation time, UTC ISO-8601, as Windows reports it

@dataclass
class Gate: ok: bool; reason: str; detail: str
# reason: "ok" | "no_permission" | "backup_root" | "other_game" | "gpu_busy"

def parse_nvidia_smi(text: str) -> list[GpuSample]
def sample_gpu(run=subprocess.run, sleep=time.sleep, n: int = 5, interval: float = 1.0) -> list[GpuSample]
def gpu_busy(samples: Sequence[GpuSample]) -> bool
def list_games(run=subprocess.run) -> list[ProcId]
def ours_from_journals(backup_root: Path) -> set[ProcId]     # "started" entries of unfinished runs
def check(permission: str, games: Sequence[ProcId], ours: set[ProcId], samples: Sequence[GpuSample],
          owner_confirmed_busy: bool, backup_error: str | None) -> Gate
```

- `sample_gpu` runs `nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits` and returns `[]` when the program is missing or fails. `gpu_busy([])` is `True`: no reading counts as busy.
- `list_games` runs `powershell.exe -NoProfile -Command "Get-Process victoria3 -ErrorAction SilentlyContinue | ForEach-Object { '{0} {1}' -f $_.Id, $_.StartTime.ToUniversalTime().ToString('o') }"`.
- `check` tests in this order and returns the first that fails: blank `permission`; `backup_error`; a game not in `ours`; `gpu_busy` without `owner_confirmed_busy`.
- Command line, each verb printing one JSON object and exiting 0 on success, 2 on a refusal: `snapshot [--save NAME]…`, `restore <id> [--run-logs DIR]`, `recover`, `held`, `gate --permission TEXT [--owner-confirmed-busy]`, `selftest-restore`. `selftest-restore` takes a snapshot of the real user-data folder, restores it into an empty temp folder, and reports whether every file's hash matches its manifest entry; it changes nothing in the user-data folder.

- [ ] **Step 1: Write the failing tests:**

```python
IDLE = [gate.GpuSample(14, 1607, 10240)] * 5

def test_parse(self):
    self.assertEqual(gate.parse_nvidia_smi("14, 1607, 10240\n"), [gate.GpuSample(14.0, 1607, 10240)])

def test_idle_is_not_busy(self):
    self.assertFalse(gate.gpu_busy(IDLE))
def test_mean_of_fifty_is_busy(self):
    self.assertTrue(gate.gpu_busy([gate.GpuSample(u, 1000, 10240) for u in (0, 100, 0, 100, 50)]))
def test_over_half_the_memory_is_busy(self):
    self.assertTrue(gate.gpu_busy([gate.GpuSample(1, 5121, 10240)] * 5))
def test_no_reading_is_busy(self):
    self.assertTrue(gate.gpu_busy([]))
def test_missing_nvidia_smi_gives_no_samples(self):
    def run(*a, **k): raise FileNotFoundError
    self.assertEqual(gate.sample_gpu(run=run, sleep=lambda s: None), [])

def test_blank_permission_refuses_first(self):
    g = gate.check("  ", [], set(), [], False, "no backup root")
    self.assertEqual((g.ok, g.reason), (False, "no_permission"))
def test_backup_error_refuses(self):
    self.assertEqual(gate.check("asked 12:40", [], set(), IDLE, False, "D: is missing").reason, "backup_root")
def test_a_game_that_is_not_ours_refuses(self):
    theirs = gate.ProcId(100, "2026-11-10T08:00:00.0000000Z")
    self.assertEqual(gate.check("session grant", [theirs], set(), IDLE, True, None).reason, "other_game")
def test_orphan_of_an_unfinished_run_is_ours(self):
    mine = gate.ProcId(100, "2026-11-10T12:00:00.0000000Z")
    self.assertTrue(gate.check("session grant", [mine], {mine}, IDLE, False, None).ok)
def test_same_pid_other_creation_time_is_not_ours(self):
    mine = gate.ProcId(100, "2026-11-10T12:00:00.0000000Z")
    reused = gate.ProcId(100, "2026-11-10T15:00:00.0000000Z")
    self.assertEqual(gate.check("session grant", [reused], {mine}, IDLE, False, None).reason, "other_game")
def test_busy_gpu_refuses_until_the_owner_confirms(self):
    busy = [gate.GpuSample(95, 9000, 10240)] * 5
    self.assertEqual(gate.check("session grant", [], set(), busy, False, None).reason, "gpu_busy")
    self.assertTrue(gate.check("session grant", [], set(), busy, True, None).ok)
```

Plus two command-line tests that call `game_qa.__main__.main([...])` with `VIC3_USER_DATA` and `VIC3_QA_BACKUPS` pointed at temp folders: `snapshot` then `restore <id>` leaves a modified `continue_game.json` as it was, and `selftest-restore` prints `"match": true` and leaves the user-data folder's listing and times unchanged.

- [ ] **Step 2: Run** `test_game_qa_gate.py`. Expected: all fail on the missing module.
- [ ] **Step 3: Implement** `gate.py` and `__main__.py`.
- [ ] **Step 4: Run** the three `test_game_qa_*.py` files, then `…/python scripts/preflight.py --quick`. Expected: all pass, 15 checks ok.
- [ ] **Step 5: Document.** In `docs/guides/python_tools.md` § "Driving the game from a session", replace the hand-backup bullet with the commands: `python3 -m game_qa gate --permission …`, `snapshot`, and after the game has closed `restore <id>`; say that `recover` and `held` exist. One paragraph.
- [ ] **Step 6: Commit** `game_qa/gate.py game_qa/__main__.py test_game_qa_gate.py docs/guides/python_tools.md`: "Game QA: the launch gate and the snapshot command line". Push and open **PR 1**.

---

### Task 5: The Windows helper

**Files:**
- Create: `game_qa/win_helper.py`, `game_qa/helper.py`, `game_qa/fakes.py`
- Test: `test_game_qa_win_helper.py`
- Read first: `docs/testing/game_qa_probe/powershell/lib.ps1` and `keys.ps1` (the Win32 calls that worked)

**Interfaces:**
- Consumes: `gate.ProcId`.
- Produces, in `win_helper.py` (no package imports):

```python
class State: ours: dict[int, str]; last_sent_tick: int; last_foreign_tick: int; sock: object | None
def handle(req: dict, backend, state: State) -> dict      # never raises: {"id": n, "ok": False, "error": "<code>"}
def main() -> None                                        # JSON lines on stdin and stdout, flushed per line
```

- Requests (`op`) and their results:

| `op` | Fields | Result or error |
|---|---|---|
| `ping` | | `python` (version string) |
| `launch` | `exe`, `args` (list), `cwd` | `pid`, `created`; the pair is added to `state.ours` |
| `adopt` | `pid`, `created` | adds to `state.ours` only if the live process's creation time equals `created`; else `not_ours` |
| `window` | `pid` | `exists`, `hwnd`, `title`, `foreground`, `responding`, `client` `[x, y, w, h]` |
| `idle_ms` | | `idle_ms`: milliseconds since the latest input the helper did not send, as far as it has seen |
| `focus` | `pid` | `foreground` after trying |
| `keys` | `pid`, `steps` | each step is `{"scan": int}`, `{"text": str}` or `{"wait_ms": int}`. Before **every** step the foreground window must be `pid`'s, else `not_foreground` and no further step. A `text` holding `\n` or `\r` is `bad_text` before any step is sent |
| `screenshot` | `pid`, `path`, `max_width` | `path`, `width`, `height`; a PNG written with `zlib` and `struct`, no third-party module |
| `kill` | `pid` | `not_ours` unless `pid` is in `state.ours` **and** the live process's creation time equals the recorded one |
| `tcp_open` / `tcp_send` / `tcp_recv` / `tcp_close` | `port`; `b64`; `timeout_ms` | `127.0.0.1` only; `tcp_recv` returns `b64` (empty on timeout) |

- `backend` is the object that holds every Win32 call (`create_process`, `creation_time`, `window_of`, `foreground_hwnd`, `set_foreground`, `send_scan`, `send_text`, `last_input_tick`, `tick`, `capture`, `terminate`). The real one is built only on Windows; `fakes.FakeBackend` scripts it for the tests.
- In `helper.py`:

```python
class HelperError(Exception):  code: str
@dataclass
class Window: exists: bool; foreground: bool; responding: bool; title: str; client: tuple[int, int, int, int]
class Helper(Protocol):
    def launch(self, exe: str, args: Sequence[str], cwd: str) -> ProcId: ...
    def adopt(self, proc: ProcId) -> None: ...
    def window(self, pid: int) -> Window: ...
    def idle_ms(self) -> int: ...
    def focus(self, pid: int) -> bool: ...
    def keys(self, pid: int, steps: Sequence[dict]) -> None: ...
    def screenshot(self, pid: int, path: Path, max_width: int = 1600) -> Path: ...
    def kill(self, proc: ProcId) -> None: ...
    def tcp_open(self, port: int) -> None: ...
    def tcp_send(self, data: bytes) -> None: ...
    def tcp_recv(self, timeout: float) -> bytes: ...
    def tcp_close(self) -> None: ...
class ProcessHelper:   # implements Helper; __init__(python_exe: str = "python.exe", popen=subprocess.Popen)
def to_windows_path(path: Path, run=subprocess.run) -> str      # wslpath -w
```

- `fakes.FakeHelper` implements `Helper` in memory: a foreground flag, an `idle` value, a list of the steps it was sent, a console-history file it appends typed text to on Enter while its `console_open` flag is set, and a queue of bytes for `tcp_recv`.

- [ ] **Step 1: Write the failing tests** against `handle` with `FakeBackend`:

```python
def test_keys_refused_when_the_game_is_not_in_front(self):
    self.backend.foreground = 999
    out = self.call("keys", pid=7, steps=[{"text": "event x"}, {"scan": 0x1C}])
    self.assertEqual(out["error"], "not_foreground"); self.assertEqual(self.backend.sent, [])

def test_keys_stop_at_the_step_where_focus_is_lost(self):
    self.backend.lose_focus_after = 1
    out = self.call("keys", pid=7, steps=[{"text": "a"}, {"scan": 0x1C}])
    self.assertEqual(out["error"], "not_foreground"); self.assertEqual(self.backend.sent, [("text", "a")])

def test_text_with_a_newline_is_refused_before_any_step(self):
    out = self.call("keys", pid=7, steps=[{"scan": 0x29}, {"text": "a\nb"}])
    self.assertEqual(out["error"], "bad_text"); self.assertEqual(self.backend.sent, [])

def test_kill_refuses_a_process_it_did_not_start(self):
    self.assertEqual(self.call("kill", pid=4242)["error"], "not_ours"); self.assertEqual(self.backend.terminated, [])

def test_kill_refuses_a_reused_pid(self):
    pid = self.call("launch", exe="victoria3.exe", args=[], cwd="C:\\g")["pid"]
    self.backend.creation[pid] = "2026-11-10T15:00:00.0000000Z"       # another process now has the id
    self.assertEqual(self.call("kill", pid=pid)["error"], "not_ours")

def test_adopt_checks_the_creation_time(self):
    self.backend.creation[55] = "A"
    self.assertEqual(self.call("adopt", pid=55, created="B")["error"], "not_ours")
    self.assertTrue(self.call("adopt", pid=55, created="A")["ok"])

def test_idle_discounts_the_helpers_own_keys(self):
    self.backend.now = 100_000; self.backend.last_input = 40_000          # a person, 60 s ago
    self.assertEqual(self.call("idle_ms")["idle_ms"], 60_000)
    self.call("keys", pid=7, steps=[{"scan": 0x29}]); self.backend.now = 101_000   # our key at 100 s
    self.assertEqual(self.call("idle_ms")["idle_ms"], 61_000)

def test_idle_sees_a_person_after_our_keys(self):
    self.call("keys", pid=7, steps=[{"scan": 0x29}])
    self.backend.now += 5_000; self.backend.last_input = self.backend.now - 1_000
    self.assertEqual(self.call("idle_ms")["idle_ms"], 1_000)

def test_tcp_only_to_loopback(self):
    self.assertTrue(self.call("tcp_open", port=6111)["ok"]); self.assertEqual(self.backend.connected, ("127.0.0.1", 6111))

def test_unknown_op_and_bad_json_do_not_raise(self):
    self.assertEqual(self.call("nope")["error"], "unknown_op")
```

Plus, for `helper.py`: `ProcessHelper` with a fake `popen` whose stdout answers scripted lines sends one JSON line per call, raises `HelperError` with the reply's code, and raises `HelperError("helper_gone")` when the pipe closes.

- [ ] **Step 2: Run** the file. Expected: all fail on the missing module.
- [ ] **Step 3: Implement** `handle`, `State`, `main`, the real backend class (constructed only when `sys.platform == "win32"`), `helper.py` and `fakes.py`. `send_scan` uses `SendInput` with `KEYEVENTF_SCANCODE`, `send_text` with `KEYEVENTF_UNICODE` per character, as `lib.ps1` does.
- [ ] **Step 4: Run** the file and `…/python -m compileall -q game_qa`. Expected: pass; the Windows-only calls are not exercised here and are proven in Task 9.
- [ ] **Step 5: Commit** `game_qa/win_helper.py game_qa/helper.py game_qa/fakes.py test_game_qa_win_helper.py`: "Game QA: the Windows-side helper and its refusals".

---

### Task 6: Following the logs

**Files:**
- Create: `game_qa/logtail.py`, `test_fixtures/game_qa/debug_console_lines.txt` (copy of `docs/testing/game_qa_probe/captures/debug_log_console_lines.txt`)
- Test: `test_game_qa_logtail.py`

**Interfaces:**
- Produces:

```python
GAP_MARKER = "<<game_qa: log lines lost in rotation>>"

class LogFollower:
    def __init__(self, path: Path): ...          # e.g. .../logs/debug.log; generations are debug.1.log … debug.5.log
    def poll(self) -> list[str]: ...             # complete new lines, oldest first, each reported once

@dataclass
class Parsed: time: str; kind: str; text: str; file: str | None; lineno: int | None
# kind: "command" | "success" | "failure" | "debug_log" | "other"
def parse(line: str) -> Parsed
@dataclass(frozen=True)
class Pending: numeric_id: int; event_id: str; options: int
def pending_events(reply_lines: Sequence[str]) -> list[Pending]
```

- Line shapes (verified, in the fixture): `[12:51:40][console.cpp:1175]: Running console command: event te_qa_probe.2` is a command; `[..][console.cpp:1203]: console_success: 10 te_qa_probe.2 options=3` a success; `console_failure:` a failure; `[..][jomini_effect_impl.cpp:459]: events/te_qa_probe_events.txt:44: TE_QA_PROBE option=C country=FRA` a `debug_log` with `file` and `lineno`. Match on the `console.cpp` and `jomini_effect_impl.cpp` names, not their line numbers, which move between patches.
- The game writes in blocks that can end mid-line: a tail with no newline is held until its newline arrives. Decode as UTF-8 with `errors="replace"`.
- Rotation: the follower remembers its offset and the first 64 bytes of the file it is reading. When the live file is shorter than the offset or starts differently, it finds its old file among the numbered generations by those 64 bytes, reads the rest of it, then every newer generation in full, oldest first, then the live file from 0. If its old file is gone, it yields `GAP_MARKER` once and reads every generation present.

- [ ] **Step 1: Write the failing tests:**

```python
def test_reports_each_line_once(self): ...            # append twice, poll twice: second poll has only the new lines
def test_holds_a_partial_last_line(self):
    self.append("[12:00:00][console.cpp:1203]: console_success: select_event_option [option index, or list] [<event id, default ")
    self.assertEqual(self.follower.poll(), [])
    self.append("oldest pending>]\n")
    self.assertEqual(len(self.follower.poll()), 1)
def test_rotation_mid_read_loses_and_repeats_nothing(self):
    self.append("a\nb\n"); self.assertEqual(self.follower.poll(), ["a", "b"])
    self.append("c\n"); self.rotate(); self.append("d\n")          # debug.log -> debug.1.log, new debug.log
    self.assertEqual(self.follower.poll(), ["c", "d"])
def test_two_rotations_between_polls(self): ...        # lines from .2, then .1, then live, in order
def test_flood_past_six_generations_reports_the_gap(self):
    self.append("a\n"); self.follower.poll()
    for i in range(7): self.rotate(); self.append("gen%d\n" % i)
    got = self.follower.poll()
    self.assertEqual(got[0], logtail.GAP_MARKER); self.assertEqual(got.count(logtail.GAP_MARKER), 1)
    self.assertEqual(got[-1], "gen6"); self.assertNotIn("a", got)
def test_parse_the_recorded_session(self):
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    kinds = [logtail.parse(l).kind for l in lines]
    self.assertIn("command", kinds); self.assertIn("success", kinds); self.assertIn("debug_log", kinds)
    opt = next(p for p in map(logtail.parse, lines) if "option=C country=FRA" in p.text)
    self.assertEqual((opt.file, opt.lineno), ("events/te_qa_probe_events.txt", 44))
def test_pending_events(self):
    self.assertEqual(logtail.pending_events(["2063597726 un_vote.3 options=3", "184549455 te_qa_probe.2 options=3"]),
                     [logtail.Pending(2063597726, "un_vote.3", 3), logtail.Pending(184549455, "te_qa_probe.2", 3)])
    self.assertEqual(logtail.pending_events(["No pending events"]), [])
```

- [ ] **Step 2: Run.** Expected: fail on the missing module.
- [ ] **Step 3: Implement** `LogFollower`, `parse`, `pending_events`.
- [ ] **Step 4: Run.** Expected: pass.
- [ ] **Step 5: Commit** `game_qa/logtail.py test_game_qa_logtail.py test_fixtures/game_qa/debug_console_lines.txt`: "Game QA: follow the game's logs across rotation and parse console lines".

---

### Task 7: The console round trip

**Files:**
- Create: `game_qa/console.py`
- Modify: `game_qa/fakes.py` (`FakeHelper` gains what the tests below use: `on(text, success=…, failure=…)` writing the reply lines to its `debug.log` when that text is entered, `console_open`, `console_never_opens`, `history_skips_repeats`, `exit_after_steps`, `foreground`, `idle`, `focus_calls`, `steps`, and `clock()` / `sleep()` as one fake clock; its `debug.log` writes are held back until a `help ndefines.ngui` is entered, as the real log's are)
- Test: `test_game_qa_console.py`

**Interfaces:**
- Consumes: `Helper`, `HelperError`, `Window` (Task 5), `fakes.FakeHelper`, `LogFollower`, `parse` (Task 6), `ProcId`.
- Produces:

```python
SCAN_CONSOLE, SCAN_ENTER = 0x29, 0x1C
FLUSH_COMMAND = "help ndefines.ngui"
PROBE_COMMAND = "select_event_option list"
PERSON_IDLE_MS, FOREGROUND_WAIT_S = 30_000, 120.0

class ConsoleError(Exception): code: str
# "bad_text" | "not_foreground" | "no_ack" | "no_reply" | "game_gone"

@dataclass
class Reply: command: str; ok: bool | None; lines: list[str]

class Console:
    def __init__(self, helper: Helper, proc: ProcId, history: Path, log: LogFollower,
                 sleep=time.sleep, clock=time.monotonic): ...
    def ensure_open(self, timeout: float = 30.0) -> None
    def run(self, text: str, reply: bool = True, timeout: float = 30.0) -> Reply
```

- Before any keys (`_front`): if the game's window does not exist or is not responding for 10 s, `game_gone`. If it is the foreground window, go on. Otherwise, while `helper.idle_ms() < PERSON_IDLE_MS`, wait one second and look again, up to `FOREGROUND_WAIT_S`, then `not_foreground`; once nobody is at the machine, `helper.focus`, and `not_foreground` if that fails.
- `run`: refuse a blank text or one with `\n` or `\r` (`bad_text`) before touching the helper. Type the text and Enter. **Arrival** is the history file growing with the text as its new last line, within 5 s. With no arrival, call `ensure_open` and type once more; then `no_ack`. If the same text was also the previous command, arrival is instead its `Running console command:` line in the log after a flush (the history file may not repeat a command; Task 9 checks).
- With `reply=True`: type `FLUSH_COMMAND` (arrival only), then poll the log until the text's `command` line and, after it, the flush's `command` line have both appeared. `Reply.lines` are the `success` and `failure` texts between the two; `ok` is `False` if any is a failure, `True` if there is at least one success and no failure, `None` if neither. No such pair within `timeout`: `no_reply`.
- `ensure_open` never presses the console key first: it types `PROBE_COMMAND` and looks for its arrival within 3 s; only without one does it press `SCAN_CONSOLE` and try again, until `timeout`.

- [ ] **Step 1: Write the failing tests** with `FakeHelper` (its fake clock advances on `sleep`; its history file and a temp `debug.log` stand in for the game):

```python
def test_round_trip_returns_the_reply(self):
    self.game.console_open = True
    self.game.on("tag FRA", success=["Now Playing - France"])
    r = self.console.run("tag FRA")
    self.assertEqual((r.ok, r.lines), (True, ["Now Playing - France"]))

def test_failure_reply(self):
    self.game.console_open = True
    self.game.on("save x", failure=["Command available only for developers."])
    self.assertIs(self.console.run("save x").ok, False)

def test_newline_is_refused_before_any_key(self):
    with self.assertRaises(console.ConsoleError) as e: self.console.run("event a\nevent b")
    self.assertEqual(e.exception.code, "bad_text"); self.assertEqual(self.game.steps, [])

def test_quotes_and_non_ascii_are_typed_verbatim(self):
    self.game.console_open = True
    self.console.run('event "é".1', reply=False)
    self.assertIn({"text": 'event "é".1'}, self.game.steps)

def test_closed_console_is_opened_and_the_command_retyped(self):
    self.game.console_open = False
    self.game.on("tag FRA", success=["Now Playing - France"])
    self.assertTrue(self.console.run("tag FRA").ok)
    self.assertEqual(self.game.steps.count({"scan": 0x29}), 1)

def test_open_console_is_never_toggled(self):
    self.game.console_open = True
    self.console.ensure_open()
    self.assertNotIn({"scan": 0x29}, self.game.steps)

def test_person_at_the_machine_makes_it_wait_then_fail(self):
    self.game.foreground = False; self.game.idle = 2_000        # stays 2 s: someone keeps typing
    with self.assertRaises(console.ConsoleError) as e: self.console.run("tag FRA")
    self.assertEqual(e.exception.code, "not_foreground")
    self.assertEqual(self.game.steps, []); self.assertEqual(self.game.focus_calls, 0)
    self.assertGreaterEqual(self.game.clock(), 120.0)

def test_nobody_at_the_machine_takes_the_foreground_back(self):
    self.game.foreground = False; self.game.idle = 45_000; self.game.console_open = True
    self.console.run("tag FRA", reply=False)
    self.assertEqual(self.game.focus_calls, 1)

def test_no_ack_after_one_retry(self):
    self.game.console_open = False; self.game.console_never_opens = True
    with self.assertRaises(console.ConsoleError) as e: self.console.run("tag FRA")
    self.assertEqual(e.exception.code, "no_ack")

def test_game_exit_mid_command_raises_game_gone(self):
    self.game.console_open = True; self.game.exit_after_steps = 1
    with self.assertRaises(console.ConsoleError) as e: self.console.run("tag FRA")
    self.assertEqual(e.exception.code, "game_gone")
    self.assertLess(self.game.clock(), 30.0)

def test_repeated_command_acks_from_the_log(self):
    self.game.console_open = True; self.game.history_skips_repeats = True
    self.console.run("select_event_option list"); self.console.run("select_event_option list")
```

- [ ] **Step 2: Run.** Expected: fail on the missing module.
- [ ] **Step 3: Implement** `Console`.
- [ ] **Step 4: Run.** Expected: pass.
- [ ] **Step 5: Commit** `game_qa/console.py test_game_qa_console.py`: "Game QA: a console command as a confirmed round trip".

---

### Task 8: The debugger client

**Files:**
- Create: `game_qa/dap.py`, `test_fixtures/game_qa/debugger_messages.json` (the replies of `docs/testing/game_qa_probe/captures/debugger_transcript.txt`, as a JSON list)
- Test: `test_game_qa_dap.py`

**Interfaces:**
- Produces:

```python
def encode(msg: dict) -> bytes            # b"Content-Length: <n>\r\n\r\n" + compact UTF-8 JSON
class Decoder:
    def feed(self, data: bytes) -> list[dict]      # whole messages only; keeps a partial one for the next call

class DebuggerError(Exception): ...
@dataclass
class Eval: ok: bool; raw: str; value: bool | float | None

class Debugger:
    def __init__(self, send: Callable[[bytes], None], recv: Callable[[float], bytes]): ...
    def attach(self, breakpoints: dict[str, list[int]] | None = None) -> dict[str, list[bool]]
    def wait_stopped(self, timeout: float) -> bool
    def evaluate(self, expr: str, frame: int = 0, timeout: float = 30.0) -> Eval
    def scopes(self, frame: int = 0) -> dict[str, dict[str, str]]
    def resume(self) -> None
    def errors(self) -> list[str]                # texts of "output" events with category "stderr", drained
```

- `attach` sends, in the order the probe used: `initialize`, `launch`, one `setBreakpoints` per file (Windows path, `{"line": n}` each), `configurationDone`; it returns each breakpoint's `verified` flag.
- A reply is matched to its request by `request_seq`. Events arrive between a request and its reply, hundreds at a time (one trigger evaluation was followed by about 900 `output` events before its reply): keep reading until the reply or the timeout, storing `output` texts and noting `stopped` and `continued`.
- `Eval.value`: a result starting `yes` is `True`, `no` is `False` (verified: `"yes - Yes: \nYes: is_player; …"`), a result that parses as a number is that `float` (verified: `"21570770.55692"`), anything else `None`. A reply with `success: false` gives `ok=False` and the reply's `message` as `raw` (verified: `"not stopped"`, `"not a valid trigger or script value"`).

- [ ] **Step 1: Write the failing tests:**

```python
def test_encode_then_decode(self):
    msg = {"seq": 1, "type": "request", "command": "threads"}
    self.assertEqual(dap.Decoder().feed(dap.encode(msg)), [msg])
def test_decoder_handles_split_and_joined_messages(self):
    data = dap.encode({"a": 1}) + dap.encode({"b": "é"}); d = dap.Decoder()
    self.assertEqual(d.feed(data[:10]), []); self.assertEqual(d.feed(data[10:]), [{"a": 1}, {"b": "é"}])
def test_attach_sends_the_probe_sequence(self):
    self.server.script_attach(verified=True)
    out = self.dbg.attach({"C:\\m\\events\\te_qa.txt": [9]})
    self.assertEqual([m["command"] for m in self.server.requests],
                     ["initialize", "launch", "setBreakpoints", "configurationDone"])
    self.assertEqual(out, {"C:\\m\\events\\te_qa.txt": [True]})
def test_reply_is_found_behind_nine_hundred_events(self):
    self.server.before_next_reply([{"type": "event", "event": "output",
                                    "body": {"category": "stderr", "output": "Flag 'KAT' is set but is never used\n"}}] * 900)
    self.server.reply("evaluate", {"result": "yes - Yes: \nYes: is_player; Subject: Country Great Britain (1); "})
    self.assertIs(self.dbg.evaluate("is_player = yes").value, True)
    self.assertEqual(len(self.dbg.errors()), 900); self.assertEqual(self.dbg.errors(), [])
def test_number_and_refusals(self):
    self.server.reply("evaluate", {"result": "21570770.55692"})
    self.assertEqual(self.dbg.evaluate("c:FRA.gdp").value, 21570770.55692)
    self.server.reply("evaluate", success=False, message="not a valid trigger or script value")
    e = self.dbg.evaluate("gdp"); self.assertEqual((e.ok, e.value), (False, None))
def test_wait_stopped(self):
    self.server.push({"type": "event", "event": "stopped", "body": {"reason": "breakpoint", "threadId": 1}})
    self.assertTrue(self.dbg.wait_stopped(1.0)); self.assertFalse(self.dbg.wait_stopped(0.01))
def test_scopes(self): ...      # the fixture's scopes + variables replies -> {"Scope": {"this": "Country Great Britain (1)", …}, "Saved Scopes": {}}
def test_no_reply_raises(self):
    with self.assertRaises(dap.DebuggerError): self.dbg.evaluate("x", timeout=0.01)
```

`self.server` is a small in-test class that decodes what `send` gets and feeds `recv` from a queue.

- [ ] **Step 2: Run.** Expected: fail on the missing module.
- [ ] **Step 3: Implement** `encode`, `Decoder`, `Debugger`.
- [ ] **Step 4: Run** all seven `test_game_qa_*.py` files and `scripts/preflight.py --quick`. Expected: pass.
- [ ] **Step 5: Commit** `game_qa/dap.py test_game_qa_dap.py test_fixtures/game_qa/debugger_messages.json`: "Game QA: a debug-adapter client for breakpoints and evaluation". Push and open **PR 2**.

---

### Task 9: The live session (needs the owner's go-ahead to launch)

**Files:**
- Create: `docs/testing/game_qa_probe/overlay/events/te_qa_probe_assumptions_events.txt`, `docs/testing/game_qa_probe/overlay/common/script_values/te_qa_probe_values.txt`, `docs/testing/game_qa_probe/live_session.py` (a throwaway driver for this task, using Tasks 2–8)
- Modify: `docs/testing/game_qa_probe/overlay/common/scripted_effects/te_qa_probe_effects.txt`, `docs/testing/game_qa_probe/captures/` (new captures), `docs/testing/game_qa_probe/README.md`, the spec's § 7 (a Result column), `docs/superpowers/README.md`

**Interfaces:**
- Consumes: everything from Tasks 1–8.
- Produces: an answer, with its log evidence, for each row of the two tables below; the captures the spec's § 11 lists as missing. No code that part 2 imports.

The probe script to add (one UTF-8 BOM, tabs):

```
namespace = te_qa_probe

# A6: would a false trigger stop a console `event`?
te_qa_probe.3 = {
	type = country_event
	hidden = yes
	trigger = { always = no }
	immediate = { debug_log = "TE_QA_PROBE A6 false_trigger_fired" }
}
# A6: would a cooldown stop a second console `event`?
te_qa_probe.4 = {
	type = country_event
	hidden = yes
	cooldown = { days = 365 }
	immediate = { debug_log = "TE_QA_PROBE A6 cooldown_fired" }
}
# A1: an event that reads a scope its caller saved.
te_qa_probe.5 = {
	type = country_event
	placement = ROOT
	event_image = { video = "africa_desert_expedition" }
	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_map.dds"
	title = te_qa_probe.2.t
	desc = te_qa_probe.2.d
	flavor = te_qa_probe.2.f
	duration = 3
	immediate = { debug_log = "TE_QA_PROBE A1 opened rival=[SCOPE.sCountry('te_qa_rival').GetTagName]" }
	option = { name = te_qa_probe.2.a default_option = yes debug_log = "TE_QA_PROBE A1 option=A" }
	option = { name = te_qa_probe.2.b debug_log = "TE_QA_PROBE A1 option=B" }
}
# A1 and A4: the carrier saves the scope, sets a variable, triggers the event.
te_qa_probe.6 = {
	type = country_event
	hidden = yes
	immediate = {
		c:GBR = { save_scope_as = te_qa_rival }
		set_variable = { name = te_qa_probe_var value = 42 }
		trigger_event = { id = te_qa_probe.5 popup = yes }
		debug_log = "TE_QA_PROBE A1 carrier_done date=[TimeKeeper.GetCurrentDate.GetString]"
	}
}
# A5: sixty lines of padding, about 5 KB.
te_qa_probe.7 = {
	type = country_event
	hidden = yes
	immediate = { te_qa_probe_pad = yes }
}
```

and, appended to the probe's scripted effects and in the new script-values file:

```
te_qa_probe_pad = {
	while = {
		count = 60
		debug_log = "TE_QA_PROBE PAD 0123456789012345678901234567890123456789012345678901234567890123456789"
	}
}
```

```
te_qa_probe_value = {
	value = 7
	add = var:te_qa_probe_var
}
```

**What the session must answer**

| # | Question | How | Evidence that settles it |
|---|---|---|---|
| A3 | Does a second mod folder added to `content_load.json` load on a direct launch? | Put the probe overlay in `mod/te_qa_overlay/` with a `.metadata/metadata.json` shaped like the mod's own, add its Windows path to `enabledMods`, run the fixture launch | The `TEST_FAIL_te_qa_fixture_*` save appears, and in the next launch `event te_qa_probe.1` logs its line |
| A6 | Does console `event` ignore `trigger` and `cooldown`? | `event te_qa_probe.3`; `event te_qa_probe.4` twice | Which `A6` lines are logged, and how many times |
| A1 | Is an event triggered from the carrier pending at once, paused, with the saved scope? | `event te_qa_probe.6`, then `select_event_option list` with no tick between | `te_qa_probe.5` listed; its line reads `rival=GBR`; `select_event_option 1 <id>` logs `option=B` |
| A4 | Does the debugger read a mod script value and a variable through `c:TAG.`? | Breakpoint on the carrier's `debug_log` line, fire it again, evaluate `c:FRA.te_qa_probe_value`, `c:FRA.var:te_qa_probe_var`, `has_variable = te_qa_probe_var` | `49`, `42`, `yes`, or the refusal text |
| A5 | Does 5 KB of `debug_log` padding flush the log? | Note `debug.log`'s size, `event te_qa_probe.7` with no help command after it, read the size for 10 s | The file grows within a second or two and holds the earlier lines |
| A2 | Does time advance from the loaded fixture's country-select screen? | After `tag FRA`, press space; fire the carrier twice ten seconds apart and compare its `date=`; press space again | Two different dates. If the same: one click on the Start button, then repeat, and record where the button was |

| # | Helper unknown | Evidence |
|---|---|---|
| U1 | Windows `python.exe` runs `win_helper.py` from its `\\wsl.localhost\` path and keeps its pipes open for the whole session | `ping` answers at the start and at the end |
| U2 | `SendInput` and the screenshot work through `ctypes` | The console round trip passes; the PNG opens and shows the game |
| U3 | `idle_ms` counts input that arrives through Chrome Remote Desktop | The owner, or a second session, moves the mouse remotely and the value drops |
| U4 | Does `console_history.txt` gain a line when the same command is entered twice running? | Its line count after two identical commands |

- [ ] **Step 1: Ask the owner** for the go-ahead to launch, unless they granted it for this session. Say it will take about four launches and fifteen minutes.
- [ ] **Step 2: Dry run, no launch.** `python3 -m game_qa selftest-restore`. Expected: `"match": true`. Stop here if not.
- [ ] **Step 3: Gate and snapshot.** `python3 -m game_qa gate --permission "<what the owner said>"` must print `"ok": true`; `python3 -m game_qa snapshot` and note the id.
- [ ] **Step 4: Write `live_session.py`** so that each launch is: record `started` with the process id and creation time, heartbeat once a minute, record `game_exited` when the process is gone, then `restore`. It keeps a raw copy of everything `LogFollower` yields.
- [ ] **Step 5: Launch 1, the fixture.** `-gdpr-compliant -debug_mode -handsoff -scripted_tests -run_until=1836.1.4` with the overlay enabled as in A3. Expected: the game quits by itself within 3 minutes and the save exists. Rename it `te_qa_fixture_probe.v3`. If no save appears, A3 is false: copy the overlay files into the deploy folder instead (and remove them at the end by manifest) and repeat.
- [ ] **Step 6: Launch 2, the questions.** `-gdpr-compliant -debug_mode -script_debugger -loadsave=te_qa_fixture_probe`. Work through U1, U2, U4, then `tag FRA`, then A6, A1, A4, A5, A2, in that order, saving the log lines for each. Take one screenshot on the country-select screen.
- [ ] **Step 7: Captures.** In the same launch: run `help` twice so `debug.log` rotates while `LogFollower` polls, and save the raw bytes of each generation before and after; save a buffered tail (the file's last 300 bytes before and after a flush); save the `content_load.json` used. U3 last, with the owner's help if they are there; otherwise record it as not settled.
- [ ] **Step 8: Stop.** End the process the helper started, restore, and confirm with `python3 -m game_qa snapshot` that a fresh snapshot's entries equal the first one's for every file but the logs' times. Remove `mod/te_qa_overlay/` and `te_qa_fixture_probe.v3`.
- [ ] **Step 9: Write it down.** Add a Result column to the spec's § 7 with each answer and its evidence line; add the captures and a line each to the probe README; update the spec's row in `docs/superpowers/README.md`. Any engine fact that is new goes into the section this design added to `docs/guides/scripting_best_practices.md`.
- [ ] **Step 10: Commit** the probe files, captures and doc edits: "Game QA: the six assumptions settled in a live session". Push and open **PR 3**. Then write the part 2 plan.

---

## Decided by the live session (part 2's shape)

| Part 2 component | Decided by | If the assumption holds | If it does not |
|---|---|---|---|
| Overlay location, playset control, fixture key | A3 | Its own mod folder, enabled through `content_load.json` | Files in the deploy folder under `te_qa_*`, excluded from `deploy.sh`'s `--delete`; playset left as the owner has it |
| How `try-event` fires an event | A6, A1 | Console `event`; a carrier with `trigger_event` only where scopes must be saved | Setup effects make each trigger true; a cooldown forces one country or one relaunch per option |
| Isolation default in `try-event` | A6 | Shared game, setup re-run per option | One country per option where named, else a relaunch per option |
| `advance` | A2 | Pause and speed keys from the country-select screen | One confirmed click on Start per session |
| `read` | A4 | Debugger evaluation through `c:TAG.` | Generated readout lines in the overlay, read from the log |
| Flush | A5 | Carrier padding | `help ndefines.ngui`, as Task 7 does |
| `pick` | (settled) | Always passes the numeric id from `events`; with two instances of one event pending it picks the oldest and says so in the report | |
| Arrival check in `Console` | U4 | History file only | The log fallback Task 7 already has |
