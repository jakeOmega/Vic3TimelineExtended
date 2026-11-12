"""Unit tests for pm_balance_lib — classification + index builder.

Tempfile-backed, apart from `RealPmDirectoryCoverageTests`, which reads the
mod's own `common/production_methods/`. No server. Run:
    .venv/bin/python -m unittest test_pm_balance_lib -v
"""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import annotators
import pm_balance_lib as lib
import tech_unlocks_lib
from paradox_file_parser import INJECT_DIRECTIVES, ParadoxFileParser

REPO = Path(__file__).resolve().parent


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
        self.assertEqual(lib.pm_file_names(bogus), [])

    def test_reads_a_file_no_list_names(self) -> None:
        # #1552: the map walked five named files while the directory held
        # twenty-one, so a PM in a newer file got no annotation at all.
        pm_dir = self.repo_root / "common" / "production_methods"
        _write(pm_dir / "zz_brand_new_generated_pms.txt",
               _pm("pm_new_ok", total_input=100, total_output=120, margin=20,
                   wage_be=0.05, profit=20)
               + _pm("pm_new_bare", no_cost_comments=True))
        _write(pm_dir / "extra_pms.txt", _pm("pm_old", no_cost_comments=True))
        _write(pm_dir / "notes.md", _pm("pm_not_script", no_cost_comments=True))
        self.assertEqual(lib.pm_file_names(self.repo_root),
                         ["extra_pms.txt", "zz_brand_new_generated_pms.txt"])
        result = lib.build_pm_balance_map(self.repo_root)
        self.assertEqual(sorted(result), ["pm_new_bare", "pm_new_ok", "pm_old"])
        self.assertEqual(result["pm_new_ok"]["flag"], "OK")
        self.assertEqual(result["pm_new_ok"]["file"],
                         "zz_brand_new_generated_pms.txt")
        self.assertEqual(result["pm_new_bare"]["flag"], "NO-COSTS")

    def test_replace_blocks_and_other_names_are_definitions(self) -> None:
        # extra_pms.txt redefines vanilla PMs with `REPLACE:`, names the
        # plantation methods `factory_farm_building_*`, and has ids with a
        # hyphen. pm_costs.py writes a cost block into each, and all of them
        # were skipped by a walker that only matched a bare `pm_[A-Za-z0-9_]+`.
        costs = dict(total_input=100, total_output=300, margin=200,
                     wage_be=0.05, profit=200)
        _write(self.repo_root / "common" / "production_methods" / "extra_pms.txt",
               _pm("REPLACE:pm_vanilla_one", **costs)
               + _pm("REPLACE_OR_CREATE:pm_vanilla_two", no_cost_comments=True)
               + _pm("factory_farm_building_vineyard", **costs)
               + _pm("pm_coal-fired_plant", **costs))
        result = lib.build_pm_balance_map(self.repo_root)
        self.assertEqual(sorted(result), [
            "factory_farm_building_vineyard", "pm_coal-fired_plant",
            "pm_vanilla_one", "pm_vanilla_two",
        ])
        self.assertEqual(result["pm_vanilla_one"]["flag"], "HIGH-PROFIT")
        self.assertEqual(result["pm_vanilla_two"]["flag"], "NO-COSTS")
        self.assertEqual(result["factory_farm_building_vineyard"]["flag"],
                         "HIGH-PROFIT")
        self.assertEqual(result["pm_coal-fired_plant"]["flag"], "HIGH-PROFIT")

    def test_inject_blocks_are_not_definitions(self) -> None:
        # An INJECT: patches a PM defined elsewhere. It must not give a
        # vanilla PM a row, nor replace the row of a PM the mod defines
        # (zz_ sorts after extra_pms.txt, so its block would be read last).
        pm_dir = self.repo_root / "common" / "production_methods"
        _write(pm_dir / "extra_pms.txt",
               _pm("pm_mod_defined", total_input=100, total_output=300,
                   margin=200, wage_be=0.05, profit=200))
        _write(pm_dir / "zz_generated_injects.txt",
               _pm("INJECT:pm_mod_defined", no_cost_comments=True)
               + _pm("INJECT:pm_vanilla_only", no_cost_comments=True)
               + _pm("TRY_INJECT:pm_vanilla_maybe", no_cost_comments=True)
               + _pm("pm_after_the_injects", no_cost_comments=True))
        result = lib.build_pm_balance_map(self.repo_root)
        self.assertEqual(sorted(result), ["pm_after_the_injects", "pm_mod_defined"])
        self.assertEqual(result["pm_mod_defined"]["flag"], "HIGH-PROFIT")
        self.assertEqual(result["pm_mod_defined"]["file"], "extra_pms.txt")


