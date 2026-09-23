"""Roster parity for the banking dashboard's market-economy tools.

A `cb_*` policy tool is registered in sixteen places across script, GUI, loc
and the balance simulator, and the engine says nothing when one is missing: a
tool left out of the law-change removal list survives a switch to a command
economy, one left out of the active-policy OR list shows "no active policies"
beside its own row, one left out of the simulator is never clicked in the
balance study. Everything here is derived from the journal entry's
`scripted_button = cb_*` lines, so a new tool is checked the moment its button
is registered, and fails until the rest of it is.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JE = ROOT / "common/journal_entries/je_banking.txt"
BUTTONS = ROOT / "common/scripted_buttons/timeline_extended_scripted_buttons.txt"
POSSIBLE = ROOT / "common/scripted_triggers/banking_policy_triggers.txt"
EFFECTS = ROOT / "common/scripted_effects/banking_policy_effects.txt"
MARKET_TRIGGERS = ROOT / "common/scripted_triggers/market_triggers.txt"
DASH_SGUIS = ROOT / "common/scripted_guis/banking_dashboard_scripted_gui.txt"
HISTORY_SGUIS = ROOT / "common/scripted_guis/te_history_scripted_gui.txt"
CLEANUP = ROOT / "common/scripted_effects/extra_effects.txt"
MODIFIERS = ROOT / "common/static_modifiers/extra_modifiers.txt"
WIDGET = ROOT / "gui/journal_entry_widgets/banking_dashboard_widget.gui"
SIM = ROOT / "scripts/analysis/banking_cycle_sim.py"
LOC_DIR = ROOT / "localization/english"


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace. Safe because nested closing braces are always
    tab-indented (format_paradox_tabs.py)."""
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}") + 2]


def _has_top_level(body, name):
    return re.search(r"(?m)^%s = \{" % re.escape(name), body) is not None


def _loc_keys():
    keys = set()
    for path in LOC_DIR.rglob("*.yml"):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"\s+([\w.]+):\d*\s*\"", line)
            if m:
                keys.add(m.group(1))
    return keys


def _tools():
    """The enable half of every market tool the journal entry registers."""
    names = re.findall(r"(?m)^\s*scripted_button = (cb_\w+)", _text(JE))
    return [n for n in names if not n.startswith("cb_disable_")]


def _suffix(tool):
    return tool[len("cb_"):]


def _modifier(tool):
    """The static modifier the tool's shared enable effect puts on the JE."""
    block = _top_level_block(_text(EFFECTS), "banking_effect_%s = {" % tool)
    m = re.search(r"add_modifier = \{\s*name = (\w+)", block)
    if m is None:
        raise AssertionError("banking_effect_%s adds no modifier" % tool)
    return m.group(1)


def _active_trigger(modifier):
    """The `banking_tool_*_active` trigger that asks whether `modifier` is on."""
    m = re.search(
        r"(?m)^(banking_tool_\w+_active)\s*= \{ je:je_banking_cycle \?= \{ has_modifier = %s \} \}"
        % re.escape(modifier),
        _text(MARKET_TRIGGERS),
    )
    if m is None:
        raise AssertionError("no banking_tool_*_active trigger reads %s" % modifier)
    return m.group(1)


