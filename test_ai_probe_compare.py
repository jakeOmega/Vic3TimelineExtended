"""scripts/analysis/ai_probe_compare.py (TEMPORARY, 2026-11-16): comparisons of AI telemetry probe runs, held on
small synthetic logs written here with keys of their own.

The logs carry only the lines the comparisons read: K and KDATE lines, keyed S lines, one positional line (so that
reading a run with another build's key shows), the X construction lines and a few events.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import ai_probe_compare as C  # noqa: E402

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
ARMED = 1836 * 12 + 1               # month 1 of the probe is February 1836, as in an unattended run from 1836


def date_of(k: int) -> tuple[int, int]:
    """The (year, month) of the probe's month k."""
    return divmod(ARMED + k - 1, 12)


def key(positional: list[str]) -> dict:
    """A key with one positional line, L1, whose fields are `positional`."""
    return {
        "version": 3,
        "lines": {"L1": positional},
        "positional_groups": ["L"],
        "country_types": ["recognized", "unrecognized", "colonial", "decentralized", "company"],
        "ranks": ["great_power", "major_power", "minor_power"],
        "law_groups": ["lawgroup_economic_system"],
        "laws": {"lawgroup_economic_system": ["law_traditionalism", "law_interventionism", "law_laissez_faire"]},
        "all_laws": ["law_traditionalism", "law_interventionism", "law_laissez_faire"],
        "strategies": {"political": ["ai_strategy_conservative_agenda", "ai_strategy_progressive_agenda"],
                       "admin": [], "diplomatic": []},
        "bank_phases": ["panic", "downturn", "stagnation", "stable", "expansion", "boom", "frenzy"],
        "data_functions": [],
    }


def write_run(folder: Path, name: str, rows: list[dict], *, positional: list[str] | None = None, version: int = 3,
              months: int | None = None, events=()) -> str:
    """A log and its key in folder; returns NAME=LOG:KEY. Each row: tag, id, k, the economic-system law (`law`),
    keyed fields, and `x` for the X construction lines."""
    positional = positional or ["lw_economic_system"]
    last = months or max(r["k"] for r in rows)
    lines = [f"TE_AIP ARM v={version}"]
    for k in range(1, last + 1):
        year, month = date_of(k)
        lines += [f"TE_AIP K {k} y={year}", f"TE_AIP KDATE {k} {MONTHS[month]} 1, {year}"]
    for r in rows:
        year, _ = date_of(r["k"])
        head = f"{r['tag']} {r['id']} {r['k']}"
        fields = {"y": year, "ai": 1, "type": 1, "gdp": 1_000_000, "pop": 1_000_000, "techs": 40, "levels": 100,
                  **{f: v for f, v in r.items() if f not in ("tag", "id", "k", "law", "x")}}
        lines.append(f"TE_AIP S A1 {head} " + " ".join(f"{f}={v}" for f, v in fields.items()))
        values = {"lw_economic_system": r.get("law", 2)}
        lines.append(f"TE_AIP S L1 {head} " + ";".join(str(values.get(f, 1)) for f in positional))
        x = {"con_used": 100.0, "con_unused": 0.0, "con_used_gov": 40.0, "con_used_priv": 60.0, "con_base": 100.0,
             "con_goods": 140_000, "con_goods_gov": 56_000, "con_goods_priv": 84_000, **r.get("x", {})}
        lines.append(f"TE_AIP X 2 {head} " + " ".join(f"{f}={x[f]}" for f in ("con_goods", "con_goods_gov",
                                                                              "con_goods_priv")))
        lines.append(f"TE_AIP X 3 {head} " + " ".join(f"{f}={x[f]}" for f in ("con_used", "con_unused", "con_used_gov",
                                                                              "con_used_priv", "con_base")))
    for event in events:
        lines.append(f"TE_AIP E {event}")
    log = folder / f"{name}.log"
    log.write_text("\n".join(f"[00:00:00][jomini_effect_impl.cpp:459]: x.txt:1: {line}" for line in lines) + "\n",
                   encoding="utf-8")
    key_path = folder / f"{name}_key.json"
    key_path.write_text(json.dumps(key(positional)), encoding="utf-8")
    return f"{name}={log}:{key_path}"


def yearly(tag, ident, first_k, years, **fields):
    """A country's reports once a year from month first_k."""
    return [{"tag": tag, "id": ident, "k": first_k + 12 * i, **fields} for i in range(years)]


class CompareTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()


