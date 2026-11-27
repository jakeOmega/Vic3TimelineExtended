# -*- coding: utf-8 -*-
"""The colonies' costs are the Space Program's inputs only (owner, 2026-11-25).

Module upkeep, free colony supply, colonial garrisons, a strike settlement and
dome breach repairs were each Space Program throughput, which scaled the
programme's outputs with its inputs (innovation, prestige, pace, module
fabrication and storage), so a module's upkeep built modules faster. Each is
now a goods_input_launch_capacity_mult on the Space Program building, from one
monthly refresh site (sr_ccost_refresh), at 100 x its flat Launch Capacity a
week / the building's Launch Capacity as billed (sr_emig_bill_divisor, as the
settlers' bill), so a unit takes the same Launch Capacity whatever the mission
and the funding and moves no output. Until the flat amounts (owner,
2026-11-25) each was a share of the programme's base, so a garrison cost ten
times as much on the Interstellar Mission as on Solar Colonization. These
tests hold the modifiers, the values, the refresh, the two events, the AI's
budget, the panel and the loc to that shape.
"""

import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

# modifier -> (its key in the values, its Launch Capacity a week a unit): each its
# old share of Solar Colonization's base, 10,000.
COSTS = {
    "sr_module_upkeep": ("upkeep", 100),
    "sr_free_colony_supply": ("supply", 300),
    "sr_colonial_garrisons": ("garrison", 200),
    "sr_strike_settlement": ("strike", 500),
    "sr_dome_breach_repairs": ("breach", 1000),
}
# The three the entry declared: their units' count and its gate.
COUNTED = {"upkeep": "sr_mod_upkeep_levels", "supply": "sr_free_supply_count", "garrison": "sr_garrison_count"}
# The two event terms: key -> (the month counter, the term value, months, the event).
TERMS = {
    "strike": ("sr_strike_settlement_months", "sr_strike_settlement_term", 36, "space_race_events.96"),
    "breach": ("sr_dome_breach_months", "sr_dome_breach_term", 12, "space_race_events.97"),
}
# The Space Program throughput kept, each a choice or a reward whose point is the output:
# funding, the Mars orbital-first strategy, and the space-race-off investment event.
THROUGHPUT_KEPT = {"sr_funding_throughput", "sr_mars_orbital_first", "space_race_achievement_modifier"}

