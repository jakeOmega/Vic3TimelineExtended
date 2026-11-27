"""Tests for vanilla_parsed (the committed vanilla parse) and the server's
choice between it and parsing the game files.

Builds tiny vanilla trees in a tempdir; needs no Victoria 3 install. The
server tests import mod_state_server, so on a machine without the game set
the dummy VIC3_* env vars CI uses.

Run: python3 -m unittest test_vanilla_parsed
"""

import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

import mod_state_server as mss
import vanilla_parsed as vp
from mod_state import ModState


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(text)


def _make_vanilla(root, version="1.13.9"):
    """A minimal vanilla tree: two entity types, one loc file, a version."""
    _write(os.path.join(root, "game/common/static_modifiers/00_a.txt"),
           "mod_a = {\n\tcountry_prestige_add = 5\n\ticon = \"gfx/a.dds\"\n}\n"
           "mod_b = {\n\tstate_pop_growth_mult = -0.1\n}\n")
    # Lists, repeated keys, operators other than `=`, anonymous objects.
    _write(os.path.join(root, "game/common/laws/00_laws.txt"),
           "law_x = {\n\tgroup = lawgroup_x\n\tunlocking_laws = { law_y law_z }\n"
           "\tpossible = {\n\t\thas_law = law_y\n\t\thas_law = law_z\n\t\tgdp > 1000\n"
           "\t\tliteracy_rate != 0\n\t}\n"
           "\tlist_of_objects = { { a = 1 } { a = 2 } }\n}\n")
    # Skipped by the loader: leading underscore, .md.
    _write(os.path.join(root, "game/common/laws/_ignored.txt"), "junk = {\n")
    _write(os.path.join(root, "game/common/laws/readme.md"), "# notes\n")
    _write(os.path.join(root, "game/localization/english/a_l_english.yml"),
           "l_english:\n law_x:0 \"Law X\"\n mod_a: \"Modifier \\\"A\\\"\"\n")
    _write(os.path.join(root, "game/localization/english/map/states_l_english.yml"),
           "l_english:\n STATE_X:0 \"State X\"\n")
    # The start map: effect script that the entity tables cannot hold (#901).
    _write(os.path.join(root, "game/common/history/states/00_states.txt"),
           "STATES = {\n\ts:STATE_X = {\n"
           "\t\tcreate_state = { country = c:AAA owned_provinces = { x0000A1 x0000A2 } }\n"
           "\t\tcreate_state = { country = c:BBB owned_provinces = { x0000B1 } }\n"
           "\t\tadd_homeland = cu:alpha\n\t}\n}\n")
    # Each tag's history block (#1628).
    _write(os.path.join(root, "game/common/history/countries/aaa - alpha.txt"),
           "COUNTRIES = {\n\tc:AAA ?= {\n\t\tactivate_law = law_type:law_x\n"
           "\t\teffect_starting_technology_tier_2_tech = yes\n\t}\n}\n")
    # The defines (#1879): a namespace opened twice keeps both blocks' leaves.
    _write(os.path.join(root, "game/common/defines/00_defines.txt"),
           "NAI = {\n\tGATE = 0.1 # a comment\n\tSTEPS = { 1 2 3 }\n}\n"
           "NPops = {\n\tA = 1\n}\nNPops = {\n\tB = 2\n}\n")
    _write(os.path.join(root, "game/common/defines/jomini/00_tooltips.txt"),
           "NTooltips = {\n\tDELAY = 0.5\n}\n")
    # Lookup-only types (#1860): kept by name, with the file that defines it.
    _write(os.path.join(root, "game/common/scripted_triggers/00_triggers.txt"),
           "country_has_x = {\n\thas_law = law_type:law_x\n}\n"
           "country_has_y = {\n\tOR = { has_law = law_type:$A$ has_law = law_type:law_y }\n}\n")
    _write(os.path.join(root, "game/common/scripted_effects/00_effects.txt"),
           "make_x = {\n\tcreate_country = { color = list \"breakaway_colors\" }\n}\n")
    _write(os.path.join(root, "game/common/scripted_effects/01_more.txt"),
           "make_x = {\n\tadd_modifier = { name = later }\n}\n")
    _write(os.path.join(root, "game/common/war_goal_types/00_war_goals.txt"),
           "make_union = {\n\tkind = make_subject\n}\n")
    _write(os.path.join(root, "launcher/launcher-settings.json"),
           json.dumps({"rawVersion": version}))


