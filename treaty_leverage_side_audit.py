"""Audit for `country_treaty_leverage_generation_add` on the wrong side of a directed treaty article.

The modifier reads like "leverage this country generates", and the engine's own
tooltip — "Leverage Generation from Treaty" — does nothing to dispel that. It is
the other way round: the leverage is generated **against** the country whose
`source_modifier` / `target_modifier` carries the line, by the dominant
counterparty, and only while that counterparty leads a power bloc.

Getting it backwards is completely engine-silent. No log line, no parse error,
no `script_parse_error`, nothing in `error.log` — the modifier name is valid and
the block it sits in is valid, so the engine simply routes the influence the
other way. It only shows up in the leverage panel mid-campaign. Monetary phase 6
(#365) shipped all five banking articles (`currency_peg`, `swap_line`,
`lender_of_last_resort`, `imposed_currency_peg`, `debt_receivership`) inverted
this way; the owner caught it in game, not in review.

The heuristic
-------------
There is no way to read "which side is dominant" out of the script, but there is
a reliable proxy already written into every article: **`maintenance_paid_by`**.
The beneficiary of a directed article pays its upkeep, and the party being
leaned on is the other one — so the leverage line belongs on the side that does
**not** pay maintenance. That holds for every vanilla article that carries the
modifier:

===========================  ===================  =================
Vanilla article              `maintenance_paid_by`  leverage line
===========================  ===================  =================
`guarantee_independence`     `source_country`     `target_modifier`
`foreign_investment_rights`  `target_country`     `source_modifier`
`trade_privilege`            `target_country`     `source_modifier`
`host_power_bloc_embassy`    `target_country`     `source_modifier`
===========================  ===================  =================

...and for 13 of the mod's 14 directed articles that carry it. The one
deliberate exception is `request_influence`, where a bloc-less petitioner both
pays the upkeep *and* is the party the bloc leader gains leverage over; it
carries a `# REVIEWED` comment.

What is and isn't flagged
-------------------------
Only a `country_treaty_leverage_generation_add` that is inside a
`source_modifier` or `target_modifier` block **directly under a top-level
article**, in an article that also declares `maintenance_paid_by`. Silent on:

- `mutual_modifier` — a symmetric block has no side to be wrong about;
- an article with no `maintenance_paid_by` — nothing to compare against, so the
  heuristic does not apply (counted under "undetermined" in the report);
- the modifier appearing anywhere else in the article (an effect block, an AI
  score), which carries no side.

Suppress a deliberate case with a trailing `# REVIEWED YYYY-MM-DD: rationale`
comment on the `country_treaty_leverage_generation_add` line or on the article's
opening `<name> = {` line.

Why a raw-text scan instead of `paradox_file_parser`
----------------------------------------------------
Same reason as `iterator_limit_audit`: the parser discards line numbers and
comments, so there would be nothing to report a location against and nothing to
hang a `# REVIEWED` suppression on. The comment/string blanking helper is shared
with that module — it preserves offsets, so line numbers stay exact.
"""
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

# Offset-preserving comment/string blanking, shared with the iterator audit so
# the two agree on what "a commented-out line" means.
from iterator_limit_audit import blank_comments_and_strings

LEVERAGE_MODIFIER = "country_treaty_leverage_generation_add"

# The two directed modifier blocks. `mutual_modifier` is deliberately absent.
DIRECTED_SIDES = ("source_modifier", "target_modifier")

# maintenance side -> the side the leverage line must NOT be on.
_PAYING_SIDE_BLOCK = {
    "source_country": "source_modifier",
    "target_country": "target_modifier",
}

AUDIT_DIRS = (os.path.join("common", "treaty_articles"),)

_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+)$"
)

_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    r"|(?P<key>[A-Za-z_][A-Za-z0-9_.:|@$\-]*)\s*(?:\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[^\s{}#]+))?"
    r"|(?P<anon>\{)"
)


