"""Asset paths named in mod script that resolve to no file (#1156).

The engine looks a texture or video up only when it first renders it, and
only then logs the miss (`VFSOpen Error`, `has missing texture`), so a path
nobody has looked at yet stays broken. Two log triages in a row found one by
hand: #1143's 36 buildings with no `background`, and #1155's
`te_orbital_network_disrupted` modifier, whose `icon` named a
`timed_modifier_icons/` file vanilla doesn't have (88 `VFSOpen Error` lines in
half an hour).

What is checked
---------------
Every value in the mod's `common/**/*.txt`, `events/**/*.txt` and
`gui/**/*.gui` (comments stripped) shaped like an asset path, whatever its
field: one that starts with `gfx/` (or `dlc/<folder>/gfx/`, the form
vanilla's `common/themes` uses), or one with no space in it that ends in an
image or video extension (`.dds`, `.png`, `.tga`, `.jpg`, `.bk2`). That covers
`icon`, `texture`, `background`, `event_image = { texture = ... }`, GUI
`texture` / `effect` / `environment` and the rest without listing field
names. One leading `/` is dropped, as vanilla's parties write
`"/gfx/interface/icons/political_parties/..."`. Text with a space in it that
doesn't start at `gfx/` is display text, as is anything in `raw_text`,
`raw_tooltip`, `text` or `tooltip` (vanilla's GUI component library prints
file names there). A `gfx/` path may hold spaces: vanilla has files such as
`gfx/event_pictures/placeholder_event scene.bk2`.

A `video = <name>` with a bare identifier is a media alias (vanilla's
`gfx/media_aliases/*.txt`), not a file: `video = "ip3_village_school"` plays
`ip3_villageschool.bk2` and falls back to another alias without the DLC. It
must name an alias; its target isn't followed.

A path resolves against the mod's tracked files (`git ls-files gfx/`, never
the disk: CI and sparse worktrees have no `gfx/`) and vanilla's mounts:
`game/gfx`, `jomini/gfx` and `clausewitz/gfx` under the install (the engine's
`gfx/FX/pdxgui_default.shader` and `gfx/editor_gui/default_icon.dds` live in
the last), plus each `game/dlc/*/gfx`, which the engine mounts at the same
`gfx/...` paths for a player who owns the DLC. In `common/coat_of_arms/` and
`common/defines/`, where vanilla names emblems and patterns by bare file name
(6,239 of them), a bare name resolves against `gfx/coat_of_arms/patterns/`,
`colored_emblems/` and `textured_emblems/`.

Kinds:
  * `missing` (error): no file at that path in any casing. A file that is on
    disk but not tracked by git says so: `git add` it.
  * `case_mismatch` (error): a file matches only case-insensitively. The game
    on Windows, and under Proton or Wine, still finds it, so this isn't a
    player-visible break today; it is an error to keep paths canonical.
    Vanilla's own script has none in ~25,000 references, nor the mod's, and a
    tool reading the files on a case-sensitive file system misses them.
  * `unknown_media_alias` (error): `video = name` that no alias defines.
  * `unrooted` (error): a file name or path that doesn't start at `gfx/`
    outside the coat-of-arms files (`icon = "modifier_coins_negative.dds"`,
    `video = "foo.bk2"`). The engine reads asset paths from the game's root.
  * `unknown_extension` (error): a `gfx/` path whose extension is neither an
    `ASSET_EXTENSIONS` one nor a `NON_ASSET_EXTENSIONS` one, or that has none:
    a typo such as `.dss`.
  * `backslash` (error): `\\` separators. Vanilla's script uses `/` only.
  * `whitespace` (error): spaces around a path inside its quotes.
  * `undeclared` (error): an entity that names no art in a field its type
    needs (Declarations, below).
  * `dlc_only` (warning, never fails `--strict`): the file, or the alias, is
    only in a DLC's folder, so a player without that DLC gets the
    missing-texture placeholder. Fine in a DLC-gated event; vanilla does it.
Skipped, and counted in the report:
  * `templated`: a path or alias built from a `$PARAM$` or a `[...]`
    expression, which can't be resolved statically.
  * `other_extension`: a `gfx/` path with a `NON_ASSET_EXTENSIONS` extension
    (meshes, entities and animations, which script names by entity name, and
    which the catalog leaves out).
Run over vanilla's own `common/`, `events/` and `gui/` (25,418 references),
the audit finds one `missing` (`gui/texticons.gui`'s `alert_icons/repairing.dds`,
a vanilla bug the mod doesn't inherit) and 34 `dlc_only`, all in DLC content.

Vanilla source
--------------
With the game installed (`<base_game_path>/game/gfx` exists) the install is
listed live (a few seconds on `/mnt/c`). Without it, as in CI, the committed
catalog `docs/engine/vanilla_asset_paths.txt` stands in: every vanilla, jomini,
clausewitz and DLC file with an `ASSET_EXTENSIONS` extension, plus every media
alias name. The scanner and the catalog share `ASSET_EXTENSIONS`, so a fresh
catalog and the live install give the same flags. Re-bootstrap it on every
vanilla bump (`vanilla_patch_runbook.md` § 4):

    python3 texture_reference_audit.py --bootstrap

A live run warns when the committed catalog no longer matches the install
(`catalog_stale`, one of the server's reload warning keys), and
`test_texture_reference_audit` fails CI when the catalog's game version isn't
`vanilla_parsed/manifest.json`'s, so a vanilla bump that rebuilds the snapshot
without `--bootstrap` doesn't pass. The listing is cached per install state
for the server's lifetime. The catalog holds the DLCs installed on the
machine that built it.

Declarations (#1182)
-------------------
A path check can't see a field nobody wrote. #1143's 36 buildings named no
`background` at all, and the engine logged `Database type <key> has missing
texture` (`guitexturehandler.h:155`) once per launch for each. So, for each
entity type in `DECLARED_FIELDS`, every entity the mod defines in
`common/<folder>/` must declare the field with a non-empty value (`undeclared`,
an error), on the entity's own opening line for suppression. A field is a key
in the entity's block or a `/` path into a nested one
(`combat_unit_image/texture`). A block counts only when it holds a non-empty
value (`icon = {}` doesn't); a key inside a bare `{ }` list item isn't the
entity's; a directive on a nested key (`REPLACE:icon`) is dropped from its name.

Which definitions count (`_final_definition`):
  * A plain `REPLACE:` applies after every INJECT and TRY_INJECT on its key,
    whichever file sorts first (#1185's probes), so the last one is the final
    entry: only its own fields count, the INJECTs are lost. It restates the
    whole entity: `REPLACE:pmg_aeroplanes` dropped vanilla's `texture`. With a
    plain REPLACE present, this rule wins.
  * A `TRY_REPLACE:` applies in load order (files in ASCII order of name), so
    an INJECT in a later file lands on it: its fields count with the INJECTs
    that sort after it. Whether one sorting after an INJECT wipes it is
    unprobed, so the earlier INJECTs don't count (errs toward flagging).
  * A `REPLACE_OR_CREATE:` or `INJECT_OR_CREATE:` applies up front, after the
    plain definitions and before every INJECT, even from a later file, so the
    INJECTs land on it and count. A REPLACE_OR_CREATE drops a plain
    definition's fields; an INJECT_OR_CREATE merges into it, or with no plain
    one creates the entity when vanilla has none of that name (or the
    snapshot doesn't hold the folder, where it's checked as if it created
    one; a tag clears a false positive).
  * Otherwise a plain definition is checked with its `INJECT:`s, and an
    `INJECT:` / `TRY_INJECT:` alone is into vanilla's entity, or into none
    (the engine's `inject_to_missing` line), and isn't the mod's to check.
  * A field vanilla's entity of the same name also lacks is exempt
    (`REPLACE:country_gdp_construction`; vanilla's has no icon either), read
    from `vanilla_parsed/` (`load_vanilla_snapshot`), so CI and a reload agree.
    23 registered folders aren't in the snapshot (`VanillaSnapshot.uncovered`),
    so there the exemption never applies.
  * No `building_group` fallback: no vanilla or mod building group declares
    any art field (vanilla's `buildings.md` documents `background` on the
    building, "Background texture for building registry items"), and the
    Grand Monuments name-carrier anchor logged the line in `bg_grand_monuments`,
    whose other buildings all declare one.

Which types and fields, and the evidence (checked 2026-10-26 on 1.14.5): every
`game/common/` type with three or more vanilla entities was scanned for the
art-like fields (`icon`, `texture`, `background`, `*_texture`, `*_icon`, ...)
every vanilla entity declares, and the logs (`debug`/`error` and their rotated
generations) and `git log` for `has missing texture` and `VFSOpen Error` lines
an undeclared field caused. Only two fields have a log line: `buildings`
`background` (load time, above) and `static_modifiers` `icon` (an empty-path
`VFSOpen Error:  not found` each time a list draws the modifier, 9023f1588 and
7870ddb2b). Vanilla declares the second on 6,096 of 6,128, all exempt by name:
26 engine modifiers in `00_code_static_modifiers.txt` (`base_values`, the
infamy and tax bands, ...), five in `104_modifiers.txt` that
`election_other_parties_events.txt` adds with `add_modifier`, and a test
modifier. The other 63 fields rest on vanilla convention, not on a log line:
`production_methods` and `production_method_groups` `texture` are on every
vanilla entity but `pm_dummy` and `pmg_dummy` (00_dummy.txt), a group's being
the building panel's icon for a mixed configuration
(`production_method_groups.md`), and the rest on every vanilla entity of their
type (`DECLARED_FIELDS` gives the count). An entity that is never shown can opt
out with a `(texture_reference)` tag. `treaty_articles` `icon` stays although
`treaty_articles.md` says "icon (default: empty)": that readme gives every
field its parse default that way (`cost` 0, `flags` empty), not a fallback
image, and every vanilla article has an icon for the treaty panel; the harvest
`map_texture` below is different, "none" being a map pattern of its own.
`test_texture_reference_audit` fails when a rebuilt `vanilla_parsed/` no longer
bears a covered folder out, and, on a machine with the game, scans the
uncovered folders in `game/common`.

Considered and left out:
  * `journal_entries` `icon`: optional, the engine falls back to
    `JOURNAL_ENTRY_ICON_DEFAULT` (`journal_entries.md`); 7 vanilla entries
    have none.
  * `harvest_condition_types` `map_texture`: "default - none"
    (`harvest_condition_types.md`); the mod's three market conditions have none
    on purpose.
  * `terrain` `textures`: "extra textures that could be used in specific cases"
    (`01_terrain.txt`).
  * `buildings` `icon`: 14 vanilla monuments have none, and none logs.
  * `diplomatic_actions` `texture` (27 of 55 in vanilla). The lens toolbar icon
    the engine derives from the action's key is `test_diplomatic_action_lens_icons`'s.
  * `character_interactions` `icon` (13/21), `game_concepts` `texture`
    (261/613), `cultures` `seal_and_signature_texture` (181/317),
    `coat_of_arms` `pattern` (96%): not universal. `decisions`, `amendments`,
    `political_movements` and `technology/eras` declare no art field in vanilla.
  * Non-art fields every vanilla entity has (`game_rules`'s and `pop_needs`'
    `default`).
  * Events: `event_image_audit` checks that a visible event declares art.

Overlap with other audits: `event_image_audit` checks that a visible event
declares art, not that the file exists. `scripts/analysis/check_gui_lint.py`
only warns that a texture no mod file names is "unproven", on the `.gui` files
a branch changed. `gui_reference_audit` doesn't look at textures. So this audit
covers `gui/` too. Not covered: `'gfx/...'` literals inside a GUI `[...]`
expression (none in the mod as of 2026-10-26).

Suppression is check-tagged, on the path's line, or for `undeclared` on the
entity's opening `<name> = {` line:

    # REVIEWED YYYY-MM-DD (texture_reference): rationale

It covers every flag on that line, the `dlc_only` warning included. A tag that
suppresses nothing is stale and fails `--strict`. The check name is listed in
`event_context_audit.FOREIGN_CHECKS`, which reads every tag inside an event.

Report: docs/engine/texture_reference_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import bisect
import json
import os
import re
import subprocess
from dataclasses import dataclass, field

# Merge directives (`INJECT:x`, `REPLACE:x`, ...); `_final_definition` says
# how the engine applies them.
from paradox_file_parser import directive_prefixes

CHECK = "texture_reference"
SCAN = (("common", ".txt"), ("events", ".txt"), ("gui", ".gui"))

# Extensions checked under `gfx/`, and the ones the catalog lists. The two
# must stay one set: a path the live install resolves but the catalog never
# lists would make CI and a reload disagree.
ASSET_EXTENSIONS = (".dds", ".png", ".tga", ".jpg", ".jpeg", ".bk2",
                    ".shader", ".fxh", ".txt", ".settings")
# Extensions that make a value path-shaped even without a `gfx/` prefix.
_IMAGE_EXTENSIONS = (".dds", ".png", ".tga", ".jpg", ".jpeg", ".bk2")
# Files under `gfx/` that script names by entity name, not path, and that the
# catalog leaves out. A `gfx/` path with one of these is skipped; with any
# other extension, or none, it is flagged (`unknown_extension`): `.dss`.
NON_ASSET_EXTENSIONS = (".mesh", ".asset", ".anim", ".entity", ".particle2",
                        ".editordata", ".compound", ".bin", ".cur", ".ani",
                        ".psd", ".json", ".md", ".meta")
# Fields whose value is display text: vanilla's GUI component library prints
# file names in `raw_text`.
DISPLAY_KEYS = frozenset({"raw_text", "raw_tooltip", "text", "tooltip"})
# Where vanilla names coat-of-arms art by bare file name. Such a name resolves
# against `COA_DIRS`; a bare name anywhere else is `unrooted`.
COA_CONTEXTS = ("common/coat_of_arms/", "common/defines/")
COA_DIRS = ("gfx/coat_of_arms/patterns/", "gfx/coat_of_arms/colored_emblems/",
            "gfx/coat_of_arms/textured_emblems/")

VANILLA_ROOTS = ("game", "jomini", "clausewitz")
BASE_ORIGIN = "base"  # game/, jomini/ or clausewitz/ gfx
MEDIA_ALIAS_DIR = "gfx/media_aliases"
ALIAS_PREFIX = "media_alias:"

CATALOG_REL = os.path.join("docs", "engine", "vanilla_asset_paths.txt")
REPORT_REL = os.path.join("docs", "engine", "texture_reference_report.md")

ERROR_KINDS = ("missing", "case_mismatch", "unknown_media_alias", "unrooted",
               "unknown_extension", "backslash", "whitespace", "undeclared")

# Art fields each entity of a type must declare: {folder under common/:
# (fields, evidence)}. A field is a key in the entity's block, or a `/` path
# into a nested one. Only `buildings` and `static_modifiers` have a log line
# behind them; the rest are vanilla convention (counts: vanilla's entities
# that declare it, 1.14.5), and an entity that is never shown opts out with a
# `(texture_reference)` tag. The module docstring says what was checked and
# what was left out.
_ALL = "vanilla convention, on every vanilla entity of its type"
DECLARED_FIELDS: dict[str, tuple[tuple[str, ...], str]] = {
    "buildings": (("background",),
                  "the building panel's art, on every vanilla building (115); one without logs "
                  "`Database type <key> has missing texture` at load (#1108, #1143)"),
    "static_modifiers": (("icon",),
                         "on 6,096 of vanilla's 6,128 (the rest exempt by name); one without logs "
                         "an empty-path `VFSOpen Error` whenever a modifier list draws it"),
    "production_methods": (("texture",), "vanilla convention, on 435 of vanilla's 436 (not `pm_dummy`)"),
    "production_method_groups": (("texture",),
                                 "vanilla convention: the building panel's icon for a mixed configuration, on 196 of "
                                 "vanilla's 197 (not `pmg_dummy`)"),
    "acceptance_statuses": (("background", "large_icon", "small_icon"), f"{_ALL} (5)"),
    "ai_strategic_region_stance_types": (("icon",), f"{_ALL} (4)"),
    "ai_strategies": (("icon",), f"{_ALL} (35)"),
    "alert_types": (("texture",), f"{_ALL} (69)"),
    "battle_conditions": (("icon",), f"{_ALL} (21)"),
    "character_roles": (("texture",), f"{_ALL} (10)"),
    "character_traits": (("texture",), f"{_ALL} (121)"),
    "cohesion_levels": (("background_texture",), f"{_ALL} (5)"),
    "combat_unit_experience_levels": (("icon",), f"{_ALL} (5)"),
    "combat_unit_groups": (("icon",), f"{_ALL} (4)"),
    "combat_unit_types": (("combat_unit_image/texture",), f"{_ALL} (19)"),
    "commander_orders": (("texture",), f"{_ALL} (12)"),
    "commander_ranks": (("texture",), f"{_ALL} (6)"),
    "company_charter_types": (("icon",), f"{_ALL} (5)"),
    "company_types": (("icon", "background"), f"{_ALL} (221)"),
    "decrees": (("texture",), f"{_ALL} (11)"),
    "diplomatic_plays": (("texture",), f"{_ALL} (53)"),
    "goods": (("texture",), f"{_ALL} (53)"),
    "harvest_condition_types": (("icon",), f"{_ALL} (22)"),
    "ideologies": (("icon",), f"{_ALL} (172)"),
    "institutions": (("icon", "background_texture"), f"{_ALL} (7)"),
    "interest_group_traits": (("icon",), f"{_ALL} (99)"),
    "interest_groups": (("texture",), f"{_ALL} (8)"),
    "interest_tier_types": (("icon", "small_icon"), f"{_ALL} (6)"),
    "laws": (("icon",), f"{_ALL} (138)"),
    "liberty_desire_levels": (("background_texture",), f"{_ALL} (3)"),
    "messages": (("texture",), f"{_ALL} (475)"),
    "military_formation_flags": (("icon",), f"{_ALL} (30)"),
    "mobilization_option_groups": (("icon",), f"{_ALL} (6)"),
    "mobilization_options": (("texture",), f"{_ALL} (18)"),
    "naval_battle_conditions": (("icon",), f"{_ALL} (7)"),
    "naval_mission_types": (("icon", "map_texture"), f"{_ALL} (9)"),
    "objectives": (("icon", "enabled_background"), f"{_ALL} (5)"),
    "parties": (("icon",), f"{_ALL} (12)"),
    "political_lobbies": (("texture",), f"{_ALL} (4)"),
    "political_movement_categories": (("icon",), f"{_ALL} (5)"),
    "pop_types": (("texture",), f"{_ALL} (15)"),
    "power_bloc_identities": (("icon", "background"), f"{_ALL} (6)"),
    "power_bloc_map_textures": (("texture",), f"{_ALL} (18)"),
    "power_bloc_principles": (("icon", "background"), f"{_ALL} (69)"),
    "prestige_goods": (("texture",), f"{_ALL} (72)"),
    "religions": (("icon",), f"{_ALL} (17)"),
    "ship_groups": (("icon",), f"{_ALL} (4)"),
    "ship_modification_slots": (("icon",), f"{_ALL} (7)"),
    "ship_modifications": (("icon",), f"{_ALL} (271)"),
    "ship_types": (("icon", "profile_texture"), f"{_ALL} (22)"),
    "ship_veterancy_levels": (("icon",), f"{_ALL} (5)"),
    "state_traits": (("icon",), f"{_ALL} (239)"),
    "technology/technologies": (("texture",), f"{_ALL} (179)"),
    "treaty_articles": (("icon",), f"{_ALL} (34)"),
    "war_goal_types": (("icon",), f"{_ALL} (39)"),
}
VANILLA_SNAPSHOT_DIR = "vanilla_parsed"
WARN_KINDS = ("dlc_only",)
SKIP_KINDS = ("templated", "other_extension")

# Strings, comments, operators (`?=`, `<=`, ... before `=`), braces, then
# bare words, which stop at an operator character.
_TOKEN_RE = re.compile(r'"[^"\n]*"?|#[^\n]*|\?=|[!<>=]=|[{}=<>!]|[^\s{}="#?<>!]+')
_OPS = frozenset({"=", "?=", "==", "!=", "<", ">", "<=", ">="})
_TAGGED_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$"
)
_ALIAS_RE = re.compile(r"[A-Za-z0-9_]+")
_DLC_PATH_RE = re.compile(r"dlc/([^/]+)/(gfx/.+)", re.I)


# --- data ------------------------------------------------------------------

@dataclass
class Flag:
    file: str
    line: int
    key: str | None
    value: str
    kind: str  # ERROR_KINDS or WARN_KINDS
    # The real path (case_mismatch), the DLC folders (dlc_only), `untracked`
    # (missing), or the corrected path (backslash, whitespace).
    detail: str = ""
    exemption: dict | None = None
    fixed_status: str = ""  # backslash / whitespace: how the corrected path resolves


@dataclass
class Skipped:
    file: str
    line: int
    key: str | None
    value: str
    kind: str  # SKIP_KINDS


@dataclass
class StaleTag:
    file: str
    line: int


@dataclass
class Definition:
    """One top-level `name = { }` in a `DECLARED_FIELDS` folder. `fields`:
    the `/`-joined key path of every non-empty value and every block in it."""
    folder: str
    name: str  # without its directive
    directive: str | None  # `INJECT`, `REPLACE`, ..., or None
    file: str
    line: int
    fields: frozenset[str]


@dataclass
class AssetIndex:
    """What a path can resolve to. `vanilla` maps each vanilla path (on-disk
    casing) to its origins: `base`, or the DLC folders that hold it.
    `aliases` does the same for media alias names."""
    vanilla: dict[str, frozenset[str]]
    aliases: dict[str, frozenset[str]]
    mod_files: set[str]
    mod_aliases: set[str] = field(default_factory=set)
    source: str = "given"  # "install", "catalog" or "given"
    mod_root: str | None = None  # to tell an untracked file from a missing one
    _folded: dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        for p in sorted(self.vanilla):
            self._folded.setdefault(p.lower(), p)
        # The mod's own file wins the folded slot, as it shadows vanilla's.
        for p in sorted(self.mod_files):
            self._folded[p.lower()] = p

    def resolve_path(self, path: str) -> tuple[str, str]:
        """(status, detail): `mod`, `vanilla`, `dlc_only`, `case_mismatch` or
        `missing`."""
        m = _DLC_PATH_RE.fullmatch(path)
        if m:
            return self._resolve_dlc_path(m.group(1), m.group(2))
        if path in self.mod_files:
            return "mod", ""
        origins = self.vanilla.get(path)
        if origins:
            if BASE_ORIGIN in origins:
                return "vanilla", ""
            return "dlc_only", ", ".join(sorted(origins))
        real = self._folded.get(path.lower())
        if real is not None:
            return "case_mismatch", real
        if self.mod_root and os.path.isfile(os.path.join(self.mod_root, path)):
            return "missing", "untracked"
        return "missing", ""

    def resolve_coa(self, name: str) -> tuple[str, str]:
        """A bare coat-of-arms file name: the first of `COA_DIRS` that holds
        it. Unresolved, it reports as the first directory's path."""
        found = [self.resolve_path(d + name) for d in COA_DIRS]
        for status in ("mod", "vanilla", "dlc_only", "case_mismatch"):
            for got in found:
                if got[0] == status:
                    return got
        return "missing", ""

    def _resolve_dlc_path(self, folder: str, rest: str) -> tuple[str, str]:
        """`dlc/<folder>/gfx/...`: the file must be in that DLC's folder."""
        if folder in self.vanilla.get(rest, ()):
            return "dlc_only", folder
        low_folder, low_rest = folder.lower(), rest.lower()
        for p, origins in self.vanilla.items():
            if p.lower() == low_rest:
                for o in origins:
                    if o.lower() == low_folder:
                        return "case_mismatch", f"dlc/{o}/{p}"
        return "missing", ""

    def resolve_alias(self, name: str) -> tuple[str, str]:
        """(status, detail): `alias`, `dlc_only` or `unknown_media_alias`."""
        if name in self.mod_aliases:
            return "alias", ""
        origins = self.aliases.get(name)
        if origins:
            if BASE_ORIGIN in origins:
                return "alias", ""
            return "dlc_only", ", ".join(sorted(origins))
        return "unknown_media_alias", ""


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)
    stale_tags: list[StaleTag] = field(default_factory=list)
    files_audited: int = 0
    references_checked: int = 0
    resolved: dict[str, int] = field(default_factory=dict)  # mod / vanilla / alias
    source: str = "given"
    catalog_stale: bool | None = None  # None: not compared (no install)
    entities_checked: int = 0  # mod entities a DECLARED_FIELDS check applied to
    # Fields left undeclared as vanilla's entity of the same name leaves them.
    vanilla_precedent: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def failing(self) -> int:
        """Flags `--strict` fails on: unexempted errors, plus stale tags."""
        return (sum(1 for f in self.flags if f.kind in ERROR_KINDS and not f.exemption)
                + len(self.stale_tags))


