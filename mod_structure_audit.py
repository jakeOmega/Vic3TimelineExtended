"""Audit for structural issues in mod Paradox files.

Catches three classes of silent bug, all of which are invisible to the
Clausewitz engine's normal logging:

1. **Brace balance** — a `.txt` file under `common/` whose `{` / `}` counts
   don't balance. Unclosed blocks cause the engine to silently truncate the
   tail of the file, dropping the entries that come after the imbalance.

2. **Silent INJECT** — an `INJECT:<name> = { ... }` directive that targets
   an entity which is either:
   - **mod-only** (not vanilla-defined; the entity's only declaration is a
     bare `<name> = { ... }` somewhere in the mod), OR
   - **REPLACEd** by another file in the mod.
   In both cases, engine merge order causes the INJECT block to silently
   *not* merge into the final entity. Symptom: the modifiers/effects in the
   INJECT block never apply at runtime, even though the file parses cleanly.
   **Fix:** edit the entity's bare/REPLACE declaration directly instead of
   using INJECT.

3. **Top-level collision** — an entity name that has more than one bare
   `<name> = { ... }` declaration across the mod's `common/` files (no
   `REPLACE:` or `INJECT:` prefix on either). Per the engine's
   "Duplicated key X will not be created" rule, only one of the
   declarations survives — the others are silently dropped.

Suppression (INJECT only): inline `# REVIEWED YYYY-MM-DD: rationale` on the
`INJECT:<name>` line. Brace and collision flags don't accept REVIEWED — they
are unambiguously bugs in the source.
"""
import os
import re
from dataclasses import dataclass, field


@dataclass
class Flag:
    kind: str  # "brace" | "inject" | "collision"
    file: str
    line: int  # 0 if not applicable (whole-file flag)
    detail: str
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0


_INJECT_RE = re.compile(r"^\s*INJECT:([A-Za-z_][\w]*)\s*=\s*\{")
_REPLACE_RE = re.compile(r"^\s*REPLACE:([A-Za-z_][\w]*)\s*=\s*\{")
_BARE_DEF_RE = re.compile(r"^\s*([A-Za-z_][\w]*)\s*=\s*\{")

_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)

# `common/<subdir>/` namespaces in which Paradox merges multiple bare blocks
# of the same name across files instead of treating them as collisions:
#   - on_actions: every file's `on_X = { events = {...} }` blocks merge
#   - defines:    every file's `NPops = {...}` group merges keyed-by-key
#   - history:    every file's `GLOBAL = {...}` block merges
# Collision detection skips these subdirectories.
_MERGE_BY_DESIGN_DIRS: frozenset[str] = frozenset({
    "on_actions",
    "defines",
    "history",
})


def _split_comment(line: str) -> tuple[str, str | None]:
    """Split a line into (content_before_comment, comment_or_None).

    Paradox `.txt` files use `#` for line-end comments. We don't try to
    handle `#` inside quoted strings — Paradox text rarely has them, and the
    failure mode (mistaking `#` inside a string for a comment) only causes
    underestimation of brace counts, which would itself surface as a
    brace-balance flag.
    """
    idx = line.find("#")
    if idx < 0:
        return line, None
    return line[:idx], line[idx:]


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _scan_file(filepath: str) -> dict:
    """Single-pass scan of one .txt file.

    Returns a dict with:
        top_level_defs: [(name, line)]   bare `<name> = { ... }` at depth 0
        injects:        [(name, line, comment)]
        replaces:       [(name, line)]
        brace_balance:  int  (0 = balanced; positive = unclosed; negative = extra closing)
    """
    top_level_defs: list[tuple[str, int]] = []
    injects: list[tuple[str, int, str | None]] = []
    replaces: list[tuple[str, int]] = []
    depth = 0

    with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
        for line_num, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            content, comment = _split_comment(line)

            if depth == 0:
                m = _INJECT_RE.match(content)
                if m:
                    injects.append((m.group(1), line_num, comment))
                else:
                    m = _REPLACE_RE.match(content)
                    if m:
                        replaces.append((m.group(1), line_num))
                    else:
                        m = _BARE_DEF_RE.match(content)
                        if m:
                            top_level_defs.append((m.group(1), line_num))

            for ch in content:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1

    return {
        "top_level_defs": top_level_defs,
        "injects": injects,
        "replaces": replaces,
        "brace_balance": depth,
    }


