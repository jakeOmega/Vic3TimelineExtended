"""Every crisis dispute at every site that branches on it (2026-10-28 rework
spec §8.5, phase 4b).

A dispatcher that lacks a code falls back without a word: the yield's `else`
stands the target down as if the dispute were an alert (5), the preview calls
it an alert, the custom loc blocks print dispute 5's texts and the yield lines
print nothing. DISPUTES is the one table of codes; each site below must name
every code in it. A new code goes into DISPUTES first, which fails every site
that doesn't have it yet.
"""

import re
import unittest

from test_nuclear_deterrence import (
    CRISIS_EFFECTS,
    CUSTOM_LOC,
    TRIGGERS,
    block,
    loc_value,
    read,
    strip_comments,
)

from pathlib import Path

ROOT = Path(__file__).resolve().parent
CRISIS_EVENTS = ROOT / "events/nuclear_crisis_events.txt"
BUILDINGS = ROOT / "common/buildings/extra_buildings.txt"

# (code, the dispute's trigger, a word every prose list of disputes uses,
#  the preview's "over" key, the yield line's key), in classification order
# (spec §8.5: 2, 1, 3, 6, 4, 7, 8, 9, 10, 5). Dispute 5 is the classifier's
# and the preview's `else`.
DISPUTES = [
    (2, "nd_dispute_war_with", "war", "nd_tt_open_over_war", "nd_tt_yield_war"),
    (1, "nd_dispute_play_with", "play", "nd_tt_open_over_play", "nd_tt_yield_play"),
    (3, "nd_dispute_guarantee_against", "guarantee", "nd_tt_open_over_guarantee", "nd_tt_yield_guarantee"),
    (6, "nd_dispute_peacetime_strike_by", "nuclear strike", "nd_tt_open_over_peacetime_strike", "nd_tt_yield_reparations"),
    (4, "nd_dispute_proliferation_by", "weapons program", "nd_tt_open_over_proliferation", "nd_tt_yield_freeze"),
    (8, "nd_dispute_claims_by", "claims", "nd_tt_open_over_claims", "nd_tt_yield_claims"),
    (10, "nd_dispute_orbital_by", "orbital", "nd_tt_open_over_orbital", "nd_tt_yield_orbital"),
    (5, "nd_dispute_alert_by", "alert", "nd_tt_open_over_alert", "nd_tt_yield_alert"),
]
CODES = [d[0] for d in DISPUTES]
FALLBACK = 5
# Codes whose concession is a branch of its own in nd_crisis_act_yield (1–3 go
# through the play and war concessions, 5 is the else).
OWN_YIELD_BRANCH = [c for c in CODES if c not in (1, 2, 3, FALLBACK)]
# Codes from the 2026-10-28 rework on: they carry their own loc keys, the AI's
# warning names them, and their yields are self-checked.
NEW_CODES = [c for c in CODES if c >= 6]
SELF_CHECKED = [c for c in CODES if c >= 7]
# The issuer is defending, whatever the details (spec §9, rulings R9).
DEFENSIVE = [c for c in CODES if c in (3, 6, 7, 8, 9)]

CUSTOM_BLOCKS = {
    "nd_crisis_dispute_phrase": ("nd_crisis_dispute_phrase_{}",),
    "nd_crisis_dispute_word": ("nd_crisis_dispute_{}",),
    "nd_crisis_demand_text": ("nd_crisis_demand_{}",),
    "nd_crisis_concession_past": ("nd_concession_past_they_{}", "nd_concession_past_we_{}"),
    "nd_crisis_concession_short": ("nd_concession_short_{}",),
    "nd_crisis_concession_long": ("nd_concession_long_{}",),
}


def dispute_var(code):
    return re.compile(r"var:nd_crisis_dispute = " + str(code) + r"\b")


def dispute_is(code):
    return re.compile(r"nd_crisis_dispute_is = \{ D = " + str(code) + r" \}")


