"""The fixture: a fresh save made by an unattended run of the game, kept under a key so a build is paid for once.

The run needs no clicks. The overlay's scripted test (game_qa.overlay) fails on the second day of a new game,
and the engine then writes `save games/TEST_FAIL_te_qa_fixture_2 January, 1836.v3`; `-run_until` ends the run
two days later. `make` drives that through the protective verbs (`snapshot`, `launch`, `watch`, `restore`), which
it reaches only through the `run_cli` it is given, so there is one implementation of the protective flow.

`restore` removes the saves a run created, `TEST_FAIL_*` among them, so `make` gives the run's save its permanent
name, `te_qa_fixture_<key>.v3` (which `restore` never removes), before it restores. Nothing else under the
user-data folder is touched here: `make` renames only a new `TEST_FAIL_te_qa_fixture_*.v3`, and `prune`
removes only files named `te_qa_fixture_*.v3`.

A launch that may have started a game (anything but a refusal given before the launch claimed the snapshot) is
followed by `watch` at once, for at most FIXTURE_LIMIT_S. The fixture cannot end a game, so when `watch` has not
recorded the game's exit `make` never restores beside it: it raises `game_may_be_up` with what the caller needs
to end that game and finish the snapshot (the session does both, as for its own game).

Shared with the session: which launch refusals mean no game was started (`no_game`), and `restore` retried while
it refuses for a reason that passes (`restore_retried`).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from game_qa.gate import ProcId

FIXTURE_ARGS = ("-gdpr-compliant", "-debug_mode", "-handsoff", "-scripted_tests", "-run_until=1836.1.4")

# What `python3 -m game_qa <argv>` printed (one JSON object) and its exit code: 0 is success, anything
# else is a refusal, a hold or an error whose reply says which (`refused`, or `held` and `reason`).
RunCli = Callable[[Sequence[str]], tuple[dict, int]]
# Starts `python3 -m game_qa watch <id>` in the background: a handle whose `poll()` is None until it returns,
# then its exit code (0: it recorded the game's exit).
SpawnWatch = Callable[[str], Any]

SAVE_FOLDER = "save games"
FIXTURE_PREFIX = "te_qa_fixture_"
FIXTURE_GLOB = f"{FIXTURE_PREFIX}*.v3"
SWITCHED_MARK = "_s"                    # in the key of a fixture copy with a rule switched (game_qa.rules)
RUN_SAVE_GLOB = "TEST_FAIL_te_qa_fixture_*.v3"
KEY_FOLDERS = ("common", "events", "map_data")  # the folders of the deployed mod that shape a new game
FIXTURE_LIMIT_S = 900.0     # from the launch's return to watch's: the run itself takes two or three minutes
WATCH_POLL_S = 2.0
RESTORE_RETRY_S = 5
RESTORE_RETRY_TOTAL_S = 30  # while restore refuses watch_still_recording
BUSY_RETRY_TOTAL_S = 60     # while it refuses busy: another session's protective verb holds the backup root's lock
# Not launch_in_flight: the fixture cannot end its game, and a restore after the claim's 90 s, beside a game
# still loading, would hold the run for good (other_game_running) with its playset left in place.
RESTORE_RETRIES = {"watch_still_recording": RESTORE_RETRY_TOTAL_S, "busy": BUSY_RETRY_TOTAL_S}
GAME_MAY_BE_UP = "game_may_be_up"

# `launch` refusals given before it claims the snapshot: no game was started (game_qa/__main__.py). Any other
# reply that is not a success (not_recorded, start_unconfirmed, a refusal after the claim, a name not known here,
# a lost or unreadable reply) may come with a game up.
# ADD_MOD_CHANGED is the session's own, given in place of a launch it did not run (a variant folder changed).
ADD_MOD_CHANGED = "add_mod_changed"
NO_GAME_REFUSALS = frozenset({
    "already_finished", "already_started", "not_armed", "no_end_date", "bad_argument", "no_permission",
    "backup_root", "other_game", "gpu_busy", "game_running", "stale_snapshot", "no_game_binary",
    "mod_not_in_playset", "playset_not_restored", "busy", ADD_MOD_CHANGED})
_CLAIMED = "stays claimed"              # said by every refusal after the claim (__main__._CLAIM_STAYS)

_KEY = re.compile(r"[A-Za-z0-9_]{1,64}")


class FixtureError(Exception):
    """A step of `make` that did not go through.

    `step` is the verb that refused (`snapshot`, `launch`, `watch`, `restore`) or the part of `make` that
    failed (`check` before anything ran, `save` when the run left no single save, `rename`); `reply` is the
    verb's reply, `{}` when no verb is to blame; `snapshot` is the snapshot's id once one was taken.

    `code` is GAME_MAY_BE_UP when a game of the run may still be up: the snapshot was then NOT restored, and the
    caller ends that game (`proc`, its pid and start time, when known) and finishes the snapshot; `watch` is the
    handle of the `watch` following it (None when none could be started), which may still be running. `restore`
    is the (reply, exit code) of the fixture's own restore, None when it was not run."""

    def __init__(self, message: str, step: str, reply: dict | None = None, snapshot: str | None = None, *,
                 code: str | None = None, proc: ProcId | None = None, watch: Any = None,
                 restore: tuple[dict, int] | None = None):
        super().__init__(message)
        self.step = step
        self.reply = reply if reply is not None else {}
        self.snapshot = snapshot
        self.code = code
        self.proc = proc
        self.watch = watch
        self.restore = restore


