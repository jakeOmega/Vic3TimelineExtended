#!/usr/bin/env python3
"""Local Climate's winter sunshine: the pull behind local_climate.csv's winter_sun_h.

The sunshine term (docs/superpowers/specs/2026-11-01-local-climate-design.md § 13) reads each region's
mean daily hours of bright sunshine in the three months around the winter solstice: December to
February north of the equator, June to August south of it. Station sunshine normals exist for a few
hundred of the 676 regions, recorded by instruments that disagree, so every row is estimated the same way
from satellite data:

1. Each region's reference place (local_climate_sun_coords.csv): the station the heat figures came from
   where it lies within 60 km, or the place itself where it is farther, the heat figures are a fit, or
   they copy another row.
2. NASA POWER's monthly climatology there (2001-2025, the CERES SYN1deg grid, about 1 degree): all-sky,
   clear-sky and top-of-atmosphere sunlight on the ground (ALLSKY_SFC_SW_DWN, CLRSKY_SFC_SW_DWN,
   TOA_SW_DWN). Cached in build/local_climate_power_cache.json (gitignored); --refresh pulls again.
3. Each month's share of the possible hours (the day's astronomical length) that are sunny, an
   Angstrom-Prescott line in the two clearness ratios, all-sky over top-of-atmosphere and all-sky over
   clear-sky, with a snow term: snow under cloud reflects light back down, so a snowy month's overcast
   lets more through than its sunshine suggests. Snow is the record's own coldest month (0 at 0 C and
   above, 1 at -10 C and colder), times the first ratio.
4. The line's four weights fitted by least squares to station normals (local_climate_sun_reference.csv,
   approximate figures from the WMO and national normals, 1961-1990 to 1991-2020), less the American
   stations: their sunshine records, from the National Weather Service's older recorders, read about
   0.9 h a day above every other country's against the same satellite data, so they are listed but kept
   out of the fit (fit = no).
5. The quarter's mean, to 0.1 h. A polar-night month (no daylight) counts 0.

    .venv/bin/python scripts/analysis/local_climate_sun_pull.py [--refresh] [--write] [--report]

--report prints the fit, its leave-one-out error and each reference station's figure against it. --write
fills local_climate.csv's winter_sun_h column (re-run scripts/generators/gen_local_climate.py after).
Network: power.larc.nasa.gov. Needs numpy (the venv).
"""
import argparse
import csv
import json
import math
import os
import ssl
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(REPO, "scripts", "generators", "data", "local_climate.csv")
COORDS = os.path.join(HERE, "local_climate_sun_coords.csv")
REFERENCE = os.path.join(HERE, "local_climate_sun_reference.csv")
CACHE = os.path.join(REPO, "build", "local_climate_power_cache.json")
API = ("https://power.larc.nasa.gov/api/temporal/climatology/point?parameters="
       "ALLSKY_SFC_SW_DWN,CLRSKY_SFC_SW_DWN,TOA_SW_DWN&community=RE&longitude={lon}&latitude={lat}&format=JSON")
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
MID_DAY = (15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349)
DAYS = (31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
NORTH_WINTER, SOUTH_WINTER = (11, 0, 1), (5, 6, 7)
SNOW_COLD = 10.0  # the coldest month's mean, below 0 C, at which the snow term is whole


def day_length(lat, day):
    """Hours from sunrise to sunset on a day of the year (Cooper's declination)."""
    decl = math.radians(23.44) * math.sin(2 * math.pi * (284 + day) / 365)
    x = -math.tan(math.radians(lat)) * math.tan(decl)
    if x >= 1:
        return 0.0
    if x <= -1:
        return 24.0
    return 24 * math.acos(x) / math.pi


def load_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fetch(coords, cache, refresh=False, workers=8):
    """Fill `cache` (state -> POWER's monthly parameters) for every row of `coords`, eight at a time."""
    ctx = ssl.create_default_context(cafile=os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE"))

    def get(row):
        url = API.format(lat=row["lat"], lon=row["lon"])
        for attempt in range(6):
            try:
                with urllib.request.urlopen(url, context=ctx, timeout=90) as f:
                    data = json.load(f)
                return row["state"], {"lat": float(row["lat"]), "lon": float(row["lon"]),
                                      "range": data["header"]["range"], "p": data["properties"]["parameter"]}
            except Exception as e:  # noqa: BLE001 - a flaky API: retry anything
                print(f"{row['state']}: retry {attempt}: {e}", file=sys.stderr)
                time.sleep(2 ** attempt)
        raise RuntimeError(f"{row['state']}: POWER did not answer")

    todo = [r for r in coords if refresh or r["state"] not in cache]
    with ThreadPoolExecutor(workers) as pool:
        for state, value in pool.map(get, todo):
            cache[state] = value
    return cache


def months(entry, winter_c):
    """Per winter month: (day length, all-sky / top-of-atmosphere, all-sky / clear-sky, snow, days)."""
    p, lat = entry["p"], entry["lat"]
    snow = min(1.0, max(0.0, -winter_c / SNOW_COLD))
    out = []
    for m in (NORTH_WINTER if lat >= 0 else SOUTH_WINTER):
        k = MONTHS[m]
        n = day_length(lat, MID_DAY[m])
        sky, clear, toa = p["ALLSKY_SFC_SW_DWN"][k], p["CLRSKY_SFC_SW_DWN"][k], p["TOA_SW_DWN"][k]
        if n < 0.5 or sky < 0 or clear <= 0.05 or toa <= 0.05:
            out.append((n, None, None, snow, DAYS[m]))
        else:
            out.append((n, sky / toa, sky / clear, snow, DAYS[m]))
    return out


def features(kt, rc, snow):
    return (1.0, kt, rc, snow * kt)


def sunshine(entry, winter_c, w):
    """The quarter's mean daily sunshine, hours, with weights w."""
    total = days = 0.0
    for n, kt, rc, snow, d in months(entry, winter_c):
        share = 0.0 if kt is None else min(1.0, max(0.0, float(np.dot(w, features(kt, rc, snow)))))
        total += n * share * d
        days += d
    return total / days


def fit(refs, cache, winter):
    """Least-squares weights on each winter month's sunny share, the station's quarter mean over the mean day."""
    x, y = [], []
    for state, hours in refs.items():
        ms = months(cache[state], winter[state])
        mean_day = sum(m[0] for m in ms) / len(ms)
        for n, kt, rc, snow, _ in ms:
            if kt is not None:
                x.append(features(kt, rc, snow))
                y.append(hours / mean_day)
    return np.linalg.lstsq(np.array(x), np.array(y), rcond=None)[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--refresh", action="store_true", help="pull every row again, not only the uncached")
    parser.add_argument("--write", action="store_true", help="fill local_climate.csv's winter_sun_h")
    parser.add_argument("--report", action="store_true", help="print the fit against the reference stations")
    args = parser.parse_args(argv)

    coords = load_csv(COORDS)
    rows = load_csv(CSV)
    winter = {r["state"]: float(r["winter_mean_c"]) for r in rows}
    if [r["state"] for r in coords] != [r["state"] for r in rows]:
        print("local_climate_sun_coords.csv must list local_climate.csv's regions in its order", file=sys.stderr)
        return 1
    cache = {}
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            cache = json.load(f)
    fetch(coords, cache, args.refresh)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f)

    reference = load_csv(REFERENCE)
    refs = {r["state"]: float(r["sun_h"]) for r in reference if r["fit"] == "yes"}
    w = fit(refs, cache, winter)
    sun = {state: round(sunshine(cache[state], winter[state], w), 1) for state in winter}

    if args.report:
        loo = []
        for state in refs:
            w2 = fit({k: v for k, v in refs.items() if k != state}, cache, winter)
            loo.append(sunshine(cache[state], winter[state], w2) - refs[state])
        print("weights (1, all-sky/top, all-sky/clear, snow x all-sky/top): " + ", ".join(f"{v:.3f}" for v in w))
        print(f"{len(refs)} stations; leave-one-out error {math.sqrt(np.mean(np.square(loo))):.2f} h a day (root mean square)")
        for r in sorted(reference, key=lambda r: float(r["sun_h"])):
            est = sunshine(cache[r["state"]], winter[r["state"]], w)
            print(f"  {r['state']:<30} {r['ref_place'][:16]:<16} station {float(r['sun_h']):5.2f}  estimate {est:5.2f}"
                  f"{'' if r['fit'] == 'yes' else '  (not fitted)'}")

    if args.write:
        fields = list(rows[0].keys())
        if "winter_sun_h" not in fields:
            fields.insert(fields.index("heat_source"), "winter_sun_h")
        for r in rows:
            r["winter_sun_h"] = f"{sun[r['state']]:.1f}"
        with open(CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote winter_sun_h for {len(rows)} regions to {os.path.relpath(CSV, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
