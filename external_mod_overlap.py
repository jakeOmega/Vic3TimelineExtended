"""Which of another mod's entries land on this mod's, and which side wins (#1170).

    python3 external_mod_overlap.py <mod root> [--ours <root>] [--json] [--trace]

`<mod root>` is a Workshop folder (`.../workshop/content/529340/<id>`) or any
mod root. Nothing is written anywhere. `GET /external-mod-overlap?path=<root>`
on mod_state_server returns the same report as JSON.

The report:

- `key_collisions`: a top-level key of a `common/<dir>` database both mods
  define, with each side's file, line and directive, whether vanilla has it,
  and a `verdict` from the load-order model.
- `defines`: an `N*` block key both mods set (never an `@name`: those are
  file-local), and whose file is read later.
- `additive_hooks` / `on_action_conflicts`: on_actions both mods hook, and a
  field both set that doesn't add up (`effect`).
- `event_namespace_collisions`, `event_id_collisions`: shared `namespace =`
  declarations and event ids.
- `loc_collisions`: English loc keys both define (`localization/english/`
  and `localization/replace/english/`).
- `path_collisions`: a file at the same relative path in both mods (any
  folder: `gui/`, `common/`, `gfx/`, ...).

The load-order model is `LOAD_ORDER_MODEL` below: each engine claim, how sure
it is, and where its evidence is (the facts themselves are written once, in
`LOAD_ORDER_DOC`). The probed ones are settings (`KNOWN_FILE_ORDER`,
`KNOWN_LOAD_READING`, `BARE_DUPLICATE_RULES`); what is still unknown is
simulated every way (`resolve`), and an in-game answer is a one-line change
to a setting.

Verdicts: `ours_wiped`, `theirs_wiped`, `both_merge` (both sides' content
reaches the final entry; `ours_lost`/`theirs_lost` still list a definition
that doesn't, such as the first of two INJECTs around a REPLACE),
`both_wiped`, and, when an unknown changes the outcome, `depends_on_playset`
or `undetermined` (with `depends_on` and `verdict_by_scenario`).
`order_depends_on_case` (ASCII vs case-folded file order) can't occur while
`KNOWN_FILE_ORDER` is set, and the rows' `order_depends_on_case` flag is then
always false.

The scan is a light top-level scanner rather than ParadoxFileParser: it needs
each key's file, line and directive, which the parser drops, and it must
survive whatever a foreign mod's files hold (an unbalanced brace costs a
warning, not the file).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import product
from typing import Iterable, Optional

from mod_state import VANILLA_COMMON_DIRS, split_loc_line
from paradox_file_parser import (
    INJECT_DIRECTIVES,
    REPLACE_DIRECTIVES,
)

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(REPO_ROOT, "vanilla_parsed")

OURS, THEIRS, VANILLA = "ours", "theirs", "vanilla"

# Verdicts. The first four are the issue's; the rest say why a verdict can't
# be given.
OURS_WIPED = "ours_wiped"
THEIRS_WIPED = "theirs_wiped"
BOTH_MERGE = "both_merge"
BOTH_WIPED = "both_wiped"
ORDER_DEPENDS_ON_CASE = "order_depends_on_case"
DEPENDS_ON_PLAYSET = "depends_on_playset"
UNDETERMINED = "undetermined"

FIRST_WINS, LAST_WINS, UNKNOWN = "first_wins", "last_wins", "unknown"


# ---------------------------------------------------------------------------
# The load-order model: each engine claim this module rests on, how sure it
# is, and where its evidence is written. The facts themselves live in one
# place, LOAD_ORDER_DOC; correct them there and here together. Status:
#   probed      read in game by the 2026-10-26 load-order probe
#   documented  Paradox, the Modding-Digests or a repo doc says so
#   unprobed    the working rule, not checked in game
#   unknown     simulated every way
# ---------------------------------------------------------------------------
LOAD_ORDER_DOC = "docs/guides/scripting_best_practices.md § Load Order (probed 2026-10-26)"
LOAD_ORDER_MODEL = {
    "file_order": {
        "status": "probed",
        "claim": "File names compare in plain ASCII byte order (B_ before a_, p_ before pa_).",
        "see": f"{LOAD_ORDER_DOC}, fact 1. Setting: KNOWN_FILE_ORDER.",
    },
    "interleaving": {
        "status": "probed",
        "claim": "Within a common/ database, vanilla's and every mod's files are one "
                 "ASCII-ordered list; vanilla is not read first.",
        "see": f"{LOAD_ORDER_DOC}, fact 2. Setting: KNOWN_LOAD_READING.",
    },
    "bare_duplicate": {
        "status": "probed",
        "claim": "A bare definition of a key that already exists is dropped (gamedatabase.h:378 "
                 "`Duplicated key X will not be created from file:`): the first one wins.",
        "see": f"{LOAD_ORDER_DOC}, fact 3 (static_modifiers, scripted_effects); for the other "
               "Modding-Digests 1.12.0 inject_types.md folders, breaking_changes.md (no implicit "
               "overwrites). Setting: BARE_DUPLICATE_RULES.",
    },
    "directives": {
        "status": "documented",
        "claim": "INJECT/REPLACE act on an existing entry and error when there is none "
                 "(gamedatabase.h:395); TRY_INJECT/TRY_REPLACE skip it; "
                 "INJECT_OR_CREATE/REPLACE_OR_CREATE create it. A REPLACE wipes what came "
                 "before it, an INJECT adds to it.",
        "see": f"Modding-Digests 1.12.0 inject_types.md; the :395 text, {LOAD_ORDER_DOC}, fact 4.",
    },
    "directives_deferred": {
        "status": "probed",
        "claim": "Directives apply after every bare definition has been read, so an INJECT "
                 "needn't sort after its target. Among themselves they are taken to apply in "
                 "file order (unprobed).",
        "see": f"{LOAD_ORDER_DOC}, fact 4. Setting: KNOWN_LOAD_READING.",
    },
    "bare_duplicate_script_values": {
        "status": "unprobed",
        "claim": "A bare duplicate script value logs nothing; the last one wins, per the mod's "
                 "practice (16 vanilla values restated bare in common/script_values/modified.txt).",
        "see": f"{LOAD_ORDER_DOC}, fact 5; § Vanilla Script-Value Overrides.",
    },
    "bare_duplicate_other": {
        "status": "unknown",
        "claim": "Which bare definition wins in a folder not probed and not in inject_types.md "
                 "(scripted_triggers, scripted_rules, game_rules, ...): both are simulated.",
        "see": f"{LOAD_ORDER_DOC} (not probed). Setting: BARE_DUPLICATE_RULES.",
    },
    "same_path": {
        "status": "documented",
        "claim": "A later-loaded mod's file at the same relative path replaces the earlier one "
                 "whole, and a mod file at a vanilla file's path replaces vanilla's. Which of two "
                 "mods loads later is the playset's order: both are simulated.",
        "see": "gui_modding_guide.md (two mods overriding one .gui: only one loads); the mod's "
               "own same-path overrides (common/scripted_rules/00_scripted_rules.txt).",
    },
    "events": {
        "status": "probed",
        "claim": "Events aren't read in the common/ order; a duplicated event id keeps the copy "
                 "read first. Which of two mods' copies that is: unknown.",
        "see": f"{LOAD_ORDER_DOC}, fact 6.",
    },
    "defines": {
        "status": "unprobed",
        "claim": "Per define key, the later file's value wins.",
        "see": "The mod's extra_defines.txt overrides vanilla's 00_defines.txt that way.",
    },
    "on_actions": {
        "status": "documented",
        "claim": "An on_action's events and on_actions lists add up across files; an effect "
                 "block overwrites (the later file's wins). Other fields: unknown.",
        "see": "scripting_best_practices.md § Extending Vanilla On-Actions Safely.",
    },
    "localization": {
        "status": "documented",
        "claim": "A key in a replace/ folder (localization/english/replace/ or "
                 "localization/replace/english/) overrides one outside it; between two files "
                 "of the same kind the winner is unknown.",
        "see": "python_tools.md (Localization note); vanilla_known_bugs.md (`Key X defined in "
               "multiple files`).",
    },
    "vanilla_source": {
        "status": "n/a",
        "claim": "in_vanilla comes from the game files when the game is installed (with file "
                 "names; a folder vanilla lacks means false), else from the committed "
                 "vanilla_parsed/ snapshot (keys only: vanilla's file name is unknown, so its "
                 "definition is put first, which vanilla's 0*_ names make right for most), else "
                 "it is null and both answers are tried.",
        "see": "",
    },
}

# Databases that take the six directives (Modding-Digests 1.12.0
# inject_types.md, `common/` entries; `technology` there covers both
# `technology/eras` and `technology/technologies`).
DIGEST_INJECT_DIRS = frozenset("""
acceptance_statuses ai_strategies amendments battle_conditions building_groups
buildings buy_packages character_interactions character_templates
character_traits cohesion_levels combat_unit_groups combat_unit_types
combat_unit_experience_levels commander_orders company_charter_types
company_types country_creation country_definitions country_formation
country_ranks country_types culture_graphics cultures decisions decrees
diplomatic_actions diplomatic_catalyst_categories diplomatic_catalysts
diplomatic_plays discrimination_trait_groups discrimination_traits dna_data
dynamic_company_names dynamic_country_names dynamic_country_map_colors
dynamic_treaty_names technology/eras technology/technologies flag_definitions
game_concepts genes geographic_regions goods government_types
harvest_condition_types ideologies institutions interest_group_traits
interest_groups journal_entry_groups journal_entries law_groups laws
legitimacy_levels liberty_desire_levels military_formation_flags
mobilization_option_groups mobilization_options objective_subgoal_categories
objective_subgoals objectives parties political_lobby_appeasement
political_lobbies political_movement_categories political_movement_pop_support
political_movements pop_needs pop_types power_bloc_coa_pieces
power_bloc_identities power_bloc_map_textures power_bloc_names
power_bloc_principle_groups power_bloc_principles prestige_goods
production_method_groups production_methods proposal_types religions
social_classes social_hierarchies state_traits strategic_regions subject_types
terrain_manipulators terrain themes tutorial_lessons tutorial_lesson_chains
labels war_goal_types alert_groups alert_types commander_ranks
scripted_buttons scripted_progress_bars treaty_articles
modifier_type_definitions ethnicities scripted_guis scripted_lists
scripted_modifiers achievements
""".split())

# ---------------------------------------------------------------------------
# What is known, as settings. None (or a folder missing from
# BARE_DUPLICATE_RULES) is an unknown that resolve() simulates every way; an
# in-game answer is a one-line change here (and its LOAD_ORDER_MODEL entry).
# ---------------------------------------------------------------------------
FILE_ORDERS = ("ascii", "lower_folded", "upper_folded")
KNOWN_FILE_ORDER: Optional[str] = "ascii"         # LOAD_ORDER_MODEL["file_order"]
# vanilla_first: vanilla's files, then the mods'. interleaved: one name-ordered
# list, applied in order. creations_first: every bare definition (vanilla's and
# the mods', interleaved by name) first, then the directives in file order.
LOAD_READINGS = ("vanilla_first", "interleaved", "creations_first")
KNOWN_LOAD_READING: Optional[str] = "creations_first"  # ["interleaving"], ["directives_deferred"]
# Who wins between two bare definitions of one key, per common/ folder.
BARE_DUPLICATE_RULES = {
    **{d: FIRST_WINS for d in DIGEST_INJECT_DIRS},   # LOAD_ORDER_MODEL["bare_duplicate"]
    "static_modifiers": FIRST_WINS,                  # probed
    "scripted_effects": FIRST_WINS,                  # probed
    "script_values": LAST_WINS,                      # ["bare_duplicate_script_values"]
}

# `common/` folders whose subfolders are separate databases.
CONTAINER_DIRS = frozenset({"coat_of_arms", "history", "technology", "terrain_manipulators"})
# Folders whose entries sit one level down, inside a wrapper block both mods
# repeat (`colors = { ... }`): the wrapper is merged, its children collide.
WRAPPER_DIRS = {"named_colors": "colors"}

# on_action fields that add up across files, and blocks that overwrite
# (LOAD_ORDER_MODEL["on_actions"]). Any other field both mods set is reported
# with an unknown rule.
ADDITIVE_ON_ACTION_FIELDS = frozenset({"events", "on_actions"})
OVERWRITING_ON_ACTION_FIELDS = frozenset({"effect"})

_OPERATORS = frozenset({"=", "<", ">", "<=", ">=", "!=", "?=", "=="})
_TOKEN_RE = re.compile(r'"(?:[^"\\]|\\.)*"?|[{}]|[<>!?=]+|[^\s{}<>!?="]+')
_DIRECTIVE_RE = re.compile(
    r"^(INJECT|REPLACE|TRY_INJECT|TRY_REPLACE|REPLACE_OR_CREATE|INJECT_OR_CREATE):(.+)$"
)
_UNKNOWN_PREFIX_RE = re.compile(r"^[A-Z][A-Z_]*:")
_EVENT_ID_RE = re.compile(r"^[\w\-]+\.[\w\-]+$")
# English loc folders; a key in a replace/ one overrides (LOAD_ORDER_MODEL["localization"]).
_LOC_DIR = "localization/english"
_LOC_REPLACE_DIR = "localization/replace/english"
_LOC_DIRS = (_LOC_DIR, _LOC_REPLACE_DIR)
# The mod state server's entity type for a folder, for /raw/<type>/<key>.
SERVER_TYPES = {
    **{rel: et for et, rel in VANILLA_COMMON_DIRS.items()},
    "scripted_effects": "Scripted Effects",
    "scripted_triggers": "Scripted Triggers",
    "scripted_guis": "Scripted GUIs",
    "scripted_progress_bars": "Scripted Progress Bars",
    "on_actions": "On Actions",
}
_SKIP_ROOT_DIRS = frozenset({".git", ".metadata", ".github", ".venv", "__pycache__"})
# Files the game doesn't read (notes, Python), left out of path_collisions.
_NOT_GAME_FILES = (".md", ".info", ".py", ".pyc")
# What makes a folder a mod root (validate_root).
_MOD_MARKERS = (".metadata/metadata.json", "descriptor.mod")
_MOD_DIRS = ("common", "events", "gui", "localization")


# ---------------------------------------------------------------------------
# Rules per database
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DirRule:
    kind: str          # database | script_values | defines | on_actions | additive | wrapper | unknown
    bare_duplicate: str  # first_wins | last_wins | unknown | n/a
    source: str        # a LOAD_ORDER_MODEL key, or a short reason

    def as_dict(self) -> dict:
        return {"kind": self.kind, "bare_duplicate": self.bare_duplicate, "source": self.source}


def rule_for(db: str) -> DirRule:
    """How the engine merges two definitions of one key in `db` (a folder
    relative to `common/`); `source` names the LOAD_ORDER_MODEL entry."""
    if db == "defines":
        return DirRule("defines", "n/a", "defines")
    if db == "on_actions":
        return DirRule("on_actions", "n/a", "on_actions")
    if db.split("/")[0] == "history":
        return DirRule("additive", "n/a", "history blocks are effects; every file's run")
    if db in WRAPPER_DIRS:
        return DirRule("wrapper", UNKNOWN, f"entries sit inside `{WRAPPER_DIRS[db]} = {{ }}`, "
                       "which both mods repeat; how a repeated entry merges isn't recorded")
    rule = BARE_DUPLICATE_RULES.get(db, UNKNOWN)
    if db == "script_values":
        return DirRule("script_values", rule, "bare_duplicate_script_values")
    if rule == UNKNOWN:
        return DirRule("unknown", UNKNOWN, "bare_duplicate_other")
    return DirRule("database", rule, "bare_duplicate")

def split_common_path(rel_in_common: str) -> Optional[tuple[str, str]]:
    """(database, path within it) for a file path relative to `common/`, or
    None for a file directly in `common/`."""
    parts = rel_in_common.split("/")
    if len(parts) < 2:
        return None
    if parts[0] in CONTAINER_DIRS and len(parts) >= 3:
        return f"{parts[0]}/{parts[1]}", "/".join(parts[2:])
    return parts[0], "/".join(parts[1:])


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

@dataclass
class Entry:
    """One key at brace depth 0 of a script file."""
    raw_key: str
    key: str
    directive: Optional[str]
    line: int
    value: Optional[str]                 # a scalar's value; None for a block
    children: list = field(default_factory=list)   # [(key, line, value)] at depth 1


def split_directive(raw_key: str) -> tuple[Optional[str], str]:
    m = _DIRECTIVE_RE.match(raw_key)
    return (m.group(1), m.group(2)) if m else (None, raw_key)


def strip_comment(line: str) -> str:
    """`line` without its `# ...` comment. A `#` inside a quoted string isn't
    one, and a backslash escapes the character after it inside a string, so
    `"say \\"hi # there\\""` keeps its `#` (ParadoxFileParser._strip_comment
    flips on every quote). A quote that never closes falls back to cutting at
    the first `#`, as the parser does."""
    first = line.find("#")
    if first == -1:
        return line
    in_string, i, n = False, 0, len(line)
    while i < n:
        c = line[i]
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_string = False
        elif c == '"':
            in_string = True
        elif c == "#":
            return line[:i]
        i += 1
    return line[:first] if in_string else line


def _tokens(text: str) -> list[tuple[str, int]]:
    out = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        out.extend((m.group(), lineno) for m in _TOKEN_RE.finditer(strip_comment(raw)))
    return out


def _block_text(tokens, start: int, cap: int = 200) -> str:
    """The tokens of the block opening at tokens[start], joined by spaces."""
    depth, parts = 0, []
    for tok, _line in tokens[start:]:
        parts.append(tok)
        if tok == "{":
            depth += 1
        elif tok == "}":
            depth -= 1
            if depth == 0:
                break
    text = " ".join(parts)
    return text if len(text) <= cap else text[: cap - 1] + "…"


def scan_script(text: str) -> tuple[list[Entry], list[str]]:
    """Every depth-0 key of a script file, with the depth-1 keys of each
    block. `@name` constants are skipped at both depths (file-local). Returns
    (entries, warnings)."""
    warnings = []
    if text.startswith("﻿"):
        warnings.append("doubled UTF-8 BOM: the engine reads the second as part of the "
                        "first token and can drop the whole file")
        text = text.lstrip("﻿")
    tokens = _tokens(text)
    entries: list[Entry] = []
    depth, current, i, n = 0, None, 0, len(tokens)
    while i < n:
        tok, line = tokens[i]
        if tok == "{":
            depth += 1
            i += 1
            continue
        if tok == "}":
            if depth == 0:
                warnings.append(f"line {line}: '}}' with no open block")
            else:
                depth -= 1
                if depth == 0:
                    current = None
            i += 1
            continue
        if i + 1 < n and tokens[i + 1][0] in _OPERATORS:
            value_tok = tokens[i + 2][0] if i + 2 < n else None
            is_block = value_tok == "{"
            if value_tok == "}":
                # `key = }`: no value; leave the brace to close its block.
                warnings.append(f"line {line}: {tok!r} has no value")
                i += 2
                continue
            if not tok.startswith("@"):
                if depth == 0:
                    directive, key = split_directive(tok)
                    if directive is None and _UNKNOWN_PREFIX_RE.match(tok):
                        warnings.append(f"line {line}: unknown directive prefix in {tok!r}")
                    entry = Entry(tok, key, directive, line, None if is_block else value_tok)
                    entries.append(entry)
                    current = entry if is_block else None
                elif depth == 1 and current is not None:
                    value = _block_text(tokens, i + 2) if is_block else value_tok
                    current.children.append((tok, line, value))
            i += 2 if is_block else 3
            continue
        i += 1
    if depth > 0:
        warnings.append(f"{depth} block(s) still open at the end of the file")
    return entries, warnings


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return f.read()


# ---------------------------------------------------------------------------
# File listing
# ---------------------------------------------------------------------------

def list_files(root: str, top: Optional[str] = None, git_fallback: bool = False) -> list[str]:
    """Every file under `root` (or `root/top`), as posix paths relative to
    `root`, skipping dot-folders. With `git_fallback`, a folder missing on
    disk but tracked by git (a sparse worktree's gfx/) is listed from `git
    ls-files`. Only this mod's own root may ask for that: git reads the
    repository's config (core.fsmonitor, hooks), so running it in another
    mod's folder could run that mod's code."""
    base = os.path.join(root, top) if top else root
    out = []
    if os.path.isdir(base):
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
            for name in sorted(filenames):
                out.append(name if rel_dir == "." else f"{rel_dir}/{name}")
        return out
    if git_fallback and top and os.path.exists(os.path.join(root, ".git")):
        try:
            res = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c",
                                  "core.hooksPath=/dev/null", "-C", root, "ls-files", "-z",
                                  "--", top],
                                 capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return out
        if res.returncode == 0:
            out = [p for p in res.stdout.split("\0") if p]
    return out


def _their_files(root: str) -> list[str]:
    """Their files the engine could read: everything in a folder, minus
    dot-folders (`.metadata`) and files at the root (descriptor, thumbnail)."""
    files = []
    for top in sorted(os.listdir(root)):
        if top.startswith(".") or top in _SKIP_ROOT_DIRS:
            continue
        if os.path.isdir(os.path.join(root, top)):
            files.extend(list_files(root, top))
    return files


def read_mod_name(root: str) -> Optional[str]:
    """`name` from `.metadata/metadata.json` (what Vic3 reads), else from a
    `descriptor.mod`."""
    meta = os.path.join(root, ".metadata", "metadata.json")
    if os.path.isfile(meta):
        try:
            with open(meta, "r", encoding="utf-8-sig") as f:
                name = json.load(f).get("name")
            if name:
                return str(name)
        except (OSError, ValueError, AttributeError):
            pass
    desc = os.path.join(root, "descriptor.mod")
    if os.path.isfile(desc):
        m = re.search(r'^\s*name\s*=\s*"([^"]*)"', read_text(desc), re.M)
        if m:
            return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Load-order model (pure)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Op:
    """One definition of a key: who, in which file (path within the
    database; None = a vanilla file of unknown name, read first), its line and
    directive (None = bare)."""
    side: str
    path: Optional[str]
    line: int
    directive: Optional[str] = None


def same_path(a: str, b: str) -> bool:
    """Paths the game treats as one file (Windows: case-insensitive)."""
    return a.casefold() == b.casefold()


def name_key(name: str, order: str) -> str:
    """`name` as FILE_ORDERS' `order` compares it."""
    if order == "lower_folded":
        return name.lower()
    if order == "upper_folded":
        return name.upper()
    return name


def file_orders() -> tuple:
    """The file-name orders still possible (LOAD_ORDER_MODEL["file_order"])."""
    return (KNOWN_FILE_ORDER,) if KNOWN_FILE_ORDER else FILE_ORDERS


def load_readings() -> tuple:
    """The load readings still possible (LOAD_ORDER_MODEL["interleaving"], ["directives_deferred"])."""
    return (KNOWN_LOAD_READING,) if KNOWN_LOAD_READING else LOAD_READINGS


def sort_ops(ops: Iterable[Op], order: str = "ascii", vanilla_first: bool = True) -> list[Op]:
    """Load order: by file name compared the `order` way (FILE_ORDERS), then
    by line. With `vanilla_first`, vanilla's definitions come before every
    mod's; without, vanilla's files take their place by name. A vanilla
    definition of unknown file (the snapshot) comes first either way."""
    def key(op: Op):
        name = op.path or ""
        first = op.side != VANILLA if vanilla_first else op.path is not None
        return (first, name_key(name, order), name, op.line)
    return sorted(ops, key=key)


def order_for_reading(ops: list[Op], order: str, reading: str) -> list[Op]:
    """`ops` in load order under one of LOAD_READINGS."""
    if reading == "vanilla_first":
        return sort_ops(ops, order, vanilla_first=True)
    ordered = sort_ops(ops, order, vanilla_first=False)
    if reading == "creations_first":
        # Every bare definition (vanilla's included) first, then every directive.
        return ([o for o in ordered if o.directive is None]
                + [o for o in ordered if o.directive is not None])
    return ordered


def simulate(ops_in_order: list[Op], bare_rule: str) -> tuple[frozenset, list[dict]]:
    """Apply each definition in order (LOAD_ORDER_MODEL["directives"],
    ["bare_duplicate"]). Returns (the definitions whose content is in the final
    entry, trace). `bare_rule` is FIRST_WINS or LAST_WINS."""
    surviving: set = set()
    present = False
    trace = []
    for op in ops_in_order:
        d = op.directive
        if d is None:
            if not present:
                present, surviving, effect = True, {op}, "created"
            elif bare_rule == FIRST_WINS:
                effect = "dropped_duplicate"
            else:
                surviving, effect = {op}, "redefined"
        elif d in REPLACE_DIRECTIVES:
            if present:
                surviving, effect = {op}, "replaced"
            elif d == "REPLACE_OR_CREATE":
                present, surviving, effect = True, {op}, "created"
            else:
                effect = "skipped_no_entry" if d.startswith("TRY_") else "error_no_entry"
        elif d in INJECT_DIRECTIVES:
            if present:
                surviving.add(op)
                effect = "injected"
            elif d == "INJECT_OR_CREATE":
                present, surviving, effect = True, {op}, "created"
            else:
                effect = "skipped_no_entry" if d.startswith("TRY_") else "error_no_entry"
        else:
            raise ValueError(f"unknown directive {d!r}")
        trace.append({"side": op.side, "path": op.path, "line": op.line,
                      "directive": d, "effect": effect})
    return frozenset(surviving), trace


def verdict_for(surviving: Iterable[Op]) -> str:
    """Whose content is in the final entry."""
    sides = {op.side for op in surviving}
    ours, theirs = OURS in sides, THEIRS in sides
    if ours and theirs:
        return BOTH_MERGE
    if theirs:
        return OURS_WIPED
    if ours:
        return THEIRS_WIPED
    return BOTH_WIPED


def _later_side(ours: list[Op], theirs: list[Op], order: str) -> str:
    last = sort_ops([*ours, *theirs], order)[-1]
    other = theirs if last.side == OURS else ours
    if last.path and any(o.path and same_path(o.path, last.path) for o in other):
        return "same_path"
    return last.side


def later_file(ours: list[Op], theirs: list[Op]) -> str:
    """Whose last definition is read later: ours, theirs, same_path (one file
    both ship) or depends_on_case (the file orders disagree)."""
    sides = {_later_side(ours, theirs, order) for order in file_orders()}
    return sides.pop() if len(sides) == 1 else "depends_on_case"


def order_depends_on_case(ours: list[Op], theirs: list[Op]) -> bool:
    """True when some file of ours and some file of theirs sort one way under
    one of the possible file orders and the other way under another."""
    orders = file_orders()
    for o in ours:
        for t in theirs:
            if not (o.path and t.path) or same_path(o.path, t.path):
                continue
            if len({name_key(o.path, x) < name_key(t.path, x) for x in orders}) > 1:
                return True
    return False


def resolve(ours: list[Op], theirs: list[Op], vanilla, bare_rule: str,
            ours_files: Optional[Iterable[str]] = None,
            theirs_files: Optional[Iterable[str]] = None) -> dict:
    """The verdict for one key both mods define.

    `vanilla`: None (unknown whether vanilla has the key), False (it doesn't),
    or a list of vanilla Ops (path None when only the snapshot is known).
    `bare_rule`: FIRST_WINS, LAST_WINS or UNKNOWN (both tried).
    `ours_files`, `theirs_files`: every file path each mod ships in the
    database, defining this key or not (a file at the other mod's or
    vanilla's path replaces it either way); default: the ops' own paths.

    Every combination of the unknowns is simulated: the file-name order
    (file_orders()), which mod the playset loads later (only when one ships a
    file at a path where the other defines the key), whether vanilla has the
    key, the bare-duplicate rule, and the load reading (load_readings()).
    When they all agree that is the verdict; otherwise the verdict names the
    one unknown that changes it (order_depends_on_case, depends_on_playset),
    or `undetermined`; `depends_on` names the unknowns that change it.

    Returns {verdict, later_file, order_depends_on_case, ours_lost,
    theirs_lost (definitions whose content doesn't reach the final entry),
    trace_scenario, trace} or, when the scenarios disagree, {verdict,
    depends_on, verdict_by_scenario (one row per combination of the deciding
    unknowns), ...}."""
    o_files = {p.casefold() for p in (ours_files if ours_files is not None
                                       else [o.path for o in ours if o.path])}
    t_files = {p.casefold() for p in (theirs_files if theirs_files is not None
                                      else [t.path for t in theirs if t.path])}
    # Our definitions in a file theirs also ships, and theirs in one we ship:
    # whichever mod the playset loads later replaces that file.
    ours_shadowed = {o.path.casefold() for o in ours if o.path} & t_files
    theirs_shadowed = {t.path.casefold() for t in theirs if t.path} & o_files
    shared = ours_shadowed | theirs_shadowed
    dims = {
        "file_order": list(file_orders()),
        "later_mod": ["theirs", "ours"] if shared else [None],
        "in_vanilla": [True, False] if vanilla is None else [bool(vanilla)],
        "bare_duplicate": [FIRST_WINS, LAST_WINS] if bare_rule == UNKNOWN else [bare_rule],
        "load_reading": list(load_readings()),
    }
    names = list(dims)
    # Each scenario's outcome: the verdict plus which of each side's
    # definitions didn't survive, so a scenario that loses one of our two
    # INJECTs differs from one that keeps both even when both read both_merge.
    results = {}
    traces = {}
    mod_paths = o_files | t_files
    for combo in product(*(dims[n] for n in names)):
        sc = dict(zip(names, combo))
        ops = []
        if sc["in_vanilla"]:
            vops = vanilla if isinstance(vanilla, list) and vanilla else [Op(VANILLA, None, 0)]
            # A mod file at a vanilla file's path replaces it.
            ops += [v for v in vops if v.path is None or v.path.casefold() not in mod_paths]
        if sc["later_mod"] == "theirs":
            ops += [o for o in ours if not (o.path and o.path.casefold() in ours_shadowed)]
            ops += list(theirs)
        elif sc["later_mod"] == "ours":
            ops += list(ours)
            ops += [t for t in theirs if not (t.path and t.path.casefold() in theirs_shadowed)]
        else:
            ops += [*ours, *theirs]
        ordered = order_for_reading(ops, sc["file_order"], sc["load_reading"])
        surviving, trace = simulate(ordered, sc["bare_duplicate"])
        results[combo] = (
            verdict_for(surviving),
            tuple(o for o in ours if o not in surviving),
            tuple(t for t in theirs if t not in surviving),
        )
        traces[combo] = trace

    first = next(iter(results))
    out = {
        "later_file": later_file(ours, theirs),
        "order_depends_on_case": order_depends_on_case(ours, theirs),
        "trace_scenario": {n: v for n, v in zip(names, first) if v is not None},
        "trace": traces[first],
    }
    outcomes = set(results.values())
    if len(outcomes) == 1:
        verdict, ours_lost, theirs_lost = outcomes.pop()
        out["verdict"] = verdict
        out["ours_lost"] = list(ours_lost)
        out["theirs_lost"] = list(theirs_lost)
        return out

    def changes_outcome(idx: int) -> bool:
        """Some scenario's outcome changes when only dimension `idx` does."""
        return any(
            results[combo[:idx] + (alt,) + combo[idx + 1:]] != outcome
            for combo, outcome in results.items()
            for alt in dims[names[idx]]
        )

    deciding = [n for i, n in enumerate(names) if len(dims[n]) > 1 and changes_outcome(i)]
    if deciding == ["file_order"]:
        out["verdict"] = ORDER_DEPENDS_ON_CASE
    elif deciding == ["later_mod"]:
        out["verdict"] = DEPENDS_ON_PLAYSET
    else:
        out["verdict"] = UNDETERMINED
    out["depends_on"] = deciding
    # The outcome is a function of the deciding unknowns alone (any other one
    # never changes it), so one row per combination of them says it all.
    rows = {}
    for combo, (verdict, ours_lost, theirs_lost) in results.items():
        key = tuple(v for n, v in zip(names, combo) if n in deciding)
        rows.setdefault(key, {**dict(zip(deciding, key)), "verdict": verdict,
                              "ours_lost": list(ours_lost), "theirs_lost": list(theirs_lost)})
    out["verdict_by_scenario"] = list(rows.values())
    return out


def resolve_later_wins(ours: list[Op], theirs: list[Op]) -> dict:
    """For a value the later file sets (a define, an on_action effect):
    whose copy is read last, under each unknown."""
    lf = later_file(ours, theirs)
    shared = {o.path.casefold() for o in ours if o.path} & {t.path.casefold() for t in theirs if t.path}
    if shared:
        # The two `same_path` files never both load; whichever mod loads later wins.
        winner = DEPENDS_ON_PLAYSET
    elif lf == "depends_on_case":
        winner = ORDER_DEPENDS_ON_CASE
    else:
        winner = lf
    return {"later_file": lf, "order_depends_on_case": order_depends_on_case(ours, theirs),
            "winner": winner}


# ---------------------------------------------------------------------------
# Vanilla
# ---------------------------------------------------------------------------

class VanillaIndex:
    """Which keys vanilla defines per database: from the game files when
    `game_common` exists (with file names; a folder vanilla lacks has no
    keys), else from the `vanilla_parsed/` snapshot (keys only), else unknown
    (LOAD_ORDER_MODEL["vanilla_source"]). `keys` ({db: iterable}) replaces
    both, for tests."""

    def __init__(self, game_common: Optional[str] = None, snapshot_dir: Optional[str] = SNAPSHOT_DIR,
                 keys: Optional[dict] = None):
        self.game_common = game_common if game_common and os.path.isdir(game_common) else None
        self.snapshot_dir = snapshot_dir
        self._keys = {db: set(v) for db, v in keys.items()} if keys is not None else None
        self._cache: dict = {}
        self._manifest = None

    @classmethod
    def default(cls) -> "VanillaIndex":
        try:
            import path_constants
            game = os.path.join(path_constants.base_game_path, "game", "common")
        except Exception:  # noqa: BLE001 - no install configured
            game = None
        return cls(game_common=game)

    def source(self, db: str) -> Optional[str]:
        return self._load(db)[0]

    def ops(self, db: str, key: str):
        """None (unknown), False (not in vanilla) or a list of Ops."""
        src, data = self._load(db)
        if src is None:
            return None
        if key not in data:
            return False
        return data[key]

    def scan(self, db: str) -> Optional[dict]:
        """{key: [Entry]} for a vanilla folder read from the game files."""
        if not self.game_common:
            return None
        return self._game_entries(db)

    def _load(self, db: str):
        if db in self._cache:
            return self._cache[db]
        result = (None, {})
        if self._keys is not None:
            if db in self._keys:
                result = ("given", {k: [Op(VANILLA, None, 0)] for k in self._keys[db]})
        elif self.game_common:
            # A folder vanilla doesn't have means no vanilla key, not unknown.
            entries = self._game_entries(db)
            result = ("game_files", {
                k: [Op(VANILLA, path, e.line, e.directive) for path, e in lst]
                for k, lst in entries.items()
            })
        else:
            keys = self._snapshot_keys(db)
            if keys is not None:
                result = ("vanilla_parsed", {k: [Op(VANILLA, None, 0)] for k in keys})
        self._cache[db] = result
        return result

    def _game_dir(self, db: str) -> str:
        return os.path.join(self.game_common, *db.split("/"))

    def _game_entries(self, db: str) -> dict:
        key = ("entries", db)
        if key in self._cache:
            return self._cache[key]
        out: dict = defaultdict(list)
        base = self._game_dir(db)
        if os.path.isdir(base):
            for rel in list_files(base):
                if not rel.endswith(".txt"):
                    continue
                entries, _w = scan_script(read_text(os.path.join(base, rel)))
                for e in _flatten(db, entries):
                    out[e.key].append((rel, e))
        self._cache[key] = out
        return out

    def _snapshot_keys(self, db: str) -> Optional[set]:
        if not self.snapshot_dir:
            return None
        if self._manifest is None:
            try:
                with open(os.path.join(self.snapshot_dir, "manifest.json"), encoding="utf-8") as f:
                    self._manifest = json.load(f)
            except (OSError, ValueError):
                self._manifest = {}
        for _et, info in (self._manifest.get("entity_types") or {}).items():
            if info.get("dir") == f"game/common/{db}":
                try:
                    with open(os.path.join(self.snapshot_dir, info["file"]), encoding="utf-8") as f:
                        return set(json.load(f))
                except (OSError, ValueError, KeyError):
                    return None
        return None


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------

def _flatten(db: str, entries: list[Entry]) -> list[Entry]:
    """A wrapper folder's entries are the wrapper block's children."""
    wrapper = WRAPPER_DIRS.get(db)
    if not wrapper:
        return entries
    out = []
    for e in entries:
        if e.key == wrapper:
            for k, line, value in e.children:
                d, key = split_directive(k)
                out.append(Entry(k, key, d, line, value))
    return out


@dataclass
class DbScan:
    files: list = field(default_factory=list)          # paths within the db
    entries: dict = field(default_factory=lambda: defaultdict(list))  # key -> [(path, Entry)]


def _scan_db(root: str, db: str, files: list[str], warnings: list, side: str) -> DbScan:
    out = DbScan(files=list(files))
    for rel in files:
        if not rel.endswith(".txt"):
            continue
        full = os.path.join(root, "common", *db.split("/"), *rel.split("/"))
        try:
            entries, w = scan_script(read_text(full))
        except OSError as exc:
            warnings.append({"side": side, "file": f"common/{db}/{rel}", "warning": str(exc)})
            continue
        for msg in w:
            warnings.append({"side": side, "file": f"common/{db}/{rel}", "warning": msg})
        for e in _flatten(db, entries):
            out.entries[e.key].append((rel, e))
    return out


def _common_files(root: str, git_fallback: bool = False) -> dict[str, list[str]]:
    """{database: [path within it]} for a mod's `common/` (git_fallback: see
    list_files; this mod's root only)."""
    out: dict = defaultdict(list)
    for rel in list_files(root, "common", git_fallback):
        split = split_common_path(rel[len("common/"):])
        if split:
            out[split[0]].append(split[1])
    return out


def _ref(db: str, path: Optional[str], entry: Optional[Entry] = None) -> dict:
    ref = {"file": f"common/{db}/{path}" if path else None}
    if entry is not None:
        ref["line"] = entry.line
        ref["directive"] = entry.directive
    return ref


def _fields(lst) -> set:
    return {split_directive(k)[1] for _p, e in lst for k, _l, _v in e.children}


def key_collisions(db: str, ours: DbScan, theirs: DbScan, vanilla: VanillaIndex,
                   include_trace: bool = True) -> list[dict]:
    rule = rule_for(db)
    out = []
    for key in sorted(set(ours.entries) & set(theirs.entries)):
        o_list, t_list = ours.entries[key], theirs.entries[key]
        o_ops = [Op(OURS, p, e.line, e.directive) for p, e in o_list]
        t_ops = [Op(THEIRS, p, e.line, e.directive) for p, e in t_list]
        v = vanilla.ops(db, key)
        res = resolve(o_ops, t_ops, v, rule.bare_duplicate,
                      ours_files=ours.files, theirs_files=theirs.files)
        row = {
            "entity_type": db,
            "server_type": SERVER_TYPES.get(db),
            "key": key,
            "theirs": [_ref(db, p, e) for p, e in t_list],
            "ours": [_ref(db, p, e) for p, e in o_list],
            "in_vanilla": None if v is None else bool(v),
            "later_file": res["later_file"],
            "order_depends_on_case": res["order_depends_on_case"],
            "verdict": res["verdict"],
        }
        def refs(ops):
            return [f"common/{db}/{op.path}:{op.line}" for op in ops]

        if "verdict_by_scenario" in res:
            row["depends_on"] = res["depends_on"]
            row["verdict_by_scenario"] = [
                {**sc, "ours_lost": refs(sc["ours_lost"]), "theirs_lost": refs(sc["theirs_lost"])}
                for sc in res["verdict_by_scenario"]
            ]
        else:
            # A partial loss: e.g. both_merge, but one of our two INJECTs sorts
            # before their REPLACE.
            row["ours_lost"] = refs(res["ours_lost"])
            row["theirs_lost"] = refs(res["theirs_lost"])
        both = sorted(_fields(o_list) & _fields(t_list))
        if both:
            row["fields_both_set"] = both[:50]
        if rule.kind == "unknown" and any(e.directive for _p, e in (*o_list, *t_list)):
            row["note"] = "whether this folder takes directives isn't recorded"
        if include_trace:
            row["trace_scenario"] = res["trace_scenario"]
            row["trace"] = [
                {**{k: v for k, v in step.items() if k != "path"},
                 "file": (None if not step["path"] else
                          f"{'game/' if step['side'] == VANILLA else ''}common/{db}/{step['path']}")}
                for step in res["trace"]
            ]
        out.append(row)
    return out


def define_collisions(ours: DbScan, theirs: DbScan, vanilla: VanillaIndex) -> list[dict]:
    def by_key(scan: DbScan):
        out = defaultdict(list)
        for block, lst in scan.entries.items():
            for path, e in lst:
                for k, line, value in e.children:
                    out[(block, k)].append((path, line, value))
        return out

    o, t = by_key(ours), by_key(theirs)
    vanilla_values = {}
    vscan = vanilla.scan("defines")
    if vscan:
        for block, lst in vscan.items():
            for _path, e in lst:
                for k, _line, value in e.children:
                    vanilla_values[(block, k)] = value
    rows = []
    for block, key in sorted(set(o) & set(t)):
        o_sorted = sorted(o[(block, key)])
        t_sorted = sorted(t[(block, key)])
        res = resolve_later_wins([Op(OURS, p, ln) for p, ln, _v in o_sorted],
                                 [Op(THEIRS, p, ln) for p, ln, _v in t_sorted])
        ours_last, theirs_last = o_sorted[-1], t_sorted[-1]
        rows.append({
            "block": block,
            "key": key,
            "ours": ours_last[2],
            "theirs": theirs_last[2],
            "ours_file": {"file": f"common/defines/{ours_last[0]}", "line": ours_last[1]},
            "theirs_file": {"file": f"common/defines/{theirs_last[0]}", "line": theirs_last[1]},
            "vanilla": vanilla_values.get((block, key)) if vscan else None,
            "same_value": ours_last[2] == theirs_last[2],
            **res,
        })
    return rows


def on_action_overlap(ours: DbScan, theirs: DbScan) -> tuple[list[str], list[dict]]:
    hooks = sorted(set(ours.entries) & set(theirs.entries))
    conflicts = []
    for hook in hooks:
        def fields(lst):
            out = defaultdict(list)
            for path, e in lst:
                for k, line, _v in e.children:
                    out[split_directive(k)[1]].append((path, line))
            return out
        of, tf = fields(ours.entries[hook]), fields(theirs.entries[hook])
        for name in sorted(set(of) & set(tf)):
            if name in ADDITIVE_ON_ACTION_FIELDS:
                continue
            res = resolve_later_wins([Op(OURS, p, ln) for p, ln in of[name]],
                                     [Op(THEIRS, p, ln) for p, ln in tf[name]])
            overwrites = name in OVERWRITING_ON_ACTION_FIELDS
            conflicts.append({
                "hook": hook,
                "field": name,
                "ours": [{"file": f"common/on_actions/{p}", "line": ln} for p, ln in of[name]],
                "theirs": [{"file": f"common/on_actions/{p}", "line": ln} for p, ln in tf[name]],
                "rule": ("overwrites: the later file's block replaces the earlier one"
                         if overwrites else "unknown: not recorded whether this field adds up"),
                "later_file": res["later_file"],
                "order_depends_on_case": res["order_depends_on_case"],
                "winner": res["winner"] if overwrites else UNDETERMINED,
            })
    return hooks, conflicts


def _scan_events(root: str, files: list[str], warnings: list, side: str):
    namespaces = defaultdict(list)
    ids = defaultdict(list)
    for rel in files:
        if not rel.endswith(".txt"):
            continue
        entries, w = scan_script(read_text(os.path.join(root, *rel.split("/"))))
        for msg in w:
            warnings.append({"side": side, "file": rel, "warning": msg})
        for e in entries:
            if e.key == "namespace" and e.value:
                namespaces[e.value.strip('"')].append({"file": rel, "line": e.line})
            elif e.value is None and _EVENT_ID_RE.match(e.key):
                ids[e.key].append({"file": rel, "line": e.line})
    return namespaces, ids


def event_collisions(ours_root: str, ours_files, theirs_root: str, theirs_files, warnings):
    o_ns, o_ids = _scan_events(ours_root, ours_files, warnings, OURS)
    t_ns, t_ids = _scan_events(theirs_root, theirs_files, warnings, THEIRS)
    namespaces = [
        {"namespace": ns, "ours": o_ns[ns], "theirs": t_ns[ns],
         "colliding_ids": sorted(i for i in set(o_ids) & set(t_ids) if i.split(".")[0] == ns)}
        for ns in sorted(set(o_ns) & set(t_ns))
    ]
    id_rows = []
    for event_id in sorted(set(o_ids) & set(t_ids)):
        o_ops = [Op(OURS, r["file"], r["line"]) for r in o_ids[event_id]]
        t_ops = [Op(THEIRS, r["file"], r["line"]) for r in t_ids[event_id]]
        res = resolve_later_wins(o_ops, t_ops)
        id_rows.append({
            "id": event_id,
            "ours": o_ids[event_id],
            "theirs": t_ids[event_id],
            "later_file": res["later_file"],
            "verdict": DEPENDS_ON_PLAYSET if res["winner"] == DEPENDS_ON_PLAYSET else UNDETERMINED,
            "rule": "the copy read first survives; events aren't read in file-name order, so "
                    "which is first is unknown (LOAD_ORDER_MODEL['events'])",
        })
    return namespaces, id_rows


def _loc_sub(rel: str) -> tuple[str, bool]:
    """(path within its English loc folder, whether it is a replace/ file)
    for a file under one of _LOC_DIRS."""
    if rel.startswith(_LOC_REPLACE_DIR + "/"):
        return "replace/" + rel[len(_LOC_REPLACE_DIR) + 1:], True
    sub = rel[len(_LOC_DIR) + 1:]
    return sub, sub.split("/")[0] == "replace"


def _loc_files(files: Iterable[str]) -> list[str]:
    return [p for p in files if any(p.startswith(d + "/") for d in _LOC_DIRS)]


def _scan_loc(root: str, files: list[str]) -> dict:
    keys = {}
    for rel in files:
        if not rel.endswith(".yml"):
            continue
        sub, replace = _loc_sub(rel)
        try:
            text = read_text(os.path.join(root, *rel.split("/")))
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            parsed = split_loc_line(line)
            if parsed is None:
                continue
            key, value, _trailing = parsed
            keys[key] = {"file": rel, "line": lineno, "replace": replace,
                         "_sub": sub, "_value": value.strip()}
    return keys


def loc_collisions(ours_root, ours_files, theirs_root, theirs_files) -> list[dict]:
    o, t = _scan_loc(ours_root, ours_files), _scan_loc(theirs_root, theirs_files)
    rows = []
    for key in sorted(set(o) & set(t)):
        a, b = o[key], t[key]
        if a["replace"] != b["replace"]:
            winner, lf = (OURS if a["replace"] else THEIRS), None
            basis = "a replace/ file overrides one outside it (LOAD_ORDER_MODEL['localization'])"
        else:
            res = resolve_later_wins([Op(OURS, a["_sub"], a["line"])], [Op(THEIRS, b["_sub"], b["line"])])
            lf = res["later_file"]
            winner = DEPENDS_ON_PLAYSET if res["winner"] == DEPENDS_ON_PLAYSET else UNDETERMINED
            basis = "which of two same-kind files wins is unknown (LOAD_ORDER_MODEL['localization'])"
        rows.append({
            "key": key,
            "ours": {k: v for k, v in a.items() if not k.startswith("_")},
            "theirs": {k: v for k, v in b.items() if not k.startswith("_")},
            "same_text": a["_value"] == b["_value"],
            "later_file": lf,
            "winner": winner,
            "basis": basis,
        })
    return rows


def _our_loc_deploy_name(rel: str) -> Optional[str]:
    """Their `localization/<lang>/x_l_<lang>.yml` -> the English file of ours
    that deploy.sh copies to that path (gen_non_english_loc.py)."""
    m = re.match(r"^localization/([^/]+)/(.*)_l_\1\.yml$", rel)
    if not m or m.group(1) == "english":
        return None
    return f"localization/english/{m.group(2)}_l_english.yml"


def path_collisions(ours_root: str, their_files: list[str]) -> list[dict]:
    tops = sorted({p.split("/")[0] for p in their_files})
    ours = {}
    for top in tops:
        for p in list_files(ours_root, top, git_fallback=True):
            ours.setdefault(p.casefold(), p)
    need_english = any(_our_loc_deploy_name(p) for p in their_files)
    english = {}
    if need_english:
        english = {p.casefold(): p for p in list_files(ours_root, _LOC_DIR, git_fallback=True)}
    rows = []
    for p in their_files:
        if p.lower().endswith(_NOT_GAME_FILES):
            continue
        ours_p = ours.get(p.casefold())
        generated = False
        if ours_p is None:
            src = _our_loc_deploy_name(p)
            if src and src.casefold() in english:
                ours_p, generated = english[src.casefold()], True
        if ours_p is None:
            continue
        row = {"path": p, "area": p.split("/")[0],
               "effect": "the mod the playset loads later replaces the other's file whole"}
        if ours_p != p:
            row["ours_path"] = ours_p
        if generated:
            row["ours_generated_at_deploy_from"] = ours_p
            row.pop("ours_path", None)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def analyze(theirs_root: str, ours_root: str, vanilla: Optional[VanillaIndex] = None,
            include_trace: bool = False) -> dict:
    """The overlap report for the mod at `theirs_root` against `ours_root`.
    Only `ours_root` is ever listed through git (list_files)."""
    if vanilla is None:
        vanilla = VanillaIndex.default()
    elif isinstance(vanilla, dict):
        vanilla = VanillaIndex(keys=vanilla)
    their_files = _their_files(theirs_root)
    warnings: list = []

    t_common = _common_files(theirs_root)
    o_common = _common_files(ours_root, git_fallback=True)
    dirs, collisions = [], []
    defines, hooks, oa_conflicts = [], [], []
    for db in sorted(t_common):
        rule = rule_for(db)
        row = {"dir": db, "server_type": SERVER_TYPES.get(db), "rule": rule.as_dict(),
               "theirs_files": len(t_common[db]), "ours_files": len(o_common.get(db, []))}
        dirs.append(row)
        if db not in o_common or rule.kind == "additive":
            continue
        t_scan = _scan_db(theirs_root, db, t_common[db], warnings, THEIRS)
        o_scan = _scan_db(ours_root, db, o_common[db], warnings, OURS)
        if rule.kind == "defines":
            defines = define_collisions(o_scan, t_scan, vanilla)
        elif rule.kind == "on_actions":
            hooks, oa_conflicts = on_action_overlap(o_scan, t_scan)
        else:
            found = key_collisions(db, o_scan, t_scan, vanilla, include_trace)
            collisions.extend(found)
            row["vanilla_source"] = vanilla.source(db) if found else None

    t_events = [p for p in their_files if p.startswith("events/")]
    ns_rows, id_rows = [], []
    if t_events:
        o_events = list_files(ours_root, "events", git_fallback=True)
        ns_rows, id_rows = event_collisions(ours_root, o_events, theirs_root, t_events, warnings)

    t_loc = _loc_files(their_files)
    loc_rows = []
    if t_loc:
        o_loc = [p for d in _LOC_DIRS for p in list_files(ours_root, d, git_fallback=True)]
        loc_rows = loc_collisions(ours_root, o_loc, theirs_root, t_loc)

    paths = path_collisions(ours_root, their_files)
    by_verdict = Counter(c["verdict"] for c in collisions)
    return {
        "mod_name": read_mod_name(theirs_root),
        "path": theirs_root,
        "ours": ours_root,
        "files_scanned": len(their_files),
        "summary": {
            "key_collisions": len(collisions),
            "by_verdict": dict(sorted(by_verdict.items())),
            "defines": len(defines),
            "additive_hooks": len(hooks),
            "on_action_conflicts": len(oa_conflicts),
            "loc_collisions": len(loc_rows),
            "event_namespace_collisions": len(ns_rows),
            "event_id_collisions": len(id_rows),
            "path_collisions": len(paths),
            "scan_warnings": len(warnings),
        },
        "path_collisions": paths,
        "key_collisions": collisions,
        "defines": defines,
        "additive_hooks": hooks,
        "on_action_conflicts": oa_conflicts,
        "loc_collisions": loc_rows,
        "event_namespace_collisions": ns_rows,
        "event_id_collisions": id_rows,
        "dirs": dirs,
        "load_order_model": LOAD_ORDER_MODEL,
        "scan_warnings": warnings,
    }


def validate_root(path: Optional[str]) -> str:
    """The mod root to scan, or ValueError with the reason. A folder with no
    `.metadata/metadata.json`, no `descriptor.mod` and none of `common/`,
    `events/`, `gui/`, `localization/` is refused: that is the Workshop folder
    with the mod's id left off, or some other folder, and walking it gives a
    clean report of nothing (and holds the single-threaded server)."""
    if not path:
        raise ValueError("pass the mod's root folder: ?path=<mod root>")
    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        raise ValueError(f"not a directory: {path}")
    if not (any(os.path.isfile(os.path.join(path, m)) for m in _MOD_MARKERS)
            or any(os.path.isdir(os.path.join(path, d)) for d in _MOD_DIRS)):
        raise ValueError(
            f"not a mod root: {path} has no .metadata/metadata.json, descriptor.mod, "
            "common/, events/, gui/ or localization/ (a Workshop mod is "
            ".../workshop/content/529340/<id>)")
    return os.path.abspath(path)


def _print_summary(report: dict) -> None:
    s = report["summary"]
    print(f"{report['mod_name'] or '(no name)'}  {report['path']}")
    print(f"files scanned: {report['files_scanned']}")
    print(f"key collisions: {s['key_collisions']}  {s['by_verdict']}")
    for c in report["key_collisions"]:
        t = ", ".join(f"{r['file']}:{r['line']} {r['directive'] or 'bare'}" for r in c["theirs"])
        o = ", ".join(f"{r['file']}:{r['line']} {r['directive'] or 'bare'}" for r in c["ours"])
        print(f"  {c['verdict']:<22} {c['entity_type']}/{c['key']}  theirs: {t}  ours: {o}")
    print(f"defines both set: {s['defines']}")
    for d in report["defines"]:
        print(f"  {d['block']}.{d['key']}: ours {d['ours']} theirs {d['theirs']} -> {d['winner']}")
    print(f"additive hooks: {s['additive_hooks']}  on_action conflicts: {s['on_action_conflicts']}")
    for c in report["on_action_conflicts"]:
        print(f"  {c['hook']}.{c['field']} -> {c['winner']}")
    print(f"loc collisions: {s['loc_collisions']}  event namespaces: "
          f"{s['event_namespace_collisions']}  event ids: {s['event_id_collisions']}")
    print(f"path collisions: {s['path_collisions']}")
    for p in report["path_collisions"]:
        print(f"  {p['path']}")
    if report["scan_warnings"]:
        print(f"scan warnings: {len(report['scan_warnings'])}")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("path", help="the other mod's root folder")
    ap.add_argument("--ours", default=REPO_ROOT, help="this mod's root (default: this checkout)")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    ap.add_argument("--trace", action="store_true",
                    help="add each collision's simulated load (first scenario)")
    args = ap.parse_args(argv)
    try:
        root = validate_root(args.path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    report = analyze(root, os.path.abspath(args.ours), include_trace=args.trace)
    if args.json:
        json.dump(report, sys.stdout, indent=1, ensure_ascii=False)
        print()
    else:
        _print_summary(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
