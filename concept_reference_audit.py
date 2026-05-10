"""Detects loc references to concepts not registered in `common/game_concepts/`.

Background: When a localization value contains `[concept_X]` or
`[Concept('concept_X', ...)]` and `concept_X` is not declared in
`common/game_concepts/` (vanilla or mod), the engine treats the bracket as a
data-system function call, fails to resolve it, and logs three error lines per
render — `Could not find data system function 'concept_X'`,
`Failed converting statement for 'concept_X'`, and
`Data error in loc string '<key>'`. UI panels that show the offending loc
spam debug.log at hundreds of lines per second and stall the game.

The engine emits no parse-time warning. `loc_coverage_audit` checks whether
mod-introduced entities have their conventional loc keys, but doesn't scan
loc *values* for unregistered concept hyperlinks. This audit closes that gap.

Coverage: every `*.yml` under `<mod_path>/localization/` (recursive). Each
`[concept_X]` and `[Concept('concept_X', ...)]` reference is checked against
the union of vanilla + mod concepts loaded into
`mod_state.mod_parsers['Game Concepts']`. Vanilla loc isn't scanned (we only
care about mod-side bugs).

Suppress an intentional unregistered reference with a trailing comment on the
loc line. The engine ignores anything after the closing quote on a loc line:

    my_loc_key:0 "... [concept_X] ..." # REVIEWED 2026-05-09: rationale
"""
import os
import re
from dataclasses import dataclass, field


@dataclass
class ConceptFlag:
    loc_key: str
    concept: str
    file: str
    line: int
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[ConceptFlag] = field(default_factory=list)
    loc_files_scanned: int = 0
    refs_checked: int = 0
    registered_concepts: int = 0


_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)
# Plain hyperlink form: `[concept_foo]`. Excluded character class on the
# closing side prevents accidental matches against `[concept_foo.GetX]` etc.
_PATTERN_PLAIN = re.compile(r"\[(concept_[A-Za-z0-9_]+)\]")
# Custom-display form: `[Concept('concept_foo', '$display$')]`. Both single
# and double quotes are accepted; whitespace around the quote is tolerated.
_PATTERN_CONCEPT_FN = re.compile(
    r"Concept\(\s*['\"](concept_[A-Za-z0-9_]+)['\"]"
)


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _parse_loc_line(raw: str) -> tuple[str, str, str] | None:
    """Mirror `mod_state.add_localization`'s parser.

    Returns (key, value, trailing) where `trailing` is everything after the
    closing quote (used to find `# REVIEWED ...` suppression comments).
    Returns None for blank lines, comment-only lines, the file header
    (`l_english:`), and malformed entries.
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
    value = rest[quote_locations[0] + 1: quote_locations[1]]
    trailing = rest[quote_locations[1] + 1:]
    return key, value, trailing


def _registered_concepts(ms) -> set[str]:
    """Concept names declared in vanilla + mod `common/game_concepts/`.

    `mod_parsers['Game Concepts'].data` already contains the merged view
    (vanilla loaded first, then mod overrides on top), so this returns the
    full registry the engine sees.
    """
    parser = ms.mod_parsers.get("Game Concepts")
    if parser is None or not parser.data:
        return set()
    return set(parser.data.keys())


def audit(ms, mod_path: str | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    registered = _registered_concepts(ms)
    flags: list[ConceptFlag] = []
    files_scanned = 0
    refs_checked = 0

    loc_root = os.path.join(mod_path, "localization")
    if not os.path.isdir(loc_root):
        return AuditResult(
            flags=[],
            loc_files_scanned=0,
            refs_checked=0,
            registered_concepts=len(registered),
        )

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
                        per_line_concepts = (
                            _PATTERN_PLAIN.findall(value)
                            + _PATTERN_CONCEPT_FN.findall(value)
                        )
                        if not per_line_concepts:
                            continue
                        exemption = _parse_reviewed(trailing)
                        seen_in_line: set[str] = set()
                        for concept in per_line_concepts:
                            refs_checked += 1
                            if concept in registered:
                                continue
                            # Collapse duplicate references on the same line
                            # (e.g. a key that mentions concept_X twice).
                            if concept in seen_in_line:
                                continue
                            seen_in_line.add(concept)
                            flags.append(ConceptFlag(
                                loc_key=loc_key,
                                concept=concept,
                                file=rel_p,
                                line=i,
                                exemption=exemption,
                            ))
            except OSError:
                pass

    return AuditResult(
        flags=flags,
        loc_files_scanned=files_scanned,
        refs_checked=refs_checked,
        registered_concepts=len(registered),
    )


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Concept reference audit report",
        "",
        "Auto-generated by `concept_reference_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a localization value contains `[concept_X]` or",
        "`[Concept('concept_X', ...)]` but `concept_X` is not registered in",
        "`common/game_concepts/` (vanilla or mod). The engine then treats the",
        "bracket as a data-system function call, fails to resolve it, and",
        "logs three error lines per render — flooding `debug.log` at hundreds",
        "of lines per second when the offending UI is shown.",
        "",
        "Fix: add `concept_X = {}` to `common/game_concepts/extra_concepts.txt`",
        "(plus the matching `concept_X:0 \"Display Name\"` and",
        "`concept_X_desc:0 \"Tooltip\"` localization keys if they don't exist).",
        "",
        "Suppress an intentional unregistered reference with a trailing",
        "comment on the loc line:",
        "`my_loc_key:0 \"... [concept_X] ...\" # REVIEWED YYYY-MM-DD: rationale`",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out.append("_None._")
        out.append("")
    else:
        # Group by concept name so the same missing concept across many loc
        # keys collapses into one section.
        by_concept: dict[str, list[ConceptFlag]] = {}
        for f in unrev:
            by_concept.setdefault(f.concept, []).append(f)
        for concept in sorted(by_concept):
            entries = by_concept[concept]
            out.append(f"### `{concept}` ({len(entries)})")
            out.append("")
            for f in entries:
                out.append(f"- `{f.file}:{f.line}` — referenced by `{f.loc_key}`")
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        for f in exemp:
            out.append(
                f"- `{f.file}:{f.line}` — `{f.loc_key}` references `{f.concept}` — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    out.append(f"- loc files scanned: {result.loc_files_scanned}")
    out.append(f"- concept references checked: {result.refs_checked}")
    out.append(f"- registered concepts (vanilla + mod): {result.registered_concepts}")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")
    out.append("")

    return "\n".join(out) + "\n"


def regenerate(mod_state) -> dict:
    """POST_LOAD_GENERATORS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(mod_path, "docs", "engine", "concept_reference_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    unrev = sum(1 for f in result.flags if not f.exemption)
    exemp = sum(1 for f in result.flags if f.exemption)
    return {
        "loc_files_scanned": result.loc_files_scanned,
        "refs_checked": result.refs_checked,
        "registered_concepts": result.registered_concepts,
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": exemp,
    }


if __name__ == "__main__":
    # CLI entry: run against the live mod state.
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from mod_state import ModState
    from path_constants import mod_path
    import mod_state_server
    ms = ModState(mod_state_server.base_game_paths, mod_state_server.mod_paths)
    result = audit(ms, mod_path=mod_path)
    print(render_report(result))
