"""Profiling a running game (#1700): the game's own dumps, copied into the run folder, and what they say.

Three sources, all plain files the game writes:

    ticktask_timings.csv          in the user-data ROOT, from console `dump_ticktask_timings`: one row per engine
                                  tick task per frame since `clear_ticktask_timings`, `frame,task,milliseconds,
                                  calls,longest_lock`, the frame being the game date in hours (four a day: hours
                                  0, 6, 12 and 18). Each dump overwrites the file in place
    logs/script_profiling.txt     from `ScriptProfiling.Dump`: `type location seconds calls` per trigger, script value
                                  and a few effects, cumulative since `ScriptProfiling.Enable`; overwritten each dump
    logs/dedicated_server.log     a `Processing Tick: <Y.M.D[.H]>` line per frame, stamped with the wall-clock second,
                                  `Pause Toggled! Paused: true|false` at every pause key, `Changing game speed to: N`.
                                  It rotates at about 512 KB, within one run too, like debug.log

The session (`Session.profile_start`, `Session.profile_dump`) copies the first two into the run folder as
`tt_<label>.csv` and `sp_<label>.txt` the moment each is written, and follows the third into the run folder's
`dedicated_server.log`. `summary` reads those copies back and needs no game: wall clock per frame type, the top
tick tasks, and script time by file, mod against vanilla.

Facts behind the rules (2026-11-12, the owner's 1931 save on 1.15.1; docs/audits/late_game_performance.md):

- A tick-task frame is `((year + 5000) * 365 + day of the year) * 24 + hour`: the game's years have 365 days.
- About 130 tasks run only on the hour-0 frame of one day in seven, `WeeklyUpdateJournalEntries` among them; on that
  save it was the day whose number (frame // 24) is 2 mod 7, in every log generation from 1929 to 1938. The phase is
  read from a tt file when one names it, and WEEKLY_PHASE is the fallback.
- The wall time of a frame is the gap from its `Processing Tick` line to the next one. A pause line between two ticks
  means the harness (or a person) paused the game there, so no gap is taken across one: the summary's segments are
  the stretches the game ran.
- The log's stamps are Windows local time, whole seconds, wrapping at midnight. They are never compared with any
  other clock: windows are joined by game date (the tt file's frames), never by wall time.
"""
from __future__ import annotations

import bisect
import csv
import io
import os
import re
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from game_qa.logtail import GAP_MARKER

# The console commands, in the spelling the 2026-11-12 sessions used (with their answers).
CLEAR_COMMAND = "clear_ticktask_timings"        # "Discarded 0 recorded frames"
ENABLE_COMMAND = "ScriptProfiling.Enable"       # "Enabled"
TT_DUMP_COMMAND = "dump_ticktask_timings"       # "Wrote 7785 rows to C:/Users/…/Victoria 3/ticktask_timings.csv"
SP_DUMP_COMMAND = "ScriptProfiling.Dump"        # "Wrote logs/script_profiling.txt"

# Where the game writes them, relative to the user-data folder.
TT_FILE = "ticktask_timings.csv"
SP_FILE = "logs/script_profiling.txt"
SERVER_LOG = "logs/dedicated_server.log"

# What the run folder holds.
TT_PREFIX, TT_SUFFIX = "tt_", ".csv"
SP_PREFIX, SP_SUFFIX = "sp_", ".txt"
RUN_SERVER_LOG = "dedicated_server.log"         # the session's copy: every line read since the first profile start

TT_HEADER = ["frame", "task", "milliseconds", "calls", "longest_lock"]
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}")
FRAMES_PER_DAY = 4
YEAR_OFFSET = 5000
WEEKLY_PHASE = 2                                # day number mod 7 of the weekly frame (2026-11-12, 1929-1938)
WEEKLY_TASK = "WeeklyUpdateJournalEntries"      # a task that runs on the weekly frame alone
MAX_GAP_S = 60                                  # a longer gap inside a segment is counted apart, not as a frame
REFERENCE_LOCATION = "common/pop_types/aristocrats.txt:33"  # a per-tick vanilla entry: the audit's clock
KINDS = ("month_start", "weekly", "ordinary", "sub")
KIND_TEXT = {"month_start": "hour 0 on the 1st", "weekly": "hour 0, weekly day", "ordinary": "hour 0, ordinary day",
             "sub": "hours 6, 12 and 18"}
