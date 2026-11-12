"""Tests for `scripts/analysis/vanilla_patch_diff.py`.

Builds tiny old/new engine-doc dumps and vanilla_parsed/ snapshots in a
tempdir; needs no Victoria 3 install and no vanilla clone.

Run: python3 -m unittest test_vanilla_patch_diff
"""

import json
import os
import shutil
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


BOM = "\ufeff"

# Vanilla at the old commit of the fixture mirror, as {path below game/: text}.
VANILLA_OLD = {
    "common/laws/00_laws.txt": BOM + (
        "law_replaced = {\n\tgroup = lawgroup_x\n\tmodifier = {\n\t\ta_add = 1\n\t}\n}\n"
        "law_injected = {\n\tgroup = lawgroup_x\n}\n"
        "law_same = {\n\tgroup = lawgroup_y\n}\n"
        "law_moved = {\n\tgroup = lawgroup_y\n}\n"
        "law_reformatted = {\n\tgroup = lawgroup_y # the old comment\n}\n"
        "law_gone = {\n\tgroup = lawgroup_z\n}\n"
        "law_old_name = {\n\tgroup = lawgroup_z\n\tprogressiveness = 50\n}\n"
        "law_mod_has_too = {\n\tgroup = lawgroup_z\n}\n"),
    # Vanilla's own line endings and BOM: LF here, CRLF at the new commit.
    "common/laws/02_crlf_laws.txt": BOM + (
        "law_crlf_same = {\n\tgroup = lawgroup_y\n}\n"
        "law_crlf_changed = {\n\tgroup = lawgroup_y\n}\n"),
    # A brace is missing, at both commits: the scanner says so.
    "common/laws/09_unclosed.txt": "law_open = {\n\tgroup = lawgroup_y\n",
    "common/script_values/00_values.txt": "vanilla_value = 5\nother_value = {\n\tvalue = 1\n}\n",
    "common/on_actions/00_code_on_actions.txt": "on_pulse = {\n\ton_actions = {\n\t\tvanilla_a\n\t}\n}\n",
    # A second definition of on_pulse, which no commit touches.
    "common/on_actions/01_other_on_actions.txt": "on_pulse = {\n\tevents = {\n\t\tvanilla.4\n\t}\n}\n",
    "common/technology/technologies/10_production.txt": "radio = {\n\tera = era_4\n}\n",
    "common/named_colors/00_colors.txt":
        "colors = {\n\tred = hsv { 0 1 1 }\n\tblue = hsv { 0.6 1 1 }\n}\n",
    "common/scripted_triggers/00_triggers.txt": (
        "van_trigger = {\n\talways = yes\n}\n"
        "van_unused_trigger = {\n\talways = no\n}\n"
        "van_kept_trigger = {\n\talways = yes\n}\n"),
    "common/scripted_rules/00_scripted_rules.txt": (
        "rule_a = {\n\talways = yes\n}\n"
        "rule_b = {\n\talways = yes\n}\n"),
    "common/defines/00_defines.txt": BOM + (
        "NGame = {\n\tKEPT = 1\n\tCHANGED_SET = 2\n\tCHANGED_UNSET = 3\n\tREMOVED_READ = 0.5\n"
        "\tREMOVED_UNUSED = 250\n\tOLD_NAME = { 1 2 3 }\n\tMOVED_AWAY = 7\n}\n"
        "NOther = {\n\tZ = 1\n}\n"),
    # No file of this folder differs between the commits, so it is never read.
    "common/buildings/00_buildings.txt": "building_untouched = {\r\n\tlevel = 1\r\n}\r\n",
    "events/vanilla_events.txt": (
        "namespace = vanilla\n"
        "vanilla.1 = {\n\ttype = country_event\n}\n"
        "vanilla.2 = {\n\ttype = country_event\n}\n"
        "vanilla.3 = {\n\ttype = country_event\n}\n"
        "vanilla.4 = {\n\ttype = country_event\n}\n"),
    "gfx/portraits/portrait_modifiers/01_clothes.txt": (
        "clothes = {\n\tusage = game\n}\n"
        "hair = {\n\tusage = game\n}\n"),
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
    "common/laws/02_crlf_laws.txt": BOM + (
        "law_crlf_same = {\r\n\tgroup = lawgroup_y\r\n}\r\n"
        "law_crlf_changed = {\r\n\tgroup = lawgroup_w\r\n}\r\n"),
    "common/laws/09_unclosed.txt": "law_open = {\n\tgroup = lawgroup_y\n",
    "common/script_values/00_values.txt": "vanilla_value = 6\nother_value = {\n\tvalue = 1\n}\n",
    "common/on_actions/00_code_on_actions.txt":
        "on_pulse = {\n\ton_actions = {\n\t\tvanilla_a\n\t\tvanilla_b\n\t}\n}\n",
    "common/on_actions/01_other_on_actions.txt": "on_pulse = {\n\tevents = {\n\t\tvanilla.4\n\t}\n}\n",
    "common/technology/technologies/10_production.txt": "radio = {\n\tera = era_5\n}\n",
    "common/named_colors/00_colors.txt":
        "colors = {\n\tred = hsv { 0 1 1 }\n\tblue = hsv { 0.7 1 1 }\n}\n",
    "common/scripted_triggers/00_triggers.txt": "van_kept_trigger = {\n\talways = yes\n}\n",
    "common/scripted_rules/00_scripted_rules.txt": (
        "rule_a = {\n\talways = no\n}\n"
        "rule_b = {\n\talways = yes\n}\n"
        "rule_new = {\n\talways = yes\n}\n"),
    # REMOVED_READ's 0.5 is also HALF's, REMOVED_UNUSED's 250 is four new
    # defines': no rename. OLD_NAME's list is NEW_NAME's alone. MOVED_AWAY
    # changed block.
    "common/defines/00_defines.txt": BOM + (
        "NGame = {\n\tKEPT = 1\n\tCHANGED_SET = 4\n\tCHANGED_UNSET = 5\n\tNEW_NAME = { 1 2 3 }\n"
        "\tHALF = 0.5\n\tQ1 = 250\n\tQ2 = 250\n\tQ3 = 250\n\tQ4 = 250\n}\n"
        "NOther = {\n\tZ = 1\n\tMOVED_AWAY = 7\n}\n"),
    "common/buildings/00_buildings.txt": VANILLA_OLD["common/buildings/00_buildings.txt"],
    "events/vanilla_events.txt": (
        "namespace = vanilla\n"
        "vanilla.1 = {\n\ttype = state_event\n}\n"
        "vanilla.3 = {\n\ttype = state_event\n}\n"
        "vanilla.4 = {\n\ttype = country_event\n}\n"),
    "gfx/portraits/portrait_modifiers/01_clothes.txt": (
        "outfits = {\n\tusage = game\n}\n"
        "hair = {\n\tusage = game\n}\n"),
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
        "law_te_own = {\n\tgroup = lawgroup_te\n}\n"                 # line 37
        "REPLACE:law_crlf_same = {\n\tgroup = lawgroup_y\n}\n"       # line 40: only its line endings
        "REPLACE:law_crlf_changed = {\n\tgroup = lawgroup_y\n}\n"    # line 43
        "law_mod_has_too = {\n\tgroup = lawgroup_te\n}\n"            # line 46
        "INJECT:law_mod_has_too = {\n\tmodifier = { b_add = 1 }\n}\n"),  # line 49
    "common/script_values/te_values.txt": "# vanilla_value = 1\nvanilla_value = 7\n",
    "common/on_actions/te_a_on_actions.txt": "on_pulse = {\n\ton_actions = {\n\t\tte_a\n\t}\n}\n",
    "common/on_actions/te_b_on_actions.txt":
        "te_b = {\n}\non_pulse = {\n\ton_actions = {\n\t\tte_b\n\t}\n}\n",
    "common/technology/technologies/modified.txt": "INJECT:radio = {\n\tmodifier = { d_add = 1 }\n}\n",
    "common/named_colors/te_colors.txt": "colors = {\n\tgreen = hsv { 0.3 1 1 }\n\tblue = hsv { 0.5 1 1 }\n}\n",
    # A copy of vanilla's file at vanilla's path: the game reads the mod's only.
    "common/scripted_rules/00_scripted_rules.txt": (
        "rule_a = {\n\talways = yes\n}\n"
        "rule_b = {\n\talways = yes # TE\n}\n"),
    "common/defines/te_defines.txt": (
        "NGame = {\n\tCHANGED_SET = 10\n\tREMOVED_READ = 0.75 # ours\n\tOLD_NAME = { 4 5 6 }\n"
        "\tMOVED_AWAY = 8\n}\n"),
    "common/scripted_effects/te_effects.txt": (
        "te_effect = {\n"
        "\t# define:NGame|REMOVED_UNUSED was read here once\n"
        "\tadd_treasury = define:NGame|REMOVED_READ\n"
        "\ttrigger_event = { id = vanilla.2 }\n"
        "\ttrigger_event = { id = vanilla.3 } # vanilla.2 is gone\n"
        "\tif = { limit = { van_trigger = yes } }\n"
        "\t# van_unused_trigger = yes\n"
        "}\n"),
    "events/te_events.txt": (
        "namespace = vanilla\n"
        "vanilla.1 = {\n\ttype = country_event\n\ttitle = vanilla.1.t\n}\n"
        "vanilla.4 = {\n\ttype = country_event\n\ttrigger = { van_trigger = yes }\n}\n"
        "vanilla.2 = {\n\ttype = country_event\n\ttitle = vanilla.2.t\n}\n"),
    "gfx/portraits/portrait_modifiers/te_clothes.txt": BOM + "INJECT:clothes = {\n\tte_suit = { }\n}\n",
    "gui/te_panel.gui": "widget = {\n\ttext = \"[GetDefine('NGame', 'REMOVED_READ')]\"\n}\n",
    "localization/english/te_l_english.yml": (
        "l_english:\n te_key:0 \"#b [GetDefine('NGame','REMOVED_READ')]#!\"\n"
        " te_tooltip:0 \"Needs van_trigger.\"\n"),
}

