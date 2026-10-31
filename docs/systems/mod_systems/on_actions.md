# On-Actions Reference

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

## On-Actions Reference

The mod uses 55 on-action files under `common/on_actions/`; the index below lists the main ones. These wire mod logic into engine hooks — either **pulse-based** (fires periodically for all relevant scopes) or **immediate** (fires the instant a specific game event occurs).

### File Index

| File | Purpose | Hook Type |
|------|---------|-----------|
| `extra_on_actions.txt` | Central hub: pulse wiring, dynamic modifiers, immediate triggers, company cleanup | Mixed |
| `te_construction_market_on_actions.txt` | Construction-market site re-placement on diplomatic/territorial and building-lifecycle changes, plus its yearly heartbeat | Mixed |
| `headlines.txt` | "World first" tech notifications (`on_acquired_technology`) | Immediate |
| `law_events_on_actions.txt` | Law enactment checkpoint events (advance/debate/stall) | Immediate |
| `amendment_on_actions.txt` | Temporary-amendment expiry follow-up events (`on_amendment_timeout`) | Immediate |
| `amendment_petition_on_actions.txt` | Amendment petitions on laws in force, one yearly roll per petition (§ Amendment Petitions) | Pulse |
| `langreform_events_on_actions.txt` | Language reform yearly random events | Pulse |
| `minor_events_on_actions.txt` | Miscellaneous yearly random events | Pulse |
| `repeatable_events_on_actions.txt` | Generic repeatable yearly events | Pulse |
| `resettlement_on_actions.txt` | Internal resettlement: the monthly country pulse (transfer, politics, Declaration, events) and the monthly state pulse (modifier refresh: destination bonuses and readouts) | Pulse (monthly) |
| `social_tensions_on_actions.txt` | Social/political tension yearly events | Pulse |
| `space_race_on_actions.txt` | Space race in-progress and cross-system yearly events | Pulse |
| `te_monetary_on_actions.txt` | Monetary policy: world reference rate and (phase 3) the world rate, the monthly country update, the yearly growth snapshot, the country-creation hooks (see **Monetary Policy (phase 1)**), and — phase 5 — the anchored-GDP refresh on the global pulse, the yearly arrangement scan + seigniorage re-sum, `on_country_default` (the guarantee is called) and `on_become_subject` (currency boards) | Mixed |
| `te_unemployment_on_actions.txt` | Each state's yearly walk for its workforce share, which `te_state_unemployment_share` divides the engine's unemployment by (§ Unemployment as a Share of the Workforce), a monthly fill for a state with none yet, and the self-check `unemployment_share_read` | Pulse |
| `te_region_area_on_actions.txt` | Writes each state region's land area once per save (`te_region_area_generated.txt`) | Mixed |
| `un_on_actions.txt` | UN formation and recurring member events | Pulse (monthly) |
| `wonder_events_on_actions.txt` | Wonder building narrative events | Pulse (monthly) |
| `te_tax_on_actions.txt` | Legislated tax code (rule-gated): the global monthly dispatch of the processor `te_tax.1` on the 1st, the country-pulse watchdog, migration at game start and for formed and released countries, the carrier re-assert on `on_law_activated`, relief marks on state transfers; under the light setting its own handlers (`te_tax_light_*`): migration (`te_tax_light.2`), the monthly processor (`te_tax_light.1`) and a sync after a taxation law is activated (`te_tax_light.3`) | Mixed |
| `te_civil_war_on_actions.txt` | The shared civil-war layer: outbreak, win and resolve hooks, which call each system's copy and repair (the tax code's `te_tax_on_uprising` and `te_tax_repair_after_civil_war` among them) | Immediate |
| `te_orbital_debris_on_actions.txt` | Orbital debris (space race rule): the world's step on the global `on_monthly_pulse` (`te_debris_global_monthly`: the Kessler term, traffic, decay, removal, the panel's globals) and, on `on_monthly_pulse_country`, `te_debris_country_monthly` (the one refresh site of `te_orbital_debris` and `te_debris_cleaner_prestige`, and the ribbon-strike roll). See Space Race → *Orbital debris* | Pulse (monthly) |
| `te_global_commons_seabed_on_actions.txt` | Seabed licences (§ Global Commons): the monthly country recording, the monthly state refresh of Long-Haul Seabed Operations, recording on `on_state_owner_change`, the yearly sharing from the global `on_monthly_pulse` when due, and the AI's policy on `on_yearly_pulse_country` | Mixed |

### Pulse Wiring (`extra_on_actions.txt`)

All pulse-based on_actions are routed through `extra_on_actions.txt`:

**`on_monthly_pulse_state`** (Root = State):
- `space_elevator_on_action` — wonder construction progress
- `solar_collector_on_action` — wonder construction progress
- `orbital_battlestation_on_action` — wonder construction progress
- `mind_upload_nexus_on_action` — wonder construction progress
- `antimatter_facility_on_action` — wonder construction progress
- `pollution_on_action` — state pollution modifier update
- `war_propaganda_on_action` — wartime propaganda effects
- `state_yearly_cultural_acceptance_add_on_action` — cultural acceptance
- `tourism_on_action` — tourism output/throughput modifier refresh (sole owner; the multipliers read monthly-varying `city_size_rank` and the live infrastructure balance and building levels)
- `ministry_of_thought_control_on_action` — monthly loyalists from `state_monthly_loyalists_add`, per incorporated state

**`on_monthly_pulse`** (Root = global):
- `city_rank_on_action` — city tier updates
- `global_warming_events_on_action` — GW threshold & recurring events

**`on_monthly_pulse_country`** (Root = Country):
- `remove_invalid_buildings` — space program placement validation
- `cheaty_on_action` — debug modifier (disabled)
- `combined_arms_update_on_action` — military doctrine bonuses
- `investment_pool_setup_on_action` — investment pool management
- `international_relations_events_on_action` — diplo events
- `decolonization_events_on_action` — decolonization narrative
- `movement_events_te_on_action` — political movement events
- `society_technology_events_on_action` — society tech events
- `world_war_events_on_action` — world war events
- `overbuild_protection_on_action` — prevents wonder overbuilding
- `aptitude_traits_cleanup_on_action` — strips aptitude traits from characters the game rules don't allow them on

**`on_yearly_pulse_state`** (Root = State):
- `global_warming_update_on_action` — GHG emissions calculation
- `te_homeland_monthly` — dynamic homeland progress (monthly state pulse)
- `violent_hostility_on_action` — cultural violence
- `migration_crowding_on_action` — migration pull reduction
- `religious_mission_conversion_on_action` — treaty-based conversion

**`on_yearly_pulse_country`** (Root = Country):
- `tech_spread_on_action` — technology diffusion
- `excess_private_construction_on_action` — Excess Private Construction (per-project construction cap raise with an efficiency penalty, removed the year it is no longer needed) and Overinvestment
- `fix_incompatible_laws` — auto-fix illegal law combos
- `construction_cost_scaling_on_action` — GDP-based construction costs
- `colonial_collapse_on_action` — tiny, poor AI countries absorbed or decentralized
- `assign_aptitude_traits_on_action` — character trait assignment

### Immediate Triggers (`extra_on_actions.txt`)

These fire instantly when the engine event occurs, providing same-tick responsiveness:

**`on_company_disbanded`** (Root = Country, scope:company = disbanded company):
- Calls `remove_disbanded_company_buildings_effect` on every state to remove buildings belonging to the disbanded company. Uses a 64-entry if/else_if mapping in `common/scripted_effects/company_building_cleanup_effects.txt`.

**`on_building_built`** (Root = Building):
- When a barracks is built, recalculates `apply_combined_arms_bonuses` for the owning country (new combat unit type enters a formation). Only fires if `country_combined_arms_bonus_enabled_bool` is true.
- Also used by the construction market (`te_construction_market_on_actions.txt`) to remove a finished state's construction site.
- Grand Monuments: `monument_events.1` (a construction site's level: the AI's dedication ceremony, a refresh). It missed a monument whose five queued levels finished on the same day, so the AI's ceremony also has a check in the monthly refresh and the site's levels are counted, with their vanity backlash, by the state pulse (§ Grand Monuments). A player's ceremony comes from the Dedicate button.

**`on_character_recruitment`** (Root = Character):
- Calls `update_characters` on the owner to immediately apply tech-based traits (immortality, logistics) to newly recruited characters instead of waiting for monthly pulse.
- Recalculates `apply_combined_arms_bonuses` for the owner (new general may change formation composition).

**`on_military_formation_created`** (Root = Military Formation):
- Recalculates `apply_combined_arms_bonuses` for the formation's country. Uses `country` accessor (not `owner`) to reach country scope from formation scope.

**`on_state_owner_change`** (Root = state):
- Removes `building_space_program` if the state has one and is not the new owner's market capital. Catches conquest scenarios same-tick instead of waiting for monthly `remove_invalid_buildings`.

**`on_acquired_technology`** (Root = Country):
- `add_arable_land_effect_on_action` — arable land from agricultural techs
- `fix_incompatible_laws` — law compatibility check
- `cultural_hegemony_tech_first_on_action` — world-first tech prestige (`cultural_hegemony_on_actions.txt`)
- `agricultural_diffusion_on_action` — broadcasts the first researcher of each diffusion-eligible tech

