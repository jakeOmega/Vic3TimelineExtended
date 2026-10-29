"""Space fleets (solar colonization slice 6, parts 6a to 6d): the generator's
output, the hand-written files' contract with it, and the rules a play test
can't see in one evening.

Design: docs/superpowers/archive/specs/2026-10-26-solar-colonization-fleets-design.md.
The legs are tested in test_launch_windows.py (FleetLegsTest), the panel's
labels in test_space_race_labels.py and its figures in
test_space_race_layout.py.

Run: python3 -m unittest test_space_fleets -v
"""

import math
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import gen_solar_sites as gss  # noqa: E402
import gen_space_fleets as gsf  # noqa: E402

FLEET_EFFECTS = ROOT / "common/scripted_effects/sr_fleet_effects.txt"
COMBAT_EFFECTS = ROOT / "common/scripted_effects/sr_fleet_combat_effects.txt"
FLEET_VALUES = ROOT / "common/script_values/sr_fleet_values.txt"
FLEET_TRIGGERS = ROOT / "common/scripted_triggers/sr_fleet_triggers.txt"
SGUIS = ROOT / "common/scripted_guis/sr_fleet_sguis.txt"
BUILDING = ROOT / "common/buildings/sr_space_command.txt"
METHODS = ROOT / "common/production_methods/sr_space_command_pms.txt"
STATIC = ROOT / "common/static_modifiers/space_race_modifiers.txt"
SITE_EFFECTS = ROOT / "common/scripted_effects/sr_site_effects.txt"
SPACE_RACE_EFFECTS = ROOT / "common/scripted_effects/space_race_effects.txt"
ON_ACTIONS = ROOT / "common/on_actions/space_race_on_actions.txt"
COVERT_ACTIONS = ROOT / "common/diplomatic_actions/covert_operations.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_space_race_events.txt"
CEDE_COLONY = ROOT / "common/treaty_articles/124_cede_colony.txt"
SPACE_RACE_EVENTS = ROOT / "events/space_race_events.txt"
EARTH_EFFECTS = ROOT / "common/scripted_effects/sr_earth_orbit_effects.txt"
BATTERY = ROOT / "common/buildings/sr_orbital_defense_battery.txt"
BATTERY_METHODS = ROOT / "common/production_methods/sr_orbital_defense_battery_pms.txt"
MODIFIER_TYPES = ROOT / "common/modifier_type_definitions/sr_fleet_modifier_types.txt"
DEBRIS_EFFECTS = ROOT / "common/scripted_effects/te_orbital_debris_effects.txt"
COLONY_FLEET_EFFECTS = ROOT / "common/scripted_effects/sr_colony_fleet_effects.txt"
MODULE_EFFECTS = ROOT / "common/scripted_effects/sr_colony_module_effects.txt"
POPULATION_EFFECTS = ROOT / "common/scripted_effects/sr_colony_population_effects.txt"


def _raw(path):
    return Path(path).read_text(encoding="utf-8-sig")


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{", text)
    assert m, f"no block {name}"
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"unclosed {name}")


def _number(text, name):
    return float(re.search(rf"(?m)^{name} = \{{ value = ([\d.]+) \}}", text).group(1))


class GeneratedFilesTest(unittest.TestCase):
    def test_generated_files_are_current(self):
        result = gsf.regenerate(dry_run=True)
        self.assertFalse(result["changed"],
                         f"stale: {result['changed_files']}; run python3 scripts/generators/gen_space_fleets.py")

    def test_one_bom_and_the_auto_generated_header(self):
        for rel in gsf.plan_outputs():
            data = (gsf.ROOT / rel).read_bytes()
            with self.subTest(file=str(rel)):
                self.assertTrue(data.startswith(b"\xef\xbb\xbf# AUTO-GENERATED"))
                self.assertFalse(data[3:].startswith(b"\xef\xbb\xbf"))


class DebugLineTest(unittest.TestCase):
    """No $PARAM$ inside a debug_log string: the engine mangles it
    (scripting_best_practices.md, "No $PARAM$ inside the string")."""

    def test_no_parameter_inside_a_debug_line(self):
        for path in (FLEET_EFFECTS, COMBAT_EFFECTS, gsf.ROOT / gsf.EFFECTS_OUT, DEBUG_EVENTS):
            for line in re.findall(r'debug_log = "([^"]*)"', _raw(path)):
                with self.subTest(file=path.name, line=line[:60]):
                    self.assertNotIn("$", line)


class SlotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT))
        cls.hand = _strip(_raw(FLEET_EFFECTS)) + _strip(_raw(COMBAT_EFFECTS))

    def test_every_slot_action_is_defined(self):
        for action in gsf.SLOT_ACTIONS:
            with self.subTest(action=action):
                self.assertRegex(self.generated + self.hand, rf"(?m)^sr_fl_{action}_at = \{{")

    def test_every_dispatcher_reaches_every_slot(self):
        for dispatcher in ("sr_fl_each_slot", "sr_fl_by_op", "sr_fl_by_local"):
            with self.subTest(dispatcher=dispatcher):
                body = _block(self.generated, dispatcher)
                for n in range(1, gsf.SLOTS + 1):
                    self.assertIn(f"sr_fl_$DO$_at = {{ N = {n} }}", body)

    def test_every_do_a_caller_passes_is_an_action(self):
        texts = self.generated + self.hand + _strip(_raw(SGUIS)) + _strip(_raw(DEBUG_EVENTS))
        for do in set(re.findall(r"sr_fl_(?:each_slot|by_op|by_local) = \{ DO = (\w+) \}", texts)):
            with self.subTest(do=do):
                self.assertIn(do, gsf.SLOT_ACTIONS)

    def test_a_cleared_slot_clears_every_variable(self):
        clear = _block(self.generated, "sr_fl_clear_at")
        for name in (*gsf.SLOT_VARS, *[r.key for r in gsf.ROLES], *[f"{r.key}_full" for r in gsf.ROLES]):
            with self.subTest(var=name):
                self.assertIn(f"sr_fl_$N$_{name}", clear)


class RolesTest(unittest.TestCase):
    def test_the_roles_figures_are_the_values_file_s(self):
        values = _raw(FLEET_VALUES)
        for role in gsf.ROLES:
            with self.subTest(role=role.key):
                self.assertEqual(_number(values, f"sr_fl_fire_fleets_{role.key}"), role.fire_fleets)
                self.assertEqual(_number(values, f"sr_fl_fire_defences_{role.key}"), role.fire_defences)
                self.assertEqual(_number(values, f"sr_fl_endurance_{role.key}"), role.endurance)
        self.assertEqual(_number(values, "sr_fl_marines_per_carrier"),
                         next(r.marines for r in gsf.ROLES if r.key == "carrier"))

    def test_screens_take_the_losses_first(self):
        """A month's loss falls on the screens up to their strength, the rest on
        the screened roles, each role by its share of its group (§ 3, F10)."""
        body = _block(_strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT)), "sr_fl_take_losses_at")
        self.assertIn("name = sr_fl_on_screens value = { value = local_var:sr_fl_loss max = local_var:sr_fl_screens }", body)
        self.assertIn("name = sr_fl_on_screened value = { value = local_var:sr_fl_loss subtract = local_var:sr_fl_on_screens",
                      body)
        for role in gsf.ROLES:
            group = "screens" if role.screen else "screened"
            with self.subTest(role=role.key):
                self.assertRegex(body, rf"value = local_var:sr_fl_on_{group} multiply = sr_fl_\$N\$_{role.key}_value "
                                       rf"divide = local_var:sr_fl_{group} max = sr_fl_\$N\$_{role.key}_value \}} \}}"
                                       rf"\s*sr_fl_cut_role = \{{ N = \$N\$ ROLE = {role.key} \}}")


