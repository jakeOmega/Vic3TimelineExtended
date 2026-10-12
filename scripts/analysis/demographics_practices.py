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
