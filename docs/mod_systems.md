# Key Mod Systems

Reference for all major gameplay systems added by the Vic3TimelineExtended mod. Each section covers purpose, file locations, and key mechanics.

## Dynamic Modifier Pattern (`add_modifier` with `multiplier`)

Several mod systems use a common pattern for continuously-scaling modifiers:
1. Define a **static modifier** in `common/static_modifiers/extra_modifiers.txt` with base values (e.g., `country_construction_goods_cost_mult = 1`).
2. Define a **script value** in `common/script_values/extra_script_values.txt` that computes a multiplier (0 to N).
3. In an **on_action** (`on_yearly_pulse_country` or `on_yearly_pulse_state`), remove the old modifier and re-apply with `add_modifier = { name = X multiplier = <script_value> }`.
4. The engine multiplies every field in the static modifier by the multiplier value.

Systems using this pattern:
- **Global Warming** — `global_warming` modifier × `temperature_anomaly_display` (applied from JE `on_monthly_pulse`)
- **Construction Cost Scaling** — `construction_cost_scaling` modifier × `construction_cost_scaling_mult` (applied yearly, country scope)
- **Migration Crowding** — `migration_crowding` modifier × `migration_crowding_mult` (applied yearly, state scope)
- **Excess Private Construction** — `too_much_private_construction` modifier × `too_much_private_construction_script_value`
- **Tourism** — `te_tourism_modifier` × `tourism_modifier_mult` (applied yearly, state scope) — uses ~3000 lines of state_region-based script values in `common/script_values/tourism.txt`. **Must** be evaluated in `on_yearly_pulse_state` due to scope chain requirements.

## Production Methods (PMs)

- PM group icons are displayed in several GUI panels: `production_methods.gui`, `building_browser_panel.gui`, `building_details_panel.gui`, `goods_state_panel.gui`.
- The mod adds a `pmg_maintenance` PM group that should be **hidden** from all PM icon displays using `visible = "[Not(EqualTo_string(ProductionMethodGroup.GetKey, 'pmg_maintenance'))]"`.
- PM icon displays use `scrollarea` + `flowcontainer` (not `fixedgridbox`) so hidden items collapse properly and scrollbars appear when > 4 PM groups. Max width: `208` pixels (4 × 52px icons).

## Global Warming (`je_global_warming`)

> See also: `docs/journal_entry_systems.md` for full JE system documentation.

- A persistent journal entry (never completes: `complete = { always = no }`).
- Tracks `temperature_anomaly_display` script value against a 4°C progress bar.
- Has `should_be_involved` for all countries with `greenhouse_gas_emissions`.
- Has `status_desc` with 6 temperature tiers (negligible → catastrophic).
- Uses 16 scripted buttons (`gw_*`) for climate policies.
- Events: `environmentalism_events.txt` — threshold events at 0.5°C, 1.0°C, 2.0°C, 3.0°C.
- Cooling/reversal support: `global_warming_events_on_action` now also fires one-time recovery events when temperatures decline below 3.0°C, 2.0°C, 1.0°C, 0.5°C, and 0.1°C (`environmentalism_events.17`–`environmentalism_events.21`).

## Construction Cost Scaling

- **Purpose:** Makes construction more expensive for richer countries (GDP per capita). Prevents runaway exponential growth and provides catchup for poorer nations.
- **Modifier:** `construction_cost_scaling` in `common/static_modifiers/extra_modifiers.txt` — `goods_input_construction_mult = 1`.
- **Script values:** `common/script_values/extra_script_values.txt` — search for `CONSTRUCTION COST SCALING`.
- **On action:** `construction_cost_scaling_on_action` in `common/on_actions/extra_on_actions.txt`, wired to `on_yearly_pulse_country`.
- **Tuning:** `construction_cost_gdppc_reference`, `construction_cost_floor_ratio` (1x), `construction_cost_ceiling_ratio` (14x), `construction_cost_max_mult` (10 = +1000%).
- **Curve:** Linear interpolation from 0 at floor to `max_mult` at ceiling.
- `goods_input_construction_mult` affects both construction project costs AND ongoing building maintenance.

## Migration Crowding

- **Purpose:** Reduces migration pull to heavily populated states. Prevents unrealistic population concentrations.
- **Modifier:** `migration_crowding` — `state_migration_pull_mult = -0.1` (base, scaled by multiplier).
- **Script values:** `common/script_values/extra_script_values.txt` — search for `MIGRATION CROWDING`.
- **On action:** `migration_crowding_on_action`, wired to `on_yearly_pulse_state`.
- **Density-based:** Uses `state_population / arable_land` as a proxy.
- **Density modifier:** `state_migration_crowding_density_mult` — custom modifier that divides effective density. Applied by `institution_ministry_of_urban_planning` (+10% per level).
- **Scaling:** Quadratic up to the 10x density knee, then linear beyond it. `migration_crowding_ratio` is 0 at the floor, 1.0 at the 10x knee, and can exceed 1.0 in the linear tail. `migration_crowding_mult` uses `4.5 * r^2` below the knee and `9 * r - 4.5` above it, giving a 45% pull penalty at 10x density and 145% at 20x density.
- **Tuning:** `migration_crowding_density_reference` (100000), `migration_crowding_floor_ratio` (1x), `migration_crowding_ceiling_ratio` (10x knee).
- **Split states:** Arable-land-derived threshold and tooltip breakdown values subtract the same-owner regional `arable_land_added` cache, so fully owned split states do not undercount geographic base land.

## State Panel GUI Enhancements

Custom `state_panel_status_item_small` widgets added to `gui/states_panel.gui` for displaying mod-specific state info:

| Widget | Icon | Concept | Content |
|---|---|---|---|
| **Homeland Dynamics** | `state_homelands.dds` | `concept_homeland_dynamics` | Creation/removal thresholds with `GetValueWithBreakdownFor`, annual change chance, change speed modifier |
| **Arable Land** | `wheat_farm.dds` | `concept_arable_land` | Total, geographic base, regional additions, multiplier %, `GetValueWithBreakdownFor('state_arable_land_mult')` |
| **Migration Crowding** | `population.dds` | `concept_migration_crowding` | Population, threshold, migration pull %, urban capacity breakdown |
| **Solar Collector** | `space_elevator.dds` | `concept_solar_collector_array` | Available/total slots, active/reserved/queued |
| **Antimatter Facility** | `power_plant.dds` | `concept_antimatter_facility` | Available/total slots, active/reserved/queued |

- **Loc keys:** `TE_STATE_*_STATUS` (inline text) and `TE_STATE_*_TT` (tooltip) in `localization/english/te_miscellaneous_l_english.yml`.
- **Script values for GUI:** `arable_land_total`, `arable_land_base`, `arable_land_from_modifiers`, `arable_land_mult_pct`, `migration_crowding_pull_pct`, `migration_crowding_threshold_pop`, `homeland_change_chance`, `solar_*`, `antimatter_*` in `common/script_values/extra_script_values.txt`.
- **Concepts:** Defined in `common/game_concepts/extra_concepts.txt` with textures for hoverable tooltip links in loc strings.
- **Tourism panel** breakdown lines also use concepts (`concept_tourism_cities`, `concept_tourism_ports`, `concept_tourism_transit`, `concept_tourism_art`, `concept_tourism_parks`, `concept_tourism_monuments`, `concept_tourism_base_appeal`) for tooltipable category labels.
- **Pattern:** Use `[concept_X]` in loc for hoverable concept links, `[State.GetModifier.GetValueWithBreakdownFor('modifier_key')]` for modifier breakdowns, and `[State.MakeScope.ScriptValue('sv_name')]` for computed values.

## Nuclear Weapons (`je_nuclear_program`)

> See also: `docs/journal_entry_systems.md` for full JE system documentation.

- Journal entry with progress bar for nuclear weapon development.
- Requires Great Power or Major Power + ICBMs tech.
- 2 funding buttons (increase/decrease).
- Diplomatic actions: `nuke_diplo_action`, `tactical_nuke_diplo_action`.
- Treaty articles: `nuclear_disarmament`, `nuclear_program_aid`.
- Events: `nuclear_weapon_events.txt` — nuclear strike response events.

## Banking Cycle (`je_banking_cycle`)

> See also: `docs/journal_entry_systems.md` for full JE system documentation.

- Uses 3 `scripted_progress_bar` instances and 28+ scripted buttons (`cb_*`, `ce_*`, `cw_*`).
- Requires `stock_exchange` tech.
- All banking buttons already have detailed AI weights.
- Events: `banking_cycle_events.txt` — 77 events covering crises from railway bubbles to derivatives, with command-economy and cooperative-ownership variants.

### Monthly Pulse Architecture
The `on_monthly_pulse` calls these scripted effects in order (all in `common/scripted_effects/banking_cycle_effects.txt`):
1. **`banking_cycle_update_fiscal_policy`** — re-applies fiscal policy modifier based on deficit/surplus relative to GDP.
2. **`banking_cycle_advance_variables`** — momentum decay, modifier-driven changes, investment pool, random mean-reversion nudge (scaled by `banking_random_nudge_down/up_value`), apply momentum to value, clamp all variables.
3. **`banking_cycle_check_and_execute_crash`** — asymmetric crash probability check based on bubble pressure × phase, scaled by `banking_crash_chance_multiplier_value`. If crash triggers, fires origin event (.6) and spreads contagion via `banking_cycle_spread_contagion`.
4. **`banking_cycle_apply_phase_modifiers`** — removes old phase + bubble-inertia modifiers, applies current ones based on cycle value and economic law type.
5. **`banking_cycle_update_progress_bars`** — updates the 3 JE progress bars (uses `scope:journal_entry`).
6. **`banking_cycle_cleanup_capital_controls`** — removes capital controls modifier if law/war conditions no longer apply.
7. **`banking_cycle_update_ce_pool_balance`** — under `law_command_economy`, recalibrates the `planning_treasury_pool_balance` modifier on the JE so investment-pool net monthly income targets zero (state treasury funds all investment directly). Also called from `ce_invest_pool_inject` / `ce_invest_pool_withdraw` button effects.

### Banking Law Modifiers
Two `script_only` modifier types allow laws (and potentially techs, PMs, etc.) to tune the banking cycle:

| Modifier | Effect | Type |
|---|---|---|
| `country_banking_random_momentum_mult` | Scales the random nudge that drives cycle volatility. +50% = 50% larger random swings. | percent, neutral |
| `country_banking_crash_chance_mult` | Scales crash probability when bubble pressure is high. +25% = 25% higher crash chance. | percent, bad |

**Current law values:**

| Law | Volatility | Crash Likelihood |
|---|---|---|
| Unregulated Banking | +50% | +25% |
| Free & Mutual Banking | — | -10% |
| Universal Light Prudence | +10% | — |
| Prudential Narrow Banking | -25% | -25% |
| Directed Credit Dev Banks | -25% | -20% |
| Central Bank Independence | -10% | -30% |

