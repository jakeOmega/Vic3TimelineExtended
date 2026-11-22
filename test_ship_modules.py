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

# Each mod utility succeeds the base-game (or earlier mod) utilities on its stat
# (design doc, "The utility roster").
SUCCESSORS = {
    "damage_control_teams": ("fire_suppression",),
    "composite_armor_plating": ("damage_control_teams", "fire_suppression"),
    "ciws": ("torpedo_nets", "camouflage"),
    "electronic_countermeasures": ("camouflage",),
    "dew_point_defense": ("ciws", "torpedo_nets"),
    "precision_warheads": ("advanced_explosives",),
    "ballistic_missile_bay": ("large_carronades", "patrol_boats"),
    "drone_complement": ("range_finder",),
    "aegis_air_defense": ("fire_control_system",),
    "surface_search_radar": ("searchlights",),
    "helicopter_pad": ("landing_skiffs",),
}
# Base-game utilities no mod ship offers: obsolete by the mod's eras.
PRUNED = ("torpedo_nets", "searchlights")
# Stats whose reducers must not stack across utility slots on a mod ship.
NO_STACK = ("ship_suffered_hull_damage_mult", "ship_suffered_crew_damage_mult",
            "ship_suffered_accuracy_mult", "ship_suffered_crit_chance_mult",
            "ship_vulnerability_mult")
LATE_CAPITALS = ("arsenal_ship", "stealth_battlecruiser", "hypersonic_missile_platform", "antimatter_battleship")
CARRIERS = ("fleet_carrier", "nuclear_supercarrier")

MEDIUM_TOTALS_BEFORE_RESHAPE = {
    'amphibious_assault_ship': {'hull_damage': 95, 'crew_damage': 30, 'armor': 110, 'hit_points_max': 4875, 'supply_capacity': 340, 'power_projection': 0},
    'antimatter_battleship': {'hull_damage': 3010, 'crew_damage': 1185, 'armor': 2170, 'hit_points_max': 29150, 'supply_capacity': 710, 'power_projection': 1350},
    'arsenal_ship': {'hull_damage': 1310, 'crew_damage': 385, 'armor': 670, 'hit_points_max': 13150, 'supply_capacity': 460, 'power_projection': 1130},
    'asw_destroyer': {'hull_damage': 155, 'crew_damage': 50, 'armor': 85, 'hit_points_max': 4675, 'supply_capacity': 105, 'power_projection': 233},  # PP 200 until #1390
    'autonomous_swarm_submarine': {'hull_damage': 680, 'crew_damage': 200, 'armor': 100, 'hit_points_max': 8175, 'supply_capacity': 165, 'power_projection': 150},
    'expeditionary_fast_transport': {'hull_damage': 65, 'crew_damage': 20, 'armor': 70, 'hit_points_max': 3875, 'supply_capacity': 190, 'power_projection': 0},
    'expeditionary_sea_base': {'hull_damage': 117, 'crew_damage': 40, 'armor': 160, 'hit_points_max': 6875, 'supply_capacity': 690, 'power_projection': 0},
    'fleet_carrier': {'hull_damage': 380, 'crew_damage': 65, 'armor': 274, 'hit_points_max': 6050, 'supply_capacity': 260, 'power_projection': 319},
    'guided_missile_ship': {'hull_damage': 280, 'crew_damage': 95, 'armor': 135, 'hit_points_max': 5675, 'supply_capacity': 125, 'power_projection': 290},
    'hypersonic_missile_platform': {'hull_damage': 1710, 'crew_damage': 685, 'armor': 1270, 'hit_points_max': 19150, 'supply_capacity': 510, 'power_projection': 1130},
    'marine_assault_ship': {'hull_damage': 105, 'crew_damage': 35, 'armor': 140, 'hit_points_max': 5875, 'supply_capacity': 440, 'power_projection': 0},
    'networked_air_defense_cruiser': {'hull_damage': 505, 'crew_damage': 140, 'armor': 381, 'hit_points_max': 6975, 'supply_capacity': 205, 'power_projection': 348},
    'nuclear_submarine': {'hull_damage': 260, 'crew_damage': 80, 'armor': 55, 'hit_points_max': 5175, 'supply_capacity': 135, 'power_projection': 75},
    'nuclear_supercarrier': {'hull_damage': 450, 'crew_damage': 100, 'armor': 344, 'hit_points_max': 8050, 'supply_capacity': 360, 'power_projection': 330},  # PP 275 until #1390
    'orbital_support_amphibious_mothership': {'hull_damage': 187, 'crew_damage': 60, 'armor': 310, 'hit_points_max': 11375, 'supply_capacity': 1290, 'power_projection': 0},
    'pulsed_laser_escort': {'hull_damage': 1030, 'crew_damage': 280, 'armor': 731, 'hit_points_max': 8975, 'supply_capacity': 225, 'power_projection': 570},
    'stealth_attack_submarine': {'hull_damage': 400, 'crew_damage': 130, 'armor': 70, 'hit_points_max': 6675, 'supply_capacity': 155, 'power_projection': 105},
    'stealth_battlecruiser': {'hull_damage': 1160, 'crew_damage': 435, 'armor': 970, 'hit_points_max': 14150, 'supply_capacity': 430, 'power_projection': 970},
    'swarm_coordination_vessel': {'hull_damage': 880, 'crew_damage': 230, 'armor': 831, 'hit_points_max': 9475, 'supply_capacity': 215, 'power_projection': 440},
}

