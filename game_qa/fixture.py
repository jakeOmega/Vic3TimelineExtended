"""The fixture: a fresh save made by an unattended run of the game, kept under a key so a build is paid for once.

The run needs no clicks. The overlay's scripted test (game_qa.overlay) fails on the second day of a new game,
and the engine then writes `save games/TEST_FAIL_te_qa_fixture_2 January, 1836.v3`; `-run_until` ends the run
two days later. `make` drives that through the protective verbs (`snapshot`, `launch`, `watch`, `restore`), which
it reaches only through the `run_cli` it is given, so there is one implementation of the protective flow.

`restore` removes the saves a run created, `TEST_FAIL_*` among them, so `make` gives the run's save its permanent
name, `te_qa_fixture_<key>.v3` (which `restore` never removes), before it restores. Nothing else under the
user-data folder is touched here: `make` renames only a new `TEST_FAIL_te_qa_fixture_*.v3`, and `prune`
removes only files named `te_qa_fixture_*.v3`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Callable, Sequence
from pathlib import Path

FIXTURE_ARGS = ("-gdpr-compliant", "-debug_mode", "-handsoff", "-scripted_tests", "-run_until=1836.1.4")

# What `python3 -m game_qa <argv>` printed (one JSON object) and its exit code: 0 is success, anything
# else is a refusal, a hold or an error whose reply says which (`refused`, or `held` and `reason`).
RunCli = Callable[[Sequence[str]], tuple[dict, int]]

SAVE_FOLDER = "save games"
FIXTURE_PREFIX = "te_qa_fixture_"
FIXTURE_GLOB = f"{FIXTURE_PREFIX}*.v3"
RUN_SAVE_GLOB = "TEST_FAIL_te_qa_fixture_*.v3"
KEY_FOLDERS = ("common", "events", "map_data")  # the folders of the deployed mod that shape a new game
RESTORE_RETRY_S = 5
RESTORE_RETRY_TOTAL_S = 30

_KEY = re.compile(r"[A-Za-z0-9_]{1,64}")


class FixtureError(Exception):
    """A step of `make` that did not go through.

    `step` is the verb that refused (`snapshot`, `launch`, `watch`, `restore`) or the part of `make` that
    failed (`check` before anything ran, `save` when the run left no single save, `rename`); `reply` is the
    verb's reply, `{}` when no verb is to blame; `snapshot` is the snapshot's id once one was taken."""

    def __init__(self, message: str, step: str, reply: dict | None = None, snapshot: str | None = None):
        super().__init__(message)
        self.step = step
        self.reply = reply if reply is not None else {}
        self.snapshot = snapshot


def key(game_version: str, enabled_mods: Sequence[str], deploy_dir: Path) -> str:
    """12 hex digits naming the game a fixture was made for: the game version, the enabled mod paths in
    order, and the relative path, size and modification time of every file under the deployed mod's
    `common/`, `events/` and `map_data/` (a folder that is missing is skipped)."""
    if isinstance(enabled_mods, str):
        raise TypeError("enabled_mods is a list of paths, not one path")
    digest = hashlib.sha256()
    _feed(digest, "version", game_version)
    for mod in enabled_mods:
        _feed(digest, "mod", mod)
    root = Path(deploy_dir)
    for folder in KEY_FOLDERS:
        records = []
        for where, _, names in os.walk(root / folder):
            for name in names:
                path = Path(where) / name
                try:
                    info = path.stat()
                except OSError:
                    continue
                records.append((path.relative_to(root).as_posix(), info.st_size, info.st_mtime_ns))
        for record in sorted(records):
            _feed(digest, "file", *record)
    return digest.hexdigest()[:12]


def find(user_data: Path, key: str) -> Path | None:
    """`save games/te_qa_fixture_<key>.v3` if it is there."""
    _check_key(key)
    path = Path(user_data) / SAVE_FOLDER / f"{FIXTURE_PREFIX}{key}.v3"
    return path if path.is_file() else None


def make(
    run_cli: RunCli,
    user_data: Path,
    key: str,
    overlay_windows_path: str,
    permission: str,
    playset: str,
    owner_confirmed_busy: bool = False,
    sleep=time.sleep,
) -> Path:
    """Make the fixture for `key` with one unattended run of the game, and return its save.

    The order is `snapshot`, `launch`, `watch` (which returns once the game has quit by itself), the rename
    of the run's save, and `restore`. Once a snapshot exists `restore` is called whatever happened (an armed
    snapshot blocks every later one, and `restore` holds by itself when something needs judging). Nothing is
    started when `save games/` already holds the fixture or a `TEST_FAIL_te_qa_fixture_*` save: the second
    would be taken for this run's. A refused or held verb raises FixtureError carrying its reply; when
    several steps fail the first is raised and the later ones are added to its message."""
    _check_key(key)
    saves = Path(user_data) / SAVE_FOLDER
    target = saves / f"{FIXTURE_PREFIX}{key}.v3"
    if target.exists():
        raise FixtureError(f"{target.name} is already there: use it", "check")
    leftovers = [path.name for path in _run_saves(saves)]
    if leftovers:
        raise FixtureError(
            f"save games/ already holds {', '.join(leftovers)}, left by an earlier run; it would be taken for this "
            "run's save, so it has to go first (the owner's call, nothing here deletes it)",
            "check",
        )

    reply, ok = _call(run_cli, ["snapshot"])
    snapshot = reply.get("id")
    if not ok or not isinstance(snapshot, str) or not snapshot:
        raise FixtureError(_message("snapshot", reply, None), "snapshot", reply)

    launch = ["launch", snapshot, "--permission", permission, "--playset", playset, "--add-mod", overlay_windows_path]
    if owner_confirmed_busy:
        launch.append("--owner-confirmed-busy")
    launch += ["--", *FIXTURE_ARGS]

    failure = None
    try:
        failure = _run(run_cli, launch, snapshot, saves, target)
    finally:
        restore_failure = _restore(run_cli, snapshot, sleep)
    if failure is None:
        failure = restore_failure
    elif restore_failure is not None:
        failure = FixtureError(f"{failure}. Then {restore_failure}", failure.step, failure.reply, snapshot)
    if failure is not None:
        raise failure
    return target


def prune(user_data: Path, keep: int = 2) -> list[str]:
    """Remove all but the `keep` newest `te_qa_fixture_*.v3` files directly in `save games/` (newest by
    modification time, equal times by name) and return the names removed, oldest first. Nothing else is touched."""
    if keep < 0:
        raise ValueError("keep is a count of fixtures, not negative")
    found = sorted(
        (path.stat().st_mtime_ns, path.name, path)
        for path in (Path(user_data) / SAVE_FOLDER).glob(FIXTURE_GLOB)
        if path.is_file() and not path.is_symlink()
    )
    doomed = found[: max(len(found) - keep, 0)]
    for _, _, path in doomed:
        path.unlink()
    return [name for _, name, _ in doomed]


def _check_key(key: str) -> None:
    if not isinstance(key, str) or _KEY.fullmatch(key) is None:
        raise ValueError(f"a fixture key is letters, digits and _ (it becomes part of a file name): {key!r}")


def _feed(digest, *fields) -> None:
    """One record in the hash: a JSON list per line, so no choice of fields can run into the next record."""
    digest.update((json.dumps(list(fields), default=str) + "\n").encode())


def _run_saves(saves: Path) -> list[Path]:
    return sorted(path for path in saves.glob(RUN_SAVE_GLOB) if path.is_file())


def _call(run_cli: RunCli, argv: list[str]) -> tuple[dict, bool]:
    """(reply, ok): the verb's reply as a dict, and whether it exited 0."""
    reply, code = run_cli(argv)
    if not isinstance(reply, dict):
        reply = {"error": f"not a JSON object: {reply!r}"[:300]}
    return reply, code == 0


