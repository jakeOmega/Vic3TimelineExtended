"""The AI doesn't subsidize its coal and oil power plants (#933), its railways
or its ports (#1050).

An INJECT into ai_strategy_default can't change these buildings, which
vanilla's subsidies block already holds (must_have), but a strategy's value
overrides the default's, and an INJECT adds a new key to a strategy's
subsidies block (read in game 2026-10-16). So te_ai_subsidy_strategies.txt
sets each to should_remove in every vanilla administrative strategy; one it
misses leaves its countries on the default's must_have.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Vanilla 1.14.5, game/common/ai_strategies/01_admin_strategies.txt (`type = administrative`).
# test_matches_the_game_files checks this list where the game is installed.
ADMIN_STRATEGIES = (
    "ai_strategy_agricultural_expansion",
    "ai_strategy_plantation_economy",
    "ai_strategy_resource_expansion",
    "ai_strategy_industrial_expansion",
    "ai_strategy_placate_population",
    "ai_strategy_colonial_extraction",
    "ai_strategy_montenegro_admin",
)
UNSUBSIDIZED = ("building_power_plant", "building_railway", "building_port")


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(r"^(?:[A-Z_]+:)?" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class TestAISubsidyStrategies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.strategies = _strip_comments(
            (ROOT / "common/ai_strategies/te_ai_subsidy_strategies.txt").read_text(encoding="utf-8-sig"))
        cls.injected = re.findall(r"(?m)^INJECT:(ai_strategy_\w+)\s*=\s*\{", cls.strategies)

    def test_every_administrative_strategy_is_injected_once(self):
        self.assertEqual(sorted(self.injected), sorted(ADMIN_STRATEGIES))

    def test_each_inject_sets_should_remove(self):
        for name in self.injected:
            for building in UNSUBSIDIZED:
                with self.subTest(strategy=name, building=building):
                    self.assertRegex(_block(self.strategies, name), r"\b" + building + r"\s*=\s*should_remove\b")

    def test_matches_the_game_files(self):
        try:
            from path_constants import base_game_path
            path = Path(base_game_path) / "game/common/ai_strategies/01_admin_strategies.txt"
        except Exception:
            path = None
        if path is None or not path.is_file():
            self.skipTest("no Victoria 3 install")
        text = _strip_comments(path.read_text(encoding="utf-8-sig"))
        admin = [name for name in re.findall(r"(?m)^(ai_strategy_\w+)\s*=\s*\{", text)
                 if re.search(r"\btype\s*=\s*administrative\b", _block(text, name))]
        self.assertEqual(sorted(admin), sorted(ADMIN_STRATEGIES))


if __name__ == "__main__":
    unittest.main()
