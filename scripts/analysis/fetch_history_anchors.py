#!/usr/bin/env python3
"""Fetch history anchors for the demographics calibration from Clio Infra.

Usage:
    fetch_history_anchors.py OUT.csv [--from DIR]

Downloads Clio Infra's country tables (life expectancy at birth, total population,
infant mortality, income inequality: the "Compact" spreadsheets) and writes one long CSV,
`measure,country,year,value`, for `demographics_harness.py history --anchors OUT.csv`.
With --from DIR it reads spreadsheets already downloaded there instead. The data stay
outside the repo (Clio Infra, https://clio-infra.eu; each dataset's page names its authors
and sources; income inequality is van Zanden et al. 2014). The spreadsheets are read with the
standard library (an .xlsx is a zip of XML), so nothing beyond Python is needed.
"""

import argparse
import csv
import re
import sys
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
                v = c.find(f"{_NS}v")
                if v is None:
                    continue
                letters = re.match(r"[A-Z]+", c.get("r")).group(0)
                col = 0
                for ch in letters:
                    col = col * 26 + ord(ch) - 64
                cells[col - 1] = shared[int(v.text)] if c.get("t") == "s" else v.text
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--from", dest="src", help="a directory holding the spreadsheets already downloaded")
    args = ap.parse_args(argv)
    out = []
    for measure, name in SOURCES.items():
        if args.src:
            path = Path(args.src) / name.replace("(", "").replace(")", "")
            if not path.exists():
                path = Path(args.src) / name
        else:
            path = Path(args.out).with_name(name.replace("(", "").replace(")", ""))
            urllib.request.urlretrieve(BASE + urllib.request.quote(name), path)
        out.extend(long_rows(measure, read_xlsx(path)))
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(("measure", "country", "year", "value"))
        w.writerows(out)
    print(f"wrote {len(out)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
