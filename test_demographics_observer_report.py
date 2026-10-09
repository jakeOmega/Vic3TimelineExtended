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
            line = re.sub(r"\[[^\]]*\]", lambda m: "GBR" if "GetTagName" in m.group(0) else str(next(sample)),
                          template)
            records, unresolved = R.read_records([PREFIX + line])
            self.assertEqual(unresolved, [])
            self.assertEqual(len(records), 1)
            self.assertEqual(set(records[0]), set(R.FIELDS))
            negative = " mig=-" in template or "; mig=-" in template
            self.assertEqual(records[0]["mig"] < 0, negative)


if __name__ == "__main__":
    unittest.main()
