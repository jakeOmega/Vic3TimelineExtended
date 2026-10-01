"""Find variable operations whose current scope is a building (issue #519).

Buildings have no variable store. Scan raw scripts so line numbers and inline
REVIEWED exemptions survive. Control-flow blocks inherit their scope; engine
links and iterators switch it. Saved building scopes are inferred across files
and through aliases, to a fixed point. This is lexical analysis, not a call-
graph analysis: an untyped scripted-effect root is unknown, and a saved name
used for both buildings and other entities is conservatively considered a
possible building. Explicit prefixes on variable reads are left alone.
"""
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

from iterator_limit_audit import blank_comments_and_strings
from prev_scope_audit import _is_scope_change, _parse_reviewed, load_links

AUDIT_DIRS = ("common", "events")
BUILDING_ITERATORS = {
    f"{kind}_scope_building" for kind in ("every", "random", "ordered", "any")
}
_BUILDING_HINT = re.compile(r"(?:every|any|random|ordered)_scope_building\b|\bb:")
VARIABLE_KEYS = {
    "set_variable", "change_variable", "remove_variable", "clamp_variable",
    "has_variable", "round_variable",
}
# Include standalone tokens (e.g. script-value arithmetic/list entries) as well
# as assignments, without confusing prefixed reads with bare var:X.
_TOKEN_RE = re.compile(
    r"(?P<close>\})|(?P<anon>\{)"
    r"|(?P<key>[A-Za-z_][A-Za-z0-9_.:|@$\-]*)"
    r"(?:\s*(?:\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[A-Za-z_][A-Za-z0-9_.:@$\-]*))?)?"
)


@dataclass
class Flag:
    file: str
    line: int
    construct: str
    enclosing_iterator: str
    enclosing_line: int
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0


def _variable_key(key: str) -> bool:
    # Local/global variable lists have their own stores, independent of THIS.
    return key in VARIABLE_KEYS or (
        key.endswith("_variable_list")
        and "global_variable_list" not in key
        and "local_variable_list" not in key
    )


def _bare_var(token: str | None) -> bool:
    return bool(token and token.startswith("var:"))


def _building_scope(key: str, aliases: set[str]) -> bool:
    # A chain ending in owner/state is not itself a building scope.
    return key in BUILDING_ITERATORS or (
        "." not in key and (
            key.startswith("b:")
            or (key.startswith("scope:") and key[6:] in aliases)
        )
    )


def _scan(text: str, rel_path: str, links: set[str], aliases: set[str]):
    # Most scripts never enter a building. Skip tokenizing those, while still
    # revisiting saved-scope callers when the fixed point learns new aliases.
    if not _BUILDING_HINT.search(text) and not any(
        f"scope:{name}" in text for name in aliases
    ):
        return [], set()
    clean, comments = blank_comments_and_strings(text)
    starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]
    # Frames carry the nearest scope switch: None means unknown/non-building.
    stack: list[tuple[str, int] | None] = []
    saved: set[str] = set()
    scope_links = links | {"owner", "state"}
    flags: list[Flag] = []
    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if stack:
                stack.pop()
            continue
        current = stack[-1] if stack else None
        if m.group("anon"):
            stack.append(current)
            continue
        key, value = m.group("key"), m.group("value")
        line = bisect_right(starts, m.start("key"))
        if current:
            if key in {"save_scope_as", "save_temporary_scope_as"} and value:
                saved.add(value)
            constructs = []
            if _variable_key(key) or _bare_var(key):
                constructs.append((key, line))
            if _bare_var(value):
                constructs.append((value, bisect_right(starts, m.start("value"))))
            for construct, flag_line in constructs:
                flags.append(Flag(
                    file=rel_path, line=flag_line, construct=construct,
                    enclosing_iterator=current[0], enclosing_line=current[1],
                    exemption=_parse_reviewed(comments.get(flag_line)),
                ))
        if m.group("open"):
            if _building_scope(key, aliases):
                current = (key, line)
            elif not stack or _is_scope_change(key, scope_links):
                current = None
            stack.append(current)
    return flags, saved


def scan_text(text: str, rel_path: str, links: set[str],
              building_scopes: set[str] | None = None) -> list[Flag]:
    """Scan one script, including aliases saved anywhere in that script."""
    aliases = set(building_scopes or ())
    while True:
        flags, saved = _scan(text, rel_path, links, aliases)
        if saved <= aliases:
            return flags
        aliases.update(saved)


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """Pure file scan; mod_state is accepted for the post-load contract."""
    if mod_path is None:
        from path_constants import mod_path
    sources = []
    for sub in AUDIT_DIRS:
        for root, dirs, files in os.walk(os.path.join(mod_path, sub)):
            dirs.sort()
            for name in sorted(files):
                if name.endswith(".txt"):
                    path = os.path.join(root, name)
                    with open(path, encoding="utf-8-sig", errors="replace") as fh:
                        sources.append((os.path.relpath(path, mod_path), fh.read()))
    links = load_links(mod_path)
    aliases: set[str] = set()
    while True:
        flags = []
        saved = set()
        for path, text in sources:
            found, names = _scan(text, path, links, aliases)
            flags.extend(found)
            saved.update(names)
        if saved <= aliases:
            return AuditResult(flags=flags, files_audited=len(sources))
        aliases.update(saved)


def render_report(result: AuditResult) -> str:
    out = [
        "# Building scope variable audit report", "",
        "Auto-generated by `building_scope_variable_audit.py` on every",
        "`POST /reload` of the mod state server. Do not hand-edit.", "",
        "Buildings have no variable store. Flagged: variable operations and",
        "bare `var:X` reads inside building iterators, `b:<type>` links, or",
        "saved building scopes. Control-flow blocks inherit their scope; a",
        "scope switch out resets it. Explicitly prefixed reads are exempt.", "",
        "Saved names are inferred across scripts, including alias chains. A",
        "name saved for both buildings and other entities is conservatively",
        "treated as a possible building. Untyped roots and scripted-effect",
        "calls are not inferred. Local/global variable stores are exempt.", "",
        "Fix: store variables on a state or country and use an explicit scope",
        "link. Suppress on the flagged line with",
        "`# REVIEWED YYYY-MM-DD: rationale`.", "",
    ]
    for title, reviewed in (("Unreviewed Flags", False), ("Reviewed Exemptions", True)):
        out.extend([f"## {title}", ""])
        flags = [f for f in result.flags if bool(f.exemption) == reviewed]
        if not flags:
            out.append("_None._")
        for f in flags:
            if reviewed:
                out.append(
                    f"- `{f.file}` — `{f.construct}` inside `{f.enclosing_iterator}` — "
                    f"**{f.exemption['date']}**: {f.exemption['rationale']}"
                )
            else:
                out.append(
                    f"- `{f.file}:{f.line}` — `{f.construct}` inside "
                    f"`{f.enclosing_iterator}` (opened at line {f.enclosing_line})"
                )
        out.append("")
    out.extend([
        "## Coverage", "",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {sum(not f.exemption for f in result.flags)}",
        f"- exempted: {sum(bool(f.exemption) for f in result.flags)}", "",
    ])
    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    path = os.path.join(mod_path, "docs", "engine", "building_scope_variable_report.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    return {
        "files_audited": result.files_audited,
        "total_flags": len(result.flags),
        "unreviewed": sum(not f.exemption for f in result.flags),
        "exempted": sum(bool(f.exemption) for f in result.flags),
    }


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    result = audit()
    print(render_report(result))
    return int(args.strict and any(not f.exemption for f in result.flags))


if __name__ == "__main__":
    raise SystemExit(main())
