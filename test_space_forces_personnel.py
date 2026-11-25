"""Space forces personnel (docs/superpowers/specs/2026-11-24-space-forces-personnel-design.md).

The Space Forces Base employs Spacers, the mod's first pop type, and gives
Space Forces Personnel; fleets and marines in service take them, a shortfall
scales fire and marines, and every loss kills as many Spacers. These tests
hold the shape the design names: the pop type and its classes, the building,
the values, the gates and the order, every loss site, the toll and the kill.
What only the game can show is in docs/testing/solar-colonies-playtest.md's
"Space forces personnel" section and its two self-checks.
"""

import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
sys.path.insert(0, str(ROOT))

import gen_solar_sites as gss  # noqa: E402
import gen_space_fleets as gsf  # noqa: E402
import organize_loc  # noqa: E402

POP_TYPE = ROOT / "common/pop_types/te_spacers.txt"
CLASSES = ROOT / "common/social_classes/te_spacers_classes.txt"
BUILDING = ROOT / "common/buildings/05_zz_te_sr_space_forces_base.txt"
PMGS = ROOT / "common/production_method_groups/sr_space_forces_base_pmgs.txt"
PMS = ROOT / "common/production_methods/sr_space_forces_base_pms.txt"
MODIFIER_TYPES = ROOT / "common/modifier_type_definitions/sr_fleet_modifier_types.txt"
VALUES = ROOT / "common/script_values/sr_fleet_values.txt"
TRIGGERS = ROOT / "common/scripted_triggers/sr_fleet_triggers.txt"
FLEET_EFFECTS = ROOT / "common/scripted_effects/sr_fleet_effects.txt"
COMBAT_EFFECTS = ROOT / "common/scripted_effects/sr_fleet_combat_effects.txt"
EARTH_EFFECTS = ROOT / "common/scripted_effects/sr_earth_orbit_effects.txt"
PERS_EFFECTS = ROOT / "common/scripted_effects/sr_space_forces_effects.txt"
DEMOG_EFFECTS = ROOT / "common/scripted_effects/te_demog_effects.txt"
RESETTLEMENT = ROOT / "common/scripted_triggers/resettlement_triggers.txt"
EVENTS = ROOT / "events/space_race_events.txt"
UNUSED_LOC = ROOT / "localization/english/te_unused_l_english.yml"

SYSTEM_FILES = (VALUES, TRIGGERS, FLEET_EFFECTS, COMBAT_EFFECTS, EARTH_EFFECTS, PERS_EFFECTS,
                ROOT / "common/script_values/sr_fleet_display_values.txt",
                ROOT / "common/scripted_guis/sr_fleet_sguis.txt",
                gsf.ROOT / gsf.VALUES_OUT, gsf.ROOT / gsf.EFFECTS_OUT, gsf.ROOT / gsf.TRIGGERS_OUT,
                gss.ROOT / gss.VALUES_OUT)


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


def _top_level_names(path):
    return set(re.findall(r"(?m)^([\w.-]+)\s*=\s*\{", _strip(_raw(path))))


