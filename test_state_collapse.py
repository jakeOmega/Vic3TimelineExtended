"""State Collapse runs only on a country that still holds a state.

A country that has lost every state has no pops and no living standard to
measure, yet je_state_collapse stayed active on one and went on collapsing it:
Dharampur, landless in the 2026-10-06 observer run, carried two Failed State
modifiers. Both the entry's visibility and its activation now require a
capital, so can_deactivate returns it to inactive when the last state goes.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _block(text, name):
    m = re.search(r"^\t?" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class TestStateCollapseGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = (ROOT / "common/journal_entries/timeline_extended_journal_entries.txt").read_text(encoding="utf-8-sig")
        text = re.sub(r"#[^\n]*", "", text)
        cls.entry = _block(text, "je_state_collapse")

    def test_both_gates_need_a_capital(self):
        for gate in ("is_shown_when_inactive", "possible"):
            self.assertRegex(_block(self.entry, gate), r"\bexists\s*=\s*capital\b", gate)

    def test_the_entry_can_deactivate(self):
        self.assertRegex(self.entry, r"\bcan_deactivate\s*=\s*yes\b")


if __name__ == "__main__":
    unittest.main()
