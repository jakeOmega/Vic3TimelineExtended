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
from decimal import Decimal, InvalidOperation
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


class LocationRankTest(unittest.TestCase):
    """Second place at a location only with two powers there: position = 1 past
    the list's end caps to the last item (a lone power ranked its own
    runner-up) and logs `Given position was bigger than the list`
    (2026-10-31, 1,000 lines in one day)."""

    def test_second_place_needs_two_powers(self):
        rank = _strip(_block(_raw(gsf.ROOT / gsf.EFFECTS_OUT), "sr_loc_rank"))
        for lc in gsf.LOCATIONS:
            with self.subTest(location=lc.key):
                guard = (f"any_in_global_list = {{ variable = sr_fleet_powers is_country_alive = yes "
                         f"has_variable = sr_fl_at_{lc.key} count >= 2 }}")
                at = rank.index(guard)
                second = rank.index(f"name = sr_loc_second_{lc.key} ")
                self.assertLess(at, second)
                self.assertEqual(rank[at:second].count("position = 1"), 1)
        self.assertEqual(rank.count("position = 1"), len(gsf.LOCATIONS))


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
        for name in (*gsf.SLOT_VARS, *gsf.SLOT_LISTS, *[r.key for r in gsf.ROLES], *[f"{r.key}_full" for r in gsf.ROLES]):
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
        self.assertEqual(len(names), 17)
        for name in names:
            with self.subTest(sgui=name):
                self.assertIn("sr_colonies_full_enabled = yes", _block(sguis, name))
        survey = _block(_strip(_raw(COVERT_ACTIONS)), "covert_survey_defences_action")
        self.assertIn("sr_colonies_full_enabled = yes", survey.split("possible = {", 1)[0])


class OccupiedStateTest(unittest.TestCase):
    """§ 5.1: a building in a state its owner doesn't control counts for no one."""

    def test_construction_counts_only_states_held_by_their_owner(self):
        values = _strip(_raw(FLEET_VALUES))
        rate = _block(values, "sr_sc_rate_buildings")
        self.assertRegex(rate, r"every_scope_state = \{\s*limit = \{ sr_state_held_by_owner = yes \}\s*"
                               r"add = modifier:state_sr_ship_construction_add")
        # Space Command's, then the colonies' Orbital Yards (colony management design § 7).
        total = _block(values, "sr_sc_rate")
        self.assertIn("value = sr_sc_rate_buildings", total)
        self.assertIn("value = sr_mod_units_yard", total)

    def test_the_battlestation_fights_only_from_a_held_state(self):
        gather = _block(_strip(_raw(COMBAT_EFFECTS)), "sr_cb_battlestation_gather")
        self.assertIn("sr_battlestation_held = yes", gather)
        self.assertIn("sr_state_held_by_owner = yes", _block(_strip(_raw(FLEET_TRIGGERS)), "sr_battlestation_held"))


def _enclosing_limits(text, i):
    """The limit = { } of every block enclosing position i, innermost first."""
    stack = []
    for j, ch in enumerate(text[:i]):
        if ch == "{":
            stack.append(j)
        elif ch == "}" and stack:
            stack.pop()
    limits = []
    for j in reversed(stack):
        body = text[j + 1:].lstrip()
        if body.startswith("limit = {"):
            depth = 0
            for k, ch in enumerate(body):
                depth += ch == "{"
                depth -= ch == "}"
                if ch == "}" and depth == 0:
                    limits.append(body[:k + 1])
                    break
    return limits


def _block_around(text, i, up):
    """The block `up` levels out from position i (1: the innermost), braces included."""
    stack = []
    for j, ch in enumerate(text[:i]):
        if ch == "{":
            stack.append(j)
        elif ch == "}" and stack:
            stack.pop()
    start, depth = stack[-up], 0
    for k in range(start, len(text)):
        depth += text[k] == "{"
        depth -= text[k] == "}"
        if depth == 0:
            return text[start:k + 1]
    return text[start:]


def _top_block(text, i):
    """The outermost { } block around position i, braces included."""
    depth, start = 0, None
    for j, ch in enumerate(text[:i]):
        if ch == "{":
            if depth == 0:
                start = j
            depth += 1
        elif ch == "}":
            depth -= 1
    depth = 0
    for k in range(start, len(text)):
        depth += text[k] == "{"
        depth -= text[k] == "}"
        if depth == 0:
            return text[start:k + 1]
    return text[start:]


