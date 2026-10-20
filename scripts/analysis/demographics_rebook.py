#!/usr/bin/env python3
"""The census re-walked through a run's saves with the run's own residual, booked by today's rules (the migrant
booking, 2026-10-12; docs/testing/demographics-migrant-booking-2026-10-12.md).

The subcommand is demographics_harness.py's rebook. A save made under Full holds every census state's last step: its
census year (te_dg_year, te_dg_stepped), its people and the residual it booked (te_dg_people, te_dg_net_migration), and
the walk's inputs the migrant profile reads. The re-walk starts each state from the ring the first save holds (or a
seed where it has none), steps it at every save where the game stepped it, seeds it again where the game did, and
books each step's residual by the booking in force in demographics_model, or by the profile alone (`booked=False`:
no cap and no correction, the booking before 2026-10-12). The residual itself doesn't depend on the ring (it is the
engine's population change less the walk's births and deaths), so it is the run's. Left out, as small next to the
residual: the war dead (tens of thousands a year at most, 1836-1901) and the mod's kills. Since 2026-10-19
te_dg_net_migration also holds a state's Internal Resettlement moves, which the census booked by their programmes'
profiles; the step stores them apart (te_dg_rs_net), and the re-walk re-books only the rest (booked_residual). The
known moves themselves aren't re-booked (a save holds no counters by profile), so an Authority's states re-walk without
them. The natural rates come from
the walk's stored inputs (standard of living, literacy, urban share), not the run's full modifier totals, so the
replay's own sex balance runs about +1 above the saves' (the 2026-10-12 run: median +0.2 to +1.4, 5th to 95th
percentile -2 to +7).

Saves: plain text (read with demographics_save_inputs; two passes) or extract_all.py's per-save JSON from the
2026-10-12 overnight analysis (`{"date", "states": {sid: {"country", "region", "devastation", "vars", "ring"}},
"countries", "laws", "techs", "wars"}`), which holds the same variables but only the medical technologies: the family
weight's transport technologies then come from whichever plain-text saves are given (each year the nearest earlier).
"""

import functools
import json
from pathlib import Path

import demographics_model as M
import demographics_modifiers as DM
import demographics_params as P
import demographics_save_inputs as S

STEP_VARS = ("te_dg_year", "te_dg_stepped", "te_dg_people", "te_dg_net_migration", "te_dg_inflow_years",
             "te_dg_sol", "te_dg_lit", "te_dg_urban_share", "te_dg_fjob_share", "te_dg_wtfr", "te_dg_agr_share",
             "te_dg_in_turm", "te_dg_rs_net")
BAND_VARS = tuple(f"te_dg_b{s}{b}" for s in "fm" for b in range(P.BANDS))
RING_VARS = (("te_dg_scale", "te_dg_pf", "te_dg_pm", "te_dg_pa")
             + tuple(f"te_dg_{s}{k}" for s in "fm" for k in range(P.RING_YEARS)))


@functools.lru_cache(maxsize=None)
def migrant_lines():
    """The migrant profile's two types' carriers in the game files (modifier-types stage 3): the women's-rights laws'
    share of women at work and the transport technologies' families, read once."""
    return tuple(DM.load_carriers(types=P.MIGRANT_PROFILE_TYPES))


def women_laws():
    """The laws a save's countries keep: those carrying the women's work share."""
    return frozenset(c.key for c in migrant_lines() if c.type == P.FEMALE_WORK_SHARE_TYPE)


def transport_techs():
    """The technologies carrying the families' line (Paddle Steamer to Jet Engine Technology)."""
    return frozenset(c.key for c in migrant_lines() if c.type == P.FAMILY_MIGRATION_TYPE)


def _year_of_date(date):
    return int(str(date).split(".")[0])


