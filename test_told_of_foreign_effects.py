"""A country is told of what another country's choice, or a hidden pulse, did
to it (#1554-#1559; the rule is scripting_best_practices.md § "An Effect That
Changes Another Country Tells That Country").

Each case here was silent before: the effect ran on a country that had no
option open and saw no tooltip. A large effect now sends an event whose one
option lists what was done (shown, not run again); a small one posts a feed
notice. These tests hold the wiring: that the effect still sends its word, to
the right country, and that the event or notice has its definition and text.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOC = ROOT / "localization" / "english"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def block(text, name):
    """The body of the top-level `name = { ... }` block."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"no block {name}")
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def inner(text, opener):
    """The body of the first `opener` block inside text (`opener` ends in `{`)."""
    start = text.index(opener) + len(opener)
    depth, i = 1, start
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[start:i - 1]


def event_trigger(body):
    """An event's own trigger, not a triggered_desc's: the one at one tab."""
    return inner(body, "\n\ttrigger = {")


def loc_keys():
    keys = {}
    for path in LOC.glob("*_l_english.yml"):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r'\s+([\w\.\-]+):\d*\s+"(.*)"\s*(?:#.*)?$', line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


MESSAGES = strip_comments(read("common/messages/extra_messages.txt"))
KEYS = loc_keys()

NOTICES = (
    "un_decolonization_pressure_notice", "un_headquarters_host_notice",
    "un_bloc_vacuum_notice", "un_dissolution_vacuum_notice",
    "te_mon_swap_settled_notice", "te_mon_swap_repaid_notice",
    "irr_cultural_ties_notice",
    "covert_exposure_repeat_notice", "covert_backlash_public_notice",
)

# event -> its file, and the keys its script names
EVENTS = {
    "minor_events_timelineextended.10": "events/minor_events.txt",
    "un_vote.8": "events/un_vote_events.txt",
    "te_union.2": "events/te_monetary_arrangement_events.txt",
    "te_inflation.2": "events/te_inflation_events.txt",
    "irredentism.12": "events/irredentism_events.txt",
    "irredentism.13": "events/irredentism_events.txt",
    "te_pb_summit.2": "events/te_power_bloc_summit_events.txt",
    "nuclear_weapon_events.33": "events/nuclear_weapon_events.txt",
    "te_orbital_debris.2": "events/te_orbital_debris_events.txt",
}


def event(event_id):
    return strip_comments(block(read(EVENTS[event_id]), event_id))


class NoticesAreDefined(unittest.TestCase):
    def test_every_notice_has_a_message_and_its_three_texts(self):
        for name in NOTICES:
            with self.subTest(notice=name):
                self.assertRegex(MESSAGES, r"(?m)^" + name + r" = \{")
                for suffix in ("name", "desc", "tooltip"):
                    self.assertIn(f"notification_{name}_{suffix}", KEYS)

    def test_every_notice_is_posted(self):
        script = "".join(strip_comments(p.read_text(encoding="utf-8-sig"))
                         for d in ("common/scripted_effects", "events")
                         for p in (ROOT / d).glob("*.txt"))
        for name in NOTICES:
            with self.subTest(notice=name):
                self.assertIn(f"post_notification = {name}", script)


class EventsAreWhole(unittest.TestCase):
    def test_each_event_has_a_picture_and_one_default_option(self):
        for event_id in EVENTS:
            with self.subTest(event=event_id):
                body = event(event_id)
                self.assertIn("event_image", body)
                self.assertEqual(body.count("option = {"), 1)
                self.assertIn("default_option = yes", body)

    def test_each_text_key_an_event_names_exists(self):
        for event_id in EVENTS:
            body = event(event_id)
            for key in set(re.findall(re.escape(event_id) + r"\.[\w\.]+", body)):
                with self.subTest(key=key):
                    self.assertIn(key, KEYS)

    def test_the_options_change_nothing(self):
        """The effect has already run where it was decided. An option that ran
        it again would double a modifier or a payment, so everything an option
        does sits in show_as_tooltip or is a custom_tooltip."""
        for event_id in EVENTS:
            with self.subTest(event=event_id):
                option = inner(event(event_id), "option = {")
                shown = option
                while "show_as_tooltip = {" in shown:
                    body = inner(shown, "show_as_tooltip = {")
                    shown = shown.replace("show_as_tooltip = {" + body + "}", "", 1)
                for effect in ("add_modifier", "change_relations", "add_treasury",
                               "activate_law", "remove_building", "set_variable",
                               "trigger_event", "add_radicals"):
                    self.assertNotIn(effect, shown)


