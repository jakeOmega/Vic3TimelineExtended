"""Execute the budget allocation script offline and check chart reconciliation.

This verifies math and wiring, not the game's GUI renderer or weekly_profit
accounting. See docs/systems/budget_breakdown.md for the in-game checks.
"""
from decimal import Decimal
from pathlib import Path
import re
import unittest

from paradox_file_parser import ParadoxFileParser
from scripts.generators import gen_budget_breakdown as gen
from test_cultural_hegemony_share import entries

ROOT = Path(__file__).resolve().parent


class BudgetHarness:
    def __init__(self, *, levels=None, production=2800, usage=1400, administration=39000, civil=50000, total=70000, private_construction=0, charges=None):
        parser = ParadoxFileParser()
        self.values = {}
        for name in ("te_budget_values.txt", "te_budget_generated_values.txt"):
            text = (ROOT / "common/script_values" / name).read_text(encoding="utf-8-sig")
            self.values.update({key: val for key, _, val in entries(parser.parse_object(parser.tokenize("{" + text + "}"))[0])})
        self.levels = levels if levels is not None else {"institution_schools": 3, "institution_national_bank": 2}
        self.production = Decimal(production)
        self.scopes = {"total": Decimal(total), "institution_usage": Decimal(usage), "private_construction": Decimal(private_construction)}
        for key, _, getters in gen.EXPENSE:
            self.scopes.update({f"{key}_{i}": Decimal(0) for i in range(len(getters))})
        self.scopes["civil_0"] = Decimal(civil)
        for key, value in (charges or {}).items():
            self.scopes[f"{key}_0"] = Decimal(value)
        self.buildings = [("building_government_administration", -Decimal(administration)), ("building_university", Decimal(-11000))]
        self.scopes["administration_actual"] = self("administration_actual")
        self.scopes["institution_levels"] = self("institution_levels")
        self.scopes["institution_pool"] = self("institution_pool")
        self.scopes["positive_total"] = self("expense_positive_total")

    def __call__(self, name):
        return self.block(self.values["te_budget_" + name])

    def operand(self, item, context=None):
        if isinstance(item, (dict, list)):
            return self.block(item, context=context)
        if item.startswith("scope:"):
            return self.scopes[item[6:]]
        if item == "produced_bureaucracy":
            return self.production
        if item == "investment":
            return Decimal(self.levels[context])
        if item == "weekly_profit":
            return context[1]
        if re.fullmatch(r"-?[\d.]+", item):
            return Decimal(item)
        assert item.startswith("te_budget_"), item
        return self(item[10:])

    def limit(self, node, context=None):
        results = []
        for key, op, value in entries(node):
            if key == "has_institution":
                results.append(value in self.levels)
            elif key == "is_building_type":
                results.append(context[0] == value)
            elif key == "NOT":
                results.append(not self.limit(value, context))
            else:
                left, right = self.operand(key, context), self.operand(value, context)
                results.append({">": left > right, ">=": left >= right, "=": left == right}[op])
        return all(results)

    def block(self, node, acc=Decimal(0), context=None):
        for key, _, value in entries(node):
            if key == "limit":
                continue
            if key == "if":
                limit = next(v for k, _, v in entries(value) if k == "limit")
                if self.limit(limit, context):
                    acc = self.block(value, acc, context)
            elif key == "every_scope_building":
                limit = next(v for k, _, v in entries(value) if k == "limit")
                for building in self.buildings:
                    if self.limit(limit, building):
                        acc = self.block(value, acc, building)
            elif key.startswith("institution:"):
                acc = self.block(value, acc, key[12:])
            else:
                operand = self.operand(value, context)
                if key == "value":
                    acc = operand
                elif key == "add":
                    acc += operand
                elif key == "subtract":
                    acc -= operand
                elif key == "multiply":
                    acc *= operand
                elif key == "divide":
                    acc /= operand
                elif key == "min":
                    acc = max(acc, operand)
                elif key == "max":
                    acc = min(acc, operand)
                else:
                    raise AssertionError(f"Unsupported operation: {key}")
        return acc


