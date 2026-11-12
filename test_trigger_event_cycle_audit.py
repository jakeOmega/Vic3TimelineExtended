"""Tests for trigger_event_cycle_audit (#1012).

An undelayed `trigger_event` on a cycle of scripted-effect calls and undelayed
`trigger_event`s recurses on the engine's stack. The shape that crashed twice
on 2026-10-17 (an effect fires an event whose refresh calls the effect again)
must flag; a delay on any edge of the cycle must clear it.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

import event_context_audit
import trigger_event_cycle_audit as tca
from trigger_event_cycle_audit import audit, cycles_through, describe, render_report

EFFECTS = "common/scripted_effects/e.txt"
EVENTS = "events/x.txt"
TAG = "# REVIEWED 2026-11-12 (trigger_event_cycle): "


def _tree(root: str, files: dict[str, str]) -> str:
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8-sig") as fh:
            fh.write(text)
    return root


def _run(files: dict[str, str]):
    with tempfile.TemporaryDirectory() as mod:
        return audit(mod_path=_tree(mod, files))


def _summary(result):
    return [(f.file, f.line, f.source, f.event, bool(f.exemption)) for f in result.flags]


def _two_events(first: str = "", second: str = "") -> dict[str, str]:
    """x.1's immediate fires x.2, whose immediate fires x.1."""
    return {EVENTS: (
        "x.1 = {\n\thidden = yes\n\timmediate = {\n"
        f"\t\ttrigger_event = {{ id = x.2{first}\n"
        "\t}\n}\n"
        "x.2 = {\n\thidden = yes\n\timmediate = {\n"
        f"\t\ttrigger_event = {{ id = x.1{second}\n"
        "\t}\n}\n"
    )}