**`on_country_formed`** (Root = the new country), **`on_country_released_as_{independent,own_subject,overlord_subject,company_subject}`** (scope:target = the released country):
- `agdiff_backfill_on_country_formed` / `agdiff_backfill_on_released_country` — give the new country every agricultural-diffusion modifier whose world-first has already fired (`agdiff_backfill_diffusion_for_country`, stateless). The broadcast only reaches countries that exist at the time. Unlike the broadcast (recognized countries only), this backfill ignores country type; that predates #460 and is left as it was.

**Civil wars** (the shared hooks in `te_civil_war_on_actions.txt`, #467). `te_civil_war_on_won` runs `te_civil_war_resolve_sides`, then nuclear custody and the #460–#465 repairs (`agdiff_repair_after_civil_war`, `un_repair_after_civil_war`, `te_monetary_repair_after_civil_war`, `cr_repair_after_civil_war`, `sr_repair_after_civil_war`), then `te_civil_war_clear`. The agricultural-diffusion ones:
- `agdiff_on_uprising`, from `te_civil_war_on_start` at `on_revolution_start` / `on_secession_start` (Root = the original, scope:target = the uprising country) — gives the rebels each diffusion modifier the original holds (`agdiff_copy_diffusion_from_root`), and nothing the nation lacked, and marks them with `agdiff_cw_copied`. The rebel object is the one that survives a rebel victory, and a revolution's winner inherits no modifier from the loser.
- `agdiff_repair_after_civil_war`, from `te_civil_war_on_won` at `on_civil_war_won` (Root = the winner) — the backfill again, only when the revolutionaries won a revolution (`var:te_cw_rebels_won = 1`), the winner carries no `agdiff_cw_copied` (a backstop for wars begun before the rebels got the copy), and it is recognized; the marker is removed here. On a rebel win only (`te_cw_rebels_won = 1`), it also restores what is left of a lost `agdiff_first_mover_prestige`, read from `agdiff_first_mover_month` (recorded with the title) off a ladder of whole years left, and not restored for titles won before that variable existed, and re-points `first_<tech>_country` from the dead loser to the winner.

**`on_law_activated`** (Root = Law scope):
- `fix_incompatible_laws_from_law_scope` — law compatibility
- `te_fix_inconsistent_laws_from_law_scope` — generated per-lawgroup consistency cleanup
- `language_reform_law_on_action` — language reform init/cleanup
- `radical_law_backlash_on_action` — backlash events for radical laws
- `banking_law_cascade_on_law_activated` — command economy force-enacts state-owned banking

**`on_law_enactment_started`** (Root = Law scope):
- Fires `minor_events_timelineextended.2` (law enactment notification)

**`on_amendment_timeout`** (Root = Country, scope:amendment = expired amendment, scope:law = its law):
- `te_amendment_timeout_on_action` — routes to the sunset-clause expiry events (`amendment_on_actions.txt`; see § Temporary Amendments)

**`on_merge_markets`** (Root = dissolving market, scope:market = absorbing market):
- `gw_market_join_on_action` removes the dissolving leader's fossil-fuel tariff-rate modifier without writing native tariff levels. National climate policies remain with the country. Monthly `gw_refresh_tariff_policies_effect` clears lost customs authority; it never synchronizes national policies.


### Construction-Market Immediate Triggers (`te_construction_market_on_actions.txt`)

The construction market hooks many engine events to keep its construction sites placed on the current map:
- `on_merge_markets`, `on_create_market` — market changes
- `on_country_released_as_independent/own_subject/overlord_subject` — country releases
- `on_country_formed`, `on_capitulation`, `on_enemy/ally_capitulated_notification` — country events
- `on_diplo_play_back_down`, `on_war_end` — diplomatic resolutions
- `on_revolution_start`, `on_secession_start` — internal conflicts
- `on_wargoal_enforced` — war results
- `on_start_expanding_building`, `on_building_expanded`, `on_building_built` — building events
- `on_production_method_changed` — removes `pm_retooling` in games whose rule setting waives it (§ Market settings without retooling or maintenance)

### Scope Chain Limitation (Important)

Building, institution and law scopes **do not support variables or modifiers**. The state modifier refresh effects in `extra_effects.txt` use `add_modifier = { multiplier = script_value }`, which evaluates the script value through the parent scope chain, so calling them from building-scope hooks like `on_building_built` / `on_production_method_changed`, from `on_law_activated`, or from `on_acquired_technology` causes cascading errors. Those hooks have all been removed (a plain `remove_modifier` on the building itself is fine: `te_remove_waived_pm_retooling` runs from `on_start_expanding_building` and `on_production_method_changed`) — the **periodic state pulses are the only refresh sites**: `pollution_on_action` and `tourism_on_action` on `on_monthly_pulse_state`, `migration_crowding_on_action` and `free_port_tariff_update_on_action` on `on_yearly_pulse_state`. Pick the pulse whose cadence matches how fast the multiplier's inputs move, and give each modifier exactly one refresh site.
