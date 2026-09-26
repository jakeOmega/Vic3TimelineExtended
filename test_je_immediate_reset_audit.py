"""Unit tests for je_immediate_reset_audit.

The crux is telling a reset from a write that cannot lose anything. A write
in a journal entry's `immediate` (directly or through a scripted effect)
flags unless it only runs while its own variable is missing, only ever
writes `yes`, feeds the entry's progress bar, is a refresh some entry's pulse
runs every time, or sits behind another variable's absence (those three are
listed, not failing). A positive `has_variable` test is not a guard, and
neither is a multi-child `NOT`.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from je_immediate_reset_audit import (
    BAR,
    OTHER_GUARD,
    REFRESH,
    UNGUARDED,
    SourceFile,
    audit,
    evaluate,
    load_file,
    parse_text,
    render_report,
)

LINKS = {"owner", "capital", "heir"}


def _source(text: str, rel: str):
    nodes, comments = parse_text(text)
    return SourceFile(rel, nodes, comments)


def _run(je: str, effects: str = "", svs: str = ""):
    return evaluate(
        [_source(je, "common/journal_entries/je.txt")],
        [_source(effects, "common/scripted_effects/fx.txt")] if effects else [],
        [_source(svs, "common/script_values/sv.txt")] if svs else [],
        LINKS,
    )


def _flags(je: str, effects: str = "", svs: str = "", category: str | None = None):
    res = _run(je, effects, svs)
    return [f for f in res.flags if category is None or f.category == category]


def _names(flags):
    return [f.name for f in flags]


def _je(immediate: str, extra: str = "") -> str:
    return "je_x = {\n\timmediate = {\n" + immediate + "\t}\n" + extra + "}\n"


class DetectionTests(unittest.TestCase):
    def test_reproduces_banking_reset(self):
        # je_banking.txt before #465: the cycle state was reset on every
        # record, so an inherited panic came back as 50, "stable".
        flags = _flags(
            "je_banking_cycle = {\n"
            "\timmediate = {\n"
            "\t\tset_variable = { name = finance_cycle_value value = 50 } # 0..100\n"
            "\t\tset_variable = {\n"
            "\t\t\tname = bubble_pressure\n"
            "\t\t\tvalue = 0\n"
            "\t\t}\n"
            "\t\tscope:journal_entry = {\n"
            "\t\t\tset_bar_progress = { name = banking_cycle_value_bar value = 50 }\n"
            "\t\t}\n"
            "\t}\n"
            "\tcan_revolution_inherit = yes\n"
            "}\n"
        )
        self.assertEqual([(f.line, f.name, f.value, f.category) for f in flags], [
            (3, "finance_cycle_value", "50", UNGUARDED),
            (4, "bubble_pressure", "0", UNGUARDED),
        ])
        self.assertEqual(flags[0].je_setting, "can_revolution_inherit: yes; can_deactivate: unset (= no)")
        self.assertTrue(flags[0].inherits)

    def test_change_remove_and_list_clear_are_writes(self):
        flags = _flags(_je(
            "\t\tchange_variable = { name = c add = 1 }\n"
            "\t\tremove_variable = r\n"
            "\t\tclear_variable_list = l\n"
            "\t\tclamp_variable = { name = k max = 5 }\n"
        ))
        self.assertEqual([(f.key, f.name) for f in flags], [
            ("change_variable", "c"), ("remove_variable", "r"), ("clear_variable_list", "l"),
        ])

    def test_global_writes_need_a_global_guard(self):
        flags = _flags(_je(
            "\t\tset_global_variable = { name = g value = 1 }\n"
            "\t\tif = {\n"
            "\t\t\tlimit = { NOT = { has_global_variable = h } }\n"
            "\t\t\tset_global_variable = { name = h value = 1 }\n"
            "\t\t}\n"
            "\t\tif = {\n"
            "\t\t\tlimit = { NOT = { has_variable = k } }\n"
            "\t\t\tset_global_variable = { name = k value = 1 }\n"
            "\t\t}\n"
        ))
        # `has_variable = k` tests a scope variable, not the global k.
        self.assertEqual(_names(flags), ["g", "k"])

    def test_positive_has_variable_is_not_a_guard(self):
        flags = _flags(_je(
            "\t\tif = {\n"
            "\t\t\tlimit = { has_variable = marker }\n"
            "\t\t\tremove_variable = marker\n"
            "\t\t}\n"
        ))
        self.assertEqual(_names(flags), ["marker"])
        self.assertEqual(flags[0].category, UNGUARDED)
        self.assertIn("positive existence test", flags[0].detail)

    def test_multi_child_not_is_not_a_guard(self):
        flags = _flags(_je(
            "\t\tif = {\n"
            "\t\t\tlimit = { NOT = { has_variable = a has_variable = b } }\n"
            "\t\t\tset_variable = { name = a value = 0 }\n"
            "\t\t}\n"
        ))
        self.assertEqual([(f.name, f.category) for f in flags], [("a", UNGUARDED)])

    def test_timed_flag_set_rearms_its_timer(self):
        flags = _flags(_je("\t\tset_variable = { name = cooldown days = 30 }\n"))
        self.assertEqual(_names(flags), ["cooldown"])
        self.assertIn("timer", flags[0].detail)

    def test_immediate_all_involved_is_audited(self):
        flags = _flags(
            "je_x = {\n\timmediate_all_involved = {\n"
            "\t\tset_variable = { name = z value = 2 }\n\t}\n}\n"
        )
        self.assertEqual(_names(flags), ["z"])

    def test_other_blocks_are_not_immediate(self):
        self.assertEqual(_flags(
            "je_x = {\n"
            "\ton_monthly_pulse = { effect = { set_variable = { name = p value = 0 } } }\n"
            "\ton_complete = { set_variable = { name = q value = 0 } }\n"
            "}\n"
        ), [])


class GuardTests(unittest.TestCase):
    def test_not_has_variable_guards_the_same_variable(self):
        self.assertEqual(_flags(_je(
            "\t\tif = {\n"
            "\t\t\tlimit = { NOT = { has_variable = x } }\n"
            "\t\t\tset_variable = { name = x value = 0 }\n"
            "\t\t}\n"
        )), [])

    def test_guard_among_other_conditions_and_inside_and(self):
        self.assertEqual(_flags(_je(
            "\t\tif = {\n"
            "\t\t\tlimit = { is_ai = no AND = { NOT = { has_variable = x } } }\n"
            "\t\t\tif = { limit = { exists = capital } set_variable = { name = x value = 0 } }\n"
            "\t\t}\n"
        )), [])

    def test_nor_guards_each_variable(self):
        self.assertEqual(_flags(_je(
            "\t\tif = {\n"
            "\t\t\tlimit = { NOR = { has_variable = x has_variable = y } }\n"
            "\t\t\tset_variable = { name = x value = 0 }\n"
            "\t\t\tset_variable = { name = y value = 0 }\n"
            "\t\t}\n"
        )), [])

    def test_else_of_a_lone_positive_test_is_guarded(self):
        flags = _flags(_je(
            "\t\tif = {\n"
            "\t\t\tlimit = { has_variable = x }\n"
            "\t\t\tchange_variable = { name = x add = 0 }\n"
            "\t\t}\n"
            "\t\telse = {\n"
            "\t\t\tset_variable = { name = x value = 0 }\n"
            "\t\t}\n"
        ))
        # The `if` branch changes an existing x; the `else` creates a missing one.
        self.assertEqual([(f.line, f.key) for f in flags], [(5, "change_variable")])

    def test_else_of_a_compound_test_is_not_guarded(self):
        flags = _flags(_je(
            "\t\tif = { limit = { has_variable = x is_ai = no } }\n"
            "\t\telse = { set_variable = { name = x value = 0 } }\n"
        ))
        self.assertEqual(_names(flags), ["x"])

    def test_iterator_limit_is_a_guard(self):
        self.assertEqual(_flags(_je(
            "\t\tevery_scope_state = {\n"
            "\t\t\tlimit = { NOT = { has_variable = s } }\n"
            "\t\t\tset_variable = { name = s value = 0 }\n"
            "\t\t}\n"
        )), [])

    def test_guard_on_another_variable_is_a_warning(self):
        flags = _flags(_je(
            "\t\tif = {\n"
            "\t\t\tlimit = { NOT = { has_variable = ch_total } }\n"
            "\t\t\tset_variable = { name = ch_total value = 0 }\n"
            "\t\t\tset_variable = { name = ch_art value = 0 }\n"
            "\t\t}\n"
        ))
        self.assertEqual([(f.name, f.category) for f in flags], [("ch_art", OTHER_GUARD)])
        self.assertIn("`ch_total` is missing", flags[0].detail)

    def test_flag_sets_are_idempotent(self):
        self.assertEqual(_flags(_je(
            "\t\tset_variable = started\n"
            "\t\tset_variable = { name = active value = yes }\n"
            "\t\their ?= { set_variable = being_educated }\n"
        )), [])

    def test_non_effect_blocks_are_skipped(self):
        self.assertEqual(_flags(_je(
            "\t\tshow_as_tooltip = { set_variable = { name = a value = 1 } }\n"
            "\t\tif = { limit = { set_variable = { name = b value = 1 } } }\n"
            "\t\trandom_list = { 10 = { modifier = { set_variable = { name = c value = 1 } } } }\n"
            "\t\t# set_variable = { name = d value = 1 }\n"
            "\t\tcustom_tooltip = \"set_variable = { name = e value = 1 }\"\n"
        )), [])

    def test_control_flow_and_scopes_are_followed(self):
        flags = _flags(_je(
            "\t\trandom_list = {\n"
            "\t\t\t20 = { set_variable = { name = a value = 1 } }\n"
            "\t\t\t80 = { hidden_effect = { set_variable = { name = b value = 2 } } }\n"
            "\t\t}\n"
            "\t\tcustom_tooltip = { text = T capital = { set_variable = { name = c value = 3 } } }\n"
        ))
        self.assertEqual(_names(flags), ["a", "b", "c"])
        self.assertEqual(flags[2].scopes, ["capital"])


class ProgressBarTests(unittest.TestCase):
    def test_current_value_input_is_listed_not_failing(self):
        res = _run(
            "je_x = {\n"
            "\timmediate = {\n"
            "\t\tset_variable = { name = progress value = 0 }\n"
            "\t\tset_variable = { name = via_sv value = 0 }\n"
            "\t\tset_variable = { name = funding value = 1 }\n"
            "\t}\n"
            "\tcurrent_value = { value = root.var:progress add = my_sv }\n"
            "}\n",
            svs="my_sv = { value = 0 if = { limit = { has_variable = via_sv } add = inner_sv } }\n"
                "inner_sv = { value = var:via_sv }\n",
        )
        self.assertEqual([(f.name, f.category) for f in res.flags], [
            ("progress", BAR), ("via_sv", BAR), ("funding", UNGUARDED),
        ])
        self.assertEqual(_names(res.unreviewed), ["funding"])


class ScriptedEffectTests(unittest.TestCase):
    EFFECTS = (
        "reset_milestone = {\n"
        "\tset_variable = { name = sr_funding_$M$ value = 1 }\n"
        "\tinner_effect = yes\n"
        "}\n"
        "inner_effect = {\n"
        "\tif = {\n"
        "\t\tlimit = { NOT = { has_variable = kept } }\n"
        "\t\tset_variable = { name = kept value = 0 }\n"
        "\t}\n"
        "\tchange_variable = { name = tally add = 1 }\n"
        "\tinner_effect = yes\n"
        "}\n"
    )

    def test_descends_with_parameters_and_reports_the_chain(self):
        flags = _flags(_je("\t\treset_milestone = { M = orbital }\n"), self.EFFECTS)
        self.assertEqual([(f.file, f.line, f.name) for f in flags], [
            ("common/scripted_effects/fx.txt", 2, "sr_funding_orbital"),
            ("common/scripted_effects/fx.txt", 10, "tally"),
        ])
        self.assertEqual(len(flags[1].via), 2)
        self.assertIn("reset_milestone", flags[1].via[0])
        self.assertIn("je.txt:3", flags[1].via[0])

    def test_guard_around_the_call_covers_the_effect(self):
        self.assertEqual(_flags(_je(
            "\t\tif = {\n"
            "\t\t\tlimit = { NOT = { has_variable = tally } }\n"
            "\t\t\tinner_effect = yes\n"
            "\t\t}\n"
        ), self.EFFECTS), [])

    def test_effect_every_pulse_runs_is_a_refresh(self):
        effects = "refresh_display = { set_variable = { name = shown value = 3 } }\n"
        flags = _flags(_je(
            "\t\trefresh_display = yes\n",
            "\ton_monthly_pulse = { effect = { refresh_display = yes } }\n",
        ), effects)
        self.assertEqual([(f.name, f.category, f.refresh) for f in flags],
                         [("shown", REFRESH, "refresh_display")])

    def test_another_entrys_pulse_also_proves_a_refresh(self):
        effects = "status = { set_variable = { name = s_$M$ value = 1 } }\n"
        je = (
            "je_a = { immediate = { status = { M = b } } }\n"
            "je_b = { on_monthly_pulse = { effect = { status = { M = b } } } }\n"
        )
        self.assertEqual([f.category for f in _flags(je, effects)], [REFRESH])

    def test_conditional_or_differently_parameterised_pulse_call_is_not_a_refresh(self):
        effects = "status = { set_variable = { name = s_$M$ value = 1 } }\n"
        je = (
            "je_a = {\n"
            "\timmediate = { status = { M = a } status = { M = b } }\n"
            "\ton_monthly_pulse = { effect = {\n"
            "\t\tif = { limit = { is_ai = no } status = { M = a } }\n"
            "\t\tstatus = { M = c }\n"
            "\t} }\n"
            "}\n"
        )
        self.assertEqual([(f.name, f.category) for f in _flags(je, effects)],
                         [("s_a", UNGUARDED), ("s_b", UNGUARDED)])


class ExemptionTests(unittest.TestCase):
    def _exemptions(self, je: str, effects: str = ""):
        return {f.name: (f.exemption or {}).get("rationale") for f in _flags(je, effects)}

    def test_reviewed_on_any_line_of_the_write(self):
        got = self._exemptions(_je(
            "\t\tset_variable = { name = a value = 0 } # REVIEWED 2026-09-26: one line\n"
            "\t\tset_variable = {\n"
            "\t\t\tname = b\n"
            "\t\t\tvalue = 0 # REVIEWED 2026-09-26: inner line\n"
            "\t\t}\n"
            "\t\tset_variable = { name = c value = 0 }\n"
        ))
        self.assertEqual(got, {"a": "one line", "b": "inner line", "c": None})

    def test_reviewed_on_the_innermost_conditional_opener(self):
        got = self._exemptions(_je(
            "\t\tif = { # REVIEWED 2026-09-26: whole branch\n"
            "\t\t\tlimit = { has_variable = m }\n"
            "\t\t\tremove_variable = m\n"
            "\t\t\tif = {\n"
            "\t\t\t\tlimit = { is_ai = no }\n"
            "\t\t\t\tset_variable = { name = n value = 0 }\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "\t\trandom_list = { # REVIEWED 2026-09-26: re-roll\n"
            "\t\t\t50 = { set_variable = { name = r value = 1 } }\n"
            "\t\t}\n"
        ))
        # n's innermost `if` carries no comment; the outer one does not reach it.
        self.assertEqual(got, {"m": "whole branch", "n": None, "r": "re-roll"})

    def test_reviewed_on_an_iterator_opener_does_not_count(self):
        got = self._exemptions(_je(
            "\t\tevery_scope_state = { # REVIEWED 2026-09-26: iterator_limit_audit's\n"
            "\t\t\tset_variable = { name = s value = 0 }\n"
            "\t\t}\n"
        ))
        self.assertEqual(got, {"s": None})

    def test_reviewed_on_a_call_line_covers_the_effect(self):
        effects = (
            "outer = {\n"
            "\tinner = yes # REVIEWED 2026-09-26: caches only\n"
            "\tset_variable = { name = o value = 0 }\n"
            "}\n"
            "inner = { set_variable = { name = i value = 0 } }\n"
        )
        got = self._exemptions(_je("\t\touter = yes\n"), effects)
        self.assertEqual(got, {"i": "caches only", "o": None})
        got = self._exemptions(_je("\t\touter = yes # REVIEWED 2026-09-26: all of it\n"), effects)
        self.assertEqual(got, {"i": "caches only", "o": "all of it"})

    def test_malformed_reviewed_does_not_count(self):
        got = self._exemptions(_je(
            "\t\tset_variable = { name = a value = 0 } # REVIEWED: no date\n"
            "\t\tset_variable = { name = b value = 0 } # REVIEWED 2026-09-26 (je_reset): tagged\n"
        ))
        self.assertEqual(got, {"a": None, "b": None})


class EntryTests(unittest.TestCase):
    def test_inheritance_and_deactivation_settings(self):
        res = _run(
            "je_a = { immediate = { set_variable = { name = a value = 0 } } can_revolution_inherit = no can_deactivate = yes }\n"
            "je_b = { immediate = { set_variable = { name = b value = 0 } } transferable = yes }\n"
            "INJECT:je_vanilla = { immediate = { set_variable = { name = c value = 0 } } }\n"
        )
        got = {f.je: (f.inherits, f.je_setting) for f in res.flags}
        self.assertEqual(got["je_a"], (False, "can_revolution_inherit: no; can_deactivate: yes"))
        self.assertEqual(got["je_b"][0], False)
        self.assertIn("`transferable = yes` blocks it", got["je_b"][1])
        self.assertEqual(got["je_vanilla"][0], True)
        self.assertIn("a mod `INJECT:` of a vanilla entry", got["je_vanilla"][1])

    def test_recursive_effect_terminates(self):
        effects = "loop = { set_variable = { name = l value = 0 } loop = yes }\n"
        self.assertEqual(_names(_flags(_je("\t\tloop = yes\n"), effects)), ["l"])


class ParserTests(unittest.TestCase):
    def test_lines_strings_and_numeric_keys(self):
        nodes, comments = parse_text(
            "a = {\n"
            "\tb = \"x = { y }\" # c = {\n"
            "\t10 = { d >= 3 }\n"
            "}\n"
        )
        self.assertEqual(len(nodes), 1)
        a = nodes[0]
        self.assertEqual((a.key, a.line, a.end_line), ("a", 1, 4))
        self.assertEqual([(c.key, c.line) for c in a.children], [("b", 2), ("10", 3)])
        self.assertEqual(a.children[1].children[0].value, "3")
        self.assertIn("c = {", comments[2])


class AuditTests(unittest.TestCase):
    def test_audit_reads_the_three_directories_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            for sub in ("journal_entries", "scripted_effects", "script_values"):
                os.makedirs(os.path.join(tmp, "common", sub))
            with open(os.path.join(tmp, "common", "journal_entries", "je.txt"), "w", encoding="utf-8-sig") as fh:
                fh.write(
                    "je_q = {\n"
                    "\timmediate = {\n"
                    "\t\tsetup = yes\n"
                    "\t\tset_variable = { name = bar value = 0 }\n"
                    "\t}\n"
                    "\tcurrent_value = { value = bar_sv }\n"
                    "\tcan_deactivate = yes\n"
                    "}\n"
                )
            with open(os.path.join(tmp, "common", "scripted_effects", "fx.txt"), "w", encoding="utf-8") as fh:
                fh.write("setup = { set_variable = { name = k value = 9 } }\n")
            with open(os.path.join(tmp, "common", "script_values", "sv.txt"), "w", encoding="utf-8") as fh:
                fh.write("bar_sv = { value = var:bar }\n")
            result = audit(mod_path=tmp)
            self.assertEqual(result.files_audited, 1)
            self.assertEqual([(f.name, f.category) for f in result.flags],
                             [("k", UNGUARDED), ("bar", BAR)])
            report = render_report(result)
            self.assertIn("### `je_q` (`common/journal_entries/je.txt`)", report)
            self.assertIn("can_revolution_inherit: unset (= yes); can_deactivate: yes", report)
            self.assertIn("`set_variable` `k` = `9` at `common/scripted_effects/fx.txt:1`", report)
            self.assertIn("- unreviewed: 1", report)
            self.assertIn("- progress-bar inputs: 1", report)

    def test_load_file_missing(self):
        sf = load_file("/nonexistent/x.txt", "x.txt")
        self.assertEqual((sf.nodes, sf.comments), ([], {}))


if __name__ == "__main__":
    unittest.main()
