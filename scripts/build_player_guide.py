#!/usr/bin/env python3
"""Build the player guide PDF from its Markdown chapters.

The guide lives in ``docs/player_guide/``: numbered chapters (``01-*.md``,
``02-*.md``, ...) in reading order, a Typst page template (``template.typ``) and
an ``images/`` folder. This script joins the chapters, converts them to Typst
with pandoc, and compiles the result with the ``typst`` Python package::

    .venv/bin/pip install -r requirements-docs.txt
    .venv/bin/python scripts/build_player_guide.py            # writes the PDF
    python3 scripts/build_player_guide.py --check             # CI: is the PDF current?

``--check`` needs neither pandoc nor Typst. The build stores a SHA-256 of the
guide's sources in the PDF's keywords; ``--check`` recomputes it and fails when
the committed PDF was built from different sources, i.e. someone edited a
chapter without rebuilding.

Chapters are written so they also read correctly on GitHub: a link to another
chapter is an ordinary relative link (``[Banking](04-banking.md#the-policy-rate)``),
which this script rewrites to an in-document link before conversion. Heading
anchors must therefore be unique across the whole guide;
``scripts/analysis/check_player_guide_style.py`` enforces that.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GUIDE_DIR = REPO_ROOT / "docs" / "player_guide"
PDF_NAME = "Vic3TimelineExtended_Player_Guide.pdf"
METADATA_PATH = REPO_ROOT / ".metadata" / "metadata.json"
REPO_URL = "https://github.com/jakeOmega/Vic3TimelineExtended"
# The mod's Workshop thumbnail doubles as the cover art.
COVER_IMAGE = REPO_ROOT / "thumbnail.png"

TITLE = "Vic3TimelineExtended"
SUBTITLE = "A Player's Guide"

# The pandoc build pinned in requirements-docs.txt (pypandoc_binary). Another
# pandoc works, but may lay the PDF out slightly differently.
EXPECTED_PANDOC = "3.9"
PANDOC_FROM = "gfm+implicit_figures"
FINGERPRINT_PREFIX = "source-sha256:"

CHAPTER_GLOB = "[0-9][0-9]-*.md"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

# [text](07-states.md#anchor) or [text](07-states.md)
_CROSS_LINK = re.compile(r"\]\((\d\d-[A-Za-z0-9_-]+\.md)(#[^)\s]*)?\)")
_ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


def chapter_paths(guide_dir: Path = GUIDE_DIR) -> list[Path]:
    """The chapters in reading order: every ``NN-name.md`` in the guide folder."""
    return sorted(guide_dir.glob(CHAPTER_GLOB))


def image_paths(guide_dir: Path = GUIDE_DIR) -> list[Path]:
    images = guide_dir / "images"
    if not images.is_dir():
        return []
    return sorted(p for p in images.rglob("*") if p.suffix.lower() in IMAGE_SUFFIXES)


def source_paths(guide_dir: Path = GUIDE_DIR) -> list[Path]:
    """Every file whose content ends up in the PDF."""
    sources = [guide_dir / "template.typ", *chapter_paths(guide_dir), *image_paths(guide_dir)]
    if COVER_IMAGE.exists():
        sources.append(COVER_IMAGE)
    return sources


def _source_label(path: Path, guide_dir: Path) -> str:
    for base in (guide_dir, REPO_ROOT):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.name


def source_fingerprint(guide_dir: Path = GUIDE_DIR) -> str:
    """SHA-256 over the sources' guide-relative paths and bytes.

    Line endings are normalized so a Windows checkout computes the same value.
    """
    digest = hashlib.sha256()
    for path in source_paths(guide_dir):
        data = path.read_bytes()
        if path.suffix in {".md", ".typ"}:
            data = data.replace(b"\r\n", b"\n")
        digest.update(_source_label(path, guide_dir).encode())
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return digest.hexdigest()


def iter_headings(text: str):
    """Yield ``(line_number, level, heading_text)`` for ATX headings outside code fences."""
    in_fence = False
    for number, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _ATX_HEADING.match(line)
        if match:
            yield number, len(match.group(1)), match.group(2)


def _plain_heading_text(heading: str) -> str:
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)  # links and images
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return re.sub(r"(\*\*|__|\*|_(?=\S)|(?<=\S)_)", "", text)


def github_slug(heading: str) -> str:
    """The anchor GitHub (and pandoc's ``gfm_auto_identifiers``) gives a heading.

    Lower-case, drop everything but letters, digits, spaces, hyphens and
    underscores, then turn each space into a hyphen.
    """
    text = _plain_heading_text(heading).strip().lower()
    text = "".join(ch for ch in text if ch.isalnum() or ch in " -_")
    return text.replace(" ", "-")


def chapter_anchor(path: Path) -> str | None:
    """Anchor of a chapter's first heading, the target of a bare ``NN-x.md`` link."""
    for _, _, heading in iter_headings(path.read_text(encoding="utf-8")):
        return github_slug(heading)
    return None


def rewrite_cross_links(text: str, anchors: dict[str, str | None]) -> str:
    """Turn links between chapter files into links within the single document."""

    def repl(match: re.Match) -> str:
        filename, fragment = match.group(1), match.group(2)
        if fragment:
            return "](" + fragment + ")"
        anchor = anchors.get(filename)
        if anchor is None:
            return match.group(0)
        return "](#" + anchor + ")"

    return _CROSS_LINK.sub(repl, text)


def combined_markdown(guide_dir: Path = GUIDE_DIR) -> str:
    chapters = chapter_paths(guide_dir)
    anchors = {path.name: chapter_anchor(path) for path in chapters}
    parts = [rewrite_cross_links(path.read_text(encoding="utf-8"), anchors) for path in chapters]
    return "\n\n".join(part.strip("\n") for part in parts) + "\n"


_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$")
_TYPST_TABLE = re.compile(r"(#table\(\s*columns: )(\d+)(,)")
# A column whose longest cell is at most this many characters is sized to its
# content; longer ones share the remaining width in proportion to their text.
NARROW_COLUMN_CHARS = 30


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line)]


