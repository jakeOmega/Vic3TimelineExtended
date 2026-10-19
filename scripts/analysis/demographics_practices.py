#!/usr/bin/env python3
"""Late Marriage and Birth Spacing in the harness (docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md).

A save's states with what the practices read (their state and strategic regions, people, incorporation and the model's
inputs, with the walk's women's job share where the save holds one), the drift replay over a run's saves (Task 4), the
regional growth table (Task 4) and the fit of the wealth curve's raise, the cuts and step 1's mortality against the
history anchors (Task 5). The subcommands are demographics_harness.py's: practices-replay, practices-fit, regions.
"""

import contextlib
import json
import math
from dataclasses import dataclass, field, replace

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
    stored: dict = field(default_factory=dict)   # the save's own shares (te_dg_pr_*), {} unless it holds every one


# the census's bands a save holds per state (te_dg_bf<b>, te_dg_bm<b>): the fit's expected deaths (Task 5)
BAND_VARS = tuple(f"te_dg_b{x}{b}" for x in "fm" for b in range(P.BANDS))


def read_save(path):
    """(sections, {state id: {"vars": ...}}) of a plain-text save: the parse (265 MB a save in the normal-speed run),
    which the fit caches by path and re-uses at every grid point."""
    sections = S.read_sections(path)
    _countries, svars = S.read_variables(path, (), ("te_dg_fjob_share", *BAND_VARS, *H.CENSUS_INPUT_VARS,
                                                    *H.PRACTICE_VARS, *H.MALARIA_VARS,
                                                    *H.SAFETY_VARS))
    return sections, svars


_WALKED = {}   # id(sections) -> (sections, S.state_inputs(sections))


def _state_inputs(sections):
    """S.state_inputs once a parsed save: the pops' walk is the slow part of a grid point, and nothing a point patches
    (the mortality knobs, the cuts, the means pair's carriers) reaches it."""
    hit = _WALKED.get(id(sections))
    if hit is None or hit[0] is not sections:
        hit = _WALKED[id(sections)] = (sections, S.state_inputs(sections))
    return hit[1]


def practice_states(path, carriers, regions=None, save=None):
    """[PracticeState] for every state of a plain-text save that has people (save: read_save's result, if cached).
    The model's inputs are the census's stored ones where the save holds them all (H.census_inputs, as `history`
    reads them since #916), else the save's techs, laws and modifiers. `stored` holds the save's own shares
    (te_dg_pr_*) where it has them all. The women's job share is the walk's
    te_dg_fjob_share where the save holds it (a game with the census running), else 0. Impartible inheritance is the
    laws' P.LM_FARMS_TYPE line in the inputs' mods; amendments aren't read from saves, so Undivided Farm Succession's
    is missing here (the script reads both)."""
    regions = R.strategic_region_of() if regions is None else regions
    sections, svars = read_save(path) if save is None else save
    state_region = S.state_regions(sections)
    out = []
    for tag, sts in _state_inputs(sections).items():
        for sid, st, inc in sts:
            v = svars.get(sid, {}).get("vars", {})
            inp = replace(H.census_inputs(H.inputs_for(st, carriers, incorporated=inc), v),
                          agrarian_share=st.agrarian_share, female_job_share=v.get("te_dg_fjob_share", 0.0))
            bands = tuple((v.get(f"te_dg_bf{b}", 0.0), v.get(f"te_dg_bm{b}", 0.0)) for b in range(P.BANDS))
            sr = state_region.get(sid, "")
            stored = H.saved_shares({sid: v}).get(sid, {})
            out.append(PracticeState(sid, tag, sr, regions.get(sr, ""), st.population, inc, inp, bands, stored))
    return out


def saved_shares(states):
    """{sid: {practice: share}}: the shares the save itself holds (Stop B, M2), for the states that hold them all."""
    return {s.sid: dict(s.stored) for s in states if s.stored}


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