def read_save(path, year_of=None, ring=False):
    """{year, states: {sid: {owner, region, devastation, vars, ring}}, countries: {cid: {tag, laws, techs, at_war}},
    techs_known}: what the re-walk reads from one save. ring: also the slots (a plain-text save's te_dg_f<k>/m<k>;
    extract_all.py keeps them only in its ring years). techs_known: the save holds every technology (plain text), not
    only the medical ones (the JSON)."""
    if str(path).endswith(".json"):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        at_war = {cid for w in data.get("wars", []) for cid in w.get("participants", [])}
        laws, techs = data.get("laws", {}), data.get("techs", {})
        countries = {cid: {"tag": c.get("tag", ""), "laws": frozenset(laws.get(cid, ())) & women_laws(),
                           "techs": frozenset(techs.get(cid, ())), "at_war": cid in at_war}
                     for cid, c in data.get("countries", {}).items()}
        states = {}
        for sid, st in data.get("states", {}).items():
            raw = st.get("ring")
            slots = None
            if raw:
                slots = {"f": {int(k): v for k, v in raw["f"].items()}, "m": {int(k): v for k, v in raw["m"].items()}}
            states[sid] = {"owner": st.get("country"), "region": st.get("region"),
                           "devastation": st.get("devastation") or 0.0, "vars": st.get("vars", {}), "ring": slots}
        return {"year": _year_of_date(data["date"]), "states": states, "countries": countries, "techs_known": False}
    names = STEP_VARS + BAND_VARS + ("te_dg_sex_balance",) + (RING_VARS if ring else ())
    raw_countries, raw_states = S.read_variables(path, (), names)
    sections = S.read_sections(path, wanted=("states", "technology"))
    acquired = {}
    for rec in sections["technology"].values():
        techs = rec.get("acquired_technologies", "").strip("{} ").split()
        acquired[rec.get("country")] = frozenset(techs)
    countries = {cid: {"tag": c["tag"], "laws": frozenset(c["laws"]) & women_laws(),
                       "techs": acquired.get(cid, frozenset()), "at_war": False}
                 for cid, c in raw_countries.items()}
    states = {}
    for sid, st in raw_states.items():
        v = st["vars"]
        slots = None
        if ring and any(f"te_dg_f{k}" in v for k in range(P.RING_YEARS)):
            slots = {s: {k: v[f"te_dg_{s}{k}"] for k in range(P.RING_YEARS) if f"te_dg_{s}{k}" in v} for s in "fm"}
        fields = sections["states"].get(sid, {})
        states[sid] = {"owner": st["owner"], "region": fields.get("region", "").strip('"'),
                       "devastation": S._num(fields.get("devastation")), "vars": v, "ring": slots}
    year = year_of(path) if year_of else None
    return {"year": year, "states": states, "countries": countries, "techs_known": True}


def merge_years(saves):
    """One save a year, in date order: where a year has an extract_all.py JSON and a plain-text save, the JSON's states
    (and rings) with the plain save's technologies."""
    by_year = {}
    for save in saves:
        have = by_year.get(save["year"])
        if have is None:
            by_year[save["year"]] = save
            continue
        base, full = (have, save) if not have["techs_known"] else (save, have)
        if not full["techs_known"]:
            continue
        for cid, country in base["countries"].items():
            if cid in full["countries"]:
                country["techs"] = full["countries"][cid]["techs"]
        base["techs_known"] = True
        by_year[save["year"]] = base
    return [by_year[y] for y in sorted(by_year)]


def _transport_by_year(saves):
    """{year: {cid: transport techs}} from the saves that hold every technology."""
    return {s["year"]: {cid: c["techs"] & transport_techs() for cid, c in s["countries"].items()}
            for s in saves if s["techs_known"]}


def _transport(known, cid, year):
    years = [y for y in known if y <= year] or ([min(known)] if known else [])
    return known[max(years)].get(cid, frozenset()) if years else frozenset()


def inputs(rec, prev, country, year, known):
    """The model's Inputs for a state's step from its stored walk (and the step before's chain-migration count, which
    the profile read before the step counted this year). The profile's two types are the totals the laws' and
    technologies' lines give (migrant_lines)."""
    v = rec["vars"]
    laws = country["laws"] if country else frozenset()
    techs = (country["techs"] | _transport(known, rec["owner"], year)) if country else frozenset()
    mods = DM.totals(migrant_lines(), techs, laws, types=P.MIGRANT_PROFILE_TYPES)
    crisis = (rec.get("devastation", 0.0) / 100.0 + v.get("te_dg_in_turm", 0.0)
              + (P.CRISIS_AT_WAR if country and country["at_war"] else 0.0))
    return M.Inputs(sol=v.get("te_dg_sol", 8.0), literacy=v.get("te_dg_lit", 0.2),
                    urban_share=v.get("te_dg_urban_share", 0.1), laws=laws, techs=techs, mods=mods,
                    female_job_share=v.get("te_dg_fjob_share", 0.0), crisis=M.clamp(crisis, 0.0, 1.0),
                    inflow_years=int((prev or {}).get("vars", {}).get("te_dg_inflow_years", 0)),
                    wealth_tfr=v.get("te_dg_wtfr"), agrarian_share=v.get("te_dg_agr_share", 0.0))