class StateCollapse(unittest.TestCase):
    def test_the_collapse_step_reports_itself(self):
        entry = strip_comments(block(read("common/journal_entries/timeline_extended_journal_entries.txt"),
                                     "je_state_collapse"))
        pulse = inner(entry, "on_weekly_pulse = {")
        step = pulse[pulse.index("reset_all_institutions_and_ministries = yes"):]
        self.assertIn("trigger_event = { id = minor_events_timelineextended.10 popup = yes }", step)

    def test_the_event_lists_what_was_lost(self):
        body = event("minor_events_timelineextended.10")
        for key in ("state_collapse_buildings_lost_tt", "state_collapse_institutions_reset_tt"):
            self.assertIn(key, body)
            self.assertIn(key, KEYS)
        self.assertIn("name = failed_state_modifier", inner(body, "show_as_tooltip = {"))

    def test_the_tooltip_names_every_building_the_step_removes(self):
        removed = re.findall(r"remove_building = (\w+)",
                             block(read("common/scripted_effects/extra_effects.txt"),
                                   "state_collapse_remove_infrastructure"))
        names = {"building_barrack": "Barracks", "building_naval_administration": "Naval Administration",
                 "building_naval_fortification": "Naval Fortification",
                 "building_naval_logistics_center": "Naval Logistics Center",
                 "building_military_base": "Military Base", "building_port": "Port",
                 "building_railway": "Railway", "building_university": "University",
                 "building_government_administration": "Government Administration"}
        self.assertEqual(set(removed), set(names))
        for name in names.values():
            self.assertIn(name, KEYS["state_collapse_buildings_lost_tt"])

    def test_the_law_reset_is_not_marked_for_a_notice_per_law(self):
        reset = strip_comments(block(read("common/scripted_effects/extra_effects.txt"),
                                     "reset_all_institutions_and_ministries"))
        self.assertNotIn("te_law_sweep_replacing", reset)


class UnitedNations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vote2 = strip_comments(block(read("events/un_vote_events.txt"), "un_vote.2"))
        cls.vote8 = event("un_vote.8")
        cls.tells = strip_comments(block(read("common/scripted_triggers/un_resolution_triggers.txt"),
                                         "un_resolution_tells_target"))

    def test_the_trigger_covers_the_verdicts_and_spares_an_accepted_one(self):
        for term in ("has_tag = un_res_passed", "has_tag = un_topic_expulsion",
                     "has_tag = un_topic_condemn", "has_tag = un_topic_sanctions",
                     "NOT = { has_tag = un_res_target_accepted }"):
            self.assertIn(term, self.tells)

    def test_the_target_gets_the_verdict_in_place_of_the_members_notice(self):
        dispatch = self.vote2[self.vote2.index("trigger_event = { id = un_vote.3 }") - 700:]
        members = dispatch[:dispatch.index("trigger_event = { id = un_vote.3 }")]
        self.assertIn("THIS = scope:un_vote_target", members)
        self.assertIn("un_resolution_tells_target = yes", members)
        self.assertRegex(dispatch, r"un_resolution_tells_target = yes[\s\S]{0,200}"
                                   r"scope:un_vote_target = \{ trigger_event = \{ id = un_vote\.8 \} \}")

    def test_the_verdict_needs_no_membership(self):
        trigger = event_trigger(self.vote8)
        self.assertNotIn("un_member_modifier", trigger)
        self.assertNotIn("un_representation_suspended", trigger)

    def test_the_verdict_shows_each_modifier_the_vote_gave(self):
        shown = inner(self.vote8, "show_as_tooltip = {")
        for modifier, days in (("un_condemned_modifier", "long_modifier_time"),
                               ("un_non_binding_rebuke_modifier", "normal_modifier_time"),
                               ("un_sanctions_voluntary_target_modifier", "normal_modifier_time"),
                               ("un_withdrawal_penalty_modifier", "long_modifier_time")):
            with self.subTest(modifier=modifier):
                # the same line un_vote.2 runs on the target
                given = re.search(r"add_modifier = \{\s*name = " + modifier + r"[^}]*\}", self.vote2).group(0)
                self.assertIn(f"days = {days}", given)
                self.assertIn(re.sub(r"\s+", " ", given), re.sub(r"\s+", " ", shown))
        self.assertIn("un_teeth_condemn_by_tier = yes", shown)
        self.assertIn("name = un_sanctions_target_modifier multiplier = un_enforcement", shown)

    def test_the_decolonization_declaration_tells_each_colonial_power(self):
        self.assertRegex(self.vote2, r"name = un_decolonization_pressure_modifier[^}]*\}\s*"
                                     r"post_notification = un_decolonization_pressure_notice")

    def test_a_new_headquarters_host_is_told(self):
        assign = strip_comments(block(read("common/scripted_effects/un_hq_effects.txt"), "un_hq_assign_host"))
        self.assertEqual(assign.count("un_hq_make_host = yes"), 2)
        self.assertEqual(len(re.findall(r"un_hq_make_host = yes\s*post_notification = un_headquarters_host_notice",
                                        assign)), 2)

    def test_bloc_leaders_hear_of_the_vacuum(self):
        ladder = strip_comments(read("common/scripted_effects/un_ladder_effects.txt"))
        update = block(ladder, "un_ladder_bloc_vacuum_update")
        self.assertRegex(update, r"add_modifier = \{ name = un_bloc_vacuum_modifier \} \}\s*"
                                 r"post_notification = un_bloc_vacuum_notice")
        # once, when the bloc gains it: not every month it holds it
        self.assertRegex(update, r"is_power_bloc_leader = yes\s*power_bloc \?= \{ NOT = \{ has_modifier = "
                                 r"un_bloc_vacuum_modifier \} \}")
        self.assertRegex(ladder, r"name = un_dissolution_vacuum_modifier[\s\S]{0,80}"
                                 r"post_notification = un_dissolution_vacuum_notice")


