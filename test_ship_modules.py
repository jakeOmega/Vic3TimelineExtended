"""Ship modules sized to their hull (design:
docs/superpowers/specs/2026-11-03-ship-module-scaling-design.md).

Every mod ship type has its own armor / guns / propulsion / range set, and for
the reshaped stats the hull and its modules split the ship's total the way the
ship's vanilla class analogue does, so going from light to high modules buys
what it does in the base game (header of
common/ship_modifications/extra_ship_modifications.txt).

MEDIUM_TOTALS_BEFORE_RESHAPE is each ship's total (hull + medium module) as it
stood before the 2026-11-03 reshape, which kept a default design's strength.
When you retune a ship's strength on purpose, update its row here.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

# Mod ship -> vanilla class analogue (the same mapping as the power projection
# derivation in the header of common/ship_types/extra_ship_types.txt).
ANALOGUE = {
    "asw_destroyer": "destroyer",
    "guided_missile_ship": "destroyer",
    "nuclear_submarine": "submarine",
    "stealth_attack_submarine": "submarine",
    "autonomous_swarm_submarine": "submarine",
    "nuclear_supercarrier": "aircraft_carrier",
    "fleet_carrier": "aircraft_carrier",
    "arsenal_ship": "super_dreadnought",
    "stealth_battlecruiser": "super_dreadnought",
    "hypersonic_missile_platform": "super_dreadnought",
    "antimatter_battleship": "super_dreadnought",
    "pulsed_laser_escort": "light_cruiser",
    "swarm_coordination_vessel": "light_cruiser",
    "networked_air_defense_cruiser": "light_cruiser",
    "expeditionary_sea_base": "troop_ship",
    "orbital_support_amphibious_mothership": "troop_ship",
    "amphibious_assault_ship": "troop_ship",
    "marine_assault_ship": "troop_ship",
    "expeditionary_fast_transport": "troop_ship",
}

# The stats the reshape covers, by the slot whose modules carry them.
RESHAPED = {
    "guns": ("ship_hull_damage_add", "ship_crew_damage_add"),
    "armor": ("ship_armor_add", "ship_hit_points_max_add"),
    "range": ("ship_supply_capacity_add", "ship_power_projection_add"),
}
CORE_SLOTS = ("armor", "guns", "propulsion", "range")
TIERS = ("light", "medium", "high")

MEDIUM_TOTALS_BEFORE_RESHAPE = {
    'amphibious_assault_ship': {'hull_damage': 95, 'crew_damage': 30, 'armor': 110, 'hit_points_max': 4875, 'supply_capacity': 340, 'power_projection': 0},
    'antimatter_battleship': {'hull_damage': 3010, 'crew_damage': 1185, 'armor': 2170, 'hit_points_max': 29150, 'supply_capacity': 710, 'power_projection': 1350},
    'arsenal_ship': {'hull_damage': 1310, 'crew_damage': 385, 'armor': 670, 'hit_points_max': 13150, 'supply_capacity': 460, 'power_projection': 1130},
    'asw_destroyer': {'hull_damage': 155, 'crew_damage': 50, 'armor': 85, 'hit_points_max': 4675, 'supply_capacity': 105, 'power_projection': 200},
    'autonomous_swarm_submarine': {'hull_damage': 680, 'crew_damage': 200, 'armor': 100, 'hit_points_max': 8175, 'supply_capacity': 165, 'power_projection': 150},
    'expeditionary_fast_transport': {'hull_damage': 65, 'crew_damage': 20, 'armor': 70, 'hit_points_max': 3875, 'supply_capacity': 190, 'power_projection': 0},
    'expeditionary_sea_base': {'hull_damage': 117, 'crew_damage': 40, 'armor': 160, 'hit_points_max': 6875, 'supply_capacity': 690, 'power_projection': 0},
    'fleet_carrier': {'hull_damage': 380, 'crew_damage': 65, 'armor': 274, 'hit_points_max': 6050, 'supply_capacity': 260, 'power_projection': 319},
    'guided_missile_ship': {'hull_damage': 280, 'crew_damage': 95, 'armor': 135, 'hit_points_max': 5675, 'supply_capacity': 125, 'power_projection': 290},
    'hypersonic_missile_platform': {'hull_damage': 1710, 'crew_damage': 685, 'armor': 1270, 'hit_points_max': 19150, 'supply_capacity': 510, 'power_projection': 1130},
    'marine_assault_ship': {'hull_damage': 105, 'crew_damage': 35, 'armor': 140, 'hit_points_max': 5875, 'supply_capacity': 440, 'power_projection': 0},
    'networked_air_defense_cruiser': {'hull_damage': 505, 'crew_damage': 140, 'armor': 381, 'hit_points_max': 6975, 'supply_capacity': 205, 'power_projection': 348},
    'nuclear_submarine': {'hull_damage': 260, 'crew_damage': 80, 'armor': 55, 'hit_points_max': 5175, 'supply_capacity': 135, 'power_projection': 75},
    'nuclear_supercarrier': {'hull_damage': 450, 'crew_damage': 100, 'armor': 344, 'hit_points_max': 8050, 'supply_capacity': 360, 'power_projection': 275},
    'orbital_support_amphibious_mothership': {'hull_damage': 187, 'crew_damage': 60, 'armor': 310, 'hit_points_max': 11375, 'supply_capacity': 1290, 'power_projection': 0},
    'pulsed_laser_escort': {'hull_damage': 1030, 'crew_damage': 280, 'armor': 731, 'hit_points_max': 8975, 'supply_capacity': 225, 'power_projection': 570},
    'stealth_attack_submarine': {'hull_damage': 400, 'crew_damage': 130, 'armor': 70, 'hit_points_max': 6675, 'supply_capacity': 155, 'power_projection': 105},
    'stealth_battlecruiser': {'hull_damage': 1160, 'crew_damage': 435, 'armor': 970, 'hit_points_max': 14150, 'supply_capacity': 430, 'power_projection': 970},
    'swarm_coordination_vessel': {'hull_damage': 880, 'crew_damage': 230, 'armor': 831, 'hit_points_max': 9475, 'supply_capacity': 215, 'power_projection': 440},
}

_STATE = None


def _body(value):
    while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def _state():
    """(ship types, ship modifications, mod ship type names, mod modification
    names, localization) with the committed vanilla snapshot under the mod."""
    global _STATE
    if _STATE is None:
        import vanilla_parsed
        from mod_state import ModState

        types = {"Ship Types": "ship_types", "Ship Modifications": "ship_modifications"}
        snapshot = vanilla_parsed.load(os.path.join(REPO, "vanilla_parsed"))
        vanilla = {k: v for k, v in snapshot.data.items() if k in types}
        state = ModState({k: "" for k in types},
                         {k: os.path.join(REPO, "common", d) for k, d in types.items()},
                         vanilla_data=vanilla)
        state.add_localization(os.path.join(REPO, "localization", "english"))
        data = {k: {name: _body(v) for name, v in state.get_data(k).items()} for k in types}
        mod_types = set(data["Ship Types"]) - set(vanilla["Ship Types"])
        mod_mods = set(data["Ship Modifications"]) - set(vanilla["Ship Modifications"])
        loc = dict(snapshot.localization)
        loc.update(state.localization)
        _STATE = (data["Ship Types"], data["Ship Modifications"], mod_types, mod_mods, loc)
    return _STATE


def _modifier(entity):
    block = _body(entity.get("modifier")) or {}
    return {k: float(_body(v)) for k, v in block.items() if not isinstance(_body(v), dict)}


def _slot(ship, slot):
    mods = _body(_body(ship["modifications"])["ship_mod_slot_" + slot])
    return [mods] if isinstance(mods, str) else list(mods)


def _tier_values(types, mods, ship, slot, stat):
    hull = _modifier(types["ship_type_" + ship]).get(stat, 0.0)
    return hull, [_modifier(mods[m]).get(stat, 0.0) for m in _slot(types["ship_type_" + ship], slot)]


class TestShipModules(unittest.TestCase):
    def test_every_mod_ship_is_covered(self):
        types, _, mod_types, _, _ = _state()
        self.assertEqual({"ship_type_" + s for s in ANALOGUE}, mod_types,
                         "a new mod ship type needs an ANALOGUE row and a golden")
        self.assertEqual(set(ANALOGUE), set(MEDIUM_TOTALS_BEFORE_RESHAPE))

    def test_every_mod_ship_has_its_own_core_set(self):
        types, mods, _, _, _ = _state()
        for ship in ANALOGUE:
            for slot in CORE_SLOTS:
                with self.subTest(ship=ship, slot=slot):
                    expected = [f"ship_mod_{ship}_{slot}_{tier}" for tier in TIERS]
                    self.assertEqual(_slot(types["ship_type_" + ship], slot), expected)
                    for name in expected:
                        self.assertIn(name, mods)

    def test_medium_totals_unchanged(self):
        types, mods, _, _, _ = _state()
        for ship, golden in MEDIUM_TOTALS_BEFORE_RESHAPE.items():
            for slot, stats in RESHAPED.items():
                for stat in stats:
                    with self.subTest(ship=ship, stat=stat):
                        hull, tiers = _tier_values(types, mods, ship, slot, stat)
                        want = golden[stat[len("ship_"):-len("_add")]]
                        self.assertLessEqual(abs(hull + tiers[1] - want), max(0.03 * want, 3),
                                             f"medium total {hull + tiers[1]} vs {want}")

    def test_light_to_high_spread_matches_analogue(self):
        """Light to high buys what it does on the vanilla analogue, within 12%."""
        types, mods, _, _, _ = _state()
        for ship, analogue in ANALOGUE.items():
            for slot, stats in RESHAPED.items():
                for stat in stats:
                    with self.subTest(ship=ship, stat=stat):
                        a_hull, a_tiers = _tier_values(types, mods, analogue, slot, stat)
                        hull, tiers = _tier_values(types, mods, ship, slot, stat)
                        if a_hull + a_tiers[0] == 0:
                            self.assertEqual(hull + tiers[2], hull + tiers[0])
                            continue
                        want = (a_hull + a_tiers[2]) / (a_hull + a_tiers[0])
                        got = (hull + tiers[2]) / (hull + tiers[0])
                        self.assertLess(abs(got / want - 1), 0.12, f"light->high x{got:.2f}, analogue x{want:.2f}")

    def test_tiers_rise(self):
        types, mods, _, _, _ = _state()
        for ship in ANALOGUE:
            for slot, stats in RESHAPED.items():
                for stat in stats:
                    with self.subTest(ship=ship, stat=stat):
                        _, tiers = _tier_values(types, mods, ship, slot, stat)
                        self.assertLessEqual(tiers[0], tiers[1])
                        self.assertLessEqual(tiers[1], tiers[2])

    def test_mod_modifications_have_names(self):
        """The engine shows a raw key for a module with no name, and
        loc_coverage_audit doesn't cover ship modifications."""
        _, _, _, mod_mods, loc = _state()
        splice = re.compile(r"\$([A-Za-z0-9_.]+)\$")
        for name in sorted(mod_mods):
            with self.subTest(module=name):
                self.assertIn(name, loc)
                for key in (name, name + "_desc"):
                    for target in splice.findall(loc.get(key, "")):
                        self.assertIn(target, loc, f"{key} splices ${target}$, which no loc file defines")

    def test_visibility_floor(self):
        """Base visibility plus the most negative visibility each core slot can
        add stays at 1 or more (scripting_best_practices.md, "ship_visibility_add
        Doesn't Clamp")."""
        types, mods, _, _, _ = _state()
        for ship in ANALOGUE:
            with self.subTest(ship=ship):
                entity = types["ship_type_" + ship]
                worst = _modifier(entity).get("ship_visibility_add", 0.0)
                for slot in CORE_SLOTS:
                    worst += min(0.0, *(_modifier(mods[m]).get("ship_visibility_add", 0.0)
                                        for m in _slot(entity, slot)))
                self.assertGreaterEqual(worst, 1)


if __name__ == "__main__":
    unittest.main()
