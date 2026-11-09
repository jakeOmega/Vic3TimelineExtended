#!/usr/bin/env python3
"""Count the forms a chain's event flavor texts take.

    python3 scripts/analysis/flavor_forms.py                  # every namespace
    python3 scripts/analysis/flavor_forms.py banking_cycle_events
    python3 scripts/analysis/flavor_forms.py banking_cycle_events --list

Flavor text (`<namespace>.<n>.f*` in te_events_l_english.yml) is where sameness
shows most: read in a row, a chain whose every event is two unnamed voices
trading lines is one text. `docs/guides/loc_style_guide.md` § "Flavor text:
vary the form" asks that no form take more than a third of a chain. Run this
before adding to a chain and write in a form it is short of.

The classes are read from the text's shape, so they are approximate:

  exchange    two or more paragraphs, nearly all of them quoted speech
  one voice   a single quoted paragraph, or one speaker throughout
  quotation   ends in an attribution line (`— Name`)
  scene       narration with some speech in it
  narration   no speech at all (a scene without speech, a document, a list)

`--check` is the ratchet CI runs. scripts/analysis/flavor_forms_baseline.json
records, for each chain of six or more texts, how many texts it had in any form
that was over a third of it when the guide was adopted. A form over a third of
its chain takes no new texts: the check fails when that count rises, or when a
form newly passes a third. `--update` re-records the counts after a rewrite,
and only lowers them unless `--grow` is given.

`--list` prints each key with its class, and marks a short last paragraph
(twelve words or fewer after a longer text), the usual shape of a closing line
built to land.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOC_FILE = os.path.join("localization", "english", "te_events_l_english.yml")

BASELINE = os.path.join("scripts", "analysis", "flavor_forms_baseline.json")
MIN_CHAIN = 6

FLAVOR_KEY = re.compile(r'^\s*((?P<ns>[\w\-]+)\.\d+\.f\w*):\d*\s*"(?P<text>.*)"\s*(?:#.*)?$')
FORMS = ("exchange", "one voice", "quotation", "scene", "narration")
SHARE_LIMIT = 1 / 3
QUOTE_OPENERS = ('\\"', "'", "\u201c", "\u2018")


def paragraphs(text: str) -> list:
    return [p.strip() for p in text.split("\\n\\n") if p.strip()]


def classify(text: str) -> str:
    paras = paragraphs(text)
    if not paras:
        return "narration"
    if paras[-1].startswith(("\u2014", "--")) or re.search(r"\\n\u2014 ", text):
        return "quotation"
    quoted = [p for p in paras if p.startswith(QUOTE_OPENERS)]
    has_speech = '\\"' in text or bool(re.search(r"(^|\s)'\w", text))
    if len(paras) == 1:
        return "one voice" if quoted else ("scene" if has_speech else "narration")
    if len(quoted) >= 0.75 * len(paras):
        return "exchange"
    return "scene" if has_speech else "narration"


def short_last_paragraph(text: str) -> bool:
    paras = [p for p in paragraphs(text) if not p.startswith("\u2014")]
    return len(paras) >= 2 and len(paras[-1].split()) <= 12


def load(repo_root=REPO_ROOT):
    """{namespace: [(key, text), ...]} for every flavor key."""
    chains = defaultdict(list)
    with open(os.path.join(repo_root, LOC_FILE), encoding="utf-8-sig") as fh:
        for line in fh:
            match = FLAVOR_KEY.match(line)
            if match:
                chains[match.group("ns")].append((match.group(1), match.group("text")))
    return chains


def summarize(entries):
    counts = Counter(classify(text) for _, text in entries)
    short = sum(short_last_paragraph(text) for _, text in entries)
    return counts, short


def row(name, entries):
    counts, short = summarize(entries)
    total = len(entries)
    cells = "".join(f"{counts.get(form, 0):>10}" for form in FORMS)
    top, top_n = counts.most_common(1)[0]
    over = f"  <- {top} is {100 * top_n // total}%" if total >= 6 and top_n / total > SHARE_LIMIT else ""
    return f"{name:32}{total:>6}{cells}{short:>12}{over}"


def over_counts(chains) -> dict:
    """{namespace: {form: count}} for every form over the limit in a chain of
    MIN_CHAIN texts or more."""
    out = {}
    for name, entries in chains.items():
        if len(entries) < MIN_CHAIN or name.startswith("te_debug"):
            continue
        counts, _ = summarize(entries)
        over = {form: n for form, n in counts.items() if n / len(entries) > SHARE_LIMIT}
        if over:
            out[name] = over
    return out


def read_baseline(repo_root=REPO_ROOT) -> dict:
    try:
        with open(os.path.join(repo_root, BASELINE), encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


def check(chains, baseline) -> list:
    """Messages for every chain with more texts in an over-used form than recorded."""
    problems = []
    for name, over in sorted(over_counts(chains).items()):
        total = len(chains[name])
        for form, count in sorted(over.items()):
            allowed = baseline.get(name, {}).get(form, 0)
            if count > allowed:
                was = f"{allowed} recorded" if allowed else "it was under a third before"
                problems.append(
                    f"{name}: {count} of {total} flavor texts are {form} ({was}). "
                    f"A form over a third of its chain takes no new texts: write this one in another form."
                )
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("namespaces", nargs="*", help="Event namespaces (default: all).")
    parser.add_argument("--list", action="store_true", help="Print each key with its class.")
    parser.add_argument("--check", action="store_true", help="Exit 1 if an over-used form gained a text.")
    parser.add_argument("--update", action="store_true", help="Re-record the counts (they only fall, unless --grow).")
    parser.add_argument("--grow", action="store_true", help="With --update: let a count rise.")
    args = parser.parse_args(argv)

    chains = load()
    if args.check or args.update:
        baseline = read_baseline()
        problems = check(chains, baseline)
        if args.update:
            if problems and not args.grow:
                print("\n".join(problems))
                print("--update only lowers counts. Vary the forms, or pass --grow to accept the rise.")
                return 1
            current = over_counts(chains)
            with open(os.path.join(REPO_ROOT, BASELINE), "w", encoding="utf-8", newline="\n") as fh:
                json.dump(current, fh, indent=1, sort_keys=True)
                fh.write("\n")
            print(f"Recorded counts for {len(current)} chain(s) in {BASELINE}.")
            return 0
        if problems:
            print("\n".join(problems))
            print("\nForms and how to choose one: docs/guides/loc_style_guide.md, \"Flavor text: vary the form\".")
            return 1
        current = over_counts(chains)
        loose = sum(
            1 for name, forms in baseline.items() for form, allowed in forms.items()
            if current.get(name, {}).get(form, 0) < allowed
        )
        note = f" {loose} recorded count(s) can come down: run --update." if loose else ""
        print(f"OK: no chain's dominant form has grown.{note}")
        return 0

    unknown = [n for n in args.namespaces if n not in chains]
    if unknown:
        print(f"No flavor keys under: {', '.join(unknown)}", file=sys.stderr)
        return 1
    names = args.namespaces or sorted(chains, key=lambda n: -len(chains[n]))

    if args.list:
        for name in names:
            for key, text in chains[name]:
                mark = "  (short last paragraph)" if short_last_paragraph(text) else ""
                print(f"{classify(text):10} {key}{mark}")
        return 0

    header = "".join(f"{form:>10}" for form in FORMS)
    print(f"{'namespace':32}{'texts':>6}{header}{'short last':>12}")
    for name in names:
        print(row(name, chains[name]))
    if not args.namespaces:
        everything = [entry for name in names for entry in chains[name]]
        print(row("ALL", everything))
    print("\nA form over a third of a chain of six or more is marked. Write the next one in another form.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
