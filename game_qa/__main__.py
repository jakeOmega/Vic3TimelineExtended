"""Command line of the in-game QA harness, part 1: protecting the owner's files.

    python3 -m game_qa snapshot [--save NAME]...           # with no game running
    python3 -m game_qa launch <id> --permission "asked 12:40" -- -debug_mode -loadsave=NAME
                                                           # the gate's checks, then start the game and
                                                           # record its start: the only way to start it
    python3 -m game_qa watch <id> [--interval S]           # right after: records that the launched game is
                                                           # alive, and its exit (S at most 10)
    python3 -m game_qa restore <id>                        # after `watch` has returned
    python3 -m game_qa gate --permission "asked 12:40"     # dry check: would a launch be allowed now?
    python3 -m game_qa recover                             # finish runs a dead session left
    python3 -m game_qa held                                # snapshots kept because the owner played since
    python3 -m game_qa selftest-restore                    # prove a snapshot restores, touching nothing

Each verb prints one JSON object. Exit 0 on success, 2 on a refusal, a hold or an error. Usage errors are
argparse's (a message on stderr, exit 2).
Spec: docs/superpowers/specs/2026-11-10-in-game-qa-harness-design.md §§ 5.2–5.3.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

from game_qa import gate, restore, snapshot

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
# Created in the snapshot's folder with O_EXCL by the one `launch` that may start the game; it counts as a
# start. A claim with no `started` is a launch whose record was lost (its reply, or the journal write).
LAUNCH_CLAIM = "launch.claim"
_END_DATE = re.compile(r"[0-9]{1,4}\.[0-9]{1,2}\.[0-9]{1,2}")   # -run_until=1836.2.10, matched whole
_VERDICTS = ("restored", "held")
_sleep = time.sleep       # patched in tests


class UnknownSnapshotError(LookupError):
    """No snapshot has the id given."""


class _Refused(Exception):
    """A refusal of `watch` or `launch`, carried out of their helpers as the JSON object to print."""

    def __init__(self, reason: str, detail: str, **fields):
        super().__init__(reason)
        self.result = {"refused": reason, "detail": detail, **fields}


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
    return {"restored": out.restored, "removed": out.removed, "held": out.held, "reason": out.reason}


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
    extra = ["save games/" + (name if name.endswith(".v3") else name + ".v3") for name in args.save]
    snap = snapshot.take(user, backups, extra=extra)
    snapshot.record(snap, "armed")
    pruned = restore.prune(backups, keep=KEEP_SNAPSHOTS, current=snap.id)
    return {"id": snap.id, "files": len(snap.files), "pruned": pruned,
            "held": [s.id for s in restore.held(backups)]}, 0


def _game_running(games: list[gate.ProcId], why: str) -> _Refused:
    return _Refused("game_running", f"a Victoria 3 process is running, and {why}. `gate` says whether this "
                                    "harness started it: if it did, finish that run first (its `watch`, then "
                                    "`restore <id>`, or `recover`); if not, it is the owner's: ask them, and "
                                    "never end it", games=_running(games))


def cmd_launch(args) -> tuple[dict, int]:
    """Start the game for a snapshot's run, after the gate's checks, and record its start at once.

    The only supported way to start the game: the journal names the process from the moment it exists, so
    no command ever has to guess which game is the run's. Nothing is started, and nothing recorded, unless
    the snapshot is armed with no `started`, no claim and no verdict; every argument can reach the game whole
    (`_check_arguments`); an unattended run (`handsoff` in any spelling) carries `-run_until=<y.m.d>`; the
    gate's checks pass (a stated permission, a usable backup root, no game this harness
    did not start, the GPU unless the owner confirmed); no Victoria 3 process at all is running (one
    snapshot, one game); and no file outside `logs/` has changed since the snapshot. That last one means
    someone has used the folder since: a start recorded now would date their writes before the run, and
    restore would put the old copies back over them. The folder, the journal and the processes are looked
    at again last; then the launch claims the snapshot (LAUNCH_CLAIM, created with O_EXCL, so of two
    launches on one id only one can start a game) and starts it.

    `started` (pid, start time, arguments) is recorded the moment the process exists. A start time
    PowerShell could not read is recorded as "unknown" and never looked up later: a process found by its pid
    alone could be another game that took the pid."""
    user, backups = _paths()
    snap = _find(backups, args.id)
    game_args = list(args.game_args)
    try:
        _launchable(snap)
        _check_arguments(game_args)
        _check_end_date(game_args)
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
        # The last looks, right before the start: the folder (slow: it hashes), then the journal and the processes.
        _check_unchanged(snap, user)
        _launchable(snap)
        games = gate.list_games()
        if games:
            raise _game_running(games, "one snapshot is for one game")
        _claim(snap)
    except _Refused as refused:
        return dict(refused.result, id=snap.id), 2
    try:
        proc = gate.start_game(exe_windows, game_args, cwd_windows)
    except gate.GateError as exc:
        return {"refused": "GateError", "id": snap.id,
                "detail": f"{exc}. Nothing was recorded: a game this started would count as another game "
                          "everywhere (`gate` and `launch` refuse beside it, `restore` and `recover` hold). The "
                          f"snapshot stays claimed, so `launch` refuses it: once no game runs, `restore {snap.id}` "
                          "finishes it, holding anything that changed"}, 2
    try:
        snapshot.record(snap, "started", pid=proc.pid, created=proc.created, args=game_args)
    except OSError as exc:
        return {"refused": "not_recorded", "id": snap.id, "pid": proc.pid, "created": proc.created,
                "detail": f"the game started (pid {proc.pid}) but its start could not be recorded: {exc}. It "
                          "counts as another game everywhere (`restore` and `recover` hold). This harness "
                          f"started it, so it may end pid {proc.pid}, but only while the game listing shows pid "
                          f"{proc.pid} with start time {proc.created}: a pid alone may be another game's by then"}, 2
    result = {"id": snap.id, "pid": proc.pid, "created": proc.created, "args": game_args}
    if proc.created == gate.UNKNOWN_START:
        result["detail"] = (f"the game's start time could not be read, so it is recorded as unknown: `watch` "
                            f"cannot tell pid {proc.pid} from another game and will refuse `unknown_start`. Once "
                            f"the game has closed, `restore {snap.id}` holds anything it wrote")
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
    owner's (spec § 5.3). Each argument is read without its leading `-` and `/`, in any case, split at its
    first `=`. `handsoff` in any spelling, also as a word of an argument with spaces in it, needs an argument
    `run_until=<y.m.d>` with nothing else in it."""
    words = [(name, value) for name, _sep, value in
             (word.lstrip("-/").lower().partition("=") for arg in game_args for word in arg.split())]
    whole = [(name, value if sep else None) for name, sep, value in
             (arg.lstrip("-/").lower().partition("=") for arg in game_args)]
    if any(name == "handsoff" for name, _ in words) and not any(
            name == "run_until" and value is not None and _END_DATE.fullmatch(value) for name, value in whole):
        raise _Refused("no_end_date", "an unattended run (-handsoff) must carry -run_until=<year.month.day>, such "
                                      "as -run_until=1836.2.10: without one it runs on and writes autosaves")


