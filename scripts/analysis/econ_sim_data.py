"""Mod and vanilla numbers for the economy growth sim (issue #1034).

WHY THIS EXISTS
---------------
The growth sim (`econ_growth_sim.py`) needs the mod's construction-cost curve,
the construction-progress and economy-of-scale caps, the retooling charge, goods
prices, and the production-method ladders of eight sectors. Every one of those is
read out of the parsed mod and vanilla data at load time, so retuning a script
value, a technology or a production method changes the sim without editing it.

A missing or renamed key raises `KeyError` naming it, and a value that is not a
number raises `ValueError`. There is deliberately no literal fallback: a sim that
quietly keeps an old number after the mod moved is worse than one that stops.

SOURCES
-------
  common/script_values/extra_script_values.txt   curve constants, cost tiers
  vanilla_parsed/ (script values)                construction_cost_very_low ... high
  common/static_modifiers/extra_modifiers.txt    pm_retooling (a REPLACE of vanilla's)
  common/defines/extra_defines.txt               RETOOLING_WEEKS (read with a regex;
                                                 the parser does not load defines)
  Modifiers  base_values                         base project and economy-of-scale caps
  Technologies                                   cap steps by era, tech -> era
  Goods                                          base price (`cost`)
  PMs, PM Groups, Buildings, Building Groups     the sector ladders

`ModState` is built directly (never through `mod_state_server`, which needs the
game's paths), with vanilla taken from the committed `vanilla_parsed/` snapshot.

USAGE
-----
    from scripts.analysis import econ_sim_data as D
    md = D.load_mod_data()                      # about 2 s
    md.numbers.curve, md.ladders["mining"].base[0]
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Direct CLI execution starts with scripts/analysis on sys.path.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
import vanilla_parsed  # noqa: E402
from mod_state import VANILLA_COMMON_DIRS, ModState  # noqa: E402

# The entity types the sim reads. Everything else is left unloaded, which is what
# keeps the load near two seconds.
WANTED = (
    "Buildings",
    "PM Groups",
    "PMs",
    "Goods",
    "Technologies",
    "Script Values",
    "Building Groups",
    "Modifiers",
)

DEFINES_FILE = "common/defines/extra_defines.txt"

# Which sector a building group belongs to. The first group in a building's chain
# (its own group, then each parent) that appears here decides the sector, so
# bg_construction and bg_high_tech (both children of bg_heavy_industry) are found
# before their parent.
GROUP_SECTOR: dict[str, str] = {
    "bg_construction": "construction",
    "te_construction_market_bg": "construction",
    "bg_service": "services",
    "bg_urban_facilities": "services",
    "bg_high_tech": "hightech",
    "bg_heavy_industry": "heavy",
    "bg_light_industry": "light",
    "bg_manufacturing": "light",
    "bg_agriculture": "farming",
    "bg_plantations": "farming",
    "bg_ranching": "farming",
    "bg_extraction": "mining",
    "bg_infrastructure": "infrastructure",
    "bg_power": "infrastructure",
}

# sector -> (building, base PM group, automation PM group or None)
SECTOR_BUILDINGS: dict[str, tuple[str, str, str | None]] = {
    "farming": (
        "building_wheat_farm",
        "pmg_base_building_wheat_farm",
        "pmg_harvesting_process_building_wheat_farm",
    ),
    "mining": (
        "building_coal_mine",
        "pmg_mining_equipment_building_coal_mine",
        "pmg_steam_automation_building_coal_mine",
    ),
    "light": (
        "building_food_industry",
        "pmg_base_building_food_industry",
        "pmg_automation_building_food_industry",
    ),
    "heavy": (
        "building_steel_mill",
        "pmg_steelmaking_process",
        "pmg_automation_building_steel_mill",
    ),
    "hightech": (
        "building_electronic_components_and_semiconductor_industry",
        "pmg_base_building_electronic_components",
        "pmg_automation_building_electronic_components",
    ),
    "infrastructure": ("building_railway", "pmg_base_building_railway", None),
    "construction": (
        "building_construction_sector",
        "pmg_base_building_construction_sector",
        "pmg_construction_automation",
    ),
    "services": ("building_urban_center", "pmg_amenities", None),
}

# Maintenance groups carry a "no maintenance" choice and, on mines, a traditional
# one that costs nothing; neither is the building's maintenance rate.
NO_MAINTENANCE_PMS = ("pm_no_maintenance", "pm_maintenance_traditional")

# PMs with this in their name need a power-bloc principle; ladders leave them out.
PRINCIPLE_MARK = "_principle_"

_EMPLOYMENT_KEY = re.compile(r"^building_employment_.+_add$")
_GOODS_IN_KEY = re.compile(r"^goods_input_(.+)_add$")
_GOODS_OUT_KEY = re.compile(r"^goods_output_(.+)_add$")
_CONSTRUCTION_OUT_KEY = re.compile(r"^goods_output_construction_add$")
_ERA_NAME = re.compile(r"^era_(\d+)$")


# --------------------------------------------------------------------------
# Parser-value helpers
# --------------------------------------------------------------------------


def val(x):
    """Unwrap the parser's `('=', v)` pairs; any other value comes back as is."""
    while isinstance(x, tuple) and len(x) == 2 and isinstance(x[0], str):
        x = x[1]
    return x


