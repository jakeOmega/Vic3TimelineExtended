#!/usr/bin/env python3
"""Summarize TE_DEMOG_CENSUS lines from an observer game's debug.log (demographics spec §11.1).

Usage: python3 scripts/analysis/demographics_observer_report.py DEBUG_LOG [MORE_LOGS ...]
           [--step 25] [--tag GBR ...] [--top N] [--json] [--closed-borders SAVE [SAVE ...]]

--closed-borders reads the migration law of each country from plain-text saves (debug mode writes
them) and prints net migration per 1,000 for Closed Borders countries against the rest. Under Closed
Borders nothing migrates across the border, so their median should be about 0: the check that the
census expects the engine's own births and deaths (phase 1's gate run).

The lines come from `event te_debug_demog.1` option b (the census log): one per country of a
million people or more at each census, every 31 December, `key=value` pairs split by `;`
(te_debug_demog_census_line in common/scripted_effects/te_debug_demog_effects.txt). People
counts are millions_thousands_units groups (demographics_harness._ungroup reads them).

Prints the world per year (people, and TFR, life expectancy and the age shares weighted by
people), each country every --step years (the first and last year logged too), and the anchors
of spec §2.2-§2.4 and the plan's owner checks beside the logged figures. The world is the sum of
the logged countries, so it leaves out countries under a million people. A line whose template
did not render (a `[` left in it) or whose number can't be read is counted as unresolved and
skipped. debug.log rolls over at 512 KB: an observer run must copy the lines out as they appear
(docs/guides/scripting_best_practices.md, "Runtime Debugging with debug_log"); pass every file.
"""

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from demographics_harness import _ungroup  # noqa: E402

PREFIX = "TE_DEMOG_CENSUS: "
FIELDS = ("tag", "year", "people", "median", "tfr", "e0", "e65", "imr", "cbr", "cdr", "mig", "young",
          "working", "old", "sex_balance", "gini", "wc", "primacy", "crisis", "devastation", "turmoil")
GROUPED = ("people", "mig")
WEIGHTED = ("tfr", "e0", "young", "old")   # world figures, weighted by people

# (where, year, field, target, lo, hi). Sources: spec §2.2 (the 1836 agrarian structure), §2.3
# (children per woman, real and sketched; world multiples), §2.4 (infant mortality, life
# expectancy at 65), and the plan's owner checks 3-4 (Britain in 1836). lo/hi only where the
# source gives a range; the others are read by eye.
ANCHORS = (
    ("world", 1836, "young", "about 35% (§2.2, 1836 agrarian)", None, None),
    ("world", 1836, "old", "5-7% (§2.2)", 0.05, 0.07),
    ("world", 1900, "x1836", "about 1.5 x 1836 (§2.3)", None, None),
    ("world", 1950, "x1900", "about 1.5 x 1900 (§2.3)", None, None),
    ("world", 2000, "x1950", "about 2.4 x 1950 (§2.3)", None, None),
    ("GBR", 1836, "tfr", "5.5-6 (owner check 3; real about 5, §2.3)", 5.5, 6.0),
    ("GBR", 1836, "e0", "about 40 (owner check 3)", None, None),
    ("GBR", 1836, "median", "about 20 (owner check 3)", None, None),
    ("GBR", 1836, "imr", "150-250 per 1,000 (§2.4, Europe 1836)", 150, 250),
    ("GBR", 1836, "gini", "about 0.5 (owner check 4)", None, None),
    ("FRA", 1836, "tfr", "about 3.8 real, 4.9 sketched (§2.3)", None, None),
    ("GBR", 1900, "tfr", "about 3.5 real, 3.9 sketched (§2.3)", None, None),
    ("GBR", 1900, "e65", "about 10 (§2.4)", None, None),
    ("GBR", 1950, "tfr", "2.5-3.5, the West before the Pill (§2.3)", 2.5, 3.5),
    ("GBR", 1950, "imr", "about 50 per 1,000 (§2.4)", None, None),
    ("GBR", 1990, "tfr", "about 1.7, the West (§2.3)", None, None),
    ("GBR", 2020, "e65", "about 20 (§2.4, today)", None, None),
    ("GBR", 2020, "imr", "under 5 per 1,000 (§2.4, today)", None, 5),
)


def _parse(text):
    fields = {}
    for part in text.split(";"):
        key, sep, value = part.strip().partition("=")
        if sep:
            fields[key.strip()] = value.strip()
    missing = [k for k in FIELDS if k not in fields]
    if missing:
        raise ValueError("lacks " + ", ".join(missing))
    out = {"tag": fields["tag"], "year": int(fields["year"])}
    if not out["tag"]:
        raise ValueError("empty tag")
    for k in FIELDS[2:]:
        out[k] = _ungroup(fields[k]) if k in GROUPED else float(fields[k])
    return out


