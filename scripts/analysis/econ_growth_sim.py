"""Economy growth sim (issue #1034): parameters, construction-cost curve, point price.

WHY THIS EXISTS
---------------
Playthrough saves show GDP growth stalling once a country is rich. The sim models
the loop that produces it -- investment buys construction points, points become
building levels, levels need workers, wages and automation follow -- so a lever
(the cost curve, the project cap, automation costs) can be swept before any script
changes. Design: docs/superpowers/specs/2026-10-17-economy-growth-sim-design.md.

This module holds the pieces every later stage reads:

  Params          every tunable, with the defaults the design calls for. A sweep
                  overrides fields by name (`dataclasses.replace`).
  cost_mult       X, the construction-cost multiplier at a GDP per capita, in the
                  mod's shape (linear) and five alternatives to compare against.
  point_price     what one construction point costs, from X (spec 4.1).
  points_bought   points a year's spend buys, and whether the per-project cap
                  limited it.

Every mod number arrives as an argument (`econ_sim_data.CurveConstants`, a base
price read from the goods data); nothing here is a copy of a script value.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Direct CLI execution starts with scripts/analysis on sys.path.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from scripts.analysis import econ_sim_data as D  # noqa: E402

CURVES = ("linear", "capped", "log", "sqrt", "world", "none")


@dataclass
class Params:
    # --- construction cost curve -------------------------------------------
    curve: str = "linear"                       # one of CURVES
    curve_cap: float | None = None              # the "capped" curve's ceiling in place of max_mult
    other_construction_mult: float = 0.0        # cost modifiers besides X (laws, techs, institutions)
    construction_good_price: float = 0.93       # market price of the construction good / its base price

    # --- investment --------------------------------------------------------
    private_invest_share: float = 0.13          # of GDP
    gov_invest_share: float = 0.05              # of GDP
    queue_per_state: float = 1.0                # projects the queue runs at once, a state

    # --- labour ------------------------------------------------------------
    fill_rate: float = 0.5                      # share of a vacancy gap filled a year
    wage_floor: float = 0.05                    # GBP a worker a week
    wage_step: float = 1.0                      # wage response to a vacancy gap
    wage_decay: float = 0.2                     # wage response to slack
    vacancy_target: float = 0.02
    slack_target: float = 0.03
    subsistence_income: float = 0.02            # GBP a head a week, peasants
    payback_years: float = 10.0                 # a building must repay its cost within this

    # --- output ------------------------------------------------------------
    price_level: float = 1.0
    services_jobs_per_gdp: float = 0.0
    demand_gdp_ratio: float = 0.3

    # --- population --------------------------------------------------------
    g_max: float = 0.025
    g_min: float = -0.005
    g_slope: float = 0.004
    workforce_share: float = 0.5

    # --- diagnostics -------------------------------------------------------
    mode1_slack: float = 0.01
    mode2_slack: float = 0.10
    rich_gdppc: float = 5.0
    labour_bind_vacancy: float = 0.05

    # --- later stages (the run loop and the scenario builder read these) ----
    return_rate: float = 0.1
    automation_lag_years: float | None = None   # when set, overrides the scenario's lag

    # --- mod-side levers (spec 8): multipliers on what econ_sim_data reads, ----
    # all neutral by default.
    cost_points_mult: float = 1.0               # scales a sector's cost points
    project_cap_mult: float = 1.0               # scales the per-project cap
    construction_labour_mult: float = 1.0       # scales workers per point
    late_employment_mult: float = 1.0           # scales employment of base and automation PMs of era 8+
    eos_cap_mult: float = 1.0                   # scales the economy-of-scale cap
    maintenance_mult: float = 1.0               # scales the maintenance rate
    retool_charge_mult: float = 1.0             # scales the retooling charge
    era_shift_years: float = 0.0                # evaluates era_at(year - era_shift_years)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _fraction(shape: str, x: float, lo: float, hi: float) -> float:
    """Where `x` sits between `lo` (0) and `hi` (1) along `shape`, clamped to [0, 1].

    A span that is not positive (a mod that sets floor == ceiling) is a step at `hi`.
    """
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    if shape == "linear":
        return _clamp((x - lo) / (hi - lo), 0.0, 1.0)
    if shape == "sqrt":
        return 0.0 if x <= lo else _clamp(math.sqrt((x - lo) / (hi - lo)), 0.0, 1.0)
    if shape == "log":
        if lo <= 0:
            raise ValueError("the log curve needs a positive floor, got " + repr(lo))
        return 0.0 if x <= lo else _clamp(math.log(x / lo) / math.log(hi / lo), 0.0, 1.0)
    raise ValueError("unknown curve shape " + repr(shape))


def cost_mult(p: Params, c: D.CurveConstants, gdppc: float, world_gdppc: float | None = None) -> float:
    """X: the construction-cost multiplier at `gdppc` (GBP a head).

    With f = reference * floor_ratio and g = reference * ceiling_ratio:
      linear  clamp((gdppc - f) / (g - f) * max_mult, 0, max_mult)   (the mod's curve)
      capped  the linear line, held flat once it reaches `p.curve_cap` (the slope
              stays max_mult / (g - f); only the ceiling it clamps to changes)
      log     max_mult * ln(gdppc / f) / ln(g / f), 0 at or below f
      sqrt    max_mult * sqrt((gdppc - f) / (g - f))
      world   linear on gdppc / world_gdppc against floor_ratio and ceiling_ratio,
              in place of gdppc / reference; 0 with no world figure
      none    0
    """
    if p.curve not in CURVES:
        raise ValueError("unknown curve " + repr(p.curve) + "; expected one of " + ", ".join(CURVES))
    if p.curve == "none":
        return 0.0
    ceiling = c.max_mult
    if p.curve == "capped":
        if p.curve_cap is None:
            raise ValueError("the capped curve needs curve_cap")
        ceiling = p.curve_cap
    ceiling = max(0.0, ceiling)
    if p.curve == "world":
        if world_gdppc is None or world_gdppc <= 0:
            return 0.0
        x, lo, hi = gdppc / world_gdppc, c.floor_ratio, c.ceiling_ratio
    else:
        x, lo, hi = gdppc, c.reference * c.floor_ratio, c.reference * c.ceiling_ratio
    shape = "linear" if p.curve in ("capped", "world") else p.curve
    return min(ceiling, c.max_mult * _fraction(shape, x, lo, hi))


def point_price(p: Params, base_price: float, x: float) -> float:
    """GBP per construction point: the construction good's base price, its market
    price level, the cost multiplier X, and any other cost modifiers (spec 4.1)."""
    return base_price * p.construction_good_price * (1.0 + x) * (1.0 + p.other_construction_mult)


def points_bought(spend_per_year: float, price: float, cap_per_year: float) -> tuple[float, bool]:
    """(points, cap_bound): what `spend_per_year` buys at `price` a point, limited
    to `cap_per_year`; cap_bound is True when the cap, not the money, set the figure.

    A price of zero or less is free points (the cap still applies); no spend buys nothing.
    """
    cap = max(0.0, cap_per_year)
    if spend_per_year <= 0:
        return 0.0, False
    wanted = spend_per_year / price if price > 0 else math.inf
    if wanted > cap:
        return cap, True
    return wanted, False
