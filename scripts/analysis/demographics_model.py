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

from dataclasses import dataclass, field, replace

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
    crowding: float = 0.0                # migration penalty from crowding: 0.1 x migration_crowding's multiplier
    wealth_tfr: float | None = None      # pop-weighted SoL curve from the walk
    means_add: float = 0.0               # static modifiers' state_fertility_means_add (Family Limitation 0.6); laws' lines come through mods
    female_job_share: float = 0.3        # light industry + services share of the employed
    crisis: float = 0.0                  # 0..1: war, devastation, turmoil at the origin
    inflow_years: int = 0                # consecutive years of net inflow (chain migration)
    mods: dict = field(default_factory=dict)   # {modifier type: total} the state reads (demographics_modifiers.totals)
    turmoil: float = 0.0                 # 0..1: the state's turmoil at the step (te_dg_in_turm)
    medicine: dict | None = None         # the drifted access and treatments the step holds; None = at the targets
    practices: dict = field(default_factory=dict)   # {practice: share 0-1}: lm Late Marriage, bs Birth Spacing
    agrarian_share: float = 0.0          # Peasants and Farmers over the state's people (the walk's te_dg_agr_share)
    impartible: bool = False             # the owner holds Primogeniture or Undivided Farm Succession
    low_share: float = 0.0               # the lower strata's share of people (te_dg_low_share, from the walk)
    pension_age: float | None = None     # the owner's pension age under Old Age Pension; None = the Standard position
    birth_limit: float = 0.0             # Birth Limit's part of P.DESIRED_TYPE (its modifier's line: 0, -0.3 or -0.45;
                                         # the script's te_demog_ms_birth_limit_part), which the Rural Exemption relieves
    malaria: int = 0                     # the state region's malaria trait level (P.MALARIA_TRAITS; calibration step 3)
    # phase 2 step 2 (§2.5): under Full, women's share of the census's own workers aged P.WORK_SPLIT_AGES at the last
    # count (te_dg_fws_wk), which splits work deaths; None = the law table (outside Full, or before a count)
    work_female_share: float | None = None
    sex_balance: float | None = None     # men per 100 women aged 20-59 the step reads (te_dg_sxb); None = no term


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


def plain_multiplier(inp, cause):
    """1 + the cause's types' sum (P.MORTALITY_TYPES), at least P.MORTALITY_MULT_FLOOR."""
    return max(P.MORTALITY_MULT_FLOOR, 1 + sum(inp.mods.get(t, 0.0) for t in P.MORTALITY_TYPES.get(cause, ())))


def medicine_targets(inp):
    """Where medicine is heading: {"access", and each of P.MEDICINE_CAUSES' treatment}, clamped as the census
    clamps them (te_demog_access_target, te_demog_treatment_target_<cause>)."""
    out = {"access": clamp(P.BASE_ACCESS + inp.mods.get(P.ACCESS_TYPE, 0.0), 0.0, 1.0)}
    for cause in P.MEDICINE_CAUSES:
        out[cause] = clamp(inp.mods.get(P.TREATMENT_TYPE[cause], 0.0), 0.0, P.TREATMENT_CAP[cause])
    return out


def diffusion(inp):
    """The share of the gap medicine closes at a census step (te_demog_medical_diffusion)."""
    return clamp(P.DIFFUSION_BASE + inp.mods.get(P.DIFFUSION_TYPE, 0.0), 0.0, P.DIFFUSION_MAX)


def medicine_drift(prev, inp):
    """One census step of the drifted medicine (te_demog_medicine_drift): each value moves diffusion(inp) of the way
    to its target and takes the target once within MEDICINE_SNAP of it. prev None (a seed, a new state, an old save's
    state) starts at the targets. The order of operations is the script's: (target - prev) x rate + prev."""
    target = medicine_targets(inp)
    if prev is None:
        return dict(target)
    rate = diffusion(inp)
    out = {}
    for key, t in target.items():
        x = (t - prev[key]) * rate + prev[key]
        out[key] = t if -P.MEDICINE_SNAP < t - x < P.MEDICINE_SNAP else x
    return out


def medicine(inp, cause):
    """1 - access x treatment for one of P.MEDICINE_CAUSES, at the drifted values the step holds (inp.medicine) or,
    with none, at the targets (modifier-types design, Decision 1)."""
    m = inp.medicine if inp.medicine is not None else medicine_targets(inp)
    return 1 - m["access"] * m[cause]


def cause_factors(inp):
    """{cause: {factor: value}} in P.CAUSE_FACTORS' order: the script's te_demog_f_<cause>_<factor>."""
    def one(factor, cause):
        if factor == "medicine":
            return medicine(inp, cause)
        if factor == "sol":
            return lerp_sol(inp.sol, 1.0, P.SOL_INFECTION_AT_HIGH if cause == "infection" else P.SOL_CHRONIC_AT_HIGH)
        if factor == "poverty":
            return poverty_infection(inp.sol)
        if factor == "literacy":
            return 1 - P.LITERACY_INFECTION_WEIGHT * inp.literacy
        if factor == "crowding":
            return 1 + min(P.CROWDING_INFECTION_PER_PULL * inp.crowding, P.CROWDING_INFECTION_MAX)
        if factor == "laws":
            return plain_multiplier(inp, cause)
        if factor == "turmoil":
            return 1 + P.TURMOIL_EXTERNAL_WEIGHT * clamp(inp.turmoil, 0.0, 1.0)
        if factor == "malaria":
            control = clamp(inp.mods.get(P.MALARIA_CONTROL_TYPE, 0.0), 0.0, 1.0)
            return 1 + P.MALARIA_INFECTION.get(inp.malaria, 0.0) * (1 - control)
        raise KeyError(factor)
    return {cause: {f: one(f, cause) for f in factors} for cause, factors in P.CAUSE_FACTORS.items()}


