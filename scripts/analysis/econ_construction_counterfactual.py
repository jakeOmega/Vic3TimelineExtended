"""Construction-channel counterfactual from the playthrough data (issue #1034, Task 8b).

WHY THIS EXISTS
---------------
The structural sim (econ_growth_sim) can't hold the owner's game: its hindcast misses.
This answers the owner's question straight from the calibration dataset instead, with
no model: if the GDP-per-capita construction cost curve had had another shape, how many
more (or fewer) construction points would the same money have bought, how many jobs
would they have made, and how fast would that have absorbed the observed slack
(peasants + unemployed)?

THE ARITHMETIC
--------------
Per interval between kept saves (a save under a year after the last kept one is dropped,
its interval merging into the next, as `econ_sim_scenarios.realised_alloc` does):

  points       sum over level-bound types (econ_growth_sim.LEVEL_BOUND) of
               max(0, levels gained) x the type's required_construction points
  gross_jobs   the same types' levels gained x staff a staffed level at the end
               (employees / staffing); jobs_per_point = gross_jobs / points
  ratio        the mean over the two ends of (1 + x_adj) / (1 + x_adj'), where
               x_adj is the script's prior_construction_scaling, x_adj' the same
               figure under the shape, and the other cost sources carry over:
               others = (1 + x_adj) / (1 + x_raw) - 1, x_adj' = (1 + x_raw')(1 + others) - 1
               (x_raw is X under econ_sim_data.HISTORICAL_CURVE, the curve the
               playthrough ran under, not the mod's current one)
  extra jobs   points x (ratio - 1) x jobs_per_point, summed over the intervals so far

and at each kept save after the first, slack_cf = max(0, slack - extra jobs) and
vacancies_cf = max(0, extra jobs - slack), as shares of the slice's workforce.
Population, the workforce and demand-bound jobs stay as observed.

Two points the definitions leave open, decided from the data:

  * A level-bound type with no required_construction (company buildings, army and
    naval logistics centres, conscription centres) buys no points, and its levels
    aren't bought with points either, so its jobs don't count in gross_jobs. They are
    reported as `uncosted_jobs`. Late in the game they gain tens of thousands of levels
    an interval, which would otherwise inflate jobs_per_point where the ratios are
    largest.
  * The other sources cancel out of the ratio: (1 + x_adj) / (1 + x_adj') is
    (1 + x_raw) / (1 + x_raw') whenever x_raw > 0, whatever the prior. The ratio is
    computed in that form, so the `historical` shape gives exactly 1.

THE SHAPES
----------
  historical   the curve the playthrough ran under (HISTORICAL_CURVE: +1000% at GBP 100,
               ruling R37): the baseline, which reproduces the observed history exactly
  current      the mod's curve as its files hold it now (since #1034 capped at +100% from
               GBP 11); `linear` is the same curve under its older name
  capped:c     the historical line held at +c (the slope kept; `capped:1` is `current`
               to within a percent)
  slope:k      the historical line at k times the steepness
  log, sqrt, world, none
               as econ_growth_sim.cost_mult defines them, on the historical constants

All are priced against the historical baseline. The shapes other than `current` and
`linear` are built on the historical constants, not the mod's: a `capped:2` built on the
current ones would stay at +100%, because that line already stops there.

STATED LIMITS
-------------
No compounding (extra levels add GDP, which buys more construction later); no extra
services demand from a bigger economy; maintenance and retooling, which X also raises,
aren't re-priced; population and migration are held at observed. The first three
understate a cheaper curve's effect; holding population ignores migration toward new
jobs, which would offset some of it.

    econ_construction_counterfactual.py [--series FRA,union,GBR,CHI] [--curves historical,current,none,...]
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REPO = Path(__file__).resolve().parents[2]
# Direct CLI execution starts with scripts/analysis on sys.path.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from scripts.analysis import econ_growth_sim as G  # noqa: E402
from scripts.analysis import econ_sim_data as D  # noqa: E402
from scripts.analysis import econ_sim_scenarios as S  # noqa: E402

DEFAULT_SERIES = ("FRA", "union", "GBR", "CHI")
DEFAULT_SHAPES = ("historical", "current", "capped:1.25", "capped:1.5", "capped:2", "slope:0.5", "log", "sqrt",
                  "world", "none")
OWN_SHAPES = ("historical", "current")          # shape names of this tool, beside econ_growth_sim.CURVES
SUMMARY_YEARS = (1917, 1954, 1976, 1998, 2023, 2045)
NEAREST_WITHIN = 3.0                            # years: a summary year with no point this close is None
VACANCY_ONSET = 0.01                            # vacancies over this share of the workforce: mode 1
OFF_BY = 2.0                                    # flag an interval whose points and observed points differ this much

CostOf = Callable[[str], "float | None"]
SectorOf = Callable[[str], "str | None"]


# --------------------------------------------------------------------------
# Curve shapes and the price ratio
# --------------------------------------------------------------------------


def _shape(shape: str, current: D.CurveConstants) -> tuple[G.Params, D.CurveConstants]:
    """The Params and curve constants a shape name stands for.

    "historical" is the curve the playthrough ran under; "current" (and "linear", the same
    curve under its older name) is `current`, the mod's constants as its files hold them.
    Every other shape is built on the historical constants: a name in
    econ_growth_sim.CURVES (bar "capped" and "linear"), "capped:c" (the historical line held
    at c), or "slope:k" (the historical line with max_mult x k)."""
    curve = D.HISTORICAL_CURVE
    if shape == "historical":
        return G.Params(curve="linear"), curve
    if shape in ("current", "linear"):
        return G.Params(curve="linear"), current
    if ":" in shape:
        kind, _, arg = shape.partition(":")
        try:
            k = float(arg)
        except ValueError:
            raise ValueError("shape " + repr(shape) + ": " + repr(arg) + " is not a number") from None
        if kind == "capped":
            return G.Params(curve="capped", curve_cap=k), curve
        if kind == "slope":
            return G.Params(curve="linear"), dataclasses.replace(curve, max_mult=curve.max_mult * k)
        raise ValueError("unknown shape " + repr(shape) + "; expected capped:<c> or slope:<k>")
    if shape == "capped":
        raise ValueError("the capped shape needs its cap: capped:<c>")
    if shape not in G.CURVES:
        raise ValueError("unknown shape " + repr(shape) + "; expected one of "
                         + ", ".join(OWN_SHAPES + tuple(c for c in G.CURVES if c != "linear"))
                         + ", capped:<c> or slope:<k>")
    return G.Params(curve=shape), curve


def x_raw_of(gdppc: float) -> float:
    """X at `gdppc` on the curve the playthrough ran under (D.HISTORICAL_CURVE)."""
    return G.cost_mult(G.Params(curve="linear"), D.HISTORICAL_CURVE, gdppc)


def x_under(shape: str, gdppc: float, current: D.CurveConstants, world_gdppc: float | None) -> float:
    """x_raw': the shape's X at `gdppc`; `current` is the mod's constants as read from its files."""
    p, c = _shape(shape, current)
    return G.cost_mult(p, c, gdppc, world_gdppc)