VALUES = ("common", "script_values", "sr_colony_cost_values.txt")
EFFECTS = ("common", "scripted_effects", "sr_colony_cost_effects.txt")


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^\s*(?:[A-Z_]+:)?{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        raise AssertionError(f"no block {name}")
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return text[m.end():i - 1]


def _flat(text):
    return " ".join(text.split())


def _walk(*subdirs):
    for sub in subdirs:
        for root, _, files in os.walk(os.path.join(REPO, sub)):
            for name in sorted(files):
                if name.endswith(".txt"):
                    path = os.path.join(root, name)
                    yield os.path.relpath(path, REPO).replace(os.sep, "/"), _strip(_raw(path))


def _loc(key):
    for name in sorted(os.listdir(os.path.join(REPO, "localization", "english"))):
        if not name.endswith(".yml"):
            continue
        text = _raw("localization", "english", name)
        m = re.search(rf'(?m)^ {re.escape(key)}:\d+ "(.*)"$', text)
        if m:
            return m.group(1)
    raise AssertionError(f"no loc {key}")


class ModifierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modifiers = _strip(_raw("common", "static_modifiers", "space_race_modifiers.txt"))
        cls.values = _strip(_raw(*VALUES))

    def test_each_cost_is_one_percent_of_launch_capacity_input_a_unit_and_nothing_else(self):
        # As the settlers' bill: the multiplier carries the amount.
        for modifier in list(COSTS) + ["sr_settler_launches"]:
            with self.subTest(modifier=modifier):
                fields = re.findall(r"(?m)^\s*(\w+) = (\S+)", _block(self.modifiers, modifier))
                self.assertEqual([f for f in fields if f[0] != "icon"],
                                 [("goods_input_launch_capacity_mult", "0.01")])

    def test_the_values_hold_each_amount(self):
        for key, lc in COSTS.values():
            with self.subTest(key=key):
                self.assertEqual(_flat(_block(self.values, f"sr_ccost_{key}_lc")), f"value = {lc}")
        self.assertNotRegex(self.values, r"sr_ccost_\w+_share\b")

    def test_only_the_rewards_and_the_funding_are_still_throughput(self):
        found = set()
        for path, text in _walk("common", "events"):
            if path.startswith("common/modifier_type_definitions/"):
                continue
            for m in re.finditer(r"(?m)^(\w+) = \{", text):
                if "building_space_program_throughput_add" in _block(text[m.start():], m.group(1)) \
                        and path.startswith("common/static_modifiers/"):
                    found.add(m.group(1))
        self.assertEqual(found, THROUGHPUT_KEPT)

    def test_the_building_modifiers_are_registered_off_the_country(self):
        import gen_nation_tab
        for modifier in COSTS:
            with self.subTest(modifier=modifier):
                self.assertEqual(gen_nation_tab.NOT_ON_COUNTRY.get(modifier), "the Space Program building")


class ValueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = _strip(_raw(*VALUES))

    def test_the_factor_is_one_plus_the_programmes_throughput(self):
        self.assertEqual(_flat(_block(self.values, "sr_program_throughput_factor")),
                         "value = modifier:building_space_program_throughput_add add = 1 min = 0.1")

    def test_each_multiplier_is_its_amount_over_the_billed_launch_capacity(self):
        # 100 x units x the amount / (base x (1 + throughput)): a unit of the
        # modifier is 1% of the building's Launch Capacity as billed.
        for key, _ in COSTS.values():
            with self.subTest(key=key):
                self.assertEqual(_flat(_block(self.values, f"sr_ccost_{key}_mult")), (
                    f"value = sr_ccost_{key}_units multiply = sr_ccost_{key}_lc multiply = 100 "
                    "divide = sr_emig_bill_divisor"))
        population = _strip(_raw("common", "script_values", "sr_colony_population_values.txt"))
        self.assertEqual(_flat(_block(population, "sr_emig_bill_divisor")),
                         "value = sr_program_throughput_factor multiply = sr_emig_lc_base min = 1")

    def test_a_unit_bills_its_amount_whatever_the_mission_and_the_funding(self):
        # The engine's bill: base x (1 + throughput) x (1 + 0.01 x the multiplier).
        for base in (500, 10_000, 100_000):
            for throughput in (0.0, 0.75, 2.5):
                for key, lc in COSTS.values():
                    with self.subTest(base=base, throughput=throughput, key=key):
                        billed = base * (1 + throughput)
                        multiplier = 2 * lc * 100 / billed
                        self.assertAlmostEqual(billed * (1 + 0.01 * multiplier) - billed, 2 * lc)

    def test_the_entry_costs_keep_the_entrys_gates(self):
        # The gates the entry's declarations had, and the entry active, as declared
        # modifiers applied only while it was.
        for key, count in COUNTED.items():
            with self.subTest(key=key):
                self.assertEqual(_flat(_block(self.values, f"sr_ccost_{key}_units")), (
                    "value = 0 if = { limit = { sr_colonies_contested_enabled = yes "
                    f"has_journal_entry = je_space_race_solar_colonization {count} >= 1 }} add = {count} }}"))

    def test_the_terms_are_a_unit_while_their_counter_stands(self):
        for key, (counter, term, months, _) in TERMS.items():
            with self.subTest(key=key):
                self.assertEqual(_flat(_block(self.values, f"sr_ccost_{key}_units")), (
                    "value = 0 if = { limit = { sr_colonies_contested_enabled = yes "
                    f"has_variable = {counter} }} add = 1 }}"))
                self.assertRegex(self.values, rf"(?m)^{term} = {months}$")

    def test_the_total_sums_every_cost(self):
        total = _flat(_block(self.values, "sr_ccost_lc_value"))
        for key, _ in COSTS.values():
            with self.subTest(key=key):
                self.assertIn(f"add = {{ value = sr_ccost_{key}_units multiply = sr_ccost_{key}_lc }}", total)
        self.assertEqual(total.count("add = {"), len(COSTS))
        self.assertEqual(_flat(_block(self.values, "sr_ccost_lc_now")),
                         "value = 0 if = { limit = { has_variable = sr_ccost_lc } value = var:sr_ccost_lc }")


class RefreshTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.refresh = _strip(_block(_raw(*EFFECTS), "sr_ccost_refresh"))

    def test_one_refresh_removes_all_then_adds_each_above_zero_on_the_building(self):
        last_remove = max(self.refresh.index(f"MODIFIER = {m} }}") for m in COSTS)
        first_add = min(self.refresh.index(f"name = {m} ") for m in COSTS)
        self.assertLess(last_remove, first_add)
        self.assertEqual(self.refresh.count("every_scope_building = {"), 2)
        self.assertEqual(self.refresh.count("is_building_type = building_space_program"), 2)
        flat = _flat(self.refresh)
        for modifier, (key, _) in COSTS.items():
            with self.subTest(modifier=modifier):
                self.assertIn(f"set_local_variable = {{ name = sr_ccost_{key} value = sr_ccost_{key}_mult }}", flat)
                self.assertIn(f"if = {{ limit = {{ local_var:sr_ccost_{key} > 0 }} add_modifier = {{ "
                              f"name = {modifier} multiplier = local_var:sr_ccost_{key} }} }}", flat)
                self.assertIn(f"remove_modifier_if_exists_effect = {{ MODIFIER = {modifier} }}", flat)

    def test_nothing_else_adds_or_tests_the_costs(self):
        names = "|".join(COSTS)
        for path, text in _walk("common", "events"):
            if path == "/".join(EFFECTS):
                continue
            with self.subTest(file=path):
                self.assertIsNone(re.search(rf"(add_modifier = \{{\s*name|has_modifier|remove_modifier) = ({names})\b",
                                            text))

    def test_an_older_saves_country_copies_come_off_first(self):
        # Until 2026-11-25 the two terms were timed country modifiers; on the country
        # the input mult would reach every building that buys Launch Capacity.
        flat = _flat(self.refresh)
        first_building = flat.index("every_scope_building")
        for modifier in ("sr_strike_settlement", "sr_dome_breach_repairs"):
            with self.subTest(modifier=modifier):
                strip = f"if = {{ limit = {{ has_modifier = {modifier} }} remove_modifier = {modifier} }}"
                self.assertIn(strip, flat)
                self.assertLess(flat.index(strip), first_building)

    def test_the_terms_count_down_after_the_bill(self):
        flat = _flat(self.refresh)
        last_add = max(self.refresh.index(f"name = {m} ") for m in COSTS)
        for key, (counter, _, _, _) in TERMS.items():
            with self.subTest(key=key):
                countdown = (f"if = {{ limit = {{ has_variable = {counter} }} change_variable = {{ name = {counter} "
                             f"add = -1 }} if = {{ limit = {{ var:{counter} <= 0 }} remove_variable = {counter} }} }}")
                self.assertIn(countdown, flat)
                self.assertGreater(self.refresh.index(f"change_variable = {{ name = {counter}"), last_add)

    def test_the_total_is_stored_for_the_ai_and_cleared_at_zero(self):
        flat = _flat(self.refresh)
        self.assertIn("set_local_variable = { name = sr_ccost_lc_new value = sr_ccost_lc_value }", flat)
        self.assertIn("if = { limit = { local_var:sr_ccost_lc_new > 0 } set_variable = { name = sr_ccost_lc "
                      "value = local_var:sr_ccost_lc_new } } else_if = { limit = { has_variable = sr_ccost_lc } "
                      "remove_variable = sr_ccost_lc }", flat)
        self.assertNotIn("sr_ccost_share", flat)

    def test_it_runs_monthly_from_the_always_on_pulse_alone(self):
        always = _flat(_strip(_raw("common", "on_actions", "space_race_on_actions.txt")))
        self.assertIn("if = { limit = { OR = { sr_has_space_program = yes "
                      "has_journal_entry = je_space_race_solar_colonization has_variable = sr_ccost_lc "
                      "has_variable = sr_strike_settlement_months has_variable = sr_dome_breach_months } } "
                      "sr_ccost_refresh = yes }", always)
        callers = [path for path, text in _walk("common", "events") if re.search(r"\bsr_ccost_refresh = yes", text)]
        self.assertEqual(callers, ["common/on_actions/space_race_on_actions.txt"])


class EventTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = _strip(_raw("events", "space_race_events.txt"))

    def test_each_option_sets_its_term_in_a_tooltip(self):
        for key, (counter, term, months, event) in TERMS.items():
            with self.subTest(event=event):
                option = _flat(_block(_block(self.events, event), "option"))
                self.assertIn(f"name = {event}.a", option)
                tooltip = _loc(f"{'sr_strike_settlement' if key == 'strike' else 'sr_dome_breach_repairs'}_tt")
                self.assertIn(f"#v {months}#! months", tooltip)
                lc = next(v for k, v in COSTS.values() if k == key)
                self.assertIn(f"#v {lc:,}#! Launch Capacity a week", tooltip)
                self.assertRegex(option, rf"custom_tooltip = \{{ text = \w+_tt set_variable = \{{ "
                                         rf"name = {counter} value = {term} \}} \}}")
                self.assertNotIn("add_modifier", option)


class AiAndPanelTest(unittest.TestCase):
    def test_the_ai_adds_the_costs_to_every_missions_bill_not_the_throughput(self):
        values = _strip(_raw("common", "script_values", "sr_ai_mission_budget_values.txt"))
        self.assertEqual(_flat(_block(values, "sr_ai_program_throughput_unfunded")), (
            "value = 1 add = modifier:building_space_program_throughput_add "
            "subtract = sr_ai_program_funding_throughput min = 1"))
        for mission in ("earth_orbit", "moon", "mars", "solar", "deep_space", "interstellar", "current", "now"):
            with self.subTest(mission=mission):
                bill = _flat(_block(values, f"sr_ai_mission_bill_{mission}"))
                self.assertRegex(bill, r"^value = \w+ multiply = sr_ai_program_throughput_(un)?funded "
                                       r"add = sr_ccost_lc_now multiply = sr_launch_capacity_unit_price$")

    def test_the_panel_shows_the_upkeep_in_launch_capacity(self):
        display = _strip(_raw("common", "script_values", "space_race_display_values.txt"))
        self.assertEqual(_flat(_block(display, "sr_disp_mod_upkeep_week")),
                         "value = sr_ccost_upkeep_units multiply = sr_ccost_upkeep_lc")
        self.assertIn("sr_disp_mod_upkeep_week", _loc("je_space_race_widget_mod_upkeep_figure"))
        self.assertIn("#v 100#! for each level", _loc("je_space_race_widget_mod_upkeep_tt"))


class LocTest(unittest.TestCase):
    def test_each_desc_gives_its_amount_and_none_says_throughput_or_a_share(self):
        for modifier, (_, lc) in COSTS.items():
            with self.subTest(modifier=modifier):
                desc = _loc(f"{modifier}_desc")
                self.assertIn(f"#v {lc:,}#! Launch Capacity a week", desc)
                self.assertNotIn("throughput", desc)
                self.assertNotIn("base Launch Capacity", desc)
        amounts = {"concept_sr_free_colony_desc": 300, "sr_free_supply_start_tt": 300, "sr_aut_garrison_tt": 200,
                   "je_space_race_widget_autonomy_garrison_tt": 200, "je_space_race_widget_free_trade_tt": 300}
        for key, lc in amounts.items():
            with self.subTest(key=key):
                self.assertIn(f"#v {lc}#! Launch Capacity a week", _loc(key))
        for key in list(amounts) + ["je_space_race_widget_mod_upkeep_label", "je_space_race_widget_mod_upkeep_tt"]:
            with self.subTest(key=key):
                self.assertNotIn("throughput", _loc(key))
                self.assertNotIn("base Launch Capacity", _loc(key))


if __name__ == "__main__":
    unittest.main()
