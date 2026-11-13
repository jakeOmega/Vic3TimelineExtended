"""Tests for tooltip_walk_variable_audit (#918).

A button's or an option's tooltip walks its effect writing nothing, so a
variable the body sets and then reads is unset in the walk. The two Grand
Monument cases (`gm_com_drop` in the country refresh, `gm_rebuild_level` as a
switch's trigger) must flag; a guard, a click-only marker, `?=`, or other code
that keeps the name set must clear a read.
"""
from __future__ import annotations

import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout

import tooltip_walk_variable_audit as tva
from tooltip_walk_variable_audit import CHECK, audit, describe, main, render_report

SGUIS = "common/scripted_guis/x_sguis.txt"
EFFECTS = "common/scripted_effects/x_effects.txt"
TRIGGERS = "common/scripted_triggers/x_triggers.txt"
VALUES = "common/script_values/x_values.txt"
ON_ACTIONS = "common/on_actions/x_on_actions.txt"
EVENTS = "events/x_events.txt"
TAG = f"# REVIEWED 2026-11-12 ({CHECK}): "


LINKS = os.path.join("docs", "engine", "event_targets_summary.txt")


def _tree(root: str, files: dict[str, str]) -> str:
    # The scope-link catalog, so `owner` and `capital` read as scope changes.
    os.makedirs(os.path.join(root, os.path.dirname(LINKS)), exist_ok=True)
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), LINKS), os.path.join(root, LINKS))
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8-sig") as fh:
            fh.write(text)
    return root


def _run(files: dict[str, str], **kw):
    with tempfile.TemporaryDirectory() as mod:
        return audit(mod_path=_tree(mod, files), **kw)


def _flags(result):
    return [(f.file, f.line, f.variable) for f in result.flags]


def _sgui(effect: str, name: str = "x_sgui") -> str:
    return f"{name} = {{\n\tscope = country\n\teffect = {{\n{effect}\n\t}}\n}}\n"


def _pulse(effect: str) -> dict[str, str]:
    """An on-action that runs `effect` every month: code outside a tooltip."""
    return {ON_ACTIONS: f"on_monthly_pulse_country = {{\n\teffect = {{ {effect} = yes }}\n}}\n"}


class SetThenReadTests(unittest.TestCase):
    def test_a_limit_read_after_a_set_in_a_button_flags(self):
        r = _run({SGUIS: _sgui(
            "\t\tset_variable = { name = x_tmp value = 5 }\n"
            "\t\tif = { limit = { var:x_tmp > 3 } add_treasury = 1 }\n"
            "\t\tremove_variable = x_tmp")})
        self.assertEqual(_flags(r), [(SGUIS, 5, "var:x_tmp")])
        f = r.flags[0]
        self.assertEqual((f.kind, f.set_at, f.roots), ("limit", f"{SGUIS}:4", ["scripted GUI `x_sgui`"]))
        self.assertEqual(len(r.failing), 1)

    def test_a_read_with_no_earlier_set_is_not_ours(self):
        r = _run({SGUIS: _sgui("\t\tif = { limit = { var:x_tmp > 3 } add_treasury = 1 }\n"
                               "\t\tset_variable = { name = x_tmp value = 5 }")})
        self.assertEqual(r.flags, [])

    def test_value_and_switch_trigger_reads_flag(self):
        r = _run({SGUIS: _sgui(
            "\t\tset_variable = { name = x_a value = 2 }\n"
            "\t\tadd_treasury = var:x_a\n"
            "\t\tswitch = {\n\t\t\ttrigger = var:x_a\n\t\t\t1 = { add_treasury = 1 }\n\t\t}")})
        self.assertEqual([(f.line, f.kind) for f in r.flags], [(5, "value"), (7, "switch trigger")])

    def test_a_question_equals_read_logs_nothing(self):
        r = _run({SGUIS: _sgui("\t\tset_variable = { name = x_a value = 2 }\n"
                               "\t\tif = { limit = { var:x_a ?= 2 } add_treasury = 1 }")})
        self.assertEqual(r.flags, [])

    def test_global_variables_are_read_too(self):
        r = _run({SGUIS: _sgui("\t\tset_global_variable = { name = x_g value = 2 }\n"
                               "\t\tcapital = { add_modifier = { name = m multiplier = global_var:x_g } }")})
        self.assertEqual(_flags(r), [(SGUIS, 5, "global_var:x_g")])


