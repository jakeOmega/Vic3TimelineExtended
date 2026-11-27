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
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

# What a preview does not sync, though a .gui leans on it: the game reads the deployed versions until a deploy (and
# the script reload). Scripted GUIs and their triggers (is_shown, is_valid), script values, custom localization
# (GetCustom), localization, and the interface's textures (a new icon draws nothing).
SCRIPT_DIRS = ("common/scripted_guis/", "common/scripted_triggers/", "common/script_values/",
               "common/customizable_localization/", "localization/", "gfx/interface/")
VANILLA_GUI_DIRS = ("game/gui", "jomini/gui")      # under the install folder; the mod's own gui/ is read after them
POPUP_SHELL = "te_ui_popup"     # gui/te_widget_library.gui: full-screen, dimmed, gated on te_popup
POPUP_BODY_BLOCK = "popup_list"
HINT_MAX = 8

PREVIEW_FILE = "gui/te_qa_preview.gui"     # in the overlay: written at build (revision 0) so the game watches it
PREVIEW_WIDGET = "te_qa_preview"
CLEAR_WIDGET = "te_qa_preview_clear"       # created once after a shot, to clear the --var values
REV_PREFIX = "te_qa_rev_"
BACKDROP = (255, 0, 255)                   # the icon's `color = { 1 0 1 1 }`
DEFAULT_WIDTH = 520                        # a journal entry's widgets: te_tax_layout_widget.gui's roots are 520
PANEL_MARGIN = (43, 37)                    # Window_Background's inset (23, 17), and 20 units of padding
GUI_FAILURES = ("Unlocalized text", "FetchData failed", "pdx_data_factory", "pdx_gui_factory",
                "is not a valid widget/type/property")
# Logged once when the game parses a file that uses a type before the file that defines it (#1989): the container
# then stays empty, through later reloads of the using file alone, with nothing more logged.
_INVALID_TYPE = re.compile(r"'([A-Za-z_][A-Za-z0-9_]*)' is not a valid widget/type/property")
INVALID_TYPES_HINT = ("the game parsed a file that uses these types before the file that defines them, and the "
                      "container stays empty with nothing more logged: change the defining file and show, then change "
                      "the using file and show again, or start the session with --gui-from so the game parses the "
                      "branch's files at launch")
_KEY = re.compile(r"[A-Za-z0-9_]+")
_REV = re.compile(r"Unlocalized text '%s([0-9]{1,9})' at %s:" % (REV_PREFIX, re.escape(PREVIEW_FILE)))
_STAMP = re.compile(r"^\[\d{2}:\d{2}:\d{2}\]")

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


def vanilla_types(base_game: Path | None) -> dict[str, Any]:
    """The installed game's types (`VANILLA_GUI_DIRS` under `base_game`, when there), by name: about 8 seconds over
    the real install, so a session computes it once and hands it to `gui_index`."""
    import gui_tree     # a repo-root module: imported here, so that importing this module never needs the repo root

    trees: dict[str, Any] = {}
    for folder in VANILLA_GUI_DIRS:
        root = Path(base_game) / folder if base_game is not None else None
        if root is not None and root.is_dir():
            for path in sorted(root.rglob("*.gui")):
                trees["%s/%s" % (folder, path.relative_to(root).as_posix())] = gui_tree.parse_file(path)
    return gui_tree.type_index(trees)


def gui_index(repo: Path, base_game: Path | None, vanilla: dict[str, Any] | None = None) -> GuiIndex:
    """The types a preview can instance: the installed game's (`vanilla`, else `vanilla_types(base_game)`), then the
    repo's `gui/` over them, so that the mod's definition of a name wins as the engine's load order makes it; and the
    root widgets the repo's journal entries attach (`widget = { gui = "..." name = "..." }`)."""
    import gui_tree

    repo = Path(repo)
    if vanilla is None:
        vanilla = vanilla_types(base_game)
    mod_trees = {path.relative_to(repo).as_posix(): gui_tree.parse_file(path) for path in gui_tree.gui_files(repo)}
    mod = gui_tree.type_index(mod_trees)
    types = {**vanilla, **mod}
    mod_types = frozenset(mod)
    je_roots: dict[str, str] = {}
    for path in sorted((repo / "common" / "journal_entries").glob("*.txt")):
        for block in _JE_WIDGET.finditer(path.read_text(encoding="utf-8-sig", errors="replace")):
            gui, name = _JE_GUI.search(block[1]), _JE_NAME.search(block[1])
            if gui and name:
                je_roots[name[1]] = gui[1]
    roots: dict[str, Any] = {}
    for name, rel in je_roots.items():
        tree = mod_trees.get(rel)
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


def parse_context(context: str) -> str:
    """`player` (the default: `[GetPlayer]`, for the types that read a Country), `none`, or `je:<key>`
    (`[GetPlayerJournalEntry('<key>')]`); `bad_argument` otherwise."""
    if context in ("player", "none"):
        return context
    if isinstance(context, str) and context.startswith("je:") and _KEY.fullmatch(context[3:]):
        return context
    raise PreviewError("bad_argument", "a context is player, none or je:<journal entry key>, not %r" % (context,))


def parse_var(text: str) -> tuple[str, str]:
    """`KEY=VALUE`, both letters, digits and _ (they go into a binding's quotes): `bad_argument` otherwise."""
    key, sep, value = text.partition("=") if isinstance(text, str) else ("", "", "")
    if not (sep and _KEY.fullmatch(key) and _KEY.fullmatch(value)):
        raise PreviewError("bad_argument", "a variable is KEY=VALUE, each letters, digits and _, not %r" % (text,))
    return key, value