# --- scanning --------------------------------------------------------------

def _parse_tag(comment: str) -> dict | None:
    if "REVIEWED" not in comment:
        return None
    m = _TAGGED_REVIEWED_RE.search(comment)
    if m and CHECK in re.split(r"[\s,]+", m.group("checks").strip()):
        return {"date": m.group("date"), "rationale": m.group("rationale").strip()}
    return None


def iter_values(text: str):
    """Yield `(line, key, value)` for every scalar value in a Paradox script
    or GUI file, comments skipped, quotes removed. `key` is the left-hand side
    of `key = value`, or the enclosing block's name for a bare list item. A
    left-hand side is not a value."""
    starts = [0] + [m.end() for m in re.finditer(r"\n", text)]
    toks = [(m.group(), m.start()) for m in _TOKEN_RE.finditer(text) if m.group()[0] != "#"]
    stack: list[str | None] = []
    for i, (tok, pos) in enumerate(toks):
        after_eq = i >= 2 and toks[i - 1][0] in _OPS
        if tok == "{":
            stack.append(toks[i - 2][0] if after_eq else None)
        elif tok == "}":
            if stack:
                stack.pop()
        elif tok not in _OPS and not (i + 1 < len(toks) and toks[i + 1][0] in _OPS):
            key = toks[i - 2][0] if after_eq else (stack[-1] if stack else None)
            value = tok[1:-1] if len(tok) >= 2 and tok[0] == tok[-1] == '"' else tok.strip('"')
            yield bisect.bisect_right(starts, pos), key, value


