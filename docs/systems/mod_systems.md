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

> See also: `docs/systems/journal_entry_systems.md` for full JE system documentation.

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

## Construction as a Market Good (FMC architecture)

> Cross-reference: `docs/vanilla/vanilla_economy_reference.md` § 9 establishes the vanilla two-FCFS-queue model (government queue from treasury, private queue from IP, allocation set by `country_private_construction_allocation_mult`). This mod adds a market layer underneath without replacing the queues.

**Why:** Decoupling construction *capacity* (the vanilla `country_construction` country-resource that the FCFS queues spend) from construction *output* (what the construction sector actually produces) lets per-state economics influence national construction throughput. A goods-side stockout in one region propagates through the price loop instead of disappearing into a black-box country resource.

**Architecture (3 layers):**

1. **Construction-sector building, REPLACE'd.** `building_construction_sector` (vanilla) is REPLACE'd in `common/buildings/fmc_construction.txt` and its tier PMs are REPLACE'd in `common/production_methods/extra_pms.txt` (`pm_wooden_buildings`, `pm_iron_frame_buildings`, `pm_steel_frame_buildings`, `pm_arc_welded_buildings`, plus newer high-tier variants). Each tier now outputs `goods_output_construction_add = N` (1, 2, 3.5, 5, 6, 10, 16 across tiers) — i.e. the construction sector produces the **`construction`** market good rather than direct country construction points. State-level `state_construction_mult` is preserved so per-state efficiency still matters.
2. **The `construction` good itself.** Defined in `common/goods/timeline_extended_extra_goods.txt`. `cost = 1000`, `category = industrial`, `traded_quantity = 0.1`, `consumption_tax_cost = 400` (Authority cost if the player consumption-taxes it). High base cost makes it a load-bearing market input.
3. **Auto-placed consumer building: `fmc_building_construction_site`.** Defined in `common/buildings/fmc_construction.txt`. Flags: `buildable = no`, `expandable = no`, `downsizeable = no`, `min_raise_to_hire = -1.0`, `levels_per_mesh = -1`, `ownership_type = self`. Placed automatically by `fmc_sector_placement_effects.txt`. Its single PM (`pm_base` in `fmc_construction.txt`) consumes 1 `goods_input_construction` per workforce and produces 1 `country_construction_add` — i.e. it converts the construction good back into the vanilla queue currency. Employment is tiny (10 laborers per level, level_scaled).

**The chain end-to-end:**

```
Construction Sector (vanilla, REPLACE'd) → produces construction good
   ↓
Market: construction good supply meets construction good demand at a price
   ↓
fmc_building_construction_site (auto-placed) consumes construction good
   ↓ produces
country_construction_add (vanilla queue currency)
   ↓
Vanilla two-FCFS queues (government from treasury / private from IP) spend it
   ↓
New buildings get built / expanded
```

**Construction-cost-scaling layer.** The `construction_cost_scaling` static modifier (above) applies `goods_input_construction_mult = 1` (multiplied by a per-country GDPpc-driven multiplier). This scales how much *construction good* every building's maintenance PM consumes. So a richer country burns more construction good per same building → competes more for the same supply → stockouts and higher prices → fewer net `country_construction_add` produced → vanilla queues stall on availability rather than treasury.

**Buildings consume the construction good as maintenance.** Most production buildings have `goods_input_construction_add = 0.5 - 1` in their `workforce_scaled` block (see `extra_pms.txt`, lines around 1303, 2033, 2260, etc.). Construction is therefore not just an upfront build cost — it's an ongoing maintenance load tied to current economic activity.

**Implications for mod authors:**

- **The two FCFS queues still apply unchanged** — government queue from treasury, private queue from IP, with allocation set by `country_private_construction_allocation_mult`. The mod hasn't replaced the queue model; it's added an upstream market that determines whether the queue's currency is actually being produced.
- **A goods-side stockout stalls both queues** regardless of treasury/IP balance. This is the design intent: construction is gated by economic capacity, not just by money.
- **The `fmc_building_construction_site` building is auto-placed and the PM `pm_base` is `is_default = yes`** — there's no UI surface for the player to see this conversion. Tooltips on the construction-good price and the country `country_construction_add` total are the visible signals.
- **When mod-adding new buildings**, give them realistic `goods_input_construction_add` in their maintenance PMs. Skipping this makes the building free to maintain in capacity terms, undermining the system.

**FMC scripts (`common/scripted_effects/fmc_*.txt`):**

| File | Purpose |
|---|---|
| `fmc_setup_effects.txt` | Initial placement at game start. |
| `fmc_sector_placement_effects.txt` | Per-state placement of `fmc_building_construction_site`. |
| `fmc_build_effects.txt` | Adjusts auto-built fmc levels in response to construction-good demand. |
| `fmc_update_effects.txt` | Periodic update of fmc state. |
| `fmc_ai_effects.txt` | AI-side decisions around the system. |
| `fmc_custom_on_actions.txt` | Wires the above to on_actions. |

**FMC script values (`common/script_values/`):**

| File | Key values |
|---|---|
| `fmc_current_values.txt` | `fmc_construction_price` and derived ratios. |
| `fmc_target_values.txt` | Target levels and stabiliser thresholds. |
| `fmc_sector_placement_values.txt` | `fmc_construction_per_site` etc. |
| `fmc_ai_values.txt` | AI weights tied to queue depth and banking stress. |

## Bulk Transportation (Merchant Marine relocalization)

> Cross-reference: `docs/vanilla/vanilla_economy_reference.md` § 17.1.

**Why:** Vanilla 1.13's Merchant Marine is produced by Ports only and represents civilian shipping logistics. The mod treats it as a more general "bulk transportation capacity" — overseas shipping isn't conceptually separate from rail-haul logistics, so the same good models both. The engine ID stays `merchant_marine`; the localization changes; and producers are broadened.

**Localization override:** `localization/english/replace/timeline_extended_override_l_english.yml:23` — `merchant_marine:0 "Bulk Transportation"`. (And matching description / icon overrides if present.) The engine sees `merchant_marine`; the player sees "Bulk Transportation".

**Producers (43 PMs total: 21 in `extra_pms.txt`, 22 in `unique_pms.txt`).** The mod's design rule is: *transport infrastructure produces, everything else consumes*. Concretely:

| Producer category | PMs (representative) | Building family |
|---|---|---|
| **Railway** | `pm_early_trains`, `pm_steam_trains`, `pm_diesel_trains`, `pm_electric_trains`, `pm_autonomous_trains`, `pm_centralized_traffic_control`, `pm_automated_loading_and_unloading` | Railway (REPLACE'd) |
| **Motorways / highways** | `pm_civil_highway`, `pm_industrial_highway`, `pm_electric_civil_highway`, `pm_electric_industrial_highway`, `pm_autonomous_highway` | Motorways |
| **Ports** | `pm_container_ports`, `pm_containerized_cargo`, `pm_global_ports` | Port (vanilla preserved + mod tiers) |
| **Airports & spaceports** | `pm_airport`, `pm_spaceport` | Airport / Spaceport (mod additions) |
| **Trading houses & flagged company HQs** | `pm_eic_trading_house`, `pm_hbc_york_factory`, `pm_rac_sitka_trading_post`, `pm_mitsui_trading_house`, `pm_sassoon_bombay_docks`, `pm_ralli_odessa_grain_elevator`, `pm_sudamericana_valparaiso_pier`, `pm_b_grimm_bangkok_warehouse`, `pm_john_holt_lagos_trading_house`, `pm_ynchausti_manila_trading_house`, `pm_volkswagen_autostadt`, `pm_suez_company_ismailia_hq`, `pm_panama_company_culebra_cut` | Vanilla / mod company buildings |
| **Logistics & shipyards (modern)** | `pm_amazon_fulfillment_center`, `pm_alibaba_cainiao_park`, `pm_shopify_fulfillment_hub`, `pm_ap_moller_copenhagen_wharf`, `pm_mitsubishi_nagasaki_shipyard`, `pm_generic_dry_dock`, `pm_generic_logistics_hub`, `pm_generic_rail_nexus`, `pm_generic_shipping_terminal` | Vanilla / mod company buildings |

**Consumers (91 PMs in `extra_pms.txt`).** Demand spans most of the catalog — anywhere goods need to move between buildings or out of the country. By family:

| Consumer category | Representative PMs | Why |
|---|---|---|
| **High-tier construction sectors** | `pm_iron_frame_buildings`, `pm_steel_frame_buildings`, `pm_arc_welded_buildings` (REPLACE'd) | Construction needs bulk transport for raw materials. |
| **Extraction with rail/transport tier** | `pm_rail_transport_building_logging_camp`, `pm_log_carts`, `pm_rail_transport_mine`, `pm_rail_transport_building_oil_rig`, `pm_steam_rail_transport`, `pm_tanker_cars` | Rail/road tiers in extraction PMs need transport to ship the resource out. |
| **Food preservation & cold chain** | `pm_flash_freezing_building_fishing_wharf`, `pm_flash_freezing_building_whaling_station`, `pm_refrigerated_rail_cars_building_fishing_wharf`, `pm_refrigerated_rail_cars_building_livestock_ranch`, `pm_refrigerated_rail_cars_building_whaling_station` | Cold chain depends on transport. |
| **Mine extraction techniques** | `pm_dragline_excavators_*`, `pm_geophysical_survey_techniques_*`, `pm_deep_well` | Bulk material movement. |
| **Advanced industry & automation** | `pm_advanced_assembly_lines_*`, `pm_ai_managed_*`, `pm_3d_printed_buildings`, `pm_advanced_construction`, `pm_advanced_process_control`, `pm_continuous_processing`, `pm_distributed_control_systems`, `pm_customized_clothing`, `pm_drone_delivery_systems`, `pm_e-commerce`, `pm_department_stores`, `pm_cleanroom_fabs`, `pm_computer_aided_design`, `pm_automated_assembly_lines`, `pm_autonomous_loading_and_unloading` (where applicable) | Automation tiers assume just-in-time logistics. |
| **Vanilla consumer (preserved)** | Trade Centers (per `vanilla_economy_reference.md` § 14.1), overseas state market access | Vanilla baseline. |

**Topology summary.** Production is concentrated in a small number of *infrastructure* and *trade-flavored company* buildings. Consumption is distributed across most of the late-game economy. This keeps Bulk Transportation as a load-bearing mid-late-game good — early agrarian economies barely touch it, but as a country industrializes and adopts rail/road/automation tiers, bulk transport becomes one of the goods most likely to bottleneck and price-spike.

**Prestige good:** `prestige_good_generic_merchant_marine` is unchanged; companies that emit it (the shipping flavor) still work.

**Implications for mod authors:**

- When adding a new building / PM that *should* logically demand bulk transport (any high-throughput industry, any extraction with goods leaving the state), add `goods_input_merchant_marine_add` at a small fractional value (~0.5–1.0) to the maintenance PM. Otherwise the building bypasses the bulk-transport demand the system depends on.
- When adding a transport-flavored building (rail variants, river/canal expansions), give it `goods_output_merchant_marine_add` so it slots into the producer side. Keep the values consistent with existing rail-transport PMs.
- **Don't grep for "Industrial Transport"** — earlier drafts of this doc and the user's notes used that name, but the actual loc is "Bulk Transportation". The engine name is still `merchant_marine`.

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

> See also: `docs/systems/journal_entry_systems.md` for full JE system documentation.

- Journal entry with progress bar for nuclear weapon development.
- Requires Great Power or Major Power + ICBMs tech.
- 2 funding buttons (increase/decrease).
- Diplomatic actions: `nuke_diplo_action`, `tactical_nuke_diplo_action`.
- Treaty articles: `nuclear_disarmament`, `nuclear_program_aid`.
- Events: `nuclear_weapon_events.txt` — nuclear strike response events.

## Banking Cycle (`je_banking_cycle`)

> See also: `docs/systems/journal_entry_systems.md` for full JE system documentation.

- Uses 3 `scripted_progress_bar` instances and 28+ scripted buttons (`cb_*`, `ce_*`, `cw_*`).
- Requires `stock_exchange` tech.
- All banking buttons already have detailed AI weights.
- Events: `banking_cycle_events.txt` — 77 events covering crises from railway bubbles to derivatives, with command-economy and cooperative-ownership variants.
- Player-facing UI is the **policy dashboard** widget (below); the scripted buttons stay on the JE as the AI's path and as a fallback.

### Policy Dashboard
`gui/journal_entry_widgets/banking_dashboard_widget.gui` renders two custom widgets into the vanilla journal-entry panel (`custom_widget_container_1` and `_2`): a **Current Conditions** readout and an **Active Policies / Available Interventions** list.

**Single source of truth.** Every button's `possible` and `effect` body lives in a named helper — `banking_possible_<button>` in `common/scripted_triggers/banking_policy_triggers.txt`, `banking_effect_<button>` in `common/scripted_effects/banking_policy_effects.txt` — and both the `scripted_button` and the dashboard's scripted GUI call it. `visible`/`possible` on both halves of every enable/disable pair read the `banking_tool_*_active` family in `market_triggers.txt`. **If you add or retune a policy, edit the helper, never the button or the scripted GUI body.**

**Do not move AI logic out of the buttons.** The AI chooses banking policy solely through the `ai_chance` blocks on the JE's `scripted_button` entries (see `common/scripted_buttons/scripted_buttons.md` in vanilla — `ai_chance` is evaluated in country scope). Deleting a `scripted_button = …` line from `je_banking.txt`, or hiding it behind `is_ai`, silently removes that policy from the AI's repertoire. Every dashboard scripted GUI therefore carries `ai_is_valid = { always = no }`.

**Asking script a yes/no question from `.gui`.** `common/scripted_guis/banking_dashboard_scripted_gui.txt` holds read-only handlers (`banking_dash_system_*`, `banking_dash_phase_*`, `banking_dash_momentum_*`, `banking_dash_bubble_risk_high`, `banking_dash_any_policy_active`) whose only job is to expose an existing scripted trigger to the widget as `[GetScriptedGui('x').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]`. This keeps thresholds (phase bands, economic-system gates) in script instead of duplicating them as numeric comparisons in `.gui`.

**No hand-typed numbers.** Row tooltips quote the button's own `name`/`desc` loc plus `[GetStaticModifier('<mod>').GetDesc]`; the action button's tooltip is `Concatenate( ScriptedGui.IsValidTooltip(…), ScriptedGui.ExecuteTooltip(…) )`, so cost and effect text is generated by the engine from the actual script. Conditions tooltips read the `banking_display_*` script values in `extra_script_values.txt`, which are thin wrappers over the same `modifier:country_*_monthly_add` reads `banking_cycle_advance_variables` uses.

**Layout.** One `banking_dash_policy_row` type, instantiated per policy with blockoverrides (label / cost / enable action / disable action). Category sections collapse through `GetVariableSystem.Toggle('banking_dash_collapsed_<cat>')` — GUI-only state, never written to the save. Rows are fixed-width columns inside `widget` wrappers with eliding text, no absolute positioning.

### History Charts
`gui/journal_entry_widgets/banking_history_widget.gui` adds a third custom widget (`custom_widget_container_3`): a collapsed-by-default **History** section with one column chart each for cycle value, momentum and bubble pressure, plus 1 / 5 / 10-year ranges and dated policy and crash markers. The store, the chart type and the marker tooltips are shared infrastructure — see **History Store and Charts** below before touching any of it.

### Monthly Pulse Architecture
The `on_monthly_pulse` calls these scripted effects in order (all in `common/scripted_effects/banking_cycle_effects.txt`):
1. **`banking_cycle_update_fiscal_policy`** — re-applies fiscal policy modifier based on deficit/surplus relative to GDP.
2. **`banking_cycle_advance_variables`** — momentum decay, modifier-driven changes, investment pool, random mean-reversion nudge (scaled by `banking_random_nudge_down/up_value`), apply momentum to value, clamp all variables.
3. **`banking_cycle_check_and_execute_crash`** — asymmetric crash probability check based on bubble pressure × phase, scaled by `banking_crash_chance_multiplier_value`. If crash triggers, fires origin event (.6) and spreads contagion via `banking_cycle_spread_contagion`.
3b. **`te_history_record_banking_samples`** (`common/scripted_effects/te_history_banking_effects.txt`) — writes the month's cycle value, momentum and bubble pressure into the history store (**History Store and Charts**, below). Deliberately placed after the crash check so a crash month's bar shows the post-crash readings beside its crash marker.
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

| Law | Volatility | Crash Likelihood | Capitalist Inv Pool |
|---|---|---|---|
| Unregulated Banking | +50% | +25% | — |
| Free & Mutual Banking | — | -10% | — |
| Universal Light Prudence | +10% | — | — |
| Prudential Narrow Banking | -60% | -50% | -10% |
| Directed Credit Dev Banks | -25% | -20% | — |
| Central Bank Independence | -10% | -30% | — |

(`state_capitalists_investment_pool_efficiency_mult` is a vanilla per-pop modifier; Prudential is the only banking law that uses it. CBI gets the opposite signal at scale through `institution_national_bank` (+5%/level for capitalists in National Bank states).)

**Script values** (in `extra_script_values.txt`):
- `banking_random_nudge_down_value` — base -1, scaled by `(1 + country_banking_random_momentum_mult)`. Used in the random nudge step.
- `banking_random_nudge_up_value` — base +1, scaled the same way.
- `banking_crash_chance_multiplier_value` — base 1.0, adds `country_banking_crash_chance_mult`, clamped to min 0. Multiplied into crash weight.

**To add banking volatility/crash modifiers from other sources** (technologies, PMs, etc.), simply add `country_banking_random_momentum_mult = 0.1` or `country_banking_crash_chance_mult = -0.15` to the modifier block.

**Per-tool law gating.** Most `cb_*` buttons are tier-unlocked by `country_banking_intervention_max_add` (a threshold per button — see the `possible` blocks in `timeline_extended_scripted_buttons.txt`). On top of the tier gate, every banking law publishes its tool restrictions via `country_banking_lock_<tool>_bool` modifiers (defined in `banking_cycle_modifier_types.txt`). The lock entries appear as red "Locks: …" lines in the law's modifier-block tooltip, and each `cb_*` button gates on a `custom_tooltip { modifier:country_banking_lock_<tool>_bool = no }` check that surfaces the reason as "Tool not available under your current banking law" when the button is greyed. To add a new law-based restriction: add `country_banking_lock_<tool>_bool = yes` to the law's modifier block — no edits to scripted_buttons needed. Crisis-only tools (`cb_emergency_liquidity_program`) remain available regardless of law as Bagehot-style lender-of-last-resort. `cb_capital_controls_outflow` has a war override (`is_at_war = yes` bypasses the lock).

**Toggle costs.** Each `cb_*` button has friction on toggle to discourage rapid cycling, calibrated to its real-world parallel: monetary tools (OMO, asset relief, directed credit, e-liquidity, fx support, export credit) cost treasury via `banking_*_activation_cost` script values scaled to GDP; political tools (countercyclical buffer, raise margin requirements, policy rate hike, deposit guarantee) generate radicals/loyalists via `banking_small_radicals_value` and `banking_medium_radicals_value` (banking-specific equivalents of vanilla `small_radicals`/`medium_radicals`, defined in `extra_script_values.txt` to allow tuning banking-button friction independently of global event balance); FX manipulation (devaluation, capital controls) costs infamy and -2/-3 relations with great-power trade partners. Moral suasion is the lone exception — speeches have no real-world toggle cost.

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

## History Store and Charts

A bounded, save-persistent store of monthly samples, plus a reusable column chart that renders them inside a journal entry. The banking system is its first consumer; the reserve and UN series are meant to be added with a sampling call and a chart instance and nothing else.

### Files

| File | Role |
|---|---|
| `common/script_values/te_history_values.txt` | the clock (`te_history_month_index`), the cap, eviction order, the "available since" readers |
| `common/scripted_triggers/te_history_triggers.txt` | `te_history_country_is_tracked` — the one eligibility rule |
| `common/scripted_effects/te_history_effects.txt` | generic country and global recording/pruning helpers |
| `common/scripted_effects/te_history_banking_effects.txt` | the banking series' sampling + marker wrappers |
| `common/scripted_guis/te_history_scripted_gui.txt` | `te_history_marker_tooltip` — display-only, emits `custom_tooltip` lines |
| `gui/journal_entry_widgets/te_history_chart.gui` | the reusable `te_history_chart` / `te_history_bar_*` / `te_history_range_button` types |
| `gui/journal_entry_widgets/banking_history_widget.gui` | the three banking charts, wired to `custom_widget_container_3` of `je_banking_cycle` |

### Data model

**One script container per (country, month), not per metric.** Each container carries:

| Variable | Meaning |
|---|---|
| `te_hist_i` | monotonic month index (`te_history_month_index` = `year * 12 + month`, Jan = 0) |
| `te_hist_y` / `te_hist_mo` | calendar year and month 1–12, display only (the GUI has no integer division) |
| `te_hist_v_<METRIC>` | one per metric recorded that month |
| `te_hist_mk` | number of markers that month — its presence is what draws the marker pip |
| `te_hist_mk_<MARK>` | one per distinct marker recorded that month |

Tags are `te_hist te_hist_sample` (plus `te_hist_global` for the global series); the parent is the recording country, so the engine culls the history when the country stops existing. The country holds `te_hist` (the capped list), `te_hist_cur` / `te_hist_cur_i` (the current month's container and its index — the once-per-month guard), `te_hist_now_i`, and `te_hist_since_y` / `te_hist_since_mo`.

Sharing one container between all of a month's metrics is what makes the store affordable: 120 containers per tracked country covers *every* series rather than 120 per series, and a month's markers land on the same container as its readings, so the chart never has to search for them. A metric that was not recorded in a month simply has no `te_hist_v_<METRIC>` variable there — that is how the charts tell **missing data from a genuine zero**, and why a country that drops out of eligibility leaves a visible gap rather than a run of zeroes.

`te_history_month_index` is stateless: the same arithmetic on the current date, identical for every country and for the global series. Nothing has to be seeded on an existing save, two pulses in one month resolve to the same container, and there is no counter that can drift.

### Caps and eligibility

- **Cap:** `te_history_sample_cap = 120` — ten years of monthly samples, defined once. One sample is added per month and `te_history_prune_samples` evicts exactly one when the list goes over, using `ordered_in_list { position = 0 order_by = te_history_sample_order }` so the oldest goes regardless of how the engine orders the list. `te_history_sample_order` **negates** the month index, because Jomini's `ordered_*` iterators sort descending — ordering by the raw index would put the *newest* sample at position 0 and the pruner would destroy the container it had just created. (`un_resolution_age_order` negates for the same reason.) The evicted container is `destroy_container`ed after `remove_list_variable`, never before, so the list never holds a dead reference.
- **Eligibility:** `te_history_country_is_tracked` = `is_player = yes` OR `country_rank >= rank_value:major_power`. Identical for AI and human countries. `unrecognized_major_power` (rank_value 5) is deliberately out — those countries are numerous and rarely run the charted systems.
- **Dropping out:** a country that falls below the bar stops sampling and **keeps** its stored history; nothing prunes it early. It is bounded at 120 containers and dies with the country, so stale history costs at most one country's worth of samples. Re-entry resumes recording and the gap renders empty.
- **System gating:** a series also gates on its own system. `te_history_record_banking_samples` requires `has_game_rule = banking_system_enabled` and `has_journal_entry = je_banking_cycle`, so a country with banking switched off records no banking metrics at all.

### Markers

`te_history_record_marker = { MARK = <key> }` sets `te_hist_mk_<key>` on the month's container and bumps `te_hist_mk`. The banking markers are recorded at the single shared site each policy already has — the `banking_effect_<button>` helpers, which both the AI's journal-entry buttons and the dashboard call — plus `banking_cycle_check_and_execute_crash` (`crash`) and `banking_contagion_crash_check` (`crash_contagion`).

The tooltip is built in script, not in `.gui`: `te_history_marker_tooltip` is a `scope = country` scripted GUI with `saved_scopes = { te_hist_sample }` whose effect is nothing but `custom_tooltip` lines, rendered from loc with `[GetScriptedGui('te_history_marker_tooltip').ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'te_hist_sample', ScriptContainer.MakeScope ).End )]`. Its policy branches quote the dashboard's existing `banking_dash_tt_<button>` keys, so a marker shows the policy's real name, description and `[GetStaticModifier(…).GetDesc]` effect list — **no number is retyped**, and retuning a policy updates its marker text automatically. `is_valid`/`ai_is_valid` are `always = no`, so neither a player nor the AI can ever execute it.

### Opening the GUI never writes state

Every recording helper body is wrapped in `hidden_effect`. That matters because the `banking_effect_<button>` helpers are also rendered as button tooltips; during a tooltip render the engine resolves scope links but never creates containers, so an unwrapped call would both spray text into the policy tooltip and read a scope that was never set. The chart itself has no effect at all: the only click targets are the collapse header and the three range buttons, and both write GUI-variable-system values that never reach the save.

### The chart

`plotline` cannot be used. Its `plotpoints` property only accepts the output of `GetTrendPlotPoints` / `GetTrendPlotPointsNormalized` / `GetDynTrendPlotPoints`, all of which take an engine-side `DataTrend`; no global function in the 1.14 data-type docs returns a `DataTrend`, and no `DataTrend` exists for a mod variable. So the chart is one vertical `progressbar` per stored month, over `datamodel = "[JournalEntry.GetCountry.MakeScope.GetList('te_hist')]"`.

- **Width.** The plot is a fixed-width `hbox`; each item is `size = { 0 100% }` + `layoutpolicy_horizontal = expanding` + `maximumsize = { 40 -1 }`, so the *visible* bars divide the width between them (vanilla's `levels_progressbar` idiom). Switching to 1 year widens the bars instead of leaving 108 empty slots.
- **Ranges.** `GetVariableSystem` holds `te_hist_range` = `1`, `5` or `10`; unset means 10 years, which is the whole store, so the default view needs no per-bar test to pass. Each bar's `visible` compares `te_history_month_index` (now) minus its own `te_hist_i` against 12 / 60.
- **Signed series.** `te_history_bar_signed` stacks two half-height bars around a zero axis. The lower one uses vanilla's `double_direction_progressbar` "REVERSE HACK": swap `progresstexture` and `noprogresstexture` and give the bar a `min .. 0` range, so the coloured part is drawn from the far end and hangs down from the axis. Both halves clamp their value with `Max_CFixedPoint`/`Min_CFixedPoint`, so a positive month draws nothing below the axis and vice versa.
- **Empty state.** `IsDataModelEmpty` on the same list shows "nothing recorded yet" — what an existing save sees until its first monthly pulse. `te_hist_since` prints the oldest retained sample's date and says in words that earlier months were never recorded.
- **Collapsed by default.** The section header toggles a GUI flag named for the *open* state (the inverse of the dashboard's collapsed flags), so a player who never opens it never pays for the bars.

### How to add a series

1. **Sample it.** From the system's own monthly pulse, in country scope:
   `te_history_record_sample = { METRIC = res_stock VALUE = var:st_res_stock_grain }`
   Wrap it in the system's own gate (game rule + journal entry) the way `te_history_record_banking_samples` does. For a world-level series use `te_history_record_global_sample` instead; it writes to the global list and needs no eligibility trigger.
2. **Chart it.** Instantiate `te_history_chart` with blockoverrides for `chart_title`, `chart_legend`, `bar_tooltip` and `bar_body`. Use `te_history_bar_unsigned` for a one-sided metric (override `values` with `min`/`max`/`value` and `color`), `te_history_bar_signed` plus a `zero_axis` override for a signed one. The bar body's `visible` must be `[ScriptContainer.HasVariable( 'te_hist_v_<METRIC>' )]` so months without that metric stay empty.
3. **Localize it.** A title, a legend, a `…_row` line and a tooltip key modelled on `te_hist_tt_bank_value` — the tooltip key is where the date line and the marker block are composed.
4. **Mark it, if the series has turning points.** `te_history_record_marker = { MARK = <key> }` at the single site the event already has, plus one branch in `te_history_marker_tooltip`.

Nothing else. The store, pruning, ranges, marker pips, empty state and "available since" line are all shared. **Do not** add a second store, a per-metric container list, or a parallel chart implementation.

### Cost

Per tracked country: 120 containers, each with 3 bookkeeping variables plus one per recorded metric (3 for banking today), plus 6 country variables. Per month per tracked country: one container create, one destroy, ~6 `set_variable`, and two 120-element ordered scans. GUI cost is paid only while the section is open: 120 items per chart, each running one script-value evaluation for the range test.

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

> **Full design document:** `docs/vanilla/treaty_articles_reference.md` — read it when implementing a new treaty article.

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
- **Button lock integration:** Remove-button `possible`/`visible` checks in `common/scripted_buttons/global_warming_buttons.txt` now block rollback when `has_emissions_reduction_treaty` is present (for emissions-reduction policies only).

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
| **UN** | `un_space_partnership_modifier` boosts progress (+0.3/+0.4 safe/ambitious) and reduces failure risk (-2). ISS cooperation event (52) fires for UN members. UN resolution topic `un_topic_space` (event un_events.19). |
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

> **Full design document:** `docs/vanilla/wonder_buildings_reference.md`

Two-phase construction pattern: buildable construction site → completed building via scripted effect.

- **Space Elevator:** `building_space_elevator_construction_site` → `building_space_elevator`. Scripted effect: `space_elevator_construction` in `extra_effects.txt`. On-action: `space_elevator_on_action` (monthly state pulse). Max 20 levels.
- **Solar Collector:** Three-building system (construction site → orbital hub → ground receivers). Hub enables receiver slots via `country_solar_receiver_max_level_add`. Max 10 levels.
- **Construction progress:** Monthly based on `(occupancy / 12) * speed_multiplier`. Speed PMs: paused=0, slow=0.25, medium=0.5, fast=1.0.
- **Custom modifier types:** `building_weekly_*_progress` and `building_total_*_progress` (percent, script_only) in `megastructure_progress_modifier_types.txt`.

## Grand Monuments (Repeatable Construction Sink)

`building_grand_monument` exists so construction never becomes worthless: a rich country that
has finished building everything profitable can always raise another monument. Expensive to
build (`construction_cost_grand_monument = 10000`), nearly free to run (only `pmg_maintenance`),
infinitely repeatable (`expandable = yes`, no `has_max_level`), and deliberately a bad
investment — roughly a 65-year payback at base tourism price.

- **Files:** `common/buildings/grand_monuments.txt`, `common/production_methods/grand_monument_pms.txt`,
  `common/production_method_groups/grand_monument_pmgs.txt`, `events/monument_events.txt`,
  `common/on_actions/monument_events_on_actions.txt`, `bg_grand_monuments` in
  `common/building_groups/extra_building_groups.txt`.
- **Self-scaling by design.** Output is a flat `goods_output_tourism_add = 1`/level. Because
  `tourism` is a luxury good with steeply convex pop demand (`popneed_tourism` ramps 1 → 622
  across wealth tiers in `common/buy_packages/00_buy_packages.txt`), that flat output is nearly
  worthless in 1836 and meaningful late-game with no extra script.
- **NOT in `bg_monuments`, and that is load-bearing.** `tourism_throughput_from_monuments`
  (`common/script_values/tourism.txt`) and `cultural_pull_from_monuments`
  (`common/script_values/cultural_hegemony_script_values.txt`) both iterate `bg_monuments` and
  assume its members are unique one-off wonders. A repeatable member would grant a flat +25%
  tourism throughput and unlimited cultural pull. `bg_grand_monuments` is a **top-level group
  with no `parent_group`**, so `is_building_group = bg_monuments` does not match it. Grand
  Monument cultural pull is added back separately and hard-capped at +5
  (`cultural_pull_from_grand_monuments`).
- **The dedication ratchet.** Eight flavour PMs (civic / religious / war memorial / artistic /
  naturalist / scientific / industrial / athletic) plus `pm_monument_undedicated`, all in one
  `pmg_monument_dedication` group. The choice is **one-way** — see the header comment in
  `grand_monument_pms.txt` and the scripting-best-practices note on locking a PM choice.
- **Dedication ceremony.** `on_building_built` → `monument_events.1` (hidden `building_event`,
  saves the state, hops to `owner`) → `monument_events.2`, whose options call
  `activate_production_method` on the saved state scope. Recurring flavour events 3–10 are
  dispatched from `monument_events_on_action` on `on_monthly_pulse_country`.
- **Scaling split.** `state_*` and `building_*_throughput_add` are `level_scaled` (genuinely
  local); `interest_group_*` and `country_*` are `unscaled` (flat per monument) because the
  building is repeatable in every state and country-wide effects would otherwise stack without
  bound. **Every dedication carries a level_scaled state-local modifier**, so growing a monument
  always pays off whichever dedication it has — the unscaled national effects sit on top of
  that, never instead of it. Employment is `unscaled` too — a monument needs a caretaker staff, not a workforce that
  grows with its height.

## Temporary Amendments (Sunset Clauses)

Three amendments can be attached **temporarily** (`add_amendment = { … timeout = <months> }`) as enactment concessions. The engine removes them when the timeout (counted from law activation) elapses and fires `on_amendment_timeout`, which `common/on_actions/amendment_on_actions.txt` routes to a follow-up event offering to make the clause permanent (re-add without `timeout`; `te_legitimacy_drain` + radicals) or let it lapse (Industrialist disapproval + a few capitalist radicals). Engine semantics and authoring rules: `docs/guides/scripting_best_practices.md` § Temporary amendments.

| Amendment | Delivery (DEBATE checkpoint) | cooldown / timeout (months) | Expiry event |
|-----------|------------------------------|-----------------------------|--------------|
| `amendment_env_grandfather_clause` (new; +5% pollution, +5% emissions, +2 Industrialist approval on `law_ministry_of_the_environment`; cancels one institution level) | `ministry_law_events.58` option a | 48 / 120 | `ministry_law_events.59` |
| `amendment_national_champion_exemption` | `extra_law_events.29` option d (option a remains the permanent variant) | 48 / 120 | `extra_law_events.85` |
| `amendment_corporate_data_exemption` | `extra_law_events.31` option d (option a remains the permanent variant) | 12 / 36 | `extra_law_events.86` |

The `has_amendment` guards on events 29/31/58 make the permanent and temporary variants mutually exclusive within one enactment. The expiry events re-derive `sunset_law` from `active_law:<lawgroup>` and `industrialists_ig` in `immediate`, and are not in any checkpoint pool. Deferred from issue #278: a financial-regulation phase-in (the three laws' penalties are structurally different — numeric, none, boolean lock) and a wartime rules-of-war clause (no per-country war-start on-action; would need a timeout on an already-active law).

## On-Actions Reference

The mod uses 21 on-action files under `common/on_actions/`. These wire mod logic into engine hooks — either **pulse-based** (fires periodically for all relevant scopes) or **immediate** (fires the instant a specific game event occurs).

### File Index

| File | Purpose | Hook Type |
|------|---------|-----------|
| `extra_on_actions.txt` | Central hub: pulse wiring, dynamic modifiers, immediate triggers, company cleanup | Mixed |
| `fmc_on_actions.txt` | FMC map update triggers on diplomatic/territorial changes | Immediate |
| `headlines.txt` | "World first" tech notifications (`on_acquired_technology`) | Immediate |
| `law_events_on_actions.txt` | Law enactment checkpoint events (advance/debate/stall) | Immediate |
| `amendment_on_actions.txt` | Temporary-amendment expiry follow-up events (`on_amendment_timeout`) | Immediate |
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
- `tourism_on_action` — tourism output/throughput modifier refresh (sole owner; the multipliers read monthly-varying `city_size_rank` and live building levels)
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
- `international_relations_events_on_action` — diplo events
- `decolonization_events_on_action` — decolonization narrative
- `movement_events_te_on_action` — political movement events
- `society_technology_events_on_action` — society tech events
- `world_war_events_on_action` — world war events
- `overbuild_protection_on_action` — prevents wonder overbuilding
- `aptitude_traits_cleanup_on_action` — strips aptitude traits from characters the game rules don't allow them on

**`on_yearly_pulse_state`** (Root = State):
- `global_warming_update_on_action` — GHG emissions calculation
- `remove_or_create_homelands_on_action` — dynamic homeland changes
- `violent_hostility_on_action` — cultural violence
- `migration_crowding_on_action` — migration pull reduction
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
- `cultural_hegemony_tech_first_on_action` — world-first tech prestige (`cultural_hegemony_on_actions.txt`)
- `agricultural_diffusion_on_action` — broadcasts the first researcher of each diffusion-eligible tech

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

Building, institution and law scopes **do not support variables or modifiers**. The state modifier refresh effects in `extra_effects.txt` use `add_modifier = { multiplier = script_value }`, which evaluates the script value through the parent scope chain, so calling them from building-scope hooks like `on_building_built` / `on_production_method_changed`, from `on_law_activated`, or from `on_acquired_technology` causes cascading errors. Those hooks have all been removed — the **periodic state pulses are the only refresh sites**: `pollution_on_action` and `tourism_on_action` on `on_monthly_pulse_state`, `migration_crowding_on_action` and `free_port_tariff_update_on_action` on `on_yearly_pulse_state`. Pick the pulse whose cadence matches how fast the multiplier's inputs move, and give each modifier exactly one refresh site.

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
  1. `on_entry_into_force` saves scopes via `scope:article_options.source_country` / `.target_country` (critical scoping pattern — see `docs/guides/scripting_best_practices.md`).
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
- **Critical pattern:** Modifier values are NOT recalculated within a single effect block, so `modifier:X` reads after `remove_modifier` still include the old value. The `intel_shield_mult` persistent variable allows subtracting the prior contribution. See `docs/guides/scripting_best_practices.md` § "Modifier Values Are NOT Recalculated Within a Single Effect Block".

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
`assign_aptitude_traits_effect` (yearly) assigns traits to adult characters who lack them: 20% terrible, 30% poor, 35% average, 12% skilled, 3% exceptional. Generals/admirals (including a ruler or heir who also holds a command) get a better military distribution (5/15/30/35/15). It skips an heir whose country has `je_heir_education` active — that heir's traits come from education.

**Rule gating** (`te_aptitude_traits_enabled` in `misc_triggers.txt` = Heir Education **or** Universal Aptitude Traits):

| Heir Education | Universal | Who has aptitude traits | Monthly `aptitude_traits_cleanup_effect` |
|---|---|---|---|
| off | off | nobody | strips every character |
| on | off | rulers and heirs (roles overlap — a ruler who is also a general qualifies) | strips traits from anyone holding neither role but keeps their `ruler_*_tier` vars; `restore_aptitude_traits_effect` gives the same tiers back the month they return to power (the yearly pass also restores before rolling). Keeping traits for life was rejected: the traits also work outside the throne (`command_modifier`, `interest_group_modifier`), so a voted-out exceptional commander would become the only such general in a world of trait-less ones |
| off | on | every adult (traits can't be shaped by education) | no-op |
| on | on | every adult | no-op |

Only the both-off state also clears the `ruler_*_tier` vars; in the Heir-Education-only state they are the memory that restoration reads. The traits' `possible` blocks carry the same trigger but can't enforce it — `possible` only filters random trait generation and `add_trait` ignores it, which is how rule-off games leaked traits to every ruler after #183 un-wrapped the effect.

### Simulation
`sim_heir_education.py` — Monte Carlo simulation (20,000 runs per scenario) that validates the probability distributions. Key scenarios: newborn with 1-3 focuses, adult heirs, neglected education, intelligence impact analysis. Run this to tune parameters before changing thresholds.

### Design Lessons
- **Simulation-driven tuning:** Write a Python sim BEFORE implementing Paradox script changes. The sim reveals non-obvious distribution outcomes (e.g., that even terrible heirs have a small exceptional chance, creating memorable moments).
- **Intelligence as gain modifier, not chance modifier:** Modifying the gain AMOUNT instead of the pulse CHANCE keeps Paradox script clean (no need for cascading if/else with different random_list weights per intelligence tier). One `random_list = { 3 = { gain_effect } 97 = { } }` per focus regardless of intelligence.
- **Scripted effects for gain encapsulation:** Each focus has a dedicated `heir_ed_gain_X` effect that handles intelligence, variable updates, bar progress, and IG reactions. This keeps the JE monthly pulse compact.
- **`change_variable multiply = -1`** is valid Paradox script for negation (used in rebel child mechanic).

## Social Movement Journal Entries (history)

This section originally documented eight social-movement JEs that all shared a passive-timer-plus-random-events shape. Four have since been deleted (LGBTQ+ Rights, Second-Wave Feminism, Decline of Religion, Environmental Crisis), **along with their dedicated event files** — the surviving content was folded into general-purpose event files with their own dispatch (see *Where the ex-JE content lives now* below). There is no `social_movement_orphans_on_action`; that on_action never shipped. Civil Rights was redesigned around a progress bar + buttons + path-dependent outcomes; see the Civil Rights section in `docs/systems/journal_entry_systems.md`.

### Currently active JEs of this family
- `je_civil_rights` — progress bar, 6 button toggle pairs, path-dependent victory/failure (see `docs/systems/journal_entry_systems.md`)
- `je_human_augmentation` — passive timer (legacy shape; not yet redesigned)
- `je_digital_rights` — passive timer (legacy shape)
- `je_post_scarcity` — passive timer (legacy shape)
- `je_mental_health` — passive timer (legacy shape)

### Where the ex-JE content lives now

`events/lgbtq_events.txt`, `events/feminist_events.txt`, `events/secular_events.txt` and `events/environmental_events.txt` **no longer exist**. What survived moved into shared event files, each with a real dispatch site:

| Movement | Tech gate | Events today | Dispatched from |
|---|---|---|---|
| LGBTQ+ rights | `LGBTQ_rights_movement` | `society_technology_events.7`–`.8` (§ 5 of that file) | `society_technology_events_on_action` in `common/on_actions/extra_on_actions.txt` |
| Second-wave feminism | `second_wave_feminism` | `society_technology_events.1`–`.2` (§ 1) | same on_action |
| Decline of religion | `decline_of_organized_religion` (OR `sexual_revolution` / `social_media`) | `social_tensions_events.13` (§ Category 7 — Religious Revivals), plus the 7-event `events/religious_revival_events.txt` counterbalance | `common/on_actions/social_tensions_on_actions.txt` random list |
| Environmental crisis | `environmental_movement` / `pollution_control` | `environmentalism_events.*` — warming thresholds `.1`–`.4`, cooling recoveries `.17`+ | `gw_fire_warming_threshold_event` / `gw_fire_cooling_threshold_event` in `extra_on_actions.txt`, under `je_global_warming` |

The `.100` (failure) and `.200` (victory) capstone events for these four have been removed along with their JE-shape modifiers (`*_struggle_active`, `*_stagnation`, `*_triumph`, `*_crushed`, `*_paralysis`, `*_revivalism`, `feminism_emancipated_character_modifier`, `feminism_backlash_character_modifier`, `env_crisis_reform_window`).

### Summary Table (legacy-shape JEs still in the mod)

| JE | Trigger Tech | Law Group | Complete | Fail |
|---|---|---|---|---|
| Human Augmentation | `biohacking_and_human_augmentation` OR `brain_computer_interfaces` (via `has_augmentation_tech`) | `lawgroup_human_augmentation` | any of `law_regulated_augmentation_market` / `law_mandatory_augmentation` / `law_unrestricted_augmentation` | `law_human_purity` |
| Digital Rights | `automated_surveillance` / `cybersecurity` | `lawgroup_privacy_rights` | `law_strong_privacy_rights` | `law_intrusive_surveillance` + ministry of intel |
| Post-Scarcity | `universal_basic_income` | `lawgroup_welfare` | `law_post-scarcity` | `fail = { always = no }` — timeout only |
| Mental Health | `mental_health_awareness` | `lawgroup_criminal_justice` | `law_rehabilitation_focused_criminal_justice` + social_security ≥ 4 | `law_punishment_focused` + `decline_of_organized_religion` |

### Event Design Patterns

Each surviving JE has monthly pulse events plus a fail-state event (except Post-Scarcity, whose `fail` block is `always = no`). Events follow these design principles:

- **Three-option structure:** Option A (progressive/reformist), Option B (moderate/compromise), Option C (regressive/oppressive). Most options have meaningful tradeoffs — treasury costs for spending decisions, opposition radicals for partisan choices.
- **Fire-once events:** Policy-debate events that represent one-time historical moments use `has_global_variable` gates so they only fire once per game. Currently: `lgbtq_military_debate_happened`, `women_military_debate_happened`, `ai_predictive_policing_debate_happened`, `ai_bureaucracy_debate_happened`, `state_religion_debate_happened`.
- **Law-gated options:** Some regressive options require specific laws to be available (e.g., surveillance expansion requires `law_intrusive_surveillance`). AI chance modifiers weight options contextually based on current laws.
- **Law-gated AI weights:** AI preference for certain options increases when the country has relevant laws (e.g., `law_laissez_faire` boosts "protect industry" choice, `law_outlawed_dissent` boosts "label as terrorists" choice).
- **Cooldowns:** Routine debate events use `normal_modifier_time`; serious incidents and fire-once events use `long_modifier_time`.

### Files

| System | JE Definition | Events | Modifiers |
|---|---|---|---|
| LGBTQ+ Rights | (JE deleted) | `society_technology_events.7`–`.8` | `common/static_modifiers/extra_modifiers.txt` (event-flavor only) |
| Second-Wave Feminism | (JE deleted) | `society_technology_events.1`–`.2` | `common/static_modifiers/extra_modifiers.txt` (event-flavor only) |
| Human Augmentation | `common/journal_entries/je_human_augmentation.txt` | `events/augmentation_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Environmental Crisis | (JE deleted; folded into `je_global_warming`) | `events/environmentalism_events.txt` | `common/static_modifiers/extra_modifiers.txt` (event-flavor only) |
| Digital Rights | `common/journal_entries/je_digital_rights.txt` | `events/surveillance_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Post-Scarcity | `common/journal_entries/je_post_scarcity.txt` | `events/post_scarcity_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Mental Health | `common/journal_entries/je_mental_health.txt` | `events/mental_health_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Decline of Religion | (JE deleted) | `social_tensions_events.13`; `events/religious_revival_events.txt` | `common/static_modifiers/extra_modifiers.txt` (`rre_*`) |
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
- Modifier Types: `common/modifier_type_definitions/sol_expectations_modifier_types.txt`
- Script Values: `common/script_values/extra_script_values.txt` (search `sol_expectations`)
- Vanilla Injections: `sol_expectations_vanilla_injections.txt` in `technologies/`, `laws/`, `interest_group_traits/`
- Loc: `localization/english/te_modifiers_l_english.yml`

### Interaction with vanilla loyalist/radical generation

> Cross-reference: `docs/vanilla/vanilla_economy_reference.md` § 5.6.

Vanilla generates loyalists when a pop's SoL **rises** and radicals when it **falls** — the channel is the *delta*, not the *level*. The SoL Expectations System above hooks the *expected SoL* side of that channel (delaying when the delta registers) but does **not** replace the delta-driven loyalist/radical flow itself. That continues to run autonomously inside the engine for every pop in every state.

What this means for mod authors:

- When the banking cycle drops country-wide SoL through a panic phase, vanilla automatically converts that into radicals over the following months. Mod systems don't need to call `add_radicals` to model "the bust radicalized people" — the engine is already doing it.
- Conversely, when global-warming pollution pushes SoL down in a polluted state, vanilla autoaments the radical fraction without any explicit hook. Mod-side `add_radicals` calls in events should reflect *additional* sources beyond the SoL channel (e.g. movement supporters losing a key vote, a discriminated minority hit by a specific event).
- The autonomous channel is *generational-decay slow* — loyalists and radicals turn over with the country's death rate, not on a feedback timescale. Sharp short-term shocks register quickly; the country's long-run political alignment shifts slowly.
- High legitimacy (a separate mechanic) generates loyalists too. Mods that flip legitimacy via events get loyalist generation as a side effect.

The risk to be aware of: if a mod system *also* adds loyalists/radicals tied to economic state (e.g. on an event where SoL crashed), it can double-count vanilla's autonomous response. Prefer to model unique additional triggers (a riot, a discriminatory incident, a political win) and let vanilla handle the SoL-delta side.

---

## Cultural Hegemony System

**Purpose:** Measures a nation's global cultural influence ("cache") — how much the rest of the world admires, envies, or mimics your culture and political model. The system drives ideology shift in foreign nations (via legitimacy pressure and **political-model movement pressure**, below), raises SoL expectations globally, and provides migration bonuses. Prestige is an **input** to cultural pull, not an output. The JE surfaces a yearly leaderboard and exposes player-facing cultural policy controls.

**Activation:** `cultural_hegemony_enabled` game rule; the JE activates once any country has researched `mass_media` and the country itself has `romanticism`. Scores are computed from game start by the on-actions, so they are already stable when the JE first appears.

**Architecture:** Share-based. Every country computes a "raw" cultural pull score, then each country's final score is `(raw / global_sum_of_raw) × 100` — a percentage of global cultural influence. This scales naturally as populations grow 5× and GDP grows 1000×+ over a 200-year game.

**Raw Cultural Pull Components:**
1. **Art Production** (`cultural_pull_from_art`): Fine art goods production via `state_goods_production` on `sg:g_fine_art` (summed across country's states, avoiding shared-market overcounting). Uses **min(absolute production, share of global production × 100)** pattern — early game is limited by small absolute output; late game is limited by market share. Multiplied by `country_cultural_hegemony_art_mult` hook. Global total uses `every_market > mg:g_fine_art > market_goods_production`.
2. **Prestige** (`cultural_pull_from_prestige`): `prestige / 5`, capped at share of global prestige × 100 (same min pattern as art). Prestige is an input to cultural pull, not an output.
3. **Standard of Living** (`cultural_pull_from_sol`): Average SoL **minus population-weighted global average SoL** (delta). Capped at -5 to +20. Countries below global average contribute negative points.
4. **Tech Leadership** (`cultural_pull_from_tech_leadership`): Variable `ch_tech_firsts_recent` that accumulates when a GP/Major researches tech while being top-ranked; decays annually.
5. **Monuments** (`cultural_pull_from_monuments`): +3 per building in `bg_monuments` building group (all 25+ wonder buildings). Uses `every_scope_state > every_scope_building` with `building_group = bg_monuments`.
6. **Megaprojects** (`cultural_pull_from_megaprojects`): +3 per completed megaproject (space elevator, solar collector, orbital battlestation, mind upload nexus, antimatter facility, nanofabrication center, consciousness network). Capped at 1 per type (unique buildings not in `bg_monuments`).
7. **Modifier Hooks** (`cultural_pull_from_modifiers`): Via `country_cultural_pull_add`.
8. **Infamy and Instability** (`cultural_pull_from_infamy`, `cultural_pull_from_stability`): negative-only terms — infamy × -0.1, turmoil × -10, and a flat -20 for an active civil war.
9. **General Multiplier**: `country_cultural_pull_mult` hook.

**Country rank does *not* multiply the raw score.** Rank scaling applies to the standard-of-living term alone (`cultural_pull_from_sol`: great power and above full, major ×0.5, minor ×0.25, lesser ×0), which is where a country's weight-class belongs — a small country with a world-leading art industry is not penalised for being small. (An earlier version of this section listed a whole-score rank multiplier; no such multiplier has ever existed in `cultural_hegemony_script_values.txt`.)

**Final Score:** `cultural_pull_total = (cultural_pull_raw / global_raw_cultural_pull) × 100` (0–100% share).

**Effects:**
- `cultural_hegemony_effect` (dynamic modifier): Migration attraction, tech spread — scaled by `cultural_hegemony_modifier_mult` (0–100×, equals cultural_pull_total share percentage). Note: does NOT add prestige (prestige is an input).
- `cultural_hegemony_foreign_benchmark` (dynamic modifier): SoL expectations pressure **and** legitimacy reduction (`country_legitimacy_base_add = -5`) on countries below the global hegemon — scaled by `cultural_hegemony_benchmark_mult` (0–3×). The legitimacy reduction represents ideology shift pressure — the hegemon's cultural dominance undermines rival governments' political legitimacy.
- Global tracking: `ch_top_cultural_pull` global variable updated yearly (now stores % share)

**Political models and movement pressure:**
- **One classification.** `ch_set_political_model` (`cultural_hegemony_effects.txt`) writes `var:ch_model`, 1–15, from one ordered `if/else_if` chain of `has_law_or_variant` tests. The header of that effect has the code table. The order is part of the classification: first match wins. Codes 1–12 are the original families. 13 Technocratic (Technocracy or Algorithmic Governance), 14 Republican (a republic or Direct Democracy that fails the Liberal test) and 15 Developmentalist Junta were added later. A junta counts as developmentalist when it has Interventionism or Command Economy and fails `ch_has_regressive_laws`, which is vanilla's critical-modernization list minus the two taxation laws, plus hereditary bureaucrats, Feudal Contracts and the slavery laws. Neocameralism is deliberately unmapped. Everything else reads `var:ch_model`; nothing re-derives it.
- **World shares.** Each rebuild classifies every country and sums its `cultural_pull_raw` into `ch_ideology_<model>_raw`, then divides by the `ch_cached_global_raw` refreshed in the same rebuild into `ch_ideology_<model>_share` (percent). The shares are weighted by pull, not by head count, and add up to 100. `ch_rank_1_ideology` (the code), `ch_rank_1_ideology_aligned_count` and `ch_rank_1_ideology_share` describe the leader's model. Don't sum `var:ch_total` for this, because its denominator is the previous rebuild's.
- **What each model pushes.** `ch_apply_hegemon_movement_pressure` branches on `scope:cultural_hegemon`'s model (re-classified at call time). Each model has a primary movement plus two fallbacks, and a fallback gets the weaker modifier only when the primary movement is absent. Independent social-law blocks also run: feminist, civil/minority rights, environmental, anti-war, anti-slavery, labor and land reform. The new models map as follows:
  - Technocratic → positivist → modernizer → transhumanist
  - Republican → radical → liberal → modernizer
  - Developmentalist Junta → modernizer → land reform → labor
- **Baseline (constant).** Every rebuild (about every 6 months: 180-day lock, the yearly pulse and war-end rebuilds), `ch_refresh_baseline_model_pressure` runs on every JE holder:
  - It strips `ch_hegemon_model_pressure` and `_weak` from all movements.
  - It then re-applies them non-decaying for 13 months where the country carries `cultural_hegemony_foreign_benchmark`, with `multiplier = ch_model_pressure_mult`.
  - The multiplier is 0 below `ch_model_pressure_min_share` (15%), otherwise `share / 50` clamped to 0.3–1.5. Its source is the **model's** share of world culture, not the hegemon's own.
- **Event spikes.** Events 7 and 15 apply `ch_hegemon_ideological_pressure(_weak)` non-decaying for half the old decaying duration (7A: 30 months full; 7C: 15 months weak; 7D and 15A: 30 months weak), so each event's lifetime total is unchanged. They stack on the baseline because the modifier names differ. Event 7 still picks a weighted-random ≥15% power, not necessarily rank 1.
- **Covert Ideological Subversion** calls the same effect with the *attacker* saved as `cultural_hegemon`, `MULT = 1`.

**JE Display:** a custom widget in all three `custom_widget_container_*` slots — the influence tier and share with a bar, world rank, the hegemon's exported political model with its share of world culture, the cultural-programme controls, a collapsible component breakdown, the collapsible top-ten board, a collapsible "Political Models of the World" pie + legend, and a collapsible history chart of the country's share. The entry's own `status_desc` is three lines. Full data contract, op tables and editing rules: `docs/systems/journal_entry_systems.md` → **Cultural Hegemony Widget**.

**JE Status Thresholds (share-based):** Dominant ≥ 25%, Major ≥ 15%, Significant ≥ 10%, Moderate ≥ 5%, Minor ≥ 2%, Negligible < 2%. These five numbers live in exactly one place — `ch_set_display_state` in `cultural_hegemony_effects.txt`, which writes the `ch_tier` variable everything else reads. Do not re-type them in localization, `.gui` or a journal-entry trigger.

**Events:** `events/cultural_hegemony_events.txt` (`cultural_hegemony.1`–`.16`) — recurring soft-power events for both the hegemon and the countries under its pull (e.g. `.2` fires for a country below 5% share carrying `cultural_hegemony_foreign_benchmark`; `.3` for a country at ≥ 20% share).

**Hooks (for other systems to modify):**
- `country_cultural_pull_add` — flat pull bonus (techs, laws, buildings)
- `country_cultural_pull_mult` — percentage pull multiplier
- `country_cultural_hegemony_art_mult` — art production contribution multiplier
- `country_ideology_resistance_mult` — resist foreign ideology shift

### Key Files
| File | Purpose |
|---|---|
| `common/script_values/cultural_hegemony_script_values.txt` | Core raw-score and display-value math for cultural pull |
| `common/scripted_effects/cultural_hegemony_effects.txt` | Monthly country cache updates, the leaderboard rebuild, `ch_set_political_model` (the one political-model classification), per-model world totals, hegemon movement-pressure helpers and the baseline refresh |
| `common/on_actions/cultural_hegemony_on_actions.txt` | Monthly and yearly update hooks, plus world-first tech tracking |
| `common/journal_entries/je_cultural_hegemony.txt` | Three-line summary, the three widget mounts, and JE-scoped modifier application |
| `common/scripted_buttons/cultural_hegemony_buttons.txt` | The AI's ten policy buttons (`is_ai = yes`); each delegates to a shared helper |
| `common/scripted_triggers/cultural_hegemony_triggers.txt` | `ch_possible_<button>` eligibility, `ch_shown_<programme>` swap triggers, and `ch_has_regressive_laws` (the developmentalist-junta gate) |
| `common/scripted_guis/cultural_hegemony_sguis.txt` | `ch_policy_sgui` (the widget's controls) plus four display-only handlers |
| `gui/journal_entry_widgets/cultural_hegemony_widget.gui` | The player-facing panels: summary, programmes, breakdown, board, history |
| `common/customizable_localization/cultural_hegemony_custom_loc.txt` | Influence tier and exported-model text, branching on `ch_tier` / `ch_rank_1_ideology` (codes 1–15) |
| `scripts/image_pipeline/gen_ch_model_pie_textures.py` | Generates the 15 per-model pie/swatch textures under `gfx/interface/journal_entry_widgets/ch_model_pie/`; its `MODELS` tuple is the pie's slice order |
| `common/scripted_effects/te_history_cultural_hegemony_effects.txt` | The `ch_share` history series and its programme markers |
| `common/static_modifiers/extra_modifiers.txt` | Timed event modifiers plus the persistent JE policy modifiers |
| `events/cultural_hegemony_events.txt` | Annual soft-power events for both hegemon and target countries |
| `events/te_debug_ch_events.txt` | Console test harness (`event te_debug_ch.1`) for the widget's awkward states |

### Player Controls
- **Increase/Decrease Cultural Program Funding:** Adjusts a `ch_program_funding_level` variable that re-applies JE-scoped flat `country_cultural_pull_add` and a separate GDP-scaled expense modifier. The maximum level comes from `country_cultural_program_max_funding_add`.
- **Funding cap sources:** `institution_ministry_of_culture` grants funding tiers through ministry investment, while `mass_media` and `television` each raise the cap further.
- **Begin International Cultural Outreach** (internally `ch_world_exposition`): a **persistent toggle**, not a one-shot and not timed — the JE-scoped modifier has no duration and runs, with its GDP-scaled cost, until the player ends it or the Ministry goes away. (An earlier version of this section described it as a one-shot decaying action; it never was one.)
- **Fund Cultural Institutes:** JE-scoped policy that trades bureaucracy for higher `country_cultural_pull_mult` and society tech progress.
- **Launch Global Media Campaign:** JE-scoped policy that requires `mass_media` and converts authority into prestige plus stronger cultural projection.
- **Enact Cultural Protectionism:** JE-scoped defensive policy that boosts pull and authority while reducing migration attraction and society tech openness.
- **Mutual exclusivity:** Global Media Campaign and Cultural Protectionism cannot be active at the same time.
- **Law cleanup:** If `law_ministry_of_culture` is removed, the JE monthly pulse zeroes funding and strips **all four** persistent cultural policy modifiers automatically, International Cultural Outreach and its cost included. Outreach was missing from that list until this was fixed, so an outreach programme begun under the Ministry kept paying out — and charging — for the rest of the game after a repeal.
- **Player surface:** the ten buttons are AI-only (`is_ai = yes`); a human acts through the widget, whose controls call the same `ch_possible_*` / `ch_effect_*` helpers. See `docs/systems/journal_entry_systems.md` → **Cultural Hegemony Widget** for the op tables and editing rules.

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
| `covert_warfare_rule` | `covert_warfare_enabled` | enabled | Covert operations command-centre JE (`je_covert_warfare`), all 9 covert diplomatic actions |
| `heir_education_rule` | `heir_education_enabled` | **disabled** | Heir education JE and focus modifiers; aptitude traits for rulers and heirs |
| `united_nations_rule` | `united_nations_enabled` | enabled | UN JE, vote events, international institutions |
| `nuclear_weapons_rule` | `nuclear_weapons_enabled` | enabled | Nuclear program JE, nuclear strike events, disarmament treaty |
| `decolonization_rule` | `decolonization_enabled` | enabled | Decolonization events and colonial collapse absorption |
| `space_race_rule` | `space_race_enabled` | enabled | Space race JE, satellite/moon/interplanetary events |
| `social_movements_rule` | `social_movements_enabled` | enabled | 8 social movement JEs and associated events |
| `universal_aptitude_traits_rule` | `universal_aptitude_traits_enabled` | **disabled** | Assigns admin/diplo/military aptitude traits to ALL adult characters instead of only rulers and heirs — works with Heir Education off too. With both rules off, no aptitude traits at all |

**Gating pattern:** Each rule sets a flag checked via `has_game_rule = <flag>`:
- **Journal entries:** `is_shown_when_inactive = { has_game_rule = X_enabled }`
- **On-actions:** Early `return = yes` if `NOT = { has_game_rule = X_enabled }`
- **Diplomatic actions:** `potential = { has_game_rule = X_enabled ... }`
- **Trait assignment (aptitude):** `limit = { te_aptitude_traits_enabled = yes  OR = { has_game_rule = universal_aptitude_traits_enabled  has_role_of_type = ruler  has_role_of_type = heir } }`

**Localization:** Rule names, option labels, and descriptions in `te_game_rules_l_english.yml`. Each rule has 5 keys: `rule_X_rule`, `setting_X_enabled`, `setting_X_enabled_desc`, `setting_X_disabled`, `setting_X_disabled_desc`.

**Game Concepts:** Both cultural hegemony and information warfare have detailed concept tooltips (8 concepts total) in `te_concepts_l_english.yml` with cross-linked `[concept_X]` references. Concepts: `concept_cultural_hegemony_system`, `concept_cultural_pull`, `concept_cultural_pull_components`, `concept_foreign_cultural_benchmark`, `concept_information_warfare_system`, `concept_digital_sovereignty`, `concept_cyber_operations`, `concept_cyber_detection`.

---

## Covert Warfare System

> Supersedes the earlier *Information Warfare (Cyber Power)* design (`je_information_warfare`, `cyber_*` diplomatic actions, Digital Sovereignty), which was removed from the mod in `45cd7d8`. Nothing from that design remains in script.

**Purpose:** Adds an espionage/covert operations layer to the Cold War+ era. Countries can run covert operations against rivals (election interference, sabotage, espionage, etc.) using pact-based diplomatic actions. Operations consume operation slots, cost GDP-scaled expenses, and carry detection risk.

**Gate:** `has_game_rule = covert_warfare_enabled` + `has_technology_researched = television`.

### Key Files
| File | Purpose |
|---|---|
| `common/diplomatic_actions/covert_operations.txt` | 9 diplomatic actions (7 peacetime, 2 wartime) |
| `common/journal_entries/je_covert_warfare.txt` | Command center JE: IC display, slots, funding, detection; wires the operations widget |
| `gui/journal_entry_widgets/covert_operations_widget.gui` | JE widget listing each running operation (type, target, phase, detection) from the `iw_ops` list |
| `common/script_values/covert_warfare_script_values.txt` | All script values: IC, slots, costs, detection, display |
| `common/static_modifiers/extra_modifiers.txt` | `covert_operation_funding_cost`, `intelligence_capacity_defense`, `iw_domestic_defense`, operation effect modifiers |
| `common/scripted_effects/covert_warfare_effects.txt` | Operation containers (create/destroy/monthly sync), duration aging, phase-based effects, election confidence |
| `common/scripted_triggers/covert_warfare_triggers.txt` | Pact-type check, target validity, per-type cap, phase triggers |
| `common/scripted_buttons/covert_warfare_scripted_buttons.txt` | `iw_increase_funding_button`, `iw_decrease_funding_button` (player-only) |
| `common/on_actions/covert_warfare_on_actions.txt` | Election confidence on `on_election_campaign_end` |
| `events/covert_warfare_events.txt` | Detection event, diplomatic incidents |

### System Architecture
- **Operations as Pacts:** Each operation type is a togglable diplomatic action (like `increase_relations`). Effects applied monthly via JE `on_monthly_pulse`.
- **Operation state as script containers (1.13.10+):** Each running operation is one container tagged `iw_op` + `iw_op_<TYPE>`, parented to the operator country, holding `iw_target` (country), `iw_duration` (months), and JE display values (`iw_target_capital`, `iw_detect`, `iw_tgt_ic`, `iw_tgt_td`). The operator lists them in its `iw_ops` variable list, and every loop walks that list instead of `every_container`. Pacts remain the source of truth: `accept_effect` calls `covert_op_start`, `manual_break_effect`/`auto_break_effect` call `covert_op_end`, the detection event's `covert_op_burn` removes the pact and container together, and `covert_ops_sync_all` runs at the top of the monthly pulse to create containers for pacts that lack one (month 0) and destroy containers whose pact is gone. Saves made before containers keep their pacts, which restart at month 0; their old `iw_*_<type>_<n>` slot variables are left inert (clearing them would log "used but never set" warnings on every load).
- **Per-type cap:** `covert_ops_type_below_cap` compares the live pact count against `covert_ops_max_per_type` (1, +1 `mainframe_computers`, +1 `cyber_warfare`). That script value is the only place the cap lives; storage has no per-type limit.
- **Phases:** `covert_op_is_established` (`iw_duration >= 6`) and `covert_op_is_fully_operational` (`>= 12`), evaluated on the container. Target-side effects use each operation's own phase; self-side effects use the best phase among that type's operations.
- **JE display:** `status_desc` keeps the capacity/funding/defense summary. Per-operation rows come from `widget_je_covert_operations` in `custom_widget_container_2`, whose datamodel is `JournalEntry.GetCountry.MakeScope.GetList('iw_ops')`.
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
- **Operation matching:** For each attacker with an election-interference pact against ROOT, reads the attacker's `iw_ops` container tagged `iw_op_election_interference` whose `iw_target` is ROOT, and takes its phase.
- **On-action:** `covert_warfare_on_actions.txt` → `on_election_campaign_end` → `on_actions = { covert_warfare_election_end }` → calls `covert_op_election_confidence_effect` scripted effect.
- **Notification:** `iw_election_interference_confidence` message sent to the affected country.

### AI Behavior
- **Evaluation chance:** Low (0.02–0.05) to prevent spammy toggling. Aggressive rulers get +0.02–0.03, cautious rulers get ×0.25–0.5.
- **Will propose guards:** `in_default = no`, `country_rank >= rank_value:major_power` (peacetime ops), rivalry/antagonistic/domineering attitude required, IC advantage check for some ops.
- **Propose score:** Scales with rivalry (+10), great power rank (+5–7), aggressive ruler (+5–8).
- **AI Funding Management:** Monthly pulse auto-sets funding: 0 if in default/bankrupt, 2 for GPs with rivals, 1 for major powers, 0 otherwise. Player uses buttons.
- **Wartime ops:** Higher eval chance (0.05), no rank requirement, `in_default = no` guard only. `propose_score` 15, +10 rivalry pact with the target, +5 GP, +5 when `is_losing_war_against = { ENEMY = scope:target_country }` (battlefield read from `common/scripted_triggers/nuke_triggers.txt`; see § War Support Feeds).

### Cancellation Conditions
- **All 7 peacetime ops** (election interference, financial subversion, industrial espionage, military espionage, influence campaign, ideological subversion, destabilization) have war and truce checks in both `possible` and `requirement_to_maintain`. Operations auto-cancel if war or truce with the target begins.
- **Wartime ops** (infrastructure sabotage, communications disruption) require active war with the target; they auto-cancel if peace is achieved.
- **Script value scope:** All covert warfare SVs use `owner = {}` wrapping to access country-scope data from JE scope (the `on_monthly_pulse` context). This is required because the JE monthly pulse runs in journal entry scope, not country scope.

## War Support Feeds (1.14 hook)

Vanilla 1.14 computes each country's weekly war support change in `common/script_values/war_support_values.txt`; its last term, `war_support_from_journal_entries`, is the only slot that accepts a per-line `desc` key. The mod injects into it from **`common/script_values/zz_te_war_support_injections.txt`** (`INJECT:war_support_from_journal_entries`; `zz_` so the file sorts after the vanilla target — INJECT errors if the target does not exist yet). `root` = country, `scope:war` = the war being evaluated; no randomness; it runs per country per war per beat, so conditions are `has_modifier` / pact / war-participant checks only. Labels live in `te_miscellaneous_l_english.yml` (`WAR_SUPPORT_TE_*`).

| System | Condition (root = country) | Per beat |
|---|---|---|
| World War | `je:je_world_war ?= { has_modifier = ww_home_front_strain_modifier }` (2+ years) — the phase modifiers sit on the **journal entry**, not the country | −0.5 |
| World War | same for `ww_prolonged_war_exhaustion_modifier` (4+ years; stacks with the line above) | −0.5 |
| United Nations | `un_condemned_modifier` on root (`else_if` `un_non_binding_rebuke_modifier`, −0.25) | −0.5 |
| United Nations | an enemy in `scope:war` carries `un_condemned_modifier` ("the world is with us") | +0.25 |
| Covert Warfare | root is `second_country` of a `covert_comms_disruption_action` pact whose attacker fights in `scope:war` (flat — operation phase lives on the attacker's containers) | −0.25 |
| Nuclear | root lacks `nuclear_power` and an enemy in `scope:war` has it (strikes themselves already drain through devastation and the one-off in `nuclear_industrial_strike`) | −0.25 |

Scale: vanilla's per-beat factors run from −5 (fully occupied) to about +2; the rival boost / taking loans are ±0.25. War support is 0–100, drifts toward 50, red band ≤ 25.

**Battle war-support modifiers** (`country_war_support_battles_increase_mult` / `_decrease_mult`, vanilla 1.14; every grant sums into `1 + Σ`, floored at 0, no upper clamp). Mod grants — laws in `common/laws/extra_laws.txt`, techs in `common/technology/technologies/era_7.txt` / `era_9.txt`:

| Entity | increase | decrease |
|---|---|---|
| `law_ministry_of_propaganda` (spin machine; always stacks on `law_outlawed_dissent`) | +0.15 | −0.15 |
| `law_state_controlled_internet` (mirrors `law_censorship`) | −0.10 | −0.20 |
| `law_unregulated_internet` / `law_net_neutrality` | +0.20 / +0.15 | same |
| `law_state_secrets` / `law_freedom_of_information` / `law_open_government` | −0.05 / +0.05 / +0.10 | same |
| `law_total_war` / `law_limited_war` (how much of society is invested) | +0.25 / −0.10 | same |
| `television_broadcasting` / `satellite_communications` / `social_media` (the living-room war) | +0.10 / +0.05 / +0.15 | +0.15 / +0.10 / +0.20 |

The worst-case mod-added negative `decrease` sum is −0.50 (`/modifier-grants/country_war_support_battles_decrease_mult?scope=mod`), so with vanilla `law_outlawed_dissent` (−0.4) it stays above the floor; vanilla's `war_propaganda` + `mass_propaganda` techs (−0.2 each) can then floor it, which is intentional — a fully censored state never hears about its defeats. `decrease_mult` is `color=bad`, so a beneficial negative renders red (vanilla's propaganda techs share the quirk). The casualties axis (`country_war_support_casualties_mult`) is deliberately untouched: the mod already saturates it (`law_total_war` −0.75 alone is 3× vanilla's largest law value).

**Battlefield "losing" reads** — `is_losing_war_against = { ENEMY = scope:x }` in `common/scripted_triggers/nuke_triggers.txt`: most size-weighted battles in the shared war lost (`size_weighted_won_battles_fraction < 0.35` after `num_significant_battles >= 5`) or `enemy_occupation >= 0.25`. Used by the nuke AI `will_propose` (strategic and tactical; the previous war-support proxy also fired for merely unpopular wars) and as the +5 desperation term in the wartime covert ops. The nuke `propose_score` is ×1.5 in a war where `is_at_war_with_rival = ROOT`. `enemy_side_occupation` is the share of the *enemy* we hold (high = winning) and is not a losing read.

**World War stalemate event** `world_war_events.31` (weight 5 in the `je_world_war` monthly pulse): `ww_years_elapsed >= 2` (world-war-wide counter) **and** a war with `war_duration_months >= 24`, `num_significant_battles >= 10`, `has_stalled_wargoal_held_by = ROOT`. Options use one-off `add_war_war_support` (+5 hold the line / −10 armistice talks); `add_war_support_change` is avoided because it accumulates for the war (see `docs/guides/scripting_best_practices.md`).

**Not moved into the hook:** `war_propaganda_on_action` (`extra_on_actions.txt`, monthly per-state `add_war_war_support` driven by the state-scoped `state_war_support_monthly_add`, which does not cascade to a country-scope read) stays a one-off level change; a phase-scaled covert line would need a country variable written by the covert JE pulse.
