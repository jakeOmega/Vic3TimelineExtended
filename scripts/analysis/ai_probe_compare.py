"""Compare AI telemetry probe runs: two side by side, the fairest paired reading, the law cadence of several runs cut
at one month, and yearly series as JSON.

TEMPORARY (2026-11-16), with scripts/analysis/ai_probe_report.py, whose parser and rules it uses, and
scripts/generators/gen_ai_probe.py, which writes the probe.

    ai_probe_compare.py side    A=LOG[:KEY] B=LOG[:KEY] [--years 10] [--until YEAR] [--top 20] [--md FILE]
    ai_probe_compare.py paired  A=LOG[:KEY] B=LOG[:KEY] [--until YEAR] [--top 20] [--md FILE]
    ai_probe_compare.py cadence --until-k K NAME=LOG[:KEY] [NAME=LOG[:KEY] ...] [--top 20]
    ai_probe_compare.py series  --out DIR NAME=LOG[:KEY] [NAME=LOG[:KEY] ...] [--top 20]

A run is NAME=LOG:KEY: LOG is the run's log (the QA harness's fixture_debug.log, or a folder `ai_probe_report.py
parse` wrote) and KEY the ai_probe_key.json of the build that ran it (without `:KEY`, the key beside the report).
**Each run is read with its own key**: two builds whose laws, technologies or building groups differ index their
positional lines differently, and one key read over both misreads one of them.

side      the two runs period by period, every cell A -> B: the largest economies first (the 20 with the highest
          GDP in each year of each run, a set that moves), then the same tags one by one, the rest, single-year
          world totals, each section through the three lenses (the 20 largest, every AI country weighted by GDP,
          the typical country), and the typical country's own tables last.
paired    the fairest reading of two single runs (the 2026-11-16 private-construction analysis, its
          a6_crash_residual.py): the same tag, among the 20 largest of either run in the decade, only in the years
          both runs have it under the same economic-system law, with no banking crash in either, and with GDP within
          1.5 times; B over A of the sums, by decade. A crash year is read from the probe where it logged the cycle
          (version 3: a crash in the 365 days before the snapshot, a month in a panic or downturn since the last, or
          a panic or downturn at it) and inferred where it did not (pool income under 60% of the country's own
          median under that law, for a country whose median is 5% of GDP or more).
cadence   law starts per idle month by political agenda (ai_probe_report.law_cadence) for several runs cut at one
          month count, for every AI country and for the 20 largest at the cut (by each country's last report).
series    yearly.json (a row for each run, lens and year: the 20 largest of that year, and the world) and
          countries.json (each economy that was ever among the 20 largest, Prussia's line carried on as Germany's)
          for charts; a year is kept once every run has reached its end.

Every subcommand counts what the report counts: AI countries that are not decentralized nations, each once a
calendar year (ai_probe_report.once_a_year: a version-1 or -2 report that drifted into a year the country had
already reported in is folded into its later one), and the construction figures without the X readings that are
not the year (ai_probe_report.x_construction). Unused construction points are `con_unused`, never `wasted`
(has_wasted_construction holds for most countries whatever they used). One run of each build is one sample of a
game whose AI is not deterministic: read a difference only where it is large, holds in every period, or survives
`paired`.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import ai_probe_report as P  # noqa: E402

num = P.num
TOP_N = P.TOP_N
SMALL = 1_000_000                    # GDP at a country's first report, below which it is a small economy
GDP_APART = 1.5                      # paired: tag-years whose GDP differ by more than this are not compared
CRASH_SHARE = 0.6                    # paired, inferred crash: pool income under this share of the country's median
CRASH_POOL_FLOOR = 0.05              # ... for a country whose median pool income is at least this share of GDP
CRASH_MEDIAN_FROM = 1850             # ... the median over its reports from this year


# --- runs ------------------------------------------------------------------------------------------------------------

def parse_spec(text: str) -> tuple[str, str, str | None]:
    """NAME=LOG[:KEY] as (name, log, key or None). The key is the part after the last colon when it names a .json."""
    name, sep, rest = text.partition("=")
    if not sep or not name or not rest:
        raise argparse.ArgumentTypeError(f"a run is NAME=LOG[:KEY], not {text!r}")
    head, colon, tail = rest.rpartition(":")
    if colon and head and tail.endswith(".json"):
        return name, head, tail
    return name, rest, None


class Run:
    """One run's AI countries, one row a country a calendar year."""

    def __init__(self, name: str, log: str, key_path: str | None = None, until: int | None = None,
                 top_n: int = TOP_N):
        self.name, self.log = name, log
        self.key_path = Path(key_path) if key_path else P.KEY_PATH
        self.key = P.load_key(self.key_path)
        self.parsed = P.gather([log], self.key)
        records = [r for r in self.parsed.records() if "y" in r and (until is None or r["y"] <= until)]
        records, self.folded = P.once_a_year(records)
        decentralized = self.key["country_types"].index("decentralized") + 1
        self.ai = [r for r in records if num(r, "type") != decentralized and num(r, "ai") == 1]
        self.years = sorted({r["y"] for r in self.ai})
        self.top = P.largest_by_year(self.ai, top_n)
        self.by_id = P.series(self.ai)
        self.first_gdp = {ident: num(rows[0], "gdp") for ident, rows in self.by_id.items()}
        self.events = self.parsed.events
        self.year_of = P.k_to_year(self.parsed.ticks)
        self.banked = any("bank_phase" in r for r in self.ai)

    def rows(self, start: int, end: int, part: str | None = None) -> list[dict]:
        """Rows of the years [start, end): all, the year's largest (`top`), the others (`rest`), or `small`."""
        rows = [r for r in self.ai if start <= r["y"] < end]
        if part == "top":
            return [r for r in rows if r["id"] in self.top.get(r["y"], ())]
        if part == "rest":
            return [r for r in rows if r["id"] not in self.top.get(r["y"], ())]
        if part == "small":
            return [r for r in rows if self.first_gdp.get(r["id"], 0) < SMALL]
        return rows

    def by_tag(self, year: int) -> dict[str, dict]:
        """The year's rows by tag; where two country objects share a tag (a civil war), the larger economy."""
        out: dict[str, dict] = {}
        for r in self.rows(year, year + 1):
            if r["tag"] not in out or num(r, "gdp") > num(out[r["tag"]], "gdp"):
                out[r["tag"]] = r
        return out

    def last_complete_year(self) -> int | None:
        """The last year whose every month the run reached: the year of its last month, if that was December."""
        if not self.parsed.ticks:
            return self.years[-1] if self.years else None
        last = self.parsed.ticks[max(self.parsed.ticks)]
        year = last.get("y")
        if not isinstance(year, int):
            return self.years[-1] if self.years else None
        return year if P.month_of(last.get("date")) == 11 else year - 1

    def describe(self) -> str:
        span = f"{self.years[0]} to {self.years[-1]}" if self.years else "no years"
        folded = f", {self.folded} doubled reports folded" if self.folded else ""
        return (f"{self.name}: {self.log} with {self.key_path.name}; probe version {self.parsed.version()}; "
                f"{len(self.ai)} rows of {len(self.by_id)} AI countries, {span}{folded}")


