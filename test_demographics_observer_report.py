"""scripts/analysis/demographics_observer_report.py: TE_DEMOG_CENSUS lines to per-tag series and world totals."""

import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_observer_report as R  # noqa: E402

CONSOLE = ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"
PREFIX = "[23:59:00][jomini_effect_impl.cpp:454]: common/scripted_effects/te_debug_demog_effects.txt:120: "


def census(tag, year, people, tfr, e0, mig="0_0_0", **extra):
    fields = {"tag": tag, "year": year, "people": people, "median": "20.10", "tfr": tfr, "e0": e0,
              "e65": "10.50", "imr": "180.00", "cbr": "38.00", "cdr": "28.00", "mig": mig, "young": "0.3500",
              "working": "0.5900", "old": "0.0600", "sex_balance": "98.00", "gini": "0.520", "wc": "50.00",
              "primacy": "0.400", "crisis": "0.000", "devastation": "0.000", "turmoil": "0.000"}
    fields.update(extra)
    return PREFIX + "TE_DEMOG_CENSUS: " + "; ".join(f"{k}={v}" for k, v in fields.items())


LINES = [
    "[23:59:00][pdx_data_localize.cpp:136]: Data error in loc string 'something else'",
    census("GBR", 1836, "25_925_658", "5.500", "40.00", mig="-0_14_715"),
    census("FRA", 1836, "33_0_50", "3.900", "38.00"),
    census("GBR", 1837, "26_100_0", "5.400", "40.50"),
    census("PRU", 1837, "14_0_0", "[THIS.Var('te_dg_tfr').GetValue|3]", "37.00"),   # a template that did not render
]


class TestRead(unittest.TestCase):
    def test_reads_the_census_lines_and_skips_an_unresolved_one(self):
        records, unresolved = R.read_records(LINES)
        self.assertEqual([(r["tag"], r["year"]) for r in records], [("GBR", 1836), ("FRA", 1836), ("GBR", 1837)])
        self.assertEqual(records[0]["people"], 25_925_658)
        self.assertEqual(records[0]["mig"], -14_715)
        self.assertEqual(records[1]["people"], 33_000_050)
        self.assertAlmostEqual(records[0]["tfr"], 5.5)
        self.assertEqual(len(unresolved), 1)
        self.assertIn("PRU", unresolved[0])

    def test_mig_raw_is_read_when_present(self):
        """Per 1,000 people and signed; lines logged before it existed have none."""
        records, unresolved = R.read_records([census("GBR", 1840, "1_0_0", "5.0", "40.0", mig_raw="-1.234"),
                                              census("FRA", 1840, "1_0_0", "5.0", "40.0")])
        self.assertEqual(unresolved, [])
        self.assertEqual(records[0]["mig_raw"], -1.234)
        self.assertNotIn("mig_raw", records[1])

    def test_lag_and_date_are_read_when_present(self):
        """lag counts the states whose census year is not the census's; date is the calendar date (under fast
        mode's clock the census year is the clock's, so saves are matched by date). Older lines have neither."""
        records, unresolved = R.read_records([census("GBR", 1900, "1_0_0", "5.0", "40.0", lag="2",
                                                     date="March 2, 1841"),
                                              census("FRA", 1840, "1_0_0", "5.0", "40.0")])
        self.assertEqual(unresolved, [])
        self.assertEqual(records[0]["lag"], 2.0)
        self.assertEqual(records[0]["date"], "March 2, 1841")
        self.assertNotIn("lag", records[1])
        self.assertNotIn("date", records[1])

    def test_the_calendar_year_of_a_logged_date(self):
        self.assertAlmostEqual(R.calendar_year("January 1, 1840"), 1840.0)
        self.assertAlmostEqual(R.calendar_year("March 2, 1841"), 1841 + (31 + 28 + 1) / 365)
        self.assertIsNone(R.calendar_year("17"))

    def test_a_line_with_a_bad_number_is_unresolved_too(self):
        records, unresolved = R.read_records([census("GBR", 1836, "25_x_658", "5.5", "40.0")])
        self.assertEqual(records, [])
        self.assertEqual(len(unresolved), 1)


