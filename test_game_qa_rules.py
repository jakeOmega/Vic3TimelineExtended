"""Tests for game_qa.rules: the rules a fresh save was made under, and a rule switched in a copy of it (#1599).

No game is needed. The saves here are built in the shape read from the harness's real fixtures on 2026-11-11:
a `SAV0100…` line whose last eight hex digits are the byte length of the `meta_data` block that follows, the
settings once in that block and once in the game state.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game_qa import fixture, rules

SETTINGS = ["achievements_allowed", "tax_light", "merges_on", "no_fantasy"]
RULE_FILE = """﻿# a comment with a brace {
tax_rule = {
	default = tax_off

	tax_off = {
		flag = tax_off
	}
	tax_light = { flag = tax_light }
	tax_full = {
		flag = "tax_full"
		modifier = { country_x_add = 1 }
	}
}

merges_rule = {
	default = merges_off	# the default
	merges_off = { }
	merges_on = { }
}
"""
VANILLA_FILE = """achievements = {
	achievements_allowed = { }
	achievements_off = { }
}
fantasy = {
	default = allow_fantasy
	allow_fantasy = { }
	no_fantasy = { }
}
tax_rule = { default = old old = { } }
"""
PRESETS = """﻿game_rules_preset={
	name="My favourites"
	setting={ a b }
	ironman=yes
}
game_rules_preset={
	name="LastAppliedRules"
	setting={ achievements_allowed tax_light merges_on no_fantasy headlines_gone }
	ironman=no
}
"""


def save_bytes(settings=SETTINGS, body=b"country_manager={\n\tx=1\n}\n", random=b"175ab1f5") -> bytes:
    listed = (' "" ' + " ".join(settings) + " ").encode()
    meta = (b"meta_data={\n\tsave_game_version=1794310339\n\tgame_rules={\n\t\tsettings={" + listed
            + b"}\n\t}\n\tironman=no\n\tnumber_of_players=1\n}\n")
    state = b"ironman={\n\tironman=no\n}\ngame_rules={\n\tsetting={" + listed + b"}\n}\n" + body
    return b"SAV0100" + random + b"%08x" % len(meta) + b"\n" + meta + state


class RulesTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.user = self.base / "user"
        self.saves = self.user / fixture.SAVE_FOLDER
        self.saves.mkdir(parents=True)
        self.vanilla = self.base / "game" / "common" / "game_rules"
        self.mod = self.base / "deploy" / "common" / "game_rules"
        for folder, name, text in ((self.vanilla, "00_rules.txt", VANILLA_FILE), (self.mod, "extra.txt", RULE_FILE)):
            folder.mkdir(parents=True)
            (folder / name).write_text(text, encoding="utf-8")
        self.table = rules.load_rules([self.vanilla, self.mod])


class LastAppliedTest(RulesTestCase):
    def write_presets(self, text=PRESETS):
        path = self.user / rules.PRESETS_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_reads_the_last_applied_preset_and_no_other(self):
        path = self.write_presets()
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        self.assertEqual(rules.last_applied(self.user),
                         ["achievements_allowed", "tax_light", "merges_on", "no_fantasy", "headlines_gone"])
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before, "the owner's file is only read")

    def test_no_file_or_no_such_preset_is_an_empty_list(self):
        self.assertEqual(rules.last_applied(self.user), [])
        self.write_presets('game_rules_preset={\n\tname="Mine"\n\tsetting={ a }\n}\n')
        self.assertEqual(rules.last_applied(self.user), [])
        self.write_presets("\xff\xfe not text".encode("latin-1").decode("latin-1"))
        self.assertEqual(rules.last_applied(self.user), [])


class RuleTableTest(RulesTestCase):
    def test_a_rule_is_a_top_level_block_and_a_setting_a_block_inside_it(self):
        found = rules.rules_in(RULE_FILE)
        self.assertEqual(found, {
            "tax_rule": {"default": "tax_off", "settings": ["tax_off", "tax_light", "tax_full"]},
            "merges_rule": {"default": "merges_off", "settings": ["merges_off", "merges_on"]},
        })

    def test_a_mod_rule_replaces_vanillas_and_the_rest_are_kept(self):
        self.assertEqual(sorted(self.table), ["achievements", "fantasy", "merges_rule", "tax_rule"])
        self.assertEqual(self.table["tax_rule"]["settings"], ["tax_off", "tax_light", "tax_full"])
        self.assertIsNone(self.table["achievements"]["default"])

    def test_a_same_named_mod_file_replaces_the_vanilla_file(self):
        (self.mod / "00_rules.txt").write_text("only = { a = { } }\n", encoding="utf-8")
        table = rules.load_rules([self.vanilla, self.mod])
        self.assertNotIn("fantasy", table)
        self.assertIn("only", table)

    def test_a_missing_folder_is_skipped(self):
        self.assertEqual(sorted(rules.load_rules([self.base / "nowhere", self.mod])), ["merges_rule", "tax_rule"])

    def test_the_real_rule_files_parse(self):
        # The mod's own file, comments and all: every rule has settings, and its default is one of them.
        here = Path(__file__).resolve().parent / rules.RULES_FOLDER
        table = rules.load_rules([here])
        self.assertIn("te_tax_code_rule", table)
        self.assertEqual(table["te_tax_code_rule"]["default"], "te_tax_code_disabled")
        self.assertIn("te_tax_code_light", table["te_tax_code_rule"]["settings"])
        for rule, entry in table.items():
            self.assertTrue(entry["settings"], rule)
            if entry["default"] is not None:
                self.assertIn(entry["default"], entry["settings"], rule)


class SwitchTest(RulesTestCase):
    def test_settings_of_reads_the_list_without_the_empty_entry(self):
        self.assertEqual(rules.settings_of(save_bytes()), SETTINGS)

    def test_a_switch_replaces_the_setting_in_both_lists_and_keeps_everything_else(self):
        data = save_bytes()
        new, changed = rules.switch(data, {"tax_rule": "tax_off"}, self.table)
        self.assertEqual(changed, {"tax_rule": {"from": "tax_light", "to": "tax_off"}})
        self.assertEqual(rules.settings_of(new), ["achievements_allowed", "tax_off", "merges_on", "no_fantasy"])
        self.assertEqual(new.count(b"tax_off"), 2)
        self.assertEqual(new.count(b"tax_light"), 0)
        # The order is kept, the body is untouched, and only the two lists and the length differ.
        self.assertTrue(new.endswith(b"country_manager={\n\tx=1\n}\n"))
        self.assertEqual(new.replace(b"tax_off", b"tax_light")[23:], data[23:])

    def test_the_header_carries_the_new_meta_length(self):
        data = save_bytes()
        new, _ = rules.switch(data, {"tax_rule": "tax_full", "merges_rule": "merges_off"}, self.table)
        old_len, new_len = int(data[15:23], 16), int(new[15:23], 16)
        self.assertEqual(new_len - old_len, len("tax_full") - len("tax_light") + len("merges_off") - len("merges_on"))
        self.assertEqual(new[:15], data[:15], "the header's other fields stay")
        self.assertEqual(new[24 + new_len - 2:24 + new_len + 9], b"}\nironman={")
        self.assertEqual(rules.settings_of(new), ["achievements_allowed", "tax_full", "merges_off", "no_fantasy"])

    def test_a_switch_to_the_setting_already_held_changes_nothing(self):
        data = save_bytes()
        new, changed = rules.switch(data, {"tax_rule": "tax_light"}, self.table)
        self.assertEqual((new, changed), (data, {"tax_rule": {"from": "tax_light", "to": "tax_light"}}))

    def test_what_is_refused(self):
        data = save_bytes()
        cases = (
            ({"nope_rule": "x"}, "no rule"),
            ({"tax_rule": "merges_on"}, "not a setting of tax_rule"),
            ({"achievements": "achievements_off"}, None),       # fine: a vanilla rule
        )
        for switches, message in cases:
            with self.subTest(switches=switches):
                if message is None:
                    rules.switch(data, switches, self.table)
                else:
                    with self.assertRaisesRegex(rules.RulesError, message):
                        rules.switch(data, switches, self.table)

    def test_a_rule_the_save_has_no_setting_of_or_two_is_refused(self):
        for settings in (["achievements_allowed", "merges_on"], SETTINGS + ["tax_full"]):
            with self.assertRaisesRegex(rules.RulesError, "not one"):
                rules.switch(save_bytes(settings), {"tax_rule": "tax_off"}, self.table)

    def test_a_save_that_is_not_plain_text_is_refused(self):
        for data in (b"SAV0103175ab1f500000739\nPK\x03\x04", b"PK\x03\x04", b"", save_bytes()[1:]):
            with self.assertRaisesRegex(rules.RulesError, "plain-text"):
                rules.settings_of(data)

    def test_lists_that_differ_or_are_missing_are_refused(self):
        data = save_bytes()
        with self.assertRaisesRegex(rules.RulesError, "differ"):
            rules.settings_of(data.replace(b"no_fantasy }\n}\ncountry", b"allow_fantasy }\n}\ncountry"))
        with self.assertRaisesRegex(rules.RulesError, "not once in each"):
            rules.settings_of(data.replace(b"\tsetting={", b"\tsettinx={"))
        doubled = data + b"\ngame_rules={\n\tsetting={ \"\" a }\n}\n"
        with self.assertRaisesRegex(rules.RulesError, "not once in each"):
            rules.settings_of(doubled)


class SwitchedFixtureTest(RulesTestCase):
    KEY = "0123456789ab"

    def setUp(self):
        super().setUp()
        self.fixture = self.saves / ("te_qa_fixture_%s.v3" % self.KEY)
        self.fixture.write_bytes(save_bytes())
        (self.saves / "autosave.v3").write_bytes(b"the owner's")

    def test_the_copy_gets_its_own_fixture_name_and_the_base_is_untouched(self):
        before = (self.fixture.read_bytes(), self.fixture.stat().st_mtime_ns)
        path, changed, settings = rules.switched_fixture(self.user, self.KEY, {"tax_rule": "tax_off"}, self.table)
        self.assertEqual(path.name, "te_qa_fixture_%s.v3" % rules.switched_key(self.KEY, {"tax_rule": "tax_off"}))
        self.assertRegex(path.stem, r"^te_qa_fixture_0123456789ab_s[0-9a-f]{8}$")
        self.assertEqual(changed, {"tax_rule": {"from": "tax_light", "to": "tax_off"}})
        self.assertEqual(settings, rules.settings_of(path.read_bytes()))
        self.assertEqual((self.fixture.read_bytes(), self.fixture.stat().st_mtime_ns), before)
        self.assertEqual(sorted(p.name for p in self.saves.iterdir()),
                         sorted(["autosave.v3", self.fixture.name, path.name]), "no staged file is left")
        self.assertIsNotNone(fixture.find(self.user, path.stem[len(fixture.FIXTURE_PREFIX):]))

    def test_the_key_depends_on_the_switches_and_not_on_their_order(self):
        a = rules.switched_key(self.KEY, {"tax_rule": "tax_off", "merges_rule": "merges_off"})
        b = rules.switched_key(self.KEY, {"merges_rule": "merges_off", "tax_rule": "tax_off"})
        self.assertEqual(a, b)
        self.assertNotEqual(a, rules.switched_key(self.KEY, {"tax_rule": "tax_off"}))
        self.assertNotEqual(a, rules.switched_key("ba9876543210", {"tax_rule": "tax_off"}))

    def test_an_existing_copy_is_used_again_and_a_wrong_one_is_rewritten(self):
        path, _, _ = rules.switched_fixture(self.user, self.KEY, {"tax_rule": "tax_off"}, self.table)
        stamp = path.stat().st_mtime_ns
        again, changed, settings = rules.switched_fixture(self.user, self.KEY, {"tax_rule": "tax_off"}, self.table)
        self.assertEqual((again, again.stat().st_mtime_ns), (path, stamp))
        self.assertEqual(settings[1], "tax_off")
        path.write_bytes(save_bytes())          # holds the wrong setting: not what its name says
        rules.switched_fixture(self.user, self.KEY, {"tax_rule": "tax_off"}, self.table)
        self.assertEqual(rules.settings_of(path.read_bytes())[1], "tax_off")

    def test_a_refusal_writes_nothing(self):
        for switches, message in (({"tax_rule": "nope"}, "not a setting"), ({"tax rule": "tax_off"}, "are names")):
            with self.assertRaisesRegex(rules.RulesError, message):
                rules.switched_fixture(self.user, self.KEY, switches, self.table)
        with self.assertRaisesRegex(rules.RulesError, "could not be read"):
            rules.switched_fixture(self.user, "ffffffffffff", {"tax_rule": "tax_off"}, self.table)
        self.assertEqual(sorted(p.name for p in self.saves.iterdir()), ["autosave.v3", self.fixture.name])

    def test_a_failed_write_leaves_no_staged_file_and_no_copy(self):
        with mock.patch("os.replace", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(rules.RulesError, "could not be written"):
                rules.switched_fixture(self.user, self.KEY, {"tax_rule": "tax_off"}, self.table)
        self.assertEqual(sorted(p.name for p in self.saves.iterdir()), ["autosave.v3", self.fixture.name])

    def test_a_staged_file_an_earlier_attempt_left_is_replaced(self):
        target = self.saves / ("te_qa_fixture_%s.v3" % rules.switched_key(self.KEY, {"tax_rule": "tax_off"}))
        (self.saves / (target.name + rules.STAGED_SUFFIX)).write_bytes(b"half a save")
        path, _, _ = rules.switched_fixture(self.user, self.KEY, {"tax_rule": "tax_off"}, self.table)
        self.assertEqual(rules.settings_of(path.read_bytes())[1], "tax_off")
        self.assertFalse((self.saves / (target.name + rules.STAGED_SUFFIX)).exists())


if __name__ == "__main__":
    unittest.main()
