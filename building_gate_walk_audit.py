"""Flag a walk in a building block the weekly private investment pass reads.

The pass (the engine's tick task `HandleAutonomousInvestment`) reads the
`possible` of every building type a country has unlocked, in each of its
states, many times a week, and before it reads `can_build_private`. It reads
`potential`, `ai_value` and `can_build_private` often too. On the owner's USA
of 2024 (script profiler, one week, 2026-11-22) the busiest building's
`possible` was read 306,316 times, `ai_value` 76,668 and `can_build_private`
29,342; on their USA of 1977 the Port's `potential` 343,097. Which type is
busiest changes from save to save, and the Construction Site's cheap
`can_build_private` was read 1,321,555 times in one capture.
`can_build_government` was read at most about 2,600 times in any capture; a
building whose group is government funded at most 21,171 in any block
(Government Administration's `ai_value`).

The Deep-Sea Mine's licence gate sat in `possible` and walked every building
of every coastal state, 2.54 ms a read: 779 s of that week's 781 s tick. With
`b:` lookups it still walked the states, and cost 117 s. Moved to
`can_build_government` it was read once in eight days.
`docs/guides/scripting_best_practices.md` § "A Building's `possible` Runs in
Every State for Private Investment, Before `can_build_private`" has the rule;
`docs/audits/late_game_performance.md` § "The USA of 2024" the measurement.

What is flagged
---------------
In a building entry under the mod's `common/buildings/` (one of its own, or an
`INJECT:` / `REPLACE:` of a vanilla one), the blocks `potential`, `possible`,
`can_build_private` and `ai_value`: every iterator (`any_*`, `every_*`,
`ordered_*`, `random_*`) the block reaches, written in it or in a scripted
trigger or script value it calls, to any depth. The mod's scripted triggers and
script values are followed, and vanilla's script values from the committed
snapshot (`vanilla_parsed/common/script_values.json`). Vanilla's scripted
triggers are not followed: the snapshot has none, and CI has no game.

A walk is not wrong in itself. It is wrong where it runs on every read. One
that runs only behind a test that fails for nearly every country, or over a
handful of scopes, can stay with a comment saying so. Otherwise use the
engine's lookups (`b:<building_type>` for the state's one building of a type,
which also finds one whose levels are all queued), test something cheap first,
or move a rule only governments need to `can_build_government`, which the
pass does not read (the production lens then hides the building while it
fails).

Suppress with a trailing `# REVIEWED YYYY-MM-DD: why` on the iterator's own
line, which covers every building that reaches it, or on the block's opening
line (`possible = {`), which covers that block.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from audit_common import AuditResult as _AuditResult
from audit_common import cli_main, parse_reviewed

# The blocks the pass reads often (see the docstring for the counts).
HOT_BLOCKS = ("potential", "possible", "can_build_private", "ai_value")

ITERATOR_RE = re.compile(r"^(?:any|every|ordered|random)_[a-z_]+$")
# Keys with an iterator's prefix that walk nothing.
NOT_ITERATORS = frozenset({"random_list", "random_valid", "any_false"})

DIRECTIVE_RE = re.compile(r"^(?:INJECT|REPLACE|TRY_INJECT|TRY_REPLACE|REPLACE_OR_CREATE|INJECT_OR_CREATE):")

DEFINITION_DIRS = (os.path.join("common", "scripted_triggers"), os.path.join("common", "script_values"))
VANILLA_VALUES = os.path.join("vanilla_parsed", "common", "script_values.json")

# A comment, a line break, a quoted string, a brace, an operator, a word.
_TOKEN_RE = re.compile(r'#[^\n]*|\n|"[^"\n]*"|[{}]|\?=|[<>!=]=|[=<>]|[^\s{}=<>!?"#]+')
_OPERATORS = frozenset({"=", "?=", "==", "!=", "<", ">", "<=", ">="})
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass
class Node:
    key: str
    value: str | None
    children: list[Node] | None
    line: int


def parse(text: str) -> tuple[list[Node], dict[int, str]]:
    """The script as a tree of nodes with their lines, and each line's comment."""
    tokens: list[tuple[str, int]] = []
    comments: dict[int, str] = {}
    number = 1
    for token in _TOKEN_RE.findall(text):
        if token == "\n":
            number += 1
        elif token[0] == "#":
            comments[number] = token
        else:
            tokens.append((token, number))
    pos = 0

    def block() -> list[Node]:
        nonlocal pos
        nodes: list[Node] = []
        while pos < len(tokens):
            token, line = tokens[pos]
            pos += 1
            if token == "}":
                return nodes
            if token == "{":
                nodes.append(Node("", None, block(), line))
            elif pos < len(tokens) and tokens[pos][0] in _OPERATORS:
                pos += 1
                if pos >= len(tokens):
                    break
                value = tokens[pos][0]
                pos += 1
                if value == "{":
                    nodes.append(Node(token.strip('"'), None, block(), line))
                else:
                    nodes.append(Node(token.strip('"'), value.strip('"'), None, line))
            else:
                nodes.append(Node(token.strip('"'), None, None, line))
        return nodes

    return block(), comments


