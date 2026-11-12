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


class RemovedFieldsTest(unittest.TestCase):
    """1.15 dropped `on_complete` & co. from every journal entry: `parsed
    --mod-uses` names the mod's entries that still set one."""

    def test_a_field_no_new_entity_sets_is_reported_with_the_mods_uses(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = os.path.join(tmp, "old"), os.path.join(tmp, "new")
            _write(os.path.join(old, "common", "journal_entries.json"), json.dumps({
                "je_a": ["=", {"on_complete": ["=", {"x": ["=", "1"]}], "weight": ["=", "1"]}],
                "je_b": ["=", {"weight": ["=", "2"]}],
            }))
            _write(os.path.join(new, "common", "journal_entries.json"), json.dumps({
                "je_a": ["=", {"outcome": ["=", {"x": ["=", "1"]}], "weight": ["=", "1"]}],
                "je_b": ["=", {"weight": ["=", "2"]}],
            }))
            _write(os.path.join(new, "manifest.json"), json.dumps({"entity_types": {
                "Journal Entries": {"dir": "game/common/journal_entries",
                                    "file": "common/journal_entries.json"}}}))
            fields = {}
            vpd.diff_parsed(new, old_dir=old, fields_out=fields)
            self.assertEqual(fields, {os.path.join("common", "journal_entries.json"): ["on_complete"]})
            mod = os.path.join(tmp, "mod")
            subprocess.run(["git", "init", "-q", mod], check=True)
            _write(os.path.join(mod, "common", "journal_entries", "j.txt"),
                   "je_x = {\n\ton_complete = { }\n\tscripted = {\n\t\ton_complete = { }\n\t}\n}\n")
            subprocess.run(["git", "add", "-A"], cwd=mod, check=True)
            hits = vpd.mod_field_uses(fields, new, repo=mod)
        self.assertEqual(hits, {("common/journal_entries", "on_complete"):
                                ["common/journal_entries/j.txt:2"]})


BOM = "﻿"

# Vanilla at the old commit of the fixture mirror, as {path below game/: text}.
VANILLA_OLD = {
    "common/laws/00_laws.txt": BOM + (
        "law_replaced = {\n\tgroup = lawgroup_x\n\tmodifier = {\n\t\ta_add = 1\n\t}\n}\n"
        "law_injected = {\n\tgroup = lawgroup_x\n}\n"
        "law_same = {\n\tgroup = lawgroup_y\n}\n"
        "law_moved = {\n\tgroup = lawgroup_y\n}\n"
        "law_reformatted = {\n\tgroup = lawgroup_y # the old comment\n}\n"
        "law_gone = {\n\tgroup = lawgroup_z\n}\n"
        "law_old_name = {\n\tgroup = lawgroup_z\n\tprogressiveness = 50\n}\n"),
    "common/script_values/00_values.txt": "vanilla_value = 5\nother_value = {\n\tvalue = 1\n}\n",
    "common/on_actions/00_code_on_actions.txt": "on_pulse = {\n\ton_actions = {\n\t\tvanilla_a\n\t}\n}\n",
    "common/technology/technologies/10_production.txt": "radio = {\n\tera = era_4\n}\n",
    "common/named_colors/00_colors.txt":
        "colors = {\n\tred = hsv { 0 1 1 }\n\tblue = hsv { 0.6 1 1 }\n}\n",
    "common/defines/00_defines.txt": BOM + (
        "NGame = {\n\tKEPT = 1\n\tCHANGED_SET = 2\n\tCHANGED_UNSET = 3\n\tREMOVED_READ = 0.5\n"
        "\tREMOVED_UNUSED = 9\n\tOLD_NAME = { 1 2 3 }\n}\n"),
    # No file of this folder differs between the commits, so it is never read.
    "common/buildings/00_buildings.txt": "building_untouched = {\r\n\tlevel = 1\r\n}\r\n",
    "events/vanilla_events.txt": (
        "namespace = vanilla\n"
        "vanilla.1 = {\n\ttype = country_event\n}\n"
        "vanilla.2 = {\n\ttype = country_event\n}\n"
        "vanilla.3 = {\n\ttype = country_event\n}\n"
        "vanilla.4 = {\n\ttype = country_event\n}\n"),
}

VANILLA_NEW = {
    # law_moved went to another file, law_reformatted lost its comment and
    # changed its indentation: neither is a change. law_old_name was renamed.
    "common/laws/00_laws.txt": BOM + (
        "law_replaced = {\n\tgroup = lawgroup_x\n\tmodifier = {\n\t\ta_add = 2\n\t}\n}\n"
        "law_injected = {\n\tgroup = lawgroup_x\n\tprogressiveness = 10\n}\n"
        "law_same = {\n\tgroup = lawgroup_y\n}\n"
        "law_reformatted = {\n    group   =   lawgroup_y\n\n}\n"
        "law_new_name = {\n\tgroup = lawgroup_z\n\tprogressiveness = 50\n}\n"),
    "common/laws/01_more_laws.txt": (
        "law_moved = {\n\tgroup = lawgroup_y\n}\n"
        "law_collides = {\n\tgroup = lawgroup_y\n}\n"
        "law_now_exists = {\n\tgroup = lawgroup_y\n}\n"),
    "common/script_values/00_values.txt": "vanilla_value = 6\nother_value = {\n\tvalue = 1\n}\n",
    "common/on_actions/00_code_on_actions.txt":
        "on_pulse = {\n\ton_actions = {\n\t\tvanilla_a\n\t\tvanilla_b\n\t}\n}\n",
    "common/technology/technologies/10_production.txt": "radio = {\n\tera = era_5\n}\n",
    "common/named_colors/00_colors.txt":
        "colors = {\n\tred = hsv { 0 1 1 }\n\tblue = hsv { 0.7 1 1 }\n}\n",
    "common/defines/00_defines.txt": BOM + (
        "NGame = {\n\tKEPT = 1\n\tCHANGED_SET = 4\n\tCHANGED_UNSET = 5\n\tNEW_NAME = { 1 2 3 }\n}\n"),
    "common/buildings/00_buildings.txt": VANILLA_OLD["common/buildings/00_buildings.txt"],
    "events/vanilla_events.txt": (
        "namespace = vanilla\n"
        "vanilla.1 = {\n\ttype = state_event\n}\n"
        "vanilla.3 = {\n\ttype = state_event\n}\n"
        "vanilla.4 = {\n\ttype = country_event\n}\n"),
}

MOD = {
    "common/laws/te_laws.txt": BOM + (
        "REPLACE:law_replaced = {\n\tgroup = lawgroup_x\n}\n"        # line 1
        "INJECT:law_injected = {\n\tmodifier = { b_add = 1 }\n}\n"   # line 4
        "REPLACE:law_same = {\n\tgroup = lawgroup_y\n}\n"            # line 7: vanilla's is unchanged
        "REPLACE:law_moved = {\n\tgroup = lawgroup_y\n}\n"           # line 10: only moved
        "REPLACE:law_reformatted = {\n\tgroup = lawgroup_y\n}\n"     # line 13: only reformatted
        "INJECT:law_gone = {\n\tmodifier = { b_add = 1 }\n}\n"       # line 16
        "TRY_INJECT:law_gone = {\n\tmodifier = { c_add = 1 }\n}\n"   # line 19
        "REPLACE_OR_CREATE:law_gone = {\n\tgroup = lawgroup_z\n}\n"  # line 22
        "INJECT:law_old_name = {\n\tmodifier = { b_add = 1 }\n}\n"   # line 25
        "law_collides = {\n\tgroup = lawgroup_te\n}\n"               # line 28
        "INJECT_OR_CREATE:law_now_exists = {\n\tgroup = lawgroup_te\n}\n"  # line 31
        "TRY_REPLACE:law_now_exists = {\n\tgroup = lawgroup_te\n}\n"       # line 34
        "law_te_own = {\n\tgroup = lawgroup_te\n}\n"),
    "common/script_values/te_values.txt": "# vanilla_value = 1\nvanilla_value = 7\n",
    "common/on_actions/te_a_on_actions.txt": "on_pulse = {\n\ton_actions = {\n\t\tte_a\n\t}\n}\n",
    "common/on_actions/te_b_on_actions.txt":
        "te_b = {\n}\non_pulse = {\n\ton_actions = {\n\t\tte_b\n\t}\n}\n",
    "common/technology/technologies/modified.txt": "INJECT:radio = {\n\tmodifier = { d_add = 1 }\n}\n",
    "common/named_colors/te_colors.txt": "colors = {\n\tgreen = hsv { 0.3 1 1 }\n\tblue = hsv { 0.5 1 1 }\n}\n",
    "common/defines/te_defines.txt":
        "NGame = {\n\tCHANGED_SET = 10\n\tREMOVED_READ = 0.75 # ours\n\tOLD_NAME = { 4 5 6 }\n}\n",
    "common/scripted_effects/te_effects.txt": (
        "te_effect = {\n"
        "\t# define:NGame|REMOVED_UNUSED was read here once\n"
        "\tadd_treasury = define:NGame|REMOVED_READ\n"
        "\ttrigger_event = { id = vanilla.2 }\n"
        "\ttrigger_event = { id = vanilla.3 } # vanilla.2 is gone\n"
        "}\n"),
    "events/te_events.txt": (
        "namespace = vanilla\n"
        "vanilla.1 = {\n\ttype = country_event\n\ttitle = vanilla.1.t\n}\n"
        "vanilla.4 = {\n\ttype = country_event\n}\n"
        "vanilla.2 = {\n\ttype = country_event\n\ttitle = vanilla.2.t\n}\n"),
    "gui/te_panel.gui": "widget = {\n\ttext = \"[GetDefine('NGame', 'REMOVED_READ')]\"\n}\n",
    "localization/english/te_l_english.yml":
        "l_english:\n te_key:0 \"#b [GetDefine('NGame','REMOVED_READ')]#!\"\n",
}


def _git(repo, *args):
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)


