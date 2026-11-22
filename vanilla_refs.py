"""Who in vanilla's script names a thing, and where vanilla tests a culture (#1563).

The server's reference lookups cover the mod: vanilla events, scripted effects
and triggers, on-actions, country definitions and history are not in
`vanilla_parsed/`, and snapshotting them would double it (about 28 MB of
JSON; owner, 2026-11-12: read the install instead). So these lookups read
the installed game's `common/` and `events/` when they are asked, and say so
plainly on a machine without one.

    vs = vanilla_refs.load(Path(base_game_path) / "game")
    vanilla_refs.refs(vs, "je_meiji_restoration", depth=3)
    vanilla_refs.culture_reads(vs, "north_german", "primary")
    vanilla_refs.formables(vs, "north_german", mod_root)

The scan is the one `scripts/generators/culture_merge_primary_reads.py` wrote
for the culture merges, with its limits: it works on tokens, not on a parsed
tree, so a name counts wherever it appears in an entity's body (a comment
aside), and a read through a saved scope is not followed.

- `refs`: every top-level vanilla entity whose body mentions the name, and,
  following those entities upward, the journal entries, on-actions and
  decisions that reach it within `depth` steps. An entity is "reached" by a
  root when a chain of mentions leads from the root to it; that is a superset
  of what runs, never a subset.
- `culture_reads`: where vanilla tests `cu:<culture>`, by what the test is
  about: `primary` (a country's primary cultures), `pop` (a pop's, a
  character's or a state's own culture), `homeland`, or `any` (every mention).
- `formables`: the `country_formation` tags whose country definition lists
  the culture, vanilla's and the mod's.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_GENERATORS = Path(__file__).resolve().parent / "scripts" / "generators"
if str(_GENERATORS) not in sys.path:
    sys.path.insert(0, str(_GENERATORS))

import culture_merge_primary_reads as _scan  # noqa: E402

SCAN_DIRS = _scan.SCAN_DIRS                     # ("common", "events")
ROOT_KINDS = {
    "common/journal_entries/": "journal_entries",
    "common/on_actions/": "on_actions",
    "common/decisions/": "decisions",
}
DEFAULT_DEPTH = 1
MAX_DEPTH = 8
MODES = ("primary", "pop", "homeland", "any")
# The keys vanilla 1.15.1 gives a `cu:` value to, by what they are about (surveyed 2026-11-12: `culture` 2,614
# uses, `country_has_primary_culture` 1,985, `add_homeland` 1,429, `is_homeland` 654, `add_primary_culture` 167,
# `remove_primary_culture` 55, `remove_homeland` 50, `country_definition_has_culture` 42, `has_culture` 13).
# `pop`: the culture of a pop, a character or a state's people. `homeland`: the test and the two effects, so
# the reply's `keys` says which a row is. Everything else is only under `any`.
POP_KEYS = frozenset({"culture", "has_culture"})
HOMELAND_KEYS = frozenset({"is_homeland", "add_homeland", "remove_homeland"})
_CULTURE = re.compile(r"[a-z0-9_]+")


class NoGame(Exception):
    """There is no installed game to read: these lookups need one."""


@dataclass
class VanillaScript:
    """The text of every vanilla script file under `common/` and `events/`, read once."""
    game: Path
    texts: dict[str, str]
    _blocks: Optional[dict[str, list]] = field(default=None, repr=False)
    _index: Optional[dict[str, set]] = field(default=None, repr=False)

    def blocks(self) -> dict[str, list]:
        """{file: [(top-level key, its tokens)]}."""
        if self._blocks is None:
            self._blocks = {rel: _scan._top_blocks(text) for rel, text in self.texts.items()}
        return self._blocks

    def index(self) -> dict[str, set]:
        """name -> the (file, top-level entity) pairs whose body mentions it, the folders that only name things
        (customizable localization, history, genes) left out, as the generator's trace leaves them."""
        if self._index is None:
            index: dict[str, set] = {}
            for rel, blocks in self.blocks().items():
                if rel.startswith(_scan.UNTRACED_DIRS):
                    continue
                for key, tokens in blocks:
                    for token, _line in tokens:
                        if _scan._NAME.fullmatch(token):
                            index.setdefault(token, set()).add((rel, key))
            self._index = index
        return self._index

    def definitions(self, name: str) -> list[str]:
        """The files that define a top-level entity of this name."""
        return sorted(rel for rel, blocks in self.blocks().items() if any(key == name for key, _ in blocks))


