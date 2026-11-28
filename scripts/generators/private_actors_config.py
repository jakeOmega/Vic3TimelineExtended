"""The hand-set inputs of the Private Actors sector generator: features, the law table and its numbers.

``gen_private_actors.py`` reads every company type's building types and production methods and writes each
firm's **sector** as generated script (docs/superpowers/specs/2026-11-28-actors-firms-design.md § 5.1; the
plan's Task 1). Everything the data can say is derived there. This file holds only what the data cannot:

* ``FEATURES``: the sector features the law table and the chains read (``te_pa_g_f_<feature>``, 0 or 1), each
  defined from building groups, building types, a production method marker, outputs or what a law names, with
  what the definition rests on.
* ``LAW_TABLE``: § 8.1's table as data. For each law of each covered group, the terms that make a firm's
  stance on it (−2 to +2, § 8.1 sums them over the sector), or no terms and the reason it has none. Every
  term's comment says what in the law (its modifiers, its ``on_activate``, the system that reads it) the sign
  rests on. These are first readings, checked against the laws' modifiers on 2026-11-28 (vanilla 1.15.2 and
  the mod as merged).
* The numbers: each becomes a named script value in ``common/script_values/te_pa_gen_values.txt``.
* ``TRAIT_TEMPERAMENT`` and ``IDEOLOGY_TEMPERAMENT`` (with their neutral lists): § 5.3's temperament, what each
  personality trait and character ideology an executive can hold says about the firm, on four axes.

``test_gen_private_actors.py`` holds the table to the laws: every law of a covered group has a row (terms or a
reason), so a law added later fails the test until it is signed here; and the temperament tables to the traits and
ideologies, the same way.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Numbers (each written as a named script value, te_pa_gen_<name>)
# ---------------------------------------------------------------------------

NUMBERS = {
    # The labor laws' bands (§ 8.1: "by how many people a level of their buildings employs"). A firm whose
    # base methods employ at least band_1 a level is weighed once, at least band_2 twice. Of the 326 types,
    # about 80% reach band 1 and 15% band 2 (2026-11-28): the generic types run vanilla's staffing, the
    # flavored ones average it with a small flagship building.
    "jobs_band_1": 3000,
    "jobs_band_2": 6000,
    # A firm this share of its sector or more is "big" on the antitrust laws: § 6.1's threshold, where the
    # home state is told the firm could soon restrict the market (te_pa_share, Task 2).
    "big_share": 0.4,
    # The laboratory strength at which a firm under Strict IP Protection may form a patent pool (§ 10.3).
    "patent_pool_lab": 80,
    # A technology the home country lacks counts this much more when some country in the world holds it
    # (§ 10.1: "counted half again").
    "tech_held_bonus": 0.5,
    # The campaign spending at which a firm's stance on the Electoral Finance laws is full (te_pa_campaign_total,
    # pounds, written by Task 5). First guess, for Task 5 to set against what firms actually spend.
    "campaign_full": 50000,
}

# ---------------------------------------------------------------------------
# Company types that are not firms
# ---------------------------------------------------------------------------

EXCLUDED_COMPANY_TYPES = {
    "company_gm_name_carrier": (
        "A placeholder the Grand Monument naming popup creates while the player types a name and removes after "
        "(common/scripted_guis/gm_sguis.txt); its one building type is a hidden anchor. Never a firm."
    ),
}

# ---------------------------------------------------------------------------
# Inputs the sector reading leaves out
# ---------------------------------------------------------------------------

# Besides local goods and goods the type itself makes (the generator's rule), these never count among a
# firm's two inputs.
INPUTS_LEFT_OUT = {
    "construction": (
        "The upkeep nearly every building pays through the mod's maintenance groups (pmg_maintenance*, hidden in "
        "the building panel; docs/systems/mod_systems/construction.md). It is no good a sector is about, and at "
        "1,000 a unit it would outrank a farm's or a port's real inputs."
    ),
}

# ---------------------------------------------------------------------------
# Sector features
# ---------------------------------------------------------------------------

# Building-group features look at a building type's group and every group above it, and leave out a company's
# flagship buildings (bg_company_buildings): that group sits under bg_private_infrastructure, so counting it
# would make nearly every flavored company an infrastructure firm. A flagship counts through its outputs and
# its company's other building types.
COMPANY_FLAGSHIP_GROUP = "bg_company_buildings"


@dataclass(frozen=True)
class Feature:
    why: str
    groups: tuple[str, ...] = ()          # a building type in one of these groups or below (flagships left out)
    buildings: tuple[str, ...] = ()       # one of these building types
    companies: tuple[str, ...] = ()       # one of these company types
    method_marker: str | None = None      # a building type with a production method carrying this modifier
    output_categories: tuple[str, ...] = ()  # main output of one of these goods categories, bought for a pop need
    law_removes: str | None = None        # a building type this law's on_activate removes (remove_building)
    law_subsidizes: str | None = None     # a building type this law makes require subsidies
    law_collectivizes: tuple[str, ...] = ()  # a building in a group these laws open to collectivization


FEATURES = {
    "fossil": Feature(
        why=(
            "The three building types the Resource Transition laws act on: their INJECTs in "
            "common/buildings/extra_buildings.txt gate construction on rt_fossil_construction_allowed_here, and "
            "Managed Fossil Phaseout's programmes retire them (docs/systems/mod_systems/global_warming.md). "
            "Company flagships that dig coal or pump oil are left out, as the laws leave them out."
        ),
        buildings=("building_coal_mine", "building_oil_rig", "building_power_plant"),
    ),
    "financial": Feature(
        why=(
            "No building type in vanilla or the mod is a bank, so a building rule finds no financial firm. These "
            "are the companies whose history is banking or investment: SoftBank's Vision Fund; the Yasuda, "
            "Mitsui, Sumitomo and Mitsubishi zaibatsu, each built round its bank; the Nederlandsche "
            "Handel-Maatschappij, later ABN AMRO; Jardine Matheson's banking and insurance."
        ),
        companies=(
            "company_softbank", "company_yasuda", "company_mitsui", "company_sumitomo", "company_mitsubishi",
            "company_nhm", "company_jardine_matheson",
        ),
    ),
    "automatable": Feature(
        why=(
            "A building type with a robotic or AI-managed method: the marker the Automation Policy laws act on "
            "(building_robotic_or_ai_managed_bool in a method's unscaled block; "
            "docs/systems/mod_systems/automation_policy.md)."
        ),
        method_marker="building_robotic_or_ai_managed_bool",
    ),
    "manufacturing": Feature(
        why="bg_manufacturing and below (light, heavy, military and high-tech industry, shipyards, construction).",
        groups=("bg_manufacturing",),
    ),
    "extraction": Feature(
        why="bg_extraction and below (mines, logging, rubber, whaling, fishing, oil): what Extraction Economy names.",
        groups=("bg_extraction",),
    ),
    "agriculture": Feature(
        why="bg_agriculture (farms, vineyards) and bg_ranching (ranches): the rural owners' sector Agrarianism favors.",
        groups=("bg_agriculture", "bg_ranching"),
    ),
    "plantation": Feature(
        why=(
            "bg_plantations, the group Industry Banned's and Extraction Economy's throughput lines name. The rubber "
            "plantation sits under bg_extraction in vanilla and counts as extraction."
        ),
        groups=("bg_plantations",),
    ),
    "infrastructure": Feature(
        why="bg_infrastructure and below (ports, railways, highways, airports, networks, trade centers, canals).",
        groups=("bg_infrastructure",),
    ),
    "power": Feature(
        why="bg_power and below (power plants, clean power): the utilities of § 6.2's Regulated Utilities row.",
        groups=("bg_power",),
    ),
    "consumer_good": Feature(
        why=(
            "The main output is a staple or luxury good some pop need lists (common/pop_needs/): sold to "
            "households. Industrial goods pops also buy (coal and oil for heating, glass) are left out."
        ),
        output_categories=("staple", "luxury"),
    ),
    "collectivizable": Feature(
        why=(
            "A building in a group Guild System, Factory Councils and Cooperative Ownership open to "
            "collectivization (building_group_<bg>_allowed_collectivization_add): manufacturing, extraction, "
            "power, private infrastructure and arts."
        ),
        law_collectivizes=("law_guild_system", "law_factory_councils", "law_cooperative_ownership"),
    ),
    "subsidized": Feature(
        why="A building type Interventionism makes require subsidies (country_building_<x>_require_subsidies_bool).",
        law_subsidizes="law_interventionism",
    ),
    "rm_industry_banned": Feature(
        why="A building type Industry Banned's on_activate removes from every state.",
        law_removes="law_industry_banned",
    ),
    "rm_extraction_economy": Feature(
        why="A building type Extraction Economy's on_activate removes from every state.",
        law_removes="law_extraction_economy",
    ),
}

# ---------------------------------------------------------------------------
# Conditions on the firm's own record (company scope), for terms that are not sector features
# ---------------------------------------------------------------------------

# Each reads a variable a later task writes (the plan's Storage table), guarded so it reads as false (or, for
# "small", as true) while the variable is unset.
CONDITIONS = {
    "big": "has_variable = te_pa_share var:te_pa_share >= te_pa_gen_big_share",
    "small": "trigger_if = { limit = { has_variable = te_pa_share } var:te_pa_share < te_pa_gen_big_share }",
    "utility": "OR = { var:te_pa_g_f_infrastructure ?= 1 var:te_pa_g_f_power ?= 1 }",
    "favored": "var:te_pa_posture ?= 1",
    "not_favored": "NOT = { var:te_pa_posture ?= 1 }",
    "lab": "has_variable = te_pa_lab var:te_pa_lab > 0",
    "patent_pool": "has_variable = te_pa_lab var:te_pa_lab >= te_pa_gen_patent_pool_lab",
    "behind_no_lab": (
        "has_variable = te_pa_g_tech_gap var:te_pa_g_tech_gap > 0 "
        "trigger_if = { limit = { has_variable = te_pa_lab } var:te_pa_lab <= 0 }"
    ),
}

# ---------------------------------------------------------------------------
# The law table (§ 8.1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Term:
    kind: str          # "feature", "all", "when", "labor", "campaign"
    weight: float      # signed; the stance is the sum, clamped to -2..+2
    arg: object = None  # the feature's name, or a tuple of CONDITIONS names (all must hold)


@dataclass(frozen=True)
class Row:
    terms: tuple[Term, ...]
    why: str           # what in the law the signs rest on, or why it has none


def feature(name: str, weight: float) -> Term:
    """weight for a firm whose sector has the feature."""
    return Term("feature", weight, name)


def every(weight: float) -> Term:
    """weight for every firm."""
    return Term("all", weight)


def when(conditions, weight: float) -> Term:
    """weight for a firm whose record meets every named condition."""
    return Term("when", weight, tuple([conditions] if isinstance(conditions, str) else conditions))


def labor(weight: float) -> Term:
    """weight x the firm's staffing band (0, 1 or 2; NUMBERS' jobs_band_1 and _2)."""
    return Term("labor", weight)


def campaign(weight: float) -> Term:
    """weight x the firm's campaign spending over NUMBERS' campaign_full, at most 1 (te_pa_campaign_total)."""
    return Term("campaign", weight)


def row(*terms: Term, why: str) -> Row:
    return Row(tuple(terms), why)


def none(why: str) -> Row:
    return Row((), why)


# Groups § 8.1 leaves out on purpose, with the reason; the test reads these so a covered group is never dropped
# by accident.
EXCLUDED_LAW_GROUPS = {
    "lawgroup_trade_policy": "Read from the market (§ 8.1's first bullet): Task 2's hand-written values.",
}

LAW_TABLE = {
    "lawgroup_economic_system": {
        "law_traditionalism": row(
            feature("manufacturing", -1),
            why=(
                "Investment pool efficiency -50% for capitalists, shopkeepers and four more classes, and +25% "
                "self-investment: the money that builds industry stays home. The modifiers hit every class's "
                "investment alike, a case for every firm at -1, left at the owner's reading (manufacturers)."
            ),
        ),
        "law_interventionism": row(
            feature("subsidized", 1),
            why=(
                "Airports and highways require subsidies (country_building_*_require_subsidies_bool), so their "
                "owners are carried by the state. Its other lines (charters, dividend reinvestment) touch no sector."
            ),
        ),
        "law_agrarianism": row(
            feature("manufacturing", -1), feature("agriculture", 1), feature("plantation", 1),
            why=(
                "Aristocrats', clergy's and farmers' investment pool efficiency +50%, capitalists' -25%: money "
                "moves from industry to the land."
            ),
        ),
        "law_industry_banned": row(
            feature("manufacturing", -1), feature("rm_industry_banned", -2),
            feature("agriculture", 1), feature("plantation", 1),
            why=(
                "on_activate removes chemical, synthetics, steel, power, motor, automotive, electrics and munitions "
                "plants from every state (-2 for a firm with one); agriculture and plantations throughput +10%."
            ),
        ),
        "law_extraction_economy": row(
            feature("manufacturing", -1), feature("rm_extraction_economy", -2),
            feature("extraction", 1), feature("agriculture", 1), feature("plantation", 1),
            why=(
                "on_activate removes the same industries as Industry Banned but power plants; extraction, "
                "agriculture and plantations throughput +10%. Its can_enact needs a subject (the open-law check "
                "mirrors it)."
            ),
        ),
        "law_laissez_faire": row(
            every(1),
            why=(
                "Capitalists' and shopkeepers' investment pool efficiency +25%, nationalization disabled, "
                "privatization forced. It also forbids monopolies (country_forbid_monopoly_bool), which the trust "
                "chain (Task 4) reads on its own."
            ),
        ),
        "law_cooperative_ownership": row(
            every(-2),
            why="Ends private ownership (owner, § 8.1): worker dividends +75%, every private group collectivizable.",
        ),
        "law_command_economy": row(
            every(-2),
            why="Ends private ownership (owner, § 8.1): seizes the investment pool and disables it.",
        ),
    },
    "lawgroup_labor_rights": {
        "law_no_workers_rights": row(
            labor(1),
            why="Wage pressure -0.002: the restrictive law, favoring firms by staffing.",
        ),
        "law_regulatory_bodies": row(
            labor(-0.5),
            why="Wage pressure +0.002 and the workplace safety institution: protective, half Worker Protections.",
        ),
        "law_worker_protections": row(
            labor(-1),
            why="Minimum wage +10% (institution), wage pressure +0.004: the most protective.",
        ),
    },
    "lawgroup_childrens_rights": {
        "law_child_labor_allowed": row(
            labor(1),
            why="Child labor participation +0.3 and dependents' wages +30%: more hands for the same pay.",
        ),
        "law_restricted_child_labor": none(
            "The middle law: child labor participation +0.1 still. Neither side of the protective line; a firm "
            "under it seeks Child Labor Allowed through the open-law reading instead."
        ),
        "law_compulsory_primary_school": row(
            labor(-0.5),
            why=(
                "No child labor participation at all (only schools' max investment +2): protective, but a smaller "
                "change to staffing than the wage laws."
            ),
        ),
    },
    "lawgroup_labour_associations": {
        "law_guild_system": row(
            labor(0.5), feature("collectivizable", -1),
            why=(
                "Strikebreaking legal and open (§ 9.2) and +25% self-investment, but manufacturing, extraction, "
                "power, private infrastructure and arts collectivizable at 0.25 and shopkeepers +25% power."
            ),
        ),
        "law_combination_acts": row(
            labor(1),
            why="Trade Unions -25% political strength, wage pressure -0.002: the most restrictive.",
        ),
        "law_anti_strike_laws": row(
            labor(0.5),
            why="Trade Unions -10% political strength, wage pressure -0.002: restrictive, milder.",
        ),
        "law_right_to_associate": row(
            labor(-0.5),
            why="Trade Unions +10% political strength, wage pressure +0.002: strikebreaking goes secret (§ 9.2).",
        ),
        "law_corporatized_unions": row(
            labor(-0.5),
            why=(
                "Wage pressure +0.004 and no strikebreaking: the state stands between firm and workers (§ 9.2). "
                "Radicals from falling SoL +15% cut both ways."
            ),
        ),
        "law_factory_councils": row(
            labor(-1), feature("collectivizable", -2),
            why=(
                "Trade Unions +25% political strength, wage pressure +0.005, and every private group collectivizable "
                "at 0.5. Its can_enact needs a revolutionary country (the open-law check mirrors it)."
            ),
        ),
    },
    "lawgroup_ministry_of_labor": {
        "law_no_ministry_of_labor": none("No institution: nothing in it touches a firm."),
        "law_pro_labor_ministry_of_labor": row(
            labor(-0.5),
            why="Worker dividends +1% and political strength from wealth -5% a level of the institution.",
        ),
        "law_pro_capital_ministry_of_labor": row(
            labor(0.5),
            why="Minimum wage -5% and labor participation up a level of the institution (§ 8.1: a Pro-Capital ministry).",
        ),
    },
    "lawgroup_antitrust": {
        "law_guilds_chartered_monopolies": row(
            when("big", 2), when("small", -1),
            why=(
                "A cartel legal and open, monopoly charters may be petitioned for (§ 6.2): the big firm's law. "
                "Company throughput -10% with no construction help, which the small firm pays for nothing."
            ),
        ),
        "law_freedom_of_contract": row(
            when("big", 2), when("small", 1),
            why=(
                "A cartel legal and open, growing 15 a year (§ 6.2); company construction efficiency +40% for every "
                "firm, against company throughput -10%."
            ),
        ),
        "law_trust_busting": row(
            when("big", -2), when("small", 1),
            why=(
                "Monopolies forbidden and a cartel illegal (§ 6.2); company throughput +10% and one more company "
                "slot, so the small firm gains while the big one is cut down."
            ),
        ),
        "law_regulated_utilities": row(
            when("big", -1), when(("big", "utility"), -1), when("small", 1),
            why=(
                "A cartel illegal in infrastructure and utilities and capped at 40 elsewhere (§ 6.2); company "
                "throughput +10%, government dividends +10%."
            ),
        ),
        "law_dirigisme": row(
            when(("big", "favored"), 2), when(("small", "favored"), 1),
            when(("big", "not_favored"), -2), when(("small", "not_favored"), -1),
            why=(
                "A cartel legal for a Favored firm only, others as under Antitrust Enforcement (§ 6.2); government "
                "dividends +10% taken from every company, export advantage +10%."
            ),
        ),
        "law_command_cooperative_economy": row(
            every(-2),
            why=(
                "No cartel and Dominance scores 0 (§ 6.2); company construction efficiency -40%; the step that "
                "unlocks Command Economy and Cooperative Ownership."
            ),
        ),
    },
    "lawgroup_resource_transition": {
        "law_unrestricted_extraction": none(
            "The default: it bans and retires nothing. § 8.1 gives the group no favors in this slice; a fossil "
            "firm under the other two seeks it through their burden (the law in force)."
        ),
        "law_fossil_expansion_moratorium": row(
            feature("fossil", -1),
            why="No new coal mines, oil rigs or power plants (rt_fossil_construction_allowed_here).",
        ),
        "law_managed_fossil_phaseout": row(
            feature("fossil", -2),
            why=(
                "The moratorium, and the retirement programmes remove whole buildings, smallest first. Its "
                "can_enact needs the environment ministry funded (the open-law check mirrors it)."
            ),
        ),
    },
    "lawgroup_automation_policy": {
        "law_unrestricted_automation": row(
            feature("automatable", 1),
            why="Every robotic or AI-managed method open and nothing taken from what it earns (§ 8.1).",
        ),
        "law_robot_tax": row(
            feature("automatable", -1),
            why="Tax collection +10% and capitalists' investment contribution -0.05, scaled by the automated share.",
        ),
        "law_human_labor_quotas": row(
            feature("automatable", -2),
            why="Withdraws the 44 marked methods (disallowing_laws): the automated firm loses its best methods.",
        ),
        "law_automation_dividend": row(
            feature("automatable", -1),
            why=(
                "Capitalists' investment contribution -0.10 at full automation (te_automation_dividend). § 8.1's "
                "first reading named only the tax and the quotas; the dividend takes twice the tax's share."
            ),
        ),
    },
    "lawgroup_intellectual_property": {
        "law_no_ip_protection": row(
            when("lab", -1), when("behind_no_lab", 1),
            why=(
                "Innovation +5%, economic covert defense -10: what a firm invents, its neighbors copy (§ 10.3). "
                "The firm with a laboratory loses its edge; the firm behind with none copies freely."
            ),
        ),
        "law_creative_commons": row(
            when("lab", -1), when("behind_no_lab", 1),
            why="Research counts a quarter more, no throughput edge (§ 10.3); art academies +10%.",
        ),
        "law_traditional_ip_protection": row(
            when("lab", 1),
            why="Innovation -10%, tech spread -10%, capitalists' investment contribution +5%: inventions are kept.",
        ),
        "law_strict_ip_protection": row(
            when("lab", 1), when("patent_pool", 1), when("behind_no_lab", -1),
            why=(
                "Tech spread -10%, economic covert defense +10, capitalists' contribution +10%; the throughput edge "
                "doubles and a laboratory at 80 may form a patent pool (§ 10.3). The firm behind with no "
                "laboratory is locked out."
            ),
        ),
        "law_open_source_innovation": row(
            when("lab", -1), when("behind_no_lab", 1),
            why="Innovation and tech spread +10%, worker dividends +5%: no throughput edge (§ 10.3).",
        ),
        "law_state_intellectual_property": row(
            every(-1), when("lab", -1),
            why=(
                "Capitalists' investment contribution -10% and Industrialists -5% political strength; a "
                "laboratory's research goes to the state's choice (§ 10.3)."
            ),
        ),
    },
    "lawgroup_financial_regulation": {
        "law_unregulated_banking": row(
            feature("financial", 2),
            why="Urban centers +25% throughput, banking crash chance +25%, no capital controls: the loosest.",
        ),
        "law_free_mutual_banking": row(
            feature("financial", 1),
            why="Urban centers +10%, farmers' investment contribution +5%: loose.",
        ),
        "law_universal_banking_light_prudence": row(
            feature("financial", 1),
            why="Urban centers +20%, random momentum +10%: loose.",
        ),
        "law_prudential_narrow_banking": row(
            feature("financial", -1),
            why="Capitalists' investment pool efficiency -10%, momentum -60%, crash chance -50%: strict.",
        ),
        "law_directed_credit_development_banks": row(
            feature("financial", -1),
            why="Credit directed to chosen sectors (country_directed_credit_sectors_add): banks lend where told.",
        ),
        "law_state_owned_banking": row(
            feature("financial", -2),
            why="Capitalists' investment contribution -10%, government dividends +10%: the state owns the banks.",
        ),
        "law_central_bank_independence": none(
            "Governs the central bank (inflation anchoring, credit standing), not the private banks' business: "
            "nothing in it reaches a firm's buildings or the investment pool."
        ),
    },
    "lawgroup_electoral_finance": {
        "law_no_campaign_finance_laws": none(
            "No elections to buy: it disallows every voting law, so campaign money has nothing to act on."
        ),
        "law_unregulated_donations": row(
            campaign(2),
            why="Capitalists +20 and aristocrats +10 voting power: money buys votes outright.",
        ),
        "law_donation_limits": row(
            campaign(-1),
            why="Political strength from wealth -10% and the classes' voting power evened out.",
        ),
        "law_publicly_funded_elections": row(
            campaign(-2),
            why="Political strength from wealth -25%: private campaign money counts for least.",
        ),
    },
}

# The open-law reading (could the country move to this law?) is `law_is_available` on the country's law
# object. Whether that reads a law's can_enact is unverified, so a covered law with a can_enact block gets its
# trigger mirrored here, read beside it. test_gen_private_actors.py fails on a covered law with a can_enact and
# no line, so a new gate can't be missed.
CAN_ENACT_MIRROR = {
    "law_extraction_economy": "is_subject = yes",
    "law_command_economy": "te_cred_leads_consortium = no",
    "law_factory_councils": "is_revolutionary = yes",
    "law_managed_fossil_phaseout": "rt_ministry_funded_for_phaseout = yes",
}

# ---------------------------------------------------------------------------
# Temperament (§ 5.3): what the executive's personality traits and ideology say about the firm
# ---------------------------------------------------------------------------

# Four axes, each -1 to +1 and 0 with no executive; the generator writes te_pa_gen_temper_<axis> (company scope,
# read through `executive ?=`), and Task 2's turn stores them as te_pa_bold_t, te_pa_force, te_pa_patern and
# te_pa_attach. Attachment's other half, the executive's culture (a primary culture of the home country or
# not), is read by the turn, which knows the home country. First readings (2026-11-28) of the traits' and
# ideologies' names and descriptions, owner § 5.3's words where it gives them.
TEMPERAMENT_AXES = {
    "bold": "Boldness (§ 7.5): raised by ambitious and reckless traits, lowered by cautious ones.",
    "force": "Taste for force: a jingoist petitions for armed protection; a pacifist or humanitarian bribes or leaves.",
    "patern": (
        "Paternalism: a reforming, humanitarian or religious executive answers labor trouble with welfare; a "
        "market-liberal or authoritarian one breaks strikes (§ 9.2)."
    ),
    "attach": "Attachment to home, the ideology's part: lowered by a cosmopolitan or radical ideology.",
}

# Personality traits (vanilla's `type = personality`; the mod adds none, and INJECTs only reckless and cautious
# for the banking cycle). Skill and condition traits say what a character can do or suffers, not how it runs a
# firm, and are not read. test_gen_private_actors.py fails on a personality trait in neither table.
TRAIT_TEMPERAMENT = {
    "ambitious": {"bold": 1},
    "reckless": {"bold": 1},
    "brave": {"bold": 0.5},
    "arrogant": {"bold": 0.5},
    "imperious": {"bold": 0.5, "force": 0.5},
    "innovative": {"bold": 0.5},
    "cautious": {"bold": -1},
    "reserved": {"bold": -0.5},
    "meticulous": {"bold": -0.5},
    "compliant": {"bold": -0.5, "force": -0.5},
    "wrathful": {"force": 0.5},
    "cruel": {"force": 0.5, "patern": -0.5},
    "ruthless": {"force": 0.5, "patern": -0.5},
    "tactful": {"force": -0.5},
    "honorable": {"patern": 0.5},
    "pious": {"patern": 0.5},
    "bigoted": {"attach": 0.5},
}

NEUTRAL_TRAITS = {
    "aesthete": "Taste in art: nothing about risk, force, workers or home.",
    "charismatic": "Charm wins people over; it says nothing about which way.",
    "direct": "Plain speaking, not a taste for force.",
    "hedonist": "Pleasure-seeking: neither bold nor careful in business.",
    "imposing": "Presence, not policy.",
    "persistent": "Holds a course; which course is the rest of the temperament's.",
    "romantic": "Sentiment, with no lean toward risk or force.",
    "scandalous": "A reputation, read by nothing here.",
    "tolerant": "Tolerance of others is not care for one's workers, and not a cosmopolitan creed.",
    "trait_child": "A child holds no executive post.",
}

# Personality traits named for one historical character: a story, not a temperament.
NEUTRAL_TRAIT_PREFIXES = ("special_character_",)

# Character ideologies (`character_ideology = yes`, vanilla's and the mod's). test_gen_private_actors.py fails on
# one in neither table.
IDEOLOGY_TEMPERAMENT = {
    "ideology_jingoist_leader": {"force": 1, "attach": 0.5},
    "ideology_pacifist": {"force": -1},
    "ideology_humanitarian": {"force": -0.5, "patern": 1},
    "ideology_humanitarian_royalist": {"force": -0.5, "patern": 1},
    "ideology_reformer": {"patern": 1},
    "ideology_theocrat": {"patern": 1},
    "ideology_integralist": {"patern": 0.5, "attach": 0.5},
    "ideology_feminist": {"patern": 0.5},
    "ideology_abolitionist": {"patern": 0.5},
    "ideology_land_reformer": {"patern": 0.5},
    "ideology_state_socialist": {"patern": 0.5},
    "ideology_corporatist_leader": {"patern": 0.5},
    "ideology_environmentalists": {"patern": 0.5},
    "ideology_market_liberal": {"patern": -1},
    "ideology_authoritarian": {"patern": -1, "force": 0.5},
    "ideology_slaver": {"patern": -1, "force": 0.5},
    "ideology_corporate": {"patern": -0.5, "bold": 0.5},
    "ideology_fascist": {"force": 1, "attach": 1, "patern": -0.5},
    "ideology_ethno_nationalist": {"attach": 1, "force": 0.5},
    "ideology_shojoi": {"attach": 1, "force": 0.5},
    "ideology_bonapartist": {"force": 0.5, "attach": 0.5},
    "ideology_vanguardist": {"force": 0.5, "attach": -0.5},
    "ideology_protectionist": {"attach": 0.5},
    "ideology_sovereignist_leader": {"attach": 0.5},
    "ideology_anti_colonialist_leader": {"attach": 0.5},
    "ideology_mitogaku": {"attach": 0.5},
    "ideology_radical": {"attach": -1},
    "ideology_multicultural": {"attach": -1},
    "ideology_multicultural_inclusive": {"attach": -1},
    "ideology_communist_leader": {"attach": -0.5},
    "ideology_anarchist": {"attach": -0.5},
    "ideology_modernizer_leader": {"bold": 0.5},
    "ideology_optimist_transhumanist": {"bold": 0.5},
}

NEUTRAL_IDEOLOGIES = {
    "ideology_royalist": "Loyalty to a crown: a view of the state, not of the firm's risks, workers or home.",
    "ideology_legitimist": "A dynastic claim, as the royalist's.",
    "ideology_orleanist": "A dynastic claim, as the royalist's.",
    "ideology_carlist": "A dynastic claim, as the royalist's.",
    "ideology_carlist_2": "A dynastic claim, as the royalist's.",
    "ideology_miguelist": "A dynastic claim, as the royalist's.",
    "ideology_miguelist_2": "A dynastic claim, as the royalist's.",
    "ideology_traditionalist": "Custom in law and religion; no lean the four axes read.",
    "ideology_traditionalist_minoritarian": "As the traditionalist, for a minority's ways.",
    "ideology_republican_leader": "A form of government, not a way of running a business.",
    "ideology_jacksonian_democrat": "A form of government and its patronage, read by Task 5's politics, not here.",
    "ideology_liberal_leader": "Constitutional liberalism: a view of the state, not of the workforce.",
    "ideology_moderate": "The middle of the road on every axis.",
    "ideology_positivist": "Order and progress through science: neither bold nor careful in itself.",
    "ideology_utilitarian_leader": "The greatest good: no fixed lean on these axes.",
    "ideology_ilustrado_leader": "An educated reformist elite's nationalism, without a lean these axes read.",
    "ideology_despotic_utopian": "A dream of a perfect order, not a business temperament.",
    "ideology_utopian": "A dream of a perfect order, not a business temperament.",
    "ideology_nihilist": "Rejects every creed, so it gives none of these leans.",
    "ideology_luddite": "Against machines; the law table's automation terms carry that, not temperament.",
    "ideology_child": "A child holds no executive post.",
}

# ---------------------------------------------------------------------------
# Names in text
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NameLoc:
    key: str        # the customizable localization's key
    kind: str       # "good" or "law"
    variable: str   # the script container variable holding the index


# A good's or a law's name from the index a firm's readings carry (te_pa_g_*_good, te_pa_g_law_*_law), read
# from a script container that holds a copy of it (the firm's row, plan § Rows). One entry a variable: a task
# that copies another index to a container (a ledger line, the firm's detail) adds its line here and reruns
# the generator.
NAME_LOCS = (
    NameLoc("te_pa_row_reason_good", "good", "te_pa_r_reason_good"),
    NameLoc("te_pa_row_reason_law", "law", "te_pa_r_reason_law"),
    # the firm detail's law being enacted (Task 3's tab)
    NameLoc("te_pa_row_enacting_law", "law", "te_pa_r_enacting_law"),
)
