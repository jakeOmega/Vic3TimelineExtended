"""Resource Transition laws and fossil retirement (issue #660).

Static checks on the script: the law group's default comes first, the
construction ban covers all three buildings and every construction path, the
player's controls and the AI's buttons call the same helpers, the panel's
numbers match the tuning constants, the laws are enforced outside the journal
entry, and nothing hands out an emissions bonus.

Run: python3 test_resource_transition.py
"""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
LAWS = os.path.join(REPO, "common", "laws", "resource_transition_laws.txt")
LAW_GROUPS = os.path.join(REPO, "common", "law_groups", "extra_law_groups.txt")
BUILDINGS = os.path.join(REPO, "common", "buildings", "extra_buildings.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "resource_transition_triggers.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "resource_transition_effects.txt")
VALUES = os.path.join(REPO, "common", "script_values", "resource_transition_values.txt")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "resource_transition_sguis.txt")
BUTTONS = os.path.join(REPO, "common", "scripted_buttons", "resource_transition_buttons.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "resource_transition_on_actions.txt")
MODIFIERS = os.path.join(REPO, "common", "static_modifiers", "resource_transition_modifiers.txt")
JE = os.path.join(REPO, "common", "journal_entries", "je_global_warming.txt")
IDEOLOGY_GEN = os.path.join(REPO, "ideology_modifications.py")
LAW_CONSISTENCY = os.path.join(REPO, "gen_law_consistency.py")
LOC_DIR = os.path.join(REPO, "localization", "english")

INDUSTRIES = {"coal": "building_coal_mine", "oil": "building_oil_rig", "power": "building_power_plant"}
LAW_ORDER = ["law_unrestricted_extraction", "law_fossil_expansion_moratorium", "law_managed_fossil_phaseout"]
MAX_LAW_DESC_CHARS = 300


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _block_from(text, start):
    depth = 0
    for j in range(start - 1, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start:j]
    raise AssertionError("unbalanced braces")


def _top_level(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert m, f"no {name}"
    return _block_from(text, m.end())


def _sub(block, key):
    m = re.search(rf"(?m)^\s*{re.escape(key)} = \{{", block)
    assert m, f"no {key}"
    return _block_from(block, m.end())


def _code(text):
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _loc_value(key):
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        m = re.search(rf'^ {re.escape(key)}:\d* "(.*)"\s*$', _read(path), re.M)
        if m:
            return m.group(1)
    raise AssertionError(f"no loc {key}")


def _constant(name):
    m = re.search(rf"(?m)^{name} = ([\d.]+)", _read(VALUES))
    assert m, name
    return float(m.group(1))


class LawTest(unittest.TestCase):
    def test_group_is_economy(self):
        group = _top_level(_read(LAW_GROUPS), "lawgroup_resource_transition")
        self.assertIn("law_group_category = economy", group)

    def test_default_law_comes_first(self):
        """The engine gives an unseeded country, and an old save, the group's
        first law in file order (scripting_best_practices.md)."""
        found = re.findall(r"(?m)^(law_\w+) = \{", _read(LAWS))
        self.assertEqual(found, LAW_ORDER)
        for law in found:
            self.assertIn("group = lawgroup_resource_transition", _top_level(_read(LAWS), law))
        # No other law file joins the group.
        others = [p for p in glob.glob(os.path.join(REPO, "common", "laws", "*.txt")) if p != LAWS]
        for p in others:
            self.assertNotIn("lawgroup_resource_transition", _read(p), p)

    def test_one_technology_per_law_and_the_ministry(self):
        laws = _read(LAWS)
        self.assertNotIn("unlocking_technologies", _top_level(laws, "law_unrestricted_extraction"))
        for law, tech in (("law_fossil_expansion_moratorium", "environmental_movement"),
                          ("law_managed_fossil_phaseout", "carbon_capture_and_storage")):
            body = _top_level(laws, law)
            self.assertEqual(_sub(body, "unlocking_technologies").split(), [tech], law)
            self.assertEqual(_sub(body, "unlocking_laws").split(), ["law_ministry_of_the_environment"], law)
        self.assertIn("rt_ministry_funded_for_phaseout = yes",
                      _sub(_top_level(laws, "law_managed_fossil_phaseout"), "can_enact"))
        funded = _top_level(_read(TRIGGERS), "rt_ministry_funded_for_phaseout")
        self.assertIn("institution = institution_ministry_of_the_environment", funded)
        self.assertRegex(funded, r"value >= 3\b")

    def test_no_law_carries_an_emissions_modifier(self):
        """The issue: no arbitrary emissions bonus. The laws work through supply."""
        for path in (LAWS, EFFECTS, MODIFIERS, VALUES, TRIGGERS):
            # A custom_tooltip names a loc key, not an effect (rt_law_emissions_tt).
            code = re.sub(r"custom_tooltip = \w+", "", _code(_read(path)))
            self.assertNotIn("greenhouse_gas", code, path)
            self.assertNotIn("emission", code, path)
            self.assertNotRegex(code, r"carbon_\w+_(?:add|mult)\s*=", path)

    def test_leaving_the_phaseout_stops_the_programmes(self):
        laws = _read(LAWS)
        for law in ("law_unrestricted_extraction", "law_fossil_expansion_moratorium"):
            self.assertIn("rt_stop_all_programmes = yes", _sub(_top_level(laws, law), "on_activate"), law)
        monthly = _top_level(_read(EFFECTS), "rt_country_monthly_update")
        self.assertRegex(monthly, r"NOT = \{ has_law = law_type:law_managed_fossil_phaseout \}\s*\}\s*"
                                  r"rt_stop_all_programmes = yes")

    def test_consistency_cascade_covers_the_group_after_the_ministry(self):
        text = _read(LAW_CONSISTENCY)
        order = re.findall(r'"(lawgroup_\w+)"', text[text.index("LAWGROUP_PRIORITY = ["):])
        self.assertLess(order.index("lawgroup_ministry_of_the_environment"),
                        order.index("lawgroup_resource_transition"))

    def test_every_ideology_with_an_environment_stance_has_a_transition_stance(self):
        text = _read(IDEOLOGY_GEN)
        ministry = len(re.findall(r'"lawgroup_ministry_of_the_environment": ministry_constructor\(', text))
        transition = len(re.findall(r'"lawgroup_resource_transition": transition_constructor\("[+\-0]+"\)', text))
        self.assertEqual(ministry, transition)
        hand = _read(os.path.join(REPO, "common", "ideologies", "extra_ideologies.txt"))
        self.assertEqual(hand.count("lawgroup_ministry_of_the_environment = {"),
                         hand.count("lawgroup_resource_transition = {"))
        generated = _read(os.path.join(REPO, "common", "ideologies", "modified.txt"))
        self.assertEqual(generated.count("lawgroup_resource_transition = {"), transition)


class ConstructionBanTest(unittest.TestCase):
    def test_each_building_blocks_government_private_and_auto_expansion(self):
        text = _read(BUILDINGS)
        for key, building in INDUSTRIES.items():
            injects = re.findall(rf"(?m)^INJECT:{building} = \{{", text)
            self.assertEqual(len(injects), 1, building)
            body = _top_level(text, f"INJECT:{building}")
            for field in ("can_build_government", "can_build_private"):
                self.assertEqual(" ".join(_sub(body, field).split()), "rt_fossil_construction_allowed_here = yes",
                                 (building, field))
            expand = " ".join(_sub(body, "should_auto_expand").split())
            self.assertEqual(expand, "default_auto_expand_rule = yes state = { rt_fossil_construction_allowed_here = yes }",
                             building)

    def test_the_law_that_counts_is_the_location_owners(self):
        allowed = _top_level(_read(TRIGGERS), "rt_fossil_construction_allowed_here")
        self.assertRegex(allowed, r"owner \?= \{\s*NOT = \{ rt_restrictive_transition_law = yes \}")
        restrictive = " ".join(_top_level(_read(TRIGGERS), "rt_restrictive_transition_law").split())
        self.assertEqual(restrictive, "OR = { has_law = law_type:law_fossil_expansion_moratorium "
                                      "has_law = law_type:law_managed_fossil_phaseout }")

    def test_no_other_building_is_touched(self):
        """Clean generation, synthetics and other mines stay buildable."""
        text = _read(BUILDINGS)
        users = re.findall(r"(?m)^(?:INJECT:|REPLACE:|REPLACE_OR_CREATE:)?(\w+) = \{", text)
        gated = [u for u in users if "rt_fossil_construction_allowed_here" in _top_level(
            text, next(p for p in (f"INJECT:{u}", f"REPLACE:{u}", f"REPLACE_OR_CREATE:{u}", u)
                       if re.search(rf"(?m)^{re.escape(p)} = \{{", text)))]
        self.assertEqual(sorted(gated), sorted(INDUSTRIES.values()))


class ProgrammeTest(unittest.TestCase):
    def test_player_and_ai_call_the_same_helpers(self):
        sguis, buttons = _read(SGUIS), _read(BUTTONS)
        for key, building in INDUSTRIES.items():
            start = f"rt_possible_start = {{ KEY = {key} BT = {building} }}"
            stop = f"rt_possible_stop = {{ KEY = {key} }}"
            sgui = _top_level(sguis, f"rt_programme_{key}_sgui")
            self.assertRegex(sgui, r"scope:op = 0 \}\s*" + re.escape(start))
            self.assertRegex(sgui, r"scope:op = 1 \}\s*" + re.escape(stop))
            self.assertRegex(sgui, r"scope:op = 0 is_player = yes \}\s*" + re.escape(f"rt_start_programme = {{ KEY = {key} }}"))
            self.assertRegex(sgui, r"scope:op = 1 is_player = yes \}\s*" + re.escape(f"rt_stop_programme = {{ KEY = {key} }}"))
            self.assertIn("ai_is_valid = {\n\t\talways = no", sgui)
            for action, possible in (("start", start), ("stop", stop)):
                button = _top_level(buttons, f"rt_{action}_{key}_button")
                self.assertRegex(button, r"visible = \{\s*is_ai = yes", (key, action))
                self.assertIn(f"possible = {{ {possible} }}", button)
                self.assertIn(f"effect = {{ rt_{action}_programme = {{ KEY = {key} }} }}", button)

    def test_the_entry_lists_every_ai_button(self):
        listed = set(re.findall(r"(?m)^\tscripted_button = (rt_\w+)", _read(JE)))
        defined = set(re.findall(r"(?m)^(rt_\w+_button) = \{", _read(BUTTONS)))
        self.assertEqual(listed, defined)
        self.assertEqual(len(defined), 6)

    def test_pulse_is_a_country_pulse_not_the_entrys(self):
        """Enforcement is independent of the journal entry (the issue)."""
        on_actions = _read(ON_ACTIONS)
        self.assertRegex(on_actions, r"on_monthly_pulse_country = \{\s*on_actions = \{\s*rt_country_monthly_on_action")
        self.assertIn("rt_country_monthly_update = yes", _top_level(on_actions, "rt_country_monthly_on_action"))
        self.assertNotIn("rt_", _sub(_top_level(_read(JE), "je_global_warming"), "on_monthly_pulse"))

    def test_the_entry_opens_for_a_restrictive_law(self):
        je = _top_level(_read(JE), "je_global_warming")
        for field in ("is_shown_when_inactive", "possible"):
            self.assertIn("rt_restrictive_transition_law = yes", _sub(je, field), field)

    def test_programme_state_is_country_variables(self):
        """A civil war's winner inherits variables, not modifiers or lists."""
        effects = _code(_read(EFFECTS))
        self.assertNotIn("add_to_variable_list", effects)
        self.assertNotRegex(effects, r"add_modifier = \{\s*name = rt_prog")
        for key in INDUSTRIES:
            self.assertIn(f"has_variable = rt_prog_{key}", _read(SGUIS))

    def test_retirement_removes_the_whole_smallest_building_and_pays(self):
        retire = _top_level(_read(EFFECTS), "rt_retire_smallest")
        self.assertIn("order_by = rt_retire_order_$KEY$", retire)
        self.assertIn("remove_building = $BT$", retire)
        self.assertRegex(retire, r"add_treasury = \{\s*value = scope:rt_retire_state\.var:rt_retired_cost\s*multiply = -1")
        self.assertRegex(retire, r"add_modifier = \{\s*name = rt_transition_assistance")
        for key in INDUSTRIES:
            order = _top_level(_read(VALUES), f"rt_retire_order_{key}")
            self.assertIn(f"value = rt_state_level_{key}", order)
            self.assertIn("multiply = -1", order)


class NumbersTest(unittest.TestCase):
    """The loc states the tuning constants; they must agree."""

    def test_interval(self):
        months = int(_constant("RT_RETIRE_INTERVAL_MONTHS"))
        for key in ("rt_law_phaseout_rule_tt", "rt_how_programmes", "rt_start_coal_tt",
                    "rt_start_oil_tt", "rt_start_power_tt", "rt_start_coal_button_desc"):
            self.assertIn(f"#v {months}#! months", _loc_value(key), key)

    def test_assistance_years(self):
        years = int(_constant("RT_ASSISTANCE_YEARS"))
        retire = _top_level(_read(EFFECTS), "rt_retire_smallest")
        self.assertRegex(retire, rf"years = {years}\s")
        for key in ("rt_how_programmes", "rt_start_coal_tt", "rt_law_phaseout_rule_tt"):
            self.assertIn(f"#v {years}#! years", _loc_value(key), key)

    def test_compensation_share(self):
        self.assertEqual(_constant("RT_COMPENSATION_SHARE"), 0.25)
        for key in ("rt_how_programmes", "rt_law_phaseout_rule_tt"):
            self.assertIn("a quarter of what it would cost to build", _loc_value(key), key)
        for key in ("concept_fossil_transition_desc",):
            self.assertIn(f"#v {int(_constant('RT_RETIRE_INTERVAL_MONTHS'))}#! months", _loc_value(key), key)


class InGameTextTest(unittest.TestCase):
    """What a player reads before deciding (#660 follow-up)."""

    def test_the_laws_say_there_is_no_emissions_cut_by_itself(self):
        for key in ("rt_law_emissions_tt", "concept_fossil_transition_desc", "rt_how_emissions"):
            text = _loc_value(key)
            self.assertTrue("emissions" in text and ("by itself" in text or "only if" in text), key)

    def test_the_phaseout_says_the_whole_building_goes_whoever_owns_it(self):
        for key in ("rt_law_phaseout_rule_tt", "rt_how_programmes"):
            text = _loc_value(key).lower()
            for phrase in ("whoever owns it, foreign investors included", "the whole building goes, every level",
                           "from the treasury"):
                self.assertIn(phrase, text, key)

    def test_the_moratorium_line_names_foreign_investors_and_what_carries_on(self):
        text = _loc_value("rt_law_moratorium_tt")
        for phrase in ("whoever invests, foreign investors included", "Those already running carry on"):
            self.assertIn(phrase, text)

    def test_law_descriptions_are_flavor_and_fit_the_enactment_popup(self):
        """The 'We now have <law>!' popup prints the description in a box that
        holds roughly nine lines and does not scroll. The phaseout's 650-character
        text of rules, in two paragraphs, ran over the law's name and art; the
        longest vanilla law description is 294 characters. A description is one
        short paragraph of flavor, with no figures: the rules are effect lines in
        the law's on_enact (and the hover on the Fossil Transition law line),
        as Collective Governance does it."""
        concept_names = {
            "[concept_greenhouse_gas_emissions]": "Greenhouse Gas Emissions",
            "[concept_fossil_transition]": "Fossil Transition",
            "$building_coal_mine$": "Coal Mine",
            "$building_oil_rig$": "Oil Rig",
            "$building_power_plant$": "Power Plant",
            "$je_global_warming$": "Global Warming",
        }
        for law in LAW_ORDER:
            raw = _loc_value(f"{law}_desc")
            text = raw
            for markup, name in concept_names.items():
                text = text.replace(markup, name)
            self.assertNotIn("\\n", raw, f"{law}: one paragraph, a break costs a line of the box")
            self.assertNotIn("#v", raw, f"{law}: figures belong in the effect lines")
            self.assertNotRegex(raw, r"\d", f"{law}: figures belong in the effect lines")
            self.assertNotRegex(text, r"\[|\$", f"{law}: unrendered markup left in the measure")
            self.assertLessEqual(len(text), MAX_LAW_DESC_CHARS, f"{law}: {len(text)} characters")

    def test_the_rules_are_effect_lines_in_on_enact(self):
        """Text in on_enact, work in on_activate (scripting_best_practices.md,
        'Law enactment preview'). Every effect line has loc."""
        laws = _read(LAWS)
        expected = {
            "law_unrestricted_extraction": [],
            "law_fossil_expansion_moratorium": ["rt_law_moratorium_tt", "rt_law_emissions_tt"],
            "law_managed_fossil_phaseout": ["rt_law_moratorium_tt", "rt_law_phaseout_tt", "rt_law_capture_tt",
                                            "rt_law_phaseout_rule_tt", "rt_law_emissions_tt"],
        }
        for law, lines in expected.items():
            body = _top_level(laws, law)
            self.assertEqual(re.findall(r"custom_tooltip = (\w+)", _code(body)), lines, law)
            if lines:
                self.assertEqual(re.findall(r"custom_tooltip = (\w+)", _sub(body, "on_enact")), lines, law)
                self.assertNotIn("custom_tooltip", _sub(body, "on_activate"), law)
            for key in lines:
                _loc_value(key)

    def test_the_hover_on_the_law_line_matches_the_enactment_preview(self):
        """rt_law_effects: the description, then the same effect lines, in order."""
        self.assertEqual(_loc_value("rt_law_line_tt"), "[Country.GetCustom('rt_law_effects')]")
        custom = _read(os.path.join(REPO, "common", "customizable_localization", "resource_transition_custom_loc.txt"))
        block = _top_level(custom, "rt_law_effects")
        laws = _read(LAWS)
        for law, composite in (("law_managed_fossil_phaseout", "rt_law_effects_phaseout"),
                               ("law_fossil_expansion_moratorium", "rt_law_effects_moratorium")):
            self.assertRegex(block, rf"has_law = law_type:{law} \}}\s*localization_key = {composite}\b")
            refs = re.findall(r"\$(\w+)\$", _loc_value(composite))
            lines = re.findall(r"custom_tooltip = (\w+)", _sub(_top_level(laws, law), "on_enact"))
            self.assertEqual(refs, [f"{law}_desc"] + lines, composite)
        self.assertRegex(block, r"always = yes \}\s*localization_key = law_unrestricted_extraction_desc")

    def test_start_tooltip_carries_the_cost(self):
        start = _top_level(_read(EFFECTS), "rt_start_programme")
        self.assertIn("custom_tooltip = rt_start_$KEY$_cost_tt", start)
        for key in INDUSTRIES:
            text = _loc_value(f"rt_start_{key}_cost_tt")
            self.assertIn(f"ScriptValue('rt_disp_next_cost_{key}')", text)
            self.assertIn(f"ScriptValue('rt_disp_all_cost_{key}')", text)

    def test_the_entry_explains_itself_with_the_rule_off(self):
        self.assertEqual(_loc_value("je_global_warming_reason"), "[ROOT.GetCountry.GetCustom('gw_reason')]")
        custom = _top_level(_read(os.path.join(REPO, "common", "customizable_localization",
                                               "global_warming_custom_loc.txt")), "gw_reason")
        self.assertRegex(custom, r"has_game_rule = global_warming_enabled \}\s*localization_key = je_global_warming_reason_climate")
        self.assertIn("localization_key = je_global_warming_reason_transition", custom)
        self.assertIn("Global Warming game rule is off", _loc_value("je_global_warming_reason_transition"))

    def test_the_concept_exists(self):
        concepts = _read(os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt"))
        self.assertRegex(concepts, r"(?m)^concept_fossil_transition = \{\}")
        self.assertEqual(_loc_value("concept_fossil_transition"), "Fossil Transition")


if __name__ == "__main__":
    unittest.main()
