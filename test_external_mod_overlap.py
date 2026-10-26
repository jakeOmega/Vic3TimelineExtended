"""Tests for external_mod_overlap (#1170): the load-order model one verdict at
a time (with the probed engine facts, and with the unknowns put back so the
scenario machinery stays covered), the scanner, and the whole report on two
small fake mods in a tmpdir. GET /external-mod-overlap is tested through the
handler in test_mod_state_server_endpoints.ExternalModOverlapEndpointTests."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest import mock

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


def unknown_engine(test):
    """Put back the unknowns the 2026-10-26 probe settled, for `test`'s
    duration, so the code that simulates them stays tested."""
    for name in ("KNOWN_FILE_ORDER", "KNOWN_LOAD_READING"):
        patch = mock.patch.object(emo, name, None)
        patch.start()
        test.addCleanup(patch.stop)


class VerdictTests(unittest.TestCase):
    """resolve() with the probed engine (ASCII file order, every bare
    definition read before any directive), one verdict per test."""

    def test_settings_are_the_probed_answers(self):
        self.assertEqual(emo.KNOWN_FILE_ORDER, "ascii")
        self.assertEqual(emo.KNOWN_LOAD_READING, "creations_first")
        self.assertEqual(emo.BARE_DUPLICATE_RULES["scripted_effects"], FIRST_WINS)
        self.assertEqual(emo.BARE_DUPLICATE_RULES["static_modifiers"], FIRST_WINS)

    def test_ours_wiped_their_later_replace(self):
        # The issue's example: our REPLACE in modified.txt, their TRY_REPLACE
        # in zMoG_SPA_citizenship.txt, which sorts later.
        res = resolve([ours("modified.txt", "REPLACE", 151)],
                      [theirs("zMoG_SPA_citizenship.txt", "TRY_REPLACE", 145)],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], OURS_WIPED)
        self.assertEqual(res["later_file"], THEIRS)
        self.assertFalse(res["order_depends_on_case"])
        self.assertEqual(res["ours_lost"], [ours("modified.txt", "REPLACE", 151)])
        self.assertEqual([s["effect"] for s in res["trace"]], ["created", "replaced", "replaced"])
        self.assertEqual(res["trace_scenario"]["load_reading"], "creations_first")

    def test_theirs_wiped_bare_duplicate_is_dropped(self):
        # A bare redefinition of a key vanilla has is `Duplicated key X will
        # not be created` when its file sorts after vanilla's.
        res = resolve([ours("a.txt", "INJECT")], [theirs("zz.txt")], IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], THEIRS_WIPED)
        effects = {s["side"]: s["effect"] for s in res["trace"]}
        self.assertEqual(effects[THEIRS], "dropped_duplicate")

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

    def test_spa_country_ranks_resolve_in_ascii_order(self):
        # `MoG_SPA_country_ranks.txt` sorts before `extra_country_ranks.txt`
        # in ASCII order (M < e), so our INJECT lands on their REPLACE.
        res = resolve([ours("extra_country_ranks.txt", "INJECT")],
                      [theirs("MoG_SPA_country_ranks.txt", "TRY_REPLACE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)
        self.assertEqual(res["ours_lost"], [])
        self.assertEqual(res["later_file"], OURS)
        self.assertFalse(res["order_depends_on_case"])

    def test_probe_file_order_is_ascii(self):
        # B_ before a_, and p_ before pa_ (`_` is 0x5F, before `a`): the first
        # bare definition wins.
        res = resolve([ours("a_x.txt")], [theirs("B_x.txt")], False, FIRST_WINS)
        self.assertEqual(res["verdict"], OURS_WIPED)
        res = resolve([ours("pa_x.txt")], [theirs("p_x.txt")], False, FIRST_WINS)
        self.assertEqual(res["verdict"], OURS_WIPED)

    def test_inject_before_its_bare_target_applies(self):
        # Probe fact 4: directives apply after every bare definition.
        res = resolve([ours("a.txt", "INJECT")], [theirs("z.txt")], False, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)

    def test_bare_copy_sorting_before_vanillas_file_wins(self):
        # Probe fact 2: vanilla's files are interleaved by name. Demography's
        # laws/00_welfare.txt restates vanilla laws bare, and vanilla's are in
        # 02_welfare.txt, so their copy stays and vanilla's is dropped.
        vanilla = [Op(VANILLA, "02_welfare.txt", 10)]
        res = resolve([ours("sol_injections.txt", "INJECT")], [theirs("00_welfare.txt")],
                      vanilla, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)
        self.assertEqual([s["side"] for s in res["trace"]], [THEIRS, VANILLA, OURS])
        self.assertEqual(res["trace"][1]["effect"], "dropped_duplicate")

    def test_bare_copy_sorting_after_vanillas_file_is_dropped(self):
        vanilla = [Op(VANILLA, "00_diplomacy_modifiers.txt", 10)]
        res = resolve([ours("extra.txt", "INJECT")], [theirs("zz_copy.txt")], vanilla, FIRST_WINS)
        self.assertEqual(res["verdict"], THEIRS_WIPED)

    def test_same_path_depends_on_playset(self):
        res = resolve([ours("00_laws.txt", "REPLACE")], [theirs("00_Laws.txt", "REPLACE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], DEPENDS_ON_PLAYSET)
        self.assertEqual(res["later_file"], "same_path")
        self.assertEqual(res["depends_on"], ["later_mod"])
        by_mod = {s["later_mod"]: s["verdict"] for s in res["verdict_by_scenario"]}
        self.assertEqual(by_mod, {THEIRS: OURS_WIPED, OURS: THEIRS_WIPED})

    def test_unknown_bare_rule_is_undetermined(self):
        # scripted_triggers: nobody recorded whether the first or the last
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
        res = resolve([ours("z.txt", "REPLACE_OR_CREATE")], [theirs("a.txt", "TRY_REPLACE")],
                      False, FIRST_WINS)
        self.assertEqual(res["verdict"], THEIRS_WIPED)
        self.assertEqual(res["trace"][0]["effect"], "skipped_no_entry")

    def test_plain_inject_with_no_entry_errors(self):
        res = resolve([ours("a.txt", "INJECT")], [theirs("b.txt", "INJECT_OR_CREATE")],
                      False, FIRST_WINS)
        self.assertEqual(res["verdict"], OURS_WIPED)
        self.assertEqual([s["effect"] for s in res["trace"]], ["error_no_entry", "created"])

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


class UnknownEngineTests(unittest.TestCase):
    """resolve() with the probed unknowns put back: the file-name order and
    the load reading are simulated every way again."""

    def setUp(self):
        unknown_engine(self)

    def test_order_depends_on_case(self):
        # `MoG_x.txt` sorts before `extra_x.txt` in ASCII order (M < e) and
        # after it folded either way.
        res = resolve([ours("extra_country_ranks.txt", "INJECT")],
                      [theirs("MoG_SPA_country_ranks.txt", "TRY_REPLACE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], ORDER_DEPENDS_ON_CASE)
        self.assertTrue(res["order_depends_on_case"])
        self.assertEqual(res["later_file"], "depends_on_case")
        self.assertEqual(res["depends_on"], ["file_order"])
        by_order = {s["file_order"]: s["verdict"] for s in res["verdict_by_scenario"]}
        self.assertEqual(by_order, {"ascii": BOTH_MERGE, "lower_folded": OURS_WIPED,
                                    "upper_folded": OURS_WIPED})

    def test_upper_and_lower_folding_differ_on_underscore(self):
        # `_` (0x5F) sorts before `a` lowercase-folded, after `A` upper-folded.
        res = resolve([ours("a_x.txt")], [theirs("_x.txt")], False, FIRST_WINS)
        by_order = {s["file_order"]: s["verdict"] for s in res["verdict_by_scenario"]}
        self.assertEqual(by_order, {"ascii": OURS_WIPED, "lower_folded": OURS_WIPED,
                                    "upper_folded": THEIRS_WIPED})

    def test_case_difference_that_changes_nothing_keeps_the_verdict(self):
        res = resolve([ours("extra.txt", "INJECT")], [theirs("MoG.txt", "INJECT")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)
        self.assertTrue(res["order_depends_on_case"])

    def test_directive_before_the_other_mods_creation(self):
        res = resolve([ours("a.txt", "INJECT")], [theirs("z.txt")], False, FIRST_WINS)
        self.assertEqual(res["verdict"], UNDETERMINED)
        self.assertEqual(res["depends_on"], ["load_reading"])
        by_reading = {s["load_reading"]: s["verdict"] for s in res["verdict_by_scenario"]}
        self.assertEqual(by_reading, {"vanilla_first": OURS_WIPED, "interleaved": OURS_WIPED,
                                      "creations_first": BOTH_MERGE})

    def test_vanilla_first_against_interleaved(self):
        # A mod INJECT in a file that sorts before vanilla's: errors when files
        # interleave and apply in order, lands with vanilla first or with
        # directives deferred.
        vanilla = [Op(VANILLA, "personality_traits.txt", 5)]
        res = resolve([ours("extra_character_traits.txt", "INJECT")], [theirs("zz.txt", "INJECT")],
                      vanilla, FIRST_WINS)
        by_reading = {s["load_reading"]: s["verdict"] for s in res["verdict_by_scenario"]}
        self.assertEqual(by_reading, {"vanilla_first": BOTH_MERGE, "interleaved": OURS_WIPED,
                                      "creations_first": BOTH_MERGE})

    def test_two_deciding_unknowns_are_undetermined(self):
        # Theirs ships our file (without the key), and their REPLACE sorts
        # before our INJECT only in ASCII order: both the playset and the
        # file order change the outcome.
        res = resolve([ours("extra.txt", "INJECT")], [theirs("MoG.txt", "REPLACE")], IN_VANILLA,
                      FIRST_WINS, ours_files=["extra.txt"], theirs_files=["extra.txt", "MoG.txt"])
        self.assertEqual(res["verdict"], UNDETERMINED)
        self.assertEqual(res["depends_on"], ["file_order", "later_mod"])
        rows = {(s["file_order"], s["later_mod"]): s["verdict"] for s in res["verdict_by_scenario"]}
        self.assertEqual(rows[("ascii", "ours")], BOTH_MERGE)
        self.assertEqual(rows[("lower_folded", "ours")], OURS_WIPED)
        self.assertEqual(rows[("ascii", "theirs")], OURS_WIPED)


class OrderHelperTests(unittest.TestCase):
    def test_sort_ops_by_order(self):
        ops = [ours("extra.txt"), theirs("MoG.txt"), Op(VANILLA, None, 0)]
        self.assertEqual([o.path for o in emo.sort_ops(ops, "ascii")], [None, "MoG.txt", "extra.txt"])
        self.assertEqual([o.path for o in emo.sort_ops(ops, "lower_folded")],
                         [None, "extra.txt", "MoG.txt"])

    def test_vanilla_interleaves_or_comes_first(self):
        ops = [ours("00_a.txt"), Op(VANILLA, "00_companies.txt", 1)]
        self.assertEqual([o.side for o in emo.sort_ops(ops, "ascii", vanilla_first=False)],
                         [OURS, VANILLA])
        self.assertEqual([o.side for o in emo.sort_ops(ops, "ascii", vanilla_first=True)],
                         [VANILLA, OURS])

    def test_creations_first_reading(self):
        ops = [ours("a.txt", "INJECT"), theirs("z.txt"), Op(VANILLA, "m.txt", 1)]
        ordered = emo.order_for_reading(ops, "ascii", "creations_first")
        self.assertEqual([(o.side, o.directive) for o in ordered],
                         [(VANILLA, None), (THEIRS, None), (OURS, "INJECT")])

    def test_order_depends_on_case_needs_an_unknown_order(self):
        self.assertFalse(emo.order_depends_on_case([ours("extra.txt")], [theirs("MoG.txt")]))
        unknown_engine(self)
        self.assertTrue(emo.order_depends_on_case([ours("extra.txt")], [theirs("MoG.txt")]))
        self.assertTrue(emo.order_depends_on_case([ours("_x.txt")], [theirs("a_x.txt")]))
        self.assertFalse(emo.order_depends_on_case([ours("00_x.txt")], [theirs("Zz.txt")]))

    def test_resolve_later_wins(self):
        self.assertEqual(emo.resolve_later_wins([ours("extra.txt")], [theirs("zzz.txt")])["winner"],
                         THEIRS)
        self.assertEqual(emo.resolve_later_wins([ours("extra.txt")], [theirs("MoG.txt")])["winner"],
                         OURS)
        self.assertEqual(emo.resolve_later_wins([ours("d.txt")], [theirs("D.txt")])["winner"],
                         DEPENDS_ON_PLAYSET)
        unknown_engine(self)
        self.assertEqual(emo.resolve_later_wins([ours("extra.txt")], [theirs("MoG.txt")])["winner"],
                         ORDER_DEPENDS_ON_CASE)


class RuleTests(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(emo.rule_for("laws").bare_duplicate, FIRST_WINS)
        self.assertEqual(emo.rule_for("technology/technologies").kind, "database")
        self.assertEqual(emo.rule_for("static_modifiers").bare_duplicate, FIRST_WINS)
        self.assertEqual(emo.rule_for("scripted_effects").bare_duplicate, FIRST_WINS)
        self.assertEqual(emo.rule_for("script_values").bare_duplicate, LAST_WINS)
        self.assertEqual(emo.rule_for("scripted_triggers").bare_duplicate, UNKNOWN)
        self.assertEqual(emo.rule_for("history/countries").kind, "additive")
        self.assertEqual(emo.rule_for("defines").kind, "defines")
        self.assertEqual(emo.rule_for("on_actions").kind, "on_actions")

    def test_rule_sources_name_model_entries(self):
        for db in ("laws", "script_values", "scripted_triggers", "defines", "on_actions"):
            with self.subTest(db=db):
                self.assertIn(emo.rule_for(db).source, emo.LOAD_ORDER_MODEL)
        for name, entry in emo.LOAD_ORDER_MODEL.items():
            with self.subTest(entry=name):
                self.assertEqual(set(entry), {"status", "claim", "see"})

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

    def test_escaped_quote_does_not_hide_a_comment_or_eat_the_file(self):
        text = 'a = { desc = "say \\"hi # there\\"" }  # a comment { \nb = { }\n'
        entries, warnings = emo.scan_script(text)
        self.assertEqual(warnings, [])
        self.assertEqual([e.key for e in entries], ["a", "b"])
        self.assertEqual(emo.strip_comment('x = "a \\" # b" # c'), 'x = "a \\" # b" ')
        self.assertEqual(emo.strip_comment('x = "never closed # c'), 'x = "never closed ')

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
    # Theirs ships a file at our decrees/modified.txt path, without decree_x.
    _write(o, "common/decrees/modified.txt", "INJECT:decree_x = { modifier = { a = 1 } }\n")
    _write(t, "common/decrees/modified.txt", "INJECT:decree_y = { modifier = { a = 1 } }\n")
    _write(t, "common/decrees/zz_decrees.txt", "INJECT:decree_x = { modifier = { b = 1 } }\n")
    _write(o, "common/defines/extra_defines.txt",
           "@shared_const = 1\nNPops = {\n\tWORKING_ADULT_RATIO_SKEW_MAXIMUM = 1000000\n"
           "\t@inner = 2\n\tONLY_OURS = 1\n}\n")
    _write(o, "common/defines/te_more_defines.txt",
           "NPops = {\n\tWORKING_ADULT_RATIO_SKEW_MAXIMUM = 7\n}\n")
    _write(t, "common/defines/zzz_def.txt",
           "@shared_const = 7\nNPops = {\n\tWORKING_ADULT_RATIO_SKEW_MAXIMUM = 4.0\n"
           "\t@inner = 9\n}\n")
    _write(o, "common/on_actions/extra_on_actions.txt",
           "on_monthly_pulse_country = {\n\ton_actions = { te_monthly }\n\teffect = { a = b }\n}\n"
           "on_game_started = { events = { te.1 } }\n")
    _write(t, "common/on_actions/zz_their_on_actions.txt",
           "on_monthly_pulse_country = {\n\ton_actions = { mog_monthly }\n\teffect = { c = d }\n}\n"
           "on_game_started = { events = { mog.1 } }\nonly_theirs = { events = { mog.2 } }\n")
    _write(o, "events/our_events.txt",
           "namespace = shared_ns\nshared_ns.1 = { type = country_event }\nshared_ns.9 = 1\n")
    _write(t, "events/their_events.txt",
           "namespace = shared_ns\nnamespace = mog\nshared_ns.1 = { type = country_event }\n"
           "shared_ns.9 = 1\nmog.1 = { }\n")
    _write(o, "localization/english/te_misc_l_english.yml",
           'l_english:\n shared_key:0 "Ours"\n only_ours:0 "x"\n')
    _write(t, "localization/english/mog_l_english.yml", 'l_english:\n shared_key:0 "Theirs"\n')
    _write(o, "localization/english/replace/te_override_l_english.yml",
           'l_english:\n vanilla_key:0 "Ours"\n')
    _write(t, "localization/english/mog2_l_english.yml", 'l_english:\n vanilla_key: "Theirs"\n')
    _write(t, "localization/replace/english/mog_replace_l_english.yml",
           'l_english:\n only_ours:0 "Theirs, replacing"\n')
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


FAKE_VANILLA = {"laws": {"law_a"}, "country_ranks": {"great_power"},
                "static_modifiers": {"state_turmoil"}, "decrees": {"decree_x", "decree_y"}}


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.ours_root, cls.theirs_root = build_fake_mods(cls._tmp.name)
        cls.report = emo.analyze(cls.theirs_root, cls.ours_root, vanilla=FAKE_VANILLA)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def collision(self, key):
        return next(c for c in self.report["key_collisions"] if c["key"] == key)

    def test_mod_name_and_counts(self):
        self.assertEqual(self.report["mod_name"], "Fake Pop Mod")
        self.assertEqual(self.report["summary"]["key_collisions"], 4)
        self.assertEqual(self.report["summary"]["by_verdict"],
                         {BOTH_MERGE: 2, DEPENDS_ON_PLAYSET: 1, OURS_WIPED: 1})

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
        self.assertNotIn("trace", row)   # opt-in
        self.assertEqual(self.collision("great_power")["verdict"], BOTH_MERGE)
        self.assertEqual(self.collision("state_turmoil")["verdict"], BOTH_MERGE)

    def test_a_file_shipped_at_our_path_reaches_the_verdict(self):
        # Their decrees/modified.txt doesn't define decree_x, but whichever
        # mod loads later keeps its own copy of that file.
        row = self.collision("decree_x")
        self.assertEqual(row["verdict"], DEPENDS_ON_PLAYSET)
        self.assertIn("common/decrees/modified.txt",
                      [p["path"] for p in self.report["path_collisions"]])

    def test_defines_per_key_and_no_at_variables(self):
        self.assertEqual(len(self.report["defines"]), 1)
        d = self.report["defines"][0]
        # Our later file (te_more_defines.txt) holds our value.
        self.assertEqual((d["block"], d["key"], d["ours"], d["theirs"]),
                         ("NPops", "WORKING_ADULT_RATIO_SKEW_MAXIMUM", "7", "4.0"))
        self.assertEqual(d["ours_file"]["file"], "common/defines/te_more_defines.txt")
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
        # shared_ns.9 = 1 is a scalar, not an event.
        self.assertEqual([(i["id"], i["verdict"]) for i in ids], [("shared_ns.1", UNDETERMINED)])

    def test_loc_collisions(self):
        rows = {r["key"]: r for r in self.report["loc_collisions"]}
        self.assertEqual(set(rows), {"shared_key", "vanilla_key", "only_ours"})
        self.assertEqual(rows["shared_key"]["winner"], UNDETERMINED)
        self.assertEqual(rows["shared_key"]["later_file"], OURS)     # te_misc_ after mog_
        self.assertFalse(rows["shared_key"]["same_text"])
        self.assertEqual(rows["vanilla_key"]["winner"], OURS)        # ours is in replace/
        self.assertTrue(rows["vanilla_key"]["ours"]["replace"])
        # localization/replace/english/ is a replace folder too.
        self.assertEqual(rows["only_ours"]["winner"], THEIRS)
        self.assertEqual(rows["only_ours"]["theirs"]["file"],
                         "localization/replace/english/mog_replace_l_english.yml")

    def test_path_collisions(self):
        rows = {r["path"]: r for r in self.report["path_collisions"]}
        # notes.md is in both, but the game doesn't read it.
        self.assertEqual(set(rows), {"gui/budget_panel.gui", "common/decrees/modified.txt",
                                     "localization/spanish/te_misc_l_spanish.yml"})
        self.assertEqual(rows["localization/spanish/te_misc_l_spanish.yml"]
                         ["ours_generated_at_deploy_from"],
                         "localization/english/te_misc_l_english.yml")

    def test_history_is_additive_and_skipped(self):
        dirs = {d["dir"]: d for d in self.report["dirs"]}
        self.assertEqual(dirs["history/countries"]["rule"]["kind"], "additive")
        self.assertNotIn("COUNTRIES", [c["key"] for c in self.report["key_collisions"]])

    def test_trace_with_game_files_names_vanillas_file(self):
        with tempfile.TemporaryDirectory() as game:
            _write(game, "laws/00_laws.txt", "law_a = { }\n")
            report = emo.analyze(self.theirs_root, self.ours_root, include_trace=True,
                                 vanilla=emo.VanillaIndex(game_common=game, snapshot_dir=None))
        row = next(c for c in report["key_collisions"] if c["key"] == "law_a")
        self.assertEqual(row["trace"][0]["file"], "game/common/laws/00_laws.txt")
        self.assertEqual(row["trace"][1]["file"], "common/laws/modified.txt")
        # The game is installed and has no decrees folder: not in vanilla.
        self.assertIs(next(c for c in report["key_collisions"]
                           if c["key"] == "decree_x")["in_vanilla"], False)


class GitGuardTests(unittest.TestCase):
    """git reads a repository's config (core.fsmonitor, hooks), so it must
    never run in the other mod's folder (review I2)."""

    def test_git_never_runs_for_the_other_mod(self):
        with tempfile.TemporaryDirectory() as tmp:
            o, t = build_fake_mods(tmp)
            os.makedirs(os.path.join(t, ".git"))
            os.makedirs(os.path.join(tmp, "bare_theirs", ".git"))
            _write(tmp, "bare_theirs/events/x.txt", "namespace = x\n")
            calls = []

            def fake_run(cmd, *a, **k):
                calls.append(cmd)
                raise AssertionError(f"git ran: {cmd}")

            with mock.patch.object(emo.subprocess, "run", side_effect=fake_run):
                emo.analyze(t, o, vanilla=FAKE_VANILLA)
                emo.analyze(os.path.join(tmp, "bare_theirs"), o, vanilla=FAKE_VANILLA)
            self.assertEqual(calls, [])

    def test_our_sparse_folder_is_listed_through_git_without_its_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".git"))
            with mock.patch.object(emo.subprocess, "run") as run:
                run.return_value = mock.Mock(returncode=0, stdout="gfx/a.dds\0")
                self.assertEqual(emo.list_files(tmp, "gfx", git_fallback=True), ["gfx/a.dds"])
                self.assertEqual(emo.list_files(tmp, "gfx"), [])
            cmd = run.call_args_list[0].args[0]
            self.assertIn("core.fsmonitor=false", cmd)
            self.assertIn("core.hooksPath=/dev/null", cmd)
            self.assertEqual(run.call_count, 1)


