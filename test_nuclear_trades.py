"""Crisis trades (2026-10-28 rework spec §8.6, phase 4c).

Either side of a crisis over deployment, claims, covert operations or orbital
weapons (disputes 7–10) can offer the matching concession of its own: a base
for a base, a claim for a claim. An accepted trade runs the existing
concession for the target, swaps the parties' saved scopes, runs it again for
the issuer, swaps them back, and closes the crisis as outcome 11, "Trade".
"""

import re
import unittest
from pathlib import Path

from test_nuclear_deterrence import (
    CRISIS_EFFECTS,
    CUSTOM_LOC,
    TRIGGERS,
    block,
    loc_value,
    option_body,
    read,
    strip_comments,
)

ROOT = Path(__file__).resolve().parent
CRISIS_EVENTS = ROOT / "events/nuclear_crisis_events.txt"
OBSERVER_EFFECTS = ROOT / "common/scripted_effects/nuclear_observer_effects.txt"

# nd_crisis_close's outcome codes, as the crisis effects' header lists them.
OUTCOMES = {
    1: "the target yielded", 2: "the issuer backed down", 3: "reciprocal stand-down",
    4: "the target backed down natively", 5: "the issuer's side backed down", 6: "the war ended",
    7: "nuclear use", 8: "expired", 9: "invalid", 10: "the dispute ended, no clear winner",
    11: "a trade",
}
TRADE = 11
# The disputes that trade, and the name their trigger and concession share
# (nd_dispute_<what>_by, nd_crisis_concede_<what>): the same-code mirrors
# (ruling R1). test_nuclear_disputes checks every code decides one way.
TRADES = {7: "deployment", 8: "claims", 9: "covert_ops", 10: "orbital"}
# 5's stand-down for a stand-down is outcome 3; 1–4 and 6 have no matching
# concession (4's target is unarmed, the issuer armed).
NO_TRADE = {1, 2, 3, 4, 5, 6}


def squash(text):
    return " ".join(text.split())


def tooltip_clause(body, key):
    """The custom_tooltip = { text = key … } block in body."""
    for m in re.finditer(r"custom_tooltip = \{", body):
        b = block(body[m.start():], "custom_tooltip")
        if re.match(r"\s*text = " + re.escape(key) + r"\s", b):
            return b
    raise AssertionError(f"no custom_tooltip for {key}")


def first_valid_keys(body):
    """(trigger text, desc key) for each triggered_desc of a first_valid, in order."""
    out = []
    for m in re.finditer(r"triggered_desc = \{", body):
        td = block(body[m.start():], "triggered_desc")
        out.append((block(td, "trigger"), re.search(r"\bdesc = ([\w.]+)", td).group(1)))
    return out


def outcome_branch(body, code):
    """The if/else_if of nd_crisis_apply_outcome_side whose limit tests outcome `code` alone."""
    for m in re.finditer(r"(?:else_if|if) = \{", body):
        branch = block(body[m.start():], "else_if" if body[m.start()] == "e" else "if")
        limit = block(branch, "limit")
        if re.fullmatch(r"\s*var:nd_crisis_pending_outcome = " + str(code) + r"\s*", limit):
            return branch
    raise AssertionError(f"no outcome branch for {code}")


