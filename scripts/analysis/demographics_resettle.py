#!/usr/bin/env python3
"""Internal Resettlement's known moves in the census, and the US frontier's 1836 seed (2026-10-19).

The twin of common/scripted_effects/te_demog_resettle_effects.txt and the generated
te_demog_resettle_generated_effects.txt (scripts/generators/gen_demographics_resettle.py). Spec: the master spec
(docs/superpowers/specs/2026-10-08-demographics-design.md) §2.5 "Known kills" and §2.6.

Known moves. A Settlement Authority's monthly walk moves people with move_partial_pop and kills its coercive
programmes' dead in transit at the source. The census books both by the programme's own profile (RESETTLE_PROFILES:
kinds over MIGRANT_CLASSES, or Rustication's ages 15-24 by single year), the same at the source and the destination:
- book() adds a month's movers to a state's counters, by class and sex, as the walk does;
- the yearly step takes the counters (known_rates), adds each class's arrivals and takes its departures at the rate
  their counts give over the class's people, and takes the moves out of the migration residual (residual_rest), so the
  residual holds only the rest. The transit dead are known kills (te_demog_note_kills), but leave by the profile, not
  from every age: the step's uniform kill rate leaves them out (Known.dead).
- A known move bypasses the residual's caps (MIGRANT_CAP_IN, _OUT) and its balance ramps: it is a count. It keeps the
  sweep's guard (a cohort gives at most half of what is left of it).

The US frontier. At the 1836 seed the states the US holds in FRONTIER_1836's state regions start with the 1840
census's male surplus among their settlers (frontier_seed): the seed's men at each age group's ages are its women times
the group's ratio, and the ring is rescaled to the state's people, so the total stays as seeded. The seed then ages
normally.
"""

from dataclasses import dataclass, field

import demographics_model as M
import demographics_params as P

SEXES = ("f", "m")
N_CLASSES = len(P.MIGRANT_CLASSES)


def kind_weights(kind):
    """A kind's weights over MIGRANT_CLASSES: MIGRANT_PROFILE's or RESETTLE_KINDS'."""
    if kind in P.MIGRANT_PROFILE:
        return P.MIGRANT_PROFILE[kind]["weights"]
    return P.RESETTLE_KINDS[kind]["weights"]


def kind_women(kind):
    """A kind's own women's share: half for the family and refugee kinds, RESETTLE_KINDS' for the programmes' own."""
    if kind in P.RESETTLE_KINDS:
        return P.RESETTLE_KINDS[kind]["women"]
    return 0.5


def labour_female_share(female_job_share, female_work_share):
    """The labour kind's women's share at a destination by its jobs, as the residual's labour kind takes it before the
    balance ramp (demographics_model.migrant_profile; the script's te_demog_rs_labour_f)."""
    rights = female_work_share / max(P.FULL_FEMALE_WORK_SHARE, 0.01)
    lo, hi = P.LABOUR_FEMALE_SHARE_MIN, P.LABOUR_FEMALE_SHARE_MAX
    return M.clamp((hi - lo) * female_job_share * rights + lo, lo, hi)


def programme_shares(programme, labour_f=P.LABOUR_FEMALE_SHARE_MIN):
    """{(class, sex): share} and {("youth", sex): share} of a programme's movers, summing to 1. labour_f: the
    destination's jobs' women's share, for a part whose share is "jobs" (the Development Program's labour)."""
    out = {}
    for kind, weight, women in P.RESETTLE_PROFILES[programme]:
        w = kind_women(kind) if women is None else (labour_f if women == "jobs" else women)
        if kind == "youth":
            for s, sh in (("f", w), ("m", 1 - w)):
                out[("youth", s)] = out.get(("youth", s), 0.0) + weight * sh
            continue
        for c, cw in enumerate(kind_weights(kind)):
            for s, sh in (("f", w), ("m", 1 - w)):
                if cw * sh:
                    out[(c, s)] = out.get((c, s), 0.0) + weight * cw * sh
    return out