def cause_multipliers(inp):
    """One multiplier per cause from the state's inputs; 1.0 at the base (§2.4): the product of its factors, in
    P.CAUSE_FACTORS' order, as the script's te_demog_mult_<cause> computes it."""
    out = {}
    for cause, factors in cause_factors(inp).items():
        m = 1.0
        for v in factors.values():
            m *= v
        out[cause] = m
    return out


def poverty_infection(sol):
    """Infection's poverty term: x1 at POVERTY_INFECTION_SOL and above, rising linearly to
    POVERTY_INFECTION_AT_FLOOR at POVERTY_INFECTION_FLOOR_SOL and below (phase 2 calibration)."""
    span = P.POVERTY_INFECTION_SOL - P.POVERTY_INFECTION_FLOOR_SOL
    t = clamp((P.POVERTY_INFECTION_SOL - sol) / span, 0.0, 1.0)
    return 1 + (P.POVERTY_INFECTION_AT_FLOOR - 1) * t


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


def work_death_share(inp):
    """Women's share of work deaths (te_demog_work_death_share): under Full the census's own count of women among the
    workers aged P.WORK_SPLIT_AGES at the last count (phase 2 step 2, §2.5), else the law table."""
    return female_work_share(inp) if inp.work_female_share is None else inp.work_female_share


def work_split(inp, work_mult):
    """(women's, men's) work-death multipliers: the cause multiplier x 2 x each sex's share."""
    fw = work_death_share(inp)
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
    """The share of the gap to desired fertility a population can close (§2.3; stage 2's types)."""
    tier = clamp(P.TRADITIONAL_MEANS + inp.mods.get(P.CONTRACEPTION_TYPE, 0.0), 0.0, 1.0)
    # Sex Education (phase 2 step 3b): access as if literacy were the type higher, at most full
    literacy = min(1.0, inp.literacy + inp.mods.get(P.MEANS_LITERACY_TYPE, 0.0))
    access = P.MEANS_ACCESS_BASE + (1 - P.MEANS_ACCESS_BASE) * literacy
    shift = inp.mods.get(P.MEANS_SHIFT_TYPE, 0.0) + inp.means_add
    return clamp(tier * access + shift, 0.0, P.MEANS_CAP)


def policy_term(inp):
    """Family policy's factor on desired fertility (phase 2 step 3b, spec §3.5; te_demog_tfr_policy): 1 + the desired
    type, with Birth Limit's part relieved by the relief type x the state's agrarian share (the Rural Exemption), at
    least 0. Birth Limit's part is negative, so the relief raises the term."""
    d = inp.mods.get(P.DESIRED_TYPE, 0.0)
    relief = inp.mods.get(P.BIRTH_LIMIT_RELIEF_TYPE, 0.0)
    if relief > 0:
        d -= inp.birth_limit * min(relief, 1.0) * inp.agrarian_share
    return max(0.0, 1 + d)


def urban_term(inp):
    """City life's pull on desired fertility, 1 - URBAN_WEIGHT x urban x (1 - the relief type within 0-1): Family
    Housing (phase 2 step 3b; te_demog_tfr_urban)."""
    relief = clamp(inp.mods.get(P.URBAN_RELIEF_TYPE, 0.0), 0.0, 1.0)
    return 1 - P.URBAN_WEIGHT * (inp.urban_share * (1 - relief))


def newborn_split(inp):
    """(girls, boys) per 100,000 births in the step (phase 2 step 3b, spec §3.4; te_demog_newborn_split): the
    constants, or, once prenatal sexing exists and the sex-ratio type is positive, 100 girls to SRB_BASE + it boys."""
    t = inp.mods.get(P.SRB_TYPE, 0.0)
    if t <= 0 or P.PRENATAL_SEXING_TECH not in inp.techs:
        return float(P.FEMALE_BIRTH_PER_100K), float(P.MALE_BIRTH_PER_100K)
    girls = 100000.0 * 100 / (100 + P.SRB_BASE + t)
    return girls, 100000.0 - girls


def fertility(inp, e0):
    """Children per woman and its terms (§2.3): wealth x natural x the practices x sex x (1 - means x (1 - desired)).
    Natural fertility is women's legal standing (phase 2 step 4, Task 7), 1 + its type, at least
    NATURAL_FERTILITY_FLOOR. Each practice (the late-marriage spec §2.1) multiplies by 1 - its cut x its share, outside
    the means; a practice with no share is 1. sex is the sex balance's term (phase 2 step 4, the consequences design
    §4.4: fewer marriages where men are few; sex_births), 1 with no balance given."""
    wealth = inp.wealth_tfr if inp.wealth_tfr is not None else wealth_tfr(inp.sol)
    natural = max(P.NATURAL_FERTILITY_FLOOR, 1 + inp.mods.get(P.NATURAL_FERTILITY_TYPE, 0.0))
    education = 1 - P.EDUCATION_WEIGHT * inp.literacy
    survival = 1 - P.SURVIVAL_WEIGHT * clamp((e0 - 30) / 50, 0.0, 1.0)
    urban = urban_term(inp)
    # family policy (phase 2 step 3b): the measures' and Pro-Natalist Policy's desired type, floored and capped
    policy = policy_term(inp)
    desired = clamp(education * survival * urban * policy, P.DESIRED_FLOOR, P.DESIRED_CAP)
    mn = means(inp)
    factor = 1 - mn * (1 - desired)
    practices = {p: 1 - cut * inp.practices.get(p, 0.0) for p, cut in P.PRACTICE_CUT.items()}
    sex = sex_births(inp.sex_balance)
    tfr = wealth * natural * factor * sex
    for term in practices.values():
        tfr *= term
    out = {"tfr": tfr, "wealth": wealth, "natural": natural, "education": education,
           "survival": survival, "urban": urban, "policy": policy, "desired": desired, "means": mn, "factor": factor,
           "sex": sex, **practices}
    # planned and unplanned births (late-game §3.1): the families who choose their number, and the births the means
    # don't reach. Computed from the result's own tfr and factor, so every term multiplying the factor (wealth,
    # natural, #906's practices) scales both parts alike.
    out["planned"] = out["tfr"] / out["factor"] * out["means"] * desired
    out["unplanned"] = out["tfr"] / out["factor"] * (1 - out["means"])
    return out


