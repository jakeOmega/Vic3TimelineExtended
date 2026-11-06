#!/usr/bin/env python3
"""Write te_journal_map_scales_generated.txt: the Map Room's color scales.

Each map in je_te_map_room (common/journal_entries/te_journal_maps.txt) colors a
state by a factor, 0 to 1, read from one of the state's figures. The factor is a
piecewise-linear curve through a few knots, and every curve here comes from one
of three shapes, so a shape changed below changes every map that uses it:

- linear(lo, hi): straight from lo to hi.
- soft_cap(lo, soft, hard): straight from lo to soft, then SLOPE_RATIO times
  shallower from soft to hard, so the common values get most of the color and
  the extremes still differ instead of all saturating at one bound.
- diverging(lower, mid, upper): 0.5 at mid, each side to its end; a side is a
  bound (straight) or a (soft, hard) pair (the soft cap's shape, mirrored below).

A script value takes no arguments, and a map paint can run no effect, so a
shared shape can't be one script value fed its input (te_sqrt's way, through
var:te_math_in): each map gets its own tree, written here from its table row.
Each reads its figure only inside an `if` on its `has_variable` guards, since a
guard in the same AND doesn't stop a read where the engine also builds a
tooltip (issue #1418). A three-color map also gets _lower (the factor doubled)
and _upper (doubled less 1), one per half; map_color splits on factor < 0.5.

Needs nothing but the repo. Re-run after changing a table; test_journal_map_scales.py
fails CI when the committed file is stale:

    python3 scripts/generators/gen_journal_map_scales.py [--check]
"""
import argparse
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "common", "script_values", "te_journal_map_scales_generated.txt")

# How much shallower a soft cap's tail runs than its main stretch (the owner, 2026-11-06: "1/4 slope above").
SLOPE_RATIO = 4


def linear(lo, hi):
    return [(lo, 0.0), (hi, 1.0)]


def _soft_share(span, tail):
    """The color a soft cap gives its main stretch: span long at slope s, tail long at s / SLOPE_RATIO."""
    return SLOPE_RATIO * span / (SLOPE_RATIO * span + tail)


def soft_cap(lo, soft, hard):
    return [(lo, 0.0), (soft, _soft_share(soft - lo, hard - soft)), (hard, 1.0)]


def _side(mid, end):
    """[(x, p)] from mid outward, p from 0 to 1: end is a bound or a (soft, hard) pair."""
    if isinstance(end, tuple):
        soft, hard = end
        return [(mid, 0.0), (soft, _soft_share(abs(soft - mid), abs(hard - soft))), (hard, 1.0)]
    return [(mid, 0.0), (end, 1.0)]


def diverging(lower, mid, upper):
    below = [(x, 0.5 - 0.5 * p) for x, p in reversed(_side(mid, lower))]
    above = [(x, 0.5 + 0.5 * p) for x, p in _side(mid, upper)[1:]]
    return below + above


# name: te_jmap_<name>_factor. input: what the tree reads (a figure, or a script value of the state's).
# guards: variables the input needs (read only once they exist). three: the map has three colors (_lower, _upper).
SCALES = [
    dict(name="turmoil", input="turmoil", guards=[], three=False, knots=soft_cap(0, 0.2, 1),
         note="Turmoil, the radicals' share: half the color by 20%, the rest to all radical"),
    dict(name="devastation", input="devastation", guards=[], three=False, knots=soft_cap(0, 0.2, 1),
         note="Devastation, a 0-1 share as turmoil is (te_demog_crisis reads it bare): half the color by 20%"),
    dict(name="urban", input="var:te_dg_urban_share", guards=["te_dg_urban_share"], three=False,
         knots=linear(0, 1), note="The urban share, the people not at a rural workplace (the yearly walk's)"),
    dict(name="gini", input="var:te_dg_gini", guards=["te_dg_gini"], three=False, knots=linear(0.3, 0.8),
         note="The state's shown Gini (the yearly walk's, 0.3-1); Britain in 1836 about 0.55"),
    dict(name="wc", input="var:te_dg_wc", guards=["te_dg_wc"], three=True, knots=diverging(0, 50, 100),
         note="Dynastic Wealth, the state's score, split at 50, where its effects turn from dispersed to "
              "concentrated property"),
    dict(name="e0", input="var:te_dg_e0", guards=["te_dg_e0"], three=True, knots=diverging(25, 52.5, 80),
         note="Life expectancy at birth, 25 to 80 years, split at 52.5"),
    dict(name="imr", input="var:te_dg_imr", guards=["te_dg_imr"], three=True, knots=diverging(0, 50, (300, 500)),
         note="Infant mortality per 1,000 births, split at 50 (the transition's end); 300 an 1836 state's worst"),
    dict(name="tfr", input="var:te_dg_tfr", guards=["te_dg_tfr"], three=True, knots=diverging(1, 2.1, 6.5),
         note="Fertility, children a woman, split at replacement (2.1)"),
    dict(name="median", input="var:te_dg_median", guards=["te_dg_median"], three=True,
         knots=diverging(15, 30, 45), note="Median age, 15 to 45 years, split at 30"),
    dict(name="natural", input="te_demog_natural_change", guards=["te_dg_cbr", "te_dg_cdr"], three=True,
         knots=diverging((-15, -40), 0, (30, 45)),
         note="Natural change per 1,000 people last year, split at none; famine and war run past -15"),
    dict(name="cdr", input="var:te_dg_cdr", guards=["te_dg_cdr"], three=False, knots=soft_cap(5, 40, 100),
         note="Deaths per 1,000 people last year; famine and war run past 40"),
    dict(name="cbr", input="var:te_dg_cbr", guards=["te_dg_cbr"], three=False, knots=linear(8, 50),
         note="Births per 1,000 people last year"),
    dict(name="old", input="var:te_dg_old_share", guards=["te_dg_old_share"], three=False,
         knots=linear(0.02, 0.3), note="The share aged 65 and over (an 1836 state 3-5%, the oldest today near 30%)"),
    dict(name="sex", input="var:te_dg_sex_balance", guards=["te_dg_sex_balance"], three=True,
         knots=diverging(80, 100, 130),
         note="Sex balance, men per 100 women aged 20-59, split at 100: the census's own bounds for its effects"),
    dict(name="mig", input="var:te_dg_mig_rate", guards=["te_dg_mig_rate"], three=True,
         knots=diverging((-20, -60), 0, (20, 60)), note="Net migration per 1,000 people last year, split at none"),
]


