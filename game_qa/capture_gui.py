"""The GUI files a capture session's overlay carries, and the scratch widget that opens a view (#2056).

A screenshot meant for the player guide or the Workshop page can't show the harness. Two things of its own draw over
the game in a session:

* **The console.** It covers the left fifth of the window, where every side panel opens. The see-through copy of
  2026-11-24 (`see_through_console`, which `scripts/analysis/qa_see_through_console.py` writes into a variant) hides
  everything in it but the edit line, drawn at half strength, and that line was still a faint band across every
  side-panel shot (#2041). The capture copy (`capture_console`) draws the edit line at alpha 0 as well, so it draws
  nothing at all. The harness never reads the console from the screen: what a verb typed is read back from
  `console_history.txt` and the log, so the console still works, as long as a widget at alpha 0 still takes the
  click and the keys (alpha changes what is drawn, not what is hit: `docs/guides/gui_modding_guide.md`, gotcha 29's
  last line).
* **Debug mode's own widgets** (the session needs `-debug_mode`): the error counter, the frame counter and the Slow
  Ticks button at the lower right, all under one root in vanilla's `gui/error_deer.gui`, `visible = "[InDebugMode]"`.
  `gated_error_deer` adds `Not( GetVariableSystem.Exists( 'te_qa_capture' ) )` to that line, so they hide only while
  a capture has set CAPTURE_KEY (the `view` verb's `set:te_qa_capture=yes`); the frame counter stays for the
  performance sessions that read it.

* **Debug mode's lines elsewhere** (`DEBUG_GATED_FILES`): a journal entry's page prints "Debug: Journal entry key:
  ... and ID is ..." (seen live 2026-11-26 on the Map Room's page), an event window its id, a tooltip its keys.
  `gate_debug_lines` puts the same condition into every `visible` line of those files that names `InDebugMode`, so
  they hide too while the key is set. Each is copied from the deployed mod where the mod ships the file (the overlay
  loads after it, so its copy must be the mod's, the build under test), else from the game.

Both are copies of the installed game's files with whole-line edits, made at `start --capture` and never kept in the
repo. A patch that moves one of the edited lines stops the start with the line that could not be found
(`CaptureGuiError("capture_gui_changed")`), rather than load a console that might not take keys.

The view's scratch widget: the mod's windows, tabs and collapsible sections are client-side keys
(`GetVariableSystem.Set('com_open_window', 'te_systems_window')`, `te_systems_window_tab`, the `te_*` section
toggles), and vanilla's panels open through `InformationPanelBar.OpenPanelTab('budget', 'default')` and its kin. A
widget whose `state` has `trigger_on_create = yes` runs its `on_start` lines when the console creates it (live
2026-11-23: the keys outlive the widget, "A popup in its real host, without a click" in
`docs/guides/python_tools.md`). `view_wrapper_text` writes one such widget per step into the overlay's preview file
(the file `gui-show` rewrites; its revision token proves the reload), and the session creates them in order, a
moment apart, then clears them. Opening a view this way needs no aim, so it survives a layout change, another window
size and another UI scale, which clicks at fractions of the window do not.

An action is one of a short list (`parse_action`), each with a fixed form, so a manifest can't run an arbitrary
binding (`ExecuteConsoleCommand`, a save) through it:

    set:KEY=VALUE        [GetVariableSystem.Set('KEY', 'VALUE')]
    clear:KEY            [GetVariableSystem.Clear('KEY')]
    panel:NAME           [InformationPanelBar.OpenPanel('NAME')]
    panel:NAME:TAB       [InformationPanelBar.OpenPanelTab('NAME', 'TAB')]
    market:TAB           [InformationPanelBar.OpenMarketPanelTab(AccessPlayer.AccessFirstMarket.Self, 'TAB')]
    construction         [InformationPanelBar.OpenConstructionPanel( GetPlayer.Self )]
    construction:TAB     [InformationPanelBar.OpenConstructionPanelTab( GetPlayer.Self, 'TAB' )]
    state:capital        [InformationPanelBar.OpenStatePanel( AccessPlayer.AccessCapital )]
    zoom:capital         [AccessPlayer.AccessCapital.ZoomToCapital]: the camera to the capital
    sgui:te_…_sgui       [GetScriptedGui('NAME').Execute( GuiScope.SetRoot( GetPlayer.MakeScope ).End )]: one of the
                         mod's scripted GUIs run as its button runs it, in the played country's scope. It changes the
                         game (a Map Room pick sets the country's selector), which is why only a copy is ever loaded
    close-panel          [InformationPanelBar.ClosePanel]

Each binding is one vanilla's own GUI uses (`OpenConstructionPanel( GetPlayer.Self )` in the outliner,
`OpenStatePanel( State.AccessSelf )`, `Country.AccessCapital.ZoomToCapital` on a country's capital link), with the
played country's capital as the State: a map object the view can name without a click. The capital is reached by
`AccessPlayer`, not `GetPlayer`: live 2026-11-26, `GetPlayer.AccessCapital` was refused "Invalid promote 'GetPlayer'
... requires non const promote" (`AccessPlayer.AccessFirstMarket` is the market tab's for the same reason).
A journal entry's page has no view action: `GetPlayerJournalEntry('KEY').AccessSelf` in a binding was refused
the same way, and the same entry given as the step widget's datacontext opened nothing and logged nothing (live
2026-11-27), so a recipe clicks the entry's outliner row or its button.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from game_qa import gui_preview

BOM = b"\xef\xbb\xbf"
CAPTURE_KEY = "te_qa_capture"               # set while a shot is taken: error_deer.gui's widgets hide
CONSOLE_FILE = "gui/console.gui"            # in the overlay, over the game's own
CONSOLE_SOURCE = "game/gui/console.gui"     # under the game's install folder
ERROR_DEER_FILE = "gui/error_deer.gui"
ERROR_DEER_SOURCE = "game/gui/error_deer.gui"
VIEW_WIDGET = "te_qa_view_%d"               # one top-level widget per step, created in order
VIEW_TOKEN_WIDGET = "te_qa_view_token"      # holds the revision token; never created (the token is read at parse)
MAX_STEPS = 6
MAX_ACTIONS = 24                            # in one step
_WORD = re.compile(r"[A-Za-z0-9_]{1,64}")
_TAB = re.compile(r"[A-Za-z0-9_|]{1,64}")   # a cycle of tabs is `a|b|c`

# (what to find, what to put, how many times it must be there): whole-line edits of vanilla 1.15.2's console.gui.
SEE_THROUGH_EDITS: tuple[tuple[str, str, int], ...] = (
    # The background template: no click blocker, nothing drawn.
    ("template ConsoleBackground\n{\n\tusing = clickthrough_blocker\n",
     "template ConsoleBackground\n{\n\t### TE QA: see-through console (no click blocker, nothing drawn)\n\talpha = 0\n", 1),
    ("\tusing = bg_tiling_pattern\n\t\talpha = 0.065", "\tusing = bg_tiling_pattern\n\t\talpha = 0", 1),
    ("template console_frame\n{\n", "template console_frame\n{\n\talpha = 0\n", 1),
    # The window lets clicks through.
    ('\tname = "console_window"\n\talwaystransparent = no\n\tscissor = no\n\tlayer = confirmation\n'
     "\tusing = clickthrough_blocker\n",
     '\tname = "console_window"\n\talwaystransparent = yes\n\tscissor = no\n\tlayer = confirmation\n', 1),
    # The column keeps its layout though its children are hidden, so the edit line stays where it was.
    ("\tflowcontainer = {\n\t\tdirection = vertical\n\t\tspacing = 4\n\t\tbackground = {\n\t\t\tusing = ConsoleBackground",
     "\tflowcontainer = {\n\t\tdirection = vertical\n\t\tspacing = 4\n\t\tignoreinvisible = no\n\t\tbackground = {\n"
     "\t\t\tusing = ConsoleBackground", 1),
    # The output and the debug toolbars are hidden.
    ('\t\t\tname = "console_output_scrollarea"\n', '\t\t\tname = "console_output_scrollarea"\n\t\t\tvisible = no\n', 1),
    ('\t\t\tname = "toolbars_window"\n', '\t\t\tname = "toolbars_window"\n\t\t\tvisible = no\n', 1),
)
EDIT_LINE = "\t\t\tbackground = {\n\t\t\t\tusing = ConsoleEditbg\n\t\t\t\tmargin = { 4 0 }\n"
# The see-through console's edit line, faint: the harness clicks it, and a person watching can see it.
FAINT_EDIT_LINE = (EDIT_LINE, EDIT_LINE + "\t\t\t\talpha = 0.5\n", 1)
# The capture console's: nothing drawn, the box (its background) and what is typed in it (the editbox's own alpha,
# which its text and caret take too). It is still where it was and still takes the click.
HIDDEN_EDIT_LINE = (EDIT_LINE, "\t\t\t### TE QA capture: the edit line draws nothing\n\t\t\talpha = 0\n" + EDIT_LINE
                    + "\t\t\t\talpha = 0\n", 1)
ERROR_DEER_EDITS: tuple[tuple[str, str, int], ...] = (
    ('\tvisible = "[InDebugMode]"\n\tlayer = layer_error_deer\n',
     "\t### TE QA capture: hidden while a capture runs\n"
     "\tvisible = \"[And( InDebugMode, Not( GetVariableSystem.Exists( '%s' ) ) )]\"\n"
     "\tlayer = layer_error_deer\n" % CAPTURE_KEY, 1),
)


# Every GUI file of vanilla 1.15.2 or the mod with a widget shown only in debug mode, error_deer.gui (above) aside.
DEBUG_GATED_FILES = ("gui/journal_entry.gui", "gui/eventwindow.gui", "gui/tooltip.gui", "gui/custom_tooltip.gui",
                     "gui/states_panel.gui", "gui/market_panel.gui", "gui/power_bloc_panel.gui",
                     "gui/right_click_menu.gui", "gui/military_formation_panel.gui", "gui/ship_panel.gui",
                     "gui/location_finder.gui", "gui/front_panel.gui", "gui/ship_designer_popup.gui")
GATED_DEBUG = "And( InDebugMode, Not( GetVariableSystem.Exists( '%s' ) ) )" % CAPTURE_KEY
_DEBUG_VISIBLE = re.compile(r'^(?P<lead>\s*visible\s*=\s*)"?\[(?P<expr>[^"\]]*\bInDebugMode\b[^"]*?)\]"?(?P<tail>\s*(?:#.*)?)$')


class CaptureGuiError(Exception):
    """A capture file that can't be made, or a view that can't be written. `code` names why."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def apply_edits(source: bytes, edits: Sequence[tuple[str, str, int]], what: str) -> bytes:
    """`source` with `edits` made, its BOM (or none) and line endings kept. `capture_gui_changed` when one of the
    lines is not there the number of times it should be: a patch moved it."""
    had_bom = source.startswith(BOM)
    try:
        text = source[len(BOM):].decode("utf-8") if had_bom else source.decode("utf-8")
    except UnicodeDecodeError as e:
        raise CaptureGuiError("capture_gui_changed", "the game's %s is not UTF-8: %s" % (what, e)) from e
    crlf = "\r\n" in text
    text = text.replace("\r\n", "\n")
    for old, new, count in edits:
        if text.count(old) != count:
            raise CaptureGuiError("capture_gui_changed", "expected %d of %r in the game's %s, found %d: a patch moved "
                                  "it, so check the edit against the new file" % (count, old, what, text.count(old)))
        text = text.replace(old, new)
    if crlf:
        text = text.replace("\n", "\r\n")
    return (BOM if had_bom else b"") + text.encode("utf-8")


