"""Structural tests for covert warfare slice 6: four new operation types.

The per-type plumbing (sync rows, tier table, detection branches, widget,
loc, icons) is pinned by test_covert_op_registry.py. This file pins what each
new operation does: its gates, its modifiers, regime change's coup push,
cultivate assets' network and Tradecraft hooks and its fixed priority, and
the console harness.

Run: python3 -m unittest test_covert_new_ops -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACTIONS = ROOT / "common/diplomatic_actions/covert_operations.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
NUKE_TRIGGERS = ROOT / "common/scripted_triggers/nuke_triggers.txt"
NUKE_CUSTOM_LOC = ROOT / "common/customizable_localization/nuclear_program_custom_loc.txt"
STATIC = ROOT / "common/static_modifiers/extra_modifiers.txt"
WIDGET = ROOT / "gui/journal_entry_widgets/covert_operations_widget.gui"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_covert_events.txt"
LOC_DIR = ROOT / "localization/english"


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry (see test_covert_op_registry)."""
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}\n") + 3]


def _loc():
    out = {}
    for path in sorted(LOC_DIR.rglob("*.yml")):
        if path.name.startswith("te_unused"):
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"^ ([A-Za-z0-9_.]+):\d* (.*)$", line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def _section(block, header):
    """The `header = { ... }` sub-block of an action, by brace counting."""
    start = block.index(header)
    depth = 0
    for i in range(start, len(block)):
        if block[i] == "{":
            depth += 1
        elif block[i] == "}":
            depth -= 1
            if depth == 0:
                return block[start: i + 1]
    raise AssertionError("unbalanced %s" % header)


def _requirements(block):
    """Every requirement_to_maintain body of an action, concatenated. The
    leading tab keeps "pact = {" from matching inside has_diplomatic_pact."""
    pact = _section(block, "\tpact = {")
    parts = []
    at = 0
    while True:
        at = pact.find("requirement_to_maintain = {", at)
        if at == -1:
            return "".join(parts)
        parts.append(_section(pact[at:], "requirement_to_maintain = {"))
        at += 1


class ConstantTests(unittest.TestCase):
    def test_slice_6_constants(self):
        body = _text(VALUES)
        for name, value in (
            ("covert_regime_change_coup_push", "5"),
            ("covert_net_cultivate_mult", "1.5"),
            ("covert_cultivate_ai_net_ceiling", "50"),
        ):
            self.assertRegex(body, r"(?m)^%s = %s$" % (name, re.escape(value)))

    def test_shared_gate_tooltips_exist(self):
        loc = _loc()
        for key in ("iw_requires_rivalry_tt", "iw_target_not_our_subject_tt",
                    "iw_severe_ops_need_tradecraft_tt"):
            self.assertIn(key, loc)
        self.assertIn("covert_tradecraft_tier_3_floor", loc["iw_severe_ops_need_tradecraft_tt"])


class RegimeChangeTests(unittest.TestCase):
    def setUp(self):
        self.block = _top_level_block(_text(ACTIONS), "covert_regime_change_action = {")

    def test_launch_gates(self):
        possible = _section(self.block, "possible = {")
        self.assertIn("has_diplomatic_pact = { who = scope:target_country type = rivalry }", possible)
        self.assertIn("NOT = { scope:target_country = { is_subject_of = ROOT } }", possible)
        self.assertIn("covert_tradecraft_unlocks_severe_ops = yes", possible)

    def test_severe_gate_is_launch_only(self):
        # Existing operations are never gated: a falling score must not end one.
        reqs = _requirements(self.block)
        self.assertNotIn("covert_tradecraft", reqs)
        self.assertIn("has_diplomatic_pact = { who = scope:target_country type = rivalry }", reqs)

    def test_ai_wants_a_hostile_rival(self):
        will = _section(self.block, "will_propose = {")
        self.assertIn("type = rivalry", will)
        self.assertIn("attitude = antagonistic", will)
        self.assertIn("attitude = domineering", will)

    def test_modifier_values(self):
        block = _top_level_block(_text(STATIC), "covert_regime_change = {")
        self.assertIn("country_coup_resistance_add = -1", block)
        self.assertIn("country_legitimacy_base_add = -5", block)
        self.assertIn("political_movement_radicalism_add = 0.05", block)

    def test_coup_push_is_fully_operational_null_safe_and_not_dlc_gated(self):
        block = _top_level_block(_text(EFFECTS), "covert_ops_apply_all_phase_effects = {")
        start = block.index("has_tag = iw_op_regime_change")
        branch = block[start: block.index("covert_refresh_priority_cost = yes", start)]
        self.assertIn("covert_op_is_fully_operational = yes", branch)
        self.assertIn("je:je_ip4_coup ?= {", branch)
        self.assertIn(
            "add_progress = { value = covert_regime_change_coup_push name = je_ip4_coup_progress_bar }",
            branch,
        )
        self.assertNotIn("has_dlc_feature", block)

    def test_script_only_coup_resistance_is_named_in_the_description(self):
        # country_coup_resistance_add is script_only: the modifier tooltip
        # never lists it, so the description has to.
        self.assertIn("coup", _loc()["covert_regime_change_desc"].lower())


