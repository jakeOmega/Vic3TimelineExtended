"""Helpers the GUI tests share (spec
docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md § 9.5).

Not a test file (no test_ prefix), so neither pytest nor unittest collects it.
Existing tests move onto it only when they are next touched, not in a sweep.

- _read, _strip_comments, _close, _block_at, _type_body, _children and
  _instances read Paradox GUI markup.
- assert_wide_matches_narrow checks a wide composer against its narrow ones.
- history_charts gives the history charts a section instances, from the
  generated wrappers (scripts/generators/gen_te_history_charts.py).
- load_loc, loc_index, gui_keys, loc_closure and type_bodies read the loc a
  panel reaches (moved from test_demographics_census_window.py).
- mod_types and type_closure give the types a panel draws, all the way down;
  guard_spans and open_types the parts of them another country sees (charts-
  help-national-info plan, PR F0; test_te_system_tab_bodies.py's BindingTest).
"""
import bisect
from dataclasses import dataclass, field
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
# A wide layout's own wrappers are flowcontainers only (_Walk.check_wrapper).
WRAPPERS = {"flowcontainer", "widget", "vbox", "hbox", "container"}

# What a wrapper in a wide layout may carry: it gates and spaces its sections,
# nothing else (no datacontext, margin, position or size of its own).
WIDE_WRAPPER_PROPS = {"direction", "parentanchor", "ignoreinvisible", "spacing", "minimumsize", "maximumsize", "name",
                      "visible"}

# The one size limit a wide wrapper may carry: a column's width, any height.
COLUMN_SIZE = ["520", "-1"]

# The spacing of a widget the check can't read: the one around a tab body's
# layout block (the frame's), or a column's (the column type's).
_UNKNOWN = object()


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


class _Filled(dict):
    """An instance's blockoverrides, by block name, and how deep in shared
    composers (_Walk.shared) the instance sits: an override is the markup of
    the layout that writes it, wherever the block it fills draws."""
    shared = 0


class _Walk:
    """The sections a layout places, in the order they draw, each with the
    gates (visible expressions) on its way down, and whether it sits in a
    column; and its columns, if any. A composer instance expands into its
    type's sections, under the instance's blockoverrides.

    The narrow side (`narrow` None) also records the spacing each te_*
    instance sits at (that of the nearest widget around it that holds two or
    more, since one that holds a single child draws no spacing), and the
    composers it expands. The wide side (`narrow` the narrow walk) holds its
    own wrappers and instances to the rules in assert_wide_matches_narrow's
    docstring. Inside a composer the narrow layout places too (`shared`),
    which draws the same in both frames, it only reads the sections, but for
    what the wide layout itself fills that composer's blocks with."""

    def __init__(self, test, where, text, composers, skip=(), narrow=None):
        self.test, self.where, self.text = test, where, text
        self.composers, self.skip = composers, set(skip)
        self.sections, self.columns, self.skipped = [], [], set()
        self.narrow = narrow
        self.spacing, self.expanded = {}, set()
        self.rows = 0        # the rows of columns walked
        self.shared = 0      # the depth inside composers the narrow layout places too

    @property
    def checking(self):
        return self.narrow is not None and not self.shared

    def is_composer(self, name):
        return name in self.composers if self.composers is not None else name.endswith("_sections")

    def body(self, body, gates, overrides=None, widget=None, spacing=_UNKNOWN):
        """Walk a body and return the te_* instances it holds directly. `widget`
        says whose it is: a wrapper's (its kind), a composer's ("composer"), or,
        when None, a block's content, which draws in the widget around the
        block. `spacing` is the spacing around the body: a block's content
        sits at it, and so does the one child of a wrapper or composer that
        holds no second, which draws no spacing of its own."""
        items = _children(body)
        gates = gates + _own_gates(items)
        props = {k: v for kind, k, v in items if kind == "property"}
        if widget and self.children(items, overrides) >= 2:
            spacing = props.get("spacing")
        held = []
        for kind, name, inner in items:
            if kind == "block" and overrides and name in overrides:    # a block draws its override,
                depth, self.shared = self.shared, overrides.shared      # the instancing layout's markup,
                held += self.body(overrides[name], gates, overrides, spacing=spacing)
                self.shared = depth
            elif kind == "block":                                       # or its default content
                held += self.body(inner, gates, overrides, spacing=spacing)
            elif kind == "blockoverride":
                held += self.body(inner, gates, overrides, spacing=spacing)
            elif kind != "widget":
                continue
            elif name in COLUMN_TYPES:
                self.columns_of(name, inner, gates)
            elif name.startswith("te_"):
                self.instance(name, inner, gates, spacing)
                held.append(name)
            elif name in WRAPPERS:
                self.body(inner, gates, overrides, widget=name, spacing=spacing)
            else:
                self.test.fail(f"{self.where} draws {name} inline: make it a te_* section type, so the check can "
                               f"follow it")
        if widget in WRAPPERS and self.checking:
            self.check_wrapper(widget, props, held)
        return held

    def children(self, items, overrides):
        """How many widgets a body holds directly, through its blocks."""
        n = 0
        for kind, name, inner in items:
            if kind == "block":
                n += self.children(_children(overrides[name] if overrides and name in overrides else inner), overrides)
            elif kind == "blockoverride":
                n += self.children(_children(inner), overrides)
            elif kind == "widget":
                n += 1
        return n

    def check_wrapper(self, kind, props, held):
        """A wide layout's own wrapper: `kind` with `props`, holding the te_*
        instances `held` directly."""
        self.test.assertEqual(kind, "flowcontainer",
                              f"{self.where} wraps sections in `{kind}`; a wide layout's wrappers are flowcontainers "
                              f"(an hbox sets its sections side by side in the 520 column, a widget or a container "
                              f"draws them over each other, and a column, a flowcontainer, can't hold a vbox)")
        extra = sorted(set(props) - WIDE_WRAPPER_PROPS)
        self.test.assertFalse(extra, f"{self.where}: a wrapper carries {extra}; a wide layout's wrappers only gate and "
                                     f"space their sections")
        self.test.assertEqual(props.get("ignoreinvisible"), "yes",
                              f"{self.where}: a wrapper without ignoreinvisible = yes keeps a hidden section's space")
        self.test.assertEqual(props.get("direction"), "vertical",
                              f"{self.where}: a flowcontainer wrapper runs vertically in its column")
        for limit in ("minimumsize", "maximumsize"):
            if limit in props:
                self.test.assertEqual(props[limit].strip("{}").split(), COLUMN_SIZE,
                                      f"{self.where}: a wrapper's {limit} is {props[limit]}; its column is 520 wide, "
                                      f"so {{ 520 -1 }} or none")
        # Its spacing draws between the sections it holds, so only two or more
        # are held to the narrow layout's: the spacing one of them sits at
        # there (a composer's root's, or a wrapper's).
        narrow = set().union(*(self.narrow.spacing.get(name, ()) for name in held))
        if len(held) >= 2 and narrow:
            self.test.assertIn(props.get("spacing"), narrow,
                               f"{self.where}: the wrapper around {held} spaces its sections {props.get('spacing')} "
                               f"apart, the narrow layout {sorted(narrow, key=str)}")

    def type_gates(self, name):
        """A type's own root visible, or () when it has none or isn't found."""
        if not re.search(rf"\btype {name} = \w+ \{{", self.text):
            return ()
        return _own_gates(_children(_type_body(self.text, name)))

    def instance(self, name, own, gates, spacing=_UNKNOWN):
        items = _children(own)
        mine = _own_gates(items)
        if mine and self.type_gates(name):
            self.test.fail(f"{self.where}: {name}'s visible replaces its type's own (gotcha #17), so it draws where "
                           f"its own gate hides it; gate a wrapper instead")
        if self.checking:
            extra = sorted({k for kind, k, _ in items if kind == "property"} - {"visible"})
            self.test.assertFalse(extra, f"{self.where}: {name} carries {extra}; an instance in a wide layout takes a "
                                         f"visible and nothing else of its own: no datacontext, margin, position or "
                                         f"size, which a wrapper may not carry either")
        if self.narrow is None and spacing is not _UNKNOWN:
            self.spacing.setdefault(name, set()).add(spacing)
        gates = gates + mine
        if name in self.skip:
            self.skipped.add(name)
        elif self.is_composer(name):
            self.expanded.add(name)
            filled = _Filled((n, inner) for kind, n, inner in items if kind == "blockoverride")
            filled.shared = self.shared
            shared = self.narrow is not None and name in self.narrow.expanded
            self.shared += shared
            where = self.where
            if self.checking:                         # the wide layout's own composer: a failure in it names it
                self.where = f"{where}'s {name}"
            self.body(_type_body(self.text, name), gates, filled, widget="composer", spacing=spacing)
            self.shared, self.where = self.shared - shared, where
        else:
            in_column = bool(self.columns) and self.columns[-1] is not None
            self.sections.append((name, gates, in_column))
            if in_column:
                self.columns[-1].append(name)

    def columns_of(self, column_type, body, gates):
        n = COLUMN_TYPES[column_type]
        if self.narrow is not None:
            self.test.assertEqual(self.rows, 0, f"{self.where} places a second row of columns; a wide layout is one "
                                                f"row, read down each column and then across")
        self.rows += 1
        items = _children(body)
        gates = gates + _own_gates(items)
        overrides = [(name, inner) for kind, name, inner in items if kind == "blockoverride"]
        filled = {name: inner for name, inner in overrides if not name.endswith("_visible")}
        shown = {name: inner for name, inner in overrides if name.endswith("_visible")}
        others = [name for kind, name, _ in items if kind != "blockoverride" and not (kind == "property" and name == "visible")]
        self.test.assertEqual(others, [], f"{self.where}: a {column_type} holds only its visible and its column blocks")
        self.test.assertEqual(sorted(filled), [f"column_{i}" for i in range(1, n + 1)],
                              f"{self.where}: {column_type} fills column_1 to column_{n}, each once")
        self.test.assertEqual(len(shown), len([name for name, _ in overrides if name.endswith("_visible")]),
                              f"{self.where}: a column's visible is given once")
        self.test.assertFalse(sorted(set(shown) - {f"column_{i}_visible" for i in range(1, n + 1)}),
                              f"{self.where}: {column_type} has no such column visible")
        for i in range(1, n + 1):
            # A column may carry a visible of its own (column_<i>_visible),
            # which collapses it when every section in it hides: one more gate
            # on each of its sections, held to the narrow ones like any other.
            column_gates = ()
            if f"column_{i}_visible" in shown:
                props = _children(shown[f"column_{i}_visible"])
                self.test.assertEqual([(kind, k) for kind, k, _ in props], [("property", "visible")],
                                      f"{self.where}: column_{i}_visible holds a visible and nothing else")
                column_gates = _own_gates(props)
            self.columns.append([])
            self.body(filled[f"column_{i}"], gates + column_gates)
            self.test.assertTrue(self.columns[-1], f"{self.where}: column_{i} is empty, but keeps its 520; "
                                                   f"two columns of content take te_ui_columns_two")
            self.columns.append(None)                 # a section after the columns sits in none