class Monetary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arr = strip_comments(read("common/scripted_effects/te_monetary_arrangement_effects.txt"))
        cls.union = strip_comments(read("common/scripted_effects/te_monetary_union_effects.txt"))

    def test_a_forced_exit_sends_the_event(self):
        discover = block(self.arr, "te_monetary_discover_arrangements")
        forced = discover[discover.index("te_mon_bloc_has_common_currency = no"):]
        forced = forced[:forced.index("te_mon_is_command = no")]
        self.assertIn("te_mon_effect_union_exit_costs = yes", forced)
        self.assertIn("trigger_event = { id = te_union.2 popup = yes }", forced)
        # the leader is named while te_mon_anchor still names it
        self.assertLess(forced.index("name = te_union_exit_from value = var:te_mon_anchor"),
                        forced.index("te_mon_effect_union_exit_costs = yes"))

    def test_a_chosen_exit_does_not(self):
        """Its tooltip said everything before the click."""
        for name in ("te_mon_effect_union_exit", "te_mon_effect_union_exit_costs"):
            self.assertNotIn("te_union.2", block(self.union, name))

    def test_the_event_shows_the_premium_the_exit_gave(self):
        costs = block(self.union, "te_mon_effect_union_exit_costs")
        given = re.sub(r"\s+", " ", re.search(r"add_modifier = \{\s*name = te_mon_union_exit_premium[^}]*\}",
                                             costs).group(0))
        self.assertIn(given, re.sub(r"\s+", " ", inner(event("te_union.2"), "show_as_tooltip = {")))

    def test_the_forced_exit_event_has_no_same_tick_modifier_gate(self):
        """It fires in the effect that adds the premium, where has_modifier
        does not see it yet: a gate on it would drop the event."""
        self.assertNotIn("trigger = {\n\t\thas_modifier", event("te_union.2"))
        self.assertNotIn("has_modifier = te_mon_union_exit_premium", event("te_union.2"))

    def test_a_settled_swap_line_tells_both_sides(self):
        settle = block(self.arr, "te_mon_effect_swap_settle")
        self.assertIn("name = te_mon_swap_settled_amount value = var:te_mon_swap_drawn", settle)
        self.assertLess(settle.index("te_mon_swap_settled_amount"), settle.index("name = te_mon_swap_drawn value = 0"))
        provider = inner(settle[settle.index("save_scope_as = te_mon_swap_settle_recipient"):],
                         "var:te_mon_swap_provider = {")
        self.assertIn("post_notification = te_mon_swap_repaid_notice", provider)
        self.assertTrue(settle.rstrip().endswith("post_notification = te_mon_swap_settled_notice"))
        for name in ("te_mon_swap_settled_notice", "te_mon_swap_repaid_notice"):
            self.assertIn("te_mon_swap_settled_amount", KEYS[f"notification_{name}_desc"])

    def test_a_dollarized_country_hears_what_its_new_money_costs(self):
        on_actions = strip_comments(read("common/on_actions/extra_on_actions.txt"))
        self.assertRegex(on_actions, r"name = te_mon_dollarised value = 0 \}\s*te_mon_effect_new_currency = yes\s*"
                                     r"trigger_event = \{ id = te_inflation\.2 popup = yes \}")
        effect = block(strip_comments(read("common/scripted_effects/te_monetary_effects.txt")),
                       "te_mon_effect_new_currency")
        given = re.sub(r"\s+", " ", re.search(r"add_modifier = \{\s*name = te_mon_currency_reform_premium[^}]*\}",
                                             effect).group(0))
        self.assertIn(given, re.sub(r"\s+", " ", inner(event("te_inflation.2"), "show_as_tooltip = {")))


