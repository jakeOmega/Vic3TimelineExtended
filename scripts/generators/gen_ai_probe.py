"""Generate the AI telemetry probe: what every AI country has, does and decides, logged to debug.log.

TEMPORARY (2026-11-15). The probe exists to show where the game's AI falls short in this mod, in the owner's order
of importance: economic growth, technological advancement, legal modernization, military modernization, expansion.
It is inert in a played game. It arms itself in a game with no human player (an observer or unattended run), or
from the console with `event te_debug_ai_probe.1` (`.2` disarms). Remove the four generated files, this generator,
`scripts/analysis/ai_probe_report.py`, `ai_probe_compare.py`, `ai_probe_key.json`, `test_ai_probe.py` and
`test_ai_probe_compare.py` once the AI work it serves is done.

    python3 scripts/generators/gen_ai_probe.py            write the files (only those whose content changed)
    python3 scripts/generators/gen_ai_probe.py --check    exit 1 if a file on disk differs from the generator's

It is a one-shot generator, not a post-load regenerator: a law, technology or building group added later does not
break anything, it only goes unread until the next run of this script, so run it before a probe run.

WHAT IT WRITES
  common/script_values/te_ai_probe_values.txt      one read-wrapper per logged field (`te_aip_<key>`)
  common/scripted_effects/te_ai_probe_effects.txt  arming, the per-country tick, the snapshot's lines, the counters
  common/on_actions/te_ai_probe_on_actions.txt     the monthly pulses and the decision hooks
  events/te_debug_ai_probe_events.txt              the two hidden console events
  scripts/analysis/ai_probe_key.json               how to decode the indexed fields (laws, strategies, techs)

WHAT THE LOG HOLDS (every line starts `TE_AIP `; `scripts/analysis/ai_probe_report.py` reads them)
  ARM v=<version>              once, when the probe arms; a `CANARY` line per data function follows (below)
  K <k> y=<year> ...           each month: the tick `k` (months since arming) against the game date
  S <group> <TAG> <id> <k> key=value ...
                               the yearly snapshot of one country, a line per field group. A country's snapshot
                               month is its id modulo 12, so a twelfth of the world reports each month and no tick
                               writes more than the log's rotation can hold. `id` is a serial the probe gives each
                               country object (two objects can share a tag in a civil war). From version 3 the
                               month is a calendar month (0 = January): a country reports at its first monthly
                               pulse in that month or after it, once each calendar year (te_aip_country_tick).
                               Versions 1 and 2 counted twelve of the country's pulses, which are 30 days apart,
                               so a report drifted five days earlier a year and every six years or so fell twice
                               in one calendar year (January and December). Version 2 adds O2
                               (manufacturing staffing without the Construction Sector, then the sector itself:
                               staffing, subsidies, methods, the construction good's price and orders, and the
                               Construction Sites' staffing), J1 (each institution's
                               maximum investment), R1 (the army by unit type) and H1 (specific technologies), and
                               the construction purchase's remaining terms to C2 and `n_law_set` to N2.
  X <n> <TAG> <id> <k> ...     with each snapshot: figures only the interface's data functions give (the
                               budget's lines, construction used and unused, innovation against its cap, the
                               technology being researched and the law being enacted by name). Each is also
                               printed alone at arming (`CANARY <name> v=...`): a data function the engine does
                               not have drops its whole line, and the canary shows which. All 21 printed in the
                               first run (2026-11-15).
  E <event> <TAG> <id> <k> ... a decision as it happens: a law enactment started, passed, failed or ended, a
                               default and its end, a diplomatic play. From version 2 a law's end says how it ended
                               (`how`: ai_probe_key.json, law_end_how) and a play gives its type and both sides'
                               ranks.
  W <k> y=<year> ...           from version 2, once a year (the month the probe armed in, and every twelfth after):
                               the world outside the AI countries, which no snapshot covers (decentralized nations
                               and the states they hold). Version 2 counted them with `every_country`, which does
                               not reach a decentralized nation, so its `dn` and `dn_states` read 0 in every line;
                               version 3 counts them with `every_decentralized_country` and adds two independent
                               reads of the same land: every state in the world, and the states of every country
                               `every_country` reaches (WORLD_FIELDS).
Version 3 also adds the banking cycle to C2 (its phase, `finance_cycle_value`, its momentum, a crash in the last
365 days; BANK_PHASES) and the months in a panic or downturn to the counters (`n_bank_down`).
Version 4 (2026-11-16) adds what the analysis of the first late-game run (1925 to 1948) could not see (#1877): H2,
the technologies that gate electricity and radios (TECH_FLAGS_4); P1 and P2 (version_4_fields): electrification
(states with a power plant, power levels queued, Electricity made, bought and its price, urban centres by street
lighting, the radios market), the construction queue by kind, the construction cost scaling, what the bureaucracy's
modifiers add and multiply, the workforce's slack, and a census of the army's battalions (te_aip_unit_census: new
since the last report, of another type than at the last report; retired in version 6); X7 and X8, the institutions' bureaucracy cost and
the strata's standard of living (DATA_FUNCTIONS); and the W line's three game rules (RULES), so a log says which
setting its fields ran under. `bt_company_headquarter` reads the headquarters' group from version 4 (BUILDING_TYPE_READS).
Version 5 (#1877) adds to C2 the interest rate the construction purchase reads (`rate`, the rate paid, and
`rate_base`, the world reference rate it is read against), what the rate asks of the purchase (`cm_reserve`, the
reserve it asks the country to keep, and `cm_credit`, the debt it allows, each a share of its limit), `cm_pass`,
the levels the AI construction pass has queued for the country since the game began (te_ai_build_pass_effects.txt),
and what its railway entry reads: `inf_short_states`, the states whose infrastructure is short of its usage, and
`inf_short`, their shortfall in all, which count unincorporated states and any shortfall; and, at the end of B2,
`rail_sites`, the states the entry would act on (te_ai_build_pass_railway_site: incorporated, short by more than
its margin). C2 is full, and a line of its own would take a snapshot past the five lines version 4 allowed it (the
log rotates every 512 KB), so it joins the line with room nearest in kind: the country's buildings by type.
Version 6 (#2090) takes out the army census: a combat unit holds no variables (its canary, `TE_AIP CANARY unit_vars`,
read v=0 in the first game it ran in, 2026-11-26: "This scope doesn't support variables"), so the battalions could not
be marked and every u_* field read 0. Its six fields leave the end of P2 (RETIRED_TAIL), with the canary, the
battalion's type index and the marks; the net change in irregulars (report table 4b) still reads from the R line.
Every figure in an S line comes through a script value (`[THIS.ScriptValue('x')|n]`), the one accessor form the
mod has always seen print (docs/guides/scripting_best_practices.md, `debug_log` Loc-String Templating Limitations).

Counters (`n_*` in the N group) are flows since the country's last snapshot: buildings built and expanded by
class, production-method changes, technologies acquired, laws started, plays started, companies founded.

OLD LOGS. A version-1 log (the first long run, 2026-11-16) must go on parsing with this version's key, so a new
field or line is only ever added: no line is renamed or renumbered, a field joins the end of its group, and a
positional line (`POSITIONAL`) never takes another field, since its lines are read by position. New positional
fields go on a line of their own: a group of their own, or a later part of the group that starts a new line
(version 4's H2, `field_groups` giving H twice). A field is retired only from the end of a positional line, and the
key names it (`retired_tail`, from RETIRED_TAIL), so an older log's longer line still reads: the parser drops that
many values from its end (version 6's army census).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

VERSION = 6
PREFIX = "te_aip_"
FIELDS_PER_LINE = 15
POSITIONAL_PER_LINE = 22
# Groups whose lines carry bare values, semicolon-separated, in the order ai_probe_key.json gives (`lines`): the bulk
# of a snapshot, at a third of the bytes of key=value. J, R and H are version 2's, P version 4's.
POSITIONAL = ("L", "T", "I", "G", "J", "R", "H", "P")
# Version 2's positional groups each fit one line (test_ai_probe.py holds every line under 1,500 characters);
# version 1's keep POSITIONAL_PER_LINE, so their lines read as they did. P's fields have long names, so 18 a line.
LINE_SIZE = {"J": 30, "R": 30, "H": 30, "P": 18}
# The snapshot lines each version added, so that `check` expects of a log only the lines its version printed.
# A line a later version adds goes under that version (test_ai_probe.py fails on a line under none).
LINES_ADDED = {
    1: ["A1", "A2", "F1", "F2", "F3", "U1", "U2", "C1", "C2", "O1", "M1", "Y1", "L1", "L2", "L3", "T1", "T2",
        "I1", "I2", "G1", "G2", "G3", "B1", "B2", "N1", "N2"],
    2: ["O2", "J1", "R1", "H1"],
    3: [],          # version 3 added fields to C2 and N2, the W line's fields, and the calendar schedule
    4: ["H2", "P1", "P2"],
    5: [],          # version 5 added fields to C2 (the rate the purchase reads, and the AI construction pass) and B2
    6: [],          # version 6 took the army census's six fields off the end of P2 (RETIRED_TAIL)
}

VALUES_FILE = "common/script_values/te_ai_probe_values.txt"
EFFECTS_FILE = "common/scripted_effects/te_ai_probe_effects.txt"
ON_ACTIONS_FILE = "common/on_actions/te_ai_probe_on_actions.txt"
EVENTS_FILE = "events/te_debug_ai_probe_events.txt"
KEY_FILE = "scripts/analysis/ai_probe_key.json"

HEADER = (
    "# AUTO-GENERATED by scripts/generators/gen_ai_probe.py. Do not edit manually.\n"
    "# TEMPORARY (2026-11-15): the AI telemetry probe. Inert in a played game; it arms itself in a game with no\n"
    "# human player, or from the console with `event te_debug_ai_probe.1` (`.2` disarms). What it logs and why:\n"
    "# the generator's docstring and docs/testing/ai-probe-runbook.md. Remove with the generator.\n"
)

# AI strategies are not in vanilla_parsed, so their names are listed here (vanilla 1.15.1's
# common/ai_strategies/01_admin, 02_diplomatic, 02_subject_diplomatic and 03_political files, plus the mod's two).
# `test_ai_probe.py` holds the list to the game's files where a game is installed.
STRATEGIES = {
    "admin": [
        "ai_strategy_agricultural_expansion", "ai_strategy_resource_expansion", "ai_strategy_industrial_expansion",
        "ai_strategy_plantation_economy", "ai_strategy_placate_population", "ai_strategy_colonial_extraction",
        "ai_strategy_montenegro_admin",
    ],
    "political": [
        "ai_strategy_conservative_agenda", "ai_strategy_reactionary_agenda", "ai_strategy_progressive_agenda",
        "ai_strategy_egalitarian_agenda", "ai_strategy_nationalist_agenda", "ai_strategy_consolidation_agenda",
        "ai_strategy_confrontation_agenda", "ai_strategy_maintain_mandate_of_heaven", "ai_strategy_meiji_restoration",
        "ai_strategy_tanzimat_reforms", "ai_strategy_great_reforms",
    ],
    "diplomatic": [
        "ai_strategy_maintain_power_balance", "ai_strategy_territorial_expansion", "ai_strategy_colonial_expansion",
        "ai_strategy_economic_imperialism", "ai_strategy_armed_isolationism", "ai_strategy_anti_imperialism",
        "ai_strategy_restore_natural_borders", "ai_strategy_prussia_of_the_balkans",
        "ai_strategy_socialism_in_one_country", "ai_strategy_world_revolution", "ai_strategy_unify_china",
        "ai_strategy_unify_ethiopia", "ai_strategy_unify_germany", "ai_strategy_unify_italy",
        "ai_strategy_subject_maintain_autonomy", "ai_strategy_subject_overlord_compliance",
        "ai_strategy_subject_strengthen_self", "ai_strategy_subject_break_free", "ai_strategy_irredentist",
        "ai_strategy_un_mandate",
    ],
}

COUNTRY_TYPES = ["recognized", "unrecognized", "colonial", "decentralized", "company"]
RANKS = ["great_power", "major_power", "minor_power", "insignificant_power", "unrecognized_major_power",
         "unrecognized_regional_power", "unrecognized_power", "decentralized_power"]

# Building types logged by level beside the groups, where one type is the thing to watch.
BUILDING_TYPES = [
    "building_construction_sector", "building_government_administration", "building_university",
    "building_barrack", "building_conscription_center", "building_military_base", "building_shipyard",
    "building_naval_administration", "building_naval_logistics_center", "building_port", "building_railway",
    "building_highway", "building_airport", "building_network_infrastructure", "building_power_plant",
    "building_hydro_plant", "building_nuclear_plant", "building_renewable_energy_plant", "building_fusion_plant",
    "building_urban_center", "building_trade_center", "building_art_academy", "building_financial_district",
    "building_manor_house", "building_company_headquarter", "building_public_housing", "building_software_industry",
    "building_electronic_components_and_semiconductor_industry",
]
# A building type logged by its group's levels instead. The engine makes a building type of its own for each company
# type (building_company_basic_fabrics, ...) from vanilla's headquarters template, so the template type is no
# headquarters in a game: `bt_company_headquarter` read 0 in every snapshot of versions 1 to 3 while
# `bg_company_headquarter` (G2) read in every snapshot with a company (scripting_best_practices.md, A Company's
# Headquarters Is a Building Type of Its Own). From version 4 the field reads the group, the same figure as G2's, so
# that the B line keeps its fields and old logs read as they did.
BUILDING_TYPE_READS = {"building_company_headquarter": "bg_company_headquarter"}

# The mod's budget mirrors: each system's script-charged expense or income, as the Budget panel itemizes it. The
# 2026-11-15 save study found script expenses at 2.5% of AI GDP and could name a third of them.
BUDGET_EXPENSES = ["banking", "climate", "colonial", "covert", "culture", "drugs", "energy_industry", "family",
                   "nuclear", "nuclear_taboo", "pensions", "space", "un"]
BUDGET_INCOMES = ["pension_reform", "reserve", "tax_code", "un", "war_tax"]

# Building classes whose staffing and retooling are summed (levels in buildings under half staffed, levels
# carrying the retooling modifier). The same study read AI manufacturing at 48% staffed and 46% retooling in 1958.
STAFFING_CLASSES = [("mfg", "bg_manufacturing"), ("infra", "bg_infrastructure"), ("power", "bg_power"),
                    ("mine", "bg_mining")]
# The rt_* fields (levels carrying pm_retooling) read 0 by design under three of free_market_construction_rule's five
# settings: no_retooling and no_maintenance remove the modifier from every building as the engine applies it, and
# no_ai_retooling from every AI-owned one (te_remove_waived_pm_retooling: at the production-method change, a day
# later, and in a sweep four times a month), so a yearly snapshot finds none. Every run before version 4 was made
# under no_retooling (the owner's last lobby rules, 2026-11-16), which is why rt_* read 0 in all of them; the save
# study's 36-52% retooling was of a game under `enabled`. Version 4 logs the setting on the W line (RULES).
RETOOLING_WAIVED = ["free_market_construction_no_ai_retooling", "free_market_construction_no_retooling",
                    "free_market_construction_no_maintenance"]

# Production methods a modern economy should have left: (key, building type, method).
STALE_METHODS = [
    ("uc_no_light", "building_urban_center", "pm_no_street_lighting"),
    ("uc_no_transit", "building_urban_center", "pm_no_public_transport"),
    ("uc_stalls", "building_urban_center", "pm_market_stalls"),
    ("ga_simple", "building_government_administration", "pm_simple_organization"),
    ("uni_scholastic", "building_university", "pm_scholastic_education"),
]

# The classes a finished building is counted under (the first group that matches).
BUILT_CLASSES = [
    ("gov", ["bg_government"]),
    ("mil", ["bg_military"]),
    ("infra", ["bg_infrastructure", "bg_private_infrastructure"]),
    ("power", ["bg_power"]),
    ("ind", ["bg_manufacturing"]),
    ("res", ["bg_mining", "bg_logging", "bg_fishing", "bg_whaling", "bg_oil_extraction", "bg_rubber"]),
    ("agri", ["bg_agriculture", "bg_plantations", "bg_ranching"]),
]

# Event counters kept on the country between two of its snapshots. `law_set` (version 2) counts a law activated
# other than by a passed enactment: by script (the mod's law-consistency sweep, an event), a revolution, or a new
# country's setup. `bank_down` (version 3) counts the country's monthly pulses with its banking cycle in a panic or
# a downturn (banking_cycle_is_recession), so that a crash between two snapshots shows.
COUNTERS = (
    ["built", "expanded"] + [f"built_{name}" for name, _ in BUILT_CLASSES]
    + ["pm", "tech", "law_start", "law_pass", "law_fail", "law_end", "default", "play", "war", "reform", "company",
       "colony", "inst_up", "inst_down", "law_set", "bank_down"]
)

# The banking cycle's phases (the C2 line's `bank_phase`, 1-based; 0 is no cycle running): the bands of
# finance_cycle_value that common/scripted_triggers/market_triggers.txt's banking_cycle_is_* triggers test (under
# 10, 25, 40, 60, 75, 88, then frenzy), which the journal entry's phase modifiers follow in every economy type.
# A cycle runs only once te_banking_cycle_running holds (the rule on, the entry held, the cycle started: a stock
# exchange and an Urban Center of level 5), so early in a game most countries read 0.
BANK_PHASES = ["panic", "downturn", "stagnation", "stable", "expansion", "boom", "frenzy"]

# How an enactment ended, the `how` of a law_end line (1-based). The engine has no hook for a cancellation, so
# the end hook reads what the pass and fail hooks marked just before it, and failing both, whether the law is still
# available. on_law_enactment_fail fires only when an enactment "fails by accumulating too many setbacks" (vanilla's
# 00_code_on_actions.txt), and in the first long run none of the 2,938 enactments that ended had more than 2 of the
# 3 setbacks a country may suffer (00_code_static_modifiers.txt: country_law_enactment_max_setbacks_add = 3): the
# 534 that ended unpassed were all stopped before a third, which is why the fail hook never fired.
LAW_END_HOW = [
    "passed",       # on_law_enactment_pass fired for it
    "failed",       # on_law_enactment_fail fired for it: the setbacks reached the country's maximum
    "cancelled",    # stopped with the law still available: by the AI, or by script
    "replaced",     # stopped with the law no longer available: a law set by script or a revolution barred it
                    # (vanilla's own on_law_activated hook cancels such an enactment)
]

# The tax and wage levels the F group's `tax_level`, `gov_wage` and `mil_wage` print, 0-based (the first long run
# printed 0 to 4 for tax and the military wage, medium the commonest).
LEVEL_NAMES = ["very_low", "low", "medium", "high", "very_high"]
LEVEL_FIELDS = ["tax_level", "gov_wage", "mil_wage"]

# Technologies logged one by one (the H line), for the gates the first run's analysis could only infer:
# Religious, Private and Public Schools; the era-3 society technologies vanilla's AI weights for Per-Capita
# taxation and Interventionism wait for; the era-2 alternative proposed for them and the Per-Capita unlock; the
# colonial laws, malaria and severe malaria; Professional Army. The unlocking technology of every unit type the R
# line names follows them (`unit_techs`). The generator stops on a key no file defines.
TECH_FLAGS = [
    "rationalism", "academia", "empiricism",
    "civilizing_mission", "human_rights", "pan-nationalism",
    "nationalism", "currency_standards",
    "colonization", "quinine", "malaria_prevention",
    "military_drill",
]

# The army by unit type (the R line): each type of these groups up to this tier (the era of its unlocking
# technology) by its share of the army, then sums for what is past it, so the shares add up to the whole army.
UNIT_LINE_GROUPS = ["combat_unit_group_infantry", "combat_unit_group_artillery", "combat_unit_group_cavalry"]
UNIT_LINE_MAX_TIER = 6
UNIT_SUM_GROUPS = [("u_tanks", "combat_unit_group_tanks"), ("u_marines", "combat_unit_group_marines"),
                   ("u_air", "combat_unit_group_aircraft")]

# The Construction Sector itself (version 2, the end of the O group). The first long run's analysis found that in
# the 20 largest economies the manufacturing levels under half staffed were almost exactly the Construction
# Sector's levels (Great Britain 1836: 80 against 82), while the construction good sold at 1.3 to 1.5 times its
# base price; vanilla's AI expands no building under PRODUCTION_BUILDING_LOW_EMPLOYMENT_THRESHOLD (00_ai.txt: 0.8,
# "unless those buildings hired last week"). These fields measure the sector where that was an inference: its
# staffing against both thresholds, its staffed levels (level times occupancy, so the report divides by its levels
# for the mean), its subsidies, its levels by construction method, and the construction good in the country's
# market. The market-placed Construction Sites are a building of their own (te_construction_market_site, group
# te_construction_market_bg), so their staffing is logged apart: a site short of workers is not a sector short of
# them.
CONSTRUCTION_SECTOR = "building_construction_sector"
CONSTRUCTION_SITE = "te_construction_market_site"
CONSTRUCTION_GOOD = "construction"
AI_EXPANSION_STAFFING = 0.8
# The sector's methods named one by one (vanilla's four: wooden, iron frame, steel frame, arc-welded); the mod's
# later ones are summed (cs_pm_later), so the line keeps its length as methods are added.
CONSTRUCTION_METHODS_NAMED = 4

# --- Version 4: what the first late-game run's analysis could not see (#1877) ---------------------------------------
# The technologies behind electricity and radios (the H2 line): Electrical Generation unlocks the power plant and
# electric street lights (vanilla pm_electric_streetlights, which requires Electricity), Steam Turbine the power
# plant's coal-fired method, Radio the
# mod's radio factory (building_electrics_industry_radio) and Telephone vanilla's electrics industry, which also
# carries the radios group. The units the analysis found blocked (squad infantry, mechanized infantry, siege
# artillery, light tanks) are unlocked by nco_training, mobile_armor and defense_in_depth, already on H1 (unit_techs);
# what blocks them is their upkeep of radios, whose market P2 reads. The generator stops on a key no file defines.
TECH_FLAGS_4 = ["electrical_generation", "steam_turbine", "radio", "telephone"]
# The urban centre's street lighting (P1): the gas method, and the electric ones, which are every method after it in
# the group (vanilla's electric street lights and the mod's three later ones). With pm_no_street_lighting (O1's
# uc_no_light) the three add up to the urban centres' levels.
STREET_LIGHTING_GROUP = "pmg_street_lighting"
STREET_LIGHTING_NONE = "pm_no_street_lighting"
STREET_LIGHTING_GAS = "pm_gas_streetlights"
# The construction queue by kind (P1, P2): queued levels of each kind's buildings, counted in either queue (a
# building's levels once its queued constructions finish, less its levels: te_construction_market_building_queued_levels).
# Universities, administrations and military buildings are government buildings; infrastructure and power plants can
# be queued by either queue, so the report sets the first three against queue_gov and the last two against the whole
# queue.
QUEUE_KINDS = [
    ("q_power", "is_building_group = bg_power"),
    ("q_uni", "is_building_type = building_university"),
    ("q_admin", "is_building_type = building_government_administration"),
    ("q_mil", "OR = { is_building_group = bg_military is_building_type = building_military_base }"),
    ("q_infra", "is_building_group = bg_infrastructure"),
]
QUEUED_LEVELS = "te_construction_market_building_queued_levels"
# Electricity is a local good (vanilla goods: local = yes), priced in each state, so it is read through the states,
# with the power grid's own state values (common/script_values/power_grid_values.txt, which its self-checks read).
ELECTRICITY_VALUES = {"made": "te_grid_electricity_production", "used": "te_grid_electricity_consumption",
                      "price": "te_grid_chk_price_now_value"}
# Game rules the probe's fields depend on (the W line, from version 4): each a 1-based index into its settings, 0
# for none. has_game_rule on a setting no file defines is TRUE (scripting_best_practices.md), so the generator stops
# on a setting it does not find in common/game_rules/. A setting's test is the system's own trigger where it has one
# (the small-economy and banking rules are read only through theirs: test_construction_cost_scaling.py holds the
# first to it). free_market_construction_rule's triggers tell only market from direct and waived retooling from not,
# so the probe, alone, reads its five settings by name.
RULES = [
    ("r_fmc", "free_market_construction_rule", [
        "free_market_construction_enabled", "free_market_construction_no_ai_retooling",
        "free_market_construction_no_retooling", "free_market_construction_no_maintenance",
        "free_market_construction_disabled"]),
    ("r_small", "te_small_economy_construction_rule", [
        "te_small_economy_construction_disabled", "te_small_economy_construction_mild",
        "te_small_economy_construction_standard", "te_small_economy_construction_enabled"]),
    ("r_bank", "banking_system_rule", ["banking_system_enabled", "banking_system_simplified",
                                       "banking_system_disabled"]),
]
# The tests of the settings read through a system's triggers, in RULES's order (common/scripted_triggers/
# te_construction_cost_triggers.txt, banking_policy_triggers.txt, te_monetary_triggers.txt). The others are
# `has_game_rule = <setting>`.
RULE_TESTS = {
    "r_small": ["te_small_economy_construction_on = no", "te_small_economy_construction_mild_on = yes",
                "te_small_economy_construction_standard_on = yes", "te_small_economy_construction_strong_on = yes"],
    "r_bank": ["te_mon_full_system = yes", "te_banking_system_on = yes", "te_banking_system_on = no"],
}


def rule_tests(name: str, settings: list[str]) -> list[str]:
    return RULE_TESTS.get(name) or [f"has_game_rule = {setting}" for setting in settings]


# Fields a version took off the end of a positional line: {line: [field, ...]}, in the order older logs print them.
# The parser drops that many values from the end of an older log's line, so a version 4 or 5 log still reads with
# this key. Version 6 (#2090): the army census of versions 4 and 5 marked each battalion with its type in a variable
# on the combat unit, to count recruits and upgrades between reports, but a combat unit holds no variables (the
# census's canary read v=0 in the first game it ran in, 2026-11-26; scripting_best_practices.md, "Combat Units Have
# No Variables"), so every one of these fields read 0.
RETIRED_TAIL = {"P2": ["u_all", "u_new", "u_changed", "u_irr_new", "u_from_irr", "u_flows"]}

# The interface's data functions, printed with each snapshot (and once each at arming, alone).
DATA_FUNCTIONS = [
    # (line, key, accessor after `THIS.GetCountry.`, or an expression with `{c}` for the country)
    (1, "subsidies", "GetSubsidiesExpenses|0"),
    (1, "gov_wages", "GetGovernmentWagesExpenses|0"),
    (1, "mil_wages", "GetMilitaryWagesExpenses|0"),
    (1, "gov_goods", "GetGovernmentGoodsExpenses|0"),
    (1, "mil_goods", "GetMilitaryGoodsExpenses|0"),
    (2, "con_goods", "GetConstructionGoodsExpenses|0"),
    (2, "con_goods_gov", "GetGovernmentConstructionGoodsExpenses|0"),
    (2, "con_goods_priv", "GetPrivateConstructionGoodsExpenses|0"),
    (2, "welfare", "GetWelfarePaymentsExpenses|0"),
    (2, "week_income", "GetWeeklyIncome|0"),
    (2, "week_expenses", "GetWeeklyExpenses|0"),
    (3, "con_used", "CalcUsedConstruction|1"),
    (3, "con_unused", "CalcUnusedConstruction|1"),
    (3, "con_used_gov", "CalcUsedGovernmentConstruction|1"),
    (3, "con_used_priv", "CalcUsedPrivateConstruction|1"),
    (3, "con_base", "CalcBaseConstructionSpeed|1"),
    (4, "innovation", "GetWeeklyInnovation|1"),
    (4, "innovation_max", "GetWeeklyMaxInnovation|1"),
    (4, "research_speed", "GetWeeklyResearchSpeed|2"),
    (5, "researching", "GetCurrentlyResearchedTechnology.GetNameNoFormatting"),
    (6, "enacting", "GetLawBeingEnacted.GetNameNoFormatting"),
    # Version 4. The institutions' bureaucracy cost and the panel's factor beside it (vanilla's
    # politics_panel_institutions.gui), so that the rest of bureaucracy_usage (incorporated states and their people,
    # modifiers' flat costs) can be told from the institutions. Script has no read of either.
    (7, "bur_inst", "GetInstitutionInvestmentBureaucracyCost|0"),
    (7, "bur_inst_factor", "GetInstitutionInvestmentBureaucracyFactor|2"),
    # The average standard of living of each stratum: the latest value of the Politics panel's trend lines (vanilla's
    # politics_panel_types.gui reads them through GetTrendValue). Script has no read of either; no data function
    # gives an average wage.
    (8, "sol_lower", "GetTrendValue({c}.GetAverageSoLLowerTrend)|1"),
    (8, "sol_middle", "GetTrendValue({c}.GetAverageSoLMiddleTrend)|1"),
    (8, "sol_upper", "GetTrendValue({c}.GetAverageSoLUpperTrend)|1"),
]
# The version each data function was added in (older ones from version 1), so that `check` asks a log only for the
# canaries its version printed.
DATA_FUNCTIONS_ADDED = {4: ["bur_inst", "bur_inst_factor", "sol_lower", "sol_middle", "sol_upper"]}


def data_function_text(accessor: str) -> str:
    """A DATA_FUNCTIONS accessor as the loc string prints it: after the country, or an expression around it."""
    return accessor.format(c="THIS.GetCountry") if "{c}" in accessor else f"THIS.GetCountry.{accessor}"


def unwrap(value):
    """Strip the parser's ('=', value) wrappers."""
    while isinstance(value, (tuple, list)) and len(value) == 2 and value[0] == "=":
        value = value[1]
    return value