class GuardTests(unittest.TestCase):
    def test_a_has_variable_guard_holds(self):
        r = _run({SGUIS: _sgui("\t\tset_variable = { name = x_a value = 2 }\n"
                               "\t\tif = { limit = { has_variable = x_a var:x_a > 1 } add_treasury = 1 }")})
        self.assertEqual(r.flags, [])

    def test_a_guard_after_the_read_does_not(self):
        r = _run({SGUIS: _sgui("\t\tset_variable = { name = x_a value = 2 }\n"
                               "\t\tif = { limit = { var:x_a > 1 has_variable = x_a } add_treasury = 1 }")})
        self.assertEqual(_flags(r), [(SGUIS, 5, "var:x_a")])

    def test_a_guard_beside_the_read_in_a_not_does_not(self):
        r = _run({SGUIS: _sgui(
            "\t\tset_variable = { name = x_a value = 2 }\n"
            "\t\tif = { limit = { NOT = { has_variable = x_a var:x_a > 1 } } add_treasury = 1 }")})
        self.assertEqual(_flags(r), [(SGUIS, 5, "var:x_a")])

    def test_the_click_only_marker_hides_the_whole_body(self):
        r = _run({SGUIS: _sgui(
            "\t\tset_variable = x_click\n"
            "\t\tif = {\n\t\t\tlimit = { has_variable = x_click }\n\t\t\tremove_variable = x_click\n"
            "\t\t\tset_variable = { name = x_a value = 2 }\n"
            "\t\t\tadd_treasury = var:x_a\n\t\t}")})
        self.assertEqual(r.flags, [])

    def test_a_flag_a_click_sets_and_leaves_does_not_hide_its_block(self):
        """Once an option has set `x_open`, the walk enters what it guards
        every frame: a guard on it is no fence for a scratch name inside."""
        r = _run({
            EVENTS: ("x.1 = {\n\ttype = country_event\n\toption = {\n\t\tname = x.1.a\n"
                     "\t\tset_variable = x_open\n\t}\n}\n"),
            SGUIS: _sgui("\t\tif = {\n\t\t\tlimit = { has_variable = x_open }\n"
                         "\t\t\tset_variable = { name = x_tmp value = 2 }\n"
                         "\t\t\tadd_treasury = var:x_tmp\n\t\t\tremove_variable = x_tmp\n\t\t}"),
        })
        self.assertEqual(_flags(r), [(SGUIS, 7, "var:x_tmp")])

    GUARDED_BODY = ("\t\tif = {\n\t\t\tlimit = { has_variable = x_mode }\n"
                    "\t\t\tset_variable = { name = x_tmp value = 5 }\n"
                    "\t\t\tif = { limit = { var:x_tmp > 3 } add_treasury = 1 }\n"
                    "\t\t\tremove_variable = x_tmp\n\t\t}")

    def test_a_flag_one_option_sets_and_another_removes_persists(self):
        """Option b's removal is not on option a's path: once a is picked the
        flag stays, so a guard on it is no fence."""
        r = _run({
            EVENTS: ("x.1 = {\n\ttype = country_event\n\toption = {\n\t\tname = x.1.a\n"
                     "\t\tset_variable = x_mode\n\t}\n\toption = {\n\t\tname = x.1.b\n"
                     "\t\tremove_variable = x_mode\n\t}\n}\n"),
            SGUIS: _sgui(self.GUARDED_BODY),
        })
        self.assertEqual(_flags(r), [(SGUIS, 7, "var:x_tmp")])

    def test_a_toggle_that_removes_in_its_else_persists(self):
        r = _run({
            EFFECTS: ("x_toggle = {\n\tif = {\n\t\tlimit = { NOT = { has_variable = x_mode } }\n"
                      "\t\tset_variable = x_mode\n\t}\n\telse = {\n\t\tremove_variable = x_mode\n\t}\n}\n"),
            SGUIS: _sgui("\t\tx_toggle = yes", "t_sgui") + _sgui(self.GUARDED_BODY),
        })
        self.assertEqual(_flags(r), [(SGUIS, 13, "var:x_tmp")])

    def test_an_or_that_passes_when_unset_guards_its_later_children(self):
        """`OR = { NOT = { has_variable = x } … var:x … }` reads x only when x
        is set (`nd_taboo_effective_ceiling_value`)."""
        r = _run({SGUIS: _sgui(
            "\t\tset_variable = { name = x_cap value = 5 }\n"
            "\t\tif = { limit = { OR = { NOT = { has_variable = x_cap } var:x_cap > 3 } } add_treasury = 1 }\n"
            "\t\tif = { limit = { OR = { var:x_cap > 3 NOT = { has_variable = x_cap } } } add_treasury = 1 }")})
        # The guard holds for what follows it in the OR, not for what precedes it.
        self.assertEqual(_flags(r), [(SGUIS, 6, "var:x_cap")])

    def test_a_template_no_caller_fills_does_not_unmake_a_marker(self):
        """`x_d$J$` with no caller fits `x_dbg_click` only by accident."""
        r = _run({
            EFFECTS: "x_band = {\n\tset_variable = { name = x_d$J$ value = 1 }\n}\n",
            SGUIS: _sgui("\t\tset_variable = x_dbg_click\n\t\tif = {\n\t\t\tlimit = { has_variable = x_dbg_click }\n"
                         "\t\t\tremove_variable = x_dbg_click\n"
                         "\t\t\tset_variable = { name = x_tmp value = 5 }\n\t\t\tadd_treasury = var:x_tmp\n\t\t}"),
        })
        self.assertEqual(r.flags, [])

    def test_a_guard_on_the_name_read_holds_even_when_it_persists(self):
        r = _run({SGUIS: _sgui("\t\tset_variable = { name = x_level value = 2 }\n"
                               "\t\tif = { limit = { has_variable = x_level var:x_level > 1 } add_treasury = 1 }\n"
                               "\t\tif = { limit = { has_variable = x_level } add_treasury = var:x_level }")})
        self.assertEqual(r.flags, [])

    def test_a_guard_in_a_scripted_trigger_holds_for_the_block(self):
        r = _run({
            SGUIS: _sgui("\t\tset_variable = { name = x_level value = 2 }\n"
                         "\t\tif = { limit = { x_has_level = yes } add_treasury = var:x_level }"),
            TRIGGERS: "x_has_level = {\n\thas_variable = x_level\n}\n",
        })
        self.assertEqual(r.flags, [])

    def test_the_else_of_a_marker_is_walked(self):
        r = _run({SGUIS: _sgui(
            "\t\tset_variable = { name = x_a value = 2 }\n"
            "\t\tif = { limit = { has_variable = x_click } add_treasury = 1 }\n"
            "\t\telse = { add_treasury = var:x_a }")})
        self.assertEqual(_flags(r), [(SGUIS, 6, "var:x_a")])

    def test_an_iterator_limit_guards_its_body(self):
        r = _run({SGUIS: _sgui(
            "\t\tset_variable = { name = x_a value = 2 }\n"
            "\t\tevery_scope_state = {\n\t\t\tlimit = { root = { has_variable = x_a } }\n"
            "\t\t\tadd_modifier = { name = m multiplier = root.var:x_a }\n\t\t}")})
        self.assertEqual(r.flags, [])

    def test_a_set_in_one_branch_is_not_earlier_for_its_sibling(self):
        r = _run({SGUIS: _sgui(
            "\t\tif = { limit = { is_at_war = yes } set_variable = { name = x_a value = 2 } }\n"
            "\t\telse = { add_treasury = var:x_a }\n"
            "\t\tadd_treasury = var:x_a")})
        # The read after the chain may follow the `if` branch's set.
        self.assertEqual([f.line for f in r.flags], [6])

    def test_an_ai_only_branch_is_not_walked(self):
        r = _run({SGUIS: _sgui("\t\tset_variable = { name = x_a value = 2 }\n"
                               "\t\tif = { limit = { is_ai = yes } add_treasury = var:x_a }")})
        self.assertEqual(r.flags, [])

    def test_a_scope_saved_in_a_created_container_does_not_exist(self):
        r = _run({SGUIS: _sgui(
            "\t\tset_global_variable = { name = x_seq value = 1 }\n"
            "\t\tcreate_container = { tags = { t } save_scope_as = x_box }\n"
            "\t\tif = { limit = { exists = scope:x_box } scope:x_box = { set_variable = { name = s value = global_var:x_seq } } }")})
        self.assertEqual(r.flags, [])