DUMP_WAIT_S = 15.0                              # from the console's answer to the file holding still, new
SETTLE_S = 0.5                                  # two looks this far apart must agree before a copy

_DAYS_BEFORE = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
_STAMP = re.compile(r"\[(\d\d):(\d\d):(\d\d)\]")
_TICK = re.compile(r"Processing Tick: (\d{1,4})\.(\d{1,2})\.(\d{1,2})(?:\.(\d{1,2}))?\s*$")
_PAUSE = re.compile(r"Pause Toggled! Paused: (true|false)\b")
_SPEED = re.compile(r"Changing game speed to: (\d+)")
_LINE_NUMBER = re.compile(r":\d+$")
_WROTE_ROWS = re.compile(r"Wrote (\d+) rows to (.+)$")
_DAY_S = 24 * 3600


class ProfileError(Exception):
    """A dump or a summary that did not go through. `code` names why (not_written, changed, bad_tick_tasks,
    bad_script_profile, no_profile, no_dump, label_used, bad_label, restarted_between, unreadable)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__("%s: %s" % (code, detail))
        self.code, self.detail = code, detail


# ---- game dates


def day_number(year: int, month: int, day: int) -> int:
    """The game's day count, as the tick-task frames number days: 365-day years from year -5000."""
    return (year + YEAR_OFFSET) * 365 + _DAYS_BEFORE[month - 1] + day - 1


def frame_of(year: int, month: int, day: int, hour: int = 0) -> int:
    return day_number(year, month, day) * 24 + hour


def date_of_frame(frame: int) -> tuple[int, int, int, int]:
    """(year, month, day, hour) of a tick-task frame."""
    day, hour = divmod(frame, 24)
    year, in_year = divmod(day, 365)
    month = bisect.bisect_right(_DAYS_BEFORE, in_year)
    return year - YEAR_OFFSET, month, in_year - _DAYS_BEFORE[month - 1] + 1, hour


def frame_text(frame: int) -> str:
    """A frame as the server log writes it: `1931.7.2.18`, and `1931.7.2` for hour 0."""
    year, month, day, hour = date_of_frame(frame)
    return "%d.%d.%d" % (year, month, day) + (".%d" % hour if hour else "")


