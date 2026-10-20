"""The late game's scenarios (demographics_harness.py lategame; docs/superpowers/archive/specs/2026-10-11-demographics-late-game-design.md).

One rich state from today's stable structure at 1.6 children per woman (the design's sketch, now the census's own model
with phase 3's biological age), run to 2300 under each era ladder and under Biological Immortality, and judged against
the design's sketched figures (§1-§3): the steady life tables (§1.2, §1.5), the 60-year projections (Context's table),
immortality's growth and the bounded lifetime births (§3.3), who is treated against the per-cohort truth (§1.3), and the
late check of adult external and work mortality (§1.4, call 20). One pass; "close enough" is the owner's bar.
"""

import copy
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import demographics_model as M  # noqa: E402
import demographics_modifiers as DM  # noqa: E402
import demographics_params as P  # noqa: E402

N = P.RING_YEARS
TFR = 1.6
YEAR0, YEAR_END = 2020, 2300
MILESTONES = (30, 50, 60, 100, YEAR_END - YEAR0)
# today's rich state: the medicine scenarios' Rich today (health law, institutions) with the workforce scenarios' laws
# (2026-10-16: with the Combustion Engine's traffic and modern safety's era 7-9 carriers, which a state of 2020 holds,
# and the Ministry of Public Safety at 5, whose levels lower deaths from violence since the same day; #1045: with
# Pharmaceuticals, the era 2 technology every later medical one stands on, whose infection treatment it lacked)
_RICH_TECHS = frozenset({"medical_degrees", "pharmaceuticals", "modern_nursing", "antibiotics", "modern_vaccines",
                         "antibiotic_mass_production",
                         "contraceptive_pill", "modern_pharmaceuticals", "vulcanization", "feminism",
                         "second_wave_feminism", "personal_appliances", "telemedicine", "combustion_engine",
                         "prefabricated_construction", "modern_urban_planning", "robotics", "containerization",
                         "computer_aided_design", "cellular_networks", "knowledge_economy"})
_RICH_LAWS = frozenset({"law_protected_class", "law_compulsory_primary_school", "law_old_age_pension",
                        "law_public_health_insurance", "law_dedicated_police", "law_worker_protections"})
_RICH_INSTITUTIONS = {"institution_health_system": 9, "institution_workplace_safety": 5,
                      "institution_ministry_of_consumer_protection": 4, "institution_social_security": 5,
                      "institution_police": 5}
ERA10 = frozenset({"mrna_therapeutics"})
ERA11 = ERA10 | {"personalized_medicine", "genetic_engineering", "synthetic_biology"}
ERA12 = ERA11 | {"biological_immortality", "advanced_nanofabrication"}   # nanomedicine's infection line (#1045)
# everyone within reach (the design's "everyone treated"): the public route at full access, a rich wealth band
EVERYONE = dict(wealth_bands={30: 1.0}, lx_w=float(P.LX_MARKET_START))


def _carriers():
    return DM.load_carriers(), DM.workforce_line_carriers()


def inputs(carriers, lines, techs=frozenset(), laws=(), drop_laws=(), ageing=None, **kw):
    """The rich state's inputs with extra technologies and laws; ageing overrides the ageing type's total (a counterfactual
    rate). wealth_tfr is set so children per woman are TFR (the design's 1.6)."""
    t = _RICH_TECHS | set(techs)
    lw = (_RICH_LAWS | set(laws)) - set(drop_laws)
    inst = dict(_RICH_INSTITUTIONS)
    mods = {**DM.totals(carriers, t, lw, inst),
            **DM.totals(lines, t, lw, inst, types=tuple(P.WORKFORCE_LINE_TYPES.values()))}
    if ageing is not None:
        mods[P.AGEING_RATE_TYPE] = ageing - 1.0
    inp = M.Inputs(sol=40, literacy=0.99, urban_share=0.8, techs=frozenset(t), laws=frozenset(lw), institutions=inst,
                   mods=mods, low_share=0.4, **{**EVERYONE, **kw})
    qf, qm, _ = M.group_rates(inp)
    e0 = (M.life_table(qf)["e0"] + M.life_table(qm)["e0"]) / 2
    fert = M.fertility(inp, e0)
    return dataclasses.replace(inp, wealth_tfr=fert["wealth"] * TFR / fert["tfr"])


