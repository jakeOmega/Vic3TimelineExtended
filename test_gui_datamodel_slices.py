"""A datamodel slice over a script list never asks for more than the list holds.

`DataModelLast( <list>, '(int32)N' )` on a list shorter than N logs "Trying to
reshape data model with negative offset -N" every frame for every widget that
does, and `DataModelSkipFirst` its sibling, "... negative count -N" (seen in
game 2026-11-24: 300 to 430 lines a second from the history charts in a game
of January 1836, 75 a second from one scratch widget; PR #2036).
`DataModelFirst` past a list's end is silent, so it is not held here.

A script list (`...GetList('<name>')`, `GetGlobalList('<name>')`) can be any
length, so each such slice in a mod `.gui` file must sit in a widget, or under
one, whose own `visible` tests the list's size:
`GreaterThanOrEqualTo_int32( GetDataModelSize( <list> ), N )`, or a
`GreaterThan_int32` of at least N - 1, alone or under `And(`. A hidden widget's
datamodel is not evaluated (no line was ever logged for a hidden plot). The
test must be on the slicing widget or an ancestor (a sibling's or a child's
`visible` hides something else), must not sit under `Or(` or `Not(` (a flag
beside it, or its opposite, does not protect), and must name the list as the
slice does. The engine's own lists, in the mod's copies of vanilla panels, are
left to vanilla.
"""
import os
import re
import unittest

from gui_test_helpers import _strip_comments

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui")

STRING = r'"(?:[^"\\]|\\.)*"'
TOKEN = re.compile(rf'(?P<visible>\bvisible\s*=\s*{STRING})|(?P<string>{STRING})|(?P<open>\{{)|(?P<close>\}})')
SCRIPT_LIST = r"Get(?:Global)?List\s*\("
SLICER = re.compile(r"\b(DataModelLast|DataModelSkipFirst|DataModelSubSpan)\s*\(")
SLICE = re.compile(r"\b(DataModelLast|DataModelSkipFirst|DataModelSubSpan)\(\s*"
                   r"((?:[^()']|'[^']*'|\((?:[^()']|'[^']*')*\))*?Get(?:Global)?List\('\w+'\))\s*,\s*'\(int32\)(\d+)'")
GUARD = re.compile(r"\b(GreaterThanOrEqualTo_int32|GreaterThan_int32)\(\s*GetDataModelSize\(\s*(.*?)\s*\)\s*,\s*'\(int32\)(\d+)'\s*\)")
CALL = re.compile(r"(\w+)\(|\(|\)")


def _squash(text):
    return re.sub(r"\s+", "", text)


def _arguments(text, open_paren):
    """The text between a call's opening parenthesis and its match (quotes skipped)."""
    depth, i, quoted = 0, open_paren, False
    while i < len(text):
        c = text[i]
        if c == "'":
            quoted = not quoted
        elif not quoted:
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return text[open_paren + 1:i]
        i += 1
    return text[open_paren + 1:]


def _under_and_only(expr, at):
    """Whether every call open around position at, inside expr, is And or And<N>."""
    plain = re.sub(r"'[^']*'", lambda m: " " * len(m.group()), expr)
    names = []
    for call in CALL.finditer(plain, 0, at):
        if call.group() == ")":
            if names:
                names.pop()
        else:
            names.append(call.group(1) or "")
    return all(re.fullmatch(r"And\d*", name) for name in names)


def _holds_enough(expr, wanted_list, n):
    """Whether a visible expression tests that the list holds at least n."""
    for guard in GUARD.finditer(expr):
        op, tested, m = guard.groups()
        if _squash(tested) != _squash(wanted_list) or not _under_and_only(expr, guard.start()):
            continue
        if (op == "GreaterThanOrEqualTo_int32" and int(m) >= n) or (op == "GreaterThan_int32" and int(m) >= n - 1):
            return True
    return False