# The first section of the report for the trees above: one line per mod definition.
EXPECTED_TARGETS = [
    # removed from vanilla: what each directive does without a target
    "REPLACE_OR_CREATE  laws/law_gone  common/laws/te_laws.txt:22  (removed from 00_laws.txt; "
    "no target now: the mod's block creates the entry by itself)",
    "bare               laws/law_mod_has_too  common/laws/te_laws.txt:46  (removed from 00_laws.txt; "
    "the mod's is now the only definition)",
    "INJECT             gfx/portraits/portrait_modifiers/clothes  "
    "gfx/portraits/portrait_modifiers/te_clothes.txt:1  (removed from 01_clothes.txt; "
    "same body now under outfits; no target now: the engine logs an error)",
    "INJECT             laws/law_gone  common/laws/te_laws.txt:16  (removed from 00_laws.txt; "
    "no target now: the engine logs an error)",
    "TRY_INJECT         laws/law_gone  common/laws/te_laws.txt:19  (removed from 00_laws.txt; "
    "no target now: the block is skipped, with no log line)",
    # the mod defines this one itself, so its INJECT still lands
    "INJECT             laws/law_mod_has_too  common/laws/te_laws.txt:49  (removed from 00_laws.txt; "
    "its target is now the mod's own definition, common/laws/te_laws.txt:46)",
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
    "REPLACE            laws/law_crlf_changed  common/laws/te_laws.txt:43  (changed in 02_crlf_laws.txt)",
    "REPLACE            laws/law_replaced  common/laws/te_laws.txt:1  (changed in 00_laws.txt)",
    "bare               named_colors/blue  common/named_colors/te_colors.txt:3  "
    "(changed in 00_colors.txt)",
    "bare               script_values/vanilla_value  common/script_values/te_values.txt:2  "
    "(changed in 00_values.txt; the last file read wins)",
    "bare               scripted_rules/rule_a  common/scripted_rules/00_scripted_rules.txt:1  "
    "(changed in 00_scripted_rules.txt; in the mod's copy of vanilla's file, which replaces it whole)",
    "INJECT             laws/law_injected  common/laws/te_laws.txt:4  (changed in 00_laws.txt)",
    "INJECT             technology/technologies/radio  "
    "common/technology/technologies/modified.txt:1  (changed in 10_production.txt)",
]


