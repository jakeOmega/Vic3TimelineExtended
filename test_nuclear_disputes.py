"""Every crisis dispute at every site that branches on it (2026-10-28 rework
spec §8.5, phase 4b).

A dispatcher that lacks a code falls back without a word: the yield's `else`
stands the target down as if the dispute were an alert (5), the preview calls
it an alert, the custom loc blocks print dispute 5's texts and the yield lines
print nothing. DISPUTES is the one table of codes; each site below must name
every code in it. A new code goes into DISPUTES first, which fails every site
that doesn't have it yet.
"""

import re
import unittest

from test_nuclear_deterrence import (
    CRISIS_EFFECTS,
    CUSTOM_LOC,
    TRIGGERS,
    block,
    loc_value,
    read,
    strip_comments,
)

from pathlib import Path

ROOT = Path(__file__).resolve().parent
CRISIS_EVENTS = ROOT / "events/nuclear_crisis_events.txt"
BUILDINGS = ROOT / "common/buildings/extra_buildings.txt"
COVERT_ACTIONS = ROOT / "common/diplomatic_actions/covert_operations.txt"
COVERT_TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
DETERRENCE_EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
BASING = ROOT / "common/treaty_articles/125_nuclear_basing.txt"
GUARANTEE = ROOT / "common/treaty_articles/115_nuclear_guarantee.txt"
MISSILE_DEFENSE = ("pm_missile_defense_battery", "pm_directed_energy_point_defense")

# (code, the dispute's trigger, a word every prose list of disputes uses,
#  the preview's "over" key, the yield line's key), in classification order
# (spec §8.5: 2, 1, 3, 6, 4, 7, 8, 9, 10, 5). Dispute 5 is the classifier's
# and the preview's `else`.
DISPUTES = [
    (2, "nd_dispute_war_with", "war", "nd_tt_open_over_war", "nd_tt_yield_war"),
    (1, "nd_dispute_play_with", "play", "nd_tt_open_over_play", "nd_tt_yield_play"),
    (3, "nd_dispute_guarantee_against", "guarantee", "nd_tt_open_over_guarantee", "nd_tt_yield_guarantee"),
    (6, "nd_dispute_peacetime_strike_by", "nuclear strike", "nd_tt_open_over_peacetime_strike", "nd_tt_yield_reparations"),
    (4, "nd_dispute_proliferation_by", "weapons program", "nd_tt_open_over_proliferation", "nd_tt_yield_freeze"),
    (7, "nd_dispute_deployment_by", "deploy", "nd_tt_open_over_deployment", "nd_tt_yield_deployment"),
    (8, "nd_dispute_claims_by", "claims", "nd_tt_open_over_claims", "nd_tt_yield_claims"),
    (9, "nd_dispute_covert_ops_by", "covert operations", "nd_tt_open_over_covert_ops", "nd_tt_yield_covert_ops"),
    (10, "nd_dispute_orbital_by", "orbital", "nd_tt_open_over_orbital", "nd_tt_yield_orbital"),
    (5, "nd_dispute_alert_by", "alert", "nd_tt_open_over_alert", "nd_tt_yield_alert"),
]
CODES = [d[0] for d in DISPUTES]
FALLBACK = 5
# Codes whose concession is a branch of its own in nd_crisis_act_yield (1–3 go
# through the play and war concessions, 5 is the else).
OWN_YIELD_BRANCH = [c for c in CODES if c not in (1, 2, 3, FALLBACK)]
# Codes from the 2026-10-28 rework on: they carry their own loc keys, the AI's
# warning names them, and their yields are self-checked.
NEW_CODES = [c for c in CODES if c >= 6]
SELF_CHECKED = [c for c in CODES if c >= 7]
# The issuer is defending, whatever the details (spec §9, rulings R9).
DEFENSIVE = [c for c in CODES if c in (3, 6, 7, 8, 9)]

CUSTOM_BLOCKS = {
    "nd_crisis_dispute_phrase": ("nd_crisis_dispute_phrase_{}",),
    "nd_crisis_dispute_word": ("nd_crisis_dispute_{}",),
    "nd_crisis_demand_text": ("nd_crisis_demand_{}",),
    "nd_crisis_concession_past": ("nd_concession_past_they_{}", "nd_concession_past_we_{}"),
    "nd_crisis_concession_short": ("nd_concession_short_{}",),
    "nd_crisis_concession_long": ("nd_concession_long_{}",),
}