def read_records(lines):
    """([record], [unresolved line]) from the TE_DEMOG_CENSUS lines among `lines`."""
    records, unresolved = [], []
    for line in lines:
        if PREFIX not in line:
            continue
        text = line.split(PREFIX, 1)[1].strip()
        if "[" in text or "]" in text:
            unresolved.append(f"unrendered template: {text[:200]}")
            continue
        try:
            records.append(_parse(text))
        except ValueError as e:
            unresolved.append(f"unreadable ({e}): {text[:200]}")
    return records, unresolved


def row_years(years, step):
    """The years a per-country table shows: each multiple of step, and the first and last."""
    years = sorted(set(years))
    if not years:
        return []
    return [y for y in years if y % step == 0 or y in (years[0], years[-1])]


def _world(tags):
    world = {}
    for series in tags.values():
        for year, r in series.items():
            w = world.setdefault(year, {"people": 0, "countries": 0, **{k: 0.0 for k in WEIGHTED}})
            w["people"] += r["people"]
            w["countries"] += 1
            for k in WEIGHTED:
                w[k] += r[k] * r["people"]
    for w in world.values():
        for k in WEIGHTED:
            w[k] = w[k] / w["people"] if w["people"] else 0.0
    return world


def _anchors(tags, world):
    out = []
    for where, year, field, target, lo, hi in ANCHORS:
        logged = None
        if where == "world" and field.startswith("x"):
            base = int(field[1:])
            if year in world and base in world and world[base]["people"]:
                logged = world[year]["people"] / world[base]["people"]
        elif where == "world":
            logged = world.get(year, {}).get(field)
        else:
            logged = tags.get(where, {}).get(year, {}).get(field)
        verdict = ""
        if logged is not None and (lo is not None or hi is not None):
            inside = (lo is None or logged >= lo) and (hi is None or logged <= hi)
            verdict = "in range" if inside else "outside"
        out.append({"where": where, "year": year, "field": field, "target": target, "lo": lo, "hi": hi,
                    "logged": logged, "verdict": verdict})
    return out


def summarize(records, unresolved=(), step=25):
    """The report: per-tag series {tag: {year: record}} (a later line for the same year wins),
    the world per year, the anchors and the unresolved count."""
    tags = {}
    for r in records:
        tags.setdefault(r["tag"], {})[r["year"]] = r
    world = _world(tags)
    return {
        "records": len(records), "unresolved": len(unresolved), "unresolved_lines": list(unresolved)[:20],
        "step": step, "tags": tags, "world": world, "rows": row_years(world, step),
        "anchors": _anchors(tags, world),
    }


def _fmt(x, places=2):
    return "-" if x is None else f"{x:,.{places}f}"


def _print(report, tag_filter, top):
    world, tags = report["world"], report["tags"]
    years = sorted(world)
    print(f"{report['records']} census lines; {len(tags)} countries; "
          f"years {years[0]}-{years[-1]}; unresolved {report['unresolved']} (skipped)")
    print("\nWorld (the logged countries, each a million people or more):")
    print(f"  {'year':>4}  {'people':>15}  {'TFR':>5}  {'e0':>5}  {'0-14':>5}  {'65+':>5}  countries")
    for y in report["rows"]:
        w = world[y]
        print(f"  {y:>4}  {w['people']:>15,.0f}  {w['tfr']:>5.2f}  {w['e0']:>5.1f}  {w['young']:>5.1%}  "
              f"{w['old']:>5.1%}  {w['countries']}")
    last = {t: s[max(s)]["people"] for t, s in tags.items()}
    order = sorted(tags, key=lambda t: -last[t])
    if tag_filter:
        order = [t for t in order if t in tag_filter]
    if top:
        order = order[:top]
    print(f"\nCountries every {report['step']} years (largest in their last year first):")
    print(f"  {'tag':<4} {'year':>4}  {'people':>13}  {'median':>6}  {'TFR':>5}  {'e0':>5}  {'e65':>5}  {'IMR':>6}  "
          f"{'CBR':>5}  {'CDR':>5}  {'migration':>10}  {'0-14':>5}  {'65+':>5}  {'Gini':>5}  {'WC':>5}")
    for t in order:
        for y in row_years(tags[t], report["step"]):
            r = tags[t][y]
            print(f"  {t:<4} {y:>4}  {r['people']:>13,.0f}  {r['median']:>6.1f}  {r['tfr']:>5.2f}  {r['e0']:>5.1f}  "
                  f"{r['e65']:>5.1f}  {r['imr']:>6.1f}  {r['cbr']:>5.1f}  {r['cdr']:>5.1f}  {r['mig']:>+10,.0f}  "
                  f"{r['young']:>5.1%}  {r['old']:>5.1%}  {r['gini']:>5.2f}  {r['wc']:>5.1f}")
    print("\nAnchors (spec §2.2-§2.4, the plan's owner checks):")
    for a in report["anchors"]:
        print(f"  {a['where']:<5} {a['year']}  {a['field']:<7} target {a['target']}; logged "
              f"{_fmt(a['logged'], 3)}{'  ' + a['verdict'] if a['verdict'] else ''}")
    if report["unresolved"]:
        print(f"\nUnresolved lines: {report['unresolved']} (first {len(report['unresolved_lines'])}):")
        for line in report["unresolved_lines"][:5]:
            print(f"  {line}")


