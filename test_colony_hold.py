# -*- coding: utf-8 -*-
"""A colony held by force (owner, 2026-11-25).

Under Full Colonies a colony at the break level declares itself free only when
our marines there can't hold it: a battalion holds 100,000 of its people, and
on the Moon and Mars our marines at every colony of ours there hold all of
ours there at the break level together. Each month held costs the garrison
0.5 battalions for each point a month the colony's terms run past the break
level's settling; once the marines fall short, every colony held there
declares together. At home the interest groups that oppose colonial
exploitation lose approval and gain radicals. These tests hold the generated
step, the hand-written helpers, the AI, the panel, the events and the loc to
that shape, and run the arithmetic of the losses, the months and the approval.
"""

import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import gen_solar_sites as gss  # noqa: E402


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        raise AssertionError(f"no block {name}")
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return text[m.end():i - 1]


def _flat(text):
    return " ".join(text.split())


def _number(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{ value = ([\d.]+) \}}", text)
    if not m:
        raise AssertionError(f"no value {name}")
    return float(m.group(1))


def _loc(key):
    for name in sorted(os.listdir(os.path.join(REPO, "localization", "english"))):
        if name.endswith(".yml") and name != "te_unused_l_english.yml":
            m = re.search(rf'(?m)^ {re.escape(key)}:\d+ "(.*)"$', _raw("localization", "english", name))
            if m:
                return m.group(1)
    raise AssertionError(f"no live loc {key}")


EFFECTS = _strip(_raw("common", "scripted_effects", "sr_sites_generated.txt"))
VALUES = _strip(_raw("common", "script_values", "sr_sites_generated.txt"))
TRIGGERS = _strip(_raw("common", "scripted_triggers", "sr_sites_generated.txt"))
DISPLAY = _strip(_raw("common", "script_values", "sr_sites_display_generated.txt"))
FLEET_VALUES = _strip(_raw("common", "script_values", "sr_fleet_values.txt"))
AUT_VALUES = _strip(_raw("common", "script_values", "sr_colony_autonomy_values.txt"))
AUT_EFFECTS = _strip(_raw("common", "scripted_effects", "sr_colony_autonomy_effects.txt"))
SHARED = {"moon": 1, "mars": 2}


class NumbersTest(unittest.TestCase):
    def test_the_owners_figures(self):
        self.assertEqual(_number(FLEET_VALUES, "sr_hold_people_per_battalion"), 100000)
        self.assertEqual(_number(FLEET_VALUES, "sr_hold_loss_per_excess"), 0.5)
        self.assertEqual(_number(FLEET_VALUES, "sr_hold_ai_reinforce_months"), 12)
        self.assertEqual(_number(AUT_VALUES, "sr_hold_approval_first"), 2)
        self.assertEqual(_number(AUT_VALUES, "sr_hold_approval_more"), 1)
        self.assertEqual(_number(AUT_VALUES, "sr_hold_approval_max"), 5)
        self.assertEqual(_number(AUT_VALUES, "sr_hold_approval_strong_factor"), 2)
        self.assertIn("sr_hold_radicals_per_battalion = { value = small_radicals }", AUT_VALUES)

    def test_the_battalion_holds_five_times_the_militia(self):
        # The tooltip's reason: a battalion holds 100,000, the militia fields one a 20,000.
        militia = float(re.search(r"(?m)^sr_militia_people = \{ value = (\d+) \}", FLEET_VALUES).group(1))
        self.assertEqual(_number(FLEET_VALUES, "sr_hold_people_per_battalion") / militia, 5)

    def test_the_losses_match_the_owners_examples(self):
        # A colony that would settle at 120 has terms of 1.2 a month; settling takes
        # 1 a month at 100, so 0.2 past it: 0.1 battalions a month, one in ten months.
        rate = _number(FLEET_VALUES, "sr_hold_loss_per_excess")
        for settles_at, months in ((120, 10), (150, 4)):
            with self.subTest(settles_at=settles_at):
                loss = (settles_at / 100 - 1) * rate
                self.assertAlmostEqual(1 / loss, months, delta=0.5)

    def test_the_approval_ladder(self):
        # -2 for the first colony held, -1 for each after, at most -5; twice that strongly;
        # times the Free Speech law's scale.
        speech = _flat(_block(AUT_VALUES, "sr_hold_speech_scale"))
        scale = dict(re.findall(r"has_law_or_variant = law_type:(\w+) \} value = ([\d.]+)", speech))
        self.assertEqual(scale, {"law_protected_speech": "1.5", "law_censorship": "0.75",
                                 "law_outlawed_dissent": "0.5"})
        self.assertTrue(speech.startswith("value = 1 "))  # Right of Assembly
        self.assertEqual(_flat(_block(AUT_VALUES, "sr_hold_approval")), (
            "value = sr_hold_count subtract = 1 multiply = sr_hold_approval_more add = sr_hold_approval_first "
            "max = sr_hold_approval_max multiply = sr_hold_speech_scale"))
        self.assertEqual(_flat(_block(AUT_VALUES, "sr_hold_approval_strong")),
                         "value = sr_hold_approval multiply = sr_hold_approval_strong_factor")
        for count, want in ((1, 2), (2, 3), (3, 4), (4, 5), (9, 5)):
            self.assertEqual(min((count - 1) * 1 + 2, 5), want)


