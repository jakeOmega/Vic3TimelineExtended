"""Vanilla textures drawn by the mod's own GUI widgets (#1484): `GET /gui/placeholder-textures`.

`/placeholder-icons` classifies entity icons only. A mod panel that draws a
vanilla icon as a stand-in (style guide rule 10) shows up nowhere unless
someone listed it by hand in a `docs/systems/*_gui_icons.md` table. This
lists every literal texture path in the mod's GUI files, says where each
resolves (the mod's own art, vanilla's, or nowhere), and which icons doc, if
any, accounts for it. What is left is the work list: vanilla icons in the
mod's own widgets that no doc names as kept or as a placeholder.

**Mod-owned.** A mod GUI file at a path vanilla also has replaces vanilla's
panel, and draws vanilla art by design; only a file with no vanilla
counterpart is the mod's own widget. A file name cannot tell the two apart
(28 of the mod's 89 files sit at a vanilla path, and most of the rest carry
no `te_` prefix), so the vanilla file names are committed as
`docs/engine/vanilla_gui_files.txt`, written by `python3
texture_reference_audit.py --bootstrap` on the machine with the game, beside
the asset catalog that run already writes. Re-run it after a vanilla patch.

**What counts.** A literal `"gfx/….dds"` (or `.png`, `.tga`) outside a
comment; a texture picked by a data function (`"[GetX]"`) names no path and
is not seen. Three kinds of vanilla texture are told apart:

- `icon`: under `gfx/interface/icons/`. These are the ones a doc should
  account for, and the only ones `unlisted` counts.
- `ui_mark`: vanilla's general marks, which are never placeholders (trend
  arrows, the transparent texture, check marks and crosses, the warning and
  information marks).
- `chrome`: anything else (backgrounds, frames, progress bars, buttons).
"""
from __future__ import annotations

import os
import re
from typing import Callable, Iterable, Optional

GUI_FILES_REL = os.path.join("docs", "engine", "vanilla_gui_files.txt")
ICON_DOCS_GLOB_DIR = os.path.join("docs", "systems")
ICON_DOC_SUFFIX = "_gui_icons.md"
ICON_PREFIX = "gfx/interface/icons/"
# The mounts a mod's `gui/` folder overlays, as texture_reference_audit.VANILLA_ROOTS.
VANILLA_ROOTS = ("game", "jomini", "clausewitz")
LINES_SHOWN = 12

_TEXTURE = re.compile(r'"(gfx/[^"\[\]\s]+?\.(?:dds|png|tga))"', re.IGNORECASE)
_KEY = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*$")
_UI_MARK = re.compile(
    r"gfx/interface/icons/generic_icons/(?:unused/)?(?:"
    r"transparent|trend_\w+|up_up|down_down|arrow_\w+|upgrade_arrow|"
    r"checkmark|green_checkmark|checkbox_\w+|red_cross|map_list_\w+|warning|information"
    r")\.dds")
_NOT_PLACEHOLDER = re.compile(r"not a placeholder|\bkept\b|\bfinal\b", re.IGNORECASE)
_PLACEHOLDER = re.compile(r"placeholder|stand-in|stands in", re.IGNORECASE)


# ---------------------------------------------------------------------------
# The committed list of vanilla GUI files
# ---------------------------------------------------------------------------

def scan_vanilla_gui(base: str) -> list[str]:
    """Every file under the install's `gui/` mounts, as the engine mounts it
    (`gui/…`), sorted. A mod file at one of these paths replaces it."""
    found: set[str] = set()
    for root in VANILLA_ROOTS:
        top = os.path.join(base, root)
        for where, _dirs, names in os.walk(os.path.join(top, "gui")):
            for name in names:
                found.add(os.path.relpath(os.path.join(where, name), top).replace(os.sep, "/"))
    return sorted(found)


