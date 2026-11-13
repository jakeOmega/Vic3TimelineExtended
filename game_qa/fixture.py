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
import shutil
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from game_qa.gate import ProcId
from game_qa.logtail import GAP_MARKER, LogFollower

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
NO_GAME_REFUSALS = frozenset({
    "already_finished", "already_started", "not_armed", "no_end_date", "bad_argument", "no_permission",
    "backup_root", "other_game", "gpu_busy", "game_running", "stale_snapshot", "no_game_binary",
    "mod_not_in_playset", "playset_not_restored", "busy", "no_long_run_grant", "handsoff_on_a_save"})
_CLAIMED = "stays claimed"              # said by every refusal after the claim (__main__._CLAIM_STAYS)

_KEY = re.compile(r"[A-Za-z0-9_]{1,64}")

# ---- dated fixtures (#1602)
#
# A dated fixture is the same unattended run carried on to a later date: the scripted test fails on that date, so
# the save is made there (game_qa.overlay writes the test from the date), and `-run_until` ends the run two days
# later, as it does two days after the 1836 fixture's. It is kept as `te_qa_fixture_<key>_d<YYYYMMDD>.v3`, the
# key of the build it was made on and the date, and reused while that key holds. The plain fixture is the one dated
# DEFAULT_DATE: its name and its run are the 1836 fixture's, byte for byte.

Date = tuple[int, int, int]                     # (year, month, day) of the game's calendar
START_DATE: Date = (1836, 1, 1)                 # NGame.START_DATE: every unattended new game begins here
DEFAULT_DATE: Date = (1836, 1, 2)               # the plain fixture's: its test fails on the game's second day
VANILLA_END_DATE: Date = (1936, 1, 1)           # NGame.END_DATE, when no defines file names one
# The game's year has 365 days and no leap day (scripting_best_practices.md, the monthly-pulse section).
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December")
RUN_ON_DAYS = 2                                 # from the save's date to `-run_until`, as for the 1836 fixture
DATED_MARK = "_d"                               # in the key of a dated fixture: then eight digits, YYYYMMDD
DATED_KEPT = 4                                  # dated fixtures kept, the newest, whatever their dates (`prune`)
# The owner's autosave setting is quarterly ("quarteryear" in pdx_settings.json); the first quarterly autosave of a
# new game is 1 April 1836. An unattended run that ends before it writes none; one that runs past it writes four a
# year into the owner's `save games/`, so `launch` asks for a grant of its own (`--long-run`) past this date.
SHORT_RUN_LAST: Date = (1836, 3, 31)

# The estimate of a run's wall-clock time: wall seconds per game day of an AI-only game on the owner's machine, by
# year, read from the archived observer runs' plain-text autosaves (each save's file time against its `game_date`;
# runs of game 1.14 and the mod of early October 2026, under /mnt/d/vic3te-data/):
#   vic3te-demog-overnight-2026-10-12   1836.2 to 1876.1: 0.47 s a day; 1877.1 to 1904.1: 0.53 (0.55 to 0.61
#                                        a year from 1895)
#   vic3te-demog-p2-normal-2026-10-11   1837.1 to 1902.1: 0.61
#   vic3te-growth-probe-data            1949.8 to 1953.2: 0.98 (a run from a save of that date)
# Between the anchors the rate is interpolated; past the last one nothing is measured, and it is taken to go on
# rising at the 1904 to 1951 slope. The owner's own play of a 1931 game ran slower (1.33 to 1.9 s a day,
# docs/audits/late_game_performance.md), with the interface drawn for a player.
RATE_ANCHORS: tuple[tuple[float, float], ...] = ((1836.0, 0.47), (1876.0, 0.47), (1904.0, 0.58), (1951.0, 0.98))
LOAD_S = 90.0               # launch to the save of the 1836 fixture's three-day run (spec § 3.6): the load, and a save
# The watch limit of a dated run: FIXTURE_LIMIT_S, the 1836 run's, plus LIMIT_FACTOR times the estimate of every day
# past the 1836 fixture's. The limit ends a game that may have hung, at the cost of the run: generous on purpose,
# since the rates above vary by about a factor of two between runs and past 1953 they are a guess.
LIMIT_FACTOR = 3.0
FOLLOW_S = 10.0             # a dated run's logs are copied this often (they rotate at 512 KB, six generations)
# The run's save is renamed again every RENAME_RETRY_S while the rename fails, RENAME_TRIES times in all (about a
# minute): OneDrive, or a scanner, may hold a new file of 100 MB or more open for a while. Then it is copied.
RENAME_TRIES = 30
RENAME_RETRY_S = 2.0
HOLD_ASKED = "hold_asked"   # a journal event: the run's restore holds with its `reason` (__main__._unvouched_hold)
RUN_LOG_COPY = "fixture_%s"             # the run's own copy of each log, in its run folder: fixture_debug.log
RUN_LOGS = ("debug.log", "error.log")
GAMETIMER_GLOB = "gametimer_*.tsv"      # the game's own seconds per game day, written by an unattended run

