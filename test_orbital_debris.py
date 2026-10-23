"""Orbital debris and the anti-satellite strike (Global Commons § 6).

docs/superpowers/archive/specs/2026-10-16-global-commons-design.md § 6. The system
keeps several numbers twice: a static modifier or a production method must
carry a literal, and the panel or the AI reads a script value mirroring it.
It also extends hand-kept lists elsewhere (the UN dossier's records), names
the interface the UN layer builds on, and rests on the spec's arithmetic
(background traffic settles near 4, fusion sweepers with an elevator clear 30
points in about 2.5 years, a cascade is beyond one early cleaner). The engine
checks none of it, so each test pins one copy to its source.

Run: python3 -m unittest test_orbital_debris -v
"""

import json
import re
import unittest
from pathlib import Path

from test_nuclear_deterrence import block, loc_keys, loc_value, read, strip_comments, tracked

ROOT = Path(__file__).resolve().parent
VALUES = ROOT / "common/script_values/te_orbital_debris_values.txt"
EFFECTS = ROOT / "common/scripted_effects/te_orbital_debris_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/te_orbital_debris_triggers.txt"
MODIFIERS = ROOT / "common/static_modifiers/te_orbital_debris_modifiers.txt"
TYPES = ROOT / "common/modifier_type_definitions/te_orbital_debris_modifier_types.txt"
PMS = ROOT / "common/production_methods/te_orbital_debris_pms.txt"
PMGS = ROOT / "common/production_method_groups/te_orbital_debris_pmgs.txt"
ACTION = ROOT / "common/diplomatic_actions/te_asat_strike_action.txt"
DECISIONS = ROOT / "common/decisions/te_orbital_debris_decisions.txt"
ON_ACTIONS = ROOT / "common/on_actions/te_orbital_debris_on_actions.txt"
EVENTS = ROOT / "events/te_orbital_debris_events.txt"
HOOK_TRIGGERS = ROOT / "common/scripted_triggers/te_asat_un_hooks.txt"
HOOK_EFFECTS = ROOT / "common/scripted_effects/te_asat_un_hooks.txt"
BUILDINGS = ROOT / "common/buildings/extra_buildings.txt"
EXTRA_PMS = ROOT / "common/production_methods/extra_pms.txt"
DOSSIER_VALUES = ROOT / "common/script_values/un_dossier_values.txt"
DOSSIER_EFFECTS = ROOT / "common/scripted_effects/un_dossier_effects.txt"
DOSSIER_TRIGGERS = ROOT / "common/scripted_triggers/un_dossier_triggers.txt"
CHAMBER = ROOT / "gui/journal_entry_widgets/un_chamber_widget.gui"
SR_GUI = ROOT / "gui/journal_entry_widgets/space_race_widget.gui"
DEBRIS_GUI = ROOT / "gui/journal_entry_widgets/te_orbital_debris_widget.gui"
VANILLA_TYPES = ROOT / "vanilla_parsed/common/modifier_types.json"
MOD_TYPES_DIR = ROOT / "common/modifier_type_definitions"
LENS = ROOT / "gfx/interface/icons/lens_toolbar_icons/te_asat_strike_action.dds"

ORBITAL_THROUGHPUT = ("building_space_mine_throughput_add", "building_space_elevator_throughput_add",
                      "building_orbital_battlestation_throughput_add",
                      "building_solar_receiver_throughput_add")
# method -> (technology, removal a month, weekly Launch Capacity, its mirror)
METHODS = {
    "pm_debris_active_removal": ("reusable_rocketry", 0.05, 300, "te_debris_units_active"),
    "pm_debris_laser_broom": ("directed_energy_weapons", 0.15, 300, "te_debris_units_laser"),
    "pm_debris_fusion_sweepers": ("compact_fusion_reactors", 0.5, 150, "te_debris_units_fusion"),
}


def number(text, name):
    """A script value written `name = { value = N }`, or `name = N` (the durations)."""
    m = re.search(rf"^{re.escape(name)} = (?:\{{ value = (-?[\d.]+) \}}|(-?[\d.]+)$)", text, re.M)
    assert m, f"{name} is not a one-line value"
    return float(m.group(1) or m.group(2))


def field(body, name):
    m = re.search(rf"^\s*{re.escape(name)} = (-?[\d.]+)\b", body, re.M)
    assert m, f"{name} not in block"
    return float(m.group(1))


def registered_types():
    names = set(json.loads(VANILLA_TYPES.read_text(encoding="utf-8")))
    for path in MOD_TYPES_DIR.glob("*.txt"):
        names |= set(re.findall(r"^([a-z_0-9]+) = \{", read(path), re.M))
    return names


