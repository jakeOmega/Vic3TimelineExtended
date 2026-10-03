"""JE-scope regression cases, transitive resolution and CI behavior (#677)."""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import je_multiplier_scope_audit as audit_module
from je_multiplier_scope_audit import (
    AuditResult, audit, load_country_triggers, main, parse_text, render_report, scan_nodes,
)

REPO = Path(__file__).resolve().parent
COUNTRY_READS = load_country_triggers(str(REPO))
LINKS = {"owner", "state", "country", "capital"}


def scan(text: str, values: str = ""):
    nodes, comments = parse_text(text, "effects.txt")
    definitions, _ = parse_text(values, "values.txt")
    return scan_nodes(nodes, comments, {n.key: n for n in definitions}, COUNTRY_READS, LINKS)


def je_modifier(multiplier: str, scope: str = "je:je_banking_cycle", extra: str = ""):
    return (f"effect = {{ {scope} ?= {{ if = {{ hidden_effect = {{\n"
            f"add_modifier = {{ name = m multiplier = {multiplier} {extra} }}\n"
            "} } } }")


class DetectionTests(unittest.TestCase):
    def test_engine_scope_metadata_includes_numeric_accessors(self):
        self.assertTrue({"gdp", "income", "total_expenses", "investment_pool_net_income"}
                        <= COUNTRY_READS)
        self.assertNotIn("global_gdp", COUNTRY_READS)
        self.assertNotIn("modifier", COUNTRY_READS)
        self.assertNotIn("always", COUNTRY_READS)

    def test_reproduces_fiscal_policy(self):
        flags = scan(je_modifier("fiscal"), """fiscal = {
value = total_expenses
subtract = income
multiply = annualisation
divide = { value = gdp min = 1 }
multiply = 10 min = -1 max = 1
}
annualisation = 52
""")
        self.assertEqual([f.read for f in flags], ["total_expenses", "income", "gdp"])
        self.assertTrue(all(f.line == 2 and f.modifier == "m" for f in flags))
        self.assertEqual(flags[-1].read_line, 5)
        self.assertEqual(flags[-1].read_file, "values.txt")
        self.assertEqual(flags[-1].chain, ("fiscal",))

    def test_reproduces_command_economy(self):
        flags = scan(je_modifier("ce_balance"),
                     "ce_balance = { value = 0 subtract = investment_pool_net_income }")
        self.assertEqual([f.read for f in flags], ["investment_pool_net_income"])

    def test_reproduces_inline_un_benefits(self):
        flags = scan(je_modifier("{ value = global_var:un_authority divide = 50 "
                                 "multiply = { value = 1 add = modifier:country_un_institutional_alignment } }",
                                 scope="je:je_united_nations"))
        self.assertEqual([f.read for f in flags], ["modifier:country_un_institutional_alignment"])
        self.assertEqual(flags[0].journal_entry, "je:je_united_nations")
        self.assertEqual(flags[0].chain, ())

    def test_country_only_condition_and_trigger_arguments(self):
        flags = scan(je_modifier("conditional"), """conditional = {
if = { limit = { total_expenses > 100 has_law = law_type:law_command_economy }
add = 1 }
}""")
        self.assertEqual([f.read for f in flags], ["total_expenses", "has_law"])

    def test_transitive_values_and_scripted_triggers(self):
        flags = scan(je_modifier("outer"), """outer = { add = middle }
middle = { if = { limit = { country_condition = yes } add = leaf } }
country_condition = { investment_pool_net_income > 0 }
leaf = gdp
""")
        self.assertEqual([f.read for f in flags], ["investment_pool_net_income", "gdp"])
        self.assertEqual(flags[0].chain, ("outer", "middle", "country_condition"))
        self.assertEqual(flags[1].chain, ("outer", "middle", "leaf"))

    def test_cyclic_values_terminate_without_hiding_reads(self):
        flags = scan(je_modifier("a"), """a = { add = b }
b = { add = a add = gdp }
""")
        self.assertEqual([f.read for f in flags], ["gdp"])

    def test_this_does_not_leave_je_scope(self):
        self.assertEqual([f.read for f in scan(je_modifier("this.gdp"))], ["this.gdp"])
        flags = scan(je_modifier("sv"), "sv = { this = { add = income } }")
        self.assertEqual([f.read for f in flags], ["income"])

    def test_owner_wrapper_and_qualified_reads_are_safe(self):
        for mult in ("wrapper", "owner.gdp", "root.income", "root.var:cached", "var:cached",
                     "global_var:un_authority", "0", "-1", "0.5"):
            with self.subTest(mult=mult):
                self.assertEqual(scan(je_modifier(mult),
                                      "wrapper = { value = 0 owner = { add = country_value } } "
                                      "country_value = { value = income divide = gdp }"), [])

    def test_scoped_wrapper_does_not_protect_unscoped_sibling_read(self):
        flags = scan(je_modifier("sv"), "sv = { owner = { add = gdp } add = income }")
        self.assertEqual([f.read for f in flags], ["income"])

    def test_same_value_used_in_country_and_je_context(self):
        text = je_modifier("sv", scope="owner") + "\n" + je_modifier("sv")
        flags = scan(text, "sv = { add = gdp }")
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].line, 5)

    def test_scope_exit_then_reentry(self):
        flags = scan("""effect = {
je:outer = {
owner = { add_modifier = { name = safe multiplier = gdp }
je:inner = { add_modifier = { name = unsafe multiplier = income } } }
add_modifier = { name = unsafe_again multiplier = gdp }
}
}""")
        self.assertEqual([(f.modifier, f.journal_entry) for f in flags],
                         [("unsafe", "je:inner"), ("unsafe_again", "je:outer")])

    def test_timed_modifiers_also_fail(self):
        self.assertEqual(len(scan(je_modifier("gdp", extra="months = 12"))), 1)

    def test_multiple_modifiers_and_multipliers_keep_source_order(self):
        flags = scan("""effect = { je:entry = {
add_modifier = { name = one multiplier = income }
add_modifier = { name = two multiplier = { add = gdp add = total_expenses } }
} }""")
        self.assertEqual([(f.modifier, f.line) for f in flags],
                         [("one", 2), ("two", 3), ("two", 3)])

    def test_comments_and_strings_cannot_create_reads(self):
        self.assertEqual(scan('effect = { desc = "je:entry = { add_modifier = { multiplier = gdp } }"\n'
                              '# je:entry = { add_modifier = { multiplier = gdp } }\n}'), [])

    def test_reviewed_suppression_only_on_multiplier_line(self):
        text = """effect = { je:entry = { add_modifier = {
name = m
multiplier = gdp # REVIEWED 2026-10-03: deliberate probe
} } }"""
        self.assertEqual(scan(text)[0].exemption,
                         {"date": "2026-10-03", "rationale": "deliberate probe"})
        for changed in (text.replace("2026-10-03:", ""),
                        text.replace(" # REVIEWED", "\n# REVIEWED")):
            self.assertIsNone(scan(changed)[0].exemption)


