"""Economy growth sim (issue #1034): parameters, construction-cost curve, point price.

WHY THIS EXISTS
---------------
Playthrough saves show GDP growth stalling once a country is rich. The sim models
the loop that produces it -- investment buys construction points, points become
building levels, levels need workers, wages and automation follow -- so a lever
(the cost curve, the project cap, automation costs) can be swept before any script
changes. Design: docs/superpowers/archive/specs/2026-10-17-economy-growth-sim-design.md.

This module holds:

  Params          every tunable, with the defaults the design calls for. A sweep
                  overrides fields by name (`dataclasses.replace`).
  cost_mult       X, the construction-cost multiplier at a GDP per capita, in the
                  mod's shape (linear) and five alternatives to compare against.
  point_price     what one construction point costs, from X (spec 4.1).
  points_bought   points a year's spend buys, and whether the per-project cap
                  limited it.
  State, step     one country's stocks, and the year that advances them
                  (spec 5.3; the algorithm is spelled out on `step`).
  run             a scenario from its start year to its end year, inclusive, as
                  one YearRecord a year.
  params_for      the calibrated Params of a scenario, from econ_sim_params.json
                  (written by econ_sim_calibrate.py fit).
  classify, turn_year, takeoff_year, first_year_below, Summary, summarize
                  the diagnostics (spec 5.5, 9): each year's mode, the year wages
                  first pass the first automation tier's breakeven, the catch-up
                  measures, and one summary row per run.
  parse_sets, parse_curve, sweep, render_table, main
                  the command line (spec 9): `run` one scenario, `sweep` cost-curve
                  shapes across country types.

Every mod number arrives as an argument (`econ_sim_data.ModData`, a base price
read from the goods data); nothing here is a copy of a script value. The three
labour rules of spec 4.2 (the 0.25 wage margin, the 10% raise to hire, the 30%
subsistence premium) are vanilla defines the snapshot doesn't carry; they are the
named constants below.

USAGE
-----
    PY=.venv/bin/python                         # from the repo root
    $PY scripts/analysis/econ_growth_sim.py run --scenario player_rich --curve capped:0.5 \\
        --set fill_rate=0.3 --end 2062 --csv out.csv
    $PY scripts/analysis/econ_growth_sim.py sweep --scenarios player_rich,ai_poor \\
        --curves linear,capped:0.5,slope:0.5,slope:2,log,sqrt,world,none

Both run on the fitted parameters (econ_sim_params.json), then `--set name=value`, then the
curve. A curve is `linear` (the mod's), `capped:C` (the line held at C), `slope:K` (the line
at K times the mod's steepness), `log`, `sqrt`, `world` or `none`. The mod's line stops at
+100% (#1034), so a cap of 1 or more is `linear` again.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

REPO = Path(__file__).resolve().parents[2]
# Direct CLI execution starts with scripts/analysis on sys.path.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from scripts.analysis import econ_sim_data as D  # noqa: E402

if TYPE_CHECKING:
    from scripts.analysis.econ_sim_scenarios import Scenario

CURVES = ("linear", "capped", "log", "sqrt", "world", "none")

# The calibrated parameters (econ_sim_calibrate.py fit). Two scenarios have no behaviour
# of their own: player_poor is China played by the player, player_union the player's whole
# union, so both behave as player_rich does.
PARAMS = Path(__file__).with_name("econ_sim_params.json")
BEHAVIOUR_FROM = {"player_poor": "player_rich", "player_union": "player_rich"}

# Level-bound sectors: jobs are levels x staff a level. `other` has no ladder.
LEVEL_BOUND = ("farming", "mining", "light", "heavy", "hightech", "infrastructure", "other")
# Demand-bound sectors: jobs follow spending (services: GDP; construction: points).
DEMAND_BOUND = ("services", "construction")
NO_EOS = ("infrastructure",)                    # its building group has no economy of scale (spec 4.3)
LATE_ERA = 8                                    # late_employment_mult reaches PMs of this era and later

# Spec 4.2, vanilla labour rules. vanilla_parsed/ carries neither file, so these are
# copies: game/common/defines/00_defines.txt and game/common/buildings/12_subsistence.txt.
WAGE_SHARE_OF_VA = 0.75                         # 1 - BUILDING_PROFIT_TARGET_TO_RAISE_WAGES (0.25)
HIRE_PREMIUM = 1.1                              # 1 + MIN_RAISE_TO_HIRE (0.10)
RETURN_PREMIUM = 1.3                            # 1 + the subsistence buildings' min_raise_to_hire (0.30):
                                                # the unemployed return once subsistence pays 1.3 x their welfare


@dataclass
class Params:
    # --- construction cost curve -------------------------------------------
    curve: str = "linear"                       # one of CURVES
    curve_cap: float | None = None              # the "capped" curve's ceiling in place of max_mult
    curve_slope: float = 1.0                    # the "linear" curve's max_mult is scaled by this (CLI: slope:k)
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
      linear  clamp((gdppc - f) / (g - f) * max_mult, 0, max_mult)   (the mod's curve);
              `p.curve_slope` scales max_mult, so the same floor and ceiling with a
              steeper or shallower line (the `slope:k` curve; negative counts as 0)
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
    max_mult = c.max_mult * max(0.0, p.curve_slope) if p.curve == "linear" else c.max_mult
    ceiling = max_mult
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
    return min(ceiling, max_mult * _fraction(shape, x, lo, hi))


def slack_target(c: D.CurveConstants, slack: float) -> float:
    """The share of the GDP part that applies at `slack` (peasants + unemployed over the
    workforce): 1 at c.slack_full or less, 0 at c.slack_none or more, a straight line
    between (the script's te_cc_slack_target). 1 when `c` has no slack band."""
    if not c.has_slack_band:
        return 1.0
    span = max(c.slack_none - c.slack_full, 0.001)       # the script's divisor floor
    return _clamp((c.slack_none - slack) / span, 0.0, 1.0)


def eased_slack_factor(c: D.CurveConstants, prev: float, slack: float, years: float = 1.0) -> float:
    """The applying share after `years` (one yearly pulse at 1.0): `prev` moved
    c.slack_ease of the remaining way toward slack_target(c, slack) a year, compounded
    over `years` (1 - (1 - ease)^years, as the script's pulses do; te_cc_slack_factor_eased).
    With no band, 1; with no ease, the target."""
    if not c.has_slack_band:
        return 1.0
    ease = 1.0 if c.slack_ease is None else _clamp(c.slack_ease, 0.0, 1.0)
    step = 1.0 - (1.0 - ease) ** max(0.0, years)
    return _clamp(prev + (slack_target(c, slack) - prev) * step, 0.0, 1.0)


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


# --------------------------------------------------------------------------
# The yearly step
# --------------------------------------------------------------------------


@dataclass
class SectorState:
    levels: float
    auto_tier: int = 0                          # index into the ladder's automation tuple; 0 is "none"
    retool_left: float = 0.0                    # years of retooling still to pay
    ready_since: float | None = None            # AI: the year ready_tier first paid, in an unbroken run
    ready_tier: int | None = None               # AI: the tier it is waiting to switch to


@dataclass
class State:
    """One country's stocks between years. `workforce` is always peasants +
    unemployed + employed_level + employed_demand; `wage` is in base prices
    (nominal / price_level); `gdp` is annual and nominal. `subsistence_capacity`
    starts as the scenario's and grows with annexations (R23)."""

    year: int                                   # the year the next step runs
    population: float
    workforce: float
    peasants: float
    unemployed: float
    employed_level: float
    employed_demand: float
    wage: float
    gdp: float
    points_week: float
    sectors: dict[str, SectorState]
    subsistence_capacity: float
    x: float = 0.0                              # last year's cost multiplier; 0 before the first step
    slack_factor: float = 0.0                   # the share of the GDP part that applies (a slack band only);
                                                # 0 before the first step, as the script's before its first pulse


@dataclass
class YearRecord:
    """One year, as `step` left it.

    People are end-of-year stocks (after population). jobs_level and jobs_demand
    are this year's jobs; vacancies counts the jobs of both kinds left unfilled
    after hiring (the wage step and labour_bound read the level-bound share,
    unfilled level-bound jobs / jobs_level). wage is in base prices (x price_level
    for nominal). gdp, spend and points are a year's totals (points / 52 is a week);
    gdppc is gdp / the population before this year's growth. auto_tiers and levels
    cover every sector the state holds (a demand-bound or `peasants` entry from the
    scenario's levels is carried, never used), and levels include the levels this
    year's points bought. jobs_by_sector is this year's level-bound jobs per sector,
    crews included (R5).
    """

    year: int
    era: float
    population: float
    workforce: float
    peasants: float
    unemployed: float
    employed: float
    jobs_level: float
    jobs_demand: float
    vacancies: float
    wage: float
    gdp: float
    gdppc: float
    x: float
    spend: float
    points: float
    money_bound: bool
    cap_bound: bool
    labour_bound: bool
    auto_tiers: dict[str, int]
    levels: dict[str, float]
    jobs_by_sector: dict[str, float]


def _late(pm: D.PMFigures, p: Params) -> D.PMFigures:
    """`pm` with late_employment_mult applied to its per-level staff (era 8 and up).
    The scaled figure feeds jobs, breakeven and the automation gain alike."""
    if pm.era >= LATE_ERA and p.late_employment_mult != 1.0:
        return dataclasses.replace(pm, employment=pm.employment * p.late_employment_mult)
    return pm


def _saving(tier: D.PMFigures, wage: float, k_emp: float, k_va: float) -> float:
    """GBP a level a week `tier` saves against "none" at `wage` (base prices): the
    wages of the jobs it cuts, less the goods it adds. Calibrated like the sector's
    staff and VA. A tier that cuts no jobs can still save goods. A tier's fixed crew
    (a building's, not a level's) isn't counted (R25)."""
    return wage * k_emp * (-tier.employment) - k_va * (tier.goods_in - tier.goods_out)


def _cap_with_steps(base: float, steps: tuple[tuple[int, str, float], ...], era: float) -> float:
    return base + sum(add for step_era, _tech, add in steps if step_era <= era)


def _ladder(md: D.ModData, sector: str) -> D.Ladder:
    if sector not in md.ladders:
        raise KeyError("ladders: " + sector)
    return md.ladders[sector]


def initial_state(sc: Scenario, md: D.ModData, p: Params) -> State:
    """People and the start economy straight from the scenario; every sector at tier 0.

    The workforce starts as the scenario's people (peasants + unemployed + employed);
    the first step's population stage moves it to population x workforce_share.
    """
    sectors = {s: SectorState(float(n)) for s, n in sc.levels.items()}
    for s in sc.cost_points:                    # sectors that can be built get a state to build into
        if s in LEVEL_BOUND:
            sectors.setdefault(s, SectorState(0.0))
    for s in sectors:
        if s in LEVEL_BOUND and s != "other":
            _ladder(md, s)
    wage = p.wage_floor if sc.wage_start is None else sc.wage_start / p.price_level
    return State(
        year=sc.start_year,
        population=float(sc.population),
        workforce=sc.peasants + sc.unemployed + sc.employed_level + sc.employed_demand,
        peasants=float(sc.peasants),
        unemployed=float(sc.unemployed),
        employed_level=float(sc.employed_level),
        employed_demand=float(sc.employed_demand),
        wage=wage,
        gdp=float(sc.gdp),
        points_week=float(sc.points_week),
        sectors=sectors,
        subsistence_capacity=float(sc.subsistence_capacity),
    )


def step(state: State, sc: Scenario, md: D.ModData, p: Params) -> YearRecord:
    """Advance `state` one year and return the year's record.

    The thirteen stages, in order (spec 5.3; numbers as in the plan's Task 6):

     1 annexations   this year's events add population, peasants, unemployed, levels
                     and subsistence capacity (R23)
     2 era           sc.era_at(year - era_shift_years)
     3 per sector    staff, crew and VA a level from the base PM at the era plus the
                     sector's current automation tier. A PM group's tiers are
                     alternatives (each tier's figures are its whole change from
                     "none"), so only the current one counts. VA a level is net of
                     maintenance at last year's X. `other` is k_emp staff and k_va VA.
     4 economy of scale  1% a level past one a state, up to the era's cap
     5 jobs          level-bound: levels x staff + crews (a building a level, at most
                     one a state); services from last year's GDP; construction from
                     last year's points a week x workers a point
     6 shedding      jobs gone take their workers to the unemployed
     7 hiring        fill_rate of the open jobs, from the unemployed, then peasants
                     above the land floor while the wage beats subsistence by 10%
     8 GDP           staffed levels x VA x (1 + EoS), less retooling payments; X, times
                     the applying share eased toward the slack after hiring when the
                     curve has a slack band
     9 construction  investment buys points (point price at X, the per-project cap);
                     new levels arrive at the end of the year by allocation share
    10 automation    a best response: the tier that saves most at this year's wage,
                     when its saving over the tier in use, over the payback horizon,
                     beats the retooling charge; tiers can be skipped or undone; the
                     AI waits its lag; one switch a year (R25)
    11 wages         rise with vacancies (up to 0.75 of VA a worker), else drift to
                     the floor with slack
    12 population    growth falls with GDP per capita; the workforce follows; the
                     unemployed return to subsistence when its income is at least
                     1.3 x their welfare (subsistence's min_raise_to_hire)
    13 flags         labour-, cap- or money-bound
    """
    nums = md.numbers
    year = state.year
    sectors = state.sectors

    # 1. Annexations.
    for event_year, event in sc.annexations:
        if event_year != year:
            continue
        # The event's employed aren't added: its levels' jobs hire from the workforce
        # the population stage reconciles to population x workforce_share.
        state.population += event.get("population", 0.0)
        state.subsistence_capacity += event.get("subsistence_capacity", 0.0)
        state.peasants += event.get("peasants", 0.0)
        state.unemployed += event.get("unemployed", 0.0)
        state.workforce += event.get("peasants", 0.0) + event.get("unemployed", 0.0)
        for s, n in event.get("levels", {}).items():
            sectors.setdefault(s, SectorState(0.0)).levels += n

    # 2. Era.
    era = sc.era_at(year - p.era_shift_years)

    # 3-5. Per sector: staff, crew, VA a level, economy of scale, jobs.
    construction_price = nums.prices["construction"]
    maint_good_prev = point_price(p, construction_price, state.x)       # GBP a construction good, at last year's X
    eos_cap = _cap_with_steps(nums.base_eos_cap, nums.eos_cap_steps, era) * p.eos_cap_mult
    n_states = sc.n_states
    figs: dict[str, tuple[float, float, float, float, float]] = {}      # s -> (staff, crew, va, eos, maint)
    jobs_by_sector: dict[str, float] = {}
    for s, ss in sectors.items():
        if s not in LEVEL_BOUND:
            continue
        k_emp, k_va = sc.k_emp.get(s, 1.0), sc.k_va.get(s, 1.0)
        if s == "other":
            staff, crew, va, maint = k_emp, 0.0, k_va, 0.0
        else:
            lad = _ladder(md, s)
            b = _late(D.base_at(lad, era), p)
            tier = _late(lad.automation[ss.auto_tier], p) if lad.automation else None
            staff = max(0.0, k_emp * (b.employment + (tier.employment if tier else 0.0)))
            buildings = min(ss.levels, n_states) if n_states > 0 else 0.0
            crew = (tier.crew if tier else 0.0) * max(0.0, buildings)
            maint = lad.maintenance * p.maintenance_mult
            va = k_va * (b.va + (tier.va if tier else 0.0)) - maint * maint_good_prev
        if s in NO_EOS or n_states <= 0:
            eos = 0.0
        else:
            eos = 0.01 * min(max(ss.levels / n_states - 1.0, 0.0), eos_cap)
        figs[s] = (staff, crew, va, eos, maint)
        jobs_by_sector[s] = ss.levels * staff + crew
    jobs_level = sum(jobs_by_sector.values())

    demand_div = 1.0 + p.demand_gdp_ratio
    gdp_level_prev = state.gdp / demand_div if demand_div > 0 else state.gdp
    jobs_services = max(0.0, p.services_jobs_per_gdp * gdp_level_prev / p.price_level)
    wb = _late(D.base_at(_ladder(md, "construction"), era), p)
    wpp = (wb.employment / wb.construction_out if wb.construction_out > 0 else 0.0) * p.construction_labour_mult
    jobs_construction = max(0.0, state.points_week * wpp)
    jobs_demand = jobs_services + jobs_construction

    # 6. Shedding.
    if state.employed_level > jobs_level:
        state.unemployed += state.employed_level - jobs_level
        state.employed_level = jobs_level
    if state.employed_demand > jobs_demand:
        state.unemployed += state.employed_demand - jobs_demand
        state.employed_demand = jobs_demand

    # 7. Hiring.
    open_level = max(0.0, jobs_level - state.employed_level)
    open_demand = max(0.0, jobs_demand - state.employed_demand)
    open_jobs = open_level + open_demand
    want = min(open_jobs, max(0.0, p.fill_rate) * open_jobs)
    from_unemployed = min(want, state.unemployed)
    from_peasants = 0.0
    if want > from_unemployed and state.wage >= HIRE_PREMIUM * p.subsistence_income:
        floor = sc.land_floor_at(year) * sc.peasants
        from_peasants = min(want - from_unemployed, max(0.0, state.peasants - floor))
    hired = from_unemployed + from_peasants
    state.unemployed -= from_unemployed
    state.peasants -= from_peasants
    if open_jobs > 0:
        state.employed_level += hired * open_level / open_jobs
        state.employed_demand += hired * open_demand / open_jobs

    # 8. GDP. Employment splits across sectors in proportion to their jobs, so every
    # sector is staffed at the same share; a sector that needs nobody is fully staffed.
    fill = min(1.0, state.employed_level / jobs_level) if jobs_level > 0 else 1.0
    va_week = 0.0                               # staffed VA, base prices, a week
    va_capacity_week = 0.0                      # the same, fully staffed (for the wage margin)
    for s, (staff, crew, va, eos, _maint) in figs.items():
        levels = sectors[s].levels
        staffed = levels * fill if jobs_by_sector[s] > 0 else levels
        va_week += staffed * va * (1.0 + eos)
        va_capacity_week += levels * va * (1.0 + eos)
    retool_years = nums.retool_weeks / 52.0
    retool_paid = 0.0                           # base prices, this year
    for s, (_staff, _crew, _va, _eos, maint) in figs.items():
        ss = sectors[s]
        if ss.retool_left <= 0:
            continue
        charge = maint * nums.retool_mult * maint_good_prev * nums.retool_weeks * p.retool_charge_mult
        if retool_years > 0:
            retool_paid += ss.levels * charge * min(1.0, ss.retool_left) / retool_years
        ss.retool_left = max(0.0, ss.retool_left - 1.0)
    gdp_level = p.price_level * (52.0 * va_week - retool_paid)
    gdp = gdp_level * (1.0 + p.demand_gdp_ratio)
    gdppc = gdp / state.population if state.population > 0 else 0.0
    x = cost_mult(p, nums.curve, gdppc, sc.world_gdppc_at(year))
    if nums.curve.has_slack_band:
        state.slack_factor = eased_slack_factor(nums.curve, state.slack_factor,
                                                _share(state.peasants + state.unemployed, state.workforce))
        x *= state.slack_factor

    # 9. Construction.
    spend = (p.private_invest_share + p.gov_invest_share) * gdp
    project_cap = _cap_with_steps(nums.base_project_cap, nums.project_cap_steps, era) * p.project_cap_mult
    cap = project_cap * 52.0 * p.queue_per_state * n_states
    points, cap_bound = points_bought(spend, point_price(p, construction_price, x), cap)
    new_levels: dict[str, float] = {}
    for s, share in sc.alloc_at(year).items():
        # services and construction aren't built; a sector with no cost figure (R14)
        # or a cost of zero or less gets nothing, and its share is dropped.
        cost = sc.cost_points.get(s, 0.0) * p.cost_points_mult
        if s in LEVEL_BOUND and cost > 0:
            new_levels[s] = points * share / cost

    # 10. Automation, a best response against the tier in use (R25). Among the tiers
    # the era allows (tier 0 is "none", saving 0), the candidate saves most a level a
    # week. A sector switches to it when that beats its current tier by more than 0,
    # and by more than the retooling charge over the payback horizon. The wage is the
    # one the year started with; the charge is at this year's X.
    lag = p.automation_lag_years if p.automation_lag_years is not None else sc.automation_lag_years
    for s, (_staff, _crew, _va, _eos, maint) in figs.items():
        ss = sectors[s]
        lad = md.ladders.get(s)
        if lad is None or len(lad.automation) < 2 or ss.retool_left > 0:
            ss.ready_since = ss.ready_tier = None
            continue
        k_emp, k_va = sc.k_emp.get(s, 1.0), sc.k_va.get(s, 1.0)
        current = ss.auto_tier
        options = [i for i, t in enumerate(lad.automation) if t.era <= era or i == current]
        saving = {i: _saving(_late(lad.automation[i], p), state.wage, k_emp, k_va) for i in options}
        candidate = max(options, key=saving.__getitem__)
        gain = saving[candidate] - saving[current]
        charge = maint * nums.retool_mult * point_price(p, construction_price, x) * nums.retool_weeks * p.retool_charge_mult
        if not (gain > 0 and gain * 52.0 * p.payback_years > charge):
            ss.ready_since = ss.ready_tier = None
            continue
        if sc.kind == "ai":
            if ss.ready_tier != candidate or ss.ready_since is None:
                ss.ready_since, ss.ready_tier = year, candidate
            if year - ss.ready_since < lag:
                continue
        ss.auto_tier = candidate
        ss.retool_left = retool_years
        ss.ready_since = ss.ready_tier = None

    # 11. Wages.
    vac = (jobs_level - state.employed_level) / jobs_level if jobs_level > 0 else 0.0
    vacancies = (jobs_level - state.employed_level) + (jobs_demand - state.employed_demand)
    slack_people = state.peasants + state.unemployed
    if vac > p.vacancy_target:
        # 0.75 of VA a worker: staffed VA / employed, which is VA a job when every
        # sector is staffed at the same share (and stays defined when nobody is).
        # The margin stops a raise; it doesn't cut a wage already past it (spec 4.2:
        # buildings cut only at BUILDING_PROFIT_TARGET_TO_LOWER_WAGES, a margin of 0.15,
        # which the model leaves out).
        margin_cap = WAGE_SHARE_OF_VA * va_capacity_week / jobs_level
        raised = state.wage * (1.0 + p.wage_step * (vac - p.vacancy_target))
        state.wage = min(raised, max(state.wage, margin_cap))
    elif state.workforce > 0 and slack_people / state.workforce > p.slack_target:
        state.wage = p.wage_floor + (state.wage - p.wage_floor) * (1.0 - p.wage_decay)
    state.wage = max(state.wage, p.wage_floor)

    # 12. Population.
    g = _clamp(p.g_max - p.g_slope * math.log(max(gdppc, 1e-9) / nums.curve.reference), p.g_min, p.g_max)
    state.population *= 1.0 + g
    workforce = state.population * p.workforce_share
    people = state.peasants + state.unemployed + state.employed_level + state.employed_demand
    delta = workforce - people
    if delta >= 0:
        peasant_share = state.peasants / people if people > 0 else 0.0
        state.peasants += delta * peasant_share
        state.unemployed += delta * (1.0 - peasant_share)
    else:
        fall = -delta
        take = min(fall, state.unemployed)
        state.unemployed -= take
        fall -= take
        take = min(fall, state.peasants)
        state.peasants -= take
        fall -= take
        employed = state.employed_level + state.employed_demand
        if employed > 0 and fall > 0:
            keep = max(0.0, employed - fall) / employed
            state.employed_level *= keep
            state.employed_demand *= keep
    state.workforce = workforce
    capacity = state.subsistence_capacity
    if state.peasants > capacity:
        state.unemployed += state.peasants - capacity
        state.peasants = capacity
    # Subsistence hires an unemployed worker only for RETURN_PREMIUM x what welfare pays
    # (the subsistence buildings' min_raise_to_hire); welfare is deflated to base prices.
    welfare = sc.welfare_at(year) / p.price_level
    if RETURN_PREMIUM * welfare <= p.subsistence_income and state.peasants < capacity:
        back = min(max(0.0, p.return_rate) * state.unemployed, capacity - state.peasants)
        state.unemployed -= back
        state.peasants += back

    # 13. Flags; then the year's new levels land and the state moves on.
    labour_bound = vac > p.labour_bind_vacancy
    money_bound = not cap_bound and not labour_bound
    for s, n in new_levels.items():
        sectors.setdefault(s, SectorState(0.0)).levels += n
    state.gdp = gdp
    state.points_week = points / 52.0
    state.x = x
    state.year = year + 1

    return YearRecord(
        year=year,
        era=era,
        population=state.population,
        workforce=state.workforce,
        peasants=state.peasants,
        unemployed=state.unemployed,
        employed=state.employed_level + state.employed_demand,
        jobs_level=jobs_level,
        jobs_demand=jobs_demand,
        vacancies=vacancies,
        wage=state.wage,
        gdp=gdp,
        gdppc=gdppc,
        x=x,
        spend=spend,
        points=points,
        money_bound=money_bound,
        cap_bound=cap_bound,
        labour_bound=labour_bound,
        auto_tiers={s: ss.auto_tier for s, ss in sectors.items()},
        levels={s: ss.levels for s, ss in sectors.items()},
        jobs_by_sector=jobs_by_sector,
    )


def run(sc: Scenario, md: D.ModData, p: Params) -> list[YearRecord]:
    """Every year from sc.start_year to sc.end_year, inclusive."""
    state = initial_state(sc, md, p)
    return [step(state, sc, md, p) for _ in range(sc.start_year, sc.end_year + 1)]


def params_for(scenario: str, path: Path | str = PARAMS) -> Params:
    """The Params a scenario runs with: the defaults, then the file's structural values
    (shared by every scenario), then the scenario's behaviour values. player_poor and
    player_union take player_rich's behaviour (BEHAVIOUR_FROM); a scenario with no
    behaviour entry keeps the defaults. A name that isn't a Params field raises KeyError.

    The file is {"structural": {name: value}, "behaviour": {scenario: {name: value}}}.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    fields = {f.name for f in dataclasses.fields(Params)}
    behaviour = data.get("behaviour", {}).get(BEHAVIOUR_FROM.get(scenario, scenario), {})
    p = Params()
    for where, values in (("structural", data.get("structural", {})), ("behaviour " + scenario, behaviour)):
        unknown = sorted(set(values) - fields)
        if unknown:
            raise KeyError(str(path) + " " + where + ": not a Params field: " + ", ".join(unknown))
        p = dataclasses.replace(p, **values)
    return p


# --------------------------------------------------------------------------
# Diagnostics and the summary row (spec 5.5, 9)
# --------------------------------------------------------------------------

TURN_JOBS_SHARE = 0.5                           # the turn: tier 1 pays in sectors holding this share of the jobs
TAKEOFF_FALL = 0.05                             # take-off: the peasant share falls this much ...
TAKEOFF_SPAN = 5                                # ... within this many years
TAKEOFF_SLOP = 1e-9                             # (so a fall of exactly 5 points, 0.60 - 0.55, counts despite float error)
TAKEOFF_WINDOW = 20                             # the catch-up growth is read over this many years from take-off
CATCH_UP_SHARE = 0.10                           # catch-up: take-off to a peasant share under this (spec 2: 35 years)
PEASANTS_GONE_SHARE = 0.05                      # "peasants close to zero": a share under this (spec 2)


def _share(people: float, workforce: float) -> float:
    """`people` as a share of the workforce; 0 with no workforce (no one is slack)."""
    return people / workforce if workforce > 0 else 0.0


def classify(r: YearRecord, sc: Scenario, p: Params) -> str:
    """The year's mode (spec 5.5): "mode1", "mode2" or "ok".

    mode1 (too fast)  almost no slack (peasants + unemployed under p.mode1_slack of the
                      workforce) while level-bound jobs go unfilled (labour_bound).
    mode2 (too slow)  a rich country with idle workers: slack over p.mode2_slack, and rich,
                      meaning GDP per head at p.rich_gdppc or more, or the scenario's
                      rich_from_year reached. Both slack tests are strict. The wage plays no
                      part (R34): the game shows mode-2 slack alongside rising wages (the
                      jobs missing are the wrong kind, not wage-stuck), and the fit can drive
                      the wage floor to about 0, where a wage clause would zero the column.
    """
    slack = _share(r.peasants + r.unemployed, r.workforce)
    if slack < p.mode1_slack and r.labour_bound:
        return "mode1"
    rich = r.gdppc >= p.rich_gdppc or (sc.rich_from_year is not None and r.year >= sc.rich_from_year)
    if slack > p.mode2_slack and rich:
        return "mode2"
    return "ok"


def turn_year(records: list[YearRecord], md: D.ModData, sc: Scenario) -> int | None:
    """The first year the wage reaches tier 1's breakeven in sectors that together hold at
    least half of that year's level-bound jobs (spec 5.5, R5); None if no year does.

    A sector's tier 1 is the first tier of its automation group that a technology unlocks:
    the first `ladder.automation[i]` with i >= 1 and `era > 0` (R29). A tier with no
    unlocking technology (era 0, farming's pm_tools) is pre-industrial and doesn't count; for
    farming tier 1 is the steam threshers. Its breakeven is the bare `econ_sim_data.breakeven`
    (R24 pairs it with the adoption year, which also pays the retooling charge and scales by
    the calibration; so `sc` is only part of the interface).

    A sector qualifies in a year once the country's era (`r.era`) has reached its tier 1's
    era (R30) and the wage has reached the breakeven. A negative breakeven (the tier saves
    goods as well) qualifies at any wage, as a wage is never below 0. A level-bound sector
    without a qualifying tier (infrastructure, `other`, no unlocked tier, a tier that cuts no
    jobs), or one whose tier isn't unlocked yet, holds jobs but doesn't qualify: the half is
    of all the year's level-bound jobs, `r.jobs_by_sector`. A year with none is skipped.
    `records` are chronological, as `run` returns them.
    """
    tier_one: dict[str, tuple[float, int]] = {}                 # sector -> (breakeven, era)
    for sector, ladder in md.ladders.items():
        tier1 = next((t for t in ladder.automation[1:] if t.era > 0), None)
        be = None if tier1 is None else D.breakeven(tier1)
        if be is not None:
            tier_one[sector] = (be, tier1.era)
    for r in records:
        total = sum(r.jobs_by_sector.values())
        if total <= 0:
            continue
        paying = sum(jobs for sector, jobs in r.jobs_by_sector.items()
                     if sector in tier_one and r.wage >= tier_one[sector][0] and r.era >= tier_one[sector][1])
        if paying >= TURN_JOBS_SHARE * total:
            return r.year
    return None


def takeoff_year(records: list[YearRecord]) -> int | None:
    """The first year t whose peasant share (peasants / workforce) is at least 5 points above
    the share five years later; None if no year is. A year with no record five years on
    can't qualify, so a run needs at least six years."""
    share = {r.year: _share(r.peasants, r.workforce) for r in records}
    for r in records:
        later = share.get(r.year + TAKEOFF_SPAN)
        if later is not None and share[r.year] - later >= TAKEOFF_FALL - TAKEOFF_SLOP:
            return r.year
    return None


def first_year_below(records: list[YearRecord], share: float, after: int | None = None) -> int | None:
    """The first year whose peasant share is strictly below `share`; with `after`, the first
    such year from that year on (inclusive). None if there is none."""
    for r in records:
        if after is not None and r.year < after:
            continue
        if _share(r.peasants, r.workforce) < share:
            return r.year
    return None


@dataclass
class Summary:
    """One run's row (spec 9). None means the run never got there (or ended first).

    setting, scenario     which run: the lever setting's label, the scenario's name
    turn_year             first year wages reach tier 1's breakeven, once its technology is there
                          (tier 1 is the first tier a technology unlocks, R29; the country's era must
                          have reached its era, R30), in sectors holding half the jobs
    adoption_year         first year any sector is on an automation tier (R24), even if it later
                          goes back to none. Usually after the turn: the tier must also repay
                          its retooling charge, and the calibration scales its saving
    peasants_below_5pct   first year peasants are under 5% of the workforce
    slack_1950 / _2000 / _2045   (peasants + unemployed) / workforce that year
    mode1_years, mode2_years     years classified mode 1 ("too fast": no slack and labour-bound),
                          mode 2 ("too slow": a rich country with over 10% of its workforce idle,
                          at any wage, R34); see `classify`
    money_years, cap_years, labour_years   years each flag was set (cap and labour can both be)
    gdppc_2045            GDP per head in 2045
    takeoff_year          see `takeoff_year`
    takeoff_to_10pct      years from take-off to the first year under 10% peasants
    takeoff_growth_ratio  this run's mean yearly GDP-per-head growth over the 20 years after
                          take-off, over the reference run's over the same years
    """

    setting: str
    scenario: str
    turn_year: int | None
    adoption_year: int | None
    peasants_below_5pct: int | None
    slack_1950: float | None
    slack_2000: float | None
    slack_2045: float | None
    mode1_years: int
    mode2_years: int
    money_years: int
    cap_years: int
    labour_years: int
    gdppc_2045: float | None
    takeoff_year: int | None
    takeoff_to_10pct: int | None
    takeoff_growth_ratio: float | None


def _mean_growth(gdppc: dict[int, float], years: list[int]) -> float:
    return sum(gdppc[y] / gdppc[y - 1] - 1.0 for y in years) / len(years)


def _growth_ratio(records: list[YearRecord], reference: list[YearRecord], takeoff: int) -> float | None:
    """Mean yearly GDP-per-head growth over the years after `takeoff` (up to 20 of them),
    divided by the reference's over the same years: the years in that window that both runs
    have, with the year before each. None with no such year, or a reference that doesn't grow."""
    own = {r.year: r.gdppc for r in records}
    ref = {r.year: r.gdppc for r in reference}
    years = [y for y in range(takeoff + 1, takeoff + TAKEOFF_WINDOW + 1)
             if y in own and y in ref and own.get(y - 1, 0.0) > 0 and ref.get(y - 1, 0.0) > 0]
    if not years:
        return None
    ref_growth = _mean_growth(ref, years)
    if ref_growth <= 0:
        return None
    return _mean_growth(own, years) / ref_growth


def summarize(records: list[YearRecord], sc: Scenario, md: D.ModData, p: Params, setting: str,
              reference: list[YearRecord] | None = None) -> Summary:
    """The run's summary row. `reference` is the rich player run under the same lever setting;
    it is only read for takeoff_growth_ratio."""
    by_year = {r.year: r for r in records}
    modes = [classify(r, sc, p) for r in records]

    def slack_in(year: int) -> float | None:
        r = by_year.get(year)
        return None if r is None else _share(r.peasants + r.unemployed, r.workforce)

    r2045 = by_year.get(2045)

    takeoff = takeoff_year(records)
    to_10pct = None
    ratio = None
    if takeoff is not None:
        below = first_year_below(records, CATCH_UP_SHARE, after=takeoff)
        to_10pct = None if below is None else below - takeoff
        if reference is not None:
            ratio = _growth_ratio(records, reference, takeoff)

    adoption = next((r.year for r in records if any(t > 0 for t in r.auto_tiers.values())), None)
    return Summary(
        setting=setting,
        scenario=sc.name,
        turn_year=turn_year(records, md, sc),
        adoption_year=adoption,
        peasants_below_5pct=first_year_below(records, PEASANTS_GONE_SHARE),
        slack_1950=slack_in(1950),
        slack_2000=slack_in(2000),
        slack_2045=slack_in(2045),
        mode1_years=modes.count("mode1"),
        mode2_years=modes.count("mode2"),
        money_years=sum(1 for r in records if r.money_bound),
        cap_years=sum(1 for r in records if r.cap_bound),
        labour_years=sum(1 for r in records if r.labour_bound),
        gdppc_2045=None if r2045 is None else r2045.gdppc,
        takeoff_year=takeoff,
        takeoff_to_10pct=to_10pct,
        takeoff_growth_ratio=ratio,
    )


# --------------------------------------------------------------------------
# Command line (spec 9)
# --------------------------------------------------------------------------

DEFAULT_SCENARIOS = "player_rich,player_poor,ai_rich,ai_poor"
DEFAULT_CURVES = "linear,capped:1,slope:0.5,slope:2,none"   # each times the mod's slack share; capped:1 holds the line at +100%; a cap of max_mult or more is `linear`
DASH = "—"
TRACE_EVERY = 10                                # `run` prints a line each decade, and the first and last year
COLUMNS = ("Setting", "Type", "Turn year", "Adoption year", "Peasants < 5%",
           "Peasants + unemployed 1950 / 2000 / 2045", "Years in mode 1 / mode 2", "Binding: money / cap / labour",
           "GDP per capita 2045", "Take-off year", "Take-off to < 10% peasants (years)", "Growth vs type 1 (x)")


def _coerce(name: str, text: str, type_name: str) -> object:
    """`text` as the Params field `name` of annotation `type_name` ("float", "float | None", "str")."""
    optional = type_name.endswith("| None")
    base = type_name.removesuffix("| None").strip()
    if optional and text.lower() == "none":
        return None
    try:
        if base == "float":
            value = float(text)
            if math.isnan(value):
                raise ValueError("nan")
            return value
        if base == "int":
            return int(text)
    except ValueError:
        raise SystemExit("--set " + name + ": expected " + base + (" or none" if optional else "")
                         + ", got " + repr(text)) from None
    if base == "str":
        if name == "curve" and text not in CURVES:
            raise SystemExit("--set curve: unknown shape " + repr(text) + "; expected one of " + ", ".join(CURVES))
        return text
    raise SystemExit("--set " + name + ": a " + type_name + " can't be set from the command line")


def parse_sets(items: list[str]) -> dict[str, object]:
    """`name=value` items as a dict of Params overrides, each value coerced to its field's type
    (a later item for the same name wins). An unknown name, a missing `=`, or a value that is
    not that type raises SystemExit; `none` sets an optional field (curve_cap, ...) to None."""
    types = {f.name: str(f.type) for f in dataclasses.fields(Params)}
    out: dict[str, object] = {}
    for item in items:
        name, eq, text = item.partition("=")
        name, text = name.strip(), text.strip()
        if not eq or not name:
            raise SystemExit("--set expects name=value, got " + repr(item))
        if name not in types:
            raise SystemExit("--set: unknown parameter " + repr(name) + "; valid names: " + ", ".join(types))
        out[name] = _coerce(name, text, types[name])
    return out


def _curve_number(shape: str, text: str, spec: str) -> float:
    try:
        value = float(text)
    except ValueError:
        value = math.nan
    if not math.isfinite(value) or value < 0:
        raise SystemExit("curve " + repr(spec) + ": " + shape + " needs a number of 0 or more, as " + shape + ":<number>")
    return value


def parse_curve(spec: str) -> dict:
    """A curve spec as the Params fields it sets. `capped:3` is {"curve": "capped", "curve_cap": 3.0};
    `slope:0.5` is the mod's line at half the steepness, {"curve": "linear", "curve_slope": 0.5};
    `linear`, `log`, `sqrt`, `world` and `none` set only the shape. An unknown shape, `capped` or
    `slope` without a number, or a number on a shape that takes none, raises SystemExit."""
    shape, colon, arg = spec.strip().partition(":")
    if shape in ("capped", "slope"):
        if not arg:
            raise SystemExit("curve " + repr(spec) + ": " + shape + " needs a number, as " + shape + ":<number>")
        value = _curve_number(shape, arg, spec)
        return {"curve": "capped", "curve_cap": value} if shape == "capped" else {"curve": "linear", "curve_slope": value}
    if shape not in CURVES:
        raise SystemExit("unknown curve shape " + repr(spec) + "; expected one of " + ", ".join(CURVES)
                         + " (capped:<cap>, slope:<k>)")
    if colon:
        raise SystemExit("curve " + repr(spec) + ": " + shape + " takes no number")
    return {"curve": shape}


def _params(scenario: str, sets: dict[str, object], curve: str | None) -> Params:
    """The fitted parameters of `scenario`, then `sets`, then `curve` (a parse_curve spec) on top."""
    p = dataclasses.replace(params_for(scenario), **sets)
    if curve is not None:
        p = dataclasses.replace(p, **parse_curve(curve))
    if p.curve == "capped" and p.curve_cap is None:
        raise SystemExit("the capped curve needs a cap: --curve capped:<cap> or --set curve_cap=<cap>")
    return p


def _known(names: list[str]) -> None:
    """SystemExit unless every name is one of econ_sim_scenarios.SCENARIOS."""
    from scripts.analysis import econ_sim_scenarios as SC

    unknown = [name for name in names if name not in SC.SCENARIOS]
    if unknown:
        raise SystemExit("unknown scenario " + ", ".join(map(repr, unknown)) + "; expected one of " + ", ".join(SC.SCENARIOS))


def sweep(curves: list[str], scenarios: list[str], md: D.ModData, dataset: dict, sets: dict) -> list[Summary]:
    """One Summary per curve spec x scenario, curves outermost. Each run uses the scenario's fitted
    parameters (`params_for`), `sets` over them, and the curve on top; the row's `setting` is the
    spec. Its reference (the take-off growth ratio's denominator) is player_rich under the same
    curve and sets. `sets` may not name `curve`: the sweep sets that itself."""
    from scripts.analysis import econ_sim_scenarios as SC

    _known(scenarios)
    if "curve" in sets:
        raise SystemExit("a sweep sets the curve itself: use --curves, not --set curve=")
    for spec in curves:
        parse_curve(spec)                                   # a bad spec stops the sweep before any run
    built = {name: SC.scenario(name, dataset, md) for name in dict.fromkeys(["player_rich", *scenarios])}
    rows: list[Summary] = []
    for spec in curves:
        records: dict[str, list[YearRecord]] = {}
        params: dict[str, Params] = {}
        for name in built:
            params[name] = _params(name, sets, spec)
            records[name] = run(built[name], md, params[name])
        for name in scenarios:
            rows.append(summarize(records[name], built[name], md, params[name], spec, reference=records["player_rich"]))
    return rows


def _percent(x: float | None) -> str:
    return DASH if x is None else f"{100.0 * x:.1f}%"


def _cell(x: object, fmt: str = "") -> str:
    return DASH if x is None else format(x, fmt)


def render_table(rows: list[Summary]) -> str:
    """The sweep as a markdown table (spec 9's columns, the adoption year after the turn year, and the
    three catch-up columns). A None shows as a dash."""
    lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    for s in rows:
        cells = [
            s.setting, s.scenario, _cell(s.turn_year), _cell(s.adoption_year), _cell(s.peasants_below_5pct),
            " / ".join(_percent(x) for x in (s.slack_1950, s.slack_2000, s.slack_2045)),
            f"{s.mode1_years} / {s.mode2_years}",
            f"{s.money_years} / {s.cap_years} / {s.labour_years}",
            _cell(s.gdppc_2045, ".1f"),
            _cell(s.takeoff_year), _cell(s.takeoff_to_10pct), _cell(s.takeoff_growth_ratio, ".2f"),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _trace(records: list[YearRecord], sc: Scenario, p: Params) -> str:
    """A line a decade (and the first and last year): the run's shape at a glance."""
    lines = ["| Year | Era | GDP per capita | Peasants | Unemployed | Wage | X | Mode |", "|---|---|---|---|---|---|---|---|"]
    for r in records:
        if r.year % TRACE_EVERY and r is not records[0] and r is not records[-1]:
            continue
        lines.append(f"| {r.year} | {r.era:.1f} | {r.gdppc:.2f} | {_percent(_share(r.peasants, r.workforce))} | "
                     f"{_percent(_share(r.unemployed, r.workforce))} | {r.wage:.3f} | {r.x:.2f} | {classify(r, sc, p)} |")
    return "\n".join(lines)


def _write_csv(path: Path, records: list[YearRecord], sc: Scenario, p: Params) -> None:
    """The yearly path: every YearRecord figure, the year's mode, the peasant and slack shares,
    and a column per sector for its automation tier (`tier_`), levels (`levels_`) and level-bound
    jobs (`jobs_`); a sector a year doesn't hold is 0."""
    sectors = sorted({s for r in records for s in (*r.auto_tiers, *r.levels, *r.jobs_by_sector)})
    scalar = [f.name for f in dataclasses.fields(YearRecord) if f.name not in ("auto_tiers", "levels", "jobs_by_sector")]
    header = (scalar + ["mode", "peasant_share", "unemployed_share", "slack_share"]
              + ["tier_" + s for s in sectors] + ["levels_" + s for s in sectors] + ["jobs_" + s for s in sectors])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        out = csv.writer(fh)
        out.writerow(header)
        for r in records:
            row = [int(v) if isinstance(v, bool) else v for v in (getattr(r, n) for n in scalar)]
            row += [classify(r, sc, p), _share(r.peasants, r.workforce), _share(r.unemployed, r.workforce),
                    _share(r.peasants + r.unemployed, r.workforce)]
            row += [r.auto_tiers.get(s, 0) for s in sectors]
            row += [r.levels.get(s, 0.0) for s in sectors]
            row += [r.jobs_by_sector.get(s, 0.0) for s in sectors]
            out.writerow(row)


def _run_main(args) -> int:
    from scripts.analysis import econ_sim_scenarios as SC

    _known([args.scenario])
    sets = parse_sets(args.set or [])
    p = _params(args.scenario, sets, args.curve)
    md, dataset = D.load_mod_data(), SC.load_dataset()
    sc = SC.scenario(args.scenario, dataset, md)
    if args.end is not None:
        if args.end < sc.start_year:
            raise SystemExit(f"--end {args.end} is before the scenario's start, {sc.start_year}")
        sc = dataclasses.replace(sc, end_year=args.end)
    records = run(sc, md, p)
    if args.scenario == "player_rich":
        reference = records
    else:
        rich_p = _params("player_rich", sets, args.curve)
        reference = run(SC.scenario("player_rich", dataset, md), md, rich_p)
    summary = summarize(records, sc, md, p, args.curve or p.curve, reference=reference)
    print(render_table([summary]) + "\n")
    print(_trace(records, sc, p))
    if args.csv:
        _write_csv(Path(args.csv), records, sc, p)
        print(f"\nwrote {args.csv}")
    return 0


def _sweep_main(args) -> int:
    from scripts.analysis import econ_sim_scenarios as SC

    md, dataset = D.load_mod_data(), SC.load_dataset()
    scenarios = [x.strip() for x in args.scenarios.split(",")]
    curves = [x.strip() for x in args.curves.split(",")]
    print(render_table(sweep(curves, scenarios, md, dataset, parse_sets(args.set or []))))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="run one scenario: print its summary and a decade trace, optionally write the yearly CSV")
    r.add_argument("--scenario", required=True, help="player_rich, player_poor, ai_rich, ai_poor or player_union")
    r.add_argument("--set", action="append", metavar="NAME=VALUE", help="override a Params field (repeatable)")
    r.add_argument("--curve", metavar="SPEC", help="the cost curve: linear, capped:C, slope:K, log, sqrt, world or none")
    r.add_argument("--end", type=int, metavar="YEAR", help="run to this year instead of the scenario's own end")
    r.add_argument("--csv", metavar="PATH", help="write the yearly path here")
    w = sub.add_parser("sweep", help="print a table of curve shapes x country types")
    w.add_argument("--scenarios", default=DEFAULT_SCENARIOS, help="comma list (default %(default)s)")
    w.add_argument("--curves", default=DEFAULT_CURVES, help="comma list of curve specs (default %(default)s)")
    w.add_argument("--set", action="append", metavar="NAME=VALUE", help="override a Params field in every run (repeatable)")
    args = ap.parse_args(argv)
    return _run_main(args) if args.command == "run" else _sweep_main(args)


if __name__ == "__main__":
    # Run the importable module, not this __main__ copy: econ_sim_scenarios imports it by
    # name, and one module object keeps Params and YearRecord single classes.
    from scripts.analysis import econ_growth_sim as _module

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")        # the table's dash
    sys.exit(_module.main())