class BudgetAllocationTests(unittest.TestCase):
    def test_requested_example(self):
        h = BudgetHarness()
        self.assertEqual(h("administration_actual"), 39000)
        self.assertEqual(h("institution_pool"), 19500)
        self.assertEqual(h("expense_institution_schools"), 11700)
        self.assertEqual(h("expense_institution_national_bank"), 7800)
        self.assertEqual(h("expense_administration"), 19500)
        self.assertEqual(h("expense_civil"), 11000)

    def test_bureaucracy_shortage_never_overallocates(self):
        h = BudgetHarness(usage=4200)
        self.assertEqual(h("institution_pool"), 39000)
        self.assertEqual(h("expense_administration"), 0)

    def test_zero_production_and_no_institutions_keep_general_administration(self):
        for kwargs in ({"production": 0}, {"levels": {}}, {"levels": {"institution_schools": 0}}, {"usage": 0}):
            with self.subTest(kwargs=kwargs):
                h = BudgetHarness(**kwargs)
                self.assertEqual(h("institution_pool"), 0)
                self.assertEqual(h("expense_administration"), 39000)

    def test_wage_change_limits_allocation_to_current_civil_total(self):
        h = BudgetHarness(civil=20000)
        self.assertEqual(h("administration_cost"), 20000)
        self.assertEqual(h("expense_civil"), 0)
        self.assertEqual(h("institution_pool"), 10000)

    def test_changed_level_changes_the_split(self):
        h = BudgetHarness(levels={"institution_schools": 2, "institution_national_bank": 3})
        self.assertEqual(h("expense_institution_schools"), 7800)
        self.assertEqual(h("expense_institution_national_bank"), 11700)

    def test_all_institutions_share_the_same_pool(self):
        h = BudgetHarness(levels=dict.fromkeys(gen.institutions(), 1))
        self.assertAlmostEqual(h("allocated_institutions"), h("institution_pool"))
        self.assertAlmostEqual(h("allocated_institutions") + h("expense_administration"), h("administration_cost"))

    def test_signed_totals_reconcile_and_positive_charts_normalize(self):
        for civil, total in ((50000, 70000), (50000, 25000), (0, 0)):
            h = BudgetHarness(civil=civil, total=total)
            keys = [key for key, _ in gen.categories("expense")]
            self.assertAlmostEqual(sum(h("expense_" + k) for k in keys), total)
            last = Decimal(0)
            for i, key in enumerate(keys):
                cumulative = h(f"expense_cum_{i}")
                self.assertGreaterEqual(cumulative, last)
                self.assertLessEqual(cumulative, 1)
                self.assertAlmostEqual(cumulative - last, h(f"expense_{key}_share"))
                last = cumulative
            self.assertEqual(last, 1 if h("expense_positive_total") else 0)

    def test_negative_income_adjustments_are_preserved_in_list(self):
        h = BudgetHarness()
        h.scopes.update({key: Decimal(0) for key, _, _ in gen.INCOME})
        h.scopes.update(total=Decimal(70), income_tax=Decimal(100), additional=Decimal(-30))
        h.scopes["positive_total"] = h("income_positive_total")
        self.assertEqual(h("income_additional"), -30)
        self.assertEqual(h("income_additional_share"), 0)
        self.assertEqual(h("income_income_tax_share"), 1)
        self.assertEqual(h("income_other"), 0)

    def test_simultaneous_journal_costs_are_separate_without_double_counting(self):
        h = BudgetHarness(civil=0, administration=0, total=18000,
                          charges={"additional": 18000, "banking": 7000, "covert": 4000,
                                   "culture": 3000, "un": 2500, "nuclear": 1000})
        for key, value in (("banking", 7000), ("covert", 4000), ("culture", 3000), ("un", 2500), ("nuclear", 1000), ("additional", 500)):
            self.assertEqual(h("expense_" + key), value)
            self.assertEqual(h("expense_" + key + "_share"), Decimal(value) / 18000)
        self.assertEqual(h("expense_other"), 0)
        self.assertEqual(sum(h("expense_" + key) for key, _ in gen.categories("expense")), 18000)

    def test_source_refunds_preserve_signed_amounts_and_do_not_become_other_costs(self):
        h = BudgetHarness(civil=0, administration=0, total=3000,
                          charges={"additional": 3000, "banking": -1000, "covert": 4000})
        self.assertEqual(h("expense_banking"), -1000)
        self.assertEqual(h("expense_banking_share"), 0)
        self.assertEqual(h("expense_covert_share"), 1)
        self.assertEqual(h("expense_additional"), 0)
        self.assertEqual(h("expense_other"), 0)

    def test_attributed_receipts_leave_only_unattributed_additional_income(self):
        h = BudgetHarness()
        h.scopes.update({key: Decimal(0) for key, _, _ in gen.INCOME})
        h.scopes.update(total=Decimal(2000), additional=Decimal(2000), un=Decimal(1200), reserve=Decimal(700))
        self.assertEqual(h("income_un"), 1200)
        self.assertEqual(h("income_reserve"), 700)
        self.assertEqual(h("income_additional"), 100)
        self.assertEqual(h("income_other"), 0)

    def test_private_construction_is_removed_once_and_totals_reconcile(self):
        h = BudgetHarness(civil=0, administration=0, total=50000, private_construction=30000,
                          charges={"construction": 50000, "military": 30000})
        self.assertEqual(h("expense_construction"), 20000)
        self.assertEqual(h("expense_other"), 0)
        self.assertEqual(sum(h("expense_" + key) for key, _ in gen.categories("expense")), 50000)
        self.assertEqual(h("expense_construction_share"), Decimal('0.4'))
        self.assertNotIn("investment", [key for key, _, _ in gen.INCOME])

    def test_rows_sort_signed_amounts_descending_hide_zeros_and_break_ties(self):
        h = BudgetHarness()
        for side in ("income", "expense"):
            keys = [key for key, _ in gen.categories(side)]
            for amounts in ([0] * len(keys), [100, 100, -5, 0, 250] + [0] * (len(keys) - 5)):
                h.scopes.update({"row_" + key: Decimal(amount) for key, amount in zip(keys, amounts)})
                expected = sorted((key for key, amount in zip(keys, amounts) if amount),
                                  key=lambda key: (-h.scopes["row_" + key], keys.index(key)))
                self.assertEqual(h(side + "_legend_height"), len(expected) * 44)
                self.assertEqual([h(side + "_" + key + "_row_y") for key in expected],
                                 [i * 44 for i in range(len(expected))])


