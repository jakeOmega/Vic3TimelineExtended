"""Low-staff methods hire a flat crew, and no level keeps a token one (#1684; owner, 2026-11-13).

The Advanced Material Fabricator's fix (#1033, #1662) found methods that cancelled nearly a
level's whole crew, so a level kept 10 or 20 staff and value added per employee ran into
the thousands (the Software Industry's AI-Mediated Mind Sharing 10,536, the Deep-Sea Mine's
automated method 5,960). The owner chose the AI-managed tier's answer for every one of them
(docs/superpowers/archive/specs/2026-10-16-ai-managed-flat-staff-design.md): the method
cancels its base method's per-level workforce exactly and a fixed crew of 1,000 in
`unscaled` runs the building at any size, so its levels are no longer limited by the people
available to staff them. Where the base methods' crews differ, the method is split by base
and hidden when unavailable (Robotic Food Processing, 3D Printed Buildings).

TokenCrewTest holds the rule across the whole mod: no combination of a building's methods
leaves a level 1 to 99 staff, so a new method keeps a real crew a level or hires a flat one.
FlatCrewTest holds the crews themselves: each runs some combination with no per-level staff
(the cancel is exact somewhere), and the ones this change made are 1,000 strong.
test_ai_managed_flat_staff.py checks that every flat crew is a very attractive job.

The Fusion Plant is not here: it keeps 210 to 360 staff a level on Integrated Smart
Systems, and its value added per employee comes from its base methods' output (Aneutronic
Fusion Power makes 345 per employee on manual operation), which needs a late save's
electricity price, not a crew.

Everything is read from the files: the buildings' method groups (vanilla_parsed under the
mod, as ModState merges them), each method's staff, and the methods each one needs
(unlocking_production_methods). The maintenance groups are left out; they hire no one.

Run: python3 -m pytest test_flat_crews.py -q
     python3 test_flat_crews.py --table   (every flat crew and the buildings it runs in)
"""
import itertools
import os
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

MIN_STAFF = 100  # a level that keeps a crew of its own keeps at least this many
CREW = 1000      # the flat crew, as pm_ai_managed_fab (owner, 2026-10-16)

# The methods that left a level 10 to 20 staff and took a flat crew (owner, 2026-11-13).
NEW_FLAT_CREWS = (
    "pm_automated_harvesters_and_planters",
    "pm_automated_harvesters_and_planters_building_rice_farm",
    "pm_ai_managed_textile_factory",
    "pm_ai_managed_building_furniture_manufactory",
    "pm_self_optimizing_production",
    "pm_bespoke_alloys",
    "pm_programmable_plastics",
    "pm_programmable_paper",
    "pm_robotic_food_processing_synthesis",
    "pm_robotic_service_providers",
    "pm_autonomous_trains",
    "pm_vactrain_freight",
    "pm_autonomous_highway",
    "pm_artificial_personalities",
    "pm_autonomous_networks",
    "pm_fully_automated_content_creation",
    "pm_ai_mediated_mind_sharing",
    "pm_ai_optimized_operations",
    "pm_automated_ocean_mine",
    "pm_automated_ocean_mine_uncapped",
    "pm_3d_printed_buildings_nanomaterial",
)

# Methods split by base, with every base the single method ran on before the split.
SPLITS = {
    ("pm_robotic_food_processing", "pm_robotic_food_processing_synthesis"): {
        "pm_baking_powder", "pm_food_additives", "pm_sweeteners", "pm_programmable_food_synthesis"},
    ("pm_3d_printed_buildings", "pm_3d_printed_buildings_nanomaterial"): {
        "pm_reinforced_concrete_buildings", "pm_arc_welded_buildings", "pm_advanced_construction",
        "pm_nanomaterial_buildings", "pm_self_replicating_construction",
        "pm_te_direct_construction_reinforced_concrete", "pm_te_direct_construction_arc_welded",
        "pm_te_direct_construction_advanced", "pm_te_direct_construction_nanomaterial",
        "pm_te_direct_construction_self_replicating"},
}