def see_through_console(source: bytes) -> bytes:
    """The game's `console.gui`, see-through, with the edit line faint: the GUI-evaluation variant's."""
    return apply_edits(source, SEE_THROUGH_EDITS + (FAINT_EDIT_LINE,), "console.gui")


def capture_console(source: bytes) -> bytes:
    """The game's `console.gui`, see-through, with the edit line drawing nothing: a capture's."""
    return apply_edits(source, SEE_THROUGH_EDITS + (HIDDEN_EDIT_LINE,), "console.gui")


def gated_error_deer(source: bytes) -> bytes:
    """The game's `error_deer.gui` with its root hidden while CAPTURE_KEY is set."""
    return apply_edits(source, ERROR_DEER_EDITS, "error_deer.gui")


def gate_debug_lines(source: bytes) -> tuple[bytes, int]:
    """`source` with every `visible = "[... InDebugMode ...]"` line (quoted or not) made to need CAPTURE_KEY unset
    as well, its BOM and line endings kept; and how many lines were changed."""
    had_bom = source.startswith(BOM)
    text = (source[len(BOM):] if had_bom else source).decode("utf-8")
    crlf = "\r\n" in text
    lines = text.replace("\r\n", "\n").split("\n")
    changed = 0
    for i, line in enumerate(lines):
        m = _DEBUG_VISIBLE.match(line)
        if m:
            expr = re.sub(r"\bInDebugMode\b", GATED_DEBUG, m["expr"])
            lines[i] = '%s"[%s]"%s' % (m["lead"], expr, m["tail"])
            changed += 1
    text = "\n".join(lines)
    if crlf:
        text = text.replace("\n", "\r\n")
    return (BOM if had_bom else b"") + text.encode("utf-8"), changed