def load_state(root: Path = ROOT):
    """Laws, technologies, groups and units: vanilla from the committed snapshot, the mod from disk."""
    from mod_state import VANILLA_COMMON_DIRS, ModState
    from vanilla_parsed import load

    kinds = ("Laws", "Law Groups", "Technologies", "Combat Unit Types", "Building Groups", "Buildings",
             "Institutions", "Diplomatic Plays", "PM Groups")
    snapshot = load(str(root / "vanilla_parsed"))
    state = ModState(
        {kind: "/nonexistent" for kind in kinds},
        {kind: str(root / "common" / VANILLA_COMMON_DIRS[kind]) for kind in kinds},
        vanilla_data=snapshot.data,
    )
    if state.parse_failures:
        raise ValueError(f"Cannot generate the AI probe from an incomplete parse: {state.parse_failures}")
    return state


def bare(key: str) -> str:
    """An entity key without its directive (`INJECT:law_x` -> `law_x`)."""
    return key.split(":", 1)[1] if ":" in key else key


def catalog(mod_state) -> dict:
    """The lists the indexed fields are built from, in a stable order."""
    laws = mod_state.get_data("Laws")
    by_group: dict[str, list[str]] = {}
    for key in laws:
        body = unwrap(laws[key])
        group = unwrap(body.get("group")) if isinstance(body, dict) else None
        if not isinstance(group, str):
            continue
        name = bare(key)
        if name not in by_group.setdefault(group, []):
            by_group[group].append(name)
    law_groups = [bare(group) for group in mod_state.get_data("Law Groups")]
    for group in by_group:
        if group not in law_groups:
            law_groups.append(group)
    law_groups = [group for group in dict.fromkeys(law_groups) if by_group.get(group)]

    techs = mod_state.get_data("Technologies")
    tech_cells: dict[tuple[str, int], list[str]] = {}
    all_techs: list[str] = []
    for key in techs:
        body = unwrap(techs[key])
        if not isinstance(body, dict):
            continue
        era, category = unwrap(body.get("era")), unwrap(body.get("category"))
        if not isinstance(era, str) or not era.startswith("era_") or category not in ("production", "military",
                                                                                      "society"):
            continue
        name = bare(key)
        if name in all_techs:
            continue
        all_techs.append(name)
        if unwrap(body.get("can_research")) == "no":
            continue
        tech_cells.setdefault((category, int(era[4:])), []).append(name)

    # A land unit type's tier is the era of the technology that unlocks it (1 with none): a measure of how modern
    # a type is that compares across infantry, artillery and cavalry. Upgrade chains do not give one: cavalry
    # types upgrade into each other in a circle.
    tech_era = {}
    for key in techs:
        body = unwrap(techs[key])
        era = unwrap(body.get("era")) if isinstance(body, dict) else None
        if isinstance(era, str) and era.startswith("era_"):
            tech_era[bare(key)] = int(era[4:])
    units = mod_state.get_data("Combat Unit Types")
    land_groups = {"combat_unit_group_infantry", "combat_unit_group_artillery", "combat_unit_group_cavalry"}
    tier: dict[str, int] = {}
    unit_types: dict[str, dict] = {}         # every unit type: its group, tier and unlocking technologies
    for key in units:
        body = unwrap(units[key])
        if not isinstance(body, dict):
            continue
        unlocks = unwrap(body.get("unlocking_technologies"))
        unlocks = [t for t in unlocks if isinstance(t, str)] if isinstance(unlocks, list) else []
        eras = [tech_era[t] for t in unlocks if t in tech_era]
        group = unwrap(body.get("group"))
        if bare(key) not in unit_types:
            unit_types[bare(key)] = {"group": group, "tier": max(eras, default=1), "techs": unlocks}
        if group not in land_groups:
            continue
        tier[bare(key)] = max(eras, default=1)

    # The R line: the named types in group order, then by tier; the sums after them.
    named = sorted((name for name, info in unit_types.items()
                    if info["group"] in UNIT_LINE_GROUPS and info["tier"] <= UNIT_LINE_MAX_TIER),
                   key=lambda name: (UNIT_LINE_GROUPS.index(unit_types[name]["group"]), unit_types[name]["tier"]))
    later = [name for name, info in unit_types.items()
             if info["group"] in UNIT_LINE_GROUPS and info["tier"] > UNIT_LINE_MAX_TIER]
    unit_line = [("u_" + short(name, "combat_unit_type_"), [name]) for name in named]
    unit_line += [(field, [name for name, info in unit_types.items() if info["group"] == group])
                  for field, group in UNIT_SUM_GROUPS]
    unit_line.append(("u_later", later))
    unit_techs = list(dict.fromkeys(t for name in named for t in unit_types[name]["techs"]))
    tech_flags = list(dict.fromkeys(TECH_FLAGS + unit_techs))
    tech_flags_4 = [t for t in dict.fromkeys(TECH_FLAGS_4) if t not in tech_flags]
    missing = [t for t in tech_flags + tech_flags_4 if t not in all_techs]
    if missing:
        raise ValueError(f"TECH_FLAGS names technologies no file defines: {missing}")

    # A group counts when a building belongs to it or to a group under it. Vanilla keeps 21 legacy groups
    # (bg_coal_mining, bg_wheat_farms, ...) that no building belongs to; test_no_dead_building_groups.py bars them.
    group_data = mod_state.get_data("Building Groups")
    parent = {}
    for key in group_data:
        body = unwrap(group_data[key])
        up = unwrap(body.get("parent_group")) if isinstance(body, dict) else None
        if isinstance(up, str):
            parent[bare(key)] = up
    building_data = mod_state.get_data("Buildings")
    live: set[str] = set()
    for key in building_data:
        body = unwrap(building_data[key])
        group = unwrap(body.get("building_group")) if isinstance(body, dict) else None
        while isinstance(group, str) and group not in live:
            live.add(group)
            group = parent.get(group)
    groups = [bare(key) for key in group_data if bare(key) in live]
    buildings = {bare(key) for key in building_data}
    institutions = [bare(key) for key in mod_state.get_data("Institutions")]
    play_types = list(dict.fromkeys(bare(key) for key in mod_state.get_data("Diplomatic Plays")))
    construction_methods = sector_methods(mod_state, building_data)
    for needed in (CONSTRUCTION_SECTOR, CONSTRUCTION_SITE):
        if needed not in buildings:
            raise ValueError(f"The probe's Construction Sector fields name a building no file defines: {needed}")
    for name, read_group in BUILDING_TYPE_READS.items():
        if read_group not in groups:
            raise ValueError(f"BUILDING_TYPE_READS reads {name} through {read_group}, which no building belongs to")
    return {
        # Version 4.
        "tech_flags_4": tech_flags_4,
        "street_lights": street_lighting_methods(mod_state),
        "law_groups": law_groups,
        "laws": {group: by_group[group] for group in law_groups},
        "all_laws": [law for group in law_groups for law in by_group[group]],
        "tech_cells": {f"{category}_{era}": names for (category, era), names in sorted(tech_cells.items())},
        "all_techs": all_techs,
        "unit_tier": tier,
        "building_groups": list(dict.fromkeys(groups)),
        "building_types": [b for b in BUILDING_TYPES if b in buildings],
        "institutions": list(dict.fromkeys(institutions)),
        "unit_line": unit_line,
        "unit_types": unit_types,
        "unit_techs": unit_techs,
        "tech_flags": tech_flags,
        "play_types": play_types,
        "construction_methods": construction_methods,
    }


