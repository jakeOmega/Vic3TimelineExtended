#!/usr/bin/env python3
"""What a system tab's panel reads that another country's panel can't show, and the mechanical rewrite.

National Info (docs/superpowers/specs/2026-11-02-charts-help-national-info-design.md
§§ 6.3-6.8) shows a system's tab for any country, so a public tab's sections read the
shown country as `Country`: JournalEntry and the player appear only under
te_own_country_only, or as a world read (a `# world: <why>` line in markup, WORLD_LOC
in loc). test_te_system_tab_bodies.py's BindingTest and GuardTest hold each public tab
to that. This tool is what a system's binding PR runs first: it lists what the tab
still reads, grouped by type and by loc key, with the file:line and the class of
each read, and --write does the mechanical part.

    python3 scripts/analysis/te_rebind_country.py <tab key | type> [--write] [--all] [--summary]

From Python, survey_tab(key) is the same listing as data (a Survey: markup and
loc reads with their classes, the controls, the text), and write(survey) the
rewrite.

It walks what the tests walk: the tab's wide composer (gen_te_systems_window.TABS),
every type it draws outside te_own_country_only, and every loc key their text renders
(gui_test_helpers.open_types, markup_reads, panel_loc_keys). A read is one of:

  mechanical    `JournalEntry.GetCountry.` or `GetPlayer.`, which becomes `Country.`.
                --write rewrites these, and only these.
  entry-only    another JournalEntry read (IsActive, the scripted bars, the goal, the
                Open Journal Entry button) or GetPlayerJournalEntry: another country
                has no entry. Guard it, or read the variable behind it. A composer's
                IsActive becomes the tab's own gate on Country (printed with it).
  bare          `GetPlayer` or `JournalEntry.GetCountry` with nothing read from it (a
                datacontext, an argument): drop it, or pass Country.Self.
  player-other  AccessPlayer, GetPlayer<X>: Country's own function by hand, or a guard
                (AccessPlayer's lists need a non-const Country: gotcha #35).
  shadowed      a mechanical read under a datacontext or datamodel that names some
                other country (a row's Scope.GetCountry, a bloc's members), where
                `Country` is that country. Read the shown Country from a block outside
                the row's datacontext.
  shared        (loc) a key something else renders where no Country is in context: a
                journal entry's own text (its status_desc, desc or a scripted progress
                bar), other script (a custom tooltip, an event), or a vanilla-copied
                panel (the state panel). Split it: a `_ni` copy for the panel. It errs
                wide: any script token that spells the key counts, so look before
                splitting.
  item tooltip  (loc) a key a tooltip inside a datamodel's item renders. Gotcha #24
                found a chart bar's (the item's own widget) has only the item's
                context; a tooltip deeper in an item is unverified, so it is left too.
                A world read keeps the player's copy and goes in WORLD_LOC; bind the
                rest by hand and check it in game, or guard the control it is on.

Reads in a generated file change in its generator, which the listing names; --write
leaves them. After the reads come the controls to guard (GuardTest) and the text that
speaks as the player (BindingTest.test_the_text_is_not_the_players). Each mod panel
has a Country since PR F0's mounts, so a key another mod panel also names is not
shared on that account. Only the vanilla-copied hosts lack one.
"""

import argparse
import collections
import functools
import glob
import os
import re
import sys
from dataclasses import dataclass, field

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import gui_test_helpers as h  # noqa: E402

MECHANICAL = ("JournalEntry.GetCountry", "GetPlayer")
NEW = "Country"
CLASSES = ("mechanical", "entry-only", "bare", "player-other", "shadowed", "shared", "item tooltip")
WRITABLE = {"mechanical"}

# A datacontext or datamodel whose last call names a country other than the panel's
# (or might: a leader can be a character, and is flagged all the same).
_CONTEXT = re.compile(r'\b(datacontext|datamodel)\s*=\s*"\[(.*?)\]"')
_OTHER = re.compile(r"^(?:Get|Access)?(?:Top)?(?:Country|Countries|Owner|Overlord|Leader|Members?|Subjects?"
                    r"|Ally|Allies|Rivals?|Target|Player\w*|Hegemon)$", re.I)