@dataclass
class _Run:
    """How `_run` ended: its first failure, and `up` (why) when a game of the run may still be up."""
    failure: FixtureError | None = None
    up: str | None = None
    proc: ProcId | None = None
    watch: Any = None


def no_game(reply: dict) -> bool:
    """Whether a `launch` reply is a refusal given before the launch claimed the snapshot, so that no game was
    started. A refusal after the claim says the snapshot stays claimed (`_CLAIMED`), and may have come with a game
    up as far as this can tell; so may a reply that is not a refusal at all."""
    refused = reply.get("refused")
    if refused in NO_GAME_REFUSALS:
        return True
    detail = str(reply.get("detail") or "")
    return refused == "playset_unwritable" and "Nothing was written" in detail and _CLAIMED not in detail


def restore_retried(run_cli: RunCli, snapshot_id: str, sleep, retries: Mapping[str, float]) -> tuple[dict, int]:
    """`restore <id>`, run again every RESTORE_RETRY_S while it refuses for a reason in `retries`, for up to that
    reason's seconds in all; then its last (reply, exit code). A call that raises, or a reply that is not an
    object, is a refusal that is not retried (`error`, `bad_reply`)."""
    waited = dict.fromkeys(retries, 0.0)
    while True:
        try:
            reply, code = run_cli(["restore", snapshot_id])
        except Exception as error:
            return {"held": False, "refused": "error", "detail": f"restore could not be run: {error!r}"}, 2
        if not isinstance(reply, dict):
            return {"held": False, "refused": "bad_reply", "detail": repr(reply)[:300]}, 2
        refused = reply.get("refused") if code != 0 else None
        if not isinstance(refused, str) or refused not in retries or waited[refused] >= retries[refused]:
            return reply, code
        sleep(RESTORE_RETRY_S)
        waited[refused] += RESTORE_RETRY_S


def key(game_version: str, enabled_mods: Sequence[str], deploy_dir: Path, *, playset: str,
        disabled_dlc: Sequence = (), rules: Sequence[str] = (), add_mod_dirs: Sequence[Path] = ()) -> str:
    """12 hex digits naming the game a fixture was made for: the game version, the run's playset (its mode,
    `playset`, `enabled_mods`, the mod paths the run loads, in order, and `disabled_dlc`, the DLC the run's
    playset switches off, as a set: launch keeps the owner's `disabledDLC`), `rules`, the rule settings the
    owner last applied in a lobby, in the file's order (an unattended new game is made under them, not under
    the defaults: game_qa.rules), and the relative path, size and
    modification time of every file under the deployed mod's `common/`, `events/` and `map_data/` (a folder that
    is missing is skipped). A fixture made under another playset, or another DLC set, is another world: a DLC
    changes what a new game sets up even where the script folders loaded are the same. `add_mod_dirs`, the
    session's variant folders (`start --add-mod`, whose Windows paths are among `enabled_mods`), are hashed as the
    deployed mod is, each by its place in the list, and with the bytes of its `.metadata/metadata.json` (whose
    `game_custom_data.replace_paths` changes which vanilla folders load), so a variant edited in place is another
    world too (`add_mod_digest`). Not covered: for `current`, the other mods' contents (only their paths are
    hashed), so an update of one keeps the key; and the deployed mod's own metadata.json, which would change
    every fixture's key."""
    if isinstance(enabled_mods, str):
        raise TypeError("enabled_mods is a list of paths, not one path")
    digest = hashlib.sha256()
    _feed(digest, "version", game_version)
    _feed(digest, "playset", playset)
    for mod in enabled_mods:
        _feed(digest, "mod", mod)
    for dlc in sorted(json.dumps(entry, sort_keys=True) for entry in disabled_dlc):
        _feed(digest, "dlc_off", dlc)
    for setting in rules:
        _feed(digest, "rule", setting)
    _feed_folders(digest, "file", Path(deploy_dir))
    _feed_add_mods(digest, add_mod_dirs)
    return digest.hexdigest()[:12]