class PopTypeTest(unittest.TestCase):
    """Design § 2: one pop type, lower strata through a class of its own in
    each social hierarchy, hired anywhere as soldiers are, and not military."""

    def test_the_pop_type(self):
        body = _block(_strip(_raw(POP_TYPE)), "spacers")
        for line in ("can_always_hire = yes", "wage_weight = 2", "start_quality_of_life = 8",
                     "unemployment = yes", "ignores_employment_proportionality = yes"):
            with self.subTest(line=line):
                self.assertIn(line, body)
        # Not one of the engine's servicemen (design § 1: military = yes).
        self.assertNotIn("military = yes", body)
        self.assertNotIn("qualifications", body)
        self.assertEqual(_top_level_names(POP_TYPE), {"spacers"})

    def test_a_class_in_every_hierarchy(self):
        text = _strip(_raw(CLASSES))
        hierarchies = {}
        for name in _top_level_names(CLASSES):
            body = _block(text, name)
            with self.subTest(cls=name):
                self.assertIn("strata = lower", body)
                self.assertRegex(body, r"allowed_professions = \{\s*spacers\s*\}")
                hierarchies[re.search(r"social_hierarchy = (\w+)", body).group(1)] = name
        self.assertEqual(set(hierarchies),
                         {"default_social_hierarchy", "british_indian_caste_system", "edo_system"})
        # Never an INJECT into vanilla's classes (design § 2).
        self.assertNotIn("INJECT:", text)

    @unittest.skipUnless(os.path.isfile(os.path.expanduser("~/src/vic3/game/common/social_hierarchies/"
                                                           "00_social_hierarchies.txt")),
                         "needs the vanilla mirror")
    def test_vanilla_has_no_other_hierarchy(self):
        vanilla = _raw(os.path.expanduser("~/src/vic3/game/common/social_hierarchies/00_social_hierarchies.txt"))
        self.assertEqual(set(re.findall(r"(?m)^(\w+) = \{", _strip(vanilla))),
                         {"default_social_hierarchy", "british_indian_caste_system", "edo_system"})

    def test_organize_loc_keeps_its_engine_keys(self):
        keys = organize_loc.find_pop_type_keys(str(ROOT))
        for key in ("spacers", "spacers_desc", "spacers_no_icon", "spacers_only_icon",
                    "te_spacers_class", "te_spacers_class_desc", "te_spacers_class_caste_desc",
                    "te_spacers_class_edo", "te_spacers_class_edo_desc"):
            with self.subTest(key=key):
                self.assertIn(key, keys)
                self.assertNotRegex(_raw(UNUSED_LOC), rf"(?m)^ {key}:")

    def test_resettlement_never_moves_them(self):
        self.assertIn("NOT = { is_pop_type = spacers }", _block(_strip(_raw(RESETTLEMENT)), "resettlement_pop_eligible"))


class BuildingTest(unittest.TestCase):
    """Design § 3: a government building under Full Colonies, no goods, 1,000
    Spacers and 1,000 Space Forces Personnel a level."""

    def test_the_building(self):
        body = _block(_strip(_raw(BUILDING)), "building_space_forces_base")
        self.assertIn("building_group = bg_government", body)
        self.assertRegex(body, r"unlocking_technologies = \{\s*cislunar_infrastructure\s*\}")
        self.assertRegex(body, r"production_method_groups = \{\s*pmg_space_forces_base\s*\}")
        self.assertIn("sr_colonies_full_enabled = yes", _block("x = {" + body.split("potential = {", 1)[1], "x"))
        self.assertIn("sr_pers_may_build_government = yes", body)
        self.assertRegex(body, r"can_build_private = \{\s*always = no\s*\}")

    def test_the_method(self):
        self.assertRegex(_block(_strip(_raw(PMGS)), "pmg_space_forces_base"),
                         r"production_methods = \{\s*pm_space_forces_training\s*\}")
        pm = _block(_strip(_raw(PMS)), "pm_space_forces_training")
        self.assertRegex(pm, r"level_scaled = \{\s*building_employment_spacers_add = 1000\s*\}")
        self.assertRegex(pm, r"workforce_scaled = \{\s*state_sr_space_personnel_add = 1000\s*"
                             r"interest_group_ig_armed_forces_pop_attraction_mult = 0.01\s*\}")
        self.assertNotIn("goods_input", pm)
        self.assertNotIn("goods_output", pm)
        types = _strip(_raw(MODIFIER_TYPES))
        self.assertIn("script_only = yes", _block(types, "state_sr_space_personnel_add"))
        _block(types, "building_employment_spacers_add")
        self.assertEqual(float(re.search(r"(?m)^sr_pers_per_level = \{ value = ([\d.]+) \}", _raw(VALUES)).group(1)), 1000)


