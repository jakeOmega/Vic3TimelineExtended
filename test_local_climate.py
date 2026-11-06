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

VALUES = ("te_climate_has_record", "te_climate_summer_humidity", "te_climate_winter_mean", "te_climate_aridity",
          "te_climate_malaria", "te_climate_latitude", "te_climate_hot_day", "te_climate_heat_index")
DEFAULTS = {"te_climate_has_record": 0, "te_climate_summer_humidity": 0, "te_climate_winter_mean": 15,
            "te_climate_aridity": 0, "te_climate_malaria": 0, "te_climate_latitude": 0, "te_climate_hot_day": 20,
            "te_climate_heat_index": 0}


def row(state="STATE_GEORGIA", summer=28, humidity=3, winter=8, aridity=0, malaria=2, latitude=32, hot_day=36.6,
        heat_index=30.2, source="KSVN:1km"):
    return gen.Row(state, "Savannah", summer, humidity, winter, aridity, malaria, latitude, hot_day, heat_index, source,
                   "x")


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
        self.assertIn("value = 36.6", block(text, "te_climate_hot_day"))
        self.assertIn("value = 30.2", block(text, "te_climate_heat_index"))
        self.assertIn("value = 8", block(text, "te_climate_winter_mean"))
        # The warmest month's mean stays in the CSV, for validation and the fill, but no script reads it.
        self.assertIsNone(block(text, "te_climate_summer_mean"))
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
        bad = [row(summer=46, hot_day=48), row(summer=-11, winter=-20), row(winter=31, summer=40, hot_day=42), row(winter=-51), row(summer=10, winter=12),
               row(humidity=4), row(aridity=3), row(malaria=3), row(latitude=91), row(humidity=-1),
               row(hot_day=53), row(hot_day=9, summer=5, winter=0, heat_index=8), row(heat_index=41, hot_day=45),
               row(heat_index=4), row(heat_index=37, hot_day=36.6), row(hot_day=27, summer=28, heat_index=26),
               row(source=""), row(source="KSVN"), row(source="nearby")]
        for r in bad:
            errs = self.errors([r])
            self.assertEqual(len(errs), 1, (r, errs))
            self.assertIn("STATE_GEORGIA", errs[0])

    def test_heat_sources(self):
        """A heat figure comes from a station (code:km), the fit from the record's own fields, or another
        region's station (analog:STATE_X), so the next pass knows which rows are estimates."""
        for source in ("KSVN:1km", "WMO02484:2km", "fit", "KSVN:312km;fit_hot_day", "KSVN:14km;fit_index"):
            self.assertEqual(self.errors([row(source=source)]), [], source)
        for source in ("KSVN:1km;fit", "KSVN:1km;fit_hot_day;fit_index", "fit_index"):
            self.assertEqual(len(self.errors([row(source=source)])), 1, source)

    def test_analog_copies_its_source(self):
        """An analog row takes another region's station figures, so it must name a region with a row and match
        that row's heat figures (review of #1312)."""
        source = row(state="STATE_SAHARA")
        self.assertEqual(self.errors([source, row(source="analog:STATE_SAHARA")]), [])
        errs = self.errors([source, row(hot_day=37, source="analog:STATE_SAHARA")])
        self.assertEqual(len(errs), 1, errs)
        self.assertIn("STATE_GEORGIA", errs[0])
        self.assertEqual(len(self.errors([row(source="analog:STATE_SAHARA")])), 1)

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


    def test_desert_trait_exceptions(self):
        """A desert-trait region whose people live by a great river or outside the desert may read ample water;
        each one is named, with its reason, in DESERT_TRAIT_EXCEPTIONS."""
        traits = {s: {"state_trait_sahara_desert"} for s in ("STATE_EGYPTIAN_DESERT", "STATE_SAHARA")}
        regions = set(traits)
        self.assertEqual(gen.validate([row("STATE_EGYPTIAN_DESERT", aridity=0, malaria=0)], regions, traits), [])
        self.assertEqual(len(gen.validate([row("STATE_SAHARA", aridity=0, malaria=0)], regions, traits)), 1)
        self.assertEqual(set(gen.DESERT_TRAIT_EXCEPTIONS),
                         {"STATE_EGYPTIAN_DESERT", "STATE_WESTERN_AUSTRALIA", "STATE_NORTHERN_TERRITORY"})
        for state, reason in gen.DESERT_TRAIT_EXCEPTIONS.items():
            self.assertTrue(reason, state)