def add_mod_digest(add_mod_dirs: Sequence[Path]) -> str:
    """What `key` reads of the variant folders, alone: the session takes it at `start` and again just before each
    launch, and refuses a launch when it has changed (the fixture would be keyed on files the game does not load)."""
    digest = hashlib.sha256()
    _feed_add_mods(digest, add_mod_dirs)
    return digest.hexdigest()


def _feed_add_mods(digest, add_mod_dirs: Sequence[Path]) -> None:
    for number, folder in enumerate(add_mod_dirs):
        _feed_folders(digest, "add_mod_file_%d" % number, Path(folder))
        try:
            meta = hashlib.sha256((Path(folder) / ".metadata" / "metadata.json").read_bytes()).hexdigest()
        except OSError as e:
            meta = "unreadable: %s" % type(e).__name__
        _feed(digest, "add_mod_metadata_%d" % number, meta)


def _feed_folders(digest, tag: str, root: Path) -> None:
    """The relative path, size and modification time of every file under `root`'s KEY_FOLDERS, in order."""
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
            _feed(digest, tag, *record)


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
    *,
    spawn_watch: SpawnWatch,
    clock=time.monotonic,
    started: Callable[[str], ProcId | None] | None = None,
    keep_lines: Callable[[str], Any] | None = None,
    add_mods: Sequence[str] = (),
) -> Path:
    """Make the fixture for `key` with one unattended run of the game, and return its save. `playset` is the
    run's (`launch --playset`), so the fixture is made in the world the run will load; `add_mods`, the session's
    variant folders (Windows paths), are loaded too, after the playset and before the overlay, as the run's are.

    The order is `snapshot`, `launch`, `watch` (spawned the moment launch returns, and followed until it has
    recorded the game's exit, which `-run_until` brings), the rename of the run's save, and `restore` (retried
    as RESTORE_RETRIES say). A launch refused before its claim started nothing: it is restored at once.

    A launch that may have started a game (not_recorded, start_unconfirmed, a refusal after the claim, a lost
    or unreadable reply) is watched too. When `watch` has not recorded the game's exit (it returned anything
    else, could not be started, or the game outlasted FIXTURE_LIMIT_S) nothing is restored beside the game:
    FixtureError `game_may_be_up` is raised with the snapshot, the game's pid and start time when known (from
    launch's reply, else from `started`, the snapshot journal's `started` entry), and the watch, for the caller
    to end the game and finish the snapshot. An interrupt (KeyboardInterrupt, SystemExit) restores nothing either.

    Nothing is started when `save games/` already holds the fixture or a `TEST_FAIL_te_qa_fixture_*` save: the
    second would be taken for this run's. A refused or held verb raises FixtureError carrying its reply; when
    several steps fail the first is raised and the later ones are added to its message.

    Once the fixture is made and its run restored, `keep_lines` is called with the run's snapshot id: the
    restore has copied the run's logs to that snapshot's `run_logs/`, the only place the lines a new game logs
    at its setup are ever written, and the snapshot is pruned long before the fixture (game_qa.selfchecks,
    #1601). It must not raise: the fixture is made whatever becomes of its lines."""
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

    launch = ["launch", snapshot, "--permission", permission, "--playset", playset]
    for folder in add_mods:
        launch += ["--add-mod", folder]
    launch += ["--add-mod", overlay_windows_path]
    if owner_confirmed_busy:
        launch.append("--owner-confirmed-busy")
    launch += ["--", *FIXTURE_ARGS]

    run = _run(run_cli, launch, snapshot, saves, target, spawn_watch, sleep, clock, started)
    if run.up is not None:
        failure = run.failure
        raise FixtureError(f"the fixture's run (snapshot {snapshot}) may have left its game up: {run.up}, so it was "
                           f"not restored. {failure}", failure.step, failure.reply, snapshot, code=GAME_MAY_BE_UP,
                           proc=run.proc, watch=run.watch)
    restored = restore_retried(run_cli, snapshot, sleep, RESTORE_RETRIES)
    restore_failure = None if restored[1] == 0 else _failure("restore", restored[0], snapshot)
    failure = run.failure
    if failure is None:
        failure = restore_failure
    elif restore_failure is not None:
        failure = FixtureError(f"{failure}. Then {restore_failure}", failure.step, failure.reply, snapshot)
    if failure is not None:
        failure.restore = restored
        raise failure
    if keep_lines is not None:
        keep_lines(snapshot)
    return target


_SWITCHED_KEY = re.compile(r"(.+)_s[0-9a-f]{8}")     # SWITCHED_MARK and the eight hex digits rules.switched_key adds


