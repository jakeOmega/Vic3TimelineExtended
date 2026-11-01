"""Bodily Autonomy and the Morphological Freedom Debate (era 13 spec § 7.1, § 7.2).

Static checks on the script: the technology's place in the tree, the law
group's default first and seeded at game start, Natural Form neutral for every
ideology (every country holds it for two centuries before anything can replace
it), every stance list naming every law, the debate on the augmentation
debate's pattern (the game rule, the resolved-variable guard for revolutions,
the twenty-year timer and the outcome branches), and the events' pool and art.

Run: python3 test_bodily_autonomy.py
"""
import glob
import os
import re
import unittest

import ideology_modifications as im

REPO = os.path.dirname(os.path.abspath(__file__))
ERA_12 = os.path.join(REPO, "common", "technology", "technologies", "era_12.txt")
LAWS = os.path.join(REPO, "common", "laws", "te_bodily_autonomy_laws.txt")
LAW_GROUPS = os.path.join(REPO, "common", "law_groups", "extra_law_groups.txt")
HISTORY = os.path.join(REPO, "common", "history", "extra_history.txt")
IDEOLOGIES = os.path.join(REPO, "common", "ideologies", "extra_ideologies.txt")
MODIFIED = os.path.join(REPO, "common", "ideologies", "modified.txt")
JE = os.path.join(REPO, "common", "journal_entries", "je_morphological_freedom.txt")
EVENTS = os.path.join(REPO, "events", "morphological_freedom_events.txt")
LAW_CONSISTENCY = os.path.join(REPO, "gen_law_consistency.py")
LOC_DIR = os.path.join(REPO, "localization", "english")

# Clade Citizenship (Self-Directed Evolution, era 13 spec § 7.3) is last: test_self_directed_evolution.py.
LAW_ORDER = ["law_natural_form", "law_licensed_modification", "law_morphological_freedom", "law_clade_citizenship"]
POOLED = [f"morphological_freedom_events.{n}" for n in range(1, 7)]
OUTCOMES = ["morphological_freedom_events.100", "morphological_freedom_events.200"]


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _code(text):
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


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


def _own(block, key):
    """A block one tab in: the entity's own key, not one nested in a desc or an option."""
    m = re.search(rf"(?m)^\t{re.escape(key)} = \{{", block)
    assert m, f"no {key}"
    return _block_from(block, m.end())


def _loc_keys():
    keys = set()
    for path in glob.glob(os.path.join(LOC_DIR, "*.yml")):
        keys |= set(re.findall(r'(?m)^ ([\w.\-]+):\d* "', _read(path)))
    return keys


class TechnologyTest(unittest.TestCase):
    def test_era_category_and_prerequisites(self):
        tech = _code(_top_level(_read(ERA_12), "morphological_freedom"))
        self.assertRegex(tech, r"era = era_12\b")
        self.assertRegex(tech, r"category = society\b")
        prereqs = set(_sub(tech, "unlocking_technologies").split())
        self.assertEqual(prereqs, {"biohacking_and_human_augmentation", "LGBTQ_rights_movement"})

    def test_no_calibrated_budget_lines(self):
        tech = _code(_top_level(_read(ERA_12), "morphological_freedom"))
        for budget in ("country_weekly_innovation_max_add", "_max_investment_add", "mortality"):
            self.assertNotIn(budget, tech)


class LawGroupTest(unittest.TestCase):
    def test_group_is_human_rights(self):
        group = _top_level(_read(LAW_GROUPS), "lawgroup_bodily_autonomy")
        self.assertRegex(group, r"law_group_category = human_rights\b")

    def test_laws_in_order_with_the_default_first(self):
        text = _code(_read(LAWS))
        found = re.findall(r"(?m)^(law_\w+) = \{", text)
        self.assertEqual(found, LAW_ORDER)
        for law in found:
            self.assertRegex(_top_level(text, law), r"group = lawgroup_bodily_autonomy\b")

    def test_natural_form_carries_nothing_and_needs_nothing(self):
        law = _code(_top_level(_read(LAWS), "law_natural_form"))
        for key in ("modifier", "unlocking_technologies", "unlocking_laws", "disallowing_laws"):
            self.assertNotRegex(law, rf"\b{key} = ")

    def test_freer_laws_need_the_technology_and_add_acceptance(self):
        text = _code(_read(LAWS))
        for law, bonus in (("law_licensed_modification", 5), ("law_morphological_freedom", 10)):
            block = _top_level(text, law)
            self.assertEqual(_sub(block, "unlocking_technologies").split(), ["morphological_freedom"])
            self.assertRegex(_sub(block, "modifier"),
                             rf"country_acceptance_no_shared_heritage_trait_add = {bonus}\b")

    def test_seeded_for_every_country_at_game_start(self):
        every = _sub(_top_level(_read(HISTORY), "GLOBAL"), "every_country")
        self.assertIn("activate_law = law_type:law_natural_form", every)

    def test_law_consistency_lists_the_group(self):
        self.assertIn('"lawgroup_bodily_autonomy"', _read(LAW_CONSISTENCY))