def _check_unchanged(snap: snapshot.Snapshot, user: Path) -> None:
    """Raise _Refused if a file outside `logs/` no longer matches the snapshot."""
    diff = restore.compare(snap, user)
    files = sorted(name for name in {*diff.changed, *diff.missing, *diff.added_in_set, *diff.created}
                   if not name.startswith("logs/"))
    if files:
        raise _Refused("stale_snapshot", "the folder has changed since the snapshot was taken, so someone has used "
                                         "it since: a run started now would make restore put the old copies back "
                                         "over theirs. Run `recover`: it judges this snapshot and holds it, unless "
                                         "the only change is a missing file, which it puts back. Then take a new "
                                         "snapshot", files=files)


def cmd_watch(args) -> tuple[dict, int]:
    """Follow the game `launch` started for the snapshot's run: a `heartbeat` at
    each look that lists it, `game_exited` at the first look that succeeds
    without it. Restore judges later changes against these times, so they must
    be written while the game runs and not when restore is called.

    `watch` never adopts a game: by its creation time alone the run's game
    cannot be told from one the owner starts. It follows only the process
    `launch` recorded (pid and start time). If that process is already gone at
    the first look, nobody saw when it exited: nothing is recorded, and restore
    judges against the last heartbeat. Run again after it died, it picks the
    same process up; after `game_exited` it refuses.

    A look that fails, or that cannot read the run's game's start time, is not
    taken for an exit: `watch` looks again, and after WATCH_LOOK_TRIES such
    looks in a row it stops without recording one. A look that finds the game
    gone after a failed look since the last heartbeat records no exit either:
    the game may have exited at any time in that stretch, and someone may have
    played since.

    Every look that lists another Victoria 3 process records it once as
    `other_game` (pid, start time): it may be the owner's, writing the same
    files, so `restore` and `recover` hold the run (`other_game_ran`)."""
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
                                            "cannot be told from another game: nothing is recorded, and once the "
                                            f"game has closed `restore {snap.id}` holds anything it wrote")
        seen = {(str(e.get("pid")), str(e.get("created"))) for e in journal if e.get("event") == "other_game"}
        _first_look(snap, proc, seen)
        beats = _follow(snap, proc, args.interval, seen)
    except _Refused as refusal:
        return dict(refusal.result, id=snap.id), 2
    return {"id": snap.id, "pid": proc.pid, "created": proc.created, "heartbeats": beats, "exited": True}, 0