def sector_methods(mod_state, building_data) -> list[tuple[str, list[str]]]:
    """The Construction Sector's construction methods (its first method group's), as (field, methods): the first
    CONSTRUCTION_METHODS_NAMED one by one, then the rest as cs_pm_later."""
    body = next((unwrap(building_data[key]) for key in building_data if bare(key) == CONSTRUCTION_SECTOR), None)
    groups = unwrap(body.get("production_method_groups")) if isinstance(body, dict) else None
    if not isinstance(groups, list) or not groups:
        raise ValueError(f"{CONSTRUCTION_SECTOR} has no production method groups")
    pm_groups = mod_state.get_data("PM Groups")
    group = next((unwrap(pm_groups[key]) for key in pm_groups if bare(key) == groups[0]), None)
    methods = unwrap(group.get("production_methods")) if isinstance(group, dict) else None
    methods = [m for m in methods if isinstance(m, str)] if isinstance(methods, list) else []
    if len(methods) <= CONSTRUCTION_METHODS_NAMED:
        raise ValueError(f"{groups[0]} lists {len(methods)} methods; the probe names {CONSTRUCTION_METHODS_NAMED}")
    named = [("cs_pm_" + short(m, "pm_").removesuffix("_buildings"), [m]) for m in methods[:CONSTRUCTION_METHODS_NAMED]]
    return named + [("cs_pm_later", methods[CONSTRUCTION_METHODS_NAMED:])]


