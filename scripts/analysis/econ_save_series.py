"""Read the economy growth sim's calibration series from Victoria 3 1.14.5 binary saves (issue #1034).

Per save and per country: the `pop_statistics` counts, the weekly GDP history,
the budget's investment figures, the construction queues and the state list,
plus a per-state slice of pops and buildings. Read-only; it needs nothing but
copies of the saves (copy a save into a scratch folder first; never read the
game's save folder in place). Run it with `python3 -I`.

Tokens are those of `~/src/vic3te-save-analysis-2026-10-17/series_probe/token_map.md`
(derived by field order against the plain-text `french commune_1949_07_20.v3`,
checked on binary `french commune_1917_10_02.v3` and `european union_1998_12_29.v3`).
They are validated on 1.14.5 only, so any other version is refused
(`check_supported`), as is a plain-text save.

"fx" is token 0x0167 read as a raw i64 (`fx_tokens`). Money and rates are
fx / 1e5; the pop counts in `pop_statistics` are raw integers stored as fx (no
scaling). `save_country_probe`'s own tokenizer reads 0x0167 as an f64, which is
wrong for these fields.

Country block (found with save_country_probe.country_headers):

| token  | text name | notes |
|--------|-----------|-------|
| 0x07dd | definition (tag) | |
| 0x3171 | budget | see below |
| 0x3f16 | gdp (trend) | { 0x3f14 sample_rate=28, 0x045a count=5214, 0x3f15 channels { 0 = { 0x06b5 date (hours), 0x020c index, 0x06ee { values fx } } } } |
| 0x2939 / 0x2fa7 / 0x4f2f | prestige / literacy / avg SoL trends | same layout |
| 0x0555 | variables | save_country_probe.read_variables |
| 0x330d | pop_statistics | see below |
| 0x09cd | states | list of state ids (match pop 0x2819 / building 0x01b7) |
| 0x333b | modifiers | save_country_probe.read_modifiers (names only) |
| 0x5720 | government_queue | { 0x567f construction_elements { {..} ... } } |
| 0x5721 | private_queue | same |

Trend ring buffer: one sample per week; `index` is the absolute week number
(8499 on 1998.12.29, 4263 on 1917.10.2). When index >= count (5214, about 100
years) it has wrapped: newest at (index - 1) % count, oldest at index % count.
The trend's date is the save date; the GDP sample is the yearly-rate GDP.

Budget 0x3171 (all fx / 1e5):

| token  | name |
|--------|------|
| 0x55be | weekly_expenses (22 slots; slot 7 = construction goods) |
| 0x55bd | weekly_income (16 slots; slot 7 = investment-pool transfer to construction) |
| 0x3776 | base_wage |
| 0x5b51 | average_productivity |
| 0x2a38 | money |
| 0x3f17 / 0x3f19 | credit / principal (debt) |
| 0x56c3 | investment_pool |
| 0x33c7 | weekly_investment_pool_change_from_construction (negative: the pool's weekly spend) |
| 0x52d6 | investment { "building_type" = weekly amount } |
| 0x5f30 | previous_building_group_investments { bg_x = v } |

pop_statistics 0x330d (raw counts): 0x573c lower_strata, 0x573d middle_strata,
0x573e upper_strata, 0x5743 salaried_workforce, 0x5744 subsisting_workforce,
0x5745 unemployed_workforce, 0x5746 government_workforce, 0x5747
military_workforce, 0x5748 laborer_workforce, 0x574b population_by_profession,
0x574c population_workforce_by_profession (15 slots, pop types alphabetical:
PROFESSIONS; slot 11 == subsisting_workforce and slot 8 == laborer_workforce
exactly). Workforce = salaried + subsisting + unemployed exactly.

Construction element (0x567f entries): 0x00e1 type, 0x01b7 state, 0x00db
identity, 0x2d93 construction_left, and only on elements progressing this week:
0x2e77 construction_speed, 0x59a1 base_construction_speed.

Pop record (`<u32 id> = { 0x00e1 = "<type>" ... }`): 0x2fd5 workforce and 0x573a
dependents (raw ints in 0x0167; written before the location, and omitted when
0), 0x2819 location (state id), 0x330b workplace (a building id; absent on an
unemployed pop), 0x4eed the weekly budget (13 fx entries: 0 wages, 1
subsistence, 2 dependent wages, 3 welfare, 4 dividends). The game keeps a
pop's employed and unemployed workers in separate pops, so a pop is employed
when it has a workplace: on FRA 1917 the non-peasant pops with one hold
28,676,702 workers (pop_statistics salaried: 28,676,621) and those without hold
6,003,962 (unemployed: 6,001,809). 0x573b, called "employed" in
scripts/pops.py, is not employment: pops with no workplace carry it too
(5.37M of their 6.00M); it is some other count of the workforce (94% of it).

Building record (`<id> = { 0x27f8 = "<type>" ... }`): 0x3a52 levels, 0x01b7
state, 0x32ed staffing (fx / 1e5), 0x5607 previous_staffing (employees, a raw
int in 0x0167), 0x2d15 goods_cost and 0x5606 goods_sales (fx / 1e5), 0x5925
production_methods.

Save files: SAV0100 is plain text. SAV0105 keeps the meta as a `meta` zip
entry; SAV0103 (autosaves) keeps it between the 24-byte header and the zip.
Binary meta writes the version as token 0x00ee = "1.14.5".
"""

