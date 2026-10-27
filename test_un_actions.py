# -*- coding: utf-8 -*-
"""The UN journal entry's buttons are the AI's; the panel's controls mirror them.

The 2026-10-27 GUI audit's UN-9 (owner decision of the same day): every
scripted_button on je_united_nations carries `is_ai = yes` in its `visible`,
Banking's proven way to hide a journal entry's grid from a human, and a human
acts through a scripted GUI beside the figure each button acts on
(common/scripted_guis/un_action_sguis.txt). Nothing in the engine checks that
a control and its button agree, or that a control is drawn at all: a mirror
that drifts, or one nobody places, gives the human and the AI different rules,
or the human no way to act. These tests hold each mirror to its button word
for word, and each to a place in the UN's panels.

Run: python3 -m unittest test_un_actions -v
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
JE = os.path.join(REPO, "common", "journal_entries", "je_united_nations.txt")
BUTTON_FILES = [os.path.join(REPO, "common", "scripted_buttons", f)
                for f in ("un_buttons.txt", "un_economy_buttons.txt")]
SGUIS = os.path.join(REPO, "common", "scripted_guis", "un_action_sguis.txt")
PROPOSE_SGUIS = os.path.join(REPO, "common", "scripted_guis", "un_chamber_sguis.txt")
WIDGETS = [os.path.join(REPO, "gui", "journal_entry_widgets", f) for f in
           ("un_overview_widget.gui", "un_chamber_widget.gui", "un_authority_widget.gui",
            "un_layout_widget.gui")]
TAB = os.path.join(REPO, "gui", "diplomatic_overview.gui")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return "\n".join(line.split("#", 1)[0] for line in text.split("\n"))


def _flat(text):
    return " ".join(_strip(text).split())


def _body(text, start):
    """The body of the brace block opening at or after `start`."""
    j = text.index("{", start)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[j + 1:k]
    raise AssertionError("unbalanced block")


def _top(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert m, f"no {name}"
    return _body(text, m.end() - 1)


def _part(body, name):
    m = re.search(rf"(?m)^\t{name} = \{{", body)
    assert m, f"no {name}"
    return _body(body, m.end() - 1)


def _buttons():
    out = {}
    for path in BUTTON_FILES:
        text = _strip(_read(path))
        for m in re.finditer(r"(?m)^(un_\w+_button) = \{", text):
            out[m.group(1)] = _body(text, m.end() - 1)
    return out


def _mirror_name(button):
    return "un_act_" + button[len("un_"):-len("_button")] + "_sgui"


# The proposals: a human tables each from the General Assembly's Propose rows,
# through un_chamber_propose_sgui, which asks the same un_propose_<key>_possible
# and runs the same un_propose_<key>_effect.
PROPOSALS = re.compile(r"^un_(propose|request)_\w+_button$")


class ButtonsAreTheAisTest(unittest.TestCase):
    def test_every_registered_button_is_hidden_from_a_human(self):
        registered = re.findall(r"(?m)^\s*scripted_button = (\w+)", _strip(_read(JE)))
        self.assertGreaterEqual(len(registered), 39)
        buttons = _buttons()
        for name in registered:
            with self.subTest(button=name):
                visible = _flat(_part(buttons[name], "visible"))
                self.assertTrue(visible.startswith("is_ai = yes"), visible)

    def test_the_tab_has_no_button_grid(self):
        tab = _read(TAB)
        start = tab.index("name = \"te_diplomacy_un_tab\"")
        un_tab = tab[start:tab.index("### END MOD ###", start)]
        self.assertIn("te_un_status_sections = {}", un_tab)
        self.assertNotIn("te_je_scripted_buttons", un_tab)
        self.assertNotIn("te_un_tab_actions_closed", un_tab)


class MirrorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.buttons = _buttons()
        cls.sguis = _strip(_read(SGUIS))
        cls.widgets = "\n".join(_read(p) for p in WIDGETS)

    def test_every_other_button_has_a_mirror(self):
        mirrored = set(re.findall(r"(?m)^(un_act_\w+_sgui) = \{", self.sguis))
        for name in self.buttons:
            if PROPOSALS.match(name):
                continue
            with self.subTest(button=name):
                self.assertIn(_mirror_name(name), mirrored)
        self.assertEqual(len(mirrored), len([b for b in self.buttons if not PROPOSALS.match(b)]))

    def test_each_mirror_says_what_its_button_says(self):
        for name, body in self.buttons.items():
            if PROPOSALS.match(name):
                continue
            sgui = _top(self.sguis, _mirror_name(name))
            with self.subTest(button=name):
                visible = _flat(_part(body, "visible"))
                self.assertEqual(_flat(_part(sgui, "is_shown")), visible[len("is_ai = yes "):].strip())
                self.assertEqual(_flat(_part(sgui, "is_valid")), _flat(_part(body, "possible")))
                self.assertEqual(_flat(_part(sgui, "effect")), _flat(_part(body, "effect")))
                self.assertIn("ai_is_valid = { always = no }", _flat(sgui))
                self.assertNotIn("saved_scopes", sgui)

    def test_each_mirror_is_placed(self):
        for name in self.buttons:
            if PROPOSALS.match(name):
                continue
            with self.subTest(button=name):
                self.assertIn(f"GetScriptedGui('{_mirror_name(name)}')", self.widgets)

    def test_every_proposal_is_the_chambers_too(self):
        propose = _flat(_top(_strip(_read(PROPOSE_SGUIS)), "un_chamber_propose_sgui"))
        for name, body in self.buttons.items():
            if not PROPOSALS.match(name) or name == "un_request_humanitarian_aid_button":
                continue
            key = re.search(r"un_propose_(\w+)_possible = yes", _flat(body)).group(1)
            with self.subTest(button=name):
                self.assertIn(f"un_propose_{key}_possible = yes", propose)
                self.assertIn(f"un_propose_{key}_effect = yes", propose)
        self.assertIn("un_propose_aid_possible = yes", propose)


class ControlTypeTest(unittest.TestCase):
    def test_a_greyed_control_says_why(self):
        chamber = _read(WIDGETS[1])
        body = chamber[chamber.index("type un_act_control = flowcontainer {"):]
        body = _body(body, 0)
        self.assertIn("ScriptedGui.IsValidTooltip(", body)
        self.assertIn("ScriptedGui.ExecuteTooltip(", body)
        self.assertIn("enabled = \"[ScriptedGui.IsValid(", body)
        self.assertNotIn("AddScope", body)

    def test_leaving_is_armed_first(self):
        overview = _read(WIDGETS[0])
        start = overview.index("datacontext = \"[GetScriptedGui('un_act_leave_sgui')]\"")
        block = overview[start:start + 4000]
        first = block.index("onclick")
        self.assertIn("GetVariableSystem.Toggle('un_leave_armed')", block[first:first + 80])
        self.assertIn("ScriptedGui.Execute(", block)


if __name__ == "__main__":
    unittest.main()
