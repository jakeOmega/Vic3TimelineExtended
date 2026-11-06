#!/usr/bin/env python3
"""Write local_climate_generated.txt: each state region's climate record as script values.

The Local Climate design (docs/superpowers/specs/2026-11-01-local-climate-design.md § 4) gives
every land state region a small record: the warmest month's mean temperature and dew-point class,
the coldest month's mean, water for settlement, malaria as of 1836, and latitude, all taken where
most of the region's people live, and (§ 11, heat v2) the hottest day of a typical year and the heat
stress on the year's worst day, from station records. The rows are
scripts/generators/data/local_climate.csv (state, ref_place, summer_mean_c, summer_humidity,
winter_mean_c, aridity, malaria, latitude, hot_day_c, heat_index, heat_source, reason). This writes a
state-scope script value for each field a script reads, each an if-chain on state_region,
so every piece of a split region reads the region's climate. A region with no row reads neutral
values (no penalty). Needs nothing but the repo. Re-run after editing the CSV;
test_local_climate.py fails CI when the committed file is stale:

    python3 scripts/generators/gen_local_climate.py [--check] [--plausibility]

--plausibility prints rows whose figures look unusual for their latitude, for a person to read, and
exits 1 on a validation error. A plain run writes the file even when a row fails validation, then exits 1.
"""
import argparse
import collections
import csv
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV = os.path.join(REPO, "scripts", "generators", "data", "local_climate.csv")
OUT = os.path.join(REPO, "common", "script_values", "local_climate_generated.txt")
STATE_REGIONS = os.path.join(REPO, "map_data", "state_regions")
SEAS = "99_seas.txt"

FIELDS = ("state ref_place summer_mean_c summer_humidity winter_mean_c aridity malaria latitude hot_day_c heat_index "
          "heat_source reason")
Row = collections.namedtuple("Row", FIELDS)
NUMERIC = ("summer_mean_c", "summer_humidity", "winter_mean_c", "aridity", "malaria", "latitude")
FLOATS = ("hot_day_c", "heat_index")
# Where a row's heat figures come from (§ 11.2): a station (its code and distance), the station with one figure
# from the fit on the record's own fields (a far or high station that missed the fit by 2.5 or more on it), the
# fit for both, or another region's row.
HEAT_SOURCE_RE = re.compile(r"[A-Z0-9]+:\d+km(?:;fit_(?:hot_day|index))?|fit|analog:STATE_\w+")

# (script value, Row field or None for has_record, neutral default, what it holds)
VALUES = (
    ("te_climate_has_record", None, 0, "1 when the region has a row, 0 when it reads the neutral defaults"),
    ("te_climate_summer_humidity", "summer_humidity", 0,
     "the warmest month's dew point: 0 dry (<10 °C), 1 moderate (10-16), 2 humid (16-20), 3 oppressive (>20); "
     "the tile's Humidity word only"),
    ("te_climate_winter_mean", "winter_mean_c", 15, "the coldest month's mean temperature, °C"),
    ("te_climate_aridity", "aridity", 0, "water for settlement: 0 ample, 1 limited, 2 scarce"),
    ("te_climate_malaria", "malaria", 0, "malaria as of 1836: 0 none, 1 seasonal or local, 2 endemic"),
    ("te_climate_latitude", "latitude", 0, "signed degrees of the reference place"),
    ("te_climate_hot_day", "hot_day_c", 20, "the hottest day of a typical year, °C (the mean of each year's highest)"),
    ("te_climate_heat_index", "heat_index", 0,
     "heat stress on a typical year's worst day, °C: 0.7 x wet-bulb + 0.3 x air temperature"),
)

RANGES = {"summer_mean_c": (-10, 45), "winter_mean_c": (-50, 30), "summer_humidity": (0, 3),
          "aridity": (0, 2), "malaria": (0, 2), "latitude": (-90, 90), "hot_day_c": (10, 52), "heat_index": (5, 40)}