class UpkeepTest(unittest.TestCase):
    """The fleets' upkeep (UI pass design § 10): an identical unscaled
    maintenance line of six goods no method otherwise uses, on every yard
    method, multiplied by +900% a unit, so it follows neither the method nor
    Space Command's levels."""

    LINE = {"electronic_components": 20, "telephones": 20, "radios": 20,
            "digital_assets": 10, "robotics": 20, "fertilizer": 40}
    K = 9

    def _methods(self):
        text = _strip(_raw(METHODS))
        return {m.group(1): _block(text, m.group(1)) for m in re.finditer(r"(?m)^(pm_sr_space_command_\w+) = \{", text)}

    def test_the_upkeep_goods_are_the_maintenance_line(self):
        methods = self._methods()
        self.assertEqual(len(methods), 4)
        for name, body in methods.items():
            with self.subTest(method=name):
                m = re.search(r"(?m)^\s*unscaled = \{", body)
                self.assertIsNotNone(m, "no unscaled block")
                # The line is a building modifier of the method's.
                bm = body.index("building_modifiers = {") + len("building_modifiers = {")
                block = _top_block(body, bm)
                self.assertTrue(bm - 1 < m.start() < bm - 1 + len(block), "the line isn't in building_modifiers")
                unscaled = _block(body[m.start():].lstrip(), "unscaled")
                line = {g: int(v) for g, v in re.findall(r"goods_input_(\w+)_add = (\d+)", unscaled)}
                self.assertEqual(line, self.LINE)
                # No other input of the method names one of the six.
                rest = body.replace(unscaled, "")
                for good in self.LINE:
                    self.assertNotIn(f"goods_input_{good}_", rest)
        upkeep = _block(_raw(STATIC), "sr_fleet_upkeep_goods")
        mults = {g: v for g, v in re.findall(r"goods_input_(\w+)_mult = (\S+)", upkeep)}
        self.assertEqual(mults, {g: str(self.K) for g in self.LINE})
        # Nothing else in it: the generic input multiplier would follow the method.
        self.assertEqual(re.findall(r"(\w+) = ", upkeep), ["icon", *[f"goods_input_{g}_mult" for g in self.LINE]])
        self.assertNotRegex(_raw(STATIC), r"(?m)^sr_fleet_upkeep = \{")

    def test_every_mult_and_add_is_registered(self):
        """A mod good's goods_input_<good>_mult is silently inert unregistered
        (scripting_best_practices.md); vanilla registers some of the six."""
        mod = "\n".join(p.read_text(encoding="utf-8-sig") for p in (ROOT / "common/modifier_type_definitions").glob("*.txt"))
        vanilla = (ROOT / "vanilla_parsed/common/modifier_types.json").read_text(encoding="utf-8")
        for good in self.LINE:
            for kind in ("add", "mult"):
                name = f"goods_input_{good}_{kind}"
                with self.subTest(modifier=name):
                    self.assertTrue(re.search(rf"(?m)^{name} = \{{", mod) or f'"{name}"' in vanilla, name)

    def test_the_upkeep_is_on_the_building_and_refreshed_once(self):
        apply = _block(_strip(_raw(FLEET_EFFECTS)), "sr_fl_upkeep_apply")
        self.assertIn("is_building_type = building_space_command", apply)
        self.assertLess(apply.index("remove_modifier = sr_fleet_upkeep_goods"), apply.index("add_modifier"))
        self.assertRegex(apply, r"limit = \{\s*level >= 1\s*root\.var:sr_fleet_upkeep_units > 0\s*\}\s*"
                                r"add_modifier = \{ name = sr_fleet_upkeep_goods multiplier = root\.var:sr_fleet_upkeep_units \}")
        calls = re.findall(r"sr_fl_upkeep_apply = yes", _strip(_raw(FLEET_EFFECTS)))
        self.assertEqual(len(calls), 1)
        refreshes = re.findall(r"sr_fl_upkeep_refresh = yes", _strip(_raw(FLEET_EFFECTS)) + _strip(_raw(DEBUG_EVENTS)))
        self.assertEqual(len(refreshes), 1)

    def test_one_building_carries_the_whole_upkeep(self):
        """One Space Command a nation (owner, 2026-10-31) replaced PR 7's
        split: the upkeep sits on the one building at the fleets' units."""
        values = _strip(_raw(FLEET_VALUES))
        self.assertNotIn("sr_fleet_upkeep_per_building_value", values)
        refresh = _block(_strip(_raw(FLEET_EFFECTS)), "sr_fl_upkeep_refresh")
        self.assertRegex(refresh, r"set_variable = \{ name = sr_fleet_upkeep_units value = sr_fleet_upkeep_units_value \}\s*"
                                  r"if = \{\s*limit = \{ has_variable = sr_fleet_upkeep_per_building \}\s*"
                                  r"remove_variable = sr_fleet_upkeep_per_building\s*\}\s*sr_fl_upkeep_apply = yes")
        # Nothing reads the old split's variable any more.
        everything = "\n".join(_strip(_raw(p)) for d in ("common", "events") for p in (ROOT / d).rglob("*.txt"))
        self.assertNotIn("var:sr_fleet_upkeep_per_building", everything)
        self.assertNotIn("name = sr_fleet_upkeep_per_building", everything)
        # The count the sweep reads: every state's buildings (an occupied one's
        # included), of a level or more, as the apply walks them.
        count = _block(values, "sr_sc_buildings")
        self.assertRegex(count, r"every_scope_state = \{\s*every_scope_building = \{\s*limit = \{\s*"
                                r"is_building_type = building_space_command\s*level >= 1\s*\}\s*add = 1")

    def test_the_upkeep_probe_is_retired(self):
        """§ 10's fixed line answered the 6a upkeep_inputs probe's question."""
        texts = _strip(_raw(FLEET_EFFECTS)) + _strip(_raw(FLEET_VALUES)) + _strip(_raw(DEBUG_EVENTS))
        for name in ("sr_fl_probe", "te_debug_space_race.7", "te_debug_space_race.6.k", "te_debug_space_race.6.l"):
            with self.subTest(name=name):
                self.assertNotIn(name, texts)
        # Nor does the text a tester or player reads still describe it, or the old +1%.
        loc = "\n".join(_raw(p) for p in (ROOT / "localization/english").glob("*.yml"))
        playtest = _raw(ROOT / "docs/testing/solar-colonies-playtest.md")
        for text, where in ((loc, "loc"), (playtest, "play-test list")):
            for phrase in ("TE_SR_PROBE", "upkeep probe", "+1% for every 10 strength"):
                with self.subTest(where=where, phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_the_self_check_reads_last_month_s_apply(self):
        refresh = _block(_strip(_raw(FLEET_EFFECTS)), "sr_fl_upkeep_refresh")
        self.assertLess(refresh.index("sr_fl_upkeep_self_check = yes"),
                        refresh.index("set_variable = { name = sr_fleet_upkeep_units"))
        check = _block(_strip(_raw(FLEET_EFFECTS)), "sr_fl_upkeep_self_check")
        self.assertIn("NOT = { has_global_variable = sr_fl_upkeep_line_checked }", check)
        self.assertIn("var:sr_fleet_upkeep_units > 0", check)
        self.assertIn("has_modifier = sr_fleet_upkeep_goods", check)
        # The three axes registered for the line, each against 9 x the building's units.
        for good, var in (("robotics", "sr_fl_upkeep_line_read"), ("telephones", "sr_fl_upkeep_line_read_tel"),
                          ("digital_assets", "sr_fl_upkeep_line_read_sw")):
            with self.subTest(good=good):
                self.assertIn(f"set_variable = {{ name = {var} value = prev.modifier:goods_input_{good}_mult }}", check)
                self.assertIn(f"var:{var} > {{ value = var:sr_fl_upkeep_line_want subtract = 0.01 }}", check)
                self.assertIn(f"var:{var} < {{ value = var:sr_fl_upkeep_line_want add = 0.01 }}", check)
        self.assertRegex(check, rf"value = var:sr_fleet_upkeep_units\s*multiply = {self.K}")
        self.assertNotIn("per_building", check)
        self.assertIn("TE_SELF_CHECK OK fleet_upkeep_line", check)
        self.assertIn("TE_SELF_CHECK BROKEN fleet_upkeep_line", check)

    def test_the_panel_shows_the_percent(self):
        shown = _block(_raw(ROOT / "common/script_values/sr_fleet_display_values.txt"), "sr_disp_sc_upkeep_pct")
        # The whole fleet's, and nothing with no Space Command to carry it.
        self.assertRegex(shown, rf"limit = \{{ sr_sc_buildings >= 1 \}}\s*value = sr_fleet_upkeep_units_value\s*multiply = {self.K * 100}")


class OneSpaceCommandTest(unittest.TestCase):
    """A nation runs one Space Command (owner, 2026-10-31): with two or more of
    a level or more, the month's first step keeps the one with the most levels
    (the market capital's on a tie) and dismantles the rest, telling a player
    of each."""

    @classmethod
    def setUpClass(cls):
        cls.effects = _strip(_raw(FLEET_EFFECTS))
        cls.values = _strip(_raw(FLEET_VALUES))
        cls.sweep = _block(cls.effects, "sr_sc_one_per_nation")

    def test_it_runs_first_in_the_month(self):
        month = _block(self.effects, "sr_fl_country_month")
        self.assertTrue(month.strip().startswith("sr_sc_one_per_nation = yes"))
        for later in ("sr_sc_month = yes", "sr_fl_upkeep_refresh = yes", "sr_fl_each_slot = { DO = month }"):
            with self.subTest(step=later):
                self.assertLess(month.index("sr_sc_one_per_nation = yes"), month.index(later))
        everything = "\n".join(_strip(_raw(p)) for d in ("common", "events") for p in (ROOT / d).rglob("*.txt"))
        self.assertEqual(everything.count("sr_sc_one_per_nation = yes"), 1)

    def test_it_acts_only_on_a_second_building(self):
        self.assertRegex(self.sweep, r"^\s*if = \{\s*limit = \{ sr_sc_buildings > 1 \}")

    def test_the_keeper_has_the_most_levels_and_the_capital_breaks_a_tie(self):
        self.assertRegex(self.sweep, r"ordered_scope_state = \{\s*limit = \{ has_building = building_space_command \}\s*"
                                     r"order_by = sr_sc_keeper_score\s*max = 1\s*save_scope_as = sr_sc_keeper\s*\}")
        score = _block(self.values, "sr_sc_keeper_score")
        self.assertRegex(score, r"limit = \{ has_building = building_space_command \}\s*"
                                r"value = b:building_space_command\.level\s*multiply = 10")
        # A level outweighs the capital: 10 a level against 1.
        self.assertRegex(score, r"limit = \{\s*exists = owner\.market_capital\s*owner\.market_capital = this\s*\}\s*add = 1\s*\}\s*$")

    def test_every_other_one_is_removed(self):
        m = re.search(r"every_scope_state = \{\s*limit = \{\s*has_building = building_space_command\s*"
                      r"NOT = \{ this = scope:sr_sc_keeper \}\s*\}", self.sweep)
        self.assertIsNotNone(m)
        body = _block("x = {" + self.sweep[m.start() + len("every_scope_state = {"):], "x")
        self.assertTrue(body.rstrip().endswith("remove_building = building_space_command"))
        self.assertEqual(self.sweep.count("remove_building"), 1)

    def test_a_player_hears_of_each(self):
        self.assertRegex(self.sweep, r"limit = \{ owner = \{ is_player = yes \} \}\s*"
                                     r"save_scope_as = sr_sc_dismantled\s*"
                                     r"owner = \{ post_notification = sr_space_command_dismantled_notice \}")
        # Told before the building goes.
        self.assertLess(self.sweep.index("post_notification"), self.sweep.index("remove_building"))
        messages = _strip(_raw(ROOT / "common/messages/extra_messages.txt"))
        body = _block(messages, "sr_space_command_dismantled_notice")
        self.assertIn("type = country", body)
        self.assertIn("notification_type = feed", body)
        loc = _raw(ROOT / "localization/english/te_notifications_l_english.yml")
        desc = re.search(r'(?m)^ notification_sr_space_command_dismantled_notice_desc:0 "(.*)"$', loc).group(1)
        self.assertIn("[SCOPE.sState('sr_sc_dismantled').GetName]", desc)
        self.assertIn("[SCOPE.sState('sr_sc_keeper').GetName]", desc)
        # The tie goes to the market capital, which needn't have more levels
        # (review of #1287, M2).
        self.assertIn("market capital", desc)
        self.assertNotIn("the one with the most levels", desc)
        for suffix in ("_name", "_tooltip"):
            with self.subTest(key=suffix):
                self.assertRegex(loc, rf"(?m)^ notification_sr_space_command_dismantled_notice{suffix}:0 ")

    def test_a_second_is_refused_at_the_source_and_the_one_held_expands(self):
        """Review of #1287, I2: a new Space Command needs the Space Program and
        no other of a level or more, with the reason shown; the one a country
        has expands where it stands, so an AI that kept an annexed one neither
        stalls at its levels nor re-queues one the sweep removes."""
        building = _block(_strip(_raw(BUILDING)), "building_space_command")
        possible = _block("x = {" + building.split("possible = {", 1)[1], "x")
        self.assertRegex(possible, r"^\s*trigger_if = \{\s*limit = \{ has_building = building_space_command \}\s*always = yes\s*\}\s*"
                                   r"trigger_else = \{\s*has_building = building_space_program\s*"
                                   r"custom_tooltip = \{\s*text = sr_sc_one_per_nation_tt\s*owner \?= \{\s*NOT = \{\s*"
                                   r"any_scope_building = \{\s*is_building_type = building_space_command\s*level >= 1\s*\}\s*\}\s*\}\s*\}\s*\}\s*$")
        loc = _raw(ROOT / "localization/english/te_miscellaneous_l_english.yml")
        self.assertRegex(loc, r'(?m)^ sr_sc_one_per_nation_tt:0 "[^"]+"$')

    def test_no_text_still_promises_a_split(self):
        loc = "\n".join(_raw(p) for p in (ROOT / "localization/english").glob("*.yml"))
        for phrase in ("shared between them", "each building's tooltip shows its share", "keeping the larger"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, loc)


class PauseTest(unittest.TestCase):
    """Pausing Space Command (owner, 2026-10-31): paused, a country builds no
    fleet strength and its yards buy none of their inputs; fleets, the reserve
    and Auto carry on. The AI pauses in default, or in deficit at peace."""

    INPUTS = ("launch_capacity", "advanced_materials", "electricity")

    @classmethod
    def setUpClass(cls):
        cls.effects = _strip(_raw(FLEET_EFFECTS))
        cls.triggers = _strip(_raw(FLEET_TRIGGERS))
        cls.sguis = _strip(_raw(SGUIS))
        cls.earth = _strip(_raw(EARTH_EFFECTS))

    def test_the_toggle_and_its_variable(self):
        self.assertRegex(_block(self.triggers, "sr_sc_is_paused"), r"^\s*has_variable = sr_sc_paused\s*$")
        self.assertRegex(_block(self.triggers, "sr_sc_is_resuming"), r"^\s*has_variable = sr_sc_resume_pending\s*$")
        toggle = _block(self.effects, "sr_sc_toggle_pause")
        # Resuming, a click cancels; paused, it asks to resume; building, it
        # pauses at once. Paused is yes; building is the variable's absence.
        self.assertRegex(toggle, r"^\s*if = \{\s*limit = \{ sr_sc_is_resuming = yes \}\s*remove_variable = sr_sc_resume_pending\s*\}\s*"
                                 r"else_if = \{\s*limit = \{ sr_sc_is_paused = yes \}\s*"
                                 r"set_variable = \{ name = sr_sc_resume_pending value = yes \}\s*\}\s*"
                                 r"else = \{\s*set_variable = \{ name = sr_sc_paused value = yes \}\s*\}\s*"
                                 r"sr_sc_pause_apply = yes\s*$")
        # A click never ends the pause itself: only the step (or the AI's
        # resume, at its step) clears sr_sc_paused.
        self.assertNotIn("remove_variable = sr_sc_paused", toggle)
        self.assertNotIn("sr_sc_clear_pause", toggle)
        sgui = _block(self.sguis, "sr_sc_pause_sgui")
        self.assertIn("always = no", _block("x = {" + sgui.split("ai_is_valid = {", 1)[1], "x"))
        # The tooltip says what each state's click does; the variable is set out of sight.
        self.assertRegex(sgui, r"limit = \{ sr_sc_is_resuming = yes \}\s*custom_tooltip = sr_sc_resume_cancel_tt\s*\}\s*"
                               r"else_if = \{\s*limit = \{ sr_sc_is_paused = yes \}\s*custom_tooltip = sr_sc_resume_tt\s*\}\s*"
                               r"else = \{\s*custom_tooltip = sr_sc_pause_tt\s*\}\s*"
                               r"hidden_effect = \{\s*sr_sc_toggle_pause = yes\s*\}")
        clear = _block(self.effects, "sr_sc_clear_pause")
        for var in ("sr_sc_resume_pending", "sr_sc_paused"):
            with self.subTest(var=var):
                self.assertRegex(clear, rf"limit = \{{ has_variable = {var} \}}\s*remove_variable = {var}")

    def test_a_resume_waits_for_the_step_which_builds_nothing(self):
        """Review of #1287, I1: the build is the month's rate in one lump, so a
        step may build only when the cut was off since the last one. The build
        check comes before the pending resume is cleared, and the cut follows
        after; the other way round, a resume the day before the step would
        build a month the inputs never paid for."""
        month = _block(self.effects, "sr_sc_month")
        build = month.index("limit = { sr_sc_is_paused = yes }")
        resume = re.search(r"if = \{\s*limit = \{ sr_sc_is_resuming = yes \}\s*sr_sc_clear_pause = yes\s*\}", month)
        self.assertIsNotNone(resume, "the step doesn't end a pending resume")
        apply = month.index("sr_sc_pause_apply = yes")
        self.assertLess(build, resume.start())
        self.assertLess(resume.end(), apply)
        # The build reads the variable alone, never the pending resume.
        self.assertEqual(month.count("sr_sc_is_resuming"), 1)
        self.assertEqual(month.count("sr_sc_clear_pause = yes"), 1)
        # Only the step and the AI end a pause.
        everything = "\n".join(_strip(_raw(p)) for d in ("common", "events") for p in (ROOT / d).rglob("*.txt"))
        self.assertEqual(everything.count("sr_sc_clear_pause = yes"), 2)
        self.assertEqual(everything.count("remove_variable = sr_sc_paused"), 1)

    def test_the_month_builds_nothing_while_paused(self):
        month = _block(self.effects, "sr_sc_month")
        gate = re.search(r"if = \{\s*limit = \{ sr_sc_is_paused = yes \}\s*"
                         r"set_variable = \{ name = sr_sc_built_last value = 0 \}\s*\}\s*else = \{", month)
        self.assertIsNotNone(gate, "no paused branch reading Built a month 0")
        build = _block("x = {" + month[gate.end():], "x")
        self.assertIn("value = sr_sc_rate", build)
        self.assertRegex(build, r"limit = \{ local_var:sr_sc_points > 0 \}\s*sr_reserve_build = yes")
        # The month's strength (Space Command's and the Orbital Yards', both in
        # sr_sc_rate) joins the reserve only there.
        rest = month.replace(build, "")
        for name in ("sr_sc_rate", "sr_reserve_build", "sr_mod_units_yard"):
            with self.subTest(name=name):
                self.assertNotIn(name, rest)
        calls = re.findall(r"sr_reserve_build = yes", self.effects + self.earth + _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT)))
        self.assertEqual(len(calls), 1)
        self.assertIn("add = {\n\t\tvalue = sr_mod_units_yard", _block(_strip(_raw(FLEET_VALUES)), "sr_sc_rate"))

    def test_the_panel_reads_paused(self):
        shown = _block(_raw(ROOT / "common/script_values/sr_fleet_display_values.txt"), "sr_disp_sc_paused")
        self.assertRegex(shown, r"if = \{ limit = \{ sr_sc_is_paused = yes \} value = 1 \}\s*"
                                r"if = \{ limit = \{ sr_sc_is_resuming = yes \} value = 2 \}")
        gui = _raw(ROOT / "gui/journal_entry_widgets/space_race_widget.gui")
        section = _block(gui.replace("\ttype te_sr_sec_space_command = flowcontainer", "te_sr_sec_space_command ="),
                         "te_sr_sec_space_command")
        def state(cmp, n):
            return f"[{cmp}_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_sc_paused'), '(CFixedPoint){n}' )]\""
        for key, shown_on in (("je_space_race_widget_sc_rate_figure", state("EqualTo", 0)),
                              ("je_space_race_widget_sc_rate_paused", state("GreaterThanOrEqualTo", 1)),
                              ("je_space_race_widget_sc_pause", state("EqualTo", 0)),
                              ("je_space_race_widget_sc_resume", state("EqualTo", 1)),
                              ("je_space_race_widget_sc_resuming", state("EqualTo", 2))):
            with self.subTest(key=key):
                i = section.index(f'text = "{key}"')
                self.assertIn(shown_on, _block_around(section, i, 2))
        self.assertEqual(section.count("GetScriptedGui('sr_sc_pause_sgui').Execute("), 3)
        # Each row's hover is its own (review of #1287, M6).
        for figure, hover in (("je_space_race_widget_sc_rate_figure", "je_space_race_widget_sc_rate_tt"),
                              ("je_space_race_widget_sc_rate_paused", "je_space_race_widget_sc_rate_paused_tt")):
            with self.subTest(row=figure):
                row = _block_around(section, section.index(f'text = "{figure}"'), 2)
                self.assertIn(f'tooltip = "{hover}"', row)

    def test_the_modifier_cuts_the_yards_inputs(self):
        body = _block(_strip(_raw(STATIC)), "sr_space_command_paused")
        self.assertEqual(re.findall(r"(\w+) = (\S+)", body)[1:],
                         [(f"goods_input_{g}_mult", "-1") for g in self.INPUTS])
        # The three are every workforce-scaled input of every yard method, and
        # none is the maintenance line's (the upkeep stays).
        text = _strip(_raw(METHODS))
        for m in re.finditer(r"(?m)^(pm_sr_space_command_\w+) = \{", text):
            body = _block(text, m.group(1))
            at = body.index("workforce_scaled = {")
            self.assertLess(body.index("building_modifiers = {"), at)
            self.assertLess(at, body.index("state_modifiers = {"))
            scaled = _block(body[at:], "workforce_scaled")
            with self.subTest(method=m.group(1)):
                goods = set(re.findall(r"goods_input_(\w+)_add", scaled))
                self.assertTrue(goods)
                self.assertLessEqual(goods, set(self.INPUTS))
        self.assertFalse(set(self.INPUTS) & set(UpkeepTest.LINE))

    def test_one_apply_site_removed_first(self):
        everything = "\n".join(_strip(p.read_text(encoding="utf-8-sig"))
                               for d in ("common", "events") for p in (ROOT / d).rglob("*.txt"))
        self.assertEqual(everything.count("add_modifier = { name = sr_space_command_paused"), 1)
        apply = _block(self.effects, "sr_sc_pause_apply")
        self.assertIn("is_building_type = building_space_command", apply)
        self.assertLess(apply.index("remove_modifier = sr_space_command_paused"), apply.index("add_modifier"))
        self.assertRegex(apply, r"limit = \{\s*level >= 1\s*root = \{ sr_sc_is_paused = yes \}\s*\}\s*"
                                r"add_modifier = \{ name = sr_space_command_paused \}")
        # Three callers: the monthly step, the toggle and the AI's resume.
        self.assertEqual(everything.count("sr_sc_pause_apply = yes"), 3)
        for caller in ("sr_sc_month", "sr_sc_toggle_pause", "sr_sc_ai_pause_review"):
            with self.subTest(caller=caller):
                self.assertEqual(_block(self.effects, caller).count("sr_sc_pause_apply = yes"), 1)
        # The toggle's callers: the button and the AI's pause.
        self.assertEqual(everything.count("sr_sc_toggle_pause = yes"), 2)
        self.assertEqual(_block(self.effects, "sr_sc_ai_pause_review").count("sr_sc_toggle_pause = yes"), 1)
        # A building modifier, never the country's.
        self.assertIn('"sr_space_command_paused": "a Space Command building"',
                      _raw(ROOT / "scripts/generators/gen_nation_tab.py"))

    def test_the_cut_reaches_every_state_s_space_command(self):
        """Review of #1287, M6: every state the country owns, an occupied one's
        included (it buys its inputs while its staff work), so the walk has
        no other limit."""
        apply = _block(self.effects, "sr_sc_pause_apply")
        self.assertRegex(apply, r"^\s*every_scope_state = \{\s*limit = \{ has_building = building_space_command \}\s*"
                                r"every_scope_building = \{\s*limit = \{ is_building_type = building_space_command \}")
        self.assertNotIn("sr_state_held_by_owner", apply)

    def test_the_texts_exist(self):
        """Review of #1287, M6: the hovers and the modifier's description,
        each with text (loc_coverage doesn't read custom tooltips' keys)."""
        loc = "\n".join(_raw(p) for p in (ROOT / "localization/english").glob("*.yml"))
        for key in ("sr_sc_pause_tt", "sr_sc_resume_tt", "sr_sc_resume_cancel_tt", "sr_space_command_paused",
                    "sr_space_command_paused_desc", "je_space_race_widget_sc_rate_paused_tt",
                    "je_space_race_widget_sc_pause", "je_space_race_widget_sc_resume", "je_space_race_widget_sc_resuming"):
            with self.subTest(key=key):
                m = re.search(rf'(?m)^ {key}:0 "(.*)"$', loc)
                self.assertIsNotNone(m, f"no {key}")
                self.assertTrue(m.group(1).strip(), f"{key} is empty")
        # The resume's hover says it waits and a click cancels.
        resume = re.search(r'(?m)^ sr_sc_resume_tt:0 "(.*)"$', loc).group(1)
        self.assertIn("next month's construction", resume)
        self.assertIn("cancels", resume)

    def test_the_ai_pauses_under_fiscal_stress(self):
        should = _block(self.triggers, "sr_sc_ai_should_pause")
        self.assertRegex(should, r"^\s*OR = \{\s*in_default = yes\s*AND = \{\s*net_fixed_income < 0\s*"
                                 r"is_at_war = no\s*\}\s*\}\s*$")
        # The same fiscal terms the AI builds Space Command on, turned round.
        build = _block(self.triggers, "sr_sc_may_build_government")
        self.assertIn("in_default = no", build)
        self.assertIn("net_fixed_income > 0", build)

    def test_the_ai_resumes_out_of_it_six_months_on(self):
        resume = _block(self.triggers, "sr_sc_ai_may_resume")
        self.assertRegex(resume, r"^\s*in_default = no\s*OR = \{\s*net_fixed_income > 0\s*is_at_war = yes\s*\}\s*"
                                 r"NOT = \{ has_variable = sr_sc_pause_hold \}\s*$")
        review = _block(self.effects, "sr_sc_ai_pause_review")
        self.assertRegex(review, r"limit = \{\s*NOT = \{ sr_sc_is_paused = yes \}\s*sr_has_space_command = yes\s*"
                                 r"sr_sc_ai_should_pause = yes\s*\}\s*"
                                 r"sr_sc_toggle_pause = yes\s*"
                                 r"set_variable = \{ name = sr_sc_pause_hold value = yes months = 6 \}\s*\}\s*"
                                 r"else_if = \{\s*limit = \{\s*sr_sc_is_paused = yes\s*sr_sc_ai_may_resume = yes\s*\}\s*"
                                 r"sr_sc_clear_pause = yes\s*sr_sc_pause_apply = yes\s*\}\s*$")
        # The hold is the AI's alone, on the country (not a container: a timed
        # variable there runs down).
        everything = "\n".join(_strip(_raw(p)) for p in (ROOT / "common").rglob("*.txt"))
        self.assertEqual(everything.count("name = sr_sc_pause_hold"), 1)
        # In the AI branch of the country's month, after its construction.
        month = _block(self.effects, "sr_fl_country_month")
        self.assertRegex(month, r"limit = \{ is_ai = yes \}\s*sr_fl_ai_review = yes\s*sr_sc_ai_pause_review = yes\s*\}")
        self.assertLess(month.index("sr_sc_month = yes"), month.index("sr_sc_ai_pause_review = yes"))

    def test_orders_the_reserve_and_auto_are_untouched(self):
        generated = _strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT))
        bodies = {
            "sr_sc_operational": _block(self.triggers, "sr_sc_operational"),
            "sr_reserve_may_launch": _block(self.triggers, "sr_reserve_may_launch"),
            "sr_reserve_auto_on": _block(self.triggers, "sr_reserve_auto_on"),
            "sr_reserve_launch": _block(self.earth, "sr_reserve_launch"),
            "sr_reserve_auto_step": _block(self.earth, "sr_reserve_auto_step"),
            "sr_reserve_toggle_auto": _block(self.earth, "sr_reserve_toggle_auto"),
            "sr_fl_1_may_depart_mars": _block(generated, "sr_fl_1_may_depart_mars"),
        }
        for name, body in bodies.items():
            with self.subTest(name=name):
                self.assertNotIn("sr_sc_paused", body)
                self.assertNotIn("sr_sc_is_paused", body)
        # Auto's step runs every month, paused or not.
        month = _block(self.effects, "sr_sc_month")
        self.assertTrue(month.rstrip().endswith("\n\tsr_sc_pause_apply = yes\n\tsr_reserve_auto_step = yes"))
        for lim in _enclosing_limits(month, month.index("sr_reserve_auto_step = yes")):
            self.assertNotIn("sr_sc_is_paused", lim)
        # Only Space Command's own month, its panel, its button and the AI read it.
        readers = set()
        for path in (ROOT / "common").rglob("*.txt"):
            if "sr_sc_is_paused = yes" in _strip(_raw(path)):
                readers.add(path.name)
        self.assertEqual(readers, {"sr_fleet_effects.txt", "sr_fleet_sguis.txt", "sr_fleet_display_values.txt"})


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
        self.assertIn("sr_icpt_rebuild = yes", _block(self.generated, "sr_fl_set_target_at"))
        self.assertIn("sr_icpt_rebuild = yes", _block(self.combat, "sr_fl_set_posture_at"))

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
        """No AI order sets Interdict: only the posture buttons and the console
        do, and the AI calls neither (design § 14)."""
        texts = {"hand": self.combat + _strip(_raw(FLEET_EFFECTS)), "generated": self.generated}
        for label, text in texts.items():
            with self.subTest(file=label):
                setters = [m.start() for m in re.finditer(r"_posture value = 4 \}", text)]
                owners = {re.findall(r"(?m)^(\w+) = \{", text[:i])[-1] for i in setters}
                self.assertLessEqual(owners, {"sr_fl_set_posture_at", "sr_fl_debug_icpt_at"})
        ai = ""
        for text in (self.generated, self.combat, _strip(_raw(FLEET_EFFECTS))):
            names = re.findall(r"(?m)^(sr_fl_ai_\w+) = \{", text)
            self.assertTrue(names)
            ai += "".join(_block(text, name) for name in names)
        self.assertNotIn("set_posture", ai)
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
                         r"limit = \{ is_at_war = yes sr_sc_operational = yes \}\s*sr_fl_ai_lunar_assault = yes\s*sr_fl_ai_attack_all = yes\s*"
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
        for line in ("limit = { has_variable = sr_fl_at_earth }", "value = sr_fl_at_earth_ready",
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
        cls.sites = _strip(_raw(gss.ROOT / gss.EFFECTS_OUT))
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
        # The posture line is shown at Earth only while a lunar world there may be
        # closed in on (the buttons' Earth rules: test_earth_offers_station_and_close_in_only).
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                combat = _block(self.display, f"sr_disp_fl_{n}_combat")
                self.assertIn(f"else_if = {{ limit = {{ sr_fl_{n}_at_earth = yes sr_fl_{n}_has_hostile_world = yes }} value = 1 }}",
                              combat)
                hostile = _block(self.gen_triggers, f"sr_fl_{n}_has_hostile_world")
                earth_line = next(line for line in hostile.splitlines() if f"var:sr_fl_{n}_loc = 1 " in line)
                self.assertEqual(re.findall(r"sr_site_hostile_target = \{ KEY = (\w+) \}", earth_line),
                                 [w.key for w in self.lunar])
        # Close in's first target at Earth is a lunar world (the hostile step).
        hostile_step = _block(self.generated, "sr_fl_step_hostile_target_at")
        earth_case = _block("x = {" + hostile_step.split("limit = { var:sr_fl_$N$_loc = 1 }", 1)[1], "x")
        self.assertEqual(sorted(set(re.findall(r"sr_site_hostile_target = \{ KEY = (\w+) \}", earth_case))),
                         sorted(w.key for w in self.lunar))

    def test_earth_offers_station_and_close_in_only(self):
        """The posture buttons (UI pass design § 7) under Earth's own rules:
        never Stand off or Interdict there; Close in on a hostile world here,
        whose Earth arm is the lunar worlds (checked above)."""
        sgui = _block(_strip(_raw(SGUIS)), "sr_fleet_set_posture_sgui")
        valid = _block("x = {" + sgui.split("\n\tis_valid = {", 1)[1], "x")
        opener = r"(?m)^\t\ttrigger_if = \{\s*limit = \{\s*scope:pick = (\d)(\s*sr_fl_op_check = \{ TEST = at_earth \})?\s*\}"
        rules = {int(m.group(1)): _block("x = {" + valid[m.end():], "x") for m in re.finditer(opener, valid)}
        at_earth_only = {int(m.group(1)) for m in re.finditer(opener, valid) if m.group(2)}
        self.assertEqual(sorted(rules), [2, 3, 4])
        # Stand off's rule applies at Earth alone, where it fails
        self.assertEqual(at_earth_only, {2})
        self.assertIn("NOT = { sr_fl_op_check = { TEST = at_earth } }", rules[2])
        self.assertIn("NOT = { sr_fl_op_check = { TEST = at_earth } }", rules[4])
        self.assertIn("sr_fl_op_check = { TEST = has_interdict_world }", rules[4])
        self.assertIn("sr_fl_op_check = { TEST = has_hostile_world }", rules[3])
        self.assertNotIn("at_earth", rules[3])
        # Earth's own words for Station and Close in.
        effect = _block("x = {" + sgui.split("\n\teffect = {", 1)[1], "x")
        for p in (1, 3):
            with self.subTest(posture=p):
                self.assertRegex(effect, rf"limit = \{{ sr_fl_op_check = \{{ TEST = at_earth \}} \}}\s*"
                                         rf"custom_tooltip = sr_fl_set_posture_{p}_earth_tt")

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
        self.assertNotIn("sr_site_interdicted_", lunar_step)
        self.assertNotIn("sr_icpt", _block(self.display, "sr_disp_loc_status_earth"))

    def test_nothing_reads_a_lunar_world_s_interdiction(self):
        """#1243: nothing sets sr_site_interdicted_<lunar key>, so any read of one is logged
        at load as never set. The Defense lists, the colony's status and its release skip it;
        every other world keeps it."""
        lunar = re.compile(r"sr_site_interdicted_(%s)\b" % "|".join(w.key for w in self.lunar))
        for path in sorted(p for d in ("common", "events", "gui") for p in (ROOT / d).rglob("*")
                           if p.suffix in (".txt", ".gui")):
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertIsNone(lunar.search(_strip(_raw(path))))
        for w in self.lunar:
            with self.subTest(site=w.key):
                self.assertNotIn("value = 4", _block(self.display, f"sr_disp_def_status_{w.key}"))
        others = [w for w in gss.SITES if w not in self.lunar]
        self.assertTrue(others)
        for w in others:
            with self.subTest(site=w.key):
                self.assertIn(f"has_global_variable = sr_site_interdicted_{w.key} }} value = 4",
                              _block(self.display, f"sr_disp_def_status_{w.key}"))
                self.assertIn(f"sr_site_interdicted_{w.key}", _block(self.sites, f"sr_site_release_{w.key}"))

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
        # First the target: the enemy's lunar world of most people and modules,
        # never a free one, only with no enemy fleet at Earth at all (any
        # stationed one bars the seizure).
        gate = "limit = { NOT = { sr_earth_hostile_present = yes } }"
        guarded = _block("x = {" + lunar.split(gate, 1)[1], "x")
        for w in self.lunar:
            with self.subTest(site=w.key):
                self.assertIn(f"sr_site_ai_lunar_target = {{ KEY = {w.key} }} sr_site_ai_worth_{w.key} > local_var:sr_ai_best",
                              guarded)
                self.assertIn(f"set_local_variable = {{ name = sr_ai_need value = sr_site_garrison_need_{w.key} }}", guarded)
        self.assertEqual(len(re.findall(r"sr_site_ai_lunar_target = \{ KEY = (\w+) \}", lunar)), len(self.lunar))
        self.assertIn("sr_cb_hs_value <= 0", _block(self.triggers, "sr_cb_seizes"))
        # Then the fleet: the strongest at Earth whose marines exceed that world's
        # garrison and militia, picked only once a target is.
        pick = _block("x = {" + lunar.split("limit = { local_var:sr_ai_tgt > 0 }", 1)[1], "x")
        self.assertLess(lunar.index(gate), lunar.index("limit = { local_var:sr_ai_tgt > 0 }"))
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                self.assertIn(f"limit = {{ sr_fl_{n}_at_earth = yes sr_fl_{n}_marines_value > local_var:sr_ai_need "
                              f"sr_fl_{n}_strength > local_var:sr_fl_best }}", pick)
                self.assertRegex(lunar, rf"limit = \{{ local_var:sr_fl_n = {n} \}}\s*"
                                        rf"set_variable = \{{ name = sr_fl_{n}_posture value = 3 \}}\s*"
                                        rf"set_variable = \{{ name = sr_fl_{n}_target value = local_var:sr_ai_tgt \}}")
                self.assertIn(f"remove_variable = sr_fl_{n}_destroy", lunar)
                # Every other fleet at Earth (all, with no target or no fleet with
                # the marines) stays stationed.
                self.assertRegex(lunar, rf"else = \{{\s*set_variable = \{{ name = sr_fl_{n}_posture value = 1 \}}")
        self.assertNotIn("_destroy value", lunar)
        self.assertNotIn("posture value = 2", lunar)
        target = _block(self.triggers, "sr_site_ai_lunar_target")
        self.assertIn("sr_site_ai_attack_target = { KEY = $KEY$ }", target)
        self.assertIn("global_var:sr_site_holder_$KEY$ ?= { sr_earth_blockaded = yes }", target)
        self.assertIn("global_var:sr_site_occupier_$KEY$ ?= { sr_earth_blockaded = yes }", target)
        # The offence's dispatch and the garrisons leave a fleet closing in at Earth where it is.
        attack_all = _block(self.generated, "sr_fl_ai_attack_all")
        garrisons = _block(self.generated, "sr_fl_ai_send_garrisons")
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                self.assertEqual(attack_all.count(f"NOT = {{ sr_fl_{n}_closing_at_earth = yes }}"), len(gsf.LOCATIONS) - 1)
                self.assertEqual(garrisons.count(f"sr_fl_{n}_may_depart_"), len(gsf.LOCATIONS) - 1)
                self.assertEqual(garrisons.count(f"NOT = {{ sr_fl_{n}_closing_at_earth = yes }}"), len(gsf.LOCATIONS) - 1)
                self.assertEqual(_block(self.gen_triggers, f"sr_fl_{n}_closing_at_earth").strip(),
                                 f"sr_fl_{n}_at_earth = yes sr_fl_{n}_posture_value = 3")

    def test_a_free_colony_s_price_only_while_closing_in(self):
        """Review of #1237: the Target button of a stationed fleet (at Earth, a
        free lunar colony makes it show at peace) charges nothing; closing in
        charges once per target, and the hover's price line shows only then."""
        step = _block(self.generated, "sr_fl_step_hostile_target_at")
        found = _block("x = {" + step.split("limit = { local_var:sr_fl_next > 0 }", 1)[1], "x")
        self.assertIn("if = { limit = { sr_fl_$N$_posture_value = 3 } sr_fl_charge_free_at = { N = $N$ } }", found)
        self.assertEqual(step.count("sr_fl_charge_free_at"), 1)
        # Entering Close in charges after the posture is set (the hostile step's
        # own charge then finds it charged: sr_fl_<n>_charged holds the world).
        posture = _block(self.combat, "sr_fl_set_posture_at")
        branches = posture.split("set_variable = { name = sr_fl_$N$_posture value = 3 }")[1:]
        self.assertEqual(len(branches), 1)
        for branch in branches:
            self.assertIn("sr_fl_charge_free_at = { N = $N$ }", branch[:branch.index("else")])
        self.assertIn("NOT = { var:sr_fl_$N$_charged = $INDEX$ }", _block(self.combat, "sr_cb_charge_free"))
        custom = _strip(_raw(gsf.ROOT / gsf.CUSTOM_LOC_OUT))
        loc = _raw(ROOT / "localization/english/te_journal_entries_l_english.yml")
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                price = _block(custom, f"sr_fl_{n}_target_price")
                self.assertRegex(price, rf"trigger = \{{ sr_fl_{n}_posture_value = 3 \}}\s*"
                                        r"localization_key = sr_fl_target_free_price_tt")
                self.assertIn("localization_key = te_tt_blank", price)
                hover = re.search(rf"(?m)^ je_space_race_widget_fl_{n}_target_tt:0 \"(.*)\"$", loc).group(1)
                self.assertTrue(hover.endswith(f"[JournalEntry.GetCountry.GetCustom('sr_fl_{n}_target_price')]"))

    def test_orbital_superiority_counts_a_fleet_closing_in_at_earth(self):
        """§ 8.5: the margin reads sr_fl_at_earth, which counts every slot at
        Earth whatever its posture."""
        note = _block(self.generated, "sr_fl_note_at")
        self.assertIn("sr_loc_add_present = { LOC = earth }", note)
        self.assertNotIn("posture", note)
        self.assertNotIn("posture", _block(_strip(_raw(FLEET_EFFECTS)), "sr_loc_add_present"))
        values = _strip(_raw(FLEET_VALUES))
        self.assertIn("value = sr_fl_at_earth_ready", _block(values, "sr_orbital_superiority_margin"))
        self.assertIn("value = var:sr_fl_at_earth", _block(values, "sr_fl_at_earth_ready"))


class EarthAlertTest(unittest.TestCase):
    """The Earth alert (UI pass design § 9): a quiet notice for every hostile
    fleet leg bound for Earth, a loud one for a leg that would change something,
    each once per leg and per volume, recorded on the moving fleet."""

    @classmethod
    def setUpClass(cls):
        cls.generated = _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT))
        cls.values = _strip(_raw(gsf.ROOT / gsf.VALUES_OUT))
        cls.fleet = _strip(_raw(FLEET_EFFECTS))
        cls.triggers = _strip(_raw(FLEET_TRIGGERS))
        cls.events = _strip(_raw(SPACE_RACE_EVENTS))
        cls.step = _block(cls.generated, "sr_earth_alert_step")

    def _bound(self, n, code):
        return f"has_variable = sr_fl_{n}_dest var:sr_fl_{n}_dest = {code} NOT = {{ has_variable = sr_fl_{n}_loc }}"

    def test_only_powers_at_war_count(self):
        for lc in gsf.LOCATIONS:
            for name in (f"sr_loc_hostile_inbound_count_{lc.key}", f"sr_loc_hostile_inbound_strength_{lc.key}",
                         f"sr_loc_hostile_inbound_first_{lc.key}"):
                with self.subTest(value=name):
                    body = _block(self.values, name)
                    self.assertIn("variable = sr_fleet_powers", body)
                    self.assertIn("has_war_with = prev", body)
                    for n in range(1, gsf.SLOTS + 1):
                        self.assertIn(self._bound(n, lc.code), body)
        self.assertIn("variable = sr_fleet_powers", self.step)
        self.assertIn("has_war_with = scope:sr_alert_viewer", self.step)

    def _heard(self, n, volume):
        return f"is_target_in_variable_list = {{ name = sr_fl_{n}_warned_{volume} target = scope:sr_alert_viewer }}"

    def _passes(self):
        """The step's two walks over the powers: the first for the popup, the
        second for everything else."""
        self.assertEqual(self.step.count("variable = sr_fleet_powers"), 2)
        second = self.step.index("variable = sr_fleet_powers", self.step.index("variable = sr_fleet_powers") + 1)
        return self.step[:second], self.step[second:]

    def _arm(self, text, n):
        arm = text[text.index(self._bound(n, gsf.EARTH)):]
        if n < gsf.SLOTS:
            arm = arm[:arm.index(self._bound(n + 1, gsf.EARTH))]
        return arm

    def test_once_per_leg_and_volume(self):
        self.assertEqual(gsf.SLOT_LISTS, ("warned_quiet", "warned_loud"))
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                self.assertIn(self._bound(n, gsf.EARTH), self.step)
                for lst in gsf.SLOT_LISTS:
                    name = f"sr_fl_{n}_{lst}"
                    self.assertIn(f"is_target_in_variable_list = {{ name = {name} target = scope:sr_alert_viewer }}", self.step)
                    self.assertIn(f"add_to_variable_list = {{ name = {name} target = scope:sr_alert_viewer }}", self.step)
        # A new leg, a landing and an emptied slot start the record over.
        for lst in gsf.SLOT_LISTS:
            with self.subTest(list=lst):
                clear = f"clear_variable_list = sr_fl_$N$_{lst}"
                self.assertIn(clear, _block(self.fleet, "sr_fl_dispatch"))
                self.assertIn(clear, _block(self.fleet, "sr_fl_arrive_at"))
                self.assertIn(clear, _block(self.generated, "sr_fl_clear_at"))

    def test_the_loud_test_and_the_month_s_flag_are_read_before_the_walks(self):
        first_walk = self.step.index("every_in_global_list")
        self.assertLess(self.step.index("if = { limit = { sr_earth_alert_loud = yes } set_local_variable = { name = sr_earth_loud value = 1 } }"),
                        first_walk)
        self.assertLess(self.step.index("set_local_variable = { name = sr_earth_loud_sent value = 0 }"), first_walk)

    def test_the_first_pass_gives_the_popup_to_a_fleet_nobody_was_told_of(self):
        """I1 (#1280 review): the popup names a loud fleet not yet heard of at
        either volume, ahead of one heard quietly before."""
        first, _ = self._passes()
        self.assertNotIn("post_notification", first)
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                arm = self._arm(first, n)
                limit = (f"limit = {{ local_var:sr_earth_loud = 1 local_var:sr_earth_loud_sent = 0 {self._bound(n, gsf.EARTH)} "
                         f"NOT = {{ {self._heard(n, 'loud')} }} NOT = {{ {self._heard(n, 'quiet')} }} }}")
                self.assertIn(limit, first)
                for lst in gsf.SLOT_LISTS:
                    self.assertIn(f"add_to_variable_list = {{ name = sr_fl_{n}_{lst} target = scope:sr_alert_viewer }}", arm)
                self._assert_popup(arm, n)

    def _assert_popup(self, arm, n):
        """The popup marks the month sent before anything else, keeps the
        fleet's landing, and sets the viewer's variables in the viewer's scope."""
        self.assertRegex(arm, r"set_local_variable = \{ name = sr_earth_loud_sent value = 1 \}\s*"
                              rf"set_local_variable = \{{ name = sr_earth_alert_arr value = var:sr_fl_{n}_arrive \}}\s*"
                              r"scope:sr_alert_viewer = \{\s*"
                              r"set_variable = \{ name = sr_earth_alert_by value = prev \}\s*"
                              r"set_variable = \{ name = sr_earth_alert_arrive value = local_var:sr_earth_alert_arr \}\s*"
                              r"trigger_event = \{ id = space_race_events\.111 days = 1 \}\s*\}")

    def test_the_second_pass(self):
        """Loud first: the popup if the month has none yet (marking the quiet
        volume heard too), else the feed notice for a fleet not yet told
        quietly. Quiet only for a fleet whose landing changes nothing."""
        _, second = self._passes()
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                arm = self._arm(second, n)
                loud = arm.index(f"limit = {{ local_var:sr_earth_loud = 1 NOT = {{ {self._heard(n, 'loud')} }} }}")
                sent = arm.index("limit = { local_var:sr_earth_loud_sent = 0 }")
                quiet = arm.index(f"limit = {{ local_var:sr_earth_loud = 0 NOT = {{ {self._heard(n, 'quiet')} }} }}")
                self.assertLess(loud, sent)
                self.assertLess(sent, quiet)
                self.assertIn(f"add_to_variable_list = {{ name = sr_fl_{n}_warned_loud target = scope:sr_alert_viewer }}", arm[loud:sent])
                popup = arm[sent:quiet]
                self.assertIn(f"if = {{ limit = {{ NOT = {{ {self._heard(n, 'quiet')} }} }} "
                              f"add_to_variable_list = {{ name = sr_fl_{n}_warned_quiet target = scope:sr_alert_viewer }} }}", popup)
                self._assert_popup(popup, n)
                # A folded fleet not yet told quietly gets the feed notice.
                folded = popup[popup.index("else_if"):]
                self.assertIn(f"limit = {{ NOT = {{ {self._heard(n, 'quiet')} }} }}", folded)
                self._assert_feed(folded, n)
                self.assertIn("else_if", arm[loud:quiet])
                self._assert_feed(arm[quiet:], n)

    def _assert_feed(self, text, n):
        self.assertRegex(text, rf"add_to_variable_list = \{{ name = sr_fl_{n}_warned_quiet target = scope:sr_alert_viewer \}}\s*"
                               r"save_scope_as = sr_earth_alert_power\s*"
                               r"scope:sr_alert_viewer = \{ post_notification = sr_earth_hostile_notice \}")

    def test_the_popup_s_variables_are_cleared_after(self):
        body = _block(self.events, "space_race_events.111")
        self.assertIn("remove_variable = sr_earth_alert_arrive", body)
        self.assertIn("remove_variable = sr_earth_alert_by", body)

    def test_the_first_landing_is_a_running_minimum(self):
        """From a 99999 ceiling, each leg in flight caps it at its landing
        month: the earliest."""
        display = _strip(_raw(gsf.ROOT / gsf.DISPLAY_OUT))
        for name, text in ((f"sr_loc_hostile_inbound_first_{lc.key}", self.values) for lc in gsf.LOCATIONS):
            with self.subTest(value=name):
                body = _block(text, name)
                self.assertIn("value = 99999", body)
                for n in range(1, gsf.SLOTS + 1):
                    self.assertIn(f"max = var:sr_fl_{n}_arrive", body)
        body = _block(display, "sr_disp_earth_power_months")
        self.assertLess(body.index("value = 99999"), body.index("max = var:sr_fl_1_arrive"))
        for n in range(1, gsf.SLOTS + 1):
            self.assertIn(f"if = {{ limit = {{ {self._bound(n, gsf.EARTH)} }} max = var:sr_fl_{n}_arrive }}", body)
        self.assertIn("subtract = te_history_month_index", body)

    def test_the_hover_has_a_line_a_power(self):
        """I2 (#1280 review): the cell's hover names each power with a fleet
        in flight to Earth, its figures read in its own scope."""
        display = _strip(_raw(gsf.ROOT / gsf.DISPLAY_OUT))
        for name in ("sr_disp_earth_power_count", "sr_disp_earth_power_strength"):
            with self.subTest(value=name):
                body = _block(display, name)
                for n in range(1, gsf.SLOTS + 1):
                    self.assertIn(f"if = {{ limit = {{ {self._bound(n, gsf.EARTH)} }}", body)
        self.assertIn("add = sr_fl_1_strength", _block(display, "sr_disp_earth_power_strength"))
        lst = _block(self.generated, "sr_ov_list_earth")
        self.assertIn("variable = sr_fleet_powers", lst)
        self.assertRegex(lst, r"limit = \{\s*is_country_alive = yes\s*has_war_with = root\s*OR = \{")
        for n in range(1, gsf.SLOTS + 1):
            self.assertIn(f"AND = {{ {self._bound(n, gsf.EARTH)} }}", lst)
        self.assertIn("custom_tooltip = je_space_race_widget_ovc_earth_line", lst)
        sgui = _block(_strip(_raw(ROOT / "common/scripted_guis/sr_colony_sguis.txt")), "sr_colony_overview_sgui")
        self.assertRegex(sgui, r"limit = \{ exists = scope:op scope:op = 3 \}\s*sr_ov_list_earth = yes")
        loc = _raw(ROOT / "localization/english/te_journal_entries_l_english.yml")
        tt = re.search(r"(?m)^ je_space_race_widget_ovc_earth_tt:0 \"(.*)\"$", loc).group(1)
        self.assertIn("ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)3' ) ).End )", tt)
        line = re.search(r"(?m)^ je_space_race_widget_ovc_earth_line:0 \"(.*)\"$", loc).group(1)
        self.assertIn("[THIS.GetCountry.GetName]", line)
        for name in ("count", "strength", "months"):
            self.assertIn(f"[THIS.ScriptValue('sr_disp_earth_power_{name}')|0]", line)

    def test_the_cell_s_state(self):
        """0 none, 1 some, 2 loud: the loud test only counts with a fleet in flight."""
        body = _block(_strip(_raw(gsf.ROOT / "common/script_values/sr_fleet_display_values.txt")), "sr_disp_earth_hostile")
        self.assertRegex(body, r"limit = \{ sr_loc_hostile_inbound_count_earth > 0 \}\s*value = 1\s*"
                               r"if = \{ limit = \{ sr_earth_alert_loud = yes \} value = 2 \}")

    def test_the_quiet_notice_is_a_bad_feed_message(self):
        messages = _strip(_raw(gsf.ROOT / "common" / "messages" / "extra_messages.txt"))
        body = _block(messages, "sr_earth_hostile_notice")
        self.assertIn("type = country", body)
        self.assertIn("notification_type = feed", body)
        self.assertIn("color = bad", body)

    def test_the_loud_test(self):
        """A landing tips the balance: no fleet of ours at Earth and no
        blockade already, or ours holds against what is there now but not
        against that and the inbound together."""
        loud = _block(self.triggers, "sr_earth_alert_loud")
        self.assertIn("sr_loc_hostile_inbound_strength_earth > 0", loud)
        self.assertRegex(loud, r"AND = \{\s*NOT = \{ has_variable = sr_fl_at_earth \}\s*NOT = \{ sr_earth_blockaded = yes \}\s*\}")
        self.assertRegex(loud, r"AND = \{\s*has_variable = sr_fl_at_earth\s*"
                               r"sr_fl_at_earth_ready >= sr_loc_ai_enemy_fleets_earth\s*"
                               r"sr_earth_hostile_total > sr_fl_at_earth_ready\s*\}")
        total = _block(_strip(_raw(FLEET_VALUES)), "sr_earth_hostile_total")
        self.assertIn("value = sr_loc_hostile_inbound_strength_earth", total)
        self.assertIn("add = sr_loc_ai_enemy_fleets_earth", total)

    def test_the_loud_notice_has_106_s_shape(self):
        body = _block(self.events, "space_race_events.111")
        self.assertIn("type = country_event", body)
        self.assertIn("event_image", body)
        self.assertIn("trigger = { has_variable = sr_earth_alert_by }", body)
        self.assertIn("remove_variable = sr_earth_alert_by", body)
        self.assertIn("default_option = yes", body)

    def test_the_step_runs_beside_the_blockade_notice(self):
        on = _strip(_raw(ON_ACTIONS))
        self.assertRegex(on, r"sr_earth_notice_step = yes\s*sr_earth_alert_step = yes")