# ---- Late Marriage and Birth Spacing (the late-marriage spec §3-§4; te_demog_practice_effects.txt) --------------

def practice_start(practice, state_region, strategic_region):
    """A state's start share (§3.2, §3.3): its state region's entry, else its strategic region's, else 0
    (te_demog_pr_start_<P>, generated)."""
    by_state = P.PRACTICE_START_STATE[practice]
    if state_region in by_state:
        return by_state[state_region]
    return P.PRACTICE_START_REGION[practice].get(strategic_region, 0.0)


def bs_held_group(state_region, strategic_region):
    """Which held Birth Spacing share a state takes (the plan's D13): "east_asia" (China, Manchuria, Korea), "india", or
    None (Japan's full share, or none)."""
    if strategic_region in P.BS_EAST_ASIA_REGIONS or state_region in P.BS_EAST_ASIA_STATES:
        return "east_asia"
    if strategic_region in P.BS_INDIA_REGIONS:
        return "india"
    return None


def contraception_beyond(inp):
    """The means beyond traditional methods: the techs' contraception x access by literacy (§4.2)."""
    return inp.mods.get(P.CONTRACEPTION_TYPE, 0.0) * (P.MEANS_ACCESS_BASE + (1 - P.MEANS_ACCESS_BASE) * inp.literacy)


def practice_erosion(practice, inp):
    """How much of the start the state's conditions take away, 0-1 (§4.2, §4.3). Health care's part reads the access
    medicine has reached above the base (te_dg_acc - BASE_ACCESS: since #916 access drifts toward its target), so
    Birth Spacing fades as medicine spreads; with no drift held it is the target, the access modifier."""
    contra = P.PRACTICE_EROSION_CONTRACEPTION * clamp(
        (contraception_beyond(inp) - P.PRACTICE_EROSION_FROM) / P.PRACTICE_EROSION_SPAN, 0.0, 1.0)
    reached = (inp.medicine if inp.medicine is not None else medicine_targets(inp))["access"] - P.BASE_ACCESS
    access = P.PRACTICE_EROSION_ACCESS[practice] * clamp(reached / P.PRACTICE_ACCESS_SPAN, 0.0, 1.0)
    return clamp(contra + access, 0.0, 1.0)


def practice_target(practice, inp, start):
    """Where a practice's share drifts (§4.2, §4.3; te_demog_pr_target_<P>): the start less its erosion, plus Late
    Marriage's drivers, impartible inheritance on the farms and women's paid work, within 0-1."""
    target = start * (1 - practice_erosion(practice, inp))
    if practice == "lm":
        if inp.impartible:
            target += P.LM_INHERITANCE * inp.agrarian_share
        target += P.LM_WOMENS_WORK * inp.female_job_share * female_work_share(inp) / P.FULL_FEMALE_WORK_SHARE
    return clamp(target, 0.0, 1.0)


def practice_drift(share, target):
    """One year's drift (§4.2): PRACTICE_RATE of the gap. The neighbour spread is phase 3's (the plan's D6)."""
    return clamp(share + P.PRACTICE_RATE * (target - share), 0.0, 1.0)


def practice_seed(practice, inp, start, siblings=(), region=None):
    """A state with no share (§3.4; the plan's D5): the people-weighted mean of the other states in its state region
    that hold one; else the region's copy of the share (te_dg_pr_<P>_r, written at each step: a whole state region that
    changed hands, Stop B's I1); else its start less what its conditions have already eroded, start x (1 - erosion)
    (te_demog_pr_seed_<P>). In 1836 nothing has eroded anywhere a practice starts (no contraception before era 3; no
    health law in Japan, China, Korea or India) and no region holds a copy, so a new game seeds the table. An old save
    or a rule switched on mid-game seeds near where the drift would have taken it, not at the 1836 custom (review I2).
    The drivers stay out, so Japan's Late Marriage starts at 0 (call 3). siblings: [(people, share)]; region: the
    region's copy, or None."""
    held = [(p, s) for p, s in siblings if p > 0]
    people = sum(p for p, _s in held)
    if people > 0:
        return sum(p * s for p, s in held) / people
    if region is not None:
        return region
    return start * (1 - practice_erosion(practice, inp))


def marriage_age(share):
    """Women's mean age at first marriage the panel shows (§5.3): 19 with no Late Marriage, 26 at a full share."""
    return P.MARRIAGE_AGE_AT_ZERO + P.MARRIAGE_AGE_SPAN * share


def asfr_shape(rate_age):
    """Share of a woman's lifetime births at this rate age, per 100k (15-49)."""
    if rate_age < 15 or rate_age > 49:
        return 0.0
    return P.ASFR_SHAPE_BY_GROUP[rate_age - rate_age % 5] / 5.0


# ---- Phase 2 step 1: the interfaces (docs/superpowers/specs/2026-10-12-demographics-phase2-consequences-design.md §1) -

def asfr_planned(rate_age):
    """Planned births' share at a calendar rate age, per 100k (P.ASFR_PLANNED_SHAPE)."""
    if rate_age < 15 or rate_age > 49:
        return 0.0
    return P.ASFR_PLANNED_SHAPE[rate_age - rate_age % 5] / 5.0


