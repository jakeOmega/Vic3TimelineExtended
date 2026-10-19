"""Grand Monument trophies (phase 5): the share each form gives up, the
trophy's name, the monthly pass, the totals, the ways home and the panels,
pinned against the registry's tables.

Design: docs/superpowers/specs/2026-10-12-grand-monument-trophies-design.md.
Adding a form to FORMS (test_grand_monument_registry.py) fails here until it
has a share in TROPHY_SHARES, its branch in the share triggers and, for a
piece or token, its part name. Adding a landmark fails until the trophy's
landmark name has its branch. Adding a trophy of 1836 is a row in
TROPHIES_1836 (loot spec 2026-10-12 §2), and an unplaced LANDMARKS row when
no monument of its own stands.

Run: python3 -m unittest test_grand_monument_trophies -v
"""
import re
import unittest
from collections import namedtuple

from test_grand_monument_registry import (
    BUILDING_FORMS, BUILT, DEDICATIONS, FORMS, LANDMARKS, NAMESAKES, PICTURES, RETIRED_FORMS, TROPHY_CODE_BASE,
    TROPHY_PICTURES, block, committed, loc, picture_key, raw_block_at, read, squash, strip_comments,
)

TR_EFFECTS = "common/scripted_effects/gm_trophy_effects.txt"
TR_TRIGGERS = "common/scripted_triggers/gm_trophy_triggers.txt"
TR_VALUES = "common/script_values/gm_trophy_values.txt"
TR_SGUIS = "common/scripted_guis/gm_trophy_sguis.txt"
TR_ON_ACTIONS = "common/on_actions/gm_trophy_on_actions.txt"
TR_CUSTOM_LOC = "common/customizable_localization/gm_trophy_custom_loc.txt"
TR_EVENTS = "events/monument_trophy_events.txt"
TR_GUI = "gui/gm_trophy_widgets.gui"
PICTURE_EFFECTS = "common/scripted_effects/gm_picture_effects.txt"
ARTICLE_RETURN = "common/treaty_articles/118_return_cultural_property.txt"
ARTICLE_SURRENDER = "common/treaty_articles/119_surrender_monument.txt"
EFFECTS = "common/scripted_effects/gm_effects.txt"
TRIGGERS = "common/scripted_triggers/monument_triggers.txt"
VALUES = "common/script_values/gm_values.txt"
MODIFIERS = "common/static_modifiers/gm_modifiers.txt"
JE = "common/journal_entries/je_grand_monuments.txt"
WIDGET = "gui/journal_entry_widgets/grand_monuments_widget.gui"
STATE_WIDGETS = "gui/te_state_panel_widgets.gui"
STATES_PANEL = "gui/states_panel.gui"
DEBUG_EVENTS = "events/te_debug_monuments_events.txt"
MESSAGES = "common/messages/extra_messages.txt"

# What a taking carries off, by form (spec §1): every form a monument can
# have, once. "object" goes whole, "piece" a quarter, "token" a tenth.
TROPHY_SHARES = {
    "object": ("column", "obelisk", "statue", "stele", "pillar", "high_cross", "rune_stone", "menorah",
               "sun_stone", "stela"),
    "piece": ("arch", "gate", "tower", "bell_tower", "round_tower", "rock_cut"),
    "token": ("hall", "hall_of_fame", "pantheon", "forum", "stoa", "court", "colonnade", "mausoleum", "pyramid",
              "pagoda", "memorial_church", "rock_hewn_church", "hill_shrine", "sacred_oak", "memorial",
              "opera_house", "gardens", "observatory", "exhibition_hall", "stadium"),
}
SHARE_VALUES = {"object": 1, "piece": 0.25, "token": 0.1}
# A landmark whose piece has its own name, ahead of the forms' (spec §1; loot
# spec 2026-10-12 §1).
LANDMARK_PARTS = {
    "brandenburg_gate": "gm_tr_part_quadriga",
    "parthenon": "gm_tr_part_marbles",
    "temple_of_dendera": "gm_tr_part_zodiac",
    "royal_palace_of_benin": "gm_tr_part_bronzes",
    "royal_palace_of_kumasi": "gm_tr_part_gold_regalia",
    "imperial_city_of_hue": "gm_tr_part_imperial_treasury",
    "persepolis": "gm_tr_part_reliefs",
    "red_fort": "gm_tr_part_mughal_regalia",
    "great_zimbabwe": "gm_tr_part_soapstone_birds",
    "royal_palaces_of_abomey": "gm_tr_part_thrones_and_statues",
    "klungkung_palace": "gm_tr_part_royal_regalia",
    "royal_palace_of_kandy": "gm_tr_part_throne",
    "uffizi_gallery": "gm_tr_part_medici_venus",
    "capitoline_museums": "gm_tr_part_dying_gaul",
    "bodrum_castle": "gm_tr_part_mausoleum_friezes",
    "temples_of_baalbek": "gm_tr_part_temple_carvings",
    "palmyra": "gm_tr_part_funerary_busts",
    "xanthos": "gm_tr_part_nereid_monument",
    "arch_of_ctesiphon": "gm_tr_part_treasures_of_khosrow",
    "nineveh_library": "gm_tr_part_nineveh_reliefs",
    "vindolanda_tablets": "gm_tr_part_ink_tablets",
    "troy_hisarlik": "gm_tr_part_priams_treasure",
    "mycenae_grave_circle": "gm_tr_part_mask_of_agamemnon",
    "pergamon_altar": "gm_tr_part_gigantomachy_frieze",
    "deir_el_bahari_cache": "gm_tr_part_royal_mummies",
    "ishtar_gate_babylon": "gm_tr_part_ishtar_gate",
    "palace_of_knossos": "gm_tr_part_bull_leaping_frescoes",
    "machu_picchu": "gm_tr_part_machu_picchu_finds",
    "mohenjo_daro": "gm_tr_part_indus_seals",
    "tomb_of_tutankhamun": "gm_tr_part_golden_mask",
    "royal_cemetery_at_ur": "gm_tr_part_standard_of_ur",
    "sanxingdui_pits": "gm_tr_part_bronze_masks",
    "sutton_hoo": "gm_tr_part_helmet_and_regalia",
    "tomb_of_pakal": "gm_tr_part_jade_mask",
    "mawangdui_tombs": "gm_tr_part_silk_banner",
    "terracotta_army": "gm_tr_part_terracotta_warriors",
    "tomb_of_philip_ii": "gm_tr_part_golden_larnax",
    "tomb_of_marquis_yi": "gm_tr_part_chime_bells",
    "royal_tombs_of_sipan": "gm_tr_part_sipan_regalia",
    "gobekli_tepe": "gm_tr_part_t_pillars",
    "olympia": "gm_tr_part_hermes_of_praxiteles",
    "delphi": "gm_tr_part_charioteer_of_delphi",
    "sidon_necropolis": "gm_tr_part_sidon_sarcophagi",
    "pompeii": "gm_tr_part_alexander_mosaic",
}
# The occasion patterns of NAMESAKES, plus the namesakes with one pattern.
NAME_PATTERNS = [p for patterns in NAMESAKES.values() for p in patterns]
IGS = ("armed_forces", "devout", "industrialists", "intelligentsia", "landowners", "petty_bourgeoisie",
       "rural_folk", "trade_unions")


def all_forms():
    return set(FORMS) | set(RETIRED_FORMS) | set(BUILDING_FORMS.values())


def custom_loc_branches(name):
    """(flag, localization_key) for each text branch of a container target."""
    body = block(read(TR_CUSTOM_LOC), name)
    assert body is not None, name
    return re.findall(r"flag:(\w+) \}\s*localization_key = (\w+)", body)


class ShareTests(unittest.TestCase):
    def test_every_form_has_one_share(self):
        listed = [f for forms in TROPHY_SHARES.values() for f in forms]
        self.assertEqual(len(listed), len(set(listed)), "a form in two shares")
        self.assertEqual(set(listed), all_forms())

    def test_the_share_triggers_match_the_table(self):
        t = read(TR_TRIGGERS)
        for kind in ("object", "piece"):
            body = block(t, f"gm_state_tr_form_is_{kind}")
            self.assertEqual(set(re.findall(r"var:gm_form = flag:(\w+)", body)), set(TROPHY_SHARES[kind]), kind)

    def test_the_share_value(self):
        body = squash(block(read(TR_VALUES), "gm_state_tr_share"))
        self.assertTrue(body.startswith(f"value = {SHARE_VALUES['token']}"), body)
        self.assertIn(f"limit = {{ gm_state_tr_form_is_piece = yes }} value = {SHARE_VALUES['piece']}", body)
        self.assertIn(f"limit = {{ gm_state_tr_form_is_object = yes }} value = {SHARE_VALUES['object']}", body)
        # The object's branch comes last: it wins.
        self.assertLess(body.find("gm_state_tr_form_is_piece"), body.find("gm_state_tr_form_is_object"))

    def test_levels_and_value(self):
        v = read(TR_VALUES)
        self.assertEqual(squash(block(v, "gm_state_tr_levels")),
                         "value = gm_state_primary_levels multiply = gm_state_tr_share ceiling = yes min = 1 "
                         "max = gm_state_primary_levels")
        self.assertEqual(squash(block(v, "gm_state_tr_value")),
                         "value = gm_state_tr_start add = gm_state_tr_age divide = 2 ceiling = yes")

    def test_never_a_shrine_and_never_twice_in_ten_years(self):
        takeable = squash(block(read(TR_TRIGGERS), "gm_state_tr_takeable"))
        for line in ("gm_system_enabled = yes", "gm_state_is_dedicated = yes", "gm_state_kind_faith = no",
                     "NOT = { has_variable = gm_restore_pm }", "NOT = { has_variable = gm_ceremony_pending }",
                     "NOT = { has_variable = gm_carried_off }", "NOT = { has_variable = gm_tr_cooldown }"):
            self.assertIn(line, takeable)
        piece = squash(block(read(TR_EFFECTS), "gm_state_tr_remove_piece"))
        self.assertIn("set_variable = { name = gm_tr_cooldown days = 3650 }", piece)