class ReadinessTest(unittest.TestCase):
    """Half fire without a Space Command (owner, 2026-10-31): a country with no
    Space Command level in a state it controls fires at half strength on
    fleets and on colony Defences, and its fleets at Earth weigh half in
    orbital fire support and the Earth alert. Losses, the battlestation, the
    batteries, the panel and the AI's estimates are unchanged."""

    @classmethod
    def setUpClass(cls):
        cls.values = _strip(_raw(FLEET_VALUES))
        cls.combat = _strip(_raw(COMBAT_EFFECTS))
        cls.triggers = _strip(_raw(FLEET_TRIGGERS))

    def test_the_value(self):
        self.assertEqual(_number(_raw(FLEET_VALUES), "sr_fleet_readiness_grounded"), 0.5)
        body = _block(self.values, "sr_fleet_readiness")
        self.assertRegex(body, r"^\s*value = 1\s*if = \{\s*limit = \{ NOT = \{ sr_sc_operational = yes \} \}\s*"
                               r"value = sr_fleet_readiness_grounded\s*\}\s*$")

    def test_both_fire_locals_take_it_beside_quality(self):
        gather = _block(self.combat, "sr_fl_gather_at")
        self.assertIn("set_local_variable = { name = sr_cb_f value = { value = sr_fl_$N$_fire_fleets "
                      "multiply = sr_fleet_quality multiply = sr_fleet_readiness } }", gather)
        target = _block(self.combat, "sr_cb_add_target")
        self.assertRegex(target, r"name = sr_cb_fd\s*value = \{\s*value = sr_fl_\$N\$_fire_defences\s*"
                                 r"multiply = sr_fleet_quality\s*multiply = sr_fleet_readiness\s*multiply = sr_cb_edge_\$KEY\$")
        # Read in the fleet's owner's scope, as sr_fleet_quality is: the gather
        # runs inside the fleet powers' walk.
        at = _block(self.combat, "sr_combat_at")
        self.assertRegex(at, r"every_in_global_list = \{\s*variable = sr_fleet_powers\s*limit = \{ is_country_alive = yes \}\s*"
                             r"sr_cb_clear_\$LOC\$ = yes\s*if = \{\s*limit = \{ has_variable = sr_fl_at_\$LOC\$ \}\s*"
                             r"sr_fl_each_slot = \{ DO = gather \}")

    def test_only_the_fleets_fire_is_halved(self):
        """The battlestation and the batteries are buildings: their fire and
        every loss are as before."""
        everything = self.combat + self.values + _strip(_raw(EARTH_EFFECTS)) + _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT)) \
            + _strip(_raw(gsf.ROOT / gsf.VALUES_OUT))
        self.assertEqual(everything.count("multiply = sr_fleet_readiness"), 3)
        self.assertNotIn("sr_fleet_readiness", _block(self.values, "sr_battlestation_fire"))
        self.assertNotIn("sr_fleet_readiness", _block(self.combat, "sr_cb_battery_gather"))
        self.assertNotIn("sr_fleet_readiness", _strip(_raw(ROOT / "common/script_values/sr_fleet_display_values.txt")))

    def test_earth_weighs_ours_at_it(self):
        ready = _block(self.values, "sr_fl_at_earth_ready")
        self.assertRegex(ready, r"limit = \{ has_variable = sr_fl_at_earth \}\s*value = var:sr_fl_at_earth\s*"
                                r"multiply = sr_fleet_readiness")
        margin = _block(self.values, "sr_orbital_superiority_margin")
        self.assertIn("value = sr_fl_at_earth_ready", margin)
        self.assertNotIn("var:sr_fl_at_earth", margin)
        loud = _block(self.triggers, "sr_earth_alert_loud")
        # Ours only: the hostile side stays hull strength.
        self.assertNotIn("var:sr_fl_at_earth >=", loud)
        self.assertNotIn("> var:sr_fl_at_earth", loud)
        self.assertEqual(loud.count("sr_fl_at_earth_ready"), 2)
        self.assertNotIn("sr_fleet_readiness", _block(self.values, "sr_earth_hostile_total"))

    def test_the_player_is_told(self):
        loc = "\n".join(_raw(p) for p in (ROOT / "localization/english").glob("*.yml"))
        for key in ("je_space_race_widget_space_fleets_no_sc", "sr_fl_req_space_command_tt"):
            with self.subTest(key=key):
                line = re.search(rf'(?m)^ {key}:0 "(.*)"$', loc).group(1)
                self.assertIn("half strength", line)
        # The Earth alert prints ours at hull strength, so it says so while
        # grounded (review of #1287, M5): the popup and the Hostile Fleet hover.
        self.assertIn("half strength", re.search(r'(?m)^ sr_earth_alert_half_fire:0 "(.*)"$', loc).group(1))
        for key, root in (("space_race_events.111.d", "ROOT.GetCountry"), ("je_space_race_widget_ovc_earth_tt", "JournalEntry.GetCountry")):
            with self.subTest(key=key):
                line = re.search(rf'(?m)^ {re.escape(key)}:0 "(.*)"$', loc).group(1)
                self.assertIn(f"[AddLocalizationIf( EqualTo_CFixedPoint( {root}.MakeScope.ScriptValue('sr_disp_sc_operational'), "
                              f"'(CFixedPoint)0' ), 'sr_earth_alert_half_fire' )]", line)


