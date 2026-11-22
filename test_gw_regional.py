"""Regional Climate Warming (#1681): the tropics take more of warming's harm, the high latitudes less.

Climate Warming (global_warming) is one modifier for the world. A state between the tropics also carries
global_warming_tropics, and one 55 degrees or more from the equator global_warming_high_latitudes, on top of it
and at the same scale, refreshed from the monthly state pulse (spec:
docs/superpowers/specs/2026-11-13-regional-climate-warming-design.md). The engine notices none of the ways this
can come apart: a band modifier re-added without its removal stacks, a multiplier read from a removed variable
reads 0, a mortality line without its Causes of Death tag drops out of the census, a wrong threshold moves
England into the far north. This pins the lines, the refresh and the text.

Run: python3 -m pytest test_gw_regional.py -q
"""

import csv
import re
import unittest
from pathlib import Path

from test_tax_code_rule import load

ROOT = Path(__file__).resolve().parent
MODIFIERS = "common/static_modifiers/extra_modifiers.txt"
VALUES = "common/script_values/global_warming_regional_values.txt"
EFFECTS = "common/scripted_effects/global_warming_regional_effects.txt"
ON_ACTIONS = "common/on_actions/global_warming_regional_on_actions.txt"
EXTRA_ON_ACTIONS = "common/on_actions/extra_on_actions.txt"
CLIMATE_CSV = "scripts/generators/data/local_climate.csv"
BANDS = ("global_warming_tropics", "global_warming_high_latitudes")

# Spec § 4: each band's lines, per degree, on top of global_warming.
TROPICS = {
    "state_mortality_mult": 0.025,
    "state_death_cause_chr_mult": 0.025,
    "state_standard_of_living_add": -0.5,
    "building_group_bg_agriculture_throughput_add": -0.05,
    "building_group_bg_plantations_throughput_add": -0.05,
    "state_harvest_condition_heatwave_impact_mult": 0.25,
    "state_harvest_condition_heatwave_duration_mult": 0.25,
}
HIGH_LATITUDES = {
    "state_mortality_mult": -0.03,
    "state_death_cause_chr_mult": -0.03,
    "state_standard_of_living_add": 0.5,
    "building_group_bg_agriculture_throughput_add": 0.145,
    "state_harvest_condition_frost_impact_mult": -0.15,
    "state_harvest_condition_frost_duration_mult": -0.15,
    "state_harvest_condition_heatwave_impact_mult": -0.25,
    "state_harvest_condition_heatwave_duration_mult": -0.25,
    "state_harvest_condition_wildfire_impact_mult": 0.25,
}


