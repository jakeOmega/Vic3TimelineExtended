# -*- coding: utf-8 -*-
"""What a revolution's winner takes over from the loser's central bank (#462).

``te_monetary_inherit_central_bank`` (common/scripted_effects/
te_monetary_civil_war_effects.txt) copies the loser's monetary state onto the
winner at ``on_civil_war_won``. Its safety rests on a classification: state and
choices are copied, while bookkeeping that records which modifier is physically
on which object is not — copying an ``_applied`` tracker without its modifier
is audit F7's bug. The engine checks none of this, so these tests do:

* every variable the effect writes is one the monetary system itself writes;
* no tracker is copied;
* every monetary variable is classified — copied, or listed in NOT_COPIED
  below — so a new contract variable fails here until someone decides;
* the copy is reached only through the rebel-win guard on the shared pointer,
  which is set at revolutions and never at secessions.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


EFFECTS = _path("common", "scripted_effects", "te_monetary_civil_war_effects.txt")
ON_ACTIONS = _path("common", "on_actions", "te_monetary_on_actions.txt")

# The files whose variables make up the monetary contract.
MONETARY_FILES = [
    ("common", "scripted_effects", "te_monetary_effects.txt"),
    ("common", "scripted_effects", "te_monetary_fx_effects.txt"),
    ("common", "scripted_effects", "te_monetary_arrangement_effects.txt"),
    ("common", "scripted_effects", "te_monetary_union_effects.txt"),
    ("common", "scripted_guis", "te_monetary_sguis.txt"),
    ("common", "on_actions", "te_monetary_on_actions.txt"),
    ("events", "te_peg_events.txt"),
    ("events", "te_inflation_events.txt"),
    ("events", "te_monetary_arrangement_events.txt"),
]

# Group (d) of the effect's header: deliberately NOT taken from the loser.
NOT_COPIED = {
    # Trackers: which modifier is physically on which object.
    "te_rate_paid_applied", "te_rate_paid_rooted", "te_mon_mod_home",
    "te_inflation_band_applied", "te_monetisation_minting_applied",
    "te_mon_stance_politics_applied", "te_mon_wage_dividend_applied",
    "te_gold_carry_applied", "te_fx_weak_applied", "te_fx_strong_applied",
    "te_capital_controls_fatigue_applied", "te_mon_arr_recipient_applied",
    "te_mon_arr_provider_applied", "te_mon_arr_standing_applied",
    "te_mon_board_lever_applied", "te_mon_board_seigniorage_applied",
    "te_mon_union_adopter_applied", "te_mon_union_banking_applied",
    "te_mon_union_reserve_applied", "te_mon_union_pressure_applied",
    "te_mon_union_seigniorage_applied",
    # Recomputed from scratch by the monthly update or the discovery.
    "te_mon_regime", "te_premium_structural", "te_premium_cyclical",
    "te_rate_paid_pts", "te_market_yield", "te_mon_deficit_pct",
    "te_neutral_rate", "te_mon_stance_gap", "te_mon_stance_band",
    "te_mon_stance_bar_pos", "te_cost_push", "te_basket_index",
    "te_basket_avg", "te_basket_market_owner", "te_gold_flow",
    "te_gold_flow_gap", "te_gold_flow_pct", "te_gold_carry",
    "te_mon_overvaluation", "te_fx_imported", "te_mon_anchor_kind_new",
    "te_mon_anchor_rate", "te_mon_anchor_fx_index", "te_mon_anchor_c",
    "te_mon_anchor_target", "te_mon_arr_recipient_pts",
    "te_mon_arr_provider_pts", "te_mon_arr_standing_pts",
    "te_mon_union_holdouts", "te_mon_union_refusers",
    "te_mon_union_seigniorage_pts", "te_mon_commodity_centre",
    # Per-pulse copies of world figures, and the global passes' shares.
    "te_mon_era_base_now", "te_mon_world_rate_now",
    "te_mon_world_inflation_now", "te_mon_world_own_num",
    "te_mon_world_own_den", "te_mon_world_infl_own_num",
    "te_mon_world_infl_own_den", "te_mon_anchored_gdp_m",
    # Scratch.
    "te_mon_work", "te_mon_work2", "te_mon_work_gdp", "te_mon_work_gdp_m",
    "te_mon_recap_work",
    # Event temporaries (120-day display flags on the ward).
    "te_lolr_answer", "te_lolr_paid",
}

# Written by the effect other than through a copy, each for a stated reason:
# the seeded flag rides with the summed vault, the basket is re-seeded, the
# scan flag sends the arrangements through the discovery, and te_mon_work is
# the scratch the timed-modifier ladder reads.
DIRECT_WRITES = {
    "te_bank_gold", "te_gold_hot_money", "te_bank_gold_seeded",
    "te_basket_seeded", "te_mon_arr_scan", "te_mon_work",
    "te_mon_anchor", "te_mon_swap_provider", "te_mon_lolr_guarantor",
    "te_mon_receiver",
}

WRITE = re.compile(
    r"(?:set_variable|change_variable|clamp_variable)\s*=\s*\{\s*name\s*=\s*(te_\w+)"
)


def _monetary_variables():
    names = set()
    for parts in MONETARY_FILES:
        names |= set(WRITE.findall(_read(_path(*parts))))
    # The shared civil-war parent pointer lives in the monetary on-actions file
    # but is not a monetary variable.
    names.discard("te_cw_parent")
    return names


def _copied():
    body = _block(_read(EFFECTS), "te_monetary_inherit_central_bank")
    take = set(re.findall(r"te_mon_cw_take\s*=\s*\{\s*VAR\s*=\s*(\w+)", body))
    take_scope = set(re.findall(r"te_mon_cw_take_scope\s*=\s*\{\s*VAR\s*=\s*(\w+)", body))
    return take, take_scope, body


class ClassificationTests(unittest.TestCase):
    def test_every_copied_variable_is_a_monetary_one(self):
        take, take_scope, body = _copied()
        written = set(WRITE.findall(body))
        known = _monetary_variables()
        for name in sorted(take | take_scope | written):
            with self.subTest(variable=name):
                self.assertIn(name, known, "not written by the monetary system")

    def test_no_tracker_is_copied(self):
        take, take_scope, body = _copied()
        for name in sorted(take | take_scope | set(WRITE.findall(body))):
            with self.subTest(variable=name):
                self.assertFalse(name.endswith("_applied"), "an _applied tracker is written")
        self.assertEqual(sorted((take | take_scope) & NOT_COPIED), [])

    def test_every_monetary_variable_is_classified(self):
        take, take_scope, body = _copied()
        classified = take | take_scope | set(WRITE.findall(body)) | NOT_COPIED
        missing = sorted(
            name for name in _monetary_variables() - classified
            if not name.startswith("te_mon_debug_")
        )
        self.assertEqual(
            missing, [],
            "classify these in te_monetary_civil_war_effects.txt (copy them) or "
            "in NOT_COPIED here (and say why in the effect's header)",
        )

    def test_not_copied_names_still_exist(self):
        stale = sorted(NOT_COPIED - _monetary_variables())
        self.assertEqual(stale, [])

    def test_direct_writes_are_the_documented_ones(self):
        _take, _take_scope, body = _copied()
        effects = _read(EFFECTS)
        written = set(WRITE.findall(body))
        written |= set(WRITE.findall(_block(effects, "te_mon_cw_repoint_to_winner")))
        self.assertEqual(written, DIRECT_WRITES)

    def test_the_vault_is_added_not_replaced(self):
        body = _copied()[2]
        self.assertRegex(
            body, r"change_variable\s*=\s*\{\s*name\s*=\s*te_bank_gold\s+add\s*=\s*"
            r"scope:te_cw_loser\.var:te_bank_gold")
        self.assertRegex(
            body, r"change_variable\s*=\s*\{\s*name\s*=\s*te_gold_hot_money\s+add\s*=\s*"
            r"scope:te_cw_loser\.var:te_gold_hot_money")
        # The inheritance guard: an equal vault is the loser's own, inherited.
        self.assertIn("NOT = { var:te_bank_gold = scope:te_cw_loser.var:te_bank_gold }", body)

    def test_timed_modifier_durations_are_literals(self):
        ladder = _block(_read(EFFECTS), "te_mon_cw_add_timed")
        durations = re.findall(r"\b(?:days|months|years)\s*=\s*(\S+)", ladder)
        self.assertTrue(durations)
        for value in durations:
            with self.subTest(duration=value):
                self.assertRegex(value, r"^\d+$")


class WiringTests(unittest.TestCase):
    def test_the_copy_runs_only_behind_the_rebel_win_guard(self):
        text = _read(ON_ACTIONS)
        self.assertRegex(
            _block(text, "on_civil_war_won"),
            r"on_actions\s*=\s*\{\s*te_monetary_on_civil_war_won\s+te_civil_war_drop_self_parent\s*\}")
        body = _block(text, "te_monetary_on_civil_war_won")
        guard = re.search(
            r"limit\s*=\s*\{\s*var:te_cw_parent\s*\?=\s*\{\s*NOT\s*=\s*\{\s*this\s*=\s*root\s*\}"
            r"\s*is_country_alive\s*=\s*no\s*has_variable\s*=\s*te_rate_paid_pts"
            r"\s*var:te_rate_paid_pts\s*>=\s*0\.5\s*\}\s*\}", body)
        self.assertIsNotNone(guard)
        self.assertEqual(body.count("te_monetary_inherit_central_bank"), 1)
        self.assertGreater(body.index("te_monetary_inherit_central_bank"), guard.end())
        self.assertLess(body.index("te_monetary_inherit_central_bank"), body.index("else_if"))
        # Nowhere else calls it.
        for root, _dirs, files in os.walk(_path("common")):
            for name in files:
                if not name.endswith(".txt") or name == "te_monetary_on_actions.txt":
                    continue
                with self.subTest(file=name):
                    text = _read(os.path.join(root, name))
                    self.assertNotRegex(text, r"te_monetary_inherit_central_bank\s*=\s*yes")

    def test_pointer_is_set_at_revolutions_and_never_at_secessions(self):
        text = _read(ON_ACTIONS)
        revolution = _block(text, "on_revolution_start")
        secession = _block(text, "on_secession_start")
        self.assertIn("te_civil_war_record_parent", revolution)
        self.assertNotIn("te_civil_war_record_parent", secession)
        self.assertIn("te_civil_war_forget_parent", secession)
        record = _block(text, "te_civil_war_record_parent")
        self.assertRegex(
            record, r"scope:target\s*\?=\s*\{\s*set_variable\s*=\s*\{\s*name\s*=\s*te_cw_parent"
            r"\s+value\s*=\s*root\s*\}")
        # The original forgets any old pointer at every start.
        for name in ("te_civil_war_record_parent", "te_civil_war_forget_parent"):
            with self.subTest(on_action=name):
                self.assertRegex(
                    _block(text, name),
                    r"^\s*effect\s*=\s*\{\s*if\s*=\s*\{\s*limit\s*=\s*\{\s*has_variable\s*=\s*"
                    r"te_cw_parent\s*\}\s*remove_variable\s*=\s*te_cw_parent")

    def test_every_loser_read_is_through_the_saved_scope(self):
        effects = _read(EFFECTS)
        self.assertNotIn("var:te_cw_parent", effects)
        self.assertNotIn("prev", effects)


if __name__ == "__main__":
    unittest.main()
