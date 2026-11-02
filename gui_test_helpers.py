"""Helpers the GUI tests share (spec
docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md § 9.5).

Not a test file (no test_ prefix), so neither pytest nor unittest collects it.
Existing tests move onto it only when they are next touched, not in a sweep.

- _read, _strip_comments, _close, _block_at, _type_body, _children and
  _instances read Paradox GUI markup.
- assert_wide_matches_narrow checks a wide composer against its narrow ones.
"""
import functools
import glob
import os
import re

REPO = os.path.dirname(os.path.abspath(__file__))


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
    kind is "block" for `block "x" {…}`, "blockoverride" for
    `blockoverride "x" {…}`, "widget" for `name = {…}`, and "property" for a
    one-line `key = value` (a one-line `x = { … }` too)."""
    items = []
    i = 0
    while i < len(body):
        m = re.compile(r'\s*(?:(block|blockoverride) "(\w+)" \{|(\w+) = \{|(\w+) = ([^\n{]+))').match(body, i)
        if not m or m.end() == i:
            rest = body[i:].strip()
            assert not rest, f"unparsed: {rest[:60]}"
            break
        if m.group(2) or m.group(3):
            end = _close(body, m.end() - 1)
            inner = body[m.end():end]
            if m.group(3) and "\n" not in inner:    # a one-line value: size = { 480 32 }
                items.append(("property", m.group(3), "{" + inner + "}"))
            else:
                items.append((m.group(1) or "widget", m.group(2) or m.group(3), inner))
            i = end + 1
        else:
            items.append(("property", m.group(4), m.group(5).strip()))
            i = m.end()
    return items


def _instances(text):
    """The te_* types a block instances, in order (one level or deeper)."""
    return re.findall(r"^\t+(te_\w+) = \{", text, re.M)


# The shared column types (gui/te_widget_library.gui) and their column counts.
COLUMN_TYPES = {"te_ui_columns_three": 3, "te_ui_columns_two": 2}


@functools.lru_cache(maxsize=1)
def _all_gui():
    """Every mod .gui file, comments cut, one after another."""
    paths = sorted(glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True))
    return "\n".join(_strip_comments(_read(p)) for p in paths)


def _gate(value):
    """A visible's expression, for comparing: no quotes, no spacing."""
    return re.sub(r"\s+", "", value.strip().strip('"'))


def _own_gates(items):
    return tuple(_gate(v) for kind, k, v in items if kind == "property" and k == "visible")


def _instance(kind, name, inner):
    """A te_* instance's body, or None. A one-line `te_x = {}` parses as a property."""
    if not name.startswith("te_"):
        return None
    if kind == "widget":
        return inner
    if kind == "property" and inner.startswith("{"):
        return inner[1:-1]
    return None


class _Walk:
    """The sections a composer places, in the order they draw, each with the
    gates (visible expressions) on its way down; and the columns, if any."""

    def __init__(self, test, where, skip=()):
        self.test, self.where, self.skip = test, where, set(skip)
        self.sections, self.columns, self.skipped = [], [], set()

    def body(self, body, gates):
        items = _children(body)
        gates = gates + _own_gates(items)
        for kind, name, inner in items:
            if kind in ("block", "blockoverride"):    # a block's default content draws in place
                self.body(inner, gates)
                continue
            if name in COLUMN_TYPES:
                self.columns_of(name, inner, gates)
                continue
            own = _instance(kind, name, inner)
            if own is not None:
                if name in self.skip:
                    self.skipped.add(name)
                else:
                    self.sections.append((name, gates + _own_gates(_children(own))))
                    if self.columns and self.columns[-1] is not None:
                        self.columns[-1].append(name)
            elif kind == "widget":                    # a plain wrapper: flowcontainer, widget, …
                self.body(inner, gates)

    def columns_of(self, column_type, body, gates):
        n = COLUMN_TYPES[column_type]
        items = _children(body)
        gates = gates + _own_gates(items)
        filled = {name: inner for kind, name, inner in items if kind == "blockoverride"}
        others = [name for kind, name, _ in items if kind != "blockoverride" and not (kind == "property" and name == "visible")]
        self.test.assertEqual(others, [], f"{self.where}: a {column_type} holds only its visible and its column blocks")
        self.test.assertEqual(sorted(filled), [f"column_{i}" for i in range(1, n + 1)],
                              f"{self.where}: {column_type} fills column_1 to column_{n}, each once")
        for i in range(1, n + 1):
            self.columns.append([])
            self.body(filled[f"column_{i}"], gates)
            self.test.assertTrue(self.columns[-1], f"{self.where}: column_{i} is empty, but keeps its 520; "
                                                   f"two columns of content take te_ui_columns_two")
            self.columns.append(None)                 # a section after the columns sits in none


