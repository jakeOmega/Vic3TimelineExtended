"""Unit tests for prev_scope_audit.

The crux is discrimination: flag a `prev` only where it must resolve to a
scope the script names outright two scope changes up (`root = { link = {
... prev ... } }`) inside some further scope. The ordinary uses of `prev` —
directly inside `root = { }` within an iterator, directly inside an iterator's
`limit`, `prev` meaning a named scope at the top of an effect — must not flag,
and effect blocks such as `add_leverage = { }` must not count as scope changes.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from prev_scope_audit import audit, render_report, scan_text

LINKS = {"power_bloc", "owner", "capital"}


def _scan(text: str):
    return scan_text(text, "test.txt", LINKS)


class DetectionTests(unittest.TestCase):
    def test_reproduces_un_vote_bloc_leverage_bug(self):
        # un_vote.2 before the fix: prev is the proposer, not the member.
        flags = _scan(
            "un_vote.2 = {\n"
            "\toption = {\n"
            "\t\tpower_bloc ?= {\n"
            "\t\t\tevery_power_bloc_member = {\n"
            "\t\t\t\troot = {\n"
            "\t\t\t\t\tpower_bloc ?= {\n"
            "\t\t\t\t\t\tadd_leverage = { target = prev value = 3 }\n"
            "\t\t\t\t\t}\n"
            "\t\t\t\t}\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        f = flags[0]
        self.assertEqual((f.line, f.named, f.named_line), (7, "root", 5))
        self.assertEqual((f.inner, f.outer), ("power_bloc", "every_power_bloc_member"))

    def test_flags_prev_as_trigger_value_and_scope_prefixes(self):
        # The irredentism shape: a trigger value, PREV upper-cased, and a
        # scope:/c: named scope instead of root.
        flags = _scan(
            "t = {\n"
            "\tany_country = {\n"
            "\t\tROOT = {\n"
            "\t\t\tany_primary_culture = { is_primary_culture_of = PREV }\n"
            "\t\t}\n"
            "\t\tscope:x = {\n"
            "\t\t\towner = { save_scope_as = y set_variable = { name = v value = prev.var:w } }\n"
            "\t\t}\n"
            "\t\tc:FRA = { capital = { prev = { add_modifier = { name = m } } } }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual([(f.line, f.named) for f in flags],
                         [(4, "ROOT"), (7, "scope:x"), (9, "c:FRA")])

    def test_prev_directly_inside_named_scope_is_not_flagged(self):
        # The ordinary use: prev is the iterated country.
        self.assertEqual(_scan(
            "e = {\n"
            "\tevery_country = {\n"
            "\t\troot = { change_relations = { country = prev value = 5 } }\n"
            "\t}\n"
            "}\n"
        ), [])

    def test_prev_inside_iterator_limit_is_not_flagged(self):
        # prev = the scope before the iterator (root): common and correct.
        self.assertEqual(_scan(
            "e = {\n"
            "\troot = {\n"
            "\t\tevery_country = { limit = { NOT = { this = prev } } add_x = yes }\n"
            "\t}\n"
            "}\n"
        ), [])

    def test_nothing_outside_the_named_scope_is_not_flagged(self):
        # The top-level entity block is not a scope change, so here prev can
        # only mean scope:op, and saying so by `prev` is merely terse.
        self.assertEqual(_scan(
            "covert_warfare.1 = {\n"
            "\timmediate = {\n"
            "\t\tscope:op = {\n"
            "\t\t\tROOT = { set_variable = { name = t value = PREV.var:type } }\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        ), [])

    def test_effect_blocks_are_transparent(self):
        # add_leverage / if / hidden_effect are not scope changes: prev inside
        # them belongs to the enclosing power_bloc, entered from the member.
        self.assertEqual(_scan(
            "e = {\n"
            "\tevery_country = {\n"
            "\t\tpower_bloc ?= {\n"
            "\t\t\tif = { limit = { always = yes }\n"
            "\t\t\t\thidden_effect = { add_leverage = { target = prev value = 3 } }\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        ), [])

    def test_unnamed_link_between_is_not_flagged(self):
        # prev = owner here; owner cannot be named outright, so using prev
        # for it is legitimate.
        self.assertEqual(_scan(
            "e = {\n"
            "\tevery_scope_state = {\n"
            "\t\towner = { capital = { add_x = { target = prev } } }\n"
            "\t}\n"
            "}\n"
        ), [])

    def test_comments_and_strings_are_ignored(self):
        self.assertEqual(_scan(
            "e = {\n"
            "\tevery_country = {\n"
            "\t\troot = {\n"
            "\t\t\tpower_bloc ?= {\n"
            "\t\t\t\t# target = prev\n"
            "\t\t\t\tcustom_tooltip = \"target = prev\"\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        ), [])


class SuppressionTests(unittest.TestCase):
    def _one(self, prev_comment="", root_comment=""):
        flags = _scan(
            "e = {\n"
            "\tevery_country = {\n"
            "\t\troot = {" + root_comment + "\n"
            "\t\t\tpower_bloc ?= {\n"
            "\t\t\t\tadd_leverage = { target = prev value = 3 }" + prev_comment + "\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        return flags[0]

    def test_unreviewed(self):
        self.assertIsNone(self._one().exemption)

    def test_reviewed_on_prev_line(self):
        f = self._one(prev_comment=" # REVIEWED 2026-09-25: prev is meant to be root")
        self.assertEqual(f.exemption["date"], "2026-09-25")

    def test_reviewed_on_named_scope_line(self):
        f = self._one(root_comment=" # REVIEWED 2026-09-25: deliberate")
        self.assertEqual(f.exemption["rationale"], "deliberate")


class AuditTests(unittest.TestCase):
    def test_audit_walks_common_and_events_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "events"))
            os.makedirs(os.path.join(tmp, "docs", "engine"))
            with open(os.path.join(tmp, "docs", "engine", "event_targets_summary.txt"), "w") as fh:
                fh.write("# header\ncountry|power_bloc|power_bloc|Scope to the power bloc\n")
            with open(os.path.join(tmp, "events", "x.txt"), "w", encoding="utf-8-sig") as fh:
                fh.write(
                    "x.1 = {\n\timmediate = {\n\t\tevery_country = {\n"
                    "\t\t\troot = { power_bloc ?= { add_leverage = { target = prev value = 1 } } }\n"
                    "\t\t}\n\t}\n}\n"
                )
            result = audit(mod_path=tmp)
            self.assertEqual(result.files_audited, 1)
            self.assertEqual(len(result.flags), 1)
            report = render_report(result)
            self.assertIn("events/x.txt", report)
            self.assertIn("- unreviewed: 1", report)

    def test_missing_catalog_still_sees_iterators_and_named_scopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "common", "scripted_effects"))
            with open(os.path.join(tmp, "common", "scripted_effects", "e.txt"), "w") as fh:
                fh.write("e = {\n\tevery_country = {\n\t\tscope:a = { random_state = { x = prev } }\n\t}\n}\n")
            self.assertEqual(len(audit(mod_path=tmp).flags), 1)


if __name__ == "__main__":
    unittest.main()
