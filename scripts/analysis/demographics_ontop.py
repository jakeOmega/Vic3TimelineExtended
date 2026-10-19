#!/usr/bin/env python3
"""Calibration step 3 in the harness: the deaths on top of the census by state-year, and #904's peacetime births less
deaths projected to the step's build (docs/superpowers/archive/specs/2026-10-12-demographics-calibration-step3-design.md §3).

The subcommand is demographics_harness.py's ontop-fit. Its inputs:
- #904's state-years (regional-rates/analyze.py --json: step year, group, peace, reasons, births, deaths, people,
  migration, tag, state id), as practices-fit reads them;
- the split of each state-year's window deaths (te_dg_ed, te_dg_ed_state, te_dg_ed_sev; Full only), from the save
  that closes the step (the step year + 1's 1 January): a plain-text save, or extract_all.py's per-save JSON of the
  same run (`{"date": "Y.M.D", "states": {sid: {"vars": {...}}}}`), which holds the same variables;
- the run's saves for the model's figures (demographics_practices.fit_states), at today's parameters and the point's.

The step's rules, per state-year (owner calls 1-2, 2026-10-12):
- the pops' own lines are te_dg_ed less its whole-state part and severe starvation's (the Causes of Death split);
  a state-year's net negative own lines are the Landowners' famine reserves (in the 2026-10-12 run every negative own
  line is the trait: the spec's §1(a)), absorbed per pop under call 1, so they leave its deaths; net positive ones
  (working conditions, dangerous methods: building scope) stay on top at the bare curve's weight, unchanged;
- the malaria factor scales the census's own rate: the deaths less the pops' own lines and severe starvation's, x the
  point's expected deaths at the state's census bands over today's (FitState.deaths), as practices-fit scales them;
- births take Late Marriage's and Birth Spacing's children per woman at main's decided point, as practices-fit does.
"""

import json
from pathlib import Path

import demographics_practices as DP
import demographics_save_inputs as S

SPLIT_VARS = ("te_dg_ed", "te_dg_ed_state", "te_dg_ed_sev")


def _year_of_date(date):
    y, m, d = (int(x) for x in date.split("."))
    return y if (m, d) == (1, 1) else None


def read_splits(paths, year_of=None):
    """{year: {sid: {var: value}}} for the 1 January saves among `paths` (.json: extract_all.py's per-save file;
    anything else: a plain-text save read with demographics_save_inputs.read_variables). year_of(path) gives a plain
    save's year (the harness's save_year)."""
    out = {}
    for path in paths:
        if str(path).endswith(".json"):
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            year = _year_of_date(data["date"])
            states = data["states"]
        else:
            year = year_of(path) if year_of else None
            _countries, states = S.read_variables(path, (), SPLIT_VARS)
        if year is None:
            continue
        out[year] = {sid: {k: rec.get("vars", {}).get(k) for k in SPLIT_VARS} for sid, rec in states.items()}
    return out


def split_of(splits, step_year, sid):
    """(own, severe) shares of a state-year's window deaths, from the save that closes it; (0, 0) where it holds no
    split (a step under Display only, or before the split existed)."""
    got = splits.get(step_year + 1, {}).get(sid)
    if not got or not got.get("te_dg_ed") or got.get("te_dg_ed_state") is None:
        return 0.0, 0.0
    ed, sev = got["te_dg_ed"], got.get("te_dg_ed_sev") or 0.0
    return (ed - got["te_dg_ed_state"] - sev) / ed, sev / ed


def measured_rates(rows):
    """{group or "World": peacetime births less deaths per 1,000 a year} (rows already in #904's span)."""
    acc = {}
    for _year, group, peace, _why, b, d, p, _mig, _tag, _sid in rows:
        if not peace or p <= 0:
            continue
        for key in (group, "World"):
            a = acc.setdefault(key, [0.0, 0.0])
            a[0] += b - d
            a[1] += p
    return {k: 1000 * a[0] / a[1] for k, a in acc.items() if a[1]}


