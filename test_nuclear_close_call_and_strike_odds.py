"""Two rules from #1619.

The Close Call (nuclear_weapon_events.21) is the false alarm of a country
with no arsenal in service: warning stations (radar), not armed, a rival
believed armed. It used to ask for the nuclear_power modifier as well, which
with "not armed" left only a country that had used or lost its last warhead.

A country that launches warheads without the nuclear_weapons technology (an
arsenal that came by custody) gets that technology's +1 attack success in
every strike formula, through one shared value, and the odds' tooltips show
it as a line of its own.
"""

import re
import unittest

from test_nuclear_deterrence import (EXTRA_EFFECTS, EXTRA_VALUES, ROOT, TRIGGERS, VALUES,
                                     WEAPON_EVENTS, block, loc_value, option_body, read,
                                     squash, strip_comments)

ON_ACTIONS = ROOT / "common/on_actions/extra_on_actions.txt"
STATIC_MODIFIERS = ROOT / "common/static_modifiers/extra_modifiers.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/zzz_extra_custom_loc.txt"
TECH_ERA_6 = ROOT / "common/technology/technologies/era_6.txt"
DETERRENCE_EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"

CLOSE_CALL = "nuclear_weapon_events.21"
GATE = ("has_technology_researched = radar", "NOT = { nd_is_armed = yes }",
        "any_rival_country = { nd_believed_armed = yes }")
RAW_MODIFIER = "modifier:country_nuclear_weapon_attack_success_add"
SHARED = "nuclear_strike_attack_rating"


class TestCloseCallGate(unittest.TestCase):

    def setUp(self):
        self.event = block(strip_comments(read(WEAPON_EVENTS)), CLOSE_CALL)

    def test_the_event_needs_no_arsenal_of_ours(self):
        trigger = squash(block(self.event, "trigger"))
        for needle in GATE:
            self.assertIn(needle, trigger)
        self.assertNotIn("has_modifier = nuclear_power", trigger,
                         "with 'not armed', only a country that spent its last warhead held it")

    def test_the_pool_entry_asks_the_same_tests(self):
        text = strip_comments(read(ON_ACTIONS))
        at = text.index("id = " + CLOSE_CALL)
        entry = squash(text[text.rindex("trigger = {", 0, at):at])
        for needle in GATE + ("has_game_rule = nuclear_weapons_enabled",):
            self.assertIn(needle, entry)
        self.assertNotIn("has_modifier = nuclear_power", entry)

    def test_believed_armed_carries_the_game_rule(self):
        """The event's own trigger has no rule test; nd_believed_armed is it."""
        believed = squash(block(strip_comments(read(TRIGGERS)), "nd_believed_armed"))
        self.assertIn("has_game_rule = nuclear_weapons_enabled", believed)

    def test_no_text_speaks_of_an_arsenal_or_a_launch_of_ours(self):
        for suffix in ("t", "d", "f", "a", "b", "c"):
            text = loc_value(f"{CLOSE_CALL}.{suffix}")
            self.assertIsNotNone(text, suffix)
            for word in ("arsenal", "retaliat", "our missiles", "our warheads", "our weapons",
                         "launch", "safety procedures"):
                self.assertNotIn(word, text.lower(), f"{CLOSE_CALL}.{suffix}: {word}")

    def test_the_review_is_named_for_the_warning_stations(self):
        option = squash(option_body(read(WEAPON_EVENTS), CLOSE_CALL + ".a"))
        self.assertIn("name = nuclear_warning_review", option)
        self.assertNotIn("nuclear_safety_review", option,
                         "its description speaks of nuclear research protocols")
        modifiers = strip_comments(read(STATIC_MODIFIERS))
        self.assertEqual(squash(block(modifiers, "nuclear_warning_review")),
                         squash(block(modifiers, "nuclear_safety_review")),
                         "the twin keeps the programme review's values")
        for key in ("nuclear_warning_review", "nuclear_warning_review_desc"):
            text = loc_value(key)
            self.assertIsNotNone(text, key)
            self.assertNotIn("nuclear", text.lower().replace("nuclear strike", ""), key)

    def test_the_ai_weight_needs_no_stockpile_of_ours(self):
        option = squash(option_body(strip_comments(read(WEAPON_EVENTS)), CLOSE_CALL + ".b"))
        self.assertNotIn("trigger = { has_variable = nuclear_weapon_stockpile", option,
                         "an unarmed country has no such variable, so the weight never applied")
        self.assertIn("NOT = { ROOT = { has_variable = nuclear_weapon_stockpile } }", option)


