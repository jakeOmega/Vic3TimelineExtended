"""Demographics model parameters: the one source for the harness and the generator.

Spec: docs/superpowers/specs/2026-10-08-demographics-design.md. Every number here is a
starting proposal (the spec's header); calibration edits this file, then
`python3 scripts/generators/gen_demographics.py` rewrites the script that mirrors it.

Units. Death rates are yearly probabilities per 100,000 people, fertility shapes per
100,000, so every literal the generator writes stays within the engine's five decimals
(scripting_best_practices.md: values are stored in units of 1e-5).
"""

RING_YEARS = 150            # spec §1: slots reach about age 150; 150+ folds into a pool
COHORT_WIDTH = 1            # spec §1 decision rule; owner to confirm (§13). Only 1 is built.
FEMALE_BIRTH_PER_100K = 48780   # 100 girls per 205 births (§3)
MALE_BIRTH_PER_100K = 51220

# Abridged age groups (start, width). Rates are constant inside a group.
GROUPS = [(0, 1), (1, 4)] + [(a, 5) for a in range(5, 150, 5)]
GROUP_STARTS = [g[0] for g in GROUPS]


def group_of(age):
    """Index into GROUPS for a rate age 0..149 (150+ uses the last group)."""
    age = min(age, 149)
    for i in range(len(GROUPS) - 1, -1, -1):
        if age >= GROUPS[i][0]:
            return i
    return 0


# ---- Mortality: five causes (§2.4), base schedules per 100k a year ----------------
# The base is a population with literacy 0, SoL 8 or below and no medical technology,
# law or institution; every multiplier is 1 there. Values are per group, in GROUPS order
# (31 entries). The women's and men's lists differ where §2.4 says they do.
def _by_group(points):
    """Expand {start_age: rate} breakpoints to one value per group (step function)."""
    out, cur = [], 0
    for start, _w in GROUPS:
        if start in points:
            cur = points[start]
        out.append(cur)
    return out


# Infection and malnutrition: mostly under 5; also 5-14 and the old.
INFECTION = {
    "f": _by_group({0: 19000, 1: 4200, 5: 1000, 10: 550, 15: 750, 45: 900, 65: 1500, 80: 2800}),
    "m": _by_group({0: 21000, 1: 4300, 5: 1000, 10: 550, 15: 750, 45: 950, 65: 1600, 80: 2900}),
}
# Work accidents per 100k people aged 15-64, before the split between the sexes (§2.4).
WORK_BASE = _by_group({0: 0, 15: 160, 65: 0})
# Other external causes: violence, traffic, accidents; 15-44 men three times women.
EXTERNAL = {
    "f": _by_group({0: 60, 5: 40, 15: 60, 45: 50, 65: 80}),
    "m": _by_group({0: 70, 5: 50, 15: 180, 45: 110, 65: 110}),
}
# Chronic and old age: rising from 40, doubling about every 8 years; men higher.
_CHRONIC_F = {0: 0, 5: 60, 20: 120, 30: 180, 40: 320, 45: 480, 50: 720, 55: 1100, 60: 1700,
              65: 2600, 70: 4000, 75: 6200, 80: 9600, 85: 14800, 90: 22000, 95: 32000,
              100: 42000, 105: 50000, 110: 56000}
