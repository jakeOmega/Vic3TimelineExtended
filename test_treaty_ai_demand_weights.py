"""Enforceable treaty articles: each tells the AI when a demand buys nothing.

An article with `flags = { can_be_enforced }` can be pressed by the AI as an
enforce war goal, and with no wargoal_score_multiplier (and proposal_weight, for
a treaty) nothing tells it that the demand is worthless against a particular
country: India pressed a Nuclear Program Freeze on Mekong, which could never
build (2026-10-16), and Britain Privatization on Tahiti, which owns no state
industry (2026-11-08). So every enforceable article in common/treaty_articles/
carries both fields, or a `# REVIEWED YYYY-MM-DD (ai_demand_weight): rationale`
comment inside its ai block saying why it needs neither (its worth doesn't
depend on the conceding country, or `possible` already holds it). A tag on an
article that has the fields, or that isn't enforceable, is stale and fails.

And a war goal checks an article's `possible`, not its `can_ratify`, so a test
of who may demand it must sit in `possible`, read one way round (ROOT the
conceding source, scope:other_country the demander).

docs/guides/scripting_best_practices.md, "proposal_weight and
wargoal_score_multiplier"; play-test: docs/testing/treaty-war-goal-playtest.md.
"""
import os
import re
import unittest

from test_seabed_script import english_loc, strip_comments

ROOT = os.path.dirname(os.path.abspath(__file__))
ARTICLES = os.path.join(ROOT, "common", "treaty_articles")
VALUES = os.path.join(ROOT, "common", "script_values", "extra_script_values.txt")
TRIGGERS = os.path.join(ROOT, "common", "scripted_triggers", "te_treaty_ai_demand_triggers.txt")

TAG = re.compile(r"#\s*REVIEWED \d{4}-\d{2}-\d{2} \(ai_demand_weight\):\s*\S")

# Articles whose two fields read one named weight. Each weight starts at 0 and
# has no bare `else`, so whatever fails its gates keeps the 0.
WEIGHTS = {
    "nuclear_program_pause": "nuclear_program_pause_ai_demand_weight",
    "nuclear_disarmament": "nuclear_disarmament_ai_demand_weight",
    "enforce_privatization": "enforce_privatization_ai_demand_weight",
    "seize_company": "seize_company_ai_demand_weight",
    "disband_company": "disband_company_ai_demand_weight",
    "minority_protection": "minority_protection_ai_demand_weight",
    "free_port_concession": "free_port_concession_ai_demand_weight",
    "religious_mission_rights": "religious_mission_rights_ai_demand_weight",
    "demilitarized_zone": "demilitarized_zone_ai_demand_weight",
    "forced_disarmament": "forced_disarmament_ai_demand_weight",
    "enforce_emissions_reduction": "enforce_emissions_reduction_ai_demand_weight",
    "imposed_currency_peg": "imposed_currency_peg_ai_demand_weight",
    "debt_receivership": "debt_receivership_ai_demand_weight",
}

# Articles that name an input: the weight reads the chosen one and, when none is
# bound yet, walks every one the source could name, through the trigger.
INPUT_WEIGHTS = {
    "seize_company": ("input_company", "any_company", "te_treaty_ai_company_worth_demanding"),
    "disband_company": ("input_company", "any_company", "te_treaty_ai_company_worth_demanding"),
    "minority_protection": ("input_state", "any_scope_state", "te_minority_protection_state_worth"),
    "free_port_concession": ("input_state", "any_scope_state", "te_free_port_state_worth"),
    "religious_mission_rights": ("input_state", "any_scope_state", "te_religious_mission_state_worth"),
    "demilitarized_zone": ("input_state", "any_scope_state", "te_demilitarized_zone_state_worth"),
}