def assert_column_closes_with_its_sections(test, wide_type, n, sections, text=None):
    """A wide layout's column_<n>_visible is exactly its sections' own gates,
    joined: the gate of the one section it holds, or Or( a, b ) of two. It
    hides the column only when each of them hides itself, so it can't hide a
    section that would show; the column then closes up instead of keeping an
    empty 520. Those sections take the gate as one more (added_gates)."""
    test.assertIn(len(sections), (1, 2), "the data system's Or takes two")
    text = _all_gui() if text is None else _strip_comments(text)
    shown = [inner for kind, name, inner in _children(_type_body(text, wide_type))
             if kind == "blockoverride" and name == f"column_{n}_visible"]
    test.assertEqual(len(shown), 1, f"{wide_type} has one column_{n}_visible")
    props = [v for kind, k, v in _children(shown[0]) if kind == "property" and k == "visible"]
    own = []
    for section in sections:
        gates = [v for kind, k, v in _children(_type_body(text, section)) if kind == "property" and k == "visible"]
        test.assertEqual(len(gates), 1, f"{section} carries one visible of its own")
        own.append(gates[0].strip('"')[1:-1])
    want = own[0] if len(own) == 1 else f"Or( {', '.join(own)} )"
    test.assertEqual(props, [f'"[{want}]"'], f"{wide_type}: column_{n}_visible is its sections' own gates")


def assert_wide_matches_narrow(test, wide_type, narrow_types=(), *, layout=None, extra=(), outside=(),
                               added_gates=(), composers=None, text=None, columns=None, split=None):
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
    - The wide composer, `wide_type`, must lay its sections out on one row of
      te_ui_columns_three or te_ui_columns_two (spec § 9.4) and place exactly
      the narrow sections, in the same order read down each column and then
      across. Every column holds at least one section. A second row of
      columns fails. A section outside the columns (the Census Data window's
      pending line) must be named in `outside`, and counts where it draws.
    - `extra` names wide-only te_* instances to skip.
    - Each section sits under exactly the gates the narrow layout gives it (a
      composer's or a wrapper's visible, or the instance's own; an And( a, b )
      counts as a and b), on the instance, a wrapper, the column type's
      instance, the column's own visible (column_<n>_visible, which closes
      up an empty column) or the wide composer's root. A section named in `added_gates`
      may carry more (the Census Data window's How waits for the first
      census). An instance's visible over a type's own fails either way: in
      game it replaces the type's (gotcha #17).
    - A wrapper in the wide layout only gates and spaces its sections: it is
      a flowcontainer, running vertically, and carries nothing but direction,
      parentanchor, ignoreinvisible = yes, spacing, a size limit of its
      column's width ({ 520 -1 }), a name and its visible. One that holds two
      or more te_* instances directly (through blocks, not through a wrapper
      inside it) spaces them as the narrow layout does: the spacing one of
      them sits at there, that of the nearest composer's root or wrapper
      around it that holds two or more widgets. A wrapper that holds one
      draws no spacing, so needs none, on either side; an instance the narrow
      layout holds in a widget the check can't read (the frame around a tab
      body's layout block) sets no spacing to match.
    - A te_* instance in the wide layout carries a visible and nothing else of
      its own (blockoverrides and child widgets aside): no datacontext,
      margin, position or size, as its wrappers.
    - Neither rule reaches inside a composer both layouts place: its type
      draws the same in both frames. What the wide layout fills such a
      composer's blocks with is its own markup, and held to both; so is a
      composer only the wide layout places.
    - `split` maps a wide-only section to the narrow section it draws part
      of (the Space Race's solar colonization tabs, which the narrow layout
      draws inside the milestones and full screen takes a column of their
      own: owner, 2026-11-05). It counts in its column, unlike `extra`, but
      not in the narrow comparison, and it sits under every gate its narrow
      section does, and may carry more. That the wide layout leaves the part
      out of the narrow section is the caller's to check.
    - A name in `extra`, `outside`, `added_gates` or `split` that no longer
      applies fails, so a stale one can't hide a change.
    - `columns`, for a layout the owner balanced by hand (Banking, Grand
      Monuments, Demographics: 2026-11-03): its columns, a list of
      section-name lists read down each. The wide composer must lay them out
      exactly so, and place the narrow sections each exactly once in any
      order; the gates are then compared section by section, by name. Without
      it, the wide order must be the narrow one.

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
    wide = _Walk(test, wide_type, text, composers, skip=extra, narrow=narrow)
    if m.group(1) in COLUMN_TYPES:
        wide.columns_of(m.group(1), _type_body(text, wide_type), ())
    else:
        wide.body(_type_body(text, wide_type), ())
    test.assertTrue(wide.columns, f"{wide_type} lays its sections out on te_ui_columns_three or te_ui_columns_two")
    stale = set(extra) - wide.skipped
    test.assertFalse(stale, f"{wide_type}: extra names {sorted(stale)}, which it doesn't place")

    split = dict(split or {})
    placed = {s: gates for s, gates, _ in wide.sections}
    narrow_gates = {s: gates for s, gates, _ in narrow.sections}
    for section, part_of in split.items():
        test.assertIn(section, placed, f"{wide_type}: split names {section}, which it doesn't place")
        test.assertNotIn(section, narrow_gates, f"{wide_type}: split names {section}, which the narrow layout places")
        test.assertIn(part_of, narrow_gates, f"{wide_type}: {section} is split out of {part_of}, "
                                             f"which the narrow layout doesn't place")
        missing = sorted(set(narrow_gates[part_of]) - set(placed[section]))
        test.assertFalse(missing, f"{wide_type}: {section} shows in the narrow layout, inside {part_of}, only while "
                                  f"{missing}, but in the wide one without it")
    sections = [entry for entry in wide.sections if entry[0] not in split]
    wide_names = [s for s, _, _ in sections]
    narrow_names = [s for s, _, _ in narrow.sections]
    if columns is None:
        test.assertEqual(wide_names, narrow_names,
                         f"{wide_type}: the narrow layout's sections, read down each column and then across")
        pairs = list(zip(narrow.sections, sections))
    else:
        test.assertEqual([c for c in wide.columns if c is not None], [list(c) for c in columns],
                         f"{wide_type}: the columns the owner set")
        test.assertEqual(len(set(narrow_names)), len(narrow_names), f"{wide_type}: the narrow layout names a section twice")
        test.assertEqual(sorted(wide_names), sorted(narrow_names),
                         f"{wide_type}: the narrow layout's sections, each once, in any order")
        # a section outside the columns still draws where the narrow layout has it (the pending line first)
        for section in outside:
            if section in wide_names and section in narrow_names:
                test.assertEqual(wide_names.index(section), narrow_names.index(section),
                                 f"{wide_type}: {section} draws outside the columns at another place than the narrow one")
        by_name = {s: (s, gates, in_column) for s, gates, in_column in sections}
        pairs = [(entry, by_name[entry[0]]) for entry in narrow.sections]
    out = [s for s, _, in_column in wide.sections if not in_column]
    test.assertFalse(sorted(set(out) - set(outside)),
                     f"{wide_type} places {sorted(set(out) - set(outside))} outside its columns; name each in outside")
    stale = set(outside) - set(out)
    test.assertFalse(stale, f"{wide_type}: outside names {sorted(stale)}, which it doesn't place outside its columns")

    further = set()
    for (section, narrow_gates, _), (_, wide_gates, _) in pairs:
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


