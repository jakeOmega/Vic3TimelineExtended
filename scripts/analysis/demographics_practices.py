#!/usr/bin/env python3
"""Late Marriage and Birth Spacing in the harness (docs/superpowers/plans/2026-10-11-demographics-late-marriage.md).

A save's states with what the practices read (their state and strategic regions, people, incorporation and the model's
inputs, with the walk's women's job share where the save holds one), the drift replay over a run's saves (Task 4), the
regional growth table (Task 4) and the fit of the wealth curve's raise, the cuts and step 1's mortality against the
history anchors (Task 5). The subcommands are demographics_harness.py's: practices-replay, practices-fit, regions.
"""

import json
from dataclasses import dataclass, replace

import demographics_harness as H
import demographics_model as M
import demographics_params as P
import demographics_regions as R
import demographics_save_inputs as S


@dataclass
class PracticeState:
    sid: str
    tag: str
    state_region: str
    strategic_region: str
    people: float
    incorporated: bool
    inp: M.Inputs          # the model's inputs with no practice set; the shares come from a replay or the table
    bands: tuple = ()      # its census's people by five-year band, ((women, men), ...), 85+ last; empty with no census


# the census's bands a save holds per state (te_dg_bf<b>, te_dg_bm<b>): the fit's expected deaths (Task 5)
BAND_VARS = tuple(f"te_dg_b{x}{b}" for x in "fm" for b in range(P.BANDS))


def read_save(path):
    """(sections, {state id: {"vars": ...}}) of a plain-text save: the parse (265 MB a save in the normal-speed run),
    which the fit caches by path and re-uses at every grid point."""
    sections = S.read_sections(path)
    _countries, svars = S.read_variables(path, (), ("te_dg_fjob_share", *BAND_VARS, *H.CENSUS_INPUT_VARS))
    return sections, svars


def practice_states(path, carriers, regions=None, save=None):
    """[PracticeState] for every state of a plain-text save that has people (save: read_save's result, if cached).
    The model's inputs are the census's stored ones where the save holds them all (H.census_inputs, as `history`
    reads them since #916), else the save's techs, laws and modifiers. The women's job share is the walk's
    te_dg_fjob_share where the save holds it (a game with the census running), else 0; Undivided Farm Succession
    isn't read from saves, so only Primogeniture counts as impartible here (the script reads both)."""
    regions = R.strategic_region_of() if regions is None else regions
    sections, svars = read_save(path) if save is None else save
    state_region = S.state_regions(sections)
    out = []
    for tag, sts in S.state_inputs(sections).items():
        for sid, st, inc in sts:
            v = svars.get(sid, {}).get("vars", {})
            inp = replace(H.census_inputs(H.inputs_for(st, carriers, incorporated=inc), v),
                          agrarian_share=st.agrarian_share, female_job_share=v.get("te_dg_fjob_share", 0.0),
                          impartible=bool(set(P.IMPARTIBLE_LAWS) & st.laws))
            bands = tuple((v.get(f"te_dg_bf{b}", 0.0), v.get(f"te_dg_bm{b}", 0.0)) for b in range(P.BANDS))
            sr = state_region.get(sid, "")
            out.append(PracticeState(sid, tag, sr, regions.get(sr, ""), st.population, inc, inp, bands))
    return out


def table_shares(states):
    """{sid: {practice: share}}: what the census's seed gives each state with no sibling holding a share, its start
    less what its conditions have eroded (the 1836 table in a new game)."""
    return {s.sid: {p: M.practice_seed(p, s.inp, M.practice_start(p, s.state_region, s.strategic_region), [])
                    for p in P.PRACTICES} for s in states}


def read_shares(path):
    """{year: {sid: {practice: share}}} from practices-replay's --out file."""
    data = json.loads(open(path, encoding="utf-8").read())
    return {int(year): {sid: {p: rec[p] for p in P.PRACTICES} for sid, rec in by_sid.items()}
            for year, by_sid in data.items()}


# ---- the drift replay (spec 5.1 item 5) ---------------------------------------------------------------------

