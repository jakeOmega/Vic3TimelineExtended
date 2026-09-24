"""Committed, pre-parsed vanilla game data for ModState (`vanilla_parsed/`).

ModState's vanilla half — every entity type in mod_state.VANILLA_COMMON_DIRS
plus the English localization dict — is a pure function of the installed game
files and the parser. Rebuilding it on every mod_state_server start costs
~35-60 s and needs a Victoria 3 install. This module writes that parse to
`vanilla_parsed/` as JSON once per vanilla patch, and loads it back in well
under a second, so:

  * a machine with no game install (cloud sessions, CI) still gets the full
    vanilla view from `ModState`, the server's entity endpoints, and every
    audit that reads `ms.base_parsers` / vanilla loc;
  * a machine WITH the game skips the vanilla parse whenever the snapshot is
    fresh (same game version, same source-file inventory, same parser).

Layout (all JSON, pretty-printed so a vanilla bump diffs line by line):

    vanilla_parsed/
        manifest.json                 version, parser fingerprint, per-type
                                      counts, every source file's size+sha256
        common/<entity_type>.json     one file per entity type
        localization_english.json     vanilla English loc {key: value}

Value encoding: the parser produces str, dict (str keys), list, and 2-tuples
`(operator, value)`. JSON has no tuple, so a tuple is written as a JSON array
whose FIRST element is the operator (`["=", "yes"]`). A parsed list never
starts with an operator token — the parser classifies any `{ }` block with a
top-level operator as a dict — and `build` asserts an exact round trip
(tuples stay tuples, lists stay lists) before writing anything.

Freshness (`check`) compares, in order: snapshot format version, the parser
fingerprint (source of the code that turns vanilla files into ModState data),
the set of entity types and their directories, the game files' version
(launcher-settings.json `rawVersion`, or a vanilla clone's HEAD subject), and
the source-file inventory — path +
size in the fast mode the server uses at startup, path + sha256 with
`full=True`. The fast mode would miss a same-size edit that ships without a
version bump; `python3 vanilla_parsed.py check --full` covers that.

CLI (run on the machine with the game installed; paths from path_constants):

    python3 vanilla_parsed.py build              # (re)write vanilla_parsed/
    python3 vanilla_parsed.py check [--full]     # exit 1 if stale
    python3 vanilla_parsed.py info               # print the manifest summary

`build --game-root DIR` builds from another vanilla tree with the same
`game/...` layout (e.g. the vic3 git clone); pass `--game-version` when DIR
has no launcher/launcher-settings.json and is not a git clone whose HEAD
subject names the version. Workflow: docs/guides/python_tools.md.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import mod_state
import paradox_file_parser
from mod_state import VANILLA_COMMON_DIRS, ModState, iter_loc_files, iter_script_files

FORMAT_VERSION = 1

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(_REPO_ROOT, "vanilla_parsed")
MANIFEST = "manifest.json"
LOC_FILE = "localization_english.json"
LOC_REL_DIR = "game/localization/english"
COMMON_REL_DIR = "game/common"

_OPERATORS = frozenset(paradox_file_parser.conditional_tokens)


# ---------------------------------------------------------------------------
# Value encoding
# ---------------------------------------------------------------------------

def encode(value):
    """Parser value -> JSON-able value (tuples become operator-first arrays)."""
    if isinstance(value, tuple):
        return [encode(v) for v in value]
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [encode(v) for v in value]
    return value


def decode(value):
    """Inverse of `encode`: an array whose first element is an operator token
    is a parser tuple; any other array is a list."""
    if isinstance(value, list):
        if value and isinstance(value[0], str) and value[0] in _OPERATORS:
            return tuple(decode(v) for v in value)
        return [decode(v) for v in value]
    if isinstance(value, dict):
        return {k: decode(v) for k, v in value.items()}
    return value


def _strict_equal(a, b) -> bool:
    """Structural equality that, unlike ==, tells a tuple from a list."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_strict_equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(_strict_equal(x, y) for x, y in zip(a, b))
    return a == b