def read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def body_span(text, opening):
    """(start, end) of the body after the `{` that ends match `opening`."""
    depth = 0
    for j in range(opening.end() - 1, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return opening.end(), j
    raise AssertionError(f"unclosed block at {opening.group(0)!r}")


def block(text, header):
    """The body of the first `header = { ... }` at the start of a line."""
    m = re.search(rf"(?m)^{header} = \{{", text)
    assert m, f"no {header!r}"
    start, end = body_span(text, m)
    return text[start:end]


def treaty_articles():
    """{name: (file, body without comments, raw ai block or "")}.

    strip_comments keeps every line, so a line range found in the stripped
    text picks the same lines out of the raw one, comments and all.
    """
    found = {}
    for fname in sorted(os.listdir(ARTICLES)):
        if not fname.endswith(".txt"):
            continue
        raw = read(os.path.join(ARTICLES, fname))
        text = strip_comments(raw)
        lines = raw.split("\n")
        for m in re.finditer(r"(?m)^(\w+) = \{", text):
            start, end = body_span(text, m)
            body = text[start:end]
            ai = re.search(r"(?m)^\tai = \{", body)
            raw_ai = ""
            if ai:
                a0, a1 = body_span(body, ai)
                first = text.count("\n", 0, start + ai.start())
                last = text.count("\n", 0, start + a1)
                raw_ai = "\n".join(lines[first:last + 1])
            found[m.group(1)] = (fname, body, raw_ai)
    return found


def is_enforceable(body):
    flags = re.search(r"(?m)^\tflags = \{([^}]*)\}", body)
    return bool(flags and re.search(r"\bcan_be_enforced\b", flags.group(1)))


def ai_fields(raw_ai):
    ai = strip_comments(raw_ai)
    return (re.search(r"(?m)^\t\tproposal_weight = ", ai) is not None,
            re.search(r"(?m)^\t\twargoal_score_multiplier = ", ai) is not None)


class EveryEnforceableArticleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = treaty_articles()

    def test_the_roster_is_found(self):
        enforceable = {n for n, (_, body, _) in self.articles.items() if is_enforceable(body)}
        # A few known ones, so a parsing slip that finds none can't pass.
        for name in ("money_transfer", "seize_company", "population_transfer", "te_cede_colony",
                     "te_seabed_lease_pacific", "surrender_monument"):
            self.assertIn(name, enforceable)
        for name in ("excavation_permit", "nuclear_basing", "grid_interconnection_agreement",
                     "nuclear_arms_limitation"):
            self.assertIn(name, self.articles)
            self.assertNotIn(name, enforceable)

    def test_each_weighs_the_demand_or_says_why_not(self):
        problems = []
        for name, (fname, body, raw_ai) in sorted(self.articles.items()):
            weight, wargoal = ai_fields(raw_ai)
            tagged = bool(TAG.search(raw_ai))
            where = f"{fname}: {name}"
            if not is_enforceable(body):
                if tagged:
                    problems.append(f"{where}: ai_demand_weight tag on an article that can't be enforced")
                continue
            if weight != wargoal:
                problems.append(f"{where}: has only one of proposal_weight and wargoal_score_multiplier")
            elif weight and tagged:
                problems.append(f"{where}: stale ai_demand_weight tag, the article has both fields")
            elif not weight and not tagged:
                problems.append(f"{where}: enforceable with neither proposal_weight nor "
                                "wargoal_score_multiplier, and no `# REVIEWED YYYY-MM-DD "
                                "(ai_demand_weight): ...` in its ai block")
        self.assertEqual(problems, [])


class NamedWeightTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = treaty_articles()
        cls.values = strip_comments(read(VALUES))
        cls.triggers = strip_comments(read(TRIGGERS))

    def test_both_fields_read_the_weight(self):
        for article, weight in WEIGHTS.items():
            ai = strip_comments(self.articles[article][2])
            for field in ("proposal_weight", "wargoal_score_multiplier"):
                self.assertTrue(f"{field} = {{ value = {weight} }}" in ai, f"{article} {field}")

    def test_a_weight_is_zero_unless_its_gates_pass(self):
        for weight in WEIGHTS.values():
            body = block(self.values, weight)
            self.assertTrue(body.strip().startswith("value = 0"), weight)
            self.assertNotRegex(body, r"\belse = \{", weight)
            self.assertIn("value = 1", body, weight)
            self.assertIn("scope:source_country", body, weight)

    def test_an_input_article_reads_the_chosen_input(self):
        for article, (link, walk, trigger) in INPUT_WEIGHTS.items():
            body = block(self.values, WEIGHTS[article])
            self.assertIn(f"scope:article ?= {{ exists = {link} }}", body, article)
            self.assertIn(f"scope:article.{link} = {{ {trigger} = yes }}", " ".join(body.split()), article)
            # No input bound yet: anything the source could name will do.
            fallback = body[body.index("else_if = {"):]
            self.assertIn("scope:source_country", fallback, article)
            self.assertIn(walk, fallback, article)
            self.assertIn(f"{trigger} = yes", fallback, article)
            self.assertRegex(self.triggers, rf"(?m)^{trigger} = \{{", trigger)

    def test_thresholds_are_named_literals(self):
        for name in ("company_article_ai_min_levels", "free_port_concession_ai_min_state_gdp",
                     "forced_disarmament_ai_min_units", "enforce_emissions_reduction_ai_min_share_pct"):
            self.assertRegex(self.values, rf"(?m)^{name} = \d+\s*$", name)

    def test_seize_needs_a_company_the_receiver_lacks(self):
        body = " ".join(block(self.values, "seize_company_ai_demand_weight").split())
        self.assertIn("scope:target_country = { NOT = { has_company = scope:article.input_company.type } }", body)


class PossibleHoldsTheDemanderTest(unittest.TestCase):
    """A war goal checks possible, not can_ratify: each test of the demander
    sits in possible on scope:other_country, and stays in can_ratify (named
    scopes, and the tooltip the treaty designer shows)."""

    BLOC = {
        "minority_protection": ("minority_protection_protector_bloc_possible_tt",
                                ("identity:identity_cultural", "identity:identity_religious")),
        "religious_mission_rights": ("religious_mission_rights_missionary_bloc_possible_tt",
                                     ("identity:identity_religious",)),
    }

    @classmethod
    def setUpClass(cls):
        cls.articles = treaty_articles()
        cls.loc = english_loc()

    def possible(self, article):
        return block(self.articles[article][1], "\tpossible")

    def test_the_protector_and_missionary_blocs(self):
        for article, (tooltip, identities) in self.BLOC.items():
            possible = self.possible(article)
            tip = block(possible, "\t\tcustom_tooltip")
            self.assertIn(f"text = {tooltip}", tip, article)
            demander = block(tip, "\t\t\tscope:other_country")
            self.assertIn("is_in_power_bloc = yes", demander, article)
            for identity in identities:
                self.assertIn(identity, demander, article)
                self.assertIn(identity, block(self.articles[article][1], "\tcan_ratify"), article)
            # possible binds no target_country, so its tooltip names nobody.
            self.assertRegex(self.loc, rf'(?m)^ {tooltip}:0 "[^"\[]*\[concept_power_bloc\]', tooltip)
            self.assertNotIn(f"{tooltip}:0 \"[SCOPE", self.loc)

    def test_the_sponsor_can_dig(self):
        possible = " ".join(self.possible("archaeological_concession").split())
        self.assertIn("text = gm_arch_article_sponsor_tech_concession_tt "
                      "scope:other_country = { gm_arch_method_antiquarian_ok = yes }", possible)

    def test_seize_offers_no_company_the_receiver_has(self):
        valid = " ".join(block(self.articles["seize_company"][1], "\tcompany_valid_trigger").split())
        # Read as passing when scope:other_country is unbound, so a pass with no
        # partner still lists the source's companies.
        self.assertIn("NOT = { scope:other_country ?= { has_company = scope:input.type } }", valid)
        self.assertIn("scope:input = { owner = root }", valid)


if __name__ == "__main__":
    unittest.main()