# Vulnerability and screening before vanilla 1.14.5's rescale (#1625): each mod
# ship's hull (V, S), and its anchors' in vanilla 1.14.4. The hull now carries
# that value times the anchor's current / old, rounded half up (header of
# common/ship_types/extra_ship_types.txt), so the ships keep their relation to
# each other and to their analogues. If vanilla rescales again, the test fails
# until the values are re-derived. A ship's anchor is its ANALOGUE, except that
# the troop ships take the capitals' V and the escorts' S (VS_ANCHOR): vanilla's
# troopship did not move, and screening counts fleet-wide, so the transports
# keep their relation to the mod's own capitals and escorts.
VS_BEFORE_RESCALE = {
    "asw_destroyer": (50, 250), "guided_missile_ship": (50, 250),
    "nuclear_submarine": (5, 5), "stealth_attack_submarine": (5, 5), "autonomous_swarm_submarine": (5, 10),
    "nuclear_supercarrier": (100, 30), "fleet_carrier": (100, 25),
    "arsenal_ship": (200, 10), "stealth_battlecruiser": (100, 30),
    "hypersonic_missile_platform": (200, 10), "antimatter_battleship": (200, 30),
    "pulsed_laser_escort": (75, 600), "swarm_coordination_vessel": (100, 700),
    "networked_air_defense_cruiser": (60, 500),
    "expeditionary_sea_base": (250, 0), "orbital_support_amphibious_mothership": (250, 20),
    "amphibious_assault_ship": (200, 0), "marine_assault_ship": (220, 0),
    "expeditionary_fast_transport": (250, 0),
}
ANALOGUE_VS_1_14_4 = {
    "destroyer": (50, 150), "submarine": (5, 5), "aircraft_carrier": (100, 10),
    "super_dreadnought": (200, 20), "light_cruiser": (10, 270),
}
VS_ANCHOR = {ship: ("super_dreadnought", "light_cruiser")
             for ship, analogue in ANALOGUE.items() if analogue == "troop_ship"}