class InputTests(unittest.TestCase):
    def test_validate_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "mod", "common"))
            self.assertEqual(emo.validate_root(os.path.join(tmp, "mod")),
                             os.path.abspath(os.path.join(tmp, "mod")))
            path = os.path.join(tmp, "f.txt")
            open(path, "w").close()
            # `tmp` itself holds only a mod folder: the Workshop parent with
            # the id left off.
            for bad in (None, "", path, os.path.join(tmp, "missing"), tmp):
                with self.subTest(bad=bad):
                    with self.assertRaises(ValueError):
                        emo.validate_root(bad)

    def test_a_descriptor_alone_is_a_mod_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "descriptor.mod"), "w", encoding="utf-8") as f:
                f.write('version="1"\nname="Old Style Mod"\n')
            self.assertEqual(emo.validate_root(tmp), os.path.abspath(tmp))
            self.assertEqual(emo.read_mod_name(tmp), "Old Style Mod")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(emo.read_mod_name(tmp))

    def test_cli_rejects_a_bad_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(emo.main([os.path.join(tmp, "missing")]), 2)
            self.assertEqual(emo.main([tmp]), 2)   # an empty folder


GUI_SAMPLE = """\
@width = 10
Types my_panel_types
{
\ttype shared_type = widget {
\t\tname = "type fake_in_string = x"
\t}
\t#type commented_out = widget { }
\ttype Other_Type = shared_type { }
}
template shared_template { size = { 1 1 } }
local_template file_local { }
layer layer_mine
{
\tpriority = 1
}
texticon = {
\ticonsize = { texture = "gfx/x.dds" }
\ticon = mine_icon
}
widget = { layer = layer_mine using = shared_template }
"""


