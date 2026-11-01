"""Self-Directed Evolution and Clade Citizenship (era 13 spec § 7.3, § 7.1).

Static checks on the script: the technology's place in the tree and its lines
(the colonies' growth marker, the census's work safety), Clade Citizenship as
the fourth Bodily Autonomy law, the stances (someone must rank it above
Morphological Freedom, or no group could back the step), the heritage parity's
dynamic-modifier shape, its arithmetic on the mod's own citizenship figures,
the once-a-game self-check, and the colonies' growth factor.

Run: python3 test_self_directed_evolution.py
"""
import glob
import os
import re
import subprocess
import sys
import unittest

import ideology_modifications as im

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
from scripts.generators import gen_nation_tab as nation  # noqa: E402
from scripts.generators import gen_solar_sites as gss  # noqa: E402
from scripts.image_pipeline import icon_prompts  # noqa: E402

TECH_DIR = os.path.join(REPO, "common", "technology", "technologies")
ERA_13 = os.path.join(TECH_DIR, "era_13.txt")
LAWS = os.path.join(REPO, "common", "laws", "te_bodily_autonomy_laws.txt")
CITIZENSHIP = os.path.join(REPO, "common", "laws", "modified.txt")
IDEOLOGIES = os.path.join(REPO, "common", "ideologies", "extra_ideologies.txt")
MODIFIED = os.path.join(REPO, "common", "ideologies", "modified.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_bodily_autonomy_effects.txt")
VALUES = os.path.join(REPO, "common", "script_values", "te_bodily_autonomy_values.txt")
MODIFIERS = os.path.join(REPO, "common", "static_modifiers", "te_bodily_autonomy_modifiers.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "te_bodily_autonomy_on_actions.txt")
SR_TYPES = os.path.join(REPO, "common", "modifier_type_definitions", "space_race_modifier_types.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")

HERITAGE = ("country_acceptance_shared_heritage_trait_add", "country_acceptance_shared_heritage_trait_group_add",
            "country_acceptance_no_shared_heritage_trait_add")
PARITY = ("te_clade_parity_trait", "te_clade_parity_group", "te_clade_parity_none")
LIFTS = ("te_clade_lift_trait", "te_clade_lift_group", "te_clade_lift_none")


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


def _loc_keys():
    keys = set()
    for path in glob.glob(os.path.join(LOC_DIR, "*.yml")):
        keys |= set(re.findall(r'(?m)^ ([\w.\-]+):\d* "', _read(path)))
    return keys


def _tech(name):
    for path in glob.glob(os.path.join(TECH_DIR, "era_*.txt")):
        text = _code(_read(path))
        if re.search(rf"(?m)^{re.escape(name)} = \{{", text):
            return _top_level(text, name)
    raise AssertionError(f"no technology {name}")


def _heritage_lines(block):
    """The three heritage figures a block's own lines set or add (0 where it names none)."""
    return tuple(float(m.group(1)) if (m := re.search(rf"\b{key} = (-?[\d.]+)", block)) else 0.0
                 for key in HERITAGE)


class TechnologyTest(unittest.TestCase):
    def setUp(self):
        self.tech = _code(_top_level(_read(ERA_13), "self_directed_evolution"))

    def test_era_category_and_prerequisites(self):
        self.assertRegex(self.tech, r"era = era_13\b")
        self.assertRegex(self.tech, r"category = society\b")
        prereqs = set(_sub(self.tech, "unlocking_technologies").split())
        self.assertEqual(prereqs, {"morphological_freedom", "rejuvenation_therapies"})
        for prereq in prereqs:   # Tech Tree Authoring: prerequisites in the technology's own category
            self.assertRegex(_tech(prereq), r"category = society\b", prereq)

    def test_its_lines_are_the_marker_and_the_census_s_work_safety(self):
        lines = dict(re.findall(r"(?m)^\s*(\w+) = (-?[\d.]+)\s*$", _sub(self.tech, "modifier")))
        self.assertEqual(lines, {gss.GROWTH_MODIFIER: "0.001", "state_work_safety_add": "0.05"})
        for budget in ("country_weekly_innovation_max_add", "_max_investment_add", "mortality"):
            self.assertNotIn(budget, self.tech)

    def test_placeholder_icon_is_tracked_and_queued(self):
        raw = _top_level(_read(ERA_13), "self_directed_evolution")
        texture = re.search(r'texture = "([^"]+)" # Placeholder Icon', raw).group(1)
        subprocess.run(["git", "ls-files", "--error-unmatch", texture], cwd=REPO, check=True, capture_output=True)
        self.assertIsNone(icon_prompts.ICONS["technology"]["self_directed_evolution"]["seed"])


class LawTest(unittest.TestCase):
    def setUp(self):
        self.text = _code(_read(LAWS))
        self.law = _top_level(self.text, "law_clade_citizenship")

    def test_last_in_its_file_at_80_with_the_technology(self):
        self.assertEqual(re.findall(r"(?m)^(law_\w+) = \{", self.text)[-1], "law_clade_citizenship")
        self.assertRegex(self.law, r"group = lawgroup_bodily_autonomy\b")
        self.assertRegex(self.law, r"progressiveness = 80\b")
        self.assertEqual(_sub(self.law, "unlocking_technologies").split(), ["self_directed_evolution"])
        for key in ("unlocking_laws", "disallowing_laws"):
            self.assertNotRegex(self.law, rf"\b{key} = ")

    def test_no_pop_is_worse_off_than_under_morphological_freedom(self):
        """The static line is Morphological Freedom's +10; the parity lifts every figure on top of it."""
        freedom = _sub(_top_level(self.text, "law_morphological_freedom"), "modifier")
        clade = _sub(self.law, "modifier")
        self.assertEqual(_heritage_lines(clade), _heritage_lines(freedom))
        pull = lambda block: float(re.search(r"state_migration_pull_mult = ([\d.]+)", block).group(1))  # noqa: E731
        self.assertGreater(pull(clade), pull(freedom))

    def test_the_tooltip_says_what_the_parity_does(self):
        on_enact = _sub(self.law, "on_enact")
        self.assertIn("custom_tooltip = te_clade_law_parity_tt", on_enact)
        self.assertIn("te_clade_law_parity_tt", _loc_keys())

    def test_placeholder_icon_is_tracked_and_queued(self):
        raw = _top_level(_read(LAWS), "law_clade_citizenship")
        icon = re.search(r'icon = "([^"]+)" # Placeholder Icon', raw).group(1)
        subprocess.run(["git", "ls-files", "--error-unmatch", icon], cwd=REPO, check=True, capture_output=True)
        self.assertIsNone(icon_prompts.ICONS["law"]["law_clade_citizenship"]["seed"])


class StanceTest(unittest.TestCase):
    RANK = {"strongly_disapprove": -2, "disapprove": -1, "neutral": 0, "approve": 1, "strongly_approve": 2}

    @staticmethod
    def _hand_written():
        """{ideology: {law: stance}} for the mod's own ideologies' Bodily Autonomy blocks."""
        text = _read(IDEOLOGIES)
        out = {}
        for m in re.finditer(r"(?m)^(ideology_\w+) = \{", text):
            body = _block_from(text, m.end())
            block = re.search(r"lawgroup_bodily_autonomy = \{([^}]*)\}", body)
            if block:
                out[m.group(1)] = dict(re.findall(r"(law_\w+) = (\w+)", block.group(1)))
        return out

    def test_every_list_and_block_names_clade_citizenship(self):
        for name, stances in im.BODILY_AUTONOMY_LISTS.items():
            with self.subTest(list=name):
                self.assertEqual([law for law, _ in stances][-1], "law_clade_citizenship")
        hand = self._hand_written()
        self.assertEqual(len(hand), 10)
        for ideology, stances in hand.items():
            with self.subTest(ideology=ideology):
                self.assertIn("law_clade_citizenship", stances)

    def test_someone_can_back_the_step_from_morphological_freedom(self):
        """A group backs enacting a law only when it ranks it above the law in force."""
        lists = {name: dict(stances) for name, stances in im.BODILY_AUTONOMY_LISTS.items()}
        everyone = {**{f"list:{k}": v for k, v in lists.items()}, **self._hand_written()}
        backers = [k for k, v in everyone.items()
                   if self.RANK[v["law_clade_citizenship"]] > self.RANK[v["law_morphological_freedom"]]]
        self.assertIn("ideology_optimist_transhumanist", backers)

    def test_the_devout_and_the_cautious_oppose_it_most(self):
        for name in ("traditional", "cautious"):
            self.assertEqual(dict(im.BODILY_AUTONOMY_LISTS[name])["law_clade_citizenship"], "strongly_disapprove")
        for ideology in ("ideology_moralist", "ideology_pious", "ideology_agrarian"):
            stance = dict(im.modifications[ideology]["lawgroup_bodily_autonomy"])["law_clade_citizenship"]
            self.assertEqual(stance, "strongly_disapprove", ideology)

    def test_generated_file_carries_the_fourth_stance(self):
        modified = _read(MODIFIED)
        for ideology in im.BODILY_AUTONOMY_STANCES:
            with self.subTest(ideology=ideology):
                m = re.search(rf"(?m)^(?:REPLACE|INJECT):{ideology} = \{{", modified)
                block = _sub(_block_from(modified, m.end()), "lawgroup_bodily_autonomy")
                self.assertIn("law_clade_citizenship = ", block, "run scripts/generators/regen_ideologies_offline.py")


class ParityScriptTest(unittest.TestCase):
    def setUp(self):
        self.effects = _code(_read(EFFECTS))
        self.refresh = _top_level(self.effects, "te_clade_parity_refresh")
        self.values = _code(_read(VALUES))

    def test_one_refresh_site_on_the_monthly_country_pulse(self):
        on_actions = _code(_read(ON_ACTIONS))
        self.assertIn("te_bodily_autonomy_country_monthly_on_action", _sub(on_actions, "on_monthly_pulse_country"))
        self.assertIn("te_clade_parity_refresh = yes",
                      _top_level(on_actions, "te_bodily_autonomy_country_monthly_on_action"))
        callers = [p for p in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True)
                   if "te_clade_parity_refresh = yes" in _code(_read(p))]
        self.assertEqual([os.path.relpath(p, REPO) for p in callers],
                         [os.path.relpath(ON_ACTIONS, REPO)])

    def test_each_parity_modifier_carries_one_point_of_one_figure(self):
        text = _code(_read(MODIFIERS))
        for name, key in zip(PARITY, HERITAGE):
            with self.subTest(modifier=name):
                lines = re.findall(r"(?m)^\s*(\w+) = (-?[\d.]+)\s*$", _top_level(text, name))
                self.assertEqual(lines, [(key, "1")])

    def test_lifts_are_worked_out_before_any_is_stored(self):
        under_law = _sub(self.refresh, "if")
        self.assertIn("has_law = law_type:law_clade_citizenship", under_law)
        last_local = max(under_law.index(f"value = {lift}_value") for lift in LIFTS)
        first_store = min(under_law.index(f"set_variable = {{ name = {lift} ") for lift in LIFTS)
        self.assertLess(last_local, first_store)
        # removed before re-added, every month: a same-name add_modifier stacks
        last_removal = max(under_law.index(f"remove_modifier_if_exists_effect = {{ MODIFIER = {m} }}") for m in PARITY)
        first_add = min(under_law.index(f"name = {m}") for m in PARITY)
        self.assertLess(last_removal, first_add)
        for name, lift in zip(PARITY, LIFTS):
            self.assertRegex(under_law, rf"name = {name}\s+multiplier = var:{lift}\b")

    def test_without_the_law_the_modifiers_go_before_their_variables(self):
        cleanup = _sub(self.refresh, "else_if")
        last_removal = max(cleanup.index(f"remove_modifier = {m}") for m in PARITY)
        first_variable = min(cleanup.index(f"remove_variable = {lift}") for lift in LIFTS)
        self.assertLess(last_removal, first_variable)

    def test_each_base_nets_out_its_lift_only_while_its_modifier_is_there(self):
        for figure, name, key, lift in zip(("trait", "group", "none"), PARITY, HERITAGE, LIFTS):
            with self.subTest(figure=figure):
                base = _top_level(self.values, f"te_clade_base_{figure}_value")
                self.assertIn(f"value = modifier:{key}", base)
                guard = _sub(base, "if")
                self.assertIn(f"has_modifier = {name}", guard)
                self.assertIn(f"subtract = var:{lift}", guard)

    def test_registered_in_the_nation_tab(self):
        self.assertIn("te_clade_parity_*", nation.SECTIONS["society"])
        for key in HERITAGE:
            self.assertIn(key, nation.TYPE_ROWS["society"]["acceptance"])


