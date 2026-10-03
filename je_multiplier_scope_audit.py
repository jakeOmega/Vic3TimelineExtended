"""Find country-only reads in JE add_modifier multipliers (issue #677).

The stored multiplier is re-evaluated in journal-entry scope. A bare country
property returns 'none', so the modifier silently applies at x1. Walk inline
arithmetic and transitive script-value/trigger references, preserving source
locations and duplicate statements. Country-only triggers come from the
committed engine supported-scopes catalog; country modifier reads are also
checked. An owner link or explicitly scoped read leaves JE scope.

This checks explicit je: links, including inside control flow, across common/
and events/. It does not infer the input scope of standalone effects or audit
other scope types. Variable lifetime is covered by modifier_multiplier_var_audit.
Suppress on the multiplier line with # REVIEWED YYYY-MM-DD: rationale.
"""
from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path

from modifier_multiplier_var_audit import blank_comments_and_strings, _parse_reviewed
from prev_scope_audit import load_links

_TOKEN_RE = re.compile(
    r"(?P<close>\})|(?P<key>[\w.:|@$-]+)\s*(?:\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[^\s{}]+))|(?P<anon>\{)"
)


@dataclass
class Node:
    key: str
    value: str | None
    children: list[Node]
    file: str
    line: int


@dataclass
class Flag:
    file: str
    line: int  # multiplier line (suppression location)
    journal_entry: str
    modifier: str
    read: str
    read_file: str
    read_line: int
    chain: tuple[str, ...]
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0


def parse_text(text: str, rel_path: str) -> tuple[list[Node], dict[int, str]]:
    clean, comments = blank_comments_and_strings(text)
    starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]
    nodes: list[Node] = []
    stack = [nodes]
    for match in _TOKEN_RE.finditer(clean):
        if match.group("close"):
            if len(stack) > 1:
                stack.pop()
            continue
        node = Node(
            key=match.group("key") or "?", value=match.group("value"),
            children=[], file=rel_path, line=bisect_right(starts, match.start()),
        )
        stack[-1].append(node)
        if match.group("open") or match.group("anon"):
            stack.append(node.children)
    return nodes, comments


def load_country_triggers(mod_path: str) -> set[str]:
    """Country-only triggers plus country accessors unavailable in JE scope.

    Missing metadata must fail the audit rather than silently weaken CI.
    """
    text = (Path(mod_path) / "docs/engine/triggers_parsed.txt").read_text(encoding="utf-8-sig")
    reads = set(re.findall(r"^## (\w+)\nScopes: country\s*$", text, re.MULTILINE))
    # Numeric accessors (income, gdp, ...) live in event_targets, not triggers.
    # GDP also accepts states/markets, but still cannot be read from a JE.
    targets = (Path(mod_path) / "docs/engine/event_targets_summary.txt").read_text(encoding="utf-8-sig")
    for line in targets.splitlines():
        fields = line.split("|")
        if len(fields) < 4:
            continue
        inputs, name, outputs = fields[:3]
        if ("country" in inputs.split(",") and "journal_entry" not in inputs.split(",")
                and "value" in outputs.split(",") and name != "modifier"):
            reads.add(name)
    if not reads:
        raise ValueError("Engine scope catalogs contain no country reads")
    return reads


def _scope(key: str, journal_entry: str | None, links: set[str]) -> str | None:
    """Scope changes are explicit links/iterators; other blocks are transparent."""
    if key.startswith("je:"):
        return key
    if key.lower() == "this":
        return journal_entry
    if (key in links or key.lower() in {"root", "prev"}
            or ":" in key or "." in key
            or (key.startswith(("every_", "random_", "ordered_", "any_"))
                and key != "random_list")):
        return None
    return journal_entry


def _unsafe_reads(nodes: list[Node], definitions: dict[str, Node],
                  country_triggers: set[str], links: set[str],
                  journal_entry: str | None,
                  chain: tuple[str, ...] = ()):
    """Yield (read, source node, reference chain); cycles terminate per path."""
    def inspect(token: str | None, node: Node):
        if token is None:
            return
        # THIS still means the JE. Other explicit paths (owner.gdp, root.var:X,
        # c:TAG.income, var:X, global_var:X, ...) are not bare country reads.
        bare = token.removeprefix("this.").removeprefix("THIS.")
        if journal_entry and (bare in country_triggers
                              or bare.startswith("modifier:country_")):
            yield token, node, chain
        elif bare in definitions and bare not in chain:
            definition = definitions[bare]
            body = definition.children or [Node(
                "value", definition.value, [], definition.file, definition.line,
            )]
            yield from _unsafe_reads(
                body, definitions, country_triggers,
                links, journal_entry, chain + (bare,),
            )

    for node in nodes:
        if node.children:
            scope = _scope(node.key, journal_entry, links)
            # Arithmetic, conditions and trigger argument blocks preserve
            # scope. The trigger key itself can be a country-only read.
            yield from inspect(node.key, node)
            yield from _unsafe_reads(node.children, definitions, country_triggers,
                                     links, scope, chain)
        else:
            yield from inspect(node.key, node)
            yield from inspect(node.value, node)