class NuclearSabotageTests(unittest.TestCase):
    def setUp(self):
        self.block = _top_level_block(_text(ACTIONS), "covert_nuclear_sabotage_action = {")

    def test_proliferating_trigger(self):
        block = _top_level_block(_text(NUKE_TRIGGERS), "nuclear_program_is_proliferating = {")
        self.assertIn("has_variable = nuclear_weapon_program_progress", block)
        self.assertIn("has_variable = nuclear_weapons_program_funding", block)
        self.assertIn("var:nuclear_weapons_program_funding >= 1", block)
        self.assertIn("modifier:country_nuclear_program_pause_bool = yes", block)
        self.assertIn("modifier:country_nuclear_disarmament_bool = yes", block)

    def test_launch_gates(self):
        possible = _section(self.block, "possible = {")
        self.assertIn("scope:target_country = { nuclear_program_is_proliferating = yes }", possible)
        self.assertIn("covert_tradecraft_unlocks_severe_ops = yes", possible)

    def test_severe_gate_is_launch_only(self):
        reqs = _requirements(self.block)
        self.assertNotIn("covert_tradecraft", reqs)
        self.assertIn("nuclear_program_is_proliferating = yes", reqs)

    def test_ai_values_a_programme_near_completion(self):
        score = _section(self.block, "propose_score = {")
        self.assertIn("var:nuclear_weapon_program_progress >= 75", score)
        self.assertIn("has_variable = nuclear_weapon_program_progress", score)

    def test_nuclear_sabotage_never_stops_progress(self):
        # je_nuclear_program multiplies progress by (1 + mult); at the largest
        # phase x priority multiplier the operation must leave it positive.
        static = _top_level_block(_text(STATIC), "covert_nuclear_sabotage = {")
        mult = float(re.search(r"country_nuclear_program_progress_mult = (-?[\d.]+)", static).group(1))
        self.assertEqual(mult, -0.25)
        values = _text(VALUES)
        pri3 = float(re.search(r"(?m)^covert_op_priority_3_effect_mult = ([\d.]+)$", values).group(1))
        full = float(re.search(r"(?m)^covert_op_phase_full_mult = ([\d.]+)$", values).group(1))
        self.assertGreater(1 + mult * pri3 * full, 0)

    def test_rate_tooltip_does_not_credit_sabotage_to_aid(self):
        # nuclear_program_display_aid_bonus is the whole progress mult, which
        # now carries sabotage too: the aid-only line must not fire then.
        block = _top_level_block(_text(NUKE_CUSTOM_LOC), "nuclear_program_aid_note = {")
        self.assertLess(
            block.index("has_modifier = covert_nuclear_sabotage"),
            block.index("localization_key = nuclear_program_aid_note_active"),
        )
        loc = _loc()
        for key in ("nuclear_program_aid_note_sabotaged", "nuclear_program_sabotage_note"):
            self.assertIn("nuclear_program_display_aid_bonus", loc[key])


if __name__ == "__main__":
    unittest.main()
