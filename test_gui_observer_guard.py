"""An observer has no GetPlayer: the system tabs on vanilla panels test for one.

A scripted GUI rooted on ``GuiScope.SetRoot( GetPlayer.MakeScope )`` logs
``untyped trigger [ Scoped object of type 'country' is not valid ]`` every frame
it is evaluated in observer mode, because the engine checks the root against
the GUI's ``scope = country`` before its block runs. An observer session on
2026-10-25 logged 10,000 such lines in nine minutes. The cure is
``Not( GetMetaPlayer.IsObserver )`` first in an ``And``, so the gate is never
read (``docs/guides/gui_modding_guide.md``, the gotcha starting "An observer
has no `GetPlayer`").

The vanilla panels that host the mod's system tabs are drawn for an observer,
so:

* every tab button's ``*_button_visibility`` / ``*_button_visibility_checked``
  that reads ``GetPlayer`` puts the observer test first;
* every other ``visible`` there that reads ``GetPlayer.MakeScope`` is guarded
  itself or sits inside one of those tabs (selected first in its own ``And``
  or an ancestor's), which an observer can't select because its button is
  hidden;
* a GUI file outside the hosts with such a tab button is in ROOT_GATED, its
  window's root hidden for an observer.
"""

import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(HERE, "gui")

# host file -> tab buttons whose visibility reads GetPlayer (two halves a tab).
HOSTS = {
    "budget_panel.gui": 4,         # Banking, Tax Code
    "culture_panel.gui": 2,        # Cultural Hegemony
    "panel_military.gui": 4,       # Nuclear, Covert
    "diplomatic_overview.gui": 2,  # UN
    "pops_overview.gui": 2,        # Demographics
    "market_panel.gui": 4,         # Climate, Reserve
}

# Other GUI files with a tab button reading GetPlayer: the file's root widget
# (by name), whose visible must test the observer itself.
ROOT_GATED = {
    "te_systems_window.gui": "te_systems_window",
}

OBSERVER = "Not( GetMetaPlayer.IsObserver )"
VISIBILITY = re.compile(r"\w+_button_visibility(?:_checked)?$")
TAB = re.compile(r"InformationPanel\.IsTabSelected\('(\w+)'\)$")


def _read(name):
    with open(os.path.join(GUI, name), encoding="utf-8-sig") as fh:
        return fh.read()


def _visibles(text):
    """Every ``visible = "..."``, with its block and its ancestors' visibles.

    Returns ``(line, value, header, ancestors)``: ``header`` is the enclosing
    block's ``blockoverride`` name (None for any other block), ``ancestors``
    the visibles of the enclosing blocks, outermost first.
    Comments are skipped; braces and ``#`` inside strings are not structure.
    """
    out = []
    # One frame a block: [header, visibles set directly in it].
    stack = [[None, []]]
    i, n, line = 0, len(text), 1
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
        elif c == "#":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        elif c == '"':
            j = i + 1
            while text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            value = text[i + 1:j]
            before = text[max(0, i - 64):i]
            if re.search(r"\bvisible\s*=\s*$", before):
                ancestors = [v for frame in stack[:-1] for v in frame[1]]
                out.append((line, value, stack[-1][0], ancestors))
                stack[-1][1].append(value)
            line += value.count("\n")
            i = j + 1
            continue
        elif c == "{":
            m = re.search(r'blockoverride\s+"(\w+)"\s*$', text[max(0, i - 128):i])
            stack.append([m.group(1) if m else None, []])
        elif c == "}":
            stack.pop()
            if not stack:
                raise ValueError(f"unbalanced '}}' at line {line}")
        i += 1
    if len(stack) != 1:
        raise ValueError("unbalanced '{'")
    return out


def _terms(expr):
    """The leading conjuncts of a visible: ``And( a, b )`` -> a's, then a."""
    expr = expr.strip()
    if expr.startswith("[") and expr.endswith("]"):
        expr = expr[1:-1].strip()
    terms = []
    while expr.startswith("And("):
        depth, k = 0, 0
        for k, ch in enumerate(expr):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 1:
                break
        first = expr[len("And("):k].strip()
        terms.append(first)
        expr = first
    return terms or [expr]


def _guards(expr, tabs):
    """Whether this visible keeps an observer from reading what it gates."""
    for term in _terms(expr):
        if term == OBSERVER:
            return True
        m = TAB.match(term)
        if m and m.group(1) in tabs:
            return True
    return False


def _root_visible(text, widget):
    m = re.search(r'name\s*=\s*"%s"' % re.escape(widget), text)
    if not m:
        return None
    rest = text[m.end():]
    v = re.search(r'\bvisible\s*=\s*"([^"]*)"', rest)
    return v.group(1) if v else None


