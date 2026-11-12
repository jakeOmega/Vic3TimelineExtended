"""Tests for scripts/generators/fold_vanilla_loc_accessors.py (#348).

The fold used to add every accessor vanilla's loc flagged as `"value"`, the
object-returning ones included, which cleared each flag by switching the check
off for the rest of the chain. It now folds the terminals and reports the rest.

Run: python3 -m pytest test_fold_vanilla_loc_accessors.py
"""
import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

import localization_accessor_audit as audit_mod
from scripts.generators import fold_vanilla_loc_accessors as fold

HAND = {
    "country": {"GetName": "value", "GetCapital": "state", "GetRuler": "value"},
    "state": {"GetName": "value"},
}
EXTRAS = {
    "country": {"GetRank": "value", "GetCapital": "value", "GetOldThing": "value",
                "GetBloc": "value"},
    "state": {"GetPopulation": "value"},
}
LOC = {
    # Terminal gaps: nothing after them anywhere.
    "ui.1.d": "[COUNTRY.GetFlag] [COUNTRY.GetCapital.GetArea|D]",
    # A gap vanilla chains further through, and once more at the end of a chain.
    "ui.2.d": "[COUNTRY.GetHeir.GetFullName] [COUNTRY.GetHeir.GetAge]",
    "ui.3.d": "[COUNTRY.GetHeir]",
    # A folded value vanilla chains further through, and a hand-typed one.
    "ui.4.d": "[COUNTRY.GetBloc.GetLeader.GetName] [COUNTRY.GetRuler.GetFullName]",
    # A typo no accessor can explain, and a flag listed as vanilla's mistake.
    "ui.5.d": "[COUNTRY.GetCapital .GetName]",
    "ui.6.d": "[COUNTRY.GetDeadThing]",
    "ui.7.d": "[COUNTRY.GetName] [COUNTRY.GetRank] [STATE.GetPopulation]",
}
KNOWN = {("ui.6.d", "COUNTRY.GetDeadThing"): "dead vanilla text"}


def plan(loc=None, hand=None, extras=None, **kwargs):
    kwargs.setdefault("known_flags", KNOWN)
    return fold.plan_fold(audit_mod.lines_from_dict(LOC if loc is None else loc),
                          HAND if hand is None else hand,
                          EXTRAS if extras is None else extras, **kwargs)


class PlanTests(unittest.TestCase):
    def test_a_terminal_gap_is_folded_as_value(self):
        p = plan()
        self.assertEqual([g.name for g in p.terminal], ["country.GetFlag", "state.GetArea"])
        self.assertEqual(p.extras["country"]["GetFlag"], "value")
        self.assertEqual(p.extras["state"]["GetArea"], "value")

    def test_a_gap_chained_further_is_reported_and_not_folded(self):
        p = plan()
        self.assertEqual([g.name for g in p.chained], ["country.GetHeir"])
        gap = p.chained[0]
        self.assertEqual(gap.continuations, ["GetFullName", "GetAge"])
        self.assertEqual((gap.key, gap.chain), ("ui.2.d", "COUNTRY.GetHeir.GetFullName"))
        # One chain past it is enough, even though `ui.3.d` ends on it.
        self.assertNotIn("GetHeir", p.extras["country"])
        self.assertTrue(p.needs_hand_typing)

    def test_an_extras_entry_the_hand_table_defines_is_dropped(self):
        p = plan()
        self.assertEqual(p.shadowed, ["country.GetCapital"])
        self.assertNotIn("GetCapital", p.extras["country"])
        self.assertEqual(p.extras["country"]["GetRank"], "value")  # the rest stays
        self.assertTrue(p.changed)

    def test_drop_removes_a_named_entry(self):
        p = plan(drop=("country.GetOldThing",))
        self.assertEqual(p.dropped, ["country.GetOldThing"])
        self.assertNotIn("GetOldThing", p.extras["country"])
        self.assertIn("GetOldThing", plan().extras["country"])

    def test_drop_refuses_a_name_the_extras_do_not_hold(self):
        with self.assertRaises(SystemExit) as caught:
            plan(drop=("country.GetNoSuch",))
        self.assertIn("country.GetNoSuch", str(caught.exception))

    def test_a_known_vanilla_flag_is_left_alone(self):
        p = plan()
        self.assertEqual(p.known, 1)
        self.assertNotIn("GetDeadThing", p.extras["country"])
        self.assertNotIn("country.GetDeadThing", [g.name for g in p.terminal + p.chained])
        # Unlisted, it is a gap like any other.
        self.assertIn("country.GetDeadThing", [g.name for g in plan(known_flags={}).terminal])

    def test_a_typo_is_residual(self):
        p = plan()
        self.assertEqual([(f.key, f.chain) for f in p.residual],
                         [("ui.5.d", "COUNTRY.GetCapital .GetName")])
        self.assertNotIn("GetCapital ", p.extras["country"])

    def test_a_folded_value_chained_further_is_listed_blind(self):
        p = plan()
        # The hand-typed `country.GetRuler` is not the fold's to list.
        self.assertEqual([b.name for b in p.blind], ["country.GetBloc"])
        self.assertEqual(p.blind[0].continuations, {"GetLeader": 1})
        self.assertEqual([b.name for b in p.untyped_blind], ["country.GetBloc"])

    def test_a_clean_catalog_changes_nothing(self):
        p = plan(loc={"ui.1.d": "[COUNTRY.GetName] [COUNTRY.GetCapital.GetName] [COUNTRY.GetRank]"},
                 extras={"country": {"GetRank": "value"}})
        self.assertFalse(p.changed)
        self.assertFalse(p.needs_hand_typing)
        self.assertEqual((p.flags, p.terminal, p.chained, p.blind), (0, [], [], []))
        self.assertEqual(p.extras, {"country": {"GetRank": "value"}})

    def test_typing_the_chained_gap_surfaces_what_sits_behind_it(self):
        hand = {**HAND, "country": {**HAND["country"], "GetHeir": "character"}, "character": {}}
        p = plan(hand=hand)
        self.assertEqual(p.chained, [])
        self.assertEqual([g.name for g in p.terminal],
                         ["character.GetAge", "character.GetFullName",
                          "country.GetFlag", "state.GetArea"])

    def test_the_inputs_are_not_modified(self):
        before = {typ: dict(accessors) for typ, accessors in EXTRAS.items()}
        plan()
        self.assertEqual(EXTRAS, before)