# --- History charts (charts PR C1) ------------------------------------------------
# A history section instances each chart as its te_hist_<id> wrapper, generated
# into gui/te_history_charts_generated.gui; the chart's text is the wrapper's.

HISTORY_CHARTS = os.path.join(REPO, "gui", "te_history_charts_generated.gui")


def history_charts(section):
    """The history charts a section's text instances, in order: each one's
    te_history_chart instance at the panel's size (its te_hist_<id> wrapper's
    child), braces included, as an inline instance used to read."""
    text = _read(HISTORY_CHARTS)
    names = set(re.findall(r"^\ttype (te_hist_\w+) = flowcontainer \{", text, re.M))
    out = []
    for name in re.findall(r"(?<![\w.])(te_hist_\w+) = \{", section):
        if name in names and not name.endswith("_large"):
            body = _type_body(text, name)
            start = body.index("te_history_chart = {")
            out.append(body[start:_close(body, body.index("{", start)) + 1])
    return out


# --- Loc a panel reaches (moved from test_demographics_census_window.py, PR F0) -------------------

LOC_DIR = os.path.join(REPO, "localization", "english")


@functools.lru_cache(maxsize=4)
def _loc_index(loc_dir, root=REPO):
    # mod_state.split_loc_line, the repo's loc-line reader: `key:0 "v"`, `key:"v"`
    # and a line with a trailing `# REVIEWED ...` comment all count.
    from mod_state import split_loc_line
    out = {}
    for path in sorted(glob.glob(os.path.join(loc_dir, "**", "*.yml"), recursive=True)):
        for n, line in enumerate(_read(path).splitlines(), 1):
            got = split_loc_line(line)
            if got:
                out[got[0]] = (got[1], os.path.relpath(path, root), n)
    return out


def loc_index(loc_dir=LOC_DIR, root=REPO):
    """Every English loc key: (value, file relative to root, line). A key
    defined twice takes the later file's text, in name order, as the game does."""
    return dict(_loc_index(loc_dir, root))


def load_loc(loc_dir=LOC_DIR):
    """Every English loc key and its value."""
    return {k: v for k, (v, _, _) in _loc_index(loc_dir).items()}


# Customizable localization: `[X.GetCustom('name')]` renders one of the entry's
# `localization_key`s (common/customizable_localization/), in the caller's context.
_GET_CUSTOM = re.compile(r"""GetCustom\(\s*\\?['"]([\w.\-]+)\\?['"]\s*\)""")
_CUSTOM_TOP = re.compile(r"(?m)^([\w.\-]+)\s*=\s*\{")
_CUSTOM_KEY = re.compile(r"""\blocalization_key\s*=\s*"?([\w.\-]+)"?""")


@functools.lru_cache(maxsize=4)
def _custom_loc(root):
    out = {}
    for path in sorted(glob.glob(os.path.join(root, "common", "customizable_localization", "*.txt"))):
        code = _strip_comments(_read(path))
        for m in _CUSTOM_TOP.finditer(code):
            brace = m.end() - 1
            out.setdefault(m.group(1), []).extend(_CUSTOM_KEY.findall(code[brace:_close(code, brace) + 1]))
    return out


def custom_loc(root=REPO):
    """Each customizable localization entry and the loc keys it may render."""
    return dict(_custom_loc(root))


def custom_keys(text, custom=None):
    """The loc keys the GetCustom calls in a text may render."""
    custom = _custom_loc(REPO) if custom is None else custom
    return {k for name in _GET_CUSTOM.findall(text) for k in custom.get(name, ())}


# A key shown only for the player's own country: the first branch of a
# SelectLocalization on Country.IsLocalPlayer (Global Warming's wording), or
# AddLocalizationIf's. own=False leaves these out of a text's keys.
_OWN_BRANCH = re.compile(r"((?:SelectLocalization|AddLocalizationIf)\(\s*Country\.IsLocalPlayer\s*,\s*)'[\w.\-]+'")


def gui_keys(text, loc, own=True, custom=None):
    """The loc keys a markup text names: a text, tooltip or raw_text, a quoted
    key inside an expression, and the keys its GetCustom calls may render
    (custom: custom_loc(); the repo's when None). own=False leaves out a key
    shown only for the player's own country (_OWN_BRANCH)."""
    if not own:
        text = _OWN_BRANCH.sub(r"\1''", text)
    out = set(re.findall(r'(?:text|tooltip|raw_text)\s*=\s*"([\w.\-]+)"', text))
    for expr in re.findall(r'"\[(.*?)\]"', text):
        out.update(re.findall(r"'([\w.\-]+)'", expr))
    out |= custom_keys(text, custom)
    return {k for k in out if k in loc}


def loc_closure(keys, loc, own=True, custom=None):
    """The keys and every key their values splice ($key$), name ('key') or
    render through GetCustom, all the way down. own and custom as gui_keys."""
    custom = _custom_loc(REPO) if custom is None else custom
    seen, stack = set(), list(keys)
    while stack:
        key = stack.pop()
        if key in seen or key not in loc:
            continue
        seen.add(key)
        value = loc[key] if own else _OWN_BRANCH.sub(r"\1''", loc[key])
        stack.extend(re.findall(r"\$([\w.\-]+)(?:\|[^$]*)?\$", value))
        stack.extend(k for k in re.findall(r"'([\w.\-]+)'", value) if k in loc)
        stack.extend(custom_keys(value, custom))
    return seen