class SystemTabButtonsTestTheObserverFirst(unittest.TestCase):
    def test_every_tab_button_visibility_reading_getplayer_is_guarded(self):
        for name, expected in HOSTS.items():
            with self.subTest(host=name):
                buttons = [(line, value) for line, value, header, _ in _visibles(_read(name))
                           if header and VISIBILITY.match(header) and "GetPlayer" in value]
                self.assertEqual(len(buttons), expected,
                                 f"{name}: {len(buttons)} tab-button visibilities read GetPlayer, "
                                 f"expected {expected}; update HOSTS if a tab was added or removed")
                for line, value in buttons:
                    self.assertTrue(value.startswith(f"[And( {OBSERVER}, "),
                                    f"gui/{name}:{line}: a tab button's visibility reads GetPlayer "
                                    f"without {OBSERVER} first in an And: {value[:120]}")

    def test_other_getplayer_gates_draw_only_in_a_guarded_tab(self):
        for name in HOSTS:
            with self.subTest(host=name):
                found = _visibles(_read(name))
                tabs = set()
                for _, value, header, _ in found:
                    if header and VISIBILITY.match(header) and value.startswith(f"[And( {OBSERVER}, "):
                        tabs.update(re.findall(r"IsTabSelected\('(\w+)'\)", value))
                self.assertTrue(tabs, f"{name}: no observer-guarded tab found")
                for line, value, header, ancestors in found:
                    if "GetPlayer.MakeScope" not in value:
                        continue
                    if header and VISIBILITY.match(header):
                        continue  # the test above
                    self.assertTrue(
                        any(_guards(v, tabs) for v in [value, *ancestors]),
                        f"gui/{name}:{line}: a visible reads GetPlayer.MakeScope outside any "
                        f"observer-guarded tab, and has no {OBSERVER} first: {value[:120]}")

    def test_tab_strips_outside_the_hosts_are_observer_gated_at_the_root(self):
        for dirpath, _, files in os.walk(GUI):
            for fname in files:
                if not fname.endswith(".gui"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, fname), GUI).replace(os.sep, "/")
                if rel in HOSTS:
                    continue
                text = _read(rel)
                if not any(header and VISIBILITY.match(header) and "GetPlayer.MakeScope" in value
                           for _, value, header, _ in _visibles(text)):
                    continue
                with self.subTest(file=rel):
                    self.assertIn(rel, ROOT_GATED,
                                  f"gui/{rel} has a tab button whose visibility reads "
                                  f"GetPlayer.MakeScope: guard it as HOSTS are, or gate the "
                                  f"window's root and list it in ROOT_GATED")
                    root = _root_visible(text, ROOT_GATED[rel])
                    self.assertIsNotNone(root, f"gui/{rel}: no root widget {ROOT_GATED[rel]!r}")
                    self.assertIn(OBSERVER, root)


class TheWalker(unittest.TestCase):
    def test_terms_and_guards(self):
        self.assertEqual(_terms("[And( And( A, B ), C )]"), ["And( A, B )", "A"])
        self.assertEqual(_terms("[X]"), ["X"])
        self.assertTrue(_guards(f"[And( {OBSERVER}, And( InformationPanel.IsTabSelected('te_y'), Y ) )]", set()))
        self.assertTrue(_guards("[InformationPanel.IsTabSelected('te_x')]", {"te_x"}))
        self.assertTrue(_guards("[And( InformationPanel.IsTabSelected('te_x'), Z )]", {"te_x"}))
        self.assertFalse(_guards("[And( InformationPanel.IsTabSelected('world_market_trade'), Z )]", {"te_x"}))
        self.assertFalse(_guards("[And( Z, Not( GetMetaPlayer.IsObserver ) )]", {"te_x"}))

    def test_an_unguarded_tab_button_is_caught(self):
        text = ('tab_buttons = {\n'
                '\tblockoverride "fifth_button_visibility"\n\t{\n'
                '\t\tvisible = "[And( InformationPanel.IsTabSelected(\'te_x\'), '
                'GetScriptedGui(\'g\').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End ) )]" # a } in a comment\n'
                '\t}\n}\n'
                'widget = {\n\tvisible = "[InformationPanel.IsTabSelected(\'te_x\')]"\n'
                '\twidget = { visible = "[GetScriptedGui(\'g\').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )]" }\n}\n')
        found = _visibles(text)
        self.assertEqual([(line, header) for line, _, header, _ in found],
                         [(4, "fifth_button_visibility"), (8, None), (9, None)])
        self.assertFalse(found[0][1].startswith(f"[And( {OBSERVER}, "))
        self.assertEqual(found[2][3], ["[InformationPanel.IsTabSelected('te_x')]"])


if __name__ == "__main__":
    unittest.main()