class RouteTests(unittest.TestCase):
    def test_occupation_reads_the_provinces(self):
        body = squash(block(read(TR_TRIGGERS), "gm_state_tr_occupied_by"))
        self.assertIn("owner = { has_war_with = $WHO$ }", body)
        self.assertIn("gm_state_tr_holds_half = { WHO = $WHO$ }", body)
        self.assertIn("NOT = { AND = { owner = { has_variable = te_cw_role } $WHO$ = { has_variable = te_cw_role } } }",
                      body, "never between the two sides of a civil war")
        half = squash(block(read(TR_TRIGGERS), "gm_state_tr_holds_half"))
        self.assertEqual(half, "$WHO$ = { save_temporary_scope_as = gm_tmp_tr_who } gm_state_tr_who_province_share >= 0.5")
        share = squash(block(read(TR_VALUES), "gm_state_tr_who_province_share"))
        self.assertIn("every_province = { limit = { controller = scope:gm_tmp_tr_who } add = 1 }", share)

    def test_no_province_iterator_runs_from_a_state(self):
        """2026-10-16: the engine registers the province iterators from a province. random_province in
        gm_state_tr_find_occupier logged 'Wrong scope for effect: state, expected province' once a month for every
        monument state and never found an occupier, so no trophy was ever taken by occupation. Only a script value's
        every_province reads a state's provinces (the base game's occupation_values.txt)."""
        for path in (TR_EFFECTS, TR_TRIGGERS, EFFECTS, "common/scripted_triggers/gm_monument_triggers.txt"):
            code = re.sub(r"#[^\n]*", "", read(path))
            self.assertIsNone(re.search(r"\b(random|any|every|ordered)_province\b", code), path)
        find = squash(block(read(TR_EFFECTS), "gm_state_tr_find_occupier"))
        self.assertIn("random_enemy_in_war = {", find)
        self.assertIn("gm_state_tr_occupied_by = { WHO = scope:gm_tmp_tr_enemy }", find)
        # the self-check gm_occupation_read, once a game, in a save under way too
        self.assertIn("gm_tr_occupation_read_self_check = yes", squash(block(read(EFFECTS), "gm_state_monthly")))
        check = squash(block(read(TR_EFFECTS), "gm_tr_occupation_read_self_check"))
        for line in ("owner = { is_at_war = no }", "gm_state_tr_holds_half = { WHO = owner }",
                     "TE_SELF_CHECK OK gm_occupation_read", "TE_SELF_CHECK BROKEN gm_occupation_read"):
            self.assertIn(line, check)

    def test_own_state_only_unincorporated_and_not_ours(self):
        body = squash(block(read(TR_TRIGGERS), "gm_state_tr_own_takeable_by"))
        self.assertEqual(body, "owner = $WHO$ is_incorporated = no has_variable = gm_built_by "
                               "gm_state_built_by_owner = no")

    def test_the_builder_is_recorded_and_forgotten(self):
        e = read(EFFECTS)
        self.assertIn("gm_state_record_builder = yes", squash(block(e, "gm_state_first_sight")))
        self.assertIn("gm_state_record_builder = yes", squash(block(e, "gm_state_dedicate")))
        clear = squash(block(e, "gm_clear_state"))
        for var in ("gm_built_by", "gm_carried_off", "gm_tr_cooldown", "gm_tr_offered_to"):
            self.assertIn(f"gm_remove_state_var = {{ VAR = {var} }}", clear, var)
        # The opportunity's gift and a taken piece keep every record.
        self.assertNotIn("gm_clear_state", squash(block(read(TR_EFFECTS), "gm_state_tr_remove_piece")))

    def test_a_monument_carried_off_is_not_torn_down(self):
        monthly = squash(block(read(EFFECTS), "gm_state_monthly"))
        self.assertIn("NOT = { has_variable = gm_carried_off } } gm_state_record_teardown = yes", monthly)
        self.assertTrue(monthly.split(" } else = {", 1)[0].endswith("gm_state_tr_monthly = yes"),
                        "the trophy part runs last in the monument's branch: a taking removes the building")

    def test_the_former_owner_is_stamped(self):
        self.assertIn("gm_state_tr_changed_hands = yes", squash(block(read(EFFECTS), "gm_state_changed_hands")))
        monthly = squash(block(read(TR_EFFECTS), "gm_state_tr_monthly"))
        self.assertTrue(monthly.startswith("set_variable = { name = gm_holder value = owner }"))


class TakingTests(unittest.TestCase):
    """No taking runs where a tooltip walks the effect (spec §4, as the gift)."""

    def test_clicks_options_and_treaties_only_order(self):
        sguis = strip_comments(read(TR_SGUIS))
        for name in ("gm_tr_take_sgui", "gm_tr_take_site_sgui", "gm_tr_return_sgui"):
            effect = squash(block(block(sguis, name), "effect"))
            for doer in ("gm_state_tr_take ", "gm_tr_take_from_site", "gm_tr_return_home", "create_container"):
                self.assertNotIn(doer, effect, name)
        ev = squash(raw_block_at(strip_comments(read(TR_EVENTS)), r"(?m)^monument_trophy_events\.1\s*=\s*\{"))
        self.assertIn("gm_state_tr_choose_take = { WHO = root ROUTE = occupation }", ev)
        choose = squash(block(read(TR_EFFECTS), "gm_state_tr_choose_take"))
        self.assertEqual(choose, "custom_tooltip = { text = gm_tr_take_$ROUTE$_tt "
                                 "gm_state_tr_order_take = { WHO = $WHO$ ROUTE = $ROUTE$ } }")
        for path, call in ((ARTICLE_SURRENDER, "gm_state_tr_order_take = { WHO = scope:gm_tr_treaty_taker ROUTE = treaty }"),
                           (ARTICLE_RETURN, "trigger_event = { id = monument_trophy_events.13 }")):
            force = squash(block(read(path), "on_entry_into_force"))
            self.assertTrue(force.startswith("scope:article_options = { if = { limit = { exists = "), path)
            self.assertIn(call, force, path)

    def test_only_a_claimant_can_demand_the_return(self):
        # ROOT is the prospective source (the holder) in possible, and a war goal enforcing the
        # article checks possible but not can_ratify: an either-way OR let the UK, holding Egypt's
        # trophies, demand their return from Egypt (2026-10-13).
        self.assertEqual(squash(block(read(ARTICLE_RETURN), "possible")),
                         "gm_system_enabled = yes gm_tr_country_holds_from = { CLAIMANT = scope:other_country }")

    def test_the_hidden_events_do_the_work(self):
        events = strip_comments(read(TR_EVENTS))
        for n, doer in ((10, "gm_state_tr_take = { WHO = scope:gm_tr_order_by ROUTE = occupation }"),
                        (11, "gm_tr_take_from_site = { WHO = root }"),
                        (12, "gm_tr_return_home = { RELATIONS = yes }"),
                        (13, "gm_tr_return_all_from = yes")):
            ev = squash(raw_block_at(events, rf"(?m)^monument_trophy_events\.{n}\s*=\s*\{{"))
            self.assertIn("hidden = yes", ev, n)
            self.assertIn(doer, ev, n)
            self.assertIn("gm_tr_finish = yes", ev, n)

    def test_the_offer_defaults_to_leaving_it(self):
        ev = squash(raw_block_at(strip_comments(read(TR_EVENTS)), r"(?m)^monument_trophy_events\.1\s*=\s*\{"))
        leave = ev.split("name = monument_trophy_events.1.b", 1)[1]
        self.assertIn("default_option = yes", leave)

    def test_the_trophy_takes_its_records(self):
        make = squash(block(read(TR_EFFECTS), "gm_state_tr_make_trophy"))
        for state_var, tr_var in (("gm_skin", "gm_tr_skin"), ("gm_form", "gm_tr_form"),
                                  ("gm_landmark", "gm_tr_landmark"), ("gm_namesake", "gm_tr_namesake"),
                                  ("gm_name_year", "gm_tr_name_year"), ("gm_name_char", "gm_tr_name_char"),
                                  ("gm_name_occasion", "gm_tr_name_occasion"),
                                  ("gm_name_enemy_cap", "gm_tr_name_enemy_cap"), ("gm_name", "gm_tr_name"),
                                  ("gm_honoree", "gm_tr_honoree"), ("gm_honoree_ig", "gm_tr_honoree_ig"),
                                  ("gm_signature", "gm_tr_signature"), ("gm_sig_parent", "gm_tr_sig_parent")):
            self.assertIn(f"gm_tr_copy_from_state = {{ FROM = {state_var} TO = {tr_var} }}", make, state_var)
            rebuilt = (squash(block(read(TR_EFFECTS), "gm_state_tr_rebuild_from_moving")) + " "
                       + squash(block(read(TR_EFFECTS), "gm_state_tr_take_records_from_moving")))
            self.assertIn(f"gm_tr_copy_to_state = {{ FROM = {tr_var} TO = {state_var} }}", rebuilt, tr_var)
        record = squash(block(read(TR_EFFECTS), "gm_tr_record_dedication"))
        for d in DEDICATIONS:
            self.assertIn(f"gm_tr_record_dedication_one = {{ KEY = {d.key} }}", record, d.key)

    def test_a_trophy_comes_home_whole_and_never_as_a_copy(self):
        # A standing monument takes the levels into its records; none is
        # built again with the trophy's (gm_state_tr_receive picks).
        self.assertIsNone(block(read(TR_EFFECTS), "gm_state_tr_add_levels"))
        rebuilt = (squash(block(read(TR_EFFECTS), "gm_state_tr_rebuild_from_moving")) + " "
                       + squash(block(read(TR_EFFECTS), "gm_state_tr_take_records_from_moving")))
        self.assertIn("gm_tr_copy_to_state = { FROM = gm_tr_dedication TO = gm_restore_pm }", rebuilt)
        for line in ("set_variable = gm_seen",
                     "set_variable = { name = gm_ceremony_level value = scope:gm_tr_moving.var:gm_tr_levels }",
                     "set_variable = { name = gm_built_by value = owner }",
                     "set_variable = { name = gm_rebuilding days = 1 }"):
            self.assertIn(line, rebuilt)


class TakerTests(unittest.TestCase):
    """A trophy remembers who carried it off (gm_tr_taken_by, 2026-10-12). Without it an AI that took a
    monument from its own colony brought it straight back at the next pass, for the Homecoming's ten years
    of legitimacy, and a piece could be taken again once its cooldown ran out."""

    def test_the_record(self):
        e = read(TR_EFFECTS)
        self.assertIn("set_variable = { name = gm_tr_taken_by value = scope:gm_tr_taker }",
                      squash(block(e, "gm_state_tr_make_trophy")))
        self.assertIn("set_variable = { name = gm_tr_taken_by value = scope:gm_tr_taker }",
                      squash(block(e, "gm_tr_take_from_site")), "a new looter is its new taker")
        self.assertEqual(squash(block(read(TR_TRIGGERS), "gm_tr_held_by_its_taker")),
                         "has_variable = gm_tr_taken_by var:gm_tr_taken_by ?= { save_temporary_scope_as = "
                         "gm_tmp_tr_taker } gm_tr_held_by = { WHO = scope:gm_tmp_tr_taker }")

    def test_the_ai_keeps_what_it_took(self):
        one = squash(block(read(TR_EFFECTS), "gm_tr_monthly_one"))
        self.assertIn("if = { limit = { gm_tr_holder_owns_origin = yes } if = { limit = { gm_tr_held_by_its_taker = "
                      "no } add_to_temporary_list = gm_tr_ai_home } } else_if = {", one,
                      "owning the origin never falls through to the ally return")
        self.assertIn("gm_tr_holder_owns_origin = yes gm_tr_held_by_its_taker = no NOT = { has_variable = "
                      "gm_tr_home_notified }", one, "no 'within reach' notice for one we took ourselves")

    def test_no_homecoming_for_its_taker(self):
        home = squash(block(read(TR_EFFECTS), "gm_tr_return_home"))
        guard = "if = { limit = { NOT = { var:gm_tr_taken_by ?= { this = scope:gm_tr_receiver } } } scope:gm_tr_receiver = {"
        self.assertIn(guard, home)
        self.assertLess(home.index(guard), home.index("name = gm_boon_homecoming"))
        effect = squash(block(block(strip_comments(read(TR_SGUIS)), "gm_tr_return_sgui"), "effect"))
        self.assertTrue(effect.startswith("scope:gm_tr = { if = { limit = { gm_tr_claimed_by = { WHO = root } "
                                          "gm_tr_held_by_its_taker = yes } custom_tooltip = { text = "
                                          "gm_tr_bring_home_own_tt"), effect)
        L = loc()
        self.assertIn("no Homecoming", L["gm_tr_bring_home_own_tt"])
        self.assertIn("Homecoming", L["gm_tr_bring_home_tt"])


