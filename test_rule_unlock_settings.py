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

    def test_an_early_war_leaves_room_for_a_second(self):
        self.assertNotIn("set_variable = ww_entry_resolved", self.je)
        self.assertEqual(self.je.count("ww_mark_entry_resolved = yes"), 2)
        mark = words(braced(code(WW_EFFECTS), r"^ww_mark_entry_resolved = \{"))
        self.assertEqual(mark, "if = { limit = { te_world_war_early = yes NOT = { has_technology_researched = "
                               "combined_arms } } set_variable = ww_early_war_resolved } "
                               "else = { set_variable = ww_entry_resolved }")
        for block in (r"^\tis_shown_when_inactive = \{", r"^\tpossible = \{"):
            self.assertIn("NOT = { ww_resting_after_early_war = yes }", words(braced(self.je, block)))

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


if __name__ == "__main__":
    unittest.main()