def _dumps(obj) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# Fingerprints and inventories
# ---------------------------------------------------------------------------

def parser_fingerprint() -> str:
    """sha256 over the code that turns vanilla files into ModState data: all of
    paradox_file_parser.py plus the ModState file-walking / loc-reading
    functions. Any edit there (comments included) marks the snapshot stale —
    a false positive costs one rebuild, a false negative serves a parse the
    current parser would not produce."""
    h = hashlib.sha256()
    parts = [inspect.getsource(paradox_file_parser)]
    parts += [
        inspect.getsource(fn)
        for fn in (
            mod_state.split_loc_line,
            mod_state.parse_loc_line,
            mod_state.iter_script_files,
            mod_state.iter_loc_files,
            ModState.add_localization,
            ModState.load_files_from_directory,
        )
    ]
    for part in parts:
        h.update(part.replace("\r\n", "\n").encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:16]


def _entity_dirs(game_root: str) -> dict[str, str]:
    """{entity_type: absolute dir} for the vanilla tree at `game_root`."""
    return {
        et: os.path.join(game_root, *COMMON_REL_DIR.split("/"), *rel.split("/"))
        for et, rel in VANILLA_COMMON_DIRS.items()
    }


def _rel(path: str, game_root: str) -> str:
    return os.path.relpath(path, game_root).replace(os.sep, "/")


def _source_files(game_root: str) -> list[str]:
    """Every file the snapshot is built from — exactly the files a live
    ModState load reads — as absolute paths."""
    files = []
    for d in _entity_dirs(game_root).values():
        if os.path.isdir(d):
            files.extend(iter_script_files(d))
    loc_dir = os.path.join(game_root, *LOC_REL_DIR.split("/"))
    if os.path.isdir(loc_dir):
        files.extend(iter_loc_files(loc_dir))
    return files


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _inventory(game_root: str, *, hashes: bool) -> dict[str, dict]:
    inv = {}
    for path in _source_files(game_root):
        entry = {"size": os.path.getsize(path)}
        if hashes:
            entry["sha256"] = _sha256(path)
        inv[_rel(path, game_root)] = entry
    return dict(sorted(inv.items()))


def live_game_version(game_root: str) -> Optional[str]:
    """`rawVersion` from <game_root>/launcher/launcher-settings.json, or None."""
    path = os.path.join(game_root, "launcher", "launcher-settings.json")
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            v = json.load(f).get("rawVersion")
    except (OSError, ValueError, AttributeError):
        return None
    return v if isinstance(v, str) and v else None


