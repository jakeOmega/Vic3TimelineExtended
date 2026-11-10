"""Inventory of what vanilla ties to a culture merge's parts being primary cultures.

A part that has switched into its merge's result has no people left. It is
removed from a country's primary cultures once nothing is tied to it (owner,
2026-11-09), and "tied" is decided from this inventory: every place vanilla
tests a part as a **primary culture**, and every formable whose definition
lists one.

Two kinds of row:

* ``reads``: one per (file, top-level entity, part). A read is
  ``country_has_primary_culture = cu:<part>``, a ``cu:<part>`` inside an
  ``any_/every_/random_/ordered_primary_culture`` block, or
  ``cu:<part> = { is_primary_culture_of = ... }``. The scan is brace-aware, so a
  block spread over several lines is found. ``add_primary_culture`` and
  ``remove_primary_culture`` are effects, not reads. Pop, homeland, fervor and
  character tests (``has_pop_culture``, ``is_homeland``, ``culture = cu:x``) are
  not reads either: they follow the pops, the kept homelands and the fervor
  copy (``docs/systems/mod_systems/culture_merges.md`` § Compatibility).
  ``entries`` names the journal entries a row belongs to: the entry itself, or,
  for an event, button, trigger or effect, the entries that reach it through
  vanilla's script (``trace_entries``). It is empty when something other than a
  journal entry reaches it too (an on-action, a decision) or nothing does, and
  then the ledger has to say what the row is.
* ``formables``: each vanilla ``common/country_formation`` tag whose country
  definition lists a part, with the definition's whole ``cultures`` list (the
  generator restates it) and whether the tag owns a state at the 1836 start.
  Forming a tag needs a primary culture from that list
  (``docs/vanilla/vanilla_formable_countries_reference.md`` § 2).

A third section, ``trigger_lists``, holds the culture list of each vanilla
trigger the mod restates (``culture_merge_primary_ledger.TRIGGER_OVERRIDES``):
a trigger that is one ``OR`` of ``country_has_primary_culture`` lines and
nothing else, which the scan checks.

The scan reads the installed game, which CI and a cloud container don't have,
so its result is committed as ``culture_merge_primary_reads.json`` beside this
file, stamped with the game version. ``gen_culture_merges`` and the tests read
the JSON. After a vanilla patch (``vanilla_parsed/manifest.json`` moves on, and
``test_culture_merge_primary_reads.py`` fails on the stamp), rescan on the
machine with the game and classify what is new in
``culture_merge_primary_ledger.py``:

    python3 scripts/generators/culture_merge_primary_reads.py --write
    python3 scripts/generators/culture_merge_primary_reads.py --check    # exit 1 when the JSON is stale
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import culture_merges_config as cfg  # noqa: E402

INVENTORY = Path("scripts/generators/culture_merge_primary_reads.json")
SCAN_DIRS = ("common", "events")
PRIMARY_ITERATORS = frozenset(
    "%s_primary_culture" % prefix for prefix in ("any", "every", "random", "ordered")
)
# Vanilla's Russian-locale grammar helpers: 2,100 culture tests that only pick a word ending. Never content.
SKIPPED_FILES = ("common/customizable_localization/99_ru_custom_loc_V3.txt",)

_TOKEN = re.compile(r'"[^"\n]*"|[{}]|[<>!?]?=|[<>]|[^\s{}=<>#"]+')


def part_cultures(merges: tuple[cfg.Merge, ...] | None = None) -> list[str]:
    """Every culture that can switch into a merge's result, in roster order: each slot culture but an absorb merge's
    own result (``french`` in the French merge; it is a part of Latin, so it is listed there)."""
    merges = cfg.MERGES if merges is None else merges
    found: list[str] = []
    for merge in merges:
        for part in merge.core + merge.optional:
            for culture in part.cultures:
                if culture != merge.result and culture not in found:
                    found.append(culture)
    return found


def _tokens(text: str):
    """(token, line number) pairs, comments dropped."""
    for number, line in enumerate(text.split("\n"), 1):
        code = line.split("#", 1)[0]
        for match in _TOKEN.finditer(code):
            yield match.group(0), number


def scan_text(text: str, parts: frozenset[str]) -> list[tuple[str, str, int]]:
    """(top-level entity, part, line) for every read of a part as a primary culture in one file's text."""
    found: list[tuple[str, str, int]] = []
    stack: list[str] = []  # the key that opened each block we are inside
    tokens = list(_tokens(text))
    index = 0

    def part_of(token: str) -> str | None:
        name = token[3:] if token.startswith("cu:") else None
        return name if name in parts else None

    while index < len(tokens):
        token, line = tokens[index]
        nxt = tokens[index + 1][0] if index + 1 < len(tokens) else ""
        after = tokens[index + 2][0] if index + 2 < len(tokens) else ""
        if token == "}":
            if stack:
                stack.pop()
            index += 1
            continue
        if token == "{":  # a bare block (a list): keep the depth right
            stack.append("")
            index += 1
            continue
        if nxt in ("=", "?=") and after == "{":
            stack.append(token)
            index += 3
            continue
        entity = stack[0] if stack else ""
        if token == "country_has_primary_culture" and nxt in ("=", "?="):
            part = part_of(after)
            if part:
                found.append((entity, part, line))
            index += 3
            continue
        if token == "is_primary_culture_of":
            for key in reversed(stack):
                part = part_of(key)
                if part:
                    found.append((entity, part, line))
                    break
        elif part_of(token) and any(key in PRIMARY_ITERATORS for key in stack):
            found.append((entity, part_of(token), line))
        index += 1
    return found


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