def load_runs(specs: list[str], until: int | None = None, top_n: int = TOP_N) -> list[Run]:
    return [Run(*parse_spec(spec), until=until, top_n=top_n) for spec in specs]


# --- figures -----------------------------------------------------------------------------------------------------------

def gdp(r: dict) -> float:
    return max(num(r, "gdp"), 0)


def xval(r: dict, name: str):
    value = (r.get("x") or {}).get(name)
    return value if isinstance(value, (int, float)) else None


def in_crisis(r: dict) -> bool:
    """A panic or downturn at the snapshot, a crash in the year before it, or a month of either since the last."""
    return num(r, "bank_phase") in (1, 2) or num(r, "bank_crashed") == 1 or num(r, "n_bank_down") > 0


class Fig:
    """A figure over rows, read through a lens: 'top' and 'all' take medians (or means, `mean=True`) of a value,
    shares of rows for a test, the median of a per-row ratio, the median of per-country growth; 'world' takes the
    GDP-weighted mean (or the yearly total, `total=True`), the share of GDP, the ratio of the totals, and growth
    weighted by GDP. `among` keeps only the rows it accepts; `custom(rows, lens)` replaces all of these."""

    def __init__(self, name, value=None, *, test=None, ratio=None, growth=None, custom=None, digits=1, scale=1.0,
                 mean=False, total=False, among=None):
        self.name, self.value, self.test, self.ratio, self.growth = name, value, test, ratio, growth
        self.custom, self.digits, self.scale, self.mean, self.total, self.among = (custom, digits, scale, mean,
                                                                                    total, among)

    def __call__(self, rows: list[dict], lens: str):
        if self.among:
            rows = [r for r in rows if self.among(r)]
        if self.custom:
            return self.custom(rows, lens)
        if self.test:
            if lens == "world":
                whole = sum(gdp(r) for r in rows)
                return 100 * sum(gdp(r) for r in rows if self.test(r)) / whole if whole else None
            return 100 * sum(1 for r in rows if self.test(r)) / len(rows) if rows else None
        if self.ratio:
            top, bottom = self.ratio
            pairs = [(top(r), bottom(r)) for r in rows]
            pairs = [(a, b) for a, b in pairs if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b > 0]
            if lens == "world":
                below = sum(b for _, b in pairs)
                return sum(a for a, _ in pairs) / below * self.scale if below else None
            return statistics.median(a / b for a, b in pairs) * self.scale if pairs else None
        if self.growth:
            rates = growth_rates(rows, self.growth)
            if lens == "world":
                weight = sum(gdp(first) for _, first in rates)
                return sum(rate * gdp(first) for rate, first in rates) / weight * 100 if weight else None
            return statistics.median(rate for rate, _ in rates) * 100 if rates else None
        values = [(self.value(r), r) for r in rows]
        values = [(v, r) for v, r in values if isinstance(v, (int, float))]
        if not values:
            return None
        if lens == "world":
            if self.total:
                years = len({r["y"] for _, r in values})
                return sum(v for v, _ in values) / years * self.scale
            weight = sum(gdp(r) for _, r in values)
            return sum(v * gdp(r) for v, r in values) / weight * self.scale if weight else None
        if self.mean:
            return statistics.fmean(v for v, _ in values) * self.scale
        return statistics.median(v for v, _ in values) * self.scale


def growth_rates(rows: list[dict], fn) -> list[tuple[float, dict]]:
    """(yearly growth of fn, the first row) for each country with two rows a month count apart among the rows."""
    mine: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        mine[r["id"]].append(r)
    out = []
    for series in mine.values():
        series.sort(key=lambda r: r["k"])
        first, last = series[0], series[-1]
        a, b, months = fn(first), fn(last), last["k"] - first["k"]
        if months > 0 and isinstance(a, (int, float)) and isinstance(b, (int, float)) and a > 0 and b > 0:
            out.append(((b / a) ** (12 / months) - 1, first))
    return out


def field(name: str):
    return lambda r: num(r, name)


def logged(name: str, fn=None):
    """fn(r) (the field itself by default) where the row's probe version logged the field, else None."""
    fn = fn or field(name)
    return lambda r: fn(r) if name in r else None


def x_field(name: str):
    return lambda r: xval(r, name)


def per_head(r):
    return num(r, "gdp") / num(r, "pop") if num(r, "pop") > 0 else None


def yearly_sum(fn, scale=1.0):
    """The rows' sum in each year, averaged over the years (a custom figure: the same through every lens)."""
    def run(rows, lens):
        by_year: dict[int, float] = defaultdict(float)
        seen = False
        for r in rows:
            value = fn(r)
            if isinstance(value, (int, float)):
                by_year[r["y"]] += value * scale
                seen = True
        return statistics.fmean(by_year.values()) if seen else None
    return run


def sum_growth(fn):
    """Growth of the rows' yearly sum from their first year to their last, % a year."""
    def run(rows, lens):
        by_year: dict[int, float] = defaultdict(float)
        for r in rows:
            value = fn(r)
            if isinstance(value, (int, float)):
                by_year[r["y"]] += value
        years = sorted(by_year)
        if len(years) < 2 or by_year[years[0]] <= 0 or by_year[years[-1]] <= 0:
            return None
        return ((by_year[years[-1]] / by_year[years[0]]) ** (1 / (years[-1] - years[0])) - 1) * 100
    return run