_DATE_TEXT = re.compile(r"([0-9]{4})(?:\.([0-9]{1,2})\.([0-9]{1,2}))?")
_DATED_KEY = re.compile(r"(.+)_d([0-9]{4})([0-9]{2})([0-9]{2})")
_SAVE_DATE = re.compile(rb"\n\tgame_date=([0-9]{1,4})\.([0-9]{1,2})\.([0-9]{1,2})\n")
_WRITTEN_DATE = re.compile(r"TEST_FAIL_te_qa_fixture_([0-9]{1,2}) ([A-Za-z]+), ([0-9]{1,4})\.v3")
_END_DATE = re.compile(r'(?m)^[^#\n]*\bEND_DATE\s*=\s*"?([0-9]{1,4})\.([0-9]{1,2})\.([0-9]{1,2})"?')


def check_date(date: Sequence[int]) -> Date:
    """`date` as a (year, month, day) of the game's calendar, or ValueError: a month 1 to 12 and a day that month
    has (no 29 February: the game has no leap day)."""
    try:
        year, month, day = (int(part) for part in date)
    except (TypeError, ValueError):
        raise ValueError(f"a date is (year, month, day), not {date!r}") from None
    if not 1 <= month <= 12 or not 1 <= day <= MONTH_DAYS[month - 1] or not 1 <= year <= 9999:
        raise ValueError(f"{year}.{month}.{day} is not a date of the game's calendar (365 days, no 29 February)")
    return year, month, day


def parse_date(text: str) -> Date:
    """`1900` (its 1 January) or `1900.1.1` as a Date; ValueError for anything else."""
    found = _DATE_TEXT.fullmatch(text.strip()) if isinstance(text, str) else None
    if found is None:
        raise ValueError(f"a date is a year (1900) or year.month.day (1900.1.1), not {text!r}")
    year, month, day = found.groups()
    return check_date((int(year), int(month or 1), int(day or 1)))


def day_number(date: Date) -> int:
    year, month, day = check_date(date)
    return year * 365 + sum(MONTH_DAYS[:month - 1]) + day - 1


def from_day_number(number: int) -> Date:
    year, rest = divmod(number, 365)
    month = 1
    while rest >= MONTH_DAYS[month - 1]:
        rest -= MONTH_DAYS[month - 1]
        month += 1
    return check_date((year, month, rest + 1))


def shift(date: Date, days: int) -> Date:
    return from_day_number(day_number(date) + days)


def dotted(date: Date) -> str:
    """`1900.1.1`, the form `-run_until` and the scripted test take."""
    year, month, day = check_date(date)
    return f"{year}.{month}.{day}"