def ring_from(rec):
    """The census's ring as the save holds it: the slots before their scale, the pool and its age."""
    v = rec["vars"]
    ring = M.Ring(year=int(v["te_dg_year"]))
    for s, slots in rec["ring"].items():
        side = ring.f if s == "f" else ring.m
        for k, value in slots.items():
            side[int(k)] = value
    ring.scale = v.get("te_dg_scale", 1.0)
    ring.pool_f, ring.pool_m, ring.pool_age = v.get("te_dg_pf", 0.0), v.get("te_dg_pm", 0.0), v.get("te_dg_pa", 150.0)
    M._refresh_denominators(ring)
    ring.total = ring.people()
    return ring


def figures(ring):
    f = M.consequence_figures(ring)
    return {"sb": f["sex_balance"], "T": f["term"], "youth": f["youth"], "people": f["people"], "fam": f["fam"]}


def saved_figures(rec):
    """The same figures from the census bands the save holds (the booking the run ran with), or None."""
    v = rec["vars"]
    bf = [v.get(f"te_dg_bf{b}", 0.0) for b in range(P.BANDS)]
    bm = [v.get(f"te_dg_bm{b}", 0.0) for b in range(P.BANDS)]
    people = sum(bf) + sum(bm)
    lo, hi = 20 // P.BAND_WIDTH, 60 // P.BAND_WIDTH
    women = sum(bf[lo:hi])
    if people <= 0 or women <= 0:
        return None
    plo, phi = P.POOL_FROM // P.BAND_WIDTH, (P.POOL_TO + 1) // P.BAND_WIDTH
    ylo, yhi = P.YOUTH_AGES[0] // P.BAND_WIDTH, (P.YOUTH_AGES[1] + 1) // P.BAND_WIDTH
    fam = sum(bm[plo:phi])
    return {"sb": 100 * sum(bm[lo:hi]) / women, "T": M.conscription_term(fam, people),
            "youth": (sum(bf[ylo:yhi]) + sum(bm[ylo:yhi])) / people, "people": people, "fam": fam}


class _ProfileOnly:
    """The booking before 2026-10-12, for the comparison: no cap and no correction of the labour kind's split."""

    def __enter__(self):
        self.kept = {k: getattr(P, k) for k in ("MIGRANT_CAP_IN", "MIGRANT_CAP_OUT", "LABOUR_BALANCE_LOW",
                                                "LABOUR_BALANCE_HIGH")}
        P.MIGRANT_CAP_IN = P.MIGRANT_CAP_OUT = float("inf")
        P.LABOUR_BALANCE_LOW, P.LABOUR_BALANCE_HIGH = (-1e9, -2e9), (1e9, 2e9)

    def __exit__(self, *exc):
        for k, v in self.kept.items():
            setattr(P, k, v)


def walk(saves, booked=True):
    """{sid: {year: figures}}: every census state re-walked through `saves` (read_save's, in date order). booked=False
    books by the profile alone (_ProfileOnly)."""
    if not booked:
        with _ProfileOnly():
            return walk(saves, booked=True)
    known = _transport_by_year(saves)
    out = {}
    sids = {sid for s in saves for sid in s["states"]}
    for sid in sids:
        ring, prev, res = None, None, {}
        for save in saves:
            rec = save["states"].get(sid)
            if rec is None:
                continue
            v = rec["vars"]
            if v.get("te_dg_year") is None or not v.get("te_dg_people"):
                prev = rec
                continue
            year, census_year = save["year"], int(v["te_dg_year"])
            country = save["countries"].get(rec["owner"])
            if ring is None:
                ring = ring_from(rec) if rec.get("ring") else M.seed(
                    inputs(rec, prev, country, year, known), census_year, v["te_dg_people"])
            elif census_year == ring.year + 1 and v.get("te_dg_stepped", 1) > 0:
                M.step(ring, inputs(rec, prev, country, year, known), census_year, engine_pop=v["te_dg_people"],
                       migration=booked_residual(v))
            elif census_year != ring.year:
                ring = M.seed(inputs(rec, prev, country, year, known), census_year, v["te_dg_people"])
            res[year] = figures(ring)
            prev = rec
        if res:
            out[sid] = res
    return out