from __future__ import annotations

import argparse
import io
import json
import re
import struct
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Direct CLI execution starts with scripts/analysis on sys.path.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from scripts.analysis import save_country_probe, save_world_report  # noqa: E402

FX_SCALE = 100_000
SUPPORTED_VERSION = "1.14.5"
PROFESSIONS = ("academics", "aristocrats", "bureaucrats", "capitalists", "clergymen", "clerks", "engineers",
               "farmers", "laborers", "machinists", "officers", "peasants", "shopkeepers", "slaves", "soldiers")

KEY_DEF, KEY_BUDGET, KEY_POP_STATS, KEY_STATES = 0x07DD, 0x3171, 0x330D, 0x09CD
KEY_GDP_TREND, KEY_TREND_COUNT, KEY_TREND_CHANNELS = 0x3F16, 0x045A, 0x3F15
KEY_TREND_INDEX, KEY_TREND_VALUES = 0x020C, 0x06EE
QUEUES = ((0x5720, "government"), (0x5721, "private"))
KEY_ELEMENTS, KEY_SPEED, KEY_BASE_SPEED = 0x567F, 0x2E77, 0x59A1
STRATA = (0x573C, 0x573D, 0x573E)
KEY_SALARIED, KEY_SUBSISTING, KEY_UNEMPLOYED, KEY_WF_BY_PROFESSION = 0x5743, 0x5744, 0x5745, 0x574C
BUDGET_FX = {"base_wage": 0x3776, "average_productivity": 0x5B51, "investment_pool": 0x56C3}
KEY_POOL_CHANGE, KEY_INVESTMENT = 0x33C7, 0x52D6
VARIABLES = ("prior_construction_scaling", "te_mon_gdp_last_year")

BINARY_VERSION_RE = re.compile(rb"\xee\x00\x01\x00(?:\x0f|\x17)\x00(..)", re.S)
VERSION_RE = re.compile(rb"\d+\.\d+\.\d+")


class UnsupportedSave(Exception):
    """The save is not a 1.14.5 binary save, so the token map can't be trusted on it."""


# ---------------------------------------------------------------- tokens (lifted from series_probe/../scripts/tok.py)
def fx_tokens(b, i, end):
    """Yield (offset, kind, value) for every token in b[i:end]; 0x0167 comes back as kind "fx", a raw i64."""
    while i < end - 1:
        t = struct.unpack_from("<H", b, i)[0]
        o = i
        i += 2
        if t == 0x0003:
            yield o, "{", None
        elif t == 0x0004:
            yield o, "}", None
        elif t == 0x0001:
            yield o, "=", None
        elif t in (0x000F, 0x0017):
            n = struct.unpack_from("<H", b, i)[0]
            yield o, "str", b[i + 2: i + 2 + n].decode("latin1")
            i += 2 + n
        elif t == 0x000C:
            yield o, "int", struct.unpack_from("<i", b, i)[0]
            i += 4
        elif t == 0x0014:
            yield o, "int", struct.unpack_from("<I", b, i)[0]
            i += 4
        elif t == 0x029C:
            yield o, "int", struct.unpack_from("<q", b, i)[0]
            i += 8
        elif t == 0x009C:
            yield o, "int", struct.unpack_from("<Q", b, i)[0]
            i += 8
        elif t == 0x000E:
            yield o, "bool", b[i]
            i += 1
        elif t == 0x000D:
            yield o, "f32", struct.unpack_from("<f", b, i)[0]
            i += 4
        elif t == 0x0167:
            yield o, "fx", struct.unpack_from("<q", b, i)[0]
            i += 8
        else:
            yield o, "tok", t


