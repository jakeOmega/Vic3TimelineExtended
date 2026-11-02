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
    `blockoverride "x" {…}`, "widget" for `name = {…}`, and "property" for
    `key = value`. A one-line `x = { … }` is a property when it holds only
    numbers (size = { 480 32 }, margin = { 10 6 }), else a widget."""
    items = []
    i = 0
    pattern = re.compile(r'\s*(?:(block|blockoverride) "(\w+)" \{|(\w+) = \{|(\w+) = ("(?:[^"\\]|\\.)*"|[^\s{}"]+))')
    while i < len(body):
        m = pattern.match(body, i)
        if not m or m.end() == i:
            rest = body[i:].strip()
            assert not rest, f"unparsed: {rest[:60]}"
            break
        if m.group(2) or m.group(3):
            end = _close(body, m.end() - 1)
            inner = body[m.end():end]
            if m.group(3) and "\n" not in inner and inner.strip() and re.fullmatch(r"[\s\d.%-]*", inner):
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


def _split_args(inner):
    """A call's arguments, split at its top-level commas."""
    out, depth, start = [], 0, 0
    for i, ch in enumerate(inner):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            out.append(inner[start:i])
            start = i + 1
    return out + [inner[start:]]


def _gates(value):
    """A visible's expression, for comparing: no quotes, no brackets, no
    spacing, and a top-level And( a, b ) as its two parts."""
    expr = re.sub(r"\s+", "", value.strip().strip('"'))
    if expr.startswith("[") and expr.endswith("]"):
        expr = expr[1:-1]
    if expr.startswith("And(") and expr.endswith(")") and _close(expr.replace("(", "{").replace(")", "}"), 3) == len(expr) - 1:
        return tuple(g for arg in _split_args(expr[4:-1]) for g in _gates(arg))
    return (expr,)


def _own_gates(items):
    return tuple(g for kind, k, v in items if kind == "property" and k == "visible" for g in _gates(v))


# The plain containers a layout may wrap its sections in. Any other widget
# drawn in a layout is content the check can't follow: make it a te_* section.
WRAPPERS = {"flowcontainer", "widget", "vbox", "hbox", "container"}

# What a wrapper in a wide layout may carry: it gates and spaces its sections,
# nothing else (no datacontext, margin, position or size of its own).
WIDE_WRAPPER_PROPS = {"direction", "parentanchor", "ignoreinvisible", "spacing", "minimumsize", "maximumsize", "name",
                      "visible"}


def _find_block(body, name):
    """The content of `block "name"` anywhere in a body, or None."""
    for kind, n, inner in _children(body):
        if kind == "block" and n == name:
            return inner
        if kind in ("block", "blockoverride", "widget"):
            found = _find_block(inner, name)
            if found is not None:
                return found
    return None


class _Walk:
    """The sections a layout places, in the order they draw, each with the
    gates (visible expressions) on its way down, and whether it sits in a
    column; and its columns, if any. A composer instance expands into its
    type's sections, under the instance's blockoverrides."""

    def __init__(self, test, where, text, composers, skip=(), narrow_spacing=None):
        self.test, self.where, self.text = test, where, text
        self.composers, self.skip = composers, set(skip)
        self.sections, self.columns, self.skipped = [], [], set()
        # the narrow side records each gated level's spacing, by the gates down to it;
        # the wide side checks its wrappers against that record
        self.narrow_spacing = narrow_spacing
        self.spacing = {}

    def is_composer(self, name):
        return name in self.composers if self.composers is not None else name.endswith("_sections")

    def body(self, body, gates, overrides=None, wrapper=None):
        items = _children(body)
        own = _own_gates(items)
        gates = gates + own
        props = {k: v for kind, k, v in items if kind == "property"}
        if own and self.narrow_spacing is None:
            self.spacing.setdefault(frozenset(gates), set()).add(props.get("spacing"))
        if wrapper and self.narrow_spacing is not None:
            self.check_wrapper(wrapper, props, own, gates)
        for kind, name, inner in items:
            if kind == "block":                       # a block draws its override, or its default content
                self.body(overrides[name] if overrides and name in overrides else inner, gates, overrides)
            elif kind == "blockoverride":
                self.body(inner, gates, overrides)
            elif kind != "widget":
                continue
            elif name in COLUMN_TYPES:
                self.columns_of(name, inner, gates)
            elif name.startswith("te_"):
                self.instance(name, inner, gates)
            elif name in WRAPPERS:
                self.body(inner, gates, overrides, wrapper=name)
            else:
                self.test.fail(f"{self.where} draws {name} inline: make it a te_* section type, so the check can "
                               f"follow it")

    def check_wrapper(self, name, props, own, gates):
        extra = sorted(set(props) - WIDE_WRAPPER_PROPS)
        self.test.assertFalse(extra, f"{self.where}: a wrapper carries {extra}; a wide layout's wrappers only gate and "
                                     f"space their sections")
        self.test.assertEqual(props.get("ignoreinvisible"), "yes",
                              f"{self.where}: a wrapper without ignoreinvisible = yes keeps a hidden section's space")
        if name == "flowcontainer":
            self.test.assertEqual(props.get("direction"), "vertical",
                                  f"{self.where}: a flowcontainer wrapper runs vertically in its column")
        narrow = self.narrow_spacing.get(frozenset(gates))
        if own and narrow is not None:
            self.test.assertIn(props.get("spacing"), narrow,
                               f"{self.where}: a wrapper spaces its sections {props.get('spacing')} apart under "
                               f"{sorted(set(gates))}, the narrow layout {sorted(narrow, key=str)}")

    def type_gates(self, name):
        """A type's own root visible, or () when it has none or isn't found."""
        if not re.search(rf"\btype {name} = \w+ \{{", self.text):
            return ()
        return _own_gates(_children(_type_body(self.text, name)))

    def instance(self, name, own, gates):
        items = _children(own)
        mine = _own_gates(items)
        if mine and self.type_gates(name):
            self.test.fail(f"{self.where}: {name}'s visible replaces its type's own (gotcha #17), so it draws where "
                           f"its own gate hides it; gate a wrapper instead")
        gates = gates + mine
        if name in self.skip:
            self.skipped.add(name)
        elif self.is_composer(name):
            filled = {n: inner for kind, n, inner in items if kind == "blockoverride"}
            self.body(_type_body(self.text, name), gates, filled)
        else:
            in_column = bool(self.columns) and self.columns[-1] is not None
            self.sections.append((name, gates, in_column))
            if in_column:
                self.columns[-1].append(name)

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