def type_bodies(text):
    """Each `type X = Y { ... }` in a types file, by name, braces included."""
    out = {}
    for m in re.finditer(r"(?m)^\ttype (\w+) = \w+ \{", text):
        brace = m.end() - 1
        out[m.group(1)] = text[brace:_close(text, brace) + 1]
    return out


# --- The types a panel draws, and what another country sees of them (PR F0) ------------------------
# The binding rule (docs/superpowers/specs/2026-11-02-charts-help-national-info-design.md §§ 6.3, 6.5,
# 7.1): a public tab's sections read the shown country as Country; JournalEntry and the player appear
# only under te_own_country_only, or as a world read under a `# world: <why>` line; every control sits
# under te_own_country_only. test_te_system_tab_bodies.py's BindingTest and GuardTest hold each public
# tab to it, and scripts/analysis/te_rebind_country.py lists what a tab still reads.

# The mod's own GUI files. The other files under gui/ copy vanilla's markup (an
# override of a vanilla file, or a 00_te_* file that redefines vanilla's types,
# gotcha #30), and their types are vanilla's: a mod panel that draws one (a law's
# FancyTooltip_Law) draws vanilla's own reads, which the binding rule leaves alone.
# A new mod GUI file whose types a panel draws takes one of these names.
MOD_GUI = ("gui/journal_entry_widgets/*.gui", "gui/te_*.gui", "gui/gm_*.gui", "gui/sr_*.gui")


@dataclass(frozen=True)
class TypeDef:
    """One type: its base, where it is (path relative to the repo, the line of
    its `type` line), and its body between its braces twice: `body` with the
    comments cut, `raw` as written. Both keep the lines, so body line i is
    file line `line + i`, and a column on body line 0 is `col` further along
    the file's line than on the others (body line 0 starts after the brace)."""
    name: str
    base: str
    path: str
    line: int
    body: str
    raw: str = ""
    col: int = 0


def mod_gui_paths(root=REPO):
    return sorted({os.path.relpath(p, root) for g in MOD_GUI for p in glob.glob(os.path.join(root, g))})


def file_types(text, path=""):
    """Every type in one GUI file's text, by name."""
    return _file_blocks(text, path, r"(?m)^\s*type (\w+) = (\w+) \{")


def file_templates(text, path=""):
    """Every template in one GUI file's text, by name, as a TypeDef whose base
    is "template"."""
    return _file_blocks(text, path, r"(?m)^\s*template (\w+)() \{")


def _file_blocks(text, path, pattern):
    code = _strip_comments(text)
    raw_lines, code_lines = text.split("\n"), code.split("\n")
    raw_starts, code_starts, n = [], [], 0
    for line in raw_lines:
        raw_starts.append(n)
        n += len(line) + 1
    n = 0
    for line in code_lines:
        code_starts.append(n)
        n += len(line) + 1

    def line_of(pos):
        return bisect.bisect_right(code_starts, pos) - 1

    def to_raw(pos):
        # comments are cut only after their #, so a brace keeps its line and column
        line = line_of(pos)
        return raw_starts[line] + pos - code_starts[line]

    out = {}
    for m in re.finditer(pattern, code):
        brace = m.end() - 1
        end = _close(code, brace)
        out[m.group(1)] = TypeDef(m.group(1), m.group(2) or "template", path, line_of(m.start(1)) + 1,
                                  code[brace + 1:end], text[to_raw(brace) + 1:to_raw(end)],
                                  brace + 1 - code_starts[line_of(brace)])
    return out


@functools.lru_cache(maxsize=4)
def _mod_types(root):
    out = {}
    for path in mod_gui_paths(root):
        out.update(file_types(_read(os.path.join(root, path)), path))
    return out


def mod_types(root=REPO):
    """Every type in the mod's own GUI files (MOD_GUI), by name."""
    return dict(_mod_types(root))


@functools.lru_cache(maxsize=4)
def _mod_templates(root):
    out = {}
    for path in mod_gui_paths(root):
        out.update(file_templates(_read(os.path.join(root, path)), path))
    return out


def mod_templates(root=REPO):
    """Every template in the mod's own GUI files, by name."""
    return dict(_mod_templates(root))


_CHILD = re.compile(r"(?<![\w.])(\w+) = \{")


@functools.lru_cache(maxsize=8192)
def _child_sites(body):
    """Each `name = {` in a body: (name, the offset of its brace)."""
    return tuple((m.group(1), m.end() - 1) for m in _CHILD.finditer(body))


def type_closure(names, types):
    """Every type the named types draw, all the way down, the named ones
    included: each type a body instances (a child anywhere in it, a
    blockoverride's contents and a block's default included) and each base
    type, wherever `types` (name -> TypeDef, mod_types()) defines it."""
    seen, todo = set(), [n for n in names if n in types]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        todo += [c for c in [c for c, _ in _child_sites(types[name].body)] + [types[name].base]
                 if c in types and c not in seen]
    return seen


GUARD = "te_own_country_only"
_GUARD_USING = re.compile(rf"\busing\s*=\s*{GUARD}\b")


def enclosing_block(body, pos):
    """The block a body offset sits in, as (start, end) offsets of its braces;
    (0, len(body)) at the type's root."""
    depth, i = 0, pos - 1
    while i >= 0:
        if body[i] == "}":
            depth += 1
        elif body[i] == "{":
            if depth == 0:
                break
            depth -= 1
        i -= 1
    return (0, len(body)) if i < 0 else (i, _close(body, i))


def guard_spans(body):
    """The parts of a body under te_own_country_only: each widget that carries
    `using = te_own_country_only`, from its opening brace to its closing one,
    as (start, end) offsets; (0, len(body)) when the type's root carries it."""
    return [enclosing_block(body, m.start()) for m in _GUARD_USING.finditer(body)]


def in_spans(pos, spans):
    return any(a <= pos <= b for a, b in spans)


def unguarded(body, spans=None):
    """The body with its guarded parts blanked, its lines kept."""
    spans = guard_spans(body) if spans is None else spans
    chars = list(body)
    for a, b in spans:
        for i in range(a, min(b, len(chars) - 1) + 1):  # (0, len(body)) is the root's
            if chars[i] != "\n":
                chars[i] = " "
    return "".join(chars)


_BRACE = re.compile(r"[{}]")


def own_props(text):
    """A block's own properties: its inside with every nested block's contents
    cut (the nested blocks' names and braces kept), so `visible =` or
    `blockoverride "x"` found in it is the block's own. Offsets don't hold."""
    out, depth, last = [], 0, 0
    for m in _BRACE.finditer(text):
        if m.group() == "{":
            if depth == 0:
                out.append(text[last:m.end()])
            depth += 1
        elif depth:
            depth -= 1
            if depth == 0:
                last = m.start()
    out.append(text[last:] if depth == 0 else "")
    return "".join(out)


_BLOCK_DEF = re.compile(r'\bblock\s+"(\w+)"\s*\{')
_OVERRIDE = re.compile(r'\bblockoverride\s+"(\w+)"')
_OWN_VISIBLE = re.compile(r"(?<![\w.])visible\s*=")
_USING = re.compile(r"\busing\s*=\s*(\w+)")


@functools.lru_cache(maxsize=8192)
def block_defaults(body):
    """Each `block "x" { ... }` default in a body: (start, end, name)."""
    return tuple((m.end() - 1, _close(body, m.end() - 1), m.group(1)) for m in _BLOCK_DEF.finditer(body))


@dataclass
class View:
    """What another country's panel draws of the types it names.

    open       the types it draws: each reached by some path through no
               te_own_country_only and no block default that is overridden
    skip       type -> the parts of its body it doesn't draw, as (start, end):
               its te_own_country_only widgets (less the root's, where an
               instance or a derived type sets its own visible, which replaces
               the template's: gotcha #17), each block default that every
               place the panel draws the type overrides (a blockoverride in the
               instance, or in a derived type's root or all of its instances),
               and each blockoverride whose contents land only in such parts
               (_dead_overrides: every `block "x"` it can fill is one the
               panel doesn't draw)
    templates  the templates the open types use outside those parts (but the
               guard itself), and the templates those use
    overrides  type -> the blockoverrides among its skip (skipped_overrides)
    """
    open: set
    skip: dict
    templates: set
    overrides: dict = field(default_factory=dict)


