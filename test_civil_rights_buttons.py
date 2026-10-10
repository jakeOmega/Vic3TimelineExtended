# -*- coding: utf-8 -*-
"""The civil rights policy buttons' tooltips state the policies' real figures.

The journal entry's button grid prints each button's effect tooltip, so the
policy modifier is added and removed bare (the engine lists its lines) and the
effects a modifier can't show are cr_btn_*_tt lines written out in
localization: the monthly Movement Support push, which lives in
civil_rights_support_bar, and the month thresholds of the endings, which live
in je_civil_rights. Nothing ties those numbers to the loc but these tests.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

BUTTONS = os.path.join("common", "scripted_buttons", "civil_rights_buttons.txt")
BAR = os.path.join("common", "scripted_progress_bars", "extra_progress_bars.txt")
JE = os.path.join("common", "journal_entries", "je_civil_rights.txt")
VALUES = os.path.join("common", "script_values", "civil_rights_values.txt")
MODIFIERS = os.path.join("common", "static_modifiers", "extra_modifiers.txt")
EVENTS = os.path.join("events", "movement_events_te.txt")
LOC_DIR = os.path.join("localization", "english")

# Policy modifier -> the token its cr_btn_<token>_* loc keys use.
POLICIES = {
    "cr_grassroots_modifier": "grassroots",
    "cr_federal_protection_modifier": "federal",
    "cr_gradualist_modifier": "gradualist",
    "cr_cooptation_modifier": "cooptation",
    "cr_suppression_modifier": "suppression",
    "cr_segregationist_modifier": "segregationist",
}

# Victory ending link key -> (the event that grants it, the modifier it grants).
ENDINGS = {
    "federal": ("movement_events_te.220", "civil_rights_triumph_federal_modifier"),
    "grassroots": ("movement_events_te.221", "civil_rights_triumph_grassroots_modifier"),
    "gradualist": ("movement_events_te.222", "civil_rights_triumph_gradualist_modifier"),
    "coopted": ("movement_events_te.223", "civil_rights_triumph_coopted_modifier"),
}


def _read(rel, strip_comments=True):
    with open(os.path.join(REPO, rel), encoding="utf-8-sig") as f:
        text = f.read()
    return re.sub(r"#[^\n]*", "", text) if strip_comments else text


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unbalanced braces")


def _block(text, name, top_level=True):
    anchor = r"^" if top_level else r"(?<![\w.:])"
    m = re.search(anchor + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _loc():
    keys = {}
    for name in os.listdir(os.path.join(REPO, LOC_DIR)):
        if not name.endswith(".yml"):
            continue
        with open(os.path.join(REPO, LOC_DIR, name), encoding="utf-8-sig") as f:
            for line in f:
                m = re.match(r'\s+([\w.\-]+):\d*\s+"(.*)"\s*$', line)
                if m:
                    keys[m.group(1)] = m.group(2)
    return keys


def _signed(value):
    """+0.2 / −0.6, as the tooltips print a push (the minus is U+2212)."""
    text = f"{abs(value):g}"
    return f"+{text}" if value > 0 else f"−{text}"


def _buttons():
    text = _read(BUTTONS)
    out = {}
    for name in re.findall(r"^(cr_\w+)\s*=\s*\{", text, re.M):
        effect = _block(_block(text, name), "effect", top_level=False)
        added = re.findall(r"add_modifier\s*=\s*\{\s*name\s*=\s*(\w+)", effect)
        removed = [m for m in re.findall(r"remove_modifier\s*=\s*(\w+)", effect) if m in POLICIES]
        out[name] = (effect, (added or removed)[0], bool(added))
    return out


class ModifierShownTests(unittest.TestCase):
    def test_policy_modifier_is_not_hidden_behind_a_custom_tooltip(self):
        # A custom_tooltip = { text = ... <effects> } block prints its text in
        # place of the effects inside it, which hid every figure until 2026-10.
        for name, (effect, _mod, _on) in _buttons().items():
            with self.subTest(button=name):
                self.assertNotRegex(effect, r"custom_tooltip\s*=\s*\{")
                self.assertNotRegex(effect, r"hidden_effect")


class PushFigureTests(unittest.TestCase):
    def setUp(self):
        bar = _block(_block(_read(BAR), "civil_rights_support_bar"), "monthly_progress", top_level=False)
        self.push = {}
        for m in re.finditer(r"has_modifier\s*=\s*(cr_\w+_modifier)\b", bar):
            if m.group(1) not in POLICIES:
                continue
            value = re.search(r"value\s*=\s*(-?[\d.]+)", bar[m.end():])
            self.push[m.group(1)] = float(value.group(1))
        self.loc = _loc()

    def test_bar_has_a_line_for_every_policy(self):
        self.assertEqual(set(self.push), set(POLICIES))

    def test_push_and_stop_lines_state_the_bar_figure(self):
        for mod, token in POLICIES.items():
            colour = "#P" if self.push[mod] > 0 else "#N"
            expected = f"{colour} {_signed(self.push[mod])}#!"
            for kind in ("push", "stop"):
                key = f"cr_btn_{token}_{kind}_tt"
                with self.subTest(key=key):
                    self.assertIn(key, self.loc)
                    self.assertIn(expected, self.loc[key])

    def test_each_button_prints_its_own_policy_line(self):
        for name, (effect, mod, on) in _buttons().items():
            token = POLICIES[mod]
            key = f"cr_btn_{token}_{'push' if on else 'stop'}_tt"
            with self.subTest(button=name):
                self.assertRegex(effect, r"custom_tooltip\s*=\s*" + key + r"\b")
                others = set(POLICIES.values()) - {token}
                for other in others:
                    self.assertNotRegex(effect, rf"cr_btn_{other}_(?:push|stop)_tt\b")


class ThresholdTests(unittest.TestCase):
    def setUp(self):
        self.loc = _loc()
        self.je = _block(_read(JE), "je_civil_rights")

    def test_cooptation_window(self):
        pulse = _block(self.je, "on_monthly_pulse", top_level=False)
        window = re.search(r"var:cr_cooptation_months\s*>=\s*(\d+)\s+NOT\s*=\s*\{\s*has_modifier\s*=\s*cr_cooptation_expired", pulse)
        months = window.group(1)
        self.assertRegex(_block(_read(VALUES), "cr_cooptation_months_left"), r"^\s*value\s*=\s*" + months + r"\b")
        for key in ("cr_btn_cooptation_push_tt", "cr_btn_cooptation_push_spent_tt", "cr_btn_cooptation_stop_tt"):
            with self.subTest(key=key):
                self.assertIn(f"#v {months}#!", self.loc[key])

    def test_ending_threshold(self):
        hooks = _block(self.je, "on_complete", top_level=False) + _block(self.je, "on_fail", top_level=False)
        thresholds = set(re.findall(r"var:cr_\w+_months\s*>\s*(\d+)", hooks))
        self.assertEqual(len(thresholds), 1, thresholds)
        months = thresholds.pop()
        for key in ("cr_btn_grassroots_ending_tt", "cr_btn_federal_ending_tt",
                    "cr_btn_gradualist_ending_tt", "cr_btn_cooptation_ending_tt"):
            with self.subTest(key=key):
                self.assertIn(f"#v {months}#!", self.loc[key])

    def test_federal_commission_threshold(self):
        pulse = _block(self.je, "on_monthly_pulse", top_level=False)
        m = re.search(r"var:cr_federal_months\s*>\s*(\d+)\s*\}\s*trigger_event\s*=\s*\{\s*id\s*=\s*movement_events_te\.304", pulse)
        self.assertIsNotNone(m)
        self.assertIn(f"#v {m.group(1)}#!", self.loc["cr_btn_federal_commission_tt"])
        self.assertIn("cr_tier_75_seen", _block(_buttons()["cr_federal_protection"][0], "if", top_level=False))


class EndingLinkTests(unittest.TestCase):
    def test_links_name_the_event_and_show_its_modifier(self):
        loc = _loc()
        events = _read(EVENTS)
        modifiers = _read(MODIFIERS)
        for token, (event, modifier) in ENDINGS.items():
            with self.subTest(ending=token):
                title = loc[f"{event}.t"]
                self.assertIn(f"#b {title}#!", loc[f"cr_btn_ending_{token}"])
                self.assertIn(f"tooltip:[GetPlayer.GetTooltipTag],cr_btn_ending_{token}_tt ", loc[f"cr_btn_ending_{token}"])
                self.assertIn(f"GetStaticModifier('{modifier}').GetDesc", loc[f"cr_btn_ending_{token}_tt"])
                self.assertRegex(modifiers, r"(?m)^" + modifier + r"\s*=\s*\{")
                self.assertRegex(_block(events, event), r"add_modifier\s*=\s*\{\s*name\s*=\s*" + modifier + r"\b")

    def test_every_referenced_key_exists(self):
        loc = _loc()
        buttons = _read(BUTTONS)
        keys = set(re.findall(r"custom_tooltip\s*=\s*(\w+)", buttons))
        for key in sorted(keys):
            with self.subTest(key=key):
                self.assertIn(key, loc)
        for key, text in loc.items():
            if key.startswith("cr_btn_"):
                for ref in re.findall(r"\$(\w+)\$", text):
                    with self.subTest(key=key, ref=ref):
                        self.assertIn(ref, loc | {"TOOLTIP_DELIMITER": ""})


if __name__ == "__main__":
    unittest.main()
