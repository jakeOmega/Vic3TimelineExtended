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
    """Body of the `name = {` block in text (comments stripped), or None.

    Prefers a column-0 definition over a match anywhere else: a parameterized
    call site (`name = { KEY = value }`) is textually identical to a
    definition's opener, so if the call appears earlier in the file than the
    definition itself, a plain first-match search would return the call's
    tiny body instead. Falls back to the first match anywhere when no
    column-0 opener exists, which nested lookups like
    `block(pm_body, "state_modifiers")` rely on (those are never at column 0).
    """
    text = strip_comments(text)
    escaped = re.escape(name)
    m = re.search(r"(?m)^" + escaped + r"\s*=\s*\{", text)
    if not m:
        m = re.search(r"(?<![\w.:$])" + escaped + r"\s*=\s*\{", text)
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


# ---- the block() test helper itself ---------------------------------------------------

class BlockHelperTests(unittest.TestCase):
    def test_prefers_the_column_zero_definition_over_an_earlier_call_site(self):
        text = "wrapper = {\n\tfoo = { X = 1 }\n}\n\nfoo = {\n\treal\n}\n"
        self.assertEqual(squash(block(text, "foo")), "real")


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


EFFECTS = "common/scripted_effects/resettlement_effects.txt"
RS_MODIFIERS = "common/static_modifiers/resettlement_modifiers.txt"
RS_ON_ACTIONS = "common/on_actions/resettlement_on_actions.txt"
RS_EVENTS = "events/resettlement_events.txt"
DECREES = "common/decrees/extra_decrees.txt"
VOLUNTARY = ("land_grants", "military_colonies", "organized_colonization", "development_program")

# (static modifier, modifier type, scope it sits on)
READOUTS = (
    ("resettlement_arrivals", "building_resettlement_arrivals_add", "building"),
    ("resettlement_transit_deaths", "building_resettlement_transit_deaths_add", "building"),
    ("resettlement_recruits", "state_resettlement_recruits_add", "state"),
)