def street_lighting_methods(mod_state) -> list[tuple[str, list[str]]]:
    """The urban centre's street lighting as (field, methods): gas, then every method after it (the electric ones)."""
    pm_groups = mod_state.get_data("PM Groups")
    group = next((unwrap(pm_groups[key]) for key in pm_groups if bare(key) == STREET_LIGHTING_GROUP), None)
    methods = unwrap(group.get("production_methods")) if isinstance(group, dict) else None
    methods = [m for m in methods if isinstance(m, str)] if isinstance(methods, list) else []
    if methods[:2] != [STREET_LIGHTING_NONE, STREET_LIGHTING_GAS] or len(methods) < 3:
        raise ValueError(f"{STREET_LIGHTING_GROUP} lists {methods}: the probe expects none, gas, then electric ones")
    return [("uc_gas_light", [STREET_LIGHTING_GAS]), ("uc_elec_light", methods[2:])]


def check_rules(root: Path = ROOT) -> None:
    """Stop on a RULES setting no file in common/game_rules/ defines inside its rule's block: has_game_rule on an
    undefined setting is true, so its index would read 1 in every game."""
    text = "\n".join(path.read_text(encoding="utf-8-sig") for path in sorted((root / "common/game_rules").glob("*.txt")))
    for _, rule, settings in RULES:
        found = re.search(rf"(?ms)^{re.escape(rule)} = \{{\n(.*?)^\}}", text)
        if not found:
            raise ValueError(f"RULES names a game rule no file defines: {rule}")
        defined = set(re.findall(r"(?m)^\t([a-z_]+) = \{", found.group(1)))
        missing = [s for s in settings if s not in defined]
        if missing:
            raise ValueError(f"RULES names settings {rule} does not define: {missing}")


class Field:
    """One logged figure: its key in the log, the body of its script value, and the decimals it prints with."""

    def __init__(self, key: str, body: str, decimals: int = 0):
        self.key, self.body, self.decimals = key, body, decimals

    @property
    def value_name(self) -> str:
        return PREFIX + self.key

    def script_value(self) -> str:
        if "\n" in self.body:
            return f"{self.value_name} = {{\n{self.body}\n}}\n"
        return f"{self.value_name} = {{ {self.body} }}\n"

    def accessor(self, keyed: bool = True) -> str:
        text = f"[THIS.ScriptValue('{self.value_name}')|{self.decimals}]"
        return f"{self.key}={text}" if keyed else text


def read(key: str, source: str, decimals: int = 0) -> Field:
    """A plain read of a value link or a numeric trigger."""
    return Field(key, f"value = {source}", decimals)


def flag(key: str, trigger: str) -> Field:
    """1 when the trigger holds."""
    return Field(key, f"value = 0 if = {{ limit = {{ {trigger} }} value = 1 }}")


def index(key: str, tests: list[str]) -> Field:
    """The 1-based position of the first test that holds, 0 when none does."""
    lines = ["\tvalue = 0"]
    for i, test in enumerate(tests, 1):
        word = "if" if i == 1 else "else_if"
        lines.append(f"\t{word} = {{ limit = {{ {test} }} value = {i} }}")
    return Field(key, "\n".join(lines))


def count(key: str, tests: list[str]) -> Field:
    """How many of the tests hold."""
    lines = ["\tvalue = 0"]
    lines += [f"\tif = {{ limit = {{ {test} }} add = 1 }}" for test in tests]
    return Field(key, "\n".join(lines))


def variable(key: str, name: str, decimals: int = 0) -> Field:
    """A country variable, 0 when unset."""
    return Field(key, f"value = 0 if = {{ limit = {{ has_variable = {name} }} value = var:{name} }}", decimals)


def levels(key: str, limit: str) -> Field:
    """The levels of the country's buildings that pass the limit (one pass over its buildings)."""
    return Field(key, f"\tvalue = 0\n\tevery_scope_building = {{\n\t\tlimit = {{ {limit} }}\n\t\tadd = level\n\t}}")


def short(name: str, prefix: str) -> str:
    """A field's key from an entity's name: the prefix off, lower case (`lawgroup_LGBTQ_rights` -> `lgbtq_rights`)."""
    return (name[len(prefix):] if name.startswith(prefix) else name).lower()