class EncodingTests(unittest.TestCase):
    def test_round_trip_keeps_tuples_and_lists_apart(self):
        value = {
            "a": ("=", "yes"),
            "b": ("=", ["x", "y"]),
            "c": [("=", "1"), (">", "2")],
            "d": ("=", {"e": ("<=", "3"), "f": [{"g": ("=", "h")}]}),
            "empty": ("=", []),
        }
        back = vp.decode(json.loads(json.dumps(vp.encode(value))))
        self.assertTrue(vp._strict_equal(back, value))

    def test_strict_equal_distinguishes_tuple_from_list(self):
        self.assertTrue(("=", "a") == ("=", "a"))
        self.assertFalse(vp._strict_equal(("=", "a"), ["=", "a"]))

    def test_version_key(self):
        self.assertLess(vp.version_key("1.13.9"), vp.version_key("1.14.0"))
        self.assertLess(vp.version_key("1.9"), vp.version_key("1.13"))
        self.assertEqual(vp.version_key("beta"), ())
        self.assertEqual(vp.version_key(None), ())


class BuildLoadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.game = os.path.join(self.tmp, "vanilla")
        self.out = os.path.join(self.tmp, "vanilla_parsed")
        _make_vanilla(self.game)

    def test_snapshot_loads_exactly_what_a_live_parse_produces(self):
        manifest = vp.build(self.game, self.out)
        self.assertEqual(manifest["game_version"], "1.13.9")
        self.assertEqual(manifest["game_version_source"], "launcher-settings.json")
        self.assertEqual(manifest["entity_types"]["Laws"]["entities"], 1)
        self.assertEqual(manifest["localization"]["keys"], 3)
        self.assertIn("game/localization/english/map/states_l_english.yml", manifest["sources"])
        # Skipped files are not sources, so editing them cannot stale it.
        self.assertIn("game/common/laws/00_laws.txt", manifest["sources"])
        self.assertNotIn("game/common/laws/_ignored.txt", manifest["sources"])
        self.assertNotIn("game/common/laws/readme.md", manifest["sources"])

        mod = os.path.join(self.tmp, "mod")
        _write(os.path.join(mod, "laws/x.txt"),
               "INJECT:law_x = {\n\tprogressiveness = 50\n}\nlaw_new = {\n\tgroup = g\n}\n")
        dirs = vp._entity_dirs(self.game)
        mod_dirs = {"Laws": os.path.join(mod, "laws")}
        live = ModState(dirs, mod_dirs)
        live.add_localization(os.path.join(self.game, "game/localization/english"))

        snap = vp.load(self.out)
        fast = ModState(dirs, mod_dirs, vanilla_data=snap.data)
        for et in dirs:
            self.assertTrue(
                vp._strict_equal(live.base_parsers[et].data, fast.base_parsers[et].data), et)
            self.assertTrue(
                vp._strict_equal(live.mod_parsers[et].data, fast.mod_parsers[et].data), et)
        self.assertEqual(snap.localization, live.localization)
        self.assertEqual(snap.localization["mod_a"], 'Modifier \\"A\\"')
        self.assertEqual(snap.localization["STATE_X"], "State X")
        # The mod layer must not leak into the snapshot's vanilla data.
        self.assertNotIn("law_new", fast.base_parsers["Laws"].data)
        self.assertIn("law_new", fast.mod_parsers["Laws"].data)

    def test_state_history_is_stored_beside_the_entity_types(self):
        manifest = vp.build(self.game, self.out)
        info = manifest["state_history"]
        self.assertEqual((info["dir"], info["files"], info["states"], info["parts"], info["split_states"]),
                         ("game/common/history/states", 1, 1, 2, 1))
        self.assertIn("game/common/history/states/00_states.txt", manifest["sources"])
        import state_history
        live = state_history.parse_dir(os.path.join(self.game, "game/common/history/states"))
        self.assertEqual(vp.load(self.out).state_history, live)
        self.assertEqual(vp.load_state_history(self.out), live)
        self.assertEqual([p["country"] for p in live["00_states.txt"]["STATE_X"]["parts"]], ["AAA", "BBB"])
        # A rebuild keeps the file: only stray common/*.json files are pruned.
        vp.build(self.game, self.out)
        self.assertTrue(os.path.isfile(os.path.join(self.out, vp.STATE_HISTORY_FILE)))

    def test_country_history_is_stored_beside_the_entity_types(self):
        import country_history
        manifest = vp.build(self.game, self.out)
        info = manifest["country_history"]
        self.assertEqual((info["dir"], info["files"], info["countries"], info["with_laws"]),
                         ("game/common/history/countries", 1, 1, 1))
        self.assertIn("game/common/history/countries/aaa - alpha.txt", manifest["sources"])
        live = country_history.parse_dir(os.path.join(self.game, "game/common/history/countries"))
        self.assertEqual(vp.load_country_history(self.out), live)
        self.assertEqual(live["aaa - alpha.txt"]["AAA"],
                         {"laws": ["law_x"], "tech_tier_effects": ["effect_starting_technology_tier_2_tech"]})

    def test_defines_are_merged_leaf_by_leaf(self):
        manifest = vp.build(self.game, self.out)
        self.assertEqual(manifest["defines"], {"dir": "game/common/defines", "file": "defines.json",
                                               "namespaces": 3, "leaves": 5})
        self.assertIn("game/common/defines/jomini/00_tooltips.txt", manifest["sources"])
        self.assertEqual(vp.vanilla_define("NAI", "GATE", self.out), "0.1")
        self.assertEqual(vp.vanilla_define("NAI", "STEPS", self.out), ["1", "2", "3"])
        # ModState's top-level merge would have kept the second NPops block alone.
        self.assertEqual((vp.vanilla_define("NPops", "A", self.out), vp.vanilla_define("NPops", "B", self.out)),
                         ("1", "2"))
        self.assertEqual(vp.vanilla_define("NTooltips", "DELAY", self.out), "0.5")
        for ns, name in (("NAI", "NOPE"), ("NOPE", "GATE")):
            with self.subTest(define=f"{ns}.{name}"), self.assertRaises(KeyError):
                vp.vanilla_define(ns, name, self.out)
        # A rebuild after a vanilla edit is read, not a cached copy.
        _write(os.path.join(self.game, "game/common/defines/00_defines.txt"), "NAI = {\n\tGATE = 0.25\n}\n")
        vp.build(self.game, self.out)
        self.assertEqual(vp.vanilla_define("NAI", "GATE", self.out), "0.25")

    def test_vanilla_define_without_defines_in_the_snapshot(self):
        vp.build(self.game, self.out)
        manifest = vp.read_manifest(self.out)
        del manifest["defines"]
        with open(os.path.join(self.out, vp.MANIFEST), "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        with self.assertRaises(FileNotFoundError):
            vp.vanilla_define("NAI", "GATE", self.out)
        self.assertIsNone(vp.load_defines(self.out))

    def test_lookup_types_are_kept_by_name_and_file(self):
        manifest = vp.build(self.game, self.out)
        self.assertEqual({et: (i["dir"], i["entities"], i["parse_failures"])
                          for et, i in manifest["lookup_types"].items()}, {
            "Scripted Triggers": ("game/common/scripted_triggers", 2, []),
            "Scripted Effects": ("game/common/scripted_effects", 1, []),
            "War Goal Types": ("game/common/war_goal_types", 1, []),
        })
        triggers = vp.load_lookup("Scripted Triggers", self.out)
        self.assertEqual(triggers["country_has_x"],
                         {"file": "00_triggers.txt", "body": ("=", {"has_law": ("=", "law_type:law_x")})})
        # The last file in name order wins a key two files define, as ModState's merge does.
        effects = vp.load_lookup("Scripted Effects", self.out)
        self.assertEqual(effects["make_x"]["file"], "01_more.txt")
        live, failures = vp.lookup_table(os.path.join(self.game, "game/common/scripted_effects"), "Scripted Effects")
        self.assertEqual(failures, [])
        self.assertTrue(vp._strict_equal(effects, live))
        # The merged tables stay mod-only: ModState never sees the lookup types.
        self.assertNotIn("Scripted Triggers", vp.load(self.out).data)
        self.assertEqual(vp.load_lookup("War Goal Types", self.out)["make_union"]["body"],
                         ("=", {"kind": ("=", "make_subject")}))
        self.assertIsNone(vp.load_lookup("Not A Type", self.out))
        # One line per entry.
        with open(os.path.join(self.out, "lookup/scripted_triggers.json"), encoding="utf-8") as f:
            self.assertEqual(len(f.read().splitlines()), 4)

    def test_a_lookup_file_that_does_not_parse_is_recorded(self):
        _write(os.path.join(self.game, "game/common/war_goal_types/01_broken.txt"), "goal = {\n\tkind = make_subject\n}\nstray_word\n")
        manifest = vp.build(self.game, self.out)
        failures = manifest["lookup_types"]["War Goal Types"]["parse_failures"]
        self.assertEqual([f["file"] for f in failures], ["game/common/war_goal_types/01_broken.txt"])
        # A lookup type's failure is not a ModState one: the server would report it on every load.
        self.assertEqual(manifest["parse_failures"], [])
        self.assertEqual(sorted(vp.load_lookup("War Goal Types", self.out)), ["make_union"])

    def test_no_history_folder_is_an_empty_table(self):
        shutil.rmtree(os.path.join(self.game, "game/common/history"))
        manifest = vp.build(self.game, self.out)
        self.assertEqual(manifest["state_history"]["states"], 0)
        self.assertEqual(vp.load(self.out).state_history, {})
        self.assertTrue(vp.check(self.out, self.game).fresh)

    def test_rebuild_of_unchanged_tree_writes_nothing(self):
        first = vp.build(self.game, self.out)
        manifest_path = os.path.join(self.out, vp.MANIFEST)
        mtime = os.path.getmtime(manifest_path)
        with mock.patch.object(vp, "datetime") as dt:
            dt.now.return_value.isoformat.return_value = "2099-01-01T00:00:00+00:00"
            second = vp.build(self.game, self.out)
        self.assertEqual(second["built_at"], first["built_at"])
        self.assertEqual(os.path.getmtime(manifest_path), mtime)

    def test_unversioned_tree_needs_game_version(self):
        os.remove(os.path.join(self.game, "launcher/launcher-settings.json"))
        with self.assertRaises(ValueError):
            vp.build(self.game, self.out)
        manifest = vp.build(self.game, self.out, game_version="1.0")
        self.assertEqual(manifest["game_version_source"], "argument")

    def test_load_refuses_other_format_version(self):
        vp.build(self.game, self.out)
        path = os.path.join(self.out, vp.MANIFEST)
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
        manifest["format_version"] = vp.FORMAT_VERSION + 1
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        with self.assertRaises(ValueError):
            vp.load(self.out)

    def test_parsed_entities_from_mod_state_or_snapshot(self):
        vp.build(self.game, self.out)
        dirs = vp._entity_dirs(self.game)
        live = ModState(dirs, {})
        real_load = vp.load
        with mock.patch.object(vp, "load", side_effect=lambda: real_load(self.out)) as load:
            # A ModState that holds every type is the source; nothing is loaded.
            got = vp.parsed_entities(("Laws", "Modifiers"), live)
            self.assertIs(got["Laws"], live.base_parsers["Laws"].data)
            self.assertEqual(set(got), {"Laws", "Modifiers"})
            load.assert_not_called()
            # No ModState, or one missing a type (a stub), reads the snapshot.
            for mod_state in (None, object(), type("S", (), {"base_parsers": {"Other": 1}})()):
                got = vp.parsed_entities(("Laws",), mod_state)
                self.assertTrue(vp._strict_equal(got["Laws"], live.base_parsers["Laws"].data))
            self.assertEqual(load.call_count, 3)


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.game = os.path.join(self.tmp, "vanilla")
        self.out = os.path.join(self.tmp, "vanilla_parsed")
        _make_vanilla(self.game)
        vp.build(self.game, self.out)

    def test_fresh_against_code_and_install(self):
        result = vp.check(self.out, self.game, full=True)
        self.assertTrue(result.fresh, result.reasons)
        self.assertTrue(result.game_checked)

    def test_no_install_checks_code_only(self):
        result = vp.check(self.out, None)
        self.assertTrue(result.fresh)
        self.assertFalse(result.game_checked)

    def test_version_bump_is_stale(self):
        _write(os.path.join(self.game, "launcher/launcher-settings.json"),
               json.dumps({"rawVersion": "1.14.0"}))
        result = vp.check(self.out, self.game)
        self.assertFalse(result.fresh)
        self.assertIn("1.14.0", " ".join(result.game_reasons))

    def test_added_removed_and_resized_files_are_stale(self):
        _write(os.path.join(self.game, "game/common/laws/01_new.txt"), "law_n = { }\n")
        os.remove(os.path.join(self.game, "game/common/static_modifiers/00_a.txt"))
        with open(os.path.join(self.game, "game/localization/english/a_l_english.yml"),
                  "a", encoding="utf-8") as f:
            f.write(' law_y:0 "Law Y"\n')
        reasons = " ".join(vp.check(self.out, self.game).game_reasons)
        self.assertIn("added: game/common/laws/01_new.txt", reasons)
        self.assertIn("removed: game/common/static_modifiers/00_a.txt", reasons)
        self.assertIn("changed: game/localization/english/a_l_english.yml", reasons)

    def test_same_size_edit_needs_full_check(self):
        path = os.path.join(self.game, "game/common/static_modifiers/00_a.txt")
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
        _write(path, text.replace("= 5", "= 6"))
        self.assertTrue(vp.check(self.out, self.game).fresh)
        self.assertFalse(vp.check(self.out, self.game, full=True).fresh)

    def test_parser_change_is_stale_even_without_install(self):
        with mock.patch.object(vp, "parser_fingerprint", return_value="0" * 16):
            result = vp.check(self.out, None)
        self.assertFalse(result.fresh)
        self.assertIn("parser changed", result.code_reasons[0])

    def test_snapshot_without_the_state_history_is_stale(self):
        manifest = vp.read_manifest(self.out)
        del manifest["state_history"]
        result = vp.check(self.out, None, manifest=manifest)
        self.assertFalse(result.fresh)
        self.assertIn("state history", " ".join(result.code_reasons))
        self.assertIsNone(vp.load_state_history(self.out, manifest=manifest))

    def test_snapshot_without_the_new_tables_is_stale(self):
        for key, words in (("country_history", "country history"), ("defines", "defines"),
                           ("lookup_types", "lookup types")):
            with self.subTest(section=key):
                manifest = vp.read_manifest(self.out)
                del manifest[key]
                result = vp.check(self.out, None, manifest=manifest)
                self.assertFalse(result.fresh)
                self.assertIn(words, " ".join(result.code_reasons))

    def test_new_lookup_type_is_stale(self):
        with mock.patch.dict(vp.VANILLA_LOOKUP_DIRS, {"On Actions": "on_actions"}):
            result = vp.check(self.out, None)
        self.assertIn("On Actions", " ".join(result.code_reasons))

    def test_edited_country_history_or_defines_file_is_stale(self):
        for rel in ("game/common/history/countries/aaa - alpha.txt", "game/common/defines/00_defines.txt",
                    "game/common/scripted_triggers/00_triggers.txt"):
            with self.subTest(file=rel):
                with open(os.path.join(self.game, rel), "a", encoding="utf-8") as f:
                    f.write("# edited\n")
                self.assertIn(f"changed: {rel}", " ".join(vp.check(self.out, self.game).game_reasons))
                vp.build(self.game, self.out)

    def test_new_readers_are_in_the_fingerprint(self):
        import country_history
        import game_defines
        before = vp.parser_fingerprint()
        for module, name in ((country_history, "parse_text"), (game_defines, "parse_text"),
                             (vp, "lookup_table")):
            with self.subTest(reader=f"{module.__name__}.{name}"), \
                    mock.patch.object(module, name, lambda *a: {}):
                self.assertNotEqual(vp.parser_fingerprint(), before)

    def test_edited_history_file_is_stale(self):
        path = os.path.join(self.game, "game/common/history/states/00_states.txt")
        with open(path, "a", encoding="utf-8") as f:
            f.write("# a border moved\n")
        self.assertFalse(vp.check(self.out, self.game).fresh)

    def test_state_history_reader_is_in_the_fingerprint(self):
        import state_history
        before = vp.parser_fingerprint()
        with mock.patch.object(state_history, "parse_text", lambda text: {}):
            self.assertNotEqual(vp.parser_fingerprint(), before)

    def test_new_entity_type_is_stale(self):
        with mock.patch.dict(vp.VANILLA_COMMON_DIRS, {"Brand New": "brand_new"}):
            result = vp.check(self.out, None)
        self.assertIn("Brand New", " ".join(result.code_reasons))

    def test_check_cli_exit_codes(self):
        self.assertEqual(vp.main(["check", "--no-game", "--out", self.out]), 0)
        self.assertEqual(vp.main(["check", "--game-root", self.game, "--full",
                                  "--out", self.out]), 0)
        _write(os.path.join(self.game, "launcher/launcher-settings.json"),
               json.dumps({"rawVersion": "9.9"}))
        self.assertEqual(vp.main(["check", "--game-root", self.game,
                                  "--out", self.out]), 1)


class ServerSourceChoiceTests(unittest.TestCase):
    """_choose_vanilla_source: which vanilla the server loads, and what it says."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.game = os.path.join(self.tmp, "vanilla")
        self.out = os.path.join(self.tmp, "vanilla_parsed")
        _make_vanilla(self.game)
        vp.build(self.game, self.out)
        patches = [
            mock.patch.object(mss, "VANILLA_PARSED_DIR", self.out),
            mock.patch.object(mss, "base_game_path", self.game),
            mock.patch.dict(os.environ, {"VIC3_VANILLA_SOURCE": ""}),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _choose(self, *, tree, mode=""):
        os.environ["VIC3_VANILLA_SOURCE"] = mode
        with mock.patch.object(mss, "_vanilla_tree_present", return_value=tree):
            return mss._choose_vanilla_source()

    def _make_stale(self):
        _write(os.path.join(self.game, "launcher/launcher-settings.json"),
               json.dumps({"rawVersion": "1.14.0"}))

    def test_fresh_snapshot_wins_over_game_files(self):
        source, warnings = self._choose(tree=True)
        self.assertEqual(source["kind"], "vanilla_parsed")
        self.assertEqual(source["reason"], "fresh")
        self.assertEqual(warnings, [])

    def test_stale_snapshot_with_game_files_parses_the_files(self):
        self._make_stale()
        source, warnings = self._choose(tree=True)
        self.assertEqual(source["kind"], "game_files")
        self.assertEqual(len(warnings), 1)
        self.assertIn("parsed the game files instead", warnings[0]["detail"])

    def test_stale_snapshot_without_game_files_still_loads(self):
        with mock.patch.object(vp, "parser_fingerprint", return_value="0" * 16):
            source, warnings = self._choose(tree=False)
        self.assertEqual(source["kind"], "vanilla_parsed")
        self.assertEqual(source["reason"], "no vanilla game files on disk")
        self.assertIn("parser changed", warnings[0]["detail"])

    def test_no_snapshot_parses_the_files(self):
        shutil.rmtree(self.out)
        source, warnings = self._choose(tree=True)
        self.assertEqual(source["kind"], "game_files")
        self.assertEqual(warnings, [])

    def test_explicit_modes(self):
        self.assertEqual(self._choose(tree=True, mode="game_files")[0]["kind"], "game_files")
        self._make_stale()
        source, warnings = self._choose(tree=True, mode="vanilla_parsed")
        self.assertEqual(source["kind"], "vanilla_parsed")
        self.assertIn("stale", warnings[0]["detail"])

    def test_older_game_files_lose_to_the_snapshot(self):
        # e.g. a cloud session whose vanilla clone lags the committed snapshot.
        _write(os.path.join(self.game, "launcher/launcher-settings.json"),
               json.dumps({"rawVersion": "1.13.2"}))
        source, warnings = self._choose(tree=True)
        self.assertEqual(source["kind"], "vanilla_parsed")
        self.assertTrue(source["game_files_outdated"])
        self.assertEqual(source["game_files_version"], "1.13.2")
        self.assertIn("older than vanilla_parsed/", warnings[0]["detail"])
        # Explicitly asking for the files still gets them.
        source, _ = self._choose(tree=True, mode="game_files")
        self.assertEqual(source["kind"], "game_files")

    def test_unusable_reason(self):
        with mock.patch.object(mss, "_vanilla_tree_present", return_value=False):
            self.assertIn("no vanilla game files", mss._vanilla_files_unusable_reason())
        with mock.patch.object(mss, "_vanilla_tree_present", return_value=True):
            with mock.patch.object(mss, "_vanilla_source", {"kind": "game_files"}):
                self.assertIsNone(mss._vanilla_files_unusable_reason())
            outdated = {"kind": "vanilla_parsed", "game_files_outdated": True,
                        "game_files_version": "1.13.2", "game_version": "1.13.9"}
            with mock.patch.object(mss, "_vanilla_source", outdated):
                self.assertIn("1.13.2, older than", mss._vanilla_files_unusable_reason())

    def test_unknown_mode_falls_back_to_auto(self):
        source, warnings = self._choose(tree=True, mode="bogus")
        self.assertEqual(source["mode"], "auto")
        self.assertIn("'bogus'", warnings[0]["detail"])

    def test_vanilla_data_loaded_counts_the_snapshot(self):
        with mock.patch.object(mss, "_vanilla_tree_present", return_value=False):
            with mock.patch.object(mss, "_vanilla_source", {"kind": "vanilla_parsed"}):
                self.assertTrue(mss._vanilla_data_loaded())
            with mock.patch.object(mss, "_vanilla_source", {"kind": "game_files"}):
                self.assertFalse(mss._vanilla_data_loaded())


class VanillaFileRegeneratorTests(unittest.TestCase):
    def _run(self, **kwargs):
        ran = []
        with mock.patch.object(mss, "_run_generator_chain",
                               side_effect=lambda _ms, chain, **kw: ran.append(
                                   ([lbl for lbl, _ in chain], kw))), \
                mock.patch.object(mss, "_snapshot_mod_text_files", return_value={}), \
                mock.patch.dict(os.environ, {"VIC3_SKIP_POST_LOAD_GENERATORS": ""}):
            mss._run_post_load_generators(object(), **kwargs)
        return ran, list(mss._post_load_warnings)

    def test_skipped_without_vanilla_files(self):
        ran, warnings = self._run(vanilla_files=False)
        regenerators = ran[0][0]
        for label in mss.VANILLA_FILE_REGENERATORS:
            self.assertNotIn(label, regenerators)
        self.assertIn("organize_loc", regenerators)
        self.assertEqual(warnings[0]["label"], "vanilla_files_missing")
        self.assertEqual(
            set(warnings[0]["skipped"]),
            set(mss.VANILLA_FILE_REGENERATORS) | {"generate_docs"},
        )

    def test_parsed_vanilla_regenerators_run_without_vanilla_files(self):
        # They read parsed vanilla only (#624): gen_law_consistency's laws and
        # ideologies, pm_costs' goods prices.
        ran, _warnings = self._run(vanilla_files=False)
        for label in ("gen_law_consistency", "pm_costs"):
            self.assertIn(label, ran[0][0])
            self.assertNotIn(label, mss.VANILLA_FILE_REGENERATORS)
            self.assertNotIn(label, _warnings[0]["skipped"])

    def test_partial_regenerators_are_named_in_the_warning(self):
        ran, warnings = self._run(vanilla_files=False)
        self.assertEqual(ran[0][1], {"vanilla_files": False})
        partial = warnings[0]["partially_skipped"]
        self.assertEqual(
            partial,
            {label: list(outs) for label, outs in mss.PARTIAL_VANILLA_FILE_REGENERATORS.items()},
        )
        self.assertIn("docs/engine/commented_vanilla_pms.txt", warnings[0]["detail"])

    def test_run_with_vanilla_files(self):
        ran, warnings = self._run()
        self.assertEqual(ran[0][0], [lbl for lbl, _ in mss.POST_LOAD_REGENERATORS])
        self.assertEqual(ran[0][1], {"vanilla_files": True})
        self.assertEqual(warnings, [])

    def test_audits_only_names_only_generate_docs(self):
        ran, warnings = self._run(audits_only=True, vanilla_files=False)
        self.assertEqual(ran[0][0], [lbl for lbl, _ in mss.POST_LOAD_AUDITS])
        self.assertEqual(warnings[0]["skipped"], ["generate_docs"])
        self.assertEqual(warnings[0]["partially_skipped"], {})

    def test_roster_names_are_real_regenerators(self):
        labels = {lbl for lbl, _ in mss.POST_LOAD_REGENERATORS}
        self.assertLessEqual(set(mss.VANILLA_FILE_REGENERATORS), labels)
        self.assertLessEqual(set(mss.PARTIAL_VANILLA_FILE_REGENERATORS), labels)
        self.assertFalse(
            set(mss.VANILLA_FILE_REGENERATORS) & set(mss.PARTIAL_VANILLA_FILE_REGENERATORS)
        )

    def test_chain_tells_only_partial_regenerators_there_are_no_vanilla_files(self):
        calls = {}

        def make(name):
            module = types.ModuleType(name)
            module.regenerate = lambda ms, **kw: calls.setdefault(name, kw)
            return module

        partial_label = next(iter(mss.PARTIAL_VANILLA_FILE_REGENERATORS))
        chain = [(partial_label, "fake_partial"), ("plain", "fake_plain")]
        fakes = {"fake_partial": make("fake_partial"), "fake_plain": make("fake_plain")}
        with mock.patch.dict(sys.modules, fakes):
            mss._run_generator_chain(object(), chain, vanilla_files=False)
            self.assertEqual(calls, {"fake_partial": {"vanilla_files": False}, "fake_plain": {}})
            calls.clear()
            mss._run_generator_chain(object(), chain)
            self.assertEqual(calls, {"fake_partial": {}, "fake_plain": {}})


class ModStateSortedLoadTests(unittest.TestCase):
    def test_files_load_in_name_order(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        for name in ("b.txt", "a.txt", "c.txt"):
            _write(os.path.join(tmp, "x", name), f"key_{name[0]} = {{ v = 1 }}\n")
        ms = ModState({"X": os.path.join(tmp, "x")}, {})
        self.assertEqual(list(ms.base_parsers["X"].data), ["key_a", "key_b", "key_c"])


if __name__ == "__main__":
    unittest.main()
