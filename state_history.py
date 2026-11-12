"""Who owns each state at game start: `common/history/states` (#901).

The history files are effect scripts, not entity tables: one `STATES = { }`
block per file, one `s:STATE_X = { }` per state region inside it, and one
`create_state = { country = c:TAG owned_provinces = { … } }` per country that
holds part of the region. ModState's top-level merge is last-wins by key, so
it would keep one `STATES` block and say nothing about the rest; this module
reads the files on their own instead and leaves the parser's merge alone.

    by_file = parse_dir(".../game/common/history/states")
    states = merge(by_file)                    # {state: record}
    describe("STATE_RAJPUTANA", states["STATE_RAJPUTANA"], hubs)

A record is plain JSON:

    {"parts": [{"country": "JAI", "provinces": ["x604D2F", …],
                "state_types": ["unincorporated"]}],     # key only when set
     "homelands": ["rajput"], "claims": ["GBR"]}

`parse_dir` keeps the file each record came from (`{file name: {state:
record}}`), because the engine replaces a vanilla history file with a mod
file of the same name and runs every other file as well: `merge(vanilla,
mod)` applies exactly that. Within the merged order a second `s:STATE_X`
block adds its parts, homelands and claims to the first, as the effects
would.

`vanilla_parsed.py` snapshots `parse_dir`'s result for vanilla
(`vanilla_parsed/history/states.json`), so the lookup works with no game
install. The hub provinces (city, port, farm, mine, wood) come from
`map_data/state_regions`, which the mod ships whole, and say which part of a
split state holds its city.

CLI (the game files when the machine has them, else the snapshot):

    python3 state_history.py STATE_RAJPUTANA        # one state's parts
    python3 state_history.py --country RUS          # what a tag owns at start
    python3 state_history.py --summary              # counts
"""
from __future__ import annotations

import argparse
import codecs
import json
import os
import sys
from typing import Iterable, Iterator, Optional

from mod_state import iter_script_files
from paradox_file_parser import ParadoxFileParser

# Relative to a game root (`<install>/game`) or to the mod root.
REL_DIR = "common/history/states"
STATE_REGIONS_REL_DIR = "map_data/state_regions"
HUBS = ("city", "port", "farm", "mine", "wood")


def _unquote(token):
    return token.strip('"') if isinstance(token, str) else token


