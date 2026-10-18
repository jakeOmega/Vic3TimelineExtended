"""Country scenarios for the economy growth sim (issue #1034).

WHY THIS EXISTS
---------------
`econ_growth_sim.step` advances one country a year. Everything it needs to know
about that country -- the people and economy it starts with, its territory, how
the saves say it calibrates against the ladders, and the schedules that run
outside the model (era arrival, land law, welfare, investment allocation, the
world's GDP per capita, annexations) -- is a `Scenario`.

This module holds the `Scenario` dataclass. The builders that read the four
country types out of the calibration dataset (`econ_series_c480d386.json`) come
with Task 8 of the plan (docs/superpowers/plans/2026-10-17-economy-growth-sim.md).

Schedules are tuples of (year, value) points:

  era_at, world_gdppc_at    linear between points, held flat past either end
  land_floor_at, welfare_at,
  alloc_at                  piecewise constant: each point's value holds from its
                            year until the next point (the first point's value
                            also holds before it)
"""

from __future__ import annotations

from dataclasses import dataclass


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

    # --- schedules ------------------------------------------------------------
    era_points: tuple[tuple[int, float], ...]
    land_floor: tuple[tuple[int, float], ...]   # share of the start peasants hiring can't go below
    welfare: tuple[tuple[int, float], ...]      # welfare per unemployed worker, GBP a week, nominal
    alloc: tuple[tuple[int, dict[str, float]], ...]
    world_gdppc: tuple[tuple[int, float], ...]

    # --- behaviour and events -------------------------------------------------
    automation_lag_years: float
    rich_from_year: int | None
    annexations: tuple[tuple[int, dict], ...]   # (year, {population, peasants, unemployed, levels})

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
