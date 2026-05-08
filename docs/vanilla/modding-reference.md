# Victoria 3 Modding Reference — Modifiers, Triggers & Effects

> Compressed reference for the Clausewitz engine scripting system.
> Full docs: `Documents\Paradox Interactive\Victoria 3\docs\{triggers,effects,modifiers}.log`
> Vanilla modifier type definitions: `game/common/modifier_type_definitions/`

---

## Table of Contents
1. [Modifier Patterns](#1-modifier-patterns)
2. [Triggers by Scope](#2-triggers-by-scope)
3. [Effects by Scope](#3-effects-by-scope)
4. [Common Gotchas & Missing Triggers](#4-common-gotchas--missing-triggers)
5. [Iterator Pattern Reference](#5-iterator-pattern-reference)

---

## 1. MODIFIER PATTERNS

Modifiers are numeric or boolean fields applied via `modifier = { }` blocks (in static modifiers, production methods, laws, technologies, etc.) or `add_modifier` effects.

New modifier fields must be registered in `common/modifier_type_definitions/` with a definition block specifying `color`, `percent`/`boolean`, and optionally `decimals` and `game_data`.

### Suffix Conventions
- `_add` — Flat additive bonus (e.g., `+0.1` = +10% for percent types)
- `_mult` — Multiplicative bonus (e.g., `0.15` = +15%)
- `_bool` — Boolean flag (enables/disables something)

### 1A. Country-Level Modifiers

#### Core Country One-Offs
| Modifier | Suffixes | Notes |
|----------|----------|-------|
| `country_bureaucracy` | `_add`, `_mult` | Bureaucracy capacity |
| `country_authority` | `_add`, `_mult` | Authority capacity |
| `country_influence` | `_add`, `_mult` | Diplomatic influence |
| `country_prestige` | `_add`, `_mult` | Prestige |
| `country_construction` | `_add` | Construction capacity |
| `country_max_weekly_construction_progress` | `_add` | Construction cap |
| `country_private_construction_allocation` | `_mult` | Private construction share |
| `country_construction_goods_cost` | `_mult` | Construction cost |
| `country_convoys_capacity` | `_add`, `_mult` | Convoy capacity |
| `country_minting` | `_add`, `_mult` | Gold standard income |
| `country_tax_income` | `_add` | Direct tax income |
| `country_expenses` | `_add` | Direct expenses |
| `country_loan_interest_rate` | `_add`, `_mult` | Loan interest |
| `country_government_dividends_efficiency` | `_add` | Gov dividend efficiency |
| `country_government_dividends_waste` | `_add` | Gov dividend waste |
| `country_government_wages` | `_mult` | Government wages |
| `country_military_wages` | `_mult` | Military wages |
| `country_military_goods_cost` | `_mult` | Military goods cost |
| `country_consumption_tax_cost` | `_mult` | Consumption tax cost |
| `country_infamy_generation` | `_mult` | Infamy generation |
| `country_infamy_decay` | `_mult` | Infamy decay |
| `country_prestige_from_army_power_projection` | `_mult` | Prestige from army |
| `country_prestige_from_navy_power_projection` | `_mult` | Prestige from navy |
| `country_max_declared_interests` | `_add`, `_mult` | Interest slots |
| `country_diplomatic_play_maneuvers` | `_add` | Maneuvers |
| `country_diplomatic_reputation` | `_add` | Diplo reputation |
| `country_improve_relations_speed` | `_mult` | Relations speed |
| `country_tension_decay` | `_mult` | Tension decay |
| `country_weekly_innovation` | `_add`, `_mult` | Innovation |
| `country_tech_research_speed` | `_mult` | Global research speed |
| `country_tech_spread` | `_add`, `_mult` | Tech spread |
| `country_production_tech_research_speed` | `_mult` | Production tech |
| `country_military_tech_research_speed` | `_mult` | Military tech |
| `country_society_tech_research_speed` | `_mult` | Society tech |
| `country_law_enactment_time` | `_mult` | Enactment time |
| `country_law_enactment_success` | `_add` | Enactment success chance |
| `country_law_enactment_stall` | `_add`, `_mult` | Stall chance |
| `country_legitimacy_base` | `_add` | Base legitimacy |
| `country_opposition_ig_approval` | `_add` | Opposition IG approval |
| `country_radicals_from_legitimacy` | `_mult` | Radicals from legitimacy |
| `country_loyalists_from_legitimacy` | `_mult` | Loyalists from legitimacy |
| `country_revolution_progress` | `_add`, `_mult` | Revolution progress |
| `country_mass_migration_attraction` | `_mult` | Mass migration pull |
| `country_resource_discovery_chance` | `_mult` | Resource discovery |
| `country_war_exhaustion_casualties` | `_mult` | War exhaustion |
| `country_radicals_from_conquest` | `_mult` | Radicals from conquest |
| `country_institution_size_change_speed` | `_mult` | Institution change speed |
| `country_liberty_desire` | `_add` | Base liberty desire |
| `country_liberty_desire_of_subjects` | `_add` | Subject liberty desire |
| `country_subject_income_transfer` | `_mult` | Subject income transfer |

#### Parameterized Country Patterns

**Per Interest Group** (`ig_key` = `ig_armed_forces`, `ig_devout`, `ig_industrialists`, `ig_intelligentsia`, `ig_landowners`, `ig_petty_bourgeoisie`, `ig_rural_folk`, `ig_trade_unions`):
```
interest_group_{ig_key}_pol_str_mult       — Political strength multiplier
interest_group_{ig_key}_approval_add       — Approval modifier
interest_group_{ig_key}_pop_attraction_mult — Pop attraction
```

**Per Pop Type** (`pop` = `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`, `engineers`, `farmers`, `laborers`, `machinists`, `officers`, `peasants`, `shopkeepers`, `soldiers`, `slaves`):
```
country_{pop}_pol_str_mult          — Political strength (14 types)
country_{pop}_voting_power_add      — Voting power (15 types)
```

**Per Law Enactment** (for specific laws):
```
country_enactment_success_chance_law_{law_key}_add   — Law-specific success chance
country_enactment_time_law_{law_key}_mult            — Law-specific enactment time
```
Vanilla defines these for: `technocracy`, `public_schools`, `autocracy`, `oligarchy`, `single_party_state`, `anarchy`. **Custom laws can have these too** — just register the modifier type definition.

**Per Institution** (`inst` = `colonial_affairs`, `police`, `schools`, `social_security`, `health_system`, `workplace_safety`, `home_affairs`, + custom):
```
country_institution_size_change_speed_institution_{inst}_mult
country_institution_cost_institution_{inst}_mult
country_institution_{inst}_max_investment_add
```

**Per Discrimination Level** (`level` = `violent_hostility`, `cultural_erasure`, `open_prejudice`, `second_rate_citizen`, `full_acceptance`):
```
country_assimilation_{level}_mult
country_standard_of_living_{level}_add
country_political_strength_{level}_mult
country_wage_{level}_mult
country_voting_power_{level}_mult
country_radicalism_increases_{level}_mult
country_loyalism_increases_{level}_mult
country_allow_assimilation_{level}_bool
country_allow_voting_{level}_bool
country_disallow_government_work_{level}_bool
country_disallow_military_work_{level}_bool
```

**Per Culture** (~316 cultures):
```
country_{culture}_cultural_acceptance_add   — Per-culture acceptance (e.g., country_scottish_cultural_acceptance_add)
country_fervor_target_{culture}_add         — Per-culture fervor target
```

**Cultural Acceptance Trait Modifiers** (one-offs):
```
country_acceptance_primary_culture_add
country_acceptance_homeland_add
country_acceptance_not_homeland_add
country_acceptance_state_religion_add
country_acceptance_shared_heritage_trait_add / _group_add
country_acceptance_shared_language_trait_add / _group_add
country_acceptance_shared_tradition_trait_add
country_acceptance_shared_religious_trait_add / _group_add
```

**Boolean Rules** (selected useful ones):
```
country_disallow_agitator_invites_bool
country_allow_multiple_alliances_bool
country_government_buildings_protected_bool
country_disable_investment_pool_bool
country_cannot_start_law_enactment_bool
country_disallow_aggressive_plays_bool
country_bg_manufacturing_require_subsidies_bool
```

### 1B. State-Level Modifiers

#### Core State One-Offs
| Modifier | Suffixes | Notes |
|----------|----------|-------|
| `state_standard_of_living` | `_add` | Global SoL bonus |
| `state_lower_strata_standard_of_living` | `_add` | Lower strata SoL |
| `state_middle_strata_standard_of_living` | `_add` | Middle strata SoL |
| `state_upper_strata_standard_of_living` | `_add` | Upper strata SoL |
| `state_education_access` | `_add` | Education access |
| `state_construction` | `_mult` | Construction speed |
| `state_infrastructure` | `_add`, `_mult` | Infrastructure |
| `state_tax_capacity` | `_add`, `_mult` | Tax capacity |
| `state_tax_collection` | `_mult` | Tax collection |
| `state_trade_capacity` | `_add`, `_mult` | Trade capacity |
| `state_trade_advantage` | `_mult` | Trade advantage |
| `state_welfare_payments` | `_add`, `_mult` | Welfare payments |
| `state_migration_pull` | `_add`, `_mult` | Migration pull |
| `state_assimilation` | `_mult` | Assimilation rate |
| `state_conversion` | `_mult` | Conversion rate |
| `state_conscription_rate` | `_add`, `_mult` | Conscription rate |
| `state_birth_rate` | `_mult` | Birth rate |
| `state_mortality` | `_mult` | Mortality |
| `state_pollution_generation` | `_add` | Pollution |
| `state_devastation_decay` | `_mult` | Devastation decay |
| `state_urbanization_per_level` | `_add`, `_mult` | Urbanization |
| `state_turmoil_effects` | `_mult` | Turmoil impact |
| `state_pop_pol_str` | `_add`, `_mult` | Pop political strength |
| `state_pop_qualifications` | `_mult` | Pop qualifications |
| `state_colony_growth_speed` | `_mult` | Colony growth |
| `state_incorporation_speed` | `_mult` | Incorporation speed |
| `state_radicals_from_political_movements` | `_mult` | Radicals from movements |
| `state_loyalists_from_political_movements` | `_mult` | Loyalists from movements |

#### Parameterized State Patterns

**Per Harvest Condition** (8 conditions: `drought`, `flood`, `wildfire`, `extreme_winds`, `torrential_rains`, `hailstorm`, `heatwave`, `disease_outbreak`):
```
state_harvest_condition_{condition}_impact_mult
state_harvest_condition_{condition}_duration_mult
```

**Per Pop Type Mortality/Investment** (~13 pop types):
```
state_{pop}_mortality_mult
state_{pop}_investment_pool_contribution_add
state_{pop}_investment_pool_efficiency_mult
```

**Per Religion SoL** (17 religions):
```
state_{religion}_standard_of_living_add    — e.g., state_catholic_standard_of_living_add
```

**Per Culture SoL** (~316 cultures):
```
state_{culture}_standard_of_living_add     — e.g., state_scottish_standard_of_living_add
```

**Per Political Movement** (33 movement types):
```
state_pop_support_movement_{movement}_add
state_pop_support_movement_{movement}_mult
```

### 1C. Building-Level Modifiers

#### Core Building One-Offs
```
building_throughput_add              — Global throughput
building_goods_input_mult            — Global input multiplier
building_subsistence_output_add      — Subsistence output
building_mobilization_cost_mult      — Mobilization cost
building_training_rate_add / _mult   — Training rate
building_working_conditions_mult     — Working conditions
building_minimum_wage_mult           — Minimum wage impact
building_economy_of_scale_level_cap_add
```

#### Per-Building Throughput (~54 buildings):
```
building_{building_key}_throughput_add
```
Examples: `building_coal_mine_throughput_add`, `building_textile_mill_throughput_add`, `building_railway_throughput_add`, `building_steel_mill_throughput_add`

#### Per-Pop Type at Building Level:
```
building_{pop}_job_attractiveness_mult   — (14 pop types)
building_{pop}_standard_of_living_add    — (15 pop types)
building_employment_{pop}_add            — (15 pop types)
building_{pop}_shares_add                — (12 pop types)
building_{pop}_mortality_mult            — (5 pop types)
```

### 1D. Building Group Modifiers

Building groups: `bg_mining`, `bg_agriculture`, `bg_ranching`, `bg_plantations`, `bg_logging`, `bg_rubber`, `bg_fishing`, `bg_whaling`, `bg_oil_extraction`, `bg_manufacturing`, `bg_light_industry`, `bg_heavy_industry`, `bg_military_industry`, `bg_infrastructure`, `bg_construction`, `bg_subsistence_agriculture`, `bg_subsistence_ranching`, `bg_manor_houses`, `bg_trade`, `bg_government`, `bg_arts`, `bg_power`, `bg_service`, `bg_technology`

**Not all groups have all suffixes!** Check vanilla definitions to confirm which combinations exist.

```
building_group_{bg}_throughput_add                — Throughput (~12 groups)
building_group_{bg}_tax_mult                      — Tax income (~12 groups)
building_group_{bg}_mortality_mult                — Worker mortality (~12 groups)
building_group_{bg}_standard_of_living_add        — SoL bonus (~13 groups)
building_group_{bg}_employee_mult                 — Employee count (~12 groups)
building_group_{bg}_construction_efficiency_add   — Construction speed (~10 groups)
building_group_{bg}_infrastructure_usage_mult     — Infrastructure cost (~4 groups)
building_group_{bg}_unincorporated_throughput_add  — Unincorporated throughput (~5 groups)
```

**Per-Pop sub-patterns within building groups:**
```
building_group_{bg}_{pop}_mortality_mult
building_group_{bg}_{pop}_standard_of_living_add
```
Example: `building_group_bg_mining_laborers_mortality_mult`

### 1E. Goods Modifiers

```
goods_output_{good}_add    — Output bonus (all ~53 goods)
goods_output_{good}_mult   — Output multiplier (22 military/industrial goods only)
goods_input_{good}_add     — Input modifier (44 goods)
goods_input_{good}_mult    — Input multiplier (6 goods only)
```

### 1F. Military/Unit Modifiers

```
unit_offense_add / _mult               — Generic offense
unit_defense_add / _mult               — Generic defense
unit_army_offense_add / _mult          — Army-specific
unit_navy_offense_add / _mult          — Navy-specific
unit_morale_loss_add / _mult           — Morale loss
unit_morale_recovery_mult              — Morale recovery
unit_kill_rate_add                     — Kill rate
unit_recovery_rate_add                 — Recovery rate
unit_experience_gain_add / _mult       — XP gain
unit_supply_consumption_mult           — Supply consumption
unit_devastation_mult                  — Devastation caused
unit_convoy_raiding_mult               — Convoy raiding
unit_convoy_defense_mult               — Convoy defense
military_formation_movement_speed_add / _mult
military_formation_mobilization_speed_add / _mult
```

**Per terrain** (6 types: `flat`, `elevated`, `forested`, `hazardous`, `developed`, `water`):
```
unit_offense_{terrain}_add / _mult
unit_defense_{terrain}_add / _mult
```

**Per combat unit type:**
```
unit_combat_unit_type_{type}_offense_mult / _add
```

### 1G. Interest Group / Character / Power Bloc Modifiers

**IG (generic — apply to any IG):**
```
interest_group_pol_str_mult
interest_group_approval_add
interest_group_pop_attraction_mult
interest_group_in_government_approval_add
interest_group_in_opposition_approval_add
```

**Character:**
```
character_command_limit_add / _mult
character_popularity_add
character_health_add
character_advancement_speed_add / _mult
```

**Power Bloc:**
```
power_bloc_cohesion_add / _mult
power_bloc_mandate_progress_mult
power_bloc_invite_acceptance_add
power_bloc_trade_advantage_add
power_bloc_customs_union_bool
```

---

## 2. TRIGGERS BY SCOPE

### 2A. Country Scope Triggers (319 total — key ones listed)

#### Comparison/Status
```
country_rank >= rank_value:{rank}           — Compare country rank
authority >= {n}                            — Available authority
bureaucracy >= {n}                          — Available bureaucracy
army_power_projection >= {n}                — Army power
navy_power_projection >= {n}                — Navy power
gdp >= {n}                                 — GDP comparison
country_gdp_per_capita >= {n}              — GDP per capita
average_sol >= {n}                         — Average standard of living
average_sol_for_primary_cultures >= {n}    — SoL for primary cultures
average_sol_for_culture = { ... }          — SoL for specific culture
average_sol_for_religion = { ... }         — SoL for specific religion
prestige >= {n}                            — Prestige
infamy >= {n}                              — Infamy
country_population >= {n}                  — Total population
literacy_rate >= {n}                       — Literacy rate
country_has_building_type_levels = { ... } — Building levels
```

#### Boolean Checks
```
is_player = yes/no                          — Is human player
is_ai = yes/no                              — Is AI
is_at_war = yes/no                          — Currently at war
is_in_war_together = {country}              — Allied in war
is_subject = yes/no                         — Is a subject
is_subject_of = {country}                   — Subject of specific country
is_junior_in_customs_union = yes/no         — In customs union
is_revolutionary = yes/no                   — Revolutionary country
is_secessionist = yes/no                    — Secessionist country
is_mobilized = yes/no                       — Army mobilized
is_enacting_law = {law_type}               — Currently enacting law
is_country_type = {type}                    — recognized/unrecognized/etc.
is_production_method_active = { ... }       — PM active in any building
country_or_subject_owns_entire_state_region — Owns state region
country_is_in_same_power_bloc = {country}  — Same power bloc
```

#### Diplomatic
```
has_diplomatic_pact = { who = X type = Y }  — Has specific pact
has_diplomatic_relevance = {country}        — Diplomatically relevant
has_war_with = {country}                    — At war with country
is_diplomatic_play_committed_participant     — Committed to play
relations = { who = X value >= Y }          — Relations check
has_truce_with = {country}                  — Truce active
```

#### Technology & Laws
```
has_technology_researched = {tech}          — Tech researched
has_law = {law_type}                        — Law active
is_enacting_law = {law_type}               — Currently enacting
has_journal_entry = {je_type}              — JE active
```

#### Variable/Modifier
```
has_variable = {name}                       — Variable exists
has_modifier = {modifier}                   — Modifier active
has_strategy = {strategy}                   — AI strategy active
```

#### Culture & Religion
```
has_state_religion = religion:{key}         — State religion
country_has_primary_culture = cu:{key}      — Primary culture
country_average_culture_pop_acceptance = { culture = cu:{key} value >= {n} }
was_formed_from = {TAG}                     — Formed from country
```

#### Scoped Iterators (Country → Sub-scopes)
```
any_scope_state / every_scope_state / random_scope_state / ordered_scope_state
any_interest_group / every_interest_group / random_interest_group
any_scope_ally / any_rival_country / any_rivaling_country
any_subject_or_below / any_direct_subject / any_overlord_or_above
any_scope_war / any_enemy_in_war / any_cobelligerent_in_war
any_active_law / any_law
any_political_movement / any_active_party
any_company / any_scope_diplomatic_pact / any_scope_treaty
any_scope_character / any_military_formation
```

### 2B. State Scope Triggers (76 total — key ones listed)

```
state_population >= {n}                     — Population
arable_land >= {n}                          — Arable land
free_arable_land >= {n}                     — Free arable land
devastation >= {n}                          — Devastation level
turmoil >= {n}                              — Turmoil (radical fraction)
loyalty >= {n}                              — Loyalty (loyalist fraction)
market_access >= {n}                        — Market access
relative_infrastructure >= {n}              — Infrastructure ratio
incorporation_progress >= {n}              — Incorporation progress
is_incorporated = yes/no                    — Incorporated state
is_capital = yes/no                         — Capital state
is_coastal = yes/no                         — Coastal state
is_under_colonization = yes/no             — Being colonized
is_slave_state = yes/no                    — Slave state
is_split_state = yes/no                    — Split state
is_treaty_port = yes/no                    — Treaty port
is_in_revolt = yes/no                      — In revolt
is_homeland_of_country_cultures = {country} — Homeland of owner cultures
has_decree = {decree_type}                 — Decree active
has_state_trait = {trait}                   — State trait
has_claim_by = {country}                   — Claimed by
has_building_group_levels >= {n}           — Building group levels
state_has_building_type_levels = { ... }   — Specific building type levels
culture_percent_state = { culture = X value >= Y }
religion_percent_state = { culture = X value >= Y }
pop_type_percent_state = { pop_type = X value >= Y }
state_cultural_acceptance = { target = X value >= Y }
can_construct_building = {building}        — Can build
available_jobs >= {n}                       — Available jobs
state_unemployment_rate >= {n}             — Unemployment %
```

**Scoped Iterators (State → Sub-scopes):**
```
any_scope_pop / every_scope_pop / random_scope_pop / ordered_scope_pop
any_scope_building / every_scope_building / random_scope_building
```

### 2C. Pop Scope Triggers (26 total)

```
pop_acceptance >= {n}                      — Acceptance value (0-100)
  # acceptance_status_1 = 0, _2 = 20, _3 = 40, _4 = 60 (accepted threshold), _5 = 80
  # pop_acceptance < acceptance_status_4  ← "pop is discriminated"
standard_of_living >= {n}                  — SoL comparison
quality_of_life >= {n}                     — Quality of life
total_size >= {n}                          — Pop size
workforce >= {n}                           — Workforce size
wealth >= {n}                              — Pop wealth
pop_radical_fraction >= {n}               — Radical fraction
pop_loyalist_fraction >= {n}              — Loyalist fraction
is_pop_type = {type}                       — Pop type (laborers, etc.)
has_pop_culture = cu:{key}                 — Pop culture
has_pop_religion = rel:{key}              — Pop religion
has_social_class = {class}                — Social class
strata = {strata}                          — Pop strata (poor/middle/rich)
pop_has_primary_culture = yes/no          — Is primary culture
has_state_religion = yes/no               — Has state religion
is_employed = yes/no                       — Is employed
is_in_starvation = yes/no                 — In starvation
pop_employment_building = bt:{key}        — Works in building type
pop_employment_building_group = bg:{key}  — Works in building group
```

### 2D. Character Scope Triggers (32 total — key ones)

```
age >= {n}                                 — Character age (ONLY for characters, NOT countries)
has_trait = {trait}                         — Has character trait
has_role = {role}                           — Has role (general/admiral/ruler/etc.)
has_ideology = ideology:{key}             — Character ideology
has_culture = cu:{key}                     — Character culture
has_religion = rel:{key}                  — Character religion
is_female = yes/no                        — Gender check
is_character_alive = yes/no               — Alive check
is_ruler = yes/no                          — Is ruler
is_heir = yes/no                           — Is heir
character_popularity >= {n}               — Popularity
experience_level >= {n}                   — Experience level
```

### 2E. Global/Utility Triggers (no scope)

```
game_date >= {date}                        — Compare game date (e.g., 1900.1.1)
year >= {n}                                — Current year
month >= {n}                               — Current month (Jan=0, Dec=11)
global_population >= {n}                   — World population
always = yes/no                            — Constant true/false
has_variable = {name}                      — Scope has variable
has_global_variable = {name}              — Global variable exists
has_dlc_feature = {feature}               — DLC check
exists = {scope}                           — Scope target exists
is_in_list = {list}                        — In temporary list
```

**Flow Control:**
```
AND = { }           — All must be true (implicit in most blocks)
OR = { }            — Any must be true
NOT = { }           — Negate
NOR = { }           — None true (= NOT + OR)
NAND = { }          — Not all true
trigger_if = { limit = { } ... }    — Conditional trigger display
trigger_else_if = { limit = { } ... }
trigger_else = { ... }
switch = { trigger = X ... }        — Switch/case
```

### 2F. Other Scope Triggers

**Interest Group:**
```
is_in_government = yes/no                  — In government
is_being_suppressed = yes/no              — Being suppressed
is_marginal = yes/no                       — Marginal IG
is_powerful = yes/no                       — Powerful IG
ig_clout >= {n}                            — Clout share
ig_approval >= {n}                         — Approval
leader = { <character triggers> }          — Leader conditions
```

**Diplomatic Play:**
```
is_diplomatic_play_type = {type}          — Play type
initiator_is = {country}                  — Initiator country
target_is = {country}                     — Target country
```

**War:**
```
is_war_participant = { who = X role = Y }  — War participation
war_has_wargoal = { ... }                  — War goal check
```

**Building:**
```
is_building_type = bt:{key}               — Building type
is_building_group = bg:{key}              — Building group
has_active_production_method = {pm}       — PM active
occupancy >= {n}                           — Occupancy %
is_subsidized = yes/no                    — Subsidized
is_under_construction = yes/no            — Under construction
```

---

## 3. EFFECTS BY SCOPE

### 3A. Country Effects (201 total — key ones listed)

#### Economy & Resources
```
add_treasury = {n}                         — Add/remove money
add_investment_pool = {n}                  — Add to investment pool
change_infamy = {n}                        — Change infamy
change_institution_investment_level = { institution = X levels = Y }
set_tax_level = {level}                   — Set tax level
set_government_wage_level = {level}       — Set gov wages
set_military_wage_level = {level}         — Set military wages
```

#### Pops & Loyalty
```
add_radicals = { value = X ... }           — Add radicals (country-wide)
add_loyalists = { value = X ... }          — Add loyalists (country-wide)
  # Optional filters: interest_group, strata, pop_type, culture, religion
kill_population = {n}                      — Kill N individuals
kill_population_percent = {n}              — Kill % of population
```

#### Technology
```
add_technology_researched = {tech}        — Instantly research tech
add_technology_progress = { progress = X technology = Y }
add_era_researched = {era}                — Research entire era
```

#### Laws & Enactment
```
activate_law = {law_type}                  — Activate law instantly
deactivate_law = {law_type}               — Deactivate law
start_enactment = {law_type}              — Start enacting
cancel_enactment = yes                    — Cancel enactment
add_enactment_phase = {n}                 — Add enactment progress
add_enactment_setback = {n}               — Add setback
```

#### Diplomacy
```
create_diplomatic_pact = { country = X type = Y }
remove_diplomatic_pact = { country = X type = Y }
create_diplomatic_play = { ... }          — Start diplomatic play
change_relations = { who = X value = Y }  — Change relations
change_tension = { who = X value = Y }    — Change tension
create_incident = { ... }                  — Generate infamy
set_relations = { who = X value = Y }     — Set relations directly
```

#### Characters
```
create_character = { ... }                 — Create character
set_as_interest_group_leader = yes        — (in character scope)
set_ideology = ideology:{key}             — (in character scope)
set_interest_group = ig:{key}             — (in character scope)
```

#### Variables & Modifiers
```
set_variable = { name = X value = Y days = Z }  — Set variable (optionally timed)
change_variable = { name = X add/subtract/multiply/divide = Y }
remove_variable = {name}                   — Remove variable
set_global_variable = { name = X value = Y }
add_modifier = { name = X days = Y is_decaying = yes }  — Add timed modifier
remove_modifier = {modifier}              — Remove modifier
```

#### State & Territory
```
set_capital = {state}                      — Change capital
annex = {country}                          — Annex country
make_independent = yes                    — Make independent
create_country = { ... }                   — Create new country
```

#### Misc
```
add_primary_culture = cu:{key}            — Add primary culture
remove_primary_culture = cu:{key}         — Remove primary culture
set_state_religion = rel:{key}            — Change state religion
trigger_event = { id = X days = Y }       — Fire event
add_journal_entry = { type = X }          — Add journal entry
```

### 3B. State Effects (32 total)

```
add_radicals_in_state = { value = X ... }  — Add radicals in state
add_loyalists_in_state = { value = X ... } — Add loyalists in state
kill_population_in_state = {n}            — Kill pops in state
kill_population_percent_in_state = {n}    — Kill % in state
create_pop = { ... }                       — Create pop
create_building = { building = X level = Y }
start_building_construction = { building = X }
activate_building = { type = X }           — Activate building
deactivate_building = { type = X }         — Deactivate building
set_state_type = {type}                   — Set incorporated/unincorporated
set_state_owner = {country}               — Transfer state
add_acceptance = { culture = X value = Y } — Add acceptance delta
force_resource_discovery = {bg}            — Force discovery
convert_population = { ... }               — Religious conversion
```

### 3C. Pop Effects (9 total)

```
change_pop_culture = { target = cu:X value = Y }  — Change culture by %
change_pop_religion = { target = rel:X value = Y } — Change religion by %
change_poptype = {pop_type}                — Change pop type
move_pop = {state}                         — Move pop to state
set_pop_literacy = {n}                     — Set literacy
set_pop_wealth = {n}                       — Set wealth
add_pop_wealth = {n}                       — Add wealth
```

### 3D. Character Effects (28 total — key ones)

```
add_trait = {trait}                         — Add trait
remove_trait = {trait}                      — Remove trait
set_ideology = ideology:{key}             — Change ideology
set_interest_group = ig:{key}             — Change IG
set_character_as_ruler = yes              — Make ruler
kill_character = {cause}                   — Kill character
exile_character = yes                      — Exile character
add_experience = {n}                       — Add commander XP
add_character_role = {role}               — Add role
transfer_character = {country}            — Transfer to country
```

### 3E. Interest Group Effects (14 total)

```
add_ideology = {ideology}                  — Add ideology to IG
remove_ideology = {ideology}              — Remove ideology
set_ig_trait = { value = X level = Y }    — Set IG trait
add_ruling_interest_group = yes           — Add to government
remove_ruling_interest_group = yes        — Remove from government
join_revolution = yes                      — Join revolution
abandon_revolution = yes                  — Leave revolution
set_interest_group_name = {loc_key}       — Rename IG
```

### 3F. Universal Effects (no specific scope)

```
debug_log = "message"                      — Print to debug.log (EFFECT only, not trigger)
hidden_effect = { ... }                    — Effects hidden from tooltip
custom_tooltip = { text = {loc_key} }     — Custom tooltip text
random_list = { X = { ... } Y = { ... } } — Random weighted choice
if / else_if / else = { limit = { } ... } — Conditional effects
save_scope_as = {name}                     — Save scope for later reference
trigger_event = { id = X days = Y }       — Fire event
add_to_variable_list = { ... }            — Add to list variable
remove_list_variable = { ... }            — Remove from list
show_as_tooltip = { ... }                  — Show effects as tooltip only
```

---

## 4. COMMON GOTCHAS & MISSING TRIGGERS

### Things That DON'T Exist
| What you might try | What to use instead |
|---------------------|---------------------|
| `country_age` | No trigger. Use `set_variable` in `on_country_formed` with `days = 7300` (~20 years), then check `has_variable` |
| `pop_is_discriminated` | Use `pop_acceptance < acceptance_status_4` (acceptance ≥ 60 = accepted) |
| `state_cultural_acceptance_growth_mult` | Use `country_acceptance_not_homeland_add` (flat add, country scope) |
| `country_army_power_projection_mult` | `country_prestige_from_army_power_projection_mult` |
| `country_navy_power_projection_mult` | `country_prestige_from_navy_power_projection_mult` |
| `random_rival_country` (for scoping) | Use `random_country` with `limit = { has_diplomatic_pact = { who = ROOT type = rivalry } }` |
| `age` (for countries) | `age` only works in **character** scope. Use variables or `game_date` for countries |

### Acceptance Status Constants
| Constant | Value | Meaning |
|----------|-------|---------|
| `acceptance_status_1` | 0 | Fully discriminated |
| `acceptance_status_2` | 20 | Heavily discriminated |
| `acceptance_status_3` | 40 | Somewhat discriminated |
| `acceptance_status_4` | 60 | **Accepted** (discrimination threshold) |
| `acceptance_status_5` | 80 | Fully accepted |

### Duration Constants
| Constant | Approximate Value |
|----------|-------------------|
| `short_modifier_time` | ~1 year (365 days) |
| `normal_modifier_time` | ~3 years (1095 days) |
| `long_modifier_time` | ~5 years (1825 days) |

### Modifier Type Definition Template
When adding custom modifier fields, register them in `common/modifier_type_definitions/`:
```
# Percent modifier (most common)
my_custom_modifier_mult = {
    decimals = 1
    color = good          # good (green) / bad (red) / neutral (yellow)
    percent = yes
    game_data = {
        ai_value = 0
    }
}

# Boolean modifier
my_custom_bool = {
    color = bad
    boolean = yes
    game_data = {
        ai_value = 0
    }
}
```

### Localization for Custom Modifiers
Every custom modifier type needs two loc keys:
```
 my_custom_modifier_mult:0 "Display Name"
 my_custom_modifier_mult_desc:0 "Tooltip description of what this modifier does"
```

---

## 5. ITERATOR PATTERN REFERENCE

All iterators come in 4 variants: `any_` (trigger), `every_` (effect), `random_` (effect), `ordered_` (effect).

| Pattern | Available From | Iterates Over |
|---------|---------------|---------------|
| `*_scope_state` | Country | States owned by country |
| `*_scope_pop` | State | Pops in state |
| `*_scope_building` | State | Buildings in state |
| `*_interest_group` | Country | Interest groups |
| `*_scope_character` | Country | Characters |
| `*_military_formation` | Country | Military formations |
| `*_active_law` | Country | Active laws |
| `*_law` | Country | All laws |
| `*_political_movement` | Country | Political movements |
| `*_active_party` | Country | Active parties |
| `*_company` | Country | Companies |
| `*_scope_ally` | Country | Allied countries |
| `*_rival_country` | Country | Rivaled countries |
| `*_rivaling_country` | Country | Countries rivaling this one |
| `*_subject_or_below` | Country | All subjects recursively |
| `*_direct_subject` | Country | Direct subjects only |
| `*_overlord_or_above` | Country | Overlords upward |
| `*_in_hierarchy` | Country | All in hierarchy |
| `*_scope_war` | Country | Wars involved in |
| `*_enemy_in_war` | Country | War enemies |
| `*_cobelligerent_in_war` | Country | War allies |
| `*_scope_diplomatic_pact` | Country | Diplomatic pacts |
| `*_scope_treaty` | Country | Treaties |
| `*_scope_theater` | Country | Military theaters |
| `*_country` | None (global) | All countries |
| `*_character` | None (global) | All characters |
| `*_state_region` | None (global) | All state regions |
| `*_market` | None (global) | All markets |
| `*_power_bloc` | None (global) | All power blocs |
| `*_sea_node_adjacent_state` | State | Adjacent via sea |
| `*_combat_unit` | Various | Combat units |

### Iterator Syntax
```
# Trigger (any_ — returns true if at least one match)
any_scope_state = {
    count >= 2              # Optional: require N matches (or "all")
    limit = { ... }         # Optional: pre-filter (only for effects)
    <triggers>
}

# Effect (every_ / random_ / ordered_)
random_scope_state = {
    limit = { ... }         # Filter which ones to consider
    save_scope_as = name    # Save the result
    <effects>
}

ordered_scope_state = {
    limit = { ... }
    order_by = script_value # Sort by value (highest first)
    position = 0            # Pick Nth (0 = first)
    <effects>
}
```