def start_ring(inp):
    """Today's stable structure of the rich state at TFR children per woman (no carrier), 1,000,000 people."""
    ring, _ = M.run_constant(inp, years=300, year0=YEAR0 - 300)
    total = ring.people()
    ring.f = [x * 1_000_000 / total for x in ring.f]
    ring.m = [x * 1_000_000 / total for x in ring.m]
    ring.pool_f *= 1_000_000 / total
    ring.pool_m *= 1_000_000 / total
    M._refresh_denominators(ring)
    ring.total = ring.people()
    return ring


class _Lifetime:
    """Children so far per woman by birth cohort (§3.3's bound): each step's births from a slot over its women, summed over
    the cohort's life (demographics_model.lx_births, recorded)."""

    def __init__(self, start=None):
        self.born = {}           # birth year -> children per woman so far
        self._orig = M.lx_births
        if start is not None:
            # the cohorts alive at the start: their children so far at the start's TFR, timed by today's shape
            for a in range(N):
                self.born[start.year - a] = TFR * sum(M.asfr_shape(x) for x in range(min(a, 50))) / 100000.0

    def __enter__(self):
        def rec(lx, ring, k, r, f, m, tfr, planned_share):
            out = self._orig(lx, ring, k, r, f, m, tfr, planned_share)
            if f > 0:
                birth_year = ring.year + 1 - (r + 1)
                self.born[birth_year] = self.born.get(birth_year, 0.0) + out[0] / f
            return out
        M.lx_births = rec
        return self

    def __exit__(self, *exc):
        M.lx_births = self._orig


def figures(ring, inp, out, people0):
    """A scenario's figures after a step: people over the start, births and deaths per 1,000, the calendar 65+ share, the mean
    calendar and biological ages, health need (x 1836's), the workforce share (workers over people) under Old Age Pension
    at 65 and with no pension law, Living to 100 and Old age from (the state's blend and the untreated's), the pool."""
    people = ring.people()
    s = M.structure(ring)
    qf, qm, _ = M.group_rates(dataclasses.replace(inp, medicine=ring.medicine))
    old = M.old_age(qf, qm)
    with_pension = M.work_figures(ring, inp, old)
    no_pension = M.work_figures(ring, dataclasses.replace(inp, laws=inp.laws - {P.PENSION_LAW}), old)
    lx = out.get("lx") or {}
    plain_l100 = (M.survivors_at(qf, P.LX_LIVING_TO) + M.survivors_at(qm, P.LX_LIVING_TO)) / 2
    blend = lx.get("blend", {"l100": plain_l100})
    untreated = lx.get("untreated", {})
    return {"people": people / people0, "cbr": 1000 * out["births"] / people, "cdr": 1000 * out["deaths"] / people,
            "old65": s["old"], "mean_age": lx.get("mean_age"), "mean_bio": lx.get("mean_bio"),
            "need": with_pension["need"], "wf_pension": with_pension["wa_share"] * with_pension["at_work"],
            "wf_none": no_pension["wa_share"] * no_pension["at_work"],
            "e0": blend.get("e0", out["e0"]), "l100": blend.get("l100"), "l100t": lx.get("treated", {}).get("l100"),
            "l100u": untreated.get("l100"), "old_age": blend.get("old_age", old), "old_age_c": untreated.get("old_age"),
            "pool": (ring.pool_f + ring.pool_m) * ring.scale / people, "elig": lx.get("elig")}


def project(ring, schedule, years=YEAR_END - YEAR0, milestones=MILESTONES):
    """Step `ring` with schedule(t) -> Inputs for t = 0 .. years - 1; {t: figures} at the milestones (years since the start),
    and the lifetime births of women aged 100 at each milestone."""
    people0 = ring.people()
    rows = {}
    with _Lifetime(ring) as life:
        for t in range(years):
            inp = schedule(t)
            out = M.step(ring, inp, ring.year + 1)
            if t + 1 in milestones:
                row = figures(ring, inp, out, people0)
                row["lifetime_100"] = life.born.get(ring.year - 100)
                rows[t + 1] = row
    return rows