class CycleTests(unittest.TestCase):
    def test_two_events_firing_each_other_with_no_delay_flag_both_edges(self):
        r = _run(_two_events(" }", " }"))
        self.assertEqual(_summary(r), [(EVENTS, 4, "x.1", "x.2", False), (EVENTS, 10, "x.2", "x.1", False)])
        self.assertEqual(r.flags[0].cycle, ["x.1", "x.2", "x.1"])
        self.assertEqual(r.flags[0].component, r.flags[1].component)
        self.assertEqual((r.components, r.failing, r.undelayed_edges), (1, 2, 2))

    def test_a_delay_on_one_edge_breaks_the_cycle(self):
        for delay in (" days = 1 }", " months = 2 }", " years = { 1 2 } }", " weeks = some_value }"):
            with self.subTest(delay=delay):
                r = _run(_two_events(" }", delay))
                self.assertEqual((r.flags, r.failing, r.undelayed_edges), ([], 0, 1))

    def test_a_literal_zero_is_no_delay(self):
        self.assertEqual(len(_run(_two_events(" }", " days = 0 }")).flags), 2)

    def test_the_bare_form_is_an_undelayed_edge(self):
        files = {EVENTS: ("x.1 = {\n\timmediate = {\n\t\ttrigger_event = x.2\n\t}\n}\n"
                          "x.2 = {\n\timmediate = {\n\t\ttrigger_event = x.1\n\t}\n}\n")}
        self.assertEqual([(f.line, f.event) for f in _run(files).flags], [(3, "x.2"), (8, "x.1")])

    def test_a_cycle_through_a_scripted_effect(self):
        # gm_com_fulfil's shape: the effect fires an event whose immediate
        # calls a refresh that calls the effect.
        r = _run({
            EVENTS: "x.1 = {\n\thidden = yes\n\timmediate = {\n\t\trefresh = yes\n\t}\n}\n",
            EFFECTS: ("refresh = {\n\tfulfil = yes\n}\n"
                      "fulfil = {\n\ttrigger_event = { id = x.1 }\n\tclose = yes\n}\n"
                      "close = {\n\tremove_variable = open\n}\n"),
        })
        self.assertEqual(_summary(r), [(EFFECTS, 5, "fulfil", "x.1", False)])
        self.assertEqual(r.flags[0].cycle, ["fulfil", "x.1", "refresh", "fulfil"])
        self.assertEqual(r.flags[0].component_size, 3)

    def test_an_event_id_passed_as_a_parameter_flags_at_the_call_that_names_it(self):
        r = _run({
            EVENTS: ("x.1 = {\n\thidden = yes\n\timmediate = {\n"
                     "\t\tsend = {\n\t\t\tWHO = root\n\t\t\tEVENT = x.2\n\t\t}\n"
                     "\t}\n}\n"
                     "x.2 = {\n\thidden = yes\n\timmediate = {\n\t\tsend = { WHO = root EVENT = x.1 }\n\t}\n}\n"
                     # Not on the cycle: x.3 names an event that fires nothing.
                     "x.3 = {\n\timmediate = {\n\t\tsend = { WHO = root EVENT = x.4 }\n\t}\n}\n"
                     "x.4 = {\n\thidden = yes\n}\n"),
            EFFECTS: "send = {\n\t$WHO$ = {\n\t\ttrigger_event = { id = $EVENT$ popup = yes }\n\t}\n}\n",
        })
        self.assertEqual(_summary(r), [(EVENTS, 4, "x.1", "x.2", False), (EVENTS, 13, "x.2", "x.1", False)])
        self.assertEqual(r.flags[0].through, "send")
        self.assertIn("the id is `send`'s parameter", describe(r.flags[0]))

    def test_a_delayed_parameter_event_is_no_edge(self):
        r = _run({
            EVENTS: ("x.1 = {\n\timmediate = {\n\t\tsend = { EVENT = x.2 }\n\t}\n}\n"
                     "x.2 = {\n\timmediate = {\n\t\tsend = { EVENT = x.1 }\n\t}\n}\n"),
            EFFECTS: "send = {\n\ttrigger_event = { id = $EVENT$ days = 1 }\n}\n",
        })
        self.assertEqual(r.flags, [])

    def test_an_event_that_fires_itself(self):
        r = _run({EVENTS: "x.1 = {\n\thidden = yes\n\timmediate = {\n\t\ttrigger_event = { id = x.1 }\n\t}\n}\n"})
        self.assertEqual(_summary(r), [(EVENTS, 4, "x.1", "x.1", False)])
        self.assertEqual(r.flags[0].cycle, ["x.1", "x.1"])
        self.assertIn("which is itself", describe(r.flags[0]))

    def test_an_option_and_a_random_branch_are_edges(self):
        r = _run({EVENTS: (
            "x.1 = {\n\toption = {\n\t\ttrigger_event = { id = x.2 }\n\t}\n}\n"
            "x.2 = {\n\timmediate = {\n\t\trandom_list = {\n\t\t\t1 = { }\n"
            "\t\t\t1 = { trigger_event = { id = x.1 } }\n\t\t}\n\t}\n}\n"
        )})
        self.assertEqual([(f.line, f.in_option, f.random) for f in r.flags], [(3, True, False), (10, False, True)])
        self.assertIn("(in an option)", describe(r.flags[0]))
        self.assertIn("(behind a random roll)", describe(r.flags[1]))

    def test_a_trigger_event_off_the_cycle_is_not_flagged(self):
        r = _run({EVENTS: (
            "x.1 = {\n\timmediate = {\n\t\ttrigger_event = { id = x.2 }\n\t\ttrigger_event = { id = x.3 }\n\t}\n}\n"
            "x.2 = {\n\timmediate = {\n\t\ttrigger_event = { id = x.1 }\n\t}\n}\n"
            "x.3 = {\n\thidden = yes\n}\n"
        )})
        self.assertEqual([(f.line, f.event) for f in r.flags], [(3, "x.2"), (9, "x.1")])
        self.assertEqual(r.undelayed_edges, 3)

    def test_a_display_only_block_fires_nothing(self):
        r = _run({
            EVENTS: "x.1 = {\n\timmediate = {\n\t\thelper = yes\n\t}\n}\n",
            "common/journal_entries/j.txt": (
                "je_x = {\n\tmap_tooltip = { trigger_event = { id = x.1 } }\n}\n"),
            EFFECTS: "helper = {\n\tadd = 1\n}\n",
        })
        self.assertEqual(r.flags, [])

    def test_a_dispatcher_does_not_join_what_no_caller_joins(self):
        # x.2's option names `stop`, which fires nothing, so the reply that
        # `go` sends does not come back; a graph with one edge from the
        # wrapper to every act would call this a cycle.
        r = _run({
            EVENTS: ("x.1 = {\n\toption = {\n\t\tpick = { ACT = go }\n\t}\n}\n"
                     "x.2 = {\n\toption = {\n\t\tpick = { ACT = stop }\n\t}\n}\n"),
            EFFECTS: ("pick = {\n\tact_$ACT$ = yes\n}\n"
                      "act_go = {\n\ttrigger_event = { id = x.2 }\n}\n"
                      "act_stop = {\n\tadd = 1\n}\n"),
        })
        self.assertEqual(r.flags, [])

    def test_a_dispatcher_that_does_lead_back_flags(self):
        r = _run({
            EVENTS: "x.1 = {\n\toption = {\n\t\tpick = { ACT = go }\n\t}\n}\n",
            EFFECTS: ("pick = {\n\tact_$ACT$ = yes\n}\n"
                      "act_go = {\n\ttrigger_event = { id = x.1 }\n}\n"),
        })
        self.assertEqual(_summary(r), [(EFFECTS, 5, "act_go", "x.1", False)])
        self.assertEqual(r.flags[0].cycle, ["act_go", "x.1", "act_go"])

    def test_console_harnesses_are_audited(self):
        r = _run({"events/te_debug_x_events.txt":
                  "te_debug_x.1 = {\n\toption = {\n\t\ttrigger_event = { id = te_debug_x.1 }\n\t}\n}\n"})
        self.assertEqual([(f.file, f.line) for f in r.flags], [("events/te_debug_x_events.txt", 3)])

    def test_cycles_through_a_name(self):
        r = _run(_two_events(" }", " }"))
        self.assertEqual(len(cycles_through(r, "x.2")), 2)
        self.assertEqual(cycles_through(r, "x.9"), [])