def _vars_state(variables: Mapping[str, str], action: str, indent: str) -> list[str]:
    if not variables:
        return []
    lines = [indent + "state = {", indent + "\tname = te_qa_vars", indent + "\ttrigger_on_create = yes"]
    for key, value in variables.items():
        call = "Set( '%s', '%s' )" % (key, value) if action == "Set" else "Clear( '%s' )" % key
        lines.append(indent + '\ton_start = "[GetVariableSystem.%s]"' % call)
    lines.append(indent + "}")
    return lines


def wrapper_text(type_name: str | None, context: str, width: int, revision: int,
                 variables: Mapping[str, str]) -> str:
    """The overlay's `PREVIEW_FILE` (no BOM: `overlay` adds it): a full-screen magenta backdrop on the top layer, a
    centred panel holding a header, the revision token (an unlocalized `text`, whose warning the game logs each time
    it parses the file: the proof of the reload) and the type; and, with `variables`, a state that sets them when the
    widget is created and a `CLEAR_WIDGET` that clears them when it is. The panel is a flowcontainer carrying the
    window background, not a `window`: live (2026-11-23) a window kept the size its resizeparent flowcontainer had
    before the type laid out, and the type spilled below it, while a flowcontainer's background grew round all of
    its content. PANEL_MARGIN covers the background's own inset (`Window_Background`: margin -23 -17) and pads. `type_name` None is the empty wrapper of
    revision 0, written at build. Arguments are trusted: the session checks them first (`check_type`,
    `parse_context`, `parse_var`)."""
    header = "%s - %s" % (type_name, context) if type_name else "game_qa GUI preview"
    out = ["### Generated by game_qa gui-show (the overlay's own file; rewritten for every preview). Revision %d."
           % revision, "", "widget = {", '\tname = "%s"' % PREVIEW_WIDGET, "\tsize = { 100% 100% }", "\tlayer = top"]
    out += _vars_state(variables, "Set", "\t")
    out += ["", "\ticon = {", "\t\tsize = { 100% 100% }", '\t\ttexture = "gfx/interface/backgrounds/white.dds"',
            "\t\tcolor = { 1 0 1 1 }", "\t}", "", "\tflowcontainer = {", "\t\tparentanchor = center",
            "\t\tdirection = vertical", "\t\tusing = Window_Background", "\t\tmargin = { %d %d }" % PANEL_MARGIN,
            "\t\tspacing = 10", "\t\tignoreinvisible = yes", "\t\tminimumsize = { %d -1 }" % width]
    if context == "player":
        out.append('\t\tdatacontext = "[GetPlayer]"')
    elif context.startswith("je:"):
        out.append("\t\tdatacontext = \"[GetPlayerJournalEntry('%s')]\"" % context[3:])
    out += ["",
            "\t\ttextbox = {", "\t\t\tsize = { %d 24 }" % width, '\t\t\traw_text = "%s"' % header,
            '\t\t\tdefault_format = "#header"', "\t\t\talign = left|nobaseline", "\t\t}",
            "\t\ttextbox = {", "\t\t\tsize = { %d 18 }" % width, '\t\t\ttext = "%s%d"' % (REV_PREFIX, revision),
            "\t\t\talign = left|nobaseline", "\t\t}"]
    if type_name and context.startswith("je:"):
        out += ["\t\ttextbox = {", '\t\t\tvisible = "[Not( JournalEntry.IsActive )]"',
                "\t\t\tsize = { %d 24 }" % width,
                '\t\t\traw_text = "%s is not active for the played country"' % context[3:],
                "\t\t\talign = left|nobaseline", "\t\t}",
                "\t\tflowcontainer = {", '\t\t\tvisible = "[JournalEntry.IsActive]"',
                "\t\t\tdirection = vertical", "\t\t\tignoreinvisible = yes",
                "\t\t\t%s = {}" % type_name, "\t\t}"]
    elif type_name:
        out.append("\t\t%s = {}" % type_name)
    out += ["\t}", "}"]
    if variables:
        out += ["", "widget = {", '\tname = "%s"' % CLEAR_WIDGET, "\tsize = { 0 0 }"]
        out += _vars_state(variables, "Clear", "\t")
        out.append("}")
    return "\n".join(out) + "\n"


def rev_in(line_text: str) -> int | None:
    """The revision the wrapper's token names in a log message (`Unlocalized text 'te_qa_rev_<n>' at
    gui/te_qa_preview.gui:<line>`), or None for any other line."""
    found = _REV.search(line_text)
    return int(found[1]) if found else None


def invalid_types(texts: Sequence[str]) -> dict[str, str]:
    """{type: the message} for each "'X' is not a valid widget/type/property" among log message `texts`, the first
    of each, its time stamp taken off."""
    found: dict[str, str] = {}
    for text in texts:
        text = _STAMP.sub("", text.rstrip("\r\n"), count=1)
        for match in _INVALID_TYPE.finditer(text):
            found.setdefault(match[1], text)
    return found


def gui_log(lines: Sequence[str], files: Sequence[str]) -> list[dict]:
    """The GUI lines among raw log `lines` (`[hh:mm:ss][file.cpp:n]: message`): those holding one of GUI_FAILURES
    or naming one of `files`, each once in first-seen order with its count (a failing binding logs every frame), the
    time stamp taken off. The wrapper's own token line is left out."""
    counts: dict[str, int] = {}
    for line in lines:
        text = _STAMP.sub("", line.rstrip("\r\n"), count=1)
        if rev_in(text) is not None:
            continue
        if any(mark in text for mark in GUI_FAILURES) or any(f in text for f in files):
            counts[text] = counts.get(text, 0) + 1
    return [{"text": text, "count": n} for text, n in counts.items()]
