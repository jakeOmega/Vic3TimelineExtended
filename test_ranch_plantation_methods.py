"""Livestock ranch and plantation ladders, and tobacco in the late eras (Workshop request, 2026-11-15).

A Workshop player found the ranch's meat ladder stopping at vanilla's era-4 method, no labor
saving after Electric Fences, no labor-saving group on plantations, and no late source of
tobacco. The mod answers with (docs/systems/mod_systems/production_methods.md
§ "Livestock ranches and plantations"):

- three meat tiers in the ranch's base group (Industrial Feedlots, era 7; Recombinant Growth
  Hormones, era 9; Gene-Edited Livestock, era 11), which the wool group's methods unlock on;
- two tiers in the ranch's Herd Management group, vanilla's Fencing (Mechanized Feeding Lines,
  era 7; Robotic Barns, era 10, robotic, so Human Labor Quotas withdraws it);
- a Harvesting Process group on every plantation-type building (Hand Harvesting, Mechanical
  Harvesters, era 8; Autonomous Harvesters, era 11, robotic);
- a secondary group on the Cultured Produce Facility whose Cultured Tobacco Leaf turns part of
  its fruit into tobacco, the only plantation good no late building made.

These tests hold what the files must keep true: every method unlocks on a technology that
exists, in the era the design names; each ladder rises; no combination of a building's methods
drives a profession below zero or leaves a level a token crew; the robotic tiers carry the
Automation Policy marker; tobacco has its new source.

Everything is read from the files: vanilla's buildings, groups and methods from the committed
vanilla_parsed/ snapshot under the mod's, as ModState merges them, and goods' base prices as
pm_costs.py reads them.

Run: python3 -m pytest test_ranch_plantation_methods.py -q
     python3 test_ranch_plantation_methods.py --table   (profit and staff a level at base prices)
"""
import glob
import itertools
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

RANCH = "building_livestock_ranch"
RANCH_BASE = "pmg_base_building_livestock_ranch"
RANCH_WOOL = "pmg_sheep_ranch"
HERD = "pmg_fencing"
MARKER = "building_robotic_or_ai_managed_bool"
QUOTAS = "law_human_labor_quotas"

# method: (technology, era). The era is the technology's, checked against the files.
NEW_METHODS = {
    "pm_industrial_feedlots": ("green_revolution", 7),
    "pm_recombinant_growth_hormones": ("biotechnology", 9),
    "pm_gene_edited_livestock": ("genetic_engineering", 11),
    "pm_mechanized_feeding_lines": ("green_revolution", 7),
    "pm_robotic_barns": ("internet_of_things", 10),
}
NEW_RANCH_BASES = ("pm_industrial_feedlots", "pm_recombinant_growth_hormones", "pm_gene_edited_livestock")
# The ranch's base group from vanilla's top method up, and Herd Management from Electric Fences up.
RANCH_MEAT_LADDER = ("pm_mechanized_slaughtering",) + NEW_RANCH_BASES
HERD_LADDER = ("pm_standard_fences", "pm_barbed_wire_fences", "pm_electric_fencing",
               "pm_mechanized_feeding_lines", "pm_robotic_barns")
ROBOTIC = ("pm_robotic_barns",)
NOT_ROBOTIC = ("pm_mechanized_feeding_lines",) + NEW_RANCH_BASES

# Buildings whose every method combination is checked for negative or token staff.
CHECKED_BUILDINGS = (RANCH,)
MIN_STAFF = 100  # test_flat_crews.py's rule: a level keeps 0 or at least this many


def _body(value):
    while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def _list(value):
    value = _body(value)
    if value is None:
        return []
    return [value] if isinstance(value, str) else [_body(v) for v in value]


def _block(modifiers, key):
    """One scaling block of a method's modifiers as a flat dict (a repeated block is merged)."""
    value = _body(modifiers.get(key)) if isinstance(modifiers, dict) else None
    if value is None:
        return {}
    blocks = [_body(v) for v in value] if isinstance(value, list) else [value]
    out = {}
    for block in blocks:
        for k, v in block.items():
            out[k] = _body(v)
    return out