CHRONIC = {
    "f": _by_group(_CHRONIC_F),
    "m": _by_group({a: (v * 13) // 10 for a, v in _CHRONIC_F.items()}),
}
# Maternal deaths per 100k births (one in 150 at the base).
MATERNAL_PER_100K_BIRTHS = 670

# ---- Fertility (§2.3) -------------------------------------------------------------
# Age-specific shape over rate ages 15-49 by five-year group, per 100k, summing to
# 100,000 over the 35 single years (each single year takes its group's value / 5).
ASFR_SHAPE_BY_GROUP = {15: 6000, 20: 22000, 25: 25000, 30: 21000, 35: 15000, 40: 8500, 45: 2500}
WEALTH_TFR_LOW, WEALTH_TFR_LOW_SOL = 6.2, 8      # children per woman at SoL 8 or below
WEALTH_TFR_HIGH, WEALTH_TFR_HIGH_SOL = 3.5, 35   # what wealth alone does at SoL 35+
EDUCATION_WEIGHT = 0.4        # desired x (1 - 0.4 x literacy)
SURVIVAL_WEIGHT = 0.4         # desired x (1 - 0.4 x (e0 - 30) / 50), clamped 0..1
URBAN_WEIGHT = 0.2            # desired x (1 - 0.2 x urban share)
MEANS_CAP = 0.95
# Every other shift to the means comes through one modifier type, state_fertility_means_add
# (common/modifier_type_definitions/demographics_modifier_types.txt), so history, events and
# later measures can grant it to any country. Family Limitation (te_demog_family_limitation)
# carries this much; France starts with it (§2.6: its transition began around 1800).
FAMILY_LIMITATION_MEANS = 0.6

# ---- Wealth Concentration (§4.2): land tenure, by base law -------------------------
# Vanilla's variants (`parent = law_x`: Manorialism, Latifundias, Expanded Latifundias,
# Homesteading) take their parent's value; the generator expands them from the laws'
# parent fields. The spec's "Homesteading -10" is its parent, Peasant Proprietorship.
LAND_TENURE = {
    "law_serfdom": 15, "law_tenant_farmers": 5, "law_commercialized_agriculture": 0,
    "law_peasant_proprietorship": -10, "law_collectivized_agriculture": -20,
}

# ---- Mortality inputs as modifier types (modifier-types design, stage 1) -----------
# Laws, technology and institutions reach the census's causes of death only through these
# registered state types (common/modifier_type_definitions/demographics_modifier_types.txt);
# their values sit on their carriers in the game files, and demographics_modifiers.py resolves a
# state's totals. A tech's or law's modifier reaches every state the country owns (states inherit
# country modifiers); a law's institution_modifier or an institution's own modifier is per
# investment level and reaches incorporated states only. The census reads each with modifier:.
ACCESS_TYPE = "state_health_care_access_add"
MEDICINE_CAUSES = ("infection", "maternal", "chronic")
TREATMENT_TYPE = {cause: f"state_{cause}_treatment_add" for cause in MEDICINE_CAUSES}
# The plain per-cause multipliers: 1 + the cause's type, floored.
MORTALITY_TYPES = {
    "external": ("state_external_mortality_mult",),
    "work": ("state_work_mortality_mult",),
    "chronic": ("state_chronic_mortality_mult",),
}
DEMOG_MORTALITY_TYPES = (
    ACCESS_TYPE, *TREATMENT_TYPE.values(),
    *MORTALITY_TYPES["external"], *MORTALITY_TYPES["work"], *MORTALITY_TYPES["chronic"],
)

# ---- Fertility inputs as modifier types (modifier-types design, stage 2) -----------
# Contraception: the methods families have, added to TRADITIONAL_MEANS (the techs' lines add, so
# research order matters); the census scales the sum by literacy. The means shift: laws, history
# (Family Limitation), events and measures, added after literacy. Both are state types read with
# modifier:, their values on their carriers (demographics_modifiers.py).
CONTRACEPTION_TYPE = "state_contraception_add"
MEANS_SHIFT_TYPE = "state_fertility_means_add"
DEMOG_FERTILITY_TYPES = (CONTRACEPTION_TYPE, MEANS_SHIFT_TYPE)
DEMOG_TYPES = DEMOG_MORTALITY_TYPES + DEMOG_FERTILITY_TYPES
# The means to plan a family (§2.3): (TRADITIONAL_MEANS + state_contraception_add, at most 1) x
# (MEANS_ACCESS_BASE + (1 - MEANS_ACCESS_BASE) x literacy) + state_fertility_means_add, within
# 0..MEANS_CAP. Traditional methods everyone has; the techs' lines add to them (the Pill without
# vulcanization is 0.4 + the Pill's line). Values on the carriers: demographics_modifiers.py.
TRADITIONAL_MEANS = 0.4
MEANS_ACCESS_BASE = 0.3

# ---- Cause multipliers from state inputs (§2.4) -----------------------------------
# Medicine for infection, maternal and chronic deaths is 1 - access x treatment (the
# modifier-types design, Decision 1). Access is how much of the population a state's medicine
# reaches: this base (markets and charity, everywhere, colonies and 1836 too) plus
# state_health_care_access_add, at most 1. Treatment is the cause's
# country_<cause>_treatment_add, at most its cap. The values of both live on their carriers in
# the game files (demographics_modifiers.py); calibrated with `demographics_harness.py medicine`.
BASE_ACCESS = 0.4
TREATMENT_CAP = {"infection": 0.95, "maternal": 0.99, "chronic": 0.85}   # chronic 0.85: phase 2 step 4 (augmentation)
# Every other law, technology or institution term is 1 + its types' sum, at least this.
MORTALITY_MULT_FLOOR = 0.2
# Nutrition: SoL lowers infection from x1 at SoL 8 to x0.6 at SoL 35; chronic x1 to x0.85.
SOL_INFECTION_AT_HIGH = 0.6
# Poverty (phase 2 calibration, 2026-10-10): below SoL 9 infection rises, to x1.75 at SoL 5 and below.
# Most of the 1836 world sits at SoL 6-9, and the high-SoL term above is flat below SoL 8, so without this the
# census gave China, India and Mexico Britain's life expectancy and the world +1.4% a year against
# history's 0.4-0.8%. Fitted against Clio Infra's life expectancy and Maddison's population on the gate
# run's 1837, 1857 and 1887 saves, with each state's crowding term as the save holds it (continuous, below): the
# strength at which China (SoL 6 by 1887 in that game) grows as Maddison's China did in peacetime, about +0.3-0.4%
# a year (1820-1840, 1870-1910). x2 would shrink it (docs/testing/demographics-history-check-2026-10-10.md).
POVERTY_INFECTION_SOL = 9          # x1 at and above
POVERTY_INFECTION_FLOOR_SOL = 5    # POVERTY_INFECTION_AT_FLOOR at and below
POVERTY_INFECTION_AT_FLOOR = 1.75
SOL_CHRONIC_AT_HIGH = 0.85
LITERACY_INFECTION_WEIGHT = 0.3   # mothers' literacy: infection x (1 - 0.3 x literacy)
# Crowding (owner, 2026-10-10: a function of how crowded the state is, not a switch): infection rises by the
# state's migration penalty from crowding. migration_crowding takes state_migration_pull_mult -0.1 a unit of its
# multiplier (extra_modifiers.txt), which is 4.5 r^2 below ten times the floor density and linear above
# (migration_crowding_mult, r the state's place between the floor and ten times it). So a state just past the
# floor adds almost nothing, the 1837 median crowded person +4%, a state at ten times the floor +45%. The Ministry
# of Urban Planning and Urban Engineering (sewerage, steel frames) lower it through the crowding itself.
MIGRATION_CROWDING_PULL_PER_MULT = 0.1   # the modifier's pull penalty a unit of multiplier (a test pins it)
CROWDING_INFECTION_PER_PULL = 1.0        # infection rises by the share migration attraction falls
CROWDING_INFECTION_MAX = 0.5             # at most +50%, just past ten times the floor density (a guess)

# Women's share of the workforce by women's-rights law, for splitting work deaths (§2.4).
FEMALE_WORK_SHARE = {
    "law_no_womens_rights": 0.1, "law_women_in_the_fields": 0.25, "law_women_own_property": 0.3,
    "law_women_in_the_workplace": 0.45, "law_womens_suffrage": 0.47, "law_protected_class": 0.48,
}
FEMALE_WORK_SHARE_DEFAULT = 0.1

# ---- War dead and migrants (§2.5) -------------------------------------------------
WAR_DEAD_MALE_SHARE = 0.95
WAR_DEAD_AGES = (18, 40)
RESIDUAL_NOISE_SHARE = 0.003   # a residual under 0.3% of the population is model error
# The engine's starvation scaling (vanilla 00_defines.txt, 1.14.5; the mod leaves these alone):
# below the first threshold a pop is in mild starvation and starvation_penalty applies scaled by
# (threshold - food security) x the factor, at most (0.4 - 0.2) x 2.5 = 0.5; below the second,
# severe_starvation_penalty applies in full. The expected births and deaths that the migration
# residual is measured against read these (gen_demographics.py, engine_rate_terms).
FOOD_SECURITY_STARVATION_THRESHOLD = 0.4
FOOD_SECURITY_SEVERE_STARVATION_THRESHOLD = 0.2
STARVATION_EFFECTS_SCALING_FACTOR = 2.5
STARVATION_BUCKET = 0.05   # mild starvation is read in food-security steps this wide, at each step's middle

# ---- phase 2 step 4: the census sets the engine's births and deaths --------------------------
# docs/superpowers/plans/2026-10-10-demographics-phase2-engine-rates.md §2. The engine adds every term
# into one (1 + total) per pop, linear from -0.9 (growth probe) to far above +1.0 (the 12x fast run), floored
# at 0. Owner, 2026-10-10: the poverty term replaces the curve's starving slope below SoL 4, and deaths added
# on top fall by the model's age pattern (the step's deaths scale).
RATE_TOTAL_MIN = -0.8         # the state read with M in it stays at or above this (-0.9 less literacy's -0.1)
RATE_TERM_MAX = 3.0           # a guard against a nonsense target, not a measured limit
ON_TOP_SCALE_MIN = -0.9       # the step's births and deaths scales (the engine's events over the model's target)
ON_TOP_SCALE_MAX = 4.0
LITERACY_BIRTH_PENALTY = -0.1 # literacy_penalty's state_birth_rate_mult (the mod's REPLACE keeps vanilla's)
STARVATION_MILD = {"births": -0.7, "deaths": 0.6}     # starvation_penalty (vanilla code static modifier)
STARVATION_SEVERE = {"births": -0.9, "deaths": 1.0}   # severe_starvation_penalty
STARVATION_MILD_CAP = 0.5     # (threshold - severe threshold) x scaling factor: vanilla's comment
# Phase 2 step 4 (plan §3 (a)): carriers whose birth or mortality lines stay on top of the census's term.
# Every other law, technology or institution line nets to zero (Tasks 6 and 8). The women's-rights laws leave
# this list in Task 8, once Task 7's natural-fertility term carries their effect.
ENGINE_LINES_ON_TOP = frozenset({
    # women's rights: on top until the census's term exists (owner, 2026-10-10)
    "law_no_womens_rights", "law_women_in_the_fields", "law_women_in_the_workplace", "law_womens_suffrage",
    "law_protected_class",
    # the family-policy laws §8.1 has yet to re-express as census terms
    "law_pro_natalist_subsidies", "law_population_control_measures", "law_communal_child_rearing",
    # late-era lines with no census term; revisit with step 6
    "law_legal_limbo", "law_basic_protections", "law_comprehensive_rights", "law_full_equality_and_protection",
    "law_state_eugenics_program", "second_wave_feminism", "sexual_revolution", "mental_health_awareness",
    "biological_immortality", "mind_backups",
})
# Age classes for migrant profiles: (first age, last age) by rate age (the age before the step).
MIGRANT_CLASSES = [(0, 14), (15, 17), (18, 35), (36, 59), (60, 150)]
# Share of each kind's migrants per class (each kind's weights sum to 1). The family and refugee
# kinds split evenly between women and men; the labour kind's split is the LABOUR_FEMALE_SHARE range.
MIGRANT_PROFILE = {
    "labour": {"weights": [0.0, 0.05, 0.9, 0.05, 0.0]},
    "family": {"weights": [0.35, 0.05, 0.35, 0.22, 0.03]},
    "refugee": {"weights": [0.27, 0.05, 0.3, 0.25, 0.13]},
}
LABOUR_FEMALE_SHARE_MIN, LABOUR_FEMALE_SHARE_MAX = 0.1, 0.6
FAMILY_TRANSPORT_TECHS = {"paddle_steamer": 0.1, "railways": 0.1, "combustion_engine": 0.15}
FAMILY_BASE = 0.2                 # families' weight before transport, rights and chain migration
FAMILY_RIGHTS_WEIGHT = 0.2        # x women's work share / FULL_FEMALE_WORK_SHARE
FULL_FEMALE_WORK_SHARE = 0.48     # Protected Class's share: women's rights at their fullest
CHAIN_STEP, CHAIN_CAP = 0.02, 0.2  # per consecutive year of net inflow, at most
CRISIS_AT_WAR = 0.3               # refugees' weight while the owner is at war, before devastation and turmoil

# ---- Income inequality (§4.1) -----------------------------------------------------
# Spending per head stands in for income: the buy package cost at the pop's wealth / 100, linear
# between GINI_INCOME_KNOTS. The owner confirmed it tracks the engine's income (Britain 1836:
# aristocrats 139x laborers a head in the engine, 115x in the stand-in). It runs uncapped to the
# top wealth level, the mod's NUM_WEALTH_LEVELS (common/defines/extra_defines.txt; the generator
# checks it): until 2026-10-10 it was flat from wealth 60, where the packages are 946 a head, and the
# last band held everyone above. In a 1953 save the 0.1% of the USA's people above 60 held 16% of
# its income, and the panel read 0.708 against 0.723 pop by pop; in a fast run with wealth up to 109,
# Germany read 0.65 against 0.77 (docs/testing/demographics-gini-check-2026-10-10.md, high wealth).
GINI_TOP_WEALTH = 200
# The Gini groups pops by wealth band, five levels wide all the way up: wealth 1 or less, 2-5, 6-10,
# ..., 191-195, 196 or more. The stand-in's pieces are the bands, so a band's income comes from one
# line and the bands are in income order: the grouped Gini needs no sort. The panel shows it as it
# is, the game's own distribution, not history's (owner, 2026-10-10): against each pop as its own
# group, mean -0.014, R^2 0.98 at 1836-1953. A five-wide band's richest level spends 1.3-1.7x its
# poorest at every height, so the bands miss about as much at mean wealth 80 as in 1836: -0.004 to
# -0.012 shown on average, at worst -0.036 for a country, in saves shifted or stretched to mean
# wealth 50-80 (docs/testing/demographics-gini-check-2026-10-10.md, high wealth).
GINI_BAND_KNOTS = (1, *range(5, GINI_TOP_WEALTH, 5))
GINI_BANDS = len(GINI_BAND_KNOTS) + 1
GINI_INCOME_KNOTS = (*GINI_BAND_KNOTS, GINI_TOP_WEALTH)
# The census sums income in units of GINI_INCOME_UNIT: each pop adds people / GINI_INCOME_UNIT x
# spending per head. Script values are i64 x 1e-5 (at most about 9.2e13): wealth 200 is 9.5e8 a head,
# so a country of 1e9 people there would be 9.5e17 in plain units, and 9.5e12 in these. The people
# divide first, which is exact; the smallest step is then 1 of spending per pop (1e-5 of the unit).
GINI_INCOME_UNIT = 100000
GINI_MAX_PEOPLE = 4e9     # one country, all at the top level, fits twice over (fast run: UNA 1.16e9, world 6.9e9)
# The layout a state's stored bands follow (te_dg_gini_layout). The country adds only states that
# carry this one, so a save's older bands are never summed with these. Bump it whenever the bands,
# the stand-in or the units change: 1 was the 14 bands to 61+, before the marker.
GINI_LAYOUT = 2
# The panel shows 1 - GINI_SHOWN_EQUALITY x (1 - the computed Gini) (owner, 2026-10-10): the census
# counts everyone in a pop (or band) as earning alike, so it sees only part of the spread historians'
# estimates hold; the equality it sees is scaled down, and total inequality stays at 1. Fitted to the
# income Ginis of van Zanden et al. (2014, Clio Infra), 1820 and 1850 interpolated to 1836, over 23
# countries against the 1836 save's band Gini: 0.685 weighting each equally, 0.711 by people.
GINI_SHOWN_EQUALITY = 0.7

# ---- Display ----------------------------------------------------------------------
BAND_WIDTH = 5
BANDS = 18          # 0-4 ... 80-84, then 85+
