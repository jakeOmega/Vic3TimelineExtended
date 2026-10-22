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
VALUES = os.path.join(REPO, "common", "script_values", "te_judiciary_values.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "te_judiciary_triggers.txt")
MODIFIERS = os.path.join(REPO, "common", "static_modifiers", "te_judiciary_modifiers.txt")

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


# Spec § 3.2: the score's modifier at 100.
SCORE_MODIFIER = {
    "country_legitimacy_base_add": "10",
    "country_credit_standing_add": "-0.005",
    "state_capitalists_investment_pool_efficiency_mult": "0.1",
    "political_movement_radicalism_from_enactment_disapproval_mult": "-0.2",
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


class ScoreDefinitionsTest(unittest.TestCase):
    def setUp(self):
        self.mods = {k: _body(v) for k, v in _parse(MODIFIERS).items()}

    def _value(self, modifier, key):
        return _body(self.mods[modifier][key])

    def test_ceiling_reads_the_laws_lines(self):
        block = _block(_read(VALUES), "te_jud_ceiling")
        self.assertIn("value = modifier:country_judicial_independence_ceiling_add", block)
        self.assertIn("add = modifier:country_judicial_independence_ceiling_mult", block)
        self.assertNotIn("has_law", block, "the ceiling is the tooltip's number, not a law check")

    def test_paper_court_reads_its_line(self):
        block = _block(_read(TRIGGERS), "te_jud_paper_court")
        self.assertIn("modifier:country_court_challenges_ignored_bool = yes", block)

    def test_score_modifier_matches_spec(self):
        body = {k: _body(v) for k, v in self.mods["te_judicial_independence"].items() if k != "icon"}
        self.assertEqual(body, SCORE_MODIFIER)

    def test_unit_modifiers(self):
        # Each is applied with multiplier = the law's tooltip line.
        self.assertEqual(self._value("te_jud_votes_legitimacy", "country_legitimacy_govt_total_votes_add"), "1")
        self.assertEqual(self._value("te_jud_unelected_authority", "country_authority_add"), "1")
        self.assertEqual(self._value("te_jud_algorithmic_capture", "country_legislative_override_capacity_add"), "1")
        values = _read(VALUES)
        for name, line in (("te_jud_votes_mult_value", "country_legitimacy_from_votes_if_elected_add"),
                           ("te_jud_authority_mult_value", "country_authority_if_unelected_add"),
                           ("te_jud_capture_mult_value", "country_override_with_algorithmic_governance_add")):
            self.assertIn("value = modifier:" + line, _block(values, name))

    def test_challenge_tiers_match_the_laws(self):
        # The engine needs a named enactment modifier, so the laws' lines pick
        # one of two tiers (te_jud_enactment_started). Every line must be a tier.
        self.assertEqual(self._value("te_jud_constitutional_challenge", "country_law_enactment_success_add"), "-0.1")
        self.assertEqual(self._value("te_jud_supremacy_challenge", "country_law_enactment_success_add"), "-0.15")
        lines = set()
        for body in _parse(LAWS).values():
            modifier = _modifier(_body(body))
            for key in ("country_constitutional_law_enactment_success_add", "country_rights_law_enactment_success_add"):
                if key in modifier:
                    lines.add(modifier[key])
        self.assertLessEqual(lines, {"-0.1", "-0.15"})

    def test_overhaul(self):
        self.assertEqual(self._value("te_jud_court_overhaul", "country_risk_premium_add"), "0.02")
        self.assertEqual(self._value("te_jud_court_overhaul", "country_legitimacy_base_add"), "-10")

    def test_concept_names_entrenchment(self):
        # Spec § 3.4: the concept is one of the three places a player reads it.
        desc = _loc_lines()["concept_judicial_independence_desc"]
        self.assertIn("enactment success", desc)

    def test_loc(self):
        keys = _loc_keys()
        for key in ("concept_judicial_independence", "te_judicial_independence", "te_jud_votes_legitimacy",
                    "te_jud_unelected_authority", "te_jud_algorithmic_capture", "te_jud_court_overhaul",
                    "te_jud_constitutional_challenge", "te_jud_supremacy_challenge"):
            self.assertIn(key, keys)
            self.assertIn(key + "_desc", keys)


EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_judiciary_effects.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "te_judiciary_on_actions.txt")
HISTORY = os.path.join(REPO, "common", "history", "extra_history.txt")
SCALED = ("te_judicial_independence", "te_jud_votes_legitimacy", "te_jud_unelected_authority",
          "te_jud_algorithmic_capture")
MULT_VARS = ("te_jud_modifier_mult", "te_jud_votes_mult", "te_jud_authority_mult", "te_jud_capture_mult",
             "te_jud_overhaul_mult")


def _script_files():
    for sub in ("common", "events"):
        for path in glob.glob(os.path.join(REPO, sub, "**", "*.txt"), recursive=True):
            yield path


class ScoreScriptTest(unittest.TestCase):
    def test_one_refresh_site(self):
        write = re.compile(r"(?:add_modifier = \{\s*name = |remove_modifier = )(?:%s)\b" % "|".join(SCALED))
        writers, callers = set(), []
        for path in _script_files():
            text = _read(path)
            if write.search(text):
                writers.add(os.path.relpath(path, REPO))
            callers += [os.path.relpath(path, REPO)] * len(re.findall(r"\bte_jud_refresh = yes", text))
        self.assertEqual(writers, {"common/scripted_effects/te_judiciary_effects.txt"})
        self.assertEqual(callers, ["common/on_actions/te_judiciary_on_actions.txt"])
        self.assertIn("te_jud_refresh = yes", _block(_read(ON_ACTIONS), "te_jud_monthly"))

    def test_multiplier_variables_are_never_removed(self):
        for path in _script_files():
            for name in MULT_VARS:
                self.assertNotIn("remove_variable = " + name, _read(path), path)

    def test_refresh_reads_the_conditions(self):
        block = _block(_read(EFFECTS), "te_jud_refresh")
        self.assertIn("te_jud_elected_government = yes", block)
        self.assertIn("NOT = { te_jud_elected_government = yes }", block)
        self.assertIn("has_law = law_type:law_algorithmic_governance", block)

    def test_yearly_step(self):
        block = _block(_read(EFFECTS), "te_jud_yearly_update")
        self.assertIn("add = 4", block)
        self.assertIn("subtract = 10", block)
        self.assertEqual(block.count("value = te_jud_ceiling"), 2, "both directions stop at the ceiling")

    def test_spend_floors_at_zero(self):
        block = _block(_read(EFFECTS), "te_jud_spend")
        self.assertIn("subtract = $AMOUNT$", block)
        self.assertIn("var:te_judicial_independence < 0", block)

    def test_seeding_waits_for_the_monthly_pulse(self):
        # Modifier sums may not be in place at on_game_started.
        start = _block(_read(ON_ACTIONS), "te_jud_on_game_started")
        self.assertNotIn("te_jud_seed_score", start)
        self.assertIn("set_global_variable = te_jud_world_seeded", start)
        monthly = _block(_read(ON_ACTIONS), "te_jud_monthly")
        self.assertIn("has_global_variable = te_jud_world_seeded", monthly)
        self.assertNotIn("te_jud_assign_court_by_rule", monthly, "a new country keeps its law")

    def test_rebels_are_not_seeded(self):
        # A revolution's winner keeps its own variables where both sides hold
        # one, so rebels seeded during the war would replace the nation's score.
        limit = _block(_read(ON_ACTIONS), "te_jud_monthly").split("te_jud_seed_score = yes")[0]
        self.assertIn("NOT = { is_revolutionary = yes }", limit)

    def test_seeding_waits_for_the_sums(self):
        # Every country holds a court law, so a ceiling of 0 means the laws'
        # modifier sums aren't in place yet (a first pulse on 1 January).
        limit = _block(_read(ON_ACTIONS), "te_jud_monthly").split("te_jud_seed_score = yes")[0]
        self.assertIn("te_jud_ceiling > 0", limit)

    def test_history(self):
        text = _read(HISTORY)
        self.assertIn("te_jud_assign_court_by_rule = yes", _block(text.replace("\n\tevery_country = {", "\nevery_country = {", 1), "every_country"))
        # A country block: `c:TAG = {`, then text and one-level blocks only.
        inside = r"c:%s = \{(?:[^{}]|\{[^{}]*\})*?"
        self.assertRegex(text, inside % "USA" + r"activate_law = law_type:law_constitutional_review")
        for tag, score in (("GBR", 70), ("USA", 60), ("NET", 50), ("SWE", 50), ("BEL", 40), ("PRU", 35), ("FRA", 35)):
            self.assertRegex(text, inside % tag + r"set_variable = \{ name = te_judicial_independence value = %d \}" % score, tag)


VANILLA_LAWS = os.path.join(REPO, "vanilla_parsed", "common", "laws.json")

# Spec § 3.4.
CORE_GROUPS = {
    "lawgroup_distribution_of_power", "lawgroup_governance_principles", "lawgroup_church_and_state",
    "lawgroup_citizenship", "lawgroup_free_speech", "lawgroup_internal_security",
    "lawgroup_state_power", "lawgroup_judiciary",
}
RIGHTS_GROUPS = {
    "lawgroup_rights_of_women", "lawgroup_slavery", "lawgroup_minority_rights",
    "lawgroup_LGBTQ_rights", "lawgroup_privacy_rights",
}


def _law_groups():
    """{law: group} over vanilla (the snapshot) and every mod law file."""
    with open(VANILLA_LAWS, encoding="utf-8") as fh:
        groups = {k: v[1]["group"][1] for k, v in json.load(fh).items() if "group" in v[1]}
    for path in glob.glob(os.path.join(REPO, "common", "laws", "*.txt")):
        for key, node in _parse(path).items():
            body = _body(node)
            if isinstance(body, dict) and "group" in body:
                groups[key] = _body(body["group"])
    return groups


class EntrenchmentTest(unittest.TestCase):
    def _named_groups(self, trigger):
        laws = re.findall(r"is_same_law_group_as = law_type:(\w+)", _block(_read(TRIGGERS), trigger))
        groups = _law_groups()
        return [groups[law] for law in laws]

    def test_protected_groups_match_spec(self):
        core = self._named_groups("te_jud_enacting_core_law")
        rights = self._named_groups("te_jud_enacting_rights_law")
        self.assertEqual(len(core), len(set(core)), "one law per group")
        self.assertEqual(set(core), CORE_GROUPS)
        self.assertEqual(set(rights), RIGHTS_GROUPS)

    def test_the_laws_lines_pick_the_tier(self):
        block = _block(_read(ON_ACTIONS), "te_jud_enactment_started")
        self.assertEqual(block.count("NOT = { te_jud_paper_court = yes }"), 2)
        self.assertIn("modifier:country_constitutional_law_enactment_success_add <= -0.15", block)
        self.assertIn("modifier:country_rights_law_enactment_success_add <= -0.15", block)
        self.assertIn("modifier:country_constitutional_law_enactment_success_add < 0", block)
        self.assertIn("add_enactment_modifier = { name = te_jud_supremacy_challenge }", block)
        self.assertIn("add_enactment_modifier = { name = te_jud_constitutional_challenge }", block)
        self.assertNotIn("has_law", block, "the tooltip's numbers decide, not a law check")

    def test_self_check_is_once_a_game_and_excludes_no_enactment(self):
        block = _block(_read(EFFECTS), "te_jud_selfcheck_enacting_scope")
        self.assertIn("enacting_any_law = yes", block)
        self.assertIn("set_global_variable = te_jud_selfcheck_enacting_done", block)
        self.assertIn("TE_SELF_CHECK OK judiciary_enacting_law_scope", block)
        self.assertIn("TE_SELF_CHECK BROKEN judiciary_enacting_law_scope", block)


EVENTS = os.path.join(REPO, "events", "te_judiciary_events.txt")
CEILING_LAWS = set(COURT_LAWS) | set(PAPER_COURT_LAWS)


class ShockTest(unittest.TestCase):
    def test_every_ceiling_law_fires_the_check(self):
        block = _block(_read(ON_ACTIONS), "te_jud_law_activated")
        self.assertEqual(set(re.findall(r"type = law_type:(\w+)", block)), CEILING_LAWS)
        self.assertIn("owner = {", block)
        # The new law's modifier sums may lag the change.
        self.assertIn("trigger_event = { id = te_judiciary_events.1 days = 7 }", block)
        self.assertNotIn("multiplier", block, "ROOT is the law here")
        self.assertNotIn("var:", block, "has_variable fails on law scopes")

    def test_shock_runs_in_a_country_event(self):
        event = _block(_read(EVENTS), "te_judiciary_events.1")
        self.assertIn("type = country_event", event)
        self.assertIn("hidden = yes", event)
        self.assertIn("multiplier = var:te_jud_overhaul_mult", event)
        self.assertIn("is_decaying = yes", event)
        self.assertIn("years = 5", event)

    def test_a_second_shock_replaces_the_first(self):
        # A same-name add_modifier stacks a copy, and every copy re-reads the
        # multiplier: a new shock removes the running one, and comes only when
        # the gap is larger than the one being paid for.
        event = _block(_read(EVENTS), "te_judiciary_events.1")
        trigger = event[event.index("\ttrigger = {"):event.index("\timmediate = {")]
        immediate = event[event.index("\timmediate = {"):]
        self.assertIn("NOT = { has_modifier = te_jud_court_overhaul }", trigger)
        self.assertIn("te_jud_overhaul_mult_value > var:te_jud_overhaul_mult", trigger)
        self.assertLess(immediate.index("remove_modifier = te_jud_court_overhaul"),
                        immediate.index("add_modifier = {"))

    def test_shock_needs_seeding(self):
        event = _block(_read(EVENTS), "te_judiciary_events.1")
        trigger = event[event.index("\ttrigger = {"):event.index("\timmediate = {")]
        self.assertIn("has_variable = te_jud_seeded", trigger)
        self.assertIn("te_jud_overhaul_gap >= 20", trigger)


MINOR_EVENTS = os.path.join(REPO, "events", "minor_events.txt")
TAX_OFFER = os.path.join(REPO, "common", "scripted_effects", "te_tax_offer_effects.txt")


class SpendTest(unittest.TestCase):
    def test_forceful_legislation_spends_and_says_so(self):
        event = _block(_read(MINOR_EVENTS), "minor_events_timelineextended.2")
        options = re.split(r"\n\toption = \{", event)[1:]
        by_name = {re.search(r"name = (\S+)", o).group(1): o for o in options}
        for name, amount, key in (("minor_events_timelineextended.2.b", 5, "te_jud_spend_small_tt"),
                                  ("minor_events_timelineextended.2.c", 10, "te_jud_spend_medium_tt"),
                                  ("minor_events_timelineextended.2.e", 20, "te_jud_spend_large_tt")):
            self.assertRegex(by_name[name],
                             r"custom_tooltip = \{\s*text = %s\s*te_jud_spend = \{ AMOUNT = %d \}" % (key, amount), name)
        self.assertNotIn("te_jud_spend", by_name["minor_events_timelineextended.2.a"])

    def test_guide_says_the_cost_does_not_fade(self):
        # The table's last column fades over five years; the score's cost
        # doesn't, so it is a sentence of its own.
        guide = _read(os.path.join(REPO, "docs", "player_guide", "06-politics.md"))
        rows = [line for line in guide.splitlines()
                if line.startswith(("| Expedite", "| Push the law", "| Force the law"))]
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertNotIn("Judicial Independence", row)
        self.assertIn("lowers Judicial Independence by 5, 10 or 20", guide)

    def test_tax_force_through_spends(self):
        block = _block(_read(TAX_OFFER), "te_tax_force_into")
        self.assertIn("te_jud_spend = { AMOUNT = 10 }", block)

    def test_loc(self):
        keys = _loc_keys()
        for key in ("te_jud_spend_small_tt", "te_jud_spend_medium_tt", "te_jud_spend_large_tt"):
            self.assertIn(key, keys)


IDEOLOGY_FILES = sorted(glob.glob(os.path.join(REPO, "common", "ideologies", "*.txt")))
CONSISTENCY = os.path.join(REPO, "common", "scripted_effects", "extra_law_consistency_generated.txt")
VANILLA_IDEOLOGIES = os.path.join(REPO, "vanilla_parsed", "common", "ideologies.json")

# Spec § 7, mod ideologies written by hand in extra_ideologies.txt.
MOD_STANCES = {
    "ideology_islamic_inheritance": "religious",
    "ideology_corporate": "market",
    "ideology_multicultural": "rights",
    "ideology_optimist_transhumanist": "technocratic",
    "ideology_custom_religion_theocratic_governance": "religious",
    "ideology_custom_religion_theocratic_society": "religious",
    "ideology_custom_religion_technocratic_governance": "technocratic",
    "ideology_custom_religion_republican_governance": "liberal",
    "ideology_custom_religion_aristocratic_governance": "traditional",
    "ideology_custom_religion_corporate_governance": "market",
    "ideology_custom_religion_imperial_cult_governance": "absolutist",
}


class StancesTest(unittest.TestCase):
    def test_lists_name_all_six_laws(self):
        import ideology_modifications as im
        for name, stances in im.JUDICIARY_LISTS.items():
            self.assertEqual(tuple(law for law, _ in stances), COURT_LAWS, name)

    def test_vanilla_keys_exist(self):
        import ideology_modifications as im
        with open(VANILLA_IDEOLOGIES, encoding="utf-8") as fh:
            vanilla = set(json.load(fh))
        self.assertLessEqual(set(im.JUDICIARY_STANCES), vanilla)
        for ideology, name in im.JUDICIARY_STANCES.items():
            self.assertEqual(im.modifications[ideology]["lawgroup_judiciary"], im.JUDICIARY_LISTS[name], ideology)

    def test_every_block_in_script_names_all_six(self):
        seen = set()
        for path in IDEOLOGY_FILES:
            for key, node in _parse(path).items():
                body = _body(node)
                if isinstance(body, dict) and "lawgroup_judiciary" in body:
                    block = _body(body["lawgroup_judiciary"])
                    self.assertEqual(set(block), set(COURT_LAWS), key)
                    seen.add(key.split(":")[-1])
        import ideology_modifications as im
        self.assertLessEqual(set(im.JUDICIARY_STANCES) | set(MOD_STANCES), seen)

    def test_mod_ideologies_use_their_lists(self):
        import ideology_modifications as im
        data = _parse(os.path.join(REPO, "common", "ideologies", "extra_ideologies.txt"))
        for ideology, name in MOD_STANCES.items():
            block = {k: _body(v) for k, v in _body(_body(data[ideology])["lawgroup_judiciary"]).items()}
            self.assertEqual(block, dict(im.JUDICIARY_LISTS[name]), ideology)

    def test_religious_courts_fall_to_statutory(self):
        block = _block(_read(CONSISTENCY), "te_fix_inconsistent_lawgroup_judiciary")
        religious = block[block.index("law_type:law_religious_courts"):]
        self.assertLess(religious.index("law_type:law_statutory_courts"),
                        religious.index("law_type:law_executive_tribunals"))


if __name__ == "__main__":
    unittest.main()
