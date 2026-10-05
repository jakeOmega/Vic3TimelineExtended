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

import difflib
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
    # Skyscrapers Galore (workshop id 3741386673) — its city types under
    # gfx/map/city_data/city_types/ predate 1.14 and fail to parse ("Unexpected
    # token: building_land_logistics_center", 2026-10-05). Only the names vanilla
    # has no file of: its default_city.txt and default_port.txt override vanilla's.
    "african_modern_city.txt",
    "african_modern_port.txt",
    "american_city_modern.txt",
    "american_port_modern.txt",
    "arabic_modern_city.txt",
    "arabic_modern_port.txt",
    "asian_modern_city.txt",
    "asian_modern_port.txt",
    "default_modern_city.txt",
    "default_modern_port.txt",
    "japan_modern_city.txt",
    "japan_modern_port.txt",
    "latin_modern_city.txt",
    "latin_modern_port.txt",
    "southasian_modern_city.txt",
    "southasian_modern_port.txt",
})


# ---------------------------------------------------------------------------
# Categorization (source-file → coarse error category)
# ---------------------------------------------------------------------------
# Keys here are matched EXACTLY against an entry's `file:line` source. A rule
# that should cover every line of a file belongs in SOURCE_CATEGORY_FILE below —
# a `"<file>:"` key here never matches anything (that's how the physfs rule sat
# dead until #254).
SOURCE_CATEGORY_PREFIX: dict[str, str] = {
    "gamedatabase.h:378": "duplicated_key",
    "gamedatabase.h:395": "inject_to_missing",
    "pdx_persistent_reader.cpp:268": "script_parse_error",
    "jomini_trigger.cpp:721": "inconsistent_trigger_scope",
    "jomini_effect.cpp:752": "inconsistent_effect_scope",
    # The parse-time validator: `Variable 'X'` / `Event target 'X'` is used
    # but is never set. Without this it fell through to the file rule below
    # and read as a scope error.
    "jomini_effect.cpp:1139": "used_but_never_set",
    "virtualfilesystem.cpp:569": "missing_file",
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
    # Every line of the physfs VFS layer is a mount/filesystem complaint,
    # regardless of line number.
    "virtualfilesystem_physfs.cpp": "vfs_mount",
    "guitexturehandler.h": "missing_texture_for_entity",
    "gfx_dds_loader.cpp": "dds_dimensions",
    "ai_strategy.cpp": "ai",
    # Every line of this file is script's own `debug_log` output (`:454`,
    # `:453` before 1.14) or the scope dump `debug_log_scopes = yes` appends
    # (`:2501`): what a probe or a system's trace printed, not an engine error.
    # Checked against every retained log generation, 2026-09-27.
    "jomini_effect_impl.cpp": "debug_log",
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
        # registered in docs/vanilla/vanilla_known_bugs.md.
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


def filter_debug_log(entries: list[LogEntry], mode: str) -> list[LogEntry]:
    """Apply a `debug_log=show|hide|only` mode to entries.

    `hide` drops script `debug_log` output (category `debug_log`), `only` keeps
    nothing else, `show` (and any other value) leaves the list alone. Triage
    hides it: the mod's trace and probe lines (`TE_*:`) would otherwise
    outnumber the errors. Read them with `only`.
    """
    if mode == "hide":
        return [e for e in entries if e.category != "debug_log"]
    if mode == "only":
        return [e for e in entries if e.category == "debug_log"]
    return entries


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
# Vanilla-bug registry: parsed from docs/vanilla/vanilla_known_bugs.md
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
# cross-reference to docs/audits/open_issues.md (mandatory for mod_low_priority refs).
_SOURCE_REF_RE = re.compile(r"^\s*-\s*source:\s*`([^`]+)`\s*$")
_TRACKED_REF_RE = re.compile(r"^\s*-\s*tracked:\s*`([^`]+)`\s*$")
# `- reviewed: <note>` records a judgement a registry check would otherwise
# re-raise. Its text never joins the basename index, so a backticked path in
# the note doesn't add an anchor. `- reviewed: helper anchor, ...` clears
# helper_anchor_warnings for that entry.
_REVIEWED_REF_RE = re.compile(r"^\s*-\s*reviewed:\s*(.+?)\s*$")

# Map ## section header substring (case-insensitive) -> kind label. Sections not
# matched default to "vanilla". A ref's kind drives validation policy and the
# `kind` field surfaced through to_dict().
_SECTION_KIND_RULES: tuple[tuple[str, str], ...] = (
    ("engine noise", "vanilla_noise"),
    ("mod-side", "mod_low_priority"),
    ("mod side", "mod_low_priority"),
)


class VanillaBugRef:
    __slots__ = ("title", "file_basenames", "source_anchors", "signatures", "anchor", "kind",
                 "tracked_issue", "reviewed")

    def __init__(self, title: str, file_basenames: list[str], source_anchors: list[str],
                 signatures: list[str], anchor: str, kind: str = "vanilla",
                 tracked_issue: str | None = None, reviewed: list[str] | None = None):
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
        # `- reviewed:` notes from the entry body (see _REVIEWED_REF_RE).
        self.reviewed = list(reviewed or [])

    def to_dict(self) -> dict:
        d: dict = {
            "title": self.title,
            "section": self.anchor,
            "kind": self.kind,
        }
        if self.tracked_issue:
            d["tracked_issue"] = self.tracked_issue
        return d


def _section_kind(section_header: str) -> str | None:
    """Map a `##` section header to a kind label, or None if no rule matches.

    Returning None lets the parser preserve the current/default kind for sections
    that don't carry kind semantics (e.g. `## Entries`, `## Format` in
    docs/audits/mod_known_noise.md). Otherwise an unrecognized header would silently
    reset every subsequent ref back to the global default.
    """
    h = section_header.lower()
    for needle, kind in _SECTION_KIND_RULES:
        if needle in h:
            return kind
    return None


# Characters GitHub keeps in a heading anchor: word chars (so `_` survives),
# hyphen and space. Everything else — `.`, `:`, backticks, parens, `/`, em dashes —
# is DELETED, not collapsed to a dash; spaces then become dashes. That is why
# `L8. Mod tooltip.gui vertical scrollbar…` slugs to `l8-mod-tooltipgui-…`.
_SLUG_STRIP_RE = re.compile(r"[^\w\- ]")


def _github_slug(heading: str, seen: dict[str, int] | None = None) -> str:
    """Slug a markdown heading the way GitHub does.

    Rule: lowercase, remove every character that is not a word char, hyphen or
    space, then replace each space with `-`. No trimming and no run-collapsing —
    `Foo — Bar` really does anchor as `foo--bar`.

    Pass a shared `seen` dict (slug -> times emitted) to reproduce GitHub's
    duplicate-heading suffixes: the first `## Notes` is `#notes`, the second
    `#notes-1`, the third `#notes-2`.
    """
    slug = _SLUG_STRIP_RE.sub("", heading.lower()).replace(" ", "-")
    if seen is None:
        return slug
    n = seen.get(slug, 0)
    seen[slug] = n + 1
    return slug if n == 0 else f"{slug}-{n}"


def _open_issues_anchors(open_issues_path: str) -> set[str]:
    """Return the set of GitHub-style anchors for `### ` headings in open_issues.md.

    Used to verify `- tracked:` cross-references in the bug registry resolve. Best
    effort — returns empty set if the file is missing or unreadable. Duplicate
    headings get GitHub's `-N` suffix (counted over the `### ` headings scanned).
    """
    try:
        with open(open_issues_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return set()
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    for ln in lines:
        m = _HEADING_RE.match(ln.rstrip("\n"))
        if not m:
            continue
        slug = _github_slug(m.group(1), seen)
        if slug:
            anchors.add(slug)
    return anchors


def _validate_ref(ref: VanillaBugRef, known_open_issue_anchors: set[str]) -> list[str]:
    """Sanity-check a parsed ref. Returns a list of warning strings; empty = ok.

    Rules:
      1. Anchor-or-die: must have at least one of file_basenames or source_anchors.
         Eliminates accidental signature-only rules at parse time.
      2. mod_low_priority refs must specify a `- tracked:` cross-reference, and its
         #anchor fragment (if any) must resolve in docs/audits/open_issues.md.
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
                "`- tracked: \\`docs/audits/open_issues.md#anchor\\`` cross-reference"
            )
        elif "#" in ref.tracked_issue and known_open_issue_anchors:
            frag = ref.tracked_issue.split("#", 1)[1]
            if frag and frag not in known_open_issue_anchors:
                # Suggest the nearest real anchor(s), and spell out the slug rule
                # so the fix is copy-paste — GitHub anchors are the `### ` heading
                # lowercased with every non-word/hyphen/space character deleted
                # (`_` survives; `.`, `:` and backticks vanish) and spaces turned
                # into dashes.
                close = difflib.get_close_matches(
                    frag, sorted(known_open_issue_anchors), n=3, cutoff=0.5
                )
                suggestion = f" Did you mean: {', '.join('#' + c for c in close)}." if close else ""
                warnings.append(
                    f"vanilla_known_bugs.md: '{ref.title}' tracked-issue anchor "
                    f"'#{frag}' does not resolve in docs/audits/open_issues.md."
                    f"{suggestion} "
                    "Anchor rule (GitHub): heading.lower(), delete every char that is "
                    "not a word char/hyphen/space, then space -> '-'; repeats get a '-N' suffix."
                )
    return warnings


# {(doc_path, default_kind): ((doc_mtime, open_issues_mtime), refs, by_basename,
#                              by_source, warnings)}
_vanilla_bug_cache: dict = {}


def load_vanilla_bug_registry(
    doc_path: str,
    default_kind: str = "vanilla",
) -> tuple[
    list[VanillaBugRef],
    dict[str, list[VanillaBugRef]],
    dict[str, list[VanillaBugRef]],
    list[str],
]:
    """Parse a registry markdown file and return (refs, by_basename, by_source, warnings).

    `default_kind` is the kind assigned to entries that aren't inside a section
    header that overrides it. `docs/vanilla/vanilla_known_bugs.md` uses default_kind
    "vanilla" (engine-noise sections override to "vanilla_noise"); `docs/audits/mod_known_noise.md`
    passes default_kind="mod_low_priority" so entries there are flagged for the
    cross-reference-required validation.

    Memoized on (doc_path, default_kind) and invalidated by the mtime of BOTH this
    doc and docs/audits/open_issues.md — anchor resolution reads the latter inside
    the cached computation, so fixing a heading there must clear a stale
    "does not resolve" warning without anyone touching the registry file.
    Returns ([], {}, {}, []) if the doc is missing or unreadable.
    """
    try:
        mtime = os.path.getmtime(doc_path)
    except OSError:
        return [], {}, {}, []
    # open_issues.md lives in docs/audits/ regardless of which registry
    # (vanilla/ or audits/) is being parsed. Resolved before the cache probe so
    # its mtime can take part in the cache key.
    docs_root = os.path.dirname(os.path.dirname(doc_path))
    open_issues_path = os.path.join(docs_root, "audits", "open_issues.md")
    try:
        open_issues_mtime = os.path.getmtime(open_issues_path)
    except OSError:
        open_issues_mtime = None
    stamp = (mtime, open_issues_mtime)
    cache_key = (doc_path, default_kind)
    cached = _vanilla_bug_cache.get(cache_key)
    if cached and cached[0] == stamp:
        return cached[1], cached[2], cached[3], cached[4]
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return [], {}, {}, []

    # Pre-load open_issues.md anchors for cross-reference validation.
    known_anchors = _open_issues_anchors(open_issues_path)

    refs: list[VanillaBugRef] = []
    warnings: list[str] = []
    current_section_kind = default_kind
    # Shared across the whole document so repeated headings get GitHub's `-N` suffix.
    anchor_seen: dict[str, int] = {}
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        sm = _SECTION_RE.match(line)
        if sm:
            new_kind = _section_kind(sm.group(1))
            if new_kind is not None:
                current_section_kind = new_kind
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
        # Anchor: GitHub's heading-slug rule (see _github_slug).
        anchor_text = _github_slug(heading, anchor_seen)
        # Derive the docs/<subdir>/<file> prefix from the registry path so the
        # anchor reflects the actual source (vanilla/vanilla_known_bugs.md or
        # audits/mod_known_noise.md).
        anchor_doc_rel = "docs/" + os.path.basename(os.path.dirname(doc_path)) + "/" + os.path.basename(doc_path)
        anchor = f"{anchor_doc_rel}#{anchor_text}"
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
        reviewed: list[str] = []
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
            rv = _REVIEWED_REF_RE.match(nxt)
            if rv:
                reviewed.append(rv.group(1))
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
            reviewed=reviewed,
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
    _vanilla_bug_cache[cache_key] = (stamp, refs, by_basename_d, by_source_d, warnings)
    return refs, by_basename_d, by_source_d, warnings


def load_mod_noise_registry(doc_path: str) -> tuple[
    list[VanillaBugRef],
    dict[str, list[VanillaBugRef]],
    dict[str, list[VanillaBugRef]],
    list[str],
]:
    """Parse `docs/audits/mod_known_noise.md` — mod-side cosmetic entries filtered for
    triage cleanliness but tracked in `docs/audits/open_issues.md` so they remain actionable.

    Thin wrapper around `load_vanilla_bug_registry` with default_kind="mod_low_priority";
    every entry must have a `- tracked: \\`docs/audits/open_issues.md#anchor\\`` cross-reference
    that resolves to a real heading.
    """
    return load_vanilla_bug_registry(doc_path, default_kind="mod_low_priority")


# ---------------------------------------------------------------------------
# Helper-anchored registry entries (#730)
# ---------------------------------------------------------------------------
# error.log's `files` is the whole script call stack, so an entry anchored on a
# vanilla *helper* file (a scripted effect, scripted trigger or script value
# file) also tags the mod's errors that pass through that helper. The
# `change_appeasement` entry, anchored on vanilla's 00_lobby_effects.txt,
# hid five mis-signed mod event options that way (PR #729).
HELPER_ANCHOR_REVIEWED = "helper anchor"
HELPER_ANCHOR_ADVICE = (
    "anchor on the vanilla caller (bottom of the stack) or narrow the signature to "
    "the vanilla case; if it already cannot match a mod call, add "
    "`- reviewed: helper anchor, signature cannot match a mod call (<why>)`"
)
# Uses listed per helper in a warning; the count covers the rest.
_HELPER_USES_SHOWN = 5
_MOD_USE_DIRS = ("common", "events", "gui")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_BRACE_RE = re.compile(r"[{}]")

# {mod_root: (names, stamp, {name: ["rel:line", ...]})}, the latest query only.
_mod_uses_cache: dict = {}


def _mod_script_files(mod_root: str) -> list[tuple[str, str, float]]:
    out = []
    for sub in _MOD_USE_DIRS:
        base = os.path.join(mod_root, sub)
        for dirpath, dirs, names in os.walk(base):
            dirs.sort()
            for name in sorted(names):
                if name.endswith((".txt", ".gui")):
                    path = os.path.join(dirpath, name)
                    try:
                        out.append((path, os.path.relpath(path, mod_root).replace("\\", "/"),
                                    os.path.getmtime(path)))
                    except OSError:
                        continue
    return out


def mod_uses(mod_root: str, names: frozenset[str]) -> dict[str, list[str]]:
    """{name: ["<rel>:<line>", ...]} for every word-bounded mention of `names`
    in the mod's `common/`, `events/` and `gui/`, outside comments.

    A mention inside a string counts (a .gui reads a script value as
    `ScriptValue('x')`). A depth-0 key is a definition, not a use, so a mod
    file that redefines the name doesn't count itself. Memoized on the files'
    mtimes, like gui_injected_scope_names.
    """
    from script_helper_index import blank_comments, line_of, line_starts

    files = _mod_script_files(mod_root)
    stamp = tuple((rel, mtime) for _, rel, mtime in files)
    cached = _mod_uses_cache.get(mod_root)
    if cached and cached[0] == names and cached[1] == stamp:
        return cached[2]
    found: dict[str, list[str]] = defaultdict(list)
    for path, rel, _ in files:
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        # Cheap reject on the raw text: comments only add words, never hide one.
        if names.isdisjoint(_IDENT_RE.findall(text)):
            continue
        no_comments, clean = blank_comments(text)
        starts = line_starts(no_comments)
        braces = [(m.start(), 1 if m.group() == "{" else -1) for m in _BRACE_RE.finditer(clean)]
        bi = depth = 0
        for m in _IDENT_RE.finditer(no_comments):
            while bi < len(braces) and braces[bi][0] < m.start():
                depth = max(depth + braces[bi][1], 0)
                bi += 1
            name = m.group()
            if name not in names:
                continue
            if depth == 0 and re.match(r"\s*=", no_comments[m.end():m.end() + 8]):
                continue
            found[name].append(f"{rel}:{line_of(starts, m.start())}")
    result = dict(found)
    _mod_uses_cache[mod_root] = (names, stamp, result)
    return result


def helper_anchor_warnings(
    refs: list[VanillaBugRef],
    mod_root: str,
    vanilla_game: str | None,
    label: str = "vanilla_bug_registry",
) -> list[dict]:
    """Warn for each registry entry anchored on a vanilla helper file the mod
    calls into (#730).

    Each `file_basenames` entry is resolved to vanilla's `common/scripted_effects/`,
    `common/scripted_triggers/` and `common/script_values/` under `vanilla_game`
    (the mod's copy when the mod overrides that path, since vanilla's is then
    never loaded). When the mod mentions any of that file's top-level
    definitions, the entry can swallow mod errors and gets a warning:

        {"label", "kind": "helper_anchor_mod_calls", "entry", "anchor",
         "helper_file", "mod_uses": {definition: ["<rel>:<line>", ...]},
         "advice", "detail"}

    An entry carrying `- reviewed: helper anchor, ...` is skipped. Returns []
    without vanilla game files.
    """
    if not vanilla_game:
        return []
    from script_helper_index import DEFINITION_DIRS, definitions_in_file

    hits: list[tuple[VanillaBugRef, str, str, list[str]]] = []
    for ref in refs:
        if any(r.lower().startswith(HELPER_ANCHOR_REVIEWED) for r in ref.reviewed):
            continue
        for basename in ref.file_basenames:
            for kind in DEFINITION_DIRS:
                rel = f"common/{kind}/{basename}"
                vanilla_path = os.path.join(vanilla_game, rel)
                if not os.path.isfile(vanilla_path):
                    continue
                mod_copy = os.path.join(mod_root, rel)
                origin, path = ("mod", mod_copy) if os.path.isfile(mod_copy) else ("vanilla", vanilla_path)
                defs = definitions_in_file(path, rel, kind, origin)
                hits.append((ref, basename, rel, sorted({d.name for d in defs})))
    if not hits:
        return []
    uses = mod_uses(mod_root, frozenset(n for _, _, _, names in hits for n in names))
    warnings: list[dict] = []
    for ref, basename, rel, names in hits:
        used = {n: uses[n] for n in names if uses.get(n)}
        if not used:
            continue
        total = sum(len(v) for v in used.values())
        warnings.append({
            "label": label,
            "kind": "helper_anchor_mod_calls",
            "entry": ref.title,
            "anchor": basename,
            "helper_file": rel,
            "mod_uses": {n: v[:_HELPER_USES_SHOWN] for n, v in sorted(used.items())},
            "advice": HELPER_ANCHOR_ADVICE,
            "detail": (
                f"'{ref.title}' is anchored on vanilla helper file {rel}, and the mod "
                f"uses {len(used)} of its definitions ({', '.join(sorted(used))}; "
                f"{total} mention{'s' if total != 1 else ''}), so the entry also tags mod "
                f"errors whose call stack passes through it. {HELPER_ANCHOR_ADVICE}."
            ),
        })
    return warnings


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
        # Skip entries already tagged by an earlier registry pass — caller can
        # invoke this function twice (vanilla registry, then mod-noise registry)
        # without later passes overwriting earlier matches.
        if e.vanilla_bug_ref is not None:
            continue
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


# ---------------------------------------------------------------------------
# GUI-injected scopes (docs/audits/open_issues.md L14)
# ---------------------------------------------------------------------------
# The load-time validator (jomini_effect.cpp:1139) reports every event target
# that script reads and no script sets. A .gui (or a loc string) that sets one
# with AddScope('name', ...) for a script value to read as scope:name sets it
# where the validator does not look, so the name is reported at every launch:
# the market charts' base_market, the Strategic Reserve's sr_rival, the budget
# panel's ~420 rows (2026-10-05). Tagging from the files that set them keeps
# the match exact: a name nothing sets still surfaces.
_GUI_ADDSCOPE_RE = re.compile(r"AddScope\(\s*'([A-Za-z0-9_]+)'")
_NEVER_SET_EVENT_TARGET_RE = re.compile(r"^Event target '([A-Za-z0-9_]+)' is used but is never set")

GUI_INJECTED_SCOPE_REF = VanillaBugRef(
    title="GUI-injected scope flagged never-set (a mod .gui or loc string sets it with AddScope)",
    file_basenames=[],
    source_anchors=["jomini_effect.cpp:1139"],
    signatures=[],
    anchor="docs/audits/mod_known_noise.md#jomini_effectcpp1139--gui-injected-scopes-flagged-never-set",
    kind="mod_low_priority",
    tracked_issue="docs/audits/open_issues.md#l14-gui-injected-event-targets-flagged-never-set",
)

_gui_scope_cache: dict[tuple[str, ...], tuple[tuple, frozenset[str]]] = {}


def gui_injected_scope_names(roots: list[str]) -> frozenset[str]:
    """Every name passed to `AddScope('<name>', ...)` in `.gui` / `.yml` files under `roots`.

    Memoized on the roots and the files' mtimes, so a /logs request after an edit
    sees the new names without a server restart.
    """
    files: list[tuple[str, float]] = []
    for root in roots:
        for dirpath, _dirs, names in os.walk(root):
            for name in names:
                if name.endswith((".gui", ".yml")):
                    path = os.path.join(dirpath, name)
                    try:
                        files.append((path, os.path.getmtime(path)))
                    except OSError:
                        continue
    stamp = tuple(sorted(files))
    key = tuple(roots)
    cached = _gui_scope_cache.get(key)
    if cached and cached[0] == stamp:
        return cached[1]
    found: set[str] = set()
    for path, _ in files:
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                found.update(_GUI_ADDSCOPE_RE.findall(f.read()))
        except OSError:
            continue
    result = frozenset(found)
    _gui_scope_cache[key] = (stamp, result)
    return result


def tag_gui_injected_scopes(entries: list[LogEntry], names: frozenset[str]) -> None:
    """Tag `Event target 'X' is used but is never set` as L14 noise when a mod file sets X with AddScope.

    Skips entries an earlier registry pass already tagged, like tag_vanilla_bugs.
    """
    ref = GUI_INJECTED_SCOPE_REF.to_dict()
    for e in entries:
        if e.vanilla_bug_ref is not None:
            continue
        m = _NEVER_SET_EVENT_TARGET_RE.match(e.message)
        if m and m.group(1) in names:
            e.vanilla_bug_ref = dict(ref)


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
    """Produce docs/engine/error_log_digest.md from the current error.log + diff vs error.1.log."""
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
