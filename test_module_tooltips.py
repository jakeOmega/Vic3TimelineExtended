"""The colony modules' + buttons say what a level does, in the script's figures.

Each module's + button (sr_colony_module_sgui, scope:op its code, in the
Modules view and on a colony's page) shows sr_mod_queue_<type>_tt. #2141
doubled the Off-World Resort's room to 20 and its + button still said 10; the
Cultural Center's left out its Resort Draw, the Training Ground's the marines
and the Orbital Yard's Space Command. These tests read each figure from the
script value, modifier or generator constant that sets it, so a change to one
fails here until the tooltip follows.

Run: python3 -m pytest test_module_tooltips.py -q
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import gen_solar_sites as gss  # noqa: E402

MISC = ROOT / "localization/english/te_miscellaneous_l_english.yml"
JE = ROOT / "localization/english/te_journal_entries_l_english.yml"
SGUI = ROOT / "common/scripted_guis/sr_colony_sguis.txt"
MODULE_VALUES = ROOT / "common/script_values/sr_colony_module_values.txt"
FLEET_VALUES = ROOT / "common/script_values/sr_fleet_values.txt"
AUTONOMY_VALUES = ROOT / "common/script_values/sr_colony_autonomy_values.txt"
MODIFIERS = ROOT / "common/static_modifiers/space_race_modifiers.txt"
TECHNOLOGIES = ROOT / "common/technology/technologies"

# The loc key's suffix for a module code's type (gss.MODULE_CODES), where it differs.
KEY_SUFFIX = {"a": "spec_a", "b": "spec_b"}


def _raw(path):
    return Path(path).read_text(encoding="utf-8-sig")


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    assert m, f"no block {name}"
    depth, i = 1, m.end()
    while depth:
        depth += text[i] == "{"
        depth -= text[i] == "}"
        i += 1
    return text[m.start():i]


def _value(path, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{ value = (-?[\d.]+) \}}", _strip(_raw(path)))
    assert m, f"no value {name} in {path}"
    return float(m.group(1))


def _field(modifier, field):
    body = _block(_strip(_raw(MODIFIERS)), modifier)
    return float(re.search(rf"\b{field} = (-?[\d.]+)", body).group(1))


def _loc(path, key):
    m = re.search(rf'(?m)^ {re.escape(key)}:0 "(.*)"$', _raw(path))
    assert m, f"no loc key {key}"
    return m.group(1)


def _num(x):
    """A figure as the tooltips write it: 20, 0.5."""
    return f"{x:g}"


def _pct(x):
    """A share as a percent: 0.03 -> 3%."""
    return f"{round(x * 100):g}%"


def _queue_tt(code_type):
    return f"sr_mod_queue_{KEY_SUFFIX.get(code_type, code_type)}_tt"


class EveryModuleHasItsLine(unittest.TestCase):
    def test_each_code_names_its_tooltip(self):
        sgui = _strip(_block(_raw(SGUI), "sr_colony_module_sgui"))
        effect = _block(sgui, "effect")
        for t, code in gss.MODULE_CODES.items():
            key = _queue_tt(t)
            with self.subTest(type=t, code=code):
                self.assertRegex(effect, rf"limit = \{{ scope:op = {code} \}}\s*custom_tooltip = \{{\s*text = {key}\s")
                _loc(MISC, key)


class FiguresMatchTheScript(unittest.TestCase):
    def assertSays(self, key, *parts):
        text = _loc(MISC, key)
        for part in parts:
            with self.subTest(key=key, part=part):
                self.assertIn(part, text)

    def test_off_world_resort(self):
        room = _value(MODULE_VALUES, "sr_mod_resort_room")
        self.assertSays("sr_mod_queue_resort_tt", f"#v {_num(room)}#! more $building_space_resort$ room",
                        "[concept_sr_resort_draw]")

    def test_cultural_center(self):
        self.assertSays("sr_mod_queue_culture_tt",
                        f"#v +{_pct(_field('sr_module_culture', 'country_cultural_pull_mult'))}#! cultural pull",
                        f"#v +{_pct(_field('sr_module_culture', 'country_prestige_mult'))}#! prestige",
                        f"#v +{_num(_value(MODULE_VALUES, 'sr_mod_culture_draw'))}#! point of [concept_sr_resort_draw]")

    def test_mining_complex(self):
        room = _value(MODULE_VALUES, "sr_mod_mine_room")
        self.assertSays("sr_mod_queue_mine_tt", f"#v {_num(room)}#! more $building_space_mine$ room",
                        "[concept_sr_base_grade]")

    def test_orbital_yard(self):
        self.assertSays("sr_mod_queue_yard_tt",
                        f"#v {_num(_value(MODULE_VALUES, 'sr_mod_yard_points'))}#! more Module Fabrication points",
                        f"#v {_num(_value(MODULE_VALUES, 'sr_mod_yard_ships'))}#! fleet strength a month to Space Command",
                        "[concept_sr_yard_reach]")

    def test_research_station(self):
        cap = _field("sr_module_lab", "country_weekly_innovation_max_add")
        self.assertSays("sr_mod_queue_lab_tt", f"#v +{_num(cap)}#! [concept_innovation] cap")

    def test_black_site(self):
        self.assertSays("sr_mod_queue_black_tt",
                        f"#v +{_num(_field('sr_module_black', 'country_intelligence_capacity_add'))}#! intelligence capacity",
                        f"#v +{_pct(_field('sr_module_black', 'country_covert_operation_efficiency_mult'))}#! covert")

    def test_training_ground(self):
        per = _value(MODULE_VALUES, "sr_mod_train_marines_per_level")
        top = _value(MODULE_VALUES, "sr_mod_train_marines_max")
        self.assertSays("sr_mod_queue_train_tt",
                        f"#v +{_pct(_field('sr_module_train', 'unit_army_experience_gain_mult'))}#! army experience gain",
                        f"[concept_sr_marines] also count #v {_pct(per)}#! more", f"at most #v +{_pct(per * top)}#!")

    def test_nuclear_command_center(self):
        self.assertSays("sr_mod_queue_bunker_tt",
                        f"#v +{_num(_value(MODULE_VALUES, 'sr_mod_bunker_reliability_per_level'))}#! nuclear command reliability",
                        f"at most #v +{_num(_value(MODULE_VALUES, 'sr_mod_bunker_reliability_max'))}#!",
                        f"#v +{_num(_value(MODULE_VALUES, 'sr_mod_bunker_redundancy_per_level'))}#! [concept_command_redundancy]",
                        f"at most #v +{_num(_value(MODULE_VALUES, 'sr_mod_bunker_redundancy_max'))}#!")

    def test_materials_foundry(self):
        out = _field("sr_module_foundry", "goods_output_advanced_materials_mult")
        self.assertSays("sr_mod_queue_foundry_tt", f"#v +{_pct(out)}#! advanced materials output")

    def test_administration(self):
        self.assertSays("sr_mod_queue_admin_tt",
                        f"#v {_num(_value(AUTONOMY_VALUES, 'sr_aut_per_admin_level'))}#! a month to the colony's autonomy",
                        f"#R {_num(_field('sr_module_admin', 'country_authority_cost_add'))}#! [concept_authority]")

    def test_spaceport(self):
        self.assertSays("sr_mod_queue_port_tt",
                        f"repair #v {_pct(_value(FLEET_VALUES, 'sr_fl_repair_port_level'))}#! of their damage a month a level",
                        f"comes back at #v {_num(_value(FLEET_VALUES, 'sr_integrity_regain_port'))}#! a month "
                        f"instead of #v {_num(_value(FLEET_VALUES, 'sr_integrity_regain'))}#!")

    def test_habitat(self):
        techs = {}
        for path in sorted(TECHNOLOGIES.glob("*.txt")):
            text = _strip(_raw(path))
            for m in re.finditer(r"(?m)^(\w+) = \{", text):
                body = _block(text, m.group(1))
                found = re.search(r"\bcountry_sr_habitat_room_add = ([\d.]+)", body)
                if found:
                    techs[m.group(1)] = float(found.group(1))
        self.assertEqual(len(set(techs.values())), 1, techs)
        self.assertSays("sr_mod_queue_hab_tt", f"#v {_pct(gss.HABITAT_BASE_SHARE)}#! of the colony's starting room",
                        f"#v {round(next(iter(techs.values())) * 100):g}#! points more",
                        *(f"${t}$" for t in techs))


class ResortHoversMatchTheRoom(unittest.TestCase):
    """The other hovers that give the resort room's figures (#2141 left them at 10)."""

    def test_the_overview_hover(self):
        rooms = [s.resort_room for s in gss.SITES]
        module = _num(_value(MODULE_VALUES, "sr_mod_resort_room"))
        text = _loc(JE, "je_space_race_widget_resort_tt")
        self.assertIn(f"Earth orbit gives room for {gss.ORBIT_RESORT_ROOM} $building_space_resort$ levels", text)
        self.assertIn(f"from {min(rooms)} levels to {max(rooms)}, and {module} more a staffed level", text)

    def test_the_colony_and_site_hovers(self):
        module = _num(_value(MODULE_VALUES, "sr_mod_resort_room"))
        self.assertIn(f"Off-World Resorts adds #v {module}#! levels", _loc(JE, "je_space_race_widget_resorts_tt"))
        self.assertIn(f"Off-World Resorts add #v {module}#! levels", _loc(JE, "je_space_race_widget_ss_resorts_tt"))
        self.assertIn(f"adds #v {module}#! levels of room here", _loc(JE, "je_space_race_widget_mod_resort_tt"))


if __name__ == "__main__":
    unittest.main()
