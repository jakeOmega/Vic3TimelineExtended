# -*- coding: utf-8 -*-
"""The government and military wage multipliers are pay, never a stand-in for a cost.

Each multiplier sets how much more or less than the normal wage the state pays its own staff or its
soldiers. A program, subsidy, operation or relief effort that costs money is a
country_expenses_add = 1 modifier applied with a GDP-scaled multiplier, as vanilla does it: a wage
multiplier also raises the employees' incomes, follows the payroll rather than the economy, and
reads as a pay rise in the tooltip. Nine event modifiers used one as a cost until November 2026.
The uses below keep theirs because pay is what changes. scripting_best_practices.md, "A Treasury
Cost Is `country_expenses_add`, Not a Wage Multiplier".

Run: python3 -m unittest test_wage_modifiers -v
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
SCANNED = ("common", "events")
ENTITY = re.compile(r"^(?:[A-Z]+:)?(\w+)\s*=\s*\{")

# Multiplier -> {top-level entity -> why its wage line is pay}.
PAY = {
    "country_government_wages_mult": {
        "declared_bankruptcy": "a bankrupt state cuts its employees' pay",
        "ste_equal_pay_reform": "equal pay raises what the state pays its own staff",
    },
    "country_military_wages_mult": {
        "declared_bankruptcy": "a bankrupt state cuts its soldiers' pay",
        "forced_disarmament": "the article's text cuts military wages by name",
        "institution_ministry_of_war": "a standing war ministry pays its soldiers more",
        "principle_aggressive_coordination_4": "an aggressive bloc pays its members' soldiers more",
        "principle_aggressive_coordination_5": "an aggressive bloc pays its members' soldiers more",
    },
}


def _uses(field):
    """The top-level entities under common/ and events/ that carry the multiplier."""
    pattern = re.compile(rf"\b{field}\s*=")
    found = {}
    for top in SCANNED:
        for root, _, names in os.walk(os.path.join(REPO, top)):
            for name in sorted(names):
                if not name.endswith(".txt"):
                    continue
                path = os.path.join(root, name)
                entity = None
                with open(path, encoding="utf-8-sig") as f:
                    for number, line in enumerate(f, 1):
                        code = line.split("#", 1)[0]
                        match = ENTITY.match(code)
                        if match:
                            entity = match.group(1)
                        if pattern.search(code):
                            found[entity] = f"{os.path.relpath(path, REPO)}:{number}"
    return found


class WagesArePayTests(unittest.TestCase):
    def test_the_scan_finds_the_reviewed_uses(self):
        """A path error would pass the next test with nothing scanned."""
        for field, reviewed in PAY.items():
            with self.subTest(field=field):
                self.assertEqual(sorted(_uses(field)), sorted(reviewed))

    def test_no_other_entity_uses_a_wage_multiplier(self):
        for field, reviewed in PAY.items():
            with self.subTest(field=field):
                extra = {entity: where for entity, where in _uses(field).items() if entity not in reviewed}
                self.assertEqual(extra, {}, "a cost is a country_expenses_add = 1 modifier applied with "
                                 f"multiplier = sv_money_flow_event_<tier>; if this {field} is pay, add it to PAY")


if __name__ == "__main__":
    unittest.main()