class ValuesTest(unittest.TestCase):
    """Design § 4: the rates, capacity over every state, the share and the room."""

    @classmethod
    def setUpClass(cls):
        cls.values = _strip(_raw(VALUES))

    def test_the_rates(self):
        self.assertRegex(_block(self.values, "sr_pers_per_point_base"), r"^\s*value = 100\s*$")
        per_point = _block(self.values, "sr_pers_per_point")
        self.assertIn("has_technology_researched = artificial_intelligence", per_point)
        self.assertIn("multiply = 0.5", per_point)
        self.assertRegex(_block(self.values, "sr_pers_per_battalion"), r"^\s*value = 1000\s*$")
        self.assertRegex(_block(self.values, "sr_assault_loss_share"), r"^\s*value = 0.5\s*$")
        self.assertRegex(_block(self.values, "sr_pers_grace_months"), r"^\s*value = 6\s*$")

    def test_capacity_counts_occupied_bases(self):
        bases = _block(self.values, "sr_pers_capacity_bases")
        self.assertIn("every_scope_state", bases)
        self.assertIn("add = modifier:state_sr_space_personnel_add", bases)
        self.assertNotIn("sr_state_held_by_owner", bases)
        self.assertNotIn("limit", bases)
        # In the grace, at least the personnel the migration found: a lower clamp.
        cap = _block(self.values, "sr_pers_capacity")
        self.assertIn("min = var:sr_pers_grace_capacity", cap)
        self.assertNotIn("max = var:sr_pers_grace_capacity", cap)

    def test_in_service_and_the_share(self):
        crews = _block(self.values, "sr_pers_crews")
        self.assertIn("sr_fl_strength_full_total", crews)
        self.assertIn("multiply = sr_pers_per_point", crews)
        marines = _block(self.values, "sr_pers_marines_in_service")
        self.assertIn("sr_pers_marines_aboard", marines)
        self.assertIn("sr_pers_marines_garrison", marines)
        share = _block(self.values, "sr_pers_share_calc")
        self.assertIn("max = 1", share)
        self.assertIn("min = 0", share)
        self.assertIn("sr_pers_in_grace", share)
        # Every fire term reads readiness, so the share reaches them all through it.
        self.assertTrue(_block(self.values, "sr_fleet_readiness").rstrip().endswith("multiply = sr_pers_share_value"))

    def test_the_room_is_never_negative(self):
        room = _block(self.values, "sr_pers_room_value")
        self.assertIn("value = sr_pers_capacity", room)
        self.assertIn("subtract = sr_pers_in_service", room)
        self.assertIn("min = 0", room)
        share = _block(self.values, "sr_pers_reserve_share")
        self.assertIn("max = 1", share)
        # The AI's launch match counts only the reserve it can crew.
        self.assertIn("max = sr_pers_room_points", _block(self.values, "sr_earth_reserve_and_ours"))

    def test_every_value_the_system_names_is_defined(self):
        """A bare script-value name the engine can't find reads as nothing, and no
        audit catches it in script (sr_pers_state_spacers was used and undefined)."""
        defined = set()
        for sub in ("script_values", "scripted_triggers", "scripted_effects"):
            for path in (ROOT / "common" / sub).glob("*.txt"):
                defined |= _top_level_names(path)
        for path in SYSTEM_FILES:
            text = _strip(_raw(path))
            for name in sorted(set(re.findall(
                    r"\b(?:value|add|subtract|multiply|divide|max|min|count)\s*=\s*(sr_(?:pers|site_assault|assault)\w*)(?![\w$])",
                    text))):
                with self.subTest(file=path.name, name=name):
                    self.assertTrue(name in defined, f"{name} is named but defined nowhere")


class GatesAndOrderTest(unittest.TestCase):
    """Design § 4: hulls launch and marines board only within the room, in the
    toggle's order; the share is stored last."""

    @classmethod
    def setUpClass(cls):
        cls.fleet = _strip(_raw(FLEET_EFFECTS))
        cls.earth = _strip(_raw(EARTH_EFFECTS))
        cls.pers = _strip(_raw(PERS_EFFECTS))

    def test_the_month(self):
        month = _block(self.fleet, "sr_fl_country_month")
        order = ["sr_pers_migrate_once = yes", "sr_sc_month = yes", "sr_fl_upkeep_refresh = yes",
                 "sr_pers_ai_priority = yes", "sr_pers_close = yes", "sr_fl_leave_powers = yes"]
        self.assertEqual(order, sorted(order, key=month.index))
        self.assertIn("sr_fleet_power", _strip(_raw(TRIGGERS)).split("sr_has_space_forces_base = yes", 1)[0][-800:])

    def test_marines_refill_within_the_room(self):
        refill = _block(self.fleet, "sr_fl_marines_refill_at")
        self.assertIn("add = sr_pers_room_battalions", refill)
        self.assertIn("max = sr_fl_$N$_marine_capacity", refill)
        month = _block(self.fleet, "sr_fl_month_at")
        self.assertIn("sr_fl_marines_refill_at = { N = $N$ }", month)

    def test_the_launch_is_gated(self):
        launch = _block(self.earth, "sr_reserve_launch")
        self.assertIn("sr_pers_can_crew_launch = yes", launch)
        self.assertIn("sr_reserve_launch_crewed = yes", launch)
        self.assertIn("sr_pers_can_crew_launch = yes", _block(self.earth, "sr_reserve_auto_step"))

    def test_the_toggle(self):
        toggle = _block(self.pers, "sr_pers_toggle_priority")
        self.assertIn("sr_pers_marines_first", toggle)
        ai = _block(self.pers, "sr_pers_ai_priority")
        self.assertIn("is_at_war = yes", ai)
        self.assertIn("sr_pers_priority_sgui", _raw(ROOT / "common/scripted_guis/sr_fleet_sguis.txt"))

    def test_close_stores_the_share_and_pays_the_dead(self):
        close = _block(self.pers, "sr_pers_close")
        self.assertLess(close.index("name = sr_pers_share value = sr_pers_share_calc"),
                        close.index("sr_pers_kill_step = yes"))


