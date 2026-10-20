#!/usr/bin/env python3
"""Family Limitation as a general practice in the harness (phase 3; parent spec section 13).

A national practice, so a save's states are summed by owner: each country's people-weighted farm share, literacy and
contraception erosion, its laws, and its neighbours (the states across its borders, from the state-adjacency snapshot,
demographics_adjacency.py, and the save's owners). The replay steps every country's share once a year through a run's
saves as te_demog_fl_refresh does; `tfr_rows` puts the line it gives into each state's means and compares each anchor
country's children per woman with Gapminder's. The subcommand is demographics_harness.py's fl-replay; results in
docs/testing/demographics-family-limitation-2026-10-12.md.
"""

from dataclasses import dataclass, replace

import demographics_harness as H
import demographics_model as M
import demographics_params as P

# The check (the brief, 2026-10-12): France's, Belgium's and Switzerland's decline. The rest are controls.
CHECK = ("France", "Belgium", "Switzerland")
CONTROLS = ("United Kingdom", "Netherlands", "Germany", "Spain", "Italy", "Denmark", "Sweden", "Austria")
TAGS = {**H.HISTORY_TAGS, "Switzerland": ("SWI",)}


@dataclass
class Country:
    tag: str
    people: float          # every state with people, incorporated or not (the census's country walk)
    agrarian: float        # people-weighted farm share
    literacy: float
    erosion: float         # people-weighted contraception erosion (M.contraception_erosion)
    laws: frozenset
    history_modifier: bool  # it holds te_demog_family_limitation (the save's timed modifiers: France)
    church: float = 0.0     # its church laws' P.FL_LITERACY_TYPE total (a country line: every state reads the same)


def countries(states):
    """{tag: Country} from DP.practice_states' list."""
    acc = {}
    for s in states:
        if s.people <= 0:
            continue
        a = acc.setdefault(s.tag, [0.0, 0.0, 0.0, 0.0, frozenset(), False, 0.0])
        a[0] += s.people
        a[1] += s.people * s.inp.agrarian_share
        a[2] += s.people * s.inp.literacy
        a[3] += s.people * M.contraception_erosion(s.inp)
        a[4] = frozenset(s.inp.laws)
        a[5] = a[5] or s.inp.means_add > 0
        a[6] = s.inp.mods.get(P.FL_LITERACY_TYPE, 0.0)
    return {t: Country(t, p, ag / p, li / p, er / p, laws, hist, church)
            for t, (p, ag, li, er, laws, hist, church) in acc.items()}


def border_states(states, adjacency):
    """{tag: [(people, other tag)]}: the states another country owns in a state region next to one of the tag's, or in
    one of its own (a split region), each once: every_neighbouring_state from country scope, owner not ROOT."""
    by_region = {}
    for s in states:
        by_region.setdefault(s.state_region, []).append(s)
    out = {}
    for tag in {s.tag for s in states}:
        own = {s.state_region for s in states if s.tag == tag}
        near = set(own)
        for r in own:
            near |= adjacency.get(r, set())
        seen = {}
        for r in near:
            for s in by_region.get(r, ()):
                if s.tag != tag and s.people > 0:
                    seen[s.sid] = (s.people, s.tag)
        out[tag] = list(seen.values())
    return out


def _neighbour_mean(borders, shares):
    return M.people_mean([(p, shares[t]) for p, t in borders if t in shares])


def replay(loaded, adjacency):
    """{year: {tag: record}} for [(year, [PracticeState])], sorted: each country seeds at the first save that holds it
    (history's modifier: FAMILY_LIMITATION_MEANS, else 0), then steps once a census year with the conditions of the
    latest save at or before it, every country from last year's shares (in game each steps on its own day of the year; the
    order moves a neighbour's mean by one year's rise at most). A record: share, target, neighbours' mean, line."""
    shares, out, prev = {}, {}, None

    def step(cs, borders):
        new = {}
        for tag, c in cs.items():
            if tag not in shares:
                continue
            target = M.fl_target(c.agrarian, c.literacy, c.laws, literacy_mult=c.church)
            new[tag] = M.fl_step(shares[tag], target, _neighbour_mean(borders.get(tag, ()), shares))
        shares.update(new)

    for year, states in loaded:
        cs, borders = countries(states), border_states(states, adjacency)
        if prev is not None:
            prev_year, prev_cs, prev_borders = prev
            for _ in range(year - prev_year - 1):
                step(prev_cs, prev_borders)
        for tag, c in cs.items():
            shares.setdefault(tag, M.fl_seed(c.history_modifier))
        if prev is not None:
            step(cs, borders)
        out[year] = {tag: {"share": shares[tag], "target": M.fl_target(c.agrarian, c.literacy, c.laws,
                                                                         literacy_mult=c.church),
                           "neighbours": _neighbour_mean(borders.get(tag, ()), shares),
                           "line": M.fl_line(shares[tag], c.erosion), "people": c.people,
                           "agrarian": c.agrarian, "literacy": c.literacy, "erosion": c.erosion,
                           "heirship": "law_equal_inheritance" in c.laws}
                     for tag, c in cs.items()}
        prev = (year, cs, borders)
    return out