class SpecTest(CompareTestCase):
    def test_a_run_is_a_name_a_log_and_its_own_key(self):
        self.assertEqual(C.parse_spec("base=/runs/a/fixture_debug.log:/keys/run1.json"),
                         ("base", "/runs/a/fixture_debug.log", "/keys/run1.json"))
        self.assertEqual(C.parse_spec("base=/runs/a/fixture_debug.log"), ("base", "/runs/a/fixture_debug.log", None))
        with self.assertRaises(Exception):
            C.parse_spec("/runs/a/fixture_debug.log")

    def test_each_run_is_read_with_its_own_key(self):
        """Two builds whose positional lines differ: each run's law reads right only with its own key."""
        a = write_run(self.folder, "a", yearly("GBR", 1, 12, 3, law=3))
        b = write_run(self.folder, "b", yearly("GBR", 1, 12, 3, law=3), positional=["lw_other", "lw_economic_system"])
        runs = C.load_runs([a, b])
        for run in runs:
            with self.subTest(run=run.name):
                self.assertEqual({C.num(r, "lw_economic_system") for r in run.ai}, {3})
        # The same log read with the other build's key misreads the positional line.
        name, log, _ = C.parse_spec(b)
        misread = C.Run(name, log, C.parse_spec(a)[2])
        self.assertNotEqual({C.num(r, "lw_economic_system") for r in misread.ai}, {3})


class OnceAYearTest(CompareTestCase):
    def test_a_country_reporting_twice_in_a_year_counts_once(self):
        """A version-2 country reporting in January and December of 1840: its GDP joins 1840's sum once."""
        rows = [{"tag": "CHI", "id": 1, "k": 48, "gdp": 5_000_000, "n_built": 4},    # January 1840
                {"tag": "CHI", "id": 1, "k": 59, "gdp": 6_000_000, "n_built": 3},    # December 1840
                {"tag": "GBR", "id": 2, "k": 50, "gdp": 4_000_000, "n_built": 1}]
        run = C.load_runs([write_run(self.folder, "a", rows, version=2, months=60)])[0]
        self.assertEqual(run.folded, 1)
        year = run.rows(1840, 1841)
        self.assertEqual(sum(C.num(r, "gdp") for r in year), 10_000_000)
        self.assertEqual(sum(C.num(r, "n_built") for r in year), 8)               # no flow lost
        yearly_rows, _ = C.series([run], names={})
        world = next(r for r in yearly_rows["rows"] if r["lens"] == "world" and r["year"] == 1840)
        self.assertEqual((world["countries"], world["gdp_m"]), (2, 10.0))


class ConstructionTest(CompareTestCase):
    def test_readings_that_are_not_the_year_are_left_out_of_the_sums(self):
        rows = [{"tag": "GBR", "id": 1, "k": 11, "x": {"con_used_priv": 1463.5, "con_goods_priv": 0}},
                {"tag": "FRA", "id": 2, "k": 11}]
        run = C.load_runs([write_run(self.folder, "a", rows, months=23)])[0]
        yearly_rows, _ = C.series([run], names={})
        world = next(r for r in yearly_rows["rows"] if r["lens"] == "world" and r["year"] == 1836)
        self.assertEqual((world["con_priv"], world["con_left_out"]), (60.0, 1))
        figure = next(f for f in C.TOP_FIGURES if f.name == "Of which private")
        self.assertEqual(figure(run.rows(1836, 1837), "top"), 60.0)


class PairedTest(CompareTestCase):
    def run_pair(self, b_fields: dict, a_fields: dict | None = None):
        """Five tags, January 1840 to January 1849, in both runs; in 1845 a tag's B row takes b_fields[tag]."""
        def rows(changes):
            out = []
            for ident, tag in enumerate(("GBR", "FRA", "RUS", "PRU", "AUS"), 1):
                for i in range(10):
                    row = {"tag": tag, "id": ident, "k": 48 + 12 * i, "gdp": 2_000_000 + ident, "bank_phase": 4,
                           "bank_crashed": 0, "n_bank_down": 0, "pool_income": 2000}
                    if i == 5:
                        row.update(changes.get(tag, {}))
                    out.append(row)
            return out
        a = write_run(self.folder, "a", rows(a_fields or {}))
        b = write_run(self.folder, "b", rows(b_fields))
        return C.paired(*C.load_runs([a, b]))

    def test_crash_law_and_gdp_apart_are_left_out(self):
        text = self.run_pair({"GBR": {"bank_crashed": 1}, "FRA": {"law": 3}, "RUS": {"gdp": 5_000_000}})
        row = next(line for line in text.splitlines() if line.startswith("| 1840s"))
        self.assertIn("| 47 of 50 | 1, 1, 1 | 5 |", row)

    def test_a_month_in_a_downturn_is_a_crash_year(self):
        text = self.run_pair({"GBR": {"n_bank_down": 2}, "FRA": {"bank_phase": 2}})
        self.assertIn("| 48 of 50 | 2, 0, 0 |", next(line for line in text.splitlines() if line.startswith("| 1840s")))
        self.assertIn("logged (version 3)", text)

    def test_without_the_cycle_a_crash_is_inferred_from_the_pool(self):
        """A version-2 log, 1850 to 1859: a pool income under 60% of the country's own median is a crash year."""
        def rows(drop):
            out = []
            for ident, tag in enumerate(("GBR", "FRA"), 1):
                for i in range(10):
                    pool = 20_000 if (drop and tag == "GBR" and i == 5) else 100_000     # 5.2 of GDP a year
                    out.append({"tag": tag, "id": ident, "k": 168 + 12 * i, "gdp": 1_000_000, "pool_income": pool})
            return out
        a = write_run(self.folder, "a", rows(False), version=2)
        b = write_run(self.folder, "b", rows(True), version=2)
        text = C.paired(*C.load_runs([a, b]))
        self.assertIn("inferred from the pool's income", text)
        self.assertIn("| 19 of 20 | 1, 0, 0 |", next(line for line in text.splitlines() if line.startswith("| 1850s")))