VS_STATS = ("ship_vulnerability_add", "ship_screening_add")

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

        from mod_state import VANILLA_COMMON_DIRS

        types = ("Ship Types", "Ship Modifications", "Goods", "Technologies")
        snapshot = vanilla_parsed.load(os.path.join(REPO, "vanilla_parsed"))
        vanilla = {k: v for k, v in snapshot.data.items() if k in types}
        state = ModState({k: "" for k in types},
                         {k: os.path.join(REPO, "common", *VANILLA_COMMON_DIRS[k].split("/")) for k in types},
                         vanilla_data=vanilla)
        state.add_localization(os.path.join(REPO, "localization", "english"))
        data = {k: {name: _body(v) for name, v in state.get_data(k).items()} for k in types}
        mod_types = set(data["Ship Types"]) - set(vanilla["Ship Types"])
        mod_mods = set(data["Ship Modifications"]) - set(vanilla["Ship Modifications"])
        loc = dict(snapshot.localization)
        loc.update(state.localization)
        _STATE = (data["Ship Types"], data["Ship Modifications"], mod_types, mod_mods, loc)
        _EXTRA.update(goods=data["Goods"], techs=data["Technologies"],
                      vanilla_techs={n: _body(v) for n, v in vanilla["Technologies"].items()})
    return _STATE


_EXTRA = {}


def _goods_value(entity):
    _state()
    total = 0.0
    for key, qty in (_body(entity.get("construction_goods")) or {}).items():
        good = key[len("goods_input_"):-len("_add")]
        total += float(_body(qty)) * float(_body(_body(_EXTRA["goods"][good])["cost"]))
    return total


def _unlock_era(entity):
    _state()
    techs = _body(entity.get("unlocking_technologies"))
    if not techs:
        return 0
    techs = [techs] if isinstance(techs, str) else techs
    return min(int(_body(_body(_EXTRA["techs"][t])["era"]).split("_")[1]) for t in techs)


def _utility_slots(ship):
    mods = _body(ship["modifications"])
    out = {}
    for slot, value in mods.items():
        if slot.startswith("ship_mod_slot_utility_"):
            value = _body(value)
            out[slot] = [value] if isinstance(value, str) else list(value)
    return out


def _modifier(entity):
    block = _body(entity.get("modifier")) or {}
    blocks = [_body(b) for b in block] if isinstance(block, list) else [block]  # INJECTed techs carry two
    out = {}
    for b in blocks:
        for k, v in b.items():
            try:
                out[k] = out.get(k, 0.0) + float(_body(v))
            except (TypeError, ValueError):  # a block, or a boolean modifier
                continue
    return out


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

    def test_hull_share_matches_analogue(self):
        """The hull keeps the analogue's share of the medium total: hull =
        T x h / (h + m), T the golden medium total, h and m the analogue's hull
        and medium module. With the medium test, this pins the split, not only
        its sum."""
        types, mods, _, _, _ = _state()
        for ship, golden in MEDIUM_TOTALS_BEFORE_RESHAPE.items():
            analogue = ANALOGUE[ship]
            for slot, stats in RESHAPED.items():
                for stat in stats:
                    with self.subTest(ship=ship, stat=stat):
                        a_hull, a_tiers = _tier_values(types, mods, analogue, slot, stat)
                        hull, _ = _tier_values(types, mods, ship, slot, stat)
                        total = golden[stat[len("ship_"):-len("_add")]]
                        if a_hull + a_tiers[1] == 0:
                            continue
                        want = total * a_hull / (a_hull + a_tiers[1])
                        self.assertLessEqual(abs(hull - want), max(0.03 * total, 3),
                                             f"hull {hull} vs {want:.1f} of {total}")

    def test_light_to_high_spread_matches_analogue(self):
        """Light to high buys what it does on the vanilla analogue, within 5%
        (rounding moves the worst case, a small supply module, about 3%)."""
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
                        self.assertLess(abs(got / want - 1), 0.05, f"light->high x{got:.2f}, analogue x{want:.2f}")

    def test_power_projection_never_below_predecessor(self):
        """With medium modules, a mod ship projects at least what its vanilla
        analogue does and what the ship it succeeds does: the same AI role,
        unlocked by the technology that makes the other obsolete (#1390: the
        Nuclear Supercarrier had projected less than the Fleet Carrier)."""
        types, mods, _, _, _ = _state()
        stat = "ship_power_projection_add"

        def medium_pp(ship):
            hull, tiers = _tier_values(types, mods, ship, "range", stat)
            return hull + tiers[1]

        def field(ship, key):
            value = _body(types["ship_type_" + ship].get(key))
            if isinstance(value, dict):
                value = value.get("has_technology_researched", value)
                value = _body(value)
            return value

        def unlocks(ship):
            value = _body(types["ship_type_" + ship].get("unlocking_technologies"))
            return {value} if isinstance(value, str) else set(value or ())

        checked = 0
        for ship, analogue in ANALOGUE.items():
            with self.subTest(ship=ship, against=analogue):
                self.assertGreaterEqual(medium_pp(ship), medium_pp(analogue))
            obsolete_at = field(ship, "is_obsolete")
            if not isinstance(obsolete_at, str):
                continue
            for successor in ANALOGUE:
                if obsolete_at in unlocks(successor) and \
                        field(successor, "ai_ship_category") == field(ship, "ai_ship_category"):
                    checked += 1
                    with self.subTest(ship=successor, succeeds=ship):
                        self.assertGreaterEqual(medium_pp(successor), medium_pp(ship))
        self.assertGreater(checked, 5, "no successor pairs found: has is_obsolete changed shape?")

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



