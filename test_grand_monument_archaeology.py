"""Grand Monument archaeology (issue #939): the buried sites, the gate that opens
them, the dig, and what a finished dig hands to the monument machinery, pinned
against the landmark registry.

Design: docs/superpowers/archive/specs/2026-10-14-grand-monument-archaeology-design.md,
reworked by 2026-10-16-grand-monument-archaeology-rework-design.md (costs by the
site, sized digs, events that name the place, the find and its history, and
foreign digs by treaty).
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
    BUILT, LANDMARKS, ROOT, block, loc, raw_block_at, read, squash, strip_comments,
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
CONCESSION = "common/treaty_articles/120_archaeological_concession.txt"
PERMIT = "common/treaty_articles/121_excavation_permit.txt"

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
    Site("pompeii", "romanticism", "excavating"),
)
BURIED = tuple(lm for lm in LANDMARKS if lm.buried)
METHODS = {"antiquarian": ("romanticism", 4), "systematic": ("empiricism", 2.5), "forensic": ("computer_networks", 3.5)}
# The weekly innovation a dig diverts, its whole cost (owner, 2026-10-16; rework spec § 1).
INNOVATION = {"antiquarian": 5, "systematic": 20, "forensic": 100}
# Months for a site of 5, 10 and 15 levels: the 10-level months scaled by (levels + 5) / 15.
MONTHS = {"antiquarian": (17, 25, 34), "systematic": (27, 40, 54), "forensic": (20, 29, 39)}
ARTICLES = ("archaeological_concession", "excavation_permit")


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
            f"VECTOR = {site.vector} FORM = {lm.form} LEVEL = {lm.level} BUILT = {BUILT[lm.key]} }}")


class TableTests(unittest.TestCase):
    def test_a_row_for_every_buried_landmark_in_order(self):
        self.assertEqual([s.key for s in ARCH_SITES], [lm.key for lm in BURIED])
        self.assertEqual(len(ARCH_SITES), 36)

    def test_what_a_site_is(self):
        states, techs = state_regions(), technologies()
        self.assertGreater(len(states), 700)
        self.assertGreater(len(techs), 300)
        for lm, site in zip(BURIED, ARCH_SITES):
            self.assertFalse(lm.placed, lm.key)
            self.assertIn(lm.state, states, f"{lm.key}: a state region that exists")
            self.assertIn(site.tech, techs, f"{lm.key}: a technology that exists")
            self.assertIn(site.vector, ("survey", "incidental", "excavating"), lm.key)
            self.assertEqual(lm.dedication, "civic", f"{lm.key}: the antiquity and archive dedications are deferred")
            self.assertIsNone(lm.tag, lm.key)

    def test_the_picture_codes_follow_the_rows(self):
        first = LANDMARKS.index(BURIED[0]) + 1
        self.assertEqual(first, 52, "append-only: the first buried site is row 52")
        # Then the historical opportunities' landmarks (signatures spec §6), after every buried site.
        historical = tuple(lm for lm in LANDMARKS if lm.year)
        self.assertEqual(len(LANDMARKS), 51 + len(BURIED) + len(historical))
        self.assertEqual(LANDMARKS[51 + len(BURIED):], historical)

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
                                        "gm_arch_seeded set_global_variable = { name = gm_arch_seed_round value = "
                                        "gm_arch_seed_rounds } gm_arch_seed_sites = yes gm_arch_self_check = yes }"),
                        body[:300])

    def test_a_site_added_later_is_seeded_in_a_game_already_seeded(self):
        body = squash(block(self.e, "gm_arch_monthly"))
        self.assertIn("if = { limit = { NOT = { has_global_variable = gm_arch_seed_round } } set_global_variable = { "
                      "name = gm_arch_seed_round value = 1 } } if = { limit = { global_var:gm_arch_seed_round < "
                      "gm_arch_seed_rounds } set_global_variable = { name = gm_arch_seed_round value = "
                      "gm_arch_seed_rounds } gm_arch_seed_sites = yes }", body)
        self.assertLess(body.index("gm_arch_self_check = yes"), body.index("global_var:gm_arch_seed_round <"),
                        "the self-check stays once a game")
        self.assertEqual(squash(block(read(VALUES), "gm_arch_seed_rounds")), "value = 3",
                         "raise it with every row added to ARCH_SITES after a game may have been seeded")

    def test_a_site_records_its_year(self):
        """The year it was built, for the split when it is unearthed (owner,
        2026-10-19); round 3 gives it to a site seeded before, still buried."""
        seed = squash(block(self.e, "gm_arch_seed_site"))
        self.assertIn("set_variable = { name = gm_tr_built value = $BUILT$ }", seed)
        self.assertIn("else_if = { limit = { has_global_variable_list = gm_arch_sites } every_in_global_list = { "
                      "variable = gm_arch_sites limit = { has_variable = gm_tr_landmark var:gm_tr_landmark = "
                      "flag:$KEY$ NOT = { has_variable = gm_tr_built } } set_variable = { name = gm_tr_built "
                      "value = $BUILT$ } } }", seed)
        # A site that never learned it counts as built the year it is found.
        self.assertEqual(squash(block(read(VALUES), "gm_mon_built")),
                         "value = gm_this_year if = { limit = { has_variable = gm_tr_built } value = var:gm_tr_built }")

    def test_a_site_being_dug_in_1836_starts_as_a_dig(self):
        excavating = [s.key for s in ARCH_SITES if s.vector == "excavating"]
        self.assertEqual(excavating, ["pompeii"])
        seed = squash(block(self.e, "gm_arch_seed_site"))
        self.assertIn("limit = { var:gm_site_vector = flag:excavating } gm_arch_seed_dig = yes", seed)
        self.assertLess(seed.index("name = gm_site_status value = 1"), seed.index("gm_arch_seed_dig = yes"))
        dig = squash(block(self.e, "gm_arch_seed_dig"))
        self.assertIn("random_scope_state = { limit = { exists = owner } owner = { save_scope_as = gm_arch_seed_sponsor } }",
                      dig, "the owner of its ground digs it")
        self.assertIn("set_variable = { name = gm_site_progress value = gm_arch_excavating_progress }", dig)
        self.assertIn("set_variable = { name = gm_site_method value = flag:antiquarian } "
                      "gm_arch_begin_dig = { WHO = scope:gm_arch_seed_sponsor }", dig)
        self.assertIn("else = { set_variable = { name = gm_site_status value = 2 } }", dig, "with no owner, known")
        self.assertLess(dig.index("gm_site_progress value"), dig.index("gm_arch_begin_dig"),
                        "the progress is set first, so the dig keeps it")
        self.assertEqual(squash(block(read(VALUES), "gm_arch_excavating_progress")), "value = 30")
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
                     "gm_arch_may_dig_ground = { WHO = $WHO$ }", "gm_arch_has_gate_for = { WHO = $WHO$ }"):
            self.assertIn(part, can)
        self.assertEqual(squash(block(t, "gm_arch_may_dig_ground")),
                         "var:gm_tr_origin_region ?= { any_scope_state = { OR = { owner = $WHO$ "
                         "gm_arch_state_open_abroad = { WHO = $WHO$ } } } }")
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

    def test_a_site_takes_longer_the_larger_it_is(self):
        self.assertEqual(squash(block(self.v, "gm_arch_size_factor")),
                         "value = 15 divide = { value = gm_arch_disp_levels add = 5 }")
        for method, (_tech, rate) in METHODS.items():
            self.assertEqual(squash(block(self.v, f"gm_arch_site_rate_{method}")),
                             f"value = gm_arch_rate_{method} multiply = gm_arch_size_factor", method)
            self.assertEqual(squash(block(self.v, f"gm_arch_site_months_{method}")),
                             f"value = 100 divide = gm_arch_site_rate_{method} ceiling = yes", method)
            months = tuple(math.ceil(100 / (rate * 15 / (levels + 5))) for levels in (5, 10, 15))
            self.assertEqual(months, MONTHS[method], method)
        self.assertIn("value = gm_arch_site_rate_systematic", block(self.v, "gm_arch_disp_rate"),
                      "the row's months to go read the site's own rate")

    def test_every_value_is_defined_before_it_is_read(self):
        text = strip_comments(self.v)
        names = re.findall(r"(?m)^(gm_arch_\w+)\s*=", text)
        for i, name in enumerate(names):
            for later in names[i + 1:]:
                self.assertNotRegex(block(self.v, name), rf"\b{later}\b", f"{name} reads {later}, defined after it")

    def test_a_month_of_progress(self):
        body = squash(block(self.e, "gm_arch_dig_step"))
        self.assertIn("gm_arch_save_dig_state = yes", body, "dug where the sponsor may dig, at home or abroad")
        for method in METHODS:
            self.assertIn(f"change_variable = {{ name = gm_site_progress add = gm_arch_site_rate_{method} }}", body)
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
        self.assertIn("gm_arch_save_dig_state = yes", body)
        self.assertIn("gm_arch_settle_levels = yes gm_arch_settle_terms = yes gm_arch_place = yes", body)
        where = squash(block(self.e, "gm_arch_save_dig_state"))
        self.assertTrue(where.startswith("clear_saved_scope = gm_arch_dig_state var:gm_tr_origin_region ?= { "
                                         "random_scope_state = { limit = { owner = scope:gm_arch_sponsor } "
                                         "save_scope_as = gm_arch_dig_state } }"), "its own ground first")
        # Abroad, a concession before a permit, each read from the treaty.
        self.assertLess(where.index("ARTICLE = archaeological_concession"), where.index("ARTICLE = excavation_permit"))
        for terms in ("own", "concession", "permit"):
            self.assertIn(f"set_variable = {{ name = gm_site_terms value = flag:{terms} }}", where)

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
        self.assertLess(body.index("gm_arch_tell_finished = yes"), body.index("gm_arch_retire = yes"))
        self.assertLess(body.index("gm_arch_tell_finished = yes"), body.index("gm_arch_stand_beside = yes"))
        self.assertIn("scope:gm_arch_dig_state = { owner = { save_scope_as = gm_arch_host } }", body)
        tell = squash(block(self.e, "gm_arch_tell_finished"))
        self.assertIn("scope:gm_arch_sponsor = { trigger_event = { id = arch_events.2 } }", tell)
        self.assertIn("scope:gm_arch_host = { trigger_event = { id = arch_events.2 } }", tell)
        # The host's copy alone carries the host's view.
        self.assertIn("scope:gm_arch_dig_state = { save_scope_as = gm_arch_ev_host_view } scope:gm_arch_host = { "
                      "trigger_event = { id = arch_events.2 } } clear_saved_scope = gm_arch_ev_host_view", tell)
        self.assertLess(tell.index("id = arch_events.2 } } } if"), tell.index("save_scope_as = gm_arch_ev_host_view"))
        for case in ("ruined", "concession", "permit", "scholar", "host_view"):
            self.assertLess(tell.index(f"clear_saved_scope = gm_arch_ev_{case}"), tell.index("gm_arch_ev_mark"), case)

    def test_beside_is_a_retag_and_the_lists_a_seeded_landmark_beside_uses(self):
        body = squash(block(self.e, "gm_arch_stand_beside"))
        self.assertIn("remove_list_global_variable = { name = gm_arch_sites target = scope:gm_tr_moving }", body)
        self.assertIn("add_to_global_variable_list = { name = gm_monuments target = scope:gm_tr_moving }", body)
        self.assertIn("remove_tag = gm_site add_tag = gm_monument", body)
        self.assertNotIn("gm_state_tr_add_levels", body)
        self.assertIn("add_to_variable_list = { name = gm_monuments_here target = scope:gm_tr_moving }", body)
        self.assertIn("add_to_variable_list = { name = gm_monuments_held target = scope:gm_tr_moving }", body)
        # The same lists, in the same order, as the landmark seeded beside another.
        seeded = squash(block(read("common/scripted_effects/gm_monument_effects.txt"), "gm_seed_landmark_beside"))
        for line in ("add_to_variable_list = { name = gm_monuments_here",
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
    """The events name their site, its place and state, the find and its history,
    through a saved scope of the site's own (rework spec § 2)."""

    @classmethod
    def setUpClass(cls):
        cls.e = read(EFFECTS)
        cls.ev = strip_comments(read(EVENTS))

    def test_each_popup_carries_one_site(self):
        body = squash(block(self.e, "gm_arch_ev_mark"))
        clears = re.findall(r"clear_saved_scope = gm_arch_ev_(\w+)", body)
        self.assertEqual(clears, [lm.key for lm in BURIED], "every name is cleared first")
        branches = re.findall(r"limit = \{ var:gm_tr_landmark = flag:(\w+) \} \$STATE\$ = \{ "
                              r"save_scope_as = gm_arch_ev_(\w+) \}", body)
        self.assertEqual(branches, [(lm.key, lm.key) for lm in BURIED])
        self.assertLess(body.rindex("clear_saved_scope"), body.index("if = {"))
        for name in ("gm_arch_tell_found", "gm_arch_tell_finished"):
            self.assertIn("gm_arch_ev_mark = { STATE =", squash(block(self.e, name)), name)

    def test_each_event_picks_the_sites_lines(self):
        for n, kind in ((1, "found"), (2, "dug")):
            ev = squash(raw_block_at(self.ev, rf"(?m)^arch_events\.{n}\s*=\s*\{{"))
            desc = ev[ev.index("desc = { first_valid"):]
            got = re.findall(r"triggered_desc = \{ trigger = \{ exists = scope:gm_arch_ev_(\w+) \} "
                             rf"desc = gm_arch_site_(\w+)_{kind} \}}", desc)
            self.assertEqual(got, [(lm.key, lm.key) for lm in BURIED], n)
            self.assertIn(f"triggered_desc = {{ desc = arch_events.{n}.d }} }} }}", desc, "a plain fallback")

    def test_every_site_says_where_what_and_its_history(self):
        L = loc()
        self.assertIn("gm_arch_history_lead", L)
        for lm in BURIED:
            k = lm.key
            for part in ("place", "found", "dug", "history"):
                self.assertIn(f"gm_arch_site_{k}_{part}", L, f"{k} {part}")
            for part in ("found", "dug"):
                text = L[f"gm_arch_site_{k}_{part}"]
                self.assertIn(f"$gm_arch_site_{k}_place$", text, f"{k} {part}: the place")
                self.assertIn(f"[SCOPE.sState('gm_arch_ev_{k}').GetName]", text, f"{k} {part}: the state, by its own scope")
                self.assertTrue(text.endswith(f"\\n\\n$gm_arch_history_lead$ $gm_arch_site_{k}_history$"),
                                f"{k} {part}: the historical note last")
            history = L[f"gm_arch_site_{k}_history"]
            self.assertRegex(history, r"\b1[89]\d\d\b|\b20[0-2]\d\b|\bBC\b|\bAD\b", f"{k}: a date in its history")
            self.assertTrue(history.endswith("."), k)
            self.assertGreater(len(L[f"gm_arch_site_{k}_dug"]), 200, k)

    def test_no_country_variable_names_the_site(self):
        # The variable the MVP used was overwritten by the next popup.
        for rel in (EFFECTS, EVENTS, CUSTOM_LOC):
            self.assertNotIn("gm_arch_last", strip_comments(read(rel)), rel)
        self.assertNotIn("gm_arch_site_name", strip_comments(read(CUSTOM_LOC)))
        for key in ("arch_events.1.d", "arch_events.2.d"):
            self.assertNotIn("GetCustom", loc()[key])

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

    def test_the_money_modifier_is_a_retired_stub(self):
        # Digs cost no money (owner, 2026-10-16). The stub stays, with its Budget
        # Breakdown category, so a save that carries it loads clean and sheds it.
        body = squash(strip_comments(read(MODIFIERS)))
        self.assertIn("gm_arch_expense = { icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_negative.dds "
                      "country_expenses_add = 1 country_te_budget_expense_archaeology_add = 1 }", body,
                      "a recurring monetary modifier joins a Budget Breakdown category (test_budget_breakdown.py)")
        self.assertIn("RETIRED 2026-10-16", read(MODIFIERS))
        gen = read("scripts/generators/gen_budget_breakdown.py")
        self.assertIn('"archaeology": ("Archaeological Digs", ("gm_arch_expense",)),', gen)
        for rel in (EFFECTS, EVENTS, SGUIS, "common/treaty_articles/120_archaeological_concession.txt",
                    "common/treaty_articles/121_excavation_permit.txt"):
            code = strip_comments(read(rel))
            self.assertNotIn("NAME = gm_arch_expense", code, rel)
            self.assertNotRegex(code, r"add_modifier = \{ name = gm_arch_expense", rel)

    def test_the_methods_cost_what_the_spec_says(self):
        v = read(VALUES)
        for method, units in INNOVATION.items():
            self.assertEqual(squash(block(v, f"gm_arch_innovation_{method}")), f"value = {units}", method)
        site = squash(block(v, "gm_arch_site_innovation"))
        for n, method in enumerate(METHODS, start=1):
            self.assertIn(f"gm_arch_disp_method = {n} }} value = gm_arch_innovation_{method}", site)

    def test_no_money_cost(self):
        # Innovation is the whole cost; nothing reads the economy (owner, 2026-10-16).
        v = strip_comments(read(VALUES))
        for word in ("gdp", "income", "net_fixed_income", "gm_arch_cost_base", "gm_arch_price_antiquarian",
                     "gm_arch_site_cost"):
            self.assertNotRegex(v, rf"\b{word}\b", word)
        e = strip_comments(read(EFFECTS))
        for word in ("gm_arch_cost_units", "gm_site_weekly_cost", "net_fixed_income", "gm_arch_ai_budget"):
            self.assertNotIn(word, e, word)

    def test_the_pass_sums_the_digs_by_method(self):
        body = squash(block(read(EFFECTS), "gm_arch_list_one"))
        for method in METHODS:
            self.assertIn(f"change_variable = {{ name = gm_arch_innovation_units add = gm_arch_innovation_{method} }}",
                          body)

    def test_the_modifiers_ride_the_journal_entry(self):
        e = read(EFFECTS)
        # gm_add_national reads ROOT's variable unguarded, and only a country the pass has
        # listed has it: the guard, as the boons' gm_add_boon has.
        self.assertEqual(squash(block(e, "gm_arch_add_national")),
                         "if = { limit = { root = { has_variable = gm_arch_innovation_units } } "
                         "gm_add_national = { NAME = gm_arch_diversion VAR = gm_arch_innovation_units } }")
        # The retired money modifier is still removed, so an old save sheds it.
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
        # Its levels and what they count for, at the 1836 rate (owner, 2026-10-19).
        self.assertIn("ScriptValue('gm_arch_disp_grandeur')|0]#! [concept_grandeur]", loc()["gm_arch_row_open_detail"])
        self.assertEqual(squash(block(read(VALUES), "gm_arch_disp_grandeur")),
                         "value = gm_arch_disp_levels multiply = gm_level_grandeur_1836")
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


