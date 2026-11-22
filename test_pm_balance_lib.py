"""Unit tests for pm_balance_lib — classification + index builder.

Tempfile-backed, apart from `RealPmDirectoryCoverageTests`, which reads the
mod's own `common/production_methods/`. No server. Run:
    .venv/bin/python -m unittest test_pm_balance_lib -v
"""
from __future__ import annotations

import copy
import json
import sys
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

    def test_annotating_a_replaced_vanilla_pm_keeps_the_entry_s_own_keys(self) -> None:
        # `/tech-unlocks?source=all&annotate=balance` lists a vanilla PM the
        # mod redefines as a vanilla-source entry with vanilla's file name.
        # It gains the flag of the PM as played, and nothing else changes:
        # the map row's `file` must not overwrite the entry's.
        _write(self.repo_root / "common" / "production_methods" / "extra_pms.txt",
               _pm("REPLACE:pm_vanilla_one", total_input=100, total_output=300,
                   margin=200, wage_be=0.05, profit=200))
        self.assertEqual(
            lib.build_pm_balance_map(self.repo_root)["pm_vanilla_one"]["file"],
            "extra_pms.txt",
        )
        entry = {"type": "PMs", "id": "pm_vanilla_one",
                 "file": "01_industry.txt", "source": "vanilla"}
        annotators.apply_to_response([entry], "balance", self.repo_root)
        self.assertEqual(entry, {
            "type": "PMs", "id": "pm_vanilla_one",
            "file": "01_industry.txt", "source": "vanilla",
            "flag": "HIGH-PROFIT", "margin_pct": 200.0, "wage_be": 0.05,
        })

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

    def _vanilla_snapshot(self, *pm_ids: str) -> None:
        snapshot = self.repo_root / "vanilla_parsed"
        (snapshot / "common").mkdir(parents=True)
        _write(snapshot / "manifest.json", json.dumps({"entity_types": {
            "PMs": {"file": "common/pms.json", "entities": len(pm_ids)}}}))
        _write(snapshot / "common" / "pms.json",
               json.dumps({pm_id: ["=", {}] for pm_id in pm_ids}))

    def test_an_inject_or_create_that_creates_is_a_definition(self) -> None:
        # #1697: INJECT_OR_CREATE creates a PM nothing else defines, so its
        # block is the whole PM and needs a row. One that names a PM the mod
        # or vanilla defines is a patch, as any INJECT is: it neither gets a
        # row of its own nor replaces the defining block's row, whichever
        # file sorts first.
        self._vanilla_snapshot("pm_vanilla_one")
        pm_dir = self.repo_root / "common" / "production_methods"
        costs = dict(total_input=100, total_output=300, margin=200,
                     wage_be=0.05, profit=200)
        _write(pm_dir / "aa_injects.txt",
               _pm("INJECT_OR_CREATE:pm_created", **costs)
               + _pm("INJECT_OR_CREATE:pm_mod_defined", no_cost_comments=True)
               + _pm("INJECT_OR_CREATE:pm_vanilla_one", no_cost_comments=True))
        _write(pm_dir / "extra_pms.txt",
               _pm("pm_mod_defined", **costs)
               + _pm("INJECT_OR_CREATE:pm_created", no_cost_comments=True))
        result = lib.build_pm_balance_map(self.repo_root)
        self.assertEqual(sorted(result), ["pm_created", "pm_mod_defined"])
        self.assertEqual(result["pm_created"]["flag"], "HIGH-PROFIT")
        self.assertEqual(result["pm_created"]["file"], "aa_injects.txt")
        self.assertEqual(result["pm_mod_defined"]["file"], "extra_pms.txt")
        self.assertEqual(result["pm_mod_defined"]["flag"], "HIGH-PROFIT")
        # iter_pms, per file, still yields only the outright definitions.
        self.assertEqual([pm for pm, _ in lib.iter_pms(pm_dir / "aa_injects.txt")], [])

    def test_without_a_snapshot_an_inject_or_create_creates(self) -> None:
        _write(self.repo_root / "common" / "production_methods" / "extra_pms.txt",
               _pm("INJECT_OR_CREATE:pm_created", no_cost_comments=True))
        self.assertEqual(lib.build_pm_balance_map(self.repo_root),
                         {"pm_created": {"flag": "NO-COSTS", "file": "extra_pms.txt",
                                         "margin_pct": None, "wage_be": None,
                                         "profit": None}})


class AuditFileHeadingTests(unittest.TestCase):
    """`scripts/analysis/pm_balance_audit.py`'s line for a file with no
    margin range (#1697)."""

    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(REPO / "scripts" / "analysis"))
        import pm_balance_audit
        cls.heading = staticmethod(pm_balance_audit.file_heading)

    def test_all_throughput_is_not_no_cost_comments(self) -> None:
        rows = [{"flag": "THROUGHPUT", "margin_pct": -100.0}] * 3 + [
            {"flag": "NO-COSTS", "margin_pct": None}]
        self.assertEqual(
            self.heading("sr_colony_module_pms.txt", rows),
            "## sr_colony_module_pms.txt — 4 PMs (3 throughput, "
            "1 without cost comments; no margin range)")
        self.assertEqual(
            self.heading("x.txt", rows[:2]),
            "## x.txt — 2 PMs (2 throughput; no margin range)")

    def test_no_cost_comments_keeps_its_line(self) -> None:
        self.assertEqual(
            self.heading("x.txt", [{"flag": "NO-COSTS", "margin_pct": None}]),
            "## x.txt — 1 PMs (no cost comments)")


def _parser_defined_pms(pm_dir: Path) -> dict[str, set[str]]:
    """The PMs each file defines, by the mod's real parser rather than by
    the library's own line matching: every top-level key but the `INJECT:`
    family, with any `REPLACE:` directive dropped, and an `INJECT_OR_CREATE:`
    key, in the first file that has it, when neither another file nor
    vanilla's snapshot defines the PM."""
    defined: dict[str, set[str]] = {}
    creating: list[tuple[str, str]] = []
    for path in sorted(pm_dir.glob("*.txt")):
        parser = ParadoxFileParser()
        parser.parse_file(str(path), apply_directives=False)
        defined[path.name] = set()
        for key in parser.data:
            directive, _, name = key.rpartition(":")
            if directive not in INJECT_DIRECTIVES:
                defined[path.name].add(name)
            elif directive == "INJECT_OR_CREATE":
                creating.append((path.name, name))
    with open(REPO / "vanilla_parsed" / "common" / "pms.json", encoding="utf-8") as f:
        taken = set(json.load(f)).union(*defined.values())
    for fname, name in creating:
        if name not in taken:
            taken.add(name)
            defined[fname].add(name)
    return defined


class RealPmDirectoryCoverageTests(unittest.TestCase):
    """The mod's own `common/production_methods/`, read offline (#1552).

    `test_annotator_endpoints.py` asserts that every PM a technology unlocks
    comes back from `?annotate=balance` with a `flag`, but it needs a live
    server and so never runs in CI.

    The two tech-unlock tests here are offline twins of the `/tech-unlocks`
    one only: they build the index `tech_unlocks_lib` builds and run the
    post-processor route() runs. `/unlocked-by/<tech>` takes another path,
    `_find_unlocked_by_tech` in `mod_state_server.py`, which walks
    ModState's merged data; `test_unlocked_by_endpoint.py` calls it offline.
    `test_every_pm_the_mod_defines_is_in_the_map` covers both: whichever PM
    the mod defines, however an endpoint came to list it, has a row.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.defined = _parser_defined_pms(REPO / lib.PM_SUBDIR)
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
