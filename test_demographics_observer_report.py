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

    def test_phase2_gate_exits_1_when_it_fails(self):
        """LINES hold 1836 only: no 1900 census leaves the multiple undecided, which fails the gate."""
        code, out = self._run("--phase2")
        self.assertEqual(code, 1)
        self.assertIn("phase 2 gate", out)
        self.assertIn("UNDECIDED", out)

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
            # every optional field the script writes today (phase 2 step 4 added the census's terms and war)
            self.assertEqual(set(records[0]), set(R.FIELDS) | set(R.OPTIONAL) | {"date"})
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


class TestPhase2(unittest.TestCase):
    def rec(self, tag, year, people, war=0.0, clamped=0.0):
        return {"tag": tag, "year": year, "people": people, "war": war, "clamped": clamped}

    def test_world_multiple(self):
        recs = [self.rec("AAA", 1836, 100e6), self.rec("AAA", 1900, 150e6)]
        out = R.phase2_check(recs)
        self.assertAlmostEqual(out["world_multiple"], 1.5)
        self.assertTrue(out["world_in_band"])
        self.assertEqual(out["world_source"], "log")

    def test_the_band_is_history_as_it_happened_to_history_without_its_catastrophes(self):
        """#894 (owner, 2026-10-11): about x1.4-x1.5 as it happened, about x1.6-x1.65 without the Chinese collapse
        and the Indian famines. The old band's x1.7 now fails; --band can set another."""
        self.assertEqual(R.WORLD_BAND, (1.4, 1.65))
        recs = [self.rec("AAA", 1836, 100e6), self.rec("AAA", 1900, 168e6)]
        self.assertFalse(R.phase2_check(recs)["world_in_band"])
        self.assertTrue(R.phase2_check(recs, band=(1.3, 1.7))["world_in_band"])
        recs = [self.rec("AAA", 1836, 100e6), self.rec("AAA", 1900, 135e6)]
        self.assertFalse(R.phase2_check(recs)["world_in_band"])

    SAVES = {"first": {"date": "1837.1.1", "people": 100e6}, "end": {"date": "1901.1.1", "people": 160e6},
             "target": "1901.1.1"}

    def test_the_saves_figure_is_judged_and_the_logs_kept(self):
        """The log sums the countries of 1M+, so colonized land joining the census inflates it (x1.92 against the
        saves' x1.77 in the 2026-10-11 normal-speed run): with saves the gate judges every state's people."""
        recs = [self.rec("AAA", 1836, 100e6), self.rec("AAA", 1900, 190e6)]
        out = R.phase2_check(recs, saves_world=self.SAVES)
        self.assertEqual(out["world_source"], "saves")
        self.assertAlmostEqual(out["world_multiple"], 1.6)
        self.assertTrue(out["world_in_band"])
        self.assertAlmostEqual(out["log_multiple"], 1.9)
        self.assertFalse(R.phase2_check(recs)["world_in_band"])   # the log's figure alone fails

    def test_no_save_near_the_gate_year_is_undecided(self):
        recs = [self.rec("AAA", 1836, 100e6), self.rec("AAA", 1900, 150e6)]
        out = R.phase2_check(recs, saves_world=dict(self.SAVES, end=None))
        self.assertIsNone(out["world_multiple"])
        self.assertFalse(out["world_in_band"])
        self.assertAlmostEqual(out["log_multiple"], 1.5)

    def test_ten_years_of_peacetime_loss_fails(self):
        recs = [self.rec("BIG", 1836 + i, 30e6 - i * 0.1e6) for i in range(12)]
        out = R.phase2_check(recs)
        # twelve censuses, eleven losses: the tenth loss in a row (1837-1846) is reported once
        self.assertEqual(out["shrinking"], [("BIG", 1837, 1846)])

    def test_a_run_after_the_gate_year_is_not_checked(self):
        # fast mode logs census years far past the gate's end (owner, 2026-10-11: the run check stops there too)
        recs = [self.rec("BIG", 1950 + i, 30e6 - i * 0.1e6) for i in range(12)]
        self.assertEqual(R.phase2_check(recs, to_year=1900)["shrinking"], [])

    def test_a_run_counts_only_its_losses_up_to_the_gate_year(self):
        # losses 1895-1900 (six) inside the window, the rest after it
        recs = [self.rec("BIG", 1894 + i, 30e6 - i * 0.1e6) for i in range(17)]
        self.assertEqual(R.phase2_check(recs, to_year=1900)["shrinking"], [])
        # ending in the gate year still counts
        recs = [self.rec("BIG", 1889 + i, 30e6 - i * 0.1e6) for i in range(12)]
        self.assertEqual(R.phase2_check(recs, to_year=1900)["shrinking"], [("BIG", 1890, 1899)])

    def test_a_war_year_breaks_the_run(self):
        recs = [self.rec("BIG", 1836 + i, 30e6 - i * 0.1e6, war=1.0 if i == 5 else 0.0) for i in range(12)]
        self.assertEqual(R.phase2_check(recs)["shrinking"], [])

    def test_small_countries_are_not_checked(self):
        recs = [self.rec("SML", 1836 + i, 10e6 - i * 0.1e6) for i in range(12)]
        self.assertEqual(R.phase2_check(recs)["shrinking"], [])

    def test_clamped_share_is_weighted_by_people(self):
        recs = [self.rec("AAA", 1850, 100e6, clamped=0.02), self.rec("BBB", 1850, 300e6, clamped=0.0)]
        self.assertAlmostEqual(R.phase2_check(recs)["clamped_share"], 0.005)

    def test_the_new_fields_parse_when_present(self):
        line = ("TE_DEMOG_CENSUS: tag=AAA; year=1850; people=1_0_0; median=20; tfr=5; e0=35; e65=10; imr=150; cbr=40; "
                "cdr=30; mig=0_0_0; young=0.35; working=0.6; old=0.05; sex_balance=100; gini=0.5; wc=50; primacy=0.2; "
                "crisis=0; devastation=0; turmoil=0; m_b=-0.120; m_d=-0.300; bz=0.020; dz=0.010; clamped=0; war=1")
        recs, bad = R.read_records([line])
        self.assertEqual(bad, [])
        self.assertEqual((recs[0]["m_b"], recs[0]["dz"], recs[0]["war"]), (-0.12, 0.01, 1.0))


