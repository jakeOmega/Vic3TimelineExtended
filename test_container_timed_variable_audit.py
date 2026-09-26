"""Unit tests for container_timed_variable_audit.

The crux is telling a container's scope from any other: a timed
`set_variable` flags when the scope it runs in uses a container-only command
(`has_tag`, `add_tag`, ...) or when its variable is one the mod reads on a
container elsewhere. A timed variable on a country, a plain `set_variable` on
a container, and a timed variable in a scope change nested inside a container
(`var:actor ?= { }` is the actor, not the container) must not flag.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from container_timed_variable_audit import audit, evaluate, render_report, scan_text

LINKS = {"owner", "capital"}


def _flags(*texts: str):
    scans = [scan_text(t, f"f{i}.txt", LINKS) for i, t in enumerate(texts)]
    return evaluate(scans)


class DetectionTests(unittest.TestCase):
    def test_reproduces_un_resolution_cooldown_bug(self):
        # un_resolution_archive before the fix: the scripted effect's own
        # scope is the resolution, which only its has_tag test gives away.
        flags = _flags(
            "un_resolution_archive = {\n"
            "\tsave_scope_as = un_res_archived\n"
            "\tif = {\n"
            "\t\tlimit = { has_tag = un_topic_expulsion }\n"
            "\t\tset_variable = { name = un_res_cooldown days = long_modifier_time }\n"
            "\t}\n"
            "\telse = {\n"
            "\t\tset_variable = { name = un_res_cooldown days = normal_modifier_time }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual([(f.line, f.name, f.time_key) for f in flags],
                         [(5, "un_res_cooldown", "days"), (8, "un_res_cooldown", "days")])
        self.assertIn("has_tag", flags[0].reason)

    def test_reproduces_mandate_grace_bug(self):
        # un_mandate_try_bind: a country-scoped effect that steps into the
        # container through a saved scope.
        flags = _flags(
            "un_mandate_try_bind = {\n"
            "\tif = {\n"
            "\t\tlimit = { has_variable = un_mandate_current }\n"
            "\t\tscope:un_mandate_binding = {\n"
            "\t\t\tremove_tag = un_mandate_active\n"
            "\t\t\tadd_tag = un_mandate_bound\n"
            "\t\t\tset_variable = { name = un_mnd_grace days = 60 }\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual([(f.line, f.name) for f in flags], [(7, "un_mnd_grace")])

    def test_container_variable_propagates_across_files(self):
        # The set site has no container evidence of its own; the name is read
        # on a container in another file.
        setter = (
            "stamp_it = {\n"
            "\tset_variable = {\n"
            "\t\tname = x_cooldown\n"
            "\t\tmonths = 6\n"
            "\t}\n"
            "}\n"
        )
        reader = (
            "x_on_cooldown = {\n"
            "\tany_in_global_list = {\n"
            "\t\tvariable = x_history\n"
            "\t\thas_tag = x_topic\n"
            "\t\thas_variable = x_cooldown\n"
            "\t}\n"
            "}\n"
        )
        flags = _flags(setter, reader)
        self.assertEqual(len(flags), 1)
        self.assertEqual((flags[0].file, flags[0].line, flags[0].time_key), ("f0.txt", 2, "months"))
        self.assertIn("f1.txt:5", flags[0].reason)

    def test_var_prefix_read_counts_as_container_variable(self):
        flags = _flags(
            "a = { set_variable = { name = y_left years = 1 } }\n",
            "v = { every_in_global_list = { variable = l limit = { has_tag = t } add = var:y_left } }\n",
        )
        self.assertEqual([f.name for f in flags], ["y_left"])

    def test_container_iterator_and_on_created_are_container_scopes(self):
        flags = _flags(
            "a = {\n"
            "\tevery_container = { tag = t set_variable = { name = p days = 5 } }\n"
            "\tcreate_container = {\n"
            "\t\ttags = { t }\n"
            "\t\ton_created = { set_variable = { name = q weeks = 2 } }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(sorted(f.name for f in flags), ["p", "q"])


class NonFlagTests(unittest.TestCase):
    def test_timed_variable_on_a_country_is_not_flagged(self):
        self.assertEqual(_flags(
            "e = {\n"
            "\tevery_country = {\n"
            "\t\tlimit = { has_variable = z }\n"
            "\t\tset_variable = { name = z days = 365 }\n"
            "\t}\n"
            "}\n"
        ), [])

    def test_plain_variable_on_a_container_is_not_flagged(self):
        self.assertEqual(_flags(
            "e = { add_tag = t set_variable = { name = n value = 3 } change_variable = { name = n add = 1 } }\n"
        ), [])

    def test_scope_change_inside_a_container_is_its_own_scope(self):
        # The actor is a country: its timed variable does expire.
        self.assertEqual(_flags(
            "e = {\n"
            "\thas_tag = un_mandate_bound\n"
            "\tvar:un_mnd_actor ?= { set_variable = { name = actor_cd days = 30 } }\n"
            "}\n"
        ), [])

    def test_names_read_outside_a_container_do_not_propagate(self):
        self.assertEqual(_flags(
            "a = { set_variable = { name = w days = 5 } }\n",
            "b = { has_variable = w owner = { has_tag = t } }\n",
        ), [])

    def test_comments_and_strings_are_ignored(self):
        self.assertEqual(_flags(
            "e = {\n"
            "\t# add_tag = t\n"
            "\tcustom_tooltip = \"has_tag = t\"\n"
            "\tset_variable = { name = s days = 5 }\n"
            "}\n"
        ), [])


class ExemptionTests(unittest.TestCase):
    TEXT = (
        "e = {{\n"
        "\tadd_tag = t\n"
        "\tset_variable = {{ name = s days = 5 }}{on_set}\n"
        "\tset_variable = {{\n"
        "\t\tname = u\n"
        "\t\tdays = 5{on_days}\n"
        "\t}}\n"
        "}}\n"
    )

    def test_unreviewed(self):
        flags = _flags(self.TEXT.format(on_set="", on_days=""))
        self.assertEqual([f.exemption for f in flags], [None, None])

    def test_reviewed_on_set_line_and_on_duration_line(self):
        note = " # REVIEWED 2026-09-25: a test"
        flags = _flags(self.TEXT.format(on_set=note, on_days=note))
        self.assertEqual([f.exemption["rationale"] for f in flags], ["a test", "a test"])


class AuditTests(unittest.TestCase):
    def test_audit_walks_common_and_events_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "common", "scripted_effects"))
            os.makedirs(os.path.join(tmp, "events"))
            with open(os.path.join(tmp, "common", "scripted_effects", "a.txt"), "w", encoding="utf-8-sig") as fh:
                fh.write("a = { add_tag = t set_variable = { name = k days = 9 } }\n")
            with open(os.path.join(tmp, "events", "b.txt"), "w", encoding="utf-8") as fh:
                fh.write("b.1 = { immediate = { set_variable = { name = k2 days = 9 } } }\n")
            result = audit(mod_path=tmp)
            self.assertEqual(result.files_audited, 2)
            self.assertEqual([f.name for f in result.flags], ["k"])
            report = render_report(result)
            self.assertIn("`set_variable` of `k` with `days`", report)
            self.assertIn("- unreviewed: 1", report)


if __name__ == "__main__":
    unittest.main()