class ScopeTests(unittest.TestCase):
    def test_a_read_on_the_scope_written_flags(self):
        r = _run({SGUIS: _sgui("\t\towner = { set_variable = { name = x_a value = 2 } }\n"
                               "\t\tadd_treasury = owner.var:x_a")})
        self.assertEqual(_flags(r), [(SGUIS, 5, "var:x_a")])

    def test_a_read_on_another_scope_does_not(self):
        r = _run({SGUIS: _sgui("\t\towner = { set_variable = { name = x_a value = 2 } }\n"
                               "\t\tadd_treasury = var:x_a")})
        self.assertEqual(r.flags, [])

    def test_prev_and_saved_scopes_resolve(self):
        r = _run({SGUIS: _sgui(
            "\t\tsave_scope_as = x_me\n"
            "\t\tset_variable = { name = x_a value = 2 }\n"
            "\t\tcapital = { set_variable = { name = x_b value = prev.var:x_a } }\n"
            "\t\tcapital = { set_variable = { name = x_c value = scope:x_me.var:x_a } }")})
        self.assertEqual([(f.line, f.variable) for f in r.flags], [(6, "var:x_a"), (7, "var:x_a")])


class CallTests(unittest.TestCase):
    def test_a_read_in_a_called_effect_flags_with_its_chain(self):
        r = _run({
            SGUIS: _sgui("\t\tset_variable = { name = x_a value = 2 }\n\t\tx_use = yes"),
            EFFECTS: "x_use = {\n\tadd_treasury = var:x_a\n}\n",
        })
        self.assertEqual(_flags(r), [(EFFECTS, 2, "var:x_a")])
        self.assertEqual(r.flags[0].chain, ["x_use"])
        self.assertIn("through `x_use`", describe(r.flags[0]))

    def test_one_flag_lists_every_root_that_reaches_it(self):
        r = _run({
            SGUIS: _sgui("\t\tx_both = yes", "a_sgui") + _sgui("\t\tx_both = yes", "b_sgui"),
            EFFECTS: "x_both = {\n\tset_variable = { name = x_a value = 2 }\n\tadd_treasury = var:x_a\n}\n",
        })
        self.assertEqual(len(r.flags), 1)
        self.assertEqual(r.flags[0].roots, ["scripted GUI `a_sgui`", "scripted GUI `b_sgui`"])

    def test_a_scripted_trigger_read_flags(self):
        r = _run({
            SGUIS: _sgui("\t\tset_variable = { name = x_a value = 2 }\n"
                         "\t\tif = { limit = { x_big = yes } add_treasury = 1 }"),
            TRIGGERS: "x_big = {\n\tvar:x_a > 1\n}\n",
        })
        self.assertEqual(_flags(r), [(TRIGGERS, 2, "var:x_a")])

    def test_a_script_value_read_is_reported_where_the_value_is_named(self):
        r = _run({
            SGUIS: _sgui("\t\tset_variable = { name = x_in value = 4 }\n"
                         "\t\tset_variable = { name = x_out value = x_root }"),
            VALUES: "x_root = {\n\tvalue = var:x_in\n\tmultiply = 0.5\n}\n",
        })
        self.assertEqual([(f.file, f.line, f.kind) for f in r.flags], [(SGUIS, 5, "value")])

    def test_rebuild_level_as_a_switch_trigger_argument(self):
        """The 2026-10-12 case: gm_state_rededicate set gm_rebuild_level and
        passed it to the 200-case switch as SPEC_LEVEL; the button's tooltip
        logged once per case. The flag sits on the call that passes it."""
        r = _run({
            SGUIS: _sgui("\t\tscope:gm_state = { gm_state_choose_rededicate = yes }", "gm_rededicate_sgui"),
            EFFECTS: (
                "gm_state_choose_rededicate = {\n\tcustom_tooltip = gm_rededicate_tt\n"
                "\thidden_effect = { gm_state_rededicate = yes }\n}\n"
                "gm_state_rededicate = {\n"
                "\tset_variable = { name = gm_rebuild_cost value = gm_state_rededicate_cost }\n"
                "\tset_variable = { name = gm_rebuild_level value = { value = gm_state_primary_levels divide = 2 } }\n"
                "\towner = { add_treasury = { value = prev.var:gm_rebuild_cost multiply = -1 } }\n"
                "\tte_construction_market_build_specified_level = {\n"
                "\t\tSPEC_TYPE = building_grand_monument\n"
                "\t\tSPEC_LEVEL = var:gm_rebuild_level\n\t}\n"
                "\tremove_variable = gm_rebuild_level\n\tremove_variable = gm_rebuild_cost\n}\n"
                "te_construction_market_build_specified_level = {\n\tswitch = {\n\t\ttrigger = $SPEC_LEVEL$\n"
                "\t\t1 = { create_building = { building = $SPEC_TYPE$ level = 1 } }\n"
                "\t\t2 = { create_building = { building = $SPEC_TYPE$ level = 2 } }\n\t}\n}\n"
            ),
            # The AI's monthly pass rededicates too, and removes both: still flagged.
            **_pulse("gm_state_rededicate"),
        })
        self.assertEqual([(f.file, f.line, f.variable, f.kind, f.via_argument) for f in r.flags], [
            (EFFECTS, 8, "var:gm_rebuild_cost", "value", False),
            (EFFECTS, 11, "var:gm_rebuild_level", "switch trigger", True),
        ])
        self.assertEqual(r.flags[1].chain, ["gm_state_choose_rededicate", "gm_state_rededicate",
                                            "te_construction_market_build_specified_level"])

    def test_rebuild_level_behind_the_click_marker_is_clean(self):
        r = _run({
            SGUIS: _sgui("\t\tgm_state_rededicate = yes", "gm_rededicate_sgui"),
            EFFECTS: (
                "gm_state_rededicate = {\n\tset_variable = gm_rededicate_click\n\tif = {\n"
                "\t\tlimit = { has_variable = gm_rededicate_click }\n\t\tremove_variable = gm_rededicate_click\n"
                "\t\tset_variable = { name = gm_rebuild_level value = 2 }\n"
                "\t\tx_build = { LEVEL = var:gm_rebuild_level }\n\t}\n}\n"
                "x_build = {\n\tswitch = {\n\t\ttrigger = $LEVEL$\n\t\t1 = { add_treasury = 1 }\n\t}\n}\n"
            ),
        })
        self.assertEqual(r.flags, [])