def others_of(x_raw: float, x_adj: float) -> float:
    """The other goods_input_construction_mult sources the script folds into x_adj."""
    return (1.0 + x_adj) / (1.0 + x_raw) - 1.0 if x_raw > 0 else 0.0


def x_adj_under(shape: str, gdppc: float, x_adj: float | None, numbers, world_gdppc: float | None) -> float:
    """x_adj': the shape's X at `gdppc`, combined with the same other sources."""
    x_raw = x_raw_of(gdppc)
    others = others_of(x_raw, x_raw if x_adj is None else x_adj)
    return (1.0 + x_under(shape, gdppc, numbers.curve, world_gdppc)) * (1.0 + others) - 1.0


def shape_ratio(shape: str, gdppc: float, x_adj: float | None, numbers, world_gdppc: float | None) -> float:
    """(1 + x_adj) / (1 + x_adj'): how many times the points the same money buys under
    `shape`. `x_adj` None means the script hadn't set one, so it is x_raw.

    With x_raw > 0 the other sources cancel and this is (1 + x_raw) / (1 + x_raw'),
    the form computed here (exactly 1 for the historical shape)."""
    x_raw = x_raw_of(gdppc)
    x_new = x_under(shape, gdppc, numbers.curve, world_gdppc)
    if x_raw > 0:
        return (1.0 + x_raw) / (1.0 + x_new)
    return (1.0 + (x_raw if x_adj is None else x_adj)) / (1.0 + x_new)


