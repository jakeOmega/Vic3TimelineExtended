"""Structural tests for covert warfare slice 7 (network-revealed intelligence).

A per-target network (slice 4) at strength >= covert_net_intel_tier_1_strength
reports its target's intelligence capacity and technology count; at >=
covert_net_intel_tier_2_strength it also counts the covert operations the
target runs against the operator. Display only.

These tests pin that the thresholds are compared in exactly one script value,
that the tier code follows every strength write (so a burn hides a report the
same day), that each report value is written only at the tier that reveals it,
that the operations count reads pacts from the target towards the operator,
that nothing in script reads the report back, and that the widget, loc and
console harness exist.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
WIDGET = ROOT / "gui/journal_entry_widgets/covert_operations_widget.gui"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_covert_events.txt"
LOC_DIR = ROOT / "localization/english"


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace. Safe because nested closing braces are always
    tab-indented (format_paradox_tabs.py)."""
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}\n") + 3]


def _type_block(gui, name):
    """One `type <name> = ... { ... }` inside the widget's types block: from the
    header to the next type or the end of the types block."""
    start = gui.index("type %s = " % name)
    rest = gui[start + 1:]
    nxt = re.search(r"\n\ttype \w+ = |\n}\n", rest)
    return gui[start: start + 1 + nxt.start()]


def _all_loc():
    return "".join(p.read_text(encoding="utf-8-sig") for p in LOC_DIR.rglob("*.yml"))


def _constant(name):
    m = re.search(r"(?m)^%s = ([\d.]+)$" % re.escape(name), _text(VALUES))
    return float(m.group(1))


def _strip_comments(body):
    return re.sub(r"#[^\n]*", "", body)