class PlayerInnovationTests(unittest.TestCase):
    """A player may not launch a dig that diverts more weekly innovation than it makes (owner, 2026-10-16)."""

    def test_each_method_has_a_floor_of_its_own_figure(self):
        t = read(TRIGGERS)
        for method in METHODS:
            self.assertEqual(squash(block(t, f"gm_arch_spares_{method}")),
                             f"country_innovation >= gm_arch_innovation_{method}", method)

    def test_the_buttons_are_greyed_below_the_floor(self):
        L = loc()
        for method, units in INNOVATION.items():
            valid = squash(block(block(read(SGUIS), f"gm_arch_launch_{method}_sgui"), "is_valid"))
            self.assertIn(f"custom_tooltip = {{ text = gm_arch_dig_innovation_{method}_tt "
                          f"gm_arch_spares_{method} = yes }}", valid, method)
            self.assertIn(f"at least {units} weekly [concept_innovation]", L[f"gm_arch_dig_innovation_{method}_tt"],
                          "the tooltip's figure is the value's")

    def test_the_find_offers_only_a_dig_we_can_spare(self):
        body = squash(raw_block_at(strip_comments(read(EVENTS)), r"(?m)^arch_events\.1\s*=\s*\{"))
        self.assertIn("name = arch_events.1.a trigger = { gm_arch_method_systematic_ok = yes "
                      "gm_arch_spares_systematic = yes }", body)
        self.assertIn("name = arch_events.1.b trigger = { NOT = { AND = { gm_arch_method_systematic_ok = yes "
                      "gm_arch_spares_systematic = yes } } gm_arch_method_antiquarian_ok = yes "
                      "gm_arch_spares_antiquarian = yes }", body)

    def test_the_worker_checks_the_innovation_again(self):
        ev = squash(raw_block_at(strip_comments(read(EVENTS)), r"(?m)^arch_events\.10\s*=\s*\{"))
        self.assertIn("has_variable = gm_site_order_method gm_arch_order_spared = { WHO = root }", ev)
        spared = squash(block(read(TRIGGERS), "gm_arch_order_spared"))
        for method in METHODS:
            self.assertIn(f"AND = {{ var:gm_site_order_method = flag:{method} "
                          f"$WHO$ = {{ gm_arch_spares_{method} = yes }} }}", spared, method)

    def test_the_ais_floor_is_above_the_players(self):
        v = read(VALUES)
        self.assertGreaterEqual(int(squash(block(v, "gm_arch_ai_innovation_multiple")).split()[-1]), 1)