def _entries(block) -> Iterator[tuple[str, object]]:
    """(key, value) pairs of a raw parsed block, in source order. The parser
    returns a dict when every key is unique and a list of single-key dicts
    when one repeats (`create_state`, `add_homeland`)."""
    items = [block] if isinstance(block, dict) else block if isinstance(block, list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        for key, pair in item.items():
            value = pair[1] if isinstance(pair, tuple) and len(pair) == 2 else pair
            yield _unquote(key), value


def _raw_parse(text: str):
    parser = ParadoxFileParser()
    return parser.parse_object(parser.tokenize("{" + text + "}"))[0]


def _strip_scope(token, prefix: str) -> Optional[str]:
    """`c:RUS` -> `RUS`; None for anything that is not a plain `prefix:` link."""
    token = _unquote(token)
    if not isinstance(token, str):
        return None
    return token[len(prefix):] if token.startswith(prefix) else token


def province_id(token) -> Optional[str]:
    """A province id in one spelling: `x` and six upper-case hex digits.
    Vanilla writes them in either case, quoted or bare."""
    token = _unquote(token)
    if not isinstance(token, str) or len(token) < 2 or token[0] not in "xX":
        return None
    return "x" + token[1:].upper()


def _new_record() -> dict:
    return {"parts": [], "homelands": [], "claims": []}


def _add_state(record: dict, body) -> None:
    for key, value in _entries(body):
        if key == "create_state":
            part = {"country": None, "provinces": []}
            types = []
            for k, v in _entries(value):
                if k == "country":
                    part["country"] = _strip_scope(v, "c:")
                elif k == "owned_provinces" and isinstance(v, list):
                    part["provinces"].extend(p for p in map(province_id, v) if p)
                elif k == "state_type" and isinstance(_unquote(v), str):
                    types.append(_unquote(v))
            if types:
                part["state_types"] = types
            record["parts"].append(part)
        elif key == "add_homeland":
            culture = _strip_scope(value, "cu:")
            if culture and culture not in record["homelands"]:
                record["homelands"].append(culture)
        elif key == "add_claim":
            tag = _strip_scope(value, "c:")
            if tag and tag not in record["claims"]:
                record["claims"].append(tag)


def parse_text(text: str) -> dict[str, dict]:
    """{state: record} for one history file's text. Every `STATES` block in
    the file counts, and a state named twice keeps both blocks' content."""
    states: dict[str, dict] = {}
    for key, block in _entries(_raw_parse(text)):
        if key != "STATES":
            continue
        for state_key, body in _entries(block):
            name = _strip_scope(state_key, "s:")
            if not name or not name.startswith("STATE_"):
                continue
            _add_state(states.setdefault(name, _new_record()), body)
    return states


def _read(path: str) -> str:
    with codecs.open(path, "r", "utf-8-sig") as f:
        return f.read()


def source_files(dir_path: str) -> list[str]:
    """The files `parse_dir` reads, in the order it reads them."""
    return list(iter_script_files(dir_path)) if os.path.isdir(dir_path) else []


def parse_dir(dir_path: str) -> dict[str, dict]:
    """{file name: {state: record}} for every history file under `dir_path`,
    in sorted name order. A missing directory is an empty table. A file that
    does not parse raises: a partial start map would read as a real one."""
    by_file: dict[str, dict] = {}
    for path in source_files(dir_path):
        rel = os.path.relpath(path, dir_path).replace(os.sep, "/")
        by_file[rel] = parse_text(_read(path))
    return by_file


def merge(*layers: Optional[dict]) -> dict[str, dict]:
    """{state: record} from `parse_dir` tables, vanilla first. A later
    layer's file replaces an earlier layer's file of the same name (the
    engine's rule for a mod file at a vanilla path); the surviving files then
    apply in name order, each adding to what came before."""
    files: dict[str, dict] = {}
    for layer in layers:
        files.update(layer or {})
    states: dict[str, dict] = {}
    for name in sorted(files):
        for state, rec in files[name].items():
            out = states.setdefault(state, _new_record())
            out["parts"].extend(json.loads(json.dumps(rec.get("parts", []))))
            for field in ("homelands", "claims"):
                out[field].extend(v for v in rec.get(field, []) if v not in out[field])
    return states


# ---------------------------------------------------------------------------
# Hub provinces (map_data/state_regions)
# ---------------------------------------------------------------------------

def state_regions(*dirs: Optional[str]) -> dict[str, dict]:
    """{state: {"provinces": [...], "hubs": {hub: province}}} from
    `map_data/state_regions` directories, vanilla first: a later directory's
    file replaces an earlier one's file of the same name, which is how the
    mod's copies (it ships every land and sea file) stand in for vanilla's."""
    files: dict[str, str] = {}
    for d in dirs:
        if d and os.path.isdir(d):
            for path in iter_script_files(d):
                files[os.path.relpath(path, d).replace(os.sep, "/")] = path
    out: dict[str, dict] = {}
    for name in sorted(files):
        for key, body in _entries(_raw_parse(_read(files[name]))):
            if not key.startswith("STATE_"):
                continue
            region = {"provinces": [], "hubs": {}}
            for k, v in _entries(body):
                if k == "provinces" and isinstance(v, list):
                    region["provinces"] = [p for p in map(province_id, v) if p]
                elif k in HUBS:
                    p = province_id(v)
                    if p:
                        region["hubs"][k] = p
            out[key] = region
    return out


# ---------------------------------------------------------------------------
# Answers
# ---------------------------------------------------------------------------

def describe(state: str, record: dict, regions: Optional[dict] = None, *,
             provinces: bool = False) -> dict:
    """One state at game start, in the `/state-history/<STATE_X>` shape.
    `hubs` names the hub provinces a part owns, so "who holds the city of a
    split state" is the part whose `hubs` has `city`. `unowned_hubs` and
    `unowned_provinces` cover land no country starts with.

    Vanilla's file lists some provinces under two countries of one state (16
    states in 1.15.1, New Mexico and the North Caucasus among them). Which
    one the engine keeps is not verified, so such a province counts for both
    parts, a hub on it shows under both, and `double_listed_provinces` (only
    present when not zero) says how many there are."""
    region = (regions or {}).get(state)
    hubs = (region or {}).get("hubs", {})
    parts = []
    owned: set[str] = set()
    double: set[str] = set()
    for part in record.get("parts", []):
        mine = set(part.get("provinces", []))
        double |= owned & mine
        owned |= mine
        row = {
            "country": part.get("country"),
            "provinces": len(part.get("provinces", [])),
            "hubs": [h for h in HUBS if hubs.get(h) in mine],
        }
        if part.get("state_types"):
            row["state_types"] = list(part["state_types"])
        if provinces:
            row["province_ids"] = list(part.get("provinces", []))
        parts.append(row)
    out = {
        "state": state,
        "split": len(parts) > 1,
        "parts": parts,
        "homelands": list(record.get("homelands", [])),
        "claims": list(record.get("claims", [])),
    }
    if double:
        out["double_listed_provinces"] = len(double)
    if region is not None:
        out["unowned_hubs"] = [h for h in HUBS if h in hubs and hubs[h] not in owned]
        out["unowned_provinces"] = len(set(region["provinces"]) - owned)
    return out


def owned_by(states: dict[str, dict], tag: str, regions: Optional[dict] = None) -> list[dict]:
    """The states (and, for a split state, the part) `tag` owns at start."""
    rows = []
    for state in sorted(states):
        full = describe(state, states[state], regions)
        for part in full["parts"]:
            if part["country"] == tag:
                rows.append({
                    "state": state, "split": full["split"],
                    "provinces": part["provinces"], "hubs": part["hubs"],
                    **({"state_types": part["state_types"]} if "state_types" in part else {}),
                    "other_owners": sorted({p["country"] for p in full["parts"]
                                            if p["country"] != tag}),
                })
    return rows


def summary(states: dict[str, dict]) -> dict:
    owners = {p.get("country") for r in states.values() for p in r.get("parts", [])}
    return {
        "states": len(states),
        "parts": sum(len(r.get("parts", [])) for r in states.values()),
        "split_states": sum(1 for r in states.values() if len(r.get("parts", [])) > 1),
        "unowned_states": sum(1 for r in states.values() if not r.get("parts")),
        "countries": len(owners - {None}),
    }


# ---------------------------------------------------------------------------
# Loading for a tool run outside the server
# ---------------------------------------------------------------------------

def load(game_root: Optional[str] = None, mod_root: Optional[str] = None,
         snapshot_dir: Optional[str] = None) -> tuple[dict[str, dict], dict[str, dict], str]:
    """(states, regions, source): the merged start map, the hub table and
    where vanilla came from (`game_files` or `vanilla_parsed`). Vanilla is
    read from `<game_root>/game` when that has the history folder, else from
    the committed snapshot; the mod's own history files, if it ever ships
    any, layer on top either way."""
    import vanilla_parsed

    vanilla_dir = os.path.join(game_root, "game", *REL_DIR.split("/")) if game_root else None
    if vanilla_dir and os.path.isdir(vanilla_dir):
        vanilla, source = parse_dir(vanilla_dir), "game_files"
    else:
        snap = vanilla_parsed.load_state_history(snapshot_dir or vanilla_parsed.DEFAULT_DIR)
        if snap is None:
            raise FileNotFoundError(
                "no vanilla state history: no game files, and vanilla_parsed/ has none "
                "(rebuild with `python3 vanilla_parsed.py build` on a machine with the game)"
            )
        vanilla, source = snap, "vanilla_parsed"
    mod = parse_dir(os.path.join(mod_root, *REL_DIR.split("/"))) if mod_root else {}
    regions = state_regions(
        os.path.join(game_root, "game", *STATE_REGIONS_REL_DIR.split("/")) if game_root else None,
        os.path.join(mod_root, *STATE_REGIONS_REL_DIR.split("/")) if mod_root else None,
    )
    return merge(vanilla, mod), regions, source


def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Who owns a state at game start (vanilla history/states).")
    ap.add_argument("state", nargs="?", help="a state region, e.g. STATE_RAJPUTANA")
    ap.add_argument("--country", help="list what this tag owns at start, e.g. RUS")
    ap.add_argument("--summary", action="store_true", help="print counts")
    ap.add_argument("--provinces", action="store_true", help="include each part's province ids")
    args = ap.parse_args(argv)

    import path_constants
    try:
        game_root = path_constants.base_game_path
    except RuntimeError:
        game_root = None
    states, regions, source = load(game_root, path_constants.mod_path)
    if args.state:
        if args.state not in states:
            print(f"{args.state}: not in the start history", file=sys.stderr)
            return 1
        out = describe(args.state, states[args.state], regions, provinces=args.provinces)
    elif args.country:
        out = {"country": args.country, "states": owned_by(states, args.country, regions)}
    else:
        out = summary(states)
    out["vanilla_source"] = source
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