ENTRY_DIR = "common/journal_entries/"
# Folders whose entities start content on their own, so a row they reach is not only a journal entry's.
OTHER_ROOT_DIRS = ("common/on_actions/", "common/decisions/")
# Folders that name things without running them, left out of the trace.
UNTRACED_DIRS = ("common/customizable_localization/", "common/history/", "common/genes/")
TRACE_DEPTH = 6
MAX_TRACED_ENTRIES = 4
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]*")


def reference_index(game: Path) -> dict[str, set[tuple[str, str]]]:
    """name -> the (file, top-level entity) pairs whose body mentions it."""
    index: dict[str, set[tuple[str, str]]] = {}
    for top in SCAN_DIRS:
        for path in sorted((game / top).rglob("*.txt")):
            relative = path.relative_to(game).as_posix()
            if relative.startswith(UNTRACED_DIRS):
                continue
            for key, tokens in _top_blocks(_read(path)):
                for token, _line in tokens:
                    if _NAME.fullmatch(token):
                        index.setdefault(token, set()).add((relative, key))
    return index


def trace_entries(file: str, entity: str, index: dict[str, set[tuple[str, str]]]) -> list[str]:
    """The journal entries that reach an entity through vanilla's script, or [] when an on-action or a decision
    reaches it too, nothing does, or more than a handful do (a helper used everywhere says nothing)."""
    if file.startswith(ENTRY_DIR):
        return [entity]
    seen = {(file, entity)}
    frontier = [(file, entity)]
    entries: set[str] = set()
    for _ in range(TRACE_DEPTH):
        following = []
        for _file, name in frontier:
            for caller in index.get(name, ()):
                if caller in seen:
                    continue
                seen.add(caller)
                if caller[0].startswith(ENTRY_DIR):
                    entries.add(caller[1])
                elif caller[0].startswith(OTHER_ROOT_DIRS):
                    return []
                else:
                    following.append(caller)
        frontier = following
    return sorted(entries) if len(entries) <= MAX_TRACED_ENTRIES else []


def scan_reads(game: Path, parts: list[str]) -> list[dict]:
    wanted = frozenset(parts)
    rows: dict[tuple[str, str, str], int] = {}
    for top in SCAN_DIRS:
        for path in sorted((game / top).rglob("*.txt")):
            relative = path.relative_to(game).as_posix()
            if relative in SKIPPED_FILES:
                continue
            text = _read(path)
            if "primary_culture" not in text:
                continue
            for entity, part, _line in scan_text(text, wanted):
                key = (relative, entity, part)
                rows[key] = rows.get(key, 0) + 1
    index = reference_index(game)
    traced: dict[tuple[str, str], list[str]] = {}
    found = []
    for (file, entity, part), count in sorted(rows.items()):
        if (file, entity) not in traced:
            traced[(file, entity)] = trace_entries(file, entity, index)
        found.append({"file": file, "entity": entity, "part": part, "count": count, "entries": traced[(file, entity)]})
    return found


def _top_blocks(text: str) -> list[tuple[str, list[tuple[str, int]]]]:
    """(key, tokens inside) for each top-level ``key = { ... }`` block."""
    tokens = list(_tokens(text))
    blocks = []
    index = 0
    while index < len(tokens):
        token = tokens[index][0]
        if index + 2 < len(tokens) and tokens[index + 1][0] in ("=", "?=") and tokens[index + 2][0] == "{":
            depth = 1
            end = index + 3
            while end < len(tokens) and depth:
                depth += tokens[end][0] == "{"
                depth -= tokens[end][0] == "}"
                end += 1
            blocks.append((token.split(":")[-1], tokens[index + 3:end - 1]))
            index = end
        else:
            index += 1
    return blocks


def _list_field(tokens: list[tuple[str, int]], name: str) -> list[str] | None:
    """The items of a depth-0 ``name = { a b c }`` list inside a block's tokens."""
    depth = 0
    for index, (token, _line) in enumerate(tokens):
        if token == "{":
            depth += 1
        elif token == "}":
            depth -= 1
        elif depth == 0 and token == name and index + 2 < len(tokens) and tokens[index + 2][0] == "{":
            items = []
            for item, _ in tokens[index + 3:]:
                if item == "}":
                    return items
                items.append(item)
    return None