class AiTests(unittest.TestCase):
    def test_the_ai_digs_at_peace_with_the_best_method_it_affords(self):
        t = read(TRIGGERS)
        may = squash(block(t, "gm_arch_ai_may_dig"))
        self.assertEqual(may, "is_ai = yes is_at_war = no in_default = no")
        e = read(EFFECTS)
        best = squash(block(e, "gm_arch_start_best"))
        self.assertLess(best.index("forensic_ok"), best.index("systematic_ok"))
        decide = squash(block(e, "gm_arch_ai_decide"))
        self.assertIn("OR = { NOT = { has_variable_list = gm_arch_digging } NOT = { any_in_list = { variable = "
                      "gm_arch_digging count >= 2 } } }", decide, "two digs at most; a country that never dug has no list")
        # It digs only with the innovation to spare for an Antiquarian dig, the grandest
        # site waiting, by the best method it affords.
        self.assertIn("gm_arch_ai_affords_antiquarian = yes", decide)
        self.assertIn("variable = gm_arch_available order_by = gm_arch_disp_levels position = 0", decide)
        self.assertIn("gm_arch_start_affordable = { WHO = scope:gm_arch_ai_country }", decide)
        start = squash(block(e, "gm_arch_start_affordable"))
        self.assertLess(start.index("gm_arch_ai_affords_forensic"), start.index("gm_arch_ai_affords_systematic"))
        self.assertIn("limit = { gm_arch_can_dig = { WHO = $WHO$ } } gm_arch_start_dig = { WHO = $WHO$ }", start)
        v = read(VALUES)
        self.assertEqual(squash(block(v, "gm_arch_ai_innovation_multiple")), "value = 4")
        for method in METHODS:
            self.assertEqual(squash(block(v, f"gm_arch_ai_floor_{method}")),
                             f"value = gm_arch_innovation_{method} multiply = gm_arch_ai_innovation_multiple", method)
            self.assertEqual(squash(block(t, f"gm_arch_ai_affords_{method}")),
                             f"gm_arch_method_{method}_ok = yes country_innovation >= gm_arch_ai_floor_{method}", method)
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
        self.assertEqual(ids, [f"arch_events.{n}" for n in (1, 2, 10, 11, 12)])
        for n in (1, 2):
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
        for n, parts in ((1, ("t", "t_survey", "d", "f", "f_survey", "a", "b", "c", "c.tt")),
                         (2, ("t", "t_ruined", "t_abroad", "t_host", "d", "f", "f_ruined", "f_concession", "f_permit",
                              "f_host_concession", "f_host", "a", "a.tt", "b", "b.tt", "c", "c.tt", "d", "d.tt",
                              "e", "e.tt", "f", "f.tt", "ruined.tt"))):
            for p in parts:
                self.assertIn(f"arch_events.{n}.{p}", L)
        for k in L:
            self.assertFalse(k.startswith("arch_events.3."), k)

    def test_a_survey_site_is_announced_once(self):
        e = read(EFFECTS)
        tell = squash(block(e, "gm_arch_tell_found"))
        self.assertIn("$WHO$ = { is_ai = no }", tell)
        self.assertIn("is_target_in_variable_list = { name = gm_site_told target = $WHO$ }", tell)
        self.assertLess(tell.index("add_to_variable_list = { name = gm_site_told target = $WHO$ }"),
                        tell.index("trigger_event = { id = arch_events.1 }"))
        self.assertIn("NOT = { var:gm_site_vector = flag:incidental } } $STATE$ = { save_scope_as = gm_arch_ev_survey }",
                      tell, "a site the scholars know: survey, or one already being dug")
        self.assertIn("gm_arch_tell_found = { WHO = scope:gm_arch_finder STATE = scope:gm_arch_find_state }",
                      squash(block(e, "gm_arch_found")))
        self.assertIn("gm_arch_tell_found = { WHO = scope:gm_arch_ls_who STATE = scope:gm_arch_ls_state }",
                      squash(block(e, "gm_arch_list_for")))

    def test_the_finished_dig_says_which_case_it_is(self):
        ev = squash(raw_block_at(self.ev, r"(?m)^arch_events\.2\s*=\s*\{"))
        self.assertEqual(ev.count("option = {"), 6)
        title = ev[ev.index("title = {"):ev.index(" desc = { first_valid")]
        order = [title.index(f"arch_events.2.t_{c}") for c in ("host", "ruined", "abroad")]
        self.assertEqual(order, sorted(order), "the host's view first, then the ruin, then abroad")

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
                     "gm_arch_launch_forensic_sgui", "gm_arch_suspend_sgui",
                     "gm_arch_abroad_concession_sgui", "gm_arch_abroad_permit_sgui"):
            self.assertIn(f"GetScriptedGui('{sgui}')", self.gui)
            self.assertIn(f"{sgui} = {{", read(SGUIS))
        self.assertEqual(self.gui.count("AddScope( 'gm_arch', ScriptContainer.MakeScope )"), 14)

    def test_the_buttons_give_this_sites_months_and_cost(self):
        L = loc()
        for method in METHODS:
            tip = L[f"gm_arch_launch_{method}_tooltip"]
            self.assertIn(f"ScriptContainer.MakeScope.ScriptValue('gm_arch_site_months_{method}')", tip, method)
            self.assertIn(f"GetPlayer.MakeScope.ScriptValue('gm_arch_innovation_{method}')", tip, method)
            self.assertNotIn("@money!", tip, "no money cost")

    def test_a_dig_row_shows_its_cost_and_its_terms(self):
        L = loc()
        self.assertIn("ScriptValue('gm_arch_site_innovation')", L["gm_arch_row_dig_innovation"])
        self.assertIn('text = "gm_arch_row_dig_innovation"', self.gui)
        for key in ("gm_je_arch_costs", "gm_je_arch_costs_tt", "gm_je_arch_summary_tt", "gm_arch_suspend_tooltip"):
            self.assertNotIn("money", L[key].lower(), key)
            self.assertNotIn("@money!", L[key], key)
        for n, key in ((1, "gm_arch_row_dig_concession"), (2, "gm_arch_row_dig_permit")):
            self.assertIn(f"ScriptValue('gm_arch_disp_terms'), '(CFixedPoint){n}' )]\"\n\t\t\ttext = \"{key}\"",
                          self.gui, key)
            self.assertIn("Var('gm_site_view_state').GetState.GetOwner.GetName", L[key])

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


