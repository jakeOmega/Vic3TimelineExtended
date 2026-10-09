"""The demographics cohort model in Python: the reference the generated script mirrors.

Spec: docs/superpowers/specs/2026-10-08-demographics-design.md §1-§3, §2.6. Every
function here has a script twin; the order of operations in `step` and `seed` is the
order of the script's sweep (common/scripted_effects/te_demog_effects.txt), so a state
logged before and after one in-game step replays here to within rounding
(`demographics_harness.py replay`).

The ring: RING_YEARS slots, one per birth year, slot = birth year mod RING_YEARS. After
the step of year Y, slot Y mod RING_YEARS holds that year's births (age 0) and the slot
for age a holds the people born in Y - a. Ages 150 and over live in a pool.
"""

from dataclasses import dataclass, field

try:  # repo layout: scripts/analysis/ on sys.path, or imported as a namespace package
    import demographics_params as P
except ImportError:  # pragma: no cover
    from scripts.analysis import demographics_params as P

N = P.RING_YEARS
assert P.COHORT_WIDTH == 1, "only one-year cohorts are built (spec §1, §13)"


@dataclass
class Inputs:
    """What one state's yearly walk and its owner's laws and technology give the model."""
    sol: float = 8.0
    literacy: float = 0.0
    urban_share: float = 0.0
    techs: frozenset = frozenset()
    laws: frozenset = frozenset()
    institutions: dict = field(default_factory=dict)
    crowding: bool = False
    wealth_tfr: float | None = None      # pop-weighted SoL curve from the walk
    means_add: float = 0.0               # modifier:country_fertility_means_add (Family Limitation 0.6)
    female_job_share: float = 0.3        # light industry + services share of the employed
    crisis: float = 0.0                  # 0..1: war, devastation, turmoil at the origin
    inflow_years: int = 0                # consecutive years of net inflow (chain migration)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp_sol(sol, at_low, at_high, lo_sol=P.WEALTH_TFR_LOW_SOL, hi_sol=P.WEALTH_TFR_HIGH_SOL):
    t = clamp((sol - lo_sol) / (hi_sol - lo_sol), 0.0, 1.0)
    return at_low + (at_high - at_low) * t


def wealth_tfr(sol):
    """Children per woman from wealth alone: the retuned SoL curve as a TFR (§2.3)."""
    return lerp_sol(sol, P.WEALTH_TFR_LOW, P.WEALTH_TFR_HIGH)


def female_work_share(inp):
    for law, share in P.FEMALE_WORK_SHARE.items():
        if law in inp.laws:
            return share
    return P.FEMALE_WORK_SHARE_DEFAULT


def cause_multipliers(inp):
    """One multiplier per cause from the state's inputs; 1.0 at the base (§2.4)."""
    mult = {c: 1.0 for c in ("infection", "work", "external", "maternal", "chronic")}
    for cause, techs in P.TECH_MULT.items():
        for tech, m in techs.items():
            if tech in inp.techs:
                mult[cause] *= m
    for cause, laws in P.LAW_MULT.items():
        for law, m in laws.items():
            if law in inp.laws:
                mult[cause] *= m
    for cause, insts in P.INSTITUTION_MULT.items():
        for inst, m in insts.items():
            mult[cause] *= m ** inp.institutions.get(inst, 0)
    mult["infection"] *= lerp_sol(inp.sol, 1.0, P.SOL_INFECTION_AT_HIGH)
    mult["infection"] *= 1 - P.LITERACY_INFECTION_WEIGHT * inp.literacy
    if inp.crowding and inp.institutions.get("institution_ministry_of_urban_planning", 0) == 0:
        mult["infection"] *= P.CROWDING_INFECTION_MULT
    mult["chronic"] *= lerp_sol(inp.sol, 1.0, P.SOL_CHRONIC_AT_HIGH)
    return mult