def asfr_unplanned(rate_age):
    """Unplanned births' share at a biological rate age, per 100k (P.ASFR_UNPLANNED_SHAPE)."""
    if rate_age < 15 or rate_age > 49:
        return 0.0
    return P.ASFR_UNPLANNED_SHAPE[rate_age - rate_age % 5] / 5.0


def slot_births(f, r, rb, tfr, planned_share):
    """One cohort's births (te_demog_slot_births). While the two schedules are the same object, today's line exactly;
    otherwise planned by the calendar rate age r and unplanned by the biological rate age rb."""
    if P.ASFR_PLANNED_SHAPE is P.ASFR_UNPLANNED_SHAPE:
        return f * asfr_shape(r) / 100000.0 * tfr
    mix = asfr_planned(r) * planned_share + asfr_unplanned(rb) * (1 - planned_share)
    return mix * f / 100000.0 * tfr


def band_value(table, age):
    """A {first age: value} table's value at an age (P.CAPACITY, P.HEALTH_NEED)."""
    return table[max(k for k in table if k <= age)]


def child_work_share(inp):
    """The 10-14s' participation by the childrens'-rights law (te_demog_child_work)."""
    for law, share in P.CHILD_WORK_SHARE.items():
        if law in inp.laws:
            return share
    return P.CHILD_WORK_SHARE_DEFAULT


def start_factor(inp, age):
    """The working-age start by calendar age (te_demog_enter_cal_band)."""
    if age < P.CHILD_WORK_AGE:
        return 0.0
    if age < P.WORKING_AGE:
        return child_work_share(inp)
    return 1.0


def women_rate_law(inp):
    """Women's participation by the women's-work family (#894): WOMEN_BASE up to MEN_RATE as its sum reaches
    WOMENS_WORK_FULL (te_demog_women_rate_law)."""
    s = min(max(inp.mods.get(P.WOMENS_WORK_TYPE, 0.0), 0.0) / P.WOMENS_WORK_FULL, 1.0)
    return s * (P.MEN_RATE - P.WOMEN_BASE) + P.WOMEN_BASE


def women_rate(inp):
    """The state's women's rate: its lower strata's women work at least WOMEN_LOWER, and where men are few more women
    work (phase 2 step 4, sex_women_add) (te_demog_women_rate)."""
    w = women_rate_law(inp)
    return (max(w, P.WOMEN_LOWER) - w) * inp.low_share + w + sex_women_add(inp.sex_balance)


def sex_rates(inp):
    """(women's, men's) rates in the working ages with call 3's participation inputs, each 0 to 1 (te_dg_wk_rf,
    te_dg_wk_rm in te_demog_work_setup)."""
    both = inp.mods.get(P.PARTICIPATION_TYPE, 0.0)
    rf = min(max(women_rate(inp) + both, 0.0), 1.0)
    rm = min(max(P.MEN_RATE + inp.mods.get(P.MALE_PARTICIPATION_TYPE, 0.0) + both, 0.0), 1.0)
    return rf, rm


def capacity_at(inp, age):
    """Capacity at a biological age with call 3's input: the table x (1 + it), 0 to 1 (te_demog_enter_bio_band)."""
    return min(band_value(P.CAPACITY, age) * max(1 + inp.mods.get(P.CAPACITY_TYPE, 0.0), 0.0), 1.0)


# ---- Phase 2 step 4: conscription, the youth bulge and sex balance (the consequences design §4) ----------------------

def sex_fewer_men(balance):
    """0 to 1: how far men are short, from SEX_FEWER_FROM men per 100 women to SEX_FEWER_FULL (te_demog_sex_fewer_men).
    None (no balance) is 0, and so is every balance while P.SEX_BALANCE_EFFECTS is off (held back), as for the other
    three sex-balance functions."""
    if balance is None or not P.SEX_BALANCE_EFFECTS:
        return 0.0
    return clamp((P.SEX_FEWER_FROM - balance) / (P.SEX_FEWER_FROM - P.SEX_FEWER_FULL), 0.0, 1.0)


def sex_more_men(balance):
    """0 to 1: how far men are in excess, from SEX_MORE_FROM to SEX_MORE_FULL (te_demog_sex_more_men)."""
    if balance is None or not P.SEX_BALANCE_EFFECTS:
        return 0.0
    return clamp((balance - P.SEX_MORE_FROM) / (P.SEX_MORE_FULL - P.SEX_MORE_FROM), 0.0, 1.0)


def sex_births(balance):
    """Children per woman's sex-balance term (te_demog_tfr_sex): the balance / SEX_FEWER_FROM, at most 1 and at least
    SEX_BIRTHS_FLOOR; 1 with no balance, or while P.SEX_BALANCE_EFFECTS is off."""
    if balance is None or not P.SEX_BALANCE_EFFECTS:
        return 1.0
    return clamp(balance / P.SEX_FEWER_FROM, P.SEX_BIRTHS_FLOOR, 1.0)


def sex_women_add(balance):
    """What the women's rate gains where men are few (te_demog_sex_women_add)."""
    return P.SEX_WOMEN_RATE * sex_fewer_men(balance)


def conscription_term(fam, people):
    """T on state_conscription_rate_mult (te_demog_conscription_term): the pool over people against the 1836 world's."""
    return clamp(fam / max(people, 1.0) / P.CONSCRIPTION_REF - 1, P.CONSCRIPTION_MIN, P.CONSCRIPTION_MAX)


def conscription_applied(term):
    """The conscription multiplier the census's pair applies (te_demog_consequences_apply): the term while
    P.CONSCRIPTION_EFFECTS is on and |term| reaches CONSCRIPTION_CUT, else 0 (held back, or too small for a line)."""
    return term if P.CONSCRIPTION_EFFECTS and abs(term) >= P.CONSCRIPTION_CUT else 0.0