def markdown_tables(markdown: str) -> list[list[list[str]]]:
    """Every pipe table in document order, as rows of cells (header row first)."""
    lines = markdown.splitlines()
    tables: list[list[list[str]]] = []
    in_fence = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if _FENCE.match(line):
            in_fence = not in_fence
        elif (not in_fence and line.lstrip().startswith("|") and i + 1 < len(lines)
              and _TABLE_SEPARATOR.match(lines[i + 1])):
            rows = [_split_row(line)]
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(_split_row(lines[i]))
                i += 1
            tables.append(rows)
            continue
        i += 1
    return tables


def column_spec(rows: list[list[str]]) -> str | None:
    """Typst ``columns:`` value for a table, or None to leave every column auto.

    Typst's auto columns squeeze a long-text column as hard as a short one, so a
    table of rule names and paragraphs of explanation comes out as four equal
    slivers. Short columns stay ``auto``; long ones share the rest of the width
    by their mean text length.
    """
    width = len(rows[0])
    lengths: list[list[int]] = [[] for _ in range(width)]
    for row in rows:
        for index, cell in enumerate(row[:width]):
            lengths[index].append(len(_plain_heading_text(cell)))
    specs = []
    for column in lengths:
        if max(column, default=0) <= NARROW_COLUMN_CHARS:
            specs.append("auto")
        else:
            # Damped, so a column of short phrases isn't starved next to one of
            # paragraphs: mean length 25 vs 100 gets 1 : 2.8 rather than 1 : 4.
            mean = sum(column) / len(column)
            specs.append(str(max(1, round(10 * mean ** 0.75))) + "fr")
    if all(spec == "auto" for spec in specs):
        return None
    return "(" + ", ".join(specs) + ")"


def apply_column_widths(typst_body: str, markdown: str) -> str:
    """Replace pandoc's all-auto ``columns: N`` with widths from :func:`column_spec`."""
    tables = markdown_tables(markdown)
    matches = list(_TYPST_TABLE.finditer(typst_body))
    if len(matches) != len(tables) or any(
        int(m.group(2)) != len(t[0]) for m, t in zip(matches, tables)
    ):
        print(
            "warning: found " + str(len(tables)) + " Markdown tables but " + str(len(matches))
            + " Typst tables; leaving column widths to Typst",
            file=sys.stderr,
        )
        return typst_body
    specs = iter([column_spec(t) for t in tables])

    def repl(match: re.Match) -> str:
        spec = next(specs)
        return match.group(0) if spec is None else match.group(1) + spec + match.group(3)

    return _TYPST_TABLE.sub(repl, typst_body)