def assert_wide_matches_narrow(test, wide_type, narrow_types=(), *, layout=None, extra=(), outside=(),
                               added_gates=(), composers=None, text=None):
    """Check a wide composer against the narrow layout it widens, and return
    its columns (a list of section-name lists, read down each column).

    - The narrow layout is either `narrow_types`, its types in order, or
      `layout=(body_type, block_name)`, the tab body's layout block (for
      example ("te_un_tab_body", "te_un_tab_layout")), read with its inline
      wrappers and the blockoverrides it gives its composers. Give one.
    - A composer (named in `composers`, by default each type named
      *_sections) expands into the sections it places, through its plain
      wrappers (flowcontainer, widget, vbox, hbox, container) and blocks, on
      either side; any other te_* instance is a section. Any other widget
      drawn inline fails: make it a te_* section.
    - The wide composer, `wide_type`, must lay its sections out on
      te_ui_columns_three or te_ui_columns_two (spec § 9.4) and place exactly
      the narrow sections, in the same order read down each column and then
      across. Every column holds at least one section. A section outside the
      columns (the Census Data window's pending line) must be named in
      `outside`, and counts where it draws.
    - `extra` names wide-only te_* instances to skip.
    - Each section sits under exactly the gates the narrow layout gives it (a
      composer's or a wrapper's visible, or the instance's own; an And( a, b )
      counts as a and b), on the instance, a wrapper, the column type's
      instance or the wide composer's root. A section named in `added_gates`
      may carry more (the Census Data window's How waits for the first
      census). An instance's visible over a type's own fails either way: in
      game it replaces the type's (gotcha #17).
    - A wrapper in the wide layout only gates and spaces its sections: it
      carries nothing but direction, parentanchor, ignoreinvisible = yes,
      spacing, a size limit, a name and its visible; a flowcontainer runs
      vertically; and one under the same gates as a narrow composer or wrapper
      spaces its sections as that one does.
    - A name in `extra`, `outside` or `added_gates` that no longer applies
      fails, so a stale one can't hide a change.

    `text` is the markup to read the types from: by default every mod .gui.
    """
    test.assertTrue(bool(narrow_types) != bool(layout), "give narrow_types or layout, not both")
    text = _all_gui() if text is None else _strip_comments(text)
    composers = set(composers) if composers is not None else None

    narrow = _Walk(test, "the narrow layout", text, composers)
    if layout:
        body_type, block_name = layout
        block = _find_block(_type_body(text, body_type), block_name)
        test.assertIsNotNone(block, f"{body_type} has no block {block_name}")
        narrow.body(block, ())
    else:
        for name in narrow_types:
            narrow.instance(name, "", ())

    m = re.search(rf"\btype {wide_type} = (\w+) \{{", text)
    test.assertIsNotNone(m, f"no type {wide_type}")
    wide = _Walk(test, wide_type, text, composers, skip=extra, narrow_spacing=narrow.spacing)
    if m.group(1) in COLUMN_TYPES:
        wide.columns_of(m.group(1), _type_body(text, wide_type), ())
    else:
        wide.body(_type_body(text, wide_type), ())
    test.assertTrue(wide.columns, f"{wide_type} lays its sections out on te_ui_columns_three or te_ui_columns_two")
    stale = set(extra) - wide.skipped
    test.assertFalse(stale, f"{wide_type}: extra names {sorted(stale)}, which it doesn't place")

    test.assertEqual([s for s, _, _ in wide.sections], [s for s, _, _ in narrow.sections],
                     f"{wide_type}: the narrow layout's sections, read down each column and then across")
    out = [s for s, _, in_column in wide.sections if not in_column]
    test.assertFalse(sorted(set(out) - set(outside)),
                     f"{wide_type} places {sorted(set(out) - set(outside))} outside its columns; name each in outside")
    stale = set(outside) - set(out)
    test.assertFalse(stale, f"{wide_type}: outside names {sorted(stale)}, which it doesn't place outside its columns")

    further = set()
    for (section, narrow_gates, _), (_, wide_gates, _) in zip(narrow.sections, wide.sections):
        missing = sorted(set(narrow_gates) - set(wide_gates))
        test.assertFalse(missing, f"{wide_type}: {section} shows in the narrow layout only while {missing}, "
                                  f"but in the wide one without it")
        more = sorted(set(wide_gates) - set(narrow_gates))
        if more:
            further.add(section)
            test.assertIn(section, added_gates, f"{wide_type}: {section} shows in the wide layout only while {more}, "
                                                f"but in the narrow one without it; name it in added_gates if meant")
    stale = set(added_gates) - further
    test.assertFalse(stale, f"{wide_type}: added_gates names {sorted(stale)}, which the wide layout gates no further")
    return [c for c in wide.columns if c is not None]