class ForeignTests(unittest.TestCase):
    """Foreign digs by treaty: an Excavation Concession (partage) or an Excavation
    Permit (the finds stay), read live from the treaty (rework spec § 3)."""

    @classmethod
    def setUpClass(cls):
        cls.e = read(EFFECTS)
        cls.t = read(TRIGGERS)
        cls.arts = {"archaeological_concession": read(CONCESSION), "excavation_permit": read(PERMIT)}

    def test_the_articles(self):
        for name, text in self.arts.items():
            self.assertTrue((ROOT / (CONCESSION if name == ARTICLES[0] else PERMIT)).read_bytes()
                            .startswith(b"\xef\xbb\xbf"), name)
            self.assertFalse((ROOT / (CONCESSION if name == ARTICLES[0] else PERMIT)).read_bytes()
                             .startswith(b"\xef\xbb\xbf" * 2), name)
            body = squash(raw_block_at(strip_comments(text), rf"(?m)^{name}\s*=\s*\{{"))
            for part in ("kind = directed", "maintenance_paid_by = target_country", "required_inputs = { state }",
                         # shown only where the host has a site open to the sponsor (owner, 2026-10-23)
                         "visible = { gm_system_enabled = yes exists = scope:other_country "
                         "gm_arch_country_offers_site = { WHO = scope:other_country } }",
                         "state_valid_trigger = { scope:input = { owner = root "
                         "gm_arch_state_offers_site = { WHO = scope:other_country } } }",
                         f"no_duplicate_treaty_article = {{ ARTICLE_TYPE = {name} }}",
                         f"custom_tooltip_no_bullet = {name}_effects_desc",
                         "trigger_event = { id = arch_events.12 days = 1 }",
                         "on_withdrawal = {} on_break = {}"):
                self.assertIn(part, body, f"{name}: {part}")
            self.assertNotIn("set_variable", body, f"{name}: nothing written on the state")
            # a war goal enforcing the article checks possible, so it asks for the site too
            self.assertIn("gm_arch_country_offers_site = { WHO = scope:other_country }",
                          squash(block(strip_comments(text), "possible")), name)
        self.assertIn("gm_arch_method_antiquarian_ok = yes", self.arts["archaeological_concession"])
        self.assertIn("gm_arch_method_systematic_ok = yes", squash(block(strip_comments(self.arts["excavation_permit"]),
                                                                         "can_ratify")))
        for name in ARTICLES:
            # An AI asks only with the innovation to spare for the dig (owner, 2026-10-16).
            self.assertIn("gm_arch_ai_affords_systematic = yes",
                          squash(block(strip_comments(self.arts[name]), "evaluation_chance")), name)
        self.assertIn("can_be_enforced", self.arts["archaeological_concession"])
        self.assertNotIn("can_be_enforced", self.arts["excavation_permit"])
        L = loc()
        for name in ARTICLES:
            for suffix in ("", "_desc", "_effects_desc", "_article_short_desc"):
                self.assertIn(f"{name}{suffix}", L)
            self.assertNotIn("SOURCE_COUNTRY", L[f"{name}_desc"], "blank names in _desc")
        for key in ("GM_ARCH_CONCESSION_RELUCTANCE", "GM_ARCH_ANTIQUITIES_NATIONALISM", "GM_ARCH_PERMIT_RELUCTANCE",
                    "GM_ARCH_SUBJECT", "GM_ARCH_DIG_WANTED", "gm_arch_article_sponsor_tech_concession_tt",
                    "gm_arch_article_sponsor_tech_permit_tt"):
            self.assertIn(key, L)

    def test_the_right_is_read_from_the_treaty(self):
        body = squash(block(self.t, "gm_arch_state_conceded_to"))
        self.assertIn("save_temporary_scope_as = gm_arch_cs_state", body)
        self.assertIn("owner = { save_temporary_scope_as = gm_arch_cs_host NOT = { this = $WHO$ } }", body)
        self.assertIn("$WHO$ = { any_scope_treaty = { any_scope_article = { has_type = $ARTICLE$ "
                      "source_country = scope:gm_arch_cs_host input_state = scope:gm_arch_cs_state } } }", body)
        both = squash(block(self.t, "gm_arch_state_open_abroad"))
        for name in ARTICLES:
            self.assertIn(f"ARTICLE = {name}", both)

    def test_whoever_holds_the_right_is_listed_once(self):
        body = squash(block(self.e, "gm_arch_list_one"))
        self.assertIn("every_scope_treaty = { every_scope_article = { limit = { OR = { has_type = "
                      "archaeological_concession has_type = excavation_permit } source_country = scope:gm_arch_ls_host "
                      "input_state = scope:gm_arch_ls_state } target_country = { save_scope_as = gm_arch_ls_who }", body)
        listed = squash(block(self.e, "gm_arch_list_for"))
        self.assertIn("is_target_in_variable_list = { name = gm_arch_available target = scope:gm_arch_listing }", listed)

    def test_the_terms_decide_what_the_sponsor_takes_home(self):
        body = squash(block(self.e, "gm_arch_settle_terms"))
        self.assertIn("var:gm_site_terms = flag:concession NOT = { var:gm_tr_form = flag:rock_cut }", body,
                      "a rock-cut site has nothing to carry")
        self.assertIn("gm_arch_partage = yes", body)
        self.assertIn("add_modifier = { name = gm_arch_scholarship days = 3650 }", body)
        mods = squash(strip_comments(read(MODIFIERS)))
        self.assertIn("gm_arch_scholarship = { icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds "
                      "country_prestige_add = 10 country_cultural_pull_add = 1 }", mods)
        for key in ("gm_arch_scholarship", "gm_arch_scholarship_desc"):
            self.assertIn(key, loc())

    def test_partage_makes_a_trophy_from_the_digs_records(self):
        body = squash(block(self.e, "gm_arch_partage"))
        self.assertIn("create_container = { tags = { gm_trophy } save_scope_as = gm_tr_new", body)
        self.assertIn("add_to_global_variable_list = { name = gm_trophies target = scope:gm_tr_new }", body)
        for record in ("name = gm_tr_origin value = scope:gm_arch_dig_state",
                       "name = gm_tr_site value = scope:gm_arch_partage_home",
                       "name = gm_tr_site_region value = scope:gm_arch_partage_home.state_region",
                       "name = gm_tr_levels value = scope:gm_arch_partage_site.var:gm_site_piece",
                       "name = gm_tr_grandeur value = scope:gm_arch_partage_site.var:gm_site_piece_grandeur",
                       "name = gm_tr_taken_by value = scope:gm_arch_sponsor",
                       "name = gm_tr_share value = flag:piece",
                       "name = gm_tr_landmark value = scope:gm_arch_partage_site.var:gm_tr_landmark"):
            self.assertIn(f"set_variable = {{ {record} }}", body, record)
        self.assertIn("gm_tr_update_picture = yes", body)
        # A find counts at the 1836 rate (owner, 2026-10-19), split by its years:
        # the piece takes the site's year and its share of them.
        self.assertIn("if = { limit = { scope:gm_arch_partage_site = { has_variable = gm_tr_built } } "
                      "set_variable = { name = gm_tr_built value = scope:gm_arch_partage_site.var:gm_tr_built } } "
                      "gm_set_historical_grandeur = { LEVELS = scope:gm_arch_partage_site.var:gm_site_piece "
                      "BUILT = gm_mon_built START = gm_tr_start_grandeur AGE = gm_tr_age }", body)
        self.assertIn("change_variable = { name = gm_tr_levels subtract = var:gm_site_piece }", body,
                      "the host keeps the rest")
        v = read(VALUES)
        self.assertEqual(squash(block(v, "gm_arch_partage_levels")),
                         "value = gm_arch_disp_levels divide = 2 floor = yes min = 1")
        self.assertEqual(squash(block(v, "gm_arch_partage_grandeur")),
                         "value = gm_arch_partage_levels multiply = gm_level_grandeur_1836 divide = 2 ceiling = yes")
        # What the host keeps standing counts at the 1836 rate too: its levels
        # once settled and shared, before it stands beside or alone.
        place = squash(strip_comments(block(self.e, "gm_arch_place")))
        start = ("gm_set_historical_grandeur = { LEVELS = var:gm_tr_levels BUILT = gm_mon_built "
                 "START = gm_tr_start_grandeur AGE = gm_tr_age }")
        self.assertIn(start, place)
        self.assertLess(place.index(start), place.index("gm_arch_stand_beside = yes"))
        self.assertLess(place.index(start), place.index("gm_state_tr_receive = yes"))
        # Every record a trophy made from a state carries, this one carries:
        # set directly, or as the historical split's START or AGE.
        made = squash(block(read("common/scripted_effects/gm_trophy_effects.txt"), "gm_state_tr_make_trophy"))
        for record in re.findall(r"set_variable = \{ name = (gm_tr_\w+) value", made):
            self.assertTrue(f"name = {record} value" in body or f"START = {record} " in body
                            or f"AGE = {record} " in body, record)

    def test_the_grant_refreshes_the_sponsor(self):
        ev = squash(raw_block_at(strip_comments(read(EVENTS)), r"(?m)^arch_events\.12\s*=\s*\{"))
        self.assertIn("type = country_event hidden = yes", ev)
        self.assertIn("gm_arch_pass = yes trigger_event = { id = monument_events.20 }", ev)

    def test_the_open_row_says_abroad_for_the_viewer(self):
        sg = read(SGUIS)
        self.assertIn("gm_arch_would_dig_abroad_by = { WHO = root ARTICLE = archaeological_concession }",
                      squash(block(sg, "gm_arch_abroad_concession_sgui")))
        permit = squash(block(sg, "gm_arch_abroad_permit_sgui"))
        self.assertIn("NOT = { gm_arch_would_dig_abroad_by = { WHO = root ARTICLE = archaeological_concession } }", permit,
                      "a concession wins over a permit")
        for name in ("gm_arch_abroad_concession_sgui", "gm_arch_abroad_permit_sgui"):
            self.assertNotIn("effect", block(sg, name), "display only")
        for name in ("gm_arch_launch_antiquarian_sgui", "gm_arch_launch_systematic_sgui", "gm_arch_launch_forensic_sgui"):
            self.assertIn("gm_arch_may_dig_ground = { WHO = root }", squash(block(sg, name)), name)


if __name__ == "__main__":
    unittest.main()