def written(date: Date) -> str:
    """`1 January, 1900`: how the engine wrote the date into the name of the 1836 fixture's save
    (`TEST_FAIL_te_qa_fixture_2 January, 1836.v3`). One data point: a later date is taken to be written alike."""
    year, month, day = check_date(date)
    return f"{day} {MONTH_NAMES[month - 1]}, {year}"


def run_until(date: Date) -> Date:
    return shift(date, RUN_ON_DAYS)


def fixture_args(date: Date = DEFAULT_DATE) -> tuple[str, ...]:
    """The launch arguments of the run that makes the fixture dated `date`: FIXTURE_ARGS for the plain one."""
    return (*FIXTURE_ARGS[:-1], f"-run_until={dotted(run_until(date))}")


def expected_save(date: Date) -> str:
    """The name the engine is expected to give the run's save: what the 1836 run left, with the date changed."""
    return f"TEST_FAIL_te_qa_fixture_{written(date)}.v3"


def dated_key(key: str, date: Date) -> str:
    """The fixture key of the fixture dated `date` on the build `key` names: `key` itself for DEFAULT_DATE."""
    _check_key(key)
    date = check_date(date)
    if date == DEFAULT_DATE:
        return key
    out = f"{key}{DATED_MARK}{date[0]:04d}{date[1]:02d}{date[2]:02d}"
    _check_key(out)
    return out


def date_of_key(key: str) -> Date | None:
    """The date a dated fixture's key names (its switched copies' too), or None for a plain one."""
    base = _base_key_of(key) or key
    found = _DATED_KEY.fullmatch(base)
    if found is None:
        return None
    try:
        return check_date((int(found.group(2)), int(found.group(3)), int(found.group(4))))
    except ValueError:
        return None


def game_end(define_folders: Sequence[Path]) -> Date:
    """NGame.END_DATE as the game loads it: the last `END_DATE = "y.m.d"` in the `.txt` files of the last of
    `define_folders` (each a `common/defines` folder, vanilla's first) that names one; VANILLA_END_DATE if none
    does. A run whose `-run_until` is past it has no tested behaviour: the game ends there."""
    found: Date | None = None
    for folder in define_folders:
        try:
            names = sorted(name for name in os.listdir(folder) if name.endswith(".txt"))
        except OSError:
            continue
        for name in names:
            try:
                text = (Path(folder) / name).read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            for match in _END_DATE.finditer(text):
                try:
                    found = check_date(tuple(int(part) for part in match.groups()))
                except ValueError:
                    continue
    return found or VANILLA_END_DATE


def check_fixture_date(date: Date, end: Date) -> Date:
    """`date` once a fixture can be made there: not before DEFAULT_DATE (the scripted test fails on the second day
    at the earliest), and with its `-run_until` before the game's END_DATE `end`. ValueError otherwise."""
    date = check_date(date)
    if day_number(date) < day_number(DEFAULT_DATE):
        raise ValueError(f"a fixture is made on {dotted(DEFAULT_DATE)} at the earliest (the game's second day), "
                         f"not {dotted(date)}")
    if day_number(run_until(date)) >= day_number(end):
        raise ValueError(f"the run would end on {dotted(run_until(date))}, at or past the game's END_DATE "
                         f"{dotted(end)}: what the game does there unattended is not known")
    return date


def seconds_per_day(year: float) -> float:
    """The estimated wall seconds of one game day in `year` (RATE_ANCHORS)."""
    anchors = RATE_ANCHORS
    if year <= anchors[0][0]:
        return anchors[0][1]
    for (y0, r0), (y1, r1) in zip(anchors, anchors[1:]):
        if year <= y1:
            return r0 + (r1 - r0) * (year - y0) / (y1 - y0)
    (y0, r0), (y1, r1) = anchors[-2], anchors[-1]
    return r1 + (r1 - r0) * (year - y1) / (y1 - y0)