class TestSummary(unittest.TestCase):
    def setUp(self):
        records, unresolved = R.read_records(LINES)
        self.report = R.summarize(records, unresolved, step=25)

    def test_per_tag_series(self):
        tags = self.report["tags"]
        self.assertEqual(sorted(tags), ["FRA", "GBR"])
        self.assertEqual(sorted(tags["GBR"]), [1836, 1837])
        self.assertEqual(tags["GBR"][1837]["people"], 26_100_000)
        self.assertAlmostEqual(tags["FRA"][1836]["tfr"], 3.9)

    def test_world_totals_per_year(self):
        world = self.report["world"]
        self.assertEqual(sorted(world), [1836, 1837])
        self.assertEqual(world[1836]["people"], 25_925_658 + 33_000_050)
        self.assertEqual(world[1836]["countries"], 2)
        want_tfr = (5.5 * 25_925_658 + 3.9 * 33_000_050) / (25_925_658 + 33_000_050)
        self.assertAlmostEqual(world[1836]["tfr"], want_tfr, places=6)
        self.assertAlmostEqual(world[1836]["e0"], (40 * 25_925_658 + 38 * 33_000_050) / (25_925_658 + 33_000_050), places=6)
        self.assertEqual(world[1837]["people"], 26_100_000)   # PRU's line was skipped
        self.assertEqual(world[1837]["countries"], 1)

    def test_unresolved_lines_are_reported(self):
        self.assertEqual(self.report["unresolved"], 1)

    def test_rows_every_step_years_plus_the_first_and_last(self):
        self.assertEqual(R.row_years([1836, 1837, 1849, 1850, 1851, 1875, 1880], 25), [1836, 1850, 1875, 1880])

    def test_a_later_line_for_the_same_year_replaces_the_earlier(self):
        records, unresolved = R.read_records([census("GBR", 1836, "1_0_0", "5.0", "40.0"),
                                              census("GBR", 1836, "2_0_0", "5.0", "40.0")])
        report = R.summarize(records, unresolved)
        self.assertEqual(report["tags"]["GBR"][1836]["people"], 2_000_000)
        self.assertEqual(report["world"][1836]["people"], 2_000_000)

    def test_anchors_carry_target_and_logged_value(self):
        gbr_tfr = [a for a in self.report["anchors"] if a["where"] == "GBR" and a["year"] == 1836 and a["field"] == "tfr"]
        self.assertEqual(len(gbr_tfr), 1)
        self.assertAlmostEqual(gbr_tfr[0]["logged"], 5.5)
        self.assertTrue(gbr_tfr[0]["target"])
        missing = [a for a in self.report["anchors"] if a["year"] == 1950]
        self.assertTrue(missing and all(a["logged"] is None for a in missing))


