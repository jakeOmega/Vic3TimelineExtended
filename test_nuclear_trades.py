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
    GUI,
    JE_DOC,
    SGUIS,
    TRIGGERS,
    VALUES,
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
        self.assertIn("nd_crisis_option = { ACT = refuse_trade }", refuse)
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
        # the demanded half; the matching half with and without the swap
        self.assertEqual(helper.count('"TE_SELF_CHECK BROKEN nd_trade_$CODE$'), 3)


def top_blocks(body):
    """The `name = { … }` blocks directly inside body, as text."""
    out, i = [], 0
    while True:
        m = re.compile(r"[\w:.]+ = \{").search(body, i)
        if not m:
            return out
        depth, j = 1, m.end()
        while depth:
            depth += body[j] == "{"
            depth -= body[j] == "}"
            j += 1
        out.append(body[m.start():j])
        i = j


def swap_sides(text):
    text = text.replace("scope:nd_issuer", "@I").replace("scope:nd_target", "scope:nd_issuer").replace("@I", "scope:nd_target")
    return text.replace("add = ", "@A").replace("subtract = ", "add = ").replace("@A", "subtract = ")


def after_limit(branch):
    """A branch's body after its limit block."""
    lim = block(branch, "limit")
    return branch[branch.index(lim) + len(lim) + 1:]


def balance_branch(body, code):
    for m in re.finditer(r"(?:else_if|if) = \{", body):
        branch = block(body[m.start():], "else_if" if body[m.start()] == "e" else "if")
        if re.fullmatch(r"\s*scope:nd_issuer = \{ var:nd_crisis_dispute = " + str(code) + r" \}\s*", block(branch, "limit")):
            return branch
    raise AssertionError(f"no balance branch for {code}")


class TestTradeAI(unittest.TestCase):
    # (weight of each item, the text that makes the target the giver in the add part)
    WEIGHTS = {7: ({10, 4}, "source_country = scope:nd_target"),
               8: ({10}, "scope:nd_target = { has_claim = PREV }"),
               9: ({4}, "var:iw_attacker ?= scope:nd_target"),
               10: ({10}, "scope:nd_target = { every_scope_state")}

    def setUp(self):
        self.values = strip_comments(read(VALUES))
        self.triggers = strip_comments(read(TRIGGERS))
        self.events = strip_comments(read(CRISIS_EVENTS))
        self.balance = block(self.values, "nd_trade_balance_value")

    def test_balance_is_antisymmetric(self):
        """What the target gives, less what the issuer gives: the issuer's part
        is the target's with the parties and the sign swapped."""
        for code in TRADES:
            parts = top_blocks(after_limit(balance_branch(self.balance, code)))
            self.assertEqual(len(parts), 2, code)
            self.assertEqual(sorted(squash(b) for b in parts), sorted(squash(swap_sides(b)) for b in parts), code)

    def test_balance_weights_and_direction(self):
        for code, (weights, giver) in self.WEIGHTS.items():
            branch = balance_branch(self.balance, code)
            adds = {int(n) for n in re.findall(r"\badd = (\d+)", branch)}
            subs = {int(n) for n in re.findall(r"\bsubtract = (\d+)", branch)}
            self.assertEqual(adds, weights, code)
            self.assertEqual(subs, weights, code)
            parts = top_blocks(after_limit(branch))
            add_part = squash(" ".join(b for b in parts if "add = " in b and "subtract = " not in b))
            self.assertIn(giver, add_part, code)
        self.assertIn("NOT = { has_active_production_method = pm_orbital_battlestation_construction_paused }",
                      squash(balance_branch(self.balance, 10)))
        self.assertRegex(read(VALUES), r"(?m)^nd_ai_trade_danger_line = 40\b")

    def test_ai_accepts_on_the_spec_rule(self):
        body = squash(block(self.triggers, "nd_ai_accepts_trade"))
        self.assertIn("nd_crisis_trade_holds = { ISSUER = scope:nd_issuer TARGET = scope:nd_target }", body)
        self.assertIn("NOT = { nd_trade_costs_us_an_alliance = yes }", body)
        self.assertIn("AND = { THIS = scope:nd_target has_variable = nd_yield_pressure "
                      "var:nd_yield_pressure >= nd_ai_concession_line nd_trade_balance_value <= 0 }", body)
        self.assertIn("AND = { THIS = scope:nd_issuer has_variable = nd_crisis_danger "
                      "var:nd_crisis_danger >= nd_ai_trade_danger_line var:nd_crisis_weeks >= nd_ai_trade_min_weeks "
                      "nd_trade_balance_value >= 0 }", body)

    def test_ai_keeps_an_ally_either_side(self):
        body = block(self.triggers, "nd_trade_costs_us_an_alliance")
        self.assertIn("nd_crisis_dispute_is = { D = 7 }", body)
        ands = [block(body[m.start():], "AND") for m in re.finditer(r"\bAND = \{", body)]
        target = [a for a in ands if re.match(r"\s*THIS = scope:nd_target\b", a)]
        issuer = [a for a in ands if re.match(r"\s*THIS = scope:nd_issuer\b", a)]
        self.assertEqual(len(target), 1)
        self.assertEqual(len(issuer), 1)
        self.assertIn("nd_concession_costs_an_alliance = yes", target[0])
        s = squash(issuer[0])
        self.assertIn("source_country = scope:nd_issuer target_country = { NOT = { THIS = scope:nd_target } "
                      "is_adjacent_to_country = scope:nd_target }", s)
        self.assertIn("has_type = alliance", s)
        self.assertIn("has_type = defensive_pact", s)

    def test_answer_weights(self):
        accept = squash(block(option_body(self.events, "nuclear_crisis.8.a"), "ai_chance"))
        refuse = squash(block(option_body(self.events, "nuclear_crisis.8.b"), "ai_chance"))
        self.assertIn("modifier = { trigger = { NOT = { nd_ai_accepts_trade = yes } } factor = 0 }", accept)
        self.assertIn("modifier = { trigger = { nd_ai_accepts_trade = yes } factor = 0 }", refuse)

    def test_deadline_offer(self):
        body = option_body(self.events, "nuclear_crisis.4.h")
        self.assertIn("nd_can_offer_trade = yes", block(body, "trigger"))
        self.assertIn("nd_crisis_option = { ACT = offer_trade }", body)
        chance = squash(block(body, "ai_chance"))
        self.assertIn("modifier = { trigger = { nd_trade_balance_value < 0 } factor = 0 }", chance)
        self.assertIn("modifier = { trigger = { nd_trade_costs_us_an_alliance = yes } factor = 0 }", chance)
        self.assertTrue(loc_value("nuclear_crisis.4.h"))