class ContractTest(unittest.TestCase):
    """The names the UN layer (§ 6.5) builds on."""

    def test_hooks_defined(self):
        # The UN layer's bodies (test_global_commons_un.py checks what they do).
        self.assertRegex(read(HOOK_TRIGGERS), r"(?m)^te_asat_moratorium_party = \{")
        self.assertRegex(read(HOOK_EFFECTS), r"(?m)^te_asat_un_on_strike = \{")

    def test_strike_calls_the_hook_with_the_target_saved(self):
        body = strip_comments(block(strip_comments(read(EFFECTS)), "te_asat_strike_effect"))
        saved = body.index("save_scope_as = te_asat_target")
        self.assertGreater(body.index("te_asat_un_on_strike = yes"), saved)
        # The records are written before the hook reads them.
        for name in ("te_asat_last_strike_month", "te_asat_strikes_total"):
            self.assertLess(body.index(f"name = {name}"), body.index("te_asat_un_on_strike = yes"), name)
        self.assertIn("set_global_variable = { name = te_asat_last_strike_month value = te_history_month_index }", body)

    def test_the_moratorium_doubles_infamy_and_case(self):
        values = strip_comments(read(VALUES))
        for name in ("te_asat_infamy", "te_asat_case_points"):
            body = block(values, name)
            self.assertIn("te_asat_moratorium_party = yes", body, name)
            self.assertIn("multiply = te_asat_moratorium_factor", body, name)
        self.assertEqual(number(values, "te_asat_moratorium_factor"), 2)

    def test_removal_modifiers_are_country_types(self):
        types = strip_comments(read(TYPES))
        for name in ("country_orbital_debris_removal_add", "country_orbital_debris_removal_mult"):
            self.assertRegex(types, rf"(?m)^{name} = \{{", name)
        self.assertRegex(block(types, "country_orbital_debris_removal_mult"), r"percent = yes")

    def test_pool_names(self):
        effects = strip_comments(read(EFFECTS))
        for pool in ("orbital_debris_low", "orbital_debris_high"):
            self.assertIn(f"set_global_variable = {{ name = {pool} value = 0 }}", effects, pool)


class ModifierTest(unittest.TestCase):
    def setUp(self):
        self.mods = strip_comments(read(MODIFIERS))
        self.values = strip_comments(read(VALUES))

    def test_every_modifier_field_is_registered(self):
        types = registered_types()
        for name in re.findall(r"^(te_\w+) = \{", self.mods, re.M):
            for key in re.findall(r"^\t([a-z_0-9]+) = ", block(self.mods, name), re.M):
                if key == "icon":
                    continue
                with self.subTest(modifier=name, key=key):
                    self.assertIn(key, types)

    def test_the_panel_mirrors_the_unit_modifier(self):
        unit = block(self.mods, "te_orbital_debris")
        self.assertAlmostEqual(field(unit, "country_space_race_risk_mult") * 100,
                               number(self.values, "te_debris_per_point_risk_pct"))
        self.assertAlmostEqual(field(unit, "country_space_race_progress_mult") * -100,
                               number(self.values, "te_debris_per_point_pace_pct"))
        for key in ORBITAL_THROUGHPUT:
            with self.subTest(key=key):
                self.assertAlmostEqual(field(unit, key) * -100,
                                       number(self.values, "te_debris_per_point_throughput_pct"))

    def test_the_solar_collector_is_spared(self):
        """Its slots are workforce-scaled, so a throughput cut there would
        let overbuild protection demolish receivers; the receivers carry it."""
        for name in ("te_orbital_debris", "te_orbital_network_disrupted"):
            self.assertNotIn("building_solar_collector_throughput_add", block(self.mods, name))

    def test_cleaner_prestige_is_one_percent_a_step(self):
        self.assertAlmostEqual(field(block(self.mods, "te_debris_cleaner_prestige"), "country_prestige_mult"), 0.01)
        self.assertEqual(number(self.values, "te_debris_cleaner_steps_per_point"), 10)

    def test_disruption_figures(self):
        body = block(self.mods, "te_orbital_network_disrupted")
        self.assertAlmostEqual(field(body, "unit_offense_mult"), -0.1)
        self.assertAlmostEqual(field(body, "unit_defense_mult"), -0.1)
        self.assertAlmostEqual(field(body, "country_space_race_progress_mult"), -0.2)
        for key in ORBITAL_THROUGHPUT[1:]:
            self.assertAlmostEqual(field(body, key), -0.25, msg=key)
        self.assertEqual(number(self.values, "te_asat_disruption_days"), 365)
        self.assertEqual(number(self.values, "te_asat_disruption_days_short"), 182)
        self.assertEqual(number(self.values, "te_asat_battlestation_factor"), 0.5)
        text = loc_value("te_asat_tt_effect_network")
        self.assertIn("for a year, or six months", text)
        self.assertIn("half as badly", text)

    def test_ribbon_strike(self):
        self.assertAlmostEqual(field(block(self.mods, "te_ribbon_strike_damage"), "building_throughput_add"), -0.5)
        self.assertEqual(number(self.values, "te_debris_ribbon_days_long"), 182)
        self.assertEqual(number(self.values, "te_debris_ribbon_days_short"), 61)
        self.assertIn("for 6 months", loc_value("te_orbital_debris.1.a.tt"))
        self.assertIn("for 2 months", loc_value("te_orbital_debris.1.b.tt"))
        self.assertEqual(number(self.values, "te_debris_ribbon_chance_per_point"), 0.02)


