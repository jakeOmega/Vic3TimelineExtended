#!/usr/bin/env python3
"""Summarize TE_DEMOG_CENSUS lines from an observer game's debug.log (demographics spec §11.1).

Usage: python3 scripts/analysis/demographics_observer_report.py DEBUG_LOG [MORE_LOGS ...]
           [--step 25] [--tag GBR ...] [--top N] [--json] [--closed-borders SAVE [SAVE ...]]
           [--phase2 [--to-year 1900] [--saves SAVE [SAVE ...]] [--band 1.4 1.65]] [--work]

--phase2 checks phase 2's gate (demographics phase 2 step 4, plan Task 12): the world's multiple to
--to-year within the band, no country of 20M or more losing people ten census years running with no war
year among them by --to-year, and the share of people in states whose census term was clamped (flagged
above 1%). It exits 1 when the gate fails. From phase 2 step 4 a line's tfr, cbr and cdr are the realized
figures (the census follows the engine's events), not the model's own: the anchors' TFR bands judge what
the engine did.

The world's multiple comes from the saves when --saves names plain-text saves (#894): every pop's people
(workforce and dependents) in the earliest save given, against the save nearest 1 January after --to-year
(UNDECIDED when no save other than the first lies within a year of it). Only those two saves are read past their
header, so a run's whole save folder can be passed. Normal-speed runs only: under fast mode the census year runs
ahead of the calendar, so a save's date and the log's census year don't name the same year. Pass the run's first autosave (1 January after the first census year): the
census log's figure runs from the first census year's line to --to-year's, each taken at a country's yearly census (on a
day of its own, not 31 December), so the two cover the same years only to within that day. The log's figure is
still printed, as a second line: it sums the logged countries
of a million people or more, so land that comes under the census as it is colonized joins the total and
inflates it (normal-speed Full run to 1901, 2026-10-11: x1.92 from the log against x1.77 from the saves,
docs/testing/demographics-phase2-engine-rates-2026-10-10.md). Without --saves the gate judges the log's
figure, as before.

The band (--band LO HI, default x1.40-x1.65, WORLD_BAND) is the owner's fair comparison (#894,
2026-10-11). History's world grew about x1.4-x1.5 over 1836-1900 (Maddison), with the Taiping, Dungan and
Nian revolts, China's 1876-79 famine and India's famines in it; without those it would have grown about
x1.6-x1.65. The upper end is that no-catastrophe estimate: a run that grows faster outgrows history even
with none of its catastrophes. The lower end is history as it happened, since a game can have catastrophes
of its own. The old band, x1.3-x1.7, let a run with no catastrophes pass at x1.7.

--work (phase 2 step 2; docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §2.6) reads
the TE_DEMOG_WORKC lines the census log writes beside each TE_DEMOG_CENSUS line under this build, and checks the
observer gate's three items for countries of WORK_BIG people or more: the game's own workforce share within
WORK_FOLLOW_TOLERANCE of the ratio the census sets (the pull's lag; the saves show 0.01-0.03 in steady state), no state's set ratio past WORK_SET_BAND, and the
pension bill's share of revenue (printed by decade, the design's 15-30% band for a rich country at Standard). It
exits 1 when a state's ratio leaves the band.

--closed-borders reads the migration law of each country from plain-text saves (debug mode writes
them) and prints net migration per 1,000 for Closed Borders countries against the rest. Under Closed
Borders nothing migrates across the border, so the median of their mig_raw should be about 0: the
check that the census expects the engine's own births and deaths (phase 1's gate run). mig_raw is the
residual before each state's noise band (a residual under RESIDUAL_NOISE_SHARE of a state's people,
3 per 1,000, is set to 0 before the country sums it). The floored mig can't decide the check: its
median sits at 0 whatever the error below 3 per 1,000, and moves between a country's own states don't
cancel in it (a state's small loss is zeroed, a city's gain kept). Lines logged before mig_raw existed
leave the check undecided; the floored figures are still printed, weighted by people.

The lines come from `event te_debug_demog.1` option b (the census log): one per country of a
million people or more at each yearly census, each country on its own day, `key=value` pairs split by `;`
(te_debug_demog_census_line in common/scripted_effects/te_debug_demog_effects.txt). People
counts are millions_thousands_units groups (demographics_harness._ungroup reads them).

Lines from fast mode (te_debug_demog.1 options h-k, common/scripted_effects/te_demog_fast_effects.txt)
carry the census clock's year, which runs ahead of the calendar; their `date` (the calendar date, in
lines logged since fast mode) matches them to saves. Their `lag` counts the country's states not at the
census year: above 0, the clock's step events ran after the census.

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

import demographics_params as P  # noqa: E402
from demographics_harness import _ungroup  # noqa: E402

PREFIX = "TE_DEMOG_CENSUS: "
# phase 2 step 2's work line (te_debug_demog_work_census_line): tag and year, then numbers
WORK_PREFIX = "TE_DEMOG_WORKC: "
WORK_FIELDS = ("wf", "wf_engine", "set", "target", "set_min", "set_max", "w", "pens", "bill", "health", "pos", "age")
WORK_BIG = 20e6                      # the gate's great powers: countries of this many people or more
WORK_FOLLOW_TOLERANCE = 0.03         # the saves' steady lag of the game's figure behind its ratio: 0.01-0.03
WORK_SET_BAND = (0.1, 0.8)           # no state's ratio past 0.8 or under 0.1 (the design §2.6)
FIELDS = ("tag", "year", "people", "median", "tfr", "e0", "e65", "imr", "cbr", "cdr", "mig", "young",
          "working", "old", "sex_balance", "gini", "wc", "primacy", "crisis", "devastation", "turmoil")
# fields later lines carry: mig_raw per 1,000 people, signed; lag a count; from phase 2 step 4, the census's
# births and deaths terms in force (m_b, m_d) and the step's on-top scales (bz, dz), people-weighted over the
# country's census states, the share of its people in clamped states, and war (1 at war)
OPTIONAL = ("mig_raw", "lag", "m_b", "m_d", "bz", "dz", "clamped", "war")
TEXT_OPTIONAL = ("date",)       # the calendar date, e.g. "January 8, 2069"
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)   # the game's year has no leap day
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
    ("GBR", 1836, "gini", "about 0.55 shown (historians 0.5-0.6; wealth bands, 2026-10-10)", 0.45, 0.65),
    ("FRA", 1836, "tfr", "about 3.8 real, 4.9 sketched (§2.3)", None, None),
    ("GBR", 1900, "tfr", "about 3.5 real, 3.9 sketched (§2.3)", None, None),
    ("GBR", 1900, "e65", "about 10 (§2.4)", None, None),
    ("GBR", 1950, "tfr", "2.5-3.5, the West before the Pill (§2.3)", 2.5, 3.5),
    ("GBR", 1950, "imr", "about 50 per 1,000 (§2.4)", None, None),
    ("GBR", 1990, "tfr", "about 1.7, the West (§2.3)", None, None),
    ("GBR", 2020, "e65", "about 20 (§2.4, today)", None, None),
    ("GBR", 2020, "imr", "under 5 per 1,000 (§2.4, today)", None, 5),
)
# phase 2's gate band for the world's multiple to 1900 (module docstring; owner, #894, 2026-10-11): history
# as it happened (about x1.4-x1.5) to history without its catastrophes (about x1.6-x1.65)
WORLD_BAND = (1.4, 1.65)


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
    for k in OPTIONAL:
        if k in fields:
            out[k] = float(fields[k])
    for k in TEXT_OPTIONAL:
        if k in fields:
            out[k] = fields[k]
    return out


def phase2_check(records, to_year=1900, big=20e6, run=10, band=WORLD_BAND, saves_world=None):
    """The calibration plan's in-game gate for phase 2 (plan 2026-10-10 engine rates, Task 12):
    the world's multiple to `to_year` within `band` (lo, hi), countries of `big` people or more that lost
    people `run` census years running with no war year among them, up to `to_year`, and the share of the
    world's people in clamped states (above 1%, the clamp is holding M back: the results doc names where).

    The multiple judged is the saves' when `saves_world` is given (world_from_saves: every state's people in the
    earliest save and the one nearest 1 January after `to_year`; None for "end" leaves it undecided), and the
    census log's otherwise (the logged countries from the first census year to `to_year`). Both are returned:
    "world_multiple" is the one judged, "world_source" says which ("saves" or "log"), "log_multiple" is the log's."""
    tags = {}
    for r in records:
        tags.setdefault(r["tag"], {})[r["year"]] = r
    world = {}
    for series in tags.values():
        for y, r in series.items():
            world[y] = world.get(y, 0.0) + r["people"]
    years = sorted(world)
    first = years[0] if years else None
    log_multiple = (world[to_year] / world[first]
                    if first is not None and to_year in world and world[first] else None)
    if saves_world is not None:
        start, end = saves_world["first"], saves_world.get("end")
        multiple = end["people"] / start["people"] if end and start["people"] else None
    else:
        multiple = log_multiple
    shrinking = []
    for tag, series in sorted(tags.items()):
        ys = [y for y in sorted(series) if y <= to_year]   # fast mode logs far past the gate's window
        streak = []
        for a, b in zip(ys, ys[1:]):
            r0, r1 = series[a], series[b]
            losing = (b == a + 1 and r1["people"] < r0["people"] and r0["people"] >= big
                      and not r1.get("war", 0) and not r0.get("war", 0))
            streak = streak + [b] if losing else []
            if len(streak) == run:
                shrinking.append((tag, streak[0], streak[-1]))
    people = sum(r["people"] for r in records) or 1.0
    clamped = sum(r["people"] * r.get("clamped", 0.0) for r in records) / people
    lo, hi = band
    return {"world_multiple": multiple, "world_in_band": multiple is not None and lo <= multiple <= hi,
            "world_source": "saves" if saves_world is not None else "log", "log_multiple": log_multiple,
            "saves_world": saves_world, "band": (lo, hi), "shrinking": shrinking, "clamped_share": clamped}


