"""Company AI wiring the engine never reports when it is missing.

- An `ai_construction_targets` entry with no `state_trigger` does nothing
  (vanilla game/common/company_types/companies.md: "scripting this with an empty
  state trigger will do nothing"). All 82 mod flavored companies shipped that way.
- A mod flavored company with no `ai_weight` competes at the engine default 1,
  below vanilla's flavored 3 (common/script_values/te_company_ai_values.txt).
- A buildable company flagship with no `ai_value` scores like any production
  building, and the AI built 13 for 319 companies in a 2029 observer save.
"""
from pathlib import Path
import re
import unittest

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
COMPANY_FILES = sorted((ROOT / "common/company_types").glob("*.txt"))
FLAGSHIPS = ROOT / "common/buildings/company_buildings.txt"


def entries(node):
    for part in node if isinstance(node, list) else [node]:
        for key, (op, value) in part.items():
            yield key, op, value


def parse(path):
    parser = ParadoxFileParser()
    return parser.parse_object(parser.tokenize("{" + path.read_text(encoding="utf-8-sig") + "}"))[0]


def field(block, key):
    return next((value for k, _, value in entries(block) if k == key), None)


def companies():
    for path in COMPANY_FILES:
        for name, _, block in entries(parse(path)):
            if isinstance(block, (dict, list)):
                yield path.name, name, block


class CompanyAiTests(unittest.TestCase):
    def test_every_construction_target_has_a_state_trigger(self):
        missing = []
        for file, name, block in companies():
            targets = field(block, "ai_construction_targets")
            for building, _, target in entries(targets) if targets else ():
                trigger = field(target, "state_trigger") if isinstance(target, (dict, list)) else None
                if not trigger:
                    missing.append(f"{file}: {name} -> {building}")
        self.assertEqual(missing, [], "ai_construction_targets entries without a state_trigger do nothing")

    def test_every_mod_flavored_company_has_an_ai_weight(self):
        missing = [f"{file}: {name}" for file, name, block in companies()
                   if ":" not in name and field(block, "flavored_company") == "yes" and field(block, "ai_weight") is None]
        self.assertEqual(missing, [])

    def test_every_buildable_flagship_has_an_ai_value(self):
        missing, checked = [], 0
        for name, _, block in entries(parse(FLAGSHIPS)):
            potential = field(block, "potential")
            if potential is not None and field(potential, "always") == "no":
                continue  # retired, kept so old saves load
            checked += 1
            if field(block, "ai_value") is None:
                missing.append(name)
        self.assertGreater(checked, 300)
        self.assertEqual(missing, [])

    def test_failing_company_check_runs_on_the_monthly_country_pulse(self):
        hooks = (ROOT / "common/on_actions/te_company_on_actions.txt").read_text(encoding="utf-8-sig")
        self.assertRegex(hooks, re.compile(r"on_monthly_pulse_country = \{\s*on_actions = \{\s*te_company_monthly_on_action\s*\}", re.S))
        self.assertIn("te_company_failing_monthly_effect = yes", hooks)

    def test_size_test_reads_a_scope_value_the_effect_saves_first(self):
        # A comparison against an unsaved scope value fails without a log line.
        triggers = (ROOT / "common/scripted_triggers/te_company_triggers.txt").read_text(encoding="utf-8-sig")
        effects = (ROOT / "common/scripted_effects/te_company_effects.txt").read_text(encoding="utf-8-sig")
        self.assertIn("company_owned_levels < scope:te_company_min_levels", triggers)
        effect = effects[effects.index("te_company_failing_monthly_effect = {"):]
        self.assertLess(effect.index("name = te_company_min_levels"), effect.index("every_company"))
        self.assertLess(effect.index("every_company"), effect.index("te_company_fails_this_month = yes"))


if __name__ == "__main__":
    unittest.main()
