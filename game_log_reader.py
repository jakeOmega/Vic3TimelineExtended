"""Vic3 game-log reader: parsing, classification, dedup, mod-only filtering.

All log files live under `path_constants.game_logs_path`. Filenames follow
two conventions:

  <family>.log         → current run
  <family>.<n>.log     → rotated backups (n=1 newest, higher = older)
  <family>-<sess>.log  → multi-player session backups (excluded by default)

Each log line typically looks like
  [HH:MM:SS][engine_file.ext:LINE]: message ...

Continuation lines (without the `[..][..]` prefix) extend the previous entry,
which is how stack traces / multi-line error messages appear.

The reader is consumed by mod_state_server's `/logs/*` endpoints. It caches
parsed results keyed on (path, mtime) so repeated requests don't re-parse.
"""
from __future__ import annotations

import fnmatch
import os
import pathlib
import re
from collections import defaultdict, OrderedDict
from datetime import datetime, timezone


# Source files belonging to other mods that flood the runtime logs. An entry
# whose only mod-file references are in this set is treated as third-party and
# dropped from error/debug log views by default. Override per-request with
# `?include_external=true` on /logs/<family>.
#
# Match is by basename (the last path segment). Add new entries when a third-
# party mod produces recognizable spam. Engine entries usually pair the script
# location (e.g. `statistics_effects.txt`) with the call-site (`sta_on_actions
# .txt`); both have to be in the set so the entry's full file list is a subset
# of the excluded names — otherwise the entry survives the filter.
EXTERNAL_MOD_SOURCE_FILES: frozenset[str] = frozenset({
    # Statistics mod — `change_local_variable [Division/modulo by zero]` spam.
    "statistics_effects.txt",
    "sta_on_actions.txt",
    # Headlines mod — `has_interest_marker_in_region` PostValidate failures,
    # `Invalid strategic region 'region_*'` lookups, and `has_technology_researched`
    # PostValidate failures (workshop id 3142463417).
    "headlines_on_actions.txt",
    "headlines_tech_on_actions.txt",
    # GDP Growth Rate Improved mod — Div/0 in `change_local_variable` (workshop
    # id 3255320685). Engine entries pair the script-effect file with the event
    # call-site (`events/gdp_events.txt`); both must be in this set.
    "GDPGR_scripted_effects.txt",
    "gdp_events.txt",
    # GDP-per-province (GDPPP) mod — GUI template/type collision warnings
    # (workshop id 3190466673). Each entry references a single GDPPP `.gui` file.
    "00_GDPPP_graph_tooltips.gui",
    "00_GDPPP_politics_panel_types.gui",
})


# ---------------------------------------------------------------------------
# Categorization (source-file → coarse error category)
# ---------------------------------------------------------------------------
SOURCE_CATEGORY_PREFIX: dict[str, str] = {
    "gamedatabase.h:378": "duplicated_key",
    "gamedatabase.h:395": "inject_to_missing",
    "pdx_persistent_reader.cpp:268": "script_parse_error",
    "jomini_trigger.cpp:721": "inconsistent_trigger_scope",
    "jomini_effect.cpp:752": "inconsistent_effect_scope",
    "virtualfilesystem.cpp:569": "missing_file",
    "virtualfilesystem_physfs.cpp:": "vfs_mount",
    "guitexturehandler.h:155": "missing_texture_for_entity",
    "gfx_dds_loader.cpp:442": "dds_dimensions",
}
# Source file (without :line) → category. Used as a fallback when the exact
# `file:line` entry isn't in the more specific table above.
SOURCE_CATEGORY_FILE: dict[str, str] = {
    "pdx_gui_factory.cpp": "gui_parse_error",
    "pdx_gui_widget.cpp": "gui_widget_error",
    "pdx_persistent_reader.cpp": "script_parse_error",
    "gamedatabase.h": "gamedatabase_other",
    "jomini_trigger.cpp": "inconsistent_trigger_scope",
    "jomini_effect.cpp": "inconsistent_effect_scope",
    "virtualfilesystem.cpp": "missing_file",
    "guitexturehandler.h": "missing_texture_for_entity",
    "gfx_dds_loader.cpp": "dds_dimensions",
    "ai_strategy.cpp": "ai",
    "localization_database.cpp": "localization",
}

