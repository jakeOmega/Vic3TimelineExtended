"""Command line of the in-game QA harness, part 1: protecting the owner's files.

    python3 -m game_qa gate --permission "asked 12:40"     # may the game be launched now?
    python3 -m game_qa snapshot [--save NAME]...           # before a launch
    python3 -m game_qa watch <id>                          # right after launching: records the game's
                                                           # start, that it is alive, and its exit
    python3 -m game_qa restore <id>                        # after the game has closed
    python3 -m game_qa recover                             # finish runs a dead session left
    python3 -m game_qa held                                # snapshots kept because the owner played since
    python3 -m game_qa selftest-restore                    # prove a snapshot restores, touching nothing

Each verb prints one JSON object. Exit 0 on success, 2 on a refusal or a hold.
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
_VERDICTS = ("restored", "held")
_sleep = time.sleep       # patched in tests


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
    raise SystemExit(f"no snapshot {snap_id!r} under {backup_root}")


def _outcome(out: restore.Outcome) -> dict:
    return {"restored": out.restored, "removed": out.removed, "held": out.held, "reason": out.reason}


def _events(snap: snapshot.Snapshot) -> list[str]:
    return [str(e.get("event")) for e in snapshot.journal(snap)]


def _started(snap: snapshot.Snapshot) -> gate.ProcId | None:
    """The game process of the snapshot's latest launch."""
    found = None
    for e in snapshot.journal(snap):
        if e.get("event") == "started":
            try:
                found = gate.ProcId(int(e["pid"]), str(e["created"]))
            except (KeyError, TypeError, ValueError):
                continue
    return found


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
                "detail": "an earlier snapshot was never restored: close its game, then `restore <id>` "
                          "(or `recover` for a run that died)"}, 2
    extra = ["save games/" + (name if name.endswith(".v3") else name + ".v3") for name in args.save]
    snap = snapshot.take(user, backups, extra=extra)
    snapshot.record(snap, "armed")
    pruned = restore.prune(backups, keep=KEEP_SNAPSHOTS, current=snap.id)
    return {"id": snap.id, "files": len(snap.files), "pruned": pruned,
            "held": [s.id for s in restore.held(backups)]}, 0


def cmd_watch(args) -> tuple[dict, int]:
    """Record the run's game in the snapshot's journal as it happens: `started`
    when the process appears, a `heartbeat` at each look, `game_exited` when
    it is gone. Restore judges later changes against these times, so they must
    be written while the game runs and not when restore is called.

    Only a game created after the snapshot was taken is adopted: a game that
    was already running is the owner's."""
    _user, backups = _paths()
    snap = _find(backups, args.id)
    journal = snapshot.journal(snap)
    events = [str(e.get("event")) for e in journal]
    if any(v in events for v in _VERDICTS):
        return {"refused": "already_finished", "detail": f"snapshot {snap.id} already has a verdict"}, 2
    armed = next((_when(str(e.get("at"))) for e in journal if e.get("event") == "armed"), None)
    if armed is None:
        return {"refused": "not_armed", "detail": "this snapshot was not taken by `snapshot` for a run"}, 2
    waited = 0.0
    while True:
        games = gate.list_games()
        mine = [g for g in games if (_when(g.created) or armed) > armed]
        if len(mine) == 1:
            proc = mine[0]
            break
        if len(mine) > 1:
            return {"refused": "several_games", "detail": "more than one game started since the snapshot"}, 2
        if waited >= args.wait:
            return {"refused": "no_game", "games_older_than_snapshot": len(games),
                    "detail": "no game process created after the snapshot appeared"}, 2
        _sleep(2.0)
        waited += 2.0
    if _started(snap) != proc:
        snapshot.record(snap, "started", pid=proc.pid, created=proc.created)
    beats = 0
    while True:
        _sleep(args.interval)
        if proc not in gate.list_games():
            break
        snapshot.record(snap, "heartbeat")
        beats += 1
    snapshot.record(snap, "game_exited")
    return {"id": snap.id, "pid": proc.pid, "created": proc.created, "heartbeats": beats, "exited": True}, 0


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
    try:
        out = restore.restore(snap, user, other_game_running=bool(games),
                              run_logs_dir=Path(args.run_logs) if args.run_logs else None)
    except OSError as exc:
        return {"held": False, "refused": "error", "detail": str(exc)}, 2
    return _outcome(out), 2 if out.held else 0


def cmd_recover(args) -> tuple[dict, int]:
    user, backups = _paths()
    games = gate.list_games()
    ours = gate.ours_from_journals(backups)

    def own_game_up(started: dict) -> bool:
        return gate.ProcId(int(started.get("pid", -1)), str(started.get("created", ""))) in games

    results = restore.recover(backups, user, any(g not in ours for g in games), own_game_up)
    runs = [dict(_outcome(out), id=snap_id) for snap_id, out in results]
    clean = all(not r["held"] and not r["reason"] for r in runs)
    return {"runs": runs}, 0 if clean else 2


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
    except (snapshot.BackupRootError, gate.GateError) as exc:
        result, code = {"refused": type(exc).__name__, "detail": str(exc)}, 2
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
