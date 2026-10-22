"""The demographic effects' curves and sizes, old and new: the Python twin of the 2026-10-22 effects design
(docs/superpowers/specs/2026-10-22-demographic-effects-impact-design.md).

Each condition's strength reads 1 at its reference point and keeps rising past it at half the slope
(`extended`), capped at 2 only where the scale has no natural end; Wealth Concentration's upper end is straight.
The `_old` twins are the curves before the design, kept so `demographics_harness.py effects` can read a save
both ways. SIZES holds every resized modifier's fields at 1x; the script's size tests pin the static modifiers
to it.
"""

CAP = 2.0

# Wealth Concentration (te_inheritance_values.txt): neutral at 50, full at 80 and 20.
WC_NEUTRAL = 50.0
WC_SPAN = 30.0
WC_SPAN_OLD = 50.0
# The urban pattern (te_demog_place_values.txt): primacy, the largest city's share of urban people.
UP_FLOOR = 0.25
UP_SPAN = 0.25
UP_SPAN_OLD = 0.35
# The metropolitan share (te_demog_metro_values.txt), 0-100.
MT_FROM = 40.0
MT_FULL = 60.0
MT_DISPERSED_FROM = 20.0
MT_DISPERSED_FULL = 5.0
# Sex balance, men per 100 women aged 20-59 (demographics_params.SEX_*).
SEX_MORE_FROM = 110.0
SEX_MORE_FULL = 130.0
SEX_MORE_FULL_OLD = 150.0
SEX_FEWER_FROM = 90.0
SEX_FEWER_FULL = 80.0
# The youth bulge (demographics_params.YOUTH_*).
YOUTH_FROM = 0.18
YOUTH_SPAN = 0.06
YOUTH_UNEMPLOYMENT_FULL = 0.2
# Inequality: the shown Gini (te_demog_inequality_refresh).
GINI_FROM = 0.45
GINI_STEEP = 0.70
GINI_SPAN = 0.20

# Wealth Concentration's national bubble line, a month at 1x (banking_cycle_simulation.md §27). The
# dispersed side is the larger: bubble pressure stops at 0, so a push down moves crashes less far.
BUBBLE_GREAT = 0.3
BUBBLE_DISPERSED = -0.4


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def extended(x, cap=None):
    """(x + min(x, 1)) / 2 for x >= 0 (0 below): x up to 1, then half the slope; at most cap."""
    x = max(x, 0.0)
    s = (x + min(x, 1.0)) / 2
    return min(s, cap) if cap is not None else s


# ---- new strengths ----

def wc_high(score):
    """Great Fortunes / Concentrated Property: straight, (score - 50) / 30, 5/3 at 100."""
    return 0.0 if score is None else max((score - WC_NEUTRAL) / WC_SPAN, 0.0)


def wc_low(score):
    """Dispersed Wealth / Dispersed Property: full at 20, then half the slope (4/3 at 0)."""
    return 0.0 if score is None else extended((WC_NEUTRAL - score) / WC_SPAN)


def primacy(p):
    return 0.0 if p is None else extended((p - UP_FLOOR) / UP_SPAN, CAP)


def metro_up(share):
    return 0.0 if share is None else extended((share - MT_FROM) / (MT_FULL - MT_FROM))


def metro_down(share):
    """Market Towns: nothing beyond the target's floor of 5, so the ramp stays 0-1."""
    if share is None:
        return 0.0
    return _clamp((MT_DISPERSED_FROM - share) / (MT_DISPERSED_FROM - MT_DISPERSED_FULL), 0.0, 1.0)


def more_men(balance):
    return 0.0 if balance is None else extended((balance - SEX_MORE_FROM) / (SEX_MORE_FULL - SEX_MORE_FROM), CAP)


def fewer_men(balance):
    return 0.0 if balance is None else extended((SEX_FEWER_FROM - balance) / (SEX_FEWER_FROM - SEX_FEWER_FULL), CAP)


def youth(share, unemployment):
    """Each factor extended past 1, the product at most 2."""
    if share is None or unemployment is None:
        return 0.0
    return min(extended((share - YOUTH_FROM) / YOUTH_SPAN) * extended(unemployment / YOUTH_UNEMPLOYMENT_FULL), CAP)


def inequality(gini):
    """+1 per 0.2 above 0.45, twice that above 0.70; no cap."""
    if gini is None:
        return 0.0
    return max(gini - GINI_FROM, 0.0) / GINI_SPAN + max(gini - GINI_STEEP, 0.0) / GINI_SPAN


# ---- old strengths (before the design), for the readouts ----

def wc_high_old(score):
    return 0.0 if score is None else _clamp((score - WC_NEUTRAL) / WC_SPAN_OLD, 0.0, 1.0)