def youth_applied(y):
    """The youth-bulge modifier's multiplier: y while P.YOUTH_BULGE_EFFECTS is on and y reaches YOUTH_CUT, else 0."""
    return y if P.YOUTH_BULGE_EFFECTS and y >= P.YOUTH_CUT else 0.0


def youth_share(ring):
    """The share of people of calendar age YOUTH_AGES (te_demog_youth_share: bands 4 and 5)."""
    rows = ring.by_age()
    total = sum(f + m for _a, f, m in rows)
    lo, hi = P.YOUTH_AGES
    return sum(f + m for a, f, m in rows if lo <= a <= hi) / max(total, 1.0)


def youth_bulge(share, unemployment):
    """y, the youth-bulge modifier's multiplier (te_demog_youth_bulge_now)."""
    return (clamp((share - P.YOUTH_FROM) / P.YOUTH_SPAN, 0.0, 1.0)
            * clamp(unemployment / P.YOUTH_UNEMPLOYMENT_FULL, 0.0, 1.0))


def consequence_figures(ring, unemployment=0.0):
    """{fam, faw, people, pool_share, pool_men_share, term, youth, y, sex_balance, fewer, more, births}: phase 2 step
    4's figures for a ring after its step (ages after the step; the pool sums by _refresh_denominators)."""
    people = ring.people()
    men = sum(m for _a, _f, m in ring.by_age())
    sb = structure(ring)["men_per_100_women"]
    share = youth_share(ring)
    return {"fam": ring.fam, "faw": ring.faw, "people": people, "pool_share": ring.fam / max(people, 1.0),
            "pool_men_share": ring.fam / max(men, 1.0), "term": conscription_term(ring.fam, people),
            "youth": share, "y": youth_bulge(share, unemployment), "sex_balance": sb,
            "fewer": sex_fewer_men(sb), "more": sex_more_men(sb), "births": sex_births(sb)}


def pension_kind(inp):
    """1 under Old Age Pension; 2 under UBI or Post-Scarcity (no pension age); else 0 (te_demog_pension_kind)."""
    if P.PENSION_LAW in inp.laws:
        return 1
    if any(law in inp.laws for law in P.NO_PENSION_AGE_LAWS):
        return 2
    return 0


def working_ages_end(inp, old_age):
    """(the end of the working ages, whether the after-pension share applies past it, whether those past it are
    pensioners): te_demog_work_setup. With no pension law the working ages run to capacity's end (late-game §2.1), which
    never comes: NO_WORKING_AGE_END."""
    kind = pension_kind(inp)
    if kind == 1:
        return (P.PENSION_AGE["standard"] if inp.pension_age is None else inp.pension_age), True, True
    if kind == 2:
        return old_age, True, False
    return float(P.NO_WORKING_AGE_END), False, False


def work_figures(ring, inp, old_age):
    """Phase 2 step 1's figures over ring.by_age() (ages after the step; the pool at 150): te_demog_work_slot and
    te_demog_work_finish. The biological age is the calendar one until phase 3."""
    end, after_on, bill_on = working_ages_end(inp, old_age)
    rate_f, rate_m = sex_rates(inp)
    total = wa = workers = pens = need = 0.0
    past = split_f = split_all = 0.0           # phase 2 step 2: workers past the end; the work-death split's sums
    lo, hi = P.WORK_SPLIT_AGES
    for a, f, m in ring.by_age():
        ab = a                                  # the biological index (phase 3: less the band's deficit)
        p = f + m
        total += p
        need += p * band_value(P.HEALTH_NEED, ab)
        start = start_factor(inp, a)
        share = 1.0
        if a >= end:
            if after_on:
                share = P.AFTER_PENSION_SHARE
            if bill_on:
                pens += p
        elif start > 0:
            wa += p
        k = start * capacity_at(inp, ab) * share
        workers += (f * rate_f + m * rate_m) * k
        if a >= end:
            past += (f * rate_f + m * rate_m) * k
        if lo <= a <= hi:
            split_f += f * rate_f * k
            split_all += (f * rate_f + m * rate_m) * k
    return {"wa_share": wa / max(total, 1.0), "at_work": workers / max(wa, 1.0),
            "pensioners": pens / max(total, 1.0), "need": need / max(total, 1.0) / P.HEALTH_NEED_1836,
            "past": past / max(total, 1.0),
            "fws_work": split_f / split_all if split_all > 0 else None}


def wf_target(figures):
    """The workforce share on the engine's scale (te_demog_wf_target; step 2's target less the pops' bases)."""
    return P.WORKFORCE_SCALE * figures["wa_share"] * figures["at_work"]


# ---- Phase 2 step 2: the workforce term, the pension setting and the bills (te_demog_work_effects.txt) ---------------

def workforce_term_target(figures):
    """W's target: the census's target less the define's base (te_demog_wf_term_target; calls 3 and 4)."""
    return wf_target(figures) - P.WORKING_ADULT_BASE


def workforce_term(target_w, prev_w, remainder):
    """W after one census step (te_demog_workforce_refresh): prev_w moved toward target_w by at most P.WF_RAMP_STEP,
    then raised so the lowest pop base plus W plus the remainder (the lines on top) stays at P.WF_POP_RATIO_MIN.
    prev_w is the term in force, or the moved lines' pair it replaces when it first lands."""
    w = prev_w + clamp(target_w - prev_w, -P.WF_RAMP_STEP, P.WF_RAMP_STEP)
    return max(w, P.WF_POP_RATIO_MIN - P.POP_BASE_RATIO_MIN - remainder)


