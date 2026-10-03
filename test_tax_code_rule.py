"""The legislated tax code's game rule, gate triggers, carrier law and vanilla-law gates.

Structural checks on the committed script (no game install needed). Under the
rule the five vanilla taxation laws cannot be enacted and `law_te_tax_code`
carries one generated amendment per instrument (see test_tax_code_generated.py).
With the rule off every one of these edits has to be inert.
"""

import json
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent

RULE = "te_tax_code_rule"
OPTIONS = ("te_tax_code_disabled", "te_tax_code_enabled", "te_tax_code_enabled_customs")
RATE_KEYS = (
    "tax_income_add", "tax_dividends_add", "tax_land_add",
    "tax_per_capita_add", "tax_consumption_add",
)
LEVELS = (
    "tax_modifier_very_low", "tax_modifier_low", "tax_modifier_medium",
    "tax_modifier_high", "tax_modifier_very_high",
)
VANILLA_TAX_LAWS = (
    "law_consumption_based_taxation", "law_land_based_taxation",
    "law_per_capita_based_taxation", "law_proportional_taxation",
    "law_graduated_taxation",
)
OPERATORS = {"=", "<", ">", "<=", ">=", "!=", "?=", "=="}


def plain(node):
    """Drop the parser's (operator, value) pairs, leaving dicts, lists and strings."""
    if isinstance(node, (tuple, list)) and len(node) == 2 and isinstance(node[0], str) and node[0] in OPERATORS:
        return plain(node[1])
    if isinstance(node, dict):
        return {key: plain(value) for key, value in node.items()}
    if isinstance(node, list):
        return [plain(item) for item in node]
    return node


def load(path):
    """Parse one mod file with its directives left intact (`INJECT:x` stays a key)."""
    parser = ParadoxFileParser()
    parser.parse_file(str(ROOT / path), apply_directives=False)
    return plain(parser.data)


class GameRuleTest(unittest.TestCase):
    def setUp(self):
        self.rules = load("common/game_rules/extra_game_rules.txt")

    def test_rule_has_the_three_options_and_defaults_to_disabled(self):
        rule = self.rules[RULE]
        self.assertEqual(rule["default"], "te_tax_code_disabled")
        self.assertEqual({key for key in rule if key != "default"}, set(OPTIONS))

    def test_each_option_sets_a_flag_named_after_itself(self):
        for option in OPTIONS:
            with self.subTest(option=option):
                self.assertEqual(self.rules[RULE][option], {"flag": option})


class RuleLocTest(unittest.TestCase):
    """Rule, option and law names live in the tax code's own loc file."""

    def setUp(self):
        self.loc = {}
        path = ROOT / "localization/english/te_tax_l_english.yml"
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            match = re.match(r'^ ([\w.\-]+):\d+ "(.*)"$', line)
            if match:
                self.loc[match.group(1)] = match.group(2)

    def test_rule_options_and_law_have_names_and_descriptions(self):
        keys = [f"rule_{RULE}", "law_te_tax_code", "law_te_tax_code_desc"]
        for option in OPTIONS:
            keys += [f"setting_{option}", f"setting_{option}_desc"]
        for key in keys:
            with self.subTest(key=key):
                self.assertTrue(self.loc.get(key), "missing or empty")

    def test_no_square_bracket_bold_markup(self):
        for key, text in self.loc.items():
            with self.subTest(key=key):
                self.assertNotIn("[b]", text)