class TransferTests(unittest.TestCase):
    def test_eligibility_has_one_branch_per_code(self):
        body = block(read(TRIGGERS), "resettlement_pop_eligible")
        codes = {int(c) for c in re.findall(r"scope:rs_destination\.var:rs_programme = (\d+)", body)}
        self.assertEqual(codes, {p.code for p in PROGRAMMES})

    def test_eligibility_never_selects_culture_or_religion(self):
        text = read(TRIGGERS)
        for name in ("resettlement_pop_eligible", "resettlement_pop_volunteer", "resettlement_pop_colonist",
                     "resettlement_pop_urban_worker", "resettlement_state_is_damaged"):
            body = block(text, name)
            self.assertIsNotNone(body, name)
            self.assertNotRegex(body, r"\b(culture|religion)\b", name)

    def test_slaves_are_never_eligible(self):
        self.assertIn("NOT = { is_pop_type = slaves }", squash(block(read(TRIGGERS), "resettlement_pop_eligible")))

    def test_code_switch_matches_the_table(self):
        body = squash(block(read(EFFECTS), "resettlement_set_programme_code"))
        found = {m.group(1): (int(m.group(2)), float(m.group(3))) for m in re.finditer(
            r"resettlement_runs_pm = \{ PM = pm_resettlement_(\w+) \} \} "
            r"set_variable = \{ name = rs_programme value = (\d+) \} "
            r"set_variable = \{ name = rs_mortality value = ([\d.]+) \}", body)}
        self.assertEqual(found, {p.key: (p.code, float(p.mortality)) for p in PROGRAMMES})

    def test_coercive_and_voluntary_triggers_partition_the_table(self):
        text = read(TRIGGERS)
        def pms(name):
            return set(re.findall(r"PM = pm_resettlement_(\w+)", block(text, name)))
        self.assertEqual(pms("resettlement_state_runs_coercive"), {p.key for p in COERCIVE})
        self.assertEqual(pms("resettlement_state_runs_voluntary"), set(VOLUNTARY))
        self.assertEqual(set(VOLUNTARY) | {p.key for p in COERCIVE} | {"managed_retreat"}, set(PROGRAMME_KEYS))

    def test_month_counters_cover_every_programme(self):
        text = read(EFFECTS)
        reset = squash(block(text, "resettlement_reset_month_counters"))
        count = squash(block(text, "resettlement_count_programme_month"))
        for p in PROGRAMMES:
            self.assertIn(f"set_variable = {{ name = rs_month_{p.key} value = 0 }}", reset, p.key)
            self.assertIn(f"resettlement_count_one = {{ CODE = {p.code} PROG = {p.key} }}", count, p.key)

    def test_caps_and_minimum(self):
        text = strip_comments(read(VALUES))
        self.assertRegex(text, r"(?m)^resettlement_pop_cap = 0\.02\s*$")
        self.assertRegex(text, r"(?m)^resettlement_drive_pop_cap = 0\.04\s*$")
        self.assertRegex(text, r"(?m)^resettlement_min_take = 100\s*$")

    def test_walk_takes_drive_states_first(self):
        body = squash(block(read(EFFECTS), "resettlement_run_destination"))
        drive = body.index("has_decree = decree_resettlement_recruitment_drive")
        rest = body.index("NOT = { has_decree = decree_resettlement_recruitment_drive }")
        self.assertLess(drive, rest)
        self.assertIn("CAP = resettlement_drive_pop_cap", body[drive:rest])
        self.assertIn("CAP = resettlement_pop_cap", body[rest:])

    def test_capacity_is_the_modifier_and_never_negative(self):
        body = squash(block(read(EFFECTS), "resettlement_run_destination"))
        self.assertIn("set_variable = { name = rs_remaining value = modifier:state_resettlement_transfer_add }", body)
        self.assertIn("limit = { var:rs_remaining < 0 } set_variable = { name = rs_remaining value = 0 }", body)
        # Review Focus 5: the program code is re-read from the active PM every month.
        self.assertIn("resettlement_set_programme_code = yes", body)

    def test_every_take_is_guarded(self):
        body = squash(block(read(EFFECTS), "resettlement_take_from_source"))
        self.assertIn("scope:rs_destination.var:rs_remaining >= resettlement_min_take", body)
        self.assertIn("local_var:rs_take >= resettlement_min_take", body)
        self.assertIn("move_partial_pop = { state = scope:rs_destination population = { value = local_var:rs_move } }", body)

    def test_deaths_in_steps_of_one_hundred_for_each_coercive_programme(self):
        body = squash(block(read(EFFECTS), "resettlement_source_consequences"))
        kills = re.findall(r"while = \{ count = local_var:rs_dead_steps kill_population_in_state = \{ value = 100 (\w+ = \w+) \} \}", body)
        self.assertEqual(sorted(kills), ["pop_type = farmers", "pop_type = laborers", "strata = lower"])
        for p in COERCIVE:
            self.assertIn(f"scope:rs_destination.var:rs_programme = {p.code}", body, p.key)

    def test_land_pressure_is_only_a_cost(self):
        body = squash(block(read(EFFECTS), "resettlement_land_pressure"))
        self.assertIn("EFFECT = add_radicals_in_state VALUE = resettlement_land_pressure_share", body)
        self.assertNotIn("loyalists", body)
        touch = squash(block(read(EFFECTS), "resettlement_touch_pressed_cultures"))
        self.assertIn("pop_acceptance < acceptance_status_4", touch)
        self.assertIn("is_target_in_variable_list", touch)

    def test_readouts(self):
        mods = read(RS_MODIFIERS)
        types = read(MODIFIER_TYPES)
        L = loc()
        for modifier, mtype, _ in READOUTS:
            self.assertEqual(number(block(mods, modifier), mtype), 1, modifier)
            tbody = block(types, mtype)
            self.assertIsNotNone(tbody, mtype)
            self.assertEqual(number(tbody, "decimals"), 0, mtype)
            for key in (modifier, f"{modifier}_desc", mtype, f"{mtype}_desc"):
                self.assertIn(key, L)
        effects = read(EFFECTS)
        dest = squash(block(effects, "resettlement_refresh_destination_readout"))
        self.assertIn("add_modifier = { name = resettlement_arrivals multiplier = var:rs_arrivals }", dest)
        self.assertIn("add_modifier = { name = resettlement_transit_deaths multiplier = var:rs_deaths }", dest)
        src = squash(block(effects, "resettlement_refresh_source_readout"))
        self.assertIn("add_modifier = { name = resettlement_recruits multiplier = var:rs_recruits }", src)

    def test_the_pulse_is_wired(self):
        text = read(RS_ON_ACTIONS)
        m = re.search(r"on_monthly_pulse_country\s*=\s*\{\s*on_actions\s*=\s*\{([^}]*)\}", text)
        self.assertIsNotNone(m)
        self.assertIn("resettlement_country_on_action", m.group(1))
        self.assertIn("resettlement_country_monthly = yes", squash(block(text, "resettlement_country_on_action")))

    def test_closure_removes_the_building_and_tells_the_owner(self):
        body = squash(block(read(EFFECTS), "resettlement_close_frontier"))
        self.assertIn("remove_building = building_resettlement_colony", body)
        self.assertIn("trigger_event = { id = resettlement.9 }", body)
        self.assertIsNotNone(block(read(RS_EVENTS), "resettlement.9"))
        monthly = squash(block(read(EFFECTS), "resettlement_country_monthly"))
        self.assertIn("limit = { resettlement_state_frontier_still_open = no } resettlement_close_frontier = yes", monthly)

    def test_the_drive_decree(self):
        body = block(read(DECREES), "decree_resettlement_recruitment_drive")
        self.assertIsNotNone(body)
        self.assertIn("has_building = building_resettlement_colony", squash(block(body, "country_trigger")))
        for key in ("decree_resettlement_recruitment_drive", "decree_resettlement_recruitment_drive_desc",
                    "decree_resettlement_recruitment_drive_needs_authority_tt"):
            self.assertIn(key, loc())


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


