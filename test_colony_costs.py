# -*- coding: utf-8 -*-
"""The colonies' costs are the Space Program's inputs only (owner, 2026-11-25).

Module upkeep, free colony supply, colonial garrisons, a strike settlement and
dome breach repairs were each Space Program throughput, which scaled the
programme's outputs with its inputs (innovation, prestige, pace, module
fabrication and storage), so a module's upkeep built modules faster. Each is
now a goods_input_launch_capacity_mult on the Space Program building, at its
units / (1 + the programme's throughput), from one monthly refresh site
(sr_ccost_refresh), so a unit takes its share of the programme's base Launch
Capacity whatever the funding and moves no output. These tests hold the
modifiers, the values, the refresh, the two events, the AI's budget, the
panel and the loc to that shape.
"""

import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

# modifier -> (its key in the values, its share of base Launch Capacity a unit)
COSTS = {
    "sr_module_upkeep": ("upkeep", 0.01),
    "sr_free_colony_supply": ("supply", 0.03),
    "sr_colonial_garrisons": ("garrison", 0.02),
    "sr_strike_settlement": ("strike", 0.05),
    "sr_dome_breach_repairs": ("breach", 0.10),
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

    def test_each_cost_is_launch_capacity_input_and_nothing_else(self):
        for modifier, (_, share) in COSTS.items():
            with self.subTest(modifier=modifier):
                fields = re.findall(r"(?m)^\s*(\w+) = (\S+)", _block(self.modifiers, modifier))
                self.assertEqual([f for f in fields if f[0] != "icon"],
                                 [("goods_input_launch_capacity_mult", f"{share:.2f}")])

    def test_the_values_shares_are_the_modifiers(self):
        for key, share in COSTS.values():
            with self.subTest(key=key):
                self.assertEqual(_flat(_block(self.values, f"sr_ccost_{key}_share")), f"value = {share:.2f}")

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

    def test_each_multiplier_divides_its_units_by_the_factor(self):
        for key, _ in COSTS.values():
            with self.subTest(key=key):
                self.assertEqual(_flat(_block(self.values, f"sr_ccost_{key}_mult")),
                                 f"value = sr_ccost_{key}_units divide = sr_program_throughput_factor")

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

    def test_the_share_sums_every_cost(self):
        share = _flat(_block(self.values, "sr_ccost_share_value"))
        for key, _ in COSTS.values():
            with self.subTest(key=key):
                self.assertIn(f"add = {{ value = sr_ccost_{key}_units multiply = sr_ccost_{key}_share }}", share)
        self.assertEqual(share.count("add = {"), len(COSTS))
        self.assertEqual(_flat(_block(self.values, "sr_ccost_share_now")),
                         "value = 0 if = { limit = { has_variable = sr_ccost_share } value = var:sr_ccost_share }")


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

    def test_the_terms_count_down_after_the_bill(self):
        flat = _flat(self.refresh)
        last_add = max(self.refresh.index(f"name = {m} ") for m in COSTS)
        for key, (counter, _, _, _) in TERMS.items():
            with self.subTest(key=key):
                countdown = (f"if = {{ limit = {{ has_variable = {counter} }} change_variable = {{ name = {counter} "
                             f"add = -1 }} if = {{ limit = {{ var:{counter} <= 0 }} remove_variable = {counter} }} }}")
                self.assertIn(countdown, flat)
                self.assertGreater(self.refresh.index(f"change_variable = {{ name = {counter}"), last_add)

    def test_the_share_is_stored_for_the_ai_and_cleared_at_zero(self):
        flat = _flat(self.refresh)
        self.assertIn("set_local_variable = { name = sr_ccost_share_new value = sr_ccost_share_value }", flat)
        self.assertIn("if = { limit = { local_var:sr_ccost_share_new > 0 } set_variable = { name = sr_ccost_share "
                      "value = local_var:sr_ccost_share_new } } else_if = { limit = { has_variable = sr_ccost_share } "
                      "remove_variable = sr_ccost_share }", flat)

    def test_it_runs_monthly_from_the_always_on_pulse_alone(self):
        always = _flat(_strip(_raw("common", "on_actions", "space_race_on_actions.txt")))
        self.assertIn("if = { limit = { OR = { sr_has_space_program = yes "
                      "has_journal_entry = je_space_race_solar_colonization has_variable = sr_ccost_share "
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
                share = next(s for k, s in COSTS.values() if k == key)
                self.assertIn(f"#v {round(share * 100)}%#! of the Space Program's base Launch Capacity", tooltip)
                self.assertRegex(option, rf"custom_tooltip = \{{ text = \w+_tt set_variable = \{{ "
                                         rf"name = {counter} value = {term} \}} \}}")
                self.assertNotIn("add_modifier", option)


class AiAndPanelTest(unittest.TestCase):
    def test_the_ai_bills_the_share_beside_the_throughput(self):
        values = _strip(_raw("common", "script_values", "sr_ai_mission_budget_values.txt"))
        self.assertEqual(_flat(_block(values, "sr_ai_program_throughput_unfunded")), (
            "value = 1 add = modifier:building_space_program_throughput_add "
            "subtract = sr_ai_program_funding_throughput min = 1 add = sr_ccost_share_now"))

    def test_the_panel_shows_the_upkeep_in_launch_capacity(self):
        display = _strip(_raw("common", "script_values", "space_race_display_values.txt"))
        self.assertEqual(_flat(_block(display, "sr_disp_mod_upkeep_week")),
                         "value = sr_ccost_upkeep_units multiply = sr_ccost_upkeep_share multiply = sr_emig_lc_base")
        self.assertIn("sr_disp_mod_upkeep_week", _loc("je_space_race_widget_mod_upkeep_figure"))
        self.assertIn("#v 1%#!", _loc("je_space_race_widget_mod_upkeep_tt"))


class LocTest(unittest.TestCase):
    def test_each_desc_gives_its_share_and_none_says_throughput(self):
        for modifier, (_, share) in COSTS.items():
            with self.subTest(modifier=modifier):
                desc = _loc(f"{modifier}_desc")
                self.assertIn(f"#v {round(share * 100)}%#!", desc)
                self.assertIn("base Launch Capacity", desc)
                self.assertNotIn("throughput", desc)
        for key in ("concept_sr_free_colony_desc", "sr_free_supply_start_tt", "sr_aut_garrison_tt",
                    "je_space_race_widget_autonomy_garrison_tt", "je_space_race_widget_free_trade_tt",
                    "je_space_race_widget_mod_upkeep_label"):
            with self.subTest(key=key):
                self.assertNotIn("throughput", _loc(key))


if __name__ == "__main__":
    unittest.main()
