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
import tempfile
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
        self.assertEqual(manifest["localization"]["keys"], 2)
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
        # The mod layer must not leak into the snapshot's vanilla data.
        self.assertNotIn("law_new", fast.base_parsers["Laws"].data)
        self.assertIn("law_new", fast.mod_parsers["Laws"].data)

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
                               side_effect=lambda _ms, chain: ran.append([lbl for lbl, _ in chain])), \
                mock.patch.object(mss, "_snapshot_mod_text_files", return_value={}), \
                mock.patch.dict(os.environ, {"VIC3_SKIP_POST_LOAD_GENERATORS": ""}):
            mss._run_post_load_generators(object(), **kwargs)
        return ran, list(mss._post_load_warnings)

    def test_skipped_without_vanilla_files(self):
        ran, warnings = self._run(vanilla_files=False)
        regenerators = ran[0]
        for label in mss.VANILLA_FILE_REGENERATORS:
            self.assertNotIn(label, regenerators)
        self.assertIn("organize_loc", regenerators)
        self.assertEqual(warnings[0]["label"], "vanilla_files_missing")
        self.assertEqual(
            set(warnings[0]["skipped"]),
            set(mss.VANILLA_FILE_REGENERATORS) | {"generate_docs"},
        )

    def test_run_with_vanilla_files(self):
        ran, warnings = self._run()
        self.assertEqual(ran[0], [lbl for lbl, _ in mss.POST_LOAD_REGENERATORS])
        self.assertEqual(warnings, [])

    def test_audits_only_names_only_generate_docs(self):
        ran, warnings = self._run(audits_only=True, vanilla_files=False)
        self.assertEqual(ran, [[lbl for lbl, _ in mss.POST_LOAD_AUDITS]])
        self.assertEqual(warnings[0]["skipped"], ["generate_docs"])

    def test_roster_names_are_real_regenerators(self):
        labels = {lbl for lbl, _ in mss.POST_LOAD_REGENERATORS}
        self.assertLessEqual(set(mss.VANILLA_FILE_REGENERATORS), labels)


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
