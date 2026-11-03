# -*- coding: utf-8 -*-
"""A country's stance on colonialism, and the Colonial Empire tab that outlives
the entry (owner, 2026-11-03).

The entry closes when it fails, succeeds or loses its colonies, and the tab
used to close with it, while The Colonial Question (decolonization_events.14)
asked every great power for a stance every three years. Now:

- the stance changes from the tab: three buttons, a cooldown, and influence
  for either side while the stance counts (a great power's);
- a player meets The Colonial Question once; the AI keeps it, with an
  influence start line and a monthly drop below zero;
- the tab opens once the country has researched Decolonization, showing the
  stance and the largest colonial powers without the entry.

These tests hold the pieces to one another: the setters are the only writers
of the stance, every surface calls them, the figures agree, and the sections
the tab shows without the entry never read the entry.

Run: python3 -m unittest test_decolonization_stance -v
"""

import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


EFFECTS = _path("common", "scripted_effects", "decolonization_stance_effects.txt")
TRIGGERS = _path("common", "scripted_triggers", "decolonization_stance_triggers.txt")
VALUES = _path("common", "script_values", "decolonization_stance_values.txt")
MODIFIERS = _path("common", "static_modifiers", "extra_modifiers.txt")
EVENTS = _path("events", "decolonization_events.txt")
ON_ACTIONS = _path("common", "on_actions", "extra_on_actions.txt")
UN_VOTE = _path("common", "scripted_effects", "un_vote_effects.txt")
DECOL = _path("common", "scripted_effects", "decolonization.txt")
CE_SGUIS = _path("common", "scripted_guis", "colonial_empire_sguis.txt")
TAB_SGUIS = _path("common", "scripted_guis", "te_system_tab_sguis.txt")
GUI = _path("gui", "journal_entry_widgets", "colonial_empire_widget.gui")
LOC_DIR = _path("localization", "english")

STANCE_VARS = ("gp_anti_colonial_stance", "gp_pro_colonial_stance")
STANCE_MODIFIERS = ("gp_anti_colonial_policy_modifier", "gp_pro_colonial_policy_modifier")
SIDES = ("anti", "neutral", "pro")