class GuiScanTests(unittest.TestCase):
    def test_scan_gui(self):
        defs = emo.scan_gui(GUI_SAMPLE)
        self.assertEqual([(d.kind, d.name, d.line, d.group) for d in defs], [
            ("type", "shared_type", 4, "my_panel_types"),
            ("type", "Other_Type", 8, "my_panel_types"),
            ("template", "shared_template", 10, None),
            ("layer", "layer_mine", 12, None),
            ("texticon", "mine_icon", 18, None),
        ])


def build_fake_gui_mods(tmp):
    """Two mods whose gui/ trees define the same names: in different files
    (a collision), and only in a file both ship (left to path_collisions)."""
    o, t = os.path.join(tmp, "ours"), os.path.join(tmp, "theirs")
    _write(o, "gui/construction_panel.gui",
           "types construction_panel {\n\ttype construction_panel = window { }\n}\n"
           "template shared_template { }\n")
    _write(t, "gui/PSC_construction_panel.gui",
           "types construction_panel\n{\n\ttype construction_panel = window { }\n}\n")
    _write(o, "gui/zzz_extra_texticons.gui", "texticon = { icon = shared_icon }\n")
    _write(t, "gui/scripted_widgets/a_icons.gui", "texticon = {\n\ticon = shared_icon\n}\n")
    # Both ship gui/topbar.gui: only one of them loads.
    _write(o, "gui/topbar.gui", "template shared_template { }\ntemplate only_topbar { }\n")
    _write(t, "gui/topbar.gui", "template only_topbar { }\n")
    _write(t, "gui/b_templates.gui", "template shared_template { }\n")
    return o, t


class GuiCollisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.ours_root, cls.theirs_root = build_fake_gui_mods(cls._tmp.name)
        game = os.path.join(cls._tmp.name, "game")
        _write(game, "common/laws/00_laws.txt", "law_a = { }\n")
        _write(game, "gui/construction_panel.gui",
               "types construction_panel {\n\n\ttype construction_panel = window { }\n}\n")
        cls.report = emo.analyze(cls.theirs_root, cls.ours_root, vanilla=emo.VanillaIndex(
            game_common=os.path.join(game, "common"), snapshot_dir=None))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_rows(self):
        rows = {(r["kind"], r["name"]): r for r in self.report["gui_type_collisions"]}
        self.assertEqual(set(rows), {("type", "construction_panel"), ("texticon", "shared_icon"),
                                     ("template", "shared_template")})
        row = rows[("type", "construction_panel")]
        self.assertEqual(row["ours"], [{"file": "gui/construction_panel.gui", "line": 2,
                                        "group": "construction_panel"}])
        self.assertEqual(row["theirs"], [{"file": "gui/PSC_construction_panel.gui", "line": 3,
                                          "group": "construction_panel"}])
        # PSC_ sorts before construction_ in ASCII order (uppercase first).
        self.assertEqual(row["sorts_first"], THEIRS)
        self.assertTrue(row["in_vanilla"])
        self.assertEqual(row["vanilla"], [{"file": "game/gui/construction_panel.gui", "line": 3}])
        self.assertNotIn("winner", row)
        self.assertNotIn("verdict", row)
        icon = rows[("texticon", "shared_icon")]
        self.assertEqual(icon["theirs"], [{"file": "gui/scripted_widgets/a_icons.gui", "line": 2}])
        self.assertEqual(icon["sorts_first"], THEIRS)   # scripted_widgets/ < zzz_
        self.assertIs(icon["in_vanilla"], False)
        # Ours defines it in topbar.gui (a file both ship) and in
        # construction_panel.gui; theirs in b_templates.gui.
        tpl = rows[("template", "shared_template")]
        self.assertEqual(tpl["files_both_ship"], ["gui/topbar.gui"])
        self.assertEqual(tpl["sorts_first"], THEIRS)

    def test_a_name_only_in_a_file_both_ship_is_a_path_collision(self):
        names = [r["name"] for r in self.report["gui_type_collisions"]]
        self.assertNotIn("only_topbar", names)
        self.assertIn("gui/topbar.gui", [p["path"] for p in self.report["path_collisions"]])

    def test_load_order_is_unprobed(self):
        self.assertEqual(self.report["gui_load_order"]["status"], "unprobed")
        self.assertEqual(self.report["summary"]["gui_type_collisions"], 3)

    def test_without_the_game_in_vanilla_is_unknown(self):
        report = emo.analyze(self.theirs_root, self.ours_root, vanilla={})
        self.assertTrue(all(r["in_vanilla"] is None for r in report["gui_type_collisions"]))


