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
    for name in ("KNOWN_FILE_ORDER", "KNOWN_LOAD_READING", "KNOWN_OR_CREATE_PHASE",
                 "KNOWN_TRY_PHASE"):
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

    def test_our_replace_outlasts_their_later_try_replace(self):
        # #1170's example: our REPLACE in modified.txt, their TRY_REPLACE in
        # zMoG_SPA_citizenship.txt, which sorts later. A TRY_REPLACE doesn't
        # wait for the INJECTs (probe round 5) and a plain REPLACE does, so
        # ours applies last under either try_phase.
        res = resolve([ours("modified.txt", "REPLACE", 151)],
                      [theirs("zMoG_SPA_citizenship.txt", "TRY_REPLACE", 145)],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], THEIRS_WIPED)
        self.assertEqual(res["later_file"], THEIRS)
        self.assertFalse(res["order_depends_on_case"])
        self.assertEqual(res["theirs_lost"], [theirs("zMoG_SPA_citizenship.txt", "TRY_REPLACE", 145)])
        self.assertEqual([(s["side"], s["effect"]) for s in res["trace"]],
                         [(VANILLA, "created"), (THEIRS, "replaced"), (OURS, "replaced")])
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

    def test_their_earlier_replace_still_wipes_our_inject(self):
        # Every INJECT applies before any REPLACE (probe round 3), so a REPLACE
        # in a file that sorts first still has the last word.
        res = resolve([ours("zz.txt", "INJECT")], [theirs("aa.txt", "REPLACE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], OURS_WIPED)
        self.assertEqual([s["effect"] for s in res["trace"]], ["created", "injected", "replaced"])

    def test_injects_on_both_sides_of_a_replace_are_both_lost(self):
        # One INJECT sorts before their REPLACE, the other after it: neither survives.
        res = resolve([ours("a.txt", "INJECT"), ours("z.txt", "INJECT")],
                      [theirs("m.txt", "REPLACE")], IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], OURS_WIPED)
        self.assertEqual(res["ours_lost"], [ours("a.txt", "INJECT"), ours("z.txt", "INJECT")])

    def test_both_merge_inject_and_or_create(self):
        res = resolve([ours("a.txt", "INJECT")], [theirs("b.txt", "INJECT_OR_CREATE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)

    def test_both_wiped_two_bare_redefinitions_of_vanilla(self):
        res = resolve([ours("a.txt")], [theirs("b.txt")], IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_WIPED)

    def test_spa_country_ranks_our_inject_lands_on_their_try_replace(self):
        # `MoG_SPA_country_ranks.txt` sorts before `extra_country_ranks.txt`
        # in ASCII order (M < e). Probe round 5: a TRY_REPLACE in a_ applied
        # before an INJECT in b_, which landed on it.
        res = resolve([ours("extra_country_ranks.txt", "INJECT")],
                      [theirs("MoG_SPA_country_ranks.txt", "TRY_REPLACE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)
        self.assertEqual(res["ours_lost"], [])
        self.assertEqual(res["later_file"], OURS)
        self.assertFalse(res["order_depends_on_case"])

    def test_try_replace_after_an_inject_is_undetermined(self):
        # Among the INJECTs in file order, their later TRY_REPLACE wipes ours;
        # before them all, ours lands on it. Unprobed (try_phase).
        res = resolve([ours("a.txt", "INJECT")], [theirs("z.txt", "TRY_REPLACE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], UNDETERMINED)
        self.assertEqual(res["depends_on"], ["try_phase"])
        by_phase = {s["try_phase"]: s["verdict"] for s in res["verdict_by_scenario"]}
        self.assertEqual(by_phase, {"inject": OURS_WIPED, "early": BOTH_MERGE})

    def test_try_phase_known_gives_one_verdict(self):
        with mock.patch.object(emo, "KNOWN_TRY_PHASE", "inject"):
            res = resolve([ours("a.txt", "INJECT")], [theirs("z.txt", "TRY_REPLACE")],
                          IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], OURS_WIPED)

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

    def test_try_directives_with_no_entry_do_nothing(self):
        res = resolve([ours("a.txt", "TRY_INJECT")], [theirs("b.txt", "TRY_REPLACE")],
                      False, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_WIPED)
        self.assertEqual([s["effect"] for s in res["trace"]],
                         ["skipped_no_entry", "skipped_no_entry"])

    def test_or_create_comes_before_try_replace_in_an_earlier_file(self):
        # Our REPLACE_OR_CREATE creates the entry in its own phase, so their
        # TRY_REPLACE (a.txt sorts first) finds it and replaces it.
        res = resolve([ours("z.txt", "REPLACE_OR_CREATE")], [theirs("a.txt", "TRY_REPLACE")],
                      False, FIRST_WINS)
        self.assertEqual(res["verdict"], OURS_WIPED)
        self.assertEqual([s["effect"] for s in res["trace"]], ["created", "replaced"])

    def test_plain_inject_with_no_entry_errors(self):
        res = resolve([ours("a.txt", "INJECT")], [theirs("b.txt", "TRY_INJECT")],
                      False, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_WIPED)
        self.assertEqual([s["effect"] for s in res["trace"]], ["error_no_entry", "skipped_no_entry"])

    def test_or_create_beside_a_bare_definition_applies_up_front(self):
        # Realism AI's shape: vanilla defines the key, their REPLACE_OR_CREATE
        # (u…) meets our REPLACE (t…). Probe round 4: an *_OR_CREATE applies
        # before the INJECTs even when the key exists, so our REPLACE has the
        # last word.
        res = resolve([ours("te_vanilla_country_names.txt", "REPLACE")],
                      [theirs("usfp_dynamic_country_names.txt", "REPLACE_OR_CREATE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], THEIRS_WIPED)

    def test_their_or_create_lands_before_our_inject(self):
        # CMF's shape: their REPLACE_OR_CREATE of a vanilla key, our INJECT.
        res = resolve([ours("a_ours.txt", "INJECT")], [theirs("z_theirs.txt", "REPLACE_OR_CREATE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)

    def test_inject_finds_the_entry_a_later_or_create_makes(self):
        # Probe rounds 1 and 2: INJECT:x in a_ with REPLACE_OR_CREATE:x in b_
        # and no other definition logged no gamedatabase.h:395 line.
        res = resolve([ours("a.txt", "INJECT")], [theirs("b.txt", "REPLACE_OR_CREATE")],
                      False, FIRST_WINS)
        self.assertEqual(res["verdict"], BOTH_MERGE)
        self.assertEqual([s["effect"] for s in res["trace"]], ["created", "injected"])

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
        # after it folded either way; of two REPLACEs the later one's body is
        # the entry, under every load reading.
        res = resolve([ours("extra_country_ranks.txt", "REPLACE")],
                      [theirs("MoG_SPA_country_ranks.txt", "REPLACE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], ORDER_DEPENDS_ON_CASE)
        self.assertTrue(res["order_depends_on_case"])
        self.assertEqual(res["later_file"], "depends_on_case")
        self.assertEqual(res["depends_on"], ["file_order"])
        by_order = {s["file_order"]: s["verdict"] for s in res["verdict_by_scenario"]}
        self.assertEqual(by_order, {"ascii": THEIRS_WIPED, "lower_folded": OURS_WIPED,
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

    def test_or_create_phase_unknown_is_undetermined(self):
        # With the round-4 answer put back, the two readings disagree.
        res = resolve([ours("te_vanilla_country_names.txt", "REPLACE")],
                      [theirs("usfp_dynamic_country_names.txt", "REPLACE_OR_CREATE")],
                      IN_VANILLA, FIRST_WINS)
        self.assertEqual(res["verdict"], UNDETERMINED)
        self.assertIn("or_create_phase", res["depends_on"])
        rows = {s["or_create_phase"]: s["verdict"] for s in res["verdict_by_scenario"]
                if s.get("load_reading", "creations_first") == "creations_first"}
        self.assertEqual(rows, {"creation": THEIRS_WIPED, "own_family": OURS_WIPED})

    def test_two_deciding_unknowns_are_undetermined(self):
        # Theirs ships our file (without the key), and their REPLACE sorts
        # before ours only in ASCII order: both the playset and the file
        # order change the outcome.
        res = resolve([ours("extra.txt", "REPLACE")], [theirs("MoG.txt", "REPLACE")], IN_VANILLA,
                      FIRST_WINS, ours_files=["extra.txt"], theirs_files=["extra.txt", "MoG.txt"])
        self.assertEqual(res["verdict"], UNDETERMINED)
        self.assertEqual(res["depends_on"], ["file_order", "later_mod"])
        rows = {(s["file_order"], s["later_mod"]): s["verdict"] for s in res["verdict_by_scenario"]}
        self.assertEqual(rows[("ascii", "ours")], THEIRS_WIPED)
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

    def test_creations_first_applies_directives_in_phases(self):
        # Probe rounds 1-5: *_OR_CREATE, then the INJECTs (the TRY_ forms
        # among them, try_phase "inject"), then the plain REPLACEs, each phase
        # in file order, whatever order the files sort in.
        ops = [ours("a.txt", "REPLACE"), theirs("b.txt", "INJECT"), ours("c.txt", "TRY_REPLACE"),
               theirs("d.txt", "REPLACE_OR_CREATE"), ours("e.txt", "TRY_INJECT"),
               Op(VANILLA, "m.txt", 1)]
        ordered = emo.order_for_reading(ops, "ascii", "creations_first")
        self.assertEqual([o.path for o in ordered],
                         ["m.txt", "d.txt", "b.txt", "c.txt", "e.txt", "a.txt"])
        early = emo.order_for_reading(ops, "ascii", "creations_first", try_phase="early")
        self.assertEqual([o.path for o in early],
                         ["m.txt", "d.txt", "c.txt", "e.txt", "b.txt", "a.txt"])

    def test_own_family_or_create_phase(self):
        # With a bare definition there, each *_OR_CREATE joins its family's
        # phase; with none, the first one still creates the entry up front.
        ops = [ours("a.txt", "REPLACE"), theirs("b.txt", "REPLACE_OR_CREATE"),
               ours("c.txt", "INJECT_OR_CREATE"), theirs("d.txt", "INJECT")]
        with_bare = emo.order_for_reading([*ops, Op(VANILLA, "m.txt", 1)], "ascii",
                                          "creations_first", "own_family")
        self.assertEqual([o.path for o in with_bare], ["m.txt", "c.txt", "d.txt", "a.txt", "b.txt"])
        without = emo.order_for_reading(ops, "ascii", "creations_first", "own_family")
        self.assertEqual([o.path for o in without], ["b.txt", "c.txt", "d.txt", "a.txt"])
        creation = emo.order_for_reading([*ops, Op(VANILLA, "m.txt", 1)], "ascii",
                                         "creations_first", "creation")
        self.assertEqual([o.path for o in creation], ["m.txt", "b.txt", "c.txt", "d.txt", "a.txt"])

    def test_directive_phases_cover_each_directive_once(self):
        phases = emo.DIRECTIVE_PHASES
        self.assertEqual(sum(len(p) for p in phases), len(frozenset().union(*phases)))
        self.assertEqual(frozenset().union(*phases),
                         emo.INJECT_DIRECTIVES | emo.REPLACE_DIRECTIVES)

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
        self.assertEqual(emo.rule_for("scripted_triggers").bare_duplicate, FIRST_WINS)
        self.assertEqual(emo.rule_for("scripted_rules").bare_duplicate, FIRST_WINS)
        self.assertEqual(emo.rule_for("game_rules").bare_duplicate, UNKNOWN)
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
                         {BOTH_MERGE: 2, DEPENDS_ON_PLAYSET: 1, THEIRS_WIPED: 1})

    def test_key_collision_row(self):
        row = self.collision("law_a")
        # Our plain REPLACE applies after their TRY_REPLACE, though theirs sorts later.
        self.assertEqual(row["verdict"], THEIRS_WIPED)
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
        # Their TRY_REPLACE (MoG_…) sorts first, so our INJECT lands on it.
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
        # Their TRY_REPLACE applies before our plain REPLACE.
        self.assertEqual(row["trace"][1]["file"], "common/laws/zMoG_laws.txt")
        self.assertEqual(row["trace"][2]["file"], "common/laws/modified.txt")
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