class RoleConceptTest(unittest.TestCase):
    """One short concept per ship role (the owner, 2026-10-27), holding the
    role's figures from the table; the ship role concept lists them all and
    each build-mix button names its own."""

    CONCEPT = {"war": "warship", "rapid": "rapid", "siege": "siege", "carrier": "carrier", "tender": "tender"}

    @staticmethod
    def _loc(key):
        for path in (ROOT / "localization/english").glob("*.yml"):
            m = re.search(rf'^ {re.escape(key)}:\d* "(.*)"\s*$', path.read_text(encoding="utf-8-sig"), re.M)
            if m:
                return m.group(1)
        raise AssertionError(f"no loc {key}")

    @staticmethod
    def _fig(x):
        return f"#v {x:g}#!"

    def test_each_role_has_its_concept_with_its_figures(self):
        concepts = _raw(ROOT / "common/game_concepts/extra_concepts.txt")
        ship_role = self._loc("concept_sr_ship_role_desc")
        for role in gsf.ROLES:
            key = f"concept_sr_role_{self.CONCEPT[role.key]}"
            with self.subTest(role=role.key):
                self.assertRegex(concepts, rf"(?m)^{key} = \{{\}}$")
                self._loc(key)
                desc = self._loc(f"{key}_desc")
                for figure in (role.fire_fleets, role.fire_defences, role.endurance):
                    self.assertIn(self._fig(figure), desc)
                if role.marines:
                    self.assertIn(self._fig(role.marines), desc)
                self.assertIn(f"[{key}]", ship_role)
                self.assertIn(f"[{key}]", self._loc(f"sr_sc_mix_step_{role.key}_tt"))


class FullColoniesGateTest(unittest.TestCase):
    """Everything here runs and shows under Full Colonies only."""

    def test_the_monthly_steps(self):
        self.assertRegex(_strip(_raw(SITE_EFFECTS)),
                         r"limit = \{ sr_colonies_full_enabled = yes \}\s*sr_fl_global_month = yes")
        self.assertIn("sr_colonies_full_enabled = yes", _block(_strip(_raw(FLEET_TRIGGERS)), "sr_fleet_power"))
        self.assertRegex(_strip(_raw(ON_ACTIONS)),
                         r"limit = \{ sr_fleet_power = yes \}\s*sr_fl_country_month = yes")

    def test_the_building(self):
        building = _block(_strip(_raw(BUILDING)), "building_space_command")
        self.assertIn("sr_colonies_full_enabled = yes", _block("x = {" + building.split("potential = {", 1)[1], "x"))

    def test_every_scripted_gui_and_the_survey(self):
        sguis = _strip(_raw(SGUIS))
        names = re.findall(r"(?m)^(sr_\w+_sgui) = \{", sguis)
        self.assertEqual(len(names), 12)
        for name in names:
            with self.subTest(sgui=name):
                self.assertIn("sr_colonies_full_enabled = yes", _block(sguis, name))
        survey = _block(_strip(_raw(COVERT_ACTIONS)), "covert_survey_defences_action")
        self.assertIn("sr_colonies_full_enabled = yes", survey.split("possible = {", 1)[0])


class OccupiedStateTest(unittest.TestCase):
    """§ 5.1: a building in a state its owner doesn't control counts for no one."""

    def test_construction_counts_only_states_held_by_their_owner(self):
        rate = _block(_strip(_raw(FLEET_VALUES)), "sr_sc_rate")
        self.assertRegex(rate, r"every_scope_state = \{\s*limit = \{ sr_state_held_by_owner = yes \}\s*"
                               r"add = modifier:state_sr_ship_construction_add")

    def test_the_battlestation_fights_only_from_a_held_state(self):
        gather = _block(_strip(_raw(COMBAT_EFFECTS)), "sr_cb_battlestation_gather")
        self.assertIn("sr_battlestation_held = yes", gather)
        self.assertIn("sr_state_held_by_owner = yes", _block(_strip(_raw(FLEET_TRIGGERS)), "sr_battlestation_held"))


class UpkeepTest(unittest.TestCase):
    def test_the_goods_upkeep_covers_every_input_of_every_method(self):
        inputs = set(re.findall(r"goods_input_(\w+)_add = ", _raw(METHODS)))
        upkeep = set(re.findall(r"goods_input_(\w+)_mult = 0\.01", _block(_raw(STATIC), "sr_fleet_upkeep_goods")))
        self.assertEqual(inputs, upkeep)
        self.assertEqual(inputs, {"launch_capacity", "advanced_materials", "electricity"})

    def test_the_upkeep_is_on_the_building_and_refreshed_once(self):
        apply = _block(_strip(_raw(FLEET_EFFECTS)), "sr_fl_upkeep_apply")
        self.assertIn("is_building_type = building_space_command", apply)
        self.assertLess(apply.index("remove_modifier = sr_fleet_upkeep_goods"), apply.index("add_modifier"))
        calls = re.findall(r"sr_fl_upkeep_apply = yes", _strip(_raw(FLEET_EFFECTS)))
        self.assertEqual(len(calls), 1)


class ShippingTest(unittest.TestCase):
    """gss.SHIPPING, re-derived from the specializations' modifiers: goods and
    throughput terms outnumbering research terms, a tie to the first term."""

    GOODS = re.compile(r"building_\w*throughput_add|goods_output_\w+_mult")
    RESEARCH = re.compile(r"country_tech_research_speed_mult|country_military_tech_research_speed_mult"
                          r"|country_weekly_innovation_max_add")

    def _ships(self, text, name):
        keys = re.findall(r"(?m)^\s*(\w+) =", _block(text, name))
        terms = [k for k in keys if self.GOODS.fullmatch(k) or self.RESEARCH.fullmatch(k)]
        goods = sum(1 for k in terms if self.GOODS.fullmatch(k))
        if goods != len(terms) - goods:
            return goods > len(terms) - goods
        return bool(terms) and bool(self.GOODS.fullmatch(terms[0]))

    def test_the_table_follows_the_rule(self):
        text = _raw(STATIC)
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertEqual(tuple(self._ships(text, m) for m in gss.spec_modifiers(site)), site.ships)

    def test_a_blockade_stops_a_shipping_specialization_only(self):
        values = _raw(gss.ROOT / gss.VALUES_OUT)
        for site in gss.SITES:
            for slot, ships in zip(("a", "b"), site.ships):
                with self.subTest(site=site.key, slot=slot):
                    body = _block(values, f"sr_site_mult_{slot}_{site.key}")
                    blockade = f"has_global_variable = sr_site_blockaded_{site.key} }} multiply = 0"
                    self.assertEqual(blockade in body, ships)


class CombatModelTest(unittest.TestCase):
    """The square law as the combat step applies it (§ 7.2), with the script's
    own k: each side loses k x the other side's fire a month."""

    @classmethod
    def setUpClass(cls):
        cls.k = _number(_raw(FLEET_VALUES), "sr_fleet_k")

    def _fight(self, a, b, fire=1.0, months=240):
        for _ in range(months):
            if a <= 0 or b <= 0:
                break
            a, b = max(0.0, a - self.k * b * fire), max(0.0, b - self.k * a * fire)
        return a, b

    def test_concentration_pays(self):
        a, b = self._fight(100.0, 50.0)
        self.assertEqual(b, 0.0)
        # The continuous law gives sqrt(100^2 - 50^2) = 86.6; monthly steps a few points less.
        self.assertAlmostEqual(a, math.sqrt(100 ** 2 - 50 ** 2), delta=5)

    def test_equal_fleets_destroy_each_other(self):
        minimum = _number(_raw(FLEET_VALUES), "sr_fl_minimum_strength")
        a, b = self._fight(100.0, 100.0)
        self.assertLess(max(a, b), minimum)

    def test_the_losses_formula_is_k_times_strength_times_fire_per_point(self):
        values = _strip(_raw(gsf.ROOT / gsf.VALUES_OUT)) + _strip(_raw(FLEET_VALUES))
        self.assertIn("sr_fleet_k", values)
        combat = _strip(_raw(COMBAT_EFFECTS))
        self.assertIn("multiply = sr_fleet_k", combat)