def iter_tags(text: str):
    """Yield `(line, exemption)` for every `(texture_reference)` tag."""
    for lineno, raw in enumerate(text.split("\n"), 1):
        if "#" not in raw:
            continue
        m = _TOKEN_RE.finditer(raw)
        for t in m:
            if t.group()[0] == "#":
                tag = _parse_tag(t.group())
                if tag:
                    yield lineno, tag
                break


def _path_shaped(v: str) -> bool:
    """A `gfx/` (or `dlc/<folder>/gfx/`) root, or, for a value with no space
    in it, an image or video extension. Text with a space that isn't rooted
    is display text (`"see gfx/a.dds here"`)."""
    low = v.replace("\\", "/").lower()
    low = low[1:] if low.startswith("/") else low
    if low.startswith("gfx/") or _DLC_PATH_RE.fullmatch(low):
        return True
    return not any(c.isspace() for c in v) and low.endswith(_IMAGE_EXTENSIONS)


def classify(key: str | None, value: str, rel: str = "") -> tuple[str, str] | None:
    """(category, value to resolve), or None when the value isn't an asset
    reference. Category: `path`, `coa` (a bare coat-of-arms name), `alias`, a
    SKIP_KINDS kind, or an ERROR_KINDS kind decided without resolving
    (`unrooted`, `unknown_extension`, `backslash`, `whitespace`)."""
    stripped = value.strip()
    if not stripped or key in DISPLAY_KEYS:
        return None
    templated = "$" in stripped or "[" in stripped
    if key == "video" and not any(c in stripped for c in "/\\. "):
        if templated:
            return "templated", value
        return ("alias", stripped) if _ALIAS_RE.fullmatch(stripped) else None
    if not _path_shaped(stripped):
        return None
    if templated:
        return "templated", value
    if stripped != value:
        return "whitespace", stripped
    if "\\" in value:
        return "backslash", value.replace("\\", "/")
    norm = value[1:] if value.startswith("/") else value
    low = norm.lower()
    if not (low.startswith("gfx/") or _DLC_PATH_RE.fullmatch(low)):
        if "/" not in norm and rel.startswith(COA_CONTEXTS):
            return "coa", norm
        return "unrooted", norm
    if low.endswith(ASSET_EXTENSIONS):
        return "path", norm
    if low.endswith(NON_ASSET_EXTENSIONS):
        return "other_extension", value
    return "unknown_extension", norm


