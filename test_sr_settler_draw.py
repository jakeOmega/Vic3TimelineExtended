# -*- coding: utf-8 -*-
"""The settler draw (colony people design § 6.3): its Python twin's rule, and
the script that follows it (sr_emig_month, te_demog_sr_note_settlers).

Run: python3 -m pytest test_sr_settler_draw.py -q
"""

import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "analysis"))

import sr_settler_draw as D  # noqa: E402


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    if not m:
        raise AssertionError(f"no block {name}")
    depth, i = 0, m.end() - 1
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
    raise AssertionError(f"unclosed {name}")


def _inner(text, opener):
    """The body of the first block opened by `opener` (e.g. "ordered_scope_state = {")."""
    i = text.index(opener) + len(opener) - 1
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
    raise AssertionError(f"unclosed {opener}")


def _run(amount, pops, months):
    carries = [0.0] * len(pops)
    totals = [0] * len(pops)
    sent = []
    for _ in range(months):
        takes, carries = D.draw(amount, list(zip(pops, carries)))
        totals = [t + k for t, k in zip(totals, takes)]
        sent.append(sum(takes))
    return totals, carries, sent


class TwinTest(unittest.TestCase):
    def test_every_state_gives_in_proportion_within_a_batch(self):
        pops = [4_000_000, 2_000_000, 100_000]
        totals, _, _ = _run(32_000, pops, 12)
        people = sum(pops)
        for pop, total in zip(pops, totals):
            with self.subTest(pop=pop):
                self.assertLessEqual(abs(total - 12 * 32_000 * pop / people), D.BATCH)
                self.assertEqual(total % D.BATCH, 0)

    def test_a_month_never_sends_more_than_the_amount(self):
        for amount in (500, 1_000, 8_000, 32_000):
            _, _, sent = _run(amount, [4_000_000, 2_000_000, 100_000, 30_000, 9_000], 24)
            with self.subTest(amount=amount):
                self.assertTrue(all(s <= amount for s in sent), sent)
                # and averages it: within a batch a state over two years
                self.assertLessEqual(abs(sum(sent) - 24 * amount), 5 * D.BATCH)

    def test_past_one_percent_of_the_people_a_month_sends_one_percent(self):
        """Review Focus 2: an amount of 10% of the people."""
        pops = [3_000_000, 1_000_000]
        takes, _ = D.draw(400_000, [(p, 0.0) for p in pops])
        self.assertEqual(sum(takes), 40_000)
        self.assertEqual(D.month_batches(400_000, 4_000_000), 80)

    def test_a_state_the_month_runs_out_before_keeps_its_whole_due(self):
        takes, carries = D.draw(500, [(1_000_000, 0.0), (1_000_000, 0.0)])
        self.assertEqual(sorted(takes), [0, 0])
        self.assertEqual(carries, [250.0, 250.0])
        takes, carries = D.draw(500, [(1_000_000, 250.0), (1_000_000, 300.0)])
        self.assertEqual(takes, [0, 500])
        self.assertEqual(carries, [500.0, 50.0])

    def test_nothing_from_no_people(self):
        self.assertEqual(D.draw(2_000, []), ([], []))
        self.assertEqual(D.draw(2_000, [(0, 0.0)]), ([0], [0.0]))


class ScriptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _strip(_raw("common", "scripted_effects", "sr_colony_population_effects.txt"))
        cls.values = _strip(_raw("common", "script_values", "sr_colony_population_values.txt"))
        cls.census = _strip(_raw("common", "scripted_effects", "te_demog_resettle_effects.txt"))
        cls.month = _block(cls.effects, "sr_emig_month")

    def test_the_month_is_gated_as_before(self):
        for term in ("sr_colonies_contested_enabled = yes", "sr_has_space_program = yes",
                     "NOT = { sr_launches_barred = yes }", "sr_emig_month_batches >= 1"):
            self.assertIn(term, self.month)

    def test_the_cap_and_the_share(self):
        self.assertIn("sr_emig_people_cap = { value = 0.01 }", self.values)
        batches = _block(self.values, "sr_emig_month_batches")
        self.assertIn("value = sr_emig_batches_now", batches)
        cap = _block(self.values, "sr_emig_people_batches")
        self.assertIn("value = total_population", cap)
        self.assertIn("multiply = sr_emig_people_cap", cap)
        self.assertIn("divide = sr_emig_batch_people", cap)
        self.assertIn("floor = yes", cap)
        self.assertIn("max = sr_emig_people_batches", batches)

    def test_two_passes_over_the_states(self):
        due = _inner(self.month, "every_scope_state = {")
        self.assertIn("name = sr_emig_due", due)
        self.assertIn("state_population", due)
        self.assertIn("var:sr_emig_carry", due)
        take = _inner(self.month, "ordered_scope_state = {")
        self.assertIn("order_by = sr_emig_due_value", take)
        self.assertIn("check_range_bounds = no", take)
        self.assertIn("local_var:sr_emig_left >= 1", take)
        self.assertLess(self.month.index("every_scope_state = {"), self.month.index("ordered_scope_state = {"))
        self.assertIn("sr_emig_due_value = {", self.values)

    def test_the_take_kills_whole_batches_and_keeps_the_rest(self):
        take = _inner(self.month, "ordered_scope_state = {")
        loop = _inner(take, "while = {")
        self.assertIn("count = local_var:sr_emig_take", loop)
        self.assertIn("kill_population_in_state = { value = 250 strata = middle }", loop)
        self.assertIn("kill_population_in_state = { value = 250 strata = lower }", loop)
        self.assertIn("te_demog_sr_note_settlers = yes", take)
        self.assertIn("name = sr_emig_carry", take)
        self.assertIn("remove_variable = sr_emig_due", take)
        self.assertLess(self.month.index("ordered_scope_state = {"), self.month.index("sr_emig_distribute = yes"))
        self.assertIn("set_variable = { name = sr_emig_last_sent value = local_var:sr_emig_sent }", self.month)

    def test_the_census_books_the_source_side_by_the_family_profile(self):
        body = _block(self.census, "te_demog_sr_note_settlers")
        self.assertIn("te_demog_cohorts_run = yes", body)
        self.assertIn("te_demog_has_census = yes", body)
        self.assertIn("set_local_variable = { name = te_dg_rs_code value = 3 }", body)
        self.assertIn("set_local_variable = { name = te_dg_rs_amt value = local_var:sr_emig_took_now }", body)
        self.assertIn("te_demog_rs_add = { SIDE = o }", body)
        self.assertIn("te_demog_rs_total = { NAME = te_dg_rs_out }", body)
        self.assertNotIn("SIDE = i", body)
        self.assertNotIn("te_dg_rs_in", body)

    def test_the_self_check_sums_the_falls(self):
        take = _inner(self.month, "ordered_scope_state = {")
        self.assertIn("sr_emig_fell_before", take)
        check = _block(self.effects, "sr_emig_self_check")
        self.assertIn("sr_emig_log_fell >= sr_emig_log_fell_needed", check)


if __name__ == "__main__":
    unittest.main()