def fx_parse_block(b, start):
    """Parse `<key> = { ... }` at `start`; return (items, end_offset), items a list of (key, value)."""
    stream = fx_tokens(b, start, len(b))
    next(stream), next(stream)
    if next(stream)[1] != "{":
        raise ValueError(f"no block at 0x{start:x}")

    def parse_list():
        items, pending = [], None
        while True:
            o, k, v = next(stream)
            if k == "}":
                if pending is not None:
                    items.append((None, pending))
                return items, o + 2
            if k == "=":
                key, pending = pending, None
                _, k2, v2 = next(stream)
                items.append((key, parse_list()[0] if k2 == "{" else (k2, v2)))
                continue
            if pending is not None:
                items.append((None, pending))
                pending = None
            if k == "{":
                items.append((None, parse_list()[0]))
            else:
                pending = (k, v)

    return parse_list()


# ---------------------------------------------------------------- values
def get(items, key):
    """The value under token `key`, or None (also when `items` is not a block)."""
    if not isinstance(items, list):
        return None
    for k, v in items:
        if k == ("tok", key):
            return v
    return None


def fx_value(v):
    """A fixed-point scalar as a float (raw / FX_SCALE), or None."""
    return v[1] / FX_SCALE if isinstance(v, tuple) and v[0] == "fx" else None


def count_value(v):
    """A raw count (stored as fx or as an int) as an int, or None."""
    return v[1] if isinstance(v, tuple) and v[0] in ("fx", "int") else None


def str_value(v):
    return v[1] if isinstance(v, tuple) and v[0] == "str" else None


def dense(lst):
    """`{ N 0=a 1=b ... }` arrays come back as [(None, N), (('int', 0), v) ...]; return {index: v}."""
    return {k[1]: v for k, v in lst if k is not None and k[0] == "int"} if isinstance(lst, list) else {}


def unwrap_ring(values, index, count):
    """A trend ring buffer in chronological order, newest last.

    `index` is the absolute number of the next sample. Until the buffer fills
    (an early save) the samples are already in order; once index >= count it
    has wrapped, and the newest sits at (index - 1) % count.
    """
    values = list(values)
    if index >= count and len(values) == count:
        newest = (index - 1) % count
        return values[newest + 1:] + values[: newest + 1]
    return values


# ---------------------------------------------------------------- save files
def _binary_meta(path):
    """(meta bytes, zip entry names) of a binary save; UnsupportedSave when there is no readable zip."""
    raw = Path(path).read_bytes()
    start = raw.find(b"PK\x03\x04")
    if start == -1:
        raise UnsupportedSave("no zip payload (ironman or corrupt save?)")
    try:
        with zipfile.ZipFile(io.BytesIO(raw[start:])) as archive:
            names = archive.namelist()
            meta = archive.read("meta") if "meta" in names else raw[24:start]
    except zipfile.BadZipFile as exc:
        raise UnsupportedSave(f"unreadable zip payload ({exc})") from exc
    return meta, names


def version_in(meta):
    """The game version in a save's meta: the binary 0x00ee string, else the first X.Y.Z after `version`."""
    m = BINARY_VERSION_RE.search(meta)
    if m:
        n = struct.unpack("<H", m.group(1))[0]
        text = meta[m.end(): m.end() + n]
        if VERSION_RE.fullmatch(text):
            return text.decode()
    at = meta.find(b"version")
    m = VERSION_RE.search(meta, at if at != -1 else 0)
    return m.group(0).decode() if m else ""


def save_version(path):
    """The game version a save was written by ("" when the meta names none)."""
    if save_world_report.is_text_save(path):
        with open(path, "rb") as handle:
            return version_in(handle.read(65536))
    return version_in(_binary_meta(path)[0])