def audit(mod_state, mod_path: str | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    flags: list[Flag] = []
    files_audited = 0

    # Cross-file aggregations. Top-level definitions are scoped per
    # `common/<subdirectory>/` since each subdirectory is its own entity-type
    # namespace -- a country tag like `BHA` in `country_definitions/` is a
    # different entity from `BHA` in `dynamic_country_names/`. Subdirectories
    # in MERGE_BY_DESIGN_DIRS (on_actions, defines, history) accept multiple
    # bare blocks of the same name from different files; the engine merges
    # them rather than treating them as collisions.
    #
    # Keys: `subdir/name`. Values: list of (relative_file, line).
    all_top_level: dict[str, list[tuple[str, int]]] = {}
    # INJECT and REPLACE are global (the engine resolves them across all
    # mod files regardless of subdirectory) so we keep one map per name.
    all_injects: dict[str, list[tuple[str, int, str | None]]] = {}
    all_replaces: dict[str, list[tuple[str, int]]] = {}
    # Bare-name-only map used to look up entity definitions when checking
    # silent-INJECT (where we only know the name, not the source subdir).
    bare_name_locations: dict[str, list[tuple[str, int]]] = {}

    common_root = os.path.join(mod_path, "common")
    if not os.path.isdir(common_root):
        return AuditResult(flags=flags, files_audited=0)

    for root, _dirs, files in os.walk(common_root):
        rel_subdir = os.path.relpath(root, common_root)
        for fname in sorted(files):
            if not fname.endswith(".txt"):
                continue
            abs_p = os.path.join(root, fname)
            rel_p = os.path.relpath(abs_p, mod_path)
            try:
                scan = _scan_file(abs_p)
            except OSError:
                continue
            files_audited += 1

            if scan["brace_balance"] != 0:
                bal = scan["brace_balance"]
                flavor = "unclosed" if bal > 0 else "extra closing"
                flags.append(Flag(
                    kind="brace",
                    file=rel_p,
                    line=0,
                    detail=f"Brace balance off by {bal:+d} ({flavor})",
                ))

            ns_key = rel_subdir.replace(os.sep, "/")
            for name, line in scan["top_level_defs"]:
                key = f"{ns_key}/{name}"
                all_top_level.setdefault(key, []).append((rel_p, line))
                bare_name_locations.setdefault(name, []).append((rel_p, line))
            for name, line, comment in scan["injects"]:
                all_injects.setdefault(name, []).append((rel_p, line, comment))
            for name, line in scan["replaces"]:
                all_replaces.setdefault(name, []).append((rel_p, line))

    # Vanilla name index (across all entity types parsed by ModState).
    vanilla_names: set[str] = set()
    base_parsers = getattr(mod_state, "base_parsers", {}) or {}
    for parser in base_parsers.values():
        try:
            vanilla_names.update(parser.data.keys())
        except (AttributeError, TypeError):
            continue

    # Silent INJECT failures
    for name, sites in all_injects.items():
        is_replaced = name in all_replaces
        is_mod_only = (name not in vanilla_names) and (name in bare_name_locations)
        if not (is_replaced or is_mod_only):
            continue
        for file, line, comment in sites:
            exemption = _parse_reviewed(comment)
            if is_replaced:
                rsite = all_replaces[name][0]
                detail = (
                    f"`INJECT:{name}` won't merge: REPLACEd by "
                    f"`{rsite[0]}:{rsite[1]}`. Edit the REPLACE block directly."
                )
            else:
                dsite = bare_name_locations[name][0]
                detail = (
                    f"`INJECT:{name}` won't merge: mod-only entity defined at "
                    f"`{dsite[0]}:{dsite[1]}`. Edit the definition directly."
                )
            flags.append(Flag(
                kind="inject",
                file=file,
                line=line,
                detail=detail,
                exemption=exemption,
            ))

    # Top-level collisions (same bare name defined multiple times within the
    # SAME `common/<subdir>/` namespace, in subdirs that don't merge by design).
    for ns_key, sites in all_top_level.items():
        if len(sites) <= 1:
            continue
        subdir = ns_key.rsplit("/", 1)[0]
        if subdir in _MERGE_BY_DESIGN_DIRS:
            continue
        name = ns_key.rsplit("/", 1)[1]
        first = sites[0]
        for site in sites[1:]:
            flags.append(Flag(
                kind="collision",
                file=site[0],
                line=site[1],
                detail=(
                    f"Duplicate top-level `{name} = {{ ... }}` in "
                    f"`{subdir}/` (also at `{first[0]}:{first[1]}`); engine "
                    f"drops all but one silently. Use `REPLACE:{name}` if "
                    f"intentional."
                ),
            ))

    return AuditResult(flags=flags, files_audited=files_audited)


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    by_kind: dict[str, list[Flag]] = {}
    for f in unrev:
        by_kind.setdefault(f.kind, []).append(f)

    out = [
        "# Mod structure audit report",
        "",
        "Auto-generated by `mod_structure_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "## What this catches",
        "",
        "**Brace balance**: `.txt` files under `common/` whose `{` / `}` counts",
        "don't balance. The engine silently truncates the tail of unbalanced",
        "files; nothing surfaces in `error.log`.",
        "",
        "**Silent INJECT**: an `INJECT:<name>` directive targeting an entity",
        "that is either mod-only (no vanilla version) or REPLACEd elsewhere",
        "in the mod. The engine's merge order causes the INJECT to silently",
        "*not* merge — symptom: the INJECT's modifiers don't apply at",
        "runtime even though the file parses cleanly. Fix: edit the entity's",
        "bare or REPLACE declaration directly.",
        "",
        "**Top-level collision**: an entity defined more than once at top",
        "level (no `REPLACE:` / `INJECT:` prefix) across the mod's `common/`",
        "files. The engine emits `Duplicated key X will not be created` and",
        "drops all but one. Fix: prefix one with `REPLACE:` if the override",
        "is intentional, or remove the duplicate.",
        "",
        "Suppression (INJECT only): inline `# REVIEWED YYYY-MM-DD: rationale`",
        "on the `INJECT:<name>` line. Brace and collision flags don't accept",
        "REVIEWED — they are unambiguously bugs in the source.",
        "",
        "## Unreviewed flags",
        "",
    ]
    if not unrev:
        out.append("_None._")
        out.append("")
    else:
        for kind, heading in (
            ("brace", "Brace balance"),
            ("collision", "Top-level collisions"),
            ("inject", "Silent INJECTs"),
        ):
            items = by_kind.get(kind, [])
            if not items:
                continue
            out.append(f"### {heading} ({len(items)})")
            out.append("")
            for f in items:
                if f.line:
                    out.append(f"- `{f.file}:{f.line}` — {f.detail}")
                else:
                    out.append(f"- `{f.file}` — {f.detail}")
            out.append("")

    out.append("## Reviewed exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        for f in exemp:
            out.append(
                f"- `{f.file}:{f.line}` — {f.detail} — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    out.append(f"- files audited: {result.files_audited}")
    by_kind_all: dict[str, int] = {}
    for f in result.flags:
        by_kind_all[f.kind] = by_kind_all.get(f.kind, 0) + 1
    if by_kind_all:
        out.append("- flags by kind:")
        for kind in sorted(by_kind_all):
            out.append(f"  - {kind}: {by_kind_all[kind]}")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")
    out.append("")

    return "\n".join(out) + "\n"


def regenerate(mod_state) -> dict:
    """POST_LOAD_GENERATORS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(mod_path, "docs", "engine", "mod_structure_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    unrev = sum(1 for f in result.flags if not f.exemption)
    exemp = sum(1 for f in result.flags if f.exemption)
    by_kind: dict[str, int] = {}
    for f in result.flags:
        by_kind[f.kind] = by_kind.get(f.kind, 0) + 1
    return {
        "files_audited": result.files_audited,
        "by_kind": by_kind,
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": exemp,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from mod_state import ModState
    from path_constants import base_game_paths, mod_paths, mod_path
    ms = ModState(base_game_paths, mod_paths)
    result = audit(ms, mod_path=mod_path)
    print(render_report(result))