_VIEWS = {}  # (names, id(types), id(templates)) -> (types, templates, View): the dicts held, so no id is reused


def panel_view(names, types, templates=None):
    """The View of what another country's panel draws of the named types.
    templates: mod_templates() (the repo's when None). The last few are kept,
    by the identity of the dicts they were drawn from."""
    templates = _mod_templates(REPO) if templates is None else templates
    key = (frozenset(names), id(types), id(templates))
    hit = _VIEWS.get(key)
    if hit and hit[0] is types and hit[1] is templates:
        return hit[2]
    view = _panel_view(names, types, templates)
    if len(_VIEWS) >= 32:
        _VIEWS.pop(next(iter(_VIEWS)))
    _VIEWS[key] = (types, templates, view)
    return view


def _panel_view(names, types, templates):
    dead, view = ({}, {}), None
    # a dead default can hide an instance, which can kill another default, and
    # an override into a part not drawn can hold the only place that draws a
    # type; each round only adds to what isn't drawn
    for _ in range(8):
        view, sites = _view_walk(names, types, dead[0], templates, dead[1])
        found = _dead_defaults(names, types, sites), _dead_overrides(view, types, templates)
        if found == dead:
            break
        dead = found
    return view


def _view_walk(names, types, dead, templates, filled=None):
    seen, skip, sites = {}, {}, {}  # seen: type -> whether a place voids its root guard
    todo = [(n, False) for n in sorted(names) if n in types]
    while todo:
        name, voided = todo.pop()
        if name in seen and (seen[name] or not voided):
            continue
        seen[name] = seen.get(name, False) or voided
        body = types[name].body
        root = (0, len(body))
        spans = [sp for sp in guard_spans(body) if not (sp == root and seen[name])]
        spans += [(a, b) for a, b, x in block_defaults(body) if x in dead.get(name, ())]
        spans += (filled or {}).get(name, ())
        skip[name] = spans
        if root in spans:
            continue
        for m in _CHILD.finditer(body):
            child, brace = m.group(1), m.end() - 1
            if child not in types or in_spans(brace, spans):
                continue
            own = own_props(body[brace + 1:_close(body, brace)])
            sites.setdefault(child, []).append((None, set(_OVERRIDE.findall(own))))
            todo.append((child, bool(_OWN_VISIBLE.search(own))))
        base = types[name].base
        if base in types:
            own = own_props(body)
            sites.setdefault(base, []).append((name, set(_OVERRIDE.findall(own))))
            todo.append((base, bool(_OWN_VISIBLE.search(own))))
    used, stack = set(), []
    for name in seen:
        stack += [u for u in _USING.findall(unguarded(types[name].body, skip[name])) if u != GUARD]
    while stack:
        t = stack.pop()
        if t in templates and t not in used:
            used.add(t)
            stack += [u for u in _USING.findall(templates[t].body) if u != GUARD]
    return View(set(seen), skip, used, dict(filled or {})), sites


def _dead_defaults(names, types, sites):
    """type -> the block names whose default no place that draws it shows."""
    memo = {}

    def dead(t, x, path=()):
        if t in names or not sites.get(t) or t in path:
            return False
        if (t, x) not in memo:
            memo[(t, x)] = all(x in over or (derived is not None and dead(derived, x, path + (t,)))
                               for derived, over in sites[t])
        return memo[(t, x)]

    out = {}
    for t in sites:
        gone = frozenset(x for _, _, x in block_defaults(types[t].body) if dead(t, x))
        if gone:
            out[t] = gone
    return out


_OVERRIDE_OPEN = re.compile(r'\bblockoverride\s+"(\w+)"\s*\{')
_OPENER = re.compile(r"(?<![\w.])(\w+) = \{$")
_BLOCK_OPENER = re.compile(r'\b(block|blockoverride)\s+"(\w+)"\s*\{$')


@functools.lru_cache(maxsize=8192)
def _block_sites(body):
    """Each `block "x"` in a body: (name, where the word starts)."""
    return tuple((m.group(1), m.start()) for m in _BLOCK_DEF.finditer(body))


@functools.lru_cache(maxsize=8192)
def _using_sites(body):
    return tuple((m.group(1), m.start()) for m in _USING.finditer(body))


def _holder(body, pos):
    """The widget a `block "x"` (or a `using`) at a body offset is written
    in: (the offset of its brace, 0 for the type's root; the blockoverrides
    passed on the way out). A block's default and a blockoverride's contents
    are no widget: what is written in them lands in the widget around them,
    a blockoverride's wherever its own block is in that instance's type."""
    a, via = enclosing_block(body, pos)[0], []
    while a > 0:
        m = _BLOCK_OPENER.search(body, max(0, a - 120), a + 1)
        if not m:
            break
        if m.group(1) == "blockoverride":
            via.append(m.group(2))
        a = enclosing_block(body, a)[0]
    return a, tuple(via)


def _lands(text):
    """A blockoverride's contents as its block's widget takes them: its own
    properties (own_props), a nested `block "x" { }` default's among them."""
    chars = list(text)
    for m in _BLOCK_DEF.finditer(text):
        for i in (*range(m.start(), m.end()), _close(text, m.end() - 1)):
            chars[i] = " "
    return own_props("".join(chars))


def _own_overrides(body, a, b):
    """The blockoverrides written directly in the block from a to b (the whole
    body at a type's root): (name, where the word starts, the offset of its
    brace, of its end)."""
    out = []
    for m in _OVERRIDE_OPEN.finditer(body, a, b):
        before = body[a + 1 if a else 0:m.start()]
        if before.count("{") == before.count("}"):
            out.append((m.group(1), m.start(), m.end() - 1, _close(body, m.end() - 1)))
    return out


