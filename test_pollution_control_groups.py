"""Every pollution-control group keeps an allowed method for every combination.

Seven groups (`common/production_method_groups/extra_pm_groups.txt`) let
polluting buildings cut local pollution: a method that does nothing, unlocked
only by `law_no_ministry_of_the_environment`, a basic tier and an advanced one.
Once the ministry is established the do-nothing method is gone, so the ministry
forces at least the basic tier wherever there is pollution to cut. A
combination of the building's other methods for which no method of the group
is allowed leaves the building with nothing valid in it. The Glassworks did
that under the ministry on Forest Glass or Bioplastics without polluting
automation, because its tiers unlock only beside a polluting method so that no
combination goes below zero pollution.

The model: a method is allowed when one of its `unlocking_laws` holds (one of
the two ministry laws), none of its `disallowing_laws` does, and one of its
`unlocking_production_methods` is in the combination. Technology is left out:
no control method needs more than Pollution Control, which the ministry law
needs too, and ignoring the other groups' technologies only adds combinations.
A method whose `replacement_if_valid` target is also allowed swaps itself for
it, so the building does not stay on it.

Merged vanilla + mod data, vanilla from the committed `vanilla_parsed/`.
"""

import itertools
import json
import os
import unittest
from collections import namedtuple
from pathlib import Path

import vanilla_parsed
from mod_state import ModState
from pm_employment_audit import _as_list, _resolve_groups, _unwrap

ROOT = Path(__file__).resolve().parent

ENTITY_TYPES = {
    "Buildings": "buildings",
    "PM Groups": "production_method_groups",
    "PMs": "production_methods",
}
CONTROL_GROUPS = (
    "pmg_tailings_wastewater_management",
    "pmg_facility_emission_standards",
    "pmg_industrial_synthesis_scrubbing",
    "pmg_precision_environmental_management",
    "pmg_effluent_filtration",
    "pmg_glassworks_fume_ventilation",
    "pmg_emissions_control",
)
MINISTRY = "law_ministry_of_the_environment"
NO_MINISTRY = "law_no_ministry_of_the_environment"
GLASSWORKS = "building_glassworks"
GLASSWORKS_GROUP = "pmg_glassworks_fume_ventilation"

Method = namedtuple("Method", "pollution unlocking_methods unlocking_laws disallowing_laws replacement techs")


def load_data():
    snap_dir = ROOT / "vanilla_parsed"
    manifest = vanilla_parsed.read_manifest(str(snap_dir)) or {}
    vanilla = {}
    for et in ENTITY_TYPES:
        info = manifest.get("entity_types", {}).get(et)
        if info:
            with open(snap_dir / info["file"], encoding="utf-8") as fh:
                vanilla[et] = vanilla_parsed.decode(json.load(fh))
    ms = ModState({et: "" for et in ENTITY_TYPES},
                  {et: os.path.join(ROOT, "common", d) for et, d in ENTITY_TYPES.items()},
                  vanilla_data=vanilla)
    return {et: ms.get_data(et) or {} for et in ENTITY_TYPES}


def _names(body, key):
    return [str(x) for x in _as_list(body.get(key))]


def method(body):
    body = _unwrap(body)
    body = body if isinstance(body, dict) else {}
    total = 0.0
    state = _unwrap(body.get("state_modifiers"))
    for scaling in ("workforce_scaled", "level_scaled", "unscaled"):
        block = _unwrap(state.get(scaling)) if isinstance(state, dict) else None
        if isinstance(block, dict) and "state_pollution_generation_add" in block:
            total += sum(float(v) for v in _as_list(block["state_pollution_generation_add"]))
    return Method(total, frozenset(_names(body, "unlocking_production_methods")),
                  frozenset(_names(body, "unlocking_laws")), frozenset(_names(body, "disallowing_laws")),
                  str(_unwrap(body.get("replacement_if_valid")) or ""),
                  frozenset(_names(body, "unlocking_technologies")))


class Model:
    """Methods, groups and combinations for the buildings that carry a control group."""

    def __init__(self, data):
        self.data = data
        self._methods = {}
        self.control = {}      # building -> (control group, its methods)
        self.others = {}       # building -> [[methods] per other group]
        for building, body in data["Buildings"].items():
            groups = _resolve_groups(body, data["PM Groups"])
            for group, members in groups:
                if group in CONTROL_GROUPS:
                    self.control[building] = (group, members)
                    self.others[building] = [m for g, m in groups if g != group]

    def m(self, pm):
        if pm not in self._methods:
            self._methods[pm] = method(self.data["PMs"].get(pm))
        return self._methods[pm]

    def allowed(self, pm, combo, ministry):
        m = self.m(pm)
        law = MINISTRY if ministry else NO_MINISTRY
        if m.unlocking_laws and law not in m.unlocking_laws:
            return False
        if law in m.disallowing_laws:
            return False
        return not m.unlocking_methods or not m.unlocking_methods.isdisjoint(combo)

    def resting(self, members, combo, ministry):
        """The allowed methods a building can stay on: an allowed method whose
        replacement_if_valid target is allowed too is swapped for it."""
        ok = [pm for pm in members if self.allowed(pm, combo, ministry)]
        return [pm for pm in ok if self.m(pm).replacement not in ok]

    def combinations(self, building):
        """(combo, pollution) for every combination of the building's other
        groups whose unlocking_production_methods hold within it. Methods of a
        group that no check can tell apart (same pollution and unlocks, and no
        unlock list names them) are tried once."""
        _, control = self.control[building]
        groups = self.others[building]
        named = set().union(*(self.m(pm).unlocking_methods for g in groups + [control] for pm in g))
        choices = []
        for members in groups:
            seen = set()
            kept = []
            for pm in members:
                key = pm if pm in named else (self.m(pm).pollution, self.m(pm).unlocking_methods)
                if key not in seen:
                    seen.add(key)
                    kept.append(pm)
            choices.append(kept)
        for combo in itertools.product(*choices):
            chosen = frozenset(combo)
            if all(not self.m(pm).unlocking_methods or not self.m(pm).unlocking_methods.isdisjoint(chosen)
                   for pm in combo):
                yield combo, chosen, sum(self.m(pm).pollution for pm in combo)

    def gaps(self):
        """[(building, ministry, combo)] where no method of the control group is allowed."""
        found = []
        for building in sorted(self.control):
            _, members = self.control[building]
            for combo, chosen, _ in self.combinations(building):
                for ministry in (False, True):
                    if not any(self.allowed(pm, chosen, ministry) for pm in members):
                        found.append((building, ministry, combo))
        return found


class PollutionControlGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        cls.model = Model(cls.data)
        cls.combos = {b: list(cls.model.combinations(b)) for b in cls.model.control}

    def test_every_group_is_on_a_building(self):
        self.assertEqual({g for g, _ in self.model.control.values()}, set(CONTROL_GROUPS))
        self.assertIn(GLASSWORKS, self.model.control)

    def test_no_control_method_needs_a_technology_the_ministry_does_not(self):
        # The model leaves technology out; that holds only while this does.
        for group, members in self.model.control.values():
            for pm in members:
                with self.subTest(pm=pm):
                    self.assertLessEqual(self.model.m(pm).techs, {"pollution_control"})

    def test_every_combination_keeps_an_allowed_method(self):
        found = self.model.gaps()
        self.assertEqual(found[:10], [], f"{len(found)} combinations have no allowed control method")

    def test_the_ministry_leaves_no_idle_method_where_there_is_pollution(self):
        for building, (_, members) in sorted(self.model.control.items()):
            for combo, chosen, polluted in self.combos[building]:
                if polluted <= 0:
                    continue
                idle = [pm for pm in self.model.resting(members, chosen, True) if self.model.m(pm).pollution >= 0]
                self.assertEqual(idle, [], f"{building} {combo} pollutes {polluted} under the ministry")

    def test_glassworks_never_cuts_below_zero(self):
        # The group comment's promise: each tier unlocks only beside enough pollution.
        _, members = self.model.control[GLASSWORKS]
        seen = 0
        for combo, chosen, polluted in self.combos[GLASSWORKS]:
            for ministry in (False, True):
                for pm in self.model.resting(members, chosen, ministry):
                    seen += 1
                    self.assertGreaterEqual(polluted + self.model.m(pm).pollution, 0, f"{pm} on {combo}")
        self.assertGreater(seen, 0)

    def test_fume_free_process_yields_to_fume_extraction(self):
        _, members = self.model.control[GLASSWORKS]
        self.assertEqual(members[-1], "pm_glassworks_fume_free_process",
                         "keep it last, so a first-valid fallback reaches a tier before it")
        self.assertEqual(self.model.m("pm_glassworks_fume_free_process").replacement,
                         "pm_glassworks_fume_extraction")
        # Beside Automatic Bottle Blowers the building pollutes, so it moves on.
        combo = {"pm_forest_glass", "pm_ceramics", "pm_automatic_bottle_blowers"}
        self.assertEqual(self.model.resting(members, combo, True), ["pm_glassworks_fume_extraction"])
        combo = {"pm_forest_glass", "pm_ceramics", "pm_manual_glassblowing"}
        self.assertEqual(self.model.resting(members, combo, True), ["pm_glassworks_fume_free_process"])
        self.assertEqual(self.model.resting(members, combo, False), ["pm_no_glassworks_fume_ventilation"])

    def test_the_check_finds_the_old_glassworks_gap(self):
        # Before the fix: no Fume-Free Process, and Mass-Produced Plastics did not
        # unlock Fume Extraction.
        _, members = self.model.control[GLASSWORKS]
        group = dict(_unwrap(self.data["PM Groups"][GLASSWORKS_GROUP]))
        group["production_methods"] = [p for p in members if p != "pm_glassworks_fume_free_process"]
        extraction = dict(_unwrap(self.data["PMs"]["pm_glassworks_fume_extraction"]))
        extraction["unlocking_production_methods"] = [
            p for p in _names(extraction, "unlocking_production_methods") if p != "pm_massed_produced_plastics"]
        found = Model({
            "Buildings": {GLASSWORKS: self.data["Buildings"][GLASSWORKS]},
            "PM Groups": {**self.data["PM Groups"], GLASSWORKS_GROUP: group},
            "PMs": {**self.data["PMs"], "pm_glassworks_fume_extraction": extraction},
        }).gaps()
        self.assertTrue(all(ministry for _, ministry, _ in found), "the no-ministry method covers everything")
        # combo order: base, luxury, glassblowing, then the mod's groups.
        self.assertEqual({(combo[0], combo[2]) for _, _, combo in found}, {
            ("pm_forest_glass", "pm_manual_glassblowing"),
            ("pm_bioplastics", "pm_manual_glassblowing"),
            ("pm_bioplastics", "pm_programmable_plastics"),
            ("pm_bioplastics", "pm_massed_produced_plastics"),
        })


if __name__ == "__main__":
    unittest.main()
