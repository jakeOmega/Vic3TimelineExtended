"""A datamodel slice over a script list never asks for more than the list holds.

`DataModelLast( <list>, '(int32)N' )` on a list shorter than N logs "Trying to
reshape data model with negative offset -N" every frame for every widget that
does, and `DataModelSkipFirst` its sibling, "... negative count -N" (seen in
game 2026-11-24: 300 to 430 lines a second from the history charts in a game
of January 1836, 75 a second from one scratch widget; PR #2036).
`DataModelFirst` past a list's end is silent, so it is not held here.

A script list (`...GetList('<name>')`) can be any length, so each such slice in
a mod `.gui` file must sit in a widget, or under one, whose `visible` tests the
list's size: `GreaterThanOrEqualTo_int32( GetDataModelSize( <list> ), N )` or a
`GreaterThan_int32` of at least N - 1. A hidden widget's datamodel is not
evaluated (no line was ever logged for a hidden plot). The engine's own lists
(vanilla's copies in the mod's panels) are left to vanilla.
"""
import os
import re
import unittest

from gui_test_helpers import _strip_comments

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui")

SLICE = re.compile(r"\b(DataModelLast|DataModelSkipFirst|DataModelSubSpan)\(\s*"
                   r"((?:[^()']|'[^']*'|\((?:[^()']|'[^']*')*\))*?GetList\('\w+'\))\s*,\s*'\(int32\)(\d+)'")
VISIBLE = re.compile(r'\bvisible\s*=\s*"([^"]*)"')
GUARD = re.compile(r"\b(GreaterThanOrEqualTo_int32|GreaterThan_int32)\(\s*GetDataModelSize\(\s*(.*?)\s*\)\s*,\s*'\(int32\)(\d+)'\s*\)")


def _squash(text):
    return re.sub(r"\s+", "", text)


def _enclosing(text, pos):
    """The start (the index of its `{`) of each block open at pos, innermost
    last. Braces inside quoted strings are not blocks."""
    stack, quoted = [], False
    for i in range(pos):
        c = text[i]
        if c == '"':
            quoted = not quoted
        elif not quoted:
            if c == "{":
                stack.append(i)
            elif c == "}" and stack:
                stack.pop()
    return stack


def _own_visibles(text, start):
    """The `visible` expressions set directly in the block that opens at start."""
    out, depth, quoted, i, line = [], 0, False, start, start + 1
    while i < len(text):
        c = text[i]
        if c == '"':
            quoted = not quoted
        elif not quoted:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
        if c == "\n":
            if depth == 1:
                out += VISIBLE.findall(text[line:i])
            line = i + 1
        i += 1
    if depth == 1 or i >= len(text) or text[line:i].strip():
        out += VISIBLE.findall(text[line:i])
    return out


def _holds_enough(expr, wanted_list, n):
    """Whether a visible expression tests that the list holds at least n."""
    for op, tested, m in GUARD.findall(expr):
        if _squash(tested) != _squash(wanted_list):
            continue
        if (op == "GreaterThanOrEqualTo_int32" and int(m) >= n) or (op == "GreaterThan_int32" and int(m) >= n - 1):
            return True
    return False


def unguarded(text):
    """Every script-list slice in text with no size test on it or above it:
    (function, list, count) each."""
    text = _strip_comments(text)
    out = []
    for m in SLICE.finditer(text):
        fn, the_list, n = m.group(1), m.group(2), int(m.group(3))
        if fn == "DataModelSubSpan":
            out.append((fn, the_list, n))   # no rule yet: a sub-span needs from + count of the list
            continue
        visibles = [v for start in _enclosing(text, m.start()) for v in _own_visibles(text, start)]
        if not any(_holds_enough(v, the_list, n) for v in visibles):
            out.append((fn, the_list, n))
    return out


class SliceGuardTest(unittest.TestCase):
    LIST = "Country.MakeScope.GetList('te_hist')"

    def widget(self, visible, fn="DataModelLast", n=60, own=True):
        gate = f'visible = "[{visible}]"' if visible else ""
        inner = f"flowcontainer = {{\n\t\t{gate if own else ''}\n\t\tblockoverride \"rows\" {{\n\t\t\t" \
                f"datamodel = \"[{fn}( {self.LIST}, '(int32){n}' )]\"\n\t\t}}\n\t}}"
        return f"widget = {{\n\t{'' if own else gate}\n\ttooltip = \"a {{ brace }} in a string\"\n\t{inner}\n}}\n"

    def size(self, op, m):
        return f"{op}( GetDataModelSize( {self.LIST} ), '(int32){m}' )"

    def test_the_checker_itself(self):
        ok = [self.widget(self.size("GreaterThanOrEqualTo_int32", 60)),
              self.widget(self.size("GreaterThan_int32", 59)),
              self.widget(f"And( GetVariableSystem.Exists('x'), {self.size('GreaterThanOrEqualTo_int32', 60)} )"),
              self.widget(self.size("GreaterThanOrEqualTo_int32", 60), own=False),          # on the parent
              self.widget(self.size("GreaterThan_int32", 10), fn="DataModelSkipFirst", n=10),
              self.widget(None, fn="DataModelFirst")]                                       # silent past the end
        for text in ok:
            self.assertEqual(unguarded(text), [], text)
        bad = [self.widget(None),
               self.widget("GetVariableSystem.Exists('x')"),
               self.widget(self.size("GreaterThanOrEqualTo_int32", 59)),                    # one short
               self.widget(self.size("GreaterThan_int32", 58)),
               self.widget(self.size("LessThan_int32", 60)),                                # the wrong way round
               self.widget(self.size("GreaterThanOrEqualTo_int32", 60).replace("te_hist", "te_dg_hist")),
               self.widget(self.size("GreaterThan_int32", 8), fn="DataModelSkipFirst", n=10),
               self.widget(self.size("GreaterThanOrEqualTo_int32", 60), fn="DataModelSubSpan")]
        for text in bad:
            self.assertEqual(len(unguarded(text)), 1, text)
        # a slice of an engine list is vanilla's business
        self.assertEqual(unguarded('widget = { datamodel = "[DataModelLast( State.GetSamplePops, \'(int32)1\' )]" }'), [])
        # a comment is not markup
        self.assertEqual(unguarded("# datamodel = \"[DataModelLast( " + self.LIST + ", '(int32)60' )]\"\n"), [])

    def test_no_mod_gui_slices_a_script_list_unguarded(self):
        seen = 0
        for folder, _dirs, files in os.walk(GUI):
            for name in sorted(files):
                if not name.endswith(".gui"):
                    continue
                path = os.path.join(folder, name)
                with open(path, encoding="utf-8-sig") as handle:
                    text = handle.read()
                if "GetList(" not in text or "DataModel" not in text:
                    continue
                seen += len(SLICE.findall(_strip_comments(text)))
                with self.subTest(file=os.path.relpath(path, REPO)):
                    self.assertEqual(
                        unguarded(text), [],
                        "a slice of a script list longer than the list logs an error every frame: put it in a widget "
                        "whose visible tests GreaterThanOrEqualTo_int32( GetDataModelSize( <the list> ), '(int32)N' ), "
                        "beside one that reads the whole list while it is shorter (gui_modding_guide.md, the "
                        "datamodel-slicing bullet)")
        self.assertGreater(seen, 100, "the history charts' plots and the Stations table were not found")


if __name__ == "__main__":
    unittest.main()