def rates_from_multipliers(mult, work_f, work_m):
    """Yearly death probability per 100k for each age group, women and men.

    mult: cause -> multiplier (infection, external, chronic; work is folded into
    work_f / work_m, which already carry the split between the sexes). The script's
    te_demog_enter_group computes the same sum.
    """
    qf, qm = [], []
    for g in range(len(P.GROUPS)):
        qf.append(min(100000.0, P.INFECTION["f"][g] * mult["infection"] + P.WORK_BASE[g] * work_f
                      + P.EXTERNAL["f"][g] * mult["external"] + P.CHRONIC["f"][g] * mult["chronic"]))
        qm.append(min(100000.0, P.INFECTION["m"][g] * mult["infection"] + P.WORK_BASE[g] * work_m
                      + P.EXTERNAL["m"][g] * mult["external"] + P.CHRONIC["m"][g] * mult["chronic"]))
    return qf, qm


def work_split(inp, work_mult):
    """(women's, men's) work-death multipliers: the cause multiplier x 2 x each sex's share."""
    fw = female_work_share(inp)
    return work_mult * 2 * fw, work_mult * 2 * (1 - fw)


def group_rates(inp):
    """Group rates for women and men, and maternal deaths per 100k births."""
    m = cause_multipliers(inp)
    work_f, work_m = work_split(inp, m["work"])
    qf, qm = rates_from_multipliers(m, work_f, work_m)
    return qf, qm, m["maternal"] * P.MATERNAL_PER_100K_BIRTHS


def life_table(q):
    """e0, e65 and infant mortality from group rates, closed form per group.

    In a group of width n with constant yearly probability q, survivors fall by (1-q)
    a year, and person-years are counted at mid-year. The script computes the same.
    """
    l, e_total, l65, py_from_65 = 1.0, 0.0, None, 0.0
    for g, (start, n) in enumerate(P.GROUPS):
        qq = q[g] / 100000.0
        p = 1.0 - qq
        pn = p ** n
        person_years = l * n if qq == 0 else l * (1 - qq / 2) * (1 - pn) / qq
        if start == 65:
            l65 = l
        if start >= 65:
            py_from_65 += person_years
        e_total += person_years
        l *= pn
    return {"e0": e_total, "e65": py_from_65 / l65 if l65 else 0.0, "q0_per_1000": q[0] / 100.0}


def means(inp):
    tier = 0.0
    for tech, value in P.MEANS_TIERS:
        if tech is None or tech in inp.techs:
            tier = max(tier, value)
    access = 0.3 + 0.7 * inp.literacy
    shift = sum(v for law, v in P.MEANS_LAW_SHIFT.items() if law in inp.laws)
    return clamp(tier * access + shift + inp.means_add, 0.0, P.MEANS_CAP)


def fertility(inp, e0):
    """Children per woman and its terms (§2.3)."""
    wealth = inp.wealth_tfr if inp.wealth_tfr is not None else wealth_tfr(inp.sol)
    education = 1 - P.EDUCATION_WEIGHT * inp.literacy
    survival = 1 - P.SURVIVAL_WEIGHT * clamp((e0 - 30) / 50, 0.0, 1.0)
    urban = 1 - P.URBAN_WEIGHT * inp.urban_share
    desired = education * survival * urban
    mn = means(inp)
    factor = 1 - mn * (1 - desired)
    return {"tfr": wealth * factor, "wealth": wealth, "education": education,
            "survival": survival, "urban": urban, "means": mn, "factor": factor}


def asfr_shape(rate_age):
    """Share of a woman's lifetime births at this rate age, per 100k (15-49)."""
    if rate_age < 15 or rate_age > 49:
        return 0.0
    return P.ASFR_SHAPE_BY_GROUP[rate_age - rate_age % 5] / 5.0


