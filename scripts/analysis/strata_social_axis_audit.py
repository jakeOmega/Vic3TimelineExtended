#!/usr/bin/env python3
"""Strata vs social-axis audit.

Flags events that model reactions to social-axis policies (civil rights,
women's rights, LGBTQ+ rights, religious tolerance, etc.) by giving one option
upper-strata radicals + lower-strata loyalists and the other option the
inverse. That shape bakes in "lower class = socially progressive, upper
class = socially conservative", which doesn't hold — social-issue stances
cut along IGs, ideologies, religions, and movements, not strata.

Two tiers of detection:

  Tier 1 (per-option, high precision): a single option = { ... } block that
    contains the mirrored upper/lower flip within itself —
    (add_radicals strata=upper + add_loyalists strata=lower) OR the inverse.

  Tier 2 (per-event): an event where one option leans "punish lower" and
    another leans "punish upper", without either option being a Tier-1
    within-option mirror. Catches the symmetric flip when it's split across
    options.

Exceptions live in docs/audits/strata_social_axis_exceptions.md as bullet
entries with the event id in backticks at the start of the line. Each entry
should carry two sentences of mechanical context explaining why the strata
reaction is the genuine economic content of the event (the doc doubles as
the "when is strata-targeted reaction actually correct?" reference).

Usage:
    python scripts/analysis/strata_social_axis_audit.py
    python scripts/analysis/strata_social_axis_audit.py --fail-on-flags
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from path_constants import mod_path  # noqa: E402


# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

# Event header (borrowed from event_magnitude_audit.py). Captures the bare
# event id, stripping REPLACE:/INJECT:/REPLACE_OR_CREATE: prefixes.
_EVENT_HEADER_RE = re.compile(
    r"^(?:REPLACE:|INJECT:|REPLACE_OR_CREATE:)?([A-Za-z_]\w*\.\w+)\s*=\s*\{"
)

# add_radicals / add_loyalists blocks. Match the full balanced { ... } body,
# then test its body for strata = upper / strata = lower. Multi-line bodies
# are common (value/strata/pop_type on separate lines), so DOTALL.
_RADLOY_BLOCK_RE = re.compile(
    r"(?P<kind>add_radicals|add_loyalists)\s*=\s*\{(?P<body>[^{}]*?)\}",
    re.DOTALL,
)
_STRATA_RE = re.compile(r"(?<!\w)strata\s*=\s*(?P<strata>\w+)")

# Exceptions doc: bullet entries with backtick-wrapped event id at the start.
# Tolerates leading whitespace and indentation.
_EXCEPTION_ENTRY_RE = re.compile(
    r"^\s*[-*]\s+`(?P<event>[A-Za-z_]\w*\.\w+)`"
)


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

@dataclass
class OptionShape:
    """Strata-related signals present in one option block."""
    has_upper_radicals: bool = False
    has_lower_loyalists: bool = False
    has_upper_loyalists: bool = False
    has_lower_radicals: bool = False
    line_no: int = 0          # line where the `option = {` opens
    option_name: str | None = None

    @property
    def is_within_option_mirror(self) -> bool:
        """True if the option contains the mirrored upper/lower flip within itself."""
        progressive_mirror = self.has_upper_radicals and self.has_lower_loyalists
        regressive_mirror = self.has_upper_loyalists and self.has_lower_radicals
        return progressive_mirror or regressive_mirror

    @property
    def mirror_shape(self) -> str | None:
        """Returns 'upper-rad+lower-loy' or 'upper-loy+lower-rad' for Tier-1 hits."""
        if self.has_upper_radicals and self.has_lower_loyalists:
            return "upper-radicals + lower-loyalists"
        if self.has_upper_loyalists and self.has_lower_radicals:
            return "upper-loyalists + lower-radicals"
        return None

    @property
    def lean(self) -> str | None:
        """One of 'punish-lower', 'punish-upper', None.

        Used for Tier-2 cross-option detection. An option that already qualifies
        as Tier-1 (within-option mirror) returns 'mirrored' so the caller can
        suppress Tier-2 listing for the event.
        """
        if self.is_within_option_mirror:
            return "mirrored"
        if self.has_upper_radicals or self.has_lower_loyalists:
            return "punish-lower"   # upper angers, lower stays loyal
        if self.has_upper_loyalists or self.has_lower_radicals:
            return "punish-upper"   # upper stays loyal, lower angers
        return None


@dataclass
class EventBlock:
    file: str
    event_id: str
    header_line: int
    options: list[OptionShape] = field(default_factory=list)


@dataclass
class Tier1Flag:
    file: str
    line: int
    event_id: str
    option_name: str | None
    shape: str            # "upper-radicals + lower-loyalists" etc.


@dataclass
class Tier2Flag:
    file: str
    line: int
    event_id: str
    option_summary: str   # short description of which options contributed


@dataclass
class AuditResult:
    tier1: list[Tier1Flag] = field(default_factory=list)
    tier2: list[Tier2Flag] = field(default_factory=list)
    exempted_tier1: list[Tier1Flag] = field(default_factory=list)
    exempted_tier2: list[Tier2Flag] = field(default_factory=list)
    files_audited: int = 0


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _strata_value(body: str) -> str | None:
    m = _STRATA_RE.search(body)
    return m.group("strata") if m else None


def _scan_option_body(body: str) -> OptionShape:
    """Build an OptionShape from the text inside an `option = { ... }` block."""
    shape = OptionShape()
    for m in _RADLOY_BLOCK_RE.finditer(body):
        kind = m.group("kind")
        strata = _strata_value(m.group("body"))
        if strata is None:
            continue
        if kind == "add_radicals":
            if strata == "upper":
                shape.has_upper_radicals = True
            elif strata == "lower":
                shape.has_lower_radicals = True
        elif kind == "add_loyalists":
            if strata == "upper":
                shape.has_upper_loyalists = True
            elif strata == "lower":
                shape.has_lower_loyalists = True
    return shape


def _scan_event_body(body: str, file: str, event_id: str, body_start_line: int) -> EventBlock:
    """Walk one event body, extracting OptionShape per `option = { ... }` block.

    Uses brace-depth tracking to find balanced option blocks (option bodies
    routinely contain nested add_modifier blocks, etc.). `body_start_line` is
    the 1-indexed line number of the `event_id = {` header; option line numbers
    are reported relative to the file.
    """
    event = EventBlock(file=file, event_id=event_id, header_line=body_start_line)
    i = 0
    lines_consumed = 0
    while i < len(body):
        # Find next `option = {` start.
        opt_match = re.search(r"(?<!\w)option\s*=\s*\{", body[i:])
        if not opt_match:
            break
        opt_start = i + opt_match.start()
        opt_body_start = i + opt_match.end()      # position just past the `{`
        opt_keyword_line = body_start_line + body.count("\n", 0, opt_start)

        # Walk forward to find the matching close brace.
        depth = 1
        j = opt_body_start
        while j < len(body) and depth > 0:
            ch = body[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            j += 1
        if depth != 0:
            # Unbalanced — bail on this event to avoid infinite loop.
            break
        opt_body = body[opt_body_start:j - 1]

        shape = _scan_option_body(opt_body)
        shape.line_no = opt_keyword_line
        shape.option_name = _extract_option_name(opt_body)
        event.options.append(shape)

        i = j

    return event


_OPTION_NAME_RE = re.compile(r"(?<!\w)name\s*=\s*(?P<name>\S+)")


def _extract_option_name(option_body: str) -> str | None:
    m = _OPTION_NAME_RE.search(option_body)
    if not m:
        return None
    return m.group("name").rstrip(",").rstrip("}")


def _strip_comments(text: str) -> str:
    """Replace `# ...` comments with spaces, preserving newlines for line counting.

    Comments inside Paradox event files can contain braces (e.g.
    `# this option = { is special }`), which would otherwise break brace-depth
    walking. We keep line counts stable by overwriting comment text with spaces
    instead of deleting it.
    """
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "#":
            # Skip until newline; keep newline so line counts don't shift.
            end = text.find("\n", i)
            if end == -1:
                out.append(" " * (len(text) - i))
                i = len(text)
            else:
                out.append(" " * (end - i))
                i = end
        elif ch == '"':
            # Preserve the quote; replace string contents (which may contain
            # braces) with spaces. No multi-line strings in Paradox script.
            out.append(ch)
            i += 1
            start = i
            while i < len(text) and text[i] != '"' and text[i] != "\n":
                i += 1
            out.append(" " * (i - start))
            if i < len(text) and text[i] == '"':
                out.append('"')
                i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _iter_events(text: str, file: str):
    """Yield EventBlock per top-level event in the file.

    Top-level: event header lines whose `{` is at the top of brace depth 0.
    """
    clean = _strip_comments(text)

    # Pre-pass: scan for top-level event headers and record (header_line, event_id, body_start_pos).
    # Then walk braces to find each body's end.
    lines = clean.splitlines(keepends=True)
    line_starts: list[int] = []
    pos = 0
    for ln in lines:
        line_starts.append(pos)
        pos += len(ln)

    headers: list[tuple[int, str, int]] = []  # (line_no_1idx, event_id, brace_open_pos)
    for line_idx, ln in enumerate(lines):
        stripped = ln.lstrip()
        if not stripped:
            continue
        m = _EVENT_HEADER_RE.match(stripped)
        if not m:
            continue
        brace_offset_in_line = ln.index("{")
        brace_open_pos = line_starts[line_idx] + brace_offset_in_line
        headers.append((line_idx + 1, m.group(1), brace_open_pos))

    # For each header, walk the brace-matched body. Track file-wide depth so
    # nested headers (which shouldn't exist at top level, but defensively)
    # are skipped.
    for header_line, event_id, brace_open_pos in headers:
        # Confirm this brace is at depth 0 by counting balanced braces before it.
        depth_before = 0
        for ch in clean[:brace_open_pos]:
            if ch == "{":
                depth_before += 1
            elif ch == "}":
                depth_before -= 1
        if depth_before != 0:
            continue   # nested; not a top-level event

        # Walk forward to find the matching close brace.
        depth = 1
        j = brace_open_pos + 1
        while j < len(clean) and depth > 0:
            ch = clean[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            j += 1
        if depth != 0:
            continue   # unbalanced; bail

        body = clean[brace_open_pos + 1 : j - 1]
        yield _scan_event_body(
            body, file=file, event_id=event_id,
            body_start_line=header_line,
        )


# ---------------------------------------------------------------------------
# Exceptions doc
# ---------------------------------------------------------------------------

def load_exceptions(repo_root: Path) -> set[str]:
    """Parse docs/audits/strata_social_axis_exceptions.md for exempted event ids."""
    doc_path = repo_root / "docs" / "audits" / "strata_social_axis_exceptions.md"
    if not doc_path.exists():
        return set()
    exempt: set[str] = set()
    for line in doc_path.read_text(encoding="utf-8").splitlines():
        m = _EXCEPTION_ENTRY_RE.match(line)
        if m:
            exempt.add(m.group("event"))
    return exempt


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def audit_text(text: str, file: str, exempted: set[str]) -> tuple[
    list[Tier1Flag], list[Tier2Flag], list[Tier1Flag], list[Tier2Flag]
]:
    """Audit one events/*.txt source. Returns (tier1, tier2, exempted_t1, exempted_t2)."""
    tier1: list[Tier1Flag] = []
    tier2: list[Tier2Flag] = []
    exempted_tier1: list[Tier1Flag] = []
    exempted_tier2: list[Tier2Flag] = []

    for event in _iter_events(text, file):
        event_tier1: list[Tier1Flag] = []

        for opt in event.options:
            if opt.is_within_option_mirror:
                flag = Tier1Flag(
                    file=event.file,
                    line=opt.line_no,
                    event_id=event.event_id,
                    option_name=opt.option_name,
                    shape=opt.mirror_shape or "",
                )
                event_tier1.append(flag)

        bucket = exempted_tier1 if event.event_id in exempted else tier1
        bucket.extend(event_tier1)

        # Tier 2 only if no Tier-1 hit already covers the event.
        if not event_tier1:
            leans = {opt.lean for opt in event.options if opt.lean}
            if "punish-lower" in leans and "punish-upper" in leans:
                contribs = ", ".join(
                    f"{opt.option_name or '?'}: {opt.lean}"
                    for opt in event.options if opt.lean
                )
                flag = Tier2Flag(
                    file=event.file,
                    line=event.header_line,
                    event_id=event.event_id,
                    option_summary=contribs,
                )
                if event.event_id in exempted:
                    exempted_tier2.append(flag)
                else:
                    tier2.append(flag)

    return tier1, tier2, exempted_tier1, exempted_tier2


def audit(repo_root: Path | None = None) -> AuditResult:
    """Walk events/*.txt under the configured mod_path."""
    repo_root = repo_root or Path(mod_path)
    events_dir = repo_root / "events"
    if not events_dir.is_dir():
        return AuditResult()

    exempted = load_exceptions(repo_root)
    result = AuditResult()

    for fpath in sorted(events_dir.glob("*.txt")):
        text = fpath.read_text(encoding="utf-8-sig")
        rel = str(fpath.relative_to(repo_root))
        t1, t2, ex1, ex2 = audit_text(text, file=rel, exempted=exempted)
        result.tier1.extend(t1)
        result.tier2.extend(t2)
        result.exempted_tier1.extend(ex1)
        result.exempted_tier2.extend(ex2)
        result.files_audited += 1

    return result


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

_FIX_HINT = (
    "Replace strata-targeted radicals/loyalists with IG-targeted approval "
    "shifts (`ig_approval_effect`), IG-ideology-gated reactions, and "
    "movement modifiers. For civil-rights / minority-rights events, "
    "consider `every_scope_pop { limit = { pop_acceptance < N } add_radicals = ... }`. "
    "If the reaction is genuinely economic-axis, add an entry to "
    "docs/audits/strata_social_axis_exceptions.md."
)


def render_report(result: AuditResult) -> str:
    out: list[str] = [
        "# Strata vs social-axis audit report",
        "",
        "Generated by `scripts/analysis/strata_social_axis_audit.py`. CLI-only —",
        "this audit is not wired into the `POST /reload` flow.",
        "",
        "Exemptions are read from `docs/audits/strata_social_axis_exceptions.md`",
        "(bullet entries with backtick-wrapped event id at the start of the line).",
        "",
        "**Fix hint:** " + _FIX_HINT,
        "",
    ]

    def _render_tier(title: str, t1: list[Tier1Flag], t2: list[Tier2Flag]) -> None:
        out.append(f"## {title}")
        out.append("")
        out.append(f"### Tier 1 — within-option mirrors ({len(t1)})")
        out.append("")
        if not t1:
            out.append("_None._")
            out.append("")
        else:
            by_file: dict[str, list[Tier1Flag]] = {}
            for f in t1:
                by_file.setdefault(f.file, []).append(f)
            for fpath in sorted(by_file):
                out.append(f"**`{fpath}`**")
                out.append("")
                for f in by_file[fpath]:
                    name = f.option_name or "?"
                    out.append(
                        f"- L{f.line} — `{f.event_id}` option `{name}` — {f.shape}"
                    )
                out.append("")

        out.append(f"### Tier 2 — cross-option flips ({len(t2)})")
        out.append("")
        if not t2:
            out.append("_None._")
            out.append("")
        else:
            by_file: dict[str, list[Tier2Flag]] = {}
            for f in t2:
                by_file.setdefault(f.file, []).append(f)
            for fpath in sorted(by_file):
                out.append(f"**`{fpath}`**")
                out.append("")
                for f in by_file[fpath]:
                    out.append(
                        f"- L{f.line} — `{f.event_id}` — {f.option_summary}"
                    )
                out.append("")

    _render_tier("Unexempted flags", result.tier1, result.tier2)
    _render_tier(
        "Exempted (from exceptions doc)",
        result.exempted_tier1,
        result.exempted_tier2,
    )

    out.append("## Coverage")
    out.append("")
    out.append(f"- files audited: {result.files_audited}")
    out.append(f"- tier 1 unexempted: {len(result.tier1)}")
    out.append(f"- tier 2 unexempted: {len(result.tier2)}")
    out.append(f"- tier 1 exempted: {len(result.exempted_tier1)}")
    out.append(f"- tier 2 exempted: {len(result.exempted_tier2)}")

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fail-on-flags",
        action="store_true",
        help="Exit nonzero if any unexempted flag is present. Use after the "
             "rewrite sweep to guard against regression.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Skip writing the markdown report; print summary only.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(mod_path)
    result = audit(repo_root)

    if not args.no_write:
        out_path = repo_root / "docs" / "audits" / "strata_social_axis_report.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(render_report(result), encoding="utf-8")
        print(f"Wrote report: {out_path}")

    print(
        f"Files audited: {result.files_audited}  "
        f"Tier 1: {len(result.tier1)} unexempted / {len(result.exempted_tier1)} exempted  "
        f"Tier 2: {len(result.tier2)} unexempted / {len(result.exempted_tier2)} exempted"
    )

    if args.fail_on_flags and (result.tier1 or result.tier2):
        print(
            "FAIL: unexempted strata/social-axis flags present. "
            "Either rewrite the events or add entries to "
            "docs/audits/strata_social_axis_exceptions.md.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
