#!/usr/bin/env python3
"""Local Climate's calibration: the comfort formula in Python, against the anchor regions.

The Local Climate design (docs/superpowers/specs/2026-11-01-local-climate-design.md § 5.3) asks for
an evidence table before any constant is final: each anchor region's penalty in 1836 and at eras 4,
7, 10 and 13. This mirrors common/script_values/local_climate_values.txt (terms), reading its
constants from that file (load_constants), the relief carriers from the technology files
(relief_schedule) and the record from scripts/generators/data/local_climate.csv. It prints the
anchor regions and, since a mass migration picks a country by the average attraction of its
eligible states, each anchor country's mean penalty over its 1836 heartland.
test_local_climate_comfort.py pins the anchors' targets.

    python3 scripts/analysis/local_climate_calibration.py [--warming W]

W is the world's felt anomaly, °C (temperature_anomaly_display): 0 in 1836, about 1.1 today. The record
holds today's normals, so each region feels W less te_climate_normals_warming, times its latitude's
amplification; the default W = 0 is 1836.
"""
import argparse
import importlib.util
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TECH = os.path.join(REPO, "common", "technology", "technologies")
VANILLA_TECH = os.path.join(REPO, "vanilla_parsed", "common", "technologies.json")
VALUES = os.path.join(REPO, "common", "script_values", "local_climate_values.txt")
GENERATOR = os.path.join(REPO, "scripts", "generators", "gen_local_climate.py")
KINDS = ("heat", "cold", "water", "disease")
# Each penalty term and the relief kind that eases it.
TERM_RELIEF = {"heat": "heat", "cold": "cold", "dry": "water", "disease": "disease"}
ERAS = (1, 4, 7, 10, 13)
CONSTANT_RE = re.compile(r"(?m)^(te_climate_\w+) = (-?[\d.]+)\s*(?:#.*)?$")

# Spec § 5.3's anchor regions, with the test's own, in the order the table prints them.
ANCHORS = (
    "STATE_GEORGIA", "STATE_LOUISIANA", "STATE_FLORIDA", "STATE_OHIO", "STATE_MASSACHUSETTS",
    "STATE_ARIZONA", "STATE_CALIFORNIA", "STATE_QUEBEC",
    "STATE_HOME_COUNTIES", "STATE_ILE_DE_FRANCE", "STATE_CATALONIA", "STATE_LAZIO",
    "STATE_LOWER_ANDALUSIA", "STATE_MOSCOW", "STATE_YAKUTSK",
    "STATE_MIDDLE_EGYPT", "STATE_SAHARA", "STATE_NEJD", "STATE_WEST_BENGAL", "STATE_HYDERABAD",
    "STATE_RIO_DE_JANEIRO", "STATE_GOIAS",
)

# Each anchor country's 1836 heartland: the regions its 1836 history incorporates (vanilla
# common/history/states, read by hand on 2026-11-01; ownership isn't read at run time). Canada and
# Australia are the colonies they formed from (less New South Wales's Northern Territory and North
# Island); Cuba is Spain's sugar colony, a country of its own (CUB); Hamburg is a city-state.
COUNTRIES = (
    ("United States", (
        "STATE_ALABAMA", "STATE_CONNECTICUT", "STATE_DELAWARE", "STATE_DISTRICT_OF_COLUMBIA",
        "STATE_GEORGIA", "STATE_ILLINOIS", "STATE_INDIANA", "STATE_KENTUCKY", "STATE_LOUISIANA",
        "STATE_MAINE", "STATE_MARYLAND", "STATE_MASSACHUSETTS", "STATE_MISSISSIPPI", "STATE_MISSOURI",
        "STATE_NEW_HAMPSHIRE", "STATE_NEW_JERSEY", "STATE_NEW_YORK", "STATE_NORTH_CAROLINA", "STATE_OHIO",
        "STATE_PENNSYLVANIA", "STATE_RHODE_ISLAND", "STATE_SOUTH_CAROLINA", "STATE_TENNESSEE",
        "STATE_VERMONT", "STATE_VIRGINIA", "STATE_WEST_VIRGINIA")),
    ("Argentina", (
        "STATE_BUENOS_AIRES", "STATE_CORRIENTES", "STATE_JUJUY", "STATE_LA_PAMPA", "STATE_SANTA_FE")),
    ("Brazil", (
        "STATE_BAHIA", "STATE_CEARA", "STATE_GOIAS", "STATE_MARANHAO", "STATE_MATO_GROSSO",
        "STATE_MINAS_GERAIS", "STATE_PARAIBA", "STATE_PARANA", "STATE_PERNAMBUCO", "STATE_PIAUI",
        "STATE_RIO_DE_JANEIRO", "STATE_RIO_GRANDE_DO_NORTE", "STATE_SANTA_CATARINA", "STATE_SAO_PAULO")),
    ("Canada", ("STATE_ONTARIO", "STATE_QUEBEC", "STATE_NEW_BRUNSWICK")),
    ("Australia", (
        "STATE_NEW_SOUTH_WALES", "STATE_VICTORIA", "STATE_QUEENSLAND", "STATE_TASMANIA",
        "STATE_SOUTH_AUSTRALIA", "STATE_WESTERN_AUSTRALIA")),
    ("Russia", (
        "STATE_AKMOLINSK", "STATE_ARKHANGELSK", "STATE_ASTRAKHAN", "STATE_BESSARABIA", "STATE_BREST",
        "STATE_BURYATIA", "STATE_CHELYABINSK", "STATE_CHERNIHIV", "STATE_CHERSON", "STATE_CHUVASHIA",
        "STATE_CRIMEA", "STATE_DOBRUDJA", "STATE_GALICH", "STATE_INGRIA", "STATE_KALMYKIA", "STATE_KARS",
        "STATE_KAZAN", "STATE_KHARKOV", "STATE_KIEV", "STATE_KOLYMA", "STATE_KRASNOYARSK", "STATE_KURSK",
        "STATE_MINSK", "STATE_MOGILEV", "STATE_MOSCOW", "STATE_NIZHNY_NOVGOROD", "STATE_NORTH_CAUCASUS",
        "STATE_NOVGOROD", "STATE_ORYOL", "STATE_PERM", "STATE_PSKOV", "STATE_ROSTOV", "STATE_RYAZAN",
        "STATE_SAMARA", "STATE_SMOLENSK", "STATE_SURGUT", "STATE_TAMBOV", "STATE_TAURIDA", "STATE_TVER",
        "STATE_UFA", "STATE_URALSK", "STATE_VITEBSK", "STATE_VOLHYNIA", "STATE_VYATKA", "STATE_YAROSLAVL")),
    ("Cuba (sugar colony)", ("STATE_WESTERN_CUBA", "STATE_CENTRAL_CUBA", "STATE_EASTERN_CUBA")),
    ("Hamburg (city-state)", ("STATE_ELBE",)),
)

