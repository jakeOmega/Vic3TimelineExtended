"""Elastics (`pm_elastics`) can be chosen on every textile mill that runs a sewing base method.

Vanilla gates Elastics on `pm_sewing_machines` and `pm_electric_sewing_machines`
(`unlocking_production_methods`, an OR over the building's active methods). The mod adds
`pm_programmable_matter_clothing` to the same primary group, and a PM that names only the
vanilla pair is unselectable on a mill running it, with no log line. The mod's own
automation methods already list it; `INJECT:pm_elastics` in extra_pms.txt adds the
Elastics entry, the same fix `pm_precision_tools` makes for the furniture manufactory.
"""
import os
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

BUILDING = "building_textile_mill"
PRIMARY_GROUP = "pmg_base_building_textile_mill"
VANILLA_UNLOCKERS = ("pm_sewing_machines", "pm_electric_sewing_machines")
MOD_PRIMARY = "pm_programmable_matter_clothing"


def _value(body):
    while isinstance(body, tuple) and len(body) == 2:
        body = body[1]
    return body


def _names(value):
    value = _value(value)
    if value is None:
        return []
    return [str(_value(v)) for v in value] if isinstance(value, list) else [str(value)]


class TextileMillElastics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import vanilla_parsed
        from mod_state import ModState

        types = {"Buildings": "buildings", "PM Groups": "production_method_groups",
                 "PMs": "production_methods"}
        snapshot = vanilla_parsed.load(os.path.join(REPO, "vanilla_parsed"))
        vanilla = {k: v for k, v in snapshot.data.items() if k in types}
        state = ModState({k: "" for k in types}, {k: os.path.join(REPO, "common", d) for k, d in types.items()},
                         vanilla_data=vanilla)
        cls.buildings, cls.groups, cls.pms = (
            {name: _value(body) for name, body in state.get_data(k).items()} for k in types)

    def mill_pms(self):
        """{group: [pm, ...]} for the textile mill's merged groups."""
        return {group: _names(self.groups[group].get("production_methods"))
                for group in _names(self.buildings[BUILDING].get("production_method_groups"))
                if group in self.groups}

    def unlockers(self, pm):
        return _names(_value(self.pms[pm]).get("unlocking_production_methods"))

    def test_the_mod_primary_method_is_in_the_primary_group(self):
        """If the primary group ever drops it, the other tests have nothing to guard."""
        self.assertIn(MOD_PRIMARY, self.mill_pms()[PRIMARY_GROUP])

    def test_elastics_unlocks_on_the_mod_primary_method(self):
        unlockers = self.unlockers("pm_elastics")
        for vanilla in VANILLA_UNLOCKERS:
            self.assertIn(vanilla, unlockers, "INJECT must append to vanilla's list, not replace it")
        self.assertIn(MOD_PRIMARY, unlockers,
                      "pm_elastics can't be chosen on a mill running " + MOD_PRIMARY)

    def test_every_method_gated_on_a_sewing_base_method_also_accepts_the_mod_primary(self):
        """The class of bug: a method in another group that names the vanilla sewing
        methods but not the mod's later primary one."""
        missed = []
        for group, pms in self.mill_pms().items():
            if group == PRIMARY_GROUP:
                continue
            for pm in pms:
                unlockers = self.unlockers(pm)
                if any(v in unlockers for v in VANILLA_UNLOCKERS) and MOD_PRIMARY not in unlockers:
                    missed.append(pm)
        self.assertEqual(missed, [], "gated on the sewing methods but not on " + MOD_PRIMARY)


if __name__ == "__main__":
    unittest.main()
