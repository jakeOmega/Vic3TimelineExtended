"""The AI construction pass (common/scripted_effects/te_ai_build_pass_effects.txt, #1877).

Once a month an AI government whose government queue has stood empty a month gets one level queued, if the interest
rate allows it the means (te_ai_build_pass_means: reserves above the reserve the rate asks for, plus the debt it may
hold at its rate, less its debt) and it has the surplus the engine's budget AI asks for before it adds spending. What
it queues is the first entry of THE ORDER that applies (owner, 2026-11-16): a Government Administration while net
bureaucracy is under 2% of its usage; the country's first power plant while nothing of its makes Electricity and it
has no grid partner; a railway where a state's infrastructure is short of its usage by more than 2%; a university
while innovation is under nine-tenths of its cap and bureaucracy is not short; a highway, then an airport, in a major
industrial state under the building's level cap; each only where the surplus pays for the level within two years;
else nothing. A university, a highway or an airport goes only beside levels of its kind staffed to 80%. It follows
the level in its state until it is built or gone, queues nothing more meanwhile, and none of a kind for a year after
one of that kind was lost, or was built and gone again within two years. The engine itself queues nothing new for a
government in debt. The
rate's curve is pinned in test_construction_market_ai_purchase.py (TheRate); this file holds the pass's own text and
values: its conditions, its order, the means it reads, the follow, the watch, the back-off, and its self-check.

Run: python3 -m pytest test_ai_build_pass.py -q
"""
import re
import unittest
from pathlib import Path

import test_ai_building_values as buildings
import test_construction_market_ai_purchase as purchase
from test_construction_market_budget_step import load

ROOT = Path(__file__).resolve().parent
EFFECTS = ROOT / "common/scripted_effects/te_ai_build_pass_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/te_ai_build_pass_triggers.txt"
VALUES = ROOT / "common/script_values/te_ai_build_pass_values.txt"
ON_ACTIONS = ROOT / "common/on_actions/te_ai_build_pass_on_actions.txt"
GATE_CHECK = ROOT / "common/on_actions/te_ai_reserve_gate_selfcheck_on_actions.txt"
FILES = (EFFECTS, TRIGGERS, VALUES, ON_ACTIONS)
AI_DOC = ROOT / "docs/systems/mod_systems/ai.md"
PLAYTEST = ROOT / "docs/testing/ai-economy-playtest.md"
COVERAGE_TRIGGERS = ROOT / "common/scripted_triggers/te_ai_coverage_triggers.txt"

# THE ORDER as built, and each kind's number (te_ai_build_pass_pending_kind), building and site ranking.
ORDER = ["administration", "power_plant", "railway", "university", "highway", "airport"]
KINDS = {
    "university": (1, "building_university", "state_population"),
    "administration": (2, "building_government_administration", "te_ai_build_pass_tax_shortfall"),
    "railway": (3, "building_railway", "te_ai_build_pass_infrastructure_shortfall"),
    "power_plant": (4, "building_power_plant", "te_ai_build_pass_power_users"),
    "highway": (5, "building_highway", "te_ai_build_pass_manufacturing_levels"),
    "airport": (6, "building_airport", "te_ai_build_pass_manufacturing_levels"),
}
# The short names the self-check's line prints each kind under.
SHORT = {"university": "uni", "administration": "adm", "railway": "rail", "power_plant": "power",
         "highway": "road", "airport": "air"}


def _code(path):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text(encoding="utf-8-sig").splitlines())


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


def _block(text, name):
    """The body of the top-level block `name = { ... }`, by brace count."""
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    if m is None:
        raise KeyError(name)
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class Files(unittest.TestCase):
    def test_one_bom_and_tabs(self):
        for path in FILES:
            raw = path.read_bytes()
            with self.subTest(path=path.name):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))
                self.assertEqual([n for n, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1)
                                  if re.match(r"^ +\S", line)], [])

    def test_every_te_ai_build_pass_name_it_reads_is_defined(self):
        defined = set()
        for path in FILES:
            defined |= set(re.findall(r"(?m)^(te_ai_build_pass_[a-z_]+) = ", _code(path)))
        variables = {"te_ai_build_pass_idle", "te_ai_build_pass_recent", "te_ai_build_pass_count",
                     "te_ai_build_pass_on_actions", "te_ai_build_pass_effects",
                     "te_ai_build_pass_pending_kind", "te_ai_build_pass_pending_base", "te_ai_build_pass_pending_months",
                     "te_ai_build_pass_pending_state", "te_ai_build_pass_site", "te_ai_build_pass_industry",
                     "te_ai_build_pass_sampled", "te_ai_build_pass_checked", "te_ai_build_pass_built",
                     "te_ai_build_pass_waiting", "te_ai_build_pass_lost", "te_ai_build_pass_cohort",
                     "te_ai_build_pass_cohort_months", "te_ai_build_pass_watcher"}
        variables |= {f"te_ai_build_pass_backoff_{kind}" for kind in KINDS}
        variables |= {f"te_ai_build_pass_{outcome}_{kind}" for kind in KINDS for outcome in ("built", "lost")}
        variables |= {f"te_ai_build_pass_down_{kind}" for kind in KINDS}
        used = set()
        for path in FILES:
            # A name built from a parameter (te_ai_build_pass_wants_$KIND$) is read whole by the tests of the order.
            used |= {name for name in re.findall(r"\b(te_ai_build_pass_[a-z_]+)\b(?!\$)", _code(path))
                     if not name.endswith("_")}
        self.assertEqual(sorted(used - defined - variables), [])


class Wiring(unittest.TestCase):
    def test_an_ai_country_runs_it_monthly_and_the_world_reads_the_verdict(self):
        code = _code(ON_ACTIONS)
        self.assertIn("on_actions = { te_ai_build_pass_on_action }",
                      _norm(_block(code, "on_monthly_pulse_country")))
        self.assertIn("on_actions = { te_ai_build_pass_selfcheck }", _norm(_block(code, "on_monthly_pulse")))
        self.assertEqual(_norm(_block(code, "te_ai_build_pass_on_action")),
                         "trigger = { is_ai = yes } effect = { te_ai_build_pass_effect = yes }")

    def test_it_queues_only_where_the_engine_has_not_and_the_budget_ai_would(self):
        may = _norm(_block(_code(TRIGGERS), "te_ai_build_pass_may_queue"))
        self.assertTrue(may.startswith("is_country_alive = yes is_ai = yes"))
        for part in ("NOT = { is_country_type = decentralized }", "te_free_market_construction_on = yes",
                     "in_default = no", "is_at_war = no", "is_construction_paused = no",
                     "has_variable = te_ai_build_pass_idle",
                     "NOT = { has_variable = te_ai_build_pass_pending_kind }",
                     "NOT = { construction_queue_num_queued_government_levels > 0 }",
                     "has_variable = te_construction_market_price_stabilizer", "net_fixed_income > 0",
                     "OR = { net_fixed_income >= TE_AI_BUILD_PASS_SURPLUS_MIN "
                     "te_ai_build_pass_surplus_share >= TE_AI_BUILD_PASS_SURPLUS_SHARE }",
                     "te_ai_build_pass_means >= 0"):
            with self.subTest(part=part):
                self.assertIn(part, may)