def _git(repo, *args):
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)


def _commit_tree(repo, files, message, root="game"):
    """Make the repository's `root` folder hold exactly `files`, and commit."""
    _git(repo, "rm", "-r", "-q", "--ignore-unmatch", root)
    for rel, text in files.items():
        _write(os.path.join(repo, root, *rel.split("/")), text)
    # A texture beside the script, different at each commit: never read.
    with open(os.path.join(repo, root, "gfx", "portraits", "te_test.dds"), "wb") as fh:
        fh.write(message.encode() * 64 + bytes(range(256)))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    _git(repo, "tag", message)


def _run_cli(argv):
    """(exit code, stdout, stderr) of `vanilla_patch_diff.py <argv>`."""
    import contextlib
    import io
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = vpd.main(argv)
        except SystemExit as exc:   # argparse's own refusal
            code = exc.code
    return code, out.getvalue(), err.getvalue()


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
        """The lines under the `== <title>...` heading, up to the next heading."""
        lines = self.text if lines is None else lines
        start = next(i for i, line in enumerate(lines) if line.lstrip("\n").startswith("== " + title))
        out = []
        for line in lines[start + 1:]:
            if line.startswith("\n=="):
                break
            out.append(line)
        return out

    def test_the_git_layer_reads_both_commits_of_the_touched_folders_only(self):
        self.assertEqual(self.differing, 12)   # eleven script files edited, one added
        self.assertNotIn("common/buildings/00_buildings.txt", self.old)
        self.assertNotIn("common/buildings/00_buildings.txt", self.new)
        # What is read is the committed text, less its BOM; CRLF stays.
        self.assertEqual(self.old, {p: t.lstrip(BOM) for p, t in VANILLA_OLD.items()
                                    if "buildings" not in p})
        self.assertEqual(self.new, {p: t.lstrip(BOM) for p, t in VANILLA_NEW.items()
                                    if "buildings" not in p})
        self.assertIn("\r\n", self.new["common/laws/02_crlf_laws.txt"])
        # Unchanged files of a touched folder are read too: a key is looked up across it.
        self.assertIn("common/laws/09_unclosed.txt", self.old)
        # Only .txt is listed, so the texture in gfx/ is never read.
        self.assertFalse([p for p in (*self.old, *self.new) if not p.endswith(".txt")])

    def test_each_directive_family_on_changed_removed_and_added_entries(self):
        self.assertEqual(self.section("the mod's definitions"), EXPECTED_TARGETS)

    def test_an_unchanged_moved_or_reformatted_entry_is_not_a_target(self):
        keys = {r["key"] for r in self.report["targets"]}
        self.assertFalse(keys & {"law_same", "law_moved", "law_reformatted", "law_te_own",
                                 "law_crlf_same", "law_open", "rule_b"})
        self.assertEqual(self.report["counts"]["laws"], {"changed": 3, "removed": 3, "added": 3})

    def test_a_script_folder_under_gfx_is_swept(self):
        """The mod's `INJECT:clothes` lives in gfx/portraits/portrait_modifiers."""
        row = next(r for r in self.report["targets"] if r["key"] == "clothes")
        self.assertEqual((row["group"], row["directive"], row["status"], row["renamed_to"]),
                         ("gfx/portraits/portrait_modifiers", "INJECT", "removed", ["outfits"]))
        self.assertEqual(vpd.group_of("gfx/map/fleet_entities/01_fleet_entities.txt"),
                         "gfx/map/fleet_entities")
        self.assertIsNone(vpd.group_of("gfx/portraits/te_test.dds"))

    def test_on_action_hooks_are_one_row_and_name_the_file_that_changed(self):
        self.assertEqual(self.section("on_actions and history"), [
            # on_pulse is in two vanilla files; one changed
            "on_actions/on_pulse  (changed in 00_code_on_actions.txt)  2 mod block(s): "
            "common/on_actions/te_a_on_actions.txt:1, common/on_actions/te_b_on_actions.txt:3"])
        diff = next(d for d in self.report["diffs"] if d["key"] == "on_pulse")
        self.assertNotIn("vanilla.4", "\n".join(diff["lines"]))   # the untouched definition

    def test_a_mod_file_at_a_changed_vanilla_files_path(self):
        self.assertEqual(self.section("mod files at the path"), [
            "common/scripted_rules/00_scripted_rules.txt  (vanilla changed its file)"])

    def test_removed_names_the_mod_still_uses(self):
        self.assertEqual(self.section("entries and events vanilla removed whose name"), [
            "events/vanilla.2  (removed from vanilla_events.txt)  1 use(s):",
            # not the mod's own redefinition, its `title = vanilla.2.t`, or the comment on line 5
            "    common/scripted_effects/te_effects.txt:4",
            "scripted_triggers/van_trigger  (removed from 00_triggers.txt)  3 use(s):",
            "    common/scripted_effects/te_effects.txt:6",
            "    events/te_events.txt:8",
            "    localization/english/te_l_english.yml:3",
        ])
        self.assertEqual(self.section("removed and used nowhere else"), [
            "gfx/portraits/portrait_modifiers: clothes",
            "laws: law_gone, law_mod_has_too, law_old_name",
            # its only mention in the mod is a comment
            "scripted_triggers: van_unused_trigger",
        ])

    def test_removed_defines_with_the_mods_overrides_and_reads(self):
        self.assertEqual(self.section("defines vanilla removed"), [
            "NGame|MOVED_AWAY = 7  (removed from 00_defines.txt; now NOther|MOVED_AWAY)",
            "    set   common/defines/te_defines.txt:5  = 8",
            "NGame|OLD_NAME = { 1 2 3 }  (removed from 00_defines.txt; same value now under NEW_NAME)",
            "    set   common/defines/te_defines.txt:4  = { 4 5 6 }",
            # 0.5 is also the new HALF's value: too common a value to call a rename
            "NGame|REMOVED_READ = 0.5  (removed from 00_defines.txt)",
            "    set   common/defines/te_defines.txt:3  = 0.75",
            "    read  common/scripted_effects/te_effects.txt:3",
            "    read  gui/te_panel.gui:2",
            "    read  localization/english/te_l_english.yml:2",
            # four new defines hold 250: no hint. Its only mention in the mod is a comment.
            "NGame|REMOVED_UNUSED = 250  (removed from 00_defines.txt)  the mod neither sets nor reads it",
        ])

    def test_changed_defines_only_where_the_mod_sets_one(self):
        self.assertEqual(self.section("changed defines the mod sets"), [
            "NGame|CHANGED_SET  2 -> 4  common/defines/te_defines.txt:2  = 10"])
        self.assertEqual(self.report["counts"]["defines"], {"changed": 2, "removed": 4, "added": 7})

    def test_events_the_mod_redefines(self):
        self.assertEqual(self.section("vanilla events the mod redefines"), [
            "redefined  vanilla.1  events/te_events.txt:2  (changed in vanilla_events.txt)",
            "redefined  vanilla.2  events/te_events.txt:10  (removed from vanilla_events.txt)",
        ])
        self.assertEqual(self.report["counts"]["events"], {"changed": 2, "removed": 1})

    def test_a_file_the_scanner_could_not_read_cleanly_is_named(self):
        self.assertEqual(self.section("files the scanner could not read cleanly"), [
            "game/common/laws/09_unclosed.txt  (the old commit and the new commit): "
            "1 block(s) still open at the end of the file"])

    def test_vanillas_diff_of_each_restated_entry(self):
        diffs = self.section("vanilla's diff of each changed entry the mod restates")
        self.assertEqual([l for l in diffs if l.startswith("@@@@@@")], [
            "@@@@@@ laws/law_crlf_changed  (changed in 02_crlf_laws.txt)",
            "@@@@@@ laws/law_replaced  (changed in 00_laws.txt)",
            "@@@@@@ named_colors/blue  (changed in 00_colors.txt)",
            "@@@@@@ script_values/vanilla_value  (changed in 00_values.txt)",
            "@@@@@@ scripted_rules/rule_a  (changed in 00_scripted_rules.txt)"])
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
        # A file that went from LF to CRLF shows its one real change.
        start = diffs.index("@@@@@@ laws/law_crlf_changed  (changed in 02_crlf_laws.txt)")
        self.assertEqual(diffs[start + 1:start + 6], [
            "@@ -1,3 +1,3 @@",
            " law_crlf_changed = {",
            "-\tgroup = lawgroup_y",
            "+\tgroup = lawgroup_w",
            " }"])
        every = self.section("vanilla's diff of each changed entry the mod defines",
                             vpd.format_targets(self.report, diffs="all"))
        self.assertEqual([l for l in every if l.startswith("@@@@@@")], [
            "@@@@@@ laws/law_crlf_changed  (changed in 02_crlf_laws.txt)",
            "@@@@@@ laws/law_injected  (changed in 00_laws.txt)",
            "@@@@@@ laws/law_replaced  (changed in 00_laws.txt)",
            "@@@@@@ named_colors/blue  (changed in 00_colors.txt)",
            "@@@@@@ on_actions/on_pulse  (changed in 00_code_on_actions.txt)",
            "@@@@@@ script_values/vanilla_value  (changed in 00_values.txt)",
            "@@@@@@ scripted_rules/rule_a  (changed in 00_scripted_rules.txt)",
            "@@@@@@ technology/technologies/radio  (changed in 10_production.txt)"])
        self.assertFalse([l for l in vpd.format_targets(self.report, diffs="none") if "@@" in l])

    def test_the_comparison_needs_no_git(self):
        def decoded(tree):   # as a utf-8-sig read gives it
            return {p: t.lstrip(BOM) for p, t in tree.items()}
        report = vpd.sweep_targets(decoded(VANILLA_OLD), decoded(VANILLA_NEW), decoded(MOD))
        self.assertEqual(vpd.format_targets(report), self.text)

    def test_cli(self):
        code, out, _err = _run_cli(["targets", "v1", "v2", "--vanilla-repo", self.repo,
                                    "--mod-root", self.mod, "--diffs", "none"])
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], f"vanilla v1 -> v2 ({self.repo}): 12 script file(s) differ")
        self.assertEqual(lines[1:4], [
            "top-level entries of vanilla's common/ and gfx/ script (a define counts as one): "
            "10 changed, 12 added, 10 removed in 9 folder(s)",
            "  defines 13, gfx/portraits/portrait_modifiers 2, laws 9, named_colors 1, on_actions 1, "
            "script_values 1, scripted_rules 2, scripted_triggers 2, technology/technologies 1",
            "vanilla events: 2 changed, 0 added, 1 removed"])
        self.assertIn("REPLACE            laws/law_replaced  common/laws/te_laws.txt:1  "
                      "(changed in 00_laws.txt)", lines)

    def test_cli_refuses_a_bad_ref_or_a_missing_mirror(self):
        for argv, message in (
                (["targets", "v1", "no_such_tag", "--vanilla-repo", self.repo], "no commit 'no_such_tag'"),
                (["targets", "v1", "--upload-pack=x", "--vanilla-repo", self.repo], ""),
                (["targets", "v1", "v2", "--vanilla-repo", os.path.join(self.tmp.name, "absent")],
                 "no vanilla mirror at")):
            code, out, err = _run_cli(argv + ["--mod-root", self.mod])
            self.assertEqual((code, out), (2, ""), argv)
            self.assertIn(message, err)

    def test_cli_refuses_a_repository_that_is_not_laid_out_as_the_mirror(self):
        """A clean report from the wrong repository would read as "nothing to do"."""
        other = os.path.join(self.tmp.name, "not_the_mirror")
        os.makedirs(other)
        subprocess.run(["git", "init", "-q", other], check=True)
        for tag in ("v1", "v2"):     # the game's files at the root, not under game/
            _commit_tree(other, VANILLA_OLD if tag == "v1" else VANILLA_NEW, tag, root=".")
        code, out, err = _run_cli(["targets", "v1", "v2", "--vanilla-repo", other,
                                   "--mod-root", self.mod])
        self.assertEqual((code, out), (2, ""))
        self.assertIn("holds no .txt file under game/common", err)

    def test_cli_refuses_a_mod_root_with_no_script(self):
        empty = os.path.join(self.tmp.name, "empty")
        os.makedirs(os.path.join(empty, "gui"))
        for root in (os.path.join(self.tmp.name, "nowhere"), empty,
                     os.path.join(self.mod, "common")):   # one level too deep
            code, out, err = _run_cli(["targets", "v1", "v2", "--vanilla-repo", self.repo,
                                       "--mod-root", root])
            self.assertEqual((code, out), (2, ""), root)
            self.assertIn("no script under", err)

    def test_a_folder_the_checkout_lacks_is_read_from_gits_index(self):
        """A sparse worktree of this repository has no gfx/ on disk."""
        mod = os.path.join(self.tmp.name, "sparse_mod")
        for rel, text in MOD.items():
            _write(os.path.join(mod, *rel.split("/")), text)
        subprocess.run(["git", "init", "-q", mod], check=True)
        _git(mod, "add", "-A")
        _git(mod, "commit", "-q", "-m", "mod")
        shutil.rmtree(os.path.join(mod, "gfx"))
        on_disk = vpd.read_mod_tree(mod)
        self.assertFalse([p for p in on_disk if p.startswith("gfx/")])
        with_git = vpd.read_mod_tree(mod, git_fallback=True)
        self.assertEqual(with_git, {p: t.lstrip(BOM) for p, t in MOD.items()})