def world_gdppc_at(world: list[dict], date: str) -> float | None:
    """The world's GDP per head at `date`, linear between the dataset's world points and
    flat past either end; None with no usable point."""
    pts = [(S.point_year(w["date"]), w["gdp"] / w["population"]) for w in world if w["population"] > 0]
    return S._linear(pts, S.point_year(date))


# --------------------------------------------------------------------------
# Intervals
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Interval:
    start: str
    end: str
    years: float
    points: float                   # realised: level-bound levels gained x their construction points
    points_observed: float          # mean of the two ends' points a week x 52 x years (a check)
    gross_jobs: float               # jobs in the levels those points bought
    jobs_per_point: float
    net_jobs_change: float          # level-bound employees at the end - at the start (a check)
    gdppc_start: float
    gdppc_end: float
    x_adj_start: float
    x_adj_end: float
    others_start: float
    others_end: float
    x_raw_start: float
    x_raw_end: float
    uncosted_jobs: float            # jobs in level-bound levels gained that cost no points
    annexed_levels: float           # levels in states new at the end (the union's per_state; else 0)


def kept_points(points: list[dict]) -> list[dict]:
    """The points in date order, each under a year after the last kept one dropped.

    The same rule as econ_sim_scenarios.realised_alloc, which keeps it inline."""
    kept: list[dict] = []
    for pt in sorted(points, key=lambda p: S.point_year(p["date"])):
        if not kept or S.point_year(pt["date"]) - S.point_year(kept[-1]["date"]) >= S.MIN_ALLOC_SPAN:
            kept.append(pt)
    return kept


def _lookups(md, cost_of: CostOf | None, sector_of: SectorOf | None) -> tuple[CostOf, SectorOf]:
    """The cost and sector lookups, defaulting to the mod's own (cached by type)."""
    if cost_of is None:
        costs: dict[str, float | None] = {}

        def cost_of(btype: str) -> float | None:
            if btype not in costs:
                costs[btype] = S._type_cost(md, btype)
            return costs[btype]
    if sector_of is None:
        sectors: dict[str, str] = {}

        def sector_of(btype: str) -> str:
            if btype not in sectors:
                sectors[btype] = D.sector_of(md.ms, btype)
            return sectors[btype]
    return cost_of, sector_of


def _x_adj(owner: dict, x_raw: float) -> float:
    prior = owner.get("variables", {}).get("prior_construction_scaling")
    return x_raw if prior is None else float(prior)