# Each code with a concession of its own: its effect is nd_crisis_concede_<name>.
CONCESSIONS = {6: "reparations", 7: "deployment", 8: "claims", 9: "covert_ops", 10: "orbital"}


def yield_branch(body, code):
    """The body of nd_crisis_act_yield's else_if for dispute `code`."""
    m = re.search(r"else_if = \{\s*limit = \{\s*var:nd_crisis_dispute = " + str(code) + r"\b", body)
    assert m, f"no yield branch for {code}"
    depth, i = 1, body.index("{", m.start()) + 1
    while depth:
        depth += body[i] == "{"
        depth -= body[i] == "}"
        i += 1
    return body[m.start():i]


def dispute_var(code):
    return re.compile(r"var:nd_crisis_dispute = " + str(code) + r"\b")


def dispute_is(code):
    return re.compile(r"nd_crisis_dispute_is = \{ D = " + str(code) + r" \}")


class TestDispatchers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.crisis = strip_comments(read(CRISIS_EFFECTS))
        cls.triggers = strip_comments(read(TRIGGERS))
        cls.custom = strip_comments(read(CUSTOM_LOC))

    def test_classification_order(self):
        body = block(self.crisis, "nd_crisis_classify_dispute")
        writes = [int(n) for n in re.findall(r"name = nd_crisis_dispute value = (\d+)", body)]
        self.assertEqual(writes, CODES)
        self.assertIn(f"name = nd_crisis_dispute value = {FALLBACK}", block(body, "else"))
        order = [body.index(d[1]) for d in DISPUTES if d[0] != FALLBACK]
        self.assertEqual(order, sorted(order))

    def test_preview_order(self):
        body = block(self.crisis, "nd_crisis_preview")
        order = [body.index(d[1] + " = { TARGET = $TARGET$ }") for d in DISPUTES if d[0] != FALLBACK]
        self.assertEqual(order, sorted(order))
        for code, trigger, _word, open_key, _yield in DISPUTES:
            if code != FALLBACK:
                i = body.index(trigger + " = { TARGET = $TARGET$ }")
                self.assertIn("custom_tooltip = " + open_key, body[i:i + 200], code)
        self.assertRegex(body, r"else = \{\s*custom_tooltip = nd_tt_open_over_alert")

    def test_revalidation_names_every_code(self):
        body = block(self.crisis, "nd_crisis_revalidate_dispute")
        for code in CODES:
            self.assertRegex(body, dispute_var(code), code)

    def test_yield_names_every_code(self):
        body = block(self.crisis, "nd_crisis_act_yield")
        for code in OWN_YIELD_BRANCH:
            self.assertRegex(body, dispute_var(code), code)
        lines = block(self.crisis, "nd_crisis_yield_lines")
        for code, _trigger, _word, _open, yield_key in DISPUTES:
            m = dispute_is(code).search(lines)
            self.assertIsNotNone(m, code)
            self.assertIn("custom_tooltip = " + yield_key, lines[m.end():m.end() + 120], code)

    def test_custom_loc_names_every_code(self):
        for name, patterns in CUSTOM_BLOCKS.items():
            body = block(self.custom, name)
            for code in CODES:
                for pattern in patterns:
                    self.assertRegex(body, r"localization_key = " + pattern.format(code) + r"\b", f"{name} {code}")

    def test_eligibility_names_every_dispute(self):
        body = block(self.triggers, "nd_has_crisis_dispute_with")
        for _code, trigger, *_ in DISPUTES:
            self.assertIn(trigger + " = { TARGET = $TARGET$ }", body)

    def test_defensive_codes(self):
        body = block(self.triggers, "nd_crisis_issuer_is_defensive")
        for code in CODES:
            if code in DEFENSIVE:
                self.assertRegex(body, dispute_var(code), code)
            elif code not in (1, 2):
                self.assertNotRegex(body, dispute_var(code), code)

    def test_ai_warning_names_every_new_dispute(self):
        body = block(self.triggers, "nd_ai_would_warn")
        for code, trigger, *_ in DISPUTES:
            if code in NEW_CODES:
                self.assertIn(trigger + " = { TARGET = $TARGET$ }", body, code)

    def test_loc_keys_exist(self):
        for code, _trigger, _word, open_key, yield_key in DISPUTES:
            for key in (open_key, yield_key):
                self.assertTrue(loc_value(key), key)
            if code in NEW_CODES:
                for pattern in sum(CUSTOM_BLOCKS.values(), ()):
                    self.assertTrue(loc_value(pattern.format(code)), pattern.format(code))

    def test_prose_lists_name_every_dispute(self):
        for key in ("nd_tt_has_dispute", "nd_w_crisis_actions_legend"):
            text = loc_value(key)
            for code, _trigger, word, *_ in DISPUTES:
                self.assertIn(word, text, f"{key}: {code}")