def _number(x, what: str) -> float:
    """A parser value as a float; `ValueError` naming `what` if it is not a number.

    A key written twice comes back as a list of pairs; those add up.
    """
    x = val(x)
    if isinstance(x, list):
        if not x:
            raise ValueError(what + " is an empty list, not a number")
        return sum(_number(item, what) for item in x)
    if isinstance(x, (int, float)) and not isinstance(x, bool):     # a value already read out of a save
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            pass
    raise ValueError(what + " is not a number: " + repr(x))


def _blocks(x) -> list[dict]:
    """The `{ ... }` blocks behind a parser value (one block, or one per repeat)."""
    x = val(x)
    if isinstance(x, dict):
        return [x]
    if isinstance(x, list):
        out: list[dict] = []
        for item in x:
            out.extend(_blocks(item))
        return out
    return []


def _names(x) -> list[str]:
    """A parser value that holds a list of names (or a single name)."""
    x = val(x)
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    if isinstance(x, list):
        return [val(item) for item in x]
    raise ValueError("expected a list of names, got " + repr(x))


def _entry(ms, category: str, name: str) -> dict:
    """One entity's block from a ModState category; `KeyError` names both."""
    data = ms.get_data(category)
    if name not in data:
        raise KeyError(category + ": " + name)
    return val(data[name])


def _need(block: dict, key: str, where: str):
    if key not in block:
        raise KeyError(where + ": " + key)
    return block[key]


def script_number(ms, name: str) -> float:
    """A script value as a number.

    Stored as a plain number (`x = 5`) or as `x = { value = 5 }`; anything else
    (a computed value with `multiply`, a reference to another value) raises
    `ValueError`, because the sim would otherwise read a number the engine does
    not use.
    """
    raw = val(_need(ms.get_data("Script Values"), name, "Script Values"))
    if isinstance(raw, dict):
        if set(raw) != {"value"}:
            raise ValueError(
                "script value " + name + " is a computed block (keys: "
                + ", ".join(sorted(raw)) + "), not a plain number"
            )
        raw = raw["value"]
    return _number(raw, "script value " + name)


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def load_mod_state(repo: Path = REPO) -> ModState:
    """A ModState over the committed vanilla snapshot plus this repo's mod files."""
    snapshot = vanilla_parsed.load(str(repo / "vanilla_parsed"))
    # Only the wanted types are set up: ModState deep-copies the snapshot of every
    # type it is told about, and the rest are never read.
    base = {k: os.path.join("/nonexistent", VANILLA_COMMON_DIRS[k]) for k in WANTED}
    mod = {k: str(repo / "common" / VANILLA_COMMON_DIRS[k]) for k in WANTED}
    return ModState(base, mod, vanilla_data=snapshot.data)