PARSED_FAMILIES = frozenset({
    "error", "debug", "game", "gui", "graphics", "event_scopes", "dedicated_server",
})

# Substring matched against a log line to decide whether it references something
# inside the active mod. We extract the first path that looks like a mod-tree
# relative path (common/ events/ gui/ localization/ gfx/ map_data/) and treat
# any line that hits this regex as mod-relevant.
_MOD_PATH_RE = re.compile(
    r"(?:(?:\b|/)(?:common|events|gui|localization|gfx|map_data)/[A-Za-z0-9_./-]+\.(?:txt|gui|yml|yaml|dds|asset|info))"
)
_LINE_RE = re.compile(r"^\[(?P<time>\d\d:\d\d:\d\d)\]\[(?P<source>[^\]]+)\]:\s*(?P<message>.*)$")


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------
class LogEntry:
    __slots__ = ("time", "source", "source_file", "message", "category", "files", "vanilla_bug_ref")

    def __init__(self, time: str, source: str, message: str):
        self.time = time
        self.source = source
        # Strip ":line" so callers can filter by source file alone
        if ":" in source:
            self.source_file = source.split(":", 1)[0]
        else:
            self.source_file = source
        self.message = message
        self.category = _classify(source, message)
        # All paths referenced inside the message body
        self.files = sorted(set(_MOD_PATH_RE.findall(message)))
        # Set later by tag_vanilla_bugs() if the entry matches a known vanilla bug
        # registered in docs/vanilla_known_bugs.md.
        self.vanilla_bug_ref: dict | None = None

    def to_dict(self, include_message: bool = True) -> dict:
        d = {
            "time": self.time,
            "source": self.source,
            "source_file": self.source_file,
            "category": self.category,
            "files": self.files,
        }
        if self.vanilla_bug_ref is not None:
            d["vanilla_bug_ref"] = self.vanilla_bug_ref
        if include_message:
            d["message"] = self.message
        return d


class LogFileInfo:
    __slots__ = ("family", "generation", "path", "mtime", "size", "line_count", "label")

    def __init__(self, family, generation, path, mtime, size, line_count, label):
        self.family = family
        self.generation = generation
        self.path = path
        self.mtime = mtime
        self.size = size
        self.line_count = line_count
        self.label = label

    def to_dict(self) -> dict:
        return {
            "family": self.family,
            "generation": self.generation,
            "path": self.path,
            "label": self.label,
            "mtime": (
                datetime.fromtimestamp(self.mtime, tz=timezone.utc).isoformat(timespec="seconds")
                if self.mtime else None
            ),
            "size_bytes": self.size,
            "line_count": self.line_count,
            "parsed": self.family in PARSED_FAMILIES,
        }


# ---------------------------------------------------------------------------
# Index: walk the logs dir and group rotated backups by family
# ---------------------------------------------------------------------------
_FAMILY_RE = re.compile(r"^(?P<family>[a-zA-Z_]+)(?:\.(?P<gen>\d+))?\.log$")


def list_logs(logs_dir: str, include_mp_sessions: bool = False) -> list[LogFileInfo]:
    out: list[LogFileInfo] = []
    if not logs_dir or not os.path.isdir(logs_dir):
        return out
    for fname in sorted(os.listdir(logs_dir)):
        if not fname.endswith(".log"):
            continue
        path = os.path.join(logs_dir, fname)
        try:
            stat = os.stat(path)
        except OSError:
            continue
        if stat.st_size == 0:
            continue
        m = _FAMILY_RE.match(fname)
        if not m:
            # Includes -Manfred / -pickle session-suffixed files.
            if not include_mp_sessions:
                continue
            family = fname[:-4]  # strip .log
            generation = None
        else:
            family = m.group("family")
            generation = int(m.group("gen") or "0")
        line_count = _quick_line_count(path)
        out.append(
            LogFileInfo(
                family=family,
                generation=generation if generation is not None else 0,
                path=path,
                mtime=stat.st_mtime,
                size=stat.st_size,
                line_count=line_count,
                label=fname,
            )
        )
    return out