class CivilWarTest(unittest.TestCase):
    def test_the_winner_joins_the_fleet_powers_at_once(self):
        repair = _block(_strip(_raw(SPACE_RACE_EFFECTS)), "sr_repair_after_civil_war")
        self.assertRegex(repair, r"limit = \{ sr_fleet_power = yes \}\s*sr_fl_join_powers = yes")

    def test_the_winner_keeps_the_old_government_s_occupations(self):
        repoint = _block(_strip(_raw(gss.ROOT / gss.EFFECTS_OUT)), "sr_sites_repoint_loser")
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"set_global_variable = {{ name = sr_site_occupier_{site.key} value = ROOT }}", repoint)

    def test_the_winner_keeps_the_interdiction_records(self):
        """Variable lists don't pass to a revolution's winner: the casus belli
        list is carried over, and other powers' records that name the old
        government are repointed (6c)."""
        repair = _block(_strip(_raw(SPACE_RACE_EFFECTS)), "sr_repair_after_civil_war")
        self.assertIn("sr_icpt_repair_after_civil_war = yes", repair)
        body = _block(_strip(_raw(COMBAT_EFFECTS)), "sr_icpt_repair_after_civil_war")
        self.assertIn("exists = scope:te_cw_loser", body)
        self.assertIn("add_to_variable_list = { name = sr_interdiction_targets target = scope:sr_icpt_carried }", body)
        self.assertIn("add_to_variable_list = { name = sr_interdiction_targets target = ROOT }", body)
        self.assertIn("sr_fl_each_slot = { DO = icpt_repoint }", body)
        self.assertIn("set_variable = { name = sr_fl_$N$_icpt value = ROOT }",
                      _block(_strip(_raw(COMBAT_EFFECTS)), "sr_fl_icpt_repoint_at"))

    def test_a_release_clears_every_slice_6_record(self):
        effects = _strip(_raw(gss.ROOT / gss.EFFECTS_OUT))
        for site in gss.SITES:
            release = _block(effects, f"sr_site_release_{site.key}")
            for name in gss.slice6_vars(site):
                with self.subTest(site=site.key, var=name):
                    self.assertIn(name, release)


class InterdictionTest(unittest.TestCase):
    """6c (design § 12; owner, 2026-10-26): an explicit Interdict posture against
    one country at peace with us and not our ally, its price once per fleet and
    target, and a blockade that only it or an enemy standing off can make."""

    @classmethod
    def setUpClass(cls):
        cls.triggers = _strip(_raw(FLEET_TRIGGERS))
        cls.combat = _strip(_raw(COMBAT_EFFECTS))
        cls.generated = _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT))
        cls.gen_triggers = _strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT))

    def test_only_a_country_at_peace_and_not_an_ally_may_be_interdicted(self):
        body = _block(self.triggers, "sr_site_interdict_target")
        for line in ("NOT = { has_global_variable = sr_site_free_$KEY$ }",
                     "NOT = { has_global_variable = sr_site_occupier_$KEY$ }",
                     "NOT = { has_global_variable = sr_site_ruined_$KEY$ }",
                     "NOT = { this = scope:sr_icpt_by }",
                     "NOT = { has_war_with = scope:sr_icpt_by }",
                     "NOT = { has_treaty_alliance_with = { TARGET = scope:sr_icpt_by } }",
                     "NOT = { has_treaty_defensive_pact_with = { TARGET = scope:sr_icpt_by } }"):
            with self.subTest(line=line):
                self.assertIn(line, body)

    def test_the_posture_steps_through_interdict_and_back_to_station(self):
        body = _block(self.combat, "sr_fl_step_posture_at")
        self.assertRegex(body, r"local_var:sr_cb_p <= 3\s*sr_fl_\$N\$_has_interdict_world = yes\s*\}\s*"
                               r"set_variable = \{ name = sr_fl_\$N\$_posture value = 4 \}")
        self.assertIn("sr_fl_charge_icpt_at = { N = $N$ }", body)
        # Leaving Interdict ends the interdiction's record.
        station = body[body.rindex("else = {"):]
        self.assertIn("value = 1", station)
        self.assertIn("remove_variable = sr_fl_$N$_icpt", station)
        self.assertTrue(body.rstrip().endswith("sr_icpt_rebuild = yes"))

    def test_interdict_fights_as_standing_off(self):
        for name in ("sr_fl_gather_at", "sr_fl_apply_losses_at"):
            with self.subTest(helper=name):
                self.assertRegex(_block(self.combat, name),
                                 r"limit = \{ local_var:sr_cb_p = 4 \}[^}]*\}?\s*"
                                 r"(?:sr_fl_check_icpt_at = \{ N = \$N\$ \}\s*)?"
                                 r"set_local_variable = \{ name = sr_cb_p value = 2 \}")

    def test_the_price_is_charged_once_per_fleet_and_target(self):
        body = _block(self.combat, "sr_cb_charge_interdict")
        self.assertIn("NOT = { var:sr_fl_$N$_icpt = scope:sr_icpt_target }", body)
        self.assertIn("set_variable = { name = sr_fl_$N$_icpt value = scope:sr_icpt_target }", body)
        self.assertIn("change_infamy = sr_interdiction_infamy", body)
        self.assertIn("un_dossier_record = { RECORD = space POINTS = sr_interdiction_dossier }", body)
        self.assertIn("set_variable = { name = sr_interdiction_recent value = yes days = 1825 }", body)
        self.assertIn("trigger_event = { id = space_race_events.105 days = 1 }", body)
        values = _raw(FLEET_VALUES)
        self.assertEqual(_number(values, "sr_interdiction_infamy"), 5)
        self.assertEqual(_number(values, "sr_interdiction_dossier"), 10)

    def test_the_lists_hold_only_interdicting_slots_at_their_own_location(self):
        body = _block(self.generated, "sr_icpt_rebuild")
        for lc in gsf.LOCATIONS[1:]:
            with self.subTest(loc=lc.key):
                self.assertIn(f"clear_variable_list = sr_icpt_{lc.key}", body)
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                self.assertIn(f"limit = {{ has_variable = sr_fl_{n}_loc has_variable = sr_fl_{n}_target "
                              f"sr_fl_{n}_posture_value = 4 }}", body)
        for site in gss.SITES:
            with self.subTest(site=site.key):
                note = f"sr_icpt_note = {{ KEY = {site.key} LOC = {site.location} }}"
                if site.location == "earth":
                    # no interdiction at Earth (lunar colonization § 8.3): posture 4 can't
                    # exist there, and no sr_icpt_earth list is built
                    self.assertNotIn(note, body)
                    continue
                self.assertIn(f"var:sr_fl_1_loc = {gsf.CODE[site.location]} var:sr_fl_1_target = {site.index} }}\n"
                              f"\t\t\t{note}", body)
        # Rebuilt with the location records, on each order and when one ends.
        self.assertIn("sr_icpt_rebuild = yes", _block(_strip(_raw(FLEET_EFFECTS)), "sr_loc_rebuild"))
        self.assertIn("sr_icpt_rebuild = yes", _block(self.combat, "sr_fl_end_icpt"))
        self.assertIn("sr_icpt_rebuild = yes", _block(self.generated, "sr_fl_step_target_at"))

    def test_a_blockade_needs_an_enemy_or_an_interdiction_and_no_holder_fleet(self):
        body = _block(self.combat, "sr_site_blockade_step")
        self.assertIn("NOT = { sr_cb_holds_orbit = yes }", body)
        self.assertRegex(body, r"OR = \{\s*has_war_with = prev\s*sr_icpt_interdicts_at = \{ LOC = \$LOC\$ \}\s*\}")
        for lc in gsf.LOCATIONS[1:]:
            for site in gsf.worlds_at(lc.key):
                with self.subTest(site=site.key):
                    self.assertIn(f"sr_site_blockade_step = {{ KEY = {site.key} LOC = {lc.key} }}",
                                  _block(self.generated, f"sr_cb_worlds_after_{lc.key}"))

    def test_a_departure_ends_the_interdiction(self):
        self.assertIn("remove_variable = sr_fl_$N$_icpt", _block(_strip(_raw(FLEET_EFFECTS)), "sr_fl_dispatch"))
        self.assertIn("icpt", gsf.SLOT_VARS)

    def test_the_ai_never_interdicts(self):
        """No AI order sets Interdict: only the posture step and the console do,
        and the AI calls neither (design § 14)."""
        texts = {"hand": self.combat + _strip(_raw(FLEET_EFFECTS)), "generated": self.generated}
        for label, text in texts.items():
            with self.subTest(file=label):
                setters = [m.start() for m in re.finditer(r"_posture value = 4 \}", text)]
                owners = {re.findall(r"(?m)^(\w+) = \{", text[:i])[-1] for i in setters}
                self.assertLessEqual(owners, {"sr_fl_step_posture_at", "sr_fl_debug_icpt_at"})
        ai = ""
        for text in (self.generated, self.combat, _strip(_raw(FLEET_EFFECTS))):
            names = re.findall(r"(?m)^(sr_fl_ai_\w+) = \{", text)
            self.assertTrue(names)
            ai += "".join(_block(text, name) for name in names)
        self.assertNotIn("step_posture", ai)
        self.assertNotIn("interdict", ai)

    def test_cede_colony_costs_no_infamy_against_an_interdictor(self):
        wargoal = _block("x = {" + _strip(_raw(CEDE_COLONY)).split("wargoal = {", 1)[1], "x")
        infamy = _block("x = {" + wargoal.split("infamy = {", 1)[1], "x")
        self.assertRegex(infamy, r"scope:target_country \?= \{ sr_interdicted_recently = \{ TARGET = root \} \}"
                                 r"\s*\}\s*multiply = \{\s*desc = \"INFAMY_SR_INTERDICTOR\"\s*value = 0")
        recently = _block(self.triggers, "sr_interdicted_recently")
        self.assertIn("has_variable = sr_interdiction_recent", recently)
        self.assertIn("is_target_in_variable_list = { name = sr_interdiction_targets target = $TARGET$ }", recently)

    def test_the_target_is_told(self):
        event = _block(_strip(_raw(SPACE_RACE_EVENTS)), "space_race_events.105")
        self.assertIn("trigger = { has_variable = sr_icpt_alert_loc }", event)
        self.assertIn("event_image", event)
        self.assertIn("remove_variable = sr_icpt_alert_loc", event)


