"""Lints localization values for render-breaking bracket-style formatting tags.

**Bracket-style formatting tags** — `[b] [/b] [i] [/i] [u] [/u]` and any `[/x]`
closing-tag form (Markdown / BBCode muscle memory). Vic3 has no such tags; the
engine tries to resolve `[b]` as a data-system-function accessor chain, emits a
per-render `data-system-function` error, and the synchronous log spam drives
measurable in-game lag (confirmed in a prior session). The correct form is
`#b …#!`.

`localization_accessor_audit` catches `[Scope.GetX]` accessor chains and
`concept_reference_audit` catches `[concept_x]` hyperlinks — neither flags
bracket formatting tags. This audit closes that gap. The check is vanilla- and
mod-clean today (0 findings); it is a regression guard against re-introducing
the known lag bug.

Note on scope: issue #134 also proposed flagging unbalanced `#…#!` formatting
runs, but an empirical sweep found 2341 "violations" across vanilla loc
(1.15M values) — Vic3 legitimately splits formatting across concatenated loc
fragments (`#R` opened in one key, `#!` reset in another) and tolerates `#!#!`
double-resets, so a balance check does not match engine behavior. That check
was dropped as unshippable; see the issue thread.

Suppress an intentional flag with a trailing comment on the loc line — the
engine ignores anything after the closing quote:

    my_loc_key:0 "... [b]bold[/b] ..." # REVIEWED 2026-05-21: rationale
"""
import os
import re
from dataclasses import dataclass, field


@dataclass
class RenderFlag:
    loc_key: str
    issue: str  # "bracket_tag"
    detail: str
    file: str
    line: int
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[RenderFlag] = field(default_factory=list)
    loc_files_scanned: int = 0
    values_checked: int = 0


_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)
# `[b] [i] [u]` and their closing forms, plus any other `[/x]` closing tag.
# Valid Vic3 loc never opens a bare single-letter bracket nor uses a `[/` slash;
# accessor chains are `[Scope.Method]` and concept links are `[concept_x]`.
_BRACKET_FMT_RE = re.compile(r"\[/?[biu]\]|\[/[A-Za-z]\w*\]?")


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _parse_loc_line(raw: str) -> tuple[str, str, str] | None:
    """Returns (key, value, trailing-after-closing-quote) or None.

    Mirrors `concept_reference_audit._parse_loc_line`. The trailing segment is
    where `# REVIEWED …` suppression comments live.
    """
    line = raw.rstrip("\n")
    stripped = line.lstrip()
    if not stripped or stripped.startswith("#") or ":" not in stripped:
        return None
    key, rest = line.split(":", 1)
    key = key.strip()
    if not key:
        return None
    quote_locations = [i for i, c in enumerate(rest) if c == '"']
    if len(quote_locations) < 2:
        return None
    value = rest[quote_locations[0] + 1: quote_locations[-1]]
    trailing = rest[quote_locations[-1] + 1:]
    return key, value, trailing


def check_value(value: str) -> list[tuple[str, str]]:
    """Return [(issue, detail)] for one loc value. Pure; unit-testable."""
    out: list[tuple[str, str]] = []
    brackets = _BRACKET_FMT_RE.findall(value)
    if brackets:
        uniq = sorted(set(brackets))
        out.append((
            "bracket_tag",
            "invalid bracket formatting tag(s): "
            + ", ".join(f"`{b}`" for b in uniq)
            + " — use `#b …#!` style, not Markdown/BBCode",
        ))
    return out


def audit(ms=None, mod_path: str | None = None) -> AuditResult:
    """Scan every mod loc value. `ms` is unused (loc files are read directly)
    but kept for the POST_LOAD_GENERATORS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    flags: list[RenderFlag] = []
    files_scanned = 0
    values_checked = 0

    loc_root = os.path.join(mod_path, "localization")
    if not os.path.isdir(loc_root):
        return AuditResult(flags=[], loc_files_scanned=0, values_checked=0)

    for root, _dirs, files in os.walk(loc_root):
        for fname in sorted(files):
            if not fname.endswith(".yml"):
                continue
            abs_p = os.path.join(root, fname)
            rel_p = os.path.relpath(abs_p, mod_path)
            files_scanned += 1
            try:
                with open(abs_p, encoding="utf-8-sig", errors="replace") as fh:
                    for i, raw_line in enumerate(fh, start=1):
                        parsed = _parse_loc_line(raw_line)
                        if parsed is None:
                            continue
                        loc_key, value, trailing = parsed
                        values_checked += 1
                        issues = check_value(value)
                        if not issues:
                            continue
                        exemption = _parse_reviewed(trailing)
                        for issue, detail in issues:
                            flags.append(RenderFlag(
                                loc_key=loc_key,
                                issue=issue,
                                detail=detail,
                                file=rel_p,
                                line=i,
                                exemption=exemption,
                            ))
            except OSError:
                pass

    return AuditResult(
        flags=flags,
        loc_files_scanned=files_scanned,
        values_checked=values_checked,
    )


_ISSUE_LABEL = {
    "bracket_tag": "Bracket formatting tags ([b], [/x], …)",
}


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Localization render audit report",
        "",
        "Auto-generated by `loc_render_audit.py` on every full `POST /reload`",
        "of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a localization value contains a bracket-style formatting tag",
        "(`[b]`, `[/i]`, …). Vic3 has no such tags — the engine treats `[b]` as",
        "a failing data-system-function and floods the log, causing in-game lag.",
        "",
        "Fix: replace `[b]X[/b]` with `#b X#!`.",
        "",
        "Suppress an intentional flag with a trailing comment on the loc line:",
        "`my_loc_key:0 \"…\" # REVIEWED YYYY-MM-DD: rationale`",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out.append("_None._")
        out.append("")
    else:
        by_issue: dict[str, list[RenderFlag]] = {}
        for f in unrev:
            by_issue.setdefault(f.issue, []).append(f)
        for issue in sorted(by_issue):
            entries = by_issue[issue]
            out.append(f"### {_ISSUE_LABEL.get(issue, issue)} ({len(entries)})")
            out.append("")
            for f in entries:
                out.append(f"- `{f.file}:{f.line}` — `{f.loc_key}`: {f.detail}")
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        for f in exemp:
            out.append(
                f"- `{f.file}:{f.line}` — `{f.loc_key}` ({f.issue}) — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    out.append(f"- loc files scanned: {result.loc_files_scanned}")
    out.append(f"- loc values checked: {result.values_checked}")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")
    out.append("")

    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_GENERATORS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(mod_path, "docs", "engine", "loc_render_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    unrev = sum(1 for f in result.flags if not f.exemption)
    exemp = sum(1 for f in result.flags if f.exemption)
    return {
        "loc_files_scanned": result.loc_files_scanned,
        "values_checked": result.values_checked,
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": exemp,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    result = audit(mod_path=mod_path)
    print(render_report(result))