def _quick_line_count(path: str) -> int:
    """Cheap line count via `wc -l`-style buffered read."""
    try:
        count = 0
        with open(path, "rb") as f:
            buf = bytearray(65536)
            view = memoryview(buf)
            while True:
                read = f.readinto(buf)
                if not read:
                    break
                count += view[:read].tobytes().count(b"\n")
        return count
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Parser (cached on (path, mtime))
# ---------------------------------------------------------------------------
_parse_cache: "OrderedDict[tuple[str, float], list[LogEntry]]" = OrderedDict()
_PARSE_CACHE_MAX = 16  # keep ~16 most-recently parsed logs in memory


def parse_log(path: str) -> list[LogEntry]:
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return []
    key = (path, mtime)
    cached = _parse_cache.get(key)
    if cached is not None:
        _parse_cache.move_to_end(key)
        return cached
    entries: list[LogEntry] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            current: LogEntry | None = None
            for line in f:
                line = line.rstrip("\n")
                m = _LINE_RE.match(line)
                if m:
                    if current is not None:
                        entries.append(current)
                    current = LogEntry(m.group("time"), m.group("source"), m.group("message"))
                elif current is not None:
                    # Continuation of the previous entry. Re-extract `files`
                    # so paths that only appear on continuation lines (e.g.
                    # `Script location: common/scripted_effects/foo.txt:NNN`
                    # in jomini_script_system errors) are visible to filters.
                    if line.strip():
                        current.message = current.message + "\n" + line
                        current.files = sorted(set(_MOD_PATH_RE.findall(current.message)))
                else:
                    # Header / non-prefixed lines (e.g. game.log perf headers)
                    # are kept as their own entries with no time/source.
                    entries.append(LogEntry("", "", line))
            if current is not None:
                entries.append(current)
    except OSError:
        return []
    _parse_cache[key] = entries
    while len(_parse_cache) > _PARSE_CACHE_MAX:
        _parse_cache.popitem(last=False)
    return entries


def _classify(source: str, message: str) -> str:
    cat = SOURCE_CATEGORY_PREFIX.get(source)
    if cat:
        return cat
    file_part = source.split(":", 1)[0]
    return SOURCE_CATEGORY_FILE.get(file_part, "other")


# ---------------------------------------------------------------------------
# Filtering / dedup / diff
# ---------------------------------------------------------------------------
def filter_mod_only(entries: list[LogEntry]) -> list[LogEntry]:
    return [e for e in entries if e.files]


def filter_external_mods(entries: list[LogEntry]) -> list[LogEntry]:
    """Drop entries whose only file references are known third-party-mod sources.

    An entry that *only* references files in EXTERNAL_MOD_SOURCE_FILES is dropped.
    An entry that mixes a third-party file with one of our own (rare cross-references)
    is kept. Empty-`files` entries are unaffected — `filter_mod_only` already governs
    those.
    """
    excluded = EXTERNAL_MOD_SOURCE_FILES
    out = []
    for e in entries:
        names = {pathlib.Path(p).name for p in e.files}
        if names and names.issubset(excluded):
            continue
        out.append(e)
    return out


