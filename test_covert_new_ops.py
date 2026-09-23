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
        self.assertIn("nuclear_program_is_standing = yes", reqs)

    def test_pausing_funding_does_not_end_the_operation(self):
        # Funding 0 for one tick costs the target nothing; a maintain condition
        # that read funding would let it end a year-old operation for free.
        reqs = _requirements(self.block)
        self.assertIn("scope:target_country = { nuclear_program_is_standing = yes }", reqs)
        self.assertNotIn("nuclear_program_is_proliferating", reqs)
        standing = _top_level_block(_text(NUKE_TRIGGERS), "nuclear_program_is_standing = {")
        self.assertIn("has_variable = nuclear_weapon_program_progress", standing)
        self.assertIn("modifier:country_nuclear_disarmament_bool = yes", standing)
        self.assertNotIn("funding", standing)

    def test_monthly_progress_comment_names_both_sources(self):
        body = _text(ROOT / "common/script_values/extra_script_values.txt")
        i = body.index("\nnuclear_program_display_monthly_progress = {")
        self.assertIn("covert_nuclear_sabotage", body[body.rindex("\n\n", 0, i): i])

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


MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "moon_base",
              "mars_landing", "interstellar_probe", "solar_colonization")


class SpaceEspionageTests(unittest.TestCase):
    def setUp(self):
        self.block = _top_level_block(_text(ACTIONS), "covert_space_espionage_action = {")

    def test_ahead_in_space_covers_every_milestone(self):
        body = _text(TRIGGERS)
        block = _top_level_block(body, "covert_target_ahead_in_space = {")
        for m in MILESTONES:
            self.assertIn("covert_target_ahead_in_space_on = { TARGET = $TARGET$ MILESTONE = %s }" % m, block)
        helper = _top_level_block(body, "covert_target_ahead_in_space_on = {")
        self.assertIn("$TARGET$ = { has_variable = sr_completed_$MILESTONE$ }", helper)
        self.assertIn("NOT = { has_variable = sr_completed_$MILESTONE$ }", helper)

    def test_gates_use_the_space_gap(self):
        gate = "covert_target_ahead_in_space = { TARGET = scope:target_country }"
        self.assertIn(gate, _section(self.block, "possible = {"))
        self.assertIn(gate, _requirements(self.block))
        will = _section(self.block, "will_propose = {")
        self.assertIn(gate, will)
        self.assertIn("sr_is_pursuing_milestone = yes", will)

    def test_modifiers(self):
        static = _text(STATIC)
        own = _top_level_block(static, "covert_space_espionage = {")
        self.assertIn("country_space_race_progress_mult = 0.10", own)
        self.assertIn("country_space_race_risk_mult = -0.10", own)
        marker = _top_level_block(static, "covert_space_espionage_detected = {")
        self.assertIn("country_authority_add = -3", marker)

    def test_self_effect_from_the_strongest_operation(self):
        block = _top_level_block(_text(EFFECTS), "covert_ops_apply_all_phase_effects = {")
        self.assertIn("covert_op_apply_self_effect = { TYPE = space_espionage MODIFIER = covert_space_espionage }", block)


