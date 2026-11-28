"""The AI electrification pass (common/scripted_effects/te_ai_power_pass_effects.txt, #1877 trap 2).

Monthly, for each AI country with Electrical Generation: follow each batch of plant levels it queued; switch to electric
street lights the urban centers of each state whose power now covers them; and, with under a year of government
construction queued and not in default, queue in the state shortest of Electricity, one a month, a batch of vanilla's
coal and oil plant sized to what the state is short of with its lights counted (owner, 2026-11-28: government
construction, plants sized to the lights, electric lights only). This file holds the pass's figures to the methods they
come from, its copies of the plant's gates to the building's own, and its hooks and self-checks.

Run: python3 -m pytest test_ai_power_pass.py -q
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EFFECTS = ROOT / "common/scripted_effects/te_ai_power_pass_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/te_ai_power_pass_triggers.txt"
VALUES = ROOT / "common/script_values/te_ai_power_pass_values.txt"
ON_ACTIONS = ROOT / "common/on_actions/te_ai_power_pass_on_actions.txt"
FILES = (EFFECTS, TRIGGERS, VALUES, ON_ACTIONS)
EXTRA_PMS = ROOT / "common/production_methods/extra_pms.txt"
EXTRA_PM_GROUPS = ROOT / "common/production_method_groups/extra_pm_groups.txt"
EXTRA_BUILDINGS = ROOT / "common/buildings/extra_buildings.txt"
VANILLA_PMS = ROOT / "vanilla_parsed/common/pms.json"
VANILLA_BUILDINGS = ROOT / "vanilla_parsed/common/buildings.json"
VANILLA_SCRIPT_VALUES = ROOT / "vanilla_parsed/common/script_values.json"
AI_DOC = ROOT / "docs/systems/mod_systems/ai.md"
PLAYTEST = ROOT / "docs/testing/ai-economy-playtest.md"


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


def _constant(name):
    m = re.search(rf"(?m)^{name} = (\S+)$", _code(VALUES))
    if m is None:
        raise KeyError(name)
    return float(m.group(1))


def _vanilla(path, key):
    value = json.loads(path.read_text(encoding="utf-8"))[key]
    return value[1] if isinstance(value, list) and value and value[0] == "=" else value


def _unwrap(node):
    return node[1] if isinstance(node, list) and len(node) == 2 and node[0] == "=" else node


def _pm_output(pm, good):
    """`goods_output_<good>_add` (workforce_scaled) of a method, the mod's REPLACE if it has one, else vanilla's."""
    code = _code(EXTRA_PMS)
    if re.search(rf"(?m)^REPLACE:{re.escape(pm)} = \{{", code):
        body = _block(code, f"REPLACE:{pm}")
    elif re.search(rf"(?m)^{re.escape(pm)} = \{{", code):
        body = _block(code, pm)
    else:
        mods = _unwrap(_unwrap(_vanilla(VANILLA_PMS, pm))["building_modifiers"])
        return float(_unwrap(_unwrap(mods["workforce_scaled"])[f"goods_output_{good}_add"]))
    m = re.search(rf"goods_output_{good}_add = (\S+)", body)
    return float(m.group(1))


def _pm_tech(pm):
    code = _code(EXTRA_PMS)
    for name in (f"REPLACE:{pm}", pm):
        try:
            body = _block(code, name)
        except KeyError:
            continue
        m = re.search(r"unlocking_technologies = \{\s*(\w+)\s*\}", body)
        return m.group(1) if m else None
    techs = _unwrap(_vanilla(VANILLA_PMS, pm).get("unlocking_technologies", ["=", []]))
    return techs[0] if techs else None


class Files(unittest.TestCase):
    def test_one_bom_and_tabs(self):
        for path in FILES:
            raw = path.read_bytes()
            with self.subTest(path=path.name):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))
                for line in raw.decode("utf-8-sig").splitlines():
                    self.assertFalse(line.startswith(" "), line)

    def test_braces_balance(self):
        for path in FILES:
            code = _code(path)
            with self.subTest(path=path.name):
                self.assertEqual(code.count("{"), code.count("}"))


class Figures(unittest.TestCase):
    """The numbers the pass sizes a plant by are the methods' own."""

    def test_light_input_is_the_electric_lights_input(self):
        mods = _unwrap(_unwrap(_vanilla(VANILLA_PMS, "pm_electric_streetlights"))["building_modifiers"])
        vanilla = float(_unwrap(_unwrap(mods["workforce_scaled"])["goods_input_electricity_add"]))
        self.assertNotRegex(_code(EXTRA_PMS), r"(?m)^(REPLACE|REPLACE_OR_CREATE):pm_electric_streetlights = ")
        self.assertEqual(_constant("TE_AI_POWER_LIGHT_INPUT"), vanilla)

    def test_level_output_ladder_matches_the_plant_methods(self):
        body = _norm(_block(_code(VALUES), "te_ai_power_level_output_value"))
        # pm_early_power_plant has no technology of its own: the building's (Electrical Generation) opens it.
        self.assertIsNone(_pm_tech("pm_early_power_plant"))
        self.assertIn("electrical_generation",
                      json.dumps(_vanilla(VANILLA_BUILDINGS, "building_power_plant")["unlocking_technologies"]))
        self.assertTrue(body.startswith(f"value = {int(_pm_output('pm_early_power_plant', 'electricity'))} "), body)
        for pm in ("pm_coal-fired_plant", "pm_modern_coal-fired_plant"):
            tech, out = _pm_tech(pm), int(_pm_output(pm, "electricity"))
            with self.subTest(pm=pm):
                self.assertIn(f"limit = {{ has_technology_researched = {tech} }} value = {out} }}", body)

    def test_oil_methods_make_at_least_coals(self):
        # Reading coal's figure where oil runs must size large, never short.
        self.assertGreaterEqual(_pm_output("pm_oil-fired_plant", "electricity"),
                                _pm_output("pm_coal-fired_plant", "electricity"))
        self.assertGreaterEqual(_pm_output("pm_modern_oil-fired_plant", "electricity"),
                                _pm_output("pm_modern_coal-fired_plant", "electricity"))

    def test_plant_group_is_most_productive(self):
        # The ladder assumes the AI runs the plant's highest-output method.
        body = _norm(_block(_code(EXTRA_PM_GROUPS), "INJECT:pmg_base_building_power_plant"))
        self.assertIn("ai_selection = most_productive", body)

    def test_level_cost_in_the_batch_comment(self):
        # TE_AI_POWER_MAX_BATCH's comment prices a level at 400 points: the plant's construction_cost_medium.
        self.assertIn("construction_cost_medium",
                      json.dumps(_vanilla(VANILLA_BUILDINGS, "building_power_plant")["required_construction"]))
        self.assertEqual(float(_unwrap(_vanilla(VANILLA_SCRIPT_VALUES, "construction_cost_medium"))), 400)
        self.assertIn("A level is 400 points (construction_cost_medium)", VALUES.read_text(encoding="utf-8-sig"))
        self.assertGreaterEqual(_constant("TE_AI_POWER_MAX_BATCH"), 1)