# Buildings whose levels keep a token staff by design, and groups whose staff is not the
# building's workforce. Everything else keeps 0 or at least MIN_STAFF a level.
TOKEN_CREW_EXEMPT = {
    "building_company_headquarter": "an ownership building: its owners, a few a level",
    "building_company_regional_headquarter": "an ownership building",
    "building_financial_district": "an ownership building",
    "building_manor_house": "an ownership building",
    "building_manila_cathedral_ruins": "a monument's ruins",
    "te_construction_market_site": "the construction market's marker building",
}
TOKEN_CREW_IGNORED_GROUPS = {
    # The state's clergy (Decentralized Religious Structures keeps 50 a level), not the
    # Urban Center's amenities staff, which Robotic Service Providers hires flat.
    "pmg_urban_clergy",
}


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

    def groups(self, building, ignored=()):
        return [g for g in _list(self.buildings[building].get("production_method_groups"))
                if not g.startswith("pmg_maintenance") and g not in ignored and g in self.groups_by_name]

    def methods(self, group):
        return [m for m in _list(self.groups_by_name[group].get("production_methods")) if m in self.pms]

    def _staff(self, name, bucket):
        modifiers = _body(self.pms[name].get("building_modifiers")) or {}
        return sum(float(_body(q)) for block in _blocks(modifiers, bucket)
                   for k, q in block.items() if k.startswith("building_employment_") and k.endswith("_add"))

    def staff(self, name):
        """Per-level staff of one method (level_scaled)."""
        return self._staff(name, "level_scaled")

    def staff_by_type(self, combo):
        """{profession: per-level staff} of one combination, every profession it names."""
        out = {}
        for name in combo:
            modifiers = _body(self.pms[name].get("building_modifiers")) or {}
            for block in _blocks(modifiers, "level_scaled"):
                for k, q in block.items():
                    if k.startswith("building_employment_") and k.endswith("_add"):
                        out[k] = out.get(k, 0.0) + float(_body(q))
        return out

    def crew(self, name):
        """The method's flat crew (unscaled)."""
        return self._staff(name, "unscaled")

    def valid(self, combo):
        chosen = set(combo)
        for name in combo:
            needs = _list(self.pms[name].get("unlocking_production_methods"))
            if needs and not chosen & set(needs):
                return False
        return True

    def combos(self, building, ignored=()):
        groups = self.groups(building, ignored)
        methods = [self.methods(g) for g in groups]
        if not groups or not all(methods):
            return []
        return [c for c in itertools.product(*methods) if self.valid(c)]

    def flat_crews(self):
        """{method: [buildings it runs in]} for every method with a flat crew."""
        out = {}
        for building in sorted(self.buildings):
            for group in self.groups(building):
                for name in self.methods(group):
                    if self.crew(name) > 0:
                        out.setdefault(name, []).append(building)
        return out


_DATA = None


def _data():
    global _DATA
    if _DATA is None:
        _DATA = _Data()
    return _DATA


class TokenCrewTest(unittest.TestCase):
    def test_no_combination_keeps_a_token_crew_a_level(self):
        data = _data()
        checked = 0
        for building in sorted(data.buildings):
            if building in TOKEN_CREW_EXEMPT:
                continue
            for combo in data.combos(building, TOKEN_CREW_IGNORED_GROUPS):
                checked += 1
                by_type = data.staff_by_type(combo)
                negative = {k: v for k, v in by_type.items() if v < 0}
                if negative:  # pm_employment_audit's rule; checked here so a sum can't hide it
                    self.fail(f"{building}: {' + '.join(combo)} goes negative: {negative}")
                staff = sum(by_type.values())
                if 0 < staff < MIN_STAFF:
                    self.fail(f"{building}: {' + '.join(combo)} keeps {staff:.0f} a level; "
                              f"keep {MIN_STAFF} or more, or hire a flat crew in unscaled")
        self.assertGreater(checked, 10000)

    def test_the_exemptions_still_need_it(self):
        """An exempt building that no longer keeps a token crew comes off the list."""
        data = _data()
        for building in TOKEN_CREW_EXEMPT:
            with self.subTest(building=building):
                self.assertIn(building, data.buildings)
                self.assertTrue(any(0 < sum(data.staff(m) for m in c) < MIN_STAFF
                                    for c in data.combos(building, TOKEN_CREW_IGNORED_GROUPS)))


class FlatCrewTest(unittest.TestCase):
    def test_every_flat_crew_cancels_a_level_exactly_somewhere(self):
        """A flat crew isn't hired on top of a per-level staff everywhere it runs: some
        combination with it keeps no one of any profession a level."""
        data = _data()
        crews = data.flat_crews()
        self.assertGreaterEqual(len(crews), 50)
        for name, buildings in sorted(crews.items()):
            with self.subTest(method=name):
                self.assertTrue(any(name in c and not any(data.staff_by_type(c).values())
                                    for b in buildings for c in data.combos(b)))

    def test_the_new_crews_are_a_thousand_strong(self):
        data = _data()
        crews = data.flat_crews()
        for name in NEW_FLAT_CREWS:
            with self.subTest(method=name):
                self.assertIn(name, crews)
                self.assertEqual(data.crew(name), CREW)

    def test_the_split_copies_hide_when_unavailable(self):
        """A building shows one copy of a method split by base (#996's pattern), and the two
        copies together still run on every base the single method did."""
        data = _data()
        for pair, bases in SPLITS.items():
            for name in pair:
                with self.subTest(method=name):
                    self.assertEqual(_body(data.pms[name].get("is_hidden_when_unavailable")), "yes")
            first, second = (set(_list(data.pms[n].get("unlocking_production_methods"))) for n in pair)
            self.assertTrue(first and second)
            self.assertFalse(first & second, pair)
            self.assertEqual(first | second, bases, pair)


if __name__ == "__main__":
    if "--table" in sys.argv:
        d = _data()
        for pm, buildings in sorted(d.flat_crews().items()):
            print(f"{pm:60s} crew {d.crew(pm):5.0f}  {', '.join(buildings)}")
    else:
        unittest.main()
