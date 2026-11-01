#!/usr/bin/env python3
"""Write local_climate_generated.txt: each state region's climate record as script values.

The Local Climate design (docs/superpowers/specs/2026-11-01-local-climate-design.md § 4) gives
every land state region a small record: the warmest month's mean temperature and dew-point class,
the coldest month's mean, water for settlement, malaria as of 1836, and latitude, all taken where
most of the region's people live. The rows are scripts/generators/data/local_climate.csv
(state, ref_place, summer_mean_c, summer_humidity, winter_mean_c, aridity, malaria, latitude,
reason). This writes one state-scope script value per field, each an if-chain on state_region,
so every piece of a split region reads the region's climate. A region with no row reads neutral
values (no penalty). Needs nothing but the repo. Re-run after editing the CSV;
test_local_climate.py fails CI when the committed file is stale:

    python3 scripts/generators/gen_local_climate.py [--check] [--plausibility]

--plausibility prints rows whose figures look unusual for their latitude, for a person to read.
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

FIELDS = "state ref_place summer_mean_c summer_humidity winter_mean_c aridity malaria latitude reason"
Row = collections.namedtuple("Row", FIELDS)
NUMERIC = ("summer_mean_c", "summer_humidity", "winter_mean_c", "aridity", "malaria", "latitude")

# (script value, Row field or None for has_record, neutral default, what it holds)
VALUES = (
    ("te_climate_has_record", None, 0, "1 when the region has a row, 0 when it reads the neutral defaults"),
    ("te_climate_summer_mean", "summer_mean_c", 15, "the warmest month's mean temperature, °C"),
    ("te_climate_summer_humidity", "summer_humidity", 0,
     "the warmest month's dew point: 0 dry (<10 °C), 1 moderate (10-16), 2 humid (16-20), 3 oppressive (>20)"),
    ("te_climate_winter_mean", "winter_mean_c", 15, "the coldest month's mean temperature, °C"),
    ("te_climate_aridity", "aridity", 0, "water for settlement: 0 ample, 1 limited, 2 scarce"),
    ("te_climate_malaria", "malaria", 0, "malaria as of 1836: 0 none, 1 seasonal or local, 2 endemic"),
    ("te_climate_latitude", "latitude", 0, "signed degrees of the reference place"),
)

RANGES = {"summer_mean_c": (-10, 45), "winter_mean_c": (-50, 30), "summer_humidity": (0, 3),
          "aridity": (0, 2), "malaria": (0, 2), "latitude": (-90, 90)}

STATE_RE = re.compile(r"(?m)^(STATE_\w+)\s*=\s*\{")
TRAITS_RE = re.compile(r"traits\s*=\s*\{([^}]*)\}")


def load_rows(path=CSV):
    """The CSV's rows, in file order, with numeric fields as ints."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = []
        for r in csv.DictReader(f):
            rows.append(Row(**{k: (int(r[k]) if k in NUMERIC else r[k]) for k in Row._fields}))
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
        own = traits.get(r.state, set())
        if "state_trait_severe_malaria" in own and r.malaria < 2:
            errors.append(f"{r.state}: vanilla's state_trait_severe_malaria needs malaria 2, not {r.malaria}")
        elif "state_trait_malaria" in own and r.malaria < 1:
            errors.append(f"{r.state}: vanilla's state_trait_malaria needs malaria 1 or more, not 0")
        if any(re.fullmatch(r"state_trait_\w+_desert", t) for t in own) and r.aridity < 1:
            errors.append(f"{r.state}: a vanilla desert trait needs aridity 1 or more, not 0")
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
        return 0
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
