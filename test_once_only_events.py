"""Events that fire once per country through 1.15's `fire_only_once` (#1404, design § 2).

Each of these 32 events used to set a variable in `immediate` that only its own trigger read. Now the engine
remembers the firing. The trigger's read of the variable stays until after 2026-12-31: a save made before the
change holds the variable but no fire record. One event, the canary, still sets its variable and logs when it
fires twice in a game started after the change, which is how a lost fire record (on a save and load, or for a
revolution's winner) would show.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from je_test_helpers import _direct_blocks, entry_text, field, strip_comments

ROOT = Path(__file__).resolve().parent

_STE = "events/society_technology_events.txt"
_JUD = "events/te_judiciary_events.txt"
ONCE_ONLY: dict[str, tuple[str, str]] = {
    **{f"society_technology_events.{n}": (_STE, f"ste_event_{n}_fired")
       for n in (1, 2, 3, 4, 5, 6, 9, 12, 13, 16, 17, 19, 20, 21, 25, 26, 27, 28, 29, 30, 31)},
    **{f"te_judiciary_events.{n}": (_JUD, f"te_jud_heard_{case}") for n, case in (
        (30, "free_soil"), (31, "otsu"), (32, "freedom_of_contract"), (33, "voided_election"),
        (34, "necessity"), (35, "house_of_justice"), (36, "new_code"))},
    "cultural_hegemony.8": ("events/cultural_hegemony_events.txt", "ch_milestone_significant"),
    "cultural_hegemony.9": ("events/cultural_hegemony_events.txt", "ch_milestone_dominant"),
    "post_scarcity_events.3": ("events/post_scarcity_events.txt", "ai_bureaucracy_debate_happened"),
    "surveillance_events.4": ("events/surveillance_events.txt", "ai_predictive_policing_debate_happened"),
}
CANARY_EVENT = "society_technology_events.1"
CANARY_MARKER = "te_fire_only_once_canary_armed"
CANARY_FILE = "common/on_actions/te_fire_only_once_selfcheck_on_actions.txt"


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def _flat(text: str) -> str:
    return " ".join(text.split())


def _event(event_id: str) -> str:
    return entry_text(_read(ONCE_ONLY[event_id][0]), event_id)


def _top_level(body: str) -> str:
    """The body with every nested block emptied, so only its own fields remain."""
    while True:
        reduced = re.sub(r"\{[^{}]*\}", "{}", body)
        if reduced == body:
            return body
        body = reduced


def _script_files(gui: bool = False):
    for sub in ("common", "events"):
        yield from sorted((ROOT / sub).rglob("*.txt"))
    if gui:
        yield from sorted((ROOT / "gui").rglob("*.gui"))


class OnceOnlyEventsTest(unittest.TestCase):
    def test_32_events(self):
        self.assertEqual(len(ONCE_ONLY), 32)

    def test_each_event_fires_once(self):
        for event_id, (_, guard) in ONCE_ONLY.items():
            body = _event(event_id)
            with self.subTest(event=event_id):
                self.assertRegex(_top_level(body), r"\bfire_only_once\s*=\s*yes\b")
                self.assertIn(f"NOT = {{ has_variable = {guard} }}", _flat(field(body, "trigger")))
                if event_id != CANARY_EVENT:
                    self.assertNotRegex(body, rf"set_variable\s*=\s*{guard}\b")

    def test_guard_variables_have_no_other_reader(self):
        """The condition that made each safe to convert: nothing outside the event (no script, no GUI) reads its
        variable."""
        guards = {guard: event_id for event_id, (_, guard) in ONCE_ONLY.items()}
        pattern = re.compile(r"\b(" + "|".join(map(re.escape, guards)) + r")\b")
        for path in _script_files(gui=True):
            text = strip_comments(path.read_text(encoding="utf-8-sig"))
            rel = path.relative_to(ROOT).as_posix()
            for name in set(pattern.findall(text)):
                event_id = guards[name]
                own = entry_text(text, event_id) if rel == ONCE_ONLY[event_id][0] else ""
                with self.subTest(file=rel, variable=name):
                    self.assertEqual(len(re.findall(rf"\b{name}\b", text)),
                                     len(re.findall(rf"\b{name}\b", own)))


class CanaryTest(unittest.TestCase):
    def test_canary_falls_back_to_its_guard_in_old_saves(self):
        trigger = _flat(field(_event(CANARY_EVENT), "trigger"))
        either = f"OR = {{ has_global_variable = {CANARY_MARKER} NOT = {{ has_variable = ste_event_1_fired }} }}"
        self.assertIn(either, trigger)
        self.assertEqual(trigger.count("NOT = { has_variable = ste_event_1_fired }"), 1)

    def test_canary_logs_a_second_firing_before_marking(self):
        immediate = field(_event(CANARY_EVENT), "immediate")
        checks = [body for body in _direct_blocks(immediate, "if")
                  if "TE_SELF_CHECK BROKEN fire_only_once_kept" in body]
        self.assertEqual(len(checks), 1)
        limit = _flat(field(checks[0], "limit"))
        self.assertIn(f"has_global_variable = {CANARY_MARKER}", limit)
        self.assertIn("has_variable = ste_event_1_fired", limit)
        self.assertRegex(checks[0], r'debug_log\s*=\s*"TE_SELF_CHECK BROKEN fire_only_once_kept')
        flat = _flat(immediate)
        self.assertLess(flat.index("TE_SELF_CHECK BROKEN"), flat.index("set_variable = ste_event_1_fired"))

    def test_canary_is_armed_only_at_game_start(self):
        text = entry_text(_read(CANARY_FILE), "on_game_started")
        self.assertIn("te_fire_only_once_canary_arm", _flat(field(text, "on_actions")).split())
        arm = _flat(field(entry_text(_read(CANARY_FILE), "te_fire_only_once_canary_arm"), "effect"))
        self.assertEqual(arm, f"set_global_variable = {CANARY_MARKER}")
        setters = [path.relative_to(ROOT).as_posix() for path in _script_files()
                   if re.search(rf"set_global_variable\s*=\s*{{?\s*(name\s*=\s*)?{CANARY_MARKER}\b",
                                strip_comments(path.read_text(encoding="utf-8-sig")))]
        self.assertEqual(setters, [CANARY_FILE])


if __name__ == "__main__":
    unittest.main()