@dataclass
class Site:
    """An iterator, where it is written."""

    iterator: str
    file: str
    line: int
    exemption: dict | None


@dataclass
class Definition:
    nodes: list[Node] | None
    file: str
    comments: dict[int, str]
    vanilla: object = None  # a parsed snapshot entry, for a vanilla script value


@dataclass
class Flag:
    file: str
    line: int  # the block's opening line
    building: str
    block: str
    iterator: str
    site_file: str
    site_line: int
    via: tuple[str, ...]
    exemption: dict | None = None

    @property
    def message(self) -> str:
        where = f"`{self.site_file}:{self.site_line}`"
        path = " → ".join(self.via)
        return (f"`{self.building}` `{self.block}` reaches `{self.iterator}` at {where}"
                + (f" through `{path}`" if path else ""))


@dataclass
class AuditResult(_AuditResult):
    blocks_audited: int = 0


def _read(path: str) -> str:
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


def _words(node: Node):
    """Every name a node's key or scalar value mentions (`a.b` gives both)."""
    for text in (node.key, node.value):
        if text:
            yield from _WORD_RE.findall(text)


def load_definitions(mod_path: str) -> dict[str, Definition]:
    """Vanilla's script values from the snapshot, then the mod's scripted
    triggers and script values over them."""
    found: dict[str, Definition] = {}
    snapshot = os.path.join(mod_path, VANILLA_VALUES)
    if os.path.isfile(snapshot):
        with open(snapshot, encoding="utf-8-sig") as fh:
            for name, entry in json.load(fh).items():
                found[name] = Definition(None, "vanilla:common/script_values", {}, vanilla=entry)
    for sub in DEFINITION_DIRS:
        directory = os.path.join(mod_path, sub)
        if not os.path.isdir(directory):
            continue
        for fname in sorted(os.listdir(directory)):
            if not fname.endswith(".txt"):
                continue
            rel = os.path.join(sub, fname)
            nodes, comments = parse(_read(os.path.join(directory, fname)))
            for node in nodes:
                if node.children is not None and node.key:
                    found[DIRECTIVE_RE.sub("", node.key)] = Definition(node.children, rel, comments)
    return found


