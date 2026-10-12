# -*- coding: utf-8 -*-
"""International actions cost influence (owner, 2026-10-12).

The UN's stances, founding, programmes and own-motion resolutions, the two
outward cultural hegemony programmes and the hegemon's "Our Model Abroad"
choice hold a ``country_influence_cost_add`` while they run. Each figure is
restated three times: in the modifier, in a script value the button's gate
reads (``influence >= ...``), and in the tooltip that explains a refusal. The
engine checks none of them against the others, so a figure changed in one place
leaves a gate that lets a country into deficit or a tooltip that names the old
price. These tests pin the three together.

Covert operations cost influence through their pact ``cost``, by exposure tier,
and the AI launches a costed one only with influence to spare. Seven treaty
articles had their payer or their cost moved to influence: their
``maintenance_paid_by`` and the absence of an authority cost are pinned here.

Run: python3 -m unittest test_international_influence_costs -v
"""

import glob
import os
import re
import unittest

from test_covert_op_registry import TIERS

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


MODIFIERS = _path("common", "static_modifiers", "extra_modifiers.txt")
UN_VALUES = _path("common", "script_values", "un_script_values.txt")
UN_AI_VALUES = _path("common", "script_values", "un_ai_values.txt")
UN_BUTTONS = _path("common", "scripted_buttons", "un_buttons.txt")
UN_TRIGGERS = _path("common", "scripted_triggers", "un_propose_triggers.txt")
UN_EFFECTS = _path("common", "scripted_effects", "un_propose_effects.txt")
CH_VALUES = _path("common", "script_values", "cultural_hegemony_script_values.txt")
CH_TRIGGERS = _path("common", "scripted_triggers", "cultural_hegemony_triggers.txt")
COVERT_ACTIONS = _path("common", "diplomatic_actions", "covert_operations.txt")
COVERT_VALUES = _path("common", "script_values", "covert_warfare_script_values.txt")
TREATIES = _path("common", "treaty_articles")
LOC_DIR = _path("localization", "english")


