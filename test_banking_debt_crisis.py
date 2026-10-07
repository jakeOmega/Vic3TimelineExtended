"""Sovereign debt crises as a process (#800).

Three pieces, each checked against the script because the engine warns about
none of them going wrong:

* the Restructure the Public Debt decision and its talks
  (``banking_debt_events.1``): the 10 / 25 / 50% ladder, its costs rising with
  the haircut, the deep haircut tied to the engine's default state, and the
  Sovereign Debt Scare's option C sharing the 25% package;
* the conditional rescue, the bailout appeal's fourth answer
  (``banking_cycle_events.45`` option E): terms the partner may refuse, a
  tranche at signing and one at each yearly review, paid only on the budget
  condition;
* the Sovereign Debt Scare's option B as the bank buying bonds: one
  monetisation step for ``te_mon_bond_support_term`` months, taken back by
  step 1b of the monetary update.

Tooltips state their figures in words; each test that reads one holds it to
the script value it quotes.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DECISIONS = ROOT / "common/decisions/extra_decisions.txt"
DEBT_EFFECTS = ROOT / "common/scripted_effects/banking_debt_effects.txt"
DEBT_TRIGGERS = ROOT / "common/scripted_triggers/banking_debt_triggers.txt"
DEBT_VALUES = ROOT / "common/script_values/banking_debt_values.txt"
DEBT_EVENTS = ROOT / "events/banking_debt_events.txt"
CYCLE_EVENTS = ROOT / "events/banking_cycle_events.txt"
MODIFIERS = ROOT / "common/static_modifiers/extra_modifiers.txt"
EXTRA_VALUES = ROOT / "common/script_values/extra_script_values.txt"
MON_EFFECTS = ROOT / "common/scripted_effects/te_monetary_effects.txt"
MON_VALUES = ROOT / "common/script_values/te_monetary_script_values.txt"
MON_CW = ROOT / "common/scripted_effects/te_monetary_civil_war_effects.txt"
ON_ACTIONS = ROOT / "common/on_actions/extra_on_actions.txt"
INFLATION_EVENTS = ROOT / "events/te_inflation_events.txt"
AGENCY_TRIGGERS = ROOT / "common/scripted_triggers/te_event_agency_misc_triggers.txt"
JE = ROOT / "common/journal_entries/je_banking.txt"
LOC_DIR = ROOT / "localization/english"


def _text(path):
    text = path.read_text(encoding="utf-8-sig")
    return re.sub(r"#[^\n]*", "", text)


def _block(text, header):
    """The body of the block opened by ``header`` (``name = {``), braces matched."""
    start = text.index(header) + len(header)
    depth = 1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i]
    raise AssertionError(f"{header} is not closed")


def _top(path, name):
    text = _text(path)
    m = re.search(r"(?m)^" + re.escape(name) + r" = \{", text)
    if m is None:
        raise AssertionError(f"{name} not found in {path.name}")
    return _block(text[m.start():], f"{name} = {{")


def _options(event_body):
    out = []
    for m in re.finditer(r"(?m)^\toption = \{", event_body):
        out.append(_block(event_body[m.start():], "option = {"))
    return out


def _option(event_body, name):
    for option in _options(event_body):
        if re.search(r"name = " + re.escape(name) + r"\b", option):
            return option
    raise AssertionError(f"no option {name}")


def _value(path, name):
    body = _top(path, name)
    m = re.fullmatch(r"\s*value = (-?[\d.]+)\s*", body)
    if m is None:
        raise AssertionError(f"{name} is not a constant")
    return float(m.group(1))


_LOC = None


def _loc(key):
    global _LOC
    if _LOC is None:
        _LOC = {}
        for path in LOC_DIR.glob("*_l_english.yml"):
            for m in re.finditer(r'(?m)^ ([^:\s]+):0 "(.*)"$', path.read_text(encoding="utf-8-sig")):
                _LOC[m.group(1)] = m.group(2)
    return _LOC[key]


def _modifier(name):
    body = _top(MODIFIERS, name)
    return {k: float(v) for k, v in re.findall(r"(\w+) = (-?[\d.]+)", body)}


WORDS = {0.1: "A tenth", 0.25: "A quarter", 0.5: "Half"}


class RestructuringLadderTests(unittest.TestCase):
    """The talks' three haircuts: bigger write-offs cost more."""

    TIERS = [
        # effect, write-off value, write-off tooltip, premium modifier, exclusion modifier, cooldown tooltip
        ("banking_restructuring_reprofile", "banking_restructuring_haircut_reprofile",
         "banking_restructuring_reprofile_write_off_tt", "banking_restructuring_reprofiled", None),
        ("banking_restructuring_haircut", "banking_partial_default_haircut",
         "banking_partial_default_write_off_tt", "banking_event_partial_default",
         "banking_restructuring_wary_lenders"),
        ("banking_restructuring_deep_haircut", "banking_restructuring_haircut_deep",
         "banking_restructuring_deep_write_off_tt", "banking_restructuring_deep_default",
         "banking_restructuring_shut_out"),
    ]

    def _share(self, value_name):
        path = EXTRA_VALUES if value_name == "banking_partial_default_haircut" else DEBT_VALUES
        body = _top(path, value_name)
        self.assertRegex(body, r"value = scaled_debt")
        return float(re.search(r"multiply = ([\d.]+)", body).group(1))

    def test_write_offs_are_a_tenth_a_quarter_and_half(self):
        shares = [self._share(value) for _, value, _, _, _ in self.TIERS]
        self.assertEqual(shares, [0.1, 0.25, 0.5])
        for (_, _, tooltip, _, _), share in zip(self.TIERS, shares):
            with self.subTest(tooltip=tooltip):
                self.assertTrue(_loc(tooltip).startswith(f"#b {WORDS[share]}#!"), _loc(tooltip))

    def test_each_tier_writes_off_its_own_share(self):
        haircut = _top(DEBT_EFFECTS, "banking_restructuring_haircut")
        self.assertIn("banking_partial_default_write_off = yes", haircut)
        for effect, value, tooltip, _, _ in (self.TIERS[0], self.TIERS[2]):
            body = _top(DEBT_EFFECTS, effect)
            with self.subTest(effect=effect):
                self.assertRegex(
                    body,
                    r"custom_tooltip = \{\s+text = %s\s+clear_scaled_debt = %s\s+\}"
                    % (re.escape(tooltip), re.escape(value)),
                )

    def test_costs_rise_with_the_haircut(self):
        premiums, prestige, reserves, relations, cooldowns = [], [], [], [], []
        for effect, _, _, premium, exclusion in self.TIERS:
            body = _top(DEBT_EFFECTS, effect)
            mod = _modifier(premium)
            premiums.append(mod["country_risk_premium_add"])
            prestige.append(mod["country_prestige_mult"])
            self.assertRegex(body, r"name = %s\s+days = \w+_modifier_time\s+is_decaying = yes" % premium)
            if exclusion is None:
                reserves.append(0.0)
            else:
                reserves.append(_modifier(exclusion)["building_cash_reserves_mult"])
                self.assertRegex(body, r"name = %s\s+days = normal_modifier_time\s+is_decaying = yes" % exclusion)
            relation = re.search(
                r"banking_restructuring_investor_relations = \{ VALUE = (-\d+) TEXT = (\w+) \}", body)
            relations.append(int(relation.group(1)))
            # the tooltip names the fall it is given
            self.assertIn(f"#R {-int(relation.group(1))}#!", _loc(relation.group(2)))
            days = int(re.search(r"name = banking_debt_restructured value = yes days = (\d+)", body).group(1))
            cooldowns.append(days)
            tooltip = re.search(r"text = (banking_restructuring_cooldown_\d+_tt)", body).group(1)
            self.assertIn(f"#b {days // 365} years#!", _loc(tooltip))
        self.assertEqual(premiums, sorted(premiums))
        self.assertEqual(len(set(premiums)), 3)
        self.assertEqual(prestige, sorted(prestige, reverse=True))
        self.assertEqual(reserves, sorted(reserves, reverse=True))
        self.assertEqual(reserves[0], 0.0)
        self.assertEqual(relations, sorted(relations, reverse=True))
        self.assertEqual(cooldowns, [1825, 3650, 3650])
        # the haircut's premium lasts longer than the reprofiling's
        reprofile = _top(DEBT_EFFECTS, "banking_restructuring_reprofile")
        self.assertIn("days = normal_modifier_time", reprofile)
        for effect in ("banking_restructuring_haircut", "banking_restructuring_deep_haircut"):
            self.assertRegex(_top(DEBT_EFFECTS, effect), r"days = long_modifier_time\s+is_decaying = yes")

    def test_investors_are_the_countries_owning_five_percent_of_us(self):
        body = _top(DEBT_EFFECTS, "banking_restructuring_investor_relations")
        self.assertRegex(body, r"gdp_ownership_ratio = \{\s+target = prev\s+value > 0\.05\s+\}")
        for tooltip in ("banking_restructuring_investors_10_tt", "banking_restructuring_investors_25_tt",
                        "banking_restructuring_investors_50_tt"):
            self.assertIn("#b 5%#!", _loc(tooltip))

    def test_the_deep_haircut_needs_the_default_state(self):
        self.assertEqual(_top(DEBT_TRIGGERS, "banking_restructuring_deep_possible").split(),
                         ["in_default", "=", "yes"])
        talks = _top(DEBT_EVENTS, "banking_debt_events.1")
        deep = _option(talks, "banking_debt_events.1.c")
        self.assertIn("trigger = { banking_restructuring_deep_possible = yes }", deep)
        self.assertIn("banking_restructuring_deep_haircut = yes", deep)
        for option in _options(talks):
            if "banking_restructuring_deep_haircut" not in option:
                self.assertNotIn("trigger =", option.split("ai_chance")[0])

    def test_the_scare_and_the_talks_share_the_quarter(self):
        talks = _top(DEBT_EVENTS, "banking_debt_events.1")
        self.assertIn("banking_restructuring_haircut = yes", _option(talks, "banking_debt_events.1.b"))
        for number in (10, 110, 160):
            option = _option(_top(CYCLE_EVENTS, f"banking_cycle_events.{number}"),
                             f"banking_cycle_events.{number}.c")
            with self.subTest(event=number):
                self.assertIn("banking_restructuring_haircut = yes", option)
                # the package carries the write-off and the premium itself
                self.assertNotIn("banking_partial_default_write_off", option)
                self.assertNotIn("banking_event_partial_default", option)

    def test_breaking_off_is_the_default_and_writes_nothing_off(self):
        talks = _top(DEBT_EVENTS, "banking_debt_events.1")
        defaults = [o for o in _options(talks) if "default_option = yes" in o]
        self.assertEqual(len(defaults), 1)
        self.assertIn("name = banking_debt_events.1.e", defaults[0])
        self.assertNotIn("banking_restructuring", defaults[0])
        self.assertIn("#b a year#!", _loc("banking_debt_events.1.e.tt"))

    def test_the_decision_opens_the_talks(self):
        decision = _top(DECISIONS, "te_decision_restructure_debt")
        self.assertIn("banking_restructuring_shown = yes", _block(decision, "is_shown = {"))
        self.assertIn("banking_restructuring_possible = yes", _block(decision, "possible = {"))
        taken = _block(decision, "when_taken = {")
        self.assertIn("trigger_event = { id = banking_debt_events.1 popup = yes }", taken)
        days = int(re.search(r"name = banking_restructuring_talks value = yes days = (\d+)", taken).group(1))
        self.assertEqual(days, 365)
        self.assertIn("#b a year#!", _loc("te_decision_tt_restructure_debt"))
        self.assertIn("ai_chance", decision)
        shown = _top(DEBT_TRIGGERS, "banking_restructuring_shown")
        for clause in ("has_journal_entry = je_banking_cycle", "is_revolutionary = no",
                       "banking_sovereign_debt_is_priced = yes", "in_default = yes"):
            self.assertIn(clause, shown)
        possible = _top(DEBT_TRIGGERS, "banking_restructuring_possible")
        for variable in ("banking_debt_restructured", "banking_restructuring_talks"):
            self.assertIn(f"has_variable = {variable}", possible)


class ConditionalRescueTests(unittest.TestCase):
    def test_the_donor_offers_terms_rather_than_money(self):
        request = _top(CYCLE_EVENTS, "banking_cycle_events.45")
        offer = _option(request, "banking_cycle_events.45.e")
        self.assertIn("banking_rescue_offer_terms = yes", offer)
        self.assertNotIn("banking_transfer_emergency_aid", offer)
        self.assertNotIn("add_treasury", offer)
        terms = _top(DEBT_EFFECTS, "banking_rescue_offer_terms")
        self.assertIn("trigger_event = { id = banking_debt_events.2 }", terms)
        self.assertIn("value = banking_rescue_offer_value", terms)

    def test_the_offer_is_the_rescue_package(self):
        # option A's terms: AMOUNT, DAYS and CAP of banking_transfer_emergency_aid
        rescue = _option(_top(CYCLE_EVENTS, "banking_cycle_events.45"), "banking_cycle_events.45.a")
        transfer = _block(rescue, "banking_transfer_emergency_aid = {")
        offer = _top(DEBT_VALUES, "banking_rescue_offer_value")
        amount = re.search(r"AMOUNT = (\w+)", transfer).group(1)
        days = re.search(r"DAYS = (\w+)", transfer).group(1)
        cap = re.search(r"CAP = (\w+)", transfer).group(1)
        self.assertIn(f"value = root.{amount}", offer)
        self.assertIn(f"multiply = {days}", offer)
        self.assertIn("divide = 14", offer)
        self.assertIn(f"max = {cap}", offer)

    def test_refusing_is_the_default(self):
        terms = _top(DEBT_EVENTS, "banking_debt_events.2")
        accept = _option(terms, "banking_debt_events.2.a")
        refuse = _option(terms, "banking_debt_events.2.b")
        self.assertIn("banking_rescue_accept = yes", accept)
        self.assertNotIn("default_option", accept)
        self.assertIn("default_option = yes", refuse)
        self.assertIn("banking_rescue_refuse = yes", refuse)

    def test_tranches_and_the_condition_match_the_tooltips(self):
        tranches = _value(DEBT_VALUES, "banking_rescue_tranches")
        months = _value(DEBT_VALUES, "banking_rescue_review_months_term")
        allowed = _value(DEBT_VALUES, "banking_rescue_borrowing_months_allowed")
        self.assertEqual((tranches, months, allowed), (3, 12, 6))
        for key in ("banking_rescue_terms_tt", "banking_cycle_events.45.e.tt"):
            with self.subTest(key=key):
                self.assertIn(f"#b {int(allowed)}#! of the #b {int(months)}#! months", _loc(key))
        # one tranche at signing, then one at each of (tranches - 1) reviews
        self.assertIn("#b two#! yearly reviews", _loc("banking_rescue_terms_tt"))
        self.assertIn("a third at each of two yearly reviews", _loc("banking_cycle_events.45.e.tt"))
        accept = _top(DEBT_EFFECTS, "banking_rescue_accept")
        self.assertRegex(accept, r"value = banking_rescue_tranches\s+subtract = 1")
        self.assertIn("value = banking_rescue_review_months_term", accept)
        self.assertRegex(_top(DEBT_TRIGGERS, "banking_rescue_condition_met"),
                         r"var:banking_rescue_borrowing_months <= banking_rescue_borrowing_months_allowed")

    def test_a_missed_review_costs_what_the_tooltip_says(self):
        review = _top(DEBT_EFFECTS, "banking_rescue_review")
        breach = review[review.index("value = 3 days = 120"):]
        relations = int(re.search(r"country = scope:bailout_donor\s+value = (-\d+)", breach).group(1))
        self.assertIn(f"#R {relations}#! relations", _loc("banking_rescue_terms_tt"))
        premium = _modifier("banking_rescue_programme_suspended")["country_risk_premium_add"]
        self.assertIn(f"#b +{premium * 100:g}#! points of risk premium fading over five years",
                      _loc("banking_rescue_terms_tt"))
        self.assertRegex(breach, r"name = banking_rescue_programme_suspended\s+days = normal_modifier_time"
                                 r"\s+is_decaying = yes")
        self.assertIn("remove_modifier_if_exists_effect = { MODIFIER = banking_rescue_programme }", breach)

    def test_a_review_pays_only_on_the_condition(self):
        review = _top(DEBT_EFFECTS, "banking_rescue_review")
        paid = _block(review, "limit = { banking_rescue_condition_met = yes }")
        self.assertNotIn("add_treasury", review.replace(paid, ""))
        branch = review[review.index("limit = { banking_rescue_condition_met = yes }"):]
        branch = branch[:branch.index("else = {")]
        self.assertIn("add_treasury = var:banking_rescue_tranche", branch)
        self.assertIn("subtract = root.var:banking_rescue_tranche", branch)
        self.assertIn("change_variable = { name = banking_rescue_tranches_left subtract = 1 }", branch)
        # a dead donor pays nothing
        self.assertIn("limit = { banking_rescue_donor_exists = no }", review)
        self.assertIn("is_country_alive = yes", _top(DEBT_TRIGGERS, "banking_rescue_donor_exists"))

    def test_the_review_runs_on_the_banking_pulse_and_counts_borrowing(self):
        pulse = _block(_text(JE), "on_monthly_pulse = {")
        self.assertIn("banking_rescue_programme_monthly = yes", pulse)
        monthly = _top(DEBT_EFFECTS, "banking_rescue_programme_monthly")
        self.assertRegex(monthly, r"limit = \{ taking_loans = yes \}\s+change_variable = \{ "
                                  r"name = banking_rescue_borrowing_months add = 1 \}")
        self.assertIn("banking_rescue_review = yes", monthly)

    def test_one_programme_at_a_time(self):
        self.assertIn("NOT = { banking_rescue_programme_running = yes }",
                      _top(AGENCY_TRIGGERS, "te_ea_bailout_can_be_asked"))
        self.assertIn("NOT = { banking_rescue_programme_running = yes }",
                      _block(_top(DEBT_EVENTS, "banking_debt_events.2"), "trigger = {"))

    def test_every_notice_outcome_has_text(self):
        recipient = _top(DEBT_EVENTS, "banking_debt_events.3")
        for outcome in (1, 2, 3, 4):
            self.assertIn(f"banking_rescue_outcome_is = {{ OUTCOME = {outcome} }}", recipient)
        donor = _top(DEBT_EVENTS, "banking_debt_events.4")
        for outcome in (1, 2, 3):
            self.assertIn(f"banking_rescue_donor_outcome_is = {{ OUTCOME = {outcome} }}", donor)
        writers = re.findall(r"name = banking_rescue_donor_outcome value = (\d)",
                             _text(DEBT_EFFECTS))
        self.assertEqual(sorted(set(writers)), ["1", "2", "3", "4"])
        writers = re.findall(r"name = banking_rescue_outcome value = (\d)", _text(DEBT_EFFECTS))
        self.assertEqual(sorted(set(writers)), ["1", "2", "3", "4"])


class BondSupportTests(unittest.TestCase):
    def test_option_b_buys_bonds_only_where_the_bank_may_monetise(self):
        scare = _option(_top(CYCLE_EVENTS, "banking_cycle_events.10"), "banking_cycle_events.10.b")
        self.assertRegex(
            scare,
            r"limit = \{\s+te_mon_full_system = yes\s+te_mon_can_monetise = yes\s+\}\s+"
            r"te_mon_effect_bond_support = yes",
        )
        for number in (110, 160):
            option = _option(_top(CYCLE_EVENTS, f"banking_cycle_events.{number}"),
                             f"banking_cycle_events.{number}.b")
            self.assertNotIn("te_mon_effect_bond_support", option)

    def test_the_step_and_its_term(self):
        effect = _top(MON_EFFECTS, "te_mon_effect_bond_support")
        self.assertIn("change_variable = { name = te_monetisation_level add = 1 }", effect)
        self.assertEqual(effect.count("value = te_mon_bond_support_term"), 2)
        self.assertIn("te_mon_monetise_can_step_up = yes", effect)
        term = _value(MON_VALUES, "te_mon_bond_support_term")
        for key in ("te_mon_bond_support_tt", "te_mon_bond_support_extend_tt"):
            self.assertIn(f"#b {int(term)} months#!", _loc(key))
        # the step's prices, as the stepper's own tooltip states them
        tooltip = _loc("te_mon_bond_support_tt")
        self.assertIn(f"#b {_value(MON_VALUES, 'te_mon_monetisation_gdp_share') * 100:g}%#!", tooltip)
        self.assertIn(f"#b {_value(MON_VALUES, 'te_mon_monetisation_pressure'):g}%#! on inflation", tooltip)
        self.assertIn(f"#b {_value(MON_VALUES, 'te_mon_monetisation_premium'):g}%#! on everything", tooltip)

    def test_step_1b_runs_the_clock_and_takes_the_step_back(self):
        step = _top(MON_EFFECTS, "te_monetary_update_monetisation")
        ineligible = _block(step, "limit = { te_mon_can_monetise = no }")
        self.assertIn("set_variable = { name = te_mon_bond_support_months value = 0 }", ineligible)
        clock = step[step.index("limit = { var:te_mon_bond_support_months > 0 }"):]
        self.assertIn("change_variable = { name = te_mon_bond_support_months subtract = 1 }", clock)
        self.assertRegex(
            clock,
            r"var:te_mon_bond_support_months = 0\s+is_player = yes\s+var:te_monetisation_level > 0\s+\}\s+"
            r"change_variable = \{ name = te_monetisation_level subtract = 1 \}",
        )
        # the AI's own step back waits for the clock
        self.assertRegex(
            step,
            r"var:te_monetisation_level > 0\s+var:te_mon_bond_support_months = 0\s+\}\s+"
            r"change_variable = \{ name = te_monetisation_level subtract = 1 \}",
        )
        # the clock runs before the AI's rule reads it
        self.assertLess(step.index("subtract = 1 }"), step.index("is_player = no"))

    def test_every_site_that_zeroes_the_level_stops_the_clock(self):
        init = _top(MON_EFFECTS, "te_monetary_init_variables")
        self.assertIn("set_variable = { name = te_mon_bond_support_months value = 0 }", init)
        for path in (ON_ACTIONS, INFLATION_EVENTS):
            text = _text(path)
            with self.subTest(path=path.name):
                for m in re.finditer(r"set_variable = \{ name = te_monetisation_level value = 0 \}", text):
                    window = text[m.end():m.end() + 300]
                    self.assertIn("set_variable = { name = te_mon_bond_support_months value = 0 }", window)
        self.assertIn("te_mon_cw_take = { VAR = te_mon_bond_support_months }", _text(MON_CW))


if __name__ == "__main__":
    unittest.main()