UN_REGISTRY = "test_un_convention_registry.py"


class PoliticsTests(unittest.TestCase):
    def test_constants(self):
        text = strip_comments(read(VALUES))
        self.assertRegex(text, r"(?m)^resettlement_volume_decay = 0\.9167\s*$")
        self.assertRegex(text, r"(?m)^resettlement_intensity_reference = 0\.0025\s*$")

    def test_each_politics_modifier_is_the_table(self):
        mods = read(RS_MODIFIERS)
        for p in PROGRAMMES:
            body = block(mods, f"resettlement_{p.key}_politics")
            if not p.politics:
                self.assertIsNone(body, p.key)
                continue
            found = {k: float(v) for k, v in re.findall(r"(interest_group_\w+_approval_add)\s*=\s*(-?[\d.]+)", body)}
            self.assertEqual(found, {k: float(v) for k, v in p.politics.items()}, p.key)
            self.assertIn(f"resettlement_{p.key}_politics", loc())
            self.assertIn(f"resettlement_{p.key}_politics_desc", loc())

    def test_magnitudes_stay_within_a_major_law_change(self):
        # A running program is an ongoing action: its scale is vanilla's approval
        # from changing a law (5 / 10 / 20), not the ±5 clamp on laws on the books.
        for p in WITH_POLITICS:
            for key, value in p.politics.items():
                self.assertLessEqual(value, 3, (p.key, key))
                self.assertGreaterEqual(value, -10, (p.key, key))

    def test_refresh_covers_every_programme_with_politics(self):
        body = squash(block(read(EFFECTS), "resettlement_refresh_politics"))
        called = re.findall(r"resettlement_refresh_programme_politics = \{ PROG = (\w+) \}", body)
        self.assertEqual(called, [p.key for p in WITH_POLITICS])

    def test_one_modifier_per_programme_scaled_by_intensity(self):
        body = squash(block(read(EFFECTS), "resettlement_refresh_programme_politics"))
        self.assertIn("change_variable = { name = rs_volume_$PROG$ multiply = resettlement_volume_decay }", body)
        self.assertIn("change_variable = { name = rs_volume_$PROG$ add = var:rs_month_$PROG$ }", body)
        self.assertIn("add_modifier = { name = resettlement_$PROG$_politics multiplier = var:rs_intensity_$PROG$ }", body)
        self.assertIn("max = 1", body)

    def test_the_pulse_keeps_running_while_reactions_fade(self):
        fading = squash(block(read(TRIGGERS), "resettlement_country_still_fading"))
        for p in WITH_POLITICS:
            self.assertIn(f"var:rs_volume_{p.key} > 1", fading, p.key)
        self.assertIn("has_variable = rs_active", squash(block(read(RS_ON_ACTIONS), "resettlement_country_on_action")))