def _why(reply: dict) -> str:
    for field in ("refused", "reason", "error"):
        if reply.get(field):
            detail = reply.get("detail")
            return f"{reply[field]} ({detail})" if detail else str(reply[field])
    return json.dumps(reply, sort_keys=True)[:300]


def _message(step: str, reply: dict, snapshot: str | None) -> str:
    where = f" (snapshot {snapshot})" if snapshot else ""
    return f"{step} did not go through{where}: {_why(reply)}"


def _failure(step: str, reply: dict, snapshot: str) -> FixtureError:
    return FixtureError(_message(step, reply, snapshot), step, reply, snapshot)


def _run(run_cli: RunCli, launch: list[str], snapshot: str, saves: Path, target: Path) -> FixtureError | None:
    """Launch, watch and keep the run's save. The first failure, or None."""
    reply, ok = _call(run_cli, launch)
    if not ok:
        return _failure("launch", reply, snapshot)  # a game may still have started: restore judges that
    failure = None
    reply, ok = _call(run_cli, ["watch", snapshot])
    if not ok:
        failure = _failure("watch", reply, snapshot)  # the save may be there all the same: keep it
    try:
        _keep_the_save(saves, target)
    except FixtureError as error:
        error.snapshot = snapshot
        failure = failure or error
    return failure


def _keep_the_save(saves: Path, target: Path) -> None:
    """Give the run's one `TEST_FAIL_te_qa_fixture_*.v3` save the fixture's name."""
    made = _run_saves(saves)
    if not made:
        raise FixtureError(f"the run left no {RUN_SAVE_GLOB} in save games/", "save")
    if len(made) > 1:
        names = [path.name for path in made]
        raise FixtureError(f"the run left {len(made)} saves, {', '.join(names)}: which is the fixture?", "save", {"saves": names})
    if target.exists():
        raise FixtureError(f"{target.name} appeared during the run and is left as it is", "rename")
    try:
        os.rename(made[0], target)
    except OSError as error:
        raise FixtureError(f"{made[0].name} could not be renamed to {target.name}: {error}", "rename", {"error": str(error)}) from error


def _restore(run_cli: RunCli, snapshot: str, sleep) -> FixtureError | None:
    """`restore`, retried while `watch` is still recording, for RESTORE_RETRY_TOTAL_S seconds at most."""
    waited = 0
    while True:
        reply, ok = _call(run_cli, ["restore", snapshot])
        if ok:
            return None
        if reply.get("refused") == "watch_still_recording" and waited < RESTORE_RETRY_TOTAL_S:
            sleep(RESTORE_RETRY_S)
            waited += RESTORE_RETRY_S
            continue
        return _failure("restore", reply, snapshot)