def _seed(shares, states, region):
    """te_demog_practice_seed: a state with no share takes its siblings' people-weighted mean (the states in its state
    region that hold one); else its region's copy (`region`, {state region: {practice: share}}, which te_demog_practice
    _step writes: a whole region that changed hands, Stop B's I1); else its start less what its conditions have
    eroded. Siblings share a start, so in a new game the order doesn't matter (the plan's D5)."""
    by_region = {}
    for s in states:
        by_region.setdefault(s.state_region, []).append(s)
    for s in states:
        if s.sid in shares:
            continue
        sibs = [x for x in by_region[s.state_region] if x.sid in shares]
        copy = region.get(s.state_region, {})
        shares[s.sid] = {p: M.practice_seed(p, s.inp, M.practice_start(p, s.state_region, s.strategic_region),
                                            [(x.people, shares[x.sid][p]) for x in sibs], copy.get(p))
                         for p in P.PRACTICES}


def neighbour_map(states, adjacency):
    """{state id: [neighbouring state]} for the phase 3 spread (te_demog_practices_neighbours): the states in the state
    regions next to its own (demographics_adjacency's land snapshot), and the other states of its own region. None
    (no adjacency given) spreads nothing."""
    if adjacency is None:
        return None
    by_region = {}
    for s in states:
        by_region.setdefault(s.state_region, []).append(s)
    out = {}
    for s in states:
        near = [x for r in adjacency.get(s.state_region, ()) for x in by_region.get(r, ())]
        near += [x for x in by_region.get(s.state_region, ()) if x.sid != s.sid]
        out[s.sid] = near
    return out


def _step(shares, states, region, neighbours=None):
    """te_demog_practice_step for every state: a year's drift toward its target at these conditions and (phase 3) the
    spread toward its neighbours' people-weighted mean, from last year's shares (in game each state steps on its own
    day, so a neighbour's share may already be this year's: a year's drift at most), then the shares copied to its state
    region (the last state of a region to step wins, as in game)."""
    before = {sid: dict(v) for sid, v in shares.items()}
    for s in states:
        for p in P.PRACTICES:
            start = M.practice_start(p, s.state_region, s.strategic_region)
            near = None
            if neighbours is not None:
                near = M.people_mean([(x.people, before[x.sid][p]) for x in neighbours.get(s.sid, ())
                                      if x.sid in before])
            shares[s.sid][p] = M.practice_drift(before[s.sid][p], M.practice_target(p, s.inp, start), near)
        region[s.state_region] = dict(shares[s.sid])


def replay(loaded, adjacency=None):
    """{year: {sid: record}} for each save in `loaded` ([(year, [PracticeState])], sorted): every state seeds at the
    first save that holds it, then the census steps once a year, each year with the conditions of the latest save at
    or before it (so the years between two saves take the earlier one's, and a save's own year takes its own). Each
    step writes its region's copy, which a new ID with no sibling holding a share seeds from, as in game (a region that
    changed hands between two sampled saves). A record holds the shares, their targets at that save's conditions, the
    state's people and its regions. adjacency ({state region: set of neighbours}, demographics_adjacency.neighbours):
    phase 3's spread; None leaves it out (phase 2's replay)."""
    shares, region, out, prev = {}, {}, {}, None
    for year, states in loaded:
        near = neighbour_map(states, adjacency)
        if prev is not None:
            prev_year, prev_states, prev_near = prev
            for _ in range(year - prev_year - 1):
                _step(shares, prev_states, region, prev_near)
        _seed(shares, states, region)
        if prev is not None:
            _step(shares, states, region, near)
        out[year] = {}
        for s in states:
            rec = {p: shares[s.sid][p] for p in P.PRACTICES}
            for p in P.PRACTICES:
                rec[f"target_{p}"] = M.practice_target(p, s.inp, M.practice_start(p, s.state_region,
                                                                                    s.strategic_region))
            rec.update(people=s.people, state_region=s.state_region, strategic_region=s.strategic_region)
            out[year][s.sid] = rec
        prev = (year, states, near)
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


# ---- the fit (spec 2.3, 5.1 item 6) and the regional projection (review C1) ---------------------------------
FLAT_GUESSES = frozenset({"China", "Iran", "Turkey", "Mexico", "Peru", "Korea"})   # half weight (spec 5.2)
DROPPED = frozenset({("United States", 1887), ("Chile", 1887)})   # fertility transitions (spec 2.3)
HIGH_GROUP = ("Iran", "Turkey", "Russia", "Mexico", "Argentina")  # history's early-marrying, about 7: reported only
WESTERN_E0 = (("United Kingdom", 41.0), ("Sweden", 41.0), ("Denmark", 41.0))   # spec 5.2: within 3 years, 1837


