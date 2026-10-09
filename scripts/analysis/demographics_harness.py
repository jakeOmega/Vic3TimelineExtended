#!/usr/bin/env python3
"""Offline harness for the demographics model (spec §11.1, §12 phase 0).

Usage:
    demographics_harness.py sketch                      # §2.2/§2.3's cases from the model
    demographics_harness.py inputs SAVE [--tag GBR]     # per-country inputs read from a save
    demographics_harness.py gini SAVE [--anchor-tag GBR --anchor 0.52]
    demographics_harness.py seed SAVE --tag GBR         # the seeded structure and life figures
    demographics_harness.py natural-change OLD NEW      # §14 Q10: world change vs the SoL curves
    demographics_harness.py replay DEBUG_LOG            # an in-game step against the model

SAVE is a plain-text save (debug mode). The model is demographics_model.py with
demographics_params.py; the generator writes the script from the same two files, so a
parameter tuned here reaches the game by `python3 scripts/generators/gen_demographics.py`.

Calibration to world history (§2.3's targets) is not here yet: it needs an observer
run's yearly saves and belongs to phase 2's plan.
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_save_inputs as S  # noqa: E402
import pop_growth as G  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BUY_PACKAGES = ROOT / "common" / "buy_packages" / "00_buy_packages.txt"

SKETCH = {
    "1836 agrarian (reference)": M.Inputs(sol=8, literacy=0.2, urban_share=0.1),
    "Britain 1836": M.Inputs(sol=11, literacy=0.35, urban_share=0.3, laws=frozenset({"law_no_womens_rights"})),
    "France 1836 (Family Limitation)": M.Inputs(sol=11, literacy=0.3, urban_share=0.15,
                                                means_add=P.FAMILY_LIMITATION_MEANS),
}


def buy_package_costs(path=BUY_PACKAGES):
    """{wealth: weekly spending per 10,000 working adults} from the committed buy packages."""
    text = Path(path).read_text(encoding="utf-8-sig")
    out = {}
    for m in re.finditer(r"^wealth_(\d+) = \{(.*?)^\}", text, re.S | re.M):
        goods = re.search(r"goods = \{[^\n]*\n(.*?)\n\t\}", m.group(2), re.S)
        out[int(m.group(1))] = sum(float(v) for v in re.findall(r"= ([0-9.]+)", goods.group(1)))
    return out


def income_proxy(wealth, costs):
    w = min(max(int(wealth), 1), P.INCOME_WEALTH_CAP)
    return costs[w]


def inputs_for(c):
    """Model inputs for a save's country (no institutions: the reader doesn't read them)."""
    return M.Inputs(sol=c.sol, literacy=c.literacy, urban_share=c.urban_share,
                    techs=frozenset(c.techs), laws=frozenset(c.laws))


def cmd_sketch(_args):
    for label, inp in SKETCH.items():
        ring, last = M.run_constant(inp, years=300)
        s = M.structure(ring)
        print(f"{label:28s} TFR {last['tfr']:.2f}  e0 {last['e0']:.1f}  e65 {last['e65']:.1f}  "
              f"IMR {last['q0_per_1000']:.0f}  0-14 {s['young']:.0%}  15-64 {s['working']:.0%}  "
              f"65+ {s['old']:.1%}  growth {last['growth']:+.2%}")
    return 0


def country_groups(sections, tag, costs):
    """[(people, income)] by strata for one country, from raw pop records."""
    tags = {cid: r.get("definition", "").strip('"') for cid, r in sections["country_manager"].items()}
    owner = {sid: r.get("country") for sid, r in sections["states"].items()}
    acc = {}
    for r in sections["pops"].values():
        if tags.get(owner.get(r.get("location"))) != tag:
            continue
        size = S._num(r.get("workforce")) + S._num(r.get("dependents"))
        if size <= 0:
            continue
        strata = S.STRATA_OF_CLASS.get(r.get("social_class"), "lower")
        n, y = acc.get(strata, (0.0, 0.0))
        acc[strata] = (n + size, y + size * income_proxy(S._num(r.get("wealth"), 1), costs))
    return list(acc.values())


def cmd_gini(args):
    sections = S.read_sections(args.save)
    costs = buy_package_costs()
    inputs = S.country_inputs(sections)
    tags = args.tag or sorted(inputs, key=lambda t: -inputs[t].population)[:15]
    grouped = {t: M.grouped_gini(country_groups(sections, t, costs)) for t in set(tags) | {args.anchor_tag}}
    anchor = grouped[args.anchor_tag]
    scale = (args.anchor - P.GINI_FLOOR) / anchor if anchor else 0.0
    print(f"GINI_SCALE for {args.anchor_tag} = {args.anchor}: {scale:.2f} (params: {P.GINI_SCALE})")
    for t in tags:
        shown = M.clamp(P.GINI_FLOOR + scale * grouped[t], 0, 0.9)
        print(f"{t} grouped {grouped[t]:.3f} shown {shown:.2f}")
    return 0


def cmd_inputs(args):
    return S.main(["summary", args.save] + [x for t in args.tag for x in ("--tag", t)])


def cmd_seed(args):
    c = S.country_inputs(S.read_sections(args.save)).get(args.tag)
    if c is None:
        print(f"no country {args.tag}", file=sys.stderr)
        return 1
    inp = inputs_for(c)
    ring = M.seed(inp, 1836, c.population)
    qf, qm, _ = M.group_rates(inp)
    f, m = M.life_table(qf), M.life_table(qm)
    fert = M.fertility(inp, (f["e0"] + m["e0"]) / 2)
    s = M.structure(ring)
    print(f"{args.tag}: pop {c.population:,.0f} SoL {c.sol:.1f} literacy {c.literacy:.2f} urban {c.urban_share:.2f}")
    print(f"  TFR {fert['tfr']:.2f} (wealth {fert['wealth']:.2f} x factor {fert['factor']:.2f}; means {fert['means']:.2f})")
    print(f"  e0 women {f['e0']:.1f} men {m['e0']:.1f}; IMR {(qf[0] + qm[0]) / 200:.0f} per 1000")
    print(f"  0-14 {s['young']:.0%} 15-64 {s['working']:.0%} 65+ {s['old']:.1%} median {s['median']:.1f}")
    return 0


def cmd_natural_change(args):
    """World population change between two saves against the defines' curves (no modifiers)."""
    d = G.read_defines()
    old, new = S.read_sections(args.old, ("pops",)), S.read_sections(args.new, ("pops",))
    total_old = total_new = expected = 0.0
    for r in old["pops"].values():
        size = S._num(r.get("workforce")) + S._num(r.get("dependents"))
        sol = S._num(r.get("previous_quality_of_life"))
        total_old += size
        expected += size * (G.monthly_birthrate(sol, d) - G.monthly_mortality(sol, d))
    for r in new["pops"].values():
        total_new += S._num(r.get("workforce")) + S._num(r.get("dependents"))
    months = args.months
    print(f"world {total_old:,.0f} -> {total_new:,.0f}: change {total_new - total_old:+,.0f} over {months} month(s)")
    print(f"expected from the curves without modifiers: {expected * months:+,.0f} "
          f"(ratio {((total_new - total_old) / (expected * months)) if expected else 0:.2f})")
    return 0