class OtherCodeTests(unittest.TestCase):
    """`gm_com_drop`: the refresh wrote and removed it in one pass, which the
    pulse runs too, so the pulse never keeps it set; `gm_grandeur`: the
    refresh writes it and leaves it, so the walk finds it."""

    REFRESH = (
        "gm_country_refresh = {\n"
        "\tset_variable = { name = gm_com_drop value = gm_com_fit_grandeur }\n"
        "\tif = { limit = { var:gm_com_drop > 0 } add_treasury = 1 }\n"
        "\tremove_variable = gm_com_drop\n"
        "\tset_variable = { name = gm_grandeur value = 3 }\n"
        "\tif = { limit = { var:gm_grandeur > 0 } add_treasury = 1 }\n"
        "}\n"
    )

    def test_com_drop_where_it_was_behind_the_open_commission(self):
        """Where gm_com_drop really sat: gm_com_check_progress, inside
        `has_variable = gm_com_open`, a flag only an event option sets
        (gm_com_accept). Open, the walk goes in, and the drop logs."""
        r = _run({
            SGUIS: _sgui("\t\thidden_effect = { gm_country_refresh = yes }", "gm_policy_culture_sgui"),
            EFFECTS: (
                "gm_country_refresh = {\n\tgm_com_check_progress = yes\n}\n"
                "gm_com_check_progress = {\n\tif = {\n\t\tlimit = { has_variable = gm_com_open }\n"
                "\t\tset_variable = { name = gm_com_drop value = gm_com_fit_grandeur }\n"
                "\t\tif = { limit = { var:gm_com_drop > 0 } add_treasury = 1 }\n"
                "\t\tremove_variable = gm_com_drop\n\t}\n}\n"
                "gm_com_accept = {\n\tset_variable = gm_com_open\n}\n"
            ),
            EVENTS: ("monument_events.21 = {\n\ttype = country_event\n\toption = {\n"
                     "\t\tname = monument_events.21.a\n\t\tgm_com_accept = yes\n\t}\n}\n"),
            **_pulse("gm_country_refresh"),
        })
        self.assertEqual(_flags(r), [(EFFECTS, 8, "var:gm_com_drop")])
        self.assertEqual(r.flags[0].chain, ["gm_country_refresh", "gm_com_check_progress"])

    def test_com_drop_flags_and_grandeur_does_not(self):
        r = _run({
            SGUIS: _sgui("\t\thidden_effect = { gm_country_refresh = yes }", "gm_policy_culture_sgui"),
            EFFECTS: self.REFRESH,
            **_pulse("gm_country_refresh"),
        })
        self.assertEqual(_flags(r), [(EFFECTS, 3, "var:gm_com_drop")])

    def test_without_the_pulse_grandeur_is_this_buttons_alone(self):
        r = _run({SGUIS: _sgui("\t\tgm_country_refresh = yes"), EFFECTS: self.REFRESH})
        self.assertEqual(_flags(r), [(EFFECTS, 3, "var:gm_com_drop"), (EFFECTS, 6, "var:gm_grandeur")])

    def test_a_write_another_button_makes_keeps_nothing(self):
        r = _run({SGUIS: _sgui("\t\tset_variable = { name = x_a value = 1 }", "a_sgui")
                  + _sgui("\t\tset_variable = { name = x_a value = 2 }\n\t\tadd_treasury = var:x_a", "b_sgui")})
        self.assertEqual(_flags(r), [(SGUIS, 11, "var:x_a")])

    def test_an_event_immediate_keeps_a_name_for_its_options(self):
        r = _run({EVENTS: (
            "x.1 = {\n\ttype = country_event\n"
            "\timmediate = { set_variable = { name = x_roll value = 2 } }\n"
            "\toption = {\n\t\tname = x.1.a\n\t\tset_variable = { name = x_roll value = 3 }\n"
            "\t\tadd_treasury = var:x_roll\n\t}\n"
            "\tafter = { remove_variable = x_roll }\n}\n")})
        self.assertEqual(r.flags, [])

    def test_a_helper_write_resolved_at_a_pulse_caller_keeps_it(self):
        r = _run({
            SGUIS: _sgui("\t\tx_set = { VAR = x_a }\n\t\tadd_treasury = var:x_a"),
            EFFECTS: "x_set = {\n\tset_variable = { name = $VAR$ value = 1 }\n}\n"
                     "x_monthly = {\n\tx_set = { VAR = x_a }\n}\n",
            **_pulse("x_monthly"),
        })
        self.assertEqual(r.flags, [])