**Script values** (in `extra_script_values.txt`):
- `banking_random_nudge_down_value` — base -1, scaled by `(1 + country_banking_random_momentum_mult)`. Used in the random nudge step.
- `banking_random_nudge_up_value` — base +1, scaled the same way.
- `banking_crash_chance_multiplier_value` — base 1.0, adds `country_banking_crash_chance_mult`, clamped to min 0. Multiplied into crash weight.

**To add banking volatility/crash modifiers from other sources** (technologies, PMs, etc.), simply add `country_banking_random_momentum_mult = 0.1` or `country_banking_crash_chance_mult = -0.15` to the modifier block.

### Contagion GDP Scaling
Contagion spread depends on relative GDP sizes (script values in `extra_script_values.txt`):
- **`banking_contagion_min_source_gdp`** — 1% of target country's GDP; source must meet this threshold for contagion to be possible.
- **`banking_contagion_gdp_weight`** — source GDP / target GDP × 5 (capped at 50). Large economies crushing small ones: +25–50 bonus. Small→large: near-zero bonus.

### Event After Blocks
All banking events (77 in `banking_cycle_events.txt`, plus `.6`/`.7` in `minor_events.txt` and `society_technology_events.30`) have `after = { banking_cycle_post_event_refresh = yes }` blocks that re-apply phase modifiers and update progress bars immediately after the player's choice.

### Other Scripted Effects
- **`banking_cycle_random_event_effect`** — cooldown-gated random event dispatcher (12-month cooldown).
- **`remove_all_banking_phase_modifiers`** — removes all 21 phase modifiers (6 market + 6 cmd + 6 coop + 3 bubble inertia).
- **`apply_banking_crash_origin_effects`** — sets cycle vars based on crash severity (called from event .6 options).
- **`apply_banking_contagion_effects`** — subtracts from cycle vars based on origin severity (called from event .7 options).
- **`banking_cycle_post_event_refresh`** — combines `banking_cycle_apply_phase_modifiers` + bar update via `je:je_banking_cycle` accessor (for event context where `scope:journal_entry` is unavailable).

## Colonial Collapse (`colonial_collapse_effect`)

- **Purpose:** After decolonization tech spreads, tiny AI countries (remnants of colonial breakups) are absorbed by culturally similar neighbors or reverted to uncolonized land.
- **Location:** `common/scripted_effects/colonial_collapse_effects.txt`, triggered by `colonial_collapse_on_action` in `common/on_actions/extra_on_actions.txt` (wired to `on_yearly_pulse_country`).
- **Criteria for collapse:** Non-player, non-decentralized, not a subject, single-state, pop < 100k, no decolonization tech, not in a diplomatic play.
- **Resolution order:**
  1. Find culturally similar neighbor → **annex** into that neighbor.
  2. If no cultural match, find any neighbor → **annex**.
  3. If no neighbors → **`set_country_type = decentralized`** (revert to uncolonized).
- **Notifications:** Countries in same strategic region AND great powers receive alerts.

## Treaty Articles with Entity Selection

> **Full design document:** `docs/treaty_articles_reference.md` — read it when implementing a new treaty article.

Key gotchas:
- **Entity input types that work generically** (no GUI changes): `state`, `country`, `strategic_region`, `goods`, `law_type`, `text`.
- **`company` input** requires mod GUI — already implemented in `gui/right_click_menu.gui`, `gui/treaty_draft_panel.gui`, `gui/treaty_panel.gui`.
- **Loc keys needed:** `<name>`, `<name>_desc`, `<name>_effects_desc`, `<name>_article_short_desc`, plus AI desc keys.
- **Direction convention** (`kind = directed`): source_country makes the concession. Use `scope:article_options` (NOT `scope:article`) in `on_entry_into_force`.
- **Company picker:** `WarGoalDraft.GetTarget.GetCompanies` for punitive articles, `GetHolder.GetCompanies` for player's own entities.
- **Invalid triggers:** `is_owned_by_company` and `company` do NOT exist — use `exists = owning_company` + `owning_company = scope:article.input_company`.
- Always guard `scope:article.input_company` with `exists = scope:article.input_company`.

### Enforce Emissions Reduction Treaty

- **Article key:** `enforce_emissions_reduction` in `common/treaty_articles/109_enforce_emissions_reduction.txt`.
- **Purpose:** Forces a **market leader** to maintain all major greenhouse-gas mitigation policies while the treaty is active.
- **Visibility and targeting:** Only visible once warming is active (`temperature_anomaly_display > 0.1`), and only targetable if `scope:other_country` is a market leader (`market_capital.owner = scope:other_country`).
- **Enforcement mechanism:**
  - `on_entry_into_force` applies market-wide mitigation modifiers (`carbon_tax_modifier`, `renewable_investment_modifier`, `emission_standards_modifier`) and country-level mitigation modifiers (`reforestation_subsidies_modifier`, `public_transit_modifier`, `fossil_fuel_divestment_modifier`, `green_building_codes_modifier`) to the source country context.
  - Sets country variable `has_emissions_reduction_treaty` used by GW scripted buttons.
  - `non_fulfillment` freezes the treaty if required mitigation modifiers are removed.
- **Button lock integration:** Remove-button `possible`/`visible` checks in `common/scripted_buttons/timeline_extended_scripted_buttons.txt` now block rollback when `has_emissions_reduction_treaty` is present (for emissions-reduction policies only).

## Space Race (`je_space_race_*`)

Multi-stage competition system simulating a space race between Great Powers. 9 milestones (including a passive waiting JE) with semi-parallel progression, "The First" bonuses, Safe/Ambitious approach choices, and failure mechanics. Solar System Colonization is repeatable with 34 globally-claimed colonies across 5 stages. Extensive cross-system connections to UN, private companies, buildings, and tourism.

### Files
- **Journal Entries:** `common/journal_entries/je_space_race.txt` — 9 JEs (suborbital → interstellar probe, plus interstellar results passive JE, plus repeatable solar colonization with 5 stages)
- **Events:** `events/space_race_events.txt` — ~35 events (completion, failure, notification, site choice, in-progress, hard-sci-fi, cross-system); `events/space_race_colony_events.txt` — 34 colony establishment events (5 stages)
- **Modifiers:** `common/static_modifiers/space_race_modifiers.txt` — approach, milestone (first/subsequent), failure, economic, plus cross-system (tourism, ISS, extraplanetary integration). Colony modifiers (68) and `sr_solar_system_trade` are applied to **JE scope** (`je:je_space_race_solar_colonization`), not country scope.
- **Legacy Cleanup:** `common/scripted_effects/legacy_modifier_cleanup.txt` — removes country-scoped colony modifiers from old saves and re-applies them to JE scope (guarded by `has_journal_entry`).
- **Script Values:** `common/script_values/space_race_values.txt` — progress goals (stage-dependent for colonization), progress rates (with building/company/UN bonuses), failure weights
- **Scripted Buttons:** `common/scripted_buttons/space_race_buttons.txt` — Safe/Ambitious approach, funding increase/decrease
- **Scripted Effects:** `common/scripted_effects/space_race_effects.txt` — milestone completion, failure, cleanup, colony establishment (`sr_establish_colony_effect`), stage advancement (`sr_check_colony_stage_effect`)
- **Scripted Triggers:** `common/scripted_triggers/space_race_triggers.txt` — has_space_program, is_pursuing, can_start, failure_cooldown
- **On Actions:** `common/on_actions/space_race_on_actions.txt` — yearly random events for all in-progress and cross-system events
- **Localization:** Organized into main loc files by `organize_loc.py` (events in `te_events_l_english.yml`, JE labels in `te_journal_entries_l_english.yml`, modifiers in `te_modifiers_l_english.yml`, etc.)

### Milestone Progression (Semi-Parallel)
```
Suborbital Flight (rocketry tech)
    └→ Orbital Flight
        ├→ Moon Landing (space_exploration tech)
        │      └→ Moon Base (reusable_rocketry tech)
        ├→ Outer Solar System Probe (space_exploration tech) [parallel with Moon]
        └→ Mars Landing (reusable_rocketry tech) [parallel with Moon Base]
               ├→ Interstellar Probe (requires Probe + Mars Landing + space_colonization)
               │      └→ Interstellar Results (passive 132-month wait, fires after probe launch)
               └→ Solar System Colonization (requires Moon Base + Mars Landing + space_colonization)
                      [Repeatable: 5 stages × variable colonies = 34 total colonies]
```

### Key Mechanics
- **"The First" Bonus:** Global variables (`sr_global_first_*`) track first achiever. First nation gets ~2× rewards (prestige, innovation max, tech speed) permanently. Subsequent nations get smaller permanent modifiers.
- **Approach Choice:** Safe (slow progress, ~2-7% failure/month) vs Ambitious (fast progress, ~10-22% failure/month). Selected via scripted buttons.
- **Funding Levels:** 0 to `sr_max_funding_level` (base 3, increased by `country_space_race_max_funding_add` modifier from techs like `reusable_rocketry` +1, `space_colonization` +2). Each level costs innovation (-15/level via `sr_space_program_cost` consolidated modifier). Funding and approach are **per-JE** — you can fund moon landing heavily with safe approach while running a cheap ambitious probe.
- **Consolidated Cost:** Single `sr_space_program_cost` modifier with `multiplier = sr_total_space_cost` (sum of all per-JE funding levels + approach overhead: safe=1, ambitious=2). Recalculated via `sr_recalculate_cost` whenever funding or approach changes.
- **Failure:** Reduces progress (50% for ambitious, 15% for safe), adds cooldown (6-24 months), applies decaying negative modifiers. Progress reduction happens inline in the monthly pulse. Cooldown is global (decremented once via `on_monthly_pulse_country`, not per-JE). Does NOT permanently block — just wastes time.
- **Failure Flags:** When failure occurs, per-JE `sr_failed_<milestone>` boolean flags are set before firing failure events. `sr_temporary_safety_review_effect` checks all flags (using `if` not `else_if`) to apply a decaying safety-review modifier to every failed milestone that month.
- **Moon Landing Site:** Special event (space_race_events.5) offers Shackleton Crater (high risk, science windfall) vs Equatorial Plain (low risk, modest rewards).
- **Interstellar Probe:** Launches a probe to Alpha Centauri. On completion, spawns a passive `je_space_race_interstellar_results` JE that ticks 1/month for 132 months (~11 years) using a separate `sr_interstellar_transit_progress` variable (not shared `sr_milestone_progress`). When complete, fires event 60 (Interstellar Probe Data Received) which randomly selects one of 30 possible discoveries across 4 categories:
  - **Category I: Dead Worlds & Data** (40% chance, 8 results) — Barren worlds, asteroid maps, stellar remnants. Grants `sr_probe_dead_worlds_data` (modest prestige/research/innovation).
  - **Category II: Astrophysical Wonders** (30%, 7 results) — Ringed terrestrials, global oceans, runaway greenhouses. Grants `sr_probe_astro_wonders_data` (good prestige/research/innovation/cultural pull).
  - **Category III: Biological Discovery** (20%, 9 results) — Atmospheric biosignatures, alien vegetation, exotic biochemistry. Grants `sr_probe_biological_data` (major prestige/research/innovation/cultural pull).
  - **Category IV: Intelligence & Tech-signatures** (10%, 6 results) — Orbital debris, technogenic gases, artificial light. Grants `sr_probe_intelligence_data` (exceptional prestige/research/innovation/cultural pull).
  - Discovery selection uses two-stage `random_list`: first picks category by weight, then picks specific result uniformly within category. Result stored in `sr_probe_category` and `sr_probe_result` variables. Event uses triggered_desc blocks for category-specific titles, flavors, and result-specific descriptions.