@dataclass
class FitState:
    sid: str
    country: str           # its HISTORY_TAGS name when its owner is the tag history uses, else ""
    tag: str
    people: float
    incorporated: bool
    base_tfr: float        # the model's children per woman with no practice, on the curve as it stands
    nrr_per_tfr: float     # daughters per woman per child per woman: survival to each childbearing age
    e0: float
    deaths: float | None   # expected deaths a year at its census bands (None: the save holds no census here)
    lm: float
    bs: float
    held: str | None       # its held Birth Spacing share: "east_asia" (China, Manchuria, Korea), "india", or None


def band_deaths(qf, qm, bands):
    """Expected deaths a year at a state's census bands (te_dg_bf<b>, te_dg_bm<b>: people by five-year band, 85+
    last) under the model's group rates (per 100,000 a year), each band at the mean of its ages' group rates."""
    total = 0.0
    for b, (women, men) in enumerate(bands):
        ages = range(5 * b, 5 * b + 5) if b < P.BANDS - 1 else range(85, 100)
        rf = sum(qf[P.group_of(a)] for a in ages) / len(ages)
        rm = sum(qm[P.group_of(a)] for a in ages) / len(ages)
        total += (women * rf + men * rm) / 100000
    return total


def fit_states(path, carriers, shares, save=None):
    """[FitState] for one save. shares: {sid: {practice: share}} (a replay's year, or table_shares); save: read_save's
    result, so a grid re-runs the model without re-reading the file. The model reads demographics_params at call time,
    so patch_params and patched carriers reach it."""
    states = practice_states(path, carriers, save=save)
    people = {}
    for s in states:
        people[s.tag] = people.get(s.tag, 0.0) + s.people
    chosen = {}
    for country, tags in H.HISTORY_TAGS.items():
        tag = next((t for t in tags if people.get(t, 0) > 0), None)
        if tag:
            chosen[tag] = country
    out = []
    for s in states:
        if s.people <= 0:
            continue
        qf, qm, _mmr = M.group_rates(s.inp)
        e0 = (M.life_table(qf)["e0"] + M.life_table(qm)["e0"]) / 2
        base = M.fertility(s.inp, e0)["tfr"]
        sh = shares.get(s.sid, {})
        held = M.bs_held_group(s.state_region, s.strategic_region)
        deaths = band_deaths(qf, qm, s.bands) if any(w or m for w, m in s.bands) else None
        out.append(FitState(s.sid, chosen.get(s.tag, ""), s.tag, s.people, s.incorporated, base, M.nrr(1.0, qf), e0,
                            deaths, sh.get("lm", 0.0), sh.get("bs", 0.0), held))
    return out


def tfr_at(st, s, cut_lm, cut_bs, held, east):
    """A state's children per woman at one point: the curve x s, its shares' terms, India's held share (held) or East
    Asia's (east) in place of its start, each scaling its replayed share (what the drift has left of the start). A
    start of 0 leaves nothing to erode, so the state takes the held share itself."""
    bs = st.bs
    if st.held == "india":
        bs = held * (st.bs / P.BS_HELD_START if P.BS_HELD_START else 1.0)
    elif st.held == "east_asia":
        bs = east * (st.bs / P.BS_EAST_ASIA_START if P.BS_EAST_ASIA_START else 1.0)
    return s * st.base_tfr * (1 - cut_lm * st.lm) * (1 - cut_bs * bs)


def cancel_share(s, cut_bs):
    """The Birth Spacing share that cancels the raise s (spec 2.2): (1 - 1/s) / cut_bs; 0 with no cut."""
    return (1 - 1 / s) / cut_bs if cut_bs else 0.0


