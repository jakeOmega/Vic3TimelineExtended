"""The state pictures (docs/superpowers/specs/2026-11-10-state-pictures-design.md): the registry, the
generated terrain file and the yearly pass that stores each state's city size.

The engine facts the file rests on were read in game on 2026-11-10 (scripting_best_practices.md § "State
pictures"): an INJECT adds to a terrain's `textures` list, and an entry without an `effect` is an error that
leaves its state with the plains picture. So every entry here must carry one.
"""

import importlib.util
import json
import re
import struct
import subprocess
import unittest

from test_demographics_registry import ROOT, _Engine, _raw_blocks

REGISTRY_PATH = ROOT / "scripts" / "image_pipeline" / "state_picture_registry.py"
GENERATOR_PATH = ROOT / "scripts" / "generators" / "gen_state_pictures.py"
GENERATED = ROOT / "common" / "terrain" / "te_state_pictures_generated.txt"
VALUES = ROOT / "common" / "script_values" / "te_state_picture_values.txt"
EFFECTS = ROOT / "common" / "scripted_effects" / "te_state_picture_effects.txt"
TRIGGERS = ROOT / "common" / "scripted_triggers" / "te_state_picture_triggers.txt"
ON_ACTIONS = ROOT / "common" / "on_actions" / "te_state_picture_on_actions.txt"
DEBUG_EVENTS = ROOT / "events" / "te_debug_state_picture_events.txt"
VANILLA_TERRAINS = ROOT / "vanilla_parsed" / "common" / "terrains.json"
VANILLA_TECHS = ROOT / "vanilla_parsed" / "common" / "technologies.json"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


registry = _load("state_picture_registry", REGISTRY_PATH)
generator = _load("gen_state_pictures", GENERATOR_PATH)

try:
    import sys

    import numpy as np
    from PIL import Image

    sys.path.insert(0, str(REGISTRY_PATH.parent))
    import convert_state_picture as converter
except ImportError:  # CI installs numpy but not Pillow
    converter = None


def _vanilla_terrains():
    return json.loads(VANILLA_TERRAINS.read_text(encoding="utf-8"))


def _vanilla_effects():
    return set(re.findall(r'vfx_entity_ui_state_\w+', VANILLA_TERRAINS.read_text(encoding="utf-8")))


def _mod_techs():
    keys = set(json.loads(VANILLA_TECHS.read_text(encoding="utf-8")))
    for path in (ROOT / "common" / "technology" / "technologies").glob("*.txt"):
        keys.update(re.findall(r"^(?:[A-Z_]+:)?([a-z0-9_]+)\s*=\s*\{", path.read_text(encoding="utf-8-sig"), re.M))
    return keys


