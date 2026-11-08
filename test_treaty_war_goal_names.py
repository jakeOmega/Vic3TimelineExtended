"""Enforce war goals: their names, their modifier headings and Privatization.

Vanilla names the war goal that enforces an article `Enforce [article]`
(war_goal_enforce_treaty_article), so an article whose own name starts with
"Enforce" reads "Enforce Enforce ..." in every war. Its tooltip heads the
article's source modifiers with the holder's name, though the side an enforced
article binds is the war goal's target (vanilla's treaty port: China cedes);
the mod swaps the headings. And Enforce Privatization was pressed on Tahiti,
which has nothing to privatize, by a Britain at war with France (2026-11-08):
its demander test sat only in can_ratify, which a war goal doesn't check, and
the AI had no weight for it. Play-test: docs/testing/treaty-war-goal-playtest.md.
"""
import os
import re
import unittest

from test_seabed_script import block, strip_comments

ROOT = os.path.dirname(os.path.abspath(__file__))
ARTICLES = os.path.join(ROOT, "common", "treaty_articles")
LOC = os.path.join(ROOT, "localization", "english")
OVERRIDE = os.path.join(LOC, "replace", "timeline_extended_override_l_english.yml")
VALUES = os.path.join(ROOT, "common", "script_values", "extra_script_values.txt")

# Articles still named "Enforce ...": each needs a rename (and its concept, guide
# and translations with it). Remove an entry once it is renamed. Emissions
# Reduction, the last, was renamed on 2026-11-08.
STILL_DOUBLED: set[str] = set()

_LOC_LINE = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\d*\s*"(.*)"\s*$')


def read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def english_loc(paths):
    loc = {}
    for path in paths:
        for line in read(path).splitlines():
            m = _LOC_LINE.match(line)
            if m:
                loc[m.group(1)] = m.group(2)
    return loc


def enforceable_articles():
    """{article: its body, comments stripped} for every can_be_enforced article."""
    found = {}
    for name in sorted(os.listdir(ARTICLES)):
        if not name.endswith(".txt"):
            continue
        text = strip_comments(read(os.path.join(ARTICLES, name)))
        for key in re.findall(r"^(\w+) = \{", text, re.M):
            body = block(text, key)
            if "can_be_enforced" in body:
                found[key] = body
    return found


class EnforceWarGoalNameTest(unittest.TestCase):
    def test_no_enforceable_article_is_named_enforce(self):
        files = [os.path.join(LOC, f) for f in sorted(os.listdir(LOC)) if f.endswith(".yml")]
        loc = english_loc(files)
        doubled = {key for key in enforceable_articles()
                   if loc.get(key, "").lower().startswith("enforce ")}
        self.assertEqual(doubled - STILL_DOUBLED, set(),
                         "the war goal would read 'Enforce Enforce ...': name the article with a noun")
        self.assertEqual(STILL_DOUBLED - doubled, set(), "renamed: drop it from STILL_DOUBLED")

    def test_emissions_reduction_concept_follows_the_article(self):
        files = [os.path.join(LOC, f) for f in sorted(os.listdir(LOC)) if f.endswith(".yml")]
        loc = english_loc(files)
        self.assertEqual(loc["concept_emissions_reduction_treaty"], loc["enforce_emissions_reduction"])
        old_links = sorted(k for k, v in loc.items()
                           if re.search(r"Concept\('concept_emissions_reduction_treaty',\s*'[^']*Enforce", v))
        self.assertEqual(old_links, [], "a concept link still shows the old name, Enforce Emissions Reduction")

    def test_headings_name_the_conceding_target_over_the_source_modifiers(self):
        loc = english_loc([OVERRIDE])
        self.assertIn("WarGoal.GetTarget.GetAdjective",
                      loc["ARTICLE_DRAFT_WAR_GOAL_SOURCE_MODIFIERS_TITLE"])
        self.assertIn("WarGoal.GetHolder.GetAdjective",
                      loc["ARTICLE_DRAFT_WAR_GOAL_TARGET_MODIFIERS_TITLE"])


class PrivatizationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = enforceable_articles()["enforce_privatization"]

    def test_possible_requires_a_capitalist_demander(self):
        demander = block(block(self.text, "\tpossible"), "\t\tscope:other_country")
        self.assertIn("law_laissez_faire", demander)
        self.assertIn("law_interventionism", demander)

    def test_ai_weights_need_something_to_privatize(self):
        for field in ("proposal_weight", "wargoal_score_multiplier"):
            self.assertRegex(self.text, rf"{field} = \{{ value = enforce_privatization_ai_demand_weight \}}", field)
        values = read(VALUES)
        for name in ("enforce_privatization_ai_demand_weight", "enforce_privatization_ai_min_levels",
                     "enforce_privatization_state_owned_levels"):
            self.assertRegex(values, rf"(?m)^{name} = ", name)
        weight = values[values.index("enforce_privatization_ai_demand_weight = {"):]
        weight = weight[:weight.index("\n}\n")]
        self.assertIn("enforce_privatization_state_owned_levels >= enforce_privatization_ai_min_levels", weight)
        self.assertIn("law_laissez_faire", weight)


if __name__ == "__main__":
    unittest.main()