- **Solar System Colonization (Repeatable):** Each completion establishes one colony at a random unclaimed location in the current stage. Colonies are tracked via global variables (`sr_colony_*`), making them first-come-first-served across all nations. Stage advances when all locations in a stage are claimed. Goals increase per stage (100/120/140/160/200). JE only sets `sr_completed_solar_colonization` after all 34 colonies across 5 stages are claimed.
  - **Stage 1:** Mars (5) + Asteroids (5) = 10 colonies
  - **Stage 2:** Jupiter system (6) + Venus clouds (1) = 7 colonies
  - **Stage 3:** Mercury (1) + Saturn moons (5) = 6 colonies
  - **Stage 4:** Uranus moons (4) + Neptune moons (2) = 6 colonies
  - **Stage 5:** Kuiper Belt/Oort Cloud (5) = 5 colonies
- **Late-Game Economic Rewards:** Interstellar Probe grants one of 4 category-specific modifiers (see Interstellar Probe above), all colonies complete grants `sr_solar_system_trade`.
- **Progress Sources:** Base rate + Aerospace Industry levels + Space Elevator + Extraplanetary Base + UN Space Partnership + SpaceX company + funding + tech bonuses.

### Cross-System Connections
| System | Connection |
|--------|-----------|
| **UN** | `un_space_partnership_modifier` boosts progress (+0.3/+0.4 safe/ambitious) and reduces failure risk (-2). ISS cooperation event (52) fires for UN members. UN vote topic `un_vote_topic_space` (event un_events.19). |
| **Private Companies** | `company_spacex` boosts progress (+0.3/+0.4) and reduces failure risk (-2). Event 50 (private sector breakthrough) fires when SpaceX exists. |
| **Buildings** | `building_aerospace_industry` levels 3/5 scale progress. `building_space_elevator` provides major bonus (+0.4/+0.6) and reduces failure (-2). `building_space_mine` (extraplanetary base) boosts colonization progress (+0.2/+0.3). Events 41, 53, 55 create direct building interactions. |
| **Tourism** | Event 51 fires after orbital achievement if tourism industry exists. Grants `sr_space_tourism_boost` (tourism output +5%). Space tourism PM (`pm_space_tourism`) already exists in tourism industry building. |
| **Society Tech Events** | `society_technology_events.18` (space colonization) and `.19` (colonial governance) fire based on aerospace industry levels and space elevator. These are separate from but thematically connected to space race milestones. |

### Variables (Country Scope)
| Variable | Description |
|----------|-------------|
| `sr_active_*` | Active milestone flag (suborbital, orbital, etc.) |
| `sr_completed_*` | Completed milestone flag |
| `sr_was_first_*` | Country was first to achieve milestone |
| `sr_active_milestone` | Generic "has active milestone" flag |
| `sr_progress_<m>` | Per-JE progress toward milestone (e.g. `sr_progress_suborbital`) |
| `sr_funding_<m>` | Per-JE funding level (0 to sr_max_funding_level) |
| `sr_safe_<m>` / `sr_ambitious_<m>` | Per-JE approach flags |
| `sr_failed_<m>` | Per-JE failure flag (set in pulse, read by events) |
| `sr_interstellar_transit_progress` | Interstellar probe transit progress (passive JE, not per-JE) |
| `sr_funding_level` | **Proxy variable** — set from per-JE funding before script value evaluation in monthly pulse. Safe because script values evaluate immediately. |
| `sr_failure_cooldown` | Global months until failure can occur again (decremented once/month via on_action) |
| `sr_progress_boost` | **Proxy variable** — set before calling `sr_boost_active_milestones` |
| `sr_moon_site_shackleton/equatorial` | Moon landing site choice |
| `sr_colony_count` | Total colonies established by this country |
| `sr_probe_launched` | Interstellar probe has been launched (triggers results JE) |

### Global Variables
| Variable | Description |
|----------|-------------|
| `sr_global_first_suborbital` | First suborbital claimed |
| `sr_global_first_orbital` | First orbital claimed |
| `sr_global_first_moon_landing` | First Moon landing claimed |
| `sr_global_first_probe` | First outer system probe claimed |
| `sr_global_first_moon_base` | First Moon base claimed |
| `sr_global_first_mars_landing` | First Mars landing claimed |
| `sr_global_first_interstellar_probe` | First interstellar probe launched |
| `sr_colonization_stage` | Current colony stage (1-5), advances when all locations in stage are claimed |
| `sr_all_colonies_complete` | All 34 colonies have been claimed |
| `sr_colony_*` (34 variables) | Individual colony claimed flags (e.g. `sr_colony_valles_marineris`, `sr_colony_europa`, `sr_colony_sedna`) |

### Important Notes
- **`building_space_program` is a monument** (`expandable = no`, single level). DO NOT check `level >= 3` etc. on it — use `building_aerospace_industry` for level-scaled bonuses instead.
- **Colony modifiers are JE-scoped.** All 68 colony modifiers and `sr_solar_system_trade` are applied to `je:je_space_race_solar_colonization`, not to the country directly. The colonization JE stays alive indefinitely while colonies exist (passive mode with hidden buttons when all 34 colonies are claimed). This means colony modifier effects still apply to the country, but display in the JE panel.
- **Localization is auto-organized** by `organize_loc.py` into category-specific files. Space race loc keys spread across `te_events_l_english.yml`, `te_journal_entries_l_english.yml`, `te_modifiers_l_english.yml`, `te_miscellaneous_l_english.yml`, and `te_concepts_l_english.yml`.

## Wonder Buildings (Construction Site Pattern)

> **Full design document:** `docs/wonder_buildings_reference.md`

Two-phase construction pattern: buildable construction site → completed building via scripted effect.

- **Space Elevator:** `building_space_elevator_construction_site` → `building_space_elevator`. Scripted effect: `space_elevator_construction` in `extra_effects.txt`. On-action: `space_elevator_on_action` (monthly state pulse). Max 20 levels.
- **Solar Collector:** Three-building system (construction site → orbital hub → ground receivers). Hub enables receiver slots via `country_solar_receiver_max_level_add`. Max 10 levels.
- **Construction progress:** Monthly based on `(occupancy / 12) * speed_multiplier`. Speed PMs: paused=0, slow=0.25, medium=0.5, fast=1.0.
- **Custom modifier types:** `building_weekly_*_progress` and `building_total_*_progress` (percent, script_only) in `extra_modifier_types.txt`.

## On-Actions Reference

The mod uses 11 on-action files under `common/on_actions/`. These wire mod logic into engine hooks — either **pulse-based** (fires periodically for all relevant scopes) or **immediate** (fires the instant a specific game event occurs).

### File Index

| File | Purpose | Hook Type |
|------|---------|-----------|
| `extra_on_actions.txt` | Central hub: pulse wiring, dynamic modifiers, immediate triggers, company cleanup | Mixed |
| `fmc_on_actions.txt` | FMC map update triggers on diplomatic/territorial changes | Immediate |
| `headlines.txt` | "World first" tech notifications (`on_acquired_technology`) | Immediate |
| `law_events_on_actions.txt` | Law enactment checkpoint events (advance/debate/stall) | Immediate |
| `langreform_events_on_actions.txt` | Language reform yearly random events | Pulse |
| `minor_events_on_actions.txt` | Miscellaneous yearly random events | Pulse |
| `repeatable_events_on_actions.txt` | Generic repeatable yearly events | Pulse |
| `social_tensions_on_actions.txt` | Social/political tension yearly events | Pulse |
| `space_race_on_actions.txt` | Space race in-progress and cross-system yearly events | Pulse |
| `un_on_actions.txt` | UN formation and recurring member events | Pulse (monthly) |
| `wonder_events_on_actions.txt` | Wonder building narrative events | Pulse (monthly) |

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
- `tourism_on_action` — tourism income/throughput
- `resettlement_transfer_on_action` — population transfer

**`on_monthly_pulse`** (Root = global):
- `city_rank_on_action` — city tier updates
- `global_warming_events_on_action` — GW threshold & recurring events

**`on_monthly_pulse_country`** (Root = Country):
- `ministry_of_thought_control_on_action` — loyalist manipulation
- `remove_invalid_buildings` — space program placement validation
- `cheaty_on_action` — debug modifier (disabled)
- `combined_arms_update_on_action` — military doctrine bonuses
- `investment_pool_setup_on_action` — investment pool management
- `character_update_on_action` — character trait updates
- `international_relations_events_on_action` — diplo events
- `decolonization_events_on_action` — decolonization narrative
- `movement_events_te_on_action` — political movement events
- `society_technology_events_on_action` — society tech events
- `world_war_events_on_action` — world war events
- `overbuild_protection_on_action` — prevents wonder overbuilding

**`on_yearly_pulse_state`** (Root = State):
- `global_warming_update_on_action` — GHG emissions calculation
- `remove_or_create_homelands_on_action` — dynamic homeland changes
- `violent_hostility_on_action` — cultural violence
- `migration_crowding_on_action` — migration pull reduction
- `tourism_update_on_action` — tourism modifier refresh
- `religious_mission_conversion_on_action` — treaty-based conversion

**`on_yearly_pulse_country`** (Root = Country):
- `tech_spread_on_action` — technology diffusion
- `excess_private_construction_on_action` — construction cost penalty
- `fix_incompatible_laws` — auto-fix illegal law combos
- `construction_cost_scaling_on_action` — GDP-based construction costs
- `colonial_collapse_on_action` — tiny AI country absorption
- `assign_aptitude_traits_on_action` — character trait assignment

### Immediate Triggers (`extra_on_actions.txt`)

These fire instantly when the engine event occurs, providing same-tick responsiveness:

**`on_company_disbanded`** (Root = Country, scope:company = disbanded company):
- Calls `remove_disbanded_company_buildings_effect` on every state to remove buildings belonging to the disbanded company. Uses a 64-entry if/else_if mapping in `common/scripted_effects/company_building_cleanup_effects.txt`.