def bootstrap(base: str, mod_path: str, version: Optional[str] = None) -> dict:
    """List the install's GUI files and write `docs/engine/vanilla_gui_files.txt`."""
    files = scan_vanilla_gui(base)
    out_path = os.path.join(mod_path, GUI_FILES_REL)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(
            "# AUTO-GENERATED list of vanilla GUI files for gui_placeholder_textures.py.\n"
            f"# Game version {version or 'unknown'}. Regenerate on a vanilla bump:\n"
            "#   python3 texture_reference_audit.py --bootstrap\n"
            "# Every file under game/gui, jomini/gui and clausewitz/gui, as the engine\n"
            "# mounts it (gui/...). A mod GUI file at one of these paths replaces a vanilla\n"
            "# panel; any other is the mod's own widget.\n"
        )
        fh.write("".join(f + "\n" for f in files))
    return {"gui_files": len(files), "path": out_path}


def load_gui_files(mod_path: str) -> frozenset[str]:
    """The committed list. Raises FileNotFoundError when it is absent: without
    it every override would read as the mod's own widget."""
    with open(os.path.join(mod_path, GUI_FILES_REL), encoding="utf-8") as fh:
        return frozenset(line.strip() for line in fh if line.strip() and not line.startswith("#"))


def list_is_stale(base: Optional[str], mod_path: str) -> Optional[bool]:
    """Whether the committed list differs from the install's GUI files; None
    with no install to compare with."""
    if not base or not os.path.isdir(os.path.join(base, "game", "gui")):
        return None
    try:
        return load_gui_files(mod_path) != frozenset(scan_vanilla_gui(base))
    except FileNotFoundError:
        return True


# ---------------------------------------------------------------------------
# The mod's GUI files and the icons docs
# ---------------------------------------------------------------------------

def mod_gui_files(mod_path: str) -> list[str]:
    """The mod's `.gui` files, as `gui/…`, sorted."""
    found = []
    top = os.path.join(mod_path, "gui")
    for where, _dirs, names in os.walk(top):
        for name in names:
            if name.endswith(".gui"):
                found.append(os.path.relpath(os.path.join(where, name), mod_path).replace(os.sep, "/"))
    return sorted(found)


def texture_refs(text: str) -> list[tuple[int, str, str]]:
    """(line, key, path) for each literal texture path outside a comment.
    `key` is the property it is given to (`texture`, `progresstexture`, …),
    or "" when the path is not a property's value."""
    refs = []
    for number, line in enumerate(text.split("\n"), start=1):
        code = _strip_comment(line)
        for found in _TEXTURE.finditer(code):
            key = _KEY.search(code[:found.start()])
            refs.append((number, key.group(1) if key else "", found.group(1)))
    return refs


def _strip_comment(line: str) -> str:
    in_string = False
    for i, char in enumerate(line):
        if char == '"':
            in_string = not in_string
        elif char == "#" and not in_string:
            return line[:i]
    return line


def icon_doc_index(mod_path: str) -> dict[str, dict]:
    """{texture path: {"doc", "line", "status"}} from the `*_gui_icons.md`
    docs: the first line of a doc that names the path in backticks. `status`
    is `kept` when that line says the texture is kept, final or not a
    placeholder, `placeholder` when it calls it one, else `listed`."""
    index: dict[str, dict] = {}
    folder = os.path.join(mod_path, ICON_DOCS_GLOB_DIR)
    try:
        names = sorted(n for n in os.listdir(folder) if n.endswith(ICON_DOC_SUFFIX))
    except OSError:
        return index
    for name in names:
        rel = os.path.join(ICON_DOCS_GLOB_DIR, name).replace(os.sep, "/")
        try:
            with open(os.path.join(folder, name), encoding="utf-8-sig") as fh:
                lines = fh.read().split("\n")
        except OSError:
            continue
        for number, line in enumerate(lines, start=1):
            for path in re.findall(r"`(gfx/[^`\s]+?\.(?:dds|png|tga))`", line):
                if path in index:
                    continue
                status = ("kept" if _NOT_PLACEHOLDER.search(line) else
                          "placeholder" if _PLACEHOLDER.search(line) else "listed")
                index[path] = {"doc": rel, "line": number, "status": status}
    return index


def kind_of(path: str) -> str:
    """`ui_mark`, `icon` or `chrome` for a texture path (see the module text)."""
    if _UI_MARK.fullmatch(path):
        return "ui_mark"
    return "icon" if path.startswith(ICON_PREFIX) else "chrome"


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------

