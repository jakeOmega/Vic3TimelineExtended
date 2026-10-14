"""Grand Monument archaeology (issue #939): the buried sites, the gate that opens
them, the dig, and what a finished dig hands to the monument machinery, pinned
against the landmark registry.

Design: docs/superpowers/specs/2026-10-14-grand-monument-archaeology-design.md.
A buried site is a LANDMARKS row with buried=True (test_grand_monument_registry.py)
plus a row of ARCH_SITES here: the technology that opens it and how it is found.
Adding a site is a row in each, and the failures name every other place.

Run: python3 -m unittest test_grand_monument_archaeology -v
"""
import json
import math
import re
import unittest
from collections import namedtuple

from test_grand_monument_registry import (
    LANDMARKS, ROOT, block, loc, raw_block_at, read, squash, strip_comments,
)

EFFECTS = "common/scripted_effects/gm_archaeology_effects.txt"
TRIGGERS = "common/scripted_triggers/gm_archaeology_triggers.txt"
GATE = "common/scripted_triggers/gm_archaeology_gate_triggers.txt"
VALUES = "common/script_values/gm_archaeology_values.txt"
SGUIS = "common/scripted_guis/gm_archaeology_sguis.txt"
ON_ACTIONS = "common/on_actions/gm_archaeology_on_actions.txt"
MODIFIERS = "common/static_modifiers/gm_archaeology_modifiers.txt"
CUSTOM_LOC = "common/customizable_localization/gm_archaeology_custom_loc.txt"
EVENTS = "events/archaeology_events.txt"
DEBUG_EVENTS = "events/te_debug_monuments_events.txt"
GUI = "gui/gm_archaeology_widgets.gui"
WIDGET = "gui/journal_entry_widgets/grand_monuments_widget.gui"
JE = "common/journal_entries/je_grand_monuments.txt"
GM_EFFECTS = "common/scripted_effects/gm_effects.txt"
MON_TRIGGERS = "common/scripted_triggers/monument_triggers.txt"
TR_CUSTOM_LOC = "common/customizable_localization/gm_trophy_custom_loc.txt"

Site = namedtuple("Site", "key tech vector")
# key, the technology that opens it (as the table writes it), and how it is
# found: `survey` (open as soon as its owner has the technology) or
# `incidental` (turned up by a monthly chance). In LANDMARKS order. Era
# technologies stand for their dates: the issue's years, mapped to the
# technology of the period (spec § The sites).
ARCH_SITES = (
    Site("nineveh_library", "romanticism", "survey"),
    Site("winged_victory_of_samothrace", "romanticism", "survey"),
    Site("vindolanda_tablets", "empiricism", "incidental"),
    Site("troy_hisarlik", "empiricism", "survey"),
    Site("mycenae_grave_circle", "empiricism", "survey"),
    Site("pergamon_altar", "empiricism", "survey"),
    Site("deir_el_bahari_cache", "empiricism", "incidental"),
    Site("ishtar_gate_babylon", "civilizing_mission", "survey"),
    Site("palace_of_knossos", "pan-nationalism", "survey"),
    Site("antikythera_mechanism", "steam_donkey", "incidental"),
    Site("oseberg_ship", "pan-nationalism", "incidental"),
    Site("machu_picchu", "mass_propaganda", "survey"),
    Site("bust_of_nefertiti", "mass_propaganda", "survey"),
    Site("mohenjo_daro", "modern_materials", "incidental"),
    Site("tomb_of_tutankhamun", "mass_media", "survey"),
    Site("royal_cemetery_at_ur", "mass_media", "survey"),
    Site("sanxingdui_pits", "public_works_programs", "incidental"),
    Site("sutton_hoo", "combined_arms", "incidental"),
    Site("lascaux_caves", "public_works_programs", "incidental"),
    Site("nag_hammadi_library", "nuclear_energy", "incidental"),
    Site("dead_sea_scrolls", "jet_engine_technology", "incidental"),
    Site("tomb_of_pakal", "television_broadcasting", "survey"),
    Site("mawangdui_tombs", "modern_pharmaceuticals", "incidental"),
    Site("terracotta_army", "containerization", "incidental"),
    Site("tomb_of_philip_ii", "microprocessor", "survey"),
    Site("tomb_of_marquis_yi", "barcodes_and_scanners", "incidental"),
    Site("royal_tombs_of_sipan", "personal_computers", "incidental"),
    Site("otzi_the_iceman", "world_wide_web", "incidental"),
    Site("caral_supe", "digital_telecommunications", "survey"),
    Site("gobekli_tepe", "e-commerce", "survey"),
    Site("olympia", "empiricism", "survey"),
    Site("delphi", "civilizing_mission", "survey"),
    Site("sidon_necropolis", "empiricism", "survey"),
    Site("villa_of_the_papyri", "microprocessor", "survey"),
    Site("tomb_of_alexander", "mainframe_computers", "survey"),
)
BURIED = tuple(lm for lm in LANDMARKS if lm.buried)
METHODS = {"antiquarian": ("romanticism", 4), "systematic": ("empiricism", 2.5), "forensic": ("computer_networks", 3.5)}


