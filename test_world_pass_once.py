"""Monthly and yearly refreshes that read a world-wide value once, not once per holder or once per use.

Each of these read a value that walks every country (or every state's buildings) several times in one
refresh, or once per holder when one census serves them all. The script profiler's call graph on a 1931
game put them among the largest serial entries (docs/audits/late_game_performance.md). These tests keep the
single read in place, and keep each shortcut equal to what it replaced.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from je_test_helpers import _direct_blocks, entry_text, field

ROOT = Path(__file__).resolve().parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def _flat(text: str) -> str:
    return " ".join(text.split())


def _monthly_effect(je_file: str, je: str) -> str:
    return field(field(entry_text(_read(je_file), je), "on_monthly_pulse"), "effect")


class CovertWorldMaximum(unittest.TestCase):
    """The world's best intelligence capacity: one census a month, not one per holder."""

    def test_the_census_sits_behind_a_lock_shorter_than_a_month(self):
        pulse = _monthly_effect("common/journal_entries/je_covert_warfare.txt", "je_covert_warfare")
        gated = [b for b in _direct_blocks(pulse, "if") if "ordered_country" in b]
        self.assertEqual(len(gated), 1, "the ordered_country census is no longer behind its lock")
        body = _flat(gated[0])
        self.assertIn("limit = { NOT = { has_global_variable = iw_max_ic_lock } }", body)
        days = re.search(r"set_global_variable = \{ name = iw_max_ic_lock value = yes days = (\d+) \}", body)
        self.assertIsNotNone(days)
        # Journal entries pulse together on the 1st, and February has 28 days: a lock of 28 days set on
        # 1 February is a race on 1 March, and a longer one skips March's census.
        self.assertLessEqual(int(days.group(1)), 27)
        self.assertNotIn("ordered_country", _flat(pulse).replace(body, ""))

    def test_only_the_display_reads_the_maximum(self):
        """A month-old maximum is fine for a panel; it would not be for a rule that decides anything.

        Every script value that reads global_max_ic, directly or through another such value, is followed to
        its readers: none may be read by script outside the script values (an effect, a trigger, an AI weight,
        an event), only by the interface and localization."""
        # Each script value's words, a `var:`/`global_var:` read left out and a `scope.` path step kept; one pass per file.
        words = {}
        for path in sorted((ROOT / "common" / "script_values").glob("*.txt")):
            text = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))
            for block in re.split(r"(?m)^(?=\w+ = \{)", text):
                head = re.match(r"(\w+) = \{", block)
                if head:
                    body = block[head.end():]
                    words[head.group(1)] = (set(re.findall(r"(?<![\w:])\w+", body)),
                                            "global_var:global_max_ic" in body)
        tainted = {name for name, (_, direct) in words.items() if direct}
        while True:
            more = {name for name, (used, _) in words.items() if name not in tainted and used & tainted}
            if not more:
                break
            tainted |= more
        self.assertIn("intelligence_capacity_relative", tainted)
        self.assertIn("covert_disp_standing_code", tainted)
        for sub in ("common", "events"):
            for path in sorted((ROOT / sub).rglob("*.txt")):
                if path.parent.name == "script_values":
                    continue
                text = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))
                rel = path.relative_to(ROOT).as_posix()
                with self.subTest(file=rel):
                    if path.name != "je_covert_warfare.txt":
                        self.assertNotIn("global_var:global_max_ic", text)
                    used = set(re.findall(r"(?<![\w:])\w+", text))
                    self.assertEqual(used & tainted, set())


class CulturalHegemonyMilestones(unittest.TestCase):
    """The milestone events read the live share; the entry tries them only where they could pass."""

    EVENTS = "events/cultural_hegemony_events.txt"

    def _pulse_gate(self, event_id: str) -> str:
        pulse = _monthly_effect("common/journal_entries/je_cultural_hegemony.txt", "je_cultural_hegemony")
        gates = [b for b in _direct_blocks(pulse, "if") if f"id = {event_id} " in _flat(b) + " "]
        self.assertEqual(len(gates), 1, f"{event_id} is not tried behind one gate")
        # And nowhere else in the pulse, ungated.
        self.assertEqual(len(re.findall(rf"id = {re.escape(event_id)}(?![\w.])", _flat(pulse))), 1,
                         f"{event_id} is tried more than once in the pulse")
        return _flat(field(gates[0], "limit"))

    def _trigger(self, event_id: str) -> str:
        return _flat(field(entry_text(_read(self.EVENTS), event_id), "trigger"))

    def test_8_is_tried_below_its_threshold(self):
        trigger = self._trigger("cultural_hegemony.8")
        threshold = float(re.search(r"cultural_pull_total >= ([\d.]+)", trigger).group(1))
        gate = self._pulse_gate("cultural_hegemony.8")
        floor = re.search(r"var:ch_total >= ([\d.]+)", gate)
        self.assertIsNotNone(floor)
        self.assertIn("has_variable = ch_total", gate)
        # Well under: the cache is up to a month old, and the event re-checks the live share.
        self.assertLessEqual(float(floor.group(1)), threshold / 2)

    def test_9_gate_is_part_of_its_own_trigger(self):
        """Every condition of the gate is one the event's trigger holds, so the gate changes nothing."""
        trigger = self._trigger("cultural_hegemony.9")
        for condition in ("has_global_variable = ch_rank_1", "exists = global_var:ch_rank_1",
                          "THIS = global_var:ch_rank_1"):
            self.assertIn(condition, trigger)
        self.assertEqual(self._pulse_gate("cultural_hegemony.9"),
                         "has_global_variable = ch_rank_1 exists = global_var:ch_rank_1 "
                         "THIS = global_var:ch_rank_1")

    def test_the_cache_is_the_live_share(self):
        update = _flat(entry_text(_read("common/scripted_effects/cultural_hegemony_effects.txt"),
                                  "ch_monthly_country_update"))
        self.assertIn("set_variable = { name = ch_total value = cultural_pull_total }", update)


class SolStrataShifts(unittest.TestCase):
    """Each class's shift reads global_average_sol, a pass over every country: read it once per class."""

    def test_each_shift_value_is_read_once(self):
        body = _flat(entry_text(_read("common/scripted_effects/sol_expectations_effects.txt"),
                                "sol_expectations_apply_strata_shifts"))
        for cls in ("upper", "middle", "lower"):
            value = f"sol_expectations_{cls}_shift_value"
            var = f"sol_expectations_{cls}_shift_applied"
            with self.subTest(cls=cls):
                self.assertEqual(body.count(value), 1)
                self.assertIn(f"set_variable = {{ name = {var} value = {value} }}", body)
                self.assertIn(f"var:{var} > 0.1 var:{var} < -0.1", body)
                self.assertIn(f"multiplier = var:{var}", body)
                # Set before the old copy goes, as the value was read before: removing a modifier isn't seen
                # in the same block, so the order changes nothing, but keep it.
                self.assertLess(body.index(f"name = {var}"),
                                body.index(f"remove_modifier = sol_expectations_{cls}_strata_shift"))

    def test_the_variables_are_never_removed(self):
        """The multiplier may be read again after the call (scripting_best_practices.md)."""
        for sub in ("common", "events"):
            for path in sorted((ROOT / sub).rglob("*.txt")):
                text = path.read_text(encoding="utf-8-sig")
                self.assertNotRegex(text, r"remove_variable\s*=\s*(\{\s*name\s*=\s*)?sol_expectations_\w+_shift_applied",
                                    path.name)


if __name__ == "__main__":
    unittest.main()
