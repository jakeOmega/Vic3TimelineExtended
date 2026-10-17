"""Judiciary law group (docs/superpowers/specs/2026-10-17-judiciary-design.md).

What the engine would never report:

- A law whose values drift from the spec, or a law out of order: the first law
  in the file is what an unseeded country and an old save get.
- A rule a player plans around that the law's tooltip doesn't show: every one
  is a display line on the law (a script_only modifier type) that script reads.
- An ideology with a Judiciary block that leaves a law out: the group backs the
  law it omits as if neutral.
- A second writer of a scaled modifier, or a multiplier applied where ROOT is
  not the country (the engine substitutes 1.0 silently).
- A Forceful Legislation option that spends the score without saying so.

No game install needed.
"""

import glob
import json
import os
import re
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
LAWS = os.path.join(REPO, "common", "laws", "te_judiciary_laws.txt")
INJECTIONS = os.path.join(REPO, "common", "laws", "te_judiciary_law_injections.txt")
EXTRA_LAWS = os.path.join(REPO, "common", "laws", "extra_laws.txt")
GROUPS = os.path.join(REPO, "common", "law_groups", "extra_law_groups.txt")
TYPES = os.path.join(REPO, "common", "modifier_type_definitions", "judiciary_modifier_types.txt")

COURT_LAWS = (
    "law_executive_tribunals",
    "law_religious_courts",
    "law_statutory_courts",
    "law_constitutional_review",
    "law_judicial_supremacy",
    "law_algorithmic_jurisprudence",
)
PAPER_COURT_LAWS = (
    "law_autocracy",
    "law_bakufu",
    "law_neo_absolutism",
    "law_single_party_state",
    "law_algorithmic_governance",
)
DISPLAY_TYPES = (
    "country_judicial_independence_ceiling_add",
    "country_judicial_independence_ceiling_mult",
    "country_court_challenges_ignored_bool",
    "country_constitutional_law_enactment_success_add",
    "country_rights_law_enactment_success_add",
    "country_legitimacy_from_votes_if_elected_add",
    "country_authority_if_unelected_add",
    "country_override_with_algorithmic_governance_add",
)

# Spec § 2 and § 2.7. Values as written in the file.
SPEC_LAWS = {
    "law_executive_tribunals": {
        "progressiveness": "-50",
        "tech": [],
        "modifier": {
            "country_judicial_independence_ceiling_add": "10",
            "country_legislative_override_capacity_add": "1",
            "country_authority_add": "50",
            "country_suppression_cost_mult": "-0.1",
            "country_credit_standing_add": "0.01",
        },
    },
    "law_religious_courts": {
        "progressiveness": "-20",
        "tech": [],
        "modifier": {
            "country_judicial_independence_ceiling_add": "40",
            "interest_group_ig_devout_pol_str_mult": "0.15",
            "state_bureaucracy_population_base_cost_factor_mult": "-0.05",
            "country_credit_standing_add": "0.005",
        },
    },
    "law_statutory_courts": {
        "progressiveness": "0",
        "tech": ["rationalism"],
        "modifier": {
            "country_judicial_independence_ceiling_add": "70",
            "country_suppression_cost_mult": "0.1",
            "state_bureaucracy_population_base_cost_factor_mult": "0.05",
            "country_legitimacy_from_votes_if_elected_add": "10",
            "country_authority_if_unelected_add": "25",
        },
    },
    "law_constitutional_review": {
        "progressiveness": "50",
        "tech": ["human_rights"],
        "modifier": {
            "country_judicial_independence_ceiling_add": "100",
            "country_legislative_override_capacity_add": "-2",
            "country_suppression_cost_mult": "0.25",
            "state_bureaucracy_population_base_cost_factor_mult": "0.05",
            "country_constitutional_law_enactment_success_add": "-0.1",
        },
    },
    "law_judicial_supremacy": {
        "progressiveness": "75",
        "tech": ["civil_rights_movement"],
        "modifier": {
            "country_judicial_independence_ceiling_add": "100",
            "country_legislative_override_capacity_add": "-3",
            "country_suppression_cost_mult": "0.4",
            "state_bureaucracy_population_base_cost_factor_mult": "0.05",
            "country_legitimacy_base_add": "-5",
            "country_credit_standing_add": "0.003",
            "country_legitimacy_ideological_incoherence_mult": "-0.25",
            "political_movement_radicalism_add": "-0.1",
            "political_movement_pop_attraction_mult": "0.1",
            "country_constitutional_law_enactment_success_add": "-0.15",
            "country_rights_law_enactment_success_add": "-0.15",
        },
    },
    "law_algorithmic_jurisprudence": {
        "progressiveness": "25",
        "tech": ["generative_ai"],
        "modifier": {
            "country_judicial_independence_ceiling_add": "60",
            "state_bureaucracy_population_base_cost_factor_mult": "-0.1",
            "country_override_with_algorithmic_governance_add": "2",
        },
    },
}


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


