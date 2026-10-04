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
            self.assertIn("trigger = { te_tax_code_on = yes }", body, event_id)

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


if __name__ == "__main__":
    unittest.main()