def report(mod_path: str, vanilla_gui: Iterable[str], resolve: Callable[[str], str], *,
           include_overrides: bool = False, unlisted_only: bool = False,
           files: Optional[Iterable[str]] = None) -> dict:
    """The `/gui/placeholder-textures` body.

    `vanilla_gui` is the vanilla GUI file list; `resolve(path)` answers
    `mod`, `vanilla` or `missing` for a texture path. Each file's textures
    are grouped by path: `uses`, the first LINES_SHOWN `lines`, `resolves`,
    `kind`, and `listed_in` (the icons doc line that names it, or None).
    `unlisted` marks the work list: a vanilla `icon` in a mod-owned file that
    no doc names. Overrides of vanilla panels are left out unless
    `include_overrides`; `unlisted_only` keeps only the work list."""
    vanilla_gui = frozenset(vanilla_gui)
    docs = icon_doc_index(mod_path)
    out_files = []
    summary = {"mod_owned_files": 0, "override_files": 0, "vanilla_textures": 0, "vanilla_icons": 0,
               "missing": 0, "listed": 0, "unlisted": 0}
    for rel in (sorted(files) if files is not None else mod_gui_files(mod_path)):
        mod_owned = rel not in vanilla_gui
        summary["mod_owned_files" if mod_owned else "override_files"] += 1
        if not mod_owned and not include_overrides:
            continue
        try:
            with open(os.path.join(mod_path, rel), encoding="utf-8-sig", errors="replace") as fh:
                refs = texture_refs(fh.read())
        except OSError:
            continue
        grouped: dict[str, dict] = {}
        for line, key, path in refs:
            row = grouped.get(path)
            if row is None:
                where = resolve(path)
                kind = kind_of(path)
                listed = docs.get(path)
                row = grouped[path] = {
                    "path": path, "resolves": where, "kind": kind, "uses": 0, "lines": [], "keys": [],
                    "listed_in": listed,
                    "unlisted": mod_owned and where == "vanilla" and kind == "icon" and listed is None,
                }
            row["uses"] += 1
            if len(row["lines"]) < LINES_SHOWN:
                row["lines"].append(line)
            if key and key not in row["keys"]:
                row["keys"].append(key)
        rows = [r for r in grouped.values() if r["resolves"] != "mod"]
        if mod_owned:
            for r in rows:
                if r["resolves"] == "missing":
                    summary["missing"] += 1
                    continue
                summary["vanilla_textures"] += 1
                if r["kind"] == "icon":
                    summary["vanilla_icons"] += 1
                    summary["unlisted" if r["unlisted"] else "listed"] += 1
        if unlisted_only:
            rows = [r for r in rows if r["unlisted"]]
        if rows:
            rows.sort(key=lambda r: (not r["unlisted"], r["lines"][0]))
            out_files.append({"file": rel, "mod_owned": mod_owned, "textures": rows})
    return {"files": out_files, "summary": summary}


def render_text(body: dict) -> str:
    """The report as plain text, for `?format=text`."""
    s = body["summary"]
    out = [
        f"{s['mod_owned_files']} mod-owned GUI files ({s['override_files']} overrides of vanilla panels left out)",
        f"{s['vanilla_textures']} vanilla textures in them, {s['vanilla_icons']} of them icons: "
        f"{s['listed']} named in an icons doc, {s['unlisted']} not; {s['missing']} paths resolve nowhere",
        "",
    ]
    for entry in body["files"]:
        out.append(entry["file"] + ("" if entry["mod_owned"] else "  (override)"))
        for r in entry["textures"]:
            where = (f"{r['listed_in']['doc']}:{r['listed_in']['line']} ({r['listed_in']['status']})"
                     if r["listed_in"] else "UNLISTED" if r["unlisted"] else r["kind"])
            lines = ", ".join(str(n) for n in r["lines"]) + (" …" if r["uses"] > len(r["lines"]) else "")
            out.append(f"  {r['resolves']:8s} {r['path']}  x{r['uses']} (line {lines})  {where}")
        out.append("")
    return "\n".join(out)