def check_supported(path):
    """Raise UnsupportedSave unless `path` is a 1.14.5 binary save with a gamestate."""
    with open(path, "rb") as handle:
        head = handle.read(256)
    if head.startswith(b"SAV0100") or save_world_report.is_text_save(path):
        raise UnsupportedSave("a plain-text save; only binary saves are read")
    meta, names = _binary_meta(path)
    if "gamestate" not in names:
        raise UnsupportedSave("no gamestate in the zip")
    version = version_in(meta)
    if not version.startswith(SUPPORTED_VERSION):
        raise UnsupportedSave(f"game version {version or 'unknown'}; the token map is validated on "
                              f"{SUPPORTED_VERSION} only")


# ---------------------------------------------------------------- country record
def _pop_statistics(items):
    ps = get(items, KEY_POP_STATS)
    out = dict.fromkeys(("population", "workforce", "salaried", "subsisting", "unemployed"))
    out["workforce_by_profession"] = {}
    if not isinstance(ps, list):
        return out
    out["population"] = sum(count_value(get(ps, k)) or 0 for k in STRATA)
    out["salaried"] = count_value(get(ps, KEY_SALARIED)) or 0
    out["subsisting"] = count_value(get(ps, KEY_SUBSISTING)) or 0
    out["unemployed"] = count_value(get(ps, KEY_UNEMPLOYED)) or 0
    slots = {i: count_value(v) or 0 for i, v in dense(get(ps, KEY_WF_BY_PROFESSION)).items()}
    by_prof = {name: slots.get(i, 0) for i, name in enumerate(PROFESSIONS)}
    # A slot past the known 15 (a pop type added later) still counts toward the workforce.
    by_prof.update({f"slot_{i}": v for i, v in sorted(slots.items()) if i >= len(PROFESSIONS)})
    out["workforce_by_profession"] = by_prof
    out["workforce"] = sum(by_prof.values())
    return out


def _gdp(items):
    trend = get(items, KEY_GDP_TREND)
    channels = get(trend, KEY_TREND_CHANNELS)
    channel = channels[0][1] if isinstance(channels, list) and channels else None
    values = get(channel, KEY_TREND_VALUES)
    index = count_value(get(channel, KEY_TREND_INDEX))
    count = count_value(get(trend, KEY_TREND_COUNT))
    if not isinstance(values, list) or index is None or count is None:
        return {"gdp_weekly": [], "gdp": None, "gdp_week_index": None}
    raw = [v[1] for _, v in values if isinstance(v, tuple) and v[0] == "fx"]
    weekly = [v / FX_SCALE for v in unwrap_ring(raw, index, count)]
    return {"gdp_weekly": weekly, "gdp": weekly[-1] if weekly else None, "gdp_week_index": index}


def _budget(items):
    budget = get(items, KEY_BUDGET)
    out = {name: fx_value(get(budget, key)) for name, key in BUDGET_FX.items()}
    change = fx_value(get(budget, KEY_POOL_CHANGE))
    # Stored as the pool's weekly change from construction, which is negative; the spend is its opposite.
    out["pool_spend_weekly"] = -change if change is not None else None
    investment = get(budget, KEY_INVESTMENT)
    out["investment_by_type"] = {
        k[1]: fx_value(v) for k, v in investment or [] if k and k[0] == "str" and fx_value(v) is not None
    } if isinstance(investment, list) else {}
    return out


def _queues(items):
    points, active, queued, caps = {}, {}, {}, []
    for key, name in QUEUES:
        queue = get(items, key)
        if not isinstance(queue, list):
            continue
        elements = get(queue, KEY_ELEMENTS)
        elements = [e for _, e in elements if isinstance(e, list)] if isinstance(elements, list) else []
        progressing = [(fx_value(get(e, KEY_SPEED)), fx_value(get(e, KEY_BASE_SPEED))) for e in elements]
        progressing = [(speed, base) for speed, base in progressing if speed is not None]
        points[name] = round(sum(speed for speed, _ in progressing), 5)   # fx resolution; drops float noise
        active[name] = len(progressing)
        queued[name] = len(elements)
        caps += [base for _, base in progressing if base is not None]
    return {"points_weekly": points, "active_projects": active, "queued_projects": queued,
            "per_project_cap": max(caps) if caps else None}