def _git_head_version(game_root: str) -> Optional[str]:
    """Version token from the HEAD commit subject of a vanilla git clone whose
    commits follow the "1.13.9 (Matcha)" convention, or None."""
    if not os.path.isdir(os.path.join(game_root, ".git")):
        return None
    try:
        subject = subprocess.run(
            ["git", "-C", game_root, "log", "-1", "--format=%s"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None
    m = re.findall(r"\d+\.\d+(?:\.\d+)?", subject)
    return m[0] if m else None


def game_files_version(game_root: str) -> Optional[str]:
    """Version of the vanilla tree at `game_root`: launcher-settings.json
    `rawVersion` (an install), else the HEAD subject of a vanilla git clone."""
    return live_game_version(game_root) or _git_head_version(game_root)


def version_key(version: Optional[str]) -> tuple:
    """Sortable key for "1.13.9"-style versions; () when unparseable."""
    try:
        return tuple(int(p) for p in (version or "").split("."))
    except ValueError:
        return ()


def _slug(entity_type: str) -> str:
    return entity_type.lower().replace(" ", "_")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(game_root: str, out_dir: str = DEFAULT_DIR, *,
          game_version: Optional[str] = None) -> dict:
    """Parse the vanilla tree at `game_root` exactly as a live ModState load
    does and write the snapshot to `out_dir`. Returns the manifest.

    Writes nothing if the round trip check fails. Leaves an existing snapshot
    untouched (including its `built_at`) when the rebuild would not change any
    data, so re-running on an unchanged install produces no diff."""
    common = os.path.join(game_root, *COMMON_REL_DIR.split("/"))
    if not os.path.isdir(common):
        raise FileNotFoundError(f"no vanilla {COMMON_REL_DIR}/ under {game_root}")
    version_source = "argument"
    if game_version is None:
        game_version, version_source = live_game_version(game_root), "launcher-settings.json"
    if game_version is None:
        game_version, version_source = _git_head_version(game_root), "git HEAD subject"
    if game_version is None:
        raise ValueError(
            f"cannot tell the game version of {game_root} (no "
            "launcher/launcher-settings.json, not a versioned git clone); "
            "pass --game-version"
        )

    entity_dirs = _entity_dirs(game_root)
    ms = ModState(entity_dirs, {})
    loc_dir = os.path.join(game_root, *LOC_REL_DIR.split("/"))
    if os.path.isdir(loc_dir):
        ms.add_localization(loc_dir)

    files: dict[str, str] = {}
    entity_types = {}
    for et in VANILLA_COMMON_DIRS:
        data = ms.base_parsers[et].data
        text = _dumps(encode(data))
        if not _strict_equal(decode(json.loads(text)), data):
            raise AssertionError(f"{et}: parsed data does not survive the JSON round trip")
        rel_file = f"common/{_slug(et)}.json"
        files[rel_file] = text
        entity_types[et] = {
            "dir": _rel(entity_dirs[et], game_root),
            "file": rel_file,
            "entities": len(data),
        }
    files[LOC_FILE] = _dumps(ms.localization)

    manifest = {
        "format_version": FORMAT_VERSION,
        "game_version": game_version,
        "game_version_source": version_source,
        "parser_fingerprint": parser_fingerprint(),
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "entity_types": entity_types,
        "localization": {
            "dir": LOC_REL_DIR,
            "file": LOC_FILE,
            "keys": len(ms.localization),
        },
        "parse_failures": [
            {"file": _rel(f["file"], game_root), "error": f["error"]}
            for f in ms.parse_failures
        ],
        "sources": _inventory(game_root, hashes=True),
    }

    old = read_manifest(out_dir)
    if old is not None and _same_build(old, manifest) and all(
        _read_text(os.path.join(out_dir, rel)) == text for rel, text in files.items()
    ):
        return old

    os.makedirs(os.path.join(out_dir, "common"), exist_ok=True)
    for rel, text in files.items():
        _write_atomic(os.path.join(out_dir, rel), text)
    keep = set(files)
    for name in os.listdir(os.path.join(out_dir, "common")):
        if f"common/{name}" not in keep and name.endswith(".json"):
            os.remove(os.path.join(out_dir, "common", name))
    # Manifest last: a snapshot whose manifest is written is complete.
    _write_atomic(os.path.join(out_dir, MANIFEST), _dumps(manifest))
    return manifest


def _same_build(a: dict, b: dict) -> bool:
    strip = lambda m: {k: v for k, v in m.items() if k != "built_at"}  # noqa: E731
    return strip(a) == strip(b)


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _write_atomic(path: str, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

@dataclass
class Snapshot:
    manifest: dict
    data: dict            # {entity_type: parsed data}, ready for ModState(vanilla_data=)
    localization: dict    # vanilla English loc {key: value}

    @property
    def parse_failures(self) -> list[dict]:
        """Vanilla files the build skipped, in ModState.parse_failures shape."""
        return [
            {"file": f["file"], "error": f["error"], "source": "vanilla"}
            for f in self.manifest.get("parse_failures", [])
        ]


def read_manifest(snapshot_dir: str) -> Optional[dict]:
    text = _read_text(os.path.join(snapshot_dir, MANIFEST))
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def exists(snapshot_dir: str = DEFAULT_DIR) -> bool:
    return read_manifest(snapshot_dir) is not None


def load(snapshot_dir: str = DEFAULT_DIR) -> Snapshot:
    """Read the snapshot. Raises FileNotFoundError when there is none and
    ValueError when it was written in another format version."""
    manifest = read_manifest(snapshot_dir)
    if manifest is None:
        raise FileNotFoundError(f"no vanilla snapshot at {snapshot_dir}")
    if manifest.get("format_version") != FORMAT_VERSION:
        raise ValueError(
            f"vanilla snapshot format {manifest.get('format_version')!r} != "
            f"{FORMAT_VERSION}; rebuild with `python3 vanilla_parsed.py build`"
        )
    data = {}
    for et, info in manifest["entity_types"].items():
        with open(os.path.join(snapshot_dir, info["file"]), "r", encoding="utf-8") as f:
            data[et] = decode(json.load(f))
    with open(os.path.join(snapshot_dir, manifest["localization"]["file"]),
              "r", encoding="utf-8") as f:
        localization = json.load(f)
    return Snapshot(manifest=manifest, data=data, localization=localization)


# ---------------------------------------------------------------------------
# Freshness
# ---------------------------------------------------------------------------

@dataclass
class Freshness:
    fresh: bool
    # Why the snapshot does not match the code (rebuild needed, possible
    # without a game install only from a vanilla clone via --game-root).
    code_reasons: list[str] = field(default_factory=list)
    # Why it does not match the live install (only checked when one exists).
    game_reasons: list[str] = field(default_factory=list)
    game_checked: bool = False

    @property
    def reasons(self) -> list[str]:
        return self.code_reasons + self.game_reasons

    def as_dict(self) -> dict:
        return {
            "fresh": self.fresh,
            "reasons": self.reasons,
            "game_checked": self.game_checked,
        }


def check(snapshot_dir: str = DEFAULT_DIR, game_root: Optional[str] = None, *,
          full: bool = False, manifest: Optional[dict] = None) -> Freshness:
    """Compare the snapshot with the current code and, when `game_root` holds a
    vanilla tree, with that install. `full=True` hashes every source file
    instead of comparing sizes."""
    if manifest is None:
        manifest = read_manifest(snapshot_dir)
    if manifest is None:
        return Freshness(False, code_reasons=[f"no snapshot at {snapshot_dir}"])
    code: list[str] = []
    if manifest.get("format_version") != FORMAT_VERSION:
        code.append(
            f"format version {manifest.get('format_version')!r} != {FORMAT_VERSION}"
        )
    if manifest.get("parser_fingerprint") != parser_fingerprint():
        code.append(
            "parser changed since the snapshot was built "
            f"(fingerprint {manifest.get('parser_fingerprint')} != {parser_fingerprint()})"
        )
    snap_types = {
        et: info.get("dir") for et, info in manifest.get("entity_types", {}).items()
    }
    want_types = {et: f"{COMMON_REL_DIR}/{rel}" for et, rel in VANILLA_COMMON_DIRS.items()}
    missing = sorted(set(want_types) - set(snap_types))
    extra = sorted(set(snap_types) - set(want_types))
    moved = sorted(
        et for et in set(want_types) & set(snap_types) if want_types[et] != snap_types[et]
    )
    if missing:
        code.append(f"entity types not in the snapshot: {', '.join(missing)}")
    if extra:
        code.append(f"entity types no longer loaded: {', '.join(extra)}")
    if moved:
        code.append(f"entity type directory changed: {', '.join(moved)}")

    game: list[str] = []
    game_checked = False
    if game_root and os.path.isdir(os.path.join(game_root, *COMMON_REL_DIR.split("/"))):
        game_checked = True
        live = game_files_version(game_root)
        if live and live != manifest.get("game_version"):
            game.append(
                f"game version {live} != snapshot {manifest.get('game_version')}"
            )
        have = _inventory(game_root, hashes=full)
        want = manifest.get("sources", {})
        added = sorted(set(have) - set(want))
        removed = sorted(set(want) - set(have))
        key = "sha256" if full else "size"
        changed = sorted(
            p for p in set(have) & set(want) if have[p].get(key) != want[p].get(key)
        )
        for label, paths in (("added", added), ("removed", removed), ("changed", changed)):
            if paths:
                shown = ", ".join(paths[:5]) + (f" (+{len(paths) - 5} more)" if len(paths) > 5 else "")
                game.append(f"{len(paths)} vanilla file(s) {label}: {shown}")
    return Freshness(not code and not game, code, game, game_checked)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_game_root() -> Optional[str]:
    """path_constants.base_game_path, or None when this machine has none."""
    try:
        from path_constants import base_game_path
    except RuntimeError:
        return None
    return base_game_path


def _summary(manifest: dict) -> str:
    n_entities = sum(i["entities"] for i in manifest["entity_types"].values())
    return (
        f"vanilla {manifest['game_version']} "
        f"({len(manifest['entity_types'])} entity types, {n_entities} entities, "
        f"{manifest['localization']['keys']} loc keys, "
        f"{len(manifest['sources'])} source files, "
        f"{len(manifest['parse_failures'])} parse failures), "
        f"built {manifest['built_at']}, parser {manifest['parser_fingerprint']}"
    )


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Build or check the committed vanilla parse (vanilla_parsed/).",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="parse vanilla and (re)write the snapshot")
    b.add_argument("--game-root", help="vanilla tree (default: path_constants.base_game_path)")
    b.add_argument("--game-version", help="version to record when the tree does not say")
    b.add_argument("--out", default=DEFAULT_DIR, help=argparse.SUPPRESS)
    c = sub.add_parser("check", help="exit 1 if the snapshot is stale")
    c.add_argument("--game-root", help="vanilla tree (default: path_constants.base_game_path)")
    c.add_argument("--full", action="store_true", help="hash every source file")
    c.add_argument("--no-game", action="store_true",
                   help="check against the code only (no install needed)")
    c.add_argument("--out", default=DEFAULT_DIR, help=argparse.SUPPRESS)
    i = sub.add_parser("info", help="print the snapshot summary")
    i.add_argument("--out", default=DEFAULT_DIR, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    if args.cmd == "info":
        manifest = read_manifest(args.out)
        if manifest is None:
            print(f"no vanilla snapshot at {args.out}")
            return 1
        print(_summary(manifest))
        return 0

    if args.cmd == "build":
        game_root = args.game_root or _default_game_root()
        if game_root is None:
            print("no vanilla tree: set VIC3_BASE_GAME / paths.local.json, or pass --game-root")
            return 2
        before = read_manifest(args.out)
        manifest = build(game_root, args.out, game_version=args.game_version)
        unchanged = before is not None and manifest.get("built_at") == before.get("built_at")
        print(("unchanged: " if unchanged else "wrote: ") + _summary(manifest))
        for f in manifest["parse_failures"]:
            print(f"  parse failure: {f['file']}: {f['error']}")
        return 0

    game_root = None if args.no_game else (args.game_root or _default_game_root())
    if game_root is None and not args.no_game:
        print("(no base_game_path configured: checking against the code only)")
    result = check(args.out, game_root, full=args.full)
    if result.fresh:
        what = "code and install" if result.game_checked else "code (no install checked)"
        print(f"fresh against {what}")
        return 0
    print("stale:")
    for r in result.reasons:
        print(f"  - {r}")
    print("rebuild: python3 vanilla_parsed.py build")
    return 1


if __name__ == "__main__":
    sys.exit(main())