def _vanilla_walks(entry, file: str) -> tuple[list[str], list[str]]:
    """(iterators, names) mentioned anywhere in a parsed snapshot entry."""
    iterators: list[str] = []
    names: list[str] = []

    def visit(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if ITERATOR_RE.match(key) and key not in NOT_ITERATORS:
                    iterators.append(key)
                names.extend(_WORD_RE.findall(key))
                visit(value)
        elif isinstance(obj, list):
            for item in obj:
                visit(item)
        elif isinstance(obj, str):
            names.extend(_WORD_RE.findall(obj))

    visit(entry)
    return iterators, names


class Walker:
    """The iterators a body reaches, each with the call path to it."""

    def __init__(self, definitions: dict[str, Definition]):
        self.definitions = definitions
        self.memo: dict[str, list[tuple[Site, tuple[str, ...]]]] = {}

    def nodes(self, nodes: list[Node], file: str, comments: dict[int, str],
              seen: frozenset[str]) -> list[tuple[Site, tuple[str, ...]]]:
        found: list[tuple[Site, tuple[str, ...]]] = []
        for node in nodes:
            if ITERATOR_RE.match(node.key) and node.key not in NOT_ITERATORS:
                found.append((Site(node.key, file, node.line, parse_reviewed(comments.get(node.line))), ()))
            for name in _words(node):
                found += self.call(name, seen)
            if node.children:
                found += self.nodes(node.children, file, comments, seen)
        return found

    def call(self, name: str, seen: frozenset[str]) -> list[tuple[Site, tuple[str, ...]]]:
        definition = self.definitions.get(name)
        if definition is None or name in seen:
            return []
        if name not in self.memo:
            self.memo[name] = []  # a cycle reads as no walk
            if definition.nodes is not None:
                inner = self.nodes(definition.nodes, definition.file, definition.comments, seen | {name})
            else:
                iterators, names = _vanilla_walks(definition.vanilla, definition.file)
                inner = [(Site(it, definition.file, 0, None), ()) for it in iterators]
                for other in names:
                    inner += self.call(other, seen | {name})
            self.memo[name] = [(site, (name,) + via) for site, via in inner]
        return self.memo[name]


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_AUDITS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    walker = Walker(load_definitions(mod_path))
    flags: list[Flag] = []
    blocks = 0
    directory = os.path.join(mod_path, "common", "buildings")
    for fname in sorted(os.listdir(directory)) if os.path.isdir(directory) else ():
        if not fname.endswith(".txt"):
            continue
        rel = os.path.join("common", "buildings", fname)
        nodes, comments = parse(_read(os.path.join(directory, fname)))
        for entry in nodes:
            if entry.children is None or not entry.key:
                continue
            for child in entry.children:
                block = DIRECTIVE_RE.sub("", child.key)
                if block not in HOT_BLOCKS:
                    continue
                blocks += 1
                if child.children is not None:
                    reached = walker.nodes(child.children, rel, comments, frozenset())
                else:
                    reached = [hit for name in _words(Node("", child.value, None, child.line))
                               for hit in walker.call(name, frozenset())]
                opener = parse_reviewed(comments.get(child.line))
                done: set[tuple] = set()
                for site, via in reached:
                    key = (site.iterator, site.file, site.line, via)
                    if key in done:
                        continue
                    done.add(key)
                    flags.append(Flag(rel, child.line, entry.key, block, site.iterator, site.file,
                                      site.line, via, site.exemption or opener))
    return AuditResult(flags=flags, blocks_audited=blocks)


TITLE = "Building gate walk audit report"
INTRO = (
    "Flagged: an iterator that a mod building's `potential`, `possible`, `can_build_private` or "
    "`ai_value` reaches, directly or through scripted triggers and script values. The weekly private "
    "investment pass reads these blocks some 300,000 times a week for its busiest type (measured "
    "2026-11-19 and 2026-11-22): a walk there runs that often unless something cheap fails first."
)


def render_report(result: AuditResult) -> str:
    """The standard report, but each reviewed walk once, with how many blocks
    reach it, and no line numbers there (an edit above one would churn the
    report): the 314 company flagships share two walks."""
    import audit_registry
    out = [f"# {TITLE}", "", "Auto-generated by `building_gate_walk_audit.py`. Do not hand-edit.", "",
           INTRO, ""]
    hint = audit_registry.suppression_hint("building_gate_walk_audit").strip().splitlines()
    out += [line + "  " for line in hint[:-1]] + hint[-1:] + ["", "## Unreviewed flags", ""]
    unreviewed = result.unreviewed
    out += [f"- `{f.file}:{f.line}`: {f.message}" for f in unreviewed] or ["_None._"]
    out += ["", "## Reviewed walks", ""]
    groups: dict[tuple, list[Flag]] = {}
    for f in result.exemptions:
        groups.setdefault((f.site_file, f.iterator, f.exemption["date"], f.exemption["rationale"]), []).append(f)
    if not groups:
        out.append("_None._")
    for (site_file, iterator, date, why), members in sorted(groups.items()):
        names = sorted({f"`{f.building}` `{f.block}`" for f in members})
        shown = ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")
        out.append(f"- `{iterator}` in `{site_file}`, reached from {shown} — **{date}**: {why}")
    out += ["", "## Coverage", "",
            f"- blocks audited: {result.blocks_audited}",
            f"- total flags: {len(result.flags)}",
            f"- unreviewed: {len(unreviewed)}",
            f"- exempted: {len(result.exemptions)}",
            f"- reviewed walks: {len(groups)}", ""]
    return "\n".join(out)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from audit_common import summary, write_text
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    write_text(os.path.join(mod_path, "docs", "engine", "building_gate_walk_report.md"), render_report(result))
    return summary(result, blocks_audited=result.blocks_audited)


def main(argv=None) -> int:
    """Print the report; `--strict` (CI) exits 1 on an unreviewed flag."""
    from path_constants import mod_path
    return cli_main(lambda args: audit(mod_path=mod_path), lambda result, args: render_report(result),
                    argv=argv, description=__doc__.splitlines()[0])


if __name__ == "__main__":
    raise SystemExit(main())