def assert_wide_matches_narrow(test, wide_type, narrow_types, *, extra=(), omit=(), composers=None, text=None):
    """Check a wide composer against the narrow layout it widens, and return
    its columns (a list of section-name lists, read down each column).

    - narrow_types: the narrow layout in order, as its tab body lists it. A
      composer among them (named in `composers`, by default each one named
      *_sections) expands into the sections it places, through its plain
      wrappers and blocks; any other name is a section.
    - The wide composer, `wide_type`, must lay its sections out on
      te_ui_columns_three or te_ui_columns_two (spec § 9.4) and place exactly
      the narrow sections, in the same order read down each column and then
      across. A section outside the columns (the Census Data window's pending
      line) counts where it draws. Every column holds at least one section.
    - `extra` names wide-only te_* instances to skip, and `omit` narrow
      sections the wide layout places elsewhere (Tax Code's draft summary is
      in the window's footer). Each must still be there, so a stale one fails.
    - Every gate the narrow layout puts on a section (a composer's or a
      wrapper's visible, or the instance's own) is on the wide section's way
      down too: on the instance, a wrapper, the column type's instance or the
      wide composer's root. The wide layout may add gates.

    `text` is the markup to read the types from: by default every mod .gui.
    """
    text = _all_gui() if text is None else _strip_comments(text)
    composers = set(composers) if composers is not None else {n for n in narrow_types if n.endswith("_sections")}

    narrow = _Walk(test, "the narrow layout")
    for name in narrow_types:
        if name in composers:
            narrow.body(_type_body(text, name), ())
        else:
            narrow.sections.append((name, ()))
    stale = set(omit) - {s for s, _ in narrow.sections}
    test.assertFalse(stale, f"{wide_type}: omit names {sorted(stale)}, which the narrow layout doesn't place")
    narrow_sections = [(s, g) for s, g in narrow.sections if s not in omit]

    m = re.search(rf"\btype {wide_type} = (\w+) \{{", text)
    test.assertIsNotNone(m, f"no type {wide_type}")
    wide = _Walk(test, wide_type, skip=extra)
    if m.group(1) in COLUMN_TYPES:
        wide.columns_of(m.group(1), _type_body(text, wide_type), ())
    else:
        wide.body(_type_body(text, wide_type), ())
    test.assertTrue(wide.columns, f"{wide_type} lays its sections out on te_ui_columns_three or te_ui_columns_two")
    stale = set(extra) - wide.skipped
    test.assertFalse(stale, f"{wide_type}: extra names {sorted(stale)}, which it doesn't place")

    test.assertEqual([s for s, _ in wide.sections], [s for s, _ in narrow_sections],
                     f"{wide_type}: the narrow layout's sections, read down each column and then across")
    for (section, narrow_gates), (_, wide_gates) in zip(narrow_sections, wide.sections):
        missing = sorted(set(narrow_gates) - set(wide_gates))
        test.assertFalse(missing, f"{wide_type}: {section} shows in the narrow layout only while {missing}, "
                                  f"but in the wide one without it")
    return [c for c in wide.columns if c is not None]
