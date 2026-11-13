"""Command line of the in-game QA harness, part 1: protecting the owner's files.

    python3 -m game_qa snapshot [--save NAME]...           # with no game running
    python3 -m game_qa launch <id> --permission "asked 12:40" [--playset current|mod_only]
                       [--add-mod WINDOWS_PATH]... -- -debug_mode -loadsave=NAME
                                                           # the gate's checks, the run's playset, then start
                                                           # the game and record its start: the only way to
                                                           # start it
    python3 -m game_qa watch <id> [--interval S]           # right after: records that the launched game is
                                                           # alive, and its exit (S at most 10)
    python3 -m game_qa restore <id>                        # after `watch` has returned
    python3 -m game_qa gate --permission "asked 12:40"     # dry check: would a launch be allowed now?
    python3 -m game_qa recover                             # finish runs a dead session left
    python3 -m game_qa held                                # snapshots kept because the owner played since
    python3 -m game_qa selftest-restore                    # prove a snapshot restores, touching nothing

A run `watch` lost sight of (a failed look, a first look more than 120 s after the start, or a resume after
more than 15 s) is held for the owner to resolve, as is one during which it saw another game. `snapshot`, `launch`, `restore`, `recover` and
`selftest-restore` take turns (a lock in the backup root): `busy` means another session is in one of them.

Each verb prints one JSON object. Exit 0 on success, 2 on a refusal, a hold or an error. Usage errors are
argparse's (a message on stderr, exit 2).
Spec: docs/superpowers/specs/2026-11-10-in-game-qa-harness-design.md §§ 5.2–5.3.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import functools
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from game_qa import gate, restore, snapshot
from game_qa import client

MIN_FREE_BYTES = 2 * 1024**3
KEEP_SNAPSHOTS = 5
SELFTEST_TIME_TOLERANCE_NS = 2_000_000_000
WATCH_INTERVAL_S = 5.0    # between looks; a heartbeat is recorded at each
# The longest interval `watch` takes: an exit is recorded at most one interval late, and a restore within
# WATCH_RECORDING_S of the last heartbeat is refused.
WATCH_MAX_INTERVAL_S = 10.0
WATCH_LOOK_TRIES = 5      # failed looks in a row after which `watch` stops, recording no exit
# A `started` or `heartbeat` younger than this, with no `game_exited`: `watch` is still recording, and a
# restore now would judge the game's exit writes against the last heartbeat. Three default intervals.
WATCH_RECORDING_S = 15.0
# A `watch_resumed` whose gap since the run's game was last seen alive is longer than this holds the run
# (`unwatched_stretch`): nobody saw in that time whether another game ran.
WATCH_RESUME_GAP_S = 15.0
# A first `watch` that began more than this after `started` (its `watching` gap) holds the run too: in between
# nobody looked whether another game ran.
WATCH_FIRST_GAP_S = 120.0
# The `watch` entries: a journal with one of them has been followed before, so a new `watch` is a resume.
_WATCH_EVENTS = ("watching", "watch_resumed", "heartbeat", "look_failed", "other_game")
# Created in the snapshot's folder with O_EXCL by the one `launch` that may start the game; it counts as a
# start. A claim with no `started` is a launch whose record was lost (its reply, or the journal write).
LAUNCH_CLAIM = "launch.claim"
# A claim younger than this with no `started` may be a `launch` still on its way to the record: `restore` and
# `recover` give it no verdict (`launch_in_flight`). gate.start_game gives PowerShell up to 60 s; the rest is
# margin for the journal write and the drive's coarse file times.
LAUNCH_IN_FLIGHT_S = 90.0
# The verbs that change things (snapshot, launch, restore, recover, selftest-restore) take turns: each holds
# LOCK_NAME in the backup root, created with O_EXCL, for its whole run, and refuses `busy` while another session
# holds it, so that no check-then-act of one can interleave with another's. A lock older than LOCK_STALE_S was
# left by a process that died: it is broken, by one session at a time (LOCK_BREAK_NAME, also O_EXCL).
LOCK_NAME = ".lock"
LOCK_BREAK_NAME = ".lock.break"
LOCK_STALE_S = 15 * 60.0
# The one spelling of the end date probed against the game, matched whole: -run_until=1836.2.10.
_END_DATE_ARG = re.compile(r"-run_until=[0-9]{1,4}\.[0-9]{1,2}\.[0-9]{1,2}")
# The playset a direct start of the game loads; the launcher writes it. `launch --playset mod_only` and `--add-mod`
# rewrite it for the run (UTF-8 without a BOM, indent 2: the form a live session proved the game reads,
# 2026-11-10). It is in the snapshot set, so `restore` puts the owner's back.
PLAYSET_FILE = "content_load.json"
PLAYSET_MODES = ("current", "mod_only")
# An --add-mod path: a drive path (`C:\…`) or a UNC path (`\\server\…`), as the launcher writes them.
_WINDOWS_PATH = re.compile(r"[A-Za-z]:\\|\\\\[^\\]")
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")
# Where `launch` writes the playset before renaming it over the file: restore's own temp name, so `compare` skips it.
_PLAYSET_TEMP = PLAYSET_FILE + restore._TEMP_SUFFIX
_PLAYSET_STAYS = (f"the playset this wrote into {PLAYSET_FILE} stays the run's until `restore` or `recover`, run "
                  "once no game is running, puts the owner's back")
_VERDICTS = ("restored", "held")
_sleep = time.sleep       # patched in tests


class UnknownSnapshotError(LookupError):
    """No snapshot has the id given."""


class _Refused(Exception):
    """A refusal of `watch` or `launch`, carried out of their helpers as the JSON object to print."""

    def __init__(self, reason: str, detail: str, **fields):
        super().__init__(reason)
        self.result = {"refused": reason, "detail": detail, **fields}


def _takes_turns(verb: str):
    """Run the decorated verb holding the backup root's lock, or refuse `busy` without waiting. The lock is
    released however the verb ends."""
    def wrap(fn):
        @functools.wraps(fn)
        def run(args) -> tuple[dict, int]:
            _user, backups = _paths()
            try:
                token = _take_lock(backups, verb)
            except _Refused as refused:
                snap_id = getattr(args, "id", None)
                return (dict(refused.result, id=snap_id) if snap_id else refused.result), 2
            try:
                return fn(args)
            finally:
                _release_lock(backups, token)
        return run
    return wrap


def _take_lock(backups: Path, verb: str) -> str:
    """Create the lock for `verb` and return its token, or raise _Refused (`busy`)."""
    if not backups.is_dir():
        if not backups.parent.is_dir():
            raise snapshot.BackupRootError(f"the folder that should hold the backups does not exist: {backups.parent}")
        backups.mkdir(exist_ok=True)
    lock = backups / LOCK_NAME
    token = os.urandom(8).hex()
    for _attempt in range(3):
        at = snapshot._drive_clock(backups).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            holder = _lock_holder(backups)
            if holder is None:                      # released between the two looks: try again
                continue
            if holder[2] <= LOCK_STALE_S:
                raise _busy(*holder) from None
            _break_stale_lock(backups, *holder)
            continue
        try:
            os.write(fd, (json.dumps({"verb": verb, "pid": os.getpid(), "at": at, "token": token}) + "\n")
                     .encode("ascii"))
            os.fsync(fd)
        except BaseException:
            os.close(fd)
            lock.unlink(missing_ok=True)
            raise
        os.close(fd)
        return token
    raise _Refused("busy", "the lock changed hands while this looked at it: retry shortly", holder="unknown")


def _lock_holder(backups: Path) -> tuple[str, object, float] | None:
    """The lock's verb, process id and age in seconds by the backup drive's clock, or None if there is none."""
    lock = backups / LOCK_NAME
    try:
        made = os.stat(lock).st_mtime
        text = lock.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None
    try:
        entry = json.loads(text.splitlines()[0])
        verb, pid = str(entry["verb"]), entry.get("pid")
    except (ValueError, IndexError, KeyError, TypeError, AttributeError):   # cut short when its process died
        verb, pid = "unknown", None
    return verb, pid, snapshot._drive_clock(backups).timestamp() - made


def _busy(verb: str, pid, age: float) -> _Refused:
    return _Refused("busy", f"another session is in `{verb}` (pid {pid}, for {max(age, 0):.0f} s): `snapshot`, "
                            "`launch`, `restore`, `recover` and `selftest-restore` take turns. Retry shortly. A "
                            f"lock older than {LOCK_STALE_S / 60:g} minutes is taken as left by a process that died, "
                            "and broken", holder=verb, holder_pid=pid, age_s=round(max(age, 0.0), 1))


def _break_stale_lock(backups: Path, verb: str, pid, age: float) -> None:
    """Remove a stale lock, one session at a time: only the session that creates LOCK_BREAK_NAME may, after
    looking at the lock again. Raises _Refused (`busy`) while another session is breaking it."""
    breaker = backups / LOCK_BREAK_NAME
    try:
        fd = os.open(breaker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        try:
            if snapshot._drive_clock(backups).timestamp() - os.stat(breaker).st_mtime > LOCK_STALE_S:
                breaker.unlink(missing_ok=True)     # its breaker died too: the next call breaks the lock
        except FileNotFoundError:
            pass
        raise _Refused("busy", f"the lock `{verb}` (pid {pid}) left {age / 60:.0f} minutes ago is being broken by "
                               "another session: retry shortly", holder=verb, holder_pid=pid,
                       age_s=round(age, 1)) from None
    os.close(fd)
    try:
        holder = _lock_holder(backups)              # again, now that no other session may break it
        if holder is not None and holder[2] > LOCK_STALE_S:
            (backups / LOCK_NAME).unlink(missing_ok=True)
    finally:
        breaker.unlink(missing_ok=True)


def _release_lock(backups: Path, token: str) -> None:
    """Remove the lock if it is still the one `token` names (never another session's)."""
    lock = backups / LOCK_NAME
    try:
        if json.loads(lock.read_text(encoding="utf-8").splitlines()[0]).get("token") == token:
            lock.unlink()
    except (OSError, ValueError, IndexError, AttributeError):
        pass


def _paths() -> tuple[Path, Path]:
    import path_constants

    return (Path(path_constants.refresh("game_user_data_path")),
            Path(path_constants.refresh("game_qa_backup_path")))


def _backup_error(backup_root: Path) -> str | None:
    """Why no snapshot could be taken into `backup_root`, or None."""
    parent = backup_root if backup_root.is_dir() else backup_root.parent
    if not parent.is_dir():
        return f"the backup root's folder {parent} does not exist"
    if not os.access(parent, os.W_OK):
        return f"the backup root's folder {parent} is not writable"
    free = shutil.disk_usage(parent).free
    if free < MIN_FREE_BYTES:
        return f"only {free // 1024**2} MB free under {parent}"
    return None


def _find(backup_root: Path, snap_id: str) -> snapshot.Snapshot:
    for snap in snapshot.all_snapshots(backup_root):
        if snap.id == snap_id:
            return snap
    raise UnknownSnapshotError(f"no snapshot {snap_id!r} under {backup_root}")


def _outcome(out: restore.Outcome) -> dict:
    result = {"restored": out.restored, "removed": out.removed, "held": out.held, "reason": out.reason}
    if out.retimed:         # same bytes as the snapshot, the run's time on them: the snapshot's time put back
        result["retimed"] = out.retimed
    if out.manual_saves:    # the owner's own saves changed, gone or new (restore._manual_saves)
        result["manual_saves"] = out.manual_saves
    return result


def _events(snap: snapshot.Snapshot) -> list[str]:
    return [str(e.get("event")) for e in snapshot.journal(snap)]


def _proc(entry: dict) -> gate.ProcId | None:
    """The game process a `started` entry names, or None if it cannot be read."""
    try:
        return gate.ProcId(int(entry["pid"]), str(entry["created"]))
    except (KeyError, TypeError, ValueError):
        return None


def _started(snap: snapshot.Snapshot) -> gate.ProcId | None:
    """The game process of the snapshot's latest launch that can be read."""
    found = None
    for e in snapshot.journal(snap):
        if e.get("event") == "started":
            found = _proc(e) or found
    return found


def _last_started(snap: snapshot.Snapshot) -> gate.ProcId | None:
    """The game process the snapshot's last `started` entry names, or None if there is none or it cannot be read."""
    starts = [e for e in snapshot.journal(snap) if e.get("event") == "started"]
    return _proc(starts[-1]) if starts else None


def _running(games: list[gate.ProcId]) -> list[str]:
    return [f"pid {g.pid} (started {g.created})" for g in games]


def _open_snapshots(backups: Path) -> list[snapshot.Snapshot]:
    """Snapshots taken for a run (`armed`, or already `started`) that have no
    verdict yet. While one exists no new snapshot may be taken: it would
    record that run's leftovers as the owner's files."""
    if not backups.is_dir():
        return []
    found = []
    for snap in snapshot.all_snapshots(backups):
        events = _events(snap)
        if (("armed" in events or "started" in events) and not any(v in events for v in _VERDICTS)):
            found.append(snap)
    return found


def _when(text: str) -> dt.datetime | None:
    """A journal time (`2026-11-10T23:06:15Z`) or a Windows creation time
    (`2026-11-10T23:06:35.4149252Z`, seven fractional digits) as a datetime."""
    try:
        head, _, frac = text.rstrip("Z").partition(".")
        when = dt.datetime.strptime(head, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)
        return when + dt.timedelta(seconds=float("0." + frac)) if frac else when
    except (AttributeError, ValueError):
        return None


def cmd_gate(args) -> tuple[dict, int]:
    _user, backups = _paths()
    result = gate.check(args.permission, gate.list_games(), gate.ours_from_journals(backups),
                        gate.sample_gpu(), args.owner_confirmed_busy, _backup_error(backups))
    return {"ok": result.ok, "reason": result.reason, "detail": result.detail,
            "permission": args.permission}, 0 if result.ok else 2


@_takes_turns("snapshot")
def cmd_snapshot(args) -> tuple[dict, int]:
    user, backups = _paths()
    open_runs = _open_snapshots(backups)
    if open_runs:
        # Snapshots must never nest: one taken over an unrestored run's leftovers records them as the owner's files.
        return {"refused": "unfinished_run", "unfinished": [s.id for s in open_runs],
                "detail": "an earlier snapshot has been neither restored nor held. If it is your own run's, wait "
                          "for its `watch` to return and run `restore <id>`. If not, run `recover`: it finishes "
                          "a run whose session died (doing nothing while that run's game is up), and puts back or "
                          "holds a snapshot nothing was launched under. A held snapshot does not block a new one"}, 2
    games = gate.list_games()
    if games:
        return _game_running(games, "a snapshot taken while a game writes its files catches them mid-run").result, 2
    left = _unanswered_write(backups, user)
    if left is not None:
        return _playset_not_restored(left.id, "a snapshot now would record it as the owner's").result, 2
    extra = ["save games/" + (name if name.endswith(".v3") else name + ".v3") for name in args.save]
    try:
        snap = snapshot.take(user, backups, extra=extra)
    except snapshot.SaveNotListed as exc:       # a name the drive answers to but does not list (an 8.3 name)
        return {"refused": "bad_argument", "detail": str(exc)}, 2
    snapshot.record(snap, "armed")
    pruned = restore.prune(backups, keep=KEEP_SNAPSHOTS, current=snap.id)
    return {"id": snap.id, "files": len(snap.files), "pruned": pruned,
            "held": [s.id for s in restore.held(backups)]}, 0


def _game_running(games: list[gate.ProcId], why: str) -> _Refused:
    return _Refused("game_running", f"a Victoria 3 process is running, and {why}. `gate` says whether this "
                                    "harness started it: if it did, finish that run first (its `watch`, then "
                                    "`restore <id>`, or `recover`); if not, it is the owner's: ask them, and "
                                    "never end it", games=_running(games))


@_takes_turns("launch")
def cmd_launch(args) -> tuple[dict, int]:
    """Start the game for a snapshot's run, after the gate's checks, and record its start at once.

    The only supported way to start the game: the journal names the process from the moment it exists, so
    no command ever has to guess which game is the run's. Nothing is started, and nothing recorded, unless
    the snapshot is armed with no `started`, no claim and no verdict; every argument can reach the game whole
    (`_check_arguments`); an unattended run (`handsoff` in any spelling) carries `-run_until=<y.m.d>`; the
    gate's checks pass (a stated permission, a usable backup root, no game this harness
    did not start, the GPU unless the owner confirmed); no Victoria 3 process at all is running (one
    snapshot, one game); and no file, logs included, has changed since the snapshot. That last one means
    someone has used the folder since: a start recorded now would date their writes before the run, and
    restore would put the old copies back over them. The folder, the journal and the processes are looked
    at again last; then the launch claims the snapshot (LAUNCH_CLAIM, created with O_EXCL, so of two
    launches on one id only one can start a game) and starts it. All of it runs holding the backup root's
    lock, so a verdict another session gave before is read here (already_finished), and a `restore` or
    `recover` arriving during it is refused `busy`. The claim and `launch_in_flight` remain for a launch
    whose process died between the start and the record.

    `started` (pid, start time, arguments) is recorded the moment the process exists. A start time
    PowerShell could not read is recorded as "unknown" and never looked up later: a process found by its pid
    alone could be another game that took the pid.

    The run's playset: with `--playset mod_only` or an `--add-mod`, `content_load.json` is rewritten for the run
    after the claim and before the start (`_plan_playset`, `_write_playset`); with neither it is not touched.
    Everything that can refuse is decided before the claim, from the file the stale check has just matched
    against the snapshot. After the claim the `playset` entry (mode, enabled paths, and the SHA-256 of the bytes
    to be written) is journaled first, and only then is the file written: a write no entry vouches for would
    be held. A refusal after the claim (the entry or the write failed, or the start did) leaves the claim, as
    for a failed start. `restore` and `recover` put the owner's file back whenever they judge the run with no
    game running, held or not (`_settle_playset`). Whatever the options, nothing starts while the folder's
    playset is another run's write never put back (`playset_not_restored`): the owner never chose it."""
    user, backups = _paths()
    snap = _find(backups, args.id)
    game_args = list(args.game_args)
    playset_wanted = args.playset == "mod_only" or bool(args.add_mod)
    playset = None
    try:
        _launchable(snap)
        _check_arguments(game_args)
        _check_end_date(game_args)
        _check_mod_paths(args.add_mod)
        left = _unanswered_write(backups, user, exclude=snap.id)
        if left is not None:
            raise _playset_not_restored(left.id, "a game started now would run with a playset the owner never chose")
        if playset_wanted:
            _check_playset_present(snap, user)
        games = gate.list_games()
        ours = gate.ours_from_journals(backups)
        backup_error = _backup_error(backups)
        early = gate.check_before_gpu(args.permission, games, ours, backup_error)
        if early is not None:
            raise _Refused(early.reason, early.detail)
        if games:
            raise _game_running(games, "one snapshot is for one game")
        verdict = gate.check(args.permission, games, ours, gate.sample_gpu(), args.owner_confirmed_busy, backup_error)
        if not verdict.ok:
            raise _Refused(verdict.reason, verdict.detail)
        exe = _game_exe()
        if not exe.is_file():   # wslpath converts a path that does not exist, and the start would then fail
            raise _Refused("no_game_binary", f"there is no game at {exe}: check base_game_path")
        exe_windows, cwd_windows = gate.windows_path(exe), gate.windows_path(exe.parent)
        this_mod = _deployed_mod() if args.playset == "mod_only" else None
        # The last looks, right before the start: the folder (slow: it hashes), then the journal and the processes.
        _check_unchanged(snap, user)
        if playset_wanted:
            playset = _plan_playset(snap, user, args.playset, args.add_mod, this_mod)
        _launchable(snap)
        games = gate.list_games()
        if games:
            raise _game_running(games, "one snapshot is for one game")
        _claim(snap)
        if playset is not None:
            _record_playset(snap, playset)
            if playset.data is not None:
                _record_written(snap, _write_playset(snap, user, playset.data))
    except _Refused as refused:
        return dict(refused.result, id=snap.id), 2
    written = playset is not None and playset.data is not None
    try:
        proc = gate.start_game(exe_windows, game_args, cwd_windows)
    except gate.GateError as exc:
        return {"refused": "start_unconfirmed", "id": snap.id,
                "detail": f"{exc}. Nothing was recorded: a game this started would count as another game "
                          "everywhere (`gate` and `launch` refuse beside it, `restore` and `recover` hold). The "
                          f"snapshot stays claimed, so `launch` refuses it: once no game runs, `restore {snap.id}` "
                          f"finishes it, {LAUNCH_IN_FLIGHT_S:g} s after the claim: "
                          + (f"{_PLAYSET_STAYS}; it holds any other file changed outside `logs/`, and leaves "
                             "`logs/` as it is" if written else
                             "it holds a changed file outside `logs/` and leaves `logs/` as it is")}, 2
    try:
        snapshot.record(snap, "started", pid=proc.pid, created=proc.created, args=game_args)
    except OSError as exc:
        return {"refused": "not_recorded", "id": snap.id, "pid": proc.pid, "created": proc.created,
                "detail": f"the game started (pid {proc.pid}) but its start could not be recorded: {exc}. It "
                          "counts as another game everywhere (`restore` and `recover` hold). This harness "
                          f"started it, so it may end pid {proc.pid}, but only while the game listing shows pid "
                          f"{proc.pid} with start time {proc.created}: a pid alone may be another game's by then"
                          + (f". Meanwhile {_PLAYSET_STAYS}" if written else "")}, 2
    result = {"id": snap.id, "pid": proc.pid, "created": proc.created, "args": game_args}
    if playset is not None:
        result["playset"] = {"mode": playset.mode, "enabled": playset.enabled, "written": written}
    if proc.created == gate.UNKNOWN_START:
        result["detail"] = (f"the game's start time could not be read, so it is recorded as unknown: `watch` "
                            f"cannot tell pid {proc.pid} from another game and will refuse `unknown_start`. Wait "
                            f"until `gate` shows no game at all, then `restore {snap.id}`: it judges the files "
                            "against the start and holds any written after it")
    return result, 0


def _game_exe() -> Path:
    import path_constants

    return Path(path_constants.refresh("base_game_path")) / "binaries" / "victoria3.exe"


def _claimed(snap: snapshot.Snapshot) -> bool:
    return (snap.dir / LAUNCH_CLAIM).exists()


def _launchable(snap: snapshot.Snapshot) -> None:
    """Raise _Refused unless the snapshot is armed, with no `started`, no claim and no verdict."""
    events = _events(snap)
    if any(v in events for v in _VERDICTS):
        raise _Refused("already_finished", f"snapshot {snap.id} already has a verdict (restored or held): take "
                                           "a new snapshot")
    if "started" in events or _claimed(snap):
        raise _Refused("already_started", f"a `launch` has already claimed snapshot {snap.id}: `watch {snap.id}`")
    if "armed" not in events:
        raise _Refused("not_armed", "this snapshot was not taken by `snapshot` for a run")


def _claim(snap: snapshot.Snapshot) -> None:
    """Claim the snapshot for this launch, or raise _Refused if another launch has: O_EXCL lets one create win."""
    try:
        fd = os.open(snap.dir / LAUNCH_CLAIM, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        raise _Refused("already_started", f"another `launch` has claimed snapshot {snap.id}") from None
    try:
        os.write(fd, f"{os.getpid()}\n".encode("ascii"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _check_arguments(game_args: list[str]) -> None:
    """Raise _Refused for an argument that cannot reach the game whole: one PowerShell cannot be handed (a lone
    surrogate), or one with a control character (a NUL may cut it short on the Windows side, after the
    end-date check read all of it)."""
    for arg in game_args:
        try:
            arg.encode("utf-16-le")
        except UnicodeEncodeError:
            raise _Refused("bad_argument", f"the game argument {arg!r} cannot be passed to Windows") from None
        if any(ord(c) < 32 or ord(c) == 127 for c in arg):
            raise _Refused("bad_argument", f"the game argument {arg!r} has a control character in it")


def _check_end_date(game_args: list[str]) -> None:
    """Raise _Refused for an unattended run without an end date: one runs on and writes autosaves over the
    owner's (spec § 5.3). `handsoff` is found in any spelling (without its leading `-` or `/`, in any case,
    before any `=`, also as a word of an argument with spaces in it); it needs an argument that is exactly
    `-run_until=<y.m.d>`, the only spelling probed against the game."""
    names = [word.lstrip("-/").lower().partition("=")[0] for arg in game_args for word in arg.split()]
    if "handsoff" in names and not any(_END_DATE_ARG.fullmatch(arg) for arg in game_args):
        raise _Refused("no_end_date", "an unattended run (-handsoff) must carry -run_until=<year.month.day>, such "
                                      "as -run_until=1836.2.10: without one it runs on and writes autosaves")


def _check_unchanged(snap: snapshot.Snapshot, user: Path) -> None:
    """Raise _Refused if a file, logs included, no longer matches the snapshot. Nothing but a game writes the
    logs, so a changed log means someone played since; the run's game would write over it, and restore would
    put the snapshot's older copy back."""
    diff = restore.compare(snap, user)
    files = sorted({*diff.changed, *diff.missing, *diff.added_in_set, *diff.created})
    if files:
        raise _Refused("stale_snapshot", "the folder has changed since the snapshot was taken, so someone has used "
                                         "it since: a run started now would make restore put the old copies back "
                                         "over theirs. Run `recover`: it judges this snapshot and holds it, unless "
                                         "the only change is a missing file, which it puts back, or is in `logs/`, "
                                         "which it leaves alone. Then take a new snapshot", files=files)


@dataclass(frozen=True)
class _Playset:
    """The run's playset as `launch` leaves it: `enabled` the mod folders, `data` the file to write, or None when
    the owner's file already enables exactly those (it is then not touched)."""
    mode: str
    enabled: list[str]
    data: bytes | None


# Said by every refusal after the claim: the snapshot cannot be launched again, and is finished as a failed start.
_CLAIM_STAYS = ("Nothing was started. The snapshot stays claimed, so `launch` refuses it: `restore <id>` or `recover` "
                f"finishes it {LAUNCH_IN_FLIGHT_S:g} s after the claim; then take a new snapshot")


def _answered(journal: list[dict], index: int) -> bool:
    """Whether the `playset` entry at `index` is answered: a `playset_restored` or a `restored` follows it. A
    restored folder equals the snapshot, so after `restored` the entry vouches for nothing: bytes equal to that
    write later are the owner's choice (their launcher's), and are neither refused nor put back. A held snapshot
    leaves its entry unanswered."""
    return any(later.get("event") in ("playset_restored", "restored") for later in journal[index + 1:])


def _written_signature(journal: list[dict], index: int) -> tuple[int, int] | None:
    """The (size, mtime_ns) `launch` journaled in `playset_written` for the `playset` entry at `index`, or None
    if none was (a kill between the rename and the read-back, or a write that never happened)."""
    for later in journal[index + 1:]:
        if later.get("event") == "playset":
            return None
        if later.get("event") == "playset_written":
            size, mtime_ns = later.get("size"), later.get("mtime_ns")
            if all(isinstance(v, int) and not isinstance(v, bool) for v in (size, mtime_ns)):
                return size, mtime_ns
            return None
    return None


def _is_launchs_write(journal: list[dict], index: int, live_sha: str, live: tuple[int, int]) -> bool:
    """Whether the live playset file (its SHA-256 and (size, mtime_ns)) is the write of the `playset` entry at
    `index`: the same bytes, and, when `playset_written` was journaled, the same size and time as read back
    right after the rename. The same bytes written again later (the owner's launcher saving that playset)
    carry another time, and are the owner's. With nothing journaled, the hash alone decides."""
    if journal[index].get("sha256") != live_sha:
        return False
    written = _written_signature(journal, index)
    return written is None or written == live


def _live_playset(user: Path) -> tuple[str, tuple[int, int]] | None:
    """The live playset file's SHA-256 and (size, mtime_ns), or None when it is not a regular file. The put-back
    looks at the file again, time and bytes, just before its rename."""
    path = user / PLAYSET_FILE
    try:
        st = os.lstat(path)
        if not stat.S_ISREG(st.st_mode):
            return None
        return _sha256(path), (st.st_size, st.st_mtime_ns)
    except FileNotFoundError:
        return None


def _unanswered_write(backups: Path, user: Path, exclude: str | None = None) -> snapshot.Snapshot | None:
    """The newest snapshot (other than `exclude`) with an unanswered (`_answered`) `playset` entry whose write
    the live `content_load.json` still is (`_is_launchs_write`): that run's playset is still in the folder, never
    put back. None when there is none, or no regular playset file. `snapshot` and `launch` refuse beside one: the
    owner never chose that playset."""
    live = _live_playset(user)
    if live is None:
        return None
    for snap in reversed(snapshot.all_snapshots(backups)):
        if snap.id == exclude:
            continue
        journal = snapshot.journal(snap)
        for i, entry in enumerate(journal):
            if entry.get("event") == "playset" and _is_launchs_write(journal, i, *live) and not _answered(journal, i):
                return snap
    return None


def _playset_not_restored(snap_id: str, why: str) -> _Refused:
    return _Refused("playset_not_restored", f"{PLAYSET_FILE} still holds the playset `launch` wrote for snapshot "
                                            f"{snap_id}'s run, never put back: {why}. Run `restore {snap_id}` with no "
                                            "game running: it puts the owner's playset back when this is the newest "
                                            "snapshot with a playset entry, and holds again for anything else that "
                                            "needs the owner. Otherwise the owner saving their playset again in the "
                                            "launcher clears it", snapshot=snap_id)


def _deployed_mod() -> str:
    """This mod's deployed folder (`mod_deploy_target`) as Windows names it, the form the playset holds."""
    import path_constants

    return gate.windows_path(Path(path_constants.refresh("mod_deploy_target")))


def _folder_key(path: str) -> str:
    """A Windows folder path as compared: in any case, with either separator, with or without a trailing one."""
    return path.replace("/", "\\").rstrip("\\").lower()


def _check_mod_paths(paths: list[str]) -> None:
    """Raise _Refused for an --add-mod that is not a Windows path (`C:\\…` or `\\\\server\\…`, as the launcher
    writes them: the caller converts a WSL path with `wslpath -w`) or that cannot be written whole (a control
    character, or a lone surrogate, which UTF-8 cannot hold)."""
    for path in paths:
        try:
            path.encode("utf-8")
        except UnicodeEncodeError:
            raise _Refused("bad_argument", f"the --add-mod path {path!r} cannot be written as UTF-8") from None
        if any(ord(c) < 32 or ord(c) == 127 for c in path):
            raise _Refused("bad_argument", f"the --add-mod path {path!r} has a control character in it")
        if not _WINDOWS_PATH.match(path):
            raise _Refused("bad_argument", f"the --add-mod path {path!r} is not a Windows path (C:\\… or "
                                           "\\\\server\\…): convert a WSL path with `wslpath -w`")


def _check_playset_present(snap: snapshot.Snapshot, user: Path) -> None:
    """Raise _Refused (`playset_unwritable`) unless both the snapshot and the folder hold the playset file:
    `launch` rewrites the owner's playset for the run, and never makes one."""
    where = [name for name, present in (("the snapshot", PLAYSET_FILE in snap.files),
                                        ("the folder", (user / PLAYSET_FILE).is_file())) if not present]
    if where:
        raise _Refused("playset_unwritable", f"{PLAYSET_FILE}, the playset a direct start loads, is missing from "
                                             f"{' and '.join(where)}: --playset mod_only and --add-mod rewrite "
                                             "the owner's playset and never make one. Nothing was written. The "
                                             "launcher writes the file when it starts the game")


def _plan_playset(snap: snapshot.Snapshot, user: Path, mode: str, add_mods: list[str],
                  this_mod: str | None) -> _Playset:
    """The run's playset, from the owner's `content_load.json`: their enabled mods (with `mod_only`, only the
    entries for this mod's deployed folder, `this_mod`), then each of `add_mods` not among them yet, in order;
    every other key, and every entry kept, as it was. Folders are matched by `_folder_key`. Raises _Refused,
    having written nothing: `stale_snapshot` when the file's bytes are not the snapshot's (the stale check has
    just matched them, but the owner's launcher writes this file); `playset_unwritable` when it cannot be read
    as a playset; `mod_not_in_playset` for `mod_only` when no entry is this mod's."""
    path = user / PLAYSET_FILE
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise _Refused("playset_unwritable", f"{path} could not be read ({exc}). Nothing was written") from None
    if hashlib.sha256(raw).hexdigest() != snap.files[PLAYSET_FILE].sha256:
        raise _Refused("stale_snapshot", f"{PLAYSET_FILE} has changed since the snapshot was taken, so someone has "
                                         "used the folder since. Run `recover`, then take a new snapshot",
                       files=[PLAYSET_FILE])
    try:
        data = json.loads(raw.decode("utf-8-sig"))
        mods = data["enabledMods"]
        if not isinstance(mods, list) or not all(isinstance(m, dict) and isinstance(m.get("path"), str)
                                                 for m in mods):
            raise ValueError('"enabledMods" is not a list of {"path": "…"}')
    except Exception as exc:    # any failure to read it: not UTF-8, not JSON, nested too deep, not a playset
        raise _Refused("playset_unwritable", f"{path} cannot be read as a playset ({type(exc).__name__}: "
                                             f"{str(exc)[:200]}). Nothing was written") from None
    if mode == "mod_only":
        kept = [m for m in mods if _folder_key(m["path"]) == _folder_key(this_mod)]
        if not kept:
            raise _Refused("mod_not_in_playset", f"--playset mod_only keeps this mod, and the playset enables no mod "
                                                 f"at its deployed folder, {this_mod} (mod_deploy_target): enable it "
                                                 "in the launcher, or check mod_deploy_target. Nothing was written",
                           enabled=[m["path"] for m in mods])
    else:
        kept = list(mods)
    for added in add_mods:
        if all(_folder_key(m["path"]) != _folder_key(added) for m in kept):
            kept.append({"path": added})
    enabled = [m["path"] for m in kept]
    if kept == mods:
        return _Playset(mode, enabled, None)
    data["enabledMods"] = kept
    try:
        return _Playset(mode, enabled, json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))
    except Exception as exc:    # a lone surrogate the owner's file spelled as an escape; nesting too deep to write
        raise _Refused("playset_unwritable", f"{path} cannot be written back ({type(exc).__name__}: "
                                             f"{str(exc)[:200]}). Nothing was written") from None


def _record_playset(snap: snapshot.Snapshot, playset: _Playset) -> None:
    """Journal `playset` (mode, enabled paths, and the SHA-256 of the bytes `launch` is about to write, when it
    writes any), or raise _Refused, having written nothing. Journaled before the write: an entry for a write
    that then fails leaves the file the snapshot's, which nothing judges; a write with no entry would be held."""
    fields = {"mode": playset.mode, "enabled": playset.enabled}
    if playset.data is not None:
        fields["sha256"] = hashlib.sha256(playset.data).hexdigest()
    try:
        snapshot.record(snap, "playset", **fields)
    except OSError as exc:
        raise _Refused("playset_unwritable", f"the journal could not take the `playset` entry ({exc}), so the playset "
                                             f"was not written. {_CLAIM_STAYS}") from None


def _write_playset(snap: snapshot.Snapshot, user: Path, data: bytes) -> tuple[int, int]:
    """Write `data` over the owner's playset file by temp name and rename, and return the file's (size,
    mtime_ns) as read back right after the rename; or raise _Refused, leaving it as it is. Right before the
    rename the file must still be the snapshot's: the owner's launcher may have written it since it was read.
    The temp name is restore's own, which `compare` skips and the next `restore` sweeps."""
    target = user / PLAYSET_FILE
    temp = user / _PLAYSET_TEMP
    try:
        with open(temp, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if _sha256(target) != snap.files[PLAYSET_FILE].sha256:
            raise _Refused("playset_unwritable", f"{PLAYSET_FILE} changed after `launch` read it (the launcher may "
                                                 f"have written it), so it was left as it is. {_CLAIM_STAYS}")
        os.replace(temp, target)
    except OSError as exc:
        raise _Refused("playset_unwritable", f"{target} could not be written ({exc}), so it is as it was. "
                                             f"{_CLAIM_STAYS}") from None
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp)
    try:
        st = os.lstat(target)
    except OSError as exc:
        raise _Refused("playset_unwritable", f"{target} was written but could not be read back ({exc}); the "
                                             "owner's playset goes back when the snapshot is finished. "
                                             f"{_CLAIM_STAYS}") from None
    return st.st_size, st.st_mtime_ns


def _record_written(snap: snapshot.Snapshot, written: tuple[int, int]) -> None:
    """Journal `playset_written`: the size and mtime_ns of the file `launch` just wrote, as read back. With them,
    the same bytes written again later (by the owner's launcher) carry another time and are not taken for
    `launch`'s write (`_is_launchs_write`). Raises _Refused if the journal cannot take it: a journal that fails
    here would fail the game's `started` too, so nothing starts."""
    try:
        snapshot.record(snap, "playset_written", size=written[0], mtime_ns=written[1])
    except OSError as exc:
        raise _Refused("playset_unwritable", f"{PLAYSET_FILE} was written, but the journal could not take its size "
                                             f"and time ({exc}); the owner's playset goes back, known by its hash, "
                                             f"when the snapshot is finished. {_CLAIM_STAYS}") from None


def cmd_watch(args) -> tuple[dict, int]:
    """Follow the game `launch` started for the snapshot's run: a `heartbeat` at
    each look that lists it, `game_exited` at the first look that succeeds
    without it. Restore judges later changes against these times, so they must
    be written while the game runs and not when restore is called.

    `watch` never adopts a game: by its creation time alone the run's game
    cannot be told from one the owner starts. It follows only the process
    `launch` recorded (pid and start time). If that process is already gone at
    the first look, nobody saw when it exited: no exit is recorded, and restore
    judges against the last heartbeat, or holds if the gap before this `watch`
    was too long (below). Run again after it died, it picks the same process
    up; after `game_exited` it refuses.

    A look that fails, or that cannot read the run's game's start time, is not
    taken for an exit: `watch` looks again, and after WATCH_LOOK_TRIES such
    looks in a row it stops without recording one. A look that finds the game
    gone after a failed look since the last heartbeat records no exit either:
    the game may have exited at any time in that stretch, and someone may have
    played since.

    Every look that lists another Victoria 3 process records it once as
    `other_game` (pid, start time): it may be the owner's, writing the same
    files, so `restore` and `recover` hold the run (`other_game_ran`).

    Each failed look is journaled (`look_failed`). A first `watch` journals
    `watching` with the seconds since `started`; one run on a journal some
    `watch` has written to before journals `watch_resumed` with the seconds
    since the game was last seen alive. During a failed look, a gap of more
    than WATCH_FIRST_GAP_S before the first `watch`, or one of more than
    WATCH_RESUME_GAP_S before a resumed one, nobody saw whether another game
    ran, so `restore` and `recover` hold the run (`unwatched_stretch`). If an
    entry cannot be written, `watch` stops (`journal_unwritable`), recording
    no exit."""
    _user, backups = _paths()
    snap = _find(backups, args.id)
    journal = snapshot.journal(snap)
    events = [str(e.get("event")) for e in journal]
    starts = [e for e in journal if e.get("event") == "started"]
    try:
        if not 0 < args.interval <= WATCH_MAX_INTERVAL_S:
            raise _Refused("bad_interval", f"--interval must be more than 0 and at most {WATCH_MAX_INTERVAL_S:g} "
                                           "seconds: an exit is recorded up to one interval late")
        if any(v in events for v in _VERDICTS):
            raise _Refused("already_finished", f"snapshot {snap.id} already has a verdict")
        if "game_exited" in events:
            raise _Refused("already_exited", f"the run's game has exited: run `restore {snap.id}`")
        if not starts and _claimed(snap):
            raise _Refused("not_recorded", f"a `launch` claimed snapshot {snap.id} but recorded no start. If a "
                                           "`launch` is still running, wait for it and run `watch` again. If not, "
                                           "its reply or its journal write was lost, and a game it started is not "
                                           "recorded: nothing is adopted, any game running counts as another "
                                           "game, and `restore` and `recover` hold beside it")
        if not starts:
            raise _Refused("not_started", f"no game was launched for snapshot {snap.id}: start the game with "
                                          f"`launch {snap.id}`. `watch` never adopts a game")
        proc = _proc(starts[-1])
        if proc is None:
            raise _Refused("unreadable_start", f"the journal's last `started` entry cannot be read: {starts[-1]!r}")
        if proc.created == gate.UNKNOWN_START:
            raise _Refused("unknown_start", f"`launch` could not read the start time of pid {proc.pid}, so it "
                                            "cannot be told from another game: nothing is recorded. Wait until "
                                            f"`gate` shows no game at all, then `restore {snap.id}`: it judges the "
                                            "files against the start and holds any written after it")
        seen = {(str(e.get("pid")), str(e.get("created"))) for e in journal if e.get("event") == "other_game"}
        _begin_watch(snap, journal)
        _first_look(snap, proc, seen)
        beats = _follow(snap, proc, args.interval, seen)
    except _Refused as refusal:
        return dict(refusal.result, id=snap.id), 2
    return {"id": snap.id, "pid": proc.pid, "created": proc.created, "heartbeats": beats, "exited": True}, 0


def _record(snap: snapshot.Snapshot, event: str, **fields) -> None:
    """Journal one of `watch`'s entries, or raise _Refused: without it `watch` must not go on to record an exit."""
    try:
        snapshot.record(snap, event, **fields)
    except OSError as exc:
        raise _Refused("journal_unwritable", f"`watch` could not write `{event}` into the journal ({exc}), so it "
                                             "stops, recording no exit: `restore` judges the files against the last "
                                             "heartbeat. Run `watch` again once the journal can be written",
                       event=event) from None


def _begin_watch(snap: snapshot.Snapshot, journal: list[dict]) -> None:
    """Journal `watching` on a first run, or `watch_resumed` when a `watch` has written to this journal before,
    each with `gap_s`: the seconds, by the backup drive's clock, since the run's game was last seen alive (for
    `watching`, its `started`; for `watch_resumed`, its last `heartbeat`, else `started`). None when no time
    can be read, which holds like a long gap."""
    resumed = any(e.get("event") in _WATCH_EVENTS for e in journal)
    kinds = ("started", "heartbeat") if resumed else ("started",)
    times = [t for t in (_when(str(e.get("at"))) for e in journal if e.get("event") in kinds) if t is not None]
    try:
        now = snapshot._drive_clock(snap.dir)
    except OSError as exc:
        raise _Refused("journal_unwritable", f"`watch` could not read the backup drive's clock ({exc}), so it "
                                             "stops, recording no exit. Run `watch` again once it can") from None
    gap = round((now - max(times)).total_seconds(), 1) if times else None
    _record(snap, "watch_resumed" if resumed else "watching", gap_s=gap)


def _look(snap: snapshot.Snapshot, proc: gate.ProcId, seen: set[tuple[str, str]]) -> list[gate.ProcId] | None:
    """The running games, or None (journaled as `look_failed`) when the look failed, or when it lists the run's
    game's pid with a start time it could not read (that may still be the run's game). Each game in the listing
    other than the run's is recorded as `other_game` the first time it is seen (`seen` holds the pid and start
    time of those recorded)."""
    try:
        games = gate.list_games()
    except gate.GateError as exc:
        _record(snap, "look_failed", why=f"the process listing failed: {str(exc)[:200]}")
        return None
    for game in games:
        key = (str(game.pid), str(game.created))
        if game != proc and game != gate.ProcId(proc.pid, gate.UNKNOWN_START) and key not in seen:
            _record(snap, "other_game", pid=game.pid, created=game.created)
            seen.add(key)
    if gate.ProcId(proc.pid, gate.UNKNOWN_START) in games:
        _record(snap, "look_failed", why=f"the start time of pid {proc.pid} could not be read")
        return None
    return games


def _cannot_look(tries: int, **fields) -> _Refused:
    return _Refused("cannot_look", f"the game processes could not be listed {tries} times running, so no exit "
                                   "is recorded. Run `watch` again once they can: it picks the run's game up "
                                   "where it was", **fields)


def _first_look(snap: snapshot.Snapshot, proc: gate.ProcId, seen: set[tuple[str, str]]) -> None:
    """Check that the run's recorded game is running. Raises _Refused."""
    failures = 0
    while (games := _look(snap, proc, seen)) is None:
        failures += 1
        if failures >= WATCH_LOOK_TRIES:
            raise _cannot_look(failures, pid=proc.pid)
        _sleep(2.0)
    if proc not in games:
        raise _Refused("game_gone_unrecorded",
                       f"this run's game (pid {proc.pid}) is no longer running and nobody saw when it exited, so "
                       "no exit is recorded: `restore` will judge the files against the last heartbeat",
                       pid=proc.pid)


def _follow(snap: snapshot.Snapshot, proc: gate.ProcId, interval: float, seen: set[tuple[str, str]]) -> int:
    """Record a heartbeat at each look that shows `proc`, and `game_exited` at the first that shows it gone;
    return the number of heartbeats. Raises _Refused, recording no exit, after WATCH_LOOK_TRIES failed looks
    in a row, or when the game is gone at a look after a failed one since the last heartbeat (`game_exited`
    would then be stamped up to WATCH_LOOK_TRIES looks late, after writes that may be the owner's)."""
    beats = 0
    failures = 0
    failed_since_beat = False
    while True:
        _sleep(interval)
        games = _look(snap, proc, seen)
        if games is None:
            failures += 1
            failed_since_beat = True
            if failures >= WATCH_LOOK_TRIES:
                raise _cannot_look(failures, pid=proc.pid, heartbeats=beats)
            continue
        failures = 0
        if proc not in games:
            if failed_since_beat:
                raise _Refused("game_gone_unrecorded",
                               f"this run's game (pid {proc.pid}) is gone, and a look failed since it was last seen, "
                               "so when it exited is not known and no exit is recorded: `restore` will judge the "
                               "files against the last heartbeat", pid=proc.pid, heartbeats=beats)
            break
        _record(snap, "heartbeat")
        beats += 1
        failed_since_beat = False
    _record(snap, "game_exited")
    return beats


@_takes_turns("restore")
def cmd_restore(args) -> tuple[dict, int]:
    """Put the owner's files back. This never writes a time into the journal:
    when the run ended is what `launch` and `watch` recorded while it
    happened. With no such record, anything that would need judging is held.
    A run during which `watch` saw another game is held (`other_game_ran`),
    changing nothing else, as is one it lost sight of (`unwatched_stretch`). With
    no `started` nothing was launched, so `logs/` and the owner's own saves are
    whoever played since: `logs/` is left alone and the saves are not compared
    (`manual_save_changed`). A snapshot a `launch` may still be on its way to recording
    a start for gets no verdict (`launch_in_flight`). Before judging, the
    playset `launch` wrote for the run is put back when it is provably still
    the harness's own and no game runs, whatever the verdict
    (`_settle_playset`); beside a game the reply says `playset_left`."""
    user, backups = _paths()
    snap = _find(backups, args.id)
    age = _in_flight_age(snap)
    if age is not None:
        return {"held": False, "refused": "launch_in_flight", "id": snap.id,
                "detail": _in_flight_detail(snap, age)}, 2
    games = gate.list_games()
    mine = _started(snap)
    if mine is not None and mine in games:
        return {"held": False, "refused": "game_still_up", "id": snap.id,
                "detail": f"this run's own game (pid {mine.pid}, started by `launch`) is still running: wait "
                          "for it to exit and for `watch` to return, then restore"}, 2
    age = _since_last_seen_alive(snap)
    if age is not None and age < WATCH_RECORDING_S:
        return {"held": False, "refused": "watch_still_recording", "id": snap.id,
                "detail": f"`watch` last wrote a sign of this run's game {max(age, 0):.0f} s ago and has not "
                          "recorded its exit: wait for `watch` to return, then restore. If `watch` has already "
                          "returned without recording an exit (game_gone_unrecorded, cannot_look) or died, run "
                          f"`restore` again {WATCH_RECORDING_S:g} s after that time"}, 2
    notes: dict = {}
    try:
        _settle_playset(snap, user, bool(games), notes)
        started = "started" in _events(snap)    # nothing launched: logs/ and the saves are whoever played since
        out = _unvouched_hold(snap) or restore.restore(
            snap, user, other_game_running=bool(games), logs=started, saves=started,
            run_logs_dir=Path(args.run_logs) if args.run_logs else None)
    except OSError as exc:
        return {"held": False, "refused": "error", "detail": str(exc), **notes}, 2
    return _reply(out, notes), 2 if out.held else 0


def _reply(out: restore.Outcome, notes: dict) -> dict:
    """The Outcome as printed, with `_settle_playset`'s notes; a playset put back is listed in `restored`."""
    result = _outcome(out)
    if notes.get("playset_restored") and PLAYSET_FILE not in result["restored"]:
        result["restored"] = [PLAYSET_FILE, *result["restored"]]
    return {**result, **notes}


def _settle_playset(snap: snapshot.Snapshot, user: Path, game_running: bool, notes: dict) -> None:
    """Before a snapshot is judged, undo `launch`'s playset write for its run when it is provably still the
    harness's own (`_launchs_live_write`), whatever the verdict then is. The write is not the owner's work, so
    putting their copy back touches nothing of theirs; left in place after a hold, the next `snapshot` would
    record it as their playset and the next `launch` would run with it.

    With no game running: a temp a killed write left is swept, the owner's copy goes back from the store (its
    hash checked against the manifest; the file's size, time and bytes looked at again just before the rename),
    `playset_restored` is journaled, and `notes` gets `playset_restored`. A game running may be anyone's, so the
    file is left as it is, and `notes` gets `playset_left` and the remedy. `notes` is filled before the journal
    write, so a caller reporting a failure can still say the playset went back. Raises OSError as restore does
    (a missing or damaged stored copy), changing nothing."""
    if not any(e.get("event") == "playset" for e in snapshot.journal(snap)):
        return
    if game_running:
        if _launchs_live_write(snap, user) is not None:
            notes.update(playset_left=True, playset_detail=(
                f"{PLAYSET_FILE} still holds the playset `launch` wrote for this run: a game is running, so it is "
                f"left as it is. Once no game is running, run `restore {snap.id}`: it puts the owner's playset back "
                "and holds again for anything else. Until then `snapshot` and `launch` refuse "
                "(playset_not_restored), and `recover` does not look at a held snapshot again"))
        return
    with contextlib.suppress(FileNotFoundError):
        os.unlink(user / _PLAYSET_TEMP)                 # the harness's own temp, never the owner's file
    live = _launchs_live_write(snap, user)
    if live is None:
        return
    sha, seen = live
    backup_root = restore._backup_root(snap)
    restore._check_store(backup_root, snap, [PLAYSET_FILE])
    entry, target = snap.files[PLAYSET_FILE], user / PLAYSET_FILE
    temp = restore._stage(restore._store_blob(backup_root, entry.sha256), entry, target)  # hash-checked, its time
    try:
        # The last look, right before the rename: the same size and time, and the same bytes (a write that kept
        # the size and the time would pass the first alone). If it is no longer `launch`'s write, leave it.
        try:
            still = restore._signature(target, follow=False) == seen and _sha256(target) == sha
        except FileNotFoundError:
            still = False
        if not still:
            return
        os.replace(temp, target)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp)
    notes["playset_restored"] = True
    snapshot.record(snap, "playset_restored", sha256=sha)


def _launchs_live_write(snap: snapshot.Snapshot, user: Path) -> tuple[str, tuple[int, int]] | None:
    """The SHA-256 and (size, mtime_ns) of the live playset file when it is this snapshot's run's write to put
    back, else None: the journal's last `playset` entry carries a SHA-256 and is unanswered (`_answered`);
    this is the newest snapshot with a `playset` entry at all (an older one's write can coincide byte for byte
    with a newer one's, with `mod_only` even after the owner changed their other mods, and its copy would then
    go back over the owner's current playset); the snapshot holds the file; and the file is still that write
    (`_is_launchs_write`: its bytes, and its size and time when `launch` journaled them)."""
    journal = snapshot.journal(snap)
    entries = [i for i, e in enumerate(journal) if e.get("event") == "playset"]
    if not entries or PLAYSET_FILE not in snap.files:
        return None
    sha = journal[entries[-1]].get("sha256")
    if not isinstance(sha, str) or not _SHA256_HEX.fullmatch(sha):
        return None
    if _answered(journal, entries[-1]):
        return None
    every = snapshot.all_snapshots(restore._backup_root(snap))
    ids = [s.id for s in every]
    if snap.id not in ids:
        return None
    if any(e.get("event") == "playset" for s in every[ids.index(snap.id) + 1:] for e in snapshot.journal(s)):
        return None
    live = _live_playset(user)
    if live is None or not _is_launchs_write(journal, entries[-1], *live):
        return None
    return live


def _unvouched_hold(snap: snapshot.Snapshot) -> restore.Outcome | None:
    """Hold, changing nothing, a run whose files nothing vouches for: `watch` saw another game (`other_game_ran`:
    its writes cannot be told from the run's), or lost sight of the run's game at a failed look or across a gap
    of more than WATCH_RESUME_GAP_S before a resumed `watch` (`unwatched_stretch`: nobody saw then whether
    another game ran). None when neither. A run already restored is left as it is, as `restore.restore` leaves
    one beside a running game."""
    journal = snapshot.journal(snap)
    others = [f"pid {e.get('pid')} (started {e.get('created')})" for e in journal if e.get("event") == "other_game"]
    failed = sum(1 for e in journal if e.get("event") == "look_failed")
    bounds = {"watch_resumed": WATCH_RESUME_GAP_S, "watching": WATCH_FIRST_GAP_S}
    long_gaps = [e.get("gap_s") for e in journal if e.get("event") in bounds
                 and not _gap_within(e.get("gap_s"), bounds[e["event"]])]
    if not (others or failed or long_gaps):
        return None
    verdicts = [e.get("event") for e in journal if e.get("event") in _VERDICTS]
    if verdicts and verdicts[-1] == "restored":
        return restore.Outcome([], [], False, "already_restored")
    if others:
        snapshot.record(snap, "held", reason="other_game_ran", games=others)
        return restore.Outcome([], [], True, "other_game_ran")
    snapshot.record(snap, "held", reason="unwatched_stretch", looks_failed=failed, gaps_s=long_gaps)
    return restore.Outcome([], [], True, "unwatched_stretch")


def _gap_within(gap, bound: float) -> bool:
    """Whether a journaled `gap_s` is a number no larger than `bound` (an unreadable one is not)."""
    return isinstance(gap, (int, float)) and not isinstance(gap, bool) and gap <= bound


def _in_flight_age(snap: snapshot.Snapshot) -> float | None:
    """The claim's age in seconds, by the backup drive's clock, when the snapshot is claimed, has no `started`,
    and the claim is younger than LAUNCH_IN_FLIGHT_S: a `launch` may be about to record its start. Else None."""
    if "started" in _events(snap):
        return None
    try:
        made = os.stat(snap.dir / LAUNCH_CLAIM).st_mtime
    except FileNotFoundError:
        return None
    age = snapshot._drive_clock(snap.dir).timestamp() - made
    return age if age < LAUNCH_IN_FLIGHT_S else None


def _in_flight_detail(snap: snapshot.Snapshot, age: float) -> str:
    return (f"a `launch` claimed snapshot {snap.id} {max(age, 0):.0f} s ago and has not recorded a start: it may "
            "be about to, and its game may not be listed yet. Nothing was recorded. Run this again once that "
            f"`launch` has replied, or {LAUNCH_IN_FLIGHT_S:g} s after the claim")


_SIGNS_OF_LIFE = ("started", "heartbeat", "watching", "watch_resumed")


def _since_last_seen_alive(snap: snapshot.Snapshot) -> float | None:
    """Seconds, by the backup drive's clock, since the journal's latest sign of life (`started`, `heartbeat`,
    `watching` or `watch_resumed`), when it has a `started` and no `game_exited` (a `watch` may still be
    recording); else None. Negative if that time is ahead of the drive's clock."""
    journal = snapshot.journal(snap)
    events = [e.get("event") for e in journal]
    if "started" not in events or "game_exited" in events:
        return None
    times = [t for t in (_when(str(e.get("at"))) for e in journal if e.get("event") in _SIGNS_OF_LIFE)
             if t is not None]
    if not times:
        return None
    return (snapshot._drive_clock(snap.dir) - max(times)).total_seconds()


@_takes_turns("recover")
def cmd_recover(args) -> tuple[dict, int]:
    """Finish the runs a dead session left: first the started ones, then, if those all finished, the
    snapshots armed for a run whose start was never recorded.

    The started ones go as `restore.recover` takes them, newest first, stopping at the first hold or error,
    and nothing at all while the last recorded game of any of them is up (`game_still_up`), or when a `started`
    cannot be read. Two things are added: any game running holds (`other_game_running`), even one an earlier
    `started` of the run names, since a game's pid and start time alone say nothing of whose files it
    writes; and a run during which `watch` saw another game holds (`other_game_ran`), as does one it lost
    sight of (`unwatched_stretch`). A run whose last sign of life is under WATCH_RECORDING_S old is reported
    `watch_still_recording`, as `restore` refuses it, and the unwinding stops there, nothing recorded. Each
    run judged gets its playset settled first, as in `restore` (`_settle_playset`). A held snapshot is never
    looked at again here: `restore <id>` does that."""
    user, backups = _paths()
    games = gate.list_games()
    stack = list(reversed(restore.unfinished(backups)))
    runs: list[dict] = []
    up = []
    for snap in stack:
        last = _last_started(snap)
        if last is None:
            return {"runs": [dict(_outcome(restore.Outcome([], [], False, "error: its last `started` entry cannot "
                                                                         "be read")), id=snap.id)]}, 2
        up.append(last in games)
    if any(up):
        return {"runs": [dict(_outcome(restore.Outcome([], [], False, "game_still_up")), id=s.id)
                         for s in stack]}, 2
    for snap in stack:
        notes: dict = {}
        try:
            age = _since_last_seen_alive(snap)
            if age is not None and age < WATCH_RECORDING_S:   # as `restore` refuses: leave it, record nothing
                runs.append(dict(_outcome(restore.Outcome([], [], False, "watch_still_recording")), id=snap.id))
                break
            _settle_playset(snap, user, bool(games), notes)
            out = _unvouched_hold(snap) or restore.restore(snap, user, other_game_running=bool(games))
        except Exception as exc:
            runs.append(dict(_outcome(restore.Outcome([], [], False, f"error: {exc}")), id=snap.id, **notes))
            break
        runs.append(dict(_reply(out, notes), id=snap.id))
        if out.held:
            break
    if all(not r["held"] and not r["reason"] for r in runs):
        runs += _recover_never_started(backups, user)
    clean = all(not r["held"] and not r["reason"] for r in runs)
    return {"runs": runs}, 0 if clean else 2


def _recover_never_started(backups: Path, user: Path) -> list[dict]:
    """Restore or hold each snapshot armed for a run that never recorded `started`, newest first, stopping at
    the first hold or error, as for the started ones. `launch` records `started` the moment the game exists,
    so nothing was launched under most such snapshots (the session died before `launch`, or `launch`
    refused). Under some a game may run unrecorded: `launch` started it and then lost its reply (GateError)
    or its journal write (not_recorded), or a session died between the start and the record. That is still
    safe: any game running may be the owner's, so this holds (`other_game_running`). With none, restore puts
    the folder back when nothing needs judging and holds (`no_reference_time`) otherwise, leaving `logs/`
    alone and the owner's own saves uncompared: with nothing recorded, they are whoever played since. A session's own snapshot, between its
    `snapshot` and `launch`, is finished too: `launch` then refuses `already_finished`, starting nothing.
    A claimed one whose claim is younger than LAUNCH_IN_FLIGHT_S gets no verdict: a `launch` may be about to
    record its start, its game not yet listed. It is reported (`launch_in_flight`) and the unwinding stops. The
    playset a failed start left is put back first, held or not (`_settle_playset`)."""
    never_started = [s for s in _open_snapshots(backups) if "started" not in _events(s)]
    if not never_started:
        return []
    runs = []
    try:
        games = gate.list_games()       # a fresh look: the restores before this one took time
    except gate.GateError as exc:
        return [dict(_outcome(restore.Outcome([], [], False, f"error: {exc}")), id=never_started[-1].id)]
    for snap in reversed(never_started):
        notes: dict = {}
        try:
            if _in_flight_age(snap) is not None:
                runs.append(dict(_outcome(restore.Outcome([], [], False, "launch_in_flight")), id=snap.id))
                break
            _settle_playset(snap, user, bool(games), notes)
            out = _unvouched_hold(snap) or restore.restore(snap, user, other_game_running=bool(games), logs=False,
                                                           saves=False)
        except Exception as exc:
            runs.append(dict(_outcome(restore.Outcome([], [], False, f"error: {exc}")), id=snap.id, **notes))
            break
        runs.append(dict(_reply(out, notes), id=snap.id))
        if out.held:
            break
    return runs


def cmd_held(args) -> tuple[dict, int]:
    _user, backups = _paths()
    return {"held": [s.id for s in restore.held(backups)]}, 0


@_takes_turns("selftest-restore")
def cmd_selftest_restore(args) -> tuple[dict, int]:
    """Snapshot the real user-data folder, restore it into an empty temp
    folder, and compare every file's hash with its manifest entry. Reads the
    user-data folder; writes only under the backup root, where the temp
    folder also sits, so the check runs on a Windows drive and not on /tmp.

    Contents must match exactly. Times are compared within two seconds and
    the coarsened ones counted: a file time set from WSL on a Windows drive
    keeps whole seconds only (measured on C: and D:, both NTFS, 2026-11-10),
    so a restored file's time is its original time cut to the second."""
    user, backups = _paths()
    games = gate.list_games()
    if games:
        return _game_running(games, "a snapshot taken while a game writes its files catches them mid-run").result, 2
    snap = snapshot.take(user, backups)
    mismatched = []
    wrong_time = []
    coarsened = 0
    with tempfile.TemporaryDirectory(prefix="selftest_", dir=backups) as tmp:
        target = Path(tmp)
        for rel in snap.files:
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
        out = restore.restore(snap, target, other_game_running=False, saves=False)   # the scratch folder holds no saves
        for rel, entry in snap.files.items():
            path = target / rel
            if not path.is_file() or _sha256(path) != entry.sha256:
                mismatched.append(rel)
                continue
            drift = abs(path.stat().st_mtime_ns - entry.mtime_ns)
            if drift > SELFTEST_TIME_TOLERANCE_NS:
                wrong_time.append(rel)
            elif drift:
                coarsened += 1
    ok = not mismatched and not wrong_time and not out.held and len(out.restored) == len(snap.files)
    return {"match": ok, "id": snap.id, "files": len(snap.files), "mismatched": mismatched,
            "wrong_time": wrong_time, "times_coarsened": coarsened}, 0 if ok else 2


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m game_qa", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="verb", required=True)

    p = sub.add_parser("gate", help="a dry check: would a launch be allowed now? (`launch` runs it itself)")
    p.add_argument("--permission", required=True,
                   help="where the permission to launch came from (asked, or granted for this session)")
    p.add_argument("--owner-confirmed-busy", action="store_true",
                   help="the owner was asked about the busy GPU and said to go ahead")
    p.set_defaults(run=cmd_gate)

    p = sub.add_parser("snapshot", help="snapshot the owner's saves, settings and logs")
    p.add_argument("--save", action="append", default=[], metavar="NAME",
                   help="a save the run will load, also snapshotted (repeatable)")
    p.set_defaults(run=cmd_snapshot)

    p = sub.add_parser("restore", help="put the owner's files back as a snapshot has them")
    p.add_argument("id")
    p.add_argument("--run-logs", metavar="DIR",
                   help="copy the run's own logs here first (default: run_logs/ in the snapshot's folder)")
    p.set_defaults(run=cmd_restore)

    p = sub.add_parser("launch", help="the gate's checks, then start the game for a snapshot's run and record it",
                       description="Everything after `--` is passed to victoria3.exe as it is; nothing is added. "
                                   f"--playset mod_only and --add-mod rewrite {PLAYSET_FILE} for the run; "
                                   "`restore` puts the owner's back.")
    p.add_argument("id")
    p.add_argument("--permission", required=True,
                   help="where the permission to launch came from (asked, or granted for this session)")
    p.add_argument("--owner-confirmed-busy", action="store_true",
                   help="the owner was asked about the busy GPU and said to go ahead")
    p.add_argument("--playset", choices=PLAYSET_MODES, default="current",
                   help="current (the default): the mods the owner has enabled; mod_only: only this mod's "
                        "deployed folder (mod_deploy_target)")
    p.add_argument("--add-mod", action="append", default=[], metavar="WINDOWS_PATH",
                   help="a mod folder to enable for the run as well, as Windows names it (repeatable)")
    p.set_defaults(run=cmd_launch)

    p = sub.add_parser("watch", help="follow the game `launch` started, recording that it is alive and its exit")
    p.add_argument("id")
    p.add_argument("--interval", type=float, default=WATCH_INTERVAL_S, help="seconds between looks")
    p.set_defaults(run=cmd_watch)

    for name, fn, text in (("recover", cmd_recover,
                            "finish the runs a dead session left, and clear snapshots nothing was launched under; "
                            "never run it between your own `snapshot` and `launch` (it would finish that "
                            "snapshot, and `launch` would then refuse already_finished)"),
                           ("held", cmd_held, "list snapshots held because the owner played since"),
                           ("selftest-restore", cmd_selftest_restore,
                            "prove a snapshot of the real folder restores, changing nothing in it")):
        sub.add_parser(name, help=text).set_defaults(run=fn)
    client.add_verbs(sub)

    argv = list(sys.argv[1:] if argv is None else argv)
    game_args: list[str] = []
    if "--" in argv:  # split by hand: argparse's handling of `--` differs between Python versions
        cut = argv.index("--")
        argv, game_args = argv[:cut], argv[cut + 1:]
    args = parser.parse_args(argv)
    if args.verb != "launch" and game_args:
        parser.error(f"only `launch` takes game arguments after `--`, not `{args.verb}`")
    args.game_args = game_args
    try:
        result, code = args.run(args)
    except Exception as exc:  # every failure is one JSON object: BackupRootError, GateError, OSError, ...
        result, code = {"refused": type(exc).__name__, "detail": str(exc)}, 2
    # ASCII, escapes and all: a reply can quote the owner's playset, which may spell a lone surrogate, and a UTF-8
    # stdout cannot print one.
    print(json.dumps(result, indent=1, ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