def field_groups(cat: dict) -> list[tuple[str, list[Field]]]:
    """Every snapshot line: (group letter, fields)."""
    economy = [
        read("y", "year"),
        flag("ai", "is_ai = yes"),
        index("rank", [f"country_rank = rank_value:{rank}" for rank in RANKS]),
        index("type", [f"is_country_type = {kind}" for kind in COUNTRY_TYPES]),
        flag("subject", "is_subject = yes"),
        read("gdp", "gdp"),
        read("pop", "total_population"),
        read("sol", "average_sol", 2),
        read("sol_exp", "average_expected_sol", 2),
        read("lit", "literacy_rate", 3),
        read("peasants", '"pop_type_percent_country(pop_type:peasants)"', 3),
        read("radicals", "radical_fraction", 3),
        read("loyalists", "loyalist_fraction", 3),
        read("legitimacy", "legitimacy"),
        read("infamy", "infamy", 1),
        read("states", "num_states"),
        read("states_inc", "num_incorporated_states"),
        read("colonies", "num_colony_projects"),
        read("subjects", "num_subjects"),
        flag("war", "is_at_war = yes"),
        read("plays", "num_active_plays"),
        read("levels", "building_levels"),
        read("techs", "techs_researched"),
        read("innovation", "country_innovation", 1),
        flag("enacting", "enacting_any_law = yes"),
        flag("researching", "is_researching_technology = any"),
        flag("revolution", "has_revolution = yes"),
        flag("insurrection", "has_insurrectionary_interest_groups = yes"),
        flag("election", "in_election_campaign = yes"),
    ]
    finance = [
        read("income", "income"),
        read("expenses", "total_expenses"),
        read("fixed_income", "fixed_income"),
        read("fixed_expenses", "fixed_expenses"),
        read("net_fixed", "net_fixed_income"),
        read("tax_income", "tax_income"),
        read("tax_level", "tax_level_value"),
        read("gold", "gold_reserves"),
        read("gold_limit", "gold_reserves_limit"),
        read("gold_scaled", "scaled_gold_reserves", 3),
        read("debt_scaled", "scaled_debt", 3),
        read("principal", "principal"),
        read("credit", "credit"),
        flag("default", "in_default = yes"),
        flag("bankrupt", "has_modifier = declared_bankruptcy"),
        flag("loans", "taking_loans = yes"),
        read("pool", "investment_pool"),
        read("pool_income", "investment_pool_gross_income"),
        read("mil_expenses", "military_expenses"),
        read("mil_share", "military_expenses_share", 3),
        read("gov_wage", "government_wage_level_value"),
        read("mil_wage", "military_wage_level_value"),
        read("bur", "bureaucracy"),
        read("bur_made", "produced_bureaucracy"),
        read("bur_used", "bureaucracy_usage"),
        read("auth", "authority"),
        read("auth_used", "authority_usage"),
        read("infl", "influence"),
        read("infl_used", "influence_usage"),
        read("exports", "total_export_value"),
        read("imports", "total_import_value"),
        read("pact_share", "diplomatic_pact_expense_ratio", 3),
        read("gdp_rank", "gdp_ranking"),
    ]
    construction = [
        read("queue_levels", "construction_queue_num_queued_levels"),
        read("queue_gov", "construction_queue_num_queued_government_levels"),
        read("queue_priv", "construction_queue_num_queued_private_levels"),
        read("queue_n", "num_queued_constructions"),
        read("queue_n_gov", "num_queued_government_constructions"),
        read("queue_n_priv", "num_queued_private_constructions"),
        read("queue_days", "construction_queue_duration"),
        read("queue_days_gov", "construction_queue_government_duration"),
        flag("paused", "is_construction_paused = yes"),
        # NOT a measure of construction points bought and not used, and silent while a country is paused: in run 2
        # (2026-11-16) has_wasted_construction held on 11,750 of 16,119 unpaused snapshots while the X line's
        # con_unused was above 0 on only 108, and on none of the 1,056 paused ones (35 of which had unused points).
        # Read con_unused for unused points (ai_probe_report.py does).
        flag("wasted", "has_wasted_construction = yes"),
        flag("healthy", "has_healthy_economy = yes"),
        # The construction market's AI purchase reads the price variable unguarded, so it is read only where set.
        Field("cm_target", "value = 0 if = { limit = { has_variable = te_construction_market_price_stabilizer } "
              "value = te_construction_market_ai_purchase_target }", 3),
        variable("cm_price", "te_construction_market_price_stabilizer"),
        # Three decimals: a small government's purchase is a fraction of a point (0.08 would print as 0).
        variable("cm_public", "te_construction_market_public_target", 3),
        read("companies", "num_companies"),
        read("companies_max", "max_num_companies"),
        # Version 2: what te_construction_market_ai_purchase_target reads that the fields above lack, so the
        # purchase can be recomputed from a snapshot (ai_probe_report.py purchase_target): the banking brake's
        # bubble pressure and the weekly maximum a queued level takes. cm_admin, a country short of bureaucracy
        # with a Government Administration queued, was a term too until the purchase through the engine's pause
        # was removed (2026-11-16); it stays as a field of its own.
        variable("bubble", "bubble_pressure", 1),
        read("cm_level_max", "modifier:country_max_weekly_construction_progress_add", 2),
        flag("cm_admin", "te_construction_market_ai_building_administration = yes"),
        # Version 3: the banking cycle (BANK_PHASES), which confounded the first comparison of two runs: a crash
        # in one run's 1890s and not the other's. The phase guards its reads with te_banking_cycle_running, as
        # the journal entry's phase modifiers guard theirs with has_variable; the value and momentum are the
        # cycle's own variables (absent before the cycle starts and after the rule is switched off); `bank_crashed`
        # is the 365-day mark every crash sets, origin and contagion (banking_mark_crashed_last_year).
        bank_phase_field(),
        variable("bank_cycle", "finance_cycle_value", 1),
        variable("bank_momentum", "finance_cycle_momentum", 2),
        flag("bank_crashed", "has_variable = banking_crashed_last_year"),
        # Version 5 (#1877): the rate the purchase reads, what it asks of the purchase, and the AI construction pass
        # (te_construction_market_ai_values.txt, THE RATE and THE PASS), so purchase_target can be recomputed with the
        # rate's terms and the pass's levels counted.
        variable("rate", "te_rate_paid_pts", 2),
        variable("rate_base", "te_mon_era_base_now", 1),
        Field("cm_reserve", "value = te_construction_market_ai_required_reserves", 3),
        Field("cm_credit", "value = te_construction_market_ai_credit_allowance", 3),
        variable("cm_pass", "te_ai_build_pass_count"),
        # The pass's railway entry reads each state's infrastructure against its usage
        # (te_ai_build_pass_infrastructure_shortfall): the states short of it, and by how much in all.
        Field("inf_short_states", "\tvalue = 0\n\tevery_scope_state = {\n"
                                  "\t\tlimit = { te_ai_build_pass_infrastructure_shortfall > 0 }\n\t\tadd = 1\n\t}"),
        Field("inf_short", "\tvalue = 0\n\tevery_scope_state = {\n"
                           "\t\tlimit = { te_ai_build_pass_infrastructure_shortfall > 0 }\n"
                           "\t\tadd = te_ai_build_pass_infrastructure_shortfall\n\t}"),
    ]
    military = [
        read("army", "army_size"),
        read("army_conscripts", "army_size_including_conscripts"),
        read("navy", "navy_size"),
        read("army_power", "army_power_projection"),
        read("navy_power", "naval_power_projection"),
        Field("army_tier", "\n".join(
            ["\tvalue = 0"] + [
                f'\tadd = {{ value = "country_army_unit_type_fraction(unit_type:{unit})" multiply = {tier} }}'
                for unit, tier in cat["unit_tier"].items()
            ]), 2),
        read("irregular", '"country_army_unit_type_fraction(unit_type:combat_unit_type_irregular_infantry)"', 3),
        read("line", '"country_army_unit_type_fraction(unit_type:combat_unit_type_line_infantry)"', 3),
        read("alliances", "num_alliances"),
        read("defensive_pacts", "num_defensive_pacts"),
        read("rivals", "num_rivals"),
        read("interests", "num_active_interests"),
        read("colony_growth", "colonial_growth_per_colony", 1),
    ]
    strategy = [
        index(f"strat_{kind}", [f"has_strategy = {name}" for name in names]) for kind, names in STRATEGIES.items()
    ] + [
        index("law_enacting", [f"is_enacting_law = law_type:{law}" for law in cat["all_laws"]]),
        index("tech_researching", [f"is_researching_technology = {tech}" for tech in cat["all_techs"]]),
    ]
    laws = [
        index("lw_" + short(group, "lawgroup_"), [f"has_law = law_type:{law}" for law in cat["laws"][group]])
        for group in cat["law_groups"]
    ]
    techs = [
        count("tc_" + cell, [f"has_technology_researched = {tech}" for tech in names])
        for cell, names in cat["tech_cells"].items()
    ]
    institutions = [
        read("in_" + short(name, "institution_"), f'"institution_investment_level({name})"')
        for name in cat["institutions"]
    ]
    groups = [
        read("bg_" + short(name, "bg_"), f'"country_has_building_group_levels({name})"')
        for name in cat["building_groups"]
    ]
    types = [
        read("bt_" + short(name, "building_"), f'"country_has_building_group_levels({BUILDING_TYPE_READS[name]})"'
             if name in BUILDING_TYPE_READS else f'"country_has_building_type_levels(bt:{name})"')
        for name in cat["building_types"]
    ] + [
        # Version 5 (#1877): the states the AI construction pass's railway entry would act on, its own site test
        # (incorporated, short of infrastructure by more than the margin; the 2026-11-17 review). C2 is full.
        Field("rail_sites", "\tvalue = 0\n\tevery_scope_state = {\n"
                            "\t\tlimit = { te_ai_build_pass_railway_site = yes }\n\t\tadd = 1\n\t}"),
    ]
    budget = (
        [read("ux_all", "modifier:country_expenses_add")]
        + [read("ux_" + name, f"modifier:country_te_budget_expense_{name}_add") for name in BUDGET_EXPENSES]
        + [read("ui_" + name, f"modifier:country_te_budget_income_{name}_add") for name in BUDGET_INCOMES]
    )
    staffing = (
        [levels("low_" + name, f"is_building_group = {group} occupancy < 0.5") for name, group in STAFFING_CLASSES]
        + [levels("rt_" + name, f"is_building_group = {group} has_modifier = pm_retooling")
           for name, group in STAFFING_CLASSES]
        + [levels("rt_all", "has_modifier = pm_retooling"), levels("sub_all", "is_subsidized = yes")]
        + [levels(key, f"is_building_type = {building} has_active_production_method = {method}")
           for key, building, method in STALE_METHODS if building in cat["building_types"]]
        # Version 2: manufacturing without the Construction Sector, which the mod puts under bg_heavy_industry
        # (extra_building_groups.txt), so that low_mfg's idle sectors in a small country do not read as idle
        # factories. Its denominator is bg_manufacturing less bg_construction, both in the G line.
        + [levels("low_mfg_nc", "is_building_group = bg_manufacturing NOT = { is_building_group = bg_construction } "
                  "occupancy < 0.5")]
        + construction_sector_fields(cat)
    )
    counters = [variable("n_" + name, PREFIX + "n_" + name) for name in COUNTERS]
    # Version 2's positional groups.
    institution_max = [
        Field("im_" + short(name, "institution_"),
              f"value = 0 if = {{ limit = {{ has_institution = {name} }} institution:{name} = {{ add = investment_max }} }}")
        for name in cat["institutions"]
    ]
    units = [
        Field(field, "\n".join(
            ["\tvalue = 0"]
            + [f'\tadd = "country_army_unit_type_fraction(unit_type:{unit})"' for unit in members]), 3)
        for field, members in cat["unit_line"]
    ]
    tech_flags = [flag("h_" + tech.replace("-", "_"), f"has_technology_researched = {tech}")
                  for tech in cat["tech_flags"]]
    # Version 4: H's second line (a positional line never takes another field) and the P group.
    tech_flags_4 = [flag("h_" + tech.replace("-", "_"), f"has_technology_researched = {tech}")
                    for tech in cat.get("tech_flags_4", [])]
    groups_ = [("A", economy), ("F", finance), ("U", budget), ("C", construction), ("O", staffing), ("M", military),
               ("Y", strategy), ("L", laws), ("T", techs), ("I", institutions), ("G", groups), ("B", types),
               ("N", counters), ("J", institution_max), ("R", units), ("H", tech_flags)]
    if tech_flags_4:
        groups_.append(("H", tech_flags_4))
    if cat.get("street_lights"):
        groups_.append(("P", version_4_fields(cat)))
    return groups_


def queued(key: str, limit: str) -> Field:
    """The levels of the country's buildings that pass the limit still in a construction queue."""
    return Field(key, f"\tvalue = 0\n\tevery_scope_building = {{\n\t\tlimit = {{ {limit} }}\n"
                      f"\t\tadd = {QUEUED_LEVELS}\n\t}}")


def market_good(key: str, good: str) -> list[Field]:
    """A traded good in the country's market (a shared market's, for a country in one): its price over base, as
    cs_price reads the construction good's, and its buy and sell orders."""
    market = f"this.market.mg:{good}"
    return [
        Field(f"{key}_price", f"\tvalue = 1\n\tadd = {{ value = {market}.market_goods_pricier min = 0 }}\n"
                              f"\tsubtract = {{ value = {market}.market_goods_cheaper min = 0 }}", 3),
        read(f"{key}_buy", f"{market}.market_goods_buy_orders", 1),
        read(f"{key}_sell", f"{market}.market_goods_sell_orders", 1),
    ]


def version_4_fields(cat: dict) -> list[Field]:
    """The P group (version 4): electrification, the construction queue by kind, the construction cost scaling, the
    bureaucracy's modifiers and the workforce's slack, in that order (versions 4 and 5 ended it with the army census:
    RETIRED_TAIL)."""
    kinds = dict(QUEUE_KINDS)
    lights = [levels(name, "is_building_type = building_urban_center " + (
        f"has_active_production_method = {methods[0]}" if len(methods) == 1 else
        "OR = { " + " ".join(f"has_active_production_method = {m}" for m in methods) + " }"))
        for name, methods in cat["street_lights"]]
    electricity = [
        # The states with a building that makes Electricity, built or under construction (te_ai_coverage_triggers.txt).
        Field("pp_states", "\tvalue = 0\n\tevery_scope_state = {\n\t\tlimit = { te_state_has_a_power_plant = yes }\n"
                           "\t\tadd = 1\n\t}"),
        queued("q_power", kinds["q_power"]),
        # A week's Electricity made and bought, summed over the country's states, and the price over base where it
        # is bought, weighted by what each state buys (0 where none is bought).
        Field("elec_made", f"\tvalue = 0\n\tevery_scope_state = {{ add = {ELECTRICITY_VALUES['made']} }}", 0),
        Field("elec_used", f"\tvalue = 0\n\tevery_scope_state = {{ add = {ELECTRICITY_VALUES['used']} }}", 0),
        Field("elec_price", "\tvalue = 0\n\tif = {\n\t\tlimit = { te_aip_elec_used > 0 }\n"
                            "\t\tevery_scope_state = {\n"
                            f"\t\t\tadd = {{ value = {ELECTRICITY_VALUES['used']} multiply = {ELECTRICITY_VALUES['price']} }}\n"
                            "\t\t}\n\t\tdivide = te_aip_elec_used\n\t}", 3),
    ] + lights + market_good("radio", "radios")
    queue = [queued(name, kinds[name]) for name, _ in QUEUE_KINDS if name != "q_power"]
    cost = [
        # A construction point's cost over its base (docs/systems/mod_systems/construction.md, Construction Cost
        # Scaling): the scaling's own factor in force (te_cc_scaling_factor, S x d) and every construction-cost
        # modifier with it (te_cc_total_factor, the Nation tab's total).
        read("cc_scale", "te_cc_scaling_factor", 3),
        read("cc_total", "te_cc_total_factor", 3),
    ]
    bureaucracy = [
        # Production's flat additions and multiplier; use's flat additions, and the multipliers of the institutions'
        # cost (37 of the mod's laws move it) and of the states' cost per head (14 of them).
        read("bur_add", "modifier:country_bureaucracy_add"),
        read("bur_mult", "modifier:country_bureaucracy_mult", 2),
        read("bur_cost_add", "modifier:country_bureaucracy_cost_add"),
        read("bur_inst_mult", "modifier:country_bureaucracy_investment_cost_factor_mult", 2),
        read("bur_pop_mult", "modifier:state_bureaucracy_population_base_cost_factor_mult", 2),
    ]
    labour = [
        # The workforce with no market workplace (peasants and the unemployed), and the peasants, over the
        # workforce of the states walked, as the cost scaling's yearly pulse stores them (te_cc_yearly_update).
        variable("slack", "te_cc_slack", 3),
        variable("slack_peasants", "te_cc_peasants", 3),
    ]
    return electricity + queue + cost + bureaucracy + labour


def bank_phase_field() -> Field:
    """The banking cycle's phase (BANK_PHASES, 1-based), 0 with no cycle running. The phase triggers read
    finance_cycle_value unguarded, so they are tested only inside te_banking_cycle_running."""
    tests = "\n".join(f"\t\t{'if' if i == 1 else 'else_if'} = {{ limit = {{ banking_cycle_is_{phase} = yes }} value = {i} }}"
                      for i, phase in enumerate(BANK_PHASES, 1))
    return Field("bank_phase", f"\tvalue = 0\n\tif = {{\n\t\tlimit = {{ te_banking_cycle_running = yes }}\n{tests}\n\t}}")


