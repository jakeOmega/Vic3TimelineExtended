"""The medical mobilization options keep their 1 : 2 : 4 recovery ladder.

First Aid and Field Hospitals are the mod's REPLACE copies of vanilla's, re-based
on each patch (1.15.2 halved them to 0.10 and 0.20); Medevac Helicopters is the
mod's third tier at twice Field Hospitals'. A patch that moves vanilla's two
again fails here until Medevac follows. No game install needed.
"""

import unittest
from decimal import Decimal

from test_war_wounded_medics import effective_options

FIRST_AID = "mobilization_option_first_aid"
FIELD_HOSPITALS = "mobilization_option_field_hospitals"
MEDEVAC = "mobilization_option_medevac_helicopters"


class RecoveryLadderTest(unittest.TestCase):
    def test_each_tier_doubles_the_one_below(self):
        options = effective_options()
        first_aid = options[FIRST_AID]["recovery"]
        self.assertGreater(first_aid, 0)
        self.assertEqual(options[FIELD_HOSPITALS]["recovery"], 2 * first_aid)
        self.assertEqual(options[MEDEVAC]["recovery"], 4 * first_aid)
        self.assertEqual(options[MEDEVAC]["recovery"], Decimal("0.40"))


if __name__ == "__main__":
    unittest.main()