class DeclarationTests(unittest.TestCase):
    def test_party_reads_the_conventions_member_and_reservations_modifiers(self):
        body = squash(block(read(TRIGGERS), "resettlement_is_declaration_party"))
        self.assertIn("je:je_united_nations ?= { has_modifier = un_human_rights_declaration_modifier }", body)
        self.assertIn("has_modifier = un_human_rights_reservations_modifier", body)

    def test_intensity_sums_the_coercive_programmes_and_halves_under_reservations(self):
        body = squash(block(read(EFFECTS), "resettlement_refresh_declaration"))
        summed = set(re.findall(r"var:rs_intensity_(\w+)", body))
        self.assertEqual(summed, {p.key for p in COERCIVE})
        self.assertIn("change_variable = { name = rs_declaration_intensity multiply = 0.5 }", body)
        self.assertIn("add_modifier = { name = resettlement_declaration_violation multiplier = var:rs_declaration_intensity }", body)
        self.assertIn("trigger_event = { id = resettlement.20 }", body)

    def test_the_violation_modifier(self):
        body = block(read(RS_MODIFIERS), "resettlement_declaration_violation")
        self.assertEqual(number(body, "country_prestige_mult"), -0.1)
        L = loc()
        self.assertIn("resettlement_declaration_violation", L)
        self.assertIn("resettlement_declaration_violation_desc", L)

    def test_communicated_at_every_step(self):
        L = loc()
        # 1. before choosing: TestProgramme.test_the_declaration_line_is_on_coercive_programmes_only
        # 2. when it starts: resettlement.20, whose second option ends the programmes
        event = block(read(RS_EVENTS), "resettlement.20")
        self.assertIsNotNone(event)
        options = re.findall(r"option\s*=\s*\{", strip_comments(event))
        self.assertEqual(len(options), 2)
        self.assertIn("resettlement_end_coercive_programmes = yes", squash(event))
        for suffix in ("t", "d", "f", "a", "b"):
            self.assertIn(f"resettlement.20.{suffix}", L)
        # 3. while it runs: the modifier's description (test_the_violation_modifier)
        # 4. at the vote: the proposal, the vote and the member modifier say so
        for key in ("un_events.3.d", "un_vote.1.d_human_rights", "un_human_rights_declaration_modifier_desc"):
            self.assertIn("resettlement", L[key].lower(), key)

    def test_the_un_registry_names_it(self):
        self.assertRegex(read(UN_REGISTRY), r'violation_modifiers=\("resettlement_declaration_violation",\)')


# ---- The program events (Task 6) -------------------------------------------------

# id: (image kind, number of options)
EVENTS = {
    1: ("video", 2), 2: ("video", 2), 3: ("video", 2), 4: ("texture", 2),
    5: ("video", 2), 6: ("video", 2), 7: ("video", 2), 8: ("video", 2),
    9: ("video", 1), 20: ("texture", 2),
}
ROLLED = (1, 2, 3, 4, 5, 6, 7, 8)


