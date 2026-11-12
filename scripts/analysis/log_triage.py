#!/usr/bin/env python3
"""One-command log triage: snapshot the game's logs, then report what is new.

    python3 scripts/analysis/log_triage.py                 # snapshot + report
    python3 scripts/analysis/log_triage.py --out DIR       # ... into DIR
    python3 scripts/analysis/log_triage.py --snapshot DIR  # report on a snapshot
                                                           # taken earlier
    python3 scripts/analysis/log_triage.py --no-report     # snapshot only

It needs neither the mod state server nor a quiet game. The logs rotate (six
generations a family, 524 KB each), so a flood or a relaunch takes lines away
while you read; the snapshot is the first step so that nothing found later can
vanish, and so that a registry edit can be checked by running the report again
on the same files.

What the report holds, and the triage step each part replaces:

  Launches        which launch each line belongs to, the game dates it covered,
                  and where each family's surviving lines begin (a launch whose
                  start has rotated out has lost its load-time errors).
  Registry        the registries' own warnings, and cpp anchors a patch moved.
  Untagged        every line no registry entry explains, over every generation
                  of debug.log, error.log, game.log and gui.log, grouped by the
                  exact message: the findings. Each has its launch, game date,
                  burst shape, whether a stack frame is a mod file, and for a
                  line with no frame what else was logged in the same seconds.
                  A `MOD GUI:` line marks a GUI data-context failure that a
                  source-only vanilla entry matches and the mod's own GUI
                  reaches, with the files that draw the key or read the type.
  Watch list      lines an entry tags and leaves visible, with its check.
  Hidden, mod     lines a vanilla entry hides although a mod file is in the
                  stack: a hidden mod error, or an entry needing review.
  Volume          what fills the logs, hidden or not.
  Self-checks     every TE_SELF_CHECK by name and verdict, a START that got no
                  verdict, a probe line the engine dropped, and the play-test
                  list that waits for each.
  Crashes         crash folders since the oldest launch in the logs.

The same registries tag the lines as /logs does (game_log_reader), so
`?vanilla_bugs=hide&mod_noise=hide&mod_only=unknown&debug_log=hide` on the
server and this report agree on the current generation. The procedure around
it is the log-triage skill.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

import game_log_reader as glr  # noqa: E402

VANILLA_DOC = "docs/vanilla/vanilla_known_bugs.md"
MOD_NOISE_DOC = "docs/audits/mod_known_noise.md"
PLAYTEST_DIR = "docs/testing"
MANIFEST = "snapshot.json"

# The families worth copying, by exact name: the folder also holds other
# machines' `debug-<name>.log` files, which a `debug*.log` glob reads in.
ERROR_FAMILIES = ("debug", "error", "game", "gui")
CLOCK_FAMILIES = ("dedicated_server", "system", "custom_automated_stats")
LOG_NAME_RE = re.compile(
    r"(?P<family>" + "|".join(ERROR_FAMILIES + CLOCK_FAMILIES) + r")(?:\.(?P<gen>[1-9]))?\.log")

# game.log repeats error.log's script errors and adds these traces of its own.
GAME_LOG_TRACE_FILES = frozenset({"jomini_eventmanager.cpp", "journal_entry_manager.cpp"})
GAME_LOG_TRACE_SOURCES = frozenset({"diplomatic_action_type.cpp:105"})

START_DATE = "1836.1.1"
OCCASIONS_SHOWN = 3
TICK_RE = re.compile(r"Processing Tick: (\d+\.\d+\.\d+)")
PAUSE_RE = re.compile(r"Pause Toggled! Paused: (true|false)")
EXE_RE = re.compile(r"Exe Git Version: (\S+)")
INGAME_RE = re.compile(r"\[time-to-reach-ingame-idler\]:\[([0-9.]+)\]")
# debug.log's startup names each mod of the playset once it has matched its
# version against the game's (`dlc.cpp`): the launch's mod list.
PLAYSET_MOD_RE = re.compile(r"^Mod (.+?) \([^)]*\) version ")
# How soon after the exe starts a family's first line comes when nothing has
# rotated away (game.log's first lines wait for the events to load).
FIRST_LINE_WITHIN = {"debug": 5, "error": 5, "game": 60}
SELF_CHECK_RE = re.compile(r"TE_SELF_CHECK (\w+) (\w+)")
TRACE_RE = re.compile(r"\.(?:txt|gui):\d+: (TE_[A-Z_]+)")
LOST_PROBE_RE = re.compile(r"loc string '(TE_\w+(?: \w+){0,2})")
LOCATION_RE = re.compile(r"((?:common|events|gui|localization|gfx|map_data)/[A-Za-z0-9_./-]+\.[a-z]+):(\d+)")


class Line:
    """One log entry with where and when it was logged."""
    __slots__ = ("family", "file", "when", "entry")

    def __init__(self, family, file, when, entry):
        self.family, self.file, self.when, self.entry = family, file, when, entry


# ------------------------------------------------------------------ snapshot
def snapshot(logs_dir: str, out_dir: str, now: dt.datetime | None = None) -> dict:
    """Copy every generation of the triage families from `logs_dir` to
    `out_dir`, mtimes kept (the report dates each line from them), and write
    the manifest. Returns the manifest."""
    now = now or dt.datetime.now()
    os.makedirs(out_dir, exist_ok=True)
    copied, unreadable, newest = [], [], 0.0
    for name in sorted(os.listdir(logs_dir)):
        if not LOG_NAME_RE.fullmatch(name):
            continue
        src = os.path.join(logs_dir, name)
        try:
            if os.path.getsize(src) == 0:
                continue
            shutil.copy2(src, os.path.join(out_dir, name))
        except OSError as exc:  # a OneDrive placeholder never downloaded
            unreadable.append(f"{name}: {exc.strerror or exc}")
            continue
        copied.append(name)
        newest = max(newest, os.path.getmtime(src))
    manifest = {
        "taken_at": now.isoformat(timespec="seconds"),
        "logs_dir": logs_dir,
        "files": copied,
        "unreadable": unreadable,
        # The game flushes gui.log when it quits; a log written within a
        # minute of the snapshot means it was probably still running.
        "game_running": bool(newest) and (now.timestamp() - newest) < 60,
        "crashes": list_crashes(os.path.join(os.path.dirname(os.path.normpath(logs_dir)), "crashes")),
    }
    with open(os.path.join(out_dir, MANIFEST), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    return manifest


def list_crashes(crashes_dir: str) -> list[dict]:
    """[{name, mtime, address}] for each crash folder, newest first. The
    address is the fault site; across launches only its low 16 bits compare."""
    out = []
    try:
        names = sorted(os.listdir(crashes_dir))
    except OSError:
        return out
    for name in names:
        folder = os.path.join(crashes_dir, name)
        if not os.path.isdir(folder):
            continue
        address = None
        try:
            with open(os.path.join(folder, "exception.txt"), encoding="utf-8", errors="replace") as fh:
                m = re.search(r"at address (0x[0-9A-Fa-f]+)", fh.read())
                address = m.group(1) if m else None
        except OSError:
            pass
        out.append({"name": name, "mtime": os.path.getmtime(folder), "address": address})
    return sorted(out, key=lambda c: -c["mtime"])


# ------------------------------------------------------------------- reading
def stamp(entries: list, mtime: float) -> list:
    """A datetime for each entry of one file. The log prints only a time of
    day, so dates are worked back from the file's mtime, which is when its
    last line was written; a time that jumps forward on the way back is a
    midnight."""
    out = [None] * len(entries)
    written = dt.datetime.fromtimestamp(mtime)
    day, later = written.date(), None
    for i in range(len(entries) - 1, -1, -1):
        t = entries[i].time
        if not t:
            continue
        tod = dt.time.fromisoformat(t)
        when = dt.datetime.combine(day, tod)
        if later is None:
            if when > written + dt.timedelta(minutes=10):
                day -= dt.timedelta(days=1)
        elif when > later + dt.timedelta(hours=12):
            day -= dt.timedelta(days=1)
        when = dt.datetime.combine(day, tod)
        out[i] = later = when
    last = None
    for i, when in enumerate(out):  # an untimed line takes the time before it
        if when is None:
            out[i] = last
        else:
            last = when
    return out


def read_snapshot(snap_dir: str) -> dict:
    """{family: [Line]} in the order logged, oldest generation first."""
    families: dict[str, list[Line]] = collections.defaultdict(list)
    names = [n for n in os.listdir(snap_dir) if LOG_NAME_RE.fullmatch(n)]

    def age(name):
        m = LOG_NAME_RE.fullmatch(name)
        return (m.group("family"), -int(m.group("gen") or 0))

    for name in sorted(names, key=age):
        path = os.path.join(snap_dir, name)
        family = LOG_NAME_RE.fullmatch(name).group("family")
        entries = glr.parse_log(path)
        for e in entries:
            e.vanilla_bug_ref = None  # parse_log caches; tag afresh each run
        for entry, when in zip(entries, stamp(entries, os.path.getmtime(path))):
            families[family].append(Line(family, name, when, entry))
    return families


class Registries:
    """Both known-noise registries, the GUI-injected scope names and what the
    mod's own GUI reaches, loaded from `docs_root` (a checkout), tagging as
    /logs tags. `vanilla_game` is the install's `game` folder: without it no
    mod `.gui` file can be told from an override of vanilla's, so the mod GUI
    untagging is limited to the mod's own loc keys and `warnings` says so."""

    def __init__(self, docs_root: str, mod_root: str, vanilla_game: str | None = None):
        self.mod_root = mod_root
        self.refs, self.vb, self.vs, w1 = glr.load_vanilla_bug_registry(os.path.join(docs_root, VANILLA_DOC))
        mod_refs, self.mb, self.ms, w2 = glr.load_mod_noise_registry(os.path.join(docs_root, MOD_NOISE_DOC))
        self.refs = list(self.refs) + list(mod_refs)
        self.warnings = list(w1) + list(w2)
        self.gui_scopes = glr.gui_injected_scope_names(
            [os.path.join(mod_root, "gui"), os.path.join(mod_root, "localization", "english")])
        self.mod_gui = glr.mod_gui_references(mod_root, glr.vanilla_gui_file_names(
            os.path.dirname(os.path.normpath(vanilla_game)) if vanilla_game else None))
        self.warnings += self.mod_gui.warnings
        self.by_title = {r.title: r for r in self.refs}

    def tag(self, entries: list) -> None:
        glr.tag_vanilla_bugs(entries, self.vb, self.vs, mod_root=self.mod_root)
        glr.tag_vanilla_bugs(entries, self.mb, self.ms, mod_root=self.mod_root)
        glr.tag_gui_injected_scopes(entries, self.gui_scopes)
        glr.untag_mod_gui_fetches(entries, self.mod_gui, (self.vs, self.ms), mod_root=self.mod_root)