def debug_gated_files(base_game, deploy_dir=None) -> dict[str, bytes]:
    """{overlay path: bytes}: each of DEBUG_GATED_FILES from the deployed mod when it ships it, else from the game,
    with its debug lines gated. A file that can't be read, or holds no such line, is left out: nothing of it shows
    in a capture then, or the game's own draws as before."""
    from pathlib import Path

    out: dict[str, bytes] = {}
    for rel in DEBUG_GATED_FILES:
        sources = ([Path(deploy_dir) / rel] if deploy_dir else []) + [Path(base_game) / "game" / rel]
        for path in sources:
            try:
                data = path.read_bytes()
            except OSError:
                continue
            gated, changed = gate_debug_lines(data)
            if changed:
                out[rel] = gated
            break
    return out


def capture_files(base_game, deploy_dir=None) -> dict[str, bytes]:
    """{overlay path: bytes} for a capture session, made from the install folder `base_game` (and the deployed mod's
    folder `deploy_dir`, for DEBUG_GATED_FILES). `capture_gui_missing` when the console or error_deer.gui can't be
    read, `capture_gui_changed` when one has moved."""
    from pathlib import Path

    out: dict[str, bytes] = debug_gated_files(base_game, deploy_dir)
    for rel, source, make in ((CONSOLE_FILE, CONSOLE_SOURCE, capture_console),
                              (ERROR_DEER_FILE, ERROR_DEER_SOURCE, gated_error_deer)):
        path = Path(base_game) / source
        try:
            data = path.read_bytes()
        except OSError as e:
            raise CaptureGuiError("capture_gui_missing", "%s could not be read (%s: %s)"
                                  % (path, type(e).__name__, e.strerror or e)) from e
        out[rel] = make(data)
    return out