class ColdBand(unittest.TestCase):
    """The record's winter against vanilla 1.15's cold at the peak of winter (max_cold_effect; #1407)."""

    def test_each_band(self):
        cases = [
            (row("STATE_A", winter=1), 0.75, True),     # above freezing under severe cold
            (row("STATE_A", winter=0), 0.75, False),
            (row("STATE_A", winter=4), 0.5, True),      # milder than London's under moderate cold
            (row("STATE_A", winter=3), 0.74, False),
            (row("STATE_A", winter=-10), 0.49, True),   # a hard winter where vanilla's cold isn't moderate
            (row("STATE_A", winter=-10), 0.5, False),
            (row("STATE_A", winter=-9), 0.0, False),
        ]
        for r, cold, flagged in cases:
            with self.subTest(winter=r.winter_mean_c, cold=cold):
                self.assertEqual(r.state in gen.cold_band_flags([r], {"STATE_A": cold}), flagged)

    def test_a_region_with_no_cold_reads_zero(self):
        self.assertIn("STATE_A", gen.cold_band_flags([row("STATE_A", winter=-12)], {}))

    def test_region_cold_reads_the_map(self):
        cold = gen.region_cold()
        self.assertEqual(set(cold), gen.land_regions())
        self.assertGreater(sum(1 for c in cold.values() if c > 0), 500)
        self.assertEqual(cold["STATE_NORTH_RHINE"], 0.0)   # vanilla's one cold-wintered gap

    def test_the_committed_record_agrees_but_for_its_listed_exceptions(self):
        flags = gen.cold_band_flags(gen.load_rows(), gen.region_cold())
        self.assertEqual({s: w for s, w in flags.items() if s not in gen.COLD_BAND_EXCEPTIONS}, {},
                         "a row disagrees with vanilla's cold: fix the row, or list it with its reason")
        self.assertEqual(sorted(set(gen.COLD_BAND_EXCEPTIONS) - set(flags)), [], "a stale exception")
        for state, reason in gen.COLD_BAND_EXCEPTIONS.items():
            self.assertTrue(reason, state)


class Committed(unittest.TestCase):
    def test_csv_rows_validate(self):
        self.assertEqual(gen.validate(gen.load_rows(), gen.land_regions(), gen.region_traits()), [])

    def test_every_land_region_has_a_row(self):
        self.assertEqual({r.state for r in gen.load_rows()}, gen.land_regions())

    def test_rows_follow_map_order(self):
        """Rows sit in map_data file order, then order within the file, so a diff reads by region."""
        order = gen.region_order()
        states = [r.state for r in gen.load_rows()]
        self.assertEqual(states, [s for s in order if s in set(states)])

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


PANEL = ROOT / "gui" / "states_panel.gui"
WIDGETS = ROOT / "gui" / "te_state_panel_widgets.gui"
TILE_KEYS = ("TE_STATE_CLIMATE_STATUS", "TE_STATE_CLIMATE_TT", "TE_STATE_CLIMATE_ROW_HOT_DAY",
             "TE_STATE_CLIMATE_ROW_HUMIDITY", "TE_STATE_CLIMATE_ROW_WINTER", "TE_STATE_CLIMATE_ROW_WATER",
             "TE_STATE_CLIMATE_ROW_MALARIA", "TE_STATE_CLIMATE_NO_DATA", "te_state_climate_hot_day_value",
             "te_state_climate_winter_value", "te_state_climate_hot_day_tt", "te_state_climate_humidity_tt",
             "te_state_climate_winter_tt", "te_state_climate_water_tt", "te_state_climate_malaria_tt",
             "TE_CLIMATE_HUMIDITY_0", "TE_CLIMATE_HUMIDITY_1", "TE_CLIMATE_HUMIDITY_2", "TE_CLIMATE_HUMIDITY_3",
             "TE_CLIMATE_WATER_0", "TE_CLIMATE_WATER_1", "TE_CLIMATE_WATER_2",
             "TE_CLIMATE_MALARIA_0", "TE_CLIMATE_MALARIA_1", "TE_CLIMATE_MALARIA_2",
             "concept_local_climate", "concept_local_climate_desc")