class ReviewTests(unittest.TestCase):
    def test_a_reviewed_cycle_is_exempt(self):
        r = _run(_two_events(" } " + TAG + "x.2's trigger reads the mark set above", " } " + TAG + "as x.1"))
        self.assertEqual([bool(f.exemption) for f in r.flags], [True, True])
        self.assertEqual(r.flags[0].exemption,
                         {"date": "2026-11-12", "rationale": "x.2's trigger reads the mark set above"})
        self.assertEqual((r.failing, r.stale_tags), (0, []))

    def test_one_tag_exempts_one_edge(self):
        r = _run(_two_events(" } " + TAG + "why", " }"))
        self.assertEqual([bool(f.exemption) for f in r.flags], [True, False])
        self.assertEqual(r.failing, 1)

    def test_a_tag_on_a_line_with_no_flag_is_stale(self):
        # The cycle was broken with a delay and the tags stayed.
        r = _run(_two_events(" } " + TAG + "why", " days = 1 } " + TAG + "why"))
        self.assertEqual(r.flags, [])
        self.assertEqual([(t.file, t.line) for t in r.stale_tags], [(EVENTS, 4), (EVENTS, 10)])
        self.assertEqual(r.failing, 2)

    def test_another_audits_tag_and_the_untagged_form_are_not_ours(self):
        r = _run(_two_events(" } # REVIEWED 2026-11-12 (script_argument): theirs",
                             " } # REVIEWED 2026-11-12: untagged"))
        self.assertEqual([bool(f.exemption) for f in r.flags], [False, False])
        self.assertEqual(r.stale_tags, [])

    def test_a_tag_shared_with_another_check_counts(self):
        r = _run(_two_events(" } # REVIEWED 2026-11-12 (script_argument, trigger_event_cycle): both", " }"))
        self.assertEqual([bool(f.exemption) for f in r.flags], [True, False])

    def test_a_parameter_events_tag_goes_on_the_call(self):
        r = _run({
            EVENTS: ("x.1 = {\n\timmediate = {\n\t\tsend = { EVENT = x.1 } " + TAG + "why\n\t}\n}\n"),
            EFFECTS: "send = {\n\ttrigger_event = { id = $EVENT$ } " + TAG + "not here\n}\n",
        })
        self.assertEqual(_summary(r), [(EVENTS, 3, "x.1", "x.1", True)])
        self.assertEqual([(t.file, t.line) for t in r.stale_tags], [(EFFECTS, 2)])

    def test_event_context_audit_leaves_the_tag_alone(self):
        self.assertIn(tca.CHECK, event_context_audit.FOREIGN_CHECKS)


class ReportTests(unittest.TestCase):
    def test_report_lists_flags_stale_tags_and_reviews(self):
        files = _two_events(" } " + TAG + "the mark is set first", " }")
        files[EFFECTS] = "lone = {\n\ttrigger_event = { id = x.1 days = 1 } " + TAG + "stale\n}\n"
        report = render_report(_run(files))
        self.assertIn("### `events/x.txt`", report)
        self.assertIn("- line 10: `x.2` fires `x.1` with no delay, and it leads back: `x.2` → `x.1` → `x.2`",
                      report)
        self.assertIn("- `common/scripted_effects/e.txt:2` (trigger_event_cycle)", report)
        self.assertIn("- `events/x.txt` — `x.1` fires `x.2` with no delay, and it leads back: "
                      "`x.1` → `x.2` → `x.1` — **2026-11-12**: the mark is set first", report)
        self.assertIn("- total flags: 2\n- unreviewed: 1\n- exempted: 1\n- stale tags: 1\n", report)

    def test_a_clean_report(self):
        report = render_report(_run({EVENTS: "x.1 = {\n\thidden = yes\n}\n"}))
        self.assertEqual(report.count("_None._"), 2)
        self.assertNotIn("## Stale tags", report)

    def test_regenerate_writes_report_and_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            _tree(tmp, _two_events(" } " + TAG + "why", " }"))
            with mock.patch("path_constants.mod_path", tmp):
                summary = tca.regenerate()
            with open(os.path.join(tmp, "docs", "engine", "trigger_event_cycle_report.md"),
                      encoding="utf-8") as fh:
                report = fh.read()
        self.assertEqual((summary["unreviewed"], summary["total_flags"], summary["exempted"],
                          summary["stale_tags"], summary["components"]), (1, 2, 1, 0, 1))
        self.assertIn("- line 10: `x.2` fires `x.1` with no delay", report)


if __name__ == "__main__":
    unittest.main()