def pops_save(date, sizes):
    """A plain-text save holding only pops, each (workforce, dependents); a nested block's fields don't count."""
    lines = ["SAV0100tiny", "meta_data={", f"\tdate={date}", "}", "pops={", "\tdatabase={"]
    for i, (workforce, dependents) in enumerate(sizes):
        lines += [f"{i}={{", f"\tworkforce={workforce}", f"\tdependents={dependents}", "\tlocation=7",
                  "\tfood_security={", "\t\tvalue=0.5", "\t\tworkforce=999", "\t}", "}"]
    lines += [f"{len(sizes)}=none", "\t}", "}", "states={", "\tdatabase={", "\t}", "}"]
    return "\n".join(lines) + "\n"


class TestPhase2Saves(unittest.TestCase):
    """--phase2 --saves: the world's multiple from every state's people in the saves (#894)."""

    def _saves(self, tmp, dated):
        paths = []
        for i, (date, sizes) in enumerate(dated):
            path = Path(tmp) / f"autosave.{i}.v3"
            path.write_text(pops_save(date, sizes), encoding="utf-8")
            paths.append(path)
        return paths

    def test_reads_the_date_and_every_pops_people(self):
        with tempfile.TemporaryDirectory() as tmp:
            [path] = self._saves(tmp, [("1837.1.1", [(100, 200), (50, 0)])])
            self.assertEqual(R.save_date(path), (1837, 1, 1))
            self.assertEqual(R.save_year(path), 1837)
            self.assertEqual(R.save_people(path), 350)

    def test_the_earliest_save_against_the_one_nearest_the_gate_years_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._saves(tmp, [("1880.1.1", [(500, 0)]), ("1901.1.1", [(700, 0)]), ("1837.1.1", [(400, 0)]),
                                      ("1902.1.1", [(900, 0)])])
            got = R.world_from_saves(paths, to_year=1900)
        self.assertEqual(got, {"first": {"date": "1837.1.1", "people": 400},
                               "end": {"date": "1901.1.1", "people": 700}, "target": "1901.1.1"})

    def test_of_two_equally_near_the_later_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._saves(tmp, [("1837.1.1", [(400, 0)]), ("1900.7.1", [(600, 0)]), ("1901.7.1", [(700, 0)])])
            self.assertEqual(R.world_from_saves(paths, to_year=1900)["end"]["date"], "1901.7.1")

    def test_no_save_within_a_year_of_the_gate_years_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._saves(tmp, [("1837.1.1", [(400, 0)]), ("1880.1.1", [(500, 0)])])
            got = R.world_from_saves(paths, to_year=1900)
            self.assertIsNone(got["end"])
            self.assertEqual(got["target"], "1901.1.1")
            # one save alone is no span, even at the gate year's end
            self.assertIsNone(R.world_from_saves(paths[:1], to_year=1836)["end"])

    def test_the_slack_is_one_year(self):
        with tempfile.TemporaryDirectory() as tmp:
            # a year and a half out is too far; exactly a year out is still near enough
            far = self._saves(tmp, [("1837.1.1", [(400, 0)]), ("1902.7.1", [(900, 0)])])
            self.assertIsNone(R.world_from_saves(far, to_year=1900)["end"])
        with tempfile.TemporaryDirectory() as tmp:
            edge = self._saves(tmp, [("1837.1.1", [(400, 0)]), ("1902.1.1", [(900, 0)])])
            self.assertEqual(R.world_from_saves(edge, to_year=1900)["end"]["date"], "1902.1.1")

    def test_month_and_day_count_in_the_nearest(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 1900.12.1 is a month short of 1901.1.1, 1901.3.1 two months past it
            paths = self._saves(tmp, [("1837.1.1", [(400, 0)]), ("1900.12.1", [(600, 0)]), ("1901.3.1", [(700, 0)])])
            self.assertEqual(R.world_from_saves(paths, to_year=1900)["end"]["date"], "1900.12.1")

    def _main(self, tmp, *flags, lines=None):
        log = Path(tmp) / "debug.log"
        lines = lines or [census("AAA", 1836, "100_0_0", "5.0", "40.0"), census("AAA", 1900, "190_0_0", "5.0", "40.0")]
        log.write_text("\n".join(lines) + "\n", encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            code = R.main([str(log), "--phase2", *flags])
        return code, out.getvalue()

    def test_cli_judges_the_saves_and_prints_the_log_beside(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._saves(tmp, [("1837.1.1", [(1_000_000, 0)]), ("1901.1.1", [(1_500_000, 0)])])
            code, out = self._main(tmp, "--saves", *map(str, paths))
            self.assertEqual(code, 0)
            self.assertIn("phase 2 gate: world x1.50 from the saves, every state (1837.1.1 1M to 1901.1.1 2M) "
                          "[x1.40-x1.65] PASS", out)
            self.assertIn("census log, world 1900 / first census year: x1.90 (not judged", out)
            code, out = self._main(tmp, "--saves", *map(str, paths), "--band", "1.0", "1.4")
            self.assertEqual(code, 1)
            self.assertIn("[x1.00-x1.40] FAIL", out)

    def test_cli_without_saves_judges_the_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = self._main(tmp)
            self.assertEqual(code, 1)
            self.assertIn("world 1900 / first census year x1.90 from the census log [x1.40-x1.65] FAIL", out)
            self.assertIn("--saves judges every state's people instead", out)
            self.assertEqual(self._main(tmp, "--band", "1.3", "2.0")[0], 0)

    def test_cli_with_no_save_near_the_end_is_undecided(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._saves(tmp, [("1837.1.1", [(1_000_000, 0)]), ("1880.1.1", [(1_200_000, 0)])])
            code, out = self._main(tmp, "--saves", *map(str, paths))
            self.assertEqual(code, 1)
            self.assertIn("no save but the first within a year of 1901.1.1 (the earliest is 1837.1.1): UNDECIDED", out)

    def test_cli_refuses_saves_without_phase2(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()):
            [path] = self._saves(tmp, [("1837.1.1", [(100, 0)])])
            log = Path(tmp) / "debug.log"
            log.write_text(census("AAA", 1836, "100_0_0", "5.0", "40.0") + "\n", encoding="utf-8")
            with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()):
                R.main([str(log), "--saves", str(path)])

    def test_cli_refuses_a_band_upside_down(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self._main(tmp, "--band", "1.7", "1.3")


class TestWork(unittest.TestCase):
    """Phase 2 step 2's work line (te_debug_demog_work_census_line) and --work's checks (the design §2.6)."""

    def _line(self, tag, year, **fields):
        base = {"wf": "0.4400", "wf_engine": "0.4300", "set": "0.4350", "target": "0.4400", "set_min": "0.3000",
                "set_max": "0.5000", "w": "0.1500", "pens": "0.1800", "bill": "0.2100", "health": "0.4000",
                "pos": "2", "age": "65"}
        base.update(fields)
        return PREFIX + f"TE_DEMOG_WORKC: tag={tag}; year={year}; " + "; ".join(f"{k}={v}" for k, v in base.items())

    def test_the_scripts_line_reads_back(self):
        text = CONSOLE.read_text(encoding="utf-8-sig")
        templates = re.findall(r'debug_log = "(TE_DEMOG_WORKC: [^"]*)"', text)
        self.assertEqual(len(templates), 1)
        sample = iter(range(1, 1000))
        line = re.sub(r"\[[^\]]*\]", lambda m: ("GBR" if "GetTagName" in m.group(0) else
                                                 "January 2, 1840" if "GetCurrentDate" in m.group(0) else
                                                 str(next(sample))), templates[0])
        (record,) = R.read_work_records([PREFIX + line])
        self.assertEqual(set(record), {"tag", "year", "date", *R.WORK_FIELDS})

    def test_the_checks(self):
        records = [R._parse(census(t, y, "30_0_0", "2.000", "70.00").split("TE_DEMOG_CENSUS: ", 1)[1])
                   for t in ("GBR", "SMA") for y in (1900, 1901)]
        records = [r for r in records if r["tag"] == "GBR"] + [dict(r, people=1e6) for r in records if r["tag"] == "SMA"]
        work = R.read_work_records([self._line("GBR", 1900), self._line("GBR", 1901, wf_engine="0.3800", set_max="0.8500"),
                                    self._line("SMA", 1900, set_min="0.0500")])
        check = R.work_check(work, records)
        self.assertEqual([(t, y) for t, y, _ in check["rows"]], [("GBR", 1900)])
        self.assertEqual([(t, y) for t, y, _ in check["lag"]], [("GBR", 1901)])
        self.assertEqual([(t, y) for t, y, *_ in check["out_of_band"]], [("GBR", 1901)], "a small country isn't judged")
        self.assertEqual(check["bill"], (0.21, 0.21))

    def test_the_cli_fails_on_a_ratio_out_of_band(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "debug.log"
            log.write_text("\n".join([census("GBR", 1900, "30_0_0", "2.000", "70.00"),
                                      self._line("GBR", 1900, set_min="0.0500")]) + "\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(R.main([str(log), "--work"]), 1)
            self.assertIn("Work and retirement", out.getvalue())


if __name__ == "__main__":
    unittest.main()
