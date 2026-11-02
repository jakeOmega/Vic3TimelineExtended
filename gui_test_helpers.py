"""Helpers the GUI tests share (spec
docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md § 9.5).

Not a test file (no test_ prefix), so neither pytest nor unittest collects it.
Existing tests move onto it only when they are next touched, not in a sweep.

- _read, _strip_comments, _close, _block_at, _type_body, _children and
  _instances read Paradox GUI markup.
"""
import re


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _strip_comments(text):
    """The text with each line's comment cut, a # inside a string kept."""
    out = []
    for line in text.split("\n"):
        quoted = False
        for i, ch in enumerate(line):
            if ch == '"':
                quoted = not quoted
            elif ch == "#" and not quoted:
                line = line[:i]
                break
        out.append(line)
    return "\n".join(out)


def _close(text, open_brace):
    """The index of the brace that closes the one at (or first after) open_brace."""
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def _block_at(text, start):
    """The block whose opening brace is the first after `start`, braces included."""
    brace = text.index("{", start)
    return text[start:_close(text, brace) + 1]


def _type_body(text, name):
    """A type's body, between its braces."""
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    return text[m.end():_close(text, m.end() - 1)]


def _children(body):
    """The top-level items of a block's body, in order: (kind, name, text).
    kind is "block" for `block "x" {…}`, "widget" for `name = {…}`, and
    "property" for a one-line `key = value` (a one-line `x = { … }` too)."""
    items = []
    i = 0
    while i < len(body):
        m = re.compile(r'\s*(?:block "(\w+)" \{|(\w+) = \{|(\w+) = ([^\n{]+))').match(body, i)
        if not m or m.end() == i:
            rest = body[i:].strip()
            assert not rest, f"unparsed: {rest[:60]}"
            break
        if m.group(1) or m.group(2):
            end = _close(body, m.end() - 1)
            inner = body[m.end():end]
            if m.group(2) and "\n" not in inner:    # a one-line value: size = { 480 32 }
                items.append(("property", m.group(2), "{" + inner + "}"))
            else:
                items.append(("block" if m.group(1) else "widget", m.group(1) or m.group(2), inner))
            i = end + 1
        else:
            items.append(("property", m.group(3), m.group(4).strip()))
            i = m.end()
    return items


def _instances(text):
    """The te_* types a block instances, in order (one level or deeper)."""
    return re.findall(r"^\t+(te_\w+) = \{", text, re.M)