def _print_phase2(check, to_year):
    m, (lo, hi) = check["world_multiple"], check["band"]
    band = f"[x{lo:.2f}-x{hi:.2f}]"
    verdict = "PASS" if check["world_in_band"] else "FAIL"
    log_m = check["log_multiple"]
    if check["world_source"] == "saves":
        sw = check["saves_world"]
        start, end = sw["first"], sw.get("end")
        if m is None:
            print(f"phase 2 gate: no save but the first within a year of {sw['target']} (the earliest is {start['date']}): "
                  "UNDECIDED")
        else:
            print(f"phase 2 gate: world x{m:.2f} from the saves, every state ({start['date']} "
                  f"{start['people'] / 1e6:,.0f}M to {end['date']} {end['people'] / 1e6:,.0f}M) {band} {verdict}")
        log = "no census in that year" if log_m is None else f"x{log_m:.2f}"
        print(f"  census log, world {to_year} / first census year: {log} (not judged: it sums the countries of a "
              "million people or more, so land colonized into the census inflates it)")
    else:
        if m is None:
            print(f"phase 2 gate: no census in {to_year} (or none at the start): UNDECIDED")
        else:
            print(f"phase 2 gate: world {to_year} / first census year x{m:.2f} from the census log {band} {verdict}")
        print("  (the log sums the countries of a million people or more, so land colonized into the census "
              "inflates it: --saves judges every state's people instead)")
    for tag, first, last in check["shrinking"]:
        print(f"  {tag} lost people every year {first}-{last} with no war year: FAIL")
    flag = "  (above 1%: the clamp is holding the census's term back)" if check["clamped_share"] > 0.01 else ""
    print(f"  people in clamped states: {check['clamped_share']:.2%}{flag}")