@dataclass
class Flag:
    file: str
    line: int  # line of the offending country_treaty_leverage_generation_add
    article: str
    article_line: int
    side: str  # "source_modifier" | "target_modifier"
    maintenance_paid_by: str  # "source_country" | "target_country"
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0
    articles_checked: int = 0  # directed articles the heuristic could judge
    articles_undetermined: int = 0  # leverage line present, no maintenance side


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for m in re.finditer(r"\n", text):
        starts.append(m.end())
    return starts


def _line_of(pos: int, starts: list[int]) -> int:
    return bisect_right(starts, pos)


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def scan_text(text: str, rel_path: str) -> list[Flag]:
    """Scan one file's raw text; return a flag per misplaced leverage line."""
    clean, comments = blank_comments_and_strings(text)
    starts = _line_starts(clean)
    flags: list[Flag] = []

    # Per-article accumulator, reset at every top-level `<name> = {`.
    article: str | None = None
    article_line = 0
    maintenance: str | None = None
    # (side, line) for every leverage line found in a directed modifier block.
    leverage_hits: list[tuple[str, int]] = []
    # Block names from the article inwards; [] means we are at file level.
    stack: list[str | None] = []

    def finish() -> None:
        nonlocal article, maintenance, leverage_hits
        if article and maintenance in _PAYING_SIDE_BLOCK:
            bad_side = _PAYING_SIDE_BLOCK[maintenance]
            for side, line in leverage_hits:
                if side == bad_side:
                    flags.append(
                        Flag(
                            file=rel_path,
                            line=line,
                            article=article,
                            article_line=article_line,
                            side=side,
                            maintenance_paid_by=maintenance,
                            exemption=(
                                _parse_reviewed(comments.get(line))
                                or _parse_reviewed(comments.get(article_line))
                            ),
                        )
                    )
        article = None
        maintenance = None
        leverage_hits = []

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
                if not stack:
                    finish()
            continue
        if m.group("anon"):
            if stack:
                stack.append(None)
            continue

        key = m.group("key")
        line = _line_of(m.start(), starts)

        if m.group("open"):
            if not stack:  # a top-level entity: this is the article itself
                article = key
                article_line = line
                maintenance = None
                leverage_hits = []
            stack.append(key)
            continue

        # A scalar `key = value` statement.
        value = m.group("value")
        if len(stack) == 1 and key == "maintenance_paid_by":
            maintenance = value
        elif (
            len(stack) == 2
            and stack[1] in DIRECTED_SIDES
            and key == LEVERAGE_MODIFIER
        ):
            leverage_hits.append((stack[1], line))

    if stack:  # unbalanced braces — judge what we have rather than dropping it
        finish()

    return flags


def scan_file(filepath: str, rel_path: str) -> list[Flag]:
    try:
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    return scan_text(text, rel_path)


