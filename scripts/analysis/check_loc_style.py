#!/usr/bin/env python3
"""Lint in-game text against docs/guides/loc_style_guide.md, as a ratchet.

    python3 scripts/analysis/check_loc_style.py            # list every finding
    python3 scripts/analysis/check_loc_style.py --check    # fail on a NEW one
    python3 scripts/analysis/check_loc_style.py --update   # rewrite the baseline
    python3 scripts/analysis/check_loc_style.py --key banking_cycle_events.3.d

It checks what a word list can check: stock metaphors, verdict words, the
machine-writing words and phrases the player guide's lint already bans (shared
from check_player_guide_style.py), " - " used as a dash, and a text that ends in
an ellipsis or a line break. The judgment in the guide (is this sentence
particular, could a game make it false, does it end on a kicker) is not here
and cannot be.

The mod's older text has several hundred findings, and rewriting them is its
own work (#1539). So `--check` compares with a baseline,
scripts/analysis/loc_style_baseline.txt, one `rule<TAB>key` per line:

* a finding not in the baseline fails: new text meets the guide;
* a baseline line whose finding is gone fails too, with the fix
  (`--update`), so the baseline only ever shrinks and a fixed line cannot
  quietly regress.

An intended use takes a comment trailing on the loc line:

    my_key:0 "A robust hull." # REVIEWED 2026-11-09 (loc_style): the ship class's name

Scope: localization/english/te_*_l_english.yml, without the generated files,
te_unused and developer test-bench keys. Needs no game and no server.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

from check_player_guide_style import AI_PHRASES, AI_WORDS, _NEG_PARALLEL  # noqa: E402
from mod_state import split_loc_line  # noqa: E402

LOC_DIR = REPO_ROOT / "localization" / "english"
BASELINE = REPO_ROOT / "scripts" / "analysis" / "loc_style_baseline.txt"

# Words the player guide bans that are ordinary in the game's own vocabulary.
GAME_WORDS = {
    r"key", r"realms?", r"journeys?", r"diverse", r"valuable", r"landscapes?", r"enduring",
    # Human enhancement is a subject of the mod's late eras, and of its laws' names.
    r"enhanc(?:e|es|ed|ing|ement)",
}

STOCK_METAPHORS = [
    r"mountains? of", r"a flood of", r"floods? of", r"a wave of", r"a tide of", r"a sea of",
    r"gr(?:inds?|ound|inding) to a (?:near-)?halt", r"plant(?:s|ed|ing)? the seeds?", r"sow(?:s|ed|ing)? the seeds?",
    r"double-edged sword", r"ticking (?:clock|time bomb)", r"shock ?waves?", r"hangs? in the balance",
    r"a new dawn", r"winds? of change", r"tip of the iceberg", r"perfect storm", r"house of cards",
    r"powder keg", r"at a crossroads", r"turning point", r"uncharted (?:waters|territory)",
    r"razor'?s edge", r"knife'?s edge", r"the dust settles?", r"tighten(?:s|ed|ing)? its grip",
    r"fan(?:s|ned|ning)? the flames", r"add(?:s|ed|ing)? fuel to the fire", r"a race against time",
    r"in the blink of an eye", r"only time will tell", r"the stage is set", r"wake-up call",
    r"starv(?:e|es|ed|ing) for", r"lifeblood", r"beating heart", r"the fabric of",
]

VERDICT_WORDS = [
    r"devastating(?:ly)?", r"harrowing", r"staggering(?:ly)?", r"unprecedented", r"sophisticated",
    r"miraculous(?:ly)?", r"fundamentally", r"enormous(?:ly)?", r"immense(?:ly)?", r"catastrophic(?:ally)?",
    r"shocking(?:ly)?", r"stunning(?:ly)?", r"dramatic(?:ally)?", r"remarkabl[ey]", r"incredibl[ey]",
    r"truly", r"utterly", r"deeply", r"vastly",
]


def _alternation(patterns) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(patterns) + r")\b", re.IGNORECASE)


RULES = {
    "stock-metaphor": "a stock metaphor: say the particular thing instead",
    "verdict-word": "a verdict word: give the fact that would make a reader think it",
    "ai-word": "an inflated word (player guide STYLE.md's list): say what the thing does",
    "ai-phrase": "a machine-writing phrase (player guide STYLE.md's list)",
    "neg-parallel": "'not just X but Y': state Y",
    "spaced-hyphen": "' - ' used as a dash: use a comma, a colon or a new sentence",
    "ellipsis-end": "the text ends in an ellipsis (news-headline notifications excepted)",
    "trailing-newline": "the text ends in \\n",
}

_PATTERNS = {
    "stock-metaphor": [_alternation(STOCK_METAPHORS)],
    "verdict-word": [_alternation(VERDICT_WORDS)],
    "ai-word": [_alternation([w for w in AI_WORDS if w not in GAME_WORDS])],
    "ai-phrase": [_alternation(AI_PHRASES)],
    "neg-parallel": list(_NEG_PARALLEL),
    "spaced-hyphen": [re.compile(r"\w - \w")],
    "ellipsis-end": [re.compile(r"(?:\.\.\.|\u2026)\s*(?:#!)?\s*$")],
    "trailing-newline": [re.compile(r"\\n\s*$")],
}

_MARKUP = re.compile(r"\[[^\]]*\]|\$[^$\s]*\$|@\w+!|#[A-Za-z_;:,\[\]().']+\s|#!")
_REVIEWED = re.compile(r"#\s*REVIEWED\s+\d{4}-\d{2}-\d{2}\s*\(loc_style\)\s*:\s*\S")
_SKIP_FILE = re.compile(r"_generated_|te_unused_|te_debug")
_HEADLINE_PREFIX = "notification_headlines_"
_SKIP_KEY = re.compile(r"^(?:te_debug|TE_DEBUG|te_tp_|te_tax_debug)")


def prose(value: str) -> str:
    """The value as a reader sees its words: data functions, spliced keys and
    formatting codes replaced by a neutral token."""
    return _MARKUP.sub(" X ", value)


def lint_value(value: str) -> list:
    """[(rule, matched text)] for one loc value."""
    text = prose(value)
    found = []
    for rule, patterns in _PATTERNS.items():
        # The two end-of-text rules read the raw value: markup stripping would hide a final \n.
        subject = value if rule in ("ellipsis-end", "trailing-newline") else text
        for pattern in patterns:
            match = pattern.search(subject)
            if match:
                found.append((rule, match.group(0).strip()))
                break
    return found


def loc_files(loc_dir=LOC_DIR):
    return sorted(p for p in loc_dir.glob("te_*_l_english.yml") if not _SKIP_FILE.search(p.name))


def scan(loc_dir=LOC_DIR):
    """[(rule, key, matched, file name, line number)], reviewed lines left out."""
    findings = []
    for path in loc_files(loc_dir):
        with open(path, encoding="utf-8-sig") as fh:
            for number, line in enumerate(fh, 1):
                parsed = split_loc_line(line)
                if not parsed:
                    continue
                key, value, trailing = parsed
                if _SKIP_KEY.match(key) or _REVIEWED.search(trailing):
                    continue
                for rule, matched in lint_value(value):
                    if rule == "ellipsis-end" and key.startswith(_HEADLINE_PREFIX):
                        continue  # a news headline trails off, as the base game's do
                    findings.append((rule, key, matched, path.name, number))
    return findings


def read_baseline(path=BASELINE) -> set:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return set()
    return {tuple(line.split("\t", 1)) for line in lines if line and not line.startswith("#")}


def write_baseline(pairs, path=BASELINE) -> None:
    header = (
        "# Findings of scripts/analysis/check_loc_style.py that predate the style guide (2026-11-09).\n"
        "# `--check` fails on a finding that is not here, and on a line here whose finding is gone.\n"
        "# Never add a line by hand: fix the text, or review it on its loc line. `--update` rewrites this file.\n"
    )
    body = "".join(f"{rule}\t{key}\n" for rule, key in sorted(pairs))
    path.write_text(header + body, encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Exit 1 on a finding the baseline lacks, or a stale baseline line.")
    mode.add_argument("--update", action="store_true", help="Rewrite the baseline. It may only shrink, unless --grow.")
    parser.add_argument("--grow", action="store_true", help="With --update: allow new findings into the baseline.")
    parser.add_argument("--key", help="Show the findings for keys containing this text.")
    parser.add_argument("--rule", choices=sorted(RULES), help="Show one rule's findings.")
    args = parser.parse_args(argv)

    findings = scan()
    current = {(rule, key) for rule, key, *_ in findings}
    baseline = read_baseline()

    if args.update:
        new = current - baseline
        if new and not args.grow:
            print(f"{len(new)} finding(s) are not in the baseline; --update only shrinks it. Fix them, or review")
            print("them on their loc lines. (--grow admits them: for a new rule, or a first baseline.)")
            return 1
        write_baseline(current)
        print(f"Baseline: {len(current)} line(s) ({len(baseline - current)} removed, {len(new)} added).")
        return 0

    if args.check:
        fresh = [f for f in findings if (f[0], f[1]) not in baseline]
        stale = sorted(baseline - current)
        for rule, key, matched, name, number in fresh:
            print(f"{name}:{number}: {key}: {rule}: \"{matched}\" ({RULES[rule]})")
        if fresh:
            print(f"\n{len(fresh)} new style finding(s). Rewrite the text (docs/guides/loc_style_guide.md), or if the")
            print("use is intended add on the loc line:  # REVIEWED YYYY-MM-DD (loc_style): why")
        if stale:
            print(f"\n{len(stale)} baseline line(s) no longer match a finding, for example {stale[0][1]} ({stale[0][0]}).")
            print("Run `python3 scripts/analysis/check_loc_style.py --update` and commit the baseline.")
        if fresh or stale:
            return 1
        print(f"OK: no new style findings ({len(current)} older ones in the baseline).")
        return 0

    shown = [f for f in findings
             if (not args.key or args.key in f[1]) and (not args.rule or args.rule == f[0])]
    for rule, key, matched, name, number in shown:
        print(f"{name}:{number}: {key}: {rule}: \"{matched}\"")
    counts = Counter(f[0] for f in shown)
    print()
    for rule in RULES:
        if counts.get(rule):
            print(f"{counts[rule]:5}  {rule}: {RULES[rule]}")
    print(f"{len(shown):5}  total, in {len({f[1] for f in shown})} keys")
    return 0


if __name__ == "__main__":
    sys.exit(main())
