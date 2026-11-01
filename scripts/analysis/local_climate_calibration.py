#!/usr/bin/env python3
"""Local Climate's calibration: the comfort formula in Python, against the anchor regions.

The Local Climate design (docs/superpowers/specs/2026-11-01-local-climate-design.md § 5.3) asks for
an evidence table before any constant is final: each anchor region's penalty in 1836 and at eras 4,
7, 10 and 13. This reads the relief carriers from the technology files (relief_schedule) and the
record from scripts/generators/data/local_climate.csv. test_local_climate_comfort.py pins the
anchors' targets.

    python3 scripts/analysis/local_climate_calibration.py
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TECH = os.path.join(REPO, "common", "technology", "technologies")
VANILLA_TECH = os.path.join(REPO, "vanilla_parsed", "common", "technologies.json")
KINDS = ("heat", "cold", "water", "disease")

TOP_RE = re.compile(r"(?m)^(INJECT:|REPLACE:)?(\w+) = \{")
RELIEF_RE = re.compile(r"state_climate_(heat|cold|water|disease)_relief_add\s*=\s*(-?[\d.]+)")
# Malaria Prevention's relief is the census's Malaria Control, which the comfort formula adds to the
# disease relief (te_climate_relief_disease, local_climate_values.txt).
CONTROL_RE = re.compile(r"state_malaria_control_add\s*=\s*(-?[\d.]+)")
ERA_RE = re.compile(r"(?m)^\s*era\s*=\s*era_(\d+)")


def _blocks(text):
    """(directive, key, body) for each top-level block, braces balanced, comments skipped."""
    for m in TOP_RE.finditer(text):
        depth, i = 1, m.end()
        while depth and i < len(text):
            c = text[i]
            if c == "#":
                i = text.find("\n", i)
                if i < 0:
                    break
                continue
            depth += {"{": 1, "}": -1}.get(c, 0)
            i += 1
        yield m.group(1) or "", m.group(2), text[m.end():i - 1]


def _tech_texts(repo):
    folder = os.path.join(repo, "common", "technology", "technologies")
    for name in sorted(os.listdir(folder)):
        if name.endswith(".txt"):
            with open(os.path.join(folder, name), encoding="utf-8-sig") as f:
                yield name, f.read()


def tech_eras(repo=REPO):
    """Technology key -> era number: the mod's bare definitions, then vanilla's for the rest."""
    eras = {}
    with open(os.path.join(repo, "vanilla_parsed", "common", "technologies.json"), encoding="utf-8") as f:
        for key, value in json.load(f).items():
            try:
                eras[key] = int(value[1]["era"][1].removeprefix("era_"))
            except (KeyError, TypeError, ValueError, IndexError):
                continue
    for _, text in _tech_texts(repo):
        for directive, key, body in _blocks(text):
            m = ERA_RE.search(body)
            if m and directive in ("", "REPLACE:"):
                eras[key] = int(m.group(1))
    return eras


def relief_schedule(repo=REPO):
    """Kind -> [(era, technology, amount)], sorted by era, from every carrier line in the tech files."""
    eras = tech_eras(repo)
    schedule = {kind: [] for kind in KINDS}
    for name, text in _tech_texts(repo):
        for _, key, body in _blocks(text):
            found = RELIEF_RE.findall(body) + [("disease", a) for a in CONTROL_RE.findall(body)]
            for kind, amount in found:
                if key not in eras:
                    raise ValueError(f"{name}: {key} carries {kind} relief but has no era")
                schedule[kind].append((eras[key], key, float(amount)))
    for kind in KINDS:
        schedule[kind].sort()
    return schedule


def relief_at(schedule, kind, era):
    """The relief a country holding every carrier up to `era` has, clamped to [0, 1]. Era 1 is 1836."""
    return max(0.0, min(1.0, sum(amount for e, _, amount in schedule[kind] if e <= era)))


def main():
    schedule = relief_schedule()
    print("era  " + "  ".join(f"{k:>7}" for k in KINDS))
    for era in range(1, 14):
        print(f"{era:>3}  " + "  ".join(f"{relief_at(schedule, k, era):7.2f}" for k in KINDS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