def scenarios_base(carriers, lines):
    """The start: the rich state today (no carrier), whose stable structure every scenario starts from."""
    return inputs(carriers, lines)


def scenarios(carriers=None, lines=None):
    """[(name, schedule(t) -> Inputs)] (§8.2's ladders and immortality; everyone within reach)."""
    carriers, lines = _carriers() if carriers is None else (carriers, lines)
    base = inputs(carriers, lines)
    era10 = inputs(carriers, lines, ERA10)
    era11 = inputs(carriers, lines, ERA11, laws={"law_medical_augmentation_only"})
    era11_no_slowing = inputs(carriers, lines, ERA11, laws={"law_medical_augmentation_only"}, ageing=1.0)
    era12 = inputs(carriers, lines, ERA12, laws={"law_medical_augmentation_only"})
    return [
        ("No change", lambda t: base),
        ("Era 11 medicine, no slowing", lambda t: era11_no_slowing),
        ("Era 10 (ageing 0.9)", lambda t: era10),
        ("Era 10 for 20 years, then era 11 (0.70)", lambda t: era10 if t < 20 else era11),
        ("Immortality (pull 3%) from today", lambda t: era12),
        ("The ladder: era 10, era 11 at 20 years, immortality at 40", lambda t: era10 if t < 20 else era11 if t < 40
         else era12),
    ]


# §1.2's and §1.5's steady life tables (sketch; everyone treated, Rich-today medicine): e0, Living to 100, old age from
# (women and men averaged). The census's own tables reach these at the steady state of the ladder's rates.
# #1045 moved them: the rich state gained Pharmaceuticals' infection treatment (it had lacked it, so its infants died at
# twice the Rich today anchor's rate), adults' infection fell to the rich world's, and eras 11-12 took infection below it.
# Together about +2 years of e0 today and at eras 10-11 (Rich today 80.3, the rich world's 80-84), +3 at ageing 0.70,
# and +0.05 of Living to 100 under immortality: the e0 bands move up 2 years, Ageing 0.70's 3, immortality's Living to
# 100 0.05.
# 2026-10-20 (owner): chronic treatment to 0.99, Genetic Engineering 0.05 in era 11 and 0.12 each on Molecular Assemblers
# and Biological Immortality in era 12, and the life tables' open last interval. Era 11's chronic treatment rises from
# 0.80 to 0.85 (with Medical Augmentation Only), a quarter fewer chronic deaths: era 11 medicine +4.4 years of e0 (92.5 to
# 96.9), +0.10 of Living to 100, +7.5 years of Old age from; Ageing 0.70 +5.3 years (the tail 0.5 of them), +0.04;
# immortality's Living to 100 +0.016 and e0 141 (cut at 150) to about 1,700 (1,280 of it the tail alone). The bands the
# figures left move with them, their widths kept; immortality's e0 gains a band. The accidents floor's removal moves
# nothing here (the rich state's lines stay above it).
STEADY = [  # (name, scenario, years, {figure: (lo, hi)})
    ("Rich today", "No change", 60, {"e0": (77, 82), "l100": (0.05, 0.13), "old_age": (73, 77)}),
    ("Era 10, ageing 0.9, everyone treated", "Era 10 (ageing 0.9)", 280,
     {"e0": (81, 87), "l100": (0.17, 0.30), "old_age": (80, 85)}),
    ("Era 11 medicine, no slowing", "Era 11 medicine, no slowing", 280,
     {"e0": (90, 99), "l100": (0.38, 0.52), "old_age": (93, 100)}),
    # the sketch's bands were for 0.75 (e0 103, Living to 100 67%, old age 117/110); era 11 reaches 0.70 since 2026-10-16
    # (Synthetic Biology), which moves the census's own tables by about +4.5 years of e0, +0.04 and +6 years: the bands
    # move with them
    ("Ageing 0.70", "Era 10 for 20 years, then era 11 (0.70)", 280,
     {"e0": (109, 124), "l100": (0.62, 0.84), "old_age": (113, 126)}),
    ("Immortality", "Immortality (pull 3%) from today", 280,
     {"e0": (1200, 2400), "l100": (0.79, 0.95), "old_age": (P.LX_OLD_AGE_NONE, 150)}),
]
# The design's 60-year projections (Context's table; sketch), at 60 years: people, the calendar 65+ share, the mean
# biological age, health need, the workforce with a pension at 65 and with none. Wide bands: the sketch's workforce used
# a flat women's rate and capacity table that phase 2 step 2 fitted since, and its need weights a 0.97 reference. The
# workforce is in the game's units since 2026-10-20 (demographics_params.MEN_RATE): the sketch's 0.65-0.85 x 0.7.
PROJECTION = [  # (scenario, {figure: (lo, hi)})
    ("No change", {"people": (0.50, 0.65), "old65": (0.25, 0.37), "need": (1.5, 1.95)}),
    ("Era 11 medicine, no slowing", {"people": (0.60, 0.78), "old65": (0.35, 0.50), "need": (1.85, 2.40)}),
    ("Era 10 (ageing 0.9)", {"people": (0.54, 0.70), "old65": (0.30, 0.42), "need": (1.45, 1.95)}),
    # 2026-10-20: era 11's chronic treatment (STEADY's note) adds 0.03 to the people at 60 years, immortality's era 12 lines
    # 0.07 (0.06 at 50): the bands they left move with them
    ("Era 10 for 20 years, then era 11 (0.70)", {"people": (0.68, 0.88), "old65": (0.40, 0.56), "need": (1.6, 2.15)}),
    # the sketch's row timed every birth by the calendar (x1.19, 67% over 65); the census times unplanned births by the
    # body (call 5), which §3.3 puts at x1.30 in 50 years: more children, so more people and a younger calendar structure
    # #1045's fewer deaths (STEADY's note) add about 0.06 to the people at 60 years and 0.05 at 50: the tops move with them
    ("Immortality (pull 3%) from today", {"people": (1.17, 1.67), "old65": (0.45, 0.75), "mean_bio": (26, 36),
                                          "need": (0.65, 1.0), "wf_none": (0.455, 0.595)}),
]
# §3.3: under immortality, everyone treated, 50 years from today's structure: people x1.17 (every birth by the calendar) to
# x1.30 (the split at means 0.9); the women aged 100's children so far 1.6 to about 2.
IMMORTAL_50 = {"people": (1.18, 1.51), "lifetime_100": (1.6, 2.1)}   # people: 2026-10-20's era 12 lines, +0.06