class TestConcessionCheck(unittest.TestCase):
    """A once-a-game TE_SELF_CHECK a day after each new concession: does the
    dispute still hold? Scheduled only when it held at the yield, so a yield
    with nothing to remove can't pass for OK."""

    @classmethod
    def setUpClass(cls):
        cls.crisis = strip_comments(read(CRISIS_EFFECTS))
        cls.events = strip_comments(read(CRISIS_EVENTS))

    def test_the_schedule(self):
        body = block(self.crisis, "nd_crisis_concession_check_schedule")
        for needle in ("NOT = { has_global_variable = nd_cc_done_$CODE$ }", "set_global_variable = nd_cc_done_$CODE$",
                       "name = nd_cc_target value = scope:nd_target days = 10", "name = nd_cc_code value = $CODE$ days = 10",
                       "trigger_event = { id = nuclear_crisis.26 days = 1 }"):
            self.assertIn(needle, body)

    def test_the_event(self):
        event = block(self.events, "nuclear_crisis.26")
        self.assertIn("hidden = yes", event)
        self.assertIn("has_variable = nd_cc_target", block(event, "trigger"))
        immediate = block(event, "immediate")
        # The record goes last: every branch reads var:nd_cc_code.
        cleared = immediate.index("remove_variable = nd_cc_target")
        self.assertIn("remove_variable = nd_cc_code", immediate[cleared:])
        for code in SELF_CHECKED:
            self.assertLess(immediate.index(f"var:nd_cc_code = {code}"), cleared, code)
            trigger = next(d[1] for d in DISPUTES if d[0] == code)
            i = immediate.index(f"var:nd_cc_code = {code}")
            branch = immediate[i:i + 900]
            self.assertIn(trigger + " = { TARGET = scope:nd_cc_target }", branch, code)
            self.assertIn(f"TE_SELF_CHECK BROKEN nd_concession_{code}:", branch, code)
            self.assertIn(f"TE_SELF_CHECK OK nd_concession_{code}:", branch, code)

    def test_concession_selfcheck_skips_an_empty_yield(self):
        body = block(self.crisis, "nd_crisis_act_yield")
        for code in SELF_CHECKED:
            trigger = next(d[1] for d in DISPUTES if d[0] == code)
            branch = yield_branch(body, code)
            call = f"nd_crisis_concession_check_schedule = {{ CODE = {code} }}"
            guarded = block(branch, "if")
            self.assertIn("limit = { " + trigger + " = { TARGET = scope:nd_target } }", guarded, code)
            self.assertIn(call, guarded, code)
            # Only inside the if: a yield with nothing to remove isn't checked.
            self.assertEqual(branch.count(call), 1, code)
            self.assertLess(branch.index(call), branch.index("nd_crisis_concede_"), code)

    def test_each_code_yields_its_own_concession(self):
        body = block(self.crisis, "nd_crisis_act_yield")
        for code, name in CONCESSIONS.items():
            branch = yield_branch(body, code)
            self.assertEqual(re.findall(r"nd_crisis_concede_(\w+) = yes", branch), [name], code)


def squash(text):
    return re.sub(r"\s+", " ", text).strip()


