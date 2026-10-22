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
# Children per woman from wealth alone at SoL 8 or below. 6.0 since 2026-10-10 (owner, phase 2 step 4's gate; was 6.2):
# the model's children per woman sat above Gapminder's almost everywhere (1837: China 6.09 against 5.5, Japan 5.75
# against 4.5, Britain 5.50 against 4.8, France 4.45 against 3.6), and the world multiple 1837-1900 at x1.78.
# At 6.0: x1.66, China +0.12% a year in 1887, every medicine and fertility anchor in band
# (docs/testing/demographics-phase2-engine-rates-2026-10-10.md, "The multiple").
# x s, the raise (the late-marriage plan's fit, 2026-10-12; spec 2.2): s = 1.00, no raise. No raise up to 1.20 passes
# the regional growth gate, and none fails fewer of its items (docs/testing/demographics-late-marriage-2026-10-12.md).
WEALTH_TFR_LOW, WEALTH_TFR_LOW_SOL = 6.0, 8
WEALTH_TFR_HIGH, WEALTH_TFR_HIGH_SOL = 3.5, 35   # what wealth alone does at SoL 35+
EDUCATION_WEIGHT = 0.4        # desired x (1 - 0.4 x literacy)
SURVIVAL_WEIGHT = 0.4         # desired x (1 - 0.4 x (e0 - 30) / 50), clamped 0..1
URBAN_WEIGHT = 0.2            # desired x (1 - 0.2 x urban share)
# The means' ceiling: 1, the natural bound of a share (owner, 2026-10-20; was 0.95, with no reason written): at 1
# every couple reaches the family size it wants.
MEANS_CAP = 1.0
# Every other shift to the means comes through one modifier type, state_fertility_means_add
# (common/modifier_type_definitions/demographics_modifier_types.txt), so history, events and
# later measures can grant it to any country. Family Limitation (te_demog_family_limitation)
# carries this much; France starts with it (§2.6: its transition began around 1800).
FAMILY_LIMITATION_MEANS = 0.6