class ParityArithmeticTest(unittest.TestCase):
    """The figures the parity works on, from the mod's own files (scripting_best_practices.md,
    "Citizenship Acceptance: Read the Mod's Laws, Not Vanilla's")."""

    CITIZENSHIP_LAWS = ("law_subjecthood", "law_ethnostate", "law_national_supremacy", "law_racial_segregation",
                        "law_cultural_exclusion", "law_multicultural")

    def _by_era_9(self):
        """{law: (shared trait, shared group, none)} under each citizenship law with Civil Rights Movement and Social
        Justice Movements, the two technologies that raise the figures."""
        text = _code(_read(CITIZENSHIP))
        techs = [_heritage_lines(_sub(_tech(t), "modifier"))
                 for t in ("civil_rights_movement", "social_justice_movements")]
        out = {}
        for law in self.CITIZENSHIP_LAWS:
            base = _heritage_lines(_sub(_top_level(text, f"REPLACE:{law}"), "modifier"))
            out[law] = tuple(b + sum(t[i] for t in techs) for i, b in enumerate(base))
        return out

    def test_the_figures_the_law_s_comment_quotes(self):
        self.assertEqual(self._by_era_9(), {
            "law_subjecthood": (20, 25, 20), "law_ethnostate": (40, 30, 10), "law_national_supremacy": (20, 20, 20),
            "law_racial_segregation": (60, 60, 0), "law_cultural_exclusion": (20, 20, 20),
            "law_multicultural": (20, 20, 20)})

    def test_a_flat_bonus_would_rank_no_shared_heritage_first(self):
        """The spec's +20 on no shared heritage alone, under the four inclusive laws."""
        inverted = [law for law, (trait, group, none) in self._by_era_9().items() if none + 20 > max(trait, group)]
        self.assertEqual(len(inverted), 4, inverted)

    def test_the_parity_gives_every_pop_one_figure_and_none_less_than_before(self):
        clade = _heritage_lines(_sub(_top_level(_code(_read(LAWS)), "law_clade_citizenship"), "modifier"))
        for law, figures in self._by_era_9().items():
            with self.subTest(law=law):
                base = tuple(f + c for f, c in zip(figures, clade))   # Morphological Freedom's figures too
                target = max(base)                                    # te_clade_parity_target_value
                lifts = tuple(max(target - b, 0) for b in base)       # te_clade_lift_*_value
                after = tuple(b + lift for b, lift in zip(base, lifts))
                self.assertEqual(len(set(after)), 1)
                for b, a in zip(base, after):
                    self.assertGreaterEqual(a, b)


