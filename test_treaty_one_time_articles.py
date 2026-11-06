"""The mod's one-off treaty articles carry vanilla 1.15's `is_one_time` and not `can_be_renegotiated` (#1407).

An article that does its work once, at entry into force, and reverts nothing at the end takes `is_one_time`, as every
vanilla one-time article does (transfer state, ship, subject and debt, recognize independence, join a power bloc): the
AI then withdraws once the binding period ends from a treaty that mostly gave it one-offs, and stops paying upkeep for
nothing. None of vanilla's also carries `can_be_renegotiated`, which would re-run the hook on a renegotiation
(scripting_best_practices.md § "1.15: renegotiation re-runs on_entry_into_force").

    python3 test_treaty_one_time_articles.py
"""
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent

ONE_OFFS = {
    "disband_company", "seize_company", "return_cultural_property", "surrender_monument", "te_cede_colony",
    "population_transfer",
}


def unwrap(value):
    while isinstance(value, tuple) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def articles():
    out = {}
    for path in sorted((ROOT / "common" / "treaty_articles").glob("*.txt")):
        parser = ParadoxFileParser()
        parser.parse_file(str(path), apply_directives=False)
        for name, body in parser.data.items():
            body = unwrap(body)
            if isinstance(body, dict):
                out[name] = [str(f) for f in unwrap(body.get("flags")) or []]
    return out


class OneTimeArticles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flags = articles()

    def test_the_one_offs_are_one_time(self):
        self.assertEqual(sorted(ONE_OFFS - set(self.flags)), [], "a one-off article no longer exists: update ONE_OFFS")
        for name in sorted(ONE_OFFS):
            with self.subTest(article=name):
                self.assertIn("is_one_time", self.flags[name])

    def test_no_one_time_article_is_renegotiable(self):
        both = sorted(n for n, f in self.flags.items() if "is_one_time" in f and "can_be_renegotiated" in f)
        self.assertEqual(both, [])

    def test_one_time_articles_are_the_listed_ones(self):
        """A new one-off joins ONE_OFFS; an article that takes the flag without being one is a mistake."""
        self.assertEqual(sorted(n for n, f in self.flags.items() if "is_one_time" in f), sorted(ONE_OFFS))


if __name__ == "__main__":
    unittest.main()