@dataclass
class Counters:
    """A state's counters since its last census step: movers by (class, sex) and ("youth", sex) arriving (inn) and
    leaving (out, the transit dead included), the moved people in and out, and the transit dead (te_dg_rs_*)."""
    inn: dict = field(default_factory=dict)
    out: dict = field(default_factory=dict)
    moved_in: float = 0.0
    moved_out: float = 0.0
    dead: float = 0.0

    def any(self):
        return bool(self.moved_in or self.moved_out or self.dead)


def book(counters, programme, people, side, labour_f=P.LABOUR_FEMALE_SHARE_MIN, dead=False):
    """Add `people` of a programme's movers to a state's counters (te_demog_rs_note_move, te_demog_rs_note_dead):
    side "in" at the destination, "out" at the source; dead=True for the transit dead (at the source)."""
    target = counters.inn if side == "in" else counters.out
    for k, sh in programme_shares(programme, labour_f).items():
        target[k] = target.get(k, 0.0) + people * sh
    if dead:
        counters.dead += people
    elif side == "in":
        counters.moved_in += people
    else:
        counters.moved_out += people


def youth_people(ring):
    """Women and men at the youth's ages now (next step's rate ages): the script's te_dg_bf3 + te_dg_bf4."""
    lo, hi = P.RESETTLE_KINDS["youth"]["ages"]
    rows = [(f, m) for a, f, m in ring.by_age() if lo <= a <= hi]
    return {"f": sum(f for f, _m in rows), "m": sum(m for _f, m in rows)}


@dataclass
class Known:
    """A step's known moves as rates (te_demog_rs_known_rates): per (class, sex) the share of each cohort that arrives
    (gain) and leaves (frac), the flat rates over every class with people, the youth's own rates at ages 15-24, and the
    transit dead the uniform kill rate leaves out."""
    gain: dict
    frac: dict
    youth_gain: dict
    youth_frac: dict
    flat_gain: float
    flat_frac: float
    has_people: dict
    dead: float

    def rates(self, c, r, s):
        """(gain, frac) for a cohort of class c and sex s at rate age r (te_demog_rs_enter_class)."""
        if not self.has_people[(c, s)]:
            return 0.0, 0.0
        g, d = self.gain[(c, s)] + self.flat_gain, self.frac[(c, s)] + self.flat_frac
        lo, hi = P.RESETTLE_KINDS["youth"]["ages"]
        if lo <= r <= hi:
            g += self.youth_gain[s]
            d += self.youth_frac[s]
        return g, d


def known_rates(ring, counters):
    """The step's Known from a state's counters and its ring's class sums (last year's: the residual's denominators)."""
    sums = {"f": ring.class_f, "m": ring.class_m}
    youth = youth_people(ring)
    has = {(c, s): sums[s][c] >= 1 for c in range(N_CLASSES) for s in SEXES}
    everyone = sum(sums[s][c] for (c, s), ok in has.items() if ok)
    rates, left = {}, {}
    for side, amounts in (("in", counters.inn), ("out", counters.out)):
        per, rest = {}, 0.0
        for c in range(N_CLASSES):
            for s in SEXES:
                a = amounts.get((c, s), 0.0)
                if has[(c, s)]:
                    per[(c, s)] = a / sums[s][c]
                else:
                    per[(c, s)] = 0.0
                    rest += a
        yr = {}
        for s in SEXES:
            a = amounts.get(("youth", s), 0.0)
            if youth[s] >= 1:
                yr[s] = a / youth[s]
            else:
                yr[s] = 0.0
                rest += a
        rates[side] = (per, yr)
        left[side] = rest / everyone if everyone >= 1 else 0.0
    return Known(gain=rates["in"][0], frac=rates["out"][0], youth_gain=rates["in"][1], youth_frac=rates["out"][1],
                 flat_gain=left["in"], flat_frac=left["out"], has_people=has, dead=counters.dead)


def residual_rest(residual, counters):
    """The migration residual less the known moves (te_demog_flows): what the residual's profile books."""
    return residual - counters.moved_in + counters.moved_out


def banded(residual, people):
    """The noise rule (te_demog_flows): a residual inside RESIDUAL_NOISE_SHARE of the people is model error, 0."""
    return 0.0 if abs(residual) < P.RESIDUAL_NOISE_SHARE * people else residual