class NoSpaceCommandTest(unittest.TestCase):
    """No Space Command, no fleet orders (UI pass design § 10): with no Space
    Command level in a state it controls, a country's fleets can't depart,
    change posture or target, start a refit or repair; a refit under way
    pauses. Fleets in flight land, fight where they are, and refill."""

    @classmethod
    def setUpClass(cls):
        cls.triggers = _strip(_raw(FLEET_TRIGGERS))
        cls.generated = _strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT))
        cls.sguis = _strip(_raw(SGUIS))
        cls.effects = _strip(_raw(FLEET_EFFECTS))
        cls.combat = _strip(_raw(COMBAT_EFFECTS))

    def test_operational_needs_a_held_level(self):
        body = _block(self.triggers, "sr_sc_operational")
        self.assertRegex(body, r"has_building = building_space_command\s*"
                               r"any_scope_state = \{\s*sr_state_held_by_owner = yes\s*has_building = building_space_command\s*"
                               r"any_scope_building = \{\s*is_building_type = building_space_command\s*level >= 1\s*\}\s*\}")

    def test_every_dispatch_is_behind_a_may_depart(self):
        """Every departure goes through sr_fl_<n>_may_depart_<loc>, which
        carries the gate: the player's Go, the AI's moves and the recall,
        directly or through a generated trigger. The AI's picks test it in the
        pass that chooses the slot (sr_fl_n), in the block around the dispatch."""
        triggers = _strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT))

        def gated(lim, n, loc):
            gate = f"sr_fl_{n}_may_depart_{loc} = yes"
            if gate in lim:
                return True
            return any(gate in _block(triggers, name)
                       for name in re.findall(rf"\b(sr_fl_{re.escape(n)}_\w+) = yes", lim)
                       if re.search(rf"(?m)^{name} = \{{", triggers))

        sites = 0
        for path in (FLEET_EFFECTS, COMBAT_EFFECTS, gsf.ROOT / gsf.EFFECTS_OUT):
            text = _strip(_raw(path))
            for m in re.finditer(r"(?m)^[\t ]+sr_fl_dispatch = \{ N = (\S+) LOC = (\w+)", text):
                sites += 1
                n, loc = m.group(1), m.group(2)
                with self.subTest(path=path.name, slot=n, loc=loc, at=m.start()):
                    limits = _enclosing_limits(text, m.start())
                    if any(gated(lim, n, loc) for lim in limits):
                        continue
                    picked = re.search(r"local_var:sr_fl_n = (\d+)", limits[0] if limits else "")
                    self.assertTrue(picked and picked.group(1) == n, "no may_depart around it")
                    around = _block_around(text, m.start(), 2)
                    picks = [p.start() for p in re.finditer(rf"set_local_variable = \{{ name = sr_fl_n value = {n} \}}", around)]
                    self.assertTrue(picks)
                    for at in picks:
                        self.assertTrue(any(gated(lim, n, loc) for lim in _enclosing_limits(around, at)))
        self.assertGreater(sites, 200)

    def test_every_may_depart_needs_it(self):
        for n in range(1, gsf.SLOTS + 1):
            for lc in gsf.LOCATIONS:
                with self.subTest(slot=n, loc=lc.key):
                    self.assertIn("sr_sc_operational = yes", _block(self.generated, f"sr_fl_{n}_may_depart_{lc.key}"))

    def test_posture_and_target_orders_need_it(self):
        def reason(key):
            return f"custom_tooltip = {{\n\t\t\ttext = {key}\n\t\t\tsr_sc_operational = yes\n\t\t}}"
        # A direct child of is_valid (one tab deeper than is_valid itself), not
        # nested in the line before: last in the target button's gate (which has
        # no effect, so its block ends there), before can_go's in Go's. The posture
        # buttons and the target popup's Target (UI pass design § 7) give the
        # short line, for the hover's length.
        for sgui, key, after in (("sr_fleet_go_sgui", "sr_fl_req_space_command_tt",
                                  "\n\t\tcustom_tooltip = {\n\t\t\ttext = sr_fl_short_tt"),
                                 ("sr_fleet_target_sgui", "sr_fl_req_space_command_tt", "\n\t}\n"),
                                 ("sr_fleet_set_posture_sgui", "sr_fl_req_space_command_short_tt", "\n\t}\n\n\teffect = {"),
                                 ("sr_fleet_set_target_sgui", "sr_fl_req_space_command_short_tt", "\n\t}\n\n\teffect = {")):
            with self.subTest(sgui=sgui):
                body = _block(self.sguis, sgui)
                self.assertRegex(body, r"\t\t\}\n\s*(#[^\n]*\n\s*)*" + re.escape(reason(key)) + re.escape(after))
        # The destination popup's Choose isn't an order: it only picks.
        self.assertNotIn("sr_sc_operational", _block(self.sguis, "sr_fleet_set_dest_sgui"))
        # Go gives this reason before the generic one can_go would.
        go = _block(self.sguis, "sr_fleet_go_sgui")
        self.assertLess(go.index("sr_fl_req_space_command_tt"), go.index("TEST = can_go"))

    def test_refit_pauses_and_repair_waits(self):
        month = _block(self.effects, "sr_fl_month_at")
        pause = re.search(r"limit = \{\s*NOT = \{ sr_sc_operational = yes \}\s*has_variable = sr_fl_\$N\$_refit_until\s*\}\s*"
                          r"change_variable = \{ name = sr_fl_\$N\$_refit_until add = 1 \}", month)
        self.assertIsNotNone(pause, "a refit under way doesn't pause")
        # The pause comes first, so a paused refit can't also complete.
        self.assertLess(pause.start(), month.index("var:sr_fl_$N$_refit_until <= te_history_month_index"))
        start = month[month.index("sr_fl_$N$_drive_value < sr_drive_level") - 200:month.index("sr_fl_$N$_drive_value < sr_drive_level") + 80]
        self.assertIn("sr_sc_operational = yes", start)
        self.assertRegex(month, r"limit = \{ local_var:sr_fl_share > 0 sr_sc_operational = yes \}\s*sr_fl_repair_roles_at")

    def test_the_month_gates_three_things_only(self):
        """The refit's pause, the refit's start and the repair: refill,
        propellant at a Spaceport and marines run without a Space Command."""
        self.assertEqual(_block(self.effects, "sr_fl_month_at").count("sr_sc_operational"), 3)

    def test_refill_still_runs(self):
        month = _block(self.effects, "sr_fl_month_at")
        for line in ("set_variable = { name = sr_fl_$N$_dv value = sr_fl_$N$_dv_capacity }",
                     "set_variable = { name = sr_fl_$N$_supply value = sr_fl_$N$_endurance }"):
            with self.subTest(line=line):
                i = month.index(line)
                # no enclosing block tests sr_sc_operational
                for lim in _enclosing_limits(month, i):
                    self.assertNotIn("sr_sc_operational", lim)

    def test_the_ai_s_voluntary_orders_need_it(self):
        """The lunar assault and the offensive set postures directly; the
        combat model's own fallbacks (sr_cb_check_target and the rest) stay."""
        attack = _block(self.combat, "sr_fl_ai_attack")
        self.assertRegex(attack, r"limit = \{ is_at_war = yes sr_sc_operational = yes \}\s*sr_fl_ai_lunar_assault = yes")
        self.assertIn("sr_fl_each_slot = { DO = ai_assault }", attack)
        calls = re.findall(r"sr_fl_ai_lunar_assault = yes", self.combat + _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT)) + self.effects)
        self.assertEqual(len(calls), 1)


def _enclosing_at(text, idx, opener="flowcontainer = {"):
    """The block opened by the last `opener` starting at or before idx, braces included."""
    start = text.rindex(opener, 0, idx + len(opener))
    brace = start + len(opener) - 1
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError("unclosed block")


def _instances(text, name):
    """Each `name = { ... }` instance in a stretch of GUI, in order, braces included."""
    out = []
    for m in re.finditer(rf"\b{name} = \{{", text):
        out.append(_enclosing_at(text, m.end(), f"{name} = {{"))
    return out


_SCOPES = re.compile(r"AddScope\( 'op', MakeScopeValue\( '\(CFixedPoint\)(\d+)' \) \)"
                     r"(?:\.AddScope\( 'pick', MakeScopeValue\( '\(CFixedPoint\)(\d+)' \) \))?"
                     r"(?:\.AddScope\( 'step', MakeScopeValue\( '\(CFixedPoint\)(\d+)' \) \))?\.End")


class TransferPopupTest(unittest.TestCase):
    """The Transfer popup (UI pass design § 6), which took in Merge and Detach:
    a body a slot, Into's buttons, then a row a role and the marines with − and
    + on the construction market's keys, each amount held to what the slot has."""

    @classmethod
    def setUpClass(cls):
        cls.rows = _raw(gsf.ROOT / gsf.GUI_OUT)
        body = cls.rows[cls.rows.index("type te_sr_xfer_popup_body"):]
        cls.bodies = {}
        for n in range(1, gsf.SLOTS + 1):
            at = body.index(f"visible = \"[GetVariableSystem.HasValue('te_popup', 'sr_xfer_{n}')]\"")
            cls.bodies[n] = _enclosing_at(body, at)
        cls.sguis = _strip(_raw(SGUIS))
        cls.effects = _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT))
        cls.values = _strip(_raw(gsf.ROOT / gsf.VALUES_OUT))
        cls.triggers = _strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT))

    def _shown(self, n):
        return f"EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_fl_{n}'), '(CFixedPoint)1' )"

    def test_a_body_a_slot(self):
        self.assertEqual(self.rows.count("GetVariableSystem.HasValue('te_popup', 'sr_xfer_"), gsf.SLOTS)
        for n, body in self.bodies.items():
            with self.subTest(slot=n):
                self.assertEqual({int(m.group(1)) for m in _SCOPES.finditer(body)}, {n})

    def test_a_body_for_an_empty_slot_shows_only_its_note(self):
        """A fleet that left or is gone under an open popup: one line, nothing to press."""
        for n, body in self.bodies.items():
            with self.subTest(slot=n):
                note = _enclosing_at(body, body.index("je_space_race_widget_xf_gone"), "te_sr_note = {")
                self.assertIn(f'visible = "[Not( {self._shown(n)} )]"', note)
                content = _enclosing_at(body, body.index(f'visible = "[{self._shown(n)}]"'))
                self.assertIn("te_sr_xf_to_line", content)
                self.assertEqual(len(_instances(content, "te_sr_xf_role_row")), len(gsf.XF_KEYS) + 1)

    def test_each_role_row_steps_its_own_amount(self):
        for n, body in self.bodies.items():
            rows = _instances(body, "te_sr_xf_role_row")
            for k, row in zip((*gsf.XF_KEYS, None), rows):
                with self.subTest(slot=n, role=k):
                    picks = {(int(m.group(1)), m.group(2)) for m in _SCOPES.finditer(row)}
                    if k is None:   # the strength's total: no buttons
                        self.assertEqual(picks, set())
                        for block in ("xf_less", "xf_more"):
                            self.assertRegex(row, rf'blockoverride "{block}" \{{\s*visible = no\s*\}}')
                        self.assertIn("ScriptValue('sr_disp_fl_%d_xf_strength')" % n, row)
                    else:
                        self.assertEqual(picks, {(n, str(gsf.XF_CODE[k]))})
                        self.assertIn(f"text = \"je_space_race_widget_xf_role_{k}\"", row)
                        for shown in ("xf", "xf_stay", "xf_there"):
                            self.assertIn(f"ScriptValue('sr_disp_fl_{n}_{shown}_{k}')", row)

    def test_the_keys_match_the_construction_market(self):
        """Click, Shift, Ctrl and Alt are click_modifiers, right-click a sibling
        (gui/construction_panel.gui), each a positive step code: − 1 to 5, + 6 to 10."""
        self.assertEqual(gsf.XF_HANDLERS, ("ondefault", "onshift", "onctrl", "onalt"))
        for n, body in self.bodies.items():
            for row in _instances(body, "te_sr_xf_role_row")[:len(gsf.XF_KEYS)]:
                for block, codes in (("xf_less", gsf.XF_LESS), ("xf_more", gsf.XF_MORE)):
                    with self.subTest(slot=n, block=block):
                        over = _enclosing_at(row, row.index(f'blockoverride "{block}" {{') + 5, f'blockoverride "{block}" {{')
                        mods = _enclosing_at(over, over.index("click_modifiers = {") + 5, "click_modifiers = {")
                        got = [(h, int(_SCOPES.search(v).group(3)))
                               for h, v in re.findall(r'(\w+) = "(\[[^"]*\])"', mods)]
                        self.assertEqual(got, list(zip(gsf.XF_HANDLERS, codes[:4])))
                        right = re.search(r'(?m)^\s*onrightclick = "([^"]*)"', over)
                        self.assertEqual(int(_SCOPES.search(right.group(1)).group(3)), codes[4])
                        self.assertNotRegex(over, r"\bonclick =")
                        # The greyed state and the hover are the plain click's.
                        for prop in ("enabled", "tooltip"):
                            line = re.search(rf'(?m)^\s*{prop} = "([^"]*)"', over).group(1)
                            self.assertEqual({int(m.group(3)) for m in _SCOPES.finditer(line)}, {codes[0]})
        self.assertEqual(sorted({*gsf.XF_LESS, *gsf.XF_MORE}), list(range(1, 11)))
        self.assertEqual({gsf.XF_STEPS[c] for c in gsf.XF_LESS[:4]}, {-1, -10, -100, -1000})
        self.assertEqual({gsf.XF_STEPS[c] for c in gsf.XF_MORE[:4]}, {1, 10, 100, 1000})

    def test_a_step_is_held_to_what_the_slot_has(self):
        step = _block(self.effects, "sr_fl_xfer_step_role")
        self.assertRegex(step, rf"scope:step = {gsf.XF_NONE} \}}\s*set_variable = \{{ name = sr_det_amt_\$ROLE\$ value = 0 \}}")
        self.assertRegex(step, rf"scope:step = {gsf.XF_ALL} \}}\s*set_variable = \{{ name = sr_det_amt_\$ROLE\$ "
                               r"value = sr_fl_\$N\$_\$ROLE\$_value \}")
        for code, amount in gsf.XF_STEPS.items():
            with self.subTest(code=code):
                self.assertRegex(step, rf"scope:step = {code} \}}\s*set_variable = \{{ name = sr_det_amt_\$ROLE\$ value = "
                                       rf"\{{ value = sr_fl_\$N\$_xf_\$ROLE\$ add = {amount} "
                                       r"max = sr_fl_\$N\$_\$ROLE\$_value min = 0 \} \}")
        dispatch = _block(self.effects, "sr_fl_xfer_step_at")
        for k, code in gsf.XF_CODE.items():
            self.assertRegex(dispatch, rf"scope:pick = {code} \}}\s*sr_fl_xfer_step_role = \{{ N = \$N\$ ROLE = {k} CODE = {code} \}}")
        # The hover by the step's sign: − below 6, + from 6.
        effect = _block(_block(self.sguis, "sr_fleet_xfer_step_sgui").replace("\n\t", "\n"), "effect")
        self.assertRegex(effect, r"if = \{\s*limit = \{ scope:step < 6 \}\s*custom_tooltip = sr_fl_xf_less_tt\s*\}\s*"
                                 r"else = \{\s*custom_tooltip = sr_fl_xf_more_tt\s*\}")

    def test_the_step_self_check_logs_once_with_its_numbers(self):
        """TE_SELF_CHECK xfer_step_scope, run: OK on the first step whose code
        arrived, BROKEN on the first that arrived with none, and never both or
        twice (the flag is set before either line). Its numbers go through
        variables, set when it logs and gone after."""
        fx = _Fx(op=1, pick=1, step=6)
        fx.fleet(1, loc=2, war=(5, 5))
        fx.choose(0, war=2)
        fx.effect("sr_fl_by_op", DO="xfer_step")
        fx.effect("sr_fl_by_op", DO="xfer_step")
        self.assertEqual(fx.vars["sr_det_amt_war"], _fxn(4))
        self.assertEqual(len(fx.logs), 1)
        line, read = fx.logs[0]
        self.assertTrue(line.startswith('"TE_SELF_CHECK OK xfer_step_scope'), line)
        self.assertEqual(read, {"sr_xf_chk_slot": _fxn(1), "sr_xf_chk_role": _fxn(1), "sr_xf_chk_amount": _fxn(3)})
        self.assertFalse([k for k in fx.vars if k.startswith("sr_xf_chk_")])
        fx = _Fx(op=3, pick=6, step=11)   # no step code: the third scope didn't arrive
        fx.fleet(3, loc=2, marines=2, war=(5, 5), carrier=(1, 1))
        fx.effect("sr_fl_by_op", DO="xfer_step")
        fx.scopes["step"] = _fxn(6)
        fx.effect("sr_fl_by_op", DO="xfer_step")
        self.assertEqual([(line[:40], read) for line, read in fx.logs],
                         [('"TE_SELF_CHECK BROKEN xfer_step_scope (a', {"sr_xf_chk_slot": _fxn(3), "sr_xf_chk_role": _fxn(6)})])
        self.assertFalse([k for k in fx.vars if k.startswith("sr_xf_chk_")])

    def test_the_amounts_shown_and_moved_are_held_to_the_slot(self):
        """A battle or a repair under an open popup: what is shown, and what a
        transfer moves, is never more than the slot has (Review Focus 3)."""
        for n in range(1, gsf.SLOTS + 1):
            for k in gsf.XF_KEYS:
                with self.subTest(slot=n, key=k):
                    body = _block(self.values, f"sr_fl_{n}_xf_{k}")
                    self.assertRegex(body, rf"if = \{{ limit = \{{ has_variable = sr_det_amt_{k} \}} value = var:sr_det_amt_{k} \}}"
                                           rf"\s*max = sr_fl_{n}_{k}_value\s*min = 0\s*$")
                    disp = _raw(gsf.ROOT / gsf.DISPLAY_OUT)
                    moved = "xf_marines_moved" if k == "marines" else f"xf_{k}"
                    self.assertIn(f"sr_disp_fl_{n}_xf_{k} = {{ value = sr_fl_{n}_{moved} }}", disp)

    def test_with_every_ship_going_the_marines_row_shows_all_of_them_and_its_keys_grey(self):
        """Review minor 1: the Move cell agrees with Stays and Other fleet, and
        − and + say why they do nothing."""
        fx = _Fx(op=1, pick=6, step=1)
        fx.fleet(1, loc=2, marines=4, war=(2, 2), carrier=(2, 2))
        fx.fleet(3, loc=2, carrier=(2, 2))
        fx.choose(3, war=1, carrier=2, marines=1)
        self.assertEqual([fx.num(f"sr_disp_fl_1_xf_{c}marines") for c in ("", "stay_", "there_")], [_fxn(1), _fxn(3), _fxn(1)])
        self.assertEqual(fx.refusals("sr_fleet_xfer_step_sgui"), [])
        fx.choose(3, war=2, carrier=2, marines=1)
        self.assertEqual([fx.num(f"sr_disp_fl_1_xf_{c}marines") for c in ("", "stay_", "there_")], [_fxn(4), 0, _fxn(4)])
        self.assertEqual(fx.refusals("sr_fleet_xfer_step_sgui"), ["sr_fl_xf_marines_follow_tt"])
        fx.scopes["pick"] = _fxn(1)
        self.assertEqual(fx.refusals("sr_fleet_xfer_step_sgui"), [])
        # The hand-written gate names the marines' code the generator gives them.
        self.assertEqual(gsf.XF_CODE["marines"], 6)
        self.assertIn("limit = { scope:pick = 6 }", _block(self.sguis, "sr_fleet_xfer_step_sgui"))

    def test_opening_resets_the_amounts(self):
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                body = _block(self.effects, f"sr_fl_{n}_xfer_open_now")
                for k in gsf.XF_KEYS:
                    self.assertIn(f"set_variable = {{ name = sr_det_amt_{k} value = {{ value = sr_fl_{n}_{k}_value "
                                  "multiply = 0.5 round = yes } }", body)
                self.assertRegex(body, r"^\s*set_variable[^\n]*\n\s*(?:set_variable[^\n]*\n\s*)*if = \{\s*"
                                       r"limit = \{ sr_fl_has_free_slot = yes \}\s*set_variable = \{ name = sr_det_to value = 0 \}")
                self.assertEqual(sorted(int(m) for m in re.findall(r"name = sr_det_to value = (\d)", body)),
                                 [0, *gsf._others(n)])
        self.assertRegex(self.effects, r"(?m)^sr_fl_xfer_open_at = \{ sr_fl_\$N\$_xfer_open_now = yes \}")
        rows = self.rows
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                row = re.findall(r"te_sr_fleet_row = \{.*?\n\t\t\}\n", rows, re.S)[n - 1]
                button = _enclosing_at(row, row.index('blockoverride "fl_transfer_button" {') + 5,
                                    'blockoverride "fl_transfer_button" {')
                self.assertIn("enabled = \"[GetScriptedGui('sr_fleet_xfer_open_sgui').IsValid(", button)
                self.assertIn("onclick = \"[GetScriptedGui('sr_fleet_xfer_open_sgui').Execute(", button)
                self.assertIn(f"onclick = \"[GetVariableSystem.Set('te_popup', 'sr_xfer_{n}')]\"", button)
                self.assertIn("IsValidTooltip", button)
                self.assertNotIn("sr_fleet_merge_sgui", row)
                self.assertNotIn("sr_fleet_detach_sgui", row)

    def test_the_popup_holds_its_rows(self):
        """The rows' minimum width plus the window's margins, the list's and a
        scrollbar (128, as the colony target popup's 760 = 632 + 128)."""
        widget = _raw(ROOT / "gui/journal_entry_widgets/space_race_widget.gui")
        popup = _enclosing_at(widget, widget.index("type te_sr_xfer_popup = te_ui_popup {") + 5, "type te_sr_xfer_popup = te_ui_popup {")
        width = int(re.search(r'blockoverride "popup_size" \{\s*size = \{ (\d+) \d+ \}', popup).group(1))
        body = self.rows[self.rows.index("type te_sr_xfer_popup_body"):]
        rows = int(re.search(r"minimumsize = \{ (\d+) -1 \}", body).group(1))
        self.assertGreaterEqual(width, rows + 128)
        for type_name in ("te_sr_xf_role_row", "te_sr_xf_head_row", "te_sr_xf_to_line", "te_sr_xf_go_row"):
            with self.subTest(row=type_name):
                cells = _enclosing_at(widget, widget.index(f"type {type_name} = ") + 5, f"type {type_name} = ")
                if type_name == "te_sr_xf_go_row":
                    self.assertIn(f"size = {{ {rows} 38 }}", cells)
                    # the button itself centered, not only its label
                    self.assertRegex(cells, r"button = \{\s*using = default_button_action\s*size = \{ \d+ \d+ \}\s*"
                                            r"parentanchor = center\s*block \"xf_go_btn\"")
                    continue
                sizes = [int(w) for w in re.findall(r"size = \{ (\d+) \d+ \}", cells)]
                if type_name == "te_sr_xf_role_row":   # the buttons sit in their 28-wide widgets
                    sizes = [w for w in sizes if w != 26]
                if type_name == "te_sr_xf_to_line":    # Into, then a line of three buttons
                    button = _enclosing_at(widget, widget.index("type te_sr_xf_to_button = ") + 5, "type te_sr_xf_to_button = ")
                    sizes += 3 * [int(re.search(r"size = \{ (\d+) 26 \}", button).group(1))]
                    self.assertEqual(sum(sizes) + 3 * 4 + 2 * 4, rows)
                    continue
                self.assertEqual(sum(sizes) + (len(sizes) - 1) * 4 + 2 * 4, rows)

    def test_the_target_buttons_list_the_new_slot_and_fleets_at_the_location(self):
        for n, body in self.bodies.items():
            with self.subTest(slot=n):
                line = _instances(body, "te_sr_xf_to_line")
                self.assertEqual(len(line), 1)
                buttons = _instances(line[0], "te_sr_xf_to_button")
                picks = [int(_SCOPES.search(b).group(2)) for b in buttons]
                self.assertEqual(picks, [0, *gsf._others(n)])
                for pick, b in zip(picks, buttons):
                    # Shown on a display value, never the scripted GUI's IsShown (review I1).
                    self.assertNotIn("IsShown(", b)
                    shown = re.findall(r'(?m)^\s*visible = "([^"]*)"', b)
                    self.assertEqual(shown, [] if pick == 0 else
                                     [f"[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_fl_{n}_xf_here_{pick}'), "
                                      "'(CFixedPoint)1' )]"])
                    enabled = re.search(r'(?m)^\s*enabled = "\[GetScriptedGui\(\'(\w+)\'\)\.IsValid\(', b)
                    self.assertEqual(enabled.group(1), "sr_fleet_xfer_to_sgui")
                    label = "je_space_race_widget_xf_new" if pick == 0 else f"je_space_race_widget_xf_to_{pick}"
                    self.assertIn(f'text = "{label}"', b)
                    self.assertEqual({(int(m.group(1)), int(m.group(2))) for m in _SCOPES.finditer(b)}, {(n, pick)})
                # A line with no fleet here hides (New fleet's always shows).
                lines = _instances(line[0], "flowcontainer")
                self.assertEqual(len(lines), 3)
                self.assertNotRegex(lines[0].split("te_sr_xf_to_button")[0], r"(?m)^\s*visible =")
                for ln in lines[1:]:
                    head = ln.split("te_sr_xf_to_button")[0]
                    self.assertEqual(sorted(int(x) for x in re.findall(rf"sr_disp_fl_{n}_xf_here_(\d)", head)),
                                     sorted(int(_SCOPES.search(b).group(2)) for b in _instances(ln, "te_sr_xf_to_button")))
                here = _block(self.triggers, f"sr_fl_{n}_xf_pick_here")
                self.assertEqual(sorted(int(m) for m in re.findall(r"scope:pick = (\d)", here)), gsf._others(n))
                for m in gsf._others(n):
                    self.assertIn(f"AND = {{ scope:pick = {m} has_variable = sr_fl_{m}_loc has_variable = sr_fl_{n}_loc "
                                  f"var:sr_fl_{m}_loc = var:sr_fl_{n}_loc }}", here)
        to = _block(self.sguis, "sr_fleet_xfer_to_sgui").replace("\n\t", "\n")
        self.assertNotIn("scope:", _block(to, "is_shown"))
        self.assertRegex(_block(to, "is_valid"), r"trigger_if = \{\s*limit = \{ NOT = \{ scope:pick = 0 \} \}\s*custom_tooltip = \{\s*"
                                                 r"text = sr_fl_xf_pick_here_tt\s*sr_fl_op_check = \{ TEST = xf_pick_here \}")
        setter = _block(self.effects, "sr_xf_set_to")
        for m in range(0, gsf.SLOTS + 1):
            self.assertRegex(setter, rf"scope:pick = {m} \}}\s*set_variable = \{{ name = sr_det_to value = {m} \}}")
        chosen = _block(self.triggers, "sr_xf_pick_chosen")
        for m in range(0, gsf.SLOTS + 1):
            self.assertIn(f"AND = {{ scope:pick = {m} sr_det_to_value = {m} }}", chosen)

    def test_into_greys_what_it_can_t_choose(self):
        """Into, run: a fleet here, never the one already chosen; a new fleet with
        a slot free; a fleet elsewhere hides (its display value) and greys."""
        fx = _Fx(op=1)
        fx.fleet(1, loc=2, war=(4, 4))
        fx.fleet(3, loc=2, war=(1, 1))
        fx.fleet(4, loc=5, war=(1, 1))
        fx.choose(0)
        verdicts = {}
        for pick in (0, 3, 4):
            fx.scopes["pick"] = _fxn(pick)
            verdicts[pick] = fx.refusals("sr_fleet_xfer_to_sgui")
        self.assertEqual(verdicts, {0: ["sr_fl_xf_not_chosen_tt"], 3: [], 4: ["sr_fl_xf_pick_here_tt"]})
        self.assertEqual({m: fx.num(f"sr_disp_fl_1_xf_here_{m}") for m in gsf._others(1)},
                         {m: _fxn(1) if m == 3 else 0 for m in gsf._others(1)})
        fx.scopes["pick"] = _fxn(3)
        fx.effect("sr_xf_set_to")
        self.assertEqual(fx.vars["sr_det_to"], _fxn(3))
        self.assertEqual(fx.refusals("sr_fleet_xfer_to_sgui"), ["sr_fl_xf_not_chosen_tt"])
        for n in range(5, gsf.SLOTS + 1):
            fx.fleet(n, loc=7, war=(1, 1))
        fx.fleet(2, loc=7, war=(1, 1))
        fx.scopes["pick"] = 0
        self.assertEqual(fx.refusals("sr_fleet_xfer_to_sgui"), ["sr_fl_xf_free_slot_tt"])

    def test_the_popup_s_buttons_act_only_on_a_fleet_here(self):
        """Each is_valid starts at the fleet's location, so a stale slot greys
        (Review Focus 1), and every reason line is a direct child."""
        for name in ("sr_fleet_xfer_open_sgui", "sr_fleet_xfer_step_sgui", "sr_fleet_xfer_to_sgui"):
            with self.subTest(sgui=name):
                valid = _block(_block(self.sguis, name).replace("\n\t", "\n"), "is_valid")
                self.assertRegex(valid, r"^\s*custom_tooltip = \{\s*text = sr_fl_not_at_location_tt\s*"
                                        r"sr_fl_op_check = \{ TEST = at_location \}\s*\}")
        opener = _block(self.sguis, "sr_fleet_xfer_open_sgui")
        self.assertIn("sr_fl_op_check = { TEST = can_transfer }", opener)
        self.assertIn("saved_scopes = { op pick step }", _block(self.sguis, "sr_fleet_xfer_step_sgui"))
        for n in range(1, gsf.SLOTS + 1):
            self.assertIn(f"sr_fl_{n}_can_transfer = {{ OR = {{ sr_fl_{n}_can_merge = yes sr_fl_{n}_can_detach = yes }} }}",
                          self.triggers)

    def test_merge_and_detach_are_gone_from_the_panel(self):
        """The popup took them in, and their effects went with them (#1298: no
        caller was left; the AI never had one)."""
        self.assertNotIn("sr_fleet_merge_sgui", self.sguis)
        self.assertNotIn("sr_fleet_detach_sgui", self.sguis)
        for pattern in (r"(?m)^sr_fl_merge = \{", r"(?m)^sr_fl_detach = \{", r"(?m)^sr_fl_merge_at = \{",
                        r"(?m)^sr_fl_detach_at = \{", r"(?m)^sr_fl_\d_merge_now = \{", r"(?m)^sr_fl_\d_detach_now = \{"):
            with self.subTest(pattern=pattern):
                self.assertNotRegex(self.effects, pattern)
        self.assertFalse({"merge", "detach"} & set(gsf.SLOT_ACTIONS))