class CleanupTest(unittest.TestCase):
    def setUp(self):
        self.pms = strip_comments(read(PMS))
        self.values = strip_comments(read(VALUES))

    def test_methods_follow_the_spec(self):
        for pm, (tech, removal, units, mirror) in METHODS.items():
            with self.subTest(pm=pm):
                body = block(self.pms, pm)
                self.assertIn(tech, block(body, "unlocking_technologies"))
                country = block(block(body, "country_modifiers"), "workforce_scaled")
                self.assertAlmostEqual(field(country, "country_orbital_debris_removal_add"), removal)
                # The prestige is script's (te_debris_removal_method_prestige), so the
                # group's most_productive gives the AI no reason to switch removal on.
                self.assertNotIn("prestige", body)
                goods = block(block(body, "building_modifiers"), "workforce_scaled")
                self.assertEqual(field(goods, "goods_input_launch_capacity_add"), units)
                self.assertEqual(number(self.values, mirror), units)
                self.assertNotIn("building_employment", body)
        laser = block(block(block(self.pms, "pm_debris_laser_broom"), "building_modifiers"), "workforce_scaled")
        self.assertEqual(field(laser, "goods_input_electricity_add"),
                         number(self.values, "te_debris_units_laser_electricity"))

    def test_launch_capacity_per_point_falls_with_technology(self):
        per_point = [units * 52 / 12 / removal for _, removal, units, _ in METHODS.values()]
        self.assertEqual(per_point, sorted(per_point, reverse=True))
        self.assertAlmostEqual(per_point[0], 26000, delta=200)
        self.assertAlmostEqual(per_point[-1], 1300, delta=50)

    def test_group_on_the_space_program(self):
        group = strip_comments(read(PMGS))
        body = block(group, "pmg_space_program_debris_removal")
        methods = re.findall(r"\bpm_\w+", block(body, "production_methods"))
        self.assertEqual(methods, ["pm_debris_removal_none"] + list(METHODS))
        self.assertIn("ai_selection = most_productive", body)
        building = block(strip_comments(read(BUILDINGS)), "REPLACE_OR_CREATE:building_space_program")
        self.assertIn("pmg_space_program_debris_removal", block(building, "production_method_groups"))

    def test_the_elevator_doubles_removal(self):
        elevator = block(strip_comments(read(EXTRA_PMS)), "pm_space_elevator")
        country = block(block(elevator, "country_modifiers"), "workforce_scaled")
        self.assertAlmostEqual(field(country, "country_orbital_debris_removal_mult"), 0.1)
        self.assertEqual(number(self.values, "te_debris_removal_mult_cap"), 1)

    def test_the_decision_picks_the_best_method(self):
        effects = strip_comments(read(EFFECTS))
        body = block(effects, "te_debris_activate_best_removal")
        order = re.findall(r"production_method = (pm_\w+)", body)
        self.assertEqual(order, list(reversed(list(METHODS))))
        decision = strip_comments(read(DECISIONS))
        self.assertIn("te_debris_activate_best_removal = yes", block(decision, "when_taken"))
        ai = block(decision, "ai_chance")
        self.assertIn("te_debris_tier_cluttered", ai)
        self.assertIn("te_debris_tier_hazardous", ai)
        self.assertNotIn("is_ai", decision)