def engine_total(figures, wbase, remainder=0.0):
    """The workforce ratio the census aims a state at on the engine's scale: its target, the pops' own bases' offset
    from the define (call 4) and the lines left on top (te_demog_wf_engine_target)."""
    return wf_target(figures) + (wbase - P.WORKING_ADULT_BASE) + remainder


def outside_full_total(wbase, lines, remainder=0.0):
    """The same state's ratio outside Full: the pops' bases and every moved line at its flat value (the pair)."""
    return wbase + lines + remainder


def pension_position_age(position, current_age=None, old_age=None):
    """A position's pension age for this year (te_demog_pension_age_refresh): the fixed ages, or for a linked one the
    country's old-age threshold less P.PENSION_LINK_OFFSET, at least P.PENSION_LINK_FLOOR, moving at most
    P.PENSION_LINK_STEP from current_age (None: it lands at once). None old_age (no census yet): the floor."""
    if position not in P.PENSION_LINKED:
        return float(P.PENSION_AGE[position])
    target = P.PENSION_LINK_FLOOR if old_age is None else max(old_age - P.PENSION_LINK_OFFSET, P.PENSION_LINK_FLOOR)
    if current_age is None:
        return float(target)
    # a linked position starts from at least the floor (te_demog_pension_age_from_position: leaving Early raises it)
    current_age = max(current_age, P.PENSION_LINK_FLOOR)
    return float(current_age + clamp(target - current_age, -P.PENSION_LINK_STEP, P.PENSION_LINK_STEP))


def pension_bill_gdp_share(pensioners, social_security_level):
    """The pension bill as a share of GDP a year: the pensioners' share x B (late-game §5.1)."""
    return pensioners * P.PENSION_B_PER_LEVEL * social_security_level


def health_term(need, techs=frozenset()):
    """The health bill's multiplier on the health system's institution cost (§2.4): the need term, capped above, and
    the chronic-treatment technologies; longevity care is phase 3's."""
    need_term = min(P.HEALTH_NEED_WEIGHT * (need - 1.0), P.HEALTH_NEED_CAP)
    return need_term + P.HEALTH_TECH_STEP * sum(1 for t in P.HEALTH_TECHS if t in techs)


def old_age_threshold(q):
    """The age with OLD_AGE_REMAINING years of life left (late-game §1.5) from one sex's group rates: remaining life at
    each group start from OLD_AGE_FROM, linear between starts. Radix 100,000, as te_demog_old_age_pass."""
    l, py, at = 100000.0, 0.0, []
    for g, (start, n) in enumerate(P.GROUPS):
        if start >= P.OLD_AGE_FROM:
            at.append((start, l, py))
        qq = q[g] / 100000.0
        pn = (1.0 - qq) ** n
        py += l * n if qq == 0 else l * (1 - qq / 2) * (1 - pn) / qq
        l *= pn
    prev = None
    for start, l_s, py_s in at:
        e = (py - py_s) / max(l_s, 0.00001)
        if e <= P.OLD_AGE_REMAINING:
            if prev is None:
                return float(start)
            s0, e0 = prev
            return (e0 - P.OLD_AGE_REMAINING) / max(e0 - e, 0.00001) * (start - s0) + s0
        prev = (start, e)
    return float(at[-1][0])


def old_age(qf, qm):
    """The state's old-age threshold: women's and men's averaged (te_dg_old_age)."""
    return (old_age_threshold(qf) + old_age_threshold(qm)) * 0.5


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
    fam: float = 0.0                    # the pool's men (phase 2 step 4): calendar POOL_FROM+, biological POOL_TO or less
    faw: float = 0.0                    # the women of the same ages: the war dead's women's share
    total: float = 0.0
    medicine: dict | None = None        # the drifted access and treatments (medicine_drift); None = at the targets

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
    """The panel's Gini (§4.1): the equality the bands show, scaled down for the spread inside them."""
    return clamp(1 - P.GINI_SHOWN_EQUALITY * (1 - grouped), 0.0, 1.0)


def wealth_band(wealth):
    """The Gini's band (1..GINI_BANDS) for a pop's wealth: the first knot at or above it."""
    for i, knot in enumerate(P.GINI_BAND_KNOTS, start=1):
        if wealth <= knot:
            return i
    return P.GINI_BANDS