def calendar_year(date):
    """A logged date ("March 2, 1841") as a year with its fraction (day of the year over 365), or None."""
    m = re.fullmatch(r"(\w+) (\d+), (\d+)", date.strip())
    if not m or m.group(1) not in MONTHS:
        return None
    month = MONTHS.index(m.group(1))
    return int(m.group(3)) + (sum(MONTH_DAYS[:month]) + int(m.group(2)) - 1) / 365


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


def read_work_records(lines):
    """[record] from the TE_DEMOG_WORKC lines among `lines` (phase 2 step 2): {tag, year, date?, and WORK_FIELDS as
    floats, those a line lacks left out}; a line whose template didn't render, or without a tag or year, is skipped."""
    records = []
    for line in lines:
        if WORK_PREFIX not in line:
            continue
        text = line.split(WORK_PREFIX, 1)[1].strip()
        if "[" in text or "]" in text:
            continue
        fields = {}
        for part in text.split(";"):
            key, sep, value = part.strip().partition("=")
            if sep:
                fields[key.strip()] = value.strip()
        try:
            r = {"tag": fields["tag"], "year": int(fields["year"])}
            for k in WORK_FIELDS:
                if k in fields:
                    r[k] = float(fields[k])
        except (KeyError, ValueError):
            continue
        if "date" in fields:
            r["date"] = fields["date"]
        records.append(r)
    return records