def prune(user_data: Path, keep: int = 2, keep_switched: int = 2, in_use: Sequence[str] = ()) -> list[str]:
    """Remove all but the `keep` newest `te_qa_fixture_*.v3` files directly in `save games/` (newest by
    modification time, equal times by name) and return the names removed, oldest first. Nothing else is touched.

    A copy with a rule switched (its key ends in SWITCHED_MARK and eight hex digits) is not counted among
    those: it is removed with the fixture it was made from, and of the ones whose fixture stays only the
    `keep_switched` newest are kept. Counted together, two switched copies would push out the fixture they came
    from, and the next plain start would pay for a new run.

    `in_use` names files (as in the folder) that are never removed, whatever their age: the save a session is
    about to load, and the fixture it was copied from. A copy used again keeps its old time, so age alone
    could remove the very save the reply names."""
    if keep < 0 or keep_switched < 0:
        raise ValueError("keep is a count of fixtures, not negative")
    found = sorted(
        (path.stat().st_mtime_ns, path.name, path)
        for path in (Path(user_data) / SAVE_FOLDER).glob(FIXTURE_GLOB)
        if path.is_file() and not path.is_symlink()
    )
    protected = set(in_use)
    plain = [entry for entry in found if _base_key(entry[1]) is None]
    switched = [entry for entry in found if _base_key(entry[1]) is not None]
    doomed = [entry for entry in plain[: max(len(plain) - keep, 0)] if entry[1] not in protected]
    going = {entry[1] for entry in doomed}
    kept_keys = {_key_of(entry[1]) for entry in plain if entry[1] not in going}
    orphans = [entry for entry in switched if _base_key(entry[1]) not in kept_keys and entry[1] not in protected]
    living = [entry for entry in switched if entry not in orphans]
    extra = [entry for entry in living[: max(len(living) - keep_switched, 0)] if entry[1] not in protected]
    doomed = sorted(doomed + orphans + extra)
    for _, _, path in doomed:
        path.unlink()
    return [name for _, name, _ in doomed]


def _base_key(name: str) -> str | None:
    """The key of the fixture a switched copy was made from, or None for a file that is not one."""
    found = _SWITCHED_KEY.fullmatch(_key_of(name))
    return found.group(1) if found else None


def _key_of(name: str) -> str:
    return name[len(FIXTURE_PREFIX):-len(".v3")]


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


def _run(run_cli: RunCli, launch: list[str], snapshot: str, saves: Path, target: Path, spawn_watch: SpawnWatch,
         sleep, clock, started) -> _Run:
    """Launch, follow the game with `watch` until it has quit, and keep the run's save."""
    try:
        reply, ok = _call(run_cli, launch)
    except Exception as error:
        reply = {"refused": "no_reply", "detail": f"launch could not be run, or its reply was lost: {error!r}"}
        ok = False
    failure = None if ok else _failure("launch", reply, snapshot)
    if not ok and no_game(reply):
        return _Run(failure)
    # From here a game of this run may be up, whatever the reply says: it is watched before anything else.
    proc = _named_proc(reply)
    if proc is None and started is not None:
        proc = started(snapshot)
    try:
        watch = spawn_watch(snapshot)
    except Exception as error:
        why = f"`watch` could not be started ({error!r}), so nothing records the game"
        return _Run(failure or _failure("watch", {"refused": "not_spawned", "detail": why}, snapshot), why, proc)
    deadline = clock() + FIXTURE_LIMIT_S
    try:
        while (code := watch.poll()) is None:
            if clock() >= deadline:
                why = f"the game had not quit {FIXTURE_LIMIT_S:g} s after its launch (its `watch` still follows it)"
                return _Run(failure or _failure("watch", {"refused": "time_limit", "detail": why}, snapshot), why,
                            proc, watch)
            sleep(WATCH_POLL_S)
    except Exception as error:
        why = f"looking at `watch` failed ({error!r})"
        return _Run(failure or _failure("watch", {"refused": "error", "detail": why}, snapshot), why, proc, watch)
    if code != 0:
        why = f"`watch` returned {code} without recording the game's exit (its reply is in the run folder's watch.log)"
        return _Run(failure or _failure("watch", {"refused": "no_exit_recorded", "exit": code, "detail": why},
                                        snapshot), why, proc, watch)
    if failure is not None:
        return _Run(failure)        # the game launch started has quit and watch recorded it: restore judges the rest
    try:
        _keep_the_save(saves, target)
    except FixtureError as error:
        error.snapshot = snapshot
        return _Run(error)
    return _Run()


def _named_proc(reply: dict) -> ProcId | None:
    try:
        return ProcId(int(reply["pid"]), str(reply["created"]))
    except (KeyError, TypeError, ValueError):
        return None


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