def gdp_share_in(test):
    return lambda rows, lens: (100 * sum(gdp(r) for r in rows if test(r)) / sum(gdp(r) for r in rows)
                               if sum(gdp(r) for r in rows) > 0 else None)


def built(r):
    return num(r, "n_built") + num(r, "n_expanded")


def banked(r):
    return "bank_phase" in r


# The largest economies of each year: what a player competes with (owner, 2026-11-16).
TOP_FIGURES = [
    Fig("GDP, sum (millions)", custom=yearly_sum(field("gdp"), 1e-6), digits=0),
    Fig("Growth of that sum, % a year", custom=sum_growth(field("gdp")), digits=2),
    Fig("GDP growth, median member, % a year", growth=field("gdp"), digits=2),
    Fig("GDP per head growth, median member", growth=per_head, digits=2),
    Fig("Building levels, sum", custom=yearly_sum(field("levels")), digits=0),
    Fig("Built + expanded a year (mean)", built, mean=True, digits=1),
    Fig("Construction points used a week, sum", custom=yearly_sum(x_field("con_used")), among=P.valid_x, digits=0),
    Fig("Of which private", custom=yearly_sum(x_field("con_used_priv")), among=P.valid_x, digits=0),
    Fig("Construction points unused a week, sum", custom=yearly_sum(x_field("con_unused")), among=P.valid_x,
        digits=0),
    Fig("Government points bought a week (median)", field("cm_public"), digits=1),
    Fig("Construction paused, %", test=lambda r: num(r, "paused") == 1, digits=0),
    Fig("In a banking crisis in the year, % of GDP", custom=gdp_share_in(in_crisis), among=banked, digits=0),
    Fig("Tax, % of GDP (median)", ratio=(field("tax_income"), field("gdp")), scale=5200, digits=1),
    Fig("Technologies (median)", field("techs"), digits=0),
    Fig("Laws passed a year (mean)", field("n_law_pass"), mean=True, digits=2),
    Fig("Army (median)", field("army"), digits=0),
]

REST_FIGURES = [
    Fig("GDP, sum (millions)", custom=yearly_sum(field("gdp"), 1e-6), digits=0),
    Fig("Growth of that sum, % a year", custom=sum_growth(field("gdp")), digits=2),
    Fig("GDP growth, median member, % a year", growth=field("gdp"), digits=2),
    Fig("Building levels, sum", custom=yearly_sum(field("levels")), digits=0),
    Fig("Built + expanded a year (mean)", built, mean=True, digits=1),
    Fig("Construction paused, %", test=lambda r: num(r, "paused") == 1, digits=0),
    Fig("Technologies (median)", field("techs"), digits=0),
]

SMALL_FIGURES = [
    Fig("Countries", custom=lambda rows, lens: len({r["id"] for r in rows}), digits=0),
    Fig("GDP growth, % a year", growth=field("gdp"), digits=2),
    Fig("Building levels", field("levels"), digits=0),
    Fig("Built + expanded a year (mean)", built, mean=True, digits=1),
    Fig("Government levels built a year (mean)", field("n_built_gov"), mean=True, digits=2),
    Fig("Points a week, where buying", field("cm_public"), among=lambda r: num(r, "cm_public") > 0, digits=2),
    Fig("Debt at 40% of limit or more, %", test=lambda r: num(r, "debt_scaled") >= 0.4, digits=0),
    Fig("In default, %", test=lambda r: num(r, "default") == 1, digits=0),
    Fig("Technologies", field("techs"), digits=0),
]

