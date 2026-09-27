#!/usr/bin/env python3
"""Lint the player guide's Markdown for structure problems and machine-sounding prose.

The player guide (``docs/player_guide/NN-*.md``) is read by players, not
modders. This check keeps it that way, and keeps it readable:

* **Structure** — one ``#`` chapter heading per file, no skipped heading levels,
  no heading followed straight by another heading, heading anchors unique across
  the guide (the PDF is one document, so a repeated anchor breaks its links), and
  every in-guide link pointing at a heading that exists.
* **Internals** — no script keys (``snake_case`` identifiers), mod file paths,
  or raw HTML (pandoc drops HTML when it builds the PDF, silently). An image
  must stand alone in its paragraph, or pandoc renders it inline with no caption.
* **Prose** — the language tells listed in Wikipedia's "Signs of AI writing":
  inflated vocabulary (*pivotal*, *showcase*, *seamless*), copula avoidance
  (*serves as*), negative parallelisms (*not just X but Y*), stock openers
  (*Additionally,*), bold-headed bullet lists, em-dash and bold overuse,
  Title Case headings, emoji and curly quotes.

A line can opt out of a rule with an HTML comment at the **end** of the line —
``<!-- style: allow ai-vocab -->`` (several rules: ``allow a, b``). GitHub hides
the comment and pandoc drops it. For paragraph-level rules (``em-dash``,
``bold-density``) the comment may sit on any line of the paragraph. Never start a
line with the comment: CommonMark then treats the whole paragraph as an HTML
block and the rest of that line vanishes from both GitHub and the PDF
(``leading-comment`` catches that). A comment alone on its own line is fine; the
chapters use that for ``<!-- screenshot: ... -->`` placeholders.

    python3 scripts/analysis/check_player_guide_style.py            # report
    python3 scripts/analysis/check_player_guide_style.py --strict   # CI: exit 1 on findings
    python3 scripts/analysis/check_player_guide_style.py --stats    # words per chapter
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_player_guide import (  # noqa: E402
    GUIDE_DIR,
    _CROSS_LINK,
    chapter_paths,
    github_slug,
    iter_headings,
)

# ── Vocabulary and phrases ──────────────────────────────────────────────────
# Words Wikipedia lists as over-used by language models, plus the usual
# promotional filler. Literal senses exist ("the key in the top-right corner");
# suppress those per line.
AI_WORDS = [
    r"boasts?", r"boasting", r"bolster(?:s|ed|ing)?", r"crucial(?:ly)?",
    r"delv(?:e|es|ed|ing)", r"emphasi[sz](?:e|es|ed|ing)", r"enduring",
    r"garner(?:s|ed|ing)?", r"intricate", r"intricacies", r"interplay", r"key",
    r"landscapes?", r"meticulous(?:ly)?", r"pivotal", r"underscor(?:e|es|ed|ing)",
    r"tapestry", r"testament", r"valuable", r"vibrant", r"enhanc(?:e|es|ed|ing|ement)",
    r"foster(?:s|ed|ing)?", r"highlight(?:s|ed|ing)?", r"showcas(?:e|es|ed|ing)",
    r"seamless(?:ly)?", r"robust", r"comprehensive(?:ly)?", r"nuanced?", r"multifaceted",
    r"holistic", r"synerg(?:y|ies)", r"realms?", r"embark(?:s|ed|ing)?", r"journeys?",
    r"elevat(?:e|es|ed|ing)", r"empower(?:s|ed|ing)?", r"unleash(?:es|ed|ing)?",
    r"myriad", r"plethora", r"diverse", r"leverag(?:ed|ing)", r"groundbreaking",
    r"cutting-edge", r"game-changer", r"transformative", r"captivat(?:e|es|ed|ing)",
    r"thrilling", r"breathtaking", r"invaluable", r"paramount", r"noteworthy",
    r"commendable", r"indelible", r"profound(?:ly)?",
]

AI_PHRASES = [
    r"serves? as", r"serving as", r"stands? as", r"acts? as an?",
    r"plays? an? (?:key|crucial|vital|significant|important|major|central|pivotal|critical) role",
    r"(?:it is|it's) worth noting", r"worth noting", r"(?:it is|it's) important to (?:note|remember)",
    r"in conclusion", r"in summary", r"to summari[sz]e", r"in essence", r"at its core",
    r"whether you(?:'re| are)", r"dive into", r"deep dive", r"a wide (?:range|array|variety) of",
    r"a variety of", r"the world of", r"when it comes to", r"in connection with",
    r"each with (?:its|their) own", r"ever-(?:changing|evolving)", r"let's", r"let us",
    r"you might be wondering", r"at the heart of", r"needless to say", r"paving the way",
    r"unlock(?:s|ing)? the (?:full|true) potential", r"delicate balance", r"strikes? a balance",
    r"not only", r"a (?:rich|vast) array", r"in today's",
]

OPENERS = [
    "Additionally", "Furthermore", "Moreover", "Notably", "Importantly", "Crucially",
    "Ultimately", "Overall", "In summary", "In conclusion", "Essentially", "Interestingly",
    "Remember", "Simply put",
]

# Words that stay lower-case inside a sentence-case heading.
SMALL_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "into", "of", "on",
    "or", "the", "to", "vs", "via", "with", "without", "your", "its", "their", "per",
}

_WORD_RE = re.compile(r"\b(?:" + "|".join(AI_WORDS) + r")\b", re.IGNORECASE)
_PHRASE_RE = re.compile(r"\b(?:" + "|".join(AI_PHRASES) + r")\b", re.IGNORECASE)
_OPENER_RE = re.compile(r"(?:^|[.!?]\s+)(" + "|".join(re.escape(o) for o in OPENERS) + r"),")
_NEG_PARALLEL = [
    re.compile(r"\bnot\s+(?:just|merely|simply)\b", re.IGNORECASE),
    re.compile(r"\b(?:isn't|aren't|wasn't|is not|are not)\b[^.;:!?]{1,80}?(?:—|--|;|,)\s*(?:it's|it is|they're|they are)\b",
               re.IGNORECASE),
    re.compile(r"\bno\s+\w+,\s+no\s+\w+,\s+just\b", re.IGNORECASE),
]
_INLINE_HEADER_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\*\*|__)[^*_]+(?:\*\*|__)\s*(?::|—|–|\s-\s)")
_BOLD_COLON = re.compile(r"(?:\*\*|__)[^*_\n]{1,60}:(?:\*\*|__)")
_BOLD_SPAN = re.compile(r"(?:\*\*|__)(?=\S)(.+?)(?<=\S)(?:\*\*|__)")
_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F000-\U0001F2FF\U00002600-\U000026FF️]"
)
_CURLY = re.compile("[‘’“”]")
_THEMATIC_BREAK = re.compile(r"^\s{0,3}(?:(?:-\s*){3,}|(?:\*\s*){3,}|(?:_\s*){3,})$")
_SNAKE = re.compile(r"(?<![\w/.#-])[a-z][a-z0-9]*(?:_[a-z0-9]+)+(?![\w/-])")
_MOD_PATH = re.compile(r"\b(?:common|events|gui|localization|gfx|map_data)/[\w./-]+")
_MERGE_DIRECTIVE = re.compile(r"\b(?:INJECT|REPLACE|TRY_INJECT|INJECT_OR_CREATE):")
_RAW_HTML = re.compile(r"<(?!!--)/?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*)?/?>")
_SUPPRESS = re.compile(r"<!--\s*style:\s*allow\s+([\w,\s-]+?)\s*-->")
_INLINE_CODE = re.compile(r"`[^`]*`")
_LINK_TARGET = re.compile(r"\]\(([^)\s]+)\)")
_URL = re.compile(r"https?://\S+")
_TABLE_ROW = re.compile(r"^\s*\|")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")

ALL_RULES = [
    "ai-vocab", "ai-phrase", "stock-opener", "negative-parallel", "inline-header-list",
    "em-dash", "bold-density", "emoji", "curly-quote", "title-case-heading", "heading-skip",
    "empty-heading", "chapter-heading", "thematic-break", "duplicate-anchor", "broken-link",
    "script-key", "mod-path", "raw-html", "leading-comment", "inline-image",
]


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str
    message: str

    def format(self) -> str:
        try:
            shown = self.path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            shown = str(self.path)
        return shown + ":" + str(self.line) + ": [" + self.rule + "] " + self.message


def _suppressed(line: str) -> set[str]:
    rules: set[str] = set()
    for match in _SUPPRESS.finditer(line):
        rules.update(r.strip() for r in match.group(1).split(",") if r.strip())
    return rules


def _prose(line: str) -> str:
    """The line with code spans, URLs, link targets and comments removed."""
    line = _SUPPRESS.sub("", line)
    line = re.sub(r"<!--.*?-->", "", line)
    line = _INLINE_CODE.sub("", line)
    line = _LINK_TARGET.sub("]", line)
    return _URL.sub("", line)


def _excerpt(text: str, start: int, end: int) -> str:
    lo, hi = max(0, start - 30), min(len(text), end + 30)
    return ("…" if lo else "") + text[lo:hi].strip() + ("…" if hi < len(text) else "")


def _is_title_case(heading: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z'’-]*", _prose(heading))
    content = [w for i, w in enumerate(words) if i > 0 and w.lower() not in SMALL_WORDS]
    # Two capitalised words are usually a proper name ("United Nations").
    if len(content) < 3:
        return False
    return all(w[0].isupper() and not w.isupper() for w in content)


def _paragraphs(lines: list[str], skip: set[int]):
    """Yield runs of consecutive prose lines as ``(first_line_number, [lines])``."""
    block: list[tuple[int, str]] = []
    for number, line in enumerate(lines, 1):
        breaks = (
            number in skip
            or not line.strip()
            or _TABLE_ROW.match(line)
            or line.lstrip().startswith("#")
            or _LIST_ITEM.match(line)
        )
        if breaks:
            if block:
                yield block
            block = []
            if number not in skip and line.strip() and (_TABLE_ROW.match(line) or _LIST_ITEM.match(line)):
                # A table row or list item is its own unit.
                yield [(number, line)]
            continue
        block.append((number, line))
    if block:
        yield block


def lint_text(path: Path, text: str) -> list[Finding]:
    """Rules that need only this one file."""
    findings: list[Finding] = []
    lines = text.splitlines()

    def add(number: int, rule: str, message: str) -> None:
        if rule not in _suppressed(lines[number - 1]):
            findings.append(Finding(path, number, rule, message))

    fence_lines: set[int] = set()
    in_fence = False
    for number, line in enumerate(lines, 1):
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            fence_lines.add(number)
        elif in_fence:
            fence_lines.add(number)

    # Headings.
    headings = list(iter_headings(text))
    if not headings or headings[0][1] != 1:
        findings.append(Finding(path, headings[0][0] if headings else 1, "chapter-heading",
                                "a chapter must open with a single '#' heading"))
    for number, level, _ in headings[1:]:
        if level == 1:
            add(number, "chapter-heading", "only one '#' heading per chapter file")
    previous_level = 0
    for number, level, heading in headings:
        if previous_level and level > previous_level + 1:
            add(number, "heading-skip", "heading jumps from level " + str(previous_level) + " to " + str(level))
        previous_level = level
        if _is_title_case(heading):
            add(number, "title-case-heading", "use sentence case: '" + heading + "'")
    heading_lines = {n: lvl for n, lvl, _ in headings}
    for number, level in heading_lines.items():
        following = next((n for n in range(number + 1, len(lines) + 1) if lines[n - 1].strip()), None)
        if following in heading_lines and heading_lines[following] > level:
            add(number, "empty-heading", "heading has no text before its first subheading")

    # Line rules.
    for number, line in enumerate(lines, 1):
        if number in fence_lines:
            continue
        stripped = line.strip()
        if stripped.startswith("<!--") and re.sub(r"^<!--.*?-->", "", stripped).strip():
            findings.append(Finding(path, number, "leading-comment",
                                    "text after a line-opening <!-- ... --> is part of an HTML block, "
                                    "which GitHub and pandoc drop; put the comment at the end of the line"))
        prose = _prose(line)
        for match in _WORD_RE.finditer(prose):
            add(number, "ai-vocab", "'" + match.group(0) + "': " + _excerpt(prose, match.start(), match.end()))
        for match in _PHRASE_RE.finditer(prose):
            add(number, "ai-phrase", "'" + match.group(0) + "': " + _excerpt(prose, match.start(), match.end()))
        for match in _OPENER_RE.finditer(prose):
            add(number, "stock-opener", "sentence opens with '" + match.group(1) + ",'")
        for pattern in _NEG_PARALLEL:
            for match in pattern.finditer(prose):
                add(number, "negative-parallel", _excerpt(prose, match.start(), match.end()))
        if _INLINE_HEADER_ITEM.match(line) or _BOLD_COLON.search(line):
            add(number, "inline-header-list",
                "bold lead-in ('**Term**: ...'); write the item as a sentence or use a table")
        if _EMOJI.search(line):
            add(number, "emoji", "emoji in text")
        if _CURLY.search(line):
            add(number, "curly-quote", "use straight quotes; the PDF build curls them")
        if _THEMATIC_BREAK.match(line):
            add(number, "thematic-break", "no horizontal rules between sections; headings separate them")
        code_free = _SUPPRESS.sub("", _INLINE_CODE.sub("", line))
        code_free = _URL.sub("", _LINK_TARGET.sub("]", code_free))
        for match in _SNAKE.finditer(code_free):
            add(number, "script-key", "script key '" + match.group(0) + "'; use the in-game name")
        for match in _MOD_PATH.finditer(code_free):
            add(number, "mod-path", "mod file path '" + match.group(0) + "'")
        if _MERGE_DIRECTIVE.search(code_free):
            add(number, "mod-path", "script merge directive in player text")
        image = _IMAGE.search(line)
        if image:
            alone = line.strip() == image.group(0)
            before = number < 2 or not lines[number - 2].strip()
            after = number >= len(lines) or not lines[number].strip()
            if not (alone and before and after):
                add(number, "inline-image",
                    "an image must be alone in its paragraph (blank lines around it) to become "
                    "a captioned figure in the PDF")
        for match in _RAW_HTML.finditer(_INLINE_CODE.sub("", line)):
            add(number, "raw-html", "raw HTML '" + match.group(0) + "' is dropped from the PDF")

    # Paragraph rules.
    for block in _paragraphs(lines, fence_lines | set(heading_lines)):
        joined = " ".join(_prose(l) for _, l in block)
        allowed: set[str] = set()
        for _, l in block:
            allowed |= _suppressed(l)
        first = block[0][0]
        dashes = joined.count("—") + len(re.findall(r"\s--\s", joined))
        if dashes > 1 and "em-dash" not in allowed:
            findings.append(Finding(path, first, "em-dash",
                                    str(dashes) + " em dashes in one paragraph; use commas, colons or full stops"))
        bolds = len(_BOLD_SPAN.findall(joined))
        if bolds > 2 and "bold-density" not in allowed:
            findings.append(Finding(path, first, "bold-density",
                                    str(bolds) + " bold spans in one paragraph; bold at most the term being defined"))
    return findings


def lint_guide(paths: list[Path]) -> list[Finding]:
    """Per-file rules plus the cross-file ones: unique anchors and live links."""
    findings: list[Finding] = []
    texts = {path: path.read_text(encoding="utf-8") for path in paths}
    anchors: dict[str, tuple[Path, int]] = {}
    per_file: dict[str, set[str]] = {}
    for path, text in texts.items():
        findings.extend(lint_text(path, text))
        per_file[path.name] = set()
        for number, _, heading in iter_headings(text):
            slug = github_slug(heading)
            per_file[path.name].add(slug)
            if slug in anchors:
                other, other_line = anchors[slug]
                findings.append(Finding(path, number, "duplicate-anchor",
                                        "heading anchor '#" + slug + "' is also used at " + other.name + ":"
                                        + str(other_line) + "; the PDF needs unique headings"))
            else:
                anchors[slug] = (path, number)
    all_anchors = set(anchors)
    for path, text in texts.items():
        for number, line in enumerate(text.splitlines(), 1):
            if "broken-link" in _suppressed(line):
                continue
            for match in _LINK_TARGET.finditer(_INLINE_CODE.sub("", line)):
                target = match.group(1)
                if target.startswith("#"):
                    if target[1:] not in per_file[path.name]:
                        where = " (it is in another chapter; link to that file)" if target[1:] in all_anchors else ""
                        findings.append(Finding(path, number, "broken-link",
                                                "no heading '" + target + "' in this chapter" + where))
                    continue
                cross = _CROSS_LINK.match("](" + target + ")")
                if cross:
                    filename, fragment = cross.group(1), cross.group(2)
                    if filename not in per_file:
                        findings.append(Finding(path, number, "broken-link", "no chapter file '" + filename + "'"))
                    elif fragment and fragment[1:] not in per_file[filename]:
                        findings.append(Finding(path, number, "broken-link",
                                                "no heading '" + fragment + "' in " + filename))
                    continue
                if target.startswith("images/") and not (path.parent / target).exists():
                    findings.append(Finding(path, number, "broken-link", "image '" + target + "' does not exist"))
    return findings


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", _prose(text)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="*", type=Path,
                        help="chapters to check (default: every chapter in docs/player_guide/)")
    parser.add_argument("--strict", action="store_true", help="exit 1 when anything is found")
    parser.add_argument("--stats", action="store_true", help="print the word count of each chapter")
    args = parser.parse_args(argv)

    paths = [p.resolve() for p in args.files] if args.files else chapter_paths(GUIDE_DIR)
    if args.files:
        # Cross-file rules need the whole guide; report only the named files.
        wanted = set(paths)
        findings = [f for f in lint_guide(chapter_paths(GUIDE_DIR) or paths) if f.path in wanted]
        if not any(p in chapter_paths(GUIDE_DIR) for p in paths):
            findings = lint_guide(paths)
    else:
        findings = lint_guide(paths)

    for finding in sorted(findings, key=lambda f: (str(f.path), f.line, f.rule)):
        print(finding.format())
    if args.stats:
        total = 0
        for path in paths:
            count = word_count(path.read_text(encoding="utf-8"))
            total += count
            print("{:>7,}  {}".format(count, path.name))
        print("{:>7,}  total".format(total))
    print(str(len(findings)) + " finding(s) in " + str(len(paths)) + " chapter(s)", file=sys.stderr)
    return 1 if (args.strict and findings) else 0


if __name__ == "__main__":
    sys.exit(main())