class TestDispatchers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.crisis = strip_comments(read(CRISIS_EFFECTS))
        cls.triggers = strip_comments(read(TRIGGERS))
        cls.custom = strip_comments(read(CUSTOM_LOC))

    def test_classification_order(self):
        body = block(self.crisis, "nd_crisis_classify_dispute")
        writes = [int(n) for n in re.findall(r"name = nd_crisis_dispute value = (\d+)", body)]
        self.assertEqual(writes, CODES)
        self.assertIn(f"name = nd_crisis_dispute value = {FALLBACK}", block(body, "else"))
        order = [body.index(d[1]) for d in DISPUTES if d[0] != FALLBACK]
        self.assertEqual(order, sorted(order))

    def test_preview_order(self):
        body = block(self.crisis, "nd_crisis_preview")
        order = [body.index(d[1] + " = { TARGET = $TARGET$ }") for d in DISPUTES if d[0] != FALLBACK]
        self.assertEqual(order, sorted(order))
        for code, trigger, _word, open_key, _yield in DISPUTES:
            if code != FALLBACK:
                i = body.index(trigger + " = { TARGET = $TARGET$ }")
                self.assertIn("custom_tooltip = " + open_key, body[i:i + 200], code)
        self.assertRegex(body, r"else = \{\s*custom_tooltip = nd_tt_open_over_alert")

    def test_revalidation_names_every_code(self):
        body = block(self.crisis, "nd_crisis_revalidate_dispute")
        for code in CODES:
            self.assertRegex(body, dispute_var(code), code)

    def test_yield_names_every_code(self):
        body = block(self.crisis, "nd_crisis_act_yield")
        for code in OWN_YIELD_BRANCH:
            self.assertRegex(body, dispute_var(code), code)
        lines = block(self.crisis, "nd_crisis_yield_lines")
        for code, _trigger, _word, _open, yield_key in DISPUTES:
            m = dispute_is(code).search(lines)
            self.assertIsNotNone(m, code)
            self.assertIn("custom_tooltip = " + yield_key, lines[m.end():m.end() + 120], code)

    def test_custom_loc_names_every_code(self):
        for name, patterns in CUSTOM_BLOCKS.items():
            body = block(self.custom, name)
            for code in CODES:
                for pattern in patterns:
                    self.assertRegex(body, r"localization_key = " + pattern.format(code) + r"\b", f"{name} {code}")

    def test_eligibility_names_every_dispute(self):
        body = block(self.triggers, "nd_has_crisis_dispute_with")
        for _code, trigger, *_ in DISPUTES:
            self.assertIn(trigger + " = { TARGET = $TARGET$ }", body)

    def test_defensive_codes(self):
        body = block(self.triggers, "nd_crisis_issuer_is_defensive")
        for code in CODES:
            if code in DEFENSIVE:
                self.assertRegex(body, dispute_var(code), code)
            elif code not in (1, 2):
                self.assertNotRegex(body, dispute_var(code), code)

    def test_ai_warning_names_every_new_dispute(self):
        body = block(self.triggers, "nd_ai_would_warn")
        for code, trigger, *_ in DISPUTES:
            if code in NEW_CODES:
                self.assertIn(trigger + " = { TARGET = $TARGET$ }", body, code)

    def test_loc_keys_exist(self):
        for code, _trigger, _word, open_key, yield_key in DISPUTES:
            for key in (open_key, yield_key):
                self.assertTrue(loc_value(key), key)
            if code in NEW_CODES:
                for pattern in sum(CUSTOM_BLOCKS.values(), ()):
                    self.assertTrue(loc_value(pattern.format(code)), pattern.format(code))

    def test_prose_lists_name_every_dispute(self):
        for key in ("nd_tt_has_dispute", "nd_w_crisis_actions_legend"):
            text = loc_value(key)
            for code, _trigger, word, *_ in DISPUTES:
                self.assertIn(word, text, f"{key}: {code}")