class RosterTests(unittest.TestCase):
    def test_roster_is_not_empty(self):
        # Guards every per-tool test below from passing vacuously.
        self.assertGreaterEqual(len(_tools()), 10)

    def test_each_tool_has_its_disable_button_registered(self):
        je = _text(JE)
        for tool in _tools():
            with self.subTest(tool=tool):
                self.assertRegex(je, r"(?m)^\s*scripted_button = cb_disable_%s$" % _suffix(tool))

    def test_each_button_pair_is_defined(self):
        body = _text(BUTTONS)
        for tool in _tools():
            with self.subTest(tool=tool):
                self.assertTrue(_has_top_level(body, tool))
                self.assertTrue(_has_top_level(body, "cb_disable_" + _suffix(tool)))

    def test_each_button_calls_the_shared_helpers(self):
        body = _text(BUTTONS)
        for tool in _tools():
            with self.subTest(tool=tool):
                enable = _top_level_block(body, tool + " = {")
                self.assertIn("banking_possible_%s = yes" % tool, enable)
                self.assertIn("banking_effect_%s = yes" % tool, enable)
                self.assertIn("ai_chance", enable)
                disable = _top_level_block(body, "cb_disable_%s = {" % _suffix(tool))
                self.assertIn("banking_effect_cb_disable_%s = yes" % _suffix(tool), disable)
                self.assertIn("ai_chance", disable)

    def test_each_tool_has_shared_helpers(self):
        possible, effects = _text(POSSIBLE), _text(EFFECTS)
        for tool in _tools():
            with self.subTest(tool=tool):
                self.assertTrue(_has_top_level(possible, "banking_possible_" + tool))
                self.assertTrue(_has_top_level(effects, "banking_effect_" + tool))
                self.assertTrue(_has_top_level(effects, "banking_effect_cb_disable_" + _suffix(tool)))

    def test_each_tool_records_history_markers(self):
        effects = _text(EFFECTS)
        for tool in _tools():
            with self.subTest(tool=tool):
                on = _top_level_block(effects, "banking_effect_%s = {" % tool)
                off = _top_level_block(effects, "banking_effect_cb_disable_%s = {" % _suffix(tool))
                self.assertIn("MARK = on_%s }" % tool, on)
                self.assertIn("MARK = off_%s }" % tool, off)

    def test_each_marker_has_a_tooltip_branch(self):
        body = _text(HISTORY_SGUIS)
        for tool in _tools():
            with self.subTest(tool=tool):
                self.assertIn("has_variable = te_hist_mk_on_%s }" % tool, body)
                self.assertIn("has_variable = te_hist_mk_off_%s }" % tool, body)

    def test_each_tool_has_a_static_modifier_with_a_point_cost(self):
        body = _text(MODIFIERS)
        for tool in _tools():
            with self.subTest(tool=tool):
                block = _top_level_block(body, _modifier(tool) + " = {")
                self.assertRegex(block, r"country_banking_intervention_max_add = -\d")

    def test_each_modifier_is_removed_on_a_law_change(self):
        block = _top_level_block(_text(CLEANUP), "remove_banking_market_modifiers_effect = {")
        for tool in _tools():
            with self.subTest(tool=tool):
                self.assertIn("remove_modifier = %s\n" % _modifier(tool), block)

    def test_each_active_trigger_is_in_the_active_policy_list(self):
        block = _top_level_block(_text(DASH_SGUIS), "banking_dash_any_policy_active = {")
        for tool in _tools():
            with self.subTest(tool=tool):
                self.assertIn("%s = yes" % _active_trigger(_modifier(tool)), block)

    def test_each_tool_has_both_dashboard_handlers(self):
        body = _text(DASH_SGUIS)
        for tool in _tools():
            with self.subTest(tool=tool):
                self.assertTrue(_has_top_level(body, "banking_dash_enable_" + tool))
                self.assertTrue(_has_top_level(body, "banking_dash_disable_" + tool))

    def test_each_tool_has_an_active_row_and_an_available_row(self):
        gui = _text(WIDGET)
        for tool in _tools():
            with self.subTest(tool=tool):
                # Active Policies: the row is drawn while the tool is on.
                self.assertIn("GetScriptedGui('banking_dash_disable_%s').IsShown" % tool, gui)
                # Available Interventions: somewhere to switch it on.
                self.assertIn("datacontext = \"[GetScriptedGui('banking_dash_enable_%s')]\"" % tool, gui)

    def test_each_tool_has_its_loc(self):
        keys = _loc_keys()
        buttons = _text(BUTTONS)
        for tool in _tools():
            with self.subTest(tool=tool):
                for key in ("banking_dash_cost_" + tool, "banking_dash_tt_" + tool,
                            _modifier(tool), _modifier(tool) + "_desc"):
                    self.assertTrue(key in keys, "no loc key " + key)
                for name in (tool, "cb_disable_" + _suffix(tool)):
                    block = _top_level_block(buttons, name + " = {")
                    for field in ("name", "desc"):
                        key = re.search(r'%s = "(\w+)"' % field, block).group(1)
                        self.assertTrue(key in keys, "no loc key %s (%s.%s)" % (key, name, field))

    def test_each_modifier_is_in_the_simulator(self):
        sim = _text(SIM)
        roster = sim[sim.index("TOOL_MODIFIER_NAMES = {"):]
        roster = roster[: roster.index("\n}")]
        for tool in _tools():
            with self.subTest(tool=tool):
                self.assertIn('"%s"' % _modifier(tool), roster)


if __name__ == "__main__":
    unittest.main()