def migrant_profile(inp):
    """Per (class, sex) share of a net migration, summing to 1 (§2.5)."""
    refugee = clamp(inp.crisis, 0.0, 1.0)
    rights = female_work_share(inp) / P.FULL_FEMALE_WORK_SHARE
    family = P.FAMILY_BASE + sum(v for t, v in P.FAMILY_TRANSPORT_TECHS.items() if t in inp.techs)
    family += P.FAMILY_RIGHTS_WEIGHT * rights + min(P.CHAIN_CAP, P.CHAIN_STEP * inp.inflow_years)
    family = clamp(family, 0.0, 1.0 - refugee)
    labour = max(0.0, 1.0 - family - refugee)
    labour_f = clamp(P.LABOUR_FEMALE_SHARE_MIN + inp.female_job_share * rights
                     * (P.LABOUR_FEMALE_SHARE_MAX - P.LABOUR_FEMALE_SHARE_MIN),
                     P.LABOUR_FEMALE_SHARE_MIN, P.LABOUR_FEMALE_SHARE_MAX)
    out = {}
    for c in range(len(P.MIGRANT_CLASSES)):
        lw = labour * P.MIGRANT_PROFILE["labour"]["weights"][c]
        fw = family * P.MIGRANT_PROFILE["family"]["weights"][c]
        rw = refugee * P.MIGRANT_PROFILE["refugee"]["weights"][c]
        out[(c, "f")] = lw * labour_f + (fw + rw) * 0.5
        out[(c, "m")] = lw * (1 - labour_f) + (fw + rw) * 0.5
    total = sum(out.values()) or 1.0
    return {k: v / total for k, v in out.items()}


def class_of(age):
    for c, (lo, hi) in enumerate(P.MIGRANT_CLASSES):
        if lo <= age <= hi:
            return c
    return len(P.MIGRANT_CLASSES) - 1


@dataclass
class Ring:
    f: list = field(default_factory=lambda: [0.0] * N)
    m: list = field(default_factory=lambda: [0.0] * N)
    pool_f: float = 0.0
    pool_m: float = 0.0
    pool_age: float = 150.0
    scale: float = 1.0                  # applied lazily at the next sweep
    year: int | None = None
    class_f: list = field(default_factory=lambda: [0.0] * len(P.MIGRANT_CLASSES))
    class_m: list = field(default_factory=lambda: [0.0] * len(P.MIGRANT_CLASSES))
    men_18_40: float = 0.0
    women_18_40: float = 0.0
    total: float = 0.0

    def age_of_slot(self, k):
        """Age of slot k's people after the step of self.year."""
        return (self.year - k) % N

    def people(self):
        return self.scale * (sum(self.f) + sum(self.m) + self.pool_f + self.pool_m)

    def by_age(self):
        """[(age, women, men)] for ages 0..149, scaled, then the pool as age 150."""
        rows = []
        for a in range(N):
            k = (self.year - a) % N
            rows.append((a, self.f[k] * self.scale, self.m[k] * self.scale))
        rows.append((150, self.pool_f * self.scale, self.pool_m * self.scale))
        return rows


def grouped_gini(groups):
    """Gini of [(people, income), ...] treating each group as equal inside (§4.1)."""
    groups = sorted((g for g in groups if g[0] > 0), key=lambda g: g[1] / g[0])
    people = sum(g[0] for g in groups)
    income = sum(g[1] for g in groups)
    if people <= 0 or income <= 0:
        return 0.0
    gini, below = 1.0, 0.0
    for n, y in groups:
        share = below + y / income
        gini -= n / people * (share + below)
        below = share
    return gini


def shown_gini(grouped):
    """The panel's Gini: an affine map of the grouped Gini (§4.1's anchors)."""
    return clamp(P.GINI_FLOOR + P.GINI_SCALE * grouped, 0.0, 0.9)


NRR_TABLE_MIN, NRR_TABLE_MAX = 0.2, 4.0   # the generated table's first and last knots


def growth_factor(nrr):
    """d = e^-r from the net reproduction rate, via r = ln(NRR) / T (T = 29 years).

    The script reads d from a generated table of this function (gen_demographics.py).
    """
    nrr = clamp(nrr, NRR_TABLE_MIN, NRR_TABLE_MAX)   # the table's knots end here, and 0 has no power
    return nrr ** (-1.0 / 29.0)


def nrr(tfr, qf):
    """Daughters per woman: TFR x female share x survival to each childbearing age."""
    l, total = 1.0, 0.0
    for r in range(50):
        if r >= 15:
            total += l * asfr_shape(r) / 100000.0
        l *= 1 - qf[P.group_of(r)] / 100000.0
    return tfr * P.FEMALE_BIRTH_PER_100K / 100000.0 * total