class TheOrder(unittest.TestCase):
    """The list is written once, as one line per entry, and each entry queues its own building in its own site."""

    def test_the_order_is_written_once_inside_the_test_of_means(self):
        effect = _norm(_block(_code(EFFECTS), "te_ai_build_pass_effect"))
        self.assertEqual(re.findall(r"te_ai_build_pass_try = \{ KIND = ([a-z_]+) \}", effect), ORDER)
        first = effect.index("te_ai_build_pass_try")
        self.assertLess(effect.index("te_ai_build_pass_may_queue = yes"), first)
        # Nothing else in the effect picks a building: the list lives on those lines alone.
        self.assertNotIn("start_building_construction", effect)
        self.assertNotIn("te_ai_build_pass_wants_", effect)
        # The order's lines are the doc's and the triggers file's list.
        triggers = TRIGGERS.read_text(encoding="utf-8-sig")
        listed = re.findall(r"(?m)^#   \d\. ([^,]+),", triggers)
        names = {"A Government Administration": "administration", "The country's first power plant": "power_plant",
                 "A railway": "railway", "A university": "university", "A highway": "highway",
                 "An airport": "airport"}
        self.assertEqual([names.get(name, name) for name in listed], ORDER)

    def test_an_entry_is_skipped_once_one_has_queued(self):
        try_ = _norm(_block(_code(EFFECTS), "te_ai_build_pass_try"))
        self.assertEqual(try_, "if = { limit = { NOT = { has_variable = te_ai_build_pass_pending_kind } "
                               "te_ai_build_pass_wants_$KIND$ = yes } te_ai_build_pass_queue_$KIND$ = yes }")
        # te_ai_build_pass_queue sets the pending kind (te_ai_build_pass_pending_start), so the next try skips.
        queue = _norm(_block(_code(EFFECTS), "te_ai_build_pass_queue"))
        self.assertIn("te_ai_build_pass_pending_start = { KIND = $KIND$ }", queue)

    def test_each_entry_queues_its_building_in_its_best_site(self):
        effects, triggers = _code(EFFECTS), _code(TRIGGERS)
        for kind, (number, building, order) in KINDS.items():
            with self.subTest(kind=kind):
                _block(triggers, f"te_ai_build_pass_wants_{kind}")
                body = _norm(_block(effects, f"te_ai_build_pass_queue_{kind}"))
                self.assertEqual(body, f"ordered_scope_state = {{ limit = {{ te_ai_build_pass_{kind}_site = yes }} "
                                       f"order_by = {order} position = 0 check_range_bounds = no save_scope_as = "
                                       f"te_ai_build_pass_site }} te_ai_build_pass_queue = {{ KIND = {number} "
                                       f"BUILDING = {building} }}")
                wants = _norm(_block(triggers, f"te_ai_build_pass_wants_{kind}"))
                self.assertIn(f"any_scope_state = {{ te_ai_build_pass_{kind}_site = yes }}", wants)
                self.assertIn(f"NOT = {{ has_variable = te_ai_build_pass_backoff_{kind} }}", wants)
                self.assertIn(f"te_ai_build_pass_{kind}_weeks <= TE_AI_BUILD_PASS_MAX_WEEKS", wants)

    def test_a_level_is_queued_in_the_saved_site_and_followed_there(self):
        queue = _norm(_block(_code(EFFECTS), "te_ai_build_pass_queue"))
        self.assertTrue(queue.startswith("if = { limit = { exists = scope:te_ai_build_pass_site }"))
        state = queue.index("set_variable = { name = te_ai_build_pass_pending_state value = scope:te_ai_build_pass_site }")
        start = queue.index("te_ai_build_pass_pending_start = { KIND = $KIND$ }")
        build = queue.index("scope:te_ai_build_pass_site = { start_building_construction = $BUILDING$ }")
        # The state first (the base is read there), then the base, then the level.
        self.assertLess(state, start)
        self.assertLess(start, build)
        self.assertIn("set_variable = { name = te_ai_build_pass_recent value = yes days = 45 }", queue)
        self.assertIn("te_ai_build_pass_count_effect = yes", queue)

    def test_the_follow_comes_first_and_the_month_of_waiting_last(self):
        effect = _norm(_block(_code(EFFECTS), "te_ai_build_pass_effect"))
        self.assertTrue(effect.startswith("te_ai_build_pass_follow = yes if = { limit = { "
                                          "te_ai_build_pass_may_queue = yes }"))
        self.assertTrue(effect.endswith(
            "if = { limit = { construction_queue_num_queued_government_levels > 0 } if = { limit = { "
            "has_variable = te_ai_build_pass_idle } remove_variable = te_ai_build_pass_idle } } else = { "
            "set_variable = te_ai_build_pass_idle }"))
        self.assertGreater(effect.index("if = { limit = { construction_queue_num_queued_government_levels > 0 }"),
                           effect.rindex("te_ai_build_pass_try"))

    def test_the_countrys_industry_is_counted_once_before_the_list_and_cleared_after(self):
        effect = _norm(_block(_code(EFFECTS), "te_ai_build_pass_effect"))
        written = effect.index("set_variable = { name = te_ai_build_pass_industry value = "
                               "te_ai_build_pass_country_manufacturing }")
        cleared = effect.index("remove_variable = te_ai_build_pass_industry")
        self.assertLess(written, effect.index("te_ai_build_pass_try"))
        self.assertGreater(cleared, effect.rindex("te_ai_build_pass_try"))
        # Written for every country that could want a highway or an airport.
        self.assertIn("OR = { has_technology_researched = paved_roads has_technology_researched = "
                      "commercial_aviation }", effect[:written])


