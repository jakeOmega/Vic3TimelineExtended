"""The Demographics tab's Largest Cities (owner, 2026-11-03): a state's towns by name, sized from its urban people.

- The generator (scripts/generators/gen_demog_towns.py) is fresh, and its classes and names match the data read
  independently here: vanilla's city_type, the mod's meshless mines, subsistence, the map's hubs and their loc keys.
- A state's towns in order (te_demog_town_walk_store), run on the census interpreter of test_demographics_registry.py:
  farm, mine and logging work at a quarter, a hub with no name or no work of its kind left out (the capital always
  counts), ties to the earlier kind, a state with no named hub one town under its own name.
- The country's ten largest (te_demog_town_country): a k-way merge, so a big state's second town outranks a small
  state's first; X(1 - X)^(k-1) of the urban people, X the share's target before the state has a share; a state under
  5,000 urban people or with no census left out; a refill.
- The rows: slot i reads slot i's variables only, on the country shown, six rows a slot, the rest under Show All.
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import gen_demog_towns as gen  # noqa: E402
import gui_test_helpers as gh  # noqa: E402
from test_demographics_registry import _CountryEngine, _Engine, _block, _text  # noqa: E402

PLACE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_place_effects.txt"
EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_effects.txt"
WIDGETS = ROOT / "gui" / "te_demographics_widgets.gui"
NAMED = {f"te_demog_town_named_{kind}": True for _, kind, _ in gen.KINDS}


def _unwrap(v):
    while isinstance(v, list) and len(v) == 2 and v[0] in ("=", "?="):
        v = v[1]
    return v


def _trigger_types(text, name):
    return re.findall(r"is_building_type = (\w+)", _block(text, name))


class GeneratorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = gen.outputs()
        cls.triggers = cls.outputs[gen.TRIGGERS_FILE].decode("utf-8-sig")

    def test_the_generated_files_are_fresh(self):
        for path, body in self.outputs.items():
            self.assertEqual(path.read_bytes(), body, f"{path.relative_to(ROOT)}: run gen_demog_towns.py")
            self.assertTrue(body.startswith(b"\xef\xbb\xbf") and not body.startswith(b"\xef\xbb\xbf" * 2))

    def test_vanilla_buildings_count_for_the_hub_their_meshes_stand_in(self):
        """Every base-game building that draws a mesh in a port, mine, farm or logging hub counts for that town."""
        vanilla = json.loads((ROOT / "vanilla_parsed" / "common" / "buildings.json").read_text(encoding="utf-8"))
        for key, body in vanilla.items():
            body = _unwrap(body)
            kind = _unwrap(body.get("city_type")) if isinstance(body, dict) else None
            if kind in gen.WORK_KINDS and str(_unwrap(body.get("levels_per_mesh"))) != "-1":
                with self.subTest(key):
                    self.assertIn(key, _trigger_types(self.triggers, f"te_demog_town_{kind}_work"))

    def test_the_mods_meshless_mines_are_mines_and_its_ocean_mine_a_port(self):
        """The mod's discoverable mines say city_type = city with levels_per_mesh = -1: they take their group's kind.
        The ocean mine says port, which it keeps; a railway (no city_type) counts for the capital."""
        mines = _trigger_types(self.triggers, "te_demog_town_mine_work")
        vanilla = json.loads((ROOT / "vanilla_parsed" / "common" / "buildings.json").read_text(encoding="utf-8"))
        for key in ("building_copper_mine", "building_lithium_mine", "building_rare_earth_metals_mine",
                    "building_bauxite_mine"):
            self.assertNotIn(key, vanilla, "a mod mine")
            self.assertIn(key, mines)
        self.assertIn("building_ocean_mine", _trigger_types(self.triggers, "te_demog_town_port_work"))
        listed = set(re.findall(r"is_building_type = (\w+)", self.triggers))
        self.assertNotIn("building_railway", listed)
        self.assertNotIn("building_eiffel_tower", listed)

    def test_only_subsistence_counts_for_no_town(self):
        groups = json.loads((ROOT / "vanilla_parsed" / "common" / "building_groups.json").read_text(encoding="utf-8"))
        subsistence = {g for g, body in groups.items() if _unwrap(_unwrap(body).get("is_subsistence")) == "yes"}
        vanilla = json.loads((ROOT / "vanilla_parsed" / "common" / "buildings.json").read_text(encoding="utf-8"))
        want = sorted(k for k, body in vanilla.items() if _unwrap(_unwrap(body).get("building_group")) in subsistence)
        self.assertTrue(want)
        self.assertEqual(_trigger_types(self.triggers, "te_demog_town_subsistence_work"), want)

    def test_a_hub_is_a_town_only_with_a_name(self):
        """The named lists are the map's hubs with a HUB_NAME_ key. A port hub is exactly a state with a naval exit
        (true of every state today), and every state has a named capital."""
        states = gen.state_hubs()
        keys = gen.hub_loc_keys()
        names = gen.named(states, keys)
        for _, kind, _ in gen.KINDS:
            for state in names[kind]:
                self.assertIn(f"HUB_NAME_{state}_{kind}", keys)
        self.assertEqual(len(names["city"]), len(states))
        self.assertIn("te_demog_town_named_city = {\n\talways = yes\n}", self.triggers)
        exits = set()
        for path in sorted((ROOT / "map_data" / "state_regions").glob("*.txt")):
            text = path.read_text(encoding="utf-8-sig")
            for m in re.finditer(r"(?m)^(STATE_\w+)\s*=\s*\{", text):
                end = text.find("\n}", m.end())
                if "naval_exit_id" in text[m.end():end]:
                    exits.add(m.group(1))
        self.assertEqual({s for s, hubs in states.items() if "port" in hubs}, exits & set(states))
        self.assertLess(len(names["mine"]), len(states), "a mining hub with no name is left out")

    def test_the_named_triggers_list_their_states(self):
        names = gen.named(gen.state_hubs(), gen.hub_loc_keys())
        everyone = set(gen.state_hubs())
        for _, kind, _ in gen.KINDS:
            body = _block(self.triggers, f"te_demog_town_named_{kind}")
            if "always = yes" in body:
                self.assertEqual(set(names[kind]), everyone, kind)
                continue
            listed = set(re.findall(r"state_region = s:(\w+)", body))
            want = set(names[kind]) if "NOT" not in body else everyone - set(names[kind])
            self.assertEqual(listed, want, kind)


def _store(w, named=None, before=None):
    """te_demog_town_walk_store on a state whose walk counted w (capital, port, mine, farm, logging): its towns."""
    eng = _Engine({}, triggers={**NAMED, **(named or {})})
    eng.vars.update(before or {})
    eng.locals.update({f"te_dg_tw_w{c}": float(x) for c, x in enumerate(w, start=1)})
    eng.call("te_demog_town_walk_store")
    n = int(eng.vars["te_dg_tw_n"])
    return [int(eng.vars[f"te_dg_tw_{k}"]) for k in range(1, n + 1)], eng.vars


class StateOrderTest(unittest.TestCase):
    def test_rural_work_counts_at_a_quarter(self):
        # 100, 10, 300/4 = 75, 500/4 = 125, 30/4 = 7.5: the farming town, the capital, mining, port, logging
        self.assertEqual(_store((100, 10, 300, 500, 30))[0], [4, 1, 3, 2, 5])
        # a mining district's 1,000 at a quarter (250) outruns a capital of 200
        self.assertEqual(_store((200, 0, 1000, 0, 0))[0][:2], [3, 1])

    def test_a_hub_with_no_name_is_no_town(self):
        # 100, port unnamed, 40/4 = 10, 80/4 = 20, 400/4 = 100: the capital ties the logging town and leads
        towns, _ = _store((100, 500, 40, 80, 400), {"te_demog_town_named_port": False})
        self.assertEqual(towns, [1, 5, 4, 3])

    def test_a_town_with_no_work_of_its_kind_is_no_town_but_the_capital_always_is(self):
        self.assertEqual(_store((0, 0, 0, 0, 0))[0], [1])
        self.assertEqual(_store((0, 0, 0, 40, 0))[0], [4, 1])
        self.assertEqual(_store((100, 0, 400, 0, 0))[0], [1, 3])

    def test_ties_go_to_the_earlier_kind(self):
        self.assertEqual(_store((40, 10, 160, 0, 0))[0], [1, 3, 2])
        self.assertEqual(_store((10, 40, 160, 160, 160))[0], [2, 3, 4, 5, 1])

    def test_a_state_with_no_named_hub_is_one_town_under_its_own_name(self):
        towns, _ = _store((100, 10, 0, 0, 0), {k: False for k in NAMED})
        self.assertEqual(towns, [0])

    def test_a_census_with_fewer_towns_drops_the_rest(self):
        _, kept = _store((100, 0, 10, 10, 10), {"te_demog_town_named_port": False},
                         before={"te_dg_tw_n": 5.0, "te_dg_tw_5": 5.0})
        self.assertEqual(kept["te_dg_tw_n"], 4.0)
        self.assertNotIn("te_dg_tw_5", kept)
        _, kept = _store((100, 0, 0, 0, 0), before={"te_dg_tw_n": 5.0, "te_dg_tw_2": 2.0, "te_dg_tw_5": 5.0})
        self.assertEqual(kept["te_dg_tw_n"], 1.0)
        self.assertFalse({"te_dg_tw_2", "te_dg_tw_5"} & set(kept))


def _state(urban, mt, towns, census=True):
    s = {"te_dg_urban": float(urban), "te_dg_tw_n": float(len(towns)), "state_population": float(urban) * 2}
    if mt is not None:
        s["te_dg_mt"] = float(mt)
    if census:
        s["te_dg_year"] = 1900.0
    s.update({f"te_dg_tw_{k}": float(c) for k, c in enumerate(towns, start=1)})
    return s


class CountryListTest(unittest.TestCase):
    def merge(self, states, fixtures=None):
        eng = _CountryEngine(states=states, fixtures=fixtures or {}, triggers={"te_demog_cohorts_run": True})
        eng.call("te_demog_town_country")
        slots = []
        for i in range(1, gen.SLOTS + 1):
            listed = eng.lists.get(f"te_dg_tw_l{i}", [])
            self.assertLessEqual(len(listed), 1)
            if listed:
                slots.append((states.index(listed[0]), int(eng.vars[f"te_dg_tw{i}_c"]), eng.vars[f"te_dg_tw{i}_p"]))
            else:
                self.assertNotIn(f"te_dg_tw{i}_c", eng.vars)
        return eng, slots

    def test_the_largest_towns_across_states(self):
        """A's second town (250K) outranks B's capital (120K): the list merges each state's towns by size."""
        a = _state(1_000_000, 50, [1, 2, 3, 4])
        b = _state(300_000, 40, [4, 1, 3, 5])
        small = _state(4_000, None, [1])              # under 5,000 urban people: no metropolitan share
        uncounted = _state(9_000_000, 60, [1], census=False)
        eng, slots = self.merge([a, b, small, uncounted])
        self.assertEqual([(s, c) for s, c, _ in slots],
                         [(0, 1), (0, 2), (0, 3), (1, 4), (1, 1), (0, 4), (1, 3), (1, 5)])
        for (_, _, people), want in zip(slots, (500_000, 250_000, 125_000, 120_000, 72_000, 62_500, 43_200, 25_920)):
            self.assertAlmostEqual(people, want, places=3)
        for st in (a, b, small, uncounted):
            self.assertNotIn("te_dg_tw_cur", st, "the cursors go once the list is built")

    def test_before_its_first_share_a_state_takes_the_shares_target(self):
        """te_dg_mt is seeded on the state's own yearly pulse, so a new game's census and a state's first year have
        none: the towns take the target it will be seeded at (te_demog_mt_target), under 5,000 urban people none."""
        new = _state(200_000, None, [1, 2])
        small = _state(4_000, None, [1])
        _, slots = self.merge([new, small], fixtures={"te_demog_mt_target": 50.0})
        self.assertEqual([(s, c) for s, c, _ in slots], [(0, 1), (0, 2)])
        for (_, _, people), want in zip(slots, (100_000, 50_000)):
            self.assertAlmostEqual(people, want, places=3)

    def test_ten_at_most_and_a_refill(self):
        states = [_state(100_000 * (i + 1), 30, [1, 2, 3]) for i in range(5)]
        eng, slots = self.merge(states)
        self.assertEqual(len(slots), 10)
        eng.call("te_demog_town_country")
        self.assertTrue(all(len(eng.lists[f"te_dg_tw_l{i}"]) == 1 for i in range(1, 11)), "refilled, not appended")

    def test_a_country_census_lists_its_towns(self):
        """te_demog_country_lists, which the census and the civil-war repair call, builds the slots."""
        self.assertIn("te_demog_town_country = yes", _block(_text(EFFECTS), "te_demog_country_lists"))