# --------------------------------------------------------------------------
# Mod numbers
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CurveConstants:
    """The construction-cost curve: the GDP part is 0 at `reference*floor_ratio` GDP per
    capita and `max_mult` at `reference*ceiling_ratio`. With a slack band, the share of it
    that applies is 1 at slack (peasants + unemployed over the workforce) `slack_full` or less
    and 0 at `slack_none` or more, and moves `slack_ease` of the way to that each year
    (econ_growth_sim.slack_target, eased_slack_factor). None: no slack part, the whole GDP
    part applies."""

    reference: float
    floor_ratio: float
    ceiling_ratio: float
    max_mult: float
    slack_full: float | None = None
    slack_none: float | None = None
    slack_ease: float | None = None

    @property
    def has_slack_band(self) -> bool:
        return self.slack_full is not None and self.slack_none is not None


# The curve in force through the c480d386 playthrough: the GDP part alone, +1000% at GBP 100,
# with no slack part (ruling R37; #1034 then capped it at +100%, and the follow-up restored the
# line with the slack part). The saved series (`econ_series_c480d386.json`) were priced under
# this one, so the calibration and the counterfactual read the history through it, whatever
# the mod's files hold now.
HISTORICAL_CURVE = CurveConstants(1.0, 1.0, 100.0, 10.0)


@dataclass(frozen=True)
class ModNumbers:
    curve: CurveConstants
    cost_tiers: dict[str, float]
    retool_mult: float
    retool_weeks: int
    prices: dict[str, float]
    base_project_cap: float
    base_eos_cap: float
    project_cap_steps: tuple[tuple[int, str, float], ...]
    eos_cap_steps: tuple[tuple[int, str, float], ...]
    tech_era: dict[str, int]


def _tech_eras(ms) -> dict[str, int]:
    out: dict[str, int] = {}
    for tech, entry in ms.get_data("Technologies").items():
        era = val(_need(val(entry), "era", "Technologies " + tech))
        m = _ERA_NAME.match(str(era))
        if not m:
            raise ValueError("Technologies " + tech + ": era " + repr(era) + " is not era_<n>")
        out[tech] = int(m.group(1))
    return out


def _cap_steps(ms, tech_era: dict[str, int], modifier: str) -> tuple[tuple[int, str, float], ...]:
    steps = []
    for tech, entry in ms.get_data("Technologies").items():
        for block in _blocks(val(entry).get("modifier")):
            if modifier in block:
                steps.append((tech_era[tech], tech, _number(block[modifier], tech + " " + modifier)))
    return tuple(sorted(steps))


def _retool_weeks(repo: Path) -> int:
    path = repo / DEFINES_FILE
    text = path.read_text(encoding="utf-8-sig")
    m = re.search(r"^[ \t]*RETOOLING_WEEKS[ \t]*=[ \t]*([^\s#]+)", text, re.MULTILINE)
    if not m:
        raise KeyError(DEFINES_FILE + ": RETOOLING_WEEKS")
    try:
        return int(m.group(1))
    except ValueError:
        raise ValueError("RETOOLING_WEEKS in " + DEFINES_FILE + " is not an integer: " + m.group(1)) from None


