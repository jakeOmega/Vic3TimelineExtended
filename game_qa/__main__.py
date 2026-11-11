"""Command line of the in-game QA harness, part 1: protecting the owner's files.

    python3 -m game_qa gate --permission "asked 12:40"     # may the game be launched now?
    python3 -m game_qa snapshot [--save NAME]...           # before a launch, with no game running
    python3 -m game_qa watch <id> [--pid N]                # right after launching: records the game's
                                                           # start, that it is alive, and its exit
    python3 -m game_qa restore <id>                        # after `watch` has returned
    python3 -m game_qa recover                             # finish runs a dead session left
    python3 -m game_qa held                                # snapshots kept because the owner played since
    python3 -m game_qa selftest-restore                    # prove a snapshot restores, touching nothing

Each verb prints one JSON object. Exit 0 on success, 2 on a refusal, a hold or an error.
Spec: docs/superpowers/specs/2026-11-10-in-game-qa-harness-design.md §§ 5.2–5.3.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from game_qa import gate, restore, snapshot

MIN_FREE_BYTES = 2 * 1024**3
KEEP_SNAPSHOTS = 5
SELFTEST_TIME_TOLERANCE_NS = 2_000_000_000
WATCH_WAIT_S = 180.0      # how long `watch` waits for the game process to appear
WATCH_INTERVAL_S = 5.0    # between looks; a heartbeat is recorded at each
# `watch` adopts only a game created after the snapshot was armed and at most this long after it: a game
# started later may be the owner's. A launch slower than this needs a fresh snapshot.
WATCH_ADOPT_WINDOW_S = 600.0
WATCH_LOOK_TRIES = 5      # failed looks in a row after which `watch` stops, recording no exit
# A `started` or `heartbeat` younger than this, with no `game_exited`: `watch` is still recording, and a
# restore now would judge the game's exit writes against the last heartbeat. Three default intervals.
WATCH_RECORDING_S = 15.0
_VERDICTS = ("restored", "held")
_sleep = time.sleep       # patched in tests
_clock = time.monotonic   # patched in tests; `watch --wait` is measured on it, not by counting naps


class UnknownSnapshotError(LookupError):
    """No snapshot has the id given."""


class _Refused(Exception):
    """A refusal of `watch`, carried out of its helpers as the JSON object to print."""

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
                "detail": "an earlier snapshot has neither been restored nor held. If its game is open, close "
                          "it and wait for `watch` to return, then run `restore <id>`; for a run whose session "
                          "died, or one whose start was never recorded, run `recover`. Either puts the files "
                          "back or holds the snapshot, and a held snapshot does not block a new one"}, 2
    games = gate.list_games()
    if games:
        return _game_running(games), 2
    extra = ["save games/" + (name if name.endswith(".v3") else name + ".v3") for name in args.save]
    snap = snapshot.take(user, backups, extra=extra)
    snapshot.record(snap, "armed")
    pruned = restore.prune(backups, keep=KEEP_SNAPSHOTS, current=snap.id)
    return {"id": snap.id, "files": len(snap.files), "pruned": pruned,
            "held": [s.id for s in restore.held(backups)]}, 0


def _game_running(games: list[gate.ProcId]) -> dict:
    return {"refused": "game_running", "games": _running(games),
            "detail": "a Victoria 3 process is running: a snapshot taken while a game writes its files "
                      "captures them mid-run. Close it first"}


def cmd_watch(args) -> tuple[dict, int]:
    """Record the run's game in the snapshot's journal as it happens: `started`
    when the process appears, a `heartbeat` at each look, `game_exited` when a
    look shows it gone. Restore judges later changes against these times, so
    they must be written while the game runs and not when restore is called.

    Which game is the run's:
    - With no `started` in the journal: the process `--pid` names, or else the
      one game created after the snapshot was armed and at most
      WATCH_ADOPT_WINDOW_S after it. A game that was already running is the
      owner's, and so may be one started later.
    - With a `started`: that process only (same pid and creation time), so a
      `watch` that died is picked up again. If it is gone, nobody saw when it
      exited: nothing is recorded, and restore judges against the last heartbeat.
    - After `game_exited`: none. The run is over.

    A look that fails, or that cannot read the run's game's start time, is not
    taken for an exit: `watch` looks again, and after WATCH_LOOK_TRIES such
    looks in a row it stops without recording one."""
    _user, backups = _paths()
    snap = _find(backups, args.id)
    journal = snapshot.journal(snap)
    events = [str(e.get("event")) for e in journal]
    if any(v in events for v in _VERDICTS):
        return {"refused": "already_finished", "detail": f"snapshot {snap.id} already has a verdict"}, 2
    armed = next((_when(str(e.get("at"))) for e in journal if e.get("event") == "armed"), None)
    if armed is None:
        return {"refused": "not_armed", "detail": "this snapshot was not taken by `snapshot` for a run"}, 2
    if "game_exited" in events:
        return {"refused": "already_exited",
                "detail": f"the game of snapshot {snap.id}'s run has exited: run `restore {snap.id}`"}, 2
    starts = [e for e in journal if e.get("event") == "started"]
    try:
        if starts:
            proc = _proc(starts[-1])
            if proc is None:
                raise _Refused("unreadable_start", f"the journal's last `started` entry cannot be read: "
                                                   f"{starts[-1]!r}. Nothing is adopted")
            _resume(proc, args.pid)
        else:
            proc = _adopt(armed, args.pid, args.wait)
            snapshot.record(snap, "started", pid=proc.pid, created=proc.created)
        beats = _follow(snap, proc, args.interval)
    except _Refused as refusal:
        return dict(refusal.result, id=snap.id), 2
    return {"id": snap.id, "pid": proc.pid, "created": proc.created, "resumed": bool(starts),
            "heartbeats": beats, "exited": True}, 0


def _look(watched: int | None = None) -> list[gate.ProcId] | None:
    """The running games, or None when the look failed, or when it lists the process `watched` with a start
    time it could not read (that may still be the run's game)."""
    try:
        games = gate.list_games()
    except gate.GateError:
        return None
    if watched is not None and gate.ProcId(watched, gate.UNKNOWN_START) in games:
        return None
    return games


def _cannot_look(tries: int, **fields) -> _Refused:
    return _Refused("cannot_look", f"the game processes could not be listed {tries} times running, so no exit "
                                   "is recorded. Run `watch` again once they can: it picks up the run's game "
                                   "if one was recorded", **fields)


def _adoptable(game: gate.ProcId, armed: dt.datetime) -> bool:
    """Created after `armed` and at most WATCH_ADOPT_WINDOW_S after it."""
    created = _when(game.created)
    return created is not None and armed < created <= armed + dt.timedelta(seconds=WATCH_ADOPT_WINDOW_S)


def _adopt(armed: dt.datetime, pid: int | None, wait: float) -> gate.ProcId:
    """The run's game, looked for until `wait` seconds have passed: the process `pid`, or else the one game
    created in the adoption window. Raises _Refused."""
    window = f"after the snapshot was armed ({armed:%H:%M:%S} UTC) and within {WATCH_ADOPT_WINDOW_S:.0f} s of it"
    start = _clock()
    failures = 0
    while True:
        games = _look()
        if games is None:
            failures += 1
            if failures >= WATCH_LOOK_TRIES:
                raise _cannot_look(failures)
        else:
            failures = 0
            if pid is not None:
                named = [g for g in games if g.pid == pid]
                if named:
                    if _adoptable(named[0], armed):
                        return named[0]
                    raise _Refused("not_the_run", f"pid {pid} (started {named[0].created}) was not created {window}")
            else:
                if any(g.created == gate.UNKNOWN_START for g in games):
                    raise _Refused("unknown_game", "a Victoria 3 process whose start time cannot be read is "
                                                   "running, so the run's game cannot be told apart: pass --pid",
                                   games=_running(games))
                mine = [g for g in games if _adoptable(g, armed)]
                if len(mine) == 1:
                    return mine[0]
                if len(mine) > 1:
                    raise _Refused("several_games", f"more than one game was created {window}: pass --pid",
                                   games=_running(mine))
        if _clock() - start >= wait:
            if games is None:
                raise _cannot_look(failures)
            if pid is not None:
                raise _Refused("not_the_run", f"no game process with pid {pid} appeared")
            raise _Refused("no_game", f"no game process created {window} appeared", games_not_adopted=len(games))
        _sleep(2.0)


def _resume(proc: gate.ProcId, pid: int | None) -> None:
    """Check that the run's recorded game is still running. Raises _Refused."""
    if pid is not None and pid != proc.pid:
        raise _Refused("not_the_run", f"this run's game is pid {proc.pid}, recorded when it started")
    failures = 0
    while (games := _look(proc.pid)) is None:
        failures += 1
        if failures >= WATCH_LOOK_TRIES:
            raise _cannot_look(failures, pid=proc.pid)
        _sleep(2.0)
    if proc not in games:
        raise _Refused("game_gone_unrecorded",
                       f"this run's game (pid {proc.pid}) is no longer running and nobody saw when it exited, so "
                       "no exit is recorded: `restore` will judge the files against the last heartbeat",
                       pid=proc.pid)


def _follow(snap: snapshot.Snapshot, proc: gate.ProcId, interval: float) -> int:
    """Record a heartbeat at each look that shows `proc`, and `game_exited` at the first that shows it gone;
    return the number of heartbeats. Raises _Refused, recording no exit, after WATCH_LOOK_TRIES failed looks."""
    beats = 0
    failures = 0
    while True:
        _sleep(interval)
        games = _look(proc.pid)
        if games is None:
            failures += 1
            if failures >= WATCH_LOOK_TRIES:
                raise _cannot_look(failures, pid=proc.pid, heartbeats=beats)
            continue
        failures = 0
        if proc not in games:
            break
        snapshot.record(snap, "heartbeat")
        beats += 1
    snapshot.record(snap, "game_exited")
    return beats


def cmd_restore(args) -> tuple[dict, int]:
    """Put the owner's files back. This never writes a time into the journal:
    when the run ended is what `watch` (or the driver) recorded while it
    happened. With no such record, anything that would need judging is held."""
    user, backups = _paths()
    snap = _find(backups, args.id)
    games = gate.list_games()
    mine = _started(snap)
    if mine is not None and mine in games:
        return {"held": False, "refused": "game_still_up",
                "detail": f"this run's own game (pid {mine.pid}) is still running: close it first"}, 2
    age = _since_last_seen_alive(snap)
    if age is not None and age < WATCH_RECORDING_S:
        return {"held": False, "refused": "watch_still_recording",
                "detail": f"`watch` last recorded this run's game alive {max(age, 0):.0f} s ago and has not "
                          "recorded its exit: wait for `watch` to return, then restore"}, 2
    try:
        out = restore.restore(snap, user, other_game_running=bool(games),
                              run_logs_dir=Path(args.run_logs) if args.run_logs else None)
    except OSError as exc:
        return {"held": False, "refused": "error", "detail": str(exc)}, 2
    return _outcome(out), 2 if out.held else 0


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
    """Finish the runs a dead session left: first the started ones (`restore.recover`), then, if those all
    finished, the snapshots armed for a run whose start was never recorded."""
    user, backups = _paths()
    games = gate.list_games()
    ours = gate.ours_from_journals(backups)

    def own_game_up(started: dict) -> bool:
        return gate.ProcId(int(started.get("pid", -1)), str(started.get("created", ""))) in games

    results = restore.recover(backups, user, any(g not in ours for g in games), own_game_up)
    runs = [dict(_outcome(out), id=snap_id) for snap_id, out in results]
    if all(not r["held"] and not r["reason"] for r in runs):
        runs += _recover_never_started(backups, user)
    clean = all(not r["held"] and not r["reason"] for r in runs)
    return {"runs": runs}, 0 if clean else 2


def _recover_never_started(backups: Path, user: Path) -> list[dict]:
    """Restore or hold each snapshot armed for a run that never recorded `started` (the session died before
    `watch`, or `watch` refused), newest first, stopping at the first hold or error, as `restore.recover`
    does. Such a run has no game of its own to wait for, so any game running may be the owner's: hold. With
    none, restore puts the folder back when nothing needs judging and holds (`no_reference_time`) otherwise."""
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
            out = restore.restore(snap, user, other_game_running=bool(games))
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
        return _game_running(games), 2
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

    p = sub.add_parser("gate", help="may the game be launched now?")
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

    p = sub.add_parser("watch", help="record the run's game in the snapshot's journal until it exits")
    p.add_argument("id")
    p.add_argument("--pid", type=int, metavar="N",
                   help="adopt exactly this process, which must have been created after the snapshot and "
                        f"within {WATCH_ADOPT_WINDOW_S:.0f} s of it (default: the one game that was)")
    p.add_argument("--wait", type=float, default=WATCH_WAIT_S, help="seconds to wait for the game to appear")
    p.add_argument("--interval", type=float, default=WATCH_INTERVAL_S, help="seconds between looks")
    p.set_defaults(run=cmd_watch)

    for name, fn, text in (("recover", cmd_recover, "finish the restore of runs that never finished"),
                           ("held", cmd_held, "list snapshots held because the owner played since"),
                           ("selftest-restore", cmd_selftest_restore,
                            "prove a snapshot of the real folder restores, changing nothing in it")):
        sub.add_parser(name, help=text).set_defaults(run=fn)

    args = parser.parse_args(argv)
    try:
        result, code = args.run(args)
    except Exception as exc:  # every failure is one JSON object: BackupRootError, GateError, OSError, ...
        result, code = {"refused": type(exc).__name__, "detail": str(exc)}, 2
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
