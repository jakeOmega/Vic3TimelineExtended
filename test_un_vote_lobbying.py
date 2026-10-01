# -*- coding: utf-8 -*-
"""UN votes: late AI ballots, visible leans and lobbying
(docs/superpowers/specs/2026-09-27-un-vote-lobbying-design.md).

The engine checks none of this at load: a casting gate that lost its
condition, a veto that reads the pledged lean, or a row that passes the wrong
slot number to one of its buttons all load cleanly and misbehave in play.
These tests pin the structure the design depends on.
"""

import os
import re
import unittest

from test_un_chamber_mission_slots import _block, _braced, _branches, _read, _sub_block, _widget_rows

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


VOTE_EVENTS = _path("events", "un_vote_events.txt")
VOTE_EFFECTS = _path("common", "scripted_effects", "un_vote_effects.txt")
DOSSIER_EFFECTS = _path("common", "scripted_effects", "un_dossier_effects.txt")
DOSSIER_TRIGGERS = _path("common", "scripted_triggers", "un_dossier_triggers.txt")
DOSSIER_VALUES = _path("common", "script_values", "un_dossier_values.txt")
LOBBYING_VALUES = _path("common", "script_values", "un_lobbying_values.txt")
LOBBYING_ACTIONS = _path("common", "diplomatic_actions", "un_lobbying.txt")
LOBBY_EFFECTS = _path("common", "scripted_effects", "un_lobby_effects.txt")
LOBBY_TRIGGERS = _path("common", "scripted_triggers", "un_lobby_triggers.txt")
CAST_EFFECTS = _path("common", "scripted_effects", "un_vote_cast_effects.txt")
WIDGET = _path("gui", "journal_entry_widgets", "un_chamber_widget.gui")
SGUIS = _path("common", "scripted_guis", "un_chamber_sguis.txt")
DISPLAY = _path("common", "scripted_effects", "un_chamber_display_effects.txt")

DELEGATION_ROWS = 24