class DossierTest(unittest.TestCase):
    """The new ground is a sixth record everywhere the five are listed."""

    def test_asat_is_a_record_everywhere(self):
        values = strip_comments(read(DOSSIER_VALUES))
        self.assertEqual(number(values, "un_dos_points_asat"), 15)
        self.assertIn("add = var:un_dos_asat", block(values, "un_case_strength"))
        self.assertIn("add = var:un_dos_asat", block(values, "un_disp_dos_asat"))
        self.assertIn("RECORD = asat", block(strip_comments(read(DOSSIER_EFFECTS)), "un_dossier_monthly_update"))
        self.assertIn("has_variable = un_dos_asat",
                      block(strip_comments(read(DOSSIER_TRIGGERS)), "un_dossier_has_records"))
        self.assertIn("ScriptValue('un_disp_dos_asat')", read(CHAMBER))
        self.assertIn("un_disp_dos_asat", loc_value("je_un_chamber_grounds_record"))
        self.assertIn("anti-satellite", loc_value("je_un_chamber_exposure_help"))
        strike = strip_comments(read(EFFECTS))
        self.assertIn("un_dossier_record = { RECORD = asat POINTS = te_asat_case_points }",
                      block(strike, "te_asat_strike_effect"))
        self.assertIn("value = un_dos_points_asat", block(strip_comments(read(VALUES)), "te_asat_case_points"))


class StrikeTest(unittest.TestCase):
    def setUp(self):
        self.action = strip_comments(read(ACTION))

    def test_requirements(self):
        body = block(self.action, "te_asat_strike_action")
        potential = block(body, "potential")
        self.assertIn("has_game_rule = space_race_enabled", potential)
        self.assertIn("has_technology_researched = guided_missiles", potential)
        possible = block(body, "possible")
        for test in ("has_war_with = scope:target_country", "sr_has_space_program = yes",
                     "te_asat_has_orbital_assets = yes", "te_asat_struck_recently = yes"):
            self.assertIn(test, possible, test)
        self.assertEqual(number(strip_comments(read(VALUES)), "te_asat_cooldown_months"), 12)

    def test_effects_run_hidden_and_infamy_once(self):
        accept = block(self.action, "accept_effect")
        self.assertEqual(accept.count("change_infamy"), 1)
        self.assertIn("te_asat_strike_effect = yes", block(accept, "hidden_effect"))
        self.assertNotIn("change_infamy", block(strip_comments(read(EFFECTS)), "te_asat_strike_effect"))

    def test_the_ai_never_reads_is_ai(self):
        self.assertNotIn("is_ai", self.action)
        self.assertIn("te_asat_ai_would_strike", block(self.action, "will_propose"))
        self.assertIn("te_debris_tier_hazardous", block(self.action, "evaluation_chance"))

    def test_the_lens_has_an_icon(self):
        self.assertTrue(LENS.exists() or tracked(LENS), "missing lens_toolbar_icons/te_asat_strike_action.dds")

    def test_the_rebuild_puts_back_the_months_left_as_literals(self):
        """add_modifier's days reads a computed script value as 0, so the rebuild branches on
        the months left (scripting_best_practices.md, "Modifier & Cooldown Duration Units")."""
        body = block(strip_comments(read(EFFECTS)), "te_asat_rebuild_disruption")
        self.assertNotIn("te_asat_disruption_days_left", body)
        rungs = [(int(m), int(d)) for m, d in re.findall(
            r"te_asat_disruption_months_left <= (\d+) \}\s*add_modifier = \{ name = te_orbital_network_disrupted "
            r"days = (\d+) multiplier = te_asat_disruption_factor_held \}", body)]
        longest = round(number(strip_comments(read(VALUES)), "te_asat_disruption_days") / 30)
        self.assertEqual(rungs, [(k, 30 * k) for k in range(1, longest)])
        self.assertRegex(body, r"else = \{\s*add_modifier = \{ name = te_orbital_network_disrupted "
                               rf"days = {30 * longest} multiplier = te_asat_disruption_factor_held \}}")

    def test_debris_and_relations(self):
        values = strip_comments(read(VALUES))
        self.assertEqual(number(values, "te_asat_debris_low"), 6)
        self.assertEqual(number(values, "te_asat_debris_high"), 6)
        self.assertEqual(number(values, "te_asat_infamy_base"), 5)
        self.assertEqual(number(values, "te_asat_relations"), -30)


