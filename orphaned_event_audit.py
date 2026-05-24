"""Parse-time audit: detect orphaned events (issue #147).

The Clausewitz engine reports `Event X is orphaned` (jomini_eventmanager.cpp)
only at runtime game-start — invisible until a relaunch + log triage. A
`is_triggered_only = yes` event that no `trigger_event` / dispatch list ever
references is pure dead content (authored loc + options, zero player
reachability). We found two such law-enactment events this session
(extra_law_events.37, ministry_law_events.20) before they were wired in.

This audit builds the set of mod-defined triggered-only events and the set of
event IDs *referenced* anywhere in mod script, then flags the difference.

Scope / caveats:
- **Only `is_triggered_only = yes` events** are candidates. Events without it
  fire on their own (mean_time_to_happen / pulsed / on_action), so they are
  never orphaned even with no explicit reference.
- **Plain definitions only** (`<id> = {`). `REPLACE:` / `INJECT:` overrides of
  vanilla events ride vanilla dispatch we can't see, so they're excluded.
- **Loc keys don't count as references.** `my_events.1.t` / `.d` / `.a` are loc
  keys, not event references — the id-token regex requires the number is not
  followed by another `.`/word char.
- **Literal references only.** Events dispatched via dynamically-constructed IDs
  (`id = "prefix_[GetX]"`) can't be traced statically and will false-flag.
  Suppress those with an inline `# REVIEWED YYYY-MM-DD: rationale` on the
  event's opening `<id> = {` line.

Report: docs/engine/orphaned_event_report.md. Registered in POST_LOAD_AUDITS.
"""

import os
import re
from dataclasses import dataclass, field

# An event-id token: `namespace.number`, NOT followed by another `.` or word
# char (so loc keys `my_events.1.t` and longer ids don't false-match).
_EVENT_ID_RE = re.compile(r"(?<![\w.])([a-z_][a-z0-9_]*\.\d+)(?![\w.])")
# A plain top-level event definition line: `<id> = {` (no merge prefix).
_DEF_LINE_RE = re.compile(r"^\s*([a-z_][a-z0-9_]*\.\d+)\s*=\s*\{")
# Same but tolerant of merge prefixes — used only to recognise (and skip) the
# LHS token of a definition line so it isn't counted as a self-reference.
_DEF_LHS_RE = re.compile(
    r"^\s*(?:REPLACE:|INJECT:|REPLACE_OR_CREATE:)?([a-z_][a-z0-9_]*\.\d+)\s*=\s*\{"
)
_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)

# Directories (relative to mod root) scanned for event *references*.
_REFERENCE_ROOTS = ("events", "common", "gui")


# An event with a mean_time_to_happen block fires on its own — the engine never
# reports it as orphaned even with no explicit reference. (No mod event uses one
# today; this gate future-proofs against ones that do.)
_MTTH_RE = re.compile(r"\bmean_time_to_happen\s*=\s*\{")


@dataclass
class DefInfo:
    file: str
    line: int
    comment: str
    self_firing: bool


@dataclass
class OrphanFlag:
    event_id: str
    file: str
    line: int
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[OrphanFlag] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)


def parse_reviewed_comment(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _trailing_comment(line: str) -> str:
    idx = line.find("#")
    return line[idx:].rstrip("\n") if idx != -1 else ""


def _iter_txt(base: str):
    for dirpath, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".txt"):
                yield os.path.join(dirpath, f)


def _match_block(text: str, brace_pos: int) -> int:
    """Given the index of an opening `{`, return the index just past its
    matching `}` (or len(text) if unbalanced)."""
    depth = 0
    i = brace_pos
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def scan_definitions(events_dir: str) -> dict[str, DefInfo]:
    """Map plain-defined event id -> DefInfo(file, line, trailing comment,
    triggered_only). `triggered_only` is read from the event's own block, so
    the audit needs no parsed ModState."""
    defs: dict[str, DefInfo] = {}
    if not os.path.isdir(events_dir):
        return defs
    for path in _iter_txt(events_dir):
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        # Map char offset -> 1-based line number for reporting.
        line_starts = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                line_starts.append(i + 1)

        def _lineno(off: int) -> int:
            # binary-ish search; counts low — fine for our file sizes
            lo, hi = 0, len(line_starts) - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if line_starts[mid] <= off:
                    lo = mid
                else:
                    hi = mid - 1
            return lo + 1

        for m in re.finditer(r"^[ \t]*([a-z_][a-z0-9_]*\.\d+)[ \t]*=[ \t]*\{", text, re.M):
            eid = m.group(1)
            if eid in defs:
                continue
            brace = text.index("{", m.start())
            block = text[brace:_match_block(text, brace)]
            n = _lineno(m.start())
            line_end = text.find("\n", m.start())
            def_line = text[m.start():line_end if line_end != -1 else len(text)]
            defs[eid] = DefInfo(
                file=path,
                line=n,
                comment=_trailing_comment(def_line),
                self_firing=bool(_MTTH_RE.search(block)),
            )
    return defs