class SweepEdgesTest(unittest.TestCase):
    """Small trees, no git: the readings at the edges."""

    def lines(self, old, new, mod):
        return vpd.format_targets(vpd.sweep_targets(old, new, mod), diffs="none")

    def test_a_removed_name_the_mod_only_calls_is_listed(self):
        """A removed scripted trigger, effect, value or war goal the mod calls
        by name is no REPLACE or INJECT target, and it is the breakage."""
        entry = "{0} = {{\n\tv = 1\n}}\n".format
        old = {"common/scripted_triggers/00.txt": entry("van_trigger") + entry("keep_t"),
               "common/scripted_effects/00.txt": entry("van_effect") + entry("keep_e"),
               "common/script_values/00.txt": "van_value = 3\nkeep_v = 1\n",
               "common/war_goal_types/00.txt": entry("van_wargoal") + entry("keep_w")}
        new = {"common/scripted_triggers/00.txt": entry("keep_t"),
               "common/scripted_effects/00.txt": entry("keep_e"),
               "common/script_values/00.txt": "keep_v = 1\n",
               "common/war_goal_types/00.txt": entry("keep_w")}
        mod = {"common/scripted_effects/te.txt":
               "te_e = {\n\tif = { limit = { van_trigger = yes } van_effect = yes }\n"
               "\tadd_treasury = van_value\n\tcreate_diplomatic_play = { type = van_wargoal }\n}\n"}
        report = vpd.sweep_targets(old, new, mod)
        self.assertEqual(report["targets"], [])
        self.assertEqual({(r["group"], r["key"]): r["uses"] for r in report["removed"]}, {
            ("script_values", "van_value"): ["common/scripted_effects/te.txt:3"],
            ("scripted_effects", "van_effect"): ["common/scripted_effects/te.txt:2"],
            ("scripted_triggers", "van_trigger"): ["common/scripted_effects/te.txt:2"],
            ("war_goal_types", "van_wargoal"): ["common/scripted_effects/te.txt:4"]})

    def test_a_much_used_removed_name_shows_ten_uses_and_a_count(self):
        old = {"common/goods/00.txt": "tea = {\n}\ngrain = {\n}\n"}
        new = {"common/goods/00.txt": "grain = {\n}\n"}
        mod = {"common/buildings/te.txt": "".join(f"b_{i} = {{ input = tea }}\n" for i in range(13))}
        lines = self.lines(old, new, mod)
        start = lines.index("goods/tea  (removed from 00.txt)  13 use(s):")
        self.assertEqual(lines[start + 1], "    common/buildings/te.txt:1")
        self.assertEqual(lines[start + 10:start + 12], ["    common/buildings/te.txt:10", "    (+3 more)"])

    def test_a_directive_on_a_removed_entry_the_mod_defines_itself_still_has_a_target(self):
        old = {"common/laws/00.txt": "law_x = {\n}\nkeep = {\n}\n"}
        new = {"common/laws/00.txt": "keep = {\n}\n"}
        mod = {"common/laws/te_a.txt": "law_x = {\n}\n",
               "common/laws/te_b.txt": "INJECT:law_x = {\n\tm = 1\n}\nTRY_REPLACE:law_x = {\n}\n"}
        notes = {(r["directive"], r["note"]) for r in vpd.sweep_targets(old, new, mod)["targets"]}
        self.assertEqual(notes, {
            (None, "the mod's is now the only definition"),
            ("INJECT", "its target is now the mod's own definition, common/laws/te_a.txt:1"),
            ("TRY_REPLACE", "its target is now the mod's own definition, common/laws/te_a.txt:1")})

    def test_a_bare_entry_in_a_mod_file_at_vanillas_path_is_not_a_duplicate(self):
        """The mod's file replaces vanilla's, so no bare-duplicate rule applies;
        an entry vanilla added to that file is missing from the mod's copy."""
        old = {"common/scripted_rules/00_rules.txt": "rule_a = {\n\tv = 1\n}\n"}
        new = {"common/scripted_rules/00_rules.txt": "rule_a = {\n\tv = 2\n}\nrule_new = {\n}\n"}
        mod = {"common/scripted_rules/00_rules.txt": "rule_a = {\n\tv = 1\n}\n",
               "common/scripted_rules/te_rules.txt": "rule_a = {\n\tv = 3\n}\n"}
        report = vpd.sweep_targets(old, new, mod)
        self.assertEqual([(r["file"], r["note"]) for r in report["targets"]], [
            ("common/scripted_rules/00_rules.txt",
             "in the mod's copy of vanilla's file, which replaces it whole"),
            ("common/scripted_rules/te_rules.txt", "the first file read wins")])
        self.assertEqual(report["same_path"],
                         [{"file": "common/scripted_rules/00_rules.txt", "status": "changed"}])
        # Line endings and comments are no change to a same-path file.
        crlf = {p: t.replace("\n", "\r\n") + "# a note\r\n" for p, t in old.items()}
        self.assertEqual(vpd.sweep_targets(old, crlf, mod)["same_path"], [])

    def test_a_rename_hint_is_capped_and_says_so(self):
        body = "{0} = {{\n\tgroup = g\n\tlevel = 3\n}}\n".format
        old = {"common/laws/00.txt": body("law_old")}
        new = {"common/laws/00.txt": "".join(body(f"law_new_{n}") for n in "abcd")}
        mod = {"common/laws/te.txt": "INJECT:law_old = {\n}\n"}
        self.assertIn("INJECT             laws/law_old  common/laws/te.txt:1  (removed from 00.txt; "
                      "same body now under law_new_a, law_new_b, law_new_c (+1 more); "
                      "no target now: the engine logs an error)", self.lines(old, new, mod))

    def test_scanner_warnings_on_the_mods_files_are_listed_too(self):
        old = {"common/laws/00.txt": "law_x = {\n\tv = 1\n}\n"}
        new = {"common/laws/00.txt": "law_x = {\n\tv = 2\n}\n}\n"}
        mod = {"common/laws/te.txt": "REPLACE:law_x = {\n\tv = 1\n"}
        self.assertEqual(vpd.sweep_targets(old, new, mod)["warnings"], [
            {"file": "common/laws/te.txt", "where": "the mod",
             "warning": "1 block(s) still open at the end of the file"},
            {"file": "game/common/laws/00.txt", "where": "the new commit",
             "warning": "line 4: '}' with no open block"}])