def _text(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")


def _squash(text):
    return " ".join(re.sub(r"#[^\n]*", "", text).split())


def _loc(key):
    for path in sorted((ROOT / "localization/english").glob("*_l_english.yml")):
        m = re.search(rf'(?m)^ {re.escape(key)}:\d+ "(.*)"', path.read_text(encoding="utf-8-sig"))
        if m:
            return m.group(1)
    raise AssertionError(f"no loc for {key}")


def _lines(name):
    body = load(MODIFIERS)[name]
    return {k: float(v) for k, v in body.items() if k != "icon"}


class ModifierTest(unittest.TestCase):
    def test_the_tropics_lines(self):
        self.assertEqual(_lines("global_warming_tropics"), TROPICS)

    def test_the_high_latitudes_lines(self):
        self.assertEqual(_lines("global_warming_high_latitudes"), HIGH_LATITUDES)

    def test_each_mortality_line_has_its_death_tag_at_the_same_value(self):
        for name in ("global_warming",) + BANDS:
            with self.subTest(name):
                lines = _lines(name)
                self.assertEqual(lines["state_death_cause_chr_mult"], lines["state_mortality_mult"])

    def test_the_death_tags_file_both_under_chronic_illness_beside_climate_warming(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
        import demographics_params as P
        for name in BANDS:
            self.assertIn(name, P.DEATH_CAUSE_TAGS["chr"])

    def test_the_high_latitudes_gain_a_little_from_their_farms_and_the_tropics_lose_most(self):
        world = _lines("global_warming")
        farm = "building_group_bg_agriculture_throughput_add"
        # Climate Warming's -2.5% on every building reaches farms too (review of #1747: without it the
        # "gain" was -0.5% a degree).
        every = world["building_throughput_add"]
        high = world[farm] + every + HIGH_LATITUDES[farm]
        tropics = world[farm] + every + TROPICS[farm]
        self.assertAlmostEqual(high, 0.02)
        self.assertLessEqual(high, 0.025, "the gain stays modest at 4 C (spec § 4)")
        self.assertLess(tropics, world[farm])
        # Mortality stays a harm everywhere: the high latitudes take less of it, not none.
        mort = "state_mortality_mult"
        self.assertGreater(world[mort] + HIGH_LATITUDES[mort], 0)
        self.assertGreater(TROPICS[mort], 0)

    def test_global_warming_is_unchanged_by_the_bands(self):
        """The world modifier's readers (the Warming Penalty cell, UN adaptation aid, the World Climate self-check)
        stay right because Climate Warming itself keeps its lines (spec § 2, goal 2)."""
        world = _lines("global_warming")
        self.assertEqual(world["state_mortality_mult"], 0.05)
        self.assertEqual(world["state_standard_of_living_add"], -1.0)
        self.assertEqual(world["building_group_bg_agriculture_throughput_add"], -0.1)
        self.assertEqual(world["state_harvest_condition_wildfire_duration_mult"], 0.5)

    def test_on_no_country(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts" / "generators"))
        import gen_nation_tab
        src = (ROOT / "scripts/generators/gen_nation_tab.py").read_text(encoding="utf-8")
        for name in BANDS:
            self.assertIn(f'"{name}": "states"', src)
        self.assertTrue(gen_nation_tab)


class BandTest(unittest.TestCase):
    def setUp(self):
        self.values = load(VALUES)

    def test_the_high_latitudes_begin_at_55(self):
        self.assertEqual(self.values["gw_regional_high_latitude_min"], "55")

    def test_the_band_reads_in_tropics_first_then_the_records_latitude(self):
        body = _squash(_text(VALUES))
        band = re.search(r"gw_regional_band_value = \{(.*?)\} \} gw_regional_target", body).group(1)
        self.assertIn("if = { limit = { in_tropics = yes } value = 1 }", band)
        self.assertIn("else_if = { limit = { te_climate_abs_latitude >= gw_regional_high_latitude_min } value = 2",
                      band)

    def test_the_record_puts_the_boreal_north_in_the_band_and_england_out(self):
        rows = {r["state"]: int(r["latitude"]) for r in csv.DictReader(open(ROOT / CLIMATE_CSV, encoding="utf-8"))}
        threshold = int(self.values["gw_regional_high_latitude_min"])
        high = {s for s, lat in rows.items() if abs(lat) >= threshold}
        self.assertEqual(len(high), 64, "the spec's count of high-latitude regions (§ 3)")
        for state in ("STATE_SVEALAND", "STATE_MOSCOW", "STATE_ST_PETERSBURG", "STATE_YAKUTSK", "STATE_ICELAND"):
            if state in rows:
                self.assertIn(state, high)
        for state in ("STATE_HOME_COUNTIES", "STATE_BRANDENBURG", "STATE_KIEV", "STATE_ALBERTA"):
            self.assertNotIn(state, high)

    def test_the_target_is_climate_warmings_scale_once_the_world_entry_has_opened(self):
        """Climate Warming applies at the felt anomaly floored at 0 from the World Climate entry's opening at 0.1 C
        until the end of the game, under any mask; the bands apply at the same figure, not rounded and not cut off
        below 0.1 (review of #1747)."""
        body = _squash(_text(VALUES))
        target = re.search(r"gw_regional_target = \{(.*?)\} \} gw_regional_gap = ", body).group(1)
        self.assertEqual(target.strip(), "value = 0 if = { limit = { has_global_variable = gw_g_world_climate_open } "
                                         "value = temperature_anomaly_display min = 0")
        world = _squash(_text("common/journal_entries/je_world_climate.txt"))
        self.assertIn("value = { value = temperature_anomaly_display min = 0 }", world)
        self.assertIn("possible = { temperature_anomaly_display >= 0.1 }", world)
        pulse = _squash(_text(EXTRA_ON_ACTIONS))
        self.assertIn("if = { limit = { NOT = { has_global_variable = gw_g_world_climate_open } "
                      "gw_unmasked_temperature >= 0.1 } set_global_variable = gw_g_world_climate_open }", pulse)
        self.assertNotIn("remove_global_variable = gw_g_world_climate_open", pulse)

    def test_the_gap_is_zero_where_no_scale_was_applied(self):
        body = _squash(_text(VALUES))
        self.assertIn("gw_regional_gap = { value = 0 if = { limit = { has_variable = gw_regional_applied } "
                      "value = var:gw_regional_applied subtract = gw_regional_target } }", body)


class RefreshTest(unittest.TestCase):
    def setUp(self):
        self.effect = _squash(_text(EFFECTS))

    def test_both_come_off_before_either_goes_on(self):
        body = self.effect
        start = body.index("gw_regional_refresh_effect = {")
        refresh = body[start:body.index("gw_regional_selfcheck_effect = {")]
        removes = [refresh.index(f"remove_modifier_if_exists_effect = {{ MODIFIER = {n} }}") for n in BANDS]
        adds = [refresh.index(f"add_modifier = {{ name = {n} multiplier = var:gw_regional_applied }}") for n in BANDS]
        self.assertLess(max(removes), min(adds))
        self.assertLess(refresh.index("set_variable = { name = gw_regional_applied value = gw_regional_target }"),
                        min(adds))
        # The band is stored once; the multiplier's variable is never removed.
        self.assertIn("limit = { NOT = { has_variable = gw_regional_band } } set_variable = { name = "
                      "gw_regional_band value = gw_regional_band_value }", refresh)
        self.assertNotIn("remove_variable = gw_regional_applied", body)
        # The self-healing marker: set only when ROOT is the state, after the write.
        self.assertTrue(refresh.rstrip().endswith("if = { limit = { root ?= this } set_variable = gw_regional_rooted } }"),
                        refresh[-200:])

    def test_one_refresh_site(self):
        callers, adders = [], []
        for path in sorted((ROOT / "common").rglob("*.txt")) + sorted((ROOT / "events").rglob("*.txt")):
            text = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))
            if "gw_regional_refresh_effect = yes" in text:
                callers.append(path.name)
            for name in BANDS:
                if re.search(rf"add_modifier = \{{\s*name = {name}\b", text):
                    adders.append(path.name)
        self.assertEqual(callers, ["global_warming_regional_on_actions.txt"])
        self.assertEqual(sorted(set(adders)), ["global_warming_regional_effects.txt"])

    def test_the_monthly_state_pulse_refreshes_a_new_state_and_a_stale_one(self):
        on = load(ON_ACTIONS)
        self.assertEqual(on["on_monthly_pulse_state"], {"on_actions": ["gw_regional_monthly_on_action"]})
        body = _squash(_text(ON_ACTIONS))
        action = body[body.index("gw_regional_monthly_on_action = {"):]
        self.assertIn("trigger = { OR = { NOT = { has_variable = gw_regional_rooted } gw_regional_gap > 0.005 "
                      "gw_regional_gap < -0.005 } }", action)
        self.assertIn("effect = { gw_regional_refresh_effect = yes }", action)
        # No rule gate: with the rule off the anomaly is held at 0, which takes the modifiers off (spec § 5).
        self.assertNotIn("has_game_rule", action)

    def test_the_self_check_runs_from_the_world_pulse_under_the_rule(self):
        text = _text(EXTRA_ON_ACTIONS)
        start = text.index("global_warming_events_on_action = {")
        body = text[start:start + 4000]
        rule = body.index("has_game_rule = global_warming_enabled")
        self.assertGreater(body.index("gw_regional_selfcheck_effect = yes"), rule)
        self.assertIn("TE_SELF_CHECK OK gw_regional", self.effect)
        self.assertIn("TE_SELF_CHECK BROKEN gw_regional", self.effect)

    def test_the_self_check_reads_the_scale_not_only_the_presence(self):
        """A band modifier stuck at x1 is present: the check reads a tropical state's heatwave duration against
        Climate Warming's 0.5 and the band's 0.25 at its scale, away from 1 C where x1 reads right (review of
        #1747). Heatwave duration's only other carrier is the termination shock, whose owners are skipped."""
        check = self.effect[self.effect.index("gw_regional_selfcheck_effect = {"):]
        self.assertIn("modifier:state_harvest_condition_heatwave_duration_mult", check)
        self.assertIn("owner = { is_involved_in_journal_entry = je_world_climate "
                      "NOT = { has_modifier = gw_termination_shock_modifier } }", check)
        skip = re.search(r"OR = \{ gw_regional_target < ([\d.]+) gw_regional_target > ([\d.]+) \}", check)
        tolerance = float(re.search(r"gw_rg_chk_scale_gap < ([\d.]+) gw_rg_chk_scale_gap > -", check).group(1))
        # A modifier stuck at x1 reads 0.25 x |1 - scale| off: outside the skipped window that must exceed the
        # tolerance, or x1 could pass (second review of #1747: 0.9-1.1 against 0.03 let 0.89 through).
        for edge in (float(skip.group(1)), float(skip.group(2))):
            self.assertGreater(0.25 * abs(1 - edge), tolerance, edge)
        self.assertEqual(_lines("global_warming")["state_harvest_condition_heatwave_duration_mult"], 0.5)
        self.assertEqual(TROPICS["state_harvest_condition_heatwave_duration_mult"], 0.25)
        carriers = []
        for path in sorted((ROOT / "common").rglob("*.txt")):
            text = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))
            for m in re.finditer(r"(?m)^(\w+) = \{", text):
                end = text.find("\n}", m.end())
                if "state_harvest_condition_heatwave_duration_mult =" in text[m.end():end]:
                    carriers.append(m.group(1))
        self.assertEqual(sorted(carriers), sorted(["global_warming", "gw_termination_shock_modifier"] + list(BANDS)))