class RenderTests(unittest.TestCase):
    def test_extras_round_trip_sorted(self):
        text = fold.render_extras({"state": {"GetB": "value", "GetA": "value"},
                                   "country": {"GetZ": "value"}, "empty": {}})
        namespace = {}
        exec(text, namespace)
        self.assertEqual(namespace["VANILLA_EXTRACTED_ACCESSORS"],
                         {"country": {"GetZ": "value"}, "state": {"GetA": "value", "GetB": "value"}})
        self.assertLess(text.index('"country"'), text.index('"state"'))
        self.assertLess(text.index('"GetA"'), text.index('"GetB"'))
        self.assertTrue(text.startswith("# Auto-extracted from vanilla loc. Do not hand-edit"))
        self.assertTrue(text.endswith("}\n"))

    def test_the_report_splits_terminal_from_chained(self):
        text = fold.render_plan(plan(), "a fixture", None, dry_run=True)
        self.assertIn('Terminal, would fold as "value": 2', text)
        self.assertIn("  + country.GetFlag", text)
        self.assertIn("Chained further in vanilla, NOT folded: 1", text)
        self.assertIn("  ! country.GetHeir, then GetFullName, GetAge   "
                      "e.g. ui.2.d: [COUNTRY.GetHeir.GetFullName]", text)
        self.assertIn("Dropped from the extras: 1 the hand table defines, 0 by --drop", text)
        self.assertIn("  - country.GetCapital", text)
        self.assertIn("ui.5.d | COUNTRY.GetCapital .GetName", text)
        self.assertIn("Folded accessors vanilla chains further through: 1 (1 to be typed", text)
        self.assertIn("  ! country.GetBloc, then GetLeader", text)
        self.assertIn("vanilla loc: a fixture", text)
        self.assertIn("vanilla flags: 7 (1 known vanilla mistakes, 1 unexplained)", text)
        self.assertIn('Terminal, folded as "value": 2',
                      fold.render_plan(plan(), "a fixture", None, dry_run=False))


DATA_TYPES = """\
Country.GetHeir
Definition type: Promote
Return type: Character

-----------------------

Country.GetHeir
Definition type: Function
Return type: [unregistered]

-----------------------

Country.GetFlag
Definition type: Function
Return type: CString

-----------------------

Scope.GetInterestGroup
Definition type: Promote
Return type: InterestGroup

-----------------------

AIAttitude.GetName( Arg0 )
Definition type: Function
Return type: CString

-----------------------

GetPlayer
Definition type: Global promote
Return type: Country
"""


class DataTypesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        with open(os.path.join(cls._tmp.name, "data_types_uncategorized.txt"), "w",
                  encoding="utf-8") as f:
            f.write(DATA_TYPES)
        cls.types = fold.load_data_types(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_dump_is_parsed_by_type(self):
        self.assertEqual(self.types["Country"]["GetHeir"],
                         [("Promote", "Character"), ("Function", "[unregistered]")])
        self.assertEqual(self.types["AIAttitude"]["GetName"], [("Function", "CString")])
        self.assertNotIn("GetPlayer", self.types)  # a global, not an accessor on a type

    def test_no_dump_means_no_hint(self):
        self.assertIsNone(fold.load_data_types(None))
        with tempfile.TemporaryDirectory() as empty:
            self.assertIsNone(fold.load_data_types(empty))
        self.assertEqual(fold.engine_says(None, "country", "GetHeir"), "")

    def test_a_promote_and_a_function_are_told_apart(self):
        self.assertEqual(fold.engine_says(self.types, "country", "GetHeir"),
                         "data types: Country.GetHeir is a promote to Character")
        self.assertEqual(fold.engine_says(self.types, "country", "GetFlag"),
                         "data types: Country.GetFlag is a function returning CString")

    def test_country_also_stands_for_a_script_scope(self):
        self.assertEqual(fold.engine_says(self.types, "country", "GetInterestGroup"),
                         "data types: Scope.GetInterestGroup is a promote to InterestGroup")

    def test_a_snake_case_type_finds_its_engine_name(self):
        self.assertEqual(fold.engine_says(self.types, "ai_attitude", "GetName"),
                         "data types: AIAttitude.GetName is a function returning CString")

    def test_an_accessor_the_engine_lacks_is_said_so(self):
        self.assertEqual(
            fold.engine_says(self.types, "country", "GetNoSuch"),
            "data types: no such accessor (Country, Scope), so vanilla's text may be dead")

    def test_the_report_carries_the_hint(self):
        text = fold.render_plan(plan(), "a fixture", self.types, dry_run=True)
        self.assertIn("  ! country.GetHeir, then GetFullName, GetAge   "
                      "e.g. ui.2.d: [COUNTRY.GetHeir.GetFullName]   "
                      "[data types: Country.GetHeir is a promote to Character]", text)
        self.assertIn("  + country.GetFlag   "
                      "[data types: Country.GetFlag is a function returning CString]", text)


class CommittedExtrasTests(unittest.TestCase):
    """The committed extras against the committed snapshot: what CI can check
    of the fold without a game install."""

    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = fold.main(list(argv))
        return code, out.getvalue()

    def test_the_fold_of_the_snapshot_has_nothing_left_to_do(self):
        lines, source = fold.load_vanilla_lines("snapshot")
        self.assertIn("vanilla_parsed/ snapshot", source)
        p = fold.plan_fold(lines, audit_mod.HAND_TYPED_ACCESSORS,
                           audit_mod.VANILLA_EXTRACTED_ACCESSORS,
                           engine_docs_dir=str(fold.ENGINE_DOCS))
        self.assertEqual(
            ([g.name for g in p.terminal], [g.name for g in p.chained], p.shadowed,
             [(f.key, f.chain) for f in p.residual], [b.name for b in p.untyped_blind]),
            ([], [], [], [], []),
            "localization_accessor_vanilla_extras.py is behind vanilla_parsed/: run "
            "python3 scripts/generators/fold_vanilla_loc_accessors.py and follow its report")
        self.assertEqual(p.extras, audit_mod.VANILLA_EXTRACTED_ACCESSORS)
        self.assertEqual(p.known, len(audit_mod.KNOWN_VANILLA_FLAGS))

    def test_the_committed_file_is_what_the_fold_writes(self):
        with open(fold.EXTRAS, encoding="utf-8") as f:
            self.assertEqual(f.read(), fold.render_extras(audit_mod.VANILLA_EXTRACTED_ACCESSORS))

    def test_a_dry_run_reports_and_writes_nothing(self):
        before = os.stat(fold.EXTRAS).st_mtime_ns
        code, text = self.run_main("--dry-run", "--source", "snapshot")
        self.assertEqual(code, 0)
        self.assertIn("vanilla loc: the vanilla_parsed/ snapshot (", text)
        self.assertIn("no game install", text)
        self.assertIn('Terminal, would fold as "value": 0', text)
        self.assertIn("Chained further in vanilla, NOT folded: 0", text)
        self.assertIn("dry run: nothing written", text)
        self.assertEqual(os.stat(fold.EXTRAS).st_mtime_ns, before)



class SourceTests(unittest.TestCase):
    def game(self, root):
        return mock.patch.object(fold.path_constants, "base_game_path", root, create=True)

    def test_install_source_without_an_install_stops(self):
        with self.game("/nonexistent/game"), self.assertRaises(SystemExit):
            fold.load_vanilla_lines("install")

    def test_auto_falls_back_to_the_snapshot_and_says_so(self):
        with self.game("/nonexistent/game"):
            lines, source = fold.load_vanilla_lines("auto")
        self.assertIn("vanilla_parsed/ snapshot", source)
        self.assertIn("no game install", source)
        self.assertGreater(len(lines), 10000)

    def test_an_install_is_read_with_its_subfolders(self):
        # The engine reads english/frontend/ and the like too, and so does the
        # snapshot; `replace/` is not descended into.
        with tempfile.TemporaryDirectory() as root:
            english = os.path.join(root, "game", "localization", "english")
            for rel, key in (("a_l_english.yml", "TOP_KEY"),
                             ("frontend/b_l_english.yml", "SUB_KEY"),
                             ("replace/c_l_english.yml", "REPLACE_KEY")):
                path = os.path.join(english, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8-sig") as f:
                    f.write(f'l_english:\n {key}:0 "[Country.GetName]"\n')
            with self.game(root):
                lines, source = fold.load_vanilla_lines("auto")
            self.assertIn("the game install", source)
            self.assertEqual([(ll.file, ll.key) for ll in lines],
                             [("a_l_english.yml", "TOP_KEY"),
                              ("frontend/b_l_english.yml", "SUB_KEY")])


if __name__ == "__main__":
    unittest.main()
