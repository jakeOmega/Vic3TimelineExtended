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

Pop record (`<u32 id> = { 0x00e1 = "<type>" ... }`): 0x2819 location (state
id), 0x2fd5 workforce, 0x573a dependents, 0x573b employed workforce (raw ints in
0x0167), 0x4eed the weekly budget (13 fx entries: 0 wages, 1 subsistence, 2
dependent wages, 3 welfare, 4 dividends). A pop of 0 people omits the counts.

Building record (`<id> = { 0x27f8 = "<type>" ... }`): 0x3a52 levels, 0x01b7
state, 0x32ed staffing (fx / 1e5), 0x5607 previous_staffing (employees, a raw
int in 0x0167), 0x2d15 goods_cost and 0x5606 goods_sales (fx / 1e5), 0x5925
production_methods.

Save files: SAV0100 is plain text. SAV0105 keeps the meta as a `meta` zip
entry; SAV0103 (autosaves) keeps it between the 24-byte header and the zip.
Binary meta writes the version as token 0x00ee = "1.14.5".
"""

from __future__ import annotations

import io
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