class TestRegistry(unittest.TestCase):
    def test_every_picture_names_real_things(self):
        terrains, effects, techs = _vanilla_terrains(), _vanilla_effects(), _mod_techs()
        for key, p in registry.PICTURES.items():
            with self.subTest(key):
                self.assertRegex(key, r"^[a-z0-9_]+$")
                self.assertTrue(p["terrain"])
                for terrain in p["terrain"]:
                    self.assertIn(terrain, terrains)
                self.assertIn(p["tech"], techs)
                self.assertIn(p["rung"], range(1, 10))
                self.assertTrue(p["region"] is None or any(p["region"] in g for g in registry.REGION_GROUPS.values()))
                self.assertTrue(p["size"] is None or p["size"] in registry.SIZES)
                self.assertTrue(p.get("scale") is None or p["scale"] in registry.SCALES)
                self.assertFalse(p["size"] and p.get("scale"), "a size and a scale share one place in the weight")
                # the engine rejects an entry without an effect; a vanilla entity is known to exist
                self.assertIn(p["effect"], effects)
                self.assertTrue(p["prompt"].strip())

    def test_every_pick_names_boxes_inside_the_render(self):
        for key, p in registry.PICTURES.items():
            for left, top, right, bottom in ([p["crop"]] if p.get("crop") else []) + list(p.get("smudge", [])):
                with self.subTest(key):
                    self.assertTrue(0 <= left < right <= 1536 and 0 <= top < bottom <= 752)
            if p.get("crop"):
                left, top, right, bottom = p["crop"]
                with self.subTest(key, crop=p["crop"]):
                    self.assertAlmostEqual((right - left) / (bottom - top), 1020 / 500, delta=0.03)

    def test_the_port_picture_needs_a_port(self):
        # vanilla's docks terrain prevails in every one-province state and shows its dry plain where there is no port
        for key, p in registry.PICTURES.items():
            if "docks" in p["terrain"]:
                with self.subTest(key):
                    self.assertIn("has_building = building_port", p.get("where", []))
                    self.assertIn("has_building = building_port", generator.conditions(key))

    def test_no_picture_takes_an_overlay_placed_for_vanillas_painting(self):
        # vanilla's European city overlay has smoke over its own chimneys, its Asian one surf on its own shore
        self.assertEqual(registry.NEUTRAL_OVERLAY, "vfx_entity_ui_state_docks")
        for key, p in {**registry.PICTURES, **{k: d for k, d in registry.DRAFTS.items() if "effect" in d}}.items():
            with self.subTest(key):
                self.assertNotIn(p["effect"], registry.PLACED_OVERLAYS)

    def test_no_two_pictures_of_a_terrain_can_tie(self):
        # the highest weight wins; two families can hold the same state (Japan lies inside East Asia), so no two
        # pictures of a terrain may weigh the same, whatever their regions
        seen = {}
        for key in registry.PICTURES:
            for terrain in registry.terrains(key):
                spot = (terrain, registry.weight(key, terrain))
                self.assertNotIn(spot, seen, f"{key} and {seen.get(spot)} weigh the same in {terrain}")
                seen[spot] = key

    def test_every_region_family_has_its_own_digit(self):
        names = [name for families in registry.REGION_GROUPS.values() for name in families]
        self.assertEqual(len(set(names)), len(names), "a family belongs to one group")
        for group, families in registry.REGION_GROUPS.items():
            digits = [digit for _lines, digit in families.values()]
            self.assertEqual(len(set(digits)), len(digits), group)
            self.assertTrue(all(1 <= d <= 9 for d in digits))
            for name, (lines, _digit) in families.items():
                with self.subTest(name):
                    # only a group's fallback family may have no trigger of its own
                    self.assertTrue(lines or registry.GROUP_FALLBACK.get(group) == name)
                    for line in lines:
                        self.assertRegex(line, r"^(is_in_geographic_region = geographic_region_[a-z_]+|is_[a-z_]+ = yes)$")
        for name, (lines, _digit) in registry.REGIONS.items():
            for line in lines:
                self.assertRegex(line, r"^is_in_geographic_region = geographic_region_[a-z_]+$")
        # vanilla ranks Japan over the East Asia that contains it
        self.assertGreater(registry.REGIONS["japanese"][1], registry.REGIONS["east_asian"][1])

    def test_an_overlapped_family_is_wired_with_the_family_it_overlaps(self):
        # a rung outranks a family's digit: East Asian rung 2 without Japanese rung 2 would show in Tokyo
        wired = registry.wired()
        spots = {(tuple(p["terrain"]), p["rung"], p["size"], p["region"]) for p in wired.values()}
        for winner, other in registry.REGION_OVERLAPS:
            self.assertGreater(registry.REGIONS[winner][1], registry.REGIONS[other][1])
            for terrain, rung, size, region in spots:
                if region == other:
                    with self.subTest(winner=winner, rung=rung, size=size):
                        self.assertIn((terrain, rung, size, winner), spots)

    def test_a_plain_and_a_special_picture_of_a_rung_are_wired_together(self):
        for keys in registry.WIRED_TOGETHER:
            if all(key in registry.PICTURES for key in keys):     # a draft not yet promoted holds nothing
                with self.subTest(keys):
                    wired = {registry.PICTURES[key]["seed"] is not None for key in keys}
                    self.assertEqual(len(wired), 1, f"wire {keys} together")

    def test_wave_3_wiring_covers_its_drafts(self):
        worked = {k for k, d in registry.DRAFTS.items() if d["family"] in ("port", "mine", "oil", "farm", "forest")}
        promoted = set(registry.WAVE3_PICKS)
        self.assertEqual(worked | promoted, set(registry.WAVE3_WIRING))
        for key, wiring in registry.WAVE3_WIRING.items():
            with self.subTest(key):
                self.assertLessEqual(set(wiring), {"region", "scale", "over", "where"})
                if wiring.get("region"):
                    self.assertTrue(any(wiring["region"] in g for g in registry.REGION_GROUPS.values()))
        for key, pick in registry.WAVE3_PICKS.items():
            with self.subTest(key):
                self.assertIsNotNone(pick.get("seed"))

    def test_wave_6_wiring_covers_what_a_weight_can_read_live(self):
        city = {k for k, d in registry.DRAFTS.items() if d["family"] in ("character", "function", "condition")}
        waiting = {k for k in city if k.startswith(registry.WAVE6_NEEDS_THE_PASS + registry.WAVE6_NEEDS_A_MARKER)}
        self.assertEqual((city - waiting) | set(registry.WAVE6_PICKS), set(registry.WAVE6_WIRING))
        self.assertFalse(waiting & set(registry.WAVE6_WIRING))
        for key, wiring in registry.WAVE6_WIRING.items():
            with self.subTest(key):
                self.assertEqual(len(wiring), 1)
                (axis, name), = wiring.items()
                self.assertIn(name, {"character": registry.CHARACTERS, "condition": registry.CONDITIONS}[axis])
        for table in (registry.CHARACTERS, registry.CONDITIONS):
            digits = [digit for _lines, digit in table.values()]
            self.assertEqual(len(set(digits)), len(digits))
            self.assertTrue(all(1 <= d <= 9 for d in digits))

    def test_the_weight_places_keep_their_order(self):
        # region < size or scale < character < rung < takeover or condition, each place wide enough
        # for nine of the one below; and no weight outgrows a 32-bit float's whole numbers
        r = registry
        self.assertLess(9 * r.W_REGION, r.W_SIZE)
        self.assertLess(9 * r.W_SIZE + 9 * r.W_REGION, r.W_CHAR)
        self.assertLess(9 * r.W_CHAR + 9 * r.W_SIZE + 9 * r.W_REGION, r.W_RUNG)
        self.assertLess(9 * r.W_RUNG + 9 * r.W_CHAR + 9 * r.W_SIZE + 9 * r.W_REGION, r.W_COND)
        top = r.W_OVER + r.W_COND * max(d for _l, d in r.CONDITIONS.values()) + 9 * r.W_RUNG + 9 * r.W_CHAR + 99
        self.assertLess(top, 2 ** 24)
        for key in r.PICTURES:
            for terrain in r.terrains(key):
                self.assertLess(r.weight(key, terrain), 2 ** 24, key)
        # a great city's takeover stands above the oil field's and under the lowest condition
        most = 9 * r.W_RUNG + 9 * r.W_CHAR + 9 * r.W_UPKEEP + 9 * r.W_MEANS + 99
        self.assertLess(r.W_OVER + most, r.W_CITY_OVER)
        self.assertLess(r.W_CITY_OVER + most, r.W_OVER + r.W_COND * min(d for _l, d in r.CONDITIONS.values()))

    def test_wave_7_wiring_covers_its_drafts(self):
        nature = {k for k, d in registry.DRAFTS.items() if d["family"] == "nature"}
        self.assertEqual(nature | set(registry.WAVE7_PICKS), set(registry.WAVE7_WIRING))
        terrains = _vanilla_terrains()
        for key, wiring in registry.WAVE7_WIRING.items():
            with self.subTest(key):
                self.assertLessEqual(set(wiring), {"region", "any_region"})
                if wiring.get("region"):
                    self.assertIn(registry.region_group(wiring["region"]), ("land", "desert", "hills"))
                for terrain in wiring.get("any_region", []):
                    self.assertIn(terrain, terrains)
        # a group's families are wired together: one rung, so a family wired alone would leave its
        # neighbors on vanilla's picture beside it, and the fallback's "none of the others" assumes them
        for group in ("land", "desert", "hills"):
            keys = [k for k, w in registry.WAVE7_WIRING.items()
                    if w.get("region") and registry.region_group(w["region"]) == group]
            for terrain in {t for k in keys for t in (registry.PICTURES.get(k) or registry.DRAFTS[k])["terrain"]
                            if t not in registry.WAVE7_WIRING[k].get("any_region", [])}:
                here = [k for k in keys if terrain in (registry.PICTURES.get(k) or registry.DRAFTS[k])["terrain"]]
                with self.subTest(group=group, terrain=terrain):
                    self.assertEqual(len({k in registry.WAVE7_PICKS for k in here}), 1, f"wire {here} together")

    def test_a_picture_asks_for_no_region_in_its_any_region_terrains(self):
        for key, p in registry.wired().items():
            for terrain in p.get("any_region", []):
                with self.subTest(key, terrain=terrain):
                    self.assertIn(terrain, p["terrain"])
                    self.assertFalse(set(registry.region_conditions(p["region"])) & set(generator.conditions(key, terrain)))
                    self.assertTrue(set(registry.region_conditions(p["region"])) <= set(generator.conditions(key)))

    def test_the_fallback_family_takes_the_states_of_no_family(self):
        fallback = registry.FALLBACK_REGION
        lines = registry.region_conditions(fallback)
        self.assertEqual(lines[0], "OR = {")
        self.assertIn("\tAND = {", lines)
        self.assertEqual("".join(lines).count("{"), "".join(lines).count("}"))
        for name, (own, _digit) in registry.REGIONS.items():
            for line in own:
                negated = "\t\t" + line.replace("is_in_geographic_region", "is_not_in_geographic_region")
                with self.subTest(name, line=line):
                    self.assertEqual(negated in lines, name != fallback)
        # every other family is its own triggers, any one of them
        self.assertEqual(registry.region_conditions("japanese"), registry.REGIONS["japanese"][0])
        self.assertEqual(registry.region_conditions("east_asian")[0], "OR = {")

    def test_every_draft_names_real_things_and_none_is_wired(self):
        terrains, techs = _vanilla_terrains(), _mod_techs()
        vanilla_pictures = set(re.findall(r"gfx/state_pictures/(\w+)\.dds", VANILLA_TERRAINS.read_text(encoding="utf-8")))
        generated = GENERATED.read_text(encoding="utf-8-sig")
        self.assertFalse(set(registry.DRAFTS) & set(registry.PICTURES), "a draft moves to PICTURES, it isn't copied")
        for key, d in registry.DRAFTS.items():
            with self.subTest(key):
                self.assertRegex(key, r"^[a-z0-9_]+$")
                self.assertTrue(d["terrain"])
                for terrain in d["terrain"]:
                    self.assertIn(terrain, terrains)
                self.assertIn(d["tech"], techs)
                self.assertIn(d["tech"], registry.WHEN)
                self.assertIn(registry.WHEN[d["tech"]], d["prompt"])
                self.assertIn(d["rung"], range(1, 10))
                self.assertIn(d["like"], vanilla_pictures)
                self.assertNotIn(generator.picture_path(key), generated)

    def test_the_generic_farmland_is_the_states_of_no_other_family(self):
        self.assertEqual(registry.region_conditions("farm_generic"),
                         ["is_arabic_farmland = no", "is_asian_farmland = no", "is_subtropic_farmland = no"])
        self.assertEqual(registry.region_conditions("farm_asian"), ["is_asian_farmland = yes"])
        # a family of several triggers is any one of them, and a group without a fallback negates nothing
        tropical = registry.region_conditions("forest_tropical")
        self.assertEqual((tropical[0], tropical[-1]), ("OR = {", "}"))
        self.assertNotIn("is_not_in_geographic_region", "".join(tropical))

    def test_a_scale_is_a_building_level_check_or_a_tag_of_the_pass(self):
        digits = [digit for _lines, digit in registry.SCALES.values()]
        self.assertTrue(all(1 <= d <= 9 for d in digits))
        for name, (lines, _digit) in registry.SCALES.items():
            with self.subTest(name):
                for line in lines:
                    # a level check in the form read in game on 2026-11-10 (scripting_best_practices.md,
                    # "State pictures"), or a tag the yearly pass stores on the state
                    self.assertRegex(line, r"^(any_scope_building = \{ is_building_type = building_[a-z_]+ level >= \d+ \}"
                                           r"|has_variable = te_sp_[a-z]+)$")

    def test_a_great_city_takes_over_every_other_land_terrain(self):
        # the engine can hold a metropolis's state to be farmland (Singapore, 2026-11-11), so a city
        # picture is in every land terrain's list, not the city's alone
        land = set(_vanilla_terrains()) - {"ocean", "lakes"}
        self.assertEqual(set(registry.CITY_TAKEOVER_TERRAINS), land - {registry.CITY_TERRAIN})
        self.assertEqual(len(set(registry.CITY_TAKEOVER_TERRAINS)), len(registry.CITY_TAKEOVER_TERRAINS))
        guard = registry.SIZES[registry.CITY_TAKEOVER_SIZE][0]
        cities = [k for k, p in registry.PICTURES.items() if registry.CITY_TERRAIN in p["terrain"]]
        self.assertGreater(len(cities), 60)
        for key in cities:
            p = registry.PICTURES[key]
            with self.subTest(key):
                self.assertEqual(p["terrain"], [registry.CITY_TERRAIN])
                if p["size"] == "town":
                    self.assertEqual(registry.terrains(key), p["terrain"])
                    continue
                self.assertEqual(set(registry.terrains(key)), land)
                # in the city's own list nothing changes; elsewhere the size comes first
                self.assertEqual(registry.weight(key, registry.CITY_TERRAIN), registry.weight(key))
                if p["size"] is None:
                    self.assertFalse(set(guard) & set(generator.conditions(key)))
                for terrain in registry.CITY_TAKEOVER_TERRAINS:
                    wants = generator.conditions(key, terrain)
                    self.assertEqual(wants[:len(guard)], guard)
                    self.assertEqual(sorted(wants), sorted({*guard, *generator.conditions(key)}))
        for key, p in registry.PICTURES.items():
            if registry.CITY_TERRAIN not in p["terrain"]:
                with self.subTest(key):
                    self.assertEqual(registry.terrains(key), p["terrain"])
                    self.assertFalse(any(registry.takes_over(key, t) for t in _vanilla_terrains()))

    def test_a_great_city_outranks_the_land_and_keeps_the_citys_own_order(self):
        lists = generator.by_terrain(registry.PICTURES)
        own = lists[registry.CITY_TERRAIN]
        for terrain in registry.CITY_TAKEOVER_TERRAINS:
            keys = lists[terrain]
            cities = [k for k in keys if registry.takes_over(k, terrain)]
            with self.subTest(terrain):
                # the land's own pictures and the oil field, then the city pictures in the city's order
                self.assertEqual(keys[-len(cities):], cities)
                self.assertEqual(cities, [k for k in own if k in cities])
                self.assertEqual(set(cities), {k for k in own if registry.PICTURES[k]["size"] != "town"})

    def test_a_takeover_outranks_every_rung(self):
        top = registry.W_RUNG * 9 + registry.W_SIZE * 9 + registry.W_REGION * 9
        self.assertGreater(registry.W_OVER, top)

    def test_no_prompt_uses_a_word_that_draws_lettering_or_a_landmark(self):
        avoid = re.compile(r"\b(" + "|".join(map(re.escape, registry.PROMPT_AVOID)) + r")\b", re.I)
        for key, p in {**registry.PICTURES, **registry.DRAFTS}.items():
            with self.subTest(key):
                self.assertIsNone(avoid.search(p["prompt"]))
                # the second text encoder reads 256 tokens; a longer prompt loses its end, where the "no text" tail is
                self.assertLessEqual(len(registry.full_prompt(key).split()), 140)

    def test_the_city_tier_is_whole(self):
        # wave 2: every region family on every rung of the city ladder, each on its rung's technology
        for region in registry.REGIONS:
            for rung, (tech, _when) in registry.CITY_LADDER.items():
                with self.subTest(region=region, rung=rung):
                    p = registry.PICTURES[f"urban_{region}_{rung}"]
                    self.assertEqual((p["tech"], p["rung"], p["region"], p["size"]), (tech, rung, region, None))
                    self.assertIn(registry.CITY_LANDMARK[region], p["prompt"])

    def test_every_weight_outranks_vanilla(self):
        for key in registry.PICTURES:
            self.assertGreater(registry.weight(key), 2)

    def test_a_larger_size_outranks_a_smaller_and_a_rung_outranks_a_size(self):
        digits = sorted(d for _lines, d in registry.SIZES.values())
        self.assertEqual(len(set(digits)), len(digits))
        top_region = registry.W_REGION * max(d for _lines, d in registry.REGIONS.values())
        self.assertGreater(registry.W_RUNG, registry.W_SIZE * max(digits) + top_region)
        self.assertGreater(registry.W_SIZE, top_region)

    def test_the_size_conditions_read_the_pass_variable(self):
        effects = EFFECTS.read_text(encoding="utf-8-sig")
        self.assertIn("set_variable = { name = te_sp_size", effects)
        for name, (lines, _digit) in registry.SIZES.items():
            with self.subTest(name):
                # a missing variable must fail the picture, not error: the guard comes first
                self.assertEqual(lines[0], "has_variable = te_sp_size")
                self.assertRegex(lines[1], r"^var:te_sp_size [<>]= [1-4]$")