def scan_text(text: str, rel: str, index: AssetIndex, result: AuditResult,
              tags: dict[int, dict] | None = None, used: set[int] | None = None) -> None:
    """Append one file's path flags and skips to `result`. `tags` (the file's
    `iter_tags`) and `used` (the tagged lines a flag consumed) are shared with
    the declaration check; without them, stale tags are appended here."""
    own = tags is None
    if own:
        tags = dict(iter_tags(text))
        used = set()
    for line, key, value in iter_values(text):
        cat = classify(key, value, rel)
        if cat is None:
            continue
        category, norm = cat
        if category in SKIP_KINDS:
            result.skipped.append(Skipped(rel, line, key, value, category))
            continue
        result.references_checked += 1
        fixed = ""
        if category == "alias":
            status, detail = index.resolve_alias(norm)
        elif category == "coa":
            status, detail = index.resolve_coa(norm)
        elif category == "path":
            status, detail = index.resolve_path(norm)
        else:
            # Flagged as written; for a corrected path, say how it resolves.
            status, detail = category, ""
            if category in ("backslash", "whitespace"):
                detail = norm
                got = classify(key, norm, rel)
                if got and got[0] == "path":
                    fixed = index.resolve_path(got[1])[0]
        if status in ("mod", "vanilla", "alias"):
            result.resolved[status] = result.resolved.get(status, 0) + 1
            continue
        exemption = tags.get(line)
        if exemption:
            used.add(line)
        result.flags.append(Flag(rel, line, key, value, status, detail, exemption, fixed))
    if own:
        for line in sorted(set(tags) - used):
            result.stale_tags.append(StaleTag(rel, line))


# --- declarations ------------------------------------------------------------

def declared_folder(rel: str) -> str | None:
    """The `DECLARED_FIELDS` folder a `common/` file belongs to, or None."""
    if not rel.startswith("common/") or not rel.endswith(".txt"):
        return None
    sub = rel[len("common/"):]
    for folder in DECLARED_FIELDS:
        if sub.startswith(folder + "/"):
            return folder
    return None


def split_directive(name: str) -> tuple[str | None, str]:
    """(`INJECT`, `x`) for `INJECT:x`; (None, name) without a directive."""
    for prefix in directive_prefixes:
        if name.startswith(prefix):
            return prefix[:-1], name[len(prefix):]
    return None, name


