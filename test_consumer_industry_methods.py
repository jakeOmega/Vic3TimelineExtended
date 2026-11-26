"""Consumer industries' production methods through the late eras (Workshop request, 2026-11-25).

A Workshop player found the textile mill, the furniture manufactory and the food industry
with nothing between their last base method (Electric Sewing Machines, era 4; Mechanized
Workshops, era 2; Food Additives, era 6) and era 13's Programmable Matter, apart from the
automation methods, which only cut staff. The owner agreed and asked that the food
industry's Distilleries (Patent Stills, era 2) and the manufactory's Luxury Production
(Precision Tools, era 2) get later tiers too, and that Programmable Food Synthesis make more
so it stays the top grocery method (docs/systems/mod_systems/production_methods.md
§ "Consumer industries").

These tests hold what the files must keep true: every new method unlocks on a technology
that exists, in the era the design names; each ladder sits in its group in order and rises in
output and in profit a level at base prices; a new base tier keeps the staff of the tier it
follows, and every method in another group that names that tier names the new ones too; a
method that takes goods off another one is never paired with one that has less of them; no
combination drives a profession below zero or leaves a level a token crew.

Everything is read from the files, through test_ranch_plantation_methods.py's loader: vanilla's
buildings, groups and methods from the committed vanilla_parsed/ snapshot under the mod's, and
goods' base prices as pm_costs.py reads them.

Run: python3 -m pytest test_consumer_industry_methods.py -q
     python3 test_consumer_industry_methods.py --table   (profit and staff a level at base prices)
"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

from test_ranch_plantation_methods import MARKER, QUOTAS, _data, _list, _loc  # noqa: E402

TEXTILE = "building_textile_mill"
FURNITURE = "building_furniture_manufactory"
FOOD = "building_food_industry"
MIN_STAFF = 100  # test_flat_crews.py's rule: a level keeps 0 or at least this many

# method: (technology, era). The era is the technology's, checked against the files.
NEW_METHODS = {
    "pm_permanent_press": ("modern_chemical_processes", 6),
    "pm_computerized_cutting": ("computer_aided_design", 8),
    "pm_whole_garment_knitting": ("additive_manufacturing", 10),
    "pm_tubular_steel_furniture": ("arc_welding", 5),
    "pm_molded_plywood_and_plastics": ("plastic_mass_production", 7),
    "pm_flat_pack_furniture": ("computer_aided_design", 8),
    "pm_bio_composite_panels": ("synthetic_biology", 11),
    "pm_modern_design_furniture": ("art_deco_architecture", 6),
    "pm_made_to_order_furniture": ("e-commerce", 9),
    "pm_enzymatic_processing": ("biotechnology", 9),
    "pm_precision_fermentation": ("synthetic_biology", 11),
    "pm_industrial_fermentation": ("stainless_steel_mass_production", 6),
    "pm_engineered_yeast": ("biotechnology", 9),
    "pm_molecular_spirits": ("synthetic_biology", 11),
}

# (building, group, the good the ladder makes, the ladder from the method it follows up).
# A base ladder ends on its era-13 method, which the new tiers sit before.
LADDERS = (
    (TEXTILE, "pmg_base_building_textile_mill", "clothes",
     ("pm_electric_sewing_machines", "pm_permanent_press", "pm_computerized_cutting",
      "pm_whole_garment_knitting", "pm_programmable_matter_clothing")),
    (FURNITURE, "pmg_base_building_furniture_manufactory", "furniture",
     ("pm_mechanized_workshops", "pm_tubular_steel_furniture", "pm_molded_plywood_and_plastics",
      "pm_flat_pack_furniture", "pm_bio_composite_panels", "pm_programmable_matter_furniture")),
    (FOOD, "pmg_base_building_food_industry", "groceries",
     ("pm_food_additives", "pm_enzymatic_processing", "pm_precision_fermentation",
      "pm_programmable_food_synthesis")),
    (FOOD, "pmg_distillery", "liquor",
     ("pm_patent_stills", "pm_industrial_fermentation", "pm_engineered_yeast", "pm_molecular_spirits")),
    (FURNITURE, "pmg_luxury_building_furniture_manufactory", "luxury_furniture",
     ("pm_precision_tools", "pm_modern_design_furniture", "pm_made_to_order_furniture")),
)
BASE_GROUPS = {"pmg_base_building_textile_mill", "pmg_base_building_furniture_manufactory",
               "pmg_base_building_food_industry"}
# Programmable Food Synthesis made 400 groceries a level before the new tiers; the owner agreed
# to raise it so it stays the top method (2026-11-25).
SYNTHESIS = ("pm_programmable_food_synthesis", 500)


def _ladder_new(ladder):
    return [m for m in ladder if m in NEW_METHODS]


def _unlockers(data, name):
    return _list(data.pms[name].get("unlocking_production_methods"))


def _signed_goods(data, name):
    """{(side, good): quantity} of one method, inputs and outputs alike."""
    return {(side, g): q for side in ("input", "output") for g, q in data.goods(name, side).items()}


class TechnologyTest(unittest.TestCase):
    def test_every_new_method_unlocks_on_an_existing_technology_of_its_era(self):
        data = _data()
        for name, (tech, era) in NEW_METHODS.items():
            with self.subTest(method=name):
                self.assertIn(name, data.pms)
                self.assertEqual(data.techs_of(name), [tech])
                self.assertIn(tech, data.techs)
                self.assertEqual(data.era(tech), era)


class LadderTest(unittest.TestCase):
    def test_each_ladder_sits_in_its_group_in_order(self):
        data = _data()
        for building, group, _good, ladder in LADDERS:
            with self.subTest(group=group):
                self.assertIn(group, data.groups(building))
                methods = data.methods(group)
                start = methods.index(ladder[0])
                self.assertEqual(tuple(methods[start:start + len(ladder)]), ladder)
                if group in BASE_GROUPS:
                    self.assertEqual(methods[-1], ladder[-1], "the era-13 method stays last")

    def test_each_ladder_rises(self):
        """Each tier makes more of the ladder's good and more profit a level at base prices
        than the one below it, and a later technology unlocks it."""
        data = _data()
        for _building, group, good, ladder in LADDERS:
            previous = None
            for name in ladder:
                made = data.goods(name, "output")[good]
                cost, value = data.value([name])
                era = data.era(data.techs_of(name)[0])
                with self.subTest(group=group, method=name):
                    if previous:
                        self.assertGreater(made, previous[0])
                        self.assertGreater(value - cost, previous[1])
                        self.assertGreater(era, previous[2])
                previous = (made, value - cost, era)

    def test_programmable_food_synthesis_was_raised(self):
        data = _data()
        name, groceries = SYNTHESIS
        self.assertEqual(data.goods(name, "output")["groceries"], groceries)

    def test_a_new_tier_keeps_the_staff_of_the_tier_it_follows(self):
        """The automation methods cut the base methods' staff by fixed amounts, and the
        Distilleries add theirs to the base method's, so a new tier hires what the tier
        before it hired, profession by profession."""
        data = _data()
        for _building, group, _good, ladder in LADDERS:
            if group == "pmg_luxury_building_furniture_manufactory":
                continue  # its tiers hire shopkeepers only, as Precision Tools does
            for name in _ladder_new(ladder):
                with self.subTest(method=name):
                    self.assertEqual(data.staff(name), data.staff(ladder[0]))


class GatingTest(unittest.TestCase):
    def test_methods_gated_on_the_old_top_tier_accept_the_new_ones(self):
        """The class of bug test_textile_mill_elastics.py guards: a method in another group
        that names a base method can't be chosen on a building running a later one it doesn't
        name, with no log line. Every method that names the tier a ladder follows names each
        new tier too."""
        data = _data()
        for building, group, _good, ladder in LADDERS:
            if group not in BASE_GROUPS:
                continue
            for other in data.groups(building):
                if other == group:
                    continue
                for name in data.methods(other):
                    needs = _unlockers(data, name)
                    if ladder[0] not in needs:
                        continue
                    for new in _ladder_new(ladder):
                        with self.subTest(method=name, base=new):
                            self.assertIn(new, needs)

    def test_nothing_takes_off_more_than_its_partner_has(self):
        """Luxury, branding, canning and distilling methods take goods off the base method
        (Precision Tools 25 wood and 55 furniture). Paired with a new method, or a new one
        paired with any base it runs on, the partner has at least that much of each good."""
        data = _data()
        for building in (TEXTILE, FURNITURE, FOOD):
            groups = data.groups(building)
            base = data.methods(groups[0])
            for group in groups[1:]:
                for name in data.methods(group):
                    taken = {k: -q for k, q in _signed_goods(data, name).items() if q < 0}
                    if not taken:
                        continue
                    needs = _unlockers(data, name)
                    for partner in base:
                        if needs and partner not in needs:
                            continue
                        if name not in NEW_METHODS and partner not in NEW_METHODS:
                            continue
                        has = _signed_goods(data, partner)
                        for key, q in taken.items():
                            with self.subTest(method=name, base=partner, good=key):
                                self.assertGreaterEqual(has.get(key, 0), q)


class EmploymentTest(unittest.TestCase):
    """pm_employment_audit's and test_flat_crews.py's rules, for these buildings by name."""

    def test_no_combination_goes_negative_or_keeps_a_token_crew(self):
        data = _data()
        for building in (TEXTILE, FURNITURE, FOOD):
            combos = data.combos(building)
            with self.subTest(building=building):
                self.assertTrue(combos)
                for combo in combos:
                    staff = data.by_profession(combo)
                    negative = {k: v for k, v in staff.items() if v < 0}
                    self.assertFalse(negative, f"{' + '.join(combo)}: {negative}")
                    total = sum(staff.values())
                    self.assertFalse(0 < total < MIN_STAFF, f"{' + '.join(combo)} keeps {total:.0f} a level")

    def test_the_new_methods_are_not_robotic(self):
        data = _data()
        for name in NEW_METHODS:
            with self.subTest(method=name):
                self.assertNotIn(MARKER, data.modifiers(name, "unscaled"))
                self.assertNotIn(QUOTAS, _list(data.pms[name].get("disallowing_laws")))


class LocTest(unittest.TestCase):
    def test_every_new_method_has_a_name_and_a_description(self):
        loc = _loc()
        for name in NEW_METHODS:
            with self.subTest(method=name):
                self.assertTrue(loc.get(name))
                self.assertTrue(loc.get(f"{name}_desc"))
                self.assertNotRegex(loc[f"{name}_desc"], r"\d", "a method description carries no figures")


def _table():
    data = _data()
    print(f"{'Method':34s} {'Era':>3s} {'Input':>7s} {'Output':>7s} {'Profit':>7s} {'Staff':>6s} {'Per head':>8s}")
    for _building, group, _good, ladder in LADDERS:
        print(group)
        for name in ladder:
            cost, value = data.value([name])
            staff = sum(data.staff(name).values())
            per = (value - cost) / staff if staff else float("nan")
            era = data.era(data.techs_of(name)[0])
            print(f"  {name:32s} {era:3d} {cost:7.0f} {value:7.0f} {value - cost:7.0f} {staff:6.0f} {per:8.2f}")


if __name__ == "__main__":
    if "--table" in sys.argv:
        _table()
    else:
        unittest.main()