class TestGeneratedFile(unittest.TestCase):
    def test_the_committed_file_is_current(self):
        self.assertEqual(GENERATED.read_text(encoding="utf-8"), generator.render(),
                         "run scripts/generators/gen_state_pictures.py")

    def test_one_bom_and_tabs(self):
        raw = GENERATED.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))
        self.assertNotRegex(GENERATED.read_text(encoding="utf-8-sig"), r"(?m)^ +\S")

    def test_every_entry_has_a_path_and_an_effect(self):
        text = GENERATED.read_text(encoding="utf-8-sig")
        self.assertEqual(text.count("{"), text.count("}"))
        wired = registry.wired()
        entries = sum(len(p["terrain"]) for p in wired.values())
        self.assertEqual(len(re.findall(r'^\t\t\tpath = "gfx/state_pictures/te_\w+\.dds"$', text, re.M)), entries)
        self.assertEqual(len(re.findall(r'^\t\t\teffect = "vfx_entity_ui_state_\w+"$', text, re.M)), entries)
        # a great city's entries in the terrains it takes over, one line each
        taken = sum(len(registry.terrains(key)) - len(p["terrain"]) for key, p in wired.items())
        self.assertGreater(taken, 0)
        one_line = (r'^\t\t\{ weight = \{ value = 0 if = \{ limit = \{ scope:state = \{ has_variable = te_sp_size '
                    r'var:te_sp_size >= 3 .+ \} \} add = \d+ \} \} path = "gfx/state_pictures/te_\w+\.dds" '
                    r'effect = "vfx_entity_ui_state_\w+" \}$')
        self.assertEqual(len(re.findall(one_line, text, re.M)), taken)
        self.assertEqual(text.count("path = "), entries + taken)
        # only INJECTs: a bare or REPLACEd terrain would drop vanilla's own pictures and its map fields
        tops = re.findall(r"^(\S[^=\n]*?)\s*=\s*\{", text, re.M)
        self.assertTrue(tops)
        for top in tops:
            self.assertRegex(top, r"^INJECT:[a-z_]+$")

    def test_only_picked_pictures_are_wired(self):
        text = GENERATED.read_text(encoding="utf-8-sig")
        for key, p in registry.PICTURES.items():
            with self.subTest(key):
                self.assertEqual(generator.picture_path(key) in text, p["seed"] is not None)

    def test_the_wired_pictures_are_tracked_and_the_right_size(self):
        tracked = set(subprocess.run(["git", "-C", str(ROOT), "ls-files", "--", "gfx/state_pictures/"],
                                     capture_output=True, text=True, check=True).stdout.split())
        for key in registry.wired():
            path = generator.picture_path(key)
            with self.subTest(key):
                self.assertIn(path, tracked)
                on_disk = ROOT / path
                if on_disk.exists():  # a sparse checkout leaves gfx/ out
                    header = on_disk.read_bytes()[:20]
                    height, width = struct.unpack("<II", header[12:20])
                    self.assertEqual((width, height), (1020, 500))


