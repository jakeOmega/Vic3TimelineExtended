"""Which state regions each strategic region holds (#917).

Pure lookups on ModState's parsed `Strategic Regions` data (vanilla's
`common/strategic_regions`, in `vanilla_parsed/` since #917, with the mod's
`REPLACE:` entries merged in), for the server's `/strategic-regions` and
`/state-region` endpoints and for tools that need the map with no game
install:

    import vanilla_parsed, strategic_regions
    data = vanilla_parsed.parsed_entities(["Strategic Regions"])["Strategic Regions"]
    strategic_regions.region_of(data)["STATE_SVEALAND"]   # region_northern_europe

That is vanilla alone. For the game as the mod loads it, take the data from a
ModState that also read the mod's folder (`ms.get_data("Strategic Regions")`).
"""
from __future__ import annotations

_OPERATORS = ("=", "?=", "<", ">", "<=", ">=", "!=", "==")


def _unwrap(value):
    while isinstance(value, tuple) and len(value) == 2 and value[0] in _OPERATORS:
        value = value[1]
    return value


def _names(value) -> list[str]:
    value = _unwrap(value)
    if isinstance(value, str):
        return [value.strip('"')]
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            out += _names(item)
        return out
    return []


def region_states(data: dict | None) -> dict[str, list[str]]:
    """{strategic region: [state regions]} in source order, sea regions
    included (their states are the sea nodes)."""
    out: dict[str, list[str]] = {}
    for name, raw in (data or {}).items():
        body = _unwrap(raw)
        if isinstance(body, dict):
            out[name] = _names(body.get("states"))
    return out


def region_of(data: dict | None) -> dict[str, str]:
    """{state region: its strategic region}. The engine puts a state region
    in one strategic region; if two list it, the later definition wins here
    and `duplicates` names the state."""
    return {state: region for region, states in region_states(data).items() for state in states}


def duplicates(data: dict | None) -> dict[str, list[str]]:
    """{state region: [every strategic region that lists it]} for the state
    regions more than one strategic region lists."""
    seen: dict[str, list[str]] = {}
    for region, states in region_states(data).items():
        for state in states:
            seen.setdefault(state, []).append(region)
    return {state: regions for state, regions in seen.items() if len(regions) > 1}
