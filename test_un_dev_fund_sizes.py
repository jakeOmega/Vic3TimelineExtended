# -*- coding: utf-8 -*-
"""Development Programs contribution sizes (owner, 2026-10-05; five since
2026-10-06).

A contribution to the World Development Fund comes in five sizes, Token to
Generous, each doubling the money and adding a quarter of Substantial's
benefits (common/script_values/un_economy_values.txt). Its benefits scale by
the size's factor, the UN's funding pillar counts its money rather than who
gives it, and the members the Fund pays are more receptive to a contributor's
lobbying through two reusable modifier types. Nothing in the engine notices
when one of these drifts (a modifier added without its multiplier silently
grants Substantial's benefits at every size), so these tests do.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


def _raw(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _read(path):
    return re.sub(r"#[^\n]*", "", _raw(path))


def _flat(text):
    return re.sub(r"\s+", " ", text).strip()


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


ECONOMY = _path("common", "script_values", "un_economy_values.txt")
AI = _path("common", "script_values", "un_ai_values.txt")
AUTHORITY = _path("common", "script_values", "un_authority_values.txt")
AUTHORITY_EFFECTS = _path("common", "scripted_effects", "un_authority_effects.txt")
STANDING = _path("common", "script_values", "un_standing_values.txt")
LOBBYING = _path("common", "script_values", "un_lobbying_values.txt")
LOBBY_ACTIONS = _path("common", "diplomatic_actions", "un_lobbying.txt")
ECONOMY_EFFECTS = _path("common", "scripted_effects", "un_economy_effects.txt")
BUTTONS = _path("common", "scripted_buttons", "un_buttons.txt")
JE = _path("common", "journal_entries", "je_united_nations.txt")
MODIFIERS = _path("common", "static_modifiers", "extra_modifiers.txt")
TYPES = _path("common", "modifier_type_definitions", "un_membership_modifier_types.txt")
LOC_DIR = _path("localization", "english")

SIZES = ("token", "small", "modest", "substantial", "generous")
SUBSTANTIAL = SIZES.index("substantial")


def _loc():
    out = []
    for name in sorted(os.listdir(LOC_DIR)):
        if name.endswith(".yml"):
            out.append(_raw(os.path.join(LOC_DIR, name)))
    return "\n".join(out)


def _script_files():
    for root in ("common", "events"):
        for dirpath, _dirs, files in os.walk(_path(root)):
            for f in files:
                if f.endswith(".txt"):
                    yield os.path.join(dirpath, f)


class SizeTableTest(unittest.TestCase):
    def setUp(self):
        self.values = _read(ECONOMY)

    def test_each_size_doubles_the_money(self):
        rates = [_constant(self.values, f"un_dev_fund_pct_{s}") for s in SIZES]
        for low, high in zip(rates, rates[1:]):
            self.assertAlmostEqual(high, 2 * low)
        # Substantial is what the programme cost before the sizes, so a
        # contribution from an older save (the legacy size) pays as it did.
        self.assertAlmostEqual(rates[SUBSTANTIAL], 0.5)
        self.assertEqual(_constant(self.values, "un_dev_fund_size_legacy"), SUBSTANTIAL + 1)
        self.assertEqual(_constant(self.values, "un_dev_fund_size_max"), len(SIZES))

    def test_each_doubling_adds_a_quarter_of_substantial(self):
        benefits = [_constant(self.values, f"un_dev_fund_benefit_{s}") for s in SIZES]
        self.assertEqual(benefits[SUBSTANTIAL], 1)
        self.assertGreater(benefits[0], 0)
        for low, high in zip(benefits, benefits[1:]):
            self.assertAlmostEqual(high - low, 0.25)

    def test_header_table_matches_the_figures(self):
        rows = re.findall(r"#\s+(\d)\s+(\w+)\s+([\d.]+)%\s+([\d.]+)", _raw(ECONOMY))
        self.assertEqual([r[1].lower() for r in rows], list(SIZES))
        for size, (num, _name, pct, benefit) in zip(SIZES, rows):
            with self.subTest(size=size):
                self.assertAlmostEqual(float(pct), _constant(self.values, f"un_dev_fund_pct_{size}"))
                self.assertAlmostEqual(float(benefit), _constant(self.values, f"un_dev_fund_benefit_{size}"))

    def test_rate_and_benefit_read_the_stored_size(self):
        for name in ("un_dev_fund_pct_value", "un_dev_fund_benefit_value"):
            body = _flat(_block(self.values, name))
            for n in range(len(SIZES), 1, -1):
                self.assertIn(f"un_dev_fund_size_stored >= {n}", body)
        expense = _flat(_block(self.values, "un_dev_fund_expense_value"))
        self.assertEqual(expense, "value = gdp multiply = un_dev_fund_pct_value divide = 100 divide = 52")
        for size in SIZES:
            with self.subTest(size=size):
                cost = _flat(_block(self.values, f"un_disp_dev_fund_cost_{size}"))
                self.assertEqual(cost, f"value = gdp multiply = un_dev_fund_pct_{size} divide = 100 divide = 52")


class BenefitModifierTest(unittest.TestCase):
    def test_benefits_are_reputation_not_bureaucracy(self):
        body = _block(_read(MODIFIERS), "un_development_contributor_modifier")
        self.assertIn("country_infamy_decay_mult", body)
        self.assertIn("country_prestige_mult", body)
        self.assertNotIn("bureaucracy", body)
        self.assertNotIn("ministry_of_commerce", body)

    def test_every_add_scales_by_the_size(self):
        # Without its multiplier the modifier grants Substantial's benefits at
        # any size.
        pattern = re.compile(r"add_modifier\s*=\s*\{\s*name\s*=\s*un_development_contributor_modifier\b([^}]*)\}")
        found = 0
        for path in _script_files():
            for m in pattern.finditer(_read(path)):
                found += 1
                with self.subTest(path=os.path.relpath(path, REPO)):
                    self.assertRegex(m.group(1), r"multiplier\s*=\s*root\.var:un_dev_fund_benefit\b")
        self.assertGreaterEqual(found, 3)  # the button, the resize, the restore

    def test_patron_modifier_and_its_display_agree(self):
        body = _block(_read(MODIFIERS), "un_development_patron_modifier")
        m = re.search(r"country_un_lobbying_fund_recipients_mult\s*=\s*([\d.]+)", body)
        self.assertIsNotNone(m)
        self.assertAlmostEqual(float(m.group(1)) * 100,
                               _constant(_read(ECONOMY), "un_dev_fund_patron_unit_pct"))

    def test_standing_accrues_at_the_size_factor(self):
        body = _flat(_block(_read(STANDING), "un_standing_program_accrual_count"))
        dev = body[body.index("un_standing_months_development"):]
        self.assertIn("add = un_dev_fund_benefit_value", dev[:dev.index("}") + 40])


class ButtonsTest(unittest.TestCase):
    def setUp(self):
        self.buttons = _read(BUTTONS)

    def test_any_rank_may_give_but_not_a_recipient_or_a_withholder(self):
        possible = _flat(_block(self.buttons, "un_fund_development_button"))
        self.assertNotIn("country_rank", possible)
        self.assertIn("NOT = { un_dev_fund_receiving = yes }", possible)
        self.assertIn("NOT = { un_dues_is_withholding = yes }", possible)

    def test_a_contribution_starts_at_token(self):
        effect = _flat(_block(self.buttons, "un_fund_development_button"))
        start = effect.index("set_variable = { name = un_dev_fund_size value = 1 }")
        self.assertLess(start, effect.index("un_dev_fund_benefit_value"))
        self.assertLess(start, effect.index("un_dev_fund_expense_value"))

    def test_raise_and_reduce_are_registered_and_move_one_size(self):
        registered = set(re.findall(r"(?m)^\s*scripted_button = (\w+)", _read(JE)))
        effects = _read(ECONOMY_EFFECTS)
        for button, effect, step in (("un_raise_development_button", "un_dev_fund_raise", "1"),
                                     ("un_reduce_development_button", "un_dev_fund_reduce", "-1")):
            with self.subTest(button=button):
                self.assertIn(button, registered)
                self.assertIn(f"{effect} = yes", _flat(_block(self.buttons, button)))
                self.assertIn(f"un_dev_fund_resize = {{ STEP = {step} }}", _flat(_block(effects, effect)))
        resize = _flat(_block(effects, "un_dev_fund_resize"))
        self.assertIn("clamp_variable = { name = un_dev_fund_size min = 1 max = un_dev_fund_size_max }", resize)

    def test_every_size_has_its_tooltips(self):
        # Raise names the size it moves to (all but Token), Reduce likewise
        # (all but Generous), and Our Obligations names every size.
        effects = _read(ECONOMY_EFFECTS)
        loc = _loc()
        raise_, reduce_ = (_flat(_block(effects, e)) for e in ("un_dev_fund_raise", "un_dev_fund_reduce"))
        obligations = _flat(_block(effects, "un_economy_obligation_lines"))
        for size in SIZES:
            with self.subTest(size=size):
                self.assertEqual(size != "token", f"un_dev_fund_to_{size}_tt" in raise_)
                self.assertEqual(size != "generous", f"un_dev_fund_to_{size}_tt" in reduce_)
                self.assertIn(f"je_un_chamber_dev_fund_contributor_{size}", obligations)
                self.assertRegex(loc, r"(?m)^ un_dev_fund_to_" + size + r"_tt:0 ")
                self.assertRegex(loc, r"(?m)^ je_un_chamber_dev_fund_contributor_" + size + r":0 ")
                self.assertIn(f"un_disp_dev_fund_cost_{size} = {{", _read(ECONOMY))


class FourSizeSaveTest(unittest.TestCase):
    """A save from the four sizes (2026-10-05) stored 1 for what is now Small.

    Every write of the size since the five sizes sets var:un_dev_fund_five_sizes
    with it, so a size without that marker reads a size up and keeps its money
    and benefit factor.
    """

    def test_an_unmarked_size_reads_a_size_up(self):
        stored = _flat(_block(_read(ECONOMY), "un_dev_fund_size_stored"))
        self.assertIn("add = var:un_dev_fund_size if = { limit = { NOT = { has_variable = un_dev_fund_five_sizes } } "
                      "add = 1 }", stored)

    def test_every_size_write_marks_it(self):
        writes = 0
        for path in _script_files():
            for line in _read(path).splitlines():
                if re.search(r"set_variable\s*=\s*\{\s*name\s*=\s*un_dev_fund_size\b", line):
                    writes += 1
        self.assertEqual(writes, 3)  # the button, the resize, the monthly pulse
        button = _flat(_block(_read(BUTTONS), "un_fund_development_button"))
        self.assertIn("set_variable = { name = un_dev_fund_size value = 1 } set_variable = un_dev_fund_five_sizes", button)
        effects = _read(ECONOMY_EFFECTS)
        resize = _flat(_block(effects, "un_dev_fund_resize"))
        self.assertIn("set_variable = { name = un_dev_fund_size value = un_dev_fund_size_stored } "
                      "set_variable = un_dev_fund_five_sizes", resize)
        monthly = _flat(_block(effects, "un_dev_fund_contribution_monthly"))
        self.assertIn("limit = { NOT = { has_variable = un_dev_fund_five_sizes } } "
                      "set_variable = { name = un_dev_fund_size value = un_dev_fund_size_stored } "
                      "set_variable = un_dev_fund_five_sizes", monthly)

    def test_the_patron_pulse_runs_for_members_and_non_members(self):
        # Before the member block, so the goodwill fades once a member leaves.
        raw = _raw(JE)
        self.assertEqual(raw.count("un_dev_fund_patron_pulse = yes"), 1)
        self.assertLess(raw.index("un_dev_fund_patron_pulse = yes"), raw.index("# ---- Member-only logic ----"))


class AiSizeTest(unittest.TestCase):
    def setUp(self):
        self.values = _read(AI)
        self.buttons = _read(BUTTONS)

    def test_size_buttons_read_the_generosity_score(self):
        for button, chance in (("un_raise_development_button", "un_raise_development_ai_chance"),
                               ("un_reduce_development_button", "un_reduce_development_ai_chance")):
            with self.subTest(button=button):
                self.assertRegex(_flat(_block(self.buttons, button)),
                                 r"ai_chance = \{ value = " + chance + r" \}")
        raise_chance = _flat(_block(self.values, "un_raise_development_ai_chance"))
        reduce_chance = _flat(_block(self.values, "un_reduce_development_ai_chance"))
        self.assertIn("un_ai_development_generosity >= un_ai_development_raise_line", raise_chance)
        self.assertIn("un_ai_development_generosity < un_ai_development_reduce_line", reduce_chance)

    def test_cutting_back_waits_a_band_below_the_raise(self):
        raise_line = _flat(_block(self.values, "un_ai_development_raise_line"))
        reduce_line = _flat(_block(self.values, "un_ai_development_reduce_line"))
        self.assertEqual(raise_line, "value = un_dev_fund_size_value subtract = un_ai_development_base_size "
                                     "add = 1 multiply = un_ai_development_size_step")
        self.assertEqual(reduce_line, "value = un_dev_fund_size_value subtract = un_ai_development_base_size "
                                      "multiply = un_ai_development_size_step subtract = un_ai_development_band")
        self.assertGreater(_constant(self.values, "un_ai_development_band"),
                           _constant(self.values, "un_ai_self_flipping_terms"))

    def test_a_sound_contributor_settles_at_the_old_token_money(self):
        # Token and Small (2026-10-06) went in below the old Token; a member
        # with no reason to give more still settles at its money, Small.
        base = int(_constant(self.values, "un_ai_development_base_size"))
        self.assertEqual(SIZES[base - 1], "small")
        self.assertAlmostEqual(_constant(_read(ECONOMY), "un_dev_fund_pct_small"), 0.125)

    def test_wealth_starts_a_gift_but_does_not_enlarge_it(self):
        # Rich members give much more often, but typically only a token
        # (owner, 2026-10-05).
        will = _flat(_block(self.values, "un_ai_development_will"))
        generosity = _flat(_block(self.values, "un_ai_development_generosity"))
        for term in ("un_dev_fund_rich = yes", "un_dev_fund_above_average = yes"):
            self.assertIn(term, will)
            self.assertNotIn(term, generosity)

    def test_recipients_among_ours_weigh_half_a_size(self):
        # A great power almost always has a recipient among its subjects, bloc
        # partners and allies; at a full size it put nearly every one at Modest
        # (owner, 2026-10-06).
        generosity = _flat(_block(self.values, "un_ai_development_generosity"))
        step = _constant(self.values, "un_ai_development_size_step")
        terms = dict(re.findall(r"limit = \{ (.+?) \} add = (-?\d+) \}", generosity))
        self.assertEqual(float(terms["has_law = law_type:law_humanitarian_regulations"]), step)
        self.assertEqual(float(terms["un_ai_development_recipients_among_ours = yes"]), step / 2)
        self.assertTrue(generosity.endswith("add = un_ai_development_poverty"))

    def test_poverty_and_debt_hold_a_contribution_back(self):
        # Being poorer than the great powers, or borrowing, is a strong reason
        # not to give more (owner, 2026-10-06), in steps that flip inside the
        # band.
        poverty = _flat(_block(self.values, "un_ai_development_poverty"))
        self.assertIn("if = { limit = { un_ai_development_peer_ratio < 0.5 } add = -30 } "
                      "else_if = { limit = { un_ai_development_peer_ratio < 1 } add = -15 }", poverty)
        self.assertIn("if = { limit = { scaled_debt >= 0.25 } add = -15 }", poverty)
        self.assertTrue(poverty.endswith("add = un_ai_treasury_penalty"))
        # Each step flips on its own as GDP per head or debt moves, so none may
        # be wider than un_ai_self_flipping_terms (which the band exceeds).
        flipping = _constant(self.values, "un_ai_self_flipping_terms")
        deep, below, debt = (int(x) for x in re.findall(r"add = (-\d+)", poverty))
        for step in (-below, below - deep, -debt):
            self.assertLessEqual(step, flipping)
        ratio = _flat(_block(self.values, "un_ai_development_peer_ratio"))
        self.assertIn("add = var:un_dev_fund_gdp_ph divide = un_ai_development_peer_gdp_ph", ratio)
        self.assertTrue(ratio.endswith("else = { add = 1 }"))  # no figure, no penalty
        peer = _flat(_block(self.values, "un_ai_development_peer_gdp_ph"))
        self.assertLess(peer.index("add = global_var:un_dev_fund_gp_avg"),
                        peer.index("add = global_var:un_dev_fund_avg"))

    def test_the_great_powers_average_is_snapshotted_and_cleared(self):
        effects = _read(ECONOMY_EFFECTS)
        update = _flat(_block(effects, "un_dev_fund_monthly_update"))
        snapshot = update.index("set_global_variable = { name = un_dev_fund_gp_avg value = un_dev_fund_gp_avg_value }")
        self.assertLess(update.index("set_variable = { name = un_dev_fund_gdp_ph"), snapshot)
        self.assertIn("un_dissolve_remove_global = { NAME = un_dev_fund_gp_avg }",
                      _flat(_block(effects, "un_economy_on_dissolve")))
        avg = _flat(_block(_read(ECONOMY), "un_dev_fund_gp_avg_value"))
        self.assertIn("country_rank >= rank_value:great_power has_variable = un_dev_fund_gdp_ph", avg)
        self.assertTrue(avg.endswith("divide = un_dev_fund_gp_count_value }"))


class FundingPillarTest(unittest.TestCase):
    def setUp(self):
        self.values = _read(AUTHORITY)

    def test_development_counts_by_money_not_by_who_gives(self):
        self.assertNotIn("development", _block(self.values, "un_programmes_running"))
        money = _flat(_block(self.values, "un_funding_dev_money_ratio_value"))
        self.assertIn("add = global_var:un_dev_fund_donations multiply = 52 "
                      "divide = global_var:un_dev_fund_members_gdp divide = un_funding_dev_money_for_full", money)
        self.assertEqual(_constant(self.values, "un_funding_dev_money_for_full"), 0.007)
        ratio = _flat(_block(self.values, "un_funding_ratio_value"))
        self.assertEqual(ratio, "value = un_funding_programmes_ratio_value "
                                "add = un_funding_dev_money_ratio_value max = 1")

    def test_the_parts_are_snapshotted_for_the_display(self):
        update = _raw(AUTHORITY_EFFECTS)
        for name in ("un_funding_programmes_ratio", "un_funding_dev_money_ratio", "un_funding_ratio"):
            self.assertIn(f"set_global_variable = {{ name = {name} value = {name}_value }}", update)


class LobbyingTest(unittest.TestCase):
    def test_types_are_registered_and_named(self):
        types = _read(TYPES)
        loc = _loc()
        for name in ("country_un_lobbying_mult", "country_un_lobbying_fund_recipients_mult"):
            with self.subTest(modifier=name):
                body = _flat(_block(types, name))
                self.assertIn("script_only = yes", body)
                self.assertIn("percent = yes", body)
                self.assertRegex(loc, r"(?m)^ " + name + r":0 ")
                self.assertRegex(loc, r"(?m)^ " + name + r"_desc:0 ")

    def test_campaigns_scale_by_effectiveness_with_the_member(self):
        values = _read(LOBBYING)
        shift = _flat(_block(values, "un_lobby_campaign_shift_value"))
        self.assertTrue(shift.endswith("multiply = un_lobby_campaign_effectiveness"))
        eff = _flat(_block(values, "un_lobby_campaign_effectiveness"))
        self.assertIn("add = modifier:country_un_lobbying_mult", eff)
        recipients = eff.index("add = modifier:country_un_lobbying_fund_recipients_mult")
        self.assertLess(eff.index("un_dev_fund_receiving = yes"), recipients)
        self.assertTrue(eff.endswith("min = 0"))

    def test_both_pledges_weigh_the_askers_effectiveness(self):
        actions = _read(LOBBY_ACTIONS)
        for action in ("un_secure_commitment_action", "un_secure_commitment_against_action"):
            body = _flat(_block(actions, action))
            with self.subTest(action=action):
                self.assertIn('desc = "UN_LOBBY_ACCEPT_EFFECTIVENESS" value = un_lobby_accept_general_value', body)
                self.assertIn('desc = "UN_LOBBY_ACCEPT_DEV_AID" value = un_lobby_accept_fund_value', body)
        fund = _flat(_block(_read(LOBBYING), "un_lobby_accept_fund_value"))
        self.assertIn("limit = { un_dev_fund_receiving = yes }", fund)
        self.assertIn("scope:actor.modifier:country_un_lobbying_fund_recipients_mult", fund)


if __name__ == "__main__":
    unittest.main()