def frame_kind(frame: int, weekly_phase: int) -> str:
    """month_start (hour 0 on the 1st, whatever the weekday), weekly (hour 0 on the weekly day), ordinary (any
    other hour 0) or sub (hours 6, 12 and 18)."""
    _year, _month, day, hour = date_of_frame(frame)
    if hour:
        return "sub"
    if day == 1:
        return "month_start"
    return "weekly" if (frame // 24) % 7 == weekly_phase else "ordinary"


# ---- the console's answers


def rows_written(lines: Sequence[str]) -> tuple[int, str] | None:
    """(rows, path) from `dump_ticktask_timings`'s answer ("Wrote 7785 rows to C:/…/ticktask_timings.csv"), or
    None when no line says that."""
    for line in lines:
        match = _WROTE_ROWS.search(line.strip())
        if match:
            return int(match.group(1)), match.group(2).strip()
    return None


def names_file(path: str, name: str) -> bool:
    """Whether a path the game printed ends in the file `name`, in any case and with either separator."""
    return path.replace("\\", "/").rstrip().lower().rsplit("/", 1)[-1] == name.lower()


# ---- tick tasks


@dataclass(frozen=True)
class TaskRow:
    frame: int
    task: str
    ms: float
    calls: int
    longest_lock: int


def parse_tick_tasks(text: str) -> list[TaskRow]:
    """The rows of a `ticktask_timings.csv` (a BOM is allowed). ProfileError `bad_tick_tasks` for another header
    or a row that does not read: a copy cut short must not pass for a dump."""
    reader = csv.reader(io.StringIO(text.removeprefix("\ufeff")))
    header = next(reader, None)
    if header != TT_HEADER:
        raise ProfileError("bad_tick_tasks", "the header is %r, not %s" % (header, ",".join(TT_HEADER)))
    rows = []
    for number, fields in enumerate(reader, start=2):
        if not fields:
            continue
        try:
            frame, task, ms, calls, lock = fields
            rows.append(TaskRow(int(frame), task, float(ms), int(calls), int(lock)))
        except ValueError:
            raise ProfileError("bad_tick_tasks", "line %d does not read as a row: %r" % (number, fields)) from None
    return rows


def weekly_phase(rows: Iterable[TaskRow]) -> int | None:
    """The day number mod 7 of the frames that run WEEKLY_TASK, when they all agree; else None."""
    phases = {(row.frame // 24) % 7 for row in rows if row.task == WEEKLY_TASK}
    return phases.pop() if len(phases) == 1 else None


def tick_tasks(rows: Sequence[TaskRow], weekly: int, top: int = 25) -> dict:
    """What the tick tasks cost over `rows`' frames: `frames`, `days`, `ms`, `ms_per_day`; `kinds`, per frame type
    its frames, its tasks' milliseconds per frame and its five costliest tasks per frame; and `top`, the costliest
    tasks overall, each with its share, calls and milliseconds per game day."""
    per_frame: dict[int, float] = defaultdict(float)
    per_task: dict[str, list] = defaultdict(lambda: [0.0, 0])
    per_kind_task: dict[str, dict[str, float]] = {kind: defaultdict(float) for kind in KINDS}
    for row in rows:
        per_frame[row.frame] += row.ms
        per_task[row.task][0] += row.ms
        per_task[row.task][1] += row.calls
        per_kind_task[frame_kind(row.frame, weekly)][row.task] += row.ms
    total = sum(per_frame.values())
    days = len(per_frame) / FRAMES_PER_DAY
    kinds = {}
    for kind in KINDS:
        frames = [frame for frame in per_frame if frame_kind(frame, weekly) == kind]
        if not frames:
            continue
        tasks = sorted(per_kind_task[kind].items(), key=lambda item: -item[1])[:5]
        kinds[kind] = {"text": KIND_TEXT[kind], "frames": len(frames),
                       "ms_each": _round(sum(per_frame[f] for f in frames) / len(frames)),
                       "top": [{"task": task, "ms_each": _round(ms / len(frames))} for task, ms in tasks]}
    ranked = sorted(per_task.items(), key=lambda item: -item[1][0])[:top]
    return {
        "frames": len(per_frame), "days": days, "ms": _round(total),
        "ms_per_day": _round(total / days) if days else None,
        "first": frame_text(min(per_frame)) if per_frame else None,
        "last": frame_text(max(per_frame)) if per_frame else None,
        "kinds": kinds,
        "top": [{"task": task, "ms": _round(ms), "share": _round(ms / total, 4) if total else None, "calls": calls,
                 "ms_per_day": _round(ms / days) if days else None} for task, (ms, calls) in ranked],
    }


# ---- the server log


@dataclass(frozen=True)
class LogEvent:
    kind: str               # tick, run (Paused: false), pause (Paused: true), speed, break (a gap marker, a clock step)
    second: int | None      # seconds since the log's first stamp, the midnights it crossed counted
    frame: int | None = None
    value: int | None = None


def parse_server_log(lines: Iterable[str]) -> list[LogEvent]:
    """The events of a dedicated_server.log, in order. A stamp earlier than the one before is a midnight crossed
    when it is more than twelve hours earlier, and otherwise a clock stepped back, which breaks the chain of ticks
    as a pause does (`break`). The follower's GAP_MARKER (lines lost in rotation) is a `break` too."""
    events: list[LogEvent] = []
    offset, last = 0, None
    for line in lines:
        if line.strip() == GAP_MARKER:
            events.append(LogEvent("break", None))
            continue
        stamp = _STAMP.match(line)
        if stamp is None:
            continue
        second = int(stamp.group(1)) * 3600 + int(stamp.group(2)) * 60 + int(stamp.group(3)) + offset
        if last is not None and second < last:
            if last - second > _DAY_S // 2:
                offset += _DAY_S
                second += _DAY_S
            else:
                events.append(LogEvent("break", second))
        last = second
        tick = _TICK.search(line)
        if tick:
            year, month, day = (int(tick.group(n)) for n in (1, 2, 3))
            hour = int(tick.group(4) or 0)
            if 1 <= month <= 12 and 1 <= day <= 31 and hour < 24:
                events.append(LogEvent("tick", second, frame_of(year, month, day, hour)))
            continue
        pause = _PAUSE.search(line)
        if pause:
            events.append(LogEvent("pause" if pause.group(1) == "true" else "run", second))
            continue
        speed = _SPEED.search(line)
        if speed:
            events.append(LogEvent("speed", second, value=int(speed.group(1))))
    return events


def wall_clock(events: Sequence[LogEvent], window: tuple[int, int], weekly: int) -> dict:
    """Wall time for the frames in `window` (its first and last frame, inclusive), whole seconds as the log has them.

    `running` is the time the game was seen running, per game day of the frames whose time it holds. It is the
    headline, since a pause key tends to land during a long frame. It adds up the `segments`, the unbroken
    stretches of play that hold ticks of the window. A stretch opens at a run line (`opened_by` run) and closes at
    the pause line after it (`closed_by` pause), holding every tick between. A break (lines lost in the log's
    rotation, or its clock stepping back) or a gap of MAX_GAP_S or more between two ticks cuts it: the stretch
    closes at its last tick before the cut, and that tick's frame, whose end is not seen, leaves its `ticks`
    (`closed_by` break or long_gap). Play resumes as a new stretch at the first tick after the cut (`opened_by`
    break or long_gap), so the time across a cut never counts. After a break, ticks before any run line are play
    seen from the first of them, since the lines lost may hold the run line. `breaks` counts the breaks between
    the window's first and last ticks.

    `kinds` splits it by frame type from the gaps: a frame's time is the gap from its tick to the next tick, taken
    only when no pause, run or break lies between them, so time paused never counts. A frame whose gap was not
    taken (the game was paused after it, or the log lost lines) is `uncounted`: the weekly and monthly frames are
    the ones a pause most often follows, so `each` is a mean over the counted ones and `gaps` undercounts them. A
    gap of MAX_GAP_S or more is not a frame's: it is listed in `long_gaps`, and is out of `running` too. `speeds`
    are the speed changes logged between the window's first and last ticks, and `speed_before` the last one before
    the first. `covered` gives the first and last tick of the window the log holds; a last tick before the window's
    end leaves `short_by` frames unread."""
    lo, hi = window
    stats: dict[str, list] = {kind: [0, 0] for kind in KINDS}
    ticks: dict[str, int] = dict.fromkeys(KINDS, 0)
    long_gaps: list[dict] = []
    prev: LogEvent | None = None
    seen: list[int] = []
    segments: list[dict] = []
    # The open stretch of play: `since` is the second it opened (None until the first tick, after a cut), `ticks`
    # the window's ticks in it, `last` its last tick of any frame.
    current: dict | None = None
    breaks: list[int] = []                  # len(seen) at each break
    speeds: list[tuple[int, dict]] = []
    speed_before: int | None = None

    def opened(by: str, since: int | None) -> dict:
        return {"by": by, "since": since, "ticks": 0, "last": None}

    def close(by: str, at: int | None = None) -> None:
        """Close the open stretch at the pause line's second `at`, or at its last tick (a cut, `at` None), whose
        frame then leaves the count: its time runs past the cut."""
        if current is None or current["since"] is None or current["last"] is None:
            return
        counted = current["ticks"]
        if at is None:
            at = current["last"].second
            if lo <= current["last"].frame <= hi:
                counted -= 1
        if counted > 0:
            segments.append({"from": current["from"], "to": current["to"], "ticks": counted,
                             "seconds": at - current["since"], "opened_by": current["by"], "closed_by": by})

    for event in events:
        if event.kind == "tick":
            gap = event.second - prev.second if prev is not None else None
            if gap is not None and lo <= prev.frame <= hi:
                if 0 <= gap < MAX_GAP_S:
                    entry = stats[frame_kind(prev.frame, weekly)]
                    entry[0] += 1
                    entry[1] += gap
                else:
                    long_gaps.append({"frame": frame_text(prev.frame), "seconds": gap})
            if gap is not None and not 0 <= gap < MAX_GAP_S and current is not None:
                close("long_gap")
                current = opened("long_gap", None)
            if current is not None and current["since"] is None:
                current["since"] = event.second
            if lo <= event.frame <= hi:
                seen.append(event.frame)
                ticks[frame_kind(event.frame, weekly)] += 1
                if current is not None:
                    current["ticks"] += 1
                    current.setdefault("from", frame_text(event.frame))
                    current["to"] = frame_text(event.frame)
            if current is not None:
                current["last"] = event
            prev = event
            continue
        if event.kind == "speed":
            if seen:
                speeds.append((len(seen), {"speed": event.value, "after": frame_text(seen[-1])}))
            else:
                speed_before = event.value
            continue
        prev = None
        if event.kind == "run":
            current = opened("run", event.second)
        elif event.kind == "pause":
            close("pause", event.second)
            current = None
        elif event.kind == "break":
            breaks.append(len(seen))
            close("break")
            current = opened("break", None)
    counted = sum(n for n, _ in stats.values())
    seconds = sum(s for _, s in stats.values())
    run_ticks = sum(segment["ticks"] for segment in segments)
    run_seconds = sum(segment["seconds"] for segment in segments)
    out = {
        "running": {"seconds": run_seconds, "ticks": run_ticks,
                    "seconds_per_day": _round(run_seconds * FRAMES_PER_DAY / run_ticks, 3) if run_ticks else None},
        "gaps": {"frames": counted, "seconds": seconds,
                 "seconds_per_day": _round(seconds * FRAMES_PER_DAY / counted, 3) if counted else None},
        "kinds": {kind: {"text": KIND_TEXT[kind], "frames": n, "uncounted": ticks[kind] - n, "seconds": s,
                         "each": _round(s / n, 3) if n else None,
                         "share": _round(s / seconds, 4) if seconds else None}
                  for kind, (n, s) in stats.items() if ticks[kind] or n},
        "segments": segments, "long_gaps": long_gaps,
        "breaks": sum(1 for count in breaks if 0 < count < len(seen)),
        "covered":{"first": frame_text(min(seen)), "last": frame_text(max(seen)), "ticks": len(seen)}
        if seen else None,
        # a change logged after the window's last tick is not the window's
        "speed_before": speed_before, "speeds": [change for count, change in speeds if count < len(seen)],
    }
    if seen and max(seen) < hi:
        out["short_by"] = (hi - max(seen)) // 6
    return out


# ---- the script profile


def parse_script_profile(text: str) -> dict[tuple[str, str], tuple[float, int]]:
    """{(type, location): (seconds, calls)} from a script_profiling.txt. ProfileError `bad_script_profile` when it
    has no header line, which a copy of something else would lack."""
    lines = text.removeprefix("\ufeff").splitlines()
    if not lines or not lines[0].startswith("# type, location"):
        raise ProfileError("bad_script_profile", "the first line is %r, not the dump's header"
                           % (lines[0][:80] if lines else ""))
    rows: dict[tuple[str, str], tuple[float, int]] = {}
    for line in lines[1:]:
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.rsplit(None, 2)
        if len(parts) != 3:
            continue
        head, seconds, calls = parts
        kind, _, location = head.partition(" ")
        try:
            rows[(kind.strip(), location.strip())] = (float(seconds), int(calls))
        except ValueError:
            continue
    return rows


def script_by_file(rows: Mapping[tuple[str, str], tuple[float, int]], origin: Callable[[str], str], days: float,
                   since: Mapping[tuple[str, str], tuple[float, int]] | None = None, top: int = 25) -> dict:
    """Script time by file over a window of `days` game days: `rows` minus `since` (the dump at the window's start,
    when it is not the profile's start). `origin(file)` says whose file it is (mod, add_mod, vanilla, other).

    `by_origin` sums each origin's seconds; `top` lists the costliest files with their origin, seconds, calls and
    milliseconds per game day; `reference` is REFERENCE_LOCATION's calls, the per-tick clock the audit compares two
    runs by. `counts_fell` counts entries whose calls are lower than in `since`: the profile was restarted between
    the two dumps, and the difference means nothing."""
    by_file: dict[str, list] = defaultdict(lambda: [0.0, 0])
    fell = 0
    reference = 0
    for key, (seconds, calls) in rows.items():
        before = (since or {}).get(key, (0.0, 0))
        if calls < before[1]:
            fell += 1
        seconds, calls = seconds - before[0], calls - before[1]
        by_file[_LINE_NUMBER.sub("", key[1])][0] += seconds
        by_file[_LINE_NUMBER.sub("", key[1])][1] += calls
        if key[1] == REFERENCE_LOCATION:
            reference += calls
    total = sum(seconds for seconds, _ in by_file.values())
    owners: dict[str, float] = defaultdict(float)
    whose = {name: origin(name) for name in by_file}
    for name, (seconds, _) in by_file.items():
        owners[whose[name]] += seconds
    ranked = sorted(by_file.items(), key=lambda item: -item[1][0])[:top]

    def per_day(seconds: float) -> float | None:
        return _round(seconds * 1000 / days, 2) if days else None
    return {
        "seconds": _round(total, 3), "ms_per_day": per_day(total), "files": len(by_file),
        "by_origin": {name: {"seconds": _round(seconds, 3), "ms_per_day": per_day(seconds),
                             "share": _round(seconds / total, 4) if total else None}
                      for name, seconds in sorted(owners.items(), key=lambda item: -item[1])},
        "top": [{"file": name, "origin": whose[name], "seconds": _round(seconds, 3), "calls": calls,
                 "ms_per_day": per_day(seconds)} for name, (seconds, calls) in ranked],
        "reference": {"location": REFERENCE_LOCATION, "calls": reference,
                      "calls_per_day": _round(reference / days, 1) if days else None},
        "counts_fell": fell,
    }


def origin_of(roots: Sequence[tuple[str, Path]]) -> Callable[[str], str]:
    """An `origin` for `script_by_file`: the name of the first root holding the file at that relative path, else
    `other` (another mod of the playset, or the dump's `<unknown>`). Give the roots in the order the game lets one
    override another, the last loaded first: the add-mods, the deployed mod, vanilla."""
    def origin(name: str) -> str:
        if not name or name.startswith("<") or ".." in Path(name).parts or Path(name).is_absolute():
            return "other"
        for label, root in roots:
            try:
                if (Path(root) / name).is_file():
                    return label
            except OSError:
                continue
        return "other"
    return origin


# ---- the run folder


def check_label(label: str) -> str:
    if not isinstance(label, str) or not LABEL.fullmatch(label):
        raise ProfileError("bad_label", "a label is 1 to 32 letters, digits, '_' or '-', beginning with a letter or a "
                                        "digit, not %r" % (label,))
    return label


def dump_paths(run_dir: Path, label: str) -> tuple[Path, Path]:
    """The run folder's copies of a dump: (tt_<label>.csv, sp_<label>.txt)."""
    run_dir = Path(run_dir)
    return run_dir / (TT_PREFIX + label + TT_SUFFIX), run_dir / (SP_PREFIX + label + SP_SUFFIX)


def profile_steps(steps: Sequence[Mapping]) -> list[Mapping]:
    """The run's `profile_start` and `profile_dump` steps that went through, in order."""
    return [step for step in steps if step.get("verb") in ("profile_start", "profile_dump")
            and step.get("outcome") == "ok"]


def summary(run_dir: Path, steps: Sequence[Mapping], labels: Sequence[str], origin: Callable[[str], str],
            top: int = 25) -> dict:
    """What a profile says, from the run folder alone.

    With no label: the newest dump, from the profile start before it. With one: that dump, from the profile start
    before it. With two: the window between them, the later minus the earlier (both after one profile start, the
    first dumped first). Raises ProfileError: `no_profile` (nothing was profiled in the run), `no_dump` (no such
    label, or its files are gone), `bad_label`, `restarted_between` (a profile start lies between the two dumps:
    the tick timings were cleared, so there is no window between them), `unreadable` (a copy that cannot be read).

    The reply: `window` (from and to, the labels, the frames' first and last), `tick_tasks` (`tick_tasks`),
    `wall_clock` (`wall_clock`, from the run's copy of dedicated_server.log, joined to the tt file by game date),
    `script` (`script_by_file`), `weekly_phase` and where it came from, and `notes`."""
    run_dir = Path(run_dir)
    done = profile_steps(steps)
    dumps = [step for step in done if step["verb"] == "profile_dump"]
    if not done:
        raise ProfileError("no_profile", "no `profile start` went through in this run")
    if not dumps:
        raise ProfileError("no_dump", "this run's profile has no dump yet: `profile dump [LABEL]`")
    for label in labels:
        check_label(label)
    if len(labels) > 2:
        raise ProfileError("bad_label", "give at most two labels, not %d" % len(labels))
    names = [step.get("label") for step in dumps]
    wanted = list(labels) or [names[-1]]
    for label in wanted:
        if label not in names:
            raise ProfileError("no_dump", "no dump is labelled %r in this run; its dumps are %s"
                               % (label, ", ".join(map(str, names))))
    at = {step.get("label"): done.index(step) for step in dumps}
    notes: list[str] = []
    if len(wanted) == 2:
        first, last = wanted
        if at[first] > at[last]:
            raise ProfileError("bad_label", "%s was dumped after %s: give the earlier one first" % (first, last))
        if first == last:
            raise ProfileError("bad_label", "the two labels are the same")
        if any(step["verb"] == "profile_start" for step in done[at[first] + 1:at[last]]):
            raise ProfileError("restarted_between", "a profile start between %s and %s cleared the tick timings, so "
                                                    "there is no window between them: summarize each by itself"
                               % (first, last))
    else:
        first, last = None, wanted[0]
    starts = [i for i, step in enumerate(done[:at[last]]) if step["verb"] == "profile_start"]
    if not starts:
        raise ProfileError("no_profile", "no `profile start` went through before the dump %s" % last)
    start_step = done[starts[-1]]
    if len(starts) > 1 and first is None:
        notes.append("the profile was started %d times in this run; the tick timings count from the last start, and "
                     "whether ScriptProfiling.Enable resets the script counts when it is already on is not verified, "
                     "so the script figures may count from the first start" % len(starts))

    tt_last, sp_last = dump_paths(run_dir, last)
    rows = _read(tt_last, parse_tick_tasks)
    script_rows = _read(sp_last, parse_script_profile)
    since = None
    if first is not None:
        tt_first, sp_first = dump_paths(run_dir, first)
        before = _read(tt_first, parse_tick_tasks)
        edge = max((row.frame for row in before), default=None)
        if edge is not None:
            rows = [row for row in rows if row.frame > edge]
        since = _read(sp_first, parse_script_profile)
    if not rows:
        raise ProfileError("no_dump", "the window holds no tick-task frame: no game time passed in it")
    phase = weekly_phase(rows)
    phase_source = "tick tasks"
    if phase is None:
        phase, phase_source = WEEKLY_PHASE, "default (no %s frame in the window)" % WEEKLY_TASK
    tasks = tick_tasks(rows, phase, top)
    window = (min(row.frame for row in rows), max(row.frame for row in rows))
    try:
        with open(run_dir / RUN_SERVER_LOG, encoding="utf-8", errors="replace") as handle:
            clock = wall_clock(parse_server_log(handle.read().splitlines()), window, phase)
    except FileNotFoundError:
        clock = None
        notes.append("the run folder has no %s: the wall clock is not known" % RUN_SERVER_LOG)
    except OSError as e:
        raise ProfileError("unreadable", "%s: %s" % (run_dir / RUN_SERVER_LOG, e)) from None
    if clock is not None and clock["covered"] is None:
        notes.append("the server log copy holds no tick of the window: the wall clock is not known")
    if clock is not None and clock.get("short_by") is not None:
        notes.append("the server log copy ends %d frames before the window does (its last lines were not read at "
                     "the dump)" % clock["short_by"])
    if clock is not None and clock["long_gaps"]:
        notes.append("%d gaps of %d s or more between two ticks are left out of the wall clock, with the frame "
                     "before each" % (len(clock["long_gaps"]), MAX_GAP_S))
    if clock is not None and clock["breaks"]:
        notes.append("the server log copy breaks %d times inside the window (lines lost in its rotation, or its "
                     "clock stepping back): no time across a break is counted, and the frame before one that cut a "
                     "stretch of play is left out of `running`" % clock["breaks"])
    script = script_by_file(script_rows, origin, tasks["days"], since, top)
    if script["counts_fell"]:
        notes.append("%d script entries count fewer calls in %s than in %s: the profile was restarted between them, "
                     "so the script difference means nothing" % (script["counts_fell"], last, first))
    return {
        "window": {"from": first or "profile start", "to": last, "start_date": start_step.get("date"),
                   "first_frame": frame_text(window[0]), "last_frame": frame_text(window[1]),
                   "days": tasks["days"]},
        "weekly_phase": {"phase": phase, "source": phase_source},
        "wall_clock": clock, "tick_tasks": tasks, "script": script, "notes": notes,
    }


def _read(path: Path, parse):
    try:
        return parse(Path(path).read_text(encoding="utf-8", errors="replace"))
    except FileNotFoundError:
        raise ProfileError("no_dump", "%s is not there" % path) from None
    except OSError as e:
        raise ProfileError("unreadable", "%s: %s" % (path, e)) from None


# ---- copying a dump the moment it is written

Signature = tuple[int, int] | None


def signature(path: Path) -> Signature:
    """(size, mtime_ns) as the file's own drive stamps it, or None when there is no regular file. Only ever
    compared with another signature of the same file, never with a clock."""
    try:
        st = os.stat(path)
    except (FileNotFoundError, NotADirectoryError):
        return None
    return (st.st_size, st.st_mtime_ns) if os.path.isfile(path) else None


def await_written(path: Path, before: Signature, sleep: Callable[[float], None], clock: Callable[[], float],
                  wait_s: float = DUMP_WAIT_S, settle_s: float = SETTLE_S) -> tuple[int, int]:
    """Wait until `path` is a file whose signature is not `before` (what was there before the dump, or None), and
    has held still across two looks `settle_s` apart; return that signature. ProfileError `not_written` when that
    has not happened within `wait_s`: the game did not write the file, or is still writing it."""
    deadline = clock() + wait_s
    seen: Signature = None
    while True:
        now = signature(path)
        if now is not None and now != before:
            if now == seen:
                return now
            seen = now
        else:
            seen = None
        if clock() >= deadline:
            raise ProfileError("not_written", "%s was not newly written within %g s of the dump (before: %s, now: %s)"
                               % (path, wait_s, before, now))
        sleep(settle_s)


def copy_written(source: Path, target: Path, written: tuple[int, int]) -> int:
    """Copy `source`, whose signature `await_written` returned, to `target` (which must not exist), through a
    `.part` name; return the bytes. ProfileError `changed` when the source is not as it was before or after the
    copy, or the bytes read are not its size: then nothing is left at `target`."""
    target = Path(target)
    if os.path.lexists(target):
        raise ProfileError("label_used", "%s is there already" % target)
    part = target.with_name(target.name + ".part")
    try:
        if signature(source) != written:
            raise ProfileError("changed", "%s changed before it could be copied" % source)
        with open(source, "rb") as reader, open(part, "wb") as writer:
            size = 0
            while chunk := reader.read(1 << 20):
                writer.write(chunk)
                size += len(chunk)
            writer.flush()
            os.fsync(writer.fileno())
        if signature(source) != written or size != written[0]:
            raise ProfileError("changed", "%s changed while it was copied" % source)
        os.replace(part, target)
        return size
    finally:
        try:
            os.unlink(part)
        except FileNotFoundError:
            pass


def _round(value: float, places: int = 1) -> float:
    return round(value, places)