class BudgetWiringTests(unittest.TestCase):
    def test_generated_values_are_current(self):
        self.assertEqual((ROOT / "common/script_values/te_budget_generated_values.txt").read_text(encoding="utf-8-sig"), gen.generated_values())
        self.assertEqual((ROOT / "gui/te_budget_generated_charts.gui").read_text(encoding="utf-8-sig"), gen.generated_gui())
        self.assertEqual((ROOT / "common/modifier_type_definitions/te_budget_generated_types.txt").read_text(encoding="utf-8-sig"), gen.generated_source_types())

    def test_every_recurring_source_has_an_exact_registered_mirror(self):
        parser = ParadoxFileParser()
        modifiers = {}
        for path in (ROOT / "common/static_modifiers").glob("*.txt"):
            obj = parser.parse_object(parser.tokenize("{" + path.read_text(encoding="utf-8-sig") + "}"))[0]
            modifiers.update({key: dict((k, v) for k, _, v in entries(block)) for key, _, block in entries(obj)})
        definitions = parser.parse_object(parser.tokenize("{" + gen.generated_source_types() + "}"))[0]
        definitions = {key: block for key, _, block in entries(definitions)}
        assigned = set()
        for side, groups in gen.SOURCES.items():
            native = "country_expenses_add" if side == "expense" else "country_tax_income_add"
            for key, (_, names) in groups.items():
                mirror = gen.source_type(side, key)
                self.assertEqual(dict((k, v) for k, _, v in entries(definitions[mirror]))["script_only"], "yes")
                for name in names:
                    self.assertNotIn(name, assigned)
                    assigned.add(name)
                    self.assertEqual(modifiers[name][mirror], modifiers[name][native], name)
                    self.assertEqual(sum(k.startswith("country_te_budget_") for k in modifiers[name]), 1, name)
        # The debug cheat remains unattributed. Newly added monetary modifiers
        # must deliberately join a source category rather than silently lumping.
        monetary = {key for key, block in modifiers.items() if "country_expenses_add" in block or "country_tax_income_add" in block}
        self.assertEqual(monetary - assigned, {"cheaty"})

    def test_source_rows_show_the_applied_source_breakdown(self):
        for side in ("income", "expense"):
            chart = gen.chart(side)
            for key in gen.SOURCES[side]:
                self.assertIn(f'tooltip = "te_budget_chart_source_{side}_{key}_tt"', chart)
                loc = (ROOT / "localization/english/te_budget_l_english.yml").read_text(encoding="utf-8-sig")
                self.assertIn(f"GetPlayer.GetModifier.GetDescFor('{gen.source_type(side, key)}')", loc)

    def test_pie_follows_reverse_cumulative_order_without_bar(self):
        for side in ("income", "expense"):
            chart = gen.chart(side)
            found = re.findall(rf"ScriptValue\('te_budget_{side}_cum_(\d+)'\)", chart)
            expected = [str(i) for i in reversed(range(len(gen.categories(side))))]
            self.assertEqual(found, expected)
            self.assertNotIn("progressbar =", chart)
            self.assertEqual(chart.count('framesize = { 128 128 }'), len(expected))

    def test_both_public_headers_exclude_the_transfer(self):
        for side, getter in (("income", "PredictWeeklyIncome"), ("expense", "GetWeeklyExpenses")):
            scope = gen.scope(side)
            self.assertIn(f"Subtract_CFixedPoint(GetPlayer.{getter}, GetPlayer.GetInvestmentIncome)", scope)
            self.assertIn("TopScope.ScriptValue('te_budget_total')", gen.section(side))

    def test_budget_tab_is_always_available(self):
        gui = (ROOT / "gui/budget_panel.gui").read_text(encoding="utf-8-sig")
        self.assertIn("te_tab_buttons_six = {", gui)
        self.assertIn("InformationPanel.SelectTab('te_breakdown')", gui)
        self.assertIn("te_budget_breakdown_panel = {}", gui)

    def test_nested_chart_math_uses_passed_values_without_building_scans(self):
        values = gen.generated_values()
        self.assertNotIn("every_scope_building", values)
        self.assertIn("value = scope:institution_pool", values)
        self.assertIn("value = scope:positive_total", values)


if __name__ == "__main__":
    unittest.main()