class Gates(unittest.TestCase):
    """The pass queues only what the building's own gates allow, and only where it is short."""

    def test_site_copies_the_plants_gates(self):
        site = _norm(_block(_code(TRIGGERS), "te_ai_power_pass_site"))
        # Vanilla's possible: the owner has no law banning industry. The mod's INJECT leaves it alone.
        possible = _norm(json.dumps(_vanilla(VANILLA_BUILDINGS, "building_power_plant")["possible"]))
        self.assertIn("law_type:law_industry_banned", possible)
        self.assertNotIn("possible", _block(_code(EXTRA_BUILDINGS), "INJECT:building_power_plant"))
        self.assertIn("owner = { NOT = { has_law_or_variant = law_type:law_industry_banned } }", site)
        # And the state allows industry at all (the 2026-11-21/22 test arms' seed passes asked the same).
        self.assertIn("is_industrial_production_allowed = yes", site)
        government = _norm(_block(_block(_code(EXTRA_BUILDINGS), "INJECT:building_power_plant"),
                                  "\tcan_build_government"))
        self.assertIn("rt_fossil_construction_allowed_here = yes", government)
        self.assertIn("rt_fossil_construction_allowed_here = yes", site)
        self.assertIn("te_ai_power_levels_wanted >= 1", site)
        self.assertIn("NOT = { has_variable = te_ai_power_pending }", site)
        # No second batch on top of plant levels still queued there (a batch given up on, an investor's).
        self.assertIn("NOT = { any_scope_building = { is_building_type = building_power_plant OR = { "
                      "is_under_construction = yes te_construction_market_building_queued_levels > 0 } } }", site)

    def test_country_gate(self):
        gate = _norm(_block(_code(TRIGGERS), "te_ai_power_pass_may_queue"))
        for line in ("is_ai = yes", "has_technology_researched = electrical_generation", "in_default = no",
                     "is_construction_paused = no", "construction_queue_government_duration < 52",
                     "te_ai_power_pending_count < TE_AI_POWER_MAX_PENDING",
                     "NOT = { is_country_type = decentralized }"):
            with self.subTest(line=line):
                self.assertIn(line, gate)

    def test_short_counts_the_lights(self):
        short = _norm(_block(_code(VALUES), "te_ai_power_short"))
        self.assertEqual(short, "value = te_grid_electricity_consumption add = te_ai_power_light_need "
                                "subtract = te_ai_power_supply min = 0")
        # What it can count on is its plants' capacity, or what is made there if more.
        supply = _norm(_block(_code(VALUES), "te_ai_power_supply"))
        self.assertEqual(supply, "value = te_grid_electricity_production if = { limit = { te_ai_power_plant_capacity > "
                                 "te_grid_electricity_production } value = te_ai_power_plant_capacity }")

    def test_electric_lights_only(self):
        effects = _code(EFFECTS)
        self.assertEqual(re.findall(r"production_method = (\w+)", effects), ["pm_electric_streetlights"])
        unswitched = _norm(_block(_code(TRIGGERS), "te_ai_power_lights_unswitched"))
        self.assertIn("pm_no_street_lighting", unswitched)
        self.assertIn("pm_gas_streetlights", unswitched)

    def test_lights_need_the_method_open(self):
        site = _norm(_block(_code(TRIGGERS), "te_ai_power_light_site"))
        self.assertIn("can_activate_production_method = { building_type = building_urban_center "
                      "production_method = pm_electric_streetlights }", site)
        self.assertIn("te_ai_power_spare >= te_ai_power_switch_threshold", site)
        self.assertIn("NOT = { has_variable = te_ai_power_revert_wait }", site)

    def test_a_revert_waits(self):
        effect = _norm(_block(_code(EFFECTS), "te_ai_power_pass_effect"))
        self.assertIn("remove_variable = te_ai_power_lit remove_variable = te_ai_power_lit_looked set_variable = { name = te_ai_power_revert_wait value = yes "
                      "days = 180 }", effect)


