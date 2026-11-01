"""Local Climate: the climate record (docs/superpowers/specs/2026-11-01-local-climate-design.md § 4).

Every land state region has one row in scripts/generators/data/local_climate.csv, and
scripts/generators/gen_local_climate.py turns the rows into state-scope script values keyed on
state_region (common/script_values/local_climate_generated.txt).

    python3 test_local_climate.py
"""
import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GENERATED = ROOT / "common" / "script_values" / "local_climate_generated.txt"

_spec = importlib.util.spec_from_file_location(
    "gen_local_climate", ROOT / "scripts" / "generators" / "gen_local_climate.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

VALUES = ("te_climate_has_record", "te_climate_summer_mean", "te_climate_summer_humidity",
          "te_climate_winter_mean", "te_climate_aridity", "te_climate_malaria", "te_climate_latitude")
DEFAULTS = {"te_climate_has_record": 0, "te_climate_summer_mean": 15, "te_climate_summer_humidity": 0,
            "te_climate_winter_mean": 15, "te_climate_aridity": 0, "te_climate_malaria": 0,
            "te_climate_latitude": 0}


def row(state="STATE_GEORGIA", summer=28, humidity=3, winter=8, aridity=0, malaria=2, latitude=32):
    return gen.Row(state, "Savannah", summer, humidity, winter, aridity, malaria, latitude, "x")


def block(text, name):
    """The body of the top-level block `name = {`, braces balanced, or None."""
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class Render(unittest.TestCase):
    def test_render_chains_on_state_region(self):
        text = gen.render([row()])
        for name in VALUES:
            body = block(text, name)
            self.assertIsNotNone(body, name)
            self.assertIn("limit = { state_region = s:STATE_GEORGIA }", body, name)
        self.assertIn("value = 28", block(text, "te_climate_summer_mean"))
        self.assertIn("value = 8", block(text, "te_climate_winter_mean"))
        self.assertIn("value = 1", block(text, "te_climate_has_record"))

    def test_render_negative_values(self):
        text = gen.render([row("STATE_YAKUTSK", 19, 1, -38, 0, 0, 62)])
        self.assertIn("value = -38", block(text, "te_climate_winter_mean"))

    def test_missing_row_is_neutral(self):
        """A region with no row reads the neutral default: the value's first line, before any branch."""
        text = gen.render([row()])
        for name, default in DEFAULTS.items():
            first = block(text, name).strip().splitlines()[0].strip()
            self.assertEqual(first, f"value = {default}", name)


class Validate(unittest.TestCase):
    REGIONS = {"STATE_GEORGIA", "STATE_SAHARA", "STATE_ZANZIBAR"}

    def errors(self, rows, traits=None):
        return gen.validate(rows, self.REGIONS, traits or {})

    def test_valid_row_passes(self):
        self.assertEqual(self.errors([row()]), [])

    def test_validate_ranges(self):
        bad = [row(summer=46), row(summer=-11, winter=-20), row(winter=31, summer=40), row(winter=-51), row(summer=10, winter=12),
               row(humidity=4), row(aridity=3), row(malaria=3), row(latitude=91), row(humidity=-1)]
        for r in bad:
            errs = self.errors([r])
            self.assertEqual(len(errs), 1, (r, errs))
            self.assertIn("STATE_GEORGIA", errs[0])

    def test_validate_unknown_and_duplicate(self):
        self.assertEqual(len(self.errors([row("STATE_NOWHERE")])), 1)
        errs = self.errors([row(), row()])
        self.assertEqual(len(errs), 1)
        self.assertIn("duplicate", errs[0])

    def test_validate_vanilla_traits(self):
        traits = {"STATE_ZANZIBAR": {"state_trait_malaria"}, "STATE_SAHARA": {"state_trait_sahara_desert"},
                  "STATE_GEORGIA": {"state_trait_severe_malaria"}}
        self.assertEqual(len(self.errors([row("STATE_ZANZIBAR", malaria=0)], traits)), 1)
        self.assertEqual(self.errors([row("STATE_ZANZIBAR", malaria=1)], traits), [])
        self.assertEqual(len(self.errors([row(malaria=1)], traits)), 1)
        self.assertEqual(self.errors([row(malaria=2)], traits), [])
        self.assertEqual(len(self.errors([row("STATE_SAHARA", aridity=0, malaria=0)], traits)), 1)
        self.assertEqual(self.errors([row("STATE_SAHARA", aridity=1, malaria=0)], traits), [])


class Committed(unittest.TestCase):
    def test_csv_rows_validate(self):
        self.assertEqual(gen.validate(gen.load_rows(), gen.land_regions(), gen.region_traits()), [])

    def test_land_regions_skip_seas(self):
        regions = gen.land_regions()
        self.assertIn("STATE_GEORGIA", regions)
        self.assertGreater(len(regions), 600)
        seas = re.findall(r"(?m)^(STATE_\w+)\s*=\s*\{",
                          (ROOT / "map_data" / "state_regions" / "99_seas.txt").read_text(encoding="utf-8-sig"))
        self.assertTrue(seas)
        self.assertFalse(regions & set(seas))

    def test_region_traits_read_first_state_of_a_file(self):
        """The first state of each file sits after the BOM; it must still be read."""
        traits = gen.region_traits()
        self.assertIn("state_trait_sahara_desert", traits["STATE_SAHARA"])
        self.assertTrue(any("state_trait_arabian_desert" in t for t in traits.values()))

    def test_generated_file_is_current(self):
        self.assertEqual(GENERATED.read_text(encoding="utf-8-sig"), gen.render(gen.load_rows()))

    def test_generated_file_bom(self):
        raw = GENERATED.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))
        self.assertTrue(raw[3:].decode("utf-8").startswith(
            "# AUTO-GENERATED by scripts/generators/gen_local_climate.py — do not edit manually."))


if __name__ == "__main__":
    unittest.main()