def _tag_of(country, people):
    return next((t for t in TAGS.get(country, ()) if people.get(t, 0) > 0), None)


def tfr_rows(states, fl, saved_shares=None):
    """{country: (today, with Family Limitation)} children per woman over its incorporated states, people-weighted.
    today: the save's own means (history's modifier) and Forced Heirship's rural cut on top (-0.15 x the state's farm
    share, which the census applies at its rate under Full); with: each state's means take its owner's line in place of
    history's modifier, and the cut is folded in (absorbed under Full). The practices take the save's own shares where
    it holds them, else the start table's seed."""
    import demographics_practices as DP
    seeds = DP.table_shares(states)
    saved = saved_shares if saved_shares is not None else DP.saved_shares(states)
    people = {}
    for s in states:
        people[s.tag] = people.get(s.tag, 0.0) + s.people
    want = {_tag_of(c, people): c for c in (*CHECK, *CONTROLS)}
    acc = {}
    for s in states:
        country = want.get(s.tag)
        if not country or not s.incorporated or s.people <= 0:
            continue
        inp = replace(s.inp, practices={**seeds.get(s.sid, {}), **saved.get(s.sid, {})})
        qf, qm, _ = M.group_rates(inp)
        e0 = (M.life_table(qf)["e0"] + M.life_table(qm)["e0"]) / 2
        today = M.fertility(inp, e0)["tfr"]
        if "law_equal_inheritance" in inp.laws:
            today *= 1 - 0.15 * inp.agrarian_share
        line = fl.get(s.tag, {}).get("line", 0.0)
        new = M.fertility(replace(inp, means_add=line), e0)["tfr"]
        a = acc.setdefault(country, [0.0, 0.0, 0.0])
        a[0] += s.people
        a[1] += s.people * today
        a[2] += s.people * new
    return {c: (t / p, n / p) for c, (p, t, n) in acc.items() if p}


def report(loaded, adjacency, anchors):
    """[(year, country, share, line, target, neighbours, today, with, history)] over the saves, and the error of `with`
    and of `today` against Gapminder over the check countries (each save year's nearest anchor within 5 years)."""
    fl = replay(loaded, adjacency)
    rows, err = [], {"today": [], "with": []}
    for year, states in loaded:
        people = {}
        for s in states:
            people[s.tag] = people.get(s.tag, 0.0) + s.people
        tfr = tfr_rows(states, fl[year])
        for country in (*CHECK, *CONTROLS):
            tag = _tag_of(country, people)
            if not tag or country not in tfr:
                continue
            rec = fl[year].get(tag, {})
            hist = H.nearest(anchors.get("tfr", {}).get(country, {}), year, 5)
            today, new = tfr[country]
            rows.append((year, country, rec.get("share", 0.0), rec.get("line", 0.0), rec.get("target", 0.0),
                         rec.get("neighbours"), today, new, hist[1] if hist else None))
            if hist and country in CHECK:
                err["today"].append((today - hist[1]) ** 2)
                err["with"].append((new - hist[1]) ** 2)
    rmse = {k: (sum(v) / len(v)) ** 0.5 if v else None for k, v in err.items()}
    return rows, rmse, fl


def state_ratios(states, fl):
    """{state id: children per woman with the practice over today's} for one save: today's carries history's
    modifier and, under Forced Heirship, the rural cut on top; with, the owner's line and no cut (tfr_rows' two)."""
    out = {}
    for s in states:
        if s.people <= 0:
            continue
        qf, qm, _ = M.group_rates(s.inp)
        e0 = (M.life_table(qf)["e0"] + M.life_table(qm)["e0"]) / 2
        today = M.fertility(s.inp, e0)["tfr"]
        if "law_equal_inheritance" in s.inp.laws:
            today *= 1 - 0.15 * s.inp.agrarian_share
        new = M.fertility(replace(s.inp, means_add=fl.get(s.tag, {}).get("line", 0.0)), e0)["tfr"]
        out[s.sid] = new / today if today > 0 else 1.0
    return out


def project_regions(rows, loaded, fl):
    """#904's peacetime births less deaths per 1,000 a year by region and for the world, measured and with the practice
    ({"groups": {label: (measured, projected)}, "world": (measured, projected)}): each peacetime state-year's births
    scaled by its state's ratio at the save at or before the one that closes it (demographics_practices.
    project_regions' rule), deaths as measured. The practice moves births only; a state the saves don't hold keeps its
    measured births."""
    years = sorted(y for y, _s in loaded)
    ratios = {y: state_ratios(states, fl[y]) for y, states in loaded}
    acc = {}
    for year, group, peace, _why, b, d, p, _mig, _tag, sid in rows:
        if not peace or p <= 0:
            continue
        y = max([x for x in years if x <= year + 1] or years[:1])
        r = ratios[y].get(sid, 1.0)
        for key in (group, "World"):
            a = acc.setdefault(key, [0.0, 0.0, 0.0])
            a[0] += b - d
            a[1] += b * r - d
            a[2] += p
    rate = {k: (1000 * a[0] / a[2], 1000 * a[1] / a[2]) for k, a in acc.items()}
    return {"groups": {k: v for k, v in rate.items() if k != "World"}, "world": rate.get("World", (0.0, 0.0))}