class Hooks(unittest.TestCase):
    def test_monthly_for_ai(self):
        code = _norm(_code(ON_ACTIONS))
        self.assertIn("on_monthly_pulse_country = { on_actions = { te_ai_power_pass_on_action } }", code)
        self.assertIn("te_ai_power_pass_on_action = { trigger = { is_ai = yes } effect = { te_ai_power_pass_effect = yes } }",
                      code)

    def test_queue_is_government_construction_of_the_plant(self):
        batch = _norm(_block(_code(EFFECTS), "te_ai_power_queue_batch"))
        self.assertIn("start_building_construction = building_power_plant", batch)
        self.assertNotIn("create_building", _code(EFFECTS))

    def test_one_state_a_month_shortest_first(self):
        effect = _norm(_block(_code(EFFECTS), "te_ai_power_pass_effect"))
        self.assertIn("ordered_scope_state = { limit = { te_ai_power_pass_site = yes } order_by = te_ai_power_short "
                      "min = 0 max = 1 check_range_bounds = no te_ai_power_queue_batch = yes }", effect)
        # The output per level is stored before any state reads it.
        self.assertLess(effect.index("set_variable = { name = te_ai_power_level_output"),
                        effect.index("every_scope_state"))

    def test_counters_start_at_zero(self):
        body = _norm(_block(_code(EFFECTS), "te_ai_power_count"))
        self.assertIn("NOT = { has_global_variable = $NAME$ } } set_global_variable = { name = $NAME$ value = 0 }", body)
        for name in re.findall(r"NAME = (\w+)", _code(EFFECTS)):
            with self.subTest(counter=name):
                self.assertIn(name.replace("te_ai_power_g_", "te_ai_power_") + "_g = {", _code(VALUES))


