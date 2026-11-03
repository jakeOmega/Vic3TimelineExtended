"""The HUD under the Timeline Extended window's Full Screen
(gui/00_te_fullscreen_hide.gui).

Vanilla hides parts of the HUD while one of its full-screen panels is open:
the outliner, the wars list, the lens toolbar and the notifications next to
the outliner (half_and_fullscreen_hide), the "Paused" frame, the
construction box and the backgrounds of the time controls and the top bar
(fullscreen_hide), and it swaps in the compact notifications
(half_and_fullscreen_show). The three templates are in vanilla's
gui/block_windows.gui:984-1000, each an Or chain of
InformationPanelBar.IsPanelOpen, which a scripted widget never trips. The mod
redefines them in a file whose name sorts before block_windows.gui: the
engine keeps the first registration of a template's name, in file-name order,
and logs the later one as `Template 'X' already registered at '<file>'` in
gui.log (gotcha #30 in docs/guides/gui_modding_guide.md).

These tests hold each template to vanilla's (the committed fixture, which
test_te_fullscreen_frame.py holds to the installed game) plus two terms: the
Timeline Extended window's Full Screen, written as the window root's
visibility AND the full-screen frame's, so the HUD hides exactly while the
frame draws and comes back by every route that closes it; and the Community
Mod Framework's own full-screen key, inert without it. They parse each
expression (balanced, And and Or with two arguments, Not with one) and
evaluate it in each state the window can be in.
"""
import itertools
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
from gui_test_helpers import _block_at, _read, _strip_comments  # noqa: E402

OURS = os.path.join(REPO, "gui", "00_te_fullscreen_hide.gui")
VANILLA = os.path.join(REPO, "test_fixtures", "vanilla_gui", "block_windows.gui")
WINDOW = os.path.join(REPO, "gui", "te_systems_window.gui")
GUI_DIR = os.path.join(REPO, "gui")

TEMPLATES = ("fullscreen_hide", "half_and_fullscreen_show", "half_and_fullscreen_hide")
CMF_TERM = "GetVariableSystem.Exists('com_fullscreen')"


# --- a small parser for the engine's binding expressions --------------------

_TOKEN = re.compile(r"\s*(?:([A-Za-z_]\w*)|('[^']*')|([().,]))")


def _tokens(expr):
    out, pos = [], 0
    expr = expr.rstrip()
    while pos < len(expr):
        m = _TOKEN.match(expr, pos)
        if not m or m.end() == pos:
            raise AssertionError(f"can't read {expr[pos:pos + 30]!r}")
        out.append(m.group(1) or m.group(2) or m.group(3))
        pos = m.end()
    return out


def parse(expr):
    """`[...]` -> a tree: ("And"|"Or"|"Not", [args]) for the logic, ("leaf",
    text) for anything else (its text without spaces). Raises on unbalanced
    parentheses and on And or Or without exactly two arguments or Not without
    exactly one."""
    expr = expr.strip()
    assert expr.startswith("[") and expr.endswith("]"), expr[:40]
    toks = _tokens(expr[1:-1])
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def take(want=None):
        nonlocal pos
        tok = peek()
        assert tok is not None, "ran out of tokens: unbalanced"
        assert want is None or tok == want, f"expected {want!r}, got {tok!r} at token {pos}"
        pos += 1
        return tok

    def node():
        parts, calls = [], []
        while True:
            tok = take()
            assert tok not in "().,", f"unexpected {tok!r} at token {pos - 1}"
            args = None
            if peek() == "(":
                take("(")
                args = []
                if peek() != ")":
                    args.append(node())
                    while peek() == ",":
                        take(",")
                        args.append(node())
                take(")")
            parts.append(tok)
            calls.append(args)
            if peek() != ".":
                break
            take(".")
        if len(parts) == 1 and parts[0] in ("And", "Or", "Not"):
            want = 1 if parts[0] == "Not" else 2
            assert len(calls[0]) == want, f"{parts[0]} takes {want} arguments, got {len(calls[0])}"
            return (parts[0], calls[0])
        text = ".".join(p if a is None else f"{p}({','.join(_text(x) for x in a)})" for p, a in zip(parts, calls))
        return ("leaf", text)

    tree = node()
    assert pos == len(toks), f"trailing tokens: {toks[pos:]}"
    return tree


def _text(tree):
    kind, body = tree
    return body if kind == "leaf" else f"{kind}({','.join(_text(a) for a in body)})"


