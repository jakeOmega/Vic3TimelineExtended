"""Command line of the in-game QA harness, part 1: protecting the owner's files.

    python3 -m game_qa gate --permission "asked 12:40"     # may the game be launched now?
    python3 -m game_qa snapshot [--save NAME]...           # before a launch
    python3 -m game_qa restore <id> --game-just-closed     # after the game has closed
    python3 -m game_qa recover                             # finish runs a dead session left
    python3 -m game_qa held                                # snapshots kept because the owner played since
    python3 -m game_qa selftest-restore                    # prove a snapshot restores, touching nothing

Each verb prints one JSON object. Exit 0 on success, 2 on a refusal or a hold.
Spec: docs/superpowers/specs/2026-11-10-in-game-qa-harness-design.md §§ 5.2–5.3.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from game_qa import gate, restore, snapshot

MIN_FREE_BYTES = 2 * 1024**3
KEEP_SNAPSHOTS = 5


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


def _started(snap: snapshot.Snapshot) -> gate.ProcId | None:
    for e in snapshot.journal(snap):
        if e.get("event") == "started" and "pid" in e and "created" in e:
            return gate.ProcId(int(e["pid"]), str(e["created"]))
    return None


def cmd_gate(args) -> tuple[dict, int]:
    _user, backups = _paths()
    result = gate.check(args.permission, gate.list_games(), gate.ours_from_journals(backups),
                        gate.sample_gpu(), args.owner_confirmed_busy, _backup_error(backups))
    return {"ok": result.ok, "reason": result.reason, "detail": result.detail,
            "permission": args.permission}, 0 if result.ok else 2


def cmd_snapshot(args) -> tuple[dict, int]:
    user, backups = _paths()
    open_runs = restore.unfinished(backups) if backups.is_dir() else []
    if open_runs:
        # Snapshots must never nest: one taken over a dead run's leftovers records them as the owner's files.
        return {"refused": "unfinished_run", "unfinished": [s.id for s in open_runs],
                "detail": "an earlier run was never restored: close its game and run `recover` first"}, 2
    extra = ["save games/" + (name if name.endswith(".v3") else name + ".v3") for name in args.save]
    snap = snapshot.take(user, backups, extra=extra)
    pruned = restore.prune(backups, keep=KEEP_SNAPSHOTS, current=snap.id)
    return {"id": snap.id, "files": len(snap.files), "pruned": pruned,
            "held": [s.id for s in restore.held(backups)]}, 0


def cmd_restore(args) -> tuple[dict, int]:
    user, backups = _paths()
    snap = _find(backups, args.id)
    games = gate.list_games()
    mine = _started(snap)
    if mine is not None and mine in games:
        return {"held": False, "refused": "game_still_up",
                "detail": f"this run's own game (pid {mine.pid}) is still running: close it first"}, 2
    events = {e.get("event") for e in snapshot.journal(snap)}
    if "game_exited" not in events:
        if args.game_just_closed and not games:
            snapshot.record(snap, "game_exited")
        elif not events & {"started", "heartbeat"}:
            return {"held": False, "refused": "no_reference_time",
                    "detail": "nothing in this snapshot's journal says when its run ended; "
                              "pass --game-just-closed right after closing the game"}, 2
    out = restore.restore(snap, user, other_game_running=bool(games),
                          run_logs_dir=Path(args.run_logs) if args.run_logs else None)
    return _outcome(out), 2 if out.held else 0


def cmd_recover(args) -> tuple[dict, int]:
    user, backups = _paths()
    games = gate.list_games()
    ours = gate.ours_from_journals(backups)

    def own_game_up(started: dict) -> bool:
        return gate.ProcId(int(started.get("pid", -1)), str(started.get("created", ""))) in games

    results = restore.recover(backups, user, any(g not in ours for g in games), own_game_up)
    return {"runs": [dict(_outcome(out), id=snap_id) for snap_id, out in results]}, 0


def cmd_held(args) -> tuple[dict, int]:
    _user, backups = _paths()
    return {"held": [s.id for s in restore.held(backups)]}, 0


def cmd_selftest_restore(args) -> tuple[dict, int]:
    """Snapshot the real user-data folder, restore it into an empty temp
    folder, and compare every file's hash and time with its manifest entry.
    Reads the user-data folder; writes only under the backup root, where the
    temp folder also sits, so the check runs on the backup drive's own
    filesystem (a Windows drive keeps times differently from /tmp)."""
    user, backups = _paths()
    snap = snapshot.take(user, backups)
    mismatched = []
    with tempfile.TemporaryDirectory(prefix="selftest_", dir=backups) as tmp:
        target = Path(tmp)
        for rel in snap.files:
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
        out = restore.restore(snap, target, other_game_running=False)
        for rel, entry in snap.files.items():
            path = target / rel
            if not path.is_file() or _sha256(path) != entry.sha256 or path.stat().st_mtime_ns != entry.mtime_ns:
                mismatched.append(rel)
    ok = not mismatched and not out.held and len(out.restored) == len(snap.files)
    return {"match": ok, "id": snap.id, "files": len(snap.files), "mismatched": mismatched}, 0 if ok else 2


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
    p.add_argument("--run-logs", metavar="DIR", help="copy the run's own logs here first")
    p.add_argument("--game-just-closed", action="store_true",
                   help="the game this snapshot was taken for has just been closed")
    p.set_defaults(run=cmd_restore)

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
