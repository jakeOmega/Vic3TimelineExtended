# -*- coding: utf-8 -*-
"""Collective Governance (law_direct_democracy): one table, pinned against
every site that lists the Distribution of Power expressions by hand.

The law keeps its engine key and is displayed as Collective Governance. Each
Distribution of Power group it allows gets one script-attached amendment and
at least one government type. Nothing in the engine checks that the
prerequisites, triggers, amendments, refresh effect, preview tooltips and
government types agree, and a mismatch is engine-silent: a country holding the
law with no amendment, or with the wrong government name. EXPRESSIONS is the
single list; each test checks one site against it. To add a Distribution of
Power law, add it to its row (or add a row) and follow the failures.

Spec: docs/superpowers/specs/2026-09-26-collective-governance-design.md

Run: python3 -m unittest test_collective_governance -v
"""

import os
import re
import unittest
from collections import namedtuple

import ideology_modifications

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


def _raw(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _read(path):
    """Script text with comments stripped (not for loc: `#b` is markup there)."""
    return re.sub(r"#[^\n]*", "", _raw(path))


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


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block (an optional
    INJECT:/REPLACE: prefix is allowed)."""
    m = re.search(r"^(?:[A-Z_]+:)?" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _inner(text, name):
    """The body of the first ``name = { ... }`` block at any depth."""
    m = re.search(r"(?<![\w.:])" + re.escape(name) + r"\s*=\s*\{", text)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _norm(text):
    return " ".join(text.split())


def _top_level_names(text):
    return re.findall(r"^(\w+)\s*=\s*\{", text, re.M)


def _modifiers(body):
    return dict(re.findall(r"(\w+)\s*=\s*(-?[\w.]+)", body))


_LOC_LINE = re.compile(r'^\s*([\w.]+):\d*\s*"(.*)"\s*$')


def _loc():
    out = {}
    folder = _path("localization", "english")
    for name in os.listdir(folder):
        if name.endswith(".yml"):
            with open(os.path.join(folder, name), encoding="utf-8-sig") as f:
                for line in f:
                    m = _LOC_LINE.match(line)
                    if m:
                        out[m.group(1)] = m.group(2)
    return out


Expression = namedtuple("Expression", "trigger dop_laws amendment tooltip")

EXPRESSIONS = [
    Expression(
        "collective_governance_is_popular",
        {"law_landed_voting", "law_wealth_voting", "law_census_voting", "law_universal_suffrage"},
        "amendment_collective_direct_democracy",
        "COLLECTIVE_GOVERNANCE_TT_POPULAR",
    ),
    Expression(
        "collective_governance_is_party",
        {"law_single_party_state"},
        "amendment_collective_leadership",
        "COLLECTIVE_GOVERNANCE_TT_PARTY",
    ),
    Expression(
        "collective_governance_is_technocratic",
        {"law_technocracy"},
        "amendment_collective_administration",
        "COLLECTIVE_GOVERNANCE_TT_TECHNOCRATIC",
    ),
    Expression(
        "collective_governance_is_anarchic",
        {"law_anarchy"},
        "amendment_collective_free_federation",
        "COLLECTIVE_GOVERNANCE_TT_ANARCHIC",
    ),
    Expression(
        "collective_governance_is_patrician",
        {"law_oligarchy", "law_organic_regulation"},
        "amendment_collective_patrician_council",
        "COLLECTIVE_GOVERNANCE_TT_PATRICIAN",
    ),
    Expression(
        "collective_governance_is_algorithmic",
        {"law_algorithmic_governance"},
        "amendment_collective_algorithmic_commons",
        "COLLECTIVE_GOVERNANCE_TT_ALGORITHMIC",
    ),
]

TRIGGERS = _path("common", "scripted_triggers", "collective_governance_triggers.txt")


class TriggerTests(unittest.TestCase):
    def test_each_trigger_lists_exactly_its_laws(self):
        text = _read(TRIGGERS)
        for e in EXPRESSIONS:
            with self.subTest(trigger=e.trigger):
                laws = set(re.findall(r"has_law\s*=\s*law_type:(\w+)", _block(text, e.trigger)))
                self.assertEqual(laws, e.dop_laws)

    def test_no_stale_trigger(self):
        self.assertEqual(set(_top_level_names(_read(TRIGGERS))), {e.trigger for e in EXPRESSIONS})

    def test_no_law_is_in_two_groups(self):
        laws = [law for e in EXPRESSIONS for law in e.dop_laws]
        self.assertEqual(len(laws), len(set(laws)))

    def test_file_has_bom(self):
        with open(TRIGGERS, "rb") as f:
            self.assertEqual(f.read(3), b"\xef\xbb\xbf")


AMENDMENTS = _path("common", "amendments", "extra_amendments.txt")

# Today's Direct Democracy law block, moved verbatim onto the amendment (spec §2).
DIRECT_DEMOCRACY_PACKAGE = {
    "country_must_have_movement_to_enact_laws_bool": "yes",
    "political_movement_pop_attraction_mult": "1",
    "political_movement_radicalism_add": "0.5",
    "political_movement_radicalism_from_enactment_approval_mult": "-0.75",
    "political_movement_radicalism_from_enactment_disapproval_mult": "-0.75",
    "country_legitimacy_govt_total_votes_add": "30",
    "state_political_strength_from_wealth_mult": "-0.25",
    "country_law_enactment_success_add": "0.25",
    "country_agitator_slots_add": "1",
}

EXPRESSION_MODIFIERS = {
    "amendment_collective_direct_democracy": DIRECT_DEMOCRACY_PACKAGE,
    "amendment_collective_leadership": {"country_coup_resistance_mult": "0.25"},
    "amendment_collective_administration": {
        "country_institution_size_change_speed_mult": "0.5",
        "state_decree_cost_mult": "0.25",
    },
    "amendment_collective_free_federation": {
        "country_must_have_movement_to_enact_laws_bool": "yes",
        "political_movement_pop_attraction_mult": "0.5",
    },
    "amendment_collective_patrician_council": {
        "country_aristocrats_pol_str_mult": "0.15",
        "country_capitalists_pol_str_mult": "0.15",
    },
    "amendment_collective_algorithmic_commons": {
        "state_political_strength_from_wealth_mult": "-0.25",
        "political_movement_radicalism_add": "-0.1",
    },
}


class AmendmentTests(unittest.TestCase):
    def setUp(self):
        self.text = _read(AMENDMENTS)

    def test_each_amendment_attaches_only_to_the_law(self):
        for e in EXPRESSIONS:
            with self.subTest(amendment=e.amendment):
                body = _block(self.text, e.amendment)
                self.assertEqual(_norm(_inner(body, "allowed_laws")), "law_direct_democracy")

    def test_each_amendment_follows_its_trigger(self):
        for e in EXPRESSIONS:
            with self.subTest(amendment=e.amendment):
                body = _block(self.text, e.amendment)
                self.assertEqual(_norm(_inner(body, "possible")), f"{e.trigger} = yes")
                self.assertEqual(
                    _norm(_inner(body, "can_repeal")),
                    "custom_tooltip = { text = COLLECTIVE_GOVERNANCE_TT_REPEAL "
                    f"NOT = {{ {e.trigger} = yes }} }}",
                )

    def test_each_amendment_is_script_only(self):
        for e in EXPRESSIONS:
            with self.subTest(amendment=e.amendment):
                body = _block(self.text, e.amendment)
                self.assertEqual(_norm(_inner(body, "would_sponsor")), "always = no")
                self.assertEqual(_norm(_inner(body, "ai_will_revoke")), "always = no")
                self.assertRegex(body, r"amendment_activism_multiplier\s*=\s*0\b")
                self.assertNotRegex(body, r"\bparent\s*=")

    def test_modifiers(self):
        for e in EXPRESSIONS:
            with self.subTest(amendment=e.amendment):
                body = _block(self.text, e.amendment)
                self.assertEqual(_modifiers(_inner(body, "modifier")), EXPRESSION_MODIFIERS[e.amendment])

    def test_no_stale_collective_amendment(self):
        defined = {n for n in _top_level_names(self.text) if n.startswith("amendment_collective_")}
        self.assertEqual(defined, {e.amendment for e in EXPRESSIONS})

    def test_loc(self):
        loc = _loc()
        for e in EXPRESSIONS:
            for key in (e.amendment, e.amendment + "_desc"):
                with self.subTest(key=key):
                    self.assertTrue(key in loc, f"no loc for {key}")
        self.assertTrue("COLLECTIVE_GOVERNANCE_TT_REPEAL" in loc, "no loc for COLLECTIVE_GOVERNANCE_TT_REPEAL")


EFFECTS = _path("common", "scripted_effects", "collective_governance_effects.txt")
ON_ACTIONS = _path("common", "on_actions", "extra_on_actions.txt")


class RefreshTests(unittest.TestCase):
    def test_refresh_syncs_every_amendment_once(self):
        body = _block(_read(EFFECTS), "te_refresh_collective_governance_amendment")
        calls = re.findall(
            r"te_cg_sync_amendment\s*=\s*\{\s*AMENDMENT\s*=\s*(\w+)\s+TRIGGER\s*=\s*(\w+)\s*\}", body)
        self.assertEqual(sorted(calls), sorted((e.amendment, e.trigger) for e in EXPRESSIONS))

    def test_refresh_only_touches_the_governance_law_of_holders(self):
        body = _norm(_block(_read(EFFECTS), "te_refresh_collective_governance_amendment"))
        self.assertIn("limit = { has_law = law_type:law_direct_democracy }", body)
        self.assertIn("save_scope_as = cg_country", body)
        self.assertIn("ruler ?= { interest_group ?= { save_scope_as = cg_sponsor } }", body)
        self.assertIn("active_law:lawgroup_governance_principles ?= {", body)

    def test_sync_removes_on_mismatch_and_adds_on_match(self):
        body = _norm(_block(_read(EFFECTS), "te_cg_sync_amendment"))
        self.assertIn(
            "limit = { has_amendment = amendment_type:$AMENDMENT$ scope:cg_country = { $TRIGGER$ = no } } "
            "random_scope_amendment = { limit = { amendment_type:$AMENDMENT$ ?= this.type } remove_amendment = yes }",
            body)
        self.assertIn(
            "limit = { NOT = { has_amendment = amendment_type:$AMENDMENT$ } "
            "scope:cg_country = { $TRIGGER$ = yes } exists = scope:cg_sponsor } "
            "add_amendment = { type = $AMENDMENT$ sponsor = scope:cg_sponsor cooldown = 0 }",
            body)

    def test_hooks_are_wired(self):
        text = _read(ON_ACTIONS)
        law_hooks = _inner(_block(text, "on_law_activated"), "on_actions").split()
        self.assertIn("te_collective_governance_from_law_scope", law_hooks)
        self.assertGreater(law_hooks.index("te_collective_governance_from_law_scope"),
                           law_hooks.index("te_fix_inconsistent_laws_from_law_scope"))
        monthly = _inner(_block(text, "on_monthly_pulse_country"), "on_actions").split()
        self.assertIn("te_collective_governance_country_pulse", monthly)
        self.assertEqual(_norm(_block(text, "te_collective_governance_from_law_scope")),
                         "effect = { owner = { te_refresh_collective_governance_amendment = yes } }")
        self.assertEqual(_norm(_block(text, "te_collective_governance_country_pulse")),
                         "effect = { te_refresh_collective_governance_amendment = yes }")

    def test_file_has_bom(self):
        with open(EFFECTS, "rb") as f:
            self.assertEqual(f.read(3), b"\xef\xbb\xbf")


LAWS = _path("common", "laws", "extra_laws.txt")

BASE_MODIFIERS = {
    "country_legitimacy_govt_size_add": "1",
    "country_authority_mult": "-0.15",
    "country_law_enactment_speed_mult": "-0.1",
    "country_legitimacy_ideological_incoherence_mult": "-0.3",
}


class LawTests(unittest.TestCase):
    def setUp(self):
        self.body = _block(_read(LAWS), "law_direct_democracy")

    def test_prerequisites_are_exactly_the_expressions(self):
        laws = set(_inner(self.body, "unlocking_laws").split())
        self.assertEqual(laws, set().union(*(e.dop_laws for e in EXPRESSIONS)))
        for excluded in ("law_autocracy", "law_bakufu", "law_neo_absolutism", "law_elder_council"):
            self.assertNotIn(excluded, laws)

    def test_tech_gate(self):
        self.assertEqual(_inner(self.body, "unlocking_technologies").split(), ["political_agitation"])

    def test_can_enact(self):
        self.assertEqual(_norm(_inner(self.body, "can_enact")),
                         "NOT = { has_government_type = gov_chartered_company }")

    def test_base_modifiers(self):
        self.assertEqual(_modifiers(_inner(self.body, "modifier")), BASE_MODIFIERS)

    def test_preview_names_each_expression(self):
        body = _norm(_inner(self.body, "on_enact"))
        for e in EXPRESSIONS:
            with self.subTest(trigger=e.trigger):
                self.assertIn(f"limit = {{ {e.trigger} = yes }} custom_tooltip = {e.tooltip}", body)
        self.assertTrue(body.endswith("custom_tooltip = COLLECTIVE_GOVERNANCE_TT_FOLLOWS_DOP"))

    def test_activation_attaches_hidden(self):
        self.assertEqual(_norm(_inner(self.body, "on_activate")),
                         "hidden_effect = { te_refresh_collective_governance_amendment = yes }")

    def test_ai(self):
        will = _norm(_inner(self.body, "ai_will_do"))
        self.assertIn("has_ideology = ideology:ideology_radical", will)
        self.assertIn("has_ideology = ideology:ideology_anarchist", will)
        self.assertNotIn("law_council_republic", _inner(self.body, "ai_impose_chance"))

    def test_loc(self):
        loc = _loc()
        self.assertEqual(loc["law_direct_democracy"], "Collective Governance")
        self.assertNotIn("participate directly", loc["law_direct_democracy_desc"])
        for key in [e.tooltip for e in EXPRESSIONS] + ["COLLECTIVE_GOVERNANCE_TT_FOLLOWS_DOP"]:
            with self.subTest(key=key):
                self.assertTrue(key in loc, f"no loc for {key}")


GOVERNMENTS = _path("common", "government_types", "timeline_extended_governments.txt")

Gov = namedtuple("Gov", "key trigger extra_law name male female transfer")

# Resolution order: the engine takes the first government type whose possible
# holds, so the more specific come first and the catch-all is last (spec §4).
GOV_TYPES = [
    Gov("gov_collective_noble_commonwealth", "collective_governance_is_patrician", "law_feudal_contracts",
        "Noble Commonwealth", "RULER_TITLE_MARSHAL", "RULER_TITLE_MARSHAL", "parliamentary_elective"),
    Gov("gov_collective_patrician_council", "collective_governance_is_patrician", None,
        "Patrician Council", "RULER_TITLE_SYNDIC", "RULER_TITLE_SYNDIC", "parliamentary_elective"),
    Gov("gov_direct_democracy_single_party_state", "collective_governance_is_party", None,
        "Collective Leadership", "RULER_CHAIRMAN", "RULER_CHAIRWOMAN", "presidential_elective"),
    Gov("gov_collective_administration", "collective_governance_is_technocratic", None,
        "Collegial Administration", "RULER_TITLE_COORDINATOR", "RULER_TITLE_COORDINATOR", "parliamentary_elective"),
    Gov("gov_collective_free_federation", "collective_governance_is_anarchic", None,
        "Free Federation", "RULER_REPRESENTATIVE", "RULER_REPRESENTATIVE", "parliamentary_elective"),
    Gov("gov_direct_democracy", "collective_governance_is_popular", None,
        "Direct Democracy", "RULER_TITLE_SPEAKER", "RULER_TITLE_SPEAKER", "parliamentary_elective"),
    Gov("gov_collective_algorithmic_commons", "collective_governance_is_algorithmic", None,
        "Algorithmic Commons", "RULER_TITLE_STEWARD", "RULER_TITLE_STEWARD", "parliamentary_elective"),
    Gov("gov_collective_governance", None, None,
        "Collective Governance", "RULER_TITLE_SPEAKER", "RULER_TITLE_SPEAKER", "parliamentary_elective"),
]


class GovernmentTypeTests(unittest.TestCase):
    def setUp(self):
        self.text = _read(GOVERNMENTS)

    def test_resolution_order(self):
        keyed = [n for n in _top_level_names(self.text)
                 if "law_type:law_direct_democracy" in _inner(_block(self.text, n), "possible")]
        self.assertEqual(keyed, [g.key for g in GOV_TYPES])

    def test_possible(self):
        for g in GOV_TYPES:
            with self.subTest(gov=g.key):
                expected = ["has_law = law_type:law_direct_democracy"]
                if g.trigger:
                    expected.append(f"{g.trigger} = yes")
                if g.extra_law:
                    expected.append(f"has_law = law_type:{g.extra_law}")
                self.assertEqual(_norm(_inner(_block(self.text, g.key), "possible")), " ".join(expected))

    def test_every_expression_has_a_government(self):
        self.assertEqual({g.trigger for g in GOV_TYPES if g.trigger}, {e.trigger for e in EXPRESSIONS})

    def test_rulers_and_succession(self):
        for g in GOV_TYPES:
            with self.subTest(gov=g.key):
                body = _block(self.text, g.key)
                self.assertRegex(body, rf'(?<!fe)male_ruler\s*=\s*"{g.male}"')
                self.assertRegex(body, rf'female_ruler\s*=\s*"{g.female}"')
                self.assertRegex(body, rf"transfer_of_power\s*=\s*{g.transfer}\b")
                self.assertIn(f"change_to_{g.transfer} = yes", body)
                self.assertIn(f"post_change_to_{g.transfer} = yes", body)
                self.assertRegex(body, r"new_leader_on_reform_government\s*=\s*yes")

    def test_plebiscitary_autocracy_is_gone(self):
        self.assertNotIn("gov_direct_democracy_autocracy", self.text)
        loc = _loc()
        self.assertFalse("gov_direct_democracy_autocracy" in loc, "stale loc gov_direct_democracy_autocracy")
        self.assertFalse("gov_direct_democracy_autocracy_desc" in loc, "stale loc gov_direct_democracy_autocracy_desc")

    def test_loc(self):
        loc = _loc()
        for g in GOV_TYPES:
            with self.subTest(gov=g.key):
                self.assertEqual(loc.get(g.key), g.name)
                self.assertTrue(g.key + "_desc" in loc, f"no loc for {g.key}_desc")
        for title in ("RULER_TITLE_MARSHAL", "RULER_TITLE_SYNDIC", "RULER_TITLE_COORDINATOR", "RULER_TITLE_STEWARD"):
            self.assertTrue(title in loc, f"no loc for {title}")


CH_EFFECTS = _path("common", "scripted_effects", "cultural_hegemony_effects.txt")
LAW_EVENTS = _path("events", "extra_law_events.txt")
ELECTION_EVENTS = _path("events", "modern_election_events.txt")


def _between(text, start_marker, end_marker):
    start = text.index(start_marker)
    return text[start:text.index(end_marker, start)]


class CallSiteTests(unittest.TestCase):
    def test_liberal_democratic_model_needs_a_franchise(self):
        branch = _norm(_between(_raw(CH_EFFECTS), "# Liberal / Progressive democratic", "# Republican:"))
        self.assertIn(
            "AND = { has_law = law_type:law_direct_democracy collective_governance_is_popular = yes }", branch)
        self.assertNotIn("has_law_or_variant = law_type:law_direct_democracy", branch)

    def test_republican_model_is_unchanged(self):
        # An oligarchic council landing in Republican is historically fair (spec §5).
        branch = _norm(_between(_raw(CH_EFFECTS), "# Republican:", "# Mixed / Other"))
        self.assertIn("has_law_or_variant = law_type:law_direct_democracy", branch)

    def test_referendum_events_need_a_franchise(self):
        text = _read(LAW_EVENTS)
        for event in ("extra_law_events.24", "extra_law_events.60", "extra_law_events.84"):
            with self.subTest(event=event):
                trigger = _norm(_inner(_block(text, event), "trigger"))
                self.assertIn("is_enacting_law = law_type:law_direct_democracy "
                              "collective_governance_is_popular = yes", trigger)

    def test_every_enactment_event_for_the_law_is_gated(self):
        text = _read(LAW_EVENTS)
        enacting = re.findall(r"is_enacting_law = law_type:law_direct_democracy", text)
        gated = re.findall(
            r"is_enacting_law = law_type:law_direct_democracy\s+collective_governance_is_popular = yes", text)
        self.assertEqual(len(enacting), len(gated))

    def test_neural_democracy_weight_needs_a_franchise(self):
        body = _norm(_block(_read(ELECTION_EVENTS), "modern_election_events.33"))
        self.assertIn("trigger = { has_law = law_type:law_direct_democracy "
                      "collective_governance_is_popular = yes } add = 5", body)

    def test_instrument_question_does_not_call_the_law_direct_democracy(self):
        self.assertNotIn("direct-democracy bill", _loc()["extra_law_events.84.d"])


EXTRA_IDEOLOGIES = _path("common", "ideologies", "extra_ideologies.txt")
MODIFIED_IDEOLOGIES = _path("common", "ideologies", "modified.txt")

# Spec §6: stances re-read against "no single head". Changes only.
STANCE_CHANGES = {
    "ideology_anarchist": "strongly_approve",
    "ideology_anarchist_movement": "strongly_approve",
    "ideology_bonapartist": "strongly_disapprove",
    "ideology_bonapartist_movement": "strongly_disapprove",
    "ideology_caudillismo": "strongly_disapprove",
    "ideology_fascist_movement": "strongly_disapprove",
    "ideology_absolutist_movement": "strongly_disapprove",
    "ideology_plutocratic": "neutral",
}
CUSTOM_RELIGION_CHANGES = {
    "ideology_custom_religion_aristocratic_governance": "neutral",
    "ideology_custom_religion_technocratic_governance": "neutral",
}


class IdeologyTests(unittest.TestCase):
    def test_vanilla_ideology_stances(self):
        for ideology, stance in STANCE_CHANGES.items():
            with self.subTest(ideology=ideology):
                pairs = dict(ideology_modifications.modifications[ideology]["lawgroup_governance_principles"])
                self.assertEqual(pairs["law_direct_democracy"], stance)

    def test_generated_file_is_current(self):
        text = _read(MODIFIED_IDEOLOGIES)
        for ideology, stance in STANCE_CHANGES.items():
            with self.subTest(ideology=ideology):
                self.assertRegex(_block(text, ideology), rf"law_direct_democracy\s*=\s*{stance}\b")

    def test_custom_religion_stances(self):
        text = _read(EXTRA_IDEOLOGIES)
        for ideology, stance in CUSTOM_RELIGION_CHANGES.items():
            with self.subTest(ideology=ideology):
                self.assertRegex(_block(text, ideology), rf"law_direct_democracy\s*=\s*{stance}\b")


class PreviewTextTests(unittest.TestCase):
    """What a player reads must include what the modifier lists can't show."""

    def test_collective_leadership_names_its_hidden_effect(self):
        # country_coup_resistance_mult is script_only: it never renders in the
        # amendment's modifier list, so the loc has to say it (the
        # covert_regime_change_desc precedent).
        value = EXPRESSION_MODIFIERS["amendment_collective_leadership"]["country_coup_resistance_mult"]
        phrase = f"+{round(float(value) * 100)}% [concept_coup_resistance]"
        loc = _loc()
        for key in ("amendment_collective_leadership_desc", "COLLECTIVE_GOVERNANCE_TT_PARTY"):
            with self.subTest(key=key):
                self.assertIn(phrase, loc[key])

    def test_direct_democracy_preview_names_its_downside(self):
        # The enactment preview is the only place a player sees the package
        # before enacting; the amendment's own modifier list appears only after.
        text = _loc()["COLLECTIVE_GOVERNANCE_TT_POPULAR"]
        self.assertIn("radicalize more readily", text)
        self.assertIn("[concept_legitimacy]", text)


if __name__ == "__main__":
    unittest.main()