def flag(tech):
    """A technology as a site stores it: the hyphen an underscore."""
    return tech.replace("-", "_")


def technologies():
    names = set(json.loads((ROOT / "vanilla_parsed/common/technologies.json").read_text(encoding="utf-8")))
    for p in (ROOT / "common/technology/technologies").glob("*.txt"):
        names |= set(re.findall(r"(?m)^([a-z0-9_-]+)\s*=\s*\{", p.read_text(encoding="utf-8-sig")))
    return names


def state_regions():
    out = set()
    for p in (ROOT / "map_data/state_regions").glob("*.txt"):
        out |= set(re.findall(r"(?m)^(STATE_[A-Z0-9_]+)\s*=\s*\{", p.read_text(encoding="utf-8-sig")))
    return out


def seed_call(lm, site):
    return (f"gm_arch_seed_site = {{ KEY = {lm.key} STATE = {lm.state} TECH = {flag(site.tech)} "
            f"VECTOR = {site.vector} FORM = {lm.form} LEVEL = {lm.level} }}")


class TableTests(unittest.TestCase):
    def test_a_row_for_every_buried_landmark_in_order(self):
        self.assertEqual([s.key for s in ARCH_SITES], [lm.key for lm in BURIED])
        self.assertEqual(len(ARCH_SITES), 35)

    def test_what_a_site_is(self):
        states, techs = state_regions(), technologies()
        self.assertGreater(len(states), 700)
        self.assertGreater(len(techs), 300)
        for lm, site in zip(BURIED, ARCH_SITES):
            self.assertFalse(lm.placed, lm.key)
            self.assertIn(lm.state, states, f"{lm.key}: a state region that exists")
            self.assertIn(site.tech, techs, f"{lm.key}: a technology that exists")
            self.assertIn(site.vector, ("survey", "incidental"), lm.key)
            self.assertEqual(lm.dedication, "civic", f"{lm.key}: the antiquity and archive dedications are deferred")
            self.assertIsNone(lm.tag, lm.key)

    def test_the_picture_codes_follow_the_rows(self):
        first = LANDMARKS.index(BURIED[0]) + 1
        self.assertEqual(first, 52, "append-only: the first buried site is row 52")
        self.assertEqual(len(LANDMARKS), 51 + len(BURIED))

    def test_the_issues_candidates_are_all_there(self):
        # Issue #939's list: the sites it names, by the key this table gives them.
        wanted = {"pergamon_altar", "ishtar_gate_babylon", "nineveh_library", "sidon_necropolis", "troy_hisarlik",
                  "olympia", "delphi", "mycenae_grave_circle", "palace_of_knossos", "bust_of_nefertiti",
                  "tomb_of_tutankhamun", "machu_picchu", "mohenjo_daro", "terracotta_army"}
        self.assertEqual(wanted - {lm.key for lm in BURIED}, set())


class SeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = read(EFFECTS)

    def test_a_call_per_row(self):
        raw = (ROOT / EFFECTS).read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "one BOM")
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf" * 2), "one BOM, not two")
        body = squash(block(self.e, "gm_arch_seed_sites"))
        self.assertEqual(re.findall(r"gm_arch_seed_site = \{[^{}]*\}", body),
                         [seed_call(lm, s) for lm, s in zip(BURIED, ARCH_SITES)])

    def test_the_seed_writes_the_records(self):
        body = squash(block(self.e, "gm_arch_seed_site"))
        self.assertIn("create_container = { tags = { gm_site } save_scope_as = gm_arch_new", body,
                      "no parent: it outlives every country")
        self.assertNotIn("parent =", body)
        self.assertNotIn("random_country", body, "no wrapper: no other global store has one")
        self.assertIn("s:$STATE$ = { save_scope_as = gm_arch_seed_region }", body,
                      "the region is saved first, as every stored region is")
        self.assertIn("add_to_global_variable_list = { name = gm_arch_sites target = scope:gm_arch_new }", body)
        for record in ("name = gm_tr_landmark value = flag:$KEY$", "name = gm_tr_skin value = flag:landmark_$KEY$",
                       "name = gm_tr_form value = flag:$FORM$", "name = gm_tr_levels value = $LEVEL$",
                       "name = gm_tr_dedication value = flag:civic", "name = gm_tr_namesake value = flag:landmark",
                       "name = gm_tr_share value = flag:whole", "name = gm_tr_origin_region value = scope:gm_arch_seed_region",
                       "name = gm_site_tech value = flag:$TECH$", "name = gm_site_vector value = flag:$VECTOR$",
                       "name = gm_site_status value = 1"):
            self.assertIn(f"set_variable = {{ {record} }}", body, record)
        self.assertIn("var:gm_tr_landmark = flag:$KEY$", body, "never twice")
        # Nor a site already dug: it has left the list for a state, the secondaries or the trophies.
        for lst in ("gm_monuments", "gm_trophies"):
            self.assertIn(f"has_global_variable_list = {lst} any_in_global_list = {{ variable = {lst} "
                          "has_variable = gm_tr_landmark var:gm_tr_landmark = flag:$KEY$", body, lst)
        self.assertIn("any_state = { has_variable = gm_landmark var:gm_landmark = flag:$KEY$ }", body)

    def test_the_self_check_logs_only_with_its_premise(self):
        body = squash(block(self.e, "gm_arch_self_check"))
        self.assertIn("var:gm_tr_landmark = flag:nineveh_library", body)
        self.assertIn("limit = { exists = scope:gm_arch_chk }", body, "nothing logged with the site absent")
        self.assertIn("any_scope_state = { always = yes }", body)
        self.assertIn("TE_SELF_CHECK OK archaeology_site_region", body)
        self.assertIn("TE_SELF_CHECK BROKEN archaeology_site_region", body)
        self.assertIn("gm_arch_seed_sites = yes gm_arch_self_check = yes", squash(block(self.e, "gm_arch_monthly")))
        self.assertIn("archaeology_site_region", read("docs/testing/grand-monuments-archaeology-playtest.md"))

    def test_seeded_once_from_the_monthly_pass(self):
        body = squash(block(self.e, "gm_arch_monthly"))
        self.assertTrue(body.startswith("if = { limit = { gm_system_enabled = yes } if = { limit = { NOT = { "
                                        "has_global_variable = gm_arch_seeded } } set_global_variable = "
                                        "gm_arch_seeded gm_arch_seed_sites = yes gm_arch_self_check = yes }"), body[:300])
        on = squash(strip_comments(read(ON_ACTIONS)))
        self.assertIn("on_monthly_pulse = { on_actions = { gm_arch_monthly_on_action } }", on)
        self.assertIn("gm_arch_monthly_on_action = { effect = { gm_arch_monthly = yes } }", on)

    def test_no_timed_variable_on_a_container(self):
        # container_timed_variable_audit's rule, held here for the file as a whole.
        self.assertNotRegex(strip_comments(self.e), r"set_variable = \{[^{}]*\bdays\s*=")


