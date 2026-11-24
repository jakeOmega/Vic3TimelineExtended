#!/usr/bin/env python3
"""Write a variant mod folder for a `game_qa` session whose console is see-through.

    python3 scripts/analysis/qa_see_through_console.py 'D:\\vic3te-data\\my-variant'   # or its /mnt/d/... path
    python3 -m game_qa start ... --add-mod 'D:\\vic3te-data\\my-variant'

The game's console (`game/gui/console.gui`) covers the left fifth of a 3840-wide window from top to bottom and blocks
clicks under it, which is where every side panel opens. For a session that looks at panels in their place, this writes
a copy of the installed game's file in which the console draws nothing and lets clicks through, with its input line
left exactly where it was: the harness's `click --console` point (`CONSOLE_INPUT_LINE`) still lands on it, and what a
verb types is still read from the log, not from the screen. Only the edit line, at half strength, is drawn.

The folder also gets the `.metadata/metadata.json` that `--add-mod` asks for and two localization files with one
marker key each (`localization/english/` and its `replace/`): a key appended to a file that was there at launch is
live on the next `gui-show`, so a branch's new or changed loc can be put there while the session runs.

The file must be in the folder before `start`: one added to a running game is not picked up (tried 2026-11-24). The
repo keeps no copy of the game's file; a patch that moves one of the lines changed here makes this script stop, with
the line it could not find, rather than write a console that might not work.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BOM = b"\xef\xbb\xbf"

# (what to find, what to put, how many times it must be there). Each is a whole-line edit of vanilla 1.15.2's file.
EDITS: tuple[tuple[str, str, int], ...] = (
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
    # The edit line, faint.
    ("\t\t\tbackground = {\n\t\t\t\tusing = ConsoleEditbg\n\t\t\t\tmargin = { 4 0 }\n",
     "\t\t\tbackground = {\n\t\t\t\tusing = ConsoleEditbg\n\t\t\t\tmargin = { 4 0 }\n\t\t\t\talpha = 0.5\n", 1),
)


class ConsoleFileChanged(ValueError):
    """The game's console.gui no longer holds a line this script edits."""


def see_through(source: bytes) -> bytes:
    """The game's `console.gui` with the console see-through. Keeps the file's BOM and line endings."""
    had_bom = source.startswith(BOM)
    text = source[len(BOM):].decode("utf-8") if had_bom else source.decode("utf-8")
    crlf = "\r\n" in text
    text = text.replace("\r\n", "\n")
    for old, new, count in EDITS:
        if text.count(old) != count:
            raise ConsoleFileChanged("expected %d of %r in the game's console.gui, found %d" % (count, old, text.count(old)))
        text = text.replace(old, new)
    if crlf:
        text = text.replace("\n", "\r\n")
    return (BOM if had_bom else b"") + text.encode("utf-8")


def metadata(name: str, game_version: str) -> str:
    return json.dumps({
        "name": name,
        "id": "",
        "version": "0.0.1",
        "supported_game_version": game_version,
        "short_description": "Scratch variant for a game_qa session: a see-through console, and loc a GUI branch under "
                             "evaluation leans on.",
        "tags": ["Gameplay"],
        "relationships": [],
        "game_custom_data": {"multiplayer_synchronized": True},
    }, indent="\t") + "\n"


def wsl_path(given: str) -> Path:
    """A `D:\\x\\y` path as `/mnt/d/x/y`; any other path as it is."""
    m = re.match(r"^([A-Za-z]):[\\/](.*)$", given)
    if m:
        return Path("/mnt") / m.group(1).lower() / m.group(2).replace("\\", "/")
    return Path(given)


def write_variant(folder: Path, console_source: Path, game_version: str, name: str) -> list[Path]:
    """Write the variant into `folder` (made if missing; files there are overwritten). Returns what was written."""
    written = []
    files = {
        folder / "gui" / "console.gui": see_through(console_source.read_bytes()),
        folder / ".metadata" / "metadata.json": metadata(name, game_version).encode("utf-8"),
        folder / "localization" / "english" / "te_qa_variant_l_english.yml":
            BOM + b'l_english:\n te_qa_variant_marker:0 "QA variant loaded"\n',
        folder / "localization" / "english" / "replace" / "te_qa_variant_replace_l_english.yml":
            BOM + b'l_english:\n te_qa_variant_replace_marker:0 "QA variant (replace) loaded"\n',
    }
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("folder", help="the variant folder to write: a drive path (D:\\...) or its WSL path, outside "
                                       "the game's user-data folder")
    parser.add_argument("--game", help="the game's install folder (default: path_constants.base_game_path)")
    parser.add_argument("--game-version", default="1.15.2", help="supported_game_version for the metadata")
    parser.add_argument("--name", default="TE QA variant (see-through console)")
    args = parser.parse_args(argv)
    if args.game:
        game = Path(args.game)
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        import path_constants
        game = Path(path_constants.base_game_path)
    source = game / "game" / "gui" / "console.gui"
    if not source.is_file():
        print("no console.gui at %s" % source, file=sys.stderr)
        return 2
    try:
        written = write_variant(wsl_path(args.folder), source, args.game_version, args.name)
    except ConsoleFileChanged as e:
        print("not written: %s" % e, file=sys.stderr)
        return 2
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
