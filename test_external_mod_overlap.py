"""Tests for external_mod_overlap (#1170): the load-order model one verdict at
a time, the scanner, and the whole report on two small fake mods in a
tmpdir. GET /external-mod-overlap is tested through the handler in
test_mod_state_server_endpoints.ExternalModOverlapEndpointTests."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import external_mod_overlap as emo
from external_mod_overlap import (
    BOTH_MERGE,
    BOTH_WIPED,
    DEPENDS_ON_PLAYSET,
    FIRST_WINS,
    LAST_WINS,
    ORDER_DEPENDS_ON_CASE,
    OURS,
    OURS_WIPED,
    THEIRS,
    THEIRS_WIPED,
    UNDETERMINED,
    UNKNOWN,
    VANILLA,
    Op,
    resolve,
)


def ours(path, directive=None, line=1):
    return Op(OURS, path, line, directive)


def theirs(path, directive=None, line=1):
    return Op(THEIRS, path, line, directive)


IN_VANILLA = [Op(VANILLA, None, 0)]   # vanilla has it, file unknown (snapshot)


class VerdictTests(unittest.TestCase):
    """resolve(), one verdict per test."""

    def test_ours_wiped_their_later_replace(self):
        # The issue's example: our REPLACE in modified.txt, their TRY_REPLACE
        # in zMoG_SPA_citizenship.txt, which sorts later either way.
        res = resolve([ours("modified.txt", "REPLACE", 151)],
                      [theirs("zMoG_SPA_citizenship.txt", "TRY_REPLACE", 145)],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], OURS_WIPED)
        self.assertEqual(res["later_file"], THEIRS)
        self.assertFalse(res["order_depends_on_case"])
        self.assertEqual(res["ours_lost"], [ours("modified.txt", "REPLACE", 151)])
        self.assertEqual([s["effect"] for s in res["trace"]], ["created", "replaced", "replaced"])

    def test_theirs_wiped_bare_duplicate_is_dropped(self):
        # A bare redefinition of a key vanilla has is `Duplicated key X will
        # not be created`, however late it sorts.
        res = resolve([ours("a.txt", "INJECT")], [theirs("zz.txt")], IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], THEIRS_WIPED)
        self.assertEqual(res["trace"][-1]["effect"], "dropped_duplicate")

    def test_theirs_wiped_by_our_later_replace(self):
        res = resolve([ours("zz.txt", "REPLACE")], [theirs("aa.txt", "REPLACE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], THEIRS_WIPED)
        self.assertEqual(res["later_file"], OURS)

    def test_both_merge_two_injects(self):
        res = resolve([ours("extra.txt", "INJECT")], [theirs("zz.txt", "INJECT")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)
        self.assertEqual(res["ours_lost"], [])

    def test_both_merge_inject_after_their_replace(self):
        res = resolve([ours("zz.txt", "INJECT")], [theirs("aa.txt", "REPLACE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)

    def test_both_merge_with_one_of_ours_lost(self):
        # Our first INJECT sorts before their REPLACE, the second after it.
        res = resolve([ours("a.txt", "INJECT"), ours("z.txt", "INJECT")],
                      [theirs("m.txt", "REPLACE")], IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)
        self.assertEqual(res["ours_lost"], [ours("a.txt", "INJECT")])

    def test_both_wiped_two_bare_redefinitions_of_vanilla(self):
        res = resolve([ours("a.txt")], [theirs("b.txt")], IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_WIPED)

    def test_order_depends_on_case(self):
        # The issue's case: `MoG_x.txt` sorts before `extra_x.txt` in ASCII
        # order (M < e) and after it case-folded (m > e).
        res = resolve([ours("extra_country_ranks.txt", "INJECT")],
                      [theirs("MoG_SPA_country_ranks.txt", "TRY_REPLACE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], ORDER_DEPENDS_ON_CASE)
        self.assertTrue(res["order_depends_on_case"])
        self.assertEqual(res["later_file"], "depends_on_case")
        self.assertEqual(res["depends_on"], ["file_order"])
        by_order = {s["file_order"]: s["verdict"] for s in res["verdict_by_scenario"]}
        self.assertEqual(by_order, {"ascii": BOTH_MERGE, "case_folded": OURS_WIPED})

    def test_case_difference_that_changes_nothing_keeps_the_verdict(self):
        res = resolve([ours("extra.txt", "INJECT")], [theirs("MoG.txt", "INJECT")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)
        self.assertTrue(res["order_depends_on_case"])

    def test_same_path_depends_on_playset(self):
        res = resolve([ours("00_laws.txt", "REPLACE")], [theirs("00_Laws.txt", "REPLACE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], DEPENDS_ON_PLAYSET)
        self.assertEqual(res["later_file"], "same_path")
        by_mod = {s["later_mod"]: s["verdict"] for s in res["verdict_by_scenario"]}
        self.assertEqual(by_mod, {THEIRS: OURS_WIPED, OURS: THEIRS_WIPED})

    def test_unknown_bare_rule_is_undetermined(self):
        # scripted_effects: nobody recorded whether the first or the last
        # bare definition wins.
        res = resolve([ours("a.txt")], [theirs("b.txt")], False, UNKNOWN)
        self.assertEqual(res["verdict"], UNDETERMINED)
        self.assertEqual(res["depends_on"], ["bare_duplicate"])
        by_rule = {s["bare_duplicate"]: s["verdict"] for s in res["verdict_by_scenario"]}
        self.assertEqual(by_rule, {FIRST_WINS: THEIRS_WIPED, LAST_WINS: OURS_WIPED})

    def test_unknown_bare_rule_that_changes_nothing(self):
        res = resolve([ours("a.txt", "INJECT")], [theirs("b.txt", "REPLACE")], IN_VANILLA, UNKNOWN)
        self.assertEqual(res["verdict"], OURS_WIPED)

    def test_last_wins_rule(self):
        # script_values: a later bare redefinition replaces.
        res = resolve([ours("a.txt")], [theirs("b.txt")], IN_VANILLA, LAST_WINS)
        self.assertEqual(res["verdict"], OURS_WIPED)
        self.assertEqual(res["trace"][-1]["effect"], "redefined")

    def test_unknown_vanilla_is_undetermined_when_it_matters(self):
        # Two INJECTs merge into vanilla's entry, but error with no entry.
        res = resolve([ours("a.txt", "INJECT")], [theirs("b.txt", "INJECT")], None, FIRST_WINS)
        self.assertEqual(res["verdict"], UNDETERMINED)
        self.assertEqual(res["depends_on"], ["in_vanilla"])

    def test_try_replace_with_no_entry_does_nothing(self):
        res = resolve([ours("z.txt")], [theirs("a.txt", "TRY_REPLACE")], False, FIRST_WINS)
        self.assertEqual(res["verdict"], THEIRS_WIPED)
        self.assertEqual(res["trace"][0]["effect"], "skipped_no_entry")

    def test_plain_inject_with_no_entry_errors(self):
        res = resolve([ours("a.txt", "INJECT")], [theirs("b.txt", "INJECT_OR_CREATE")],
                      False, FIRST_WINS)
        self.assertEqual(res["verdict"], OURS_WIPED)
        self.assertEqual([s["effect"] for s in res["trace"]], ["error_no_entry", "created"])

    def test_vanilla_is_in_place_before_any_mod_file(self):
        # This mod's INJECT:cautious sits in extra_character_traits.txt, which
        # sorts before vanilla's personality_traits.txt, and logs no
        # inject_to_missing: vanilla's definitions come first.
        vanilla = [Op(VANILLA, "personality_traits.txt", 5)]
        res = resolve([ours("extra_character_traits.txt", "INJECT")], [theirs("zz.txt", "INJECT")],
                      vanilla, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)
        self.assertEqual(res["trace"][0]["side"], VANILLA)

    def test_a_mod_file_at_vanilla_path_removes_vanilla_even_without_the_key(self):
        # Their 00_x.txt replaces vanilla's whole file, so vanilla's copy of
        # the key is gone although their file doesn't define it.
        vanilla = [Op(VANILLA, "00_x.txt", 1)]
        res = resolve([ours("extra.txt", "INJECT")], [theirs("zz.txt", "INJECT")], vanilla,
                      FIRST_WINS, ours_files=["extra.txt"], theirs_files=["00_x.txt", "zz.txt"])
        self.assertEqual(res["verdict"], BOTH_WIPED)

    def test_their_file_at_our_path_without_the_key_depends_on_playset(self):
        res = resolve([ours("a.txt", "INJECT")], [theirs("z.txt", "INJECT")], IN_VANILLA,
                      FIRST_WINS, ours_files=["a.txt"], theirs_files=["a.txt", "z.txt"])
        self.assertEqual(res["verdict"], DEPENDS_ON_PLAYSET)
        by_mod = {s["later_mod"]: s["verdict"] for s in res["verdict_by_scenario"]}
        self.assertEqual(by_mod, {THEIRS: OURS_WIPED, OURS: BOTH_MERGE})

    def test_a_mod_file_at_vanilla_path_replaces_vanilla(self):
        # Their bare definition sits in a file at vanilla's path: vanilla's
        # file never loads, so theirs creates the entry instead of being a
        # dropped duplicate (CMF's common/parties/conservative_party.txt).
        vanilla = [Op(VANILLA, "conservative_party.txt", 1)]
        res = resolve([ours("zz_weights.txt", "INJECT")], [theirs("conservative_party.txt")],
                      vanilla, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)
        self.assertEqual(res["trace"][0]["side"], THEIRS)


class OrderHelperTests(unittest.TestCase):
    def test_sort_ops_ascii_and_case_folded(self):
        ops = [ours("extra.txt"), theirs("MoG.txt"), Op(VANILLA, None, 0)]
        self.assertEqual([o.path for o in emo.sort_ops(ops, casefold=False)],
                         [None, "MoG.txt", "extra.txt"])
        self.assertEqual([o.path for o in emo.sort_ops(ops, casefold=True)],
                         [None, "extra.txt", "MoG.txt"])

    def test_digits_and_underscore(self):
        # `_` (0x5F) sorts after `Z` and before `a` in ASCII: no case flip
        # between `_x` and `a_x`, but one between `_x` and `B_x`.
        self.assertFalse(emo.order_depends_on_case([ours("_x.txt")], [theirs("a_x.txt")]))
        self.assertTrue(emo.order_depends_on_case([ours("_x.txt")], [theirs("B_x.txt")]))
        self.assertFalse(emo.order_depends_on_case([ours("00_x.txt")], [theirs("Zz.txt")]))

    def test_resolve_later_wins(self):
        self.assertEqual(emo.resolve_later_wins([ours("extra.txt")], [theirs("zzz.txt")])["winner"],
                         THEIRS)
        self.assertEqual(emo.resolve_later_wins([ours("extra.txt")], [theirs("MoG.txt")])["winner"],
                         ORDER_DEPENDS_ON_CASE)
        self.assertEqual(emo.resolve_later_wins([ours("d.txt")], [theirs("D.txt")])["winner"],
                         DEPENDS_ON_PLAYSET)


class RuleTests(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(emo.rule_for("laws").bare_duplicate, FIRST_WINS)
        self.assertEqual(emo.rule_for("technology/technologies").kind, "database")
        self.assertEqual(emo.rule_for("static_modifiers").bare_duplicate, FIRST_WINS)
        self.assertEqual(emo.rule_for("script_values").bare_duplicate, LAST_WINS)
        self.assertEqual(emo.rule_for("scripted_effects").bare_duplicate, UNKNOWN)
        self.assertEqual(emo.rule_for("history/countries").kind, "additive")
        self.assertEqual(emo.rule_for("defines").kind, "defines")
        self.assertEqual(emo.rule_for("on_actions").kind, "on_actions")

    def test_split_common_path(self):
        self.assertEqual(emo.split_common_path("laws/x.txt"), ("laws", "x.txt"))
        self.assertEqual(emo.split_common_path("laws/sub/x.txt"), ("laws", "sub/x.txt"))
        self.assertEqual(emo.split_common_path("technology/technologies/x.txt"),
                         ("technology/technologies", "x.txt"))
        self.assertEqual(emo.split_common_path("defines/jomini/x.txt"), ("defines", "jomini/x.txt"))
        self.assertIsNone(emo.split_common_path("x.txt"))


class ScannerTests(unittest.TestCase):
    def test_top_level_keys_directives_and_lines(self):
        text = (
            "# TRY_REPLACE:commented_out = {\n"
            "@cost = 5\n"
            "TRY_REPLACE:law_a = {\n"
            "\tgroup = lawgroup_x\n"
            "\t@local = 3\n"
            "\tmodifier = { a_add = 1 }\n"
            "}\n"
            'INJECT:law_b = { desc = "a # not a comment" x = 1 } plain = 4\n'
            "REPLACE_OR_CREATE:law_c = { }\n"
        )
        entries, warnings = emo.scan_script(text)
        self.assertEqual(warnings, [])
        self.assertEqual([(e.key, e.directive, e.line) for e in entries], [
            ("law_a", "TRY_REPLACE", 3),
            ("law_b", "INJECT", 8),
            ("plain", None, 8),
            ("law_c", "REPLACE_OR_CREATE", 9),
        ])
        self.assertEqual([c[0] for c in entries[0].children], ["group", "modifier"])
        self.assertEqual(entries[0].children[1][2], "{ a_add = 1 }")
        self.assertEqual(entries[2].value, "4")

    def test_warnings(self):
        _e, w = emo.scan_script("a = { b = 1 }\n}\nc = {\n")
        self.assertEqual(len(w), 2)
        _e, w = emo.scan_script("FOO:x = { }")
        self.assertIn("unknown directive prefix", w[0])
        entries, w = emo.scan_script("﻿a = { }")
        self.assertIn("doubled UTF-8 BOM", w[0])
        self.assertEqual(entries[0].key, "a")

    def test_value_less_key_does_not_eat_the_brace(self):
        entries, w = emo.scan_script("a = { b = }\nc = { }")
        self.assertEqual([e.key for e in entries], ["a", "c"])
        self.assertEqual(len(w), 1)


def _write(root, rel, text, bom=True):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig" if bom else "utf-8") as f:
        f.write(text)


def build_fake_mods(tmp):
    """Two small mods: `ours` (this mod's shape) and `theirs`, with one
    collision of each kind the report covers."""
    o, t = os.path.join(tmp, "ours"), os.path.join(tmp, "theirs")
    _write(o, "common/laws/modified.txt", "REPLACE:law_a = {\n\tgroup = lawgroup_x\n}\n")
    _write(t, "common/laws/zMoG_laws.txt", "\n\nTRY_REPLACE:law_a = {\n\tgroup = lawgroup_x\n}\n")
    _write(o, "common/country_ranks/extra_country_ranks.txt",
           "INJECT:great_power = { modifier = { x_add = 1 } }\n")
    _write(t, "common/country_ranks/MoG_country_ranks.txt",
           "TRY_REPLACE:great_power = { rank_value = 7 }\n")
    _write(o, "common/static_modifiers/extra_modifiers.txt", "INJECT:state_turmoil = { a = 1 }\n")
    _write(t, "common/static_modifiers/zzz_overwrite.txt", "INJECT:state_turmoil = { b = 1 }\n")
    _write(o, "common/defines/extra_defines.txt",
           "@shared_const = 1\nNPops = {\n\tWORKING_ADULT_RATIO_SKEW_MAXIMUM = 1000000\n"
           "\t@inner = 2\n\tONLY_OURS = 1\n}\n")
    _write(t, "common/defines/zzz_def.txt",
           "@shared_const = 7\nNPops = {\n\tWORKING_ADULT_RATIO_SKEW_MAXIMUM = 4.0\n"
           "\t@inner = 9\n}\n")
    _write(o, "common/on_actions/extra_on_actions.txt",
           "on_monthly_pulse_country = {\n\ton_actions = { te_monthly }\n\teffect = { a = b }\n}\n"
           "on_game_started = { events = { te.1 } }\n")
    _write(t, "common/on_actions/zz_their_on_actions.txt",
           "on_monthly_pulse_country = {\n\ton_actions = { mog_monthly }\n\teffect = { c = d }\n}\n"
           "on_game_started = { events = { mog.1 } }\nonly_theirs = { events = { mog.2 } }\n")
    _write(o, "events/our_events.txt", "namespace = shared_ns\nshared_ns.1 = { type = country_event }\n")
    _write(t, "events/their_events.txt",
           "namespace = shared_ns\nnamespace = mog\nshared_ns.1 = { type = country_event }\n"
           "mog.1 = { }\n")
    _write(o, "localization/english/te_misc_l_english.yml",
           'l_english:\n shared_key:0 "Ours"\n only_ours:0 "x"\n')
    _write(t, "localization/english/mog_l_english.yml", 'l_english:\n shared_key:0 "Theirs"\n')
    _write(o, "localization/english/replace/te_override_l_english.yml",
           'l_english:\n vanilla_key:0 "Ours"\n')
    _write(t, "localization/english/mog2_l_english.yml", 'l_english:\n vanilla_key: "Theirs"\n')
    _write(o, "gui/budget_panel.gui", "types x {}\n")
    _write(t, "gui/budget_panel.gui", "types y {}\n")
    _write(t, "localization/spanish/te_misc_l_spanish.yml", 'l_spanish:\n shared_key:0 "x"\n')
    _write(t, "common/history/countries/mog.txt", "COUNTRIES = { }\n")
    _write(o, "common/history/countries/te.txt", "COUNTRIES = { }\n")
    _write(t, "common/political_movements/notes.md", "notes\n")
    _write(o, "common/political_movements/notes.md", "notes\n")
    os.makedirs(os.path.join(t, ".metadata"))
    with open(os.path.join(t, ".metadata", "metadata.json"), "w", encoding="utf-8") as f:
        json.dump({"name": "Fake Pop Mod", "id": "1"}, f)
    return o, t


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.ours_root, cls.theirs_root = build_fake_mods(cls._tmp.name)
        cls.vanilla = {"laws": {"law_a"}, "country_ranks": {"great_power"},
                       "static_modifiers": {"state_turmoil"}}
        cls.report = emo.analyze(cls.theirs_root, cls.ours_root, vanilla=cls.vanilla)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def collision(self, key):
        return next(c for c in self.report["key_collisions"] if c["key"] == key)

    def test_mod_name_and_counts(self):
        self.assertEqual(self.report["mod_name"], "Fake Pop Mod")
        self.assertEqual(self.report["summary"]["key_collisions"], 3)
        self.assertEqual(self.report["summary"]["by_verdict"],
                         {BOTH_MERGE: 1, ORDER_DEPENDS_ON_CASE: 1, OURS_WIPED: 1})

    def test_key_collision_row(self):
        row = self.collision("law_a")
        self.assertEqual(row["verdict"], OURS_WIPED)
        self.assertEqual(row["entity_type"], "laws")
        self.assertEqual(row["server_type"], "Laws")
        self.assertEqual(row["theirs"], [{"file": "common/laws/zMoG_laws.txt", "line": 3,
                                          "directive": "TRY_REPLACE"}])
        self.assertEqual(row["ours"], [{"file": "common/laws/modified.txt", "line": 1,
                                        "directive": "REPLACE"}])
        self.assertTrue(row["in_vanilla"])
        self.assertEqual(row["later_file"], THEIRS)
        self.assertEqual(row["fields_both_set"], ["group"])
        self.assertEqual(self.collision("great_power")["verdict"], ORDER_DEPENDS_ON_CASE)
        self.assertEqual(self.collision("state_turmoil")["verdict"], BOTH_MERGE)

    def test_defines_per_key_and_no_at_variables(self):
        self.assertEqual(len(self.report["defines"]), 1)
        d = self.report["defines"][0]
        self.assertEqual((d["block"], d["key"], d["ours"], d["theirs"]),
                         ("NPops", "WORKING_ADULT_RATIO_SKEW_MAXIMUM", "1000000", "4.0"))
        self.assertEqual(d["winner"], THEIRS)
        dumped = json.dumps(self.report)
        self.assertNotIn("@inner", dumped)
        self.assertNotIn("@shared_const", dumped)

    def test_on_action_hooks_are_additive(self):
        self.assertEqual(self.report["additive_hooks"],
                         ["on_game_started", "on_monthly_pulse_country"])
        self.assertNotIn("on_monthly_pulse_country",
                         [c["key"] for c in self.report["key_collisions"]])
        conflicts = self.report["on_action_conflicts"]
        self.assertEqual([(c["hook"], c["field"], c["winner"]) for c in conflicts],
                         [("on_monthly_pulse_country", "effect", THEIRS)])

    def test_event_namespace_and_id_collisions(self):
        ns = self.report["event_namespace_collisions"]
        self.assertEqual([n["namespace"] for n in ns], ["shared_ns"])
        self.assertEqual(ns[0]["colliding_ids"], ["shared_ns.1"])
        ids = self.report["event_id_collisions"]
        self.assertEqual([(i["id"], i["verdict"]) for i in ids], [("shared_ns.1", UNDETERMINED)])

    def test_loc_collisions(self):
        rows = {r["key"]: r for r in self.report["loc_collisions"]}
        self.assertEqual(set(rows), {"shared_key", "vanilla_key"})
        self.assertEqual(rows["shared_key"]["winner"], UNDETERMINED)
        self.assertEqual(rows["shared_key"]["later_file"], OURS)     # te_misc_ after mog_
        self.assertFalse(rows["shared_key"]["same_text"])
        self.assertEqual(rows["vanilla_key"]["winner"], OURS)        # ours is in replace/
        self.assertTrue(rows["vanilla_key"]["ours"]["replace"])

    def test_path_collisions(self):
        rows = {r["path"]: r for r in self.report["path_collisions"]}
        # notes.md is in both, but the game doesn't read it.
        self.assertEqual(set(rows), {"gui/budget_panel.gui",
                                     "localization/spanish/te_misc_l_spanish.yml"})
        self.assertEqual(rows["localization/spanish/te_misc_l_spanish.yml"]
                         ["ours_generated_at_deploy_from"],
                         "localization/english/te_misc_l_english.yml")

    def test_history_is_additive_and_skipped(self):
        dirs = {d["dir"]: d for d in self.report["dirs"]}
        self.assertEqual(dirs["history/countries"]["rule"]["kind"], "additive")
        self.assertNotIn("COUNTRIES", [c["key"] for c in self.report["key_collisions"]])


class InputTests(unittest.TestCase):
    def test_validate_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(emo.validate_root(tmp), os.path.abspath(tmp))
            path = os.path.join(tmp, "f.txt")
            open(path, "w").close()
            for bad in (None, "", path, os.path.join(tmp, "missing")):
                with self.subTest(bad=bad):
                    with self.assertRaises(ValueError):
                        emo.validate_root(bad)

    def test_mod_name_from_descriptor(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "descriptor.mod"), "w", encoding="utf-8") as f:
                f.write('version="1"\nname="Old Style Mod"\n')
            self.assertEqual(emo.read_mod_name(tmp), "Old Style Mod")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(emo.read_mod_name(tmp))

    def test_cli_rejects_a_bad_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(emo.main([os.path.join(tmp, "missing")]), 2)


class VanillaIndexTests(unittest.TestCase):
    def test_game_files_give_file_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "laws/00_laws.txt", "law_a = { }\n\nlaw_b = { }\n")
            idx = emo.VanillaIndex(game_common=tmp, snapshot_dir=None)
            self.assertEqual(idx.source("laws"), "game_files")
            self.assertEqual(idx.ops("laws", "law_b"), [Op(VANILLA, "00_laws.txt", 3)])
            self.assertIs(idx.ops("laws", "law_nope"), False)
            self.assertIsNone(idx.ops("parties", "x"))   # no such vanilla folder

    def test_snapshot_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "common"))
            with open(os.path.join(tmp, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump({"entity_types": {"Laws": {"dir": "game/common/laws",
                                                     "file": "common/laws.json"}}}, f)
            with open(os.path.join(tmp, "common", "laws.json"), "w", encoding="utf-8") as f:
                json.dump({"law_a": ["=", {}]}, f)
            idx = emo.VanillaIndex(game_common=None, snapshot_dir=tmp)
            self.assertEqual(idx.ops("laws", "law_a"), [Op(VANILLA, None, 0)])
            self.assertIs(idx.ops("laws", "law_b"), False)
            self.assertIsNone(idx.ops("scripted_effects", "x"))


if __name__ == "__main__":
    unittest.main()
