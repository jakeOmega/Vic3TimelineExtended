#!/usr/bin/env python3
"""Where every Grand Monument landmark stands in a binary save (log triage 2026-11-06).

A state's own monument keeps its records on the state (`gm_landmark`). A monument beside another and a trophy are
script containers, listed on the state they stand in (`gm_monuments_here`, `gm_trophies_here`) and naming their
landmark in `gm_tr_landmark`. A census of `gm_landmark` alone counts those as gone: on 2026-11-06 it called 16
landmarks lost by 1893, and six of them still stood as trophies or beside another monument.

    python3 scripts/analysis/gm_landmark_census.py <save.v3> [--placed <debug.log> ...]

prints one line per landmark: `own`, `beside` or `trophy`, then the state and its owner. With `--placed`, the
`TE_MONUMENTS: landmark X placed` lines of a session's logs (the 1836 placement) give the full roster, and every
landmark placed but found nowhere is listed as `nowhere`. About 5 s a save: the states come from
save_country_probe.py, and each container is found by its header in the gamestate.
"""
import argparse
import re
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import save_country_probe as probe  # noqa: E402
from check_save_history_order import read_gamestate  # noqa: E402

STATE_LINE = re.compile(r"\s+(state#\d+ \S+, owner \S+)")
LANDMARK_LINE = re.compile(r"\s+gm_landmark = flag:(\S+)")
LIST_LINE = re.compile(r"\s+(gm_monuments_here|gm_trophies_here) = (.*)")
PLACED = re.compile(r"TE_MONUMENTS: landmark ([a-z0-9_]+) placed")
KIND = {"gm_monuments_here": "beside", "gm_trophies_here": "trophy"}


def states_text(save):
    out = subprocess.run([sys.executable, str(HERE / "save_country_probe.py"), "--states", "--var", "^gm_", save],
                         capture_output=True, text=True, check=True)
    return out.stdout


def read_states(text):
    """([(landmark, "own", state)], {container id: (kind, state)}) from the probe's --states output."""
    own, containers, state = [], {}, None
    for line in text.splitlines():
        m = STATE_LINE.match(line)
        if m:
            state = m.group(1)
            continue
        m = LANDMARK_LINE.match(line)
        if m:
            own.append((m.group(1), "own", state))
            continue
        m = LIST_LINE.match(line)
        if m:
            for cid in re.findall(r"container#(\d+)", m.group(2)):
                containers[int(cid)] = (KIND[m.group(1)], state)
    return own, containers


def container_landmark(blob, cid):
    """The container's gm_tr_landmark, None when it has none, or "?" when its record isn't found."""
    at = blob.find(b"\x14\x00" + struct.pack("<I", cid) + b"\x01\x00\x03\x00\x55\x05")
    if at < 0:
        return "?"
    items, _ = probe.parse_block(blob, at)
    value = probe.read_variables(items).get("gm_tr_landmark")
    return value[5:] if isinstance(value, str) and value.startswith("flag:") else None


def census(save):
    own, containers = read_states(states_text(save))
    blob = read_gamestate(save)
    rows = list(own)
    for cid, (kind, state) in sorted(containers.items()):
        name = container_landmark(blob, cid)
        if name == "?":
            rows.append((f"container#{cid} (record not found)", kind, state))
        elif name:
            rows.append((name, kind, state))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("save")
    ap.add_argument("--placed", nargs="+", default=[], help="debug logs holding the session's placement lines")
    args = ap.parse_args(argv)
    rows = census(args.save)
    for name, kind, state in sorted(rows):
        print(f"{kind}\t{name}\t{state}")
    if args.placed:
        placed = set()
        for log in args.placed:
            placed.update(PLACED.findall(Path(log).read_text(encoding="utf-8", errors="replace")))
        for name in sorted(placed - {r[0] for r in rows}):
            print(f"nowhere\t{name}\t-")
    return 0


if __name__ == "__main__":
    sys.exit(main())
