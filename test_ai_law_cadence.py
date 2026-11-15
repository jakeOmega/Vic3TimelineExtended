"""AI law cadence (2026-11-15): AI countries start law changes more often, with more revolution aversion to match.

- common/ai_strategies/edited_default_strategy.txt: ai_strategy_default's change_law_chance is vanilla's 1 plus 39,
  times 10 in the mod's crisis case. The default's field adds to every political strategy's own.
- common/ai_strategies/edited_political_strategies.txt: seven political agendas' revolution_aversion, each vanilla's
  whole block plus one `add` line; nothing else in those strategies (the pass-chance floor stays vanilla's).
- TE_SELF_CHECK ai_law_cadence (common/on_actions/te_ai_law_cadence_selfcheck_on_actions.txt) and its play-test row.

The arithmetic behind the numbers: docs/systems/mod_systems/ai.md § Law-Change Cadence.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT = ROOT / "common/ai_strategies/edited_default_strategy.txt"
POLITICAL = ROOT / "common/ai_strategies/edited_political_strategies.txt"
SELFCHECK = ROOT / "common/on_actions/te_ai_law_cadence_selfcheck_on_actions.txt"
SELFCHECK_VALUES = ROOT / "common/script_values/te_ai_law_cadence_selfcheck_values.txt"
PLAYTEST = ROOT / "docs/testing/ai-economy-playtest.md"
SYSTEM_DOC = ROOT / "docs/systems/mod_systems/ai.md"

# Vanilla 1.15.1 (game/common/ai_strategies/00_default_strategy.txt): `change_law_chance = { value = 1 }`.
VANILLA_DEFAULT_CHANCE = 1
CHANCE_ADD = 39
CRISIS_MULTIPLIER = 10

# Vanilla 1.15.1's revolution_aversion block per agenda (game/common/ai_strategies/03_political_strategies.txt),
# whitespace-normalized, and the mod's rise. test_restated_blocks_match_the_game_files reads the game where installed.
VANILLA_AVERSION = {
    "ai_strategy_conservative_agenda": (
        "value = 75 "
        "if = { limit = { has_journal_entry = je_tp_pool_suppress_revolts } add = 50 } "
        "if = { limit = { divided_monarchists_ai_monarchist = yes } add = 50 } "
        "if = { limit = { divided_monarchists_ai_republican = yes } subtract = 50 } "
        "min = 10"
    ),
    "ai_strategy_reactionary_agenda": (
        "value = 50 if = { limit = { has_journal_entry = je_tp_pool_suppress_revolts } add = 50 }"
    ),
    "ai_strategy_progressive_agenda": "value = 50",
    "ai_strategy_egalitarian_agenda": "value = 25",
    "ai_strategy_nationalist_agenda": "value = 35",
    "ai_strategy_consolidation_agenda": "value = 75",
    "ai_strategy_confrontation_agenda": "value = 25",
}
AVERSION_ADD = {
    "ai_strategy_conservative_agenda": 10,
    "ai_strategy_reactionary_agenda": 20,
    "ai_strategy_progressive_agenda": 10,
    "ai_strategy_egalitarian_agenda": 10,
    "ai_strategy_nationalist_agenda": 10,
    "ai_strategy_consolidation_agenda": 5,
    "ai_strategy_confrontation_agenda": 5,
}


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    """The body of the first `name = { ... }` (a top-level entry may carry a directive prefix)."""
    m = re.search(r"(?:^|\s)(?:[A-Z_]+:)?" + re.escape(name) + r"\s*=\s*\{", text)
    if m is None:
        return None
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def _top_level_keys(body):
    """The keys at depth 0 of a block body, in order."""
    keys, depth = [], 0
    for tok in re.findall(r"[{}]|[^\s{}=]+(?=\s*=)", body):
        if tok == "{":
            depth += 1
        elif tok == "}":
            depth -= 1
        elif depth == 0:
            keys.append(tok)
    return keys


def _norm(text):
    return " ".join(text.replace("{", " { ").replace("}", " } ").split())


def _without_line(body, pattern):
    """The body with the first line matching `pattern` removed."""
    return re.sub(pattern, "", body, count=1)


class TestDefaultChangeLawChance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _strip_comments(DEFAULT.read_text(encoding="utf-8-sig"))
        cls.strategy = _block(cls.text, "ai_strategy_default")
        cls.field = _block(cls.strategy, "change_law_chance")

    def test_the_field_appears_once(self):
        self.assertEqual(_top_level_keys(self.strategy).count("change_law_chance"), 1)

    def test_restates_vanilla_then_adds(self):
        keys = _top_level_keys(self.field)
        self.assertEqual(keys[:2], ["value", "add"], "value = 1 (vanilla's), then the add, then the crisis branch")
        self.assertRegex(self.field, r"^\s*value\s*=\s*%d\s" % VANILLA_DEFAULT_CHANCE)
        self.assertRegex(self.field, r"\badd\s*=\s*%d\b" % CHANCE_ADD)
        self.assertEqual(VANILLA_DEFAULT_CHANCE + CHANCE_ADD, 40)

    def test_the_crisis_multiplier_still_applies(self):
        branch = _block(self.field, "if")
        self.assertIsNotNone(branch)
        self.assertEqual(_top_level_keys(self.field), ["value", "add", "if"])
        movement = _block(branch, "any_political_movement")
        self.assertRegex(movement, r"political_movement_support\s*>\s*0\.2\b")
        self.assertRegex(movement, r"political_movement_radicalism\s*>\s*0\.75\b")
        self.assertEqual(_top_level_keys(branch), ["limit", "multiply"])
        self.assertRegex(branch, r"\bmultiply\s*=\s*%d\b" % CRISIS_MULTIPLIER)

    def test_matches_the_game_files(self):
        path = _game_file("00_default_strategy.txt")
        if path is None:
            self.skipTest("no Victoria 3 install")
        vanilla = _block(_strip_comments(path.read_text(encoding="utf-8-sig")), "ai_strategy_default")
        self.assertEqual(_norm(_block(vanilla, "change_law_chance")), "value = %d" % VANILLA_DEFAULT_CHANCE)


class TestPoliticalStrategies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _strip_comments(POLITICAL.read_text(encoding="utf-8-sig"))
        cls.injected = re.findall(r"(?m)^INJECT:(ai_strategy_\w+)\s*=\s*\{", cls.text)

    def test_injects_the_seven_agendas_once_each(self):
        self.assertEqual(sorted(self.injected), sorted(VANILLA_AVERSION))
        self.assertNotRegex(self.text, r"(?m)^(?:REPLACE|TRY_REPLACE|REPLACE_OR_CREATE):", "INJECT only")

    def test_only_revolution_aversion(self):
        # The pass-chance floor and the agendas' own rates stay vanilla's (ai.md § Law-Change Cadence).
        for name in self.injected:
            with self.subTest(strategy=name):
                self.assertEqual(_top_level_keys(_block(self.text, name)), ["revolution_aversion"])

    def test_each_restates_vanilla_and_adds_once(self):
        for name, vanilla in VANILLA_AVERSION.items():
            with self.subTest(strategy=name):
                field = _block(_block(self.text, name), "revolution_aversion")
                adds = re.findall(r"(?m)^\s*add\s*=\s*(\d+)\s*$", field)
                self.assertIn(str(AVERSION_ADD[name]), adds)
                own = _without_line(field, r"(?m)^\s*add\s*=\s*%d\s*$" % AVERSION_ADD[name])
                self.assertEqual(_norm(own), vanilla)
                self.assertEqual(_top_level_keys(field)[:2], ["value", "add"])

    def test_aversion_stays_within_the_engine_range(self):
        for name, add in AVERSION_ADD.items():
            base = int(re.match(r"value = (\d+)", VANILLA_AVERSION[name]).group(1))
            with self.subTest(strategy=name):
                self.assertGreater(add, 0)
                self.assertLessEqual(base + add, 100)

    def test_sorts_before_the_other_ai_mods_file(self):
        # Two INJECTs of one field apply in file order and the later one wins; with that mod on, its aversion stands.
        self.assertLess(POLITICAL.name, "kai_political_strategies.txt")

    def test_restated_blocks_match_the_game_files(self):
        path = _game_file("03_political_strategies.txt")
        if path is None:
            self.skipTest("no Victoria 3 install")
        game = _strip_comments(path.read_text(encoding="utf-8-sig"))
        for name, vanilla in VANILLA_AVERSION.items():
            with self.subTest(strategy=name):
                self.assertEqual(_norm(_block(_block(game, name), "revolution_aversion")), vanilla)


class TestSelfCheck(unittest.TestCase):
    def test_once_a_game_with_all_verdicts(self):
        text = SELFCHECK.read_text(encoding="utf-8-sig")
        body = _strip_comments(text)
        self.assertRegex(body, r"on_monthly_pulse\s*=\s*\{\s*on_actions\s*=\s*\{\s*te_ai_law_cadence_selfcheck\s*\}")
        self.assertNotRegex(body, r"on_monthly_pulse\s*=\s*\{[^}]*\beffect\b", "a sub-action, never a vanilla effect")
        self.assertIn("NOT = { has_global_variable = te_alc_checked }", body)
        self.assertIn("set_global_variable = te_alc_checked", body)
        for verdict in ("OK", "BROKEN", "NO_VERDICT"):
            self.assertIn("TE_SELF_CHECK %s ai_law_cadence" % verdict, body)
        self.assertRegex(body, r"te_alc_chk_share\s*>=\s*0\.35")
        self.assertRegex(body, r"te_alc_chk_share\s*<\s*0\.30")
        values = _strip_comments(SELFCHECK_VALUES.read_text(encoding="utf-8-sig"))
        for name in ("te_alc_chk_countries_g", "te_alc_chk_enacting_g", "te_alc_chk_share"):
            self.assertRegex(values, r"(?m)^%s\s*=" % name)

    def test_the_play_test_list_and_the_doc_carry_it(self):
        playtest = PLAYTEST.read_text(encoding="utf-8")
        self.assertIn("ai_law_cadence", playtest)
        self.assertIn("Fallback", playtest)
        self.assertIn("## Law-Change Cadence", SYSTEM_DOC.read_text(encoding="utf-8"))


def _game_file(name):
    try:
        from path_constants import base_game_path
    except Exception:
        return None
    path = Path(base_game_path) / "game/common/ai_strategies" / name
    return path if path.is_file() else None


if __name__ == "__main__":
    unittest.main()