_SAME = {"JournalEntry.GetCountry", "Country", "Country.Self"}
_DATAMODEL = re.compile(r"\bdatamodel\s*=")
_TOOLTIP = re.compile(r'\btooltip\s*=\s*"([^"]*)"')
# A chart bar's tooltip, which the chart's instance fills from outside its datamodel.
_BAR_TOOLTIP = re.compile(r'blockoverride\s+"bar_tooltip"\s*\{')
_GENERATED = re.compile(r"AUTO-GENERATED", re.I)
_GENERATOR = re.compile(r"scripts/generators/[\w/]+\.py")
_TOKEN = re.compile(r"[A-Za-z_][\w.\-]*")
_JE_TOP = re.compile(r"(?m)^(\w+)\s*=\s*\{")


def _other_country(expr):
    """Whether a datacontext's or datamodel's expression gives some other country."""
    e = expr.strip()
    if e in _SAME:
        return False
    while True:
        flat = re.sub(r"\([^()]*\)", "", e)
        if flat == e:
            break
        e = flat
    return bool(_OTHER.match(e.split(".")[-1].strip()))


def _read_kind(read, after):
    if h.is_entry_read(read) and read != "JournalEntry.GetCountry":
        return "entry-only"
    if read in MECHANICAL:
        return "mechanical" if after == "." else "bare"
    return "player-other"


@functools.lru_cache(maxsize=None)
def _file_lines(root, path):
    return h._read(os.path.join(root, path)).split("\n")


@functools.lru_cache(maxsize=None)
def generator_of(root, path):
    """The generator a file's header names, '' for a file written by hand."""
    head = "\n".join(_file_lines(root, path)[:4])
    if not _GENERATED.search(head):
        return ""
    m = _GENERATOR.search(head)
    return m.group(0) if m else "its generator"


@dataclass
class Read:
    """One read: its class, the Finding, why it is shadowed, and the block whose
    default holds it (a shared type's `block "x"`), if any."""
    cls: str
    finding: h.Finding
    why: str = ""
    block: str = ""


_BLOCK = re.compile(r'\bblock\s+"(\w+)"\s*\{')


@functools.lru_cache(maxsize=None)
def _block_spans(body):
    """Each `block "x" { ... }` default in a body: (start, end, name)."""
    return [(m.end() - 1, h._close(body, m.end() - 1), m.group(1)) for m in _BLOCK.finditer(body)]


@dataclass
class KeyReport:
    key: str
    path: str
    line: int
    notes: list = field(default_factory=list)
    reads: list = field(default_factory=list)
    generated: str = ""


@dataclass
class Survey:
    target: str
    wide: str
    root: str
    types: set
    drawn_at: dict
    generated: dict
    markup: list
    world_markup: int
    loc: dict
    world_loc: set
    controls: list
    text: dict
    gate: str | None
    where: dict = field(default_factory=dict)


def _walk(names, types):
    """Each type another country's panel draws (open_types), with the first place
    it is drawn, why `Country` may be some other country in it (None: never), and
    the spans in its body where it is: (start, end, context start, context end,
    why, items only). A datacontext's span is its widget, whose own properties
    read it; a datamodel's is what its widget holds, its items. Also each type
    drawn inside a datamodel's item, and each body's datamodels (widget start,
    end, place)."""
    other, item, drawn_at, spans_of, items_of = {}, {}, {}, {}, {}
    todo = [(n, None, None) for n in sorted(names) if n in types]
    while todo:
        name, why, in_item = todo.pop()
        if name in other and (other[name] is not None or why is None) and (item[name] is not None or in_item is None):
            continue
        other[name] = other.get(name) or why
        item[name] = item.get(name) or in_item
        td = types[name]
        body = td.body
        guards = h.guard_spans(body)
        if (0, len(body)) in guards:
            continue
        if name not in spans_of:
            spans, items = [], []
            for m in _CONTEXT.finditer(body):
                where = f"{td.path}:{td.line + h._line_of(td, m.start())}"
                a, b = h.enclosing_block(body, m.start())
                model = m.group(1) == "datamodel"
                if _other_country(m.group(2)):
                    spans.append((a, b, m.start(), m.end(), f'{where} {m.group(1)} = "[{m.group(2)}]"', model))
                if model:
                    items.append((a, b, f"{where} datamodel"))
            spans_of[name], items_of[name] = spans, items
        for m in h._CHILD.finditer(body):
            child, pos = m.group(1), m.end() - 1
            if child not in types or h.in_spans(pos, guards):
                continue
            drawn_at.setdefault(child, f"{td.path}:{td.line + h._line_of(td, pos)}")
            todo.append((child, other[name] or _span_why(pos, spans_of[name]),
                         item[name] or next((w for a, b, w in items_of[name] if a < pos < b), None)))
        if td.base in types:
            todo.append((td.base, other[name], item[name]))
    return other, item, drawn_at, spans_of, items_of


