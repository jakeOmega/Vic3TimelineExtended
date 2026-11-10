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
ON_ACTIONS = ROOT / "common" / "on_actions" / "te_state_picture_on_actions.txt"
VANILLA_TERRAINS = ROOT / "vanilla_parsed" / "common" / "terrains.json"
VANILLA_TECHS = ROOT / "vanilla_parsed" / "common" / "technologies.json"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


registry = _load("state_picture_registry", REGISTRY_PATH)
generator = _load("gen_state_pictures", GENERATOR_PATH)


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
                self.assertTrue(p["region"] is None or p["region"] in registry.REGIONS)
                self.assertTrue(p["size"] is None or p["size"] in registry.SIZES)
                # the engine rejects an entry without an effect; a vanilla entity is known to exist
                self.assertIn(p["effect"], effects)
                self.assertTrue(p["prompt"].strip())

    def test_the_port_picture_needs_a_port(self):
        # vanilla's docks terrain prevails in every one-province state and shows its dry plain where there is no port
        for key, p in registry.PICTURES.items():
            if "docks" in p["terrain"]:
                with self.subTest(key):
                    self.assertIn("has_building = building_port", p.get("where", []))
                    self.assertIn("has_building = building_port", generator.conditions(key))

    def test_no_two_pictures_of_a_terrain_can_tie(self):
        # the highest weight wins; two families can hold the same state (Japan lies inside East Asia), so no two
        # pictures of a terrain may weigh the same, whatever their regions
        seen = {}
        for key, p in registry.PICTURES.items():
            for terrain in p["terrain"]:
                spot = (terrain, registry.weight(key))
                self.assertNotIn(spot, seen, f"{key} and {seen.get(spot)} weigh the same in {terrain}")
                seen[spot] = key

    def test_every_region_family_has_its_own_digit(self):
        digits = [digit for _lines, digit in registry.REGIONS.values()]
        self.assertEqual(len(set(digits)), len(digits))
        self.assertTrue(all(1 <= d <= 9 for d in digits))
        for name, (lines, _digit) in registry.REGIONS.items():
            with self.subTest(name):
                self.assertTrue(lines)
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


class TestYearlyPass(unittest.TestCase):
    """te_state_picture_refresh: the size its people make a state, kept until it falls a tenth below the floor."""

    def refresh(self, urban, share=None, size=None):
        eng = _Engine({}, effects={**_raw_blocks([EFFECTS]), "te_state_picture_selfcheck": ""})
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

    def test_the_pass_is_on_the_yearly_state_pulse(self):
        text = ON_ACTIONS.read_text(encoding="utf-8-sig")
        self.assertRegex(text, r"on_yearly_pulse_state = \{\s*on_actions = \{\s*te_state_picture_yearly_on_action")
        self.assertRegex(text, r"te_state_picture_yearly_on_action = \{\s*effect = \{\s*te_state_picture_refresh = yes")

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