def _look(snap: snapshot.Snapshot, proc: gate.ProcId, seen: set[tuple[str, str]]) -> list[gate.ProcId] | None:
    """The running games, or None when the look failed, or when it lists the run's game's pid with a start
    time it could not read (that may still be the run's game). Each game in the listing other than the run's
    is recorded as `other_game` the first time it is seen (`seen` holds the pid and start time of those
    recorded)."""
    try:
        games = gate.list_games()
    except gate.GateError:
        return None
    for game in games:
        key = (str(game.pid), str(game.created))
        if game != proc and game != gate.ProcId(proc.pid, gate.UNKNOWN_START) and key not in seen:
            snapshot.record(snap, "other_game", pid=game.pid, created=game.created)
            seen.add(key)
    if gate.ProcId(proc.pid, gate.UNKNOWN_START) in games:
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
        snapshot.record(snap, "heartbeat")
        beats += 1
        failed_since_beat = False
    snapshot.record(snap, "game_exited")
    return beats


def cmd_restore(args) -> tuple[dict, int]:
    """Put the owner's files back. This never writes a time into the journal:
    when the run ended is what `launch` and `watch` recorded while it
    happened. With no such record, anything that would need judging is held.
    A run during which `watch` saw another game is held (`other_game_ran`),
    changing nothing. With no `started` nothing was launched, so `logs/` is
    whoever played since, and is left alone."""
    user, backups = _paths()
    snap = _find(backups, args.id)
    games = gate.list_games()
    mine = _started(snap)
    if mine is not None and mine in games:
        return {"held": False, "refused": "game_still_up",
                "detail": f"this run's own game (pid {mine.pid}, started by `launch`) is still running: wait "
                          "for it to exit and for `watch` to return, then restore"}, 2
    age = _since_last_seen_alive(snap)
    if age is not None and age < WATCH_RECORDING_S:
        return {"held": False, "refused": "watch_still_recording",
                "detail": f"`watch` last recorded this run's game alive {max(age, 0):.0f} s ago and has not "
                          "recorded its exit: wait for `watch` to return, then restore. If `watch` has already "
                          "returned without recording an exit (game_gone_unrecorded, cannot_look) or died, run "
                          f"`restore` again {WATCH_RECORDING_S:g} s after that time"}, 2
    try:
        out = _other_game_hold(snap) or restore.restore(
            snap, user, other_game_running=bool(games), logs="started" in _events(snap),
            run_logs_dir=Path(args.run_logs) if args.run_logs else None)
    except OSError as exc:
        return {"held": False, "refused": "error", "detail": str(exc)}, 2
    return _outcome(out), 2 if out.held else 0