def flat_or(tree):
    """The terms of an Or chain, nested any way."""
    if tree[0] == "Or":
        return [t for arg in tree[1] for t in flat_or(arg)]
    return [tree]


def evaluate(tree, world):
    kind, body = tree
    if kind == "And":
        return evaluate(body[0], world) and evaluate(body[1], world)
    if kind == "Or":
        return evaluate(body[0], world) or evaluate(body[1], world)
    if kind == "Not":
        return not evaluate(body[0], world)
    m = re.fullmatch(r"InformationPanelBar\.IsPanelOpen\('(\w+)'\)", body)
    if m:
        return m.group(1) in world["panels"]
    m = re.fullmatch(r"GetVariableSystem\.Exists\('(\w+)'\)", body)
    if m:
        return m.group(1) in world["vars"]
    m = re.fullmatch(r"GetVariableSystem\.HasValue\('(\w+)','(\w+)'\)", body)
    if m:
        return world["vars"].get(m.group(1)) == m.group(2)
    if body == "GetMetaPlayer.GetPlayedOrObservedCountry.IsValid":
        return world["played"]
    if body == "GetMetaPlayer.IsObserver":
        return world["observer"]
    raise AssertionError(f"no value for {body}")


def world(panels=(), played=True, observer=False, **variables):
    return {"panels": set(panels), "played": played, "observer": observer, "vars": dict(variables)}


# --- reading the files -------------------------------------------------------

def templates(path):
    """{name: the visible expression} for each top-level template whose only
    property is visible."""
    text = _strip_comments(_read(path))
    out = {}
    for m in re.finditer(r"^template (\w+) \{", text, re.M):
        body = _block_at(text, m.start())
        vis = re.fullmatch(r'template \w+ \{\s*visible = "([^"]*)"\s*\}', body)
        if vis:
            out[m.group(1)] = vis.group(1)
    return out


def _visible(block):
    m = re.search(r'^\t+visible = "([^"]*)"$', block, re.M)
    assert m, block[:80]
    return m.group(1)


def te_full_screen_term():
    """The window root's visible AND the full-screen frame's: when the frame
    draws."""
    gui = _strip_comments(_read(WINDOW))
    root = re.search(r'^widget = \{\n\tname = "te_systems_window"$', gui, re.M)
    assert root, "no te_systems_window root"
    root_vis = _visible(_block_at(gui, root.start()).split("\n\n")[0])
    frame = re.search(r"^\tte_systems_window_panel_wide = \{$", gui, re.M)
    assert frame, "no te_systems_window_panel_wide instance"
    frame_vis = _visible(_block_at(gui, frame.start()))
    return ("And", [parse(root_vis), parse(frame_vis)])


