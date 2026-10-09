# -*- coding: utf-8 -*-
"""The tax code's test console (events/te_tax_debug_events.txt, plan Tasks 22
and 25; runbook docs/testing/tax-code-playtest.md).

Vic3's console has no `effect` command, so test setup runs as `event <id>`.
These events must stay console-only: nothing in the mod fires them, each is
gated on the game rule, and the setup events reach the code through the same
commands and transitions the game uses, so a scenario they set up is one the
game can reach.

Run: python3 -m unittest test_tax_code_console -v
"""

import re
import unittest
from pathlib import Path

from test_tax_code_state import block, read

ROOT = Path(__file__).resolve().parent
EVENTS = "events/te_tax_debug_events.txt"
SETUP = ("te_tax_debug.5", "te_tax_debug.6", "te_tax_debug.7", "te_tax_debug.8")
NATIVE_SETTERS = ("add_amendment", "remove_amendment", "set_tax_level", "add_taxed_goods",
                  "remove_taxed_goods", "set_import_tariff_level", "set_export_tariff_level",
                  "activate_law")


class ConsoleEventTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(EVENTS)

    def test_every_console_event_is_hidden_rule_gated_and_marked_console_only(self):
        ids = re.findall(r"(?m)^(te_tax_debug\.\d+) = \{(.*)$", read(EVENTS, strip_comments=False))
        self.assertGreaterEqual(len(ids), 5)
        for event_id, tail in ids:
            self.assertIn("REVIEWED", tail, event_id)
            body = block(self.text, event_id)
            self.assertIn("hidden = yes", body, event_id)
            # .9 and .10 test the light code (te_tax_code_light_on); the rest the full one.
            gate = "te_tax_code_light_on" if event_id in ("te_tax_debug.9", "te_tax_debug.10") else "te_tax_code_full"
            self.assertIn(f"trigger = {{ {gate} = yes }}", body, event_id)

    def test_nothing_fires_a_console_event(self):
        pattern = re.compile(r"\bte_tax_debug\.\d+")
        for folder in ("common", "events", "gui"):
            for path in sorted((ROOT / folder).rglob("*")):
                if path.suffix not in {".txt", ".gui"} or path.name == "te_tax_debug_events.txt":
                    continue
                self.assertIsNone(pattern.search(path.read_text(encoding="utf-8-sig")), str(path))

    def test_setup_events_need_the_code_in_force_and_write_no_native_state(self):
        for event_id in SETUP:
            body = block(self.text, event_id)
            self.assertIn("te_tax_code_in_force = yes", body, event_id)
            for setter in NATIVE_SETTERS:
                self.assertNotRegex(body, rf"\b{setter}\b", f"{event_id}: {setter}")

    def test_the_test_bill_goes_through_the_commands_behind_their_triggers(self):
        body = block(self.text, "te_tax_debug.5")
        for command in ("draft_discard", "draft_new", "draft_step", "draft_due", "introduce"):
            for m in re.finditer(rf"te_tax_cmd_{command}\b", body):
                guard = body[max(0, m.start() - 120):m.start()]
                self.assertIn(f"te_tax_can_{command}", guard, command)
        # The one shortcut: a 1-month expiry (no control offers it), then the
        # pass sequence, whose store still checks the bill.
        self.assertIn("set_variable = { name = te_tax_bl_wage_sun value = 1 }", body)
        self.assertIn("te_tax_pass_into = { SLOT = a OTHER = b }", body)
        self.assertIn("te_tax_pass_into = { SLOT = b OTHER = a }", body)

    def test_the_dispatch_skip_claims_only_next_month(self):
        body = block(self.text, "te_tax_debug.6")
        self.assertEqual(re.findall(r"name = (te_tax_\w+)", body), ["te_tax_last_month"])
        self.assertIn("value = te_tax_due_earliest", body)

    def test_the_outside_change_bumps_only_the_wage_external_version(self):
        body = block(self.text, "te_tax_debug.7")
        self.assertEqual(re.findall(r"name = (te_tax_\w+)", body), ["te_tax_xver_wage"])

    def test_the_relief_setup_caps_the_list_at_three_and_syncs_tomorrow(self):
        body = block(self.text, "te_tax_debug.8")
        self.assertIn("count >= 3", body)
        self.assertIn("change_variable = { name = te_tax_xver_relief add = 1 }", body)
        self.assertIn("trigger_event = { id = te_tax.4 days = 1 }", body)
        self.assertNotIn("remove_variable", body)