class GuideTableTest(unittest.TestCase):
    """Chapter 15's table of totals is Climate Warming plus each band (review of #1747: a farm cell missed
    Climate Warming's -2.5% on every building)."""

    def test_the_totals(self):
        text = (ROOT / "docs/player_guide/15-climate.md").read_text(encoding="utf-8")
        rows = {}
        for line in text.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 4 and cells[0] and not cells[0].startswith("-"):
                rows[cells[0]] = cells[1:]
        world = _lines("global_warming")
        every = world["building_throughput_add"]
        order = (TROPICS, {}, HIGH_LATITUDES)  # the table's columns: tropics, mid-latitudes, high latitudes

        def total(field, band, plus=0.0):
            return world.get(field, 0) + band.get(field, 0) + plus

        def pct(x):
            return ("+" if x > 0 else "−") + f"{abs(x) * 100:.1f}".rstrip("0").rstrip(".") + "%"

        for label, field, plus in (("Mortality", "state_mortality_mult", 0.0),
                                   ("Farm throughput", "building_group_bg_agriculture_throughput_add", every),
                                   ("Plantation throughput", "building_group_bg_plantations_throughput_add", every)):
            with self.subTest(label):
                self.assertEqual(rows[label], [pct(total(field, b, plus)) for b in order])
        with self.subTest("Standard of living"):
            self.assertEqual(rows["Standard of living"],
                             [("+" if x > 0 else "−") + f"{abs(x):g}"
                              for x in (total("state_standard_of_living_add", b) for b in order)])
        for label, field, word in (("Heatwaves", "state_harvest_condition_heatwave_impact_mult", "worse"),
                                   ("Wildfire impact", "state_harvest_condition_wildfire_impact_mult", "worse"),
                                   ("Frost", "state_harvest_condition_frost_impact_mult", "milder")):
            with self.subTest(label):
                self.assertEqual(rows[label], [f"{abs(total(field, b)) * 100:g}% {word}" for b in order])