TOP_RE = re.compile(r"(?m)^(INJECT:|REPLACE:)?(\w+) = \{")
RELIEF_RE = re.compile(r"state_climate_(heat|cold|water|disease)_relief_add\s*=\s*(-?[\d.]+)")
# Malaria Prevention's relief is the census's Malaria Control, which the comfort formula adds to the
# disease relief (te_climate_relief_disease, local_climate_values.txt).
CONTROL_RE = re.compile(r"state_malaria_control_add\s*=\s*(-?[\d.]+)")
ERA_RE = re.compile(r"(?m)^\s*era\s*=\s*era_(\d+)")


def _blocks(text):
    """(directive, key, body) for each top-level block, braces balanced, comments skipped."""
    for m in TOP_RE.finditer(text):
        depth, i = 1, m.end()
        while depth and i < len(text):
            c = text[i]
            if c == "#":
                i = text.find("\n", i)
                if i < 0:
                    break
                continue
            depth += {"{": 1, "}": -1}.get(c, 0)
            i += 1
        yield m.group(1) or "", m.group(2), text[m.end():i - 1]


def _tech_texts(repo):
    folder = os.path.join(repo, "common", "technology", "technologies")
    for name in sorted(os.listdir(folder)):
        if name.endswith(".txt"):
            with open(os.path.join(folder, name), encoding="utf-8-sig") as f:
                yield name, f.read()


def tech_eras(repo=REPO):
    """Technology key -> era number: the mod's bare definitions, then vanilla's for the rest."""
    eras = {}
    with open(os.path.join(repo, "vanilla_parsed", "common", "technologies.json"), encoding="utf-8") as f:
        for key, value in json.load(f).items():
            try:
                eras[key] = int(value[1]["era"][1].removeprefix("era_"))
            except (KeyError, TypeError, ValueError, IndexError):
                continue
    for _, text in _tech_texts(repo):
        for directive, key, body in _blocks(text):
            m = ERA_RE.search(body)
            if m and directive in ("", "REPLACE:"):
                eras[key] = int(m.group(1))
    return eras


def relief_schedule(repo=REPO):
    """Kind -> [(era, technology, amount)], sorted by era, from every carrier line in the tech files."""
    eras = tech_eras(repo)
    schedule = {kind: [] for kind in KINDS}
    for name, text in _tech_texts(repo):
        for _, key, body in _blocks(text):
            found = RELIEF_RE.findall(body) + [("disease", a) for a in CONTROL_RE.findall(body)]
            for kind, amount in found:
                if key not in eras:
                    raise ValueError(f"{name}: {key} carries {kind} relief but has no era")
                schedule[kind].append((eras[key], key, float(amount)))
    for kind in KINDS:
        schedule[kind].sort()
    return schedule


