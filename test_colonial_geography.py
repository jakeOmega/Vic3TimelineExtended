# -*- coding: utf-8 -*-
"""The colony test's geography: the separation cache and its sea crossings.

A colony is separated from its ruler (UN Resolution 1541, Principle IV): not
joined to our capital over land through states we own, a strait joining two
states only when both are homelands of our primary cultures
(docs/superpowers/specs/2026-10-24-colonial-criteria-and-independence-wars-design.md
§ 1.4). The engine's answer is cached monthly by a ring fill
(common/scripted_effects/colonial_geography_effects.txt), whose tests and
strait list live in common/scripted_triggers/colonial_geography_triggers.txt.

Pinned here: the strait list matches the map's sea crossings, the fill gives
the same answer whether or not the engine's neighbour iterator crosses a
strait (unverified in game), the cache is refreshed monthly and at game
start, and only the Continental Union HQ still reads the old macro-region
test.
"""

import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _read(*parts):
    return re.sub(r"#[^\n]*", "", _raw(*parts))


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def _block(text, name, start=0):
    m = re.compile(r"(?<![\w.:$])" + re.escape(name) + r"\s*=\s*\{").search(text, start)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


ADJACENCY = json.loads(_raw("scripts", "analysis", "demographics_state_adjacency.json"))
LAND = ADJACENCY["land"]
STRAIT_PAIRS = {frozenset((a, b)) for a, bs in ADJACENCY["strait"].items() for b in bs}
GEO_TRIGGERS = _read("common", "scripted_triggers", "colonial_geography_triggers.txt")
GEO_EFFECTS = _read("common", "scripted_effects", "colonial_geography_effects.txt")
GEO_ON_ACTIONS = _read("common", "on_actions", "colonial_geography_on_actions.txt")
TRIGGERS = _read("common", "scripted_triggers", "colonial_empire_triggers.txt")


def _fill(owned, capital, homelands, iterator_crosses_straits):
    """The script's fill (ce_refresh_separation), in Python. Returns the separated states."""
    def neighbours(state):
        found = set(LAND.get(state, ()))
        if iterator_crosses_straits:
            found |= {s for pair in STRAIT_PAIRS if state in pair for s in pair if s != state}
        return found

    def strait_partners(state):
        return {s for pair in STRAIT_PAIRS if state in pair for s in pair if s != state}

    linked = {capital}
    grew = True
    while grew:
        grew = False
        for x in sorted(owned - linked):
            link = False
            for n in neighbours(x):
                if n not in owned or n not in linked:
                    continue
                # ce_fill_land_link: a crossing the iterator returns joins only two homelands.
                if frozenset((n, x)) in STRAIT_PAIRS and not (n in homelands and x in homelands):
                    continue
                link = True
            # ce_fill_homeland_strait: the fill's own crossing between two homelands.
            if not link and x in homelands:
                link = any(p in owned and p in linked and p in homelands for p in strait_partners(x))
            if link:
                linked.add(x)
                grew = True
    return owned - linked


class StraitListTests(unittest.TestCase):
    def test_endpoints_match_the_map(self):
        listed = set(re.findall(r"state_region = s:(STATE_\w+)", _block(GEO_TRIGGERS, "ce_is_strait_endpoint")))
        self.assertEqual(listed, {s for pair in STRAIT_PAIRS for s in pair})

    def test_pairs_match_the_map_in_both_directions(self):
        body = _block(GEO_TRIGGERS, "ce_strait_pair_with_other")
        found = re.findall(r"AND = \{ state_region = s:(STATE_\w+) scope:ce_strait_other = \{ state_region = s:(STATE_\w+) \} \}",
                           body)
        directed = set(found)
        self.assertEqual(len(found), len(directed), "a crossing is listed twice")
        self.assertEqual({frozenset(p) for p in directed}, STRAIT_PAIRS)
        for a, b in directed:
            with self.subTest(pair=(a, b)):
                self.assertIn((b, a), directed)

    def test_no_crossing_is_also_a_land_border(self):
        # ce_fill_land_link refuses a crossing between two non-homelands; a pair that
        # is also a land border would lose its land link too.
        for pair in STRAIT_PAIRS:
            a, b = sorted(pair)
            with self.subTest(pair=(a, b)):
                self.assertNotIn(b, LAND.get(a, ()))
                self.assertNotIn(a, LAND.get(b, ()))