SECTIONS: list[tuple[str, list[Fig]]] = [
    ("1. Economic growth", [
        Fig("GDP growth, % a year", growth=field("gdp"), digits=2),
        Fig("GDP per head growth, % a year", growth=per_head, digits=2),
        Fig("GDP per head", ratio=(field("gdp"), field("pop")), digits=2),
        Fig("Standard of living", field("sol"), digits=1),
        Fig("Peasants, % of pops", field("peasants"), scale=100, digits=0),
        Fig("Building levels (world: total)", field("levels"), total=True, digits=0),
    ]),
    ("1a. Construction", [
        Fig("Construction sector levels", field("bt_construction_sector"), digits=0),
        Fig("No construction sector, %", test=lambda r: num(r, "bt_construction_sector") == 0, digits=0),
        Fig("Built + expanded a year (mean; world: total)", built, mean=True, total=True, digits=1),
        Fig("Government levels built a year", field("n_built_gov"), mean=True, total=True, digits=2),
        Fig("Queued levels", field("queue_levels"), digits=0),
        Fig("Points used a week (world: total)", x_field("con_used"), total=True, among=P.valid_x, digits=0),
        Fig("Private, % of points used", ratio=(x_field("con_used_priv"), x_field("con_used")), scale=100,
            among=P.valid_x, digits=0),
        Fig("Unused, % of the base", ratio=(x_field("con_unused"), x_field("con_base")), scale=100, among=P.valid_x,
            digits=0),
        Fig("Readings left out (unpaid or idle), %", test=lambda r: P.x_construction(r) in ("unpaid", "idle"),
            among=lambda r: P.x_construction(r) != "none", digits=0),
    ]),
    ("1d. The government's construction purchase", [
        Fig("Buying any, %", test=lambda r: num(r, "cm_public") > 0, digits=0),
        Fig("Points a week, where buying", field("cm_public"), among=lambda r: num(r, "cm_public") > 0, digits=2),
        Fig("Bill over weekly income, where buying", ratio=(lambda r: num(r, "cm_public") * num(r, "cm_price"),
                                                            field("income")),
            among=lambda r: num(r, "cm_public") > 0, digits=2),
        Fig("Government level queued but buying none, %",
            test=lambda r: num(r, "queue_gov") > 0 and num(r, "cm_public") == 0 and num(r, "paused") == 0, digits=0),
        Fig("Construction paused, %", test=lambda r: num(r, "paused") == 1, digits=0),
        Fig("No government level queued, %", test=lambda r: num(r, "queue_gov") == 0, digits=0),
    ]),
    ("1b. Solvency", [
        Fig("In default, %", test=lambda r: num(r, "default") == 1, digits=0),
        Fig("Declared bankrupt, %", test=lambda r: num(r, "bankrupt") == 1, digits=0),
        Fig("Debt at 40% of limit or more, %", test=lambda r: num(r, "debt_scaled") >= 0.4, digits=0),
        Fig("Debt, share of limit", field("debt_scaled"), digits=2),
        Fig("Reserves, share of limit", field("gold_scaled"), digits=2),
        Fig("Income / expenses", ratio=(field("income"), field("expenses")), digits=2),
        Fig("Bureaucracy below 0, %", test=lambda r: num(r, "bur") < 0, digits=0),
    ]),
    ("1e. The budget (share of GDP, %)", [
        Fig("Tax", ratio=(field("tax_income"), field("gdp")), scale=5200, digits=1),
        Fig("All income", ratio=(field("income"), field("gdp")), scale=5200, digits=1),
        Fig("All expenses", ratio=(field("expenses"), field("gdp")), scale=5200, digits=1),
        Fig("Government wages", ratio=(x_field("gov_wages"), field("gdp")), scale=5200, digits=1),
        Fig("Government goods", ratio=(x_field("gov_goods"), field("gdp")), scale=5200, digits=1),
        Fig("Construction goods, government", ratio=(x_field("con_goods_gov"), field("gdp")), scale=5200,
            among=P.valid_x, digits=1),
        Fig("Investment pool income", ratio=(field("pool_income"), field("gdp")), scale=5200, digits=1),
        Fig("Investment pool, weeks of income", ratio=(field("pool"), field("income")), digits=1),
    ]),
    ("1h. The banking cycle (version 3)", [
        Fig("In a panic or downturn at the snapshot, %", test=lambda r: num(r, "bank_phase") in (1, 2),
            among=banked, digits=0),
        Fig("A crash in the year before, %", test=lambda r: num(r, "bank_crashed") == 1, among=banked, digits=0),
        Fig("A crisis in the year at all, %", test=in_crisis, among=banked, digits=0),
        Fig("Months in a panic or downturn a year", field("n_bank_down"), mean=True, among=banked, digits=2),
        Fig("Cycle running, %", test=lambda r: num(r, "bank_phase") > 0, among=banked, digits=0),
        Fig("Cycle value, where running", field("bank_cycle"), among=lambda r: num(r, "bank_phase") > 0, digits=0),
    ]),
    ("2. Technology", [
        Fig("Technologies", field("techs"), digits=0),
        Fig("Leader", custom=lambda rows, lens: max((num(r, "techs") for r in rows), default=None), digits=0),
        Fig("Acquired a year", field("n_tech"), mean=True, digits=2),
        Fig("Innovation", field("innovation"), digits=0),
        Fig("University levels (world: total)", field("bt_university"), total=True, digits=1),
        Fig("No university, %", test=lambda r: num(r, "bt_university") == 0, digits=0),
        Fig("Literacy, %", field("lit"), scale=100, digits=0),
    ]),
    ("3. Laws", [
        Fig("Enacting a law, %", test=lambda r: num(r, "enacting") == 1, digits=0),
        Fig("Enactments started a year", field("n_law_start"), mean=True, total=True, digits=2),
        Fig("Passed a year", field("n_law_pass"), mean=True, total=True, digits=2),
        Fig("Failed a year", field("n_law_fail"), mean=True, total=True, digits=2),
        Fig("Institution levels, all", lambda r: sum(num(r, f) for f in r if f.startswith("in_")), digits=0),
    ]),
    ("4. Military", [
        Fig("Army (battalions; world: total)", field("army"), total=True, digits=0),
        Fig("Navy (world: total)", field("navy"), total=True, digits=0),
        Fig("Army units, mean era", field("army_tier"), among=lambda r: num(r, "army") > 0, digits=2),
        Fig("Military technologies", lambda r: sum(num(r, f) for f in r if f.startswith("tc_military_")), digits=0),
        Fig("Barracks levels", field("bt_barrack"), digits=0),
    ]),
    ("5. Expansion", [
        Fig("States (world: total)", field("states"), total=True, digits=0),
        Fig("Colonies under way, %", test=lambda r: num(r, "colonies") > 0, digits=0),
        Fig("Plays started a year", field("n_play"), mean=True, total=True, digits=3),
        Fig("Wars started a year", field("n_war"), mean=True, total=True, digits=3),
        Fig("At war, %", test=lambda r: num(r, "war") == 1, digits=0),
        Fig("Infamy", field("infamy"), digits=0),
    ]),
]

LENSES = [
    ("top", "The {n} largest AI economies of each year (by that year's GDP): medians"),
    ("world", "Every AI country weighted by GDP: means weighted by GDP, shares of GDP, ratios of the totals, "
              "totals a year"),
    ("all", "The typical country: medians over every AI country (most are small)"),
]


# --- side ------------------------------------------------------------------------------------------------------------

def fmt(value, digits: int) -> str:
    return "-" if value is None else f"{value:,.{digits}f}"


def arrow(a, b, digits: int) -> str:
    return f"{fmt(a, digits)} → {fmt(b, digits)}"


def periods(a: Run, b: Run, step: int):
    years = sorted(set(a.years) & set(b.years))
    if not years:
        return
    start = years[0] - years[0] % step
    while start <= years[-1]:
        yield (f"{start}s" if step == 10 else f"{start}-{start + step - 1}"), start, start + step
        start += step


def figure_table(out: list[str], a: Run, b: Run, step: int, title: str, figures: list[Fig], part=None,
                 lens: str = "top", note: str = ""):
    out += ["", f"## {title}", ""]
    if note:
        out += [note, ""]
    out.append("| Years | " + " | ".join(f.name for f in figures) + " |")
    out.append("|---|" + "---|" * len(figures))
    for label, start, end in periods(a, b, step):
        ra, rb = a.rows(start, end, part), b.rows(start, end, part)
        if ra or rb:
            out.append(f"| {label} | " + " | ".join(arrow(f(ra, lens), f(rb, lens), f.digits) for f in figures) + " |")