class ConsequenceTests(unittest.TestCase):
    def test_the_numbers(self):
        v = read(TR_VALUES)
        self.assertEqual(squash(block(v, "gm_tr_infamy")),
                         "value = var:gm_tr_tmp_grandeur divide = 5 add = 2 max = 8 if = { limit = { "
                         "has_global_variable = un_agency_unesco } multiply = 2 }")
        for name, value in (("gm_tr_relations_taken", "-30"), ("gm_tr_relations_returned", "40"),
                            ("gm_tr_war_support", "10"), ("gm_tr_ai_own_chance", "1"),
                            ("gm_tr_ai_return_chance", "2")):
            self.assertRegex(strip_comments(v), rf"(?m)^{name} = {value}$", name)
        own = squash(block(read(TR_EFFECTS), "gm_state_tr_consequences_own"))
        self.assertTrue(own.startswith("add_radicals_in_state = { value = 0.1 }"))
        war = squash(block(read(TR_EFFECTS), "gm_state_tr_consequences_occupation"))
        for line in ("change_infamy = gm_tr_infamy",
                     "change_relations = { country = scope:gm_tr_victim value = gm_tr_relations_taken }",
                     "add_war_war_support = { target = scope:gm_tr_victim value = gm_tr_war_support }"):
            self.assertIn(line, war)

    def test_the_homecoming(self):
        body = block(read(MODIFIERS), "gm_boon_homecoming")
        fields = [k for k in re.findall(r"(?m)^\s*(\w+)\s*=", body) if k != "icon"]
        self.assertEqual(fields, ["country_legitimacy_base_add"])
        self.assertIn("country_legitimacy_base_add = 5", body)
        home = squash(block(read(TR_EFFECTS), "gm_tr_return_home"))
        self.assertIn("set_variable = { name = gm_boon_homecoming value = gm_boon_months }", home)
        e = read(EFFECTS)
        self.assertIn("gm_tr_add_national = yes", squash(block(e, "gm_apply_national_modifiers")))
        self.assertIn("gm_tr_remove_national = yes", squash(block(e, "gm_remove_national_modifiers")))
        self.assertIn("gm_tr_country_monthly = yes", squash(block(e, "gm_country_monthly")))
        self.assertEqual(squash(block(read(TR_EFFECTS), "gm_tr_country_monthly")), "gm_tick_boon = { SRC = homecoming }")
        L = loc()
        for key in ("gm_boon_homecoming", "gm_boon_homecoming_desc", "gm_boon_homecoming_effect"):
            self.assertIn(key, L)
        self.assertTrue(L["gm_boon_homecoming_effect"].startswith("#G +5#!"))

    def test_the_ai_follows_law_stances(self):
        minded = squash(block(read(TR_TRIGGERS), "gm_tr_ig_looting_minded"))
        self.assertIn("is_in_government = yes", minded)
        for law in ("law_total_war", "law_ethnostate", "law_national_supremacy"):
            self.assertIn(f"law_stance = {{ law = law_type:{law} value > neutral }}", minded, law)
        base = squash(block(read(TR_VALUES), "gm_tr_ai_loot_base"))
        self.assertIn("every_interest_group = { limit = { gm_tr_ig_looting_minded = yes } add = { value = ig_clout "
                      "multiply = 10 } }", base)
        self.assertIn("limit = { is_country_type = unrecognized } add = 5", base)
        for name in ("gm_tr_ai_loot_chance", "gm_tr_ai_loot_chance_trophy"):
            body = squash(block(read(TR_VALUES), name))
            self.assertIn("scope:gm_tr_taker = { add = gm_tr_ai_loot_base }", body, name)
            self.assertIn("limit = { has_global_variable = un_agency_unesco } multiply = 0.25", body, name)


class PassTests(unittest.TestCase):
    def test_wired_to_the_global_pulse(self):
        oa = squash(strip_comments(read(TR_ON_ACTIONS)))
        self.assertIn("on_monthly_pulse = { on_actions = { gm_trophy_monthly_on_action } }", oa)
        self.assertIn("effect = { gm_trophy_monthly = yes }", oa)
        self.assertTrue(squash(block(read(TR_EFFECTS), "gm_trophy_monthly")).endswith("gm_trophy_pass = yes"))

    def test_the_pass_clears_before_it_lists(self):
        body = squash(block(read(TR_EFFECTS), "gm_trophy_pass"))
        self.assertLess(body.find("clear_variable_list = gm_trophies_held"), body.find("gm_tr_list_one = yes"))
        self.assertLess(body.find("clear_variable_list = gm_trophies_here"), body.find("gm_tr_list_one = yes"))
        listed = squash(block(read(TR_EFFECTS), "gm_tr_list_one"))
        for line in ("add_to_variable_list = { name = gm_trophies_here", "add_to_variable_list = { name = gm_trophies_held",
                     "add_to_variable_list = { name = gm_trophies_abroad",
                     "change_variable = { name = gm_tr_held_grandeur add = scope:gm_tr_listing.var:gm_tr_grandeur }"):
            self.assertIn(line, listed)

    def test_a_return_leaves_no_dead_reference(self):
        home = squash(block(read(TR_EFFECTS), "gm_tr_return_home"))
        self.assertLess(home.find("remove_list_global_variable = { name = gm_trophies"), home.find("destroy_container = yes"))
        self.assertTrue(home.rstrip(" }").endswith("destroy_container = yes"))


class TotalsTests(unittest.TestCase):
    def test_standing_and_the_armed_forces(self):
        self.assertTrue(squash(block(read(VALUES), "gm_sum_standing")).endswith("add = gm_tr_disp_held_grandeur"))
        self.assertIn("change_variable = { name = gm_ig_net_$IG$ add = gm_tr_ig_share_$IG$ }",
                      squash(block(read(EFFECTS), "gm_compute_ig")))
        v = strip_comments(read(TR_VALUES))
        for ig in IGS:
            if ig == "armed_forces":
                self.assertEqual(squash(block(v, f"gm_tr_ig_share_{ig}")), "value = gm_tr_disp_held_grandeur")
            else:
                self.assertRegex(v, rf"(?m)^gm_tr_ig_share_{ig} = 0$", ig)

    def test_a_trophys_signature_counts_for_its_holder(self):
        """Signatures spec 2026-10-16 §2.4: a trophy keeps its unique dedication
        and its holder counts the trophy's own grandeur toward its sum, on its
        parent, whatever the holder's government; no local effect, no group."""
        sums = squash(strip_comments(block(read("common/scripted_effects/gm_signature_effects.txt"),
                                           "gm_sig_compute_sums")))
        held = sums[sums.index("variable = gm_trophies_held"):]
        self.assertTrue(held.startswith("variable = gm_trophies_held limit = { has_variable = gm_tr_signature "
                                        "has_variable = gm_tr_grandeur gm_mon_sig_on_parent = yes }"), held[:200])
        self.assertIn("gm_mon_sig_add_to_sum = { SIG = antiquity G = gm_tr_grandeur }", held)
        self.assertNotIn("gm_mon_status_fits", held[:held.index("gm_mon_sig_add_to_sum")])
        piece = squash(block(read("common/scripted_effects/gm_monument_effects.txt"), "gm_mon_tr_take_piece"))
        for key in ("gm_tr_signature", "gm_tr_sig_parent"):
            self.assertIn(f"gm_mon_copy_record = {{ KEY = {key} }}", piece, key)

    def test_the_entry_stays_for_trophies(self):
        je = squash(strip_comments(read(JE)))
        self.assertEqual(je.count("gm_tr_country_has_any = yes"), 2, "is_shown_when_inactive and possible")
        self.assertIn("gm_tr_country_idle = yes", squash(block(read(TRIGGERS), "gm_ledgers_idle")))
        self.assertIn("gm_tr_country_has_any = yes", squash(block(read(TRIGGERS), "gm_entry_unlocked")))
        refresh = squash(block(read(EFFECTS), "gm_country_refresh"))
        self.assertEqual(refresh.count("gm_tr_country_has_any = yes"), 2, "gm_active and add_journal_entry")


class NameTests(unittest.TestCase):
    def test_every_form_has_its_noun(self):
        branches = dict(custom_loc_branches("gm_tr_form_name"))
        self.assertEqual(set(branches), all_forms())
        L = loc()
        for form, key in branches.items():
            self.assertEqual(key, f"gm_form_{form}")
            self.assertIn(key, L)

    def test_every_piece_and_token_has_its_part(self):
        branches = custom_loc_branches("gm_tr_part_name")
        n = len(LANDMARK_PARTS)
        self.assertEqual(branches[:n], list(LANDMARK_PARTS.items()), "the landmarks' own parts first, the Quadriga's first")
        for key in LANDMARK_PARTS:
            self.assertIn(key, {lm.key for lm in LANDMARKS}, key)
        forms = {flag for flag, _ in branches[n:]}
        self.assertEqual(forms, set(TROPHY_SHARES["piece"]) | set(TROPHY_SHARES["token"]))
        L = loc()
        for _, key in branches:
            self.assertIn(key, L)

    def test_every_landmark_keeps_its_name(self):
        branches = custom_loc_branches("gm_tr_landmark_name")
        self.assertEqual([flag for flag, _ in branches], [lm.key for lm in LANDMARKS])
        for flag, key in branches:
            self.assertEqual(key, f"gm_skin_landmark_{flag}")

    def test_every_name_pattern_has_its_trophy_pattern(self):
        body = block(read(TR_CUSTOM_LOC), "gm_trophy_name")
        keys = re.findall(r"localization_key = (\w+)", body)
        L = loc()
        for pattern in NAME_PATTERNS:
            self.assertIn(f"gm_tr_name_{pattern}", keys, pattern)
        for key in keys:
            self.assertIn(key, L, key)
            self.assertNotIn("State.", L[key].replace("GetState.", ""), f"{key} reads a State context")

    def test_dedication_and_honours_names(self):
        # A unique dedication's names come first (signatures spec §3), the twelve after.
        plain = [(f, key) for f, key in custom_loc_branches("gm_tr_dedication_name") if key.startswith("pm_monument_")]
        self.assertEqual({f for f, _ in plain}, {d.key for d in DEDICATIONS})
        for d, key in plain:
            self.assertEqual(key, f"pm_monument_{d}")