def read_numbers(ms, repo: Path = REPO) -> ModNumbers:
    """Every mod number the sim uses, read from `ms` (and the defines file)."""
    curve = CurveConstants(
        reference=script_number(ms, "construction_cost_gdppc_reference"),
        floor_ratio=script_number(ms, "construction_cost_floor_ratio"),
        ceiling_ratio=script_number(ms, "construction_cost_ceiling_ratio"),
        max_mult=script_number(ms, "construction_cost_max_mult"),
        slack_full=script_number(ms, "construction_cost_slack_full"),
        slack_none=script_number(ms, "construction_cost_slack_none"),
        slack_ease=script_number(ms, "construction_cost_slack_ease"),
    )

    tier_names = set()
    for building in ms.get_data("Buildings").values():
        req = val(val(building).get("required_construction"))
        if isinstance(req, str):
            tier_names.add(req)
    cost_tiers = {}
    for name in sorted(tier_names):
        try:
            cost_tiers[name] = float(name)
        except ValueError:
            cost_tiers[name] = script_number(ms, name)

    retool = _entry(ms, "Modifiers", "pm_retooling")
    retool_mult = _number(
        _need(retool, "goods_input_construction_mult", "Modifiers pm_retooling"),
        "pm_retooling goods_input_construction_mult",
    )

    prices = {}
    for good, entry in ms.get_data("Goods").items():
        prices[good] = _number(_need(val(entry), "cost", "Goods " + good), "Goods " + good + " cost")

    base_values = _entry(ms, "Modifiers", "base_values")
    project_key = "country_max_weekly_construction_progress_add"
    eos_key = "building_economy_of_scale_level_cap_add"
    tech_era = _tech_eras(ms)

    return ModNumbers(
        curve=curve,
        cost_tiers=cost_tiers,
        retool_mult=retool_mult,
        retool_weeks=_retool_weeks(repo),
        prices=prices,
        base_project_cap=_number(_need(base_values, project_key, "Modifiers base_values"), project_key),
        base_eos_cap=_number(_need(base_values, eos_key, "Modifiers base_values"), eos_key),
        project_cap_steps=_cap_steps(ms, tech_era, project_key),
        eos_cap_steps=_cap_steps(ms, tech_era, eos_key),
        tech_era=tech_era,
    )


# --------------------------------------------------------------------------
# Production-method figures and sector ladders
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class PMFigures:
    """One production method's numbers.

    employment      sum of building_employment_*_add in level_scaled (jobs a level;
                    negative when the method removes jobs)
    crew            the same in unscaled (jobs a building, whatever its levels)
    goods_in/out    GBP a week a level at base prices, from the workforce_scaled
                    goods_input_*_add and goods_output_*_add (an output can be
                    negative: a method that cuts what the building makes)
    construction_out goods_output_construction_add, in goods (not GBP), a level
    """

    pm: str
    era: int
    employment: float
    crew: float
    goods_in: float
    goods_out: float
    construction_out: float

    @property
    def va(self) -> float:
        return self.goods_out - self.goods_in


def _scoped_sum(scopes: dict[str, list[dict]], scope: str, key_re: re.Pattern, prices: dict | None, pm: str) -> float:
    """Sum the `key_re` modifiers in one scope (`level_scaled`, `workforce_scaled`,
    `unscaled`) of a PM's building_modifiers.

    With `prices`, each amount is multiplied by the good's price (the good is the
    regex's first group); without, the raw amounts add up.
    """
    total = 0.0
    for block in scopes.get(scope, []):
        for key, raw in block.items():
            m = key_re.match(key)
            if not m:
                continue
            amount = _number(raw, pm + " " + key)
            if prices is not None:
                good = m.group(1)
                if good not in prices:
                    raise KeyError("Goods: " + good + " (used by " + pm + ")")
                amount *= prices[good]
            total += amount
    return total


def _scopes(pm_entry: dict) -> dict[str, list[dict]]:
    """A PM's `building_modifiers` as scope name -> its blocks (one per repeat)."""
    scopes: dict[str, list[dict]] = {}
    for block in _blocks(pm_entry.get("building_modifiers")):
        for scope, inner in block.items():
            scopes.setdefault(scope, []).extend(_blocks(inner))
    return scopes