**`on_building_built`** (Root = Building):
- When a barracks is built, recalculates `apply_combined_arms_bonuses` for the owning country (new combat unit type enters a formation). Only fires if `country_combined_arms_bonus_enabled_bool` is true.
- Also used by FMC (`fmc_on_actions.txt`) to trigger map updates.

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
- `character_update_on_action` — trait updates for new tech
- `te_modifier_update_on_technology_on_action` — state modifier refresh

**`on_law_activated`** (Root = Law scope):
- `fix_incompatible_laws_from_law_scope` — law compatibility
- `language_reform_law_on_action` — language reform init/cleanup
- `te_modifier_update_on_law_on_action` — state modifier refresh
- `radical_law_backlash_on_action` — backlash events for radical laws

**`on_law_enactment_started`** (Root = Law scope):
- Fires `minor_events_timelineextended.2` (law enactment notification)

**`on_merge_markets`** (Root = dissolving market, scope:market = absorbing market):
- `gw_market_join_on_action` — copies market leader's GW policy modifiers to new member


### FMC Immediate Triggers (`fmc_on_actions.txt`)

The FMC system hooks many engine events to keep the map up to date:
- `on_merge_markets`, `on_create_market` — market changes
- `on_country_released_as_independent/own_subject/overlord_subject` — country releases
- `on_country_formed`, `on_capitulation`, `on_enemy/ally_capitulated_notification` — country events
- `on_diplo_play_back_down`, `on_war_end` — diplomatic resolutions
- `on_revolution_start`, `on_secession_start` — internal conflicts
- `on_wargoal_enforced` — war results
- `on_start_expanding_building`, `on_building_expanded`, `on_building_built` — building events

### Scope Chain Limitation (Important)

Building and institution scopes **do not support variables or modifiers**. Calling `te_update_state_modifiers` (which uses `add_modifier = { multiplier = script_value }` that evaluates through the parent scope chain) from building-scope hooks like `on_building_built` or `on_production_method_changed` causes cascading errors. The yearly state pulse and law/technology hooks handle these slow-changing modifiers instead.

## AI Weights Guidelines

- **Journal entries:** `weight` determines priority in the JE list. Global issues use 1000+, personal/national issues use 10.
- **Scripted buttons:** `ai_chance = { value = 0 ... }` — base value with conditional `add` modifiers.
- **Diplomatic actions:** Key fields: `evaluation_chance`, `will_propose`, `propose_score`, `will_break`.
- **Treaty articles:** Key fields: `article_ai_usage = { offer request none }`, `evaluation_chance`, `inherent_accept_score`.
- Always look at **vanilla files** for AI pattern reference.

## Decolonization System (`je_colonial_empire`)

### Overview

The decolonization system models the decline of colonial empires through a journal entry with a stability progress bar, scripted buttons for colonial policies, and a series of events. The system is designed so that **most colonial powers except the top 2-3 GPs will lose most of their colonies** after the `decolonization` tech is researched (era 7).

### Architecture

Three layers:
1. **Gate & Progress Bar:** `je_colonial_empire` activates when a country has colonial states and `decolonization` tech. The `colonial_stability_bar` (0-100, starts at 50) tracks how stable the empire is. At 0 the empire collapses; at 100 it solidifies.
2. **Player Interaction:** 8 scripted buttons (invest, garrison, assimilate, release, planned decolonization) let the player (and AI) manage colonies. Each button costs bureaucracy/authority and adjusts the stability bar.
3. **Events:** 21 events fire from `decolonization_events_on_action` (monthly pulse), covering colonial negotiations, crackdowns, releases, GP stance choices, post-independence transitions, and the Suez Crisis model.

### Files

| File | Purpose |
|---|---|
| `common/journal_entries/je_colonial_empire.txt` | JE definition with stability bar, status_desc thresholds |
| `common/scripted_progress_bars/extra_progress_bars.txt` | `colonial_stability_bar` monthly_progress formula |
| `common/script_values/colonial_empire_values.txt` | Script values: colony counts, GP condemner/supporter counts, cost formulas |
| `common/scripted_triggers/colonial_empire_triggers.txt` | Macro-region definitions, `is_overseas_colonial_state` |
| `common/scripted_buttons/colonial_empire_buttons.txt` | 8 JE buttons for colonial policy management |
| `common/scripted_effects/decolonization.txt` | `form_decolonized_country` effect |
| `common/scripted_effects/colonial_collapse_effects.txt` | AI country absorption for tiny post-colonial remnants |
| `common/on_actions/extra_on_actions.txt` | `decolonization_events_on_action` wiring |
| `events/decolonization_events.txt` | All 21 decolonization events |
| `common/static_modifiers/extra_modifiers.txt` | 40+ decolonization modifiers |

### Stability Bar Formula (`colonial_stability_bar.monthly_progress`)

**Downward pressure (decolonization):**
- Base drift: **-1.0**/month
- Imperial overstretch: **-0.15** × number of colonial states
- Non-GP penalty: **-0.5** if not a great power
- Era pressure: **-1.5** if `globalization` researched, else **-0.75** if `knowledge_economy` researched
- GP condemnation: **-0.6** per GP with `gp_anti_colonial_stance`
- Low acceptance states: **-0.4** per state
- Wartime disruption: **-0.5** if at war
- Negative event flag: **-1.0**

**Upward pressure (stabilization):**
- GP rank bonus: **+0.3**
- GP support: **+0.3** per GP with `gp_pro_colonial_stance`
- Development investment policy: **+0.8**
- Military garrison policy: **+0.5**
- Cultural assimilation policy: **+0.6**
- Well-integrated states: **+0.5** per high-acceptance state
- Positive event flag: **+1.0**

**Design intent:** A typical GP with 5 colonies nets approximately -0.5 to -1.0/month even with policies active. Only GPs with very few, well-integrated colonies and no GP condemnation can stabilize. Late-game techs (knowledge_economy, globalization) make holding colonies nearly impossible.

### Events (1-21)

Events 1-15 handle the core colonial cycle: negotiations, crackdowns, releases, GP stances, cultural identity, post-independence economics, nationalization.

**Post-Independence Events (16-21):**
- **Event 16 "The Partition Question"** — New nations near neighbors with shared heritage can demand unification (claims+tension), propose federation (truces+goodwill), or accept borders (stability).
- **Event 17 "Whose Country Is This?"** — Border disputes between two recently-formed nations. Options: press claims, seek mediation, accept borders.
- **Event 18 "The Strongman's Promise"** — Political instability in new nations. Options: military coup (authority+SoL loss), democratic transition (legitimacy), one-party state (authority+research).
- **Event 19 "The Crisis" (Suez model)** — GP reacts when a former colony nationalizes assets. Options: military intervention (infamy 15, **triggers Event 20** for all other GPs), economic sanctions (infamy 5), accept outcome. This is the flagship "interactive" GP event.
- **Event 20 "Gunboats in the Harbor"** — Other GPs respond to military intervention. Options: condemn (+moral authority, relations penalties to intervener), support intervention, stay neutral. **Not in on_actions** — triggered directly by Event 19 option A.
- **Event 21 "The Non-Aligned Path"** — New nations choose between competing superpowers or non-alignment.

### AI Behavior Tuning

AI weights across events are tuned to favor decolonization:
- Release/negotiate options have base weights of 2-4 with bonuses for non-GPs and high GP condemnation
- Crackdown/suppress options have base weights of 1
- The `ce_planned_decolonization` button fires when 3+ GPs condemn or 3+ states have low acceptance; non-GPs get an extra +30 weight bonus
- GP stance event (14): condemn colonialism base 5 with knowledge_economy bonus; support base 0

## Independence Nationalization Event (`decolonization_events.15`)

- **Purpose:** When a country gains independence, presents a choice about foreign-owned assets.
- **Trigger:** `on_become_independent` on_action → fires event with 1-tick delay.
- **Condition:** At least one foreign country owns >5% of the new country's GDP.
- **Branching description:** Uses `first_valid` + `triggered_desc` — violent version if `is_at_war = yes`, peaceful version otherwise.
- **Options:**
  - **(A) Full nationalization:** Seize all foreign assets. +10 infamy, -60 relations with all foreign owners, prestige boost, throughput penalty. Loyalists among lower strata, trade unions approve, industrialists oppose.
  - **(B) Selective nationalization:** Strategic sectors only. +5 infamy, -30 relations, moderate prestige boost.
  - **(C) Protect foreign property:** No infamy, +20 relations, foreign investment continues. Radicals among lower strata, industrialists approve.
- **Modifiers:** `independence_nationalization_modifier`, `selective_nationalization_modifier`, `foreign_property_protected_modifier` (all timed, decaying).
- **Notification:** `nationalization_notice` sent to affected foreign countries.
- **Files:** `events/decolonization_events.txt` (event 15), `common/on_actions/extra_on_actions.txt` (hook), `common/static_modifiers/extra_modifiers.txt` (3 modifiers), `common/messages/extra_messages.txt` (notification).

## Dynamic Treaty Names