def stand_in_income(wealth, costs):
    """§4.1's income per head at a pop's wealth: the buy package's cost / 100, linear between
    GINI_INCOME_KNOTS, flat below the first, held at the top wealth level's above it. `costs` is
    {wealth: package cost} (demographics_harness.buy_package_costs). The census adds people /
    GINI_INCOME_UNIT times this (te_demog_gini_band_add)."""
    knots = P.GINI_INCOME_KNOTS
    w = min(wealth, P.GINI_TOP_WEALTH)
    if w <= knots[0]:
        return costs[knots[0]] / 100
    for x0, x1 in zip(knots, knots[1:]):
        if w <= x1:
            y0, y1 = costs[x0] / 100, costs[x1] / 100
            return y0 + (w - x0) * (y1 - y0) / (x1 - x0)
    raise AssertionError("unreachable: the last knot is the top wealth level")


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
    equilibrium; nrr and life_table leave them out (a documented approximation). Medicine starts at its targets,
    as the script's seed sets it (te_demog_medicine_at_target before te_demog_prepare), whatever inp.medicine holds.
    """
    inp = replace(inp, medicine=None)
    qf, qm, mmr = group_rates(inp)
    e0 = life_table(qf)["e0"] * 0.5 + life_table(qm)["e0"] * 0.5
    tfr = fertility(inp, e0)["tfr"]
    d = growth_factor(nrr(tfr, qf))
    ring = Ring(year=year)
    ring.medicine = medicine_targets(inp)
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


def in_pool(age, bio_age):
    """The conscription pool's ages (phase 2 step 4; late-game call 21): calendar POOL_FROM or more and biological
    POOL_TO or less. The war dead come from the same ages."""
    return age >= P.POOL_FROM and bio_age <= P.POOL_TO


def _refresh_denominators(ring):
    """Class and pool sums for next year's flows, by the age each cohort has now.

    Next year's step applies the flows by rate age (a - 1), so it divides by exactly the
    cohorts it applies them to. The age-149 cohort and the pool are left out: they are
    folded, not flowed. The pool's sums (fam, faw) are also the conscription term's input (te_dg_fam, te_dg_faw).
    """
    ring.class_f = [0.0] * len(P.MIGRANT_CLASSES)
    ring.class_m = [0.0] * len(P.MIGRANT_CLASSES)
    ring.fam = ring.faw = 0.0
    for a, f, m in ring.by_age():
        if a > N - 2:
            continue
        c = class_of(a)
        ring.class_f[c] += f
        ring.class_m[c] += m
        if in_pool(a, a):                       # the biological index is the calendar one until phase 3
            ring.fam += m
            ring.faw += f


def rate_term(target, bare, absorbed=0.0, other=0.0, on_top=0.0, added=0.0):
    """The census's births or deaths modifier for one state (phase 2 step 4). Returns (M, clamped).

    The engine gives each pop bare x max(0, 1 + its terms + M) (growth probe), so over a state M adds
    M x bare. M = target / bare - 1 - absorbed / bare makes the engine's events the model's (target)
    plus every term added on top, at the bare curve's weight. All three are in the same units (the walk's:
    events a month x 100,000). `on_top` is the state-level lines left on top (pollution, devastation, global
    warming, events): taking on_top x (1 - target / bare) off M as well makes each of them act on the census's
    rate, as its tooltip reads (owner, 2026-10-11), exactly for every pop. A pop's own lines on top (severe
    starvation, workplace lines) stay at the bare curve's weight: one state-wide M can't scale them without
    moving the other pops' rates. A line past RATE_TOTAL_MIN scales as RATE_TOTAL_MIN: the engine's rate can't
    go lower. `added` is the moved lines' on-top family (owner, 2026-10-11; the engine-lines plan): script-only, so the
    engine doesn't apply it, and the census adds it at its own rate, + added x target / bare. `other` is the state read without the census's and fast mode's
    terms: other + M stays at or above RATE_TOTAL_MIN, M never goes below 0 when other alone is
    past it, and M stays at or below RATE_TERM_MAX.
    """
    if bare <= 0:
        return 0.0, False
    m = target / bare - 1 - absorbed / bare - max(on_top, P.RATE_TOTAL_MIN) * (1 - target / bare) + added * target / bare
    lo = min(0.0, P.RATE_TOTAL_MIN - other)
    if m < lo:
        return lo, True
    if m > P.RATE_TERM_MAX:
        return P.RATE_TERM_MAX, True
    return m, False


def on_top_scale(engine, target):
    """How far the engine's births or deaths over a step ran from the model's target, as a scale for the
    step's rates: engine / target - 1, clamped to ON_TOP_SCALE_MIN..ON_TOP_SCALE_MAX; 0 with no target."""
    if target <= 0:
        return 0.0
    return clamp(engine / target - 1, P.ON_TOP_SCALE_MIN, P.ON_TOP_SCALE_MAX)


def window_events(end_rate, start_rate=None):
    """The engine's expected births or deaths over a step's window (the trapezoid, owner 2026-10-11; #894; the review
    of #907). The walk's snapshot is the engine's rate on the step's day; the window takes WINDOW_START_WEIGHT x the
    rate the last step left in force (after it set M, and fast mode its term) and the rest x today's, both in the same
    units (a rate x the window, or a rate). Each end is the engine's whole rate, so every line that moved inside the
    window counts at the engine's own weight: the lines on top, the absorbed lines M nets, the bare curves. With no
    start rate (the first step after a seed, a new state, an old save) it is the snapshot. Never below 0. The script's
    te_demog_window_events."""
    if start_rate is None:
        return end_rate
    return max(0.0, P.WINDOW_START_WEIGHT * start_rate + (1 - P.WINDOW_START_WEIGHT) * end_rate)


def on_top_split(end, start=None):
    """(events, the whole state's part, severe starvation's part) over a step's window (the Causes of Death plan, Task 6;
    the script's te_demog_on_top_split). end, start: (the engine's rate, the pops' own lines in it, severe
    starvation's part of those) at that end of the window, in one unit; start None where the window took the
    snapshot. Each part is weighted as window_events weighs the rate; the whole state's part is the events less the
    pops' own lines, at least 0."""
    events = window_events(end[0], None if start is None else start[0])
    if start is None:
        own, severe = end[1], end[2]
    else:
        w = P.WINDOW_START_WEIGHT
        own, severe = w * start[1] + (1 - w) * end[1], w * start[2] + (1 - w) * end[2]
    return events, max(0.0, events - own), severe


def starvation_value(food_security):
    """The engine's starvation value for a pop at this food security: clamp((FOOD_SECURITY_STARVATION_THRESHOLD - food
    security) x STARVATION_EFFECTS_SCALING_FACTOR, 0, STARVATION_VALUE_MAX) (vanilla 00_defines.txt's comment). The
    save stores it per pop as food_security={ starvation= } (the famine probe, 2026-10-11: equal on every starving
    pop, to 5e-06)."""
    return clamp((P.FOOD_SECURITY_STARVATION_THRESHOLD - food_security) * P.STARVATION_EFFECTS_SCALING_FACTOR,
                 0.0, P.STARVATION_VALUE_MAX)