def _dead_overrides(view, types, templates):
    """type -> the blockoverrides in its drawn parts whose contents the panel
    never draws, as (start, end) of their braces: in game an override's
    contents sit where its block is, so one that fills only blocks under
    te_own_country_only (or in any other part the View skips, or in a type it
    doesn't draw) is the player's own, as if the guard were written around it.

    An override belongs to the instance it is written in (the base type, at a
    type's root). The blocks it can fill are every `block "x"` of that type,
    of the mod types its own contents draw (the derived type's whole body, at
    a root), of all those draw (type_closure: bases, and the types inside
    them, since an override reaches the blocks of nested types too) and of
    the templates any of them use, and any the instance's own contents
    declare. One of them drawn keeps the override drawn. So does finding
    none: the block is then a type's the mod doesn't define (vanilla's). And
    so does a drawn block of the name anywhere else in the panel: a block of
    that name can reach the instance from another level (a slot an outer
    instance fills, a derived type's instance), which this doesn't trace.

    An override that sets a `visible` (its own, a template's, or a nested
    block default's) sets it on the widget its block is written in: at a
    type's root, the widget that instances the type. Where that widget
    carries the guard, the override's `visible` replaces the guard's (gotcha
    #17). Every guard so replaced by one of the instance's overrides, or by
    one at the root of its type or of that type's bases, counts as gone for
    all of the instance's overrides, and so do the block defaults and
    overrides the View skips: only the guards left hide a block then.

    Two things keep this from reading a drawn override as not drawn (the
    unsafe way); neither is redundant with the rules above:
    - the rule that one drawn block of the name anywhere in the panel keeps
      an override drawn, which covers every way a block reaches an instance;
    - guard_visible_overrides, which test_te_system_tab_bodies.py's
      SkippedOverrideTest holds empty for the whole mod: no override of a
      block that sits on a guard's widget sets a `visible`. The rules above
      follow such a `visible` from the instance's own overrides and its
      type's roots only; one from an instance further out or further in,
      and one on an instance that itself carries the guard (which
      guard_spans skips whole, before this is asked), are caught there.
    One limit is left open, unsafe the same way and not met on main: a
    vanilla type inside the instanced one with a block of the same name as
    a guarded mod block, since vanilla's types are not read
    (SkippedOverrideTest holds the skipped names to ones no vanilla copy
    under gui/ declares, the part the repo can check)."""
    guards, occ, held, hold, universes, by_block = {}, {}, {}, {}, {}, {}

    def guard_set(name):
        if name not in guards:
            guards[name] = frozenset(guard_spans(types[name].body))
        return guards[name]

    def template_blocks(t):
        """The block names a template declares, those it uses included."""
        if t not in held:
            found, seen, todo = set(), set(), [t]
            while todo:
                u = todo.pop()
                if u in templates and u not in seen:
                    seen.add(u)
                    found.update(x for x, _ in _block_sites(templates[u].body))
                    todo += [v for v, _ in _using_sites(templates[u].body)]
            held[t] = found
        return held[t]

    def occurrences(name):
        """(block name, offset) for each block a type's own body offers an
        override: a `block "x"`, or one of a template it uses, at the `using`."""
        if name not in occ:
            body = types[name].body
            found = list(_block_sites(body))
            for t, pos in _using_sites(body):
                found += [(x, pos) for x in template_blocks(t)]
            occ[name] = found
        return occ[name]

    def drawn(name, pos, voided):
        """Whether the panel draws what lands at a body offset, with the
        guards in `voided` replaced."""
        if not voided:
            return name in view.open and not in_spans(pos, view.skip[name])
        left = [sp for sp in guard_set(name) if (name, sp) not in voided]
        if name in view.open:  # less a root guard the walk found replaced
            left = [sp for sp in left if sp in view.skip[name]]
        return not in_spans(pos, left)

    def universe(key):
        """For a set of type names: all they draw; within those, each type's
        places (type -> [(the type it is in, its brace)]) and derived types."""
        if key not in universes:
            names = type_closure(key, types)
            sites, derived = {}, {}
            for name in names:
                for child, brace in _child_sites(types[name].body):
                    if child in names:
                        sites.setdefault(child, []).append((name, brace))
                if types[name].base in names:
                    derived.setdefault(types[name].base, []).append(name)
            universes[key] = (names, sites, derived)
        return universes[key]

    def blocks_in(key, x):
        """Each `block "x"` in a universe: (type, offset)."""
        if key not in by_block:
            found = {}
            for name in universe(key)[0]:
                for block, pos in occurrences(name):
                    found.setdefault(block, []).append((name, pos))
            by_block[key] = found
        return by_block[key].get(x, ())

    def root_guards(name):
        """The guard on a type's root, and on its bases' roots."""
        out, seen = set(), set()
        while name in types and name not in seen:
            seen.add(name)
            if (0, len(types[name].body)) in guard_set(name):
                out.add((name, (0, len(types[name].body))))
            name = types[name].base
        return out

    def carriers(name, pos, key, seen=frozenset()):
        """The guards a `visible` replaces when it lands with the block at a
        body offset, as (type, span): the guard of the widget the block is
        written in. At a type's root that is the type's own root guard and
        each place in the universe that instances the type, or a type derived
        from it, with the guard on the instance."""
        if (name, pos) not in hold:
            hold[(name, pos)] = _holder(types[name].body, pos)
        (w, via), body, out = hold[(name, pos)], types[name].body, set()
        if w == 0:
            _, sites, derived = universe(key)
            inst, todo, done = types[name].base, [name], set()
            while todo:
                n = todo.pop()
                if n in done:
                    continue
                done.add(n)
                out |= root_guards(n)
                for parent, brace in sites.get(n, ()):
                    span = (brace, _close(types[parent].body, brace))
                    if span in guard_set(parent):
                        out.add((parent, span))
                todo += derived.get(n, ())
        else:
            span = (w, _close(body, w))
            if span in guard_set(name):
                out.add((name, span))
            opener = _OPENER.search(body, max(0, w - 120), w + 1)
            inst = opener.group(1) if opener else None
            if inst in types:  # written in an instance: on that type's root
                out |= root_guards(inst)
        if inst in types:  # in a blockoverride of that instance: where its block is
            for y in via:
                if (inst, y) not in seen:
                    for other in type_closure({inst}, types):
                        for block, p in occurrences(other):
                            if block == y:
                                out |= carriers(other, p, key, seen | {(inst, y)})
        return out

    def sets_visible(body, brace, end):
        props = _lands(body[brace + 1:end])
        return bool(_OWN_VISIBLE.search(props) or _USING.search(props))

    # the names with a block not drawn somewhere: no other override can be dead;
    # nor can one whose name has a block the panel draws anywhere
    maybe = {x for name in type_closure(view.open, types) for x, pos in occurrences(name) if not drawn(name, pos, ())}
    maybe -= {x for name in view.open for x, pos in occurrences(name) if drawn(name, pos, ())}
    out = {}
    for name in view.open:
        body, skip = types[name].body, view.skip[name]
        root = (0, len(body))
        if root in skip:
            continue
        instances, spans = set(), []
        for m in _OVERRIDE_OPEN.finditer(body):
            if m.group(1) in maybe and not in_spans(m.start(), skip):
                instances.add(enclosing_block(body, m.start()))
        for a, b in sorted(instances):
            if (a, b) == root:
                target = types[name].base
            else:
                opener = _OPENER.search(body, max(0, a - 120), a + 1)
                target = opener.group(1) if opener else None
            if target not in types:
                continue
            # what this instance draws: its type, and the mod types its own contents hold
            key = frozenset({target} | {c for c, brace in _child_sites(body)
                                        if a < brace < b and c in types and not in_spans(brace, skip)})
            local = [(x, pos) for x, pos in occurrences(name) if a < pos < b]
            own = _own_overrides(body, a, b)
            setters, chain = [x for x, _, brace, end in own if sets_visible(body, brace, end)], target
            for _ in range(8):  # and the overrides its type and that type's bases make at their roots
                if chain not in types:
                    break
                other = types[chain].body
                setters += [x for x, _, brace, end in _own_overrides(other, 0, len(other))
                            if sets_visible(other, brace, end)]
                chain = types[chain].base
            voided = set()
            for x in set(setters):
                for other, pos in list(blocks_in(key, x)) + [(name, pos) for block, pos in local if block == x]:
                    voided |= carriers(other, pos, key)
            for x, start, brace, end in own:
                if x not in maybe or in_spans(start, skip):
                    continue
                mine = [pos for block, pos in local if block == x]
                fills = blocks_in(key, x)
                if not fills and not mine:
                    continue  # a block no mod type defines
                if any(drawn(name, pos, voided) for pos in mine) or any(drawn(t, pos, voided) for t, pos in fills):
                    continue
                spans.append((brace, end))
        if spans:
            out[name] = tuple(spans)
    return out


def _on_guard_widgets(types, templates):
    """block name -> (path, line, type) of a widget that carries
    te_own_country_only, for each `block "x"` that sits on one: written at
    that widget's own level (in a block default or a blockoverride there
    too), declared by a template it uses, or at the root of the mod type it
    instances, that type's bases' roots included; and at the root of any type
    whose own root, or a base's, carries the guard. Also (block name, the
    text of its default) for each of those blocks."""
    names, defaults, roots = {}, [], {}

    def tmpl_blocks(t, seen):
        if t not in templates or t in seen:
            return set()
        seen.add(t)
        out = {x for x, _ in _block_sites(templates[t].body)}
        for u, _ in _using_sites(templates[t].body):
            out |= tmpl_blocks(u, seen)
        return out

    def at(td, a, where):
        """The blocks on the widget whose brace is at a body offset (0: the root)."""
        body = td.body
        lo, hi = (0, len(body)) if a == 0 else (a, _close(body, a))
        for x, pos in _block_sites(body):
            if lo <= pos <= hi and _holder(body, pos)[0] == a:
                names.setdefault(x, where)
                brace = body.index("{", pos)
                defaults.append((x, body[brace + 1:_close(body, brace)]))
        for t, pos in _using_sites(body):
            if lo <= pos <= hi and _holder(body, pos)[0] == a:
                for x in tmpl_blocks(t, set()):
                    names.setdefault(x, where)

    def root_of(name, where):
        seen = set()
        while name in types and name not in seen:
            seen.add(name)
            at(types[name], 0, where)
            name = types[name].base

    def guarded_root(name):
        if name not in roots:
            roots[name] = False  # a loop of bases
            body = types[name].body
            roots[name] = (0, len(body)) in guard_spans(body) or (types[name].base in types
                                                                  and guarded_root(types[name].base))
        return roots[name]

    for kind, group in (("", types), ("template ", templates)):
        for name, td in group.items():
            body = td.body
            for a, b in guard_spans(body):
                where = (td.path, td.line + _line_of(td, a), kind + name)
                if (a, b) == (0, len(body)):
                    if kind:  # a type's guarded root: below, with the types derived from it
                        at(td, 0, where)
                    continue
                at(td, a, where)
                opener = _OPENER.search(body, max(0, a - 120), a + 1)
                if opener and opener.group(1) in types:
                    root_of(opener.group(1), where)
    for name, td in types.items():
        if guarded_root(name):
            root_of(name, (td.path, td.line, name))
    return names, defaults