def gui_instance(gui, type_name, block_name, key):
    """The `type_name = { … }` instance whose `block_name` override shows key."""
    for m in re.finditer(r"(?m)^\t+" + type_name + r" = \{", gui):
        body = block(gui[m.start():], type_name)
        if re.search(r'blockoverride "' + block_name + r'" \{\s*text = "' + key + '"', body):
            return body
    raise AssertionError(f"no {type_name} showing {key}")


class TestTradePanel(unittest.TestCase):
    SHOWN = "visible = \"[GetScriptedGui('nd_crisis_tradeable_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]\""

    def setUp(self):
        self.sguis = strip_comments(read(SGUIS))
        self.gui = read(GUI)

    def test_op_six(self):
        body = block(self.sguis, "nd_crisis_action_sgui")
        valid, effect = squash(block(body, "is_valid")), squash(block(body, "effect"))
        self.assertIn("limit = { exists = scope:op scope:op = 6 } nd_can_offer_trade = yes", valid)
        self.assertIn("limit = { exists = scope:op scope:op = 6 } nd_crisis_act_offer_trade = yes", effect)

    def test_rows_shown_only_for_a_tradeable_dispute(self):
        shown = block(self.sguis, "nd_crisis_tradeable_sgui")
        self.assertEqual(squash(block(shown, "is_shown")), "nd_crisis_dispute_tradeable = yes")
        self.assertIn("ai_is_valid = { always = no }", squash(shown))
        move = gui_instance(self.gui, "nd_choice_row", "choice_name", "nd_w_crisis_act_trade")
        outcome = gui_instance(self.gui, "nd_outcome_row", "outcome_label", "nd_w_crisis_trade_label")
        for row in (move, outcome):
            self.assertEqual(row.count("visible = "), 1)
            self.assertIn(self.SHOWN, row)
        self.assertIn("MakeScopeValue( '(CFixedPoint)6' )", move)
        for key in ("nd_w_crisis_trade_effect", "nd_w_crisis_cred_trade", "nd_w_crisis_trade_tt"):
            self.assertIn(key, outcome)
        for key in ("nd_w_crisis_act_trade", "nd_w_crisis_act_trade_btn", "nd_w_crisis_trade_label",
                    "nd_w_crisis_trade_effect", "nd_w_crisis_cred_trade", "nd_w_crisis_trade_tt"):
            self.assertTrue(loc_value(key), key)

    def test_legend_names_trades(self):
        self.assertIn("trade", loc_value("nd_w_crisis_actions_legend"))

    def test_je_doc_lists_the_handler(self):
        doc = JE_DOC.read_bytes().decode("utf-8")
        self.assertIn("`nd_crisis_tradeable_sgui`", doc)
        self.assertRegex(doc, r"\| \| 6 \| offer a trade \(either side\) \|")
        self.assertIn("twenty-five display handlers", doc)