# A vanilla desert trait needs water 1 or more, except where the region's people live by a great river or
# outside the desert: the trait describes the land, the record where people live (2026-11-01, PR #1307 review).
DESERT_TRAIT_EXCEPTIONS = {
    "STATE_EGYPTIAN_DESERT": "its people live on the Nile at Aswan",
    "STATE_WESTERN_AUSTRALIA": "its people live in Perth's Mediterranean south-west",
    "STATE_NORTHERN_TERRITORY": "its people live in the wet tropical Top End",
}

# Vanilla 1.15's cold (#1407): each state region's max_cold_effect, its cold at the peak of winter, which vanilla reads
# as moderate from 0.5 and severe from 0.75 (NWinter's MODERATE_ / SEVERE_COLD_EFFECT_THRESHOLD) for its world market
# access, supply ships and fleet speed. Nothing moves it at runtime, so Global Warming leaves it alone. The record's winter
# and vanilla's cold agree across the map (a straight line through winter and latitude misses vanilla's figure by 0.12, root
# mean square); cold_band_flags names a row that disagrees in kind, and each one it names here, with its reason, is accepted:
COLD_MODERATE, COLD_SEVERE = 0.5, 0.75
COLD_BAND_EXCEPTIONS = {
    # A mountain region whose people live in a valley: vanilla's cold covers the high ground, the record the valley.
    "STATE_HIMALAYAS": "its people live in the Kathmandu valley, below the snows vanilla's cold covers",
    "STATE_EASTERN_HIMALAYAS": "its people live in Bhutan's valleys (Punakha), below the snows vanilla's cold covers",
    "STATE_TAJIKISTAN": "its people live in the Hisor valley at Dushanbe, below the Pamirs vanilla's cold covers",
    "STATE_ALASKA": "its people lived on the mild panhandle coast at Sitka, not the arctic interior",
    # Vanilla's cold runs low across dry continental East Asia and the Armenian plateau, though the stations' winters
    # are hard: the record is the station's.
    "STATE_DZUNGARIA": "Urumqi's January is -12 C; vanilla's cold runs low on dry continental winters",
    "STATE_HINGGAN": "Hohhot's January is -11 C; vanilla's cold runs low on dry continental winters",
    "STATE_SHENGJING": "Mukden's January is -11 C; vanilla's cold runs low on dry continental winters",
    "STATE_SOUTHERN_MANCHURIA": "Jilin's January is -17 C; vanilla's cold runs low on dry continental winters",
    "STATE_KARS": "Kars's January is -11 C on the plateau; vanilla's cold runs low there",
}
# STATE_NORTH_RHINE is the one cold-wintered land region vanilla gives no cold pair at all (Cologne, 2 C; its
# neighbors read 0.49 to 0.56). The mod's state-region copies pass vanilla's fields through unchanged
# (test_state_regions_vanilla_sync), so it stays a vanilla gap; its winter of 2 C is under every band.

STATE_RE = re.compile(r"(?m)^(STATE_\w+)\s*=\s*\{")
TRAITS_RE = re.compile(r"traits\s*=\s*\{([^}]*)\}")
COLD_RE = re.compile(r"(?m)^\s*max_cold_effect\s*=\s*([\d.]+)")


def load_rows(path=CSV):
    """The CSV's rows, in file order, with numeric fields as ints."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = []
        for r in csv.DictReader(f):
            rows.append(Row(**{k: (int(r[k]) if k in NUMERIC else float(r[k]) if k in FLOATS else r[k])
                               for k in Row._fields}))
    return rows


def _region_files(repo):
    folder = os.path.join(repo, "map_data", "state_regions")
    for name in sorted(os.listdir(folder)):
        if name.endswith(".txt") and name != SEAS:
            with open(os.path.join(folder, name), encoding="utf-8-sig") as f:
                yield name, f.read()


def land_regions(repo=REPO):
    """Every state region in the mod's map_data/state_regions/ except the seas."""
    return {m.group(1) for _, text in _region_files(repo) for m in STATE_RE.finditer(text)}