def read_metadata(path: Path = METADATA_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def edition_date(guide_dir: Path = GUIDE_DIR) -> dt.date:
    """The date printed on the title page.

    Today while the sources have uncommitted changes, otherwise the date of the
    last commit that touched them, so rebuilding an unchanged guide gives an
    identical PDF.
    """
    rel = [p.relative_to(REPO_ROOT).as_posix() for p in source_paths(guide_dir)]
    if not rel or _git("status", "--porcelain", "--", *rel):
        return dt.date.today()
    stamp = _git("log", "-1", "--format=%cs", "--", *rel)
    try:
        return dt.date.fromisoformat(stamp)
    except ValueError:
        return dt.date.today()


def find_pandoc() -> str:
    """Prefer the pandoc bundled with pypandoc_binary (pinned), then one on PATH."""
    try:
        import pypandoc  # type: ignore[import-not-found]
    except ImportError:
        pypandoc = None
    if pypandoc is not None:
        bundled = Path(pypandoc.__file__).parent / "files" / "pandoc"
        if bundled.exists():
            return str(bundled)
    found = shutil.which("pandoc")
    if found:
        return found
    sys.exit(
        "pandoc not found. Install the docs requirements:\n"
        "  .venv/bin/pip install -r requirements-docs.txt"
    )


def markdown_to_typst(markdown: str, pandoc: str) -> str:
    version = subprocess.run(
        [pandoc, "--version"], capture_output=True, text=True, check=True
    ).stdout.split("\n", 1)[0]
    if not version.split()[-1].startswith(EXPECTED_PANDOC):
        print(
            "warning: " + version + " (the pinned build is pandoc " + EXPECTED_PANDOC
            + "); the PDF may differ from one built with the pinned version",
            file=sys.stderr,
        )
    result = subprocess.run(
        [pandoc, "--from", PANDOC_FROM, "--to", "typst", "--wrap=preserve"],
        input=markdown,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.exit("pandoc failed:\n" + result.stderr)
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return result.stdout


def _typst_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def typst_document(body: str, *, metadata: dict, edition: dt.date, fingerprint: str) -> str:
    args = {
        "title": _typst_string(TITLE),
        "subtitle": _typst_string(SUBTITLE),
        "game-version": _typst_string(str(metadata.get("supported_game_version", ""))),
        "edition": _typst_string(str(edition.day) + edition.strftime(" %B %Y")),
        "date": "datetime(year: %d, month: %d, day: %d)" % (edition.year, edition.month, edition.day),
        "fingerprint": _typst_string(fingerprint),
        "repo": _typst_string(REPO_URL),
    }
    call = ",\n  ".join(key + ": " + value for key, value in args.items())
    return (
        "// Generated by scripts/build_player_guide.py -- do not edit.\n"
        '#import "template.typ": guide, horizontalrule\n'
        "#show: guide.with(\n  " + call + ",\n)\n\n" + body
    )


def build(output: Path, keep_typst: Path | None = None, guide_dir: Path = GUIDE_DIR) -> Path:
    try:
        import typst  # type: ignore[import-not-found]
    except ImportError:
        sys.exit(
            "The typst package is missing. Install the docs requirements:\n"
            "  .venv/bin/pip install -r requirements-docs.txt"
        )
    fingerprint = source_fingerprint(guide_dir)
    edition = edition_date(guide_dir)
    markdown = combined_markdown(guide_dir)
    body = apply_column_widths(markdown_to_typst(markdown, find_pandoc()), markdown)
    document = typst_document(
        body, metadata=read_metadata(), edition=edition, fingerprint=fingerprint
    )
    # The main file has to sit in the guide folder so the template import and
    # the chapters' relative image paths resolve. The Typst root is the repo
    # root so the template can reach the cover image.
    main = guide_dir / ".player_guide.typ"
    main.write_text(document, encoding="utf-8")
    try:
        typst.compile(
            str(main),
            output=str(output),
            root=str(REPO_ROOT),
            font_paths=[],
            ignore_system_fonts=True,
            timestamp=int(
                dt.datetime.combine(edition, dt.time(12), tzinfo=dt.timezone.utc).timestamp()
            ),
        )
    finally:
        if keep_typst is not None:
            shutil.copyfile(main, keep_typst)
        main.unlink(missing_ok=True)
    return output


def _display(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def check(pdf: Path, guide_dir: Path = GUIDE_DIR) -> int:
    """0 when ``pdf`` carries the fingerprint of the current sources, else 1."""
    fingerprint = source_fingerprint(guide_dir)
    if not pdf.exists():
        print(_display(pdf) + " is missing; run scripts/build_player_guide.py")
        return 1
    if (FINGERPRINT_PREFIX + fingerprint).encode() in pdf.read_bytes():
        print("player guide PDF is up to date with its sources")
        return 0
    print(
        _display(pdf) + " was built from different sources than " + _display(guide_dir)
        + " now holds.\nRebuild it:  .venv/bin/python scripts/build_player_guide.py"
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="only verify the committed PDF matches the sources (no pandoc/typst needed)")
    parser.add_argument("--output", type=Path, default=GUIDE_DIR / PDF_NAME,
                        help="where to write the PDF (default: %(default)s)")
    parser.add_argument("--keep-typst", type=Path, metavar="PATH",
                        help="also save the generated Typst source here, for debugging layout")
    args = parser.parse_args(argv)
    if args.check:
        return check(args.output)
    out = build(args.output, keep_typst=args.keep_typst)
    print("wrote " + str(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