class SelfCheckTest(unittest.TestCase):
    def test_once_a_game_ok_and_broken(self):
        check = _top_level(_read(EFFECTS), "te_clade_parity_selfcheck")
        self.assertIn("set_global_variable = te_clade_parity_checked", check)
        self.assertIn("TE_SELF_CHECK OK clade_heritage_parity", check)
        self.assertEqual(check.count("TE_SELF_CHECK BROKEN clade_heritage_parity"), 2)
        # armed only when the month's lifts close a gap of at least 1, so OK can't be a false pass
        self.assertIn("te_clade_parity_gap_value >= 1", _code(check))
        self.assertIn("te_clade_parity_selfcheck = yes", _sub(_top_level(_code(_read(EFFECTS)),
                                                                          "te_clade_parity_refresh"), "if"))


class ColonyGrowthTest(unittest.TestCase):
    def test_the_marker_is_script_only_and_the_technology_alone_carries_it(self):
        block = _top_level(_code(_read(SR_TYPES)), gss.GROWTH_MODIFIER)
        self.assertIn("script_only = yes", block)
        self.assertIn("percent = yes", block)
        carriers = []
        for path in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True):
            if "modifier_type_definitions" in path or "script_values" in path:
                continue
            if re.search(rf"\b{gss.GROWTH_MODIFIER} = ", _code(_read(path))):
                carriers.append(os.path.relpath(path, REPO))
        self.assertEqual(carriers, [os.path.relpath(ERA_13, REPO)])

    def test_every_world_s_growth_reads_its_holder_s_marker(self):
        values = _code(_read(os.path.join(REPO, gss.VALUES_OUT)))
        effects = _code(_read(os.path.join(REPO, gss.EFFECTS_OUT)))
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                factor = _top_level(values, f"sr_site_growth_{k}")
                self.assertIn(f"value = {1 + gss.GROWTH_PER_MONTH}", factor)
                self.assertIn(f"global_var:sr_site_holder_{k} = {{ add = modifier:{gss.GROWTH_MODIFIER} }}", factor)
                self.assertIn(f"multiply = sr_site_growth_{k}", _top_level(effects, f"sr_site_monthly_{k}"))


class LocalizationTest(unittest.TestCase):
    def test_names_and_descriptions(self):
        keys = _loc_keys()
        for key in ("self_directed_evolution", "law_clade_citizenship", gss.GROWTH_MODIFIER, *PARITY):
            with self.subTest(key=key):
                self.assertIn(key, keys)
                self.assertIn(f"{key}_desc", keys)
        self.assertIn("je_morphological_freedom_status_clade", keys)


if __name__ == "__main__":
    unittest.main()