# ------------------------------------------------------------------ launches
class Clock:
    """Wall-clock time to launch, game date and pause state."""

    def __init__(self, families: dict):
        self.launches: list[dict] = []
        for line in families.get("system", []):
            m = EXE_RE.search(line.entry.message)
            if m and line.when:
                self.launches.append({"start": line.when, "exe": m.group(1)})
        self.launches.sort(key=lambda l: l["start"])
        self.starts = [l["start"] for l in self.launches]
        self.ticks: list[tuple] = []   # (when, "Y.M.D")
        self.pauses: list[tuple] = []  # (when, paused)
        for line in families.get("dedicated_server", []):
            if not line.when:
                continue
            m = TICK_RE.search(line.entry.message)
            if m:
                self.ticks.append((line.when, m.group(1)))
                continue
            m = PAUSE_RE.search(line.entry.message)
            if m:
                self.pauses.append((line.when, m.group(1) == "true"))
        self.tick_times = [t[0] for t in self.ticks]
        self.pause_times = [p[0] for p in self.pauses]
        for line in families.get("custom_automated_stats", []):
            m = INGAME_RE.search(line.entry.message)
            launch = self.launch_of(line.when)
            if m and launch is not None:
                self.launches[launch]["in_game"] = line.when

    def launch_of(self, when) -> int | None:
        """Index into `launches`, or None for a line older than every launch
        whose start is known."""
        if when is None or not self.starts:
            return None
        i = bisect.bisect_right(self.starts, when) - 1
        return i if i >= 0 else None

    def game_date(self, when) -> str | None:
        """The last tick at or before `when`, within the same launch."""
        if when is None or not self.ticks:
            return None
        i = bisect.bisect_right(self.tick_times, when) - 1
        if i < 0 or self.launch_of(self.tick_times[i]) != self.launch_of(when):
            return None
        return self.ticks[i][1]

    def paused(self, when) -> bool | None:
        """Whether the game was paused at `when`; None when no pause toggle
        of that launch precedes it."""
        if when is None or not self.pauses:
            return None
        i = bisect.bisect_right(self.pause_times, when) - 1
        if i < 0 or self.launch_of(self.pause_times[i]) != self.launch_of(when):
            return None
        return self.pauses[i][1]