class LossesTest(unittest.TestCase):
    """Design § 5.1: every loss adds its people to the due, at the loser's
    share; moves that are not deaths add nothing."""

    @classmethod
    def setUpClass(cls):
        cls.fleet = _strip(_raw(FLEET_EFFECTS))
        cls.combat = _strip(_raw(COMBAT_EFFECTS))
        cls.pers = _strip(_raw(PERS_EFFECTS))

    def test_the_fleet_losses(self):
        cut = _block(self.fleet, "sr_fl_cut_role")
        self.assertLess(cut.index("name = sr_pers_full_was"), cut.index("sr_pers_note_lost = yes"))
        month = _block(self.fleet, "sr_fl_month_at")
        # a slot cleared, attrition and the marine trim
        self.assertEqual(month.count("sr_pers_note_lost = yes"), 3)
        self.assertLess(month.index("sr_pers_note_lost = yes"), month.index("sr_fl_clear_at = { N = $N$ }"))

    def test_the_garrison_losses(self):
        for name in ("sr_site_occupy", "sr_site_liberate"):
            with self.subTest(effect=name):
                self.assertTrue(_block(self.combat, name).lstrip().startswith("sr_site_note_garrison_dead = { KEY = $KEY$ }"))
        # A destroyed world charges its own marines only: on the Moon and Mars its
        # holder's others there stay in service (review of #2020).
        destroy = _block(self.combat, "sr_site_destroy")
        self.assertLess(destroy.index("sr_site_note_destroyed_dead = { KEY = $KEY$ }"),
                        destroy.index("sr_site_release_$KEY$"))
        self.assertNotIn("sr_site_note_garrison_dead", destroy)
        self.assertIn("MARINES = sr_site_shared_marines_$KEY$ NOTICE = yes", _block(self.pers, "sr_site_note_garrison_dead"))
        self.assertIn("MARINES = sr_site_marines_value_$KEY$ NOTICE = no", _block(self.pers, "sr_site_note_destroyed_dead"))
        note = _block(self.pers, "sr_site_note_marines_dead")
        self.assertIn("value = $MARINES$", note)
        self.assertIn("sr_pers_note_people = yes", note)

    def test_the_share_applies_once(self):
        # Counts of hulls and battalions are nominal: the dead are their crewed share.
        self.assertIn("multiply = sr_pers_share_value", _block(self.pers, "sr_pers_note_lost"))
        note = _block(self.pers, "sr_pers_note_lost")
        self.assertLess(note.index("multiply = sr_pers_share_value"), note.index("sr_pers_note_people = yes"))
        self.assertNotIn("sr_pers_share_value", _block(self.pers, "sr_pers_note_people"))

    def test_moves_are_not_deaths(self):
        for name in ("sr_fl_land_at", "sr_fl_embark_at"):
            if re.search(rf"(?m)^{name}\s*=", self.fleet):
                with self.subTest(effect=name):
                    self.assertNotIn("sr_pers_note", _block(self.fleet, name))


