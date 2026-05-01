"""Unit tests for pm_balance_lib — classification + index builder.

Pure-unit, tempfile-backed. No server, no real mod data. Run:
    .venv/bin/python -m unittest test_pm_balance_lib -v
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import annotators
import pm_balance_lib as lib


# ---------------------------------------------------------------------------
# PM fixture factory
# ---------------------------------------------------------------------------

def _pm(pm_id: str, *, total_input: float | None = None,
        total_output: float | None = None,
        margin: float | None = None,
        wage_be: float | None = None,
        profit: float | None = None,
        explicit_throughput_tag: bool = False,
        modifier_block: str = "",
        no_cost_comments: bool = False) -> str:
    """Render a synthetic PM block matching the auto-generated comment shape.

    Mirrors the structure produced by `pm_costs.py`: a body containing one or
    more modifier blocks, with cost-summary comments inside the
    `building_modifiers.workforce_scaled` sub-block.
    """
    inner_lines: list[str] = []
    if explicit_throughput_tag:
        inner_lines.append("\t\t\t# AUDIT: throughput-pm")
    if not no_cost_comments:
        if total_input is not None:
            inner_lines.append(f"\t\t\t# Total input cost: {total_input}")
        if total_output is not None:
            inner_lines.append(f"\t\t\t# Total output cost: {total_output}")
        if profit is not None:
            inner_lines.append(f"\t\t\t# Profit: {profit}")
        if margin is not None:
            inner_lines.append(f"\t\t\t# Profit margin: {margin}%")
        if wage_be is not None:
            inner_lines.append(f"\t\t\t# Wage breakeven: {wage_be}")
    inner = "\n".join(inner_lines)
    extra = f"\n\t{modifier_block}" if modifier_block else ""
    return (
        f"{pm_id} = {{\n"
        f"\tbuilding_modifiers = {{\n"
        f"\t\tworkforce_scaled = {{\n"
        f"{inner}\n"
        f"\t\t}}\n"
        f"\t}}"
        f"{extra}\n"
        f"}}\n"
    )


def _write(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")


class ParseCostCommentsTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        body = _pm("pm_x", total_input=1000, total_output=1500,
                   margin=50, wage_be=0.10, profit=500)
        costs = lib.parse_cost_comments(body)
        self.assertIsNotNone(costs)
        assert costs is not None  # for type checker
        self.assertEqual(costs["total_input"], 1000)
        self.assertEqual(costs["total_output"], 1500)
        self.assertEqual(costs["profit_margin_pct"], 50)
        self.assertEqual(costs["wage_breakeven"], 0.10)
        self.assertEqual(costs["profit"], 500)
        self.assertFalse(costs["has_throughput_tag"])

    def test_returns_none_when_no_margin_line(self) -> None:
        body = _pm("pm_x", no_cost_comments=True)
        self.assertIsNone(lib.parse_cost_comments(body))

    def test_explicit_throughput_tag(self) -> None:
        body = _pm("pm_x", margin=50, explicit_throughput_tag=True)
        costs = lib.parse_cost_comments(body)
        assert costs is not None
        self.assertTrue(costs["has_throughput_tag"])


class ClassifyPmTests(unittest.TestCase):
    def test_no_costs(self) -> None:
        self.assertEqual(lib.classify_pm("", None), "NO-COSTS")

    def test_high_profit(self) -> None:
        body = _pm("pm_x", total_input=100, total_output=300, margin=200,
                   wage_be=0.05)
        costs = lib.parse_cost_comments(body)
        self.assertEqual(lib.classify_pm(body, costs), "HIGH-PROFIT")

    def test_deep_loss(self) -> None:
        # Real loss (not a throughput PM): output > 0 + negative margin.
        body = _pm("pm_x", total_input=1000, total_output=400, margin=-60,
                   wage_be=0.10)
        costs = lib.parse_cost_comments(body)
        self.assertEqual(lib.classify_pm(body, costs), "DEEP-LOSS")

    def test_high_wage(self) -> None:
        body = _pm("pm_x", total_input=100, total_output=200, margin=20,
                   wage_be=0.50)
        costs = lib.parse_cost_comments(body)
        self.assertEqual(lib.classify_pm(body, costs), "HIGH-WAGE")

    def test_low_wage(self) -> None:
        body = _pm("pm_x", total_input=100, total_output=110, margin=10,
                   wage_be=0.005)
        costs = lib.parse_cost_comments(body)
        self.assertEqual(lib.classify_pm(body, costs), "LOW-WAGE")

    def test_ok(self) -> None:
        body = _pm("pm_x", total_input=100, total_output=150, margin=50,
                   wage_be=0.15)
        costs = lib.parse_cost_comments(body)
        self.assertEqual(lib.classify_pm(body, costs), "OK")

    def test_throughput_auto(self) -> None:
        # Zero output + a country_modifiers block carrying a non-goods line.
        modifier_block = (
            "country_modifiers = { workforce_scaled = { "
            "country_weekly_innovation_add = 3 } }"
        )
        body = _pm("pm_research", total_input=1000, total_output=0,
                   margin=-100, wage_be=-2.5, modifier_block=modifier_block)
        costs = lib.parse_cost_comments(body)
        self.assertEqual(lib.classify_pm(body, costs), "THROUGHPUT")

    def test_throughput_explicit_overrides_high_wage(self) -> None:
        # PM has positive output AND high wage breakeven, but the explicit
        # author tag forces THROUGHPUT classification.
        body = _pm("pm_x", total_input=100, total_output=110, margin=10,
                   wage_be=0.50, explicit_throughput_tag=True)
        costs = lib.parse_cost_comments(body)
        self.assertEqual(lib.classify_pm(body, costs), "THROUGHPUT")

    def test_zero_output_without_modifier_block_stays_deep_loss(self) -> None:
        # Pathological: a negative-margin PM whose body has NO modifier block
        # at all (just a flat cost-comment list). is_throughput_pm finds no
        # `country_modifiers` / `building_modifiers` block to inspect, so it
        # returns False and the PM falls through to DEEP-LOSS.
        body = (
            "# Total input cost: 1000\n"
            "# Total output cost: 0\n"
            "# Profit: -1000\n"
            "# Profit margin: -100%\n"
            "# Wage breakeven: -2.5\n"
        )
        costs = lib.parse_cost_comments(body)
        self.assertEqual(lib.classify_pm(body, costs), "DEEP-LOSS")


class BuildPmBalanceMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmpdir.name)
        (self.repo_root / "common" / "production_methods").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_walks_known_files_and_classifies(self) -> None:
        modifier_block = (
            "country_modifiers = { workforce_scaled = { "
            "country_weekly_innovation_add = 3 } }"
        )
        contents = (
            _pm("pm_high", total_input=100, total_output=300, margin=200,
                wage_be=0.05, profit=200)
            + _pm("pm_through", total_input=1000, total_output=0,
                  margin=-100, wage_be=-2.5, profit=-1000,
                  modifier_block=modifier_block)
            + _pm("pm_no_costs", no_cost_comments=True)
        )
        _write(self.repo_root / "common" / "production_methods" / "extra_pms.txt",
               contents)
        result = lib.build_pm_balance_map(self.repo_root)
        self.assertEqual(result["pm_high"]["flag"], "HIGH-PROFIT")
        self.assertEqual(result["pm_high"]["margin_pct"], 200)
        self.assertEqual(result["pm_through"]["flag"], "THROUGHPUT")
        self.assertEqual(result["pm_no_costs"]["flag"], "NO-COSTS")
        self.assertIsNone(result["pm_no_costs"]["margin_pct"])
        self.assertEqual(result["pm_high"]["file"], "extra_pms.txt")

    def test_missing_repo_returns_empty(self) -> None:
        bogus = self.repo_root / "does-not-exist"
        self.assertEqual(lib.build_pm_balance_map(bogus), {})


class AnnotatorRegistrationTests(unittest.TestCase):
    def test_balance_annotator_registered_at_import(self) -> None:
        # pm_balance_lib was imported above; the registration should already
        # be present. Look it up directly.
        ann = annotators.get("balance", "PMs")
        self.assertIsNotNone(ann)
        assert ann is not None
        self.assertEqual(ann.name, "balance")
        self.assertEqual(ann.entity_type, "PMs")
        self.assertIn("flag", ann.fields)
        self.assertIn("margin_pct", ann.fields)
        self.assertIn("wage_be", ann.fields)


if __name__ == "__main__":
    unittest.main()
