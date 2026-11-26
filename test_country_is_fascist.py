"""``country_is_fascist`` holds for the countries the world-war guide says it does, and for no others.

Its second branch used to AND Autocracy with Single-Party State, both in ``lawgroup_distribution_of_power``,
so no country passed it and only Corporate State with Single-Party State was ever fascist. It now follows
the Fascist political model of ``ch_set_political_model`` (``cultural_hegemony_effects.txt``), kept to a
one-party state or an autocracy so the camp never meets the democratic one:

* Corporate State with Single-Party State;
* Ancestral Citizenship under Autocracy or Single-Party State;
* Cultural Citizenship in a Single-Party State the left does not run;
* Cultural Citizenship under Autocracy run by fascists;
* never under a Council Republic, which the model tests first.

The trigger text is parsed and evaluated here over concrete law sets, so the table below is read from the
script, not restated from it. ``ch_government_led_by_the_left`` and ``ch_government_led_by_fascists`` are
inputs. Every law test is read as the engine reads it: ``has_law`` is the exact law, ``has_law_or_variant``
also takes a variant of it (Bakufu and Neo-Absolutism for Autocracy).

Run: python3 -m pytest test_country_is_fascist.py
"""

import itertools
import re
import unittest
from pathlib import Path

from test_law_has_law_same_group import TOKEN, code, law_groups

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/world_war_triggers.txt"
LAWS_DIR = ROOT / "common/laws"
VANILLA_LAWS = ROOT / "vanilla_parsed/common/laws.json"

# The groups the three camps read, and the one input each camp's trigger takes from the government.
CAMP_GROUPS = (
    "lawgroup_distribution_of_power",
    "lawgroup_governance_principles",
    "lawgroup_citizenship",
    "lawgroup_economic_system",
)
FLAG_TRIGGERS = ("ch_government_led_by_the_left", "ch_government_led_by_fascists")


def parse_block(tokens, i):
    """(key, value) pairs up to the closing brace; a value is a token or a nested list of pairs."""
    items = []
    while i < len(tokens) and tokens[i] != "}":
        if i + 2 >= len(tokens) or tokens[i + 1] != "=":
            raise ValueError(f"cannot read {' '.join(tokens[i : i + 4])!r}")
        key = tokens[i]
        if tokens[i + 2] == "{":
            value, i = parse_block(tokens, i + 3)
            i += 1
        else:
            value, i = tokens[i + 2], i + 3
        items.append((key, value))
    return items, i


def trigger_bodies():
    """Trigger name -> the tokens between its braces, for each top-level trigger in the file.

    The file also holds triggers with comparisons (``>=``) that ``parse_block`` does not read; the
    ones these tests evaluate are parsed on demand, and only those.
    """
    tokens = TOKEN.findall(code(TRIGGERS))
    bodies, i = {}, 0
    while i + 2 < len(tokens):
        if tokens[i + 1] == "=" and tokens[i + 2] == "{":
            depth, j = 1, i + 3
            while depth and j < len(tokens):
                depth += {"{": 1, "}": -1}.get(tokens[j], 0)
                j += 1
            bodies[tokens[i]] = tokens[i + 3 : j - 1]
            i = j
        else:
            i += 1
    return bodies


def law_parents():
    """Variant -> parent law, from the vanilla snapshot and the mod's own law files."""
    import json

    parents = {}
    for key, value in json.loads(VANILLA_LAWS.read_text(encoding="utf-8")).items():
        body = value[1] if isinstance(value, list) and isinstance(value[1], dict) else {}
        if "parent" in body:
            parents[key] = body["parent"][1]
    header = re.compile(r"^(?:REPLACE:|INJECT:)?(law_\w+)\s*=\s*\{[^{}]*?\bparent\s*=\s*(law_\w+)", re.M)
    for path in sorted(LAWS_DIR.glob("*.txt")):
        for m in header.finditer(code(path)):
            parents[m.group(1)] = m.group(2)
    return parents