class GateTests(unittest.TestCase):
    def test_a_branch_per_technology(self):
        body = squash(block(read(GATE), "gm_arch_has_gate_for"))
        found = re.findall(r"AND = \{ var:gm_site_tech = flag:(\w+) \$WHO\$ = \{ has_technology_researched = "
                           r"([\w-]+) \} \}", body)
        techs = []
        for s in ARCH_SITES:
            if s.tech not in techs:
                techs.append(s.tech)
        self.assertEqual(found, [(flag(t), t) for t in techs])

    def test_the_gate_is_read_from_the_sites_side_with_no_saved_scope(self):
        # A saved scope a trigger writes can be shadowed by one an effect left
        # set under the same name (the AI's start ran after the pass): the gate
        # takes the country as its argument instead, and the callers save theirs
        # under a name nothing else saves, as a temporary scope.
        gate = read(GATE)
        self.assertNotIn("save_temporary_scope_as", strip_comments(gate))
        self.assertNotIn("gm_arch_has_gate_for", strip_comments(read(TRIGGERS)).split("gm_arch_can_dig = {")[0])
        everything = strip_comments(read(EFFECTS) + read(TRIGGERS) + gate)
        self.assertNotIn("gm_arch_gate_site", everything)
        self.assertNotIn("gm_arch_country_has_gate", everything)
        for name in ("gm_arch_try_find", "gm_arch_list_one"):
            body = squash(block(read(EFFECTS), name))
            self.assertIn("owner = { save_temporary_scope_as = gm_arch_cand }", body, name)
            self.assertIn("gm_arch_has_gate_for = { WHO = scope:gm_arch_cand }", body, name)
        self.assertNotIn("scope:gm_arch_cand", squash(block(read(EFFECTS), "gm_arch_ai_decide")))
        self.assertNotRegex(read(EFFECTS), r"(?m)^\s*save_scope_as = gm_arch_cand")

    def test_who_may_dig(self):
        t = read(TRIGGERS)
        self.assertEqual(squash(block(t, "gm_arch_owns_ground")),
                         "var:gm_tr_origin_region ?= { any_scope_state = { owner = $WHO$ } }")
        can = squash(block(t, "gm_arch_can_dig"))
        for part in ("gm_system_enabled = yes", "has_tag = gm_site", "gm_arch_site_open = yes",
                     "gm_arch_owns_ground = { WHO = $WHO$ }", "gm_arch_has_gate_for = { WHO = $WHO$ }"):
            self.assertIn(part, can)
        opened = squash(block(t, "gm_arch_site_open"))
        self.assertIn("var:gm_site_status = 2", opened, "a site turned up")
        self.assertIn("var:gm_site_status = 1 var:gm_site_vector = flag:survey", opened,
                      "a survey site is open as soon as it is buried; an incidental one only when found")

    def test_each_method_asks_for_its_technology(self):
        t = read(TRIGGERS)
        for method, (tech, _rate) in METHODS.items():
            self.assertEqual(squash(block(t, f"gm_arch_method_{method}_ok")),
                             f"has_technology_researched = {tech}", method)


class DigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = read(EFFECTS)
        cls.v = read(VALUES)

    def test_the_rates_make_25_40_and_29_months(self):
        for method, (_tech, rate) in METHODS.items():
            self.assertEqual(squash(block(self.v, f"gm_arch_rate_{method}")), f"value = {rate:g}", method)
        self.assertEqual([math.ceil(100 / rate) for _t, rate in METHODS.values()], [25, 40, 29])

    def test_a_month_of_progress(self):
        body = squash(block(self.e, "gm_arch_dig_step"))
        for method in METHODS:
            self.assertIn(f"change_variable = {{ name = gm_site_progress add = gm_arch_rate_{method} }}", body)
        self.assertIn("clamp_variable = { name = gm_site_progress max = 100 min = 0 }", body)
        self.assertIn("var:gm_site_progress >= 100 } add_to_temporary_list = gm_arch_done", body,
                      "finished after the walk over the list, not in it")
        self.assertIn("} else = { gm_arch_suspend = yes }", body, "a sponsor with no ground left suspends it")
        monthly = squash(block(self.e, "gm_arch_monthly"))
        self.assertLess(monthly.index("gm_arch_site_monthly = yes"), monthly.index("list = gm_arch_done"))
        self.assertLess(monthly.index("list = gm_arch_done"), monthly.index("gm_arch_pass = yes"))

    def test_a_suspended_dig_keeps_its_progress(self):
        body = squash(block(self.e, "gm_arch_suspend"))
        self.assertEqual(body, "set_variable = { name = gm_site_status value = 2 } remove_variable = gm_site_sponsor")
        begin = squash(block(self.e, "gm_arch_begin_dig"))
        self.assertIn("limit = { NOT = { has_variable = gm_site_progress } } set_variable = { name = "
                      "gm_site_progress value = 0 }", begin)

    def test_the_method_decides_what_it_makes_of_the_site(self):
        body = squash(block(self.e, "gm_arch_settle_levels"))
        self.assertIn("var:gm_site_method = flag:forensic } change_variable = { name = gm_tr_levels add = "
                      "gm_arch_forensic_bonus }", body)
        self.assertIn("random = { chance = gm_arch_destruction_chance set_variable = gm_arch_ruined", body)
        self.assertIn("divide = 2 ceiling = yes min = 3", body, "half, at least 3")
        self.assertEqual(squash(block(self.v, "gm_arch_destruction_chance")), "value = 35")
        self.assertEqual(squash(block(self.v, "gm_arch_forensic_bonus")), "value = 2")

    def test_only_antiquarian_risks_destruction(self):
        body = squash(block(self.e, "gm_arch_settle_levels"))
        self.assertIn("else_if = { limit = { var:gm_site_method = flag:antiquarian } random =", body)

    def test_an_incidental_site_is_turned_up_by_a_chance(self):
        body = squash(block(self.e, "gm_arch_try_find"))
        self.assertIn("gm_arch_has_gate_for = { WHO = scope:gm_arch_cand }", body)
        self.assertIn("random = { chance = gm_arch_find_chance gm_arch_found = yes }", body)
        monthly = squash(block(self.e, "gm_arch_site_monthly"))
        self.assertIn("var:gm_site_status = 1 var:gm_site_vector = flag:incidental } gm_arch_try_find = yes", monthly)
        self.assertEqual(squash(block(self.v, "gm_arch_find_chance")), "value = 1")


