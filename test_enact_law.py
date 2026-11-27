# -*- coding: utf-8 -*-
"""enact_law on six event options, with a one-day fallback (#1443).

Vanilla 1.15's enact_law passes a law as a successful enactment (on_enact, movement loyalists, interest group
approval), where activate_law only switches it. Whether it respects can_enact, passes the law at once and copes with
an enactment already running is unverified (vanilla_1_15_prep.md C20), so each of the six options calls
te_enact_law_checked (common/scripted_effects/te_enact_law_effects.txt), which queues te_enact_law.1 (or .2 when an
enactment was already running) a day on: its te_enact_law_check activates the law as before if enact_law did not pass it, and logs TE_SELF_CHECK OK|BROKEN enact_law.
Play-test row: docs/testing/vanilla-1-15-playtest.md, "Panels and systems".
"""

import re
import unittest

from test_decolonization_wars import _block, _close, _def, _raw, _read

EFFECTS = _read("common", "scripted_effects", "te_enact_law_effects.txt")
EVENTS = _read("events", "te_enact_law_events.txt")
VALUES = _read("common", "script_values", "te_enact_law_values.txt")
PLAYTEST = _raw("docs", "testing", "vanilla-1-15-playtest.md")

# option -> the laws it passes, in file order
SITES = {
    ("cultural_hegemony_events.txt", "cultural_hegemony.16", "cultural_hegemony.16.a"):
        ["scope:ch_pressure_law_type"],
    ("extra_law_events.txt", "extra_law_events.36", "extra_law_events.36.b"):
        ["law_type:law_traditional_family_structure", "law_type:law_freedom_of_conscience",
         "law_type:law_interventionism", "law_type:law_interventionism", "law_type:law_homesteading"],
    ("decolonization_events.txt", "decolonization_events.75", "decolonization_events.75.a"):
        ["law_type:law_universal_suffrage", "law_type:law_parliamentary_republic"],
    ("decolonization_events.txt", "decolonization_events.75", "decolonization_events.75.c"):
        ["law_type:law_presidential_republic"],
    ("te_judiciary_events.txt", "te_judiciary_events.5", "te_judiciary_events.5.a"):
        ["law_type:law_statutory_courts"],
    ("te_peg_events.txt", "te_peg.3", "te_peg.3.b"):
        ["law_type:law_fiat_currency"],
}


def _options(event):
    """Each `option = { ... }` of an event's body, by its name."""
    out = {}
    for m in re.finditer(r"(?<![\w.])option\s*=\s*\{", event):
        body = event[m.end():_close(event, m.end() - 1)]
        out[re.search(r"name\s*=\s*(\S+)", body).group(1)] = body
    return out


class CallSiteTests(unittest.TestCase):
    def test_each_option_passes_its_laws_through_the_check(self):
        for (file, event, option), laws in SITES.items():
            with self.subTest(option=option):
                body = _options(_def(_read("events", file), event))[option]
                self.assertNotIn("activate_law", body)
                self.assertNotIn("enact_law =", body)
                self.assertEqual(re.findall(r"te_enact_law_checked\s*=\s*\{\s*LAW\s*=\s*(\S+)\s*\}", body), laws)

    def test_no_other_site_calls_the_check(self):
        """The check's fallback is activate_law, which is what these six did before: a new caller is a decision of
        its own, so it is added here on purpose."""
        import os
        root = os.path.dirname(os.path.abspath(__file__))
        callers = set()
        for folder in ("events", os.path.join("common", "scripted_effects"), os.path.join("common", "decisions"),
                       os.path.join("common", "scripted_buttons"), os.path.join("common", "journal_entries")):
            for name in os.listdir(os.path.join(root, folder)):
                if name.endswith(".txt") and re.search(r"te_enact_law_checked\s*=\s*\{\s*LAW\b", _read(*folder.split(os.sep), name)):
                    callers.add(name)
        self.assertEqual(callers, {file for file, _event, _option in SITES})


class CheckTests(unittest.TestCase):
    def test_the_check_is_queued_before_enact_law_and_only_for_a_law_not_held(self):
        effect = _def(EFFECTS, "te_enact_law_checked")
        hidden = _block(effect, "hidden_effect")
        self.assertLess(effect.index("hidden_effect"), effect.index("enact_law = $LAW$"))
        guard = _block(hidden, "if")
        self.assertIn("NOT = { has_law = $LAW$ }", _block(guard, "limit"))
        self.assertIn("$LAW$ = { save_scope_as = te_enact_law }", guard)
        # which event records whether an enactment was running at the call
        running = _block(guard, "if")
        self.assertIn("enacting_any_law = yes", _block(running, "limit"))
        self.assertIn("trigger_event = { id = te_enact_law.2 days = 1 }", running)
        self.assertIn("trigger_event = { id = te_enact_law.1 days = 1 }", _block(guard, "else"))
        # enact_law itself stays outside hidden_effect, so the option's tooltip shows it
        self.assertNotIn("enact_law =", hidden)

    def test_the_events_take_no_trigger_and_pass_what_ran_before(self):
        for event_id, before in (("te_enact_law.1", 0), ("te_enact_law.2", 1)):
            with self.subTest(event=event_id):
                event = _def(EVENTS, event_id)
                self.assertIn("hidden = yes", event)
                self.assertNotRegex(event, r"(?<![\w.])trigger\s*=\s*\{")
                self.assertEqual(_block(event, "immediate").split(),
                                 ["te_enact_law_check", "=", "{", "BEFORE", "=", str(before), "}"])

    def test_the_check_falls_back_to_activate_law(self):
        check = _def(EFFECTS, "te_enact_law_check")
        self.assertIn("exists = scope:te_enact_law", _block(check, "limit"))
        fallback = _block(check, "else")
        self.assertIn("activate_law = scope:te_enact_law", fallback)
        cancel = fallback.index("cancel_enactment = yes")
        self.assertLess(cancel, fallback.index("activate_law = scope:te_enact_law"))
        self.assertIn("is_enacting_law = scope:te_enact_law", fallback[:cancel])

    def test_each_verdict_logs_once_a_game(self):
        check = _def(EFFECTS, "te_enact_law_check")
        for flag, verdicts in (("te_sc_enact_law_ok", ["TE_SELF_CHECK OK enact_law "]),
                               ("te_sc_enact_law_broken", ["TE_SELF_CHECK BROKEN enact_law started=yes ",
                                                           "TE_SELF_CHECK BROKEN enact_law started=no "])):
            with self.subTest(flag=flag):
                self.assertIn(f"NOT = {{ has_global_variable = {flag} }}", check)
                self.assertIn(f"set_global_variable = {flag}", check)
                for verdict in verdicts:
                    self.assertEqual(check.count(verdict), 1, verdict)
        self.assertEqual(check.count("enacting_before=$BEFORE$"), 3)
        self.assertIn("te_enact_law_enacting_now = {", VALUES)
        self.assertIn("THIS.ScriptValue('te_enact_law_enacting_now')", check)

    def test_the_play_test_list_names_the_check_and_its_fallback(self):
        self.assertIn("TE_SELF_CHECK OK|BROKEN enact_law", PLAYTEST)
        self.assertIn("#1443", PLAYTEST)

if __name__ == "__main__":
    unittest.main()