def intervals(series: dict, md, cost_of: CostOf | None = None, sector_of: SectorOf | None = None) -> list[Interval]:
    """One Interval per pair of consecutive kept points of `series` (a dataset series)."""
    cost_of, sector_of = _lookups(md, cost_of, sector_of)
    kept = kept_points(series["points"])
    out: list[Interval] = []
    for a, b in zip(kept, kept[1:]):
        before, after = a["slice"]["buildings_by_type"], b["slice"]["buildings_by_type"]
        points = gross = uncosted = 0.0
        for btype, info in after.items():
            if sector_of(btype) not in G.LEVEL_BOUND:
                continue
            gained = info["levels"] - before.get(btype, {}).get("levels", 0.0)
            if gained <= 0:
                continue
            staff = info["employees"] / info["staffing"] if info["staffing"] > 0 else 0.0
            cost = cost_of(btype) or 0.0
            if cost > 0:
                points += gained * cost
                gross += gained * staff
            else:
                uncosted += gained * staff

        def employees(buildings: dict) -> float:
            return sum(i["employees"] for t, i in buildings.items() if sector_of(t) in G.LEVEL_BOUND)

        years = S.point_year(b["date"]) - S.point_year(a["date"])
        observed = (sum(a["owner"]["points_weekly"].values()) + sum(b["owner"]["points_weekly"].values())) / 2
        new_states = set(b.get("per_state", {})) - set(a.get("per_state", {}))
        ends = []
        for pt in (a, b):
            gdppc = pt["owner"]["gdppc"]
            x_raw = x_raw_of(gdppc)
            x_adj = _x_adj(pt["owner"], x_raw)
            ends.append((gdppc, x_raw, x_adj, others_of(x_raw, x_adj)))
        (g_a, xr_a, xa_a, o_a), (g_b, xr_b, xa_b, o_b) = ends
        out.append(Interval(
            start=a["date"], end=b["date"], years=years,
            points=points, points_observed=observed * 52.0 * years,
            gross_jobs=gross, jobs_per_point=gross / points if points > 0 else 0.0,
            net_jobs_change=employees(after) - employees(before),
            gdppc_start=g_a, gdppc_end=g_b, x_adj_start=xa_a, x_adj_end=xa_b,
            others_start=o_a, others_end=o_b, x_raw_start=xr_a, x_raw_end=xr_b,
            uncosted_jobs=uncosted,
            annexed_levels=float(sum(b["per_state"][s][4] for s in new_states)),
        ))
    return out


# --------------------------------------------------------------------------
# The counterfactual
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Row:
    date: str
    workforce: float
    slack_obs_share: float
    slack_cf_share: float
    vacancies_cf_share: float
    cum_extra_jobs: float


def _interval_ratio(iv: Interval, shape: str, numbers, world: list[dict]) -> float:
    return (shape_ratio(shape, iv.gdppc_start, iv.x_adj_start, numbers, world_gdppc_at(world, iv.start))
            + shape_ratio(shape, iv.gdppc_end, iv.x_adj_end, numbers, world_gdppc_at(world, iv.end))) / 2.0


def _paths(series: dict, md, shape: str, world: list[dict], cost_of, sector_of) -> tuple[list[Row], float, float]:
    """(rows, total extra points, total realised points)."""
    _shape(shape, md.numbers.curve)                     # an unknown shape raises before any arithmetic
    ivs = intervals(series, md, cost_of, sector_of)
    by_date = {pt["date"]: pt for pt in kept_points(series["points"])}
    rows: list[Row] = []
    cum = extra_points = 0.0
    for iv in ivs:
        extra = iv.points * (_interval_ratio(iv, shape, md.numbers, world) - 1.0)
        extra_points += extra
        cum += extra * iv.jobs_per_point
        slice_ = by_date[iv.end]["slice"]
        workforce = float(slice_["workforce"])
        slack = float(slice_["peasants"] + slice_["unemployed"])

        def share(x: float) -> float:
            return x / workforce if workforce > 0 else 0.0

        rows.append(Row(
            date=iv.end, workforce=workforce,
            slack_obs_share=share(slack),
            slack_cf_share=share(max(0.0, slack - cum)),
            vacancies_cf_share=share(max(0.0, cum - slack)),
            cum_extra_jobs=cum,
        ))
    return rows, extra_points, sum(iv.points for iv in ivs)


def counterfactual(series: dict, md, shape: str, world: list[dict],
                   cost_of: CostOf | None = None, sector_of: SectorOf | None = None) -> list[Row]:
    """The slack path under `shape`: one Row per kept point after the first."""
    return _paths(series, md, shape, world, cost_of, sector_of)[0]


