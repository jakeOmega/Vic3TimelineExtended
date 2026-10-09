"""Execute the budget allocation script offline and check chart reconciliation.

This verifies math and wiring, not the game's GUI renderer or weekly_profit
accounting. See docs/systems/budget_breakdown.md for the in-game checks.
"""
import json
from decimal import Decimal
from itertools import product
from pathlib import Path
import re
import unittest

from paradox_file_parser import ParadoxFileParser
from scripts.generators import gen_budget_breakdown as gen
from test_cultural_hegemony_share import entries

ROOT = Path(__file__).resolve().parent


class BudgetHarness:
    def __init__(self, *, levels=None, production=2800, usage=1400, administration=39000, civil=50000, total=70000, private_construction=0, charges=None, military_fields=None, military_buildings=(), space_program=0):
        parser = ParadoxFileParser()
        self.values = {}
        for name in ("te_budget_values.txt", "te_budget_generated_values.txt"):
            text = (ROOT / "common/script_values" / name).read_text(encoding="utf-8-sig")
            self.values.update({key: val for key, _, val in entries(parser.parse_object(parser.tokenize("{" + text + "}"))[0])})
        self.levels = levels if levels is not None else {"institution_schools": 3, "institution_national_bank": 2}
        self.production = Decimal(production)
        self.building_definitions = json.loads((ROOT / "vanilla_parsed/common/buildings.json").read_text())
        # A mod building (common/buildings/extra_buildings.txt), not in vanilla's snapshot.
        self.building_definitions.setdefault("building_space_program", ["=", {"building_group": ["=", "bg_monuments"]}])
        self.scopes = {"total": Decimal(total), "institution_usage": Decimal(usage), "private_construction": Decimal(private_construction)}
        for key, _, getters in gen.EXPENSE:
            self.scopes.update({f"{key}_{i}": Decimal(0) for i in range(len(getters))})
        self.scopes.update({key: Decimal(0) for key in gen.MILITARY_FIELDS})
        self.scopes.update({key: Decimal(value) for key, value in (military_fields or {}).items()})
        for side in ("income", "expense"):
            self.scopes.update({"open_" + node.key: Decimal(0) for node, _ in gen.walk(gen.tree(side)) if node.children})
        self.scopes["civil_0"] = Decimal(civil)
        for key, value in (charges or {}).items():
            self.scopes[f"{key}_0"] = Decimal(value)
        self.buildings = [("building_government_administration", -Decimal(administration)), ("building_university", Decimal(-11000)),
                          *((key, -Decimal(cost)) for key, cost in military_buildings)]
        if space_program:
            self.buildings.append(("building_space_program", -Decimal(space_program)))
        self.scopes["administration_actual"] = self("administration_actual")
        self.scopes["space_program_actual"] = self("space_program_actual")
        self.scopes["institution_levels"] = self("institution_levels")
        self.scopes["institution_pool"] = self("institution_pool")
        for branch in ("army", "navy"):
            self.scopes[branch + "_support_actual"] = self(branch + "_support_actual")
        self.scopes["positive_total"] = self("expense_positive_total")

    def __call__(self, name):
        return self.block(self.values["te_budget_" + name])

    def operand(self, item, context=None):
        if isinstance(item, (dict, list)):
            return self.block(item, context=context)
        if item.startswith("scope:"):
            key = item[6:]
            if key.startswith("positive_") and key != "positive_total":
                return self(key[9:] + "_positive")
            return self.scopes[key]
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
            elif key == "is_building_group":
                results.append(self.building_definitions[context[0]][1]["building_group"][1] == value)
            elif key == "OR":
                results.append(any(self.limit({k: [op, v]}, context) for k, op, v in entries(value)))
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
            for i, (node, _) in enumerate(gen.walk(gen.tree("expense"))):
                cumulative = h(f"expense_cum_{i}")
                self.assertGreaterEqual(cumulative, last)
                self.assertLessEqual(cumulative, 1)
                self.assertAlmostEqual(cumulative - last, h(f"expense_{node.key}_slice") / max(h.scopes["positive_total"], Decimal("0.001")))
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

    def test_space_program_moves_from_civil_buildings_to_space_race(self):
        # Civil getters cover administration 39000, a university 11000 and the
        # Space Program 8000. The debris-clearance charge is 500.
        h = BudgetHarness(civil=58000, total=58500, space_program=8000, charges={"additional": 500, "space": 500})
        self.assertEqual(h("space_program_actual"), 8000)
        self.assertEqual(h("expense_space"), 8500)
        self.assertEqual(h("expense_civil"), 11000)
        self.assertEqual(h("expense_additional"), 0)
        self.assertEqual(h("expense_programmes"), 8500)
        self.assertEqual(h("expense_other"), 0)
        self.assertEqual(sum(h("expense_" + key) for key, _ in gen.categories("expense")), 58500)

    def test_space_program_never_takes_more_than_civil_after_administration(self):
        h = BudgetHarness(civil=41000, total=41000, space_program=8000)
        self.assertEqual(h("administration_cost"), 39000)
        self.assertEqual(h("space_program_cost"), 2000)
        self.assertEqual(h("expense_space"), 2000)
        self.assertEqual(h("expense_civil"), 0)

    def test_no_space_program_leaves_space_race_to_its_charges(self):
        h = BudgetHarness(civil=50000, total=50300, charges={"additional": 300, "space": 300})
        self.assertEqual(h("expense_space"), 300)
        self.assertEqual(h("expense_civil"), 11000)
        self.assertEqual(h("expense_additional"), 0)

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

    def test_empty_groups_have_no_display_rows(self):
        h = BudgetHarness(civil=0, administration=0, total=0)
        nodes = list(gen.walk(gen.tree("expense")))
        h.scopes.update({"subtree_" + node.key: h("expense_" + node.key + "_subtree_rows") for node, _ in nodes})
        self.assertEqual(h("expense_display_count"), 0)
        self.assertTrue(all(h("expense_" + node.key + "_visible") == 0 for node, _ in nodes))

    def test_military_branch_breakdowns_reconcile_wages_goods_and_ship_costs(self):
        h = BudgetHarness(civil=0, administration=0, total=20500,
                          charges={"military": 10000},
                          military_fields={"army_total": 10000, "army_goods": 4000,
                                           "navy_total": 6000, "navy_goods": 2000})
        h.scopes.update(military_1=Decimal(6000), military_2=Decimal(500),
                        military_3=Decimal(3000), military_4=Decimal(1000))
        for key, expected in (("army_wages", 6000), ("army_materials", 4000), ("army", 10000),
                              ("navy_wages", 4000), ("navy_materials", 6000), ("navy", 10000),
                              ("military_adjustment", 500), ("military", 20500)):
            self.assertEqual(h("expense_" + key), expected)
        self.assertEqual(h("expense_other"), 0)

    def test_screenshot_barracks_wages_are_not_subtracted_from_logistics_upkeep(self):
        # Rounded tooltip amounts: barracks wages are a separate country cost,
        # not part of the Army Logistics Center's weekly operating deficit.
        h = BudgetHarness(civil=0, administration=0, total=64773,
                          charges={"military": 23523, "shipping": 1560},
                          military_fields={"army_total": 18600, "navy_total": 2690},
                          military_buildings=(("building_barrack", 0),
                                              ("building_army_logistics_center", 30860),
                                              ("building_naval_administration", 2690),
                                              ("building_naval_logistics_center", 3743),
                                              ("building_naval_fortification", 3130)))
        h.scopes.update(military_1=Decimal(35500), military_4=Decimal(4190))
        self.assertEqual(h("expense_army_wages"), 18600)
        self.assertEqual(h("expense_army_materials"), 30860)
        self.assertEqual(h("expense_army"), 49460)
        self.assertEqual(h("expense_navy_materials"), 11063)
        self.assertEqual(h("expense_navy"), 13753)
        self.assertEqual(h("expense_military"), 63213)
        self.assertEqual(h("expense_shipping"), 1560)
        self.assertEqual(h("expense_military_adjustment"), 0)
        self.assertEqual(h("expense_other"), 0)

    def test_logistics_and_fortifications_belong_to_branch_support_not_other(self):
        # Modern branch goods getters return zero despite £8,470 of goods in
        # the military total. Support also includes £590 of logistics wages.
        h = BudgetHarness(civil=0, administration=0, total=15390,
                          charges={"military": 4340},
                          military_fields={"army_total": 2040, "navy_total": 1710},
                          military_buildings=(("building_barrack", 2040),
                                              ("building_army_logistics_center", 4640),
                                              ("building_naval_administration", 1710),
                                              ("building_naval_logistics_center", 2880),
                                              ("building_naval_fortification", 1540)))
        h.scopes.update(military_1=Decimal(8470), military_4=Decimal(2580))
        self.assertEqual(h("army_support_actual"), 4640)
        self.assertEqual(h("navy_support_actual"), 4420)
        self.assertEqual(h("expense_army_materials"), 4640)
        self.assertEqual(h("expense_army"), 6680)
        self.assertEqual(h("expense_navy_materials"), 7000)
        self.assertEqual(h("expense_navy"), 8710)
        self.assertEqual(h("expense_military_adjustment"), 0)
        self.assertEqual(h("expense_other"), 0)
        h.scopes["positive_total"] = h("expense_positive_total")
        h.scopes.update(open_military=Decimal(1), open_army=Decimal(1), open_navy=Decimal(1))
        self.assertEqual(h("expense_army_materials_slice"), 4640)
        self.assertAlmostEqual(h("expense_army_materials_share"), Decimal(4640) / 15390)

    def test_already_covered_branch_buildings_are_excluded_from_support(self):
        for actual in (0, 9000, 10000, 12500):
            with self.subTest(actual=actual):
                h = BudgetHarness(civil=0, administration=0, total=16000,
                                  charges={"military": 16000},
                                  military_fields={"army_total": 10000, "army_goods": 4000,
                                                   "navy_total": 6000, "navy_goods": 2000},
                                  military_buildings=(("building_barrack", actual),
                                                      ("building_conscription_center", actual),
                                                      ("building_naval_administration", actual)))
                self.assertEqual(h("army_support_actual"), 0)
                self.assertEqual(h("navy_support_actual"), 0)
                self.assertEqual(h("expense_army_wages"), 6000)
                self.assertEqual(h("expense_army_materials"), 4000)
                self.assertEqual(h("expense_navy_materials"), 2000)
                self.assertEqual(h("expense_military_adjustment"), 0)
                self.assertEqual(h("expense_other"), 0)

    def test_support_cost_is_independent_of_branch_wage_forecast(self):
        for wages in (0, 1000, 10000):
            h = BudgetHarness(civil=0, administration=0, total=wages + 500,
                              charges={"military": wages + 500},
                              military_fields={"army_total": wages},
                              military_buildings=(("building_army_logistics_center", 500),))
            self.assertEqual(h("expense_army_wages"), wages)
            self.assertEqual(h("expense_army_materials"), 500)
            self.assertEqual(h("expense_military_adjustment"), 0)
            self.assertEqual(h("expense_other"), 0)

    def test_only_branch_buildings_with_operating_deficits_are_attributed(self):
        h = BudgetHarness(military_buildings=(("building_army_logistics_center", -500),
                                               ("building_barrack", 5000),
                                               ("building_conscription_center", 3000),
                                               ("building_arms_industry", 10000)))
        self.assertEqual(h("army_support_actual"), 0)
        self.assertEqual(h("navy_support_actual"), 0)
        self.assertEqual(h("administration_actual"), 39000)

    def test_group_totals_equal_children_without_double_counting(self):
        h = BudgetHarness(charges={"military": 10000, "shipping": 1500, "additional": 800,
                                   "banking": -200, "covert": 1000})
        h.scopes.update({key: Decimal(100) for key, _, _ in gen.INCOME})
        for side in ("income", "expense"):
            for node, _ in gen.walk(gen.tree(side)):
                if node.children:
                    self.assertAlmostEqual(h(side + "_" + node.key),
                                           sum(h(side + "_" + child.key) for child in node.children))
            self.assertAlmostEqual(sum(h(side + "_" + node.key) for node in gen.tree(side)), h.scopes["total"])

    def test_every_expansion_state_partitions_positive_leaf_amounts(self):
        h = BudgetHarness(charges={"military": 15000, "additional": 800, "banking": -200, "covert": 1000},
                          military_fields={"army_total": 7000, "army_goods": 2000, "navy_total": 3000, "navy_goods": 1000},
                          military_buildings=(("building_barrack", 7000), ("building_army_logistics_center", 3000),
                                              ("building_naval_administration", 3000), ("building_naval_fortification", 2000)))
        h.scopes.update({key: Decimal(100) for key, _, _ in gen.INCOME})
        for side in ("income", "expense"):
            nodes = list(gen.walk(gen.tree(side)))
            groups = [node for node, _ in nodes if node.children]
            total = h(side + "_positive_total")
            h.scopes["positive_total"] = total
            leaves = sum(max(h(side + "_" + node.key), 0) for node, _ in nodes if not node.children)
            self.assertAlmostEqual(total, leaves)
            for state in product((0, 1), repeat=len(groups)):
                h.scopes.update({"open_" + node.key: Decimal(value) for node, value in zip(groups, state)})
                h.scopes.update({"row_" + node.key: h(side + "_" + node.key) for node, _ in nodes})
                h.scopes.update({"subtree_" + node.key: h(side + "_" + node.key + "_subtree_rows") for node, _ in nodes})
                def sorted_visible(siblings):
                    # Stable descending sort at each level, then preorder.
                    for item in sorted(siblings, key=lambda item: -h(side + "_" + item.key)):
                        if not h(side + "_" + item.key + "_active"):
                            continue
                        yield item.key
                        if item.children and h.scopes["open_" + item.key]:
                            yield from sorted_visible(item.children)
                ordered = list(sorted_visible(gen.tree(side)))
                self.assertEqual(h(side + "_display_count"), len(ordered))
                h.scopes.update({"rank_" + node.key: h(side + "_" + node.key + "_display_rank") for node, _ in nodes})
                for rank, key in enumerate(ordered):
                    self.assertEqual(h(side + "_" + key + "_cached_rank"), rank)
                self.assertEqual({node.key for node, _ in nodes if h(side + "_" + node.key + "_visible")}, set(ordered))
                slices = []
                for node, ancestors in nodes:
                    visible = all(h.scopes["open_" + p.key] for p in ancestors)
                    visible = visible and (not node.children or not h.scopes["open_" + node.key])
                    actual = h(side + "_" + node.key + "_slice")
                    self.assertEqual(actual, h(side + "_" + node.key + "_positive") if visible else 0)
                    slices.append(actual)
                self.assertAlmostEqual(sum(slices), total)
                self.assertEqual(h(side + "_cum_" + str(len(nodes) - 1)), 1)

    def test_zero_net_group_keeps_cost_and_refund_accessible(self):
        h = BudgetHarness(civil=0, administration=0, total=0, charges={"banking": -1000, "covert": 1000})
        self.assertEqual(h("expense_programmes"), 0)
        self.assertEqual(h("expense_programmes_active"), 1)
        self.assertEqual(h("expense_programmes_slice"), 1000)
        self.assertEqual(h("expense_programmes_share"), 1)
        h.scopes["open_programmes"] = Decimal(1)
        self.assertEqual(h("expense_programmes_slice"), 0)
        self.assertEqual(h("expense_banking_slice"), 0)
        self.assertEqual(h("expense_covert_slice"), 1000)
        self.assertEqual(h("expense_banking_active"), 1)
        self.assertEqual(h("expense_positive_total"), 1000)

    def test_parent_collapse_hides_previously_open_descendants(self):
        h = BudgetHarness(civil=0, administration=0, total=10000, charges={"military": 10000},
                          military_fields={"army_total": 10000, "army_goods": 4000})
        h.scopes["open_army"] = Decimal(1)
        self.assertEqual(h("expense_army_wages_slice"), 0)
        self.assertEqual(h("expense_military_slice"), 10000)
        h.scopes["open_military"] = Decimal(1)
        self.assertEqual(h("expense_military_slice"), 0)
        self.assertEqual(h("expense_army_slice"), 0)
        self.assertEqual(h("expense_army_wages_slice"), 6000)
        self.assertEqual(h("expense_army_materials_slice"), 4000)


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
            native = gen.NATIVE[side]
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

    def test_mirror_lines_read_as_breakdown_labels(self):
        # A source modifier's tooltip lists the mirror beside its native field,
        # and no modifier-type key hides it. So the mirror prints the native
        # line's figure in the same format and is named as a label: the playtest
        # read "£+11570607.7 Government Expenses" over "£+11570607.74 Colonial
        # Development: Weekly Expenses" as a second charge.
        parser = ParadoxFileParser()
        definitions = parser.parse_object(parser.tokenize("{" + gen.generated_source_types() + "}"))[0]
        definitions = {key: dict((k, v) for k, _, v in entries(block)) for key, _, block in entries(definitions)}
        vanilla = json.loads((ROOT / "vanilla_parsed/common/modifier_types.json").read_text())
        loc = (ROOT / "localization/english/te_budget_l_english.yml").read_text(encoding="utf-8-sig")
        for side, groups in gen.SOURCES.items():
            native = {k: v[1] for k, v in vanilla[gen.NATIVE[side]][1].items()}
            for key, (label, _) in groups.items():
                mirror = gen.source_type(side, key)
                self.assertEqual(definitions[mirror]["decimals"], native["decimals"], mirror)
                self.assertEqual(definitions[mirror]["prefix"], native["prefix"], mirror)
                self.assertEqual(definitions[mirror]["color"], "neutral", mirror)
                self.assertIn(f' {mirror}:0 "Counted in the Budget Breakdown under {label}"\n', loc)
                desc = re.search(rf'^ {mirror}_desc:0 "(.*)"$', loc, re.M).group(1)
                self.assertIn(f"${gen.NATIVE[side]}$ line already includes this amount", desc)

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
            expected = [str(i) for i in reversed(range(len(list(gen.walk(gen.tree(side))))))]
            self.assertEqual(found, expected)
            self.assertNotIn("progressbar =", chart)
            self.assertEqual(chart.count('framesize = { 128 128 }'), len(expected))

    def test_sorted_rows_use_flow_slots_instead_of_expression_vectors(self):
        from scripts.analysis.check_gui_lint import bare_vector_expressions
        gui = gen.generated_gui()
        self.assertEqual(bare_vector_expressions(gui), [])
        for side in ("income", "expense"):
            chart = gen.chart(side)
            keys = [node.key for node, _ in gen.walk(gen.tree(side))]
            self.assertIn(f"type te_budget_{side}_list_root = flowcontainer", chart)
            self.assertIn(f"type te_budget_{side}_slot_root = flowcontainer", chart)
            self.assertNotIn("position =", chart)
            slots = re.findall(r"AddScope\('row_slot', MakeScopeValue\('\(CFixedPoint\)(\d+)'\)\)", chart)
            self.assertEqual(slots, [str(i) for i in range(len(keys))])
            for key in keys:
                self.assertIn(f"te_budget_{side}_row_{key} = {{}}", chart)
                self.assertIn(f"te_budget_{side}_{key}_cached_rank", chart)
                self.assertIn(f"te_budget_{side}_{key}_display_rank", gen.section(side))

    def test_expansion_controls_and_cached_visibility_share_the_same_state(self):
        for side in ("income", "expense"):
            chart, context = gen.chart(side), gen.section(side)
            for node, _ in gen.walk(gen.tree(side)):
                self.assertIn(f"AddScope('active_{node.key}', MakeScopeValue(TopScope.ScriptValue('te_budget_{side}_{node.key}_visible')))", context)
                if node.children:
                    state = gen.flag(side, node.key)
                    self.assertIn(f"GetVariableSystem.Toggle('{state}')", chart)
                    self.assertIn(f"AddScope('open_{node.key}', MakeScopeValue(Select_CFixedPoint(GetVariableSystem.Exists('{state}'), '(CFixedPoint)1', '(CFixedPoint)0')))", context)

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
        for branch in ("army", "navy"):
            self.assertIn(f"AddScope('{branch}_support_actual', MakeScopeValue(GetPlayer.MakeScope.ScriptValue('te_budget_{branch}_support_actual')))", gen.scope("expense"))
            self.assertTrue(f"add = scope:{branch}_support_actual" in values, f"{branch} support must use its cached sum")


if __name__ == "__main__":
    unittest.main()