def starvation_terms(food_security):
    """(births, deaths) the engine adds for a pop at this food security (vanilla code static modifiers): each penalty x
    the pop's starvation value, severe_starvation_penalty's below the severe threshold (0.5 to 1) and
    starvation_penalty's above it (at most STARVATION_MILD_CAP). The famine probe (2026-10-11) measured the severe
    one scaled, not in full. Exact; the script reads both in STARVATION_BUCKET steps of food security."""
    s = starvation_value(food_security)
    if food_security < P.FOOD_SECURITY_SEVERE_STARVATION_THRESHOLD:
        return P.STARVATION_SEVERE["births"] * s, P.STARVATION_SEVERE["deaths"] * s
    if food_security < P.FOOD_SECURITY_STARVATION_THRESHOLD:
        s = min(s, P.STARVATION_MILD_CAP)
        return P.STARVATION_MILD["births"] * s, P.STARVATION_MILD["deaths"] * s
    return 0.0, 0.0


def model_crude_rates(inp, year=1836):
    """(births, deaths) per 1,000 a year of the stable population of the state's inputs: the census's
    own rates for a state with no census in the save (demographics_harness.py predict)."""
    ring = seed(inp, year, 100000.0)
    out = step(ring, inp, year + 1)
    return out["births_model"] / 100.0, out["deaths_model"] / 100.0


def step(ring, inp, year, engine_pop=None, war_dead=0.0, kills=0.0, migration=0.0, rates=None,
         births_scale=0.0, deaths_scale=0.0):
    """One yearly step (§2.1), in the script's order: medicine drifts before the rates (te_demog_medicine_drift
    before te_demog_prepare). Returns the year's figures.

    engine_pop None = no scaling (a pure model run). war_dead, kills and migration are
    people this year (migration net, signed); the residual noise rule is the caller's.
    Flows (war, kills, migration) are applied by rate age to the counts before deaths.
    rates = (qf, qm, mmr, tfr, profile) replays an in-game step with the rates the game
    logged instead of recomputing them from inputs.
    births_scale and deaths_scale (phase 2 step 4, the script's te_dg_bz / te_dg_dz) scale the
    year's children per woman and the cause multipliers, so the ring places the events the engine
    added on top of the model: newborns, and deaths by the model's age pattern. The life table,
    "tfr" and the *_model totals stay the model's own; "tfr_shown" is the scaled one.
    """
    assert ring.year is not None and year == ring.year + 1, "one step per year"
    if rates is None:
        # the sex balance the step's fertility and women's rate read (te_demog_sex_births_store): the ring's before its
        # sweep, which is the census's last figure (phase 2 step 4)
        inp = replace(inp, sex_balance=structure(ring)["men_per_100_women"])
        # medicine spreads (the Causes of Death plan): the drifted values move, then the year's rates use them
        ring.medicine = medicine_drift(ring.medicine, inp)
        inp = replace(inp, medicine=ring.medicine)
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
    # planned births' share of the year's children per woman (te_dg_sh_pl): the birth line's two-term form reads it
    if rates is None:
        planned_share = fert["planned"] / fert["tfr"] if fert["tfr"] else 1.0
    else:
        assert P.ASFR_PLANNED_SHAPE is P.ASFR_UNPLANNED_SHAPE, "a replay logs one schedule"
        planned_share = 1.0
    tfr_model = tfr
    q0_model = (qf[0] + qm[0]) / 200.0   # the life table's infant mortality, before the scales
    tfr = tfr * (1 + births_scale)
    if deaths_scale:
        if rates is None:
            mult = cause_multipliers(inp)
            work_f, work_m = work_split(inp, mult["work"])
            k = 1 + deaths_scale
            qf, qm = rates_from_multipliers({c: v * k for c, v in mult.items()}, work_f * k, work_m * k)
        else:
            qf = [min(100000.0, q * (1 + deaths_scale)) for q in qf]
            qm = [min(100000.0, q * (1 + deaths_scale)) for q in qm]
    maternal = 0.0
    s = ring.scale
    war_m = clamp(war_dead * P.WAR_DEAD_MALE_SHARE / ring.fam, 0, 0.5) if ring.fam else 0.0
    war_f = clamp(war_dead * (1 - P.WAR_DEAD_MALE_SHARE) / ring.faw, 0, 0.5) if ring.faw else 0.0
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
        b = slot_births(f, r, r, tfr, planned_share)
        births += b
        maternal += b * mmr / 100000.0
        f2 = f * (1 - qf[g] / 100000.0) - b * mmr / 100000.0
        m2 = m * (1 - qm[g] / 100000.0)
        deaths += (f - f2) + (m - m2)
        if in_pool(r, r):                       # the pool's ages by rate age (phase 2 step 4, §4.2)
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
    # the newborns' split: the constants, or the sex ratio at birth with prenatal sexing (phase 2 step 3b)
    girls, boys = newborn_split(inp)
    ring.f[open_k] = births * girls / 100000.0
    ring.m[open_k] = births * boys / 100000.0
    ring.year = year
    raw = sum(ring.f) + sum(ring.m) + ring.pool_f + ring.pool_m
    ring.scale = (engine_pop / raw) if (engine_pop is not None and raw > 0) else 1.0
    _refresh_denominators(ring)
    ring.total = ring.people()
    return {"births": births, "deaths": deaths, "tfr": tfr_model, "e0": e0, "e0_f": lt_f["e0"], "e0_m": lt_m["e0"],
            "e65": (lt_f["e65"] + lt_m["e65"]) / 2, "q0_per_1000": q0_model,
            "fertility": fert, "raw": raw,
            "tfr_shown": tfr, "maternal": maternal,
            "births_model": births / (1 + births_scale),
            "deaths_model": (deaths - maternal) / (1 + deaths_scale) + maternal / (1 + births_scale)}


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