@dataclass(frozen=True)
class Summary:
    series: str
    shape: str
    extra_points_pct: float         # sum of extra points / sum of realised points x 100
    slack_1917: float | None        # slack_cf_share at the point nearest each year (None: none within 3 years)
    slack_1954: float | None
    slack_1976: float | None
    slack_1998: float | None
    slack_2023: float | None
    slack_2045: float | None
    first_below_10pct: int | None   # first year slack_cf_share < 0.10
    first_below_5pct: int | None
    first_vacancies: int | None     # first year vacancies_cf_share > 0.01: the mode-1 onset proxy
    vacancies: tuple[float | None, ...] = ()    # vacancies_cf_share at the same points, in SUMMARY_YEARS order


def _nearest(rows: list[Row], year: int) -> Row | None:
    near = [(abs(S.point_year(r.date) - year), r) for r in rows]
    near = [(d, r) for d, r in near if d <= NEAREST_WITHIN]
    return min(near, key=lambda dr: dr[0])[1] if near else None


def _first(rows: list[Row], test) -> int | None:
    return next((int(r.date[:4]) for r in rows if test(r)), None)


def summarize(series_name: str, series: dict, md, shape: str, world: list[dict],
              cost_of: CostOf | None = None, sector_of: SectorOf | None = None) -> Summary:
    rows, extra, total = _paths(series, md, shape, world, cost_of, sector_of)
    near = [_nearest(rows, y) for y in SUMMARY_YEARS]
    return Summary(
        series=series_name, shape=shape,
        extra_points_pct=extra / total * 100.0 if total > 0 else 0.0,
        **{"slack_" + str(y): None if r is None else r.slack_cf_share for y, r in zip(SUMMARY_YEARS, near)},
        first_below_10pct=_first(rows, lambda r: r.slack_cf_share < 0.10),
        first_below_5pct=_first(rows, lambda r: r.slack_cf_share < 0.05),
        first_vacancies=_first(rows, lambda r: r.vacancies_cf_share > VACANCY_ONSET),
        vacancies=tuple(None if r is None else r.vacancies_cf_share for r in near),
    )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _pct(x: float | None) -> str:
    return "n/a" if x is None else format(100.0 * x, ".1f") + "%"


def _num(x: float) -> str:
    return format(x, ",.0f")


def _diagnostics(name: str, ivs: list[Interval]) -> list[str]:
    lines = [
        "### " + name,
        "",
        "| start | end | years | points | observed | pts/obs | gross jobs | jobs/pt | uncosted jobs"
        " | net jobs change | gdppc | x_raw | x_adj | others | annexed levels |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---:|",
    ]
    for iv in ivs:
        ratio = iv.points / iv.points_observed if iv.points_observed > 0 else 0.0
        flag = " !" if ratio > OFF_BY or ratio < 1.0 / OFF_BY else ""
        lines.append("| " + " | ".join([
            iv.start, iv.end, format(iv.years, ".2f"), _num(iv.points), _num(iv.points_observed),
            format(ratio, ".2f") + flag, _num(iv.gross_jobs), format(iv.jobs_per_point, ".2f"),
            _num(iv.uncosted_jobs), _num(iv.net_jobs_change),
            format(iv.gdppc_start, ".2f") + " → " + format(iv.gdppc_end, ".2f"),
            format(iv.x_raw_start, ".2f") + " → " + format(iv.x_raw_end, ".2f"),
            format(iv.x_adj_start, ".2f") + " → " + format(iv.x_adj_end, ".2f"),
            format(iv.others_start, ".2f") + " → " + format(iv.others_end, ".2f"),
            _num(iv.annexed_levels),
        ]) + " |")
    points, observed = sum(iv.points for iv in ivs), sum(iv.points_observed for iv in ivs)
    off = sum(1 for iv in ivs if iv.points_observed > 0
              and not 1.0 / OFF_BY <= iv.points / iv.points_observed <= OFF_BY)
    lines += ["", "Totals: points " + _num(points) + ", observed " + _num(observed)
              + (", ratio " + format(points / observed, ".2f") if observed > 0 else "")
              + "; " + str(off) + " of " + str(len(ivs)) + " intervals off by more than "
              + format(OFF_BY, "g") + "x (marked !).", ""]
    return lines