class StepTest(unittest.TestCase):
    def test_the_step_holds_or_declares_at_the_break_level(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                step = _flat(_block(EFFECTS, f"sr_site_aut_step_{k}"))
                self.assertIn(f"if = {{ limit = {{ local_var:sr_aut_peak >= sr_aut_break_level sr_site_peopled_{k} = yes }} "
                              f"if = {{ limit = {{ sr_site_may_hold_{k} = yes }} sr_site_hold_{k} = yes }} "
                              f"else = {{ sr_site_declare_{k} = yes }} }}", step)
                self.assertNotIn("sr_aut_break_away", step)
                # The hold ends once the drift takes it under the break level.
                self.assertTrue(step.endswith(
                    f"if = {{ limit = {{ has_global_variable = sr_site_resisting_{k} "
                    f"sr_site_autonomy_value_{k} < sr_aut_break_level }} remove_global_variable = sr_site_resisting_{k} }}"))

    def test_only_full_colonies_unoccupied_with_marines_may_hold(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertEqual(_flat(_block(TRIGGERS, f"sr_site_may_hold_{k}")), (
                    f"sr_colonies_full_enabled = yes NOT = {{ has_global_variable = sr_site_occupier_{k} }} "
                    f"sr_site_hold_marines_{k} > 0"))

    def test_the_hold_takes_its_losses_then_tests(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                hold = _flat(_block(EFFECTS, f"sr_site_hold_{k}"))
                self.assertTrue(hold.startswith(
                    f"set_global_variable = {{ name = sr_site_autonomy_{k} value = sr_aut_break_level }}"))
                own = hold.index(f"sr_hold_take_marines = {{ KEY = {k} }}")
                mates = [hold.index(f"sr_hold_take_marines = {{ KEY = {t.key} }}") for t in gss.world_mates(site)]
                self.assertTrue(all(own < m for m in mates), "its own marines first")
                radicals = hold.index("sr_hold_radicals = yes")
                test = hold.index(f"limit = {{ sr_site_hold_marines_{k} < sr_site_hold_need_{k} }} sr_site_declare_{k} = yes")
                self.assertLess(max([own, *mates]), radicals)
                self.assertLess(radicals, test)
                # A player hears a hold begin, once, a day later.
                self.assertIn(f"sr_site_event_open = {{ VAR = sr_rising_site INDEX = {site.index} }} "
                              "trigger_event = { id = space_race_events.114 days = 1 }", hold)
                self.assertIn("local_var:sr_hold_new = 1 is_player = yes", hold)

    def test_a_shared_world_declares_together(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                declare = _flat(_block(EFFECTS, f"sr_site_declare_{k}"))
                for t in gss.world_mates(site):
                    self.assertIn(f"if = {{ limit = {{ sr_site_shares = {{ A = {k} B = {t.key} }} "
                                  f"has_global_variable = sr_site_resisting_{t.key} }} "
                                  f"sr_aut_break_away = {{ KEY = {t.key} INDEX = {t.index} }} }}", declare)
                world = SHARED.get(gss.world_of(site), 0)
                self.assertTrue(declare.endswith(f"sr_aut_break_away = {{ KEY = {k} INDEX = {site.index} }} "
                                                 f"sr_freed_note = {{ WORLD = {world} }}"))
                # The marines lost are counted before any break-away frees them.
                self.assertLess(declare.rindex("sr_freed_marines_now"), declare.index("sr_aut_break_away"))

    def test_the_flag_goes_with_freedom_a_release_and_a_transfer(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertIn(f"sr_site_resisting_{k}", gss.slice5_vars(site))
                for helper in (f"sr_site_set_free_{k}", f"sr_site_transfer_{k}"):
                    self.assertIn(f"remove_global_variable = sr_site_resisting_{k}", _block(EFFECTS, helper))


class ValuesTest(unittest.TestCase):
    def test_need_marines_loss_and_months(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                people = _flat(_block(VALUES, f"sr_site_hold_people_{k}"))
                self.assertTrue(people.startswith(f"value = sr_site_pop_value_{k}"))
                for t in gss.world_mates(site):
                    self.assertIn(f"if = {{ limit = {{ sr_site_shares = {{ A = {k} B = {t.key} }} "
                                  f"has_global_variable = sr_site_resisting_{t.key} }} add = sr_site_pop_value_{t.key} }}",
                                  people)
                self.assertEqual(people.count("add ="), len(gss.world_mates(site)))
                self.assertIn(f"sr_site_hold_need_{k} = {{ value = sr_site_hold_people_{k} "
                              "divide = sr_hold_people_per_battalion }", VALUES)
                self.assertIn(f"sr_site_hold_marines_{k} = {{ value = sr_site_shared_marines_{k} "
                              f"multiply = sr_site_marines_share_{k} }}", VALUES)
                self.assertEqual(_flat(_block(VALUES, f"sr_site_hold_loss_{k}")), (
                    f"value = sr_site_aut_pressure_{k} subtract = {{ value = sr_aut_break_level "
                    "multiply = sr_aut_settle_rate } min = 0 multiply = sr_hold_loss_per_excess"))
                months = _flat(_block(VALUES, f"sr_site_hold_months_{k}"))
                self.assertIn(f"value = sr_site_hold_marines_{k} subtract = sr_site_hold_need_{k} "
                              f"divide = {{ value = sr_site_hold_world_loss_{k} multiply = sr_site_marines_share_{k} "
                              "min = 0.001 }", months)

    def test_a_held_colony_fields_no_militia_for_its_holder(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                need = _flat(_block(VALUES, f"sr_site_garrison_need_{k}"))
                self.assertIn(f"NOT = {{ has_global_variable = sr_site_resisting_{k} }} }} "
                              f"add = sr_site_militia_value_{k}", need)

    def test_the_count_reads_full_colonies(self):
        count = _flat(_block(VALUES, "sr_hold_count"))
        self.assertTrue(count.startswith("value = 0 if = { limit = { sr_colonies_full_enabled = yes }"))
        self.assertEqual(count.count("has_global_variable = sr_site_resisting_"), len(gss.SITES))

    def test_months_arithmetic(self):
        # Two battalions holding 50,000 people (need 0.5) at 0.1 lost a month: 15 months.
        marines, need, loss, share = 2.0, 50000 / 100000, 0.1, 1.0
        self.assertEqual(int((marines * share - need) / (loss * share)), 15)


class HomeTest(unittest.TestCase):
    def test_the_interest_groups_are_read_from_their_stance(self):
        triggers = _strip(_raw("common", "scripted_triggers", "sr_fleet_triggers.txt"))
        self.assertEqual(_flat(_block(triggers, "sr_ig_anticolonial")),
                         "law_stance = { law = law_type:law_colonial_exploitation value < neutral }")
        self.assertEqual(_flat(_block(triggers, "sr_ig_strongly_anticolonial")),
                         "law_stance = { law = law_type:law_colonial_exploitation value < disapprove }")

    def test_one_refresh_site_off_then_on(self):
        refresh = _flat(_block(AUT_EFFECTS, "sr_hold_ig_refresh"))
        off = refresh.index("remove_modifier = sr_hold_by_force_ig")
        on = refresh.index("add_modifier = { name = sr_hold_by_force_ig")
        self.assertLess(off, on)
        self.assertIn("multiplier = local_var:sr_hold_appr_strong", refresh)
        self.assertIn("multiplier = local_var:sr_hold_appr }", refresh)
        pulse = _flat(_strip(_raw("common", "on_actions", "space_race_on_actions.txt")))
        self.assertIn("if = { limit = { OR = { sr_hold_count >= 1 has_variable = sr_hold_ig_on } } "
                      "sr_hold_ig_refresh = yes }", pulse)
        adders = [p for p in ("common", "events") for root, _, files in os.walk(os.path.join(REPO, p))
                  for f in files if f.endswith(".txt")
                  and "name = sr_hold_by_force_ig" in _strip(_raw(os.path.relpath(os.path.join(root, f), REPO)))]
        self.assertEqual(len(adders), 1)

    def test_the_modifier_is_one_point_of_approval(self):
        modifiers = _strip(_raw("common", "static_modifiers", "space_race_modifiers.txt"))
        fields = re.findall(r"(?m)^\s*(\w+) = (\S+)", _block(modifiers, "sr_hold_by_force_ig"))
        self.assertEqual([f for f in fields if f[0] != "icon"], [("interest_group_approval_add", "-1")])
        import gen_nation_tab
        self.assertEqual(gen_nation_tab.NOT_ON_COUNTRY.get("sr_hold_by_force_ig"), "interest groups")

    def test_radicals_scale_with_the_battalions_lost_and_the_speech_law(self):
        radicals = _flat(_block(AUT_EFFECTS, "sr_hold_radicals"))
        self.assertIn("value = local_var:sr_hold_lost multiply = sr_hold_radicals_per_battalion "
                      "multiply = sr_hold_speech_scale", radicals)
        self.assertIn("every_interest_group = { limit = { sr_ig_anticolonial = yes } save_temporary_scope_as = sr_hold_ig "
                      "owner = { add_radicals = { value = local_var:sr_hold_rad interest_group = scope:sr_hold_ig } } }",
                      radicals)


class AiTest(unittest.TestCase):
    def test_a_hold_running_short_is_a_garrison_due_and_lands_first(self):
        fleets = _strip(_raw("common", "scripted_triggers", "sr_fleets_generated.txt"))
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"has_global_variable = sr_site_resisting_{site.key} "
                              f"sr_site_hold_months_{site.key} < sr_hold_ai_reinforce_months", fleets)
        effects = _flat(_strip(_raw("common", "scripted_effects", "sr_fleets_generated.txt")))
        land = _flat(_block(effects.replace(" sr_fl_land_at = {", "\nsr_fl_land_at = {"), "sr_fl_land_at"))
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertLess(land.index(f"has_global_variable = sr_site_resisting_{k}"),
                                land.index(f"has_global_variable = sr_site_garrison_due_{k}"))


class EventsAndPanelTest(unittest.TestCase):
    def test_the_rising_event(self):
        events = _strip(_raw("events", "space_race_events.txt"))
        body = _flat(_block(events, "space_race_events.114"))
        self.assertIn("trigger = { has_variable = sr_rising_site }", body)
        self.assertIn("event_image = { texture = \"gfx/event_pictures/colony_hellas_planitia.dds\" }", body)
        self.assertIn("default_option = yes custom_tooltip = sr_hold_tt", body)
        self.assertIn("custom_tooltip = { text = sr_hold_let_go_tt sr_site_idx_from = { VAR = sr_rising_site } "
                      "sr_site_by_index = { DO = let_go } }", body)
        for key in ("t", "d", "f", "a", "b"):
            self.assertTrue(_loc(f"space_race_events.114.{key}"))
        self.assertIn("sr_rising_site_name", _loc("space_race_events.114.t"))

    def test_none_leaves_unheard(self):
        breakaway = _flat(_block(AUT_EFFECTS, "sr_aut_break_away"))
        self.assertIn("else = { change_variable = { name = sr_freed_count add = 1 } }", breakaway)
        events = _strip(_raw("events", "space_race_events.txt"))
        body = _flat(_block(events, "space_race_events.98"))
        for key in ("t_moon", "t_mars", "t_more", "d_moon", "d_mars", "d_more", "d_overrun", "f_together"):
            with self.subTest(key=key):
                self.assertIn(f"desc = space_race_events.98.{key}", body)
                self.assertTrue(_loc(f"space_race_events.98.{key}"))
        self.assertIn("if = { limit = { has_variable = sr_freed_marines } custom_tooltip = sr_freed_marines_tt }", body)
        for var in ("sr_freed_count", "sr_freed_marines", "sr_freed_world"):
            self.assertIn(f"if = {{ limit = {{ has_variable = {var} }} remove_variable = {var} }}", body)

    def test_letting_go_brings_the_marines_home(self):
        let_go = _flat(_block(AUT_EFFECTS, "sr_site_let_go_at"))
        self.assertLess(let_go.index("sr_fl_marines_home = { AMOUNT = sr_site_marines_value_$KEY$ }"),
                        let_go.index("sr_site_set_free_$KEY$ = yes"))

    def test_the_status_cell_and_page(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertIn(f"sr_disp_site_held_{k} = {{ value = 0 if = {{ limit = {{ global_var:sr_site_holder_{k} ?= this "
                              f"has_global_variable = sr_site_resisting_{k} }} value = 1 }} }}", DISPLAY)
                tooltip = _loc(f"je_space_race_widget_autonomy_held_tt_{k}")
                for figure in ("marines", "need", "loss"):
                    self.assertIn(f"ScriptValue('sr_disp_hold_{figure}_{k}')", tooltip)
                self.assertIn(f"'je_space_race_widget_autonomy_held_months_{k}'", tooltip)
                self.assertIn("#v 100,000#!", tooltip)
                shared = gss.world_of(site) in SHARED
                self.assertEqual("hold every one of ours there at #v 100#! together" in tooltip, shared)
                self.assertIn(f"ScriptValue('sr_disp_hold_months_{k}')",
                              _loc(f"je_space_race_widget_autonomy_held_months_{k}"))
        rows = _raw("gui", "journal_entry_widgets", "sr_sites_generated_rows.gui")
        self.assertEqual(rows.count('blockoverride "aut_held_visible"'), len(gss.SITES))
        self.assertEqual(rows.count('blockoverride "aut_held_months_visible"'), len(gss.SITES))

    def test_the_concept_gives_the_rule(self):
        concept = _loc("concept_sr_colony_autonomy_desc")
        for part in ("Under Full Colonies our marines there can hold it", "#v 100,000#!", "#v 0.5#! battalions",
                     "oppose colonial exploitation"):
            self.assertIn(part, concept)


if __name__ == "__main__":
    unittest.main()
