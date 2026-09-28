"""Stage localization for the game's ten non-English languages.

Victoria 3 does not fall back to English for a key the player's language lacks:
it shows the raw key. The mod ships only `localization/english/`, so a player
running the game in German (or any other language) would see `je_strategic_reserve`
where the English player sees "Strategic Reserve". This script writes, for every
English loc file, one copy per language that the engine loads in its place:

    localization/english/te_events_l_english.yml
        -> <out>/german/te_events_l_german.yml   (header `l_german:`)
    localization/english/replace/x_l_english.yml
        -> <out>/german/replace/x_l_german.yml

A copy is byte-identical to its English source apart from the header line and
the file name, so the UTF-8 BOM and every comment carry over. A language with a
translation memory (`i18n/<language>/tm/`, from scripts/i18n/translate_loc.py)
also gets each translated value swapped in, line by line, with the declined
country-name forms added after their base key; untranslated keys, and keys
whose English changed too much since translation, stay English. `replace/` is
copied too: its keys are vanilla keys the mod redefines (renamed goods, the
redesigned citizenship laws), and the mod's English text is right where the
vanilla translation would describe the unmodded game.

Nothing here is committed. `scripts/deploy.sh` runs this into `build/localization/`
(gitignored, and ignored by the deploy watcher) and rsyncs the result into the
Paradox mod folder as `localization/<language>/`. Writing into the repo's own
`localization/` would put ten copies of every English change into each diff and
have ModState parse them.

The script only writes a file whose content changed, so `rsync -t` sees stable
mtimes, and removes staged files whose English source is gone. Standard library
only: deploy.sh runs it with the system `python3`.

Usage:
    python3 scripts/generators/gen_non_english_loc.py [--out DIR] [--quiet]
    python3 scripts/generators/gen_non_english_loc.py --list-languages
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENGLISH_DIR = os.path.join(REPO_ROOT, "localization", "english")
DEFAULT_OUT = os.path.join(REPO_ROOT, "build", "localization")

# The vanilla game's localization languages other than English, by the folder and
# `_l_<language>.yml` suffix vanilla uses for each.
LANGUAGES = (
    "braz_por",
    "french",
    "german",
    "japanese",
    "korean",
    "polish",
    "russian",
    "simp_chinese",
    "spanish",
    "turkish",
)

# The translation-memory field holding each language's text.
TM_FIELDS = {"german": "de"}

SOURCE_SUFFIX = "_l_english.yml"
SOURCE_HEADER = "l_english:"


class LocSourceError(ValueError):
    """An English loc file this script cannot turn into a copy."""


@dataclass
class BuildResult:
    written: list[str] = field(default_factory=list)
    unchanged: int = 0
    removed: list[str] = field(default_factory=list)


def output_relpath(english_relpath: str, language: str) -> str:
    """Map `sub/x_l_english.yml` (relative to localization/english) to
    `<language>/sub/x_l_<language>.yml` (relative to the output root)."""
    if not english_relpath.endswith(SOURCE_SUFFIX):
        raise LocSourceError(
            f"{english_relpath}: name does not end in {SOURCE_SUFFIX!r}; the game "
            f"reads a loc file's language from that suffix"
        )
    stem = english_relpath[: -len(SOURCE_SUFFIX)]
    return os.path.join(language, f"{stem}_l_{language}.yml")


def render(english: bytes, language: str, name: str = "<source>", overlay=None) -> bytes:
    """Return `english` with its `l_english:` header line renamed to `l_<language>:`.

    The header is the first line that is neither blank nor a comment. Without an
    overlay everything else, the BOM included, is returned unchanged; with one,
    each value the overlay translates is replaced in place (key, version number
    and trailing comment kept) and its extra lines follow it."""
    text = english.decode("utf-8")
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        stripped = line.strip().lstrip("\ufeff")
        if not stripped or stripped.startswith("#"):
            continue
        if stripped != SOURCE_HEADER:
            raise LocSourceError(
                f"{name}: first non-blank line is {stripped!r}, expected {SOURCE_HEADER!r}"
            )
        lines[index] = line.replace(SOURCE_HEADER, f"l_{language}:", 1)
        if overlay is not None:
            lines[index + 1:] = _translate_lines(lines[index + 1:], overlay)
        return "".join(lines).encode("utf-8")
    raise LocSourceError(f"{name}: no {SOURCE_HEADER!r} header")


def _translate_lines(lines: list[str], overlay) -> list[str]:
    from mod_state import split_loc_line

    out = []
    for line in lines:
        parsed = split_loc_line(line)
        if parsed is None:
            out.append(line)
            continue
        key, en, _trailing = parsed
        start = line.index('"', line.index(":"))
        end = start + 1 + len(en)
        value = overlay.value(key, en)
        out.append(line[: start + 1] + value + line[end:] if value != en else line)
        newline = "\r\n" if line.endswith("\r\n") else "\n"
        for extra_key, extra_value in overlay.extra_lines(key, en):
            out.append(f' {extra_key}:0 "{extra_value}"{newline}')
    return out


def load_overlays(languages: tuple[str, ...] = LANGUAGES) -> dict:
    """{language: Overlay} for every language with a translation memory."""
    for path in (REPO_ROOT, os.path.join(REPO_ROOT, "scripts", "i18n")):
        if path not in sys.path:
            sys.path.insert(0, path)
    from translate_loc import load_overlay

    overlays = {}
    for language in languages:
        overlay = load_overlay(language, TM_FIELDS.get(language, language))
        if overlay is not None:
            overlays[language] = overlay
    return overlays


def iter_english_files(english_dir: str) -> list[str]:
    """Every `.yml` under `english_dir`, `replace/` included, relative to it."""
    found = []
    for dirpath, dirnames, filenames in os.walk(english_dir):
        dirnames.sort()
        for name in sorted(filenames):
            if name.endswith(".yml"):
                found.append(os.path.relpath(os.path.join(dirpath, name), english_dir))
    return found


def build(
    english_dir: str = ENGLISH_DIR,
    out_dir: str = DEFAULT_OUT,
    languages: tuple[str, ...] = LANGUAGES,
    overlays: dict | None = None,
) -> BuildResult:
    """Write every language's copies into `out_dir`; prune stale ones.

    Raises LocSourceError, before writing anything, if an English file is
    misnamed or has no `l_english:` header."""
    sources = iter_english_files(english_dir)
    if not sources:
        raise LocSourceError(f"no .yml files under {english_dir}")

    planned: dict[str, bytes] = {}
    for rel in sources:
        with open(os.path.join(english_dir, rel), "rb") as fh:
            english = fh.read()
        for language in languages:
            overlay = (overlays or {}).get(language)
            planned[output_relpath(rel, language)] = render(english, language, rel, overlay)

    result = BuildResult()
    for rel, content in sorted(planned.items()):
        path = os.path.join(out_dir, rel)
        try:
            with open(path, "rb") as fh:
                if fh.read() == content:
                    result.unchanged += 1
                    continue
        except FileNotFoundError:
            pass
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(content)
        result.written.append(rel)

    # Prune only inside the language folders this script owns.
    for language in languages:
        root = os.path.join(out_dir, language)
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root, topdown=False):
            for name in filenames:
                rel = os.path.relpath(os.path.join(dirpath, name), out_dir)
                if rel not in planned:
                    os.remove(os.path.join(dirpath, name))
                    result.removed.append(rel)
            if dirpath != root and not os.listdir(dirpath):
                os.rmdir(dirpath)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=DEFAULT_OUT, help="output root (default: build/localization)")
    parser.add_argument("--quiet", action="store_true", help="print nothing unless files changed")
    parser.add_argument("--list-languages", action="store_true", help="print the language folder names and exit")
    args = parser.parse_args(argv)

    if args.list_languages:
        print("\n".join(LANGUAGES))
        return 0

    overlays = load_overlays()
    try:
        result = build(out_dir=args.out, overlays=overlays)
    except LocSourceError as exc:
        print(f"gen_non_english_loc: {exc}", file=sys.stderr)
        return 1

    if result.written or result.removed or not args.quiet:
        print(
            f"gen_non_english_loc: {len(result.written)} written, "
            f"{len(result.removed)} removed, {result.unchanged} unchanged "
            f"({len(LANGUAGES)} languages) -> {os.path.relpath(args.out, REPO_ROOT)}"
        )
        for language, overlay in sorted(overlays.items()):
            c = overlay.counts
            print(
                f"  {language}: {c['translated']} translated, {c['stale_kept']} changed slightly "
                f"(old translation kept), {c['stale_english']} changed (English until "
                f"retranslated), {c['english']} not yet translated"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