class WhatEachEntryNeeds(unittest.TestCase):
    """Each entry's technology, rules and site, against the building's own definition."""

    @classmethod
    def setUpClass(cls):
        cls.triggers = _code(TRIGGERS)
        cls.values = _code(VALUES)
        cls.vanilla = buildings.vanilla("buildings")
        cls.mod = buildings.mod_buildings()

    def definition(self, building):
        """The building's top-level fields: the mod's parse for a building the mod defines, else the snapshot's."""
        if building in self.mod:
            return {key: value for key, _, value in buildings.entries(self.mod[building][1])}
        entry = self.vanilla[building][1]
        return {key: value[1] for key, value in entry.items()}

    def test_each_entry_asks_for_the_technology_that_unlocks_its_building(self):
        for kind, (_, building, _) in KINDS.items():
            techs = list(self.definition(building)["unlocking_technologies"])
            with self.subTest(kind=kind):
                self.assertEqual(len(techs), 1)
                self.assertIn(f"has_technology_researched = {techs[0]}",
                              _norm(_block(self.triggers, f"te_ai_build_pass_wants_{kind}")))

    def test_each_entry_weighs_its_buildings_own_points(self):
        for kind, (_, building, _) in KINDS.items():
            cost = self.definition(building)["required_construction"]
            with self.subTest(kind=kind):
                self.assertTrue(_norm(_block(self.values, f"te_ai_build_pass_{kind}_weeks")).startswith(
                    f"value = {cost} multiply = var:te_construction_market_price_stabilizer divide = {{ value = "
                    f"net_fixed_income min = 1 }}"))

    def test_the_administration_and_the_university(self):
        administration = _norm(_block(self.triggers, "te_ai_build_pass_wants_administration"))
        self.assertIn("bureaucracy < te_ai_build_pass_bureaucracy_margin", administration)
        self.assertNotIn("tax_capacity", administration)
        university = _norm(_block(self.triggers, "te_ai_build_pass_wants_university"))
        for part in ("NOT = { has_variable = poland_universities_closed_var }", "bureaucracy >= 0",
                     "te_ai_build_pass_innovation_share < TE_AI_BUILD_PASS_INNOVATION_SHARE"):
            with self.subTest(part=part):
                self.assertIn(part, university)
        self.assertEqual(_norm(_block(self.triggers, "te_ai_build_pass_administration_site")), "is_incorporated = yes")
        self.assertEqual(_norm(_block(self.triggers, "te_ai_build_pass_university_site")),
                         "is_incorporated = yes te_ai_build_pass_staffed = { BUILDING = building_university }")
        self.assertIn("multiply = TE_AI_BUILD_PASS_BUREAUCRACY_MARGIN",
                      _norm(_block(self.values, "te_ai_build_pass_bureaucracy_margin")))

    def test_the_administration_goes_where_taxes_most_outrun_capacity(self):
        # ordered_scope_state takes the highest first: usage less capacity ranks a state short of capacity above one
        # with capacity to spare.
        self.assertEqual(_norm(_block(self.values, "te_ai_build_pass_tax_shortfall")),
                         "value = tax_capacity_usage subtract = tax_capacity")
        constants, values = load(VALUES)
        c = purchase.Country(30000.0, 6000.0)
        short, spare = [Env.evaluate(c, values, "te_ai_build_pass_tax_shortfall", tax_capacity_usage=usage,
                                     tax_capacity=100.0) for usage in (130.0, 70.0)]
        self.assertEqual((short, spare), (30.0, -30.0))

    def test_the_polish_closure_is_vanillas_university_rule(self):
        rule = self.vanilla["building_university"][1]["can_build_government"]
        self.assertIn("poland_universities_closed_var", repr(rule))

    def test_the_first_plant_only_where_nothing_makes_electricity_and_no_partner_brings_it(self):
        wants = _norm(_block(self.triggers, "te_ai_build_pass_wants_power_plant"))
        self.assertIn("NOT = { any_scope_state = { te_state_has_a_power_plant = yes } }", wants)
        self.assertIn("NOT = { te_ai_build_pass_grid_serves = yes }", wants)
        self.assertNotIn("te_ai_build_pass_has_grid_partner", wants)
        self.assertEqual(_norm(_block(self.triggers, "te_ai_build_pass_has_grid_partner")),
                         "has_variable_list = te_grid_partners any_in_list = { variable = te_grid_partners count >= 1 }")
        # Out only where the grid's pass would queue a station: its own technology and site rule.
        self.assertEqual(_norm(_block(self.triggers, "te_ai_build_pass_grid_serves")),
                         "has_technology_researched = electrical_capacitors te_ai_build_pass_has_grid_partner = yes "
                         "any_scope_state = { te_grid_ai_station_site = yes }")
        grid = _norm(_block(_code(ROOT / "common/scripted_effects/power_grid_effects.txt"), "te_grid_ai_build_effect"))
        self.assertTrue(grid.startswith("if = { limit = { has_technology_researched = electrical_capacitors }"))
        for part in ("in_default = no", "construction_queue_government_duration < 52",
                     "OR = { any_scope_state = { te_grid_electricity_production > 0 } has_variable_list = "
                     "te_grid_partners }", "limit = { te_grid_ai_station_site = yes }",
                     "start_building_construction = building_grid_transfer_station"):
            with self.subTest(part=part):
                self.assertIn(part, grid)
        # The pass itself holds the grid's other tests: not in default, and an empty government queue.
        may = _norm(_block(self.triggers, "te_ai_build_pass_may_queue"))
        self.assertIn("in_default = no", may)
        self.assertIn("NOT = { construction_queue_num_queued_government_levels > 0 }", may)
        # For a country with no power the site is a partner's station near (the market-area branch needs power).
        site = _norm(_block(_code(ROOT / "common/scripted_triggers/power_grid_triggers.txt"), "te_grid_ai_station_site"))
        self.assertIn("te_grid_ai_partner_near = { ANY = no }", site)

    def test_what_counts_as_power_is_every_building_whose_methods_make_electricity(self):
        # Derived from the production methods (test_ai_building_values.electricity_makers), not a hand list; the
        # trigger the entry reads names exactly these, built or under construction.
        makers = buildings.electricity_makers()
        self.assertEqual(sorted(makers), [
            "building_calcutta_electric_victoria_house", "building_eea_dock_sud_power_station",
            "building_electricidad_caracas_power_house", "building_fusion_plant", "building_generic_power_hub",
            "building_grid_transfer_station", "building_hanseong_jeongi_gwanghwamun_station", "building_hydro_plant",
            "building_ingolstadt_power_station", "building_nuclear_plant", "building_power_plant",
            "building_renewable_energy_plant", "building_rosatom_mayak_association",
            "building_siam_electric_wat_liab_station", "building_solar_receiver",
            "building_tokyo_electric_asakusa_station"])
        trigger = _norm(_block(_code(COVERAGE_TRIGGERS), "te_state_has_a_power_plant"))
        built = set(re.findall(r"has_building = (building_[a-z_]+)", trigger))
        queued = set(re.findall(r"is_building_type = (building_[a-z_]+)", trigger))
        self.assertEqual(built, makers)
        self.assertEqual(queued, makers)
        self.assertIn("is_under_construction = yes", trigger)

    def test_the_plant_carries_the_buildings_own_rules(self):
        wants = _norm(_block(self.triggers, "te_ai_build_pass_wants_power_plant"))
        self.assertEqual(self.vanilla["building_power_plant"][1]["possible"],
                         ["=", {"owner": ["=", {"NOT": ["=", {"has_law_or_variant": [
                             "=", "law_type:law_industry_banned"]}]}]}])
        self.assertIn("NOT = { has_law_or_variant = law_type:law_industry_banned }", wants)
        # Every INJECT of the plant in the mod, wherever it is (extra_buildings.txt and zz_te_carbon_capture_injects.txt
        # today): the one rule any of them adds to a government's construction is the one the pass copies
        # (can_build_private is the investors').
        rules = {}
        for path in sorted((ROOT / "common/buildings").glob("*.txt")):
            code = _code(path)
            for match in re.finditer(r"(?m)^INJECT:building_power_plant = \{", code):
                body = _norm(_block(code[match.start():], "INJECT:building_power_plant"))
                for rule in ("possible", "can_build_government", "potential"):
                    if f"{rule} = {{" in body:
                        rules.setdefault(rule, []).append((path.name, body))
        self.assertGreaterEqual(sum(1 for path in (ROOT / "common/buildings").glob("*.txt")
                                    if "INJECT:building_power_plant = {" in _code(path)), 2)
        self.assertEqual(sorted(rules), ["can_build_government"])
        self.assertEqual([name for name, _ in rules["can_build_government"]], ["extra_buildings.txt"])
        self.assertIn("can_build_government = { rt_fossil_construction_allowed_here = yes }",
                      rules["can_build_government"][0][1])
        self.assertEqual(_norm(_block(self.triggers, "te_ai_build_pass_power_plant_site")),
                         "is_incorporated = yes has_building = building_urban_center "
                         "rt_fossil_construction_allowed_here = yes")

    def test_the_plant_goes_where_its_electricity_has_buyers(self):
        users = _norm(_block(self.values, "te_ai_build_pass_power_users"))
        self.assertEqual(users, "value = 0 every_scope_building = { limit = { OR = { is_building_type = "
                                "building_urban_center is_building_group = bg_manufacturing } } add = level }")
        # The plant's own technology lets urban centres light their streets with Electricity.
        lights = buildings.vanilla("pms")["pm_electric_streetlights"][1]
        self.assertEqual(lights["unlocking_technologies"][1], ["electrical_generation"])
        self.assertEqual(lights["required_input_goods"][1], "electricity")

    def test_a_railway_where_infrastructure_is_short_by_more_than_the_margin(self):
        self.assertEqual(_norm(_block(self.values, "te_ai_build_pass_infrastructure_shortfall")),
                         "value = infrastructure_usage subtract = infrastructure")
        self.assertEqual(_norm(_block(self.values, "te_ai_build_pass_infrastructure_margin")),
                         "value = infrastructure_usage multiply = TE_AI_BUILD_PASS_INFRASTRUCTURE_MARGIN")
        self.assertEqual(_norm(_block(self.triggers, "te_ai_build_pass_railway_site")),
                         "is_incorporated = yes te_ai_build_pass_infrastructure_shortfall > "
                         "te_ai_build_pass_infrastructure_margin")
        # The railway has no level cap of its own.
        self.assertNotIn("has_max_level", self.vanilla["building_railway"][1])

    def test_the_mods_railway_successors_are_its_own_methods(self):
        # No building of the mod's replaces the railway: its later trains are methods of the same building, so a
        # level the pass queues runs what the building runs. Highways and airports are entries of their own.
        group = buildings.vanilla("pm_groups")["pmg_base_building_railway"][1]["production_methods"][1]
        self.assertIn("pm_early_trains", group)
        injected = _norm(_block(_code(ROOT / "common/production_method_groups/extra_pm_groups.txt"),
                                "INJECT:pmg_base_building_railway"))
        for method in ("pm_autonomous_trains", "pm_vactrain_freight"):
            self.assertIn(method, injected)

    def test_highways_and_airports_in_a_major_industrial_state_under_the_cap(self):
        for kind in ("highway", "airport"):
            definition = self.definition(f"building_{kind}")
            with self.subTest(kind=kind):
                # The cap: has_max_level and no number of the building's own; the state modifier sets it.
                self.assertEqual(definition["has_max_level"], "yes")
                self.assertNotIn("max_level", {k for k in definition if k != "has_max_level"})
                self.assertEqual(_norm(_block(self.values, f"te_ai_build_pass_{kind}_cap")),
                                 f"value = modifier:state_building_{kind}_max_level_add")
                self.assertIn(f"state_building_{kind}_max_level_add = {{",
                              (ROOT / "common/modifier_type_definitions/mod_entity_modifier_types.txt").read_text(
                                  encoding="utf-8-sig"))
                site = _norm(_block(self.triggers, f"te_ai_build_pass_{kind}_site"))
                self.assertEqual(site, f"is_incorporated = yes te_ai_build_pass_major_industrial = yes "
                                       f"te_ai_build_pass_staffed = {{ BUILDING = building_{kind} }} OR = {{ "
                                       f"any_scope_building = {{ is_building_type = building_{kind} "
                                       f"can_queue_building_levels = 1 }} AND = {{ NOT = {{ any_scope_building = {{ "
                                       f"is_building_type = building_{kind} }} }} te_ai_build_pass_{kind}_cap >= 1 }} }}")
        self.assertEqual(_norm(_block(self.triggers, "te_ai_build_pass_major_industrial")),
                         "te_ai_build_pass_manufacturing_levels >= te_ai_build_pass_industrial_floor")
        floor = _norm(_block(self.values, "te_ai_build_pass_industrial_floor"))
        self.assertEqual(floor, "value = 1000000 if = { limit = { owner ?= { has_variable = te_ai_build_pass_industry "
                                "} } value = owner.var:te_ai_build_pass_industry multiply = "
                                "TE_AI_BUILD_PASS_INDUSTRIAL_SHARE min = 1 }")
        for name in ("te_ai_build_pass_manufacturing_levels", "te_ai_build_pass_country_manufacturing"):
            self.assertEqual(_norm(_block(self.values, name)), "value = 0 every_scope_building = { limit = { "
                                                               "is_building_group = bg_manufacturing } add = level }")

    def test_staffed_is_the_highways_and_the_airports_own_rule_to_expand(self):
        self.assertEqual(_norm(_block(self.triggers, "te_ai_build_pass_staffed")),
                         "NOT = { any_scope_building = { is_building_type = $BUILDING$ occupancy < 0.8 } }")
        for kind in ("highway", "airport"):
            with self.subTest(kind=kind):
                rule = _norm(_block(_code(ROOT / "common/buildings/11_zz_te_infrastructure.txt"), f"building_{kind}"))
                self.assertIn("should_auto_expand = { occupancy >= 0.8 }", rule)

    def methods(self, group):
        """The methods of a group, vanilla's and the mod's INJECTs, each with its body in the mod (or vanilla's)."""
        names = list(buildings.vanilla("pm_groups").get(group, ["=", {"production_methods": ["=", []]}])[1]
                     ["production_methods"][1])
        groups = _code(ROOT / "common/production_method_groups/extra_pm_groups.txt")
        for prefix in ("INJECT:", "REPLACE_OR_CREATE:"):
            if re.search(rf"(?m)^{prefix}{group} = \{{", groups):
                names += re.findall(r"\b(pm_[a-z_-]+)\b", _block(groups, f"{prefix}{group}"))
        pms = _code(ROOT / "common/production_methods/extra_pms.txt")
        bodies = {}
        for name in dict.fromkeys(names):
            for form in (f"REPLACE:{name}", name):
                if re.search(rf"(?m)^{re.escape(form)} = \{{", pms):
                    bodies[name] = _block(pms, form)
                    break
        return names, bodies

    def where_infrastructure(self, body):
        """Which state_modifiers blocks of a method carry state_infrastructure_add."""
        state = _block(body, "\tstate_modifiers")
        return sorted(kind for kind in ("workforce_scaled", "level_scaled", "unscaled")
                      if re.search(rf"(?m)^\t\t{kind} = \{{", state)
                      and "state_infrastructure_add" in _block(state, f"\t\t{kind}"))

    def test_a_railway_needs_no_staffing_its_infrastructure_is_per_level(self):
        # The mod's railway methods all give their infrastructure per level (#1050), so a level nobody staffs still
        # closes the shortfall: its site has no staffing test.
        names, bodies = self.methods("pmg_base_building_railway")
        self.assertGreaterEqual(len(names), 12)
        self.assertEqual(sorted(names), sorted(bodies))
        for name in names:
            with self.subTest(method=name):
                self.assertEqual(self.where_infrastructure(bodies[name]), ["level_scaled"])
        self.assertNotIn("te_ai_build_pass_staffed", _block(self.triggers, "te_ai_build_pass_railway_site"))

    def test_an_airports_and_a_highways_state_modifiers_come_with_their_staff(self):
        # Every state modifier of their methods is per worker: an empty level gives none, the owner's reason to keep
        # the airport included, so the staffing test keeps a level from joining one that stands empty.
        for group in ("pmg_base_building_airport", "pmg_base_building_highway"):
            names, bodies = self.methods(group)
            self.assertTrue(names, group)
            for name in names:
                state = _block(bodies[name], "\tstate_modifiers")
                with self.subTest(method=name):
                    self.assertEqual(re.findall(r"(?m)^\t\t([a-z_]+) = \{", state), ["workforce_scaled"])
                    self.assertEqual(self.where_infrastructure(bodies[name]), ["workforce_scaled"])

    def test_the_two_laws_that_force_a_subsidy_on_both(self):
        laws = _code(ROOT / "common/laws/construction_system_law_injections.txt")
        forcing = sorted(re.findall(r"(?m)^INJECT:(law_[a-z_]+) = \{", laws))
        forced = [law for law in forcing if "country_building_airport_require_subsidies_bool = yes" in _block(
            laws, f"INJECT:{law}")]
        self.assertEqual(forced, ["law_command_economy", "law_interventionism"])
        for law in forced:
            self.assertIn("country_building_highway_require_subsidies_bool = yes", _block(laws, f"INJECT:{law}"))

    def test_manufacturing_is_the_three_industry_groups(self):
        groups = buildings.vanilla("building_groups")
        children = sorted(name for name, entry in groups.items()
                          if entry[1].get("parent_group", [None, None])[1] == "bg_manufacturing")
        self.assertEqual(children, ["bg_heavy_industry", "bg_light_industry", "bg_military_industry"])