LAYER_TYPES = {"Laws": "laws", "Modifiers": "static_modifiers", "Script Values": "script_values",
               "Scripted Triggers": "scripted_triggers", "Decrees": "decrees"}


def build_fake_layer_mods(tmp):
    """Vanilla game files, `ours` and `theirs`, for the layered state
    (#1184): (game common dir, ours root, theirs root)."""
    game, o, t = (os.path.join(tmp, d) for d in ("game", "ours", "theirs"))
    _write(game, "common/laws/00_laws.txt",
           "law_v = { group = lawgroup_x modifier = { v_add = 1 } }\n"
           "law_rebare = { group = lawgroup_x }\n")
    _write(game, "common/decrees/00_decrees.txt", "decree_v = { cost = 1 }\n")
    _write(game, "common/script_values/00_values.txt", "sv_v = { value = 1 add = 2 }\n")
    # Their INJECT, in a file that sorts before ours, lands on our bare entry:
    # directives apply after every bare definition.
    _write(o, "common/laws/te_laws.txt",
           "te_law = { group = lawgroup_x modifier = { a_add = 1 } }\n"
           "law_rebare = { group = lawgroup_ours }\n")
    _write(t, "common/laws/a_their_laws.txt",
           "INJECT:te_law = { modifier = { b_add = 2 } }\n"
           "INJECT:law_rebare = { icon = x }\n"
           "TRY_INJECT:law_nowhere = { icon = x }\n"
           "law_theirs = { group = lawgroup_x }\n")
    _write(t, "common/laws/zz_broken.txt", "law_broken = { = }\n")
    # Bare duplicates (static modifiers: the first one wins).
    _write(o, "common/static_modifiers/te_mods.txt",
           "shared_mod = { x_add = 1 }\nours_first = { y_add = 1 }\n")
    _write(t, "common/static_modifiers/a_their_mods.txt", "shared_mod = { x_add = 2 }\n")
    _write(t, "common/static_modifiers/zz_their_mods.txt", "ours_first = { y_add = 2 }\n")
    # A bare duplicate in a folder whose rule isn't recorded (the tests
    # take scripted_triggers' rule out of BARE_DUPLICATE_RULES).
    _write(o, "common/scripted_triggers/te_triggers.txt", "shared_trigger = { always = yes }\n")
    _write(t, "common/scripted_triggers/zz_triggers.txt",
           "shared_trigger = { always = no }\nREPLACE:vanilla_trigger = { always = no }\n")
    # The server keeps no vanilla scripted triggers; the game files do.
    _write(game, "common/scripted_triggers/00_triggers.txt", "vanilla_trigger = { always = yes }\n")
    # Their file at vanilla's path drops decree_v; one at ours, our decree.
    _write(t, "common/decrees/00_decrees.txt", "decree_w = { cost = 2 }\n")
    _write(o, "common/decrees/te_decrees.txt", "decree_ours = { cost = 3 }\n")
    _write(t, "common/decrees/te_decrees.txt", "decree_w2 = { cost = 4 }\n")
    # An INJECT into a script value appends its steps.
    _write(t, "common/script_values/zz_values.txt", "INJECT:sv_v = { multiply = 3 }\n")
    _write(t, "common/defines/zz_defines.txt", "NGame = { X = 1 }\n")
    _write(t, "common/acceptance_statuses/zz.txt", "status_x = { }\n")
    _write(t, "events/their_events.txt", "namespace = mog\n")
    return os.path.join(game, "common"), o, t


