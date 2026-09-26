"""The internal resettlement registry: every programme in one table, pinned
against every site that lists programmes by hand.

Design: docs/superpowers/specs/2026-09-26-internal-resettlement-design.md.
Adding a programme touches the PM, its loc, the recruitment rule's branch, the
programme-code switch, the transit-mortality table, the volume counter, the
politics modifier, the law gates, the Declaration line and the docs. Nothing in
the engine checks that they agree. PROGRAMMES is the single list; each test
checks one site against it, so a half-added programme fails here, naming the
site. The frontier values and the game rule are pinned here too.

Run: python3 -m unittest test_resettlement_programme_registry -v
"""
import re
import unittest
from collections import namedtuple
from pathlib import Path

ROOT = Path(__file__).resolve().parent

VALUES = "common/script_values/resettlement_values.txt"
TRIGGERS = "common/scripted_triggers/resettlement_triggers.txt"
RULES = "common/game_rules/extra_game_rules.txt"

RULE_SETTINGS = ("internal_resettlement_enabled", "internal_resettlement_ai_voluntary",
                 "internal_resettlement_disabled")

BUILDING_FILE = "common/buildings/resettlement.txt"
PMG_FILE = "common/production_method_groups/resettlement_pmgs.txt"
PM_FILE = "common/production_methods/resettlement_pms.txt"
MODIFIER_TYPES = "common/modifier_type_definitions/mod_entity_modifier_types.txt"
BASE_VALUES = "common/static_modifiers/extra_modifiers.txt"
TECH_FILES = ("common/technology/technologies/modified.txt",
              "common/technology/technologies/era_6.txt",
              "common/technology/technologies/era_7.txt")
CAP_TECHS = ("nationalism", "civilizing_mission", "mass_propaganda",
             "keynesian_economics", "civil_rights_movement")

# ---- The table ----------------------------------------------------------------------
# key         the programme: pm_resettlement_<key>, rs_month_<key>, resettlement_<key>_politics
# code        the value of var:rs_programme on a destination running it (resettlement_set_programme_code)
# techs       unlocking_technologies (any of)
# laws        unlocking_laws (any of)
# disallowed  disallowing_laws
# coercive    carries transit deaths, the Declaration violation and the Declaration line
# capacity    people a month per level (half level_scaled, half workforce_scaled)
# mortality   the share of recruits who die in transit
# politics    its country modifier (§7.2), or None for a programme with no IG reaction
Programme = namedtuple("Programme", "key code techs laws disallowed coercive capacity mortality politics")

PROGRAMMES = (
    Programme("land_grants", 0, (), (), (), False, 300, 0,
              {"interest_group_ig_rural_folk_approval_add": 3, "interest_group_ig_landowners_approval_add": -3}),
    Programme("military_colonies", 1, ("standing_army",), (), (), False, 250, 0,
              {"interest_group_ig_armed_forces_approval_add": 3, "interest_group_ig_rural_folk_approval_add": -3}),
    Programme("penal_transportation", 2, ("law_enforcement",), (), ("law_guaranteed_liberties",), True, 100, 0.05,
              {"interest_group_ig_intelligentsia_approval_add": -3}),
    Programme("organized_colonization", 3, ("railways",), (), (), False, 500, 0,
              {"interest_group_ig_rural_folk_approval_add": 3}),
    Programme("special_settlements", 4, ("mass_propaganda",), ("law_collectivized_agriculture",),
              ("law_guaranteed_liberties", "law_protected_speech", "law_right_of_assembly"), True, 1000, 0.15,
              {"interest_group_ig_rural_folk_approval_add": -10, "interest_group_ig_intelligentsia_approval_add": -5}),
    Programme("development_program", 5, ("keynesian_economics",), (), (), False, 800, 0, None),
    Programme("rustication", 6, ("mass_media",), ("law_single_party_state",), (), True, 800, 0.01,
              {"interest_group_ig_intelligentsia_approval_add": -10,
               "interest_group_ig_petty_bourgeoisie_approval_add": -5}),
    Programme("managed_retreat", 7, ("environmental_movement",), (), (), False, 600, 0, None),
)
PROGRAMME_KEYS = tuple(p.key for p in PROGRAMMES)
COERCIVE = tuple(p for p in PROGRAMMES if p.coercive)
WITH_POLITICS = tuple(p for p in PROGRAMMES if p.politics)

