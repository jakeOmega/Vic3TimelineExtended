"""Regression tests for building-variable scopes, aliasing, and CI integration."""
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import building_scope_variable_audit as audit


class ScopeTests(unittest.TestCase):
    def scan(self, body):
        return audit.scan_text(body, "common/test.txt", {"owner", "state", "capital"})

    def test_all_building_iterators_and_links(self):
        for scope in sorted(audit.BUILDING_ITERATORS) + ["b:building_settlement_authority"]:
            with self.subTest(scope=scope):
                flags = self.scan(f"effect = {{ {scope} = {{ set_variable = {{ name = x value = 1 }} }} }}")
                self.assertEqual([f.construct for f in flags], ["set_variable"])
                self.assertEqual(flags[0].enclosing_iterator, scope)

    def test_operations_and_variable_lists(self):
        keys = sorted(audit.VARIABLE_KEYS) + [
            "add_to_variable_list", "remove_from_variable_list", "clear_variable_list",
            "is_in_variable_list", "has_variable_list",
        ]
        for key in keys:
            with self.subTest(key=key):
                self.assertEqual([f.construct for f in self.scan(
                    f"e = {{ every_scope_building = {{ {key} = x }} }}"
                )], [key])

    def test_nested_conditions_and_bare_reads(self):
        flags = self.scan("""e = {
 every_scope_building = {
  if = { limit = { var:arrived > 0 } add_modifier = { multiplier = var:arrived } }
  random_list = { 50 = { hidden_effect = { remove_variable = x } } }
  value = { add = { var:a var:b } }
 }
}""")
        self.assertEqual([f.construct for f in flags], [
            "var:arrived", "var:arrived", "remove_variable", "var:a", "var:b",
        ])
        self.assertEqual([f.line for f in flags], [3, 3, 4, 5, 5])
        self.assertTrue(all(f.enclosing_line == 2 for f in flags))

    def test_scope_switches_reset_and_restore(self):
        for scope in ["owner", "state", "root", "ROOT", "prev", "PREV", "this", "capital",
                      "scope:unknown", "scope:site.owner", "b:site.state", "every_scope_country"]:
            with self.subTest(scope=scope):
                flags = self.scan(f"""e = {{ every_scope_building = {{
 {scope} = {{ if = {{ set_variable = x multiplier = var:x }} }}
 has_variable = x
}} }}""")
                self.assertEqual([f.construct for f in flags], ["has_variable"])

    def test_prefixed_reads_and_independent_stores(self):
        self.assertEqual(self.scan("""e = { every_scope_building = {
 root.var:x > 0 owner.var:x > 0 state.var:x > 0 scope:site.var:x > 0
 multiplier = root.var:x
 set_global_variable = x set_local_variable = x
 add_to_global_variable_list = x clear_local_variable_list = x
} }"""), [])

    def test_comments_strings_and_exact_inline_review(self):
        flags = self.scan('''\ufeffe = {
 every_scope_building = {
 # set_variable = x var:x > 0 }
 text = "set_variable = x { var:x } # comment"
 set_variable = x # REVIEWED 2026-10-01: fixture demonstrates a deliberate exemption
 # REVIEWED 2026-10-01: does not suppress the next line
 remove_variable = x
 has_variable = x # REVIEWED 2026-10-01:
 }
}''')
        self.assertEqual([f.line for f in flags], [5, 7, 8])
        self.assertEqual(flags[0].exemption["date"], "2026-10-01")
        self.assertIsNone(flags[1].exemption)
        self.assertIsNone(flags[2].exemption)

    def test_saved_scopes_and_alias_chains(self):
        flags = self.scan("""e = {
 scope:second = { remove_variable = x }
 every_scope_building = {
  save_scope_as = first
  owner = { save_scope_as = country }
 }
 scope:first = { save_temporary_scope_as = second has_variable = x }
 scope:country = { set_variable = x }
 scope:second.state = { set_variable = x }
}""")
        self.assertEqual([f.construct for f in flags], ["remove_variable", "has_variable"])
        self.assertEqual([f.enclosing_iterator for f in flags], ["scope:second", "scope:first"])

    def test_unknown_roots_and_top_level_entities_do_not_leak(self):
        self.assertEqual(self.scan("""a = { every_scope_building = { save_scope_as = site } }
 b = { set_variable = x var:x > 0 }
 c = { state = { every_scope_building = { owner = { set_variable = x } } } }
"""), [])

    def test_original_settlement_authority_regression_and_fix(self):
        broken = """e = { every_scope_building = {
 set_variable = { name = rs_arrived value = root.var:rs_arrived }
 if = { limit = { var:rs_arrived > 0 }
  add_modifier = { name = readout multiplier = var:rs_arrived }
 }
} }"""
        self.assertEqual([f.construct for f in self.scan(broken)], [
            "set_variable", "var:rs_arrived", "var:rs_arrived",
        ])
        fixed = """e = { set_variable = { name = rs_arrived value = 1 }
 every_scope_building = { if = { limit = { root.var:rs_arrived > 0 }
  add_modifier = { name = readout multiplier = root.var:rs_arrived }
 } } }"""
        self.assertEqual(self.scan(fixed), [])