def commits_since(when: dt.datetime, ref: str | None) -> int | None:
    if not ref:
        return None
    try:
        out = subprocess.run(
            ["git", "-C", REPO_ROOT, "rev-list", "--count", f"--since={when.isoformat()}", ref],
            capture_output=True, text=True, timeout=20, check=True).stdout
        return int(out.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def launch_rows(families: dict, clock: Clock, git_ref: str | None) -> list[str]:
    rows = []
    if not clock.launches:
        return ["  no system.log in the snapshot, so launches are not told apart"]
    for i, launch in enumerate(clock.launches):
        start = launch["start"]
        ticks = [d for when, d in clock.ticks if clock.launch_of(when) == i]
        if ticks:
            game = ("new game " if ticks[0] == START_DATE else "loaded a save, ") + f"{ticks[0]} to {ticks[-1]}"
        else:
            game = "no game dates kept (the ticks rotated out, or it never left the menu)"
        # debug.log names every mod; error.log only one whose version mismatches.
        mods = sorted({m.group(1) for line in families.get("debug", [])
                       if clock.launch_of(line.when) == i
                       for m in [PLAYSET_MOD_RE.search(line.entry.message)] if m})
        covers = []
        for family, within in FIRST_LINE_WITHIN.items():
            first = next((line.when for line in families.get(family, [])
                          if line.when and clock.launch_of(line.when) == i), None)
            if first is None:
                covers.append(f"{family}.log nothing")
            elif (first - start).total_seconds() <= within:
                covers.append(f"{family}.log whole")
            else:
                covers.append(f"{family}.log from {first:%H:%M:%S}")
        if not ticks and all(c.endswith(" nothing") for c in covers):
            rows.append(f"  #{i + 1} {start:%Y-%m-%d %H:%M:%S}  {launch['exe']}  nothing of it is left in the logs")
            continue
        behind = commits_since(start, git_ref)
        rows.append(f"  #{i + 1} {start:%Y-%m-%d %H:%M:%S}  {launch['exe']}  {game}"
                    + (f"  ({behind} commits on {git_ref} since)" if behind else ""))
        rows.append("     kept: " + ", ".join(covers) + "; playset: "
                    + (", ".join(mods) if mods else "rotated out (debug.log's first second names it)"))
    rows.append("  A family not kept whole has lost that launch's load-time errors: only a fresh "
                "launch shows them.")
    if any(commits_since(l["start"], git_ref) for l in clock.launches[-1:]):
        rows.append(f"  {git_ref} has moved since the last launch: check each finding's files "
                    "against it, and against open PRs, before fixing.")
    return rows


# ------------------------------------------------------------------ findings
def kernel(message: str) -> str:
    lines = [ln.strip() for ln in message.split("\n") if ln.strip()]
    return next((ln[7:] for ln in lines if ln.startswith("Error: ")), lines[0] if lines else "")


def split_location(message: str) -> tuple[str, str | None, str | None]:
    """(the message with its first script location's line number taken out,
    that location's path, its line). Two lines of one file with the same
    message then group together, and both line numbers are kept."""
    m = LOCATION_RE.search(message)
    if not m:
        return message, None, None
    return message[:m.start(2)] + "N" + message[m.end(2):], m.group(1), m.group(2)


def is_trace(line: Line) -> bool:
    e = line.entry
    return line.family == "game" and (
        e.source_file in GAME_LOG_TRACE_FILES or e.source in GAME_LOG_TRACE_SOURCES)


def error_lines(families: dict, registries: Registries) -> list[Line]:
    """The lines triage judges: every timed line of the error families that is
    not script `debug_log` output, a third-party mod's, or one of game.log's
    traces, each tagged. A game.log or gui.log line that error.log also holds
    is dropped (same second, source and message), so what stays of those two
    families is what error.log has rotated away or never had."""
    kept: list[Line] = []
    in_error = collections.Counter()
    for family in ERROR_FAMILIES:
        lines = families.get(family, [])
        registries.tag([line.entry for line in lines])
        for line in lines:
            e = line.entry
            if not e.time or e.category == "debug_log" or is_trace(line):
                continue
            names = {os.path.basename(p) for p in e.files}
            if names and names <= glr.EXTERNAL_MOD_SOURCE_FILES:
                continue
            key = (e.time, e.source, e.message)
            if family == "error":
                in_error[key] += 1
            elif family in ("game", "gui") and in_error[key] > 0:
                in_error[key] -= 1
                continue
            kept.append(line)
    return kept


def where_of(files: list, mod_root: str, vanilla_game: str | None) -> str:
    if not files:
        return "no file named"
    if any(os.path.isfile(os.path.join(mod_root, f.lstrip("/"))) for f in files):
        return "MOD FILE in the stack"
    if vanilla_game and os.path.isdir(vanilla_game):
        if any(os.path.isfile(os.path.join(vanilla_game, f.lstrip("/"))) for f in files):
            return "vanilla files only"
        return "in neither the mod nor vanilla (a third-party mod?)"
    return "no mod file in the stack"


class Finding:
    def __init__(self, source, text, path):
        self.source, self.text, self.path = source, text, path
        self.sites = collections.Counter()      # script line -> count
        self.per_family = collections.Counter()
        self.times: list = []
        self.files: list = []
        self.ref = None
        self.mod_gui = None  # the entry's mod_gui_context (glr.untag_mod_gui_fetches)

    def add(self, line: Line, site: str | None) -> None:
        self.per_family[line.family] += 1
        if site:
            self.sites[site] += 1
        if line.when:
            self.times.append(line.when)
        self.files = self.files or line.entry.files
        self.ref = self.ref or line.entry.vanilla_bug_ref
        self.mod_gui = self.mod_gui or line.entry.mod_gui_context

    @property
    def count(self) -> int:
        return sum(self.per_family.values())


def group(lines: list[Line]) -> list[Finding]:
    found: dict = {}
    for line in lines:
        text, path, site = split_location(line.entry.message)
        key = (line.entry.source, text)
        if key not in found:
            found[key] = Finding(line.entry.source, text, path)
        found[key].add(line, site)
    return list(found.values())


def occasions(times: list, gap: float = 60.0) -> list[list]:
    """`times` split wherever more than `gap` seconds pass without a line."""
    out: list[list] = []
    for t in sorted(times):
        if out and (t - out[-1][-1]).total_seconds() <= gap:
            out[-1].append(t)
        else:
            out.append([t])
    return out


def neighbours(finding: Finding, first: dt.datetime, lines_by_second: dict, limit: int = 4) -> list[str]:
    """For a line that names no file: what else was logged within a second
    of `first`, script traces first. A frameless assert is often explained by
    the script error or the trace line beside it."""
    first = first.replace(microsecond=0)
    seen, out = set(), []
    for offset in (0, -1, 1):
        for line in lines_by_second.get(first + dt.timedelta(seconds=offset), []):
            text = kernel(line.entry.message)
            if line.entry.source == finding.source and split_location(line.entry.message)[0] == finding.text:
                continue
            if text in seen:
                continue
            seen.add(text)
            trace = line.entry.category == "debug_log" and "TE_" in text
            out.append((0 if trace else 1 if line.entry.files else 2,
                        f"{line.when:%H:%M:%S} {line.file}: {text[:200]}"))
    return [text for _rank, text in sorted(out)[:limit]]


def mod_gui_note(context: dict) -> str:
    """Why a GUI data-context failure is listed although a vanilla entry
    matches it: the mod files that draw the key or read the data type."""
    files = ", ".join(context["files"])
    more = context["file_count"] - len(context["files"])
    files += f" and {more} more" if more > 0 else ""
    if "type" in context:
        what = f"data type '{context['type']}' is read by {files}"
    elif context["files"][0].endswith(".gui"):
        what = f"loc key '{context['key']}' is drawn by {files}"
    else:  # a key only the mod's loc defines, which no .gui names
        what = f"loc key '{context['key']}' is the mod's own ({files}); no .gui names it"
    return f"MOD GUI: {what}; otherwise hidden by '{context['untagged_from']}'"


def describe(finding: Finding, clock: Clock, mod_root: str, vanilla_game: str | None,
             lines_by_second: dict, full: bool) -> list[str]:
    times = sorted(finding.times)
    counts = ", ".join(f"{fam} {n}" for fam, n in sorted(finding.per_family.items()))
    head = f"{finding.count} lines ({counts}); {where_of(finding.files, mod_root, vanilla_game)}"
    when = ""
    if times:
        first, last = times[0], times[-1]
        launches = sorted({clock.launch_of(t) for t in times} - {None})
        when = ("launch " + ", ".join(f"#{n + 1}" for n in launches) + "; ") if launches else ""
        stamp_format = "%H:%M:%S" if first.date() == last.date() else "%m-%d %H:%M:%S"
        when += f"{first:{stamp_format}}"
        if last != first:
            when += f" to {last:{stamp_format}}"
        d0, d1 = clock.game_date(first), clock.game_date(last)
        if d0:
            when += f"; game date {d0}" + (f" to {d1}" if d1 and d1 != d0 else "")
        span = (last - first).total_seconds()
        if finding.count >= 20 and span <= 120:
            when += f"; a burst, {finding.count / max(span, 1):.0f} lines a second"
        paused = [clock.paused(t) for t in times]
        known = [p for p in paused if p is not None]
        if known and sum(known) * 2 > len(known):
            when += f"; {sum(known)} of {len(known)} while paused (a tooltip or panel, not the simulation)"
    out = [head, f"  {when}" if when else "", f"  [{finding.source}]"]
    body = finding.text.split("\n")
    out += ["  " + ln for ln in (body if full else body[:8])]
    if finding.mod_gui:
        out.append("  " + mod_gui_note(finding.mod_gui))
    if finding.sites:
        sites = ", ".join(f"{s}" + (f" x{n}" if n > 1 else "")
                          for s, n in sorted(finding.sites.items(), key=lambda kv: int(kv[0])))
        out.append(f"  lines of {finding.path}: {sites}")
    if not finding.files:
        each = occasions(times)
        for occasion in each[:OCCASIONS_SHOWN]:
            if len(each) > 1:
                date = clock.game_date(occasion[0])
                out.append(f"  occasion {occasion[0]:%m-%d %H:%M:%S}, {len(occasion)} lines"
                           + (f", game date {date}" if date else ""))
            out += [f"    near: {text}" for text in neighbours(finding, occasion[0], lines_by_second)]
        if len(each) > OCCASIONS_SHOWN:
            out.append(f"  and {len(each) - OCCASIONS_SHOWN} more occasions")
    return [ln for ln in out if ln]


# --------------------------------------------------------------- registry
def drift(lines: list[Line], registries: Registries) -> list[str]:
    """Untagged lines at a cpp line no entry names, whose message holds the
    signature of an entry anchored on another line of the same cpp file: the
    engine moved the line (a patch), so the entry needs the new anchor. A
    different message from the same file is not drift and is not listed."""
    by_file = collections.defaultdict(list)
    for ref in registries.refs:
        for anchor in ref.source_anchors:
            by_file[anchor.split(":")[0]].append((anchor, ref))
    registered = {anchor for refs in by_file.values() for anchor, _ in refs}
    hits = collections.Counter()
    for line in lines:
        e = line.entry
        if e.vanilla_bug_ref is not None or e.source in registered or e.source_file not in by_file:
            continue
        message = glr._normalize_for_signature_match(e.message)
        for anchor, ref in by_file[e.source_file]:
            if ref.signatures and any(
                    glr._normalize_for_signature_match(s) in message for s in ref.signatures):
                hits[(e.source, ref.title)] += 1
                break
    return [f"  DRIFT {source}: {n} lines carry the signature of '{title}'; add `- source: `{source}`` to it"
            for (source, title), n in sorted(hits.items())]


def hidden_with_mod_frame(lines: list[Line], registries: Registries) -> list[str]:
    has_mod_frame = glr.mod_frame_test(registries.mod_root)
    per = collections.defaultdict(collections.Counter)
    for line in lines:
        ref = line.entry.vanilla_bug_ref
        if ref is None or ref.get("kind") not in glr.VANILLA_KINDS:
            continue
        mod_files = [f for f in line.entry.files if has_mod_frame([f])]
        if mod_files:
            per[ref["title"]][(kernel(line.entry.message)[:140], ", ".join(mod_files[:3]))] += 1
    out = []
    for title, kernels in sorted(per.items(), key=lambda kv: -sum(kv[1].values())):
        ref = registries.by_title.get(title)
        cleared = [note for note in (ref.reviewed if ref is not None else [])
                   if note.lower().startswith((glr.MOD_FRAME_REVIEWED, glr.MOD_ANCHOR_REVIEWED))]
        if cleared:
            out.append(f"  {sum(kernels.values())} lines: {title} (reviewed: {cleared[0][:110]})")
            continue
        out.append(f"  {sum(kernels.values())} lines: {title}  <-- NOT REVIEWED")
        for (text, mods), n in kernels.most_common(3):
            out.append(f"      {n:5d} {text}")
            out.append(f"            via {mods}")
    return out


def volume(lines: list[Line], limit: int = 8) -> list[str]:
    per = collections.Counter()
    for line in lines:
        ref = line.entry.vanilla_bug_ref
        per[(ref["kind"], ref["title"]) if ref else ("untagged", kernel(line.entry.message)[:90])] += 1
    total = sum(per.values()) or 1
    return [f"  {n:6d} {100 * n / total:3.0f}%  [{kind}] {title[:110]}"
            for (kind, title), n in per.most_common(limit)]


# ------------------------------------------------------------ self-checks
def playtest_lists(docs_root: str) -> dict:
    """{file name: text} of the play-test lists."""
    out = {}
    folder = os.path.join(docs_root, PLAYTEST_DIR)
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return out
    for name in names:
        if name.endswith(".md"):
            try:
                with open(os.path.join(folder, name), encoding="utf-8") as fh:
                    out[name] = fh.read()
            except OSError:
                continue
    return out


def self_checks(families: dict, clock: Clock, docs_root: str) -> list[str]:
    checks: dict = collections.OrderedDict()
    traces = collections.Counter()
    for line in families.get("debug", []):
        e = line.entry
        if e.category != "debug_log":
            continue
        m = SELF_CHECK_RE.search(e.message)
        if m:
            key = (clock.launch_of(line.when), m.group(2))
            rec = checks.setdefault(key, {"status": collections.Counter(), "first": {}})
            rec["status"][m.group(1)] += 1
            rec["first"].setdefault(m.group(1), line)
            continue
        m = TRACE_RE.search(e.message)
        if m:
            traces[m.group(1)] += 1
    lists = playtest_lists(docs_root)
    out = []
    for (launch, name), rec in checks.items():
        status = rec["status"]
        verdict = ", ".join(f"{s} x{n}" if n > 1 else s for s, n in sorted(status.items()))
        flag = ""
        if status.get("BROKEN"):
            flag = "  <-- BROKEN"
        elif status.get("START") and not (status.get("OK") or status.get("BROKEN")):
            flag = "  <-- START with no verdict: a dead path until the save says otherwise"
        homes = [doc for doc, text in lists.items() if name in text]
        first = rec["first"].get("BROKEN") or rec["first"].get("OK") or next(iter(rec["first"].values()))
        out.append(f"  {name}: {verdict}{flag}")
        out.append(f"      {'launch #%d, ' % (launch + 1) if launch is not None else ''}"
                   f"{first.when:%H:%M:%S}"
                   + (f", game date {clock.game_date(first.when)}" if clock.game_date(first.when) else "")
                   + ("; listed in " + ", ".join(f"{PLAYTEST_DIR}/{h}" for h in homes) if homes
                      else "; in no play-test list"))
        text = first.entry.message
        out.append("      " + text[text.find("TE_SELF_CHECK"):][:400])
    lost = collections.Counter()
    for family in ERROR_FAMILIES:
        for line in families.get(family, []):
            m = LOST_PROBE_RE.search(line.entry.message)
            if m:
                lost[m.group(1)] += 1
    for name, n in sorted(lost.items()):
        out.append(f"  LOST {name}: {n} lines the engine could not render (a bad accessor in the "
                   "debug_log string); fix it and re-arm the check")
    if traces:
        out.append("  other trace lines: " + ", ".join(f"{k} {n}" for k, n in traces.most_common(12)))
    return out


# -------------------------------------------------------------------- report
def report(snap_dir: str, docs_root: str = REPO_ROOT, mod_root: str | None = None,
           vanilla_game: str | None = None, git_ref: str | None = "origin/main",
           full: bool = False) -> str:
    mod_root = mod_root or docs_root
    families = read_snapshot(snap_dir)
    registries = Registries(docs_root, mod_root, vanilla_game)
    clock = Clock(families)
    lines = error_lines(families, registries)
    manifest = {}
    try:
        with open(os.path.join(snap_dir, MANIFEST), encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError):
        pass

    out = [f"Log triage of {snap_dir}"
           + (f" (taken {manifest['taken_at']})" if manifest.get("taken_at") else "")]
    if manifest.get("game_running"):
        out.append("The game was still running: gui.log is written when it quits, so read it "
                   "again after, and the newest generation is still growing.")
    for name in manifest.get("unreadable", []):
        out.append(f"UNREADABLE {name} (a OneDrive placeholder? no hits there is not evidence)")

    out.append("\n== Launches")
    out += launch_rows(families, clock, git_ref)

    health = [f"  {w}" for w in registries.warnings] + drift(lines, registries)
    if health:
        out.append("\n== Registry")
        out += health

    lines_by_second = collections.defaultdict(list)
    for family in ERROR_FAMILIES:
        for line in families.get(family, []):
            if line.when and not is_trace(line):
                lines_by_second[line.when.replace(microsecond=0)].append(line)

    def kind_of(line):
        return (line.entry.vanilla_bug_ref or {}).get("kind")

    untagged = group([line for line in lines if kind_of(line) is None])
    rank = {"MOD FILE in the stack": 0, "no file named": 1}
    untagged.sort(key=lambda f: (rank.get(where_of(f.files, mod_root, vanilla_game), 2),
                                 min(f.times) if f.times else dt.datetime.max))
    out.append(f"\n== Untagged: {len(untagged)} messages, {sum(f.count for f in untagged)} lines")
    if not untagged:
        out.append("  none")
    for n, finding in enumerate(untagged, 1):
        text = describe(finding, clock, mod_root, vanilla_game, lines_by_second, full)
        out.append(f"[{n}] {text[0]}")
        out += text[1:]

    watched = group([line for line in lines if kind_of(line) == glr.WATCH_KIND])
    if watched:
        out.append(f"\n== Watch list: {len(watched)} messages left visible on purpose")
        for finding in watched:
            text = describe(finding, clock, mod_root, vanilla_game, lines_by_second, full)
            out.append(f"[w] {text[0]}")
            out += text[1:]
            out.append(f"  WATCH {finding.ref['title']}")
            out.append(f"  check: {finding.ref.get('check', '(none given)')}")

    hidden = hidden_with_mod_frame(lines, registries)
    if hidden:
        out.append("\n== Hidden by a vanilla entry, with a mod file in the stack")
        out += hidden
        if any("NOT REVIEWED" in ln for ln in hidden):
            out.append("  A mod frame under a vanilla entry is a hidden mod error until read: narrow the "
                       "entry (`- stack: vanilla only`, a tighter signature) or give it a "
                       "`- reviewed: mod frame, <why>` line.")

    out.append(f"\n== Volume: {len(lines)} lines judged; the largest classes")
    out += volume(lines)

    checks = self_checks(families, clock, docs_root)
    if checks:
        out.append("\n== Self-checks and traces")
        out += checks

    crashes = manifest.get("crashes", [])
    since = clock.starts[0].timestamp() if clock.starts else 0
    recent = [c for c in crashes if c["mtime"] >= since] if since else []
    out.append("\n== Crashes")
    if recent:
        for c in recent:
            out.append(f"  {dt.datetime.fromtimestamp(c['mtime']):%Y-%m-%d %H:%M} {c['name']} "
                       f"at {c['address'] or '?'} (compare the last four hex digits across dumps)")
    else:
        newest = f"; the newest is {crashes[0]['name']}" if crashes else ""
        out.append(f"  none since the oldest launch in the logs{newest}")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", metavar="DIR", help="report on this snapshot instead of taking one")
    ap.add_argument("--out", metavar="DIR", help="where the new snapshot goes (default: a new temp folder)")
    ap.add_argument("--logs", metavar="DIR", help="the game's logs folder (default: path_constants.game_logs_path)")
    ap.add_argument("--mod-root", help="the full mod checkout, for the mod-frame test "
                                       "(default: path_constants.mod_path)")
    ap.add_argument("--no-report", action="store_true", help="take the snapshot and stop")
    ap.add_argument("--full", action="store_true", help="print each message whole")
    ap.add_argument("--git-ref", default="origin/main",
                    help="count commits on this ref since each launch ('' to skip)")
    args = ap.parse_args(argv)

    import path_constants
    snap = args.snapshot
    if not snap:
        logs = args.logs or path_constants.game_logs_path
        if not logs or not os.path.isdir(logs):
            print(f"no logs folder at {logs!r}; pass --logs or --snapshot", file=sys.stderr)
            return 2
        snap = args.out or tempfile.mkdtemp(prefix=f"vic3te-logs-{dt.datetime.now():%Y%m%d-%H%M%S}-")
        manifest = snapshot(logs, snap)
        print(f"snapshot: {len(manifest['files'])} files -> {snap}", file=sys.stderr)
        if args.no_report:
            print(snap)
            return 0
    base = getattr(path_constants, "base_game_path", None)
    sys.stdout.write(report(
        snap, docs_root=REPO_ROOT, mod_root=args.mod_root or path_constants.mod_path,
        vanilla_game=os.path.join(base, "game") if base else None,
        git_ref=args.git_ref or None, full=args.full))
    return 0


if __name__ == "__main__":
    sys.exit(main())