def pm_figures(ms, numbers: ModNumbers, pm: str) -> PMFigures:
    entry = _entry(ms, "PMs", pm)
    techs = _names(entry.get("unlocking_technologies"))
    era = 0
    for tech in techs:
        if tech not in numbers.tech_era:
            raise KeyError("Technologies: " + tech + " (unlocks " + pm + ")")
        era = max(era, numbers.tech_era[tech])
    scopes = _scopes(entry)
    return PMFigures(
        pm=pm,
        era=era,
        employment=_scoped_sum(scopes, "level_scaled", _EMPLOYMENT_KEY, None, pm),
        crew=_scoped_sum(scopes, "unscaled", _EMPLOYMENT_KEY, None, pm),
        goods_in=_scoped_sum(scopes, "workforce_scaled", _GOODS_IN_KEY, numbers.prices, pm),
        goods_out=_scoped_sum(scopes, "workforce_scaled", _GOODS_OUT_KEY, numbers.prices, pm),
        construction_out=_scoped_sum(scopes, "workforce_scaled", _CONSTRUCTION_OUT_KEY, None, pm),
    )


@dataclass(frozen=True)
class Ladder:
    """A sector's representative building: its maintenance rate (construction
    goods a level a week), the base-method ladder, and the automation ladder.
    `automation[0]` is the group's first method, the "none" tier.

    `maintenance_by_base` holds the rate for base methods that unlock a dearer
    maintenance method (`pmg_maintenance_graded`: railways step up with their
    trains); a base method not in it pays `maintenance` (`maintenance_at`)."""

    sector: str
    building: str
    maintenance: float
    base: tuple[PMFigures, ...]
    automation: tuple[PMFigures, ...]
    maintenance_by_base: tuple[tuple[str, float], ...] = ()


def maintenance_at(lad: Ladder, base_pm: str) -> float:
    """The ladder's maintenance rate while its building runs `base_pm`."""
    return dict(lad.maintenance_by_base).get(base_pm, lad.maintenance)


def _group_pms(ms, group: str) -> list[str]:
    return _names(_need(_entry(ms, "PM Groups", group), "production_methods", "PM Groups " + group))


def _maintenance(ms, building: str) -> float:
    """Per-level construction goods of the building's maintenance method: the first
    method of any `pmg_maintenance*` group it uses that isn't a no-cost choice."""
    groups = _names(_need(_entry(ms, "Buildings", building), "production_method_groups", "Buildings " + building))
    for group in groups:
        if not group.startswith("pmg_maintenance"):
            continue
        for pm in _group_pms(ms, group):
            if pm in NO_MAINTENANCE_PMS:
                continue
            total = 0.0
            for level_block in _scopes(_entry(ms, "PMs", pm)).get("level_scaled", []):
                if "goods_input_construction_add" in level_block:
                    total += _number(level_block["goods_input_construction_add"], pm + " maintenance")
            return total
    return 0.0


def _maintenance_by_base(ms, building: str) -> tuple[tuple[str, float], ...]:
    """(base method, rate) for every method that a paid maintenance method of the
    building lists in `unlocking_production_methods`, at the dearest such rate: the
    graded group steps up through `replacement_if_valid` to the dearest method that
    fits. Mines' mechanized methods unlock the same rate `_maintenance` returns."""
    groups = _names(_need(_entry(ms, "Buildings", building), "production_method_groups", "Buildings " + building))
    rates: dict[str, float] = {}
    for group in groups:
        if not group.startswith("pmg_maintenance"):
            continue
        for pm in _group_pms(ms, group):
            if pm in NO_MAINTENANCE_PMS:
                continue
            entry = _entry(ms, "PMs", pm)
            rate = 0.0
            for level_block in _scopes(entry).get("level_scaled", []):
                if "goods_input_construction_add" in level_block:
                    rate += _number(level_block["goods_input_construction_add"], pm + " maintenance")
            for base_pm in _names(entry.get("unlocking_production_methods")):
                rates[base_pm] = max(rates.get(base_pm, 0.0), rate)
    return tuple(sorted(rates.items()))


