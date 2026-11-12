"""Tests for load_order_audit (#1191): where ModState's merge and the
engine's load order, as external_mod_overlap models it, give a key different
values. One fixture (a vanilla tree and a mod) is read both ways the audit
runs: from a snapshot built off the vanilla tree, as CI does, and from the
vanilla files themselves, as a machine with the game does."""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

import external_mod_overlap as emo
import load_order_audit as loa
import vanilla_parsed
from load_order_audit import (
    DIFFERENCE,
    IDENTICAL,
    MODEL_UNSURE,
    NOT_COMPARED,
    UNDETERMINED,
    VANILLA_ONLY,
)

TYPES = {
    "Modifiers": "static_modifiers",
    "Script Values": "script_values",
    "Laws": "laws",
    "Decrees": "decrees",
    "Messages": "messages",
}
MOD_ONLY = {"Scripted Effects": "scripted_effects"}


def _write(root, rel, text):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="\n") as fh:
        fh.write(text)


def build_fixture(tmp):
    """(install root, mod root). Vanilla's static modifiers sit in two files,
    `10_a.txt` and `30_c.txt`, so a mod file can sort before both, between
    them or after both."""
    install, mod = os.path.join(tmp, "install"), os.path.join(tmp, "mod")
    v = "game/common/"
    _write(install, v + "static_modifiers/10_a.txt",
           "v_first = { a = 1 }\nv_last = { a = 1 }\nv_mid = { a = 1 }\n"
           "v_rep = { a = 1 }\nv_try = { a = 1 }\nv_two = { a = 1 }\n"
           "v_own = { a = 1 }\nv_inject = { a = 1 }\n")
    _write(install, v + "static_modifiers/30_c.txt",
           "v_mid_late = { a = 1 }\nv_own = { a = 2 }\n")
    _write(install, v + "script_values/50_values.txt", "sv_before = 1\nsv_after = 1\n")
    _write(install, v + "decrees/00_decrees.txt",
           "decree_kept = { cost = 1 }\ndecree_gone = { cost = 1 }\n")
    _write(install, v + "scripted_effects/00_effects.txt", "v_effect = { add_treasury = 1 }\n")
    # ModState skips a type whose vanilla folder is missing, the mod's files included.
    _write(install, v + "laws/00_laws.txt", "law_v = { group = x }\n")
    _write(install, v + "messages/00_messages.txt", "msg_v = { type = v }\n")

    c = "common/"
    # A mod bare copy of a vanilla key, its file sorting first, between, last.
    _write(mod, c + "static_modifiers/00_first.txt", "v_first = { a = 2 }\n")
    _write(mod, c + "static_modifiers/20_mid.txt", "v_mid = { a = 2 }\nv_mid_late = { a = 2 }\n")
    _write(mod, c + "static_modifiers/zz_last.txt", "v_last = { a = 2 }\n")
    _write(mod, c + "static_modifiers/a_te.txt",
           "m_dup = { a = 1 }\n"                      # bare, again in b_te.txt
           "m_same = { a = 1 }\n"                     # the same body in b_te.txt
           "m_rep = { a = 1 }\n"                      # REPLACEd from b_te.txt
           "INJECT:m_nowhere = { a = 1 }\n"           # nothing defines it
           "REPLACE:v_rep = { b = 1 }\n"              # an INJECT follows in b_te.txt
           "INJECT:m_late = { b = 1 }\n"              # its bare target sorts later
           "INJECT:v_try = { b = 1 }\n"               # a TRY_REPLACE follows
           "REPLACE:v_two = { x = 1 }\n"              # a second REPLACE and an INJECT follow
           "INJECT:v_inject = { b = 1 }\n"
           "m_twice = { a = 1 }\nm_twice = { a = 2 }\n"
           "INJECT:m_self = { b = 1 }\nm_self = { a = 1 }\n")   # an INJECT above its own target
    _write(mod, c + "static_modifiers/b_te.txt",
           "m_dup = { a = 2 }\nm_same = { a = 1 }\nREPLACE:m_rep = { a = 2 }\n"
           "INJECT:v_rep = { c = 1 }\nm_late = { a = 1 }\nTRY_REPLACE:v_try = { c = 1 }\n"
           "REPLACE:v_two = { x = 2 }\n")
    _write(mod, c + "static_modifiers/c_te.txt", "INJECT:v_two = { y = 1 }\n")
    # Script values: the copy read last wins.
    _write(mod, c + "script_values/00_te.txt", "sv_before = 5\nsv_dup = 1\n")
    _write(mod, c + "script_values/zz_te.txt", "sv_after = 5\nsv_dup = 2\n")
    # laws: first-wins on the digest's word, not probed.
    _write(mod, c + "laws/a_te.txt", "law_dup = { group = x }\n")
    _write(mod, c + "laws/b_te.txt", "law_dup = { group = y }\n")
    # messages: no rule recorded.
    _write(mod, c + "messages/a_te.txt", "msg_dup = { type = a }\n")
    _write(mod, c + "messages/b_te.txt", "msg_dup = { type = b }\n")
    # A mod file at a vanilla file's path replaces it whole.
    _write(mod, c + "decrees/00_decrees.txt", "decree_kept = { cost = 2 }\n")
    # A mod copy of a vanilla scripted effect: ModState holds no vanilla there.
    _write(mod, c + "scripted_effects/zz_te.txt",
           "v_effect = { add_treasury = 2 }\nte_effect = { add_treasury = 3 }\n")
    _write(mod, c + "on_actions/te.txt", "on_monthly_pulse = { events = { te.1 } }\n")
    _write(mod, c + "game_rules/te.txt", "te_rule = { }\n")
    return install, mod