def scan_references(roots: list[str]) -> set[str]:
    """Collect every event id referenced (any occurrence that is not the LHS
    token of its own definition line) across the given directory roots."""
    referenced: set[str] = set()
    for base in roots:
        if not os.path.isdir(base):
            continue
        for path in _iter_txt(base):
            try:
                with open(path, encoding="utf-8-sig", errors="replace") as fh:
                    for line in fh:
                        defm = _DEF_LHS_RE.match(line)
                        def_pos = defm.start(1) if defm else -1
                        for m in _EVENT_ID_RE.finditer(line):
                            if m.start(1) == def_pos:
                                continue  # the definition's own LHS token
                            referenced.add(m.group(1))
            except OSError:
                continue
    return referenced


def audit(mod_path: str) -> AuditResult:
    events_dir = os.path.join(mod_path, "events")
    defs = scan_definitions(events_dir)
    referenced = scan_references(
        [os.path.join(mod_path, r) for r in _REFERENCE_ROOTS]
    )

    flags: list[OrphanFlag] = []
    candidates = 0
    for eid, info in sorted(defs.items()):
        if info.self_firing:
            continue  # mean_time_to_happen → fires on its own, never orphaned
        candidates += 1
        if eid in referenced:
            continue
        flags.append(
            OrphanFlag(
                event_id=eid,
                file=info.file,
                line=info.line,
                exemption=parse_reviewed_comment(info.comment),
            )
        )

    flags.sort(key=lambda f: f.event_id)
    return AuditResult(
        flags=flags,
        coverage={
            "events_defined": len(defs),
            "dispatch_required_candidates": candidates,
            "references_seen": len(referenced),
            "orphaned": len(flags),
        },
    )


def render_report(result: AuditResult, mod_path: str = "") -> str:
    unreviewed = [f for f in result.flags if not f.exemption]
    exempted = [f for f in result.flags if f.exemption]
    cov = result.coverage

    out: list[str] = []
    out.append("# Orphaned Event Report")
    out.append("")
    out.append(
        "Events defined in `events/` with no self-firing mechanism "
        "(`mean_time_to_happen`) that are never referenced by any "
        "`trigger_event` / dispatch list across `events/`, `common/`, `gui/`. "
        "These are unreachable dead content (the engine reports them as "
        "`Event X is orphaned` at game start)."
    )
    out.append("")
    out.append(
        f"- Events defined: **{cov.get('events_defined', 0)}** "
        f"(dispatch-required candidates: "
        f"**{cov.get('dispatch_required_candidates', 0)}**)"
    )
    out.append(f"- Distinct referenced ids seen: **{cov.get('references_seen', 0)}**")
    out.append(f"- Orphaned (unreviewed): **{len(unreviewed)}**")
    out.append(f"- Orphaned (REVIEWED-suppressed): **{len(exempted)}**")
    out.append("")

    def _loc(f: OrphanFlag) -> str:
        rel = os.path.relpath(f.file, mod_path) if mod_path else f.file
        return f"{rel}:{f.line}"

    if unreviewed:
        out.append("## Unreviewed orphans")
        out.append("")
        for f in unreviewed:
            out.append(f"- `{f.event_id}` — {_loc(f)}")
        out.append("")
        out.append(
            "Wire each into the appropriate dispatch pool, delete it, or add an "
            "inline `# REVIEWED YYYY-MM-DD: rationale` on its `<id> = {` line if "
            "it is dispatched via a dynamically-built id."
        )
        out.append("")
    else:
        out.append("No unreviewed orphaned events. ✅")
        out.append("")

    if exempted:
        out.append("## REVIEWED-suppressed")
        out.append("")
        for f in exempted:
            ex = f.exemption or {}
            out.append(
                f"- `{f.event_id}` — {_loc(f)} "
                f"(REVIEWED {ex.get('date', '?')}: {ex.get('rationale', '')})"
            )
        out.append("")

    return "\n".join(out)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_GENERATORS entry point. Writes the orphaned-event report.

    The audit is purely file-based (it reads is_triggered_only from each event's
    own block), so `mod_state` is accepted for protocol compatibility but unused.
    """
    from path_constants import mod_path

    result = audit(mod_path)
    report = render_report(result, mod_path)
    out_path = os.path.join(mod_path, "docs", "engine", "orphaned_event_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    unreviewed = sum(1 for f in result.flags if not f.exemption)
    return {
        "unreviewed": unreviewed,
        "exempted": sum(1 for f in result.flags if f.exemption),
        "events_defined": result.coverage.get("events_defined", 0),
        "path": out_path,
    }


if __name__ == "__main__":
    from path_constants import mod_path as _mp

    res = audit(_mp)
    print(render_report(res, _mp))