def judge(name, row, bands):
    parts, bad = [], 0
    for k, (lo, hi) in bands.items():
        v = row.get(k)
        if v is None:
            parts.append(f"{k} n/a")
            bad += 1
            continue
        ok = lo <= v <= hi
        bad += not ok
        parts.append(f"{k} {v:.3g} [{lo:g}-{hi:g}]{'' if ok else ' OUT'}")
    print(f"  {name:58s} " + "  ".join(parts))
    return bad


# ---- §1.3: who is treated, the band model against the per-cohort truth ------------------------------------------------
# Era 11 medicine's rates, a constant share treated from year 0 (and of each cohort joining at 25), year 50: deaths per
# 1,000 and people over the start. The truth tracks every cohort's treated, formerly treated and untreated apart (the
# design's review); the census keeps a share and a deficit per five-year band. §1.3's table (sketch): within 0.1 per 1,000.
TRUTH_CASES = [  # (name, technologies, share treated)
    ("Immortality, 20% treated", ERA12, 0.2),
    ("Immortality, 50% treated", ERA12, 0.5),
    ("Immortality, 90% treated", ERA12, 0.9),
    ("Era 11 (r 0.70), 50% treated", ERA11, 0.5),
]
TRUTH_TOLERANCE = 0.5      # deaths per 1,000; the multiple within 2%


def _share_inputs(carriers, lines, techs, share):
    """The rich state's era-11 inputs with a constant share of its people within reach: no public route (Private Health
    Insurance), a market threshold between a poor band (out of reach) and a rich one (in)."""
    return inputs(carriers, lines, techs, laws={"law_medical_augmentation_only", "law_private_health_insurance"},
                  drop_laws={"law_public_health_insurance"}, wealth_bands={1: 1 - share, 40: share}, lx_w=100.0)