class TestConcessionCheck(unittest.TestCase):
    """A once-a-game TE_SELF_CHECK a day after each new concession: does the
    dispute still hold? Scheduled only when it held at the yield, so a yield
    with nothing to remove can't pass for OK."""

    @classmethod
    def setUpClass(cls):
        cls.crisis = strip_comments(read(CRISIS_EFFECTS))
        cls.events = strip_comments(read(CRISIS_EVENTS))

    def test_the_schedule(self):
        body = block(self.crisis, "nd_crisis_concession_check_schedule")
        for needle in ("NOT = { has_global_variable = nd_cc_done_$CODE$ }", "set_global_variable = nd_cc_done_$CODE$",
                       "name = nd_cc_target value = scope:nd_target days = 10", "name = nd_cc_code value = $CODE$ days = 10",
                       "trigger_event = { id = nuclear_crisis.26 days = 1 }"):
            self.assertIn(needle, body)

    def test_the_event(self):
        event = block(self.events, "nuclear_crisis.26")
        self.assertIn("hidden = yes", event)
        self.assertIn("has_variable = nd_cc_target", block(event, "trigger"))
        immediate = block(event, "immediate")
        # The record goes last: every branch reads var:nd_cc_code.
        cleared = immediate.index("remove_variable = nd_cc_target")
        self.assertIn("remove_variable = nd_cc_code", immediate[cleared:])
        for code in SELF_CHECKED:
            self.assertLess(immediate.index(f"var:nd_cc_code = {code}"), cleared, code)
            trigger = next(d[1] for d in DISPUTES if d[0] == code)
            i = immediate.index(f"var:nd_cc_code = {code}")
            branch = immediate[i:i + 900]
            self.assertIn(trigger + " = { TARGET = scope:nd_cc_target }", branch, code)
            self.assertIn(f"TE_SELF_CHECK BROKEN nd_concession_{code}:", branch, code)
            self.assertIn(f"TE_SELF_CHECK OK nd_concession_{code}:", branch, code)

    def test_concession_selfcheck_skips_an_empty_yield(self):
        body = block(self.crisis, "nd_crisis_act_yield")
        for code in SELF_CHECKED:
            trigger = next(d[1] for d in DISPUTES if d[0] == code)
            i = dispute_var(code).search(body).end()
            branch = body[i:i + 600]
            call = branch.index(f"nd_crisis_concession_check_schedule = {{ CODE = {code} }}")
            guard = branch.rfind("limit = { " + trigger + " = { TARGET = scope:nd_target } }", 0, call)
            self.assertGreaterEqual(guard, 0, code)
            self.assertLess(call, branch.index("nd_crisis_concede_"), code)


def squash(text):
    return re.sub(r"\s+", " ", text).strip()


class TestClaims(unittest.TestCase):
    """Dispute 8: the target claims one of our incorporated states. Conceding
    renounces each such claim; claims can't be renewed at will, so there is
    no bar, and the dispute ends when none is left (rulings R7)."""

    @classmethod
    def setUpClass(cls):
        cls.crisis = strip_comments(read(CRISIS_EFFECTS))
        cls.triggers = strip_comments(read(TRIGGERS))

    def test_trigger_reads_the_region(self):
        body = squash(block(self.triggers, "nd_dispute_claims_by"))
        self.assertIn("any_scope_state = { is_incorporated = yes state_region = { $TARGET$ = { has_claim = PREV } } }", body)
        self.assertNotIn("has_claim_by", body)

    def test_concession_removes_on_the_region(self):
        body = squash(block(self.crisis, "nd_crisis_concede_claims"))
        self.assertIn("every_scope_state = { limit = { is_incorporated = yes state_region = { scope:nd_target = { has_claim = PREV } } }"
                      " state_region = { remove_claim = scope:nd_target } }", body)
        self.assertNotIn("set_variable", body)

    def test_claims_concession_names_the_whole_region(self):
        for key in ("nd_concession_long_8", "nd_tt_yield_claims", "nd_tt_open_over_claims"):
            self.assertIn("region", loc_value(key), key)

    def test_revalidate_closes_when_no_claim_is_left(self):
        body = block(self.crisis, "nd_crisis_revalidate_dispute")
        i = dispute_var(8).search(body).start()
        branch = squash(body[i:i + 700])
        self.assertIn("has_war_with = scope:nd_target } set_variable = { name = nd_crisis_dispute value = 2 }", branch)
        self.assertIn("NOT = { nd_dispute_claims_by = { TARGET = scope:nd_target } } } nd_crisis_close = { OUTCOME = 10 }", branch)

    def test_ai_warns_only_against_a_rival(self):
        body = squash(block(self.triggers, "nd_ai_would_warn"))
        i = body.index("nd_dispute_claims_by")
        rival = body.rfind("has_diplomatic_pact = { who = $TARGET$ type = rivalry }", 0, i)
        self.assertGreaterEqual(rival, 0)
        self.assertEqual(body.count("nd_dispute_claims_by"), 1)