class TestClaims(unittest.TestCase):
    """Dispute 8: the target claims one of our incorporated states. Conceding
    renounces each such claim; claims can't be renewed at will, so there is
    no bar, and the dispute ends when none is left (rulings R7)."""

    @classmethod
    def setUpClass(cls):
        cls.crisis = strip_comments(read(CRISIS_EFFECTS))
        cls.triggers = strip_comments(read(TRIGGERS))

    def test_trigger_reads_the_region(self):
        body = squash(block(self.triggers, "nd_dispute_claims_by"))
        self.assertIn("any_scope_state = { is_incorporated = yes state_region = { $TARGET$ = { has_claim = PREV } } }", body)
        self.assertNotIn("has_claim_by", body)

    def test_concession_removes_on_the_region(self):
        body = squash(block(self.crisis, "nd_crisis_concede_claims"))
        self.assertIn("every_scope_state = { limit = { is_incorporated = yes state_region = { scope:nd_target = { has_claim = PREV } } }"
                      " state_region = { remove_claim = scope:nd_target } }", body)
        self.assertNotIn("set_variable", body)

    def test_claims_concession_names_the_whole_region(self):
        for key in ("nd_concession_long_8", "nd_tt_yield_claims", "nd_tt_open_over_claims"):
            self.assertIn("region", loc_value(key), key)

    def test_revalidate_closes_when_no_claim_is_left(self):
        body = block(self.crisis, "nd_crisis_revalidate_dispute")
        i = dispute_var(8).search(body).start()
        branch = squash(body[i:i + 700])
        self.assertIn("has_war_with = scope:nd_target } set_variable = { name = nd_crisis_dispute value = 2 }", branch)
        self.assertIn("NOT = { nd_dispute_claims_by = { TARGET = scope:nd_target } } } nd_crisis_close = { OUTCOME = 10 }", branch)

    def test_ai_warns_only_against_a_rival(self):
        body = squash(block(self.triggers, "nd_ai_would_warn"))
        i = body.index("nd_dispute_claims_by")
        rival = body.rfind("has_diplomatic_pact = { who = $TARGET$ type = rivalry }", 0, i)
        self.assertGreaterEqual(rival, 0)
        # Once as a licence; the orbital licence names it only to exclude it.
        self.assertEqual(body.count("nd_dispute_claims_by") - body.count("NOT = { nd_dispute_claims_by = "), 1)


class TestOrbital(unittest.TestCase):
    """Dispute 10: the target is building an Orbital Battlestation, which
    gives every state its owner holds nuclear defense. Conceding tears the
    construction site down with its progress and freezes new sites for ten
    years; finished levels stay."""

    @classmethod
    def setUpClass(cls):
        cls.crisis = strip_comments(read(CRISIS_EFFECTS))
        cls.triggers = strip_comments(read(TRIGGERS))

    def test_trigger_reads_the_site(self):
        # A site on its Paused method is not a battlestation going up.
        body = squash(block(self.triggers, "nd_dispute_orbital_by"))
        self.assertIn("$TARGET$ = { any_scope_state = { any_scope_building = {"
                      " is_building_type = building_orbital_battlestation_construction_site"
                      " NOT = { has_active_production_method = pm_orbital_battlestation_construction_paused } } } }", body)

    def test_concession_removes_site_and_progress(self):
        body = squash(block(self.crisis, "nd_crisis_concede_orbital"))
        self.assertIn("every_scope_state = { limit = { has_building = building_orbital_battlestation_construction_site }"
                      " set_variable = { name = orbital_battlestation_progress_var value = 0 }"
                      " remove_building = building_orbital_battlestation_construction_site }", body)
        self.assertNotIn("building_orbital_battlestation }", body)

    def test_freeze_is_ten_years_and_read_by_the_site(self):
        body = squash(block(self.crisis, "nd_crisis_concede_orbital"))
        self.assertIn("set_variable = { name = nd_crisis_orbital_freeze value = scope:nd_issuer days = 3650 }", body)
        site = squash(block(block(strip_comments(read(BUILDINGS)),
                                  "REPLACE_OR_CREATE:building_orbital_battlestation_construction_site"), "possible"))
        self.assertIn("custom_tooltip = { text = nd_tt_orbital_frozen owner = { NOT = { has_variable = nd_crisis_orbital_freeze } } }", site)
        self.assertTrue(loc_value("nd_tt_orbital_frozen"))

    def test_not_defensive(self):
        self.assertNotRegex(block(self.triggers, "nd_crisis_issuer_is_defensive"), dispute_var(10))

    def test_ai_great_power_only(self):
        body = squash(block(self.triggers, "nd_ai_would_warn"))
        i = body.index("nd_dispute_orbital_by = { TARGET = $TARGET$ }")
        licence = body[body.rfind("AND = {", 0, i):]
        licence = licence[:licence.index("} # ") if "} # " in licence else len(licence)]
        self.assertIn("country_rank >= rank_value:great_power", licence[:900])
        self.assertEqual(body.count("nd_dispute_orbital_by"), 1)

    def test_finished_levels_stay(self):
        for key in ("nd_concession_long_10", "nd_tt_yield_orbital"):
            self.assertIn("levels", loc_value(key).lower(), key)

    def test_revalidate_only_a_war(self):
        # A site torn down by the target itself can go up again at once, so
        # it doesn't end the crisis (rulings R7).
        body = squash(block(self.crisis, "nd_crisis_revalidate_dispute"))
        self.assertIn("else_if = { limit = { var:nd_crisis_dispute = 10 } if = { limit = { has_war_with = scope:nd_target }"
                      " set_variable = { name = nd_crisis_dispute value = 2 } } }", body)


