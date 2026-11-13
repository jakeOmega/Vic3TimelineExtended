"""Rules with an early and a late unlock: the late setting is the system as it was, the early one opens it sooner.

Prompted by Steam Workshop feedback (covert operations long before computers), each of these rules has three
settings (`docs/systems/mod_systems/game_rules.md`): early unlock, late unlock and off. The late setting keeps the
old setting name and flag (`<system>_enabled`), so a save made before keeps it and behaves as it did.

Whether `has_game_rule` reads a second flag on a setting is unverified, so every setting has one flag, named after it,
and script reads the rule through two triggers per system in `common/scripted_triggers/te_rule_setting_triggers.txt`:
`te_<system>_on` (either unlock) and `te_<system>_early`. A bare `has_game_rule = <system>_enabled` anywhere else
would now mean the late setting alone, so this fails on one.

Run: python3 -m pytest test_rule_unlock_settings.py
"""

import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
RULES = ROOT / "common/game_rules/extra_game_rules.txt"
GATES = ROOT / "common/scripted_triggers/te_rule_setting_triggers.txt"
RULES_LOC = ROOT / "localization/english/te_game_rules_l_english.yml"

# rule: (system prefix, gate trigger prefix)
SYSTEMS = {
    "covert_warfare_rule": ("covert_warfare", "te_covert_warfare"),
    "world_war_rule": ("world_war", "te_world_war"),
    "united_nations_rule": ("united_nations", "te_united_nations"),
    "cultural_hegemony_rule": ("cultural_hegemony", "te_cultural_hegemony"),
}


def read(path):
    return Path(path).read_text(encoding="utf-8-sig")


def code(path):
    return re.sub(r"#[^\n]*", "", read(path))


def braced(text, header):
    """The body of the first block whose opening line matches `header` (a regex ending in `{`)."""
    m = re.search(header, text, re.M)
    assert m, header
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def words(text):
    return " ".join(text.split())


def parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(str(path), apply_directives=False)
    return parser.data