class Env(unittest.TestCase):
    """The pass's values through the construction market's evaluator."""

    @classmethod
    def setUpClass(cls):
        cls.constants, cls.values = load(VALUES)

    def value(self, c, name, **names):
        return Env.evaluate(c, self.values, name, **names)

    @staticmethod
    def evaluate(c, values, name, **names):
        env = c.env()
        env.values = dict(env.values, **values)
        env.names.update(names)
        return env.value(name)


class TheMeans(Env):
    def means(self, c):
        return self.value(c, "te_ai_build_pass_means")

    def test_by_rate_reserves_and_debt(self):
        surplus, era = 0.4 * 75817.0, 2.5
        for spread, reserves, debt, has_means in (
                # A high rate asks for a reserve first.
                (9.0, 0.0, 0.0, False), (9.0, 0.05, 0.0, False), (9.0, purchase.RESERVE_MAX, 0.0, True),
                # The middle asks for nothing and tolerates nothing: no debt.
                (purchase.SPREAD_MID, 0.0, 0.0, True), (purchase.SPREAD_MID, 0.0, 0.01, False),
                # A low rate tolerates a debt up to DEBT_MAX.
                (0.0, 0.0, 0.05, True), (0.0, 0.0, purchase.PASS_DEBT_MAX - 0.001, True), (0.0, 0.0, 0.11, False),
                (3.0, 0.0, 0.04, True), (3.0, 0.0, 0.06, False)):
            for constants in (None, purchase.NO_CREDIT):
                c = purchase.Country(75817.0, surplus, 1256.0, reserves, debt, rate=era + spread, era=era,
                                     constants=constants)
                with self.subTest(spread=spread, reserves=reserves, debt=debt, credit_switch=constants):
                    # The credit's switch at 0 leaves the pass reaching a debtor at a low rate.
                    self.assertEqual(self.means(c) >= 0, has_means)

    def test_with_its_own_number_at_zero_it_reaches_no_debtor(self):
        c = purchase.Country(75817.0, 30000.0, 1256.0, 0.0, 0.01, rate=2.5, constants={"TE_AI_BUILD_PASS_DEBT_MAX": 0.0})
        self.assertLess(self.means(c), 0)

    def test_in_a_crisis_at_war_or_in_a_bubble_a_government_in_debt_has_none(self):
        for crisis, at_war, bubble in ((True, False, None), (False, True, None), (False, False, 60.0)):
            c = purchase.Country(75817.0, 30000.0, 1256.0, 0.0, 0.03, rate=2.5, crisis=crisis, at_war=at_war,
                                 bubble=bubble)
            with self.subTest(crisis=crisis, at_war=at_war, bubble=bubble):
                self.assertLess(self.means(c), 0)

    def test_a_thin_surplus_has_the_means_only_for_a_thin_debt(self):
        # The tolerance is what a third of the surplus carries at the high rate: about 0.0044 of a 320-week ceiling
        # for a surplus of 1% of fixed income.
        thin = [purchase.Country(10000.0, 100.0, 1256.0, 0.0, debt, rate=2.5) for debt in (0.004, 0.006)]
        self.assertEqual([self.means(c) >= 0 for c in thin], [True, False])

    def test_the_innovation_share_reads_one_where_the_cap_reads_nothing(self):
        body = _norm(_block(_code(VALUES), "te_ai_build_pass_innovation_share"))
        self.assertEqual(body, "value = 1 if = { limit = { te_ai_build_pass_innovation_cap > 0 } value = "
                               "country_innovation divide = te_ai_build_pass_innovation_cap }")
        self.assertIn("te_ai_build_pass_innovation_cap = { value = modifier:country_weekly_innovation_max_add }",
                      _code(VALUES))