def iter_entities(text: str):
    """Yield `(name, line, fields)` for each top-level `name = { ... }`:
    `fields` holds the `/`-joined key path of every non-empty value inside it
    (`icon`, `combat_unit_image/texture`), and of every block that holds one
    (`icon = { default = ... }`, not `icon = {}`). A key inside a bare `{ }`
    (a list item) isn't a field of the entity; a directive on a nested key
    (`REPLACE:icon`) is dropped from its name. `@constants` and top-level
    scalars are not entities."""
    starts = [0] + [m.end() for m in re.finditer(r"\n", text)]
    toks = [(m.group(), m.start()) for m in _TOKEN_RE.finditer(text) if m.group()[0] != "#"]
    n = len(toks)
    i = 0
    while i < n:
        tok, pos = toks[i]
        if not (i + 2 < n and toks[i + 1][0] in _OPS and toks[i + 2][0] == "{"
                and tok not in _OPS and tok not in "{}"):
            i += 1
            continue
        fields: set[str] = set()
        # Open blocks inside the entity: [key, its path (None under a bare
        # `{`), holds something non-empty]. A bare `{` has key None.
        frames: list[list] = []
        j = i + 3
        while j < n:
            t = toks[j][0]
            if t == "{":
                frames.append([None, None, False])
            elif t == "}":
                if not frames:
                    j += 1
                    break  # the entity's own closing brace
                _key, full, nonempty = frames.pop()
                if nonempty:
                    if full:
                        fields.add(full)
                    if frames:
                        frames[-1][2] = True
            elif t not in _OPS and j + 2 < n and toks[j + 1][0] in _OPS:
                key = split_directive(t)[1]
                bare = any(f[0] is None for f in frames)
                full = None if bare else "/".join([f[0] for f in frames] + [key])
                val = toks[j + 2][0]
                if val == "{":
                    frames.append([key, full, False])
                elif val.strip('"').strip():
                    if full:
                        fields.add(full)
                    if frames:
                        frames[-1][2] = True
                j += 3
                continue
            elif t not in _OPS and frames:
                frames[-1][2] = True  # a list item
            j += 1
        if not tok.startswith("@"):
            yield tok.strip('"'), bisect.bisect_right(starts, pos), frozenset(fields)
        i = j


def collect_definitions(text: str, rel: str, folder: str) -> list[Definition]:
    out = []
    for raw, line, fields in iter_entities(text):
        directive, name = split_directive(raw)
        out.append(Definition(folder, name, directive, rel, line, fields))
    return out


def _json_values(node):
    """The values of a `vanilla_parsed` key: `["=", v]`, or a list of those
    for a repeated key."""
    if isinstance(node, list) and node and isinstance(node[0], str) and node[0] in _OPS:
        return [node[1]] if len(node) > 1 else []
    if isinstance(node, list):
        return [v for item in node for v in _json_values(item)]
    return [node]


def _json_nonempty(v) -> bool:
    """A non-empty string, or a block or list holding one."""
    if isinstance(v, str):
        return bool(v.strip('"').strip())
    if isinstance(v, dict):
        return any(_json_nonempty(x) for val in v.values() for x in _json_values(val))
    if isinstance(v, list):
        return any(_json_nonempty(x) for x in _json_values(v))
    return v is not None


def json_declares(body, field_path: str) -> bool:
    """Whether a `vanilla_parsed` entity body has a non-empty value (or a
    block holding one) at `field_path`, as `iter_entities` counts it."""
    head, _, rest = field_path.partition("/")
    if not isinstance(body, dict) or head not in body:
        return False
    for v in _json_values(body[head]):
        if rest:
            if json_declares(v, rest):
                return True
        elif _json_nonempty(v):
            return True
    return False


@dataclass
class VanillaSnapshot:
    """What the declaration check knows of vanilla, for each `DECLARED_FIELDS`
    folder `vanilla_parsed/` holds: `names`, its entities; `gaps`, {field:
    the entities that don't declare it}. 23 of the 55 folders aren't in the
    snapshot (`uncovered`)."""
    names: dict[str, frozenset[str]] = field(default_factory=dict)
    gaps: dict[str, dict[str, frozenset[str]]] = field(default_factory=dict)

    def covers(self, folder: str) -> bool:
        return folder in self.names

    def uncovered(self) -> list[str]:
        return sorted(set(DECLARED_FIELDS) - set(self.names))