def hostile_covert_types():
    """(short name, action) of every hostile covert operation, from the pact
    list the covert system's own triggers use."""
    pacts = block(strip_comments(read(COVERT_TRIGGERS)), "is_covert_operation_pact")
    actions = re.findall(r"is_diplomatic_action_type = (covert_(\w+)_action)", pacts)
    return [(short, action) for action, short in actions if short != "counterintel_support"]


class TestCovert(unittest.TestCase):
    """Dispute 9: the target runs an operation against us that we have caught.
    Conceding ends each caught one and bars new hostile ones for ten years."""

    @classmethod
    def setUpClass(cls):
        cls.crisis = strip_comments(read(CRISIS_EFFECTS))
        cls.triggers = strip_comments(read(TRIGGERS))
        cls.actions = strip_comments(read(COVERT_ACTIONS))
        cls.types = hostile_covert_types()

    def test_seventeen_hostile_types(self):
        self.assertEqual(len(self.types), 17)

    def test_dispute_reads_the_issuers_records(self):
        body = squash(block(self.triggers, "nd_dispute_covert_ops_by"))
        self.assertIn("has_variable_list = iw_known_ops any_in_list = { variable = iw_known_ops var:iw_attacker ?= $TARGET$"
                      " NOT = { has_tag = iw_known_counterintel_support } }", body)

    def test_covert_concession_goes_type_by_type(self):
        body = squash(block(self.crisis, "nd_crisis_concede_covert_ops"))
        calls = re.findall(r"nd_crisis_end_known_op = \{ TYPE = (\w+) ACTION = (\w+) \}", body)
        self.assertEqual(sorted(calls), sorted(self.types))
        helper = squash(block(self.crisis, "nd_crisis_end_known_op"))
        for text in (body, helper):
            self.assertNotIn("every_in_list", text)
        for needle in ("has_diplomatic_pact = { who = scope:nd_issuer type = $ACTION$ }",
                       "any_in_list = { variable = iw_known_ops has_tag = iw_known_$TYPE$ var:iw_attacker ?= scope:nd_target }",
                       "remove_diplomatic_pact = { country = scope:nd_issuer type = $ACTION$ }",
                       "covert_op_destroy = { TYPE = $TYPE$ TARGET = scope:nd_issuer }"):
            self.assertIn(needle, helper)

    def test_bar_set_for_ten_years(self):
        body = squash(block(self.crisis, "nd_crisis_concede_covert_ops"))
        self.assertIn("set_variable = { name = nd_crisis_covert_bar value = scope:nd_issuer days = 3650 }", body)

    def test_bar_on_every_hostile_action(self):
        bar = "custom_tooltip = { text = nd_tt_covert_conceded NOT = { var:nd_crisis_covert_bar ?= scope:target_country } }"
        for _short, action in self.types:
            self.assertIn(bar, squash(block(block(self.actions, action), "possible")), action)
        self.assertTrue(loc_value("nd_tt_covert_conceded"))

    def test_no_bar_on_counterintel_support(self):
        self.assertNotIn("nd_crisis_covert_bar", block(self.actions, "covert_counterintel_support_action"))

    def test_ai_warns_only_against_a_rival(self):
        body = squash(block(self.triggers, "nd_ai_would_warn"))
        i = body.index("nd_dispute_covert_ops_by")
        self.assertGreaterEqual(body.rfind("has_diplomatic_pact = { who = $TARGET$ type = rivalry }", 0, i), 0)
        # Once as a licence; the orbital licence names it only to exclude it.
        self.assertEqual(body.count("nd_dispute_covert_ops_by") - body.count("NOT = { nd_dispute_covert_ops_by = "), 1)

    def test_revalidate_only_a_war(self):
        body = squash(block(self.crisis, "nd_crisis_revalidate_dispute"))
        self.assertIn("else_if = { limit = { var:nd_crisis_dispute = 9 } if = { limit = { has_war_with = scope:nd_target }"
                      " set_variable = { name = nd_crisis_dispute value = 2 } } }", body)

    def test_uncaught_operations_go_on(self):
        for key in ("nd_concession_long_9", "nd_tt_yield_covert_ops"):
            self.assertIn("caught", loc_value(key), key)


