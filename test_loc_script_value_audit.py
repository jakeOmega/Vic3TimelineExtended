"""Unit tests for loc_script_value_audit (#1120, #1181).

Each fixture is a throwaway mod tree: a vanilla snapshot JSON, mod script
value files, English loc and, for the script-string scan, files under
common/ and events/. The crux is what counts as a definition (a depth-0 key,
scalars and `*_OR_CREATE:` names included, but not a constant or a name
behind INJECT/REPLACE), which arguments are skipped as dynamic, what counts as
a comment in script, and the tagged suppression, stale tags included.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import gui_reference_audit
import loc_script_value_audit
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
INJECT:vanilla_sv = { add = 1 }
REPLACE:mod_block_sv = { value = 2 }
INJECT:inject_only_sv = { add = 1 }
REPLACE:replace_only_sv = { value = 2 }
TRY_INJECT:try_inject_only_sv = { add = 1 }
TRY_REPLACE:try_replace_only_sv = { value = 2 }
INJECT_OR_CREATE:created_sv = { value = 3 }
REPLACE_OR_CREATE:recreated_sv = { value = 4 }
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
        _write(self.root, "common/script_values/sub/te_sub_values.txt", "sub_sv = 1\n")

    def loc(self, *lines: str, name: str = "te_test_l_english.yml") -> None:
        _write(self.root, f"localization/english/{name}", _loc(*lines))

    def run_audit(self):
        return audit(self.root)


class DefinitionTests(_Fixture):
    def test_depth_zero_keys_scalars_and_or_create_names(self):
        self.assertEqual(
            mod_script_value_names(self.root),
            {"mod_block_sv", "mod_scalar_sv", "created_sv", "recreated_sv", "sub_sv"},
        )

    def test_definition_rule_is_shared_with_gui_reference_audit(self):
        # #1180: one helper, so the two audits can't drift on what defines.
        self.assertIs(loc_script_value_audit.defined_names, gui_reference_audit.defined_names)

    def test_missing_snapshot_raises(self):
        os.remove(os.path.join(self.root, "vanilla_parsed", "common", "script_values.json"))
        self.loc("k:0 \"[ScriptValue('vanilla_sv')]\"")
        with self.assertRaises(FileNotFoundError):
            self.run_audit()

    def test_no_loc_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.run_audit()
        self.loc("k:0 \"[ScriptValue('gone_sv')]\"", name="te_unused_l_english.yml")
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

    def test_subfolder_definition_resolves(self):
        self.loc("k:0 \"[ScriptValue('sub_sv')]\"")
        r = self.run_audit()
        self.assertEqual(r.flags, [])
        self.assertEqual(r.refs_checked, 1)

    def test_merge_targets_and_or_create_names_resolve(self):
        # vanilla_sv is injected and mod_block_sv replaced; each resolves
        # through its own definition.
        self.loc("k:0 \"[ScriptValue('vanilla_sv')] [ScriptValue('mod_block_sv')] "
                 "[ScriptValue('created_sv')] [ScriptValue('recreated_sv')]\"")
        r = self.run_audit()
        self.assertEqual(r.flags, [])
        self.assertEqual(r.refs_checked, 4)

    def test_inject_or_replace_with_no_base_is_flagged(self):
        self.loc("k:0 \"[ScriptValue('inject_only_sv')] [ScriptValue('replace_only_sv')] "
                 "[ScriptValue('try_inject_only_sv')] [ScriptValue('try_replace_only_sv')]\"")
        self.assertEqual(
            [f.name for f in self.run_audit().flags],
            ["inject_only_sv", "replace_only_sv", "try_inject_only_sv", "try_replace_only_sv"],
        )

    def test_nested_key_and_constant_are_not_definitions(self):
        self.loc("k:0 \"[ScriptValue('nested_not_top')] [ScriptValue('const_not_sv')]\"")
        self.assertEqual([f.name for f in self.run_audit().flags],
                         ["nested_not_top", "const_not_sv"])

    def test_escaped_double_quote_form_is_checked(self):
        self.loc('k:0 "[ScriptValue(\\"gone_sv\\")] [ScriptValue(\\"vanilla_sv\\")]"')
        self.assertEqual([f.name for f in self.run_audit().flags], ["gone_sv"])

    def test_whitespace_inside_the_parentheses(self):
        self.loc('k:0 "[ScriptValue( \'gone_sv\' )] [ScriptValue(  \\"vanilla_sv\\"  )]"')
        r = self.run_audit()
        self.assertEqual([f.name for f in r.flags], ["gone_sv"])
        self.assertEqual((r.refs_checked, r.dynamic_skipped), (2, 0))

    def test_dynamic_arguments_are_skipped(self):
        self.loc(
            "k1:0 \"[ScriptValue(Concatenate('gone','_sv'))]\"",
            "k2:0 \"[ScriptValue('te_$KIND$_sv')]\"",
            "k3:0 \"[ScriptValue('$gone_key$')]\"",
            "k4:0 \"[ScriptValue('gone.dotted')] [ScriptValue('gone-hyphen')]\"",
            # An unescaped quote ends the value as split_loc_line reads it.
            'k5:0 "[ScriptValue("gone_sv")]"',
        )
        r = self.run_audit()
        self.assertEqual(r.flags, [])
        self.assertEqual(r.dynamic_skipped, 6)
        self.assertEqual(r.refs_checked, 0)

    def test_repeated_name_on_a_line_is_one_flag(self):
        self.loc("k:0 \"[ScriptValue('gone_sv')] and [ScriptValue('gone_sv')]\"")
        r = self.run_audit()
        self.assertEqual(len(r.flags), 1)
        self.assertEqual(r.refs_checked, 2)

    def test_te_unused_is_skipped_flags_and_tags(self):
        self.loc("k:0 \"[ScriptValue('vanilla_sv')]\"")
        self.loc(
            "k:0 \"[ScriptValue('gone_sv')]\"",
            "k2:0 \"plain\" # REVIEWED 2026-10-26 (loc_script_value): stale but unscanned",
            name="te_unused_l_english.yml",
        )
        r = self.run_audit()
        self.assertEqual((r.flags, r.stale_tags, r.loc_files_scanned), ([], [], 1))

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


class ScriptStringTests(_Fixture):
    """`ScriptValue('x')` in quoted strings under common/ and events/ (#1181)."""

    EVENTS = "events/te_test_events.txt"

    def setUp(self):
        super().setUp()
        self.loc("ok:0 \"plain\"")

    def script(self, text: str, rel: str = EVENTS) -> None:
        _write(self.root, rel, text)

    def flags(self, result=None):
        result = result or self.run_audit()
        return [(f.file, f.line, f.key, f.name) for f in result.flags]

    def test_missing_name_is_flagged_with_its_entry(self):
        self.script(
            "namespace = te_test\n"
            "te_test.1 = {\n"
            "\timmediate = {\n"
            "\t\tdebug_log = \"TE_SELF_CHECK OK [ScriptValue('vanilla_sv')]\"\n"
            "\t\tdebug_log = \"TE_SELF_CHECK BROKEN [ScriptValue('gone_sv')|0]\"\n"
            "\t}\n"
            "}\n"
        )
        r = self.run_audit()
        self.assertEqual(self.flags(r), [(self.EVENTS, 5, "te_test.1", "gone_sv")])
        self.assertEqual((r.script_refs_checked, r.script_dynamic_skipped), (2, 0))
        self.assertEqual(r.failing, 1)

    def test_common_is_scanned_and_names_resolve(self):
        rel = "common/scripted_effects/te_test_effects.txt"
        self.script(
            "te_effect = {\n"
            "\tdebug_log = \"[ScriptValue('mod_scalar_sv')] [ScriptValue('sub_sv')] "
            "[ScriptValue('created_sv')] [ScriptValue('vanilla_sv')]\"\n"
            "\tdebug_log = \"[ScriptValue('nested_not_top')]\"\n"
            "}\n",
            rel,
        )
        r = self.run_audit()
        self.assertEqual(self.flags(r), [(rel, 3, "te_effect", "nested_not_top")])
        self.assertEqual(r.script_refs_checked, 5)

    def test_inject_or_replace_with_no_base_is_flagged(self):
        self.script("e = { debug_log = \"[ScriptValue('inject_only_sv')] "
                    "[ScriptValue('try_replace_only_sv')] [ScriptValue('recreated_sv')]\" }\n")
        self.assertEqual([f.name for f in self.run_audit().flags],
                         ["inject_only_sv", "try_replace_only_sv"])

    def test_commented_out_read_is_ignored(self):
        self.script(
            "e = {\n"
            "\t# debug_log = \"[ScriptValue('gone_sv')]\"\n"
            "\tvalue = 1 # was [ScriptValue('gone_sv')], don't \"quote\n"
            "\tdebug_log = \"[ScriptValue('vanilla_sv')]\"\n"
            "}\n"
        )
        r = self.run_audit()
        self.assertEqual(r.flags, [])
        self.assertEqual(r.script_refs_checked, 1)

    def test_hash_inside_a_string_is_not_a_comment(self):
        self.script("e = { debug_log = \"#b [ScriptValue('gone_sv')]#!\" }\n")
        self.assertEqual([f.name for f in self.run_audit().flags], ["gone_sv"])

    def test_read_outside_a_string_is_not_scanned(self):
        self.script("e = { value = ScriptValue('gone_sv') }\n")
        r = self.run_audit()
        self.assertEqual((r.flags, r.script_refs_checked), ([], 0))

    def test_escaped_double_quote_form_is_checked(self):
        self.script('e = { debug_log = "[ScriptValue(\\"gone_sv\\")] [ScriptValue(\\"vanilla_sv\\")]" }\n')
        r = self.run_audit()
        self.assertEqual([f.name for f in r.flags], ["gone_sv"])
        self.assertEqual(r.script_refs_checked, 2)

    def test_dynamic_arguments_are_skipped(self):
        self.script(
            "te_helper = {\n"
            "\tdebug_log = \"[ScriptValue('te_$KIND$_sv')] [ScriptValue('$SV$')]\"\n"
            "\tdebug_log = \"[ScriptValue(Concatenate('gone','_sv'))] [ScriptValue('gone.dotted')]\"\n"
            "}\n"
        )
        r = self.run_audit()
        self.assertEqual(r.flags, [])
        self.assertEqual((r.script_refs_checked, r.script_dynamic_skipped), (0, 4))

    def test_repeated_name_on_a_line_is_one_flag(self):
        self.script("e = { debug_log = \"[ScriptValue('gone_sv')] [ScriptValue('gone_sv')]\" }\n")
        r = self.run_audit()
        self.assertEqual(len(r.flags), 1)
        self.assertEqual(r.script_refs_checked, 2)

    def test_tag_suppresses(self):
        self.script("e = {\n\tdebug_log = \"[ScriptValue('gone_sv')]\" "
                    "# REVIEWED 2026-10-26 (loc_script_value): defined by a later PR\n}\n")
        r = self.run_audit()
        self.assertEqual(len(r.flags), 1)
        self.assertEqual(r.flags[0].exemption,
                         {"date": "2026-10-26", "rationale": "defined by a later PR"})
        self.assertEqual((r.stale_tags, r.failing), ([], 0))
        self.assertIn("`e` reads `gone_sv` — **2026-10-26**: defined by a later PR",
                      render_report(r))

    def test_tag_on_the_closing_line_of_a_multiline_string(self):
        self.script("e = {\n\tdebug_log = \"[ScriptValue('gone_sv')]\n"
                    "\t\tmore\" # REVIEWED 2026-10-26 (loc_script_value): why\n}\n")
        r = self.run_audit()
        self.assertEqual([(f.line, f.exemption is not None) for f in r.flags], [(2, True)])
        self.assertEqual(r.failing, 0)

    def test_tag_inside_a_string_or_for_another_check_does_not_suppress(self):
        self.script(
            "e = {\n"
            "\tdebug_log = \"[ScriptValue('gone_sv')] # REVIEWED 2026-10-26 (loc_script_value): in text\"\n"
            "\tdebug_log = \"[ScriptValue('gone_sv')]\" # REVIEWED 2026-10-26 (script_argument): other\n"
            "\tdebug_log = \"[ScriptValue('gone_sv')]\" # REVIEWED 2026-10-26: untagged\n"
            "}\n"
        )
        r = self.run_audit()
        self.assertEqual([f.exemption for f in r.flags], [None, None, None])
        self.assertEqual((r.stale_tags, r.failing), ([], 3))

    def test_stale_tag_fails_strict(self):
        self.script(
            "e = {\n"
            "\tdebug_log = \"[ScriptValue('vanilla_sv')]\" # REVIEWED 2026-10-26 (loc_script_value): fixed\n"
            "\tvalue = 1 # REVIEWED 2026-10-26 (loc_script_value): never needed\n"
            "}\n"
        )
        r = self.run_audit()
        self.assertEqual(r.flags, [])
        self.assertEqual([(t.file, t.line, t.key) for t in r.stale_tags],
                         [(self.EVENTS, 2, "e"), (self.EVENTS, 3, "e")])
        self.assertEqual(r.failing, 2)
        self.assertIn(f"`{self.EVENTS}:2` `e` ({CHECK})", render_report(r))

    def test_strict_exit_codes(self):
        def run(*argv):
            with contextlib.redirect_stdout(io.StringIO()):
                return main(["--mod-path", self.root, *argv])
        self.script("e = { debug_log = \"[ScriptValue('vanilla_sv')]\" }\n")
        self.assertEqual(run("--strict"), 0)
        self.script("e = { debug_log = \"[ScriptValue('gone_sv')]\" }\n")
        self.assertEqual((run(), run("--strict")), (0, 1))

    def test_no_script_file_raises(self):
        import shutil
        shutil.rmtree(os.path.join(self.root, "common"))
        with self.assertRaises(FileNotFoundError):
            self.run_audit()


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
        _write(self.root, "events/te_test_events.txt",
               "e = { debug_log = \"[ScriptValue('vanilla_sv')] [ScriptValue('$X$')]\" }\n")
        with mock.patch("path_constants.mod_path", self.root):
            summary = regenerate(None)
        self.assertEqual((summary["unreviewed"], summary["total_flags"], summary["stale_tags"]),
                         (2, 1, 1))
        self.assertEqual((summary["script_refs_checked"], summary["script_dynamic_skipped"]), (1, 1))
        self.assertGreaterEqual(summary["script_files_scanned"], 1)
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