class WhatItQueues(Env):
    def test_two_years_of_the_surplus_pays_for_the_level(self):
        # A sixth of fixed income at 1,250 a point: a university's or a power plant's 400 points from 28,800 a week,
        # an administration's 100 from 7,200, a railway's 800 from 57,700, a highway's or an airport's 2,000 from
        # 144,200 (the values file's figures).
        for kind, income in (("university", 28800.0), ("administration", 7200.0), ("power_plant", 28800.0),
                             ("railway", 57700.0), ("highway", 144200.0), ("airport", 144200.0)):
            for scale, fits in ((1.02, True), (0.98, False)):
                c = purchase.Country(income * scale, income * scale / 6, 1250.0)
                with self.subTest(kind=kind, income=income * scale):
                    self.assertEqual(self.value(c, f"te_ai_build_pass_{kind}_weeks") <= purchase.PASS_MAX_WEEKS,
                                     fits)

    def test_close_to_net_zero_is_two_hundredths_of_usage(self):
        c = purchase.Country(30000.0, 6000.0)
        self.assertAlmostEqual(self.value(c, "te_ai_build_pass_bureaucracy_margin", bureaucracy_usage=4000.0),
                               purchase.PASS_BUREAUCRACY_MARGIN * 4000.0, delta=0.001)

    def test_the_numbers_it_reads_are_the_values_files(self):
        triggers, values = _code(TRIGGERS), _code(VALUES)
        for name in ("TE_AI_BUILD_PASS_MAX_WEEKS", "TE_AI_BUILD_PASS_INNOVATION_SHARE"):
            self.assertIn(name, triggers)
        for name in ("TE_AI_BUILD_PASS_BUREAUCRACY_MARGIN", "TE_AI_BUILD_PASS_INFRASTRUCTURE_MARGIN",
                     "TE_AI_BUILD_PASS_INDUSTRIAL_SHARE"):
            self.assertIn(f"multiply = {name}", values)