_TOP_LEVEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*\{", re.M)


def _all_script(*dirs):
    """Every top-level name defined under common/<dir> for each dir."""
    names = set()
    for d in dirs:
        root = _path("common", d)
        for name in os.listdir(root):
            if name.endswith(".txt"):
                names |= set(_TOP_LEVEL.findall(_read(os.path.join(root, name))))
    return names


def _event(name):
    return _block(_read(VOTE_EVENTS), name)


def _options(event_body):
    out = []
    for m in re.finditer(r"^\toption\s*=\s*\{", event_body, re.M):
        out.append(_braced(event_body, m.end() - 1))
    return out


class CastingTimingTest(unittest.TestCase):
    """§1: the AI votes at month 9, 10 or 11, by its lean at that time."""

    @classmethod
    def setUpClass(cls):
        cls.effects = _read(DOSSIER_EFFECTS)
        cls.vote_effects = _read(VOTE_EFFECTS)
        cls.draws = _block(cls.effects, "un_vote_ai_draws")
        cls.vote4 = _sub_block(_event("un_vote.4"), "immediate")

    def test_the_casting_month_is_nine_ten_or_eleven(self):
        months = re.findall(r"name\s*=\s*un_vote_cast_month\s+value\s*=\s*(\d+)", self.draws)
        self.assertEqual(months[:3], ["9", "10", "11"])

    def test_the_misreading_is_minus_ten_nought_or_ten(self):
        found = re.findall(r"name\s*=\s*un_lean_misread\s+value\s*=\s*(-?\d+)", self.draws)
        self.assertEqual(found, ["-10", "0", "10"])

    def test_a_late_draw_is_no_earlier_than_next_month(self):
        self.assertRegex(
            self.draws,
            r"un_vote_cast_month\s*<\s*un_res_next_month[\s\S]*?"
            r"name\s*=\s*un_vote_cast_month\s+value\s*=\s*un_res_next_month",
        )

    def test_the_draw_is_once_per_resolution(self):
        self.assertRegex(self.draws, r"NOT\s*=\s*\{\s*var:un_vote_draw_res\s*\?=\s*scope:un_resolution\s*\}")

    def test_un_vote_4_draws_then_snapshots_then_casts_only_when_due(self):
        body = self.vote4
        draw = body.index("un_vote_ai_draws")
        snap = body.index("un_lean_snapshot")
        cast = body.index("un_vote_ai_cast = yes")
        self.assertLess(draw, snap)
        self.assertLess(snap, cast)
        # The cast sits in an `if` whose limit asks whether its month has come.
        cast_if = body.rfind("if = {", 0, cast)
        limit = _sub_block(body[cast_if:], "limit")
        self.assertIn("un_vote_ai_cast_due = yes", limit)
        self.assertIn("un_vote_can_cast_ballot = yes", limit)
        self.assertIn("is_ai = yes", limit)

    def test_the_cast_is_due_at_its_month_or_at_the_last_call(self):
        due = _block(_read(DOSSIER_TRIGGERS), "un_vote_ai_cast_due")
        self.assertIn("un_res_last_call", due)
        self.assertRegex(due, r"var:un_vote_cast_month\s*<=\s*un_res_months_now")

    def test_nothing_dispatches_ballots_at_day_thirty_any_more(self):
        self.assertNotIn("un_vote_dispatch_ai_ballots", _all_script("scripted_effects"))
        self.assertNotIn("un_vote_dispatch_ai_ballots", _read(VOTE_EVENTS))
        vote5 = _event("un_vote.5")
        self.assertNotIn("un_res_ai_cast", vote5)
        self.assertNotIn("un_vote_ai_cast", vote5)

    def test_opening_sends_every_member_its_lean_and_queues_the_last_call(self):
        opening = _block(self.vote_effects, "un_resolution_open")
        self.assertIn("un_vote_refresh_leans = yes", opening)
        self.assertNotIn("un_vote.5", opening)
        last_call = re.search(r"id\s*=\s*un_vote\.6\s+days\s*=\s*(\d+)", opening)
        decision = re.search(r"id\s*=\s*un_vote\.2\s+days\s*=\s*(\d+)", opening)
        self.assertIsNotNone(last_call)
        self.assertLess(int(last_call.group(1)), int(decision.group(1)))

    def test_the_last_call_marks_the_resolution_and_refreshes_the_ai(self):
        immediate = _sub_block(_event("un_vote.6"), "immediate")
        self.assertIn("set_variable = un_res_last_call", immediate)
        self.assertIn("un_vote_refresh_leans = yes", immediate)

    def test_the_monthly_update_refreshes_every_lean_and_calls_the_last_call_at_twelve(self):
        monthly = _block(self.vote_effects, "un_resolutions_monthly_update")
        self.assertIn("un_vote_refresh_leans = yes", monthly)
        self.assertRegex(monthly, r"var:un_res_months\s*>=\s*12[\s\S]*?set_variable\s*=\s*un_res_last_call")

    def test_the_refresh_reaches_every_member(self):
        refresh = _block(self.effects, "un_vote_refresh_leans")
        fan_out = [
            b for b in (_braced(refresh, m.end() - 1) for m in re.finditer(r"every_country\s*=\s*\{", refresh))
            if "id = un_vote.4" in b
        ]
        self.assertEqual(len(fan_out), 1)
        self.assertNotIn("is_ai", fan_out[0])


class VetoBasisTest(unittest.TestCase):
    """§4: a pledge never makes a veto and never prevents one it did not promise away."""

    def test_the_veto_reads_the_lean_without_the_pledge(self):
        veto = _block(_read(DOSSIER_TRIGGERS), "un_vote_ai_should_veto")
        self.assertIn("var:un_lean_veto_basis", veto)
        self.assertNotIn("un_lean_total", veto)

    def test_the_snapshot_writes_the_basis_and_the_shown_lean(self):
        snapshot = _block(_read(DOSSIER_EFFECTS), "un_lean_snapshot")
        self.assertRegex(snapshot, r"name\s*=\s*un_lean_veto_basis\s+value\s*=\s*un_lean_veto_basis_value")
        self.assertRegex(snapshot, r"name\s*=\s*un_lean_shown\s+value\s*=\s*un_lean_shown_value")
        values = _read(LOBBYING_VALUES)
        basis = _block(values, "un_lean_veto_basis_value")
        self.assertIn("var:un_lean_total", basis)
        self.assertIn("subtract = var:un_lean_pledge", basis)
        shown = _block(values, "un_lean_shown_value")
        self.assertIn("add = var:un_lean_misread", shown)


class DecideLaterTest(unittest.TestCase):
    """§2: the human vote event can be put off, and comes back at months 9 and 11."""

    @classmethod
    def setUpClass(cls):
        cls.options = _options(_event("un_vote.1"))
        cls.later = [o for o in cls.options if "un_vote.1.later" in o]

    def test_there_is_one_decide_later_option(self):
        self.assertEqual(len(self.later), 1)

    def test_deciding_later_casts_nothing_and_the_ai_never_takes_it(self):
        later = self.later[0]
        self.assertNotIn("un_vote_cast_", later)
        self.assertRegex(later, r"ai_chance\s*=\s*\{\s*base\s*=\s*0\s*\}")
        self.assertIn("name = un_res_deferred", later)

    def test_the_default_option_is_still_the_vote_in_favour(self):
        defaults = [o for o in self.options if "default_option = yes" in o]
        self.assertEqual(len(defaults), 1)
        self.assertIn("un_vote_cast_yes = yes", defaults[0])

    def test_the_monthly_update_asks_again_at_nine_and_eleven(self):
        monthly = _block(_read(VOTE_EFFECTS), "un_resolutions_monthly_update")
        self.assertRegex(
            monthly,
            r"var:un_res_months\s*=\s*9\s+var:un_res_months\s*=\s*11[\s\S]*?"
            r"variable\s*=\s*un_res_deferred[\s\S]*?trigger_event\s*=\s*\{\s*id\s*=\s*un_vote\.1\s*\}",
        )



def _accept_terms(action_body):
    """{desc: value} for each `add = { desc = X value = N }` in the accept score."""
    score = _sub_block(_sub_block(action_body, "ai"), "accept_score")
    return {
        d: int(v)
        for d, v in re.findall(r'desc\s*=\s*"([A-Z_]+)"\s+value\s*=\s*(-?\d+)', score)
    }


class PledgeTest(unittest.TestCase):
    """§4: a pledge for or against, sought by any member, paid with an obligation."""

    @classmethod
    def setUpClass(cls):
        actions = _read(LOBBYING_ACTIONS)
        cls.pledge_for = _block(actions, "un_secure_commitment_action")
        cls.pledge_against = _block(actions, "un_secure_commitment_against_action")
        cls.effects = _read(LOBBY_EFFECTS)
        cls.triggers = _read(LOBBY_TRIGGERS)

    def test_any_member_may_ask(self):
        for body in (self.pledge_for, self.pledge_against):
            self.assertNotIn("un_res_proposer", _sub_block(body, "selectable"))

    def test_the_target_ties_flip_for_a_pledge_against(self):
        yes = _accept_terms(self.pledge_for)
        no = _accept_terms(self.pledge_against)
        for key in ("UN_LOBBY_ACCEPT_TARGET_ALLY", "UN_LOBBY_ACCEPT_TARGET_BLOC", "UN_LOBBY_ACCEPT_TARGET_RIVAL"):
            with self.subTest(term=key):
                self.assertEqual(no[key], -yes[key])
        for key in ("UN_LOBBY_ACCEPT_BASE", "UN_LOBBY_ACCEPT_OBLIGATION", "UN_LOBBY_ACCEPT_RIVALRY"):
            with self.subTest(term=key):
                self.assertEqual(no[key], yes[key])

    def test_each_direction_books_its_own_list(self):
        self.assertRegex(_sub_block(self.pledge_for, "accept_effect"), r"un_lobby_accept_commitment\s*=\s*\{\s*LIST\s*=\s*yes\s+DIR\s*=\s*1\s*\}")
        self.assertRegex(_sub_block(self.pledge_against, "accept_effect"), r"un_lobby_accept_commitment\s*=\s*\{\s*LIST\s*=\s*no\s+DIR\s*=\s*-1\s*\}")
        accept = _block(self.effects, "un_lobby_accept_commitment")
        self.assertIn("name = un_res_committed_$LIST$", accept)
        self.assertIn("name = un_pledge_dir value = $DIR$", accept)

    def test_one_pledge_per_member_and_two_per_asker(self):
        made = _block(self.triggers, "un_pledge_made_by")
        for lst in ("un_res_committed_yes", "un_res_committed_no", "un_res_commit_kept", "un_res_commit_broken"):
            self.assertIn(lst, made)
        deal = _block(self.triggers, "un_pledge_deal_available")
        self.assertIn("un_pledge_made_by", deal)
        self.assertIn("un_pledge_under_cap = yes", deal)
        cap = _block(self.triggers, "un_pledge_under_cap")
        self.assertIn("var:un_pledge_count < un_lobby_commitment_cap", cap)

    def test_the_lean_moves_a_hundred_either_way(self):
        pledge = _block(_read(DOSSIER_VALUES), "un_lean_pledge")
        self.assertRegex(pledge, r"un_lobby_holds_pending_commitment\s*=\s*yes\s*\}\s*add\s*=\s*100")
        self.assertRegex(pledge, r"un_lobby_holds_pending_against\s*=\s*yes\s*\}\s*add\s*=\s*-100")

    def test_settlement_reads_the_side_each_pledge_was_made_on(self):
        settle = _block(self.effects, "un_lobby_settle_commitment")
        self.assertRegex(settle, r"un_res_committed_yes[\s\S]*?un_lobby_settle_pledge\s*=\s*\{\s*KEPT_LIST\s*=\s*un_res_yes\s*\}")
        self.assertRegex(settle, r"un_res_committed_no[\s\S]*?un_lobby_settle_pledge\s*=\s*\{\s*KEPT_LIST\s*=\s*un_res_no\s*\}")
        pledge = _block(self.effects, "un_lobby_settle_pledge")
        self.assertIn("var:un_pledge_to", pledge)

    def test_the_ballot_says_whether_it_keeps_or_breaks_either_pledge(self):
        cast = _read(CAST_EFFECTS)
        yes = _block(cast, "un_vote_cast_yes")
        self.assertRegex(yes, r"un_lobby_holds_pending_commitment\s*=\s*yes\s*\}\s*custom_tooltip\s*=\s*UN_VOTE_COMMITMENT_KEEP_TT")
        self.assertRegex(yes, r"un_lobby_holds_pending_against\s*=\s*yes\s*\}\s*custom_tooltip\s*=\s*UN_VOTE_COMMITMENT_BREAK_TT")
        for name in ("un_vote_cast_no", "un_vote_cast_veto"):
            body = _block(cast, name)
            with self.subTest(cast=name):
                self.assertRegex(body, r"un_lobby_holds_pending_commitment\s*=\s*yes\s*\}\s*custom_tooltip\s*=\s*UN_VOTE_COMMITMENT_BREAK_TT")
                self.assertRegex(body, r"un_lobby_holds_pending_against\s*=\s*yes\s*\}\s*custom_tooltip\s*=\s*UN_VOTE_COMMITMENT_KEEP_TT")



class CampaignTest(unittest.TestCase):
    """§3: an influence campaign on an AI member, a one-sided pact."""

    @classmethod
    def setUpClass(cls):
        actions = _read(LOBBYING_ACTIONS)
        cls.pacts = {d: _block(actions, f"un_lobby_{d}_action") for d in ("for", "against")}
        cls.effects = _read(LOBBY_EFFECTS)
        cls.values = _read(LOBBYING_VALUES)
        cls.vote_effects = _read(VOTE_EFFECTS)

    def test_both_pacts_cost_a_hundred_and_are_one_sided(self):
        for d, body in self.pacts.items():
            pact = _sub_block(body, "pact")
            with self.subTest(direction=d):
                self.assertRegex(pact, r"\bcost\s*=\s*100\b")
                self.assertRegex(pact, r"is_two_sided_pact\s*=\s*no")
                self.assertIn("un_lobby_campaign_live_ok = yes", _sub_block(pact, "requirement_to_maintain"))

    def test_each_pact_ends_its_own_campaign(self):
        for d, body in self.pacts.items():
            pact = _sub_block(body, "pact")
            for hook in ("manual_break_effect", "auto_break_effect"):
                with self.subTest(direction=d, hook=hook):
                    self.assertRegex(_sub_block(pact, hook), r"un_lobby_campaign_end\s*=\s*\{\s*DIR\s*=\s*" + d + r"\s*\}")
            self.assertRegex(_sub_block(body, "accept_effect"), r"un_lobby_campaign_start\s*=\s*\{\s*DIR\s*=\s*" + d + r"\s*\}")

    def test_script_alone_starts_and_stops_the_ai_s_campaigns(self):
        for d, body in self.pacts.items():
            ai = _sub_block(body, "ai")
            with self.subTest(direction=d):
                self.assertRegex(_sub_block(ai, "evaluation_chance"), r"value\s*=\s*0\s*$")
                self.assertRegex(ai, r"will_break\s*=\s*\{\s*always\s*=\s*no\s*\}")

    def test_only_ai_members_can_be_lobbied(self):
        for d, body in self.pacts.items():
            with self.subTest(direction=d):
                self.assertRegex(_sub_block(body, "potential"), r"is_ai\s*=\s*yes")
        triggers = _read(LOBBY_TRIGGERS)
        self.assertIn("un_lobby_member_lobbyable = yes", _block(triggers, "un_lobby_campaign_live_ok"))
        self.assertRegex(_block(triggers, "un_lobby_member_lobbyable"), r"is_ai\s*=\s*yes")

    def test_the_steps_and_caps(self):
        for name, value in (("un_lobby_campaign_step", "3"), ("un_lobby_campaign_cap", "15"), ("un_lobby_campaign_stack_cap", "20")):
            with self.subTest(value=name):
                self.assertRegex(self.values, re.compile(r"^" + name + r"\s*=\s*\{\s*value\s*=\s*" + value + r"\s*\}", re.M))
        shift = _block(self.values, "un_lobby_campaign_shift_value")
        self.assertIn("multiply = un_lobby_campaign_step", shift)
        self.assertIn("max = un_lobby_campaign_cap", shift)
        aggregate = _block(self.effects, "un_lobby_campaigns_aggregate")
        self.assertIn("max = un_lobby_campaign_stack_cap", aggregate)

    def test_the_lean_reads_the_net_shift(self):
        self.assertIn("add = un_lean_lobbying", _block(_read(DOSSIER_VALUES), "un_vote_lean"))
        term = _block(self.values, "un_lean_lobbying")
        self.assertIn("add = var:un_lobby_for_shift", term)
        self.assertIn("subtract = var:un_lobby_against_shift", term)
        self.assertIn("var:un_lobby_shift_res ?= scope:un_resolution", term)
        self.assertRegex(_block(_read(DOSSIER_EFFECTS), "un_lean_snapshot"), r"name\s*=\s*un_lean_lobbying\s+value\s*=\s*un_lean_lobbying")

    def test_voting_and_closing_end_the_campaigns(self):
        for name in ("un_resolution_record_vote", "un_resolution_record_veto"):
            with self.subTest(site=name):
                self.assertRegex(_block(self.vote_effects, name), r"un_lobby_campaigns_end_on\s*=\s*\{\s*MEMBER\s*=\s*scope:un_res_voter\s*\}")
        self.assertIn("un_lobby_campaigns_close = yes", _block(self.vote_effects, "un_resolution_archive"))
        for name in ("un_lobby_campaigns_end_on", "un_lobby_campaigns_close"):
            self.assertIn("un_lobby_campaign_remove_pact = yes", _block(self.effects, name))

    def test_the_month_ticks_before_the_leans_are_read(self):
        monthly = _block(self.vote_effects, "un_resolutions_monthly_update")
        self.assertLess(monthly.index("un_lobby_campaigns_monthly = yes"), monthly.index("un_vote_refresh_leans = yes"))

    def test_a_live_pact_is_found_by_its_direction(self):
        reap = _block(self.effects, "un_lobby_campaigns_reap")
        self.assertRegex(reap, r"first_country\s*=\s*prev\s+second_country\s*=\s*scope:un_lc_m\b")
        self.assertNotIn("has_diplomatic_pact", reap)

    def test_a_cancelled_campaign_drops_its_shift_at_once(self):
        end = _block(self.effects, "un_lobby_campaign_end")
        self.assertIn("un_lobby_campaign_drop", end)
        self.assertIn("un_lobby_member_recompute", end)



class AiLobbyingTest(unittest.TestCase):
    """§5: the proposer lobbies for; the target, its allies and bloc leader against."""

    @classmethod
    def setUpClass(cls):
        effects = _read(LOBBY_EFFECTS)
        cls.monthly = _block(effects, "un_lobby_ai_monthly")
        cls.lobby = _block(effects, "un_lobby_ai_lobby")
        cls.values = _read(LOBBYING_VALUES)

    def test_it_runs_after_the_campaign_month_and_before_the_leans(self):
        monthly = _block(_read(VOTE_EFFECTS), "un_resolutions_monthly_update")
        tick = monthly.index("un_lobby_campaigns_monthly = yes")
        ai = monthly.index("un_lobby_ai_monthly = yes")
        leans = monthly.index("un_vote_refresh_leans = yes")
        self.assertLess(tick, ai)
        self.assertLess(ai, leans)

    def test_the_sides_and_the_leans_each_side_works_on(self):
        self.assertRegex(self.monthly, r"var:un_res_proposer[\s\S]*?un_lobby_ai_lobby\s*=\s*\{\s*DIR\s*=\s*for\s+LOW\s*=\s*-29\s+HIGH\s*=\s*9\s*\}")
        self.assertRegex(self.monthly, r"un_resolution_accuses_target\s*=\s*yes[\s\S]*?un_lobby_ai_lobby\s*=\s*\{\s*DIR\s*=\s*against\s+LOW\s*=\s*-9\s+HIGH\s*=\s*29\s*\}")
        for side in ("has_treaty_alliance_with = { TARGET = scope:un_lai_target }", "is_power_bloc_leader = yes"):
            self.assertIn(side, self.monthly)

    def test_only_ai_countries_lobby_and_only_ai_members_are_lobbied(self):
        self.assertEqual(len(re.findall(r"is_ai\s*=\s*yes", self.monthly)), 2)
        pick = _sub_block(self.lobby, "ordered_country")
        self.assertIn("un_lobby_member_lobbyable = yes", _sub_block(pick, "limit"))

    def test_it_starts_one_a_month_within_three_and_with_influence_to_spare(self):
        self.assertRegex(self.values, re.compile(r"^un_lobby_ai_influence_floor\s*=\s*\{\s*value\s*=\s*150\s*\}", re.M))
        self.assertIn("influence >= un_lobby_ai_influence_floor", self.lobby)
        self.assertRegex(self.lobby, r"count\s*>=\s*3\b")
        pick = _sub_block(self.lobby, "ordered_country")
        self.assertRegex(pick, r"max\s*=\s*1\b")
        self.assertLess(pick.index("create_diplomatic_pact"), pick.index("un_lobby_campaign_start"))

    def test_it_lets_a_campaign_go_when_it_runs_short(self):
        self.assertRegex(self.lobby, r"influence\s*<\s*0[\s\S]*?un_lobby_campaign_remove_pact\s*=\s*yes")



class DelegationRowTest(unittest.TestCase):
    """§6: up to 24 member rows, one scripted-GUI row per member (the #453 pattern).

    Nothing in the engine checks that op 7 means row 7 in every switch, or that
    a row passes one op to all its bindings; a row whose button acted on
    another member would load cleanly.
    """

    SGUIS = {
        # sgui: (is_valid helper, effect helper)
        "un_chamber_deleg_row_sgui": ("un_deleg_row_filled", "un_chamber_deleg_row"),
        "un_chamber_deleg_for_sgui": ("un_deleg_row_can_lobby", "un_deleg_row_lobby"),
        "un_chamber_deleg_against_sgui": ("un_deleg_row_can_lobby", "un_deleg_row_lobby"),
        "un_chamber_deleg_stop_sgui": ("un_deleg_row_lobbying", "un_deleg_row_stop"),
        "un_chamber_deleg_pledge_for_sgui": ("un_deleg_row_can_pledge", "un_deleg_row_pledge"),
        "un_chamber_deleg_pledge_against_sgui": ("un_deleg_row_can_pledge", "un_deleg_row_pledge"),
    }

    @classmethod
    def setUpClass(cls):
        sguis = _read(SGUIS)
        cls.switches = {}
        for sgui in cls.SGUIS:
            body = _block(sguis, sgui)
            cls.switches[(sgui, "is_valid")] = _branches(_sub_block(body, "is_valid"))
            cls.switches[(sgui, "effect")] = _branches(_sub_block(body, "effect"))
        cls.rows = _widget_rows(_read(WIDGET), "un_chamber_deleg_row")
        cls.reassign = _block(_read(DOSSIER_EFFECTS), "un_deleg_reassign_rows")

    def test_the_widget_has_one_row_per_slot(self):
        self.assertEqual(sorted(ops[0] for ops in self.rows), list(range(DELEGATION_ROWS)))

    def test_each_row_passes_one_slot_to_every_binding(self):
        for ops in self.rows:
            # the row's visible and text; Lobby For and Lobby Against: visible
            # (Stop's IsValid), enabled, onclick, tooltip x2; Stop: visible,
            # onclick, tooltip; each Pledge: enabled, onclick, tooltip x2
            self.assertEqual(len(ops), 23, ops)
            self.assertEqual(len(set(ops)), 1, f"a delegation row mixes slots {ops}")

    def test_every_switch_maps_op_to_the_same_slot(self):
        for (sgui, part), branches in self.switches.items():
            helper = self.SGUIS[sgui][0 if part == "is_valid" else 1]
            with self.subTest(sgui=sgui, part=part):
                self.assertEqual(sorted(branches), list(range(DELEGATION_ROWS)))
                for op, branch in branches.items():
                    calls = re.findall(r"\b(\w+)\s*=\s*\{\s*N\s*=\s*(\d+)\b", branch)
                    self.assertEqual(calls, [(helper, str(op))], f"op {op}")

    def test_the_direction_each_button_passes(self):
        expect = {
            "un_chamber_deleg_for_sgui": r"DIR\s*=\s*for\b",
            "un_chamber_deleg_against_sgui": r"DIR\s*=\s*against\b",
            "un_chamber_deleg_pledge_for_sgui": r"ACTION\s*=\s*un_secure_commitment_action\b",
            "un_chamber_deleg_pledge_against_sgui": r"ACTION\s*=\s*un_secure_commitment_against_action\b",
        }
        for sgui, pattern in expect.items():
            for part in ("is_valid", "effect"):
                for op, branch in self.switches[(sgui, part)].items():
                    with self.subTest(sgui=sgui, part=part, op=op):
                        self.assertRegex(branch, pattern)

    def test_rows_are_filled_in_order_and_all_of_them(self):
        calls = re.findall(r"un_deleg_assign_row\s*=\s*\{\s*N\s*=\s*(\d+)\s+COUNT\s*=\s*(\d+)\s*\}", self.reassign)
        self.assertEqual(calls, [(str(k), str(k + 1)) for k in range(DELEGATION_ROWS)])
        cleared = re.findall(r"un_deleg_clear_row\s*=\s*\{\s*N\s*=\s*(\d+)\s*\}", self.reassign)
        self.assertEqual(cleared, [str(k) for k in range(DELEGATION_ROWS)])
        assign = _block(_read(DOSSIER_EFFECTS), "un_deleg_assign_row")
        self.assertRegex(assign, r"position\s*=\s*\$N\$")
        self.assertRegex(assign, r"name\s*=\s*un_deleg_row_\$N\$")

    def test_every_ai_member_refreshes_its_row_after_it_may_have_voted(self):
        body = _sub_block(_event("un_vote.4"), "immediate")
        self.assertLess(body.index("un_vote_ai_cast = yes"), body.index("un_deleg_refresh_self = yes"))

    def test_the_order_reads_the_shown_lean_never_the_true_one(self):
        key = _block(_read(LOBBYING_VALUES), "un_deleg_key_value")
        self.assertIn("var:un_lean_shown", key)
        self.assertNotIn("un_lean_total", key)

    def test_a_campaigner_reads_the_true_band_and_everyone_else_the_estimate(self):
        lines = _block(_read(DISPLAY), "un_chamber_deleg_member_lines")
        self.assertRegex(lines, r"un_deleg_viewer_campaigns_on[\s\S]*?un_chamber_deleg_band\s*=\s*\{\s*VAR\s*=\s*un_lean_total\s*\}[\s\S]*?else[\s\S]*?un_chamber_deleg_band\s*=\s*\{\s*VAR\s*=\s*un_lean_shown\s*\}")



def _loc_values():
    """{key: value} over every English localization file."""
    out = {}
    root = _path("localization", "english")
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith(".yml"):
                with open(os.path.join(dirpath, f), encoding="utf-8-sig") as fh:
                    for line in fh:
                        m = re.match(r'^ ([^:#\s]+):\d* "(.*)"\s*$', line)
                        if m:
                            out[m.group(1)] = m.group(2)
    return out


class ReviewFixesTest(unittest.TestCase):
    """What the whole-branch review found: text the late ballots made wrong,
    the projection early in a session, the rows' sort cost, and a pledge
    settled against the wrong country."""

    @classmethod
    def setUpClass(cls):
        cls.loc = _loc_values()

    def test_no_text_still_says_the_members_vote_within_a_month(self):
        stale = re.compile(r"over the next (30|90) days|ballots thirty days|vote about thirty days", re.I)
        found = sorted(k for k, v in self.loc.items() if stale.search(v))
        self.assertEqual(found, [])

    def test_the_pledge_count_names_no_side(self):
        self.assertNotIn("in favour", self.loc["je_un_chamber_tally_committed"])

    def test_standing_help_no_longer_ties_pledges_to_the_sponsor(self):
        for key in ("je_un_standing_help_limits", "je_un_standing_help_losses", "je_un_standing_help_sources"):
            with self.subTest(key=key):
                self.assertNotIn("sponsor", self.loc[key])

    def test_the_projection_says_when_ai_members_have_yet_to_vote(self):
        projection = _block(_read(DISPLAY), "un_chamber_projection_line")
        self.assertRegex(projection, r"un_res_delegates[\s\S]*?custom_tooltip_no_bullet\s*=\s*je_un_chamber_projection_pending")
        self.assertIn("je_un_chamber_projection_pending", self.loc)

    def test_the_rows_are_sorted_once_per_fan_out_not_per_member(self):
        effects = _read(DOSSIER_EFFECTS)
        self.assertNotIn("un_deleg_reassign_rows", _block(effects, "un_deleg_refresh_self"))
        refresh = _block(effects, "un_vote_refresh_leans")
        self.assertRegex(refresh, r"trigger_event\s*=\s*\{\s*id\s*=\s*un_vote\.7\s+days\s*=\s*1\s*\}")
        self.assertIn("un_deleg_reassign_rows = yes", _sub_block(_event("un_vote.7"), "immediate"))

    def test_a_member_that_has_voted_leaves_its_row_at_once(self):
        listed = _block(_read(LOBBY_TRIGGERS), "un_deleg_listed")
        self.assertIn("un_lobby_has_voted", listed)

    def test_an_annexed_asker_is_never_replaced_by_the_proposer(self):
        settle = _block(_read(LOBBY_EFFECTS), "un_lobby_settle_pledge")
        # The proposer stands in only for a pledge made before the rework,
        # i.e. one whose un_pledge_res is not this resolution.
        self.assertRegex(
            settle,
            r"NOT\s*=\s*\{\s*var:un_pledge_res\s*\?=\s*scope:un_lobby_settle_res\s*\}[\s\S]*?"
            r"var:un_res_proposer\s*\?=\s*\{\s*save_temporary_scope_as\s*=\s*un_lobby_settle_lobbyist",
        )


class BulkLobbyTest(unittest.TestCase):
    """Lobby Top Members For / Against: one press starts a campaign on each
    listed member that qualifies, from the top row down, until the influence
    runs out.

    Nothing in the engine checks that the budget counts what the pacts cost,
    that the button reads every row in order, or that the For button is not
    wired to the Against effect: each loads cleanly and misspends in play.
    """

    @classmethod
    def setUpClass(cls):
        cls.values = _read(LOBBYING_VALUES)
        cls.effects = _read(LOBBY_EFFECTS)
        cls.triggers = _read(LOBBY_TRIGGERS)
        cls.sguis = _read(SGUIS)
        cls.widget = _read(WIDGET)
        cls.loc = _loc_values()

    def test_the_budget_counts_one_campaign_per_hundred_influence(self):
        cost = int(re.search(r"un_lobby_campaign_cost\s*=\s*\{\s*value\s*=\s*(\d+)", self.values).group(1))
        for action in ("un_lobby_for_action", "un_lobby_against_action"):
            pact = _sub_block(_block(_read(LOBBYING_ACTIONS), action), "pact")
            self.assertEqual(int(re.search(r"\bcost\s*=\s*(\d+)", pact).group(1)), cost, action)
        budget = _block(self.values, "un_deleg_bulk_budget")
        steps = re.findall(r"limit\s*=\s*\{\s*influence\s*>=\s*(\d+)\s*\}\s*add\s*=\s*1\s*\}", budget)
        self.assertEqual(steps, [str(cost * k) for k in range(1, DELEGATION_ROWS + 1)])

    def test_the_run_reads_its_budget_once_before_any_pact_and_cleans_up(self):
        body = _block(self.effects, "un_deleg_bulk_lobby")
        first = body.index("set_variable")
        self.assertRegex(body[first:], r"set_variable\s*=\s*\{\s*name\s*=\s*un_bulk_left\s+value\s*=\s*un_deleg_bulk_budget\s*\}")
        self.assertLess(first, body.index("un_deleg_bulk_row"))
        self.assertEqual(body.count("un_deleg_bulk_budget"), 1)
        self.assertTrue(body.rstrip().endswith("remove_variable = un_bulk_left"))

    def test_the_run_visits_every_row_top_down(self):
        body = _block(self.effects, "un_deleg_bulk_lobby")
        calls = re.findall(r"un_deleg_bulk_row\s*=\s*\{\s*N\s*=\s*(\d+)\s+DIR\s*=\s*\$DIR\$\s*\}", body)
        self.assertEqual(calls, [str(n) for n in range(DELEGATION_ROWS)])

    def test_a_row_spends_one_campaign_from_the_budget_and_starts_the_rows_own(self):
        row = _block(self.effects, "un_deleg_bulk_row")
        limit = _sub_block(row, "limit")
        self.assertIn("var:un_bulk_left > 0", limit)
        self.assertRegex(limit, r"un_deleg_row_bulk_ok\s*=\s*\{\s*N\s*=\s*\$N\$\s+DIR\s*=\s*\$DIR\$\s*\}")
        self.assertLess(
            row.index("un_deleg_row_lobby = { N = $N$ DIR = $DIR$ }"),
            row.index("change_variable = { name = un_bulk_left add = -1 }"),
        )

    def test_a_row_qualifies_by_the_band_the_chamber_shows(self):
        ok = _block(self.triggers, "un_deleg_row_bulk_ok")
        for needle in (
            "un_lobby_member_lobbyable = yes",
            "un_deleg_band_open_$DIR$ = yes",
            "type = un_lobby_for_action",
            "type = un_lobby_against_action",
            "can_send_diplomatic_action",
        ):
            self.assertIn(needle, ok)
        # the engine's own send check is the last word, and affordability is
        # the budget's, not a live read that a pact made a moment ago may not
        # have reached
        self.assertNotIn("can_afford_diplomatic_action", ok)
        for name, test in (
            ("un_deleg_band_open_for", r"var:un_lean_shown\s*<\s*un_lean_band_lean\b"),
            ("un_deleg_band_open_against", r"var:un_lean_shown\s*>\s*un_lean_band_lean_against\b"),
        ):
            band = _block(self.triggers, name)
            with self.subTest(band=name):
                self.assertRegex(band, test)
                self.assertNotIn("un_lean_total", band)

    def test_the_button_is_valid_only_with_a_vote_a_campaign_s_influence_and_a_row(self):
        can = _block(self.triggers, "un_deleg_bulk_can")
        self.assertIn("un_lobby_campaign_selectable = yes", can)
        self.assertRegex(can, r"influence\s*>=\s*un_lobby_campaign_cost")
        self.assertLess(can.index("influence >="), can.index("un_deleg_row_bulk_ok"))
        calls = re.findall(r"un_deleg_row_bulk_ok\s*=\s*\{\s*N\s*=\s*(\d+)\s+DIR\s*=\s*\$DIR\$\s*\}", can)
        self.assertEqual(calls, [str(n) for n in range(DELEGATION_ROWS)])

    def test_each_sgui_passes_its_own_direction(self):
        for d in ("for", "against"):
            body = _block(self.sguis, f"un_chamber_deleg_bulk_{d}_sgui")
            with self.subTest(direction=d):
                self.assertIn(f"un_deleg_bulk_can = {{ DIR = {d} }}", _sub_block(body, "is_valid"))
                effect = _sub_block(body, "effect")
                self.assertIn(f"un_deleg_bulk_lobby = {{ DIR = {d} }}", _sub_block(effect, "hidden_effect"))
                self.assertIn(f"custom_tooltip = un_deleg_bulk_{d}_effect_tt", effect)
                self.assertIn("ai_is_valid = { always = no }", body)
                self.assertNotIn("scope:op", body)

    def test_the_widget_wires_each_button_to_its_own_sgui_only(self):
        buttons = re.findall(r"un_chamber_deleg_bulk_button\s*=\s*\{", self.widget)
        self.assertEqual(len(buttons), 2)
        for d, other in (("for", "against"), ("against", "for")):
            start = self.widget.index(f"je_un_chamber_deleg_bulk_{d}_label")
            body = _braced(self.widget, self.widget.rindex("un_chamber_deleg_bulk_button", 0, start))
            with self.subTest(direction=d):
                self.assertIn(f"un_chamber_deleg_bulk_{d}_sgui", body)
                self.assertNotIn(f"un_chamber_deleg_bulk_{other}_sgui", body)
                for accessor in ("IsValid(", "Execute(", "IsValidTooltip(", "ExecuteTooltip("):
                    self.assertIn(accessor, body)

    def test_the_text_exists(self):
        for key in (
            "je_un_chamber_deleg_bulk_for_label",
            "je_un_chamber_deleg_bulk_against_label",
            "un_deleg_bulk_for_effect_tt",
            "un_deleg_bulk_against_effect_tt",
            "un_deleg_bulk_target_for_tt",
            "un_deleg_bulk_target_against_tt",
        ):
            with self.subTest(key=key):
                self.assertIn(key, self.loc)
        for d in ("for", "against"):
            self.assertIn("un_deleg_bulk_budget", self.loc[f"un_deleg_bulk_{d}_effect_tt"])


if __name__ == "__main__":
    unittest.main()
