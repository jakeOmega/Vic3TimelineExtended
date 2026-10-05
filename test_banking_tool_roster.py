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
ALT_BUTTONS = ROOT / "common/scripted_buttons/banking_alt_economy_buttons.txt"
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


def _braced(body, start):
    """`body` from `start` through the brace that closes the first `{` after it."""
    depth = 0
    for i in range(body.index("{", start), len(body)):
        depth += {"{": 1, "}": -1}.get(body[i], 0)
        if depth == 0:
            return body[start: i + 1]
    raise AssertionError("unbalanced braces after %r" % body[start: start + 40])


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


# Market tools whose disable button has no hold gate: switching them on or off
# costs nothing, so the AI may lift them whenever a stronger tool wants the point.
UNGATED_DISABLES = {"cb_moral_suasion"}
# The same for the command and cooperative economies' tools: the three 1-point
# tools whose lift frees their point.
UNGATED_ALT_DISABLES = {"ce_coordination_protocol", "cw_solidarity_campaign", "cw_council_directive"}


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
                self.assertRegex(
                    block,
                    r"banking_strip_tool = \{ MODIFIER = %s\s+MARK = off_%s \}"
                    % (re.escape(_modifier(tool)), re.escape(tool)),
                )

    def test_law_strip_refunds_emergency_liquidity(self):
        # The program's money is lent to the banks, so a law that closes it
        # pays the manual Disable's refund too. The refund is paid from
        # on_law_activated, where ROOT is the law, so the value must read the
        # country in scope, not root.
        block = _top_level_block(_text(CLEANUP), "remove_banking_market_modifiers_effect = {")
        refund_at = block.index("add_treasury = emergency_liquidity_program_deactivation_refund")
        strip_at = block.index("MODIFIER = banking_emergency_liquidity_program ")
        self.assertLess(refund_at, strip_at)
        # Once per opening: one law change can run the bundle more than once
        # (nested on_law_activated), and has_modifier may not see the strip.
        guard = block[block.rfind("limit", 0, refund_at):refund_at]
        self.assertIn("NOT = { has_variable = banking_eliq_strip_refunded }", guard)
        self.assertIn("set_variable = banking_eliq_strip_refunded", block)
        opening = _top_level_block(_text(EFFECTS), "banking_effect_cb_emergency_liquidity_program = {")
        self.assertIn("remove_variable = banking_eliq_strip_refunded", opening)
        manual = _top_level_block(_text(EFFECTS), "banking_effect_cb_disable_emergency_liquidity_program = {")
        self.assertIn("add_treasury = emergency_liquidity_program_deactivation_refund", manual)
        value = _top_level_block(
            _text(ROOT / "common/script_values/extra_script_values.txt"),
            "emergency_liquidity_program_deactivation_refund = {")
        self.assertNotIn("root.", value)

    def test_law_strip_marks_each_tool_as_its_manual_disable_does(self):
        # A tool a law switches off (planning, cooperative or market) posts
        # the same off_* history marker as its manual Disable, so the chart
        # shows it ending (te_banking_economy_law_cleanup, #337 follow-up).
        manual = {}
        for m in re.finditer(r"(?ms)^banking_effect_\w+_disable_\w+ = \{\n(.*?)^\}", _text(EFFECTS)):
            mark = re.search(r"MARK = (off_\w+) \}", m.group(1))
            removed = re.search(r"remove_modifier = (\w+) \}", m.group(1))
            if mark and removed:
                manual[removed.group(1)] = mark.group(1)
        pairs = re.findall(
            r"banking_strip_tool = \{ MODIFIER = (\w+)\s+MARK = (\w+) \}", _text(CLEANUP))
        self.assertTrue(pairs)
        for modifier, mark in pairs:
            with self.subTest(modifier=modifier):
                self.assertEqual(manual.get(modifier), mark)

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

    def test_each_disable_waits_until_its_reason_is_gone(self):
        # The AI lifts a tool only once the conditions it was bought for have
        # changed: a cycle tool's disable ends its ai_chance by multiplying by 0
        # while banking_ai_hold_cb_<tool> holds, and an external tool's disable
        # scores only while banking_ai_core_cb_<tool> is false. A gate placed
        # before an `add` would let that add through, so it must come last.
        # Moral suasion is exempt: it costs nothing to switch on or off.
        buttons, triggers = _text(BUTTONS), _text(POSSIBLE)
        for tool in _tools():
            if tool in UNGATED_DISABLES:
                self.assertFalse(_has_top_level(triggers, "banking_ai_hold_" + tool))
                continue
            with self.subTest(tool=tool):
                disable = _top_level_block(buttons, "cb_disable_%s = {" % _suffix(tool))
                ai = _braced(disable, disable.index("ai_chance = {"))
                if re.search(r"limit = \{ banking_ai_core_%s = no \} add = " % tool, ai):
                    continue
                self._assert_gate_last(ai, "banking_ai_hold_" + tool, triggers)

    def test_each_alt_economy_disable_waits_until_its_reason_is_gone(self):
        # The command (ce_*) and cooperative (cw_*) tools follow the market
        # tools' rule, with their own exemptions.
        buttons, triggers = _text(ALT_BUTTONS), _text(POSSIBLE)
        disables = re.findall(r"(?m)^(c[ew])_disable_(\w+) = \{", buttons)
        self.assertGreaterEqual(len(disables), 16)
        for eco, name in disables:
            tool = "%s_%s" % (eco, name)
            with self.subTest(tool=tool):
                block = _top_level_block(buttons, "%s_disable_%s = {" % (eco, name))
                ai = _braced(block, block.index("ai_chance = {"))
                hold = "banking_ai_hold_" + tool
                if tool in UNGATED_ALT_DISABLES:
                    self.assertNotIn(hold, ai)
                    self.assertFalse(_has_top_level(triggers, hold))
                    continue
                self._assert_gate_last(ai, hold, triggers)

    def _assert_gate_last(self, ai, hold, triggers):
        gate = re.search(r"if = \{ limit = \{ %s = yes[^{}]*\} multiply = 0 \}" % hold, ai)
        self.assertIsNotNone(gate, "no %s gate" % hold)
        self.assertNotIn("add =", ai[gate.end():])
        self.assertTrue(_has_top_level(triggers, hold), "%s is not defined" % hold)

    def test_each_hold_gate_is_in_the_simulator(self):
        # banking_cycle_sim.ai_holds mirrors the banking_ai_hold_cb_* triggers,
        # keyed by the simulator's own tool names (TOOL_MODIFIER_NAMES).
        sim = _text(SIM)
        roster = sim[sim.index("TOOL_MODIFIER_NAMES = {"):]
        roster = roster[: roster.index("\n}")]
        holds = sim[sim.index("def ai_holds("):]
        holds = holds[: holds.index("\n    return h")]
        triggers = _text(POSSIBLE)
        for tool in _tools():
            if not _has_top_level(triggers, "banking_ai_hold_" + tool):
                continue
            with self.subTest(tool=tool):
                key = re.search(r'"(\w+)": "%s"' % re.escape(_modifier(tool)), roster)
                self.assertIsNotNone(key, "%s is not in TOOL_MODIFIER_NAMES" % _modifier(tool))
                name = key.group(1)
                # the four newer directed-credit sectors are set by one loop
                in_dc_loop = name in ("dc_heavy", "dc_agri", "dc_arms", "dc_elec")
                self.assertTrue(in_dc_loop or '"%s":' % name in holds, "ai_holds has no %s" % name)

    def test_no_toggle_farms_loyalists(self):
        # A tool that grants loyalists on one switch and costs nothing on the
        # other could be clicked back and forth for loyalists without limit
        # (cooperative mutual aid and dividend restraint, until 2026-10-05).
        # Each grant must be paid for by radicals on the opposite switch, or
        # sit behind a cooldown: `NOT = { has_variable = X }` around it, with
        # X set for a number of days in the same block.
        effects = _text(EFFECTS)
        blocks = dict(re.findall(r"(?ms)^(banking_effect_\w+) = \{\n(.*?)^\}", effects))
        granting = [n for n, b in blocks.items() if "add_loyalists" in b]
        self.assertTrue(granting)
        for name in granting:
            with self.subTest(effect=name):
                m = re.fullmatch(r"banking_effect_(c[bew])_(disable_)?(\w+)", name)
                self.assertIsNotNone(m, name)
                eco, off, tool = m.groups()
                other = "banking_effect_%s_%s%s" % (eco, "" if off else "disable_", tool)
                if "add_radicals" in blocks.get(other, ""):
                    continue
                body = blocks[name]
                guard = re.search(r"NOT = \{ has_variable = (\w+) \}", body)
                self.assertIsNotNone(guard, "%s grants loyalists with no cost or cooldown" % name)
                self.assertRegex(body, r"set_variable = \{ name = %s days = \d+ \}" % guard.group(1))
                self.assertLess(body.index(guard.group(0)), body.index("add_loyalists"))

    def test_each_modifier_is_in_the_simulator(self):
        sim = _text(SIM)
        roster = sim[sim.index("TOOL_MODIFIER_NAMES = {"):]
        roster = roster[: roster.index("\n}")]
        for tool in _tools():
            with self.subTest(tool=tool):
                self.assertIn('"%s"' % _modifier(tool), roster)


if __name__ == "__main__":
    unittest.main()