class WiringTest(unittest.TestCase):
    def test_pulses(self):
        text = strip_comments(read(ON_ACTIONS))
        self.assertIn("te_debris_global_monthly_on_action", block(text, "on_monthly_pulse"))
        self.assertIn("te_debris_country_monthly_on_action", block(text, "on_monthly_pulse_country"))
        for name in ("te_debris_global_monthly_on_action", "te_debris_country_monthly_on_action"):
            self.assertIn("space_race_enabled", block(text, name))

    def test_one_refresh_site_each(self):
        """te_orbital_debris and te_debris_cleaner_prestige are added in one place."""
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "events").rglob("*.txt")):
            text = strip_comments(read(path))
            for name in ("te_orbital_debris", "te_debris_cleaner_prestige",
                         "te_debris_removal_method_prestige"):
                hits = re.findall(rf"add_modifier = \{{ name = {name}\b", text)
                if hits:
                    self.assertEqual(path, EFFECTS, f"{name} added in {path}")
                    self.assertEqual(len(hits), 1)

    def test_the_mission_control_row(self):
        gui = read(SR_GUI)
        start = gui.index("type te_sr_sec_control = flowcontainer {")
        end = gui.index("\n\ttype ", start + 1)
        self.assertIn("te_sr_debris_row = {}", gui[start:end])
        self.assertIn("type te_sr_debris_row = te_sr_text", read(DEBRIS_GUI))
        for key in ("te_debris_row", "te_debris_row_tt", "te_debris_row_tt_hazardous",
                    "te_debris_row_tt_kessler", "te_debris_row_tt_cleaners",
                    "te_debris_row_tt_no_cleaners", "te_debris_tier_clear", "te_debris_tier_cluttered",
                    "te_debris_tier_hazardous", "te_debris_tier_kessler", "concept_orbital_debris",
                    "concept_orbital_debris_desc"):
            self.assertIn(key, loc_keys(), key)

    def test_the_event_has_art(self):
        self.assertIn("event_image = { texture = ", block(read(EVENTS), "te_orbital_debris.1"))


class ModelTest(unittest.TestCase):
    """The spec's arithmetic, run on the script's own numbers: the monthly step
    of te_debris_global_monthly (sources on last month's index, decay, removal
    from the high pool first, the ceiling)."""

    def setUp(self):
        v = strip_comments(read(VALUES))
        self.d_low = number(v, "te_debris_low_decay")
        self.d_high = number(v, "te_debris_high_decay")
        self.traffic = number(v, "te_debris_traffic_per_program")
        self.k_at = number(v, "te_debris_kessler_threshold")
        self.k_rate = number(v, "te_debris_kessler_rate")
        self.cap = number(v, "te_debris_index_cap")
        self.strike = number(v, "te_asat_debris_low"), number(v, "te_asat_debris_high")

    def step(self, low, high, programs, removal):
        if low + high >= self.k_at:
            high += self.k_rate
        low += programs * self.traffic
        low *= 1 - self.d_low
        high *= 1 - self.d_high
        if high >= removal:
            high -= removal
        else:
            low -= removal - high
            high = 0
        high = min(max(high, 0), self.cap)
        low = max(min(low, self.cap - high), 0)
        return low, high

    def run_months(self, low, high, months, programs=0, removal=0.0):
        for _ in range(months):
            low, high = self.step(low, high, programs, removal)
        return low, high

    def test_half_lives(self):
        self.assertAlmostEqual(0.5 ** (1 / 48), 1 - self.d_low, delta=0.003)    # about 4 years
        self.assertAlmostEqual(0.5 ** (1 / (115 * 12)), 1 - self.d_high, delta=0.0001)

    def test_six_programs_settle_near_four(self):
        low, high = self.run_months(0, 0, 1200, programs=6)
        self.assertAlmostEqual(low + high, 4, delta=0.2)

    def test_fusion_and_an_elevator_clear_thirty_in_about_two_and_a_half_years(self):
        low, high = 0.0, 30.0
        months = 0
        while low + high > 0.01:
            low, high = self.step(low, high, 0, 0.5 * 2)
            months += 1
        self.assertTrue(24 <= months <= 33, months)

    def test_a_cascade_is_beyond_one_early_cleaner(self):
        low, high = self.run_months(0, 80, 240, removal=0.05)
        self.assertGreaterEqual(low + high, self.k_at)
        low, high = self.run_months(0, 80, 240, removal=0.5)
        self.assertLess(low + high, self.k_at)

    def test_the_ceiling_keeps_the_long_lived_debris(self):
        """Twenty strikes in a row: the index stops at the ceiling, and since
        the low pool gives way, more strikes never shorten the cascade."""
        low, high = 0.0, 0.0
        for _ in range(20):
            low += self.strike[0]
            high += self.strike[1]
            high = min(high, self.cap)
            low = max(min(low, self.cap - high), 0)
            self.assertLessEqual(low + high, self.cap + 1e-9)
            low, high = self.step(low, high, 10, 0)
        low, high = self.run_months(low, high, 600, programs=10)
        self.assertLessEqual(low + high, self.cap + 1e-9)
        self.assertGreater(low + high, self.k_at)

    def test_strikes_add_twelve(self):
        self.assertEqual(sum(self.strike), 12)


if __name__ == "__main__":
    unittest.main()
