"""`gui-show`'s pure parts: what a preview syncs, which types it takes, the wrapper it writes and the GUI lines it
reads back (spec docs/superpowers/specs/2026-11-23-gui-preview-design.md).

A preview shows one GUI type from the caller's working tree, alone, in the running game: the session copies the
`.gui` files the caller's branch changed into the overlay, rewrites the overlay's wrapper (a full-screen magenta
backdrop and a centred window that instances the type), waits for the game to log the wrapper's revision, and
recreates the widget with the console. Nothing here touches the game or the overlay; `overlay.py` writes and
`session.py` drives.

The files are the branch's, not "every file that differs from the deployed copy": a worktree branched from an
older `main` differs in every file `main` changed since, and syncing those would lay the branch's older copies over
the deployed build for the rest of the session (spec § 5.2, step 1).
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCRIPT_DIRS = ("common/scripted_guis/", "common/script_values/", "localization/")
VANILLA_GUI_DIRS = ("game/gui", "jomini/gui")      # under the install folder; the mod's own gui/ is read after them
POPUP_SHELL = "te_ui_popup"     # gui/te_widget_library.gui: full-screen, dimmed, gated on te_popup
POPUP_BODY_BLOCK = "popup_list"
HINT_MAX = 8

_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_JE_WIDGET = re.compile(r"\bwidget\s*=\s*\{([^{}]*)\}")
_JE_GUI = re.compile(r'\bgui\s*=\s*"([^"]+)"')
_JE_NAME = re.compile(r'\bname\s*=\s*"([^"]+)"')


class PreviewError(Exception):
    """A preview that cannot go ahead. `code` names why; `info` holds what goes with it (a `hint`, a `file`)."""

    def __init__(self, code: str, detail: str = "", **info: Any) -> None:
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code, self.detail, self.info = code, detail, info


@dataclass(frozen=True)
class BranchChanges:
    base: str           # the merge base with the upstream, which the changes are measured from
    gui: list[str]      # the `.gui` files under gui/ the branch changed, committed or not, that exist now
    script: list[str]   # the files under SCRIPT_DIRS it changed: a preview reads the deployed versions of these


def _git(repo: Path, *args: str) -> str:
    cmd = ["git", "-C", str(repo), *args]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise PreviewError("not_a_repo", "%s failed: %s" % (" ".join(cmd), e)) from e
    if done.returncode != 0:
        raise PreviewError("not_a_repo", "%s failed: %s" % (" ".join(cmd), done.stderr.strip()))
    return done.stdout


def branch_changes(repo: Path, upstream: str = "origin/main") -> BranchChanges:
    """The files the branch checked out in `repo` changed against its merge base with `upstream`: its commits, its
    uncommitted edits and its untracked files. A file deleted since is left out (there is nothing to sync).
    `PreviewError("not_a_repo")` when `repo` is not a checkout or has no `upstream`."""
    repo = Path(repo)
    base = _git(repo, "merge-base", "HEAD", upstream).strip()
    changed = set(_git(repo, "diff", "--name-only", base).splitlines())
    changed |= set(_git(repo, "ls-files", "--others", "--exclude-standard").splitlines())
    present = sorted(rel for rel in changed if rel and (repo / rel).is_file())
    gui = [rel for rel in present if rel.startswith("gui/") and rel.endswith(".gui")]
    script = [rel for rel in present if rel.startswith(SCRIPT_DIRS)]
    return BranchChanges(base, gui, script)


@dataclass
class GuiIndex:
    types: dict[str, Any]           # type name -> its gui_tree.Node: vanilla's, then the mod's over them
    je_roots: dict[str, str]        # a journal entry's root widget name -> the .gui file the entry names
    mod_types: frozenset[str] = frozenset()     # the names the mod's gui/ defines (a hint names only these)
    roots: dict[str, Any] = field(default_factory=dict)     # a root widget's name -> its node, in its file


def gui_index(repo: Path, base_game: Path | None) -> GuiIndex:
    """The types a preview can instance: the installed game's (`VANILLA_GUI_DIRS` under `base_game`, when there),
    then the repo's `gui/`, so that the mod's definition of a name wins as the engine's load order makes it; and the
    root widgets the repo's journal entries attach (`widget = { gui = "..." name = "..." }`)."""
    import gui_tree     # a repo-root module: imported here, so that importing this module never needs the repo root

    repo = Path(repo)
    trees: dict[str, Any] = {}
    for folder in VANILLA_GUI_DIRS:
        root = Path(base_game) / folder if base_game is not None else None
        if root is not None and root.is_dir():
            for path in sorted(root.rglob("*.gui")):
                trees["0 %s/%s" % (folder, path.relative_to(root).as_posix())] = gui_tree.parse_file(path)
    mod_trees = {"1 " + path.relative_to(repo).as_posix(): gui_tree.parse_file(path)
                 for path in gui_tree.gui_files(repo)}
    types = gui_tree.type_index({**trees, **mod_trees})
    mod_types = frozenset(gui_tree.type_index(mod_trees))
    je_roots: dict[str, str] = {}
    for path in sorted((repo / "common" / "journal_entries").glob("*.txt")):
        for block in _JE_WIDGET.finditer(path.read_text(encoding="utf-8-sig", errors="replace")):
            gui, name = _JE_GUI.search(block[1]), _JE_NAME.search(block[1])
            if gui and name:
                je_roots[name[1]] = gui[1]
    roots: dict[str, Any] = {}
    for name, rel in je_roots.items():
        tree = mod_trees.get("1 " + rel)
        for node in tree.children if tree is not None else ():
            prop = node.prop("name")
            if prop is not None and prop.value == name:
                roots[name] = node
    return GuiIndex(types, je_roots, mod_types, roots)