class AiOffenceTest(unittest.TestCase):
    """6c (design § 14): the AI attacks at war, through the checks a player's
    orders pass, never destroying, never taking a free colony, never
    interdicting; an interdiction of its colonies is a threat it answers."""

    @classmethod
    def setUpClass(cls):
        cls.generated = _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT))
        cls.gen_triggers = _strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT))
        cls.combat = _strip(_raw(COMBAT_EFFECTS))
        cls.triggers = _strip(_raw(FLEET_TRIGGERS))

    def test_it_attacks_only_at_war_after_the_defence(self):
        # At war: the lunar step at Earth (lunar colonization § 8.4), then the
        # dispatch, then each slot's assault.
        self.assertRegex(_block(self.combat, "sr_fl_ai_attack"),
                         r"limit = \{ is_at_war = yes \}\s*sr_fl_ai_lunar_assault = yes\s*sr_fl_ai_attack_all = yes\s*"
                         r"sr_fl_each_slot = \{ DO = ai_assault \}")
        review = _block(_strip(_raw(FLEET_EFFECTS)), "sr_fl_ai_review")
        self.assertLess(review.index("sr_fl_ai_defend = yes"), review.index("sr_fl_ai_attack = yes"))

    def test_every_attack_order_passes_a_player_s_checks_and_can_come_home(self):
        attack = _block(self.generated, "sr_fl_ai_attack_all")
        for lc in gsf.LOCATIONS[1:]:
            for n in range(1, gsf.SLOTS + 1):
                with self.subTest(loc=lc.key, slot=n):
                    self.assertIn(f"sr_fl_{n}_ai_free = yes sr_fl_{n}_ai_attacks_{lc.key} = yes", attack)
                    body = _block(self.gen_triggers, f"sr_fl_{n}_ai_attacks_{lc.key}")
                    for line in (f"sr_fl_{n}_docked = yes", f"sr_fl_{n}_may_depart_{lc.key} = yes",
                                 f"sr_fl_{n}_leg_months_{lc.key} <= sr_fl_ai_attack_months",
                                 f"sr_loc_port_{lc.key} = yes",
                                 f"sr_fl_{n}_dv_value >= {{ value = sr_fl_{n}_leg_dv_{lc.key} add = sr_fl_{n}_return_dv_{lc.key} }}",
                                 f"sr_fl_{n}_strength >= {{ value = sr_loc_ai_enemy_force_{lc.key} multiply = sr_fl_ai_attack_margin }}"):
                        self.assertIn(line, body)
        # One order a month at most.
        self.assertEqual(attack.count("set_local_variable = { name = sr_fl_ai_sent value = 1 }"),
                         (len(gsf.LOCATIONS) - 1) * gsf.SLOTS)
        self.assertEqual(attack.count("limit = { local_var:sr_fl_ai_sent = 0 "), len(gsf.LOCATIONS) - 1)
        values = _raw(FLEET_VALUES)
        self.assertEqual(_number(values, "sr_fl_ai_attack_months"), 12)
        self.assertEqual(_number(values, "sr_fl_ai_attack_margin"), 1.5)

    def test_it_never_destroys_or_takes_a_free_colony(self):
        target = _block(self.triggers, "sr_site_ai_attack_target")
        self.assertIn("sr_site_hostile_target = { KEY = $KEY$ }", target)
        self.assertIn("NOT = { has_global_variable = sr_site_free_$KEY$ }", target)
        assault = _block(self.generated, "sr_fl_ai_assault_at")
        self.assertIn("remove_variable = sr_fl_$N$_destroy", assault)
        self.assertNotIn("set_variable = { name = sr_fl_$N$_destroy", assault)
        self.assertNotIn("sr_site_hostile_target", assault)
        for site in gss.SITES:
            with self.subTest(site=site.key):
                # A slot's assault skips Earth: the lunar worlds are the country-level
                # sr_fl_ai_lunar_assault's (lunar colonization § 8.4; LunarAtEarthTest)
                self.assertEqual(f"sr_site_ai_attack_target = {{ KEY = {site.key} }} sr_site_ai_worth_{site.key} > "
                                 "local_var:sr_ai_best" in assault, site.location != "earth")

    def test_it_closes_in_to_seize_only_with_the_marines_for_it(self):
        assault = _block(self.generated, "sr_fl_ai_assault_at")
        self.assertRegex(assault, r"limit = \{ sr_fl_\$N\$_marines_value > local_var:sr_ai_need \}\s*"
                                  r"set_variable = \{ name = sr_fl_\$N\$_posture value = 3 \}")
        self.assertRegex(assault, r"else = \{\s*set_variable = \{ name = sr_fl_\$N\$_posture value = 2 \}")

    def test_an_interdiction_of_its_colonies_is_a_threat(self):
        for lc in gsf.LOCATIONS[1:]:
            with self.subTest(loc=lc.key):
                body = _block(self.gen_triggers, f"sr_fl_ai_threatened_{lc.key}")
                self.assertIn("save_temporary_scope_as = sr_icpt_victim", body)
                self.assertIn(f"sr_icpt_interdicts_at = {{ LOC = {lc.key} }}", body)

    def test_a_fleet_attacking_and_holding_its_own_stays(self):
        home = _block(self.generated, "sr_fl_ai_home_at")
        for lc in gsf.LOCATIONS[1:]:
            with self.subTest(loc=lc.key):
                self.assertIn(f"NOT = {{ AND = {{ sr_loc_ai_target_{lc.key} = yes sr_fl_ai_holds_{lc.key} = yes }} }}", home)


