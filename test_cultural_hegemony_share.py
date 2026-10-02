"""Cultural share: every other country frozen at the census, our own pull live.

Evaluates the real script values in a small offline harness (unknown syntax
fails rather than being skipped) and checks the census and the on-action that
feed them. It does not prove engine behaviour; the PR lists the in-game checks.
"""
from decimal import Decimal
from pathlib import Path
import re
import unittest

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).parent
VALUES = "common/script_values/cultural_hegemony_script_values.txt"
EFFECTS = "common/scripted_effects/cultural_hegemony_effects.txt"
ON_ACTIONS = "common/on_actions/cultural_hegemony_on_actions.txt"


def read(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")


def entries(node):
    for part in node if isinstance(node, list) else [node]:
        for key, (op, value) in part.items():
            yield key, op, value


class ShareHarness:
    """The script-value subset these values use, for one country."""

    def __init__(self, raw, globals_=None, variables=None):
        parser = ParadoxFileParser()
        tree = parser.parse_object(parser.tokenize("{" + read(VALUES) + "}"))[0]
        self.values = {key: value for key, _, value in entries(tree)}
        self.raw = Decimal(str(raw))
        self.globals = {k: Decimal(str(v)) for k, v in (globals_ or {}).items()}
        self.variables = {k: Decimal(str(v)) for k, v in (variables or {}).items()}

    def __call__(self, name):
        if name == "cultural_pull_raw":
            return self.raw
        return self.block(self.values[name])

    def operand(self, item):
        if isinstance(item, (dict, list)):
            return self.block(item)
        if item.startswith("global_var:"):
            return self.globals[item[11:]]
        if item.startswith("var:"):
            return self.variables[item[4:]]
        if re.fullmatch(r"-?[\d.]+", item):
            return Decimal(item)
        return self(item)

    def limit(self, node):
        results = []
        for key, _, item in entries(node):
            if key == "has_global_variable":
                results.append(item in self.globals)
            elif key == "has_variable":
                results.append(item in self.variables)
            else:
                raise AssertionError(f"unsupported trigger: {key}")
        return all(results)

    def block(self, node, acc=Decimal(0)):
        matched = None  # None outside an if-chain
        for key, _, item in entries(node):
            if key in ("if", "else_if", "else"):
                if key == "if":
                    matched = False
                if matched:
                    continue
                body = list(entries(item))
                if key == "else" or self.limit(next(v for k, _, v in body if k == "limit")):
                    matched = True
                    acc = self.block([{k: ("=", v)} for k, _, v in body if k != "limit"], acc)
                continue
            matched = None
            if key == "value":
                acc = self.operand(item)
            elif key == "add":
                acc += self.operand(item)
            elif key == "subtract":
                acc -= self.operand(item)
            elif key == "multiply":
                acc *= self.operand(item)
            elif key == "divide":
                acc /= self.operand(item)
            elif key == "min":
                acc = max(acc, self.operand(item))
            elif key == "max":
                acc = min(acc, self.operand(item))
            elif key == "round":
                acc = acc.quantize(Decimal(1))
            else:
                raise AssertionError(f"unsupported script-value op: {key}")
        return acc


def share(raw, globals_=None, variables=None):
    return ShareHarness(raw, globals_, variables)("cultural_pull_total")


def world(raw, globals_=None, variables=None):
    return ShareHarness(raw, globals_, variables)("ch_global_raw_display")


CENSUS = {"ch_cached_global_raw": 769, "ch_census_own_raw": 1}


class CulturalShareTests(unittest.TestCase):
    def test_before_the_first_census_there_is_no_share(self):
        self.assertEqual(share(500), 0)
        self.assertEqual(world(500), 0)

    def test_on_census_day_the_share_is_raw_over_the_census_total(self):
        self.assertAlmostEqual(share(700, CENSUS, {"ch_raw_at_census": 700}), Decimal(700) / 769 * 100)
        self.assertEqual(world(700, CENSUS, {"ch_raw_at_census": 700}), 769)

    def test_growth_after_the_census_counts_against_the_others_frozen(self):
        # The reported case: 1074.9 of a world total of 769 read as 100%.
        got = share(Decimal("1074.9"), CENSUS, {"ch_raw_at_census": 700})
        self.assertAlmostEqual(got, Decimal("1074.9") / (69 + Decimal("1074.9")) * 100)
        self.assertLess(got, 100)
        self.assertEqual(world(Decimal("1074.9"), CENSUS, {"ch_raw_at_census": 700}), 1144)

    def test_a_country_absent_from_the_census_adds_to_the_full_total(self):
        self.assertAlmostEqual(share(31, CENSUS), Decimal(31) / 800 * 100)

    def test_a_save_from_before_the_change_keeps_the_old_formula_until_its_recount(self):
        old = {"ch_cached_global_raw": 769}
        self.assertEqual(share(Decimal("1074.9"), old), 100)
        self.assertAlmostEqual(share(300, old), Decimal(300) / 769 * 100)
        self.assertEqual(world(300, old), 769)

    def test_the_denominator_never_falls_below_one(self):
        tiny = {"ch_cached_global_raw": 1, "ch_census_own_raw": 1}
        self.assertEqual(share(0, tiny, {"ch_raw_at_census": Decimal("0.5")}), 0)
        self.assertEqual(ShareHarness(0, tiny, {"ch_raw_at_census": 2})("ch_world_raw_others"), 0)

    def test_census_stores_each_countrys_pull_before_ranking_and_model_totals(self):
        effects = read(EFFECTS)
        body = effects[effects.index("ch_yearly_global_update = {"):]
        sweep = re.search(
            r"every_country = \{\s*set_variable = \{ name = ch_raw_at_census value = cultural_pull_raw \}\s*"
            r"change_global_variable = \{ name = ch_census_raw_sum add = var:ch_raw_at_census \}", body)
        self.assertIsNotNone(sweep)
        cached = body.index("set_global_variable = { name = ch_cached_global_raw value = global_var:ch_census_raw_sum }")
        marker = body.index("set_global_variable = { name = ch_census_own_raw value = yes }")
        self.assertLess(sweep.start(), cached)
        self.assertLess(cached, marker)
        self.assertLess(marker, body.index("ordered_country = {"))
        self.assertLess(marker, body.index("ch_finish_all_model_buckets = yes"))
        self.assertNotIn("global_raw_cultural_pull", read(VALUES) + effects)

    def test_a_save_without_the_marker_recounts_at_the_next_monthly_pulse(self):
        on_actions = read(ON_ACTIONS)
        monthly = on_actions[on_actions.index("ch_monthly_pulse_on_action = {"):]
        force = re.search(
            r"limit = \{\s*NOT = \{ has_global_variable = ch_census_own_raw \}\s*has_global_variable = ch_ldr_lock\s*\}"
            r"\s*remove_global_variable = ch_ldr_lock", monthly)
        self.assertIsNotNone(force)
        self.assertLess(force.start(), monthly.index("ch_yearly_global_update = yes"))


if __name__ == "__main__":
    unittest.main()