def unguarded(text):
    """Every script-list slice in text with no size test on its widget or above
    it, as (line, function, list, count); a slice of a script list the test
    cannot read comes back with the function "unreadable"."""
    text = _strip_comments(text)
    stack, visibles, slices, serial = [], {}, [], 0
    for token in TOKEN.finditer(text):
        if token.group("open"):
            serial += 1
            stack.append(serial)
        elif token.group("close"):
            if stack:
                stack.pop()
        elif token.group("visible"):
            # the innermost block open here owns it, whatever line it is on
            visibles.setdefault(stack[-1] if stack else 0, []).append(token.group("visible"))
        else:
            value, line = token.group("string"), text.count("\n", 0, token.start()) + 1
            for slicer in SLICER.finditer(value):
                found = SLICE.match(value, slicer.start())
                if found:
                    slices.append((line, found.group(1), found.group(2), int(found.group(3)), tuple(stack)))
                elif re.search(SCRIPT_LIST, _arguments(value, slicer.end() - 1)):
                    slices.append((line, "unreadable", _squash(value[slicer.start():slicer.start() + 80]), 0, ()))
    out = []
    for line, fn, the_list, n, ancestors in slices:
        guarded = fn in ("DataModelLast", "DataModelSkipFirst") and any(
            _holds_enough(v, the_list, n) for block in ancestors for v in visibles.get(block, []))
        if not guarded:      # a sub-span has no rule yet: it needs its from + count of the list
            out.append((line, fn, the_list, n))
    return out


