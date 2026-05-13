<!-- Auto-generated from triggers.log @ 2026-05-12T15:06:59+00:00; effects.log @ 2026-05-12T15:06:59+00:00. Do not hand-edit. Run POST /reload after the engine regenerates the source. -->

# Victoria 3 — Triggers & Effects Compressed Reference

*Auto-generated from 1764 trigger entries and 3059 effect entries.*
*93 iterator families, 871 standalone triggers, 369 standalone effects.*

## Reading Guide

| Symbol | Meaning |
|--------|---------|
| **Scope:** | Entity that must be current scope for this to work |
| `[cmp]` | Supports comparison operators: `<, <=, =, !=, >, >=` |
| `[yes/no]` | Boolean trigger |
| `→ type` | Target scope type for iterators / scope targets |
| **(scopes: x, y)** | Works in multiple scope types |

**Iterator pattern:** for each scope iteration, four variants exist:
- `any_X = { ... }` — **Trigger**: true if ≥1 entity matches inner triggers (supports `count = num/all`, `percent = fixed_point`)
- `every_X = { ... }` — **Effect**: runs inner effects on ALL matching entities (supports `limit = { triggers }`)
- `random_X = { ... }` — **Effect**: picks ONE random matching entity (supports `limit`, `weight`)
- `ordered_X = { ... }` — **Effect**: picks entity by sort order (supports `limit`, `order_by`, `position`, `min/max`)

**Regional iterators** (`any/every/random/ordered_(country|state|province|state_region|strategic_region)_in_<region>`) are filtered out — apply the pattern to any vanilla region.

---
## Country

### Iterators (51)

- `any/every/ordered/random_active_law` → law — Iterate through all active laws in a country   any_active_law
- `any/every/ordered/random_active_party` → party — Iterate through all active political parties in a country   any_active_party
- `any/every/ordered/random_civil_war` → civil_war — Iterate through all civil wars related to the scoped country   any_civil_war
- `any/every/ordered/random_cobelligerent_in_diplo_play` → country — Iterate through all co-belligerents of scope country in all diplomatic plays (includes wars)   any_cobelligerent_in_diplo_play
- `any/every/ordered/random_cobelligerent_in_war` → country — Iterate through all co-belligerents of scope country in all wars   any_cobelligerent_in_war
- `any/every/ordered/random_company` → company — Iterate through all companies in a country   any_company
- `any/every/ordered/random_country_strategic_region` → strategic_region — Iterate through all strategic regions containing states owned by the scoped country   any_country_strategic_region
- `any/every/ordered/random_diplomatic_catalyst` → diplomatic_catalyst — Iterate through all diplomatic catalysts in the recent memory of a country   any_diplomatic_catalyst
- `any/every/ordered/random_diplomatically_relevant_country` → country — Iterate through all diplomatically relevant countries of a country scope   any_diplomatically_relevant_country
- `any/every/ordered/random_direct_subject` → country — Any country directly below current in hierarchy   any_direct_subject
- `any/every/ordered/random_enemy_in_diplo_play` → country — Iterate through all enemies of scope country in all diplomatic plays (includes wars)   any_enemy_in_diplo_play
- `any/every/ordered/random_enemy_in_war` → country — Iterate through all enemies of scope country in all wars   any_enemy_in_war
- `any/every/ordered/random_harvest_condition` → harvest_condition (scopes: country, state, state_region, strategic_region) — Iterate through all harvest conditions affecting a state, state region, strategic region, or country   any_harvest_condition
- `any/every/ordered/random_in_hierarchy` → country — Any country in current hierarchy, including current   any_in_hierarchy
- `any/every/ordered/random_interest_group` → interest_group — Iterate through all interest groups in a country   any_interest_group
- `any/every/ordered/random_law` → law — Iterate through all laws in a country   any_law
- `any/every/ordered/random_military_formation` → military_formation (scopes: country, front, hq) — Iterate through all military formations currently present at input scope   Supported scopes: country, front, hq   any_military_formation
- `any/every/ordered/random_neighbouring_state` → state (scopes: country, state, state_region, strategic_region) — Iterate through all states neighbouring a state region   any_neighbouring_state
- `any/every/ordered/random_overlord_or_above` → country — Any country above current in hierarchy   any_overlord_or_above
- `any/every/ordered/random_political_lobby` → political_lobby (scopes: country, interest_group) — Iterate through all political lobbies in a country or interest group   any_political_lobby
- `any/every/ordered/random_political_movement` → political_movement — Iterate through all political movements in a country   any_political_movement
- `any/every/ordered/random_potential_party` → party — Iterate through all potential political parties in a country   any_potential_party
- `any/every/ordered/random_primary_culture` → culture (scopes: country, country_definition) — Primary cultures of the scoped country or country definition   any_primary_culture
- `any/every/ordered/random_rival_country` → country — Any country that is being rivaled by the country in a scope   any_rival_country
- `any/every/ordered/random_rivaling_country` → country — Any country that is rivaling the country in a scope   any_rivaling_country
- `any/every/ordered/random_scope_admiral` → character (scopes: country, front, interest_group, military_formation) — Iterate through all admirals in a: country, interestgroup, or military formation   any_scope_admiral
- `any/every/ordered/random_scope_ally` → country — Iterate through all allies to a: country   any_scope_ally
- `any/every/ordered/random_scope_army` → military_formation (scopes: country, front, hq) — Iterate through all armies currently present at input scope   Supported scopes: country, front, hq   any_scope_army
- `any/every/ordered/random_scope_building` → building (scopes: country, state) — Iterate through all buildings in a: state, country   any_scope_building
- `any/every/ordered/random_scope_character` → character (scopes: country, front, interest_group, military_formation) — Iterate through all characters in a: country, interestgroup, or front   any_scope_character
- `any/every/ordered/random_scope_culture` → culture (scopes: country, state) — Iterate through all cultures in the scope   any_scope_culture
- `any/every/ordered/random_scope_diplomatic_pact` → diplomatic_pact — Any diplomatic pact of the country in a scope   any_scope_diplomatic_pact
- `any/every/ordered/random_scope_fleet` → military_formation (scopes: country, hq) — Iterate through all fleets currently present at input scope   Supported scopes: country, hq   any_scope_fleet
- `any/every/ordered/random_scope_general` → character (scopes: country, front, interest_group, military_formation) — Iterate through all generals in a: country, interestgroup, front, or military formation   any_scope_general
- `any/every/ordered/random_scope_held_interest_marker` → interest_marker — Iterate through all interest markers held by a country   any_scope_held_interest_marker
- `any/every/ordered/random_scope_homeland_state` → state (scopes: country, culture) — Iterate through all states that are a homeland for the scoped culture, or a homeland of any primary culture of the scoped country   any_scope_homel...
- `any/every/ordered/random_scope_interest_marker` → interest_marker (scopes: country, state_region, strategic_region) — Iterate through all interest markers in a: country, strategic region, state region   any_scope_interest_marker
- `any/every/ordered/random_scope_politician` → character (scopes: country, front, interest_group, military_formation) — Iterate through all politicians in a: country or interestgroup   any_scope_politician
- `any/every/ordered/random_scope_pop` → pop (scopes: country, culture, interest_group, state) — Iterate through all pops in a: country, state, interest group, culture   any_scope_pop
- `any/every/ordered/random_scope_ship` → ship (scopes: country, military_formation) — Iterate through all ships in a country or military formation   any_scope_ship
- `any/every/ordered/random_scope_state` → state (scopes: country, front, state_region, strait, strategic_region, theater) — Iterate through all states including provinces from a: country, state_region, theater, front, or strait   any_scope_state
- `any/every/ordered/random_scope_strait` → strait (scopes: country, state) — Iterate through all straits with a land endpoint in the scoped state or country   any_scope_strait
- `any/every/ordered/random_scope_theater` → theater — Iterate through all theaters in a: country   any_scope_theater
- `any/every/ordered/random_scope_treaty` → treaty — Iterate through in force treaties binding the scoped country   any_scope_treaty
- `any/every/ordered/random_scope_violate_sovereignty_interested_parties` → country — Iterate through all countries that would be interested if country in scope has their sovereignty violated   any_scope_violate_sovereignty_intereste...
- `any/every/ordered/random_scope_violate_sovereignty_wars` → war — Iterate through all relevant wars if target country had their sovereignty violated by scoped country   any_scope_violate_sovereignty_wars
- `any/every/ordered/random_scope_war` → war — Iterate through all wars related to the scope   any_scope_war
- `any/every/ordered/random_strategic_objective` → state — Iterate through all Strategic Objective states from the scoped Country   any_strategic_objective
- `any/every/ordered/random_subject_of_subject` → country — Any country below direct subjects in hierarchy   any_subject_of_subject
- `any/every/ordered/random_subject_or_below` → country — Any country below current in hierarchy   any_subject_or_below
- `any/every/ordered/random_valid_mass_migration_culture` → culture — Lists for cultures in the scoped country that are valid for mass migration   any_valid_mass_migration_culture

### Triggers (315)