def evaluate(fit_by_year, anchors, s, cut_lm, cut_bs, held=None, east=None, years=None):
    """One grid point over {year: [FitState]}: the error over the anchor countries in `years` (default every year), the
    world's children per woman (states of tags with 1M people or more), each anchor country's (model, history), and
    the high group's range in the first year (reported, not judged). held: India's Birth Spacing share, default the
    cancel share (spec 2.2); east: China's, Manchuria's and Korea's, default the same (D13)."""
    h = cancel_share(s, cut_bs) if held is None else held
    e = h if east is None else east
    countries, sq, weights, world_tfr = {}, 0.0, 0.0, {}
    for year, states in sorted(fit_by_year.items()):
        tag_people = {}
        for st in states:
            tag_people[st.tag] = tag_people.get(st.tag, 0.0) + st.people
        acc, wp, wt = {}, 0.0, 0.0
        for st in states:
            tfr = tfr_at(st, s, cut_lm, cut_bs, h, e)
            if tag_people[st.tag] >= 1e6:
                wp, wt = wp + st.people, wt + st.people * tfr
            if st.country and st.incorporated:
                a = acc.setdefault(st.country, [0.0, 0.0])
                a[0], a[1] = a[0] + st.people, a[1] + st.people * tfr
        world_tfr[year] = wt / wp if wp else None
        for country, (p, t) in acc.items():
            hist = H.nearest(anchors.get("tfr", {}).get(country, {}), year, 5)
            countries[(country, year)] = (t / p, hist[1] if hist else None)
            if hist and (country, year) not in DROPPED and (years is None or year in years):
                w = 0.5 if country in FLAT_GUESSES else 1.0
                sq, weights = sq + w * (t / p - hist[1]) ** 2, weights + w
    first = min(fit_by_year)
    high = [countries[(c, first)][0] for c in HIGH_GROUP if (c, first) in countries]
    return {"error": (sq / weights) ** 0.5 if weights else None, "world_tfr": world_tfr, "countries": countries,
            "high": (min(high), max(high)) if high else None, "held": h, "east": e}


def fit_table(fit_by_year, anchors, s_grid, lm_grid, bs_grid, years=None):
    """[(s, cut_lm, cut_bs, result)]: for each raise, the cuts with the least error (spec 2.3's method)."""
    rows = []
    for s in s_grid:
        best = None
        for cut_lm in lm_grid:
            for cut_bs in bs_grid:
                res = evaluate(fit_by_year, anchors, s, cut_lm, cut_bs, years=years)
                if res["error"] is not None and (best is None or res["error"] < best[3]["error"]):
                    best = (s, cut_lm, cut_bs, res)
        if best:
            rows.append(best)
    return rows


# #904's table spans the census steps of 1837-1900 (its analyze.py's five-year intervals, 1837 to 1901). Its rows also
# hold 1901's steps (the 1902 save), which the table leaves out.
PEACETIME_YEARS = (1837, 1901)


def peacetime_span(rows, first=PEACETIME_YEARS[0], end=PEACETIME_YEARS[1]):
    """#904's state-years inside its table's span, first <= step year < end, so a projection's measured column is its
    peacetime column."""
    return [r for r in rows if first <= r[0] < end]


def project_regions(rows, today, point, s, cut_lm, cut_bs, held=None, east=None):
    """#904's peacetime births less deaths, projected to one point of the fit (review C1).

    rows: #904's state-years ([step year, group, peace, reasons, births, deaths, people, migration, tag, state id],
    from its analyze.py --json; its peacetime filter is the `peace` flag). today, point: {save year: [FitState]} with
    today's parameters and with the point's (the mortality knobs patched, or the same lists). Each peacetime state-year
    takes the fit save at or before the one that closes it (the step year + 1): births x the point's children per woman
    over today's (no practice, s = 1), deaths x the point's expected deaths at the state's census bands over today's. A
    state the fit saves don't hold keeps its measured rates. Returns, per 1,000 a year, {"groups": {label: (measured,
    projected)}, "world": (measured, projected), "tags": {tag: (people, measured, projected)}}; a tag's people are its
    largest year's peacetime people. held, east: the two held Birth Spacing shares, as evaluate takes them."""
    h = cancel_share(s, cut_bs) if held is None else held
    e = h if east is None else east
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
            br = tfr_at(q, s, cut_lm, cut_bs, h, e) / t.base_tfr if t.base_tfr else 1.0
            dr = q.deaths / t.deaths if t.deaths and q.deaths else 1.0
        for key in (group, "World", "tag:" + tag):
            a = acc.setdefault(key, [0.0, 0.0, 0.0])
            a[0] += b - d
            a[1] += b * br - d * dr
            a[2] += p
        tag_year[(tag, year)] = tag_year.get((tag, year), 0.0) + p
    size = {}
    for (tag, _y), p in tag_year.items():
        size[tag] = max(size.get(tag, 0.0), p)

    def rate(a):
        return 1000 * a[0] / a[2], 1000 * a[1] / a[2]

    return {"groups": {k: rate(a) for k, a in acc.items() if k != "World" and not k.startswith("tag:")},
            "world": rate(acc["World"]) if "World" in acc else (0.0, 0.0),
            "tags": {k[4:]: (size[k[4:]], *rate(a)) for k, a in acc.items() if k.startswith("tag:")}}