class TollTest(unittest.TestCase):
    """Design § 5.2: a seizure needs and pays the need plus half again, and
    lands the need and one."""

    def test_the_generated_values(self):
        values = _strip(_raw(gss.ROOT / gss.VALUES_OUT))
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertRegex(values, rf"(?m)^sr_site_assault_toll_{k} = \{{ value = sr_site_garrison_need_{k} "
                                         r"multiply = sr_assault_loss_share \}")
                self.assertRegex(values, rf"(?m)^sr_site_assault_need_{k} = \{{ value = sr_site_garrison_need_{k} "
                                         rf"add = sr_site_assault_toll_{k} \}}")
                self.assertIn(f"multiply = sr_site_marines_share_{k}", _block(values, f"sr_site_garrison_need_{k}"))

    def test_the_seizure(self):
        self.assertIn("var:sr_cb_mar_$KEY$ > sr_site_assault_need_$KEY$",
                      _block(_strip(_raw(TRIGGERS)), "sr_cb_seizes"))
        seize = _block(_strip(_raw(COMBAT_EFFECTS)), "sr_site_seize")
        pay = _block("x = {" + seize.split("name = sr_cb_pay", 1)[1], "x")
        for line in ("value = sr_site_garrison_need_$KEY$", "add = 1", "add = sr_site_assault_toll_$KEY$",
                     "max = var:sr_cb_mar_$KEY$"):
            self.assertIn(line, pay)
        self.assertIn("subtract = local_var:sr_cb_toll", seize)
        # Effective marines back into battalions before they are spent: at the crewed
        # share and the Training Grounds' weight (sr_marine_weight_value, 2026-11-24).
        self.assertLess(seize.index("divide = sr_marine_weight_value"), seize.index("sr_fl_spend_marines_$KEY$ = yes"))

    def test_the_ai_weighs_it(self):
        generated = _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT))
        for name in ("sr_fl_ai_assault_at", "sr_fl_ai_lunar_assault"):
            with self.subTest(effect=name):
                body = _block(generated, name)
                self.assertIn("sr_site_assault_need_", body)
                self.assertNotIn("value = sr_site_garrison_need_", body)


class KillTest(unittest.TestCase):
    """Design § 5.3: whole hundreds, by each state's capacity, at most its
    Spacers, booked as the census's war dead."""

    @classmethod
    def setUpClass(cls):
        cls.pers = _strip(_raw(PERS_EFFECTS))
        cls.values = _strip(_raw(VALUES))

    def test_the_batch_is_the_kill_s_constant(self):
        kill = _block(self.pers, "sr_pers_kill_step")
        batch = re.search(r"kill_population_in_state = \{ value = (\d+) pop_type = spacers \}", kill)
        self.assertIsNotNone(batch)
        self.assertRegex(_block(self.values, "sr_pers_kill_batch"), rf"^\s*value = {batch.group(1)}\s*$")
        self.assertIn("count = local_var:sr_pk_here", kill)
        self.assertIn("max = sr_pers_state_spacer_steps", kill)
        self.assertIn("max = sr_pers_kill_max_steps", kill)
        self.assertIn("te_demog_note_war_dead = { VALUE = local_var:sr_pk_people }", kill)

    def test_the_state_s_spacers(self):
        spacers = _block(self.values, "sr_pers_state_spacers")
        self.assertIn("every_scope_pop", spacers)
        self.assertIn("is_pop_type = spacers", spacers)
        self.assertIn("add = total_size", spacers)
        steps = _block(self.values, "sr_pers_state_spacer_steps")
        self.assertIn("divide = sr_pers_kill_batch", steps)
        self.assertIn("floor = yes", steps)

    def test_the_census_books_them_as_war_dead(self):
        book = _block(_strip(_raw(DEMOG_EFFECTS)), "te_demog_note_war_dead")
        self.assertIn("te_demog_cohorts_run = yes", book)
        self.assertIn("te_demog_has_census = yes", book)
        self.assertIn("change_variable = { name = te_dg_war_in add = $VALUE$ }", book)