class TheFollow(unittest.TestCase):
    """What became of each level the pass queued: the back-off, the reserve gate's mark and the self-check read it."""

    def test_it_starts_from_the_built_levels_of_the_kind(self):
        start = _norm(_block(_code(EFFECTS), "te_ai_build_pass_pending_start"))
        self.assertTrue(start.startswith(
            "set_variable = { name = te_ai_build_pass_pending_kind value = $KIND$ } set_variable = { name = "
            "te_ai_build_pass_pending_base value = te_ai_build_pass_tracked_levels } set_variable = { name = "
            "te_ai_build_pass_pending_months value = 0 }"))
        # The cohort: a sampled government's level of any kind but an administration (2).
        self.assertEqual(KINDS["administration"][0], 2)
        self.assertIn("if = { limit = { NOT = { has_global_variable = te_ai_build_pass_checked } NOT = { "
                      "var:te_ai_build_pass_pending_kind = 2 } te_ai_build_pass_in_sample = yes }", start)
        init = start.index("if = { limit = { NOT = { has_global_variable = te_ai_build_pass_cohort } }")
        for counter in ("cohort", "cohort_months", "built", "waiting", "lost"):
            self.assertIn(f"set_global_variable = {{ name = te_ai_build_pass_{counter} value = 0 }}", start[init:])
        # Every kind's counters start with the totals; no administration in the cohort's.
        self.assertEqual(sorted(re.findall(r"te_ai_build_pass_tally_start = \{ KIND = ([a-z_]+) \}", start)),
                         sorted(kind for kind in KINDS if kind != "administration"))
        self.assertEqual(sorted(re.findall(r"te_ai_build_pass_down_start = \{ KIND = ([a-z_]+) \}", start)),
                         sorted(KINDS))
        self.assertEqual(_norm(_block(_code(EFFECTS), "te_ai_build_pass_tally_start")),
                         "set_global_variable = { name = te_ai_build_pass_built_$KIND$ value = 0 } "
                         "set_global_variable = { name = te_ai_build_pass_lost_$KIND$ value = 0 }")
        # Closed: a level joins only while the cohort has room, counted as it joins.
        joined = start.index("if = { limit = { te_ai_build_pass_cohort_g < te_ai_build_pass_cohort_size } "
                             "change_global_variable = { name = te_ai_build_pass_cohort add = 1 } "
                             "set_variable = te_ai_build_pass_sampled }")
        self.assertGreater(joined, init)
        self.assertEqual(start.count("set_variable = te_ai_build_pass_sampled"), 1)

    def test_the_sample_is_a_government_the_engine_would_not_queue_for(self):
        self.assertEqual(_norm(_block(_code(TRIGGERS), "te_ai_build_pass_in_sample")),
                         "OR = { scaled_debt > 0 scaled_gold_reserves < 0.02 }")
        self.assertEqual(purchase.MOD_NAI["CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS"], 0.02)

    def test_built_lost_or_waiting_with_the_base_following_a_downsizing(self):
        follow = _norm(_block(_code(EFFECTS), "te_ai_build_pass_follow"))
        self.assertTrue(follow.startswith("te_ai_build_pass_watch = yes if = { limit = { has_variable = "
                                          "te_ai_build_pass_pending_kind }"))
        # A level of the kind taken down in the state lowers the base to what stands.
        down = follow.index("if = { limit = { te_ai_build_pass_tracked_levels < var:te_ai_build_pass_pending_base } "
                            "set_variable = { name = te_ai_build_pass_pending_base value = "
                            "te_ai_build_pass_tracked_levels } }")
        built = follow.index("te_ai_build_pass_tracked_levels > var:te_ai_build_pass_pending_base")
        # Lost: none of the kind queued in the state, or (an investor's level of the kind queued there) the
        # government queue the pass's level was alone in is empty.
        lost = follow.index("OR = { te_ai_build_pass_tracked_queued <= 0 NOT = { "
                            "construction_queue_num_queued_government_levels > 0 } }")
        waiting = follow.index("var:te_ai_build_pass_pending_months >= te_ai_build_pass_waiting_months")
        self.assertLess(down, built)
        self.assertLess(built, lost)
        self.assertLess(lost, waiting)
        self.assertLess(built, follow.index("te_ai_build_pass_tally = { OUTCOME = built }"))
        self.assertLess(follow.index("te_ai_build_pass_tally = { OUTCOME = built }"),
                        follow.index("te_ai_build_pass_watch_start = yes"))
        self.assertLess(follow.index("te_ai_build_pass_watch_start = yes"), lost)
        self.assertEqual(follow.count("te_ai_build_pass_watch_start = yes"), 1)
        self.assertLess(lost, follow.index("te_ai_build_pass_tally = { OUTCOME = lost }"))
        self.assertLess(follow.index("te_ai_build_pass_tally = { OUTCOME = lost }"),
                        follow.index("te_ai_build_pass_backoff = yes"))
        self.assertLess(follow.index("te_ai_build_pass_backoff = yes"), waiting)
        self.assertLess(waiting, follow.index("te_ai_build_pass_waiting add = 1"))
        # Each counts only a sampled level, and only until the verdict.
        self.assertEqual(follow.count("has_variable = te_ai_build_pass_sampled NOT = { has_global_variable = "
                                      "te_ai_build_pass_checked }"), 2)
        self.assertEqual(follow.count("te_ai_build_pass_pending_clear = yes"), 2)
        clear = _norm(_block(_code(EFFECTS), "te_ai_build_pass_pending_clear"))
        for name in ("kind", "base", "months"):
            self.assertIn(f"remove_variable = te_ai_build_pass_pending_{name}", clear)
        for name in ("te_ai_build_pass_pending_state", "te_ai_build_pass_sampled"):
            self.assertIn(f"if = {{ limit = {{ has_variable = {name} }} remove_variable = {name} }}", clear)

    def test_a_lost_level_backs_its_kind_off_for_a_year(self):
        backoff = _norm(_block(_code(EFFECTS), "te_ai_build_pass_backoff"))
        days = int(purchase.PASS_BACKOFF_DAYS)
        branches = re.findall(r"limit = \{ var:te_ai_build_pass_pending_kind = (\d) \} set_variable = \{ name = "
                              r"te_ai_build_pass_backoff_([a-z_]+) value = yes days = (\d+) \}", backoff)
        self.assertEqual({kind: (str(number), str(days)) for number, kind, days in branches},
                         {kind: (str(number), str(days)) for kind, (number, _, _) in KINDS.items()})
        # The literal is the values file's number.
        self.assertEqual(purchase._parsed()["constants"]["TE_AI_BUILD_PASS_BACKOFF_DAYS"], days)

    def test_a_level_built_and_gone_again_within_two_years_backs_its_kind_off(self):
        effects, triggers = _code(EFFECTS), _code(TRIGGERS)
        start = _norm(_block(effects, "te_ai_build_pass_watch_start"))
        branches = re.findall(r"limit = \{ var:te_ai_build_pass_pending_kind = (\d) \} te_ai_build_pass_watch_set = "
                              r"\{ KIND = ([a-z_]+) \}", start)
        self.assertEqual({kind: int(number) for number, kind in branches},
                         {kind: number for kind, (number, _, _) in KINDS.items()})
        days = int(purchase._parsed()["constants"]["TE_AI_BUILD_PASS_WATCH_DAYS"])
        self.assertEqual(days, 730)
        self.assertEqual(_norm(_block(effects, "te_ai_build_pass_watch_set")),
                         f"set_variable = {{ name = te_ai_build_pass_watch_state_$KIND$ value = "
                         f"var:te_ai_build_pass_pending_state days = {days} }} set_variable = {{ name = "
                         f"te_ai_build_pass_watch_level_$KIND$ value = te_ai_build_pass_tracked_levels days = {days} }}")
        watch = _norm(_block(effects, "te_ai_build_pass_watch"))
        self.assertEqual(dict(re.findall(r"te_ai_build_pass_watch_one = \{ KIND = ([a-z_]+) BUILDING = "
                                         r"(building_[a-z_]+) \}", watch)),
                         {kind: building for kind, (_, building, _) in KINDS.items()})
        one = _norm(_block(effects, "te_ai_build_pass_watch_one"))
        backoff = int(purchase.PASS_BACKOFF_DAYS)
        self.assertEqual(one, "if = { limit = { has_variable = te_ai_build_pass_watch_state_$KIND$ has_variable = "
                              "te_ai_build_pass_watch_level_$KIND$ te_ai_build_pass_watch_fell = { KIND = $KIND$ "
                              "BUILDING = $BUILDING$ } } set_variable = { name = te_ai_build_pass_backoff_$KIND$ value = "
                              f"yes days = {backoff} }} te_ai_build_pass_down_start = {{ KIND = $KIND$ }} "
                              "change_global_variable = { name = te_ai_build_pass_down_$KIND$ add = 1 } "
                              "remove_variable = te_ai_build_pass_watch_state_$KIND$ remove_variable = "
                              "te_ai_build_pass_watch_level_$KIND$ }")
        # Fell: the state holds no building of the kind at the level it had once built, none at all included.
        self.assertEqual(_norm(_block(triggers, "te_ai_build_pass_watch_fell")),
                         "save_temporary_scope_as = te_ai_build_pass_watcher var:te_ai_build_pass_watch_state_$KIND$ ?= "
                         "{ NOT = { any_scope_building = { is_building_type = $BUILDING$ level >= "
                         "scope:te_ai_build_pass_watcher.var:te_ai_build_pass_watch_level_$KIND$ } } }")
        self.assertEqual(_norm(_block(effects, "te_ai_build_pass_down_start")),
                         "if = { limit = { NOT = { has_global_variable = te_ai_build_pass_down_$KIND$ } } "
                         "set_global_variable = { name = te_ai_build_pass_down_$KIND$ value = 0 } }")

    def test_each_level_is_counted_by_its_kind_in_its_state(self):
        values = _code(VALUES)
        for name, field in (("te_ai_build_pass_tracked_levels", "level"),
                            ("te_ai_build_pass_tracked_queued", "te_construction_market_building_queued_levels")):
            body = _norm(_block(values, name))
            branches = re.findall(r"limit = \{ var:te_ai_build_pass_pending_kind = (\d) \} "
                                  r"var:te_ai_build_pass_pending_state \?= \{ every_scope_building = \{ limit = \{ "
                                  r"is_building_type = (building_[a-z_]+) \} add = ([a-z_]+) \} \}", body)
            with self.subTest(value=name):
                self.assertTrue(body.startswith("value = 0 if = {"))
                self.assertEqual({int(number): (building, added) for number, building, added in branches},
                                 {number: (building, field) for number, building, _ in KINDS.values()})
        self.assertIn("te_construction_market_building_queued_levels = { value = level_after_queued_constructions "
                      "subtract = level }",
                      _norm(_code(ROOT / "common/script_values/te_construction_market_ai_values.txt")))

    def test_a_big_level_waits_longer_before_it_counts_as_waiting(self):
        body = _norm(_block(_code(VALUES), "te_ai_build_pass_waiting_months"))
        self.assertEqual(body, "value = 18 if = { limit = { var:te_ai_build_pass_pending_kind = 3 } value = 24 } "
                               "else_if = { limit = { var:te_ai_build_pass_pending_kind >= 5 } value = 36 }")
        self.assertEqual(KINDS["railway"][0], 3)
        self.assertEqual({KINDS["highway"][0], KINDS["airport"][0]}, {5, 6})

    def test_each_outcome_is_tallied_in_all_and_by_kind(self):
        tally = _norm(_block(_code(EFFECTS), "te_ai_build_pass_tally"))
        self.assertTrue(tally.startswith("change_global_variable = { name = te_ai_build_pass_$OUTCOME$ add = 1 }"))
        branches = re.findall(r"limit = \{ var:te_ai_build_pass_pending_kind = (\d) \} change_global_variable = \{ "
                              r"name = te_ai_build_pass_\$OUTCOME\$_([a-z_]+) add = 1 \}", tally)
        # No administration: the cohort holds none.
        self.assertEqual({kind: int(number) for number, kind in branches},
                         {kind: number for kind, (number, _, _) in KINDS.items() if kind != "administration"})

    def test_the_reserve_gates_check_leaves_out_what_the_pass_queued(self):
        gate = _norm(_code(GATE_CHECK))
        # The watch: the 45-day mark, or a level still followed; the control: a level still followed.
        self.assertIn("NOT = { has_variable = te_ai_build_pass_recent } NOT = { has_variable = "
                      "te_ai_build_pass_pending_kind }", gate)
        self.assertIn("construction_queue_num_queued_government_levels > 0 NOT = { has_variable = "
                      "te_ai_build_pass_pending_kind } }", gate)
        self.assertIn("name = te_ai_build_pass_recent value = yes days = 45", _norm(_code(EFFECTS)))