class TextTest(unittest.TestCase):
    def test_names_and_descriptions(self):
        self.assertEqual(_loc("global_warming_tropics"), "Tropical Warming")
        self.assertEqual(_loc("global_warming_high_latitudes"), "High-Latitude Warming")
        for name in BANDS:
            self.assertIn("$global_warming$", _loc(f"{name}_desc"))
        self.assertIn("55°", _loc("global_warming_high_latitudes_desc"))

    def test_the_warming_penalty_hover_lists_both_bands_and_counts_our_states(self):
        tt = _loc("gw_cond_penalty_tt")
        for name in BANDS:
            self.assertIn(f"[GetStaticModifier('{name}').GetDesc]", tt)
        self.assertIn("ScriptValue('gw_regional_n_tropics')", tt)
        self.assertIn("ScriptValue('gw_regional_n_high_latitudes')", tt)
        self.assertIn("[GetStaticModifier('global_warming').GetDesc]", tt)

    def test_the_threshold_in_the_text_is_the_values(self):
        threshold = load(VALUES)["gw_regional_high_latitude_min"]
        for key in ("global_warming_high_latitudes_desc", "gw_cond_penalty_tt", "gw_how_penalty_2",
                    "je_world_climate_reason"):
            with self.subTest(key):
                self.assertIn(f"{threshold}°", _loc(key))

    def test_the_help_page_and_the_world_entry_name_both(self):
        for key in ("gw_how_penalty_2", "je_world_climate_reason"):
            for name in BANDS:
                self.assertIn(f"${name}$", _loc(key), key)


if __name__ == "__main__":
    unittest.main()
