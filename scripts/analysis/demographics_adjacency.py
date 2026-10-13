#!/usr/bin/env python3
"""Which state regions touch, for the demographics harness's neighbour spread (phase 3).

The census's practices spread from neighbouring states (`every_neighbouring_state`: Late Marriage and Birth Spacing
state to state, Family Limitation country to country over its border states). The harness needs the same adjacency
for a save's states, which name only their state region. The map itself (game/map_data/provinces.png, a colour per
province) isn't in the repo and CI has no game, so a snapshot sits beside this file:

    demographics_adjacency.py --refresh [--game-dir DIR]   # rewrite demographics_state_adjacency.json
    demographics_adjacency.py --check   [--game-dir DIR]   # exit 1 if a fresh build would differ

Two state regions are land neighbours when a pixel of one of their provinces touches a pixel of the other's, across
a row or a column (the map wraps east to west). The province lists are the mod's copy of map_data/state_regions (the
game reads it in place of the base game's); seas are left out. The straits in game/map_data/adjacencies.csv (type
`sea`: Ireland to Scotland and the like) are kept apart: whether the engine's iterator crosses them is unverified
(the late-marriage spec 4.4), so the replay leaves them out unless asked. Re-run --refresh after a vanilla patch that
moves a province (docs/guides/vanilla_patch_runbook.md).
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = Path(__file__).resolve().parent / "demographics_state_adjacency.json"
STATE_REGIONS = ROOT / "map_data" / "state_regions"

_STATE_BLOCK = re.compile(r"^(STATE_[A-Z0-9_]+)\s*=\s*\{", re.M)
_PROVINCES = re.compile(r"\bprovinces\s*=\s*\{([^{}]*)\}")
_PROVINCE = re.compile(r"x[0-9A-Fa-f]{6}")


def province_regions(state_regions=STATE_REGIONS):
    """{province colour as 0xRRGGBB: state region} from the map files, seas left out."""
    out = {}
    for path in sorted(Path(state_regions).glob("*.txt")):
        if path.name == "99_seas.txt":
            continue
        text = path.read_text(encoding="utf-8-sig")
        heads = list(_STATE_BLOCK.finditer(text))
        for i, head in enumerate(heads):
            body = text[head.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
            m = _PROVINCES.search(body)
            if not m:
                continue
            for prov in _PROVINCE.findall(m.group(1)):
                out[int(prov[1:], 16)] = head.group(1)
    return out


def _game_dir(arg=None):
    if arg:
        return Path(arg)
    sys.path.insert(0, str(ROOT))
    import path_constants
    return Path(path_constants.base_game_path) / "game"


def land_pairs(png, regions):
    """{(a, b)} of state regions whose provinces touch on the map (a < b)."""
    import numpy as np
    from PIL import Image
    img = np.asarray(Image.open(png).convert("RGB"), dtype=np.uint32)
    colour = (img[:, :, 0] << 16) | (img[:, :, 1] << 8) | img[:, :, 2]
    keys = set()
    for a, b in ((colour[:, :-1], colour[:, 1:]), (colour[:-1, :], colour[1:, :]), (colour[:, -1:], colour[:, :1])):
        diff = a != b
        pairs = np.unique((a[diff].astype(np.uint64) << np.uint64(24)) | b[diff].astype(np.uint64))
        keys.update(int(k) for k in pairs)
    out = set()
    for k in keys:
        ra, rb = regions.get(k >> 24), regions.get(k & 0xFFFFFF)
        if ra and rb and ra != rb:
            out.add(tuple(sorted((ra, rb))))
    return out


def strait_pairs(adjacencies, regions):
    """{(a, b)} of state regions joined by a `sea` crossing in adjacencies.csv (a < b)."""
    out = set()
    with open(adjacencies, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            if (row.get("Type") or "").strip() != "sea":
                continue
            try:
                ra = regions.get(int(row["From"].strip()[1:], 16))
                rb = regions.get(int(row["To"].strip()[1:], 16))
            except (KeyError, ValueError):
                continue
            if ra and rb and ra != rb:
                out.add(tuple(sorted((ra, rb))))
    return out


def build(game_dir):
    regions = province_regions()
    land = land_pairs(Path(game_dir) / "map_data" / "provinces.png", regions)
    strait = strait_pairs(Path(game_dir) / "map_data" / "adjacencies.csv", regions) - land

    def table(pairs):
        out = {}
        for a, b in sorted(pairs):
            out.setdefault(a, []).append(b)
            out.setdefault(b, []).append(a)
        return {k: sorted(v) for k, v in sorted(out.items())}

    return {"land": table(land), "strait": table(strait)}


def load(path=SNAPSHOT):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def neighbours(snapshot=None, straits=False):
    """{state region: set of its neighbouring state regions}: land, and the straits if asked."""
    snap = load() if snapshot is None else snapshot
    out = {k: set(v) for k, v in snap["land"].items()}
    if straits:
        for k, v in snap["strait"].items():
            out.setdefault(k, set()).update(v)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--refresh", action="store_true")
    mode.add_argument("--check", action="store_true")
    ap.add_argument("--game-dir", help="the base game's game/ folder (default: path_constants)")
    args = ap.parse_args(argv)
    fresh = build(_game_dir(args.game_dir))
    text = json.dumps(fresh, indent=1, sort_keys=True) + "\n"
    if args.refresh:
        SNAPSHOT.write_text(text, encoding="utf-8")
        print(f"{SNAPSHOT.name}: {len(fresh['land'])} state regions with land neighbours, "
              f"{sum(len(v) for v in fresh['strait'].values()) // 2} straits")
        return 0
    same = SNAPSHOT.exists() and SNAPSHOT.read_text(encoding="utf-8") == text
    print("up to date" if same else f"{SNAPSHOT.name} is stale: run --refresh")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
