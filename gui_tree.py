"""A light block tree of a `.gui` file, for the offline GUI audits (#1213).

`long_tooltip_audit`, `unmarked_hover_audit` and `button_reason_audit` need
more than a regex over the text: which widget a property sits in, what its
ancestors are, and what a type's definition holds. This module reads a
`.gui` file into a tree of brace blocks, each with its direct `key = value`
properties, and nothing more. It does not know widget semantics: a node is
whatever opened a brace.

Openers it recognises (comments are dropped first; a `#` or a brace inside a
quoted string is text, through `gui_reference_audit.masks`):

- `type NAME = BASE {`: a type definition (`kind` is `type`, `name` NAME,
  `base` BASE)
- `block "NAME" {` and `blockoverride "NAME" {` (`kind` `block` or
  `blockoverride`, `name` NAME)
- `types NAME {` and `template NAME {` (`kind` the keyword, `name` NAME)
- `KEY = {`: a widget, a type instance or a compound property (`kind` KEY)
- a bare `{` (`kind` empty)

Everything else of the form `KEY = VALUE` is a property of the innermost
node, with the quotes taken off a quoted value. A bare token inside a block
(`size = { 100 20 }`) is kept in `values`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from gui_reference_audit import masks

_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|[{}=]|[^\s{}="]+')


@dataclass
class Prop:
    key: str
    value: str
    line: int
    quoted: bool


@dataclass(eq=False)
class Node:
    kind: str
    name: str = ""
    base: str = ""
    line: int = 0
    end_line: int = 0
    parent: Node | None = None
    props: list[Prop] = field(default_factory=list)
    children: list[Node] = field(default_factory=list)
    values: list[str] = field(default_factory=list)

    def prop(self, key: str) -> Prop | None:
        """The last direct property `key` (the engine keeps the last one)."""
        found = None
        for p in self.props:
            if p.key == key:
                found = p
        return found

    def walk(self):
        """This node and every node under it, depth first, in source order."""
        yield self
        for child in self.children:
            yield from child.walk()

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    @property
    def label(self) -> str:
        """How the report names the node: `type foo`, `blockoverride "x"`, `textbox`."""
        if self.kind in ("block", "blockoverride"):
            return f'{self.kind} "{self.name}"'
        if self.name:
            return f"{self.kind} {self.name}"
        return self.kind or "{ }"


def _unquote(token: str) -> tuple[str, bool]:
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        return token[1:-1], True
    return token, False


def parse(text: str) -> Node:
    """The block tree of one `.gui` file's text (BOM already removed)."""
    code = masks(text)[0]
    tokens = [(m[0], m.start()) for m in _TOKEN.finditer(code)]
    line_at: list[int] = []
    line = 1
    pos = 0

    def lineno(offset: int) -> int:
        nonlocal line, pos
        if offset >= pos:
            line += code.count("\n", pos, offset)
        else:
            line = code.count("\n", 0, offset) + 1
        pos = offset
        return line

    for _, offset in tokens:
        line_at.append(lineno(offset))

    root = Node(kind="<file>", line=1)
    stack = [root]
    n = len(tokens)

    def tok(i: int) -> str:
        return tokens[i][0] if i < n else ""

    def open_node(i: int, kind: str, name: str = "", base: str = "") -> None:
        node = Node(kind=kind, name=name, base=base, line=line_at[i], parent=stack[-1])
        stack[-1].children.append(node)
        stack.append(node)

    i = 0
    while i < n:
        t = tok(i)
        if t == "}":
            if len(stack) > 1:
                stack[-1].end_line = line_at[i]
                stack.pop()
            i += 1
        elif t == "{":
            open_node(i, "")
            i += 1
        elif t == "=":
            i += 1
        elif t == "type" and tok(i + 2) == "=" and tok(i + 4) == "{":
            open_node(i, "type", tok(i + 1), tok(i + 3))
            i += 5
        elif t in ("block", "blockoverride") and tok(i + 1).startswith('"') and tok(i + 2) == "{":
            open_node(i, t, _unquote(tok(i + 1))[0])
            i += 3
        elif tok(i + 1) == "=":
            value = tok(i + 2)
            if value == "{":
                open_node(i, t)
            elif value not in ("", "}", "="):
                v, quoted = _unquote(value)
                stack[-1].props.append(Prop(t, v, line_at[i], quoted))
            i += 3
        elif tok(i + 1) not in ("", "{", "}", "=") and tok(i + 2) == "{" and not t.startswith('"'):
            open_node(i, t, _unquote(tok(i + 1))[0])
            i += 3
        elif tok(i + 1) == "{" and not t.startswith('"'):
            open_node(i, t)
            i += 2
        else:
            stack[-1].values.append(_unquote(t)[0])
            i += 1
    for node in stack[1:]:
        node.end_line = line_at[-1] if line_at else node.line
    root.end_line = text.count("\n") + 1
    return root


def parse_file(path: Path) -> Node:
    return parse(path.read_text(encoding="utf-8-sig", errors="replace"))


def gui_files(root: Path):
    """The mod's `.gui` files, sorted."""
    yield from sorted((root / "gui").rglob("*.gui"))


def type_index(trees: dict[str, Node]) -> dict[str, Node]:
    """Every `type NAME = BASE { }` in the given trees, by name. A later file
    (in sorted order) replaces an earlier one, as the engine's last-loaded
    definition wins."""
    out: dict[str, Node] = {}
    for rel in sorted(trees):
        for node in trees[rel].walk():
            if node.kind == "type" and node.name:
                out[node.name] = node
    return out


def base_chain(kind: str, types: dict[str, Node], limit: int = 20) -> list[str]:
    """`kind`, then the base of each mod type it derives from, in order:
    `nd_row` -> [`nd_row`, `flowcontainer`]. A vanilla type ends the chain."""
    chain = [kind]
    while kind in types and len(chain) < limit:
        kind = types[kind].base
        if kind in chain:
            break
        chain.append(kind)
    return chain


_HOW_TOKEN = re.compile(r"(?:^|_)(?:how|help)(?:_|$)", re.I)
_HOW_TOGGLE = re.compile(r"GetVariableSystem\.Exists\(\s*'([^']*)'\s*\)")


def how_named(name: str) -> bool:
    """A name with a `how` or `help` token: `te_un_sec_how`, `te_un_help_standing`."""
    return bool(_HOW_TOKEN.search(name or ""))


def opens_how_section(node: Node) -> bool:
    """A node a How-it-works section is made of: named for one (`type
    te_demog_sec_how`, an instance `te_un_help_standing = {}`), or shown only
    while a How toggle is open (`visible = "[GetVariableSystem.Exists(
    'un_how_open')]"`). Every How section in the mod has that toggle, named
    `<system>_how_open` (style rule 7), so the toggle catches a topic whose
    own names don't say How (the UN's `je_un_chamber_missions_help`)."""
    if how_named(node.name) or (node.kind not in ("", "block", "blockoverride") and how_named(node.kind)):
        return True
    visible = node.prop("visible")
    if visible is None:
        return False
    value = visible.value.replace(" ", "")
    if value.startswith("[Not("):
        return False
    return any(how_named(flag) for flag in _HOW_TOGGLE.findall(visible.value))


def in_how_section(node: Node) -> bool:
    return opens_how_section(node) or any(opens_how_section(a) for a in node.ancestors())
