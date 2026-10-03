# -*- coding: utf-8 -*-
"""The UN's AI pairs: each on/off button pair reads one score and one line.

common/script_values/un_ai_values.txt gives six button pairs (Join / Leave,
Pay / Withhold dues, Fund / Stop funding Development Programs, Contribute to /
End peacekeeping, Champion / Stop championing and Undermine / Stop undermining
the order) one score per country. The "on" button scores only at or
above a line, the "off" button only a band below it, so a country does not
toggle (docs/systems/un_redesign_design.md §0.13; the same shape as
test_gw_ai_policy_table.py). Nothing in the engine notices when a pair drifts
apart -- an off line above its on line flips the pair every roll, and an on
weight with no off weight is the old ratchet -- so these tests do. They also
pin the money term to the Fund's single-source prospect and the levy, and the
header table to the code.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


VALUES = _path("common", "script_values", "un_ai_values.txt")
ECONOMY = _path("common", "script_values", "un_economy_values.txt")
BUTTONS = _path("common", "scripted_buttons", "un_buttons.txt")
JE = _path("common", "journal_entries", "je_united_nations.txt")

# (on button, off button, score, on line, off line, band, on chance, off chance)
PAIRS = (
    ("un_join_button", "un_leave_button", "un_ai_membership_will",
     "un_ai_membership_join_line", "un_ai_membership_leave_line", "un_ai_membership_band",
     "un_join_ai_chance", "un_leave_ai_chance"),
    ("un_pay_dues_button", "un_withhold_dues_button", "un_ai_dues_will",
     "un_ai_dues_pay_line", "un_ai_dues_withhold_line", "un_ai_dues_band",
     "un_pay_dues_ai_chance", "un_withhold_dues_ai_chance"),
    ("un_fund_development_button", "un_defund_development_button", "un_ai_development_will",
     "un_ai_development_line", "un_ai_development_stop_line", "un_ai_development_band",
     "un_fund_development_ai_chance", "un_defund_development_ai_chance"),
    ("un_peacekeeping_mission_button", "un_end_peacekeeping_button", "un_ai_peacekeeping_will",
     "un_ai_peacekeeping_line", "un_ai_peacekeeping_stop_line", "un_ai_peacekeeping_band",
     "un_peacekeeping_ai_chance", "un_end_peacekeeping_ai_chance"),
    ("un_champion_order_button", "un_stop_championing_button", "un_ai_order_will",
     "un_ai_order_line", "un_ai_order_stop_line", "un_ai_order_band",
     "un_champion_order_ai_chance", "un_stop_championing_ai_chance"),
    ("un_undermine_order_button", "un_stop_undermining_button", "un_ai_dissent_will",
     "un_ai_order_line", "un_ai_order_stop_line", "un_ai_order_band",
     "un_undermine_order_ai_chance", "un_stop_undermining_ai_chance"),
)

# The header table's score column, by pair.
TABLE_SCORES = {p[2] for p in PAIRS}


def _raw(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _read(path):
    return re.sub(r"#[^\n]*", "", _raw(path))


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


def _constant(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{\s*value\s*=\s*(-?\d+(?:\.\d+)?)\s*\}", text, re.M)
    if m is None:
        raise AssertionError(f"{name} is not a constant")
    return float(m.group(1))


def _ai_chance(buttons, button):
    body = _block(buttons, button)
    i = body.index("ai_chance")
    return body[i:body.index("}", i) + 1]


class UnAiPairsTest(unittest.TestCase):
    def setUp(self):
        self.values = _read(VALUES)
        self.buttons = _read(BUTTONS)

    def test_every_pair_is_registered_on_the_entry(self):
        registered = set(re.findall(r"(?m)^\s*scripted_button = (\w+)", _read(JE)))
        for pair in PAIRS:
            for button in pair[:2]:
                self.assertIn(button, registered)

    def test_each_button_reads_its_own_chance(self):
        for on, off, *_rest, on_chance, off_chance in PAIRS:
            for button, chance in ((on, on_chance), (off, off_chance)):
                with self.subTest(button=button):
                    block = _ai_chance(self.buttons, button)
                    self.assertRegex(block, r"ai_chance\s*=\s*\{\s*value\s*=\s*" + chance + r"\s*\}")
                    _block(self.values, chance)

    def test_on_scores_at_or_above_the_line_off_below_the_off_line(self):
        for _on, _off, score, on_line, off_line, _band, on_chance, off_chance in PAIRS:
            with self.subTest(score=score):
                on = _block(self.values, on_chance)
                off = _block(self.values, off_chance)
                self.assertIn(f"{score} >= {on_line}", on)
                self.assertIn(f"{score} < {off_line}", off)
                # Each reads only its own score.
                self.assertEqual(set(re.findall(r"un_ai_\w+_will", on)), {score})
                self.assertEqual(set(re.findall(r"un_ai_\w+_will", off)), {score})

    def test_off_line_is_the_band_below_the_on_line(self):
        for *_buttons, score, on_line, off_line, band, _on, _off in PAIRS:
            with self.subTest(score=score):
                body = _block(self.values, off_line)
                self.assertRegex(body, r"^\s*value\s*=\s*" + on_line + r"\s+subtract\s*=\s*" + band + r"\s*$")

    def test_every_band_is_wider_than_any_self_flipping_term(self):
        flipping = _constant(self.values, "un_ai_self_flipping_terms")
        for *_buttons, score, _on_line, _off_line, band, _on, _off in PAIRS:
            with self.subTest(score=score):
                self.assertGreater(_constant(self.values, band), flipping)

    def test_membership_score_reads_no_war(self):
        # A war flips on its own; on the membership score it would move a
        # country in and out of the UN with every war it is dragged into.
        self.assertNotIn("is_at_war", _block(self.values, "un_ai_membership_will"))

    def test_header_table_matches_the_lines(self):
        rows = {}
        for line in _raw(VALUES).splitlines():
            m = re.match(r"#\s+[a-z /]+?\s+(un_ai_\w+_will)\s+(-?\d+)\s+(-?\d+)\s", line)
            if m:
                rows[m.group(1)] = (int(m.group(2)), int(m.group(3)))
        self.assertEqual(set(rows), TABLE_SCORES)
        for *_buttons, score, on_line, _off_line, band, _on, _off in PAIRS:
            with self.subTest(score=score):
                on = _constant(self.values, on_line)
                self.assertEqual(rows[score], (on, on - _constant(self.values, band)))


class UnAiStanceTest(unittest.TestCase):
    """Champion and undermine read one signed stance; authority only nudges it."""

    def setUp(self):
        self.values = _read(VALUES)

    def test_dissent_is_minus_the_order_stance(self):
        self.assertRegex(_block(self.values, "un_ai_dissent_will"),
                         r"^\s*value\s*=\s*0\s+subtract\s*=\s*un_ai_order_will\s*$")

    def test_authority_alone_never_crosses_the_band(self):
        # The owner (2026-10-03): a mild pull from authority, but a power with
        # good reasons either way must not switch on authority alone. Its whole
        # swing (authority 0 to 100) stays inside the band.
        will = _block(self.values, "un_ai_order_will")
        self.assertRegex(will, r"value\s*=\s*50\s+subtract\s*=\s*un_ai_authority\s+multiply\s*=\s*un_ai_order_authority_weight")
        swing = 100 * _constant(self.values, "un_ai_order_authority_weight")
        self.assertLess(swing, _constant(self.values, "un_ai_order_band"))
        self.assertLessEqual(swing, _constant(self.values, "un_ai_self_flipping_terms"))
        # No step on authority anywhere else in the stance.
        self.assertNotIn("global_var:un_authority", will)


class UnAiMembershipCrisisTest(unittest.TestCase):
    def test_a_failing_un_costs_membership_gradually(self):
        # Gradual, not the old cliff (owner, 2026-10-03): a continuous term
        # below a start line, no step on the Moribund tier.
        values = _read(VALUES)
        will = _block(values, "un_ai_membership_will")
        self.assertIn("un_ai_authority < un_ai_membership_crisis_start", will)
        self.assertIn("multiply = un_ai_membership_crisis_per_point", will)
        self.assertNotIn("un_tier_is_moribund", will)


class UnPeacekeepingDeploymentCostTest(unittest.TestCase):
    def test_a_full_force_costs_money_unless_the_programme_pays(self):
        # Owner, 2026-10-03: un_events.4 A should charge the programme's cost.
        events = _read(_path("events", "un_events.txt"))
        option = _block(events, "un_events.4")
        a = option[option.index("name = un_events.4.a"):option.index("name = un_events.4.b")]
        self.assertRegex(a, r"NOT\s*=\s*\{\s*un_standing_program_active_peacekeeping\s*=\s*yes\s*\}\s*\}\s*add_modifier\s*=\s*\{\s*name\s*=\s*un_peacekeeping_deployment_cost\s+multiplier\s*=\s*un_program_expense_value")
        modifiers = _read(_path("common", "static_modifiers", "extra_modifiers.txt"))
        self.assertIn("country_expenses_add = 1", _block(modifiers, "un_peacekeeping_deployment_cost"))


class UnAiMoneyTest(unittest.TestCase):
    def setUp(self):
        self.values = _read(VALUES)
        self.economy = _read(ECONOMY)

    def test_money_term_is_the_prospect_less_the_levy(self):
        money = _block(self.values, "un_ai_money_points")
        self.assertIn("value = un_dev_fund_prospect_share", money)
        self.assertIn("subtract = un_dues_rate", money)
        self.assertIn("multiply = un_ai_points_per_gdp_share", money)

    def test_membership_and_dues_both_count_the_money(self):
        for score in ("un_ai_membership_will", "un_ai_dues_will"):
            with self.subTest(score=score):
                self.assertIn("add = un_ai_money_points", _block(self.values, score))

    def test_the_fund_offsets_the_treasury_case_against_dues(self):
        will = _block(self.values, "un_ai_dues_will")
        self.assertRegex(will, r"value\s*=\s*un_ai_treasury_penalty\s+multiply\s*=\s*un_ai_dues_net_cost_factor")
        factor = _block(self.values, "un_ai_dues_net_cost_factor")
        self.assertIn("un_dev_fund_prospect_value", factor)
        self.assertIn("un_dues_weekly_value", factor)

    def test_the_prospect_lives_with_the_fund(self):
        # One source for the Fund's figures (un_economy_values.txt's header).
        for name in ("un_dev_fund_prospect_value", "un_dev_fund_prospect_share",
                     "un_dev_fund_grant_preview_share"):
            with self.subTest(name=name):
                _block(self.economy, name)
                self.assertNotRegex(self.values, r"(?m)^" + name + r"\s*=")

    def test_the_fund_lean_scales_with_the_grant(self):
        lean = _block(self.economy, "un_lean_interests_development_fund")
        self.assertIn("un_dev_fund_grant_preview_share", lean)
        self.assertIn("multiply = un_ai_points_per_gdp_share", lean)
        chance = _block(self.economy, "un_development_fund_ai_chance")
        self.assertIn("un_dev_fund_grant_preview_share", chance)


if __name__ == "__main__":
    unittest.main()