_REPLAY = re.compile(r"TE_DEMOG_REPLAY (\w+) (.*)$")
HEAD_PEOPLE = ("pop_last", "pop", "war", "kills", "mig")
HEAD_RATES = ("tfr", "mmr", "m_inf", "m_ext", "m_chr", "m_work_f", "m_work_m")


def _fmt(x):
    return f"{x:.5f}".rstrip("0").rstrip(".") if x else "0"


def _grouped(x):
    """millions_thousands_units, as the debug log prints a large number (the probe's form)."""
    sign = "-" if x < 0 else ""
    n = int(round(abs(x)))
    return f"{sign}{n // 1_000_000}_{n // 1000 % 1000}_{n % 1000}"


def _group_part(text):
    """One group of a grouped number: an int, or a float when the units part carries a fraction."""
    if not text:
        return 0
    return float(text) if "." in text else int(text)


def _ungroup(text):
    """The number a grouped one stands for; a fractional units part (`0_0_500.5`) is kept."""
    sign = -1 if text.startswith("-") else 1
    parts = [_group_part(p) for p in text.lstrip("-").split("_")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return sign * (parts[0] * 1_000_000 + parts[1] * 1000 + parts[2])


def _per_mille(ring):
    total = ring.people() or 1.0
    k = 1000.0 * ring.scale / total
    return [x * k for x in ring.f], [x * k for x in ring.m], (ring.pool_f * k, ring.pool_m * k)


def format_replay(state, year, ring_before, head, ring_after):
    """The TE_DEMOG_REPLAY lines one in-game step logs (te_debug_demog.1 option a).

    The debug log abbreviates numbers of 1,000 and more, so people counts print as
    millions_thousands_units groups and every slot as per mille of the state's people.
    head: pop (engine, now), war, kills, mig (signed), tfr, mmr, m_inf, m_ext, m_chr,
    m_work_f, m_work_m, profile (10 shares: classes 0-4 women, then men). pop_last is the
    ring's people before the step. Then fifteen `before` and fifteen `after` lines of ten
    slots each; the slot-0 line also carries the pool and its mean age.
    """
    n = len(P.MIGRANT_CLASSES)
    h = dict(head, pop_last=ring_before.people())
    prof = ",".join(_fmt(head["profile"][(c, s)]) for s in ("f", "m") for c in range(n))
    lines = [f"TE_DEMOG_REPLAY head state={state} year={year} "
             + " ".join(f"{k}={_grouped(h[k])}" for k in HEAD_PEOPLE) + " "
             + " ".join(f"{k}={_fmt(h[k])}" for k in HEAD_RATES) + f" profile={prof}"]
    for when, ring in (("before", ring_before), ("after", ring_after)):
        f, m, (pf, pm) = _per_mille(ring)
        for first in range(0, P.RING_YEARS, 10):
            extra = f" pool_f={_fmt(pf)} pool_m={_fmt(pm)} pool_age={_fmt(ring.pool_age)}" if first == 0 else ""
            lines.append(f"TE_DEMOG_REPLAY {when} from={first} f={','.join(_fmt(x) for x in f[first:first + 10])}"
                         f" m={','.join(_fmt(x) for x in m[first:first + 10])}{extra}")
    return lines


def parse_replay(lines):
    """[{'head': {...}, 'before': {...}, 'after': {...}, 'errors': [...]}] from TE_DEMOG_REPLAY lines.

    A line that can't be read doesn't stop the parse: it is noted in the block's `errors`,
    and check_block reports the block as malformed.
    """
    blocks, cur = [], None
    for line in lines:
        hit = _REPLAY.search(line)
        if not hit:
            continue
        kind, rest = hit.group(1), hit.group(2)
        fields = dict(kv.split("=", 1) for kv in rest.split() if "=" in kv)
        if kind == "head":
            cur = {"head": fields, "before": {"f": {}, "m": {}}, "after": {"f": {}, "m": {}}, "errors": []}
            blocks.append(cur)
        elif cur is not None and kind in ("before", "after"):
            try:
                first = int(fields["from"])
                for sex in ("f", "m"):
                    for i, v in enumerate(fields[sex].split(",")):
                        cur[kind][sex][first + i] = float(v or 0)
                if "pool_f" in fields:
                    cur[kind]["pool"] = (float(fields["pool_f"] or 0), float(fields["pool_m"] or 0),
                                         float(fields["pool_age"] or 150))
            except (KeyError, ValueError) as e:
                cur["errors"].append(f"unreadable {kind} line (from={fields.get('from', '?')}): {type(e).__name__} {e}")
    return blocks


def check_block(b):
    """None for a block replay_block can run; otherwise why not, as `malformed: …` or `incomplete: …`.

    A complete block has every head field, all RING_YEARS slots of each sex in both `before`
    and `after`, and the pool (slot-0 line) in both. replay_block compares only the slots it
    is given, so without this a log cut short would pass.
    """
    if b.get("errors"):
        return "malformed: " + b["errors"][0]
    h = b["head"]
    missing = [k for k in ("year",) + HEAD_PEOPLE + HEAD_RATES + ("profile",) if k not in h]
    if missing:
        return "malformed: head lacks " + ", ".join(missing)
    try:
        int(h["year"])
        for k in HEAD_PEOPLE:
            _ungroup(h[k])
        for k in HEAD_RATES:
            float(h[k])
        shares = [float(x) for x in h["profile"].split(",")]
    except ValueError as e:
        return f"malformed: head value unreadable ({e})"
    want = 2 * len(P.MIGRANT_CLASSES)
    if len(shares) != want:
        return f"malformed: profile has {len(shares)} shares, expected {want}"
    gaps = []
    for when in ("before", "after"):
        for sex, who in (("f", "women"), ("m", "men")):
            slots = b[when][sex]
            if any(not 0 <= k < P.RING_YEARS for k in slots):
                return f"malformed: {when} {who} has a slot outside 0-{P.RING_YEARS - 1}"
            if len(slots) < P.RING_YEARS:
                gaps.append(f"{when} {who} {len(slots)} of {P.RING_YEARS} slots")
        if "pool" not in b[when]:
            gaps.append(f"{when} pool missing")
    return "incomplete: " + "; ".join(gaps) if gaps else None


def replay_block(b):
    """Step the model from a logged before-state; the worst relative error over slots above 0.05 per mille."""
    h = b["head"]
    year = int(h["year"])
    pop_last = _ungroup(h["pop_last"])
    ring = M.Ring(year=year - 1)
    for k in range(P.RING_YEARS):
        ring.f[k] = b["before"]["f"].get(k, 0.0) * pop_last / 1000.0
        ring.m[k] = b["before"]["m"].get(k, 0.0) * pop_last / 1000.0
    pf, pm, page = b["before"].get("pool", (0.0, 0.0, 150.0))
    ring.pool_f, ring.pool_m, ring.pool_age = pf * pop_last / 1000.0, pm * pop_last / 1000.0, page
    M._refresh_denominators(ring)
    ring.total = ring.people()
    mult = {"infection": float(h["m_inf"]), "external": float(h["m_ext"]), "chronic": float(h["m_chr"])}
    qf, qm = M.rates_from_multipliers(mult, float(h["m_work_f"]), float(h["m_work_m"]))
    shares = [float(x) for x in h["profile"].split(",")]
    n = len(P.MIGRANT_CLASSES)
    prof = {(c, "f"): shares[c] for c in range(n)} | {(c, "m"): shares[n + c] for c in range(n)}
    M.step(ring, M.Inputs(), year, engine_pop=_ungroup(h["pop"]), war_dead=_ungroup(h["war"]),
           kills=_ungroup(h["kills"]), migration=_ungroup(h["mig"]),
           rates=(qf, qm, float(h["mmr"]), float(h["tfr"]), prof))
    mine_f, mine_m, _pool = _per_mille(ring)
    worst = 0.0
    for sex, mine in (("f", mine_f), ("m", mine_m)):
        for k, logged in b["after"][sex].items():
            if max(mine[k], logged) > 0.05:
                worst = max(worst, abs(mine[k] - logged) / max(mine[k], logged))
    return worst


def cmd_replay(args):
    lines = Path(args.log).read_text(encoding="utf-8", errors="replace").splitlines()
    blocks = parse_replay(lines)
    if not blocks:
        print("no TE_DEMOG_REPLAY blocks", file=sys.stderr)
        return 1
    bad = 0
    for b in blocks:
        label = f"{b['head'].get('state', '?')} {b['head'].get('year', '?')}"
        problem, worst = check_block(b), 0.0
        if problem is None:
            try:
                worst = replay_block(b)
            except (ArithmeticError, KeyError, IndexError, TypeError, ValueError) as e:
                problem = f"malformed: {type(e).__name__} {e}"
        if problem:
            bad += 1
            print(f"{label}: MISMATCH ({problem})")
            continue
        flag = "OK" if worst <= args.tolerance else "MISMATCH"
        bad += flag != "OK"
        print(f"{label}: worst slot error {worst:.2%} {flag}")
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sketch").set_defaults(fn=cmd_sketch)
    p = sub.add_parser("inputs")
    p.add_argument("save")
    p.add_argument("--tag", action="append", default=[])
    p.set_defaults(fn=cmd_inputs)
    p = sub.add_parser("gini")
    p.add_argument("save")
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--anchor-tag", default="GBR")
    p.add_argument("--anchor", type=float, default=0.52)
    p.set_defaults(fn=cmd_gini)
    p = sub.add_parser("seed")
    p.add_argument("save")
    p.add_argument("--tag", required=True)
    p.set_defaults(fn=cmd_seed)
    p = sub.add_parser("natural-change")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--months", type=int, default=1)
    p.set_defaults(fn=cmd_natural_change)
    p = sub.add_parser("replay")
    p.add_argument("log")
    p.add_argument("--tolerance", type=float, default=0.01)
    p.set_defaults(fn=cmd_replay)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