def east_for_china(rows, today, point, s, cut_lm, cut_bs, held=None, top=0.9):
    """Owner, 2026-10-11 (D13): East Asia's Birth Spacing share at this point, the smallest on a 0.01 grid from the cancel
    share up to `top` at which China's projected peacetime births less deaths is at most the top of its band (+6), and
    China's rate there. Never below the cancel share: if China is below +3 even there, it fails the gate on mortality."""
    hi = dict((label, band) for label, _r, band in R.REPORT_REGIONS)["China"][1]
    h = cancel_share(s, cut_bs) if held is None else held
    e = math.ceil(h * 100 - 1e-9) / 100
    while True:
        rate = project_regions(rows, today, point, s, cut_lm, cut_bs, held, e)["groups"].get("China", (0.0, 0.0))[1]
        if rate <= hi or e >= top:
            return e, rate
        e = round(e + 0.01, 2)


def region_gate(proj, world_margin=1.0, big=2e7, widen=None):
    """Review C1's gate on a projection: every #904 group with a band (R.REPORT_REGIONS) inside it; the world at or
    below today's measured rate less world_margin per 1,000 (x1.65 over 1836-1900 needs about 1 less than the run's
    +8.8); no country of `big` people or more with projected peacetime births below deaths. Returns the failures.
    widen: {group: w}, each band widened by w on both sides (calibration step 3's call 3: R.widening(), half the
    two-run spread, at least 0.5); None judges on history's bands."""
    fails = []
    for label, _regions, band in R.REPORT_REGIONS:
        if band and label in proj["groups"]:
            lo, hi = band
            w = (widen or {}).get(label, 0.0)
            got = proj["groups"][label][1]
            if not lo - w <= got <= hi + w:
                wide = f", widened {lo - w:+.2f} to {hi + w:+.2f}" if w else ""
                fails.append(f"{label}: {got:+.2f} per 1,000 (history {lo:+g} to {hi:+g}{wide})")
    measured, projected = proj["world"]
    if projected > measured - world_margin:
        fails.append(f"World: {projected:+.2f} per 1,000 (at most {measured - world_margin:+.2f})")
    for tag, (people, _measured, got) in sorted(proj["tags"].items()):
        if people >= big and got < 0:
            fails.append(f"{tag}: {got:+.2f} per 1,000 with {people / 1e6:.0f}M people")
    return fails


@contextlib.contextmanager
def patch_params(infection_scale=1.0, **values):
    """demographics_params' values for one grid point, restored after; infection_scale multiplies the base infection
    schedule (both sexes, every age group). The model reads P at call time, so the next fit_states sees them."""
    saved = {k: getattr(P, k) for k in values}
    saved_infection = P.INFECTION
    try:
        for k, v in values.items():
            setattr(P, k, v)
        P.INFECTION = {sex: [x * infection_scale for x in rates] for sex, rates in saved_infection.items()}
        yield
    finally:
        for k, v in saved.items():
            setattr(P, k, v)
        P.INFECTION = saved_infection


def mortality_report(fit_by_year):
    """Spec 5.2's Western item: the United Kingdom's, Sweden's and Denmark's life expectancy in the first year (their
    incorporated states, by people), against 41."""
    first = min(fit_by_year)
    acc = {}
    for st in fit_by_year[first]:
        if st.country in dict(WESTERN_E0) and st.incorporated:
            a = acc.setdefault(st.country, [0.0, 0.0])
            a[0], a[1] = a[0] + st.people, a[1] + st.people * st.e0
    return {c: e / p for c, (p, e) in acc.items() if p}
