"""The mod's four ideological movements on the political agendas' movement lists (#1822).

Each vanilla political agenda lists the movements its government sides with and against; none named a movement the
mod adds, so every AI government was indifferent to all four. common/ai_strategies/te_ai_movement_strategies.txt
INJECTs them into four agendas' lists, placed by what each movement's ideology wants
(docs/systems/mod_systems/ai.md § AI Coverage of the Mod's Content has the table;
scripts/analysis/ai_agenda_movement_alignment.py computes it). The conservative agenda, the commonest among AI
countries, gets no entry: its three anti placements are a proposal, held until the self-check has read OK.

- the file INJECTs exactly PLACEMENT, and only list fields, so vanilla's agendas keep everything else;
- every movement the mod defines is placed for at least one agenda, and none sits on both lists of one;
- TE_SELF_CHECK ai_movement_lists reads the same placement (its triggers are held to the file), has vanilla's own
  entries on the same lists as its control, ends only on a verdict or at its last try, and calls BROKEN on a share.
"""
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
STRATEGIES = ROOT / "common/ai_strategies/te_ai_movement_strategies.txt"
MOVEMENTS = ROOT / "common/political_movements/new_ideological_movements.txt"
TRIGGERS = ROOT / "common/scripted_triggers/te_ai_coverage_triggers.txt"
SELFCHECK = ROOT / "common/on_actions/te_ai_movement_lists_selfcheck_on_actions.txt"
SELFCHECK_VALUES = ROOT / "common/script_values/te_ai_movement_lists_selfcheck_values.txt"
PLAYTEST = ROOT / "docs/testing/ai-economy-playtest.md"
SYSTEM_DOC = ROOT / "docs/systems/mod_systems/ai.md"

# agenda -> (pro, anti). A movement on neither list for an agenda is left off on purpose (ai.md's table).
PLACEMENT = {
    "ai_strategy_conservative_agenda": (set(), set()),  # held: ai.md, "Proposals left for the owner"
    "ai_strategy_reactionary_agenda": (set(), {"movement_civil_rights", "movement_transhumanist"}),
    "ai_strategy_progressive_agenda": ({"movement_civil_rights", "movement_transhumanist"}, set()),
    "ai_strategy_egalitarian_agenda": ({"movement_environmental", "movement_civil_rights", "movement_anti_war"}, set()),
    "ai_strategy_nationalist_agenda": (set(), {"movement_civil_rights", "movement_anti_war"}),
}

# The self-check's control: movements vanilla itself lists on each list the mod INJECTs into.
VANILLA_CONTROL = {
    "ai_strategy_reactionary_agenda": (set(), {"movement_socialist", "movement_labor", "movement_liberal"}),
    "ai_strategy_progressive_agenda": ({"movement_liberal", "movement_modernizer", "movement_feminist"}, set()),
    "ai_strategy_egalitarian_agenda": ({"movement_labor", "movement_socialist", "movement_feminist"}, set()),
    "ai_strategy_nationalist_agenda": (set(), {"movement_socialist", "movement_labor", "movement_feminist"}),
}


def entries(node):
    for part in node if isinstance(node, list) else [node]:
        if isinstance(part, dict):
            for key, (op, value) in part.items():
                yield key, op, value


def parse(path):
    parser = ParadoxFileParser()
    return parser.parse_object(parser.tokenize("{" + path.read_text(encoding="utf-8-sig") + "}"))[0]


def field(block, key):
    return next((value for k, _, value in entries(block) if k == key), None)


def injected():
    """{agenda: {field: set of movements}} as the strategy file writes it."""
    out = {}
    for name, _, block in entries(parse(STRATEGIES)):
        out[name] = {key: set(value) for key, _, value in entries(block)}
    return out


def plain_text(node):
    return " ".join(str(key) + " " + (plain_text(value) if isinstance(value, (dict, list)) else str(value))
                    for key, _, value in entries(node))


def listed_by_trigger(name):
    """{agenda: movements} read from a te_aml_on_*_list trigger's OR of (owner has_strategy, movement types)."""
    out = {}
    for key, _, branch in entries(field(field(parse(TRIGGERS), name), "OR")):
        assert key == "AND"
        agenda = field(field(branch, "owner"), "has_strategy")
        either = field(branch, "OR")
        source = either if either is not None else branch
        out[agenda] = {v for k, _, v in entries(source) if k == "is_political_movement_type"}
    return out


class MovementListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.injected = injected()
        cls.movements = [name for name, _, _ in entries(parse(MOVEMENTS))]

    def test_the_file_injects_the_placement_and_nothing_else(self):
        self.assertEqual(set(self.injected), {"INJECT:" + agenda for agenda, lists in PLACEMENT.items() if any(lists)})
        for agenda, (pro, anti) in PLACEMENT.items():
            with self.subTest(agenda=agenda):
                fields = self.injected.get("INJECT:" + agenda, {})
                self.assertLessEqual(set(fields), {"pro_movements", "anti_movements"})
                self.assertEqual(fields.get("pro_movements", set()), pro)
                self.assertEqual(fields.get("anti_movements", set()), anti)
                self.assertEqual(pro & anti, set())

    def test_every_mod_movement_is_placed_somewhere(self):
        self.assertEqual(len(self.movements), 4)
        placed = set().union(*(pro | anti for pro, anti in PLACEMENT.values()))
        self.assertEqual(placed, set(self.movements),
                         "a movement the mod defines is on no agenda's list (or a listed one is gone)")

    def test_each_placement_agrees_with_the_alignment_score(self):
        # The placement's method (scripts/analysis/ai_agenda_movement_alignment.py): a pro entry scores above
        # zero for that agenda and an anti entry below. A stance change that flips a sign means revisiting the entry.
        import sys
        sys.path.insert(0, str(ROOT / "scripts/analysis"))
        import ai_agenda_movement_alignment as alignment
        data = alignment.Data()
        self.assertEqual(set(alignment.MOD_MOVEMENTS), set(self.movements))
        for agenda, (pro, anti) in PLACEMENT.items():
            short = agenda.removeprefix("ai_strategy_").removesuffix("_agenda")
            for movement in pro:
                with self.subTest(agenda=short, movement=movement):
                    self.assertGreater(data.score(movement, short), 0)
            for movement in anti:
                with self.subTest(agenda=short, movement=movement):
                    self.assertLess(data.score(movement, short), 0)

    def test_the_conservative_agenda_is_held(self):
        self.assertEqual(PLACEMENT["ai_strategy_conservative_agenda"], (set(), set()))
        self.assertNotIn("INJECT:ai_strategy_conservative_agenda", self.injected)

    def test_the_self_check_reads_the_same_placement(self):
        pro, anti = listed_by_trigger("te_aml_on_pro_list"), listed_by_trigger("te_aml_on_anti_list")
        self.assertEqual(pro, {a: p for a, (p, _) in PLACEMENT.items() if p})
        self.assertEqual(anti, {a: n for a, (_, n) in PLACEMENT.items() if n})
        triggers = parse(TRIGGERS)
        mod = {v for k, _, v in entries(field(field(triggers, "te_aml_is_mod_movement"), "OR"))}
        self.assertEqual(mod, set(self.movements))
        agendas = {v for k, _, v in entries(field(field(triggers, "te_aml_holds_a_common_agenda"), "OR"))}
        self.assertEqual(agendas, set(PLACEMENT))

    def test_the_control_sits_on_the_lists_the_mod_injects_into(self):
        pro = listed_by_trigger("te_aml_vanilla_on_pro_list")
        anti = listed_by_trigger("te_aml_vanilla_on_anti_list")
        self.assertEqual(pro, {a: p for a, (p, _) in VANILLA_CONTROL.items() if p})
        self.assertEqual(anti, {a: n for a, (_, n) in VANILLA_CONTROL.items() if n})
        # The same agenda and the same side as each INJECT: a replaced list is the one that loses its control.
        for agenda, (mod_pro, mod_anti) in PLACEMENT.items():
            with self.subTest(agenda=agenda):
                control_pro, control_anti = VANILLA_CONTROL.get(agenda, (set(), set()))
                self.assertEqual(bool(mod_pro), bool(control_pro))
                self.assertEqual(bool(mod_anti), bool(control_anti))
                self.assertEqual((control_pro | control_anti) & set(self.movements), set())

    def test_the_self_check_is_wired_and_bounded(self):
        text = re.sub(r"#[^\n]*", "", SELFCHECK.read_text(encoding="utf-8-sig"))
        tree = parse(SELFCHECK)
        hooked = list(field(field(tree, "on_yearly_pulse"), "on_actions"))
        self.assertEqual(hooked, ["te_ai_movement_lists_selfcheck_settle", "te_ai_movement_lists_selfcheck"])
        check = field(tree, "te_ai_movement_lists_selfcheck")
        self.assertIn("te_aml_checked", str(field(check, "trigger")))  # runs until it latches
        for verdict in ("START", "OK", "REPLACED", "BROKEN", "NO_VERDICT"):
            self.assertRegex(text, r'debug_log = "TE_SELF_CHECK %s ai_movement_lists\b' % verdict)
        # A try needs enough listed movements, and only a try counts toward the bound.
        self.assertRegex(text, r"limit\s*=\s*\{\s*global_var:te_aml_listed\s*>=\s*te_aml_min_counted\s*\}\s*"
                               r"change_global_variable\s*=\s*\{\s*name\s*=\s*te_aml_tries\s+add\s*=\s*1\s*\}")
        # The latch: each of OK, REPLACED and BROKEN sets it, the last try sets it, the first try does not.
        branches = re.split(r"\b(?:if|else_if)\s*=\s*\{\s*limit", text[text.index("random_country"):])[1:]
        latched = {}
        for branch in branches:
            verdict = re.search(r"TE_SELF_CHECK (OK|REPLACED|BROKEN|NO_VERDICT) ai_movement_lists[^\"]*", branch)
            key = verdict.group(1) + (" last" if "last try" in verdict.group(0) else
                                      " first" if "first try" in verdict.group(0) else "")
            latched[key] = "set_global_variable = te_aml_checked" in branch
        self.assertEqual(latched, {"OK": True, "REPLACED": True, "BROKEN": True,
                                   "NO_VERDICT last": True, "NO_VERDICT first": False})
        self.assertRegex(branches[3], r"te_aml_tries_g\s*>=\s*te_aml_max_tries")
        # OK and REPLACED differ only in the control: vanilla's entries still acted on, or none of them.
        self.assertRegex(branches[0], r"te_aml_follows_the_mods_entries\s*=\s*yes\s*"
                                      r"te_aml_vanilla_listed_g\s*>=\s*te_aml_min_counted\s*te_aml_vanilla_match_g\s*>=\s*1")
        self.assertRegex(branches[1], r"te_aml_follows_the_mods_entries\s*=\s*yes\s*"
                                      r"te_aml_vanilla_listed_g\s*>=\s*te_aml_min_counted\s*te_aml_vanilla_match_g\s*=\s*0")
        # BROKEN on a share of the listed movements, never on one movement.
        self.assertRegex(branches[2], r"te_aml_mismatch_g\s*>=\s*3\s*te_aml_mismatch_share\s*>=\s*te_aml_against_share_broken")
        follows = plain_text(field(parse(TRIGGERS), "te_aml_follows_the_mods_entries"))
        for needed in ("te_aml_match_g", "te_aml_mismatch_share", "te_aml_match_share", "te_aml_unlisted_share"):
            self.assertIn(needed, follows)
        values = SELFCHECK_VALUES.read_text(encoding="utf-8-sig")
        used = set(re.findall(r"ScriptValue\('(\w+)'\)", text)) | set(re.findall(r"\b(te_aml_\w+_(?:g|share|tries|counted|broken))\b", text))
        for name in used:
            self.assertRegex(values, r"(?m)^" + name + r"\s*=", name)

    def test_the_play_test_list_and_the_doc_cover_it(self):
        playtest = PLAYTEST.read_text(encoding="utf-8")
        self.assertTrue("TE_SELF_CHECK … ai_movement_lists" in playtest, "the play-test list lacks the self-check row")
        doc = SYSTEM_DOC.read_text(encoding="utf-8")
        for movement in self.movements:
            self.assertTrue(f"`{movement}`" in doc, f"ai.md does not place {movement}")

    def test_matches_the_game_files(self):
        try:
            from path_constants import base_game_path
            path = Path(base_game_path) / "game/common/ai_strategies/03_political_strategies.txt"
        except Exception:
            path = None
        if path is None or not path.is_file():
            self.skipTest("no Victoria 3 install")
        vanilla = {name: block for name, _, block in entries(parse(path))}
        for agenda, (pro, anti) in PLACEMENT.items():
            with self.subTest(agenda=agenda):
                self.assertIn(agenda, vanilla)
                # The INJECT appends to a list vanilla already has, and repeats nothing in it.
                for key, added in (("pro_movements", pro), ("anti_movements", anti)):
                    if added:
                        theirs = field(vanilla[agenda], key)
                        self.assertIsNotNone(theirs)
                        self.assertEqual(set(theirs) & added, set())
                control_pro, control_anti = VANILLA_CONTROL.get(agenda, (set(), set()))
                self.assertLessEqual(control_pro, set(field(vanilla[agenda], "pro_movements") or ()))
                self.assertLessEqual(control_anti, set(field(vanilla[agenda], "anti_movements") or ()))


if __name__ == "__main__":
    unittest.main()
