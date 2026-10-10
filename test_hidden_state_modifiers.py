"""The state panel's modifier rows and the mod's blank-icon modifiers.

Some state modifiers are the mod's bookkeeping, refreshed by script each month
or step: tourism, pollution, migration crowding, the free port's tariffs, and
the demographics census's corrections to birth and death rates. They carry the
mod's blank icon, modifier_system.dds, and still take an empty slot in the
state panel's rows. A GUI cannot leave them out: `TimedModifier` has no GetKey
(GetName and GetDesc are localized), and comparing its icon,
`EqualTo_string(TimedModifier.GetIcon, '<path>')`, fails at runtime with
"FetchData failed" on every frame the row is drawn (2026-10-10: 13,690 lines in
minutes, from both rows; GetIcon is not a string). No row may try it.

The condensed view's box fades out when the state carries nothing else, which
needs a count of the blank-icon modifiers the GUI cannot make itself:
gui_state_hidden_modifier_count (common/script_values/gui_chart_script_values.txt)
names each static modifier with that icon by a has_modifier term. This test
fails when a static modifier takes that icon without a term there.
"""
import os
import re
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui")
STATIC_MODIFIERS = os.path.join(REPO, "common", "static_modifiers")
COUNT_FILE = os.path.join(REPO, "common", "script_values", "gui_chart_script_values.txt")
COUNT = "gui_state_hidden_modifier_count"

# The mod's one invisible modifier icon (4x4, alpha 0): a bookkeeping modifier
# carries it and gets a term in gui_state_hidden_modifier_count.
HIDDEN_ICONS = (
    "gfx/interface/icons/timed_modifier_icons/modifier_system.dds",
)

DATAMODEL = 'datamodel = "[State.GetTimedModifiers]"'


def _strip_comments(text):
    """The text with `# ...` comments blanked, keeping a quoted `#` and every
    offset unchanged."""
    out = []
    in_string = in_comment = False
    for ch in text:
        if in_comment:
            if ch == "\n":
                in_comment = False
                out.append(ch)
            else:
                out.append(" ")
            continue
        if ch == '"':
            in_string = not in_string
        elif ch == "#" and not in_string:
            in_comment = True
            out.append(" ")
            continue
        elif ch == "\n":
            in_string = False
        out.append(ch)
    return "".join(out)


def _block_around(text, pos):
    """(opener, start, end) of the innermost `name = { ... }` holding `pos`."""
    depth = 0
    i = pos
    while i >= 0:
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth == 0:
                break
            depth -= 1
        i -= 1
    start = i
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    line_start = text.rfind("\n", 0, start) + 1
    opener = re.match(r"\s*(\w+)", text[line_start:start]).group(1)
    return opener, start, end


def _own_lines(block):
    """The block's own properties: its text with every nested `{ ... }` removed."""
    out, depth = [], 0
    for ch in block[1:-1]:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def _sites():
    """One dict per container in gui/**/*.gui whose datamodel is a state's
    timed modifiers."""
    found = []
    for root, _, files in os.walk(GUI):
        for fn in sorted(files):
            if not fn.endswith(".gui"):
                continue
            path = os.path.join(root, fn)
            with open(path, encoding="utf-8-sig") as f:
                text = _strip_comments(f.read())
            for m in re.finditer(re.escape(DATAMODEL), text):
                opener, start, end = _block_around(text, m.start())
                block = text[start:end]
                item = re.search(r"\bitem\s*=\s*\{", block)
                found.append({
                    "where": f"{os.path.relpath(path, REPO)}:{text.count(chr(10), 0, m.start()) + 1}",
                    "container": opener,
                    "own": _own_lines(block),
                    "item": block[item.start():] if item else "",
                })
    return found


def _entries(node):
    for part in node if isinstance(node, list) else [node]:
        for key, (op, value) in part.items():
            yield key, op, value


def _parse(path):
    parser = ParadoxFileParser()
    with open(path, encoding="utf-8-sig") as f:
        return parser.parse_object(parser.tokenize("{" + f.read() + "}"))[0]


def _blank_icon_modifiers():
    names = set()
    for fn in sorted(os.listdir(STATIC_MODIFIERS)):
        if not fn.endswith(".txt"):
            continue
        for key, _, block in _entries(_parse(os.path.join(STATIC_MODIFIERS, fn))):
            if not isinstance(block, (dict, list)):
                continue
            icons = [value for k, _, value in _entries(block) if k == "icon"]
            if any(icon in HIDDEN_ICONS for icon in icons):
                names.add(key.split(":", 1)[-1])
    return names


def _count_terms():
    """{modifier: add} for each `if = { limit = { has_modifier = X } add = N }`."""
    tree = dict((k, v) for k, _, v in _entries(_parse(COUNT_FILE)))
    terms = {}
    for key, _, value in _entries(tree[COUNT]):
        if key != "if":
            continue
        fields = dict((k, v) for k, _, v in _entries(value))
        limit = dict((k, v) for k, _, v in _entries(fields["limit"]))
        terms[limit["has_modifier"]] = fields.get("add")
    return terms


class HiddenStateModifierTest(unittest.TestCase):
    def setUp(self):
        self.sites = _sites()

    def test_both_state_panel_rows_are_found(self):
        # The full view's row over the state's picture and the condensed view's box.
        where = [site["where"].split(":")[0] for site in self.sites]
        self.assertGreaterEqual(where.count("gui/states_panel.gui"), 2, self.sites)

    def test_no_gui_compares_a_modifiers_icon_as_a_string(self):
        # GetIcon is not a string: EqualTo_string on it fails every frame (#872's filter, removed)
        for root, _, files in os.walk(GUI):
            for fn in sorted(files):
                if fn.endswith(".gui"):
                    path = os.path.join(root, fn)
                    with open(path, encoding="utf-8-sig") as f:
                        text = _strip_comments(f.read())
                    lines = [text.count("\n", 0, m.start()) + 1
                             for m in re.finditer(r"EqualTo_string\(\s*TimedModifier\.GetIcon", text)]
                    self.assertFalse(lines, f"{os.path.relpath(path, REPO)} compares TimedModifier.GetIcon at lines {lines}")

    def test_no_row_treats_hidden_modifiers_as_content(self):
        # An emptiness test on the raw list counts the hidden modifiers too,
        # and tourism and pollution sit on every state.
        for site in self.sites:
            with self.subTest(site=site["where"]):
                self.assertNotIn("IsDataModelEmpty(State.GetTimedModifiers)", site["own"])
                if "alpha" in site["own"]:
                    self.assertIn(f"ScriptValue('{COUNT}')", site["own"])

    def test_count_names_every_blank_icon_modifier(self):
        terms = _count_terms()
        blank = _blank_icon_modifiers()
        self.assertTrue(blank)
        missing = sorted(blank - set(terms))
        self.assertFalse(missing, f"static modifiers with a hidden icon and no has_modifier term in {COUNT} ({os.path.relpath(COUNT_FILE, REPO)}): {missing}")
        extra = sorted(set(terms) - blank)
        self.assertFalse(extra, f"{COUNT} counts modifiers the state panel shows (icon not in HIDDEN_ICONS): {extra}")
        self.assertEqual(set(terms.values()), {"1"})


if __name__ == "__main__":
    unittest.main()