def _raw(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _read(path):
    return re.sub(r"#[^\n]*", "", _raw(path))


def _block(text, name, prefix=r"^\t*"):
    """The body of the first ``name = { ... }`` block."""
    m = re.search(prefix + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


def _gui_type(text, name):
    """The body of ``type <name> = <base> {``, a type in the file's types block."""
    m = re.search(rf"^\ttype {re.escape(name)} = \w+ \{{", text, re.M)
    if m is None:
        raise AssertionError(f"type {name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"type {name} is not closed")


def _value(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*(-?\d+(?:\.\d+)?)\b", text, re.M)
    if m is None:
        raise AssertionError(f"{name} is not a constant")
    return float(m.group(1))


def _loc():
    keys = {}
    for path in glob.glob(os.path.join(LOC_DIR, "*_l_english.yml")):
        for line in _raw(path).splitlines():
            m = re.match(r'^ ([\w.\-]+):\d* "(.*)"\s*$', line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


def _script_files():
    for sub in ("common", "events"):
        yield from glob.glob(os.path.join(REPO, sub, "**", "*.txt"), recursive=True)


class WritersTest(unittest.TestCase):
    """The setters are the only writers of the stance and its modifiers."""

    def test_only_the_setters_write_a_stance(self):
        allowed = {os.path.normpath(EFFECTS), os.path.normpath(_path("events", "te_debug_colonial_empire_events.txt"))}
        for path in _script_files():
            text = _read(path)
            for var in STANCE_VARS:
                with self.subTest(path=os.path.relpath(path, REPO), var=var):
                    writes = re.findall(rf"\bset_variable = (?:\{{ name = )?{var}\b", text)
                    if os.path.normpath(path) not in allowed:
                        self.assertFalse(writes, f"{var} set outside the stance setters")

    def test_only_the_setters_add_the_policy_modifiers(self):
        for path in _script_files():
            text = _read(path)
            for modifier in STANCE_MODIFIERS:
                adds = re.findall(rf"add_modifier = \{{\s*name = {modifier}\b([^}}]*)\}}", text)
                with self.subTest(path=os.path.relpath(path, REPO), modifier=modifier):
                    if os.path.normpath(path) != os.path.normpath(EFFECTS):
                        self.assertFalse(adds, f"{modifier} added outside the stance setters")
                    for rest in adds:
                        # held while the stance counts: never a duration
                        self.assertNotRegex(rest, r"\b(days|months|years)\b")

    def test_each_core_writes_its_modifiers_on_great_power_rank(self):
        effects = _read(EFFECTS)
        for side, mine, other in (("anti", "gp_anti_colonial_policy_modifier", "gp_pro_colonial_policy_modifier"),
                                  ("pro", "gp_pro_colonial_policy_modifier", "gp_anti_colonial_policy_modifier")):
            core = _block(effects, f"decol_stance_core_{side}")
            with self.subTest(side=side):
                self.assertIn("decol_stance_start_cooldown = yes", core)
                self.assertIn(f"remove_modifier = {other}", core)
                self.assertRegex(core, rf"country_rank >= rank_value:great_power\s*NOT = \{{ has_modifier = {mine} \}}"
                                       rf"\s*\}}\s*add_modifier = \{{ name = {mine} \}}")
        neutral = _block(effects, "decol_stance_core_neutral")
        for name in STANCE_MODIFIERS:
            self.assertIn(f"remove_modifier = {name}", neutral)
        self.assertIn("decol_stance_start_cooldown = yes", neutral)

    def test_each_take_is_its_core_with_a_tooltip(self):
        effects = _read(EFFECTS)
        for side in SIDES:
            take = _block(effects, f"decol_stance_take_{side}")
            with self.subTest(side=side):
                self.assertIn(f"custom_tooltip = decol_stance_take_{side}_tt", take)
                self.assertIn(f"decol_stance_core_{side} = yes", take)

    def test_the_refresh_follows_the_variables_and_the_rank(self):
        triggers = _read(TRIGGERS)
        for side, var in (("anti", "gp_anti_colonial_stance"), ("pro", "gp_pro_colonial_stance")):
            counts = _block(triggers, f"decol_stance_{side}_counts")
            self.assertIn(f"has_variable = {var}", counts)
            self.assertIn("country_rank >= rank_value:great_power", counts)
        refresh = _block(_read(EFFECTS), "decol_stance_refresh")
        for side, modifier in (("anti", "gp_anti_colonial_policy_modifier"), ("pro", "gp_pro_colonial_policy_modifier")):
            self.assertIn(f"decol_stance_{side}_counts = yes", refresh)
            self.assertIn(f"add_modifier = {{ name = {modifier} }}", refresh)
            self.assertIn(f"remove_modifier = {modifier}", refresh)


class SurfacesTest(unittest.TestCase):
    """The Colonial Question, the UN vote, the buttons, the monthly pass and a
    revolution's repair all go through the setters."""

    def test_the_colonial_question_calls_the_takes(self):
        event = _block(_read(EVENTS), "decolonization_events.14", prefix=r"^")
        self.assertIn("decol_stance_question_due = yes", _block(event, "trigger"))
        self.assertIn("set_variable = decol_stance_asked", _block(event, "immediate"))
        options = re.findall(r"\boption = \{", event)
        self.assertEqual(len(options), 3)
        for side in SIDES:
            self.assertEqual(event.count(f"decol_stance_take_{side} = yes"), 1, side)
        for var in STANCE_VARS:
            self.assertNotIn(var, event, "the event writes no stance itself")
        # Both sides cost influence: shown greyed without it, the AI held to
        # its start line; neutral is free, so it is the default.
        self.assertEqual(event.count("trigger = { decol_stance_affordable = yes }"), 2)
        self.assertEqual(event.count("show_as_unavailable = { always = yes }"), 2)
        self.assertEqual(event.count("trigger = { NOT = { decol_stance_ai_can_hold = yes } }"), 2)
        neutral = event[event.index("name = decolonization_events.14.b"):]
        self.assertIn("default_option = yes", neutral[:200])
        self.assertEqual(event.count("default_option = yes"), 1)

    def test_a_player_is_asked_once(self):
        due = _block(_read(TRIGGERS), "decol_stance_question_due")
        self.assertIn("is_ai = yes", due)
        self.assertIn("NOT = { has_variable = decol_stance_asked }", due)
        pool = _read(ON_ACTIONS)
        entry = pool[:pool.index("trigger_event = { id = decolonization_events.14 }")]
        self.assertIn("decol_stance_question_due = yes", entry[-600:])

    def test_the_un_vote_takes_the_core(self):
        text = _read(UN_VOTE)
        self.assertRegex(text, r"custom_tooltip = \{\s*text = decol_stance_un_vote_tt\s*decol_stance_core_anti = yes\s*\}")

    def test_the_monthly_pass_and_the_repair(self):
        pulse = _block(_read(ON_ACTIONS), "decolonization_events_on_action", prefix=r"^")
        self.assertIn("decol_stance_monthly = yes", pulse)
        # every player, tab open or not: National Info shows another country's
        # Colonial Powers to a player without Decolonization
        self.assertRegex(pulse, r"is_player = yes\s*has_game_rule = decolonization_enabled"
                                r"\s*\}\s*decol_world_refresh_display = yes")
        monthly = _block(_read(EFFECTS), "decol_stance_monthly")
        self.assertRegex(monthly, r"is_ai = yes\s*decol_stance_paid = yes\s*influence < 0\s*\}\s*decol_stance_core_neutral = yes")
        self.assertIn("decol_stance_refresh = yes", monthly)
        self.assertIn("decol_stance_refresh = yes", _block(_read(DECOL), "decol_repair_after_civil_war"))

    def test_the_buttons_op_table(self):
        sgui = _block(_read(CE_SGUIS), "colonial_empire_stance_sgui")
        self.assertIn("ai_is_valid = { always = no }", sgui)
        self.assertIn("is_shown = { always = yes }", sgui)
        for op, side in enumerate(SIDES):
            with self.subTest(op=op):
                self.assertRegex(sgui, rf"scope:op = {op} \}}\s*decol_stance_possible_{side} = yes")
                self.assertRegex(sgui, rf"scope:op = {op} \}}\s*decol_stance_take_{side} = yes")
        self.assertIn("decol_world_refresh_display = yes", _block(sgui, "effect"))
        gui = _raw(GUI)
        stance = _gui_type(gui, "te_ce_sec_stance")
        for op, side in enumerate(SIDES):
            self.assertEqual(stance.count(f"MakeScopeValue( '(CFixedPoint){op}' )"), 4, side)
            self.assertIn(f'text = "je_colonial_empire_stance_btn_{side}"', stance)

    def test_the_gates(self):
        triggers = _read(TRIGGERS)
        for side in ("anti", "pro"):
            gate = _block(triggers, f"decol_stance_possible_{side}")
            for line in ("decol_stance_current_tt", "decol_stance_not_cooling_down = yes",
                         "decol_stance_great_power_tt", "decol_stance_affordable = yes"):
                self.assertIn(line, gate, side)
        neutral = _block(triggers, "decol_stance_possible_neutral")
        self.assertIn("decol_stance_not_cooling_down = yes", neutral)
        self.assertNotIn("great_power", neutral)
        self.assertNotIn("influence", neutral)
        affordable = _block(triggers, "decol_stance_affordable")
        self.assertIn("decol_stance_paid = yes", affordable)
        self.assertIn("influence >= decol_stance_influence_cost", affordable)


class FiguresTest(unittest.TestCase):
    """Each figure is restated in the modifiers, the values and the tooltips."""

    @classmethod
    def setUpClass(cls):
        cls.values = _read(VALUES)
        cls.loc = _loc()

    def test_the_cost(self):
        cost = _value(self.values, "decol_stance_influence_cost")
        modifiers = _read(MODIFIERS)
        for name in STANCE_MODIFIERS:
            body = _block(modifiers, name, prefix=r"^")
            self.assertIn(f"country_influence_cost_add = {int(cost)}", body, name)
            self.assertNotIn("country_influence_add", body, name)
        for key in ("decol_stance_influence_tt", "decol_stance_un_vote_tt"):
            self.assertIn(f"#bold {int(cost)}#!", self.loc[key], key)

    def test_the_cooldown(self):
        months = int(_value(self.values, "decol_stance_cooldown_months"))
        for key in ("decol_stance_cooldown_tt", "decol_stance_un_vote_tt", "decol_stance_take_anti_tt",
                    "decol_stance_take_pro_tt", "decol_stance_take_neutral_tt"):
            self.assertIn(f"#bold {months}#! months", self.loc[key], key)
        # The Colonial Question's description says "every two years".
        self.assertEqual(months, 24)
        self.assertIn("every two years", self.loc["decolonization_events.14.d"])

    def test_the_status_codes_match_the_rows(self):
        """ce_power_status: 0 not begun, 1-5 the band, 6 secured, 7 collapsed,
        each with its own cell in the row."""
        status = _block(self.values, "ce_power_status")
        self.assertIn("value = colonial_empire_live_tier", status)
        self.assertRegex(status, r"has_variable = colonial_empire_completed \}\s*value = 6")
        self.assertRegex(status, r"has_variable = colonial_empire_collapsed_recently \}\s*value = 7")
        row = _gui_type(_raw(GUI), "te_ce_power_row")
        names = ["not_begun", "collapsing", "crumbling", "strained", "stable", "solidified", "secured", "collapsed"]
        for code, name in enumerate(names):
            with self.subTest(code=code):
                self.assertRegex(row, rf"'\(CFixedPoint\){code}' \)\]\"\s*text = \"je_colonial_empire_power_status_{name}\"")
                self.assertIn(f"je_colonial_empire_power_status_{name}_tt", self.loc)


class TabTest(unittest.TestCase):
    """The tab opens with the research; without the entry it shows the readout,
    whose sections read the player and never the entry."""

    def test_the_readout_gate_excludes_the_entry(self):
        sguis = _read(TAB_SGUIS)
        readout = _block(sguis, "te_window_colonial_empire_readout_sgui")
        self.assertIn("NOT = { has_journal_entry = je_colonial_empire }", readout)
        self.assertIn("ce_tab_unlocked = yes", readout)
        self.assertIn("has_journal_entry = je_colonial_empire", _block(sguis, "te_window_colonial_empire_tab_sgui"))
        self.assertIn("has_technology_researched = decolonization", _block(_read(TRIGGERS), "ce_tab_unlocked"))

    def test_the_body_shows_the_readout_before_the_gate(self):
        gui = _raw(GUI)
        body = _gui_type(gui, "te_ce_tab_body")
        start = body.index('blockoverride "tab_before_gate" {')
        before = body[start:body.index('blockoverride "tab_gate" {')]
        self.assertIn("te_window_colonial_empire_readout_sgui", before)
        self.assertIn("te_ce_readout = {}", before)
        readout = _gui_type(gui, "te_ce_readout")
        self.assertEqual(re.findall(r"^\t\t(te_ce_sec_\w+) = \{\}", readout, re.M), ["te_ce_sec_stance", "te_ce_sec_powers"])
        self.assertIn("te_window_colonial_empire_entry_unlock_sgui", readout)

    def test_the_outliving_sections_read_the_player_only(self):
        gui = _raw(GUI)
        loc = _loc()
        for name in ("te_ce_readout", "te_ce_sec_stance", "te_ce_sec_powers", "te_ce_stance_line",
                     "te_ce_power_head", "te_ce_power_row"):
            body = _gui_type(gui, name)
            with self.subTest(type=name):
                self.assertNotIn("JournalEntry", body)
                for key in re.findall(r'(?:text|tooltip) = "(\w+)"', body):
                    self.assertNotIn("JournalEntry", loc.get(key, ""), key)
                    self.assertIn(key, loc, f"{key} has no loc")


if __name__ == "__main__":
    unittest.main()
