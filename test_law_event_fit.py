"""The law-enactment events' effects and triggers fit the law being enacted.

events/extra_law_events.txt fires one event for several laws of a group, and
some of those laws point opposite ways. Issue #1613 listed where an event's
effect, description or debate did not fit one of its laws. What these checks
pin:

- extra_law_events.25 (language reform) shows a country's own classical tongue.
  te_heritage_hebrew holds for every Semitic-language culture and
  te_heritage_gothic for every Germanic one, so an Arabic, Ethiopian, Aramaic
  or Scandinavian country always held two heritage triggers and was shown
  d_multi; the four specific descriptions could never show.
- extra_law_events.32 (rules of war) never fires with "no amendment" as its
  only option.
- A side effect named for one direction is not applied when the law points the
  other way (.7.a, .16.a, .49.b, .52.b, .53.b), and the two debates whose
  options carried the opposite side's effect no longer do (.73, .77).
- A debate fires only for the laws its two clauses fit (.65, .77, .81, .82, as
  .79 was narrowed on 2026-10-12).
- The amendment-expiry events .85 and .86, whose descriptions name the
  Industrialists, need the group to exist.

No game install needed.
"""

import os
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
EVENTS = os.path.join(REPO, "events", "extra_law_events.txt")
SCRIPTED_TRIGGERS = (
    os.path.join(REPO, "common", "scripted_triggers", "te_heritage_triggers.txt"),
    os.path.join(REPO, "common", "scripted_triggers", "te_event_agency_a_triggers.txt"),
)


def _parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(path, apply_directives=False)
    return parser.data


def _entries(block):
    """Every (key, value) of a parsed block, duplicates included."""
    for key, node in block.items():
        for _, value in node if isinstance(node, list) else [node]:
            yield key, value


def _names(block, key):
    """Every `<key> = { name = X }` name anywhere under a block."""
    found = []
    for k, value in _entries(block):
        if k == key and isinstance(value, dict):
            found.extend(v for kk, v in _entries(value) if kk == "name")
        elif isinstance(value, dict):
            found.extend(_names(value, key))
    return found


def _culture_holds(block, culture):
    language, group = culture
    for key, value in _entries(block):
        if key == "has_discrimination_trait":
            ok = value == language
        elif key == "has_discrimination_trait_group":
            ok = value == group
        elif key == "OR":
            ok = any(_culture_holds({k: ("=", v)}, culture) for k, v in _entries(value))
        else:
            raise AssertionError(f"culture trigger not modelled: {key}")
        if not ok:
            return False
    return True


class Country:
    """The few facts the triggers under test read."""

    def __init__(self, cultures=(), religion=None, enacting=None, nuclear=False):
        self.cultures = cultures  # (language trait, language group) pairs
        self.religion = religion
        self.enacting = enacting
        self.nuclear = nuclear  # the nuclear game rule and the technology


class Evaluator:
    def __init__(self, scripted):
        self.scripted = scripted

    def one(self, key, value, country):
        if key in self.scripted:
            return self.holds(self.scripted[key][1], country) == (value == "yes")
        if key == "AND":
            return self.holds(value, country)
        if key == "OR":
            return any(self.one(k, v, country) for k, v in _entries(value))
        if key in ("NOR", "NOT"):
            return not any(self.one(k, v, country) for k, v in _entries(value))
        if key == "calc_true_if":
            members = [(k, v) for k, v in _entries(value) if k != "amount"]
            return sum(self.one(k, v, country) for k, v in members) >= int(value["amount"][1])
        if key == "always":
            return value == "yes"
        if key == "country_has_state_religion":
            return value == f"rel:{country.religion}"
        if key == "any_primary_culture":
            return any(_culture_holds(value, culture) for culture in country.cultures)
        if key == "is_enacting_law":
            return value == f"law_type:{country.enacting}"
        if key in ("has_game_rule", "has_technology_researched"):
            return country.nuclear
        if key == "currently_enacting_law":  # only asked whether it has an amendment yet
            return False
        raise AssertionError(f"trigger not modelled: {key}")

    def holds(self, block, country):
        return all(self.one(key, value, country) for key, value in _entries(block))


class LawEventFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = _parse(EVENTS)
        scripted = {}
        for path in SCRIPTED_TRIGGERS:
            scripted.update(_parse(path))
        cls.evaluate = Evaluator(scripted)

    def _event(self, number):
        return self.events[f"extra_law_events.{number}"][1]

    def _option(self, number, letter):
        for key, option in _entries(self._event(number)):
            if key == "option" and option["name"][1] == f"extra_law_events.{number}.{letter}":
                return option
        raise AssertionError(f"extra_law_events.{number}.{letter} not found")

    def _enacting_laws(self, number):
        """The laws an event's trigger names, at its top level or in its one OR."""
        event = self._event(number)
        if "trigger" not in event:
            return set()  # a hidden relay (#1596)
        trigger = event["trigger"][1]
        laws = [v for k, v in _entries(trigger) if k == "is_enacting_law"]
        for key, value in _entries(trigger):
            if key == "OR":
                laws.extend(v for k, v in _entries(value) if k == "is_enacting_law")
        return {law.removeprefix("law_type:") for law in laws}

    # --- .25: the description is the country's own tongue -----------------

    def _reform_description(self, country):
        ladder = self._event(25)["desc"][1]["first_valid"][1]["triggered_desc"]
        for _, rung in ladder:
            if self.evaluate.holds(rung["trigger"][1], country):
                return rung["desc"][1].removeprefix("extra_law_events.25.")
        raise AssertionError("no description holds")

    def test_one_tongue_gets_its_own_description(self):
        semitic, germanic = "language_group_semitic", "language_group_germanic"
        cases = {
            "d_arabic": Country([("language_arabic", semitic)], "sunni"),
            "d_geez": Country([("language_amharic", semitic)], "sunni"),
            "d_aramaic": Country([("language_aramaic", semitic)], "catholic"),
            "d_norse": Country([("language_scandinavian", germanic)], "protestant"),
            "d_germanic": Country([("language_germanophone", germanic)], "protestant"),
            "d_romance": Country([("language_french", "language_group_romance")], "catholic"),
            # Hebrew alone: a Jewish state religion, a culture with no claim.
            "d_semitic": Country([("language_basque", "language_group_isolate")], "jewish"),
            "d_default": Country([("language_basque", "language_group_isolate")], "catholic"),
        }
        for expected, country in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(self._reform_description(country), expected)

    def test_two_separate_claims_still_read_as_several(self):
        semitic = "language_group_semitic"
        cases = {
            "Ge'ez and Coptic": Country([("language_amharic", semitic)], "oriental_orthodox"),
            "Arabic and Hebrew by faith": Country([("language_arabic", semitic)], "jewish"),
            "Gothic and Hebrew by faith": Country([("language_yiddish", "language_group_germanic")], "jewish"),
            "Norse and Latin": Country(
                [("language_scandinavian", "language_group_germanic"), ("language_french", "language_group_romance")],
                "protestant",
            ),
        }
        for label, country in cases.items():
            with self.subTest(case=label):
                self.assertEqual(self._reform_description(country), "d_multi")

    # --- .32: always an amendment on offer ---------------------------------

    def test_rules_of_war_amendment_event_always_offers_an_amendment(self):
        event = self._event(32)
        fires = {}
        for law in ("law_humanitarian_regulations", "law_limited_war", "law_war_crimes_forbidden"):
            for nuclear in (True, False):
                country = Country(enacting=law, nuclear=nuclear)
                fires[law, nuclear] = self.evaluate.holds(event["trigger"][1], country)
                if not fires[law, nuclear]:
                    continue
                offered = [
                    letter
                    for letter in "ab"
                    if self.evaluate.holds(self._option(32, letter)["trigger"][1], country)
                ]
                with self.subTest(law=law, nuclear=nuclear):
                    self.assertTrue(offered, "the event fires with 'no amendment' as its only option")
        # Narrowed by exactly the one case.
        self.assertEqual([case for case, fired in fires.items() if not fired], [("law_limited_war", False)])

    # --- side effects follow the law's direction ---------------------------

    def _unconditional_modifiers(self, option):
        """Country modifiers the option adds whatever the law (not inside an if / else)."""
        return [v["name"][1] for k, v in _entries(option) if k == "add_modifier"]

    def _conditional(self, option, branch="if"):
        blocks = [v for k, v in _entries(option) if k == branch]
        self.assertEqual(len(blocks), 1, f"expected one {branch} block")
        return blocks[0]

    def test_stall_side_effects_are_gated_on_the_law(self):
        cases = {
            # option: (modifier, laws under which it must not apply)
            (49, "b"): ("langpol_assimilation_boost", {"law_multilingual_federalism", "law_ubiquitous_translation"}),
            (52, "b"): ("augment_health_panic", {"law_human_purity", "law_medical_augmentation_only"}),
            (53, "b"): (
                "inherit_wealth_consolidation",
                {"law_equal_inheritance", "law_state_universal_heir", "law_non_inheritable_usage_rights"},
            ),
        }
        for (number, letter), (modifier, excluded) in cases.items():
            option = self._option(number, letter)
            with self.subTest(option=f"{number}.{letter}"):
                self.assertNotIn(modifier, self._unconditional_modifiers(option))
                block = self._conditional(option)
                self.assertIn(modifier, _names(block, "add_modifier"))
                for law in self._enacting_laws(number):
                    applies = self.evaluate.holds(block["limit"][1], Country(enacting=law))
                    self.assertEqual(applies, law not in excluded, law)

    def test_advance_costs_fall_on_the_law_s_opponents(self):
        # .7.a: the Devout want the Ban, so its cost is the Intelligentsia's.
        option = self._option(7, "a")
        ban = self._conditional(option)
        self.assertTrue(self.evaluate.holds(ban["limit"][1], Country(enacting="law_ban_on_genetic_modification")))
        self.assertFalse(self.evaluate.holds(ban["limit"][1], Country(enacting="law_open_source_genetics")))
        self.assertIn("ig:ig_intelligentsia", ban)
        self.assertIn("scope:devout_ig", self._conditional(option, "else"))
        self.assertNotIn("scope:devout_ig", option)
        # .16.a: no augmentation health scare from a law that forbids augmentation.
        option = self._option(16, "a")
        self.assertNotIn("augment_health_panic", self._unconditional_modifiers(option))
        purity = self._conditional(option)
        self.assertTrue(self.evaluate.holds(purity["limit"][1], Country(enacting="law_human_purity")))
        self.assertFalse(self.evaluate.holds(purity["limit"][1], Country(enacting="law_unrestricted_augmentation")))
        self.assertNotIn("augment_health_panic", _names(purity, "add_modifier"))
        self.assertIn("augment_health_panic", _names(self._conditional(option, "else"), "add_modifier"))

    def test_debate_options_do_not_carry_the_other_side_s_effect(self):
        # .73: the assimilation push belongs to "bring everyone to the national language".
        self.assertNotIn("langpol_assimilation_boost", _names(self._option(73, "a"), "add_modifier"))
        self.assertIn("langpol_assimilation_boost", self._unconditional_modifiers(self._option(73, "b")))
        # .77: breaking up the estates does not strengthen the aristocrats.
        self.assertNotIn("inherit_wealth_consolidation", _names(self._option(77, "a"), "add_modifier"))

    # --- debates fire for the laws their clauses fit -----------------------

    def test_debates_are_narrowed_to_their_laws(self):
        expected = {
            65: {"law_moderate_data_privacy", "law_strong_privacy_rights"},
            77: {"law_equal_inheritance", "law_free_testation"},
            79: {"law_pro_natalist_subsidies", "law_state_sponsored_family_planning"},
            81: {"law_minority_rights_protection", "law_minority_rights_affirmative_action"},
            82: {"law_universal_basic_income"},
        }
        for number, laws in expected.items():
            with self.subTest(event=number):
                self.assertEqual(self._enacting_laws(number), laws)

    def test_narrowed_laws_keep_another_event(self):
        narrowed_out = {
            "law_intrusive_surveillance": 65,
            "law_state_universal_heir": 77,
            "law_non_inheritable_usage_rights": 77,
            "law_minority_rights_indifference": 81,
            "law_post-scarcity": 82,
        }
        for law, dropped in narrowed_out.items():
            others = [
                name
                for name, node in self.events.items()
                if name.startswith("extra_law_events.")
                and name != f"extra_law_events.{dropped}"
                and law in self._enacting_laws(name.split(".")[1])
            ]
            with self.subTest(law=law):
                self.assertTrue(others, f"{law} has no enactment event left")

    # --- .85 / .86 name the Industrialists ---------------------------------

    def test_expiry_events_need_the_industrialists(self):
        for number in (85, 86):
            with self.subTest(event=number):
                trigger = self._event(number)["trigger"][1]
                self.assertEqual(trigger.get("exists"), ("=", "ig:ig_industrialists"))


if __name__ == "__main__":
    unittest.main()
