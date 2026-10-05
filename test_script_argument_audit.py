"""Unit tests for script_argument_audit (#732) and script_helper_index.

A call that passes an argument its scripted effect or trigger never names, or
leaves out a `$X$` the body names, fails the engine's per-call compile. The
two shapes #731 fixed (the Strategic Reserve steppers' unused SETTING, the tax
dispatcher's arguments to kinds 2 and 4 that named none) must flag, and the
dispatchers that resolve correctly must not.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

import event_context_audit
import script_argument_audit
from iterator_limit_audit import blank_comments_and_strings
from script_argument_audit import audit, describe, helper_callers, render_report
from script_helper_index import blank_comments, load_helpers, scan_definitions


def _tree(root: str, files: dict[str, str]) -> str:
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return root


def _run(files: dict[str, str], vanilla: dict[str, str] | None = None):
    with tempfile.TemporaryDirectory() as mod, tempfile.TemporaryDirectory() as van:
        _tree(mod, files)
        vgame = None
        if vanilla is not None:
            vgame = os.path.join(van, "game")
            _tree(vgame, vanilla)
        return audit(mod_path=mod, vanilla_game=vgame)


def _summary(result):
    return [(f.file, f.line, f.callee, f.unknown, f.missing, f.no_params_block, f.target_missing)
            for f in result.flags]


EFFECTS = "common/scripted_effects/e.txt"
TRIGGERS = "common/scripted_triggers/t.txt"
EVENTS = "events/x.txt"


class ScriptHelperIndexTests(unittest.TestCase):
    def test_blank_comments_matches_the_shared_blanker(self):
        text = 'a = "x # y" # c $Q$\nb = { c = "$P$" } # z\n"unterminated\nq = 1'
        keep, clean = blank_comments(text)
        self.assertEqual(clean, blank_comments_and_strings(text)[0])
        self.assertEqual(len(keep), len(text))
        self.assertIn('"$P$"', keep)
        self.assertNotIn("$Q$", keep)

    def test_scan_definitions(self):
        text = (
            "@cap = 5\n"
            "# commented = { $NOPE$ }\n"
            "plain = 200\n"
            "INJECT:injected = { x = 1 }\n"
            "helper = {\n"
            "\tif = { limit = { $COND$ = yes } }\n"
            '\tcustom_tooltip = "tt_$KEY$" # $NOT_A_PARAM$\n'
            '\tset_variable = { name = "a{b" value = $V$ }\n'
            "}\n"
            "after = { }\n"
        )
        defs = {d.name: d for d in scan_definitions(text, "f.txt", "scripted_effects", "mod")}
        self.assertEqual(sorted(defs), ["after", "helper", "injected", "plain"])
        self.assertEqual(defs["helper"].params, frozenset({"COND", "KEY", "V"}))
        self.assertEqual(defs["helper"].line, 5)
        self.assertEqual(defs["after"].line, 10)
        self.assertEqual(defs["plain"].params, frozenset())

    def test_mod_wins_over_vanilla_and_overridden_files_drop_out(self):
        with tempfile.TemporaryDirectory() as mod, tempfile.TemporaryDirectory() as van:
            _tree(mod, {
                "common/scripted_effects/00_shared.txt": "kept = { $A$ }\n",
                "common/scripted_triggers/m.txt": "both = { $MOD$ }\n",
            })
            _tree(van, {
                "common/scripted_effects/00_shared.txt": "dropped = { $X$ }\n",
                "common/scripted_triggers/v.txt": "both = { $VAN$ }\nvanilla_only = { $Y$ }\n",
            })
            index = load_helpers(mod, van)
        self.assertNotIn("dropped", index)
        self.assertEqual([d.params for d in index["both"]], [frozenset({"MOD"})])
        self.assertEqual(index["vanilla_only"][0].origin, "vanilla")


class DetectionTests(unittest.TestCase):
    def test_reproduces_strategic_reserve_unused_setting(self):
        # st_res_policy_step_up_base before #731.
        r = _run({EFFECTS: (
            "st_res_policy_step_up_base = {\n"
            "\tchange_variable = { name = st_res_$GOOD$_$SETTING$ add = $STEP$ }\n"
            "\tst_res_policy_set_by_hand_base = { GOOD = $GOOD$ SETTING = $SETTING$ }\n"
            "}\n"
            "st_res_policy_set_by_hand_base = {\n"
            "\tremove_variable = st_res_$GOOD$_preset\n"
            "}\n"
        )})
        self.assertEqual(_summary(r), [
            (EFFECTS, 3, "st_res_policy_set_by_hand_base", ["SETTING"], [], False, False),
        ])
        self.assertIn("passes SETTING, which the callee never names", describe(r.flags[0]))

    def test_reproduces_tax_dispatcher_kinds_without_parameters(self):
        # te_tax_obl_is_maintenance before #731: kinds 2 and 4 named neither
        # ARG nor TARGET, and only kinds 1, 2 and 4 are ever passed.
        r = _run({
            TRIGGERS: (
                "te_tax_obl_is_maintenance = {\n"
                "\tte_tax_obl_is_maintenance_$KIND$ = { ARG = $ARG$ TARGET = $TARGET$ }\n"
                "}\n"
                "te_tax_obl_is_maintenance_1 = { te_tax_level_$ARG$ >= $TARGET$ }\n"
                "te_tax_obl_is_maintenance_2 = { te_tax_rec_ok = yes }\n"
                "te_tax_obl_is_maintenance_3 = { te_tax_wages_$ARG$ = yes }\n"
                "te_tax_obl_is_maintenance_4 = { te_tax_surplus = yes }\n"
            ),
            EFFECTS: (
                "bill_a = { if = { limit = { te_tax_obl_is_maintenance = { KIND = 1 ARG = 1 TARGET = var:t } } } }\n"
                "bill_b = { if = { limit = { te_tax_obl_is_maintenance = { KIND = 2 ARG = 0 TARGET = var:t } } } }\n"
                "bill_c = { if = { limit = { te_tax_obl_is_maintenance = { KIND = 4 ARG = 0 TARGET = var:t } } } }\n"
            ),
        })
        self.assertEqual(_summary(r), [
            (TRIGGERS, 2, "te_tax_obl_is_maintenance_2", ["ARG", "TARGET"], [], True, False),
            (TRIGGERS, 2, "te_tax_obl_is_maintenance_4", ["ARG", "TARGET"], [], True, False),
        ])
        self.assertIn("names no `$X$`", describe(r.flags[0]))

    def test_missing_arguments(self):
        r = _run({
            TRIGGERS: "has_pact_with = { has_treaty = $TARGET$ }\n",
            EVENTS: (
                "x.1 = {\n"
                "\ttrigger = { has_pact_with = ROOT }\n"
                "\timmediate = { if = { limit = { has_pact_with = yes } } }\n"
                "\toption = { trigger = { has_pact_with = { } } }\n"
                "}\n"
            ),
        })
        self.assertEqual([(f.line, f.missing) for f in r.flags],
                         [(2, ["TARGET"]), (3, ["TARGET"]), (4, ["TARGET"])])

    def test_matching_calls_do_not_flag(self):
        r = _run({
            EFFECTS: "two = { set_variable = { name = $A$ value = $B$ } }\nnone = { add_prestige = 1 }\n",
            EVENTS: (
                "x.1 = {\n"
                "\timmediate = {\n"
                "\t\ttwo = {\n"
                "\t\t\tA = a\n"
                '\t\t\tB = "quoted"\n'
                "\t\t}\n"
                "\t\tnone = yes\n"
                "\t}\n"
                "}\n"
            ),
        })
        self.assertEqual(r.flags, [])
        self.assertEqual(r.calls_checked, 2)

    def test_multi_line_call_flags_its_opening_line(self):
        r = _run({
            EFFECTS: "one = { add = $A$ }\n",
            EVENTS: "x.1 = {\n\timmediate = {\n\t\tone = {\n\t\t\tA = 1\n\t\t\tB = 2\n\t\t}\n\t}\n}\n",
        })
        self.assertEqual([(f.line, f.unknown) for f in r.flags], [(3, ["B"])])

    def test_comments_are_neither_calls_nor_parameters(self):
        r = _run({
            EFFECTS: "one = {\n\t# was $OLD$\n\tadd = 1\n}\n",
            EVENTS: "x.1 = {\n\timmediate = {\n\t\t# one = { OLD = 1 }\n\t\tone = { OLD = 1 }\n\t}\n}\n",
        })
        self.assertEqual([(f.line, f.no_params_block) for f in r.flags], [(4, True)])

    def test_effect_and_trigger_of_one_name_pass_on_either_signature(self):
        r = _run({
            EFFECTS: "dual = { add = $A$ }\n",
            TRIGGERS: "dual = { always = yes }\n",
            EVENTS: "x.1 = {\n\ttrigger = { dual = yes }\n\timmediate = { dual = { A = 1 } }\n}\n",
        })
        self.assertEqual(r.flags, [])

    def test_vanilla_callees_only_with_game_files(self):
        files = {EVENTS: "x.1 = {\n\ttrigger = { has_treaty_alliance_with = ROOT }\n}\n"}
        vanilla = {"common/scripted_triggers/00_diplomacy_triggers.txt":
                   "has_treaty_alliance_with = { has_diplomatic_pact = { who = $TARGET$ } }\n"}
        self.assertEqual(_run(files).flags, [])
        r = _run(files, vanilla)
        self.assertTrue(r.vanilla_indexed)
        self.assertEqual([(f.callee, f.missing) for f in r.flags],
                         [("has_treaty_alliance_with", ["TARGET"])])


class DispatcherTests(unittest.TestCase):
    def test_chain_through_another_dispatcher_resolves(self):
        # The tax bill's te_tax_dr_relief_touch: KEY reaches it from literal
        # calls and through te_tax_dr_relief_$DIR$, so `te_tax_dr_$KEY$_touch`
        # expands to agrel and regrel only, never back to the dispatcher.
        r = _run({EFFECTS: (
            "cmd = { te_tax_dr_relief_$DIR$ = { KEY = $KEY$ } }\n"
            "te_tax_dr_relief_0 = { te_tax_dr_relief_touch = { KEY = $KEY$ } }\n"
            "te_tax_dr_relief_1 = { te_tax_dr_relief_touch = { KEY = $KEY$ } }\n"
            "te_tax_dr_relief_touch = { te_tax_dr_$KEY$_touch = yes }\n"
            "te_tax_dr_agrel_touch = { add = 1 }\n"
            "te_tax_dr_regrel_touch = { add = 1 }\n"
            "a = { cmd = { DIR = 0 KEY = agrel } }\n"
            "b = { cmd = { DIR = 1 KEY = regrel } }\n"
            "c = { te_tax_dr_relief_touch = { KEY = agrel } }\n"
        )})
        self.assertEqual(r.flags, [])
        callers = helper_callers(r, "te_tax_dr_agrel_touch")["callers"]
        self.assertEqual([c["call"] for c in callers], ["te_tax_dr_$KEY$_touch"])

    def test_literal_expansion_with_no_helper_flags(self):
        r = _run({TRIGGERS: (
            "is_kind = { is_kind_$KIND$ = yes }\n"
            "is_kind_1 = { always = yes }\n"
            "is_kind_2 = { always = no }\n"
            "user = { is_kind = { KIND = 1 } is_kind = { KIND = 5 } }\n"
        )})
        self.assertEqual(_summary(r), [(TRIGGERS, 1, "is_kind_5", [], [], False, True)])
        self.assertIn("no scripted effect or trigger has this name", describe(r.flags[0]))

    def test_unresolved_dispatcher_checks_every_pattern_match_but_itself(self):
        # KIND reaches `is_kind` as a saved scope here, so it can't be expanded.
        r = _run({TRIGGERS: (
            "is_kind = { is_kind_$KIND$ = { A = 1 } }\n"
            "is_kind_x = { always = $A$ }\n"
            "is_kind_y = { always = yes }\n"
            "user = { is_kind = { KIND = scope:k } }\n"
        )})
        self.assertEqual([(f.callee, f.no_params_block) for f in r.flags], [("is_kind_y", True)])

    def test_a_whole_parameter_scope_switch_is_not_flagged(self):
        # `$TARGET$ = { ... }` with TARGET a scope: no helper family to miss.
        r = _run({
            EFFECTS: "on_target = { $TARGET$ = { add_prestige = 1 } }\nadd_prestige_to = { add = $X$ }\n",
            EVENTS: (
                "x.1 = { immediate = { on_target = { TARGET = ROOT } } }\n"
                "x.2 = { immediate = { on_target = { TARGET = scope:other } } }\n"
            ),
        })
        self.assertEqual(r.flags, [])


class SuppressionTests(unittest.TestCase):
    FILES = {
        EFFECTS: "one = { add = $A$ }\n",
        EVENTS: (
            "x.1 = {\n"
            "\timmediate = {\n"
            "\t\tone = { A = 1 B = 2 } # REVIEWED 2026-10-05 (script_argument): B kept for symmetry\n"
            "\t\tone = { A = 1 C = 2 } # REVIEWED 2026-10-05: untagged, so not ours\n"
            "\t\tone = { A = 1 } # REVIEWED 2026-10-05 (script_argument): nothing to suppress\n"
            "\t\tvanilla_helper = { X = 1 } # REVIEWED 2026-10-05 (script_argument): vanilla callee\n"
            "\t}\n"
            "}\n"
        ),
    }

    def test_tagged_flag_is_exempt_and_untagged_is_not(self):
        r = _run(self.FILES)
        self.assertEqual([(f.line, bool(f.exemption)) for f in r.flags], [(3, True), (4, False)])
        self.assertEqual(r.flags[0].exemption["rationale"], "B kept for symmetry")

    def test_stale_tags_fail_and_unverifiable_ones_wait_for_vanilla(self):
        r = _run(self.FILES)
        self.assertEqual([t.line for t in r.stale_tags], [5])
        self.assertEqual(r.failing, 2)
        r = _run(self.FILES, {"common/scripted_effects/v.txt": "vanilla_helper = { add = 1 }\n"})
        self.assertEqual([t.line for t in r.stale_tags], [5])
        self.assertEqual([(f.line, f.callee, bool(f.exemption)) for f in r.flags if f.line == 6],
                         [(6, "vanilla_helper", True)])
        r = _run(self.FILES, {"common/scripted_effects/v.txt": "vanilla_helper = { add = $X$ }\n"})
        self.assertEqual([t.line for t in r.stale_tags], [5, 6])

    def test_event_context_audit_leaves_the_tag_alone(self):
        self.assertIn(script_argument_audit.CHECK, event_context_audit.FOREIGN_CHECKS)


class ReportTests(unittest.TestCase):
    def test_regenerate_writes_report_and_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            _tree(tmp, {
                EFFECTS: "one = { add = $A$ }\n",
                EVENTS: "x.1 = { immediate = { one = { A = 1 B = 2 } } }\n",
            })
            with mock.patch("path_constants.mod_path", tmp), \
                    mock.patch.object(script_argument_audit, "vanilla_game_dir", return_value=None):
                summary = script_argument_audit.regenerate()
            with open(os.path.join(tmp, "docs", "engine", "script_argument_report.md"), encoding="utf-8") as fh:
                report = fh.read()
        self.assertEqual(summary["unreviewed"], 1)
        self.assertFalse(summary["vanilla_indexed"])
        self.assertIn("### `events/x.txt`", report)
        self.assertIn("- line 1: `one`: passes B, which the callee never names", report)

    def test_report_carries_no_volatile_numbers(self):
        r = _run({EFFECTS: "one = { add = 1 }\n", EVENTS: "x.1 = { immediate = { one = yes } }\n"})
        report = render_report(r)
        self.assertIn("_None._", report)
        self.assertNotIn(str(r.calls_checked) + " call", report)
        self.assertNotIn("files", report.split("## Coverage")[1])

    def test_helper_callers_shape(self):
        r = _run({
            EFFECTS: "two = { add = $A$ sub = $B$ }\n",
            EVENTS: "x.1 = { immediate = { two = { A = 1 C = 2 } } }\n",
        })
        info = helper_callers(r, "two")
        self.assertEqual(info["params"], ["A", "B"])
        self.assertEqual(info["callers"], [{
            "file": EVENTS, "line": 1, "call": "two", "form": "block",
            "args": ["A", "C"], "unknown": ["C"], "missing": ["B"],
        }])
        self.assertIsNone(helper_callers(r, "nope"))


class LiveTreeTests(unittest.TestCase):
    def test_mod_is_clean(self):
        # The same check CI runs with --strict; vanilla callees aside.
        root = os.path.dirname(os.path.abspath(__file__))
        r = audit(mod_path=root, vanilla_game=None)
        self.assertEqual([describe(f) for f in r.flags if not f.exemption], [])
        self.assertEqual(r.stale_tags, [])


if __name__ == "__main__":
    unittest.main()