# (key, unlocking technologies)
SETTLEMENTS = (
    ("homesteads", ()),
    ("work_settlements", ()),
    ("planned_towns", ("modern_urban_planning",)),
)
# (key, unlocking technologies, capacity per level)
TRANSPORTS = (
    ("overland", (), 0),
    ("rail_steamship", ("railways",), 200),
    ("motor_transport", ("combustion_engine",), 400),
    ("airlift", ("commercial_aviation",), 600),
)


def pm(key):
    return f"pm_resettlement_{key}"


def list_field(body, field):
    inner = block(body, field)
    return tuple(inner.split()) if inner else ()


def transfer_in(pm_body, scaling):
    return number(block(block(pm_body, "state_modifiers") or "", scaling) or "",
                  "state_resettlement_transfer_add") or 0.0


# ---- helpers -------------------------------------------------------------------------

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def block(text, name):
    """Body of the first `name = {` block in text (comments stripped), or None."""
    text = strip_comments(text)
    m = re.search(r"(?<![\w.:$])" + re.escape(name) + r"\s*=\s*\{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def number(body, key):
    """The first `key = <number>` in body, as a float, or None."""
    m = re.search(r"(?<![\w.:])" + re.escape(key) + r"\s*=\s*(-?\d+(?:\.\d+)?)", body or "")
    return float(m.group(1)) if m else None


def squash(text):
    return " ".join((text or "").split())


def top_level_blocks(text):
    """(name, body) for every top-level `name = {` in text (comments stripped)."""
    text = strip_comments(text)
    for m in re.finditer(r"(?m)^([\w:.]+)\s*=\s*\{", text):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        yield m.group(1), text[m.end():i - 1]


_LOC = None


def loc():
    global _LOC
    if _LOC is None:
        _LOC = {}
        for path in sorted((ROOT / "localization/english").glob("*.yml")):
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                m = re.match(r'\s*([\w.$]+):\d*\s+"(.*)"\s*$', line)
                if m:
                    _LOC[m.group(1)] = m.group(2)
    return _LOC


# ---- the frontier and the game rule (Task 2) -----------------------------------------

class FrontierTests(unittest.TestCase):
    def test_thresholds_are_the_specs(self):
        text = strip_comments(read(VALUES))
        self.assertRegex(text, r"(?m)^resettlement_frontier_open_base = 2\s*$")
        self.assertRegex(text, r"(?m)^resettlement_frontier_close_base = 10\s*$")

    def test_density_is_region_population_over_area(self):
        text = read(VALUES)
        pop = squash(block(text, "te_region_population"))
        self.assertIn("state_region = { every_scope_state = { add = state_population } }", pop)
        area = block(text, "te_region_area_km2")
        self.assertIn("var:te_region_area", area)
        self.assertEqual(number(area, "value"), 1.0, "no table yet must read as 1 km² (never a frontier)")
        density = squash(block(text, "resettlement_frontier_density"))
        self.assertIn("value = te_region_population", density)
        self.assertIn("divide = te_region_area_km2", density)

    def test_both_thresholds_scale_with_the_crowding_modifier(self):
        text = read(VALUES)
        self.assertIn("modifier:state_migration_crowding_density_mult",
                      block(text, "resettlement_crowding_scale"))
        for name, base in (("resettlement_frontier_open_density", "resettlement_frontier_open_base"),
                           ("resettlement_frontier_close_density", "resettlement_frontier_close_base")):
            body = squash(block(text, name))
            self.assertIn(f"value = {base}", body)
            self.assertIn("multiply = resettlement_crowding_scale", body)

    def test_margins_are_threshold_minus_density(self):
        text = read(VALUES)
        for margin, threshold in (("resettlement_frontier_open_margin", "resettlement_frontier_open_density"),
                                  ("resettlement_frontier_close_margin", "resettlement_frontier_close_density")):
            body = squash(block(text, margin))
            self.assertIn(f"value = {threshold}", body)
            self.assertIn("subtract = resettlement_frontier_density", body)

    def test_frontier_triggers_read_the_margins(self):
        text = read(TRIGGERS)
        self.assertIn("resettlement_frontier_open_margin > 0",
                      squash(block(text, "resettlement_state_is_open_frontier")))
        self.assertIn("resettlement_frontier_close_margin > 0",
                      squash(block(text, "resettlement_state_frontier_still_open")))

    def test_rule_triggers(self):
        text = read(TRIGGERS)
        self.assertIn("NOT = { has_game_rule = internal_resettlement_disabled }",
                      squash(block(text, "resettlement_system_enabled")))
        voluntary = squash(block(text, "resettlement_ai_voluntary_only"))
        self.assertIn("is_ai = yes", voluntary)
        self.assertIn("has_game_rule = internal_resettlement_ai_voluntary", voluntary)

    def test_rule_has_three_settings_default_enabled(self):
        body = block(read(RULES), "internal_resettlement_rule")
        self.assertIsNotNone(body)
        self.assertIn("default = internal_resettlement_enabled", squash(body))
        for setting in RULE_SETTINGS:
            self.assertIn(f"flag = {setting}", squash(block(body, setting)))

    def test_rule_is_localized(self):
        L = loc()
        self.assertIn("rule_internal_resettlement_rule", L)
        for setting in RULE_SETTINGS:
            self.assertIn(f"setting_{setting}", L)
            self.assertIn(f"setting_{setting}_desc", L)


# ---- the building and its production methods (Task 3) --------------------------------

class GroupTests(unittest.TestCase):
    def test_building_has_the_three_groups_in_order(self):
        body = block(read(BUILDING_FILE), "building_resettlement_colony")
        self.assertEqual(list_field(body, "production_method_groups"),
                         ("pmg_resettlement_programme", "pmg_resettlement_settlement",
                          "pmg_resettlement_transportation"))

    def test_groups_list_the_tables(self):
        text = read(PMG_FILE)
        self.assertEqual(list_field(block(text, "pmg_resettlement_programme"), "production_methods"),
                         tuple(pm(p.key) for p in PROGRAMMES))
        self.assertEqual(list_field(block(text, "pmg_resettlement_settlement"), "production_methods"),
                         tuple(pm(k) for k, _ in SETTLEMENTS))
        self.assertEqual(list_field(block(text, "pmg_resettlement_transportation"), "production_methods"),
                         tuple(pm(k) for k, _, _ in TRANSPORTS))

    def test_codes_are_contiguous_from_zero(self):
        self.assertEqual([p.code for p in PROGRAMMES], list(range(len(PROGRAMMES))))


class ProgrammeTests(unittest.TestCase):
    def test_unlocks_and_law_gates(self):
        text = read(PM_FILE)
        for p in PROGRAMMES:
            body = block(text, pm(p.key))
            self.assertIsNotNone(body, pm(p.key))
            self.assertEqual(list_field(body, "unlocking_technologies"), p.techs, p.key)
            self.assertEqual(list_field(body, "unlocking_laws"), p.laws, p.key)
            self.assertEqual(list_field(body, "disallowing_laws"), p.disallowed, p.key)

    def test_capacity_is_split_half_and_half(self):
        text = read(PM_FILE)
        for p in PROGRAMMES:
            body = block(text, pm(p.key))
            self.assertEqual(transfer_in(body, "level_scaled"), p.capacity / 2, p.key)
            self.assertEqual(transfer_in(body, "workforce_scaled"), p.capacity / 2, p.key)

    def test_every_programme_speeds_incorporation_and_colony_growth(self):
        text = read(PM_FILE)
        for p in PROGRAMMES:
            unscaled = block(block(block(text, pm(p.key)), "state_modifiers"), "unscaled")
            self.assertGreater(number(unscaled, "state_incorporation_speed_mult") or 0, 0, p.key)
            self.assertGreater(number(unscaled, "state_colony_growth_speed_mult") or 0, 0, p.key)

    def test_the_declaration_line_is_on_coercive_programmes_only(self):
        L = loc()
        self.assertIn("resettlement_declaration_pm_line", L)
        for p in PROGRAMMES:
            desc = L.get(f"{pm(p.key)}_desc", "")
            self.assertEqual("$resettlement_declaration_pm_line$" in desc, p.coercive, p.key)


class SettlementAndTransportTests(unittest.TestCase):
    def test_settlement_unlocks(self):
        text = read(PM_FILE)
        for key, techs in SETTLEMENTS:
            self.assertEqual(list_field(block(text, pm(key)), "unlocking_technologies"), techs, key)

    def test_homesteads_add_no_arable_land(self):
        body = block(read(PM_FILE), pm("homesteads"))
        self.assertNotIn("arable", body)
        unscaled = block(block(body, "state_modifiers"), "unscaled")
        self.assertGreater(number(unscaled, "building_group_bg_agriculture_throughput_add"), 0)
        self.assertGreater(number(unscaled, "building_group_bg_ranching_throughput_add"), 0)

    def test_every_settlement_adds_level_scaled_pull(self):
        text = read(PM_FILE)
        for key, _ in SETTLEMENTS:
            level = block(block(block(text, pm(key)), "state_modifiers"), "level_scaled")
            self.assertGreater(number(level, "state_migration_pull_add") or 0, 0, key)

    def test_transport_unlocks_and_capacity(self):
        text = read(PM_FILE)
        for key, techs, capacity in TRANSPORTS:
            body = block(text, pm(key))
            self.assertEqual(list_field(body, "unlocking_technologies"), techs, key)
            self.assertEqual(transfer_in(body, "level_scaled") + transfer_in(body, "workforce_scaled"),
                             capacity, key)


class PmHygieneTests(unittest.TestCase):
    def _all_pms(self):
        text = read(PM_FILE)
        names = [pm(p.key) for p in PROGRAMMES] + [pm(k) for k, _ in SETTLEMENTS] + [pm(k) for k, _, _ in TRANSPORTS]
        return {n: block(text, n) for n in names}

    def test_multipliers_only_in_unscaled_blocks(self):
        for name, body in self._all_pms().items():
            for section in ("state_modifiers", "country_modifiers", "building_modifiers"):
                sec = block(body, section) or ""
                for scaling in ("level_scaled", "workforce_scaled", "throughput_scaled"):
                    self.assertNotRegex(block(sec, scaling) or "", r"_mult\s*=", f"{name} {section}.{scaling}")

    def test_no_ig_approval_in_any_pm(self):
        for name, body in self._all_pms().items():
            self.assertNotIn("interest_group_", body, name)

    def test_every_pm_and_group_is_localized(self):
        L = loc()
        for name in self._all_pms():
            self.assertIn(name, L)
            self.assertIn(f"{name}_desc", L)
        for group in ("pmg_resettlement_programme", "pmg_resettlement_settlement",
                      "pmg_resettlement_transportation", "building_resettlement_colony",
                      "building_resettlement_colony_desc"):
            self.assertIn(group, L)


class BuildingTests(unittest.TestCase):
    def test_possible_reads_the_rule_and_both_frontier_gates(self):
        possible = squash(block(block(read(BUILDING_FILE), "building_resettlement_colony"), "possible"))
        for trig in ("resettlement_system_enabled = yes", "resettlement_state_is_open_frontier = yes",
                     "resettlement_state_frontier_still_open = yes"):
            self.assertIn(trig, possible)
        self.assertNotIn("law_closed_borders", possible)

    def test_level_cap_is_five_plus_five_per_tech(self):
        base = block(read(BASE_VALUES), "INJECT:base_values")
        self.assertEqual(number(base, "state_building_resettlement_colony_max_level_add"), 5)
        granted = [name.split(":")[-1]
                   for rel in TECH_FILES for name, body in top_level_blocks(read(rel))
                   if number(body, "state_building_resettlement_colony_max_level_add") == 5]
        self.assertEqual(sorted(granted), sorted(CAP_TECHS))


class OldSystemGoneTests(unittest.TestCase):
    GONE = ("building_resettlement_camp", "pmg_resettlement_method", "state_building_resettlement_camp_max_level_add",
            "resettlement_transfer_effect", "resettlement_transfer_on_action", "pm_homesteading_program",
            "pm_forced_resettlement", "pm_incentivized_relocation", "pm_settler_homesteads",
            "pm_administered_territory", "pm_development_zone", "pm_resettlement_railway",
            "pm_resettlement_steamship", "pm_organized_colonization", "pm_penal_transportation",
            "pm_planned_settlement")

    def test_no_trace_in_script_or_loc(self):
        for sub in ("common", "events", "localization/english", "gui"):
            for path in (ROOT / sub).rglob("*"):
                if path.suffix not in (".txt", ".yml", ".gui") or not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8-sig", errors="replace")
                for name in self.GONE:
                    self.assertNotRegex(text, rf"(?<![\w]){name}(?![\w])", f"{name} in {path.relative_to(ROOT)}")


if __name__ == "__main__":
    unittest.main()
