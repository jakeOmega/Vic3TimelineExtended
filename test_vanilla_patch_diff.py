"""Tests for `scripts/analysis/vanilla_patch_diff.py`.

Builds tiny old/new engine-doc dumps and vanilla_parsed/ snapshots in a
tempdir; needs no Victoria 3 install and no vanilla clone.

Run: python3 -m unittest test_vanilla_patch_diff
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts", "analysis"))

import vanilla_patch_diff as vpd  # noqa: E402


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def _region_block(suffix, body):
    """The eight iterator headers a map region adds to effects.log."""
    return "".join(f"## {kind}_{scope}_in_{suffix}\n{body}\n**Supported Scopes**: none\n\n"
                   for kind in ("every", "any", "random", "ordered")
                   for scope in ("country", "state"))


class EngineDocsDiffTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old = os.path.join(self.tmp.name, "old")
        self.new = os.path.join(self.tmp.name, "new")

    def test_effects_removed_added_changed_and_region_noise_skipped(self):
        _write(os.path.join(self.old, "effects.log"),
               "# Effect Documentation\r\n"
               "## keep\r\nSame\r\n\r\n"
               "## gone\r\nRemoved effect\r\n\r\n"
               "## edit\r\nOld text\r\n**Supported Scopes**: country\r\n\r\n"
               + _region_block("andes", "leaked script A").replace("\n", "\r\n"))
        _write(os.path.join(self.new, "effects.log"),
               "# Effect Documentation\n"
               "## keep\nSame\n\n"
               "## edit\nNew text\n**Supported Scopes**: country, state\n\n"
               "## brand_new\nAdded effect\n\n"
               + _region_block("andes", "leaked script B"))
        removed, added, changed = vpd.diff_doc_file(
            os.path.join(self.old, "effects.log"), os.path.join(self.new, "effects.log"),
            vpd._DOC_HEADERS["effects.log"])
        self.assertEqual(removed, ["gone"])
        self.assertEqual(added, ["brand_new"])
        self.assertEqual(list(changed), ["edit"])
        self.assertIn("-Old text", changed["edit"])
        self.assertIn("+New text", changed["edit"])

    def test_a_lone_iterator_with_an_in_suffix_is_not_noise(self):
        _write(os.path.join(self.old, "effects.log"), "## keep\nx\n")
        _write(os.path.join(self.new, "effects.log"),
               "## keep\nx\n\n## every_country_in_hierarchy\nNew iterator\n")
        _, added, _ = vpd.diff_doc_file(
            os.path.join(self.old, "effects.log"), os.path.join(self.new, "effects.log"),
            vpd._DOC_HEADERS["effects.log"])
        self.assertEqual(added, ["every_country_in_hierarchy"])

    def test_modifiers_and_on_actions_use_name_colon_headers(self):
        _write(os.path.join(self.old, "modifiers.log"),
               "old_mod:\n  Mask: country\n  Name: Old\n\nkept_mod:\n  Mask: state\n")
        _write(os.path.join(self.new, "modifiers.log"),
               "new_mod:\n  Mask: country\n  Name: New\n\nkept_mod:\n  Mask: state\n")
        _write(os.path.join(self.old, "on_actions.log"),
               "On Action Documentation:\n\n--------------------\n\non_a:\nFrom Code: Yes\n")
        _write(os.path.join(self.new, "on_actions.log"),
               "On Action Documentation:\n\n--------------------\n\non_a:\nFrom Code: Yes\n\n"
               "--------------------\n\non_b:\nFrom Code: Yes\n")
        results = vpd.diff_docs(self.old, self.new)
        self.assertEqual(results["modifiers.log"][0], ["old_mod"])
        self.assertEqual(results["modifiers.log"][1], ["new_mod"])
        self.assertEqual(results["on_actions.log"][1], ["on_b"])
        # a log missing from both dumps is an empty diff, not an error
        self.assertEqual(results["triggers.log"], ([], [], {}))


class ParsedDiffTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old = os.path.join(self.tmp.name, "old")
        self.new = os.path.join(self.tmp.name, "new")
        _write(os.path.join(self.old, "common", "journal_entries.json"), json.dumps({
            "je_a": ["=", {"complete": ["=", {"is_at_war": ["=", "no"]}], "weight": ["=", "100"]}],
            "je_b": ["=", {"weight": ["=", "1"]}],
            "je_same": ["=", {"weight": ["=", "5"]}],
        }))
        _write(os.path.join(self.new, "common", "journal_entries.json"), json.dumps({
            "je_a": ["=", {"complete": ["=", {"is_at_war": ["=", "yes"]}], "weight": ["=", "100"]}],
            "je_c": ["=", {"weight": ["=", "2"]}],
            "je_same": ["=", {"weight": ["=", "5"]}],
        }))
        _write(os.path.join(self.old, "localization_english.json"),
               json.dumps({"k_gone": "Old", "k_kept": "Same", "k_edit": "Before"}))
        _write(os.path.join(self.new, "localization_english.json"),
               json.dumps({"k_new": "New", "k_kept": "Same", "k_edit": "After"}))

    def test_entities_removed_added_changed_with_rendered_diff(self):
        res = vpd.diff_parsed(self.new, old_dir=self.old)
        removed, added, changed, diffs = res[os.path.join("common", "journal_entries.json")]
        self.assertEqual((removed, added, changed), (["je_b"], ["je_c"], ["je_a"]))
        joined = "\n".join(diffs["je_a"])
        self.assertIn("-\t\tis_at_war = no", joined)
        self.assertIn("+\t\tis_at_war = yes", joined)
        self.assertNotIn("weight", "\n".join(l for l in diffs["je_a"] if l[:1] in "+-"))

    def test_localization_values_render_as_text_not_characters(self):
        removed, added, changed, diffs = vpd.diff_parsed(self.new, old_dir=self.old)["localization_english.json"]
        self.assertEqual((removed, added, changed), (["k_gone"], ["k_new"], ["k_edit"]))
        self.assertEqual([l for l in diffs["k_edit"] if l[:1] in "+-"],
                         ["-k_edit = Before", "+k_edit = After"])

    def test_a_type_missing_from_the_old_snapshot_is_reported(self):
        _write(os.path.join(self.new, "common", "brand_new_type.json"), json.dumps({"x": ["=", "1"]}))
        res = vpd.diff_parsed(self.new, old_dir=self.old)
        self.assertIn("absent", res[os.path.join("common", "brand_new_type.json")][0][0])


class ModUsesTest(unittest.TestCase):
    def test_code_hits_and_comment_only_hits_are_separated(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            _write(os.path.join(tmp, "common", "a.txt"),
                   "x = {\n\tremoved_thing = 1\n\t# removed_thing was renamed\n\tother_removed_thing_2 = 1\n}\n")
            subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
            hits = vpd.mod_uses(["removed_thing", "never_mentioned"], repo=tmp)
        self.assertEqual(list(hits), ["removed_thing"])
        self.assertEqual(hits["removed_thing"], {"code": ["common/a.txt:2"], "comment": 1})


if __name__ == "__main__":
    unittest.main()