class TestCli(unittest.TestCase):
    def _run(self, *flags):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "debug.log"
            path.write_text("\n".join(LINES) + "\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = R.main([str(path), *flags])
        return code, out.getvalue()

    def test_text_report(self):
        code, out = self._run()
        self.assertEqual(code, 0)
        self.assertIn("GBR", out)
        self.assertIn("World", out)
        self.assertIn("Unresolved", out)

    def test_json_report(self):
        code, out = self._run("--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["world"]["1836"]["people"], 25_925_658 + 33_000_050)
        self.assertEqual(data["unresolved"], 1)

    def _run_lines(self, lines):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "debug.log"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(R.main([str(path)]), 0)
        return out.getvalue()

    def test_a_census_taken_before_its_states_stepped_is_flagged(self):
        """Under fast mode's clock every state steps a day before the countries' census: a lag above 0 means
        the step events ran late (te_demog_clock_tick's order)."""
        out = self._run_lines([census("GBR", 1900, "1_0_0", "5.0", "40.0", lag="0", date="April 2, 1840"),
                               census("FRA", 1900, "2_0_0", "5.0", "40.0", lag="3", date="April 2, 1840")])
        self.assertIn("Lag: 1 census line counted states not at its census year", out)
        self.assertIn("FRA 1900 (3)", out)
        out = self._run_lines([census("GBR", 1900, "1_0_0", "5.0", "40.0", lag="0", date="April 2, 1840")])
        self.assertIn("Lag: every census found its states at its census year", out)
        out = self._run_lines([census("GBR", 1900, "1_0_0", "5.0", "40.0")])
        self.assertNotIn("Lag:", out)
        # an archive mixing lines from before the field with later ones (a gate run's logs beside a fast run's)
        out = self._run_lines([census("GBR", 1880, "1_0_0", "5.0", "40.0"),
                               census("FRA", 1900, "2_0_0", "5.0", "40.0", lag="3", date="April 2, 1840")])
        self.assertIn("Lag: 1 census line counted states not at its census year", out)

    def test_no_census_lines_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "debug.log"
            path.write_text("nothing here\n", encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(R.main([str(path)]), 1)
            self.assertIn("no TE_DEMOG_CENSUS lines", err.getvalue())


class TestTheScriptsLine(unittest.TestCase):
    """The line te_debug_demog_census_line writes, rendered with sample numbers, reads back."""

    def test_both_variants_read(self):
        text = CONSOLE.read_text(encoding="utf-8-sig")
        templates = re.findall(r'debug_log = "(TE_DEMOG_CENSUS: [^"]*)"', text)
        self.assertEqual(len(templates), 2)
        for template in templates:
            sample = iter(range(1, 1000))
            line = re.sub(r"\[[^\]]*\]", lambda m: ("GBR" if "GetTagName" in m.group(0) else
                                                     "January 2, 1840" if "GetCurrentDate" in m.group(0) else
                                                     str(next(sample))), template)
            records, unresolved = R.read_records([PREFIX + line])
            self.assertEqual(unresolved, [])
            self.assertEqual(len(records), 1)
            self.assertEqual(set(records[0]), set(R.FIELDS) | {"mig_raw", "lag", "date"})
            self.assertEqual(records[0]["date"], "January 2, 1840")
            negative = " mig=-" in template or "; mig=-" in template
            self.assertEqual(records[0]["mig"] < 0, negative)


SAVE = """SAV0100tiny
meta_data={
\tdate=1840.1.1
\tversion="1.14.5"
}
country_manager={
\tdatabase={
1={
\tdefinition="GBR"
}
2={
\tdefinition="FRA"
}
\t}
}
laws={
\tdatabase={
0={
\tlaw=law_closed_borders
\tcountry=1
\tactive=yes
}
1={
\tlaw=law_no_migration_controls
\tcountry=2
\tactive=yes
}
2={
\tlaw=law_migration_controls
\tcountry=1
}
\t}
}
"""


class TestClosedBorders(unittest.TestCase):
    """Under Closed Borders nothing migrates across the border, so the census's migration there is the error in
    the births and deaths it expects the engine to produce (the phase 1 gate run's check)."""

    def _save(self, tmp):
        path = Path(tmp) / "autosave.v3"
        path.write_text(SAVE, encoding="utf-8")
        return path

    def test_reads_the_year_and_each_countrys_active_migration_law(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._save(tmp)
            self.assertEqual(R.save_year(path), 1840)
            self.assertEqual(R.migration_laws([path]), {1840: {"GBR": "law_closed_borders",
                                                               "FRA": "law_no_migration_controls"}})

    LAWS = {1840: {"GBR": "law_closed_borders", "SWE": "law_closed_borders", "FRA": "law_no_migration_controls"}}

    @staticmethod
    def rec(tag, year, people, mig, mig_raw=None):
        r = {"tag": tag, "year": year, "people": people, "mig": mig}
        if mig_raw is not None:
            r["mig_raw"] = mig_raw
        return r

    def test_the_gate_reads_the_closed_median_of_the_residual_before_the_band(self):
        records = [self.rec("GBR", 1839, 1_000_000, 0, mig_raw=-0.5),     # inside the band: mig floored to 0
                   self.rec("GBR", 1841, 1_000_000, 0, mig_raw=0.3),
                   self.rec("FRA", 1840, 2_000_000, -20_000, mig_raw=-10.0),   # real emigration
                   self.rec("XXX", 1840, 2_000_000, -20_000, mig_raw=-10.0)]   # no law in the save
        groups, passed = R.closed_borders_check(records, self.LAWS)
        self.assertIs(passed, True)
        self.assertEqual(sorted(r["mig_raw"] for r in groups[(1840, "closed")]), [-0.5, 0.3])
        self.assertEqual([r["tag"] for r in groups[(1840, "open or controlled")]], ["FRA"])
        bad = [self.rec("GBR", 1840, 1_000_000, -6_000, mig_raw=-6.0)]   # the pre-fix -6 per 1,000
        self.assertIs(R.closed_borders_check(bad, self.LAWS)[1], False)

    def test_without_mig_raw_the_gate_is_undecided(self):
        """The floored figure can't fail: under 3 per 1,000 every state reads 0, so the median sits at 0."""
        records = [self.rec("GBR", 1840, 1_000_000, 0), self.rec("SWE", 1840, 1_000_000, 0)]
        self.assertIsNone(R.closed_borders_check(records, self.LAWS)[1])

    def test_a_line_archived_twice_counts_once(self):
        """An observer run's archive holds the same line in several snapshots of debug.log."""
        one = self.rec("GBR", 1840, 1_000_000, 0, mig_raw=-0.5)
        groups, _ = R.closed_borders_check([one, dict(one), dict(one, mig_raw=-0.4)], self.LAWS)
        self.assertEqual([r["mig_raw"] for r in groups[(1840, "closed")]], [-0.4])   # the later line wins

    def test_a_census_of_seeds_is_left_out(self):
        """A game's first census only seeds, so its residual is 0 by construction (CBR and CDR read 0)."""
        seed = dict(self.rec("GBR", 1840, 1_000_000, 0, mig_raw=0.0), cbr=0.0, cdr=0.0)
        step = dict(self.rec("GBR", 1841, 1_000_000, 0, mig_raw=-2.0), cbr=38.0, cdr=0.0)
        groups, passed = R.closed_borders_check([seed, step], self.LAWS)
        self.assertEqual([r["year"] for r in groups[(1840, "closed")]], [1841])
        self.assertIs(passed, False)

    def test_a_dated_line_meets_the_save_nearest_its_calendar_date(self):
        """Under fast mode's clock the census year runs ahead of the calendar, so a dated line is matched by its
        date; an undated one (logged before the field) by its census year, as before."""
        laws = {1840: {"GBR": "law_closed_borders"}, 1850: {"GBR": "law_no_migration_controls"}}
        fast = dict(self.rec("GBR", 1900, 1_000_000, 0, mig_raw=-0.2), date="March 2, 1841")
        self.assertEqual(list(R.closed_borders_check([fast], laws)[0]), [(1840, "closed")])
        undated = self.rec("GBR", 1849, 1_000_000, 0, mig_raw=-0.2)
        self.assertEqual(list(R.closed_borders_check([undated], laws)[0]), [(1850, "open or controlled")])

    def test_weighted_figures(self):
        rs = [self.rec("GBR", 1840, 1_000_000, 0, mig_raw=-1.0), self.rec("SWE", 1840, 3_000_000, 6_000, mig_raw=2.0)]
        stats = R.migration_stats(rs)
        self.assertEqual(stats["n"], 2)
        self.assertAlmostEqual(stats["weighted"], 1.5)       # 6,000 over 4 million
        self.assertAlmostEqual(stats["raw_weighted"], 1.25)  # (-1 x 1 + 2 x 3) / 4
        self.assertAlmostEqual(stats["raw_median"], 0.5)
        self.assertEqual((stats["positive"], stats["zero"], stats["negative"]), (1, 1, 0))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = self._save(tmp)
            log = Path(tmp) / "debug.log"
            line = census("GBR", 1840, "1_0_0", "5.000", "40.00", mig="0_0_0", mig_raw="-0.200")
            log.write_text("\n".join([line, line, census("FRA", 1840, "2_0_0", "4.000", "40.00", mig="-0_20_0",
                                                           mig_raw="-10.000")]) + "\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(R.main([str(log), "--closed-borders", str(save)]), 0)
        self.assertIn("Closed Borders overall: median -0.20 per 1,000 before the noise band", out.getvalue())
        self.assertIn("over 1 country-years", out.getvalue())
        self.assertIn("PASS", out.getvalue())

    def test_cli_without_mig_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = self._save(tmp)
            log = Path(tmp) / "debug.log"
            log.write_text(census("GBR", 1840, "1_0_0", "5.000", "40.00") + "\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(R.main([str(log), "--closed-borders", str(save)]), 0)
        self.assertIn("UNDECIDED", out.getvalue())
        self.assertNotIn("PASS", out.getvalue())

if __name__ == "__main__":
    unittest.main()