def load(game: Optional[Path]) -> VanillaScript:
    """Read the install's script. NoGame when `game` is not a vanilla `game/` folder."""
    if game is None or not (Path(game) / "common" / "journal_entries").is_dir():
        raise NoGame("no installed game to read (base_game_path/game/common): vanilla's events, scripted "
                     "triggers and effects, on-actions and country definitions are not in vanilla_parsed/")
    game = Path(game)
    texts = {}
    for top in SCAN_DIRS:
        for path in sorted((game / top).rglob("*.txt")):
            rel = path.relative_to(game).as_posix()
            if rel not in _scan.SKIPPED_FILES:
                texts[rel] = _scan._read(path)
    return VanillaScript(game, texts)


# One reading per install state, for the server's lifetime: the first lookup reads about 3,500 files (30 MB)
# from the game's drive, half a minute or more on /mnt/c, and indexes them (ten seconds more).
_CACHE: dict[tuple, VanillaScript] = {}


def _install_key(game: Path) -> tuple:
    stamp = None
    try:
        stamp = (game.parent / "launcher" / "launcher-settings.json").stat().st_mtime_ns
    except OSError:
        pass
    return (str(game), stamp)


def cached(game: Optional[Path]) -> VanillaScript:
    """`load(game)`, read once per install state (the launcher settings' time moves with a patch)."""
    if game is None:
        return load(None)
    key = _install_key(Path(game))
    if key not in _CACHE:
        fresh = load(game)
        _CACHE.clear()
        _CACHE[key] = fresh
    return _CACHE[key]


def kind_of(file: str) -> str:
    """What a file's entities are, from its folder: `events`, or the folder under `common/`."""
    parts = file.split("/")
    if parts[0] == "events":
        return "events"
    return "/".join(parts[1:-1]) if len(parts) > 2 else parts[0]


# ---------------------------------------------------------------------------
# /vanilla-refs
# ---------------------------------------------------------------------------

def refs(vs: VanillaScript, name: str, depth: int = DEFAULT_DEPTH) -> dict:
    """Who mentions `name`, `depth` steps up (1: the entities that name it; 2: also the entities that name
    those; and so on), each with the depth it was found at, and the roots among them: the journal entries,
    on-actions and decisions. A root is not followed further: what starts it is the game, not script."""
    depth = max(1, min(int(depth), MAX_DEPTH))
    index = vs.index()
    seen: dict[tuple[str, str], int] = {}
    frontier = [name]
    for level in range(1, depth + 1):
        following = []
        for target in frontier:
            for caller in sorted(index.get(target, ())):
                if caller in seen or caller[1] == name:
                    continue
                seen[caller] = level
                if not caller[0].startswith(tuple(ROOT_KINDS)):
                    following.append(caller[1])
        frontier = following
        if not frontier:
            break
    rows = [{"file": file, "entity": entity, "kind": kind_of(file), "depth": level}
            for (file, entity), level in sorted(seen.items(), key=lambda item: (item[1], item[0]))]
    roots = {label: sorted({r["entity"] for r in rows if r["file"].startswith(prefix)})
             for prefix, label in ROOT_KINDS.items()}
    return {"name": name, "defined_in": vs.definitions(name), "depth": depth,
            "referenced_by": rows, "roots": roots, "more": bool(frontier)}


# ---------------------------------------------------------------------------
# /culture-reads
# ---------------------------------------------------------------------------

def _mode_reads(text: str, culture: str, mode: str) -> list[tuple[str, int, str]]:
    """(top-level entity, line, the key or block the test sits under) for one file."""
    target = "cu:" + culture
    if mode == "primary":
        return [(entity, line, block) for entity, _part, line, block
                in _scan.scan_text(text, frozenset({culture}))]
    found = []
    stack: list[str] = []
    tokens = list(_scan._tokens(text))
    i = 0
    while i < len(tokens):
        token, line = tokens[i]
        nxt = tokens[i + 1][0] if i + 1 < len(tokens) else ""
        after = tokens[i + 2][0] if i + 2 < len(tokens) else ""
        if token == "}":
            if stack:
                stack.pop()
        elif token == "{":
            stack.append("")
        elif nxt in ("=", "?=") and after == "{":
            if token.strip('"') == target and mode == "any" and stack:
                found.append((stack[0], line, token))
            stack.append(token)
            i += 3
            continue
        elif token.strip('"') == target and stack:
            key = tokens[i - 2][0] if i >= 2 and tokens[i - 1][0] in ("=", "?=", "!=") else ""
            keys = POP_KEYS if mode == "pop" else HOMELAND_KEYS if mode == "homeland" else None
            if keys is None or key in keys:
                found.append((stack[0], line, key or (stack[-1] if stack else "")))
        i += 1
    return found