class TestTradeDocs(unittest.TestCase):
    def test_design_records_trades(self):
        doc = (ROOT / "docs/systems/nuclear_crisis_design.md").read_text(encoding="utf-8")
        self.assertIn("### 0.17", doc)
        self.assertRegex(doc, r"\| 11 \|")

    def test_guide_explains_a_trade(self):
        guide = (ROOT / "docs/player_guide/14-nuclear.md").read_text(encoding="utf-8")
        moves = guide.split("Moves during a crisis", 1)[1]
        self.assertIn("trade", moves.lower())

    def test_playtest_lists_the_self_check(self):
        doc = (ROOT / "docs/testing/nuclear-playtest.md").read_text(encoding="utf-8")
        self.assertIn("nd_trade_", doc)


class TestFinalReviewFixes4c(unittest.TestCase):
    """The phase 4c final review's Important findings, each pinned."""

    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.triggers = strip_comments(read(TRIGGERS))
        self.events = strip_comments(read(CRISIS_EVENTS))
        self.values = strip_comments(read(VALUES))
        self.accept = block(self.effects, "nd_crisis_act_accept_trade")
        self.hidden = block(self.accept, "hidden_effect")

    def test_close_only_inside_the_guard(self):
        """A lapsed offer must not close as a trade (script review I1)."""
        guarded = block(self.hidden, "if")
        self.assertEqual(self.accept.count("nd_crisis_close"), 1)
        self.assertIn("nd_crisis_close = { OUTCOME = 11 }", guarded)

    def test_dispatch_reads_the_issuer(self):
        """The dispute code is the issuer's record (script review I2)."""
        guarded = block(self.hidden, "if")
        self.assertRegex(squash(guarded), r"scope:nd_issuer = \{ if = \{ limit = \{ var:nd_crisis_dispute = 7 \} "
                                          r"nd_crisis_trade_halves = \{ CODE = 7 WHAT = deployment \} \}")

    def test_no_proposal_pending_reads_talks(self):
        """The one-proposal gate itself (script review I3)."""
        body = squash(block(self.triggers, "nd_crisis_no_proposal_pending"))
        self.assertIn("AND = { nd_is_crisis_owner = yes var:nd_crisis_talks = 0 }", body)
        self.assertIn("AND = { nd_is_crisis_target = yes var:nd_crisis_opponent ?= { has_variable = nd_crisis_talks "
                      "var:nd_crisis_talks = 0 } }", body)

    def test_refusing_a_trade_says_so(self):
        """.8.b no longer reads "We refuse to stand down" (both reviews)."""
        refuse = option_body(self.events, "nuclear_crisis.8.b")
        self.assertIn("nd_crisis_option = { ACT = refuse_trade }", refuse)
        body = block(self.effects, "nd_crisis_act_refuse_trade")
        self.assertIn("custom_tooltip = nd_tt_act_refuse_trade", body)
        self.assertNotIn("nd_tt_act_refuse_talks", body)
        self.assertIn("nd_crisis_talks_refused = yes", body)
        self.assertIn("nd_crisis_talks_refused = yes", block(self.effects, "nd_crisis_act_refuse_talks"))
        hidden = squash(block(block(self.effects, "nd_crisis_talks_refused"), "hidden_effect"))
        self.assertIn("set_variable = { name = nd_crisis_talks value = 0 } set_variable = { name = nd_crisis_pressure_weeks value = 0 }", hidden)
        self.assertNotIn("stand down", loc_value("nd_tt_act_refuse_trade"))
        self.assertNotIn("stand-down", loc_value("nd_wc_detail_talks"))

    def test_self_check_tells_the_swap_apart(self):
        """A BROKEN matching half says whether the swap took (script review M6)."""
        halves = block(self.effects, "nd_crisis_trade_halves")
        swaps = [m.start() for m in re.finditer(r"nd_crisis_swap_parties = yes", halves)]
        flag = halves.index("scope:nd_issuer = { nd_is_crisis_target = yes }")
        self.assertLess(swaps[0], flag)
        self.assertLess(flag, swaps[1])
        self.assertIn("set_variable = { name = nd_tc_swap value = 1 days = 10 }", halves)
        self.assertIn("set_variable = { name = nd_tc_swap value = 0 days = 10 }", halves)
        helper = block(self.effects, "nd_crisis_trade_check_log")
        self.assertIn("var:nd_tc_swap ?= 0", helper)
        self.assertIn("the swap did not take", helper)
        self.assertRegex(helper, r"the demanded half; \[THIS\.GetCountry\.GetNameNoFormatting\] still has")
        imm = block(block(self.events, "nuclear_crisis.27"), "immediate")
        self.assertIn("nd_tc_swap", imm)

    def test_accept_logs_the_balance(self):
        """every_scope_treaty in a script value is unprobed: the balance is logged (script review M7)."""
        guarded = block(self.hidden, "if")
        self.assertRegex(guarded, r"debug_log = \"TE_NUCLEAR: type=trade; [^\"]*balance=\[SCOPE\.ScriptValue\('nd_trade_balance_value'\)\|0\]")
        self.assertLess(guarded.index("type=trade"), guarded.index("nd_crisis_trade_halves"))

    def test_ai_issuer_waits_for_its_first_deadline(self):
        """A public ultimatum starts near danger 40, so danger alone let a target trade out in week one (gameplay I1)."""
        self.assertRegex(read(VALUES), r"(?m)^nd_ai_trade_min_weeks = 8\b")
        body = squash(block(self.triggers, "nd_ai_accepts_trade"))
        self.assertIn("THIS = scope:nd_issuer has_variable = nd_crisis_danger var:nd_crisis_danger >= nd_ai_trade_danger_line "
                      "var:nd_crisis_weeks >= nd_ai_trade_min_weeks", body)

    def test_ai_offers_only_what_would_be_taken(self):
        """No deadline spent on a trade the AI can see refused (gameplay I2)."""
        chance = squash(block(option_body(self.events, "nuclear_crisis.4.h"), "ai_chance"))
        self.assertIn("modifier = { trigger = { scope:nd_target = { NOT = { nd_ai_accepts_trade = yes } } } factor = 0 }", chance)
        self.assertNotIn("is_ai", chance)

    def test_no_trade_launders_a_bar(self):
        """A bar holds one country, so a trade would overwrite one held against a third (gameplay I3)."""
        body = block(self.triggers, "nd_crisis_trade_holds")
        ands = [block(body[m.start():], "AND") for m in re.finditer(r"\bAND = \{", body)]
        bars = {7: "nd_crisis_deploy_bar", 9: "nd_crisis_covert_bar", 10: "nd_crisis_orbital_freeze"}
        for code in TRADES:
            a = squash([x for x in ands if re.search(r"var:nd_crisis_dispute = " + str(code) + r"\b", x)][0])
            for bar in bars.values():
                if bar == bars.get(code):
                    self.assertIn(f"NOT = {{ $ISSUER$ = {{ has_variable = {bar} }} }}", a, code)
                    self.assertIn(f"NOT = {{ $TARGET$ = {{ has_variable = {bar} }} }}", a, code)
                else:
                    self.assertNotIn(bar, a, code)
        self.assertIn("bar", loc_value("nd_tt_trade_matching"))

    def test_playtest_items_are_runnable(self):
        """Gameplay I5: the tester must be the one who answers, and know the AI's rule."""
        doc = (ROOT / "docs/testing/nuclear-playtest.md").read_text(encoding="utf-8")
        item61 = re.search(r"(?m)^61\. .*$", doc).group(0)
        item63 = re.search(r"(?m)^63\. .*$", doc).group(0)
        self.assertIn("40", item61)
        self.assertIn("te_debug_deterrence.4", item63)


if __name__ == "__main__":
    unittest.main()
