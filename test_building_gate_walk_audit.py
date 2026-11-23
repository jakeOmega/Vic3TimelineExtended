"""Unit tests for building_gate_walk_audit.

A walk counts in the four blocks the weekly private investment pass reads
often (`potential`, `possible`, `can_build_private`, `ai_value`), written there or reached
through scripted triggers and script values, and nowhere else. A `# REVIEWED`
comment on the iterator's line covers every building that reaches it; one on
the block's opening line covers that block.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from building_gate_walk_audit import audit, render_report


class Tree:
    """A mod tree in a temporary folder."""

    def __init__(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = self.dir.name

    def write(self, rel: str, text: str) -> None:
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8-sig") as fh:
            fh.write(text)

    def run(self):
        return audit(mod_path=self.root)


class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.tree = Tree()
        self.addCleanup(self.tree.dir.cleanup)

    def test_a_walk_written_in_possible(self):
        self.tree.write("common/buildings/b.txt", (
            "building_x = {\n"
            "\tpossible = {\n"
            "\t\tany_scope_building = { is_building_type = building_y }\n"
            "\t}\n"
            "}\n"))
        flags = self.tree.run().flags
        self.assertEqual(len(flags), 1)
        f = flags[0]
        self.assertEqual((f.building, f.block, f.iterator, f.line, f.site_line, f.via),
                         ("building_x", "possible", "any_scope_building", 2, 3, ()))

    def test_a_walk_through_a_trigger_and_a_value(self):
        self.tree.write("common/scripted_triggers/t.txt", "my_gate = {\n\towner = { my_room > 0 }\n}\n")
        self.tree.write("common/script_values/v.txt", (
            "my_room = {\n"
            "\tvalue = 0\n"
            "\tevery_scope_state = { add = 1 }\n"
            "}\n"))
        self.tree.write("common/buildings/b.txt", "building_x = {\n\tpossible = { my_gate = yes }\n}\n")
        flags = self.tree.run().flags
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].via, ("my_gate", "my_room"))
        self.assertEqual((flags[0].site_file, flags[0].site_line), ("common/script_values/v.txt", 3))

    def test_the_hot_blocks_only(self):
        walk = "{ any_scope_state = { always = yes } }"
        self.tree.write("common/buildings/b.txt", (
            "building_x = {\n"
            f"\tpotential = {walk}\n"
            f"\tcan_build_government = {walk}\n"
            f"\tcan_build_private = {walk}\n"
            f"\tai_value = {{ value = 1 if = {{ limit = {walk} add = 1 }} }}\n"
            "}\n"))
        self.assertEqual(sorted(f.block for f in self.tree.run().flags), ["ai_value", "can_build_private", "potential"])

    def test_a_scalar_ai_value_is_followed(self):
        self.tree.write("common/script_values/v.txt", "my_ai = {\n\tvalue = 0\n\tevery_scope_pop = { add = 1 }\n}\n")
        self.tree.write("common/buildings/b.txt", "building_x = {\n\tai_value = my_ai\n}\n")
        self.assertEqual([f.iterator for f in self.tree.run().flags], ["every_scope_pop"])

    def test_an_inject_of_a_vanilla_building(self):
        self.tree.write("common/buildings/b.txt", (
            "INJECT:building_power_plant = {\n"
            "\tpossible = { owner = { any_scope_state = { always = yes } } }\n"
            "}\n"))
        self.assertEqual([f.building for f in self.tree.run().flags], ["INJECT:building_power_plant"])

    def test_engine_lookups_and_non_iterators_pass(self):
        self.tree.write("common/buildings/b.txt", (
            "building_x = {\n"
            "\tpossible = {\n"
            "\t\texists = b:building_y\n"
            "\t\thas_building = building_y\n"
            "\t\trandom_list = { 1 = { } }\n"
            "\t}\n"
            "}\n"))
        self.assertEqual(self.tree.run().flags, [])

    def test_a_vanilla_script_value_from_the_snapshot(self):
        self.tree.write("vanilla_parsed/common/script_values.json", json.dumps(
            {"vanilla_walk": ["=", {"value": 0, "every_scope_building": ["=", {"add": 1}]}]}))
        self.tree.write("common/buildings/b.txt", "building_x = {\n\tpossible = { vanilla_walk > 0 }\n}\n")
        flags = self.tree.run().flags
        self.assertEqual([(f.iterator, f.site_file) for f in flags],
                         [("every_scope_building", "vanilla:common/script_values")])

    def test_a_cycle_ends(self):
        self.tree.write("common/scripted_triggers/t.txt", "a = { b = yes }\nb = { a = yes any_scope_state = { } }\n")
        self.tree.write("common/buildings/b.txt", "building_x = {\n\tpossible = { a = yes }\n}\n")
        self.assertEqual([f.via for f in self.tree.run().flags], [("a", "b")])


class ExemptionTests(unittest.TestCase):
    def setUp(self):
        self.tree = Tree()
        self.addCleanup(self.tree.dir.cleanup)
        self.tree.write("common/scripted_triggers/t.txt", (
            "my_gate = {\n"
            "\tany_scope_state = { always = yes } # REVIEWED 2026-11-22: behind a test nearly every country fails\n"
            "}\n"))

    def test_on_the_iterator_line_covers_every_caller(self):
        self.tree.write("common/buildings/b.txt", (
            "building_x = {\n\tpossible = { my_gate = yes }\n}\n"
            "building_y = {\n\tai_value = { value = 1 if = { limit = { my_gate = yes } add = 1 } }\n}\n"))
        result = self.tree.run()
        self.assertEqual(len(result.flags), 2)
        self.assertEqual(result.unreviewed, [])

    def test_on_the_block_line_covers_that_block(self):
        self.tree.write("common/buildings/b.txt", (
            "building_x = {\n"
            "\tpossible = { # REVIEWED 2026-11-22: one state, a handful of buildings\n"
            "\t\tany_scope_building = { is_building_type = building_z }\n"
            "\t}\n"
            "\tcan_build_private = { any_scope_building = { is_building_type = building_z } }\n"
            "}\n"))
        result = self.tree.run()
        self.assertEqual([f.block for f in result.unreviewed], ["can_build_private"])

    def test_the_report_names_the_path(self):
        self.tree.write("common/buildings/b.txt", (
            "building_x = {\n\tpossible = { any_scope_building = { always = yes } }\n}\n"))
        report = render_report(self.tree.run())
        self.assertIn("`building_x` `possible` reaches `any_scope_building` at `common/buildings/b.txt:2`", report)
        self.assertIn("total flags: 1", report)

    def test_the_report_lists_a_reviewed_walk_once(self):
        self.tree.write("common/buildings/b.txt", (
            "building_x = {\n\tpossible = { my_gate = yes }\n}\n"
            "building_y = {\n\tpossible = { my_gate = yes }\n}\n"))
        report = render_report(self.tree.run())
        self.assertEqual(report.count("- `any_scope_state` in `common/scripted_triggers/t.txt`"), 1)
        self.assertIn("reached from `building_x` `possible`, `building_y` `possible`", report)
        self.assertNotIn("t.txt:2", report)


if __name__ == "__main__":
    unittest.main()
