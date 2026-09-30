"""The Enforce Emissions Reduction treaty waives the authority cost of the policies it forces.

The treaty locks its source into seven mitigation policies and bars repealing
any of them. Five of the seven cost authority (`country_authority_cost_add` on
the policy's static modifier). A country that cannot choose to drop them should
not be charged for them: authority below the limit cuts bureaucracy, which can
start a bankruptcy cycle. So the article's `source_modifier` carries a negative
`country_authority_cost_add` equal to their sum, and the treaty itself costs no
authority (its cost is industrialist disapproval instead).

Nothing in the engine notices when the two drift apart -- a policy retuned from
200 to 250 would silently leave the source paying 50 -- so this checks the
waiver against the modifiers it cancels. Climate adaptation also costs
authority but is not forced, so it must stay OUT of the sum.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TREATY = ROOT / "common/treaty_articles/109_enforce_emissions_reduction.txt"
MODIFIERS = ROOT / "common/static_modifiers/extra_modifiers.txt"

# The modifiers the treaty's on_entry_into_force adds to the source's journal
# entry, read from the article so a policy added to the treaty is counted.
NOT_FORCED = "climate_adaptation_modifier"


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _block(text, header):
    """The body of a top-level or nested `header = {` block, by brace matching."""
    start = text.index(header + " = {") + len(header) + 4
    depth = 1
    i = start
    while depth:
        c = text[i]
        depth += (c == "{") - (c == "}")
        i += 1
    return text[start:i - 1]


def _authority_cost(modifier):
    body = _block(_text(MODIFIERS), modifier)
    m = re.search(r"country_authority_cost_add\s*=\s*(-?\d+)", body)
    return int(m.group(1)) if m else 0


class TreatyAuthorityWaiver(unittest.TestCase):
    def setUp(self):
        self.treaty = _text(TREATY)
        self.source = _block(self.treaty, "source_modifier")

    def _forced(self):
        # Every policy modifier the treaty adds is named in its non_fulfillment
        # check, which lists exactly the policies whose removal freezes it.
        block = _block(self.treaty, "non_fulfillment")
        return sorted(set(re.findall(r"has_modifier = (\w+_modifier)", block)))

    def test_forced_set_is_the_seven_policies(self):
        self.assertEqual(len(self._forced()), 7)
        self.assertNotIn(NOT_FORCED, self._forced())

    def test_waiver_cancels_the_forced_policies_authority_cost(self):
        costs = {m: _authority_cost(m) for m in self._forced()}
        total = sum(costs.values())
        self.assertGreater(total, 0, costs)
        waiver = re.search(r"country_authority_cost_add\s*=\s*(-\d+)", self.source)
        self.assertIsNotNone(waiver, "source_modifier has no authority waiver")
        self.assertEqual(int(waiver.group(1)), -total, costs)

    def test_treaty_charges_no_authority_of_its_own(self):
        # The only authority line in the source modifier is the negative waiver.
        lines = re.findall(r"country_authority_cost_add\s*=\s*(-?\d+)", self.source)
        self.assertEqual(len(lines), 1)
        self.assertLess(int(lines[0]), 0)
        self.assertNotIn("country_authority_cost_add", _block(self.treaty, "target_modifier"))

    def test_industrialists_disapprove(self):
        m = re.search(r"interest_group_ig_industrialists_approval_add\s*=\s*(-\d+)", self.source)
        self.assertIsNotNone(m, "source_modifier has no industrialist disapproval")

    def test_source_needs_the_journal_entry_the_waiver_assumes(self):
        possible = _block(self.treaty, "\tpossible")
        self.assertIn("has_journal_entry = je_global_warming", possible)


if __name__ == "__main__":
    unittest.main()