class IntegrationTests(unittest.TestCase):
    def test_cross_file_resolution_and_missing_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for rel, text in {
                "docs/engine/triggers_parsed.txt": "## total_expenses\nScopes: country\n",
                "docs/engine/event_targets_summary.txt": "country|income|value|Income\n",
                "common/script_values/a.txt": "a = { add = b }",
                "common/script_values/b.txt": "b = { value = income }",
                "common/scripted_buttons/button.txt": je_modifier("a"),
                "events/event.txt": je_modifier("income"),
            }.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8-sig")
            result = audit(mod_path=str(root))
            self.assertEqual(result.files_audited, 4)
            self.assertEqual(len(result.flags), 2)
            self.assertEqual(result.flags[0].read_file, "common/script_values/b.txt")
            self.assertEqual(result.flags[0].chain, ("a", "b"))
            (root / "docs/engine/triggers_parsed.txt").unlink()
            with self.assertRaises(FileNotFoundError):
                audit(mod_path=str(root))

    def test_report_and_strict_exit(self):
        flags = scan(je_modifier("gdp"))
        report = render_report(AuditResult(flags, 1))
        self.assertIn("effects.txt:2", report)
        self.assertIn("`gdp`", report)
        self.assertIn("- unreviewed: 1", report)
        for result, expected in ((AuditResult(flags), 1), (AuditResult(), 0)):
            with patch.object(audit_module, "audit", return_value=result), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--strict"]), expected)
                self.assertEqual(main([]), 0)
        flags[0].exemption = {"date": "2026-10-03", "rationale": "intentional"}
        with patch.object(audit_module, "audit", return_value=AuditResult(flags)), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--strict"]), 0)
        self.assertIn("**2026-10-03**: intentional", render_report(AuditResult(flags)))

    def test_repository_has_no_unsafe_je_multipliers(self):
        self.assertEqual(audit(mod_path=str(REPO)).flags, [])


if __name__ == "__main__":
    unittest.main()