def game_state(install, mod):
    from mod_state import ModState
    game_common = os.path.join(install, "game", "common")
    return ModState({et: os.path.join(game_common, d) for et, d in TYPES.items()},
                    {et: os.path.join(mod, "common", d) for et, d in {**TYPES, **MOD_ONLY}.items()})


class _Fixture(unittest.TestCase):
    """Builds the fixture once and runs the audit in both modes."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.install, cls.mod = build_fixture(cls._tmp.name)
        snap = os.path.join(cls.mod, "vanilla_parsed")
        vanilla_parsed.build(cls.install, snap, game_version="test")
        cls.snapshot = loa.audit(
            loa.load_state(cls.mod), cls.mod,
            emo.VanillaIndex(game_common=None, snapshot_dir=snap))
        game_common = os.path.join(cls.install, "game", "common")
        cls.game = loa.audit(
            game_state(cls.install, cls.mod), cls.mod,
            emo.VanillaIndex(game_common=game_common, snapshot_dir=None))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def row(self, result, key):
        rows = [r for r in result.rows if r.key == key]
        self.assertLessEqual(len(rows), 1, key)
        return rows[0] if rows else None

    def both(self, key):
        return self.row(self.snapshot, key), self.row(self.game, key)

    def entries(self, row):
        return [d["entry"] for d in row.decided_by]


class BareCopyOfVanillaTests(_Fixture):
    def test_modes(self):
        self.assertEqual(self.snapshot.mode, loa.SNAPSHOT_MODE)
        self.assertEqual(self.game.mode, loa.GAME_MODE)

    def test_mod_file_sorting_before_every_vanilla_file_agrees(self):
        # The engine keeps the mod's copy (read first), as ModState does.
        for row in self.both("v_first"):
            self.assertIsNone(row)

    def test_mod_file_sorting_after_every_vanilla_file_is_a_difference(self):
        for row in self.both("v_last"):
            self.assertEqual(row.kind, DIFFERENCE)
            self.assertIn("zz_last.txt", row.mod_state)
            self.assertEqual(self.entries(row), ["bare_duplicate"])
            self.assertEqual(row.decided_by[0]["status"], "probed")
            self.assertEqual(row.decided_by[0]["facts"], "fact 3")
            self.assertEqual(row.fields, ["a"])
        # Offline the engine's side is "vanilla's entry"; with the game, its file.
        snap, game = self.both("v_last")
        self.assertEqual(snap.engine, "vanilla's entry")
        self.assertEqual(game.engine,
                         "the definition at `game/common/static_modifiers/10_a.txt:2`")
        self.assertIn("dropped, the key already exists", game.load[1])

    def test_mod_file_between_vanilla_files_is_undetermined_offline(self):
        snap, game = self.both("v_mid")
        self.assertEqual(snap.kind, UNDETERMINED)
        self.assertEqual([c["agrees"] for c in snap.cases], [False, True])
        self.assertIn("sorts before `20_mid.txt` (1 of vanilla's 2 files)", snap.cases[0]["when"])
        self.assertIn("sorts after `20_mid.txt`", snap.cases[1]["when"])
        # With the game files vanilla's copy is in 10_a.txt, read first.
        self.assertEqual(game.kind, DIFFERENCE)
        self.assertEqual(self.entries(game), ["bare_duplicate"])

    def test_the_game_files_clear_the_other_undetermined_key(self):
        snap, game = self.both("v_mid_late")
        self.assertEqual(snap.kind, UNDETERMINED)
        self.assertIsNone(game)       # vanilla's copy is in 30_c.txt, read after the mod's

    def test_nothing_is_undetermined_with_the_game_files(self):
        self.assertEqual(self.game.of(UNDETERMINED), [])
        self.assertEqual(sorted(r.key for r in self.snapshot.of(UNDETERMINED)),
                         ["v_mid", "v_mid_late"])


class ModFilesTests(_Fixture):
    def test_bare_duplicate_in_two_mod_files_keeps_the_first(self):
        for row in self.both("m_dup"):
            self.assertEqual(row.kind, DIFFERENCE)
            self.assertEqual(row.mod_state,
                             "the definition at `common/static_modifiers/b_te.txt:1`")
            self.assertEqual(row.engine,
                             "the definition at `common/static_modifiers/a_te.txt:1`")
            self.assertEqual(self.entries(row), ["bare_duplicate"])

    def test_identical_copies_are_no_difference(self):
        for row in self.both("m_same"):
            self.assertEqual(row.kind, IDENTICAL)

    def test_replace_after_a_bare_definition_agrees(self):
        for row in self.both("m_rep"):
            self.assertIsNone(row)

    def test_inject_into_a_vanilla_key_agrees(self):
        for row in self.both("v_inject"):
            self.assertIsNone(row)

    def test_inject_into_a_missing_key(self):
        # ModState creates the entry from the INJECT's body; the engine has none.
        for row in self.both("m_nowhere"):
            self.assertEqual(row.kind, DIFFERENCE)
            self.assertEqual(row.engine, "no entry")
            self.assertIn("a_te.txt", row.mod_state)
            self.assertEqual(self.entries(row), ["directives"])
            self.assertEqual(row.decided_by[0]["status"], "documented")
            self.assertIn("no entry to act on", row.load[0])

    def test_inject_sorting_after_a_replace_is_lost(self):
        # Fact 8: the REPLACE's body is the final entry; ModState adds the INJECT to it.
        for row in self.both("v_rep"):
            self.assertEqual(row.kind, DIFFERENCE)
            self.assertEqual(self.entries(row), ["directive_phases"])
            self.assertEqual(row.decided_by[0]["facts"], "facts 7-10")
            self.assertEqual(row.mod_state, "a merge of several definitions")
            self.assertIn("a_te.txt", row.engine)
            self.assertEqual(row.fields, ["c"])

    def test_inject_sorting_before_its_bare_target_applies(self):
        # Fact 4: directives wait for every bare definition; ModState's later
        # bare copy overwrites what the INJECT made.
        for row in self.both("m_late"):
            self.assertEqual(row.kind, DIFFERENCE)
            self.assertEqual(self.entries(row), ["directives_deferred"])
            self.assertIn("with the INJECT at", row.engine)

    def test_a_key_one_file_repeats_is_not_compared(self):
        for row in self.both("m_twice"):
            self.assertEqual(row.kind, NOT_COMPARED)
            self.assertIn("defines it 2 times", row.note)

    def test_a_lone_bare_definition_is_not_replayed(self):
        for result in (self.snapshot, self.game):
            self.assertIsNone(self.row(result, "te_effect"))
        self.assertLess(self.snapshot.keys_checked, self.snapshot.keys_defined)


class FolderRuleTests(_Fixture):
    def test_script_values_keep_the_last_copy_as_modstate_does(self):
        for row in self.both("sv_dup"):
            self.assertIsNone(row)
        for row in self.both("sv_after"):
            self.assertIsNone(row)

    def test_script_value_read_before_vanilla_loses_to_it(self):
        # Vanilla has one file there, so the snapshot decides it too.
        for row in self.both("sv_before"):
            self.assertEqual(row.kind, DIFFERENCE)
            self.assertEqual(self.entries(row), ["bare_duplicate_script_values", "interleaving"])
            self.assertEqual([d["facts"] for d in row.decided_by], ["fact 5", "fact 2"])
            self.assertIn("00_te.txt", row.mod_state)

    def test_a_documented_folder_is_a_difference_that_says_so(self):
        for row in self.both("law_dup"):
            self.assertEqual(row.kind, DIFFERENCE)
            self.assertIn("b_te.txt", row.mod_state)
            self.assertEqual(self.entries(row), ["bare_duplicate"])
            self.assertEqual(row.decided_by[0]["status"], "documented")

    def test_a_folder_with_no_rule_is_model_unsure(self):
        for row in self.both("msg_dup"):
            self.assertEqual(row.kind, MODEL_UNSURE)
            self.assertEqual(row.depends_on, ["bare_duplicate"])
            self.assertEqual({c["when"]: c["agrees"] for c in row.cases},
                             {"bare_duplicate is first_wins": False,
                              "bare_duplicate is last_wins": True})

    def test_a_try_form_is_model_unsure(self):
        # Fact 10's open question: among the INJECTs in file order, or before them.
        for row in self.both("v_try"):
            self.assertEqual(row.kind, MODEL_UNSURE)
            self.assertEqual(row.depends_on, ["try_phase"])
            self.assertEqual(len(row.cases), 2)

    def test_two_plain_replaces_rest_on_an_unprobed_order(self):
        for row in self.both("v_two"):
            self.assertEqual(row.kind, MODEL_UNSURE)
            self.assertEqual(self.entries(row), ["directive_phases"])
            self.assertIn("not read in game", row.note)

    def test_an_inject_in_its_target_s_own_file_is_unprobed(self):
        # ModState's later bare copy overwrites the INJECT; the model applies
        # the INJECT after it, which nobody has read in game for one file.
        for row in self.both("m_self"):
            self.assertEqual(row.kind, MODEL_UNSURE)
            self.assertEqual(self.entries(row), ["directives_deferred"])
            self.assertIn("same file", row.note)

    def test_a_settled_unknown_becomes_a_difference(self):
        # An in-game answer is one setting; the audit follows it.
        snap = os.path.join(self.mod, "vanilla_parsed")
        with mock.patch.object(emo, "KNOWN_TRY_PHASE", "inject"):
            result = loa.audit(loa.load_state(self.mod), self.mod,
                               emo.VanillaIndex(game_common=None, snapshot_dir=snap))
        self.assertIsNone(self.row(result, "v_try"))
        with mock.patch.object(emo, "KNOWN_TRY_PHASE", "early"):
            result = loa.audit(loa.load_state(self.mod), self.mod,
                               emo.VanillaIndex(game_common=None, snapshot_dir=snap))
        self.assertEqual(self.row(result, "v_try").kind, DIFFERENCE)


class GameFilesTests(_Fixture):
    def test_vanilla_key_in_a_replaced_file(self):
        # The mod's 00_decrees.txt replaces vanilla's and leaves decree_gone out.
        snap, game = self.both("decree_gone")
        self.assertIsNone(snap)       # the snapshot can't list a vanilla file's keys
        self.assertEqual(self.snapshot.replaced_vanilla_files, ["common/decrees/00_decrees.txt"])
        self.assertEqual(game.kind, DIFFERENCE)
        self.assertEqual(game.engine, "no entry")
        self.assertEqual(self.entries(game), ["same_path"])
        self.assertEqual(game.mod_state,
                         "the definition at `game/common/decrees/00_decrees.txt:2`")

    def test_the_replacing_file_s_own_copy_agrees(self):
        for row in self.both("decree_kept"):
            self.assertIsNone(row)

    def test_mod_copy_of_a_vanilla_scripted_effect(self):
        snap, game = self.both("v_effect")
        self.assertIsNone(snap)
        self.assertEqual(self.snapshot.no_vanilla, ["common/scripted_effects"])
        self.assertEqual(self.game.no_vanilla, [])
        self.assertEqual(game.kind, DIFFERENCE)
        self.assertIn("00_effects.txt", game.engine)
        self.assertIn("ModState holds no vanilla for this type", game.note)

    def test_vanilla_s_own_repeated_key(self):
        snap, game = self.both("v_own")
        self.assertIsNone(snap)
        self.assertEqual(game.kind, VANILLA_ONLY)
        self.assertIn("30_c.txt", game.mod_state)
        self.assertIn("10_a.txt", game.engine)
        self.assertEqual(self.snapshot.of(VANILLA_ONLY), [])


class ReportTests(_Fixture):
    def test_summary_counts(self):
        s = self.snapshot.summary()
        self.assertEqual(s["mode"], loa.SNAPSHOT_MODE)
        self.assertEqual(s["unreviewed"], len(self.snapshot.of(DIFFERENCE)))
        self.assertEqual(
            sorted(r.key for r in self.snapshot.of(DIFFERENCE)),
            ["law_dup", "m_dup", "m_late", "m_nowhere", "sv_before", "v_last", "v_rep"])
        self.assertEqual(s["undetermined"], 2)
        self.assertEqual(s["model_unsure"], 4)
        self.assertEqual(s["not_compared"], 1)
        self.assertEqual(s["identical"], 1)
        self.assertEqual(self.game.summary()["vanilla_only"], 1)

    def test_rows_are_sorted(self):
        for result in (self.snapshot, self.game):
            keys = [(loa.KINDS.index(r.kind), r.db, r.key) for r in result.rows]
            self.assertEqual(keys, sorted(keys))

    def test_report_names_its_mode_and_sections(self):
        snap, game = loa.render_report(self.snapshot), loa.render_report(self.game)
        self.assertIn("**Mode: snapshot.**", snap)
        self.assertIn("**Mode: game files.**", game)
        self.assertIn("_Not checked: needs the game files._", snap)
        for text in (snap, game):
            for title in ("## Differences", "## Model unsure",
                          "## Undetermined without the game files", "## Not compared",
                          "## Vanilla's own files", "## Identical bare copies", "## Not covered"):
                self.assertIn(title, text)
        self.assertIn("### `common/static_modifiers` `v_last`", snap)
        self.assertIn("- Decided by: `bare_duplicate` (probed, fact 3)", snap)
        self.assertIn("- Depends on: `try_phase`", snap)
        self.assertIn("`common/on_actions`", snap)
        self.assertIn("Folders ModState doesn't parse: `common/game_rules`", snap)

    def test_undetermined_keys_group_without_line_numbers(self):
        text = loa.render_report(self.snapshot)
        block = text.split("## Undetermined without the game files")[1].split("## Not compared")[0]
        self.assertIn("### `common/static_modifiers`: 2 keys", block)
        self.assertIn("- Keys: `v_mid`, `v_mid_late`", block)
        self.assertNotRegex(block, r"\.txt:\d")
        self.assertIn("**differs**", block)

    def test_report_is_deterministic(self):
        snap = os.path.join(self.mod, "vanilla_parsed")
        again = loa.audit(loa.load_state(self.mod), self.mod,
                          emo.VanillaIndex(game_common=None, snapshot_dir=snap))
        self.assertEqual(loa.render_report(again), loa.render_report(self.snapshot))

    def test_every_citation_names_a_model_entry(self):
        for result in (self.snapshot, self.game):
            for row in result.rows:
                for d in row.decided_by:
                    self.assertIn(d["entry"], emo.LOAD_ORDER_MODEL)
                    self.assertIn(d["status"], loa._STATUS_ORDER)

    def test_strict_exit_code(self):
        # conftest's dummy game path: main() runs from the mod's own snapshot.
        with mock.patch("builtins.print"):
            self.assertEqual(loa.main(["--strict"], mod_path=self.mod), 1)
            self.assertEqual(loa.main([], mod_path=self.mod), 0)

    def test_strict_passes_without_differences(self):
        with tempfile.TemporaryDirectory() as tmp:
            install, mod = os.path.join(tmp, "install"), os.path.join(tmp, "mod")
            _write(install, "game/common/static_modifiers/10_a.txt", "v_mid = { a = 1 }\n")
            _write(install, "game/common/static_modifiers/30_c.txt", "v_other = { a = 1 }\n")
            _write(mod, "common/static_modifiers/20_mid.txt",
                   "v_mid = { a = 2 }\nINJECT:v_other = { b = 1 }\n")
            vanilla_parsed.build(install, os.path.join(mod, "vanilla_parsed"), game_version="test")
            result = loa.audit(mod_path=mod)
            # Undetermined is neither clean nor a finding: listed, and not a failure.
            self.assertEqual([r.kind for r in result.rows], [UNDETERMINED])
            with mock.patch("builtins.print"):
                self.assertEqual(loa.main(["--strict"], mod_path=mod), 0)

    def test_regenerate_writes_the_report(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("path_constants.mod_path", tmp, create=True), \
                mock.patch.object(loa, "audit", return_value=self.snapshot):
            summary = loa.regenerate(object())
            with open(os.path.join(tmp, loa.REPORT_PATH), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), loa.render_report(self.snapshot))
        self.assertEqual(summary["unreviewed"], 7)


class VanillaSourceTests(unittest.TestCase):
    """Which vanilla the engine side reads: it must be the one ModState holds."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.install, self.mod = build_fixture(tmp.name)
        self.snap = os.path.join(self.mod, "vanilla_parsed")
        vanilla_parsed.build(self.install, self.snap, game_version="test")

    def test_no_game_install_reads_the_snapshot(self):
        index = loa.default_vanilla(self.mod)     # conftest's dummy game path
        self.assertIsNone(index.game_common)
        self.assertEqual(index.snapshot_dir, self.snap)

    def test_game_files_serve_when_the_snapshot_matches_them(self):
        with mock.patch("path_constants.base_game_path", self.install, create=True):
            index = loa.default_vanilla(self.mod)
            self.assertEqual(index.game_common, os.path.join(self.install, "game", "common"))
            result = loa.audit(mod_path=self.mod)
        self.assertEqual(result.mode, loa.GAME_MODE)
        self.assertEqual(result.of(UNDETERMINED), [])

    def test_a_stale_snapshot_keeps_the_audit_on_the_snapshot(self):
        # load_state() reads the snapshot; newer game files would be another vanilla.
        _write(self.install, "game/common/static_modifiers/10_a.txt", "v_first = { a = 9 }\n")
        with mock.patch("path_constants.base_game_path", self.install, create=True):
            self.assertIsNone(loa.default_vanilla(self.mod).game_common)

    def test_a_reload_reads_the_server_s_vanilla(self):
        game_common = os.path.join(self.install, "game", "common")
        served = emo.VanillaIndex(game_common=game_common, snapshot_dir=self.snap)
        server = mock.Mock(_overlap_vanilla_index=lambda: served)
        with mock.patch.dict("sys.modules", {"__main__": server}):
            index = loa._server_vanilla()
        self.assertEqual((index.game_common, index.snapshot_dir), (game_common, self.snap))
        self.assertIs(index.scan_cache, loa._SCAN_CACHE)
        with mock.patch.dict("sys.modules", {"__main__": object()}):
            self.assertIsNone(loa._server_vanilla())

    def test_regenerate_passes_the_server_s_vanilla(self):
        served = emo.VanillaIndex(game_common=None, snapshot_dir=self.snap)
        server = mock.Mock(_overlap_vanilla_index=lambda: served)
        ms = loa.load_state(self.mod)
        with mock.patch.dict("sys.modules", {"__main__": server}), \
                mock.patch("path_constants.mod_path", self.mod, create=True):
            summary = loa.regenerate(ms)
        self.assertEqual(summary["mode"], loa.SNAPSHOT_MODE)
        self.assertEqual(summary["undetermined"], 2)
        self.assertTrue(os.path.isfile(os.path.join(self.mod, loa.REPORT_PATH)))

    def test_an_unchanged_file_is_scanned_once(self):
        index = emo.VanillaIndex(game_common=None, snapshot_dir=self.snap)
        ms = loa.load_state(self.mod)
        loa.audit(ms, self.mod, index)
        with mock.patch.object(emo, "scan_script", wraps=emo.scan_script) as scan:
            loa.audit(ms, self.mod, index)
            self.assertEqual(scan.call_count, 0)
            # An edit is seen: the file's size changed.
            _write(self.mod, "common/laws/b_te.txt", "law_dup = { group = y }\nlaw_new = { }\n")
            loa.audit(ms, self.mod, index)
            self.assertEqual(scan.call_count, 1)


