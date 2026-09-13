"""Tests for `scripts/analysis/check_post_load_rosters.py` (issue #248).

Two jobs:

1. Unit-test the AST roster extraction and the doc word-boundary matcher
   against synthetic fixtures, so the checker's own logic is pinned.
2. Run the real check against the real tree — the regression guard that made
   issue #248's drift (11 roster modules undocumented across three docs)
   impossible to reintroduce silently.
"""

import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts", "analysis"))

import check_post_load_rosters as checker  # noqa: E402


_FAKE_SERVER = '''
"""Fake server module."""

POST_LOAD_REGENERATORS = [
    ("alpha_gen", "alpha_gen"),
    ("beta_gen",  "scripts.generators.beta_gen"),
]

POST_LOAD_AUDITS = [
    ("gamma_audit", "gamma_audit"),
]

POST_LOAD_GENERATORS = POST_LOAD_REGENERATORS + POST_LOAD_AUDITS
'''


class ExtractRostersTest(unittest.TestCase):
    def _write(self, text):
        tmp = tempfile.NamedTemporaryFile(
            "w", suffix=".py", delete=False, encoding="utf-8"
        )
        tmp.write(text)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    def test_extracts_labels_from_both_rosters(self):
        rosters = checker.extract_rosters(self._write(_FAKE_SERVER))
        self.assertEqual(
            rosters["POST_LOAD_REGENERATORS"], ["alpha_gen", "beta_gen"]
        )
        self.assertEqual(rosters["POST_LOAD_AUDITS"], ["gamma_audit"])

    def test_missing_roster_raises(self):
        with self.assertRaises(SystemExit):
            checker.extract_rosters(
                self._write("POST_LOAD_REGENERATORS = [('a', 'a')]\n")
            )

    def test_non_literal_roster_raises(self):
        src = (
            "POST_LOAD_REGENERATORS = build_regenerators()\n"
            "POST_LOAD_AUDITS = [('gamma_audit', 'gamma_audit')]\n"
        )
        with self.assertRaises(SystemExit):
            checker.extract_rosters(self._write(src))

    def test_non_tuple_entry_raises(self):
        src = (
            "POST_LOAD_REGENERATORS = ['alpha_gen']\n"
            "POST_LOAD_AUDITS = [('gamma_audit', 'gamma_audit')]\n"
        )
        with self.assertRaises(SystemExit):
            checker.extract_rosters(self._write(src))


class CheckDocsTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.docs = ("one.md", "two.md")

    def _docs(self, first, second):
        for name, text in zip(self.docs, (first, second)):
            with open(
                os.path.join(self.tmpdir.name, name), "w", encoding="utf-8"
            ) as fh:
                fh.write(text)

    def test_all_documented_returns_empty(self):
        self._docs(
            "`alpha_gen` runs first, then `gamma_audit`.",
            "| `alpha_gen.py` | out |\n| `gamma_audit.py` | report |\n",
        )
        missing = checker.check_docs(
            {"R": ["alpha_gen"], "A": ["gamma_audit"]},
            repo_root=self.tmpdir.name,
            doc_files=self.docs,
        )
        self.assertEqual(missing, [])

    def test_reports_per_doc_misses(self):
        self._docs("`alpha_gen` only.", "`alpha_gen.py` only.")
        missing = checker.check_docs(
            {"R": ["alpha_gen"], "A": ["gamma_audit"]},
            repo_root=self.tmpdir.name,
            doc_files=self.docs,
        )
        self.assertEqual(
            missing, [("gamma_audit", "one.md"), ("gamma_audit", "two.md")]
        )

    def test_substring_of_a_longer_name_does_not_count(self):
        # `loc_render_audit` must not be satisfied by `loc_render_audit_extra`,
        # nor `any_limit_audit` by `iterator_any_limit_audit`.
        self._docs("`loc_render_audit_extra`", "`loc_render_audit_extra`")
        missing = checker.check_docs(
            {"A": ["loc_render_audit"]},
            repo_root=self.tmpdir.name,
            doc_files=self.docs,
        )
        self.assertEqual(len(missing), 2)

    def test_path_qualified_mention_counts(self):
        self._docs(
            "see `scripts/generators/gen_company_building_cleanup.py`",
            "`gen_company_building_cleanup` output",
        )
        missing = checker.check_docs(
            {"R": ["gen_company_building_cleanup"]},
            repo_root=self.tmpdir.name,
            doc_files=self.docs,
        )
        self.assertEqual(missing, [])


class RealTreeTest(unittest.TestCase):
    """The regression guard: the shipped docs must name every roster module."""

    def test_rosters_are_fully_documented(self):
        rosters = checker.extract_rosters(
            os.path.join(checker.REPO_ROOT, checker.SERVER_FILE)
        )
        self.assertTrue(rosters["POST_LOAD_REGENERATORS"])
        self.assertTrue(rosters["POST_LOAD_AUDITS"])
        missing = checker.check_docs(rosters)
        self.assertEqual(
            missing,
            [],
            "Post-load roster modules missing from docs:\n"
            + "\n".join(f"  {doc}: `{mod}`" for mod, doc in missing)
            + "\nRun python3 scripts/analysis/check_post_load_rosters.py",
        )


if __name__ == "__main__":
    unittest.main()
