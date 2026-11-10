# -*- coding: utf-8 -*-
"""country_government_wages_mult is pay, never a stand-in for a cost.

The multiplier sets how much more or less than the normal wage the state pays its own staff. A
program, subsidy or relief effort that costs money is a country_expenses_add = 1 modifier applied
with a GDP-scaled multiplier, as vanilla does it: a wage multiplier also raises government
employees' incomes, follows the payroll rather than the economy, and reads as a pay rise in the
tooltip. Six event modifiers used one as a cost until 2026-11-09. The three below keep theirs
because the state's own pay is what changes. scripting_best_practices.md, "A Treasury Cost Is
`country_expenses_add`, Not a Wage Multiplier".

Run: python3 -m unittest test_wage_modifiers -v
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
SCANNED = ("common", "events")
WAGES = re.compile(r"\bcountry_government_wages_mult\s*=")
ENTITY = re.compile(r"^(?:[A-Z]+:)?(\w+)\s*=\s*\{")

# Top-level entity -> why its government wage line is pay.
PAY = {
    "declared_bankruptcy": "a bankrupt state cuts its employees' pay",
    "ste_equal_pay_reform": "equal pay raises what the state pays its own staff",
    "ste_antiglobal_concession": "the labor standards conceded bind the state as an employer",
}


def _uses():
    """The top-level entities under common/ and events/ that carry the multiplier."""
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
                        if WAGES.search(code):
                            found[entity] = f"{os.path.relpath(path, REPO)}:{number}"
    return found


class GovernmentWagesArePayTests(unittest.TestCase):
    def test_the_scan_finds_the_reviewed_uses(self):
        """A path error would pass the next test with nothing scanned."""
        self.assertEqual(sorted(_uses()), sorted(PAY))

    def test_no_other_entity_uses_government_wages(self):
        extra = {entity: where for entity, where in _uses().items() if entity not in PAY}
        self.assertEqual(extra, {}, "a cost is a country_expenses_add = 1 modifier applied with "
                         "multiplier = sv_money_flow_event_<tier>; if this one is pay, add it to PAY")


if __name__ == "__main__":
    unittest.main()