class PanelTests(unittest.TestCase):
    def test_mounted(self):
        status = squash(strip_comments(raw_block_at(read(WIDGET),
                                                    r"(?m)^\ttype te_gm_status_sections = flowcontainer \{")))
        self.assertTrue(status.endswith("te_gm_sec_monuments = {} te_gm_sec_trophies = {} te_gm_sec_abroad = {}"),
                        status[-200:])
        self.assertIn("gm_tr_take_button = {}", squash(raw_block_at(read(WIDGET),
                                                                    r"(?m)^\ttype gm_monument_row = flowcontainer \{")))
        self.assertIn("gm_tr_take_button = {}", squash(raw_block_at(read(STATE_WIDGETS),
                                                                    r"(?m)^\ttype te_state_gm_card = flowcontainer \{")))
        self.assertIn("te_state_gm_card = {} te_state_gm_site_card = {} te_state_gm_trophy_card = {}", squash(strip_comments(read(STATES_PANEL))))

    def test_flags_say_their_default(self):
        gui = strip_comments(read(TR_GUI))
        flags = set(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", gui))
        self.assertEqual(flags, {"gm_trophies_closed", "gm_abroad_closed"})
        for f in flags:
            negated = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{f}'\)\s*\)", gui))
            bare = len(re.findall(rf"GetVariableSystem\.Exists\('{f}'\)", gui)) - negated
            self.assertEqual((bare, negated), (1, 2), f)

    def test_rows_read_no_journal_entry(self):
        """Gotcha #24: a datamodel row renders its tooltips without JournalEntry."""
        gui = read(TR_GUI)
        L = loc()
        for row in ("gm_tr_row_held", "gm_tr_row_abroad", "gm_tr_row_site", "gm_tr_take_button"):
            body = raw_block_at(gui, rf"(?m)^\ttype {row} = \w+ \{{")
            self.assertNotIn("JournalEntry", body, row)
            for key in re.findall(r'(?:text|tooltip) = "(\w+)"', body):
                self.assertNotIn("JournalEntry", L.get(key, ""), (row, key))

    def test_every_gui_loc_key_exists(self):
        L = loc()
        for key in re.findall(r'(?:text|tooltip) = "(\w+)"', strip_comments(read(TR_GUI))):
            self.assertIn(key, L, key)

    def test_every_tooltip_and_notice_key_exists(self):
        L = loc()
        keys = set(re.findall(r"text = (gm_tr_\w+)", read(TR_SGUIS) + read(TR_TRIGGERS)))
        keys |= {f"gm_tr_take_{route}_tt" for route in ("occupation", "own")}
        for key in sorted(keys):
            self.assertIn(key, L, key)
        for notice in re.findall(r"post_notification = (\w+)", read(TR_EFFECTS)):
            self.assertIsNotNone(block(read(MESSAGES), notice), notice)
            for suffix in ("name", "desc"):
                self.assertIn(f"notification_{notice}_{suffix}", L, notice)
        for article in ("return_cultural_property", "surrender_monument"):
            for suffix in ("", "_desc", "_effects_desc", "_article_short_desc"):
                self.assertIn(f"{article}{suffix}", L, article + suffix)


class StateCardViewTests(unittest.TestCase):
    """The state view's Trophies on Display card has three views: Full (the pictured rows, with what each
    counts for spelled out), Short (one line a trophy, no pictures, the rest on hover) and Collapsed (the
    summary line alone: how many, and what they count for together). The client-side gm_state_tr_view
    chooses; unset is Full, so a fresh session opens as before."""

    VIEW = "gm_state_tr_view"

    @staticmethod
    def code(text):
        """A .gui block without its `###` comment lines (`#tooltippable` is code, so not strip_comments)."""
        return re.sub(r"(?m)^\s*###.*$", "", text)

    def type_body(self, name, kind="flowcontainer"):
        raw = raw_block_at(read(TR_GUI), rf"(?m)^\ttype {name} = {kind} \{{")
        self.assertIsNotNone(raw, name)
        return squash(self.code(raw))

    def test_the_pass_totals_what_stands_in_each_state(self):
        e = read(TR_EFFECTS)
        listed = squash(block(e, "gm_tr_list_one"))
        self.assertIn("gm_tr_count_add = { VAR = gm_tr_here_count ADD = 1 } gm_tr_count_add = { VAR = "
                      "gm_tr_here_grandeur ADD = scope:gm_tr_listing.var:gm_tr_grandeur }", listed)
        # The same grandeur the holder's total adds.
        self.assertIn("change_variable = { name = gm_tr_held_grandeur add = scope:gm_tr_listing.var:gm_tr_grandeur }",
                      listed)
        cleared = squash(block(e, "gm_trophy_pass"))
        self.assertIn("remove_variable = gm_tr_here_count gm_remove_state_var = { VAR = gm_tr_here_grandeur }", cleared)
        self.assertLess(cleared.find("gm_remove_state_var = { VAR = gm_tr_here_grandeur }"),
                        cleared.find("gm_tr_list_one = yes"), "cleared before it is written")
        self.assertEqual(squash(block(read(TR_VALUES), "gm_state_tr_disp_here_grandeur")),
                         "value = 0 if = { limit = { has_variable = gm_tr_here_grandeur } "
                         "value = var:gm_tr_here_grandeur }")

    def test_three_buttons_choose_the_view(self):
        card = self.type_body("te_state_gm_trophy_card")
        self.assertNotIn("GetVariableSystem.Toggle", card, "a Toggle flag cannot hold three views")
        buttons = re.findall(
            r'gm_tr_view_button = \{ tooltip = "(\w+)" blockoverride "tr_view_button" \{ enabled = "([^"]+)" '
            r'onclick = "([^"]+)" \} blockoverride "tr_view_button_text" \{ text = "(\w+)" \} \}', card)
        self.assertEqual([(b[0], b[3]) for b in buttons],
                         [("gm_state_tr_view_full_tt", "gm_state_tr_view_full"),
                          ("gm_state_tr_view_short_tt", "gm_state_tr_view_short"),
                          ("gm_state_tr_view_collapsed_tt", "gm_state_tr_view_collapsed")])
        # Full is the unset value; each button is off while its own view shows.
        self.assertEqual(buttons[0][1:3], (f"[GetVariableSystem.Exists('{self.VIEW}')]",
                                           f"[GetVariableSystem.Clear('{self.VIEW}')]"))
        for (_, enabled, onclick, _), view in zip(buttons[1:], ("short", "collapsed")):
            self.assertEqual(enabled, f"[Not(GetVariableSystem.HasValue('{self.VIEW}', '{view}'))]")
            self.assertEqual(onclick, f"[GetVariableSystem.Set('{self.VIEW}', '{view}')]")

    def test_each_view_shows_its_rows_and_collapsed_none(self):
        card = self.type_body("te_state_gm_trophy_card")
        lists = re.findall(r'flowcontainer = \{ visible = "([^"]+)" direction = vertical ignoreinvisible = yes '
                           r'spacing = \d+ datamodel = "\[State\.MakeScope\.GetList\(\'gm_trophies_here\'\)\]" '
                           r'item = \{ (\w+) = \{ datacontext = "\[Scope\.GetScriptContainer\]" \}', card)
        self.assertEqual(lists, [(f"[Not(GetVariableSystem.Exists('{self.VIEW}'))]", "gm_tr_row_site"),
                                 (f"[GetVariableSystem.HasValue('{self.VIEW}', 'short')]", "gm_tr_row_short")])
        self.assertEqual(card.count("GetList('gm_trophies_here')"), 2, "Collapsed lists no trophy")

    def test_the_summary_shows_but_for_a_full_view_of_one_trophy(self):
        card = self.type_body("te_state_gm_trophy_card")
        self.assertIn(f"textbox = {{ visible = \"[Or( GetVariableSystem.Exists('{self.VIEW}'), GreaterThan_CFixedPoint("
                      "State.MakeScope.ScriptValue('gm_state_tr_disp_here'), '(CFixedPoint)1' ) )]\" autoresize = yes",
                      card.replace("GreaterThan_CFixedPoint( ", "GreaterThan_CFixedPoint("))
        self.assertIn('tooltip = "gm_state_tr_summary_tt" text = "gm_state_tr_summary"', card)

    def test_short_is_a_line_with_the_rest_on_hover(self):
        row = self.type_body("gm_tr_row_short")
        self.assertNotIn("gm_tr_picture", row, "no pictures")
        self.assertIn('tooltip = "gm_tr_short_tt" text = "gm_tr_short_line"', row)
        # 392 + 6 + 112 = the card's 510 inside its margins.
        self.assertIn("spacing = 6", row)
        self.assertIn("minimumsize = { 392 -1 } maximumsize = { 392 -1 }", row)
        self.assertIn('blockoverride "tr_button_layout" { size = { 112 22 } parentanchor = vcenter }', row)
        self.assertEqual(392 + 6 + 112, 530 - 2 * 10)
        # The same scripted GUI, shown and run the same way, as the Full row's button.
        pick = r'blockoverride "tr_button" \{ (.*?) \} blockoverride "tr_button_text"'
        self.assertEqual(re.search(pick, row).group(1), re.search(pick, self.type_body("gm_tr_row_site")).group(1))

    def test_the_button_keeps_its_size_everywhere_else(self):
        btn = self.type_body("gm_tr_button", "button")
        self.assertIn('block "tr_button_layout" { size = { 200 26 } parentanchor = hcenter margin_top = 2 }', btn)
        self.assertIn('block "tr_button_text_width" { max_width = 190 }', btn)
        for row in ("gm_tr_row_held", "gm_tr_row_site"):
            self.assertNotIn("tr_button_layout", self.type_body(row), row)

    def test_full_shows_grandeur_with_aggregation_tooltip(self):
        site = self.type_body("gm_tr_row_site")
        self.assertIn('tooltip = "gm_tr_row_site_value_tt" text = "gm_tr_row_site_value"', site)
        L = loc()
        self.assertEqual(L["gm_tr_row_site_value"], "[concept_grandeur]: #v [ScriptContainer.MakeScope.ScriptValue('gm_tr_disp_grandeur')|0]#!")
        for word in ("concept_grandeur", "aggregated", "Timeline Extended", "Journal Entry"):
            self.assertIn(word, L["gm_tr_row_site_value_tt"], word)
        for word in ("concept_grandeur", "concept_prestige", "concept_cultural_pull", "Armed Forces"):
            self.assertIn(word, L["gm_state_tr_summary_tt"], word)

    def test_the_summary_counts_and_totals(self):
        L = loc()
        self.assertIn("'gm_state_tr_summary_one', 'gm_state_tr_summary_many'", L["gm_state_tr_summary"])
        self.assertIn("ScriptValue('gm_state_tr_disp_here'), '(CFixedPoint)1' )", L["gm_state_tr_summary"])
        self.assertIn("1#! trophy,", L["gm_state_tr_summary_one"])
        self.assertIn("ScriptValue('gm_state_tr_disp_here')|0]#! trophies,", L["gm_state_tr_summary_many"])
        for key in ("gm_state_tr_summary_one", "gm_state_tr_summary_many"):
            self.assertIn("ScriptValue('gm_state_tr_disp_here_grandeur')|0]", L[key], key)
            self.assertIn("[State.GetOwner.GetName]", L[key], key)

    def test_short_hover_carries_what_the_line_drops(self):
        L = loc()
        self.assertIn("ScriptValue('gm_tr_disp_is_landmark'), '(CFixedPoint)1' ), 'gm_tr_short_tt_landmark', "
                      "'gm_tr_short_tt_plain'",
                      L["gm_tr_short_tt"])
        for part in ("$gm_tr_row_title$", "$gm_tr_row_detail$", "$gm_tr_row_site_value$"):
            self.assertIn(part, L["gm_tr_short_tt_plain"], part)
        self.assertIn("$gm_tr_short_tt_plain$", L["gm_tr_short_tt_landmark"])
        self.assertIn("$gm_tr_row_landmark_tt$", L["gm_tr_short_tt_landmark"])
        for key in ("gm_tr_short_tt_plain", "gm_tr_short_tt_landmark"):
            self.assertFalse(L[key].startswith("\\n") or L[key].endswith("\\n"), key)

    def test_the_card_and_short_row_read_no_journal_entry(self):
        L = loc()
        gui = read(TR_GUI)
        for name in ("te_state_gm_trophy_card", "gm_tr_row_short", "gm_tr_view_button"):
            kind = "button" if name.endswith("button") else "flowcontainer"
            body = raw_block_at(gui, rf"(?m)^\ttype {name} = {kind} \{{")
            self.assertNotIn("JournalEntry", body, name)
            for key in re.findall(r'(?:text|tooltip) = "(\w+)"', body):
                self.assertNotIn("JournalEntry", L.get(key, ""), (name, key))
        for key in ("gm_tr_short_line", "gm_tr_short_tt", "gm_tr_row_site_value", "gm_tr_row_site_value_tt", "gm_state_tr_summary_tt"):
            self.assertNotIn("JournalEntry", L[key], key)


class PictureTests(unittest.TestCase):
    """A trophy shows the picture of the monument it was taken from (2026-10-13): the monuments' own
    table run on its records, and gm_picture's icons read from the container."""

    def test_the_monuments_table_on_the_trophys_records(self):
        body = squash(block(read(TR_EFFECTS), "gm_tr_update_picture"))
        self.assertEqual(body,
                         "gm_tr_lend_look = { FROM = gm_tr_skin TO = gm_skin } "
                         "gm_tr_lend_look = { FROM = gm_tr_form TO = gm_form } "
                         "gm_tr_lend_look = { FROM = gm_tr_landmark TO = gm_landmark } "
                         "set_variable = { name = gm_picture_code value = 1 } "
                         "if = { limit = { has_variable = gm_form } gm_picture_from_look = yes } "
                         "gm_state_picture_landmarks = yes "
                         "set_variable = { name = gm_tr_picture_code value = var:gm_picture_code } "
                         "gm_remove_state_var = { VAR = gm_skin } gm_remove_state_var = { VAR = gm_form } "
                         "gm_remove_state_var = { VAR = gm_landmark } gm_remove_state_var = { VAR = gm_picture_code } "
                         "gm_tr_picture_trophies = yes")
        self.assertEqual(squash(block(read(TR_EFFECTS), "gm_tr_lend_look")),
                         "if = { limit = { has_variable = $FROM$ } set_variable = { name = $TO$ value = var:$FROM$ } }")
        # The state's own update runs the same table, behind its dedicated check.
        self.assertIn("gm_picture_from_look = yes", squash(block(read(PICTURE_EFFECTS), "gm_state_update_picture")))

    def test_set_when_made_seeded_and_every_month(self):
        e = read(TR_EFFECTS)
        self.assertIn("gm_tr_copy_from_state = { FROM = gm_sig_parent TO = gm_tr_sig_parent } gm_tr_update_picture = yes",
                      squash(block(e, "gm_state_tr_make_trophy")), "after the records it reads")
        self.assertIn("set_variable = { name = gm_tr_namesake value = flag:landmark } gm_tr_sig_backfill = yes "
                      "gm_tr_update_picture = yes", squash(block(e, "gm_seed_trophy")))
        self.assertIn("every_in_global_list = { variable = gm_trophies gm_tr_repair_places = yes "
                      "gm_tr_update_picture = yes gm_tr_sig_backfill = yes }", squash(block(e, "gm_trophy_monthly")),
                      "a landmark drawn later, or an older save's trophy, catches up")

    def test_display_value_defaults_to_the_draped_picture(self):
        self.assertEqual(squash(block(read(TR_VALUES), "gm_tr_disp_picture_code")),
                         "value = 1 if = { limit = { has_variable = gm_tr_picture_code } value = var:gm_tr_picture_code }")

    def test_widget_has_every_picture(self):
        raw = raw_block_at(read(TR_GUI), r"(?m)^\ttype gm_tr_picture = widget \{")
        self.assertIsNotNone(raw)
        body = squash(strip_comments(raw))
        self.assertTrue(body.startswith("size = { 96 96 } icon = {"), body[:80])
        for code in PICTURES:
            self.assertIn(f"icon = {{ visible = \"[EqualTo_CFixedPoint( ScriptContainer.MakeScope.ScriptValue("
                          f"'gm_tr_disp_picture_code'), '(CFixedPoint){code}' )]\" size = {{ 100% 100% }} "
                          f"texture = \"gfx/interface/icons/gm_pictures/{picture_key(code)}.dds\" }}", body, code)
        self.assertEqual(body.count("icon = {"), len(PICTURES))
        self.assertNotIn("frame_tier", body, "the grandeur frame is a standing monument's")

    def test_every_row_shows_it(self):
        gui = read(TR_GUI)
        for row in ("gm_tr_row_held", "gm_tr_row_abroad", "gm_tr_row_site"):
            # With the trophy's own picture over it (TrophyOwnPictureTests).
            self.assertIn("gm_tr_trophy_picture = {}", squash(raw_block_at(gui, rf"(?m)^\ttype {row} = \w+ \{{")), row)
        self.assertTrue(squash(raw_block_at(gui, r"(?m)^\ttype gm_tr_trophy_picture = widget \{"))
                        .startswith("size = { 96 96 } gm_tr_picture = {}"), "the monument's picture under it")
        self.assertNotIn("modifier_statue_positive", gui)
        # Beside the picture, the row's lines: 96 + 8 + 376 = 480, a monument row's width.
        line = squash(raw_block_at(gui, r"(?m)^\ttype gm_tr_line = textbox \{"))
        self.assertIn("minimumsize = { 376 -1 } maximumsize = { 376 -1 }", line)



class TrophyOwnPictureTests(unittest.TestCase):
    """A trophy's own picture (2026-10-16): what was carried off, on display in a museum room, drawn
    over its monument's picture in a trophy's rows, for the landmarks that have one."""

    def test_codes_follow_the_rows(self):
        for code, key in TROPHY_PICTURES.items():
            lm = LANDMARKS[code - TROPHY_CODE_BASE - 1]
            self.assertEqual(key, f"trophy_{lm.key}", code)
        self.assertEqual(list(TROPHY_PICTURES), sorted(TROPHY_PICTURES))

    def test_the_trophy_takes_its_code(self):
        e = read(PICTURE_EFFECTS)
        body = squash(block(e, "gm_tr_picture_trophies"))
        expected = "set_variable = { name = gm_tr_trophy_picture_code value = 0 }"
        expected += "".join(f" gm_tr_picture_trophy = {{ KEY = {key[len('trophy_'):]} CODE = {code} }}"
                            for code, key in TROPHY_PICTURES.items())
        self.assertEqual(body, expected, "reset first, so a stale code can't stick")
        self.assertEqual(squash(block(e, "gm_tr_picture_trophy")),
                         "if = { limit = { has_variable = gm_tr_landmark var:gm_tr_landmark = flag:$KEY$ } "
                         "set_variable = { name = gm_tr_trophy_picture_code value = $CODE$ } }")

    def test_display_value_defaults_to_none(self):
        self.assertEqual(squash(block(read(TR_VALUES), "gm_tr_disp_trophy_picture_code")),
                         "value = 0 if = { limit = { has_variable = gm_tr_trophy_picture_code } "
                         "value = var:gm_tr_trophy_picture_code }")

    def test_widget_draws_it_over_the_monuments(self):
        body = squash(strip_comments(raw_block_at(read(TR_GUI), r"(?m)^\ttype gm_tr_trophy_picture = widget \{")))
        self.assertTrue(body.startswith("size = { 96 96 } gm_tr_picture = {}"), body[:80])
        for code, key in TROPHY_PICTURES.items():
            self.assertIn(f"icon = {{ visible = \"[EqualTo_CFixedPoint( ScriptContainer.MakeScope.ScriptValue("
                          f"'gm_tr_disp_trophy_picture_code'), '(CFixedPoint){code}' )]\" size = {{ 100% 100% }} "
                          f"texture = \"gfx/interface/icons/gm_pictures/{key}.dds\" }}", body, code)
            self.assertTrue(committed(f"gfx/interface/icons/gm_pictures/{key}.dds"), key)
        self.assertEqual(body.count("icon = {"), len(TROPHY_PICTURES))

    def test_only_a_trophys_rows(self):
        gui = read(TR_GUI)
        row = squash(raw_block_at(gui, r"(?m)^\ttype gm_mon_row_site = \w+ \{"))
        self.assertIn("gm_tr_picture = {}", row)
        self.assertNotIn("gm_tr_trophy_picture", row, "a secondary monument is no trophy")


# The trophies already abroad on 1 January 1836 (loot spec 2026-10-12 §2), in
# seeding order. Owners from the game's 00_states.txt: the origin's part is
# its claimant's, the site's part its holder's. Adding a row is the checklist.
Trophy1836 = namedtuple("Trophy1836", "landmark origin origin_tag site site_tag levels share year")
TROPHIES_1836 = (
    Trophy1836("parthenon", "STATE_ATTICA", "GRE", "STATE_HOME_COUNTIES", "GBR", 5, "piece", 1801),
    Trophy1836("rosetta_stone", "STATE_LOWER_EGYPT", "EGY", "STATE_HOME_COUNTIES", "GBR", 3, "whole", 1801),
    Trophy1836("tipus_tiger", "STATE_MYSORE", "MYS", "STATE_HOME_COUNTIES", "GBR", 2, "whole", 1799),
    # Windsor. Its claimant is British Ceylon, Britain's own colony, until it goes free.
    Trophy1836("royal_palace_of_kandy", "STATE_CEYLON", "BCE", "STATE_HOME_COUNTIES", "GBR", 2, "piece", 1815),
    Trophy1836("temple_of_dendera", "STATE_UPPER_EGYPT", "EGY", "STATE_ILE_DE_FRANCE", "FRA", 2, "piece", 1821),
    Trophy1836("luxor_obelisk", "STATE_UPPER_EGYPT", "EGY", "STATE_ILE_DE_FRANCE", "FRA", 5, "whole", 1831),
    Trophy1836("venus_de_milo", "STATE_WEST_AEGEAN_ISLANDS", "GRE", "STATE_ILE_DE_FRANCE", "FRA", 3, "whole", 1820),
    # Brest's arsenal. Algiers is French in one province, Mascara's in the rest.
    Trophy1836("baba_merzoug", "STATE_ALGIERS", "MAS", "STATE_BRITTANY", "FRA", 2, "whole", 1830),
    # Venice: whoever holds Venetia holds them.
    Trophy1836("piraeus_lion", "STATE_ATTICA", "GRE", "STATE_VENETIA", "AUS", 2, "whole", 1687),
    Trophy1836("horses_of_saint_mark", "STATE_EASTERN_THRACE", "TUR", "STATE_VENETIA", "AUS", 5, "whole", 1204),
)


def trophy_seed_call(tr):
    lm = {lm.key: lm for lm in LANDMARKS}[tr.landmark]
    return (f"gm_seed_trophy = {{ LANDMARK = {tr.landmark} ORIGIN = {tr.origin} ORIGIN_TAG = {tr.origin_tag} "
            f"SITE = {tr.site} SITE_TAG = {tr.site_tag} DEDICATION = {lm.dedication} FORM = {lm.form} "
            f"SHARE = {tr.share} LEVELS = {tr.levels} YEAR = {tr.year} BUILT = {BUILT[tr.landmark]} }}")


class Trophies1836Tests(unittest.TestCase):
    """Loot spec 2026-10-12 §2: the trophies already abroad when the game begins."""

    def test_the_table(self):
        by_key = {lm.key: lm for lm in LANDMARKS}
        seen = [tr.landmark for tr in TROPHIES_1836]
        self.assertEqual(len(seen), len(set(seen)), "one trophy per landmark")
        for tr in TROPHIES_1836:
            lm = by_key[tr.landmark]
            self.assertNotEqual(tr.origin_tag, tr.site_tag, f"{tr.landmark}: a holder that owns the origin brings it "
                                                            "home at the first pass")
            self.assertLess(tr.year, 1836, tr.landmark)
            self.assertGreaterEqual(tr.levels, 1, tr.landmark)
            # The share picks the title: whole for an object, a part's name otherwise.
            self.assertEqual(tr.share == "whole", lm.form in TROPHY_SHARES["object"], tr.landmark)
            self.assertIn(tr.share, ("whole", "piece", "token"), tr.landmark)
            if not lm.placed:
                self.assertEqual((lm.state, lm.tag), (tr.origin, tr.origin_tag),
                                 f"{tr.landmark}: an unplaced landmark stands where its trophy came from")
            else:
                self.assertEqual(lm.state, tr.origin, f"{tr.landmark}: a piece comes from its landmark's state")
            if tr.share != "whole":
                self.assertIn(tr.landmark, LANDMARK_PARTS, f"{tr.landmark}: a part names what was taken")
        # A buried site and a historical opportunity's landmark (signatures spec §6) are unplaced too.
        unplaced = {lm.key for lm in LANDMARKS if not lm.placed and not lm.buried and not lm.year}
        self.assertEqual(unplaced - set(seen), set(), "an unplaced landmark exists only for its trophy")

    def test_a_call_per_row(self):
        body = squash(block(read(TR_EFFECTS), "gm_seed_trophies"))
        self.assertEqual(re.findall(r"gm_seed_trophy = \{[^{}]*\}", body), [trophy_seed_call(tr) for tr in TROPHIES_1836])
        # The lists, then every listed country's refresh, which opens its entry.
        self.assertTrue(body.endswith("gm_trophy_pass = yes every_country = { limit = { has_variable = gm_tr_listed } "
                                      "trigger_event = { id = monument_events.20 } }"), body[-200:])

    def test_the_seed_writes_the_records(self):
        body = squash(block(read(TR_EFFECTS), "gm_seed_trophy"))
        self.assertIn("s:$ORIGIN$.region_state:$ORIGIN_TAG$ ?= { save_scope_as = gm_tr_state }", body)
        self.assertIn("s:$SITE$.region_state:$SITE_TAG$ ?= { save_scope_as = gm_tr_site_state "
                      "owner = { save_scope_as = gm_tr_seed_holder } }", body)
        self.assertIn("scope:gm_tr_state = { NOT = { owner = scope:gm_tr_seed_holder } }", body,
                      "never one whose holder owns its origin")
        self.assertIn("NOT = { AND = { has_global_variable_list = gm_trophies any_in_global_list = { variable = "
                      "gm_trophies has_variable = gm_tr_landmark var:gm_tr_landmark = flag:$LANDMARK$ } } }", body,
                      "never twice")
        self.assertIn("scope:gm_tr_site_state = { create_container = { tags = { gm_trophy }", body)
        self.assertIn("add_to_global_variable_list = { name = gm_trophies target = scope:gm_tr_new }", body)
        for record in ("name = gm_tr_origin value = scope:gm_tr_state",
                       "name = gm_tr_origin_region value = scope:gm_tr_state.state_region",
                       "name = gm_tr_site value = scope:gm_tr_site_state",
                       "name = gm_tr_site_region value = scope:gm_tr_site_state.state_region",
                       "name = gm_tr_levels value = $LEVELS$",
                       # The 1836 rate (owner, 2026-10-19), half of it abroad.
                       "name = gm_tr_grandeur value = { value = $LEVELS$ multiply = gm_level_grandeur_1836 "
                       "divide = 2 ceiling = yes }",
                       "name = gm_tr_year value = $YEAR$", "name = gm_tr_taken_by value = scope:gm_tr_seed_holder",
                       "name = gm_tr_share value = flag:$SHARE$",
                       "name = gm_tr_dedication value = flag:$DEDICATION$",
                       "name = gm_tr_skin value = flag:landmark_$LANDMARK$", "name = gm_tr_form value = flag:$FORM$",
                       "name = gm_tr_landmark value = flag:$LANDMARK$", "name = gm_tr_namesake value = flag:landmark"):
            self.assertIn(f"set_variable = {{ {record} }}", body, record)
        # Split by the years since it was built (owner, 2026-10-19); both
        # parts rejoin its monument when it goes home.
        self.assertIn("gm_set_historical_grandeur = { LEVELS = $LEVELS$ BUILT = $BUILT$ START = gm_tr_start_grandeur "
                      "AGE = gm_tr_age }", body)
        # Taken before the game began: none of a taking's consequences.
        for line in ("change_infamy", "change_relations", "post_notification", "add_war_war_support"):
            self.assertNotIn(line, body, line)
        self.assertIn('else = { debug_log = "TE_MONUMENTS: trophy $LANDMARK$ not placed', body)

    def test_seeded_after_the_landmarks_and_from_the_debug_event(self):
        on = squash(block(read("common/on_actions/monument_events_on_actions.txt"),
                          "gm_landmarks_on_game_started_after_lobby"))
        self.assertIn("gm_seed_landmarks = yes gm_seed_trophies = yes", on)
        ev = squash(raw_block_at(strip_comments(read(DEBUG_EVENTS)), r"(?m)^te_debug_monuments\.5\s*=\s*\{"))
        self.assertIn("name = te_debug_monuments.5.c gm_seed_trophies = yes", ev)
        self.assertIn("te_debug_monuments.5.c", loc())

    def test_a_trophy_row_tells_its_history(self):
        branches = custom_loc_branches("gm_tr_landmark_desc")
        self.assertEqual(branches, [(lm.key, f"gm_landmark_{lm.key}_desc") for lm in LANDMARKS])
        body = squash(block(read(TR_CUSTOM_LOC), "gm_tr_landmark_desc"))
        self.assertTrue(body.endswith("text = { localization_key = gm_landmark_desc_none }"))
        self.assertEqual(squash(block(read(TR_VALUES), "gm_tr_disp_is_landmark")),
                         "value = 0 if = { limit = { has_variable = gm_tr_landmark } value = 1 }")
        gui = read(TR_GUI)
        line = ("gm_tr_line = { visible = \"[EqualTo_CFixedPoint( ScriptContainer.MakeScope.ScriptValue("
                "'gm_tr_disp_is_landmark'), '(CFixedPoint)1' )]\" default_format = \"#tooltippable\" "
                "tooltip = \"gm_tr_row_landmark_tt\" text = \"gm_row_landmark\" }")
        for row in ("gm_tr_row_held", "gm_tr_row_abroad", "gm_tr_row_site"):
            self.assertIn(line, squash(raw_block_at(gui, rf"(?m)^\ttype {row} = \w+ \{{")), row)
        L = loc()
        self.assertEqual(L["gm_tr_row_landmark_tt"],
                         "#b Historical monument#!\\n[ScriptContainer.GetCustom('gm_tr_landmark_desc')]")


MON_EFFECTS = "common/scripted_effects/gm_monument_effects.txt"
MON_TRIGGERS = "common/scripted_triggers/gm_monument_triggers.txt"


def homecoming_kind(tr):
    """How a trophy of 1836 comes home, by the rule of spec 2026-10-13 §4.1:
    "rebuild" where nothing stands, "rejoin" when it is a piece of the landmark
    that stands there, "apart" for anything else (its own monument)."""
    standing = {lm.state: lm for lm in LANDMARKS if lm.placed}.get(tr.origin)
    if standing is None:
        return "rebuild"
    if standing.key == tr.landmark and tr.share != "whole":
        return "rejoin"
    return "apart"


class ReturnToAStateWithAMonumentTests(unittest.TestCase):
    """Task 3: a trophy that is a piece of what stands rejoins it (the Quadriga
    on the Gate); any other, with a monument standing, stays a monument of its
    own (the Luxor Obelisk beside the Obelisks of Karnak): it keeps its name,
    form, landmark and picture, adds its levels to the state's building and
    leaves the primary's dedication alone."""

    def test_the_trophies_of_1836_that_stand_apart(self):
        kinds = {tr.landmark: homecoming_kind(tr) for tr in TROPHIES_1836}
        # Upper Egypt: the Obelisks of Karnak stand; neither returning piece is theirs.
        self.assertEqual(kinds["luxor_obelisk"], "apart")
        self.assertEqual(kinds["temple_of_dendera"], "apart")
        # Attica: the Parthenon stands; its marbles rejoin it, the Piraeus Lion stays itself.
        self.assertEqual(kinds["parthenon"], "rejoin")
        self.assertEqual(kinds["piraeus_lion"], "apart")
        # Eastern Thrace: Topkapi stands.
        self.assertEqual(kinds["horses_of_saint_mark"], "apart")
        # Nothing stands where these came from: rebuilt, as before.
        for key in ("rosetta_stone", "tipus_tiger", "venus_de_milo", "baba_merzoug", "royal_palace_of_kandy"):
            self.assertEqual(kinds[key], "rebuild", key)

    def test_the_levels_a_state_of_1836_comes_to(self):
        # Upper Egypt with both home: Karnak 10 + Luxor 5 + Dendera's piece 2.
        by_key = {lm.key: lm for lm in LANDMARKS}
        total = by_key["obelisks_of_karnak"].level + sum(
            tr.levels for tr in TROPHIES_1836 if tr.origin == "STATE_UPPER_EGYPT")
        self.assertEqual(total, 17)

    def test_a_return_chooses_one_of_three_ways(self):
        home = squash(block(read(TR_EFFECTS), "gm_tr_return_home"))
        self.assertIn("if = { limit = { gm_tr_rejoins_secondary = yes } gm_tr_rejoin_secondary = yes } "
                      "else_if = { limit = { gm_tr_stands_apart = yes } gm_tr_become_monument = yes } "
                      "else = { var:gm_tr_origin = { gm_state_tr_receive = yes } }", home)

    def test_only_a_rejoining_return_destroys_the_container(self):
        home = squash(block(read(TR_EFFECTS), "gm_tr_return_home"))
        # The trophy that becomes a monument is not destroyed: the destroy
        # sits with the other two ways, after the boon and the relations.
        self.assertIn("if = { limit = { NOT = { has_tag = gm_monument } } "
                      "remove_list_global_variable = { name = gm_trophies target = scope:gm_tr_moving } "
                      "destroy_container = yes }", home)
        self.assertLess(home.find("gm_boon_homecoming"), home.find("destroy_container = yes"))
        self.assertLess(home.find("gm_tr_become_monument = yes"), home.find("destroy_container = yes"))

    def test_standing_matches_by_landmark_or_by_neither_having_one(self):
        body = squash(block(read(MON_TRIGGERS), "gm_state_stands_for_moving"))
        self.assertIn("AND = { has_variable = gm_landmark scope:gm_tr_moving = { has_variable = gm_tr_landmark } "
                      "var:gm_landmark = scope:gm_tr_moving.var:gm_tr_landmark }", body)
        self.assertIn("AND = { NOT = { has_variable = gm_landmark } "
                      "scope:gm_tr_moving = { NOT = { has_variable = gm_tr_landmark } } }", body)

    def test_a_piece_rejoins_and_a_whole_one_stands_apart(self):
        body = squash(block(read(MON_TRIGGERS), "gm_tr_rejoins_primary"))
        self.assertIn("has_variable = gm_tr_share NOT = { var:gm_tr_share = flag:whole }", body)
        self.assertIn("gm_state_stands_for_moving = yes", body)
        apart = squash(block(read(MON_TRIGGERS), "gm_tr_stands_apart"))
        # A building raised there today stands too (sites spec 2026-10-18 §3.3).
        self.assertIn("var:gm_tr_origin ?= { OR = { has_building = building_grand_monument "
                      "has_variable = gm_rebuilding } }", apart)
        self.assertIn("NOT = { gm_tr_rejoins_primary = yes }", apart)
        self.assertIn("NOT = { gm_tr_rejoins_secondary = yes }", apart)

    def test_a_piece_of_a_secondary_rejoins_that_secondary(self):
        trig = squash(block(read(MON_TRIGGERS), "gm_tr_rejoins_secondary"))
        self.assertIn("has_variable = gm_tr_share NOT = { var:gm_tr_share = flag:whole }", trig)
        self.assertIn("any_in_list = { variable = gm_monuments_here has_variable = gm_tr_landmark "
                      "var:gm_tr_landmark = scope:gm_tr_moving.var:gm_tr_landmark }", trig)
        eff = squash(block(read(MON_EFFECTS), "gm_tr_rejoin_secondary"))
        self.assertIn("random_in_list = { variable = gm_monuments_here limit = { has_variable = gm_tr_landmark "
                      "var:gm_tr_landmark = scope:gm_tr_moving.var:gm_tr_landmark } save_scope_as = gm_mon_match }", eff)
        self.assertIn("change_variable = { name = gm_tr_levels add = scope:gm_tr_moving.var:gm_tr_levels }", eff)
        # Records only: the building is not rebuilt (sites spec 2026-10-18 §3.3).
        self.assertNotIn("gm_state_tr_add_levels", eff)
        self.assertIn("owner = { trigger_event = { id = monument_events.20 } }", eff)

    def test_a_distinct_monument_keeps_its_identity_and_the_primarys_dedication(self):
        body = squash(block(read(MON_EFFECTS), "gm_tr_become_monument"))
        # Its levels are its records; the building is not rebuilt.
        self.assertNotIn("gm_state_tr_add_levels", body)
        for line in ("remove_list_global_variable = { name = gm_trophies target = scope:gm_tr_moving }",
                     "add_to_global_variable_list = { name = gm_monuments target = scope:gm_tr_moving }",
                     "remove_tag = gm_trophy", "add_tag = gm_monument",
                     "set_variable = { name = gm_tr_site value = var:gm_tr_origin }",
                     "gm_tr_forget_notes = yes",
                     "set_variable = gm_mon_listed trigger_event = { id = monument_events.20 } }"):
            self.assertIn(line, body)
        # Its identity is kept: nothing is cleared or destroyed.
        self.assertNotIn("destroy_container", body)
        for record in ("gm_tr_skin", "gm_tr_form", "gm_tr_landmark", "gm_tr_name", "gm_tr_picture_code",
                       "gm_tr_dedication"):
            self.assertNotIn(f"remove_variable = {record}", body)


MON_VALUES = "common/script_values/gm_monument_values.txt"
MON_SGUIS = "common/scripted_guis/gm_monument_sguis.txt"


class LootingASecondaryTests(unittest.TestCase):
    """Task 4: an occupier carries off one monument of a state, not the state's
    building. A secondary goes whole, or as a piece by its form's share; the
    building shrinks by the levels taken and every other monument stands."""

    def test_the_share_triggers_read_the_secondarys_form_from_the_same_table(self):
        for name, key in (("gm_mon_form_is_object", "object"), ("gm_mon_form_is_piece", "piece")):
            body = squash(block(read(MON_TRIGGERS), name))
            self.assertTrue(body.startswith("has_variable = gm_tr_form OR = {"), name)
            flags = re.findall(r"var:gm_tr_form = flag:(\w+)", body)
            self.assertEqual(flags, list(TROPHY_SHARES[key]), name)

    def test_the_secondarys_share_levels_and_whole(self):
        v = read(MON_VALUES)
        share = squash(block(v, "gm_mon_tr_share"))
        self.assertIn(f"value = {SHARE_VALUES['token']}", share)
        self.assertIn(f"limit = {{ gm_mon_form_is_piece = yes }} value = {SHARE_VALUES['piece']}", share)
        self.assertIn(f"limit = {{ gm_mon_form_is_object = yes }} value = {SHARE_VALUES['object']}", share)
        self.assertLess(share.find("gm_mon_form_is_piece"), share.find("gm_mon_form_is_object"))
        self.assertEqual(squash(block(v, "gm_mon_tr_levels")),
                         "value = gm_mon_levels multiply = gm_mon_tr_share ceiling = yes min = 1 max = gm_mon_levels")
        self.assertEqual(squash(block(v, "gm_mon_tr_whole")),
                         "value = 0 if = { limit = { gm_mon_tr_levels >= gm_mon_levels } value = 1 }")

    def test_a_click_names_the_monument_and_only_orders(self):
        order = squash(block(read(MON_EFFECTS), "gm_mon_tr_order_take"))
        self.assertIn("save_scope_as = gm_mon_pick", order)
        self.assertIn("set_variable = { name = gm_tr_take_target value = scope:gm_mon_pick }", order)
        self.assertIn("gm_state_tr_order_take = { WHO = $WHO$ ROUTE = occupation }", order)
        sgui = strip_comments(read(MON_SGUIS))
        self.assertEqual(squash(block(block(sgui, "gm_mon_take_sgui"), "ai_is_valid")), "always = no")
        effect = squash(block(block(sgui, "gm_mon_take_sgui"), "effect"))
        for doer in ("gm_state_tr_take ", "gm_mon_tr_take", "create_container", "remove_building"):
            self.assertNotIn(doer, effect)
        self.assertIn("gm_mon_tr_order_take = { WHO = root }", effect)
        self.assertIn("saved_scopes = { gm_mon }", squash(block(sgui, "gm_mon_take_sgui")))

    def test_the_gate_for_a_secondary_asks_nothing_of_the_primarys_dedication(self):
        body = squash(block(read(MON_TRIGGERS), "gm_state_tr_takeable_secondary"))
        for line in ("gm_system_enabled = yes", "has_building = building_grand_monument",
                     "NOT = { has_variable = gm_restore_pm }", "NOT = { has_variable = gm_ceremony_pending }",
                     "NOT = { has_variable = gm_gift }", "NOT = { has_variable = gm_carried_off }",
                     "NOT = { has_variable = gm_tr_cooldown }"):
            self.assertIn(line, body)
        self.assertNotIn("gm_state_is_dedicated", body)
        can = squash(block(read(MON_TRIGGERS), "gm_mon_tr_can_take"))
        self.assertIn("var:gm_tr_origin ?= { gm_state_tr_takeable_secondary = yes "
                      "gm_state_tr_occupied_by = { WHO = $WHO$ } }", can)

    def test_the_hidden_event_gates_the_target_by_its_own_rule_and_forgets_it(self):
        ev = squash(raw_block_at(strip_comments(read(TR_EVENTS)), r"(?m)^monument_trophy_events\.10\s*=\s*\{"))
        self.assertIn("OR = { AND = { NOT = { has_variable = gm_tr_take_target } gm_state_tr_takeable = yes } "
                      "AND = { has_variable = gm_tr_take_target gm_state_tr_takeable_secondary = yes } }", ev)
        self.assertIn("gm_remove_state_var = { VAR = gm_tr_take_target }", ev)

    def test_a_taking_branches_on_its_target(self):
        body = squash(block(read(TR_EFFECTS), "gm_state_tr_take"))
        self.assertIn("if = { limit = { has_variable = gm_tr_take_target } gm_mon_tr_take = yes } else = {", body)
        # The consequences follow either way, once a trophy exists.
        after = body.split("gm_mon_tr_take = yes", 1)[1]
        self.assertIn("if = { limit = { exists = scope:gm_tr_new } gm_state_tr_consequences_$ROUTE$ = yes }", after)
        self.assertIn("gm_remove_state_var = { VAR = gm_tr_take_target }", body)

    def test_a_whole_secondary_becomes_the_trophy_and_the_building_shrinks_by_it(self):
        body = squash(block(read(MON_EFFECTS), "gm_mon_tr_take_whole"))
        self.assertIn("save_scope_as = gm_tr_new", body)
        for line in ("remove_list_variable = { name = gm_monuments_here target = scope:gm_tr_new }",
                     "remove_list_global_variable = { name = gm_monuments target = scope:gm_tr_new }",
                     "add_to_global_variable_list = { name = gm_trophies target = scope:gm_tr_new }",
                     "remove_tag = gm_monument", "add_tag = gm_trophy",
                     "set_variable = { name = gm_tr_site value = scope:gm_tr_site_state }",
                     "set_variable = { name = gm_tr_taken_by value = scope:gm_tr_taker }"):
            self.assertIn(line, body)
        self.assertNotIn("shrink", body)
        # A piece it already was stays a piece; only a monument with no share
        # recorded (a co-located landmark) is a whole one.
        self.assertIn("if = { limit = { NOT = { has_variable = gm_tr_share } } "
                      "set_variable = { name = gm_tr_share value = flag:whole } }", body)
        # Its records and the state's other monuments are not touched.
        self.assertNotIn("destroy_container", body)
        self.assertNotIn("gm_clear_state", body)
        self.assertNotIn("remove_building", body)

    def test_a_piece_of_a_secondary_is_a_new_trophy_with_its_records(self):
        body = squash(block(read(MON_EFFECTS), "gm_mon_tr_take_piece"))
        self.assertIn("create_container = { tags = { gm_trophy } save_scope_as = gm_tr_new", body)
        for key in ("gm_tr_skin", "gm_tr_form", "gm_tr_landmark", "gm_tr_namesake", "gm_tr_name_year",
                    "gm_tr_name_char", "gm_tr_name_occasion", "gm_tr_name_enemy_cap", "gm_tr_name",
                    "gm_tr_honoree", "gm_tr_honoree_ig", "gm_tr_dedication"):
            self.assertIn(f"gm_mon_copy_record = {{ KEY = {key} }}", body, key)
        self.assertIn("change_variable = { name = gm_tr_levels subtract = scope:gm_tr_state.var:gm_tr_take_levels }", body)
        self.assertIn("set_variable = { name = gm_tr_cooldown days = 3650 }", body)
        self.assertNotIn("shrink", body)
        self.assertIn("gm_tr_update_picture = yes", body)
        self.assertIn("add_to_global_variable_list = { name = gm_trophies target = scope:gm_tr_new }", body)

    def test_the_ai_picks_one_monument_of_the_state_to_loot(self):
        pick = squash(block(read(MON_EFFECTS), "gm_state_tr_ai_choose_target"))
        self.assertIn("gm_remove_state_var = { VAR = gm_tr_take_target }", pick)
        self.assertIn("limit = { gm_state_has_secondary = yes gm_state_tr_takeable_secondary = yes }", pick)
        # A primary that cannot go leaves the roll to the secondaries (review
        # 2026-10-16, finding 2); otherwise every monument is as likely.
        self.assertIn("if = { limit = { gm_state_tr_takeable = no } "
                      "random_in_list = { variable = gm_monuments_here save_scope_as = gm_mon_pick } } "
                      "else = { random = { chance = gm_state_tr_ai_secondary_chance "
                      "random_in_list = { variable = gm_monuments_here save_scope_as = gm_mon_pick } } } "
                      "if = { limit = { exists = scope:gm_mon_pick } "
                      "set_variable = { name = gm_tr_take_target value = scope:gm_mon_pick } }", pick)
        monthly = squash(block(read(TR_EFFECTS), "gm_state_tr_monthly"))
        self.assertIn("random = { chance = gm_tr_ai_loot_chance gm_state_tr_ai_choose_target = yes "
                      "gm_state_tr_take = { WHO = scope:gm_tr_occupier ROUTE = occupation } }", monthly)
        chance = squash(block(read(MON_VALUES), "gm_state_tr_ai_secondary_chance"))
        self.assertEqual(chance, "value = gm_state_monument_count subtract = 1 multiply = 100 "
                                 "divide = gm_state_monument_count")


class AlsoStandingHereTests(unittest.TestCase):
    """Task 5: the state view. The monument card is the state's whole and its
    primary, as before. Under its details, inside the same card and while a
    secondary monument stands here, a section lists each with its picture,
    name, form, dedication and levels, and a Carry It Off of its own."""

    def setUp(self):
        self.gui = read(TR_GUI)
        self.card = squash(strip_comments(
            raw_block_at(self.gui, r"(?m)^\ttype te_state_gm_beside = flowcontainer \{") or ""))

    def test_the_section_shows_only_while_a_secondary_stands_here(self):
        self.assertIn("visible = \"[NotEqualTo_CFixedPoint(State.MakeScope.ScriptValue('gm_state_mon_disp_here'), "
                      "'(CFixedPoint)0')]\"", self.card)
        v = squash(block(read(MON_VALUES), "gm_state_mon_disp_here"))
        self.assertEqual(v, "value = 0 if = { limit = { gm_state_has_secondary = yes } "
                            "every_in_list = { variable = gm_monuments_here add = 1 } }")

    def test_a_row_for_each_secondary_from_the_states_list(self):
        self.assertIn("datamodel = \"[State.MakeScope.GetList('gm_monuments_here')]\"", self.card)
        self.assertIn("item = { gm_mon_row_site = { datacontext = \"[Scope.GetScriptContainer]\" } }", self.card)
        self.assertIn("text = \"gm_state_mon_header\"", self.card)
        self.assertIn("tooltip = \"gm_state_mon_header_tt\"", self.card)
        self.assertIn("text = \"gm_state_mon_summary\"", self.card)

    def test_a_row_is_the_trophys_with_a_button_of_its_own(self):
        row = squash(strip_comments(raw_block_at(self.gui, r"(?m)^\ttype gm_mon_row_site = flowcontainer \{") or ""))
        for line in ("gm_tr_picture = {}", "text = \"gm_tr_row_title\"", "text = \"gm_mon_row_detail\"",
                     "text = \"gm_mon_row_value\"", "tooltip = \"gm_mon_row_value_tt\"", "gm_mon_take_button = {}"):
            self.assertIn(line, row)
        # A landmark's history on hover, as every trophy's row.
        self.assertIn("ScriptContainer.MakeScope.ScriptValue('gm_tr_disp_is_landmark')", row)
        self.assertIn("tooltip = \"gm_tr_row_landmark_tt\"", row)

    def test_the_button_orders_through_its_scripted_gui(self):
        btn = squash(strip_comments(raw_block_at(self.gui, r"(?m)^\ttype gm_mon_take_button = button \{") or ""))
        self.assertIn("datacontext = \"[GetScriptedGui('gm_mon_take_sgui')]\"", btn)
        for call in ("IsShown", "IsValid", "Execute"):
            self.assertIn(f"ScriptedGui.{call}( GuiScope.SetRoot( GetPlayer.MakeScope ).AddScope( 'gm_mon', "
                          "ScriptContainer.MakeScope ).End )", btn)
        self.assertIn("tooltip = \"gm_mon_take_button_tooltip\"", btn)
        self.assertIn("text = \"gm_button_tr_take\"", btn)

    def test_rows_read_no_journal_entry(self):
        """Gotcha #24: a datamodel row renders its tooltips without JournalEntry."""
        L = loc()
        for row, kind in (("gm_mon_row_site", "flowcontainer"), ("gm_mon_take_button", "button"),
                          ("te_state_gm_beside", "flowcontainer")):
            body = raw_block_at(self.gui, rf"(?m)^\ttype {row} = {kind} \{{")
            self.assertIsNotNone(body, row)
            self.assertNotIn("JournalEntry", body, row)
            for key in re.findall(r'(?:text|tooltip) = "(\w+)"', body):
                self.assertNotIn("JournalEntry", L.get(key, ""), (row, key))

    def test_every_key_the_card_and_the_button_use_exists(self):
        L = loc()
        for key in re.findall(r'(?:text|tooltip) = "(\w+)"', strip_comments(self.gui)):
            self.assertIn(key, L, key)
        for key in re.findall(r"text = (gm_mon_\w+)", read(MON_SGUIS) + read(MON_TRIGGERS)):
            self.assertIn(key, L, key)

    def test_one_card_holds_the_primary_and_the_rest(self):
        panel = squash(strip_comments(read(STATES_PANEL)))
        self.assertIn("te_state_gm_card = {} te_state_gm_site_card = {} te_state_gm_trophy_card = {}", panel)
        self.assertNotIn("te_state_gm_monument_card", panel)
        self.assertNotIn("te_state_gm_monument_card", strip_comments(self.gui))
        card = squash(strip_comments(raw_block_at(read(STATE_WIDGETS), r"(?m)^\ttype te_state_gm_card = flowcontainer \{")))
        # Inside the card's background, after the picture and details row,
        # before the corner's goto.
        self.assertEqual(card.count("te_state_gm_beside = {}"), 1)
        self.assertLess(card.find("gm_tr_take_button = {}"), card.find("te_state_gm_beside = {}"))
        self.assertLess(card.find("te_state_gm_beside = {}"), card.find("button_icon_goto"))

    def test_the_monument_card_names_the_building_as_the_whole(self):
        # The grandeur row's hover says, with a secondary here, that the level
        # is every monument's together and which part is the first's.
        self.assertEqual(
            loc().get("gm_state_grandeur_tt"),
            "[SelectLocalization( EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_state_mon_disp_here'), "
            "'(CFixedPoint)0' ), 'gm_state_grandeur_tt_one', 'gm_state_grandeur_tt_many' )]")
        many = loc().get("gm_state_grandeur_tt_many", "")
        self.assertIn("ScriptValue('gm_state_primary_grandeur')", many)
        self.assertIn("ScriptValue('gm_state_secondary_grandeur')", many)

    def test_a_secondarys_picture_catches_up_each_month(self):
        monthly = squash(block(read(MON_EFFECTS), "gm_monument_monthly"))
        self.assertIn("every_in_global_list = { variable = gm_monuments gm_tr_repair_places = yes "
                      "gm_tr_update_picture = yes ", monthly)


class OurMonumentsListTests(unittest.TestCase):
    """Task 6: Our Monuments (the journal entry and the Timeline Extended
    window's tab) lists every monument we own, a row per state's primary as
    before and a row per secondary after them, each with its own picture,
    name, form, dedication and levels."""

    def test_the_pass_lists_each_secondary_under_its_states_owner(self):
        pass_ = squash(block(read(MON_EFFECTS), "gm_monument_pass"))
        self.assertIn("every_country = { limit = { has_variable = gm_mon_listed } "
                      "clear_variable_list = gm_monuments_held remove_variable = gm_mon_listed }", pass_)
        self.assertLess(pass_.find("clear_variable_list = gm_monuments_held"), pass_.find("gm_mon_list_one = yes"))
        one = squash(block(read(MON_EFFECTS), "gm_mon_list_one"))
        self.assertIn("owner = { add_to_variable_list = { name = gm_monuments_held target = scope:gm_mon_listing } "
                      "set_variable = gm_mon_listed }", one)

    def test_a_return_a_taking_and_a_promotion_keep_the_owners_list(self):
        become = squash(block(read(MON_EFFECTS), "gm_tr_become_monument"))
        self.assertIn("owner = { add_to_variable_list = { name = gm_monuments_held target = scope:gm_tr_moving } "
                      "set_variable = gm_mon_listed", become)
        whole = squash(block(read(MON_EFFECTS), "gm_mon_tr_take_whole"))
        self.assertIn("owner = { remove_list_variable = { name = gm_monuments_held target = scope:gm_tr_new } }", whole)
        promote = squash(block(read(MON_EFFECTS), "gm_state_promote_secondary"))
        self.assertIn("owner = { remove_list_variable = { name = gm_monuments_held target = scope:gm_mon_promoted } }",
                      promote)

    def test_the_section_lists_primaries_then_secondaries(self):
        sec = squash(strip_comments(raw_block_at(read(WIDGET), r"(?m)^\ttype te_gm_sec_monuments = flowcontainer \{")))
        first = sec.find("GetList('gm_states')")
        second = sec.find("GetList('gm_monuments_held')")
        self.assertNotEqual(first, -1)
        self.assertGreater(second, first)
        self.assertIn("gm_mon_row_site = { datacontext = \"[Scope.GetScriptContainer]\" "
                      "blockoverride \"mon_where\" { gm_tr_line = { text = \"gm_mon_row_where\" } } "
                      "blockoverride \"mon_choices\" {", sec)

    def test_the_row_says_where_it_stands_only_where_asked(self):
        gui = strip_comments(read(TR_GUI))
        row = squash(raw_block_at(gui, r"(?m)^\ttype gm_mon_row_site = flowcontainer \{"))
        self.assertIn("block \"mon_where\" {}", row)
        self.assertNotIn("gm_mon_row_where", row)
        self.assertIn("gm_mon_row_where", loc())
        self.assertNotIn("JournalEntry", loc()["gm_mon_row_where"])


class DebugTests(unittest.TestCase):
    def test_the_debug_event(self):
        ev = squash(raw_block_at(strip_comments(read(DEBUG_EVENTS)), r"(?m)^te_debug_monuments\.6\s*=\s*\{"))
        for call in ("gm_state_tr_take = { WHO = root ROUTE = occupation }", "gm_state_tr_take = { WHO = root ROUTE = own }",
                     "gm_tr_return_home = { RELATIONS = yes }", "gm_trophy_monthly = yes", "gm_tr_debug_log = yes"):
            self.assertIn(call, ev)
        self.assertIn("gm_tr_debug_log = yes", squash(block(read(EFFECTS), "gm_debug_log")))


if __name__ == "__main__":
    unittest.main()
