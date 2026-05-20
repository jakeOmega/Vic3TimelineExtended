#!/usr/bin/env python3
"""One-shot refactor: collapse the repeated #TECH blocks in
common/on_actions/headlines.txt into headlines_tech_announce_effect calls.

Each of the ~166 inner blocks of extra_headlines_tech is byte-for-byte
identical except for the tech id. This script validates that every block
matches the canonical shape (and that all six tech-id occurrences agree),
then rewrites the file as the preamble + one call line per tech + closing
braces. The output is a normal hand-maintained file (no AUTO-GENERATED
header); this script is a re-run convenience, not part of any pipeline.

Aborts without writing if ANY block deviates from the canonical shape or if
the region between the preamble and the closing braces contains anything but
whitespace and matched blocks.

Usage: python3 scripts/generators/refactor_headlines_techs.py [--check]
  --check  validate + report the tech list, write nothing.
"""
import re
import sys
from pathlib import Path

HEADLINES = Path(__file__).resolve().parents[2] / "common/on_actions/headlines.txt"

# Canonical block: comment + the 14-line if-block. \s* between tokens absorbs
# the file's mixed tabs/spaces and the stray trailing space after `limit = {`.
BLOCK = re.compile(
    r"#(?P<c>\S+)\s*"
    r"if\s*=\s*\{\s*"
    r"limit\s*=\s*\{\s*"
    r"has_technology_researched\s*=\s*(?P<t1>\S+)\s*"
    r"NOT\s*=\s*\{\s*"
    r"has_global_variable\s*=\s*headlines_(?P<t2>\S+)_researched\s*"
    r"\}\s*"
    r"\}\s*"
    r"set_global_variable\s*=\s*headlines_(?P<t3>\S+)_researched\s*"
    r"save_scope_as\s*=\s*headlines_(?P<t4>\S+)_researcher\s*"
    r"every_country\s*=\s*\{\s*"
    r"limit\s*=\s*\{\s*"
    r"is_ai\s*=\s*no\s*"
    r"\}\s*"
    r"post_notification\s*=\s*headlines_tech_(?P<t5>\S+)\s*"
    r"\}\s*"
    r"\}"
)


def main():
    check_only = "--check" in sys.argv
    text = HEADLINES.read_text(encoding="utf-8")
    matches = list(BLOCK.finditer(text))
    if not matches:
        sys.exit("ERROR: no canonical blocks matched -- aborting.")

    techs = []
    for m in matches:
        ids = {m.group("c"), m.group("t1"), m.group("t2"),
               m.group("t3"), m.group("t4"), m.group("t5")}
        if len(ids) != 1:
            sys.exit(f"ERROR: tech-id mismatch in block: {ids} -- aborting.")
        techs.append(m.group("c"))

    # Everything between matched blocks (and after the last) must be only
    # whitespace + the two closing braces, or this file isn't what we think.
    for a, b in zip(matches, matches[1:]):
        gap = text[a.end():b.start()]
        if gap.strip():
            sys.exit(f"ERROR: non-whitespace between blocks: {gap!r} -- aborting.")
    footer = text[matches[-1].end():]
    if footer.replace("}", "").strip() or footer.count("}") != 2:
        sys.exit(f"ERROR: unexpected footer {footer!r} -- aborting.")

    preamble = text[:matches[0].start()]
    if "extra_headlines_tech" not in preamble or "headlines_tech_acquired" not in preamble:
        sys.exit("ERROR: preamble missing expected setup -- aborting.")

    if len(set(techs)) != len(techs):
        dupes = {t for t in techs if techs.count(t) > 1}
        sys.exit(f"ERROR: duplicate techs {dupes} -- aborting.")

    print(f"{len(techs)} canonical blocks validated.")
    if check_only:
        for t in techs:
            print(f"  {t}")
        return

    calls = "".join(f"\t\theadlines_tech_announce_effect = {{ TECH = {t} }}\n"
                    for t in techs)
    new_text = preamble.rstrip() + "\n" + calls + "\t}\n}\n"
    HEADLINES.write_text(new_text, encoding="utf-8")
    print(f"Rewrote {HEADLINES} -> {len(new_text.splitlines())} lines.")


if __name__ == "__main__":
    main()