# ---- the view


@dataclass(frozen=True)
class Action:
    text: str           # as given: `set:KEY=VALUE`, …
    binding: str        # what the widget's on_start runs


def parse_action(text: str) -> Action:
    """One action of the list in the module's docstring; `bad_action` for anything else."""
    if not isinstance(text, str):
        raise CaptureGuiError("bad_action", "an action is text, not %r" % (text,))
    kind, _, rest = text.partition(":")
    binding = None
    if kind == "set":
        key, sep, value = rest.partition("=")
        if sep and _WORD.fullmatch(key) and _WORD.fullmatch(value):
            binding = "GetVariableSystem.Set( '%s', '%s' )" % (key, value)
    elif kind == "clear" and _WORD.fullmatch(rest):
        binding = "GetVariableSystem.Clear( '%s' )" % rest
    elif kind == "panel":
        name, _, tab = rest.partition(":")
        if _WORD.fullmatch(name) and not tab:
            binding = "InformationPanelBar.OpenPanel( '%s' )" % name
        elif _WORD.fullmatch(name) and _TAB.fullmatch(tab):
            binding = "InformationPanelBar.OpenPanelTab( '%s', '%s' )" % (name, tab)
    elif kind == "market" and _TAB.fullmatch(rest):
        binding = "InformationPanelBar.OpenMarketPanelTab( AccessPlayer.AccessFirstMarket.Self, '%s' )" % rest
    elif text == "construction":
        binding = "InformationPanelBar.OpenConstructionPanel( GetPlayer.Self )"
    elif kind == "construction" and _WORD.fullmatch(rest):
        binding = "InformationPanelBar.OpenConstructionPanelTab( GetPlayer.Self, '%s' )" % rest
    elif text == "state:capital":
        binding = "InformationPanelBar.OpenStatePanel( AccessPlayer.AccessCapital )"
    elif text == "zoom:capital":
        binding = "AccessPlayer.AccessCapital.ZoomToCapital"
    elif kind == "sgui" and _WORD.fullmatch(rest) and rest.startswith("te_") and rest.endswith("_sgui"):
        binding = "GetScriptedGui('%s').Execute( GuiScope.SetRoot( GetPlayer.MakeScope ).End )" % rest
    elif text == "close-panel":
        binding = "InformationPanelBar.ClosePanel"
    if binding is None:
        raise CaptureGuiError("bad_action", "%r is not an action: set:KEY=VALUE, clear:KEY, panel:NAME, "
                              "panel:NAME:TAB, market:TAB, construction[:TAB], state:capital, zoom:capital, "
                              "sgui:te_NAME_sgui or close-panel, each name letters, digits and _" % (text,))
    return Action(text, binding)