def _seed(shares, states):
    """te_demog_practice_seed: a state with no share takes its siblings' people-weighted mean (the states in its state
    region that hold one), else its start less what its conditions have eroded. Siblings share a start, so in a new
    game the order doesn't matter (the plan's D5)."""
    by_region = {}
    for s in states:
        by_region.setdefault(s.state_region, []).append(s)
    for s in states:
        if s.sid in shares:
            continue
        sibs = [x for x in by_region[s.state_region] if x.sid in shares]
        shares[s.sid] = {p: M.practice_seed(p, s.inp, M.practice_start(p, s.state_region, s.strategic_region),
                                            [(x.people, shares[x.sid][p]) for x in sibs]) for p in P.PRACTICES}


def _step(shares, states):
    """te_demog_practice_step for every state: a year's drift toward its target at these conditions."""
    for s in states:
        for p in P.PRACTICES:
            start = M.practice_start(p, s.state_region, s.strategic_region)
            shares[s.sid][p] = M.practice_drift(shares[s.sid][p], M.practice_target(p, s.inp, start))


def replay(loaded):
    """{year: {sid: record}} for each save in `loaded` ([(year, [PracticeState])], sorted): every state seeds at the
    first save that holds it, then the census steps once a year, each year with the conditions of the latest save at
    or before it (so the years between two saves take the earlier one's, and a save's own year takes its own). A
    record holds the shares, their targets at that save's conditions, the state's people and its regions."""
    shares, out, prev = {}, {}, None
    for year, states in loaded:
        if prev is not None:
            prev_year, prev_states = prev
            for _ in range(year - prev_year - 1):
                _step(shares, prev_states)
        _seed(shares, states)
        if prev is not None:
            _step(shares, states)
        out[year] = {}
        for s in states:
            rec = {p: shares[s.sid][p] for p in P.PRACTICES}
            for p in P.PRACTICES:
                rec[f"target_{p}"] = M.practice_target(p, s.inp, M.practice_start(p, s.state_region,
                                                                                    s.strategic_region))
            rec.update(people=s.people, state_region=s.state_region, strategic_region=s.strategic_region)
            out[year][s.sid] = rec
        prev = (year, states)
    return out


WEST = frozenset({"region_western_europe", "region_northern_europe", "region_central_europe"})
EAST_ASIA_BS = (("Japan", lambda r: P.PRACTICE_START_STATE["bs"].get(r["state_region"]) == 1.0),
                ("China, Manchuria, Korea", lambda r: M.bs_held_group(r["state_region"], r["strategic_region"])
                 == "east_asia"))


def _mean(records, key, keep):
    held = [(r["people"], r[key]) for r in records if keep(r) and r["people"] > 0]
    people = sum(p for p, _v in held)
    return sum(p * v for p, v in held) / people if people else None


def replay_gate(result, upto=1887):
    """Spec 5.2's replay items: the West's Late Marriage at 0.8 or more, and East Asia's Birth Spacing within 0.1 of
    its start, at every save up to `upto`. Returns the failures as lines."""
    fails = []
    for year, recs in sorted(result.items()):
        if year > upto:
            continue
        west = _mean(recs.values(), "lm", lambda r: r["strategic_region"] in WEST)
        if west is not None and west < 0.8:
            fails.append(f"{year}: the West's Late Marriage {west:.2f} (at least 0.8)")
        for label, keep in EAST_ASIA_BS:
            got = _mean(recs.values(), "bs", keep)
            start = _mean([dict(r, start=M.practice_start("bs", r["state_region"], r["strategic_region"]))
                           for r in recs.values()], "start", keep)
            if got is not None and abs(got - start) > 0.1:
                fails.append(f"{year}: East Asia's Birth Spacing, {label}, {got:.2f} against its start {start:.2f}")
    return fails


def replay_moves(result, top=10):
    """The states whose shares moved most from their start by the last save: [(move, practice, sid, state region,
    start, share, target)], largest first. Phase 2 has no spread, so every move is the state's own conditions."""
    year = max(result)
    rows = []
    for sid, r in result[year].items():
        for p in P.PRACTICES:
            start = M.practice_start(p, r["state_region"], r["strategic_region"])
            rows.append((abs(r[p] - start), p, sid, r["state_region"], start, r[p], r[f"target_{p}"]))
    return sorted(rows, reverse=True)[:top]