class TransferTest(unittest.TestCase):
    """Transfer itself (UI pass design § 6): slot N's chosen share of each role,
    now and at full by the one share, and its marines, into a new fleet
    (Detach's shape) or one of ours there (Merge's rules); the refusals on
    the button match what the effect assumes."""

    @classmethod
    def setUpClass(cls):
        cls.effects = _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT))
        cls.triggers = _strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT))
        cls.sguis = _strip(_raw(SGUIS))
        cls.new = _block(cls.effects, "sr_fl_transfer_new")
        cls.into = _block(cls.effects, "sr_fl_transfer_into")

    def test_amounts_are_clamped_before_moving(self):
        """Each role's amount is the clamped one (sr_fl_$N$_xf_<role>, held to
        what N has), never the raw variable; it and the role's strength now are
        read before the first move (the clamp follows the variables)."""
        for name, body in (("new", self.new), ("into", self.into)):
            with self.subTest(effect=name):
                self.assertNotIn("sr_det_amt_", body)
                first_move = body.index("sr_fl_add_role_part")
                for r in gsf.ROLES:
                    for read in (f"set_local_variable = {{ name = sr_xf_amt_{r.key} value = sr_fl_$N$_xf_{r.key} }}",
                                 f"set_local_variable = {{ name = sr_xf_now_{r.key} value = sr_fl_$N$_{r.key}_value }}"):
                        self.assertLess(body.index(read), first_move)
                for read in ("sr_xf_marines value = sr_fl_$N$_xf_marines_moved", "sr_xf_ships value = sr_fl_$N$_xf_strength",
                             "sr_fl_$N$_xf_left <= 0"):
                    self.assertLess(body.index(read), first_move)
        self.assertNotIn("sr_det_amt_", _block(self.effects, "sr_fl_1_transfer_now"))

    def test_each_role_moves_its_amount_and_its_full_in_proportion(self):
        """The amount itself at the strength now; full x amount / now at full,
        multiplied first, never under the amount; all of a role as it stands when
        all of the fleet goes (TransferRunTest runs them)."""
        for name, body in (("new", self.new), ("into", self.into)):
            for r in gsf.ROLES:
                k = r.key
                with self.subTest(effect=name, role=k):
                    self.assertRegex(body, rf"limit = \{{ local_var:sr_xf_all = 1 \}}\s*"
                                           rf"if = \{{ limit = \{{ has_variable = sr_fl_\$N\$_{k} \}} sr_fl_add_role_part = \{{ N = \$M\$ "
                                           rf"VAR = {k} AMOUNT = var:sr_fl_\$N\$_{k} \}}")
                    self.assertRegex(body, rf"limit = \{{ local_var:sr_xf_amt_{k} > 0 \}}\s*"
                                           rf"set_local_variable = \{{ name = sr_xf_part value = \{{ value = sr_fl_\$N\$_{k}_full_value "
                                           rf"multiply = local_var:sr_xf_amt_{k} divide = local_var:sr_xf_now_{k} "
                                           rf"min = local_var:sr_xf_amt_{k} \}} \}}\s*"
                                           rf"sr_fl_add_role_part = \{{ N = \$M\$ VAR = {k} AMOUNT = local_var:sr_xf_amt_{k} \}}\s*"
                                           rf"sr_fl_add_role_part = \{{ N = \$M\$ VAR = {k}_full AMOUNT = local_var:sr_xf_part \}}")
                    self.assertNotIn("sr_xf_share_", body)
            self.assertIn("set_variable = { name = sr_fl_$M$_marines value = { value = sr_fl_$M$_marines_value "
                          "add = local_var:sr_xf_marines } }", body)
            self.assertIn("set_variable = { name = sr_fl_$N$_marines value = { value = sr_fl_$N$_marines_value "
                          "subtract = local_var:sr_xf_marines min = 0 } }", body)

    def test_all_into_an_existing_fleet_clears_the_source(self):
        """All of N: every role at share 1 (a role damaged to nothing takes its
        full along), every marine, and N cleared after, as Merge did."""
        self.assertRegex(self.into, r"limit = \{ sr_fl_\$N\$_strength < sr_fl_minimum_strength \}\s*sr_fl_clear_at = \{ N = \$N\$ \}")
        self.assertLess(self.into.rindex("sr_fl_add_role_part"), self.into.index("sr_fl_clear_at = { N = $N$ }"))
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                moved = _block(_strip(_raw(gsf.ROOT / gsf.VALUES_OUT)), f"sr_fl_{n}_xf_marines_moved")
                self.assertIn(f"if = {{ limit = {{ sr_fl_{n}_xf_left <= 0 }} value = sr_fl_{n}_marines_value }}", moved)
        self.assertNotIn("sr_fl_clear_at = { N = $N$ }", self.new)

    def test_a_new_fleet_copies_location_posture_drive_and_refit(self):
        body = self.new
        clear = body.index("sr_fl_clear_at = { N = $M$ }")
        for line in ("set_variable = { name = sr_fl_$M$_loc value = var:sr_fl_$N$_loc }",
                     "set_variable = { name = sr_fl_$M$_drive value = sr_fl_$N$_drive_value }",
                     "set_variable = { name = sr_fl_$M$_posture value = { value = sr_fl_$N$_posture_value max = 2 } }",
                     "set_variable = { name = sr_fl_$M$_refit_until value = var:sr_fl_$N$_refit_until }"):
            with self.subTest(line=line):
                self.assertLess(clear, body.index(line))
                self.assertLess(body.index(line), body.index("sr_fl_add_role_part"))
        for slot in ("N", "M"):
            self.assertIn(f"set_variable = {{ name = sr_fl_${slot}$_dv value = {{ value = sr_fl_${slot}$_dv_capacity "
                          "multiply = local_var:sr_fl_dv_share } }", body)
            self.assertIn(f"set_variable = {{ name = sr_fl_${slot}$_supply value = {{ value = sr_fl_${slot}$_endurance "
                          "multiply = local_var:sr_fl_supply_share } }", body)
        self.assertIn("sr_loc_rebuild = yes", body)

    def test_into_a_fleet_keeps_merge_s_rules(self):
        """The slower drive, the later refit and the lower shares, only with ships
        joining; marines alone change none of it."""
        ships = _block("x = {" + self.into.split("limit = { local_var:sr_xf_ships > 0 }", 1)[1], "x")
        self.assertIn("set_local_variable = { name = sr_xf_m_dv_share value = local_var:sr_fl_dv_share }", ships)
        self.assertIn("set_local_variable = { name = sr_xf_m_supply_share value = local_var:sr_fl_supply_share }", ships)
        self.assertIn("limit = { sr_fl_$N$_drive_value < sr_fl_$M$_drive_value }", ships)
        self.assertIn("var:sr_fl_$M$_refit_until < var:sr_fl_$N$_refit_until", ships)
        self.assertNotIn("sr_fl_$M$_posture", self.into)
        self.assertIn("set_variable = { name = sr_fl_$M$_dv value = { value = sr_fl_$M$_dv_capacity "
                      "multiply = local_var:sr_xf_m_dv_share } }", self.into)

    def test_each_slot_pair_is_generated_once(self):
        """9 × 8 into a fleet there, and 9 × 8 into the lowest empty slot."""
        for kind in ("new", "into"):
            calls = re.findall(rf"sr_fl_transfer_{kind} = \{{ N = (\d) M = (\d) \}}", self.effects)
            with self.subTest(kind=kind):
                self.assertEqual(sorted(calls), sorted((str(n), str(m)) for n in range(1, gsf.SLOTS + 1) for m in gsf._others(n)))
        for n in range(1, gsf.SLOTS + 1):
            body = _block(self.effects, f"sr_fl_{n}_transfer_now")
            with self.subTest(slot=n):
                self.assertRegex(body, r"^\s*if = \{\s*limit = \{ sr_det_to_value = 0 \}")
                for m in gsf._others(n):
                    self.assertIn(f"limit = {{ sr_det_to_value = {m} has_variable = sr_fl_{m}_loc has_variable = sr_fl_{n}_loc "
                                  f"var:sr_fl_{m}_loc = var:sr_fl_{n}_loc }}\n\t\tsr_fl_transfer_into = {{ N = {n} M = {m} }}", body)
        self.assertRegex(self.effects, r"(?m)^sr_fl_transfer_at = \{ sr_fl_\$N\$_transfer_now = yes \}")

    def test_the_refusals(self):
        """Each refusal is its own line, a direct child of is_valid or of the
        trigger_if on where it goes, so a greyed Transfer names it."""
        valid = _block(_block(self.sguis, "sr_fleet_transfer_sgui").replace("\n\t", "\n"), "is_valid")
        top = [m.group(1) for m in re.finditer(r"(?m)^\t(\w+) = \{", valid)]
        self.assertEqual(top, ["custom_tooltip", "custom_tooltip", "trigger_if", "trigger_else", "custom_tooltip"])
        texts = re.findall(r"text = (\w+)\s*([^\n]*\n[^\n]*)", valid)
        self.assertEqual([t for t, _ in texts],
                         ["sr_fl_not_at_location_tt", "sr_fl_xf_moves_tt", "sr_fl_xf_free_slot_tt", "sr_fl_xf_new_min_tt",
                          "sr_fl_xf_keeps_tt", "sr_fl_xf_partner_here_tt", "sr_fl_xf_keeps_or_all_tt", "sr_fl_xf_room_tt"])
        self.assertRegex(valid, r"trigger_if = \{\s*limit = \{ sr_det_to_value = 0 \}")
        for test in ("xf_moves", "xf_new_min", "xf_keeps", "xf_partner_here", "xf_keeps_or_all", "xf_room"):
            self.assertIn(f"sr_fl_op_check = {{ TEST = {test} }}", valid)
        effect = _block(_block(self.sguis, "sr_fleet_transfer_sgui").replace("\n\t", "\n"), "effect")
        self.assertRegex(effect, r"custom_tooltip = sr_fl_xf_transfer_tt\s*hidden_effect = \{\s*sr_fl_by_op = \{ DO = transfer \}")
        n = 4
        t = self.triggers
        self.assertIn(f"sr_fl_{n}_xf_keeps = {{ sr_fl_{n}_xf_left >= sr_fl_minimum_strength }}", t)
        self.assertIn(f"sr_fl_{n}_xf_keeps_or_all = {{ OR = {{ sr_fl_{n}_xf_left >= sr_fl_minimum_strength sr_fl_{n}_xf_left <= 0 }} }}", t)
        self.assertIn(f"sr_fl_{n}_xf_new_min = {{ sr_fl_{n}_xf_strength >= sr_fl_minimum_strength }}", t)
        room = _block(t, f"sr_fl_{n}_xf_room")
        self.assertIn(f"sr_fl_{n}_xf_there_marines <= sr_fl_{n}_xf_there_room", room)
        self.assertIn(f"OR = {{ sr_fl_{n}_xf_left <= 0 sr_fl_{n}_xf_stay_over <= sr_fl_{n}_xf_now_over }}", room)
        partner = _block(t, f"sr_fl_{n}_xf_partner_here")
        self.assertEqual(sorted(int(m) for m in re.findall(r"sr_det_to_value = (\d)", partner)), gsf._others(n))

    def test_the_button_closes_the_popup(self):
        rows = _raw(gsf.ROOT / gsf.GUI_OUT)
        body = rows[rows.index("type te_sr_xfer_popup_body"):]
        go = _instances(body, "te_sr_xf_go_row")
        self.assertEqual(len(go), gsf.SLOTS)
        for n, row in enumerate(go, start=1):
            with self.subTest(slot=n):
                self.assertIn(f"GetScriptedGui('sr_fleet_transfer_sgui').Execute( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope )"
                              f".AddScope( 'op', MakeScopeValue( '(CFixedPoint){n}' ) ).End )", row)
                self.assertIn("onclick = \"[GetVariableSystem.Clear('te_popup')]\"", row)
                self.assertIn("enabled = \"[GetScriptedGui('sr_fleet_transfer_sgui').IsValid( GuiScope.SetRoot( "
                              f"JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint){n}' ) ).End )]\"", row)
                self.assertIn("IsValidTooltip", row)


# ---------------------------------------------------------------------------
# Transfer, run: the script itself in the engine's fixed point (#1286's review, I-2)
# ---------------------------------------------------------------------------