def load_vanilla_snapshot(mod_path: str) -> VanillaSnapshot:
    """The `DECLARED_FIELDS` folders the committed `vanilla_parsed/` snapshot
    holds. A folder it doesn't hold gets no entry: by the registry's premise,
    every vanilla entity there declares its fields, and an `*_OR_CREATE`
    there counts as creating its entity. Empty without a snapshot."""
    snap = VanillaSnapshot()
    root = os.path.join(mod_path, VANILLA_SNAPSHOT_DIR)
    try:
        with open(os.path.join(root, "manifest.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError):
        return snap
    files = {info.get("dir", "").removeprefix("game/common/"): info.get("file")
             for info in manifest.get("entity_types", {}).values()}
    for folder, (fields, _why) in DECLARED_FIELDS.items():
        rel = files.get(folder)
        if not rel:
            continue
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        snap.names[folder] = frozenset(data)
        snap.gaps[folder] = {
            f: frozenset(name for name, node in data.items()
                         if not any(json_declares(v, f) for v in _json_values(node)))
            for f in fields}
    return snap


_INJECTS = frozenset({"INJECT", "TRY_INJECT"})


def load_order(d: Definition) -> tuple:
    """Where a definition falls in the engine's load order: a type's files are
    one list in ASCII order of file name, whatever their subfolder, and a
    file is read top to bottom."""
    return (d.file.rsplit("/", 1)[-1], d.file, d.line)


def _fields(*groups) -> frozenset[str]:
    return frozenset().union(*(d.fields for g in groups for d in g))


def _final_definition(ds: list[Definition], vanilla: VanillaSnapshot,
                      folder: str, name: str) -> tuple[Definition, frozenset[str]] | None:
    """(the definition a flag goes on, the fields the loaded entity has), or
    None when the entity isn't the mod's to check. #1185's probes, on one key:

      * A plain `REPLACE:` applies after every INJECT and TRY_INJECT,
        whichever file sorts first: the last one's own fields are the entry,
        the INJECTs are lost. It wins over every rule below.
      * A `TRY_REPLACE:` applies in load order, so an INJECT in a later file
        lands on it. Whether one that sorts after an INJECT wipes it is
        unprobed: only the INJECTs after the last TRY_REPLACE count, which
        errs toward flagging (a tag clears it).
      * A `REPLACE_OR_CREATE:` / `INJECT_OR_CREATE:` applies up front, after
        the plain definitions and before every INJECT, even from a later file:
        the INJECTs land on it. A REPLACE_OR_CREATE replaces a plain
        definition; an INJECT_OR_CREATE merges into it, or, with none in the
        mod, creates the entity when vanilla has none of that name (or the
        snapshot doesn't hold the folder).
      * Otherwise a plain definition takes every INJECT, and an INJECT alone
        is into vanilla's entity, or into none (the engine's
        `inject_to_missing`)."""
    order = sorted(ds, key=load_order)
    by = {k: [d for d in order if d.directive == k]
          for k in (None, "REPLACE", "TRY_REPLACE", "REPLACE_OR_CREATE", "INJECT_OR_CREATE")}
    injects = [d for d in order if d.directive in _INJECTS]
    if by["REPLACE"]:
        last = by["REPLACE"][-1]
        return last, last.fields
    if by["TRY_REPLACE"]:
        last = by["TRY_REPLACE"][-1]
        later = [d for d in injects if load_order(d) > load_order(last)]
        return last, _fields([last], later)
    if by["REPLACE_OR_CREATE"]:
        last = by["REPLACE_OR_CREATE"][-1]
        return last, _fields([last], by["INJECT_OR_CREATE"], injects)
    if by[None]:
        return by[None][0], _fields(order)
    creates = by["INJECT_OR_CREATE"]
    if creates and not (vanilla.covers(folder) and name in vanilla.names[folder]):
        return creates[0], _fields(order)
    return None


def check_declarations(defs: list[Definition], vanilla: VanillaSnapshot,
                       tags: dict[str, dict[int, dict]], used: dict[str, set[int]],
                       result: AuditResult) -> None:
    """Append an `undeclared` flag for each mod entity that lacks a field its
    type needs (`_final_definition` says which definitions count)."""
    by_entity: dict[tuple[str, str], list[Definition]] = {}
    for d in defs:
        by_entity.setdefault((d.folder, d.name), []).append(d)
    for (folder, name), ds in sorted(by_entity.items()):
        final = _final_definition(ds, vanilla, folder, name)
        if final is None:
            continue
        owner, have = final
        result.entities_checked += 1
        fields, why = DECLARED_FIELDS[folder]
        for f in fields:
            if f in have:
                continue
            if name in vanilla.gaps.get(folder, {}).get(f, ()):
                result.vanilla_precedent.append((folder, name, f))
                continue
            exemption = tags.get(owner.file, {}).get(owner.line)
            if exemption:
                used.setdefault(owner.file, set()).add(owner.line)
            raw = f"{owner.directive}:{name}" if owner.directive else name
            result.flags.append(Flag(owner.file, owner.line, f, raw, "undeclared", why, exemption))


def iter_scan_files(mod_path: str):
    """Yield (abs path, rel path) for every scanned file, sorted."""
    for sub, ext in SCAN:
        root_dir = os.path.join(mod_path, sub)
        if not os.path.isdir(root_dir):
            continue
        for root, dirs, files in os.walk(root_dir):
            dirs.sort()
            for fname in sorted(files):
                if fname.endswith(ext):
                    abs_p = os.path.join(root, fname)
                    yield abs_p, os.path.relpath(abs_p, mod_path).replace("\\", "/")


# --- the resolution set ----------------------------------------------------

def mod_gfx_files(mod_path: str) -> set[str]:
    """The mod's tracked `gfx/` files. Read from git's index, which lists every
    tracked texture even where `gfx/` isn't on disk (CI, sparse worktrees).
    Outside a git checkout, the files on disk."""
    try:
        out = subprocess.run(["git", "-C", mod_path, "ls-files", "-z", "--", "gfx/"],
                             capture_output=True, timeout=60, check=True).stdout
        return {p for p in out.decode("utf-8", "replace").split("\0") if p}
    except (OSError, subprocess.SubprocessError):
        pass
    files: set[str] = set()
    gfx = os.path.join(mod_path, "gfx")
    for root, _dirs, names in os.walk(gfx):
        for n in names:
            files.add(os.path.relpath(os.path.join(root, n), mod_path).replace("\\", "/"))
    return files


def _alias_names(text: str) -> set[str]:
    """Top-level keys of a media alias file."""
    names: set[str] = set()
    depth = 0
    prev: list[str] = []
    for m in _TOKEN_RE.finditer(text):
        tok = m.group()
        if tok[0] == "#":
            continue
        if tok == "{":
            if depth == 0 and len(prev) >= 2 and prev[-1] in _OPS:
                names.add(prev[-2])
            depth += 1
        elif tok == "}":
            depth = max(0, depth - 1)
        prev = (prev + [tok])[-2:]
    return names


def mod_media_aliases(mod_path: str, mod_files: set[str]) -> set[str]:
    """Alias names the mod's own tracked `gfx/media_aliases/*.txt` define,
    read from disk or, where `gfx/` isn't checked out, from git's index."""
    names: set[str] = set()
    for rel in sorted(mod_files):
        if not (rel.startswith(MEDIA_ALIAS_DIR + "/") and rel.endswith(".txt")):
            continue
        text = _read(os.path.join(mod_path, rel))
        if text is None:
            try:
                text = subprocess.run(["git", "-C", mod_path, "show", f":{rel}"],
                                      capture_output=True, timeout=60, check=True
                                      ).stdout.decode("utf-8-sig", "replace")
            except (OSError, subprocess.SubprocessError):
                continue
        names |= _alias_names(text)
    return names


def install_root() -> str | None:
    """`<base_game_path>` when it holds the game's `gfx/`, else None (no
    install configured, as in CI and cloud sessions)."""
    try:
        import path_constants
        base = path_constants.base_game_path
    except (ImportError, RuntimeError, AttributeError):
        return None
    if base and os.path.isdir(os.path.join(base, "game", "gfx")):
        return base
    return None


def _walk(root: str, rel: str, out: list[str]) -> None:
    """Every file under `root`, as `rel/...`. `os.scandir` with the cached
    d_type is several times faster than `os.walk` on a `/mnt/c` mount."""
    try:
        it = os.scandir(root)
    except OSError:
        return
    with it:
        for e in it:
            sub = f"{rel}/{e.name}"
            if e.is_dir(follow_symlinks=False):
                _walk(e.path, sub, out)
            else:
                out.append(sub)


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def scan_install(base: str) -> tuple[dict[str, frozenset[str]], dict[str, frozenset[str]]]:
    """(paths, aliases) from a game install: each `ASSET_EXTENSIONS` file under
    the vanilla mounts and each DLC's `gfx/`, and each media alias name, with
    its origins (`base`, or DLC folder names)."""
    paths: dict[str, set[str]] = {}
    aliases: dict[str, set[str]] = {}
    mounts = [(os.path.join(base, r, "gfx"), BASE_ORIGIN) for r in VANILLA_ROOTS]
    dlc_dir = os.path.join(base, "game", "dlc")
    if os.path.isdir(dlc_dir):
        for name in sorted(os.listdir(dlc_dir)):
            if os.path.isdir(os.path.join(dlc_dir, name, "gfx")):
                mounts.append((os.path.join(dlc_dir, name, "gfx"), name))
    for root, origin in mounts:
        files: list[str] = []
        _walk(root, "gfx", files)
        for rel in files:
            if rel.lower().endswith(ASSET_EXTENSIONS):
                paths.setdefault(rel, set()).add(origin)
            if rel.startswith(MEDIA_ALIAS_DIR + "/") and rel.endswith(".txt"):
                text = _read(os.path.join(root, rel[len("gfx/"):]))
                for n in _alias_names(text or ""):
                    aliases.setdefault(n, set()).add(origin)
    return ({p: frozenset(o) for p, o in paths.items()},
            {a: frozenset(o) for a, o in aliases.items()})


# One listing per install state, for the server's lifetime: a reload would
# otherwise walk ~22,000 files on `/mnt/c` each time (~3 s). Keyed on the
# game version, the DLC folders and the checksum manifest, which a patch or a
# DLC install changes. `--bootstrap` always lists afresh.
_INSTALL_CACHE: dict[tuple, tuple[dict, dict]] = {}


def _install_key(base: str) -> tuple:
    dlc_dir = os.path.join(base, "game", "dlc")
    try:
        dlcs = tuple(sorted(os.listdir(dlc_dir)))
    except OSError:
        dlcs = ()
    try:
        st = os.stat(os.path.join(base, "game", "checksum_manifest.txt"))
        manifest = (st.st_mtime_ns, st.st_size)
    except OSError:
        manifest = None
    return (os.path.abspath(base), _game_version(base), dlcs, manifest)


def scan_install_cached(base: str) -> tuple[dict[str, frozenset[str]], dict[str, frozenset[str]]]:
    """`scan_install`, listed once per install state (see `_INSTALL_CACHE`).
    Callers must not mutate the result."""
    key = _install_key(base)
    if key not in _INSTALL_CACHE:
        _INSTALL_CACHE.clear()
        _INSTALL_CACHE[key] = scan_install(base)
    return _INSTALL_CACHE[key]


def _game_version(base: str) -> str | None:
    try:
        with open(os.path.join(base, "launcher", "launcher-settings.json"), encoding="utf-8-sig") as fh:
            v = json.load(fh).get("rawVersion")
    except (OSError, ValueError, AttributeError):
        return None
    return v if isinstance(v, str) else None


def _catalog_line(name: str, origins: frozenset[str]) -> str:
    if origins == {BASE_ORIGIN}:
        return name
    return f"{name}\t{','.join(sorted(origins))}"


def catalog_lines(paths, aliases) -> list[str]:
    """The catalog's entries: paths, then `media_alias:` names, each sorted;
    a second, tab-separated column lists the origins when they aren't just
    `base`."""
    return ([_catalog_line(p, paths[p]) for p in sorted(paths)]
            + [_catalog_line(ALIAS_PREFIX + a, aliases[a]) for a in sorted(aliases)])


def bootstrap_catalog(base: str, mod_path: str) -> dict:
    """List the install and write `docs/engine/vanilla_asset_paths.txt`.
    Re-run on a vanilla bump."""
    paths, aliases = scan_install(base)
    version = _game_version(base) or "unknown"
    out_path = os.path.join(mod_path, CATALOG_REL)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(
            "# AUTO-GENERATED vanilla asset path catalog for texture_reference_audit.py.\n"
            f"# Game version {version}. Regenerate on a vanilla bump:\n"
            "#   python3 texture_reference_audit.py --bootstrap\n"
            "# Every file under game/gfx, jomini/gfx, clausewitz/gfx and game/dlc/*/gfx\n"
            f"# with one of the extensions {' '.join(ASSET_EXTENSIONS)}, as the engine\n"
            "# mounts it (gfx/...), then every media alias name (media_alias:<name>).\n"
            "# A second, tab-separated column lists the origins when the entry isn't\n"
            "# only in the base game: DLC folder names, plus `base` when both.\n"
        )
        for line in catalog_lines(paths, aliases):
            fh.write(line + "\n")
    return {"paths": len(paths), "aliases": len(aliases), "version": version,
            "path": out_path, "bytes": os.path.getsize(out_path)}


def catalog_version(mod_path: str) -> str | None:
    """The game version in the committed catalog's header."""
    with open(os.path.join(mod_path, CATALOG_REL), encoding="utf-8") as fh:
        for raw in fh:
            if not raw.startswith("#"):
                break
            m = re.match(r"# Game version (\S+?)\.?\s", raw)
            if m:
                return m.group(1)
    return None


def load_catalog(mod_path: str) -> tuple[dict[str, frozenset[str]], dict[str, frozenset[str]]]:
    """(paths, aliases) from the committed catalog. Raises FileNotFoundError
    when it is absent, since without it every vanilla path would flag."""
    path = os.path.join(mod_path, CATALOG_REL)
    paths: dict[str, frozenset[str]] = {}
    aliases: dict[str, frozenset[str]] = {}
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.rstrip("\n")
            if not raw or raw.startswith("#"):
                continue
            name, _, col = raw.partition("\t")
            origins = frozenset(col.split(",")) if col else frozenset({BASE_ORIGIN})
            if name.startswith(ALIAS_PREFIX):
                aliases[name[len(ALIAS_PREFIX):]] = origins
            else:
                paths[name] = origins
    return paths, aliases


def build_index(mod_path: str, source: str = "auto", base: str | None = None,
                mod_files: set[str] | None = None) -> tuple[AssetIndex, bool | None]:
    """(index, catalog_stale). `source`: `install` lists the game at `base`
    (default: `install_root()`), `catalog` reads the committed catalog, and
    `auto` takes the install when there is one. `catalog_stale` is None unless
    the install was listed, then whether the catalog differs from it."""
    if mod_files is None:
        mod_files = mod_gfx_files(mod_path)
    if source in ("auto", "install") and base is None:
        base = install_root()
    if source == "install" and base is None:
        raise FileNotFoundError("no game install found (base_game_path/game/gfx)")
    stale: bool | None = None
    if source != "catalog" and base is not None:
        paths, aliases = scan_install_cached(base)
        used = "install"
        try:
            stale = load_catalog(mod_path) != (paths, aliases)
        except FileNotFoundError:
            stale = True
    else:
        paths, aliases = load_catalog(mod_path)
        used = "catalog"
    index = AssetIndex(paths, aliases, set(mod_files),
                       mod_media_aliases(mod_path, mod_files), source=used, mod_root=mod_path)
    return index, stale


# --- audit -----------------------------------------------------------------

def audit(mod_path: str | None = None, index: AssetIndex | None = None,
          source: str = "auto", vanilla: VanillaSnapshot | None = None) -> AuditResult:
    """`vanilla`: what the declaration check knows of vanilla
    (`load_vanilla_snapshot`), read from `mod_path` when None."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    stale = None
    if index is None:
        index, stale = build_index(mod_path, source)
    if vanilla is None:
        vanilla = load_vanilla_snapshot(mod_path)
    result = AuditResult(source=index.source, catalog_stale=stale)
    tags: dict[str, dict[int, dict]] = {}
    used: dict[str, set[int]] = {}
    defs: list[Definition] = []
    for abs_p, rel in iter_scan_files(mod_path):
        text = _read(abs_p)
        if text is None:
            continue
        result.files_audited += 1
        tags[rel] = dict(iter_tags(text))
        used[rel] = set()
        scan_text(text, rel, index, result, tags[rel], used[rel])
        folder = declared_folder(rel)
        if folder:
            defs += collect_definitions(text, rel, folder)
    check_declarations(defs, vanilla, tags, used, result)
    for rel in sorted(tags):
        for line in sorted(set(tags[rel]) - used[rel]):
            result.stale_tags.append(StaleTag(rel, line))
    result.flags.sort(key=lambda f: (f.file, f.line, f.value))
    result.skipped.sort(key=lambda s: (s.file, s.line, s.value))
    result.stale_tags.sort(key=lambda t: (t.file, t.line))
    return result


def describe(f: Flag) -> str:
    if f.kind == "undeclared":
        return (f"`{f.value}` declares no `{f.key}` ({f.detail}): add it, or opt out with a "
                f"`({CHECK})` tag on its opening line if it is never shown")
    ref = f"`{f.key} = {f.value}`" if f.key else f"`{f.value}`"
    if f.kind == "missing":
        if f.detail == "untracked":
            return f"{ref}: on disk but untracked: `git add` it"
        return f"{ref}: no such file in the mod or vanilla"
    if f.kind == "case_mismatch":
        return f"{ref}: only `{f.detail}` exists (differs in case)"
    if f.kind == "unknown_media_alias":
        return f"{ref}: no media alias of that name"
    if f.kind == "unrooted":
        return f"{ref}: not a path from `gfx/`; the engine reads it from the game's root"
    if f.kind == "unknown_extension":
        return f"{ref}: not an asset extension the audit knows (a typo?)"
    if f.kind in ("backslash", "whitespace"):
        what = "`\\` separators" if f.kind == "backslash" else "whitespace around the path"
        tail = {"": "", "mod": ", which resolves", "vanilla": ", which resolves",
                "dlc_only": ", which only a DLC has", "case_mismatch": ", which differs in case from the file",
                }.get(f.fixed_status, ", which doesn't resolve either")
        return f"{ref}: {what}; write `{f.detail}`{tail}"
    return f"{ref}: only in DLC {f.detail}"


def flag_dict(f: Flag) -> dict:
    return {"file": f.file, "line": f.line, "key": f.key, "value": f.value,
            "kind": f.kind, "detail": f.detail, "fixed_status": f.fixed_status,
            "description": describe(f), "reviewed": f.exemption}


def render_report(result: AuditResult) -> str:
    errors = [f for f in result.flags if f.kind in ERROR_KINDS and not f.exemption]
    warns = [f for f in result.flags if f.kind in WARN_KINDS and not f.exemption]
    exemp = [f for f in result.flags if f.exemption]
    out = [
        "# Texture reference audit report",
        "",
        "Auto-generated by `texture_reference_audit.py` on every `POST /reload` of",
        "the mod state server. Do not hand-edit.",
        "",
        "Flagged in `common/`, `events/` and `gui/`, for any value that starts with",
        "`gfx/` or ends in an image or video extension, and any `video = name`:",
        "",
        "- `missing`: no file in the mod's tracked `gfx/` or vanilla's (`game/`,",
        "  `jomini/`, `clausewitz/` and each DLC's `gfx/`);",
        "- `case_mismatch`: a file only in another casing;",
        "- `unknown_media_alias`: a `video = name` that names no media alias;",
        "- `unrooted`, `unknown_extension`, `backslash`, `whitespace`: a path that",
        "  doesn't start at `gfx/`, has an unknown extension, uses `\\`, or has spaces",
        "  around it inside its quotes;",
        "- `undeclared`: a mod entity, as its definitions load, that declares no art",
        "  in a field its type needs (see *Declarations checked*).",
        "",
        "The engine logs a miss only when it first renders the asset. Vanilla comes",
        "from the install when there is one, else from",
        "`docs/engine/vanilla_asset_paths.txt`.",
        "",
        "Fix: point the field at an existing file (list the vanilla folder for the",
        "closest by name and meaning), write the path from `gfx/` with `/`, fix the",
        "casing, `git add` a file that is on disk but untracked, or add the art.",
        "For `undeclared`, add the field (a `REPLACE:` restates vanilla's).",
        "",
        "Suppress a deliberate case on the path's line, or for `undeclared` on the",
        "entity's opening `<name> = {` line:",
        "`# REVIEWED YYYY-MM-DD (texture_reference): why`",
        "",
        "## Unreviewed flags",
        "",
    ]
    if not errors:
        out += ["_None._", ""]
    else:
        by_file: dict[str, list[Flag]] = {}
        for f in errors:
            by_file.setdefault(f.file, []).append(f)
        for fname in sorted(by_file):
            out += [f"### `{fname}`", ""]
            out += [f"- line {f.line} ({f.kind}): {describe(f)}" for f in by_file[fname]]
            out.append("")

    out += ["## DLC-only references (warning)", "",
            "Players without the DLC get the missing-texture placeholder. Fine in an",
            "event or option the DLC gates; tag it once checked. Doesn't fail `--strict`.",
            ""]
    if not warns:
        out += ["_None._", ""]
    else:
        out += [f"- `{f.file}:{f.line}` — {describe(f)}" for f in warns]
        out.append("")

    if result.stale_tags:
        out += ["## Stale tags", "", "Tags that suppress nothing; remove them.", ""]
        out += [f"- `{t.file}:{t.line}` ({CHECK})" for t in result.stale_tags]
        out.append("")

    out += ["## Reviewed exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        # No line number on a reviewed entry: an edit above it would otherwise
        # churn the report.
        out += [f"- `{f.file}` — {describe(f)} — **{f.exemption['date']}**: {f.exemption['rationale']}"
                for f in exemp]
        out.append("")

    out += ["## Declarations checked", "",
            "Each mod entity in these `common/` folders must declare the field. A",
            "plain `REPLACE:` counts alone (every `INJECT:` applies before it and is lost),",
            "a `TRY_REPLACE:` with the `INJECT:`s that sort after it, an `*_OR_CREATE:` or",
            "a plain definition with them all; an entity the mod only `INJECT:`s into is",
            "vanilla's. Only `buildings` and",
            "`static_modifiers` have a log line behind them; the rest are vanilla",
            "convention, and an entity that is never shown opts out with a tag. Why each",
            "is checked, and the types and fields left out, are in",
            "`texture_reference_audit.py`'s docstring.",
            ""]
    out += [f"- `{folder}`: {', '.join(f'`{x}`' for x in fields)}"
            for folder, (fields, _why) in sorted(DECLARED_FIELDS.items())]
    out.append("")
    if result.vanilla_precedent:
        out += ["Undeclared as vanilla's entity of the same name is, so not flagged:", ""]
        out += [f"- `{folder}` `{name}`: `{f}`" for folder, name, f in sorted(result.vanilla_precedent)]
        out.append("")

    out += ["## Skipped", "",
            "Not resolved: `templated` (built from `$PARAM$` or a `[...]` expression) and",
            "`other_extension` (a `gfx/` path to a mesh, entity, animation or other file",
            "script names by entity, which the catalog doesn't list).",
            ""]
    if not result.skipped:
        out += ["_None._", ""]
    else:
        for kind in SKIP_KINDS:
            rows = [s for s in result.skipped if s.kind == kind]
            if rows:
                out += [f"### {kind} ({len(rows)})", ""]
                out += [f"- `{s.file}` — `{s.value}`" for s in rows]
                out.append("")

    # Flag counts only: the file and reference counts stay on the result (and
    # in the regenerate() summary) but move with unrelated mod content.
    out += ["## Coverage", "",
            f"- total flags: {len(result.flags)}",
            f"- unreviewed errors: {len(errors)}",
            f"- unreviewed DLC-only: {len(warns)}",
            f"- exempted: {len(exemp)}",
            f"- stale tags: {len(result.stale_tags)}"]
    out += [f"- skipped {k}: {sum(1 for s in result.skipped if s.kind == k)}" for k in SKIP_KINDS]
    out.append("")
    return "\n".join(out) + "\n"


def summary(result: AuditResult) -> dict:
    return {
        # Unexempted errors, plus tags that suppress nothing.
        "unreviewed": result.failing,
        "total_flags": len(result.flags),
        "exempted": sum(1 for f in result.flags if f.exemption),
        "dlc_only": sum(1 for f in result.flags if f.kind == "dlc_only" and not f.exemption),
        "stale_tags": len(result.stale_tags),
        **{f"skipped_{k}": sum(1 for s in result.skipped if s.kind == k) for k in SKIP_KINDS},
        "files_audited": result.files_audited,
        "references_checked": result.references_checked,
        "undeclared": sum(1 for f in result.flags if f.kind == "undeclared" and not f.exemption),
        "entities_checked": result.entities_checked,
        "vanilla_precedent": len(result.vanilla_precedent),
        "resolved": dict(sorted(result.resolved.items())),
        "vanilla_source": result.source,
        "catalog_stale": result.catalog_stale,
    }


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report. `mod_state`
    is unused (a file scan), kept for the post-load contract."""
    from path_constants import mod_path
    result = audit(mod_path=mod_path)
    out_path = os.path.join(mod_path, REPORT_REL)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    return {**summary(result), "path": out_path}


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on an unexempted error or a stale tag")
    ap.add_argument("--bootstrap", action="store_true",
                    help=f"list the game install and rewrite {CATALOG_REL}")
    ap.add_argument("--source", choices=("auto", "install", "catalog"), default="auto",
                    help="where vanilla's files come from (default: the install if present)")
    args = ap.parse_args(argv)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path

    if args.bootstrap:
        base = install_root()
        if base is None:
            print("no game install found (base_game_path/game/gfx); nothing to bootstrap from",
                  file=sys.stderr)
            return 2
        print(bootstrap_catalog(base, mod_path))
        return 0
    try:
        result = audit(mod_path=mod_path, source=args.source)
    except FileNotFoundError as e:
        print(f"texture_reference_audit: {e}", file=sys.stderr)
        return 2
    print(render_report(result))
    note = f"(vanilla from the {result.source}"
    if result.catalog_stale:
        note += f"; {CATALOG_REL} differs from the install: run --bootstrap"
    print(note + ")", file=sys.stderr)
    if args.strict:
        return 1 if result.failing else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