def work_check(work, records, big=WORK_BIG, step=10):
    """The observer gate's work items (the design §2.6) over the TE_DEMOG_WORKC lines `work`, the countries judged by
    their people in the matching TE_DEMOG_CENSUS `records`: {"rows": [(tag, year, record)] for great powers every
    `step` years, "lag": [(tag, year, engine - set)] past WORK_FOLLOW_TOLERANCE where a term is in force,
    "out_of_band": [(tag, year, set_min, set_max)] past WORK_SET_BAND, "bill": (min, max) of the great powers' bill
    shares with a bill}."""
    people = {(r["tag"], r["year"]): r["people"] for r in records}
    rows, lag, out, bills = [], [], [], []
    lo, hi = WORK_SET_BAND
    for w in sorted(work, key=lambda r: (r["tag"], r["year"])):
        if people.get((w["tag"], w["year"]), 0) < big:
            continue
        if w["year"] % step == 0:
            rows.append((w["tag"], w["year"], w))
        if w.get("w", 0) and "wf_engine" in w and "set" in w and w["wf_engine"] >= 0:
            gap = w["wf_engine"] - w["set"]
            if abs(gap) > WORK_FOLLOW_TOLERANCE:
                lag.append((w["tag"], w["year"], gap))
        if "set_min" in w and "set_max" in w and (w["set_min"] < lo or w["set_max"] > hi):
            out.append((w["tag"], w["year"], w["set_min"], w["set_max"]))
        if w.get("bill", 0) > 0:
            bills.append(w["bill"])
    return {"rows": rows, "lag": lag, "out_of_band": out, "bill": (min(bills), max(bills)) if bills else None}