class IntegrationTests(unittest.TestCase):
    def test_cross_file_aliases_and_report_determinism(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "common").mkdir()
            Path(root, "events").mkdir()
            Path(root, "common", "a.txt").write_text(
                "e = { scope:second = { remove_variable = x } }", encoding="utf-8")
            Path(root, "events", "b.txt").write_text(
                "e = { every_scope_building = { save_scope_as = first } }", encoding="utf-8")
            Path(root, "events", "c.txt").write_text(
                "e = { scope:first = { save_scope_as = second } }", encoding="utf-8")
            Path(root, "events", "ignored.md").write_text("set_variable = x", encoding="utf-8")
            result = audit.audit(mod_path=root)
            self.assertEqual(result.files_audited, 3)
            self.assertEqual([(f.file, f.construct) for f in result.flags], [
                (os.path.join("common", "a.txt"), "remove_variable"),
            ])
            self.assertEqual(audit.render_report(result), audit.render_report(audit.audit(mod_path=root)))
            self.assertIn("unreviewed: 1", audit.render_report(result))

    def test_cli_strict_and_post_load_summary(self):
        flags = audit.scan_text(
            "e = { every_scope_building = { has_variable = x } }", "events/a.txt", set())
        with patch.object(audit, "audit", return_value=audit.AuditResult(flags, 1)):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(audit.main([]), 0)
                self.assertEqual(audit.main(["--strict"]), 1)
            with tempfile.TemporaryDirectory() as root:
                with patch("path_constants.mod_path", root):
                    summary = audit.regenerate()
                self.assertEqual(summary, {
                    "files_audited": 1, "total_flags": 1, "unreviewed": 1, "exempted": 0,
                })
                self.assertTrue(Path(root, "docs/engine/building_scope_variable_report.md").is_file())
            flags[0].exemption = {"date": "2026-10-01", "rationale": "fixture"}
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(audit.main(["--strict"]), 0)

    def test_findings_feed_reload_warnings(self):
        with patch.dict(os.environ, {
            "VIC3_BASE_GAME": "/nonexistent", "VIC3_MOD_DEPLOY_TARGET": "/nonexistent",
            "VIC3_VANILLA_REPO": "/nonexistent", "VIC3_VANILLA_DOCS_RUNTIME": "/nonexistent",
            "VIC3_GAME_LOGS": "/nonexistent",
        }):
            import mod_state_server as server
        entry = ("building_scope_variable_audit", "building_scope_variable_audit")
        flags = audit.scan_text(
            "e = { every_scope_building = { has_variable = x } }", "events/a.txt", set())
        with tempfile.TemporaryDirectory() as root:
            with patch("path_constants.mod_path", root), patch.object(
                audit, "audit", return_value=audit.AuditResult(flags, 1)
            ), patch.object(server, "_post_load_warnings", []):
                server._run_generator_chain(None, [entry])
                self.assertEqual(server._post_load_warnings[0]["label"], entry[0])
                self.assertEqual(server._post_load_warnings[0]["counts"], {"unreviewed": 1})

    def test_post_load_roster_and_ci(self):
        from scripts.analysis.check_post_load_rosters import extract_rosters
        root = Path(__file__).resolve().parent
        self.assertIn("building_scope_variable_audit", extract_rosters(
            str(root / "mod_state_server.py"))["POST_LOAD_AUDITS"])
        self.assertIn("python3 building_scope_variable_audit.py --strict",
                      (root / ".github/workflows/ci.yml").read_text())


if __name__ == "__main__":
    unittest.main()