@unittest.skipIf(converter is None, "needs Pillow")
class TestConverter(unittest.TestCase):
    def test_a_dark_strip_along_an_edge_is_found(self):
        # one seed's renders often end in 9 to 25 near-black rows; such a picture must be cropped, not shipped
        clean = Image.new("RGB", (200, 100), (120, 140, 160))
        self.assertIsNone(converter.dark_edge(clean))
        banded = clean.copy()
        banded.paste((2, 2, 2), (0, 90, 200, 100))
        self.assertEqual(converter.dark_edge(banded), "bottom")
        banded = clean.copy()
        banded.paste((2, 2, 2), (0, 0, 200, 10))
        self.assertEqual(converter.dark_edge(banded), "top")
        # a dark picture is not a strip: night streets and smoke stay
        self.assertIsNone(converter.dark_edge(Image.new("RGB", (200, 100), (30, 30, 34))))

    def test_a_smudge_blurs_its_box_and_leaves_the_rest(self):
        img = Image.new("RGB", (300, 200), (200, 200, 200))
        for x in range(100, 160, 6):                        # a "sign": black strokes on white
            img.paste((0, 0, 0), (x, 80, x + 3, 110))
        before = np.asarray(img, dtype=float)
        after = np.asarray(converter.smudge(img.copy(), [(96, 76, 164, 114)]), dtype=float)
        self.assertEqual(before.shape, after.shape)
        inside = (slice(84, 106), slice(104, 156))
        self.assertLess(after[inside].std(), before[inside].std() / 3)     # the strokes are gone
        self.assertTrue((after[:40] == before[:40]).all())                 # far from the box, nothing moved
        self.assertTrue((after[:, :40] == before[:, :40]).all())