class TestShipUtilities(unittest.TestCase):
    def test_no_incompatible_with_on_ship_modifications(self):
        """On a ship modification the engine reads the documented bare
        `incompatible_with = <key>` as an unclosed list: it swallows every
        token up to the next closing brace, which is the modifier block, so the
        module keeps its goods and loses all its effects (eleven utilities
        shipped that way, 2026-11-04). This file's parser reads it fine, so no
        other test sees it."""
        folder = os.path.join(REPO, "common", "ship_modifications")
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".txt"):
                continue
            with self.subTest(file=name):
                with open(os.path.join(folder, name), encoding="utf-8-sig") as f:
                    text = re.sub(r"#[^\n]*", "", f.read())
                self.assertNotIn("incompatible_with", text)

    def test_successor_shares_its_predecessors_slot(self):
        """A slot holds one module, so listing a successor in the same utility
        slot as its predecessor is what keeps a ship from fitting both."""
        types, _, _, _, _ = _state()
        for ship in ANALOGUE:
            slots = _utility_slots(types["ship_type_" + ship])
            where = {m: slot for slot, listed in slots.items() for m in listed}
            for succ, preds in SUCCESSORS.items():
                for pred in preds:
                    a, b = where.get("utility_mod_" + succ), where.get("utility_mod_" + pred)
                    if a and b:
                        with self.subTest(ship=ship, module=succ, predecessor=pred):
                            self.assertEqual(a, b)

    def test_successors_stronger_on_every_shared_stat(self):
        _, mods, _, _, _ = _state()
        for succ, preds in SUCCESSORS.items():
            new = _modifier(mods["utility_mod_" + succ])
            for pred in preds:
                with self.subTest(module=succ, predecessor=pred):
                    old = _modifier(mods["utility_mod_" + pred])
                    shared = set(new) & set(old)
                    self.assertTrue(shared, "a successor shares at least one stat with its predecessor")
                    for stat in shared:
                        self.assertEqual(new[stat] > 0, old[stat] > 0, stat)
                        self.assertGreater(abs(new[stat]), abs(old[stat]), stat)

    def test_successors_cost_more_and_unlock_later(self):
        _, mods, _, _, _ = _state()
        for succ, preds in SUCCESSORS.items():
            for pred in preds:
                with self.subTest(module=succ, predecessor=pred):
                    new, old = mods["utility_mod_" + succ], mods["utility_mod_" + pred]
                    self.assertGreater(_goods_value(new), _goods_value(old))
                    self.assertGreater(_unlock_era(new), _unlock_era(old))

    def test_mod_utilities_are_tech_gated(self):
        _, mods, _, mod_mods, _ = _state()
        for name in sorted(m for m in mod_mods if m.startswith("utility_mod_")):
            with self.subTest(module=name):
                self.assertGreater(_unlock_era(mods[name]), 0)

    def test_pruned_utilities_not_on_mod_ships(self):
        types, _, _, _, _ = _state()
        for ship in ANALOGUE:
            for slot, listed in _utility_slots(types["ship_type_" + ship]).items():
                for pruned in PRUNED:
                    self.assertNotIn("utility_mod_" + pruned, listed, f"{ship} {slot}")

    def test_no_module_in_two_slots_and_no_stacking_reducers(self):
        types, mods, _, _, _ = _state()
        for ship in ANALOGUE:
            slots = _utility_slots(types["ship_type_" + ship])
            with self.subTest(ship=ship):
                seen = [m for listed in slots.values() for m in listed]
                self.assertEqual(len(seen), len(set(seen)), "a module listed in two utility slots")
                for stat in NO_STACK:
                    holders = {slot for slot, listed in slots.items()
                               if any(_modifier(mods[m]).get(stat, 0) < 0 for m in listed)}
                    self.assertLessEqual(len(holders), 1, f"{stat} reducers in {sorted(holders)}")

    def test_late_capitals_have_three_utility_slots(self):
        types, _, _, _, _ = _state()
        for ship in LATE_CAPITALS:
            with self.subTest(ship=ship):
                self.assertEqual(len(_utility_slots(types["ship_type_" + ship])), 3)

    def test_hull_accuracy_stays_where_misses_happen(self):
        """A shot misses with chance 0.5 + 0.03 x (target speed - visibility /
        15 - 5 x accuracy), clamped to 5-90% (NBattle defines). Against modern
        speeds every shot hits once effective accuracy passes about 7, and
        technologies add up to +35%, so a combat hull above 9 hits everything.
        Carriers keep the base game's carrier accuracy (20)."""
        types, _, _, _, _ = _state()
        for ship in ANALOGUE:
            with self.subTest(ship=ship):
                accuracy = _modifier(types["ship_type_" + ship]).get("ship_accuracy_add", 0)
                self.assertLessEqual(accuracy, 20 if ship in CARRIERS else 9)

    def test_modules_carry_no_flat_accuracy(self):
        """A flat ship_accuracy_add on a module undoes the hull ladder above (the
        Guided Missile Ship's heavy guns took it from 7 to 32 and made every
        countermeasure useless against it). The base game's modules carry none;
        a module that sharpens aim uses ship_accuracy_mult."""
        _, mods, _, mod_mods, _ = _state()
        for name in sorted(mod_mods):
            with self.subTest(module=name):
                self.assertLessEqual(_modifier(mods[name]).get("ship_accuracy_add", 0), 0)

    def test_accuracy_budget(self):
        """No target-side accuracy term below -0.4, and an attacker's penalty
        against a target plus the target's built-in defense plus its best
        countermeasure stays at -0.8 or above: the engine's rule for combining
        them is undocumented, and if it adds them and the sum went negative the
        attacker would miss 90% of the time with no log line."""
        types, mods, _, _, _ = _state()
        for target in ANALOGUE:
            entity = types["ship_type_" + target]
            built_in = _modifier(entity).get("ship_suffered_accuracy_mult", 0)
            listed = [m for ms in _utility_slots(entity).values() for m in ms]
            best = min([0.0] + [_modifier(mods[m]).get("ship_suffered_accuracy_mult", 0) for m in listed])
            with self.subTest(target=target):
                self.assertGreaterEqual(built_in, -0.4)
                self.assertGreaterEqual(best, -0.4)
            for attacker in ANALOGUE:
                penalty = min(0.0, _modifier(types["ship_type_" + attacker]).get(
                    f"ship_battle_against_ship_type_{target}_accuracy_mult", 0))
                with self.subTest(attacker=attacker, target=target):
                    self.assertGreaterEqual(round(penalty + built_in + best, 6), -0.8)

    def test_vulnerability_and_screening_follow_the_analogues_rescale(self):
        """Vanilla 1.14.5 rescaled vulnerability and screening by about x0.56;
        each mod hull keeps its pre-rescale relation to its anchor (#1625)."""
        types, _, _, _, _ = _state()
        self.assertEqual(set(VS_BEFORE_RESCALE), set(ANALOGUE))
        for ship, before in VS_BEFORE_RESCALE.items():
            anchors = VS_ANCHOR.get(ship, (ANALOGUE[ship],) * 2)
            for i, (stat, old, anchor) in enumerate(zip(VS_STATS, before, anchors)):
                now = _modifier(types["ship_type_" + anchor]).get(stat, 0.0)
                want = int(old * now / ANALOGUE_VS_1_14_4[anchor][i] + 0.5)
                with self.subTest(ship=ship, stat=stat):
                    self.assertEqual(_modifier(types["ship_type_" + ship]).get(stat, 0.0), want)

    def test_gun_module_vulnerability_is_the_analogues(self):
        """A gun module's ship_vulnerability_add is its analogue's gun module of
        the same tier, at the base game's current value (none where vanilla has
        none, as on the 1.15 submarine)."""
        types, mods, _, _, _ = _state()
        for ship, analogue in ANALOGUE.items():
            _, want = _tier_values(types, mods, analogue, "guns", "ship_vulnerability_add")
            _, have = _tier_values(types, mods, ship, "guns", "ship_vulnerability_add")
            with self.subTest(ship=ship):
                self.assertEqual(have, want)

    def test_point_defense_keeps_its_ratio_to_torpedo_nets(self):
        """Torpedo Nets are pruned from mod hulls, so the two vulnerability
        reducers are sized against a vanilla ship that fits them: a ship with
        the Close-In Weapon System keeps 80% of the vulnerability one with
        Torpedo Nets keeps, with DEW Point Defense 60% (the 2026-11-03 spec's
        -0.60 and -0.70 against Torpedo Nets' -0.5). Vanilla 1.15 halved Torpedo
        Nets to -0.25 and the two followed (#1682). Fails when vanilla moves
        Torpedo Nets again, so the successors are re-sized with it."""
        _, mods, _, _, _ = _state()
        stat = "ship_vulnerability_mult"
        kept = 1 + _modifier(mods["utility_mod_torpedo_nets"])[stat]
        for module, share in (("ciws", 0.8), ("dew_point_defense", 0.6)):
            with self.subTest(module=module):
                self.assertAlmostEqual(1 + _modifier(mods["utility_mod_" + module])[stat], share * kept, places=6)

    def test_no_module_or_technology_on_the_old_screening_scale(self):
        """Flat screening outside the hulls follows the light cruiser's rescale
        (270 -> 150): the utilities' 200 became 111, Unmanned Aerial Vehicles'
        50 became 28, the Swarm Coordination Vessel's high guns' 100 became 56.
        Pins every mod module and every technology the mod adds or changes that
        carries ship_screening_add, so a new one has to be sized on this scale."""
        _, mods, _, mod_mods, _ = _state()
        want = {"utility_mod_dew_point_defense": 111, "utility_mod_aegis_air_defense": 111,
                "ship_mod_swarm_coordination_vessel_guns_high": 56}
        have = {m: _modifier(mods[m])["ship_screening_add"] for m in sorted(mod_mods)
                if "ship_screening_add" in _modifier(mods[m])}
        self.assertEqual(have, want)
        techs, vanilla_techs = _EXTRA["techs"], _EXTRA["vanilla_techs"]
        have = {}
        for name, tech in techs.items():
            value = _modifier(tech).get("ship_screening_add")
            vanilla = _modifier(vanilla_techs[name]).get("ship_screening_add") if name in vanilla_techs else None
            if value is not None and value != vanilla:
                have[name] = value
        self.assertEqual(have, {"unmanned_aerial_vehicles": 28})


if __name__ == "__main__":
    unittest.main()