class FillModelTests(unittest.TestCase):
    """The rule's verdicts, and that they hold whichever way the iterator works."""

    CASES = {
        # Spain with the Rif: Gibraltar does not carry the fill into Morocco.
        "spain": ({"STATE_NEW_CASTILE", "STATE_UPPER_ANDALUSIA", "STATE_LOWER_ANDALUSIA", "STATE_MURCIA",
                   "STATE_AL_RIF", "STATE_FEZ"},
                  "STATE_NEW_CASTILE",
                  {"STATE_NEW_CASTILE", "STATE_UPPER_ANDALUSIA", "STATE_LOWER_ANDALUSIA", "STATE_MURCIA"},
                  {"STATE_AL_RIF", "STATE_FEZ"}),
        # Japan with Korea, Ryukyu and Sakhalin: Kyushu, Shikoku and Hokkaido are
        # reached across their straits; Ryukyu and Sakhalin are not.
        "japan": ({"STATE_KANTO", "STATE_TOHOKU", "STATE_HOKUSHINETSU", "STATE_TOKAI", "STATE_KANSAI", "STATE_KYOTO",
                   "STATE_CHUGOKU", "STATE_SHIKOKU", "STATE_KYUSHU", "STATE_HOKKAIDO", "STATE_RYUKYU_ISLANDS",
                   "STATE_SAKHALIN", "STATE_SEOUL", "STATE_BUSAN"},
                  "STATE_KANTO",
                  {"STATE_KANTO", "STATE_TOHOKU", "STATE_HOKUSHINETSU", "STATE_TOKAI", "STATE_KANSAI", "STATE_KYOTO",
                   "STATE_CHUGOKU", "STATE_SHIKOKU", "STATE_KYUSHU", "STATE_HOKKAIDO"},
                  {"STATE_RYUKYU_ISLANDS", "STATE_SAKHALIN", "STATE_SEOUL", "STATE_BUSAN"}),
        # Denmark from Zealand: Jutland and Scania across their straits; Iceland apart.
        "denmark": ({"STATE_ZEALAND", "STATE_JUTLAND", "STATE_SCHLESWIG_HOLSTEIN", "STATE_ICELAND"},
                    "STATE_ZEALAND",
                    {"STATE_ZEALAND", "STATE_JUTLAND", "STATE_SCHLESWIG_HOLSTEIN"},
                    {"STATE_ICELAND"}),
        # Britain with Ireland: the North Channel joins Ulster only if it were a homeland.
        "britain": ({"STATE_HOME_COUNTIES", "STATE_EAST_ANGLIA", "STATE_MIDLANDS", "STATE_WEST_COUNTRY",
                     "STATE_LANCASHIRE", "STATE_YORKSHIRE", "STATE_LOWLANDS", "STATE_HIGHLANDS", "STATE_WALES",
                     "STATE_ULSTER", "STATE_LEINSTER", "STATE_MUNSTER", "STATE_CONNAUGHT", "STATE_MALTA"},
                    "STATE_HOME_COUNTIES",
                    {"STATE_HOME_COUNTIES", "STATE_EAST_ANGLIA", "STATE_MIDLANDS", "STATE_WEST_COUNTRY",
                     "STATE_LANCASHIRE", "STATE_YORKSHIRE", "STATE_LOWLANDS", "STATE_HIGHLANDS", "STATE_WALES"},
                    {"STATE_ULSTER", "STATE_LEINSTER", "STATE_MUNSTER", "STATE_CONNAUGHT", "STATE_MALTA"}),
        # The Ottomans across the Bosporus: Anatolia and the Levant stay contiguous.
        "ottomans": ({"STATE_EASTERN_THRACE", "STATE_HUDAVENDIGAR", "STATE_CRETE"},
                     "STATE_EASTERN_THRACE",
                     {"STATE_EASTERN_THRACE", "STATE_HUDAVENDIGAR"},
                     {"STATE_CRETE"}),
    }

    def test_the_cases(self):
        for name, (owned, capital, homelands, separated) in self.CASES.items():
            for crosses in (False, True):
                with self.subTest(case=name, iterator_crosses_straits=crosses):
                    self.assertEqual(_fill(owned, capital, homelands, crosses), separated)

    def test_a_non_homeland_strait_never_links(self):
        # Every crossing with a non-homeland end, under both readings of the iterator.
        for pair in STRAIT_PAIRS:
            a, b = sorted(pair)
            for crosses in (False, True):
                with self.subTest(pair=(a, b), iterator_crosses_straits=crosses):
                    self.assertEqual(_fill({a, b}, a, {a}, crosses), {b})
                    self.assertEqual(_fill({a, b}, a, {a, b}, crosses), set())


