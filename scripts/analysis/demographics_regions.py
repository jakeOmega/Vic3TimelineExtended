#!/usr/bin/env python3
"""Strategic regions for the demographics harness: which strategic region each state region is in.

The practices' start tables (demographics_params.PRACTICE_START_REGION) are keyed by strategic region, and the script
reads them with `region = sr:<name>`. The harness needs the same map for a save's states, which name only their state
region (`region="STATE_X"`). The base game keeps it in game/common/strategic_regions/, which CI doesn't have, and
vanilla_parsed/ has no strategic regions, so a snapshot sits beside this file (land regions only):

    demographics_regions.py --refresh [--game-dir DIR]   # rewrite demographics_strategic_regions.json
    demographics_regions.py --check   [--game-dir DIR]   # exit 1 if a fresh build would differ

Re-run --refresh after a vanilla patch that moves a state region (docs/guides/vanilla_patch_runbook.md).
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = Path(__file__).resolve().parent / "demographics_strategic_regions.json"
MOD_OVERRIDE = ROOT / "common" / "strategic_regions" / "zzz_modified_strategic_regions.txt"
STATE_REGIONS = ROOT / "map_data" / "state_regions"

_HEADER = re.compile(r"^(?:REPLACE:)?(region_\w+)\s*=\s*\{", re.M)
_STATES = re.compile(r"\bstates\s*=\s*\{([^{}]*)\}")
_STATE = re.compile(r"\bSTATE_[A-Z0-9_]+\b")

# #904's regional groups (its analyze.py's GROUPS and labels, which its state-years carry) with history's peacetime births
# less deaths in normal years, per 1,000 a year (PR #904's results doc, "Peacetime births less deaths, by region"): the
# late-marriage plan's gate (review C1). China's is the pace without its collapse; Africa's and the Middle East's are
# conjectures. Oceania has no band.
REPORT_REGIONS = (
    ("China", ("region_north_china", "region_south_china"), (3, 6)),
    ("India", ("region_north_india", "region_south_india", "region_himalayas"), (6, 9)),
    ("W/N/C/S Europe",
     ("region_western_europe", "region_northern_europe", "region_central_europe", "region_southern_europe"), (8, 10)),
    ("Africa", ("region_nile_basin", "region_north_africa", "region_west_africa", "region_equatorial_africa",
                "region_southern_africa", "region_east_africa"), (3, 8)),
    ("USA, Canada", ("region_canada", "region_pacific_coast", "region_great_plains", "region_atlantic_coast"),
     (17, 21)),
    ("E Europe, Balkans", ("region_eastern_europe", "region_balkans"), (8, 12)),
    ("Japan, Korea, Manchuria", ("region_northeast_asia",), (2, 6)),
    ("Russia, Siberia", ("region_russia", "region_siberia"), (10, 13)),
    ("Middle East, C Asia", ("region_near_east", "region_arabia", "region_greater_persia", "region_central_asia"),
     (4, 8)),
    ("South America", ("region_brazil", "region_andes", "region_la_plata", "region_gran_colombia"), (12, 16)),
    ("SE Asia", ("region_indochina", "region_indonesia"), (9, 13)),
    ("Mexico, C America", ("region_central_america",), (10, 13)),
    ("Oceania", ("region_oceania",), None),
)
# Calibration step 3, owner call 3 (2026-10-12): the gate widens each band by half the measured two-run spread on each
# side, at least WIDEN_FLOOR. The spread is each group's peacetime births less deaths, 1837-1900, in the two normal-speed
# Full runs from 1836 (ec304526, 2026-10-11, and 4002821a, the overnight run of 2026-10-12), per 1,000 a year, as
# `demographics_harness.py ontop-fit --spread-rows` measures it from their #904 state-years. Oceania stays unjudged.
TWO_RUN_SPREAD = {
    "China": 1.14, "India": 1.15, "W/N/C/S Europe": 0.08, "Africa": 0.27, "USA, Canada": 1.10,
    "E Europe, Balkans": 0.30, "Japan, Korea, Manchuria": 0.18, "Russia, Siberia": 0.18, "Middle East, C Asia": 0.13,
    "South America": 0.35, "SE Asia": 1.93, "Mexico, C America": 1.84, "Oceania": 4.22,
}
WIDEN_FLOOR = 0.5


def widening(spread=None, floor=WIDEN_FLOOR):
    """{group: how far the gate widens its band on each side}: half the two-run spread, at least `floor`."""
    spread = TWO_RUN_SPREAD if spread is None else spread
    return {label: max(floor, s / 2) for label, s in spread.items()}


_STATE_BLOCK = re.compile(r"^(STATE_[A-Z0-9_]+)\s*=\s*\{", re.M)
_TRAITS = re.compile(r"\btraits\s*=\s*\{([^{}]*)\}")


def state_region_traits(state_regions=STATE_REGIONS):
    """{state region: [its traits]} from the map files (map_data/state_regions, the mod's copy of every file, which the
    game reads in place of the base game's), seas left out."""
    out = {}
    for path in sorted(Path(state_regions).glob("*.txt")):
        if path.name == "99_seas.txt":
            continue
        text = path.read_text(encoding="utf-8-sig")
        heads = list(_STATE_BLOCK.finditer(text))
        for i, m in enumerate(heads):
            body = text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
            traits = _TRAITS.search(body)
            out[m.group(1)] = re.findall(r'"([^"]+)"', traits.group(1)) if traits else []
    return out


def malaria_levels(levels=None, state_regions=STATE_REGIONS):
    """{state region: its malaria level} for the state regions with one of vanilla's malaria traits (calibration step 3,
    demographics_params.MALARIA_TRAITS: 1 malaria, 2 severe; the higher if a region had both)."""
    import demographics_params as P
    levels = P.MALARIA_TRAITS if levels is None else levels
    out = {}
    for region, traits in state_region_traits(state_regions).items():
        level = max((levels[t] for t in traits if t in levels), default=0)
        if level:
            out[region] = level
    return out


def parse(text):
    """{region: [state regions]} from a strategic_regions file; a mod's REPLACE:region_x counts as region_x."""
    code = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
    out, pos = {}, 0
    while True:
        m = _HEADER.search(code, pos)
        if not m:
            return out
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(code[i], 0)
            i += 1
        states = _STATES.search(code[m.end():i - 1])
        if states:
            out[m.group(1)] = _STATE.findall(states.group(1))
        pos = i


def land_state_regions():
    """Every state region in map_data/state_regions/ outside the seas file."""
    out = set()
    for path in STATE_REGIONS.glob("*.txt"):
        if path.name != "99_seas.txt":
            out |= set(re.findall(r"^(STATE_[A-Z0-9_]+)\s*=\s*\{", path.read_text(encoding="utf-8-sig"), re.M))
    return out


def build(game_dir):
    """The table from the base game's files, the mod's REPLACEs on top, land regions only."""
    table = {}
    for path in sorted(Path(game_dir).glob("*.txt")):
        table.update(parse(path.read_text(encoding="utf-8-sig")))
    table.update(parse(MOD_OVERRIDE.read_text(encoding="utf-8-sig")))
    land = land_state_regions()
    return {r: sorted(s) for r, s in sorted(table.items()) if set(s) & land}


def load_table(path=SNAPSHOT):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def strategic_region_of(path=SNAPSHOT):
    return {state: region for region, states in load_table(path).items() for state in states}


def report_row_of():
    """{strategic region: its REPORT_REGIONS label}."""
    return {r: label for label, regions, _hist in REPORT_REGIONS for r in regions}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--game-dir")
    args = ap.parse_args(argv)
    game_dir = args.game_dir
    if game_dir is None:
        sys.path.insert(0, str(ROOT))
        import path_constants
        game_dir = Path(path_constants.base_game_path) / "game" / "common" / "strategic_regions"
    table = build(game_dir)
    text = json.dumps(table, indent=1, sort_keys=True) + "\n"
    if args.check:
        same = SNAPSHOT.exists() and SNAPSHOT.read_text(encoding="utf-8") == text
        print("current" if same else f"stale: {SNAPSHOT}")
        return 0 if same else 1
    if args.refresh:
        SNAPSHOT.write_text(text, encoding="utf-8")
        print(f"wrote {SNAPSHOT}: {len(table)} regions, {sum(len(s) for s in table.values())} state regions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