class Irredentism(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = strip_comments(read("events/irredentism_events.txt"))
        cls.ruling = block(cls.text, "irredentism.8")

    def test_both_countries_hear_either_ruling(self):
        bless = self.ruling[self.ruling.index("name = irredentism.8.a"):self.ruling.index("name = irredentism.8.b")]
        forbid = self.ruling[self.ruling.index("name = irredentism.8.b"):]
        for option, answer in ((bless, "irredentism.12"), (forbid, "irredentism.13")):
            with self.subTest(answer=answer):
                self.assertIn(f"scope:irr_proposed_target = {{ trigger_event = {{ id = {answer} days = 1 }} }}", option)
                self.assertIn(f"scope:irr_unifier = {{ trigger_event = {{ id = {answer} days = 1 }} }}", option)
                # a leader that is itself the proposer has just ruled
                self.assertIn("NOT = { scope:irr_unifier = ROOT }", option)

    def test_each_ruling_reads_from_either_side(self):
        for event_id in ("irredentism.12", "irredentism.13"):
            body = event(event_id)
            self.assertIn(f"desc = {event_id}.d_target", body)
            self.assertIn(f"desc = {event_id}.d_unifier", body)

    def test_the_forbidden_country_is_shown_its_modifier(self):
        body = event("irredentism.13")
        self.assertIn("name = irr_union_forbidden_modifier", inner(body, "show_as_tooltip = {"))

    def test_funded_cultural_ties_tell_the_neighbor(self):
        first = block(self.text, "irredentism.1")
        option = first[first.index("name = irredentism.1.b"):first.index("name = irredentism.1.c")]
        self.assertLess(option.index("save_scope_as = irr_ties_funder"),
                        option.index("post_notification = irr_cultural_ties_notice"))
        self.assertIn("irr_ties_funder", KEYS["notification_irr_cultural_ties_notice_desc"])


class Summits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grant = strip_comments(block(read("common/scripted_effects/te_power_bloc_summit_effects.txt"),
                                         "te_pb_summit_grant_member_initiative"))
        cls.summit = strip_comments(block(read("events/te_power_bloc_summit_events.txt"), "te_pb_summit.1"))
        cls.told = event("te_pb_summit.2")

    def test_every_member_but_the_leader_is_sent_the_communique(self):
        self.assertIn("save_scope_as = te_pb_summit_leader", self.grant)
        tell = self.grant[self.grant.index("NOT = { this = scope:te_pb_summit_leader }"):]
        self.assertIn("set_variable = { name = $MODIFIER$_told days = 30 }", tell)
        self.assertIn("trigger_event = { id = te_pb_summit.2 days = 1 }", tell)

    def test_every_member_initiative_has_its_text_and_its_line(self):
        initiatives = set(re.findall(r"te_pb_summit_grant_member_initiative = \{ MODIFIER = (\w+) \}", self.summit))
        self.assertEqual(len(initiatives), 6)
        for modifier in initiatives:
            with self.subTest(modifier=modifier):
                short = modifier.removeprefix("te_pb_summit_")
                self.assertIn(f"has_variable = {modifier}_told", event_trigger(self.told))
                self.assertIn(f"te_pb_summit.2.d_{short}", KEYS)
                self.assertRegex(inner(self.told, "show_as_tooltip = {"),
                                 r"has_variable = " + modifier + r"_told \}\s*add_modifier = \{\s*name = "
                                 + modifier + r"\s*days = long_modifier_time")
                self.assertIn(f"remove_variable = {modifier}_told", inner(self.told, "after = {"))


class SmallerCases(unittest.TestCase):
    def test_a_demand_for_reparations_is_answered_either_way(self):
        demand = strip_comments(block(read("events/nuclear_weapon_events.txt"), "nuclear_weapon_events.27"))
        pay = demand[demand.index("name = nuclear_weapon_events.27.a"):demand.index("name = nuclear_weapon_events.27.b")]
        refuse = demand[demand.index("name = nuclear_weapon_events.27.b"):]
        for option, answer in ((pay, 1), (refuse, 2)):
            victim = inner(option, "scope:nd_claim_victim = {")
            self.assertIn(f"name = nd_claim_answer value = {answer} days = 60", victim)
            self.assertIn("trigger_event = { id = nuclear_weapon_events.33 popup = yes }", victim)
        self.assertIn("name = nd_claim_paid value = nd_loose_compensation_value", pay)
        self.assertNotIn("nd_claim_paid", refuse)

    def test_the_answer_shows_the_sum_and_forgets_it(self):
        body = event("nuclear_weapon_events.33")
        self.assertIn("add_treasury = var:nd_claim_paid", inner(body, "show_as_tooltip = {"))
        self.assertIn("nd_claim_paid", KEYS["nuclear_weapon_events.33.d_paid"])
        for name in ("nd_claim_answer", "nd_claim_paid"):
            self.assertIn(f"remove_variable = {name}", inner(body, "after = {"))

    def test_the_target_of_an_anti_satellite_strike_is_told(self):
        strike = strip_comments(block(read("common/scripted_effects/te_orbital_debris_effects.txt"),
                                      "te_asat_strike_effect"))
        self.assertLess(strike.index("save_scope_as = te_asat_striker"),
                        strike.index("scope:te_asat_target = { trigger_event = { id = te_orbital_debris.2 popup = yes } }"))
        self.assertIn("te_asat_striker", KEYS["te_orbital_debris.2.d"])

    def test_the_strike_event_repeats_the_disruption_ladder(self):
        strike = strip_comments(block(read("common/scripted_effects/te_orbital_debris_effects.txt"),
                                      "te_asat_strike_effect"))
        ladder = re.findall(r"add_modifier = \{\s*name = te_orbital_network_disrupted([^}]*)\}", strike)
        shown = re.findall(r"add_modifier = \{\s*name = te_orbital_network_disrupted([^}]*)\}",
                           inner(event("te_orbital_debris.2"), "show_as_tooltip = {"))
        squash = lambda rows: [re.sub(r"\s+", " ", r).strip() for r in rows]  # noqa: E731
        self.assertEqual(len(ladder), 4)
        self.assertEqual(squash(shown), squash(ladder))

    def test_an_exposure_the_defender_event_skips_still_reaches_it(self):
        attacker = strip_comments(block(read("events/covert_warfare_events.txt"), "covert_warfare.1"))
        after = attacker[attacker.index("covert_backlash_public = yes"):]
        self.assertRegex(after, r"has_variable = iw_expose_response \}\s*scope:detected_by_country = \{\s*"
                                r"covert_exposure_response_apply = yes\s*covert_exposure_tell_public = yes")
        self.assertRegex(after, r"scope:detected_by_country = \{ has_variable = iw_defender_event_cooldown \} \}\s*"
                                r"scope:detected_by_country = \{ covert_exposure_tell_repeat = yes \}")
        # the cooldown the notice stands in for is the one covert_warfare.2 sets
        defender = strip_comments(block(read("events/covert_warfare_events.txt"), "covert_warfare.2"))
        self.assertIn("NOT = { has_variable = iw_defender_event_cooldown }", event_trigger(defender))

    def test_the_covert_notices_name_the_attacker(self):
        effects = strip_comments(read("common/scripted_effects/covert_warfare_effects.txt"))
        for name, notice in (("covert_exposure_tell_public", "covert_backlash_public_notice"),
                             ("covert_exposure_tell_repeat", "covert_exposure_repeat_notice")):
            body = block(effects, name)
            self.assertLess(body.index("ROOT = { save_scope_as = iw_exposed_by }"),
                            body.index(f"post_notification = {notice}"))
            self.assertIn("iw_exposed_by", KEYS[f"notification_{notice}_desc"])
        self.assertIn("has_variable = iw_last_exposed_public", block(effects, "covert_exposure_tell_public"))

    def test_a_colonial_subjects_liberty_desire_modifiers_say_why(self):
        for band in ("strained", "crumbling", "collapsing"):
            desc = KEYS[f"colonial_overlord_{band}_subject_ld_modifier_desc"]
            self.assertIn("[concept_colonial_stability]", desc)
        self.assertIn("colonial_collapse_subject_unrest_modifier_desc", KEYS)
        # the thresholds the texts give are the ones the entry applies them at
        entry = strip_comments(read("common/journal_entries/je_colonial_empire.txt"))
        for band, below in (("collapsing", 20), ("crumbling", 40), ("strained", 65)):
            self.assertRegex(entry, r'colonial_stability_bar\)" < ' + str(below) + r"[\s\S]{0,200}"
                                    r"colonial_overlord_" + band + "_subject_ld_modifier")
            self.assertIn(f"below {below}", KEYS[f"colonial_overlord_{band}_subject_ld_modifier_desc"])


if __name__ == "__main__":
    unittest.main()