def lens_tables(out: list[str], a: Run, b: Run, step: int, title: str, figures: list[Fig], top_n: int):
    out += ["", f"## {title}"]
    for lens, heading in LENSES:
        out += ["", f"**{heading.format(n=top_n)}**", ""]
        out.append("| Years | " + " | ".join(f.name for f in figures) + " |")
        out.append("|---|" + "---|" * len(figures))
        for label, start, end in periods(a, b, step):
            part = "top" if lens == "top" else None
            ra, rb = a.rows(start, end, part), b.rows(start, end, part)
            if ra or rb:
                out.append(f"| {label} | " + " | ".join(arrow(f(ra, lens), f(rb, lens), f.digits) for f in figures)
                           + " |")


def common_years(a: Run, b: Run) -> list[int]:
    return sorted(set(a.years) & set(b.years))


def top_by_tag(out: list[str], a: Run, b: Run, step: int, top_n: int):
    """The largest economies one by one: the same tag in both runs, in a few years both reached."""
    years = common_years(a, b)
    if not years:
        return
    picks = [y for y in years if y % (2 * step) == 0 or y == years[-1]][-3:]
    out += ["", "## The largest economies one by one: the same tag in both runs", "",
            f"The {top_n} largest of either run in each year shown. GDP in millions; B over A in brackets. A tag "
            "missing from a run that year (annexed, or not yet formed) shows a dash."]
    for year in picks:
        ta, tb = a.by_tag(year), b.by_tag(year)
        tags = ({r["tag"] for r in a.rows(year, year + 1, "top")} | {r["tag"] for r in b.rows(year, year + 1, "top")})
        order = sorted(tags, key=lambda t: -max(num(ta.get(t, {}), "gdp"), num(tb.get(t, {}), "gdp")))
        out += ["", f"**{year}**", "",
                "| Tag | GDP | Building levels | Technologies | Construction sector levels | Laws passed to that year |",
                "|---|---|---|---|---|---|"]
        ratios = []
        for tag in order:
            ra, rb = ta.get(tag), tb.get(tag)

            def pair(name, scale=1.0, digits=0, ra=ra, rb=rb):
                va = num(ra, name) * scale if ra else None
                vb = num(rb, name) * scale if rb else None
                return arrow(va, vb, digits) + (f" ({vb / va:.2f})" if va and vb else "")
            if ra and rb and num(ra, "gdp") > 0:
                ratios.append(num(rb, "gdp") / num(ra, "gdp"))
            laws = [sum(1 for e in run.events if e["event"] == "law_pass" and e.get("tag") == tag
                        and (run.year_of(e["k"]) or 9999) <= year) for run in (a, b)]
            out.append(f"| {tag} | {pair('gdp', 1e-6, 1)} | {pair('levels')} | {pair('techs')} | "
                       f"{pair('bt_construction_sector')} | {laws[0]} → {laws[1]} |")
        if ratios:
            out += ["", f"GDP, B over A, across the {len(ratios)} tags in both runs: median "
                        f"{statistics.median(ratios):.2f}; B higher in {sum(1 for v in ratios if v > 1)} of {len(ratios)}."]


def world_totals(out: list[str], a: Run, b: Run, step: int):
    out += ["", "## World totals over AI countries, in single years", "",
            "| Year | Countries | GDP, sum (millions) | Building levels, sum | Technologies, sum | In default | "
            "Declared bankrupt | Debt at 40% or more | In a banking crisis in the year |",
            "|---|---|---|---|---|---|---|---|---|"]
    years = common_years(a, b)
    for year in [y for y in years if y % step == 0 or y == years[-1] or y == years[0] + 1]:
        ra, rb = a.rows(year, year + 1), b.rows(year, year + 1)

        def total(rows, name, scale=1.0):
            return sum(num(r, name) for r in rows) * scale

        def count(rows, test):
            return sum(1 for r in rows if test(r))

        def crises(run, rows):
            return str(count(rows, in_crisis)) if run.banked else "-"
        out.append(f"| {year} | {len(ra)} → {len(rb)} | {arrow(total(ra, 'gdp', 1e-6), total(rb, 'gdp', 1e-6), 0)} | "
                   f"{arrow(total(ra, 'levels'), total(rb, 'levels'), 0)} | "
                   f"{arrow(total(ra, 'techs'), total(rb, 'techs'), 0)} | "
                   f"{count(ra, lambda r: num(r, 'default') == 1)} → {count(rb, lambda r: num(r, 'default') == 1)} | "
                   f"{count(ra, lambda r: num(r, 'bankrupt') == 1)} → {count(rb, lambda r: num(r, 'bankrupt') == 1)} | "
                   f"{count(ra, lambda r: num(r, 'debt_scaled') >= 0.4)} → "
                   f"{count(rb, lambda r: num(r, 'debt_scaled') >= 0.4)} | {crises(a, ra)} → {crises(b, rb)} |")


def same_tags(out: list[str], a: Run, b: Run, step: int):
    """Every tag in both runs in the same year: the median of B over A."""
    out += ["", "## Every country in both runs: B over A", "",
            "The median of the ratio over the tags present in both runs that year, and the share of tags where B is "
            "higher. 1.00 is no difference.", "",
            "| Year | Tags | GDP | B higher | Building levels | B higher | Technologies | B higher | "
            "Small economies: GDP | B higher |", "|---|---|---|---|---|---|---|---|---|---|"]
    years = common_years(a, b)
    for year in [y for y in years if y % step == 0 or y == years[-1]]:
        ta, tb = a.by_tag(year), b.by_tag(year)
        tags = sorted(set(ta) & set(tb))

        def cells(name, only=None):
            values = [num(tb[t], name) / num(ta[t], name) for t in tags
                      if num(ta[t], name) > 0 and (only is None or only(t))]
            if not values:
                return "- | -"
            return f"{statistics.median(values):.2f} | {100 * sum(1 for v in values if v > 1) / len(values):.0f}%"
        small = (lambda t: a.first_gdp.get(ta[t]["id"], 0) < SMALL)
        out.append(f"| {year} | {len(tags)} | {cells('gdp')} | {cells('levels')} | {cells('techs')} | "
                   f"{cells('gdp', small)} |")