def _span_why(pos, spans, body=None):
    """Why `Country` at a body offset is another country, or None. With the body,
    the offset is a read's, and a datamodel's own widget reads in its parent's
    context; without, it is a child's brace, inside the widget and so an item."""
    for a, b, ms, me, why, model in spans:
        if not (a <= pos <= b) or ms <= pos < me:
            continue
        if model and (pos == a or (body is not None and h.enclosing_block(body, pos)[0] == a)):
            continue
        return why
    return None


def _inner_blocks(body, a, b):
    """The blocks directly inside the block from a to b: a datamodel's items."""
    out, i = [], a + 1
    while i < b:
        if body[i] == "{":
            end = h._close(body, i)
            out.append((i, end))
            i = end
        i += 1
    return out


def _keys_where(names, types, loc, pick):
    """{key: why} for the loc closure of the keys named in the parts of each type
    that `pick(name, body)` gives: a list of (start, end, why), or None."""
    roots = {}
    for name in sorted(names):
        body = h.unguarded(types[name].body)
        for a, b, why in pick(name, body) or ():
            for key in _gui_keys(body[a:b + 1], loc):
                roots.setdefault(key, why)
    return _closure_with_source(roots, loc)


def _closure_with_source(roots, loc):
    """{key: source} for the roots and every key they reach (loc_closure, own=False),
    each with the source of the first root that reaches it."""
    out, todo = {}, collections.deque(roots.items())
    while todo:
        key, source = todo.popleft()
        if key in out or key not in loc:
            continue
        out[key] = source
        value = h._OWN_BRANCH.sub(r"\1''", loc[key])
        todo.extend((k, source) for k in re.findall(r"\$([\w.\-]+)\$", value))
        todo.extend((k, source) for k in re.findall(r"'([\w.\-]+)'", value) if k in loc)
    return out


_PROP_KEY = re.compile(r'(?:text|tooltip|raw_text)\s*=\s*"([\w.\-]+)"')
_EXPR = re.compile(r'"\[(.*?)\]"')
_QUOTED = re.compile(r"'([\w.\-]+)'")


def _gui_keys(text, loc):
    """gui_keys(text, loc, own=False), for many calls: membership in loc, not a set of it."""
    text = h._OWN_BRANCH.sub(r"\1''", text)
    out = {k for k in _PROP_KEY.findall(text) if k in loc}
    for expr in _EXPR.findall(text):
        out.update(k for k in _QUOTED.findall(expr) if k in loc)
    return out


def _script_keys(root, loc, types):
    """Each loc key something other than a mod panel renders, with what renders it:
    a journal entry's own text, a scripted progress bar, other script, or a
    vanilla-copied panel, reached through its splices."""
    roots = {}

    def name(key, source):
        if key in loc:
            roots.setdefault(key, source)

    for path in sorted(glob.glob(os.path.join(root, "common", "journal_entries", "*.txt"))):
        rel = os.path.relpath(path, root)
        text = h._read(path)
        for m in _JE_TOP.finditer(text):
            for suffix in ("", "_reason", "_goal", "_desc"):
                name(m.group(1) + suffix, f"journal entry text ({rel}:{text.count(chr(10), 0, m.start()) + 1})")
    for sub, label in (("common/journal_entries", "journal entry text"),
                       ("common/scripted_progress_bars", "scripted progress bar"),
                       ("common", "script"), ("events", "event")):
        for path in sorted(glob.glob(os.path.join(root, sub, "**", "*.txt"), recursive=True)):
            rel = os.path.relpath(path, root)
            for n, line in enumerate(h._read(path).split("\n"), 1):
                code = line.split("#", 1)[0]
                if code.strip():
                    for tok in _TOKEN.findall(code):
                        name(tok, f"{label} ({rel}:{n})")
    mod, named = set(h.mod_gui_paths(root)), {}
    for path in sorted(glob.glob(os.path.join(root, "gui", "**", "*.gui"), recursive=True)):
        rel = os.path.relpath(path, root)
        if rel in mod:
            continue
        text = h._strip_comments(h._read(path))
        lines = text.split("\n")
        for n, line in enumerate(lines, 1):
            if '"' in line:
                for key in _gui_keys(line, loc):
                    name(key, f"vanilla-copied panel ({rel}:{n})")
        for m in h._CHILD.finditer(text):
            host = m.group(1)
            if host in types and not _is_frame(host, types):
                n = text.count("\n", 0, m.start()) + 1
                for t in h.type_closure({host}, types):
                    if t not in named:
                        named[t] = _gui_keys(types[t].body, loc)
                    for key in named[t]:
                        name(key, f"vanilla-copied panel ({rel}:{n}, through {host})")
    return _closure_with_source(roots, loc)


