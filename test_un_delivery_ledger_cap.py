"""The UN delivery ledger holds only what its pillar can show, 0..un_delivery_cap.

Uncapped, the ledger banked a surplus: the 2015 observer save held 24.9
against a cap of 10, so the Delivery pillar sat at +10 for years whatever the
UN delivered (owner report and ruling, 2026-10-06). un_delivery_ledger_clamp
bounds it after every ledger entry and after the monthly decay, which also
repairs a save that banked a surplus before the cap.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EFFECTS = ROOT / "common/scripted_effects/un_authority_effects.txt"


def _block(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class TestUnDeliveryLedgerCap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = re.sub(r"#[^\n]*", "", EFFECTS.read_text(encoding="utf-8-sig"))

    def test_the_clamp_bounds_the_ledger_to_the_pillar_range(self):
        clamp = _block(self.text, "un_delivery_ledger_clamp")
        self.assertRegex(clamp, r"global_var:un_ledger_delivery\s*>\s*un_delivery_cap")
        self.assertRegex(clamp, r"name\s*=\s*un_ledger_delivery\s+value\s*=\s*un_delivery_cap")
        self.assertRegex(clamp, r"global_var:un_ledger_delivery\s*<\s*0")
        self.assertRegex(clamp, r"name\s*=\s*un_ledger_delivery\s+value\s*=\s*0\b")
        self.assertIn("has_global_variable = un_ledger_delivery", clamp)

    def test_every_entry_is_clamped_after_it_is_added(self):
        record = _block(self.text, "un_ledger_record")
        added = record.index("change_global_variable = { name = un_ledger_$PILLAR$ add")
        self.assertGreater(record.find("un_delivery_ledger_clamp = yes", added), added)

    def test_the_monthly_decay_clamps_too(self):
        monthly = _block(self.text, "un_authority_monthly_update")
        decay = monthly.index("name = un_ledger_delivery multiply")
        self.assertGreater(monthly.find("un_delivery_ledger_clamp = yes", decay), decay)


if __name__ == "__main__":
    unittest.main()
