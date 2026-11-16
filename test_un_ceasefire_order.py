"""The UN's cease-fire order keeps its counters (docs/systems/un_redesign_design.md
§0.12 item 6; the header of common/scripted_effects/un_order_effects.txt).

An order lives in variables on the aggressor: it starts in
`un_ceasefire_order_impose`, runs a month at a time in
`un_ceasefire_order_month`, and ends in `un_ceasefire_order_clear`. The month
counts with `change_variable`, which does nothing on a variable that is not
set and logs an error instead. Until #1818 the unbooked debit,
`un_cf_debit_months`, was changed every month and set nowhere but in the reset
after a booking, so no order ever cost the UN's peace and order anything: 68
log lines over 17 months of one game were the only sign.

- Every counter the month changes is started when the order is imposed, and
  every variable the order keeps is removed when it ends.
- Each change in the file has a set that can run first (the mod-wide
  `change_variable_init_audit`, held here to this file alone).
- The debit counts each month of fighting on and no other month, is booked at
  the batch size, and is booked before every ending.

Run: python3 -m unittest test_un_ceasefire_order -v
"""
from __future__ import annotations

import os
import re
import unittest
from collections import Counter

import change_variable_init_audit
from blanked_text import blank_comments_and_strings
from variable_guard_audit import parse_tree

ROOT = os.path.dirname(os.path.abspath(__file__))
REL = "common/scripted_effects/un_order_effects.txt"

IMPOSE = "un_ceasefire_order_impose"
MONTH = "un_ceasefire_order_month"
BOOK = "un_ceasefire_book_accrued_debit"
CLEAR = "un_ceasefire_order_clear"


def _text() -> str:
    with open(os.path.join(ROOT, REL), encoding="utf-8-sig") as fh:
        return fh.read()


def _effects() -> dict:
    tree = parse_tree(blank_comments_and_strings(_text())[0])
    return {child[1].key: child[1] for child in tree.children if child[0] == "block"}


def _statements(node, depth=0):
    """Every statement under `node`, in source order: (key, child, depth)."""
    for child in node.children:
        if child[0] == "scalar":
            yield child[1], child, depth
        elif child[0] == "block":
            yield child[1].key, child, depth
            yield from _statements(child[1], depth + 1)


def _named(child) -> str | None:
    """The variable a set / change / remove statement names."""
    if child[0] == "scalar":
        return child[3]
    return next((c[3] for c in child[1].children if c[0] == "scalar" and c[1] == "name"), None)


def _names(node, key: str) -> list[str]:
    return [_named(child) for k, child, _ in _statements(node) if k == key]


def _block(node, key: str):
    return next(child[1] for k, child, _ in _statements(node) if k == key and child[0] == "block")


def _calls(node) -> list[str]:
    """The `name = yes` calls directly in `node`, in order."""
    return [c[1] for c in node.children if c[0] == "scalar" and c[3] == "yes"]


class CeasefireOrderCounters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _effects()

    def test_every_counter_the_month_changes_starts_at_imposition(self):
        changed = sorted(set(_names(self.effects[MONTH], "change_variable")))
        # The order's months, the months fought on, the unbooked debit.
        self.assertEqual(changed, ["un_cf_debit_months", "un_cf_fought_months", "un_cf_order_months"])
        # Set outright as the effect's own statements, not inside an `if`.
        started = {_named(c) for c in self.effects[IMPOSE].children
                   if c[0] != "bare" and (c[1] if c[0] == "scalar" else c[1].key) == "set_variable"}
        for name in changed:
            self.assertIn(name, started, f"{IMPOSE} never sets {name}, so {MONTH}'s change_variable fails")

    def test_every_change_in_the_file_has_a_set_that_can_run_first(self):
        # The file alone: no other file, and nothing of vanilla's, sets these.
        result = change_variable_init_audit.judge({REL: _text()})
        self.assertEqual([(f.line, f.message) for f in result.flags], [])
        # It judged every change the file writes (comments aside).
        written = re.findall(r"\bchange_variable\s*=\s*\{", blank_comments_and_strings(_text())[0])
        self.assertEqual((result.judged, result.unjudged), (len(written), 0))
        self.assertGreaterEqual(len(written), 4)

    def test_the_order_ends_with_none_of_its_variables(self):
        kept = set()
        for name in (IMPOSE, MONTH, BOOK, "un_ceasefire_on_tabled"):
            kept.update(n for n in _names(self.effects[name], "set_variable") if n.startswith("un_cf_"))
        self.assertIn("un_cf_debit_months", kept)
        removed = set(_names(self.effects[CLEAR], "remove_variable"))
        self.assertEqual(sorted(kept - removed), [])