class RootTests(unittest.TestCase):
    def test_an_option_is_a_root_and_its_trigger_is_not(self):
        r = _run({EVENTS: (
            "x.1 = {\n\ttype = country_event\n\toption = {\n\t\tname = x.1.a\n"
            "\t\tset_variable = { name = x_a value = 2 }\n"
            "\t\tai_chance = { base = 1 modifier = { add = var:x_a } }\n"
            "\t\tadd_treasury = var:x_a\n\t\tremove_variable = x_a\n\t}\n}\n")})
        self.assertEqual(_flags(r), [(EVENTS, 7, "var:x_a")])
        self.assertEqual(r.flags[0].roots, ["`x.1 option 1`"])

    def test_an_options_walk_goes_on_into_the_events_after(self):
        r = _run({EVENTS: (
            "x.1 = {\n\ttype = country_event\n\toption = {\n\t\tname = x.1.a\n"
            "\t\tset_variable = { name = x_a value = 2 }\n\t}\n"
            "\tafter = {\n\t\tadd_treasury = var:x_a\n\t\tremove_variable = x_a\n\t}\n}\n")})
        self.assertEqual(_flags(r), [(EVENTS, 8, "var:x_a")])

    def test_decisions_and_journal_buttons_are_roots(self):
        body = "\t\tset_variable = { name = x_a value = 2 }\n\t\tadd_treasury = var:x_a"
        r = _run({
            "common/decisions/x.txt": f"x_decision = {{\n\twhen_taken = {{\n{body}\n\t}}\n}}\n",
            "common/scripted_buttons/x.txt": f"x_button = {{\n\teffect = {{\n{body}\n\t}}\n}}\n",
        })
        self.assertEqual(sorted(f.roots[0] for f in r.flags), ["button `x_button`", "decision `x_decision`"])

    def test_an_events_immediate_is_not_a_root(self):
        r = _run({EVENTS: (
            "x.1 = {\n\ttype = country_event\n\timmediate = {\n"
            "\t\tset_variable = { name = x_a value = 2 }\n\t\tadd_treasury = var:x_a\n\t}\n}\n")})
        self.assertEqual(r.flags, [])

    def test_only_root_walks_one(self):
        files = {SGUIS: _sgui("\t\tset_variable = { name = x_a value = 2 }\n\t\tadd_treasury = var:x_a", "a_sgui")
                 + _sgui("\t\tadd_treasury = 1", "b_sgui")}
        self.assertEqual(_run(files, only_root="b_sgui").flags, [])
        self.assertEqual(len(_run(files, only_root="a_sgui").flags), 1)