class ScriptShapeTests(unittest.TestCase):
    def test_the_fill_reads_the_two_link_tests(self):
        fill = _block(GEO_EFFECTS, "ce_refresh_separation")
        self.assertIn("ce_fill_land_link = yes", fill)
        self.assertIn("ce_fill_homeland_strait = yes", fill)
        self.assertIn("ce_is_strait_endpoint = yes", fill)
        self.assertIn("set_variable = { name = ce_separated value = scope:ce_fill_country }", fill)
        self.assertIn("set_variable = { name = ce_subject_separated value = scope:ce_fill_country }", fill)
        self.assertIn("set_variable = ce_separation_cached", fill)
        # A neighbour we have lost keeps last month's mark; the owner test refuses it.
        self.assertRegex(fill, r"any_neighbouring_state = \{\s*owner = scope:ce_fill_country\s*"
                               r"var:ce_linked \?= scope:ce_fill_country")

    def test_monthly_and_at_game_start(self):
        self.assertIn("colonial_geography_on_action", _block(GEO_ON_ACTIONS, "on_monthly_pulse_country"))
        self.assertIn("colonial_geography_game_start_on_action", _block(GEO_ON_ACTIONS, "on_game_started"))
        self.assertIn("ce_separation_step = yes", _block(GEO_ON_ACTIONS, "colonial_geography_on_action"))
        start = _block(GEO_ON_ACTIONS, "colonial_geography_game_start_on_action")
        self.assertRegex(start, r"every_country = \{\s*ce_separation_step = yes\s*\}")
        step = _block(GEO_EFFECTS, "ce_separation_step")
        self.assertIn("ce_needs_separation = yes", step)
        self.assertIn("set_variable = ce_separation_cached", step)

    def test_the_tests_read_the_cache(self):
        self.assertIn("var:ce_separated ?= scope:ce_sep_owner", _block(TRIGGERS, "is_separated_from_capital"))
        self.assertIn("var:ce_subject_separated ?= scope:ce_overlord_ref",
                      _block(TRIGGERS, "is_qualifying_colonial_subject"))
        self.assertIn("shares_heritage_trait_with_any_primary_culture",
                      _block(TRIGGERS, "is_qualifying_colonial_subject"))
        self.assertNotIn("shares_heritage_trait_group", _block(TRIGGERS, "is_qualifying_colonial_subject"))

    def test_the_voluntary_end_waits_for_the_cache(self):
        je = _read("common", "journal_entries", "je_colonial_empire.txt")
        fail = _block(je, "fail")
        self.assertRegex(fail, r"je_colonial_empire_voluntary_fail_tt\s*has_variable = ce_separation_cached")

    def test_only_the_wonder_reads_the_macro_regions(self):
        callers = []
        for root in ("common", "events"):
            for dirpath, _, files in os.walk(os.path.join(REPO, root)):
                for name in files:
                    if not name.endswith(".txt"):
                        continue
                    path = os.path.join(dirpath, name)
                    text = re.sub(r"#[^\n]*", "", open(path, encoding="utf-8-sig").read())
                    if re.search(r"\bis_overseas_from_capital\s*=\s*(yes|no)\b", text):
                        callers.append(os.path.relpath(path, REPO).replace(os.sep, "/"))
        self.assertEqual(callers, ["common/buildings/wonders.txt"])
        self.assertNotIn("is_overseas_from_overlord_capital", TRIGGERS)


if __name__ == "__main__":
    unittest.main()