class CeasefireOrderDebit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _effects()
        cls.month = cls.effects[MONTH]

    def test_a_month_of_fighting_on_counts_one_and_books_at_the_batch(self):
        fighting = next(child[1] for child in self.month.children
                        if child[0] == "block" and child[1].key == "if"
                        and "un_order_wages_war_on_member" in [c[1] for c in _block(child[1], "limit").children])
        own = [(c[1] if c[0] == "scalar" else c[1].key, c) for c in fighting.children if c[0] != "bare"]
        count = [i for i, (key, c) in enumerate(own) if key == "change_variable" and _named(c) == "un_cf_debit_months"]
        self.assertEqual(len(count), 1, "one count a month, in the fighting branch itself")
        # And nowhere else in the month: a second count outside the branch
        # would charge the months the aggressor does not fight (the mutation
        # the review of PR #1850 found this test let through).
        self.assertEqual(Counter(_names(self.month, "change_variable")),
                         {"un_cf_order_months": 1, "un_cf_fought_months": 1, "un_cf_debit_months": 1})
        adds = [c for c in own[count[0]][1][1].children if c[0] == "scalar" and c[1] == "add"]
        self.assertEqual([c[3] for c in adds], ["1"])
        # The next statement books the batch once it is full.
        key, batch = own[count[0] + 1]
        self.assertEqual(key, "if")
        limit = [(c[1], c[2], c[3]) for c in _block(batch[1], "limit").children if c[0] == "scalar"]
        self.assertEqual(limit, [("var:un_cf_debit_months", ">=", "un_cf_order_debit_batch_months")])
        self.assertEqual(_calls(batch[1]), [BOOK])

    def test_every_ending_books_what_has_accrued_first(self):
        # "The accrued debit (ledger 30) is booked on every ending."
        endings = [child[1] for _, child, _ in _statements(self.month)
                   if child[0] == "block" and CLEAR in _calls(child[1])]
        self.assertEqual(len(endings), 5, "defied (run out), moot, defied (gained), kept, victim gone")
        for block in endings:
            calls = _calls(block)
            self.assertEqual(calls[0], BOOK, f"line {block.line}: {calls}")
            self.assertEqual(calls[-1], CLEAR, f"line {block.line}: {calls}")

    def test_a_booking_is_one_ledger_entry_and_starts_the_count_again(self):
        book = self.effects[BOOK]
        guard = _block(book, "limit")
        self.assertEqual([(c[1], c[2], c[3]) for c in guard.children if c[0] == "scalar"],
                         [("has_variable", "=", "un_cf_debit_months"), ("var:un_cf_debit_months", ">", "0")])
        entry = _block(book, "un_ledger_entry_on")
        args = {c[1]: c[3] for c in entry.children if c[0] == "scalar"}
        self.assertEqual((args["PILLAR"], args["POINTS"], args["REASON"]),
                         ("order", "un_cf_order_debit_accrued", "30"))
        reset = [c for k, c, _ in _statements(book) if k == "set_variable"]
        self.assertEqual([_named(c) for c in reset], ["un_cf_debit_months"])
        self.assertEqual([c[3] for c in reset[0][1].children if c[0] == "scalar" and c[1] == "value"], ["0"])


if __name__ == "__main__":
    unittest.main()