def _run_seconds(first: Date, last: Date) -> float:
    """The estimated wall seconds of the game days after `first` up to `last`, by year."""
    start, end = day_number(first), day_number(last)
    total = 0.0
    number = start
    while number < end:
        year = number // 365
        upto = min(end, (year + 1) * 365)
        total += (upto - number) * seconds_per_day(year + ((number + upto) / 2 - year * 365) / 365)
        number = upto
    return total


def estimate_s(date: Date) -> float:
    """The estimated wall seconds of the run that makes the fixture dated `date`: LOAD_S, and every game day from
    the start to its `-run_until`."""
    return LOAD_S + _run_seconds(START_DATE, run_until(date))


def time_limit_s(date: Date) -> float:
    """How long the fixture waits for the run's game to quit before it takes it for hung: FIXTURE_LIMIT_S, the 1836
    run's limit, plus LIMIT_FACTOR times the estimate of every day the run goes on past the 1836 fixture's."""
    return FIXTURE_LIMIT_S + LIMIT_FACTOR * _run_seconds(run_until(DEFAULT_DATE), max(
        run_until(date), run_until(DEFAULT_DATE), key=day_number))


def save_date(path: Path) -> Date | None:
    """The `game_date` the save's own `meta_data` gives (`\\tgame_date=1836.1.2` near its start: a plain-text save
    of the harness's), or None when its first 64 KB hold none."""
    try:
        with open(path, "rb") as handle:
            head = handle.read(64 * 1024)
    except OSError:
        return None
    found = _SAVE_DATE.search(head)
    if found is None:
        return None
    try:
        return check_date(tuple(int(part) for part in found.groups()))
    except ValueError:
        return None


def written_date(name: str) -> Date | None:
    """The date a run's save name gives (`TEST_FAIL_te_qa_fixture_2 January, 1836.v3`), or None."""
    found = _WRITTEN_DATE.fullmatch(name)
    if found is None or found.group(2) not in MONTH_NAMES:
        return None
    try:
        return check_date((int(found.group(3)), MONTH_NAMES.index(found.group(2)) + 1, int(found.group(1))))
    except ValueError:
        return None


def timing(text: str) -> dict:
    """The game's own timing of a run, from its `gametimer_*.tsv`: `days` (game days with a `Day` row), `seconds`
    (their rows summed: the time of the day's ticks, a little under the wall clock), `seconds_per_day`, and
    `years`, {year: seconds per day}. The file's `Month` rows repeat the month's days and are not counted."""
    per_day: dict[str, float] = {}
    for line in text.splitlines()[1:]:
        parts = [part.strip() for part in line.split("\t")]
        if len(parts) != 3 or parts[1] != "Day":
            continue
        try:
            per_day[parts[0]] = per_day.get(parts[0], 0.0) + float(parts[2])
        except ValueError:
            continue
    years: dict[str, list[float]] = {}
    for day, seconds in per_day.items():
        years.setdefault(day[:4], []).append(seconds)
    total = sum(per_day.values())
    return {"days": len(per_day), "seconds": round(total, 1),
            "seconds_per_day": round(total / len(per_day), 3) if per_day else None,
            "years": {year: round(sum(values) / len(values), 3) for year, values in sorted(years.items())}}


