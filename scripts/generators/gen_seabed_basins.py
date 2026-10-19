"""Generate the seabed basin of every coastal state (Global Commons, spec § 2.1).

No trigger reads which sea a coastal state faces, but every coastal land state
in ``map_data/state_regions/*.txt`` names one sea region as its
``naval_exit_id``, the ``id`` of a block in ``99_seas.txt``. This maps state ->
sea region -> basin offline and writes one effect:

* ``common/scripted_effects/te_seabed_basins_generated.txt``:
  ``te_seabed_set_state_basin`` (state scope) sets the state variable
  ``te_seabed_basin`` to the basin's number, from an ``if`` / ``else_if``
  chain on ``state_region = s:STATE_X`` (one ``OR`` per basin).

Basin numbers (``BASINS``; the script's ``$N$`` and the display read them):
1 Pacific, 2 Atlantic, 3 Indian, 4 Arctic, 5 Southern. The order is the spec's
§ 2.1 list; the pools (§ 2.2) are separate script values, so the numbering
carries no weight.

The mod ships the full set of state region files (``resources.py`` rewrites
all 17 of vanilla's, docs/auto_generated_files.md), so the mod's files are
the whole map: no vanilla region is left out.

Run ``python3 scripts/generators/gen_seabed_basins.py [--dry-run | --check]``.
No game install or running server is needed. Full server reloads call
``regenerate`` (mod_state_server.POST_LOAD_REGENERATORS).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STATE_REGIONS = Path("map_data/state_regions")
SEAS_FILE = STATE_REGIONS / "99_seas.txt"
OUT = Path("common/scripted_effects/te_seabed_basins_generated.txt")

# Basin number -> key. The keys name the variables (te_seabed_unbuilt_<key>,
# te_seabed_held_<key>, te_seabed_lic_<key>) and the pool script values.
BASINS = {1: "pacific", 2: "atlantic", 3: "indian", 4: "arctic", 5: "southern"}

# Every sea region in 99_seas.txt -> basin key. The spec (§ 2.1) fixes the
# named seas; the rest follow the real ocean. "unused" = no land state names
# it as its naval exit (85 of the 106 are used), so its basin decides nothing
# today; it is listed so that a map change that starts using it is mapped.
#
# Borderline calls, checked against the states that use each sea:
# - BERING_SEA (Chukotka): a marginal sea of the Pacific, not one of the
#   spec's Arctic seas, so Pacific, though Chukotka's real coast is mostly
#   Arctic. The naval exit decides.
# - HUDSON_BAY (Ontario, Manitoba, Nunavut): Arctic, as the spec says. The
#   game gives Ontario its naval exit there, so Ontario is an Arctic state.
# - DAVIS_STRAIT (Greenland), NORWEGIAN_SEA (Northern Norway), BARENTS_SEA
#   (East Karelia, Kola, Arkhangelsk, Nenetsia): Arctic, per the spec.
# - NORTHERN_NORTH_ATLANTIC_OCEAN (Iceland), GRAND_BANKS (Newfoundland),
#   LABRADOR_SEA (unused): Atlantic. Not in the spec's Arctic list.
# - MALACCA_STRAIT (Tenasserim, Pegu, Aceh): Indian. The three coasts face the
#   Andaman Sea, an arm of the Indian Ocean.
# - MALAY_SEA (Cambodia, Bangkok, Mekong, Nakhon Ratchasima, Malaya, North and
#   West Borneo): Pacific, the Gulf of Thailand and the southern South China
#   Sea.
# - JAVA_SEA (East Borneo, the three Java states, Sunda Islands) and
#   MOLUCCA_SEA (Western New Guinea, Moluccas, Celebes, Mindanao, Northern
#   Territory): Pacific. The seas of the Indonesian archipelago belong to the
#   western Pacific; Java's and the Northern Territory's south coasts face the
#   Indian Ocean, but their naval exits are these seas.
# - EASTERN_INDIAN_OCEAN (North and South Sumatra) and SOUTH_INDIAN_OCEAN
#   (Western Australia): Indian.
# - CAPE_OF_GOOD_HOPE (Zululand, Eastern Cape, Cape Colony): Southern, per the
#   spec, Zululand included, since it shares the naval exit.
# - TASMAN_SEA (New South Wales, Victoria, Tasmania, North Island) and
#   GREAT_AUSTRALIAN_BIGHT (South Australia): Southern, per the spec.
# - WESTERN_POLYNESIAN_SEA (Fiji, Tonga, South Island): Pacific. New Zealand's
#   South Island exits there, not to the Tasman Sea.
# - PATAGONIAN_SEA (Patagonia, South Atlantic Islands) and PATAGONIAN_CHANNELS
#   (Araucania): Southern, per the spec. Uruguay and Buenos Aires (RIVER_PLATE)
#   stay Atlantic.
# - BENGUELA_COAST (Congo to Hereroland): Atlantic.
# - SOUTHERN_BIGHT (Midlands, East Anglia, the Low Countries, Elbe, Hannover):
#   the southern North Sea, so Atlantic.
# - MAIN_EQUATORIAL_CRURRENT (unused): Atlantic. Vanilla's hurricane season
#   (harvest_condition_types, cyclone) groups it with the Cape Verde Sea and
#   the Equatorial Atlantic.
# - SOUTHERN_ATLANTIC_CRURRENT and SOUTH_ATLANTIC_OCEAN (both unused):
#   Atlantic, by name. SOUTHERN_OCEAN_01/02 (unused): Southern.
SEA_BASIN = {
    # Pacific
    "STATE_MICRONESIAN_SEA": "pacific",
    "STATE_EQUATORIAL_PACIFIC_OCEAN": "pacific",        # unused
    "STATE_NORTH_PACIFIC_OCEAN": "pacific",             # unused
    "STATE_NORTHEAST_PACIFIC_OCEAN": "pacific",         # unused
    "STATE_NORTHWEST_PACIFIC_OCEAN": "pacific",
    "STATE_SOUTH_PACIFIC_OCEAN": "pacific",             # unused
    "STATE_GALAPAGOS_RISE": "pacific",
    "STATE_BERING_SEA": "pacific",
    "STATE_GULF_OF_ALASKA": "pacific",
    "STATE_INSIDE_PASSAGE": "pacific",
    "STATE_PACIFIC_SEABOARD": "pacific",
    "STATE_CENTROAMERICAN_SEA": "pacific",
    "STATE_PERUVIAN_SEA": "pacific",
    "STATE_SEA_OF_OKHOTSK": "pacific",
    "STATE_SEA_OF_JAPAN": "pacific",
    "STATE_JAPAN_CURRENT": "pacific",
    "STATE_YELLOW_SEA": "pacific",
    "STATE_EAST_CHINA_SEA": "pacific",
    "STATE_SOUTH_CHINA_SEA": "pacific",
    "STATE_MALAY_SEA": "pacific",
    "STATE_JAVA_SEA": "pacific",
    "STATE_MOLUCCA_SEA": "pacific",
    "STATE_PHILIPPINES_SEA": "pacific",
    "STATE_CORAL_SEA": "pacific",
    "STATE_NORTHERN_POLYNESIAN_SEA": "pacific",
    "STATE_EASTERN_POLYNESIA": "pacific",
    "STATE_WESTERN_POLYNESIAN_SEA": "pacific",
    # Atlantic, with the Mediterranean, Black Sea, Baltic, North Sea,
    # Caribbean and Gulf of Mexico
    "STATE_NORTHERN_BALTIC_SEA": "atlantic",
    "STATE_SOUTHERN_BALTIC_SEA": "atlantic",
    "STATE_GULF_OF_FINLAND": "atlantic",
    "STATE_BALTIC_ENTRANCES": "atlantic",
    "STATE_NORTH_SEA": "atlantic",
    "STATE_SOUTHERN_BIGHT": "atlantic",
    "STATE_ENGLISH_CHANNEL": "atlantic",
    "STATE_CELTIC_SEA": "atlantic",
    "STATE_IRISH_SEA": "atlantic",
    "STATE_BAY_OF_BISCAY": "atlantic",
    "STATE_LUSITANIAN_SEA": "atlantic",
    "STATE_WESTERN_MEDITERRANEAN_SEA": "atlantic",
    "STATE_BALEARIC_SEA": "atlantic",
    "STATE_TYRRHENIAN_SEA": "atlantic",
    "STATE_CENTRAL_MEDITERRANEAN_SEA": "atlantic",
    "STATE_ADRIATIC_SEA": "atlantic",
    "STATE_AEGEAN_SEA": "atlantic",
    "STATE_EASTERN_MEDITERRANEAN_SEA": "atlantic",
    "STATE_SEA_OF_MARMARA": "atlantic",
    "STATE_WESTERN_BLACK_SEA": "atlantic",
    "STATE_EASTERN_BLACK_SEA": "atlantic",
    "STATE_NORTH_ATLANTIC_OCEAN": "atlantic",
    "STATE_NORTHERN_NORTH_ATLANTIC_OCEAN": "atlantic",
    "STATE_NORTH_ATLANTIC_CURRENT": "atlantic",         # unused
    "STATE_LABRADOR_SEA": "atlantic",                   # unused
    "STATE_GRAND_BANKS": "atlantic",
    "STATE_GULF_OF_SAINT_LAWRENCE": "atlantic",
    "STATE_NORTHEAST_ATLANTIC_COAST": "atlantic",
    "STATE_MID_ATLANTIC_COAST": "atlantic",
    "STATE_SOUTH_ATLANTIC_COAST": "atlantic",
    "STATE_SARGASSO_SEA": "atlantic",
    "STATE_BAHAMA_BANKS": "atlantic",
    "STATE_GULF_OF_MEXICO": "atlantic",
    "STATE_WESTERN_CARIBBEAN_SEA": "atlantic",
    "STATE_EASTERN_CARIBBEAN_SEA": "atlantic",
    "STATE_COAST_OF_GUYANA": "atlantic",
    "STATE_AMAZON_DELTA": "atlantic",
    "STATE_CAPE_ST_ROQUE": "atlantic",
    "STATE_SOUTH_BRAZIL_BIGHT": "atlantic",
    "STATE_RIVER_PLATE": "atlantic",
    "STATE_EQUATORIAL_ATLANTIC_OCEAN": "atlantic",      # unused
    "STATE_MAIN_EQUATORIAL_CRURRENT": "atlantic",       # unused
    "STATE_SOUTH_ATLANTIC_OCEAN": "atlantic",           # unused
    "STATE_SOUTHERN_ATLANTIC_CRURRENT": "atlantic",     # unused
    "STATE_CAPE_VERDE_SEA": "atlantic",
    "STATE_GUINEA_CURRENT": "atlantic",                 # unused
    "STATE_GULF_OF_GUINEA": "atlantic",
    "STATE_BENGUELA_COAST": "atlantic",
    # Indian, with the Red Sea, Persian Gulf and Arabian Sea
    "STATE_RED_SEA": "indian",
    "STATE_PERSIAN_GULF": "indian",
    "STATE_ARABIAN_SEA": "indian",
    "STATE_HORN_OF_AFRICA": "indian",
    "STATE_LACCADIVE_SEA": "indian",
    "STATE_BAY_OF_BENGAL": "indian",
    "STATE_MALACCA_STRAIT": "indian",
    "STATE_EASTERN_INDIAN_OCEAN": "indian",
    "STATE_SOUTH_INDIAN_OCEAN": "indian",
    "STATE_WESTERN_INDIAN_OCEAN": "indian",
    "STATE_ZANZIBAR_COAST": "indian",
    "STATE_MOZAMBIQUE_CHANNEL": "indian",
    # Arctic
    "STATE_BARENTS_SEA": "arctic",
    "STATE_KARA_SEA": "arctic",                         # unused
    "STATE_LAPTEV_SEA": "arctic",                       # unused
    "STATE_EAST_SIBERIAN_SEA": "arctic",                # unused
    "STATE_CHUCKCHI_SEA": "arctic",                     # unused
    "STATE_BEAUFORT_SEA": "arctic",                     # unused
    "STATE_GREENLAND_SEA": "arctic",                    # unused
    "STATE_NORWEGIAN_SEA": "arctic",
    "STATE_NORTHWEST_PASSAGE": "arctic",                # unused
    "STATE_BAFFIN_BAY": "arctic",                       # unused
    "STATE_DAVIS_STRAIT": "arctic",
    "STATE_HUDSON_BAY": "arctic",
    # Southern
    "STATE_PATAGONIAN_SEA": "southern",
    "STATE_PATAGONIAN_CHANNELS": "southern",
    "STATE_CAPE_OF_GOOD_HOPE": "southern",
    "STATE_GREAT_AUSTRALIAN_BIGHT": "southern",
    "STATE_TASMAN_SEA": "southern",
    "STATE_SOUTHERN_OCEAN_01": "southern",              # unused
    "STATE_SOUTHERN_OCEAN_02": "southern",              # unused
}

_STATE_RE = re.compile(r"^(STATE_\w+)\s*=\s*\{", re.M)
_ID_RE = re.compile(r"\bid\s*=\s*(\d+)")
_EXIT_RE = re.compile(r"\bnaval_exit_id\s*=\s*(\d+)")

HEADER = (
    "# AUTO-GENERATED by scripts/generators/gen_seabed_basins.py - do not edit manually.\n"
    "# Global Commons, seabed basins: docs/superpowers/archive/specs/2026-10-16-global-commons-design.md § 2.1\n"
)
PREAMBLE = """\
# Scope: state. Sets the state variable te_seabed_basin to its basin, from the
# naval exit of its state region (map_data/state_regions/*.txt -> 99_seas.txt
# -> the generator's SEA_BASIN table): 1 Pacific, 2 Atlantic, 3 Indian,
# 4 Arctic, 5 Southern. A landlocked state matches no branch and gets no
# variable. Called by te_seabed_ensure_state_basin
# (te_global_commons_seabed_effects.txt) for coastal states without the
# variable: the yearly pass and any recording that meets one (conquest and
# splits make new state scopes).
"""


def _blocks(text: str):
    """(name, body) of each top-level ``STATE_X = { ... }`` block."""
    starts = list(_STATE_RE.finditer(text))
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        yield m.group(1), text[m.end():end]


def read_seas(root: Path = ROOT) -> dict[int, str]:
    """Sea region id -> its STATE_ key, from 99_seas.txt."""
    text = (root / SEAS_FILE).read_text(encoding="utf-8-sig")
    seas = {}
    for name, body in _blocks(text):
        m = _ID_RE.search(body)
        if m:
            seas[int(m.group(1))] = name
    return seas


def read_naval_exits(root: Path = ROOT) -> dict[str, list[int]]:
    """Land state region -> the naval exit ids its block names (empty if landlocked)."""
    exits = {}
    for path in sorted((root / STATE_REGIONS).glob("*.txt")):
        if path.name == SEAS_FILE.name:
            continue
        for name, body in _blocks(path.read_text(encoding="utf-8-sig")):
            exits[name] = [int(n) for n in _EXIT_RE.findall(body)]
    return exits


def state_basins(root: Path = ROOT) -> dict[str, int]:
    """Coastal land state region -> basin number. Raises on an unmapped sea or
    a state with more than one naval exit."""
    seas = read_seas(root)
    number = {key: n for n, key in BASINS.items()}
    out = {}
    for state, ids in read_naval_exits(root).items():
        if not ids:
            continue
        if len(ids) > 1:
            raise ValueError(f"{state} names {len(ids)} naval exits")
        sea = seas.get(ids[0])
        if sea is None:
            raise ValueError(f"{state}: naval_exit_id {ids[0]} is no sea region in {SEAS_FILE}")
        if sea not in SEA_BASIN:
            raise ValueError(f"{state}: sea region {sea} has no basin in SEA_BASIN")
        out[state] = number[SEA_BASIN[sea]]
    return out


def render(basins: dict[str, int]) -> str:
    lines = [HEADER, PREAMBLE]
    counts = ", ".join(f"{BASINS[n].capitalize()} {sum(1 for b in basins.values() if b == n)}"
                       for n in BASINS)
    lines.append(f"# {len(basins)} coastal state regions: {counts}.\n")
    lines.append("te_seabed_set_state_basin = {\n")
    for i, (n, key) in enumerate(BASINS.items()):
        states = sorted(s for s, b in basins.items() if b == n)
        opener = "if" if i == 0 else "else_if"
        lines.append(f"\t{opener} = {{\n")
        lines.append(f"\t\tlimit = {{  # {key.capitalize()}\n")
        lines.append("\t\t\tOR = {\n")
        lines.extend(f"\t\t\t\tstate_region = s:{s}\n" for s in states)
        lines.append("\t\t\t}\n")
        lines.append("\t\t}\n")
        lines.append(f"\t\tset_variable = {{ name = te_seabed_basin value = {n} }}\n")
        lines.append("\t}\n")
    lines.append("}\n")
    return "".join(lines)


def plan_outputs(root: Path = ROOT) -> dict[Path, str]:
    return {OUT: render(state_basins(root))}


def regenerate(mod_state=None, *, root: Path = ROOT, dry_run: bool = False) -> dict:
    """Post-load entry point (mod_state_server.POST_LOAD_REGENERATORS) and CLI body.

    Reads only the map files; `mod_state` is unused. Writes the file only when
    its content changed, with one UTF-8 BOM.
    """
    changed = []
    for relative, text in plan_outputs(root).items():
        target = root / relative
        expected = text.encode("utf-8-sig")
        if not target.exists() or target.read_bytes() != expected:
            changed.append(str(relative))
            if not dry_run:
                target.write_bytes(expected)
    return {"changed": bool(changed), "changed_files": changed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="report what would change; write nothing")
    mode.add_argument("--check", action="store_true", help="exit 1 if the output is stale")
    args = parser.parse_args()
    result = regenerate(dry_run=args.dry_run or args.check)
    verb = "stale" if args.check else "would write" if args.dry_run else "wrote"
    for path in result["changed_files"]:
        print(f"{verb}: {path}")
    if not result["changed"]:
        print("seabed basins: current")
    return int(args.check and result["changed"])


if __name__ == "__main__":
    sys.exit(main())
