# Quick Reference — Game IDs & Script Values

Commonly needed IDs when writing events, laws, triggers, and effects. For the full list, use the mod state server (`/keys/Laws`, `/keys/Interest%20Groups`, etc.).

## Vanilla Law Groups & Law IDs

| Law Group | Laws |
|---|---|
| `lawgroup_army_model` | `law_peasant_levies`, `law_professional_army`, `law_national_militia`, `law_mass_conscription` |
| `lawgroup_church_and_state` | `law_state_religion`, `law_millet_system`, `law_people_of_the_book`, `law_freedom_of_conscience`, `law_total_separation`, `law_state_atheism` |
| `lawgroup_citizenship` | `law_subjecthood`, `law_ethnostate`, `law_national_supremacy`, `law_racial_segregation`, `law_cultural_exclusion`, `law_multicultural` |
| `lawgroup_distribution_of_power` | `law_autocracy`, `law_neo_absolutism`, `law_technocracy`, `law_oligarchy`, `law_organic_regulation`, `law_elder_council`, `law_landed_voting`, `law_wealth_voting`, `law_census_voting`, `law_universal_suffrage`, `law_anarchy`, `law_single_party_state` |
| `lawgroup_economic_system` | `law_traditionalism`, `law_interventionism`, `law_agrarianism`, `law_industry_banned`, `law_extraction_economy`, `law_laissez_faire`, `law_cooperative_ownership`, `law_command_economy` |
| `lawgroup_free_speech` | `law_outlawed_dissent`, `law_censorship`, `law_right_of_assembly`, `law_protected_speech` |
| `lawgroup_governance_principles` | `law_chiefdom`, `law_monarchy`, `law_colonial_administration`, `law_presidential_republic`, `law_parliamentary_republic`, `law_theocracy`, `law_council_republic`, `law_corporate_state` |
| `lawgroup_internal_security` | `law_no_home_affairs`, `law_national_guard`, `law_secret_police`, `law_guaranteed_liberties` |
| `lawgroup_labor_rights` | `law_no_workers_rights`, `law_regulatory_bodies`, `law_worker_protections` |
| `lawgroup_migration` | `law_no_migration_controls`, `law_migration_controls`, `law_closed_borders` |
| `lawgroup_policing` | `law_no_police`, `law_local_police`, `law_dedicated_police`, `law_militarized_police` |
| `lawgroup_trade_policy` | `law_mercantilism`, `law_protectionism`, `law_free_trade`, `law_isolationism` |
| `lawgroup_welfare` | `law_no_social_security`, `law_poor_laws`, `law_wage_subsidies`, `law_old_age_pension` |

Mod-added law groups are in `common/laws/extra_laws.txt`. Key ones: `lawgroup_antitrust`, `lawgroup_rules_of_war`, `lawgroup_electoral_finance`, `lawgroup_criminal_justice`, `lawgroup_minority_rights`, `lawgroup_privacy_rights`, `lawgroup_monetary_policy`, `lawgroup_LGBTQ_rights`, plus 15+ ministry law groups.

## Interest Group IDs

`ig_armed_forces`, `ig_devout`, `ig_industrialists`, `ig_intelligentsia`, `ig_landowners`, `ig_petty_bourgeoisie`, `ig_rural_folk`, `ig_trade_unions`

## Pop Types

`academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`, `engineers`, `farmers`, `laborers`, `machinists`, `officers`, `peasants`, `shopkeepers`, `slaves`, `soldiers`

## Strata (for `add_radicals`/`add_loyalists`)

`strata = upper` (capitalists, aristocrats, officers, clergymen), `strata = middle` (shopkeepers, engineers, clerks, bureaucrats, academics), `strata = lower` (laborers, machinists, farmers, peasants, soldiers). Can also target `pop_type = <type>`.

## Radicals/Loyalists Script Values

`very_small_radicals` (0.01), `small_radicals` (0.02), `medium_radicals` (0.05), `large_radicals` (0.1), `very_large_radicals` (0.2). Used in `add_radicals = { value = <name> }` and `add_loyalists`. Despite the name, these values work for both — the name refers to magnitude.

## Election Momentum Script Values

`momentum_small` (0.1), `momentum_medium` (0.2), `momentum_large` (0.3), `momentum_very_large` (0.5), `momentum_utterly_fraudulent` (1.5). Negative: `momentum_small_decrease` (-0.1), `momentum_medium_decrease` (-0.2), `momentum_large_decrease` (-0.3).

## Modifier Duration Script Values

`short_modifier_time` (~1 year / 365 days), `normal_modifier_time` (~3 years / 1095 days), `long_modifier_time` (~5 years / 1825 days).

## Custom Script-Only Modifiers (Mod-Added)

These `script_only` modifiers can be applied in any `modifier = { }` block (laws, techs, PMs, traits, etc.):

| Modifier | System | Effect |
|---|---|---|
| `country_banking_random_momentum_mult` | Banking | Scales cycle volatility (±%) |
| `country_banking_crash_chance_mult` | Banking | Scales crash probability (±%) |
| `country_finance_momentum_monthly_add` | Banking | Flat monthly momentum change |
| `country_bubble_pressure_monthly_add` | Banking | Flat monthly bubble pressure change |
| `country_finance_value_monthly_add` | Banking | Flat monthly cycle value change |
| `country_banking_intervention_max_add` | Banking | Available intervention points |
| `country_sol_expectation_adaptation_rate_mult` | SoL Expectations | Scales adaptation speed (±%) |
| `country_nuclear_weapon_attack_success_add` | Nuclear | Attack success chance (flat, 0–1 scale) |
| `country_nuclear_weapon_defense_chance_add` | Nuclear | Defense chance (flat, 0–1 scale) |
| `country_monthly_investment_pool_add` | Economy | Flat monthly investment income |
| `country_monthly_investment_pool_mult` | Economy | Scales monthly investment income |