class RunLogs:
    """A dated run's `debug.log` and `error.log`, copied into its run folder (`fixture_debug.log`,
    `fixture_error.log`) as the game writes them. The game rotates each log at 512 KB through six generations, so
    of a run that lasts years only the last few megabytes are still in `logs/` when it ends, and the lines a new
    game logs at its setup are long gone: they survive only in this copy.

    Each log is followed by its inode across rotation (`LogFollower`); `found` gives, per log, the (size, SHA-256)
    the run's snapshot recorded, so a log the game appended to has the owner's beginning skipped.
    `found_unknown` says that record could not be read: everything is copied, and the record says so. A rotation the
    follower missed is written as GAP_MARKER and counted in `gaps`. `poll` never raises: the first error stops the
    copying for good and is kept in `error` (a copy with a hole in it would pass for a whole one).

    Whose lines these are is vouched for by the run's restore, not here: a game beside the run's (which `watch`
    journals) holds the restore, and the fixture's lines are kept only after a restore that went through."""

    def __init__(self, logs_dir: Path, out_dir: Path, found: Mapping[str, tuple[int, str] | None] | None = None,
                 found_unknown: bool = False):
        self.found_unknown = found_unknown      # the snapshot gave no record of the logs: nothing could be skipped
        found = dict(found or {})
        self.out_dir = Path(out_dir)
        self.followers = {name: LogFollower(Path(logs_dir) / name, found=found.get(name)) for name in RUN_LOGS}
        self.lines = dict.fromkeys(RUN_LOGS, 0)
        self.gaps = 0
        self.skipped: dict[str, int] = {}
        self.error: str | None = None
        self.polls = 0

    def copy(self, name: str = "debug.log") -> Path:
        return self.out_dir / (RUN_LOG_COPY % name)

    def poll(self) -> None:
        if self.error is not None:
            return
        self.polls += 1
        try:
            for name, follower in self.followers.items():
                lines = follower.poll()
                if follower.skipped:
                    self.skipped[name] = follower.skipped
                if not lines:
                    continue
                self.gaps += sum(1 for line in lines if line == GAP_MARKER)
                self.out_dir.mkdir(parents=True, exist_ok=True)
                with open(self.copy(name), "a", encoding="utf-8", newline="\n") as handle:
                    handle.write("".join(line + "\n" for line in lines))
                self.lines[name] += len(lines)
        except Exception as error:
            self.error = f"{type(error).__name__}: {error}"

    def record(self) -> dict:
        out: dict = {"files": {name: str(self.copy(name)) for name in RUN_LOGS}, "lines": dict(self.lines),
                     "gaps": self.gaps, "polls": self.polls}
        if self.skipped:
            out["prefix_skipped"] = dict(self.skipped)
        if self.error is not None:
            out["error"] = self.error
        if self.found_unknown:
            out["found_unknown"] = True
        return out