_FX_SCALE = 100_000  # the engine's values: i64 x 1e-5, every result cut toward zero
_FX_TOKEN = re.compile(r'"[^"]*"|#[^\n]*|<=|>=|!=|\?=|[{}=<>]|[^\s{}=<>#"?]+')
_FX_OPS = {"=": lambda a, b: a == b, "?=": lambda a, b: a == b, "!=": lambda a, b: a != b, "<": lambda a, b: a < b,
           "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b}


def _fxn(x):
    """A figure in fixed point."""
    return int(Decimal(str(x)) * _FX_SCALE)


def _fx_cut(p, q):
    """p / q, cut toward zero, as the engine's every operation is."""
    r = abs(p) // abs(q)
    return r if (p < 0) == (q < 0) else -r


def _fx_mul(a, b):
    return _fx_cut(a * b, _FX_SCALE)


def _fx_div(a, b):
    return _fx_cut(a * _FX_SCALE, b)


def _fx_tokens(text):
    return [t for t in _FX_TOKEN.findall(text) if not t.startswith("#")]


def _fx_parse(tokens, i=0):
    """[(key, op, value)] up to the matching '}' (value a token or a nested list)."""
    out = []
    while i < len(tokens) and tokens[i] != "}":
        if tokens[i + 1] not in _FX_OPS:  # a bare word in a list
            out.append((tokens[i], None, None))
            i += 1
            continue
        key, op = tokens[i], tokens[i + 1]
        if tokens[i + 2] == "{":
            value, i = _fx_parse(tokens, i + 3)
            i += 1
        else:
            value, i = tokens[i + 2], i + 3
        out.append((key, op, value))
    return out, i


def _fx_top_raw(text):
    """Each top-level `name = { ... }` of a file, its body's raw text (for $ARG$)."""
    out, depth, name, start = {}, 0, None, 0
    for m in _FX_TOKEN.finditer(text):
        t = m.group(0)
        if t[0] in '#"':
            continue
        if t == "{":
            start = m.end() if depth == 0 else start
            depth += 1
        elif t == "}":
            depth -= 1
            if depth == 0:
                out[name] = text[start:m.start()]
        elif depth == 0 and t not in _FX_OPS:
            name = t
    return out


class _Fx:
    """Enough of the engine to run a transfer, from the files as they are: value
    blocks applied in order (min and max clamp where they stand), variables and
    locals, if / else_if / else, triggers, scripted effects and triggers with
    their $ARG$ substituted as text, saved scopes, and a scripted GUI's is_valid.
    Every value is an integer of 1e-5 and every operation is cut toward zero:
    test_demographics_registry._Engine(truncate=True)'s model, exactly. A read of
    a variable or local never set fails, as does an argument the callee doesn't
    name or one it names and isn't given (script_argument_audit's rule)."""

    STUBS = ("sr_loc_rebuild",)  # the location records: recorded, not run
    _sources = None

    def __init__(self, **scopes):
        if _Fx._sources is None:
            values = {}
            for path in (gsf.ROOT / gsf.VALUES_OUT, gsf.ROOT / gsf.DISPLAY_OUT, FLEET_VALUES):
                values.update({k: _fx_parse(_fx_tokens(v))[0] for k, v in _fx_top_raw(_raw(path)).items()})
            triggers = {**_fx_top_raw(_raw(gsf.ROOT / gsf.TRIGGERS_OUT)), **_fx_top_raw(_raw(FLEET_TRIGGERS))}
            effects = {**_fx_top_raw(_raw(gsf.ROOT / gsf.EFFECTS_OUT)), **_fx_top_raw(_raw(FLEET_EFFECTS))}
            sguis = {k: _fx_parse(_fx_tokens(v))[0] for k, v in _fx_top_raw(_raw(SGUIS)).items()}
            _Fx._sources = values, triggers, effects, sguis, {}
        self.values, self.triggers, self.effects, self.sguis, self._parsed = _Fx._sources
        self.scopes = {k: _fxn(v) for k, v in scopes.items()}
        self.vars, self.locals, self.globals = {}, {}, set()
        self.calls, self.logs = [], []

    # -- the fixtures ---------------------------------------------------------
    def fleet(self, n, loc, drive=0, posture=1, marines=0, refit=None, dv=0.5, supply=0.5, **roles):
        """Slot n at loc: each role (now, full); dv and supply as shares of its capacity."""
        self.vars[f"sr_fl_{n}_loc"] = _fxn(loc)
        for k, (now, full) in roles.items():
            self.vars[f"sr_fl_{n}_{k}"], self.vars[f"sr_fl_{n}_{k}_full"] = _fxn(now), _fxn(full)
        self.vars[f"sr_fl_{n}_drive"] = _fxn(drive)
        self.vars[f"sr_fl_{n}_posture"] = _fxn(posture)
        self.vars[f"sr_fl_{n}_marines"] = _fxn(marines)
        if refit is not None:
            self.vars[f"sr_fl_{n}_refit_until"] = _fxn(refit)
        self.vars[f"sr_fl_{n}_dv"] = _fx_mul(self.num(f"sr_fl_{n}_dv_capacity"), _fxn(dv))
        self.vars[f"sr_fl_{n}_supply"] = _fx_mul(self.num(f"sr_fl_{n}_endurance"), _fxn(supply))

    def choose(self, to, **amounts):
        """The popup's choice: sr_det_to and each amount (sr_det_amt_<key>)."""
        self.vars["sr_det_to"] = _fxn(to)
        for k, x in amounts.items():
            self.vars[f"sr_det_amt_{k}"] = _fxn(x)

    def slot(self, n):
        """Slot n's variables, as figures."""
        return {k[len(f"sr_fl_{n}_"):]: Decimal(v) / _FX_SCALE for k, v in self.vars.items() if k.startswith(f"sr_fl_{n}_")}

    def share(self, n, what):
        """Slot n's propellant (dv) or supply over its capacity now, as the transfer reads it."""
        cap = self.num(f"sr_fl_{n}_dv_capacity" if what == "dv" else f"sr_fl_{n}_endurance")
        return min(_fx_div(self.vars[f"sr_fl_{n}_{what}"], cap), _FX_SCALE)

    # -- the engine -----------------------------------------------------------
    def num(self, v):
        if isinstance(v, list):
            return self.calc(v)
        for prefix, store in (("var:", self.vars), ("local_var:", self.locals), ("scope:", self.scopes)):
            if v.startswith(prefix):
                assert v[len(prefix):] in store, f"{v} read, never set"
                return store[v[len(prefix):]]
        if v in self.values:
            return self.calc(self.values[v])
        try:
            return _fxn(v)
        except InvalidOperation:
            raise AssertionError(f"no value {v}") from None

    def calc(self, block, acc=0):
        taken = False
        for key, _, v in block:
            if key in ("if", "else_if", "else"):
                taken = False if key == "if" else taken
                if taken or (key != "else" and not self.test(next(x for k, _, x in v if k == "limit"))):
                    continue
                taken = True
                acc = self.calc([e for e in v if e[0] != "limit"], acc)
            elif key == "round":
                q, r = divmod(abs(acc), _FX_SCALE)
                acc = (q + (2 * r >= _FX_SCALE)) * _FX_SCALE * (1 if acc >= 0 else -1)
            else:
                x = self.num(v)
                if key == "value":
                    acc = x
                elif key == "add":
                    acc += x
                elif key == "subtract":
                    acc -= x
                elif key == "multiply":
                    acc = _fx_mul(acc, x)
                elif key == "divide":
                    assert x != 0, "a division by zero"
                    acc = _fx_div(acc, x)
                elif key == "min":
                    acc = max(acc, x)
                elif key == "max":
                    acc = min(acc, x)
                else:
                    raise AssertionError(f"unsupported value step {key}")
        return acc

    def _body(self, table, name, args):
        given = {} if args == "yes" else {k: x for k, _, x in args}
        raw = table[name]
        for k, x in given.items():
            assert isinstance(x, str), f"{name}: argument {k} is a block"
            assert f"${k}$" in raw, f"{name} doesn't name ${k}$"
            raw = raw.replace(f"${k}$", x)
        key = (id(table), name, tuple(sorted(given.items())))
        if key not in self._parsed:
            tokens = _fx_tokens(raw)
            assert not [t for t in tokens if "$" in t and not t.startswith('"')], f"{name}: an argument missing"
            self._parsed[key] = _fx_parse(tokens)[0]
        return self._parsed[key]

    def test(self, block):
        return all(self.cond(*c) for c in block)

    def cond(self, key, op, v):
        if key == "OR":
            return any(self.cond(*c) for c in v)
        if key == "AND":
            return self.test(v)
        if key == "NOT":
            assert len(v) == 1, "NOT over more than one trigger"
            return not self.cond(*v[0])
        if key == "has_variable":
            return v in self.vars
        if key == "has_global_variable":
            return v in self.globals
        if key == "has_variable_list":
            return False
        if key in self.triggers:
            if v in ("yes", "no"):
                return self.test(self._body(self.triggers, key, "yes")) == (v == "yes")
            return self.test(self._body(self.triggers, key, v))
        return _FX_OPS[op](self.num(key), self.num(v))

    def run(self, block):
        taken = False
        for key, _, v in block:
            if key in ("if", "else_if", "else"):
                taken = False if key == "if" else taken
                if taken or (key != "else" and not self.test(next(x for k, _, x in v if k == "limit"))):
                    continue
                taken = True
                self.run([e for e in v if e[0] != "limit"])
            elif key in ("set_variable", "set_local_variable"):
                d = {k: x for k, _, x in v}
                (self.locals if key == "set_local_variable" else self.vars)[d["name"]] = self.num(d["value"])
            elif key == "change_variable":
                d = {k: x for k, _, x in v}
                assert d["name"] in self.vars, f"change_variable on {d['name']}, never set"
                self.vars[d["name"]] += self.num(d["add"]) if "add" in d else -self.num(d["subtract"])
            elif key == "remove_variable":
                del self.vars[v]
            elif key == "set_global_variable":
                self.globals.add(dict((k, x) for k, _, x in v)["name"])
            elif key == "debug_log":
                read = re.findall(r"THIS\.Var\('(\w+)'\)", v)   # what the line reads is set when it logs
                assert all(name in self.vars for name in read), f"the line reads {read}, not all set"
                self.logs.append((v, {name: self.vars[name] for name in read}))
            elif key == "hidden_effect":
                self.run(v)
            elif key in self.STUBS:
                self.calls.append(key)
            elif key in self.effects:
                self.calls.append(key)
                self.run(self._body(self.effects, key, v))
            else:
                raise AssertionError(f"unsupported effect {key}")

    def effect(self, name, **args):
        self.run([(name, "=", [(k, "=", str(x)) for k, x in args.items()] if args else "yes")])

    def refusals(self, sgui):
        """The is_valid lines of a scripted GUI that fail: each custom_tooltip's
        text, through trigger_if / trigger_else."""
        out = []

        def walk(block):
            taken = False
            for key, op, v in block:
                if key in ("trigger_if", "trigger_else"):
                    if key == "trigger_if":
                        taken = self.test(next(x for k, _, x in v if k == "limit"))
                        if taken:
                            walk([e for e in v if e[0] != "limit"])
                    elif not taken:
                        walk(v)
                elif key == "custom_tooltip":
                    if not self.test([e for e in v if e[0] != "text"]):
                        out.append(next(x for k, _, x in v if k == "text"))
                elif not self.cond(key, op, v):
                    out.append(key)

        walk(next(v for k, _, v in self.sguis[sgui] if k == "is_valid"))
        return out


class TransferRunTest(unittest.TestCase):
    """Transfer run as the engine runs it, in fixed point (#1286's review, I-2):
    what each fleet holds after, and the refusals' verdicts. From the scripted
    GUI's own effect, sr_fl_by_op = { DO = transfer } with scope:op."""

    def go(self, fx, n):
        fx.scopes["op"] = _fxn(n)
        self.assertEqual(fx.refusals("sr_fleet_transfer_sgui"), [], "Transfer greyed")
        fx.effect("sr_fl_by_op", DO="transfer")

    def roles(self, fx, n):
        s = fx.slot(n)
        return {r.key: (s.get(r.key), s.get(f"{r.key}_full")) for r in gsf.ROLES if r.key in s or f"{r.key}_full" in s}

    def test_part_of_a_fleet_into_a_new_one(self):
        """The lowest empty slot; the amounts exactly; the location, the drive,
        the refit; a source closing in leaves the new fleet at Stand off (owner,
        2026-10-31); both fleets N's shares of their new capacities, with the
        tenders moving (so both capacities change)."""
        fx = _Fx()
        fx.fleet(1, loc=3, drive=1, posture=3, refit=500, dv=0.5, supply=0.6, war=(6, 6), tender=(2, 2))
        fx.fleet(3, loc=3, war=(1, 1))
        fx.choose(0, war=3, tender=2)
        dv, supply = fx.share(1, "dv"), fx.share(1, "supply")
        caps = {n: (fx.num(f"sr_fl_{n}_dv_capacity"), fx.num(f"sr_fl_{n}_endurance")) for n in (1, 2)}
        self.go(fx, 1)
        self.assertEqual(self.roles(fx, 2), {"war": (3, 3), "tender": (2, 2)})
        self.assertEqual(self.roles(fx, 1), {"war": (3, 3), "tender": (0, 0)})
        new = fx.slot(2)
        self.assertEqual((new["loc"], new["drive"], new["posture"], new["refit_until"], new["marines"]), (3, 1, 2, 500, 0))
        for n in range(4, gsf.SLOTS + 1):
            self.assertEqual(fx.slot(n), {}, f"slot {n}")
        for n in (1, 2):
            cap, end = fx.num(f"sr_fl_{n}_dv_capacity"), fx.num(f"sr_fl_{n}_endurance")
            self.assertNotEqual((cap, end), caps[n])
            self.assertEqual(fx.vars[f"sr_fl_{n}_dv"], _fx_mul(cap, dv), n)
            self.assertEqual(fx.vars[f"sr_fl_{n}_supply"], _fx_mul(end, supply), n)
        self.assertEqual(fx.calls[-1], "sr_loc_rebuild")

    def test_a_new_fleet_from_one_at_station_or_stand_off_keeps_its_posture(self):
        for posture in (1, 2):
            fx = _Fx()
            fx.fleet(1, loc=3, posture=posture, war=(6, 6))
            fx.choose(0, war=3)
            self.go(fx, 1)
            self.assertEqual(fx.slot(2)["posture"], posture)

    def test_part_of_a_fleet_into_another(self):
        """Merge's rules with ships joining: the slower drive, the later refit, the
        lower of each share; the other fleet keeps its posture; the source keeps
        its own shares, of its new capacities (its tenders gone, both change)."""
        fx = _Fx()
        fx.fleet(4, loc=5, drive=1, posture=2, refit=600, dv=0.9, supply=0.3, war=(4, 4), tender=(2, 2))
        fx.fleet(7, loc=5, drive=2, posture=1, dv=0.4, supply=0.8, war=(5, 5))
        fx.choose(7, war=2, tender=2)
        n_dv, n_supply, m_dv, m_supply = fx.share(4, "dv"), fx.share(4, "supply"), fx.share(7, "dv"), fx.share(7, "supply")
        self.assertGreater(n_dv, m_dv)
        self.assertLess(n_supply, m_supply)
        n_end = fx.num("sr_fl_4_endurance")
        self.go(fx, 4)
        self.assertEqual(self.roles(fx, 7), {"war": (7, 7), "tender": (2, 2)})
        self.assertEqual(self.roles(fx, 4), {"war": (2, 2), "tender": (0, 0)})
        m = fx.slot(7)
        self.assertEqual((m["drive"], m["refit_until"], m["posture"]), (1, 600, 1))
        self.assertEqual(fx.vars["sr_fl_7_dv"], _fx_mul(fx.num("sr_fl_7_dv_capacity"), m_dv))
        self.assertEqual(fx.vars["sr_fl_7_supply"], _fx_mul(fx.num("sr_fl_7_endurance"), n_supply))
        self.assertEqual(fx.vars["sr_fl_4_dv"], _fx_mul(fx.num("sr_fl_4_dv_capacity"), n_dv))
        self.assertNotEqual(fx.num("sr_fl_4_endurance"), n_end)
        self.assertEqual(fx.vars["sr_fl_4_supply"], _fx_mul(fx.num("sr_fl_4_endurance"), n_supply))
        self.assertEqual(fx.calls[-1], "sr_loc_rebuild")

    def test_a_faster_fleet_or_a_later_refit_joining_changes_neither(self):
        fx = _Fx()
        fx.fleet(4, loc=5, drive=3, refit=300, war=(4, 4))
        fx.fleet(7, loc=5, drive=1, refit=600, war=(5, 5))
        fx.choose(7, war=2)
        self.go(fx, 4)
        self.assertEqual((fx.slot(7)["drive"], fx.slot(7)["refit_until"]), (1, 600))

    def test_all_of_a_fleet_into_another_with_a_role_damaged_to_nothing(self):
        """Every role goes, the one damaged to 0 now with its full strength, and
        the source is cleared, as Merge did; an amount past what it has moves no more."""
        fx = _Fx()
        fx.fleet(2, loc=4, drive=2, war=(0, 2), rapid=(3, 3))
        fx.fleet(5, loc=4, drive=3, war=(1, 1))
        fx.choose(5, war=1, rapid=5)
        self.go(fx, 2)
        self.assertEqual(self.roles(fx, 5), {"war": (1, 3), "rapid": (3, 3)})
        self.assertEqual(fx.slot(5)["drive"], 2)
        self.assertEqual(fx.slot(2), {})

    def test_a_wreck_s_full_strength_goes_into_another_fleet(self):
        """All of a fleet damaged to 0 now, no marines: its full strength counts as
        something moving, as Merge allowed (owner, 2026-10-31), and joins as ships do."""
        fx = _Fx()
        fx.fleet(2, loc=4, drive=1, war=(0, 2))
        fx.fleet(5, loc=4, drive=3, war=(1, 1))
        fx.choose(5)
        self.go(fx, 2)
        self.assertEqual(self.roles(fx, 5), {"war": (1, 3)})
        self.assertEqual(fx.slot(5)["drive"], 1)
        self.assertEqual(fx.slot(2), {})

    def test_marines_alone(self):
        """Nothing but the marines changes: no drive, refit or share."""
        fx = _Fx()
        fx.fleet(1, loc=6, drive=0, refit=700, marines=4, dv=0.2, war=(1, 1), carrier=(2, 2))
        fx.fleet(2, loc=6, drive=3, dv=0.5, supply=0.5, carrier=(3, 3))
        fx.choose(2, marines=2)
        before = dict(fx.vars)
        self.go(fx, 1)
        self.assertEqual((fx.slot(1)["marines"], fx.slot(2)["marines"]), (2, 2))
        for k in ("sr_fl_2_drive", "sr_fl_2_dv", "sr_fl_2_supply", "sr_fl_2_carrier", "sr_fl_2_carrier_full",
                  "sr_fl_1_war", "sr_fl_1_carrier", "sr_fl_1_dv"):
            self.assertEqual(fx.vars[k], before[k], k)
        self.assertNotIn("sr_fl_2_refit_until", fx.vars)

    def test_no_phantom_role_is_left_behind(self):
        """Review I-1: 3 of 7 warships out, then the 4 shown into another fleet.
        Each amount moves exactly, so nothing of 1e-5 stays to cost the fleet its
        rapid response pace or its endurance."""
        fx = _Fx()
        fx.fleet(1, loc=2, war=(7, 7), rapid=(10, 10))
        fx.fleet(3, loc=2, rapid=(1, 1))
        fx.choose(0, war=3, rapid=0)
        self.go(fx, 1)
        self.assertEqual(self.roles(fx, 2), {"war": (3, 3)})
        self.assertEqual(self.roles(fx, 1)["war"], (4, 4))
        fx.choose(3, war=4)
        self.go(fx, 1)
        self.assertEqual(self.roles(fx, 1), {"war": (0, 0), "rapid": (10, 10)})
        self.assertEqual(self.roles(fx, 3), {"war": (4, 4), "rapid": (1, 1)})
        self.assertTrue(fx.cond("sr_fl_1_all_rapid", "=", "yes"))
        self.assertEqual(fx.num("sr_fl_1_endurance"), _fxn(12))

    def test_a_damaged_role_keeps_its_ratio(self):
        """The amount moves exactly at its strength now; its full by full x amount
        / now, multiplied first, never under the amount (so full >= now on both sides)."""
        fx = _Fx()
        fx.fleet(1, loc=2, war=("7.33333", "9.1"), rapid=(1, 1))
        fx.choose(0, war=3, rapid=0)
        self.go(fx, 1)
        ratio = Decimal("7.33333") / Decimal("9.1")
        for n, now in ((2, 3), (1, Decimal("4.33333"))):
            got_now, got_full = self.roles(fx, n)["war"]
            self.assertEqual(got_now, now)
            self.assertGreaterEqual(got_full, got_now)
            self.assertAlmostEqual(float(got_now / got_full), float(ratio), places=4)
        self.assertEqual(sum(self.roles(fx, n)["war"][1] for n in (1, 2)), Decimal("9.1"))
        # Undamaged, at a strength no product divides back exactly (7.33333 x 3 /
        # 7.33333 cuts to 2.99999): the floor keeps full at the amount.
        fx = _Fx()
        fx.fleet(1, loc=2, war=("7.33333", "7.33333"), rapid=(1, 1))
        fx.choose(0, war=3, rapid=0)
        self.go(fx, 1)
        self.assertEqual(self.roles(fx, 2)["war"], (3, 3))
        self.assertEqual(self.roles(fx, 1)["war"], (Decimal("4.33333"), Decimal("4.33333")))

    def test_the_marines_room(self):
        """There: the other fleet's own marines and carriers count; here: the
        carriers that stay. A fleet already past its room (carriers lost in
        battle) may still move marines out, or ships with no carriers; it can't
        move carriers away from its marines (owner, 2026-10-31)."""
        def room(**amounts):
            fx = _Fx(op=1)
            fx.fleet(1, loc=2, marines=2, war=(2, 2), carrier=(1, 1))
            fx.fleet(3, loc=2, marines=3, carrier=(2, 2))
            fx.choose(3, **amounts)
            return "sr_fl_xf_room_tt" not in fx.refusals("sr_fleet_transfer_sgui")
        self.assertFalse(room(marines=2))             # 5 there, room for 4
        self.assertTrue(room(marines=2, carrier=1))   # 5 there, room for 6; none here
        self.assertFalse(room(carrier=1))             # 2 here, room for none

        def over(**amounts):
            fx = _Fx(op=1)
            fx.fleet(1, loc=2, marines=4, war=(2, 2), carrier=(1, 1))   # room for 2: 2 over
            fx.fleet(3, loc=2, carrier=(3, 3))
            fx.choose(3, **amounts)
            return "sr_fl_xf_room_tt" not in fx.refusals("sr_fleet_transfer_sgui")
        self.assertTrue(over(marines=1))     # 3 here, 1 over
        self.assertTrue(over(war=1))         # still 2 over, no worse
        self.assertFalse(over(carrier=1))    # 4 over

    def test_the_fleet_it_goes_into_must_still_be_here(self):
        fx = _Fx(op=1)
        fx.fleet(1, loc=2, war=(4, 4))
        fx.fleet(3, loc=5, war=(4, 4))
        fx.choose(3, war=2)
        self.assertIn("sr_fl_xf_partner_here_tt", fx.refusals("sr_fleet_transfer_sgui"))
        before = dict(fx.vars)
        fx.effect("sr_fl_by_op", DO="transfer")
        self.assertEqual(fx.vars, before)
        fx.vars["sr_fl_3_loc"] = _fxn(2)
        self.assertEqual(fx.refusals("sr_fleet_transfer_sgui"), [])


def _gui_block(text, opener, start=0):
    """The body of the first `opener = {` block at or after start, and its end."""
    i = text.index(opener + " = {", start)
    depth = 0
    for j in range(i + len(opener) + 2, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + len(opener) + 4:j], j
    raise AssertionError(f"unclosed {opener}")


def _gui_blocks(text, opener):
    out, start = [], 0
    while (opener + " = {") in text[start:]:
        body, start = _gui_block(text, opener, start)
        out.append(body)
    return out


def _override_body(text, name):
    """A blockoverride's body (blockoverride "name" { ... }: no `=`)."""
    i = text.index(f'blockoverride "{name}" {{')
    j = text.index("{", i)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[j + 1:k]
    raise AssertionError(f"unclosed override {name}")


class DestinationPopupTest(unittest.TestCase):
    """UI pass design § 4: a fleet's destination button opens a popup with a
    row per location; a row's Choose sets the destination, and closes it."""

    @classmethod
    def setUpClass(cls):
        rows = _raw(gsf.ROOT / gsf.GUI_OUT)
        body = rows[rows.index("type te_sr_dest_popup_body = flowcontainer"):]
        cls.slots = _gui_blocks(body, "te_sr_dest_slot")
        cls.fleet_rows = _gui_blocks(rows[rows.index("type te_sr_fleet_rows"):rows.index("type te_sr_location_rows")],
                                     "te_sr_fleet_row")
        cls.display = _strip(_raw(gsf.ROOT / gsf.DISPLAY_OUT))
        cls.sguis = _strip(_raw(SGUIS))
        cls.generated = _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT))
        cls.gen_triggers = _strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT))

    def test_one_body_per_slot_and_one_row_per_location(self):
        self.assertEqual(len(self.slots), gsf.SLOTS)
        for n, slot in enumerate(self.slots, 1):
            with self.subTest(slot=n):
                self.assertEqual(_override_body(slot, "dp_visible").strip(),
                                 f"visible = \"[GetVariableSystem.HasValue('te_popup', 'sr_dest_{n}')]\"")
                rows = _gui_blocks(slot, "te_sr_dest_row")
                self.assertEqual([re.search(r'text = "sr_loc_name_(\w+)"', r).group(1) for r in rows],
                                 [lc.key for lc in gsf.LOCATIONS])
                for lc, row in zip(gsf.LOCATIONS, rows):
                    # hidden for where the fleet is
                    self.assertIn(f"Not( EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue("
                                  f"'sr_fl_{n}_loc_value'), '(CFixedPoint){lc.code}' ) )", _override_body(row, "dr_visible"))

    def test_each_row_passes_its_slot_and_location(self):
        for n, slot in enumerate(self.slots, 1):
            for lc, row in zip(gsf.LOCATIONS, _gui_blocks(slot, "te_sr_dest_row")):
                button = _override_body(row, "dr_button")
                with self.subTest(slot=n, location=lc.key):
                    self.assertEqual(set(re.findall(r"AddScope\( 'op', MakeScopeValue\( '\(CFixedPoint\)(\d+)' \) \)", button)),
                                     {str(n)})
                    self.assertEqual(set(re.findall(r"AddScope\( 'pick', MakeScopeValue\( '\(CFixedPoint\)(\d+)' \) \)", button)),
                                     {str(lc.code)})
                    self.assertEqual(set(re.findall(r"GetScriptedGui\('(\w+)'\)", button)), {"sr_fleet_set_dest_sgui"})
                    self.assertIn(".IsValidTooltip(", button)
                    # the leg's own figures, at this slot's pace from where it is
                    self.assertIn(f"ScriptValue('sr_fl_{n}_leg_months_{lc.key}')|0]", _override_body(row, "dr_months"))
                    short = _override_body(row, "dr_dv_short")
                    self.assertIn(f"Not( GreaterThanOrEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue("
                                  f"'sr_fl_{n}_dv_value'), JournalEntry.GetCountry.MakeScope.ScriptValue('sr_fl_{n}_leg_dv_{lc.key}') ) )",
                                  short)
                    self.assertIn("#R ", short)

    def test_picking_closes_the_popup(self):
        for n, slot in enumerate(self.slots, 1):
            for row in _gui_blocks(slot, "te_sr_dest_row"):
                onclicks = re.findall(r'(?m)^\s*onclick = "(.*)"$', _override_body(row, "dr_button"))
                with self.subTest(slot=n):
                    # the choice first, then the close, on one button
                    self.assertEqual(len(onclicks), 2)
                    self.assertTrue(onclicks[0].startswith("[GetScriptedGui('sr_fleet_set_dest_sgui').Execute("))
                    self.assertEqual(onclicks[1], "[GetVariableSystem.Clear('te_popup')]")

    def test_a_body_for_an_empty_slot_shows_only_its_note(self):
        """Review Focus 1: the slot's fleet leaves, merges or is destroyed with
        the popup open; nothing then acts on it. The rows show on the test the
        fleet row's orders show on (at a location), the note on its negation."""
        for n, (slot, row) in enumerate(zip(self.slots, self.fleet_rows), 1):
            with self.subTest(slot=n):
                here = re.search(r'visible = "\[(.*)\]"', _override_body(row, "fl_orders_visible")).group(1)
                self.assertEqual(_override_body(slot, "dp_here_visible").strip(), f'visible = "[{here}]"')
                self.assertEqual(_override_body(slot, "dp_gone_visible").strip(), f'visible = "[Not( {here} )]"')
        # the gone note sits outside the content's block
        gui = _raw(ROOT / "gui/journal_entry_widgets/space_race_widget.gui")
        slot_type = gui[gui.index("type te_sr_dest_slot = flowcontainer"):]
        content, end = _gui_block(slot_type, "flowcontainer")
        self.assertIn('block "dp_here_visible"', content)
        self.assertIn('block "dp_rows"', content)
        self.assertNotIn('block "dp_gone_visible"', content)
        self.assertIn('block "dp_gone_visible"', slot_type[end:slot_type.index("type te_sr_dest_header_row")])

    def test_the_why_value_covers_may_depart_s_slot_terms(self):
        for n in range(1, gsf.SLOTS + 1):
            body = _block(self.display, f"sr_disp_fl_{n}_why")
            depart = _block(self.gen_triggers, f"sr_fl_{n}_may_depart_mars")
            with self.subTest(slot=n):
                self.assertIn(f"sr_fl_{n}_refitting = yes", body)
                self.assertIn(f"sr_fl_{n}_strength < sr_fl_minimum_strength", body)
                self.assertIn("sr_launches_barred = yes", body)
                self.assertIn(f"sr_fl_{n}_at_earth = yes", body)
                # no Space Command first: it pauses a refit, so "leave when the
                # refit ends" would mislead
                self.assertRegex(body, r"value = 0\s*if = \{ limit = \{ NOT = \{ sr_sc_operational = yes \} \} value = 4 \}")
                # ... the same terms may_depart reads
                self.assertIn(f"NOT = {{ sr_fl_{n}_refitting = yes }}", depart)
                self.assertIn(f"sr_fl_{n}_strength >= sr_fl_minimum_strength", depart)
                self.assertIn("sr_launches_barred = yes", depart)
                self.assertIn("sr_sc_operational = yes", depart)
                self.assertEqual(sorted(int(v) for v in re.findall(r"value = (\d) \}", body)), [1, 2, 3, 4])
        # each code its note
        for n, slot in enumerate(self.slots, 1):
            for code in (1, 2, 3, 4):
                with self.subTest(slot=n, code=code):
                    self.assertIn(f"ScriptValue('sr_disp_fl_{n}_why'), '(CFixedPoint){code}'",
                                  _override_body(slot, f"dp_why_{code}_visible"))

    def test_the_choice_s_rule(self):
        """At a location, any location but its own; Go keeps the leg's gate."""
        sgui = _block(self.sguis, "sr_fleet_set_dest_sgui")
        self.assertIn("saved_scopes = { op pick }", sgui)
        valid = _block("x = {" + sgui.split("\n\tis_valid = {", 1)[1], "x")
        self.assertEqual(re.findall(r"TEST = (\w+)", valid), ["at_location", "pick_elsewhere"])
        # each reason its own line, a direct child of is_valid
        self.assertRegex(valid, r"^\s*custom_tooltip = \{\s*text = sr_fl_not_at_location_tt\s*sr_fl_op_check = "
                                r"\{ TEST = at_location \}\s*\}\s*custom_tooltip = \{\s*text = sr_fl_req_other_location_tt\s*"
                                r"sr_fl_op_check = \{ TEST = pick_elsewhere \}\s*\}\s*$")
        self.assertIn("sr_fl_by_op = { DO = set_pick }", sgui)
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                elsewhere = _block(self.gen_triggers, f"sr_fl_{n}_pick_elsewhere")
                self.assertIn(f"has_variable = sr_fl_{n}_loc", elsewhere)
                self.assertEqual(re.findall(r"AND = \{ scope:pick = (\d+) NOT = \{ var:sr_fl_\d_loc = (\d+) \} \}", elsewhere),
                                 [(str(lc.code), str(lc.code)) for lc in gsf.LOCATIONS])
        setter = _block(self.generated, "sr_fl_set_pick_at")
        self.assertEqual(re.findall(r"scope:pick = (\d+) \}\s*set_variable = \{ name = sr_fl_dest_pick_\$N\$ value = (\d+) \}",
                                    setter),
                         [(str(lc.code), str(lc.code)) for lc in gsf.LOCATIONS])
        # the old step to the next location is gone (#1298)
        self.assertNotIn("sr_fl_step_pick", self.generated)

    def test_the_window_shows_from_earth_only(self):
        for n, slot in enumerate(self.slots, 1):
            for lc, row in zip(gsf.LOCATIONS, _gui_blocks(slot, "te_sr_dest_row")):
                opened, wait = _override_body(row, "dr_win_open_visible"), _override_body(row, "dr_win_wait")
                with self.subTest(slot=n, location=lc.key):
                    if lc.code == gsf.EARTH:
                        self.assertEqual((opened.strip(), wait.strip()), ("visible = no", "visible = no"))
                        continue
                    at_earth = f"EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('sr_fl_{n}_loc_value'), '(CFixedPoint)1' )"
                    self.assertIn(f"And( {at_earth}, EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue("
                                  f"'sr_window_wait_months_{lc.body}'), '(CFixedPoint)0' ) )", opened)
                    self.assertIn(f"And( {at_earth}, GreaterThanOrEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue("
                                  f"'sr_window_wait_months_{lc.body}'), '(CFixedPoint)1' ) )", wait)
                    self.assertIn(f'text = "je_space_race_widget_win_wait_{lc.body}"', wait)

    def test_the_chosen_destination_is_marked(self):
        for n, slot in enumerate(self.slots, 1):
            pick = _block(self.display, f"sr_disp_fl_{n}_pick")
            self.assertIn(f"if = {{ limit = {{ has_variable = sr_fl_dest_pick_{n} }} value = var:sr_fl_dest_pick_{n} }}", pick)
            for lc, row in zip(gsf.LOCATIONS, _gui_blocks(slot, "te_sr_dest_row")):
                chosen = f"EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_fl_{n}_pick'), '(CFixedPoint){lc.code}' )"
                with self.subTest(slot=n, location=lc.key):
                    self.assertEqual(_override_body(row, "dr_chosen_visible").strip(), f'visible = "[{chosen}]"')
                    self.assertEqual(_override_body(row, "dr_choose_visible").strip(), f'visible = "[Not( {chosen} )]"')

    def test_our_worlds_at_each_location(self):
        for lc in gsf.LOCATIONS:
            body = _block(self.display, f"sr_disp_loc_worlds_{lc.key}")
            with self.subTest(location=lc.key):
                self.assertEqual(sorted(re.findall(r"global_var:sr_site_holder_(\w+) \?= this \} add = 1", body)),
                                 sorted(w.key for w in gsf.worlds_at(lc.key)))


