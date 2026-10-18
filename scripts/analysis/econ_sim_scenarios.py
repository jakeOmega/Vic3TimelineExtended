"""Country scenarios for the economy growth sim (issue #1034).

WHY THIS EXISTS
---------------
`econ_growth_sim.step` advances one country a year. Everything it needs to know
about that country -- the people and economy it starts with, its territory, how
the saves say it calibrates against the ladders, and the schedules that run
outside the model (era arrival, land law, welfare, investment allocation, the
world's GDP per capita, annexations) -- is a `Scenario`.

This module holds the `Scenario` dataclass and `scenario`, which builds the four
country types (and the whole-union check) out of the calibration dataset,
`econ_series_c480d386.json` (docs/systems/economy_growth_sim.md § Data):

  player_rich   series FRA: France's 1867 states, the player's own
  player_poor   series CHI's 1867 start, with player_rich's era pace and allocation
  ai_rich       series GBR: Britain's 1867 states, AI-held, to 1990
  ai_poor       series CHI: China's 1867 states, AI-held
  player_union  series union: the player's own states at each save, annexations as events

Schedules are tuples of (year, value) points, the year fractional (a save's date):

  era_at, world_gdppc_at    linear between points, held flat past either end
  land_floor_at, welfare_at,
  alloc_at                  piecewise constant: each point's value holds from its
                            year until the next point (the first point's value
                            also holds before it)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Direct CLI execution starts with scripts/analysis on sys.path.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from scripts.analysis import econ_growth_sim as G  # noqa: E402
from scripts.analysis import econ_sim_data as D  # noqa: E402

DATASET = Path(__file__).with_name("econ_series_c480d386.json")
SCENARIOS = ("player_rich", "player_poor", "ai_rich", "ai_poor", "player_union")


def _by_year(points):
    return sorted(points, key=lambda point: point[0])


def _linear(points, year: float):
    """Linear interpolation over (year, value) points, flat past either end; None with no points."""
    pts = _by_year(points)
    if not pts:
        return None
    if year <= pts[0][0]:
        return float(pts[0][1])
    for (y0, v0), (y1, v1) in zip(pts, pts[1:]):
        if year <= y1:
            if y1 == y0:
                return float(v1)
            return v0 + (v1 - v0) * (year - y0) / (y1 - y0)
    return float(pts[-1][1])


def _step(points, year: float, default):
    """The value of the last point at or before `year` (the first point's before it)."""
    pts = _by_year(points)
    if not pts:
        return default
    value = pts[0][1]
    for y, v in pts:
        if y > year:
            break
        value = v
    return value


@dataclass(frozen=True, kw_only=True)
class Scenario:
    """One country's start and schedules. Money is in GBP, nominal unless noted."""

    # --- identity and timing ------------------------------------------------
    name: str
    kind: str                                   # "player" | "ai"
    series: str                                 # dataset series: "FRA", "GBR", "CHI", "union"; "" for toys
    start_year: int
    end_year: int

    # --- people ---------------------------------------------------------------
    population: float
    peasants: float                             # the land floor is a share of these (the start's)
    unemployed: float
    subsistence_capacity: float                 # peasant slots arable land holds

    # --- the start economy ----------------------------------------------------
    employed_level: float                       # employees of level-bound sectors
    employed_demand: float                      # employees of services and construction
    gdp: float                                  # annual
    points_week: float                          # construction points a week
    wage_start: float | None = None             # GBP a worker a week, nominal; None starts at the wage floor

    # --- territory and stock --------------------------------------------------
    n_states: int
    levels: dict[str, float]                    # building levels by sector

    # --- per-sector calibration (observed / ladder; 1.0 for a sector with no buildings at the start) --
    k_emp: dict[str, float]
    k_va: dict[str, float]
    cost_points: dict[str, float]               # construction points a level

    # --- schedules (years may be fractional: a save's date) --------------------
    era_points: tuple[tuple[float, float], ...]
    land_floor: tuple[tuple[float, float], ...]  # share of the start peasants hiring can't go below
    welfare: tuple[tuple[float, float], ...]    # welfare per unemployed worker, GBP a week, nominal
    alloc: tuple[tuple[float, dict[str, float]], ...]
    world_gdppc: tuple[tuple[float, float], ...]

    # --- behaviour and events -------------------------------------------------
    automation_lag_years: float
    rich_from_year: int | None
    annexations: tuple[tuple[int, dict], ...]   # (year, {population, peasants, unemployed, levels,
                                                #         subsistence_capacity})

    def era_at(self, year: float) -> float:
        era = _linear(self.era_points, year)
        return 0.0 if era is None else era

    def land_floor_at(self, year: float) -> float:
        return float(_step(self.land_floor, year, 0.0))

    def welfare_at(self, year: float) -> float:
        return float(_step(self.welfare, year, 0.0))

    def alloc_at(self, year: float) -> dict[str, float]:
        return dict(_step(self.alloc, year, {}))

    def world_gdppc_at(self, year: float) -> float | None:
        return _linear(self.world_gdppc, year)


# --------------------------------------------------------------------------
# Building the scenarios from the dataset
# --------------------------------------------------------------------------

END_YEAR = 2050                                 # a series that runs to the last save runs to here
RICH_FROM_YEAR = 1920                           # rich_from_year of the rich types (spec 2: the turn by 1920)
AI_LAG_YEARS = 5.0                              # the AI's automation lag; players take a tier at once
ERA_TECH_SHARE = 0.5                            # an era is reached with half its technologies
SUBSISTENCE_HEADROOM = 1.5                      # subsistence capacity, over the peasants it holds
FLOOR_LAWS = ("law_serfdom", "law_manorialism")  # land laws that keep an employment floor (spec 4.2)
FLOOR_SHARE = 0.5                               # ... of 0.5
MIN_ALLOC_SPAN = 1.0                            # years: a shorter interval merges into the next

# name -> (dataset series, kind, rich_from_year, the scenario that lends its era pace and allocation)
SPECS = {
    "player_rich": ("FRA", "player", RICH_FROM_YEAR, None),
    "player_poor": ("CHI", "player", None, "player_rich"),
    "ai_rich": ("GBR", "ai", RICH_FROM_YEAR, None),
    "ai_poor": ("CHI", "ai", None, None),
    "player_union": ("union", "player", RICH_FROM_YEAR, "player_rich"),
}


def load_dataset(path: Path | str = DATASET) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def point_year(date: str) -> float:
    """A save date ("1867.8.16") as a fractional year (1867.62); months count as twelfths."""
    y, m, d = (int(x) for x in date.split(".")[:3])
    return y + (m - 1 + (d - 1) / 31.0) / 12.0


def era_reached(techs, tech_era: dict[str, int]) -> int:
    """The highest era e for which `techs` hold at least half of the era-e technologies
    in `tech_era`; 0 if none. A technology `tech_era` doesn't know is ignored."""
    held = set(techs)
    by_era: dict[int, list[str]] = {}
    for tech, era in tech_era.items():
        by_era.setdefault(era, []).append(tech)
    reached = 0
    for era, era_techs in by_era.items():
        if era > reached and sum(1 for t in era_techs if t in held) >= ERA_TECH_SHARE * len(era_techs):
            reached = era
    return reached


def _sector_totals(md: D.ModData, slice_: dict) -> dict[str, dict[str, float]]:
    """Per sector (`econ_sim_data.sector_of`): levels, staffing, employees and weekly VA
    (goods_sales - goods_cost, GBP) of the slice's buildings."""
    out: dict[str, dict[str, float]] = {}
    for btype, info in slice_["buildings_by_type"].items():
        tot = out.setdefault(D.sector_of(md.ms, btype), {"levels": 0.0, "staffing": 0.0, "employees": 0.0, "va": 0.0})
        tot["levels"] += info["levels"]
        tot["staffing"] += info["staffing"]
        tot["employees"] += info["employees"]
        tot["va"] += info["goods_sales"] - info["goods_cost"]
    return out


def sector_calibration(slice_: dict, md: D.ModData, era: float) -> tuple[dict[str, float], dict[str, float]]:
    """(k_emp, k_va) for each level-bound sector the slice staffs.

    k_emp is the observed employees a staffed level (sum of employees / sum of staffing)
    over the ladder's base PM at `era`; k_va the observed VA a staffed level, goods_sales -
    goods_cost, over that PM's VA. Building money in the dataset is weekly (checked against
    the 1949 text save: a construction sector's goods_sales is its week's output at market
    price), so there is no / 52. `other` has no ladder: its k_emp and k_va are the observed
    figures themselves.

    A ladder sector whose observed VA (or ladder VA) is 0 or less gets k_va 1.0, the
    Scenario's "no information" value. A negative k_va would multiply a ladder VA that
    grows with the era, so the sector's loss would grow with technology. FRA and GBR
    infrastructure in 1867 is such a case: trade centres earn trade revenue, not goods
    sales, and ports and railways sold transport below their input costs.
    """
    k_emp: dict[str, float] = {}
    k_va: dict[str, float] = {}
    for s, tot in _sector_totals(md, slice_).items():
        if s not in G.LEVEL_BOUND or tot["staffing"] <= 0:
            continue
        emp, va = tot["employees"] / tot["staffing"], tot["va"] / tot["staffing"]
        if s == "other":
            k_emp[s], k_va[s] = emp, va
            continue
        base = D.base_at(md.ladders[s], era)
        k_emp[s] = emp / base.employment if base.employment > 0 else 1.0
        k_va[s] = va / base.va if va > 0 and base.va > 0 else 1.0
    return k_emp, k_va


def _type_cost(md: D.ModData, btype: str) -> float | None:
    """Construction points a level of `btype` (its required_construction tier); None for a
    type that is never queued or that the Buildings data doesn't know."""
    buildings = md.ms.get_data("Buildings")
    if btype not in buildings:
        return None
    tier = D.val(D.val(buildings[btype]).get("required_construction"))
    if tier is None:
        return None
    if tier not in md.numbers.cost_tiers:
        raise KeyError("cost tier: " + str(tier) + " (required_construction of " + btype + ")")
    return md.numbers.cost_tiers[tier]


def realised_alloc(points: list[dict], md: D.ModData) -> tuple[tuple[float, dict[str, float]], ...]:
    """Where construction went, per point: each sector's share of the points the next
    interval's new levels cost.

    A sector's points over an interval are the sum over its building types of
    max(0, levels gained) x the type's required_construction tier. Types with no cost (urban
    centres grow by urbanization; ownership buildings are never queued) don't count. Services
    and construction-sector types do: they took points in the game, and the step drops their
    shares, as it builds neither. A point under MIN_ALLOC_SPAN years after the last kept one
    is skipped, so its interval merges into the next. An interval with no construction keeps
    the previous one's shares; the last point repeats the last interval's.

    This stands in for the brief's `investment_by_type`, which is the investment pool's
    inflow by the building that paid it (company headquarters, financial districts, manor
    houses lead it), not where the pool's money was spent.
    """
    kept: list[dict] = []
    for pt in points:
        if not kept or point_year(pt["date"]) - point_year(kept[-1]["date"]) >= MIN_ALLOC_SPAN:
            kept.append(pt)
    out: list[tuple[float, dict[str, float]]] = []
    shares: dict[str, float] = {}
    for a, b in zip(kept, kept[1:]):
        before, after = a["slice"]["buildings_by_type"], b["slice"]["buildings_by_type"]
        spent: dict[str, float] = {}
        for btype, info in after.items():
            gained = info["levels"] - before.get(btype, {}).get("levels", 0.0)
            cost = _type_cost(md, btype) if gained > 0 else None
            if cost:
                s = D.sector_of(md.ms, btype)
                spent[s] = spent.get(s, 0.0) + gained * cost
        total = sum(spent.values())
        if total > 0:
            shares = {s: v / total for s, v in sorted(spent.items())}
        out.append((point_year(a["date"]), dict(shares)))
    if kept:
        out.append((point_year(kept[-1]["date"]), dict(shares)))
    return tuple(out)


def _cost_points(md: D.ModData, slice_: dict) -> dict[str, float]:
    """`sector_cost_points` over the slice's buildings, for the level-bound sectors; one it
    leaves out takes its representative building's own required_construction tier (R14).
    `other` has no representative building, so it keeps only what the slice gives."""
    observed = D.sector_cost_points(md.ms, md.numbers, slice_["buildings_by_type"])
    out = {s: v for s, v in observed.items() if s in G.LEVEL_BOUND}
    for s in G.LEVEL_BOUND:
        if s in out or s not in D.SECTOR_BUILDINGS:
            continue
        building = D.SECTOR_BUILDINGS[s][0]
        cost = _type_cost(md, building)
        if cost is None:
            raise KeyError("Buildings " + building + ": required_construction (sector " + s + ")")
        out[s] = cost
    return out


def _annexations(points: list[dict], md: D.ModData) -> tuple[tuple[int, dict], ...]:
    """The union's annexations: per point, the states in its per_state that weren't in the
    previous point's, added in that point's year. Their levels are spread over the sectors
    in the union's level shares at that point; the event also adds subsistence capacity,
    SUBSISTENCE_HEADROOM x the annexed peasants (R23). States the union loses aren't
    modelled (four in 1954, 0.7% of its people; one each in 2023 and 2033)."""
    events = []
    for a, b in zip(points, points[1:]):
        new = sorted(set(b["per_state"]) - set(a["per_state"]))
        if not new:
            continue
        rows = [b["per_state"][state] for state in new]
        population, _workforce, peasants, unemployed, levels = (sum(r[i] for r in rows) for i in range(5))
        totals = _sector_totals(md, b["slice"])
        all_levels = sum(t["levels"] for t in totals.values())
        spread = {s: levels * t["levels"] / all_levels for s, t in totals.items()} if all_levels > 0 else {}
        events.append((int(b["date"][:4]), {
            "population": float(population),
            "peasants": float(peasants),
            "unemployed": float(unemployed),
            "levels": spread,
            "subsistence_capacity": SUBSISTENCE_HEADROOM * peasants,
        }))
    return tuple(events)


def scenario(name: str, dataset: dict, md: D.ModData) -> Scenario:
    """One of SCENARIOS, built from the dataset (spec 6; plan Task 8).

    Every type starts at its series' first point (1867). The start's people, wage and
    levels are the point's slice; GDP is the owner's GDP per head x the slice's people,
    points a week the owner's (already scaled to the slice). k_emp and k_va calibrate
    against the ladders at the start's era (`sector_calibration`). Cost points come from
    the latest slice of the series that lends the allocation. The schedules are per point:
    era (the owner's technologies, `era_reached`), allocation (`realised_alloc`), land floor
    (0.5 under serfdom or manorialism), welfare a week per unemployed worker, and the world's
    GDP per head. A series that stops before the dataset's last save (GBR, at 1990) ends
    in its last point's year; one that runs to it ends in END_YEAR.
    """
    if name not in SPECS:
        raise KeyError("scenario: " + name + "; expected one of " + ", ".join(SCENARIOS))
    series_name, kind, rich_from, lender = SPECS[name]
    series = dataset["series"][series_name]
    points = series["points"]
    start = points[0]
    slice_, owner = start["slice"], start["owner"]
    tech_era = md.numbers.tech_era

    if lender is None:
        era_points = tuple((point_year(pt["date"]), float(era_reached(pt["owner"]["acquired_techs"], tech_era)))
                           for pt in points)
        alloc = realised_alloc(points, md)
        cost_points = _cost_points(md, points[-1]["slice"])
    else:
        # player_poor builds what the player builds, at the player's pace, so it takes the
        # lender's cost points too. The union is the player's own country (the same owner
        # record as FRA), and its level changes include annexed buildings, so its allocation
        # is FRA's realised one; its own latest slice prices its levels.
        lent = scenario(lender, dataset, md)
        era_points, alloc = lent.era_points, lent.alloc
        cost_points = _cost_points(md, points[-1]["slice"]) if series_name == "union" else lent.cost_points

    # The start calibrates against the PMs the series' own country could use: its own era.
    k_emp, k_va = sector_calibration(slice_, md, era_reached(owner["acquired_techs"], tech_era))
    totals = _sector_totals(md, slice_)
    last_save_year = max(int(pt["date"][:4]) for c in dataset["series"].values() for pt in c["points"])
    own_last_year = int(points[-1]["date"][:4])
    world = tuple((point_year(w["date"]), w["gdp"] / w["population"]) for w in dataset["world"] if w["population"] > 0)

    return Scenario(
        name=name,
        kind=kind,
        series=series_name,
        start_year=int(start["date"][:4]),
        end_year=END_YEAR if own_last_year == last_save_year else own_last_year,
        population=float(slice_["population"]),
        peasants=float(slice_["peasants"]),
        unemployed=float(slice_["unemployed"]),
        subsistence_capacity=SUBSISTENCE_HEADROOM * slice_["peasants"],
        employed_level=sum(t["employees"] for s, t in totals.items() if s in G.LEVEL_BOUND),
        employed_demand=sum(t["employees"] for s, t in totals.items() if s in G.DEMAND_BOUND),
        gdp=owner["gdppc"] * slice_["population"],
        points_week=sum(owner["points_weekly"].values()),
        wage_start=slice_["wage_per_worker"],
        n_states=len(series["core_states"]) if "core_states" in series else len(start["per_state"]),
        levels={s: t["levels"] for s, t in totals.items()},
        k_emp=k_emp,
        k_va=k_va,
        cost_points=cost_points,
        era_points=era_points,
        land_floor=tuple((point_year(pt["date"]), FLOOR_SHARE if pt["owner"]["land_law"] in FLOOR_LAWS else 0.0)
                         for pt in points),
        welfare=tuple((point_year(pt["date"]), float(pt["slice"]["welfare_per_unemployed"])) for pt in points),
        alloc=alloc,
        world_gdppc=world,
        automation_lag_years=AI_LAG_YEARS if kind == "ai" else 0.0,
        rich_from_year=rich_from,
        annexations=_annexations(points, md) if series_name == "union" else (),
    )