class TestDeployment(unittest.TestCase):
    """Dispute 7: the target's weapons based in a country next to us, its
    nuclear guarantee over one, or its missile defense in a state next to
    ours. Conceding leaves those treaties whole (no break penalties), switches
    the missile defense off and bars all three for ten years."""

    @classmethod
    def setUpClass(cls):
        cls.crisis = strip_comments(read(CRISIS_EFFECTS))
        cls.triggers = strip_comments(read(TRIGGERS))
        cls.effects = strip_comments(read(DETERRENCE_EFFECTS))

    def test_three_clauses(self):
        body = squash(block(self.triggers, "nd_dispute_deployment_by"))
        self.assertIn("save_temporary_scope_as = nd_dd_self", body)
        # Basing and guarantees read live, the same articles the concession
        # leaves, so a day after it the self-check sees the result (the
        # weekly nd_based_near list would still name the guest).
        self.assertIn("$TARGET$ = { any_scope_treaty = { any_scope_article = { OR = { has_type = nuclear_basing has_type = nuclear_guarantee }"
                      " source_country = $TARGET$ target_country = { NOT = { THIS = scope:nd_dd_self }"
                      " is_adjacent_to_country = scope:nd_dd_self } } } }", body)
        self.assertNotIn("nd_based_near", body)
        self.assertIn("nd_state_has_missile_defense = yes any_neighbouring_state = { owner = scope:nd_dd_self }", body)
        md = squash(block(self.triggers, "nd_state_has_missile_defense"))
        for pm in MISSILE_DEFENSE:
            self.assertIn("has_active_production_method = " + pm, md)
        self.assertIn("is_building_type = building_military_base", md)

    def test_no_umbrella_clause(self):
        body = block(self.triggers, "nd_dispute_deployment_by")
        self.assertNotIn("umbrella", body)
        self.assertNotIn("has_strategic_adjacency", body)

    def test_concession_withdraws_without_penalties(self):
        body = squash(block(self.crisis, "nd_crisis_concede_deployment"))
        self.assertIn("every_scope_treaty = { limit = { any_scope_article = { OR = { has_type = nuclear_basing has_type = nuclear_guarantee }"
                      " source_country = scope:nd_target target_country = { NOT = { THIS = scope:nd_issuer }"
                      " is_adjacent_to_country = scope:nd_issuer } } } withdraw = { country = scope:nd_target } }", body)
        self.assertNotIn("apply_break_penalties", body)
        for key in ("nd_concession_long_7", "nd_tt_yield_deployment"):
            self.assertIn("treaty", loc_value(key), key)
            self.assertIn("no penalt", loc_value(key), key)

    def test_concession_switches_both_methods_off(self):
        body = squash(block(self.crisis, "nd_crisis_concede_deployment"))
        self.assertIn("every_scope_state = { limit = { nd_state_has_missile_defense = yes any_neighbouring_state = { owner = scope:nd_issuer } }"
                      " nd_missile_defense_off = yes }", body)
        off = squash(block(self.effects, "nd_missile_defense_off"))
        self.assertIn("activate_production_method = { building_type = building_military_base production_method = pm_no_missile_defense }", off)

    def test_bar_set_for_ten_years(self):
        body = squash(block(self.crisis, "nd_crisis_concede_deployment"))
        self.assertIn("set_variable = { name = nd_crisis_deploy_bar value = scope:nd_issuer days = 3650 }", body)

    def test_articles_refuse_a_barred_guest(self):
        bar = ("custom_tooltip = { text = nd_tt_deploy_barred scope:source_country = { NOT = { var:nd_crisis_deploy_bar ?= {"
               " is_adjacent_to_country = scope:target_country } } } }")
        for path, name in ((BASING, "nuclear_basing"), (GUARANTEE, "nuclear_guarantee")):
            ratify = squash(block(block(strip_comments(read(path)), name), "can_ratify"))
            self.assertIn(bar, ratify, name)
        self.assertTrue(loc_value("nd_tt_deploy_barred"))

    def test_deploy_bar_switches_batteries_off_weekly(self):
        self.assertIn("nd_deploy_bar_enforce = yes", block(self.effects, "nd_weekly_update"))
        body = squash(block(self.effects, "nd_deploy_bar_enforce"))
        self.assertIn("has_variable = nd_crisis_deploy_bar", body)
        self.assertIn("every_scope_state = { limit = { nd_state_has_missile_defense = yes any_neighbouring_state = { owner = scope:nd_dbe_issuer } }"
                      " nd_missile_defense_off = yes }", body)

    def test_reach_rebuilt_after_the_concession(self):
        body = squash(block(self.crisis, "nd_crisis_concede_deployment"))
        self.assertIn("trigger_event = { id = nuclear_weapon_events.32 days = 1 }", body)
        # Our warning time comes back at once, not at the next weekly rebuild.
        self.assertIn("scope:nd_issuer = { if = { limit = { has_variable_list = nd_based_near }"
                      " remove_list_variable = { name = nd_based_near target = scope:nd_target } } }", body)

    def test_ai_warns_only_against_a_rival(self):
        body = squash(block(self.triggers, "nd_ai_would_warn"))
        i = body.index("nd_dispute_deployment_by")
        self.assertGreaterEqual(body.rfind("has_diplomatic_pact = { who = $TARGET$ type = rivalry }", 0, i), 0)
        # Once as a licence; the orbital licence names it only to exclude it.
        self.assertEqual(body.count("nd_dispute_deployment_by") - body.count("NOT = { nd_dispute_deployment_by = "), 1)

    def test_revalidate_only_a_war(self):
        body = squash(block(self.crisis, "nd_crisis_revalidate_dispute"))
        self.assertIn("else_if = { limit = { var:nd_crisis_dispute = 7 } if = { limit = { has_war_with = scope:nd_target }"
                      " set_variable = { name = nd_crisis_dispute value = 2 } } }", body)


