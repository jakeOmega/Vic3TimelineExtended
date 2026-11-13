"""Detects loc references to concepts not registered in `common/game_concepts/`.

Background: When a localization value contains `[concept_X]` or
`[Concept('concept_X', ...)]` and `concept_X` is not declared in
`common/game_concepts/` (vanilla or mod), the engine treats the bracket as a
data-system function call, fails to resolve it, and logs three error lines per
render — `Could not find data system function 'concept_X'`,
`Failed converting statement for 'concept_X'`, and
`Data error in loc string '<key>'`. UI panels that show the offending loc
spam debug.log at hundreds of lines per second and stall the game.

`Concept()`'s first argument is checked whatever its name (#438): every
registered concept starts with `concept_`, but `gen_un_button_descs.py`
shipped `[Concept('<modifier_name>', ...)]` for 13 keys, and only the two whose
expansion carried a `[` logged anything (#437). The plain `[X]` form stays
limited to `concept_` names, since any other bracketed word is a data function.

1.15 glossary links are checked the same way against `common/glossary/`
(vanilla or mod): `[glossary_x]` and `[Glossary('glossary_x', 'text')]`, the
two forms `common/glossary/glossary.md` and vanilla's loc use. A
`Concept('glossary_x', ...)` still flags as a missing concept: vanilla never
links a glossary entry that way, and Concept() looks up game concepts.

The engine emits no parse-time warning. `loc_coverage_audit` checks whether
mod-introduced entities have their conventional loc keys, but doesn't scan
loc *values* for unregistered concept hyperlinks. This audit closes that gap.

Coverage: every `*.yml` under `<mod_path>/localization/` (recursive). Each
`[concept_X]` and `[Concept('X', ...)]` reference is checked against
the union of vanilla + mod concepts loaded into
`mod_state.mod_parsers['Game Concepts']`. Vanilla loc isn't scanned (we only
care about mod-side bugs).

Suppress an intentional unregistered reference with a trailing comment on the
loc line. The engine ignores anything after the closing quote on a loc line:

    my_loc_key:0 "... [concept_X] ..." # REVIEWED 2026-05-09: rationale

`python3 concept_reference_audit.py --strict` is the CI mode (the committed
`vanilla_parsed/` snapshot stands in for the game). It exits 1 when any flag
lacks that comment: #1257 shipped `je_space_race_widget_mod_mine_tt` linking
`[concept_sr_extraplanetary_base]`, which never existed, and nothing failed.
"""
import os
import re
from dataclasses import dataclass, field

from audit_common import AuditResult as _AuditResult
from audit_common import cli_main, parse_reviewed, write_text
from mod_state import split_loc_line


@dataclass
class ConceptFlag:
    loc_key: str
    concept: str
    file: str
    line: int
    exemption: dict | None = None
    # "concept" (game_concepts) or "glossary" (1.15 glossary entries).
    kind: str = "concept"


@dataclass
class AuditResult(_AuditResult):
    flags: list[ConceptFlag] = field(default_factory=list)
    loc_files_scanned: int = 0
    refs_checked: int = 0
    registered_concepts: int = 0


# Plain hyperlink form: `[concept_foo]`. Excluded character class on the
# closing side prevents accidental matches against `[concept_foo.GetX]` etc.
_PATTERN_PLAIN = re.compile(r"\[(concept_[A-Za-z0-9_]+)\]")
# Custom-display form: `[Concept('concept_foo', '$display$')]`. Both single
# and double quotes are accepted; whitespace around the quote is tolerated.
# Any first argument is captured, not only `concept_*` ones (#438). A
# `$PARAM$`-built name can't match, so it is never flagged.
_PATTERN_CONCEPT_FN = re.compile(
    r"Concept\(\s*['\"]([A-Za-z0-9_]+)['\"]"
)
# 1.15 glossary links: `[glossary_foo]` and `[Glossary('glossary_foo', 'text')]`
# (the global function the 1.15 data types add). The plain form is limited to
# `glossary_` names, which the readme makes every entry's prefix, as the
# concept one is; the function's first argument is checked whatever it is.
_PATTERN_GLOSSARY_PLAIN = re.compile(r"\[(glossary_[A-Za-z0-9_]+)\]")
_PATTERN_GLOSSARY_FN = re.compile(
    r"(?<![A-Za-z0-9_.])Glossary\(\s*['\"]([A-Za-z0-9_]+)['\"]"
)


def _parse_loc_line(raw: str) -> tuple[str, str, str] | None:
    r"""Split one loc line with the shared, escape-aware
    `mod_state.split_loc_line` — the same rule `ModState.add_localization`
    uses — so a `\"` inside a value no longer truncates it (or misfiles the
    rest of the text as `trailing`).

    Returns (key, value, trailing) where `trailing` is everything after the
    closing quote (used to find `# REVIEWED ...` suppression comments).
    Returns None for blank lines, comment-only lines, the file header
    (`l_english:`), and malformed entries.
    """
    return split_loc_line(raw)


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