def country_record(blob, offset):
    """One country block's economy fields (see the module docstring); absent sections read None, {} or []."""
    items, _ = fx_parse_block(blob, offset)
    rec = {"tag": str_value(get(items, KEY_DEF))}
    rec.update(_pop_statistics(items))
    rec.update(_gdp(items))
    rec.update(_budget(items))
    rec.update(_queues(items))
    states = get(items, KEY_STATES)
    rec["states"] = [v[1] for k, v in states if k is None and isinstance(v, tuple) and v[0] == "int"] \
        if isinstance(states, list) else []
    variables = save_country_probe.read_variables(items)
    rec["variables"] = {name: variables[name] if isinstance(variables.get(name), float) else None
                        for name in VARIABLES}
    return rec


# ---------------------------------------------------------------- per-state slice
POP_RE = re.compile(rb"\x14\x00(....)\x01\x00\x03\x00\xe1\x00\x01\x00(?:\x0f|\x17)\x00", re.S)
KEY_POP_TYPE, KEY_LOCATION, KEY_POP_WORKFORCE, KEY_DEPENDENTS, KEY_WORKPLACE = 0x00E1, 0x2819, 0x2FD5, 0x573A, 0x330B
KEY_POP_BUDGET, POP_BUDGET_WAGES, POP_BUDGET_WELFARE = 0x4EED, 0, 3
KEY_BUILDING, KEY_LEVELS, KEY_BUILDING_STATE, KEY_PMS = 0x27F8, 0x3A52, 0x01B7, 0x5925
BUILDING_FX = {"staffing": 0x32ED, "goods_sales": 0x5606, "goods_cost": 0x2D15}
KEY_EMPLOYEES = 0x5607
PARSE_ERRORS = (ValueError, StopIteration, struct.error, IndexError)
_EQ_FX = b"\x01\x00\x67\x01"
# Real pops write the workforce and dependents (each 14 bytes: key, '=', 0x0167, i64) before the location.
_LEADING_COUNTS = (struct.pack("<H", KEY_POP_WORKFORCE), struct.pack("<H", KEY_DEPENDENTS))
_LOCATION = struct.pack("<H", KEY_LOCATION) + b"\x01\x00"
POP_FIELDS = ("population", "workforce", "peasants", "employed", "unemployed", "wages_weekly", "welfare_weekly")
UUID_RE = re.compile(rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
LAND_LAW_GROUP = "lawgroup_land_reform"


def _quick_location(blob, at):
    """The pop's state id read straight from the bytes after its type string, or None when it isn't there."""
    for key in _LEADING_COUNTS:
        if blob[at: at + 2] == key and blob[at + 2: at + 6] == _EQ_FX:
            at += 14
    if blob[at: at + 4] != _LOCATION:
        return None
    kind = blob[at + 4: at + 6]
    if kind == b"\x14\x00":
        return struct.unpack_from("<I", blob, at + 6)[0]
    if kind == b"\x0c\x00":
        return struct.unpack_from("<i", blob, at + 6)[0]
    return None


def pops_by_state(blob, states, warnings=None):
    """{state id: {population, workforce, peasants, employed, unemployed, wages_weekly, welfare_weekly}}.

    Population is workforce plus dependents. Peasants are the workforce of
    `peasants` pops. Every other pop's workforce is employed when it has a
    workplace and unemployed when it has none (the game splits a laid-off part
    into a pop of its own); its wages and welfare are slots 0 and 3 of its
    weekly budget. Only states that hold a pop appear.
    """
    states = set(states)
    sums, failed = {}, 0
    for m in POP_RE.finditer(blob):
        at = m.end()
        n = struct.unpack_from("<H", blob, at)[0]
        ptype = blob[at + 2: at + 2 + n].decode("latin1")
        if ptype not in PROFESSIONS:
            continue   # journal entries and other records open the same way
        quick = _quick_location(blob, at + 2 + n)
        if quick is not None and quick not in states:
            continue
        try:
            items, _ = fx_parse_block(blob, m.start())
        except PARSE_ERRORS:
            failed += 1
            continue
        loc = count_value(get(items, KEY_LOCATION))
        if loc not in states:
            continue
        wf = count_value(get(items, KEY_POP_WORKFORCE)) or 0
        dep = count_value(get(items, KEY_DEPENDENTS)) or 0
        s = sums.setdefault(loc, dict.fromkeys(POP_FIELDS, 0))
        s["population"] += wf + dep
        s["workforce"] += wf
        if ptype == "peasants":
            s["peasants"] += wf
            continue
        budget = [v for _, v in get(items, KEY_POP_BUDGET) or []]
        s["employed" if get(items, KEY_WORKPLACE) is not None else "unemployed"] += wf
        # Raw fx summed as integers; scaled once below, so the sums carry no float noise.
        for field, slot in (("wages_weekly", POP_BUDGET_WAGES), ("welfare_weekly", POP_BUDGET_WELFARE)):
            if slot < len(budget) and isinstance(budget[slot], tuple) and budget[slot][0] == "fx":
                s[field] += budget[slot][1]
    for s in sums.values():
        s["wages_weekly"] /= FX_SCALE
        s["welfare_weekly"] /= FX_SCALE
    if failed and warnings is not None:
        warnings.append(f"{failed} pop-like records failed to parse")
    return sums


def buildings_in(blob, states, warnings=None):
    """[{type, levels, state, staffing, employees, goods_sales, goods_cost, pms}] for each building in `states`."""
    states = set(states)
    out, failed = [], 0
    for m in save_world_report.BUILDING_RE.finditer(blob):
        try:
            items, _ = fx_parse_block(blob, m.start())
        except PARSE_ERRORS:
            failed += 1
            continue
        state, pms = count_value(get(items, KEY_BUILDING_STATE)), get(items, KEY_PMS)
        if state not in states or not isinstance(pms, list):
            continue
        rec = {"type": str_value(get(items, KEY_BUILDING)), "levels": count_value(get(items, KEY_LEVELS)) or 0,
               "state": state}
        for name, key in BUILDING_FX.items():
            rec[name] = fx_value(get(items, key)) or 0.0
        rec["employees"] = count_value(get(items, KEY_EMPLOYEES)) or 0
        rec = {k: rec[k] for k in ("type", "levels", "state", "staffing", "employees", "goods_sales", "goods_cost")}
        rec["pms"] = [str_value(v) for k, v in pms if k is None and str_value(v)]
        out.append(rec)
    if failed and warnings is not None:
        warnings.append(f"{failed} building-like records failed to parse")
    return out


def land_laws(blob, warnings, groups=None):
    """{country id: its active law in lawgroup_land_reform}; groups defaults to save_country_probe.known_law_groups()."""
    records, warning = save_country_probe.law_records(blob)
    if warning:
        warnings.append(warning)
    if not records:
        return {}
    groups = save_country_probe.known_law_groups() if groups is None else groups
    return {r["country"]: r["law"] for r in records if r["active"] and groups.get(r["law"]) == LAND_LAW_GROUP}


def playthrough_id(blob):
    m = UUID_RE.search(blob, 0, 200_000)
    return m.group(0).decode() if m else None


# ---------------------------------------------------------------- extract
def extract_from_blob(blob, date, country_ids, core=None, headers=None):
    """One save's extract from its gamestate (see `extract`).

    headers: [(offset, id, tag, ...)] for the country blocks; default
    save_country_probe.country_headers(blob). A requested id with no block is
    left out of countries, whole and core. The world sums run over every block.
    """
    warnings = []
    headers = save_country_probe.country_headers(blob) if headers is None else headers
    wanted = set(country_ids)
    countries, world_gdp, world_pop = {}, 0.0, 0
    for head in headers:
        offset, cid = head[0], head[1]
        rec = country_record(blob, offset)
        world_gdp += rec["gdp"] or 0.0
        world_pop += rec["population"] or 0
        if cid in wanted:
            countries[cid] = rec
    if countries:
        techs = {t["country"]: t["acquired"] for t in save_world_report.binary_techs(blob, warnings)}
        land = land_laws(blob, warnings)
        for cid, rec in countries.items():
            rec["acquired_techs"] = sorted(techs.get(cid, []))
            rec["land_law"] = land.get(cid)
    whole_sets = {cid: set(rec["states"]) for cid, rec in countries.items()}
    core_sets = {cid: set(s) for cid, s in (core or {}).items() if cid in countries}
    union = set().union(*whole_sets.values(), *core_sets.values())
    pops = pops_by_state(blob, union, warnings) if union else {}
    buildings = buildings_in(blob, union, warnings) if union else []

    def part(states):
        return {"states": {s: pops[s] for s in sorted(states) if s in pops},
                "buildings": [b for b in buildings if b["state"] in states]}

    return {
        "date": date,
        "playthrough": playthrough_id(blob),
        "countries": countries,
        "whole": {cid: part(s) for cid, s in whole_sets.items()},
        "core": {cid: {"state_ids": sorted(s), **part(s)} for cid, s in core_sets.items()},
        "world": {"gdp": round(world_gdp, 5), "population": world_pop},
        "warnings": warnings,
    }


def extract(path, country_ids, core=None):
    """{save, date, version, playthrough, countries, whole, core, world, warnings} for one supported save.

    countries: {id: country_record + acquired_techs + land_law}. whole: {id:
    {states: pops_by_state, buildings: buildings_in}} over the country's own
    states. core: the same over the given fixed state sets (plus their
    state_ids), only for the ids `core` names. world: Σ newest gdp and Σ
    population over every country block. Raises UnsupportedSave.
    """
    check_supported(path)
    world = save_world_report.World(path)
    try:
        out = extract_from_blob(world.source.blob, world.date, country_ids, core)
    finally:
        world.close()
    return {"save": Path(path).name, "date": out.pop("date"), "version": save_version(path), **out}


def core_states_from(path, country_ids):
    """{id: set of state ids}: each country's states in `path`, a save or a JSON extract this tool wrote."""
    path = Path(path)
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        countries = (data[0] if isinstance(data, list) else data)["countries"]
        found = {cid: set(_lookup(countries, cid)["states"]) for cid in country_ids if _lookup(countries, cid)}
    else:
        check_supported(path)
        world = save_world_report.World(path)
        try:
            blob = world.source.blob
            heads = {h[1]: h[0] for h in save_country_probe.country_headers(blob)}
            found = {cid: set(country_record(blob, heads[cid])["states"]) for cid in country_ids if cid in heads}
        finally:
            world.close()
    for cid in country_ids:
        if cid not in found:
            print(f"warning: country {cid} is not in {path.name}; it gets no core slice", file=sys.stderr)
    return found


# ---------------------------------------------------------------- dataset
def _lookup(mapping, cid):
    """A value keyed by a country or state id, as an int (fresh extract) or a string (JSON-loaded one)."""
    if not mapping:
        return None
    return mapping.get(cid, mapping.get(str(cid)))


def _ratio(num, den):
    return float("%.9g" % (num / den)) if den else 0.0


def slice_summary(part):
    """A whole or core extract part as the dataset's slice: pop sums, wage and welfare rates, buildings by type."""
    pops = list((part.get("states") or {}).values())
    out = {f: sum(p[f] for p in pops) for f in ("population", "workforce", "peasants", "employed", "unemployed")}
    out["wage_per_worker"] = _ratio(sum(p["wages_weekly"] for p in pops), out["employed"])
    out["welfare_per_unemployed"] = _ratio(sum(p["welfare_weekly"] for p in pops), out["unemployed"])
    by_type = {}
    for b in part.get("buildings") or []:
        t = by_type.setdefault(b["type"], {"levels": 0, "staffing": 0.0, "employees": 0, "goods_sales": 0.0,
                                           "goods_cost": 0.0, "pms": {}})
        for f in ("levels", "staffing", "employees", "goods_sales", "goods_cost"):
            t[f] += b[f]
        for pm in b["pms"]:
            t["pms"][pm] = t["pms"].get(pm, 0) + b["levels"]
    for t in by_type.values():
        for f in ("staffing", "goods_sales", "goods_cost"):
            t[f] = round(t[f], 5)
        t["pms"] = dict(sorted(t["pms"].items()))
    out["buildings_by_type"] = dict(sorted(by_type.items()))
    return out


def _year(hours):
    return hours // 24 // 365 - 5000


def build_dataset(raw):
    """Merge per-save extracts into the calibration dataset (format in docs/systems/economy_growth_sim.md § Data).

    Points are sorted by date. gdp_yearly is the mean of each calendar year's
    weekly GDP samples, merged across saves by absolute week number with later
    saves winning on overlap. A country's points end at the last save that has
    it. Raises ValueError on extracts from more than one playthrough.
    """
    for e in raw:
        if save_world_report.date_hours(e.get("date")) is None:
            raise ValueError(f"extract of {e.get('save')} has no readable date ({e.get('date')!r})")
    extracts = sorted(raw, key=lambda e: save_world_report.date_hours(e["date"]))
    ids = {e.get("playthrough") for e in extracts} - {None}
    if len(ids) > 1:
        raise ValueError(f"extracts from more than one playthrough: {sorted(ids)}")
    countries, weeks, world, core_states = {}, {}, [], {}
    for e in extracts:
        date, hours = e["date"], save_world_report.date_hours(e["date"])
        world.append({"date": date, "gdp": e["world"]["gdp"], "population": e["world"]["population"]})
        for cid, rec in e["countries"].items():
            key = str(cid)
            series = countries.setdefault(key, {"tag_by_date": {}, "gdp_yearly": {}, "points": []})
            series["tag_by_date"][date] = rec["tag"]
            values, index = rec.get("gdp_weekly") or [], rec.get("gdp_week_index")
            if index is not None:
                n = len(values)
                # The newest sample is the save date's; the samples before it are a week apart.
                for j, v in enumerate(values):
                    weeks.setdefault(key, {})[index - n + j] = (_year(hours - (n - 1 - j) * 168), v)
            point = {"date": date, **{k: v for k, v in rec.items() if k != "gdp_weekly"}}
            core = _lookup(e.get("core"), cid)
            if core:
                point["core"] = slice_summary(core)
                states = sorted(core["state_ids"])
                if core_states.setdefault(key, states) != states:
                    raise ValueError(f"country {key}: core states differ between extracts ({e.get('save')})")
            whole = _lookup(e.get("whole"), cid)
            if whole:
                point["whole"] = slice_summary(whole)
            series["points"].append(point)
    for key, merged in weeks.items():
        by_year = {}
        for year, v in merged.values():
            by_year.setdefault(year, []).append(v)
        countries[key]["gdp_yearly"] = {str(y): round(sum(vs) / len(vs), 5) for y, vs in sorted(by_year.items())}
    playthrough = ids.pop()[:8] if ids else None
    return {"playthrough": playthrough, "countries": countries, "world": world, "core_states": core_states}


# ---------------------------------------------------------------- CLI
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract the economy growth sim's calibration series from 1.14.5 binary saves (issue #1034).")
    parser.add_argument("inputs", nargs="+", help=".v3 saves to extract (copies, not the game's folder), "
                        "or .json extracts an earlier --out wrote")
    parser.add_argument("--country-id", type=int, action="append", default=[], help="a country id to read; repeatable")
    parser.add_argument("--core-from", help="a save (or JSON extract) whose state lists fix each core country's core")
    parser.add_argument("--core-id", type=int, action="append",
                        help="a country that gets a core slice; repeatable; default every --country-id")
    parser.add_argument("--out", help="write the per-save extracts (a JSON list) here")
    parser.add_argument("--dataset", help="write the merged dataset (build_dataset) here")
    args = parser.parse_args(argv)
    saves = [p for p in args.inputs if not p.endswith(".json")]
    if saves and not args.country_id:
        parser.error("--country-id is needed to extract a save")
    try:
        core = core_states_from(args.core_from, args.core_id or args.country_id) if args.core_from else None
    except UnsupportedSave as exc:
        parser.error(f"--core-from {Path(args.core_from).name}: {exc}")
    raws = []
    for name in args.inputs:
        if name.endswith(".json"):
            data = json.loads(Path(name).read_text(encoding="utf-8"))
            raws.extend(data if isinstance(data, list) else [data])
            continue
        try:
            raw = extract(name, args.country_id, core)
        except UnsupportedSave as exc:
            print(f"skip {Path(name).name}: {exc}")
            continue
        missing = sorted(set(args.country_id) - set(raw["countries"]))
        print(f"read {raw['save']}: {raw['date']}, countries {sorted(raw['countries'])}"
              + (f", absent {missing}" if missing else "") + "".join(f"\n  warning: {w}" for w in raw["warnings"]))
        raws.append(raw)
    if args.out:
        Path(args.out).write_text(json.dumps(raws, separators=(",", ":")), encoding="utf-8")
    if args.dataset:
        if not raws:
            print("no extracts to build a dataset from", file=sys.stderr)
            return 1
        Path(args.dataset).write_text(json.dumps(build_dataset(raws), separators=(",", ":")) + "\n",
                                      encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