def fake_layer_mod_state(game_common, ours_root):
    from mod_state import ModState
    return ModState({et: os.path.join(game_common, d) for et, d in LAYER_TYPES.items()
                     if et != "Scripted Triggers"},
                    {et: os.path.join(ours_root, "common", d) for et, d in LAYER_TYPES.items()})


class LayeredStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import external_mod_state as ems
        cls.ems = ems
        cls._tmp = tempfile.TemporaryDirectory()
        cls.game, cls.ours_root, cls.theirs_root = build_fake_layer_mods(cls._tmp.name)
        cls.ms = fake_layer_mod_state(cls.game, cls.ours_root)
        cls.vanilla = emo.VanillaIndex(game_common=cls.game, snapshot_dir=None)
        # scripted_triggers stands in for a folder whose bare-duplicate rule
        # isn't recorded: put that unknown back for the build, whatever
        # BARE_DUPLICATE_RULES says about the folder itself.
        with mock.patch.dict(emo.BARE_DUPLICATE_RULES):
            emo.BARE_DUPLICATE_RULES.pop("scripted_triggers", None)
            cls.state = ems.build(cls.ms, cls.theirs_root, cls.ours_root, vanilla=cls.vanilla)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def entry(self, et, key):
        return self.state.entity(et, key)

    def test_their_inject_lands_on_our_entry(self):
        e = self.entry("Laws", "te_law")
        self.assertEqual(e["status"], "changed")
        self.assertEqual(e["value"], ["=", {"group": ["=", "lawgroup_x"],
                                            "modifier": ["=", {"a_add": ["=", "1"],
                                                               "b_add": ["=", "2"]}]}])
        self.assertEqual(e["server_value"][1]["modifier"], ["=", {"a_add": ["=", "1"]}])
        self.assertTrue(e["server_matches_model"])
        self.assertEqual([(s["side"], s["effect"]) for s in e["load"]],
                         [(OURS, "created"), (THEIRS, "injected")])
        self.assertEqual(e["definitions"][0]["file"], "common/laws/a_their_laws.txt")
        # The layered ModState holds it; the server's is untouched.
        laws = self.state.mod_state.get_data("Laws")
        self.assertIn("b_add", laws["te_law"][1]["modifier"][1])
        self.assertNotIn("b_add", self.ms.get_data("Laws")["te_law"][1]["modifier"][1])

    def test_the_order_comes_from_the_model(self):
        # Nothing restates the load order: reverse what order_for_reading
        # returns and their INJECT runs before our entry exists.
        original = emo.order_for_reading
        with mock.patch.object(emo, "order_for_reading",
                               lambda ops, order, reading: original(ops, order, reading)[::-1]):
            state = self.ems.build(self.ms, self.theirs_root, self.ours_root, vanilla=self.vanilla)
        e = state.entity("Laws", "te_law")
        self.assertEqual([(s["side"], s["effect"]) for s in e["load"]],
                         [(THEIRS, "error_no_entry"), (OURS, "created")])
        self.assertNotIn("b_add", e["value"][1]["modifier"][1])

    def test_bare_duplicates_first_wins(self):
        theirs_wins = self.entry("Modifiers", "shared_mod")
        self.assertEqual(theirs_wins["status"], "changed")
        self.assertEqual(theirs_wins["value"], ["=", {"x_add": ["=", "2"]}])
        self.assertEqual([s["effect"] for s in theirs_wins["load"]],
                         ["created", "dropped_duplicate"])
        ours_wins = self.entry("Modifiers", "ours_first")
        self.assertEqual(ours_wins["status"], "unchanged")
        self.assertEqual(ours_wins["value"], ["=", {"y_add": ["=", "1"]}])

    def test_new_and_skipped_keys(self):
        self.assertEqual(self.entry("Laws", "law_theirs")["status"], "added")
        nowhere = self.entry("Laws", "law_nowhere")
        self.assertEqual(nowhere["status"], "not_created")
        self.assertFalse(nowhere["present"])
        self.assertEqual(nowhere["load"][0]["effect"], "skipped_no_entry")

    def test_unknown_bare_rule_gives_candidates(self):
        e = self.entry("Scripted Triggers", "shared_trigger")
        self.assertEqual(e["status"], "undetermined")
        self.assertEqual(e["depends_on"], ["bare_duplicate"])
        by = {c["scenario"]["bare_duplicate"]: c["value"] for c in e["candidates"]}
        self.assertEqual(by[FIRST_WINS], ["=", {"always": ["=", "yes"]}])
        self.assertEqual(by[LAST_WINS], ["=", {"always": ["=", "no"]}])
        self.assertEqual(e["state_holds"], {"bare_duplicate": FIRST_WINS})
        self.assertEqual(e["value"], by[FIRST_WINS])
        self.assertEqual(self.ems._STATE_HOLDS["bare_duplicate"], FIRST_WINS)

    def test_a_type_the_server_holds_no_vanilla_for(self):
        e = self.entry("Scripted Triggers", "vanilla_trigger")
        self.assertEqual(e["status"], "changed")
        self.assertTrue(e["in_vanilla"])
        self.assertEqual([(s["side"], s["effect"]) for s in e["load"]],
                         [(VANILLA, "created"), (THEIRS, "replaced")])
        # The server's mod-only view has no entry, and that matches the
        # model with vanilla left out.
        self.assertFalse(e["server_present"])
        self.assertTrue(e["server_matches_model"])
        layer = self.state.entity_type("Scripted Triggers")
        self.assertFalse(layer["server_holds_vanilla"])

    def test_same_path_files(self):
        # Their 00_decrees.txt replaces vanilla's, which held decree_v.
        removed = self.entry("Decrees", "decree_v")
        self.assertEqual(removed["status"], "removed")
        self.assertTrue(removed["server_present"])
        # Their te_decrees.txt lands on ours: the playset decides.
        e = self.entry("Decrees", "decree_ours")
        self.assertEqual(e["status"], "undetermined")
        self.assertEqual(e["depends_on"], ["later_mod"])
        by = {c["scenario"]["later_mod"]: c["present"] for c in e["candidates"]}
        self.assertEqual(by, {"theirs": False, "ours": True})
        self.assertEqual(e["state_holds"], {"later_mod": "theirs"})
        self.assertNotIn("decree_ours", self.state.mod_state.get_data("Decrees"))
        self.assertEqual(self.ems._STATE_HOLDS["later_mod"], "theirs")

    def test_script_value_inject_appends_steps(self):
        e = self.entry("Script Values", "sv_v")
        self.assertEqual(e["status"], "changed")
        self.assertEqual(e["value"][1]["multiply"], ["=", "3"])
        self.assertEqual(e["value"][1]["value"], ["=", "1"])
        self.assertEqual(e["definitions"][0]["file"], "game/common/script_values/00_values.txt")

    def test_server_merge_that_differs_from_the_model_is_flagged(self):
        # Our bare law_rebare sorts after vanilla's file: the engine drops
        # it, ModState keeps it.
        e = self.entry("Laws", "law_rebare")
        self.assertFalse(e["server_matches_model"])
        self.assertEqual(e["server_value"][1]["group"], ["=", "lawgroup_ours"])
        self.assertEqual(e["value"][1]["group"], ["=", "lawgroup_x"])
        self.assertEqual(e["model_without_them"][0][1]["group"], ["=", "lawgroup_x"])
        laws = next(t for t in self.state.summary()["entity_types"] if t["entity_type"] == "Laws")
        self.assertEqual(laws["server_differs_from_model"], ["law_rebare"])

    def test_a_file_that_does_not_parse(self):
        e = self.entry("Laws", "law_broken")
        self.assertEqual(e["status"], "parse_failed")
        self.assertFalse(e["present"])
        self.assertEqual([f["file"] for f in self.state.parse_failures],
                         ["common/laws/zz_broken.txt"])

    def test_unlayered_key_is_the_servers(self):
        e = self.entry("Laws", "law_v")
        self.assertFalse(e["layered"])
        self.assertEqual(e["value"], ["=", {"group": ["=", "lawgroup_x"],
                                            "modifier": ["=", {"v_add": ["=", "1"]}]}])
        self.assertIsNone(self.entry("Laws", "law_missing"))

    def test_summary(self):
        s = self.state.summary()
        self.assertEqual(s["model"]["load_reading"], ["creations_first"])
        dirs = {n["dir"]: n["reason"] for n in s["not_layered"]}
        self.assertEqual(set(dirs), {"common/defines", "common/acceptance_statuses", "events"})
        self.assertEqual({t["entity_type"] for t in s["entity_types"]}, set(LAYER_TYPES))
        laws = self.state.entity_type("Laws")
        self.assertEqual({r["key"]: r["status"] for r in laws["keys"]},
                         {"te_law": "changed", "law_rebare": "changed", "law_nowhere": "not_created",
                          "law_theirs": "added", "law_broken": "parse_failed"})
        self.assertFalse(self.state.entity_type("Goods")["layered"])
        # shared_trigger, decree_ours, and decree_w2 (their te_decrees.txt
        # loads only if they come later).
        self.assertEqual(s["summary"]["by_status"]["undetermined"], 3)
        decrees = next(t for t in s["entity_types"] if t["entity_type"] == "Decrees")
        self.assertEqual(decrees["undetermined"], ["decree_ours", "decree_w2"])

    def test_snapshot_vanilla_has_no_file_names(self):
        # Without the game files vanilla's definition is the server's value,
        # read first (the snapshot fallback).
        state = self.ems.build(self.ms, self.theirs_root, self.ours_root,
                               vanilla={"laws": {"law_v", "law_rebare"}, "decrees": {"decree_v"},
                                        "script_values": {"sv_v"}, "static_modifiers": set()})
        e = state.entity("Script Values", "sv_v")
        self.assertEqual(e["definitions"][0], {"side": VANILLA, "file": None, "line": None,
                                               "directive": None})
        self.assertEqual(e["value"][1]["multiply"], ["=", "3"])
        # The scripted_triggers folder has no vanilla side either way.
        self.assertEqual(next(t for t in state.summary()["entity_types"]
                              if t["entity_type"] == "Scripted Triggers")["vanilla_source"],
                         "unavailable")


class VanillaIndexTests(unittest.TestCase):
    def test_game_files_give_file_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, "laws/00_laws.txt", "law_a = { }\n\nlaw_b = { }\n")
            idx = emo.VanillaIndex(game_common=tmp, snapshot_dir=None)
            self.assertEqual(idx.source("laws"), "game_files")
            self.assertEqual(idx.ops("laws", "law_b"), [Op(VANILLA, "00_laws.txt", 3)])
            self.assertIs(idx.ops("laws", "law_nope"), False)
            # The game is installed and has no such folder: no vanilla key.
            self.assertIs(idx.ops("parties", "x"), False)
            self.assertEqual(idx.source("parties"), "game_files")

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
            # No game: a folder the snapshot lacks is unknown.
            self.assertIsNone(idx.ops("scripted_effects", "x"))


if __name__ == "__main__":
    unittest.main()