class CultivateAssetsTests(unittest.TestCase):
    def setUp(self):
        self.block = _top_level_block(_text(ACTIONS), "covert_cultivate_assets_action = {")

    def test_no_modifiers_of_its_own(self):
        self.assertNotIn("\ncovert_cultivate_assets = {", _text(STATIC))

    def test_gates(self):
        possible = _section(self.block, "possible = {")
        self.assertIn("NOT = { scope:target_country = { is_subject_of = ROOT } }", possible)
        self.assertNotIn("type = rivalry", possible)
        self.assertNotIn("covert_tradecraft", possible)
        self.assertIn("covert_action_valid_target = yes", _requirements(self.block))

    def test_ai_builds_thin_networks(self):
        will = _section(self.block, "will_propose = {")
        self.assertIn(
            "covert_net_weaker_than = { TARGET = scope:target_country STRENGTH = covert_cultivate_ai_net_ceiling }",
            will,
        )
        pred = _top_level_block(_text(TRIGGERS), "covert_net_weaker_than = {")
        self.assertIn("has_variable_list = iw_nets", pred)
        self.assertIn("var:iw_net_strength >= $STRENGTH$", pred)

    def test_cultivate_multiplier_is_guarded_and_zeroed(self):
        gain = _top_level_block(_text(VALUES), "covert_net_tick_gain = {")
        self.assertIn("has_variable = iw_net_cultivating", gain)
        self.assertIn("multiply = covert_net_cultivate_mult", gain)
        sync = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        count = sync[sync.index("# ---- 2. Count ----"): sync.index("# ---- 3. Tick ----")]
        self.assertIn("set_variable = { name = iw_net_cultivating value = 0 }", count)
        self.assertIn("has_tag = iw_op_cultivate_assets", count)
        self.assertIn("set_variable = { name = iw_net_cultivating value = 1 }", count)

    def test_tradecraft_counts_it_at_the_preparatory_rate(self):
        # The full-rate branch's limit must exclude it (comments may sit between).
        block = _top_level_block(_text(EFFECTS), "covert_tradecraft_monthly = {")
        self.assertRegex(
            block,
            r"covert_op_is_established = yes(?:\s*#[^\n]*)*\s*NOT = \{ has_tag = iw_op_cultivate_assets \}",
        )

    def test_cultivate_assets_is_pinned_at_priority_1(self):
        # The stepper and the AI both step through covert_possible_priority_up.
        # The pin speaks only on a cultivate-assets row: IsValidTooltip prints
        # every bare custom_tooltip with a tick or a cross, so an unconditional
        # line would appear on every other operation's stepper too.
        block = _top_level_block(_text(TRIGGERS), "covert_possible_priority_up = {")
        self.assertRegex(
            block,
            r"trigger_if = \{\s*limit = \{ scope:iw_op \?= \{ has_tag = iw_op_cultivate_assets \} \}\s*"
            r"custom_tooltip = \{\s*text = iw_priority_cultivate_fixed_tt\s*always = no",
        )
        gui = _text(WIDGET)
        stepper = gui[gui.index("type covert_op_priority_stepper = flowcontainer {"):]
        stepper = stepper[: stepper.index("textbox = {")]
        self.assertIn("Not( ScriptContainer.HasTag('iw_op_cultivate_assets') )", stepper)

    def test_its_row_says_what_it_does_instead_of_phase_and_priority(self):
        gui = _text(WIDGET)
        for key in ("je_iw_op_row_phase_prep", "je_iw_op_row_phase_est", "je_iw_op_row_phase_full",
                    "je_iw_op_row_priority_1", "je_iw_op_row_priority_2", "je_iw_op_row_priority_3"):
            line = gui[: gui.index('text = "%s"' % key)].rsplit("visible = ", 1)[1]
            self.assertIn("Not( ScriptContainer.HasTag('iw_op_cultivate_assets') )", line, key)
        self.assertIn(
            "visible = \"[ScriptContainer.HasTag('iw_op_cultivate_assets')]\"\n\t\t\ttext = \"je_iw_op_row_cultivate_detail\"",
            gui,
        )
        self.assertIn("covert_net_cultivate_mult", _loc()["je_iw_op_row_cultivate_detail"])


class DebugHarnessTests(unittest.TestCase):
    def test_seed_plants_all_four_new_codes(self):
        block = _top_level_block(_text(DEBUG_EFFECTS), "te_debug_covert_seed_new_ops = {")
        self.assertEqual({int(c) for c in re.findall(r"CODE = (\d+)", block)}, {9, 10, 11, 12})
        self.assertIn("type = rivalry", block)
        self.assertIn("nuclear_program_is_proliferating = yes", block)
        self.assertIn("covert_target_ahead_in_space = { TARGET = PREV }", block)

    def test_event_is_console_only_and_localised(self):
        body = _text(DEBUG_EVENTS)
        opener = re.search(r"(?m)^te_debug_covert\.4 = \{.*$", body).group(0)
        self.assertIn("REVIEWED", opener)
        ev = body[body.index("te_debug_covert.4 = {"):]
        self.assertIn("event_image", ev)
        loc = _loc()
        for suffix in ("t", "d", "f", "a", "b"):
            self.assertIn("te_debug_covert.4.%s" % suffix, loc)


if __name__ == "__main__":
    unittest.main()
