#!/usr/bin/env python3
"""Read the growth probe's TE_PG lines (branch probe/demographics-growth) and fit the engine's births and deaths.

    demographics_growth_probe.py check  LOG [LOG ...]   # mid-run health: ticks, groups, phases, both-off, daily lines
    demographics_growth_probe.py report LOG [LOG ...]   # per-country fits (noisy: see below)
    demographics_growth_probe.py pooled LOG [LOG ...]   # one fit over all countries and windows
    demographics_growth_probe.py deaths --version 3 LOG [LOG ...]   # v3: do the mortality reads close the gap?

LOG may be any mix of debug.log generations and archived copies; identical lines are read once. Only
v=2 lines are read (the 28-day schedule); the first run's 30-day lines carry no v and are skipped.

The probe (common/scripted_effects/te_debug_growth_effects.txt) logs every probe country every 28 days
(four of the engine's weekly growth days, so each window holds whole batch cycles).
A line's ph= is the phase that ran in the 30 days before it, so the window from tick t-1 to t belongs to
ph(t). The schedule switches at ticks 0, 3, 6 ...: phase = cycle x 8 + (block + group) mod 8, where
block = (t - 1) // 3 and cycle = block // 8. The first window after a switch is a transition and is
not measured.

Model under test, per country and 28-day window (eb, ed: the curves' births and deaths a month, no modifiers):
    births = s_b x (1 + M_b + X)     deaths = s_d x (1 + M_d + Y)
X and Y are the probe's steps. s_b / eb and s_d / ed should be 1; M_b less the state read mb is what the
census misses (per-pop terms: literacy, starvation ...), and is regressed on the logged shares.
"""
import argparse
import collections
import re
import statistics as st
import sys

PHASE_NAMES = {
    0: "none", 1: "births off", 2: "deaths off", 3: "both off",
    4: "deaths off, births +0.5", 5: "deaths off, births +1.0",
    6: "births off, deaths +0.5", 7: "births off, deaths +1.0",
    8: "none", 9: "births off", 10: "deaths off", 11: "both off",
    12: "deaths off, births -0.5", 13: "deaths off, births -0.9",
    14: "births off, deaths -0.5", 15: "births off, deaths -0.9",
}
BIRTH_STEP = {2: 0.0, 10: 0.0, 4: 0.5, 5: 1.0, 12: -0.5, 13: -0.9}   # deaths off: change = births
DEATH_STEP = {1: 0.0, 9: 0.0, 6: 0.5, 7: 1.0, 14: -0.5, 15: -0.9}   # births off: change = -deaths
SLOPE_X = (0.0, 0.5, 1.0)   # the steps the slopes are fitted from; -0.5 and -0.9 test the floor
TICKS = 48
NUM = ("t", "g", "ph", "st", "war", "pop", "n", "eb", "ebl", "ebs", "ebm", "ebst", "ebsv", "mb",
       "ed", "edst", "edsv", "edlab", "edmach", "edeng", "edslv", "edtu", "md")
NUM_V3 = ("eddn", "edw", "edcls", "edemp", "edbld", "edbg", "edwc", "ednh0", "ednh", "edtum", "kills", "warin")
_LINE = re.compile(r"TE_PG v=(\d) (t=.*)$")
_TICK = re.compile(r"TE_PG_TICK v=(\d) t=(-?\d+) date=(.*)$")
_DAY = re.compile(r"TE_PG_DAY v=(\d) d=(\d+) tag=(\S+) pop=(-?[\d.]+) ph=(-?\d+) date=(.*)$")
_ST = re.compile(r"TE_PG_ST v=(\d) d=(\d+) sid=(\d+) pop=(-?[\d.]+) prev=(-?[\d.]+)")


