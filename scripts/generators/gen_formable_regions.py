#!/usr/bin/env python3
"""Generate state-region-form geographic_regions for the four mod formables
(EUN, AFU, UNA, UNE) that need them.

Vic3's formable code only reads `state_regions = {...}` from a geographic
region; `strategic_regions = {...}` (used by vanilla geographic_region_europe
etc.) is silently ignored when a formable references the region via its
`geographic_region = ...` field. So the mod can't point a formable at a
strategic_regions-form region and expect required-states enumeration to work.

This script reads vanilla `common/strategic_regions/*.txt`, expands the
config below to explicit state lists, and writes
`common/geographic_regions/te_formable_regions_generated.txt`.

Run after vanilla strategic-region changes (see docs/guides/vanilla_patch_runbook.md):
    .venv/bin/python scripts/generators/gen_formable_regions.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import path_constants  # noqa: E402

STRATEGIC_REGIONS_DIR = Path(path_constants.base_game_path) / "game" / "common" / "strategic_regions"
OUTPUT_FILE = Path(path_constants.mod_path) / "common" / "geographic_regions" / "te_formable_regions_generated.txt"

# Each formable geographic_region -> ordered list of vanilla strategic regions
# whose states it should contain. Mirrors the strategic_regions blocks the mod
# previously used (or vanilla's geographic_region_europe / _africa for EUN/AFU).
FORMABLE_REGIONS = [
    ("geographic_region_united_europe", "united_europe", [
        "region_western_europe",
        "region_southern_europe",
        "region_central_europe",
        "region_northern_europe",
        "region_balkans",
        "region_russia",
        "region_eastern_europe",
    ]),
    ("geographic_region_united_africa", "united_africa", [
        "region_nile_basin",
        "region_north_africa",
        "region_west_africa",
        "region_equatorial_africa",
        "region_southern_africa",
        "region_east_africa",
    ]),
    ("geographic_region_united_north_america", "united_north_america", [
        "region_canada",
        "region_atlantic_coast",
        "region_pacific_coast",
        "region_great_plains",
        "region_central_america",
    ]),
    ("geographic_region_united_earth", "united_earth", [
        # Europe
        "region_western_europe", "region_southern_europe", "region_central_europe",
        "region_northern_europe", "region_balkans", "region_russia", "region_eastern_europe",
        # Americas
        "region_canada", "region_atlantic_coast", "region_pacific_coast",
        "region_great_plains", "region_central_america",
        "region_brazil", "region_la_plata", "region_andes", "region_gran_colombia",
        # Africa
        "region_nile_basin", "region_north_africa", "region_west_africa",
        "region_equatorial_africa", "region_southern_africa", "region_east_africa",
        # Asia
        "region_near_east", "region_arabia", "region_greater_persia",
        "region_himalayas", "region_central_asia",
        "region_north_india", "region_south_india",
        "region_south_china", "region_north_china",
        "region_northeast_asia", "region_siberia",
        "region_indonesia", "region_indochina",
        # Oceania
        "region_oceania",
    ]),
]

REGION_HEADER_RE = re.compile(r"^(region_\w+)\s*=\s*\{", re.MULTILINE)
STATES_BLOCK_RE = re.compile(r"\bstates\s*=\s*\{([^{}]*)\}", re.DOTALL)
STATE_TOKEN_RE = re.compile(r"\bSTATE_[A-Z0-9_]+\b")


def parse_region_to_states(text: str) -> dict[str, list[str]]:
    """Return {region_name: [state, ...]} from one strategic_regions file.

    Walks brace depth so each top-level `region_X = { ... }` is handled in
    isolation, then pulls the single `states = {...}` block out of the body.
    """
    out: dict[str, list[str]] = {}
    cleaned = "\n".join(line.split("#", 1)[0] for line in text.splitlines())

    i = 0
    while i < len(cleaned):
        m = REGION_HEADER_RE.search(cleaned, i)
        if not m:
            break
        region_name = m.group(1)
        depth = 1
        j = m.end()
        while j < len(cleaned) and depth > 0:
            c = cleaned[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            j += 1
        body = cleaned[m.end():j - 1]
        sm = STATES_BLOCK_RE.search(body)
        if sm:
            out[region_name] = STATE_TOKEN_RE.findall(sm.group(1))
        i = j
    return out


def load_all_strategic_regions() -> dict[str, list[str]]:
    table: dict[str, list[str]] = {}
    for f in sorted(STRATEGIC_REGIONS_DIR.glob("*.txt")):
        text = f.read_text(encoding="utf-8-sig", errors="replace")
        for region, states in parse_region_to_states(text).items():
            if region in table:
                raise RuntimeError(f"duplicate strategic region {region} in {f.name}")
            table[region] = states
    return table


def expand_formable(region_table: dict[str, list[str]], srs: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for sr in srs:
        if sr not in region_table:
            raise RuntimeError(f"strategic region {sr} not found in vanilla data (sources: {sorted(region_table)[:5]}...)")
        for st in region_table[sr]:
            if st not in seen:
                seen.add(st)
                ordered.append(st)
    return ordered


HEADER = """\
# AUTO-GENERATED by scripts/generators/gen_formable_regions.py — do not hand-edit.
#
# Re-run the generator after vanilla strategic-region changes
# (see docs/guides/vanilla_patch_runbook.md).
#
# These are the state-list-form geographic_regions used by the mod's EUN /
# AFU / UNA / UNE formables. The Vic3 formable engine only reads
# `state_regions = {...}` from a geographic region, so vanilla
# `geographic_region_europe` / `geographic_region_africa` (which use
# `strategic_regions = {...}`) cannot drive a formable's required-states list.
# This file is the explicit-state-list replacement.

"""


def render(formable_regions, region_table) -> str:
    out = [HEADER]
    for name, short_key, srs in formable_regions:
        states = expand_formable(region_table, srs)
        out.append(f"{name} = {{\n")
        out.append(f'\tshort_key = "{short_key}"\n\n')
        out.append("\tstate_regions = {\n")
        for i in range(0, len(states), 8):
            chunk = " ".join(states[i:i + 8])
            out.append(f"\t\t{chunk}\n")
        out.append("\t}\n")
        out.append("}\n\n")
    return "".join(out)


def main():
    region_table = load_all_strategic_regions()
    print(
        f"Loaded {len(region_table)} strategic regions from {STRATEGIC_REGIONS_DIR}",
        file=sys.stderr,
    )
    text = render(FORMABLE_REGIONS, region_table)
    if "--dry-run" in sys.argv:
        sys.stdout.write(text)
        return
    OUTPUT_FILE.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    summary = ", ".join(
        f"{name}={len(expand_formable(region_table, srs))}"
        for name, _, srs in FORMABLE_REGIONS
    )
    print(f"Wrote {OUTPUT_FILE}", file=sys.stderr)
    print(f"  {summary}", file=sys.stderr)


if __name__ == "__main__":
    main()
