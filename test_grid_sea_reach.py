"""How far an undersea cable reaches (Power Grids, power_grids.md § Undersea
cables): the table gen_grid_sea_reach.py measures from the map, the script that
reads it, and the self-check that holds it to the engine.

Game-free: reads map_data/, the committed sea borders and the generated file.
The one test that reads the install's provinces.png skips without it.
"""
import os
import re
import sys
import unittest
from collections import deque
from pathlib import Path

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import gen_grid_sea_reach as gen  # noqa: E402

COMMON = os.path.join(REPO, "common")
EFFECTS = os.path.join(COMMON, "scripted_effects", "power_grid_effects.txt")
GENERATED = os.path.join(REPO, str(gen.OUT))


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _code(text):
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _top_level(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert m, name
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class _Table:
    _cache = None

    @classmethod
    def get(cls):
        if cls._cache is None:
            region_seas, sea_next = gen.sea_map()
            cls._cache = (region_seas, sea_next, gen.reach(region_seas, sea_next))
        return cls._cache


class ReachTest(unittest.TestCase):
    """The distances, on the cases that led to the table (2026-11-24)."""

    def setUp(self):
        self.region_seas, self.sea_next, self.table = _Table.get()

    def hops(self, a, b):
        return self.table[a].get(b)

    def test_bermuda_reaches_the_american_coast(self):
        # Bermuda is the only state on the Sargasso Sea, which borders the
        # coastal seas: the walk from coast to coast reached nothing from it.
        self.assertEqual(self.region_seas["STATE_BERMUDA"], {"STATE_SARGASSO_SEA"})
        self.assertEqual(self.hops("STATE_BERMUDA", "STATE_NORTH_CAROLINA"), 2)
        self.assertEqual(self.hops("STATE_BERMUDA", "STATE_BAHAMAS"), 2)

    def test_hawaii_reaches_the_west_coast_at_three(self):
        # Five steps from coast to coast; across the North Pacific, three Sea Nodes.
        for coast in ("STATE_CALIFORNIA", "STATE_BAJA_CALIFORNIA", "STATE_ALASKA"):
            self.assertEqual(self.hops("STATE_HAWAIIAN_ISLANDS", coast), 3, coast)

    def test_the_southern_ocean_is_not_crossed(self):
        self.assertEqual(gen.UNCROSSABLE, {"STATE_SOUTHERN_OCEAN_01", "STATE_SOUTHERN_OCEAN_02"})
        for sea in gen.UNCROSSABLE:
            self.assertNotIn(sea, self.sea_next)
            self.assertFalse(any(sea in v for v in self.sea_next.values()), sea)
            self.assertFalse(any(sea in v for v in self.region_seas.values()), sea)
        # Two Sea Nodes from the Falklands to Queensland across it, before it was left out.
        self.assertIsNone(self.hops("STATE_SOUTH_ATLANTIC_ISLANDS", "STATE_QUEENSLAND"))
        self.assertIn("STATE_SOUTH_ATLANTIC_ISLANDS", self.region_seas)

    def test_a_coast_is_one_with_a_naval_exit(self):
        land = gen.read_land()
        coastal = {r for r, v in land.items() if v["naval_exit"] is not None}
        self.assertEqual(set(self.region_seas), coastal)
        for src, row in self.table.items():
            self.assertEqual(set(row) - coastal, set(), src)
        # The six Arctic regions that touch a sea with no naval exit carry no
        # cable on, so the Northwest Territories don't join the Chukchi Sea to
        # the Northwest Passage.
        self.assertIsNone(land["STATE_NORTHWEST_TERRITORIES"]["naval_exit"])
        self.assertNotIn("STATE_NORTHWEST_TERRITORIES", self.region_seas)
        self.assertNotIn("STATE_NORTHWEST_PASSAGE", self.sea_next["STATE_CHUCKCHI_SEA"])

    def test_a_naval_exit_counts_only_where_the_map_shows_no_sea(self):
        # Lithuania's exit is the Northern Baltic, which it doesn't touch on the
        # map; it stays two Sea Nodes from that sea's coasts, as the old walk had it.
        self.assertEqual(self.region_seas["STATE_LITHUANIA"], {"STATE_SOUTHERN_BALTIC_SEA"})
        self.assertEqual(self.hops("STATE_LITHUANIA", "STATE_UUSIMAA"), 2)

    def test_distances_are_symmetric_and_a_region_reaches_itself(self):
        for a, row in self.table.items():
            self.assertEqual(row.get(a), 1, a)
            for b, h in row.items():
                self.assertEqual(self.table[b].get(a), h, (a, b))
                self.assertTrue(1 <= h <= gen.MAX_HOPS, (a, b, h))

    def test_no_pair_is_farther_than_the_walk_from_coast_to_coast(self):
        """The walk the table replaced stepped between states sharing a Sea Node
        (every_sea_node_adjacent_state), rebuilt here from the same borders. The
        table must put no pair farther apart, so no grid that joined before
        splits. The six regions with no naval exit are taken as the engine is
        assumed to take them, not coastal; if it counted them, 20 pairs across
        the Arctic (Kamchatka to Hudson Bay) would be farther now, and a walk the
        self-check judges beside one would read missing=."""
        borders = gen.load_borders()["sea_borders"]
        seas, land = gen.read_seas(), gen.read_land()
        sea_of = {p: n for n, s in seas.items() for p in s["provinces"]}
        region_of = {p: n for n, r in land.items() for p in r["provinces"]}
        touch = {}
        for p, nbrs in borders.items():
            for n in nbrs:
                if n in region_of:
                    touch.setdefault(region_of[n], set()).add(sea_of[p])
        coastal = {r for r, v in land.items() if v["naval_exit"] is not None}
        for with_shores in (False,):
            states = {r: s for r, s in touch.items() if with_shores or r in coastal}
            on = {}
            for r, ss in states.items():
                for s in ss:
                    on.setdefault(s, set()).add(r)
            farther, pairs = [], 0
            for src in sorted(coastal & set(states)):
                hops, queue = {src: 0}, deque([src])
                while queue:
                    r = queue.popleft()
                    if hops[r] >= gen.MAX_HOPS:
                        continue
                    for s in states[r]:
                        for n in on[s]:
                            if n not in hops:
                                hops[n] = hops[r] + 1
                                queue.append(n)
                for dst, h in hops.items():
                    if dst != src and dst in coastal:
                        pairs += 1
                        if self.table[src].get(dst, gen.MAX_HOPS + 1) > h:
                            farther.append((src, dst, h, self.table[src].get(dst)))
            self.assertGreater(pairs, 17000)
            self.assertEqual(farther, [], f"with shores={with_shores}")


class RangeCapTest(unittest.TestCase):
    def test_the_table_goes_as_far_as_the_longest_cable(self):
        """Every Undersea Cable Range line in the mod, added up, is the longest a
        cable can be; the table must reach that far, or a longer cable stops short."""
        total = 0
        for dirpath, _dirs, files in os.walk(COMMON):
            if "modifier_type_definitions" in dirpath:
                continue
            for name in files:
                if name.endswith(".txt"):
                    text = _code(_read(os.path.join(dirpath, name)))
                    total += sum(int(n) for n in
                                 re.findall(r"\bbuilding_grid_undersea_cable_range_add\s*=\s*(\d+)", text))
        self.assertEqual(total, 3)
        self.assertGreaterEqual(gen.MAX_HOPS, total)


class ScriptTest(unittest.TestCase):
    def setUp(self):
        self.effects = _code(_read(EFFECTS))

    def test_the_walk_reads_the_table(self):
        walk = _top_level(self.effects, "te_grid_sea_reach_effect")
        self.assertTrue(walk.lstrip().startswith("te_grid_sea_reach_clear_effect = yes"))
        self.assertIn("set_variable = { name = te_grid_sea_hops value = 0 }", walk)
        self.assertIn("te_grid_sea_reach_table_effect = yes", walk)
        self.assertNotIn("sea_node_adjacent_state", walk)
        self.assertNotIn("while", walk)
        clear = _top_level(self.effects, "te_grid_sea_reach_clear_effect")
        self.assertIn("remove_variable = te_grid_sea_hops", clear)
        self.assertIn("clear_global_variable_list = te_grid_sea_reach", clear)
        for gone in ("te_grid_sea_layer", "te_grid_sea_next"):
            self.assertNotIn(gone, self.effects)

    def test_a_region_marks_its_coastal_states_once(self):
        region = _top_level(self.effects, "te_grid_sea_reach_region_effect")
        self.assertIn("$REGION$ = {", region)
        self.assertIn("every_scope_state", region)
        self.assertIn("is_coastal = yes", region)
        self.assertIn("NOT = { has_variable = te_grid_sea_hops }", region)
        self.assertIn("set_variable = { name = te_grid_sea_hops value = $HOPS$ }", region)
        self.assertIn("add_to_global_variable_list = { name = te_grid_sea_reach target = this }", region)

    def test_the_table_goes_ring_by_ring_within_the_radius(self):
        text = _read(GENERATED)
        self.assertTrue(text.startswith("# AUTO-GENERATED by scripts/generators/gen_grid_sea_reach.py"))
        body = _code(_top_level(text, "te_grid_sea_reach_table_effect"))
        branches = re.findall(r"(?m)^\t(?:if|else_if) = \{\n\t\tlimit = \{ state_region = s:(STATE_\w+) \}", body)
        _, _, table = _Table.get()
        self.assertEqual(branches, sorted(table))
        bermuda = re.search(r"s:STATE_BERMUDA \}(.*?)\n\t\}", body, re.S).group(1)
        rings = re.findall(r"local_var:te_grid_sea_radius >= (\d)", bermuda)
        self.assertEqual(rings, ["1", "2", "3"])
        self.assertIn("te_grid_sea_reach_region_effect = { REGION = s:STATE_BERMUDA HOPS = 1 }", bermuda)
        self.assertIn("te_grid_sea_reach_region_effect = { REGION = s:STATE_NORTH_CAROLINA HOPS = 2 }", bermuda)

    def test_self_check_compares_the_table_with_the_engine(self):
        links = _top_level(self.effects, "te_grid_cable_links_effect")
        self.assertLess(links.index("te_grid_sea_reach_effect = yes"),
                        links.index("te_grid_sea_table_selfcheck_effect = yes"))
        self.assertLess(links.index("te_grid_sea_table_selfcheck_effect = yes"),
                        links.index("te_grid_sea_reach_clear_effect = yes"))
        check = _top_level(_read(EFFECTS), "te_grid_sea_table_selfcheck_effect")
        self.assertIn("NOT = { has_global_variable = te_grid_sea_table_checked }", check)
        self.assertIn("set_global_variable = te_grid_sea_table_checked", check)
        # Never judged on an island alone on its Sea Node, which would read OK on nothing.
        guard = check[:check.index("set_global_variable = te_grid_sea_table_checked")]
        self.assertIn("any_sea_node_adjacent_state", guard)
        # The table goes by region and the engine by state: the start must hold its
        # region whole, and extra= counts only whole regions.
        whole = "any_scope_state = { NOT = { this = scope:te_grid_chk_sea_from } }"
        self.assertIn(whole, guard)
        extra = check[check.index("variable = te_grid_sea_reach"):]
        self.assertIn("any_scope_state = { NOT = { this = scope:te_grid_chk_sea_to } }", extra)
        self.assertIn("TE_GRID sea_table_missing", check)
        self.assertIn("TE_GRID sea_table_extra", check)
        self.assertIn("every_sea_node_adjacent_state", check)
        self.assertIn("TE_SELF_CHECK OK grid_sea_table", check)
        self.assertIn("TE_SELF_CHECK BROKEN grid_sea_table", check)


class FreshnessTest(unittest.TestCase):
    def test_the_committed_table_is_current(self):
        self.assertEqual(gen.regenerate(dry_run=True)["changed_files"], [])

    def test_the_borders_name_every_sea_province(self):
        borders = gen.load_borders()["sea_borders"]
        provinces = {p for s in gen.read_seas().values() for p in s["provinces"]}
        self.assertEqual(len(gen.read_seas()), 106)
        self.assertEqual(set(borders), provinces)

    def test_the_borders_match_the_installed_map(self):
        try:
            game = gen._game_dir()
        except Exception:  # no install configured
            self.skipTest("no Victoria 3 install")
        png = Path(game) / "map_data" / "provinces.png"
        if not png.is_file():
            self.skipTest("no provinces.png in the install")
        recorded = gen.load_borders()["provinces_png"]
        self.assertEqual(
            (png.stat().st_size, gen._sha256(png)), (recorded["size"], recorded["sha256"]),
            "the map changed: run scripts/generators/gen_grid_sea_reach.py --refresh")


if __name__ == "__main__":
    unittest.main()