class PlacingTests(unittest.TestCase):
    """A finished dig hands the monument to the machinery trophies already use."""

    @classmethod
    def setUpClass(cls):
        cls.e = read(EFFECTS)

    def test_it_stands_in_the_sponsors_part(self):
        body = squash(block(self.e, "gm_arch_finish"))
        self.assertIn("limit = { owner = scope:gm_arch_sponsor } save_scope_as = gm_arch_dig_state", body)
        self.assertIn("gm_arch_settle_levels = yes gm_arch_place = yes", body)

    def test_the_records_a_return_reads(self):
        body = squash(block(self.e, "gm_arch_place"))
        self.assertTrue(body.startswith("save_scope_as = gm_tr_moving"), "the name the machinery reads")
        for record in ("name = gm_site_status value = 4", "name = gm_tr_origin value = scope:gm_arch_dig_state",
                       "name = gm_tr_site value = scope:gm_arch_dig_state",
                       "name = gm_tr_site_region value = var:gm_tr_origin_region", "name = gm_tr_year value = gm_this_year"):
            self.assertIn(f"set_variable = {{ {record} }}", body, record)
        self.assertIn("gm_tr_update_picture = yes", body)

    def test_none_standing_builds_it_and_one_standing_puts_it_beside(self):
        body = squash(block(self.e, "gm_arch_place"))
        self.assertIn("limit = { scope:gm_arch_dig_state = { has_building = building_grand_monument } } "
                      "gm_arch_stand_beside = yes } else = { scope:gm_arch_dig_state = { gm_state_tr_receive = yes } "
                      "gm_arch_retire = yes }", body)

    def test_a_player_is_told_before_the_container_may_go(self):
        body = squash(block(self.e, "gm_arch_place"))
        self.assertLess(body.index("trigger_event = { id = arch_events.3 }"), body.index("gm_arch_retire = yes"))
        self.assertLess(body.index("trigger_event = { id = arch_events.2 }"), body.index("gm_arch_retire = yes"))
        self.assertIn("name = gm_arch_last value = scope:gm_tr_moving.var:gm_tr_landmark", body)

    def test_beside_is_a_retag_and_the_lists_a_seeded_landmark_beside_uses(self):
        body = squash(block(self.e, "gm_arch_stand_beside"))
        self.assertIn("remove_list_global_variable = { name = gm_arch_sites target = scope:gm_tr_moving }", body)
        self.assertIn("add_to_global_variable_list = { name = gm_monuments target = scope:gm_tr_moving }", body)
        self.assertIn("remove_tag = gm_site add_tag = gm_monument", body)
        self.assertIn("gm_state_tr_add_levels = yes", body)
        self.assertIn("add_to_variable_list = { name = gm_monuments_here target = scope:gm_tr_moving }", body)
        self.assertIn("add_to_variable_list = { name = gm_monuments_held target = scope:gm_tr_moving }", body)
        # The same lists, in the same order, as the landmark seeded beside another.
        seeded = squash(block(read("common/scripted_effects/gm_monument_effects.txt"), "gm_seed_landmark_beside"))
        for line in ("gm_state_tr_add_levels = yes", "add_to_variable_list = { name = gm_monuments_here",
                     "add_to_variable_list = { name = gm_monuments_held", "set_variable = gm_mon_listed"):
            self.assertIn(line, seeded)
            self.assertIn(line, body)

    def test_the_container_is_taken_off_the_list_before_it_goes(self):
        body = squash(block(self.e, "gm_arch_retire"))
        self.assertEqual(body, "remove_list_global_variable = { name = gm_arch_sites target = scope:gm_tr_moving } "
                               "destroy_container = yes")

    def test_a_site_names_itself_as_a_trophy_does(self):
        names = [flag_ for flag_, _ in re.findall(r"flag:(\w+) \}\s*localization_key = (\w+)",
                                                  block(read(TR_CUSTOM_LOC), "gm_tr_landmark_name"))]
        for lm in BURIED:
            self.assertIn(lm.key, names, f"{lm.key}: gm_tr_landmark_name names the site's row")


class NamesTests(unittest.TestCase):
    def test_the_event_names_follow_the_rows(self):
        body = squash(block(read(CUSTOM_LOC), "gm_arch_site_name"))
        self.assertTrue(body.startswith("type = country random_valid = no"))
        branches = re.findall(r"var:gm_arch_last = flag:(\w+) \} localization_key = (\w+)", body)
        self.assertEqual(branches, [(lm.key, f"gm_landmark_{lm.key}_evt") for lm in BURIED])
        self.assertTrue(body.endswith("text = { localization_key = gm_arch_site_name_none }"))
        L = loc()
        for _, key in branches:
            self.assertIn(key, L)

    def test_the_method_names(self):
        body = squash(block(read(CUSTOM_LOC), "gm_arch_method_name"))
        self.assertEqual(re.findall(r"flag:(\w+) \} localization_key = (\w+)", body),
                         [(m, f"gm_arch_method_{m}") for m in METHODS])
        L = loc()
        for m in (*METHODS, "none"):
            self.assertIn(f"gm_arch_method_{m}", L)


class BrakeTests(unittest.TestCase):
    def test_innovation_falls_weekly_and_the_cap_does_not(self):
        body = squash(strip_comments(read(MODIFIERS)))
        self.assertIn("gm_arch_diversion = { icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_negative.dds "
                      "country_weekly_innovation_add = -1 }", body)
        self.assertNotIn("innovation_max", body, "the cap is never touched (owner, 2026-10-14)")
        self.assertIn("gm_arch_expense = { icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_negative.dds "
                      "country_expenses_add = 1 country_te_budget_expense_archaeology_add = 1 }", body,
                      "a recurring monetary modifier joins a Budget Breakdown category (test_budget_breakdown.py)")
        gen = read("scripts/generators/gen_budget_breakdown.py")
        self.assertIn('"archaeology": ("Archaeological Digs", ("gm_arch_expense",)),', gen)

    def test_the_methods_cost_what_the_spec_says(self):
        v = read(VALUES)
        for method, units in (("antiquarian", 5), ("systematic", 15), ("forensic", 30)):
            self.assertEqual(squash(block(v, f"gm_arch_innovation_{method}")), f"value = {units}", method)
        self.assertEqual(squash(block(v, "gm_arch_cost_base")), "value = gdp multiply = 0.0002 min = 100")
        self.assertEqual(squash(block(v, "gm_arch_cost_antiquarian")), "value = gm_arch_cost_base")
        self.assertEqual(squash(block(v, "gm_arch_cost_systematic")), "value = gm_arch_cost_base multiply = 2.5")
        self.assertEqual(squash(block(v, "gm_arch_cost_forensic")), "value = gm_arch_cost_base multiply = 5")

    def test_the_pass_sums_the_digs_by_method(self):
        body = squash(block(read(EFFECTS), "gm_arch_list_one"))
        for method in METHODS:
            self.assertIn(f"change_variable = {{ name = gm_arch_innovation_units add = gm_arch_innovation_{method} }}",
                          body)
            self.assertIn(f"change_variable = {{ name = gm_arch_cost_units add = gm_arch_cost_{method} }}", body)

    def test_the_modifiers_ride_the_journal_entry(self):
        e = read(EFFECTS)
        # gm_add_national reads ROOT's variable unguarded, and only a country the pass has
        # listed has these two: the guard, as the boons' gm_add_boon has.
        self.assertEqual(squash(block(e, "gm_arch_add_national")),
                         "if = { limit = { root = { has_variable = gm_arch_innovation_units } } "
                         "gm_add_national = { NAME = gm_arch_diversion VAR = gm_arch_innovation_units } } "
                         "if = { limit = { root = { has_variable = gm_arch_cost_units } } "
                         "gm_add_national = { NAME = gm_arch_expense VAR = gm_arch_cost_units } }")
        self.assertEqual(squash(block(e, "gm_arch_remove_national")),
                         "remove_modifier = gm_arch_diversion remove_modifier = gm_arch_expense")
        g = read(GM_EFFECTS)
        self.assertIn("gm_arch_add_national = yes", squash(block(g, "gm_apply_national_modifiers")))
        self.assertIn("gm_arch_remove_national = yes", squash(block(g, "gm_remove_national_modifiers")))
        L = loc()
        for key in ("gm_arch_diversion", "gm_arch_diversion_desc", "gm_arch_expense", "gm_arch_expense_desc"):
            self.assertIn(key, L)