def construction_sector_fields(cat: dict) -> list[Field]:
    """Version 2's Construction Sector fields (CONSTRUCTION_SECTOR's comment): fourteen, which fill the O2 line."""
    sector = f"is_building_type = {CONSTRUCTION_SECTOR}"
    market = f"this.market.mg:{CONSTRUCTION_GOOD}"
    return [
        levels("cs_low", f"{sector} occupancy < 0.5"),
        levels("cs_low80", f"{sector} occupancy < {AI_EXPANSION_STAFFING}"),
        # Level times occupancy: the bare value read power_grid_values.txt's te_grid_mix_staffed_output_value makes
        # (its self-check read a staffed share, grid_mix_staffing OK on 2026-11-13).
        Field("cs_staffed", f"\tvalue = 0\n\tevery_scope_building = {{\n\t\tlimit = {{ {sector} }}\n"
                            "\t\tadd = { value = level multiply = occupancy }\n\t}", 1),
        levels("cs_sub", f"{sector} is_subsidized = yes"),
    ] + [
        levels(name, f"{sector} " + (f"has_active_production_method = {methods[0]}" if len(methods) == 1 else
                                     "OR = { " + " ".join(f"has_active_production_method = {m}" for m in methods)
                                     + " }"))
        for name, methods in cat["construction_methods"]
    ] + [
        # The good's price over its base price in the country's market (a shared market's, for a country in one):
        # the dot chain te_construction_market_price reads, whose price moved in the first long run; the cheaper
        # side the Strategic Reserve's way (st_res_<good>_price_rel), since no engine doc says whether either term
        # is signed.
        Field("cs_price", f"\tvalue = 1\n\tadd = {{ value = {market}.market_goods_pricier min = 0 }}\n"
                          f"\tsubtract = {{ value = {market}.market_goods_cheaper min = 0 }}", 3),
        read("cs_buy", f"{market}.market_goods_buy_orders", 1),
        read("cs_sell", f"{market}.market_goods_sell_orders", 1),
        levels("site_low", f"is_building_type = {CONSTRUCTION_SITE} occupancy < 0.5"),
        levels("site_low80", f"is_building_type = {CONSTRUCTION_SITE} occupancy < {AI_EXPANSION_STAFFING}"),
    ]


def all_fields(cat: dict) -> list[Field]:
    return [field for _, fields in field_groups(cat) for field in fields]


# The script values the lines' own prefixes use, beside the fields.
BASE_VALUES = (
    "te_aip_id = { value = 0 if = { limit = { has_variable = te_aip_id } value = var:te_aip_id } }\n"
    "te_aip_k = { value = 0 if = { limit = { has_global_variable = te_aip_k } value = global_var:te_aip_k } }\n"
    "te_aip_year = { value = year }\n"
    "# The calendar month a country reports in each year (0 = January): its serial modulo 12, so the world's\n"
    "# snapshots spread over the year.\n"
    "te_aip_id_phase = {\n"
    "\tvalue = 0\n"
    "\tif = { limit = { has_variable = te_aip_id } value = var:te_aip_id }\n"
    "\tmodulo = 12\n"
    "}\n"
    "# Version 3's schedule (te_aip_country_tick). The calendar month as a running count, year * 12 + month\n"
    "# (0 = January), the form te_history_month_index reads.\n"
    "te_aip_month_index = {\n"
    "\tvalue = year\n"
    "\tmultiply = 12\n"
    + "".join(f"\tif = {{ limit = {{ month = {m} }} add = {m} }}\n" for m in range(1, 12))
    + "}\n"
    "# The month a country first reports in: its month this year (te_aip_country_tick moves it a year on if it\n"
    "# has passed), then the same month of each next year.\n"
    "te_aip_first_due = {\n"
    "\tvalue = year\n"
    "\tmultiply = 12\n"
    "\tadd = te_aip_id_phase\n"
    "}\n"
    "te_aip_next_due = {\n"
    "\tvalue = year\n"
    "\tadd = 1\n"
    "\tmultiply = 12\n"
    "\tadd = te_aip_id_phase\n"
    "}\n"
    "# Months until the country's next report: 0 or less is due.\n"
    "te_aip_due_in = {\n"
    "\tvalue = 0\n"
    "\tif = {\n"
    "\t\tlimit = { has_variable = te_aip_due }\n"
    "\t\tvalue = var:te_aip_due\n"
    "\t\tsubtract = te_aip_month_index\n"
    "\t}\n"
    "}\n"
    "# The global month's place in the probe's year: the W line prints at 1, the month the probe armed in and\n"
    "# every twelfth after.\n"
    "te_aip_k_phase = {\n"
    "\tvalue = 0\n"
    "\tif = { limit = { has_global_variable = te_aip_k } value = global_var:te_aip_k }\n"
    "\tmodulo = 12\n"
    "}\n"
)


def render_values(cat: dict) -> str:
    parts = [HEADER, "\n", BASE_VALUES, "\n"]
    for group, fields in field_groups(cat):
        parts.append(f"# --- {group} ---\n")
        parts.extend(field.script_value() for field in fields)
        parts.append("\n")
    parts.append("# --- version 2: a diplomatic play's type (ai_probe_key.json, play_types), read in the play's scope ---\n")
    parts.append(index("play_type_index", [f"is_diplomatic_play_type = {play}" for play in cat["play_types"]])
                 .script_value())
    parts.append("\n")
    return "".join(parts)