class TagTests(unittest.TestCase):
    BODY = "\t\tset_variable = { name = x_a value = 2 }\n\t\tadd_treasury = var:x_a"

    def test_a_tag_on_the_read_line_suppresses(self):
        r = _run({SGUIS: _sgui(self.BODY + " " + TAG + "never shown")})
        self.assertEqual(len(r.flags), 1)
        self.assertEqual(r.flags[0].exemption["rationale"], "never shown")
        self.assertEqual(r.failing, [])
        self.assertIn("never shown", render_report(r))

    def test_a_tag_with_no_flag_is_stale(self):
        r = _run({SGUIS: _sgui("\t\tadd_treasury = 1 " + TAG + "old")})
        self.assertEqual([(t.file, t.line) for t in r.stale], [(SGUIS, 4)])
        self.assertEqual(len(r.failing), 1)
        self.assertIn("## Stale tags", render_report(r))

    def test_event_context_audit_leaves_our_tag_alone(self):
        import event_context_audit
        self.assertIn(CHECK, event_context_audit.FOREIGN_CHECKS)

    def test_another_checks_tag_is_not_ours(self):
        r = _run({SGUIS: _sgui(self.BODY + " # REVIEWED 2026-11-12 (variable_guard): x")})
        self.assertEqual((len(r.flags), len(r.failing), r.stale), (1, 1, []))


class CacheTests(unittest.TestCase):
    def test_a_second_run_reads_a_changed_file_again(self):
        with tempfile.TemporaryDirectory() as mod:
            _tree(mod, {SGUIS: _sgui("\t\tadd_treasury = 1")})
            self.assertEqual(audit(mod_path=mod).flags, [])
            path = os.path.join(mod, SGUIS)
            self.assertIn(path, tva._PARSE_CACHE)
            _tree(mod, {SGUIS: _sgui(TagTests.BODY)})
            st = os.stat(path)
            os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
            self.assertEqual(len(audit(mod_path=mod).flags), 1)


class CommandLineTests(unittest.TestCase):
    def test_strict_exits_one_on_an_unreviewed_flag_and_root_lists_it(self):
        with tempfile.TemporaryDirectory() as mod:
            _tree(mod, {SGUIS: _sgui(TagTests.BODY)})
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["--strict"], mod_path=mod), 1)
                self.assertEqual(main([], mod_path=mod), 0)
                main(["--root", "x_sgui"], mod_path=mod)
            self.assertIn(f"{SGUIS}:5 [UNREVIEWED]", out.getvalue())


if __name__ == "__main__":
    unittest.main()