def step(ring, inp, year, counters=None, engine_pop=None, war_dead=0.0, kills=0.0, residual=0.0, **kw):
    """demographics_model.step as te_demog_step runs it, with a state's known moves: `kills` every kill the mod noted
    (the transit dead included, as te_dg_kills_in holds them), `residual` the whole residual before the noise rule (the
    change less natural change, war dead and kills). The known moves come out of it and are booked by their profiles;
    the noise rule applies to the rest. No counters: the plain step. Returns (figures, the rest after the noise rule,
    the panel's net migration)."""
    if counters is None or not counters.any():
        rest = banded(residual, ring.total)
        return M.step(ring, inp, year, engine_pop=engine_pop, war_dead=war_dead, kills=kills, migration=rest, **kw), \
            rest, rest
    known = known_rates(ring, counters)
    rest = banded(residual_rest(residual, counters), ring.total)
    figures = M.step(ring, inp, year, engine_pop=engine_pop, war_dead=war_dead, kills=kills, migration=rest,
                     known=known, **kw)
    return figures, rest, rest + counters.moved_in - counters.moved_out


# ---- The US frontier at the 1836 seed -------------------------------------------------------------------------------

def frontier_ratio(region, age):
    """Men per woman the seed gives a FRONTIER_1836 state region's people at `age`, or None outside its ages."""
    row = P.FRONTIER_1836.get(region)
    if row is None:
        return None
    for (lo, hi), ratio in row["ratios"].items():
        if lo <= age <= hi:
            return ratio
    return None


def frontier_seed(inp, year, engine_pop, region):
    """demographics_model.seed with the frontier's men (te_demog_frontier_slot): at each of the table's ages a cohort's
    men are its women x the ratio, then the ring is rescaled to engine_pop, as the script's normalisation does."""
    ring = M.seed(inp, year, engine_pop)
    if region not in P.FRONTIER_1836:
        return ring
    for a in range(M.N):
        r = frontier_ratio(region, a)
        if r is not None:
            k = (year - a) % M.N
            ring.m[k] = ring.f[k] * r
    raw = sum(ring.f) + sum(ring.m)
    ring.scale = engine_pop / raw if raw > 0 else 1.0
    M._refresh_denominators(ring)
    ring.total = engine_pop
    return ring


def men_per_100(ring, lo=0, hi=150):
    rows = [(f, m) for a, f, m in ring.by_age() if lo <= a <= hi]
    f = sum(f for f, _m in rows)
    return 100.0 * sum(m for _f, m in rows) / f if f else 0.0


# ---- The harness's subcommands (demographics_harness.py frontier, resettle) ----------------------------------------

# A stand-in 1836 US frontier state: poor, half literate, rural, with the US's 1836 women's-rights law.
FRONTIER_STAND_IN = dict(sol=10, literacy=0.5, urban_share=0.05, laws=frozenset({"law_no_womens_rights"}))


def _stand_in(**kw):
    import demographics_modifiers as DM
    base = {**FRONTIER_STAND_IN, **kw}
    inp = M.Inputs(**base)
    inp.mods = DM.totals(DM.load_carriers(), inp.techs, inp.laws, inp.institutions)
    return inp


def full_effects(ring):
    """Phase 2 step 4's Full-mode effects a ring's structure sets (demographics_model.consequence_figures): radicals from
    movements from More Men (SEX_RADICALS x more), Fewer Men's children per woman, the conscription term, the share
    aged 20-29 and the youth bulge's y at YOUTH_UNEMPLOYMENT_FULL (work short)."""
    c = M.consequence_figures(ring, unemployment=P.YOUTH_UNEMPLOYMENT_FULL)
    return {"more_radicals": P.SEX_RADICALS * c["more"], "fewer": c["fewer"], "births": c["births"],
            "term": M.conscription_applied(c["term"]), "youth": c["youth"], "y": M.youth_applied(c["y"])}


def frontier_rows(inp=None, years=(0, 10, 25, 50), people=100000.0):
    """[(region, {years on: {"20-59": men per 100 women aged 20-59, "15-49", "all", "0-14", "full": full_effects}})]:
    each frontier region's 1836 seed, then plain steps (no migration) as the ring ages."""
    inp = inp or _stand_in()
    out = []
    for region in sorted(P.FRONTIER_1836):
        ring = frontier_seed(inp, 1836, people, region)
        figs, year = {}, 1836
        for target in years:
            while year < 1836 + target:
                year += 1
                M.step(ring, inp, year)
            figs[target] = {"20-59": men_per_100(ring, 20, 59), "15-49": men_per_100(ring, 15, 49),
                            "all": men_per_100(ring), "0-14": men_per_100(ring, 0, 14), "full": full_effects(ring)}
        out.append((region, figs))
    return out