- `additional_war_exhaustion` — Compares the additional war exhaustion the scoped country has accumulated from scripted events in the target diplomatic play   additional_war_exhaustion
- `aggressive_diplomatic_plays_permitted` — True if country is independent or permitted to start their own Diplomatic Plays
- `approaching_bureaucracy_shortage` — Check if Institutions in the country will incur a Bureaucracy shortage eventually Traits: yes/no  Reads gamestate for all scopes.
- `arable_land_country` — Compare arable land in *all* states
- `army_mobilization_option_fraction` — Checks that a countries army has a certain percentage of units with a specific monbilization option   scope:country
- `army_power_projection` — Compare to a country's total army power projection    scope:example_country
- `authority` — Compares the available authority of the scoped country Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `authority_usage` — Compares the consumed authority of the scoped country Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `average_country_infrastructure` — Check average infrastructure in all states owned by scope country
- `average_incorporated_country_infrastructure` — Check average infrastructure in incorporated states owned by the scope country
- `average_sol_for_culture` — Compares the average standard of living for the target culture in the country   average_sol_for_culture
- `average_sol_for_primary_cultures` — Compare average standard of living for primary cultures Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `average_sol_for_religion` — Compares the average standard of living for the target religion in the country   average_sol_for_religion
- `average_sol_for_slaves` — Compare average standard of living for enslaved pops Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `bureaucracy` — Compares the available bureaucracy of the scoped country Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `bureaucracy_usage` — Compares the consumed bureaucracy of the scoped country Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `can_afford_diplomatic_action` — Checks if the country in scope can afford the Influence for the specified diplomatic action (pact or ongoing)   can_afford_diplomatic_action
- `can_break_diplomatic_pact` — Checks if there is a diplomatic pact of the specified type with target country that can be broken by scope country   can_break_diplomatic_pact
- `can_create_diplomatic_pact` — Checks if a diplomatic pact is valid to create with another country   can_create_diplomatic_pact
- `can_decrease_autonomy` — Check if a subject country is able to become a less autonomous subject type
- `can_establish_company` — Check if the country can establish a new company Traits: yes/no  Reads gamestate for all scopes.
- `can_form_nation` — Check if the target country is able to potentially form a nation   can_form_nation
- `can_have_as_subject` — Checks if a country can have another country as a particular type of subject   can_have_as_subject
- `can_have_subjects` — Check if the country is able to have subjects of it sown Traits: yes/no  Reads gamestate for all scopes.
- `can_increase_autonomy` — Check if a subject country is able to become a more autonomous subject type
- `can_leave_power_bloc` — Checks if the country in scope can leave its current Power Bloc (returns false if country is not in a Power Bloc)
- `can_lobbies_target` — Checks if target country is a valid target for lobbies in the scoped country   can_lobbies_target → country
- `can_own_autonomy_be_decreased` — Check if scoped country can have it's autonomy decreased
- `can_research` — True if a country can research an technology
- `can_send_diplomatic_action` — Checks if a diplomatic action is valid to send by scope country to target country   can_send_diplomatic_action
- `can_take_on_scaled_debt` — Checks if scoped country can take on a certain amount of scaled debt from another country   can_take_on_scaled_debt
- `can_transfer_subject` — Check if the target country can be transferred as a subject to the scoped country   scope:country → country
- `can_trigger_event` — Check if country can trigger the specified event
- `check_area` — Compares areas of object to another object Reads gamestate for all scopes. (scopes: country, market, province, state, state_region, strategic_region, theater)
- `construction_queue_duration` — Compares the maximum of all the very roughly approximated weeks remaining to finish the constructions in any queue:
- `construction_queue_government_duration` — Compares the very roughly approximated weeks remaining to finish the constructions in the government queue:
- `construction_queue_num_queued_government_levels` — Compares the number of government constructed building levels in the construction queue Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `construction_queue_num_queued_levels` — Compares the number of building levels in the construction queue Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `construction_queue_num_queued_private_levels` — Compares the number of privately constructed building levels in the construction queue Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `construction_queue_private_duration` — Compares the very roughly approximated weeks remaining to finish the constructions in the private queue:
- `country_army_unit_type_fraction` — Checks that a country has a certain percentage of a specific army unit type   scope:example_formation
- `country_average_cultural_acceptance` — Compares the average acceptance of a culture that is present in a country against a value   country_average_cultural_acceptance
- `country_average_culture_and_religion_pop_acceptance` — Average acceptance of country pops of a specific culture and religion.
- `country_average_culture_pop_acceptance` — Average acceptance of country pops of a specific culture.
- `country_average_religion_pop_acceptance` — Average acceptance of country pops of a specific religion.
- `country_average_religious_acceptance` — Compares the average acceptance of a religion that is present in a country against a value   country_average_religious_acceptance
- `country_can_have_mass_migration_to` — Checks if the scoped country can have mass migration to target country → country
- `country_fervor_primary_culture` — Compares with the hightest fervor of a country's primary cultures
- `country_has_building_group_levels` — Checks the sum of building levels for a building group in a country    country_has_building_group_levels
- `country_has_building_levels` — Checks the sum of building levels for a country
- `country_has_building_type_levels` — Checks the sum of building levels for a building type in a country    country_has_building_type_levels
- `country_has_building_type_monopoly` — Check if the scoped country has a monopoly of the specified building type → building_type
- `country_has_country_monopoly` — Check if the scoped country has any country monopolies Traits: yes/no  Reads gamestate for all scopes.
- `country_has_primary_culture` — Checks if a culture is one of the primary cultures in the country   country_has_primary_culture → culture
- `country_has_state_religion` — Checks if a religion is the state religion in the country   country_has_accepted_religion → religion
- `country_innovation` — Checks the amount of weekly innovation a country produces
- `country_or_subject_owns_entire_state_region` — Checks whether the scoped country or any of its subjects owns the entire specified state region
- `country_rank` — Compares a Country's Power Ranking
- `country_ship_type_fraction` — Checks that a country has a certain fraction of a specific ship type   country_ship_type_fraction
- `country_tier` — Compare tier of country tag
- `country_turmoil` — Compares the country's population weighted turmoil
- `cultural_acceptance_base` — Compares the acceptance from shared cultural traits of a culture in the scoped country against an acceptence value   cultural_acceptance_base
- `culture_percent_country` — Checks that a country's population has a certain percentage of a specific culture   scope:example_country
- `current_law_enactment_score` — Check what the scoped country's AI enactment score is for the currently enacting law Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `discriminates_religion` — Checks if the scoped country discriminates the given religion (key)   discriminates_religion
- `economic_dependence` — Compares the degree of dependence the country in scope has to the target country.
- `electoral_confidence` — Compares the electoral confidence of scope country
- `empty_agitator_slots` — Checks number of empty agitator slots in a country
- `enacting_any_law` — Checks if you're enacting any law.
- `enactment_chance` — Compares the current enactment success chance in scope country (including values from enactment modifier) Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `enactment_chance_for_law` — Compares the enactment success chance in scope country for given law (including values from enactment modifier)   enactment_chance_for_law
- `enactment_chance_for_law_without_enactment_modifier` — Compares the enactment success chance in scope country for given law but excludes values from enactment modifier   enactment_chance_for_law_without_enactment_modifier
- `enactment_chance_without_enactment_modifier` — Compares the current enactment success chance in scope country but excludes values from enactment modifier Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `enactment_phase` — Compares the current law enactment phase in scope country.
- `enactment_setback_count` — Compares the current enactment setback count in scope country.
- `enemy_contested_wargoals` — Determines the fraction of war goals that enemies in the war are currently contesting   enemy_contested_wargoals
- `enemy_occupation` — Determines the (weighted) enemy occupation score of a country
- `expanding_institution` — Checks if the institution is expanding   expanding_institution
- `fixed_expenses` — Does the country have this amount of weekly fixed expenses
- `fixed_income` — Does the country have this amount of weekly fixed income
- `gdp_ownership_ratio` — Compares the ratio of GDP the specified country owns in the scoped country   gdp_ownership_ratio
- `gdp_per_capita_ranking` — Compares a Country's GDP per Capita Ranking (position)
- `gdp_ranking` — Compares a Country's GDP Ranking (position)
- `global_country_ranking` — Compares a Country's Power Ranking (position)
- `gold_reserves` — Does the country have the required gold reserves
- `gold_reserves_limit` — Compares the country's gold reserves limit
- `goods_production_rank` — Compare to a country's production leaderboard rank of a good   "goods_production_rank(g:luxury_clothes)" < 10 Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `government_legitimacy` — Compare Legitimacy Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `government_transfer_of_power` — Checks country's government's transfer of power
- `government_wage_level` — Compares the government wage level of scoped country   government_wage_level
- `government_wage_level_value` — Compares the government wage level value of scoped country   government_wage_level_value
- `has_active_peace_deal` — True if the country is in a war where there is a proposed peace deal
- `has_any_law_commitment` — Checks if a country has a commitment to enact any law
- `has_any_naval_only_hostilities` — Check if the country has naval hostilities with any country it is not also at war with
- `has_any_secessionists_broken_out` — Check if the country has secessionists broken out Traits: yes/no  Reads gamestate for all scopes.
- `has_any_secessionists_growing` — Check if the country has any secessionists growing Traits: yes/no  Reads gamestate for all scopes.
- `has_any_strait_control` — Check if the scoped country owns a strait province with naval fortification → country
- `has_any_strait_province` — Check if the scoped country owns any strait province → country
- `has_any_subventions_on` — Check if the scoped country has any level of subventions on a goods   scope:country → goods
- `has_any_tariffs_on` — Check if the scoped country has any level of tariffs on a goods   scope:country → goods
- `has_attitude` — Checks if scoped country has a particular attitude towards another country   has_attitude
- `has_building` — True if a state/market/state region/country has a building type (scopes: country, market, state, state_region)
- `has_civil_war_from_movement_type` — Checks if a country is having a civil war started by a particular movement type → political_movement_type
- `has_claim` — Checks if country in scope has a claim on state/state region/country   has_claim
- `has_company` — Checks if a company of the specified type exists in scope country → company_type
- `has_completed_subgoal` — Checks if the scoped country has completed a certain subgoal
- `has_consumption_tax` — Checks if the country is taxing the target good. → goods
- `has_convoys_being_sunk` — Check if the country has convoys being sunk through convoy raiding Traits: yes/no  Reads gamestate for all scopes.
- `has_diplomatic_pact` — Checks if two countries have an active diplomatic pact of type   has_diplomatic_pact
- `has_diplomatic_relevance` — Checks if target country is diplomatically relevant for scope country   has_diplomatic_relevance → country
- `has_diplomats_expelled` — Checks if country in scope has recently expelled diplomats of event target → country
- `has_famine` — Check if state or country has famine (scopes: country, state)
- `has_free_government_reform` — Check if the country has a free (of radicals) government reform    has_free_government_reform
- `has_global_highest_gdp` — Checks if the scoped country has the highest GDP
- `has_global_highest_innovation` — Checks if the scoped country has the highest weekly innovation
- `has_government_clout` — Does the country's government have the necessary total Clout Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `has_government_type` — Is the country's government type as specified
- `has_healthy_economy` — Check if the country has a healthy economy Traits: yes/no  Reads gamestate for all scopes.
- `has_inactive_journal_entry` — Check if the country has at least one inactive journal entry of the specified type
- `has_institution` — Checks if scope country has a particular type of institution   has_institution
- `has_insurrectionary_interest_groups` — Check if the country has Interest Groups that are insurrectionary Traits: yes/no  Reads gamestate for all scopes.
- `has_interest_marker_in_region` — True if scope country has an interest marker in target region
- `has_journal_entry` — Check if the country has at least one active journal entry of the specified type
- `has_law` — Checks if a country has a certain law active Traits: law_type scope Reads gamestate for all scopes. → law_type
- `has_law_commitment` — Checks if a country has a commitment to enact a certain law Traits: law_type scope Reads gamestate for all scopes. → law_type
- `has_law_imposition_rights` — Checks if the scoped country has the necessary permits to demand another country enacts a certain law   has_law_imposition_rights
- `has_law_or_variant` — Checks if a country has a certain law or one its variant laws active Traits: law_type scope Reads gamestate for all scopes. → law_type
- `has_modifier` — Check if a supported scope has a certain timed modifier   Supported scopes: Country, Character, State, Building, InterestGroup, PoliticalMovement, Institution, Front   has_modifier (scopes: country, building, character, institution, interest_group, journal_entry, political_movement, power_bloc, state)
- `has_objective` — Checks if the scoped country has a certain objective type
- `has_overlapping_interests` — Checks if country in scope has an overlapping interest marker with any of target country's interests   has_overlapping_interests → country
- `has_port_country` — Check if scoped country has at least one port
- `has_possible_decisions` — Check if a country has any possible Decisions
- `has_potential_to_form_country` — Check if the target country could ever be able to form a nation   has_potential_to_form_country
- `has_power_struggle` — Checks if scope Power Bloc has a power struggle
- `has_region_stance` — Checks if the scoped country's AI has the specified stance for a strategic region   Usage:   region_stance
- `has_researchable_technology` — Check if the country has any researchable technology left.
- `has_revolution` — Check if the country has revolutionary uprising Traits: yes/no  Reads gamestate for all scopes.
- `has_ruling_interest_group` — Does the country's government include the named IG Reads gamestate for all scopes.
- `has_ruling_interest_group_count` — Does the country's government consist of the specified number of IGs Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `has_secret_goal` — Checks if scoped country has a particular secret goal towards another country   has_secret_goal
- `has_social_hierarchy` — Checks if the scoped country has adopted a specific social hierarchy   has_social_hierarchy
- `has_state_in_state_region` — Check if country has a state in the state region
- `has_strategic_adjacency` — Checks if country in scope has a strategic adjacency (direct/coastal/war goal adjacency) to target state/country   has_strategic_adjacency
- `has_strategic_land_adjacency` — Checks if country in scope has a strategic adjacency (direct land border or war goal adjacency only) to target state/country   has_strategic_adjacency
- `has_strategic_region_interest_tier` — Checks the scoped country's interest tier rank in a specific strategic region   scope:country
- `has_strategy` — Checks if country in scope has a particular AI strategy   has_strategy
- `has_subject_relation_with` — Checks if country in scope is subject or overlord of event target → country
- `has_sufficient_construction_capacity_for_investment` — Check if country has enough construction capacity to be spending all of its incoming investment pool funds.
- `has_technology_progress` — Does the country have the required progress for an technology   has_technology_progress
- `has_technology_researched` — True if a country has researched an technology   has_technology_researched
- `has_treaty_port_in_market` — Checks if the scoped country has a treaty port in target market   c:POR → market
- `has_truce_with` — Check if a country has a truce with a different target country → country
- `has_war_with` — Checks if country in scope is at war with event target → country
- `has_wasted_construction` — Check if country is wasting any of its produced construction.
- `highest_overlapping_interest_tier` — Compares the highest interest tier rank (scope country) among strategic regions where both countries have an interest.
- `highest_secession_progress` — Compares the highest secession progress of any secession movement in a given country
- `in_default` — Check if the country is currently in default Traits: yes/no  Reads gamestate for all scopes.
- `in_election_campaign` — Check if the country is in election campaign period   in_election_campaign
- `influence` — Compares the available influence of the scoped country Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `influence_usage` — Compares the consumed influence of the scoped country Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `institution_investment_level` — Compares the level of investment in an institution   institution_investment_level
- `investment_pool` — Does the country have this amount of money saved in its investment pool
- `investment_pool_gross_income` — Does the country have this amount of gross income (income before expenses) for its investment pool
- `investment_pool_net_income` — Does the country have this amount of net income (income after expenses) for its investment pool
- `is_adjacent_to_country` — Checks if country in scope is adjacent to a target country   is_adjacent_to_country → country
- `is_adjacent_to_state` — Checks if country in scope is adjacent to a target state   is_adjacent_to_state → state
- `is_ai` — True if country scope is controlled by an AI
- `is_at_war` — Check if the country is at war Traits: yes/no  Reads gamestate for all scopes.
- `is_banning_goods` — Check if a country is banning a good   is_banning_goods
- `is_considered_adjacent_due_to_wargoals` — Checks if the scoped country is considered adjacent to the target country by virtue of the scoped country having war goals that are adjacent to the target country in a committed diplomatic play   i... → country
- `is_construction_paused` — Check if construction in a state is paused.
- `is_country_alive` — Checks if the scoped country is alive, i.e.
- `is_country_type` — Checks the countrys type
- `is_diplomatic_play_ally_of` — Checks if country in scope is in a diplomatic play together with event target → country
- `is_diplomatic_play_committed_participant` — True if country is a committed participant of any diplomatic play
- `is_diplomatic_play_enemy_of` — Checks if country in scope is in a diplomatic play against event target → country
- `is_diplomatic_play_initiator` — True if country is the initiator of any diplomatic play
- `is_diplomatic_play_involved_with` — Checks if country in scope is involved in the same diplomatic play as event target → country
- `is_diplomatic_play_participant_with` — Checks if country in scope is a committed participant in the same diplomatic play as event target → country
- `is_diplomatic_play_target` — True if country is the target of any diplomatic play
- `is_diplomatic_play_undecided_participant` — True if country is a undecided participant of any diplomatic play
- `is_direct_subject_of` — Checks if country in scope is a direct subject (not subject-of-subject) of event target → country
- `is_enacting_law` — Checks if the scoped country is enacting a specific law type. → law_type
- `is_expanding_institution` — Are you expanding an institution   is_expanding_institution
- `is_forced_to_join_plays` — Checks if the scoped country is forced to join the target country's Diplomatic Plays → country
- `is_home_country_for` — Checks if a country is the home country for target country Traits: country scope Reads gamestate for all scopes. → country
- `is_immune_to_revolutions` — Checks if the country has been set to be immune to revolutions via set_immune_to_revolutions   Warning: This does not check if the country is naturally immune to revolutions due to for example bein...
- `is_in_customs_union` — Check if the country is part of a customs union Traits: yes/no  Reads gamestate for all scopes.
- `is_in_customs_union_with` — Check if the country is in a customs union with scoped country → country
- `is_in_geographic_region` — Checks if a scoped object is in a specific geographic region (scopes: country, state, state_region, strategic_region)
- `is_in_power_bloc` — Checks if the country is in a Power Bloc
- `is_in_same_power_bloc` — Checks if the scoped country is in the same power bloc as the target scoped country → country
- `is_in_war_together` — Checks if country in scope is in war on the same side as event target → country
- `is_indirect_subject_of` — Checks if country in scope is an indirect subject (subject-of-subject) of event target → country
- `is_insurrectionary` — Check if country, movement or IG is insurrectionary Traits: yes/no  Reads gamestate for all scopes. (scopes: country, interest_group, political_movement)
- `is_involved_in_journal_entry` — Check if the country is involved in a specific journal entry
- `is_junior_in_customs_union` — True if country is a junior country in a customs custom
- `is_local_country` — Checks if the scoped country is local in specified strategic region
- `is_local_player` — True if country scope is a player
- `is_losing_power_rank` — Check if the country is in the process of dropping in power ranking Traits: yes/no  Reads gamestate for all scopes.
- `is_market_reachable_for_trade` — Check if the scope country can reach the specified market scope for purposes of trade → market
- `is_mass_migration_origin` — Checks if the scoped country is the origin of mass migration
- `is_mass_migration_origin_of_culture` — Checks if the scoped country origin of mass migration of specific culture → culture
- `is_negotiating` — Check if the scoped country or interest group is currently negotiating. (scopes: country, interest_group)
- `is_not_in_geographic_region` — Checks if a scoped object is NOT in a specific geographic region (scopes: country, state, state_region, strategic_region)
- `is_owed_obligation_by` — Checks if the scoped country is owed a obligation by the target country → country
- `is_player` — True if country scope is a player
- `is_power_bloc_leader` — Checks if the country is a leader of a Power Bloc
- `is_researching_technology` — Check if the country is actively researching a tech   is_researching_technology
- `is_researching_technology_category` — Check if the country is actively researching a tech category   is_researching_technology_category
- `is_revolutionary` — Check if the country, movement or interest group is revolutionary Traits: yes/no  Reads gamestate for all scopes. (scopes: country, interest_group, political_movement)
- `is_secessionist` — Check if the country, movement or interest group is secessionist Traits: yes/no  Reads gamestate for all scopes. (scopes: country, interest_group, political_movement)
- `is_subject` — True if country is a subject
- `is_subject_of` — Checks if country in scope is subject (or subject-of-subject) of event target → country
- `is_subject_type` — Checks the country's subject type
- `is_supporting_unification_candidate` — Check if scope country is supporting a unification candidate for a specific country formation   is_supporting_unification_candidate
- `is_taxing_goods` — Check if a country is taxing a good   has_embargo
- `is_unification_candidate` — Check if scope country is a unification candidate for country tag
- `is_violating_sovereignty_of` — Check if the scoped country is violating the sovereignty of a target country → country
- `isolated_states` — Compare number of Isolated States Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `leading_producer_of` — Checks if country is producing the most of a certain good → goods
- `leads_customs_union` — Check if any other country is part of this country's customs union
- `liberty_desire` — Compare trigger for the Liberty Desire value in a scoped country.
- `liberty_desire_weekly_progress` — Compare trigger for the weekly Liberty Desire progress value in a scoped country.
- `liberty_desire_weekly_progress_from_support_independence` — Compare trigger for the weekly Liberty Desire progress value from the scoped country having their independence supported.
- `literacy_rate` — Checks if a pop, state or country has a certain amount of literacy (scopes: country, pop, state)
- `loyalist_fraction` — Compares loyalist fraction in pops in state or country, all parameters except value are optional   loyalist_fraction (scopes: country, state)
- `max_law_enactment_setbacks` — Compares to the max number of law enactment setbacks a country can suffer before the law fails Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `max_num_companies` — The limit of how many companies the scoped country is allowed to have
- `military_ship_maintenance_fulfillment` — Compares the military ship maintenance fulfillment ratio of a country
- `military_wage_level` — Compares the military wage level of scoped country   military_wage_level
- `military_wage_level_value` — Compares the military wage level value of scoped country   military_wage_level_value
- `nationalization_cost` — Compares the total cost of nationalizing all buildings in scope country owned by the government or pops of target country   nationalization_cost
- `naval_power_projection` — Compare to a country's total navy power projection    scope:example_country
- `neighbors_any_power_bloc` — Checks if the scoped country neighbors any power bloc.
- `neighbors_member_of_same_power_bloc` — Checks if the scoped country neighbors any other country belonging to the same power bloc
- `neighbors_power_bloc` — Checks if the scoped country neighbors the target power bloc. → power_bloc
- `net_fixed_income` — Does the country have this amount of income after expenses (counting only fixed income & expenses)
- `net_total_income` — Does the country have this amount of income after expenses (counting all income & expenses)
- `num_companies` — How many companies the scoped country has
- `num_diplomatic_pacts` — Compare to a country's number of diplomatic pacts of the specified type   num_diplomatic_pacts
- `num_investments_of_type` — Checks the number of buildings levels of a given type the scoped country has outside their own country.
- `num_political_lobbies` — Compare to number of political lobbies in scoped country or interest group (scopes: country, interest_group)
- `num_subjects` — Compares the number of subjects of scoped country   num_subjects
- `num_taxed_goods` — Compares the number of consumption taxed goods of scoped country   num_taxed_goods
- `number_of_claims` — The number of claims on foreign states the country has
- `number_of_possible_decisions` — The number of possible Descision a Country can take
- `overlord_can_decrease_subject_autonomy` — Check if an overlord can decrease a subject autonomy
- `owes_obligation_to` — Checks if country in scope owes a obligation to event target → country
- `owns_entire_state_region` — Check if country owns entire region
- `owns_treaty_port_in` — Does country own the treaty port in assigned state region
- `play_participant_has_war_goal_of_type_against` — Checks if scope country holds a war goal of a specific type targeting a specific country in any diplomatic play   play_participant_has_war_goal_of_type_against
- `play_side_has_war_goal_of_type_against` — Checks if any country on the same side as scope country in any diplomatic play holds a war goal of a specific type targeting a specificcountry   play_side_has_war_goal_of_type_against
- `political_strength_share` — Checks the political strength share of a pop type, religion or culture in a country or state. (scopes: country, state)
- `politically_involved_ratio` — Compares the percentage of politically involved population in a country
- `pop_type_percent_country` — Checks whether the scoped country has <percent> of its population belonging to the specified pop type   scope:example_country
- `potential_diplomatic_play_power_ratio` — Check the expected power ratio between scope country side and target country side in a potential diplomatic play   Attempts to predict which sides involved participants will take (if any) so doesn'...
- `potential_income` — Compare the potential income of the country (weekly income plus tax waste)
- `power_bloc_share_gdp` — Compare the share of GDP of the country in scope against all its Power Bloc current members, returns -1 if not in a Power Bloc
- `power_bloc_share_gdp_with` — Compare the share of GDP of the country in scope against all its Power Bloc members plus an additional country, returns -1 if not in a Power Bloc   "power_bloc_share_gdp_with(scope:country) > 0.2" ...
- `power_bloc_share_gdp_without` — Compare the share of GDP of the country in scope against all its Power Bloc members minus one of the members, returns -1 if not in a Power Bloc   "power_bloc_share_gdp_without(scope:country) > 0.2"...
- `power_bloc_share_power_projection` — Compare the share of Power Projection of the country in scope against all its Power Bloc members, returns -1 if not in a Power Bloc
- `power_bloc_share_power_projection_with` — Compare the share of Power Projection of the country in scope against all its Power Bloc members plus an additional country, returns -1 if not in a Power Bloc   "power_bloc_share_power_projection_w...
- `power_bloc_share_power_projection_without` — Compare the share of Power Projection of the country in scope against all its Power Bloc members minus one of the members, returns -1 if not in a Power Bloc   "power_bloc_share_power_projection_wit...
- `power_bloc_share_prestige` — Compare the share of Prestige of the country in scope against all its Power Bloc members, returns -1 if not in a Power Bloc
- `power_bloc_share_prestige_with` — Compare the share of Prestige of the country in scope against all its Power Bloc members plus an additional country, returns -1 if not in a Power Bloc   "power_bloc_share_prestige_with(scope:countr...
- `power_bloc_share_prestige_without` — Compare the share of Prestige of the country in scope against all its Power Bloc members minus one of the members, returns -1 if not in a Power Bloc   "power_bloc_share_prestige_without(scope:count...
- `prestige` — Compare prestige Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `primary_cultures_percent_country` — Checks that a country's population has a certain percentage of the country's primary cultures   scope:example_country
- `produced_authority` — Compares the produced authority of the scoped country Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `produced_bureaucracy` — Compares the produced bureaucracy of the scoped country Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `produced_influence` — Compares the produced influence of the scoped country Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `radical_fraction` — Compares radical fraction in pops in state or country, all parameters except value are optional   radical_fraction (scopes: country, state)
- `radical_population_fraction` — Compares the fraction of the population that are radicals in a given country
- `region_score` — Compares the aggregated AI strategy region score for the specified strategic region in country scope   Returns 0 in case the country is player controled   region_score
- `relative_authority` — Compares the unused fraction of authority for the scoped country Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `relative_bureaucracy` — Compares the unused fraction of bureaucracy for the scoped country Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `relative_influence` — Compares the unused fraction of influence for the scoped country Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `religion_percent_country` — Checks that a country's population has a certain percentage of a specific religion   scope:example_country
- `ruler_can_have_command` — Checks if the country's government type allows its ruler to have command
- `scaled_debt` — Compare value to a country's debt relative to debt ceiling
- `scaled_gold_reserves` — Compare value to a country's gold reserves relative to reserves limit
- `ship_modification_market_demand_ratio` — Goods-weighted buy/sell ratio for the construction goods of the target ship modification, evaluated against the country-scope's market.
- `should_set_wargoal` — should_set_wargoal = {
- `shrinking_institution` — Checks if the institution is shrinking   expanding_institution
- `size_weighted_lost_battles_fraction` — Determines the fraction of battles the target country has lost in the target war, weighted by manpower size of all battles in the war   size_weighted_lost_battles_fraction
- `sol_ranking` — Compares a Country's Standard of Living Ranking (position)
- `stall_chance` — Compares the current enactment stall chance in scope country (including values from enactment modifier) Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `stall_chance_for_law` — Compares the enactment stall chance in scope country for given law (including values from enactment modifier)   stall_chance_for_law
- `stall_chance_for_law_without_enactment_modifier` — Compares the enactment stall chance in scope country for given law but excludes values from enactment modifier   stall_chance_for_law_without_enactment_modifier
- `stall_chance_without_enactment_modifier` — Compares the current enactment stall chance in scope country but excludes values from enactment modifier Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `subject_can_increase_autonomy` — Check if a subject can increase its autonomy
- `supply_network_strength` — Compares the country's supply network strength (can exceed 1)
- `supply_ship_maintenance_fulfillment` — Compares the supply ship maintenance fulfillment ratio of a country
- `taking_loans` — Check if the country is currently running a weekly deficit and taking loans to compensate Traits: yes/no  Reads gamestate for all scopes.
- `tax_level` — Compares the overall tax level of scoped country   tax_level
- `tax_level_value` — Compares the overall tax level integer value of scoped country   income_tax_level_value
- `tax_waste` — Compare the tax waste of the country
- `tenure_in_current_power_bloc_days` — Compare the number of days the country in scope has been a member of their current Power Bloc
- `tenure_in_current_power_bloc_months` — Compare the number of (whole) months the country in scope has been a member of their current Power Bloc
- `tenure_in_current_power_bloc_weeks` — Compare the number of (whole) weeks the country in scope has been a member of their current Power Bloc
- `tenure_in_current_power_bloc_years` — Compare the number of (whole) years the country in scope has been a member of their current Power Bloc
- `total_expenses` — Does the country have this amount of expenses, including from temporary sources
- `total_income` — Does the country have this amount of income, including from temporary sources
- `total_population` — Compares the total population of a given country
- `total_population_including_subjects` — Compares the total population in the scope country and its subjects
- `total_population_including_subjects_share` — Compares the total population in the scope country and its subjects' share of the global population
- `total_population_share` — Compares the total population of a given country's share of the global population
- `transfer_money_gross_income` — Does the country have this amount of gross income (income before expenses) from money transfer treaties
- `transfer_money_net_income` — Does the country have this amount of net income (income after expenses) from money transfer treaties
- `war_participant_has_war_goal_of_type_against` — Checks if scope country holds a war goal of a specific type targeting a specific country in any war   war_participant_has_war_goal_of_type_against
- `war_side_has_war_goal_of_type_against` — Checks if any country on the same side as scope country in any war holds a war goal of a specific type targeting a specific country   war_side_has_war_goal_of_type_against
- `was_formed_from` — Check if a formed country previously had a specific definition   was_formed_from
- `wealth_share` — Checks the wealth political strength share of a pop type, religion or culture in a country or state. (scopes: country, state)
- `would_accept_diplomatic_action` — Checks if a country would accept a diplomatic action proposed by another country   would_accept_diplomatic_action

### Effects (117)

- `activate_law` — Activates a law for a country → law_type
- `activate_production_method` — Activates the named production method for buildings of a certain type in country/state (scopes: country, state)
- `add_banned_goods` — Adds a total ban of a good to a country   add_banned_goods → goods
- `add_change_relations_progress` — Add progress towards changing relations between two countries   add_change_relations_progress
- `add_company` — Adds company type to a country's companies → company_type
- `add_country_monopoly` — Adds a monopoly to a country scope: → building_type
- `add_culture_acceptance_modifier` — Apply a cultural acceptance modifier in the scoped country for the given culture.
- `add_electoral_confidence` — Adds x% electoral confidence to scope country
- `add_enactment_modifier` — Adds an enactment-related timed modifier effect to object in scope
- `add_enactment_phase` — Changes the current law enactment phase in scope country by an added amount.
- `add_enactment_setback` — Changes the current law enactment setback count in scope country by an added amount.
- `add_era_researched` — Add specified era as researched in a country scope
- `add_fervor_target_modifier` — Apply a fervor target modifier in the scoped country for the given culture.
- `add_investment_pool` — Directly adds money to the investment pool
- `add_involvement` — Adds involvement for the scoped country in the given strategic region   add_involvement
- `add_law_progress` — Adds x% progress to the current checkpoint of the law being passed (range is [0, 1], 0.1 means 10 percentage points)
- `add_liberty_desire` — Adds Liberty Desire to a Subject Country.
- `add_loyalists` — Adds loyalists to pops in the scoped country.
- `add_modifier` — Adds a timed modifier effect to object in scope (scopes: country, building, character, institution, interest_group, journal_entry, political_movement, power_bloc, state)
- `add_primary_culture` — Adds a culture to the primary cultures of a country → culture
- `add_radicals` — Adds radicals to pops in the scoped country.
- `add_supply_ships` — Adds number of supply ships to the scoped country
- `add_taxed_goods` — Adds consumption taxes on a good to a country   add_taxed_goods → goods
- `add_technology_progress` — Add technology progress   add_technology_progress
- `add_technology_researched` — Research the specified technology in a country scope
- `add_treasury` — Add/remove money from a country
- `annex` — Annexes a country → country
- `annex_as_civil_war` — Annexes a country with all the inheritance effects of a victorious side in a civil war → country
- `annex_with_incorporation` — Annexes a country, inheriting incorporation of their states → country
- `call_election` — Sets the next election date for country in N months   call_election
- `cancel_enactment` — Stops enacting the country's currently enacting law
- `change_infamy` — Change infamy of scope country
- `change_institution_investment_level` — Add/remove the investment level for the institution   change_institution_investment_level
- `change_relations` — Change relations between two countries   change_relations
- `change_subject_type` — Changes the subject type of the country in scope while retaining the current Liberty Desire value.
- `change_tag` — Change the tag for the scoped country   c:GBR
- `change_tension` — Change tension between two countries   change_tension
- `clear_debt` — Clear country loans = bool
- `clear_enactment_modifier` — Clears the current law enactment modifier of scope country.
- `clear_ownership_transfer_fleet` — Clears the ownership transfer fleet in the scoped country, should be done after a series of set_ship_owner_multiple
- `clear_scaled_debt` — Clears an amount of debt equal to the defined multiplier on target's max credit
- `complete_objective_subgoal` — Completes an objective subgoal   complete_objective_subgoal
- `copy_laws` — Copies the constitution of the target country scope   Warning: This stops any current enactment. → country
- `create_bidirectional_truce` — Create a bidirectional truce between two countries   create_bidirectional_truce
- `create_character` — Creates a character, any option can be omitted.
- `create_diplomatic_catalyst` — Creates a new diplomatic catalyst   create_diplomatic_catalyst
- `create_diplomatic_pact` — Create a diplomatic pact between two countries, with scope country as initiator   create_diplomatic_pact
- `create_diplomatic_play` — Create a diplomatic play with the scoped object as target   create_diplomatic_play
- `create_incident` — Creates a diplomatic incident that generates infamy, with target country as the victim   create_incident
- `create_military_formation` — Creates a military formation   create_military_formation
- `create_political_lobby` — Creates a new political lobby   create_political_lobby
- `create_political_movement` — Creates a political movement of the specified type in the country, culture/religion optional   create_political_movement
- `create_power_bloc` — Creates a power bloc with the scoped object as leader   create_power_bloc
- `create_ship` — Creates a ship in a scoped country   create_ship
- `create_unidirectional_truce` — Create a unidirectional truce for one country towards another   create_unidirectional_truce
- `deactivate_law` — Deactivates a law for a country → law_type
- `deactivate_parties` — Deactivates parties in scoped country.
- `decrease_autonomy` — Change a country's subject type to a less autonomus one
- `disable_temporary_hostilities` — Disable temporary hostilities of a given type between two countries   disable_temporary_hostilities
- `enable_temporary_hostilities` — Enable temporary hostilities between two countries for a duration   enable_temporary_hostilities
- `end_national_awakening` — Ends a cultural awakening: → culture
- `end_truce` — Ends any truce betweeen two countries → country
- `increase_autonomy` — Change a country's subject type to a more autonomus one
- `join_power_bloc` — Scoped country joins the power bloc of the target scoped country → country
- `kill_population` — Kills a number of individuals in the population in the scoped country.
- `kill_population_percent` — Kills a percentage of the population in the scoped country.
- `liberate_slaves` — Frees all slaves in the country/state (scopes: country, state)
- `liberate_slaves_in_incorporated_states` — Frees all slaves in the country's incorporated states
- `liberate_slaves_in_unincorporated_states` — Frees all slaves in the country's unincorporated states
- `make_independent` — Makes a country independent.
- `play_as` — Change which country scoped country's player will play as   play_as → country
- `recalculate_pop_ig_support` — Recalculates and updates a country's pop IG
- `regime_change` — Executes a regime change by the scope country in the target country. → country
- `remove_active_objective_subgoal` — Removes an active objective subgoal   remove_active_objective_subgoal
- `remove_banned_goods` — Removes a total ban of a good from a country   remove_banned_goods → goods
- `remove_company` — Removes company type from a country's companies → company_type
- `remove_diplomatic_pact` — Removes a diplomatic pact between two countries, with scope country as initiator   remove_diplomatic_pact
- `remove_enactment_modifier` — Removes an enactment-related timed modifier effect to object in scope
- `remove_modifier` — Removes a timed modifier effect to object in scope (scopes: country, building, character, institution, interest_group, journal_entry, political_movement, power_bloc, state)
- `remove_monopoly` — removes a monopoly in a country scope for a specific building: → building_type
- `remove_primary_culture` — Removes a culture from the primary cultures of a country → culture
- `remove_taxed_goods` — Removes consumption taxes on a good from a country   remove_taxed_goods → goods
- `seize_investment_pool` — Seize investment pool for the treasury and transfer all private construction queue elements to the government
- `set_capital` — Set capital state in a country scope
- `set_country_type` — Sets the type of country for a country, for history
- `set_diplomats_expelled` — Expels diplomats from target country in scoped country → country
- `set_electoral_confidence` — Set x% electoral confidence in scope country
- `set_export_tariff_level` — Sets export tariff level for a good in scoped country   set_export_tariff_level
- `set_government_wage_level` — Sets the government wage level of scoped country
- `set_heir` — Sets the heir of the scoped country to the character scope specified → character
- `set_immune_to_revolutions` — Makes a country immune to revolutions or removes such immunity.
- `set_import_tariff_level` — Sets import tariff level for a good in scoped country   set_import_tariff_level
- `set_institution_investment_level` — Sets the investment level for an institution   set_institution_investment_level
- `set_market_capital` — Set market capital in a country scope
- `set_military_wage_level` — Sets the military wage level of scoped country
- `set_mutual_secret_goal` — Set mutual secret AI goal for scope country and target country   set_mutual_secret_goal
- `set_next_election_date` — Set next election date for country
- `set_only_legal_party_from_ig` — Sets the only party that is legal in a country, used for single-party state law. → interest_group
- `set_owes_obligation_to` — Set whether a country owes another a obligation   set_owes_obligation
- `set_relations` — Set relations between two countries   set_relations
- `set_ruling_interest_groups` — Creates a government for the country in scope from a set of interest groups   set_ruling_interest_groups
- `set_secret_goal` — Set a secret AI goal for scope country towards another country   set_secret_goal
- `set_social_hierarchy` — Sets the social hierarchy the scoped country   set_social_hierarchy
- `set_state_religion` — Changes the state religion of the country to the specified religion → religion
- `set_strategy` — Set AI strategy for scope country   set_strategy
- `set_tax_level` — Sets the overall tax level of scoped country
- `set_tension` — Set tension between two countries   set_tension
- `start_enactment` — Starts enacting the specified law type for the country in scope → law_type
- `start_national_awakening` — Starts a cultural awakening   start_national_awakening
- `start_research_random_technology` — Scoped country starts research of any random technology they can
- `take_on_scaled_debt` — Transfers an amount of debt equal to the defined multiplier on target's max credit   take_on_scaled_debt
- `transfer_subject` — Transfers subject from another country to current scope country → country
- `try_form_government_with` — Tries to form a new govt with provided IGs, If not possible with legitimacy provided will try and add as many IGs into the govt as possible    try_form_government_with
- `unset_only_legal_party` — Returns the country to a non single-party state state, where multiple parties can exist if they are allowed by other laws
- `update_party_support` — Updates party support in scoped country.
- `validate_subsidies` — Validates subsidies across a country's buildings.
- `violate_sovereignty_join` — Target joins scoped war   violate_sovereignty_accept

---
## State

### Iterators (1)

- `any/every/ordered/random_sea_node_adjacent_state` → state — Iterate through all states that share a sea node with a state   any_sea_node_adjacent_state

### Triggers (80)

- `arable_land` — Check arable land in state
- `available_jobs` — Checks the state's number of available jobs in non-subsistence buildings
- `blockade_level` — Compare to state's blockade level
- `can_activate_production_method` — Checks if the building of a particular type in scoped state is able to active the specified production method   can_activate_production_method
- `can_construct_building` — Checks if 1 level of <building_type> can be constructed in a scoped state   can_construct_building
- `controls_treaty_port_province` — Checks if the scoped state controls the treaty port province in the state region
- `cultural_acceptance_delta` — Compare the current local delta (modification) to a culture's acceptance in the scoped state   cultural_acceptance_delta
- `culture_percent_state` — Checks that a state's population has a certain percentage of a specific culture   scope:example_state
- `devastation` — Compares the devastation of a given state
- `free_arable_land` — Check free arable land in state
- `has_assimilating_pops` — Check if a state has any pops currently in the process of assimilating.
- `has_claim_by` — Checks if a state is claimed by a country   any_state → country
- `has_converting_pops` — Check if a state has any pops currently in the process of converting.
- `has_cultural_community` — Checks if a culture has a cultural community in the scoped state.
- `has_decree` — Checks if scope state has a particular type of decree   has_decree
- `has_mobilizing_unit` — Checks if any Building in a scoped State maintains any Combat Units that are currently mobilizing
- `has_port_state` — Check if scoped state has at least one port
- `has_potential_resource` — Checks if the specificed building group is allowed in the scoped state. → building_type
- `has_state_trait` — Checks if scoped state has a certain trait
- `ig_state_pol_strength_share` — True if IG in scope has scripted political strength in state   ig_state_pol_strength_share
- `incorporation_progress` — Check incorporation progress in state
- `infrastructure` — Compares the infrastructure value of a given state (scopes: state, state_region)
- `infrastructure_delta` — Compares the infrastructure balance of a given state (scopes: state, state_region)
- `infrastructure_usage` — Compares the infrastructure usage value of a given state (scopes: state, state_region)
- `is_being_bombarded` — Checks if a state is currently being port bombarded by a hostile fleet
- `is_blockaded_by` — Checks if a state is blockaded by a country Traits: country scope Reads gamestate for all scopes. → country
- `is_capital` — Check if state is the capital of the
- `is_coastal` — Check if state borders a (non-impassable) sea region
- `is_homeland_of_country_cultures` — Checks if state is homeland of any of the target country's primary cultures   is_homeland_of_country_cultures → country
- `is_in_revolt` — Check if a state has any chance to split off into a revolutionary or seceding country
- `is_in_same_market_area` — Checks if scope state is in the same market area as target state → state
- `is_incorporated` — Check if state is
- `is_isolated_from_market` — Check if a state is isolated from its market Traits: yes/no  Reads gamestate for all scopes.
- `is_largest_state_in_region` — Check if state is the largest in the state
- `is_mass_migration_target` — Mass migration target is state.
- `is_mass_migration_target_for_culture` — Scoped state is a mass migration target for the specified culture. → culture
- `is_potential_treaty_port` — Checks if the scoped state has the potential to become a treaty port for target country → country
- `is_production_method_active` — Checks if the building of a particular type in scoped state has the specified production method active   is_production_method_active
- `is_sea_adjacent` — Check if state borders a sea region (regular or impassable)
- `is_slave_state` — Check if a state employs or has the potential to employ slaves.
- `is_split_state` — Checks if the scoped state is a split state.
- `is_strategic_objective` — Checks if the scoped State is a Strategic Objective of a Country   is_strategic_objective → country
- `is_target_of_wargoal` — Checks if state is target of any war goal in wars involving a specific country   has_war_goal → country
- `is_treaty_port` — Checks if the scoped state is a treaty port
- `is_under_colonization` — Check if state is under colonization
- `is_world_market_hub` — Check if state is a world market hub
- `loyalists` — Compares the loyalty in a given state, i.e.
- `market_access` — Checks the market access of the scoped state
- `most_prominent_revolting_interest_group` — Checks if the most prominent revolting interest group in the scoped state has the given interest group type.
- `num_cultural_communities` — Check cultural communities in state
- `num_potential_resources` — Checks the amount of the specified building type allowed in the state.
- `obstinance` — Compares state obstinance
- `pollution_generation` — Compare total pollution generation across all buildings in the state Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `pop_type_percent_state` — Checks that a state's population has a certain percentage of a specific pop type   scope:example_state
- `population_by_culture` — Compare the current population of a target culture in the scoped state   population_by_culture
- `primary_cultures_percent_state` — Checks that a state's population has a certain percentage of the country's primary cultures   scope:example_state
- `relative_infrastructure` — Compares the infrastructure to infrastructure usage of a state
- `religion_percent_state` — Checks that a state's population has a certain percentage of a specific religion   scope:example_state
- `state_average_culture_and_religion_pop_acceptance` — Average acceptance of state pops of a specific culture and religion.
- `state_average_culture_pop_acceptance` — Average acceptance of state pops of a specific culture.
- `state_average_religion_pop_acceptance` — Average acceptance of state pops of a specific religion.
- `state_cultural_acceptance` — Checks how accepted a pop of the target culture is in the scoped state    state_cultural_acceptance
- `state_exports` — Compare total units of exports from scope to target state (if set) or world state in general (if no state specified)   state_exports
- `state_has_building_group_levels` — Checks the sum of building levels for a building group in a state    state_has_building_group_levels
- `state_has_building_levels` — Checks the sum of building levels for a state
- `state_has_building_type_levels` — Checks the sum of building levels for a building type in a state    state_has_building_type_levels
- `state_has_goods_shortage` — Check if state has a shortage on any of its building inputs
- `state_has_national_awakening` — Checks if the scoped state is in a state region with an active national awakening map marker
- `state_imports` — Compare total units of imports from target to scope state   state_imports
- `state_is_eligible_as_mass_migration_target` — Check if state can receive a mass migration at all.
- `state_population` — Checks the total population of the scoped state
- `state_religious_acceptance` — Checks how accepted a pop of the given religion is in the the scoped state    state_religious_acceptance
- `state_trade` — Compare total units of goods traded between scope state and target state (if set) or world state in general (if no state specified)   state_trade
- `state_unemployment_rate` — Checks the unemployment rate (percentage) in the scoped state
- `tax_capacity` — Checks the taxation capacity of the scoped state
- `tax_capacity_usage` — Checks the taxation capacity usage of the scoped state
- `total_urbanization` — Compares the total urbanization of a given state/ntotal_urbanization > 5 Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `turmoil` — Compares the turmoil in a given state, i.e.
- `world_market_access` — Checks the world market access of the scoped state   Worldmarket_access > 0.8 Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `years_to_incorporate` — Checks how many years it would take for target country to incorporate scope state   years_to_incorporate

### Effects (34)

- `activate_building` — Activate a building in a state   activate_building
- `add_acceptance` — Adds an acceptance delta for a culture in a state   add_acceptance
- `add_cultural_community` — Adds a cultural community for the target culture in the scoped state. → culture
- `add_culture_standard_of_living_modifier` — Apply a standard of living modifier in the scoped state for the given culture.
- `add_devastation` — Add/remove devastation from a state region or a state (scopes: state, state_region)
- `add_loyalists_in_state` — Adds loyalists to pops in the scoped state.
- `add_radicals_in_state` — Adds radicals to pops in the scoped state.
- `add_religion_standard_of_living_modifier` — Apply a standard of living modifier in the scoped state for the given religion.
- `add_resource_potential` — Add a building type as a resource potential to a state region (scopes: state, state_region)
- `cede_treaty_port` — Cedes a treaty port in scope state to target country → country
- `change_resource_potential` — Change the potential max buildings of a resource in a state region. (scopes: state, state_region)
- `convert_population` — Changes X% of the different religion population to the specified religion.
- `create_building` — Creates a building in the scoped state.
- `create_mass_migration` — Initiates mass migration of a specific culture from a origin country to a scoped state   create_mass_migration
- `create_pop` — Creates a pop in the scoped state
- `deactivate_building` — Deactivate a building in a state   deactivate_building
- `force_resource_depletion` — Forces a resource depletion in state
- `force_resource_discovery` — Forces a resource discovery in state
- `kill_population_in_state` — Kills a number of individuals in the population in the scoped state.
- `kill_population_percent_in_state` — Kills a percentage of the population in the scoped state.
- `remove_building` — Remove a building in the scope state
- `remove_resource_potential` — Remove a building type from the resource potentials of a state region (scopes: state, state_region)
- `reset_hub_names` — Resets the names of all hubs in a scoped state
- `reset_state_name` — Resets the name of a scoped state
- `set_available_for_autonomous_investment` — Sets a building type as available for autonomous investment in the current scoped State → building_type
- `set_devastation` — Set devastation to a state region or state (scopes: state, state_region)
- `set_hub_name` — Sets the name of a hub in a scoped state to a localization string   set_state_name
- `set_hub_names` — Sets the names of all the hubs in a scoped state to localization strings based on the name of the state region, the type of hub and a specified suffix
- `set_state_name` — Sets the name of a scoped state to a localization string
- `set_state_owner` — Set State Owner   set_state_owner = scope → country
- `set_state_type` — Sets a state to a certain type (incorporated, unincorporated, treaty_port)
- `start_building_construction` — Start constructing a building in a scoped state as a government construction
- `start_privately_funded_building_construction` — Start constructing a building in a scoped state as a private construction
- `unset_available_for_autonomous_investment` — Sets a building type as unavailable for autonomous investment in the current scoped State → building_type

---
## State Region

### Triggers (6)

- `contains_capital_of` — Checks if scoped state region contains the capital of target tag
- `has_harvest_condition` — Check if the scoped state region has a harvest condition of type
- `is_homeland` — Checks if scoped state region is a homeland of target culture
- `is_state_region_land` — Check if the state region is on land Traits: yes/no  Reads gamestate for all scopes.
- `pollution_amount` — Compare state region pollution Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `remaining_undepleted` — Check remaining amount of resource, like gold mines in a state   remaining_undepleted

### Effects (15)

- `add_arable_land` — Add/remove arable land from a state region
- `add_claim` — Adds scoped state region as a claim for target country → country
- `add_homeland` — Adds scoped state region as Homeland for target culture → culture
- `add_pollution` — Increase/decrease pollution level in a scoped state region
- `add_state_trait` — add state trait in a scoped state region   add_state_trait
- `create_state` — creates a state in a state region
- `finish_harvest_condition` — Finish a harvest condition of type in the scoped state region   finish_harvest_condition
- `remove_claim` — Removes scoped state region as a claim for target country → country
- `remove_homeland` — Removes scoped state region as Homeland for target culture → culture
- `remove_state_trait` — remove state trait in a scoped state region   remove_state_trait
- `set_owner_of_provinces` — Gives a set of provinces in a state region to a specific country   set_owner_of_provinces
- `spawn_entity_effect` — Spawns a temporary entity at the center of the scoped state region for a number of seconds   spawn_entity_effect
- `start_earthquake_effect` — Starts an earthquake camera shake centered on the scoped state region
- `start_harvest_condition` — Start a harvest condition of type (or refresh it if already exists) in the scoped state region   start_harvest_condition
- `start_harvest_condition_with_params` — Start a harvest condition of type in scoped state region where intensity and duration(in days) are optionally provided   start_harvest_condition_with_params

---
## Pop

### Triggers (26)

- `dependents` — Compares the dependents size of the scoped pop
- `food_security` — Checks if a pop has a certain amount of food security
- `has_ongoing_assimilation` — Checks if the scoped pop has ongoing cultural assimilation
- `has_ongoing_conversion` — Checks if the scoped pop has ongoing religious conversion
- `has_pop_culture` — Checks if pop has specific culture
- `has_pop_religion` — Checks if pop has specific religion
- `has_social_class` — Checks if the scoped pop belongs to a specific social class   has_social_class
- `has_state_religion` — Check if the Pop has the state religion Traits: yes/no  Reads gamestate for all scopes.
- `is_employed` — Check if the pop is employed Traits: yes/no  Reads gamestate for all scopes.
- `is_in_mild_starvation` — Check if the pop is in mild starvation
- `is_in_severe_starvation` — Check if the pop is in severe starvation
- `is_in_starvation` — Check if the pop is in starvation (mild or severe)
- `is_pop_type` — Checks if pop is of specified type
- `pop_acceptance` — Compares the scoped pop's acceptance against an acceptence value
- `pop_employment_building` — Checks if pop is working in a specific building type
- `pop_employment_building_group` — Checks if pop is working in a specific building type
- `pop_has_primary_culture` — Checks if pop's culture is primary
- `pop_loyalist_fraction` — Compares the number of Radicals in a pop to its total size
- `pop_neutral_fraction` — Compares the number of Neutrals (not Radical, not Loyalist) in a pop to its total size
- `pop_radical_fraction` — Compares the number of Radicals in a pop to its total size
- `quality_of_life` — Compares the quality of life of the given pop
- `standard_of_living` — Compares the standard of living of a given pop
- `strata` — Checks the strata of the scoped pop
- `total_size` — Compares the total size of the scoped pop
- `wealth` — Checks if a pop has a certain amount of wealth
- `workforce` — Compares the workforce size of the scoped pop

### Effects (9)

- `add_pop_wealth` — Adds the wealth of the pop   add_pop_wealth
- `change_pop_culture` — Changes the culture of the scoped pop to a specified culture by a specified percentage   change_pop_culture
- `change_pop_religion` — Changes the religion of the scoped pop to a specified religion by a specified percentage   change_pop_religion
- `change_poptype` — Changes the type of the pop to the given type → pop_type
- `move_partial_pop` — Moves the scoped pop to the specified state (they become unemployed)
- `move_pop` — Moves the scoped pop in its entirety to the specified state (they become unemployed) → state
- `set_pop_literacy` — Sets the literacy of the pop   set_pop_literacy
- `set_pop_qualifications` — Sets the pop qualifications of the pop for the given type   set_pop_qualifications
- `set_pop_wealth` — Sets the wealth of the pop   set_pop_wealth

---
## Building

### Triggers (23)

- `building_has_goods_shortage` — Check if building has a shortage of any of its inputs
- `can_queue_building_levels` — Checks if the building's owner could queue the provided number of additional levels without hitting a level or resource potential cap
- `cash_reserves_available` — Evaluates a production building's available cash reserves
- `cash_reserves_ratio` — Evaluates a production building's available cash reserve ratio compared to its maximum   Returns 1 if the building has no maximum cash reserves
- `country_ownership_fraction` — Compares the fraction of this building's levels that are owned by a country
- `earnings` — Compare a building's current annual earnings per employee
- `fraction_of_levels_owned_by_country` — Compares the fraction of total levels of a building a country or investors in that country owns    fraction_of_levels_owned_by_country
- `has_active_production_method` — Checks if a scoped building has the specified production method active
- `has_deployed_units` — Check if a building supports any units which have been deployed outside of home HQ
- `has_employee_slots_filled` — Checks whether the amount of employees of a certain poptype are above or below a given percentage of the total amount the building can currently hire.
- `has_failed_hires` — Checks if a building failed to hire someone last week
- `is_buildable` — Check if a building is
- `is_building_group` — True if scope is a building of given group
- `is_building_type` — True if scope is a building of given type
- `is_government_funded` — Check if a building is is_government_funded
- `is_subsidized` — Check if a building is being subsidized
- `is_subsistence_building` — Check if a building is a subsistence building
- `is_under_construction` — Checks if building is under construction
- `levels_owned_by_country` — Compares how many levels a country or investors in that country own in a building    levels_owned_by_country
- `occupancy` — Evaluates a building's current occupancy
- `private_ownership_fraction` — Compares the fraction of this building's levels that are privately owned
- `self_ownership_fraction` — Compares the fraction of this building's levels that are owned by the building itself
- `weekly_profit` — Checks whether the profits the building has made this week are above or below a given value

### Effects (1)

- `set_subsidized` — Sets whether a building is subsidized

---
## Character

### Iterators (1)

- `any/every/ordered/random_character_role` → character_role — Iterate through all roles of the scoped character   any_character_role

### Triggers (49)

- `age` — Compares the character age
- `amendment_stance` — Compares the stance of the scoped character, movement or interest group has on the specified amendment type, assuming the amendment type has a parent law   amendment_stance (scopes: character, interest_group, political_movement)
- `can_agitate` — Check if the scope character can agitate the target country   can_agitate → country
- `character_acceptance` — Compares the acceptance of the scoped character in the target country against an acceptence value   character_acceptance
- `character_supports_political_movement` — Checks whether the scoped character supports a political movement
- `commander_is_available` — Check if a commander is not busy
- `commander_rank` — Compares the commanders rank
- `could_support_political_movement` — Check if a character could potentially support a political movement   could_support_political_movement
- `experience_level` — Compares the character experience level
- `has_commander_order` — Checks whether the scoped character is following the given order
- `has_culture` — Checks characters culture
- `has_ideology` — Check if scoped character or interest group has ideology Reads gamestate for all scopes. (scopes: character, interest_group, political_movement)
- `has_military_formation` — Checks if character has a Military Formation
- `has_religion` — Checks characters religion
- `has_role` — Checks if character has specific role
- `has_role_of_type` — Checks if character has a role of the specified archetype
- `has_template` — Checks if character was made from the specified template
- `has_trait` — Checks if character has specific trait
- `is_adult` — Check if character is an adult
- `is_advancing_on_front` — Checks if a commander is advancing on a front → front
- `is_attacker_in_battle` — Checks if a Commander or Ship is attacker in a battle (scopes: character, ship)
- `is_busy` — Check if character is busy
- `is_character_alive` — Checks if the scoped character is alive
- `is_defender_in_battle` — Checks if a Commander or Ship is defender in a battle (scopes: character, ship)
- `is_female` — Check if character is female
- `is_heir_of_own_country` — Checks whether the scoped character is the heir in the country they live in
- `is_historical` — Check if character is historical
- `is_immortal` — checks if the scoped character is immortal   scope:abbath
- `is_in_battle` — Checks if a Commander or Ship is engaged in battle (scopes: character, ship)
- `is_in_exile_pool` — Checks whether the scoped character is in the exile pool
- `is_in_void` — Check if character is in the void
- `is_interest_group_leader` — Checks if character is the leader of their interest group   is_interest_group_Leader = bool Traits: yes/no  Reads gamestate for all scopes.
- `is_interest_group_type` — Checks if Interest Group is of a certain type   Can also be used on characters directly (scopes: character, interest_group)
- `is_monarch` — Checks if character is a monarch of a country with hereditary succession
- `is_noble` — Check if character is a noble
- `is_on_front` — Checks if a character or military formation has been assigned to a Front and has arrived there (scopes: character, military_formation)
- `is_ruler_of_any_country` — Checks if character is a ruler/head of state of any country
- `is_ruler_of_other_country` — Checks if character is a ruler/head of state of a country they don't live in
- `is_ruler_of_own_country` — Checks if character is a ruler/head of state of the country they live in
- `law_enactment_stance` — Compares the stance of the scoped character, movement or interest group has about enactment of the specified law compared to the current active law in the same group Reads gamestate for all scopes. (scopes: character, interest_group, political_movement)
- `law_stance` — Compares the base stance of the scoped character, movement or interest group has about the specified law, ignoring the current active law in the same group Reads gamestate for all scopes. (scopes: character, interest_group, political_movement)
- `lifetime_piracy_income` — Compares the lifetime piracy income of a character
- `loyalty` — Compares the character loyalty
- `primary_role` — Checks if the character's primary role is the specified role
- `prominence` — Compares the character prominence
- `remaining_career_length` — Checks if the character's remaining career length meets a duration threshold.
- `trait_value` — Compares the character's total trait value
- `was_exiled` — Checks whether the scoped character was exiled
- `years_of_service` — Compares the commander's years of service

### Effects (38)

- `add_career_length` — Adds to a character's current career length in a role.
- `add_character_role` — Adds a new role to a character, works with either archetype or database role
- `add_commander_rank` — Promotes/demotes a character a given amount of military ranks
- `add_experience` — Adds an amount of experience to a commander
- `add_random_trait` — Adds a random qualifying Trait of the specified category
- `add_trait` — Add a trait to a Character
- `change_character_culture` — Changes the culture of the scoped character → culture
- `change_character_religion` — Changes the religion of the scoped character → religion
- `disinherit_character` — Strips the scoped character of their heir status in whichever countries apply.
- `exile_character` — Exile a character to the exile pool
- `free_character_from_void` — Frees a character from the void, if set to no character is deleted instead
- `kill_character` — Kill a character
- `place_character_in_void` — Banishes a character to the void, duration is how long character is kept before being deleted
- `remove_as_interest_group_leader` — Removes a character from position as interest group leader
- `remove_character_role` — Removes an existing role from a character, works with either archetype or database role
- `remove_trait` — Remove a trait from a Character
- `replace_character_roles` — Replaces existing role(s) from a character with another, works with either archetype or database role   replace_character_role
- `retire_character` — Retire a character
- `retire_character_if_should_be_culled` — Conditionally retire a character if it should be culled
- `set_as_adult` — Turns the scoped character into an adult if they are not one already.
- `set_as_interest_group_leader` — Sets a character as interest group leader
- `set_career_length` — Sets the career length from now for a character in a role.
- `set_character_as_executive` — Makes scope character the executive of target company   set_character_as_executive → company
- `set_character_as_ruler` — Set scoped character as ruler in their country.
- `set_character_busy_and_immortal` — Mark a character as busy and immortal or clear said mark
- `set_character_immortal` — Set scoped character as immortal.
- `set_commander_rank` — Promotes/demotes a character to a given military rank value
- `set_first_name` — Changes the first name of a character to a loc key
- `set_home_country` — Set a character's home country. → country
- `set_home_country_definition` — Set a character's home country directly to a tag, you can use this to avoid making sure that the tag exists, this makes them an exile → country_definition
- `set_home_state` — Changes the home state of the scoped character   set_home_state → state
- `set_ideology` — Changes scoped character's ideology → ideology
- `set_interest_group` — Sets the interest group of the character → interest_group
- `set_is_noble` — Sets the noble flag of the scoped character.
- `set_last_name` — Changes the last name of a character to a loc key
- `transfer_character` — Transfers current scope character to target country → country
- `transfer_to_formation` — Transfers scope character to target formation → military_formation
- `unassign_from_formation` — Unassigns the scoped commander from their formation

---
## Market

### Iterators (2)

- `any/every/ordered/random_market_goods` → market_goods — Iterate through all active (market) goods in a market   any_market_goods
- `any/every/ordered/random_scope_country` → country (scopes: market, state_region, strategic_region) — Iterate through all countries with a presence in the supported scope (currently: market, strategic region)   any_scope_country

### Triggers (15)

- `has_active_building` — True if a state has an active building type (scopes: market, state)
- `has_port_market` — Check if scoped market has at least one port
- `is_adjacent_to_market` — Checks if market in scope is adjacent to a target market   is_adjacent_to_market → market
- `market_consumption_share` — Compare fraction of scope market consumption coming from target country   market_consumption_share
- `market_exports` — Compare total units of exports from scope to target market (if set) or world market in general (if no market specified)   market_exports
- `market_exports_reliance` — Compare fraction of buy orders in scope market that are due to exports to target market (if set) or world market in general (if no market specified)   market_exports_reliance
- `market_has_goods_shortage` — Check if market has a shortage on any of its building inputs
- `market_imports` — Compare total units of imports from target to scope market   market_imports
- `market_imports_reliance` — Compare fraction of buy orders in scope market that are due to imports from target market (if set) or world market in general (if no market specified)   market_imports_reliance
- `market_number_goods_shortages` — Check how many shortages a market has on any of its building inputs
- `market_number_goods_shortages_with` — Check how many shortages a market has on any of its building inputs, plus the ones from the target country   "market_number_goods_shortages_with(scope:target) >= 2" Traits: <, <=, =, !=, >, >= Read...
- `market_number_goods_shortages_without` — Check how many shortages a market has on any of its building inputs, subtracting the ones from the target country   "market_number_goods_shortages_without(scope:target) >= 2" Traits: <, <=, =, !=, ...
- `market_production_share` — Compare fraction of scope market production coming from target country   market_production_share
- `market_trade` — Compare total units of goods traded between scope market and target market (if set) or world market in general (if no market specified)   market_trade
- `market_trade_reliance` — Compare fraction of buy and sell orders in scope market that are due to trade with target market (if set) or world market in general (if no market specified)   market_trade_reliance

---
## Market Goods

### Triggers (28)

- `country_has_local_shortage` — Whether the scoped market goods are in shortage in the target country → country
- `has_potential_supply` — Check if the market goods or state goods has a potential supply, either though local production or theoretical import Traits: yes/no  Reads gamestate for all scopes. (scopes: market_goods, state_goods)
- `is_consumed_by_government_buildings` — Check if the market goods is instrumental in running the bureaucratic machine Traits: yes/no  Reads gamestate for all scopes.
- `is_consumed_by_military_buildings` — Check if the goods is instrumental in running the war machine Traits: yes/no  Reads gamestate for all scopes.
- `is_exported_to` — Whether the scoped market goods are being exported to the target market by the local market → market
- `is_imported_from` — Whether the scoped market goods are being imported from the Target market by the local market → market
- `market_goods_buy_orders` — Checks if market goods has the specified number of buy orders
- `market_goods_cheaper` — Checks if market goods is at least the specified percentage cheaper than base price
- `market_goods_consumption` — Checks if market goods has the specified number of total consumption
- `market_goods_delta` — Checks if market has the specified goods delta (production + imports) - (consumption + exports)
- `market_goods_export_share` — Checks if market goods exports are the specified fraction of world market exports
- `market_goods_exports` — Checks if market goods has the specified number of exports
- `market_goods_has_goods_shortage` — Check if market goods has a shortage in the market
- `market_goods_import_share` — Checks if market goods imports are the specified fraction of world market imports
- `market_goods_imports` — Checks if market goods has the specified number of imports
- `market_goods_pricier` — Checks if market goods is at least the specified percentage more expensive than base price
- `market_goods_production` — Checks if market goods has the specified number of total production
- `market_goods_sell_orders` — Checks if market goods has the specified number of sell orders
- `market_goods_shortage_ratio` — Compares the shortage ratio of a market goods in its market
- `market_prestige_goods_buy_orders` — Compare the buy orders of a specific prestige good type in the market   market_prestige_goods_buy_orders
- `market_prestige_goods_consumption` — Compare the consumption value of a specific prestige good type in the market   market_prestige_goods_consumption
- `market_prestige_goods_delta` — Compare the delta (sell orders - buy orders) of a specific prestige good type in the market   market_prestige_goods_delta
- `market_prestige_goods_export_share` — Compare the world market expore share of a specific prestige good type in the market   market_prestige_goods_export_share
- `market_prestige_goods_exports` — Compare the export value of a specific prestige good type in the market   market_prestige_goods_exports
- `market_prestige_goods_import_share` — Compare the world market export share of a specific prestige good type in the market   market_prestige_goods_import_share
- `market_prestige_goods_imports` — Compare the import value of a specific prestige good type in the market   market_prestige_goods_imports
- `market_prestige_goods_production` — Compare the production value of a specific prestige good type in the market   market_prestige_goods_production
- `market_prestige_goods_sell_orders` — Compare the sell orders of a specific prestige good type in the market   market_prestige_goods_sell_orders

---
## State Goods

### Triggers (12)

- `export_advantage` — Compare to state goods export advantage
- `export_tariff_level` — Checks if state goods has a particular export tariff level set
- `import_advantage` — Compare to state goods import advantage
- `import_tariff_level` — Checks if state goods has a particular import tariff level set
- `relative_export_advantage` — Compare to state goods relative export advantage
- `relative_import_advantage` — Compare to state goodsrelative  import advantage
- `state_goods_cheaper` — Checks if state goods is at least the specified percentage cheaper than base price
- `state_goods_consumption` — Checks if state goods has the specified number of total consumption
- `state_goods_delta` — Checks if state has the specified goods delta (production - consumption)
- `state_goods_has_local_goods_shortage` — Check if state goods has a shortage in a state, but NOT in the whole market
- `state_goods_pricier` — Checks if state goods is at least the specified percentage more expensive than base price
- `state_goods_production` — Checks if state goods has the specified number of total production

### Effects (6)

- `add_exports` — Adds a multiplier of exports to the state for the scoped state goods
- `add_imports` — Adds a multiplier of imports to the state for the scoped state goods
- `remove_exports` — Removes a multiplier of exports to the state for the scoped state goods
- `remove_imports` — Removes a multiplier of imports to the state for the scoped state goods
- `set_exports` — Sets a multiplier of exports to the state for the scoped state goods
- `set_imports` — Sets a multiplier of imports to the state for the scoped state goods

---
## Interest Group

### Iterators (1)

- `any/every/ordered/random_preferred_law` → law — Iterate through all active and possible laws in an interest group's country, ordered by how much they prefer that law   any_preferred_law

### Triggers (19)

- `has_negotiated` — Checks whether the interest group has finished negotiation:
- `has_party` — True if IG scope has a party
- `ig_approval` — Compare to scoped interest group approval   Usages:
- `ig_clout` — Compare to scoped interest group's clout
- `ig_government_power_share` — Compare to scoped interest group's political strength divided by total government political strength
- `interest_group_population` — Compares population number in an interest group
- `interest_group_population_percentage` — Compares percentage of population in an interest group
- `interest_group_supports_political_movement` — Checks whether the scoped interest group supports a political movement
- `is_in_government` — True if IG scope is in the government
- `is_marginal` — True if IG scope is marginal
- `is_member_of_any_lobby` — Checks if interest group is member of any lobby
- `is_member_of_lobby` — Checks if interest group is member of a certain lobby type → political_lobby_type
- `is_member_of_party` — Checks if Interest Group is a member of target party   is_member_of_party → party
- `is_powerful` — True if IG scope is influential
- `is_same_interest_group_type` — Checks if Interest Group is of the same IG type as target → interest_group
- `is_strongest_ig_in_government` — Checks whether the scoped interest group has the most clout out of all interest groups in government
- `most_powerful_strata` — Compares an interest groups most powerful strata Reads gamestate for all scopes.
- `prefers_law` — Checks if the scoped interest group prefers the specified law to the comparison law Reads gamestate for all scopes.
- `would_sponsor_amendment` — Check if scoped IG would sponsor an amendment of a given type   would_sponsor_amendment → amendment_type

### Effects (11)

- `abandon_revolution` — Removes interest group from revolution
- `add_ideology` — Adds an ideology to scoped interest group
- `add_ruling_interest_group` — Adds interest group to government
- `finish_negotiation` — Finishes the negotiation that has started for an interest group:
- `improve_stance` — Improves the stance of an IG on the currently enacting law by the given number of steps:
- `join_revolution` — Adds interest group to ongoing revolution
- `remove_ideology` — Removes an ideology from scoped interest group
- `remove_ruling_interest_group` — Removes interest group in scope from government
- `set_has_negotiated` — Sets whether an interest group has finished negotiating:
- `set_ig_trait` — Adds a trait to the Interest Group, or replaces their current trait with the same approval level → interest_group_trait
- `set_interest_group_name` — Renames interest group to the specified loc key

---
## Political Movement

### Iterators (2)

- `any/every/ordered/random_influenced_interest_group` → interest_group — Iterate through all interest groups influenced by a political movement   any_influenced_interest_group
- `any/every/ordered/random_supporting_character` → character — Iterate through all characters that support the scoped political movement   any_supporting_character

### Triggers (14)

- `has_character_ideology` — Check if scoped political movement has character ideology Reads gamestate for all scopes.
- `has_core_ideology` — Check if scoped political movement has core ideology Reads gamestate for all scopes.
- `is_being_bolstered` — Check if scoped movement is being bolstered   is_being_bolstered
- `is_being_suppressed` — Check if scoped movement is being suppressed   is_being_suppressed
- `is_political_movement_type` — Check if a political movement is a particular type
- `movement_can_cause_obstinance` — Check if the political movement can generate obstinance in states Traits: yes/no  Reads gamestate for all scopes.
- `movement_is_causing_obstinance` — Check if the political movement is causing obstinance in any state Traits: yes/no  Reads gamestate for all scopes.
- `movement_pressure` — Compares the pressure of the scoped movement on the target IG   movement_pressure( ig:intelligentsia ) > 0.1 Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.
- `political_movement_identity_support` — Compare pop with correct culture/religion identity support of political movement
- `political_movement_military_support` — Compare military support of political movement
- `political_movement_popular_support` — Compare popular support of political movement
- `political_movement_radicalism` — Compare radicalism of political movement
- `political_movement_support` — Compare support of political movement
- `political_movement_wealth_support` — Compare wealth support of political movement

### Effects (5)

- `add_character_ideology` — Adds a character ideology to the scoped political movement
- `remove_character_ideology` — Removes a character ideology from the scoped political movement
- `set_bolstering` — Starts/stops bolstering the political movement in scope
- `set_core_ideology` — Sets the core ideology of a political movement
- `set_suppression` — Starts/stops suppressing the political movement in scope

---
## Political Lobby

### Iterators (1)

- `any/every/ordered/random_lobby_member` → interest_group — Iterate through all interest group members of a lobby   any_lobby_member

### Triggers (3)

- `appeasement` — Compares the appeasement of a political lobby.
- `is_political_lobby_type` — Checks political lobby is of a certain lobby type
- `lobby_clout` — Compare to total clout of scoped lobby's interest groups

### Effects (4)

- `add_lobby_member` — Adds an interest group as a member of scope political lobby → interest_group
- `change_appeasement` — Change appeasement of scope political lobby   change_appeasement
- `disband_political_lobby` — Disband scoped political lobby
- `remove_lobby_member` — Removes an interest group as a member of scope political lobby → interest_group

---
## Party

### Iterators (1)

- `any/every/ordered/random_member` → interest_group — Iterate through all interest group members of a party   any_member

### Triggers (5)

- `election_momentum` — Compare election momentum of the scoped party against a value
- `has_party_member` — Checks if the target interest group is a member of scope party   has_party_member → interest_group
- `is_party` — Checks if the target party is same as scoped party. → party
- `is_party_type` — Checks if the scoped party's type is the specified one
- `is_same_party_type` — Checks if Party is of the same party type as target → party

### Effects (5)

- `add_ig_to_party` — Adds target interest group to scope party   py:py_key → interest_group
- `add_momentum` — Adds momentum to a Party during a campaign perioddd_momentum = value
- `disband_party` — Removes all interest groups from the party, causing it to disband
- `remove_ig_from_party` — Removes target interest group from scope party   py:py_key → interest_group
- `set_ruling_party` — Adds all interest groups in a party to government and removes all other interest groups from the government

---
## Culture

### Triggers (23)

- `culture_can_have_mass_migration_to_country` — Checks if the scoped culture can have mass migration to target country → country
- `culture_current_fervor` — Compares the current fervor for a given culture,
- `culture_has_community_in_state` — Checks if the scoped culture has a cultural community in a state.
- `culture_has_national_awakening` — Checks if the scoped culture has an active national awakening
- `culture_national_awakening_occurred` — Checks if the scoped culture has ever had a national awakening started
- `culture_secession_progress` — Checks the culture's progress percentage towards secession in a country.
- `culture_target_fervor` — Compares the target fervor for a given culture,
- `has_cultural_obsession` — Checks if a culture has a certain goods as obsession   has_cultural_obsession
- `has_culture_graphics` — Checks if a culture has a certain culture_graphics   has_culture_graphics
- `has_discrimination_trait` — Checks if scoped culture or religion has the given discrimination trait (scopes: culture, religion)
- `has_discrimination_trait_group` — Checks if scoped culture or religion has the given discrimination trait group (scopes: culture, religion)
- `has_homeland` — Checks if scoped culture has a homeland in target state or state region
- `is_primary_culture_of` — Checks if culture is any of a country's primary cultures   is_primary_culture_of → country
- `shares_heritage_trait_group_with_any_primary_culture` — Checks if culture shares any trait group marked as 'heritage' with any of a country's primary cultures   shares_heritage_trait_group_with_any_primary_culture → country
- `shares_heritage_trait_group_with_culture` — Checks if culture shares any trait group marked as 'heritage' with another culture   shares_heritage_trait_group_with_culture → culture
- `shares_heritage_trait_with_any_primary_culture` — Checks if culture shares any trait marked as 'heritage' with any of a country's primary cultures   shares_heritage_trait_with_any_primary_culture → country
- `shares_heritage_trait_with_culture` — Checks if culture shares any trait marked as 'heritage' with another culture   shares_heritage_trait_with_culture → culture
- `shares_language_trait_group_with_any_primary_culture` — Checks if culture shares any trait group marked as 'language' with any of a country's primary cultures   shares_language_trait_group_with_any_primary_culture → country
- `shares_language_trait_group_with_culture` — Checks if culture shares any trait group marked as 'language' with another culture   shares_language_trait_group_with_culture → culture
- `shares_language_trait_with_any_primary_culture` — Checks if culture shares any trait marked as 'language' with any of a country's primary cultures   shares_language_trait_with_any_primary_culture → country
- `shares_language_trait_with_culture` — Checks if culture shares any trait marked as 'language' with another culture   shares_language_trait_with_culture → culture
- `shares_tradition_trait_with_any_primary_culture` — Checks if culture shares any trait marked as 'tradition' with any of a country's primary cultures   shares_tradition_trait_with_any_primary_culture → country
- `shares_tradition_trait_with_culture` — Checks if culture shares any trait marked as 'tradition' with another culture   shares_tradition_trait_with_culture → culture

### Effects (10)

- `add_cultural_community_in_state` — Adds a cultural community for the scoped culture in the target state. → state
- `add_cultural_obsession` — Adds a new obsession to the culture in scope
- `add_cultural_taboo` — Adds a new taboo to the culture in scope
- `add_fervor` — Adds fervor to a scoped culture
- `add_tradition_trait` — Adds a new tradition trait to the culture in scope
- `remove_cultural_obsession` — Removes a new obsession to the culture in scope
- `remove_cultural_taboo` — Removes a taboo from the culture in scope
- `remove_tradition_trait` — Removes an existing tradition trait from the culture in scope
- `set_fervor` — Sets the fervor of a scoped culture
- `set_name_format` — Sets the name format of a scoped culture

---
## Religion

### Triggers (6)

- `has_religious_taboo` — Checks if a religion has a certain goods as taboo   has_religious_taboo
- `is_state_religion` — Checks if the religion is the state religion in a country   is_accepted_religion → country
- `shares_heritage_trait_group_with_religion` — Checks if the religion shares any heritage trait group with another religion   shares_heritage_trait_with_religion → religion
- `shares_heritage_trait_group_with_state_religion` — Checks if the religion shares any heritage trait group with a country's state religion   shares_heritage_trait_group_with_state_religion → country
- `shares_heritage_trait_with_religion` — Checks if the religion shares any heritage trait with another religion   shares_heritage_trait_with_religion → religion
- `shares_heritage_trait_with_state_religion` — Checks if the religion shares any heritage trait with a country's religion   shares_heritage_trait_with_state_religion → country

---
## War

### Iterators (2)

- `any/every/ordered/random_scope_front` → front — Iterate through all Fronts related to the scoped War   any_scope_front
- `any/every/ordered/random_war_participant` → country — Iterate through all participants in a war   any_war_participant

### Triggers (15)

- `has_war_exhaustion` — Checks the war exhaustion of the target country in the scoped war   has_war_exhaustion
- `has_war_goal` — Checks if war has a certain war goal type
- `has_war_support` — Checks the war support of the target country in the scoped war   has_war_support
- `is_holder_of_wargoal_in_war` — Checks if the specified country is the holder of any war goal in the scoped war   is_holder_of_wargoal_in_war → country
- `is_target_of_wargoal_in_war` — Checks if the specified country is the target of any war goal in the scoped war   is_target_of_wargoal_in_war → country
- `is_war_participant` — Check if the target country is participant in a war Traits: country scope Reads gamestate for all scopes. → country
- `is_warleader` — Check if country is warleader in war Traits: country scope Reads gamestate for all scopes. → country
- `num_casualties` — Checks the number of total casualties in the scoped war
- `num_country_casualties` — Checks the number of casualties for the target country in the scoped war   num_country_casualties
- `num_country_dead` — Checks the number of dead for the target country in the scoped war   num_country_dead
- `num_country_wounded` — Checks the number of wounded for the target country in the scoped war   num_country_wounded
- `num_dead` — Checks the number of total dead in the scoped war
- `num_wounded` — Checks the number of total wounded in the scoped war
- `war_exhaustion_from_acceptance_of_dead` — Determines the war exhaustion a country gets from their degree of cultural acceptance of manpower killed in the war, regardless of what side they were on   war_exhaustion_from_acceptance_of_dead
- `war_has_active_peace_deal` — True if the war has a proposed peace deal

### Effects (3)

- `add_war_exhaustion` — Adds war exhaustion to the target country in the scoped war.
- `add_war_war_support` — Adds war support to the target country in the scoped war.
- `join_war` — Makes target join a scoped war in a specific side.

---
## Diplomatic Play

### Iterators (3)

- `any/every/ordered/random_scope_initiator_ally` → country — Iterate through all allies to an initiator in a: diplomatic play   any_scope_initiator_ally
- `any/every/ordered/random_scope_play_involved` → country — Iterate through all involved in a: diplomatic play   any_scope_play_involved
- `any/every/ordered/random_scope_target_ally` → country — Iterate through all allies to a target in a: diplomatic play   any_scope_target_ally

### Triggers (6)

- `escalation` — Checks whether escalation has passed a certain threshold
- `has_play_goal` — Checks if diplomatic play has a certain war goal type
- `initiator_is` — Checks who the initiator of a diplomatic play is → country
- `is_diplomatic_play_type` — Checks diplomatic play is of a certain type
- `is_war` — True if the diplomatic play has escalated into war
- `target_is` — Checks who the target of a diplomatic play is → country

### Effects (12)

- `add_diplomatic_play_war_support` — Adds war support to the target country in the scoped diplomatic play.
- `add_escalation` — Add escalation to a diplomatic play
- `add_initiator_backers` — Add a tag/scope country to the initiator side of a diplomatic play   add_initiator_backers
- `add_target_backers` — Add a tag/scope country to the target side of a diplomatic play   add_target_backers
- `add_war_goal` — Adds a war goal to a DP.
- `end_play` — End a diplomatic play
- `remove_initiator_backers` — Remove a tag/scope country from the initiator side of a diplomatic play   remove_initiator_backers
- `remove_target_backers` — Remove a tag/scope country to the target side of a diplomatic play   remove_target_backers
- `remove_war_goal` — Removes a war goal from a DP.
- `resolve_play_for` — effect end diplo play for one side, with it gaining war goals → country
- `set_key` — Set name to a diplomatic play
- `set_war` — Set a diplomatic play to be a war

---
## Diplomatic Pact

### Iterators (1)

- `any/every/ordered/random_participant` → country — Any of two participants of the diplomatic pact in a scope   any_participant

### Triggers (4)

- `income_transfer` — Compares the base income transfer of the diplomatic pact
- `is_diplomatic_action_type` — Checks diplomatic pact is of a certain action type
- `is_diplomatic_pact_in_danger` — Checks if diplomatic pact is in danger of breaking
- `is_forced_pact` — Check if a diplomatic pact has a forced duration due to reasons such as a sway or obligation Traits: yes/no  Reads gamestate for all scopes.

---
## Diplomatic Catalyst

### Triggers (2)

- `is_diplomatic_catalyst_type` — Checks diplomatic catalyst is of a certain catalyst type
- `lobby_formation_reason` — Check scope diplomatic catalyst or political lobby scope for lobby formation reason (scopes: diplomatic_catalyst, political_lobby)

---
## Military Formation

### Triggers (14)

- `formation_army_unit_type_fraction` — Checks that a formation has a certain percentage of a specific army unit type   scope:example_formation
- `formation_ship_type_fraction` — Checks that a formation has a certain fraction of a specific ship type   formation_ship_type_fraction
- `has_high_attrition` — Checks if a Military Formation's attrition risk is higher than the base value for their type
- `has_mobilization_option` — Checks that a formation has a specific mobilization option → mobilization_option
- `has_naval_mission_with_invalid_area` — Checks if a Fleet has a naval mission with an invalid area
- `has_ship_outside_max_port_distance` — Checks if a Fleet has any ship that is beyond its maximum distance to port
- `is_army` — Checks if a military formation is Army
- `is_doing_piracy_in_region` — Checks if a Fleet is doing piracy in the specified strategic region → strategic_region
- `is_fleet` — Checks if a military formation is Fleet
- `is_fully_mobilized` — Checks if the Military Formation is fully mobilized
- `is_invalid_naval_mission_grace_period_active` — Checks if a Fleet is in the grace period from having an invalid naval mission
- `is_mobilized` — Checks if the military formation is mobilized
- `organization` — Compares the Organization of the Military Formation in scope
- `organization_target` — Compares the target Organization of the Military Formation in scope

### Effects (5)

- `add_organization` — Adds the specified amount of Organization to the Military Formation in scope
- `deploy_to_front` — Deploys the scope formation to the target front
- `fully_mobilize_army` — Fully mobilizes scope army
- `mobilize_army` — Mobilizes scope army
- `teleport_to_front` — Teleports the scope formation to the target front

---
## Front

### Triggers (4)

- `is_vulnerable_front` — Whether the scoped Front doesn't have any Battalions nor Generals on target side, and the enemy has at least one General. → country
- `num_front_casualties` — Checks the number of casualties for the target country in the scoped front   num_front_casualties
- `num_front_dead` — Checks the number of dead for the target country in the scoped front   num_front_dead
- `num_front_wounded` — Checks the number of wounded for the target country in the scoped front   num_front_wounded

---
## Battle

### Iterators (1)

- `any/every/ordered/random_combat_unit` → new_combat_unit (scopes: battle, building, front, hq, military_formation) — Iterate through all combat units of input scope   Supported scopes: building, military formation, front, battle   any_combat_unit

---
## Battle Side

### Triggers (3)

- `current_manpower` — Compares the current manpower of a battle side
- `has_battle_condition` — True if the battle side currently has a condition with the given key
- `starting_manpower` — Compares the starting manpower of a battle side

---
## Theater

### Triggers (3)

- `is_land_theater` — Checks if a theater is a land theater
- `num_mobilized_units_in_theater` — Determines the number of mobilized units belonging to the scoped theater's owner or their allies, in fronts intersecting the scoped theater
- `num_provinces_in_theater` — Determines the number provinces in the scoped theater

---
## Power Bloc

### Iterators (1)

- `any/every/ordered/random_power_bloc_member` → country — Iterate through all members of the scoped power bloc including the leader   any_power_bloc_member

### Triggers (37)

- `can_invite_any_country` — Checks whether is possible to invite any country to the scoped Power Bloc.
- `current_cohesion_number` — Compare the current Cohesion as a numeric value
- `current_cohesion_percentage` — Compare the current Cohesion as a percentage of the maximum of a Power Bloc in scope
- `free_principle_slots` — Compare a power bloc's free principle slot count
- `has_identity` — Checks if the scoped power bloc has certain central identity → power_bloc_identity
- `has_principle` — Checks if the scoped power bloc has certain principle → power_bloc_principle
- `has_principle_group` — Checks if the scoped power bloc has a principle in the specified group → power_bloc_principle_group
- `leverage_advantage` — Checks that the leverage advantage between power bloc and target country meets condition
- `num_power_bloc_members` — Compare the number of members in a power bloc against a value
- `num_power_bloc_states` — Compare the number of states in a power bloc against a value
- `power_bloc_rank` — Compare a power bloc's rank
- `power_bloc_total_leading_goods_producers` — Compare how many members are among the leading producers for all goods worldwide weighted by their position in the ranking.The top producer is weighted by MIN_SPOT_PRESTIGE_AWARD and then each subs...
- `power_bloc_total_leading_goods_producers_with` — Compare how many members are among the leading producers for all goods worldwide weighted by their position in the ranking, plus one additional country not currently in the power bloc.The top produ...
- `power_bloc_total_leading_goods_producers_without` — Compare how many members are among the leading producers for all goods worldwide weighted by their position in the ranking, minus one country that is currently in the power bloc.The top producer is...
- `power_bloc_worst_economic_dependence` — If used in a power bloc scope, compare the member with the lowest economic dependence on the leader.
- `power_bloc_worst_economic_dependence_with` — If used in a power bloc scope, compare the member with the lowest economic dependence on the leader.
- `power_bloc_worst_economic_dependence_without` — If used in a power bloc scope, compare the member with the lowest economic dependence on the leader.
- `power_bloc_worst_infamy` — If used in a power bloc scope, compare the Infamy value of the member country with the worst (highest) Infamy
- `power_bloc_worst_infamy_with` — If used in a power bloc scope, compare the Infamy value of the member country with the worst (highest) Infamy
- `power_bloc_worst_infamy_without` — If used in a power bloc scope, compare the Infamy value of the member country with the worst (highest) Infamy
- `power_bloc_worst_leader_relations` — If used in a power bloc scope, compare the Relations value to the power bloc leader for the member country with the worst (lowest) Relations
- `power_bloc_worst_leader_relations_with` — If used in a power bloc scope, compare the Relations value to the power bloc leader for the member country with the worst (lowest) Relations
- `power_bloc_worst_leader_relations_without` — If used in a power bloc scope, compare the Relations value to the power bloc leader for the member country with the worst (lowest) Relations
- `power_bloc_worst_leader_religion_population_fraction` — If used in a power bloc scope, compare the lowest population fraction in a member country that follows the leader's religion.
- `power_bloc_worst_leader_religion_population_fraction_with` — If used in a power bloc scope, compare the lowest population fraction in a member country that follows the leader's religion.
- `power_bloc_worst_leader_religion_population_fraction_without` — If used in a power bloc scope, compare the lowest population fraction in a member country that follows the leader's religion.
- `power_bloc_worst_liberty_desire` — If used in a power bloc scope, compare the Liberty Desire value of the member country with the worst (highest) Liberty Desire
- `power_bloc_worst_liberty_desire_with` — If used in a power bloc scope, compare the Liberty Desire value of the member country with the worst (highest) Liberty Desire
- `power_bloc_worst_liberty_desire_without` — If used in a power bloc scope, compare the Liberty Desire value of the member country with the worst (highest) Liberty Desire
- `power_bloc_worst_progressiveness_difference_government_type` — If used in a power bloc scope, compare the total Progressiveness value difference for the member country with the worst (highest) difference in progressiveness between their Governance Principles a...
- `power_bloc_worst_progressiveness_difference_government_type_with` — If used in a power bloc scope, compare the total Progressiveness value difference for the member country with the worst (highest) difference in progressiveness between their Governance Principles a...
- `power_bloc_worst_progressiveness_difference_government_type_without` — If used in a power bloc scope, compare the total Progressiveness value difference for the member country with the worst (highest) difference in progressiveness between their Governance Principles a...
- `predicted_cohesion_percentage_with` — Predicts the cohesion of a Power Bloc (as a fraction of 1) if it included target country as a member   predicted_cohesion_percentage_with,
- `target_cohesion_number` — Compare the target Cohesion as a numeric value
- `target_cohesion_percentage` — Compare the target Cohesion as a percentage of the maximum of a Power Bloc in scope
- `total_used_principle_levels` — Compare a power bloc's total number of active principle levels
- `used_principle_slots` — Compare a power bloc's used principle slot count

### Effects (5)

- `add_cohesion_number` — Adds a specific amount of Cohesion to the Power Bloc in scope
- `add_cohesion_percent` — Adds a percentage-based amount of Cohesion to the Power Bloc in scope
- `add_leverage` — Adds the specified amount of leverage for the Power Bloc in scope on the country specified   If the value is positive, also reduces the amount of Leverage of all other Blocs proportionally to match...
- `add_principle` — Adds principle to powerbloc
- `remove_principle` — Removes principle from powerbloc

---
## Company

### Iterators (2)

- `any/every/ordered/random_owned_country` → country — Iterate through all countries owned by the scoped company   any_owned_country
- `any/every/ordered/random_scope_regional_hqs` → building — Iterate through regional HQs of the scoped company   any_scope_regional_hqs

### Triggers (11)

- `can_potentially_produce_prestige_goods` — Checks if scope company can potentially produce target prestige good type
- `company_employed_levels` — Check the number of employed building levels of the scoped company
- `company_global_productivity_comparison` — Check the average global productivity of buildings matching this company's buildings, scaled by owned levels for each type
- `company_has_building_type_monopoly` — Check if the scoped company has a monopoly of the specified building type → building_type
- `company_has_monopoly` — Check if the scoped company has any monopoly
- `company_is_prosperous` — Check if a company is considered to be prosperous Traits: yes/no  Reads gamestate for all scopes.
- `company_owned_levels` — Check the number of owned building levels of the scoped company
- `company_productivity` — Check the productivity of the scoped company
- `company_prosperity` — Check the prosperity of a company
- `is_company_type` — Checks if scoped company is of the specified type → company_type
- `is_producing_prestige_goods` — Checks if scope company is producing prstige goods

### Effects (5)

- `add_company_monopoly` — Adds a monopoly to a company scope: → building_type
- `add_owned_country` — Sets the scoped company as a founding company for the target country → country
- `remove_owned_country` — Removes the scoped company's ownership of the target country → country
- `set_company_establishment_date` — Sets the establishment date of scope company
- `set_company_state_region` — Sets the state region for the scoped company, so the company building can be built there → state_region

---
## Law

### Iterators (2)

- `any/every/ordered/random_possible_amendment_type` → amendment_type — Iterate through amendment types that could be added to the scoped law   any_possible_amendment_type
- `any/every/ordered/random_scope_amendment` → amendment — Iterate through amendments of the scoped law   any_scope_amendment

### Triggers (6)

- `amendment_count` — Compares the number of amendments in scope law
- `can_be_enacted` — Checks if a law could be enacted by its country, considering its current situation
- `has_amendment` — Check if scoped law has an amendment of the given type   has_amendment → amendment_type
- `is_reasonable_law_for_petition` — Checks if a law is considered reasonable for a government petition to enact it
- `law_approved_by` — Checks whether the scoped law is approved by an interest group
- `law_is_available` — Checks if a law is available for its country, considering its current situation.

### Effects (1)

- `add_amendment` — Adds an amendment to the scoped law.

---
## Law Type

### Triggers (3)

- `is_same_law_group_as` — Checks if scope law type is in the same group as the target law type scope   is_same_law_group_as → law_type
- `law_progressiveness_difference` — Compares the progressiveness of the scoped law type to the target law type, higher value means greater difference   "law_progressiveness_difference( scope:target_law )" > 50 Traits: <, <=, =, !=, >...
- `progressiveness` — Compare the progressiveness of the law type in scope   law_type:law_isolationism.progressiveness > 50 Traits: <, <=, =, !=, >, >= Reads gamestate for all scopes.

---
## Journal Entry

### Iterators (1)

- `any/every/ordered/random_scope_je_involved` → country — Iterate through all involved in a journal entry   any_scope_je_involved

### Triggers (4)

- `is_goal_complete` — Check if the journal entry's goal has been met
- `is_progressing` — Check if the journal entry is progressing
- `journal_entry_age` — Return the age of the journal entry (since activation) in days
- `scripted_bar_progress` — Determines the progress of a scripted progress bar   scripted_bar_progress

### Effects (5)

- `add_involved_country` — Makes target country an involved country in scope journal entry → country
- `add_progress` — Adds progress to a journal entry progressbar   add_progress
- `remove_involved_country` — Removes target country from involved countries in scope journal entry → country
- `set_bar_progress` — Sets progress for a journal entry scripted progressbar   set_bar_progress
- `set_target_technology` — Sets a (new) target technology scope for a journal entry   set_target_technology

---
## Treaty

### Iterators (2)

- `any/every/ordered/random_scope_article` → treaty_article — Iterate through articles of the scoped treaty   any_scope_article
- `any/every/ordered/random_scope_article_option` → treaty_article_options (scopes: treaty_options, treaty) — Iterate through article_options of the scoped treaty or treaty_options   any_scope_article_option

### Triggers (8)

- `binds` — Checks if the scoped treaty or treaty_options binds the given country   scope:some_treaty → country (scopes: treaty_options, treaty)
- `is_enforced` — Checks if the scoped treaty is enforced on either party   scope:some_treaty
- `is_equal_exchange_for` — Checks if the scoped treaty is considered an equal exchange by target country,   scope:some_treaty → country (scopes: treaty_options, treaty)
- `is_exchanging_obligations` — Checks if the scoped treaty is exchanging any obligations,   scope:some_treaty (scopes: treaty_options, treaty)
- `is_fulfilled_by` — Check if the scoped treaty is fulfilled by the given country   scope:treaty → country
- `is_historical_treaty` — Checks if the scoped treaty was signed before the game start date   scope:some_treaty (scopes: treaty_options, treaty)
- `is_renegotiation` — Checks if the scoped treaty is amending an existing treaty   scope:some_treaty (scopes: treaty_options, treaty)
- `was_coerced_with_naval_threat` — Check if the scoped treaty was accepted through threatening naval hostilities

### Effects (1)

- `withdraw` — Withdraws a country from a treaty   scope:treaty = {

---
## Treaty Article

### Triggers (6)

- `has_type` — Checks if the scoped object has the type identified by the given string   scope:some_object (scopes: treaty_article, treaty_article_options)
- `is_desired_by` — Check if the scoped article or article_options has positive inherent acceptance with the target country   scope:treaty_article → country (scopes: treaty_article, treaty_article_options)
- `is_giftable_to` — Check if the scoped article or article_options is giftable to target country   scope:treaty_article → country (scopes: treaty_article, treaty_article_options)
- `is_treaty_article_in_danger` — Checks if treaty article is in danger of breaking
- `max_contraventions` — Check the maximum contraventions for the article type of the scoped article or article_options   scope:treaty_article (scopes: treaty_article, treaty_article_options)
- `num_contraventions` — Check if the scoped article has the given number of contravention from the given country   scope:treaty_article

---
## Goods

### Triggers (4)

- `is_tradeable` — Check if a goods or market goods is tradeable (scopes: goods, market_goods)
- `world_market_delta` — Checks if goods has the specified number of exports minus imports in the world market
- `world_market_exports` — Checks if goods has the specified number of exports in the world market
- `world_market_imports` — Checks if goods has the specified number of imports in the world market

---
## Combat Unit

### Triggers (2)

- `has_unit_type` — Checks if a Combat Unit is of the specified type → combat_unit_type
- `unit_formation_has_commander` — Checks if ther formation of the scoped combat unit has the provided character as one of its commanders   unit_formation_has_commander → character

### Effects (1)

- `add_morale` — Adds the specified amount of Morale to the Combat Unit in scope

---
## Province

### Iterators (1)

- `any/every/ordered/random_province` → state — Iterate through all Provinces in the scoped State   any_province

### Triggers (3)

- `has_label` — Check if the scope object has the specified label
- `has_terrain` — Check if the province has the specified terrain type
- `is_province_land` — Check if the province is on land Traits: yes/no  Reads gamestate for all scopes.

---
## Strategic Region

### Triggers (1)

- `has_diplomatic_play` — Check if strategic region has a diplomatic play or not Traits: yes/no  Reads gamestate for all scopes.

---
## Civil War

### Triggers (2)

- `civil_war_progress` — Compare progress of civil war
- `is_civil_war_type` — Check if the scoped civil war is of a specific type

### Effects (1)

- `add_civil_war_progress` — Adds the specified number of percentage points to a civil war progress (range is [0, 1], 0.1 means 10 percentage points)

---
## Amendment

### Triggers (2)

- `amendment_can_be_repealed` — Check if the amendment can be repealed
- `has_parent_law` — Check if the amendment type has a parent law

### Effects (1)

- `remove_amendment` — Removes an amendment immediately without checking cooldown

---
## Country Formation

### Triggers (1)

- `is_major_formation` — Checks if a country formation is a major formation

---
## Country Definition

### Triggers (1)

- `country_definition_has_culture` — Checks if a culture is one of the cultures of the country definition   country_definition_has_culture → culture

---
## Invasion

### Triggers (3)

- `invasion_has_marines` — Checks if any combat unit in the scoped invasion's armies is a marine
- `is_invasion_stalled` — Checks if the invasion is stalled due to wrong commander orders
- `is_naval_invasion` — Checks if the scoped invasion is a naval invasion

---
## Harvest Condition

### Triggers (1)

- `harvest_condition_intensity` — With a harvest condition scope, compare the intensity of the harvest condition in a given country (since the state region can span multiple countries)   harvest_condition_intensity

---
## Character Role

### Triggers (5)

- `is_auto_assigned` — Checks if the character role is auto assigned
- `is_character_role` — Checks if the scoped character role is a specific role
- `is_character_role_type` — Checks if the scoped character role is of a specific archetype
- `role_priority` — Compares the priority of the character role
- `spawns_characters_to_pool` — Checks if the character role spawns characters to the pool

---
## None

### Iterators (17)

- `any/every/ordered/random_character` → character — Iterate through all characters globally   any_character
- `any/every/ordered/random_character_in_exile_pool` → character — Iterate through characters in the exile pool   any_character_in_exile_pool
- `any/every/ordered/random_character_in_void` → character — Iterate through characters in the void   any_character_in_void
- `any/every/ordered/random_country` → country — Iterate through all countries globally   any_country
- `any/every/ordered/random_decentralized_country` → country — Iterate through all countries that are decentralized   any_decentralized_country
- `any/every/ordered/random_diplomatic_play` → diplomatic_play — Iterate through all diplomatic plays globally   any_diplomatic_play
- `every/ordered/random_in_global_list` →  — Iterate through all items in global list.
- `every/ordered/random_in_list` →  — Iterate through all items in list.
- `every/ordered/random_in_local_list` →  — Iterate through all items in local list.
- `random_list` →  — Selects one effect from a weighted random list and executes it.
- `random_log_scopes` →  — Log the current scope to the random log when this effect executes.
- `any/every/ordered/random_market` → market — Iterate through all markets globally   any_market
- `any/every/ordered/random_power_bloc` → power_bloc — Iterate through all power blocs   any_power_bloc
- `any/every/ordered/random_state` → state — Iterate through all states globally   any_state
- `any/every/ordered/random_state_region` → state_region — Iterate through all state regions   any_state_region
- `any/every/ordered/random_strategic_region` → strategic_region — Iterate through all strategic regions globally   any_strategic_region
- `any/every/ordered/random_treaty` → treaty — Iterate through treaties (both in force and drafts)   any_treaty

### Triggers (83)

- `active_lens` — Checks if the specified lens is open
- `active_lens_option` — Checks if the specified lens option is activated
- `add_to_temporary_list` — Saves a temporary target for use during the trigger execution   This is used to build lists in triggers.
- `all_false` — true if all children are false (equivalent to NOR)
- `always` — checks if the assigned yes/no value is true
- `and` — all inside trigger must be true
- `any_false` — true if any child is false (equivalent to NAND)
- `any_in_global_list` — Iterate through all items in global list.
- `any_in_list` — Iterate through all items in list.
- `any_in_local_list` — Iterate through all items in local list.
- `assert_if` — Conditionally cause an assert during run time   assert_if
- `assert_read` — Conditionally cause an assert during read time
- `calc_true_if` — Returns true if the specified number of sub-triggers return true   calc_true_if
- `can_create_treaty` — Checks if a treaty between countries can be created
- `can_start_tutorial_lesson` — Can the specified tutorial lesson be started?
- `current_tooltip_depth` — Returns the number of tooltips currently open on screen Traits: <, <=, =, !=, >, >=
- `custom_description` — Wraps triggers that get a custom description instead of the auto-generated one
- `custom_tooltip` — Replaces the tooltips for the enclosed triggers with a custom text   custom_tooltip
- `day_value` — Day value Traits: <, <=, =, !=, >, >=
- `daynight_value` — DayNight value Traits: <, <=, =, !=, >, >=
- `debug_log` — Log whether the parent trigger succeeded or failed
- `debug_log_details` — Log whether the parent trigger succeeded or failed.
- `exists` — Checks whether the specified scope target exists (check for not being the null object)
- `game_date` — Compare to current game date
- `global_population` — Compares the global population
- `global_variable_list_size` — Checks the size of a variable list   variable_list_size
- `has_account_item` — Does the player have the item in the account   has_account_item
- `has_cosmetic_dlc` — Does the client have this cosmetic DLC
- `has_cosmetic_dlc_feature` — Does the client have DLC that enables this particular cosmetic feature
- `has_dlc_feature` — Does the host have DLC that enables this particular feature
- `has_game_rule` — Is the given game rule setting enabled?
- `has_game_started` — True if game has started
- `has_gameplay_dlc` — Does the host have this gameplay DLC
- `has_global_variable` — Checks whether the current scope has the specified variable set
- `has_global_variable_list` — Checks whether the current scope has the specified variable list set
- `has_local_variable` — Checks whether the current scope has the specified variable set
- `has_local_variable_list` — Checks whether the current scope has the specified variable list set
- `has_map_interaction` — Checks if the map interaction type is active
- `has_map_interaction_diplomatic_action` — Checks if our current map interaction is a specific diplomatic action   has_map_interaction_diplomatic_action
- `has_reached_end_date` — True if the end date (NDefines::NGame::END_DATE) has been reached
- `has_unification_candidate` — Check if there is at least one unification candidate for country tag
- `has_variable` — Checks whether the current scope has the specified variable set
- `has_variable_list` — Checks whether the current scope has the specified variable list set
- `hidden_trigger` — Enclosed triggers are not shown in tooltips   hidden_trigger
- `is_building_type_expanded` — Checks if the CProductionMethodsPanelEntry for a particular CBuildingType is expanded   is_building_type_expanded
- `is_game_paused` — Checks if the game is paused
- `is_gamestate_tutorial_active` — Is the gamestate tutorial active? See save_progress_in_gamestate in tutorial_lesson_chains documentation.
- `is_in_list` — Checks if a target in in a list
- `is_lens_open` — Checks if a certain lens is open, specified as a lens key.
- `is_objective_completed` — Is the objective completed for the country in scope?
- `is_panel_open` — Checks if a certain infopanel is open, specified as an event target (target) or as a string (panel_name).
- `is_popup_open` — Checks if the specified popup panel is open
- `is_rightclick_menu_open` — Checks if the specified rightclick menu is open   is_rightclick_menu_open
- `is_set` — Checks whether the specified scope target has been set (includes being the null object)
- `is_target_in_global_variable_list` — Checks if a target is in a variable list   is_target_in_variable_list
- `is_target_in_local_variable_list` — Checks if a target is in a variable list   is_target_in_variable_list
- `is_target_in_variable_list` — Checks if a target is in a variable list   is_target_in_variable_list
- `is_template_used` — Checks if character template has already been used
- `is_theme_selected` — Does the player have the theme selected in settings   is_theme_selected
- `is_tutorial_active` — Is the tutorial active? Traits: yes/no
- `is_tutorial_lesson_active` — Is this the current tutorial lesson?
- `is_tutorial_lesson_chain_completed` — Has the tutorial lesson chain with the specified key been finished?
- `is_tutorial_lesson_completed` — has the tutorial lesson with the specified name been finished?
- `is_tutorial_lesson_step_completed` — Has the tutorial lesson step been finished?
- `list_size` — Checks the size of a list   list_size
- `local_variable_list_size` — Checks the size of a variable list   variable_list_size
- `month` — Compare to current game date month (Jan: 0, Dec: 11)
- `nand` — a negated AND trigger
- `night_value` — Night value Traits: <, <=, =, !=, >, >=
- `nor` — a negated OR trigger
- `not` — negates content of trigger
- `or` — at least one entry inside trigger must be true
- `real_month` — Compare to current real date month (Jan: 1, Dec: 12)
- `save_temporary_scope_as` — Saves a temporary target for use during the trigger execution
- `save_temporary_scope_value_as` — Saves a numerical or bool value as an arbitrarily-named temporary target to be referenced later in the same effect   save_temporary_scope_value_as
- `should_show_nudity` — can nudity be shown?
- `switch` — Switch on a trigger for the evaluation of another trigger with an optional fallback trigger.
- `trigger_else` — Evaluates the triggers if the display_triggers of preceding 'trigger_if' or 'trigger_else_if' is not mettrigger_if
- `trigger_else_if` — Evaluates the enclosed triggers if the display_triggers of the preceding `trigger_if` or `trigger_else_if` is not met and its own display_trigger of the limit is mettrigger_if
- `trigger_if` — Evaluates the triggers if the display_triggers of the limit are met   trigger_if
- `variable_list_size` — Checks the size of a variable list   variable_list_size
- `weighted_calc_true_if` — Returns true if the sum of weights of fulfilled sub-triggers amount to the specified sum   weighted_calc_true_if
- `year` — Compares the current year of the game

### Effects (66)

- `add_contextless_journal_entry` — Activates a contextless journal entry of the given type   add_contextless_journal_entry
- `add_journal_entry` — Adds a journal entry to a scoped country's journal, with optional saved scope target   add_journal_entry
- `add_to_global_variable_list` — Adds the event target to a variable list for the given duration   add_to_variable_list
- `add_to_list` — Adds the current scope to an arbitrarily-named list (or creates the list if not already present) to be referenced later in the (unbroken) event chain
- `add_to_local_variable_list` — Adds the event target to a variable list for the given duration   add_to_variable_list
- `add_to_temporary_list` — Adds the current scope to an arbitrarily-named list (or creates the list if not already present) to be referenced later in the same effect
- `add_to_variable_list` — Adds the event target to a variable list for the given duration   add_to_variable_list
- `assert_if` — Conditionally cause an assert during run time   assert_if
- `assert_read` — Conditionally cause an assert during read time
- `cancel_imposition` — Cancels imposition of the law (not law type) in scope   scope:country.imposed_law
- `change_global_variable` — Changes the value or a numeric variable   change_variable
- `change_local_variable` — Changes the value or a numeric variable   change_variable
- `change_variable` — Changes the value or a numeric variable   change_variable
- `clamp_global_variable` — Clamps a variable the specified max and min   clamp_variable
- `clamp_local_variable` — Clamps a variable the specified max and min   clamp_variable
- `clamp_variable` — Clamps a variable the specified max and min   clamp_variable
- `clear_global_variable_list` — Empties the list
- `clear_local_variable_list` — Empties the list
- `clear_saved_scope` — Clears a saved scope from the top scope
- `clear_variable_list` — Empties the list
- `create_country` — Creates a new country   create_country
- `create_dynamic_country` — Creates a new country with a dynamic tag   create_dynamic_country
- `create_treaty` — Creates a treaty between countries
- `custom_description` — Wraps effects that get a custom description instead of the auto-generated one
- `custom_description_no_bullet` — Wraps effects that get a custom description instead of the auto-generated one.
- `custom_label` — just a tooltip, the scope as object (for grouping, localization).
- `custom_label_no_bullet` — just a tooltip, the scope as object (for grouping, localization).
- `custom_tooltip` — just a tooltip, the scope as subject (for grouping, localization).
- `custom_tooltip_no_bullet` — just a tooltip, the scope as subject (for grouping, localization).
- `debug_log` — Log a string to the debug log when this effect executes,
- `debug_log_scopes` — Log the current scope to the debug log when this effect executes
- `else` — Executes enclosed effects if limit criteria of preceding 'if' or 'else_if' is not met   if
- `else_if` — Executes enclosed effects if limit criteria of preceding 'if' or 'else_if' is not met, and its own limit is met   if
- `error_log` — Log a string to the error log when this effect executes,
- `execute_event_option` — Execute effects of the specified event option in the specified event   execute_event_option
- `hidden_effect` — Enclosed effects are not shown in tooltips   hidden_effect
- `if` — Executes enclosed effects if limit criteria are met   if
- `post_audio_event` — Runs an audio even on a "persistent" audio object    post_audio_event
- `post_notification` — Posts notification
- `post_proposal` — Posts proposal
- `random` — run an effect depending on a random chance, do nothing otherwise.
- `remove_from_list` — Removes the current scope from a named list remove_from_list
- `remove_global_variable` — Removes a variable
- `remove_list_global_variable` — Removes the target from a variable list   remove_list_variable
- `remove_list_local_variable` — Removes the target from a variable list   remove_list_variable
- `remove_list_variable` — Removes the target from a variable list   remove_list_variable
- `remove_local_variable` — Removes a variable
- `remove_variable` — Removes a variable
- `round_global_variable` — Rounds a variable to the nearest specified value   round_variable
- `round_local_variable` — Rounds a variable to the nearest specified value   round_variable
- `round_variable` — Rounds a variable to the nearest specified value   round_variable
- `save_scope_as` — Saves the current scope as an arbitrarily-named target to be referenced later in the (unbroken) event chain   save_scope_as
- `save_scope_value_as` — Saves a numerical or bool value as an arbitrarily-named target to be referenced later in the (unbroken) event chain   save_scope_value_as
- `save_temporary_scope_as` — Saves the current scope as an arbitrarily-named temporary target to be referenced later in the same effect   save_temporary_scope_as
- `save_temporary_scope_value_as` — Saves a numerical or bool value as an arbitrarily-named temporary target to be referenced later in the same effect   save_temporary_scope_value_as
- `set_global_variable` — Sets a variable   set_variable = { name = X value = Y days = Z }   Where X is the name of the variable used to then access it   Where Y is any event target, bool, value, script value or flag (flag:...
- `set_local_variable` — Sets a variable   set_variable = { name = X value = Y days = Z }   Where X is the name of the variable used to then access it   Where Y is any event target, bool, value, script value or flag (flag:...
- `set_variable` — Sets a variable   set_variable = { name = X value = Y days = Z }   Where X is the name of the variable used to then access it   Where Y is any event target, bool, value, script value or flag (flag:...
- `show_as_tooltip` — Enclosed effects are only shown in tooltips (but are not actually executed)   show_as_tooltip
- `sort_global_variable_list` — Sorts a variable list   sort_variable_list
- `sort_local_variable_list` — Sorts a variable list   sort_variable_list
- `sort_variable_list` — Sorts a variable list   sort_variable_list
- `start_tutorial_lesson` — Starts the tutorial lesson with the given key.
- `switch` — Switch on a trigger for the evaluation of another trigger with an optional fallback trigger.
- `trigger_event` — Triggers an event for the current scope
- `while` — Repeats enclosed effects while limit criteria are met or until set iteration count is reached   while

---
## Ship

### Triggers (13)

- `ai_ship_value` — AI valuation of a ship in £, equal to the current template-version construction cost times NAI::SHIP_TRANSFER_BASE_VALUE_PER_CONSTRUCTION_POINT
- `armor` — Compare a ship's armor
- `crew` — Compare a ship's current crew
- `crew_percent` — Compare a ship's current crew
- `days_obsolete` — Compare the number of days since a ship was first marked obsolete by the AI.
- `hit_points` — Compare a ship's current hit points
- `hit_points_percent` — Compare a ship's current hit points
- `is_damaged` — Checks if a ship is damaged
- `is_flagship` — Checks if the scoped ship is assigned as the flagship
- `is_in_port` — Checks if a ship is in port
- `is_ship_type` — Checks if scoped ship is of the specified type → ship_type
- `power_projection_value` — Compare a ship's power projection
- `speed` — Compare a ship's speed

### Effects (8)

- `damage_ship_hull` — Damages a ship's hull by a given amount
- `damage_ship_hull_percent` — Damages a ship's hull by a given percentage of its total health
- `kill_crew` — Kills a given amount of a ship's crew
- `kill_crew_percent` — Kills a given percentage of a ship's crew
- `kill_ship` — Destroys the scoped ship
- `set_as_flagship` — Assign/unassign the ship as a flagship for the country
- `set_ship_owner` — Set ship owner country → country
- `set_ship_owner_multiple` — Set ship owner country, use when setting multiple ships in a row to put them in a single ownership transfer fleet, then use clear_ownership_transfer_fleet to clear it → country