def _raw(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _read(path):
    return re.sub(r"#[^\n]*", "", _raw(path))


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


def _value(text, name):
    """A constant script value, written ``name = N`` or ``name = { value = N }``."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*(?:\{\s*value\s*=\s*)?(-?\d+(?:\.\d+)?)\b", text, re.M)
    if m is None:
        raise AssertionError(f"{name} is not a constant")
    return float(m.group(1))


def _field(body, field):
    m = re.search(r"\b" + re.escape(field) + r"\s*=\s*(-?\d+(?:\.\d+)?)", body)
    return None if m is None else float(m.group(1))


def _loc():
    keys = {}
    for path in glob.glob(os.path.join(LOC_DIR, "*_l_english.yml")):
        for line in _raw(path).splitlines():
            m = re.match(r'^ ([\w.]+):\d* "(.*)"\s*$', line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


def _bold_number(text):
    m = re.search(r"#bold (\d+)#!", text)
    if m is None:
        raise AssertionError(f"no bold figure in {text!r}")
    return float(m.group(1))


# (modifier, script value the gate reads, tooltip key, values file)
GATED_COSTS = (
    ("un_founding_cost_modifier", "un_found_influence_cost", "un_found_influence_tt", UN_VALUES),
    ("un_champion_order_cost", "un_stance_influence_cost", "un_stance_influence_tt", UN_VALUES),
    ("un_undermine_order_cost", "un_stance_influence_cost", "un_stance_influence_tt", UN_VALUES),
    ("un_peacekeeping_contributor_modifier", "un_programme_influence_cost", "un_programme_influence_tt", UN_VALUES),
    ("un_human_rights_champion_modifier", "un_programme_influence_cost", "un_programme_influence_tt", UN_VALUES),
    ("un_arms_control_participant_modifier", "un_programme_influence_cost", "un_programme_influence_tt", UN_VALUES),
    ("un_sponsor_cost_modifier", "un_sponsor_influence_cost", "un_sponsor_influence_tt", UN_VALUES),
    ("un_sponsor_punitive_cost_modifier", "un_sponsor_punitive_influence_cost",
     "un_sponsor_punitive_influence_tt", UN_VALUES),
    ("ch_cultural_institutes_program", "ch_cultural_institutes_influence_cost", "CH_INSTITUTES_INFLUENCE_TT", CH_VALUES),
    ("ch_global_media_campaign", "ch_global_media_influence_cost", "CH_MEDIA_INFLUENCE_TT", CH_VALUES),
)

# Influence instead of the authority or bureaucracy they used to cost.
INFLUENCE_ONLY = (
    "un_founding_cost_modifier",
    "un_champion_order_cost",
    "un_undermine_order_cost",
    "un_peacekeeping_contributor_modifier",
    "un_human_rights_champion_modifier",
    "un_arms_control_participant_modifier",
    "ch_cultural_institutes_program",
    "ch_global_media_campaign",
    "ch_model_champion",
)

# Each button's `possible` asks for its tooltip's figure.
BUTTON_GATES = {
    "un_found_button": "un_found_influence_cost",
    "un_champion_order_button": "un_stance_influence_cost",
    "un_undermine_order_button": "un_stance_influence_cost",
    "un_peacekeeping_mission_button": "un_programme_influence_cost",
    "un_human_rights_resolution_button": "un_programme_influence_cost",
    "un_arms_control_button": "un_programme_influence_cost",
}

# Own-motion topics by the sponsor's cost they take. Requests for help take none.
PUNITIVE_TOPICS = ("sanctions", "expulsion", "mandate", "court_referral", "arms_embargo", "credentials")
STANDARD_TOPICS = ("condemn", "reform", "standing_force", "food_reserve", "ceasefire",
                   "development_fund", "referendum")
REQUESTS = ("peacekeepers", "aid", "observer_request")

COVERT_TIER_COST = {"mild": 25, "moderate": 50, "severe": 100, "war": 0}

# Articles the beneficiary now pays for, as vanilla's demands and gifts do.
TARGET_PAYS = (
    ("101_disband_company.txt", "disband_company"),
    ("102_seize_company.txt", "seize_company"),
    ("118_return_cultural_property.txt", "return_cultural_property"),
    ("119_surrender_monument.txt", "surrender_monument"),
    ("extra_treaty_articles.txt", "suppress_subject_liberty"),
)
# Articles that cost influence alone, at these figures.
INFLUENCE_ONLY_ARTICLES = {"crisis_resolution": 500, "development_assistance": 200}


class GatedCostTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modifiers = _read(MODIFIERS)
        cls.loc = _loc()
        cls.values = {UN_VALUES: _read(UN_VALUES), CH_VALUES: _read(CH_VALUES)}

    def test_modifier_value_and_tooltip_agree(self):
        for modifier, value, tooltip, values_file in GATED_COSTS:
            with self.subTest(modifier=modifier):
                cost = _field(_block(self.modifiers, modifier), "country_influence_cost_add")
                self.assertIsNotNone(cost, f"{modifier} has no country_influence_cost_add")
                self.assertEqual(cost, _value(self.values[values_file], value))
                self.assertEqual(cost, _bold_number(self.loc[tooltip]))

    def test_no_authority_or_bureaucracy_cost_left(self):
        for modifier in INFLUENCE_ONLY:
            body = _block(self.modifiers, modifier)
            with self.subTest(modifier=modifier):
                self.assertIsNotNone(_field(body, "country_influence_cost_add"))
                for field in ("country_authority_cost_add", "country_bureaucracy_cost_add",
                              "country_bureaucracy_add", "country_influence_add", "country_influence_mult"):
                    self.assertNotIn(field, body)

    def test_founding_cost_matches_a_power_bloc(self):
        self.assertEqual(_field(_block(self.modifiers, "un_founding_cost_modifier"),
                                "country_influence_cost_add"), 500)
        for stance in ("un_champion_order_cost", "un_undermine_order_cost"):
            self.assertEqual(_field(_block(self.modifiers, stance), "country_influence_cost_add"), 500)


class UnGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.buttons = _read(UN_BUTTONS)
        cls.triggers = _read(UN_TRIGGERS)
        cls.effects = _read(UN_EFFECTS)
        cls.ai = _read(UN_AI_VALUES)

    def test_each_button_asks_for_its_cost(self):
        for button, value in BUTTON_GATES.items():
            with self.subTest(button=button):
                self.assertIn(f"influence >= {value}", self._possible(button))

    def _possible(self, button):
        body = _block(self.buttons, button)
        i = body.index("possible = {")
        depth = 0
        for j in range(i + len("possible = "), len(body)):
            if body[j] == "{":
                depth += 1
            elif body[j] == "}":
                depth -= 1
                if depth == 0:
                    return body[i:j + 1]
        raise AssertionError(f"{button}'s possible is not closed")

    def test_ai_takes_up_a_stance_or_programme_only_with_influence_to_spare(self):
        self.assertIn("influence >= un_ai_stance_influence_start", _block(self.ai, "un_champion_order_ai_chance"))
        self.assertIn("influence >= un_ai_stance_influence_start", _block(self.ai, "un_undermine_order_ai_chance"))
        self.assertIn("influence >= un_ai_programme_influence_start", _block(self.ai, "un_peacekeeping_ai_chance"))
        for off in ("un_stop_championing_ai_chance", "un_stop_undermining_ai_chance",
                    "un_end_peacekeeping_ai_chance"):
            with self.subTest(off=off):
                self.assertIn("influence < 0", _block(self.ai, off))
        self.assertGreater(_value(self.ai, "un_ai_influence_spare"), 0)

    def test_punitive_topics_take_the_punitive_cost(self):
        for topic in PUNITIVE_TOPICS:
            with self.subTest(topic=topic):
                possible = _block(self.triggers, f"un_propose_{topic}_possible")
                effect = _block(self.effects, f"un_propose_{topic}_effect")
                self.assertTrue("un_propose_can_afford_sponsor_punitive = yes" in possible
                                or "un_propose_own_motion_possible_punitive = yes" in possible)
                self.assertTrue("un_propose_sponsor_punitive_cost = yes" in effect
                                or "un_propose_own_motion_costs_punitive = yes" in effect)
                self.assertNotIn("un_propose_own_motion_possible = yes", possible)
                self.assertNotIn("un_propose_own_motion_costs = yes", effect)

    def test_standard_topics_take_the_sponsor_cost(self):
        for topic in STANDARD_TOPICS:
            with self.subTest(topic=topic):
                possible = _block(self.triggers, f"un_propose_{topic}_possible")
                effect = _block(self.effects, f"un_propose_{topic}_effect")
                self.assertTrue("un_propose_can_afford_sponsor = yes" in possible
                                or "un_propose_own_motion_possible = yes" in possible)
                self.assertTrue("un_propose_sponsor_cost = yes" in effect
                                or "un_propose_own_motion_costs = yes" in effect)
                self.assertNotIn("punitive", possible + effect)

    def test_requests_for_help_are_free(self):
        for topic in REQUESTS:
            with self.subTest(topic=topic):
                possible = _block(self.triggers, f"un_propose_{topic}_possible")
                effect = _block(self.effects, f"un_propose_{topic}_effect")
                self.assertNotIn("sponsor", possible + effect)
                self.assertNotIn("own_motion", possible + effect)

    def test_shared_helpers_carry_the_costs(self):
        self.assertIn("un_propose_can_afford_sponsor = yes", _block(self.triggers, "un_propose_own_motion_possible"))
        self.assertIn("un_propose_can_afford_sponsor_punitive = yes",
                      _block(self.triggers, "un_propose_own_motion_possible_punitive"))
        self.assertIn("un_propose_sponsor_cost = yes", _block(self.effects, "un_propose_own_motion_costs"))
        self.assertIn("un_propose_sponsor_punitive_cost = yes",
                      _block(self.effects, "un_propose_own_motion_costs_punitive"))
        self.assertIn("name = un_sponsor_cost_modifier", _block(self.effects, "un_propose_sponsor_cost"))
        self.assertIn("name = un_sponsor_punitive_cost_modifier",
                      _block(self.effects, "un_propose_sponsor_punitive_cost"))
        self.assertIn("influence >= un_sponsor_influence_cost",
                      _block(self.triggers, "un_propose_can_afford_sponsor"))
        self.assertIn("influence >= un_sponsor_punitive_influence_cost",
                      _block(self.triggers, "un_propose_can_afford_sponsor_punitive"))


class CulturalHegemonyGateTest(unittest.TestCase):
    def test_programmes_ask_for_their_cost(self):
        triggers = _read(CH_TRIGGERS)
        self.assertIn("influence >= ch_cultural_institutes_influence_cost",
                      _block(triggers, "ch_possible_cultural_institutes"))
        self.assertIn("influence >= ch_global_media_influence_cost",
                      _block(triggers, "ch_possible_global_media_campaign"))

    def test_ai_start_leaves_influence_to_spare(self):
        values = _read(CH_VALUES)
        for cost, start in (("ch_cultural_institutes_influence_cost", "ch_cultural_institutes_ai_influence_start"),
                            ("ch_global_media_influence_cost", "ch_global_media_ai_influence_start")):
            with self.subTest(cost=cost):
                self.assertGreater(_value(values, start), _value(values, cost))


class CovertCostTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actions = _read(COVERT_ACTIONS)

    def test_pact_cost_by_exposure_tier(self):
        for op_type, tier in TIERS.items():
            with self.subTest(op_type=op_type):
                block = _block(self.actions, f"covert_{op_type}_action")
                pact = block[block.index("\tpact = {"):]
                self.assertEqual(_field(pact, "cost"), COVERT_TIER_COST[tier])

    def test_costed_operations_launch_only_with_influence_to_spare(self):
        for op_type, tier in TIERS.items():
            block = _block(self.actions, f"covert_{op_type}_action")
            gate = f"covert_ai_can_spare_influence = {{ TYPE = covert_{op_type}_action }}"
            with self.subTest(op_type=op_type):
                if COVERT_TIER_COST[tier]:
                    self.assertIn(gate, block)
                else:
                    self.assertNotIn("covert_ai_can_spare_influence", block)

    def test_floor_covers_a_great_powers_dearest_operation(self):
        # The engine doubles a pact's cost for a great power.
        floor = _value(_read(COVERT_VALUES), "covert_ai_influence_floor")
        self.assertGreater(floor, 2 * max(COVERT_TIER_COST.values()))


class TreatyPayerTest(unittest.TestCase):
    def test_beneficiary_pays(self):
        for filename, article in TARGET_PAYS:
            with self.subTest(article=article):
                body = _block(_read(os.path.join(TREATIES, filename)), article)
                self.assertRegex(body, r"\bmaintenance_paid_by\s*=\s*target_country\b")

    def test_influence_only_articles(self):
        text = _read(os.path.join(TREATIES, "extra_treaty_articles.txt"))
        for article, cost in INFLUENCE_ONLY_ARTICLES.items():
            with self.subTest(article=article):
                body = _block(text, article)
                self.assertEqual(_field(body, "cost"), cost)
                self.assertNotIn("country_authority_cost_add", body)
                self.assertNotRegex(body, r"\bauthority\s*[<>]")


if __name__ == "__main__":
    unittest.main()