def known_rows(inp=None, years=10, arrivals=10000.0, destination=100000.0, source=1000000.0, mortality=None):
    """[(programme, destination figures, source figures)] after `years` years of a programme moving `arrivals` people
    a year from a source to a destination (both at the stand-in's equilibrium), its transit dead at the walk's
    mortality (the registry's 5%, 15%, 1%), no other migration: men per 100 women aged 20-59 and the median age."""
    inp = inp or _stand_in()
    mortality = mortality or {"penal_transportation": 0.05, "special_settlements": 0.15, "rustication": 0.01}
    lf = labour_female_share(inp.female_job_share, M.female_work_share(inp))
    out = []
    for programme in P.RESETTLE_PROGRAMMES:
        dest, src = M.seed(inp, 1836, destination), M.seed(inp, 1836, source)
        moved = arrivals
        dead = arrivals * mortality.get(programme, 0.0) / (1 - mortality.get(programme, 0.0))
        for y in range(1837, 1837 + years):
            cd, cs = Counters(), Counters()
            book(cd, programme, moved, "in", lf)
            book(cs, programme, moved, "out", lf)
            if dead:
                book(cs, programme, dead, "out", lf, dead=True)
            # no engine population: the ring's own count carries the moves (the residual is all known)
            step(dest, inp, y, cd, kills=0.0, residual=moved)
            step(src, inp, y, cs, kills=dead, residual=-moved)
        out.append((programme, {**M.structure(dest), **full_effects(dest)}, {**M.structure(src), **full_effects(src)}))
    return out


def cmd_frontier(_args):
    print("The US frontier's 1836 seed: men per 100 women by age (demographics_params.FRONTIER_1836), then ageing")
    print("with no migration. A stand-in frontier state: SoL 10, literacy 0.5, No Women's Rights.")
    print("Under Full the census's consequence modifiers follow: More Men's radicals from movements, the conscription term")
    print("(no ceiling) and the share aged 20-29 with the youth bulge's y where a fifth of the workforce has no work.")
    print(f"{'region':18} {'years':>5} {'0-14':>6} {'15-49':>6} {'20-59':>6} {'all':>6} {'radicals':>8} {'consc':>7} "
          f"{'20-29':>6} {'y':>5}")
    for region, figs in frontier_rows():
        for years, f in figs.items():
            e = f["full"]
            print(f"{region:18} {years:>5} {f['0-14']:6.1f} {f['15-49']:6.1f} {f['20-59']:6.1f} {f['all']:6.1f} "
                  f"{e['more_radicals']:+8.1%} {e['term']:+7.1%} {e['youth']:6.3f} {e['y']:5.2f}")
    return 0


def cmd_resettle(args):
    print(f"Internal Resettlement's known moves: {args.arrivals:,.0f} people a year for {args.years} years from a source")
    print(f"of {args.source:,.0f} to a destination of {args.destination:,.0f} (the stand-in state at equilibrium, no")
    print("other migration): men per 100 women aged 20-59 and the median age at both ends.")
    print("Under Full: the conscription term, More Men's radicals and Fewer Men's children-per-woman factor at each end.")
    print(f"{'programme':24} {'dest m/100f':>11} {'median':>6} {'consc':>7} {'radicals':>8} | {'src m/100f':>10} "
          f"{'median':>6} {'consc':>7} {'tfr x':>6}")
    for programme, d, s in known_rows(years=args.years, arrivals=args.arrivals, destination=args.destination,
                                      source=args.source):
        print(f"{programme:24} {d['men_per_100_women']:11.1f} {d['median']:6.1f} {d['term']:+7.1%} "
              f"{d['more_radicals']:+8.1%} | {s['men_per_100_women']:10.1f} {s['median']:6.1f} {s['term']:+7.1%} "
              f"{s['births']:6.2f}")
    return 0