def two_run_spread(rows_a, rows_b):
    """{group: |the two runs' measured peacetime rates' difference|} (call 3's spread; R.TWO_RUN_SPREAD records it)."""
    a, b = measured_rates(rows_a), measured_rates(rows_b)
    return {k: abs(a[k] - b[k]) for k in a if k in b and k != "World"}


def project(rows, splits, today, point, s, cut_lm, cut_bs, held, east, absorb=True):
    """#904's peacetime births less deaths at one point of the step, per 1,000 a year, in project_regions' shape
    ({"groups": {label: (measured, projected)}, "world": ..., "tags": {tag: (people, measured, projected)}}), with
    "parts": {label: {"own_neg", "own_pos", "sev"}} per 1,000. today, point: {save year: [FitState]} at today's
    parameters and at the point's (the malaria factor's size), as practices-fit takes them. absorb: call 1's rule (the
    net negative own lines leave the deaths); off, the own lines stay as measured."""
    years = sorted(today)
    by_today = {y: {st.sid: st for st in today[y]} for y in years}
    by_point = {y: {st.sid: st for st in point[y]} for y in years}
    acc, tag_year = {}, {}
    for year, group, peace, _why, b, d, p, _mig, tag, sid in rows:
        if not peace or p <= 0:
            continue
        y = max([x for x in years if x <= year + 1] or years[:1])
        t, q = by_today[y].get(sid), by_point[y].get(sid)
        br = dr = 1.0
        if t and q:
            br = DP.tfr_at(q, s, cut_lm, cut_bs, held, east) / t.base_tfr if t.base_tfr else 1.0
            dr = q.deaths / t.deaths if t.deaths and q.deaths else 1.0
        own_s, sev_s = split_of(splits, year, sid)
        own, sev = own_s * d, sev_s * d
        own_neg, own_pos = min(own, 0.0), max(own, 0.0)
        core = d - own - sev                       # the census's rate with the state-level lines: the factor scales it
        kept_own = own_pos if absorb else own
        after = core * dr + kept_own + sev
        for key in (group, "World", "tag:" + tag):
            a = acc.setdefault(key, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            a[0] += b - d
            a[1] += b * br - after
            a[2] += p
            a[3] += own_neg
            a[4] += own_pos
            a[5] += sev
        tag_year[(tag, year)] = tag_year.get((tag, year), 0.0) + p
    size = {}
    for (tag, _y), p in tag_year.items():
        size[tag] = max(size.get(tag, 0.0), p)

    def rate(a):
        return 1000 * a[0] / a[2], 1000 * a[1] / a[2]

    groups = {k: a for k, a in acc.items() if k != "World" and not k.startswith("tag:")}
    return {"groups": {k: rate(a) for k, a in groups.items()},
            "world": rate(acc["World"]) if "World" in acc else (0.0, 0.0),
            "tags": {k[4:]: (size[k[4:]], *rate(a)) for k, a in acc.items() if k.startswith("tag:")},
            "parts": {k: {"own_neg": 1000 * a[3] / a[2], "own_pos": 1000 * a[4] / a[2], "sev": 1000 * a[5] / a[2]}
                      for k, a in {**groups, "World": acc.get("World", [0.0] * 6)}.items() if a[2]}}


def malaria_infection(g):
    """MALARIA_INFECTION at mild excess g: the severe trait's at vanilla's ratio, to 0.01 (demographics_params)."""
    import demographics_params as P
    return {1: g, 2: round(g * P.MALARIA_SEVERE_RATIO, 2)}


def fit_g(rows, splits, today, by_g, practice, label="Africa", top=None):
    """The smallest g (by_g: {g: [FitState] by year}) at which `label`'s projected rate is at most `top` (default its
    history band's top), with call 1's absorption; None if none is."""
    import demographics_regions as R
    hi = dict((lbl, band) for lbl, _r, band in R.REPORT_REGIONS)[label][1] if top is None else top
    for g in sorted(by_g):
        got = project(rows, splits, today, by_g[g], *practice)["groups"].get(label, (0.0, 0.0))[1]
        if got <= hi:
            return g
    return None
