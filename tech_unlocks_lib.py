"""Tech → unlocks inverted index.

Walks every `common/<dir>/*.txt` file that contains
`unlocking_technologies = { ... }` blocks and produces a map from each
technology id to the entities that depend on it. Used by:

- `mod_state_server.py` to serve `GET /tech-unlocks` and to back the
  enriched `/unlocked-by/<tech>` shape.
- `scripts/analysis/tech_balance_audit.py` to answer "what does this
  WEAK-flagged tech actually unlock?" without round-tripping through
  the server.

The library is deliberately ignorant of annotators — annotation is a
post-process step that consumers run via `annotators.apply_to_response`.
The index always emits entries shaped like `{type, id, file, source}`,
which is the contract the annotator wire-up expects.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator


# (entity_type, common_subdir) tuples for every directory whose entities
# can declare `unlocking_technologies = { ... }`.
#
# `entity_type` matches the `ms.mod_parsers` keys used by mod_state_server
# (see `base_game_paths` in that file). `parties/` is mod-only and isn't
# in mod_parsers; we still index it so annotators that target "Parties"
# would work if registered later.
UNLOCK_SOURCES: list[tuple[str, str]] = [
    ("Buildings",            "buildings"),
    ("Combat Unit Types",    "combat_unit_types"),
    ("Decrees",              "decrees"),
    ("Laws",                 "laws"),
    ("Mobilization Options", "mobilization_options"),
    ("Parties",              "parties"),
    ("PMs",                  "production_methods"),
    ("Ship Modifications",   "ship_modifications"),
    ("Ship Types",           "ship_types"),
]


# ---------------------------------------------------------------------------
# Generic block walker (also used by the tech audit script)
# ---------------------------------------------------------------------------

# Match `<id> = {` at the start of a line. The leading character class allows
# letters, digits, and underscores — typical Paradox identifier syntax.
#
# Vic3 also uses Clausewitz merge-directive prefixes: `INJECT:foo = { … }`,
# `REPLACE:foo = { … }`, `REPLACE_OR_CREATE:foo = { … }`. The engine resolves
# them to the underlying entity `foo`, so the inverted index needs to do the
# same — otherwise (e.g.) `REPLACE_OR_CREATE:building_synthetics_plant_rubber`
# falls out of the walk and its `unlocking_technologies` is missed.
_TOP_LEVEL_RE = re.compile(
    r"^(?:(?P<directive>[A-Z_]+):)?(?P<id>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{",
    re.MULTILINE,
)


def iter_top_level_blocks(text: str) -> Iterator[tuple[str, str]]:
    """Yield (entity_id, body_text) for each top-level `<id> = { ... }` block.

    Strips Clausewitz merge-directive prefixes (`INJECT:`, `REPLACE:`,
    `REPLACE_OR_CREATE:`) so the yielded id matches the underlying entity
    the engine resolves to. The body is the brace-delimited text between the
    opening `{` and the matching `}`. Comments and nested braces are
    preserved (callers can strip them or not as they see fit).
    """
    pos = 0
    while pos < len(text):
        m = _TOP_LEVEL_RE.search(text, pos)
        if not m:
            break
        entity_id = m.group("id")
        body_start = m.end()
        depth = 1
        i = body_start
        while i < len(text) and depth > 0:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            i += 1
        yield entity_id, text[body_start:i - 1]
        pos = i


# ---------------------------------------------------------------------------
# unlocking_technologies parsing
# ---------------------------------------------------------------------------

# Match the `unlocking_technologies = { ... }` block. Capture group 1 is the
# raw inside, which we tokenize separately to drop comments + whitespace.
_UNLOCKING_BLOCK_RE = re.compile(
    r"\bunlocking_technologies\s*=\s*\{([^}]*)\}",
)
# Identifier — same shape as the engine accepts.
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")


def parse_unlocking_techs(body: str) -> list[str]:
    """Return the list of tech ids inside `unlocking_technologies = { ... }`.

    Multiple-tech blocks are supported — `{ tech_a tech_b }` returns two
    entries. Inline `# comment` is stripped. Empty / missing block returns
    an empty list.
    """
    m = _UNLOCKING_BLOCK_RE.search(body)
    if not m:
        return []
    inside = m.group(1)
    # Strip `# comment` runs before tokenizing.
    inside = re.sub(r"#[^\n]*", "", inside)
    return _IDENT_RE.findall(inside)


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------

def _walk_unlock_dir(root: Path, entity_type: str, source: str,
                    rel_subdir: str) -> Iterator[tuple[str, dict]]:
    """Yield (tech_id, entry_dict) for every entity in `root/<rel_subdir>` that
    declares unlocking_technologies. Entries carry {type, id, file, source}.
    """
    subdir = root / rel_subdir
    if not subdir.exists():
        return
    for path in sorted(subdir.glob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        for entity_id, body in iter_top_level_blocks(text):
            techs = parse_unlocking_techs(body)
            if not techs:
                continue
            for tid in techs:
                yield tid, {
                    "type": entity_type,
                    "id": entity_id,
                    "file": path.name,
                    "source": source,
                }


def build_tech_unlock_index(
    repo_root: Path,
    *,
    include_vanilla: bool = False,
    vanilla_common_root: Path | None = None,
) -> dict[str, dict]:
    """Build the inverted index `tech_id -> {by_type, summary, n_total}`.

    Mod files (`<repo_root>/common/<subdir>/`) are always walked. Vanilla
    files (`<vanilla_common_root>/<subdir>/`) are walked when
    `include_vanilla=True` and `vanilla_common_root` exists. Each entry
    in the result is shaped `{type, id, file, source}` — `source` is
    `"mod"` or `"vanilla"`.
    """
    out: dict[str, dict] = {}

    def _add(tech_id: str, entry: dict) -> None:
        rec = out.setdefault(tech_id, {"by_type": {}, "summary": {}, "n_total": 0})
        rec["by_type"].setdefault(entry["type"], []).append(entry)
        rec["summary"][entry["type"]] = rec["summary"].get(entry["type"], 0) + 1
        rec["n_total"] += 1

    mod_common = repo_root / "common"
    for entity_type, subdir in UNLOCK_SOURCES:
        for tid, entry in _walk_unlock_dir(mod_common, entity_type, "mod", subdir):
            _add(tid, entry)

    if include_vanilla and vanilla_common_root and vanilla_common_root.exists():
        for entity_type, subdir in UNLOCK_SOURCES:
            for tid, entry in _walk_unlock_dir(
                vanilla_common_root, entity_type, "vanilla", subdir,
            ):
                _add(tid, entry)

    return out