def scan_nodes(nodes: list[Node], comments: dict[int, str],
               definitions: dict[str, Node], country_triggers: set[str],
               links: set[str], journal_entry: str | None = None) -> list[Flag]:
    flags: list[Flag] = []
    for node in nodes:
        if node.key == "add_modifier" and journal_entry:
            modifier = next((n.value for n in node.children if n.key == "name"), "?")
            for mult in (n for n in node.children if n.key == "multiplier"):
                reads = _unsafe_reads([mult], definitions, country_triggers,
                                      links, journal_entry)
                seen = set()
                for read, source, chain in reads:
                    identity = (read, source.file, source.line, chain)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    flags.append(Flag(
                        node.file, mult.line, journal_entry, modifier, read,
                        source.file, source.line, chain,
                        _parse_reviewed(comments.get(mult.line)),
                    ))
        flags.extend(scan_nodes(node.children, comments, definitions, country_triggers,
                                links, _scope(node.key, journal_entry, links)))
    return flags


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """Pure file scan; no game install or ModState is needed."""
    if mod_path is None:
        from path_constants import mod_path
    root = Path(mod_path)
    country_triggers = load_country_triggers(mod_path)
    links = load_links(mod_path) | {"owner"}
    files = sorted(p for sub in ("common", "events") for p in (root / sub).rglob("*.txt"))
    parsed = []
    definitions: dict[str, Node] = {}
    for path in files:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8-sig")
        is_definition = rel.startswith(("common/script_values/", "common/scripted_triggers/"))
        if not is_definition and "add_modifier" not in text:
            continue
        nodes, comments = parse_text(text, rel)
        parsed.append((nodes, comments))
        if is_definition:
            definitions.update((node.key, node) for node in nodes)
    flags = []
    for nodes, comments in parsed:
        flags.extend(scan_nodes(nodes, comments, definitions, country_triggers, links))
    return AuditResult(flags, len(files))


def render_report(result: AuditResult) -> str:
    out = [
        "# Journal-entry multiplier scope audit report", "",
        "Auto-generated by `je_multiplier_scope_audit.py` on server reload. Do not hand-edit.", "",
        "Country-only reads in a JE multiplier return `none` and scale the modifier by 1.",
        "Route reads through `owner = { }`, or precompute a persistent country variable",
        "and read it flat through `root.var:X`. Named script values and triggers are",
        "followed transitively; country-only triggers come from the engine scope catalog.", "",
        "Suppress on the multiplier line: `# REVIEWED YYYY-MM-DD: rationale`.", "",
    ]
    for title, reviewed in (("Unreviewed Flags", False), ("Reviewed Exemptions", True)):
        out.extend((f"## {title}", ""))
        flags = [f for f in result.flags if bool(f.exemption) == reviewed]
        if not flags:
            out.append("_None._")
        for f in flags:
            via = " → ".join(f.chain) or "inline"
            row = (f"- `{f.file}:{f.line}` — `{f.journal_entry}`, `{f.modifier}`: "
                   f"`{f.read}` at `{f.read_file}:{f.read_line}` ({via})")
            if f.exemption:
                row += f" — **{f.exemption['date']}**: {f.exemption['rationale']}"
            out.append(row)
        out.append("")
    out.extend(("## Coverage", "", f"- total flags: {len(result.flags)}",
                f"- unreviewed: {sum(not f.exemption for f in result.flags)}",
                f"- exempted: {sum(bool(f.exemption) for f in result.flags)}", ""))
    return "\n".join(out)


def regenerate(mod_state=None) -> dict:
    from path_constants import mod_path
    result = audit(mod_state, mod_path)
    out = Path(mod_path) / "docs/engine/je_multiplier_scope_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(result), encoding="utf-8")
    return {"files_audited": result.files_audited, "total_flags": len(result.flags),
            "unreviewed": sum(not f.exemption for f in result.flags),
            "exempted": sum(bool(f.exemption) for f in result.flags)}


def main(argv: list[str] | None = None) -> int:
    import sys
    result = audit()
    print(render_report(result))
    strict = "--strict" in (sys.argv[1:] if argv is None else argv)
    return int(strict and any(not f.exemption for f in result.flags))


if __name__ == "__main__":
    raise SystemExit(main())