class GateTriggerTest(unittest.TestCase):
    def setUp(self):
        self.triggers = load("common/scripted_triggers/te_tax_triggers.txt")

    def test_tax_code_on_is_two_positive_rule_checks(self):
        # Positive on purpose: a save from before the rule existed has no value
        # for it, and a NOT = { has_game_rule = ...disabled } would turn the
        # system on in such a save and migrate it.
        self.assertEqual(
            self.triggers["te_tax_code_on"],
            {"OR": {"has_game_rule": ["te_tax_code_enabled", "te_tax_code_enabled_customs"]}},
        )

    def test_customs_on_is_the_customs_setting_only(self):
        self.assertEqual(
            self.triggers["te_tax_customs_on"],
            {"has_game_rule": "te_tax_code_enabled_customs"},
        )

    def test_the_two_gates_contain_no_negation(self):
        # Scoped to the two gate triggers: later tasks add ordinary triggers to
        # this file, and an "instrument is unset" check is a NOT by nature.
        def keys(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    yield key
                    yield from keys(value)
            elif isinstance(node, list):
                for item in node:
                    yield from keys(item)

        for gate in ("te_tax_code_on", "te_tax_customs_on"):
            with self.subTest(gate=gate):
                self.assertFalse({"NOT", "NOR"} & set(keys(self.triggers[gate])))


class CarrierLawTest(unittest.TestCase):
    def setUp(self):
        self.law = load("common/laws/zz_te_tax_code_law.txt")["law_te_tax_code"]

    def test_law_sits_in_the_taxation_group_at_zero_progressiveness(self):
        self.assertEqual(self.law["group"], "lawgroup_taxation")
        self.assertEqual(self.law["progressiveness"], "0")
        self.assertEqual(
            self.law["icon"], '"gfx/interface/icons/law_icons/proportional_taxation.dds"'
        )

    def test_visible_only_under_the_rule_and_never_enactable_by_a_player(self):
        # Installed by activate_law only (Task 5), which ignores can_enact.
        self.assertEqual(self.law["is_visible"], {"te_tax_code_on": "yes"})
        self.assertEqual(self.law["can_enact"], {"always": "no"})
        self.assertEqual(self.law["ai_will_do"], {"always": "no"})

    def test_ai_enact_weight_is_prohibitive(self):
        self.assertLessEqual(int(self.law["ai_enact_weight_modifier"]["value"]), -100000)

    def test_possible_is_not_a_law_field(self):
        # The engine rejects it on a law ("Unexpected token: possible"); it is an
        # amendment field.
        self.assertNotIn("possible", self.law)

    def test_every_level_carries_all_five_rates_at_zero(self):
        for level in LEVELS:
            with self.subTest(level=level):
                self.assertEqual(self.law[level], {key: "0" for key in RATE_KEYS})

    def test_carrier_is_in_the_law_consistency_denylist(self):
        import gen_law_consistency

        self.assertIn("law_te_tax_code", gen_law_consistency.CARRIER_LAW_DENYLIST)


class VanillaLawGateTest(unittest.TestCase):
    def setUp(self):
        self.injects = load("common/laws/te_tax_vanilla_law_gates.txt")

    def test_exactly_the_five_vanilla_laws_are_injected(self):
        self.assertEqual(set(self.injects), {f"INJECT:{law}" for law in VANILLA_TAX_LAWS})

    def test_each_gets_exactly_the_two_negated_gates(self):
        # In a custom_tooltip (final review A-Minor 6): it evaluates the same, so a
        # rule-off game is unchanged, and a tooltip prints one plain line.
        gate = {"custom_tooltip": {"text": "te_tax_tt_vanilla_law_replaced", "NOT": {"te_tax_code_on": "yes"}}}
        for law in VANILLA_TAX_LAWS:
            with self.subTest(law=law):
                self.assertEqual(
                    self.injects[f"INJECT:{law}"], {"can_enact": gate, "is_visible": gate}
                )

    def test_vanilla_1_14_5_defines_neither_gate_on_these_laws(self):
        # An INJECT of a field the law already has would duplicate it. The
        # committed snapshot is vanilla 1.14.5.
        with open(ROOT / "vanilla_parsed" / "common" / "laws.json", encoding="utf-8") as handle:
            vanilla = plain(json.load(handle))
        for law in VANILLA_TAX_LAWS:
            with self.subTest(law=law):
                for field in ("can_enact", "is_visible"):
                    self.assertNotIn(field, vanilla[law])

    def test_no_other_mod_file_injects_or_replaces_these_laws(self):
        # A second INJECT of can_enact would be the duplicate the check above
        # guards against.
        gate_file = ROOT / "common/laws/te_tax_vanilla_law_gates.txt"
        pattern = re.compile(
            r"^\s*(?:INJECT|REPLACE|REPLACE_OR_CREATE|TRY_INJECT):(%s)\b" % "|".join(VANILLA_TAX_LAWS),
            re.M,
        )
        offenders = []
        for path in sorted((ROOT / "common").rglob("*.txt")):
            if path != gate_file:
                text = path.read_text(encoding="utf-8-sig", errors="ignore")
                offenders += [f"{path.name}: {m.group(0).strip()}" for m in pattern.finditer(text)]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
