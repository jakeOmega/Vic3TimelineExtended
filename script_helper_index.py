"""Top-level definitions of scripted effects, scripted triggers and script values,
with the `$PARAM$` names each body uses.

Shared by two checks that need the same view of a helper file:

  * `script_argument_audit` (#732): does every call pass exactly the
    arguments its callee's body names?
  * `game_log_reader.helper_anchor_warnings` (#730): is a
    `vanilla_known_bugs.md` entry anchored on a vanilla helper file the mod
    calls into? error.log lists the whole call stack, so such an entry also
    tags the mod's errors that pass through the helper as vanilla.

Raw text, not `paradox_file_parser`: both checks report file and line, which
the parser drops. Comments are blanked before anything is read, so a `$X$` or
a definition inside a comment does not count. Quoted strings are kept for the
`$PARAM$` scan (the engine substitutes inside them too) and blanked for the
brace structure.

Vanilla helpers come from the game files (`<base_game_path>/game`), since the
committed `vanilla_parsed/` snapshot carries no scripted effects or triggers.
`vanilla_game_dir()` returns None without them, and callers go mod-only.
"""
from __future__ import annotations

import os
import re
from bisect import bisect_right
from dataclasses import dataclass

HELPER_DIRS = ("scripted_effects", "scripted_triggers")
DEFINITION_DIRS = HELPER_DIRS + ("script_values",)

PARAM_RE = re.compile(r"\$([A-Za-z0-9_]+)\$")
_DEF_TOKEN_RE = re.compile(
    r"(?P<open>\{)|(?P<close>\})"
    r"|(?P<key>[A-Za-z_@][A-Za-z0-9_.:@\-]*)\s*=\s*(?P<block>\{)?"
)
_MERGE_PREFIX_RE = re.compile(r"^(?:INJECT|REPLACE|REPLACE_OR_CREATE|TRY_INJECT|INJECT_OR_CREATE):")


@dataclass(frozen=True)
class Definition:
    name: str
    kind: str  # "scripted_effects", "scripted_triggers" or "script_values"
    origin: str  # "mod" or "vanilla"
    file: str  # relative to its tree root, e.g. common/scripted_triggers/x.txt
    line: int
    params: frozenset[str]


# A quoted string (it ends at its closing quote or the end of the line) or a
# comment. Scanned left to right, so a `#` inside a string is not a comment.
_STRING_OR_COMMENT_RE = re.compile(r'"[^"\n]*"?|#[^\n]*')


def blank_comments(text: str) -> tuple[str, str]:
    """Return (no_comments, clean), both the same length as `text`.

    `no_comments` blanks comment bodies; `clean` also blanks quoted string
    bodies, so a brace or `key =` inside a string doesn't count. Offsets in
    either map to the same line.
    """
    keep: list[str] = []
    clean: list[str] = []
    pos = 0
    for m in _STRING_OR_COMMENT_RE.finditer(text):
        s = m.group()
        keep.append(text[pos:m.start()])
        clean.append(text[pos:m.start()])
        if s[0] == "#":
            keep.append(" " * len(s))
            clean.append(" " * len(s))
        else:
            keep.append(s)
            closed = len(s) > 1 and s.endswith('"')
            clean.append('"' + " " * (len(s) - 1 - closed) + ('"' if closed else ""))
        pos = m.end()
    keep.append(text[pos:])
    clean.append(text[pos:])
    return "".join(keep), "".join(clean)


def line_starts(text: str) -> list[int]:
    return [0] + [m.end() for m in re.finditer(r"\n", text)]


def line_of(starts: list[int], pos: int) -> int:
    return bisect_right(starts, pos)


def scan_definitions(text: str, rel: str, kind: str, origin: str) -> list[Definition]:
    """Every depth-0 `name = { ... }` (or `name = <scalar>`, a constant script
    value) in one file. `@constants` are skipped; merge prefixes (`INJECT:`)
    are stripped from the name."""
    no_comments, clean = blank_comments(text)
    starts = line_starts(clean)
    defs: list[Definition] = []
    depth = 0
    current: tuple[str, int, int] | None = None  # (name, line, body start)
    for m in _DEF_TOKEN_RE.finditer(clean):
        if m.group("open"):
            depth += 1
        elif m.group("close"):
            depth = max(depth - 1, 0)
            if depth == 0 and current:
                name, line, start = current
                params = frozenset(PARAM_RE.findall(no_comments[start:m.start()]))
                defs.append(Definition(name, kind, origin, rel, line, params))
                current = None
        elif depth == 0:
            name = _MERGE_PREFIX_RE.sub("", m.group("key"))
            line = line_of(starts, m.start())
            if m.group("block"):
                depth = 1
                if not name.startswith("@"):
                    current = (name, line, m.end())
            elif not name.startswith("@"):
                defs.append(Definition(name, kind, origin, rel, line, frozenset()))
        elif m.group("block"):
            depth += 1
    return defs


def read_script(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def definitions_in_file(abs_path: str, rel: str, kind: str, origin: str) -> list[Definition]:
    text = read_script(abs_path)
    return [] if text is None else scan_definitions(text, rel, kind, origin)


def iter_tree_definitions(root: str, origin: str, dirs=HELPER_DIRS,
                          skip_rel: frozenset[str] = frozenset()):
    """Yield every definition under `<root>/common/<dir>/*.txt`, sorted by
    file. `skip_rel` holds relative paths to leave out: a vanilla file the mod
    overrides by path is never loaded."""
    for kind in dirs:
        base = os.path.join(root, "common", kind)
        if not os.path.isdir(base):
            continue
        for fname in sorted(os.listdir(base)):
            if not fname.endswith(".txt"):
                continue
            rel = f"common/{kind}/{fname}"
            if rel in skip_rel:
                continue
            yield from definitions_in_file(os.path.join(base, fname), rel, kind, origin)


def mod_override_paths(mod_root: str, dirs=DEFINITION_DIRS) -> frozenset[str]:
    """Relative paths of the mod's files in `dirs`; each replaces vanilla's
    file of the same path."""
    out = set()
    for kind in dirs:
        base = os.path.join(mod_root, "common", kind)
        if os.path.isdir(base):
            out.update(f"common/{kind}/{f}" for f in os.listdir(base) if f.endswith(".txt"))
    return frozenset(out)


def load_helpers(mod_root: str, vanilla_game: str | None = None,
                 dirs=HELPER_DIRS) -> dict[str, list[Definition]]:
    """name -> definitions, mod first. A vanilla definition is kept only when
    the mod neither defines the name nor overrides its file. A name can carry
    two definitions when it is both a scripted effect and a scripted trigger."""
    index: dict[str, list[Definition]] = {}
    for d in iter_tree_definitions(mod_root, "mod", dirs):
        index.setdefault(d.name, []).append(d)
    if vanilla_game:
        mod_names = set(index)
        skip = mod_override_paths(mod_root, dirs)
        for d in iter_tree_definitions(vanilla_game, "vanilla", dirs, skip):
            if d.name not in mod_names:
                index.setdefault(d.name, []).append(d)
    return index


def vanilla_game_dir() -> str | None:
    """`<base_game_path>/game` when it holds vanilla script, else None (no
    install configured, as in CI and cloud sessions)."""
    try:
        import path_constants
        base = path_constants.base_game_path
    except (ImportError, RuntimeError):
        return None
    if not base:
        return None
    game = os.path.join(base, "game")
    return game if os.path.isdir(os.path.join(game, "common", "scripted_effects")) else None