def _registered_glossary(ms) -> set[str]:
    """Glossary entries declared in vanilla + mod `common/glossary/` (1.15)."""
    parser = ms.mod_parsers.get("Glossary")
    if parser is None or not parser.data:
        return set()
    return set(parser.data.keys())


def audit(ms, mod_path: str | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    registered = _registered_concepts(ms)
    registry = {"concept": registered, "glossary": _registered_glossary(ms)}
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
                        per_line_refs = [
                            (name, "concept")
                            for name in _PATTERN_PLAIN.findall(value)
                            + _PATTERN_CONCEPT_FN.findall(value)
                        ] + [
                            (name, "glossary")
                            for name in _PATTERN_GLOSSARY_PLAIN.findall(value)
                            + _PATTERN_GLOSSARY_FN.findall(value)
                        ]
                        if not per_line_refs:
                            continue
                        exemption = parse_reviewed(trailing)
                        seen_in_line: set[tuple[str, str]] = set()
                        for concept, kind in per_line_refs:
                            refs_checked += 1
                            if concept in registry[kind]:
                                continue
                            # Collapse duplicate references on the same line
                            # (e.g. a key that mentions concept_X twice).
                            if (concept, kind) in seen_in_line:
                                continue
                            seen_in_line.add((concept, kind))
                            flags.append(ConceptFlag(
                                loc_key=loc_key,
                                concept=concept,
                                file=rel_p,
                                line=i,
                                exemption=exemption,
                                kind=kind,
                            ))
            except OSError:
                pass

    return AuditResult(
        flags=flags,
        loc_files_scanned=files_scanned,
        refs_checked=refs_checked,
        registered_concepts=len(registered),
    )


def strict_exit_code(result: AuditResult) -> int:
    """Exit status for `--strict` (CI mode): 1 if any flag lacks a
    `# REVIEWED` exemption."""
    return 1 if result.failed else 0


def render_report(result: AuditResult) -> str:
    unrev = result.unreviewed
    exemp = result.exemptions

    out = [
        "# Concept reference audit report",
        "",
        "Auto-generated by `concept_reference_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a localization value contains `[concept_X]` or",
        "`[Concept('X', ...)]` whose concept name is not registered in",
        "`common/game_concepts/` (vanilla or mod). The engine then treats the",
        "bracket as a data-system function call, fails to resolve it, and",
        "logs three error lines per render — flooding `debug.log` at hundreds",
        "of lines per second when the offending UI is shown.",
        "",
        "Fix: add `concept_X = {}` to `common/game_concepts/extra_concepts.txt`",
        "(plus the matching `concept_X:0 \"Display Name\"` and",
        "`concept_X_desc:0 \"Tooltip\"` localization keys if they don't exist).",
        "When `X` is not meant to be a concept at all (a modifier or other",
        "entity name), drop the `Concept()` wrapper and keep the display text.",
        "",
        "A **glossary** flag is a 1.15 glossary link, `[glossary_X]` or",
        "`[Glossary('glossary_X', 'text')]`, with no `glossary_X` in",
        "`common/glossary/` (vanilla or mod): add `glossary_X = {}` and its",
        "`glossary_X` / `glossary_X_desc` loc. A glossary entry is never",
        "linked through `Concept()`, which looks up game concepts only.",
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
        by_concept: dict[tuple[str, str], list[ConceptFlag]] = {}
        for f in unrev:
            by_concept.setdefault((f.concept, f.kind), []).append(f)
        for concept, kind in sorted(by_concept):
            entries = by_concept[(concept, kind)]
            what = "" if kind == "concept" else f"{kind}, "
            out.append(f"### `{concept}` ({what}{len(entries)})")
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
        # No line number on a reviewed entry: the loc key names it, and an
        # edit above it would otherwise churn the report.
        for f in exemp:
            out.append(
                f"- `{f.file}` — `{f.loc_key}` references `{f.concept}` — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    # Flag counts only: the file / reference / concept counts stay on the
    # result (and in the regenerate() summary) but move with unrelated loc.
    out.append("## Coverage")
    out.append("")
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
    write_text(os.path.join(mod_path, "docs", "engine", "concept_reference_report.md"), report)
    unrev = len(result.unreviewed)
    exemp = len(result.exemptions)
    return {
        "loc_files_scanned": result.loc_files_scanned,
        "refs_checked": result.refs_checked,
        "registered_concepts": result.registered_concepts,
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": exemp,
    }


def main(argv=None) -> int:
    """Print the report; `--strict` (CI) exits 1 if any flag lacks a
    `# REVIEWED ...` exemption."""
    from path_constants import mod_path

    def run(args) -> AuditResult:
        import mod_state_server
        # Vanilla's concepts from where a server load takes them (the
        # vanilla_parsed/ snapshot without a game install): a bare ModState has
        # none, so every reference to one false-flags.
        return audit(mod_state_server.cli_mod_state(), mod_path=mod_path)

    return cli_main(run, lambda result, args: render_report(result),
                    argv=argv, description=__doc__.splitlines()[0])


if __name__ == "__main__":
    raise SystemExit(main())
