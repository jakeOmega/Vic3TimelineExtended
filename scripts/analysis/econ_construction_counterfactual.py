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
               max(0, levels gained) x the type's required_construction points,
               less the annexed share (below)
  gross_jobs   the same types' levels gained x staff a staffed level at the end
               (employees / staffing); jobs_per_point = gross_jobs / points
  ratio        the mean over the two ends of (1 + x_adj + others) / (1 + x_adj' + others),
               the point's whole goods_input_construction_mult now and under the shape.
               The script sets x_adj (its prior_construction_scaling) to x_raw x (1 + others),
               others being every other goods_input_construction_mult source, so
               others = x_adj / x_raw - 1 and x_adj' = x_raw' x (1 + others); the whole
               multiplier is (1 + x_raw)(1 + others), and the ratio is
               (1 + x_raw) / (1 + x_raw') (x_raw is X under econ_sim_data.HISTORICAL_CURVE,
               the curve the playthrough ran under, not the mod's current one)
  extra jobs   points x (ratio - 1) x jobs_per_point, summed over the intervals so far

and at each kept save after the first, slack_cf = max(0, slack - extra jobs) and
vacancies_cf = max(0, extra jobs - slack), as shares of the slice's workforce.
Population, the workforce and demand-bound jobs stay as observed.

A shape with a slack band (`current`, `slack:...`) has no ratio of its own: the share of
the GDP part that applies follows the counterfactual's own slack. Its path is yearly: each
interval is cut into about yearly steps (round(years) of them), the observed workforce,
slack, GDP per capita and other sources linear between the ends, the interval's points
spread evenly and its jobs per point kept. Each step reads the slack the steps before it
left, moves the applying share as the script's yearly pulse does
(econ_growth_sim.eased_slack_factor; 0 before the first step, as the script's before its
first pulse), and prices the step's points at the GDP part times that share. Where both
paths apply (a shape with constant ratio) they agree; a percent or two otherwise.

`--share-from SERIES` prices the other series' slack-band shapes at SERIES' share at each step as
well (rows `shape@SERIES`). The script reads one slack for the whole owner country, so a slice of it
builds at the owner's share: France's core inside France with its colonies, then the EU, is
`FRA` at `union`'s share. That assumes no migration into the slice; its own share assumes the
owner's labour pools perfectly. The two series must have the same kept dates.

`--others-scale k` multiplies the other construction-cost sources the counterfactual holds
at observed, as if they had been k times as large: each ratio gains (1 + others) /
(1 + k x others). The playthrough ran with two ministries at +5% a level, about 85% of the
others in the 1998 and 2045 saves; #1038 made them +1% a level, which k = 0.32 approximates
(1 - 0.85 x 0.8).

Three points the definitions leave open, decided from the data:

  * Annexed levels weren't bought. In a series with per-state figures (the union), the
    states in the end point's per_state that the start's lacks were annexed in the
    interval, and some of the levels gained came with them. The share of those levels
    in costed level-bound types is taken as the end point's: annexed_costed = annexed
    levels x (the level-bound costed types' levels / every type's levels), and the points
    and gross_jobs are scaled by max(0, 1 - annexed_costed / costed levels gained),
    costed levels gained being sum of max(0, levels gained) over those types.
    points_observed (the queues' own rate) isn't scaled. FRA, GBR and CHI follow fixed
    state sets, so nothing is annexed into them.
  * A level-bound type with no required_construction (company buildings, army and
    naval logistics centres, conscription centres) buys no points, and its levels
    aren't bought with points either, so its jobs don't count in gross_jobs. They are
    reported as `uncosted_jobs`. Late in the game they gain tens of thousands of levels
    an interval, which would otherwise inflate jobs_per_point where the ratios are
    largest.
  * The other sources cancel out of the ratio, whatever the prior, so it is computed as
    (1 + x_raw) / (1 + x_raw') and the `historical` shape gives exactly 1. Where x_raw
    is 0 the script sets no scaling, and a prior left over from an earlier pulse is
    stale: others is taken as 0 there, which the ratio doesn't need either.

THE SHAPES
----------
  historical   the curve the playthrough ran under (HISTORICAL_CURVE: +1000% at GBP 100,
               ruling R37): the baseline, which reproduces the observed history exactly
  current      the mod's curve as its files hold it now: the historical line times the
               share that applies, from its slack band (full at 3% slack, none at 15%,
               moving a third of the way a year); `linear` is the same curve under its
               older name
  capped:c     the historical line held at +c (the slope kept; `capped:1` is #1034's
               +100% cap to within a percent)
  slack:lo:hi[:ease]
               the historical line times a share that applies in full at slack lo or less
               and not at all at hi or more, moving `ease` of the way a year (at once
               without it)
  slope:k      the historical line at k times the steepness
  log, sqrt, world, none
               as econ_growth_sim.cost_mult defines them, on the historical constants

All are priced against the historical baseline. The shapes other than `current` and
`linear` are built on the historical constants, not the mod's, so they carry no slack band
unless they name one (`slack:`).

STATED LIMITS
-------------
Understating a cheaper curve's effect: no compounding (extra levels add GDP, which buys
more construction later); no extra services demand from a bigger economy; maintenance
and retooling, which X also raises, aren't re-priced.
Overstating it: no ceiling on goods demand (many times the late levels would lower
prices and profits, and with them the pool's inflow and construction); population is
held at observed, so no migration into the new jobs; no floor holding the last peasants.
The vacancy figure is an upper bound: no per-project cap or construction-supply limit,
and no wage response.

    econ_construction_counterfactual.py [--series FRA,union,GBR,CHI] [--curves historical,current,none,...]
                                        [--others-scale 0.32] [--share-from union]
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
DEFAULT_SHAPES = ("historical", "current", "capped:1", "capped:2", "slack:0.03:0.15", "slack:0.03:0.2:0.33333",
                  "slope:0.5", "log", "sqrt", "world", "none")
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
    curve under its older name) is `current`, the mod's constants as its files hold them,
    slack band and all. Every other shape is built on the historical constants: a name in
    econ_growth_sim.CURVES (bar "capped" and "linear"), "capped:c" (the historical line held
    at c), "slope:k" (the historical line with max_mult x k), or "slack:lo:hi[:ease]" (the
    historical line with that slack band)."""
    curve = D.HISTORICAL_CURVE
    if shape == "historical":
        return G.Params(curve="linear"), curve
    if shape in ("current", "linear"):
        return G.Params(curve="linear"), current
    if shape.startswith("slack:"):
        parts = shape.split(":")[1:]
        try:
            nums = [float(x) for x in parts]
        except ValueError:
            raise ValueError("shape " + repr(shape) + ": expected slack:<lo>:<hi>[:<ease>] numbers") from None
        if len(nums) not in (2, 3) or not 0.0 <= nums[0] < nums[1] or (len(nums) == 3 and nums[2] <= 0.0):
            raise ValueError("shape " + repr(shape) + ": expected slack:<lo>:<hi>[:<ease>], 0 <= lo < hi, ease > 0")
        return G.Params(curve="linear"), dataclasses.replace(
            curve, slack_full=nums[0], slack_none=nums[1], slack_ease=nums[2] if len(nums) == 3 else None)
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
        raise ValueError("unknown shape " + repr(shape) + "; expected capped:<c>, slope:<k> or slack:<lo>:<hi>[:<ease>]")
    if shape == "capped":
        raise ValueError("the capped shape needs its cap: capped:<c>")
    if shape not in G.CURVES:
        raise ValueError("unknown shape " + repr(shape) + "; expected one of "
                         + ", ".join(OWN_SHAPES + tuple(c for c in G.CURVES if c != "linear"))
                         + ", capped:<c>, slope:<k> or slack:<lo>:<hi>[:<ease>]")
    return G.Params(curve=shape), curve


def x_raw_of(gdppc: float) -> float:
    """X at `gdppc` on the curve the playthrough ran under (D.HISTORICAL_CURVE)."""
    return G.cost_mult(G.Params(curve="linear"), D.HISTORICAL_CURVE, gdppc)


def x_under(shape: str, gdppc: float, current: D.CurveConstants, world_gdppc: float | None) -> float:
    """x_raw': the shape's X at `gdppc` (its GDP part, before any slack share); `current` is
    the mod's constants as read from its files."""
    p, c = _shape(shape, current)
    return G.cost_mult(p, c, gdppc, world_gdppc)


def has_slack_band(shape: str, current: D.CurveConstants) -> bool:
    """Whether the shape's X follows the slack (the feedback path), so it has no ratio of its own."""
    return _shape(shape, current)[1].has_slack_band


def others_of(x_raw: float, x_adj: float) -> float:
    """The other goods_input_construction_mult sources the script folds into x_adj.

    The script sets x_adj = x_raw x (1 + others), so others = x_adj / x_raw - 1. With
    x_raw 0 the script sets no scaling and a prior is stale: others is 0 (no cost)."""
    return x_adj / x_raw - 1.0 if x_raw > 0 else 0.0


def x_adj_under(shape: str, gdppc: float, x_adj: float | None, numbers, world_gdppc: float | None) -> float:
    """x_adj': what the script would set under the shape, x_raw' x (1 + others), with the
    same other sources. `x_adj` None means the script hadn't set one, so it is x_raw."""
    x_raw = x_raw_of(gdppc)
    others = others_of(x_raw, x_raw if x_adj is None else x_adj)
    return x_under(shape, gdppc, numbers.curve, world_gdppc) * (1.0 + others)


def shape_ratio(shape: str, gdppc: float, x_adj: float | None, numbers, world_gdppc: float | None) -> float:
    """How many times the points the same money buys under `shape`: the point's whole
    goods_input_construction_mult now over under the shape,
    (1 + x_adj + others) / (1 + x_adj' + others) = (1 + x_raw)(1 + others) / ((1 + x_raw')(1 + others)).

    The other sources cancel, so this is (1 + x_raw) / (1 + x_raw') whatever `x_adj` is
    (exactly 1 for the historical shape). With x_raw 0 a prior is stale and others is 0,
    which gives the same form. `x_adj` is kept for the signature's callers. A shape with a
    slack band has no ratio at a GDP per capita alone: it raises ValueError."""
    if has_slack_band(shape, numbers.curve):
        raise ValueError("shape " + repr(shape) + " follows the slack: it has a path, not a ratio")
    x_raw = x_raw_of(gdppc)
    x_new = x_under(shape, gdppc, numbers.curve, world_gdppc)
    return (1.0 + x_raw) / (1.0 + x_new)


def world_gdppc_at(world: list[dict], date: str) -> float | None:
    """The world's GDP per head at `date`, linear between the dataset's world points and
    flat past either end; None with no usable point."""
    return _world_at_year(world, S.point_year(date))


def _world_at_year(world: list[dict], year: float) -> float | None:
    pts = [(S.point_year(w["date"]), w["gdp"] / w["population"]) for w in world if w["population"] > 0]
    return S._linear(pts, year)


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
    bought_share: float = 1.0       # the share of the costed levels gained that points bought (not annexed)


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
        points = gross = uncosted = costed_gained = costed_levels = 0.0
        for btype, info in after.items():
            if sector_of(btype) not in G.LEVEL_BOUND:
                continue
            cost = cost_of(btype) or 0.0
            if cost > 0:
                costed_levels += info["levels"]
            gained = info["levels"] - before.get(btype, {}).get("levels", 0.0)
            if gained <= 0:
                continue
            staff = info["employees"] / info["staffing"] if info["staffing"] > 0 else 0.0
            if cost > 0:
                points += gained * cost
                gross += gained * staff
                costed_gained += gained
            else:
                uncosted += gained * staff
        # Annexed levels weren't bought: take their costed share out of the levels gained.
        new_states = set(b["per_state"]) - set(a["per_state"]) if "per_state" in a and "per_state" in b else set()
        annexed = float(sum(b["per_state"][s][4] for s in new_states))
        all_levels = sum(info["levels"] for info in after.values())
        costed_share = costed_levels / all_levels if all_levels > 0 else 0.0
        bought = max(0.0, 1.0 - annexed * costed_share / costed_gained) if costed_gained > 0 else 1.0
        points *= bought
        gross *= bought

        def employees(buildings: dict) -> float:
            return sum(i["employees"] for t, i in buildings.items() if sector_of(t) in G.LEVEL_BOUND)

        years = S.point_year(b["date"]) - S.point_year(a["date"])
        observed = (sum(a["owner"]["points_weekly"].values()) + sum(b["owner"]["points_weekly"].values())) / 2
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
            annexed_levels=annexed, bought_share=bought,
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


def others_ratio(others: float, others_scale: float) -> float:
    """(1 + others) / (1 + others_scale x others): how many times the points the same money
    buys with the other sources scaled (1 at others_scale 1)."""
    return (1.0 + others) / max(1.0 + others_scale * others, 1e-9)


def _interval_ratio(iv: Interval, shape: str, numbers, world: list[dict], others_scale: float = 1.0) -> float:
    return (shape_ratio(shape, iv.gdppc_start, iv.x_adj_start, numbers, world_gdppc_at(world, iv.start))
            * others_ratio(iv.others_start, others_scale)
            + shape_ratio(shape, iv.gdppc_end, iv.x_adj_end, numbers, world_gdppc_at(world, iv.end))
            * others_ratio(iv.others_end, others_scale)) / 2.0


def _feedback_extra(iv: Interval, a: dict, b: dict, shape: str, numbers, world: list[dict], others_scale: float,
                    cum: float, factor: float, shares: list[float] | None = None
                    ) -> tuple[float, float, float, list[float]]:
    """One interval of a slack-band shape's yearly path: (extra points, cum, factor, the shares used) after it.
    `a` and `b` are the interval's end slices; `cum` and `factor` carry over from the last. With `shares`
    (another series' shares for the same steps), each step uses those instead of moving its own."""
    p, c = _shape(shape, numbers.curve)
    n = max(1, round(iv.years))
    if shares is not None and len(shares) != n:
        raise ValueError("interval " + iv.start + " to " + iv.end + ": " + str(len(shares)) + " shares for "
                         + str(n) + " steps")
    dt = iv.years / n
    y0 = S.point_year(iv.start)
    extra_points = 0.0
    used: list[float] = []
    for k in range(n):
        t = (k + 0.5) / n

        def lerp(x0: float, x1: float) -> float:
            return x0 + (x1 - x0) * t

        workforce = lerp(a["workforce"], b["workforce"])
        slack = lerp(a["peasants"] + a["unemployed"], b["peasants"] + b["unemployed"])
        gdppc = lerp(iv.gdppc_start, iv.gdppc_end)
        others = lerp(iv.others_start, iv.others_end)
        slack_cf = max(0.0, slack - cum) / workforce if workforce > 0 else 0.0
        factor = G.eased_slack_factor(c, factor, slack_cf, dt) if shares is None else shares[k]
        used.append(factor)
        x_new = G.cost_mult(p, c, gdppc, _world_at_year(world, y0 + iv.years * t)) * factor
        ratio = (1.0 + x_raw_of(gdppc)) / (1.0 + x_new) * others_ratio(others, others_scale)
        extra = iv.points / n * (ratio - 1.0)
        extra_points += extra
        cum += extra * iv.jobs_per_point
    return extra_points, cum, factor, used


@dataclass(frozen=True)
class Path:
    rows: list[Row]
    extra_points: float
    points: float
    shares: tuple[tuple[float, ...], ...] = ()      # a slack-band shape's share at each yearly step, by interval


def _paths(series: dict, md, shape: str, world: list[dict], cost_of, sector_of,
           others_scale: float = 1.0, share_from: dict | None = None) -> Path:
    """The path under `shape`. With `share_from` (another series, with the same kept dates), a slack-band
    shape takes that series' share at each step instead of moving its own: the script reads one slack for
    the whole owner country, so a slice of it (France's core) builds at the owner's share."""
    feedback = has_slack_band(shape, md.numbers.curve)  # an unknown shape raises before any arithmetic
    ivs = intervals(series, md, cost_of, sector_of)
    source: tuple[tuple[float, ...], ...] | None = None
    if feedback and share_from is not None:
        source_ivs = intervals(share_from, md, cost_of, sector_of)
        if [(iv.start, iv.end) for iv in source_ivs] != [(iv.start, iv.end) for iv in ivs]:
            raise ValueError("--share-from: the series' kept dates differ, so their steps don't line up")
        source = _paths(share_from, md, shape, world, cost_of, sector_of, others_scale).shares
    by_date = {pt["date"]: pt for pt in kept_points(series["points"])}
    rows: list[Row] = []
    shares: list[tuple[float, ...]] = []
    cum = extra_points = factor = 0.0
    for i, iv in enumerate(ivs):
        if feedback:
            extra, cum, factor, used = _feedback_extra(
                iv, by_date[iv.start]["slice"], by_date[iv.end]["slice"], shape, md.numbers, world, others_scale,
                cum, factor, None if source is None else list(source[i]))
            shares.append(tuple(used))
            extra_points += extra
        else:
            extra = iv.points * (_interval_ratio(iv, shape, md.numbers, world, others_scale) - 1.0)
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
    return Path(rows, extra_points, sum(iv.points for iv in ivs), tuple(shares))


def counterfactual(series: dict, md, shape: str, world: list[dict],
                   cost_of: CostOf | None = None, sector_of: SectorOf | None = None,
                   others_scale: float = 1.0, share_from: dict | None = None) -> list[Row]:
    """The slack path under `shape`: one Row per kept point after the first."""
    return _paths(series, md, shape, world, cost_of, sector_of, others_scale, share_from).rows


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
              cost_of: CostOf | None = None, sector_of: SectorOf | None = None,
              others_scale: float = 1.0, share_from: dict | None = None, label: str | None = None) -> Summary:
    path = _paths(series, md, shape, world, cost_of, sector_of, others_scale, share_from)
    rows, extra, total = path.rows, path.extra_points, path.points
    near = [_nearest(rows, y) for y in SUMMARY_YEARS]
    return Summary(
        series=series_name, shape=shape if label is None else label,
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
        " | net jobs change | gdppc | x_raw | x_adj | others | annexed levels | bought share |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---:|---:|",
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
            _num(iv.annexed_levels), format(iv.bought_share, ".2f"),
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
                    + ", capped:<c>, slope:<k>, slack:<lo>:<hi>[:<ease>]; linear is current (default %(default)s)")
    ap.add_argument("--share-from", default=None, metavar="SERIES",
                    help="also price each other series' slack-band shapes at this series' share (rows marked"
                    " shape@SERIES): the script reads the owner country's slack, so a slice such as FRA builds at"
                    " the owner's share (union). Meaningful only for slices of SERIES: choose them with --series")
    ap.add_argument("--others-scale", type=float, default=1.0,
                    help="scale the other construction-cost sources held at observed (0.32 ~ the ministries at"
                    " +1%% a level, #1038; default %(default)s)")
    args = ap.parse_args(argv)
    names = [s for s in args.series.split(",") if s]
    shapes = [s for s in args.curves.split(",") if s]
    if not names or not shapes:
        print("error: --series and --curves each need at least one name", file=sys.stderr)
        return 2
    if args.others_scale < 0:
        print("error: --others-scale must be 0 or more", file=sys.stderr)
        return 2
    probe = D.CurveConstants(1.0, 1.0, 2.0, 1.0)      # a syntax check only: no figure here is the mod's
    for shape in shapes:
        try:
            _shape(shape, probe)
        except ValueError as exc:
            print("error: " + str(exc), file=sys.stderr)
            return 2
    dataset = S.load_dataset()
    unknown = [n for n in names + ([args.share_from] if args.share_from else []) if n not in dataset["series"]]
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
    k = args.others_scale
    out += ["## Summary", ""]
    if k != 1.0:
        out += ["Other construction-cost sources scaled by " + format(k, "g") + ".", ""]
    src_name = args.share_from
    source = dataset["series"][src_name] if src_name else None

    def borrowed(name: str, shape: str) -> bool:
        return source is not None and name != src_name and has_slack_band(shape, md.numbers.curve)

    summaries = []
    for name in names:
        for shape in shapes:
            summaries.append(summarize(name, dataset["series"][name], md, shape, world, cost_of, sector_of, k))
            if borrowed(name, shape):
                summaries.append(summarize(name, dataset["series"][name], md, shape, world, cost_of, sector_of, k,
                                           share_from=source, label=shape + "@" + src_name))
    out += _summary_table(summaries)
    if "FRA" in names:
        fra = dataset["series"]["FRA"]
        paths = {}
        for shape in shapes:
            paths[shape] = counterfactual(fra, md, shape, world, cost_of, sector_of, k)
            if borrowed("FRA", shape):
                paths[shape + "@" + src_name] = counterfactual(fra, md, shape, world, cost_of, sector_of, k,
                                                               share_from=source)
        out += ["## FRA slack path", "", *_path_table(paths)]
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