class GroundReserveTest(unittest.TestCase):
    """6d (design § 15): Space Command builds into a reserve on the ground, which
    goes up together, by Launch at any time or by itself while no hostile fleet
    is at Earth; a blockade can't stop a Launch, an occupied launch site can."""

    @classmethod
    def setUpClass(cls):
        cls.fleet = _strip(_raw(FLEET_EFFECTS))
        cls.earth = _strip(_raw(EARTH_EFFECTS))
        cls.triggers = _strip(_raw(FLEET_TRIGGERS))
        cls.generated = _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT))
        cls.values = _strip(_raw(gsf.ROOT / gsf.VALUES_OUT))

    def test_construction_joins_the_reserve(self):
        month = _block(self.fleet, "sr_sc_month")
        self.assertRegex(month, r"limit = \{ local_var:sr_sc_points > 0 \}\s*sr_reserve_build = yes")
        self.assertTrue(month.rstrip().endswith("sr_reserve_auto_step = yes"))
        self.assertNotIn("sr_fl_find_home", month)
        build = _block(self.generated, "sr_reserve_build")
        for role in gsf.ROLES:
            with self.subTest(role=role.key):
                self.assertIn(f"multiply = sr_sc_mix_share_{role.key}", build)
                self.assertIn(f"change_variable = {{ name = sr_reserve_{role.key} add = local_var:sr_sc_share }}", build)
        total = _block(self.values, "sr_reserve_total")
        self.assertEqual(len(re.findall(r"add = sr_reserve_\w+_value", total)), len(gsf.ROLES))

    def test_a_launch_takes_the_whole_reserve(self):
        body = _block(self.generated, "sr_fl_reserve_in_at")
        for role in gsf.ROLES:
            with self.subTest(role=role.key):
                self.assertIn(f"sr_fl_add_role = {{ N = $N$ ROLE = {role.key} AMOUNT = var:sr_reserve_{role.key} }}", body)
                self.assertIn(f"remove_variable = sr_reserve_{role.key}", body)
        self.assertIn("sr_fl_fill_at = { N = $N$ }", body)

    def test_it_launches_itself_only_with_no_hostile_fleet_at_earth(self):
        auto = _block(self.earth, "sr_reserve_auto_step")
        for line in ("sr_reserve_auto_on = yes", "NOT = { sr_earth_hostile_present = yes }",
                     "NOT = { sr_launch_site_lost = yes }", "sr_fl_find_home = yes",
                     "sr_fl_by_local = { DO = reserve_in }"):
            with self.subTest(line=line):
                self.assertIn(line, auto)
        self.assertIn("NOT = { has_variable = sr_reserve_auto }", _block(self.triggers, "sr_reserve_auto_on"))

    def test_a_blockade_cannot_stop_a_launch(self):
        may = _block(self.triggers, "sr_reserve_may_launch")
        self.assertIn("NOT = { sr_launch_site_lost = yes }", may)
        self.assertNotIn("blockade", may)
        self.assertNotIn("sr_launches_barred", may)
        sgui = _block(_strip(_raw(SGUIS)), "sr_reserve_launch_sgui")
        self.assertIn("sr_reserve_may_launch = yes", sgui)
        self.assertIn("sr_reserve_launch = yes", sgui)

    def test_the_reserve_pays_upkeep_and_keeps_its_power_on_the_list(self):
        self.assertIn("add = sr_reserve_total", _block(_strip(_raw(FLEET_VALUES)), "sr_fleet_upkeep_units_value"))
        self.assertIn("sr_reserve_total > 0", _block(self.triggers, "sr_fleet_power"))

    def test_the_ai_launches_when_it_matches_the_enemy_at_earth(self):
        self.assertTrue(_block(self.fleet, "sr_fl_ai_review").strip().startswith("sr_fl_ai_reserve = yes"))
        ai = _block(self.earth, "sr_fl_ai_reserve")
        self.assertIn("sr_reserve_may_launch = yes", ai)
        self.assertIn("sr_fl_ai_reserve_matches = yes", ai)
        self.assertIn("sr_earth_reserve_and_ours >= sr_loc_ai_enemy_fleets_earth",
                      _block(self.triggers, "sr_fl_ai_reserve_matches"))
        self.assertIn("sr_loc_ai_enemy_fleets_earth = {", self.values)


class BatteryTest(unittest.TestCase):
    """6d (design § 15): ground-to-orbit batteries fire on hostile fleets at
    Earth, and Ground Lasers sweep the low debris pool in peace; both figures
    are state modifiers the script sums over the states the owner controls."""

    @classmethod
    def setUpClass(cls):
        cls.values = _strip(_raw(FLEET_VALUES))
        cls.methods = _strip(_raw(BATTERY_METHODS))
        cls.combat = _strip(_raw(COMBAT_EFFECTS))
        cls.earth = _strip(_raw(EARTH_EFFECTS))

    def test_the_building(self):
        building = _block(_strip(_raw(BATTERY)), "building_orbital_defense_battery")
        self.assertIn("sr_colonies_full_enabled = yes", _block("x = {" + building.split("potential = {", 1)[1], "x"))
        self.assertIn("space_militarization", _block("x = {" + building.split("unlocking_technologies = {", 1)[1], "x"))
        self.assertIn("owner ?= { sr_battery_may_build_government = yes }", building)
        self.assertIn("pmg_orbital_defense_battery", building)

    def test_each_method_carries_its_figures_as_state_modifiers_only(self):
        expected = {"pm_orbital_battery_kinetic": {"state_orbital_battery_fire_add": 1.0},
                    "pm_orbital_battery_lasers": {"state_orbital_battery_fire_add": 2.0,
                                                  "state_orbital_debris_sweep_add": 0.01}}
        for pm, figures in expected.items():
            body = _block(self.methods, pm)
            state = _block("x = {" + body.split("state_modifiers = {", 1)[1], "x")
            with self.subTest(pm=pm):
                self.assertIn("workforce_scaled", state)
                self.assertEqual({k: float(v) for k, v in re.findall(r"(state_orbital_\w+) = ([\d.]+)", state)}, figures)
                building = _block("x = {" + body.split("building_modifiers = {", 1)[1], "x")
                self.assertNotIn("orbital_battery", building)
                self.assertNotIn("debris", building)
        self.assertIn("directed_energy_weapons", _block(self.methods, "pm_orbital_battery_lasers"))
        self.assertIn("goods_input_electricity_add", _block(self.methods, "pm_orbital_battery_lasers"))

    def test_the_types_are_script_only_with_their_decimals(self):
        types = _strip(_raw(MODIFIER_TYPES))
        for name, decimals in (("state_orbital_battery_fire_add", 1), ("state_orbital_debris_sweep_add", 2)):
            body = _block(types, name)
            with self.subTest(type=name):
                self.assertIn("script_only = yes", body)
                self.assertIn(f"decimals = {decimals}", body)

    def test_fire_and_sweep_count_only_states_held_by_their_owner(self):
        for name, mod in (("sr_battery_fire", "state_orbital_battery_fire_add"),
                          ("sr_battery_fire_kinetic", "state_orbital_battery_fire_add"),
                          ("sr_battery_sweep", "state_orbital_debris_sweep_add")):
            body = _block(self.values, name)
            with self.subTest(value=name):
                self.assertRegex(body, r"every_scope_state = \{\s*limit = \{\s*sr_state_held_by_owner = yes")
                self.assertIn(f"add = modifier:{mod}", body)
        self.assertRegex(_block(self.values, "sr_battery_sweep"), r"limit = \{ is_at_war = no \}")
        # Nothing else reads the two types.
        for path in (FLEET_EFFECTS, COMBAT_EFFECTS, EARTH_EFFECTS, FLEET_TRIGGERS, gsf.ROOT / gsf.VALUES_OUT):
            with self.subTest(file=path.name):
                self.assertNotIn("modifier:state_orbital", _strip(_raw(path)))

    def test_batteries_fire_in_the_earth_battle_and_take_no_losses(self):
        at = _block(self.combat, "sr_combat_at")
        self.assertRegex(at, r"limit = \{ local_var:sr_cb_code = 1 \}\s*sr_cb_battlestation_gather = yes\s*"
                             r"sr_cb_battery_gather = yes")
        gather = _block(self.combat, "sr_cb_battery_gather")
        self.assertIn("sr_cb_add = { VAR = sr_cb_f1 AMOUNT = local_var:sr_cb_bf }", gather)
        self.assertNotIn("sr_cb_s1", gather)
        self.assertIn("set_variable = { name = sr_cb_kf value = sr_battery_fire_kinetic }", gather)
        self.assertIn("kf", gsf.CB_VARS)
        self.assertIn("te_debris_add = { LOW = local_var:sr_cb_debris_low HIGH = 0 }", at)
        self.assertEqual(_number(_raw(FLEET_VALUES), "sr_battery_debris_low"), 0.02)

    def test_the_sweep_takes_from_the_low_pool_alone_after_removal(self):
        monthly = _block(_strip(_raw(DEBRIS_EFFECTS)), "te_debris_global_monthly")
        self.assertLess(monthly.index("te_debris_removal_month"), monthly.index("sr_battery_sweep_step = yes"))
        self.assertLess(monthly.index("sr_battery_sweep_step = yes"), monthly.index("te_debris_clamp_pools = yes"))
        step = _block(self.earth, "sr_battery_sweep_step")
        self.assertIn("name = orbital_debris_low", step)
        self.assertNotRegex(step, r"name = orbital_debris_high\b")
        self.assertIn("every_in_global_list = {\n\t\t\tvariable = sr_fleet_powers", step)
        self.assertNotIn("every_country", step)
        self.assertIn("sr_has_battery = yes", _block(_strip(_raw(FLEET_TRIGGERS)), "sr_fleet_power"))


