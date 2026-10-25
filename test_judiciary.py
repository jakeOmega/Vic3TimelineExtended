"""Judiciary law group (docs/superpowers/archive/specs/2026-10-17-judiciary-design.md).

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
    "country_court_reviews_forced_laws_bool",
    "country_amendment_lapses_at_peace_bool",
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
            "country_court_reviews_forced_laws_bool": "yes",
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
            "country_court_reviews_forced_laws_bool": "yes",
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
REPAIRS = os.path.join(REPO, "common", "on_actions", "te_old_save_repairs.txt")
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

    def test_old_save_seeding_is_a_marked_repair(self):
        text = _read(REPAIRS)
        self.assertIn("te_repair_judiciary_seed", _block(text, "on_monthly_pulse"))
        block = _block(text, "te_repair_judiciary_seed")
        self.assertIn("NOT = { has_global_variable = te_jud_world_seeded }", block)
        self.assertIn("te_jud_assign_court_by_rule = yes", block)
        # The score is released a month after the courts change, once their
        # modifiers are in place.
        self.assertIn("has_global_variable = te_jud_courts_assigned", block)
        self.assertRegex(text, r"# OLD-SAVE REPAIR \(#\d+\): remove after \d{4}-\d{2}-\d{2}[^\n]*\n(#[^\n]*\n)*te_repair_judiciary_seed")

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


# ----------------------------------------------------------------------
#  Phases 2-4 (spec § 14)
# ----------------------------------------------------------------------

AMENDMENTS_FILE = os.path.join(REPO, "common", "amendments", "te_judiciary_amendments.txt")
PETITION_EVENTS = os.path.join(REPO, "events", "amendment_petition_events.txt")
PETITION_ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "amendment_petition_on_actions.txt")
PETITION_TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "amendment_petition_triggers.txt")
LAW_EVENT_POOLS = os.path.join(REPO, "common", "on_actions", "law_events_on_actions.txt")

# Spec § 14.1: the score at which the court strikes a forced law down, by
# Forceful Legislation option (size key, tier).
STRIKE = {("small", 1): 90, ("medium", 2): 60, ("large", 3): 30}


def _without_comments(text):
    return re.sub(r"#[^\n]*", "", text)


class DefyingTheCourtTest(unittest.TestCase):
    """Phase 2: a law forced through under a reviewing court goes to it."""

    def test_reviews_need_the_line_and_a_court_the_executive_cannot_ignore(self):
        block = _block(_read(TRIGGERS), "te_jud_court_can_strike_laws")
        self.assertIn("modifier:country_court_reviews_forced_laws_bool = yes", block)
        self.assertIn("NOT = { te_jud_paper_court = yes }", block)

    def test_forceful_options_open_a_challenge_and_say_so(self):
        event = _block(_read(MINOR_EVENTS), "minor_events_timelineextended.2")
        options = re.split(r"\n\toption = \{", event)[1:]
        by_name = {re.search(r"name = (\S+)", o).group(1): o for o in options}
        for name, size, tier in (("minor_events_timelineextended.2.b", "small", 1),
                                 ("minor_events_timelineextended.2.c", "medium", 2),
                                 ("minor_events_timelineextended.2.e", "large", 3)):
            self.assertRegex(
                by_name[name],
                r"limit = \{ te_jud_court_can_strike_laws = yes \}\s*custom_tooltip = \{\s*text = te_jud_review_%s_tt"
                r"\s*te_jud_open_challenge = \{ TIER = %d \}" % (size, tier), name)
        self.assertNotIn("te_jud_open_challenge", by_name["minor_events_timelineextended.2.a"])

    def test_thresholds_match_what_the_tooltips_say(self):
        block = _block(_read(VALUES), "te_jud_strike_threshold")
        self.assertRegex(block, r"value = 90")
        self.assertRegex(block, r"var:te_jud_case_tier = 2 \}\s*value = 60")
        self.assertRegex(block, r"var:te_jud_case_tier >= 3 \}\s*value = 30")
        lines = _loc_lines()
        for (size, _), score in STRIKE.items():
            self.assertIn("#v %d#!" % score, lines["te_jud_review_%s_tt" % size], size)
            self.assertIn("#v %d#!" % score, lines["country_court_reviews_forced_laws_bool_desc"], size)

    def test_the_case_is_filed_in_the_country_pulse_once_the_law_stands(self):
        monthly = _block(_read(ON_ACTIONS), "te_jud_monthly")
        self.assertIn("te_jud_challenge_monthly = yes", monthly)
        block = _without_comments(_block(_read(EFFECTS), "te_jud_challenge_monthly"))
        self.assertIn("NOT = { enacting_any_law = yes }", block)
        self.assertIn("has_law = var:te_jud_challenge_law", block)
        self.assertIn("NOT = { has_variable = te_jud_case_filed }", block, "one case at a time")
        self.assertIn("trigger_event = { id = te_judiciary_events.2 days = 180 }", block)
        # The filed case is a copy, so a second forced law can't overwrite it.
        for name, source in (("te_jud_case_law", "te_jud_challenge_law"), ("te_jud_case_replaced", "te_jud_replaced_law"),
                             ("te_jud_case_tier", "te_jud_challenge_tier")):
            self.assertRegex(block, r"name = %s\s*value = var:%s" % (name, source))

    def test_the_challenge_stores_both_laws(self):
        block = _without_comments(_block(_read(EFFECTS), "te_jud_open_challenge"))
        self.assertIn("te_jud_court_can_strike_laws = yes", block)
        self.assertIn("currently_active_law_in_group", block)
        self.assertRegex(block, r"name = te_jud_challenge_law\s*value = scope:te_jud_forced_type")
        self.assertRegex(block, r"name = te_jud_replaced_law\s*value = scope:te_jud_replaced_type")
        self.assertIn("te_jud_selfcheck_law_type_variable = yes", block)

    def test_self_check_is_once_a_game_and_needs_the_type(self):
        block = _block(_read(EFFECTS), "te_jud_selfcheck_law_type_variable")
        limit = block[:block.index("set_global_variable")]
        self.assertIn("NOT = { has_global_variable = te_jud_selfcheck_law_type_done }", limit)
        self.assertIn("exists = scope:te_jud_forced_type", limit, "a missing scope must not read as OK")
        self.assertIn("TE_SELF_CHECK OK judiciary_law_type_variable", block)
        self.assertIn("TE_SELF_CHECK BROKEN judiciary_law_type_variable", block)

    def test_every_ruling_closes_the_case(self):
        events = _read(EVENTS)
        ruling = _block(events, "te_judiciary_events.2")
        self.assertIn("hidden = yes", ruling)
        self.assertIn("var:te_judicial_independence >= te_jud_strike_threshold", ruling)
        self.assertIn("te_jud_close_case = yes", ruling, "a lapsed case is closed")
        for event in ("te_judiciary_events.3", "te_judiciary_events.4"):
            immediate = _block(events, event)
            immediate = immediate[immediate.index("\timmediate = {"):immediate.index("\toption = {")]
            self.assertIn("te_jud_close_case = yes", immediate, event)

    def test_answers_to_a_ruling(self):
        event = _block(_read(EVENTS), "te_judiciary_events.3")
        options = re.split(r"\n\toption = \{", event)[1:]
        comply, defy, pack = options
        self.assertIn("activate_law = scope:te_jud_restored_type", comply)
        self.assertIn("te_jud_ruling_unreversed", comply, "the fallback when no law was recorded")
        self.assertRegex(defy, r"text = te_jud_spend_large_tt\s*te_jud_spend = \{ AMOUNT = 20 \}")
        self.assertIn("te_jud_ruling_defied", defy)
        self.assertRegex(pack, r"text = te_jud_spend_pack_tt\s*te_jud_spend = \{ AMOUNT = 15 \}")
        self.assertIn("te_jud_pack_court = yes", pack)
        self.assertIn("#N -15#!", _loc_lines()["te_jud_spend_pack_tt"])

    def test_a_packed_court_challenges_nothing(self):
        mods = {k: _body(v) for k, v in _parse(MODIFIERS).items()}
        packed = {k: _body(v) for k, v in mods["te_jud_court_packed"].items()}
        self.assertEqual(packed["country_court_challenges_ignored_bool"], "yes")
        self.assertEqual(packed["country_judicial_independence_ceiling_mult"], "-0.3")
        block = _block(_read(EFFECTS), "te_jud_pack_court")
        self.assertLess(block.index("remove_modifier = te_jud_court_packed"),
                        block.index("add_modifier = { name = te_jud_court_packed years = 10 }"))
        self.assertIn("trigger_event = { id = te_judiciary_events.5 days = 365 }", block)
        # Its authority cost is a cost, never a negative add (CLAUDE.md).
        cost = {k: _body(v) for k, v in mods["te_jud_packing_cost"].items()}
        self.assertNotIn("country_authority_add", cost)
        self.assertEqual(cost["country_authority_cost_add"], "150")

    def test_the_overhaul_protests_are_an_event(self):
        event = _block(_read(EVENTS), "te_judiciary_events.1")
        immediate = event[event.index("\timmediate = {"):]
        self.assertIn("trigger_event = { id = te_judiciary_events.6 }", immediate)
        self.assertNotIn("add_radicals", immediate)

    def test_loc(self):
        keys = _loc_keys()
        for n in (3, 4, 5, 6):
            self.assertIn("te_judiciary_events.%d.t" % n, keys)
            self.assertIn("te_judiciary_events.%d.d" % n, keys)
        for key in ("te_jud_ruling_obeyed", "te_jud_ruling_unreversed", "te_jud_ruling_defied", "te_jud_court_packed",
                    "te_jud_packing_cost", "te_jud_bench_restored", "te_jud_act_upheld", "te_jud_protests_dispersed",
                    "te_jud_tenure_promised"):
            self.assertIn(key, keys)
            self.assertIn(key + "_desc", keys)


# Spec § 14.2: parent, hosts.
AMENDMENTS = {
    "amendment_habeas_corpus_suspension": ("law_secret_police", {"law_statutory_courts", "law_constitutional_review"}),
    "amendment_judicial_elections": ("law_universal_suffrage", {"law_statutory_courts", "law_constitutional_review"}),
    "amendment_mixed_commercial_courts": ("law_free_trade", {"law_religious_courts", "law_executive_tribunals"}),
    "amendment_jury_trials": ("law_guaranteed_liberties", {"law_statutory_courts", "law_constitutional_review"}),
    "amendment_military_tribunals": ("law_outlawed_dissent", {"law_executive_tribunals", "law_statutory_courts"}),
    "amendment_peoples_tribunals": ("law_single_party_state", {"law_executive_tribunals"}),
    "amendment_human_in_the_loop": ("law_strong_privacy_rights", {"law_algorithmic_jurisprudence"}),
}
DEBATED = {"amendment_judicial_elections": 20, "amendment_jury_trials": 21, "amendment_human_in_the_loop": 22}


class AmendmentsTest(unittest.TestCase):
    """Phase 3: seven amendments, each with a scripted way in."""

    @classmethod
    def setUpClass(cls):
        cls.amendments = {k: _body(v) for k, v in _parse(AMENDMENTS_FILE).items()}

    def test_parents_and_hosts_match_spec(self):
        self.assertEqual(set(self.amendments), set(AMENDMENTS))
        for name, (parent, hosts) in AMENDMENTS.items():
            body = self.amendments[name]
            with self.subTest(amendment=name):
                self.assertEqual(_body(body["parent"]), parent)
                self.assertEqual(set(_body(body["allowed_laws"])), hosts)

    def test_hosts_are_court_laws(self):
        for name, (_, hosts) in AMENDMENTS.items():
            self.assertLessEqual(hosts, set(COURT_LAWS), name)

    def test_every_amendment_has_a_petition(self):
        events = _read(PETITION_EVENTS)
        pulse = _block(_read(PETITION_ON_ACTIONS), "on_yearly_pulse_country")
        triggers = _read(PETITION_TRIGGERS)
        for name, (_, hosts) in AMENDMENTS.items():
            short = name[len("amendment_"):]
            with self.subTest(amendment=name):
                self.assertRegex(events, r"add_amendment = \{\s*type = %s\b" % name)
                self.assertIn("te_amendment_petition_%s" % short, pulse)
                ok = _block(triggers, "te_ap_law_ok_%s" % short)
                self.assertEqual(set(re.findall(r"has_law = law_type:(\w+)", ok)), hosts,
                                 "the petition restates allowed_laws")
                self.assertIn("te_ap_enacting_in_judiciary = yes", ok)

    def test_debates_are_pooled_and_attach_to_the_incoming_law(self):
        pool = _block(_read(LAW_EVENT_POOLS), "on_law_checkpoint_debate")
        events = _read(EVENTS)
        for name, n in DEBATED.items():
            event = _block(events, "te_judiciary_events.%d" % n)
            with self.subTest(amendment=name):
                self.assertIn("te_judiciary_events.%d" % n, pool)
                self.assertIn("category = enactment", event)
                self.assertRegex(event, r"currently_enacting_law = \{\s*add_amendment = \{\s*type = %s\b" % name)
                self.assertIn("amendment_compromise_modifier", event)
                self.assertIn("amendment_purist_modifier", event)

    def test_standing_conditions_are_enforced_monthly(self):
        habeas = {k: _body(v) for k, v in _body(self.amendments["amendment_habeas_corpus_suspension"]["modifier"]).items()}
        self.assertEqual(habeas["country_amendment_lapses_at_peace_bool"], "yes")
        self.assertIn("te_jud_amendment_upkeep = yes", _block(_read(ON_ACTIONS), "te_jud_monthly"))
        upkeep = _block(_read(EFFECTS), "te_jud_amendment_upkeep")
        self.assertIn("modifier:country_amendment_lapses_at_peace_bool = yes", upkeep)
        self.assertIn("amendment_type:amendment_habeas_corpus_suspension ?= this.type", upkeep)
        self.assertIn("NOT = { has_law = law_type:law_single_party_state }", upkeep)
        self.assertIn("amendment_type:amendment_peoples_tribunals ?= this.type", upkeep)

    def test_human_in_the_loop_cancels_the_capture(self):
        modifier = {k: _body(v) for k, v in _body(self.amendments["amendment_human_in_the_loop"]["modifier"]).items()}
        law = SPEC_LAWS["law_algorithmic_jurisprudence"]["modifier"]
        self.assertEqual(float(modifier["country_override_with_algorithmic_governance_add"]),
                         -float(law["country_override_with_algorithmic_governance_add"]))

    def test_names_and_descriptions(self):
        keys = _loc_keys()
        for name in AMENDMENTS:
            self.assertIn(name, keys)
            self.assertIn(name + "_desc", keys)
        for n in range(21, 28):
            for suffix in ("t", "d", "f", "a", "b"):
                self.assertIn("amendment_petition_events.%d.%s" % (n, suffix), keys)


# Spec § 14.3: event, its once-per-country variable.
CASES = {
    30: "free_soil", 31: "otsu", 32: "freedom_of_contract", 33: "voided_election",
    34: "necessity", 35: "house_of_justice", 36: "new_code",
}


class LandmarkCasesTest(unittest.TestCase):
    """Phase 4: keyed to game state, once per country."""

    def test_each_case_comes_once(self):
        events = _read(EVENTS)
        for n, case in CASES.items():
            event = _block(events, "te_judiciary_events.%d" % n)
            trigger = event[event.index("\ttrigger = {"):event.index("\timmediate = {")]
            immediate = event[event.index("\timmediate = {"):]
            with self.subTest(case=case):
                self.assertIn("NOT = { has_variable = te_jud_heard_%s }" % case, trigger)
                self.assertIn("set_variable = te_jud_heard_%s" % case, immediate)

    def test_no_dates_or_tags(self):
        # The owner (spec Decisions): the alternate timeline may lack the
        # context by the 20th century, so state, never a date or a tag.
        events = _read(EVENTS)
        for n in CASES:
            event = _without_comments(_block(events, "te_judiciary_events.%d" % n))
            with self.subTest(event=n):
                self.assertNotRegex(event, r"\bc:[A-Z]{3}\b|has_tag|game_date|current_date")

    def test_each_case_is_dispatched(self):
        on_actions = _read(ON_ACTIONS)
        yearly = _block(on_actions, "on_yearly_pulse_country")
        for n, case in CASES.items():
            if n in (33, 34):
                continue
            with self.subTest(case=case):
                self.assertIn("te_jud_landmark_%s" % case, yearly)
                self.assertIn("te_judiciary_events.%d" % n, _block(on_actions, "te_jud_landmark_%s" % case))
        self.assertIn("te_jud_landmark_voided_election", _block(on_actions, "on_election_campaign_end"))
        activated = _block(on_actions, "te_jud_law_activated")
        self.assertIn("trigger_event = { id = te_judiciary_events.34 days = 14 }", activated)

    def test_the_otsu_power_is_never_a_player(self):
        event = _block(_read(EVENTS), "te_judiciary_events.31")
        self.assertEqual(event.count("is_ai = yes"), 2, "the trigger and the scope it saves")

    def test_reform_paths_lead_to_statutory_courts(self):
        events = _read(EVENTS)
        for n in (35, 36):
            self.assertIn("start_enactment = law_type:law_statutory_courts", _block(events, "te_judiciary_events.%d" % n))
        self.assertRegex(_block(events, "te_judiciary_events.36"),
                         r"add_amendment = \{\s*type = amendment_mixed_commercial_courts")

    def test_loc(self):
        keys = _loc_keys()
        for n in CASES:
            for suffix in ("t", "d", "f", "a", "b"):
                self.assertIn("te_judiciary_events.%d.%s" % (n, suffix), keys)
        for key in ("te_jud_case_dred_scott", "te_jud_case_free_soil", "te_jud_case_otsu_upheld",
                    "te_jud_case_otsu_overruled", "te_jud_case_freedom_of_contract", "te_jud_case_election_respected",
                    "te_jud_case_emergency", "te_jud_case_necessity", "te_jud_case_judges_resign"):
            self.assertIn(key, keys)
            self.assertIn(key + "_desc", keys)


if __name__ == "__main__":
    unittest.main()