def relief_at(schedule, kind, era):
    """The relief a country holding every carrier up to `era` has, clamped to [0, 1]. Era 1 is 1836.

    The sum is rounded to 9 places: the engine's fixed-point sum of 0.1 + 0.35 + ... is exact, and a
    float's last-place error would leave a sliver of penalty where the game has none."""
    return max(0.0, min(1.0, round(sum(amount for e, _, amount in schedule[kind] if e <= era), 9)))


def load_constants(path=VALUES):
    """The tuning constants at the head of local_climate_values.txt: script value name -> number."""
    with open(path, encoding="utf-8-sig") as f:
        return {name: float(value) for name, value in CONSTANT_RE.findall(f.read())}


def amplification(lat, c):
    """te_climate_amplification: 1 at |lat| <= amp_low_lat, rising linearly to amp_max at amp_high_lat."""
    low, high = c["te_climate_amp_low_lat"], c["te_climate_amp_high_lat"]
    share = min(1.0, max(0.0, (abs(lat) - low) / (high - low)))
    return 1 + share * (c["te_climate_amp_max"] - 1)


def terms(row, era, c, schedule, warming=0.0):
    """A row's four penalty terms and their sum, for a country holding every carrier up to `era`.

    `warming` is the world's felt anomaly (temperature_anomaly_display; 0 in 1836). The record holds at
    te_climate_normals_warming, so the row feels the anomaly less that, times its
    latitude's amplification. Mirrors local_climate_values.txt step by step."""
    felt = (warming - c["te_climate_normals_warming"]) * amplification(row.latitude, c)
    summer, winter = row.summer_mean_c + felt, row.winter_mean_c + felt
    raw = {
        "heat": max(0.0, summer - c["te_climate_heat_start"])
        * (1 + c["te_climate_humidity_factor"] * row.summer_humidity) * c["te_climate_heat_weight"],
        "cold": max(0.0, c["te_climate_cold_start"] - winter) * c["te_climate_cold_weight"],
        "dry": c["te_climate_dry_per_class"] * row.aridity,
        "disease": c["te_climate_malaria_per_class"] * row.malaria,
    }
    out = {term: value * (1 - relief_at(schedule, TERM_RELIEF[term], era)) for term, value in raw.items()}
    out["penalty"] = max(0.0, min(c["te_climate_penalty_max"], sum(out.values())))
    return out


def _load_rows():
    spec = importlib.util.spec_from_file_location("gen_local_climate", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {r.state: r for r in module.load_rows()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--warming", type=float, default=0.0,
                        help="the world's felt anomaly, °C (temperature_anomaly_display); default 0, 1836")
    args = parser.parse_args(argv)
    c, schedule, rows = load_constants(), relief_schedule(), _load_rows()
    heads = "".join(f"  era {e:>2}" for e in ERAS)
    print(f"Local Climate calibration: penalty in attraction points (1 SoL = 2), world anomaly {args.warming:+.1f} °C "
          f"(the record's normals hold at {c['te_climate_normals_warming']:+.1f}),")
    print("for a country holding every relief carrier up to each era (era 1 = 1836).\n")

    print(f"  {'Relief':<18}{heads}")
    for kind in KINDS:
        print(f"  {kind:<18}" + "".join(f"  {relief_at(schedule, kind, e):6.2f}" for e in ERAS))

    split_heads = "".join(f"{h:>6}" for h in ("heat", "cold", "dry", "dis."))
    print(f"\n  {'Anchor region':<26}  {'place':<14}  {split_heads}{heads}")
    print(f"  {'':<26}  {'':<14}  {'(the 1836 terms)':>24}")
    for state in ANCHORS:
        r = rows.get(state)
        if r is None:
            print(f"  {state:<26}  (no row yet)")
            continue
        t1 = terms(r, 1, c, schedule, args.warming)
        split = "".join(f"{t1[k]:6.1f}" for k in ("heat", "cold", "dry", "disease"))
        eras = "".join(f"  {terms(r, e, c, schedule, args.warming)['penalty']:6.1f}" for e in ERAS)
        print(f"  {state:<26}  {r.ref_place[:14]:<14}  {split}{eras}")

    print(f"\n  {'Anchor country: mean over its 1836 heartland':<50}  {'rows':<6}{heads}")
    for name, regions in COUNTRIES:
        have = [rows[s] for s in regions if s in rows]
        if not have:
            print(f"  {name:<50}  0/{len(regions):<3}  (no rows yet)")
            continue
        means = "".join(
            f"  {sum(terms(r, e, c, schedule, args.warming)['penalty'] for r in have) / len(have):6.1f}"
            for e in ERAS)
        print(f"  {name:<50}  {len(have)}/{len(regions):<3}{means}")
    print("\nHeartlands (regions with no row yet are left out of the mean, not counted as 0):")
    for name, regions in COUNTRIES:
        print(f"  {name}: " + ", ".join(s.removeprefix("STATE_").lower() for s in regions))
    return 0


if __name__ == "__main__":
    sys.exit(main())