def _parser_defined_pms(path: Path) -> set[str]:
    """The PMs a file defines, by the mod's real parser rather than by the
    library's own line matching: every top-level key but the `INJECT:`
    family, with any `REPLACE:` directive dropped."""
    parser = ParadoxFileParser()
    parser.parse_file(str(path), apply_directives=False)
    defined = set()
    for key in parser.data:
        directive, _, name = key.rpartition(":")
        if directive not in INJECT_DIRECTIVES:
            defined.add(name)
    return defined


class RealPmDirectoryCoverageTests(unittest.TestCase):
    """The mod's own `common/production_methods/`, read offline (#1552).

    `test_annotator_endpoints.py` asserts that every PM a technology unlocks
    comes back from `?annotate=balance` with a `flag`, but it needs a live
    server and so never runs in CI. These are its offline twins: they call
    what the endpoints call.
    """

    @classmethod
    def setUpClass(cls) -> None:
        pm_dir = REPO / lib.PM_SUBDIR
        cls.defined = {path.name: _parser_defined_pms(path)
                       for path in sorted(pm_dir.glob("*.txt"))}
        cls.balance = lib.build_pm_balance_map(REPO)
        cls.unlocks = tech_unlocks_lib.build_tech_unlock_index(REPO)

    def test_every_pm_the_mod_defines_is_in_the_map(self) -> None:
        # Fails when the directory gains a file the map does not read, or a
        # file gains a definition the walker does not recognise.
        self.assertGreater(len(self.defined), 5)
        mapped: dict[str, set[str]] = {name: set() for name in self.defined}
        for pm_id, row in self.balance.items():
            mapped.setdefault(row["file"], set()).add(pm_id)
        for name, defined in self.defined.items():
            self.assertEqual(
                sorted(defined - mapped[name]), [],
                f"{name} defines PMs the balance map lacks, so "
                "`?annotate=balance` returns them with no `flag`",
            )
            self.assertEqual(
                sorted(mapped[name] - defined), [],
                f"the balance map has rows for {name} that it does not define",
            )
        self.assertEqual(sorted(set(mapped) - set(self.defined)), [])

    def _annotated_pms(self, tech_id: str) -> list[dict]:
        # What `/tech-unlocks/<tech>?annotate=balance` does: the server
        # copies the index record, then route() runs the post-processor.
        rec = copy.deepcopy(self.unlocks[tech_id])
        annotators.apply_to_response(rec, "balance", REPO)
        return rec["by_type"].get("PMs", [])

    def test_modern_tools_unlocks_all_carry_a_flag(self) -> None:
        # The two live tests that failed on main: ten of the twenty PMs
        # `modern_tools` unlocks live in mine_coproduct_generated_pms.txt.
        entries = self._annotated_pms("modern_tools")
        self.assertGreater(len(entries), 0)
        self.assertGreater(len({e["file"] for e in entries}), 1)
        for e in entries:
            self.assertIn("flag", e, e)
            self.assertIn(e["flag"], lib.FLAGS)

    def test_every_tech_unlocked_pm_the_mod_defines_carries_a_flag(self) -> None:
        # The same check for every technology, not only the one the live
        # tests happen to ask about. A PM the mod only INJECTs into is
        # vanilla's and gets no flag, like every other vanilla PM.
        defined = set().union(*self.defined.values())
        cache: dict = {}
        checked = 0
        missing = []
        for tech_id in self.unlocks:
            rec = copy.deepcopy(self.unlocks[tech_id])
            annotators.apply_to_response(rec, "balance", REPO, cache=cache)
            for e in rec["by_type"].get("PMs", []):
                if e["id"] not in defined:
                    continue
                checked += 1
                if e.get("flag") not in lib.FLAGS:
                    missing.append((tech_id, e["id"], e["file"]))
        self.assertGreater(checked, 500)
        self.assertEqual(missing, [])


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
