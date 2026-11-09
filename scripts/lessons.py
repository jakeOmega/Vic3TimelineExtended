#!/usr/bin/env python3
"""Find what the guides already say about the thing you are about to write.

    python3 scripts/lessons.py add_modifier            # sections that mention it
    python3 scripts/lessons.py add_modifier multiplier # sections with both
    python3 scripts/lessons.py trigger_event --show 2  # print the second hit
    python3 scripts/lessons.py --index                 # every section heading

The guides hold several hundred lessons, each a `##` section whose heading
states the rule. They are filed in the order they were learned, so the way in
is a search, and the best search term is a name from the script: an effect, a
trigger, a modifier, a scope, a file. Run this before writing an effect or
trigger you have not used in this mod before.

Hits are ranked: a term in the heading counts far more than one in the body.
Stdlib only; needs neither the server nor the game.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GUIDES = (
    "docs/guides/scripting_best_practices.md",
    "docs/guides/event_creation_guide.md",
    "docs/guides/gui_modding_guide.md",
    "docs/guides/gui_style_guide.md",
    "docs/guides/python_tools.md",
    "docs/guides/git_workflow.md",
    ".claude/rules/script.md",
)

HEADING = re.compile(r"^(#{2,3}) +(.*\S)\s*$")


def sections(repo_root=REPO_ROOT, guides=GUIDES):
    """Yield (path, line, heading, body) for every `##` / `###` section. A code
    fence's `#` lines are not headings."""
    for rel in guides:
        path = os.path.join(repo_root, rel)
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                lines = fh.read().replace("\r\n", "\n").split("\n")
        except OSError:
            continue
        current, fenced = None, False
        for number, line in enumerate(lines, 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
            match = None if fenced else HEADING.match(line)
            if match:
                if current:
                    yield current[0], current[1], current[2], "\n".join(current[3])
                current = (rel, number, match.group(2), [])
            elif current:
                current[3].append(line)
        if current:
            yield current[0], current[1], current[2], "\n".join(current[3])


def search(terms, repo_root=REPO_ROOT, guides=GUIDES):
    """Sections containing every term (case-insensitive), best first."""
    terms = [t.lower() for t in terms]
    hits = []
    for rel, line, heading, body in sections(repo_root, guides):
        head, text = heading.lower(), body.lower()
        if not all(t in head or t in text for t in terms):
            continue
        score = sum(25 * head.count(t) + min(text.count(t), 10) for t in terms)
        hits.append((score, rel, line, heading, body))
    hits.sort(key=lambda h: (-h[0], h[1], h[2]))
    return hits


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("terms", nargs="*", help="Names or words; a section must contain all of them.")
    parser.add_argument("--show", type=int, metavar="N", help="Print the Nth hit's section in full.")
    parser.add_argument("--limit", type=int, default=15, help="Hits to list (default 15; 0 for all).")
    parser.add_argument("--index", action="store_true", help="List every section heading.")
    args = parser.parse_args(argv)

    if args.index:
        for rel, line, heading, _ in sections():
            print(f"{rel}:{line}: {heading}")
        return 0
    if not args.terms:
        parser.error("give at least one term, or --index")

    hits = search(args.terms)
    if not hits:
        print(f"No section mentions {' and '.join(args.terms)}. Try one term, or a shorter one.")
        return 1
    if args.show:
        if not 1 <= args.show <= len(hits):
            parser.error(f"--show takes 1 to {len(hits)}")
        _, rel, line, heading, body = hits[args.show - 1]
        print(f"{rel}:{line}\n## {heading}\n{body.rstrip()}")
        return 0
    shown = hits if args.limit <= 0 else hits[: args.limit]
    for number, (_, rel, line, heading, _) in enumerate(shown, 1):
        print(f"{number:3}. {heading}\n     {rel}:{line}")
    if len(shown) < len(hits):
        print(f"({len(hits) - len(shown)} more: add a term to narrow, or --limit 0)")
    print(f"\nRead one in full: scripts/lessons.py {' '.join(args.terms)} --show N")
    return 0


if __name__ == "__main__":
    sys.exit(main())