# ---------------------------------------------------------------------------
# Vanilla-bug registry: parsed from docs/vanilla_known_bugs.md
# ---------------------------------------------------------------------------
# Heading lines look like:
#   ### `common/path/to/file.txt:5101` — short title
#   ### `common/path/to/file.txt:131, 142, 153, 517` — short title
#   ### `common/path/to/file.txt:25` and `common/other_file.txt:397-414` — title
# We extract every `path:lines` pair from the heading and the first line of the
# fenced code block (if any) as a message-substring signature. Matching is by
# file basename + signature substring (case-insensitive); line numbers are
# ignored because they shift between vanilla version bumps.
_HEADING_RE = re.compile(r"^###\s+(.*)$")
_SECTION_RE = re.compile(r"^##\s+(.*)$")
_PATH_REF_RE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:txt|gui|yml|yaml))(?::[0-9,\s\-]+)?`")
_TITLE_AFTER_DASH_RE = re.compile(r"\s[—-]\s+(.+)$")
# `- source: \`<token>\`` and `- tracked: \`<token>\`` body fields. Captured per-entry
# during the body walk. `source` extends the source-anchored index. `tracked` is the
# cross-reference to docs/open_issues.md (mandatory for mod_low_priority refs).
_SOURCE_REF_RE = re.compile(r"^\s*-\s*source:\s*`([^`]+)`\s*$")
_TRACKED_REF_RE = re.compile(r"^\s*-\s*tracked:\s*`([^`]+)`\s*$")

# Map ## section header substring (case-insensitive) -> kind label. Sections not
# matched default to "vanilla". A ref's kind drives validation policy and the
# `kind` field surfaced through to_dict().
_SECTION_KIND_RULES: tuple[tuple[str, str], ...] = (
    ("engine noise", "vanilla_noise"),
    ("mod-side", "mod_low_priority"),
    ("mod side", "mod_low_priority"),
)


class VanillaBugRef:
    __slots__ = ("title", "file_basenames", "source_anchors", "signatures", "anchor", "kind", "tracked_issue")

    def __init__(self, title: str, file_basenames: list[str], source_anchors: list[str],
                 signatures: list[str], anchor: str, kind: str = "vanilla",
                 tracked_issue: str | None = None):
        self.title = title
        self.file_basenames = file_basenames
        # Exact-match against entry.source. Empty for legacy path-anchored entries.
        self.source_anchors = source_anchors
        # Empty list = match purely on anchor (no signature filter).
        # A non-empty list matches if ANY signature substring appears in the message.
        self.signatures = signatures
        self.anchor = anchor
        # "vanilla" (default), "vanilla_noise" (engine cpp-source noise), or
        # "mod_low_priority" (mod-side cosmetic, must cross-link to open_issues.md).
        self.kind = kind
        self.tracked_issue = tracked_issue

    def to_dict(self) -> dict:
        d: dict = {
            "title": self.title,
            "section": self.anchor,
            "kind": self.kind,
        }
        if self.tracked_issue:
            d["tracked_issue"] = self.tracked_issue
        return d


def _section_kind(section_header: str) -> str:
    h = section_header.lower()
    for needle, kind in _SECTION_KIND_RULES:
        if needle in h:
            return kind
    return "vanilla"