AI_CONSOLE = ("te_tax_debug.2", "te_tax_debug.3", "te_tax_debug.4")
AI_EFFECTS = "common/scripted_effects/te_tax_ai_effects.txt"
SCHEDULE = "common/scripted_effects/te_tax_schedule_effects.txt"


class AiConsoleTest(unittest.TestCase):
    """Plan Task 22: the AI's console options and its yearly summary."""

    @classmethod
    def setUpClass(cls):
        cls.text = read(EVENTS)

    def test_the_ai_console_runs_the_managers_never_the_step_or_te_tax_8(self):
        body = block(self.text, "te_tax_debug.2")
        self.assertIn("te_tax_code_in_force = yes", body)
        self.assertIn("NOT = { is_country_type = decentralized }", body)
        order = [body.index(s) for s in ("te_tax_ai_manage_packages = yes", "te_tax_ai_manage_promises = yes",
                                         "te_tax_ai_manage_bill = yes", "te_tax_ai_initiative = yes")]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("te_tax_ai_step = yes", body)
        self.assertNotIn("te_tax.8", self.text)

    def test_only_the_step_and_the_console_run_the_managers(self):
        # Task 19 review minor 3: a manager run from events/ on a player country would
        # enact or renegotiate for the player; only the console may do that.
        for manager in ("te_tax_ai_manage_packages", "te_tax_ai_manage_promises",
                        "te_tax_ai_manage_bill", "te_tax_ai_initiative"):
            callers = set()
            for folder in ("common", "events"):
                for path in sorted((ROOT / folder).rglob("*.txt")):
                    if re.search(rf"\b{manager} = yes", read(path.relative_to(ROOT).as_posix())):
                        callers.add(path.name)
            self.assertEqual(callers, {"te_tax_ai_effects.txt", "te_tax_debug_events.txt"}, manager)

    def test_the_signals_option_only_logs(self):
        body = block(self.text, "te_tax_debug.3")
        self.assertNotRegex(body, r"set_variable|change_variable|te_tax_cmd_|te_tax_ai_manage")
        for key in ("wage", "div", "land", "head", "cons"):
            self.assertIn(f"te_tax_ai_cost_{key}", body)

    def test_the_streak_option_writes_only_the_need_streak_the_cooldown_and_the_marker(self):
        body = block(self.text, "te_tax_debug.4")
        self.assertEqual(sorted(re.findall(r"name = (te_tax_\w+)", body)),
                         ["te_tax_ai_def_streak", "te_tax_ai_next_month", "te_tax_ai_noviable"])
        self.assertIn("set_variable = { name = te_tax_ai_noviable value = 0 }", body)

    def test_the_yearly_summary_is_ai_only_in_january_from_the_processor(self):
        effect = block(read(AI_EFFECTS), "te_tax_ai_log_year")
        self.assertIn("te_tax_code_full = yes", effect)
        self.assertIn("is_ai = yes", effect)
        self.assertIn("te_tax_ai_month_of_year = 0", effect)
        self.assertIn("TE_TAX ai_year", effect)
        body = block(read(SCHEDULE), "te_tax_process_month")
        self.assertLess(body.index("te_tax_ai_dispatch = yes"), body.index("te_tax_ai_log_year = yes"))
        self.assertLess(body.index("te_tax_ai_log_year = yes"), body.index("te_tax_gen_sunset_wage = yes"))


SCHEMA_DOC = "docs/systems/tax_code_schema.md"


class DebugTagIndexTest(unittest.TestCase):
    """Plan Task 25: the schema doc's "Debug-line index" lists every TE_TAX tag the
    script writes, and nothing it no longer writes, so the play-test can read
    debug.log from the doc."""

    def test_every_tag_written_is_indexed_and_every_indexed_tag_is_written(self):
        written = set()
        for folder in ("common", "events"):
            for path in sorted((ROOT / folder).rglob("*.txt")):
                written |= set(re.findall(r'debug_log = "TE_TAX ([a-z_]+)', path.read_text(encoding="utf-8-sig")))
        doc = (ROOT / SCHEMA_DOC).read_text(encoding="utf-8")
        start = doc.index("### Debug-line index")
        section = doc[start:doc.index("\n### ", start + 1)]
        indexed = set(re.findall(r"(?m)^\| `([a-z_]+)` \|", section))
        self.assertEqual(sorted(written - indexed), [], "tags written but not in the index")
        self.assertEqual(sorted(indexed - written), [], "tags in the index no longer written")


if __name__ == "__main__":
    unittest.main()