def seed(inp, year, engine_pop):
    """A ring at the stable structure of the state's own rates (§2.6, rule 5).

    The women's survivorship includes maternal deaths, so the seed is the step's own
    equilibrium; nrr and life_table leave them out (a documented approximation).
    """
    qf, qm, mmr = group_rates(inp)
    e0 = life_table(qf)["e0"] * 0.5 + life_table(qm)["e0"] * 0.5
    tfr = fertility(inp, e0)["tfr"]
    d = growth_factor(nrr(tfr, qf))
    ring = Ring(year=year)
    lf = lm = 100000.0
    dpow = 1.0
    for a in range(N):
        k = (year - a) % N
        ring.f[k] = P.FEMALE_BIRTH_PER_100K / 100000.0 * lf * dpow
        ring.m[k] = P.MALE_BIRTH_PER_100K / 100000.0 * lm * dpow
        g = P.group_of(a)
        lf *= 1 - (qf[g] + asfr_shape(a) * tfr * mmr / 100000.0) / 100000.0
        lm *= 1 - qm[g] / 100000.0
        dpow *= d
    raw = sum(ring.f) + sum(ring.m)
    ring.scale = engine_pop / raw if raw > 0 else 1.0
    _refresh_denominators(ring)
    ring.total = engine_pop
    return ring


def _refresh_denominators(ring):
    """Class and 18-40 sums for next year's flows, by the age each cohort has now.

    Next year's step applies the flows by rate age (a - 1), so it divides by exactly the
    cohorts it applies them to. The age-149 cohort and the pool are left out: they are
    folded, not flowed.
    """
    ring.class_f = [0.0] * len(P.MIGRANT_CLASSES)
    ring.class_m = [0.0] * len(P.MIGRANT_CLASSES)
    ring.men_18_40 = ring.women_18_40 = 0.0
    for a, f, m in ring.by_age():
        if a > N - 2:
            continue
        c = class_of(a)
        ring.class_f[c] += f
        ring.class_m[c] += m
        if P.WAR_DEAD_AGES[0] <= a <= P.WAR_DEAD_AGES[1]:
            ring.men_18_40 += m
            ring.women_18_40 += f