def culture_reads(vs: VanillaScript, culture: str, mode: str = "primary") -> list[dict]:
    """One row per (file, entity) that tests `cu:<culture>` in the way `mode` names: `count`, the `keys` or
    blocks the tests sit under, the first `lines`, and `entries`, the journal entries the entity belongs to or
    is reached from (the generator's trace: empty when an on-action or a decision reaches it too, nothing
    does, or too many do)."""
    if mode not in MODES:
        raise ValueError(f"as is one of {', '.join(MODES)}, not {mode!r}")
    if not _CULTURE.fullmatch(culture):
        raise ValueError(f"a culture is a plain name, not {culture!r}")
    needle = "cu:" + culture
    rows: dict[tuple[str, str], dict] = {}
    for rel, text in vs.texts.items():
        if needle not in text or (mode == "primary" and "primary_culture" not in text):
            continue
        for entity, line, key in _mode_reads(text, culture, mode):
            row = rows.setdefault((rel, entity), {"file": rel, "entity": entity, "kind": kind_of(rel),
                                                  "count": 0, "keys": [], "lines": []})
            row["count"] += 1
            if key and key not in row["keys"]:
                row["keys"].append(key)
            if len(row["lines"]) < 10:
                row["lines"].append(line)
    index = vs.index()
    out = []
    for (rel, entity), row in sorted(rows.items()):
        row["entries"] = _scan.trace_entries(rel, entity, index)
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# /formables
# ---------------------------------------------------------------------------

def _definitions(texts: dict[str, str]) -> dict[str, dict]:
    """{tag: {"cultures": [...]}} from country_definitions files' text."""
    found: dict[str, dict] = {}
    for rel in sorted(texts):
        for tag, tokens in _scan._top_blocks(texts[rel]):
            cultures = _scan._list_field(tokens, "cultures")
            if cultures is not None:
                found[tag] = {"cultures": cultures}
    return found


def _formation(texts: dict[str, str]) -> dict[str, dict]:
    """{tag: {"use_culture_states": bool}} from country_formation files' text."""
    found: dict[str, dict] = {}
    for rel in sorted(texts):
        for tag, tokens in _scan._top_blocks(texts[rel]):
            words = [t for t, _ in tokens]
            use = any(words[i] == "use_culture_states" and words[i + 2] == "yes"
                      for i in range(len(words) - 2))
            found[tag] = {"use_culture_states": use}
    return found


def _folder(texts_or_root, folder: str) -> dict[str, str]:
    if isinstance(texts_or_root, dict):
        return {rel: text for rel, text in texts_or_root.items() if rel.startswith(folder + "/")}
    root = Path(texts_or_root) / folder
    return {path.relative_to(texts_or_root).as_posix(): _scan._read(path)
            for path in sorted(root.rglob("*.txt"))} if root.is_dir() else {}


def formables(vs: VanillaScript, culture: Optional[str] = None, mod_root: Optional[Path] = None) -> list[dict]:
    """The `country_formation` tags whose country definition lists `culture` (every formable when None):
    `{tag, cultures, exists_at_start, use_culture_states, source}`. `cultures` is the list the game loads:
    the mod's when its country definition gives one, else vanilla's; `vanilla_cultures` is added when the two
    differ, and a culture in either list counts. `source` is `vanilla`, `mod` (the mod adds the formable) or
    `both` (the mod restates a vanilla one, or its definition). A tag exists at start when a state's history
    names it as an owner."""
    vanilla_defs = _definitions(_folder(vs.texts, "common/country_definitions"))
    vanilla_forms = _formation(_folder(vs.texts, "common/country_formation"))
    mod_defs = _definitions(_folder(mod_root, "common/country_definitions")) if mod_root else {}
    mod_forms = _formation(_folder(mod_root, "common/country_formation")) if mod_root else {}
    owners: set[str] = set()
    for text in _folder(vs.texts, "common/history/states").values():
        owners.update(re.findall(r"\bc:([A-Z0-9]{3})\b", text))
    rows = []
    for tag in sorted(set(vanilla_forms) | set(mod_forms)):
        definition = mod_defs.get(tag) or vanilla_defs.get(tag)
        cultures = definition["cultures"] if definition else []
        vanilla_cultures = vanilla_defs.get(tag, {}).get("cultures")
        if culture is not None and culture not in cultures and culture not in (vanilla_cultures or []):
            continue
        in_vanilla = tag in vanilla_forms
        in_mod = tag in mod_forms or tag in mod_defs
        row = {
            "tag": tag, "cultures": cultures, "exists_at_start": tag in owners,
            "use_culture_states": (mod_forms.get(tag) or vanilla_forms.get(tag))["use_culture_states"],
            "source": "both" if in_vanilla and in_mod else "vanilla" if in_vanilla else "mod",
        }
        if vanilla_cultures is not None and vanilla_cultures != cultures:
            row["vanilla_cultures"] = vanilla_cultures
        rows.append(row)
    return rows
