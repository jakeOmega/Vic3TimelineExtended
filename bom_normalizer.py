"""Auto-normalize UTF-8 BOM on mod Paradox-script `.txt` files (issue #148).

The Clausewitz engine warns once per mod `.txt` that lacks a leading UTF-8 BOM
(`should be in utf8-bom encoding`). These accumulate as permanent debug.log
triage noise, and every new hand-authored file reintroduces them. This module
prepends `\\xef\\xbb\\xbf` to any in-scope mod-script `.txt` missing it.

Design (see issue #148):
- **File-rewriting** → registered in `POST_LOAD_REGENERATORS`, NOT
  `POST_LOAD_AUDITS`. `audits_only=true` / `mod_only=true` fast-iteration
  reloads skip it, so they never dirty the working tree (per CLAUDE.md).
- **Runs last** among the regenerators so it normalizes whatever the other
  file-writing generators just emitted. (They also write `utf-8-sig` now, so
  this is belt-and-suspenders; this catches hand-authored files and any
  generator that regresses.)
- **Scoped to Paradox-script roots** — `common/`, `events/`, and `.txt` under
  `gfx/` (fleet entities, portrait modifiers). Never YAML / JSON / Python /
  `.metadata/`. A BOM on any of these `.txt` is harmless and is exactly what
  the engine wants.
- **Idempotent** — only files that don't already start with the BOM are
  rewritten, so a clean tree stays clean across reloads.
"""

import os

BOM = b"\xef\xbb\xbf"

# Directories (relative to mod root) whose `.txt` files the engine reads as
# Paradox script and flags for a missing BOM.
_SCOPED_ROOTS = ("common", "events", "gfx")


def _iter_txt_files(mod_path: str):
    for root in _SCOPED_ROOTS:
        base = os.path.join(mod_path, root)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirnames, filenames in os.walk(base):
            for fname in filenames:
                if fname.endswith(".txt"):
                    yield os.path.join(dirpath, fname)


def normalize_bom(mod_path: str) -> dict:
    """Prepend a UTF-8 BOM to every in-scope `.txt` under `mod_path` that lacks
    one. Returns a summary dict: files_scanned, files_normalized, and the list
    of normalized paths (relative to mod_path, sorted)."""
    scanned = 0
    normalized: list[str] = []
    for path in _iter_txt_files(mod_path):
        scanned += 1
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        if data.startswith(BOM):
            continue
        try:
            with open(path, "wb") as fh:
                fh.write(BOM + data)
        except OSError:
            continue
        normalized.append(os.path.relpath(path, mod_path))
    normalized.sort()
    return {
        "files_scanned": scanned,
        "files_normalized": len(normalized),
        "normalized_paths": normalized,
    }


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_GENERATORS entry point. Normalizes BOM across the mod tree.

    Returns a summary dict matching the generator protocol. `files_normalized`
    is intentionally NOT in `_POST_LOAD_WARN_KEYS`: a non-zero count is routine
    housekeeping (a freshly authored file), not an audit finding, so it logs as
    `ok` rather than surfacing in the reload `warnings` array.
    """
    from path_constants import mod_path
    return normalize_bom(mod_path)