class ReviewFixesTest(unittest.TestCase):
    """The independent review of #2020: each fix held in place."""

    @classmethod
    def setUpClass(cls):
        cls.fleet = _strip(_raw(FLEET_EFFECTS))
        cls.combat = _strip(_raw(COMBAT_EFFECTS))
        cls.pers = _strip(_raw(PERS_EFFECTS))
        cls.values = _strip(_raw(VALUES))
        cls.triggers = _strip(_raw(TRIGGERS))

    def test_marines_coming_home_stay_within_the_room(self):
        # Coming home is no loss: uncapped, the month's trim counted them dead.
        take = _block(self.fleet, "sr_fl_take_marines_at")
        self.assertIn("max = sr_fl_$N$_marine_capacity", take)

    def test_only_marines_past_the_full_room_die(self):
        # Damage kills no crew: a damaged carrier's marines leave service alive.
        month = _block(self.fleet, "sr_fl_month_at")
        trim = month[month.index("sr_fl_$N$_marines_value > sr_fl_$N$_marine_capacity"):]
        self.assertLess(trim.index("sr_fl_$N$_carrier_full_value"), trim.index("sr_pers_note_lost = yes"))
        self.assertIn("multiply = sr_fl_marines_per_carrier", trim[:trim.index("sr_pers_note_lost = yes")])

    def test_the_kill_shares_add_up(self):
        kill = _block(self.pers, "sr_pers_kill_step")
        self.assertIn("divide = local_var:sr_pk_cap_left", kill)
        self.assertIn("multiply = local_var:sr_pk_left", kill)
        self.assertIn("change_local_variable = { name = sr_pk_left subtract = local_var:sr_pk_here }", kill)
        self.assertIn("change_local_variable = { name = sr_pk_cap_left subtract = modifier:state_sr_space_personnel_add }", kill)
        # A while loop runs at most 1,000 times.
        cap = float(re.search(r"(?m)^sr_pers_kill_max_steps = \{ value = (\d+) \}", _raw(VALUES)).group(1))
        self.assertLessEqual(cap, 1000)

    def test_the_ai_counts_levels_built_and_queued(self):
        wanted = _block(self.values, "sr_pers_ai_wanted")
        self.assertIn("value = sr_pers_planned_levels", wanted)
        self.assertNotIn("sr_pers_capacity", wanted)
        for name in ("sr_pers_planned_levels", "sr_pers_queued_levels"):
            with self.subTest(value=name):
                body = _block(self.values, name)
                self.assertIn("exists = b:building_space_forces_base", body)
                self.assertNotIn("has_building", body)

    def test_a_launch_is_at_least_a_fleet(self):
        self.assertIn("sr_pers_room_points >= sr_fl_minimum_strength", _block(self.triggers, "sr_pers_can_crew_launch"))

    def test_the_battle_report_gives_what_was_booked(self):
        record = _block(self.combat, "sr_cb_battle_record")
        self.assertIn("set_variable = { name = sr_battle_dead value = local_var:sr_pers_noted }", record)
        self.assertIn("change_local_variable = { name = sr_pers_noted add = local_var:sr_pers_lost }",
                      _block(self.pers, "sr_pers_note_people"))
        step = self.combat[:self.combat.index("sr_cb_battle_record = { CODE = $CODE$ }")]
        self.assertLess(step.rindex("set_local_variable = { name = sr_pers_noted value = 0 }"),
                        step.rindex("sr_fl_each_slot = { DO = apply_losses }"))

    def test_the_year_s_dead_go_stale(self):
        shown = _block(_strip(_raw(ROOT / "common/script_values/sr_fleet_display_values.txt")), "sr_disp_pers_killed_year")
        self.assertIn("var:sr_pers_killed_year_from >=", shown)

    def test_the_migration_crews_the_reserve(self):
        need = _block(self.values, "sr_pers_migrate_need")
        self.assertIn("value = sr_pers_in_service", need)
        self.assertIn("sr_reserve_total", need)
        self.assertIn("value = sr_pers_migrate_need", _block(self.values, "sr_pers_migrate_levels"))
        self.assertIn("name = sr_pers_grace_capacity value = sr_pers_migrate_need", _block(self.pers, "sr_pers_migrate_once"))


class SelfChecksTest(unittest.TestCase):
    def test_the_kill_check_s_event(self):
        events = _strip(_raw(EVENTS))
        body = _block(events, "space_race_events.140")
        self.assertIn("hidden = yes", body)
        self.assertIn("sr_pers_kill_self_check = yes", body)
        self.assertIn("trigger_event = { id = space_race_events.140 days = 1 }",
                      _block(_strip(_raw(PERS_EFFECTS)), "sr_pers_kill_check_arm"))

    def test_the_pop_type_check_arms_on_its_country(self):
        check = _block(_strip(_raw(PERS_EFFECTS)), "sr_pers_pop_type_self_check")
        # Armed on a base of a level or more, whatever its staff, so a pop type that
        # never hires still gets a line; read three months on, with room for
        # throughput (review of #2020).
        self.assertIn("sr_pers_has_base_level = yes", check)
        self.assertIn("add = 3", check)
        self.assertIn("multiply = 0.75", check)
        self.assertIn("multiply = 1.5", check)
        # A global arm is cleared by any fleet power without a staffed base that runs first.
        self.assertNotIn("has_global_variable = sr_pers_pop_type_armed", check)
        self.assertIn("set_variable = { name = sr_pers_pop_type_armed value = te_history_month_index }", check)
        self.assertIn("TE_SELF_CHECK OK pers_pop_type", _raw(PERS_EFFECTS))
        self.assertIn("TE_SELF_CHECK BROKEN pers_pop_type", _raw(PERS_EFFECTS))