class EarthBlockadeTest(unittest.TestCase):
    """6d (design §§ 5.1, 15): a fleet at war with us at Earth and none of ours
    there, or an occupied launch site, stops every launch; Launch from the
    reserve reads only the occupation half, and so does fabrication."""

    @classmethod
    def setUpClass(cls):
        cls.triggers = _strip(_raw(FLEET_TRIGGERS))
        cls.gen_triggers = _strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT))
        cls.generated = _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT))

    def test_the_tests_are_full_colonies_only(self):
        for name in ("sr_earth_blockaded", "sr_launch_site_lost"):
            with self.subTest(trigger=name):
                self.assertIn("sr_colonies_full_enabled = yes", _block(self.triggers, name))
        barred = _block(self.triggers, "sr_launches_barred")
        self.assertIn("sr_earth_blockaded = yes", barred)
        self.assertIn("sr_launch_site_lost = yes", barred)
        blockaded = _block(self.triggers, "sr_earth_blockaded")
        self.assertIn("NOT = { has_variable = sr_fl_at_earth }", blockaded)
        self.assertIn("sr_earth_hostile_present = yes", blockaded)
        lost = _block(self.triggers, "sr_launch_site_lost")
        self.assertIn("is_building_type = building_space_program", lost)
        self.assertIn("state = { sr_state_held_by_owner = yes }", lost)

    def test_every_departure_reads_the_one_test(self):
        launch = _block(_strip(_raw(COLONY_FLEET_EFFECTS)), "sr_cf_launch_month")
        self.assertRegex(launch, r"^\s*if = \{\s*limit = \{ sr_launches_barred = yes \}\s*sr_launch_note_held = yes")
        step = _block(_strip(_raw(MODULE_EFFECTS)), "sr_ms_step_slot")
        self.assertRegex(step, r"limit = \{ NOT = \{ sr_launches_barred = yes \} \}\s*sr_ms_departure_by_index = yes")
        self.assertEqual(step.count("sr_ms_departure_by_index"), 1)
        emig = _block(_strip(_raw(POPULATION_EFFECTS)), "sr_emig_month")
        self.assertIn("NOT = { sr_launches_barred = yes }", _block("x = {" + emig.split("limit = {", 1)[1], "x"))
        for n in range(1, gsf.SLOTS + 1):
            for lc in gsf.LOCATIONS[1:]:
                with self.subTest(slot=n, loc=lc.key):
                    self.assertIn(f"NOT = {{ AND = {{ var:sr_fl_{n}_loc = 1 sr_launches_barred = yes }} }}",
                                  _block(self.gen_triggers, f"sr_fl_{n}_may_depart_{lc.key}"))

    def test_fabrication_and_the_reserve_read_only_the_occupation(self):
        month = _block(_strip(_raw(MODULE_EFFECTS)), "sr_mod_month")
        self.assertEqual(month.count("NOT = { sr_launch_site_lost = yes }"), 2)
        self.assertNotIn("sr_launches_barred", month)
        for name in ("sr_reserve_may_launch",):
            self.assertNotIn("sr_launches_barred", _block(self.triggers, name))

    def test_no_contact_while_earth_is_blockaded(self):
        arrival = _block(self.generated, "sr_fl_arrival_contact_at")
        self.assertTrue(arrival.strip().startswith("if = {\n\t\tlimit = { NOT = { sr_earth_blockaded = yes } }"))
        sites = _strip(_raw(gss.ROOT / gss.EFFECTS_OUT))
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertRegex(_block(sites, f"sr_mod_install_{site.key}"),
                                 r"limit = \{ NOT = \{ sr_earth_blockaded = yes \} \}\s*"
                                 rf"set_global_variable = \{{ name = sr_site_contact_{site.key} ")

    def test_players_are_told(self):
        on = _strip(_raw(ON_ACTIONS))
        self.assertRegex(on, r"is_player = yes\s*sr_colonies_full_enabled = yes[^}]*\{[^}]*\}[^}]*\}\s*sr_earth_notice_step = yes")
        step = _block(_strip(_raw(EARTH_EFFECTS)), "sr_earth_notice_step")
        self.assertIn("trigger_event = { id = space_race_events.106 days = 1 }", step)
        self.assertEqual(step.count("trigger_event = { id = space_race_events.108 days = 1 }"), 2)
        events = _strip(_raw(SPACE_RACE_EVENTS))
        for event, var in (("space_race_events.106", "sr_earth_blockade_by"), ("space_race_events.108", "sr_launch_site_kind")):
            body = _block(events, event)
            with self.subTest(event=event):
                self.assertIn("event_image", body)
                self.assertIn(f"trigger = {{ has_variable = {var} }}", body)
                self.assertIn(f"remove_variable = {var}", body)


class OrbitalSuperiorityTest(unittest.TestCase):
    """6d (design § 15): at war, holding Earth orbit gives +10% offense and +5%
    defense at the margin our fleets there hold, from one refresh site."""

    def test_the_modifier(self):
        body = _block(_strip(_raw(STATIC)), "sr_orbital_superiority")
        self.assertIn("unit_offense_mult = 0.1", body)
        self.assertIn("unit_defense_mult = 0.05", body)

    def test_the_margin(self):
        margin = _block(_strip(_raw(FLEET_VALUES)), "sr_orbital_superiority_margin")
        for line in ("limit = { has_variable = sr_fl_at_earth }", "value = var:sr_fl_at_earth",
                     "subtract = sr_loc_ai_enemy_fleets_earth", "min = sr_orbital_superiority_floor",
                     "max = 1", "min = 0"):
            with self.subTest(line=line):
                self.assertIn(line, margin)
        self.assertEqual(_number(_raw(FLEET_VALUES), "sr_orbital_superiority_floor"), 10)

    def test_one_refresh_site_removed_first_at_war_only(self):
        texts = {path.name: _strip(_raw(path)) for path in (FLEET_EFFECTS, COMBAT_EFFECTS, EARTH_EFFECTS, ON_ACTIONS)}
        adds = [name for name, text in texts.items() if "add_modifier = { name = sr_orbital_superiority" in text]
        self.assertEqual(adds, [EARTH_EFFECTS.name])
        refresh = _block(texts[EARTH_EFFECTS.name], "sr_orbital_superiority_refresh")
        self.assertLess(refresh.index("remove_modifier = sr_orbital_superiority"), refresh.index("add_modifier"))
        self.assertIn("is_at_war = yes", refresh)
        self.assertIn("multiplier = sr_orbital_superiority_margin", refresh)
        self.assertEqual(texts[FLEET_EFFECTS.name].count("sr_orbital_superiority_refresh = yes"), 1)
        # A country off the fleet powers list loses it.
        self.assertRegex(texts[ON_ACTIONS.name], r"sr_fl_country_month = yes\s*\}\s*else_if = \{\s*"
                                                 r"limit = \{ has_modifier = sr_orbital_superiority \}\s*"
                                                 r"remove_modifier = sr_orbital_superiority")