def chunks(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def snapshot_lines(cat: dict) -> list[tuple[str, list[Field]]]:
    """Every line of a snapshot: (its name, `G2`, and the fields it carries, in order)."""
    lines, numbered = [], {}
    for group, fields in field_groups(cat):
        size = LINE_SIZE.get(group, POSITIONAL_PER_LINE if group in POSITIONAL else FIELDS_PER_LINE)
        for part in chunks(fields, size):
            # A group given twice (H from version 4) numbers its second part's lines on from the first's.
            numbered[group] = numbered.get(group, 0) + 1
            lines.append((f"{group}{numbered[group]}", part))
    return lines


LINE_HEAD = "[THIS.GetCountry.GetTagName] [THIS.ScriptValue('te_aip_id')|0] [THIS.ScriptValue('te_aip_k')|0]"
# The W line's fields (te_aip_w_<name>), in the order it prints them: countries that are not decentralized
# nations, decentralized nations, and the states they hold, which is the land left to colonize; from version 3,
# every state in the world and the states of the countries that are not decentralized nations, so that
# `states - c_states` reads the same land a second way (EVENT_VALUES); from version 4, the setting of each of the
# game rules the probe's fields depend on (RULES), the first W line being the arming month's.
WORLD_FIELDS = ["countries", "dn", "dn_states", "states", "c_states"] + [name for name, _, _ in RULES]
LAW_FIELDS = ("law=[THIS.ScriptValue('te_aip_law_enacting')|0] chance=[THIS.ScriptValue('te_aip_ev_enact_chance')|2] "
              "stall=[THIS.ScriptValue('te_aip_ev_stall_chance')|2] setbacks=[THIS.ScriptValue('te_aip_ev_setbacks')|0]")
WORLD_LINE = ("TE_AIP W [THIS.ScriptValue('te_aip_k')|0] y=[THIS.ScriptValue('te_aip_year')|0] "
              + " ".join(f"{name}=[THIS.ScriptValue('te_aip_w_{name}')|0]" for name in WORLD_FIELDS))


def render_effects(cat: dict) -> str:
    out = [HEADER, "\n"]
    out.append(
        "# One more of a counter the country keeps between two snapshots. The set comes first: change_variable on a\n"
        "# variable nobody set fails with an error and counts nothing (#1818).\n"
        "te_aip_count = {\n"
        "\tif = {\n"
        "\t\tlimit = { NOT = { has_variable = te_aip_n_$N$ } }\n"
        "\t\tset_variable = { name = te_aip_n_$N$ value = 0 }\n"
        "\t}\n"
        "\tchange_variable = { name = te_aip_n_$N$ add = 1 }\n"
        "}\n\n"
    )
    out.append(
        "# Arms the probe: the latch, the month count, the canaries. Called from the global monthly pulse in a game\n"
        "# with no human player, and from `event te_debug_ai_probe.1`.\n"
        "te_aip_arm = {\n"
        "\tset_global_variable = te_aip_on\n"
        "\tif = {\n"
        "\t\tlimit = { has_global_variable = te_aip_off }\n"
        "\t\tremove_global_variable = te_aip_off\n"
        "\t}\n"
        "\tif = {\n"
        "\t\tlimit = { NOT = { has_global_variable = te_aip_k } }\n"
        "\t\tset_global_variable = { name = te_aip_k value = 0 }\n"
        "\t\tset_global_variable = { name = te_aip_next_id value = 0 }\n"
        "\t}\n"
        f'\tdebug_log = "TE_AIP ARM v={VERSION}"\n'
        "\tordered_country = {\n"
        "\t\tlimit = { NOT = { is_country_type = decentralized } }\n"
        "\t\torder_by = gdp\n"
        "\t\tposition = 0\n"                  # the first only: with no position the walk takes every country
        "\t\tte_aip_canary = yes\n"
        "\t}\n"
        "}\n\n"
        "te_aip_disarm = {\n"
        "\tremove_global_variable = te_aip_on\n"
        "\tset_global_variable = te_aip_off\n"
        '\tdebug_log = "TE_AIP DISARM"\n'
        "}\n\n"
    )
    out.append(
        "# Each data function alone, once, for the largest economy: a line that never appears names a function the\n"
        "# engine does not have (or a form debug_log cannot print), and the X line carrying it is lost with it.\n"
        "te_aip_canary = {\n"
        '\tdebug_log = "TE_AIP CANARY start t=[THIS.GetCountry.GetTagName] y=[THIS.ScriptValue(\'te_aip_year\')|0]"\n'
        '\tdebug_log = "TE_AIP CANARY date v=[TimeKeeper.GetCurrentDate.GetString]"\n'
    )
    for _, key, accessor in DATA_FUNCTIONS:
        out.append(f'\tdebug_log = "TE_AIP CANARY {key} v=[{data_function_text(accessor)}]"\n')
    out.append('\tdebug_log = "TE_AIP CANARY end"\n}\n\n')

    out.append(
        "# The global month: arm in a game nobody plays, then count the month and stamp it with the date.\n"
        "te_aip_global_tick = {\n"
        "\tif = {\n"
        "\t\tlimit = {\n"
        "\t\t\tNOT = { has_global_variable = te_aip_on }\n"
        "\t\t\tNOT = { has_global_variable = te_aip_off }\n"
        "\t\t\tNOT = { any_country = { is_player = yes } }\n"
        "\t\t}\n"
        "\t\tte_aip_arm = yes\n"
        "\t}\n"
        "\tif = {\n"
        "\t\tlimit = { has_global_variable = te_aip_on }\n"
        "\t\tchange_global_variable = { name = te_aip_k add = 1 }\n"
        "\t\trandom_country = {\n"
        "\t\t\tdebug_log = \"TE_AIP K [THIS.ScriptValue('te_aip_k')|0] y=[THIS.ScriptValue('te_aip_year')|0]\"\n"
        "\t\t\tdebug_log = \"TE_AIP KDATE [THIS.ScriptValue('te_aip_k')|0] [TimeKeeper.GetCurrentDate.GetString]\"\n"
        "\t\t\tif = {\n"
        "\t\t\t\tlimit = { te_aip_k_phase = 1 }\n"
        f"\t\t\t\tdebug_log = \"{WORLD_LINE}\"\n"
        "\t\t\t}\n"
        "\t\t}\n"
        "\t}\n"
        "}\n\n"
        "# A serial for the country in scope, the first time the probe sees it: at its first monthly pulse, or at an\n"
        "# event before that (version 1 logged such events, and every play, with id 0).\n"
        "te_aip_ensure_id = {\n"
        "\tif = {\n"
        "\t\tlimit = { NOT = { has_variable = te_aip_id } }\n"
        "\t\tchange_global_variable = { name = te_aip_next_id add = 1 }\n"
        "\t\tset_variable = { name = te_aip_id value = global_var:te_aip_next_id }\n"
        "\t}\n"
        "}\n\n"
        "# A country's pulse (every 30 days, not each calendar month: scripting_best_practices.md,\n"
        "# `on_monthly_pulse_country` Is a 30-Day Timer): a serial on first sight, the month it is first due (this\n"
        "# year's reporting month, or next year's once that has passed), then a snapshot at the first pulse in the due\n"
        "# month or after it, which sets the next due month a calendar year on. So a country reports once in each\n"
        "# calendar year, in its month (a February one in March when its pulse misses February). A second pulse in a\n"
        "# 31-day month finds the next report a year off. Versions 1 and 2 counted twelve pulses instead (te_aip_m,\n"
        "# now unused), 360 days, so a report drifted five days earlier a year.\n"
        "te_aip_country_tick = {\n"
        "\tte_aip_ensure_id = yes\n"
        "\tif = {\n"
        "\t\tlimit = { NOT = { has_variable = te_aip_due } }\n"
        "\t\tset_variable = { name = te_aip_due value = te_aip_first_due }\n"
        "\t\tif = {\n"
        "\t\t\tlimit = { te_aip_due_in < 0 }\n"
        "\t\t\tchange_variable = { name = te_aip_due add = 12 }\n"
        "\t\t}\n"
        "\t}\n"
        "\t# The cycle's phase triggers read finance_cycle_value unguarded, so they run only once the cycle runs.\n"
        "\tif = {\n"
        "\t\tlimit = { te_banking_cycle_running = yes }\n"
        "\t\tif = {\n"
        "\t\t\tlimit = { banking_cycle_is_recession = yes }\n"
        "\t\t\tte_aip_count = { N = bank_down }\n"
        "\t\t}\n"
        "\t}\n"
        "\tif = {\n"
        "\t\tlimit = { te_aip_due_in <= 0 }\n"
        "\t\tset_variable = { name = te_aip_due value = te_aip_next_due }\n"
        "\t\tte_aip_snapshot = yes\n"
        "\t}\n"
        "}\n\n"
    )

    out.append("# The yearly snapshot of the country in scope, then its counters start again.\nte_aip_snapshot = {\n")
    for name, part in snapshot_lines(cat):
        if name[0] in POSITIONAL:
            body = ";".join(field.accessor(keyed=False) for field in part)
        else:
            body = " ".join(field.accessor() for field in part)
        out.append(f'\tdebug_log = "TE_AIP S {name} {LINE_HEAD} {body}"\n')
    out.append("\tte_aip_snapshot_data_functions = yes\n")
    for name in COUNTERS:
        out.append(f"\tset_variable = {{ name = te_aip_n_{name} value = 0 }}\n")
    out.append("}\n\n")

    out.append("# The interface's figures (see te_aip_canary).\n"
               "te_aip_snapshot_data_functions = {\n")
    for line in sorted({line for line, _, _ in DATA_FUNCTIONS}):
        body = " ".join(f"{key}=[{data_function_text(accessor)}]" for n, key, accessor in DATA_FUNCTIONS if n == line)
        out.append(f'\tdebug_log = "TE_AIP X {line} {LINE_HEAD} {body}"\n')
    out.append("}\n\n")

    out.append(
        "# A law's enactment as it starts, passes or fails: the law by its index (ai_probe_key.json, all_laws).\n"
        "te_aip_law_event = {\n"
        "\tte_aip_ensure_id = yes\n"
        "\tte_aip_count = { N = law_$WHAT$ }\n"
        f"\tdebug_log = \"TE_AIP E law_$WHAT$ {LINE_HEAD} {LAW_FIELDS}\"\n"
        "}\n\n"
        "# An enactment's end, with how it ended (ai_probe_key.json, law_end_how) and the setbacks it could take. The\n"
        "# pass and fail hooks mark it just before (te_aip_law_how); the pass's mark stays for on_law_activated, which\n"
        "# follows the end (vanilla's 00_code_on_actions.txt), so that activation is not counted as a law set by\n"
        "# script (te_aip_law_activated). Any other mark is spent here.\n"
        "te_aip_law_end_event = {\n"
        "\tte_aip_ensure_id = yes\n"
        "\tte_aip_count = { N = law_end }\n"
        f"\tdebug_log = \"TE_AIP E law_end {LINE_HEAD} {LAW_FIELDS} "
        "how=[THIS.ScriptValue('te_aip_ev_law_how')|0] max=[THIS.ScriptValue('te_aip_ev_max_setbacks')|0]\"\n"
        "\tif = {\n"
        "\t\tlimit = {\n"
        "\t\t\thas_variable = te_aip_law_how\n"
        "\t\t\tNOT = { var:te_aip_law_how = 1 }\n"
        "\t\t}\n"
        "\t\tremove_variable = te_aip_law_how\n"
        "\t}\n"
        "}\n\n"
        "te_aip_default_event = {\n"
        "\tte_aip_ensure_id = yes\n"
        f"\tdebug_log = \"TE_AIP E $WHAT$ {LINE_HEAD} debt=[THIS.ScriptValue('te_aip_debt_scaled')|3] "
        "gold=[THIS.ScriptValue('te_aip_gold')|0] net_fixed=[THIS.ScriptValue('te_aip_net_fixed')|0]\"\n"
        "}\n\n"
        "# A finished building, counted for its owner under the first class its group falls in.\n"
        "te_aip_built_event = {\n"
        "\tsave_scope_as = te_aip_building\n"
        "\towner ?= {\n"
        "\t\tte_aip_count = { N = $WHAT$ }\n"
    )
    for i, (name, groups) in enumerate(BUILT_CLASSES):
        known = [g for g in groups if g in cat["building_groups"]]
        if not known:
            continue
        test = " ".join(f"is_building_group = {g}" for g in known)
        if len(known) > 1:
            test = f"OR = {{ {test} }}"
        word = "if" if i == 0 else "else_if"
        out.append(f"\t\t{word} = {{\n\t\t\tlimit = {{ scope:te_aip_building = {{ {test} }} }}\n"
                   f"\t\t\tte_aip_count = {{ N = built_{name} }}\n\t\t}}\n")
    out.append("\t}\n}\n")
    return "".join(out)


EVENT_VALUES = (
    "# --- read at a law event ---\n"
    "te_aip_ev_enact_chance = { value = enactment_chance }\n"
    "te_aip_ev_stall_chance = { value = stall_chance }\n"
    "te_aip_ev_setbacks = { value = enactment_setback_count }\n"
    "# Version 2, at a law's end: how it ended (ai_probe_key.json, law_end_how), and the setbacks it could take.\n"
    "te_aip_ev_law_how = {\n"
    "\tvalue = 3\n"
    "\tif = { limit = { has_variable = te_aip_law_how } value = var:te_aip_law_how }\n"
    "\telse_if = { limit = { currently_enacting_law ?= { law_is_available = no } } value = 4 }\n"
    "}\n"
    "te_aip_ev_max_setbacks = { value = max_law_enactment_setbacks }\n"
    "\n"
    "# --- version 2, read at a diplomatic play: the globals te_aip_play_started sets ---\n"
    + "".join(
        f"te_aip_ev_play_{name} = {{ value = 0 if = {{ limit = {{ has_global_variable = te_aip_play_{name} }} "
        f"value = global_var:te_aip_play_{name} }} }}\n"
        for name in ("type", "a_id", "a_rank", "b_id", "b_rank"))
    + "\n"
    "# --- version 2, the W line: the world outside the AI countries ---\n"
    "# every_country does not reach a decentralized nation (scripting_best_practices.md, Country Type Mechanics):\n"
    "# version 2 counted them with it and read 0 in every line of its first run, while the same game's\n"
    "# decentralized_law_baseline self-check, which tests any_decentralized_country, printed OK. Version 3 uses the\n"
    "# dedicated iterator, and two reads that do not depend on it: every state in the world (every_state from a\n"
    "# country scope is global), and the states of the countries every_country reaches, whose difference is the\n"
    "# land the decentralized nations hold.\n"
    "te_aip_w_countries = {\n"
    "\tvalue = 0\n"
    "\tevery_country = { limit = { NOT = { is_country_type = decentralized } } add = 1 }\n"
    "}\n"
    "te_aip_w_dn = {\n"
    "\tvalue = 0\n"
    "\tevery_decentralized_country = { add = 1 }\n"
    "}\n"
    "te_aip_w_dn_states = {\n"
    "\tvalue = 0\n"
    "\tevery_decentralized_country = { add = num_states }\n"
    "}\n"
    "te_aip_w_states = {\n"
    "\tvalue = 0\n"
    "\tevery_state = { add = 1 }\n"
    "}\n"
    "te_aip_w_c_states = {\n"
    "\tvalue = 0\n"
    "\tevery_country = { limit = { NOT = { is_country_type = decentralized } } add = num_states }\n"
    "}\n"
    "# --- version 4, the W line: the game rules the probe's fields depend on (RULES), each a 1-based index into its\n"
    "# settings (ai_probe_key.json, rules). The W line prints in the month the probe arms and once a year after,\n"
    "# so a log says which setting each year ran under (a rule can be changed in a running game).\n"
    + "".join(index("w_" + name, rule_tests(name, settings)).script_value() for name, _, settings in RULES)
)


ON_ACTIONS = HEADER + """
# Every hook is behind the latch te_aip_on, so a played game pays one global-variable test a hook and nothing else.
on_monthly_pulse = {
	on_actions = { te_aip_global_monthly }
}
te_aip_global_monthly = {
	effect = { te_aip_global_tick = yes }
}

on_monthly_pulse_country = {
	on_actions = { te_aip_country_monthly }
}
te_aip_country_monthly = {
	trigger = {
		has_global_variable = te_aip_on
		NOT = { is_country_type = decentralized }
	}
	effect = { te_aip_country_tick = yes }
}

# Root = the law's country; currently_enacting_law still holds in all four (vanilla's 00_code_on_actions.txt).
# The pass and fail hooks run just before the end hook (the first run's log: each law_pass line is followed by its
# law_end), so each marks how the enactment ended for the end hook to log (te_aip_law_end_event). A mark left from
# an earlier enactment is cleared when the next one starts.
on_law_enactment_started = {
	on_actions = { te_aip_law_started }
}
te_aip_law_started = {
	trigger = { has_global_variable = te_aip_on }
	effect = {
		if = {
			limit = { has_variable = te_aip_law_how }
			remove_variable = te_aip_law_how
		}
		te_aip_law_event = { WHAT = start }
	}
}
on_law_enactment_pass = {
	on_actions = { te_aip_law_passed }
}
te_aip_law_passed = {
	trigger = { has_global_variable = te_aip_on }
	effect = {
		set_variable = { name = te_aip_law_how value = 1 }
		te_aip_law_event = { WHAT = pass }
	}
}
# Fires only when the setbacks reach the country's maximum (vanilla's comment on the hook); none did in the first
# long run (gen_ai_probe.py, LAW_END_HOW).
on_law_enactment_fail = {
	on_actions = { te_aip_law_failed }
}
te_aip_law_failed = {
	trigger = { has_global_variable = te_aip_on }
	effect = {
		set_variable = { name = te_aip_law_how value = 2 }
		te_aip_law_event = { WHAT = fail }
	}
}
on_law_enactment_ended = {
	on_actions = { te_aip_law_ended }
}
te_aip_law_ended = {
	trigger = { has_global_variable = te_aip_on }
	effect = { te_aip_law_end_event = yes }
}

# Root = the law; owner = its country. Every activation: a passed enactment's (its end hook left the pass mark,
# taken here), or a law set any other way, counted as law_set: by script (the mod's law-consistency sweep, an
# event), a revolution, or a new country's setup. A sweep's nested activation runs this again and counts too.
on_law_activated = {
	on_actions = { te_aip_law_activated }
}
te_aip_law_activated = {
	trigger = { has_global_variable = te_aip_on }
	effect = {
		owner ?= {
			if = {
				limit = { has_variable = te_aip_law_how }
				remove_variable = te_aip_law_how
			}
			else = {
				te_aip_count = { N = law_set }
			}
		}
	}
}

# Root = the country.
on_acquired_technology = {
	on_actions = { te_aip_tech_acquired }
}
te_aip_tech_acquired = {
	trigger = { has_global_variable = te_aip_on }
	effect = { te_aip_count = { N = tech } }
}
on_country_default = {
	on_actions = { te_aip_defaulted }
}
te_aip_defaulted = {
	trigger = { has_global_variable = te_aip_on }
	effect = {
		te_aip_count = { N = default }
		te_aip_default_event = { WHAT = default }
	}
}
on_country_no_longer_default = {
	on_actions = { te_aip_default_over }
}
te_aip_default_over = {
	trigger = { has_global_variable = te_aip_on }
	effect = { te_aip_default_event = { WHAT = default_end } }
}
on_government_reformed = {
	on_actions = { te_aip_government_reformed }
}
te_aip_government_reformed = {
	trigger = { has_global_variable = te_aip_on }
	effect = { te_aip_count = { N = reform } }
}
on_company_established = {
	on_actions = { te_aip_company_established }
}
te_aip_company_established = {
	trigger = { has_global_variable = te_aip_on }
	effect = { te_aip_count = { N = company } }
}

# Root = the play; scope:initiator and scope:target are the hook's own (vanilla's comment on the on-action). A
# script value read in a debug_log line cannot see a scope (scripting_best_practices.md, `debug_log` Loc-String
# Templating Limitations), so the play's type and each side's serial and rank go through global variables set
# here, where the scopes are visible. Version 1 printed 0 for the initiator's serial.
on_diplomatic_play_started = {
	on_actions = { te_aip_play_started }
}
te_aip_play_started = {
	trigger = { has_global_variable = te_aip_on }
	effect = {
		set_global_variable = { name = te_aip_play_type value = te_aip_play_type_index }
		set_global_variable = { name = te_aip_play_a_id value = 0 }
		set_global_variable = { name = te_aip_play_a_rank value = 0 }
		set_global_variable = { name = te_aip_play_b_id value = 0 }
		set_global_variable = { name = te_aip_play_b_rank value = 0 }
		scope:initiator ?= {
			te_aip_ensure_id = yes
			te_aip_count = { N = play }
			set_global_variable = { name = te_aip_play_a_id value = var:te_aip_id }
			set_global_variable = { name = te_aip_play_a_rank value = te_aip_rank }
		}
		scope:target ?= {
			te_aip_ensure_id = yes
			set_global_variable = { name = te_aip_play_b_id value = var:te_aip_id }
			set_global_variable = { name = te_aip_play_b_rank value = te_aip_rank }
		}
		debug_log = "TE_AIP E play [SCOPE.sCountry('initiator').GetTagName] [SCOPE.ScriptValue('te_aip_ev_play_a_id')|0] [SCOPE.ScriptValue('te_aip_k')|0] target=[SCOPE.sCountry('target').GetTagName] type=[SCOPE.ScriptValue('te_aip_ev_play_type')|0] rank=[SCOPE.ScriptValue('te_aip_ev_play_a_rank')|0] target_rank=[SCOPE.ScriptValue('te_aip_ev_play_b_rank')|0] target_id=[SCOPE.ScriptValue('te_aip_ev_play_b_id')|0]"
	}
}
on_diplo_play_war_start = {
	on_actions = { te_aip_war_started }
}
te_aip_war_started = {
	trigger = { has_global_variable = te_aip_on }
	effect = {
		initiator ?= { te_aip_count = { N = war } }
	}
}

# Root = the building.
on_building_built = {
	on_actions = { te_aip_building_built }
}
te_aip_building_built = {
	trigger = { has_global_variable = te_aip_on }
	effect = { te_aip_built_event = { WHAT = built } }
}
on_building_expanded = {
	on_actions = { te_aip_building_expanded }
}
te_aip_building_expanded = {
	trigger = { has_global_variable = te_aip_on }
	effect = { te_aip_built_event = { WHAT = expanded } }
}
on_production_method_changed = {
	on_actions = { te_aip_method_changed }
}
te_aip_method_changed = {
	trigger = { has_global_variable = te_aip_on }
	effect = {
		owner ?= { te_aip_count = { N = pm } }
	}
}

# Root = the institution.
on_investment_increased = {
	on_actions = { te_aip_investment_increased }
}
te_aip_investment_increased = {
	trigger = { has_global_variable = te_aip_on }
	effect = {
		owner ?= { te_aip_count = { N = inst_up } }
	}
}
on_investment_decreased = {
	on_actions = { te_aip_investment_decreased }
}
te_aip_investment_decreased = {
	trigger = { has_global_variable = te_aip_on }
	effect = {
		owner ?= { te_aip_count = { N = inst_down } }
	}
}

# Root = the colony's state.
on_colony_created = {
	on_actions = { te_aip_colony_created }
}
te_aip_colony_created = {
	trigger = { has_global_variable = te_aip_on }
	effect = {
		owner ?= { te_aip_count = { N = colony } }
	}
}
"""

EVENTS = HEADER + """#
#   event te_debug_ai_probe.1    arm the probe in a game someone is playing (a save loaded with `observe` after it)
#   event te_debug_ai_probe.2    disarm it, and keep it from arming itself again in this game
#
# Hidden and console-only: nothing in the mod fires these.
namespace = te_debug_ai_probe

te_debug_ai_probe.1 = { # REVIEWED 2026-11-15: console-only (`event te_debug_ai_probe.1`); never fired by script on purpose
	type = country_event
	hidden = yes
	immediate = {
		te_aip_arm = yes
	}
}

te_debug_ai_probe.2 = { # REVIEWED 2026-11-15: console-only (`event te_debug_ai_probe.2`); never fired by script on purpose
	type = country_event
	hidden = yes
	immediate = {
		te_aip_disarm = yes
	}
}
"""


def render_key(cat: dict) -> str:
    key = {
        "version": VERSION,
        "note": "Generated by scripts/generators/gen_ai_probe.py. An indexed field is 1-based into its list; 0 is none.",
        "ranks": RANKS,
        "country_types": COUNTRY_TYPES,
        "strategies": STRATEGIES,
        "law_groups": cat["law_groups"],
        "laws": cat["laws"],
        "all_laws": cat["all_laws"],
        "all_techs": cat["all_techs"],
        "tech_cells": {cell: len(names) for cell, names in cat["tech_cells"].items()},
        "unit_tier": cat["unit_tier"],
        "institutions": cat["institutions"],
        "building_groups": cat["building_groups"],
        "building_types": cat["building_types"],
        "counters": COUNTERS,
        "positional_groups": list(POSITIONAL),
        "lines": {name: [field.key for field in part] for name, part in snapshot_lines(cat)},
        "data_functions": [key for _, key, _ in DATA_FUNCTIONS],
        # Version 2.
        "lines_added": LINES_ADDED,
        "level_names": LEVEL_NAMES,
        "level_fields": LEVEL_FIELDS,
        "law_end_how": LAW_END_HOW,
        "play_types": cat["play_types"],
        "tech_flags": {"h_" + tech.replace("-", "_"): tech for tech in cat["tech_flags"] + cat.get("tech_flags_4", [])},
        # Each R field's unit types; for a field of one type, its group, tier and unlocking technologies.
        "unit_line": {field: members for field, members in cat["unit_line"]},
        "unit_info": {field: cat["unit_types"][members[0]] for field, members in cat["unit_line"]
                      if len(members) == 1},
        "world_fields": WORLD_FIELDS,
        # Version 3: the C2 line's bank_phase names (1-based), and how a log's snapshots are spaced: version 3
        # reports each country once a calendar year, versions 1 and 2 every twelve of its 30-day pulses.
        "bank_phases": BANK_PHASES,
        "calendar_schedule_from": 3,
        # Each T field's technologies, so that the files can be rebuilt from the key alone (catalog_from_key).
        "tech_cell_names": cat["tech_cells"],
        # The O2 line's Construction Sector fields: each cs_pm_* field's methods, and the staffing the *80 fields
        # test below (vanilla's PRODUCTION_BUILDING_LOW_EMPLOYMENT_THRESHOLD).
        "construction_methods": {name: methods for name, methods in cat["construction_methods"]},
        "ai_expansion_staffing": AI_EXPANSION_STAFFING,
        # Version 4: the technologies of the H2 line (tech_flags names them all, H1's and H2's); the street
        # lighting methods each P1 field counts; the W line's game rules, each field's settings (1-based); the
        # version each data function was added in; the construction queue's kinds; the settings under which rt_*
        # reads 0 by design.
        "tech_flags_4": cat.get("tech_flags_4", []),
        "street_lights": {name: methods for name, methods in cat.get("street_lights", [])},
        "rules": {name: {"rule": rule, "settings": settings} for name, rule, settings in RULES},
        "data_functions_added": DATA_FUNCTIONS_ADDED,
        "queue_kinds": {name: limit for name, limit in QUEUE_KINDS},
        "retooling_waived": RETOOLING_WAIVED,
        # Version 6: the fields a version took off the end of a positional line, which an older log still prints.
        "retired_tail": RETIRED_TAIL,
    }
    return json.dumps(key, indent=1) + "\n"


def plan_outputs(mod_state) -> dict[str, tuple[str, bool]]:
    """{relative path: (text, with BOM)}."""
    return render_outputs(catalog(mod_state))


def catalog_from_key(key: dict) -> dict:
    """The catalog a key was written from: what render_outputs needs, so a test can hold the committed files to
    this generator without holding them to the mod's laws and technologies of the day (the probe's catalog is
    frozen at its last run, and a law added since only goes unread)."""
    return {
        "law_groups": key["law_groups"],
        "laws": key["laws"],
        "all_laws": key["all_laws"],
        "tech_cells": key["tech_cell_names"],
        "all_techs": key["all_techs"],
        "unit_tier": key["unit_tier"],
        "building_groups": key["building_groups"],
        "building_types": key["building_types"],
        "institutions": key["institutions"],
        "unit_line": [(name, members) for name, members in key["unit_line"].items()],
        "unit_types": {key["unit_line"][name][0]: info for name, info in key["unit_info"].items()},
        "tech_flags": [t for t in key["tech_flags"].values() if t not in key.get("tech_flags_4", [])],
        "play_types": key["play_types"],
        "construction_methods": [(name, methods) for name, methods in key["construction_methods"].items()],
        "tech_flags_4": key.get("tech_flags_4", []),
        "street_lights": [(name, methods) for name, methods in key.get("street_lights", {}).items()],
    }


def render_outputs(cat: dict) -> dict[str, tuple[str, bool]]:
    return {
        VALUES_FILE: (render_values(cat) + EVENT_VALUES, True),
        EFFECTS_FILE: (render_effects(cat), True),
        ON_ACTIONS_FILE: (ON_ACTIONS, True),
        EVENTS_FILE: (EVENTS, True),
        KEY_FILE: (render_key(cat), False),
    }


def regenerate(mod_state=None, *, root: Path = ROOT, dry_run: bool = False) -> dict:
    """Write each file whose content changed; a script file gets exactly one UTF-8 BOM."""
    if mod_state is None:
        mod_state = load_state(root)
    check_rules(root)
    changed = []
    for relative, (text, bom) in plan_outputs(mod_state).items():
        target = root / relative
        expected = text.encode("utf-8-sig" if bom else "utf-8")
        if not target.exists() or target.read_bytes() != expected:
            changed.append(relative)
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(expected)
    return {"changed": bool(changed), "changed_files": changed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 if a file would change")
    args = parser.parse_args()
    result = regenerate(dry_run=args.check)
    for name in result["changed_files"]:
        print(("stale: " if args.check else "wrote: ") + name)
    if not result["changed_files"]:
        print("up to date")
    return 1 if args.check and result["changed"] else 0


if __name__ == "__main__":
    sys.exit(main())
