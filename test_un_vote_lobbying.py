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

from test_un_chamber_mission_slots import _block, _braced, _read, _sub_block

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
        self.assertNotIn("is_ai", refresh)
        self.assertIn("trigger_event = { id = un_vote.4 }", refresh)


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


if __name__ == "__main__":
    unittest.main()