class WalkHookTest(unittest.TestCase):
    """The yearly walk (te_demog_walks, whose text the golden pins) reaches the towns through the work walk's three
    hooks, under the census's cohorts gate."""

    def test_the_hooks(self):
        text = _text(EFFECTS)
        self.assertIn("te_demog_town_walk_init = yes", _block(text, "te_demog_work_walk_init"))
        for hook, call in (("te_demog_work_walk_pop", "te_demog_town_walk_pop"),
                           ("te_demog_work_walk_store", "te_demog_town_walk_store")):
            body = _block(text, hook)
            gate = body.index("local_var:te_dg_w_on > 0")
            self.assertGreater(body.index(f"{call} = yes"), gate, hook)

    def test_each_pop_counts_for_its_workplaces_town(self):
        body = _block(_text(PLACE_EFFECTS), "te_demog_town_walk_pop")
        order = re.findall(r"te_demog_town_(\w+)_work = yes", body)
        self.assertEqual(order, ["port", "mine", "farm", "wood", "subsistence"])
        self.assertRegex(body, r"NOT = \{ workplace = \{ te_demog_town_subsistence_work = yes \} \}\s*\}\s*"
                               r"change_local_variable = \{ name = te_dg_tw_w1 add = total_size \}")
        self.assertRegex(body, r"else = \{\s*change_local_variable = \{ name = te_dg_tw_w1 add = total_size \}")


class RowsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = gh._type_body(gh._all_gui(), "te_demog_town_rows")
        cls.places = gh._type_body(gh._all_gui(), "te_demog_sec_places")

    def test_each_slot_reads_its_own_variables(self):
        slots = re.split(r"(?=flowcontainer = \{\s*datamodel)", self.rows)[1:]
        self.assertEqual(len(slots), gen.SLOTS)
        for i, slot in enumerate(slots, start=1):
            with self.subTest(slot=i):
                self.assertEqual(set(re.findall(r"GetList\('(\w+)'\)", slot)), {f"te_dg_tw_l{i}"})
                self.assertEqual(set(re.findall(r"Var\('(\w+)'\)", slot)), {f"te_dg_tw{i}_c", f"te_dg_tw{i}_p"})
                # on the country shown, which wrote the slot: a listed state that has changed hands since the
                # census has an owner with other slots, or none
                self.assertEqual(set(re.findall(r"([\w.]+)\.Var\('", slot)), {"Country.MakeScope"})
                self.assertNotIn("GetOwner", slot)
                codes = re.findall(r"\(CFixedPoint\)(\d)", slot)
                self.assertEqual(sorted(codes), ["0", "1", "2", "3", "4", "5"])
                for code, kind, accessor in gen.KINDS:
                    self.assertRegex(slot, rf"\(CFixedPoint\){code}' \)\]\" }}\s*blockoverride \"town_tooltip\" "
                                           rf"\{{ tooltip = \"te_demog_town_tt_{kind}\" }}\s*blockoverride \"town_name\" "
                                           rf"\{{ text = \"\[State\.{accessor}\]\" }}")

    def test_three_shown_and_the_rest_under_show_all(self):
        flag = self.rows.index("GetVariableSystem.Exists('te_demog_towns_all_open')")
        self.assertLess(self.rows.index("te_dg_tw_l3"), flag)
        self.assertGreater(self.rows.index("te_dg_tw_l4"), flag)

    def test_the_section_lists_the_cities_then_the_urban_states(self):
        order = [self.places.index(k) for k in ('"te_demog_towns_head"', "te_demog_town_rows = {}",
                                                "GetVariableSystem.Toggle('te_demog_towns_all_open')",
                                                '"te_demog_cities_head"', "GetList('te_dg_cities')")]
        self.assertEqual(order, sorted(order))
        self.assertIn("Not( IsDataModelEmpty( Country.MakeScope.GetList('te_dg_tw_l4') ) )", self.places,
                      "Show All only once a fourth town is listed")

    def test_the_row_fits_its_480(self):
        row = gh._type_body(gh._all_gui(), "te_demog_town_row")
        widths = [int(w) for w in re.findall(r"minimumsize = \{ (\d+) -1 \}", row)]
        self.assertEqual(widths, [184, 196, 84])
        self.assertLessEqual(4 + sum(widths) + 4 * (len(widths) - 1), 480)
        self.assertIn("size = { 480 28 }", row)


if __name__ == "__main__":
    unittest.main()