def wc_low_old(score):
    return 0.0 if score is None else _clamp((WC_NEUTRAL - score) / WC_SPAN_OLD, 0.0, 1.0)


def primacy_old(p):
    return 0.0 if p is None else _clamp((p - UP_FLOOR) / UP_SPAN_OLD, 0.0, 1.0)


def metro_up_old(share):
    return 0.0 if share is None else _clamp((share - MT_FROM) / (MT_FULL - MT_FROM), 0.0, 1.0)


def more_men_old(balance):
    if balance is None:
        return 0.0
    return _clamp((balance - SEX_MORE_FROM) / (SEX_MORE_FULL_OLD - SEX_MORE_FROM), 0.0, 1.0)


def fewer_men_old(balance):
    if balance is None:
        return 0.0
    return _clamp((SEX_FEWER_FROM - balance) / (SEX_FEWER_FROM - SEX_FEWER_FULL), 0.0, 1.0)


def youth_old(share, unemployment):
    if share is None or unemployment is None:
        return 0.0
    return (_clamp((share - YOUTH_FROM) / YOUTH_SPAN, 0.0, 1.0)
            * _clamp(unemployment / YOUTH_UNEMPLOYMENT_FULL, 0.0, 1.0))


def inequality_old(gini):
    return 0.0 if gini is None else max(gini - GINI_FROM, 0.0) / GINI_SPAN


# The one-figure conditions: name -> (old, new). The youth bulge takes two figures and is read by name.
CONDITIONS = {
    "wc_high": (wc_high_old, wc_high),
    "wc_low": (wc_low_old, wc_low),
    "primacy": (primacy_old, primacy),
    "metro_up": (metro_up_old, metro_up),
    "metro_down": (metro_down, metro_down),
    "fewer_men": (fewer_men_old, fewer_men),
    "more_men": (more_men_old, more_men),
    "inequality": (inequality_old, inequality),
}

# Every resized modifier's fields at 1x (the spec's tables).
SIZES = {
    "inh_great_fortunes": {
        "country_aristocrats_pol_str_mult": 0.2,
        "country_capitalists_pol_str_mult": 0.2,
        "country_bubble_pressure_monthly_add": BUBBLE_GREAT,
    },
    "inh_dispersed_wealth": {
        "country_aristocrats_pol_str_mult": -0.2,
        "country_capitalists_pol_str_mult": -0.2,
        "country_bubble_pressure_monthly_add": BUBBLE_DISPERSED,
    },
    "inh_concentrated_property": {
        "state_aristocrats_investment_pool_efficiency_mult": 0.2,
        "state_capitalists_investment_pool_efficiency_mult": 0.2,
        "state_political_strength_from_wealth_mult": 0.2,
        "state_pop_qualifications_mult": -0.2,
        "state_education_access_add": -0.1,
    },
    "inh_dispersed_property": {
        "state_political_strength_from_wealth_mult": -0.1,
        "state_pop_qualifications_mult": 0.1,
        "state_education_access_add": 0.1,
        "state_radicals_from_political_movements_mult": -0.1,
    },
    "inh_land_hunger": {
        "state_migration_quota_mult": 0.3,
        "state_pop_support_movement_land_reform_mult": 0.25,
        "state_radicals_from_political_movements_mult": 0.1,
    },
    "te_demog_census_inequality": {
        "state_radicals_from_political_movements_mult": 0.1,
        "state_pop_support_movement_socialist_mult": 0.1,
        "state_pop_support_movement_labor_mult": 0.1,
    },
    "te_demog_primate_city": {
        "building_urban_center_throughput_add": 0.2,
        "state_migration_pull_mult": 0.25,
        "building_university_throughput_add": 0.1,
    },
    "te_demog_provincial_neglect": {
        "state_migration_pull_mult": -0.15,
        "state_turmoil_effects_mult": 0.15,
        "state_pop_support_movement_cultural_minority_mult": 0.15,
    },
    "te_demog_mt_metropolis": {
        "state_infrastructure_from_population_mult": 0.2,
        "building_urban_center_throughput_add": 0.1,
        "state_turmoil_effects_mult": 0.1,
    },
    "te_demog_mt_crowding": {
        "state_migration_crowding_density_mult": -0.1,
    },
    "te_demog_mt_dispersed": {
        "state_infrastructure_from_population_mult": -0.2,
    },
    "te_demog_census_youth_bulge": {
        "state_radicals_from_political_movements_mult": 0.25,
        "state_turmoil_effects_mult": 0.15,
    },
    "te_demog_census_fewer_men": {
        "state_pop_support_movement_feminist_mult": 0.25,
    },
    "te_demog_census_more_men": {
        "state_radicals_from_political_movements_mult": 0.15,
        "state_turmoil_effects_mult": 0.15,
    },
}
