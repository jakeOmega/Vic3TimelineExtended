#!/usr/bin/env python3
"""Repeat the count behind the assimilation cultures' counted roster, from the 1836 history.

    .venv/bin/python scripts/analysis/assimilation_cultures_roster.py

Needs the game (``path_constants.base_game_path``); not in CI. Exits 0 when the count gives
``assimilation_cultures_config.COUNTED``'s languages, 1 with the difference when it does not.

THE COUNT (docs/superpowers/specs/2026-11-25-assimilation-cultures-design.md § The cultures). From the pops of
``game/common/history/pops`` (every country, the decentralized nations among them) and the primary cultures of
``game/common/country_definitions``:

* **ruled**: a language's figure is every pop of every country one of whose primary cultures speaks it. A country
  whose primary cultures speak two languages counts its people under both.
* **speakers**: every pop of a culture that speaks it.

The roster is the 30 languages first by ruled together with the 30 first by speakers. A count by rulers alone
misses the languages of colonized peoples (Bengali's is second by speakers and 70th by rulers).

It also prints each language's largest culture by 1836 pops, which the config's ``names_from`` should be, and notes
where a heritage group's largest culture with one ethnicity is not its ``looks_from``, with both ethnicities. The
config takes the group's own plain ethnicity (``african``, ``caucasian``) over a narrower one (``central_african``,
``slavic``), so Equatorial Bantu and Russian, larger than Hausa and North German, are noted (2026-11-25). A note
does not fail the run. Culture traits come from the committed ``vanilla_parsed/`` snapshot, as the generator reads
them.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "scripts" / "generators"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import assimilation_cultures_config as cfg  # noqa: E402
import culture_merges_config as cm_cfg  # noqa: E402
import gen_culture_merges as gen  # noqa: E402

TOP = 30

_COMMENT = re.compile(r"#[^\n]*")
_STATE = re.compile(r"s:(STATE_\w+)\s*=\s*\{")
_REGION_STATE = re.compile(r"region_state:(\w+)\s*=\s*\{")
_CREATE_POP = re.compile(r"create_pop\s*=\s*\{([^}]*)\}")
_TAG = re.compile(r"^([A-Z][A-Z0-9]{2})\s*=\s*\{", re.M)
_CULTURES = re.compile(r"cultures\s*=\s*\{([^}]*)\}")


def _read(path: Path) -> str:
    return _COMMENT.sub("", path.read_text(encoding="utf-8-sig"))


def _block(text: str, start: int) -> str:
    """The body of the block whose opening brace ends at ``start``."""
    depth, i = 1, start
    while depth and i < len(text):
        depth += text[i] == "{"
        depth -= text[i] == "}"
        i += 1
    return text[start:i - 1]


def primary_cultures(game: Path) -> dict[str, list[str]]:
    """Country tag -> its primary cultures."""
    out = {}
    for path in sorted((game / "common/country_definitions").glob("*.txt")):
        text = _read(path)
        for match in _TAG.finditer(text):
            found = _CULTURES.search(_block(text, match.end()))
            out[match.group(1)] = found.group(1).split() if found else []
    return out


def pops_1836(game: Path) -> Counter:
    """(country tag, culture) -> its 1836 pops."""
    pops: Counter = Counter()
    for path in sorted((game / "common/history/pops").glob("*.txt")):
        text = _read(path)
        for state in _STATE.finditer(text):
            body = _block(text, state.end())
            for region in _REGION_STATE.finditer(body):
                for pop in _CREATE_POP.finditer(_block(body, region.end())):
                    culture = re.search(r"\bculture\s*=\s*(\w+)", pop.group(1))
                    size = re.search(r"\bsize\s*=\s*(\d+)", pop.group(1))
                    if culture and size:
                        pops[(region.group(1).upper(), culture.group(1))] += int(size.group(1))
    return pops


def main() -> int:
    from path_constants import base_game_path

    game = Path(base_game_path) / "game"
    if not (game / "common/history/pops").is_dir():
        print(f"no game at {game}: this script needs the installed game", file=sys.stderr)
        return 2

    cultures = gen.load_vanilla()
    bodies = {c: gen.culture_fields(body) for c, body in cultures.items() if c != cm_cfg.TRAITS_KEY}
    language = {c: cm_cfg.unwrap(b.get("language")) for c, b in bodies.items()}
    group = {c: cm_cfg.trait_group(cm_cfg.unwrap(b.get("heritage")), cultures) for c, b in bodies.items()}
    primaries = primary_cultures(game)
    pops = pops_1836(game)

    ruled: Counter = Counter()
    speakers: Counter = Counter()
    by_culture: Counter = Counter()
    for (tag, culture), size in pops.items():
        if culture not in language:
            continue
        by_culture[culture] += size
        speakers[language[culture]] += size
        for spoken in {language[c] for c in primaries.get(tag, []) if c in language}:
            ruled[spoken] += size

    by_ruled = sorted(ruled, key=lambda key: (-ruled[key], key))
    by_speakers = sorted(speakers, key=lambda key: (-speakers[key], key))
    union = list(dict.fromkeys(by_ruled[:TOP] + by_speakers[:TOP]))

    def largest(members) -> str:
        return max(sorted(members), key=lambda c: by_culture[c])

    def rank(order, key) -> str:
        return str(order.index(key) + 1) if key in order else "-"

    world = sum(speakers.values())
    print(f"1836: {world / 1e6:.1f}M people in {len({tag for tag, _ in pops})} countries")
    print(f"the union of the top {TOP} by people ruled and the top {TOP} by speakers: {len(union)} languages\n")
    print(f"{'language':28} {'ruled M':>8} {'rank':>5} {'speak M':>8} {'rank':>5}  largest culture")
    for key in sorted(union, key=lambda k: -max(ruled[k], speakers[k])):
        print(f"{key.removeprefix('language_'):28} {ruled[key] / 1e6:8.1f} {rank(by_ruled, key):>5} "
              f"{speakers[key] / 1e6:8.1f} {rank(by_speakers, key):>5}  {largest(c for c in language if language[c] == key)}")

    notes = []
    for row in cfg.COUNTED + cfg.HAND:
        members = [c for c in language if language[c] == cfg.LANGUAGE_PREFIX + row.key]
        if members and largest(members) != row.names_from:
            notes.append(f"names_from of {row.key} is {row.names_from}; the largest culture is {largest(members)}")
    def ethnicity(culture) -> str:
        return " ".join(name for _, name in gen.ethnicities(bodies[culture]))

    for row in cfg.GROUPS:
        members = [c for c in group if group[c] == cfg.GROUP_PREFIX + row.key
                   and len(gen.ethnicities(bodies[c])) == 1]
        if members and largest(members) != row.looks_from:
            other = largest(members)
            notes.append(f"looks_from of {row.key} is {row.looks_from} ({ethnicity(row.looks_from)}); the largest "
                         f"one-ethnicity culture is {other} ({ethnicity(other)})")
    covered = sum(speakers[cfg.LANGUAGE_PREFIX + row.key] for row in cfg.COUNTED + cfg.HAND)
    print(f"\nthe counted and hand languages speak {100 * covered / world:.1f}% of 1836's people")
    for note in notes:
        print("note:", note)

    counted = {cfg.LANGUAGE_PREFIX + row.key for row in cfg.COUNTED}
    missing, extra = sorted(set(union) - counted), sorted(counted - set(union))
    if missing or extra:
        print("\nCOUNTED differs from the count:")
        for key in missing:
            print(f"  + {key.removeprefix('language_')}  (in the count, not in COUNTED)")
        for key in extra:
            print(f"  - {key.removeprefix('language_')}  (in COUNTED, not in the count)")
        return 1
    print(f"\nCOUNTED matches the count ({len(counted)} languages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