def _commit_tree(repo, files, message):
    """Make the mirror's `game/` hold exactly `files`, and commit."""
    _git(repo, "rm", "-r", "-q", "--ignore-unmatch", "game")
    for rel, text in files.items():
        _write(os.path.join(repo, "game", *rel.split("/")), text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    _git(repo, "tag", message)


class TargetsTest(unittest.TestCase):
    """`targets`: two commits of a fixture vanilla mirror against a fixture mod."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.repo = os.path.join(cls.tmp.name, "vic3")
        cls.mod = os.path.join(cls.tmp.name, "mod")
        os.makedirs(cls.repo)
        subprocess.run(["git", "init", "-q", cls.repo], check=True)
        _commit_tree(cls.repo, VANILLA_OLD, "v1")
        _commit_tree(cls.repo, VANILLA_NEW, "v2")
        for rel, text in MOD.items():
            _write(os.path.join(cls.mod, *rel.split("/")), text)
        cls.old, cls.new, cls.differing = vpd.read_vanilla_pair(cls.repo, "v1", "v2")
        cls.report = vpd.sweep_targets(cls.old, cls.new, vpd.read_mod_tree(cls.mod))
        cls.text = vpd.format_targets(cls.report)

    def section(self, title, lines=None):
        """The lines under the `== <title>...` heading, up to the next blank line."""
        lines = self.text if lines is None else lines
        start = next(i for i, line in enumerate(lines) if line.lstrip("\n").startswith("== " + title))
        out = []
        for line in lines[start + 1:]:
            if line.startswith("\n=="):
                break
            out.append(line)
        return out

    def test_the_git_layer_reads_both_commits_of_the_touched_folders_only(self):
        self.assertEqual(self.differing, 8)   # seven files edited, one added
        self.assertNotIn("common/buildings/00_buildings.txt", self.old)
        self.assertNotIn("common/buildings/00_buildings.txt", self.new)
        self.assertEqual(self.old, {p: t.lstrip(BOM) for p, t in VANILLA_OLD.items()
                                    if "buildings" not in p})
        self.assertIn("common/laws/01_more_laws.txt", self.new)
        self.assertNotIn("common/laws/01_more_laws.txt", self.old)

    def test_each_directive_family_on_changed_removed_and_added_entries(self):
        self.assertEqual(self.section("the mod's definitions"), [
            # removed from vanilla: what each directive does without a target
            "REPLACE_OR_CREATE  laws/law_gone  common/laws/te_laws.txt:22  (removed from 00_laws.txt; "
            "no target now: the mod's block creates the entry by itself)",
            "INJECT             laws/law_gone  common/laws/te_laws.txt:16  (removed from 00_laws.txt; "
            "no target now: the engine logs an error)",
            "TRY_INJECT         laws/law_gone  common/laws/te_laws.txt:19  (removed from 00_laws.txt; "
            "no target now: the block is skipped, with no log line)",
            "INJECT             laws/law_old_name  common/laws/te_laws.txt:25  (removed from 00_laws.txt; "
            "same body now under law_new_name; no target now: the engine logs an error)",
            # added to vanilla under a mod definition
            "TRY_REPLACE        laws/law_now_exists  common/laws/te_laws.txt:34  (added in "
            "01_more_laws.txt; has a target now and applies)",
            "bare               laws/law_collides  common/laws/te_laws.txt:28  (added in "
            "01_more_laws.txt; now a duplicate key: the first file read wins)",
            "INJECT_OR_CREATE   laws/law_now_exists  common/laws/te_laws.txt:31  (added in "
            "01_more_laws.txt; lands on vanilla's entry now instead of creating one)",
            # changed under the mod: restated copies first, then the injects
            "REPLACE            laws/law_replaced  common/laws/te_laws.txt:1  (changed in 00_laws.txt)",
            "bare               named_colors/blue  common/named_colors/te_colors.txt:3  "
            "(changed in 00_colors.txt)",
            "bare               script_values/vanilla_value  common/script_values/te_values.txt:2  "
            "(changed in 00_values.txt; the last file read wins)",
            "INJECT             laws/law_injected  common/laws/te_laws.txt:4  (changed in 00_laws.txt)",
            "INJECT             technology/technologies/radio  "
            "common/technology/technologies/modified.txt:1  (changed in 10_production.txt)",
        ])

    def test_an_unchanged_moved_or_reformatted_entry_is_not_a_target(self):
        keys = {r["key"] for r in self.report["targets"]}
        self.assertFalse(keys & {"law_same", "law_moved", "law_reformatted", "law_te_own"})
        self.assertEqual(self.report["counts"]["laws"], {"changed": 2, "removed": 2, "added": 3})

    def test_on_action_hooks_are_one_row_not_one_per_block(self):
        self.assertEqual(self.section("on_actions and history"), [
            "on_actions/on_pulse  (changed in 00_code_on_actions.txt)  2 mod block(s): "
            "common/on_actions/te_a_on_actions.txt:1, common/on_actions/te_b_on_actions.txt:3"])

    def test_removed_defines_with_the_mods_overrides_and_reads(self):
        self.assertEqual(self.section("defines vanilla removed"), [
            "NGame|OLD_NAME = { 1 2 3 }  (removed from 00_defines.txt; same value now under NEW_NAME)",
            "    set   common/defines/te_defines.txt:4  = { 4 5 6 }",
            "NGame|REMOVED_READ = 0.5  (removed from 00_defines.txt)",
            "    set   common/defines/te_defines.txt:3  = 0.75",
            "    read  common/scripted_effects/te_effects.txt:3",
            "    read  gui/te_panel.gui:2",
            "    read  localization/english/te_l_english.yml:2",
            # its only mention in the mod is a comment
            "NGame|REMOVED_UNUSED = 9  (removed from 00_defines.txt)  the mod neither sets nor reads it",
        ])

    def test_changed_defines_only_where_the_mod_sets_one(self):
        self.assertEqual(self.section("changed defines the mod sets"), [
            "NGame|CHANGED_SET  2 -> 4  common/defines/te_defines.txt:2  = 10"])
        self.assertEqual(self.report["counts"]["defines"], {"changed": 2, "removed": 3, "added": 1})

    def test_events_redefined_and_removed_events_still_named(self):
        self.assertEqual(self.section("vanilla events the mod"), [
            "redefined  vanilla.1  events/te_events.txt:2  (changed in vanilla_events.txt)",
            "redefined  vanilla.2  events/te_events.txt:9  (removed from vanilla_events.txt)",
            # not the mod's `title = vanilla.2.t`, not the comment on line 5
            "named      vanilla.2  common/scripted_effects/te_effects.txt:4  "
            "(removed from vanilla_events.txt)",
        ])
        self.assertEqual(self.report["counts"]["events"], {"changed": 2, "removed": 1})

    def test_vanillas_diff_of_each_restated_entry(self):
        diffs = self.section("vanilla's diff of each changed entry the mod restates")
        self.assertEqual([l for l in diffs if l.startswith("@@@@@@")], [
            "@@@@@@ laws/law_replaced  (changed in 00_laws.txt)",
            "@@@@@@ named_colors/blue  (changed in 00_colors.txt)",
            "@@@@@@ script_values/vanilla_value  (changed in 00_values.txt)"])
        start = diffs.index("@@@@@@ laws/law_replaced  (changed in 00_laws.txt)")
        self.assertEqual(diffs[start + 1:start + 9], [
            "@@ -1,6 +1,6 @@",
            " law_replaced = {",
            " \tgroup = lawgroup_x",
            " \tmodifier = {",
            "-\t\ta_add = 1",
            "+\t\ta_add = 2",
            " \t}",
            " }"])
        every = self.section("vanilla's diff of each changed entry the mod defines",
                             vpd.format_targets(self.report, diffs="all"))
        self.assertEqual([l for l in every if l.startswith("@@@@@@")], [
            "@@@@@@ laws/law_injected  (changed in 00_laws.txt)",
            "@@@@@@ laws/law_replaced  (changed in 00_laws.txt)",
            "@@@@@@ named_colors/blue  (changed in 00_colors.txt)",
            "@@@@@@ on_actions/on_pulse  (changed in 00_code_on_actions.txt)",
            "@@@@@@ script_values/vanilla_value  (changed in 00_values.txt)",
            "@@@@@@ technology/technologies/radio  (changed in 10_production.txt)"])
        self.assertFalse([l for l in vpd.format_targets(self.report, diffs="none") if "@@" in l])

    def test_the_comparison_needs_no_git(self):
        report = vpd.sweep_targets(VANILLA_OLD, VANILLA_NEW, MOD)
        self.assertEqual(vpd.format_targets(report), self.text)

    def test_cli(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vpd.main(["targets", "v1", "v2", "--vanilla-repo", self.repo,
                             "--mod-root", self.mod, "--diffs", "none"])
        self.assertEqual(code, 0)
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0], f"vanilla v1 -> v2 ({self.repo}): 8 script file(s) differ")
        self.assertEqual(lines[1:4], [
            "top-level entries of vanilla's common/ (a define counts as one): "
            "8 changed, 4 added, 5 removed in 6 folder(s)",
            "  defines 6, laws 7, named_colors 1, on_actions 1, script_values 1, "
            "technology/technologies 1",
            "vanilla events: 2 changed, 0 added, 1 removed"])
        self.assertIn("REPLACE            laws/law_replaced  common/laws/te_laws.txt:1  "
                      "(changed in 00_laws.txt)", lines)

    def test_cli_says_what_is_missing(self):
        import contextlib
        import io
        for argv, message in (
                (["targets", "v1", "no_such_tag", "--vanilla-repo", self.repo], "no commit 'no_such_tag'"),
                (["targets", "v1", "--upload-pack=x", "--vanilla-repo", self.repo], None),
                (["targets", "v1", "v2", "--vanilla-repo", os.path.join(self.tmp.name, "absent")],
                 "no vanilla mirror at")):
            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                try:
                    code = vpd.main(argv + ["--mod-root", self.mod])
                except SystemExit as exc:   # argparse refuses an option-like ref itself
                    code = exc.code
            self.assertEqual(code, 2, argv)
            if message:
                self.assertIn(message, err.getvalue())


class ConsequenceTest(unittest.TestCase):
    """Every directive the engine takes, against each kind of vanilla change."""

    def test_every_directive_has_a_reading_when_its_target_goes_or_appears(self):
        directives = sorted(vpd.REPLACE_DIRECTIVES | vpd.INJECT_DIRECTIVES) + [None]
        self.assertEqual(len(directives), 7)
        for status in ("removed", "added"):
            for directive in directives:
                self.assertTrue(vpd.consequence(status, directive), (status, directive))
        # A changed target under a directive needs no note: the directive says it.
        self.assertEqual({vpd.consequence("changed", d) for d in directives}, {""})
        # The plain forms error without a target; only they do.
        errors = [d for d in directives if "error" in vpd.consequence("removed", d)]
        self.assertEqual(errors, ["INJECT", "REPLACE"])


if __name__ == "__main__":
    unittest.main()