# ---- Wealth Concentration (§4.2): the laws' terms ----------------------------------
# Script-only types on the laws since 2026-10-17, so each law's tooltip says what it does
# (demographics_wealth_concentration_types.txt; the vanilla laws' lines in
# te_demog_wealth_law_injections.txt, Graduated Taxation's in te_tax_vanilla_law_gates.txt, the
# antitrust laws' in extra_laws.txt). Not census
# inputs, so not in DEMOG_TYPES: Wealth Concentration runs whatever the Demographics rule, and
# a release keeps them. Land tenure, x a state's agrarian share: Serfdom +15, Tenant Farmers +5,
# Commercialized Agriculture none, Peasant Proprietorship -10, Collectivized Agriculture -20,
# each variant (`parent = law_x`: Manorialism, Latifundias, Expanded Latifundias, Homesteading)
# at its parent's value. Taxes: Graduated Taxation -5. The economic laws: Laissez-Faire +10,
# Extraction Economy +5, Interventionism -5, Guilds and Chartered Monopolies and Freedom of
# Contract +5, Antitrust Enforcement and Regulated Utilities -5. Public goods (2026-10-21): Private Health
# Insurance, Private Schools, Terakoya and Traditional IP Protection +5, Strict IP Protection +10, Public Health
# Insurance and Public Schools -5. Slavery (2026-10-21): Colonial Slavery, Legacy Slavery and Debt Slavery +10, Slave
# Trade +5. Inheritance (2026-10-21, #822's has_law lookups until then; on the mod's laws and amendments in
# extra_laws.txt and extra_amendments.txt, from 50): Primogeniture & Entail +30, Freedom of Testation +10, Customary
# Inheritance none, Forced Heirship -25, State as Universal Heir and Possession by Use -50; Estate Duties -30, the
# Birthright Endowment -20, Perpetual Dynastic Trusts +30, Undivided Farm Succession +10.
WC_INHERITANCE_TYPE = "country_wealth_concentration_inheritance_add"
WC_LAND_TYPE = "state_wealth_concentration_land_add"
WC_TAX_TYPE = "country_wealth_concentration_tax_add"
WC_ECONOMY_TYPE = "country_wealth_concentration_economy_add"
WC_PUBLIC_TYPE = "country_wealth_concentration_public_goods_add"
WC_SLAVERY_TYPE = "country_wealth_concentration_slavery_add"
WC_LAW_TYPES = (WC_INHERITANCE_TYPE, WC_LAND_TYPE, WC_TAX_TYPE, WC_ECONOMY_TYPE, WC_PUBLIC_TYPE, WC_SLAVERY_TYPE)

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
# The plain per-cause multipliers: 1 + the cause's type, floored. Accidents and violence (2026-10-16): the police laws a
# level of the Ministry of Public Safety (their institution_modifier, so the law with the Ministry at 0 gives nothing:
# Local Police and Private Policing -0.02, Dedicated and Militarized -0.03), Restorative Justice -0.04,
# Rehabilitation-Focused -0.08, the Ministry of Consumer Protection -0.08 a level, the Combustion Engine +0.30 and the
# late-era lines (LATE_EXTERNAL_LINES). Work: Child Labor Allowed and Penal Labor Camps +0.10, Regulatory Bodies and
# Worker Protections -0.10 a Workplace Safety level. Mind Backups' restore of both is on BACKUP_TYPES (uploaded minds),
# which plain_multiplier adds x last step's longevity care.
MORTALITY_TYPES = {
    "external": ("state_external_mortality_mult",),
    "work": ("state_work_mortality_mult",),
    "chronic": ("state_chronic_mortality_mult",),
    "maternal": ("state_maternal_mortality_mult",),   # phase 2 step 3b: Restricted Contraception (MEASURE_TYPES)
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
# Natural fertility (phase 2 step 4, Task 7): women's legal status before modern contraception, through who
# marries and when. Multiplies the wealth term before the means. Its carriers are the women's-rights laws,
# re-centred on No Women's Rights so step 2's fit (83% of the 1837 world) is unchanged (owner call (d), 2026-10-10).
NATURAL_FERTILITY_TYPE = "state_natural_fertility_mult"
NATURAL_FERTILITY_FLOOR = 0.2
NATURAL_FERTILITY_BY_LAW = {
    "law_no_womens_rights": 0.0, "law_women_in_the_fields": -0.15, "law_women_own_property": -0.05,
    "law_women_in_the_workplace": -0.10, "law_womens_suffrage": -0.10, "law_protected_class": -0.15,
}
DEMOG_FERTILITY_TYPES = (CONTRACEPTION_TYPE, MEANS_SHIFT_TYPE, NATURAL_FERTILITY_TYPE)
# The spread of medicine (the Causes of Death plan): the share of the gap health-care access and treatments close at a
# census step, beyond DIFFUSION_BASE (below, with the rest of the drift's numbers).
DIFFUSION_TYPE = "state_medical_diffusion_add"
# The World Health Organization's convention carries a line of the same type (un_pandemic_cooperation_modifier, a static
# modifier, so load_carriers doesn't walk it), scaled by the UN's enforcement like the rest of that modifier. The late
# game's market threshold adds it for a party (gen_demographics_lx.py); test_demographics_modifiers pins it to the file.
WHO_DIFFUSION = 0.05
# DEMOG_TYPES, every census input type, is defined after phase 2 step 1's participation inputs (below).
# The means to plan a family (§2.3): (TRADITIONAL_MEANS + state_contraception_add, at most 1) x
# (MEANS_ACCESS_BASE + (1 - MEANS_ACCESS_BASE) x literacy) + state_fertility_means_add, within
# 0..MEANS_CAP. Traditional methods everyone has; the techs' lines add to them (the Pill without
# vulcanization is 0.4 + the Pill's line). Values on the carriers: demographics_modifiers.py.
TRADITIONAL_MEANS = 0.4
MEANS_ACCESS_BASE = 0.3

# ---- Phase 2 step 1: the interfaces -----------------------------------------------------------------------------
# docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §1. The census computes these figures
# at every seed and step and applies none of them until step 2, whose harness fits the numbers (owner, 2026-10-12).
# Participation (late-game §2.1; #894): people x start(calendar age) x [below the end of the working ages ? 1 : the
# after-pension share] x capacity(biological age) x the sex's rate.
CHILD_WORK_AGE = 10            # calendar: the 10-14s work at the childrens'-rights laws' share (parent §7)
WORKING_AGE = 15               # calendar: everyone from here
# The 10-14s' share at work, within 0-1: a census-only type on the childrens'-rights laws (since 2026-10-17, so a law's
# tooltip says it; te_demog_law_injections.txt): Child Labor Allowed 0.3, Restricted Child Labor 0.1, Compulsory Primary
# School none. In DEMOG_TYPES (below).
CHILD_WORK_TYPE = "state_child_labor_participation_add"
CAPACITY = {0: 1.0, 60: 1.0, 65: 0.95, 70: 0.85, 75: 0.7, 80: 0.5, 85: 0.2}   # by biological band start
AFTER_PENSION_SHARE = 0.3      # the share of the eligible who keep working, x capacity
# The sexes' rates are in the game's units (owner, 2026-10-20): the historical rates (men 0.92, women 0.05 to the men's,
# the lower strata's women 0.2, a shortage of men +0.1) x 0.7, which step 2's fit set as the game's count of them (1836
# 0.25 of the people at work, rich today 0.42), so the panel's rates and the workforce the pops are set to agree. The
# carriers' participation lines are in the same units. RATE_MAX is the most a sex's rate reaches: 1 x 0.7.
MEN_RATE = 0.644
WOMEN_BASE = 0.035             # the middle and upper strata's women under No Women's Rights
WOMEN_LOWER = 0.14             # the lower strata's women under any law (Goldin's U-shape)
WOMENS_WORK_FULL = 0.35        # the women's-work family's sum at which women work at the men's rate
RATE_MAX = 0.7                 # a sex's rate in the working ages with call 3's inputs, at most (te_demog_k_rate_max)
# Health need by biological band start (late-game §5.2), and 1836's people-weighted need (the figure's 1.0).
HEALTH_NEED = {0: 1.0, 5: 0.5, 15: 0.8, 45: 1.4, 65: 2.4, 75: 3.4, 85: 4.5}
HEALTH_NEED_1836 = 0.952      # step 2's fit: the 1836 save's world need, people-weighted (harness `workforce`)
BIO_BANDS = tuple(sorted(set(CAPACITY) | set(HEALTH_NEED)))
# The pension positions' ages (late-game §2.2). Step 1 sets a country's pension age to the Standard one under Old Age
# Pension; step 2 adds the setting.
PENSION_AGE = {"early": 60, "standard": 65, "raised": 70}
PENSION_LAW = "law_old_age_pension"
NO_PENSION_AGE_LAWS = ("law_universal_basic_income", "law_post-scarcity")  # the threshold ends the working ages
NO_WORKING_AGE_END = 999       # no pension law: the working ages run to capacity's end, which never comes (D10)
OLD_AGE_REMAINING = 15         # the old-age threshold: years of life left (Sanderson and Scherbov)
OLD_AGE_FROM = 40              # its search's first group start
# Planned and unplanned births (late-game §3.1): one schedule each, the same object until phase 3. While they are,
# the generator writes the sweep's birth line as today's single term.
ASFR_PLANNED_SHAPE = ASFR_SHAPE_BY_GROUP
ASFR_UNPLANNED_SHAPE = ASFR_SHAPE_BY_GROUP
# The pops' own working-adult ratios (vanilla pop_types; the rest take the define WORKING_ADULT_RATIO_BASE).
POP_BASE_RATIO = {"aristocrats": 0.2, "slaves": 0.5}
POP_BASE_RATIO_DEFAULT = 0.25
# The working-adult lines' two script-only families (Task 6; demographics_workforce_line_types.txt).
WOMENS_WORK_TYPE = "state_demog_womens_work_ratio_add"
REPLACED_TYPE = "state_demog_replaced_ratio_add"   # lines a census term replaces under Full (the design §1.7)
# Call 3's participation inputs (owner, 2026-10-12; the design §1.7): census-only types
# (demographics_modifier_types.txt), carried by laws beside the replaced family's lines (Task 6).
MALE_PARTICIPATION_TYPE = "state_male_labor_participation_add"   # the men's rate in the working ages
PARTICIPATION_TYPE = "state_labor_participation_add"             # both sexes' rates in the working ages
CAPACITY_TYPE = "state_work_capacity_mult"                       # capacity x (1 + it), at every age
PARTICIPATION_TYPES = (MALE_PARTICIPATION_TYPE, PARTICIPATION_TYPE, CAPACITY_TYPE)
# Every census input type: the mortality and fertility inputs, the spread of medicine and call 3's participation inputs
# (demographics_modifier_types.txt, which a release comments out with their carriers' lines).
# Calibration step 3's malaria control (the malaria factor's off switch, with the factor below): 0 to 1, on
# malaria_prevention at 1 (te_demog_tech_injections.txt).
MALARIA_CONTROL_TYPE = "state_malaria_control_add"
DEMOG_TYPES = (DEMOG_MORTALITY_TYPES + DEMOG_FERTILITY_TYPES + (DIFFUSION_TYPE,) + PARTICIPATION_TYPES
               + (MALARIA_CONTROL_TYPE, CHILD_WORK_TYPE))

# ---- Phase 2 step 2: the workforce, pensions and health costs ------------------------------------------------------
# docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §2 and §5. Everything here acts under
# Full only (te_demog_work_effects.txt). The harness fits the numbers (demographics_harness.py workforce, pensions).
# The workforce term W = te_demog_wf_target - the define's base (call 4), on a fixed-sign state pair. It lands on that
# target at each census step, and the engine's own pull toward a pop's ratio phases the change in (owner, 2026-10-20:
# until then W moved at most 0.01 a step, so a pension position took two to three census years and Women in the
# Fields' first landing about fifteen; it bound in 29% of the 2057 save's steps, 418M people, and the saves showed the
# engine's pull already lagging, so the change was slowed twice over). When W first lands it replaces the moved lines'
# pair, so a state's set ratio moves from the pair to the target at that step. The self-check workforce_follows_target
# reads how fast the engine follows.
WORKING_ADULT_BASE = 0.25      # the define WORKING_ADULT_RATIO_BASE (vanilla 00_defines.txt); the term nets only it
WF_POP_RATIO_MIN = 0.05        # the guard: no pop's own ratio below this (W is raised instead; no cap above)
POP_BASE_RATIO_MIN = min(min(POP_BASE_RATIO.values()), POP_BASE_RATIO_DEFAULT)   # aristocrats' 0.2
# The pension setting (late-game §2.2): five positions, the country variable te_dg_pension_pos (absent = Standard).
# The linked positions follow the country's people-weighted old-age threshold less PENSION_LINK_OFFSET, at least
# PENSION_LINK_FLOOR, moving at most PENSION_LINK_STEP a year. Every position holds for PENSION_TERM_YEARS.
PENSION_POSITIONS = ("early", "standard", "raised", "linked_average", "linked_common")
PENSION_POSITION_ID = {p: i + 1 for i, p in enumerate(PENSION_POSITIONS)}   # te_dg_pension_pos
PENSION_LINKED = ("linked_average", "linked_common")
PENSION_LINK_OFFSET = 5
PENSION_LINK_FLOOR = 65
PENSION_LINK_STEP = 1
PENSION_TERM_YEARS = 5
# Approval while in force (a country static modifier per position; late-game §2.2's table). Standard has none.
PENSION_IG_APPROVAL = {
    "early": {"ig_trade_unions": 2, "ig_industrialists": -1},
    "raised": {"ig_trade_unions": -2, "ig_rural_folk": -1, "ig_industrialists": 1},
    "linked_average": {"ig_trade_unions": -1, "ig_rural_folk": -1, "ig_industrialists": 1},
    "linked_common": {"ig_trade_unions": 1, "ig_rural_folk": 1, "ig_industrialists": -1},
}
# The pension bill (§2.3, money): a weekly expense of GDP / 52 x the pensioners' share x B, B = PENSION_B_PER_LEVEL x
# the Social Security level. Fitted against revenue (late-game call 16): the bill 15-30% of a rich country's revenue at
# Standard with 18-22% pensioners.
# Call 16's fit (2026-10-12, harness `pensions SAVE`, the 15 largest economies' median revenue over GDP): 1949 0.32,
# 1953 0.27, 1959 0.38 (the bill 16-23% of revenue at 20% pensioners), and the only plain-text late-game save, 2062
# 0.10 over all 15 but 0.26 over the eight whose revenue is at least 10% of GDP (the other seven run expenses 5-34x their
# income: the AI's chronic insolvency), which puts B at 0.059. 0.06 stands.
PENSION_B_PER_LEVEL = 0.06      # step 2's fit (0.08 proposed), held by call 16's fit above
PENSION_BILL_BAND = (0.15, 0.30)
# The health bill (§2.4, bureaucracy): country_institution_cost_institution_health_system_mult = the need term
# HEALTH_NEED_WEIGHT x (need - 1), at most HEALTH_NEED_CAP, plus HEALTH_TECH_STEP for each chronic-treatment technology.
# Below 1836's need the term is negative (a young country's system costs a little less), on a fixed-sign pair.
# HEALTH_TECHS are all six of chronic treatment's carriers (TREATMENT_CAP's comment), so full technology costs +0.30
# (owner, 2026-10-20; the first three alone until then): molecular nanotech treats with expensive advanced materials, and
# the bill is a good sink for an ultra-wealthy late-game country.
HEALTH_NEED_WEIGHT = 0.8      # step 2's fit (0.5 proposed): rich today +0.35 to +0.5 with its technologies
HEALTH_NEED_CAP = 1.0
HEALTH_TECHS = ("modern_pharmaceuticals", "telemedicine", "personalized_medicine", "genetic_engineering",
                "molecular_assemblers", "biological_immortality")
HEALTH_TECH_STEP = 0.05
# Work deaths follow the participation model under Full (§2.5): women's share of the census's own workers aged
# WORK_SPLIT_AGES (first, last), from the last count; the laws' share (female_work_share) before one.
WORK_SPLIT_AGES = (15, 64)
# The AI's yearly pulse (§2.2, §9): the same weights for every country; is_ai only decides whom the pulse acts for. A
# bill over PENSION_AI_BILL_HIGH of revenue, or debt over PENSION_AI_DEBT of its ceiling, pushes toward the cheaper
# positions (Linked to Average where its age passes Raised's, else Raised); unemployment over PENSION_AI_UNEMPLOYMENT
# (people-weighted over its states) toward Early. A wide longevity gap toward Linked to Common waits for phase 3. It goes
# back to Standard only once the reason has clearly gone (hysteresis, the review of 2026-10-12): from a cheaper position
# when the bill is under PENSION_AI_BILL_LOW of revenue and the debt and default have gone, from Early when unemployment
# is under PENSION_AI_UNEMPLOYMENT_LOW.
PENSION_AI_BILL_HIGH = 0.3
PENSION_AI_BILL_LOW = 0.2
PENSION_AI_DEBT = 0.25
PENSION_AI_UNEMPLOYMENT = 0.1
PENSION_AI_UNEMPLOYMENT_LOW = 0.05

# ---- Phase 2 step 4: conscription, the youth bulge and sex balance ----------------------------------------------
# docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §4 and §5. The figures are the census's
# (Full and Display only); the four state modifiers act under Full only. `demographics_harness.py consequences` checks
# every band against the model's structures and the saves given.
# The pool (late-game call 21): men of calendar age POOL_FROM or more and biological age POOL_TO or less, summed in the
# sweep through step 1's two indexes; before phase 3, men aged 20-39. The war dead come from the same ages (§4.2), their
# women's share from the women of those ages.
POOL_FROM = 20                 # calendar: legal adulthood
POOL_TO = 39                   # biological: fitness
# Conscription T = max(the pool / people / CONSCRIPTION_REF - 1, CONSCRIPTION_MIN) on state_conscription_rate_mult
# (§4.1). The reference is the 1836 save's world, people-weighted: 0.1389 in the census's own seeded bands (the
# overnight Full run's 1836.2.1 save) and 0.1390 in the model's 1836 agrarian stable structure (starting value 0.14). No
# floor but -1 (call 21); parent §7's -0.25 floor is gone. No ceiling either (owner, 2026-10-16): the spec's +0.25 is
# gone, so a state rich in young men raises as many more conscripts as its pool's share is above the reference.
CONSCRIPTION_REF = 0.139
CONSCRIPTION_MIN = -1.0
# On since the migrant booking (2026-10-12; docs/testing/demographics-migrant-booking-2026-10-12.md), with the youth bulge
# and the sex balance. Step 4 held all three back (controller's decision, 2026-10-12, after its review): T reads the men
# the census's booking of the residual distorted (in the overnight Full run's 1848 save 32 states sat at T -0.5 or below
# and 15% at the +0.25 ceiling; 29.5-34.6% of people lived in states past +-0.05 in 1848-1904). Booked by the cap and
# the self-correcting labour split, the run's re-walk keeps T within -0.13 to +0.25 with 0.4-1.6% of people past 0.15
# and the great powers within +-0.07 by decade (`demographics_harness.py rebook`). The generator writes the switch as
# te_demog_k_conscription_effects (1 on, 0 held back).
CONSCRIPTION_EFFECTS = True
# When it applies, no pair below this |T| (the review's Minor 2: a term that small isn't worth a modifier line).
CONSCRIPTION_CUT = 0.01
# The youth bulge (§4.3): y = clamp((the share aged 20-29 - YOUTH_FROM) / YOUTH_SPAN, 0, 1) x clamp(unemployment /
# YOUTH_UNEMPLOYMENT_FULL, 0, 1), on one state modifier at multiplier y. The census's 1836 share is 0.159 in every
# state (the spec's sketch said about 0.17); a sharp transition's peak in the model is 0.20-0.23. Kept at the spec's
# starting values: they meet the bands.
YOUTH_AGES = (20, 29)          # calendar (life stage)
YOUTH_FROM = 0.18
YOUTH_SPAN = 0.06
YOUTH_UNEMPLOYMENT_FULL = 0.2
YOUTH_RADICALS = 0.15          # state_radicals_from_political_movements_mult at y = 1
YOUTH_TURMOIL = 0.10           # state_turmoil_effects_mult at y = 1
# On with conscription (above): step 4 held it back because 73% of the 1898 save's bulge states sat outside 90-110 men
# per 100 women, the booking's young men; re-walked with the booking, no state's 20-29 share passes 0.183 to 1901.
# Written as te_demog_k_youth_effects.
YOUTH_BULGE_EFFECTS = True
YOUTH_CUT = 0.02               # when it applies, no modifier below this y
# Sex balance (§4.4, call 10), on te_dg_sex_balance (men per 100 women aged 20-59). The census's adults run 91.5-98 men
# per 100 women in every 1836 state (male deaths from work, accidents and violence), so an effect measured from 100
# would fall on every state in peace: the fewer-men effects start below SEX_FEWER_FROM instead, just under 1836's lowest
# state. Children per woman x the balance / SEX_FEWER_FROM, at most 1 and at least SEX_BIRTHS_FLOOR (fewer marriages):
# the spec's square-root rule from 100 gave -9% at the Soviet Union's 82 of 1959; from 90 a straight ratio keeps that
# anchor (-8.9%) where the square root would give -4.6%. The floor is parent §3's "capped". The women's rate gains up to
# SEX_WOMEN_RATE and feminist movement support up to SEX_FEMINIST, both full at SEX_FEWER_FULL. More men than women:
# radicals from movements up to SEX_RADICALS, from SEX_MORE_FROM to full at SEX_MORE_FULL (Bare Branches).
# On with the other two (above). Step 4 held it back because the census's booking of the residual hollowed out or piled
# up states' men: in the overnight Full run's 1848-1904 saves 37-41% of states sat at one effect or the other against the
# design's "under 2% in peace" (Hyderabad 50 men per 100 women in 1898, the Central Provinces 28). Re-walked with the
# booking, 0.0-0.6% do (1848, 1898, 1901). The generator writes it as te_demog_k_sex_effects (1 on, 0 held back), and
# children per woman's breakdown shows its "Few men to marry" line (te_demog_tfr_sex).
SEX_BALANCE_EFFECTS = True
SEX_FEWER_FROM = 90.0
SEX_FEWER_FULL = 80.0
SEX_BIRTHS_FLOOR = 0.8
SEX_WOMEN_RATE = 0.07           # in the game's units, as MEN_RATE (0.1 x 0.7)
SEX_FEMINIST = 0.10            # state_pop_support_movement_feminist_mult (a percentage; the _add form is not one)
SEX_MORE_FROM = 110.0
SEX_MORE_FULL = 150.0
SEX_RADICALS = 0.10            # state_radicals_from_political_movements_mult at full


# ---- Late Marriage and Birth Spacing ---------------------------------------------------------------------------
# docs/superpowers/specs/2026-10-10-demographics-late-marriage-design.md (approved by the owner 2026-10-11, all nine of
# its section 7 calls; Birth Spacing's cut at 0.35); plan docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md.
# Two customs, each a share of a state's people (0-1): children per woman x (1 - cut x share) for each, outside the
# means. Every value is a starting proposal the harness fits (plan Task 6), rounded to neat figures. The short names
# key the script (te_dg_pr_<P>, te_demog_pr_*_<P>); phase 3 adds Family Limitation to the same machinery.
PRACTICES = ("lm", "bs")
# The fit (plan Task 6, 2026-10-12; docs/testing/demographics-late-marriage-2026-10-12.md): with no raise, the cuts that
# fit children per woman best are 0.10 and 0.20 (the spec's 0.30 and 0.34 were fitted at a raise of 1.15 on the old
# 6.2 curve).
PRACTICE_CUT = {"lm": 0.10, "bs": 0.20}
# Birth Spacing's start for India: the share that cancels the wealth curve's raise, (1 - 1/s) / cut (spec 2.2, "held,
# not history"). With no raise there is nothing to cancel, so 0 (the fit, 2026-10-12). India's excess is early
# mortality, calibration step 3's (owner, 2026-10-11).
BS_HELD_START = 0.0
# Birth Spacing's start for China, Manchuria and Korea (owner, 2026-10-11; plan D13): at least the share that cancels the
# raise, and above it as far as China's peacetime births less deaths needs to land in history's +3 to +6, which lowers
# their births toward history's ~5.5 children per woman (spec 2.2's second variant). The fit with today's mortality
# (2026-10-12, the owner's option 2 at Stop A): 0.06, the smallest share on the 0.01 grid that brings China's projected
# peacetime births less deaths inside +3 to +6 (+5.9; +6.5 with none). Membership, not the value, says which states
# take it (demographics_model.bs_held_group).
BS_EAST_ASIA_START = 0.06
BS_EAST_ASIA_REGIONS = ("region_north_china", "region_south_china")
BS_INDIA_REGIONS = ("region_north_india", "region_south_india")
_OCCITANIA = ("STATE_PROVENCE", "STATE_GUYENNE", "STATE_LANGUEDOC", "STATE_AQUITAINE", "STATE_RHONE", "STATE_SAVOY",
              "STATE_AUVERGNE_LIMOUSIN")
_NW_IBERIA = ("STATE_GALICIA", "STATE_ASTURIAS", "STATE_BASQUE_COUNTRY", "STATE_LEON", "STATE_OLD_CASTILE",
              "STATE_ENTRE_DOURO_E_MINHO", "STATE_BEIRA", "STATE_ESTREMADURA", "STATE_AZORES", "STATE_MADEIRA")
_IBERIA = ("STATE_CATALONIA", "STATE_BALEARIC_ISLANDS", "STATE_ARAGON", "STATE_LOWER_ANDALUSIA", "STATE_ALENTEJO",
           "STATE_EXTREMADURA", "STATE_NEW_CASTILE", "STATE_UPPER_ANDALUSIA", "STATE_VALENCIA", "STATE_MURCIA",
           "STATE_CANARY_ISLANDS")
_ITALY = ("STATE_PIEDMONT", "STATE_EMILIA", "STATE_TUSCANY", "STATE_LAZIO", "STATE_CAMPANIA", "STATE_CALABRIA",
          "STATE_SICILY", "STATE_SARDINIA", "STATE_MALTA", "STATE_CORSICA", "STATE_UMBRIA", "STATE_APULIA",
          "STATE_ABRUZZO", "STATE_ROMAGNA", "STATE_VENETIA", "STATE_ISTRIA", "STATE_LOMBARDY", "STATE_SOUTH_TYROL")
_WEST_OF_THE_LINE = ("STATE_COURLAND", "STATE_TARTU", "STATE_RIGA", "STATE_TALINN", "STATE_EAST_PRUSSIA",
                     "STATE_WEST_PRUSSIA", "STATE_POSEN", "STATE_GREATER_POLAND", "STATE_SLOVENIA")
_THE_GRADIENT = ("STATE_MAZOVIA", "STATE_LESSER_POLAND", "STATE_WEST_GALICIA", "STATE_KAUNAS", "STATE_VILNIUS",
                 "STATE_CROATIA", "STATE_TRANSDANUBIA", "STATE_SLOVAKIA")
_JAPAN = ("STATE_HOKKAIDO", "STATE_TOHOKU", "STATE_KANTO", "STATE_HOKUSHINETSU", "STATE_TOKAI", "STATE_KYOTO",
          "STATE_KANSAI", "STATE_CHUGOKU", "STATE_SHIKOKU", "STATE_KYUSHU")
BS_EAST_ASIA_STATES = ("STATE_SOUTHERN_MANCHURIA", "STATE_NORTHERN_MANCHURIA", "STATE_SHENGJING", "STATE_SEOUL",
                       "STATE_BUSAN", "STATE_SARIWON", "STATE_PYONGYANG", "STATE_YANGHO")   # Manchuria and Korea
# Start shares (spec 3.2, 3.3): by strategic region, then by state region, which wins. Geography, not culture. Malta and
# Corsica take Italy's (the vanilla file's Italy group); Cape Verde, an African archipelago, stays at 0 (plan D10).
PRACTICE_START_REGION = {
    "lm": {"region_western_europe": 1.0, "region_northern_europe": 1.0, "region_central_europe": 1.0},
    "bs": {**dict.fromkeys(BS_EAST_ASIA_REGIONS, BS_EAST_ASIA_START), **dict.fromkeys(BS_INDIA_REGIONS, BS_HELD_START)},
}
PRACTICE_START_STATE = {
    "lm": {**dict.fromkeys(("STATE_KOLA", "STATE_EAST_KARELIA"), 0.2), **dict.fromkeys(_OCCITANIA, 1.0),
           **dict.fromkeys(_NW_IBERIA, 0.9), **dict.fromkeys(_IBERIA, 0.6), **dict.fromkeys(_ITALY, 0.5),
           **dict.fromkeys(_WEST_OF_THE_LINE, 0.8), **dict.fromkeys(_THE_GRADIENT, 0.4)},
    "bs": {**dict.fromkeys(_JAPAN, 1.0), **dict.fromkeys(BS_EAST_ASIA_STATES, BS_EAST_ASIA_START)},
}
# The yearly drift (spec 4.2, 4.3): share += PRACTICE_RATE x (target - share), a generation's half-life. The neighbour
# spread is phase 3's (plan D6). target = start x (1 - erosion), plus Late Marriage's drivers, within 0-1.
PRACTICE_RATE = 0.025
# Erosion by contraception (calls 5, 6): the means beyond traditional methods, state_contraception_add x (0.3 + 0.7 x
# literacy), from 0 at 0.1 to full at 0.3.
PRACTICE_EROSION_CONTRACEPTION = 0.7
PRACTICE_EROSION_FROM = 0.1
PRACTICE_EROSION_SPAN = 0.2
# Erosion by health care (call 5, Birth Spacing only): state_health_care_access_add, full at 0.5, standing in for the
# state that registers births and licenses midwives (the Meiji rise).
PRACTICE_EROSION_ACCESS = {"lm": 0.0, "bs": 0.3}
PRACTICE_ACCESS_SPAN = 0.5
# Late Marriage's drivers (call 6): impartible inheritance x the agrarian share; women's paid work before marriage,
# x the women's job share x the law's women's work share / FULL_FEMALE_WORK_SHARE. Impartible inheritance is a
# census-only type (since 2026-10-17, so its tooltip says it), 0.15 on Primogeniture (extra_laws.txt) and on Undivided
# Farm Succession (extra_amendments.txt, an amendment: load_carriers' kind "amendment"). The two never meet: the
# amendment sits only on Forced Heirship and Customary Inheritance.
LM_FARMS_TYPE = "state_late_marriage_farms_add"
DEMOG_TYPES = DEMOG_TYPES + (LM_FARMS_TYPE,)
LM_WOMENS_WORK = 0.3
# The panel (spec 5.3): women's mean age at first marriage, about 19 + 7 x the Late Marriage share.
MARRIAGE_AGE_AT_ZERO, MARRIAGE_AGE_SPAN = 19, 7

# ---- Phase 3: the neighbour spread, Family Limitation as a general practice, Cultural Hegemony's drift ----------
# Parent spec docs/superpowers/specs/2026-10-08-demographics-design.md section 13 ("Family Limitation as a general
# practice, not France's") and section 6's Cultural Hegemony row; the late-marriage spec's 4.4 (the spread). Owner,
# 2026-10-12: build as section 13 proposes (a national practice), no country-specific mechanics. Results:
# docs/testing/demographics-family-limitation-2026-10-12.md.
#
# The neighbour spread of Late Marriage and Birth Spacing (late-marriage spec 4.2-4.4): each step also closes this share
# of the gap to its neighbouring states' people-weighted mean, both ways (te_demog_practices_neighbours). Kept slow
# because the Hajnal line was stable for centuries: an edge state moves about a fifth of the way in 50 years.
PRACTICE_SPREAD = 0.005
# Family Limitation: a national practice, the share of couples who stop at the family size they want by methods older
# than any modern one (withdrawal, abstinence). A country's share, 0-1 (te_dg_pr_fl), under the Demographics rule's Full
# setting only; outside Full France keeps history's te_demog_family_limitation at FAMILY_LIMITATION_MEANS, as before.
# Applied as that same modifier at multiplier line / FAMILY_LIMITATION_MEANS, so its one line in the means
# (state_fertility_means_add) reads line = share x (1 - what modern methods have replaced), which the census reads
# through te_demog_means as before. Below FL_LINE_MIN the country carries no line (no "+0.4%" rows on half the map).
FL_LINE_MIN = 0.02
# The start: a country holding history's modifier (France, as history sets its Forced Heirship) seeds at its value,
# FAMILY_LIMITATION_MEANS; every other country at 0.
# The yearly rise, each census year (fl_step): FL_RATE of the gap to the target its conditions give, and FL_SPREAD of the
# gap to its neighbours' share (neighbouring states' owners, weighted by those states' people: a border-weighted mean,
# so Catalonia's frontier with France counts and Portugal's size doesn't). Both act upward only: a practice once
# learned is not unlearned (in the European Fertility Project no province's marital fertility rose again once it had
# fallen 10%), and France's share would otherwise leak to its neighbours' zero. What replaces it is modern methods, below.
FL_RATE = 0.025
FL_SPREAD = 0.02
# The target from the country's conditions, people-weighted over its census states, within 0-1:
#   smallholders under partible inheritance: FL_HEIRSHIP x the agrarian share under Forced Heirship (law_equal_
#   inheritance), not with Undivided Farm Succession, which switches the rural cut off today too. It is Forced Heirship's
#   old rural birth cut (inh_forced_heirship_rural, -15% x the farm share), folded in under Full (section 13);
#   + literacy, read through the church law: FL_LITERACY x clamp((literacy - FL_LITERACY_FROM) / FL_LITERACY_SPAN, 0, 1)
#   x the church laws' weight, 1 + FL_LITERACY_TYPE (a secular, literate society limits births; the game's literacy
#   rises fast in the West, so the term starts late and stays small).
FL_HEIRSHIP = 1.0
FL_LITERACY = 0.3
FL_LITERACY_FROM = 0.8
FL_LITERACY_SPAN = 0.2
# The church laws' weight: a census-only country type (since 2026-10-17, so a law's tooltip says it;
# te_demog_law_injections.txt): State Religion, the Millet System and People of the Book -0.5, Total Separation and
# State Atheism +0.5, Freedom of Conscience none. The weight is 1 + it, at least 0.
FL_LITERACY_TYPE = "country_family_limitation_literacy_mult"
DEMOG_TYPES = DEMOG_TYPES + (FL_LITERACY_TYPE,)
# Modern methods replace it: the line is share x (1 - the erosion Late Marriage and Birth Spacing take from contraception,
# te_demog_pr_erosion_contraception), at the country's people-weighted literacy. The couples who practised it now use
# the methods the means already count (the techs' state_contraception_add), so the West of 1950 isn't counted twice.
FL_ERODES = True
# Cultural Hegemony's drift (section 6, "the soap-opera effect": Brazil's fertility fell where TV novelas reached, La
# Ferrara, Chong and Duryea 2012): under Full, a factor on each state's desired fertility, the country's te_dg_ch_desired.
# Each census year it moves CH_RATE of the way to 1 + CH_WEIGHT x exposure x (the hegemon's desired / the country's own
# - 1), within 1 +- CH_CAP. Exposure is the hegemon's cultural lead over the country, as the foreign benchmark reads
# it (ch_benchmark_applied / cultural_hegemony_foreign_benchmark_max: (the hegemon's share - the country's) / 100 x 1 -
# its ideology resistance; 0 for the hegemon, and only while the Cultural Hegemony journal entry runs, the mass-media
# era). Small: at a 30-point lead and the hegemon wanting two-thirds as many children, desired falls by 5%.
CH_WEIGHT = 0.5
CH_RATE = 0.2
CH_CAP = 0.1
CH_BENCHMARK_MAX = 3.0   # cultural_hegemony_foreign_benchmark_max (cultural_hegemony_script_values.txt)

# ---- Cause multipliers from state inputs (§2.4) -----------------------------------
# Medicine for infection, maternal and chronic deaths is 1 - access x treatment (the
# modifier-types design, Decision 1). Access is how much of the population a state's medicine
# reaches: this base (markets and charity, everywhere, colonies and 1836 too) plus
# state_health_care_access_add, at most 1. Treatment is the cause's
# country_<cause>_treatment_add, at most its cap. The values of both live on their carriers in
# the game files (demographics_modifiers.py); calibrated with `demographics_harness.py medicine`.
BASE_ACCESS = 0.4
# chronic 0.99 (owner, 2026-10-20; was 0.85, phase 2 step 4's headroom): as infection's, the technologies alone reach
# it in the last era. modern_pharmaceuticals 0.3 (era 8), telemedicine 0.2 (era 10) and personalized_medicine 0.2 (era 11)
# make 0.70; genetic_engineering 0.05 (era 11), molecular_assemblers 0.12 and biological_immortality 0.12 (era 12) take
# it to 0.99. The augmentation laws' flat lines (Medical Augmentation Only 0.10; Unrestricted, Regulated Market and
# Mandatory 0.05) bring it there sooner and past it only cap. The health bill's HEALTH_TECHS counts all six (2026-10-20).
# infection 0.99 (#1045; was 0.95): the base game's carriers reach 0.94 by era 7 (medical_degrees 0.03, pharmaceuticals
# 0.07, modern_nursing 0.08, antibiotics 0.4, modern_vaccines 0.25, antibiotic_mass_production 0.11), which matches the
# rich world of eras 9-10; the late carriers take the rest (personalized_medicine 0.03 in era 11, advanced_nanofabrication
# 0.02 in era 12), so infection's medicine halves by era 11 and falls to a sixth by era 12 (owner, 2026-10-18: match the
# rich world in eras 9-10, well below it after).
TREATMENT_CAP = {"infection": 0.99, "maternal": 0.99, "chronic": 0.99}
# Every other law, technology or institution term is 1 + its types' sum, at least this: 0, the natural bound, since a
# negative rate would add people (owner, 2026-10-20; was 0.2, which held accidents and violence at 0.2 in every late
# state whose lines sum to -0.9).
MORTALITY_MULT_FLOOR = 0.0
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
# Adults' infection (#1045): medicine reaches the infection deaths of the ages INFECTION_ADULT_AGES (from, to) a second
# time, at this weight, so there infection is x (1 - INFECTION_ADULT_MEDICINE x access x treatment) more than its
# multiplier. The 1836 schedule's adult deaths (750 a year per 100,000 at 15-44) are mostly tuberculosis, typhoid and
# pneumonia, which antibiotics and vaccines all but ended, so the one multiplier that fits the infants' anchor left the
# rich state's 15-44s at 19 per 100,000 against the rich world's 3-6 (and as the top killer of immortals, whose bodies
# sit at those ages). Infants keep the plain multiplier (their rate also carries the perinatal deaths, and the infant
# anchors are fitted to it), and so do the old (pneumonia still kills the rich world's old). Fitted on
# demographics_late.py's rich state today: 15-44s' infection deaths 4.7 per 100,000 a year, 35q15 from infection 0.0017
# (the rich world's 0.001-0.002). The bounds sit on the age groups' and the bands' five-year edges.
INFECTION_ADULT_AGES = (15, 65)
INFECTION_ADULT_MEDICINE = 0.8
# Crowding (owner, 2026-10-10: a function of how crowded the state is, not a switch): infection rises by the
# state's migration penalty from crowding. migration_crowding takes state_migration_pull_mult -0.1 a unit of its
# multiplier (extra_modifiers.txt), which is 4.5 r^2 below ten times the floor density and linear above
# (migration_crowding_mult, r the state's place between the floor and ten times it). So a state just past the
# floor adds almost nothing, the 1837 median crowded person +4%, a state at ten times the floor +45%. The Ministry
# of Urban Planning and Urban Engineering (sewerage, steel frames) lower it through the crowding itself.
MIGRATION_CROWDING_PULL_PER_MULT = 0.1   # the modifier's pull penalty a unit of multiplier (a test pins it)
CROWDING_INFECTION_PER_PULL = 1.0        # infection rises by the share migration attraction falls, with no ceiling
# (owner, 2026-10-20: the old +50% cap was a guess; Ile-de-France's pull 1.008 doubles its infection)

# ---- Causes of Death (owner, 2026-10-11; docs/superpowers/archive/plans/2026-10-11-demographics-causes-of-death.md) ----
# Each cause's multiplier is the product of these factors, in this order. The generator writes one script value per
# factor (te_demog_f_<cause>_<factor>) and each te_demog_mult_<cause> as their product; the state subtab's Causes of
# Death section reads the same values, so the display and the census can't disagree.
CAUSE_FACTORS = {
    "infection": ("medicine", "sol", "poverty", "literacy", "crowding", "malaria"),
    "work": ("laws", "safety"),
    "external": ("laws", "safety", "turmoil"),
    "maternal": ("medicine", "laws"),   # laws: phase 2 step 3b's state_maternal_mortality_mult
    "chronic": ("medicine", "laws", "sol"),
}
# Short names of the state variables (te_dg_m_<short>, te_dg_trt_<short>, te_dg_in_<short>).
CAUSE_SHORT = {"infection": "inf", "work": "work", "external": "ext", "maternal": "mat", "chronic": "chr"}
# Modern safety (owner, 2026-10-16; the late-game build's adult-mortality check, #947): era 7-9 technologies make work
# and everyday life safer whatever the laws do, so each prevents a share of the cause's deaths, 1 - the type's sum, at
# most SAFETY_MAX. The laws factor's floor (MORTALITY_MULT_FLOOR) doesn't reach it: robots and container ports cut the
# deaths of every job that remains, under any law. The step stores each sum, clamped, as te_dg_in_saf_<short>; a step
# from before stored none, so the factor reads 1 until the state's next step. Carriers (their own era_N.txt definitions):
# work, Prefabricated Construction 0.15, Industrial Robotics 0.35, Containerization 0.15, Knowledge Economy 0.25 (0.90 by
# era 9: x0.05 with Workplace Safety at level 5, near today's rich-world 2-4 deaths a year per 100,000 workers);
# accidents and violence, Modern Urban Planning 0.20, Computer-Aided Design 0.10, Cellular Networks 0.10 (0.40), and
# Autonomous Vehicles 0.10 in era 11 (0.50; 2026-10-16: the late-game design's §1.4 proposal, traffic deaths, built here
# rather than as a laws line, since self-driving cars save lives whatever the laws).
SAFETY_TYPES = {"work": "state_work_safety_add", "external": "state_external_safety_add"}
SAFETY_MAX = 0.95
DEMOG_TYPES = DEMOG_TYPES + tuple(SAFETY_TYPES.values())

# ---- Calibration step 3: the regional mortality gap (owner, 2026-10-12; #894) ----------------------------------------
# docs/superpowers/archive/specs/2026-10-12-demographics-calibration-step3-design.md. Owner calls 1-3 approved 2026-10-12.
# The malaria factor (§2.2, call 2): infection x (1 + the excess) in a state with one of vanilla's malaria traits, the
# only geographic input that reaches a region needing more deaths (Africa) and nothing that needs fewer. The factor is
# 1 + the trait's excess x (1 - the state's MALARIA_CONTROL_TYPE, 0 to 1). The trait's level (0 none,
# 1 state_trait_malaria, 2 state_trait_severe_malaria) and the control are the step's inputs te_dg_in_mal and
# te_dg_in_malc. Malaria Prevention (era 4) carries the control at 1, so it ends the factor. Quinine leaves it alone:
# vanilla's traits are colonists' mortality, and quinine protected colonists, not the people who lived there. The
# census's infection treatment reaches it through the medicine factor, which multiplies the whole infection rate, this
# factor included. The severe trait's excess is the mild one's x vanilla's own ratio for colonists (0.25 against 0.15),
# to 0.01. Fitted with `demographics_harness.py ontop-fit` against Africa's band on the overnight observer run of
# 2026-10-12 (the spec's §3).
MALARIA_TRAITS = {"state_trait_malaria": 1, "state_trait_severe_malaria": 2}
MALARIA_SEVERE_RATIO = 0.25 / 0.15
MALARIA_INFECTION = {1: 0.08, 2: 0.13}
# The fallback for spec §6's P3 (the malaria_trait_read self-check): True reads the trait from the state regions the
# map files give it (map_data/state_regions) instead of has_state_trait, should the check find the trait unreadable
# once a disabling technology has switched its modifier off.
MALARIA_READS_REGION_LIST = False
# The Landowners' famine reserves (§2.1, call 1): under Full the census absorbs, per pop, the country-scope lines on these
# building groups' mortality keys, as it absorbs mild starvation: each pop working in the group adds its owner's read
# of building_group_<g>_mortality_mult x COUNTRY_ABSORBED_SCALE to the walk's absorbed sum, so M nets it. Today the only
# country carrier of the key is vanilla's ig_trait_famine_reserves (agriculture -0.10). The country's read carries the
# interest group's power: a powerful group's traits count double (POWERFUL_IG_TRAIT_BONUS), so in 1836 India it reads
# -0.20, the size the walk measured on farm pops (the spec's "doubled" line). Building-scope lines (working conditions,
# production methods, company lines, executives' traits) stay on top at the bare curve's weight. That the country's read
# carries the doubling, and reads a building-group key at all, is inferred from the saves until the self-check
# famine_reserves_absorbed (spec §6's P1) logs OK. Its two fallbacks: should the walk read a farm pop's line at k x the
# country's, set the scale to k; should the country's read be 0, set COUNTRY_ABSORBED_FROM_FARM, which absorbs the
# workplace's own read on subsistence farms only. No company owns one, so that read holds only the trait (no
# building-scope line), but it leaves the trait on top for commercial farms' workers (the other agriculture groups).
COUNTRY_ABSORBED_GROUPS = ("bg_agriculture",)
COUNTRY_ABSORBED_SCALE = 1.0
COUNTRY_ABSORBED_FROM_FARM = False
# Turmoil (owner, 2026-10-11): accidents and violence x (1 + this x the state's turmoil, a 0-1 share). Vanilla's
# state_turmoil modifiers carry no mortality; state_mortality_turmoil_mult's carriers (Violent Suppression, Militarized
# Police, events) stay engine lines on top, which the walk leaves out (scaling unknown, measured about 0).
TURMOIL_EXTERNAL_WEIGHT = 0.5
# Medicine spreads (owner, 2026-10-11): at each census step health-care access and each cause's treatment move this
# share of the gap to their targets: DIFFUSION_BASE everywhere, plus DIFFUSION_TYPE (communication and medical-training
# technologies, the Medical Outreach decree), at most DIFFUSION_MAX. Within MEDICINE_SNAP of its target a value takes
# the target. A seed, a new state and an old save's state start at their targets. DIFFUSION_TYPE is with the other
# types, above.
DIFFUSION_BASE = 0.1
DIFFUSION_MAX = 1.0
MEDICINE_SNAP = 0.005
MEDICAL_OUTREACH_DIFFUSION = 0.2   # decree_medical_outreach's line (a test pins the decree to it)
DEATHS_ON_TOP_HIGH = 1.25          # 1 + te_dg_dz at or above this reads red on the state subtab

# Women's share of the workforce (§2.4, §2.5): this base plus the women's-rights laws' FEMALE_WORK_SHARE_TYPE line (stage 3
# of the modifier-types design, 2026-10-19, below), for the migrant profile, Late Marriage's women's work and, outside
# Full, splitting work deaths.
FEMALE_WORK_SHARE_DEFAULT = 0.1

# ---- War dead and migrants (§2.5) -------------------------------------------------
# The war dead come from the conscription pool's ages (phase 2 step 4, below: POOL_FROM, POOL_TO), 95% of them men.
WAR_DEAD_MALE_SHARE = 0.95
RESIDUAL_NOISE_SHARE = 0.003   # a residual under 0.3% of the population is model error
# The engine's starvation scaling (vanilla 00_defines.txt, 1.14.5; the mod leaves these alone): a pop's
# starvation value is clamp((the first threshold - food security) x the factor, 0, 1), which the save stores per
# pop as food_security={ starvation= }. Below the first threshold a pop is in mild starvation and
# starvation_penalty applies x that value, at most (0.4 - 0.2) x 2.5 = 0.5; below the second,
# severe_starvation_penalty applies x the same value, 0.5 to 1 (the famine probe, 2026-10-11: not in full; the
# walk took it flat until then). The expected births and deaths that the migration residual is measured against
# read these (gen_demographics.py, engine_rate_terms).
FOOD_SECURITY_STARVATION_THRESHOLD = 0.4
FOOD_SECURITY_SEVERE_STARVATION_THRESHOLD = 0.2
STARVATION_EFFECTS_SCALING_FACTOR = 2.5
STARVATION_VALUE_MAX = 1.0  # the define's clamp
STARVATION_BUCKET = 0.05   # both penalties are read in food-security steps this wide, at each step's middle

# ---- phase 2 step 4: the census sets the engine's births and deaths --------------------------
# docs/superpowers/archive/plans/2026-10-10-demographics-phase2-engine-rates.md §2. The engine adds every term
# into one (1 + total) per pop, linear from -0.9 (growth probe) to far above +1.0 (the 12x fast run), floored
# at 0. Owner, 2026-10-10: the poverty term replaces the curve's starving slope below SoL 4, and deaths added
# on top fall by the model's age pattern (the step's deaths scale).
# The engine's own per-pop floor (owner, 2026-10-20: the census's terms go down to it; until then -0.8, a precaution
# that kept the read inside the probes' measured range and made the engine kill twice the census's target in the late
# game). A plain pop's births or deaths reach 0 at a total of -1: Q7 stopped births at -3, and the growth probe's -5
# gave no deaths at all. The state read with M in it stays at or above this, and when the lines left on top alone
# are past it, M is 0. The self-check rate_below_measured watches the stretch from -0.9 down.
RATE_TOTAL_FLOOR = -1.0
# M has no ceiling (until 2026-10-20 +3, "a guard against a nonsense target"). target / bare is at most the model's rate
# over the curves' lowest (80 births, 100 deaths a month per 100,000), so M stays finite; the script skips a state whose
# walk found less than one person at the lowest curve (te_demog_k_rate_bare_min, the walk's units: people x the curve).
RATE_BARE_MIN = 80.0
# The step's births and deaths scales (the engine's events over the model's target, less 1) have only the natural
# floor, -1 (no events), and no ceiling (until 2026-10-20 -0.9 and +4): each age's probability is already capped at 1.
# Under 1 + scale = ON_TOP_FACTOR_MIN the ring's events are too few to read the model's own rate back from, so the step
# keeps the last one (te_dg_cbr_model, te_dg_cdr_model; demographics_model.step returns None).
ON_TOP_SCALE_MIN = -1.0
ON_TOP_FACTOR_MIN = 0.01
# The window's events (owner, 2026-10-11; #894; the review of #907): the walk is a snapshot on the step's day, and the
# step books the whole window that ends that day. The window is booked at the engine's rate at its start (stored by the
# last step's refresh) at this weight and today's at the rest: 0.5 is the trapezoid, which halves the misplacement when
# a famine starts or ends inside the window and lags a one-off by half a window (demographics_model.window_events).
WINDOW_START_WEIGHT = 0.5
LITERACY_BIRTH_PENALTY = -0.1 # literacy_penalty's state_birth_rate_mult (the mod's REPLACE keeps vanilla's)
# Owner, 2026-10-11 (docs/superpowers/archive/plans/2026-10-11-demographics-engine-lines-script-only.md): the engine's birth and
# mortality lines on laws, technologies and institutions move to script-only types, one per field and family
# (demographics_engine_line_types.txt). The mod re-applies both families while the census doesn't set a state's births
# and deaths (te_demog_lines_refresh); under Full the census models the absorbed family and applies the on-top one.
ENGINE_LINE_FIELDS = ("state_birth_rate_mult", "state_mortality_mult", "state_farmers_mortality_mult",
                      "state_laborers_mortality_mult", "state_machinists_mortality_mult",
                      "state_peasants_mortality_mult", "state_mortality_wealth_mult")
ENGINE_LINE_SHORT = {"state_birth_rate_mult": "births", "state_mortality_mult": "deaths",
                     "state_farmers_mortality_mult": "farmers_deaths", "state_laborers_mortality_mult": "laborers_deaths",
                     "state_machinists_mortality_mult": "machinists_deaths",
                     "state_peasants_mortality_mult": "peasants_deaths",
                     "state_mortality_wealth_mult": "wealth_deaths"}
ENGINE_LINE_TYPES = {
    ("absorbed", "state_birth_rate_mult"): "state_demog_absorbed_birth_rate_mult",
    ("absorbed", "state_mortality_mult"): "state_demog_absorbed_mortality_mult",
    ("absorbed", "state_farmers_mortality_mult"): "state_demog_absorbed_farmers_mortality_mult",
    ("absorbed", "state_laborers_mortality_mult"): "state_demog_absorbed_laborers_mortality_mult",
    ("absorbed", "state_machinists_mortality_mult"): "state_demog_absorbed_machinists_mortality_mult",
    ("absorbed", "state_peasants_mortality_mult"): "state_demog_absorbed_peasants_mortality_mult",
    ("ontop", "state_birth_rate_mult"): "state_demog_ontop_birth_rate_mult",
    ("ontop", "state_mortality_mult"): "state_demog_ontop_mortality_mult",
    ("ontop", "state_mortality_wealth_mult"): "state_demog_ontop_mortality_wealth_mult",
}
# Private Health Insurance's wealth line under Full (owner, 2026-10-11, option b): at the census's rate, at least this a
# wealth level, so a wealth-99 pop dies at no less than half the census's rate.
WEALTH_LINE_FLOOR = -0.005
STARVATION_MILD = {"births": -0.7, "deaths": 0.6}     # starvation_penalty (vanilla code static modifier), x the value
STARVATION_SEVERE = {"births": -0.9, "deaths": 1.0}   # severe_starvation_penalty, x the starvation value (0.5-1)
STARVATION_MILD_CAP = 0.5     # (threshold - severe threshold) x scaling factor: vanilla's comment
# Pollution Impact's mortality line (vanilla code static modifier state_region_pollution_health's 0.5 plus the mod's
# INJECTed 0.05), at full pollution: predict takes it x the region's pollution / POLLUTION_MAX (vanilla define).
# An approximation (2026-10-11): the engine's impact isn't pollution / 255 exactly. Yorkshire at 49.4 showed +8%
# (this gives +11%), West Bengal at about 167-176 showed +32% (+36% to +38%). The census reads the real line.
POLLUTION_HEALTH_MORTALITY = 0.55
POLLUTION_MAX = 255
# Phase 2 step 4 (plan §3 (a), owner amendment 2026-10-10): carriers whose birth or mortality lines stay on top
# of the census's term: their lines sit on the on-top family's script-only types (state_demog_ontop_*), which under
# Full the census adds at its rate. Every other law, technology or institution line is on the absorbed family's
# (state_demog_absorbed_*), which under Full the engine doesn't apply (the engine-lines plan, 2026-10-11).
# Hand-kept, not derived: TestEngineRateLines.test_the_families_match_the_on_top_lists pins it to the carriers'
# types. The women's-rights laws left this list in Task 8: Task 7's natural-fertility term
# (NATURAL_FERTILITY_BY_LAW) carries their effect.
ENGINE_LINES_ON_TOP = frozenset({
    # Communal Child-Rearing's -20%, which a State Youth Center's method cancels (phase 2 §3.2, call 9). Pro-Natalist
    # Policy's and Population Control Measures' births lines are absorbed since phase 2 step 3b: their force under Full
    # comes from desired fertility and the measures
    "law_communal_child_rearing",
    # late-era lines with no census term; revisit with step 6. Of the LGBTQ+ Rights laws only Full Equality and
    # Protection keeps a birth line, a token -0.01 (#881, owner, 2026-10-10). Mental Health Awareness, Biological
    # Immortality and Mind Backups left this list in phase 3 (the late-game design §8.4, call 19): the census carries them
    # under Full (LATE_EXTERNAL_LINES, LATE_WORK_LINES, the ageing ladder), their flat lines on the absorbed family
    "law_full_equality_and_protection", "law_state_eugenics_program", "second_wave_feminism", "sexual_revolution",
})
# Fields whose lines stay on top wherever they sit: wealth mortality's per-pop scaling ("per Wealth") waits on probe P6,
# so M doesn't net it out yet. Private Health Insurance's -0.002 a level is its main source (owner, 2026-10-10: on top
# for now). Nobody holds the law in the owner's 1949 save; had the rich health-law countries held it at their own
# level, France would lose about a fifth of its deaths (results doc, phase 2 step 4). Absorbing it per pop under Full,
# as mild starvation, is proposed.
ENGINE_FIELDS_ON_TOP = frozenset({"state_mortality_wealth_mult"})
# Phase 2 step 1 (the design §1.7; late-game call 11; the owner's call 3, 2026-10-12): every working-adult line on two
# script-only families (demographics_workforce_line_types.txt), each at its old flat value, re-applied by their own pair
# while no workforce term is in force (te_demog_workforce_lines_apply: not Full, or no te_dg_mw, step 2's term). Their
# own files and parameters, so the births and deaths term never takes them off (D3).
WORKING_ADULT_FIELD = "state_working_adult_ratio_add"
WORKFORCE_LINE_FIELDS = (WORKING_ADULT_FIELD,)
WORKFORCE_LINE_SHORT = {WORKING_ADULT_FIELD: "working_adults"}
WORKFORCE_LINE_TYPES = {("womens_work", WORKING_ADULT_FIELD): WOMENS_WORK_TYPE,
                        ("replaced", WORKING_ADULT_FIELD): REPLACED_TYPE}
# The only engine working-adult lines left in common/ (file, top-level block): Rosen's androids (call 12), the pairs and
# the console's probe; the cancels in the injection files are checked against their families' lines by the MOVED tests.
LIVE_WORKFORCE_LINES = frozenset({
    ("extra_companies_flavored.txt", "company_rosen_association"),
    ("unique_pms.txt", "pm_rosen_association_hq"),
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
FAMILY_BASE = 0.2                 # families' weight before transport (FAMILY_MIGRATION_TYPE), rights and chain migration
FAMILY_RIGHTS_WEIGHT = 0.2        # x women's work share / FULL_FEMALE_WORK_SHARE
FULL_FEMALE_WORK_SHARE = 0.48     # Protected Class's share: women's rights at their fullest
CHAIN_STEP, CHAIN_CAP = 0.02, 0.2  # per consecutive year of net inflow, at most
CRISIS_AT_WAR = 0.3               # refugees' weight while the owner is at war, before devastation and turmoil
# ---- The residual's booking keeps the structure plausible (migrant booking, 2026-10-12) ---------------------------
# docs/testing/demographics-migrant-booking-2026-10-12.md. The residual is the engine's own migration (its per-state
# weekly statistics agree with it, in starving states too), and the engine moves whole pops, which have no age or sex:
# the profile above is the census's overlay. Booked the same way year after year, a state losing 2-7% of its people a
# year for decades lost nearly all its young men (Hill Punjab 2 men per 100 women by 1870) and frontiers piled them up
# (Durango 194). Two rules, fitted on a re-walk of the 2026-10-12 overnight run (demographics_harness.py rebook):
# - The cap: in one step the profile adds to a class and sex at most MIGRANT_CAP_IN of its people, and takes at most
#   MIGRANT_CAP_OUT; what is left over is booked at one flat rate over every class and sex (whole families moving).
#   Below the cap the booking is the profile's, as before.
MIGRANT_CAP_OUT = 0.03
MIGRANT_CAP_IN = 0.05
# - The labour kind's sex split corrects itself: departures' women's share moves to LABOUR_BALANCE_SHARE as the state's
#   men per 100 women aged 20-59 (te_dg_sex_balance, the census's last figure) fall from LABOUR_BALANCE_LOW's first
#   figure to its second, and arrivals' as they rise through LABOUR_BALANCE_HIGH. With the cap they keep migration
#   alone from carrying a state past the sex-balance effects' thresholds (SEX_FEWER_FROM 90, SEX_MORE_FROM 110).
LABOUR_BALANCE_SHARE = 0.5
LABOUR_BALANCE_LOW = (95.0, 91.0)
LABOUR_BALANCE_HIGH = (105.0, 115.0)

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

# ---- Phase 2 step 3b: the census reads the Family Policy measures and laws ------------------------------------
# docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §3.2, §3.5. Six script-only state types
# (demographics_modifier_types.txt), carried by the measures' country modifiers (te_demog_measure_modifiers.txt) and,
# for desired fertility, Pro-Natalist Policy. Not in DEMOG_TYPES: apart from that law's line they sit on static
# modifiers, which load_carriers doesn't walk (demographics_modifiers.measure_lines reads them).
DESIRED_TYPE = "state_desired_fertility_mult"               # desired x (1 + it), at least DESIRED_FLOOR
URBAN_RELIEF_TYPE = "state_urban_fertility_relief_add"      # the urban term 1 - 0.2 x urban x (1 - it), it within 0-1
MEANS_LITERACY_TYPE = "state_means_literacy_add"            # the means' access as if literacy were this much higher
MATERNAL_TYPE = MORTALITY_TYPES["maternal"][0]              # the maternal cause x (1 + it): a "laws" factor (above)
BIRTH_LIMIT_RELIEF_TYPE = "state_birth_limit_relief_add"    # Birth Limit's part x (1 - it x the agrarian share)
SRB_TYPE = "state_sex_ratio_at_birth_add"                   # boys per 100 girls SRB_BASE + it, with prenatal sexing
MEASURE_TYPES = (DESIRED_TYPE, URBAN_RELIEF_TYPE, MEANS_LITERACY_TYPE, MATERNAL_TYPE, BIRTH_LIMIT_RELIEF_TYPE,
                 SRB_TYPE)
# Desired fertility with the policy term is floored here (spec §3.5) and held at 1 at most: families can't plan more
# children than nature gives them (a decision, step 3b; without a measure desired is at most 1 anyway).
DESIRED_FLOOR = 0.1
DESIRED_CAP = 1.0
# The sex ratio at birth (§3.4): the constants above are 105 boys per 100 girls; with prenatal sexing (no technology of
# its own; the spec's proposal, Microprocessor, era 8) a positive SRB_TYPE moves the newborns' split in the step only.
SRB_BASE = 105
PRENATAL_SEXING_TECH = "microprocessor"
# Pro-Natalist Policy's own census line (§3.2): desired +5%, beside its births line moved to the absorbed family.
PRO_NATALIST_LAW = "law_pro_natalist_subsidies"

# ---- Phase 3: the late game ----------------------------------------------------------------------------------------
# docs/superpowers/archive/specs/2026-10-11-demographics-late-game-design.md (approved by the owner 2026-10-11, every call in its
# §9). Biological age, who gets life extension, Biological Immortality, fertility under the late eras and their display.
# Everything here is inert before the first ageing carrier (era 10): a state with no carrier and no treated people
# runs the census exactly as before (test_demographics_golden.py), and outside Full nothing reaches the engine.
#
# The ageing rate r of those in care (§1.2): biological years a calendar year, 1 + state_ageing_rate_add, within 0-1;
# Biological Immortality's pull (§1.4): each year a treated body above LX_PULL_TO closes this share of its gap to it,
# state_rejuvenation_add. Both are census-only state types (demographics_modifier_types.txt) on the technologies below
# (call 3: the ladder 0.9 at era 10, 0.75 at era 11, 0 at era 12; call 4: the pull 3% a year). 2026-10-16 (owner): 0.05 of
# Biological Immortality's line moved to Synthetic Biology, so era 11 reaches 0.70 and era 12 still 0.
AGEING_RATE_TYPE = "state_ageing_rate_add"
REJUVENATION_TYPE = "state_rejuvenation_add"
LATE_TYPES = (AGEING_RATE_TYPE, REJUVENATION_TYPE)
DEMOG_TYPES = DEMOG_TYPES + LATE_TYPES
AGEING_RATE_LINES = {"mrna_therapeutics": -0.10, "personalized_medicine": -0.10, "genetic_engineering": -0.05,
                     "synthetic_biology": -0.05, "biological_immortality": -0.70}
REJUVENATION_LINES = {"biological_immortality": 0.03}
# Who is treated (§1.2-§1.3, call 8): a treated share te_dg_s<j> and their mean deficit te_dg_d<j> (calendar less
# biological age) per five-year birth band j = slot // LX_BAND_WIDTH (birth year / 5 mod 30), adults only: a cohort
# reaching LX_JOIN_AGE joins at the state's eligibility E. The pool (150+) keeps its own (te_dg_lx_ps, te_dg_lx_pd).
LX_JOIN_AGE = 25
LX_BAND_WIDTH = 5
LX_BANDS = RING_YEARS // LX_BAND_WIDTH
LX_PULL_TO = 35
# Eligibility E drifts toward its target at the medical diffusion rate (DIFFUSION_BASE + state_medical_diffusion_add),
# both ways, and takes the target within this of it (as medicine does).
LX_SNAP = 0.005
# Access by wealth band (§4.2, call 12): the larger of a public route (the drifted health-care access x the health
# system's cover for longevity care, at least a floor) and a market route (a ramp from 0 at LX_MARKET_RAMP below the
# threshold W less the market's reach, to 1 as far above it). W is one country variable (te_dg_lx_w): LX_MARKET_START
# when the country's first carrier arrives, falling LX_MARKET_FALL a year x (1 + the laws' price fall) x (1 +
# LX_MARKET_DIFFUSION x the capital's state_medical_diffusion_add).
# The laws' parts are census-only types on the laws (demographics_modifier_types.txt; since 2026-10-17, so a law's tooltip
# says what it does, as the ageing ladder's techs do). The values sit on the laws (Decision 2 of the modifier-types
# design): the health laws' INJECTs in te_demog_law_injections.txt, the augmentation laws' lines in extra_laws.txt.
LX_COVER_TYPE = "state_longevity_care_cover_add"        # the public route's cover, 0-1: Public Health Insurance 1,
                                                        # Charitable 0.25, Mandatory Augmentation 1
LX_FLOOR_TYPE = "state_longevity_care_floor_add"        # the public route at least this, 0-1: Mandatory Augmentation 0.9
LX_REACH_TYPE = "state_longevity_care_market_reach_add"  # the market threshold this much lower: Unrestricted 20
LX_BAN_TYPE = "country_longevity_care_banned_bool"      # no longevity care at all: Human Purity (the Devout's law)
LX_PRICE_FALL_TYPE = "country_longevity_care_price_fall_mult"   # W's fall x (1 + it): Private Health Insurance 1 (its
                                                                # insurers pool the price), Regulated Market 0.5
LX_LAW_TYPES = (LX_COVER_TYPE, LX_FLOOR_TYPE, LX_REACH_TYPE, LX_BAN_TYPE, LX_PRICE_FALL_TYPE)
DEMOG_TYPES = DEMOG_TYPES + LX_LAW_TYPES
LX_MARKET_START = 80
LX_MARKET_FLOOR = -20                                # W stops falling here: everyone is within reach well before
LX_MARKET_FALL = 1.0
LX_MARKET_DIFFUSION = 1.0
LX_MARKET_RAMP = 10
# The wealth band's wealth for access (te_dg_gn<k>, GINI_BAND_KNOTS): the middle of its levels.
LX_BAND_WEALTH = {k: (1.0 if k == 1 else ((GINI_BAND_KNOTS[k - 2] + 1 + (GINI_BAND_KNOTS[k - 1]
                                                                       if k <= len(GINI_BAND_KNOTS) else GINI_TOP_WEALTH))
                                         / 2.0))
                  for k in range(1, GINI_BANDS + 1)}
# The health bill's third term (§5.2, call 13): + this x the share of people on the public route.
LX_PUBLIC_HEALTH_WEIGHT = 0.5
# Living to 100 (§6.1): survivors of the life table at this age; the longevity gap is the treated table's less the
# untreated's, in points.
LX_LIVING_TO = 100
# Old age from shows "none" at or past this (§1.5: under immortality no age has 15 years left; the census's life table
# stops at 150, so its threshold can't pass 135).
LX_OLD_AGE_NONE = 130
# The late-era lines (§8.4, call 19): under Full the census carries them; outside Full their flat lines stay (they sit on
# the absorbed family since phase 3). Mental Health Awareness: accidents and violence -10% (suicide). Mind Backups'
# accidents, violence and work -50% (the backed-up are restored) sits on BACKUP_TYPES since uploaded minds' call 2
# (2026-10-19), x the state's longevity care. autonomous_vehicles' -10% (traffic), §1.4's proposal, is built as modern
# safety instead (SAFETY_TYPES, 2026-10-16).
LATE_EXTERNAL_LINES = {"mental_health_awareness": -0.10}
LATE_WORK_LINES = {}
# Fertility (§3.1-§3.2, call 5): planned births follow the calendar for their timing and the body for whether it allows
# them; unplanned births the body. Fecundity by biological age (after Leridon 2004), by five-year group start.
FECUNDITY = {0: 1.0, 35: 0.9, 40: 0.7, 45: 0.35, 50: 0.0}
# The planned schedule's shift by the mean age at childbearing (§3.2): the machinery is built, its driver held at 0 (a
# decision, 2026-10-12): the spec's historical drivers (education, women's work, the means) act on today's states and
# would move the 1836-today calibration, which this phase keeps; today's shape already has a mean of 30.1 against
# Europe's ~31. Postponement in years = LX_POSTPONEMENT x the state's treated share (people who expect long lives
# start families later), 0 now.
LX_POSTPONEMENT = 0.0
# Ectogenesis (§3.5): e = State Youth Centers' levels on pm_ectogenesis x LX_ECTO_PER_LEVEL births a year / the state's
# births, at most LX_ECTO_MAX. That share of planned births carries no maternal death and no fecundity loss, and its
# parents count as the mean of the cohort's women and men.
LX_ECTO_PM = "pm_ectogenesis"
LX_ECTO_BUILDING = "building_state_youth_centers"
LX_ECTO_TECH = "biotechnology"     # the method's technology: the census counts the buildings only once the owner has it
LX_ECTO_PER_LEVEL = 1000
LX_ECTO_MAX = 0.9
# The gap's politics (§4.4, call 15): Trade Unions and Rural Folk approval down to LX_POLITICS_APPROVAL at full, the
# multiplier the national gap x the share of all the country's people not in care (te_demog_lx_gap_politics_x; the spec
# names the lower strata's untreated share, which the census doesn't keep: the built form is milder where the market
# reaches the rich first); Labor movement support up to LX_POLITICS_LABOR x the state's gap (state_pop_support_movement_
# labor_mult; the spec's _add). Generated as te_demog_k_lx_politics. Built off until a play-test sized it; on at the
# spec's sizes since 2026-10-16 (owner), which the play-test checks instead.
LONGEVITY_POLITICS = True
LX_POLITICS_APPROVAL = -3
LX_POLITICS_LABOR = 0.10
# The AI's pension pulse (late-game §2.2): a longevity gap (Living to 100, treated less untreated) over PENSION_AI_GAP picks
# Linked to Common Longevity, as the country's unions would; it goes back to Standard under PENSION_AI_GAP_LOW.
PENSION_AI_GAP = 0.2
PENSION_AI_GAP_LOW = 0.1

# ---- The migrant profile's inputs as modifier types (modifier-types design, stage 3, 2026-10-19) ----
# docs/superpowers/archive/specs/2026-10-09-demographics-modifier-types-design.md. Two census-only state types
# (demographics_modifier_types.txt) on their carriers in the game files, which demographics_modifiers.py resolves; they
# replaced the FEMALE_WORK_SHARE law table and the FAMILY_TRANSPORT_TECHS table. Women's share of the workforce is
# FEMALE_WORK_SHARE_DEFAULT + the women's-rights law's line, at most 1 (Women in the Fields 0.15, Women Own Property
# 0.20, Women in the Workplace 0.35, Women's Suffrage 0.37, Protected Class 0.38: the old table less the base), so
# FULL_FEMALE_WORK_SHARE is the base plus Protected Class's line. The family kind's weight takes the transport
# technologies' line on top of FAMILY_BASE: Paddle Steamer and Railways 0.10, Combustion Engine 0.15, and the aviation
# techs §2.5 names, Commercial Aviation and Jet Engine Technology 0.05 each (owner, 2026-10-19).
FEMALE_WORK_SHARE_TYPE = "state_female_work_share_add"
FAMILY_MIGRATION_TYPE = "state_family_migration_add"
MIGRANT_PROFILE_TYPES = (FEMALE_WORK_SHARE_TYPE, FAMILY_MIGRATION_TYPE)
DEMOG_TYPES = DEMOG_TYPES + MIGRANT_PROFILE_TYPES

# ---- Internal Resettlement's known moves (2026-10-19) ----
# Spec §2.5 "Known kills": the census books a Settlement Authority's moves with its programme's own age and sex profile,
# the same at the source (departures) and the destination (arrivals), and takes them out of the migration residual
# (demographics_resettle.py; common/scripted_effects/te_demog_resettle_effects.txt). The codes are var:rs_programme's
# (resettlement_set_programme_code; test_resettlement_programme_registry.PROGRAMMES): the index here.
RESETTLE_PROGRAMMES = ("land_grants", "military_colonies", "penal_transportation", "organized_colonization",
                       "special_settlements", "development_program", "rustication", "managed_retreat")
# The programmes' own kinds, beside MIGRANT_PROFILE's: each has weights over MIGRANT_CLASSES (summing to 1) and a women's
# share, or (Rustication's youth) an age range booked by single year in proportion to each age's people.
# - penal: mostly 15-35, 85% men. Of the ~162,000 convicts sent to Australia, ~25,000 were women (15.4%), their average
#   age about 25 and a fifth under 20 (owner, 2026-10-19). Classes 15-17, 18-35, 36-59 at 12/78/10 (the controller's
#   proposal after review, confirmed by the owner on 2026-10-20): a fifth under 20 is about 12% at 15-17, three of its
#   five years; 18-19 sit in the 18-35 class; a tenth over 35.
# - youth: China's sent-down youth, 15-24, both sexes evenly. 15-24 straddles the classes (15-17, 18-35), so it is booked
#   over the single years 15-24 instead: one rate per sex over the people of those ages (the bands 15-19 and 20-24).
# - retreat: Managed Retreat moves whole communities, weighted to the old: the refugee kind with its 60+ weight doubled,
#   renormalised.
_REFUGEE_W = MIGRANT_PROFILE["refugee"]["weights"]
RESETTLE_KINDS = {
    "penal": {"weights": [0.0, 0.12, 0.78, 0.10, 0.0], "women": 0.15},
    "youth": {"ages": (15, 24), "women": 0.5},
    "retreat": {"weights": [w / (sum(_REFUGEE_W) + _REFUGEE_W[-1]) * (2 if c == len(_REFUGEE_W) - 1 else 1)
                            for c, w in enumerate(_REFUGEE_W)], "women": 0.5},
}
# Each programme's movers as (kind, weight, women's share) parts, the weights summing to 1. The family and refugee kinds
# split evenly (None: the kind's own share); the labour kind takes the women's share given, or "jobs": the destination's
# jobs, as the residual's labour kind (LABOUR_FEMALE_SHARE_MIN + its female_job_share x women's rights x the range; no
# balance ramp, LABOUR_BALANCE_*: a known move is not an estimate). Owner calls, 2026-10-19; Penal Transportation's class
# split (above) was confirmed on 2026-10-20, and the Development Program's 60/40 was being confirmed as this was built:
# one edit here if it changes.
RESETTLE_PROFILES = {
    "land_grants": (("family", 1.0, None),),
    "military_colonies": (("labour", 0.5, 0.2), ("family", 0.5, None)),   # half the labour kind at 80% men, half families
    "penal_transportation": (("penal", 1.0, None),),
    "organized_colonization": (("family", 1.0, None),),
    "special_settlements": (("refugee", 1.0, None),),                     # whole families, all ages
    # FELDA and Transmigrasi moved households; the Virgin Lands began young and male, and the families followed
    "development_program": (("family", 0.6, None), ("labour", 0.4, "jobs")),
    "rustication": (("youth", 1.0, None),),
    "managed_retreat": (("retreat", 1.0, None),),
}
# The booking (my call, 2026-10-19): a known move bypasses the residual's caps (MIGRANT_CAP_IN, _OUT) and its labour
# balance ramps: it is a count, not an estimate. It keeps the sweep's own guard (a cohort gives at most half of what is
# left of it), and a class or the youth's ages with under one person pass their share to one flat rate over every class
# with people, as the residual's leftover does.

# ---- The US frontier at the 1836 seed (2026-10-19) ----
# Spec §2.6: "The US frontier states start young and male." History data, as France's Family Limitation is:
# common/history/extra_history.txt marks the states the US holds in these state regions in 1836 (te_dg_frontier), and
# their 1836 seed (te_demog_frontier_begin, te_demog_frontier_slot) sets each age group's men to its women x the
# ratio below; the seed's normalisation keeps the state's people, and the ring then ages as any other.
# Source: the Sixth Census, 1840: Compendium of the Enumeration of the Inhabitants and Statistics of the United States
# (1841), each state's "Total in ..." rows of free white persons by sex and age
# (https://www.census.gov/library/publications/1841/dec/1840c.html; the scans
# https://www2.census.gov/library/publications/decennial/1840/1840v3/1840c-04.pdf (Alabama, Mississippi, Louisiana),
# 1840c-05.pdf (Indiana), 1840c-06.pdf (Illinois, Missouri, Arkansas, Michigan, Florida Territory) and 1840c-07.pdf
# (Wisconsin and Iowa Territories)), read 2026-10-19; every state's cells sum to its official white total (Gibson and
# Jung, Census Bureau Working Paper 56, 2002, Table A-21).
# Free white (men, women) by the census's age groups; 60+ sums its 60-69 ... 100+. Under 15 the census reads 102-109
# men per 100 women, about the seed's own, so the seed's children stay as they are.
# Which states (owner, 2026-10-20): the West the first build chose (Michigan, Indiana, Illinois, Missouri, Arkansas,
# Iowa, Wisconsin), and every other state or territory the US holds in 1836 whose free white men per 100 women aged
# 15-49 were 110 or more in 1840: the Old Southwest and Florida, Mississippi 131.6, Alabama 116.2, Louisiana 155.7,
# Florida Territory 177.3. Every other state's row was read from the same scans (1840c-02 to -07) on 2026-10-20 and
# each sums to its Table A-21 white total (A-21 counts Alexandria County, then in the District of Columbia, in Virginia,
# so those two sum once it is moved back): Maine 100.5, New Hampshire 93.0, Vermont 99.3, Massachusetts 99.4, Rhode Island 92.7, Connecticut 95.7,
# New York 103.0, New Jersey 100.1, Pennsylvania 100.5, Delaware 98.7, Maryland 98.0, the District of Columbia 91.8,
# Virginia 97.1 (Western District 102.0), North Carolina 91.7, South Carolina 99.0, Georgia 106.6, Kentucky 108.0,
# Tennessee 98.8, Ohio 107.2. Indiana (107.7) stays as one of the first build's West: the 110 rule is for additions.
FRONTIER_1840_WHITE = {
    "STATE_MICHIGAN": {(15, 19): (10887, 10819), (20, 29): (22759, 18706), (30, 39): (16025, 11864),
                       (40, 49): (8276, 6109), (50, 59): (4442, 3394), (60, 149): (2629, 1985)},
    "STATE_INDIANA": {(15, 19): (36599, 36904), (20, 29): (60002, 55176), (30, 39): (37565, 32708),
                      (40, 49): (21678, 19967), (50, 59): (13789, 10759), (60, 149): (9086, 7319)},
    "STATE_ILLINOIS": {(15, 19): (24876, 24078), (20, 29): (52580, 38823), (30, 39): (31428, 22676),
                       (40, 49): (15809, 12712), (50, 59): (8755, 6514), (60, 149): (5084, 4032)},
    "STATE_MISSOURI": {(15, 19): (16784, 16952), (20, 29): (33772, 26330), (30, 39): (20568, 14889),
                       (40, 49): (11384, 8580), (50, 59): (5620, 4259), (60, 149): (3469, 2808)},
    "STATE_ARKANSAS": {(15, 19): (3863, 3911), (20, 29): (8532, 5881), (30, 39): (5129, 3317),
                       (40, 49): (2751, 1715), (50, 59): (1194, 805), (60, 149): (727, 504)},
    "STATE_IOWA": {(15, 19): (2179, 2064), (20, 29): (6207, 3789), (30, 39): (3310, 1865),             # Iowa Territory
                   (40, 49): (1512, 979), (50, 59): (698, 494), (60, 149): (357, 245)},
    "STATE_WISCONSIN": {(15, 19): (1344, 1200), (20, 29): (6328, 2713), (30, 39): (3348, 1423),        # Wisconsin Territory
                        (40, 49): (1191, 612), (50, 59): (554, 360), (60, 149): (269, 175)},
    # the Old Southwest and Florida (owner, 2026-10-20): 1840c-04.pdf PDF pp.5-6, 9-10, 13-14 (Compendium pp.52-61) and
    # 1840c-06.pdf pp.13-14 (pp.96-97)
    "STATE_MISSISSIPPI": {(15, 19): (8662, 8911), (20, 29): (20084, 14464), (30, 39): (11995, 7847),
                          (40, 49): (6001, 4284), (50, 59): (3289, 2250), (60, 149): (2044, 1580)},
    "STATE_ALABAMA": {(15, 19): (16222, 17911), (20, 29): (31455, 25574), (30, 39): (19340, 15152),
                      (40, 49): (11783, 9184), (50, 59): (6024, 4647), (60, 149): (4223, 3518)},
    "STATE_LOUISIANA": {(15, 19): (7218, 7947), (20, 29): (20795, 13602), (30, 39): (16304, 7907),
                        (40, 49): (7940, 4099), (50, 59): (3309, 1967), (60, 149): (1762, 1315)},
    "STATE_FLORIDA": {(15, 19): (1305, 1322), (20, 29): (4388, 2220), (30, 39): (2801, 1219),         # Florida Territory
                      (40, 49): (1193, 704), (50, 59): (530, 354), (60, 149): (317, 218)},
}
# The census counts free whites; the game's 1836 state also holds enslaved and free Black people and Native nations
# (Arkansas's state region takes in the Cherokee, Iowa's the Sauk and Meskwaki and the Dakota), whose numbers of men
# and women were near even (Missouri's and Arkansas's slaves 97 and 103 men per 100 women in 1840). So each age group's
# men per woman is the mixture of a settler share s of its people at the settlers' ratio r with the rest at one to one,
# (s r/(1+r) + (1-s)/2) / (s/(1+r) + (1-s)/2) (frontier_mix; my call, 2026-10-19, the exact form since review): s is the share of
# region_state:USA's pops in game/common/history/pops/05_north_america.txt (1.14.5) of the settler cultures (yankee,
# dixie, cajun, irish, north_german; dixie of every religion). Minnesota and the US's unincorporated western states hold
# no settlers in 1836. In the Old Southwest the enslaved are a third to nearly half of the people, so the settler share
# is low there and frontier_mix pulls the census's ratio most of the way to one to one. Louisiana's French settlers are
# the game's cajun pops, already in the list; it has no other white culture. Florida's share is the US's state alone
# (the Seminole hold the rest of the region).
FRONTIER_SETTLER_SHARE = {
    "STATE_MICHIGAN": (128000 + 8000) / 152000,
    "STATE_INDIANA": (631504 + 4004 + 20000) / 663508,
    "STATE_ILLINOIS": 452400 / 456400,
    "STATE_MISSOURI": (9642 + 142662 + 2000 + 165204 + 8000) / 367508,
    "STATE_ARKANSAS": (12635 + 33857) / 92620,
    "STATE_IOWA": 23992 / 43992,
    "STATE_WISCONSIN": 28004 / 36004,
    "STATE_MISSISSIPPI": 172804 / 260804,
    "STATE_ALABAMA": (329008 + 16004) / 600480,
    "STATE_LOUISIANA": (35992 + 118392 + 200) / 294684,
    "STATE_FLORIDA": 47996 / 82996,
}


def frontier_mix(r, s):
    """Men per woman of people a share s of whom are settlers at r men per woman, the rest at one to one."""
    women = s / (1 + r) + (1 - s) / 2
    return (s * r / (1 + r) + (1 - s) / 2) / women


# {state region: {"ratios": {(first age, last age): men per woman at the seed}}}
FRONTIER_1836 = {
    region: {"ratios": {ages: frontier_mix(m / f, FRONTIER_SETTLER_SHARE[region]) for ages, (m, f) in groups.items()}}
    for region, groups in FRONTIER_1840_WHITE.items()
}

# ---- Uploaded minds (2026-10-19) ----
# docs/superpowers/archive/specs/2026-10-16-demographics-uploaded-minds-design.md, the owner's calls of 2026-10-19 (§7); the model
# is demographics_uploads.py, the script te_demog_um_effects.txt. Under Full only.
# Mind Backups' restore (call 2): its two -0.5 lines sit on these census-only types, which the census adds x the state's
# longevity care E (last step's), so the restore is 1 - 0.5 x E; outside Full the flat absorbed -5% stays.
BACKUP_TYPES = {"external": "state_backup_external_mortality_mult", "work": "state_backup_work_mortality_mult"}
DEMOG_TYPES = DEMOG_TYPES + tuple(BACKUP_TYPES.values())
# Who uploads (call 1): those in longevity care facing death from infection or chronic illness (call 4) in a country with
# UM_TECH and at least one level of UM_BUILDING. Capacity (call 3): UM_PER_LEVEL minds a level, country-wide.
UM_TECH = "mind_backups"
UM_BUILDING = "building_mind_upload_nexus"
UM_PER_LEVEL = 1_000_000
# The pool's loss (call 5): this share of the active minds a year choose to end; archived minds (call 7) don't.
UM_END_RATE = 0.001
# The Nexus's output under Full (call 6): each good's production-method line x the country's utilisation (active minds
# over capacity) x its factor, so a full level makes about UM_MIND_OUTPUT a mind a week at base prices (the calibration in
# the PR body: between an era-12 services worker and the top software method's 64). Digital assets lead (traded);
# services stay at today's line (local: they flood their own state). Inputs lean on the traded goods; electricity and
# digital access are local.
UM_MIND_OUTPUT = 40
UM_OUTPUT_FACTORS = {"digital_assets": 15, "tourism": 2, "fine_art": 2, "services": 1}
UM_INPUT_FACTORS = {"electricity": 2, "electronic_components": 8, "digital_access": 2, "advanced_materials": 8}
# its research speed a level, the production method's country line, which the census scales by utilisation
UM_RESEARCH_PER_LEVEL = 0.05
# The Devout's approval (call 8): while the pool is over UM_DEVOUT_SHARE of the people (minds and bodies), by
# UM_DEVOUT_APPROVAL. Built behind the switch, off by default (generated te_demog_k_um_politics), like the gap's was.
UM_POLITICS = False
UM_DEVOUT_SHARE = 0.01
UM_DEVOUT_APPROVAL = -3

# ---- The metropolitan share (spec §5.2; 2026-10-19) ----
# A state's metropolitan share, 0-100: the share of its urban people living in its largest city. A modelled stock
# (a state has one city hub and no cities below it) that moves MT_DRIFT of the way to its target each year, at the
# state's yearly count, and starts at its target. The target is MT_BASE plus eight terms, in share points, within
# MT_MIN..MT_MAX (scripts/analysis/demographics_metro.py; te_demog_metro_values.txt, which
# test_demographics_metro.py pins to these).
MT_DRIFT = 0.05
MT_BASE = 40
MT_MIN = 5
MT_MAX = 95
# A state with fewer urban people than this has no settlement pattern (no share, no effects): one market town's worth.
MT_MIN_URBAN = 5000
# The labels (owner, 2026-10-08): Metropolis from 60, Leading City from 40, Several Cities from 20, Market Towns below.
MT_LABELS = (60, 40, 20)
# 1. The national capital: government, finance and the court draw one city (Paris, Moscow).
MT_CAPITAL = 35
# 2. A gateway: the market area's World Market Hub (one per market area, its port to the world: New York, Buenos
# Aires), and a Financial District, a point a level up to MT_FINANCE_MAX.
MT_HUB = 30
MT_FINANCE_PER_LEVEL = 1
MT_FINANCE_MAX = 10
# 3. Area (the state region's, te_region_area_km2): MT_AREA_STEP points down for each doubling past MT_AREA_FREE km2,
# MT_AREA_DOUBLINGS doublings at most (Texas, 536,000 km2, takes more than two: large enough for four metros; New York
# and Ile-de-France none to speak of).
MT_AREA_FREE = 100000
MT_AREA_STEP = 5
MT_AREA_DOUBLINGS = 3
# 4. Farms and mines: MT_WORK points down at a wholly rural state, x the walk's rural share (1 - te_dg_urban_share).
MT_WORK = 30
# 5. Urbanisation, the inverted U (Williamson, 1965): the owner's national urban share (te_dg_urban_share at its
# census), MT_URBAN_SIZE x (1 - ((N - MT_URBAN_PEAK) / MT_URBAN_WIDTH)^2): 0 at 10% and at 90% urban, MT_URBAN_SIZE at
# half, and a little below 0 beyond them (-2.7 at 95%, -5.6 at 0% or 100%). The script's floor of -MT_URBAN_SIZE is a
# guard that never binds on 0-1.
MT_URBAN_PEAK = 0.5
MT_URBAN_WIDTH = 0.4
MT_URBAN_SIZE = 10
# 6. Infrastructure surplus over usage: MT_INFRA points down at a surplus as large as the usage (the ratio within 0-1).
MT_INFRA = 10
# 7. Migration Crowding: MT_CROWD points down at its ceiling (the applied multiplier MT_CROWD_CEILING, ten times the
# reference density), in proportion below it.
MT_CROWD = 10
MT_CROWD_CEILING = 4.5
# 8. Planning: the Ministry of Urban Planning (MT_TYPE on the institution, MT_MINISTRY_PER_LEVEL a level), a Settlement
# Authority on Planned Towns (MT_PLANNED_TOWNS_PER_LEVEL a level) and a Planned Capital (MT_PLANNED_CAPITAL), all down;
# the term within MT_PLAN_MIN..0.
MT_TYPE = "state_metro_share_add"
MT_MINISTRY_PER_LEVEL = -1
MT_PLANNED_TOWNS_PER_LEVEL = -2
MT_PLANNED_CAPITAL = -10
MT_PLAN_MIN = -30
# The effects (Full only), each at most 10% (owner, 2026-10-19). The concentrated side grows in a straight line from
# nothing at MT_EFFECT_FROM (Leading City's floor) to full at MT_EFFECT_FULL (Metropolis's); the dispersed side, the
# infrastructure loss alone, from nothing at MT_DISPERSED_FROM (Market Towns' ceiling) to full at MT_DISPERSED_FULL (the
# target's floor, MT_MIN).
MT_EFFECT_FROM = 40
MT_EFFECT_FULL = 60
MT_DISPERSED_FROM = 20
MT_DISPERSED_FULL = 5
MT_EFFECTS = {"state_migration_crowding_density_mult": -0.10,     # crowds sooner (a positive value is capacity)
              "state_infrastructure_from_population_mult": 0.10,  # a compact city is cheaper to serve
              "building_urban_center_throughput_add": 0.05,       # agglomeration: the city's services
              "state_turmoil_effects_mult": 0.05}                 # one city concentrates its radicals (a little)
MT_DISPERSED_EFFECTS = {"state_infrastructure_from_population_mult": -0.10}
# Fertility: the census's urban term (URBAN_WEIGHT x urban x relief) is raised by MT_FERTILITY x the concentrated
# side's strength, so at full strength by a tenth.
MT_FERTILITY = 0.10

# ---- The life table's open last interval (2026-10-20) ----
# The life tables (demographics_model.life_table, te_demog_lt_finish) sum person-years over GROUPS, which end at 145-149;
# the survivors at 150 live on at the death rate past 150, q a year (per 100,000): l150 x (1 - q/2) / q more person-years
# (life_table's mid-year convention for an open interval), in e0 and in e65 (owner, 2026-10-20). q is the last group's
# in the plain table and the untreated's; in the late game's treated and blended tables the rate the pool (150+) dies
# at, its treated part at its biological rate age. LT_TAIL_RATE_MIN floors q: one per 100,000, the fixed point's
# smallest step for a yearly probability, so the tail is at most about 100,000 years and stays inside the script's
# range (survivors at a radix of 100,000 x 100,000 / q). The old-age threshold still reads the table to 150.
LT_TAIL_RATE_MIN = 1.0
# The panel shows life expectancy as it is up to this and "over" it past (owner, 2026-10-20); the stored figure stays
# exact. The history chart's axis runs to the largest figure it holds, at least E0_AXIS_MIN, at most this.
E0_SHOWN_MAX = 10000
E0_AXIS_MIN = 100