class TheSelfCheck(unittest.TestCase):
    def test_the_verdict_once_every_level_of_a_closed_cohort_is_read(self):
        check = _norm(_block(_code(ON_ACTIONS), "te_ai_build_pass_selfcheck"))
        self.assertIn("trigger = { NOT = { has_global_variable = te_ai_build_pass_checked } has_global_variable = "
                      "te_ai_build_pass_cohort te_ai_build_pass_cohort_g >= te_ai_build_pass_cohort_size }", check)
        effect = check[check.index("effect = {"):]
        self.assertTrue(effect.startswith(
            "effect = { change_global_variable = { name = te_ai_build_pass_cohort_months add = 1 } if = { limit = { "
            "OR = { te_ai_build_pass_sampled_g >= te_ai_build_pass_cohort_g te_ai_build_pass_cohort_months_g >= "
            "te_ai_build_pass_cohort_wait } } set_global_variable = te_ai_build_pass_checked debug_log = "
            "\"TE_SELF_CHECK START ai_build_pass"))
        values = _code(VALUES)
        self.assertEqual(_norm(_block(values, "te_ai_build_pass_cohort_size")), "value = 36")
        # The wait outlasts the longest a level can stay unread: waiting at 36 months, read on the follow after.
        waiting = re.findall(r"value = (\d+)", _block(values, "te_ai_build_pass_waiting_months"))
        self.assertEqual(_norm(_block(values, "te_ai_build_pass_cohort_wait")),
                         f"value = {max(int(w) for w in waiting) + 2}")
        self.assertEqual(_norm(_block(values, "te_ai_build_pass_unread_g")),
                         "value = te_ai_build_pass_cohort_g subtract = te_ai_build_pass_sampled_g")
        ok = effect.index("te_ai_build_pass_built_g >= 6 te_ai_build_pass_lost_share <= 0.25")
        broken = effect.index("te_ai_build_pass_decided_g >= 6 te_ai_build_pass_lost_share >= 0.5")
        self.assertLess(effect.index("START"), effect.index("random_country"))
        self.assertLess(ok, effect.index("TE_SELF_CHECK OK ai_build_pass"))
        self.assertLess(ok, broken)
        self.assertLess(broken, effect.index("TE_SELF_CHECK BROKEN ai_build_pass"))
        self.assertLess(effect.index("TE_SELF_CHECK BROKEN"), effect.index("TE_SELF_CHECK NO_VERDICT ai_build_pass"))

    def test_lost_is_judged_on_the_levels_whose_fate_is_known(self):
        values = _code(VALUES)
        self.assertEqual(_norm(_block(values, "te_ai_build_pass_decided_g")),
                         "value = global_var:te_ai_build_pass_built add = global_var:te_ai_build_pass_lost")
        self.assertEqual(_norm(_block(values, "te_ai_build_pass_lost_share")),
                         "value = global_var:te_ai_build_pass_lost divide = { value = te_ai_build_pass_decided_g "
                         "min = 1 }")
        self.assertEqual(_norm(_block(values, "te_ai_build_pass_sampled_g")),
                         "value = te_ai_build_pass_decided_g add = global_var:te_ai_build_pass_waiting")

    def test_the_verdict_prints_built_and_lost_by_kind(self):
        text = ON_ACTIONS.read_text(encoding="utf-8-sig")
        values = _code(VALUES)
        for line in re.findall(r'debug_log = "(TE_SELF_CHECK (?:OK|BROKEN|NO_VERDICT) [^"]+)"', text):
            with self.subTest(line=line[:40]):
                for kind, short in SHORT.items():
                    if kind == "administration":
                        continue
                    self.assertIn(f"{short}=[SCOPE.ScriptValue('te_ai_build_pass_built_{kind}_g')|0]/"
                                  f"[SCOPE.ScriptValue('te_ai_build_pass_lost_{kind}_g')|0]", line)
                self.assertNotIn("adm=", line)
                self.assertIn("unread=[SCOPE.ScriptValue('te_ai_build_pass_unread_g')|0]", line)
                self.assertIn("down uni/adm/rail/power/road/air=" + "/".join(
                    f"[SCOPE.ScriptValue('te_ai_build_pass_down_{kind}_g')|0]" for kind in (
                        "university", "administration", "railway", "power_plant", "highway", "airport")), line)
        for kind in KINDS:
            outcomes = ("down",) if kind == "administration" else ("built", "lost", "down")
            for outcome in outcomes:
                self.assertIn(f"te_ai_build_pass_{outcome}_{kind}_g = {{ value = "
                              f"global_var:te_ai_build_pass_{outcome}_{kind} }}", values)

    def test_its_lines_fit_log_triage(self):
        lines = re.findall(r'debug_log = "(TE_SELF_CHECK [^"]+)"', ON_ACTIONS.read_text(encoding="utf-8-sig"))
        self.assertEqual(len(lines), 4)
        for line in lines:
            printed = re.sub(r"\[SCOPE\.ScriptValue\('[a-z_]+'\)\|0\]", "999", line)
            printed = printed.replace("[TimeKeeper.GetCurrentDate.GetString]", "September 30, 1947")
            with self.subTest(line=line[:60]):
                self.assertLess(len(printed), 400)

    def test_the_docs_and_the_play_test_list_carry_it(self):
        doc = AI_DOC.read_text(encoding="utf-8")
        self.assertIn("te_ai_build_pass_effects.txt", doc)
        self.assertIn("ai_build_pass", doc)
        playtest = PLAYTEST.read_text(encoding="utf-8")
        self.assertIn("TE_SELF_CHECK … ai_build_pass", playtest)
        for field in ("rate", "cm_reserve", "cm_credit", "cm_pass", "inf_short_states", "inf_short", "rail_sites",
                      "pp_states", "elec_made", "elec_used", "elec_price", "q_power"):
            self.assertIn(f"`{field}`", playtest)


if __name__ == "__main__":
    unittest.main()