def _is_frame(name, types):
    """A tab body: its frame's root supplies the player's Country (block tab_country)."""
    seen = set()
    while name in types and name not in seen:
        if name == "te_system_tab_frame":
            return True
        seen.add(name)
        name = types[name].base
    return False


def survey(target, root=REPO, world_loc=(), gate=None):
    """Everything the tool reports for a wide composer (a tab's, or any type)."""
    types = h.mod_types(root)
    index = h.loc_index(os.path.join(root, "localization", "english"), root)
    loc = {k: v for k, (v, _, _) in index.items()}
    names = {target}
    other, item, drawn_at, spans_of, items_of = _walk(names, types)
    opened = h.open_types(names, types)

    markup, world_markup, generated = [], 0, {}
    for f in h.markup_reads(names, types):
        if f.world:
            world_markup += 1
            continue
        line = _file_lines(root, f.path)[f.line - 1]
        kind = _read_kind(f.what, line[f.col + len(f.what):f.col + len(f.what) + 1])
        td = types[f.where]
        # body offset of the read, from its line and column
        k = f.line - td.line
        pos = h._line_starts(td.body)[k] + f.col - (td.col if k == 0 else 0)
        why = ""
        if kind == "mechanical":
            why = other.get(f.where) or _span_why(pos, spans_of.get(f.where, []), td.body) or ""
            if why:
                kind = "shadowed"
        block = next((name for a, b, name in _block_spans(td.body) if a < pos < b), "")
        markup.append(Read(kind, f, why, block))
        generated.setdefault(f.path, generator_of(root, f.path))

    keys = h.panel_loc_keys(names, types, loc)
    world_loc = set(world_loc)
    shared = _script_keys(root, loc, types)
    def shadowed(n, b):
        if other.get(n):
            return [(0, len(b), other[n])]
        out = []
        for a, e, _, _, why, model in spans_of.get(n, []):
            out += [(c, d, why) for c, d in _inner_blocks(b, a, e)] if model else [(a, e, why)]
        return out

    def item_tooltips(n, b):
        if item.get(n):
            return [(m.start(), m.end(), item[n]) for m in _TOOLTIP.finditer(b)]
        out = [(m.start(), m.end(), why) for a, e, why in items_of.get(n, []) for m in _TOOLTIP.finditer(b, a, e)
               if h.enclosing_block(b, m.start())[0] != a]
        td = types[n]
        return out + [(*h.enclosing_block(b, m.end()), f"{td.path}:{td.line + h._line_of(td, m.start())} bar_tooltip")
                      for m in _BAR_TOOLTIP.finditer(b)]

    shadow_keys = _keys_where(opened, types, loc, shadowed)
    item_keys = _keys_where(opened, types, loc, item_tooltips)
    report = {}
    for f in h.loc_reads(keys - world_loc, index):
        kr = report.get(f.where)
        if kr is None:
            kr = report[f.where] = KeyReport(f.where, f.path, f.line, generated=generator_of(root, f.path))
            if f.where in shared:
                kr.notes.append(("shared", shared[f.where]))
            if f.where in item_keys:
                kr.notes.append(("item tooltip", item_keys[f.where]))
            if f.where in shadow_keys:
                kr.notes.append(("shadowed", shadow_keys[f.where]))
        pos = f.text.find(f.what)
        kind = _read_kind(f.what, f.text[pos + len(f.what):pos + len(f.what) + 1])
        if kind == "mechanical" and kr.notes:
            kind = kr.notes[0][0]
        kr.reads.append(Read(kind, f))

    text = h.personal_text(keys, loc)
    return Survey(target, target, root, opened, drawn_at, generated, markup, world_markup, report,
                  world_loc & keys, h.unguarded_controls(names, types), text, gate,
                  {k: index[k][1:] for k in text})