def loc(path):
    out = {}
    for line in read(path).splitlines():
        m = re.match(r'\s+([\w.]+):\d* "(.*)"\s*$', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


class RuleSettingsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rules = parse(RULES)
        cls.loc = loc(RULES_LOC)

    def test_three_settings_each_with_one_flag_named_after_it(self):
        for rule, (system, _gate) in SYSTEMS.items():
            with self.subTest(rule=rule):
                body = self.rules[rule][1]
                settings = [k for k in body if k != "default"]
                self.assertEqual(sorted(settings), sorted([f"{system}_early_unlock", f"{system}_enabled",
                                                           f"{system}_disabled"]))
                for setting in settings:
                    self.assertEqual(body[setting][1], {"flag": ("=", setting)}, setting)

    def test_the_default_is_unchanged(self):
        for rule, (system, _gate) in SYSTEMS.items():
            with self.subTest(rule=rule):
                expected = f"{system}_disabled" if system == "world_war" else f"{system}_enabled"
                self.assertEqual(self.rules[rule][1]["default"][1], expected)

    def test_the_gates_read_the_settings(self):
        gates = code(GATES)
        for system, gate in SYSTEMS.values():
            with self.subTest(system=system):
                self.assertEqual(words(braced(gates, rf"^{gate}_on = \{{")),
                                 f"OR = {{ has_game_rule = {system}_enabled has_game_rule = {system}_early_unlock }}")
                self.assertEqual(words(braced(gates, rf"^{gate}_early = \{{")),
                                 f"has_game_rule = {system}_early_unlock")

    def test_no_bare_read_of_a_setting(self):
        for system, _gate in SYSTEMS.values():
            pattern = re.compile(rf"has_game_rule\s*=\s*{system}_(enabled|early_unlock)\b")
            for folder in ("common", "events", "gui"):
                for path in sorted((ROOT / folder).rglob("*")):
                    if path.suffix not in (".txt", ".gui") or path == GATES:
                        continue
                    for n, line in enumerate(code(path).splitlines(), 1):
                        if pattern.search(line):
                            self.fail(f"{path.relative_to(ROOT)}:{n}: read {system}'s rule through its gate in "
                                      f"te_rule_setting_triggers.txt, not has_game_rule ({line.strip()})")

    def test_every_setting_has_a_name_and_a_description(self):
        for system, _gate in SYSTEMS.values():
            for setting in ("early_unlock", "enabled", "disabled"):
                for suffix in ("", "_desc"):
                    key = f"setting_{system}_{setting}{suffix}"
                    self.assertIn(key, self.loc)
            self.assertIn("Early Unlock", self.loc[f"setting_{system}_early_unlock"])
            self.assertIn("Late Unlock", self.loc[f"setting_{system}_enabled"])


# --- Covert Warfare ------------------------------------------------------------------------------------------------

COVERT_JE = ROOT / "common/journal_entries/je_covert_warfare.txt"
COVERT_TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
COVERT_ACTIONS = ROOT / "common/diplomatic_actions/covert_operations.txt"
COVERT_VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
COVERT_ON_ACTIONS = ROOT / "common/on_actions/covert_warfare_on_actions.txt"
MISC_LOC = ROOT / "localization/english/te_miscellaneous_l_english.yml"
TECH_DIR = ROOT / "common/technology/technologies"

# The entry's `possible` before the early unlock (2026-11-08): the late gate, unchanged.
COVERT_LATE_GATE = ("OR = { has_technology_researched = mainframe_computers "
                    "has_technology_researched = computer_networks has_technology_researched = cyber_warfare "
                    "has_technology_researched = quantum_computing "
                    "has_law = law_type:law_ministry_of_intelligence_and_security }")

# Operations an early agency can launch before the late gate: the classic ones, which need no technology.
COVERT_PRE_COMPUTER = {"industrial_espionage", "military_espionage", "infrastructure_sabotage", "cultivate_assets",
                       "counterintel_support"}
# Operations with no technology of their own whose target can't exist before the late gate: a nuclear programme,
# a space race lead, loose nuclear material, a space colony.
COVERT_NEED_A_LATE_TARGET = {"nuclear_sabotage": "iw_target_nuclear_programme_tt",
                             "space_espionage": "iw_target_ahead_in_space_tt",
                             "secure_material": "iw_target_has_loose_material_tt",
                             "incite_autonomy": "iw_target_holds_peopled_colony_tt",
                             "sabotage_colony": "iw_target_holds_space_colony_tt",
                             "survey_defences": "iw_target_holds_space_colony_tt"}


def tech_eras():
    eras = {}
    for path in sorted(TECH_DIR.glob("*.txt")):
        for name, value in parse(path).items():
            body = value[1] if isinstance(value, tuple) else None
            if isinstance(body, dict) and "era" in body:
                eras[name] = int(body["era"][1].split("_")[1])
    return eras


class CovertEarlyUnlockTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.triggers = code(COVERT_TRIGGERS)
        cls.je = code(COVERT_JE)

    def test_late_is_todays_gate(self):
        self.assertEqual(words(braced(self.triggers, r"^covert_warfare_slot_source = \{")), COVERT_LATE_GATE)
        unlocked = braced(self.triggers, r"^covert_warfare_entry_unlocked = \{")
        self.assertEqual(words(braced(unlocked, r"trigger_else = \{")),
                         "custom_tooltip = { text = covert_warfare_unlock_tt covert_warfare_slot_source = yes }")
        self.assertEqual(words(braced(self.je, r"^\tpossible = \{")), "covert_warfare_entry_unlocked = yes")

    def test_early_opens_at_central_archives(self):
        unlocked = braced(self.triggers, r"^covert_warfare_entry_unlocked = \{")
        early = braced(unlocked, r"trigger_if = \{")
        self.assertIn("limit = { te_covert_warfare_early = yes }", words(early))
        self.assertIn("OR = { has_technology_researched = central_archives covert_warfare_slot_source = yes }",
                      words(early))

    def test_the_cap_binds_only_an_early_agency_short_of_the_late_gate(self):
        self.assertEqual(words(braced(self.triggers, r"^covert_agency_limited = \{")),
                         "te_covert_warfare_early = yes NOT = { covert_warfare_slot_source = yes }")
        self.assertRegex(code(COVERT_VALUES), r"(?m)^covert_agency_funding_cap = 2$")
        self.assertEqual(loc(MISC_LOC)["iw_funding_name_2"], "Professional")
        increase = words(braced(self.triggers, r"^covert_possible_increase_funding = \{"))
        self.assertIn("trigger_if = { limit = { covert_agency_limited = yes } custom_tooltip = { "
                      "text = iw_funding_early_cap_tt", increase)
        self.assertIn("var:iw_funding_level < covert_agency_funding_cap", increase)
        # The AI's levels and a level from before a switch are cut to the cap each month.
        self.assertIn("set_variable = { name = iw_funding_level value = covert_agency_funding_cap }", words(self.je))

    def test_early_operations_wait_for_their_technology_or_their_target(self):
        """Before the late gate an early agency launches only what fits its time: the operations whose technology it
        has (each technology gate is era 6 or later) and the classic ones. The rest need a target that can't exist
        yet. A new operation must take one of the three, or the early unlock hands it out in 1850."""
        eras = tech_eras()
        text = code(COVERT_ACTIONS)
        actions = re.findall(r"^covert_(\w+)_action = \{", text, re.M)
        self.assertEqual(len(actions), 18)
        for name in actions:
            with self.subTest(op=name):
                possible = braced(braced(text, rf"^covert_{name}_action = \{{"), r"^\tpossible = \{")
                gate = re.search(r"text = covert_op_tech_\w+_tt\s+has_technology_researched = (\w+)", possible)
                if gate:
                    self.assertGreaterEqual(eras[gate.group(1)], 6, gate.group(1))
                    self.assertNotIn(name, COVERT_PRE_COMPUTER)
                elif name in COVERT_NEED_A_LATE_TARGET:
                    self.assertIn(f"text = {COVERT_NEED_A_LATE_TARGET[name]}", possible)
                else:
                    self.assertIn(name, COVERT_PRE_COMPUTER, "an operation with no technology gate: give it one, "
                                                             "or list it as fit for an early agency")

    def test_switched_to_late_the_early_entry_closes_and_comes_back_at_the_gate(self):
        immediate = words(braced(self.je, r"^\timmediate = \{"))
        self.assertIn("if = { limit = { covert_agency_limited = yes } set_variable = iw_opened_early }", immediate)
        outcome = words(braced(self.je, r"^\toutcome = \{"))
        self.assertIn("OR = { NOT = { te_covert_warfare_on = yes } AND = { has_variable = iw_opened_early "
                      "NOT = { te_covert_warfare_early = yes } NOT = { covert_warfare_slot_source = yes } } }", outcome)
        self.assertIn("covert_stop_for_rule = yes", outcome)
        self.assertIn("set_variable = iw_reopen_at_gate", outcome)
        net = words(braced(code(COVERT_ON_ACTIONS), r"^covert_warfare_monthly_country = \{"))
        self.assertIn("has_variable = iw_reopen_at_gate te_covert_warfare_on = yes "
                      "covert_warfare_entry_unlocked = yes", net)
        self.assertIn("add_journal_entry = { type = je_covert_warfare }", net)

    def test_the_setting_descriptions_name_their_technology(self):
        rules = loc(RULES_LOC)
        self.assertIn("$central_archives$", rules["setting_covert_warfare_early_unlock_desc"])
        self.assertIn("$mainframe_computers$", rules["setting_covert_warfare_enabled_desc"])


# --- World War -----------------------------------------------------------------------------------------------------

WW_JE = ROOT / "common/journal_entries/world_war_je.txt"
WW_TRIGGERS = ROOT / "common/scripted_triggers/world_war_triggers.txt"
WW_BUTTONS = ROOT / "common/scripted_buttons/world_war_buttons.txt"
WW_EFFECTS = ROOT / "common/scripted_effects/te_event_agency_ww_effects.txt"
WW_ON_ACTIONS = ROOT / "common/on_actions/extra_on_actions.txt"
WW_EVENTS = ROOT / "events/world_war_events.txt"


class WorldWarEarlyUnlockTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.triggers = code(WW_TRIGGERS)
        cls.je = code(WW_JE)

    def test_late_is_combined_arms_early_adds_trench_works(self):
        self.assertEqual(words(braced(self.triggers, r"^ww_era_reached = \{")),
                         "OR = { has_technology_researched = combined_arms AND = { te_world_war_early = yes "
                         "has_technology_researched = trench_works } }")

    def test_every_gate_that_named_combined_arms_reads_the_era(self):
        for block in (r"^\tis_shown_when_inactive = \{", r"^\tpossible = \{"):
            body = words(braced(self.je, block))
            self.assertIn("ww_era_reached = yes", body)
            self.assertNotIn("combined_arms", body)
            self.assertIn("country_rank >= rank_value:great_power", body)
        conditions = words(braced(self.triggers, r"^world_war_conditions_met = \{"))
        self.assertIn("ww_era_reached = yes", conditions)
        self.assertNotIn("combined_arms", conditions)
        buttons = code(WW_BUTTONS)
        self.assertNotIn("has_technology_researched = combined_arms", buttons)
        self.assertEqual(buttons.count("ww_era_reached_tt = yes"), 2)
        # The late unlock's tooltip line is the one the buttons always showed.
        tt = words(braced(self.triggers, r"^ww_era_reached_tt = \{"))
        self.assertIn("trigger_else = { custom_tooltip = { text = WW_REQ_COMBINED_ARMS_TT "
                      "has_technology_researched = combined_arms } }", tt)

    def test_the_early_opposition_is_gated_and_symmetric(self):
        opposed = words(braced(self.triggers, r"^country_has_opposed_ideology = \{"))
        self.assertIn("AND = { te_world_war_early = yes ww_before_ideological_age = { TARGET = $TARGET$ } OR = { "
                      "AND = { country_is_democratic = yes $TARGET$ = { country_is_authoritarian = yes } } "
                      "AND = { country_is_authoritarian = yes $TARGET$ = { country_is_democratic = yes } } } }",
                      opposed)
        self.assertEqual(words(braced(self.triggers, r"^ww_before_ideological_age = \{")),
                         "NOT = { has_technology_researched = combined_arms } "
                         "$TARGET$ = { NOT = { has_technology_researched = combined_arms } }")

    def test_the_late_opposition_is_the_three_ideological_pairs(self):
        # country_has_opposed_ideology is the ideological pairs or the early pairing, and the early pairing needs
        # the early setting, so under the late unlock it is what it was before the setting existed.
        opposed = words(braced(self.triggers, r"^country_has_opposed_ideology = \{"))
        self.assertTrue(opposed.startswith(
            "OR = { country_has_ideological_opposition = { TARGET = $TARGET$ } AND = { te_world_war_early = yes "),
            opposed[:120])
        pairs = words(braced(self.triggers, r"^country_has_ideological_opposition = \{"))
        self.assertNotIn("te_world_war_early", pairs)
        self.assertNotIn("authoritarian", pairs)
        for a, b in (("democratic", "communist"), ("democratic", "fascist"), ("communist", "fascist")):
            for x, y in ((a, b), (b, a)):
                self.assertIn("AND = { country_is_%s = yes $TARGET$ = { country_is_%s = yes } }" % (x, y), pairs)
        self.assertEqual(pairs.count("AND = {"), 6)

    def test_yesterdays_ally_needs_an_ideological_opposition(self):
        # Review, 2026-11-13: a liberal and an autocratic great power that fought the war on one side are
        # "opposed" by the early pairing all through it, so world_war_events.105 (an ally turning into the next
        # rival) would fire between them, take 30 relations and close the war early. It asks for the ideological
        # pairs alone, in its trigger and where it picks the rival.
        event = words(braced(code(WW_EVENTS), r"^world_war_events\.105 = \{"))
        self.assertEqual(event.count("ROOT = { country_has_ideological_opposition = { TARGET = prev } }"), 2)
        self.assertNotIn("country_has_opposed_ideology", event)
        self.assertEqual(event.count("ww_fought_alongside = { COUNTRY = root }"), 2)

    def test_an_early_war_leaves_room_for_a_second(self):
        self.assertNotIn("set_variable = ww_entry_resolved", self.je)
        self.assertEqual(self.je.count("ww_mark_entry_resolved = yes"), 2)
        for block in (r"^\tis_shown_when_inactive = \{", r"^\tpossible = \{"):
            self.assertIn("NOT = { ww_resting_after_early_war = yes }", words(braced(self.je, block)))

    def test_the_war_is_classed_when_it_breaks_out(self):
        # Review, 2026-11-13: the entry's outcomes tested the country's own Combined Arms on the day the entry
        # closed, 36 months after the peace. Which of the two wars it was is settled at the outbreak, once, for
        # the whole world.
        effects = code(WW_EFFECTS)
        self.assertEqual(words(braced(effects, r"^ww_record_war_kind = \{")),
                         "if = { limit = { te_world_war_early = yes ww_before_ideological_age = { TARGET = "
                         "scope:war_target } } set_global_variable = { name = ww_last_war_early value = 1 } } "
                         "else = { set_global_variable = { name = ww_last_war_early value = 0 } }")
        launch = words(braced(code(WW_EVENTS), r"^world_war_events\.5 = \{"))
        self.assertEqual(launch.count("ww_record_war_kind = yes"), 1)
        # In the launch option, where the two belligerents are marked, and after scope:war_target is saved.
        self.assertLess(launch.index("save_scope_as = war_target"), launch.index("ww_record_war_kind = yes"))
        self.assertLess(launch.index("ww_record_war_kind = yes"), launch.index("set_variable = ww_aggressor_side"))
        self.assertEqual(code(WW_EVENTS).count("ww_record_war_kind = yes"), 1)
        self.assertEqual(effects.count("ww_last_war_early"), 5)     # two writes, two guards and the read

    def test_the_entry_closes_on_the_war_not_on_the_countrys_research(self):
        mark = words(braced(code(WW_EFFECTS), r"^ww_mark_entry_resolved = \{"))
        self.assertEqual(mark, "if = { limit = { te_world_war_early = yes OR = { "
                               "AND = { has_global_variable = ww_last_war_early global_var:ww_last_war_early >= 1 } "
                               "AND = { NOT = { has_global_variable = ww_last_war_early } "
                               "NOT = { has_technology_researched = combined_arms } } } } "
                               "set_variable = ww_early_war_resolved } else = { set_variable = ww_entry_resolved }")

        def resolved(early_setting, last_war_early, combined_arms):
            """What ww_mark_entry_resolved sets, by the rule the string above pins. last_war_early is None while
            no world war has broken out in the game."""
            if early_setting and (last_war_early == 1 or (last_war_early is None and not combined_arms)):
                return "ww_early_war_resolved"
            return "ww_entry_resolved"

        # The review's two scenarios: a power that researched Combined Arms during an early war or its
        # aftermath, and one that held it while others fought an early war. Both keep the later war.
        self.assertEqual(resolved(True, 1, True), "ww_early_war_resolved")
        # A power without it after an early war, as before.
        self.assertEqual(resolved(True, 1, False), "ww_early_war_resolved")
        # A war begun with Combined Arms on either side is the last one, whoever lacks the technology.
        self.assertEqual(resolved(True, 0, False), "ww_entry_resolved")
        self.assertEqual(resolved(True, 0, True), "ww_entry_resolved")
        # No war yet (the entry failed on rank): the old test.
        self.assertEqual(resolved(True, None, False), "ww_early_war_resolved")
        self.assertEqual(resolved(True, None, True), "ww_entry_resolved")
        # The late unlock: for good, whatever else holds, as before the setting existed.
        for last, tech in ((1, True), (1, False), (0, False), (None, False), (None, True)):
            self.assertEqual(resolved(False, last, tech), "ww_entry_resolved")

    def test_a_power_with_combined_arms_gets_its_entry_back_once_the_early_war_has_wound_down(self):
        # ww_early_war_resolved with Combined Arms is not "resting", so the monthly net adds the entry back; it
        # waits until no country still carries the old war's peace, or the new entry's observer branch would
        # read that peace as its own and complete again three years on.
        self.assertEqual(words(braced(self.triggers, r"^ww_resting_after_early_war = \{")),
                         "has_variable = ww_early_war_resolved NOT = { has_technology_researched = combined_arms }")
        net = words(braced(code(WW_ON_ACTIONS), r"^world_war_events_on_action = \{"))
        add = net[:net.index("add_journal_entry = { type = je_world_war }")]
        self.assertIn("OR = { has_variable = ww_reopen_at_gate has_variable = ww_early_war_resolved }", add)
        self.assertIn("NOT = { has_inactive_journal_entry = je_world_war } "
                      "NOT = { any_country = { has_variable = ww_peace_concluded } } }", add)
        # The walk over every country comes last, after the tests only a marked country passes.
        self.assertLess(add.index("has_variable = ww_early_war_resolved"), add.index("any_country"))

    def test_switched_to_late_the_entry_closes_and_the_net_brings_it_back(self):
        outcomes = re.findall(r"^\toutcome = \{", self.je, re.M)
        self.assertEqual(len(outcomes), 3)
        invalid = words(self.je[self.je.index("flags = { hidden invalid_outcome }"):])
        self.assertIn("OR = { NOT = { te_world_war_on = yes } NOT = { ww_era_reached = yes } }", invalid)
        self.assertIn("set_variable = ww_reopen_at_gate", invalid)
        net = words(braced(code(WW_ON_ACTIONS), r"^world_war_events_on_action = \{"))
        self.assertIn("te_world_war_on = yes ww_era_reached = yes NOT = { ww_resting_after_early_war = yes }", net)
        self.assertIn("add_journal_entry = { type = je_world_war }", net)

    def test_the_setting_descriptions_name_their_technology(self):
        rules = loc(RULES_LOC)
        self.assertIn("$trench_works$", rules["setting_world_war_early_unlock_desc"])
        self.assertIn("$combined_arms$", rules["setting_world_war_enabled_desc"])


# --- United Nations ------------------------------------------------------------------------------------------------

UN_MEMBERSHIP = ROOT / "common/scripted_triggers/un_membership_triggers.txt"
UN_LADDER = ROOT / "common/scripted_triggers/un_ladder_triggers.txt"
UN_PROPOSE = ROOT / "common/scripted_triggers/un_propose_triggers.txt"
UN_BUTTONS = ROOT / "common/scripted_buttons/un_buttons.txt"
UN_ACTION_SGUIS = ROOT / "common/scripted_guis/un_action_sguis.txt"
UN_ON_ACTIONS = ROOT / "common/on_actions/un_on_actions.txt"


class UnitedNationsEarlyUnlockTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.membership = code(UN_MEMBERSHIP)

    def test_late_is_todays_gate(self):
        unlocked = braced(self.membership, r"^un_entry_unlocked = \{")
        self.assertEqual(words(braced(unlocked, r"trigger_else = \{")),
                         "custom_tooltip = { text = un_unlock_tt OR = { has_technology_researched = "
                         "intergovernmental_organizations has_global_variable = un_founded } }")
        founding = words(braced(self.membership, r"^un_founding_tech_reached_tt = \{"))
        self.assertIn("trigger_else = { has_technology_researched = intergovernmental_organizations }", founding)

    def test_early_founds_at_multilateral_alliances(self):
        self.assertEqual(words(braced(self.membership, r"^un_founding_tech_reached = \{")),
                         "OR = { has_technology_researched = intergovernmental_organizations AND = { "
                         "te_united_nations_early = yes has_technology_researched = multilateral_alliances } }")
        unlocked = braced(self.membership, r"^un_entry_unlocked = \{")
        self.assertIn("limit = { te_united_nations_early = yes } custom_tooltip = { text = un_unlock_early_tt OR = { "
                      "un_founding_tech_reached = yes has_global_variable = un_founded } }",
                      words(braced(unlocked, r"trigger_if = \{")))

    def test_both_founding_controls_read_the_founding_technology(self):
        for path, header in ((UN_BUTTONS, r"^un_found_button = \{"), (UN_ACTION_SGUIS, r"^un_act_found_sgui = \{")):
            with self.subTest(control=header):
                body = braced(code(path), header)
                self.assertNotIn("intergovernmental_organizations", body)
                self.assertIn("un_founding_tech_reached = yes", body)
                self.assertIn("un_founding_tech_reached_tt = yes", body)

    def test_the_league_reforms_nothing_until_the_age_of_intergovernmental_organizations(self):
        self.assertEqual(words(braced(self.membership, r"^un_league_stage = \{")),
                         "te_united_nations_early = yes NOT = { has_global_variable = un_igo_age }")
        ladder = code(UN_LADDER)
        self.assertEqual(words(braced(ladder, r"^un_charter_reform_ripe = \{")),
                         "un_charter_pressure_met = yes NOT = { un_league_stage = yes }")
        possible = words(braced(code(UN_PROPOSE), r"^un_propose_reform_possible = \{"))
        # The league's line shows only under the early setting (review, 2026-11-13: under the late unlock it was a
        # new, always-met tooltip line about a setting the game is not in). un_league_stage needs the early flag,
        # so the late unlock's test is unchanged.
        self.assertIn("trigger_if = { limit = { te_united_nations_early = yes } custom_tooltip = { "
                      "text = un_charter_league_tt NOT = { un_league_stage = yes } } }", possible)
        self.assertEqual(possible.count("un_charter_league_tt"), 1)
        pulse = words(braced(code(UN_ON_ACTIONS), r"^un_global_authority_on_action = \{"))
        # The league's notice (UnitedNationsLeagueNameTest) may sit between the test and the mark.
        self.assertRegex(pulse, re.escape("any_country = { has_technology_researched = intergovernmental_organizations } }")
                         + r" (if = \{ limit = \{ un_league_stage = yes .*? \} )?set_global_variable = un_igo_age")
        # Nothing ever removes the mark.
        for folder in ("common", "events"):
            for path in (ROOT / folder).rglob("*.txt"):
                self.assertNotRegex(code(path), r"remove_global_variable\s*=\s*un_igo_age\b", path)

    def test_the_setting_descriptions_name_their_technology(self):
        rules = loc(RULES_LOC)
        self.assertIn("$multilateral_alliances$", rules["setting_united_nations_early_unlock_desc"])
        self.assertIn("$intergovernmental_organizations$", rules["setting_united_nations_enabled_desc"])


UN_CUSTOM_LOC = ROOT / "common/customizable_localization/zzz_extra_custom_loc.txt"
UN_EVENTS = ROOT / "events/un_events.txt"
EXTRA_MESSAGES = ROOT / "common/messages/extra_messages.txt"
UN_CHAMBER_SGUIS = ROOT / "common/scripted_guis/un_chamber_sguis.txt"
UN_OVERVIEW_GUI = ROOT / "gui/journal_entry_widgets/un_overview_widget.gui"
LOC_DIR = ROOT / "localization/english"


def all_loc():
    out = {}
    for path in sorted(LOC_DIR.glob("*_l_english.yml")):
        out.update(loc(path))
    return out


def splice(text, keys, plain):
    """`text` with each `$key$` expanded from `keys`, a key in `plain` read as that fixed text instead."""
    def one(m):
        key = m.group(1)
        if key in plain:
            return plain[key]
        return splice(keys[key], keys, plain) if key in keys else m.group(0)
    return re.sub(r"\$(\w+)\$", one, text)


class UnitedNationsLeagueNameTest(unittest.TestCase):
    """While the early unlock's league stands (un_league_stage) the names a player meets first read "League of
    Nations"; under the late unlock, and from the month of un_igo_age, they read as before."""

    @classmethod
    def setUpClass(cls):
        cls.loc = all_loc()

    def test_the_name_is_the_league_only_in_the_league_stage(self):
        body = words(braced(code(UN_CUSTOM_LOC), r"^un_org_name = \{"))
        self.assertEqual(body, "type = country random_valid = no "
                               "text = { trigger = { un_league_stage = yes } localization_key = un_org_name_league } "
                               "text = { trigger = { always = yes } localization_key = un_org_name_un }")
        self.assertEqual(self.loc["un_org_name_league"], "League of Nations")
        self.assertEqual(self.loc["un_org_name_un"], "United Nations")
        self.assertEqual(self.loc["un_org_name_ingame"], "[GetPlayer.GetCustom('un_org_name')]")

    def test_the_title_is_guarded_and_falls_back_to_the_united_nations(self):
        # No player (an observer's National Info, a loading screen): the plain name, never a GetCustom.
        self.assertEqual(self.loc["je_united_nations"],
                         "[SelectLocalization(GetPlayer.IsValid,'un_org_name_ingame','un_org_name_un')]")

    def test_outside_the_league_every_switched_name_reads_as_before(self):
        # Today's text, with je_united_nations read as its fallback (un_org_name_un).
        plain = {"je_united_nations": self.loc["un_org_name_un"]}
        before = {
            "je_united_nations": "United Nations",
            "te_window_tab_united_nations": "United Nations",
            "te_window_tab_united_nations_locked_tt": r"#b United Nations#!\nNot open yet. It opens once:\n",
            "je_un_act_found_label": "Found the United Nations",
        }
        for key, text in before.items():
            with self.subTest(key=key):
                self.assertEqual(splice(f"${key}$", self.loc, plain), text)

    def test_the_founding_control_reads_the_league_stage(self):
        # "Found the League of Nations" is wider than the button, so the label is a short key picked in the GUI.
        sgui = words(braced(code(UN_CHAMBER_SGUIS), r"^un_ov_league_sgui = \{"))
        self.assertEqual(sgui, "scope = country is_shown = { un_league_stage = yes } "
                               "ai_is_valid = { always = no } is_valid = { always = no } effect = { }")
        scope = "GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End"
        self.assertIn(f"'je_un_act_convene_label', SelectLocalization( GetScriptedGui('un_ov_league_sgui').IsShown( "
                      f"{scope} ), 'je_un_act_found_league_label', 'je_un_act_found_label' ) )",
                      read(UN_OVERVIEW_GUI))
        self.assertEqual(self.loc["je_un_act_found_label"], "Found the United Nations")
        self.assertEqual(self.loc["je_un_act_found_league_label"], "Found the League")

    def test_the_founding_event_title_reads_the_league_stage(self):
        event = braced(code(UN_EVENTS), r"^un_events\.1 = \{")
        title = words(braced(event, r"^\ttitle = \{"))
        self.assertEqual(title, "first_valid = { triggered_desc = { trigger = { un_league_stage = yes } "
                                "desc = un_events.1.t_league } desc = un_events.1.t }")
        self.assertEqual(self.loc["un_events.1.t"], "The United Nations Charter")
        self.assertIn("League of Nations", self.loc["un_events.1.t_league"])

    def test_the_league_is_told_once_when_it_becomes_the_united_nations(self):
        pulse = words(braced(code(UN_ON_ACTIONS), r"^un_global_authority_on_action = \{"))
        notice = ("if = { limit = { un_league_stage = yes has_global_variable = un_founded } every_country = { "
                  "limit = { OR = { je:je_united_nations ?= { has_modifier = un_member_modifier } is_player = yes } } "
                  "post_notification = un_league_refounded_notice } } set_global_variable = un_igo_age")
        # Inside the block that sets the mark, so it runs only the month the mark is set, and before the mark,
        # while un_league_stage still holds.
        self.assertIn("any_country = { has_technology_researched = intergovernmental_organizations } } " + notice,
                      pulse)
        self.assertEqual(pulse.count("un_league_refounded_notice"), 1)
        self.assertRegex(code(EXTRA_MESSAGES), r"(?m)^un_league_refounded_notice = \{")
        for suffix in ("name", "desc", "tooltip"):
            self.assertIn(f"notification_un_league_refounded_notice_{suffix}", self.loc)


# --- Cultural Hegemony ---------------------------------------------------------------------------------------------

CH_TRIGGERS = ROOT / "common/scripted_triggers/cultural_hegemony_triggers.txt"
CH_JE = ROOT / "common/journal_entries/je_cultural_hegemony.txt"
CH_ON_ACTIONS = ROOT / "common/on_actions/cultural_hegemony_on_actions.txt"
CH_EVENTS = ROOT / "events/cultural_hegemony_events.txt"
EVENTS_LOC = ROOT / "localization/english/te_events_l_english.yml"


class CulturalHegemonyEarlyUnlockTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.triggers = code(CH_TRIGGERS)
        cls.je = code(CH_JE)

    def test_late_is_todays_gate(self):
        unlocked = braced(self.triggers, r"^ch_entry_unlocked = \{")
        self.assertEqual(words(braced(unlocked, r"trigger_else = \{")),
                         "custom_tooltip = { text = ch_unlock_any_mass_media_tt any_country = { "
                         "has_technology_researched = mass_media } }")
        self.assertTrue(words(unlocked).endswith("has_technology_researched = romanticism"))
        self.assertEqual(words(braced(self.triggers, r"^ch_late_gate_met = \{")),
                         "any_country = { has_technology_researched = mass_media } "
                         "has_technology_researched = romanticism")
        self.assertEqual(words(braced(self.je, r"^\tpossible = \{")), "ch_entry_unlocked = yes")

    def test_early_opens_at_the_electric_telegraph(self):
        unlocked = braced(self.triggers, r"^ch_entry_unlocked = \{")
        self.assertEqual(words(braced(unlocked, r"trigger_if = \{")),
                         "limit = { te_cultural_hegemony_early = yes } custom_tooltip = { text = "
                         "ch_unlock_any_telegraph_tt any_country = { OR = { has_technology_researched = "
                         "electric_telegraph has_technology_researched = mass_media } } }")

    def test_outreach_comes_with_the_telegraph_the_media_campaign_waits_for_mass_media(self):
        exposition = words(braced(self.triggers, r"^ch_possible_world_exposition = \{"))
        self.assertIn("ch_world_exposition_tech = yes", exposition)
        self.assertNotIn("mass_media", exposition)
        tech = words(braced(self.triggers, r"^ch_world_exposition_tech = \{"))
        self.assertIn("trigger_else = { custom_tooltip = { text = CH_REQUIRES_MASS_MEDIA_TT "
                      "has_technology_researched = mass_media } }", tech)
        self.assertIn("electric_telegraph", tech)
        media = words(braced(self.triggers, r"^ch_possible_global_media_campaign = \{"))
        self.assertIn("custom_tooltip = { text = CH_REQUIRES_MASS_MEDIA_TT has_technology_researched = mass_media }",
                      media)

    def test_events_that_need_no_mass_media_name_none(self):
        """The events with no Mass Media test of their own fire for an entry opened early, so their text must not
        assume broadcast media (radio, film, television)."""
        text = code(CH_EVENTS)
        events = list(re.finditer(r"^(cultural_hegemony\.\d+) = \{", text, re.M))
        texts = loc(EVENTS_LOC)
        ungated = []
        for i, m in enumerate(events):
            body = text[m.start():events[i + 1].start() if i + 1 < len(events) else len(text)]
            if "mass_media" not in body:
                ungated.append(m.group(1))
        self.assertTrue(ungated)
        for event in ungated:
            for key, value in texts.items():
                if key.startswith(event + "."):
                    with self.subTest(key=key):
                        self.assertNotRegex(value.lower(), r"\b(radio|television|broadcast|cinema|film|internet)\b")

    def test_switched_to_late_the_early_entry_closes_and_comes_back_at_the_gate(self):
        immediate = words(braced(self.je, r"^\timmediate = \{"))
        self.assertIn("if = { limit = { te_cultural_hegemony_early = yes NOT = { ch_late_gate_met = yes } } "
                      "set_variable = ch_opened_early }", immediate)
        outcome = words(self.je[self.je.index("flags = { hidden invalid_outcome }"):])
        self.assertIn("OR = { NOT = { te_cultural_hegemony_on = yes } AND = { has_variable = ch_opened_early "
                      "NOT = { te_cultural_hegemony_early = yes } NOT = { ch_late_gate_met = yes } } }", outcome)
        self.assertIn("set_variable = ch_reopen_at_gate", outcome)
        net = words(braced(code(CH_ON_ACTIONS), r"^ch_monthly_pulse_on_action = \{"))
        self.assertIn("has_variable = ch_reopen_at_gate te_cultural_hegemony_on = yes ch_entry_unlocked = yes", net)
        self.assertIn("add_journal_entry = { type = je_cultural_hegemony }", net)

    def test_the_setting_descriptions_name_their_technology(self):
        rules = loc(RULES_LOC)
        self.assertIn("$electric_telegraph$", rules["setting_cultural_hegemony_early_unlock_desc"])
        self.assertIn("$mass_media$", rules["setting_cultural_hegemony_enabled_desc"])


if __name__ == "__main__":
    unittest.main()