def _instances(node: Any, names: frozenset[str]) -> list[str]:
    """The types of `names` instanced under `node`, in source order, each once. An instance's written content counts
    (`te_je_country = { te_tax_status_sections = {} }` holds both); its type's definition is not walked."""
    found: list[str] = []
    for child in node.children:
        if child.kind in names and child.kind not in found:
            found.append(child.kind)
        if child.kind not in ("block", "blockoverride"):
            found.extend(k for k in _instances(child, names) if k not in found)
    return found


def check_type(name: str, idx: GuiIndex) -> None:
    """Raise PreviewError unless `name` is a type a preview can show on its own: `bad_argument` (not a name),
    `je_root` (a journal entry's root widget: it needs the entry, and its gates; `hint` the mod types it holds),
    `popup_shell` (a full-screen popup: `hint` the types of its body), `unknown_type`."""
    import gui_tree

    if not isinstance(name, str) or _NAME.fullmatch(name) is None:
        raise PreviewError("bad_argument", "a type is a name of letters, digits and _, not %r" % (name,))
    if name in idx.je_roots:
        node = idx.roots.get(name)
        hint = _instances(node, idx.mod_types)[:HINT_MAX] if node is not None else []
        raise PreviewError("je_root", "%s is a journal entry's root widget (%s), which needs the entry and its gates: "
                           "show the types inside it instead" % (name, idx.je_roots[name]), hint=hint)
    if POPUP_SHELL in gui_tree.base_chain(name, idx.types):
        hint: list[str] = []
        for child in idx.types[name].children:
            if child.kind == "blockoverride" and child.name == POPUP_BODY_BLOCK:
                hint = _instances(child, idx.mod_types)[:HINT_MAX]
        raise PreviewError("popup_shell", "%s is a full-screen popup (it derives from %s): show its body instead"
                           % (name, POPUP_SHELL), hint=hint)
    if name not in idx.types:
        raise PreviewError("unknown_type", "no .gui file of the mod or the installed game defines a type %s" % name)
