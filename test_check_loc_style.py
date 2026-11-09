"""`scripts/analysis/check_loc_style.py`: its rules, its exceptions and its ratchet."""
import tempfile
import unittest
from pathlib import Path

import scripts.analysis.check_loc_style as cls


def rules(value):
    return [rule for rule, _ in cls.lint_value(value)]


class RuleTests(unittest.TestCase):
    def test_each_rule_fires(self):
        cases = {
            "Banks sit on mountains of reserves.": "stock-metaphor",
            "The accounts are harrowing.": "verdict-word",
            "A comprehensive review followed.": "ai-word",
            "It stands as the center of the world.": "ai-phrase",
            "They fight in them, not just travel in them.": "neg-parallel",
            "This is not justice - this is theft.": "spaced-hyphen",
            "And so it goes...": "ellipsis-end",
            r"A list:\nOne.\n": "trailing-newline",
        }
        for value, rule in cases.items():
            self.assertIn(rule, rules(value), value)

    def test_plain_text_passes(self):
        for value in (
            "We have settled a border dispute with a neighbor.",
            "The loan and a tenth more, over five years.",
            r"Its ties rise #v 2#! a month.\nAt full ties it asks to join.",
            "A key industry in the realm.",  # ordinary game vocabulary
            "A well-known figure, 10-15 years on.",  # hyphens that are not dashes
        ):
            self.assertEqual(rules(value), [], value)

    def test_markup_is_not_prose(self):
        self.assertEqual(rules("[GetStaticModifier('comprehensive_review').GetDesc] applies."), [])
        self.assertEqual(rules("$unprecedented_growth$ is in force."), [])

    def test_every_rule_has_a_pattern_and_a_message(self):
        self.assertEqual(set(cls.RULES), set(cls._PATTERNS))


class ScanTests(unittest.TestCase):
    def scan(self, body):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "te_sample_l_english.yml"
            path.write_text("﻿l_english:\n" + body, encoding="utf-8")
            return [(rule, key) for rule, key, *_ in cls.scan(Path(tmp))]

    def test_reviewed_line_and_headlines_and_test_benches(self):
        found = self.scan(
            ' a:0 "A robust hull."\n'
            ' b:0 "A robust hull." # REVIEWED 2026-11-09 (loc_style): the class name\n'
            ' c:0 "A robust hull." # REVIEWED 2026-11-09: another audit\'s comment\n'
            ' notification_headlines_x_desc:0 "It spreads... #!"\n'
            ' other_desc:0 "It spreads..."\n'
            ' te_debug_x:0 "A robust bench."\n'
        )
        self.assertEqual(found, [("ai-word", "a"), ("ai-word", "c"), ("ellipsis-end", "other_desc")])

    def test_generated_and_unused_files_are_skipped(self):
        names = {p.name for p in cls.loc_files()}
        self.assertIn("te_events_l_english.yml", names)
        self.assertFalse([n for n in names if "generated" in n or "unused" in n])


class BaselineTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baseline.txt"
            pairs = {("ai-word", "b.key"), ("ai-word", "a.key"), ("verdict-word", "a.key")}
            cls.write_baseline(pairs, path)
            self.assertEqual(cls.read_baseline(path), pairs)
            body = [line for line in path.read_text().splitlines() if not line.startswith("#")]
            self.assertEqual(body, sorted(body))

    def test_committed_baseline_matches_the_text(self):
        """Nothing new, and nothing stale: the same thing `--check` enforces."""
        current = {(rule, key) for rule, key, *_ in cls.scan()}
        baseline = cls.read_baseline()
        self.assertEqual(sorted(current - baseline), [], "new style findings: see check_loc_style.py --check")
        self.assertEqual(sorted(baseline - current), [], "stale baseline lines: run check_loc_style.py --update")


if __name__ == "__main__":
    unittest.main()
