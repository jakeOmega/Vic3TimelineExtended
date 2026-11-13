"""`audit_registry.py` is the one roster of the audits: hold it to the files on
disk, to the server's reload roster, to the generated page and to CI."""
import ast
import os
import re
import unittest

import audit_registry
from scripts.analysis.check_post_load_rosters import extract_rosters

ROOT = os.path.dirname(os.path.abspath(__file__))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class RosterTests(unittest.TestCase):
    def test_every_audit_file_is_registered(self):
        on_disk = {
            name[:-3] for name in os.listdir(ROOT)
            if name.endswith("_audit.py") and not name.startswith("test_")
        }
        self.assertEqual(
            on_disk, set(audit_registry.BY_NAME),
            "audit_registry.AUDITS and the *_audit.py files at the repo root differ",
        )

    def test_names_are_unique(self):
        self.assertEqual(len(audit_registry.AUDITS), len(audit_registry.BY_NAME))

    def test_reload_roster_matches_the_server(self):
        server = extract_rosters(os.path.join(ROOT, "mod_state_server.py"))["POST_LOAD_AUDITS"]
        self.assertEqual(
            {a.name for a in audit_registry.post_load_audits()}, set(server),
            "an audit's `post_load` disagrees with POST_LOAD_AUDITS in mod_state_server.py",
        )

    def test_every_audit_runs_somewhere(self):
        for audit in audit_registry.AUDITS:
            self.assertTrue(audit.ci is not None or audit.post_load, audit.name)

    def test_ci_arguments_are_ones_the_audit_takes(self):
        for audit in audit_registry.ci_audits():
            source = read(f"{audit.name}.py")
            for arg in audit.ci:
                # `audit_common.cli_main` gives an audit its `--strict`.
                if arg == "--strict" and "cli_main(" in source:
                    continue
                self.assertIn(f'"{arg}"', source, f"{audit.name} does not define {arg}")

    def test_builds_mod_state_matches_the_source(self):
        """`builds_mod_state` is what python_tools.md counts the pure file scans
        from: an audit that calls `ModState(...)` or `cli_mod_state()` builds one."""
        builders = {"ModState", "cli_mod_state"}
        for audit in audit_registry.AUDITS:
            tree = ast.parse(read(f"{audit.name}.py"))
            calls = {
                node.func.id if isinstance(node.func, ast.Name) else node.func.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))
            }
            self.assertEqual(
                audit.builds_mod_state, bool(calls & builders),
                f"{audit.name}: `builds_mod_state` disagrees with whether it calls "
                "ModState( or cli_mod_state(",
            )

    def test_reports_named_exist(self):
        tracked = set(os.listdir(os.path.join(ROOT, "docs", "engine")))
        for audit in audit_registry.AUDITS:
            if audit.report_path:
                self.assertIn(os.path.basename(audit.report_path), tracked, audit.name)


class SuppressionTests(unittest.TestCase):
    def test_tags_are_ones_the_audit_reads(self):
        """A tag the registry names must appear in the audit's source, and a
        tagged form the audit documents must be in the registry."""
        for audit in audit_registry.AUDITS:
            source = read(f"{audit.name}.py")
            for tag in filter(None, audit.tags):
                self.assertIn(tag, source, f"{audit.name}: tag ({tag}) is not in its source")
            documented = set(re.findall(r"REVIEWED YYYY-MM-DD \(([a-z_]+)\)", source))
            self.assertLessEqual(
                documented, set(audit.tags),
                f"{audit.name} documents a tag the registry leaves out",
            )

    def test_an_audit_with_no_reviewed_parser_takes_no_comment(self):
        for audit in audit_registry.AUDITS:
            reads_reviewed = "REVIEWED" in read(f"{audit.name}.py")
            self.assertEqual(
                audit.where is not None, reads_reviewed,
                f"{audit.name}: `where` and the audit's REVIEWED handling disagree",
            )

    def test_hint_names_the_comment_and_the_place(self):
        hint = audit_registry.suppression_hint("silent_variable_audit")
        self.assertIn("# REVIEWED YYYY-MM-DD (silent_variable): why", hint)
        self.assertIn("anywhere inside the option", hint)
        self.assertIn("takes no suppression", audit_registry.suppression_hint("gui_reference_audit"))
        self.assertEqual(audit_registry.suppression_hint("no_such_audit"), "")

    def test_plain_and_tagged_forms(self):
        self.assertEqual(audit_registry.get("any_limit_audit").comment_forms,
                         ("# REVIEWED YYYY-MM-DD: why",))
        self.assertEqual(audit_registry.get("treaty_leverage_side_audit").comment_forms,
                         ("# REVIEWED YYYY-MM-DD: why", "# REVIEWED YYYY-MM-DD (involvement): why"))
        self.assertEqual(audit_registry.get("gui_reference_audit").comment_forms, ())


class GeneratedPageTests(unittest.TestCase):
    def test_page_is_current(self):
        self.assertEqual(
            read(audit_registry.DOC_PATH), audit_registry.render_markdown(),
            "docs/guides/audits.md is stale: run `python3 audit_registry.py --write`",
        )

    def test_page_lists_every_audit_three_times(self):
        page = audit_registry.render_markdown()
        for audit in audit_registry.AUDITS:
            self.assertEqual(page.count(f"| `{audit.name}` |"), 3, audit.name)


