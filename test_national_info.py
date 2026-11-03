"""National Info: the Census Data window, renamed, with a tab per public system
(spec docs/superpowers/specs/2026-11-02-charts-help-national-info-design.md §§ 6.2,
7.3; plan PR F1).

The window (gui/pop_browser_panel.gui) shows the country it was opened for.
Its strip, its selection templates and its column of mounts are generated from
the Timeline Extended window's TABS registry
(scripts/generators/gen_te_systems_window.py, the public tabs in NI_ORDER) into
gui/te_national_info_generated.gui. These tests hold:

* the shown tab: the last one chosen while it is open for the window's country,
  otherwise Pops (evaluated per stored value, today's public tabs and every
  tab National Info is to show);
* the strips: five a strip, in NI_ORDER, every gate on the window's Country;
* the mounts: the player's own country's is the window's full-screen mount,
  another country's the tab's header, its readout and its wide composer, with
  no journal entry and no frame;
* the registry's readouts, against the bodies' tab_before_gate;
* the generated file.
"""
import glob
import os
import re
import unittest
from dataclasses import replace
from unittest import mock

from gui_test_helpers import (_block_at, _children, _close, _read, _split_args, _strip_comments, markup_reads,
                              mod_types)
from scripts.generators import gen_te_systems_window as gen

REPO = os.path.dirname(os.path.abspath(__file__))
GENERATED = os.path.join(REPO, "gui", "te_national_info_generated.gui")
POPUPS = os.path.join(REPO, "gui", "te_popups.gui")
LOCAL = "Country.IsLocalPlayer"


def _template(text, name):
    m = re.search(rf'^template {name} \{{\n\tvisible = (?:"\[(.*)\]"|(yes|no))\n\}}', text, re.M)
    assert m, f"no template {name}"
    return m.group(1) or m.group(2)