def booked_residual(v):
    """The residual a step booked by the residual's profile: its net migration less Internal Resettlement's known moves
    (te_dg_rs_net, stored by a step that had them; demographics_resettle)."""
    return v.get("te_dg_net_migration", 0.0) - v.get("te_dg_rs_net", 0.0)


def band_summary(rows):
    """{n, fewer, more, either, sb_min, sb_max, term_past, term_far, term_min, term_max, youth_max, youth_over}: the
    consequences design's §5 bands on one year's figures (rows: [figures]). fewer/more: shares of states at the
    sex-balance effects (below SEX_FEWER_FROM, at SEX_MORE_FROM or more); term_past/far: people in states with |T| past
    0.05 and 0.15; youth_over: states above YOUTH_FROM aged 20-29 (no youth bulge without it)."""
    n = len(rows) or 1
    people = sum(r["people"] for r in rows) or 1.0
    fewer = sum(1 for r in rows if r["sb"] < P.SEX_FEWER_FROM) / n
    more = sum(1 for r in rows if r["sb"] >= P.SEX_MORE_FROM) / n
    return {"n": len(rows), "fewer": fewer, "more": more, "either": fewer + more,
            "sb_min": min((r["sb"] for r in rows), default=0.0), "sb_max": max((r["sb"] for r in rows), default=0.0),
            "term_past": sum(r["people"] for r in rows if abs(r["T"]) > 0.05) / people,
            "term_far": sum(r["people"] for r in rows if abs(r["T"]) > 0.15) / people,
            "term_min": min((r["T"] for r in rows), default=0.0), "term_max": max((r["T"] for r in rows), default=0.0),
            "youth_max": max((r["youth"] for r in rows), default=0.0),
            "youth_over": sum(1 for r in rows if r["youth"] > P.YOUTH_FROM) / n}


def country_terms(walked, saves, tags, years):
    """{tag: {year: T}}: each country's conscription term from its census states' pools (the country's figure)."""
    by_year = {s["year"]: s for s in saves}
    out = {}
    for tag in tags:
        for year in years:
            save = by_year.get(year)
            if save is None:
                continue
            fam = people = 0.0
            for sid, res in walked.items():
                rec = save["states"].get(sid)
                country = save["countries"].get(rec["owner"]) if rec else None
                if country and country["tag"] == tag and year in res:
                    fam += res[year]["fam"]
                    people += res[year]["people"]
            if people:
                out.setdefault(tag, {})[year] = M.conscription_term(fam, people)
    return out


def fidelity(walked, saves, year):
    """(median, 5th, 95th percentile of the re-walk's sex balance less the save's, share of states outside 90-110 in
    the save, in the re-walk): how well the re-walk with the run's own booking reproduces the run."""
    save = next((s for s in saves if s["year"] == year), None)
    if save is None:
        return None
    diffs, out_save, out_walk = [], 0, 0
    for sid, res in walked.items():
        rec = save["states"].get(sid)
        got = saved_figures(rec) if rec else None
        if got is None or year not in res:
            continue
        diffs.append(res[year]["sb"] - got["sb"])
        out_save += not (P.SEX_FEWER_FROM <= got["sb"] < P.SEX_MORE_FROM)
        out_walk += not (P.SEX_FEWER_FROM <= res[year]["sb"] < P.SEX_MORE_FROM)
    if not diffs:
        return None
    diffs.sort()

    def q(p):
        return diffs[int(p * (len(diffs) - 1))]
    return q(0.5), q(0.05), q(0.95), out_save / len(diffs), out_walk / len(diffs)