def _other_game_hold(snap: snapshot.Snapshot) -> restore.Outcome | None:
    """Hold, changing nothing, a run during which `watch` saw another game (`other_game` in the journal): its
    writes cannot be told from the run's. None when there is no such entry. A run already restored is left as
    it is, as `restore.restore` leaves one beside a running game."""
    journal = snapshot.journal(snap)
    others = [f"pid {e.get('pid')} (started {e.get('created')})" for e in journal if e.get("event") == "other_game"]
    if not others:
        return None
    verdicts = [e.get("event") for e in journal if e.get("event") in _VERDICTS]
    if verdicts and verdicts[-1] == "restored":
        return restore.Outcome([], [], False, "already_restored")
    snapshot.record(snap, "held", reason="other_game_ran", games=others)
    return restore.Outcome([], [], True, "other_game_ran")


def _since_last_seen_alive(snap: snapshot.Snapshot) -> float | None:
    """Seconds, by the backup drive's clock, since the journal's latest `started` or `heartbeat`, when it has
    a `started` and no `game_exited` (a `watch` may still be recording); else None. Negative if that time is
    ahead of the drive's clock."""
    journal = snapshot.journal(snap)
    events = [e.get("event") for e in journal]
    if "started" not in events or "game_exited" in events:
        return None
    times = [t for t in (_when(str(e.get("at"))) for e in journal if e.get("event") in ("started", "heartbeat"))
             if t is not None]
    if not times:
        return None
    return (snapshot._drive_clock(snap.dir) - max(times)).total_seconds()


def cmd_recover(args) -> tuple[dict, int]:
    """Finish the runs a dead session left: first the started ones, then, if those all finished, the
    snapshots armed for a run whose start was never recorded.

    The started ones go as `restore.recover` takes them, newest first, stopping at the first hold or error,
    and nothing at all while the last recorded game of any of them is up (`game_still_up`), or when a `started`
    cannot be read. Two things are added: any game running holds (`other_game_running`), even one an earlier
    `started` of the run names, since a game's pid and start time alone say nothing of whose files it
    writes; and a run during which `watch` saw another game holds (`other_game_ran`)."""
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
        try:
            out = _other_game_hold(snap) or restore.restore(snap, user, other_game_running=bool(games))
        except Exception as exc:
            runs.append(dict(_outcome(restore.Outcome([], [], False, f"error: {exc}")), id=snap.id))
            break
        runs.append(dict(_outcome(out), id=snap.id))
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
    alone: with nothing recorded, the logs are whoever played since. A session's own snapshot, between its
    `snapshot` and `launch`, is finished too: `launch` then refuses `already_finished`, starting nothing."""
    never_started = [s for s in _open_snapshots(backups) if "started" not in _events(s)]
    if not never_started:
        return []
    runs = []
    try:
        games = gate.list_games()       # a fresh look: the restores before this one took time
    except gate.GateError as exc:
        return [dict(_outcome(restore.Outcome([], [], False, f"error: {exc}")), id=never_started[-1].id)]
    for snap in reversed(never_started):
        try:
            out = _other_game_hold(snap) or restore.restore(snap, user, other_game_running=bool(games), logs=False)
        except Exception as exc:
            runs.append(dict(_outcome(restore.Outcome([], [], False, f"error: {exc}")), id=snap.id))
            break
        runs.append(dict(_outcome(out), id=snap.id))
        if out.held:
            break
    return runs


def cmd_held(args) -> tuple[dict, int]:
    _user, backups = _paths()
    return {"held": [s.id for s in restore.held(backups)]}, 0


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
        out = restore.restore(snap, target, other_game_running=False)
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
                       description="Everything after `--` is passed to victoria3.exe as it is; nothing is added.")
    p.add_argument("id")
    p.add_argument("--permission", required=True,
                   help="where the permission to launch came from (asked, or granted for this session)")
    p.add_argument("--owner-confirmed-busy", action="store_true",
                   help="the owner was asked about the busy GPU and said to go ahead")
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
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