def band_model(inp, share, start, years=50):
    """The census's model from `start` (today's ring, deep-copied) with `share` treated from year 0 and no deficit."""
    ring = copy.deepcopy(start)
    ring.medicine = None              # medicine at its targets from year 0, as the truth takes it
    ring.lx_elig, ring.lx_cover, ring.lx_sbar = share, 1.0, share
    for j in range(P.LX_BANDS):
        if (ring.year - P.LX_BAND_WIDTH * j) % N >= P.LX_JOIN_AGE:
            ring.lx_s[j], ring.lx_d[j] = share, 0.0
    people0 = ring.people()
    out = None
    for _t in range(years):
        out = M.step(ring, inp, ring.year + 1)
    return 1000 * out["deaths"] / ring.people(), ring.people() / people0


def truth(inp, share, start, years=50, ages=400):
    """Every cohort and sex: treated in care T, untreated U (no one leaves care at a constant share), the treated body's
    age per cohort; deaths at each part's rates, births by the census's rule (planned by the calendar as intended x the
    body's fecundity, unplanned by the body), the cohort turning 25 at the share."""
    qf, qm, mmr = M.group_rates(inp)
    q = {"f": qf, "m": qm}
    rr, pull = M.ageing_rate(inp), M.rejuvenation(inp)
    P_ = {"f": [0.0] * ages, "m": [0.0] * ages}
    for a, f, m in start.by_age()[:-1]:
        P_["f"][a], P_["m"][a] = f, m
    T = {sx: [x * share if a >= P.LX_JOIN_AGE else 0.0 for a, x in enumerate(P_[sx])] for sx in "fm"}
    body = [float(a) for a in range(ages)]
    e0 = (M.life_table(qf)["e0"] + M.life_table(qm)["e0"]) / 2
    fert = M.fertility(inp, e0)
    tfr, planned = fert["tfr"], fert["planned"] / fert["tfr"]
    people0 = sum(P_["f"]) + sum(P_["m"])
    deaths = 0.0
    for _t in range(years):
        births = deaths = 0.0
        nP = {sx: [0.0] * ages for sx in "fm"}
        nT = {sx: [0.0] * ages for sx in "fm"}
        nbody = [0.0] * ages
        for a in range(ages - 1):
            bt = body[a]
            tf, uf = T["f"][a], P_["f"][a] - T["f"][a]
            b_u = uf * tfr / 1e5 * (planned * M.asfr_planned(a) + (1 - planned) * M.asfr_unplanned(a))
            b_t = tf * tfr / 1e5 * (planned * M.intended(a) * M.fecundity(bt) + (1 - planned) * M.asfr_unplanned(bt))
            births += b_u + b_t
            for sx in "fm":
                tt, uu = T[sx][a], P_[sx][a] - T[sx][a]
                qt, qu = q[sx][P.group_of(bt)] / 1e5, q[sx][P.group_of(a)] / 1e5
                mat = (b_u * mmr / 1e5, b_t * mmr / 1e5) if sx == "f" else (0.0, 0.0)
                t2 = tt * (1 - qt) - mat[1]
                u2 = uu * (1 - qu) - mat[0]
                deaths += (tt - t2) + (uu - u2)
                nT[sx][a + 1] = max(t2, 0.0)
                nP[sx][a + 1] = max(t2, 0.0) + max(u2, 0.0)
            if a + 1 > P.LX_JOIN_AGE:
                nb = bt + rr
                if pull and nb > P.LX_PULL_TO:
                    nb -= pull * (nb - P.LX_PULL_TO)
            else:
                nb = float(a + 1)
            nbody[a + 1] = nb
            if a + 1 == P.LX_JOIN_AGE:
                for sx in "fm":
                    nT[sx][a + 1] = nP[sx][a + 1] * share
        nP["f"][0], nP["m"][0] = births * P.FEMALE_BIRTH_PER_100K / 1e5, births * P.MALE_BIRTH_PER_100K / 1e5
        P_, T, body = nP, nT, nbody
    people = sum(P_["f"]) + sum(P_["m"])
    return 1000 * deaths / people, people / people0