def _cell(slack: float | None, vacancies: float | None) -> str:
    return "vac " + _pct(vacancies) if vacancies else _pct(slack)


def _summary_table(summaries: list[Summary]) -> list[str]:
    head = (["series", "shape", "extra points"] + ["slack " + str(y) for y in SUMMARY_YEARS]
            + ["slack < 10%", "slack < 5%", "vacancies > 1%"])
    lines = ["Slack cells are the counterfactual slack share, or \"vac x%\" where extra jobs exceed the slack;"
             " n/a: no point within " + format(NEAREST_WITHIN, "g") + " years.", "",
             "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for s in summaries:
        cells = [s.series, s.shape, format(s.extra_points_pct, "+.0f") + "%"]
        vacs = s.vacancies or (None,) * len(SUMMARY_YEARS)
        cells += [_cell(getattr(s, "slack_" + str(y)), v) for y, v in zip(SUMMARY_YEARS, vacs)]
        cells += ["never" if y is None else str(y) for y in (s.first_below_10pct, s.first_below_5pct, s.first_vacancies)]
        lines.append("| " + " | ".join(cells) + " |")
    return lines + [""]


def _path_table(paths: dict[str, list[Row]]) -> list[str]:
    shapes = list(paths)
    first = paths[shapes[0]]
    head = ["date", "workforce", "slack observed"] + shapes
    lines = ["Each cell is the counterfactual slack share, or \"vac x%\" where extra jobs exceed the slack.", "",
             "| " + " | ".join(head) + " |", "|---|---:|---:|" + "---:|" * len(shapes)]
    for i, row in enumerate(first):
        cells = [row.date, _num(row.workforce), _pct(row.slack_obs_share)]
        for shape in shapes:
            r = paths[shape][i]
            cells.append(_cell(r.slack_cf_share, r.vacancies_cf_share))
        lines.append("| " + " | ".join(cells) + " |")
    return lines + [""]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--series", default=",".join(DEFAULT_SERIES),
                    help="comma-separated dataset series (default %(default)s)")
    ap.add_argument("--curves", default=",".join(DEFAULT_SHAPES),
                    help="comma-separated shapes: " + ", ".join(OWN_SHAPES) + ", "
                    + ", ".join(c for c in G.CURVES if c not in ("capped", "linear"))
                    + ", capped:<c>, slope:<k>; linear is current (default %(default)s)")
    args = ap.parse_args(argv)
    names = [s for s in args.series.split(",") if s]
    shapes = [s for s in args.curves.split(",") if s]
    if not names or not shapes:
        print("error: --series and --curves each need at least one name", file=sys.stderr)
        return 2
    probe = D.CurveConstants(1.0, 1.0, 2.0, 1.0)      # a syntax check only: no figure here is the mod's
    for shape in shapes:
        try:
            _shape(shape, probe)
        except ValueError as exc:
            print("error: " + str(exc), file=sys.stderr)
            return 2
    dataset = S.load_dataset()
    unknown = [n for n in names if n not in dataset["series"]]
    if unknown:
        print("error: unknown series " + ", ".join(unknown) + "; the dataset has "
              + ", ".join(dataset["series"]), file=sys.stderr)
        return 2
    md = D.load_mod_data()
    cost_of, sector_of = _lookups(md, None, None)
    world = dataset["world"]

    out = ["## Per-interval diagnostics", ""]
    for name in names:
        out += _diagnostics(name, intervals(dataset["series"][name], md, cost_of, sector_of))
    out += ["## Summary", "", *_summary_table([
        summarize(name, dataset["series"][name], md, shape, world, cost_of, sector_of)
        for name in names for shape in shapes])]
    if "FRA" in names:
        fra = dataset["series"]["FRA"]
        out += ["## FRA slack path", "", *_path_table(
            {shape: counterfactual(fra, md, shape, world, cost_of, sector_of) for shape in shapes})]
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
