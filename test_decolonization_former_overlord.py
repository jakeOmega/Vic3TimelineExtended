"""A former colony's former_overlord variable can name a country that has
since died, so reads go through `var:former_overlord ?= { is_country_alive = yes }`.

decolonization_events.7 used to find the overlord with a random_country whose
limit compared every country with root's var:former_overlord. Once that
overlord was dead, the comparison logged "Event target link 'var' returned an
invalid object" once per country, 208 lines a firing (observer run,
2026-10-06). It now saves the scope from the variable behind the alive check,
as decol_is_independent_former_colony already did.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_ITERATOR = re.compile(r"\b(random|every|any|ordered)_country\s*=\s*\{")


def _strip(text):
    return re.sub(r'("[^"\n]*")|#[^\n]*', lambda m: m[1] or "", text)


def _close(text, start):
    depth, i = 1, start
    while depth and i < len(text):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return i


def _event(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    return text[m.end():_close(text, m.end())]


class TestFormerOverlordReads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = _strip((ROOT / "events/decolonization_events.txt").read_text(encoding="utf-8-sig"))

    def test_no_country_iterator_compares_the_former_overlord(self):
        bad = []
        for m in _ITERATOR.finditer(self.events):
            block = self.events[m.end():_close(self.events, m.end())]
            if re.search(r"var:former_overlord\s*=\s*prev\b", block):
                bad.append(self.events[:m.start()].count("\n") + 1)
        self.assertEqual(bad, [], "read var:former_overlord directly behind is_country_alive")

    def test_event_7_saves_a_living_former_overlord(self):
        immediate = _event(self.events, "decolonization_events.7")
        immediate = immediate[immediate.index("immediate"):]
        self.assertRegex(immediate, r"var:former_overlord\s*\?=\s*\{\s*is_country_alive\s*=\s*yes\s*\}")
        self.assertRegex(immediate, r"var:former_overlord\s*=\s*\{\s*save_scope_as\s*=\s*former_overlord\s*\}")


if __name__ == "__main__":
    unittest.main()