class TestAILicences(unittest.TestCase):
    """The AI's warnings over codes 7–10 (rulings R8, revised in the final
    review): licensed by the code the crisis would classify as, not the
    dispute alone; never a bluff; code 10 only against a hostile country."""

    @classmethod
    def setUpClass(cls):
        cls.triggers = strip_comments(read(TRIGGERS))
        cls.warn = squash(block(cls.triggers, "nd_ai_would_warn"))

    def licence(self, trigger):
        i = self.warn.index(trigger + " = { TARGET = $TARGET$ }")
        start = self.warn.rfind("AND = { ", 0, i)
        # The licence's own AND block, brace-matched.
        depth, j = 0, start
        while True:
            depth += self.warn[j] == "{"
            depth -= self.warn[j] == "}"
            j += 1
            if depth == 0 and self.warn[j - 1] == "}":
                return self.warn[start:j]

    def test_weightier_codes_listed_in_order(self):
        body = squash(block(self.triggers, "nd_dispute_weightier_than_7"))
        before = [d[1] for d in DISPUTES[:[d[0] for d in DISPUTES].index(7)]]
        self.assertEqual(re.findall(r"(nd_dispute_\w+) = \{ TARGET = \$TARGET\$ \}", body), before)

    def test_not_when_a_weightier_code_holds(self):
        for trigger in ("nd_dispute_deployment_by", "nd_dispute_orbital_by"):
            self.assertIn("NOT = { nd_dispute_weightier_than_7 = { TARGET = $TARGET$ } }", self.licence(trigger), trigger)
        orbital = self.licence("nd_dispute_orbital_by")
        for trigger in ("nd_dispute_deployment_by", "nd_dispute_claims_by", "nd_dispute_covert_ops_by"):
            self.assertIn("NOT = { " + trigger + " = { TARGET = $TARGET$ } }", orbital, trigger)

    def test_never_a_bluff(self):
        for trigger in ("nd_dispute_deployment_by", "nd_dispute_orbital_by"):
            self.assertIn("OR = { nd_threat_backed = { TARGET = $TARGET$ } nd_threat_uncertain = { TARGET = $TARGET$ } }",
                          self.licence(trigger), trigger)

    def test_orbital_only_against_a_hostile_country(self):
        orbital = self.licence("nd_dispute_orbital_by")
        self.assertIn("OR = { has_diplomatic_pact = { who = $TARGET$ type = rivalry }"
                      " has_attitude = { who = $TARGET$ attitude = antagonistic }"
                      " has_attitude = { who = $TARGET$ attitude = belligerent }"
                      " has_attitude = { who = $TARGET$ attitude = domineering } }", orbital)


class TestFinalReviewFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.crisis = strip_comments(read(CRISIS_EFFECTS))
        cls.triggers = strip_comments(read(TRIGGERS))
        cls.effects = strip_comments(read(DETERRENCE_EFFECTS))
        cls.events = strip_comments(read(CRISIS_EVENTS))

    def test_ai_keeps_an_ally_over_a_deployment(self):
        body = squash(block(self.triggers, "nd_concession_costs_an_alliance"))
        for needle in ("nd_crisis_dispute_is = { D = 7 }", "has_type = alliance", "has_type = defensive_pact",
                       "OR = { has_type = nuclear_basing has_type = nuclear_guarantee }",
                       "is_adjacent_to_country = scope:nd_issuer"):
            self.assertIn(needle, body)
        from test_nuclear_deterrence import option_body
        for option in ("nuclear_crisis.1.a", "nuclear_crisis.5.a"):
            chance = squash(block(option_body(self.events, option), "ai_chance"))
            self.assertIn("modifier = { trigger = { nd_concession_costs_an_alliance = yes } factor = 0 }", chance, option)

    def test_bars_lapse_in_a_war_with_the_issuer(self):
        weekly = block(self.effects, "nd_weekly_update")
        self.assertLess(weekly.index("nd_crisis_bars_void_in_war = yes"), weekly.index("nd_deploy_bar_enforce = yes"))
        body = squash(block(self.effects, "nd_crisis_bars_void_in_war"))
        for bar in ("nd_crisis_deploy_bar", "nd_crisis_covert_bar", "nd_crisis_orbital_freeze"):
            self.assertIn("limit = { var:" + bar + " ?= { has_war_with = scope:nd_bv_self } } remove_variable = " + bar, body)

    def test_a_player_hears_of_the_switch_off(self):
        body = squash(block(self.effects, "nd_deploy_bar_enforce"))
        self.assertIn("var:nd_crisis_deploy_bar ?= { save_scope_as = nd_dbe_issuer }", body)
        self.assertIn("post_notification = nd_deploy_bar_enforced", body)
        self.assertIn("is_ai = no", body)
        messages = strip_comments(read(ROOT / "common/messages/extra_messages.txt"))
        self.assertRegex(messages, r"(?m)^nd_deploy_bar_enforced = \{")
        for suffix in ("_name", "_desc", "_tooltip"):
            self.assertTrue(loc_value("notification_nd_deploy_bar_enforced" + suffix), suffix)

    def test_covert_helper_acts_on_the_record(self):
        helper = block(self.crisis, "nd_crisis_end_known_op")
        limit = squash(block(helper, "limit"))
        self.assertNotIn("has_diplomatic_pact", limit)
        self.assertIn("iw_known_$TYPE$", limit)
        h = squash(helper)
        self.assertIn("if = { limit = { has_diplomatic_pact = { who = scope:nd_issuer type = $ACTION$ } }"
                      " remove_diplomatic_pact = { country = scope:nd_issuer type = $ACTION$ } }", h)
        self.assertIn("scope:nd_issuer = { covert_watch_forget = { ATTACKER = scope:nd_target TYPE = $TYPE$ } }", h)

    def test_script_guarantees_read_the_bar(self):
        cand = squash(block(self.triggers, "nd_proliferation_guarantee_candidate"))
        self.assertIn("NOT = { var:nd_crisis_deploy_bar ?= { is_adjacent_to_country = scope:nd_pg_beneficiary } }", cand)
        bp = squash(block(strip_comments(read(ROOT / "common/scripted_triggers/nuclear_custody_triggers.txt")),
                          "nd_bp_guarantor_valid"))
        self.assertIn("NOT = { var:nd_crisis_deploy_bar ?= { is_adjacent_to_country = $STATE$ } }", bp)

    def test_demands_speak_of_the_issuer_in_the_third_person(self):
        # Spliced into the target's events ("…has warned our government…").
        for code in CODES:
            self.assertNotRegex(loc_value(f"nd_crisis_demand_{code}"), r"\b(we|us|our)\b", code)

    def test_eligibility_line_needs_no_rival_for_the_new_disputes(self):
        text = loc_value("nd_tt_has_dispute")
        for phrase in ("a rival's forces deployed", "a rival's claims", "a rival's covert operations"):
            self.assertNotIn(phrase, text)

    def test_legend_says_what_the_concessions_do(self):
        legend = loc_value("nd_w_crisis_actions_legend")
        self.assertNotIn("halts its battlestation", legend)
        self.assertIn("battlestation site", legend)

    def test_basing_bar_line_says_which_country(self):
        self.assertIn("conceded to", loc_value("nd_tt_deploy_barred"))



class TestTradeDecision(unittest.TestCase):
    """Phase 4c: every dispute either trades (a same-code mirror, its own
    branch at every trade site) or is listed as not trading."""

    def test_every_dispute_decides_on_trades(self):
        from test_nuclear_trades import NO_TRADE, TRADES

        self.assertFalse(set(TRADES) & NO_TRADE)
        self.assertEqual(set(TRADES) | NO_TRADE, set(CODES))


if __name__ == "__main__":
    unittest.main()