def _type_body(text, name):
    m = re.search(rf"\btype {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    return text[m.end():_close(text, m.end() - 1)]


# --- a small evaluator: gates on the window's Country, the stored tab, the local player ---------------------------

_ATOM = re.compile(r"GetScriptedGui\('(\w+)'\)\.(IsShown|IsValid)\( GuiScope\.SetRoot\( Country\.MakeScope \)\.End \)"
                   r"|GetVariableSystem\.HasValue\('(\w+)', '(\w+)'\)"
                   r"|(Country\.IsLocalPlayer)")


def _atoms(expr):
    if expr is None:
        return set()
    return {m.group(1) if m.group(2) == "IsShown" else f"{m.group(1)}:valid"
            for m in _ATOM.finditer(expr) if m.group(1)}


def _evaluate(expr, shown, stored, local=False):
    """An And/Or/Not expression of scripted-GUI gates on Country, the stored
    te_ni_tab value and Country.IsLocalPlayer. `shown` holds the gates that
    pass: a bare name for IsShown, `<name>:valid` for IsValid."""
    if expr in ("yes", "no"):
        return expr == "yes"

    def atom(m):
        if m.group(1):
            name = m.group(1) if m.group(2) == "IsShown" else f"{m.group(1)}:valid"
            return "T" if name in shown else "F"
        if m.group(5):
            return "T" if local else "F"
        assert m.group(3) == gen.NI_STORED, m.group(0)
        return "T" if stored == m.group(4) else "F"
    s = _ATOM.sub(atom, expr)
    assert "GetPlayer" not in s, s
    s = s.replace("And(", "_and(").replace("Or(", "_or(").replace("Not(", "_not(")
    assert re.fullmatch(r"[\s_andortTF(),]*", s), s
    return eval(s, {"_and": lambda a, b: a and b, "_or": lambda a, b: a or b,  # noqa: S307
                    "_not": lambda a: not a, "T": True, "F": False})


def _pick(expr, shown, local):
    """The loc a tooltip expression picks: a key, or ('checklist', its lead
    line) for the grayed tab's Concatenate."""
    expr = expr.strip()
    if expr.startswith("'"):
        return expr.strip("'")
    if expr.startswith("SelectLocalization("):
        inner = expr[expr.index("(") + 1:expr.rindex(")")]
        cond, a, b = _split_args(inner)
        return _pick(a if _evaluate(cond, shown, None, local) else b, shown, local)
    m = re.match(r"Concatenate\( Localize\( '(\w+)' \), GetScriptedGui\('(\w+)'\)\.IsValidTooltip\(", expr)
    assert m, expr
    return ("checklist", m.group(1))


def _cases(tabs):
    """Every stored value against each tab's state: the stored tab in each of
    (closed, off the strip), (closed, on it), (open, on it), every other tab in
    one shared state. Each template reads only its own tab's gates and stored
    value (test_templates_read_only_their_gates), so this covers every case."""
    states = [(False, False), (False, True), (True, True)]
    keys = [t.key for t in tabs]
    for stored in [None, gen.NI_FALLBACK, "unknown"] + keys:
        for own in (states if stored in keys else [None]):
            for rest in states:
                shown = set()
                for t in tabs:
                    opened, on_strip = own if t.key == stored else rest
                    if opened:
                        shown |= _atoms(gen.ni_open_gate(t))
                    if on_strip:
                        shown |= _atoms(gen.rooted(t.strip, gen.COUNTRY_ROOT))
                # the states enumerated are the gates' own, compound ones too
                for t in tabs:
                    opened, on_strip = own if t.key == stored else rest
                    for gate, want in ((gen.ni_open_gate(t), opened), (t.strip and gen.rooted(t.strip, gen.COUNTRY_ROOT),
                                                                         on_strip)):
                        if gate is not None:
                            assert _evaluate(gate, shown, stored) == want, (t.key, gate)
                yield stored, shown


# --- "open implies on the strip": the scripted GUIs' is_shown, scripted triggers expanded --------------------

_SHOWN = r"GetScriptedGui\('(\w+)'\)\.IsShown\( GuiScope\.SetRoot\( GetPlayer\.MakeScope \)\.End \)"
_TOKEN = re.compile(r'"[^"]*"|[{}]|[<>!?]?=|[<>]|[^\s{}=<>!?]+')


def _definitions(folder):
    """name -> the text of its { } body, for each top-level `name = {` in the
    mod's .txt files in `folder`."""
    out = {}
    for path in sorted(glob.glob(os.path.join(REPO, "common", folder, "*.txt"))):
        text = re.sub(r"#[^\n]*", "", open(path, encoding="utf-8-sig").read())
        for m in re.finditer(r"^(\w+)\s*=\s*\{", text, re.M):
            out.setdefault(m.group(1), text[m.end():_close(text, m.end() - 1)])
    return out


def _parse(text):
    """A body's statements, (key, op, value), a block's value its statements."""
    tokens, out, stack = _TOKEN.findall(text), [], []
    i = 0
    while i < len(tokens):
        if tokens[i] == "}":
            key, op, inner = stack.pop()
            inner.append((key, op, out))
            out = inner
            i += 1
        elif tokens[i + 2:i + 3] == ["{"]:
            stack.append((tokens[i], tokens[i + 1], out))
            out = []
            i += 3
        else:
            out.append((tokens[i], tokens[i + 1], tokens[i + 2]))
            i += 3
    assert not stack, text[:80]
    return out


_SGUIS, _TRIGGERS = {}, {}


def _norm(item):
    key, op, value = item
    return f"{key} {op} " + (value if isinstance(value, str) else "{ " + " ".join(map(_norm, value)) + " }")


def _trigger(item):
    key, op, value = item
    if (op, value) == ("=", "yes"):
        if not _TRIGGERS:
            _TRIGGERS.update(_definitions("scripted_triggers"))
        body = _TRIGGERS.get(key)
        if body is not None and "$" not in body:
            return _parse(body)
    return None


def _flat(items):
    """The conditions a list of them asserts: AND blocks and scripted triggers
    expanded, anything else as it is written."""
    out = set()
    for item in items:
        body = _trigger(item)
        if body is not None:
            out |= {_norm(item)} | _flat(body)
        elif item[0] == "AND" and not isinstance(item[2], str):
            out |= _flat(item[2])
        else:
            out.add(_norm(item))
    return out


def _implied(conds, item):
    if _norm(item) in conds:
        return True
    body = _trigger(item)
    if body is not None:
        return all(_implied(conds, x) for x in body)
    key, _, value = item
    if key == "AND" and not isinstance(value, str):
        return all(_implied(conds, x) for x in value)
    if key == "OR" and not isinstance(value, str):
        return any(_implied(conds, x) for x in value)
    return False


def _is_shown(sgui):
    if not _SGUIS:
        _SGUIS.update(_definitions("scripted_guis"))
    found = [v for k, _, v in _parse(_SGUIS[sgui]) if k == "is_shown"]
    assert len(found) == 1, sgui
    return found[0]


def _expr_implies(expr, strip):
    """Whether a gate expression (And/Or/Not of scripted GUIs on the player)
    can be true only while `strip`'s is_shown is."""
    expr = expr.strip()
    for op, combine in (("And(", any), ("Or(", all)):
        if expr.startswith(op):
            return combine(_expr_implies(a, strip) for a in _split_args(expr[len(op):expr.rindex(")")]))
    m = re.fullmatch(_SHOWN, expr)
    if not m:
        return False
    conds = _flat(_is_shown(m.group(1)))
    return all(_implied(conds, item) for item in _is_shown(strip))


def _every_candidate_public():
    """TABS with every tab National Info is to show made public, as once each
    system's PR has landed."""
    return [replace(t, public=True) if t.key in gen.NI_ORDER else t for t in gen.TABS]


class SelectionTest(unittest.TestCase):
    """The tab shown: the last one chosen while it is open for the window's
    country, otherwise Pops (Review Focus 6), for today's public tabs and with
    every tab National Info is to show public."""

    def _check(self, text, tabs):
        sel = {t.key: _template(text, f"te_ni_{t.key}_selected") for t in tabs}
        unsel = {t.key: _template(text, f"te_ni_{t.key}_unselected") for t in tabs}
        pops, pops_un = _template(text, "te_ni_pops_selected"), _template(text, "te_ni_pops_unselected")
        content = _template(text, "te_ni_content_shown")
        strip = _template(text, "te_ni_strip_shown")
        cases = 0
        for stored, shown in _cases(tabs):
            cases += 1
            want = next((t.key for t in tabs if t.key == stored
                         and (t.open_ is None or _evaluate(gen.ni_open_gate(t), shown, stored))),
                        gen.NI_FALLBACK)
            with self.subTest(stored=stored, shown=sorted(shown)):
                self.assertEqual(_evaluate(pops, shown, stored), want == gen.NI_FALLBACK)
                self.assertEqual(_evaluate(pops_un, shown, stored), want != gen.NI_FALLBACK)
                self.assertEqual(_evaluate(content, shown, stored), want != gen.NI_FALLBACK,
                                 "the column is up exactly while Pops isn't")
                self.assertEqual(_evaluate(strip, shown, stored),
                                 any(t.strip is None or _evaluate(gen.rooted(t.strip, gen.COUNTRY_ROOT), shown, stored)
                                     for t in tabs), "the strip is up while any tab is on it")
                for t in tabs:
                    s, u = _evaluate(sel[t.key], shown, stored), _evaluate(unsel[t.key], shown, stored)
                    self.assertEqual(s, t.key == want)
                    on_strip = t.strip is None or _evaluate(gen.rooted(t.strip, gen.COUNTRY_ROOT), shown, stored)
                    self.assertFalse(s and u)
                    self.assertEqual(s or u, on_strip, "one half shows while the tab is on the strip")
                    # neither half reads whether the country is the player's
                    self.assertEqual(_evaluate(sel[t.key], shown, stored, local=True), s)
        return cases

    def test_the_public_tabs(self):
        tabs = gen.ni_tabs()
        self.assertIn("demographics", [t.key for t in tabs], "F1 ships Pops and Demographics")
        self.assertEqual([t.key for t in tabs], [k for k in gen.NI_ORDER if k in {t.key for t in gen.TABS if t.public}])
        cases = self._check(_read(GENERATED), tabs)
        self.assertEqual(cases, 3 * 3 + len(tabs) * 9)

    def test_every_tab_national_info_is_to_show(self):
        with mock.patch.object(gen, "TABS", _every_candidate_public()):
            tabs = gen.ni_tabs()
            text = gen.render_ni()
        self.assertEqual([t.key for t in tabs], gen.NI_ORDER[1:])
        self._check(text, tabs)

    def test_templates_read_only_their_gates(self):
        """What makes the enumeration enough: a tab's templates read its own
        gates and stored value only; Pops' reads each tab's open gate only
        under that tab's stored value."""
        with mock.patch.object(gen, "TABS", _every_candidate_public()):
            tabs = gen.ni_tabs()
            text = gen.render_ni()
        for t in tabs:
            with self.subTest(tab=t.key):
                expr = _template(text, f"te_ni_{t.key}_selected") + _template(text, f"te_ni_{t.key}_unselected")
                own = _atoms(gen.ni_open_gate(t)) | _atoms(gen.rooted(t.strip, gen.COUNTRY_ROOT))
                self.assertLessEqual(_atoms(expr), own)
                self.assertEqual({m.group(4) for m in _ATOM.finditer(expr) if m.group(3)}, {t.key})
        pops = _template(text, "te_ni_pops_selected")
        for t in tabs:
            if t.open_ is not None:
                self.assertIn(gen.and_(gen.ni_stored(t.key), gen.ni_open_gate(t)), pops)

    def test_the_strip_shows_while_a_tab_could(self):
        """Its gate per case is _check's; here its form: the public tabs' strip
        gates, or `yes` once one of them has none (Nation)."""
        tabs = gen.ni_tabs()
        want = ("yes" if any(t.strip is None for t in tabs)
                else gen.rooted(gen.or_all([t.strip for t in tabs]), gen.COUNTRY_ROOT))
        self.assertEqual(_template(_read(GENERATED), "te_ni_strip_shown"), want)
        with mock.patch.object(gen, "TABS", _every_candidate_public()):
            self.assertEqual(_template(gen.render_ni(), "te_ni_strip_shown"), "yes")

    def test_a_tab_open_is_on_the_strip(self):
        """Every tab National Info is to show: its open gate implies its strip
        gate, or its column could show with the strip hidden and no way back
        to Pops. Read from the scripted GUIs' is_shown, scripted triggers
        expanded."""
        for t in gen.TABS:
            if t.key not in gen.NI_ORDER or t.strip is None:
                continue
            with self.subTest(tab=t.key):
                strip = re.fullmatch(_SHOWN, t.strip)
                self.assertTrue(strip, f"{t.key}: a strip gate of one scripted GUI")
                self.assertIsNotNone(t.open_, f"{t.key}: always open, so always on the strip")
                self.assertTrue(_expr_implies(t.open_, strip.group(1)),
                                f"{t.key}: open without {strip.group(1)}")
                if t.ni_open:
                    self.assertTrue(_expr_implies(gen.shown(t.ni_open), strip.group(1)),
                                    f"{t.key}: open for another country without {strip.group(1)}")


class StripTest(unittest.TestCase):
    """te_ni_strips: Pops, then each public tab in NI_ORDER, five a strip, at
    the narrow strip width; every gate on the window's Country."""

    @classmethod
    def setUpClass(cls):
        cls.text = _strip_comments(_read(GENERATED))
        cls.strips = _type_body(cls.text, "te_ni_strips")

    def _strip_keys(self, strips):
        out = []
        for m in re.finditer(r"\ttab_buttons = \{", strips):
            strip = _block_at(strips, m.start() + 1)
            out.append([re.search(r"GetVariableSystem\.Set\('te_ni_tab', '(\w+)'\)", block).group(1)
                        for block in re.findall(r'blockoverride "\w+_button_click" \{[^}]*\}', strip)])
            self.assertEqual(strip.count("minimumsize = { 540 -1 }"), 1)
            self.assertEqual(strip.count("maximumsize = { 540 -1 }"), 1)
        return out

    def test_strips_of_five_in_order(self):
        keys = [gen.NI_FALLBACK] + [t.key for t in gen.ni_tabs()]
        self.assertEqual(self._strip_keys(self.strips),
                         [keys[i:i + gen.NI_PER_STRIP] for i in range(0, len(keys), gen.NI_PER_STRIP)])
        with mock.patch.object(gen, "TABS", _every_candidate_public()):
            strips = _type_body(_strip_comments(gen.render_ni()), "te_ni_strips")
        keys = self._strip_keys(strips)
        self.assertEqual([len(k) for k in keys], [5, 5, 1])
        self.assertEqual(sum(keys, []), gen.NI_ORDER)
        # centered: the strips between two expands, as the full-screen frame's
        top = [name for _, name, _ in _children(strips)]
        self.assertEqual([n for n in top if n in ("expand", "tab_buttons")],
                         ["expand", "tab_buttons", "tab_buttons", "tab_buttons", "expand"])

    def test_no_player_read(self):
        self.assertNotIn("GetPlayer", _read(GENERATED))
        self.assertNotIn("AccessPlayer", _read(GENERATED))
        self.assertNotIn("JournalEntry", _read(GENERATED))
        self.assertIn("Country.MakeScope", self.strips)

    def test_each_tab_opens_on_its_gate_and_stores_the_choice(self):
        with mock.patch.object(gen, "TABS", _every_candidate_public()):
            every = gen.render_ni()
        for text, tabs in ((_read(GENERATED), gen.ni_tabs()), (every, [t for t in _every_candidate_public()
                                                                         if t.key in gen.NI_ORDER])):
            for t in tabs:
                with self.subTest(tab=t.key):
                    slot = re.search(rf"\t\t\t### {t.key}\n(.*?)(?=\n\t\t\t###|\n\t\t\}})", text, re.S).group(1)
                    if t.open_ is None:
                        self.assertNotIn("enabled", slot, "always open")
                    else:
                        self.assertIn(f'enabled = "[{gen.ni_open_gate(t)}]"', slot)
                    self.assertIn(f"onclick = \"[GetVariableSystem.Set('te_ni_tab', '{t.key}')]\"", slot)
                    self.assertIn(f"using = te_ni_{t.key}_selected", slot)
                    self.assertIn(f"using = te_ni_{t.key}_unselected", slot)
                    self.assertEqual(slot.count(f'text = "{t.label}"'), 2)
        pops = re.search(r"\t\t\t### pops\n(.*?)(?=\n\t\t\t###|\n\t\t\})", _read(GENERATED), re.S).group(1)
        self.assertNotIn("enabled", pops, "Pops is always open")
        self.assertIn('tooltip = "te_pop_browser_tab_pops_tt"', pops)
        self.assertIn("using = te_ni_pops_selected", pops)

    def test_the_tooltips(self):
        """Open: the window's tooltip for the player, what the country shows the
        world for another. Grayed: the player's checklist, one line for another.
        Every combination of the tooltip's gates, tooltip_expr's tabs too."""
        with mock.patch.object(gen, "TABS", _every_candidate_public()):
            tabs = gen.ni_tabs()
        for t in tabs:
            tooltip = re.fullmatch(r'tooltip = "\[(.*)\]"', gen.ni_tooltip(t)).group(1)
            player = gen._tooltip_value(t, gen.COUNTRY_ROOT)
            atoms = sorted(_atoms(tooltip) | _atoms(gen.ni_open_gate(t) or "yes"))
            for n in range(1 << len(atoms)):
                shown = {a for i, a in enumerate(atoms) if n >> i & 1}
                is_open = t.open_ is None or _evaluate(gen.ni_open_gate(t), shown, None)
                with self.subTest(tab=t.key, shown=sorted(shown)):
                    self.assertEqual(_pick(tooltip, shown, local=False),
                                     gen.NI_OTHER_TT if is_open else gen.NI_NOT_RUNNING_TT)
                    self.assertEqual(_pick(tooltip, shown, local=True), _pick(player, shown, local=True))
            # the player's branch is the window's tooltip, on the window's Country
            self.assertIn(player, tooltip)
            self.assertNotIn("GetPlayer", tooltip)
            # SelectLocalization nests in its third argument only
            for m in re.finditer(r"SelectLocalization\(", tooltip):
                args = _split_args(tooltip[m.end():_close_paren(tooltip, m.end() - 1)])
                self.assertEqual(len(args), 3)
                self.assertNotIn("SelectLocalization", args[1])

    def test_the_new_keys_exist(self):
        from gui_test_helpers import load_loc
        loc = load_loc()
        for key in (gen.NI_OTHER_TT, gen.NI_NOT_RUNNING_TT, gen.NI_POPS_LABEL, gen.NI_POPS_TOOLTIP):
            with self.subTest(key=key):
                self.assertIn(key, loc)
        for key in (gen.NI_OTHER_TT, gen.NI_NOT_RUNNING_TT):
            self.assertIn("[Country.GetName]", loc[key])
            self.assertNotRegex(loc[key], r"\b(you|your|we|our)\b")


def _close_paren(text, open_paren):
    depth = 0
    for i in range(open_paren, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed call")


class MountTest(unittest.TestCase):
    """Each public tab: one flowcontainer, up while its tab is shown, holding
    the player's mount (the window's full-screen mount) and another country's
    (the header, the readout, the wide composer), each on its own visible."""

    @classmethod
    def setUpClass(cls):
        cls.text = _strip_comments(_read(GENERATED))
        cls.column = _type_body(cls.text, "te_ni_tabs")
        cls.types = mod_types()

    def _mounts(self, column, tab):
        m = re.search(rf'name = "te_ni_{tab.key}_tab"', column)
        self.assertTrue(m, tab.key)
        start = column.rindex("flowcontainer = {", 0, m.start())
        block = _block_at(column, start)
        kids = _children(block[block.index("{") + 1:block.rindex("}")])
        props = {name: value for kind, name, value in kids if kind == "property"}
        self.assertEqual(props.get("using"), f"te_ni_{tab.key}_selected")
        self.assertNotIn("visible", props)
        mounts = [text for kind, name, text in kids if kind == "widget"]
        self.assertEqual(len(mounts), 2)
        return mounts

    def test_every_public_tab_has_two_mounts(self):
        self.assertEqual(len(re.findall(r'name = "te_ni_\w+_tab"', self.column)), len(gen.ni_tabs()))
        with mock.patch.object(gen, "TABS", _every_candidate_public()):
            every = (_type_body(_strip_comments(gen.render_ni()), "te_ni_tabs"), gen.ni_tabs())
        for column, tabs in ((self.column, gen.ni_tabs()), every):
            for t in tabs:
                with self.subTest(tab=t.key):
                    own, other = self._mounts(column, t)
                    own_props = dict((n, v) for k, n, v in _children(own) if k == "property")
                    self.assertEqual(own_props["visible"], f'"[{LOCAL}]"')
                    self.assertEqual(own_props["name"], f'"te_ni_{t.key}_own"')
                    self.assertEqual([n for k, n, _ in _children(own) if k == "widget"],
                                     [gen._content(t, wide=True)[0].split(" = ")[0], *t.footer])
                    other_props = dict((n, v) for k, n, v in _children(other) if k == "property")
                    self.assertEqual(other_props["visible"], f'"[Not( {LOCAL} )]"')
                    self.assertEqual(other_props["name"], f'"te_ni_{t.key}_other"')

    def _other(self, column, tab):
        return self._mounts(column, tab)[1]

    def test_another_countrys_mount(self):
        with mock.patch.object(gen, "TABS", _every_candidate_public()):
            tabs = gen.ni_tabs()
            column = _type_body(_strip_comments(gen.render_ni()), "te_ni_tabs")
        popups = _read(POPUPS)
        for t in tabs:
            with self.subTest(tab=t.key):
                other = self._other(column, t)
                kids = [(kind, name) for kind, name, _ in _children(other) if kind == "widget"]
                want = [("widget", "default_header")]
                want += [("widget", "flowcontainer")] * 2 if t.readout else [("widget", t.wide)]
                self.assertEqual(kids, want)
                header = _children(other)[[n for _, n, _ in _children(other)].index("default_header")][2]
                label = (f"SelectLocalization( {gen.shown(t.readout.sgui, gen.COUNTRY_ROOT)}, "
                         f"'{t.readout.label}', '{t.label}' )" if t.readout and t.readout.label else None)
                self.assertIn(f'text = "[{label}]"' if label else f'text = "{t.label}"', header)
                self.assertIn(f"GetVariableSystem.Set('te_popup', 'help_{t.key}')", header)
                self.assertIn(f"te_{t.key}_help_popup = {{}}", popups, "the \"?\" opens a page that exists")
                # te_popups is down for an observer, so the "?" is too
                self.assertIn(f'visible = "[{gen.NOT_OBSERVER}]"', header)
                self.assertIn("Not( GetMetaPlayer.IsObserver )",
                              re.search(r'name = "te_popups".*?visible = "([^"]*)"', popups, re.S).group(1))
                if t.readout:
                    # as the frame: the readout under its gate (tab_before_gate), the
                    # rest under the entry's (tab_gate), never both
                    box, rest = [text for kind, name, text in _children(other) if name == "flowcontainer"]
                    self.assertIn(f'visible = "[{gen.shown(t.readout.sgui, gen.COUNTRY_ROOT)}]"', box)
                    self.assertEqual([n for k, n, _ in _children(box) if k == "widget"], [t.readout.panel])
                    self.assertIn(f'visible = "[{gen.shown(t.readout.entry, gen.COUNTRY_ROOT)}]"', rest)
                    self.assertEqual([n for k, n, _ in _children(rest) if k == "widget"], [t.wide])
                for name in t.footer:
                    self.assertNotIn(name, other, "the footer's controls are the player's")
                # no entry, no player, no frame: another country has no journal entry
                for read in ("GetPlayerJournalEntry", "JournalEntry", "GetPlayer", "AccessPlayer"):
                    self.assertNotIn(read, other)
                for name in re.findall(r"(?<![\w.])(\w+) = \{", other):
                    td = self.types.get(name)
                    self.assertFalse(td is not None and td.base == "te_system_tab_frame",
                                     f"{name} is a frame, whose tab_country is the player")

    def test_the_players_mount_is_the_windows(self):
        """The player's own country gets the Timeline Extended window's
        full-screen mount: the body with its layout override, so its gate, its
        entry and its controls (owner call 3)."""
        window = _read(os.path.join(REPO, "gui", "te_systems_window_generated.gui"))
        for t in gen.ni_tabs():
            with self.subTest(tab=t.key):
                own = self._mounts(self.column, t)[0]
                content = "\n".join(gen._content(t, wide=True))
                self.assertIn(content.replace("\n", "\n\t\t\t\t"), _read(GENERATED))
                wide = re.search(rf'name = "te_systems_window_{t.key}_tab_wide"', window)
                self.assertTrue(wide)
                self.assertIn(content.replace("\n", "\n\t\t\t"), window[wide.start():])
                self.assertIn(content.split("\n")[0], own)

    def test_the_players_mount_keeps_the_entry(self):
        """Every tab National Info is to show, public or not: the player's
        mount holds the body, whose frame sets the entry's datacontext
        (tab_entry) on the widget around tab_content, where the layout block
        the mount overrides sits, so the wide composer reads JournalEntry as
        the window's does (a Colonial Empire row is a GetScriptedProgressBars
        item). A tab with no layout block mounts its composer bare, so its
        body must read no entry."""
        types = mod_types()
        frame = _strip_comments(types["te_system_tab_frame"].body)
        entry = frame.index('block "tab_entry"')
        holder = frame.rindex("flowcontainer = {", 0, entry)
        self.assertIn('block "tab_content"', frame[holder:_close(frame, frame.index("{", holder))])
        for t in gen.TABS:
            if t.key not in gen.NI_ORDER or t.wide is None:
                continue
            with self.subTest(tab=t.key):
                body = _strip_comments(types[t.body].body)
                own = gen._content(t, wide=True)
                if t.layout is None:
                    self.assertNotIn("JournalEntry", body)
                    continue
                self.assertEqual(own[0], f"{t.body} = {{")
                m = re.search(r'blockoverride "tab_entry" \{\s*datacontext = "\[GetPlayerJournalEntry', body)
                if m:
                    content = re.search(r'blockoverride "tab_content" \{', body)
                    self.assertTrue(content, t.body)
                    self.assertIn(f'block "{t.layout}"', body[content.end():_close(body, content.end() - 1)])

    def test_the_players_mount_draws_the_windows_footer(self):
        """What the window draws below a tab, in its frames' fixed_bottom
        (te_systems_window_<key>_footer), the player's mount draws below the
        body: Tax Code's draft and bill summaries, with Introduce, Discard and
        Review (owner call 3: the same view, with its controls)."""
        window = _strip_comments(_read(os.path.join(REPO, "gui", "te_systems_window.gui")))
        footers = {}
        for name in re.findall(r"\btype (te_systems_window_\w+_footer) = ", window):
            body = _type_body(window, name)
            # whose: the tab its selected template names
            footers[re.search(r"using = te_systems_window_(\w+)_selected", body).group(1)] = body
        self.assertIn("tax_code", footers)
        tabs = {t.key: t for t in gen.TABS}
        for key, body in footers.items():
            with self.subTest(tab=key):
                drawn = [n for n in re.findall(r"(?<![\w.])(\w+) = \{\}", body)
                         if n not in ("divider_clean", "background")]
                self.assertEqual(list(tabs[key].footer), drawn)
        for t in gen.TABS:
            if t.footer:
                self.assertIn(t.key, footers, f"{t.key}: a footer the window doesn't draw")
        with mock.patch.object(gen, "TABS", _every_candidate_public()):
            column = _type_body(_strip_comments(gen.render_ni()), "te_ni_tabs")
            own = self._mounts(column, next(t for t in gen.ni_tabs() if t.key == "tax_code"))[0]
        widgets = [n for k, n, _ in _children(own) if k == "widget"]
        self.assertEqual(widgets, ["te_tax_tab_body", "te_tax_draft_summary", "te_tax_bill_summary"])

    def test_one_visible_per_widget(self):
        stack = [0]
        for line in self.text.splitlines():
            s = line.strip()
            if s.startswith("visible =") or (s.startswith("using = te_ni_") and "selected" in s):
                stack[-1] += 1
                self.assertLessEqual(stack[-1], 1, f"two visibles near {s[:70]}")
            stack.extend([0] * line.count("{"))
            for _ in range(line.count("}")):
                if len(stack) > 1:
                    stack.pop()


class ForeignViewerTest(unittest.TestCase):
    """Another country's chart viewers (te_ni_chart_<id>_popup, which the
    window holds at its own level, under its Country): for a public tab's
    charts, the viewer reads no entry and no player. BindingTest walks the
    panel's small wrappers; this walks the large ones the viewer draws, and
    the key under them."""

    def test_a_public_tabs_viewers_read_the_window_country(self):
        from scripts.generators import gen_te_history_charts as charts
        types = mod_types()
        public = {t.key for t in gen.ni_tabs()}
        shown = [c for c in charts.CHARTS if c.system in public]
        self.assertEqual({c.system for c in shown}, public & {c.system for c in charts.CHARTS})
        self.assertTrue(shown, "Demographics' eight at least")
        for chart in shown:
            with self.subTest(chart=chart.id):
                found = [f for f in markup_reads({charts.ni_popup_name(chart)}, types) if not f.world]
                self.assertEqual(found, [], "\n".join(map(str, found[:10])))


def _override(body, name):
    m = re.search(rf'blockoverride "{name}" \{{', body)
    return body[m.end():_close(body, m.end() - 1)] if m else ""


def _tab_gate(body):
    """The frame's tab_gate expression, as the body's override writes it."""
    m = re.search(r'visible = "\[(.*)\]"', _override(body, "tab_gate"))
    return m.group(1) if m else None


class ReadoutTest(unittest.TestCase):
    """Tab.readout names what the body's frame shows without the entry, in its
    tab_before_gate, under that scripted GUI; National Info's foreign mount
    draws it (it draws no frame), and the binding tests walk it."""

    def test_each_readout_is_its_bodys(self):
        """Each field of a Readout is what the body's frame has: the panel under
        the readout's gate in tab_before_gate, the entry's gate in tab_gate,
        and the header the frame swaps in under the readout's gate."""
        types = mod_types()
        named = [t for t in gen.TABS if t.readout]
        self.assertEqual({t.key for t in named}, {"banking", "colonial_empire"})
        for t in named:
            r = t.readout
            with self.subTest(tab=t.key):
                body = _strip_comments(types[t.body].body)
                before = _override(body, "tab_before_gate")
                self.assertIn(f'visible = "[{gen.shown(r.sgui)}]"', before)
                self.assertRegex(before, rf"(?<![\w.]){r.panel} = \{{")
                self.assertIn(r.panel, gen.ni_types(t))
                self.assertIn(gen.shown(r.sgui), t.open_, "the readout opens the tab")
                self.assertEqual(_tab_gate(body), gen.shown(r.entry), "the entry's gate is the frame's tab_gate")
                self.assertEqual(t.open_, gen.or_(gen.shown(r.entry), gen.shown(r.sgui)), "open: one or the other")
                headers = {}
                for m in re.finditer(r"\bdefault_header = \{", _override(body, "tab_header")):
                    h = _block_at(_override(body, "tab_header"), m.start())
                    gate = re.search(r'^\t*visible = "\[(.*)\]"', h, re.M)
                    headers[gate.group(1) if gate else None] = re.search(r'text = "(\w+)"', h).group(1)
                self.assertEqual(r.label, headers.get(gen.shown(r.sgui)), "the header over the readout")

    def test_without_a_readout_the_open_gate_is_the_frames(self):
        """A tab with no readout opens only while its frame's tab_gate is
        true (the gate itself, or one term of an And), so its foreign mount
        can draw the composer under the tab's own selected template."""
        types = mod_types()
        for t in gen.TABS:
            if t.key not in gen.NI_ORDER or t.readout or t.body not in types:
                continue
            with self.subTest(tab=t.key):
                gate = _tab_gate(_strip_comments(types[t.body].body))
                if gate is None:
                    continue
                terms = _split_args(t.open_[len("And("):t.open_.rindex(")")]) if t.open_.startswith("And(") else [t.open_]
                self.assertIn(gate, [x.strip() for x in terms])

    def test_a_tab_with_a_tab_before_gate_names_its_readout(self):
        types = mod_types()
        for t in gen.TABS:
            td = types.get(t.body)
            if td is None or not re.search(r'blockoverride "tab_before_gate" \{\s*\S', _strip_comments(td.body)):
                continue
            with self.subTest(tab=t.key):
                if t.key == "strategic_reserve":
                    continue   # its tab_before_gate is the other-market note, which needs the entry's market
                self.assertIsNotNone(t.readout, f"{t.key}: its frame draws something before the gate")


class ForeignOpenTest(unittest.TestCase):
    """Tab.ni_open (Nuclear's: te_ni_nuclear_tab_sgui). Before the world's
    first warhead only a country with a programme holds je_nuclear_program,
    so another country's tab opens on the taboo's birth instead of the entry:
    an open or grayed tab tells nothing then. The player's own opens on the
    tab's gate as before, in National Info and in the window."""

    def test_nuclear_opens_for_another_country_on_the_taboo(self):
        tab = {t.key: t for t in gen.TABS}["nuclear_weapons"]
        self.assertEqual(tab.ni_open, "te_ni_nuclear_tab_sgui")
        body = _is_shown(tab.ni_open)
        # the tab's own gate, and the taboo born (or, in a save from before it, a country believed armed or in crisis)
        conds = _flat(body)
        for item in _is_shown("te_military_nuclear_tab_sgui"):
            self.assertIn(_norm(item), conds)
        ors = [v for k, _, v in body if k == "OR"]
        self.assertEqual(len(ors), 1)
        self.assertEqual(sorted(_norm(x) for x in ors[0]),
                         ["has_global_variable = nd_taboo", "nd_believed_armed = yes", "nd_in_crisis = yes"])

    def test_the_gates_it_changes(self):
        tab = {t.key: t for t in gen.TABS}["nuclear_weapons"]
        text = _read(GENERATED)
        sel = _template(text, "te_ni_nuclear_weapons_selected")
        unsel = _template(text, "te_ni_nuclear_weapons_unselected")
        tooltip = re.fullmatch(r'tooltip = "\[(.*)\]"', gen.ni_tooltip(tab)).group(1)
        entry_only = {"te_military_nuclear_tab_sgui", "te_military_nuclear_tab_unlock_sgui"}   # a programme, no taboo
        with_taboo = entry_only | {"te_ni_nuclear_tab_sgui"}
        for local, shown, want in ((True, entry_only, True), (False, entry_only, False), (False, with_taboo, True),
                                   (True, with_taboo, True), (True, {"te_military_nuclear_tab_unlock_sgui"}, False)):
            with self.subTest(local=local, shown=sorted(shown)):
                self.assertEqual(_evaluate(sel, shown, "nuclear_weapons", local), want)
                self.assertEqual(_evaluate(unsel, shown, "nuclear_weapons", local), not want)
                self.assertEqual(_evaluate(gen.ni_open_gate(tab), shown, None, local), want, "the button's enabled")
                if not local:
                    self.assertEqual(_pick(tooltip, shown, local),
                                     gen.NI_OTHER_TT if want else gen.NI_NOT_RUNNING_TT)
        self.assertIn(f'enabled = "[{gen.ni_open_gate(tab)}]"', text)
        # the window and the player's mount keep the tab's own gate
        window = _read(os.path.join(REPO, "gui", "te_systems_window_generated.gui"))
        self.assertNotIn("te_ni_nuclear_tab_sgui", window)
        # National Info reads it in its selection templates (top-level visibles), the button's enabled and its
        # tooltip only: never in a mount
        lines = [ln for ln in text.split("\n") if "te_ni_nuclear_tab_sgui" in ln]
        self.assertEqual(sorted({ln.split(" =")[0].strip() for ln in lines}), ["enabled", "tooltip", "visible"])
        self.assertTrue(all(ln.startswith("\tvisible = ") for ln in lines if "visible =" in ln))

    def test_a_tab_without_it_keeps_its_gate(self):
        for t in gen.TABS:
            if t.ni_open is None and t.open_ is not None:
                self.assertEqual(gen.ni_open_gate(t), gen.rooted(t.open_, gen.COUNTRY_ROOT), t.key)


class GeneratorTest(unittest.TestCase):
    def test_generated_file_is_current(self):
        with open(GENERATED, "rb") as f:
            committed = f.read()
        self.assertTrue(committed.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(committed[3:].startswith(b"\xef\xbb\xbf"))
        self.assertEqual(committed.decode("utf-8-sig"), gen.render_ni(),
                         "stale: run python3 scripts/generators/gen_te_systems_window.py")
        self.assertEqual(gen.main(["--check"]), 0)

    def test_a_public_tab_needs_a_place(self):
        extra = replace(gen.TABS[1], key="elsewhere", public=True)
        with mock.patch.object(gen, "TABS", gen.TABS + [extra]):
            with self.assertRaisesRegex(ValueError, "elsewhere"):
                gen.render_ni()

    def test_the_order(self):
        self.assertEqual(gen.NI_ORDER[0], "pops")
        self.assertEqual(gen.NI_STORED, "te_ni_tab")
        self.assertEqual(set(gen.NI_ORDER[1:]) - {t.key for t in gen.TABS}, set())


if __name__ == "__main__":
    unittest.main()
