"""
Mod State Client - CLI helper for querying the mod-state server.

Usage:
    python mod_state_client.py status
    python mod_state_client.py laws
    python mod_state_client.py laws law_monarchy
    python mod_state_client.py localize law_monarchy
    python mod_state_client.py unlocalize Monarchy
    python mod_state_client.py search nuclear
    python mod_state_client.py technologies --era 5
    python mod_state_client.py raw Laws law_monarchy
    python mod_state_client.py keys Laws
    python mod_state_client.py references law_anarchy
    python mod_state_client.py tech-tree nuclear_energy
    python mod_state_client.py modifier-search goods_output
    python mod_state_client.py unlocked-by nuclear_energy
    python mod_state_client.py filter Technologies era era_5

Alternatively, query the server directly from PowerShell:
    Invoke-RestMethod http://localhost:8950/laws
    (Invoke-RestMethod http://localhost:8950/laws) | ConvertTo-Json -Depth 10
"""

import json
import sys
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

SERVER = "http://127.0.0.1:8950"


def query(endpoint: str):
    """Send a GET request to the mod-state server and return parsed JSON."""
    url = f"{SERVER}/{endpoint}"
    try:
        with urlopen(url) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError:
        print(
            "ERROR: Mod-state server is not running.\n"
            "Start it with:  python mod_state_server.py",
            file=sys.stderr,
        )
        sys.exit(1)


def _encode(text: str) -> str:
    return quote(text, safe="")


USAGE = """\
Usage: python mod_state_client.py <command> [args] [options]

Commands:
  status                       Server status
  entity-types                 List all entity type names
  keys <EntityType>            List entity IDs with names
  raw <EntityType> [id]        Raw parsed data
  localize <key>               Localize a game key
  unlocalize <text>            Reverse-localize display text
  search <query>               Search entities & localization
  laws [law_id]                Laws grouped by law group
  technologies [tech_id]       Technologies grouped by era
    --era N                      Filter to one era
  buildings [building_id]      Buildings with PM groups
  goods                        All goods
  combat-units                 Combat units grouped
  ideologies [ideology_id]     Ideologies
  references <key>             Find all entities referencing a key
  tech-tree <tech_id>          Prerequisite chain + unlocks
  modifier-search <pattern>    Find modifier fields matching pattern
  unlocked-by <tech_id>        All entities unlocked by a tech
  filter <Type> <field> [val]  Filter entities by field value

Server: python mod_state_server.py  (start once, query many times)
"""


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(USAGE)
        return

    cmd = args[0]
    rest = args[1:]

    # Parse named options
    options = {}
    positional = []
    i = 0
    while i < len(rest):
        if rest[i].startswith("--") and i + 1 < len(rest):
            options[rest[i].lstrip("-")] = rest[i + 1]
            i += 2
        else:
            positional.append(rest[i])
            i += 1

    endpoint = ""

    if cmd == "status":
        endpoint = "status"
    elif cmd == "entity-types":
        endpoint = "entity-types"
    elif cmd == "keys":
        if not positional:
            print("Usage: keys <EntityType>", file=sys.stderr)
            sys.exit(1)
        endpoint = f"keys/{_encode(positional[0])}"
    elif cmd == "raw":
        if not positional:
            endpoint = "raw"
        else:
            endpoint = "raw/" + "/".join(_encode(p) for p in positional)
    elif cmd == "localize":
        if not positional:
            print("Usage: localize <key>", file=sys.stderr)
            sys.exit(1)
        endpoint = f"localize/{_encode(positional[0])}"
    elif cmd == "unlocalize":
        if not positional:
            print("Usage: unlocalize <display_text>", file=sys.stderr)
            sys.exit(1)
        endpoint = f"unlocalize/{_encode(positional[0])}"
    elif cmd == "search":
        if not positional:
            print("Usage: search <query>", file=sys.stderr)
            sys.exit(1)
        endpoint = f"search?q={_encode(positional[0])}"
    elif cmd in ("laws", "technologies", "buildings", "ideologies"):
        endpoint = cmd
        if positional:
            endpoint += f"/{_encode(positional[0])}"
        if "era" in options:
            sep = "&" if "?" in endpoint else "?"
            endpoint += f"{sep}era={_encode(options['era'])}"
    elif cmd in ("goods", "combat-units"):
        endpoint = cmd
    elif cmd == "references":
        if not positional:
            print("Usage: references <key>", file=sys.stderr)
            sys.exit(1)
        endpoint = f"references/{_encode(positional[0])}"
    elif cmd == "tech-tree":
        if not positional:
            print("Usage: tech-tree <tech_id>", file=sys.stderr)
            sys.exit(1)
        endpoint = f"tech-tree/{_encode(positional[0])}"
    elif cmd == "modifier-search":
        if not positional:
            print("Usage: modifier-search <pattern>", file=sys.stderr)
            sys.exit(1)
        endpoint = f"modifier-search?q={_encode(positional[0])}"
    elif cmd == "unlocked-by":
        if not positional:
            print("Usage: unlocked-by <tech_id>", file=sys.stderr)
            sys.exit(1)
        endpoint = f"unlocked-by/{_encode(positional[0])}"
    elif cmd == "filter":
        if len(positional) < 2:
            print("Usage: filter <EntityType> <field> [value]", file=sys.stderr)
            sys.exit(1)
        etype = _encode(positional[0])
        field = _encode(positional[1])
        if len(positional) >= 3:
            endpoint = f"filter/{etype}?field={field}&value={_encode(positional[2])}"
        else:
            endpoint = f"filter/{etype}?field=has:{field}"
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        sys.exit(1)

    result = query(endpoint)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