def _loc_lines():
    """{key: line} over every English loc file (organize_loc may move a key)."""
    lines = {}
    for path in glob.glob(os.path.join(REPO, "localization", "english", "**", "*.yml"), recursive=True):
        for line in _read(path).splitlines():
            match = re.match(r"\s+([A-Za-z0-9_.\-]+):\d*\s", line)
            if match:
                lines[match.group(1)] = line
    return lines


def _loc_keys():
    return set(_loc_lines())


def _modifier(body):
    return {k: _body(v) for k, v in _body(body["modifier"]).items()}


class LawsTest(unittest.TestCase):
    def setUp(self):
        self.laws = _parse(LAWS)

    def test_group_is_power_structure(self):
        group = _body(_parse(GROUPS)["lawgroup_judiciary"])
        self.assertEqual(_body(group["law_group_category"]), "power_structure")
        self.assertEqual(_body(group["ideological_opinion_impact"]), "0.5")
        self.assertEqual(_body(group["affected_by_regime_change"]), "yes")

    def test_six_laws_executive_first(self):
        self.assertEqual(tuple(self.laws), COURT_LAWS)

    def test_values_match_spec(self):
        for law, spec in SPEC_LAWS.items():
            body = _body(self.laws[law])
            with self.subTest(law=law):
                self.assertEqual(_body(body["group"]), "lawgroup_judiciary")
                self.assertEqual(_body(body["progressiveness"]), spec["progressiveness"])
                self.assertEqual(_body(body.get("unlocking_technologies", ("=", []))), spec["tech"])
                self.assertEqual(_modifier(body), spec["modifier"])

    def test_religious_courts_need_a_church(self):
        body = _body(self.laws["law_religious_courts"])
        self.assertEqual(_body(body["disallowing_laws"]), ["law_total_separation", "law_state_atheism"])

    def test_no_law_gates(self):
        # The owner (2026-10-17): Judicial Supremacy is reachable from any court.
        for law in COURT_LAWS:
            self.assertNotIn("unlocking_laws", _body(self.laws[law]), law)

    def test_display_types_are_script_only(self):
        types = {k: _body(v) for k, v in _parse(TYPES).items()}
        self.assertEqual(set(types), set(DISPLAY_TYPES))
        for name, body in types.items():
            if name.endswith("_bool"):
                self.assertEqual(_body(body["boolean"]), "yes", name)
            else:
                self.assertEqual(_body(body["script_only"]), "yes", name)

    def test_paper_courts_carry_both_lines(self):
        injected = _parse(INJECTIONS)
        bodies = {law: _body(injected["INJECT:" + law]) for law in PAPER_COURT_LAWS[:-1]}
        bodies["law_algorithmic_governance"] = _body(_parse(EXTRA_LAWS)["law_algorithmic_governance"])
        for law, body in bodies.items():
            modifier = _modifier(body)
            self.assertEqual(modifier.get("country_judicial_independence_ceiling_mult"), "-0.5", law)
            self.assertEqual(modifier.get("country_court_challenges_ignored_bool"), "yes", law)

    def test_names_and_descriptions(self):
        keys = _loc_keys()
        for key in COURT_LAWS + DISPLAY_TYPES + ("lawgroup_judiciary",):
            self.assertIn(key, keys)
            self.assertIn(key + "_desc", keys)

    def test_supremacy_says_the_courts_do_not_govern(self):
        # The owner's requirement (spec Decisions): otherwise it would be a
        # Distribution of Power law.
        self.assertIn("the government still governs", _loc_lines()["law_judicial_supremacy_desc"])


if __name__ == "__main__":
    unittest.main()