class TestOrbital(unittest.TestCase):
    """Dispute 10: the target is building an Orbital Battlestation, which
    gives every state its owner holds nuclear defense. Conceding tears the
    construction site down with its progress and freezes new sites for ten
    years; finished levels stay."""

    @classmethod
    def setUpClass(cls):
        cls.crisis = strip_comments(read(CRISIS_EFFECTS))
        cls.triggers = strip_comments(read(TRIGGERS))

    def test_trigger_reads_the_site(self):
        body = squash(block(self.triggers, "nd_dispute_orbital_by"))
        self.assertIn("$TARGET$ = { any_scope_state = { has_building = building_orbital_battlestation_construction_site } }", body)

    def test_concession_removes_site_and_progress(self):
        body = squash(block(self.crisis, "nd_crisis_concede_orbital"))
        self.assertIn("every_scope_state = { limit = { has_building = building_orbital_battlestation_construction_site }"
                      " set_variable = { name = orbital_battlestation_progress_var value = 0 }"
                      " remove_building = building_orbital_battlestation_construction_site }", body)
        self.assertNotIn("building_orbital_battlestation }", body)

    def test_freeze_is_ten_years_and_read_by_the_site(self):
        body = squash(block(self.crisis, "nd_crisis_concede_orbital"))
        self.assertIn("set_variable = { name = nd_crisis_orbital_freeze value = scope:nd_issuer days = 3650 }", body)
        site = squash(block(block(strip_comments(read(BUILDINGS)),
                                  "REPLACE_OR_CREATE:building_orbital_battlestation_construction_site"), "possible"))
        self.assertIn("custom_tooltip = { text = nd_tt_orbital_frozen owner = { NOT = { has_variable = nd_crisis_orbital_freeze } } }", site)
        self.assertTrue(loc_value("nd_tt_orbital_frozen"))

    def test_not_defensive(self):
        self.assertNotRegex(block(self.triggers, "nd_crisis_issuer_is_defensive"), dispute_var(10))

    def test_ai_great_power_only(self):
        body = squash(block(self.triggers, "nd_ai_would_warn"))
        self.assertIn("AND = { nd_dispute_orbital_by = { TARGET = $TARGET$ } country_rank >= rank_value:great_power }", body)
        self.assertEqual(body.count("nd_dispute_orbital_by"), 1)

    def test_finished_levels_stay(self):
        for key in ("nd_concession_long_10", "nd_tt_yield_orbital"):
            self.assertIn("levels", loc_value(key).lower(), key)

    def test_revalidate_only_a_war(self):
        # A site torn down by the target itself can go up again at once, so
        # it doesn't end the crisis (rulings R7).
        body = squash(block(self.crisis, "nd_crisis_revalidate_dispute"))
        self.assertIn("else_if = { limit = { var:nd_crisis_dispute = 10 } if = { limit = { has_war_with = scope:nd_target }"
                      " set_variable = { name = nd_crisis_dispute value = 2 } } }", body)


if __name__ == "__main__":
    unittest.main()