class _Data:
    def __init__(self):
        import vanilla_parsed
        from mod_state import VANILLA_COMMON_DIRS, ModState
        import pm_costs

        types = ("Buildings", "PM Groups", "PMs", "Technologies")
        snapshot = vanilla_parsed.load(os.path.join(REPO, "vanilla_parsed"))
        vanilla = {k: v for k, v in snapshot.data.items() if k in types}
        state = ModState({k: "" for k in types},
                         {k: os.path.join(REPO, "common", *VANILLA_COMMON_DIRS[k].split("/")) for k in types},
                         vanilla_data=vanilla)
        data = {k: {n: _body(v) for n, v in state.get_data(k).items()} for k in types}
        self.buildings, self.groups_by_name = data["Buildings"], data["PM Groups"]
        self.pms, self.techs = data["PMs"], data["Technologies"]
        self.prices = pm_costs.load_goods()

    def groups(self, building):
        return [g for g in _list(self.buildings[building].get("production_method_groups"))
                if g in self.groups_by_name and not g.startswith(("pmg_maintenance", "pmg_carbon_capture_"))]

    def methods(self, group):
        return [m for m in _list(self.groups_by_name[group].get("production_methods")) if m in self.pms]

    def modifiers(self, name, scaling):
        return _block(_body(self.pms[name].get("building_modifiers")) or {}, scaling)

    def staff(self, name):
        """{profession: per-level staff} of one method."""
        return {k[len("building_employment_"):-len("_add")]: float(v)
                for k, v in self.modifiers(name, "level_scaled").items()
                if k.startswith("building_employment_") and k.endswith("_add")}

    def goods(self, name, side):
        prefix = f"goods_{side}_"
        return {k[len(prefix):-len("_add")]: float(v) for k, v in self.modifiers(name, "workforce_scaled").items()
                if k.startswith(prefix) and k.endswith("_add")}

    def value(self, names):
        """(input cost, output value) a level at base prices of a set of methods."""
        cost = sum(q * self.prices[g] for n in names for g, q in self.goods(n, "input").items())
        value = sum(q * self.prices[g] for n in names for g, q in self.goods(n, "output").items())
        return cost, value

    def techs_of(self, name):
        return _list(self.pms[name].get("unlocking_technologies"))

    def era(self, tech):
        return int(str(_body(self.techs[tech].get("era"))).replace("era_", ""))

    def valid(self, combo):
        chosen = set(combo)
        for name in combo:
            needs = _list(self.pms[name].get("unlocking_production_methods"))
            if needs and not chosen & set(needs):
                return False
        return True

    def combos(self, building):
        methods = [self.methods(g) for g in self.groups(building)]
        return [c for c in itertools.product(*methods) if self.valid(c)]

    def by_profession(self, combo):
        out = {}
        for name in combo:
            for k, v in self.staff(name).items():
                out[k] = out.get(k, 0.0) + v
        return out


_DATA = None


def _data():
    global _DATA
    if _DATA is None:
        _DATA = _Data()
    return _DATA


def _loc():
    out = {}
    for path in glob.glob(os.path.join(REPO, "localization", "english", "**", "*.yml"), recursive=True):
        with open(path, encoding="utf-8-sig") as f:
            for m in re.finditer(r'^ ([\w.\-]+):\d* "(.*)"\s*$', f.read(), re.M):
                out[m.group(1)] = m.group(2)
    return out


class TechnologyTest(unittest.TestCase):
    def test_every_new_method_unlocks_on_an_existing_technology_of_its_era(self):
        data = _data()
        for name, (tech, era) in NEW_METHODS.items():
            with self.subTest(method=name):
                self.assertIn(name, data.pms)
                self.assertEqual(data.techs_of(name), [tech])
                self.assertIn(tech, data.techs)
                self.assertEqual(data.era(tech), era)