def expected_phase(t, group):
    """The phase that ran in the window ending at tick t (t >= 1)."""
    block = (t - 1) // 3
    return (block // 8) * 8 + (block + group) % 8


def measured(t):
    """Whether the window ending at tick t is measured (not the first after a switch)."""
    return t >= 1 and (t - 1) % 3 != 0


_YEAR = re.compile(r"TE_PG_(?:TICK|DAY|START|DONE)(?: v=\d)? .*date=\w+ \d+, (\d{4})")


def _file_years(path):
    """The years of the probe dates a log file mentions (tick, day, start and done lines)."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        return {int(m.group(1)) for m in map(_YEAR.search, fh) if m}


def parse(paths, min_year=0, version=2):
    """Read the probe's lines. With min_year, a file that dates any probe line before that year is
    skipped whole: one debug.log is one game session, so an earlier run's file holds only its lines."""
    rows, ticks, days, bad = {}, {}, {}, []
    states = collections.defaultdict(dict)
    seen = set()
    if min_year:
        paths = [p for p in paths if all(y >= min_year for y in _file_years(p))]
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.rstrip("\n")
                if "TE_PG" not in line or line in seen:
                    continue
                seen.add(line)
                m = _TICK.search(line)
                if m:
                    if int(m.group(1)) == version:
                        ticks[int(m.group(2))] = m.group(3).strip()
                    continue
                m = _DAY.search(line)
                if m:
                    if int(m.group(1)) == version:
                        days[(m.group(3), int(m.group(2)))] = (float(m.group(4)), int(m.group(5)), m.group(6).strip())
                    continue
                m = _ST.search(line)
                if m:
                    if int(m.group(1)) == version:
                        states[int(m.group(3))][int(m.group(2))] = float(m.group(4)) - float(m.group(5))
                    continue
                m = _LINE.search(line)
                if not m or int(m.group(1)) != version:
                    continue
                fields = dict(kv.split("=", 1) for kv in m.group(2).split() if "=" in kv)
                try:
                    rec = {k: float(fields[k]) for k in NUM}
                except (KeyError, ValueError):
                    bad.append(line[-200:])
                    continue
                for k in NUM_V3:
                    try:
                        rec[k] = float(fields.get(k, 0))
                    except ValueError:
                        rec[k] = 0.0
                rec["tag"] = fields.get("tag", "?")
                rows[(rec["tag"], int(rec["t"]))] = rec
    parse.states = states
    return rows, ticks, days, bad


def windows(rows):
    """{tag: [window]}: each tick t >= 1 with the previous tick's line, its change and averaged regressors."""
    out = collections.defaultdict(list)
    for (tag, t), r in rows.items():
        prev = rows.get((tag, t - 1))
        if prev is None or t < 1:
            continue
        w = {k: (prev[k] + r[k]) / 2 for k in NUM + NUM_V3 if k not in ("t", "g", "ph", "st", "war", "pop", "kills", "warin")}
        w["kills"] = max(0.0, r["kills"] - prev["kills"])
        w.update(tag=tag, t=t, g=int(r["g"]), ph=int(r["ph"]), change=r["pop"] - prev["pop"], pop=prev["pop"],
                 clean=prev["war"] == 0 and r["war"] == 0 and prev["st"] == r["st"],
                 measured=measured(t))
        out[tag].append(w)
    return out


def phase_means(ws, min_pop):
    """{tag: {phase: averaged measured clean window}}."""
    res = {}
    for tag, lst in ws.items():
        by = collections.defaultdict(list)
        for w in lst:
            if w["measured"] and w["clean"] and w["pop"] >= min_pop:
                by[w["ph"]].append(w)
        if by:
            res[tag] = {ph: {k: st.mean(x[k] for x in v) for k in v[0] if k not in ("tag", "clean", "measured")}
                        for ph, v in by.items()}
    return res


def _fit_line(xs, ys):
    """Least-squares (slope, intercept)."""
    mx, my = st.mean(xs), st.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if not sxx:
        return None, None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return slope, my - slope * mx


def _solve(a, b):
    """Gaussian elimination for a small dense system; None when singular."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        if abs(m[piv][c]) < 1e-12:
            return None
        m[c], m[piv] = m[piv], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def regress(rows, names, weights):
    """Weighted least squares of y on an intercept and the named columns; {name: coefficient}."""
    cols = ["const"] + names
    x = [[1.0] + [r[n] for n in names] for r in rows]
    y = [r["y"] for r in rows]
    a = [[sum(w * xi[i] * xi[j] for w, xi in zip(weights, x)) for j in range(len(cols))] for i in range(len(cols))]
    b = [sum(w * xi[i] * yi for w, xi, yi in zip(weights, x, y)) for i in range(len(cols))]
    sol = _solve(a, b)
    return dict(zip(cols, sol)) if sol else None


def fit_country(ph):
    """Per-country slopes and totals from its phase means; None where a phase is missing."""
    out = {}
    births = {BIRTH_STEP[p]: ph[p]["change"] for p in BIRTH_STEP if p in ph}
    deaths = {DEATH_STEP[p]: -ph[p]["change"] for p in DEATH_STEP if p in ph}
    for kind, data, base in (("b", births, 2), ("d", deaths, 1)):
        xs = [x for x in SLOPE_X if x in data]
        if len(xs) < 2 or base not in ph:
            continue
        slope, icept = _fit_line(xs, [data[x] for x in xs])
        if not slope:
            continue
        curve = ph[base]["eb" if kind == "b" else "ed"]
        read = ph[base]["mb" if kind == "b" else "md"]
        out[kind] = dict(slope=slope, icept=icept, ratio=slope / curve if curve else None,
                         total=icept / slope - 1, read=read, curve=curve,
                         floor={x: (data[x], slope * (1 + icept / slope - 1 + x)) for x in (-0.5, -0.9) if x in data})
    return out


def cmd_check(args):
    rows, ticks, days, bad = parse(args.logs, args.min_year, args.version)
    print(f"{len(rows)} TE_PG lines, {len(ticks)} tick headers, {len(days)} daily lines, {len(bad)} unreadable")
    for b in bad[:5]:
        print("  unreadable:", b)
    if not rows:
        return 1
    ts = sorted({t for _, t in rows})
    gaps = [t for t in range(ts[0], ts[-1] + 1) if t not in ts]
    print(f"ticks {ts[0]}..{ts[-1]} ({ticks.get(ts[0], '?')} .. {ticks.get(ts[-1], '?')}); missing: {gaps or 'none'}")
    per_tick = collections.Counter(t for _, t in rows)
    print("countries per tick:", " ".join(f"{t}:{per_tick[t]}" for t in ts))
    groups = collections.Counter(int(r["g"]) for (tag, t), r in rows.items() if t == ts[0])
    print("countries per group:", dict(sorted(groups.items())))
    wrong = [(tag, t, int(r["ph"]), expected_phase(t, int(r["g"]))) for (tag, t), r in rows.items()
             if t >= 1 and int(r["ph"]) != expected_phase(t, int(r["g"]))]
    print(f"phases off the schedule: {len(wrong)}", wrong[:5] if wrong else "")
    ws = windows(rows)
    both = [w["change"] / w["pop"] * 1000 for lst in ws.values() for w in lst
            if w["ph"] in (3, 11) and w["measured"] and w["clean"] and w["pop"] >= args.min_pop]
    if both:
        print(f"both-off windows: {len(both)}; change per 1,000 a month median {st.median(both):+.3f}, "
              f"largest |{max(both, key=abs):+.3f}|")
    seen_ph = collections.Counter(w["ph"] for lst in ws.values() for w in lst if w["measured"])
    print("measured windows per phase:", dict(sorted(seen_ph.items())))
    zero = [(tag, t) for (tag, t), r in rows.items() if r["eb"] == 0 and r["pop"] > 0]
    if zero:
        print(f"lines with eb=0 but people: {len(zero)} (a failed walk read?)", zero[:5])
    if days:
        print("daily lines (change from the day before; date):")
        for tag in sorted({k[0] for k in days}):
            seq = sorted((d, v) for (tg, d), v in days.items() if tg == tag)
            ch = [(d, v[0] - p[0], v[2]) for (dp, p), (d, v) in zip(seq, seq[1:])]
            nonzero = [c for c in ch if c[1]]
            print(f"  {tag}: {len(ch)} days, {len(nonzero)} with a change; "
                  + ", ".join(f"d{d} {c:+.0f} ({date})" for d, c, date in ch[:12]))
    states = parse.states
    if states:
        gaps = collections.Counter()
        per_state = []
        for sid, ch in states.items():
            ds = sorted(ch)
            per_state.append(len(ds))
            gaps.update(b - a for a, b in zip(ds, ds[1:]))
        weekdays = collections.Counter(d % 7 for ch in states.values() for d in ch)
        print(f"state change lines: {len(states)} states; changes per state min {min(per_state)} "
              f"median {st.median(per_state)} max {max(per_state)}")
        print("  days between a state's changes:", dict(sorted(gaps.items())))
        print("  change days mod 7:", dict(sorted(weekdays.items())))
    return 0


def cmd_report(args):
    rows, ticks, days, bad = parse(args.logs, args.min_year, args.version)
    ws = windows(rows)
    pm = phase_means(ws, args.min_pop)
    print(f"{len(rows)} lines, {len(pm)} countries with measured windows (>= {args.min_pop:,.0f} people)")
    # identities
    both, ident = [], []
    for tag, ph in pm.items():
        for p in (3, 11):
            if p in ph:
                both.append(ph[p]["change"] / ph[p]["pop"] * 1000)
        for base, boff, doff in ((0, 1, 2), (8, 9, 10)):
            if all(p in ph for p in (base, boff, doff)):
                pred = ph[doff]["change"] + ph[boff]["change"]
                ident.append((ph[base]["change"] - pred) / ph[base]["pop"] * 1000)
    if both:
        print(f"both off (should be 0): median {st.median(both):+.3f} per 1,000 a month over {len(both)}")
    if ident:
        print(f"none - (births only + deaths only) (should be 0): median {st.median(ident):+.3f} per 1,000 a month "
              f"over {len(ident)}")
    fits = {tag: fit_country(ph) for tag, ph in pm.items()}
    for kind, label in (("b", "births"), ("d", "deaths")):
        fs = [(tag, f[kind]) for tag, f in fits.items() if kind in f and f[kind]["ratio"]]
        if not fs:
            print(f"{label}: no fits yet")
            continue
        print(f"\n{label}: {len(fs)} countries")
        print(f"  slope / curve (1 if the step adds to 1 + total and the curve is right): "
              f"median {st.median(f['ratio'] for _, f in fs):.4f}")
        print(f"  measured total multiplier: median {st.median(f['total'] for _, f in fs):+.4f}; "
              f"state read: median {st.median(f['read'] for _, f in fs):+.4f}; "
              f"missing (total - read): median {st.median(f['total'] - f['read'] for _, f in fs):+.4f}")
        flo = [(x, (got - lin) / f["slope"]) for _, f in fs for x, (got, lin) in f["floor"].items()]
        for x in (-0.5, -0.9):
            v = [d for xx, d in flo if xx == x]
            if v:
                print(f"  step {x:+.1f}: measured less linear, in units of the slope: median {st.median(v):+.4f} "
                      f"over {len(v)}")
        base = 2 if kind == "b" else 1
        data = []
        for tag, f in fs:
            p = pm[tag][base]
            if kind == "b":
                cur = p["eb"] or 1
                data.append(dict(y=f["total"] - f["read"], lit=p["ebl"] / cur, mild=p["ebst"] / cur,
                                 severe=p["ebsv"] / cur, maln=p["ebm"] / cur, sol=p["ebs"] / cur, w=p["eb"]))
            else:
                cur = p["ed"] or 1
                data.append(dict(y=f["total"] - f["read"], lab=p["edlab"] / cur, mach=p["edmach"] / cur,
                                 eng=p["edeng"] / cur, slv=p["edslv"] / cur, mild=p["edst"] / cur,
                                 severe=p["edsv"] / cur, turmoil=p["edtu"] / cur, w=p["ed"]))
        names = (["lit", "mild", "severe", "maln", "sol"] if kind == "b"
                 else ["lab", "mach", "eng", "slv", "mild", "severe", "turmoil"])
        live = [n for n in names if len(data) > 1 and st.pstdev(d[n] for d in data) > 1e-4]
        coef = regress(data, live, [d["w"] for d in data]) if len(data) > len(live) + 1 else None
        if coef:
            hint = "   (weighted by the curve; literacy_penalty predicts lit -0.1)" if kind == "b" else ""
            print("  missing ~ " + "  ".join(f"{k} {v:+.4f}" for k, v in coef.items()) + hint)
        if args.verbose:
            for tag, f in sorted(fs, key=lambda x: -x[1]["curve"])[:args.verbose]:
                print(f"    {tag:4} curve {f['curve']:12,.1f}  slope/curve {f['ratio']:.4f}  total {f['total']:+.4f}  "
                      f"read {f['read']:+.4f}")
    return 0


KAPPA_MONTHLY = 12 * 28 / 365.25   # a 28-day window's share of a year's twelve monthly updates


def pooled_fit(ws, min_pop, kind, steps):
    """One weighted least-squares fit over every clean measured window of the given steps, all countries:
    change = k x curve x (1 + read) + k b1 x split1 + ... (no intercept; weights 1 / curve). For births,
    change is the births (deaths off); for deaths, minus the change (births off). The read includes the
    probe's own step (Q5). Returns ({'k': ..., split: coefficient / k}, n, per-window factors)."""
    if kind == "b":
        base, read, splits = "eb", "mb", ["ebl", "ebst", "ebsv"]
    else:
        base, read, splits = "ed", "md", ["edlab", "edmach", "edeng", "edslv", "edst", "edsv", "edtu"]
    data, weights, by_t = [], [], collections.defaultdict(lambda: [0.0, 0.0])
    for lst in ws.values():
        for w in lst:
            if not (w["measured"] and w["clean"] and w["pop"] >= min_pop and w["ph"] in steps and w[base] > 0):
                continue
            y = w["change"] if kind == "b" else -w["change"]
            row = {"y": y, "base": w[base] * (1 + w[read])}
            row.update({k: w[k] for k in splits})
            data.append(row)
            weights.append(1 / w[base])
            by_t[w["t"]][0] += y
            by_t[w["t"]][1] += row["base"]
    live = [k for k in splits if any(abs(r[k]) > 1e-9 for r in data)]
    cols = ["base"] + live
    a = [[sum(wt * r[ci] * r[cj] for wt, r in zip(weights, data)) for cj in cols] for ci in cols]
    b = [sum(wt * r[ci] * r["y"] for wt, r in zip(weights, data)) for ci in cols]
    sol = _solve(a, b) if data else None
    if not sol:
        return None, len(data), {}
    k = sol[0]
    out = {"k": k}
    out.update({c: v / k for c, v in zip(cols[1:], sol[1:])})
    return out, len(data), {t: y / x for t, (y, x) in sorted(by_t.items()) if x}


def cmd_pooled(args):
    rows, ticks, days, bad = parse(args.logs, args.min_year, args.version)
    ws = windows(rows)
    # Births leave out -0.9: a starving or literate pop's total can cross the floor there. Deaths keep every
    # step: their per-pop terms add, so the small totals of -0.5 and -0.9 show them best.
    steps_b = {p for p, x in BIRTH_STEP.items() if x >= -0.5}
    steps_d = set(DEATH_STEP)
    for kind, label, steps, floor_steps in (("b", "births", steps_b, {12: -0.5, 13: -0.9}),
                                            ("d", "deaths", steps_d, {14: -0.5, 15: -0.9})):
        fit, n, by_t = pooled_fit(ws, args.min_pop, kind, steps)
        if not fit:
            print(f"{label}: no data")
            continue
        used = ", ".join(f"{x:+.1f}" for x in sorted({(BIRTH_STEP if kind == 'b' else DEATH_STEP)[p] for p in steps}))
        print(f"\n{label}: pooled over {n} windows (steps {used})")
        print(f"  k = {fit['k']:.4f} a 28-day window = {fit['k'] / KAPPA_MONTHLY:.4f} x the curve's month x 12 a year"
              f" (1 = the census's x 12 is right)")
        names = {"ebl": "literacy (literacy_penalty predicts -0.1)", "ebst": "mild starvation", "ebsv": "severe starvation",
                 "edlab": "employed laborers", "edmach": "employed machinists", "edeng": "employed engineers",
                 "edslv": "employed slaves", "edst": "mild starvation", "edsv": "severe starvation", "edtu": "turmoil"}
        for c, v in fit.items():
            if c != "k":
                print(f"  multiplier per unit of {names.get(c, c)}: {v:+.4f}")
        print("  per window, change / (curve x (1 + read)):",
              " ".join(f"{t}:{v:.3f}" for t, v in by_t.items()))
        for p, x in floor_steps.items():
            f2, n2, _ = pooled_fit(ws, args.min_pop, kind, {p})
            if f2:
                print(f"  step {x:+.1f} alone: k = {f2['k']:.4f} over {n2} windows (the floor bends it if below the fit's k)")
    return 0


DEATH_PARTS = ("edcls", "edbld", "edbg", "ednh", "edtum", "edw")   # v3: curve deaths x each read (people a month)


def cmd_deaths(args):
    """v3: do the reads close the gap? deaths = k x (ed (1 + md) + every read), with k = 12 a year if complete."""
    rows, ticks, days, bad = parse(args.logs, args.min_year, args.version)
    ws = windows(rows)
    steps = {p for p, x in DEATH_STEP.items() if x >= -0.5}
    sel = [w for lst in ws.values() for w in lst
           if w["measured"] and w["clean"] and w["pop"] >= args.min_pop and w["ph"] in steps and w["ed"] > 0]
    print(f"{len(sel)} death windows (births off, steps -0.5 to +1.0)")
    if not sel:
        return 1
    tot_ed = sum(w["ed"] for w in sel)
    print("each read as a share of the curve's deaths (curve-weighted): " + "  ".join(
        f"{k} {sum(w[k] for w in sel) / tot_ed:+.4f}" for k in DEATH_PARTS + ("edwc", "edsv", "edst", "eddn", "edemp")))

    def fit(cols, base):
        data = [dict(y=-w["change"], base=base(w), **{c: w[c] for c in cols}) for w in sel]
        wts = [1 / w["ed"] for w in sel]
        names = ["base"] + list(cols)
        a = [[sum(wt * r[i] * r[j] for wt, r in zip(wts, data)) for j in names] for i in names]
        b = [sum(wt * r[i] * r["y"] for wt, r in zip(wts, data)) for i in names]
        sol = _solve(a, b)
        return dict(zip(names, sol)) if sol else None

    plain = fit((), lambda w: w["ed"] * (1 + w["md"]))
    full = fit((), lambda w: w["ed"] * (1 + w["md"]) + sum(w[k] for k in DEATH_PARTS) + w["edsv"])
    table = fit((), lambda w: w["ed"] * (1 + w["md"]) + w["edcls"] + w["edbld"] + w["edwc"] + w["ednh"] + w["edtum"]
                + w["edw"] + w["edsv"])
    free = fit(DEATH_PARTS + ("edwc", "edst", "edsv", "eddn"), lambda w: w["ed"] * (1 + w["md"]))
    for label, f in (("census (curve x (1 + state read))", plain), ("+ every read + severe starvation", full),
                     ("same, working conditions from the table", table)):
        if f:
            print(f"  {label:42} k = {f['base'] / KAPPA_MONTHLY:.4f}  (1 = complete)")
    if free:
        k = free["base"]
        print(f"  free fit: k = {k / KAPPA_MONTHLY:.4f}; each read's coefficient relative to k (1 = the read is the engine's): "
              + "  ".join(f"{c} {v / k:+.3f}" for c, v in free.items() if c != "base"))
    kills = sum(w["kills"] for w in sel)
    print(f"  recorded kills in these windows: {kills:,.0f} ({kills / max(1, sum(-w['change'] for w in sel)):.4%} of deaths)")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("check", cmd_check), ("report", cmd_report), ("pooled", cmd_pooled), ("deaths", cmd_deaths)):
        sp = sub.add_parser(name)
        sp.add_argument("logs", nargs="+")
        sp.add_argument("--min-pop", type=float, default=500000, help="ignore smaller countries (default 500,000)")
        sp.add_argument("--verbose", type=int, default=0, help="list the N largest countries' fits")
        sp.add_argument("--version", type=int, default=2, help="the probe's line version to read (default 2)")
        sp.add_argument("--min-year", type=int, default=0,
                        help="skip a log file that dates any probe line before this year (an earlier run's)")
        sp.set_defaults(fn=fn)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