def counts(s):
    out = collections.Counter()
    for r in s.markup:
        out[("markup", r.cls)] += 1
    for kr in s.loc.values():
        for r in kr.reads:
            out[("loc", r.cls)] += 1
    return out


def _lines(nums, cap):
    nums = sorted(set(nums))
    shown = " ".join(f":{n}" for n in nums[:cap])
    return shown + (f" ... (+{len(nums) - cap})" if len(nums) > cap else "")


HINTS = {
    "entry-only": "guard it, or read the variable behind it",
    "bare": "drop it, or pass Country.Self",
    "player-other": "Country's own function by hand, or guard it (gotcha #35)",
    "shadowed": "Country here is another country: read the shown one from a block outside",
    "shared": "split it: a _ni copy for the panel, the original left as it is",
    "item tooltip": ("a chart bar's has only the item's context (gotcha #24); deeper in an item is unverified. "
                     "A world read goes in WORLD_LOC; else bind it and check in game, or guard its control"),
}


def render(s, full=False, summary=False):
    out = []
    c = counts(s)
    out.append(f"{s.target}: {len(s.types)} types and {sum(1 for _ in s.loc)} loc keys with reads, "
               f"{len(s.controls)} controls to guard, {len(s.text)} keys speaking as the player")
    for part in ("markup", "loc"):
        row = "  ".join(f"{cls} {c[(part, cls)]}" for cls in CLASSES if c[(part, cls)])
        out.append(f"  {part:7} {row or 'nothing to bind'}")
    out.append(f"  already world reads: {s.world_markup} in markup, {len(s.world_loc)} keys in WORLD_LOC")
    if summary:
        return "\n".join(out)

    by_type = collections.defaultdict(list)
    for r in s.markup:
        by_type[r.finding.where].append(r)
    if by_type:
        out += ["", "Markup, by type (file:line)"]
    for name in sorted(by_type, key=lambda n: (by_type[n][0].finding.path, by_type[n][0].finding.line)):
        reads = by_type[name]
        f0 = reads[0].finding
        head = f"  {name}  {f0.path}"
        if name in s.drawn_at:
            head += f"  (drawn at {s.drawn_at[name]})"
        if s.generated.get(f0.path):
            head += f"  [generated: change {s.generated[f0.path]}]"
        out.append(head)
        mech = [r for r in reads if r.cls == "mechanical"]
        if mech and not full:
            out.append(f"    mechanical    {len(mech)}  {_lines([r.finding.line for r in mech], 20)}")
        rows = collections.Counter((r.finding.line, r.cls, r.finding.what) for r in reads
                                   if full or r.cls != "mechanical")
        first = {}
        for r in reads:
            first.setdefault((r.finding.line, r.cls, r.finding.what), r)
        for (line, cls, what), n in sorted(rows.items()):
            r = first[(line, cls, what)]
            times = f" x{n}" if n > 1 else ""
            out.append(f"    {cls:13} :{line}  {what}{times}  | {r.finding.text.strip()[:110]}")
            if cls == "shadowed":
                out.append(f"                  under {r.why}")
            if cls == "entry-only" and what == "JournalEntry.IsActive" and s.gate:
                out.append(f"                  the tab's gate on Country: [{s.gate}]")
            if r.block and cls != "mechanical":
                where = f" (drawn at {s.drawn_at[name]})" if name in s.drawn_at else ""
                out.append(f'                  the default of block "{r.block}" of {name}, which other panels '
                           f'draw too: leave it, and give this panel a blockoverride "{r.block}" where it draws '
                           f'{name}{where}')
    if s.loc:
        out += ["", "Loc, by key (file:line)"]
    for key in sorted(s.loc, key=lambda k: (s.loc[k].path, s.loc[k].line)):
        kr = s.loc[key]
        tally = collections.Counter((r.cls, r.finding.what) for r in kr.reads)
        reads = ", ".join(f"{cls} {what}" + (f" x{n}" if n > 1 else "") for (cls, what), n in sorted(tally.items()))
        head = f"  {key}  {kr.path}:{kr.line}  {reads}"
        if kr.generated:
            head += f"  [generated: change {kr.generated}]"
        out.append(head)
        for cls, source in kr.notes:
            out.append(f"    {cls}: {source}  -> {HINTS[cls]}")
    if s.controls:
        out += ["", "Controls to guard (GuardTest): put each under te_own_country_only, a wrapper where it has a visible"]
        out += [f"  {f}" for f in s.controls]
    if s.text:
        out += ["", "Text that speaks as the player (spec § 6.8): neutral, or SelectLocalization( Country.IsLocalPlayer, ... )"]
        out += [f"  {key}  {s.where[key][0]}:{s.where[key][1]}  | {' '.join(text.split())[:100]}"
                for key, text in s.text.items()]
    out += ["", "Classes: " + "; ".join(f"{k}: {v}" for k, v in HINTS.items()),
            "Next: --write for the mechanical reads, the rest by hand, then "
            "test_te_system_tab_bodies.py (BindingTest, GuardTest)."]
    return "\n".join(out)