def step(ring, inp, year, engine_pop=None, war_dead=0.0, kills=0.0, migration=0.0, rates=None):
    """One yearly step (§2.1), in the script's order. Returns the year's figures.

    engine_pop None = no scaling (a pure model run). war_dead, kills and migration are
    people this year (migration net, signed); the residual noise rule is the caller's.
    Flows (war, kills, migration) are applied by rate age to the counts before deaths.
    rates = (qf, qm, mmr, tfr, profile) replays an in-game step with the rates the game
    logged instead of recomputing them from inputs.
    """
    assert ring.year is not None and year == ring.year + 1, "one step per year"
    if rates is None:
        qf, qm, mmr = group_rates(inp)
        lt_f, lt_m = life_table(qf), life_table(qm)
        e0 = (lt_f["e0"] + lt_m["e0"]) / 2
        fert = fertility(inp, e0)
        tfr = fert["tfr"]
        prof = migrant_profile(inp)
    else:
        qf, qm, mmr, tfr, prof = rates
        lt_f, lt_m = life_table(qf), life_table(qm)
        e0 = (lt_f["e0"] + lt_m["e0"]) / 2
        fert = {"tfr": tfr}
    s = ring.scale
    war_m = clamp(war_dead * P.WAR_DEAD_MALE_SHARE / ring.men_18_40, 0, 0.5) if ring.men_18_40 else 0.0
    war_f = clamp(war_dead * (1 - P.WAR_DEAD_MALE_SHARE) / ring.women_18_40, 0, 0.5) if ring.women_18_40 else 0.0
    kill = clamp(kills / ring.total, 0, 0.9) if ring.total else 0.0
    births = deaths = 0.0
    open_k = year % N
    # ages 1..150 at this step; the slot at 150 is the open slot, folded then refilled
    for a in range(1, N + 1):
        k = (year - a) % N
        f, m = ring.f[k] * s, ring.m[k] * s
        if a == N:
            ring.pool_age = ((ring.pool_f + ring.pool_m) * s * (ring.pool_age + 1) + (f + m) * N) / max(
                (ring.pool_f + ring.pool_m) * s + f + m, 1e-9)
            ring.pool_f, ring.pool_m = ring.pool_f * s + f, ring.pool_m * s + m
            ring.pool_f *= 1 - kill
            ring.pool_m *= 1 - kill
            ring.f[k] = ring.m[k] = 0.0
            continue
        r = a - 1
        g = P.group_of(r)
        b = f * asfr_shape(r) / 100000.0 * tfr
        births += b
        f2 = f * (1 - qf[g] / 100000.0) - b * mmr / 100000.0
        m2 = m * (1 - qm[g] / 100000.0)
        deaths += (f - f2) + (m - m2)
        if P.WAR_DEAD_AGES[0] <= r <= P.WAR_DEAD_AGES[1]:
            f2 -= f * war_f
            m2 -= m * war_m
        f2 -= f * kill
        m2 -= m * kill
        c = class_of(r)
        if migration > 0:
            if ring.class_f[c] >= 1:
                f2 += migration * prof[(c, "f")] * f / ring.class_f[c]
            if ring.class_m[c] >= 1:
                m2 += migration * prof[(c, "m")] * m / ring.class_m[c]
        elif migration < 0:
            if ring.class_f[c] >= 1:
                f2 -= min(max(f2, 0.0) * 0.5, -migration * prof[(c, "f")] * f / ring.class_f[c])
            if ring.class_m[c] >= 1:
                m2 -= min(max(m2, 0.0) * 0.5, -migration * prof[(c, "m")] * m / ring.class_m[c])
        ring.f[k], ring.m[k] = max(f2, 0.0), max(m2, 0.0)
    # the pool: last group's rates, ages a year
    pq_f, pq_m = qf[-1] / 100000.0, qm[-1] / 100000.0
    deaths += ring.pool_f * pq_f + ring.pool_m * pq_m
    ring.pool_f *= 1 - pq_f
    ring.pool_m *= 1 - pq_m
    ring.f[open_k] = births * P.FEMALE_BIRTH_PER_100K / 100000.0
    ring.m[open_k] = births * P.MALE_BIRTH_PER_100K / 100000.0
    ring.year = year
    raw = sum(ring.f) + sum(ring.m) + ring.pool_f + ring.pool_m
    ring.scale = (engine_pop / raw) if (engine_pop is not None and raw > 0) else 1.0
    _refresh_denominators(ring)
    ring.total = ring.people()
    return {"births": births, "deaths": deaths, "tfr": tfr, "e0": e0, "e0_f": lt_f["e0"], "e0_m": lt_m["e0"],
            "e65": (lt_f["e65"] + lt_m["e65"]) / 2, "q0_per_1000": (qf[0] + qm[0]) / 200.0,
            "fertility": fert, "raw": raw}


def structure(ring):
    """Shares 0-14, 15-64, 65+, median age, men per 100 women (20-59)."""
    rows = ring.by_age()
    tot = sum(f + m for _a, f, m in rows) or 1.0
    young = sum(f + m for a, f, m in rows if a <= 14) / tot
    old = sum(f + m for a, f, m in rows if a >= 65) / tot
    half, run, median = tot / 2, 0.0, 0.0
    for a, f, m in rows:
        if run + f + m >= half:
            median = a + (half - run) / max(f + m, 1e-9)
            break
        run += f + m
    w = sum(f for a, f, _m in rows if 20 <= a <= 59) or 1.0
    men = sum(m for a, _f, m in rows if 20 <= a <= 59)
    return {"young": young, "working": 1 - young - old, "old": old, "median": median,
            "men_per_100_women": 100 * men / w}


def run_constant(inp, years=400, year0=1836):
    """Seed, then step with fixed inputs and no engine scaling; return the last step."""
    ring = seed(inp, year0, 1_000_000)
    ring.scale = 1.0
    raw = sum(ring.f) + sum(ring.m)
    ring.f = [x * 1_000_000 / raw for x in ring.f]
    ring.m = [x * 1_000_000 / raw for x in ring.m]
    _refresh_denominators(ring)
    ring.total = ring.people()
    last, prev = None, ring.people()
    for y in range(year0 + 1, year0 + years + 1):
        last = step(ring, inp, y)
        cur = ring.people()
        last["growth"] = cur / prev - 1
        prev = cur
    return ring, last