def region_order(repo=REPO):
    """Land regions in map_data file order, then order within the file."""
    return [m.group(1) for _, text in _region_files(repo) for m in STATE_RE.finditer(text)]


def region_traits(repo=REPO):
    """STATE_X -> the traits its block lists."""
    traits = {}
    for _, text in _region_files(repo):
        starts = list(STATE_RE.finditer(text))
        for i, m in enumerate(starts):
            end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
            t = TRAITS_RE.search(text, m.end(), end)
            traits[m.group(1)] = set(re.findall(r'"?(\w+)"?', t.group(1))) if t else set()
    return traits


def region_cold(repo=REPO):
    """STATE_X -> its max_cold_effect (vanilla's, passed through), 0 where its block has none."""
    cold = {}
    for _, text in _region_files(repo):
        starts = list(STATE_RE.finditer(text))
        for i, m in enumerate(starts):
            end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
            c = COLD_RE.search(text, m.end(), end)
            cold[m.group(1)] = float(c.group(1)) if c else 0.0
    return cold


def cold_band_flags(rows, cold):
    """{state: why} for each row whose winter disagrees in kind with vanilla's cold at the peak of winter: a winter
    above freezing where vanilla's cold is severe, one milder than London's (3 C, the winter term's neutral) where it is
    at least moderate, or one of -10 C or harder where it isn't moderate."""
    flags = {}
    for r in rows:
        c, w = cold.get(r.state, 0.0), r.winter_mean_c
        if c >= COLD_SEVERE and w > 0:
            flags[r.state] = f"a {w} C winter under vanilla's severe cold ({c})"
        elif c >= COLD_MODERATE and w > 3:
            flags[r.state] = f"a {w} C winter under vanilla's moderate cold ({c})"
        elif w <= -10 and c < COLD_MODERATE:
            flags[r.state] = f"a {w} C winter where vanilla's cold is only {c}"
    return flags


def validate(rows, regions, traits):
    """One error string per problem, each naming its state."""
    errors = []
    seen = set()
    for r in rows:
        if r.state in seen:
            errors.append(f"{r.state}: duplicate row")
            continue
        seen.add(r.state)
        if r.state not in regions:
            errors.append(f"{r.state}: not a land state region of map_data/state_regions")
            continue
        for field, (low, high) in RANGES.items():
            value = getattr(r, field)
            if not low <= value <= high:
                errors.append(f"{r.state}: {field} {value} outside {low}..{high}")
        if r.winter_mean_c > r.summer_mean_c:
            errors.append(f"{r.state}: winter {r.winter_mean_c} warmer than summer {r.summer_mean_c}")
        if r.hot_day_c < r.summer_mean_c:
            errors.append(f"{r.state}: hottest day {r.hot_day_c} cooler than the warmest month {r.summer_mean_c}")
        if r.heat_index > r.hot_day_c:
            errors.append(f"{r.state}: heat index {r.heat_index} above the hottest day {r.hot_day_c}")
        if not HEAT_SOURCE_RE.fullmatch(r.heat_source):
            errors.append(f"{r.state}: heat_source {r.heat_source!r} is not code:Nkm[;fit_hot_day|;fit_index], "
                          "fit or analog:STATE_X")
        own = traits.get(r.state, set())
        if "state_trait_severe_malaria" in own and r.malaria < 2:
            errors.append(f"{r.state}: vanilla's state_trait_severe_malaria needs malaria 2, not {r.malaria}")
        elif "state_trait_malaria" in own and r.malaria < 1:
            errors.append(f"{r.state}: vanilla's state_trait_malaria needs malaria 1 or more, not 0")
        if (any(re.fullmatch(r"state_trait_\w+_desert", t) for t in own) and r.aridity < 1
                and r.state not in DESERT_TRAIT_EXCEPTIONS):
            errors.append(f"{r.state}: a vanilla desert trait needs aridity 1 or more, not 0")
    by_state = {r.state: r for r in rows}
    for r in rows:
        if r.heat_source.startswith("analog:"):
            src = by_state.get(r.heat_source.removeprefix("analog:"))
            if src is None:
                errors.append(f"{r.state}: {r.heat_source} names a region with no row")
            elif (src.hot_day_c, src.heat_index) != (r.hot_day_c, r.heat_index):
                errors.append(f"{r.state}: {r.heat_source} has hot day {src.hot_day_c} and heat index "
                              f"{src.heat_index}, not {r.hot_day_c} and {r.heat_index}")
    return errors