def num(x):
    """A literal as the engine reads it: five decimals, no trailing zeros."""
    s = f"{x:.5f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def segments(knots):
    """(start, end, value at start, slope's divisor) per segment."""
    return [(a, b, fa, (b - a) / (fb - fa)) for (a, fa), (b, fb) in zip(knots, knots[1:])]


def _leaf(inp, seg):
    a, _b, fa, div = seg
    ops = [f"value = {inp}"]
    if a > 0:
        ops.append(f"subtract = {num(a)}")
    elif a < 0:
        ops.append(f"add = {num(-a)}")
    if num(div) != "1":
        ops.append(f"divide = {num(div)}")
    if fa:
        ops.append(f"add = {num(fa)}")
    return " ".join(ops)


def factor(scale):
    """te_jmap_<name>_factor's lines: one segment per stretch between knots, the first carried on below the
    first knot and the last past the last, both then clamped to 0-1 (each knot's ends are 0 and 1)."""
    inp, segs = scale["input"], segments(scale["knots"])
    if len(segs) == 1:
        body = [_leaf(inp, segs[0])]
    else:
        body = []
        for i, seg in enumerate(segs):
            if i == len(segs) - 1:
                body.append("else = {")
            else:
                body.append("else_if = {" if i else "if = {")
                body.append(f"\tlimit = {{ {inp} < {num(seg[1])} }}")
            body.append("\t" + _leaf(inp, seg))
            body.append("}")
    if scale["guards"]:
        guards = " ".join(f"has_variable = {g}" for g in scale["guards"])
        body = ["value = 0", "if = {", f"\tlimit = {{ {guards} }}"] + ["\t" + ln for ln in body] + ["}"]
    lines = [f"te_jmap_{scale['name']}_factor = {{"] + ["\t" + ln for ln in body]
    lines += ["\tmin = 0", "\tmax = 1", "}"]
    return lines


def render():
    lines = [
        "# AUTO-GENERATED by scripts/generators/gen_journal_map_scales.py — do not edit manually.",
        "# The Map Room's color scales (common/journal_entries/te_journal_maps.txt): each map's factor, 0-1, a",
        "# piecewise-linear curve through the knots its table row gives, from one of three shapes (linear, soft cap,",
        "# diverging). Change a shape or a row in the generator and re-run it; test_journal_map_scales.py fails when",
        "# this file is stale. Every value here runs with a STATE as root, once per state as the map paints.",
    ]
    for scale in SCALES:
        knots = ", ".join(f"{num(x)} -> {num(y)}" for x, y in scale["knots"])
        lines += ["", f"# {scale['note']}.", f"# Knots: {knots}."]
        lines += factor(scale)
        if scale["three"]:
            name = f"te_jmap_{scale['name']}_factor"
            lines += [f"{name}_lower = {{", f"\tvalue = {name}", "\tmultiply = 2", "\tmin = 0", "\tmax = 1", "}"]
            lines += [f"{name}_upper = {{", f"\tvalue = {name}", "\tmultiply = 2", "\tsubtract = 1", "\tmin = 0",
                      "\tmax = 1", "}"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 when the committed file is stale; write nothing")
    args = parser.parse_args()
    text = render()
    rel = os.path.relpath(OUT, REPO)
    if args.check:
        try:
            with open(OUT, encoding="utf-8-sig") as f:
                current = f.read()
        except FileNotFoundError:
            current = None
        if current != text:
            print(f"{rel} is stale: run scripts/generators/gen_journal_map_scales.py")
            return 1
        print(f"{rel} is current")
        return 0
    with open(OUT, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write(text)
    print(f"wrote {len(SCALES)} map scales to {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