def event(n):
    return block(read(RS_EVENTS), f"resettlement.{n}")


def options(body):
    text = strip_comments(body)
    out = []
    for m in re.finditer(r"(?<![\w])option\s*=\s*\{", text):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        out.append(text[m.end():i - 1])
    return out


class EventTests(unittest.TestCase):
    def test_every_event_has_image_placement_options_and_loc(self):
        L = loc()
        for n, (kind, count) in EVENTS.items():
            body = event(n)
            self.assertIsNotNone(body, n)
            self.assertIn(f"{kind} =", block(body, "event_image"), n)
            self.assertIn("placement =", body, n)
            opts = options(body)
            self.assertEqual(len(opts), count, n)
            for suffix in ("t", "d", "f"):
                self.assertIn(f"resettlement.{n}.{suffix}", L, n)
            for opt in opts:
                name = re.search(r"name\s*=\s*([\w.]+)", opt).group(1)
                self.assertIn(name, L, n)

    def test_the_roll_offers_each_programme_event_once(self):
        body = squash(block(read(EFFECTS), "resettlement_roll_events"))
        rolled = [int(n) for n in re.findall(r"trigger_event = \{ id = resettlement\.(\d+) \}", body)]
        self.assertEqual(sorted(rolled), list(ROLLED))
        self.assertIn("resettlement_system_enabled = yes", body)
        self.assertIn("NOT = { has_variable = rs_event_cooldown }", body)
        self.assertIn("resettlement_roll_events = yes", squash(block(read(EFFECTS), "resettlement_country_monthly")))

    def test_once_only_events_mark_their_state(self):
        roll = squash(block(read(EFFECTS), "resettlement_roll_events"))
        for n, flag in ((4, "rs_dust_done"), (7, "rs_petition_done")):
            self.assertIn(f"set_variable = {flag}", squash(block(event(n), "immediate")), n)
            self.assertIn(f"NOT = {{ has_variable = {flag} }}", roll, n)

    def test_land_disputes_rewards_nothing(self):
        negotiate, back = options(event(8))
        for opt in (negotiate, back):
            self.assertNotIn("approval", opt)
            self.assertNotIn("_positive_", opt)
        self.assertIn("EFFECT = add_radicals_in_state", squash(back))
        self.assertNotIn("add_modifier", back)

    def test_event_modifiers_are_localized(self):
        mods = read(RS_MODIFIERS)
        L = loc()
        for name in ("resettlement_land_rush", "resettlement_orderly_survey", "resettlement_land_office_crackdown",
                     "resettlement_speculators", "resettlement_hard_winter", "resettlement_soil_conservation",
                     "resettlement_dust_bowl", "resettlement_reformed", "resettlement_defiant",
                     "resettlement_reserves", "resettlement_negotiation_cost"):
            self.assertIsNotNone(block(mods, name), name)
            self.assertIn(name, L)
            self.assertIn(f"{name}_desc", L)


# ---- the console test event (Task 7) --------------------------------------------------

DEBUG_EVENTS = "events/te_debug_resettlement_events.txt"


class DebugTests(unittest.TestCase):
    def test_console_event(self):
        text = read(DEBUG_EVENTS)
        self.assertRegex(text, r"(?m)^te_debug_resettlement\.1 = \{ # REVIEWED \d{4}-\d{2}-\d{2}: console-only")
        body = block(text, "te_debug_resettlement.1")
        self.assertEqual(len(options(body)), 4)
        flat = squash(body)
        for call in ("create_building = { building = building_resettlement_colony level = 5 }",
                     "resettlement_country_monthly = yes", "resettlement_close_frontier = yes",
                     "TE_RESETTLEMENT:"):
            self.assertIn(call, flat)
        L = loc()
        for suffix in ("t", "desc", "flavor", "a", "b", "c", "d"):
            self.assertIn(f"te_debug_resettlement.1.{suffix}", L)


if __name__ == "__main__":
    unittest.main()
