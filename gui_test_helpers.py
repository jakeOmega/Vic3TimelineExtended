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
from dataclasses import dataclass
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
_LOC_LINE = re.compile(r'^\s*([\w.\-]+):\d*\s+"(.*)"\s*$')


@functools.lru_cache(maxsize=4)
def _loc_index(loc_dir, root=REPO):
    out = {}
    for path in sorted(glob.glob(os.path.join(loc_dir, "**", "*.yml"), recursive=True)):
        for n, line in enumerate(_read(path).splitlines(), 1):
            m = _LOC_LINE.match(line)
            if m:
                out[m.group(1)] = (m.group(2), os.path.relpath(path, root), n)
    return out


def loc_index(loc_dir=LOC_DIR, root=REPO):
    """Every English loc key: (value, file relative to root, line). A key
    defined twice takes the later file's text, in name order, as the game does."""
    return dict(_loc_index(loc_dir, root))


def load_loc(loc_dir=LOC_DIR):
    """Every English loc key and its value."""
    return {k: v for k, (v, _, _) in _loc_index(loc_dir).items()}


# A key shown only for the player's own country: the first branch of a
# SelectLocalization on Country.IsLocalPlayer (Global Warming's wording), or
# AddLocalizationIf's. own=False leaves these out of a text's keys.
_OWN_BRANCH = re.compile(r"((?:SelectLocalization|AddLocalizationIf)\(\s*Country\.IsLocalPlayer\s*,\s*)'[\w.\-]+'")


def gui_keys(text, loc, own=True):
    """The loc keys a markup text names: a text, tooltip or raw_text, and a
    quoted key inside an expression. own=False leaves out a key shown only for
    the player's own country (_OWN_BRANCH)."""
    if not own:
        text = _OWN_BRANCH.sub(r"\1''", text)
    out = set(re.findall(r'(?:text|tooltip|raw_text)\s*=\s*"([\w.\-]+)"', text))
    for expr in re.findall(r'"\[(.*?)\]"', text):
        out |= {k for k in re.findall(r"'([\w.\-]+)'", expr) if k in loc}
    return out & set(loc)


def loc_closure(keys, loc, own=True):
    """The keys and every key their values splice ($key$) or name ('key'),
    all the way down. own=False as gui_keys."""
    seen, stack = set(), list(keys)
    while stack:
        key = stack.pop()
        if key in seen or key not in loc:
            continue
        seen.add(key)
        value = loc[key] if own else _OWN_BRANCH.sub(r"\1''", loc[key])
        stack.extend(re.findall(r"\$([\w.\-]+)\$", value))
        stack.extend(k for k in re.findall(r"'([\w.\-]+)'", value) if k in loc)
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
    for m in re.finditer(r"(?m)^\s*type (\w+) = (\w+) \{", code):
        brace = m.end() - 1
        end = _close(code, brace)
        out[m.group(1)] = TypeDef(m.group(1), m.group(2), path, line_of(m.start(1)) + 1,
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


_CHILD = re.compile(r"(?<![\w.])(\w+) = \{")


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
        todo += [c for c in _CHILD.findall(types[name].body) + [types[name].base] if c in types and c not in seen]
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
        for i in range(a, b + 1):
            if chars[i] != "\n":
                chars[i] = " "
    return "".join(chars)


def open_types(names, types):
    """The types of type_closure(names) another country's panel draws: each
    reached by some path that passes no te_own_country_only. A child whose block
    sits in a guarded part of its parent is the player's own, and so is
    everything under it; a type whose root carries the guard draws nothing
    else either, its base included."""
    seen, todo = set(), [n for n in names if n in types]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        body = types[name].body
        spans = guard_spans(body)
        if (0, len(body)) in spans:
            continue
        for m in _CHILD.finditer(body):
            if m.group(1) in types and not in_spans(m.end() - 1, spans):
                todo.append(m.group(1))
        if types[name].base in types:
            todo.append(types[name].base)
    return seen


# A read of the entry or of the player. GetPlayerJournalEntry is an entry read
# (of the player's own entry), never a player one.
READ = re.compile(r"(?<![\w.])(JournalEntry\.\w+|GetPlayerJournalEntry|GetPlayer\w*|AccessPlayer\w*)")
# A world read's marker: the comment line directly over a read of the player's
# copy of what is the same for every country (spec § 6.7). It lets a player
# read through, never an entry read: another country's panel has no entry.
WORLD = re.compile(r"^\s*# world: \S")
# A control: a scripted GUI's Execute (not ExecuteTooltip).
CONTROL = re.compile(r"\.Execute\s*\(")
# A popup's opener, and the popup that shows on its value (te_popups.gui).
OPENER = re.compile(r"GetVariableSystem\.Set\(\s*'te_popup'\s*,\s*'(\w+)'\s*\)")
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


def markup_reads(names, types):
    """Each JournalEntry or player read in what another country sees of the
    named types (open_types), outside te_own_country_only, as a Finding;
    world=True where a `# world:` line marks it."""
    out = []
    for name in sorted(open_types(names, types)):
        td = types[name]
        spans = guard_spans(td.body)
        raw = td.raw.split("\n") if td.raw else []
        lines = td.body.split("\n")
        for m in READ.finditer(td.body):
            if in_spans(m.start(), spans):
                continue
            k = _line_of(td, m.start())
            world = k >= 1 and k - 1 < len(raw) and bool(WORLD.match(raw[k - 1]))
            out.append(Finding(name, td.path, td.line + k, m.group(1), lines[k], world, file_col(td, m.start())))
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
            out.append(Finding(name, td.path, td.line + k, "Execute", td.body.split("\n")[k]))
    return out


def unguarded_controls(names, types):
    """Each control another country's panel would draw: an Execute, or an
    opener of a popup that holds controls (or of a popup that isn't there),
    outside te_own_country_only, as a Finding."""
    out, shown, held = [], popups(types), {}
    for name in sorted(open_types(names, types)):
        td = types[name]
        spans = guard_spans(td.body)
        lines = td.body.split("\n")
        for m in CONTROL.finditer(td.body):
            if not in_spans(m.start(), spans):
                k = _line_of(td, m.start())
                out.append(Finding(name, td.path, td.line + k, "Execute", lines[k]))
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


def panel_loc_keys(names, types, loc):
    """The loc keys another country's panel renders: those the open types'
    unguarded text names, and every key they reach, less a key shown only for
    the player's own country (the first branch of a SelectLocalization on
    Country.IsLocalPlayer, which another country's panel never renders)."""
    roots = set()
    for name in open_types(names, types):
        roots |= gui_keys(unguarded(types[name].body), loc, own=False)
    return loc_closure(roots, loc, own=False)


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


def personal_text(keys, loc):
    """The keys whose text speaks as the player ("our", "you"), with the text:
    another country's panel shows them. Markup, splices and formatting left out."""
    out = {}
    for key in sorted(keys):
        text = re.sub(r"\[[^\]]*\]|\$[\w.\-]+\$|#\w+|\\n", " ", loc[key])
        if PERSONAL.search(text):
            out[key] = text
    return out
