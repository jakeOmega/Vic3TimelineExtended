"""Frontier AI Control law group (era 13 spec § 7.1; docs/systems/mod_systems/governance_laws.md).

What the engine would never report:

- A law out of order: the first law in the file is what an unseeded country
  and an old save get, so the pre-AI placeholder must come first.
- A modifier name the engine doesn't know (it drops the line silently), or a
  value that drifts from the table the docs and the player guide quote.
- The group opening without its switch: activate_law ignores
  unlocking_technologies, so nothing moves a country off the placeholder
  unless fix_incompatible_laws does.
- International Oversight kept by a country that left the United Nations.
- Open Weights' world share turning into another sweep of the world inside
  global_tech_spread_script_value, or its tooltip quoting other figures.
- An ideology block that leaves a law out (the group backs it as neutral), or
  stances that no longer give the spec's backers their laws.
- A group without a constraint-free fallback for the consistency walk.

No game install needed.
"""

import glob
import json
import os
import re
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
LAWS = os.path.join(REPO, "common", "laws", "te_frontier_ai_laws.txt")
GROUPS = os.path.join(REPO, "common", "law_groups", "extra_law_groups.txt")
HISTORY = os.path.join(REPO, "common", "history", "extra_history.txt")
EXTRA_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "extra_effects.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_frontier_ai_effects.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "te_frontier_ai_triggers.txt")
VALUES = os.path.join(REPO, "common", "script_values", "te_frontier_ai_values.txt")
EXTRA_VALUES = os.path.join(REPO, "common", "script_values", "extra_script_values.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "te_frontier_ai_on_actions.txt")
UN_LADDER = os.path.join(REPO, "common", "scripted_effects", "un_ladder_effects.txt")
EXTRA_IDEOLOGIES = os.path.join(REPO, "common", "ideologies", "extra_ideologies.txt")
IDEOLOGY_FILES = sorted(glob.glob(os.path.join(REPO, "common", "ideologies", "*.txt")))
VANILLA_IDEOLOGIES = os.path.join(REPO, "vanilla_parsed", "common", "ideologies.json")
ENGINE_MODIFIERS = os.path.join(REPO, "docs", "engine", "modifiers_summary.txt")
MODIFIER_TYPES = os.path.join(REPO, "common", "modifier_type_definitions")
ERA_11 = os.path.join(REPO, "common", "technology", "technologies", "era_11.txt")

GROUP = "lawgroup_frontier_ai_control"
PLACEHOLDER = "law_no_frontier_ai_policy"
# Spec § 7.1's laws, default first, after the pre-AI placeholder: file order.
ORDER = (
    PLACEHOLDER,
    "law_private_ai_labs",
    "law_national_ai_licensing",
    "law_state_ai_monopoly",
    "law_international_ai_oversight",
    "law_open_weights",
)

# The values the docs and the player guide quote (06-politics.md, "Who builds
# frontier AI"; governance_laws.md). As written in the file.
SPEC_LAWS = {
    PLACEHOLDER: {"progressiveness": "0", "modifier": {}},
    "law_private_ai_labs": {
        "progressiveness": "50",
        "modifier": {
            "country_weekly_innovation_mult": "0.1",
            "country_covert_defense_economic_add": "-10",
            "interest_group_ig_industrialists_pol_str_mult": "0.1",
        },
    },
    "law_national_ai_licensing": {
        "progressiveness": "40",
        "modifier": {
            "country_weekly_innovation_mult": "0.05",
            "country_covert_defense_economic_add": "5",
            "country_intelligence_capacity_add": "1",
        },
    },
    "law_state_ai_monopoly": {
        "progressiveness": "25",
        "modifier": {
            "country_weekly_innovation_mult": "-0.05",
            "country_authority_add": "100",
            "country_intelligence_capacity_add": "3",
            "country_covert_defense_economic_add": "10",
            "interest_group_ig_armed_forces_pol_str_mult": "0.1",
        },
    },
    "law_international_ai_oversight": {
        "progressiveness": "65",
        "modifier": {
            "country_weekly_innovation_mult": "0.05",
            "country_diplomatic_reputation_add": "2",
            "country_un_authority_target_add": "0.5",
        },
    },
    "law_open_weights": {
        "progressiveness": "80",
        "modifier": {
            "country_tech_spread_mult": "0.1",
            "country_covert_defense_economic_add": "-10",
            "interest_group_ig_intelligentsia_pop_attraction_mult": "0.1",
        },
    },
}

# Calibrated budgets (scripting_best_practices.md § Calibrated modifier budgets):
# no law here may touch them.
BUDGETED = ("country_weekly_innovation_max_add", "country_tech_research_speed_mult")

# Spec § 7.1's backers, by their interest groups' late-game ideologies.
BACKERS = {
    "law_state_ai_monopoly": ("ideology_jingoist", "ideology_loyalist", "ideology_patriotic"),
    "law_private_ai_labs": ("ideology_plutocratic", "ideology_laissez_faire", "ideology_individualist"),
    "law_open_weights": ("ideology_liberal_modern", "ideology_anti_clerical", "ideology_republican"),
}

# Mod ideologies written by hand in extra_ideologies.txt.
MOD_STANCES = {
    "ideology_environmentalists": "internationalist",
    "ideology_optimist_transhumanist": "accelerationist",
    "ideology_corporate": "market",
    "ideology_custom_religion_aristocratic_governance": "traditional",
    "ideology_custom_religion_technocratic_governance": "technocratic",
    "ideology_custom_religion_republican_governance": "liberal",
    "ideology_custom_religion_corporate_governance": "market",
    "ideology_custom_religion_imperial_cult_governance": "statist",
    "ideology_custom_religion_theocratic_governance": "religious",
}

SCORES = {"strongly_disapprove": -2, "disapprove": -1, "neutral": 0, "approve": 1, "strongly_approve": 2}


def _parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(path, apply_directives=False)
    return parser.data


def _body(node):
    """The parser stores `key = { ... }` as ('=', body); unwrap it."""
    return node[1] if isinstance(node, tuple) else node


def _read(path):
    with open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    """The text of the top-level `name = {` block, braces balanced."""
    match = re.search(r"^%s = \{" % re.escape(name), text, re.M)
    if match is None:
        raise AssertionError("%s not found" % name)
    depth = 0
    for i in range(text.index("{", match.start()), len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : i + 1]
    raise AssertionError("%s is unbalanced" % name)


def _loc():
    keys = {}
    for path in glob.glob(os.path.join(REPO, "localization", "english", "**", "*.yml"), recursive=True):
        for line in _read(path).splitlines():
            match = re.match(r'\s+([A-Za-z0-9_.\-]+):\d*\s+"(.*)"\s*$', line)
            if match:
                keys[match.group(1)] = match.group(2)
    return keys


def _laws():
    return {k: _body(v) for k, v in _parse(LAWS).items()}


class LawsTest(unittest.TestCase):
    def test_group_is_power_structure(self):
        body = _block(_read(GROUPS), GROUP)
        self.assertIn("law_group_category = power_structure", body)

    def test_laws_in_order_placeholder_first(self):
        self.assertEqual(tuple(_laws()), ORDER)
        for law, body in _laws().items():
            self.assertEqual(_body(body["group"]), GROUP, law)

    def test_values_match_the_table(self):
        for law, body in _laws().items():
            spec = SPEC_LAWS[law]
            self.assertEqual(_body(body["progressiveness"]), spec["progressiveness"], law)
            modifier = {k: _body(v) for k, v in _body(body.get("modifier", ("=", {}))).items()}
            self.assertEqual(modifier, spec["modifier"], law)
            for name in BUDGETED:
                self.assertNotIn(name, modifier, law)

    def test_every_modifier_is_known_to_the_engine(self):
        known = set()
        with open(ENGINE_MODIFIERS, encoding="utf-8") as fh:
            for line in fh:
                parts = line.split("|")
                if len(parts) >= 2:
                    known.add(parts[1])
        for path in glob.glob(os.path.join(MODIFIER_TYPES, "*.txt")):
            known.update(re.findall(r"^(\w+) = \{", _read(path), re.M))
        for law, spec in SPEC_LAWS.items():
            for name in spec["modifier"]:
                self.assertIn(name, known, f"{law}: {name}")

    def test_no_negative_authority_add(self):
        """CLAUDE.md: a law that takes authority uses country_authority_cost_add."""
        for law, spec in SPEC_LAWS.items():
            self.assertFalse(spec["modifier"].get("country_authority_add", "0").startswith("-"), law)

    def test_the_real_laws_need_ai_agents(self):
        self.assertIn("ai_agents = {", _read(ERA_11))
        for law, body in _laws().items():
            if law == PLACEHOLDER:
                continue
            self.assertEqual(_body(body["unlocking_technologies"]), ["ai_agents"], law)

    def test_the_placeholder_is_a_constraint_free_fallback(self):
        """gen_law_consistency's terminal fallback: no unlocking_laws, no
        disallowing_laws, no parent, no technology. Re-enactment is closed by
        can_enact, which the generator does not read."""
        placeholder = _laws()[PLACEHOLDER]
        for key in ("unlocking_laws", "disallowing_laws", "parent", "unlocking_technologies"):
            self.assertNotIn(key, placeholder)
        can_enact = _strip_comments(_block(_read(LAWS), PLACEHOLDER))
        self.assertRegex(can_enact, r"NOT = \{ has_technology_researched = ai_agents \}")

        import gen_law_consistency as glc

        laws = glc.parse_laws(glc.load_vanilla()["laws"])
        group = glc.laws_by_group(laws)[GROUP]
        self.assertEqual(sorted(group), sorted(ORDER))
        fallbacks = [
            lid for lid in group
            if not laws[lid]["unlocking_laws"] and not laws[lid]["disallowing_laws"]
            and not laws[lid].get("parent") and not laws[lid].get("unlocking_technologies")
        ]
        self.assertEqual(fallbacks, [PLACEHOLDER])
        self.assertIn(GROUP, glc.LAWGROUP_PRIORITY)

    def test_a_cascade_tries_the_real_laws_before_the_placeholder(self):
        """Every real law has another real law nearer in progressiveness than
        the placeholder, so the walk's candidate order puts it last."""
        prog = {law: int(spec["progressiveness"]) for law, spec in SPEC_LAWS.items()}
        for law in ORDER[1:]:
            nearest = min(abs(prog[law] - prog[other]) for other in ORDER[1:] if other != law)
            self.assertLess(nearest, abs(prog[law] - prog[PLACEHOLDER]), law)

    def test_international_oversight_needs_the_un(self):
        body = _strip_comments(_block(_read(LAWS), "law_international_ai_oversight"))
        self.assertIn("te_frontier_ai_un_member = yes", body[body.index("can_enact"):])
        self.assertIn("has_game_rule = united_nations_enabled", body[body.index("is_visible"):])
        trigger = _strip_comments(_block(_read(TRIGGERS), "te_frontier_ai_un_member"))
        self.assertIn("has_modifier = un_member_modifier", trigger)
        self.assertIn("has_variable = un_member_modifier_on", trigger)

    def test_loc(self):
        loc = _loc()
        for key in (GROUP, f"{GROUP}_desc", *ORDER, *(f"{law}_desc" for law in ORDER),
                    "law_no_frontier_ai_policy_closed_tt", "law_international_ai_oversight_needs_un_tt",
                    "law_international_ai_oversight_falls_tt", "law_open_weights_world_spread_tt",
                    "un_leave_drops_international_ai_oversight_tt"):
            self.assertIn(key, loc)
        names = {law: loc[law] for law in ORDER[1:]}
        self.assertEqual(names, {
            "law_private_ai_labs": "Private Labs",
            "law_national_ai_licensing": "National Licensing",
            "law_state_ai_monopoly": "State Monopoly",
            "law_international_ai_oversight": "International Oversight",
            "law_open_weights": "Open Weights",
        })


class OpeningTest(unittest.TestCase):
    def test_history_seeds_the_placeholder(self):
        text = _strip_comments(_read(HISTORY))
        every = text[text.index("every_country = {"):]
        self.assertIn(f"activate_law = law_type:{PLACEHOLDER}", every[:every.index("c:FRA")])

    def test_fix_incompatible_laws_runs_the_switch(self):
        self.assertIn("te_frontier_ai_fix_law = yes", _strip_comments(_block(_read(EXTRA_EFFECTS), "fix_incompatible_laws")))
        body = _strip_comments(_block(_read(EFFECTS), "te_frontier_ai_fix_law"))
        self.assertRegex(body, r"has_law = law_type:law_no_frontier_ai_policy\s+has_technology_researched = ai_agents"
                         r"\s+\}\s+activate_law = law_type:law_private_ai_labs")
        self.assertRegex(body, r"has_law = law_type:law_international_ai_oversight\s+NOT = \{ te_frontier_ai_un_member = yes \}"
                         r"\s+\}\s+activate_law = law_type:law_national_ai_licensing")

    def test_leaving_the_un_drops_oversight_and_says_so(self):
        ladder = _strip_comments(_read(UN_LADDER))
        self.assertIn("te_frontier_ai_on_un_membership_end = yes", _block(ladder, "un_membership_end_effect"))
        leave = _block(ladder, "un_leave_organisation")
        line = leave.index("un_leave_drops_international_ai_oversight_tt")
        self.assertLess(line, leave.index('text = "UN_LEAVE_DESC"'), "the line must sit outside the hiding tooltip")
        body = _strip_comments(_block(_read(EFFECTS), "te_frontier_ai_on_un_membership_end"))
        self.assertIn("activate_law = law_type:law_national_ai_licensing", body)


class OpenWeightsTest(unittest.TestCase):
    def test_the_spread_is_a_read_of_the_monthly_count(self):
        value = _strip_comments(_block(_read(VALUES), "te_frontier_ai_open_weights_spread"))
        self.assertIn("global_var:te_frontier_ai_open_weights_count", value)
        self.assertNotRegex(value, r"\b(every|any|ordered|random)_country\b")
        self.assertIn("multiply = 100", value)
        self.assertIn("max = 300", value)
        total = _strip_comments(_block(_read(EXTRA_VALUES), "global_tech_spread_script_value"))
        self.assertIn("add = te_frontier_ai_open_weights_spread", total)

    def test_the_count_runs_once_a_month_for_the_world(self):
        on_actions = _strip_comments(_read(ON_ACTIONS))
        self.assertIn("te_frontier_ai_monthly_on_action", _block(on_actions, "on_monthly_pulse"))
        self.assertIn("te_frontier_ai_refresh_open_weights_count = yes", _block(on_actions, "te_frontier_ai_monthly_on_action"))
        count = _strip_comments(_block(_read(EFFECTS), "te_frontier_ai_refresh_open_weights_count"))
        self.assertIn("has_law = law_type:law_open_weights", count)
        self.assertIn("country_rank >= rank_value:major_power", count)

    def test_the_tooltip_quotes_the_figures(self):
        text = _loc()["law_open_weights_world_spread_tt"]
        self.assertIn("+100", text)
        self.assertIn("+300", text)
        self.assertIn("law_open_weights_world_spread_tt", _block(_read(LAWS), "law_open_weights"))


class StancesTest(unittest.TestCase):
    def test_lists_name_all_six_laws_placeholder_neutral(self):
        import ideology_modifications as im
        for name, stances in im.FRONTIER_AI_LISTS.items():
            self.assertEqual(tuple(law for law, _ in stances), ORDER, name)
            self.assertEqual(stances[0], (PLACEHOLDER, "neutral"), name)

    def test_vanilla_keys_exist_and_carry_their_lists(self):
        import ideology_modifications as im
        with open(VANILLA_IDEOLOGIES, encoding="utf-8") as fh:
            vanilla = set(json.load(fh))
        self.assertLessEqual(set(im.FRONTIER_AI_STANCES), vanilla)
        for ideology, name in im.FRONTIER_AI_STANCES.items():
            self.assertEqual(im.modifications[ideology][GROUP], im.FRONTIER_AI_LISTS[name], ideology)

    def test_every_block_in_script_names_all_six(self):
        seen = set()
        for path in IDEOLOGY_FILES:
            for key, node in _parse(path).items():
                body = _body(node)
                if isinstance(body, dict) and GROUP in body:
                    self.assertEqual(set(_body(body[GROUP])), set(ORDER), key)
                    seen.add(key.split(":")[-1])
        import ideology_modifications as im
        self.assertLessEqual(set(im.FRONTIER_AI_STANCES) | set(MOD_STANCES), seen)

    def test_mod_ideologies_use_their_lists(self):
        import ideology_modifications as im
        data = _parse(EXTRA_IDEOLOGIES)
        for ideology, name in MOD_STANCES.items():
            block = {k: _body(v) for k, v in _body(_body(data[ideology])[GROUP]).items()}
            self.assertEqual(block, dict(im.FRONTIER_AI_LISTS[name]), ideology)

    def test_the_spec_backers_peak_at_their_laws(self):
        """Summed over an interest group's three ideologies, its own law scores
        highest: the Armed Forces' State Monopoly, the Industrialists' Private
        Labs, the Intelligentsia's Open Weights."""
        import ideology_modifications as im
        for law, ideologies in BACKERS.items():
            totals = {other: 0 for other in ORDER[1:]}
            for ideology in ideologies:
                for other, stance in im.modifications[ideology][GROUP]:
                    if other in totals:
                        totals[other] += SCORES[stance]
            best = max(totals.values())
            self.assertEqual([k for k, v in totals.items() if v == best], [law], (law, totals))


if __name__ == "__main__":
    unittest.main()
