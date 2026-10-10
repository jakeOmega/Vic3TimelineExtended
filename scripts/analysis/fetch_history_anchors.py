#!/usr/bin/env python3
"""Fetch history anchors for the demographics calibration from Clio Infra.

Usage:
    fetch_history_anchors.py OUT.csv [--from DIR | --download-dir DIR]

Downloads Clio Infra's country tables (life expectancy at birth, total population,
infant mortality, income inequality: the "Compact" spreadsheets) and Gapminder's children per
woman (GAPMINDER_FILES, the `tfr` measure), and writes one long CSV,
`measure,country,year,value`, for `demographics_harness.py history --anchors OUT.csv`.
Downloads go to --download-dir (a temporary directory by default, so nothing lands in the
repo); with --from DIR it reads spreadsheets already downloaded there instead. The data stay
outside the repo (Clio Infra, https://clio-infra.eu; each dataset's page names its authors
and sources; income inequality is van Zanden et al. 2014). The spreadsheets are read with the
standard library (an .xlsx is a zip of XML), so nothing beyond Python is needed.
"""

import argparse
import csv
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

BASE = "https://clio-infra.eu/data/"
SOURCES = {
    "e0": "LifeExpectancyatBirth(Total)_Compact.xlsx",
    "population": "TotalPopulation_Compact.xlsx",
    "imr": "InfantMortality_Compact.xlsx",
    "gini": "IncomeInequality_Compact.xlsx",
}
# Children per woman from Gapminder (open-numbers/ddf--gapminder--fertility_rate on GitHub), by country code,
# with the codes' names; written as the `tfr` measure under the country's name.
GAPMINDER_BASE = "https://raw.githubusercontent.com/open-numbers/ddf--gapminder--fertility_rate/master/"
GAPMINDER_TFR = "gapminder-children_per_woman.csv"
GAPMINDER_GEO = "gapminder-geo-country.csv"
GAPMINDER_FILES = {GAPMINDER_TFR: "ddf--datapoints--children_per_woman_total_fertility--by--country--year.csv",
                   GAPMINDER_GEO: "ddf--entities--geo--country.csv"}
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def read_xlsx(path):
    """The first sheet's rows as lists of strings (None for an empty cell)."""
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{_NS}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))
        sheet = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
        rows = []
        for row in ET.fromstring(z.read(sheet)).iter(f"{_NS}row"):
            cells = {}
            for c in row.iter(f"{_NS}c"):
                ref = c.get("r")
                if ref is None:
                    continue
                if c.get("t") == "inlineStr":
                    text = "".join(t.text or "" for t in c.iter(f"{_NS}t"))
                else:
                    v = c.find(f"{_NS}v")
                    if v is None:
                        continue
                    text = shared[int(v.text)] if c.get("t") == "s" else v.text
                col = 0
                for ch in re.match(r"[A-Z]+", ref).group(0):
                    col = col * 26 + ord(ch) - 64
                cells[col - 1] = text
            if cells:
                rows.append([cells.get(i) for i in range(max(cells) + 1)])
        return rows


def long_rows(measure, rows):
    """(measure, country, year, value) from a Compact table: ccode, country name, then one column a year."""
    header = rows[0]
    years = {i: int(h) for i, h in enumerate(header) if h and str(h).isdigit()}
    for r in rows[1:]:
        if len(r) < 2 or not r[1]:
            continue
        for i, v in enumerate(r):
            if i in years and v not in (None, ""):
                yield measure, r[1], years[i], float(v)


def gapminder_rows(tfr_path, geo_path):
    """("tfr", country name, year, children per woman) from Gapminder's country-year file and its names."""
    with open(geo_path, newline="", encoding="utf-8") as fh:
        names = {r["country"]: r["name"] for r in csv.DictReader(fh)}
    with open(tfr_path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            yield "tfr", names.get(r["country"], r["country"]), int(r["year"]), float(r["children_per_woman_total_fertility"])


def _download(url, path):
    with urllib.request.urlopen(url, timeout=60) as resp, open(path, "wb") as fh:
        shutil.copyfileobj(resp, fh)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--from", dest="src", help="a directory holding the spreadsheets already downloaded")
    ap.add_argument("--download-dir", help="where downloads go (default: a temporary directory)")
    args = ap.parse_args(argv)
    out = []
    downloads = None if args.src else Path(args.download_dir or tempfile.mkdtemp(prefix="history-anchors-"))
    for measure, name in SOURCES.items():
        if args.src:
            path = Path(args.src) / name.replace("(", "").replace(")", "")
            if not path.exists():
                path = Path(args.src) / name
        else:
            path = downloads / name.replace("(", "").replace(")", "")
            try:
                _download(BASE + urllib.parse.quote(name), path)
            except (urllib.error.URLError, OSError) as e:
                print(f"cannot download {BASE + name}: {e}", file=sys.stderr)
                return 1
        out.extend(long_rows(measure, read_xlsx(path)))
    folder = Path(args.src) if args.src else downloads
    if not args.src:
        for local, remote in GAPMINDER_FILES.items():
            try:
                _download(GAPMINDER_BASE + remote, folder / local)
            except (urllib.error.URLError, OSError) as e:
                print(f"cannot download {GAPMINDER_BASE + remote}: {e}", file=sys.stderr)
                return 1
    if (folder / GAPMINDER_TFR).exists() and (folder / GAPMINDER_GEO).exists():
        out.extend(gapminder_rows(folder / GAPMINDER_TFR, folder / GAPMINDER_GEO))
    elif args.src:
        print(f"no {GAPMINDER_TFR} and {GAPMINDER_GEO} in {args.src}: no children-per-woman anchors", file=sys.stderr)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(("measure", "country", "year", "value"))
        w.writerows(out)
    print(f"wrote {len(out)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