class EarthOrbitAiAndConsoleTest(unittest.TestCase):
    """6d (design § 14, § 18): the AI's batteries, and the console's options."""

    def test_the_ai_builds_batteries_only_at_war_with_a_fleet_power(self):
        triggers = _strip(_raw(FLEET_TRIGGERS))
        may = _block(triggers, "sr_battery_may_build_government")
        self.assertIn("is_ai = no", may)
        self.assertIn("sr_battery_ai_wants = yes", may)
        self.assertIn("sr_battery_queued_levels < sr_battery_ai_max_levels", may)
        wants = _block(triggers, "sr_battery_ai_wants")
        self.assertIn("is_at_war = yes", wants)
        self.assertIn("has_war_with = prev", wants)
        self.assertIn("sr_fl_has_any = yes", wants)
        self.assertEqual(_number(_raw(FLEET_VALUES), "sr_battery_ai_max_levels"), 5)

    def test_the_ai_runs_lasers_at_war_or_from_cluttered(self):
        self.assertIn("sr_fl_ai_batteries = yes", _block(_strip(_raw(FLEET_EFFECTS)), "sr_fl_ai_review"))
        ai = _block(_strip(_raw(EARTH_EFFECTS)), "sr_fl_ai_batteries")
        self.assertIn("has_technology_researched = directed_energy_weapons", ai)
        self.assertRegex(ai, r"OR = \{\s*is_at_war = yes\s*te_debris_index >= te_debris_tier_cluttered\s*\}")
        self.assertIn("production_method = pm_orbital_battery_lasers", ai)
        self.assertIn("production_method = pm_orbital_battery_kinetic", ai)

    def test_the_console_options(self):
        event = _block(_strip(_raw(DEBUG_EVENTS)), "te_debug_space_race.6")
        self.assertIn("sr_reserve_debug_fill = yes", event)
        self.assertIn("sr_earth_debug_blockade = yes", event)
        blockade = _block(_strip(_raw(EARTH_EFFECTS)), "sr_earth_debug_blockade")
        self.assertIn("has_war_with = root", blockade)
        self.assertIn("sr_fl_by_local = { DO = new_at_earth }", blockade)