class ModelStatusTests(unittest.TestCase):
    def test_bare_rule_status(self):
        self.assertEqual(emo.bare_rule_status("static_modifiers"), "probed")
        self.assertEqual(emo.bare_rule_status("script_values"), "probed")
        self.assertEqual(emo.bare_rule_status("laws"), "documented")
        self.assertEqual(emo.bare_rule_status("messages"), "unknown")

    def test_probed_folders_have_a_rule(self):
        self.assertLessEqual(emo.BARE_DUPLICATE_PROBED, set(emo.BARE_DUPLICATE_RULES))

    def test_unknown_names_map_to_model_entries(self):
        self.assertEqual(set(loa._UNKNOWN_ENTRY), set(loa._MODEL_UNKNOWNS))
        for entry in loa._UNKNOWN_ENTRY.values():
            self.assertIn(entry, emo.LOAD_ORDER_MODEL)

    def test_position_text(self):
        self.assertEqual(
            loa._position_text("05.txt", ["10.txt", "20.txt"], 3, 1),
            "vanilla defines it in a file that sorts before `10.txt` (1 of vanilla's 3 files)")
        self.assertIn("between `10.txt` and `20.txt`",
                      loa._position_text("15.txt", ["10.txt", "20.txt"], 3, 1))
        self.assertIn("after `20.txt`", loa._position_text("B.txt", ["10.txt", "20.txt"], 3, 1))


if __name__ == "__main__":
    unittest.main()