class TestYearlyPass(unittest.TestCase):
    """te_state_picture_refresh: the size its people make a state, kept until it falls a tenth below the floor."""

    def refresh(self, urban, share=None, size=None):
        eng = _Engine({}, effects={**_raw_blocks([EFFECTS]), "te_state_picture_selfcheck": "",
                                   "te_state_picture_refresh_land": "", "te_state_picture_refresh_city": "",
                                   "te_state_picture_refresh_prosperity": ""})
        eng.values.update(_raw_blocks([VALUES]))
        if urban is not None:
            eng.vars["te_dg_urban"] = float(urban)
        if share is not None:
            eng.vars["te_dg_mt"] = float(share)
        if size is not None:
            eng.vars["te_sp_size"] = float(size)
        eng.call("te_state_picture_refresh")
        return eng.vars.get("te_sp_size")

    def test_no_walk_no_size(self):
        self.assertIsNone(self.refresh(None))
        self.assertIsNone(self.refresh(None, size=3))

    def test_the_first_size_is_the_one_its_people_make(self):
        # the largest city: urban people x the metropolitan share
        self.assertEqual(self.refresh(100_000, share=50), 1)       # 50,000
        self.assertEqual(self.refresh(400_000, share=50), 2)       # 200,000
        self.assertEqual(self.refresh(4_000_000, share=50), 3)     # 2,000,000
        self.assertEqual(self.refresh(30_000_000, share=50), 4)    # 15,000,000

    def test_without_a_census_share_the_base_share_stands_in(self):
        self.assertEqual(self.refresh(2_400_000), 2)               # x 0.4 = 960,000
        self.assertEqual(self.refresh(2_600_000), 3)               # x 0.4 = 1,040,000

    def test_a_size_is_kept_until_a_tenth_below_its_floor(self):
        self.assertEqual(self.refresh(1_900_000, share=50, size=3), 3)   # 950,000: under the floor, kept
        self.assertEqual(self.refresh(1_700_000, share=50, size=3), 2)   # 850,000: lost
        self.assertEqual(self.refresh(1_900_000, share=50, size=2), 2)   # and not regained until the floor
        self.assertEqual(self.refresh(2_000_000, share=50, size=2), 3)

    def test_a_size_can_move_more_than_one_step(self):
        self.assertEqual(self.refresh(30_000_000, share=50, size=1), 4)
        self.assertEqual(self.refresh(100_000, share=50, size=4), 1)

    def land(self, levels, oil=0, mines=0, coal=0, tagged=()):
        """The tags after a pass over a state of that many levels: the walk's sums stubbed in."""
        sums = {"te_sp_all": levels, "te_sp_oil_lv": oil, "te_sp_mine": mines, "te_sp_coal_lv": coal,
                "te_sp_heavy_lv": 0, "te_sp_tour_lv": 0}
        stub = "\n".join(f"set_local_variable = {{ name = {k} value = {v} }}" for k, v in sums.items())
        eng = _Engine({}, effects={**_raw_blocks([EFFECTS]), "te_state_picture_land_sums": stub,
                                   "te_state_picture_land_selfcheck": ""})
        eng.values.update(_raw_blocks([VALUES]))
        for name in tagged:
            eng.vars[name] = 1.0
        eng.call("te_state_picture_refresh_land")
        return {name for name in ("te_sp_oil", "te_sp_coal") if name in eng.vars}

    def city(self, size=2, levels=1000, heavy=0, tour=0, walk=None, prev=None, prov=10, gini=None, state=None):
        """The state's variables after a pass: the walk's sums stubbed in, the Demographics walk's figures as given,
        and `state` the variables it carried in (tags, te_sp_growth, te_sp_prov)."""
        sums = {"te_sp_all": levels, "te_sp_oil_lv": 0, "te_sp_mine": 0, "te_sp_coal_lv": 0,
                "te_sp_heavy_lv": heavy, "te_sp_tour_lv": tour}
        stub = "\n".join(f"set_local_variable = {{ name = {k} value = {v} }}" for k, v in sums.items())
        eng = _Engine({}, effects={**_raw_blocks([EFFECTS]), "te_state_picture_land_sums": stub,
                                   "te_state_picture_land_selfcheck": ""})
        eng.values.update(_raw_blocks([VALUES]))
        eng.triggers.update(_raw_blocks([TRIGGERS]))
        eng.vars.update({"te_sp_size": float(size), **{k: float(v) for k, v in (state or {}).items()}})
        if walk is not None:
            eng.vars.update({"te_dg_walk_pop": float(walk), "te_dg_walk_pop_prev": float(prev),
                             "te_dg_provinces": float(prov)})
        if gini is not None:
            eng.vars["te_dg_gini"] = gini
        eng.call("te_state_picture_refresh_land")
        eng.call("te_state_picture_refresh_city")
        return eng.vars

    def years(self, rates, **kw):
        """The state after a run of yearly growth rates, each pass carrying the last one's variables."""
        state, people = {}, 1_000_000.0
        for rate in rates:
            new = people * (1 + rate)
            out = self.city(walk=new, prev=people, state=state, **kw)
            state = {k: v for k, v in out.items() if k.startswith("te_sp_") and k != "te_sp_size"}
            people = new
        return state

    def test_a_heavy_industry_city_and_a_resort_are_shares_of_the_states_levels(self):
        self.assertIn("te_sp_industry", self.city(levels=1000, heavy=250))
        self.assertNotIn("te_sp_industry", self.city(levels=1000, heavy=240))      # under a quarter
        self.assertNotIn("te_sp_industry", self.city(levels=100, heavy=29))        # a share, but under 30 levels
        self.assertIn("te_sp_industry", self.city(levels=1000, heavy=226, state={"te_sp_industry": 1}))   # kept to 225
        self.assertNotIn("te_sp_industry", self.city(levels=1000, heavy=224, state={"te_sp_industry": 1}))
        self.assertIn("te_sp_resort", self.city(levels=1000, tour=20))
        self.assertNotIn("te_sp_resort", self.city(levels=1000, tour=19))
        self.assertNotIn("te_sp_resort", self.city(levels=100, tour=9))            # under ten levels
        self.assertNotIn("te_sp_resort", self.city(levels=1000, tour=17, state={"te_sp_resort": 1}))

    def test_a_boomtown_needs_several_years_of_growth(self):
        self.assertNotIn("te_sp_boom", self.years([0.06]))                 # one good year: 1.2% smoothed
        self.assertNotIn("te_sp_boom", self.years([0.06] * 3))             # three: 2.9%
        self.assertNotIn("te_sp_boom", self.years([0.05] * 4))             # 5% a year: 2.95% after four
        self.assertIn("te_sp_boom", self.years([0.05] * 5))                # and 3.4% after five
        self.assertNotIn("te_sp_boom", self.years([0.02] * 20))            # steady 2% never gets there
        # a single year's leap counts as a tenth at most: a migration wave is not a trend
        self.assertAlmostEqual(self.years([3.0])["te_sp_growth"], 0.02, places=4)
        # a town is no boomtown however it grows
        self.assertNotIn("te_sp_boom", self.years([0.05] * 6, size=1))

    def test_a_boomtown_cools_and_a_city_declines(self):
        boom = self.years([0.05] * 6)
        self.assertIn("te_sp_boom", boom)
        self.assertNotIn("te_sp_boom", self.years([0.05] * 6 + [0.0] * 3))
        self.assertIn("te_sp_decline", self.years([-0.02] * 4))
        self.assertNotIn("te_sp_decline", self.years([-0.005] * 20))
        self.assertNotIn("te_sp_decline", self.years([-0.02] * 4 + [0.01] * 3))
        both = self.years([0.05] * 6 + [-0.03] * 8)
        self.assertEqual({"te_sp_boom" in both, "te_sp_decline" in both}, {False, True})

    def test_a_year_of_border_changes_is_left_out_of_the_growth(self):
        before = self.city(walk=1_020_000, prev=1_000_000, prov=10)
        after = self.city(walk=2_000_000, prev=1_020_000, prov=14,
                          state={"te_sp_growth": before["te_sp_growth"], "te_sp_prov": before["te_sp_prov"]})
        self.assertEqual(after["te_sp_growth"], before["te_sp_growth"])
        self.assertEqual(after["te_sp_prov"], 14)
        # and with no walk there is no growth at all
        self.assertNotIn("te_sp_growth", self.city())

    def test_a_divided_city_is_a_very_unequal_metropolis(self):
        self.assertIn("te_sp_divided", self.city(size=3, gini=0.86))
        self.assertNotIn("te_sp_divided", self.city(size=3, gini=0.84))
        self.assertNotIn("te_sp_divided", self.city(size=2, gini=0.95))
        self.assertNotIn("te_sp_divided", self.city(size=3))               # no census figure, no tag
        self.assertIn("te_sp_divided", self.city(size=3, gini=0.84, state={"te_sp_divided": 1}))
        self.assertNotIn("te_sp_divided", self.city(size=3, gini=0.82, state={"te_sp_divided": 1}))
        self.assertNotIn("te_sp_divided", self.city(size=2, gini=0.9, state={"te_sp_divided": 1}))

    def test_the_city_pictures_read_the_tags_the_pass_stores(self):
        effects = EFFECTS.read_text(encoding="utf-8-sig")
        for name in ("boomtown", "declining", "divided", "industry", "resort"):
            (line,), _digit = registry.CHARACTERS[name]
            tag = line.removeprefix("has_variable = ")
            self.assertIn(f"set_variable = {{ name = {tag} value = 1 }}", effects)
            self.assertIn(f"remove_variable = {tag}", effects)
        # the design's order of precedence (section 7)
        order = ["housing_blocks", "boomtown", "declining", "divided", "smog", "industry", "resort"]
        digits = [registry.CHARACTERS[name][1] for name in order]
        self.assertEqual(digits, sorted(digits, reverse=True))

    def prosperity(self, rung, sol, expected=None, state=None):
        """The means (1 poor, 2 ordinary, 3 affluent) and whether run-down, after a pass in a state of that
        standard of living whose owner is on that city rung."""
        eng = _Engine({"te_state_picture_city_rung": float(rung), "average_sol": float(sol),
                       "average_expected_sol": float(sol if expected is None else expected)},
                      effects=_raw_blocks([EFFECTS]))
        eng.values.update(_raw_blocks([VALUES]))
        eng.vars.update({k: float(v) for k, v in (state or {}).items()})
        eng.call("te_state_picture_refresh_prosperity")
        return eng.vars.get("te_sp_means", 2.0), "te_sp_rundown" in eng.vars

    def test_means_follow_the_owners_floors_by_rung(self):
        # the owner's first-pass figures (2026-11-11), at the era of each city rung
        floors = {1: (12, 20), 2: (14, 22), 3: (18, 28), 4: (26, 36), 5: (35, 45)}
        for rung, (poor, rich) in floors.items():
            with self.subTest(rung=rung):
                self.assertEqual(self.prosperity(rung, poor - 0.1)[0], 1)
                self.assertEqual(self.prosperity(rung, poor)[0], 2)
                self.assertEqual(self.prosperity(rung, rich - 0.1)[0], 2)
                self.assertEqual(self.prosperity(rung, rich)[0], 3)
        # the same standard of living is ordinary in 1930 and poor in 1990
        self.assertEqual((self.prosperity(1, 15)[0], self.prosperity(3, 15)[0]), (2, 1))
        # before the first city technology there is nothing to tag, and a tag is taken away
        self.assertEqual(self.prosperity(0, 3, expected=30), (2, False))
        self.assertEqual(self.prosperity(0, 3, expected=30, state={"te_sp_means": 1, "te_sp_rundown": 1}), (2, False))

    def test_a_means_tag_is_kept_half_a_point_past_its_floor(self):
        self.assertEqual(self.prosperity(1, 12.3, state={"te_sp_means": 1})[0], 1)     # poor until 12.5
        self.assertEqual(self.prosperity(1, 12.5, state={"te_sp_means": 1})[0], 2)
        self.assertEqual(self.prosperity(1, 19.6, state={"te_sp_means": 3})[0], 3)     # affluent down to 19.5
        self.assertEqual(self.prosperity(1, 19.4, state={"te_sp_means": 3})[0], 2)
        self.assertEqual(self.prosperity(1, 25, state={"te_sp_means": 1})[0], 3)       # straight from poor to rich

    def test_run_down_is_the_standard_of_living_against_expectations(self):
        self.assertFalse(self.prosperity(3, 20, expected=21.9)[1])
        self.assertTrue(self.prosperity(3, 20, expected=22)[1])
        self.assertTrue(self.prosperity(3, 20, expected=21.6, state={"te_sp_rundown": 1})[1])   # kept to 1.5 under
        self.assertFalse(self.prosperity(3, 20, expected=21.4, state={"te_sp_rundown": 1})[1])
        # the owner's split: a poor state that never had more is poor and kept; a rich one in decline is
        # affluent and run-down
        self.assertEqual(self.prosperity(3, 10, expected=10), (1, False))
        self.assertEqual(self.prosperity(3, 30, expected=34), (3, True))

    def test_a_reword_reaches_the_prompt_of_a_table_variant(self):
        # a reword of a field its variant's sentence does not use, or of a pilot picture written by
        # hand, would change nothing and say nothing
        r = registry
        fields = set(r._REGION_FIELDS) | set(r._RUNG_FIELDS)
        self.assertEqual(len(r.VARIANT_REGION["european"]), len(r._REGION_FIELDS))
        self.assertEqual(len(r.VARIANT_RUNG[1]), len(r._RUNG_FIELDS))
        for (region, rung, variant), words in r.VARIANT_REWORD.items():
            key = f"urban_{region}_{rung}_{variant}"
            with self.subTest(key):
                entry = r.DRAFTS.get(key) or r.PICTURES[key]
                self.assertLessEqual(set(words), fields)
                self.assertTrue(words)
                self.assertEqual(entry["prompt"],
                                 r.variant_prompt(region, rung, variant).format(
                                     when=r.CITY_LADDER[rung][1], landmark=r.CITY_LANDMARK[region]))
                for text in words.values():
                    self.assertIn(text, entry["prompt"])

    def test_the_variants_take_their_axis_from_their_name(self):
        r = registry
        variants = {k: d for k, d in r.DRAFTS.items() if d["family"] == "variant"}
        self.assertEqual(len(variants) + len(r.VARIANT_PICKS), 223)
        for key, d in variants.items():
            with self.subTest(key):
                self.assertEqual(key, f"urban_{d['region']}_{d['rung']}_{d['variant']}")
                axis = r.VARIANT_AXIS[d["variant"]]
                self.assertIn(d["variant"], {"size": r.SIZES, "means": r.MEANS, "upkeep": r.UPKEEP}[axis])
                self.assertIn(r.CITY_LANDMARK[d["region"]], d["prompt"])
                self.assertFalse(d["variant"] == "megacity" and d["rung"] < 3)
        # run-down over poor or affluent over any size over the plain street, all under a character
        self.assertLess(9 * r.W_SIZE + 9 * r.W_REGION, r.W_MEANS)
        self.assertLess(9 * r.W_MEANS + 9 * r.W_SIZE + 9 * r.W_REGION, r.W_UPKEEP)
        self.assertLess(9 * r.W_UPKEEP + 9 * r.W_MEANS + 9 * r.W_SIZE + 9 * r.W_REGION, r.W_CHAR)
        effects = EFFECTS.read_text(encoding="utf-8-sig")
        for tag in ("te_sp_means", "te_sp_rundown"):
            self.assertIn(f"name = {tag} value", effects)
            self.assertIn(f"remove_variable = {tag}", effects)

    def test_oil_country_is_a_share_of_the_states_levels(self):
        # the owner's case: many rigs beside a great city is not an oil state
        self.assertEqual(self.land(4499, oil=100), set())
        self.assertEqual(self.land(265, oil=60), {"te_sp_oil"})
        self.assertEqual(self.land(200, oil=10), {"te_sp_oil"})        # 5%, ten levels: just in
        self.assertEqual(self.land(100, oil=9), set())                 # a share, but under ten levels
        self.assertEqual(self.land(1000, oil=49), set())               # ten levels, but under the share

    def test_a_tag_is_kept_until_a_tenth_below_its_floor(self):
        self.assertEqual(self.land(1000, oil=46, tagged=["te_sp_oil"]), {"te_sp_oil"})   # floor 50, kept to 45
        self.assertEqual(self.land(1000, oil=44, tagged=["te_sp_oil"]), set())
        self.assertEqual(self.land(100, oil=9, tagged=["te_sp_oil"]), {"te_sp_oil"})     # nine levels keeps it
        self.assertEqual(self.land(100, oil=8, tagged=["te_sp_oil"]), set())
        self.assertEqual(self.land(100, mines=40, coal=19, tagged=["te_sp_coal"]), {"te_sp_coal"})  # floor 20, kept to 18
        self.assertEqual(self.land(100, mines=40, coal=17, tagged=["te_sp_coal"]), set())

    def test_a_colliery_is_coal_as_the_larger_part_of_the_mines(self):
        self.assertEqual(self.land(300, mines=40, coal=25), {"te_sp_coal"})
        self.assertEqual(self.land(300, mines=60, coal=25), set())     # more iron than coal
        self.assertEqual(self.land(300, mines=9, coal=9), set())       # all coal, but under ten levels
        self.assertEqual(self.land(300, oil=30, mines=40, coal=25), {"te_sp_oil", "te_sp_coal"})

    def test_the_walk_counts_every_building_but_subsistence_once(self):
        body = _raw_blocks([EFFECTS])["te_state_picture_land_sums"]
        self.assertEqual(body.count("every_scope_building"), 1)
        self.assertIn("limit = { is_subsistence_building = no }", body)
        for line in ("change_local_variable = { name = te_sp_all add = level }",
                     "limit = { is_building_type = building_oil_rig }",
                     "limit = { is_building_group = bg_mining }",
                     "limit = { is_building_type = building_coal_mine }"):
            self.assertIn(line, body)

    def test_the_pictures_read_the_tags_the_pass_stores(self):
        effects = EFFECTS.read_text(encoding="utf-8-sig")
        for tag in ("te_sp_oil", "te_sp_coal"):
            self.assertIn(f"set_variable = {{ name = {tag} value = 1 }}", effects)
            self.assertIn(f"remove_variable = {tag}", effects)
        self.assertEqual(registry.WAVE3_WIRING["oil_1"]["where"], ["has_variable = te_sp_oil"])
        self.assertEqual(registry.SCALES["colliery"][0], ["has_variable = te_sp_coal"])
        generated = GENERATED.read_text(encoding="utf-8-sig")
        self.assertIn("has_variable = te_sp_oil", generated)
        self.assertIn("has_variable = te_sp_coal", generated)
        self.assertNotIn("building_oil_rig", generated)

    def test_the_pass_is_on_the_yearly_state_pulse(self):
        text = ON_ACTIONS.read_text(encoding="utf-8-sig")
        self.assertRegex(text, r"on_yearly_pulse_state = \{\s*on_actions = \{\s*te_state_picture_yearly_on_action")
        self.assertRegex(text, r"te_state_picture_yearly_on_action = \{\s*effect = \{\s*te_state_picture_refresh = yes")

    def test_the_console_events_run_the_pass_and_force_a_metropolis(self):
        text = DEBUG_EVENTS.read_text(encoding="utf-8-sig")
        events = dict(re.findall(r"^(te_debug_state_picture\.\d+) = \{.*?\n(.*?)^\}", text, re.M | re.S))
        self.assertEqual(sorted(events), ["te_debug_state_picture.1", "te_debug_state_picture.2"])
        for body in events.values():
            self.assertIn("hidden = yes", body)
        # .1: the same pass the yearly pulse runs, in every state, not a copy of its logic
        self.assertRegex(events["te_debug_state_picture.1"], r"every_state = \{\s*te_state_picture_refresh = yes\s*\}")
        # .2: the capital at the metropolis picture's own floor (SIZES: var:te_sp_size >= 3)
        self.assertRegex(events["te_debug_state_picture.2"],
                         r"capital = \{\s*set_variable = \{ name = te_sp_size value = 3 \}")
        self.assertEqual(registry.SIZES["metropolis"][0][1], "var:te_sp_size >= 3")
        # .1's line for a state carries the tags the worked-land pictures read
        for value in ("te_state_picture_oil_shown", "te_state_picture_coal_shown"):
            self.assertIn(f"THIS.ScriptValue('{value}')", events["te_debug_state_picture.1"])
            self.assertIn(value, _raw_blocks([VALUES]))
        # a forced size is undone by the next pass: 200,000 people make a city, not a metropolis
        self.assertEqual(self.refresh(400_000, share=50, size=3), 2)

    def test_the_self_check_can_fail(self):
        # OK only where the largest city fits inside its state; a size of 3 already means a metropolis's people
        text = EFFECTS.read_text(encoding="utf-8-sig")
        ok = text.index('debug_log = "TE_SELF_CHECK OK state_picture_size')
        gate = text.rindex("limit = {", 0, ok)
        self.assertIn("te_state_picture_city_people <= te_state_picture_state_people", text[gate:ok])
        self.assertIn('debug_log = "TE_SELF_CHECK BROKEN state_picture_size', text[ok:])
        self.assertIn("te_state_picture_state_people = { value = state_population }",
                      VALUES.read_text(encoding="utf-8-sig"))
        # no debug_log string takes .MakeScope after THIS (it drops the whole line)
        self.assertNotIn("THIS.MakeScope", text)

if __name__ == "__main__":
    unittest.main()