def _landing(text):
    """What a block's contents put on the widget the block is written in:
    (why a `visible` may be among it, the blocks declared there), each at
    the contents' own level or in a block default nested there."""
    flat = _lands(text)
    why = [reason for found, reason in ((_OWN_VISIBLE.search(flat), "sets a visible"),
                                        (_USING.search(flat), "uses a template, which may set a visible"),
                                        (_OVERRIDE.search(flat), "holds a blockoverride, which may set a visible"))
           if found]
    held = set()
    for m in _BLOCK_DEF.finditer(text):
        a, b = enclosing_block(text, m.start())
        while (a, b) != (0, len(text)):
            opener = _BLOCK_OPENER.search(text, max(0, a - 120), a + 1)
            if not opener or opener.group(1) != "block":
                break
            a, b = enclosing_block(text, a)
        else:
            held.add(m.group(1))
    return why, held


def guard_visible_overrides(types, templates, texts):
    """Each place that could put a `visible` on a widget that carries
    te_own_country_only, where it would replace the guard (gotcha #17), as
    (path, line, block name, why, the guard's widget as (path, line, type)).
    That is a blockoverride, anywhere in `texts` (path -> a GUI file's text,
    comments cut), of a block that sits on such a widget (_on_guard_widgets),
    which sets a `visible`, uses a template or holds another blockoverride
    at its own level; or such a block's own default that does (line 0). A
    block that an override of one of those names declares at its own level
    sits on the widget as well. By name, so every instance level is covered:
    the blockoverride walk (_dead_overrides) and the guard itself
    (guard_spans, which reads the guard where it is written) rest on this
    finding nothing."""
    names, defaults = _on_guard_widgets(types, templates)
    out = {(names[x][0], 0, x, f"its default {w}", names[x]) for x, text in defaults for w in _landing(text)[0]}
    by_name = {}
    for path, text in texts.items():
        for m in _OVERRIDE_OPEN.finditer(text):
            by_name.setdefault(m.group(1), []).append((path, text, m))
    todo, seen = list(names), set()
    while todo:
        x = todo.pop()
        if x in seen:
            continue
        seen.add(x)
        for path, text, m in by_name.get(x, ()):
            why, held = _landing(text[m.end():_close(text, m.end() - 1)])
            line = text.count("\n", 0, m.start()) + 1
            out |= {(path, line, x, w, names[x]) for w in why}
            for y in held:  # a block declared there lands on the same widget
                names.setdefault(y, names[x])
                todo.append(y)
    return sorted(out)


def skipped_overrides(view, types):
    """The blockoverrides a View skips because they fill no block the panel
    draws (_dead_overrides), as sorted (type, block name) pairs."""
    out = set()
    for name, spans in view.overrides.items():
        for a, _ in spans:
            out.add((name, _BLOCK_OPENER.search(types[name].body, max(0, a - 120), a + 1).group(2)))
    return sorted(out)


def open_types(names, types):
    """The types of type_closure(names) another country's panel draws
    (panel_view(names, types).open): each reached by some path that passes no
    te_own_country_only and no overridden block default. A child whose block
    sits in a guarded part of its parent is the player's own, and so is
    everything under it; a type whose root carries the guard draws nothing
    else either, its base included, unless the place that draws it sets its
    own visible."""
    return panel_view(names, types).open


# A read of the entry or of the player. GetPlayerJournalEntry is an entry read
# (of the player's own entry), never a player one.
READ = re.compile(r"(?<![\w.])(JournalEntry\.\w+|GetPlayerJournalEntry|GetPlayer\w*|AccessPlayer\w*)")
# A world read's marker: the comment line directly over a read of the player's
# copy of what is the same for every country (spec § 6.7). It lets a player
# read through, never an entry read: another country's panel has no entry.
WORLD = re.compile(r"^\s*# world: \S")
# A control: a scripted GUI's Execute (not ExecuteTooltip), or a PopupManager
# dialog that changes the country (Grand Monuments' ShowCompanyChangeName).
CONTROL = re.compile(r"\.Execute\s*\(|\bPopupManager\.Show\w*\s*\(")


def _control_name(m):
    return "Execute" if m.group(0).startswith(".") else m.group(0).rstrip("( ")
# A popup's opener, and the popup that shows on its value (te_popups.gui).
OPENER = re.compile(r"GetVariableSystem\.(?:Set|Toggle)\(\s*'te_popup'\s*,\s*'(\w+)'\s*\)")
_POPUP_KEY = re.compile(r"GetVariableSystem\.HasValue\(\s*'te_popup'\s*,\s*'(\w+)'\s*\)")


def is_entry_read(read):
    return read.startswith("JournalEntry.") or read == "GetPlayerJournalEntry"


@dataclass(frozen=True)
class Finding:
    """One read or control another country's panel would draw: where (the type,
    or the loc key, its file and line), what (the read's text, or the control),
    the line as written, and whether a `# world:` line marks it. A markup
    read's col is where it starts on its file line (-1 elsewhere)."""
    where: str
    path: str
    line: int
    what: str
    text: str
    world: bool = False
    col: int = -1

    def __str__(self):
        return f"{self.path}:{self.line}  {self.where}  {self.what}  | {self.text.strip()[:120]}"


@functools.lru_cache(maxsize=4096)
def _line_starts(body):
    return [0] + [m.end() for m in re.finditer("\n", body)]


def _line_of(td, pos):
    """The body line (0 = the type's own line) a body offset is on."""
    return bisect.bisect_right(_line_starts(td.body), pos) - 1


def file_col(td, pos):
    """The column on its file line of a body offset."""
    k = _line_of(td, pos)
    return pos - _line_starts(td.body)[k] + (td.col if k == 0 else 0)


def _drawn(names, types, templates=None):
    """(where, TypeDef, spans not drawn) for each body another country's panel
    draws: the View's open types, then its templates ("template X")."""
    templates = _mod_templates(REPO) if templates is None else templates
    view = panel_view(names, types, templates)
    out = [(name, types[name], view.skip[name]) for name in sorted(view.open)]
    return out + [(f"template {t}", templates[t], []) for t in sorted(view.templates)]


def markup_reads(names, types, templates=None):
    """Each JournalEntry or player read in what another country sees of the
    named types (panel_view: outside te_own_country_only and overridden block
    defaults, the templates they use included), as a Finding; world=True where
    a `# world:` line marks it."""
    out = []
    for where, td, spans in _drawn(names, types, templates):
        raw = td.raw.split("\n") if td.raw else []
        lines = td.body.split("\n")
        for m in READ.finditer(td.body):
            if in_spans(m.start(), spans):
                continue
            k = _line_of(td, m.start())
            world = k >= 1 and k - 1 < len(raw) and bool(WORLD.match(raw[k - 1]))
            out.append(Finding(where, td.path, td.line + k, m.group(1), lines[k], world, file_col(td, m.start())))
    return out