def _q35(q):
    """35q15 from group rates per 100k."""
    alive = 1.0
    for a in range(15, 50):
        alive *= 1 - q[P.group_of(a)] / 1e5
    return 1 - alive


def adult_mortality(carriers, lines):
    """§1.4's late check (call 20): the probability of dying between 15 and 50, 35q15, for the rich state today."""
    inp = inputs(carriers, lines)
    qf, qm, _ = M.group_rates(inp)
    return {"women": _q35(qf), "men": _q35(qm)}


def adult_mortality_by_cause(carriers, lines):
    """{sex: {cause: 35q15 from that cause alone}} for the rich state today: which schedules the figure comes from."""
    inp = inputs(carriers, lines)
    m = M.cause_multipliers(inp)
    work = dict(zip("fm", M.work_split(inp, m["work"])))
    infection = _infection_rates(inp)
    out = {}
    for sx, name in (("f", "women"), ("m", "men")):
        groups = range(len(P.GROUPS))
        out[name] = {
            "infection": _q35(infection[sx]),
            "work": _q35([P.WORK_BASE[g] * work[sx] for g in groups]),
            "accidents and violence": _q35([P.EXTERNAL[sx][g] * m["external"] for g in groups]),
            "chronic": _q35([P.CHRONIC[sx][g] * m["chronic"] for g in groups]),
        }
    return out


def _infection_rates(inp):
    """{sex: [infection deaths a year per 100,000 by age group]}: the multiplier, and the adults' factor on their ages."""
    m, adult = M.cause_multipliers(inp)["infection"], M.infection_adult(inp)
    return {sx: [P.INFECTION[sx][g] * m * (adult if g in M.INFECTION_ADULT_GROUPS else 1.0)
                 for g in range(len(P.GROUPS))] for sx in "fm"}


def young_adult_infection(inp):
    """Infection deaths a year per 100,000 people aged 15-44, women's and men's averaged (#1045)."""
    rates = _infection_rates(inp)
    groups = [g for g, (start, _n) in enumerate(P.GROUPS) if 15 <= start < 45]
    return sum(rates[sx][g] for sx in "fm" for g in groups) / (2 * len(groups))


# 2000-2020 anchors for the rich world (Human Mortality Database, as summarised): 35q15 women about 0.02-0.035 (Japan,
# Western Europe) to 0.045 (the United States), men about 0.035-0.06 to 0.09.
ADULT_BANDS = {"women": (0.015, 0.045), "men": (0.03, 0.09)}
# #1045 (owner, 2026-10-18: the rich world in eras 9-10, well below it after): infection deaths a year per 100,000 aged
# 15-44, the rich state with each era's medicine, against the rich world's 3-6 (2000-2020) and below it
INFECTION_ERAS = [  # (name, technologies, extra laws, (low, high))
    ("Today (eras 9-10's medicine)", frozenset(), frozenset(), (3, 6)),
    ("Era 10", ERA10, frozenset(), (3, 6)),
    ("Era 11", ERA11, frozenset({"law_medical_augmentation_only"}), (1, 3)),
    ("Era 12", ERA12, frozenset({"law_medical_augmentation_only"}), (0, 1)),
]


def infection_by_era(carriers, lines):
    """[(name, 15-44s' infection deaths per 100,000, (low, high))] for INFECTION_ERAS."""
    return [(name, young_adult_infection(inputs(carriers, lines, techs, laws=laws)), band)
            for name, techs, laws, band in INFECTION_ERAS]