class ConstantTests(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(_constant("covert_net_intel_tier_1_strength"), 50)
        self.assertEqual(_constant("covert_net_intel_tier_2_strength"), 75)

    def test_thresholds_reachable_and_ordered(self):
        tier_1 = _constant("covert_net_intel_tier_1_strength")
        tier_2 = _constant("covert_net_intel_tier_2_strength")
        self.assertGreater(tier_1, 0)
        self.assertLess(tier_1, tier_2)
        self.assertLessEqual(tier_2, _constant("covert_net_max"))

    def test_thresholds_compared_in_one_place(self):
        # The 50 / 75 comparison lives only in covert_net_intel_tier_value;
        # every other reader (the widget) goes through the stored code.
        tier_value = _top_level_block(_text(VALUES), "covert_net_intel_tier_value = {")
        for name in ("covert_net_intel_tier_1_strength", "covert_net_intel_tier_2_strength"):
            self.assertIn("var:iw_net_strength >= %s" % name, tier_value)
            for path in ROOT.glob("common/**/*.txt"):
                body = _strip_comments(_text(path))
                uses = len(re.findall(r"\b%s\b" % name, body))
                if path == VALUES:
                    # The definition, plus the one comparison.
                    self.assertEqual(uses, 2, name)
                else:
                    self.assertEqual(uses, 0, "%s in %s" % (name, path.name))


class ScriptValueTests(unittest.TestCase):
    def test_tier_value_guards_missing_strength(self):
        block = _top_level_block(_text(VALUES), "covert_net_intel_tier_value = {")
        self.assertIn("value = 0", block)
        self.assertEqual(block.count("has_variable = iw_net_strength"), 2)
        self.assertEqual(block.count("add = 1"), 2)

    def test_own_tech_display(self):
        block = _top_level_block(_text(VALUES), "covert_techs_researched_display = {")
        self.assertIn("techs_researched", block)


class EffectTests(unittest.TestCase):
    def test_clamp_restates_tier_after_clamping(self):
        # A burn (covert_net_loss -> covert_net_clamp) must hide a tier the
        # network no longer earns the same day.
        block = _top_level_block(_text(EFFECTS), "covert_net_clamp = {")
        clamp = block.index("clamp_variable = { name = iw_net_strength")
        tier = block.index(
            "set_variable = { name = iw_net_intel_tier value = covert_net_intel_tier_value }"
        )
        self.assertLess(clamp, tier)

    def test_new_network_starts_at_tier_0(self):
        block = _top_level_block(_text(EFFECTS), "covert_net_create = {")
        self.assertIn("set_variable = { name = iw_net_intel_tier value = 0 }", block)

    def test_each_value_written_only_at_its_tier(self):
        block = _top_level_block(_text(EFFECTS), "covert_net_refresh_intel = {")
        tier_1 = block.index("var:iw_net_intel_tier >= 1")
        tier_2 = block.index("var:iw_net_intel_tier >= 2")
        ic = block.index("name = iw_net_intel_ic")
        techs = block.index("name = iw_net_intel_techs")
        ops = block.index("name = iw_net_intel_ops value = 0")
        self.assertLess(tier_1, ic)
        self.assertLess(ic, tier_2)
        self.assertLess(techs, tier_2)
        self.assertLess(tier_2, ops)
        self.assertIn("PREV.intelligence_capacity_total", block)
        self.assertIn("PREV.techs_researched", block)

    def test_tier_read_on_the_network_itself(self):
        # Never through a scope:<container>.var: chain (file rule).
        block = _top_level_block(_text(EFFECTS), "covert_net_refresh_intel = {")
        self.assertNotRegex(block, r"scope:iw_net_intel_net\.var:")
        self.assertEqual(block.count("has_variable = iw_net_intel_tier"), 2)

    def test_ops_count_reads_target_to_operator_pacts(self):
        block = _top_level_block(_text(EFFECTS), "covert_net_refresh_intel = {")
        loop = block[block.index("every_scope_diplomatic_pact = {"):]
        limit = loop[: loop.index("scope:iw_net_intel_net = { change_variable")]
        self.assertIn("is_covert_operation_pact = yes", limit)
        self.assertIn("first_country = scope:iw_net_intel_tgt", limit)
        self.assertIn("second_country = { this = scope:iw_net_operator }", limit)
        # Accumulated, the shape slice 4 chose over any_* count >= N.
        self.assertIn("change_variable = { name = iw_net_intel_ops add = 1 }", loop)
        self.assertNotRegex(block, r"count\s*>=")

    def test_refresh_skips_dead_targets(self):
        block = _top_level_block(_text(EFFECTS), "covert_net_refresh_intel = {")
        self.assertEqual(block.count("is_country_alive = yes"), 2)
        self.assertEqual(block.count("var:iw_target ?= {"), 2)

    def test_tick_refreshes_after_the_strength_write(self):
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        tick = block[block.index("# ---- 3. Tick ----"): block.index("# ---- 4. Reap ----")]
        refresh = tick.index("covert_net_refresh_intel = yes")
        self.assertLess(tick.index("covert_net_gain = { AMOUNT = covert_net_tick_gain }"), refresh)
        self.assertLess(tick.index("covert_net_loss = { AMOUNT = covert_net_decay_base }"), refresh)

    def test_refresh_only_called_from_the_pass_and_the_harness(self):
        # It relies on saved scopes, so it must stay off every path the engine
        # walks to render tooltips (the steppers' covert_refresh_funding_state,
        # covert_warfare.1's after).
        callers = {}
        for path in list(ROOT.glob("common/**/*.txt")) + list(ROOT.glob("events/*.txt")):
            body = _strip_comments(_text(path))
            count = body.count("covert_net_refresh_intel = yes")
            if count:
                callers[path.name] = count
        self.assertEqual(
            callers,
            {"covert_warfare_effects.txt": 1, "te_debug_covert_effects.txt": 2},
        )
        effects = _text(EFFECTS)
        for name in ("covert_ops_sync_all = {", "covert_refresh_funding_state = {", "covert_op_burn = {"):
            self.assertNotIn("covert_net_refresh_intel", _top_level_block(effects, name))

    def test_report_is_display_only(self):
        # Nothing in script reads the report back: it is for the widget.
        for path in list(ROOT.glob("common/**/*.txt")) + list(ROOT.glob("events/*.txt")):
            body = _strip_comments(_text(path))
            self.assertNotRegex(body, r"var:iw_net_intel_(ic|techs|ops)\b", path.name)


INTEL_LINES = (
    ("je_iw_net_row_intel_none", ("0",)),
    ("je_iw_net_row_intel_service", ("1", "2")),
    ("je_iw_net_row_intel_ops_locked", ("1",)),
    ("je_iw_net_row_intel_ops", ("2",)),
)

INTEL_LOC_KEYS = (
    "je_iw_net_row_intel_none",
    "je_iw_net_row_intel_service",
    "je_iw_net_row_intel_service_tooltip",
    "je_iw_net_row_intel_ops_locked",
    "je_iw_net_row_intel_ops",
    "je_iw_net_row_intel_ops_tooltip",
)


class WidgetTests(unittest.TestCase):
    def _row(self):
        return _type_block(_text(WIDGET), "widget_je_covert_network_row")

    def _line(self, key):
        row = self._row()
        end = row.index('text = "%s"' % key)
        start = row.rindex("widget_je_covert_operation_detail = {", 0, end)
        return row[start:row.index("}", end)]

    def test_lines_on_the_network_row_gated_on_the_code(self):
        for key, codes in INTEL_LINES:
            line = self._line(key)
            self.assertIn("ScriptContainer.HasVariable('iw_net_intel_tier')", line, key)
            for code in codes:
                self.assertIn(
                    "EqualTo_CFixedPoint(ScriptContainer.GetVariableValue('iw_net_intel_tier'), '(CFixedPoint)%s')"
                    % code,
                    line,
                    key,
                )
            for code in {"0", "1", "2"} - set(codes):
                self.assertNotIn("'(CFixedPoint)%s'" % code, line, key)

    def test_no_threshold_in_the_widget(self):
        row = self._row()
        self.assertNotIn("iw_net_intel_tier_1_strength", row)
        self.assertNotIn("iw_net_intel_tier_2_strength", row)
        self.assertNotRegex(row, r"GetVariableValue\('iw_net_strength'\)")

    def test_loc_keys_exist(self):
        loc = _all_loc()
        for key in INTEL_LOC_KEYS:
            self.assertRegex(loc, r"(?m)^ %s:0 " % re.escape(key))

    def test_loc_reads_the_report(self):
        loc = _all_loc()

        def value(key):
            return re.search(r"(?m)^ %s:0 (.*)$" % re.escape(key), loc).group(1)

        service = value("je_iw_net_row_intel_service")
        self.assertIn("GetVariableValue('iw_net_intel_ic')", service)
        self.assertIn("GetVariableValue('iw_net_intel_techs')", service)
        self.assertIn("ScriptValue('covert_techs_researched_display')", service)
        self.assertIn("GetVariableValue('iw_net_intel_ops')", value("je_iw_net_row_intel_ops"))
        # Thresholds are printed from the constants, never typed.
        self.assertIn("covert_net_intel_tier_1_strength", value("je_iw_net_row_intel_none"))
        self.assertIn("covert_net_intel_tier_2_strength", value("je_iw_net_row_intel_ops_locked"))
        header = value("je_iw_net_header_tooltip")
        self.assertIn("covert_net_intel_tier_1_strength", header)
        self.assertIn("covert_net_intel_tier_2_strength", header)


class HarnessTests(unittest.TestCase):
    def test_set_strength_refreshes_the_report(self):
        block = _top_level_block(_text(DEBUG_EFFECTS), "te_debug_covert_set_net_strength = {")
        self.assertIn("save_scope_as = iw_net_operator", block)
        self.assertLess(
            block.index("covert_net_clamp = yes"),
            block.index("covert_net_refresh_intel = yes"),
        )

    def test_hostile_cultivate(self):
        body = _text(DEBUG_EFFECTS)
        block = _top_level_block(body, "te_debug_covert_hostile_cultivate = {")
        # Our own cultivate-assets pact against the target must not count.
        self.assertIn("is_initiator = yes", block)
        self.assertIn("set_variable = { name = iw_funding_level value = 1 }", block)
        self.assertIn("TYPE = cultivate_assets", block)
        self.assertIn("add_to_temporary_list = te_debug_covert_hostiles", block)
        self.assertTrue(block.rstrip().endswith("te_debug_covert_refresh_net_intel = yes\n}"))
        refresh = _top_level_block(body, "te_debug_covert_refresh_net_intel = {")
        # Planting from the target's scope re-saves iw_net_operator.
        self.assertLess(
            refresh.index("save_scope_as = iw_net_operator"),
            refresh.index("covert_net_refresh_intel = yes"),
        )

    def test_event_and_loc(self):
        events = _text(DEBUG_EVENTS)
        loc = _all_loc()
        self.assertIn("te_debug_covert.5 = { # REVIEWED", events)
        for key in ("t", "d", "f", "a", "b", "c"):
            self.assertRegex(loc, r"(?m)^ te_debug_covert\.5\.%s:0 " % key)
        for opt in ("a", "b", "c"):
            self.assertIn("name = te_debug_covert.5.%s" % opt, events)


if __name__ == "__main__":
    unittest.main()