class TestStrikeOddsWithoutTheTechnology(unittest.TestCase):

    def setUp(self):
        self.values = strip_comments(read(EXTRA_VALUES))
        self.triggers = strip_comments(read(TRIGGERS))

    def test_the_technology_gives_plus_one(self):
        """The +1 the shared value stands in for."""
        tech = squash(block(strip_comments(read(TECH_ERA_6)), "nuclear_weapons"))
        self.assertIn("country_nuclear_weapon_attack_success_add = 1", tech)

    def test_the_shared_value_adds_the_technologys_plus_one(self):
        rating = squash(block(self.values, SHARED))
        self.assertEqual(
            rating,
            f"value = {RAW_MODIFIER} if = {{ limit = {{ nd_lacks_weapon_technology = yes }} add = 1 }}")
        self.assertEqual(squash(block(self.triggers, "nd_lacks_weapon_technology")),
                         "NOT = { has_technology_researched = nuclear_weapons }",
                         "with the technology the value is the modifier unchanged")

    def test_the_strike_roll_does_not_test_the_stockpile(self):
        """Every strike path takes the warhead off before it rolls, so a
        stockpile test would deny a last warhead its +1."""
        lacks = squash(block(self.triggers, "nd_lacks_weapon_technology"))
        self.assertNotIn("stockpile", lacks)
        self.assertNotIn("nd_is_armed", lacks)
        for path, name in ((EXTRA_EFFECTS, "nuclear_first_strike"),
                           (DETERRENCE_EFFECTS, "nd_tactical_strike_resolve")):
            body = squash(block(strip_comments(read(path)), name))
            self.assertLess(body.index("name = nuclear_weapon_stockpile"),
                            body.index("modifier = nuclear_strike_success_chance"), name)

    def test_every_strike_formula_reads_the_shared_value(self):
        chance = squash(block(self.values, "nuclear_strike_success_chance"))
        self.assertTrue(chance.startswith(f"value = {SHARED} "), chance)
        here = squash(block(self.values, "nuclear_strike_success_fraction_here"))
        for holder in ("scope:target_country", "scope:attacking_country", "root"):
            self.assertIn(f"add = {holder}.{SHARED}", here)
        capital = squash(block(strip_comments(read(VALUES)), "nd_ai_capital_hit_share"))
        self.assertTrue(capital.startswith(f"value = {SHARED} "), capital)

    def test_nothing_else_reads_the_raw_modifier(self):
        """A new formula that reads the modifier directly would again clamp a
        custody arsenal to 5%. Only the shared value and the panel's display
        (which adds the +1 for a holder itself) may."""
        allowed = {SHARED, "nuclear_program_display_attack_rating"}
        readers = set()
        for path in sorted((ROOT / "common").rglob("*.txt")) + sorted((ROOT / "events").rglob("*.txt")):
            text = strip_comments(read(path))
            if RAW_MODIFIER not in text:
                continue
            for m in re.finditer(r"^([A-Za-z_0-9]+)\s*=\s*\{", text, re.M):
                if RAW_MODIFIER in block(text, m.group(1)):
                    readers.add(m.group(1))
        self.assertEqual(readers, allowed)

    def test_the_panel_shows_it_only_to_a_holder(self):
        display = squash(block(self.values, "nuclear_program_display_attack_rating"))
        self.assertIn("if = { limit = { nd_holds_arsenal_without_technology = yes } add = 1 }", display)
        holds = squash(block(self.triggers, "nd_holds_arsenal_without_technology"))
        self.assertEqual(holds, "nd_is_armed = yes nd_lacks_weapon_technology = yes")

    def test_the_tooltips_carry_the_line(self):
        custom = squash(block(strip_comments(read(CUSTOM_LOC)), "te_nuke_attack_held_arsenal"))
        self.assertIn("trigger = { nd_holds_arsenal_without_technology = yes } "
                      "localization_key = nuke_attack_line_held_arsenal", custom)
        self.assertIn("+100%", loc_value("nuke_attack_line_held_arsenal"))
        for key in ("je_nuclear_program_widget_delivery_tt", "nuke_success_chance_desc",
                    "nuke_success_final_chance_breakdown_tt"):
            self.assertIn("GetCustom('te_nuke_attack_held_arsenal')", loc_value(key), key)


if __name__ == "__main__":
    unittest.main()
