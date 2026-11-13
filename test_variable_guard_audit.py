"""Unit tests for variable_guard_audit (issue #1053).

The crux is discrimination: flag a `has_variable = X` guard only where it is a
direct child of a `NOT` / `NAND` / `NOR` that also reads X bare. A guard in a
`trigger_if` limit, a `?=` read, an `AND` or top-level sibling, and another
object's variable must not produce flags.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from variable_guard_audit import (
    AuditResult,
    Flag,
    Read,
    audit,
    load_scope_links,
    render_report,
    scan_text,
)

LINKS = {"owner", "capital"}


def _scan(text: str, links=LINKS):
    return scan_text(text, "test.txt", links)


class FlaggedShapes(unittest.TestCase):
    def test_multi_child_not(self):
        # The seabed lease start, as it logged `Failed to fetch variable` on
        # 2026-10-18 (#1052).
        flags = _scan(
            "x = {\n"
            "\tNOT = {\n"
            "\t\thas_variable = te_seabed_lease_n_$B$\n"
            "\t\tvar:te_seabed_lease_n_$B$ > 0\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        flag = flags[0]
        self.assertEqual((flag.line, flag.block), (2, "NOT"))
        self.assertEqual(flag.guard, "has_variable = te_seabed_lease_n_$B$")
        self.assertEqual(flag.guard_line, 3)
        self.assertEqual(flag.variable, "var:te_seabed_lease_n_$B$")
        self.assertEqual([(r.line, r.text) for r in flag.reads],
                         [(4, "var:te_seabed_lease_n_$B$ > 0")])
        self.assertIsNone(flag.exemption)

    def test_nand_and_nor(self):
        for key in ("NAND", "NOR"):
            with self.subTest(key=key):
                flags = _scan(f"x = {{ {key} = {{ has_variable = v var:v = 1 }} }}\n")
                self.assertEqual([(f.block, f.variable) for f in flags], [(key, "var:v")])

    def test_lower_case_block(self):
        self.assertEqual(len(_scan("x = { nand = { has_variable = v var:v = 1 } }\n")), 1)

    def test_read_one_level_down_inside_an_and(self):
        flags = _scan(
            "x = {\n"
            "\tNOT = {\n"
            "\t\thas_variable = v\n"
            "\t\tAND = {\n"
            "\t\t\tvar:v > 0\n"
            "\t\t\tis_ai = yes\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].line, 2)
        self.assertEqual(flags[0].reads[0].line, 5)

    def test_global_and_local_forms(self):
        flags = _scan(
            "x = {\n"
            "\tNOR = { has_global_variable = g global_var:g > 2 }\n"
            "\tNAND = { has_local_variable = l local_var:l = 1 }\n"
            "}\n"
        )
        self.assertEqual([(f.guard, f.variable) for f in flags],
                         [("has_global_variable = g", "global_var:g"),
                          ("has_local_variable = l", "local_var:l")])

    def test_read_on_the_right_or_as_a_value_or_scope(self):
        for read in ("gold_reserves > var:v", "value = var:v", "var:v = { is_ai = yes }",
                     "exists = var:v", "var:v.owner = root"):
            with self.subTest(read=read):
                flags = _scan(f"x = {{ NAND = {{ has_variable = v {read} }} }}\n")
                self.assertEqual(len(flags), 1)

    def test_read_inside_an_inline_script_value(self):
        flags = _scan("x = { NOR = { has_variable = v gdp > { value = var:v multiply = 2 } } }\n")
        self.assertEqual(len(flags), 1)

    def test_two_variables_in_one_block_are_two_flags(self):
        # te_tax_can_accept_offer's "not committed" test before this audit.
        flags = _scan(
            "x = {\n"
            "\tNAND = {\n"
            "\t\thas_variable = te_tax_com_$IG$\n"
            "\t\thas_variable = te_tax_com_$IG$_rev\n"
            "\t\tvar:te_tax_com_$IG$ = 1\n"
            "\t\tvar:te_tax_com_$IG$_rev = var:te_tax_bl_rev\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual([f.variable for f in flags],
                         ["var:te_tax_com_$IG$", "var:te_tax_com_$IG$_rev"])
        self.assertEqual([len(f.reads) for f in flags], [1, 1])

    def test_global_read_behind_a_scope_change_still_counts(self):
        flags = _scan("x = { NOR = { has_global_variable = g owner = { global_var:g > 0 } } }\n")
        self.assertEqual(len(flags), 1)

    def test_this_is_the_current_scope(self):
        for read in ("this.var:v > 0", "this = { var:v > 0 }", "THIS.var:v > 0"):
            with self.subTest(read=read):
                self.assertEqual(len(_scan(f"x = {{ NAND = {{ has_variable = v {read} }} }}\n")), 1)
        # Once: the head read and the chain read are the same one.
        flags = _scan("x = { NAND = { has_global_variable = g this.global_var:g > 0 } }\n")
        self.assertEqual([len(f.reads) for f in flags], [1])

    def test_an_or_does_not_guard_its_siblings(self):
        # `OR = { has_variable = v  var:v > 0 }` reads v whether or not it is
        # set, so the outer block's guard is still the only one, and useless.
        flags = _scan("x = {\n\tNOR = {\n\t\thas_variable = v\n"
                      "\t\tOR = { has_variable = v var:v > 0 }\n\t}\n}\n")
        self.assertEqual([(f.line, f.reads[0].line) for f in flags], [(2, 4)])

    def test_a_limit_above_a_scope_change_guards_another_object(self):
        # The country's `v` is set; the state's is what the NAND reads.
        flags = _scan("x = { if = { limit = { has_variable = v } "
                      "capital = { set_x = { limit = { NAND = { has_variable = v var:v > 0 } } } } } }\n")
        self.assertEqual(len(flags), 1)
        flags = _scan("x = { trigger_if = { limit = { has_variable = v } "
                      "any_scope_state = { NAND = { has_variable = v var:v > 0 } } } }\n")
        self.assertEqual(len(flags), 1)
        # A global has no scope: the limit still guards it.
        self.assertEqual(_scan(
            "x = { trigger_if = { limit = { has_global_variable = g } "
            "owner = { NAND = { has_global_variable = g global_var:g > 0 } } } }\n"), [])
        # And a limit inside the scope change is that object's own.
        self.assertEqual(_scan(
            "x = { owner = { trigger_if = { limit = { has_variable = v } "
            "NAND = { has_variable = v var:v > 0 } } } }\n"), [])

    def test_a_safe_read_does_not_hide_a_bare_one(self):
        flags = _scan("x = { NOR = { has_variable = v var:v ?= 1 var:v > 3 } }\n")
        self.assertEqual(len(flags), 1)
        self.assertEqual([r.text for r in flags[0].reads], ["var:v > 3"])


class UnflaggedShapes(unittest.TestCase):
    def assertClean(self, text: str):
        self.assertEqual(_scan(text), [])

    def test_single_child_not(self):
        self.assertClean("x = { NOT = { has_variable = v } }\n")
        self.assertClean("x = { NOT = { var:v > 0 } }\n")

    def test_guard_in_an_enclosing_trigger_if_limit(self):
        # The fix the guide gives.
        self.assertClean(
            "x = {\n"
            "\ttrigger_if = {\n"
            "\t\tlimit = { has_variable = v }\n"
            "\t\tNOT = { var:v > 0 }\n"
            "\t}\n"
            "}\n"
        )

    def test_redundant_inner_guard_under_a_trigger_if_limit(self):
        for key in ("trigger_if", "trigger_else_if", "if", "else_if"):
            with self.subTest(key=key):
                self.assertClean(
                    f"x = {{ {key} = {{ limit = {{ has_variable = v }} "
                    "NAND = { has_variable = v var:v > 0 } } }\n"
                )

    def test_a_limit_does_not_guard_itself(self):
        # The NAND is the limit's own child: nothing has been tested yet.
        flags = _scan("x = { trigger_if = { limit = { is_ai = yes NAND = { has_variable = v var:v > 0 } } } }\n")
        self.assertEqual(len(flags), 1)

    def test_a_trigger_else_is_not_guarded(self):
        flags = _scan(
            "x = { trigger_if = { limit = { has_variable = v } always = yes } "
            "trigger_else = { NOR = { has_variable = v var:v > 0 } } }\n"
        )
        self.assertEqual(len(flags), 1)

    def test_null_safe_read(self):
        self.assertClean("x = { NOR = { has_variable = v var:v ?= 1 } }\n")
        self.assertClean("x = { NAND = { has_variable = v var:v ?= { is_ai = yes } } }\n")

    def test_and_and_top_level_siblings(self):
        # The mod's ordinary idiom: this audit leaves it alone.
        self.assertClean("x = { has_variable = v var:v > 0 }\n")
        self.assertClean("x = { AND = { has_variable = v var:v > 0 } }\n")
        self.assertClean("x = { OR = { is_ai = yes AND = { has_variable = v var:v > 0 } } }\n")

    def test_guard_and_read_together_one_level_down(self):
        self.assertClean("x = { NOT = { AND = { has_variable = v var:v > 0 } } }\n")
        self.assertClean("x = { NAND = { is_ai = yes AND = { has_variable = v var:v > 0 } } }\n")

    def test_read_guarded_again_further_in(self):
        self.assertClean("x = { NOR = { has_variable = v AND = { has_variable = v var:v > 0 } } }\n")
        self.assertClean(
            "x = { NOR = { has_variable = v "
            "trigger_if = { limit = { has_variable = v } var:v > 0 } } }\n"
        )

    def test_another_objects_variable(self):
        self.assertClean("x = { NOR = { has_variable = v owner = { var:v > 0 } } }\n")
        self.assertClean("x = { NOR = { has_variable = v any_scope_state = { var:v > 0 } } }\n")
        self.assertClean("x = { NOR = { has_variable = v scope:target = { var:v > 0 } } }\n")
        self.assertClean("x = { NOR = { has_variable = v owner.var:v > 0 } }\n")
        self.assertClean("x = { NOR = { has_variable = v scope:target.var:v > 0 } }\n")

    def test_a_different_variable(self):
        self.assertClean("x = { NAND = { has_variable = v var:v_rev > 0 } }\n")
        self.assertClean("x = { NAND = { has_variable = v_rev var:v > 0 } }\n")
        self.assertClean("x = { NAND = { has_variable = v global_var:v > 0 } }\n")
        self.assertClean("x = { NAND = { has_global_variable = v var:v > 0 } }\n")

    def test_guard_alone_beside_other_conditions(self):
        self.assertClean("x = { NOR = { has_variable = v has_variable = w is_ai = yes } }\n")

    def test_comments_and_strings(self):
        self.assertClean("x = {\n\t# NOT = { has_variable = v var:v > 0 }\n\tis_ai = yes\n}\n")
        self.assertClean('x = { NOR = { has_variable = v text = "var:v > 0" } }\n')

    def test_not_a_negating_block(self):
        self.assertClean("x = { NOT_this = { has_variable = v var:v > 0 } }\n")


class SuppressionTests(unittest.TestCase):
    TEXT = (
        "x = {{\n"
        "\tNAND = {{{comment}\n"
        "\t\thas_variable = v\n"
        "\t\tvar:v > 0\n"
        "\t}}\n"
        "}}\n"
    )

    def test_tagged_review_on_the_opening_line(self):
        flags = _scan(self.TEXT.format(
            comment=" # REVIEWED 2026-11-12 (variable_guard): a verbatim vanilla copy"))
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].exemption,
                         {"date": "2026-11-12", "tag": "variable_guard", "rationale": "a verbatim vanilla copy"})

    def test_one_line_block(self):
        flags = _scan("x = { NAND = { has_variable = v var:v > 0 } "
                      "# REVIEWED 2026-11-12 (other_check, variable_guard): why\n}\n")
        self.assertIsNotNone(flags[0].exemption)

    def test_untagged_or_other_tag_does_not_suppress(self):
        for comment in (" # REVIEWED 2026-11-12: untagged",
                        " # REVIEWED 2026-11-12 (silent_variable): another audit's",
                        " # REVIEWED (variable_guard): no date",
                        " # variable_guard"):
            with self.subTest(comment=comment):
                self.assertIsNone(_scan(self.TEXT.format(comment=comment))[0].exemption)

    def test_review_elsewhere_does_not_suppress(self):
        flags = _scan(
            "x = {\n"
            "\tNAND = {\n"
            "\t\thas_variable = v # REVIEWED 2026-11-12 (variable_guard): wrong line\n"
            "\t\tvar:v > 0\n"
            "\t}\n"
            "}\n"
        )
        self.assertIsNone(flags[0].exemption)


class SuggestionTests(unittest.TestCase):
    WRAPPED = ("`trigger_if = { limit = { has_variable = v } NAND = { <the block's other conditions> } }` "
               "(`NOT` if one condition is left; passes when unset)")

    def suggestion(self, block: str) -> str:
        return _scan(f"x = {{ {block} }}\n")[0].suggestion

    def test_equality_with_a_number_offers_the_null_safe_read(self):
        for read in ("var:v = 1", "var:v = -2", "var:v = 0.5"):
            with self.subTest(read=read):
                text = self.suggestion(f"NAND = {{ has_variable = v {read} }}")
                self.assertIn("read it as `var:v ?= <number>` and drop the guard", text)
                self.assertIn(self.WRAPPED, text)

    def test_equality_with_anything_else_does_not(self):
        # `?=` guards its left side only, and with a `var:` or a `flag:` on the
        # right it is unverified (scripting_best_practices.md, "Triggered
        # Option Names"). On main's script this audit once suggested it for
        # both of these, and one reached a pull request.
        for read in ("var:v = var:te_tax_bl_rev", "var:v = flag:rededicate", "var:v = scope:target",
                     "var:v = some_script_value", "var:v = global_var:g", "var:v = root",
                     "var:v = yes", "var:v = { value = 1 }"):
            with self.subTest(read=read):
                text = self.suggestion(f"NAND = {{ has_variable = v {read} }}")
                self.assertNotIn("?=", text)
                self.assertIn(self.WRAPPED, text)

    def test_one_read_that_is_not_a_numeric_equality_withholds_it(self):
        text = self.suggestion("NAND = { has_variable = v var:v = 1 has_variable = w var:w = var:v }")
        self.assertNotIn("?=", text)

    def test_inequality_offers_the_trigger_if_only(self):
        flag = _scan("x = { NAND = { has_global_variable = g global_var:g > 0 } }\n")[0]
        self.assertNotIn("?=", flag.suggestion)
        self.assertIn("trigger_if = { limit = { has_global_variable = g } NAND = { "
                      "<the block's other conditions> } }", flag.suggestion)

    def test_the_rest_of_the_block_stays_inside_the_negation(self):
        # Followed literally, "NOT = { <the read> }" would drop `is_ai = yes`.
        for block in ("NAND = { has_variable = v var:v > 0 is_ai = yes }",
                      "NOT = { has_variable = v var:v = 1 is_ai = yes }"):
            with self.subTest(block=block):
                text = self.suggestion(block)
                self.assertIn("keep the rest of the block inside the negation", text)
                self.assertNotIn("<the read>", text)
        self.assertIn("leaving the block's other conditions where they are",
                      self.suggestion("NOT = { has_variable = v var:v = 1 is_ai = yes }"))

    def test_a_nor_is_not_given_a_mechanical_rewrite(self):
        # NOR = { has_variable = v  var:v = 1 } is "v is unset and …": no
        # rewrite keeps a meaning the author can have wanted.
        text = self.suggestion("NOR = { has_variable = v var:v = 1 }")
        self.assertTrue(text.startswith("as `NOR` this is false whenever the variable is set"))
        self.assertNotIn("?=", text)
        self.assertIn(self.WRAPPED, text)


class AuditAndReportTests(unittest.TestCase):
    BAD = "x = {\n\tNOT = {\n\t\thas_variable = v\n\t\tvar:v > 0\n\t}\n}\n"

    def test_walks_common_and_events_and_renders_report(self):
        with tempfile.TemporaryDirectory() as td:
            for sub in (("common", "scripted_triggers"), ("events",), ("gui",)):
                folder = os.path.join(td, *sub)
                os.makedirs(folder)
                with open(os.path.join(folder, "a.txt"), "w", encoding="utf-8-sig") as fh:
                    fh.write(self.BAD)
            with open(os.path.join(td, "events", "notes.md"), "w", encoding="utf-8") as fh:
                fh.write(self.BAD)

            result = audit(mod_path=td)
            self.assertEqual(result.files_audited, 2)  # not gui/, not the .md
            self.assertEqual(sorted(f.file for f in result.flags),
                             ["common/scripted_triggers/a.txt", "events/a.txt"])

            report = render_report(result)
            self.assertIn("# Variable guard audit report", report)
            self.assertIn("### `events/a.txt`", report)
            self.assertIn("- line 2: `NOT` holds `has_variable = v` beside `var:v > 0` (line 4). "
                          "Fix: move the guard into a limit", report)
            self.assertIn("- unreviewed: 2", report)

    def test_scope_links_come_from_the_catalog(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "docs", "engine"))
            with open(os.path.join(td, "docs", "engine", "event_targets_summary.txt"),
                      "w", encoding="utf-8") as fh:
                fh.write("# header\n\nstate|owner|country|Scope to the owner\n"
                         "country|army_size|value|Number of battalions\n")
            self.assertEqual(load_scope_links(td), {"owner"})
            folder = os.path.join(td, "events")
            os.makedirs(folder)
            with open(os.path.join(folder, "a.txt"), "w", encoding="utf-8") as fh:
                fh.write("x = { NOR = { has_variable = v owner = { var:v > 0 } } }\n"
                         "y = { NOR = { has_variable = v army_size > { value = var:v } } }\n")
            self.assertEqual([f.line for f in audit(mod_path=td).flags], [2])

    def test_no_catalog_still_knows_iterators_and_named_scopes(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(load_scope_links(td), set())
        self.assertEqual(
            _scan("x = { NOR = { has_variable = v any_scope_state = { var:v > 0 } } }\n", links=set()), [])

    def test_report_reports_none_when_clean(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "events"))
            report = render_report(audit(mod_path=td))
            self.assertIn("_None._", report)
            self.assertIn("- total flags: 0", report)

    def test_report_carries_no_volatile_numbers(self):
        """A reviewed entry prints no line number and Coverage no file count,
        so the report changes only when the findings do."""
        result = AuditResult(flags=[
            Flag("events/x.txt", 4, "NOT", "has_variable = v", 5, "var:v",
                 [Read(6, "var:v > 0", False)]),
            Flag("events/y.txt", 44, "NAND", "has_variable = w", 45, "var:w",
                 [Read(46, "var:w = 1", True)],
                 exemption={"date": "2026-06-01", "rationale": "a vanilla copy"}),
        ], files_audited=162)
        report = render_report(result)
        self.assertIn("- `events/y.txt` — `NAND` with `has_variable = w` — "
                      "**2026-06-01**: a vanilla copy", report)
        self.assertNotIn("44", report)
        self.assertIn("- line 4: `NOT` holds `has_variable = v`", report)
        self.assertNotIn("162", report)


class ModIsCleanTest(unittest.TestCase):
    """The audit runs `--strict` in CI; this names the sites when it fails."""

    def test_no_unreviewed_flag_in_the_mod(self):
        root = os.path.dirname(os.path.abspath(__file__))
        result = audit(mod_path=root)
        self.assertGreater(result.files_audited, 500)
        unreviewed = [f"{f.file}:{f.line} {f.block} {f.guard}"
                      for f in result.flags if not f.exemption]
        self.assertEqual(unreviewed, [])


if __name__ == "__main__":
    unittest.main()
