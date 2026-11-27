"""The engine defines: `common/defines` (#1879).

A defines file is namespace blocks of leaf values, `NAI = {
CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS = 0.1 … }`, plus the odd file-level
`@constant = value`. The engine merges them leaf by leaf: vanilla's
00_defines.txt opens `NPops` twice and 00_interfaces.txt `NGUI` twice, and a
mod file that sets one leaf leaves the rest of the namespace alone. ModState's
merge is last-wins by top-level key, which would keep one `NPops` block and
drop the other's leaves, so this module reads the files on its own.

    defines = parse_dir(".../game/common/defines")
    defines["NAI"]["CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS"]   # "0.1"

A value is the token as written (a string: `"0.1"`, `"yes"`, a quoted
`"\\"ai_strategy_default\\""`, `"@min_birthrate"`), or a list of tokens for an
array define (`{ 0.5 1.0 }`); vanilla 1.15 has no deeper nesting. Comments
are dropped. `vanilla_parsed.py` stores vanilla's merged table as
`vanilla_parsed/defines.json`, and `vanilla_parsed.vanilla_define(ns, name)`
reads one value from it with no game install.
"""
from __future__ import annotations

import codecs
import os

from mod_state import iter_script_files
from state_history import _entries, _raw_parse

# Relative to a game root (`<install>/game`) or to the mod root.
REL_DIR = "common/defines"


def parse_text(text: str) -> dict:
    """{namespace: {leaf: value}} for one file, `@constant`s as top-level
    strings. A namespace opened twice keeps both blocks' leaves, the later
    one winning a leaf both set."""
    out: dict = {}
    for key, value in _entries(_raw_parse(text)):
        if isinstance(value, (dict, list)) and not key.startswith("@"):
            block = out.setdefault(key, {})
            for leaf, leaf_value in _entries(value):
                block[leaf] = _leaf(leaf_value)
        else:
            out[key] = value
    return out


def _leaf(value):
    """A leaf's value: the token, a list of tokens, or (never in vanilla
    1.15) a nested block as {key: value}."""
    if isinstance(value, dict):
        return {k: _leaf(v) for k, v in _entries(value)}
    if isinstance(value, list):
        if value and all(isinstance(v, dict) for v in value):
            return {k: _leaf(v) for k, v in _entries(value)}
        return [_leaf(v) for v in value]
    return value


def _read(path: str) -> str:
    with codecs.open(path, "r", "utf-8-sig") as f:
        return f.read()


def source_files(dir_path: str) -> list[str]:
    """The files `parse_dir` reads, in the order it reads them (subfolders
    such as vanilla's `jomini/` included)."""
    return list(iter_script_files(dir_path)) if os.path.isdir(dir_path) else []


def parse_files(dir_path: str) -> dict[str, dict]:
    """{file name: parse_text(file)} in load order."""
    return {
        os.path.relpath(path, dir_path).replace(os.sep, "/"): parse_text(_read(path))
        for path in source_files(dir_path)
    }


def merge(*tables: dict) -> dict:
    """Leaf-by-leaf merge of `parse_text` tables, later ones winning a leaf."""
    out: dict = {}
    for table in tables:
        for key, value in table.items():
            if isinstance(value, dict):
                out.setdefault(key, {}).update(value)
            else:
                out[key] = value
    return out


def parse_dir(dir_path: str) -> dict:
    """The merged defines of every file under `dir_path`, in name order. A
    missing directory is an empty table; a file that does not parse raises."""
    return merge(*parse_files(dir_path).values())


def leaf_count(defines: dict) -> int:
    return sum(len(v) for v in defines.values() if isinstance(v, dict))