class CadenceTest(CompareTestCase):
    def test_the_largest_at_the_cut_are_read_from_each_countrys_last_report(self):
        """Three countries reporting in different months; with --top 1 the largest is the one whose last report
        is largest, though it did not report in the cut's own month."""
        rows = (yearly("BIG", 1, 3, 2, gdp=9_000_000, strat_political=1)
                + yearly("MID", 2, 5, 2, gdp=5_000_000, strat_political=1)
                + yearly("SML", 3, 12, 2, gdp=1_000_000, strat_political=2))
        events = ["law_start BIG 1 4 law=2", "law_end BIG 1 8 law=2", "law_start SML 3 6 law=2",
                  "law_start BIG 1 30 law=1"]
        run = write_run(self.folder, "a", rows, events=events, months=30)
        text = C.cadence(C.load_runs([run], top_n=1), until_k=24, top_n=1)
        top = text.split("## Every AI country")[0]
        self.assertIn("month 24 is January 1, 1838", text)
        self.assertIn("| all agendas | 1 / ", top)                      # BIG's one start to the cut; SML's is not
        self.assertNotIn("ai_strategy_progressive_agenda", top)
        every = text.split("## Every AI country")[1]
        self.assertIn("| ai_strategy_progressive_agenda | 1 / ", every)


class SideTest(CompareTestCase):
    def test_the_largest_lead_and_the_typical_country_comes_last(self):
        rows_a = yearly("GBR", 1, 12, 12, gdp=3_000_000) + yearly("FRA", 2, 13, 12, gdp=2_000_000)
        rows_b = yearly("GBR", 1, 12, 12, gdp=3_300_000) + yearly("FRA", 2, 13, 12, gdp=1_900_000)
        a, b = C.load_runs([write_run(self.folder, "a", rows_a), write_run(self.folder, "b", rows_b)])
        text = C.side(a, b)
        largest = text.index("## The 20 largest AI economies of each year")
        weighted = text.index("**Every AI country weighted by GDP")
        typical = text.index("# The typical country (most are small)")
        self.assertLess(largest, weighted)
        self.assertLess(weighted, typical)
        self.assertIn("| GBR | 3.0 → 3.3 (1.10) |", text)
        self.assertIn("with a_key.json", text)
        self.assertIn("with b_key.json", text)


class SeriesTest(CompareTestCase):
    def test_complete_years_and_prussia_carried_on_as_germany(self):
        rows = yearly("PRU", 1, 12, 3, gdp=2_000_000) + yearly("GER", 2, 48, 3, gdp=4_000_000)
        run = C.load_runs([write_run(self.folder, "a", rows, months=74)])[0]     # to March 1842
        self.assertEqual(run.last_complete_year(), 1841)
        yearly_rows, countries = C.series([run], names={"PRU": "Prussia", "GER": "Germany"})
        self.assertEqual(max(r["year"] for r in yearly_rows["rows"]), 1841)
        line = {r["year"]: r["country"] for r in countries["rows"] if r["tag"] == "PRU-GER"}
        self.assertEqual(line, {1837: "Prussia", 1838: "Prussia", 1839: "Prussia", 1840: "Germany",
                                1841: "Germany"})
        self.assertEqual({r["lens"] for r in yearly_rows["rows"]}, {"top20", "world"})

    def test_names_come_from_the_localization(self):
        names = C.country_names()
        if names:                                       # vanilla_parsed holds the vanilla names
            self.assertEqual(names.get("GBR"), "Great Britain")


if __name__ == "__main__":
    unittest.main()