class SelfChecks(unittest.TestCase):
    def test_lights_check_reads_each_switch_at_its_first_look(self):
        effect = _norm(_block(_code(EFFECTS), "te_ai_power_pass_effect"))
        self.assertIn("if = { limit = { NOT = { has_variable = te_ai_power_lit_looked } } set_variable = "
                      "te_ai_power_lit_looked te_ai_power_count = { NAME = te_ai_power_g_looked ADD = 1 } if = { limit = "
                      "{ te_ai_power_lights_unswitched = yes } te_ai_power_count = { NAME = te_ai_power_g_first_reverts "
                      "ADD = 1 } } }", effect)
        check = _norm(_block(_code(ON_ACTIONS), "te_ai_power_lights_selfcheck"))
        self.assertIn("te_ai_power_looked_g >= TE_AI_POWER_CHECK_LOOKS", check)
        share = _norm(_block(_code(VALUES), "te_ai_power_revert_share"))
        self.assertTrue(share.startswith("value = te_ai_power_first_reverts_g divide = { value = te_ai_power_looked_g"),
                        share)

    def test_build_check_reads_a_closed_cohort(self):
        batch = _norm(_block(_code(EFFECTS), "te_ai_power_queue_batch"))
        self.assertIn("if = { limit = { te_ai_power_cohort_g < TE_AI_POWER_COHORT } set_variable = te_ai_power_in_cohort",
                      batch)
        check = _norm(_block(_code(ON_ACTIONS), "te_ai_power_pass_selfcheck"))
        self.assertIn("te_ai_power_cohort_decided_g >= TE_AI_POWER_COHORT_READ", check)
        self.assertLessEqual(_constant("TE_AI_POWER_COHORT_READ"), _constant("TE_AI_POWER_COHORT"))
        share = _norm(_block(_code(VALUES), "te_ai_power_lost_share"))
        self.assertTrue(share.startswith("value = te_ai_power_cohort_lost_g "), share)

    def test_each_reads_once_with_a_start_line(self):
        code = _code(ON_ACTIONS)
        for name, flag in (("ai_power_pass", "te_ai_power_pass_checked"),
                           ("ai_power_lights", "te_ai_power_lights_checked")):
            with self.subTest(check=name):
                for verdict in ("START", "OK", "BROKEN", "NO_VERDICT"):
                    self.assertIn(f"TE_SELF_CHECK {verdict} {name} ", code)
                self.assertIn(f"NOT = {{ has_global_variable = {flag} }}", code)
                self.assertIn(f"set_global_variable = {flag}", code)

    def test_documented(self):
        doc = AI_DOC.read_text(encoding="utf-8")
        self.assertIn("## AI Electrification Pass", doc)
        playtest = PLAYTEST.read_text(encoding="utf-8")
        for name in ("ai_power_pass", "ai_power_lights"):
            with self.subTest(check=name):
                self.assertIn(name, playtest)


if __name__ == "__main__":
    unittest.main()