class EntryTests(unittest.TestCase):
    """The journal entry opens for a country that digs or has a site waiting."""

    def test_the_entry_and_the_refresh_count_a_site(self):
        je = squash(strip_comments(read(JE)))
        self.assertEqual(je.count("gm_arch_country_has_any = yes"), 2, "is_shown_when_inactive and possible")
        refresh = squash(block(read(GM_EFFECTS), "gm_country_refresh"))
        self.assertEqual(refresh.count("gm_arch_country_has_any = yes"), 2, "gm_active and add_journal_entry")
        idle = squash(block(read(MON_TRIGGERS), "gm_ledgers_idle"))
        self.assertIn("gm_arch_country_idle = yes", idle, "the entry does not close on a dig")

    def test_the_counts_the_pass_writes(self):
        t = read(TRIGGERS)
        self.assertEqual(squash(block(t, "gm_arch_country_idle")), "gm_arch_country_has_any = no")
        has = squash(block(t, "gm_arch_country_has_any"))
        self.assertIn("has_variable = gm_arch_dig_count var:gm_arch_dig_count > 0", has)
        self.assertIn("has_variable = gm_arch_open_count var:gm_arch_open_count > 0", has)

    def test_a_country_that_digs_keeps_its_pulse(self):
        body = squash(block(read(EFFECTS), "gm_arch_country_listed"))
        self.assertIn("set_variable = gm_active", body)

    def test_a_player_is_refreshed_after_the_pass_so_a_finished_digs_cost_ends(self):
        monthly = squash(block(read(EFFECTS), "gm_arch_monthly"))
        self.assertLess(monthly.index("gm_arch_pass = yes"), monthly.index("is_ai = no } trigger_event = { id = monument_events.20 }"))
        self.assertNotIn("is_ai = no gm_arch_country_has_any = yes", monthly)

    def test_an_open_row_names_no_state(self):
        # One variable on a container shared by every country that may dig it: the
        # last listed would name its state in everyone's row.
        self.assertNotIn("gm_site_view_state", loc()["gm_arch_row_open_detail"])
        pass_ = squash(block(read(EFFECTS), "gm_arch_list_one"))
        self.assertEqual(pass_.count("gm_site_view_state"), 1, "written for a dig, which has one sponsor")
        self.assertNotIn("is_target_in_variable_list", pass_)

    def test_the_lists_are_rebuilt_after_every_order(self):
        events = read(EVENTS)
        for n in (10, 11):
            ev = squash(raw_block_at(strip_comments(events), rf"(?m)^arch_events\.{n}\s*=\s*\{{"))
            self.assertIn("gm_arch_pass = yes trigger_event = { id = monument_events.20 }", ev, n)