class FixtureError(Exception):
    """A step of `make` that did not go through.

    `step` is the verb that refused (`snapshot`, `launch`, `watch`, `restore`) or the part of `make` that
    failed (`check` before anything ran, `save` when the run left no single save, `rename`); `reply` is the
    verb's reply, `{}` when no verb is to blame; `snapshot` is the snapshot's id once one was taken.

    `code` is GAME_MAY_BE_UP when a game of the run may still be up: the snapshot was then NOT restored, and the
    caller ends that game (`proc`, its pid and start time, when known) and finishes the snapshot; `watch` is the
    handle of the `watch` following it (None when none could be started), which may still be running. `restore`
    is the (reply, exit code) of the fixture's own restore, None when it was not run. `saved` is the fixture's save
    when the run's save had been given its name before the failure (a restore that held or was refused after it):
    the save is there, and a later start can load it once the owner has resolved the hold. `left` is the run's
    save under the engine's name when it could be neither renamed nor copied: the run's restore was asked to hold
    (HOLD_ASKED) so that it is not removed, and the owner moves it."""

    def __init__(self, message: str, step: str, reply: dict | None = None, snapshot: str | None = None, *,
                 code: str | None = None, proc: ProcId | None = None, watch: Any = None,
                 restore: tuple[dict, int] | None = None, saved: Path | None = None, left: Path | None = None):
        super().__init__(message)
        self.left = left
        self.step = step
        self.reply = reply if reply is not None else {}
        self.snapshot = snapshot
        self.code = code
        self.proc = proc
        self.watch = watch
        self.restore = restore
        self.saved = saved


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
        disabled_dlc: Sequence = (), rules: Sequence[str] = ()) -> str:
    """12 hex digits naming the game a fixture was made for: the game version, the run's playset (its mode,
    `playset`, `enabled_mods`, the mod paths the run loads, in order, and `disabled_dlc`, the DLC the run's
    playset switches off, as a set: launch keeps the owner's `disabledDLC`), `rules`, the rule settings the
    owner last applied in a lobby, in the file's order (an unattended new game is made under them, not under
    the defaults: game_qa.rules), and the relative path, size and
    modification time of every file under the deployed mod's `common/`, `events/` and `map_data/` (a folder that
    is missing is skipped). A fixture made under another playset, or another DLC set, is another world: a DLC
    changes what a new game sets up even where the script folders loaded are the same. Not covered: for
    `current`, the other mods' contents (only their paths are hashed), so an update of one keeps the key."""
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
    *,
    spawn_watch: SpawnWatch,
    clock=time.monotonic,
    started: Callable[[str], ProcId | None] | None = None,
    keep_lines: Callable[[str], Any] | None = None,
    date: Date = DEFAULT_DATE,
    limit_s: float = FIXTURE_LIMIT_S,
    follow: Callable[[str], Any] | None = None,
    long_run: str | None = None,
    facts: dict | None = None,
    mark: Callable[..., Any] | None = None,
) -> Path:
    """Make the fixture for `key` with one unattended run of the game, and return its save. `playset` is the
    run's (`launch --playset`), so the fixture is made in the world the run will load.

    `date` is the save's date (DEFAULT_DATE: the 1836 fixture): the overlay's scripted test must have been built
    for it (`overlay.build(..., fixture_date=date)`), and the launch carries its `-run_until` (`fixture_args`) and,
    for a run past SHORT_RUN_LAST, `--long-run` with `long_run`, the owner's grant for it. `limit_s` replaces
    FIXTURE_LIMIT_S as the wait for the game to quit (`time_limit_s`). `follow(snapshot_id)`, when given, is
    called every FOLLOW_S while `watch` follows the game and once more when it has recorded the exit, before the
    save is renamed (a dated run copies its logs so: `RunLogs`); it must not raise. `facts`, when given, is
    filled with what was found of the run's save: `save_found` (the name the engine gave it), `save_expected`,
    `game_date` (from the save's own meta_data) and `date_matches`. A name or a date other than the expected is
    reported there, never refused: one save is the only test, since the restore would remove it. `mark(snapshot_id,
    event, **fields)` journals an event in the run's snapshot: when the save could be neither renamed nor copied,
    HOLD_ASKED, so that the restore holds rather than remove it.

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

    launch = ["launch", snapshot, "--permission", permission, "--playset", playset, "--add-mod", overlay_windows_path]
    if owner_confirmed_busy:
        launch.append("--owner-confirmed-busy")
    if long_run is not None:
        launch += ["--long-run", long_run]
    launch += ["--", *fixture_args(date)]

    run = _run(run_cli, launch, snapshot, saves, target, spawn_watch, sleep, clock, started, limit_s, follow,
               date, facts)
    if run.up is not None:
        failure = run.failure
        raise FixtureError(f"the fixture's run (snapshot {snapshot}) may have left its game up: {run.up}, so it was "
                           f"not restored. {failure}", failure.step, failure.reply, snapshot, code=GAME_MAY_BE_UP,
                           proc=run.proc, watch=run.watch)
    if run.failure is not None and run.failure.left is not None:
        _ask_hold(mark, snapshot, run.failure)
    restored = restore_retried(run_cli, snapshot, sleep, RESTORE_RETRIES)
    restore_failure = None if restored[1] == 0 else _failure("restore", restored[0], snapshot)
    failure = run.failure
    if failure is None:
        failure = restore_failure
    elif restore_failure is not None:
        failure = FixtureError(f"{failure}. Then {restore_failure}", failure.step, failure.reply, snapshot,
                               left=failure.left)
    if failure is not None:
        failure.restore = restored
        if run.failure is None and target.is_file():
            failure.saved = target          # the run's save has its name: only the restore failed after it
        raise failure
    if keep_lines is not None:
        keep_lines(snapshot)
    return target


def _ask_hold(mark, snapshot: str, failure: FixtureError) -> None:
    """Journal HOLD_ASKED for the run's save that could not be kept under the fixture's name, so that the restore
    leaves it; when that cannot be journaled the message says the restore may remove it."""
    name = f"{SAVE_FOLDER}/{failure.left.name}"
    try:
        if mark is None:
            raise RuntimeError("no way to journal it was given")
        mark(snapshot, HOLD_ASKED, reason="save_not_kept", files=[name])
    except Exception as error:
        failure.args = (f"{failure}. The hold could not be asked for ({error!r}): the restore may remove {name}",)


_SWITCHED_KEY = re.compile(r"(.+)_s[0-9a-f]{8}")     # SWITCHED_MARK and the eight hex digits rules.switched_key adds


def prune(user_data: Path, keep: int = 2, keep_switched: int = 2, in_use: Sequence[str] = (),
          keep_dated: int = DATED_KEPT) -> list[str]:
    """Remove all but the `keep` newest `te_qa_fixture_*.v3` files directly in `save games/` (newest by
    modification time, equal times by name) and return the names removed, oldest first. Nothing else is touched.

    A dated fixture (its key ends in DATED_MARK and eight digits) is not counted among those: it cost a run of
    hours, so two cheap 1836 fixtures must never push it out. Of the dated ones the `keep_dated` newest stay,
    whatever their dates. A newer fixture of the same date does not make an older one go: the key cannot say
    whether the older one is of an earlier build or of the other playset, and a fixture of the other playset is
    no less in use.

    A copy with a rule switched (its key ends in SWITCHED_MARK and eight hex digits) is not counted among
    either: it is removed with the fixture it was made from, plain or dated, and of the ones whose fixture stays
    only the `keep_switched` newest are kept. Counted together, two switched copies would push out the fixture
    they came from, and the next start would pay for a new run.

    `in_use` names files (as in the folder) that are never removed, whatever their age: the save a session is
    about to load, and the fixture it was copied from. A copy used again keeps its old time, so age alone
    could remove the very save the reply names."""
    if keep < 0 or keep_switched < 0 or keep_dated < 0:
        raise ValueError("keep is a count of fixtures, not negative")
    found = sorted(
        (path.stat().st_mtime_ns, path.name, path)
        for path in (Path(user_data) / SAVE_FOLDER).glob(FIXTURE_GLOB)
        if path.is_file() and not path.is_symlink()
    )
    protected = set(in_use)
    switched = [entry for entry in found if _base_key(entry[1]) is not None]
    dated = [entry for entry in found if _base_key(entry[1]) is None and date_of_key(_key_of(entry[1])) is not None]
    plain = [entry for entry in found if entry not in switched and entry not in dated]
    doomed = [entry for entry in plain[: max(len(plain) - keep, 0)] if entry[1] not in protected]
    doomed += [entry for entry in dated[: max(len(dated) - keep_dated, 0)] if entry[1] not in protected]
    going = {entry[1] for entry in doomed}
    kept_keys = {_key_of(entry[1]) for entry in plain + dated if entry[1] not in going}
    orphans = [entry for entry in switched if _base_key(entry[1]) not in kept_keys and entry[1] not in protected]
    living = [entry for entry in switched if entry not in orphans]
    extra = [entry for entry in living[: max(len(living) - keep_switched, 0)] if entry[1] not in protected]
    doomed = sorted(doomed + orphans + extra)
    for _, _, path in doomed:
        path.unlink()
    return [name for _, name, _ in doomed]


def _base_key(name: str) -> str | None:
    """The key of the fixture a switched copy was made from, or None for a file that is not one."""
    return _base_key_of(_key_of(name))


def _base_key_of(key: str) -> str | None:
    found = _SWITCHED_KEY.fullmatch(key)
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
         sleep, clock, started, limit_s: float = FIXTURE_LIMIT_S, follow=None, date: Date = DEFAULT_DATE,
         facts: dict | None = None) -> _Run:
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
    deadline = clock() + limit_s
    next_follow = clock()
    try:
        while (code := watch.poll()) is None:
            if follow is not None and clock() >= next_follow:
                _follow(follow, snapshot)
                next_follow = clock() + FOLLOW_S
            if clock() >= deadline:
                why = f"the game had not quit {limit_s:g} s after its launch (its `watch` still follows it)"
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
    if follow is not None:
        _follow(follow, snapshot)   # the last lines, written as the game quit: the restore copies `logs/` as late
    if failure is not None:
        return _Run(failure)        # the game launch started has quit and watch recorded it: restore judges the rest
    try:
        _keep_the_save(saves, target, date, facts, sleep)
    except FixtureError as error:
        error.snapshot = snapshot
        return _Run(error)
    return _Run()


def _follow(follow, snapshot: str) -> None:
    try:
        follow(snapshot)
    except Exception:
        pass                        # a copy of the logs is never worth the run: RunLogs keeps its own error


def _named_proc(reply: dict) -> ProcId | None:
    try:
        return ProcId(int(reply["pid"]), str(reply["created"]))
    except (KeyError, TypeError, ValueError):
        return None


def _keep_the_save(saves: Path, target: Path, date: Date = DEFAULT_DATE, facts: dict | None = None,
                   sleep=time.sleep) -> None:
    """Give the run's one `TEST_FAIL_te_qa_fixture_*.v3` save the fixture's name. Exactly one such save is the only
    test (`make` refused to start beside one, so it is the run's): its name and its own date are reported in
    `facts`, never refused, since the restore that follows would remove it with the run's hours. A rename that
    fails is tried again (RENAME_TRIES, RENAME_RETRY_S), then the save is copied to the name; one that can be
    neither is raised with `left`, the save, for the restore to be held over it."""
    made = _run_saves(saves)
    if not made:
        raise FixtureError(f"the run left no {RUN_SAVE_GLOB} in save games/", "save")
    if len(made) > 1:
        names = [path.name for path in made]
        raise FixtureError(f"the run left {len(made)} saves, {', '.join(names)}: which is the fixture?", "save", {"saves": names})
    if target.exists():
        raise FixtureError(f"{target.name} appeared during the run and is left as it is", "rename")
    error: OSError | None = None
    tries = 0
    for tries in range(1, RENAME_TRIES + 1):
        try:
            os.rename(made[0], target)
            error = None
            break
        except OSError as failed:
            error = failed
        if tries < RENAME_TRIES:
            sleep(RENAME_RETRY_S)
    kept_by = "rename"
    if error is not None:
        try:
            _copy_to(made[0], target)
            kept_by = "copy"                # the run's own copy stays under its name: the restore removes it
        except OSError as copy_error:
            raise FixtureError(
                f"{made[0].name} could not be renamed to {target.name} in {tries} tries over about "
                f"{(tries - 1) * RENAME_RETRY_S:g} s ({error}), nor copied ({copy_error}): it is left in save games/ "
                "under its own name, and the run's restore holds so that it is not removed", "rename",
                {"error": str(error), "copy_error": str(copy_error), "left": made[0].name}, left=made[0]) from error
    if facts is not None:
        found = save_date(target)
        facts.update(save_found=made[0].name, save_expected=expected_save(date), name_date=_dotted_or_none(
            written_date(made[0].name)), game_date=_dotted_or_none(found), date_matches=found == check_date(date),
            kept_by=kept_by, rename_tries=tries)


def _copy_to(source: Path, target: Path) -> None:
    """Copy `source` to `target` through a `.part` beside it, so that a copy cut short never has the name."""
    part = target.with_name(target.name + ".part")
    try:
        shutil.copy2(source, part)
        os.replace(part, target)
    except OSError:
        try:
            part.unlink()
        except OSError:
            pass
        raise


def _dotted_or_none(date: Date | None) -> str | None:
    return dotted(date) if date is not None else None

