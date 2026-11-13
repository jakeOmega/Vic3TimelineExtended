"""Value added per employee on the stacked automation methods, at base prices (#1684).

The Advanced Material Fabricator's fix (#1033, #1662) found the same pattern in five more
buildings: a base method plus an automation method that cancelled nearly the whole crew,
so a level kept 10 or 20 staff and value added per employee ran into the thousands (the
Software Industry's AI-Mediated Mind Sharing 10,536, the Deep-Sea Mine's automated method
5,960, Network Infrastructure's Autonomous Networks 1,974, Aerospace's AI-Optimized
Operations 1,525, the Construction Sector's 3D-Printed Buildings 350). As on the
fabricator, the goods' prices stay and the cuts are smaller:

- every combination keeps at least 100 staff a level (#1662's floor);
- no combination makes more than 320 value added per employee, the fabricator's best case,
  the highest the owner has accepted (2026-11-12);
- each automation method still employs fewer than the one before it on every base method,
  and pays for itself at a wage of 10 a worker a week (the 2045 save paid 5.9 a worker on
  average across producing buildings, high-technology ones far more), so the floor does
  not make automation pointless.

The Fusion Plant is not here: it keeps 210 to 360 staff a level on Integrated Smart
Systems, and its figure comes from its base methods (Aneutronic Fusion Power makes 345 per
employee on manual operation, from 16,000 electricity a level), so it needs the electricity
price of a late save, not a staff floor. The AI-managed methods' flat crews
(pm_ai_managed_*, a fixed crew at any level by design, docs/superpowers/archive/specs/
2026-10-16-ai-managed-flat-staff-design.md) aren't per-level staff and are left out too.

Everything is read from the files: the buildings' method groups (vanilla_parsed under the
mod, as ModState merges them), each method's goods and staff, the methods each one needs
(unlocking_production_methods), and the goods' base prices as pm_costs.py prices them. The
maintenance groups are left out; they carry no goods or staff.

Run: python3 -m pytest test_automated_methods_balance.py -q
     python3 test_automated_methods_balance.py --table   (the best combination of each building)
"""
import itertools
import os
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

MIN_STAFF = 100            # a level's staff, whatever the methods
MAX_VALUE_ADDED = 320.0    # per employee per level at base prices, the fabricator's best case
MAX_BREAKEVEN_WAGE = 10.0  # what an automation step may cost per worker it saves, a week

# Building -> the group whose methods automate it, in order. The Deep-Sea Mine automates in
# its base group: each automated method follows its advanced twin (the two families are
# the Global Commons rule's settings, extra_game_rules.txt).
BUILDINGS = {
    "building_software_industry": "pmg_automation_building_software",
    "building_network_infrastructure": "pmg_automation_building_network",
    "building_aerospace_industry": "pmg_automation_building_aerospace_industry",
    "building_construction_sector": "pmg_construction_automation",
    "building_ocean_mine": "pmg_base_building_ocean_mine",
}
OCEAN_STEPS = (("pm_advanced_ocean_mine", "pm_automated_ocean_mine"),
               ("pm_advanced_ocean_mine_uncapped", "pm_automated_ocean_mine_uncapped"))


def _body(value):
    while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def _list(value):
    value = _body(value)
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def _blocks(modifiers, key):
    value = _body(modifiers.get(key)) if isinstance(modifiers, dict) else None
    if value is None:
        return []
    return [_body(v) for v in value] if isinstance(value, list) else [value]


