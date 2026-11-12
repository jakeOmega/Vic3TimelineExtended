"""The Advanced Material Fabricator's value added per employee, at base prices (#1033).

In a 2045 save the fabricator made about 90 times the average building's value added per
employee. Two things did it: the top base methods paid back their inputs 3.5 times over at
Advanced Materials' price of 4,000, and the automation and orbital methods together cut a
level's staff from 300 to 10. The good's price stays (combat units, construction methods,
space methods, companies and the AI read it); the fix raises the base methods' inputs and
trims the two staff cuts, so every combination keeps a level's staff at 100 or more and
stays within the range of its high-technology peers (Network Infrastructure's top method
is about 40 at its base staff and 133 on predictive maintenance).

Everything is read from the files: the building's method groups, each method's goods and
staff, and the goods' base prices as pm_costs.py prices them (vanilla_parsed plus the mod's
goods file). The maintenance group is left out; every peer shares it.

Run: python3 -m pytest test_advanced_material_fabricator_balance.py -q
     python3 test_advanced_material_fabricator_balance.py --table   (prints every combination)
"""
import itertools
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import pm_balance_lib  # noqa: E402

BUILDING = "building_advanced_material_fabricator"
MIN_STAFF = 100          # a level's staff, whatever the methods
MAX_VALUE_ADDED = 120.0  # per employee per level at base prices, the stacked best case
# At the base staff (no automation, no orbital), each base method in turn, in tech order.
BASE_STAFF_CEILING = 45.0


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _top_block(text, name):
    match = re.search(rf"(?m)^(?:[A-Z_]+:)?{re.escape(name)} = \{{", text)
    if match is None:
        raise AssertionError(f"no top-level {name}")
    depth = 0
    for i in range(match.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start():i + 1]
    raise AssertionError(f"unclosed {name}")


def _names(block, field):
    inner = re.search(rf"{field} = \{{([^}}]*)\}}", block)
    return inner.group(1).split() if inner else []


class _Data:
    def __init__(self):
        import pm_costs

        self.prices = pm_costs.load_goods()
        buildings = "".join(_strip(p.read_text(encoding="utf-8-sig"))
                            for p in sorted((ROOT / "common/buildings").glob("*.txt")))
        groups_text = "".join(_strip(p.read_text(encoding="utf-8-sig"))
                              for p in sorted((ROOT / "common/production_method_groups").glob("*.txt")))
        self.groups = [g for g in _names(_top_block(buildings, BUILDING), "production_method_groups")
                       if not g.startswith("pmg_maintenance")]
        self.methods = {g: _names(_top_block(groups_text, g), "production_methods") for g in self.groups}
        self.bodies = {}
        for name in pm_balance_lib.pm_file_names(ROOT):
            for pm_id, body in pm_balance_lib.iter_pms(ROOT / pm_balance_lib.PM_SUBDIR / name):
                self.bodies[pm_id.split(":")[-1]] = _strip(body)

    def figures(self, combo):
        cost = revenue = staff = 0.0
        for pm in combo:
            body = self.bodies[pm]
            for good, qty in re.findall(r"goods_input_(\w+)_add = (-?[\d.]+)", body):
                cost += float(qty) * self.prices[good]
            for good, qty in re.findall(r"goods_output_(\w+)_add = (-?[\d.]+)", body):
                revenue += float(qty) * self.prices[good]
            staff += sum(float(q) for q in re.findall(r"building_employment_\w+_add = (-?[\d.]+)", body))
        return staff, (revenue - cost) / staff if staff else float("inf")

    def combos(self):
        return list(itertools.product(*(self.methods[g] for g in self.groups)))


_DATA = None


def _data():
    global _DATA
    if _DATA is None:
        _DATA = _Data()
    return _DATA


class FabricatorBalanceTest(unittest.TestCase):
    def test_the_building_has_the_groups_this_test_reads(self):
        data = _data()
        self.assertEqual(len(data.groups), 3, data.groups)
        self.assertGreaterEqual(len(data.combos()), 24)

    def test_every_combination_keeps_a_level_staffed(self):
        data = _data()
        for combo in data.combos():
            with self.subTest(combo=combo):
                self.assertGreaterEqual(data.figures(combo)[0], MIN_STAFF)

    def test_no_combination_outearns_its_peers(self):
        data = _data()
        for combo in data.combos():
            with self.subTest(combo=combo):
                self.assertLessEqual(data.figures(combo)[1], MAX_VALUE_ADDED)

    def test_base_methods_climb_at_the_base_staff(self):
        """Each base method still earns more than the one before it, on the default methods of the other groups."""
        data = _data()
        base_group, *others = data.groups
        defaults = [data.methods[g][0] for g in others]
        previous = 0.0
        for pm in data.methods[base_group]:
            value_added = data.figures([pm, *defaults])[1]
            with self.subTest(pm=pm):
                self.assertGreater(value_added, previous)
                self.assertLessEqual(value_added, BASE_STAFF_CEILING)
            previous = value_added


if __name__ == "__main__":
    if "--table" in sys.argv:
        d = _data()
        for c in d.combos():
            s, va = d.figures(c)
            print(f"{' + '.join(c):100s} staff {s:5.0f} value added/employee {va:7.1f}")
    else:
        unittest.main()
