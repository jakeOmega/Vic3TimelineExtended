"""Tests for script_call_graph: the forward call graph over
event_context_audit's scan, and its graph questions (#1012)."""
from __future__ import annotations

import os
import tempfile
import unittest

import script_call_graph as scg
from script_call_graph import EFFECT, EVENT, ON_ACTION, Edge, Node

EFFECTS = "common/scripted_effects/e.txt"
EVENTS = "events/x.txt"


def _build(files: dict[str, str], **kw) -> scg.CallGraph:
    with tempfile.TemporaryDirectory() as mod:
        for rel, text in files.items():
            path = os.path.join(mod, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8-sig") as fh:
                fh.write(text)
        return scg.build(mod, **kw)


def _edges(cg: scg.CallGraph, kind: str | None = None):
    return sorted((e.src.name, e.dst.name, e.kind, e.line) for e in cg.edges
                  if kind is None or e.kind == kind)


def _ev(name: str) -> Node:
    return Node(EVENT, name)


def _fx(name: str) -> Node:
    return Node(EFFECT, name)


class BuildTests(unittest.TestCase):
    def test_calls_and_events_become_typed_edges(self):
        cg = _build({
            EVENTS: ("x.1 = {\n\timmediate = {\n\t\thelper = { A = 1 }\n\t}\n"
                     "\toption = {\n\t\trandom_list = {\n\t\t\t1 = { trigger_event = { id = x.2 days = 3 } }\n"
                     "\t\t}\n\t}\n}\n"
                     "x.2 = {\n\thidden = yes\n}\n"),
            EFFECTS: "helper = {\n\tadd = $A$\n\ttrigger_event = { id = x.2 }\n}\n",
        })
        self.assertEqual(_edges(cg), [
            ("helper", "x.2", "event", 3),
            ("x.1", "helper", "call", 3),
            ("x.1", "x.2", "event", 7),
        ])
        by = {(e.src.name, e.dst.name): e for e in cg.edges}
        self.assertEqual(by["x.1", "helper"].params, (("A", "1"),))
        self.assertEqual(by["x.1", "helper"].path, ("immediate",))
        delayed = by["x.1", "x.2"]
        self.assertTrue(delayed.delayed and delayed.in_option and delayed.random)
        self.assertFalse(by["helper", "x.2"].delayed)
        self.assertEqual(cg.nodes[_ev("x.1")], (EVENTS, 1))
        self.assertEqual(cg.nodes[_fx("helper")][0], EFFECTS)
        self.assertEqual([e.dst.name for e in cg.callees(_ev("x.1"))], ["helper"])

    def test_an_event_passed_as_a_parameter_is_an_edge_from_the_caller_that_names_it(self):
        cg = _build({
            EVENTS: ("x.1 = {\n\timmediate = {\n\t\tfwd = { EV = x.2 }\n\t}\n}\n"
                     "x.2 = {\n\thidden = yes\n}\n"),
            EFFECTS: ("send = {\n\ttrigger_event = { id = $EVENT$ }\n}\n"
                      "fwd = {\n\tsend = { EVENT = $EV$ }\n}\n"),
        })
        [edge] = [e for e in cg.edges if e.kind == "event"]
        self.assertEqual((edge.src, edge.dst, edge.file, edge.line, edge.through),
                         (_ev("x.1"), _ev("x.2"), EVENTS, 3, ("send",)))
        # The helpers' own bodies name no event.
        self.assertEqual(cg.edges_from(_fx("send")), [])

    def test_a_literal_event_in_a_parameter_scope_is_one_edge_where_it_is_written(self):
        cg = _build({
            EVENTS: ("x.1 = {\n\timmediate = {\n\t\ttell = { WHO = root }\n\t\ttell = { WHO = scope:a }\n\t}\n}\n"
                     "x.2 = {\n\thidden = yes\n}\n"),
            EFFECTS: "tell = {\n\t$WHO$ = {\n\t\ttrigger_event = { id = x.2 }\n\t}\n}\n",
        })
        self.assertEqual(_edges(cg, "event"), [("tell", "x.2", "event", 3)])

    def test_a_dispatcher_reaches_only_what_each_caller_names(self):
        cg = _build({
            EVENTS: ("x.1 = {\n\toption = {\n\t\tpick = { ACT = go }\n\t}\n}\n"
                     "x.2 = {\n\toption = {\n\t\twrap = { WHAT = stop }\n\t}\n}\n"),
            EFFECTS: ("pick = {\n\tact_$ACT$ = yes\n}\n"
                      "wrap = {\n\tpick = { ACT = $WHAT$ }\n}\n"
                      "act_go = {\n\tadd = 1\n}\n"
                      "act_stop = {\n\tadd = 1\n}\n"
                      "act_never = {\n\tadd = 1\n}\n"),
        })
        dispatched = sorted((e.src.name, e.dst.name, e.line, e.through) for e in cg.edges if e.dispatch)
        self.assertEqual(dispatched, [
            ("x.1", "act_go", 3, ("pick",)),
            ("x.2", "act_stop", 8, ("wrap", "pick")),
        ])
        self.assertEqual(cg.reachable(_ev("x.1")), {_fx("pick"), _fx("act_go")})

    def test_a_dispatcher_nobody_calls_reaches_every_name_its_pattern_fits(self):
        cg = _build({
            EFFECTS: ("pick = {\n\tact_$ACT$ = yes\n}\n"
                      "act_go = {\n\tadd = 1\n}\n"
                      "act_stop = {\n\tadd = 1\n}\n"
                      "other = {\n\tadd = 1\n}\n"),
        })
        self.assertEqual(sorted(e.dst.name for e in cg.edges_from(_fx("pick"))), ["act_go", "act_stop"])

    def test_a_dispatcher_whose_callers_name_nothing_falls_back_to_the_pattern(self):
        cg = _build({
            EVENTS: "x.1 = {\n\toption = {\n\t\tpick = yes\n\t\tpick = { ACT = scope:who }\n\t}\n}\n",
            EFFECTS: ("pick = {\n\tact_$ACT$ = yes\n}\n"
                      "act_go = {\n\tadd = 1\n}\n"),
        })
        self.assertEqual([(e.src.name, e.dst.name, e.line) for e in cg.edges if e.dispatch],
                         [("pick", "act_go", 2)])

    def test_on_actions_chain_and_fire_events(self):
        cg = _build({
            EVENTS: "x.1 = {\n\thidden = yes\n}\n",
            "common/on_actions/o.txt": ("on_monthly_pulse_country = {\n\ton_actions = { my_pulse }\n}\n"
                                        "my_pulse = {\n\tevents = { x.1 }\n}\n"),
        })
        self.assertEqual(_edges(cg), [
            ("my_pulse", "x.1", "event", 5),
            ("on_monthly_pulse_country", "my_pulse", "on_action", 2),
        ])
        [fired] = cg.edges_from(Node(ON_ACTION, "my_pulse"))
        self.assertEqual(fired.via, "events")

    def test_console_harnesses_are_in_unless_left_out(self):
        files = {"events/te_debug_x_events.txt": "te_debug_x.1 = {\n\toption = { trigger_event = { id = te_debug_x.1 } }\n}\n"}
        self.assertEqual(len(_build(files).edges), 1)
        self.assertEqual(len(_build(files, include_console=False).edges), 0)


class GraphTests(unittest.TestCase):
    def _graph(self, pairs, delayed=()) -> scg.CallGraph:
        cg = scg.CallGraph()
        for i, (a, b) in enumerate(pairs):
            kind = "event" if "." in b else "call"
            cg.add_edge(Edge(_ev(a) if "." in a else _fx(a), _ev(b) if "." in b else _fx(b), kind,
                             "f.txt", i + 1, delayed=(a, b) in delayed))
        return cg

    def test_components_are_the_nodes_on_a_cycle(self):
        cg = self._graph([("a.1", "fx"), ("fx", "a.2"), ("a.2", "a.1"), ("a.2", "leaf"),
                          ("b.1", "b.1"), ("c.1", "c.2")])
        comp = cg.components()
        self.assertEqual({n.name for n in comp}, {"a.1", "fx", "a.2", "b.1"})
        self.assertEqual(len({comp[_ev("a.1")], comp[_fx("fx")], comp[_ev("a.2")]}), 1)
        self.assertNotEqual(comp[_ev("a.1")], comp[_ev("b.1")])

    def test_a_filter_drops_delayed_edges(self):
        cg = self._graph([("a.1", "a.2"), ("a.2", "a.1")], delayed={("a.2", "a.1")})
        self.assertEqual(len(cg.components()), 2)
        self.assertEqual(cg.components(scg.runs_at_once), {})

    def test_shortest_path_and_reachable(self):
        cg = self._graph([("a.1", "fx"), ("fx", "a.2"), ("a.1", "a.2"), ("a.2", "a.1"), ("a.2", "leaf")])
        path = cg.shortest_path(_ev("a.1"), _ev("a.1"))
        self.assertEqual([(e.src.name, e.dst.name) for e in path], [("a.1", "a.2"), ("a.2", "a.1")])
        self.assertIsNone(cg.shortest_path(_fx("leaf"), _ev("a.1")))
        self.assertIsNone(cg.shortest_path(_ev("a.1"), _fx("leaf"), within={_ev("a.1"), _fx("fx")}))
        self.assertEqual({n.name for n in cg.reachable(_fx("fx"))}, {"a.1", "a.2", "fx", "leaf"})

    def test_a_long_chain_does_not_recurse(self):
        pairs = [(f"n{i}", f"n{i + 1}") for i in range(5000)] + [("n5000", "n0")]
        self.assertEqual(len(self._graph(pairs).components()), 5001)


if __name__ == "__main__":
    unittest.main()