class _Data:
    def __init__(self):
        import pm_costs
        import vanilla_parsed
        from mod_state import VANILLA_COMMON_DIRS, ModState

        types = ("Buildings", "PM Groups", "PMs")
        snapshot = vanilla_parsed.load(os.path.join(REPO, "vanilla_parsed"))
        vanilla = {k: v for k, v in snapshot.data.items() if k in types}
        state = ModState({k: "" for k in types},
                         {k: os.path.join(REPO, "common", *VANILLA_COMMON_DIRS[k].split("/")) for k in types},
                         vanilla_data=vanilla)
        data = {k: {n: _body(v) for n, v in state.get_data(k).items()} for k in types}
        self.buildings, self.groups_by_name, self.pms = data["Buildings"], data["PM Groups"], data["PMs"]
        self.prices = pm_costs.load_goods()
        self._figures = {}

    def groups(self, building):
        return [g for g in _list(self.buildings[building].get("production_method_groups"))
                if not g.startswith("pmg_maintenance")]

    def methods(self, group):
        return _list(self.groups_by_name[group].get("production_methods"))

    def pm(self, name):
        """(input cost, output value, staff a level) of one method at base prices."""
        if name not in self._figures:
            modifiers = _body(self.pms[name].get("building_modifiers")) or {}
            cost = revenue = staff = 0.0
            for block in _blocks(modifiers, "workforce_scaled"):
                for key, qty in block.items():
                    if key.startswith("goods_input_") and key.endswith("_add"):
                        cost += float(_body(qty)) * self.prices[key[len("goods_input_"):-4]]
                    elif key.startswith("goods_output_") and key.endswith("_add"):
                        revenue += float(_body(qty)) * self.prices[key[len("goods_output_"):-4]]
            for block in _blocks(modifiers, "level_scaled"):
                staff += sum(float(_body(q)) for k, q in block.items()
                             if k.startswith("building_employment_") and k.endswith("_add"))
            self._figures[name] = (cost, revenue, staff)
        return self._figures[name]

    def valid(self, combo):
        chosen = set(combo)
        for name in combo:
            needs = _list(self.pms[name].get("unlocking_production_methods"))
            if needs and not chosen & set(needs):
                return False
        return True

    def figures(self, combo):
        """(staff a level, value added per employee) of one combination."""
        cost = revenue = staff = 0.0
        for name in combo:
            c, r, s = self.pm(name)
            cost, revenue, staff = cost + c, revenue + r, staff + s
        return staff, (revenue - cost) / staff if staff > 0 else float("inf")

    def combos(self, building):
        groups = self.groups(building)
        return [c for c in itertools.product(*(self.methods(g) for g in groups)) if self.valid(c)]

    def steps(self, building):
        """(combination, the next combination) for each automation step on every base."""
        group = BUILDINGS[building]
        groups = self.groups(building)
        index = groups.index(group)
        pairs = OCEAN_STEPS if building == "building_ocean_mine" else \
            list(zip(self.methods(group), self.methods(group)[1:]))
        others = [self.methods(g) for g in groups[:index] + groups[index + 1:]]
        out = []
        for rest in itertools.product(*others):
            for before, after in pairs:
                a = (*rest[:index], before, *rest[index:])
                b = (*rest[:index], after, *rest[index:])
                if self.valid(a) and self.valid(b):
                    out.append((a, b))
        return out


_DATA = None


def _data():
    global _DATA
    if _DATA is None:
        _DATA = _Data()
    return _DATA


class AutomatedMethodsBalanceTest(unittest.TestCase):
    def test_each_building_has_the_group_this_test_reads(self):
        data = _data()
        for building, group in BUILDINGS.items():
            with self.subTest(building=building):
                self.assertIn(group, data.groups(building))
                self.assertTrue(data.steps(building))
        for pair in OCEAN_STEPS:
            for name in pair:
                self.assertIn(name, data.methods(BUILDINGS["building_ocean_mine"]))

    def test_every_combination_keeps_a_level_staffed(self):
        data = _data()
        for building in BUILDINGS:
            for combo in data.combos(building):
                with self.subTest(building=building, combo=combo):
                    self.assertGreaterEqual(data.figures(combo)[0], MIN_STAFF)

    def test_no_combination_outearns_the_fabricator(self):
        data = _data()
        for building in BUILDINGS:
            for combo in data.combos(building):
                with self.subTest(building=building, combo=combo):
                    self.assertLessEqual(data.figures(combo)[1], MAX_VALUE_ADDED)

    def test_each_automation_step_still_cuts_staff_and_pays(self):
        data = _data()
        for building in BUILDINGS:
            for before, after in data.steps(building):
                staff_before, staff_after = data.figures(before)[0], data.figures(after)[0]
                extra = sum(data.pm(m)[0] - data.pm(m)[1] for m in after) - \
                    sum(data.pm(m)[0] - data.pm(m)[1] for m in before)
                with self.subTest(building=building, before=before, after=after):
                    self.assertLess(staff_after, staff_before)
                    self.assertLessEqual(extra / (staff_before - staff_after), MAX_BREAKEVEN_WAGE)


if __name__ == "__main__":
    if "--table" in sys.argv:
        d = _data()
        for b in BUILDINGS:
            best = max(d.combos(b), key=lambda c: d.figures(c)[1])
            staff, va = d.figures(best)
            print(f"{b:35s} staff {staff:5.0f} value added/employee {va:7.1f}  {' + '.join(best)}")
    else:
        unittest.main()