class PostureRowTest(unittest.TestCase):
    """UI pass design § 7: the posture's four buttons, the one in force lit;
    each sets its posture with what taking it brings (a target, a price),
    where its rules allow."""

    @classmethod
    def setUpClass(cls):
        rows = _raw(gsf.ROOT / gsf.GUI_OUT)
        cls.fleet_rows = _gui_blocks(rows[rows.index("type te_sr_fleet_rows"):rows.index("type te_sr_location_rows")],
                                     "te_sr_fleet_row")
        cls.combat = _strip(_raw(COMBAT_EFFECTS))
        cls.sgui = _block(_strip(_raw(SGUIS)), "sr_fleet_set_posture_sgui")
        cls.gui = _raw(ROOT / "gui/journal_entry_widgets/space_race_widget.gui")

    def test_four_buttons_lit_on_the_current_posture(self):
        row_type = self.gui[self.gui.index("type te_sr_fleet_row = flowcontainer"):self.gui.index("type te_sr_dest_popup = ")]
        self.assertEqual(re.findall(r'text = "je_space_race_widget_fl_posture_(\d)"', row_type), ["1", "2", "3", "4"])
        self.assertEqual(row_type.count("te_sr_posture_choice = {"), 4)
        self.assertNotIn('block "fl_posture_button"', row_type)
        for n, row in enumerate(self.fleet_rows, 1):
            self.assertNotIn("sr_fleet_posture_sgui", row)
            for p in gsf.POSTURES:
                held = f"EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_fl_{n}_posture'), '(CFixedPoint){p}' )"
                with self.subTest(slot=n, posture=p):
                    self.assertEqual(_override_body(row, f"fl_posture_{p}_selected").strip(), f'visible = "[{held}]"')
                    self.assertEqual(_override_body(row, f"fl_posture_{p}_choice").strip(), f'visible = "[Not( {held} )]"')
                    button = _override_body(row, f"fl_posture_{p}_button")
                    self.assertEqual(set(re.findall(r"GetScriptedGui\('(\w+)'\)", button)), {"sr_fleet_set_posture_sgui"})
                    self.assertEqual(set(re.findall(r"AddScope\( 'op', MakeScopeValue\( '\(CFixedPoint\)(\d+)' \) \)", button)), {str(n)})
                    self.assertEqual(set(re.findall(r"AddScope\( 'pick', MakeScopeValue\( '\(CFixedPoint\)(\d+)' \) \)", button)), {str(p)})
                    self.assertIn(".IsValidTooltip(", button)
        # The button and the lit look share one slot, each with the label.
        choice = self.gui[self.gui.index("type te_sr_posture_choice = widget"):]
        choice = choice[:choice.index("\n\t}\n") + 3]
        self.assertIn("size = { 104 22 }", choice)
        self.assertIn("using = selected_tabs", choice)
        self.assertEqual(choice.count('block "pc_label"'), 2)
        # The posture line keeps the combat line's gate (at Earth, only while a
        # lunar world may be closed in on).
        combat = row_type[row_type.index('block "fl_combat_visible"'):]
        self.assertLess(combat.index("te_sr_posture_choice"), combat.index('block "fl_target_button"'))

    def test_set_posture_s_side_effects(self):
        body = _block(self.combat, "sr_fl_set_posture_at")
        for helper in ("sr_fl_charge_free_at", "sr_fl_charge_icpt_at", "sr_fl_step_hostile_target_at",
                       "sr_fl_step_icpt_target_at"):
            with self.subTest(helper=helper):
                self.assertEqual(body.count(f"{helper} = {{ N = $N$ }}"), 1)
        self.assertTrue(body.rstrip().endswith("sr_icpt_rebuild = yes"))
        close = _block("x = {" + body.split("limit = { scope:pick = 3 }", 1)[1], "x")
        self.assertIn("set_variable = { name = sr_fl_$N$_posture value = 3 }", close)
        self.assertRegex(close, r"NOT = \{ sr_fl_\$N\$_target_hostile = yes \}\s*\}\s*\}\s*sr_fl_step_hostile_target_at")
        self.assertLess(close.index("sr_fl_step_hostile_target_at"), close.index("sr_fl_charge_free_at"))
        self.assertIn("remove_variable = sr_fl_$N$_icpt", close)
        icpt = _block("x = {" + body.split("limit = { scope:pick = 4 }", 1)[1], "x")
        self.assertIn("set_variable = { name = sr_fl_$N$_posture value = 4 }", icpt)
        self.assertIn("remove_variable = sr_fl_$N$_destroy", icpt)
        self.assertRegex(icpt, r"NOT = \{ sr_fl_\$N\$_target_interdictable = yes \}\s*\}\s*sr_fl_step_icpt_target_at")
        self.assertLess(icpt.index("sr_fl_step_icpt_target_at"), icpt.index("sr_fl_charge_icpt_at"))
        rest = body[body.index("scope:pick = 1"):]
        for line in ("value = 1 }", "value = 2 }", "remove_variable = sr_fl_$N$_destroy", "remove_variable = sr_fl_$N$_icpt"):
            with self.subTest(line=line):
                self.assertIn(line, rest)
        self.assertNotIn("charge", rest)

    def test_each_pick_s_rule_is_its_own_line(self):
        valid = _block("x = {" + self.sgui.split("\n\tis_valid = {", 1)[1], "x")
        # direct children of is_valid: the unlisted checks, a trigger_if for
        # Stand off at Earth, Close in and Interdict, then no Space Command
        # (NoSpaceCommandTest)
        self.assertEqual(re.findall(r"(?m)^\t\t(\w+) = \{", valid),
                         ["hidden_trigger", "trigger_if", "trigger_if", "trigger_if", "custom_tooltip"])
        # true wherever the button shows (at a location; the held posture is lit,
        # not a button), so checked without a line (the hover's length)
        hidden = _block("x = {" + valid.split("hidden_trigger = {", 1)[1], "x")
        self.assertRegex(hidden, r"^\s*sr_fl_op_check = \{ TEST = at_location \}\s*"
                                 r"NOT = \{ sr_fl_op_check = \{ TEST = pick_is_posture \} \}\s*$")
        # Stand off's and Interdict's Earth lines show only at Earth, where they fail
        self.assertRegex(valid, r"limit = \{\s*scope:pick = 2\s*sr_fl_op_check = \{ TEST = at_earth \}\s*\}\s*"
                                r"custom_tooltip = \{\s*text = sr_fl_req_standoff_not_earth_tt\s*"
                                r"NOT = \{ sr_fl_op_check = \{ TEST = at_earth \} \}\s*\}\s*\}")
        self.assertRegex(valid, r"limit = \{ scope:pick = 3 \}\s*custom_tooltip = \{\s*text = sr_fl_req_hostile_world_tt\s*"
                                r"sr_fl_op_check = \{ TEST = has_hostile_world \}\s*\}\s*\}")
        self.assertRegex(valid, r"limit = \{ scope:pick = 4 \}\s*trigger_if = \{\s*limit = \{ sr_fl_op_check = \{ TEST = at_earth \} \}\s*"
                                r"custom_tooltip = \{\s*text = sr_fl_req_interdict_not_earth_tt\s*"
                                r"NOT = \{ sr_fl_op_check = \{ TEST = at_earth \} \}\s*\}\s*\}\s*trigger_else = \{\s*"
                                r"custom_tooltip = \{\s*text = sr_fl_req_interdict_world_tt\s*"
                                r"sr_fl_op_check = \{ TEST = has_interdict_world \}\s*\}\s*\}\s*\}")
        # no reason nested in another
        for m in re.finditer(r"custom_tooltip = \{", valid):
            with self.subTest(at=m.start()):
                self.assertNotIn("custom_tooltip", _block("x = {" + valid[m.end():], "x"))
        self.assertIn("sr_fl_by_op = { DO = set_posture }", self.sgui)
        for n in range(1, gsf.SLOTS + 1):
            body = _block(_strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT)), f"sr_fl_{n}_pick_is_posture")
            with self.subTest(slot=n):
                self.assertEqual(re.findall(rf"AND = \{{ scope:pick = (\d) sr_fl_{n}_posture_value = (\d) \}}", body),
                                 [(str(p), str(p)) for p in gsf.POSTURES])


def _parse_script(text):
    """A brace block's statements as (key, op, value) triples, value a word or
    a nested list: enough for the generated triggers' AND/OR/NOT trees."""
    tokens = re.findall(r"[{}]|[<>]=?|=|[^\s{}<>=]+", text)

    def block(i):
        out = []
        while i < len(tokens) and tokens[i] != "}":
            key, op = tokens[i], tokens[i + 1]
            if op not in ("=", "<", ">", "<=", ">="):
                out.append((key, None, None))  # a bare word (saved_scopes = { op pick })
                i += 1
                continue
            if tokens[i + 2] == "{":
                value, i = block(i + 3)
                i += 1
            else:
                value, i = tokens[i + 2], i + 3
            out.append((key, op, value))
        return out, i

    return block(0)[0]


def _eval_step_trigger(stmts, loc, target, hostile, free):
    """The generated hostile-step triggers' terms, for slot $N$ at location
    code loc, its target index (None without one), and the hostile and free
    worlds' keys."""
    def one(key, op, value):
        if key == "AND":
            return all(one(*s) for s in value)
        if key == "OR":
            return any(one(*s) for s in value)
        if key == "NOT":
            assert len(value) == 1, "NOT of more than one term"
            return not one(*value[0])
        if key == "has_variable":
            return {"sr_fl_$N$_loc": True, "sr_fl_$N$_target": target is not None}[value]
        if key == "var:sr_fl_$N$_loc" and op == "=":
            return loc == int(value)
        if key == "var:sr_fl_$N$_target" and op == "<":
            return target < int(value)
        if key == "has_global_variable" and value.startswith("sr_site_free_"):
            return value[len("sr_site_free_"):] in free
        if key == "sr_site_hostile_target":
            return dict((k, v) for k, _, v in value)["KEY"] in hostile
        raise AssertionError(f"unexpected term {key} {op} {value}")
    return all(one(*s) for s in stmts)


class CloseInPriceTest(unittest.TestCase):
    """Review of #1285: Close in without a hostile target takes the hostile
    step's world, and its hover must show the free colony's price whenever
    that world is free (sr_fl_<n>_hostile_step_free)."""

    @classmethod
    def setUpClass(cls):
        cls.triggers = _strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT))
        cls.effects = _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT))
        cls.sgui = _block(_strip(_raw(SGUIS)), "sr_fleet_set_posture_sgui")

    def _step(self, loc, target, hostile):
        """The world sr_fl_step_hostile_target_at takes, run from its own
        generated if-lines (first match in file order wins)."""
        step = _block(self.effects, "sr_fl_step_hostile_target_at")
        case = _block("x = {" + step.split(f"limit = {{ var:sr_fl_$N$_loc = {loc} }}", 1)[1], "x")
        tgt = target or 0
        for m in re.finditer(r"limit = \{ local_var:sr_fl_next = 0 (?:local_var:sr_fl_tgt < (\d+) )?"
                             r"sr_site_hostile_target = \{ KEY = (\w+) \} \} set_local_variable = \{ name = sr_fl_next "
                             r"value = (\d+) \}", case):
            if (m.group(1) is None or tgt < int(m.group(1))) and m.group(2) in hostile:
                return m.group(2)
        return None

    def test_each_slot_calls_the_shared_trigger(self):
        for n in range(1, gsf.SLOTS + 1):
            with self.subTest(slot=n):
                self.assertRegex(self.triggers, rf"(?m)^sr_fl_{n}_hostile_step_free = \{{ "
                                                rf"sr_fl_hostile_step_free_at = \{{ N = {n} \}} \}}$")

    def test_it_is_true_exactly_when_the_step_takes_a_free_colony(self):
        import random
        stmts = _parse_script(_block(self.triggers, "sr_fl_hostile_step_free_at"))
        rng = random.Random(1285)
        cases = 0
        for lc in gsf.CLOSE_IN_LOCATIONS:
            ws = [w.key for w in gsf.worlds_at(lc.key)]
            indices = [w.index for w in gsf.worlds_at(lc.key)]
            targets = [None, 0, 1, 999, *indices]
            for _ in range(300):
                hostile = {k for k in ws if rng.random() < 0.5}
                free = {k for k in ws if rng.random() < 0.5}
                target = rng.choice(targets)
                picked = self._step(lc.code, target, hostile)
                with self.subTest(loc=lc.key, target=target, hostile=sorted(hostile), free=sorted(free)):
                    self.assertEqual(_eval_step_trigger(stmts, lc.code, target, hostile, free),
                                     picked is not None and picked in free)
                cases += 1
            # a location elsewhere never matches
            self.assertFalse(_eval_step_trigger(stmts, 9999, None, set(ws), set(ws)))
        self.assertGreater(cases, 2000)

    def test_close_in_s_hover_lists_the_price_of_the_world_it_takes(self):
        effect = _block("x = {" + self.sgui.split("\n\teffect = {", 1)[1], "x")
        close = _block("x = {" + effect.split("limit = { scope:pick = 3 }", 1)[1], "x")
        self.assertRegex(close, r"limit = \{\s*OR = \{\s*AND = \{\s*sr_fl_op_check = \{ TEST = target_hostile \}\s*"
                                r"sr_fl_op_check = \{ TEST = closes_on_free \}\s*\}\s*AND = \{\s*"
                                r"NOT = \{ sr_fl_op_check = \{ TEST = target_hostile \} \}\s*"
                                r"sr_fl_op_check = \{ TEST = hostile_step_free \}\s*\}\s*\}\s*\}\s*"
                                r"custom_tooltip = sr_fl_free_price_tt")
        # ... the same split sr_fl_set_posture_at makes: a hostile target stays
        posture = _block(_strip(_raw(COMBAT_EFFECTS)), "sr_fl_set_posture_at")
        self.assertRegex(posture, r"OR = \{\s*NOT = \{ has_variable = sr_fl_\$N\$_target \}\s*"
                                  r"NOT = \{ sr_fl_\$N\$_target_hostile = yes \}\s*\}\s*\}\s*sr_fl_step_hostile_target_at")