class ToolsDocTests(unittest.TestCase):
    """python_tools.md spells out figures from the registry (#1695)."""

    def setUp(self):
        self.text = read(audit_registry.TOOLS_DOC_PATH)

    def test_tools_doc_agrees_with_the_registry(self):
        fixed, problems = audit_registry.check_tools_doc(self.text)
        self.assertEqual(problems, [], "run `python3 audit_registry.py --write`")
        self.assertEqual(fixed, self.text)

    def test_a_figure_one_short_is_named_and_corrected(self):
        """Two PRs that each add an audit both write the same figure; the merged
        text is one short and nothing conflicts."""
        n = len(audit_registry.post_load_audits())
        right = f"`POST_LOAD_AUDITS` (the {n} read-only audits)"
        self.assertIn(right, self.text)
        stale = self.text.replace(right, f"`POST_LOAD_AUDITS` (the {n - 1} read-only audits)")
        fixed, problems = audit_registry.check_tools_doc(stale)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(f"gives {n - 1} ", problems[0])
        self.assertIn(f"the registry gives {n}.", problems[0])
        self.assertEqual(fixed, self.text)

    def test_spelled_figures_keep_their_form(self):
        ci = len(audit_registry.ci_audits())
        right = f"Of those {audit_registry.spell(ci)}, "
        self.assertIn(right, self.text)
        stale = self.text.replace(right, "Of those twelve, ")
        fixed, problems = audit_registry.check_tools_doc(stale)
        self.assertEqual(len(problems), 1, problems)
        self.assertEqual(fixed, self.text)
        lead = audit_registry.spell(
            sum(1 for a in audit_registry.post_load_audits() if a.ci is not None))
        right = lead.capitalize() + " of these post-load audits"
        self.assertIn(right, self.text)
        fixed, _ = audit_registry.check_tools_doc(self.text.replace(right, "Seven of these post-load audits"))
        self.assertEqual(fixed, self.text)

    def test_a_reworded_sentence_fails_rather_than_passing_unread(self):
        stale = self.text.replace("file-rewriting generators", "generators that rewrite files")
        problems = audit_registry.check_tools_doc(stale)[1]
        self.assertTrue(any("PROSE_FIGURES" in p for p in problems), problems)

    def test_an_audit_out_of_ci_left_unnamed(self):
        stale = self.text.replace("Two, `mod_structure_audit` and `modifier_visibility_audit`, need",
                                  "Two, `mod_structure_audit` and another, need")
        self.assertNotEqual(stale, self.text)
        problems = audit_registry.check_tools_doc(stale)[1]
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("`modifier_visibility_audit`", problems[0])

    def test_a_ci_command_without_a_row(self):
        row = next(line for line in self.text.splitlines()
                   if line.startswith("| `python3 sol_fraction_audit.py --strict` |"))
        problems = audit_registry.check_tools_doc(self.text.replace(row + "\n", ""))[1]
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("0 rows for `python3 sol_fraction_audit.py --strict`", problems[0])

    def test_the_reload_table_in_run_order(self):
        lines = self.text.split("\n")
        i = next(n for n, line in enumerate(lines) if line.startswith("| `event_magnitude_audit` |"))
        lines[i], lines[i + 1] = lines[i + 1], lines[i]
        problems = audit_registry.check_tools_doc("\n".join(lines))[1]
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("run order", problems[0])

    def test_spell(self):
        self.assertEqual(
            [audit_registry.spell(n) for n in (0, 3, 19, 20, 46, 99, 120)],
            ["zero", "three", "nineteen", "twenty", "forty-six", "ninety-nine", "120"],
        )


class WiringTests(unittest.TestCase):
    """CI runs preflight's groups, preflight's audits check runs the registry."""

    def test_ci_runs_every_preflight_group(self):
        import scripts.preflight as preflight
        workflow = read(".github", "workflows", "ci.yml")
        for group in preflight.GROUPS:
            self.assertRegex(
                workflow, rf"scripts/preflight\.py --ci --only {group}\b",
                f"ci.yml has no step for preflight's `{group}` group",
            )

    def test_ci_names_no_audit_itself(self):
        workflow = read(".github", "workflows", "ci.yml")
        self.assertEqual(re.findall(r"python3 \w+_audit\.py", workflow), [])

    def test_runner_resolves_names(self):
        import scripts.run_audits as run_audits
        self.assertEqual([a.name for a in run_audits.resolve(["prev_scope"])], ["prev_scope_audit"])
        self.assertEqual([a.name for a in run_audits.resolve(["prev_scope_audit.py"])],
                         ["prev_scope_audit"])
        self.assertEqual(len(run_audits.resolve([])), len(audit_registry.ci_audits()))
        with self.assertRaises(SystemExit):
            run_audits.resolve(["no_such"])
        with self.assertRaises(SystemExit):
            run_audits.resolve(["mod_structure"])  # reload only

    def test_registry_imports_no_audit(self):
        tree = ast.parse(read("audit_registry.py"))
        imported = {
            alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
            for alias in node.names
        } | {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertFalse({m for m in imported if m and m.endswith("_audit")})


if __name__ == "__main__":
    unittest.main()