class TestOutcomeEleven(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.events = strip_comments(read(CRISIS_EVENTS))
        self.custom = strip_comments(read(CUSTOM_LOC))

    def test_header_lists_eleven(self):
        header = read(CRISIS_EFFECTS).split("# TOOLTIP PASSES", 1)[0]
        self.assertRegex(header, r"#.*\b11 a trade\b")

    def test_log_names_every_outcome(self):
        body = block(read(OBSERVER_EFFECTS), "nd_log_crisis_end")
        for n in OUTCOMES:
            self.assertIn(f"var:nd_crisis_outcome_now = {n} }} }} debug_log = \"TE_NUCLEAR: type=crisis_end; outcome={n};", body, n)

    def test_trade_pays_five_each(self):
        branch = outcome_branch(block(self.effects, "nd_crisis_apply_outcome_side"), TRADE)
        self.assertRegex(branch, r"text = nd_tt_credibility_up_5\s*nd_change_credibility = \{ AMOUNT = 5 \}")
        self.assertEqual(branch.count("nd_change_credibility"), 1)
        self.assertNotIn("nd_crisis_pending_role", branch)
        self.assertNotIn("nd_crisis_climbdown", branch)
        self.assertNotIn("nd_crisis_bluff_called", branch)

    def test_notice_titles_and_describes_a_trade(self):
        body = block(self.events, "nuclear_crisis.6")
        for part, key in (("title", "nuclear_crisis.6.t_trade"), ("desc", "nuclear_crisis.6.d_trade")):
            pairs = first_valid_keys(block(body, part))
            keys = [k for _, k in pairs]
            self.assertIn(key, keys, part)
            trig = pairs[keys.index(key)][0]
            self.assertIn(f"O = {TRADE}", trig)
            self.assertLess(keys.index(key), len(keys) - 1, f"{part}: the trade must come before the fallback")

    def test_last_word_names_a_trade(self):
        body = block(self.custom, "nd_crisis_last_outcome_word")
        texts = [block(body[m.start():], "text") for m in re.finditer(r"\btext = \{", body)]
        hits = [t for t in texts if f"var:nd_crisis_last_outcome = {TRADE}" in t]
        self.assertEqual(len(hits), 1)
        self.assertIn("localization_key = nd_last_outcome_trade", hits[0])
        self.assertIn("always = yes", texts[-1])

    def test_outcome_loc_exists(self):
        for key in ("nuclear_crisis.6.t_trade", "nuclear_crisis.6.d_trade", "nd_last_outcome_trade"):
            self.assertTrue(loc_value(key), key)


class TestTradeOffer(unittest.TestCase):
    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.events = strip_comments(read(CRISIS_EVENTS))

    def test_holds_reads_both_directions(self):
        body = block(self.triggers, "nd_crisis_trade_holds")
        self.assertIn("exists = $ISSUER$", body)
        self.assertIn("exists = $TARGET$", body)
        ands = [block(body[m.start():], "AND") for m in re.finditer(r"\bAND = \{", body)]
        for code, what in TRADES.items():
            hit = [a for a in ands if re.search(r"var:nd_crisis_dispute = " + str(code) + r"\b", a)]
            self.assertEqual(len(hit), 1, code)
            self.assertIn(f"$ISSUER$ = {{ nd_dispute_{what}_by = {{ TARGET = $TARGET$ }} }}", squash(hit[0]))
            self.assertIn(f"$TARGET$ = {{ nd_dispute_{what}_by = {{ TARGET = $ISSUER$ }} }}", squash(hit[0]))
        for code in NO_TRADE:
            self.assertNotRegex(body, r"var:nd_crisis_dispute = " + str(code) + r"\b")

    def test_tradeable_names_the_trades(self):
        body = block(self.triggers, "nd_crisis_dispute_tradeable")
        self.assertEqual({int(c) for c in re.findall(r"nd_crisis_dispute_is = \{ D = (\d+) \}", body)}, set(TRADES))

    def test_holds_for_us_saves_both_parties(self):
        body = squash(block(self.triggers, "nd_crisis_trade_holds_for_us"))
        for role, me, other in (("owner", "nd_tr_issuer", "nd_tr_target"), ("target", "nd_tr_target", "nd_tr_issuer")):
            self.assertIn(f"nd_is_crisis_{role} = yes save_temporary_scope_as = {me} "
                          f"var:nd_crisis_opponent ?= {{ save_temporary_scope_as = {other} }} "
                          "nd_crisis_trade_holds = { ISSUER = scope:nd_tr_issuer TARGET = scope:nd_tr_target }", body)

    def test_one_proposal_at_a_time(self):
        gate = block(self.triggers, "nd_can_offer_trade")
        talks = block(self.triggers, "nd_can_propose_talks")
        self.assertEqual(squash(tooltip_clause(gate, "nd_tt_talks_pending")), squash(tooltip_clause(talks, "nd_tt_talks_pending")))
        self.assertIn("nd_in_crisis = yes", tooltip_clause(gate, "nd_tt_in_crisis"))
        self.assertIn("nd_crisis_dispute_tradeable = yes", tooltip_clause(gate, "nd_tt_trade_kind"))
        self.assertIn("nd_crisis_trade_holds_for_us = yes", tooltip_clause(gate, "nd_tt_trade_matching"))
        offer = block(self.effects, "nd_crisis_act_offer_trade")
        hidden = block(offer, "hidden_effect")
        self.assertIn("scope:nd_issuer = { set_variable = { name = nd_crisis_talks value = 1 } }", hidden)
        self.assertEqual(hidden.count("EVENT = nuclear_crisis.8 }"), 2)
        self.assertEqual(hidden.count("save_scope_as = nd_crisis_proposer"), 2)

    def test_offer_says_what_it_offers(self):
        offer = block(self.effects, "nd_crisis_act_offer_trade")
        visible = offer.split("hidden_effect", 1)[0]
        for line in ("custom_tooltip = nd_tt_act_trade", "nd_crisis_trade_lines = yes",
                     "custom_tooltip = nd_tt_trade_cred", "custom_tooltip = nd_tt_talks_meanwhile"):
            self.assertIn(line, visible)
        for key in ("nd_tt_act_trade", "nd_tt_trade_cred", "nd_tt_talks_meanwhile", "nd_tt_trade_kind",
                    "nd_tt_trade_matching", "nd_tt_act_accept_trade", "nd_tt_trade_lapsed"):
            self.assertTrue(loc_value(key), key)
        self.assertIn("trade", loc_value("nd_tt_talks_pending"))

    def test_offer_event(self):
        ev = block(self.events, "nuclear_crisis.8")
        self.assertIn("nd_crisis_event_matches = yes", block(ev, "trigger"))
        self.assertRegex(ev, r'event_image = \{ texture = "gfx/event_pictures/\w+\.dds" \}')
        accept = option_body(self.events, "nuclear_crisis.8.a")
        refuse = option_body(self.events, "nuclear_crisis.8.b")
        self.assertIn("nd_crisis_option = { ACT = accept_trade }", accept)
        self.assertIn("nd_crisis_option = { ACT = refuse_talks }", refuse)
        # R3: a concession takes a click; an unanswered offer lapses.
        self.assertIn("default_option = yes", refuse)
        self.assertNotIn("default_option", accept)
        for key in ("t", "d", "f", "a", "b"):
            self.assertTrue(loc_value(f"nuclear_crisis.8.{key}"), key)


class TestTradeAccept(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.accept = block(self.effects, "nd_crisis_act_accept_trade")
        self.hidden = block(self.accept, "hidden_effect")

    def test_accept_rechecks_both_halves(self):
        first = block(self.hidden, "if")
        self.assertIn("nd_crisis_trade_holds = { ISSUER = scope:nd_issuer TARGET = scope:nd_target }", block(first, "limit"))
        self.assertIn("nd_crisis_trade_halves", first)
        rest = self.hidden[self.hidden.index(first) + len(first):]
        self.assertIn("else_if", rest)
        lapse = block(rest, "else_if")
        self.assertIn("nd_is_crisis_owner = yes", block(lapse, "limit"))
        self.assertIn("set_variable = { name = nd_crisis_talks value = 0 }", lapse)
        self.assertNotIn("nd_crisis_trade_halves", lapse)
        self.assertNotIn("nd_crisis_close", lapse)
        visible = self.accept.split("hidden_effect", 1)[0]
        shown = block(visible, "if")
        self.assertIn("nd_crisis_trade_holds = { ISSUER = scope:nd_issuer TARGET = scope:nd_target }", block(shown, "limit"))
        self.assertIn("custom_tooltip = nd_tt_act_accept_trade", shown)
        self.assertIn("custom_tooltip = nd_tt_trade_lapsed", block(visible[visible.index(shown) + len(shown):], "else"))

    def test_swap_is_undone_before_close(self):
        swap = squash(block(self.effects, "nd_crisis_swap_parties"))
        self.assertEqual(swap, "scope:nd_issuer = { save_scope_as = nd_crisis_swap } "
                               "scope:nd_target = { save_scope_as = nd_issuer } "
                               "scope:nd_crisis_swap = { save_scope_as = nd_target }")
        halves = block(self.effects, "nd_crisis_trade_halves")
        swaps = [m.start() for m in re.finditer(r"nd_crisis_swap_parties = yes", halves)]
        concedes = [m.start() for m in re.finditer(r"scope:nd_issuer = \{ nd_crisis_concede_\$WHAT\$ = yes \}", halves)]
        self.assertEqual(len(swaps), 2)
        self.assertEqual(len(concedes), 2)
        self.assertLess(concedes[0], swaps[0])
        self.assertLess(swaps[0], concedes[1])
        self.assertLess(concedes[1], swaps[1])
        self.assertNotIn("nd_crisis_close", halves)
        self.assertLess(halves.index("nd_crisis_trade_check_schedule = { CODE = $CODE$ }"), concedes[0])
        close = self.hidden.index("nd_crisis_close = { OUTCOME = 11 }")
        self.assertLess(self.hidden.rindex("nd_crisis_trade_halves"), close)

    def test_dispatch_names_every_trade(self):
        for code, what in TRADES.items():
            self.assertRegex(self.hidden, r"var:nd_crisis_dispute = " + str(code) + r" \}\s*nd_crisis_trade_halves = \{ CODE = "
                             + str(code) + r" WHAT = " + what + r" \}")
        lines = block(self.effects, "nd_crisis_trade_lines")
        for code, what in TRADES.items():
            self.assertRegex(lines, r"nd_crisis_dispute_is = \{ D = " + str(code) + r" \} \}\s*custom_tooltip = nd_tt_trade_" + what + r"\b")
            self.assertTrue(loc_value(f"nd_tt_trade_{what}"), what)


class TestTradeSelfCheck(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.events = strip_comments(read(CRISIS_EVENTS))

    def test_schedule_once_a_game_per_code(self):
        body = block(self.effects, "nd_crisis_trade_check_schedule")
        self.assertIn("NOT = { has_global_variable = nd_tc_done_$CODE$ }", body)
        self.assertIn("set_global_variable = nd_tc_done_$CODE$", body)
        self.assertIn("set_variable = { name = nd_tc_other value = scope:nd_target days = 10 }", body)
        self.assertIn("set_variable = { name = nd_tc_code value = $CODE$ days = 10 }", body)
        self.assertIn("trigger_event = { id = nuclear_crisis.27 days = 1 }", body)

    def test_self_check_both_halves(self):
        ev = block(self.events, "nuclear_crisis.27")
        self.assertIn("hidden = yes", ev)
        self.assertIn("has_variable = nd_tc_other", block(ev, "trigger"))
        imm = block(ev, "immediate")
        self.assertIn("save_scope_as = nd_tc_self", imm)
        self.assertIn("var:nd_tc_other = { save_scope_as = nd_tc_other }", imm)
        for code, what in TRADES.items():
            self.assertIn(f"nd_crisis_trade_check_log = {{ CODE = {code} WHAT = {what} }}", imm)
        last_log = imm.rindex("nd_crisis_trade_check_log")
        self.assertLess(last_log, imm.index("remove_variable = nd_tc_other"))
        self.assertLess(last_log, imm.index("remove_variable = nd_tc_code"))
        helper = block(self.effects, "nd_crisis_trade_check_log")
        self.assertIn("var:nd_tc_code = $CODE$", block(helper, "limit"))
        self.assertIn("nd_dispute_$WHAT$_by = { TARGET = scope:nd_tc_other }", helper)
        self.assertIn("scope:nd_tc_other = { nd_dispute_$WHAT$_by = { TARGET = scope:nd_tc_self } }", helper)
        self.assertIn('"TE_SELF_CHECK OK nd_trade_$CODE$', helper)
        self.assertEqual(helper.count('"TE_SELF_CHECK BROKEN nd_trade_$CODE$'), 2)


if __name__ == "__main__":
    unittest.main()