class OrderTests(unittest.TestCase):
    def test_a_button_only_orders_the_work(self):
        sg = squash(strip_comments(read(SGUIS)))
        for method, (tech, _rate) in METHODS.items():
            body = squash(block(read(SGUIS), f"gm_arch_launch_{method}_sgui"))
            self.assertIn("scope = country saved_scopes = { gm_arch }", body)
            self.assertIn(f"gm_arch_method_{method}_ok = yes", body.split("is_valid")[0], "shown only with the technology")
            self.assertIn("gm_arch_choose_launch = { WHO = root METHOD = " + method + " }", body)
            self.assertIn("ai_is_valid = { always = no }", body)
        self.assertEqual(sg.count("gm_arch_choose_launch"), 3)
        susp = squash(block(read(SGUIS), "gm_arch_suspend_sgui"))
        self.assertIn("gm_arch_order_suspend = { WHO = root }", susp)
        self.assertIn("custom_tooltip = { text = gm_arch_suspend_tt", susp)

    def test_the_orders_hand_the_site_to_a_hidden_event(self):
        e = read(EFFECTS)
        self.assertEqual(squash(block(e, "gm_arch_order_launch")),
                         "set_variable = { name = gm_site_order_method value = flag:$METHOD$ } "
                         "save_scope_as = gm_arch_pick $WHO$ = { trigger_event = { id = arch_events.10 } }")
        self.assertEqual(squash(block(e, "gm_arch_order_suspend")),
                         "save_scope_as = gm_arch_pick $WHO$ = { trigger_event = { id = arch_events.11 } }")
        choose = squash(block(e, "gm_arch_choose_launch"))
        self.assertIn("text = gm_arch_launch_$METHOD$_tt gm_arch_order_launch", choose,
                      "the tooltip says what it costs")
        events = strip_comments(read(EVENTS))
        for n in (10, 11):
            ev = squash(raw_block_at(events, rf"(?m)^arch_events\.{n}\s*=\s*\{{"))
            self.assertIn("type = country_event hidden = yes", ev, n)

    def test_the_launch_worker_checks_again(self):
        ev = squash(raw_block_at(strip_comments(read(EVENTS)), r"(?m)^arch_events\.10\s*=\s*\{"))
        self.assertIn("gm_arch_can_dig = { WHO = root } has_variable = gm_site_order_method", ev)
        self.assertIn("gm_arch_start_dig = { WHO = root }", ev)
        start = squash(block(read(EFFECTS), "gm_arch_start_dig"))
        for method in METHODS:
            self.assertIn(f"var:gm_site_order_method = flag:{method} $WHO$ = {{ gm_arch_method_{method}_ok = yes }}",
                          start)

    def test_tooltips_and_loc(self):
        L = loc()
        for key in ("gm_arch_dig_open_tt", "gm_arch_dig_ground_tt", "gm_arch_dig_tech_tt", "gm_arch_suspend_tt",
                    *(f"gm_arch_launch_{m}_tt" for m in METHODS)):
            self.assertIn(key, L)


class AiTests(unittest.TestCase):
    def test_the_ai_digs_at_peace_with_the_best_method(self):
        t = read(TRIGGERS)
        may = squash(block(t, "gm_arch_ai_may_dig"))
        self.assertEqual(may, "is_ai = yes is_at_war = no in_default = no")
        e = read(EFFECTS)
        best = squash(block(e, "gm_arch_start_best"))
        self.assertLess(best.index("forensic_ok"), best.index("systematic_ok"))
        decide = squash(block(e, "gm_arch_ai_decide"))
        self.assertIn("OR = { NOT = { has_variable_list = gm_arch_digging } NOT = { any_in_list = { variable = "
                      "gm_arch_digging count >= 2 } } }", decide, "two digs at most; a country that never dug has no list")
        self.assertIn("gm_arch_start_best = { WHO = scope:gm_arch_ai_country }", decide)
        monthly = squash(block(e, "gm_arch_monthly"))
        self.assertIn("gm_arch_ai_may_dig = yes } gm_arch_ai_decide = yes", monthly)

    def test_no_variable_list_size(self):
        # Its `target` key fails to load in 1.14 (un_mandate_effects.txt).
        for rel in (EFFECTS, TRIGGERS):
            self.assertNotIn("variable_list_size", strip_comments(read(rel)), rel)


class EventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ev = strip_comments(read(EVENTS))

    def test_the_events(self):
        self.assertTrue(read(EVENTS).lstrip("﻿").startswith("namespace = arch_events"))
        ids = re.findall(r"(?m)^(arch_events\.\d+)\s*=\s*\{", self.ev)
        self.assertEqual(ids, [f"arch_events.{n}" for n in (1, 2, 3, 10, 11)])
        for n in (1, 2, 3):
            body = squash(raw_block_at(self.ev, rf"(?m)^arch_events\.{n}\s*=\s*\{{"))
            self.assertIn("type = country_event", body)
            self.assertIn("event_image = { video =", body)
            self.assertNotIn("hidden = yes", body)

    def test_a_find_offers_a_dig_or_to_wait(self):
        body = squash(raw_block_at(self.ev, r"(?m)^arch_events\.1\s*=\s*\{"))
        self.assertIn("gm_arch_choose_launch = { WHO = root METHOD = systematic }", body)
        self.assertIn("gm_arch_choose_launch = { WHO = root METHOD = antiquarian }", body)
        self.assertEqual(body.count("option = {"), 3)

    def test_loc(self):
        L = loc()
        for n, parts in ((1, ("t", "d", "f", "a", "b", "c", "c.tt")), (2, ("t", "d", "f", "a", "a.tt")),
                         (3, ("t", "d", "f", "a", "a.tt"))):
            for p in parts:
                self.assertIn(f"arch_events.{n}.{p}", L)
        for n in (2, 3):
            self.assertIn("[ROOT.GetCountry.GetCustom('gm_arch_site_name')]", L[f"arch_events.{n}.d"])

    def test_the_debug_event(self):
        ev = squash(raw_block_at(strip_comments(read(DEBUG_EVENTS)), r"(?m)^te_debug_monuments\.7\s*=\s*\{"))
        for part in ("gm_arch_seed_sites = yes", "gm_arch_start_best = { WHO = root }", "gm_arch_monthly = yes",
                     "gm_arch_debug_log = yes"):
            self.assertIn(part, ev)
        L = loc()
        for k in ("t", "desc", "flavor", "a", "a.tt", "b", "b.tt", "c", "c.tt", "d", "d.tt"):
            self.assertIn(f"te_debug_monuments.7.{k}", L)


class PanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = read(GUI)

    def test_mounted_after_the_opportunity(self):
        status = squash(strip_comments(raw_block_at(read(WIDGET), r"(?m)^\ttype te_gm_status_sections = flowcontainer \{")))
        self.assertIn("te_gm_sec_commission = {} te_gm_sec_archaeology = {} te_gm_sec_national = {}", status)

    def test_its_flag_says_its_default(self):
        text = strip_comments(self.gui)
        self.assertEqual(set(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", text)), {"gm_arch_closed"})
        negated = len(re.findall(r"Not\(\s*GetVariableSystem\.Exists\('gm_arch_closed'\)\s*\)", text))
        bare = len(re.findall(r"GetVariableSystem\.Exists\('gm_arch_closed'\)", text)) - negated
        self.assertEqual((bare, negated), (1, 2), "shown unless closed")

    def test_the_rows_come_from_the_lists_the_pass_writes(self):
        for lst, row in (("gm_arch_digging", "gm_arch_row_digging"), ("gm_arch_available", "gm_arch_row_open")):
            self.assertIn(f"GetList('{lst}')", self.gui)
            self.assertIn(f'{row} = {{ datacontext = "[Scope.GetScriptContainer]" }}', self.gui)
        self.assertEqual(self.gui.count("GetList("), 2)

    def test_each_button_is_a_scripted_gui(self):
        for sgui in ("gm_arch_launch_antiquarian_sgui", "gm_arch_launch_systematic_sgui",
                     "gm_arch_launch_forensic_sgui", "gm_arch_suspend_sgui"):
            self.assertIn(f"GetScriptedGui('{sgui}')", self.gui)
            self.assertIn(f"{sgui} = {{", read(SGUIS))
        self.assertEqual(self.gui.count("AddScope( 'gm_arch', ScriptContainer.MakeScope )"), 12)

    def test_every_rendered_key_exists(self):
        L = loc()
        keys = set(re.findall(r'(?:text|tooltip) = "([a-z]\w*)"', strip_comments(self.gui)))
        self.assertGreater(len(keys), 10)
        for key in keys:
            self.assertIn(key, L, key)

    def test_every_value_it_reads_exists_and_is_guarded(self):
        values = read(VALUES)
        used = set(re.findall(r"ScriptValue\('(gm_arch_\w+)'\)", self.gui)) | set(
            re.findall(r"ScriptValue\('(gm_arch_\w+)'\)", "\n".join(loc().values())))
        self.assertGreater(len(used), 6)
        for name in used:
            body = block(values, name)
            self.assertIsNotNone(body, name)
        for name in ("gm_arch_disp_method", "gm_arch_disp_progress", "gm_arch_disp_levels", "gm_arch_disp_status"):
            self.assertIn("has_variable", block(values, name), f"{name}: a site that was never dug has no record")

    def test_a_row_names_itself_as_a_trophy_does(self):
        L = loc()
        self.assertEqual(L["gm_arch_row_title"], "#b [ScriptContainer.GetCustom('gm_tr_landmark_name')]#!")
        self.assertIn("gm_tr_row_landmark_tt", self.gui)
        self.assertIn("[ScriptContainer.GetCustom('gm_tr_landmark_desc')]", L["gm_tr_row_landmark_tt"])


class RegistryTests(unittest.TestCase):
    """Every plumbing site a landmark has, for every buried row (LandmarkTests covers
    the rest of them: names, histories, pictures and the debug log)."""

    def test_a_buried_site_is_never_seeded_at_the_start(self):
        body = squash(block(read("common/scripted_effects/gm_landmark_effects.txt"), "gm_seed_landmarks"))
        for lm in BURIED:
            self.assertNotIn(f"KEY = {lm.key} ", body, lm.key)

    def test_the_trophy_parts_name_what_a_dig_yields(self):
        branches = re.findall(r"flag:(\w+) \}\s*localization_key = (gm_tr_part_\w+)",
                              block(read(TR_CUSTOM_LOC), "gm_tr_part_name"))
        parted = {k for k, _ in branches}
        self.assertIn("troy_hisarlik", parted)
        L = loc()
        for _, key in branches:
            self.assertIn(key, L)

    def test_every_history_line_says_what_was_found(self):
        L = loc()
        for lm in BURIED:
            line = L[f"gm_landmark_{lm.key}_desc"]
            self.assertTrue(line.endswith("."), lm.key)
            self.assertGreater(len(line), 60, lm.key)
            self.assertNotIn("1836", line, f"{lm.key}: a buried site is not a monument of 1836")


if __name__ == "__main__":
    unittest.main()