def _loc_english():
    out = {}
    for path in sorted((ROOT / "localization/english").rglob("*_l_english.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r'^\s+([\w.]+):\d*\s+"(.*)"\s*(#.*)?$', line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def _rendered_length(loc, key):
    """A loc key's length as the review of #1285 measured it: $key$ spliced,
    each [..] two characters, formatting codes dropped."""
    text = re.sub(r"\$(\w+)\$", lambda m: "x" * _rendered_length(loc, m.group(1)) if m.group(1) in loc else m.group(0),
                  loc[key])
    text = re.sub(r"\[[^\[\]]*(\[[^\[\]]*\][^\[\]]*)*\]", "xx", text)
    text = re.sub(r"#[a-zA-Z_]+ ?|#!", "", text)
    return len(text.replace("\\n", "\n"))


class HoverLengthTest(unittest.TestCase):
    """Review of #1285: the posture buttons' and Target's hovers, built at
    runtime (IsValidTooltip, te_tt_break, ExecuteTooltip) where
    long_tooltip_audit can't see them, stay under 500 rendered characters in
    the worst case: every listed reason, every price that may show."""

    LIMIT = 500

    @classmethod
    def setUpClass(cls):
        cls.sguis = _strip(_raw(SGUIS))
        cls.loc = _loc_english()

    @staticmethod
    def _decide(limit, ctx):
        """True, False, or None (unknown: either may hold) for a limit's
        terms, from the pick and whether the fleet is at Earth."""
        def term(key, op, value):
            if key == "scope:pick":
                return ctx["pick"] == int(value)
            if key == "sr_fl_op_check" and isinstance(value, list) and value == [("TEST", "=", "at_earth")]:
                return ctx["at_earth"]
            if key == "OR":
                parts = [term(*t) for t in value]
                return True if True in parts else (None if None in parts else False)
            if key == "AND":
                return HoverLengthTest._decide(value, ctx)
            if key == "NOT":
                inner = HoverLengthTest._decide(value, ctx)
                return None if inner is None else not inner
            return None
        parts = [term(*t) for t in limit]
        return False if False in parts else (None if None in parts else True)

    def _lines(self, stmts, ctx):
        """The worst case's listed keys: an undecided branch counts its longest
        arm, an if-chain its longest taken arm."""
        out, i = [], 0
        while i < len(stmts):
            key, _, value = stmts[i]
            if key == "custom_tooltip":
                out.append(value if isinstance(value, str) else dict((k, v) for k, _, v in value)["text"])
            elif key in ("if", "trigger_if"):
                arms, j = [], i
                while j < len(stmts) and (j == i or stmts[j][0] in ("else_if", "else", "trigger_else")):
                    body = stmts[j][2]
                    limit = next((v for k, _, v in body if k == "limit"), None)
                    arms.append((self._decide(limit, ctx) if limit is not None else True,
                                 [s for s in body if s[0] != "limit"]))
                    j += 1
                worst = []
                for decided, body in arms:
                    if decided is False:
                        continue
                    lines = self._lines(body, ctx)
                    worst = max(worst, lines, key=lambda ks: sum(_rendered_length(self.loc, k) + 1 for k in ks))
                    if decided is True:
                        break
                out += worst
                i = j
                continue
            elif key in ("AND", "OR"):
                out += self._lines(value, ctx)
            i += 1
        return out

    def _hover(self, sgui, ctx):
        body = _parse_script(_block(self.sguis, sgui))
        valid = next(v for k, _, v in body if k == "is_valid")
        effect = next(v for k, _, v in body if k == "effect")
        keys = self._lines(valid, ctx), self._lines(effect, ctx)
        total = sum(sum(_rendered_length(self.loc, k) for k in part) + max(len(part) - 1, 0) for part in keys) + 2
        return total, keys

    def test_the_posture_buttons_and_target_stay_short(self):
        worst = {}
        for sgui, picks in (("sr_fleet_set_posture_sgui", (1, 2, 3, 4)), ("sr_fleet_set_target_sgui", (1,))):
            for pick in picks:
                for at_earth in (False, True):
                    total, keys = self._hover(sgui, {"pick": pick, "at_earth": at_earth})
                    worst[(sgui, pick, at_earth)] = total
                    with self.subTest(sgui=sgui, pick=pick, at_earth=at_earth, keys=keys):
                        self.assertLessEqual(total, self.LIMIT)
                        self.assertTrue(keys[1], "no effect lines read")
        # the walk reads the prices: Interdict's is its longest case
        self.assertGreater(worst[("sr_fleet_set_posture_sgui", 4, False)], 400)


def _gui_type(text, name):
    """A GUI type's body (`type <name> = <base> {`)."""
    m = re.search(rf"(?m)^\ttype {re.escape(name)} = [\w.]+ \{{", text)
    assert m, f"no type {name}"
    body, _ = _gui_block(text[m.start():].replace(m.group(0).strip(), "TYPE = {", 1), "TYPE")
    return body


def _enclosing(text, marker):
    """The opener and body of the innermost block around the one marker."""
    assert text.count(marker) == 1, f"{marker} {text.count(marker)} times"
    depth = 0
    for i in range(text.index(marker), -1, -1):
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth == 0:
                opener = re.search(r"([\w\"]+)\s*=?\s*$", text[:i]).group(1)
                body, _ = _gui_block("X = " + text[i:], "X")
                return opener, body
            depth -= 1
    raise AssertionError(f"no block around {marker}")


class HandWrittenWiringTest(unittest.TestCase):
    """Review of #1285: what the generated overrides can't show, the
    hand-written types' and effects' wiring: which element carries which
    block, each note's text against its code, each posture's value."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _raw(ROOT / "gui/journal_entry_widgets/space_race_widget.gui")
        rows = _raw(gsf.ROOT / gsf.GUI_OUT)
        cls.dest_slots = _gui_blocks(rows[rows.index("type te_sr_dest_popup_body"):rows.index("type te_sr_ftarget_popup_body")],
                                     "te_sr_dest_slot")
        cls.display = _strip(_raw(gsf.ROOT / gsf.DISPLAY_OUT))
        cls.combat = _strip(_raw(COMBAT_EFFECTS))

    def _button_and_lit(self, type_name, button_blocks, lit_blocks, button_text, lit_text, lit_tooltip):
        body = _gui_type(self.gui, type_name)
        for marker in button_blocks:
            with self.subTest(type=type_name, marker=marker):
                opener, block = _enclosing(body, f'block "{marker}" {{}}')
                self.assertEqual(opener, "button")
                self.assertIn("using = default_button_action", block)
                if button_text:
                    self.assertIn(f'text = "{button_text}"', block)
        for marker in lit_blocks:
            with self.subTest(type=type_name, marker=marker):
                opener, block = _enclosing(body, f'block "{marker}" {{}}')
                self.assertEqual(opener, "icon")
                self.assertIn("using = selected_tabs", block)
                if lit_text:
                    self.assertIn(f'text = "{lit_text}"', block)
                if lit_tooltip:
                    self.assertIn(f'tooltip = "{lit_tooltip}"', block)

    def test_the_posture_choice_lights_the_held_posture(self):
        """M16: the button carries pc_shown and pc_action, the lit icon
        pc_selected and the held posture's hover."""
        self._button_and_lit("te_sr_posture_choice", ("pc_shown", "pc_action"), ("pc_selected", "pc_held_tooltip"),
                             None, None, None)
        row = _gui_type(self.gui, "te_sr_fleet_row")
        choices = _gui_blocks(row, "te_sr_posture_choice")
        self.assertEqual(len(choices), 4)
        for p, choice in zip(gsf.POSTURES, choices):
            with self.subTest(posture=p):
                self.assertEqual(_override_body(choice, "pc_label").strip(), f'text = "je_space_race_widget_fl_posture_{p}"')
                self.assertEqual(_override_body(choice, "pc_shown").strip(), f'block "fl_posture_{p}_choice" {{}}')
                self.assertEqual(_override_body(choice, "pc_selected").strip(), f'block "fl_posture_{p}_selected" {{}}')
                self.assertEqual(_override_body(choice, "pc_action").strip(), f'block "fl_posture_{p}_button" {{}}')
                self.assertEqual(_override_body(choice, "pc_held_tooltip").strip(),
                                 f'tooltip = "je_space_race_widget_fl_posture_{p}_held_tt"')

    def test_choose_and_target_buttons_and_their_marks(self):
        """M17: Choose and Target are the buttons, Chosen and Targeted the lit
        marks, each with its hover."""
        self._button_and_lit("te_sr_dest_row", ("dr_choose_visible", "dr_button"), ("dr_chosen_visible",),
                             "je_space_race_widget_dp_choose", "je_space_race_widget_dp_chosen",
                             "je_space_race_widget_dp_chosen_tt")
        self._button_and_lit("te_sr_ftarget_row", ("fr_target_visible", "fr_button"), ("fr_targeted_visible",),
                             "je_space_race_widget_ss_target_button", "je_space_race_widget_ft_targeted",
                             "je_space_race_widget_ft_targeted_tt")

    def test_each_why_note_reads_its_code(self):
        """M13: note n's text is the reason code n stands for, and the code
        is set from that reason."""
        slot = _gui_type(self.gui, "te_sr_dest_slot")
        reasons = {1: ("refit", r"sr_fl_{n}_refitting = yes"),
                   2: ("weak", r"sr_fl_{n}_strength < sr_fl_minimum_strength"),
                   3: ("barred", r"sr_fl_{n}_at_earth = yes sr_launches_barred = yes"),
                   4: ("no_sc", r"NOT = { sr_sc_operational = yes }")}
        for code, (word, condition) in reasons.items():
            with self.subTest(code=code):
                opener, note = _enclosing(slot, f'block "dp_why_{code}_visible" {{}}')
                self.assertEqual(opener, "te_sr_note")
                self.assertEqual(re.findall(r'text = "(\w+)"', note), [f"je_space_race_widget_dp_why_{word}"])
                for n in range(1, gsf.SLOTS + 1):
                    why = _block(self.display, f"sr_disp_fl_{n}_why")
                    self.assertIn(f"limit = {{ {condition.replace('{n}', str(n))} }} value = {code} }}", why)

    def test_the_propellant_cells_split_on_one_comparison(self):
        """M20: covered shows where the fleet carries at least the leg's
        delta-v (equal included), short exactly where it doesn't."""
        for n, slot in enumerate(self.dest_slots, 1):
            for lc, row in zip(gsf.LOCATIONS, _gui_blocks(slot, "te_sr_dest_row")):
                with self.subTest(slot=n, location=lc.key):
                    covered = re.search(r'visible = "\[(.*)\]"', _override_body(row, "dr_dv_covered")).group(1)
                    self.assertEqual(covered, f"GreaterThanOrEqualTo_CFixedPoint( "
                                              f"JournalEntry.GetCountry.MakeScope.ScriptValue('sr_fl_{n}_dv_value'), "
                                              f"JournalEntry.GetCountry.MakeScope.ScriptValue('sr_fl_{n}_leg_dv_{lc.key}') )")
                    self.assertIn(f'visible = "[Not( {covered} )]"', _override_body(row, "dr_dv_short"))

    def test_station_and_stand_off_set_their_own_values(self):
        """M2: each posture button's branch sets its own posture."""
        body = _block(self.combat, "sr_fl_set_posture_at")
        for p in (3, 4):
            with self.subTest(posture=p):
                self.assertRegex(body, rf"limit = \{{ scope:pick = {p} \}}\s*"
                                       rf"set_variable = \{{ name = sr_fl_\$N\$_posture value = {p} \}}")
        self.assertRegex(body, r"if = \{\s*limit = \{ scope:pick = 1 \}\s*set_variable = \{ name = sr_fl_\$N\$_posture value = 1 \}\s*\}\s*"
                               r"else = \{\s*set_variable = \{ name = sr_fl_\$N\$_posture value = 2 \}\s*\}")
        # ... and the else arm is reached only by Stand off
        self.assertRegex(body, r"OR = \{\s*scope:pick = 1\s*scope:pick = 2\s*\}")
        self.assertEqual(len(re.findall(r"name = sr_fl_\$N\$_posture value = \d", body)), 4)


class TargetPopupTest(unittest.TestCase):
    """UI pass design § 7: the target button opens a list of the worlds at
    the fleet's location; Target sets the world and charges its price."""

    @classmethod
    def setUpClass(cls):
        rows = _raw(gsf.ROOT / gsf.GUI_OUT)
        cls.fleet_rows = _gui_blocks(rows[rows.index("type te_sr_fleet_rows"):rows.index("type te_sr_location_rows")],
                                     "te_sr_fleet_row")
        cls.slots = _gui_blocks(rows[rows.index("type te_sr_ftarget_popup_body"):], "te_sr_ftarget_slot")
        cls.generated = _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT))
        cls.gen_triggers = _strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT))
        cls.sgui = _block(_strip(_raw(SGUIS)), "sr_fleet_set_target_sgui")

    def test_the_target_button_opens_the_world_list(self):
        for n, row in enumerate(self.fleet_rows, 1):
            button = _override_body(row, "fl_target_button")
            with self.subTest(slot=n):
                self.assertEqual(re.findall(r'onclick = "(.*)"', button), [f"[GetVariableSystem.Set('te_popup', 'sr_ftarget_{n}')]"])
                self.assertIn("GetScriptedGui('sr_fleet_target_sgui').IsValid(", button)
                self.assertIn(f'tooltip = "je_space_race_widget_fl_{n}_target_tt"', button)
        self.assertEqual(len(self.slots), gsf.SLOTS)
        for n, slot in enumerate(self.slots, 1):
            with self.subTest(slot=n):
                self.assertEqual(_override_body(slot, "ft_visible").strip(),
                                 f"visible = \"[GetVariableSystem.HasValue('te_popup', 'sr_ftarget_{n}')]\"")
                rows = _gui_blocks(slot, "te_sr_ftarget_row")
                self.assertEqual([re.search(r'text = "sr_site_name_(\w+)"', r).group(1) for r in rows],
                                 [w.key for w in gss.panel_order()])
                for w, r in zip(gss.panel_order(), rows):
                    self.assertEqual(_override_body(r, "fr_visible").strip(),
                                     f"visible = \"[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue("
                                     f"'sr_fl_{n}_loc_value'), '(CFixedPoint){gsf.CODE[w.location]}' )]\"")

    def test_each_row_passes_its_slot_and_world_and_closes(self):
        for n, slot in enumerate(self.slots, 1):
            for w, r in zip(gss.panel_order(), _gui_blocks(slot, "te_sr_ftarget_row")):
                button = _override_body(r, "fr_button")
                onclicks = re.findall(r'(?m)^\s*onclick = "(.*)"$', button)
                with self.subTest(slot=n, world=w.key):
                    self.assertEqual(set(re.findall(r"AddScope\( 'op', MakeScopeValue\( '\(CFixedPoint\)(\d+)' \) \)", button)), {str(n)})
                    self.assertEqual(set(re.findall(r"AddScope\( 'pick', MakeScopeValue\( '\(CFixedPoint\)(\d+)' \) \)", button)),
                                     {str(w.index)})
                    self.assertEqual(len(onclicks), 2)
                    self.assertTrue(onclicks[0].startswith("[GetScriptedGui('sr_fleet_set_target_sgui').Execute("))
                    self.assertEqual(onclicks[1], "[GetVariableSystem.Clear('te_popup')]")
                    targeted = (f"EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_fl_{n}_target'), "
                                f"'(CFixedPoint){w.index}' )")
                    self.assertEqual(_override_body(r, "fr_targeted_visible").strip(), f'visible = "[{targeted}]"')
                    self.assertEqual(_override_body(r, "fr_target_visible").strip(), f'visible = "[Not( {targeted} )]"')

    def test_a_body_for_a_fleet_away_shows_only_its_note(self):
        for n, (slot, row) in enumerate(zip(self.slots, self.fleet_rows), 1):
            with self.subTest(slot=n):
                here = re.search(r'visible = "\[(.*)\]"', _override_body(row, "fl_orders_visible")).group(1)
                self.assertEqual(_override_body(slot, "ft_here_visible").strip(), f'visible = "[{here}]"')
                self.assertEqual(_override_body(slot, "ft_gone_visible").strip(), f'visible = "[Not( {here} )]"')

    def test_the_pick_s_rule(self):
        valid = _block("x = {" + self.sgui.split("\n\tis_valid = {", 1)[1], "x")
        # true wherever the popup shows the button: checked without a line
        hidden = _block("x = {" + valid.split("hidden_trigger = {", 1)[1], "x")
        self.assertRegex(hidden, r"^\s*sr_fl_op_check = \{ TEST = at_location \}\s*"
                                 r"sr_fl_op_check = \{ TEST = pick_world_here \}\s*$")
        self.assertRegex(valid, r"trigger_if = \{\s*limit = \{ sr_fl_op_check = \{ TEST = interdicting \} \}\s*"
                                r"custom_tooltip = \{\s*text = sr_fl_req_pick_interdictable_tt\s*sr_fl_pick_interdictable = yes\s*\}\s*\}\s*"
                                r"trigger_else = \{\s*custom_tooltip = \{\s*text = sr_fl_req_pick_hostile_tt\s*sr_fl_pick_hostile = yes")
        hostile = _block(self.gen_triggers, "sr_fl_pick_hostile")
        self.assertEqual(re.findall(r"scope:pick = (\d+) sr_site_hostile_target = \{ KEY = (\w+) \}", hostile),
                         [(str(w.index), w.key) for w in gss.SITES])
        icpt = _block(self.gen_triggers, "sr_fl_pick_interdictable")
        # never at Earth (lunar colonization § 8.3)
        self.assertEqual(re.findall(r"scope:pick = (\d+) sr_site_interdict_target = \{ KEY = (\w+) \}", icpt),
                         [(str(w.index), w.key) for w in gss.SITES if w.location != "earth"])
        for n in range(1, gsf.SLOTS + 1):
            here = _block(self.gen_triggers, f"sr_fl_{n}_pick_world_here")
            with self.subTest(slot=n):
                self.assertEqual(re.findall(rf"scope:pick = (\d+) var:sr_fl_{n}_loc = (\d+)", here),
                                 [(str(w.index), str(gsf.CODE[w.location])) for w in gss.SITES])

    def test_set_target_charges_its_price(self):
        body = _block(self.generated, "sr_fl_set_target_at")
        self.assertEqual(re.findall(r"scope:pick = (\d+) \}\s*set_variable = \{ name = sr_fl_\$N\$_target value = (\d+) \}", body),
                         [(str(w.index), str(w.index)) for w in gss.SITES])
        self.assertRegex(body, r"limit = \{ sr_fl_\$N\$_posture_value = 4 \}\s*sr_fl_charge_icpt_at = \{ N = \$N\$ \}\s*"
                               r"sr_icpt_rebuild = yes\s*\}\s*else_if = \{\s*limit = \{ sr_fl_\$N\$_posture_value = 3 \}\s*"
                               r"sr_fl_charge_free_at = \{ N = \$N\$ \}")
        # the price on the hover, where it is charged
        effect = _block("x = {" + self.sgui.split("\n\teffect = {", 1)[1], "x")
        self.assertRegex(effect, r"TEST = interdicting \} \}\s*custom_tooltip = sr_fl_set_icpt_target_tt\s*"
                                 r"custom_tooltip = sr_fl_interdict_price_tt")
        self.assertRegex(effect, r"sr_fl_op_check = \{ TEST = closing_in \}\s*sr_fl_pick_free = yes\s*\}\s*"
                                 r"custom_tooltip = sr_fl_free_price_tt")


class ButtonGateTest(unittest.TestCase):
    """#1298: the destination and target buttons open their popups and read
    only a gate's is_valid, for the greyed state and the reason on hover. The
    gates have no effect, and the old steps they ran, the posture step and
    its scripted GUI went with them."""

    GATES = {
        "sr_fleet_pick_sgui": ("fl_pick_button", "leg_tt",
                               [("sr_fl_not_at_location_tt", "sr_fl_op_check = { TEST = at_location }")]),
        "sr_fleet_target_sgui": ("fl_target_button", "target_tt",
                                 [("sr_fl_no_target_tt", "sr_fl_op_check = { TEST = can_target }"),
                                  ("sr_fl_req_space_command_tt", "sr_sc_operational = yes")]),
    }

    @classmethod
    def setUpClass(cls):
        cls.sguis = _strip(_raw(SGUIS))
        rows = _raw(gsf.ROOT / gsf.GUI_OUT)
        cls.fleet_rows = _gui_blocks(rows[rows.index("type te_sr_fleet_rows"):rows.index("type te_sr_location_rows")],
                                     "te_sr_fleet_row")
        cls.loc = _raw(ROOT / "localization/english/te_journal_entries_l_english.yml")

    def test_each_gate_keeps_its_reasons_and_has_no_effect(self):
        for name, (_, _, reasons) in self.GATES.items():
            body = _block(self.sguis, name)
            with self.subTest(sgui=name):
                self.assertEqual(re.findall(r"(?m)^\t(\w+) = ", body),
                                 ["scope", "saved_scopes", "is_shown", "ai_is_valid", "is_valid"])
                self.assertIn("saved_scopes = { op }", body)
                self.assertIn("sr_colonies_full_enabled = yes", _block(body.replace("\n\t", "\n"), "is_shown"))
                valid = _block(body.replace("\n\t", "\n"), "is_valid")
                self.assertEqual(re.findall(r"custom_tooltip = \{\s*text = (\w+)\n\s*([^\n]*)\n\s*\}", valid), reasons)
                self.assertEqual(valid.count("custom_tooltip"), len(reasons))

    def test_every_row_greys_and_explains_on_its_gate(self):
        self.assertEqual(len(self.fleet_rows), gsf.SLOTS)
        for name, (override, hover, _) in self.GATES.items():
            for n, row in enumerate(self.fleet_rows, 1):
                button = _override_body(row, override)
                scope = (f"GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', "
                         f"MakeScopeValue( '(CFixedPoint){n}' ) ).End")
                with self.subTest(sgui=name, slot=n):
                    self.assertEqual(re.findall(r'(?m)^\s*enabled = "(.*)"$', button),
                                     [f"[GetScriptedGui('{name}').IsValid( {scope} )]"])
                    self.assertNotIn("Execute", button)
                    self.assertIn(f'tooltip = "je_space_race_widget_fl_{n}_{hover}"', button)
                    text = re.search(rf"(?m)^ je_space_race_widget_fl_{n}_{hover}:0 \"(.*)\"$", self.loc).group(1)
                    self.assertTrue(text.startswith(f"[GetScriptedGui('{name}').IsValidTooltip( {scope} )]$te_tt_break$"))

    def test_the_old_steps_are_gone(self):
        texts = {"sguis": self.sguis, "combat": _strip(_raw(COMBAT_EFFECTS)),
                 "effects": _strip(_raw(gsf.ROOT / gsf.EFFECTS_OUT)), "triggers": _strip(_raw(gsf.ROOT / gsf.TRIGGERS_OUT))}
        for label, text in texts.items():
            for name in ("sr_fleet_posture_sgui", "sr_fl_step_pick_at", "sr_fl_step_pick_once", "sr_fl_step_posture_at",
                         "sr_fl_step_target_at", "next_interdict", "DO = step_"):
                with self.subTest(file=label, name=name):
                    self.assertNotIn(name, text)
        self.assertFalse({"step_pick", "step_posture", "step_target"} & set(gsf.SLOT_ACTIONS))
        loc = _loc_english()
        for key in ("sr_fl_pick_step_tt", "sr_fl_posture_tt", "sr_fl_posture_earth_tt", "sr_fl_icpt_target_tt",
                    "sr_fl_target_tt"):
            with self.subTest(key=key):
                self.assertNotIn(key, loc)
        # the target steps that Close in, Interdict and the console still take
        for name in ("sr_fl_step_hostile_target_at", "sr_fl_step_icpt_target_at"):
            with self.subTest(kept=name):
                self.assertIn(f"{name} = {{ N = $N$ }}", _block(texts["combat"], "sr_fl_set_posture_at"))


if __name__ == "__main__":
    unittest.main()
