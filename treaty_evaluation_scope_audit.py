"""Find named-scope reads in treaty AI evaluation_chance (root-only).

Vanilla's treaty_articles.md gives this field only the evaluating country as
root. Partner eligibility belongs in possible, and partner preferences in
inherent_accept_score. This scan covers direct reads, including quoted script
value expressions; it does not expand called scripted triggers/values.
"""
import argparse
import re
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

from iterator_limit_audit import blank_comments_and_strings
from paradox_file_parser import ParadoxFileParser

_TOKEN = re.compile(
    r"(?P<close>\})|(?P<key>[A-Za-z_][A-Za-z0-9_.:|@$\-]*)"
    r"\s*(?:\?=|[!<>=]=|[=<>])\s*(?:(?P<open>\{)|[^\s{}]+)?"
    r"|(?P<anon>\{)"
)
_SCOPE = re.compile(r"\bscope:[A-Za-z_][A-Za-z0-9_]*", re.IGNORECASE)


@dataclass(frozen=True)
class Flag:
    file: str
    line: int
    article: str
    scope: str


def scan_text(text: str, rel_path: str) -> list[Flag]:
    """Ignore comments and unrelated fields, retaining source line numbers."""
    clean, _ = blank_comments_and_strings(text)
    starts = [0] + [m.end() for m in re.finditer(r"\n", text)]
    stack = []
    flags = []
    evaluation_start = None
    for token in _TOKEN.finditer(clean):
        if token.group("close"):
            if len(stack) == 3 and stack[1:] == ["ai", "evaluation_chance"]:
                # Keep quoted expressions here: a function argument can read a
                # named scope even though quotes protect its braces/comments.
                offset = evaluation_start
                for line in text[evaluation_start:token.start()].splitlines(keepends=True):
                    code = ParadoxFileParser._strip_comment(line)
                    for hit in _SCOPE.finditer(code):
                        flags.append(Flag(rel_path, bisect_right(starts, offset + hit.start()),
                                          stack[0], hit.group()))
                    offset += len(line)
                evaluation_start = None
            if stack:
                stack.pop()
        elif token.group("open"):
            key = token.group("key")
            if len(stack) == 2 and stack[1] == "ai" and key == "evaluation_chance":
                evaluation_start = token.end()
            stack.append(key)
        elif token.group("anon"):
            stack.append(None)
    return flags


def audit(mod_path: str | Path) -> list[Flag]:
    root = Path(mod_path)
    flags = []
    for path in sorted((root / "common/treaty_articles").rglob("*.txt")):
        flags.extend(scan_text(path.read_text(encoding="utf-8-sig"),
                               path.relative_to(root).as_posix()))
    return flags


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mod-path", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--strict", action="store_true", help="Fail if a named-scope read is found")
    args = parser.parse_args(argv)
    flags = audit(args.mod_path)
    for flag in flags:
        print(f"{flag.file}:{flag.line}: {flag.article}: {flag.scope} in root-only evaluation_chance")
    print(f"Treaty evaluation scope audit: {len(flags)} invalid named-scope reads")
    return int(args.strict and bool(flags))


if __name__ == "__main__":
    raise SystemExit(main())