def ladder(ms, numbers: ModNumbers, sector: str) -> Ladder:
    if sector not in SECTOR_BUILDINGS:
        raise KeyError("SECTOR_BUILDINGS: " + sector)
    building, base_group, auto_group = SECTOR_BUILDINGS[sector]
    # A `_principle_` PM needs a power-bloc principle, not a technology, and shares its
    # era with the plain PM beside it, so it would win every same-era tie in base_at.
    base = tuple(pm_figures(ms, numbers, pm) for pm in _group_pms(ms, base_group) if PRINCIPLE_MARK not in pm)
    auto = (
        tuple(pm_figures(ms, numbers, pm) for pm in _group_pms(ms, auto_group) if PRINCIPLE_MARK not in pm)
        if auto_group
        else ()
    )
    return Ladder(sector, building, _maintenance(ms, building), base, auto, _maintenance_by_base(ms, building))


def base_at(lad: Ladder, era: float) -> PMFigures:
    """The last base method whose era is `era` or earlier; the first if none is."""
    chosen = lad.base[0]
    for tier in lad.base:
        if tier.era <= era:
            chosen = tier
    return chosen


def breakeven(tier: PMFigures) -> float | None:
    """Wage (GBP a worker a week) at which this tier costs what the jobs it removes
    would. None for a tier that does not remove jobs."""
    if tier.employment >= 0:
        return None
    return (tier.goods_in - tier.goods_out) / -tier.employment


# --------------------------------------------------------------------------
# Sectors and building cost
# --------------------------------------------------------------------------


def sector_of(ms, building_type: str) -> str:
    """The sector a building type belongs to: `peasants` for subsistence farms (not
    in the Buildings data), `other` for anything that matches no group."""
    if building_type.startswith("building_subsistence"):
        return "peasants"
    buildings = ms.get_data("Buildings")
    if building_type not in buildings:
        return "other"
    groups = ms.get_data("Building Groups")
    group = val(val(buildings[building_type]).get("building_group"))
    seen: set[str] = set()
    while isinstance(group, str) and group not in seen:
        if group in GROUP_SECTOR:
            return GROUP_SECTOR[group]
        seen.add(group)
        group = val(val(groups[group]).get("parent_group")) if group in groups else None
    return "other"


def sector_cost_points(ms, numbers: ModNumbers, buildings_by_type: dict[str, dict]) -> dict[str, float]:
    """Per sector, the level-weighted mean `required_construction` (construction
    points) of the given building types, each entry being `{"levels": n, ...}`.

    A building type with no `required_construction` (it is never queued) or that
    the Buildings data does not know carries no cost and is left out; a sector
    with no cost-bearing levels is absent.
    """
    weight: dict[str, float] = {}
    total: dict[str, float] = {}
    buildings = ms.get_data("Buildings")
    for btype, info in buildings_by_type.items():
        if btype not in buildings:
            continue
        tier = val(val(buildings[btype]).get("required_construction"))
        if tier is None:
            continue
        if tier not in numbers.cost_tiers:
            raise KeyError("cost tier: " + str(tier) + " (required_construction of " + btype + ")")
        levels = _number(_need(info, "levels", "buildings_by_type " + btype), btype + " levels")
        if levels <= 0:
            continue
        sector = sector_of(ms, btype)
        weight[sector] = weight.get(sector, 0.0) + levels
        total[sector] = total.get(sector, 0.0) + levels * numbers.cost_tiers[tier]
    return {s: total[s] / weight[s] for s in weight}


# --------------------------------------------------------------------------
# Everything at once
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ModData:
    numbers: ModNumbers
    ladders: dict[str, Ladder]
    ms: ModState


def load_mod_data(repo: Path = REPO) -> ModData:
    ms = load_mod_state(repo)
    numbers = read_numbers(ms, repo)
    ladders = {sector: ladder(ms, numbers, sector) for sector in SECTOR_BUILDINGS}
    return ModData(numbers, ladders, ms)