def scan_formables(game: Path, parts: list[str]) -> dict[str, dict]:
    wanted = frozenset(parts)
    definitions: dict[str, list[str]] = {}
    for path in sorted((game / "common" / "country_definitions").glob("*.txt")):
        for tag, tokens in _top_blocks(_read(path)):
            cultures = _list_field(tokens, "cultures")
            if cultures is not None:
                definitions[tag] = cultures
    owners: set[str] = set()
    for path in sorted((game / "common" / "history" / "states").glob("*.txt")):
        owners.update(re.findall(r"\bc:([A-Z0-9]{3})\b", _read(path)))
    found: dict[str, dict] = {}
    for path in sorted((game / "common" / "country_formation").glob("*.txt")):
        for tag, _tokens_inside in _top_blocks(_read(path)):
            cultures = definitions.get(tag)
            if cultures and wanted.intersection(cultures):
                found[tag] = {"cultures": cultures, "exists_at_start": tag in owners}
    return dict(sorted(found.items()))


def scan_trigger_lists(game: Path, names: tuple[str, ...]) -> dict[str, dict]:
    """For each named vanilla scripted trigger, its file and the cultures it lists. Raises if a trigger is anything
    but ``OR = { country_has_primary_culture = cu:x ... }``: a restated copy of another shape would drop vanilla's
    other conditions."""
    found: dict[str, dict] = {}
    for path in sorted((game / "common" / "scripted_triggers").glob("*.txt")):
        for name, tokens in _top_blocks(_read(path)):
            if name not in names:
                continue
            words = [token for token, _line in tokens]
            cultures = []
            body = words[3:-1] if words[:3] == ["OR", "=", "{"] and words[-1:] == ["}"] else None
            if body is None or len(body) % 3:
                raise ValueError("%s is no longer a plain OR of primary cultures" % name)
            for index in range(0, len(body), 3):
                key, equals, value = body[index:index + 3]
                if key != "country_has_primary_culture" or equals != "=" or not value.startswith("cu:"):
                    raise ValueError("%s is no longer a plain OR of primary cultures" % name)
                cultures.append(value[3:])
            found[name] = {"file": path.relative_to(game).as_posix(), "cultures": cultures}
    missing = sorted(set(names) - set(found))
    if missing:
        raise ValueError("vanilla no longer defines %s" % ", ".join(missing))
    return found


def game_version(root: Path = ROOT) -> str:
    return json.loads((root / "vanilla_parsed" / "manifest.json").read_text(encoding="utf-8"))["game_version"]


def scan(game: Path, root: Path = ROOT) -> dict:
    import culture_merge_primary_ledger as ledger  # here, not at the top: the ledger imports this module

    parts = part_cultures()
    return {
        "game_version": game_version(root),
        "parts": parts,
        "reads": scan_reads(game, parts),
        "formables": scan_formables(game, parts),
        "trigger_lists": scan_trigger_lists(game, ledger.TRIGGER_OVERRIDES),
    }


def render(inventory: dict) -> str:
    """One read per line, so a vanilla patch's diff shows the rows that changed."""
    lines = ["{", ' "game_version": %s,' % json.dumps(inventory["game_version"])]
    lines.append(' "parts": %s,' % json.dumps(inventory["parts"]))
    lines.append(' "reads": [')
    reads = inventory["reads"]
    for index, row in enumerate(reads):
        lines.append("  %s%s" % (json.dumps(row), "," if index + 1 < len(reads) else ""))
    lines.append(" ],")
    lines.append(' "formables": {')
    formables = list(inventory["formables"].items())
    for index, (tag, entry) in enumerate(formables):
        lines.append("  %s: %s%s" % (json.dumps(tag), json.dumps(entry), "," if index + 1 < len(formables) else ""))
    lines.append(" },")
    lines.append(' "trigger_lists": %s' % json.dumps(inventory["trigger_lists"]))
    lines.append("}")
    return "\n".join(lines) + "\n"


def load(root: Path = ROOT) -> dict:
    return json.loads((root / INVENTORY).read_text(encoding="utf-8"))


def installed_game() -> Path | None:
    """The installed game's ``game`` folder, or None on a machine without one."""
    sys.path.insert(0, str(ROOT))
    try:
        import path_constants
    except Exception:  # noqa: BLE001 - no paths configured at all
        return None
    game = Path(path_constants.base_game_path) / "game"
    return game if (game / "common" / "country_definitions").is_dir() else None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="rescan the installed game and rewrite the JSON")
    mode.add_argument("--check", action="store_true", help="exit 1 if the JSON differs from a fresh scan")
    args = parser.parse_args(argv)
    game = installed_game()
    if game is None:
        print("culture merge primary reads: no installed game to scan", file=sys.stderr)
        return 2
    text = render(scan(game))
    target = ROOT / INVENTORY
    current = target.read_text(encoding="utf-8") if target.exists() else ""
    if text == current:
        print("culture merge primary reads: current")
        return 0
    if args.check:
        print("stale: %s" % INVENTORY)
        return 1
    target.write_text(text, encoding="utf-8")
    print("wrote: %s" % INVENTORY)
    return 0


if __name__ == "__main__":
    sys.exit(main())