def _print_work(check):
    print("\nWork and retirement (TE_DEMOG_WORKC; countries of 20M people or more, every 10 years):")
    print(f"  {'tag':5s} {'year':>5s} {'wf':>6s} {'engine':>7s} {'set':>6s} {'target':>7s} {'min':>6s} {'max':>6s} "
          f"{'w':>7s} {'pens':>6s} {'bill':>6s} {'health':>7s} {'pos':>4s} {'age':>4s}")
    for tag, year, w in check["rows"]:
        print(f"  {tag:5s} {year:5d} {w.get('wf', -1):6.3f} {w.get('wf_engine', -1):7.3f} {w.get('set', -1):6.3f} "
              f"{w.get('target', -1):7.3f} {w.get('set_min', -1):6.3f} {w.get('set_max', -1):6.3f} "
              f"{w.get('w', 0):+7.3f} {w.get('pens', -1):6.3f} {w.get('bill', 0):6.1%} {w.get('health', -1):+7.3f} "
              f"{w.get('pos', 0):4.0f} {w.get('age', -1):4.0f}")
    print(f"  the game's figure more than {WORK_FOLLOW_TOLERANCE:g} from the set ratio under a term: "
          f"{len(check['lag'])} country-years" + (f" (e.g. {check['lag'][0]})" if check["lag"] else ""))
    lo, hi = WORK_SET_BAND
    print(f"  a state's set ratio outside {lo:g}-{hi:g}: {len(check['out_of_band'])} country-years"
          + (f" (e.g. {check['out_of_band'][0]})" if check["out_of_band"] else "") + ("" if not check["out_of_band"]
                                                                                   else "  FAIL"))
    b = check["bill"]
    print("  the pension bill's share of revenue: " + (f"{b[0]:.1%} to {b[1]:.1%}" if b else "no bill logged"))


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
    latest = [r for series in tags.values() for r in series.values()]
    return {
        "records": len(records), "unresolved": len(unresolved), "unresolved_lines": list(unresolved)[:20],
        "step": step, "tags": tags, "world": world, "rows": row_years(world, step),
        "anchors": _anchors(tags, world),
        # None when no line carries lag (logged before it existed); a line without it counts as none
        "lagging": ([(r["tag"], r["year"], r["lag"]) for r in latest if r.get("lag", 0) > 0]
                    if any("lag" in r for r in latest) else None),
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
    lagging = report["lagging"]
    if lagging == []:
        print("\nLag: every census found its states at its census year")
    elif lagging:
        first = ", ".join(f"{t} {y} ({lag:g})" for t, y, lag in sorted(lagging, key=lambda x: (x[1], x[0]))[:5])
        print(f"\nLag: {len(lagging)} census line{'s' if len(lagging) > 1 else ''} counted states not at its census "
              f"year (under fast mode's clock, step events that ran after the census): {first}")
    if report["unresolved"]:
        print(f"\nUnresolved lines: {report['unresolved']} (first {len(report['unresolved_lines'])}):")
        for line in report["unresolved_lines"][:5]:
            print(f"  {line}")


CLOSED = "law_closed_borders"
MIGRATION_LAWS = (CLOSED, "law_migration_controls", "law_no_migration_controls")


def save_date(path):
    """The in-game date of a plain-text save (its meta date) as (year, month, day)."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        head = fh.read(4000)
    m = re.search(r"date=(\d+)\.(\d+)\.(\d+)", head)
    if not m:
        raise ValueError(f"{path}: no date in the first 4,000 bytes (not a plain-text save?)")
    return tuple(int(g) for g in m.groups())


def save_year(path):
    """The in-game year of a plain-text save (its meta date)."""
    return save_date(path)[0]


def save_people(path):
    """Every pop's people (workforce and dependents) in a plain-text save: every state, in a census or not."""
    import demographics_save_inputs as S
    pops = S.read_sections(str(path), ("pops",))["pops"]
    return sum(S._num(r.get("workforce")) + S._num(r.get("dependents")) for r in pops.values())


def world_from_saves(saves, to_year=1900, slack=1.0):
    """The world's people for the phase 2 gate from plain-text saves (#894): the earliest save, and the save
    nearest 1 January after `to_year` (the later of two equally near), each read for every pop. Dates come from
    the headers, so only those two saves are read in full. Returns {"first": {"date", "people"}, "end": the same
    or None when no save other than the first lies within `slack` years of that date, "target": "Y.1.1"}."""
    def years(d):
        return d[0] + (d[1] - 1) / 12 + (d[2] - 1) / 365

    dated = sorted(((save_date(p), str(p)) for p in saves), key=lambda dp: years(dp[0]))
    target = to_year + 1
    first = dated[0]
    end = min(dated, key=lambda dp: (abs(years(dp[0]) - target), -years(dp[0])))
    if end is first or abs(years(end[0]) - target) > slack:
        end = None

    def entry(dp):
        return {"date": ".".join(str(x) for x in dp[0]), "people": save_people(dp[1])}

    return {"first": entry(first), "end": entry(end) if end else None, "target": f"{target}.1.1"}


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
    """Census lines for countries under Closed Borders (vanilla: no migration in or out) against the rest,
    by the save nearest each census year. The census's migration is a residual: the population change less
    the births and deaths it expects the engine to produce. Under Closed Borders the true value is about 0
    (moves between a country's own states cancel in mig_raw), so a median off 0 means the expected births
    or deaths are off (2026-10-09: -6 per 1,000 a year before the per-pop rates; docs/testing/demographics-
    growth-probe-results-2026-10-09.md). A line archived more than once counts once (the later wins, as in
    summarize). A census of seeds only (CBR and CDR 0: a game's first census) is left out, as its residual is
    0 by construction. A line with a date meets the save nearest that calendar date (under fast mode's clock its
    census year runs ahead of the calendar); one without, the save nearest its census year. Returns
    ({(save year, group): [record]}, verdict): True or False on the Closed Borders median of mig_raw, None when
    none of their lines carries it."""
    years = sorted(laws_by_year)
    latest = {(r["tag"], r["year"]): r for r in records}
    groups = {}
    for r in latest.values():
        if not r["people"] or not years or (r.get("cbr") == 0 and r.get("cdr") == 0):
            continue
        when = calendar_year(r["date"]) if "date" in r else None
        when = r["year"] if when is None else when
        near = min(years, key=lambda y: abs(y - when))
        law = laws_by_year[near].get(r["tag"])
        if law is None:
            continue
        groups.setdefault((near, "closed" if law == CLOSED else "open or controlled"), []).append(r)
    closed = [r for (y, g), rs in groups.items() if g == "closed" for r in rs]
    raw = [r["mig_raw"] for r in closed if "mig_raw" in r]
    verdict = abs(statistics.median(raw)) <= tolerance if raw else None
    return groups, verdict


def migration_stats(records):
    """Per 1,000 a year over the records: the floored migration weighted by people and its signs (+/0/-),
    and, over the lines that carry it, mig_raw's median and its mean weighted by people."""
    people = sum(r["people"] for r in records)
    raw = [r for r in records if "mig_raw" in r]
    raw_people = sum(r["people"] for r in raw)
    return {
        "n": len(records),
        "weighted": sum(r["mig"] for r in records) / people * 1000 if people else 0.0,
        "positive": sum(1 for r in records if r["mig"] > 0),
        "zero": sum(1 for r in records if r["mig"] == 0),
        "negative": sum(1 for r in records if r["mig"] < 0),
        "raw_n": len(raw),
        "raw_median": statistics.median(r["mig_raw"] for r in raw) if raw else None,
        "raw_weighted": sum(r["mig_raw"] * r["people"] for r in raw) / raw_people if raw_people else None,
    }


def _print_closed(groups, verdict, tolerance):
    band = P.RESIDUAL_NOISE_SHARE * 1000
    print("\nNet migration per 1,000 a year by migration law (nearest save). Floored: each state's residual under "
          f"{band:g} per 1,000 reads 0; raw: before that.")
    for (year, group) in sorted(groups):
        st = migration_stats(groups[(year, group)])
        raw = (f"  raw median {st['raw_median']:+6.2f} weighted {st['raw_weighted']:+6.2f}"
               if st["raw_n"] else "  raw -")
        print(f"  {year}  {group:20} n={st['n']:4d}  floored weighted {st['weighted']:+6.2f}  "
              f"+/0/- {st['positive']}/{st['zero']}/{st['negative']}{raw}")
    closed = [r for (y, g), rs in groups.items() if g == "closed" for r in rs]
    if not closed:
        print("  no Closed Borders country-years matched a save")
        return
    st = migration_stats(closed)
    if verdict is None:
        print(f"  Closed Borders overall: {st['n']} country-years, floored weighted {st['weighted']:+.2f} per 1,000. "
              f"UNDECIDED: no line carries mig_raw (logged before it existed), and the floored median sits at 0 "
              f"whatever the error below {band:g} per 1,000.")
        return
    print(f"  Closed Borders overall: median {st['raw_median']:+.2f} per 1,000 before the noise band over "
          f"{st['raw_n']} country-years (weighted {st['raw_weighted']:+.2f}): "
          f"{'PASS' if verdict else 'FAIL'} (within +/-{tolerance:g} of 0)")


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
                        help="the Closed Borders mig_raw median's pass band, per 1,000 a year (default 1)")
    parser.add_argument("--phase2", action="store_true",
                        help="phase 2's gate: the world's multiple to --to-year, 20M+ countries shrinking ten "
                             "peacetime years running, the clamped share; exit 1 when it fails")
    parser.add_argument("--to-year", type=int, default=1900, help="the gate's end year (default 1900)")
    parser.add_argument("--saves", type=Path, nargs="+", metavar="SAVE",
                        help="plain-text saves (normal-speed runs only): --phase2 judges the world's multiple from every "
                             "state's people in the earliest and the one nearest 1 January after --to-year, not the "
                             "census log's")
    parser.add_argument("--work", action="store_true",
                        help="phase 2 step 2's observer items from the TE_DEMOG_WORKC lines: the game's workforce "
                             "against the census's, every state's ratio within 0.1-0.8, the pension bill; exit 1 "
                             "when a state's ratio leaves the band")
    parser.add_argument("--band", type=float, nargs=2, metavar=("LO", "HI"), default=WORLD_BAND,
                        help="--phase2's band for the world's multiple (default %(default)s: history as it "
                             "happened to history without its catastrophes, #894)")
    args = parser.parse_args(argv)
    if args.band[0] > args.band[1]:
        parser.error("--band: LO above HI")
    if args.saves and not args.phase2:
        parser.error("--saves is read only by --phase2")
    records, unresolved, work = [], [], []
    for path in args.logs:
        with path.open(encoding="utf-8-sig", errors="replace") as lines:
            text = list(lines)
        got, bad = read_records(text)
        records += got
        unresolved += bad
        if args.work:
            work += read_work_records(text)
    if not records:
        print("no TE_DEMOG_CENSUS lines", file=sys.stderr)
        return 1
    report = summarize(records, unresolved, args.step)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print(report, set(args.tag), args.top)
    if args.closed_borders:
        groups, verdict = closed_borders_check(records, migration_laws(args.closed_borders), args.tolerance)
        _print_closed(groups, verdict, args.tolerance)
    if args.phase2:
        saves_world = world_from_saves(args.saves, args.to_year) if args.saves else None
        check = phase2_check(records, to_year=args.to_year, band=tuple(args.band), saves_world=saves_world)
        _print_phase2(check, args.to_year)
        if not check["world_in_band"] or check["shrinking"]:
            return 1
    if args.work:
        check = work_check(work, records)
        _print_work(check)
        if check["out_of_band"]:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