CLOSED = "law_closed_borders"
MIGRATION_LAWS = (CLOSED, "law_migration_controls", "law_no_migration_controls")


def save_year(path):
    """The in-game year of a plain-text save (its meta date)."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        head = fh.read(4000)
    m = re.search(r"date=(\d+)\.", head)
    if not m:
        raise ValueError(f"{path}: no date in the first 4,000 bytes (not a plain-text save?)")
    return int(m.group(1))


def migration_laws(saves):
    """{save year: {tag: active migration law}} from plain-text saves."""
    import demographics_save_inputs as S
    out = {}
    for path in saves:
        sec = S.read_sections(str(path), ("country_manager", "laws"))
        tags = {cid: r.get("definition", "").strip('"') for cid, r in sec["country_manager"].items()}
        laws = {}
        for r in sec["laws"].values():
            if r.get("active") == "yes" and r.get("law") in MIGRATION_LAWS:
                laws[tags.get(r.get("country"), "?")] = r.get("law")
        out[save_year(path)] = laws
    return out


def closed_borders_check(records, laws_by_year, tolerance=1.0):
    """Net migration per 1,000 for countries under Closed Borders (vanilla: no migration in or out) against
    the rest, by the save nearest each census year. The census's migration is a residual: the population
    change less the births and deaths it expects the engine to produce. Under Closed Borders the true value
    is about 0 (moves between a country's own states cancel), so a median off 0 means the expected births or
    deaths are off (2026-10-09: -6 per 1,000 a year before the per-pop rates; docs/testing/demographics-growth-probe-
    results-2026-10-09.md). Returns ({(save year, group): [per 1,000]}, passed)."""
    years = sorted(laws_by_year)
    groups = {}
    for r in records:
        if not r["people"] or not years:
            continue
        near = min(years, key=lambda y: abs(y - r["year"]))
        law = laws_by_year[near].get(r["tag"])
        if law is None:
            continue
        key = (near, "closed" if law == CLOSED else "open or controlled")
        groups.setdefault(key, []).append(r["mig"] / r["people"] * 1000)
    closed = [v for (y, g), vs in groups.items() if g == "closed" for v in vs]
    passed = bool(closed) and abs(statistics.median(closed)) <= tolerance
    return groups, passed


def _print_closed(groups, passed, tolerance):
    print("\nNet migration per 1,000 a year by migration law (nearest save):")
    for (year, group) in sorted(groups):
        vs = groups[(year, group)]
        neg = sum(1 for v in vs if v < 0)
        print(f"  {year}  {group:20} n={len(vs):4d}  median {statistics.median(vs):+6.2f}  "
              f"mean {statistics.mean(vs):+6.2f}  negative {neg}/{len(vs)}")
    closed = [v for (y, g), vs in groups.items() if g == "closed" for v in vs]
    if closed:
        print(f"  Closed Borders overall: median {statistics.median(closed):+.2f} per 1,000 over {len(closed)} "
              f"country-years: {'PASS' if passed else 'FAIL'} (within +/-{tolerance:g} of 0)")
    else:
        print("  no Closed Borders country-years matched a save")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("logs", type=Path, nargs="+")
    parser.add_argument("--step", type=int, default=25, help="years between rows (default 25)")
    parser.add_argument("--tag", action="append", default=[], help="show only these countries (repeatable)")
    parser.add_argument("--top", type=int, default=0, help="show only the N largest countries")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--closed-borders", type=Path, nargs="+", metavar="SAVE",
                        help="plain-text saves: compare Closed Borders countries' migration with the rest")
    parser.add_argument("--tolerance", type=float, default=1.0,
                        help="the Closed Borders median's pass band, per 1,000 a year (default 1)")
    args = parser.parse_args(argv)
    records, unresolved = [], []
    for path in args.logs:
        with path.open(encoding="utf-8-sig", errors="replace") as lines:
            got, bad = read_records(lines)
        records += got
        unresolved += bad
    if not records:
        print("no TE_DEMOG_CENSUS lines", file=sys.stderr)
        return 1
    report = summarize(records, unresolved, args.step)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print(report, set(args.tag), args.top)
    if args.closed_borders:
        groups, passed = closed_borders_check(records, migration_laws(args.closed_borders), args.tolerance)
        _print_closed(groups, passed, args.tolerance)
    return 0


if __name__ == "__main__":
    sys.exit(main())