def parse_steps(steps) -> list[list[Action]]:
    """Steps (each a list of actions, run together when its widget is created): `bad_action` for an empty or
    over-long list, or an action `parse_action` refuses."""
    if isinstance(steps, (str, bytes)) or not isinstance(steps, Sequence) or not 0 < len(steps) <= MAX_STEPS:
        raise CaptureGuiError("bad_action", "a view is 1 to %d steps, each a list of actions, not %r"
                              % (MAX_STEPS, steps))
    out: list[list[Action]] = []
    for step in steps:
        if isinstance(step, (str, bytes)) or not isinstance(step, Sequence) or not 0 < len(step) <= MAX_ACTIONS:
            raise CaptureGuiError("bad_action", "a step is 1 to %d actions, not %r" % (MAX_ACTIONS, step))
        out.append([parse_action(a) for a in step])
    return out


def view_wrapper_text(steps: Sequence[Sequence[Action]], revision: int) -> str:
    """The overlay's preview file (no BOM: `overlay` adds it) holding one zero-size widget per step, VIEW_WIDGET % i,
    whose `on_start` lines run when it is created, and the revision token in a widget that is never created: the game
    logs the token's warning when it parses the file (the proof of the reload `gui-show` waits for, logged before its
    wrapper is created)."""
    out = ["### Generated by game_qa view (the overlay's own file; rewritten for every view). Revision %d." % revision,
           ""]
    for i, step in enumerate(steps):
        out += ["widget = {", '\tname = "%s"' % (VIEW_WIDGET % i), "\tsize = { 0 0 }", "\tstate = {",
                "\t\tname = te_qa_view", "\t\ttrigger_on_create = yes"]
        out += ['\t\ton_start = "[%s]"' % action.binding for action in step]
        out += ["\t}", "}", ""]
    out += ["widget = {", '\tname = "%s"' % VIEW_TOKEN_WIDGET, "\tsize = { 0 0 }", "\ttextbox = {",
            "\t\tsize = { 0 0 }", '\t\ttext = "%s%d"' % (gui_preview.REV_PREFIX, revision), "\t}", "}"]
    return "\n".join(out) + "\n"