class SliceGuardTest(unittest.TestCase):
    L = "Country.MakeScope.GetList('te_hist')"
    G = f"GreaterThanOrEqualTo_int32( GetDataModelSize( {L} ), '(int32)60' )"
    S = f"DataModelLast( {L}, '(int32)60' )"

    def widget(self, visible, fn="DataModelLast", n=60, own=True):
        gate = f'visible = "[{visible}]"' if visible else ""
        inner = f"flowcontainer = {{\n\t\t{gate if own else ''}\n\t\tblockoverride \"rows\" {{\n\t\t\t" \
                f"datamodel = \"[{fn}( {self.L}, '(int32){n}' )]\"\n\t\t}}\n\t}}"
        return f"widget = {{\n\t{'' if own else gate}\n\ttooltip = \"a {{ brace }} in a string\"\n\t{inner}\n}}\n"

    def size(self, op, m):
        return f"{op}( GetDataModelSize( {self.L} ), '(int32){m}' )"

    def test_guards_the_checker_accepts(self):
        L, G, S = self.L, self.G, self.S
        ok = [self.widget(G),
              self.widget(self.size("GreaterThan_int32", 59)),
              self.widget(self.size("GreaterThanOrEqualTo_int32", 240)),                    # more than needed
              self.widget(f"And( GetVariableSystem.Exists('x'), {G} )"),
              self.widget(f"And( GetVariableSystem.Exists('x'), And3( A, B, {G} ) )"),
              self.widget(G, own=False),                                                    # on the parent
              self.widget(self.size("GreaterThan_int32", 10), fn="DataModelSkipFirst", n=10),
              self.widget(None, fn="DataModelFirst"),                                       # silent past the end
              # a visible written over several lines, and one on the line that opens a child
              f'widget = {{\n\tvisible = "[And(\n\t\tGetVariableSystem.Exists(\'x\'),\n\t\t{G} )]"\n\tdatamodel = "[{S}]"\n}}\n',
              f'widget = {{\n\tvisible = "[{G}]" flowcontainer = {{\n\t\tdatamodel = "[{S}]"\n\t}}\n}}\n',
              # spacing inside the guard's list does not matter
              self.widget(G.replace("Country.MakeScope.GetList('te_hist')", "Country.MakeScope.GetList('te_hist') ")),
              f'widget = {{ visible = "[{G.replace("GetList", "GetGlobalList")}]" '
              f'datamodel = "[{S.replace("GetList", "GetGlobalList")}]" }}']
        for text in ok:
            self.assertEqual(unguarded(text), [], text)
        # a slice of an engine list is vanilla's business, and a comment is not markup
        self.assertEqual(unguarded('widget = { datamodel = "[DataModelLast( State.GetSamplePops, \'(int32)1\' )]" }'), [])
        self.assertEqual(unguarded(f'# datamodel = "[{S}]"\n'), [])
        self.assertEqual(L.count("GetList"), 1)

    def test_faults_the_checker_reports(self):
        L, G, S = self.L, self.G, self.S
        bad = [self.widget(None),
               self.widget("GetVariableSystem.Exists('x')"),
               self.widget(self.size("GreaterThanOrEqualTo_int32", 59)),                    # one short
               self.widget(self.size("GreaterThan_int32", 58)),
               self.widget(self.size("LessThan_int32", 60)),                                # the wrong way round
               self.widget(G.replace("te_hist", "te_dg_hist")),                             # another list
               self.widget(self.size("GreaterThan_int32", 8), fn="DataModelSkipFirst", n=10),
               self.widget(G, fn="DataModelSubSpan"),
               # a flag beside the test, or its opposite, does not protect
               self.widget(f"Or( GetVariableSystem.Exists('x'), {G} )"),
               self.widget(f"Not( {G} )"),
               self.widget(f"Or3( IsDebug, GetVariableSystem.Exists('x'), {G} )"),
               self.widget(f"And( A, Or( B, {G} ) )"),
               # a sibling's, a child's or another block's visible hides something else
               f'widget = {{\n\twidget = {{ visible = "[{G}]" }}\n\tflowcontainer = {{\n\t\tdatamodel = "[{S}]"\n\t}}\n}}\n',
               f'flowcontainer = {{\n\tdatamodel = "[{S}]"\n\titem = {{ widget = {{ visible = "[{G}]" }} }}\n}}\n',
               f'widget = {{\n\tblockoverride "other" {{ visible = "[{G}]" }}\n\tflowcontainer = {{\n\t\tdatamodel = "[{S}]"\n\t}}\n}}\n',
               f'widget = {{\n\twidget = {{\n\t\tsize = {{ 1 1 }}\n\t\tvisible = "[{G}]" }}\n\tflowcontainer = {{\n\t\tdatamodel = "[{S}]"\n\t}}\n}}\n',
               # a slice of a script list written in a way the test cannot read is reported, not passed
               f'widget = {{ visible = "[{G}]" datamodel = "[DataModelLast ( {L}, \'(int32)60\' )]" }}',
               f'widget = {{ visible = "[{G}]" datamodel = "[DataModelLast( Country.MakeScope.GetList( \'te_hist\' ), \'(int32)60\' )]" }}',
               f'widget = {{ visible = "[{G}]" datamodel = "[DataModelLast( {L}, GetVariableSystem.GetInt(\'n\') )]" }}']
        for text in bad:
            self.assertEqual(len(unguarded(text)), 1, text)
        self.assertEqual([found[1] for text in bad[-3:] for found in unguarded(text)], ["unreadable"] * 3)
        # the report says where: the slice's line
        self.assertEqual(unguarded("a = {\n\n\tdatamodel = \"[" + S + "]\"\n}\n")[0][0], 3)
        # the same slice twice, one of them guarded
        twice = self.widget(G) + self.widget(None)
        self.assertEqual(len(unguarded(twice)), 1)

    def test_no_mod_gui_slices_a_script_list_unguarded(self):
        seen = 0
        for folder, _dirs, files in os.walk(GUI):
            for name in sorted(files):
                if not name.endswith(".gui"):
                    continue
                path = os.path.join(folder, name)
                with open(path, encoding="utf-8-sig") as handle:
                    text = handle.read()
                if "DataModel" not in text or not re.search(SCRIPT_LIST, text):
                    continue
                seen += len(SLICE.findall(_strip_comments(text)))
                with self.subTest(file=os.path.relpath(path, REPO)):
                    self.assertEqual(
                        unguarded(text), [],
                        "(line, function, list, count) of each slice of a script list with no size test. Asked for "
                        "more than the list holds it logs an error every frame: put a DataModelLast or "
                        "DataModelSkipFirst in a widget whose own visible holds GreaterThanOrEqualTo_int32( "
                        "GetDataModelSize( <the list, written as the slice writes it> ), '(int32)N' ), alone or under "
                        "And(, beside a widget that reads the whole list while it is shorter (gui_modding_guide.md, "
                        "the datamodel-slicing bullet). \"unreadable\" is a slice this test could not parse (write "
                        "DataModelLast( X.GetList('name'), '(int32)N' ) or teach the test); a DataModelSubSpan of a "
                        "script list has no rule here yet: add one with its guard")
        self.assertGreater(seen, 100, "the history charts' plots and the Stations table were not found")


if __name__ == "__main__":
    unittest.main()