- **Purpose:** Gives thematic names to treaties containing mod-specific treaty articles (instead of generic "Treaty of [City]").
- **How it works:** Each entry in `common/dynamic_treaty_names/` has a `trigger` (checked against the treaty's articles via `any_scope_article_option = { has_type = X }`) and a `weight` (higher = more likely). The engine picks the highest-weighted matching name.
- **Coverage by article type:**
  - Corporate: `seize_company`, `disband_company`, `enforce_privatization`, `corporate_concessions`, `free_port_concession`, `money_transfer`
  - Humanitarian: `minority_protection`, `cultural_exchange`, `religious_mission_rights`
  - Military: `dmz_and_disarmament`
  - Diplomatic/Aid: `education_aid`, `healthcare_aid`, `request_influence`, `extend_influence`, `crisis_resolution`
- **Loc variables:** `$SIGNING_LOCATION$`, `[FIRST_COUNTRY.GetAdjectiveNoFormatting]`, `[SECOND_COUNTRY.GetAdjectiveNoFormatting]`, `[FIRST_COUNTRY.GetNameNoFormatting]`.
- **Files:** `common/dynamic_treaty_names/te_dynamic_treaty_names.txt`, localization in `te_miscellaneous_l_english.yml`.

## Nuclear Program Pause (Treaty Article)

- **Purpose:** Freezes the target country's nuclear weapons program, halting progress toward nuclear capability.
- **Article type:** Directed (source = concession-maker whose program is frozen, target = requestor).
- **Mechanism:** Applies a timed modifier that blocks nuclear progress via a journal entry weekly pulse handler; the JE checks whether the country has the modifier and skips progress if so.
- **Key modifier:** `nuclear_program_paused_modifier` — applied to source country on entry into force.
- **AI logic:** AI will accept if it doesn't yet have nukes and the other party is much stronger, or if relations are very high. AI proposes this against rivals pursuing nuclear weapons.
- **Files:** `common/treaty_articles/extra_treaty_articles.txt` (article definition), `common/static_modifiers/extra_modifiers.txt` (modifier), localization in main loc file.

## Population Transfer (Treaty Article)

- **Purpose:** Moves minority pops of the target country's primary culture(s) from the source country to the target country. Models forced population exchanges (e.g., Treaty of Lausanne).
- **Article type:** Directed, one-time effect on entry into force.
- **Mechanism:**
  1. `on_entry_into_force` saves scopes via `scope:article_options.source_country` / `.target_country` (critical scoping pattern — see `docs/scripting_best_practices.md`).
  2. Calls `population_transfer_effect` scripted effect.
  3. The effect iterates target country's primary cultures, for each culture finds source-country states with matching pops via population-weighted random selection (tiered modifiers since `state_population` is a trigger, not a value).
  4. Uses `move_pop` to transfer pops, increments a counter variable.
  5. Applies `population_transfer_disruption` timed modifier to affected states, scaled by transfer count.
- **Key scripted effect:** `population_transfer_effect` in `common/scripted_effects/extra_effects.txt`.
- **Key modifier:** `population_transfer_disruption` — reduces state throughput and increases mortality, applied per-state.
- **Files:** `common/treaty_articles/extra_treaty_articles.txt`, `common/scripted_effects/extra_effects.txt`, `common/static_modifiers/extra_modifiers.txt`, localization.

## Intelligence Sharing Defense Shield

- **Purpose:** Countries with an intelligence sharing pact benefit from their partner's covert defense strength. The weaker partner receives a shield equal to 50% of the difference between their base defense and their strongest partner's base defense.
- **Mechanism:** Uses the "prior variable subtraction" pattern for modifier recalculation. Each country stores `intel_shield_mult` (the multiplier currently applied to their shield modifier). When recalculating:
  1. Reads own total defense from `modifier:country_covert_defense_*_add` (3 types summed).
  2. Subtracts `3 * intel_shield_mult` to get base defense (since the shield adds multiplier to each of 3 types).
  3. For each partner, reads their total defense and subtracts `3 * PREV.var:intel_shield_mult` to get their base.
  4. Computes `boost = (partner_base - own_base) * 0.5`, takes the best across all partners.
  5. Removes old modifier, applies new one with the computed multiplier, stores it for next tick.
- **Key modifier:** `intelligence_sharing_defense_shield_modifier` in `common/static_modifiers/extra_modifiers.txt` (each defense type = 1, applied with multiplier).
- **Key effect:** `update_intel_sharing_defense` in `common/scripted_effects/treaty_article_effects.txt`.
- **Wiring:** Called from `on_yearly_intel_sharing_defense` on_action, triggered by `on_yearly_pulse_country` in `common/on_actions/treaty_article_events_on_actions.txt`.
- **Critical pattern:** Modifier values are NOT recalculated within a single effect block, so `modifier:X` reads after `remove_modifier` still include the old value. The `intel_shield_mult` persistent variable allows subtracting the prior contribution. See `docs/scripting_best_practices.md` § "Modifier Values Are NOT Recalculated Within a Single Effect Block".

## Heir Education System (`je_heir_education`)

### Overview
Allows monarchies to shape their heir's education through focus selection and random events. Inspired by EU4/CK3 heir education mechanics. The system uses a monthly probabilistic pulse where active focuses each have a small chance to advance investments, ultimately resolving into ruler aptitude traits, ideology, and interest group alignment when the heir reaches adulthood.

### Architecture
- **Journal Entry:** `je_heir_education` — main controller with monthly pulse, scripted buttons, progress bar
- **Scripted Effects:** `heir_education_effects.txt` — gain effects (intelligence-modified), resolve effect (5-tier), adult initialization, cleanup, IG reactions, non-heir trait assignment
- **Scripted Buttons:** `heir_education_buttons.txt` — 14 toggle buttons (enable/disable pairs for 8 focuses)
- **Progress Bar:** `heir_education_progress_bars.txt` — 0-20 range
- **Static Modifiers:** `heir_education_modifiers.txt` — innovation cost, grace period, event cooldown
- **Events:** `heir_education_events.txt` — 3 events (Promising Pupil, Difficult Student, Foreign Correspondence)
- **Traits:** `ruler_aptitude_traits.txt` — 15 traits (5 tiers × 3 categories: admin, diplomat, commander)
- **Localization:** Spread across `te_concepts_l_english.yml` (traits), `te_journal_entries_l_english.yml` (JE status), `te_events_l_english.yml` (events)

### Key Variables (Country Scope)
| Variable | Purpose |
|---|---|
| `heir_ed_admin` / `diplo` / `military` | Trait investment counters (0+) |
| `heir_ed_ideology` | Ideology direction (positive=progressive, negative=conservative) |
| `heir_ed_ig_radical` / `moderate` / `regressive` | IG alignment counters |
| `heir_ed_total` | Sum of all investments (progress bar value) |
| `heir_ed_intelligence` | Hidden (1-5), affects gain amount per tick |
| `heir_ed_focus_*` | Active focus flags (8 possible) |

### 5-Tier Trait Resolution
Investment levels map to probability distributions across 5 tiers:

| Investment | Terrible | Poor | Average | Skilled | Exceptional |
|---|---|---|---|---|---|
| 0 (none) | 35% | 30% | 25% | 8% | 2% |
| 1-2 (light) | 15% | 25% | 35% | 20% | 5% |
| 3-4 (moderate) | 5% | 15% | 30% | 35% | 15% |
| 5-7 (heavy) | 2% | 5% | 18% | 45% | 30% |
| 8+ (extreme) | 0% | 2% | 10% | 38% | 50% |

### Intelligence System
- Randomly assigned 1-5 (uniform) at JE initialization
- **High (4-5):** 30% chance of double gain (+2) per successful pulse
- **Medium (3):** Standard +1 gain
- **Low (1-2):** 25% chance of wasted opportunity (no gain on success)
- Player sees subtle hint: "quick study" (4-5) or "struggles to grasp concepts" (1-2)
- Effectively creates a 1.5%-4.5% range around the 3% base pulse chance

### Monthly Pulse Mechanics
- **Base chance per focus:** 3% per month (down from original 5%)
- 8 possible focuses: admin/diplo/military (trait), progressive/conservative (ideology), radical/moderate/regressive (IG)
- Each successful pulse calls an intelligence-modified gain effect
- IG reaction modifiers applied on each gain (short-duration decaying)

### Rebel Child Mechanic
- 8% chance at resolution that ideology score inverts (`multiply = -1`)
- Applied BEFORE ideology is mapped to specific ideology types
- Creates strategic tension: focused ideology investment isn't guaranteed

### Adult Heir Initialization
At JE start, heirs older than newborn receive pre-initialized investments:
- **Age 5-9:** 40% chance of +1 per trait
- **Age 10-14:** +1-2 per trait (50/50)
- **Age 15+:** +1-3 per trait (25/50/25) + random ideology lean ±1 + random IG lean

### Non-Educated Characters
`assign_aptitude_traits_effect` assigns traits to characters who reach adulthood without education: 20% terrible, 30% poor, 35% average, 12% skilled, 3% exceptional. Generals/admirals get a better military distribution (5/15/30/35/15).

### Simulation
`sim_heir_education.py` — Monte Carlo simulation (20,000 runs per scenario) that validates the probability distributions. Key scenarios: newborn with 1-3 focuses, adult heirs, neglected education, intelligence impact analysis. Run this to tune parameters before changing thresholds.

### Design Lessons
- **Simulation-driven tuning:** Write a Python sim BEFORE implementing Paradox script changes. The sim reveals non-obvious distribution outcomes (e.g., that even terrible heirs have a small exceptional chance, creating memorable moments).
- **Intelligence as gain modifier, not chance modifier:** Modifying the gain AMOUNT instead of the pulse CHANCE keeps Paradox script clean (no need for cascading if/else with different random_list weights per intelligence tier). One `random_list = { 3 = { gain_effect } 97 = { } }` per focus regardless of intelligence.
- **Scripted effects for gain encapsulation:** Each focus has a dedicated `heir_ed_gain_X` effect that handles intelligence, variable updates, bar progress, and IG reactions. This keeps the JE monthly pulse compact.
- **`change_variable multiply = -1`** is valid Paradox script for negation (used in rebel child mechanic).

## Social Movement Journal Entries (MVP)

Eight journal entries tracking major social/political movements of the modern era. Each has a `modifiers_while_active` modifier, 2 monthly pulse events (3 options each), a fail-state event, and completion/timeout modifiers.

### Files
- **JE Definitions:** `common/journal_entries/je_lgbtq_rights.txt`, `je_second_wave_feminism.txt`, `je_human_augmentation.txt`, `je_environmental_crisis.txt`, `je_digital_rights.txt`, `je_post_scarcity.txt`, `je_mental_health.txt`, `je_decline_of_religion.txt`
- **Events:** `events/lgbtq_events.txt`, `feminist_events.txt`, `augmentation_events.txt`, `environmental_events.txt`, `surveillance_events.txt`, `post_scarcity_events.txt`, `mental_health_events.txt`, `secular_events.txt`
- **Modifiers:** `common/static_modifiers/extra_modifiers.txt` (search for the JE section headers)
- **Design doc:** `docs/future_journal_entry_ideas.md`

### Summary Table

| JE | Trigger Tech | Law Group | Complete | Fail |
|---|---|---|---|---|
| LGBTQ+ Rights | `LGBTQ_rights_movement` | `lawgroup_LGBTQ_rights` | `law_full_equality_and_protection` | `law_active_persecution` + `social_justice_movements` |
| Second-Wave Feminism | `second_wave_feminism` | `lawgroup_womens_rights` | `law_protected_class` | `law_no_womens_rights` + `contraceptive_pill` |
| Human Augmentation | `biohacking_and_human_augmentation` / `brain_computer_interfaces` | `lawgroup_human_augmentation` | `law_regulated_augmentation_market` / `law_mandatory_augmentation` | `law_human_purity` |
| Environmental Crisis | `environmental_movement` / `pollution_control` | ministry of environment institution | `law_ministry_of_the_environment` + investment ≥ 3 | no ministry + `clean_energy_technologies` |
| Digital Rights | `automated_surveillance` / `cybersecurity` | `lawgroup_privacy_rights` | `law_strong_privacy_rights` | `law_intrusive_surveillance` + ministry of intel |
| Post-Scarcity | `universal_basic_income` | `lawgroup_welfare` | `law_post-scarcity` | (timeout only) |
| Mental Health | `mental_health_awareness` | `lawgroup_criminal_justice` | `law_rehabilitation_focused_criminal_justice` + social_security ≥ 4 | `law_punishment_focused` + `decline_of_organized_religion` |
| Decline of Religion | `decline_of_organized_religion` | `lawgroup_ministry_of_religion` | `law_no_ministry_of_religion` | ministry + investment ≥ 4 |

### Event Design Patterns

Each JE has **5 monthly events + 1 fail-state event** (except Post-Scarcity which has 5 monthly + no fail). Events follow these design principles:

- **Three-option structure:** Option A (progressive/reformist), Option B (moderate/compromise), Option C (regressive/oppressive). Most options have meaningful tradeoffs — treasury costs for spending decisions, opposition radicals for partisan choices.
- **Fire-once events:** Policy-debate events that represent one-time historical moments use `has_global_variable` gates so they only fire once per game. Currently: `lgbtq_military_debate_happened`, `women_military_debate_happened`, `ai_predictive_policing_debate_happened`, `ai_bureaucracy_debate_happened`, `state_religion_debate_happened`.
- **Law-gated options:** Some regressive options require specific laws to be available (e.g., surveillance expansion requires `law_intrusive_surveillance`). AI chance modifiers weight options contextually based on current laws.
- **Law-gated AI weights:** AI preference for certain options increases when the country has relevant laws (e.g., `law_laissez_faire` boosts "protect industry" choice, `law_outlawed_dissent` boosts "label as terrorists" choice).
- **Cooldowns:** Routine debate events use `normal_modifier_time`; serious incidents and fire-once events use `long_modifier_time`.

### Files

| System | JE Definition | Events | Modifiers |
|---|---|---|---|
| LGBTQ+ Rights | `common/journal_entries/je_lgbtq_rights.txt` | `events/lgbtq_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Second-Wave Feminism | `common/journal_entries/je_second_wave_feminism.txt` | `events/feminist_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Human Augmentation | `common/journal_entries/je_augmentation_debate.txt` | `events/augmentation_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Environmental Crisis | `common/journal_entries/je_environmental_crisis.txt` | `events/environmental_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Digital Rights | `common/journal_entries/je_digital_rights.txt` | `events/surveillance_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Post-Scarcity | `common/journal_entries/je_post_scarcity.txt` | `events/post_scarcity_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Mental Health | `common/journal_entries/je_mental_health.txt` | `events/mental_health_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Decline of Religion | `common/journal_entries/je_secular_transition.txt` | `events/secular_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Religious Revivals | — (no JE, event-driven) | `events/religious_revival_events.txt` | `common/static_modifiers/extra_modifiers.txt` |

## Religious Revival Events

**Purpose:** Counterbalance the natural decline of the Devout IG caused by urbanization, literacy, and modernization techs. Inspired by 20th/21st century religious-political movements.

**Mechanism:** 7 events fire from the `society_technology_events_on_action` random list, each tied to a different social tech (eras 7–9). Each offers three options:
- **Strong option:** Adds a permanent modifier with large `interest_group_ig_devout_pop_attraction_mult` (0.25–0.50) and `interest_group_ig_devout_pol_str_mult` (0.20–0.50). Some include costs (authority, research speed, prestige). These stack — a player who embraces multiple religious movements will see a very strong Devout IG.
- **Moderate option:** Adds a decaying modifier lasting 20 years with moderate attraction/pol_str bonuses.
- **Secular option:** No devout boost or negative (radicals), with alternative benefits.

**Law Gating:**
- **State atheism** blocks events 1, 2, 4, 5, 6 (mainstream religious organizing implausible under state suppression).
- Events 3 (Liberation Theology) and 7 (Faith-Based Welfare) CAN fire under state atheism — representing underground religious movements for justice/welfare. They get special variant text describing clandestine faith communities.
- AI weights are modified by relevant laws: `law_ministry_of_religion` boosts embrace options, `law_total_separation` and `law_no_ministry_of_religion` favor secular options.

**Religion-Variant Localization:**
- Descriptions and flavor text use `first_valid`/`triggered_desc` blocks based on the country's religion heritage trait (`heritage_islamic`, `heritage_dharmic`, `heritage_jewish`).
- **Islamic variants:** Reference ummah, Quran, fatwas, zakat, masjid, khutba, dawah, Sharia.
- **Dharmic variants:** Reference dharma, swamis/gurus, ashrams, satsangs, seva, darshan, saffron, Hindutva.
- **Jewish variants:** Event 4 has a religious Zionist variant.
- **Default:** Covers Christian and other religions with generic or broadly Western religious language.
- Some events also have variant titles (e.g., "The Satellite Minbar" for Islamic event 2, "One Ummah, One Law" for Islamic event 4).

**Removal:** The "Secularization Campaign" decision (requires `decline_of_organized_religion` tech) removes all permanent religious revival modifiers at once, with a radicals cost.

**Events:**
1. **The Moral Majority** (`television_broadcasting`, era 7) — Religious political organizing via broadcast media
2. **The Electronic Pulpit** (`pop_culture`, era 8) — Televangelism and megachurches
3. **The Preferential Option** (`civil_rights_movement`, era 7) — Liberation theology (fires under state atheism)
4. **One Nation Under God** (`globalization`, era 9) — Religious nationalism
5. **The Digital Pulpit** (`social_media`, era 9) — Online faith communities
6. **The Culture War** (`sexual_revolution`, era 8) — Religious conservative backlash
7. **The Faithful Hand** (`social_justice_movements`, era 9) — Faith-based welfare (fires under state atheism)

**Files:**
- Events: `events/religious_revival_events.txt`
- Modifiers: `common/static_modifiers/extra_modifiers.txt` (search for `rre_`)
- On_action: `common/on_actions/extra_on_actions.txt` (in `society_technology_events_on_action`)
- Decision: `common/decisions/extra_decisions.txt` (`secularization_campaign`)
- Loc: `localization/english/te_events_l_english.yml` (variant keys with `_islamic`, `_dharmic`, `_jewish`, `_atheism` suffixes)

---

## SoL Expectations System

**Purpose:** Adds adaptive standard of living expectations that create inertia around SoL changes. When SoL rises suddenly, people's expectations lag behind (contentment bonus). When SoL drops, expectations remain high (dissatisfaction penalty). Expectations converge toward a target (actual SoL + permanent offsets) with a configurable half-life.

**Mechanic:**
- Country variable `var:sol_expectations_shift` tracks the adaptive shift applied via a static modifier
- Monthly: `gap = (average_sol + target_add) - average_expected_sol`, then `shift += gap * rate + monthly_bias`
- Rate derived from half-life: `rate = ln(2) / (half_life_years × 12)` (default 5y → ~0.01155/month)
- At equilibrium: `average_expected_sol ≈ average_sol + target_add` (shift stabilizes at whatever bridges the gap)
- Applied via `sol_expectations_adaptive_shift` static modifier with `multiplier = shift`
- Shift threshold: only applied when |shift| > 0.05 (avoids modifier clutter in steady state)

**Target offset:** `country_sol_expectations_target_add` (script_only) — offsets the convergence target above/below actual SoL. Techs, laws, IG traits, and power bloc principles use this to represent permanent changes in societal expectations. Example: egalitarianism tech adds `country_sol_expectations_target_add = 1`, meaning a society with that tech permanently expects 1 point above their actual average SoL.

**Vanilla modifier conversion:** All vanilla `state_expected_sol_from_literacy`, `state_expected_sol_mult`, and per-strata `state_*_strata_expected_sol_add` modifiers from techs, laws, and IG traits have been replaced with `country_sol_expectations_target_add` using `INJECT:` directives that cancel the original values with inverse modifiers and add the new target offset. Injection files:
- `common/technology/technologies/sol_expectations_vanilla_injections.txt` — egalitarianism, labor_movement, socialism, political_agitation, mass_propaganda
- `common/laws/sol_expectations_vanilla_injections.txt` — law_industry_banned, law_women_in_the_fields
- `common/interest_group_traits/sol_expectations_vanilla_injections.txt` — ig_trait_biedermanner

**NOT converted** (intentionally): Engine-hardcoded code static modifiers (base_values, tax_modifier_*, unincorporated_state) and temporary DLC/event modifiers (expecting_riches_forever, etc.) — these are either unchangeable or correctly handled by the adaptive lag.

**Tuning:**
- `sol_expectations_half_life_years = 5` — script value controlling convergence speed. Change this single value to tune. 5y = ~50% adapted after 5y, ~75% after 10y, ~94% after 20y.

**Modifiers:**
- `country_sol_expectation_adaptation_rate_mult` (percent, script_only) — scales the adaptation rate. +50% = faster convergence (~3.3y half-life).
- `country_sol_expectations_shift_add` (decimals=2, script_only) — persistent monthly bias added to shift. Positive = expectations rise faster.
- `country_sol_expectations_target_add` (decimals=1, script_only) — permanent offset to the convergence target. Positive = people expect more than actual SoL.

**Utility scripted effects** (in `sol_expectations_effects.txt`):
- `sol_expectations_instant_adjust = { AMOUNT = X }` — instantly add X to the shift
- `sol_expectations_close_gap = { FRACTION = X }` — close X fraction of the remaining gap (0.5 = half, 1.0 = full)
- `sol_expectations_reset = yes` — fully reset expectations to match current target
- `sol_expectations_reapply_modifier = yes` — internal: remove and re-apply the static modifier

**Static modifier:** `sol_expectations_adaptive_shift` — applied at country level with `multiplier = shift_value`. Base modifier provides +1 to all three strata expected_sol_add, so multiplier directly controls the SoL shift.

**Script values** (in `extra_script_values.txt`):
- `sol_expectations_half_life_years` — half-life parameter in years (default 5)
- `sol_expectations_adaptation_rate_value` — derived monthly rate, scaled by modifier, clamped [0.001, 0.1]
- `sol_expectations_gap_value` — (average_sol + target_add) - average_expected_sol
- `sol_expectations_shift_value` — current shift variable, used as modifier multiplier
- `sol_expectations_shift_display` — rounded shift for UI display
- `sol_expectations_gap_display` — rounded cached gap for UI display

**Files:**
- Scripted Effect: `common/scripted_effects/sol_expectations_effects.txt` (`sol_expectations_monthly_update` + utilities)
- On_action: `common/on_actions/sol_expectations_on_actions.txt`
- Static Modifier: `common/static_modifiers/sol_expectations_modifiers.txt`
- Modifier Types: `common/modifier_type_definitions/extra_modifier_types.txt` (search `country_sol_expectation`)
- Script Values: `common/script_values/extra_script_values.txt` (search `sol_expectations`)
- Vanilla Injections: `sol_expectations_vanilla_injections.txt` in `technologies/`, `laws/`, `interest_group_traits/`
- Loc: `localization/english/te_modifiers_l_english.yml`

---

## Cultural Hegemony (Soft Power)

**Purpose:** Measures a nation's global cultural influence ("cache") — how much the rest of the world admires, envies, or mimics your culture and political model. The system drives ideology shift in foreign nations (via legitimacy pressure), raises SoL expectations globally, and provides migration bonuses. Prestige is an **input** to cultural pull, not an output.

**Activation:** Country rank ≥ Minor Power + has researched `romanticism`.

**Architecture:** Share-based. Every country computes a "raw" cultural pull score, then each country's final score is `(raw / global_sum_of_raw) × 100` — a percentage of global cultural influence. This scales naturally as populations grow 5× and GDP grows 1000×+ over a 200-year game.

**Raw Cultural Pull Components:**
1. **Art Production** (`cultural_pull_from_art`): Fine art goods production via `state_goods_production` on `sg:g_fine_art` (summed across country's states, avoiding shared-market overcounting). Uses **min(absolute production, share of global production × 100)** pattern — early game is limited by small absolute output; late game is limited by market share. Multiplied by `country_cultural_hegemony_art_mult` hook. Global total uses `every_market > mg:g_fine_art > market_goods_production`.
2. **Prestige** (`cultural_pull_from_prestige`): `prestige / 5`, capped at share of global prestige × 100 (same min pattern as art). Prestige is an input to cultural pull, not an output.
3. **Standard of Living** (`cultural_pull_from_sol`): Average SoL **minus population-weighted global average SoL** (delta). Capped at -5 to +20. Countries below global average contribute negative points.
4. **Tech Leadership** (`cultural_pull_from_tech_leadership`): Variable `ch_tech_firsts_recent` that accumulates when a GP/Major researches tech while being top-ranked; decays annually.
5. **Monuments** (`cultural_pull_from_monuments`): +3 per building in `bg_monuments` building group (all 25+ wonder buildings). Uses `every_scope_state > every_scope_building` with `building_group = bg_monuments`.
6. **Megaprojects** (`cultural_pull_from_megaprojects`): +3 per completed megaproject (space elevator, solar collector, orbital battlestation, mind upload nexus, antimatter facility, nanofabrication center, consciousness network). Capped at 1 per type (unique buildings not in `bg_monuments`).
7. **Modifier Hooks** (`cultural_pull_from_modifiers`): Via `country_cultural_pull_add`.
8. **Rank Multiplier**: GP ×1.5, Major ×1.0, Minor ×0.5, Insignificant ×0.25.
9. **General Multiplier**: `country_cultural_pull_mult` hook.

**Final Score:** `cultural_pull_total = (cultural_pull_raw / global_raw_cultural_pull) × 100` (0–100% share).

**Effects:**
- `cultural_hegemony_effect` (dynamic modifier): Migration attraction, tech spread — scaled by `cultural_hegemony_modifier_mult` (0–100×, equals cultural_pull_total share percentage). Note: does NOT add prestige (prestige is an input).
- `cultural_hegemony_foreign_benchmark` (dynamic modifier): SoL expectations pressure **and** legitimacy reduction (`country_legitimacy_base_add = -5`) on countries below the global hegemon — scaled by `cultural_hegemony_benchmark_mult` (0–3×). The legitimacy reduction represents ideology shift pressure — the hegemon's cultural dominance undermines rival governments' political legitimacy.
- Global tracking: `ch_top_cultural_pull` global variable updated yearly (now stores % share)

**JE Display:** Shows cultural share (%), raw score, component breakdown (art, prestige, SoL vs avg, tech, monuments, megaprojects, rank), and global hegemon comparison.

**JE Status Thresholds (share-based):**
- Dominant: ≥ 25%, Major: ≥ 15%, Significant: ≥ 10%, Moderate: ≥ 5%, Minor: ≥ 2%, Negligible: < 2%

**Events:**
- `information_warfare.2` — "The World is Watching" (one-time at share ≥ 10%)
- `information_warfare.3` — "The Cultural Hegemon" (one-time at share ≥ 25%)

**Files:**
- Journal Entry: `common/journal_entries/je_cultural_hegemony.txt`
- Journal Entry Group: `common/journal_entry_groups/timeline_extended_je_groups.txt` (`je_group_soft_power`)
- Script Values: `common/script_values/hegemony_cyber_script_values.txt`
- Static Modifiers: `common/static_modifiers/extra_modifiers.txt` (search `cultural_hegemony`)
- Modifier Types: `common/modifier_type_definitions/hegemony_cyber_modifier_types.txt`
- On-action: `common/on_actions/hegemony_cyber_on_actions.txt` (tech-first tracking)
- On-action wiring: `common/on_actions/extra_on_actions.txt` (added `cultural_hegemony_tech_first_on_action`)
- Events: `events/information_warfare_events.txt` (events 2, 3)
- Loc: `te_journal_entries_l_english.yml`, `te_modifiers_l_english.yml`, `te_events_l_english.yml`

**Hooks (for other systems to modify):**
- `country_cultural_pull_add` — flat pull bonus (techs, laws, buildings)
- `country_cultural_pull_mult` — percentage pull multiplier
- `country_cultural_hegemony_art_mult` — art production contribution multiplier
- `country_ideology_resistance_mult` — resist foreign ideology shift

---

## Information Warfare (Cyber Power)

**Purpose:** Enables digital subversion of rivals through covert cyber operations, balanced by a defensive Digital Sovereignty score. Operations have ongoing costs, risk of detection, and generate infamy on exposure. Operations are launched via **diplomatic actions** targeting specific countries.

**Activation:** Has researched `television` (era 6).

### Digital Sovereignty (Defense)

**Architecture:** Uses modifier hooks applied directly to techs, laws, and institutions via `country_digital_sovereignty_add` (like the nuclear attack/defense pattern), rather than hardcoded script value checks. This makes DS contributions visible in tech/law tooltips and extensible.

**Score Computation (script value: `digital_sovereignty_total`, 0–100):**
1. **Tech/Laws/Institutions** (`digital_sovereignty_from_modifiers`): Sum of `modifier:country_digital_sovereignty_add` from all sources:
   - Techs: Telecommunications +2, Radio +2, Television +3, Mainframe Computers +4, Personal Computers +4, Cloud Computing +3, Military-Grade Cybersecurity +5 (total: up to 23)
   - Laws: Secret Police +5, Censorship +3, Right of Assembly +1
   - Institutions: Intelligence Ministry +4 per investment level (up to 20 at max)
2. **Literacy** (`digital_sovereignty_from_literacy`): `literacy_rate × 100`, capped at 20.
3. **GDP Share** (`digital_sovereignty_from_gdp`): `(gdp / global_gdp) × 100`, capped at 15.
4. **Multiplier Hook**: `country_digital_sovereignty_mult`.

**Defensive Effect:** `digital_sovereignty_defense` dynamic modifier — separatism resistance and coup resistance, scaled by `digital_sovereignty_modifier_mult` (0–5×).

**JE Display:** Shows breakdown by tech/laws/institutions (combined), literacy, and GDP share.

### Cyber Operations (Offense)

**Operation Slots (script value: `cyber_operation_max_slots`):**
- Base 1, +2 for GP, +1 for Major, +1 for Mainframe Computers tech, +`country_cyber_operation_slot_add` hook. Max 6.

**Mission Types (launched via diplomatic actions):**
| Operation | Diplomatic Action | Type | Effect | Requires |
|---|---|---|---|---|
| Election Interference | `cyber_election_interference_action` | Peacetime | -5 Legitimacy, -25 Authority on rival | Rivalry + peace |
| Financial Subversion | `cyber_financial_subversion_action` | Peacetime | +2 bubble pressure on rival | Rivalry + peace |
| Infrastructure Sabotage | `cyber_infrastructure_sabotage_action` | Wartime | -15% infra, -10% throughput on enemy state | Active war |
| Comms Disruption | `cyber_comms_disruption_action` | Wartime | -10% offense/defense on enemy | Active war |

**Diplomatic Action Flow:**
1. Player selects target country via diplomatic action interface
2. `accept_effect` stores `iw_op_<type>` (active flag) and `iw_target_<type>` (target country reference)
3. JE monthly pulse reads stored target variables and applies effects to the specific target country
4. Cancel buttons on JE remove both the op flag and the target variable
5. AI evaluation uses `propose_score` system with rivalry/war checks

**Funding Levels:** 0 (Paused) to 3 (High). At level 0, operations remain in slots but have no effects, no cost, and no detection risk. Higher funding increases effectiveness but also detection risk and cost. Funding is managed via scripted buttons on the JE.

**Detection:** Monthly `random_list` check (only when funding ≥ 1); base 10% + funding bonus. Detection fires `information_warfare.1`, which cancels one operation, generates infamy, and provides deny/harden choice. The detector is scoped from stored target variables.

**Cost:** `cyber_operation_funding_cost` dynamic modifier scales minting by active ops × funding level × GDP fraction.

**Wartime ops auto-cancel on peace** (target variables cleaned up in monthly pulse).

**Events:**
- `information_warfare.1` — "Operation Compromised" (detection; cleans up target variables)
- `information_warfare.4` — "Foreign Interference Detected" (defender perspective)

**Files:**
- Journal Entry: `common/journal_entries/je_information_warfare.txt`
- Journal Entry Group: `common/journal_entry_groups/timeline_extended_je_groups.txt` (`je_group_cyber_power`)
- Diplomatic Actions: `common/diplomatic_actions/cyber_operations.txt` (4 actions for launching ops)
- Scripted Buttons: `common/scripted_buttons/hegemony_cyber_scripted_buttons.txt` (6 buttons: 4 cancel + 2 funding)
- Script Values: `common/script_values/hegemony_cyber_script_values.txt`
- Static Modifiers: `common/static_modifiers/extra_modifiers.txt` (search `cyber_`, `digital_sovereignty`)
- Modifier Types: `common/modifier_type_definitions/hegemony_cyber_modifier_types.txt`
- Messages: `common/messages/extra_messages.txt` (search `iw_`)
- Events: `events/information_warfare_events.txt` (events 1, 4)
- Loc: `te_journal_entries_l_english.yml`, `te_modifiers_l_english.yml`, `te_events_l_english.yml`, `te_notifications_l_english.yml`, `te_miscellaneous_l_english.yml`, `te_concepts_l_english.yml` (diplo action descs)

**Hooks (for other systems to modify):**
- `country_digital_sovereignty_add` — flat defense bonus (institutions, laws)
- `country_digital_sovereignty_mult` — percentage defense multiplier
- `country_cyber_attack_efficiency_mult` — offensive stealth/effectiveness
- `country_cyber_operation_slot_add` — extra operation slots

---

## Cultural Hegemony System

**Purpose:** Tracks each country's share of global cultural influence from prestige, art, standard of living, recent tech-first leadership, monuments, megaprojects, modifiers, and instability. The JE surfaces a yearly leaderboard and exposes player-facing cultural policy controls.

### Key Files
| File | Purpose |
|---|---|
| `common/script_values/cultural_hegemony_script_values.txt` | Core raw-score and display-value math for cultural pull |
| `common/scripted_effects/cultural_hegemony_effects.txt` | Monthly country cache updates, yearly leaderboard rebuild, hegemon ideology pressure helpers |
| `common/on_actions/cultural_hegemony_on_actions.txt` | Monthly and yearly update hooks, plus world-first tech tracking |
| `common/journal_entries/je_cultural_hegemony.txt` | Display JE, active policy readout, and JE-scoped modifier application |
| `common/scripted_buttons/cultural_hegemony_buttons.txt` | Funding controls, timed exposition action, and persistent policy toggles |
| `common/static_modifiers/extra_modifiers.txt` | Timed event modifiers plus the persistent JE policy modifiers |
| `events/cultural_hegemony_events.txt` | Annual soft-power events for both hegemon and target countries |

### Player Controls
- **Increase/Decrease Cultural Program Funding:** Adjusts a `ch_program_funding_level` variable that re-applies JE-scoped flat `country_cultural_pull_add` and a separate GDP-scaled expense modifier. The maximum level comes from `country_cultural_program_max_funding_add`.
- **Funding cap sources:** `institution_ministry_of_culture` grants funding tiers through ministry investment, while `mass_media` and `television` each raise the cap further.
- **Host World Exposition:** One-shot timed action that adds a decaying JE modifier for prestige, migration attraction, and cultural pull plus a separate GDP-scaled exposition cost.
- **Fund Cultural Institutes:** JE-scoped policy that trades bureaucracy for higher `country_cultural_pull_mult` and society tech progress.
- **Launch Global Media Campaign:** JE-scoped policy that requires `mass_media` and converts authority into prestige plus stronger cultural projection.
- **Enact Cultural Protectionism:** JE-scoped defensive policy that boosts pull and authority while reducing migration attraction and society tech openness.
- **Mutual exclusivity:** Global Media Campaign and Cultural Protectionism cannot be active at the same time.
- **Law cleanup:** If `law_ministry_of_culture` is removed, the JE monthly pulse zeroes funding and strips all three persistent cultural policy modifiers automatically.

### Notable Rules
- **Activation gate:** JE shows once the rule is enabled, any country has `mass_media`, and the player has `romanticism`.
- **Monument scoring:** `cultural_pull_from_monuments` now excludes `building_power_bloc_statue`, even though power bloc statues sit inside `bg_monuments`.
- **Scope pattern:** Persistent cultural-hegemony policy effects live on `je:je_cultural_hegemony`, not on the country, so the JE remains the single source of truth for both display and cleanup.

---

## Game Rules

Thirteen mod systems can be toggled on/off at game setup via `common/game_rules/extra_game_rules.txt`.

| Rule | Flag (enabled) | Default | Systems Gated |
|---|---|---|---|
| `custom_religions_allowed_rule` | `custom_religions_allowed` | **disabled** | Custom religion events, JE visibility |
| `banking_system_rule` | `banking_system_enabled` | enabled | Banking cycle, crash contagion |
| `global_warming_rule` | `global_warming_enabled` | enabled | CO₂ tracking, GW modifiers |
| `world_war_rule` | `world_war_enabled` | **disabled** | World war escalation, related JEs |
| `cultural_hegemony_rule` | `cultural_hegemony_enabled` | enabled | Cultural pull calculation, hegemony JE, hegemony on-action |
| `covert_warfare_rule` | `covert_warfare_enabled` | enabled | Cyber operations, digital sovereignty JE, all 4 cyber diplomatic actions |
| `heir_education_rule` | `heir_education_enabled` | enabled | Heir education JE and focus modifiers |
| `united_nations_rule` | `united_nations_enabled` | enabled | UN JE, vote events, international institutions |
| `nuclear_weapons_rule` | `nuclear_weapons_enabled` | enabled | Nuclear program JE, nuclear strike events, disarmament treaty |
| `decolonization_rule` | `decolonization_enabled` | enabled | Decolonization events and colonial collapse absorption |
| `space_race_rule` | `space_race_enabled` | enabled | Space race JE, satellite/moon/interplanetary events |
| `social_movements_rule` | `social_movements_enabled` | enabled | 8 social movement JEs and associated events |
| `universal_aptitude_traits_rule` | `universal_aptitude_traits_enabled` | **disabled** | Assigns admin/diplo/military aptitude traits to ALL adult characters instead of only rulers/politicians/agitators/generals/admirals |

**Gating pattern:** Each rule sets a flag checked via `has_game_rule = <flag>`:
- **Journal entries:** `is_shown_when_inactive = { has_game_rule = X_enabled }`
- **On-actions:** Early `return = yes` if `NOT = { has_game_rule = X_enabled }`
- **Diplomatic actions:** `potential = { has_game_rule = X_enabled ... }`
- **Trait assignment (aptitude):** `limit = { OR = { is_ruler = yes ... has_game_rule = universal_aptitude_traits_enabled } }`

**Localization:** Rule names, option labels, and descriptions in `te_game_rules_l_english.yml`. Each rule has 5 keys: `rule_X_rule`, `setting_X_enabled`, `setting_X_enabled_desc`, `setting_X_disabled`, `setting_X_disabled_desc`.

**Game Concepts:** Both cultural hegemony and information warfare have detailed concept tooltips (8 concepts total) in `te_concepts_l_english.yml` with cross-linked `[concept_X]` references. Concepts: `concept_cultural_hegemony_system`, `concept_cultural_pull`, `concept_cultural_pull_components`, `concept_foreign_cultural_benchmark`, `concept_information_warfare_system`, `concept_digital_sovereignty`, `concept_cyber_operations`, `concept_cyber_detection`.

---

## Covert Warfare System

**Purpose:** Adds an espionage/covert operations layer to the Cold War+ era. Countries can run covert operations against rivals (election interference, sabotage, espionage, etc.) using pact-based diplomatic actions. Operations consume operation slots, cost GDP-scaled expenses, and carry detection risk.

**Gate:** `has_game_rule = covert_warfare_enabled` + `has_technology_researched = television`.

### Key Files
| File | Purpose |
|---|---|
| `common/diplomatic_actions/covert_operations.txt` | 9 diplomatic actions (7 peacetime, 2 wartime) |
| `common/journal_entries/je_covert_warfare.txt` | Command center JE: IC display, slots, funding, detection, active ops |
| `common/script_values/covert_warfare_script_values.txt` | All script values: IC, slots, costs, detection, display |
| `common/static_modifiers/extra_modifiers.txt` | `covert_operation_funding_cost`, `intelligence_capacity_defense`, `iw_domestic_defense`, operation effect modifiers |
| `common/scripted_effects/covert_warfare_effects.txt` | Duration tracking, phase-based effects, election confidence |
| `common/scripted_buttons/covert_warfare_scripted_buttons.txt` | `iw_increase_funding_button`, `iw_decrease_funding_button` (player-only) |
| `common/on_actions/covert_warfare_on_actions.txt` | Election confidence on `on_election_campaign_end` |
| `events/covert_warfare_events.txt` | Detection event, diplomatic incidents |

### System Architecture
- **Operations as Pacts:** Each operation type is a togglable diplomatic action (like `increase_relations`). Effects applied monthly via JE `on_monthly_pulse`.
- **Intelligence Capacity (IC):** Base 5 (from `INJECT:base_values`) + rank bonus (GP +10, Major +5 from `INJECT:country_ranks`) + literacy component (`literacy_rate × 50`) + GDP component (`ln(gdp) × 3`, capped at 25) + modifiers (`country_intelligence_capacity_add`).
- **Operation Slots:** Single modifier-driven value: `modifier:country_covert_operation_slot_add`. Base 1 (`INJECT:base_values`) + rank bonus (GP +2, Major +1) + tech/law modifiers. Capped at 10.
- **Funding:** 4 levels (0=Dormant, 1=Operational, 2=Professional Tradecraft, 3=Black Budget). At level 0, operations remain in slots but have no effects, no cost, and no detection risk. Level 2: -3% detection, +5 counterintelligence IC. Level 3: -8% detection, +10 counterintelligence IC. Applies `iw_funding_defense` static modifier scaled by `covert_ops_funding_ci_mult`.
- **Cost:** `country_expenses_add` with GDP-scaled multiplier: `(active_ops + 1) × funding_level × banking_event_expense_small`. The `+1` ensures a base maintenance cost even with 0 active operations (you pay for defensive IC benefits like counterintelligence). Cost modifier applies whenever `iw_funding_level >= 1`, regardless of active op count.
- **Detection:** Base 10% + target counterintelligence penalty (target IC / attacker IC ratio, capped at +20%) × efficiency factor (from `country_covert_operation_efficiency_mult`) - funding stealth bonus (Level 2: -3%, Level 3: -8%). Final capped 1–50%.

### Election Interference & Electoral Confidence
- **Gate:** Election interference (`covert_election_interference_action`) requires the target to have an elected legislature (Landed/Wealth/Census/Universal Suffrage). If the target abolishes elections, the operation auto-cancels via `requirement_to_maintain`.
- **Electoral Confidence Effect:** On `on_election_campaign_end`, the system checks if any country has an active election interference operation against the country holding the election. Based on the **worst** (most advanced) operation among all attackers:
  - **Preparatory phase** (<6 months): No effect.
  - **Establishing phase** (6–11 months): `-0.05` electoral confidence.
  - **Fully Operational** (12+ months): `-0.1` electoral confidence.
- **Slot matching:** Uses `iw_target_election_interference_<slot>` (stores target's capital state) to find the correct slot, then checks `iw_duration_election_interference_<slot>` for phase determination.
- **On-action:** `covert_warfare_on_actions.txt` → `on_election_campaign_end` → `on_actions = { covert_warfare_election_end }` → calls `covert_op_election_confidence_effect` scripted effect.
- **Notification:** `iw_election_interference_confidence` message sent to the affected country.

### AI Behavior
- **Evaluation chance:** Low (0.02–0.05) to prevent spammy toggling. Aggressive rulers get +0.02–0.03, cautious rulers get ×0.25–0.5.
- **Will propose guards:** `in_default = no`, `country_rank >= rank_value:major_power` (peacetime ops), rivalry/antagonistic/domineering attitude required, IC advantage check for some ops.
- **Propose score:** Scales with rivalry (+10), great power rank (+5–7), aggressive ruler (+5–8).
- **AI Funding Management:** Monthly pulse auto-sets funding: 0 if in default/bankrupt, 2 for GPs with rivals, 1 for major powers, 0 otherwise. Player uses buttons.
- **Wartime ops:** Higher eval chance (0.05), no rank requirement, `in_default = no` guard only.

### Cancellation Conditions
- **All 7 peacetime ops** (election interference, financial subversion, industrial espionage, military espionage, influence campaign, ideological subversion, destabilization) have war and truce checks in both `possible` and `requirement_to_maintain`. Operations auto-cancel if war or truce with the target begins.
- **Wartime ops** (infrastructure sabotage, communications disruption) require active war with the target; they auto-cancel if peace is achieved.
- **Script value scope:** All covert warfare SVs use `owner = {}` wrapping to access country-scope data from JE scope (the `on_monthly_pulse` context). This is required because the JE monthly pulse runs in journal entry scope, not country scope.