def loc_value(key):
    """The text of an English loc key, or None."""
    for path in (ROOT / "localization" / "english").glob("*.yml"):
        m = re.search(rf'(?m)^ {re.escape(key)}:\d* "(.*)"\s*$', path.read_text(encoding="utf-8-sig"))
        if m:
            return m.group(1)
    return None


def gui_type(text, name):
    m = re.search(rf"(?m)^\s*type {re.escape(name)} = \w+ \{{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        if c == "#":
            i = text.index("\n", i)
            continue
        depth += {"{": 1, "}": -1}.get(c, 0)
        i += 1
    return text[m.end():i - 1]


class Tile(unittest.TestCase):
    def test_tile_instance_in_status_grid(self):
        panel = PANEL.read_text(encoding="utf-8-sig")
        m = re.search(r'text = "TE_STATE_CLIMATE_STATUS"', panel)
        self.assertIsNotNone(m)
        self.assertIn("te_state_climate_tile = {}", panel[m.end():m.end() + 400])

    def test_tile_reads_the_record(self):
        body = gui_type(WIDGETS.read_text(encoding="utf-8-sig"), "te_state_climate_tile")
        self.assertIsNotNone(body)
        for value in ("te_climate_summer_humidity", "te_climate_aridity", "te_climate_malaria",
                      "te_climate_has_record"):
            self.assertIn(f"ScriptValue('{value}')", body, value)
        for key in ("te_state_climate_hot_day_value", "te_state_climate_winter_value", "TE_STATE_CLIMATE_NO_DATA"):
            self.assertIn(key, body, key)
        # The rows show the record with the warming against today's normals (te_climate_*_eff,
        # test_local_climate_comfort.py's test_seasons_show_the_climate_now); the hover gives the normal.
        self.assertIn("te_climate_hot_day", loc_value("te_state_climate_hot_day_value"))
        self.assertIn("te_climate_winter", loc_value("te_state_climate_winter_value"))

    def test_word_chains_pick_each_class(self):
        """Each word row's nested SelectLocalization maps class n to its own key: thresholds run down from the
        top class, each GreaterThan n picking _(n+1), and _0 is the last fallback."""
        body = gui_type(WIDGETS.read_text(encoding="utf-8-sig"), "te_state_climate_tile")
        chains = {"te_climate_summer_humidity": ("TE_CLIMATE_HUMIDITY", 3), "te_climate_aridity": ("TE_CLIMATE_WATER", 2),
                  "te_climate_malaria": ("TE_CLIMATE_MALARIA", 2)}
        for value, (prefix, top) in chains.items():
            line = next(x for x in body.splitlines() if "raw_text" in x and f"'{value}'" in x)
            picks = re.findall(rf"ScriptValue\('{value}'\), '\(CFixedPoint\)(\d)'\), '({prefix}_\d)'", line)
            self.assertEqual(picks, [(str(n), f"{prefix}_{n + 1}") for n in range(top - 1, -1, -1)], value)
            self.assertTrue(line.rstrip().endswith(f"'{prefix}_0'" + ")" * top + ']#!"'), value)

    def test_rows_wait_for_a_record(self):
        """Every reading row hides when the region has no row, so the no-data line shows alone."""
        body = gui_type(WIDGETS.read_text(encoding="utf-8-sig"), "te_state_climate_tile")
        rows = body.split("te_state_climate_row = {")[1:]
        self.assertEqual(len(rows), 9)  # five readings and Comfort's four (cost, bonus, none, pending)
        for row in rows:
            self.assertIn("row_visible", row)
            self.assertIn("ScriptValue('te_climate_has_record'), '(CFixedPoint)0')", row.split("row_tooltip")[0])

    def test_tile_loc_exists(self):
        for key in TILE_KEYS:
            text = loc_value(key)
            self.assertIsNotNone(text, key)
            self.assertNotRegex(re.sub(r"Local Climate|concept_local_climate", "", text), r"\bClimate\b", key)

    def test_concept_defined(self):
        concepts = (ROOT / "common" / "game_concepts" / "extra_concepts.txt").read_text(encoding="utf-8-sig")
        self.assertRegex(concepts, r"(?m)^concept_local_climate = \{")


if __name__ == "__main__":
    unittest.main()