def _bom_write(path, lines):
    """Write the lines back, with the one BOM the file had (or none)."""
    with open(path, "rb") as fh:
        bom = fh.read(3) == b"\xef\xbb\xbf"
    with open(path, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as fh:
        fh.write("\n".join(lines))


def write(s):
    """Rewrite the mechanical reads: in the closure's types and loc keys, outside
    generated files. Returns {path: reads rewritten}."""
    edits = collections.defaultdict(list)  # path -> (line, col, old)
    for r in s.markup:
        f = r.finding
        if r.cls in WRITABLE and not s.generated.get(f.path):
            edits[f.path].append((f.line, f.col, f.what + "."))
    loc_sub = re.compile(r"(?<![\w.])(?:JournalEntry\.GetCountry|GetPlayer)\.")
    for kr in s.loc.values():
        if kr.generated or kr.notes or not any(r.cls in WRITABLE for r in kr.reads):
            continue
        edits[kr.path].append((kr.line, None, None))
    done = {}
    for path, todo in sorted(edits.items()):
        full = os.path.join(s.root, path)
        with open(full, encoding="utf-8-sig", newline="") as fh:
            lines = fh.read().split("\n")
        n = 0
        # right to left along a line, so each column still holds
        for line, col, old in sorted(todo, key=lambda e: (e[0], e[1] or 0), reverse=True):
            text = lines[line - 1]
            if col is None:
                q = text.index('"')
                new, k = loc_sub.subn(NEW + ".", text[q:])
                lines[line - 1], n = text[:q] + new, n + k
            elif text[col:col + len(old)] == old:
                lines[line - 1], n = text[:col] + NEW + "." + text[col + len(old):], n + 1
            else:
                print(f"skipped {path}:{line}:{col}: expected {old!r}", file=sys.stderr)
        _bom_write(full, lines)
        done[path] = n
    h._mod_types.cache_clear()
    h._loc_index.cache_clear()
    _file_lines.cache_clear()
    return done


def _tab(key):
    from scripts.generators import gen_te_systems_window as gen
    return next((t for t in gen.TABS if t.key == key), None), gen


def world_loc_keys():
    """test_te_system_tab_bodies.WORLD_LOC: the loc keys that are world reads."""
    try:
        from test_te_system_tab_bodies import WORLD_LOC
    except ImportError:
        return {}
    return WORLD_LOC


def survey_tab(key, root=REPO):
    """survey() of a tab (gen_te_systems_window.TABS) as BindingTest sees it:
    its wide composer, WORLD_LOC, and its gate on Country for IsActive reads."""
    tab, gen = _tab(key)
    if tab is None:
        raise KeyError(f"{key}: no such tab in gen_te_systems_window.TABS")
    s = survey(tab.wide, root, world_loc_keys(), gen.rooted(tab.open_, gen.COUNTRY_ROOT))
    s.target = f"{tab.key} ({tab.wide})"
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("target", help="a tab key (gen_te_systems_window.TABS) or a type name")
    ap.add_argument("--write", action="store_true", help="rewrite the mechanical reads, then list what is left")
    ap.add_argument("--all", action="store_true", help="list each mechanical read in full")
    ap.add_argument("--summary", action="store_true", help="the counts only")
    ap.add_argument("--root", default=REPO, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    is_tab = args.root == REPO and _tab(args.target)[0] is not None
    if not is_tab and args.target not in h.mod_types(args.root):
        ap.error(f"{args.target}: neither a tab key nor a type in the mod's GUI files")

    def run():
        return survey_tab(args.target) if is_tab else survey(args.target, args.root)

    s = run()
    if args.write:
        done = write(s)
        print(f"rewrote {sum(done.values())} reads in {len(done)} files" +
              "".join(f"\n  {p}: {n}" for p, n in done.items()))
        s = run()
        print("\nWhat is left:")
    print(render(s, full=args.all, summary=args.summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
