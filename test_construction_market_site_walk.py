"""The construction market's site re-placement walks the country's own states, not the world.

te_construction_market_country_update_sites runs in a country's scope, once for each country a border change
touches and once a year for every country (te_construction_market_recalc_events.1). It came from the Free
Market Construction mod with `every_state`, the world iterator, so every call re-placed the sites of every
country on the map: about 20 ms a call on the main thread in a 1931 game, 3 s in 30 days
(docs/audits/late_game_performance.md). The scoped iterator is `every_scope_state`.

Run: python3 -m unittest test_construction_market_site_walk -v
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EFFECTS = ROOT / "common/scripted_effects/te_construction_market_update_effects.txt"
EFFECT = "te_construction_market_country_update_sites"
WORLD_STATE_ITERATORS = ("every_state", "any_state", "random_state", "ordered_state")
# A walk over every country's own states is the world walk again.
COUNTRY_ITERATORS = ("every_country", "any_country", "random_country", "ordered_country")


def body(text: str, name: str) -> str:
    """The text between the braces of the top-level `name = { ... }`, comments removed."""
    text = "\n".join(line.split("#", 1)[0] for line in text.lstrip("﻿").splitlines())
    match = re.search(r"^%s\s*=\s*\{" % re.escape(name), text, re.M)
    if match is None:
        raise AssertionError("%s is not defined in %s" % (name, EFFECTS.name))
    depth, start = 1, match.end()
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i]
    raise AssertionError("%s's braces do not close" % name)


class SiteWalkTest(unittest.TestCase):
    def setUp(self):
        self.body = body(EFFECTS.read_text(encoding="utf-8"), EFFECT)

    def test_the_walk_is_over_the_countrys_own_states(self):
        self.assertRegex(self.body, r"\bevery_scope_state\s*=\s*\{")

    def test_no_world_state_iterator(self):
        for iterator in WORLD_STATE_ITERATORS:
            with self.subTest(iterator=iterator):
                self.assertNotRegex(self.body, r"(?<![\w.:])%s\s*=" % iterator,
                                    "%s walks every state in the world; the country's own are every_scope_state"
                                    % iterator)

    def test_no_country_iterator(self):
        for iterator in COUNTRY_ITERATORS:
            with self.subTest(iterator=iterator):
                self.assertNotRegex(self.body, r"(?<![\w.:])%s\s*=" % iterator,
                                    "%s = { every_scope_state = { ... } } walks every state in the world again"
                                    % iterator)


if __name__ == "__main__":
    unittest.main()