class RanchTest(unittest.TestCase):
    def test_the_new_tiers_sit_in_the_ranch_groups_in_order(self):
        data = _data()
        self.assertEqual(data.groups(RANCH)[:3], [RANCH_BASE, RANCH_WOOL, HERD])
        base = data.methods(RANCH_BASE)
        self.assertEqual(tuple(base[-len(RANCH_MEAT_LADDER):]), RANCH_MEAT_LADDER)
        self.assertEqual(tuple(data.methods(HERD)), HERD_LADDER)

    def test_the_meat_ladder_rises(self):
        """Each tier makes more meat and more profit a level at base prices than the one
        below it, a later technology unlocks it, and it keeps the same 5,000 staff."""
        data = _data()
        previous = None
        for name in RANCH_MEAT_LADDER:
            meat = data.goods(name, "output")["meat"]
            cost, value = data.value([name])
            era = data.era(data.techs_of(name)[0])
            with self.subTest(method=name):
                self.assertEqual(sum(data.staff(name).values()), 5000)
                if previous:
                    self.assertGreater(meat, previous[0])
                    self.assertGreater(value - cost, previous[1])
                    self.assertGreater(era, previous[2])
            previous = (meat, value - cost, era)

    def test_herd_management_cuts_more_labor_at_each_tier(self):
        data = _data()
        previous = None
        for name in HERD_LADDER:
            cut = -sum(data.staff(name).values())
            techs = data.techs_of(name)
            era = data.era(techs[0]) if techs else 1
            with self.subTest(method=name):
                if previous:
                    self.assertGreater(cut, previous[0])
                    self.assertGreaterEqual(era, previous[1])
            previous = (cut, era)

    def test_the_wool_methods_unlock_on_the_new_bases(self):
        """Intensive Wool Gathering (vanilla, INJECTed) and Antibiotic Growth Promoters
        need one of the base methods; a ranch on a new tier keeps them."""
        data = _data()
        for name in ("pm_intensive_grazing_ranch", "pm_antibiotic_growth_promoters"):
            needs = _list(data.pms[name].get("unlocking_production_methods"))
            for base in NEW_RANCH_BASES:
                with self.subTest(method=name, base=base):
                    self.assertIn(base, needs)

    def test_robotic_barns_join_the_automation_policy(self):
        data = _data()
        for name in ROBOTIC:
            with self.subTest(method=name):
                self.assertEqual(data.modifiers(name, "unscaled").get(MARKER), "yes")
                self.assertIn(QUOTAS, _list(data.pms[name].get("disallowing_laws")))
        for name in NOT_ROBOTIC:
            with self.subTest(method=name):
                self.assertNotIn(MARKER, data.modifiers(name, "unscaled"))
                self.assertNotIn(QUOTAS, _list(data.pms[name].get("disallowing_laws")))

    def test_the_group_is_named_for_what_it_now_holds(self):
        loc = _loc()
        self.assertEqual(loc.get(HERD), "Herd Management")


class EmploymentTest(unittest.TestCase):
    """pm_employment_audit's and test_flat_crews.py's rules, for these buildings by name, so a
    later change to one of them fails here with the combination that breaks."""

    def test_no_combination_goes_negative_or_keeps_a_token_crew(self):
        data = _data()
        for building in CHECKED_BUILDINGS:
            combos = data.combos(building)
            with self.subTest(building=building):
                self.assertTrue(combos)
                for combo in combos:
                    staff = data.by_profession(combo)
                    negative = {k: v for k, v in staff.items() if v < 0}
                    self.assertFalse(negative, f"{' + '.join(combo)}: {negative}")
                    total = sum(staff.values())
                    self.assertFalse(0 < total < MIN_STAFF, f"{' + '.join(combo)} keeps {total:.0f} a level")

    def test_the_top_tiers_reach_the_floor(self):
        """Robotic Barns and refrigerated rail cars take a new base's laborers to zero
        exactly, and Robotic Barns takes its farmers to zero: the cuts use the room the
        bases leave and no more."""
        data = _data()
        rail = "pm_refrigerated_rail_cars_building_livestock_ranch"
        for base in NEW_RANCH_BASES:
            staff = data.by_profession((base, "pm_robotic_barns", rail))
            with self.subTest(base=base):
                self.assertEqual(staff["laborers"], 0)
        self.assertEqual(data.by_profession(("pm_gene_edited_livestock", "pm_robotic_barns"))["farmers"], 0)


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
    rail = "pm_refrigerated_rail_cars_building_livestock_ranch"
    rows = [
        ("Ranch, era 4", ("pm_mechanized_slaughtering", "pm_intensive_grazing_ranch", "pm_electric_fencing", rail)),
        ("Ranch, era 7", ("pm_industrial_feedlots", "pm_intensive_grazing_ranch", "pm_mechanized_feeding_lines", rail)),
        ("Ranch, era 8", ("pm_industrial_feedlots", "pm_antibiotic_growth_promoters", "pm_mechanized_feeding_lines", rail)),
        ("Ranch, era 9", ("pm_recombinant_growth_hormones", "pm_antibiotic_growth_promoters", "pm_mechanized_feeding_lines", rail)),
        ("Ranch, era 10", ("pm_recombinant_growth_hormones", "pm_antibiotic_growth_promoters", "pm_robotic_barns", rail)),
        ("Ranch, era 11", ("pm_gene_edited_livestock", "pm_antibiotic_growth_promoters", "pm_robotic_barns", rail)),
    ]
    print(f"{'Combination':16s} {'Input':>7s} {'Output':>7s} {'Profit':>7s} {'Staff':>6s} {'Per head':>8s}")
    for label, combo in rows:
        cost, value = data.value(combo)
        staff = sum(data.by_profession(combo).values())
        per = (value - cost) / staff if staff else float("nan")
        print(f"{label:16s} {cost:7.0f} {value:7.0f} {value - cost:7.0f} {staff:6.0f} {per:8.2f}")
        print(f"    {' + '.join(combo)}")


if __name__ == "__main__":
    if "--table" in sys.argv:
        _table()
    else:
        unittest.main()