def laws_held(out: list[str], a: Run, b: Run, part=None, title="Laws held in the last year both runs reached"):
    years = common_years(a, b)
    if not years:
        return
    year = years[-1]
    out += ["", f"## {title}", "", f"Year {year}. The four commonest laws of each group, A then B; each run's laws "
            "are named by its own key.", "", "| Group | A | B |", "|---|---|---|"]
    for group in a.key["law_groups"]:
        name = "lw_" + (group[len("lawgroup_"):] if group.startswith("lawgroup_") else group).lower()

        def commonest(run):
            names = run.key["laws"].get(group, [])
            counts = Counter(num(r, name) for r in run.rows(year, year + 1, part))
            if not counts.keys() - {0}:
                return None
            return ", ".join(f"{names[i - 1] if 0 < i <= len(names) else 'none'} {n}" for i, n in counts.most_common(4))
        ca, cb = commonest(a), commonest(b)
        if ca or cb:
            out.append(f"| {group} | {ca or '-'} | {cb or '-'} |")


def events_logged(out: list[str], a: Run, b: Run):
    ea, eb = Counter(e["event"] for e in a.events), Counter(e["event"] for e in b.events)
    out += ["", "## Events logged over the whole run", "", "| Event | A | B |", "|---|---|---|"]
    for name in sorted(set(ea) | set(eb), key=lambda n: -(ea[n] + eb[n])):
        out.append(f"| {name} | {ea[name]:,} | {eb[name]:,} |")
    for label, run in (("A", a), ("B", b)):
        names = run.key["all_laws"]
        starts = Counter(num(e, "law") for e in run.events if e["event"] == "law_start")
        if starts:
            out += ["", f"Laws the AI started most in {label}: " + ", ".join(
                f"{names[i - 1] if 0 < i <= len(names) else 'unknown'} {n}" for i, n in starts.most_common(15))]


def side(a: Run, b: Run, step: int = 10, top_n: int = TOP_N) -> str:
    out = [f"# AI probe: {a.name} (A) against {b.name} (B)", "", f"- {a.describe()}", f"- {b.describe()}", "",
           "Every cell is A → B. One run of each build is one sample: the AI is not deterministic, so read a "
           "difference only where it is large or steady, and see `ai_probe_compare.py paired` for the fairest "
           "reading. The largest economies come first: they are what a player competes with (owner, 2026-11-16), "
           "and by count most countries are small, so a median over every country describes a small one. Each "
           "country counts once a calendar year, and the construction figures leave out the readings that are "
           "not the year (ai_probe_report.x_construction)."]
    figure_table(out, a, b, step, f"The {top_n} largest AI economies of each year, by that year's GDP", TOP_FIGURES,
                 part="top")
    top_by_tag(out, a, b, step, top_n)
    figure_table(out, a, b, step, f"Every other AI country (outside the {top_n} largest), for contrast",
                 REST_FIGURES, part="rest")
    world_totals(out, a, b, step)
    for title, figures in SECTIONS:
        lens_tables(out, a, b, step, title, figures, top_n)
    laws_held(out, a, b, part="top", title=f"Laws held by the {top_n} largest in the last year both runs reached")
    out += ["", "# The typical country (most are small)"]
    same_tags(out, a, b, step)
    figure_table(out, a, b, step, "Small economies only (GDP under 1 million at the first report)", SMALL_FIGURES,
                 part="small", lens="all")
    laws_held(out, a, b)
    events_logged(out, a, b)
    return "\n".join(out) + "\n"


# --- paired ----------------------------------------------------------------------------------------------------------

def crash_test(run: Run):
    """crash(row) for one run, and how it is read: from the logged cycle where the row has it (version 3), else
    inferred from the pool's income against the country's own median under the same economic-system law."""
    def pool_share(r):
        return num(r, "pool_income") * 52 / num(r, "gdp") if num(r, "gdp") > 0 else None

    shares: dict[tuple, list[float]] = defaultdict(list)
    for r in run.ai:
        share = pool_share(r)
        if r["y"] >= CRASH_MEDIAN_FROM and share is not None:
            shares[(r["tag"], num(r, "lw_economic_system"))].append(share)
    medians = {slot: statistics.median(v) for slot, v in shares.items() if len(v) >= 5}

    def crash(r) -> bool:
        if banked(r):
            return in_crisis(r)
        median = medians.get((r["tag"], num(r, "lw_economic_system")))
        share = pool_share(r)
        return median is not None and median >= CRASH_POOL_FLOOR and share is not None and share < CRASH_SHARE * median
    return crash