class Evaluator:
    """The boolean structure of a trigger, with one concrete country: a set of law keys and two inputs."""

    def __init__(self, bodies, parents):
        self.bodies = bodies
        self.parents = parents
        self._parsed = {}

    def definition(self, name):
        if name not in self._parsed:
            self._parsed[name] = parse_block(self.bodies[name], 0)[0]
        return self._parsed[name]

    def holds(self, name, laws, left=False, fascists=False):
        flags = {"ch_government_led_by_the_left": left, "ch_government_led_by_fascists": fascists}
        return self._all(self.definition(name), frozenset(laws), flags)

    def _all(self, items, laws, flags):
        return all(self._one(k, v, laws, flags) for k, v in items)

    def _any(self, items, laws, flags):
        return any(self._one(k, v, laws, flags) for k, v in items)

    def _one(self, key, value, laws, flags):
        if key == "AND":
            return self._all(value, laws, flags)
        if key == "OR":
            return self._any(value, laws, flags)
        if key in ("NOT", "NOR"):  # several children under NOT read as NOR
            return not self._any(value, laws, flags)
        if key == "NAND":
            return not self._all(value, laws, flags)
        if key in ("has_law", "has_law_or_variant"):
            law = value.removeprefix("law_type:")
            if key == "has_law":
                return law in laws
            return law in laws or any(self.parents.get(held) == law for held in laws)
        if key in flags:
            return flags[key] == (value == "yes")
        if key in self.bodies and value in ("yes", "no"):
            return self._all(self.definition(key), laws, flags) == (value == "yes")
        raise ValueError(f"the evaluator does not model `{key} = {value}`: teach it, or the test reads nothing")


def evaluator():
    return Evaluator(trigger_bodies(), law_parents())


# (what it is, the laws held, led by the left, led by fascists, is it fascist)
CASES = (
    ("Corporate State with Single-Party State", ("law_corporate_state", "law_single_party_state"), False, False, True),
    ("Corporate State under Autocracy", ("law_corporate_state", "law_autocracy"), False, False, False),
    ("Corporate State under Oligarchy", ("law_corporate_state", "law_oligarchy"), False, False, False),
    ("Ancestral Citizenship under Autocracy", ("law_autocracy", "law_ethnostate"), False, False, True),
    ("Ancestral Citizenship under Single-Party State", ("law_single_party_state", "law_ethnostate"), False, False, True),
    ("Ancestral Citizenship under Bakufu", ("law_bakufu", "law_ethnostate"), False, False, True),
    ("Ancestral Citizenship under Neo-Absolutism", ("law_neo_absolutism", "law_ethnostate"), False, False, True),
    ("Ancestral Citizenship under Oligarchy", ("law_oligarchy", "law_ethnostate"), False, False, False),
    (
        "Ancestral Citizenship in a democracy",
        ("law_universal_suffrage", "law_parliamentary_republic", "law_ethnostate"),
        False,
        True,
        False,
    ),
    ("Cultural Citizenship under Autocracy", ("law_autocracy", "law_national_supremacy"), False, False, False),
    ("Cultural Citizenship under Autocracy, the left in charge", ("law_autocracy", "law_national_supremacy"), True, False, False),
    ("Cultural Citizenship under Autocracy run by fascists", ("law_autocracy", "law_national_supremacy"), False, True, True),
    ("Cultural Citizenship under Bakufu run by fascists", ("law_bakufu", "law_national_supremacy"), False, True, True),
    ("Cultural Citizenship in a Single-Party State", ("law_single_party_state", "law_national_supremacy"), False, False, True),
    (
        "Cultural Citizenship in a Single-Party State the left runs",
        ("law_single_party_state", "law_national_supremacy"),
        True,
        False,
        False,
    ),
    ("Cultural Citizenship under Oligarchy run by fascists", ("law_oligarchy", "law_national_supremacy"), False, True, False),
    ("Racialized Citizenship under Single-Party State", ("law_single_party_state", "law_racial_segregation"), False, False, False),
    ("Racialized Citizenship under Autocracy run by fascists", ("law_autocracy", "law_racial_segregation"), False, True, False),
    ("Cultural Exclusion under Single-Party State", ("law_single_party_state", "law_cultural_exclusion"), False, True, False),
    (
        "Council Republic, Single-Party State and Ancestral Citizenship",
        ("law_council_republic", "law_single_party_state", "law_ethnostate"),
        False,
        True,
        False,
    ),
    (
        "Council Republic, Autocracy and Cultural Citizenship run by fascists",
        ("law_council_republic", "law_autocracy", "law_national_supremacy"),
        False,
        True,
        False,
    ),
)


class FascistTruthTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ev = evaluator()

    def test_each_case(self):
        for what, laws, left, fascists, expected in CASES:
            with self.subTest(what):
                self.assertEqual(self.ev.holds("country_is_fascist", laws, left, fascists), expected, what)

    def test_the_variants_the_cases_rest_on_are_variants_of_autocracy(self):
        parents = law_parents()
        self.assertEqual(parents.get("law_bakufu"), "law_autocracy")
        self.assertEqual(parents.get("law_neo_absolutism"), "law_autocracy")

    def test_the_cases_name_laws_that_exist_in_the_groups_the_camps_read(self):
        groups = law_groups()
        for what, laws, *_ in CASES:
            for law in laws:
                self.assertIn(law, groups, f"{what}: {law} is not a law")


class CampsAreDisjointTest(unittest.TestCase):
    """A country holds one law a group, so enumerate one law from each group the camps read."""

    @classmethod
    def setUpClass(cls):
        cls.ev = evaluator()
        groups = law_groups()
        cls.by_group = {g: sorted(law for law, grp in groups.items() if grp == g) for g in CAMP_GROUPS}

    def countries(self):
        for held in itertools.product(*(self.by_group[g] for g in CAMP_GROUPS)):
            for left, fascists in itertools.product((False, True), repeat=2):
                yield held, left, fascists

    def test_the_groups_are_read(self):
        for group in CAMP_GROUPS:
            self.assertGreater(len(self.by_group[group]), 3, group)
        self.assertIn("law_autocracy", self.by_group["lawgroup_distribution_of_power"])
        self.assertIn("law_liquid_democracy", self.by_group["lawgroup_distribution_of_power"])
        self.assertIn("law_council_republic", self.by_group["lawgroup_governance_principles"])
        self.assertIn("law_ethnostate", self.by_group["lawgroup_citizenship"])

    def test_the_search_finds_fascist_countries_at_all(self):
        """Without one the checks below would pass on a trigger that is never true."""
        self.assertTrue(any(self.ev.holds("country_is_fascist", *c) for c in self.countries()))
        self.assertTrue(any(self.ev.holds("country_is_democratic", *c) for c in self.countries()))
        self.assertTrue(any(self.ev.holds("country_is_communist", *c) for c in self.countries()))

    def test_no_country_is_in_two_camps(self):
        camps = ("country_is_democratic", "country_is_communist", "country_is_fascist")
        problems = []
        for country in self.countries():
            in_camps = [c for c in camps if self.ev.holds(c, *country)]
            if len(in_camps) > 1:
                problems.append(f"{', '.join(in_camps)}: {', '.join(country[0])} left={country[1]} fascists={country[2]}")
        self.assertEqual(problems[:5], [], f"{len(problems)} countries in two camps")

    def test_an_authoritarian_country_is_in_no_camp_besides(self):
        for country in self.countries():
            if self.ev.holds("country_is_authoritarian", *country):
                self.assertFalse(self.ev.holds("country_is_fascist", *country))
                self.assertFalse(self.ev.holds("country_is_communist", *country))


if __name__ == "__main__":
    unittest.main()
