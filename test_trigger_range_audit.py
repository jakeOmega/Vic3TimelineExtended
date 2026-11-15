"""Tests for trigger_range_audit.

A comparison of a bounded value against a number outside its range is
constant, and the engine says nothing: `political_movement_radicalism >= 25`
never passed in five of the mod's comparisons, and `turmoil > 25` in three
more, until 2026-11-15 (#1829). A number at a bound, or inside the range, must
not flag; nor may a right-hand side the audit cannot read as a constant.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import tempfile
import unittest

import trigger_range_audit as tra
from trigger_range_audit import LEFT_OUT, RANGES, audit, outcome, scan_parsed

REPO = os.path.dirname(os.path.abspath(__file__))

_ROOTS: list[str] = []


def tearDownModule():
    for root in _ROOTS:
        shutil.rmtree(root, ignore_errors=True)


def _tree(files: dict[str, str], vanilla_values: dict | None = None) -> str:
    """A throwaway mod tree; `vanilla_values` stands in for the snapshot."""
    root = tempfile.mkdtemp()
    _ROOTS.append(root)
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8-sig") as fh:
            fh.write(text)
    snapshot = os.path.join(root, "vanilla_parsed", "common")
    os.makedirs(snapshot)
    with open(os.path.join(snapshot, "script_values.json"), "w", encoding="utf-8") as fh:
        json.dump(vanilla_values or {}, fh)
    return root


def _run(body: str, **files):
    return audit(_tree({"events/e.txt": f"e.1 = {{\n\ttrigger = {{\n{body}\n\t}}\n}}\n", **files}))


class OutcomeTest(unittest.TestCase):
    def test_above_the_maximum(self):
        for op, want in ((">", "never"), (">=", "never"), ("=", "never"), ("?=", "never"),
                         ("<", "always"), ("<=", "always"), ("!=", "always")):
            self.assertEqual(outcome(op, 25, 0, 1), want, op)

    def test_below_the_minimum(self):
        for op, want in ((">", "always"), (">=", "always"), ("<", "never"), ("<=", "never"),
                         ("=", "never"), ("!=", "always")):
            self.assertEqual(outcome(op, -0.5, 0, 1), want, op)

    def test_at_a_bound_or_inside_is_not_constant(self):
        for op in (">", ">=", "<", "<=", "=", "!=", "?="):
            for value in (0, 0.25, 1):
                self.assertIsNone(outcome(op, value, 0, 1), (op, value))


class ScanTest(unittest.TestCase):
    def test_the_bug_is_flagged(self):
        r = _run("\t\tany_political_movement = { political_movement_radicalism >= 25 }")
        self.assertEqual([(f.name, f.op, f.value, f.outcome) for f in r.unreviewed],
                         [("political_movement_radicalism", ">=", 25.0, "never")])
        self.assertTrue(r.failed)

    def test_always_passes_is_flagged(self):
        r = _run("\t\tturmoil < 25")
        self.assertEqual([f.outcome for f in r.unreviewed], ["always"])

    def test_fractions_and_bounds_are_clean(self):
        r = _run("\t\tturmoil > 0.25\n\t\tliberty_desire >= 100\n\t\tig_approval > -20\n"
                 "\t\tpolitical_movement_radicalism >= 1")
        self.assertEqual(r.flags, [])
        self.assertEqual(r.judged, 4)

    def test_a_scope_chain_names_the_value_by_its_last_segment(self):
        r = _run("\t\tscope:target_country.capital.turmoil > 25\n\t\tscope:m.political_movement_radicalism <= 25")
        self.assertEqual([(f.name, f.outcome) for f in r.unreviewed],
                         [("turmoil", "never"), ("political_movement_radicalism", "always")])

    def test_a_quoted_call_on_the_left(self):
        r = _run('\t\t"owner.pop_type_percent_country(pop_type:peasants)" >= 25\n'
                 '\t\t"owner.pop_type_percent_country(pop_type:peasants)" < 0.25\n'
                 '\t\t"unknown_call(x)" > 25')
        self.assertEqual([(f.name, f.form, f.outcome) for f in r.unreviewed],
                         [("pop_type_percent_country", "call", "never")])
        self.assertIn('`"pop_type_percent_country(…)" >= 25`', r.unreviewed[0].message)

    def test_the_block_forms_value(self):
        r = _run("\t\tradical_fraction = {\n\t\t\tstrata = lower\n\t\t\tvalue >= 10\n\t\t}\n"
                 "\t\tculture_percent_country = { target = cu:x value > 0 }")
        self.assertEqual([(f.name, f.form, f.line) for f in r.unreviewed], [("radical_fraction", "block", 5)])

    def test_a_value_key_outside_a_ranged_block_is_ignored(self):
        r = _run("\t\tadd_radicals = { value = 25 }\n\t\tinstitution_x = { value = 50 }")
        self.assertEqual(r.flags, [])

    def test_a_constant_script_value_is_resolved(self):
        r = _run("\t\tturmoil > big_turmoil\n\t\tturmoil > small_turmoil\n\t\tturmoil > vanilla_turmoil",
                 **{"common/script_values/v.txt": "big_turmoil = { value = 25 }\nsmall_turmoil = 0.25\n"
                                                  "long_turmoil = {\n\tvalue = 30\n}\n"})
        self.assertEqual([(f.written, f.value) for f in r.unreviewed], [("big_turmoil", 25.0)])
        self.assertIn("(`big_turmoil` = 25)", r.unreviewed[0].message)
        # vanilla_turmoil names nothing in this tree: counted, not judged.
        self.assertEqual(r.unjudged.get("named level or other name"), 1)

    def test_a_vanilla_constant_is_resolved(self):
        root = _tree({"events/e.txt": "e.1 = { trigger = { turmoil > vt } }\n"},
                     vanilla_values={"vt": ["=", "25"], "vb": ["=", {"value": ["=", "30"]}]})
        self.assertEqual([f.value for f in audit(root).unreviewed], [25.0])

    def test_what_is_not_a_constant_is_counted_not_judged(self):
        r = _run("\t\tturmoil > computed\n\t\tturmoil > $X$\n\t\tturmoil > define:NPolitics|A\n"
                 "\t\tturmoil > var:t\n\t\tig_approval < happy",
                 **{"common/script_values/v.txt": "computed = {\n\tvalue = 1\n\tmultiply = 50\n}\n"})
        self.assertEqual(r.flags, [])
        self.assertEqual(r.judged, 0)
        self.assertEqual(r.unjudged, {"computed script value": 1, "parameter": 1, "define": 1,
                                      "variable, scope or other": 1, "named level or other name": 1})

    def test_comments_and_strings_are_not_read(self):
        r = _run('\t\t# turmoil > 25\n\t\tcustom_tooltip = "turmoil > 25"')
        self.assertEqual(r.flags, [])

    def test_a_mod_define_moves_the_bound(self):
        files = {"common/defines/d.txt": "NInstitutions = {\n\tMAX_INSTITUTION_INVESTMENT = 9\n}\n"}
        ok = _run("\t\tinstitution_investment_level = { institution = i value >= 9 }", **files)
        self.assertEqual(ok.flags, [])
        bad = _run("\t\tinstitution_investment_level = { institution = i value >= 10 }", **files)
        self.assertEqual([f.hi for f in bad.unreviewed], [9.0])
        vanilla_default = _run("\t\tinstitution_investment_level = { institution = i value >= 9 }")
        self.assertEqual([f.hi for f in vanilla_default.unreviewed], [5.0])


class SuppressionTest(unittest.TestCase):
    def test_a_tag_on_the_line_suppresses(self):
        r = _run("\t\tturmoil > 25 # REVIEWED 2026-11-15 (trigger_range): deliberately off")
        self.assertEqual(r.unreviewed, [])
        self.assertEqual(len(r.exemptions), 1)
        self.assertFalse(r.failed)

    def test_a_tag_on_the_block_opener_suppresses(self):
        r = _run("\t\tradical_fraction = { # REVIEWED 2026-11-15 (trigger_range): why\n\t\t\tvalue > 2\n\t\t}")
        self.assertEqual(r.unreviewed, [])
        self.assertEqual(r.stale, [])

    def test_the_plain_form_does_not_suppress(self):
        r = _run("\t\tturmoil > 25 # REVIEWED 2026-11-15: no tag")
        self.assertEqual(len(r.unreviewed), 1)

    def test_a_constant_written_over_three_lines_is_resolved(self):
        r = _run("\t\tturmoil > long_turmoil",
                 **{"common/script_values/v.txt": "long_turmoil = {\n\tvalue = 30\n}\n"})
        self.assertEqual([f.value for f in r.unreviewed], [30.0])

    def test_a_stale_tag_in_a_file_with_no_ranged_value_is_found(self):
        r = audit(_tree({"events/e.txt": "e.1 = { # REVIEWED 2026-11-15 (trigger_range): gone\n}\n"}))
        self.assertEqual([s.line for s in r.stale], [1])

    def test_a_tag_that_suppresses_nothing_is_stale(self):
        r = _run("\t\tturmoil > 0.25 # REVIEWED 2026-11-15 (trigger_range): left over")
        self.assertEqual([(s.line, s.tag) for s in r.stale], [(3, "trigger_range")])
        self.assertTrue(r.failed)


class TableTest(unittest.TestCase):
    def test_every_name_is_an_engine_trigger_or_value(self):
        known = set()
        for rel in ("docs/engine/triggers_summary.txt", "docs/engine/event_targets_summary.txt"):
            with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
                for line in fh:
                    parts = line.rstrip("\n").split("|")
                    known.update(p.strip() for p in parts[:2])
        for name in list(RANGES) + list(LEFT_OUT):
            self.assertIn(name, known, f"{name} is not in the engine's trigger or event target summary")

    def test_each_row_has_a_range_and_evidence(self):
        for name, r in RANGES.items():
            self.assertLess(r.lo, r.hi, name)
            self.assertTrue(r.evidence.strip(), name)
        self.assertFalse(set(RANGES) & set(LEFT_OUT))
        self.assertTrue(all(why.strip() for why in LEFT_OUT.values()))

    def test_the_value_key_is_not_a_row(self):
        # A block's `value` child is read against its block's row.
        self.assertNotIn("value", RANGES)


class ModTest(unittest.TestCase):
    def test_the_mod_is_clean(self):
        result = audit(REPO)
        self.assertEqual([(f.file, f.line, f.message) for f in result.failing], [])
        self.assertGreater(result.judged, 500)


class VanillaTest(unittest.TestCase):
    """The inverse: a row that flags vanilla's own script is probably a wrong
    range. Vanilla's two real hits are in docs/vanilla/vanilla_known_bugs.md."""

    def test_vanilla_parsed_inverse(self):
        hits = set()
        for path in sorted(glob.glob(os.path.join(REPO, "vanilla_parsed", "common", "*.json"))):
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            kind = os.path.basename(path)[:-5]
            for entity, body in data.items():
                for where, name, op, literal, verdict in scan_parsed(body, (entity,)):
                    hits.add((kind, where[0], name, op, literal, verdict))
        # The snapshot has no events/, so movement_events.txt:968 is not here.
        self.assertEqual(hits, {
            ("diplomatic_actions", "invoke_doctrine_of_lapse", "turmoil", ">", "25", "never"),
        })

    def test_the_known_vanilla_bugs_are_recorded(self):
        with open(os.path.join(REPO, "docs", "vanilla", "vanilla_known_bugs.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("46_doctrine_of_lapse.txt:151", text)
        self.assertIn("movement_events.txt:968", text)


def _game_dir() -> str | None:
    try:
        from path_constants import base_game_path
    except Exception:
        return None
    game = os.path.join(base_game_path, "game")
    return game if os.path.isdir(os.path.join(game, "common", "defines")) else None


@unittest.skipIf(_game_dir() is None, "needs the game's files")
class VanillaFilesTest(unittest.TestCase):
    def test_the_raw_vanilla_tree_flags_only_the_two_known_bugs(self):
        result = audit(REPO, root=_game_dir())
        self.assertEqual(sorted((f.file, f.line, f.name) for f in result.flags), [
            ("common/diplomatic_actions/46_doctrine_of_lapse.txt", 151, "turmoil"),
            ("events/movement_events.txt", 968, "political_movement_radicalism"),
        ])

    def test_the_baked_defaults_are_vanillas_defines(self):
        defines = tra.read_defines(_game_dir())
        for name, r in RANGES.items():
            for define, baked in ((r.lo_define, r.lo), (r.hi_define, r.hi)):
                if define:
                    self.assertEqual(defines.get(define), baked, f"{name}: {define}")


class ReportTest(unittest.TestCase):
    def test_the_report_lists_the_ranges_and_left_out(self):
        text = tra.render_report(_run("\t\tturmoil > 25"))
        self.assertIn("## Unreviewed flags", text)
        self.assertIn("`turmoil > 25` never passes", text)
        self.assertIn("| `political_movement_radicalism` | 0 to 1 |", text)
        self.assertIn("| `occupancy` |", text)
        self.assertIsNotNone(re.search(r"comparisons judged: 1\b", text))


if __name__ == "__main__":
    unittest.main()