def _count_articles(text: str) -> tuple[int, int]:
    """Return (judgeable, undetermined) article counts for coverage stats."""
    clean, _ = blank_comments_and_strings(text)
    judgeable = undetermined = 0
    maintenance: str | None = None
    has_directed_leverage = False
    stack: list[str | None] = []

    def finish() -> None:
        nonlocal judgeable, undetermined, maintenance, has_directed_leverage
        if has_directed_leverage:
            if maintenance in _PAYING_SIDE_BLOCK:
                judgeable += 1
            else:
                undetermined += 1
        maintenance = None
        has_directed_leverage = False

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
                if not stack:
                    finish()
            continue
        if m.group("anon"):
            if stack:
                stack.append(None)
            continue
        key = m.group("key")
        if m.group("open"):
            if not stack:
                maintenance = None
                has_directed_leverage = False
            stack.append(key)
            continue
        if len(stack) == 1 and key == "maintenance_paid_by":
            maintenance = m.group("value")
        elif len(stack) == 2 and stack[1] in DIRECTED_SIDES and key == LEVERAGE_MODIFIER:
            has_directed_leverage = True
    if stack:
        finish()
    return judgeable, undetermined


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_GENERATORS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    flags: list[Flag] = []
    files_audited = 0
    checked = 0
    undetermined = 0
    for sub in AUDIT_DIRS:
        root_dir = os.path.join(mod_path, sub)
        if not os.path.isdir(root_dir):
            continue
        for root, _dirs, files in os.walk(root_dir):
            for fname in sorted(files):
                if not fname.endswith(".txt"):
                    continue
                abs_p = os.path.join(root, fname)
                rel_p = os.path.relpath(abs_p, mod_path).replace(os.sep, "/")
                files_audited += 1
                flags.extend(scan_file(abs_p, rel_p))
                try:
                    with open(abs_p, "r", encoding="utf-8-sig", errors="replace") as fh:
                        c, u = _count_articles(fh.read())
                except OSError:
                    c = u = 0
                checked += c
                undetermined += u

    return AuditResult(
        flags=flags,
        files_audited=files_audited,
        articles_checked=checked,
        articles_undetermined=undetermined,
    )


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Treaty leverage side audit report",
        "",
        "Auto-generated by `treaty_leverage_side_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a directed treaty article whose",
        "`country_treaty_leverage_generation_add` sits in the same side's",
        "modifier block as the side named by `maintenance_paid_by`.",
        "",
        "The modifier generates leverage **against** the country whose block",
        "carries it, not by it. The beneficiary of a directed article pays its",
        "upkeep, so the leverage belongs on the *other* side. Vanilla is",
        "consistent: `guarantee_independence` pays from the source and puts the",
        "line on `target_modifier`; `foreign_investment_rights`,",
        "`trade_privilege` and `host_power_bloc_embassy` pay from the target and",
        "put it on `source_modifier`.",
        "",
        "Getting this backwards is engine-silent — no log line, no parse error,",
        "just influence flowing the wrong way. Phase 6 of the monetary system",
        "shipped five articles inverted this way (corrected 2026-09-21).",
        "",
        "`mutual_modifier` blocks and articles with no `maintenance_paid_by`",
        "are not judged — see Coverage below.",
        "",
        "Suppress a deliberate case with a trailing comment on the",
        "`country_treaty_leverage_generation_add` line or the article's opening",
        "`<name> = {` line:",
        "`country_treaty_leverage_generation_add = 200  # REVIEWED YYYY-MM-DD: why`",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out.append("_None._")
        out.append("")
    else:
        by_file: dict[str, list[Flag]] = {}
        for f in unrev:
            by_file.setdefault(f.file, []).append(f)
        for fname in sorted(by_file):
            out.append(f"### `{fname}`")
            out.append("")
            for f in by_file[fname]:
                other = (
                    "target_modifier"
                    if f.side == "source_modifier"
                    else "source_modifier"
                )
                out.append(
                    f"- line {f.line}: `{f.article}` (opened at line "
                    f"{f.article_line}) pays maintenance from "
                    f"`{f.maintenance_paid_by}` and carries the leverage line in "
                    f"`{f.side}` — move it to `{other}`, or mark it reviewed"
                )
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        for f in exemp:
            out.append(
                f"- `{f.file}:{f.line}` — `{f.article}`: leverage in `{f.side}` "
                f"with `maintenance_paid_by = {f.maintenance_paid_by}` — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    out.append(f"- files audited: {result.files_audited}")
    out.append(f"- directed articles judged: {result.articles_checked}")
    out.append(
        f"- articles with a leverage line but no `maintenance_paid_by`: "
        f"{result.articles_undetermined}"
    )
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")
    out.append("")

    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(
        mod_path, "docs", "engine", "treaty_leverage_side_report.md"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    unrev = sum(1 for f in result.flags if not f.exemption)
    exemp = sum(1 for f in result.flags if f.exemption)
    return {
        "files_audited": result.files_audited,
        "articles_checked": result.articles_checked,
        "articles_undetermined": result.articles_undetermined,
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
    # --strict: CI mode. Exit 1 if any flag lacks a `# REVIEWED ...` exemption.
    if "--strict" in sys.argv:
        raise SystemExit(1 if any(not f.exemption for f in result.flags) else 0)
