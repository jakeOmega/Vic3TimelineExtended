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


YOUNG_STATE = (4, 7, 16, 17, 18, 21)


class TestOncePerIndependence(unittest.TestCase):
    """Each young-state event fires once per independence (owner, 2026-11-10):
    a 10-year cooldown inside the 20-year recently_decolonized window let The
    Strongman's Promise fire twice. The event marks itself seen, its trigger
    and its pool entry test the mark, and being freed again clears it."""

    @classmethod
    def setUpClass(cls):
        cls.events = _strip((ROOT / "events/decolonization_events.txt").read_text(encoding="utf-8-sig"))
        cls.pool = _strip((ROOT / "common/on_actions/extra_on_actions.txt").read_text(encoding="utf-8-sig"))
        cls.effects = _strip((ROOT / "common/scripted_effects/decolonization.txt").read_text(encoding="utf-8-sig"))
        cls.release = _strip(
            (ROOT / "common/on_actions/te_construction_market_on_actions.txt").read_text(encoding="utf-8-sig"))

    def test_the_list_is_every_event_that_reads_the_window(self):
        found = set()
        for m in re.finditer(r"^decolonization_events\.(\d+)\s*=\s*\{", self.events, re.M):
            event = self.events[m.end():_close(self.events, m.end())]
            trigger = _block(event, r"^\ttrigger\s*=\s*\{") if re.search(r"^\ttrigger\s*=", event, re.M) else ""
            if re.search(r"^\t\thas_variable = recently_decolonized", trigger, re.M):
                found.add(int(m[1]))
        self.assertEqual(found, set(YOUNG_STATE))

    def test_event_marks_itself_and_tests_the_mark(self):
        for n in YOUNG_STATE:
            event = _block(self.events, rf"^decolonization_events\.{n}\s*=\s*\{{")
            self.assertIn(f"NOT = {{ has_variable = decol_young_state_seen_{n} }}",
                          _norm(_block(event, r"^\ttrigger\s*=\s*\{")), n)
            self.assertIn(f"decol_young_state_seen = {{ EVENT = {n} }}",
                          _norm(_block(event, r"^\timmediate\s*=\s*\{")), n)

    def test_pool_entry_tests_the_mark(self):
        for n in YOUNG_STATE:
            call = re.search(rf"trigger_event\s*=\s*\{{\s*id\s*=\s*decolonization_events\.{n}\s*\}}", self.pool)
            start = self.pool.rfind("trigger = {", 0, call.start())
            trigger = self.pool[start:_close(self.pool, start + len("trigger = {"))]
            self.assertIn(f"NOT = {{ has_variable = decol_young_state_seen_{n} }}", _norm(trigger), n)

    def test_mark_lasts_the_window(self):
        seen = _norm(_block(self.effects, r"^decol_young_state_seen\s*=\s*\{"))
        self.assertIn("name = decol_young_state_seen_$EVENT$ days = 7300", seen)
        self.assertIn("name = recently_decolonized days = 7300", _norm(self.effects))

    def test_being_freed_again_clears_every_mark(self):
        reset = _block(self.effects, r"^decol_young_state_reset\s*=\s*\{")
        for n in YOUNG_STATE:
            self.assertIn(f"remove_variable = decol_young_state_seen_{n}", reset, n)
        for text in (_block(self.effects, r"^decol_mark_former_colony\s*=\s*\{"), self.release):
            self.assertRegex(_norm(text), r"name = recently_decolonized days = 7300 \} decol_young_state_reset = yes")
        # Nothing else sets the window without the reset.
        sets = len(re.findall(r"name = recently_decolonized\b", self.effects + self.release + self.events + self.pool))
        self.assertEqual(sets, 2)


if __name__ == "__main__":
    unittest.main()