class StanceTest(unittest.TestCase):
    def test_every_list_names_every_law_in_order(self):
        for name, stances in im.BODILY_AUTONOMY_LISTS.items():
            with self.subTest(list=name):
                self.assertEqual([law for law, _ in stances], LAW_ORDER)

    def test_natural_form_is_neutral_everywhere(self):
        for name, stances in im.BODILY_AUTONOMY_LISTS.items():
            with self.subTest(list=name):
                self.assertEqual(dict(stances)["law_natural_form"], "neutral")
        # The hand-written blocks and the generated file, too.
        for path in (IDEOLOGIES, MODIFIED):
            for block in re.finditer(r"lawgroup_bodily_autonomy = \{([^}]*)\}", _read(path)):
                with self.subTest(path=os.path.basename(path)):
                    self.assertRegex(block.group(1), r"law_natural_form = neutral\b")

    def test_interest_groups_split_as_designed(self):
        def stance(ideology, law):
            return dict(im.modifications[ideology]["lawgroup_bodily_autonomy"])[law]

        # The Devout and the Rural Folk oppose the freer laws; the Intelligentsia back them.
        for ideology in ("ideology_moralist", "ideology_pious", "ideology_agrarian"):
            self.assertIn(stance(ideology, "law_morphological_freedom"), ("disapprove", "strongly_disapprove"))
        for ideology in ("ideology_liberal", "ideology_liberal_modern", "ideology_anti_clerical"):
            self.assertIn(stance(ideology, "law_morphological_freedom"), ("approve", "strongly_approve"))

    def test_generated_file_carries_the_stances(self):
        modified = _read(MODIFIED)
        for ideology in im.BODILY_AUTONOMY_STANCES:
            with self.subTest(ideology=ideology):
                m = re.search(rf"(?m)^(?:REPLACE|INJECT):{ideology} = \{{", modified)
                self.assertIsNotNone(m, "run scripts/generators/regen_ideologies_offline.py")
                self.assertIn("lawgroup_bodily_autonomy = {", _block_from(modified, m.end()))


class DebateTest(unittest.TestCase):
    def setUp(self):
        self.je = _code(_top_level(_read(JE), "je_morphological_freedom"))

    def test_rule_and_revolution_guards(self):
        shown = _sub(self.je, "is_shown_when_inactive")
        self.assertIn("has_game_rule = social_movements_enabled", shown)
        self.assertIn("has_technology_researched = morphological_freedom", shown)
        self.assertIn("is_revolutionary = no", shown)
        self.assertIn("NOT = { has_variable = morphological_freedom_resolved }", shown)
        possible = _sub(self.je, "possible")
        self.assertIn("NOT = { has_variable = morphological_freedom_resolved }", possible)
        self.assertNotIn("is_revolutionary", possible)

    def test_every_ending_sets_the_resolved_variable(self):
        for block in ("on_complete", "on_timeout"):
            self.assertIn("set_variable = morphological_freedom_resolved", _sub(self.je, block))

    def test_twenty_years_succeeds_on_the_law_fails_on_natural_form(self):
        self.assertRegex(self.je, r"timeout = 7300\b")
        complete = _sub(_sub(self.je, "complete"), "OR")
        self.assertIn("has_law = law_type:law_morphological_freedom", complete)
        self.assertIn("has_law = law_type:law_clade_citizenship", complete)
        self.assertIn("morphological_freedom_events.200", _sub(self.je, "on_complete"))
        timeout = _sub(self.je, "on_timeout")
        failed = _sub(timeout, "if")
        self.assertIn("has_law = law_type:law_natural_form", failed)
        self.assertIn("morphological_freedom_events.100", failed)
        self.assertIn("morphological_freedom_unsettled_modifier", _sub(timeout, "else"))

    def test_pool_names_the_six_events(self):
        pool = _sub(_sub(self.je, "on_monthly_pulse"), "random_events")
        self.assertEqual(re.findall(r"morphological_freedom_events\.\d+", pool), POOLED)

    def test_a_status_line_for_each_law(self):
        status = _sub(self.je, "status_desc")
        for law in LAW_ORDER:
            self.assertIn(f"has_law = law_type:{law}", status)


class EventTest(unittest.TestCase):
    def setUp(self):
        self.text = _code(_read(EVENTS))

    def test_pooled_events_share_the_lockout(self):
        for event in POOLED:
            with self.subTest(event=event):
                block = _top_level(self.text, event)
                self.assertIn("NOT = { has_variable = te_mf_event_recent }", _own(block, "trigger"))
                self.assertIn("set_variable = { name = te_mf_event_recent days = 730 }", _own(block, "immediate"))

    def test_every_event_has_a_picture(self):
        for event in POOLED + OUTCOMES:
            with self.subTest(event=event):
                self.assertRegex(_top_level(self.text, event), r'event_image = \{ texture = "gfx/event_pictures/\w+\.dds" \}')

    def test_loc_for_every_key_the_events_name(self):
        keys = _loc_keys()
        for key in set(re.findall(r"\b(morphological_freedom_events\.\d+\.\w+)", self.text)):
            with self.subTest(key=key):
                self.assertIn(key, keys)

    def test_legal_clinic_events_skip_natural_form(self):
        for event in ("morphological_freedom_events.4", "morphological_freedom_events.6"):
            with self.subTest(event=event):
                trigger = _own(_top_level(self.text, event), "trigger")
                self.assertIn("NOT = { has_law = law_type:law_natural_form }", trigger)


class LocalizationTest(unittest.TestCase):
    def test_names_and_descriptions(self):
        keys = _loc_keys()
        wanted = ["morphological_freedom", "lawgroup_bodily_autonomy", "je_morphological_freedom",
                  "je_morphological_freedom_reason", "je_morphological_freedom_status_natural",
                  "je_morphological_freedom_status_licensed", "je_morphological_freedom_status_free",
                  "je_morphological_freedom_status_clade"]
        wanted += LAW_ORDER
        for key in wanted:
            with self.subTest(key=key):
                self.assertIn(key, keys)
                if not key.startswith("je_morphological_freedom_"):
                    self.assertIn(f"{key}_desc", keys)


if __name__ == "__main__":
    unittest.main()