# What hides a world read from an observer, who has no GetPlayer (National Info
# opens to one; gui_modding_guide.md, "An observer has no GetPlayer"): a
# `visible` that tests for the observer, or for a player, first: alone or
# leading an And, whose later arguments are then not read.
OBSERVER_GATE = re.compile(r'(?<![\w.])visible\s*=\s*"\[(?:And\(\s*)?'
                           r'(?:Not\(\s*GetMetaPlayer\.IsObserver\s*\)|GetPlayer\.IsValid\b)')
_IS_VALID = "GetPlayer.IsValid"


def _observer_gate(body, pos):
    """Whether a block around a body offset (the widget it is written in, or
    one that holds it) has an observer gate as its own `visible`. The type's
    root is not asked: an instance's own `visible` replaces it (gotcha #17)."""
    a, b = enclosing_block(body, pos)
    while (a, b) != (0, len(body)):
        if OBSERVER_GATE.search(own_props(body[a + 1:b])):
            return True
        a, b = enclosing_block(body, a)
    return False


def _observer_open(names, types, view):
    """The types an observer's panel draws outside every observer gate: the
    named ones (whose mounts set their own `visible`), and each type a place
    in one of them draws (View.skip left out) with no gate around the place
    and none that holds on the type's own root, which an instance that sets
    its own `visible` replaces. A base type is as open as the type derived
    from it."""
    bare, todo, rooted = set(), [n for n in sorted(names) if n in types], {}

    def tests(body):  # most bodies have no gate to look for
        return "IsObserver" in body or _IS_VALID in body

    while todo:
        name = todo.pop()
        if name in bare:
            continue
        bare.add(name)
        body, skip = types[name].body, view.skip.get(name, ())
        if (0, len(body)) in skip:
            continue
        gates = tests(body)
        for child, brace in _child_sites(body):
            if child not in types or child in bare or in_spans(brace, skip) or (gates and _observer_gate(body, brace + 1)):
                continue
            if child not in rooted:
                rooted[child] = tests(types[child].body) and bool(OBSERVER_GATE.search(own_props(types[child].body)))
            if not rooted[child] or _OWN_VISIBLE.search(own_props(body[brace + 1:_close(body, brace)])):
                todo.append(child)
        if types[name].base in types:
            todo.append(types[name].base)
    return bare


def ungated_world_reads(names, types, templates=None):
    """Each `# world:` read another country's panel draws (markup_reads) that
    an observer's would evaluate, as a Finding. A read is gated when its own
    line is an observer gate (OBSERVER_GATE: the test first, the read after
    it) or has GetPlayer.IsValid before it, when a block around it has the
    gate (its own widget's `visible`, or a container's), or when every place
    the panel draws its type sits under one, the type's own root included
    while no such place sets its own `visible`. A template's read takes a
    gate inside the template."""
    templates = _mod_templates(REPO) if templates is None else templates
    bare = _observer_open(names, types, panel_view(names, types, templates))
    out = []
    for f in markup_reads(names, types, templates):
        if not f.world:
            continue
        in_template = f.where.startswith("template ")
        td = templates[f.where[len("template "):]] if in_template else types[f.where]
        k = f.line - td.line
        start = _line_starts(td.body)[k]
        pos = start + f.col - (td.col if k == 0 else 0)
        if (OBSERVER_GATE.search(td.body, start, pos) or td.body.find(_IS_VALID, start, pos + len(_IS_VALID)) >= 0
                or _observer_gate(td.body, pos)):
            continue
        if in_template or f.where in bare:
            out.append(f)
    return out


def popups(types):
    """Each te_popup value and the popup types that show on it."""
    out = {}
    for name, td in types.items():
        m = re.search(r'blockoverride "popup_visible" \{', td.body)
        if m:
            block = td.body[m.end():_close(td.body, m.end() - 1)]
            for key in _POPUP_KEY.findall(block):
                out.setdefault(key, []).append(name)
    return out


def popup_controls(key, types, shown=None):
    """The controls the popup(s) on a te_popup value hold, as Findings (empty
    for a page that only reads: a Help page, a chart viewer), or None when no
    popup shows on it."""
    shown = popups(types) if shown is None else shown
    if key not in shown:
        return None
    out = []
    for name in sorted(type_closure(set(shown[key]), types)):
        td = types[name]
        for m in CONTROL.finditer(td.body):
            k = _line_of(td, m.start())
            out.append(Finding(name, td.path, td.line + k, _control_name(m), td.body.split("\n")[k]))
    return out


def unguarded_controls(names, types, templates=None):
    """Each control another country's panel would draw (CONTROL: an Execute, a
    PopupManager dialog), or an opener of a popup that holds controls (or of a
    popup that isn't there), outside te_own_country_only, as a Finding."""
    out, shown, held = [], popups(types), {}
    for name, td, spans in _drawn(names, types, templates):
        lines = td.body.split("\n")
        for m in CONTROL.finditer(td.body):
            if not in_spans(m.start(), spans):
                k = _line_of(td, m.start())
                out.append(Finding(name, td.path, td.line + k, _control_name(m), lines[k]))
        for m in OPENER.finditer(td.body):
            if in_spans(m.start(), spans):
                continue
            if m.group(1) not in held:
                held[m.group(1)] = popup_controls(m.group(1), types, shown)
            inside = held[m.group(1)]
            if inside is None or inside:
                k = _line_of(td, m.start())
                what = (f"opens te_popup = {m.group(1)}, which no popup shows on" if inside is None else
                        f"opens te_popup = {m.group(1)}, whose popup holds controls ({inside[0].path}:{inside[0].line})")
                out.append(Finding(name, td.path, td.line + k, what, lines[k]))
    return out


def panel_loc_keys(names, types, loc, templates=None, custom=None):
    """The loc keys another country's panel renders: those the drawn parts of
    the open types and their templates name (panel_view), and every key they
    reach, GetCustom's included, less a key shown only for the player's own
    country (the first branch of a SelectLocalization on Country.IsLocalPlayer,
    which another country's panel never renders). custom: custom_loc()."""
    roots = set()
    for _, td, spans in _drawn(names, types, templates):
        roots |= gui_keys(unguarded(td.body, spans), loc, own=False, custom=custom)
    return loc_closure(roots, loc, own=False, custom=custom)


def loc_reads(keys, index):
    """Each JournalEntry or player read in the loc keys' values, as a Finding.
    index: loc_index()."""
    out = []
    for key in sorted(keys):
        value, path, line = index[key]
        for m in READ.finditer(value):
            out.append(Finding(key, path, line, m.group(1), value))
    return out


PERSONAL = re.compile(r"\b(you|your|yours|we|our|ours|us)\b", re.I)

_PERSONAL_REVIEWED = re.compile(r"#\s*REVIEWED\s+\d{4}-\d{2}-\d{2}\s*\(personal_text\)\s*:")


@functools.lru_cache(maxsize=4)
def _personal_reviewed(loc_dir):
    """Loc keys whose line carries `# REVIEWED YYYY-MM-DD (personal_text): why`, a proper name that says "we" or "our" (a boon, a modifier) rather than the panel speaking as the player."""
    from mod_state import split_loc_line
    out = set()
    for path in sorted(glob.glob(os.path.join(loc_dir, "**", "*.yml"), recursive=True)):
        for line in _read(path).splitlines():
            got = split_loc_line(line)
            if got and _PERSONAL_REVIEWED.search(got[2]):
                out.add(got[0])
    return frozenset(out)


def personal_text(keys, loc):
    """The keys whose text speaks as the player ("our", "you"), with the text:
    another country's panel shows them. Markup, splices and formatting left out."""
    out = {}
    reviewed = _personal_reviewed(LOC_DIR)
    for key in sorted(keys):
        if key in reviewed:
            continue
        text = re.sub(r"\[[^\]]*\]|\$[\w.\-]+\$|#\w+|\\n", " ", loc[key])
        if PERSONAL.search(text):
            out[key] = text
    return out
