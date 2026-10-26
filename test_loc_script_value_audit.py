"""Unit tests for loc_script_value_audit (#1120).

Each fixture is a throwaway mod tree: a vanilla snapshot JSON, mod script
value files and English loc. The crux is what counts as a definition (any
depth-0 key, scalars and merge prefixes included), which arguments are
skipped as dynamic, and the tagged suppression, stale tags included.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from loc_script_value_audit import (
    CHECK, REPORT_PATH, audit, main, mod_script_value_names, regenerate, render_report,
)

SCRIPT_VALUES = """\
# commented_sv = 1
mod_block_sv = {
\tvalue = 1
\tnested_not_top = 2
}
mod_scalar_sv = 5
INJECT:injected_sv = { add = 1 }
REPLACE:replaced_sv = { value = 2 }
@const_not_sv = 3
"""


def _write(root: str, rel: str, text: str) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as fh:
        fh.write(text)


def _loc(*lines: str) -> str:
    return "l_english:\n" + "".join(f" {line}\n" for line in lines)


class _Fixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        os.makedirs(os.path.join(self.root, "vanilla_parsed", "common"))
        with open(os.path.join(self.root, "vanilla_parsed", "common", "script_values.json"),
                  "w", encoding="utf-8") as fh:
            json.dump({"vanilla_sv": ["=", "1"]}, fh)
        _write(self.root, "common/script_values/te_test_values.txt", SCRIPT_VALUES)

    def loc(self, *lines: str, name: str = "te_test_l_english.yml") -> None:
        _write(self.root, f"localization/english/{name}", _loc(*lines))

    def run_audit(self):
        return audit(self.root)


class DefinitionTests(_Fixture):
    def test_depth_zero_keys_scalars_and_merge_prefixes(self):
        self.assertEqual(
            mod_script_value_names(self.root),
            {"mod_block_sv", "mod_scalar_sv", "injected_sv", "replaced_sv"},
        )

    def test_missing_snapshot_raises(self):
        os.remove(os.path.join(self.root, "vanilla_parsed", "common", "script_values.json"))
        self.loc("k:0 \"[ScriptValue('vanilla_sv')]\"")
        with self.assertRaises(FileNotFoundError):
            self.run_audit()


class FlagTests(_Fixture):
    def test_missing_name_is_flagged(self):
        self.loc(
            "ok:0 \"fine\"",
            "k_hit:0 \"Factor: [GetPlayer.MakeScope.ScriptValue('gone_sv')|1]\"",
        )
        r = self.run_audit()
        self.assertEqual(
            [(f.file, f.line, f.key, f.name) for f in r.flags],
            [("localization/english/te_test_l_english.yml", 3, "k_hit", "gone_sv")],
        )
        self.assertEqual(r.failing, 1)

    def test_vanilla_name_resolves(self):
        self.loc("k:0 \"[ScriptValue('vanilla_sv')]\"")
        r = self.run_audit()
        self.assertEqual(r.flags, [])
        self.assertEqual(r.refs_checked, 1)

    def test_mod_scalar_resolves(self):
        self.loc("k:0 \"[ScriptValue('mod_scalar_sv')]\"")
        self.assertEqual(self.run_audit().flags, [])

    def test_inject_and_replace_names_resolve(self):
        self.loc("k:0 \"[ScriptValue('injected_sv')] [ScriptValue('replaced_sv')]\"")
        r = self.run_audit()
        self.assertEqual(r.flags, [])
        self.assertEqual(r.refs_checked, 2)

    def test_nested_key_and_constant_are_not_definitions(self):
        self.loc("k:0 \"[ScriptValue('nested_not_top')] [ScriptValue('const_not_sv')]\"")
        self.assertEqual([f.name for f in self.run_audit().flags],
                         ["nested_not_top", "const_not_sv"])

    def test_escaped_double_quote_form_is_checked(self):
        self.loc('k:0 "[ScriptValue(\\"gone_sv\\")] [ScriptValue(\\"vanilla_sv\\")]"')
        self.assertEqual([f.name for f in self.run_audit().flags], ["gone_sv"])

    def test_dynamic_arguments_are_skipped(self):
        self.loc(
            "k1:0 \"[ScriptValue(Concatenate('gone','_sv'))]\"",
            "k2:0 \"[ScriptValue('te_$KIND$_sv')]\"",
            "k3:0 \"[ScriptValue('$gone_key$')]\"",
        )
        r = self.run_audit()
        self.assertEqual(r.flags, [])
        self.assertEqual(r.dynamic_skipped, 3)
        self.assertEqual(r.refs_checked, 0)

    def test_repeated_name_on_a_line_is_one_flag(self):
        self.loc("k:0 \"[ScriptValue('gone_sv')] and [ScriptValue('gone_sv')]\"")
        r = self.run_audit()
        self.assertEqual(len(r.flags), 1)
        self.assertEqual(r.refs_checked, 2)

    def test_te_unused_is_skipped_flags_and_tags(self):
        self.loc(
            "k:0 \"[ScriptValue('gone_sv')]\"",
            "k2:0 \"plain\" # REVIEWED 2026-10-26 (loc_script_value): stale but unscanned",
            name="te_unused_l_english.yml",
        )
        r = self.run_audit()
        self.assertEqual((r.flags, r.stale_tags, r.loc_files_scanned), ([], [], 0))

    def test_replace_folder_is_scanned(self):
        _write(self.root, "localization/english/replace/te_over_l_english.yml",
               _loc("k:0 \"[ScriptValue('gone_sv')]\""))
        self.assertEqual([f.file for f in self.run_audit().flags],
                         ["localization/english/replace/te_over_l_english.yml"])


class SuppressionTests(_Fixture):
    def test_tag_suppresses(self):
        self.loc("k:0 \"[ScriptValue('gone_sv')]\" "
                 "# REVIEWED 2026-10-26 (loc_script_value): defined by a later PR")
        r = self.run_audit()
        self.assertEqual(len(r.flags), 1)
        self.assertEqual(r.flags[0].exemption,
                         {"date": "2026-10-26", "rationale": "defined by a later PR"})
        self.assertEqual((r.stale_tags, r.failing), ([], 0))

    def test_tag_listing_several_checks_suppresses(self):
        self.loc("k:0 \"[ScriptValue('gone_sv')]\" "
                 "# REVIEWED 2026-10-26 (concept, loc_script_value): why")
        self.assertEqual(self.run_audit().failing, 0)

    def test_untagged_or_foreign_tag_does_not_suppress(self):
        self.loc(
            "k1:0 \"[ScriptValue('gone_sv')]\" # REVIEWED 2026-10-26: untagged",
            "k2:0 \"[ScriptValue('gone_sv')]\" # REVIEWED 2026-10-26 (script_argument): other check",
        )
        r = self.run_audit()
        self.assertEqual([f.exemption for f in r.flags], [None, None])
        self.assertEqual((r.stale_tags, r.failing), ([], 2))

    def test_stale_tag_fails_strict(self):
        self.loc(
            "k1:0 \"[ScriptValue('vanilla_sv')]\" # REVIEWED 2026-10-26 (loc_script_value): fixed since",
            "k2:0 \"no call\" # REVIEWED 2026-10-26 (loc_script_value): never needed",
        )
        r = self.run_audit()
        self.assertEqual(r.flags, [])
        self.assertEqual([(t.line, t.key) for t in r.stale_tags], [(2, "k1"), (3, "k2")])
        self.assertEqual(r.failing, 2)
        report = render_report(r)
        self.assertIn("## Stale tags", report)
        self.assertIn(f"`localization/english/te_test_l_english.yml:2` `k1` ({CHECK})", report)


class EntryPointTests(_Fixture):
    def _main(self, *argv: str) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return main(["--mod-path", self.root, *argv])

    def test_strict_exit_codes(self):
        self.loc("k:0 \"[ScriptValue('vanilla_sv')]\"")
        self.assertEqual(self._main("--strict"), 0)
        self.loc("k:0 \"[ScriptValue('gone_sv')]\"")
        self.assertEqual(self._main(), 0)
        self.assertEqual(self._main("--strict"), 1)
        self.loc("k:0 \"[ScriptValue('gone_sv')]\" # REVIEWED 2026-10-26 (loc_script_value): ok")
        self.assertEqual(self._main("--strict"), 0)

    def test_report_lists_flag_and_exemption(self):
        self.loc(
            "k1:0 \"[ScriptValue('gone_sv')]\"",
            "k2:0 \"[ScriptValue('other_sv')]\" # REVIEWED 2026-10-26 (loc_script_value): kept",
        )
        report = render_report(self.run_audit())
        self.assertIn("- line 2: `k1` reads `gone_sv`", report)
        self.assertIn("`k2` reads `other_sv` — **2026-10-26**: kept", report)
        self.assertIn("- unreviewed: 1", report)

    def test_regenerate_writes_report_and_counts_stale_tags(self):
        self.loc(
            "k1:0 \"[ScriptValue('gone_sv')]\"",
            "k2:0 \"x\" # REVIEWED 2026-10-26 (loc_script_value): stale",
        )
        with mock.patch("path_constants.mod_path", self.root):
            summary = regenerate(None)
        self.assertEqual((summary["unreviewed"], summary["total_flags"], summary["stale_tags"]),
                         (2, 1, 1))
        with open(os.path.join(self.root, REPORT_PATH), encoding="utf-8") as fh:
            self.assertIn("`k1` reads `gone_sv`", fh.read())


class RepoTests(unittest.TestCase):
    def test_the_mod_has_no_failing_flag(self):
        from path_constants import mod_path
        result = audit(mod_path)
        self.assertEqual([f for f in result.flags if not f.exemption], [])
        self.assertEqual(result.stale_tags, [])

    def test_post_load_roster_and_ci(self):
        from scripts.analysis.check_post_load_rosters import extract_rosters
        root = os.path.dirname(os.path.abspath(__file__))
        self.assertIn("loc_script_value_audit", extract_rosters(
            os.path.join(root, "mod_state_server.py"))["POST_LOAD_AUDITS"])
        with open(os.path.join(root, ".github", "workflows", "ci.yml"), encoding="utf-8") as fh:
            self.assertIn("python3 loc_script_value_audit.py --strict", fh.read())


if __name__ == "__main__":
    unittest.main()