class ConsequenceTest(unittest.TestCase):
    """Every directive the engine takes, against each kind of vanilla change
    (the Load Order facts external_mod_overlap.LOAD_ORDER_MODEL records)."""

    ERROR = "no target now: the engine logs an error"
    SKIPPED = "no target now: the block is skipped, with no log line"
    CREATES = "no target now: the mod's block creates the entry by itself"

    def test_a_removed_target(self):
        self.assertEqual({d: vpd.consequence("removed", d) for d in DIRECTIVES}, {
            "REPLACE": self.ERROR, "INJECT": self.ERROR,
            "TRY_REPLACE": self.SKIPPED, "TRY_INJECT": self.SKIPPED,
            "REPLACE_OR_CREATE": self.CREATES, "INJECT_OR_CREATE": self.CREATES,
            None: "the mod's is now the only definition"})

    def test_a_new_vanilla_entry_under_a_mod_definition(self):
        lands = "lands on vanilla's entry now instead of creating one"
        self.assertEqual({d: vpd.consequence("added", d, vpd.emo.FIRST_WINS) for d in DIRECTIVES}, {
            "REPLACE": "vanilla defines its target now", "INJECT": "vanilla defines its target now",
            "TRY_REPLACE": "has a target now and applies", "TRY_INJECT": "has a target now and applies",
            "REPLACE_OR_CREATE": lands, "INJECT_OR_CREATE": lands,
            None: "now a duplicate key: the first file read wins"})
        self.assertEqual(vpd.consequence("added", None, vpd.emo.LAST_WINS),
                         "now a duplicate key: the last file read wins")
        self.assertEqual(vpd.consequence("added", None), "now a duplicate key")

    def test_a_changed_target_needs_no_note_under_a_directive(self):
        self.assertEqual({vpd.consequence("changed", d) for d in DIRECTIVES if d}, {""})
        self.assertEqual(vpd.consequence("changed", None, vpd.emo.LAST_WINS), "the last file read wins")

    def test_the_directives_are_the_engines_seven(self):
        self.assertEqual(set(DIRECTIVES) - {None}, vpd.REPLACE_DIRECTIVES | vpd.INJECT_DIRECTIVES)


DIRECTIVES = ("REPLACE", "TRY_REPLACE", "REPLACE_OR_CREATE",
              "INJECT", "TRY_INJECT", "INJECT_OR_CREATE", None)


if __name__ == "__main__":
    unittest.main()