class LunarAtEarthTest(unittest.TestCase):
    """Lunar colonization design § 8: the Moon's six worlds sit at Earth. A fleet
    there may close in on a hostile lunar world (everything else at Earth is
    stationed), a lunar world is blockaded while its holder's Earth is, nobody
    interdicts at Earth, the AI closes in from Earth while it holds orbit, and
    Orbital Superiority counts a closing-in fleet as at Earth."""

    EARTH_OVERRIDE = (r"limit = \{\s*local_var:sr_cb_code = 1\s*NOT = \{\s*AND = \{\s*local_var:sr_cb_p = 3\s*"
                      r"sr_fl_\$N\$_target_lunar = yes\s*\}\s*\}\s*\}\s*"
                      r"set_local_variable = \{ name = sr_cb_p value = 1 \}")

    @classmethod
    def setUpClass(cls):
        cls.combat = _strip(_raw(COMBAT_EFFECTS))
        cls.triggers = _strip(_raw(FLEET_TRIGGERS))
        cls.generated = _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT))
        cls.gen_triggers = _strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT))
        cls.display = _strip(_raw(gsf.ROOT / gsf.DISPLAY_OUT))
        cls.lunar = [w for w in gss.SITES if w.location == "earth"]

    def test_the_moon_is_at_earth(self):
        self.assertEqual([w.key for w in gsf.LUNAR], [w.key for w in self.lunar])
        self.assertEqual(len(self.lunar), 6)
        self.assertIn("earth", [lc.key for lc in gsf.CLOSE_IN_LOCATIONS])
        self.assertNotIn("earth", [lc.key for lc in gsf.INTERDICT_LOCATIONS])

    def test_a_lunar_target_is_exactly_a_lunar_world(self):
        for n in range(1, gsf.SLOTS + 1):
            body = _block(self.gen_triggers, f"sr_fl_{n}_target_lunar")
            with self.subTest(slot=n):
                self.assertIn(f"has_variable = sr_fl_{n}_target", body)
                self.assertEqual(sorted(int(i) for i in re.findall(rf"var:sr_fl_{n}_target = (\d+)", body)),
                                 sorted(w.index for w in self.lunar))
                self.assertEqual(_block(self.gen_triggers, f"sr_fl_{n}_at_earth").strip(),
                                 f"has_variable = sr_fl_{n}_loc var:sr_fl_{n}_loc = 1")

    def test_posture_3_survives_gathering_at_earth_only_for_a_lunar_target(self):
        gather = _block(self.combat, "sr_fl_gather_at")
        losses = _block(self.combat, "sr_fl_apply_losses_at")
        for name, body in (("gather", gather), ("losses", losses)):
            with self.subTest(helper=name):
                # Earth stations everything else; the same rule in both, so the
                # strength gathered closing in is the strength whose losses close in.
                self.assertRegex(body, self.EARTH_OVERRIDE)
                self.assertNotRegex(body, r"limit = \{ local_var:sr_cb_code = 1 \} set_local_variable = "
                                          r"\{ name = sr_cb_p value = 1 \}")
        # The override runs before the target check, and puts the stored posture
        # back to Station (no Stand off at Earth for the panel to show).
        override = re.search(self.EARTH_OVERRIDE, gather)
        self.assertLess(override.start(), gather.index("sr_fl_check_target_at = { N = $N$ }"))
        self.assertIn("set_variable = { name = sr_fl_$N$_posture value = 1 }", gather[override.end():
                                                                                     gather.index("sr_fl_check_target_at")])
        # A target no longer hostile stations a fleet at Earth, stands it off elsewhere.
        check = _block(self.combat, "sr_cb_check_target")
        self.assertRegex(check, r"limit = \{ sr_fl_\$N\$_at_earth = yes \}\s*"
                                r"set_variable = \{ name = sr_fl_\$N\$_posture value = 1 \}\s*\}\s*else = \{\s*"
                                r"set_variable = \{ name = sr_fl_\$N\$_posture value = 2 \}")

    def test_the_earth_posture_options(self):
        step = _block(self.combat, "sr_fl_step_posture_at")
        earth = _block("x = {" + step.split("limit = { sr_fl_$N$_at_earth = yes }", 1)[1], "x")
        # Station and Close in, Close in only on a hostile world here; never Stand
        # off or Interdict at Earth.
        self.assertRegex(earth, r"NOT = \{ local_var:sr_cb_p = 3 \}\s*sr_fl_\$N\$_has_hostile_world = yes\s*\}\s*"
                                r"set_variable = \{ name = sr_fl_\$N\$_posture value = 3 \}")
        self.assertIn("sr_fl_step_hostile_target_at = { N = $N$ }", earth)
        self.assertIn("sr_fl_charge_free_at = { N = $N$ }", earth)
        self.assertRegex(earth, r"else = \{\s*set_variable = \{ name = sr_fl_\$N\$_posture value = 1 \}")
        self.assertNotIn("value = 2 }", earth)
        self.assertNotIn("value = 4 }", earth)
        self.assertLess(step.index("sr_fl_$N$_at_earth = yes"), step.index("local_var:sr_cb_p <= 1"))
        # The button is shown at Earth only while such a world exists, with its own tooltip.
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                combat = _block(self.display, f"sr_disp_fl_{n}_combat")
                self.assertIn(f"else_if = {{ limit = {{ sr_fl_{n}_at_earth = yes sr_fl_{n}_has_hostile_world = yes }} value = 1 }}",
                              combat)
                hostile = _block(self.gen_triggers, f"sr_fl_{n}_has_hostile_world")
                earth_line = next(line for line in hostile.splitlines() if f"var:sr_fl_{n}_loc = 1 " in line)
                self.assertEqual(re.findall(r"sr_site_hostile_target = \{ KEY = (\w+) \}", earth_line),
                                 [w.key for w in self.lunar])
        sgui = _block(_strip(_raw(SGUIS)), "sr_fleet_posture_sgui")
        self.assertRegex(sgui, r"limit = \{ sr_fl_op_check = \{ TEST = at_earth \} \}\s*custom_tooltip = sr_fl_posture_earth_tt")
        # The target button steps through the lunar worlds at Earth.
        hostile_step = _block(self.generated, "sr_fl_step_hostile_target_at")
        earth_case = _block("x = {" + hostile_step.split("limit = { var:sr_fl_$N$_loc = 1 }", 1)[1], "x")
        self.assertEqual(sorted(set(re.findall(r"sr_site_hostile_target = \{ KEY = (\w+) \}", earth_case))),
                         sorted(w.key for w in self.lunar))

    def test_no_interdiction_at_earth(self):
        """Owner, § 15.3: posture 4 is never offered at Earth, so no lunar world is interdicted."""
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                self.assertNotIn(f"var:sr_fl_{n}_loc = 1 ", _block(self.gen_triggers, f"sr_fl_{n}_has_interdict_world"))
        self.assertNotIn("var:sr_fl_$N$_loc = 1 }", _block(self.generated, "sr_fl_step_icpt_target_at"))
        rebuild = _block(self.generated, "sr_icpt_rebuild")
        self.assertNotIn("LOC = earth", rebuild)
        self.assertNotIn("sr_icpt_earth", rebuild)
        lunar_step = _block(self.combat, "sr_site_lunar_blockade_step")
        self.assertNotIn("sr_icpt_interdicts_at", lunar_step)
        self.assertNotIn("set_global_variable = { name = sr_site_interdicted_", lunar_step)
        self.assertNotIn("sr_icpt", _block(self.display, "sr_disp_loc_status_earth"))

    def test_a_lunar_world_is_blockaded_while_its_holder_s_earth_is(self):
        after = _block(self.generated, "sr_cb_worlds_after_earth")
        for w in self.lunar:
            with self.subTest(site=w.key):
                self.assertIn(f"sr_site_assault_step = {{ KEY = {w.key} INDEX = {w.index} }}", after)
                self.assertIn(f"sr_site_lunar_blockade_step = {{ KEY = {w.key} }}", after)
        # The generic step's stand-off test never holds at Earth, so it is not called there.
        self.assertNotIn("sr_site_blockade_step", after)
        self.assertIn("sr_cb_s2_value > 0", _block(self.combat, "sr_site_blockade_step"))
        step = _block(self.combat, "sr_site_lunar_blockade_step")
        self.assertRegex(step, r"NOT = \{ has_global_variable = sr_site_occupier_\$KEY\$ \}\s*"
                               r"global_var:sr_site_holder_\$KEY\$ \?= \{\s*is_country_alive = yes\s*sr_earth_blockaded = yes\s*\}")
        self.assertIn("set_global_variable = { name = sr_site_blockaded_$KEY$ value = yes }", step)
        self.assertIn("remove_global_variable = sr_site_blockaded_$KEY$", step)
        self.assertEqual(step.count("sr_sites_refresh_players = yes"), 2)
        # Earth's Locations row: a battle, our Earth blockaded, or theirs.
        status = _block(self.display, "sr_disp_loc_status_earth")
        self.assertEqual(re.findall(r"value = (\d) \}", status), ["1", "6", "7"])

    def test_the_ai_closes_in_from_earth_while_it_holds_orbit(self):
        attack = _block(self.combat, "sr_fl_ai_attack")
        self.assertLess(attack.index("sr_fl_ai_lunar_assault = yes"), attack.index("sr_fl_ai_attack_all = yes"))
        lunar = _block(self.generated, "sr_fl_ai_lunar_assault")
        # Its strongest fleet at Earth.
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                self.assertIn(f"limit = {{ sr_fl_{n}_at_earth = yes sr_fl_{n}_strength > local_var:sr_fl_best }}", lunar)
                self.assertRegex(lunar, rf"limit = \{{ local_var:sr_fl_n = {n} local_var:sr_ai_tgt > 0 "
                                        rf"sr_fl_{n}_marines_value > local_var:sr_ai_need \}}\s*"
                                        rf"set_variable = \{{ name = sr_fl_{n}_posture value = 3 \}}\s*"
                                        rf"set_variable = \{{ name = sr_fl_{n}_target value = local_var:sr_ai_tgt \}}")
                self.assertIn(f"remove_variable = sr_fl_{n}_destroy", lunar)
                # Every other fleet at Earth, and this one without the marines, stays stationed.
                self.assertRegex(lunar, rf"else = \{{\s*set_variable = \{{ name = sr_fl_{n}_posture value = 1 \}}")
        # The enemy's lunar world of most people and modules, never a free one,
        # only while that enemy's Earth is blockaded.
        for w in self.lunar:
            with self.subTest(site=w.key):
                self.assertIn(f"sr_site_ai_lunar_target = {{ KEY = {w.key} }} sr_site_ai_worth_{w.key} > local_var:sr_ai_best", lunar)
                self.assertIn(f"set_local_variable = {{ name = sr_ai_need value = sr_site_garrison_need_{w.key} }}", lunar)
        self.assertEqual(len(re.findall(r"sr_site_ai_lunar_target = \{ KEY = (\w+) \}", lunar)), len(self.lunar))
        # Only with no enemy fleet at Earth at all: any stationed one bars the seizure.
        guarded = _block("x = {" + lunar.split("limit = { NOT = { sr_earth_hostile_present = yes } }", 1)[1], "x")
        self.assertEqual(len(re.findall(r"sr_site_ai_lunar_target = \{ KEY = (\w+) \}", guarded)), len(self.lunar))
        self.assertIn("sr_cb_hs_value <= 0", _block(self.triggers, "sr_cb_seizes"))
        self.assertNotIn("_destroy value", lunar)
        self.assertNotIn("posture value = 2", lunar)
        target = _block(self.triggers, "sr_site_ai_lunar_target")
        self.assertIn("sr_site_ai_attack_target = { KEY = $KEY$ }", target)
        self.assertIn("global_var:sr_site_holder_$KEY$ ?= { sr_earth_blockaded = yes }", target)
        self.assertIn("global_var:sr_site_occupier_$KEY$ ?= { sr_earth_blockaded = yes }", target)
        # The offence's dispatch leaves a fleet closing in at Earth where it is.
        attack_all = _block(self.generated, "sr_fl_ai_attack_all")
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                self.assertEqual(attack_all.count(f"NOT = {{ sr_fl_{n}_closing_at_earth = yes }}"), len(gsf.LOCATIONS) - 1)
                self.assertEqual(_block(self.gen_triggers, f"sr_fl_{n}_closing_at_earth").strip(),
                                 f"sr_fl_{n}_at_earth = yes sr_fl_{n}_posture_value = 3")

    def test_orbital_superiority_counts_a_fleet_closing_in_at_earth(self):
        """§ 8.5: the margin reads sr_fl_at_earth, which counts every slot at
        Earth whatever its posture."""
        note = _block(self.generated, "sr_fl_note_at")
        self.assertIn("sr_loc_add_present = { LOC = earth }", note)
        self.assertNotIn("posture", note)
        self.assertNotIn("posture", _block(_strip(_raw(FLEET_EFFECTS)), "sr_loc_add_present"))
        self.assertIn("value = var:sr_fl_at_earth", _block(_strip(_raw(FLEET_VALUES)), "sr_orbital_superiority_margin"))


if __name__ == "__main__":
    unittest.main()
