"""`scripts/preflight.py`: the checks it defines itself, and how it selects."""
import argparse
import os
import sys
import tempfile
import unittest
from unittest import mock

import scripts.preflight as preflight
import scripts.run_audits as run_audits

ROOT = os.path.dirname(os.path.abspath(__file__))


def ctx(changed=None):
    return preflight.Ctx(env=dict(os.environ), ci=False, changed=changed)


def args(**overrides):
    base = dict(only=[], skip=[], quick=False)
    base.update(overrides)
    return argparse.Namespace(**base)


class SelectionTests(unittest.TestCase):
    def test_ids_are_unique_and_distinct_from_groups(self):
        ids = [c.id for c in preflight.CHECKS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids) & set(preflight.GROUPS), {"tests", "audits"})

    def test_default_runs_everything(self):
        self.assertEqual(preflight.select(args(), None), list(preflight.CHECKS))

    def test_quick_drops_only_the_suite(self):
        kept = {c.id for c in preflight.select(args(quick=True), None)}
        self.assertEqual({c.id for c in preflight.CHECKS} - kept, {"tests"})

    def test_only_and_skip_take_groups_and_ids(self):
        self.assertEqual({c.group for c in preflight.select(args(only=["docs"]), None)}, {"docs"})
        self.assertEqual([c.id for c in preflight.select(args(only=["ruff"]), None)], ["ruff"])
        self.assertNotIn("ruff", [c.id for c in preflight.select(args(skip=["ruff"]), None)])

    def test_changed_drops_checks_the_diff_cannot_reach(self):
        ids = [c.id for c in preflight.select(args(), ["docs/player_guide/04-banking.md"])]
        self.assertIn("guide-pdf", ids)
        self.assertIn("spelling", ids)
        self.assertIn("tests", ids)  # no triggers: any test may read the docs
        self.assertNotIn("ruff", ids)
        self.assertNotIn("tabs", ids)
        self.assertNotIn("audits", ids)

    def test_script_change_runs_the_audits(self):
        ids = [c.id for c in preflight.select(args(), ["events/banking_events.txt"])]
        self.assertIn("audits", ids)
        self.assertIn("tabs", ids)


class Py311Tests(unittest.TestCase):
    def scan(self, source):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "sample.py"), "w", encoding="utf-8") as fh:
                fh.write(source)
            with mock.patch.object(preflight, "REPO_ROOT", tmp), \
                    mock.patch.object(preflight, "git", return_value="sample.py\n"):
                return preflight.check_py311_fstrings(ctx())

    @unittest.skipIf(sys.version_info < (3, 12), "3.11 rejects these at compile time")
    def test_flags_what_3_11_rejects(self):
        # Assembled so this file itself still compiles on 3.11.
        quote, backslash = '"', "\\"
        reused = "x = f" + quote + "{d[" + quote + "k" + quote + "]}" + quote + "\n"
        escaped = "x = f'{" + quote + backslash + "n" + quote + ".join(a)}'\n"
        for source in (reused, escaped):
            result = self.scan(source)
            self.assertFalse(result.ok, source)
            self.assertIn("sample.py:1", result.output)

    @unittest.skipIf(sys.version_info < (3, 12), "the check defers to compileall on 3.11")
    def test_passes_what_3_11_accepts(self):
        source = (
            "x = f\"{d['k']} {n:>{w}} {{literal}}\"\n"
            "y = f'''{d[\"k\"]}\n{n}'''\n"
            "z = f'{a!r:^10}' rf'\\d{n}'\n"
        )
        result = self.scan(source)
        self.assertTrue(result.ok, result.output)

    def test_repo_is_clean(self):
        result = preflight.check_py311_fstrings(ctx())
        self.assertTrue(result.ok, result.output)


class LineEndingTests(unittest.TestCase):
    def test_crlf_docs_are_crlf(self):
        result = preflight.check_line_endings(ctx())
        self.assertTrue(result.ok, result.output)

    def test_a_flipped_doc_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "a.md"), "wb") as fh:
                fh.write(b"one\r\ntwo\nthree\r\n")
            with mock.patch.object(preflight, "REPO_ROOT", tmp), \
                    mock.patch.object(preflight, "CRLF_DOCS", ("a.md", "gone.md")):
                result = preflight.check_line_endings(ctx())
        self.assertFalse(result.ok)
        self.assertIn("a.md: 1 of 3 lines end in LF", result.output)
        self.assertIn("gone.md: missing", result.output)


class EnvironmentTests(unittest.TestCase):
    def test_default_environment_is_ci_s(self):
        with mock.patch.dict(os.environ, {"VIC3_BASE_GAME": "/real/game", "PYTHONPATH": "/opt/ros"}):
            env = run_audits.child_env()
            self.assertEqual(env["VIC3_BASE_GAME"], run_audits.DUMMY_ENV["VIC3_BASE_GAME"])
            self.assertNotIn("PYTHONPATH", env)
            real = run_audits.child_env(real_paths=True)
            self.assertEqual(real["VIC3_BASE_GAME"], "/real/game")
            self.assertEqual(real["PYTHONPATH"], "/opt/ros")

    def test_conftest_and_runner_agree_on_the_dummies(self):
        import conftest
        self.assertEqual(conftest._DUMMY_ENV, run_audits.DUMMY_ENV)

    def test_ci_workflow_sets_the_same_variables(self):
        with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as fh:
            workflow = fh.read()
        for key in run_audits.DUMMY_ENV:
            self.assertIn(f"{key}:", workflow)


if __name__ == "__main__":
    unittest.main()