class ModulePersonnelTest(unittest.TestCase):
    """The owner, 2026-11-25: Spaceport, Defenses, Black Site, Training Ground and
    Nuclear Command Center each take 1,000 personnel a level as well as a crew,
    under Full Colonies. They count in service with the fleets and marines, and
    their effects run at the holder's crewed share."""

    @classmethod
    def setUpClass(cls):
        cls.values = _strip(_raw(VALUES))
        cls.generated = _strip(_raw(gss.ROOT / gss.VALUES_OUT))
        cls.fleets = _strip(_raw(gsf.ROOT / gsf.VALUES_OUT))
        cls.pers = _strip(_raw(PERS_EFFECTS))

    def test_the_types(self):
        self.assertEqual(gss.PERSONNEL_TYPES, ("def", "port", "black", "train", "bunker"))
        self.assertRegex(_block(self.values, "sr_pers_per_module"), r"^\s*value = 1000\s*$")

    def test_they_count_in_service_under_full_colonies_only(self):
        modules = _block(self.values, "sr_pers_modules")
        self.assertIn("sr_colonies_full_enabled = yes", modules)
        self.assertIn("value = sr_pers_module_levels", modules)
        self.assertIn("multiply = sr_pers_per_module", modules)
        self.assertIn("add = sr_pers_modules", _block(self.values, "sr_pers_in_service"))

    def test_each_world_counts_its_personnel_levels(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                levels = _block(self.generated, f"sr_site_pers_levels_{k}")
                named = set(re.findall(rf"sr_site_(\w+?)_value_{k}\b", levels))
                self.assertEqual(named, set(gss._types_at(site, gss.PERSONNEL_TYPES)))
                total = _block(self.generated, "sr_pers_module_levels")
                self.assertRegex(total, rf"global_var:sr_site_holder_{k} \?= this NOT = \{{ has_global_variable = "
                                        rf"sr_site_occupier_{k} \}} \}} add = sr_site_pers_levels_{k}")

    def test_their_effects_run_at_the_share(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                share = _block(self.generated, f"sr_site_pers_share_{k}")
                self.assertIn("sr_colonies_full_enabled = yes", share)
                self.assertIn(f"global_var:sr_site_holder_{k} = {{ add = sr_pers_share_value }}", share)
                self.assertIn("else = { add = 1 }", share)
                self.assertIn(f"multiply = sr_site_pers_share_{k}", _block(self.generated, f"sr_site_def_staffed_{k}"))
                self.assertIn(f"multiply = sr_site_pers_share_{k}", _block(self.generated, f"sr_site_port_crewed_{k}"))
                for t in gss.FACILITY_TYPES:
                    if t not in gss.generic_types(site):
                        continue
                    staffed = _block(self.generated, f"sr_site_{t}_staffed_{k}")
                    if t in gss.PERSONNEL_TYPES:
                        self.assertIn(f"multiply = sr_site_pers_share_{k}", staffed, t)
                    else:
                        self.assertNotIn("sr_site_pers_share", staffed, t)
        # A Spaceport's repairs read the crewed level.
        for loc in gsf.LOCATIONS[1:]:
            port = _block(self.fleets, f"sr_loc_port_level_{loc.key}")
            self.assertNotIn("min = sr_site_port_value_", port)
            for s in gsf.worlds_at(loc.key):
                self.assertIn(f"min = sr_site_port_crewed_{s.key}", port)

    def test_a_holder_with_no_fleet_stores_the_share(self):
        on_action = _strip(_raw(ROOT / "common/on_actions/space_race_on_actions.txt"))
        m = re.search(r"if = \{\s*limit = \{\s*sr_colonies_full_enabled = yes\s*OR = \{\s*sr_has_space_colony = yes\s*"
                      r"has_variable = sr_pers_share\s*\}\s*NOT = \{ sr_fleet_power = yes \}\s*\}\s*"
                      r"set_variable = \{ name = sr_pers_share value = sr_pers_share_calc \}", on_action)
        self.assertTrue(m, "the non-fleet-power branch that stores the share")

    def test_the_migration_runs_once_a_save(self):
        migrate = _block(self.pers, "sr_pers_modules_migrate_once")
        self.assertIn("NOT = { has_global_variable = sr_pers_modules_migrated }", migrate)
        self.assertIn("every_country", migrate)
        self.assertIn("sr_pers_module_levels > 0", migrate)
        # It counts as the fleets' migration, which would build the hiring levels again.
        self.assertIn("set_variable = { name = sr_pers_migrated value = yes }", migrate)
        self.assertIn("name = sr_pers_grace_capacity value = sr_pers_migrate_need", migrate)
        self.assertIn("value = sr_pers_mod_migrate_levels", migrate)
        levels = _block(self.values, "sr_pers_mod_migrate_levels")
        self.assertIn("value = sr_pers_planned_levels", levels)
        self.assertIn("max = 100", levels)
        self.assertIn("sr_pers_migrate_build = yes", _block(self.pers, "sr_pers_migrate_once"))
        sites = _strip(_raw(ROOT / "common/scripted_effects/sr_site_effects.txt"))
        self.assertRegex(_block(sites, "sr_sites_global_monthly"),
                         r"limit = \{ sr_colonies_full_enabled = yes \}\s*sr_fl_global_month = yes\s*"
                         r"sr_pers_modules_migrate_once = yes")

    def test_the_plus_button_line(self):
        sgui = _strip(_raw(ROOT / "common/scripted_guis/sr_colony_sguis.txt"))
        body = _block(sgui, "sr_colony_module_sgui")
        codes = sorted(re.findall(r"scope:op = (\d+)", body.split("sr_mod_scope_pers_spare", 1)[0].rsplit("sr_colonies_full_enabled", 1)[1]))
        self.assertEqual(sorted(str(gss.MODULE_CODES[t]) for t in gss.PERSONNEL_TYPES), codes)
        self.assertIn("custom_tooltip = sr_mod_queue_pers_spare_tt", body)
        self.assertIn("custom_tooltip = sr_mod_queue_pers_short_tt", body)
        trigger = _block(_strip(_raw(TRIGGERS)), "sr_mod_scope_pers_spare")
        self.assertIn("sr_pers_room_value >= sr_mod_pers_next_need", trigger)
        self.assertIn("value = sr_mod_pers_pending", _block(self.values, "sr_mod_pers_next_need"))
        loc = "".join(Path(p).read_text(encoding="utf-8-sig") for p in (ROOT / "localization/english").glob("*.yml"))
        for key in ("sr_mod_queue_pers_spare_tt", "sr_mod_queue_pers_short_tt",
                    "concept_sr_space_personnel", "concept_sr_space_personnel_desc"):
            self.assertRegex(loc, rf"(?m)^ {key}:0 ")
        self.assertIn("concept_sr_space_personnel = {}", _raw(ROOT / "common/game_concepts/extra_concepts.txt"))

    def test_the_base_comes_with_the_first_fabrication_method(self):
        """The owner, 2026-11-25: a country can staff a personnel module from the
        first it can build, so the base and its method unlock with the technology
        of the first Module Fabrication method, not with fleets'."""
        fab = _block(_strip(_raw(ROOT / "common/production_methods/sr_colony_module_pms.txt")),
                     "pm_sr_fabrication_orbital_assembly")
        tech = re.search(r"unlocking_technologies = \{\s*(\w+)\s*\}", fab).group(1)
        self.assertEqual(tech, "cislunar_infrastructure")
        for body in (_block(_strip(_raw(BUILDING)), "building_space_forces_base"),
                     _block(_strip(_raw(PMS)), "pm_space_forces_training")):
            self.assertRegex(body, rf"unlocking_technologies = \{{\s*{tech}\s*\}}")
        # So the AI's plan needs no personnel gate of its own: a module it can build
        # is one it can build a base for.
        self.assertNotIn("sr_pers_ai_may_staff_module", _raw(gss.ROOT / gss.EFFECTS_OUT))

    def test_yards_build_hulls_only_with_space_militarization(self):
        """A base makes its owner a fleet power, whose month runs Space Command's
        build, so a base and an Orbital Yard would otherwise build warships a
        technology early."""
        rate = _block(self.values, "sr_sc_rate")
        self.assertRegex(rate, r"if = \{\s*limit = \{ has_technology_researched = space_militarization \}\s*"
                               r"add = \{\s*value = sr_mod_units_yard\s*multiply = sr_mod_yard_ships\s*\}")
        self.assertEqual(rate.count("sr_mod_units_yard"), 1)

if __name__ == "__main__":
    unittest.main()