def _open_issues_anchors(open_issues_path: str) -> set[str]:
    """Return the set of GitHub-style anchors for `### ` headings in open_issues.md.

    Used to verify `- tracked:` cross-references in the bug registry resolve. Best
    effort — returns empty set if the file is missing or unreadable.
    """
    try:
        with open(open_issues_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return set()
    anchors: set[str] = set()
    for ln in lines:
        m = _HEADING_RE.match(ln.rstrip("\n"))
        if not m:
            continue
        heading = m.group(1)
        slug = re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")
        if slug:
            anchors.add(slug)
    return anchors


def _validate_ref(ref: VanillaBugRef, known_open_issue_anchors: set[str]) -> list[str]:
    """Sanity-check a parsed ref. Returns a list of warning strings; empty = ok.

    Rules:
      1. Anchor-or-die: must have at least one of file_basenames or source_anchors.
         Eliminates accidental signature-only rules at parse time.
      2. mod_low_priority refs must specify a `- tracked:` cross-reference, and its
         #anchor fragment (if any) must resolve in docs/open_issues.md.
    """
    warnings: list[str] = []
    if not ref.file_basenames and not ref.source_anchors:
        warnings.append(
            f"vanilla_known_bugs.md: '{ref.title}' has no file path or source anchor — rejected "
            "(would match every log entry)"
        )
        return warnings
    if ref.kind == "mod_low_priority":
        if not ref.tracked_issue:
            warnings.append(
                f"vanilla_known_bugs.md: '{ref.title}' is in mod-side section but has no "
                "`- tracked: \\`docs/open_issues.md#anchor\\`` cross-reference"
            )
        elif "#" in ref.tracked_issue and known_open_issue_anchors:
            frag = ref.tracked_issue.split("#", 1)[1]
            if frag and frag not in known_open_issue_anchors:
                warnings.append(
                    f"vanilla_known_bugs.md: '{ref.title}' tracked-issue anchor "
                    f"'#{frag}' does not resolve in docs/open_issues.md"
                )
    return warnings


_vanilla_bug_cache: dict = {}  # {doc_path: (mtime, refs, by_basename, by_source, warnings)}


def load_vanilla_bug_registry(doc_path: str) -> tuple[
    list[VanillaBugRef],
    dict[str, list[VanillaBugRef]],
    dict[str, list[VanillaBugRef]],
    list[str],
]:
    """Parse `docs/vanilla_known_bugs.md` and return (refs, by_basename, by_source, warnings).

    Memoized on the doc's mtime so repeated requests don't re-parse.
    Returns ([], {}, {}, []) if the doc is missing or unreadable.
    """
    try:
        mtime = os.path.getmtime(doc_path)
    except OSError:
        return [], {}, {}, []
    cached = _vanilla_bug_cache.get(doc_path)
    if cached and cached[0] == mtime:
        return cached[1], cached[2], cached[3], cached[4]
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return [], {}, {}, []

    # Pre-load open_issues.md anchors for cross-reference validation. Same dir
    # convention as doc_path.
    open_issues_path = os.path.join(os.path.dirname(doc_path), "open_issues.md")
    known_anchors = _open_issues_anchors(open_issues_path)

    refs: list[VanillaBugRef] = []
    warnings: list[str] = []
    current_section_kind = "vanilla"
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        sm = _SECTION_RE.match(line)
        if sm:
            current_section_kind = _section_kind(sm.group(1))
            i += 1
            continue
        m = _HEADING_RE.match(line)
        if not m:
            i += 1
            continue
        heading = m.group(1)
        paths = _PATH_REF_RE.findall(heading)
        title_match = _TITLE_AFTER_DASH_RE.search(heading)
        title = title_match.group(1).strip() if title_match else heading.strip()
        # Anchor: GitHub-style — lowercase, replace non-alnum runs with `-`
        anchor_text = re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")
        anchor = f"docs/vanilla_known_bugs.md#{anchor_text}"
        # Walk the entry body up to the next `### ` or `## ` heading. Capture:
        #   - additional path references (so a heading can list one path and the
        #     body can enumerate sibling files affected by the same root cause)
        #   - `- source:` and `- tracked:` lines
        #   - the first fenced code block, ALL non-empty lines, as signatures
        #     (many bugs surface as 2-3 distinct error messages — tagging
        #     should hit any of them)
        signatures: list[str] = []
        body_paths: list[str] = []
        body_sources: list[str] = []
        tracked_issue: str | None = None
        captured_block = False
        j = i + 1
        while j < len(lines):
            nxt = lines[j].rstrip("\n")
            # Stop at the next entry (`### `) or section break (`## `).
            # Note: "### " does NOT startswith "## " — must check both.
            if nxt.startswith("### ") or nxt.startswith("## "):
                break
            if not captured_block and nxt.startswith("```"):
                k = j + 1
                while k < len(lines):
                    inner = lines[k].rstrip("\n")
                    if inner.startswith("```"):
                        break
                    if inner.strip():
                        signatures.append(inner.strip())
                    k += 1
                captured_block = True
                j = k + 1
                continue
            sr = _SOURCE_REF_RE.match(nxt)
            if sr:
                body_sources.append(sr.group(1))
                j += 1
                continue
            tr = _TRACKED_REF_RE.match(nxt)
            if tr:
                if tracked_issue is None:
                    tracked_issue = tr.group(1)
                # Multiple `- tracked:` lines: keep first, ignore rest (warn? not yet)
                j += 1
                continue
            body_paths.extend(_PATH_REF_RE.findall(nxt))
            j += 1
        all_paths = paths + body_paths
        basenames = sorted({pathlib.Path(p).name for p in all_paths})
        ref = VanillaBugRef(
            title=title,
            file_basenames=basenames,
            source_anchors=sorted(set(body_sources)),
            signatures=signatures,
            anchor=anchor,
            kind=current_section_kind,
            tracked_issue=tracked_issue,
        )
        ref_warnings = _validate_ref(ref, known_anchors)
        if ref_warnings:
            warnings.extend(ref_warnings)
            # Reject the ref if anchor-less (empty basenames AND empty sources).
            if not ref.file_basenames and not ref.source_anchors:
                i += 1
                continue
        refs.append(ref)
        i += 1
    by_basename: dict[str, list[VanillaBugRef]] = defaultdict(list)
    by_source: dict[str, list[VanillaBugRef]] = defaultdict(list)
    for r in refs:
        for bn in r.file_basenames:
            by_basename[bn].append(r)
        for src in r.source_anchors:
            by_source[src].append(r)
    by_basename_d, by_source_d = dict(by_basename), dict(by_source)
    _vanilla_bug_cache[doc_path] = (mtime, refs, by_basename_d, by_source_d, warnings)
    return refs, by_basename_d, by_source_d, warnings


_LINE_NUM_RE = re.compile(r":\d+")


def _normalize_for_signature_match(s: str) -> str:
    """Lowercase + collapse `:NNN` line references so version-shifted line numbers
    don't break the substring match."""
    return _LINE_NUM_RE.sub(":N", s.lower())


def tag_vanilla_bugs(
    entries: list[LogEntry],
    by_basename: dict[str, list[VanillaBugRef]],
    by_source: dict[str, list[VanillaBugRef]] | None = None,
) -> None:
    """Mutate entries: set `vanilla_bug_ref` on each that matches a registered vanilla bug.

    Two-stage match:
      1. Path-anchored (legacy) — file basename appears in entry.files.
      2. Source-anchored (fallback) — entry.source matches a `- source:` token from
         the registry. Used for engine-cpp-emit-point noise like
         `building_manager.cpp:1792` whose entries have no script-file path.

    Within each stage, the ref's signatures filter further: empty list = match
    purely on anchor; non-empty = ANY signature must appear (case-insensitive,
    normalized) in the message. Path-anchored wins over source-anchored when
    both are present, preserving legacy behavior.
    """
    if not by_basename and not by_source:
        return
    by_source = by_source or {}
    # Pre-normalize signatures once across both indexes.
    sig_cache: dict[int, list[str]] = {}
    for index in (by_basename, by_source):
        for refs in index.values():
            for ref in refs:
                if id(ref) not in sig_cache:
                    sig_cache[id(ref)] = [_normalize_for_signature_match(s) for s in ref.signatures]
    for e in entries:
        norm_msg = _normalize_for_signature_match(e.message)
        matched: VanillaBugRef | None = None
        # Stage 1: path-anchored
        if e.files:
            for f in e.files:
                base = pathlib.Path(f).name
                for ref in by_basename.get(base, ()):
                    sigs = sig_cache.get(id(ref), [])
                    if not sigs or any(s in norm_msg for s in sigs):
                        matched = ref
                        break
                if matched:
                    break
        # Stage 2: source-anchored (only if path-anchored didn't match)
        if matched is None and e.source and by_source:
            for ref in by_source.get(e.source, ()):
                sigs = sig_cache.get(id(ref), [])
                if not sigs or any(s in norm_msg for s in sigs):
                    matched = ref
                    break
        if matched:
            e.vanilla_bug_ref = matched.to_dict()


def filter_entries(
    entries: list[LogEntry],
    *,
    q: str | None = None,
    file_glob: str | None = None,
    source: str | None = None,
    category: str | None = None,
    since: str | None = None,
) -> list[LogEntry]:
    out = entries
    if q:
        ql = q.lower()
        out = [e for e in out if ql in e.message.lower()]
    if file_glob:
        out = [e for e in out if any(fnmatch.fnmatch(f, file_glob) for f in e.files)]
    if source:
        out = [e for e in out if source in e.source]
    if category:
        out = [e for e in out if e.category == category]
    if since:
        out = [e for e in out if e.time and e.time >= since]
    return out


def dedupe(
    entries: list[LogEntry],
    key: str = "message+file",
) -> list[dict]:
    """Collapse runs of identical lines. Returns a list of dicts with
    `first_seen`, `last_seen`, `repeated_times`, plus the entry data."""
    groups: "OrderedDict[tuple, list[LogEntry]]" = OrderedDict()
    for e in entries:
        if key == "exact":
            k = (e.time, e.source, e.message)
        elif key == "message":
            k = (e.message,)
        elif key == "message+file":
            # Normalize line numbers in messages so "near line: 32" != "near line: 64"
            normalized_msg = re.sub(r"\d+", "<n>", e.message)
            k = (e.category, normalized_msg, tuple(e.files))
        elif key == "category":
            k = (e.category,)
        else:
            k = (e.message,)
        groups.setdefault(k, []).append(e)
    out: list[dict] = []
    for group in groups.values():
        first = group[0]
        last = group[-1]
        rep = len(group)
        d = first.to_dict(include_message=True)
        d["first_seen"] = first.time
        d["last_seen"] = last.time
        d["repeated_times"] = rep
        out.append(d)
    return out


def summarize(entries: list[LogEntry]) -> dict:
    """Category histogram + top-N most-repeated messages, for ?summary=true."""
    cats: dict[str, int] = defaultdict(int)
    for e in entries:
        cats[e.category] += 1
    deduped = dedupe(entries, key="message+file")
    top_repeats = sorted(
        ({**d, "repeated_times": d["repeated_times"]} for d in deduped if d["repeated_times"] > 1),
        key=lambda d: -d["repeated_times"],
    )[:25]
    return {
        "total_entries": len(entries),
        "categories": dict(sorted(cats.items(), key=lambda kv: -kv[1])),
        "top_repeats": [
            {
                "category": d["category"],
                "source": d["source"],
                "message": d["message"][:200],
                "repeated_times": d["repeated_times"],
                "first_seen": d.get("first_seen"),
                "last_seen": d.get("last_seen"),
            }
            for d in top_repeats
        ],
    }


def diff_against_backup(current_entries: list[LogEntry], backup_entries: list[LogEntry]) -> dict:
    """Return entries new in `current` vs entries no longer present in `backup`.

    Comparison is on (category, normalized_message, files) so unrelated
    timestamps and line numbers don't trip the diff.
    """
    def _key(e: LogEntry):
        normalized_msg = re.sub(r"\d+", "<n>", e.message)
        return (e.category, normalized_msg, tuple(e.files))

    current_keys = {_key(e) for e in current_entries}
    backup_keys = {_key(e) for e in backup_entries}

    new_only = [e.to_dict() for e in current_entries if _key(e) not in backup_keys]
    gone = [e.to_dict() for e in backup_entries if _key(e) not in current_keys]
    # Dedup the "new" list so a single new error appearing 100x doesn't flood the diff.
    seen: set[tuple] = set()
    deduped_new: list[dict] = []
    for entry in new_only:
        k = (entry["category"], entry.get("message", ""), tuple(entry.get("files", [])))
        if k not in seen:
            seen.add(k)
            deduped_new.append(entry)
    return {
        "added": deduped_new,
        "removed_categories": _category_histogram(gone),
        "added_count_raw": len(new_only),
        "added_count_unique": len(deduped_new),
        "removed_count": len(gone),
    }


def _category_histogram(entries: list[dict]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for e in entries:
        out[e.get("category", "other")] += 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


# ---------------------------------------------------------------------------
# Sessions: cluster mtimes (within 5 min of each other) into runs.
# ---------------------------------------------------------------------------
def cluster_sessions(infos: list[LogFileInfo], window_seconds: float = 300.0) -> list[dict]:
    sorted_infos = sorted(infos, key=lambda i: i.mtime or 0.0, reverse=True)
    sessions: list[list[LogFileInfo]] = []
    for info in sorted_infos:
        if not info.mtime:
            continue
        if not sessions:
            sessions.append([info])
            continue
        last_mtime = sessions[-1][-1].mtime
        if abs(info.mtime - last_mtime) <= window_seconds:
            sessions[-1].append(info)
        else:
            sessions.append([info])
    out: list[dict] = []
    for s in sessions:
        latest = max(i.mtime for i in s)
        earliest = min(i.mtime for i in s)
        out.append({
            "started": datetime.fromtimestamp(earliest, tz=timezone.utc).isoformat(timespec="seconds"),
            "last_write": datetime.fromtimestamp(latest, tz=timezone.utc).isoformat(timespec="seconds"),
            "files": [i.label for i in s],
            "families": sorted({i.family for i in s}),
        })
    return out


# ---------------------------------------------------------------------------
# Markdown digest (called by /reload)
# ---------------------------------------------------------------------------
def render_error_log_digest(logs_dir: str, mod_path: str) -> str:
    """Produce docs/error_log_digest.md from the current error.log + diff vs error.1.log."""
    infos = list_logs(logs_dir)
    by_gen = {(i.family, i.generation): i for i in infos if i.family == "error"}
    current = by_gen.get(("error", 0))
    prev = by_gen.get(("error", 1))
    if current is None:
        return "# Error Log Digest\n\nNo current `error.log` found.\n"

    current_entries = parse_log(current.path)
    current_mod = filter_external_mods(filter_mod_only(current_entries))
    summary = summarize(current_mod)

    out: list[str] = []
    out.append("<!-- Auto-generated by mod_state_server. Do not hand-edit. -->")
    out.append("")
    out.append(f"# Error Log Digest — `{current.label}`")
    out.append("")
    if current.mtime:
        ts = datetime.fromtimestamp(current.mtime, tz=timezone.utc).isoformat(timespec="seconds")
        out.append(f"Source: `{current.path}` (mtime {ts})")
        out.append("")
    out.append(
        f"Total parsed lines: **{summary['total_entries']}** "
        f"(of which **{len(current_mod)}** reference mod files)."
    )
    out.append("")
    out.append("## Categories")
    out.append("")
    out.append("| Category | Count |")
    out.append("|---|---|")
    for cat, n in summary["categories"].items():
        out.append(f"| `{cat}` | {n} |")
    out.append("")
    if summary["top_repeats"]:
        out.append("## Most-repeated lines (top 25)")
        out.append("")
        for r in summary["top_repeats"]:
            out.append(
                f"- ×{r['repeated_times']} [{r['category']}] `{r['source']}` — "
                f"{r['message']}"
            )
        out.append("")
    if prev is not None:
        prev_entries = parse_log(prev.path)
        prev_mod = filter_external_mods(filter_mod_only(prev_entries))
        diff = diff_against_backup(current_mod, prev_mod)
        out.append(f"## Diff vs `{prev.label}`")
        out.append("")
        out.append(
            f"- Added (unique): **{diff['added_count_unique']}** "
            f"(raw count {diff['added_count_raw']})"
        )
        out.append(f"- Removed: **{diff['removed_count']}**")
        out.append("")
        if diff["added"]:
            out.append("### New since last launch")
            out.append("")
            for entry in diff["added"][:50]:
                out.append(
                    f"- [{entry.get('category', 'other')}] `{entry.get('source', '')}` — "
                    f"{(entry.get('message') or '')[:200]}"
                )
            if len(diff["added"]) > 50:
                out.append(f"- … and {len(diff['added']) - 50} more")
            out.append("")
    return "\n".join(out) + "\n"