def paired(a: Run, b: Run, top_n: int = TOP_N, step: int = 10) -> str:
    crash_a, crash_b = crash_test(a), crash_test(b)
    how = {run.name: "logged (version 3)" if run.banked else "inferred from the pool's income" for run in (a, b)}
    out = [f"# AI probe, paired: {a.name} (A) against {b.name} (B)", "", f"- {a.describe()}", f"- {b.describe()}", "",
           f"The same tag in both runs, among the {top_n} largest of either run in the decade (by mean GDP) and "
           "present in both, kept only in the years both runs have it under the same economic-system law, with no "
           f"banking crash in either and GDP within {GDP_APART} times. Crash years: A {how[a.name]}, B {how[b.name]}. "
           "Logged, a crash year is a crash in the year before the report, a month in a panic or downturn since "
           "the last, or a panic or downturn at it; inferred, it is a year whose pool income is under "
           f"{CRASH_SHARE:.0%} of the country's own median under that law, for a country whose median is "
           f"{CRASH_POOL_FLOOR:.0%} of GDP or more. Cells are sums over the "
           "kept tag-years: A → B, and B over A where it reads as one. The construction points leave out the "
           "readings that are not the year in either run. This answers whether the same economies did differently "
           "in comparable years; what the runs did differently in which years (wars, crashes, law paths) is the "
           "`side` report's.", "",
           "| Decade | Kept (of tag-years in both) | Left out: crash, law, GDP apart | Tags | GDP, B/A | "
           "Building levels per M GDP | Technologies, mean | Tax, % of GDP | Pool income, % of GDP | "
           "Built + expanded per country a year | Private points per M GDP | Government points per M GDP | "
           "Private goods per private point |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    years = common_years(a, b)
    if not years:
        return "\n".join(out + ["", "The runs share no year."]) + "\n"
    start = years[0] - years[0] % step
    for d0 in range(start, years[-1] + 1, step):
        span = [y for y in years if d0 <= y < d0 + step]
        if not span:
            continue
        tables = {run.name: {y: run.by_tag(y) for y in span} for run in (a, b)}

        def largest(run):
            gdps = defaultdict(list)
            for y in span:
                for tag, r in tables[run.name][y].items():
                    gdps[tag].append(gdp(r))
            return {t for t, _ in sorted(gdps.items(), key=lambda item: -statistics.fmean(item[1]))[:top_n]}
        tags = largest(a) | largest(b)
        sums = {"A": defaultdict(float), "B": defaultdict(float)}
        kept, both, left, kept_tags = 0, 0, Counter(), set()
        for tag in tags:
            for y in span:
                ra, rb = tables[a.name][y].get(tag), tables[b.name][y].get(tag)
                if not ra or not rb:
                    continue
                both += 1
                if crash_a(ra) or crash_b(rb):
                    left["crash"] += 1
                    continue
                if num(ra, "lw_economic_system") != num(rb, "lw_economic_system"):
                    left["law"] += 1
                    continue
                if gdp(ra) <= 0 or gdp(rb) <= 0 or max(gdp(ra), gdp(rb)) / min(gdp(ra), gdp(rb)) > GDP_APART:
                    left["gdp"] += 1
                    continue
                kept += 1
                kept_tags.add(tag)
                x_ok = P.valid_x(ra) and P.valid_x(rb)
                for side_, r in (("A", ra), ("B", rb)):
                    s = sums[side_]
                    for name in ("gdp", "levels", "techs", "tax_income", "pool_income"):
                        s[name] += num(r, name)
                    s["built"] += built(r)
                    s["rows"] += 1
                    if x_ok:
                        s["x_gdp"] += gdp(r)
                        for name in ("con_used_priv", "con_used_gov", "con_goods_priv"):
                            s["x_" + name] += xval(r, name) or 0
        if not both:
            continue
        sa, sb = sums["A"], sums["B"]

        def ratio_of(s, top, bottom, scale=1.0, digits=1):
            return f"{s[top] / s[bottom] * scale:,.{digits}f}" if s[bottom] else "-"

        def cell(top, bottom, scale=1.0, digits=1):
            return f"{ratio_of(sa, top, bottom, scale, digits)} → {ratio_of(sb, top, bottom, scale, digits)}"
        gdp_ratio = f"{sb['gdp'] / sa['gdp']:.3f}" if sa["gdp"] else "-"
        out.append(f"| {d0}s | {kept} of {both} | {left['crash']}, {left['law']}, {left['gdp']} | {len(kept_tags)} | "
                   f"{gdp_ratio} | {cell('levels', 'gdp', 1e6, 1)} | {cell('techs', 'rows', 1, 1)} | "
                   f"{cell('tax_income', 'gdp', 5200, 1)} | {cell('pool_income', 'gdp', 5200, 1)} | "
                   f"{cell('built', 'rows', 1, 1)} | {cell('x_con_used_priv', 'x_gdp', 1e6, 2)} | "
                   f"{cell('x_con_used_gov', 'x_gdp', 1e6, 2)} | {cell('x_con_goods_priv', 'x_con_used_priv', 1, 0)} |")
    return "\n".join(out) + "\n"


# --- cadence ---------------------------------------------------------------------------------------------------------

def cadence(runs: list[Run], until_k: int, top_n: int = TOP_N) -> str:
    """Law starts per idle month by agenda, months 1..until_k, every AI country and the largest at the cut."""
    results = []
    for run in runs:
        events = [e for e in run.events if e["k"] <= until_k]
        rows = [r for r in run.ai if r["k"] <= until_k]
        latest: dict[int, dict] = {}
        for r in rows:
            if r["id"] not in latest or r["k"] > latest[r["id"]]["k"]:
                latest[r["id"]] = r
        tags = {r["tag"] for r in sorted(latest.values(), key=lambda r: -gdp(r))[:top_n]}
        strategies = run.key["strategies"]["political"]
        every = P.law_cadence(events, rows, strategies)
        biggest = P.law_cadence(events, rows, strategies, include=lambda tag, k, tags=tags: tag in tags)
        date = run.parsed.ticks.get(until_k, {}).get("date", "not reached")
        results.append((run, {"every": every, "top": biggest}, date, len(events)))
    out = [f"# Law starts per idle month, months 1 to {until_k}", ""]
    out += [f"- {run.describe()}; month {until_k} is {date}; {n:,} events to the cut" for run, _, date, n in results]
    for part, heading in (("top", f"The {top_n} largest AI economies at the cut (each country's last report)"),
                          ("every", "Every AI country")):
        out += ["", f"## {heading}: starts / idle months = starts per idle month", "",
                "| Agenda | " + " | ".join(run.name for run, *_ in results) + " |",
                "|---|" + "---|" * len(results)]
        agendas = list(dict.fromkeys(row["agenda"] for _, tables, *_ in results for row in tables[part]))
        for agenda in agendas + ["all agendas"]:
            cells = []
            for _, tables, *_ in results:
                rows = tables[part] if agenda == "all agendas" else [r for r in tables[part] if r["agenda"] == agenda]
                starts, months = sum(r["starts"] for r in rows), sum(r["months"] for r in rows)
                cells.append(f"{starts} / {months} = {starts / months:.4f}" if months else "-")
            out.append(f"| {agenda} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


# --- series ----------------------------------------------------------------------------------------------------------

def country_names(root: Path = ROOT) -> dict[str, str]:
    """Each tag's English name: vanilla's (vanilla_parsed/localization_english.json), the mod's replace/ files over
    it (the mod renames some vanilla things)."""
    names: dict[str, str] = {}
    vanilla = root / "vanilla_parsed" / "localization_english.json"
    if vanilla.is_file():
        data = json.loads(vanilla.read_text(encoding="utf-8"))
        names = {k: v for k, v in data.items() if re.fullmatch(r"[A-Z][A-Z0-9]{2}", k) and isinstance(v, str)}
    for path in sorted((root / "localization" / "english" / "replace").glob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            found = re.match(r'\s+([A-Z][A-Z0-9]{2}):\d*\s+"(.*)"', line)
            if found:
                names[found.group(1)] = found.group(2)
    return names


def measures(rows: list[dict]) -> dict:
    n = len(rows)
    total_gdp = sum(gdp(r) for r in rows)
    pop = sum(num(r, "pop") for r in rows)
    kept = [r for r in rows if P.valid_x(r)]

    def pct(test, among=rows):
        return round(100 * sum(1 for r in among if test(r)) / len(among), 1) if among else None

    def of_gdp(total):
        return round(total * 5200 / total_gdp, 2) if total_gdp else None
    banking = [r for r in rows if banked(r)]
    banking_gdp = sum(gdp(r) for r in banking)
    return {
        "countries": n,
        "gdp_m": round(total_gdp / 1e6, 1),
        "gdp_head": round(total_gdp / pop, 3) if pop else None,
        "levels": round(sum(num(r, "levels") for r in rows)),
        "tax_pct": of_gdp(sum(num(r, "tax_income") for r in rows)),
        "buying_pct": pct(lambda r: num(r, "cm_public") > 0),
        "paused_pct": pct(lambda r: num(r, "paused") == 1),
        "debt40_pct": pct(lambda r: num(r, "debt_scaled") >= 0.4),
        "con_gov": round(sum(xval(r, "con_used_gov") or 0 for r in kept), 1),
        "con_priv": round(sum(xval(r, "con_used_priv") or 0 for r in kept), 1),
        "con_unused": round(sum(xval(r, "con_unused") or 0 for r in kept), 1),
        "con_left_out": sum(1 for r in rows if P.x_construction(r) in ("unpaid", "idle")),
        "pool_pct": of_gdp(sum(num(r, "pool_income") for r in rows)),
        "crisis_gdp_pct": (round(100 * sum(gdp(r) for r in banking if in_crisis(r)) / banking_gdp, 1)
                           if banking_gdp else None),
        "techs": statistics.median(num(r, "techs") for r in rows) if rows else None,
        "universities": round(statistics.fmean(num(r, "bt_university") for r in rows), 2) if rows else None,
        "enacting_pct": pct(lambda r: num(r, "enacting") == 1),
        "army": statistics.median(num(r, "army") for r in rows) if rows else None,
        "sol": round(sum(num(r, "sol") * num(r, "pop") for r in rows) / pop, 2) if pop else None,
    }


def series(runs: list[Run], top_n: int = TOP_N, names: dict[str, str] | None = None) -> tuple[dict, dict]:
    """yearly.json's and countries.json's contents."""
    names = country_names() if names is None else names
    lasts = [run.last_complete_year() for run in runs]
    if not runs or any(year is None for year in lasts) or any(not run.years for run in runs):
        return {"rows": [], "meta": []}, {"rows": [], "meta": []}
    last = min(lasts)
    first = max(run.years[0] for run in runs)
    shown = {r["tag"] for run in runs for r in run.ai if r["id"] in run.top.get(r["y"], ())}
    yearly, countries = [], []
    for run in runs:
        for year in range(first, last + 1):
            rows = run.rows(year, year + 1)
            ranked = sorted(rows, key=lambda r: -gdp(r))
            for lens, members in (("top20", ranked[:top_n]), ("world", rows)):
                yearly.append({"key": f"{lens}-{run.name}-{year}", "lens": lens, "run": run.name, "year": year,
                               "latest": "yes" if year == last else "no", **measures(members)})
            by_tag = {tag: r for tag, r in run.by_tag(year).items() if tag in shown}
            line = dict(by_tag)
            successor = by_tag.get("GER") or by_tag.get("PRU")      # Prussia's line carries on as Germany's
            if successor is not None:
                line["PRU-GER"] = successor
            for tag, r in line.items():
                countries.append({"key": f"{tag}-{run.name}-{year}", "tag": tag,
                                  "country": names.get(r["tag"], r["tag"]), "run": run.name, "year": year,
                                  "gdp_m": round(num(r, "gdp") / 1e6, 2), "levels": round(num(r, "levels")),
                                  "techs": num(r, "techs")})
    meta = [{"label": "Made by", "value": "scripts/analysis/ai_probe_compare.py series"},
            {"label": "Runs", "value": "; ".join(run.describe() for run in runs)},
            {"label": "Note", "value": f"Years {first} to {last}, each complete in every run. Each country once a "
                                       "calendar year; construction sums leave out the readings that are not the "
                                       "year (con_left_out counts them). One game of each build, and the AI is not "
                                       "deterministic."}]
    return {"rows": yearly, "meta": meta}, {"rows": countries, "meta": meta}


# --- main ------------------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = parser.add_subparsers(dest="verb", required=True)
    for verb in ("side", "paired"):
        p = sub.add_parser(verb)
        p.add_argument("a", help="the baseline run, NAME=LOG[:KEY]")
        p.add_argument("b", help="the changed build's run, NAME=LOG[:KEY]")
        p.add_argument("--until", type=int, help="read no report after this year")
        p.add_argument("--top", type=int, default=TOP_N, help="how many economies count as the largest")
        p.add_argument("--md", type=Path, help="write the tables here as well")
        if verb == "side":
            p.add_argument("--years", type=int, default=10, help="years per row (default 10)")
    p = sub.add_parser("cadence")
    p.add_argument("runs", nargs="+", help="NAME=LOG[:KEY] for each run")
    p.add_argument("--until-k", type=int, required=True, help="the probe's month count to cut every run at")
    p.add_argument("--top", type=int, default=TOP_N)
    p.add_argument("--md", type=Path)
    p = sub.add_parser("series")
    p.add_argument("runs", nargs="+", help="NAME=LOG[:KEY] for each run")
    p.add_argument("--out", type=Path, required=True, help="the folder for yearly.json and countries.json")
    p.add_argument("--top", type=int, default=TOP_N)
    args = parser.parse_args(argv)

    if args.verb in ("side", "paired"):
        a, b = load_runs([args.a, args.b], args.until, args.top)
        text = side(a, b, args.years, args.top) if args.verb == "side" else paired(a, b, args.top)
    elif args.verb == "cadence":
        text = cadence(load_runs(args.runs, top_n=args.top), args.until_k, args.top)
    else:
        yearly, countries = series(load_runs(args.runs, top_n=args.top), args.top)
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "yearly.json").write_text(json.dumps(yearly), encoding="utf-8")
        (args.out / "countries.json").write_text(json.dumps(countries), encoding="utf-8")
        print(f"{len(yearly['rows'])} yearly rows, {len(countries['rows'])} country rows -> {args.out}")
        return 0
    sys.stdout.write(text)
    if getattr(args, "md", None):
        args.md.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