class FileTest(unittest.TestCase):
    def test_one_bom(self):
        with open(OURS, "rb") as f:
            head = f.read(6)
        self.assertTrue(head.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(head.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"))

    def test_it_loads_before_vanillas_file(self):
        # The first registration of a template's name wins (gotcha #30).
        name = os.path.basename(OURS)
        self.assertLess(name, "block_windows.gui")
        self.assertTrue(name.startswith("00_"))

    def test_it_holds_the_three_and_nothing_else(self):
        text = _strip_comments(_read(OURS))
        self.assertEqual(sorted(re.findall(r"^template (\w+) \{", text, re.M)), sorted(TEMPLATES))
        self.assertNotRegex(text, r"(?m)^(types|type|widget|layer)\b")

    def test_no_other_mod_file_defines_them(self):
        for dirpath, _, names in os.walk(GUI_DIR):
            for fname in names:
                path = os.path.join(dirpath, fname)
                if not fname.endswith(".gui") or path == OURS:
                    continue
                text = _strip_comments(_read(path))
                for name in TEMPLATES:
                    with self.subTest(file=fname, template=name):
                        self.assertNotRegex(text, rf"(?m)^\s*template\s+{name}\b")


class TemplateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vanilla = {k: parse(v) for k, v in templates(VANILLA).items()}
        cls.ours = {k: parse(v) for k, v in templates(OURS).items()}
        cls.te = te_full_screen_term()

    def test_vanilla_still_has_the_three(self):
        # A vanilla patch that renames one, or adds a fourth that reads the
        # panel bar, needs this file changed too.
        reading = {k for k, v in templates(VANILLA).items() if "InformationPanelBar.IsPanelOpen" in v}
        self.assertEqual(reading, set(TEMPLATES))

    def test_each_is_vanillas_or_the_two_full_screens(self):
        for name in TEMPLATES:
            with self.subTest(template=name):
                van, ours = self.vanilla[name], self.ours[name]
                self.assertEqual(van[0], ours[0])                     # Not(...) or a bare Or
                if van[0] == "Not":
                    van, ours = van[1][0], ours[1][0]
                van_terms = {_text(t) for t in flat_or(van)}
                our_terms = [_text(t) for t in flat_or(ours)]
                self.assertEqual(len(our_terms), len(set(our_terms)), "a term twice")
                self.assertEqual(set(our_terms), van_terms | {CMF_TERM, _text(self.te)})

    def test_the_full_screen_term_is_when_the_frame_draws(self):
        # Root: the played country, not an observer, com_open_window; frame:
        # te_systems_window_wide. So it needs the window open, not just the
        # remembered width.
        text = _text(self.te)
        self.assertIn("GetVariableSystem.HasValue('com_open_window','te_systems_window')", text)
        self.assertIn("GetVariableSystem.Exists('te_systems_window_wide')", text)
        self.assertIn("GetMetaPlayer.GetPlayedOrObservedCountry.IsValid", text)

    def test_the_treaty_draft_distinction_is_vanillas(self):
        def panels(tree):
            return set(re.findall(r"IsPanelOpen\('(\w+)'\)", _text(tree)))
        self.assertNotIn("treaty_draft_panel", panels(self.ours["fullscreen_hide"]))
        self.assertIn("treaty_draft_panel", panels(self.ours["half_and_fullscreen_hide"]))
        self.assertIn("treaty_draft_panel", panels(self.ours["half_and_fullscreen_show"]))

    def _hud_hidden(self, w):
        """{template: whether its widgets behave as under a full screen}."""
        out = {}
        for name in TEMPLATES:
            shown = evaluate(self.ours[name], w)
            out[name] = shown if name.endswith("_show") else not shown
        return out

    def assert_full_screen(self, w, expect):
        self.assertEqual(self._hud_hidden(w), {name: expect for name in TEMPLATES})

    def test_full_screen_hides_the_hud(self):
        self.assert_full_screen(world(com_open_window="te_systems_window", te_systems_window_wide="yes"), True)

    def test_the_side_panel_keeps_it(self):
        self.assert_full_screen(world(com_open_window="te_systems_window"), False)

    def test_closing_brings_it_back_though_the_width_is_remembered(self):
        # Every close route clears com_open_window (Back, Close and Escape on
        # the frame, the launcher, a vanilla panel or the ledger opening);
        # te_systems_window_wide stays for the session.
        self.assert_full_screen(world(te_systems_window_wide="yes"), False)
        self.assert_full_screen(world(com_open_window="com_some_other_window", te_systems_window_wide="yes"), False)

    def test_not_for_an_observer_or_without_a_played_country(self):
        # The root is hidden there, so the HUD must not be.
        on = dict(com_open_window="te_systems_window", te_systems_window_wide="yes")
        self.assert_full_screen(world(observer=True, **on), False)
        self.assert_full_screen(world(played=False, **on), False)

    def test_cmf_full_screens_still_hide_it(self):
        self.assert_full_screen(world(com_fullscreen="yes"), True)

    def test_vanilla_panels_as_vanilla(self):
        names = sorted({p for t in self.vanilla.values() for p in re.findall(r"IsPanelOpen\('(\w+)'\)", _text(t))})
        for n in range(0, 3):
            for panels in itertools.combinations(names, n):
                for te in ({}, {"com_open_window": "te_systems_window"}, {"te_systems_window_wide": "yes"}):
                    w = world(panels, **te)
                    for name in TEMPLATES:
                        with self.subTest(panels=panels, te=te, template=name):
                            self.assertEqual(evaluate(self.ours[name], w), evaluate(self.vanilla[name], w))


class ParserTest(unittest.TestCase):
    """The parser rejects what the engine would misread."""

    def test_rejects(self):
        for bad in ("[Or(A.B, C.D, E.F)]", "[And(A.B)]", "[Not(A.B, C.D)]", "[Or(A.B, C.D]", "[Or(A.B, C.D))]"):
            with self.subTest(expr=bad), self.assertRaises(AssertionError):
                parse(bad)

    def test_reads_vanillas(self):
        for name, expr in templates(VANILLA).items():
            with self.subTest(template=name):
                parse(expr)


if __name__ == "__main__":
    unittest.main()
