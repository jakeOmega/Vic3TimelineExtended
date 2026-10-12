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
    BUILDING_FORMS, DEDICATIONS, FORMS, LANDMARKS, NAMESAKES, RETIRED_FORMS, block, loc, raw_block_at, read,
    squash, strip_comments,
)

TR_EFFECTS = "common/scripted_effects/gm_trophy_effects.txt"
TR_TRIGGERS = "common/scripted_triggers/gm_trophy_triggers.txt"
TR_VALUES = "common/script_values/gm_trophy_values.txt"
TR_SGUIS = "common/scripted_guis/gm_trophy_sguis.txt"
TR_ON_ACTIONS = "common/on_actions/gm_trophy_on_actions.txt"
TR_CUSTOM_LOC = "common/customizable_localization/gm_trophy_custom_loc.txt"
TR_EVENTS = "events/monument_trophy_events.txt"
TR_GUI = "gui/gm_trophy_widgets.gui"
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
                         "value = gm_state_grandeur multiply = gm_state_tr_share ceiling = yes min = 1 "
                         "max = gm_state_grandeur")
        self.assertEqual(squash(block(v, "gm_state_tr_value")),
                         "value = gm_state_tr_levels divide = 2 ceiling = yes")

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
        self.assertIn("any_province = { percent >= 0.5 controller = $WHO$ }", body)
        self.assertIn("NOT = { AND = { owner = { has_variable = te_cw_role } $WHO$ = { has_variable = te_cw_role } } }",
                      body, "never between the two sides of a civil war")

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
                                  ("gm_honoree", "gm_tr_honoree"), ("gm_honoree_ig", "gm_tr_honoree_ig")):
            self.assertIn(f"gm_tr_copy_from_state = {{ FROM = {state_var} TO = {tr_var} }}", make, state_var)
            receive = squash(block(read(TR_EFFECTS), "gm_state_tr_receive"))
            self.assertIn(f"gm_tr_copy_to_state = {{ FROM = {tr_var} TO = {state_var} }}", receive, tr_var)
        record = squash(block(read(TR_EFFECTS), "gm_tr_record_dedication"))
        for d in DEDICATIONS:
            self.assertIn(f"gm_tr_record_dedication_one = {{ KEY = {d.key} }}", record, d.key)

    def test_a_trophy_comes_home_whole_and_never_as_a_copy(self):
        receive = squash(block(read(TR_EFFECTS), "gm_state_tr_receive"))
        self.assertIn("add = scope:gm_tr_moving.var:gm_tr_levels max = 200", receive)
        self.assertIn("gm_tr_copy_to_state = { FROM = gm_tr_dedication TO = gm_restore_pm }", receive)
        for line in ("set_variable = gm_seen", "set_variable = { name = gm_ceremony_level value = var:gm_rebuild_level }",
                     "set_variable = { name = gm_built_by value = owner }",
                     "set_variable = { name = gm_rebuilding days = 1 }"):
            self.assertIn(line, receive)


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
                         "value = var:gm_tr_tmp_levels divide = 5 add = 2 max = 8 if = { limit = { "
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
        self.assertEqual({f for f, _ in custom_loc_branches("gm_tr_dedication_name")}, {d.key for d in DEDICATIONS})
        for d, key in custom_loc_branches("gm_tr_dedication_name"):
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
        self.assertIn("te_state_gm_card = {} te_state_gm_trophy_card = {}", squash(strip_comments(read(STATES_PANEL))))

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
            f"SHARE = {tr.share} LEVELS = {tr.levels} YEAR = {tr.year} }}")


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
        unplaced = {lm.key for lm in LANDMARKS if not lm.placed}
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
                       "name = gm_tr_grandeur value = { value = $LEVELS$ divide = 2 ceiling = yes }",
                       "name = gm_tr_year value = $YEAR$", "name = gm_tr_taken_by value = scope:gm_tr_seed_holder",
                       "name = gm_tr_share value = flag:$SHARE$",
                       "name = gm_tr_dedication value = flag:$DEDICATION$",
                       "name = gm_tr_skin value = flag:landmark_$LANDMARK$", "name = gm_tr_form value = flag:$FORM$",
                       "name = gm_tr_landmark value = flag:$LANDMARK$", "name = gm_tr_namesake value = flag:landmark"):
            self.assertIn(f"set_variable = {{ {record} }}", body, record)
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


class DebugTests(unittest.TestCase):
    def test_the_debug_event(self):
        ev = squash(raw_block_at(strip_comments(read(DEBUG_EVENTS)), r"(?m)^te_debug_monuments\.6\s*=\s*\{"))
        for call in ("gm_state_tr_take = { WHO = root ROUTE = occupation }", "gm_state_tr_take = { WHO = root ROUTE = own }",
                     "gm_tr_return_home = { RELATIONS = yes }", "gm_trophy_monthly = yes", "gm_tr_debug_log = yes"):
            self.assertIn(call, ev)
        self.assertIn("gm_tr_debug_log = yes", squash(block(read(EFFECTS), "gm_debug_log")))


if __name__ == "__main__":
    unittest.main()