def implausible(rows):
    """Rows worth a second look: not errors, since highlands and rain shadows are real."""
    notes = []
    for r in rows:
        if abs(r.latitude) >= 55 and r.winter_mean_c > 5:
            notes.append(f"{r.state} ({r.ref_place}): latitude {r.latitude} with a {r.winter_mean_c} °C winter")
        if abs(r.latitude) <= 15 and r.winter_mean_c < 10 and r.summer_mean_c < 20:
            notes.append(f"{r.state} ({r.ref_place}): latitude {r.latitude}, summer {r.summer_mean_c} and "
                         f"winter {r.winter_mean_c} °C (a highland?)")
        if r.summer_humidity == 3 and r.aridity == 2:
            notes.append(f"{r.state} ({r.ref_place}): oppressive summer humidity in a region scarce of water")
    for state, why in cold_band_flags(rows, region_cold()).items():
        notes.append(f"{state}: {why}{' (accepted: ' + COLD_BAND_EXCEPTIONS[state] + ')' if state in COLD_BAND_EXCEPTIONS else ''}")
    return notes


def render(rows):
    lines = [
        "# AUTO-GENERATED by scripts/generators/gen_local_climate.py — do not edit manually.",
        "# Each state region's climate record (Local Climate design 2026-11-01 § 4), from",
        "# scripts/generators/data/local_climate.csv, taken where most of the region's people live.",
        "# Keyed on state_region, so every piece of a split region reads the region's climate; a region",
        "# with no row reads the first line's neutral value, which costs no comfort. Re-run the",
        "# generator after editing the CSV; test_local_climate.py fails when this file is stale.",
    ]
    for name, field, default, meaning in VALUES:
        lines += ["", f"# State scope: {meaning}.", f"{name} = {{", f"\tvalue = {default}"]
        for i, r in enumerate(rows):
            value = 1 if field is None else getattr(r, field)
            if isinstance(value, float):
                value = f"{value:g}"
            lines.append(f"\t{'if' if i == 0 else 'else_if'} = {{ limit = {{ state_region = s:{r.state} }} "
                         f"value = {value} }}")
        lines.append("}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 when the committed file is stale; write nothing")
    parser.add_argument("--plausibility", action="store_true", help="print rows worth a second look")
    args = parser.parse_args()
    rows = load_rows()
    errors = validate(rows, land_regions(), region_traits())
    for e in errors:
        print(f"error: {e}")
    if args.plausibility:
        for note in implausible(rows):
            print(f"look: {note}")
        return 1 if errors else 0
    text = render(rows)
    if args.check:
        try:
            with open(OUT, encoding="utf-8-sig") as f:
                current = f.read()
        except FileNotFoundError:
            current = None
        if current != text:
            print(f"{os.path.relpath(OUT, REPO)} is stale: run scripts/generators/gen_local_climate.py")
            return 1
        print(f"{os.path.relpath(OUT, REPO)} is current")
        return 1 if errors else 0
    with open(OUT, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write(text)
    print(f"wrote {len(rows)} regions to {os.path.relpath(OUT, REPO)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
