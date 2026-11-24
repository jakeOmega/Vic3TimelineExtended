"""A stronger battalion type never unlocks before a weaker one of its group.

The era 13 technology rework (#1281) moved Robotic Soldiers from JADC2 to a new Autonomous Weapons that followed Swarm
Technology, so Swarm Bots (offense 540, defense 1675) came strictly before the Robotic Soldiers (240, 585) they
succeed. Nothing caught it: every unit kept a valid technology and its era. Autonomous Weapons now leads to Swarm
Technology (2026-11-24). This test checks every land unit group, the mod's types against each other and vanilla's:

- strictly before: no type's technologies, with all their prerequisites, are a proper subset of a weaker type's;
- by era: no type unlocks in an earlier era than a weaker type.

Strength is offense plus defense, the per-battalion figures the unit panel shows. A type no technology unlocks
(Irregular Infantry) is left out.

Run: .venv/bin/python -m pytest test_combat_unit_tier_order.py -q
"""
import functools
import os
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

_STATE = None


def _body(value):
    while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def _names(value):
    value = _body(value)
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    out = []
    for item in value:
        item = _body(item)
        out.extend(item if isinstance(item, list) else [item])
    return out


def _merged():
    """(technologies, unit types, the mod's unit type names): vanilla's snapshot under the mod."""
    global _STATE
    if _STATE is None:
        import vanilla_parsed
        from mod_state import ModState

        types = {"Technologies": os.path.join("technology", "technologies"), "Combat Unit Types": "combat_unit_types"}
        snapshot = vanilla_parsed.load(os.path.join(REPO, "vanilla_parsed"))
        vanilla = {k: v for k, v in snapshot.data.items() if k in types}
        state = ModState({k: "" for k in types}, {k: os.path.join(REPO, "common", d) for k, d in types.items()},
                         vanilla_data=vanilla)
        techs = {name: _body(v) for name, v in state.get_data("Technologies").items()}
        units = {name: _body(v) for name, v in state.get_data("Combat Unit Types").items()}
        _STATE = (techs, units, set(state.mod_parsers["Combat Unit Types"].data))
    return _STATE


def _era(techs, tech):
    return int(_body(techs[tech]["era"]).split("_")[1])


def _reach(techs):
    """A function giving the technologies a set needs: the set and every prerequisite of each, transitively."""
    @functools.lru_cache(maxsize=None)
    def ancestors(tech):
        out = set()
        for parent in _names(techs[tech].get("unlocking_technologies")):
            out.add(parent)
            out |= ancestors(parent)
        return frozenset(out)

    def reach(names):
        out = set(names)
        for tech in names:
            out |= ancestors(tech)
        return frozenset(out)
    return reach


def _strength(unit):
    battle = _body(unit.get("battle_modifier")) or {}
    return sum(float(_body(battle.get(key, 0)) or 0) for key in ("unit_offense_add", "unit_defense_add"))


def _groups():
    """{group: [(strength, unit type, its technologies)]} for every type some technology unlocks."""
    techs, units, _ = _merged()
    groups = {}
    for name, unit in units.items():
        if not isinstance(unit, dict):
            continue
        unlocks = _names(unit.get("unlocking_technologies"))
        if unlocks:
            groups.setdefault(_body(unit["group"]), []).append((_strength(unit), name, tuple(unlocks)))
    return groups


def _pairs():
    """(group, weaker, its technologies, stronger, its technologies) for each pair with a mod type in it."""
    _, _, mod_units = _merged()
    for group, rows in sorted(_groups().items()):
        for weak_strength, weak, weak_techs in rows:
            for strong_strength, strong, strong_techs in rows:
                if strong_strength > weak_strength and (weak in mod_units or strong in mod_units):
                    yield group, weak, weak_techs, strong, strong_techs


class TierOrder(unittest.TestCase):
    def test_every_unlocking_technology_exists(self):
        techs, _, _ = _merged()
        missing = sorted((name, tech) for rows in _groups().values() for _, name, unlocks in rows
                         for tech in unlocks if tech not in techs)
        self.assertEqual(missing, [])

    def test_no_stronger_type_unlocks_strictly_before_a_weaker_one(self):
        techs, _, _ = _merged()
        reach = _reach(techs)
        inverted = [f"{group}: {strong} ({', '.join(strong_techs)}) unlocks strictly before the weaker {weak} "
                    f"({', '.join(weak_techs)})"
                    for group, weak, weak_techs, strong, strong_techs in _pairs()
                    if reach(strong_techs) < reach(weak_techs)]
        self.assertEqual(inverted, [])

    def test_no_stronger_type_sits_an_era_before_a_weaker_one(self):
        techs, _, _ = _merged()
        earlier = [f"{group}: {strong} (era {max(_era(techs, t) for t in strong_techs)}) is stronger than {weak} "
                   f"(era {max(_era(techs, t) for t in weak_techs)})"
                   for group, weak, weak_techs, strong, strong_techs in _pairs()
                   if max(_era(techs, t) for t in strong_techs) < max(_era(techs, t) for t in weak_techs)]
        self.assertEqual(earlier, [])

    def test_robotic_soldiers_come_before_swarm_bots(self):
        """The case the era 13 rework broke: Autonomous Weapons is a prerequisite of Swarm Technology."""
        techs, units, _ = _merged()
        reach = _reach(techs)
        robotic = _names(units["combat_unit_type_robotic_soldiers"]["unlocking_technologies"])
        swarm = _names(units["combat_unit_type_swarm_bots"]["unlocking_technologies"])
        self.assertLess(reach(robotic), reach(swarm))


if __name__ == "__main__":
    unittest.main()
