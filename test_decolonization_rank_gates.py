"""Events written for a weaker country don't reach the strongest ones.

The Non-Aligned Path (decolonization_events.21) has great powers courting a
young nation, and gated only on recently_decolonized, so a former colony that
had become a great power was courted by its own peers. Powerful Friends
(decolonization_events.12) offers a colonial power a patron, and reached the
world's first-ranked country (owner report, 2026-11-10). Each event and its
entry in the monthly pool carry the same rank gate, so the pool doesn't spend
its roll on an event that then refuses to fire.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

GATES = {
    "decolonization_events.21": "country_rank < rank_value:great_power",
    "decolonization_events.12": "global_country_ranking > 1",
}


def _strip(text):
    return re.sub(r'("[^"\n]*")|#[^\n]*', lambda m: m[1] or "", text)


def _close(text, start):
    depth, i = 1, start
    while depth and i < len(text):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return i


def _block(text, pattern):
    m = re.search(pattern, text, re.M)
    return text[m.end():_close(text, m.end())]


def _norm(text):
    return re.sub(r"\s+", " ", text)


class TestRankGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = _strip((ROOT / "events/decolonization_events.txt").read_text(encoding="utf-8-sig"))
        cls.pool = _strip((ROOT / "common/on_actions/extra_on_actions.txt").read_text(encoding="utf-8-sig"))

    def test_event_trigger_has_the_gate(self):
        for name, gate in GATES.items():
            event = _block(self.events, r"^" + re.escape(name) + r"\s*=\s*\{")
            trigger = _block(event, r"^\ttrigger\s*=\s*\{")
            # Top level of the trigger, not inside an any_country block.
            top = re.sub(r"\{[^{}]*\}", "", trigger)
            while "{" in top:
                top = re.sub(r"\{[^{}]*\}", "", top)
            self.assertIn(gate, _norm(top), name)

    def test_pool_entry_has_the_gate(self):
        for name, gate in GATES.items():
            call = re.search(r"trigger_event\s*=\s*\{\s*id\s*=\s*" + re.escape(name) + r"\s*\}", self.pool)
            self.assertIsNotNone(call, name)
            # The pool entry's trigger block is the last one opened before the call.
            start = self.pool.rfind("trigger = {", 0, call.start())
            trigger = self.pool[start:_close(self.pool, start + len("trigger = {"))]
            self.assertLess(_close(self.pool, start + len("trigger = {")), call.start(), name)
            self.assertIn(gate, _norm(trigger), name)


if __name__ == "__main__":
    unittest.main()