def main(args):
    carriers, lines = _carriers()
    bad = 0
    years = getattr(args, "years", YEAR_END - YEAR0)
    runs = {}
    print(f"One rich state from today's stable structure at {TFR} children per woman, everyone within reach of longevity "
          f"care, {YEAR0} to {YEAR0 + years}.")
    for name, schedule in scenarios(carriers, lines):
        ring = start_ring(scenarios_base(carriers, lines))
        rows = project(ring, schedule, years)
        runs[name] = rows
        print(f"\n{name}")
        print("   year  people  births  deaths  65+   age (bio)    need  wf@65 wf-none  e0     to100 (treated/untr.)  "
              "old age (untr.)  pool  lifetime@100")
        for t, r in sorted(rows.items()):
            bio = f"{r['mean_age']:5.1f} ({r['mean_bio']:4.1f})" if r["mean_bio"] is not None else "    -      "
            l100 = (f"{r['l100']:.2f} ({r['l100t']:.2f}/{r['l100u']:.2f})" if r["l100t"] is not None
                    else f"{r['l100']:.2f}")
            oac = f"{r['old_age']:6.1f} ({r['old_age_c']:5.1f})" if r["old_age_c"] is not None else f"{r['old_age']:6.1f}"
            life = f"{r['lifetime_100']:.2f}" if r.get("lifetime_100") else "-"
            print(f"  {YEAR0 + t:5d}  x{r['people']:5.2f}  {r['cbr']:6.1f}  {r['cdr']:6.1f}  {r['old65']:4.2f}  {bio}  "
                  f"{r['need']:5.2f}  {r['wf_pension']:5.2f}  {r['wf_none']:5.2f}  {r['e0']:6.1f}  {l100:22s}  "
                  f"{oac:16s}  {r['pool']:5.3f}  {life}")
    print("\nThe design's steady life tables (§1.2, §1.5; sketch bands, everyone treated):")
    for label, scen, t, bands in STEADY:
        if t > years:
            print(f"  {label:58s} (needs {t} years)")
            continue
        bad += judge(label, runs[scen][t], bands)
    print("\nThe design's projections at 60 years (Context's table; sketch bands):")
    for scen, bands in PROJECTION:
        row = runs[scen].get(60)
        if row:
            bad += judge(scen, row, bands)
    print("\nImmortality after 50 years (§3.3: growth and the bounded lifetime births):")
    if 50 in runs["Immortality (pull 3%) from today"]:
        bad += judge("Immortality (pull 3%) from today", runs["Immortality (pull 3%) from today"][50], IMMORTAL_50)
    print("\nWho is treated (§1.3): a share and a deficit per band against the per-cohort truth, year 50:")
    start = start_ring(scenarios_base(carriers, lines))
    for name, techs, share in TRUTH_CASES:
        inp = _share_inputs(carriers, lines, techs, share)
        d_band, x_band = band_model(inp, share, start)
        d_truth, x_truth = truth(inp, share, start)
        ok = abs(d_band - d_truth) <= TRUTH_TOLERANCE and abs(x_band / x_truth - 1) <= 0.02
        bad += not ok
        print(f"  {name:34s} truth {d_truth:5.1f} per 1,000, x{x_truth:4.2f}   bands {d_band:5.1f}, x{x_band:4.2f}"
              f"{'' if ok else '  OUT'}")
    print("\nAdult mortality today (§1.4, call 20): 35q15, the probability of dying between 15 and 50:")
    causes = adult_mortality_by_cause(carriers, lines)
    for sx, v in adult_mortality(carriers, lines).items():
        lo, hi = ADULT_BANDS[sx]
        ok = lo <= v <= hi
        split = ", ".join(f"{c} {q:.3f}" for c, q in causes[sx].items())
        print(f"  {sx:6s} {v:.3f} [{lo:g}-{hi:g}]{'' if ok else ' OUT'}  ({split})")
    # Modern safety (2026-10-16) brought work and accidents down, and the adults' infection factor (#1045) adult infection,
    # to the rich world's
    print("  (rich-world 2000-2020 by cause, about: infection 0.001-0.002, work 0.001, accidents and violence 0.004-0.012 "
          "for women and 0.014-0.037 for men, chronic 0.02-0.03)")
    print("\nInfection deaths a year per 100,000 aged 15-44 by era's medicine (#1045; the rich world's 3-6 in eras 9-10, "
          "below after):")
    for name, v, (lo, hi) in infection_by_era(carriers, lines):
        ok = lo <= v <= hi
        bad += not ok
        print(f"  {name:30s} {v:5.2f} [{lo:g}-{hi:g}]{'' if ok else ' OUT'}")
    return 1 if bad else 0
