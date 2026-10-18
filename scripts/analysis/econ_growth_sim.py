"""Economy growth sim (issue #1034): parameters, construction-cost curve, point price.

WHY THIS EXISTS
---------------
Playthrough saves show GDP growth stalling once a country is rich. The sim models
the loop that produces it -- investment buys construction points, points become
building levels, levels need workers, wages and automation follow -- so a lever
(the cost curve, the project cap, automation costs) can be swept before any script
changes. Design: docs/superpowers/specs/2026-10-17-economy-growth-sim-design.md.

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

Every mod number arrives as an argument (`econ_sim_data.ModData`, a base price
read from the goods data); nothing here is a copy of a script value. The three
labour rules of spec 4.2 (the 0.25 wage margin, the 10% raise to hire, the 30%
subsistence premium) are vanilla defines the snapshot doesn't carry; they are the
named constants below.
"""

from __future__ import annotations

import dataclasses
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
RETURN_PREMIUM = 1.3                            # 1 + the subsistence buildings' min_raise_to_hire (0.30)


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
    (nominal / price_level); `gdp` is annual and nominal."""

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
    x: float = 0.0                              # last year's cost multiplier; 0 before the first step


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
    )


def step(state: State, sc: Scenario, md: D.ModData, p: Params) -> YearRecord:
    """Advance `state` one year and return the year's record.

    The thirteen stages, in order (spec 5.3; numbers as in the plan's Task 6):

     1 annexations   this year's events add population, peasants, unemployed, levels
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
     8 GDP           staffed levels x VA x (1 + EoS), less retooling payments; X
     9 construction  investment buys points (point price at X, the per-project cap);
                     new levels arrive at the end of the year by allocation share
    10 automation    a best response: the tier that saves most at this year's wage,
                     when its saving over the tier in use, over the payback horizon,
                     beats the retooling charge; tiers can be skipped or undone; the
                     AI waits its lag; one switch a year (R25)
    11 wages         rise with vacancies (up to 0.75 of VA a worker), else drift to
                     the floor with slack
    12 population    growth falls with GDP per capita; the workforce follows; the
                     unemployed return to subsistence when welfare is below its
                     income x 1.3
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
    capacity = sc.subsistence_capacity
    if state.peasants > capacity:
        state.unemployed += state.peasants - capacity
        state.peasants = capacity
    welfare = sc.welfare_at(year) / p.price_level
    if welfare < RETURN_PREMIUM * p.subsistence_income and state.peasants < capacity:
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
