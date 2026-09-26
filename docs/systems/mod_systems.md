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
- **Tourism** — `tourism_output` × `total_tourism_output_bonus_percent` and `tourism_throughput` × `total_tourism_throughput_bonus_percent` (state scope), re-applied by `te_update_tourism_modifier` from `tourism_on_action` on `on_monthly_pulse_state`, because its inputs (`city_size_rank`, building levels) move monthly. Uses ~2700 lines of state_region appeal values in `common/script_values/tourism.txt`. It must run from a state pulse: law, treaty and building hooks have unreliable scope chains for state-targeted script values.

## Production Methods (PMs)

- PM group icons are displayed in several GUI panels: `production_methods.gui`, `building_browser_panel.gui`, `building_details_panel.gui`, `goods_state_panel.gui`.
- The mod adds a `pmg_maintenance` PM group that should be **hidden** from all PM icon displays using `visible = "[Not(EqualTo_string(ProductionMethodGroup.GetKey, 'pmg_maintenance'))]"`.
- PM icon displays use `scrollarea` + `flowcontainer` (not `fixedgridbox`) so hidden items collapse properly and scrollbars appear when > 4 PM groups. Max width: `208` pixels (4 × 52px icons).

## Global Warming (`je_global_warming`)

> See also: `docs/systems/journal_entry_systems.md` for full JE system documentation.

- A persistent journal entry (never completes: `complete = { always = no }`, `can_deactivate = no`).
- Tracks `temperature_anomaly_display` script value against a 4°C progress bar. The goal is frozen at activation, which is why `goal_add_value` is `4 - temperature_anomaly_display` and not a flat `4` — see `journal_entry_systems.md` before touching it.
- Auto-activates from `is_shown_when_inactive` (game rule) + `possible` (anomaly ≥ 0.1°C). There is **no** `should_be_involved` block; an earlier version of this line claimed one.
- 6 temperature tiers (negligible → catastrophic), defined **once** in `gw_severity_text` / `gw_severity_short` (`common/customizable_localization/global_warming_custom_loc.txt`). `status_desc` is a single key that calls it.
- Uses 16 scripted buttons (`gw_*`) for climate policies, each carrying `is_ai = yes` so only the AI sees the grid. Their `possible`/`effect` bodies live in `common/scripted_triggers/global_warming_triggers.txt` and `common/scripted_effects/global_warming_effects.txt`, shared with the widget's scripted GUIs.
- **Player surface: the climate dashboard**, three widgets from `gui/journal_entry_widgets/global_warming_widget.gui` in `custom_widget_container_1/_2/_3`, handled by `common/scripted_guis/global_warming_sguis.txt`. Full documentation, op table and editing rules in `journal_entry_systems.md` → **Climate Dashboard**.
- **Emissions are a property of a market, not a country.** `market_greenhouse_gas_emissions_script_value` sums the whole market's oil and coal consumption, so the snapshot is stored on the market leader and every member reads it through `market_capital.owner`.
- **Display figures are snapshots, not live reads.** The reason text used to evaluate 14 script values every frame the panel was open, three of them world-scale sweeps. Now: `gw_snapshot_market_emissions_effect` (yearly state pulse, leaders only, at the site that was already computing the figure), `gw_rebase_annual_emissions_effect` (monthly global pulse, acts in January, O(1)), `gw_refresh_global_counts_effect` (monthly global pulse, one country sweep filling all eight adoption counters). Readers are the guarded O(1) values in `common/script_values/global_warming_values.txt`. The eight old `gw_countries_with_*_script_value` sweeps are deleted — do not reintroduce them.
- **History charts:** two series (`gw_temp`, `gw_share`) recorded by `common/scripted_effects/te_history_global_warming_effects.txt`. Both step once a year because that is the cadence emissions move at. Temperature is global but stored per tracked country, because `te_history_chart`'s datamodel is hard-coded to the country list — see **History Store and Charts**. No markers this wave.
- Events: `environmentalism_events.txt` — threshold events at 0.5°C, 1.0°C, 2.0°C, 3.0°C.
- Cooling/reversal support: `global_warming_events_on_action` now also fires one-time recovery events when temperatures decline below 3.0°C, 2.0°C, 1.0°C, 0.5°C, and 0.1°C (`environmentalism_events.17`–`environmentalism_events.21`).
- **Disabled rule = no climate change.** `global_warming_update_on_action` accumulates emissions only under `global_warming_enabled`, and `global_warming_events_on_action` runs the display snapshots and the threshold events (`.1`–`.4`, `.17`–`.21`) only then. Its `else` holds `global_var:greenhouse_gas_emissions` at 0, which also clears the warming an older disabled-rule save built up, so every outside reader of `temperature_anomaly_display` (UN docket, election events, movements, treaty article 109) sees 0. The JE never activates, so its recurring events never fire. `.7` (pollution scandal) is about pollution, not warming, and fires under both settings. There are no `*_no_gw_modifier` fallbacks any more.
- `.13` (climate summit) is the fallback for a world without a UN. It needs `united_nations_disabled` or no `un_founded`, because while a UN exists the accord is `un_events.17`.
- Test console: `event te_debug_gw.1` (`events/te_debug_gw_events.txt`).
- The JE sits in `je_group_internal_affairs`. A `je_group_environment` is declared in `common/journal_entry_groups/timeline_extended_je_groups.txt` and unused; moving this entry there was deliberately left out of scope.

## Construction Cost Scaling

- **Purpose:** Makes construction more expensive for richer countries (GDP per capita). Prevents runaway exponential growth and provides catchup for poorer nations.
- **Modifier:** `construction_cost_scaling` in `common/static_modifiers/extra_modifiers.txt` — `goods_input_construction_mult = 1`.
- **Script values:** `common/script_values/extra_script_values.txt` — search for `CONSTRUCTION COST SCALING`.
- **On action:** `construction_cost_scaling_on_action` in `common/on_actions/extra_on_actions.txt`, wired to `on_yearly_pulse_country`.
- **Tuning:** `construction_cost_gdppc_reference`, `construction_cost_floor_ratio` (1x), `construction_cost_ceiling_ratio` (14x), `construction_cost_max_mult` (10 = +1000%).
- **Curve:** Linear interpolation from 0 at floor to `max_mult` at ceiling.
- `goods_input_construction_mult` affects both construction project costs AND ongoing building maintenance.
- With `free_market_construction_rule` disabled there is no construction good to scale, so the on_action applies `construction_cost_scaling_direct` (`country_construction_goods_cost_mult = 1`, adjusted by `construction_cost_scaling_direct_adjusted_mult`) instead. See § Free Market Construction off.

## Construction as a Market Good (FMC architecture)

> Cross-reference: `docs/vanilla/vanilla_economy_reference.md` § 9 establishes the vanilla two-FCFS-queue model (government queue from treasury, private queue from IP, allocation set by `country_private_construction_allocation_mult`). This mod adds a market layer underneath without replacing the queues. Based on the third-party *Free Market Construction* mod (credited in `README.md`); every file is prefixed `te_construction_market_*`.

**Why:** Decoupling construction *capacity* (the vanilla `country_construction` country-resource that the FCFS queues spend) from construction *output* (what the construction sector actually produces) lets per-state economics influence national construction throughput. A goods-side stockout in one region propagates through the price loop instead of disappearing into a black-box country resource.

**Architecture (3 layers):**

1. **Construction-sector building, REPLACE'd.** `building_construction_sector` (vanilla) is REPLACE'd in `common/buildings/te_construction_market_site.txt` (its group `bg_construction` is REPLACE'd as ordinary heavy industry in `extra_building_groups.txt`, so it is no longer government-funded), and its tier PMs are REPLACE'd in `common/production_methods/extra_pms.txt` (`pm_wooden_buildings`, `pm_iron_frame_buildings`, `pm_steel_frame_buildings`, `pm_arc_welded_buildings`, plus the mod tiers `pm_reinforced_concrete_buildings`, `pm_advanced_construction`, `pm_nanomaterial_buildings` INJECTed into `pmg_base_building_construction_sector`). Each tier now outputs `goods_output_construction_add = N` (1, 2, 3.5, 5, 6, 10, 16 across tiers) — i.e. the construction sector produces the **`construction`** market good rather than direct country construction points. State-level `state_construction_mult` is preserved so per-state efficiency still matters. Barracks under the Engineering & Logistics principle (`pm_principle_engineering_and_logistics`) also produce 0.2 per level.
2. **The `construction` good itself.** Defined in `common/goods/timeline_extended_extra_goods.txt`. `cost = 1000`, `category = industrial`, `traded_quantity = 0.1`, `consumption_tax_cost = 400` (Authority cost if the player consumption-taxes it). High base cost makes it a load-bearing market input.
3. **Auto-placed consumer building: `te_construction_market_site`.** Defined in `common/buildings/te_construction_market_site.txt`, group `te_construction_market_bg` (government-funded, hidden from the outliner). `common/defines/te_construction_market_defines.txt` points `NCountry.CONSTRUCTION_CAMP_BUILDING` at it, which is what makes the engine charge its inputs only for the points actually spent — to the treasury or the investment pool, by queue. Flags: `buildable = yes` and `expandable = yes` for direct games, but `can_build_government` is false in a market game, so nobody builds one (script's own placement raises `te_cm_placing_site`, which the trigger accepts); `downsizeable = yes`, also for direct games, so a player or the AI can remove a site — capacity is spread over the remaining staffed sites each pulse, and `te_construction_market_ensure_site` re-places a capital site at the end of the pulse if none is left; `min_raise_to_hire = -1.0`, `levels_per_mesh = -1`. Placed automatically by `te_construction_market_sector_placement_effects.txt` in each state where construction starts (with a capital fallback). Its single PM (`pm_te_construction_market_base` in `common/production_methods/te_construction_market_pms.txt`) consumes 1 `goods_input_construction` per workforce and produces 1 `country_construction_add` — i.e. it converts the construction good back into the vanilla queue currency. Each weekly pulse re-applies `te_construction_market_capacity_modifier` (`building_throughput_add`) to every site so the sites together deliver exactly the week's public + private purchase. Employment is tiny (10 laborers per level, level_scaled).

**The chain end-to-end:**

```
Construction Sector (vanilla, REPLACE'd) → produces construction good
   ↓
Market: construction good supply meets construction good demand at a price
   ↓
te_construction_market_site (auto-placed, the engine's construction camp) consumes construction good
   ↓ produces
country_construction_add (vanilla queue currency)
   ↓
Vanilla two-FCFS queues (government from treasury / private from IP) spend it
   ↓
New buildings get built / expanded
```

**Purchases and the queue split.** The government purchase is the country variable `te_construction_market_public_target` (set by the player in the construction panel, by `te_construction_market_ai_update_buy` for the AI), capped each week at what the government queue can absorb (`te_construction_market_public_use_target`: queued government levels × `country_max_weekly_construction_progress_add`). The private purchase (`te_construction_market_private_use_target`) is roughly the investment pool's gross weekly income, scaled by how full the pool is against 24 weeks of income, divided by the smoothed price (`te_construction_market_price_stabilizer`) and capped by the private queue. The private share of construction (`te_construction_market_private_share_modifier`, `country_private_construction_allocation_mult = 0.01` × the private share in percent) is set weekly from those two purchases; `common/laws/construction_system_law_injections.txt` cancels the economic-system laws' vanilla allocations so nothing else moves it.

**Construction-cost-scaling layer.** The `construction_cost_scaling` static modifier (above) applies `goods_input_construction_mult = 1` (multiplied by a per-country GDPpc-driven multiplier). This scales how much *construction good* every consumer burns — each construction site per point delivered, and every building's maintenance PM. So a richer country burns more construction good per same building → competes more for the same supply → stockouts and higher prices → fewer net `country_construction_add` produced → vanilla queues stall on availability rather than treasury.

**Buildings consume the construction good as maintenance.** `pm_maintenance` (`pmg_maintenance`, hidden in PM displays) carries `goods_input_construction_add = 0.1` per level; it is on 54 building types — industry, power, and transport infrastructure (railways, ports, airports, highways), not farms, mines or urban centres. A few company buildings in `unique_pms.txt` consume more (0.5–1). Construction is therefore not just an upfront build cost — it's an ongoing maintenance load tied to current economic activity.

**Retooling.** The engine puts the `pm_retooling` static modifier on a building that switches production methods (`NEconomy.RETOOLING_WEEKS = 260` in `extra_defines.txt`); this mod REPLACEs it with `goods_input_construction_mult = 10`, so a retooling building pays +1000% on its construction input. Two `free_market_construction_rule` settings waive the retooling cost, and one of them maintenance as well (§ Market settings without retooling or maintenance).

**Player UI.** The domestic tab of the construction panel (`gui/construction_panel.gui`, the `te_construction_market_section` block) carries the purchase control (+/- buttons bound to `te_construction_market_{increase,decrease}_target_*` in `common/scripted_guis/te_construction_market_scripted_gui.txt`; click / shift / ctrl / alt steps 1 / 10 / 100 / 1,000, right-click +10,000 or reset), a live read-out (government purchase in force and its treasury cost, private purchase and share, price per point, market supply vs demand with a shortage flag) and a collapsible "How does the construction market work?" explanation. The figures come from `common/script_values/te_construction_market_display_values.txt` (display-only, every `var:` read guarded); the text is the `TE_CM_*` keys plus the `concept_te_construction_market` game concept.

**Implications for mod authors:**

- **The two FCFS queues still apply unchanged** — government queue from treasury, private queue from IP. The mod hasn't replaced the queue model; it's added an upstream market that determines whether the queue's currency is actually being produced, and drives the allocation between the queues from the two purchases.
- **A goods-side stockout stalls both queues** regardless of treasury/IP balance. This is the design intent: construction is gated by economic capacity, not just by money.
- **When mod-adding new buildings**, give them realistic `goods_input_construction_add` in their maintenance PMs (or add `pmg_maintenance`). Skipping this makes the building free to maintain in capacity terms, undermining the system.

**Scripts (`common/scripted_effects/te_construction_market_*.txt`):**

| File | Purpose |
|---|---|
| `te_construction_market_setup_effects.txt` | Per-country setup at game start / formation: seeds the purchase and price-stabilizer variables, places the capital site. |
| `te_construction_market_sector_placement_effects.txt` | Per-state placement and removal of `te_construction_market_site` as construction starts and finishes. |
| `te_construction_market_build_effects.txt` | `te_construction_market_set_specified_level` and friends — set a building to an exact level without level creep. |
| `te_construction_market_update_effects.txt` | Weekly data refresh: private-share modifier, per-site capacity modifier, price stabilizer; border-change site re-placement. |
| `te_construction_market_pulse_effects.txt` | Weekly pulse and border-change entry points. |
| `te_construction_market_ai_effects.txt` | AI purchase target. |

Wiring: `common/on_actions/te_construction_market_on_actions.txt` (yearly heartbeat, border and building-lifecycle hooks), `events/te_construction_market_{pulse,recalc,building}_events.txt` (a self-relaying daily tick that fans out the weekly body to every country every 7th tick), `common/history/te_construction_market_global.txt` (game-start setup).

**Script values (`common/script_values/te_construction_market_*.txt`):**

| File | Key values |
|---|---|
| `te_construction_market_current_values.txt` | `te_construction_market_price` (market price × construction cost scaling) and the realised spending/use split. |
| `te_construction_market_target_values.txt` | Public/private purchase targets, private share, price-stabilizer step. |
| `te_construction_market_sector_placement_values.txt` | `te_construction_market_per_site` and the staffing-adjusted per-site throughput. |
| `te_construction_market_ai_values.txt` | AI purchase target (income, reserves, debt; war and banking-stress brakes). |
| `te_construction_market_pulse_values.txt` | Tick bookkeeping for the self-relaying pulse. |
| `te_construction_market_display_values.txt` | Display-only figures for the construction panel. |

### Market settings without retooling or maintenance

`free_market_construction_rule` has four settings. Three run the market (`te_free_market_construction_on` is true for all three, so nothing else in the system tells them apart):

| Setting | Maintenance (`pmg_maintenance`) | Retooling (`pm_retooling`) |
|---|---|---|
| `free_market_construction_enabled` (default) | `pm_maintenance` | applies |
| `free_market_construction_no_retooling` | `pm_maintenance` | removed by script |
| `free_market_construction_no_maintenance` | `pm_no_maintenance`, forced (the direct setting's flags for that group) | removed by script (it would multiply nothing) |
| `free_market_construction_disabled` | `pm_no_maintenance`, forced | applies, multiplies nothing (§ Free Market Construction off) |

Everything else in both new settings is the enabled setting's: the Construction Site's market method, and the company buildings (`pm_disney_world`, `pm_generic_industrial_city`, `pm_generic_monument_to_industry`) and Engineering & Logistics barracks keep their construction-good recipes, which are production, not upkeep.

**No retooling cannot be a PM flag.** `pm_retooling` is a static modifier the engine applies for `RETOOLING_WEEKS`; neither a static modifier nor a define has a rule gate, and a cancelling modifier would have to be put on each retooling building by the same script that can simply remove the penalty (`scripting_best_practices.md`, "Gating a Mechanic on a Game Rule When It Lives in a Define, PM or Building Group"). So `te_pm_retooling_waived` (`te_construction_market_triggers.txt`; names the two settings, so a pre-rule save keeps paying) gates `te_remove_waived_pm_retooling` (`extra_effects.txt`, building scope), which removes the modifier:
- from `on_production_method_changed` (`te_on_production_method_changed_retooling`, `te_construction_market_on_actions.txt`; root = the building), at once and again a day later through `te_construction_market_building_events.3`, since whether the engine applies the modifier before or after the hook fires is unverified;
- from the weekly sweep `minor_events_timelineextended.100` (every building of every state), which catches any PM change the hook misses, such as one the engine makes itself.

The same effect keeps its older job in every setting: removing the modifier from level-0 buildings (also from `on_start_expanding_building`).

**Play-test list.**
1. *No retooling, switch a PM* on a factory with maintenance: the Retooling modifier does not appear on the building (or is gone the next day), and its construction input stays at 0.1 per level (times cost scaling). An AI country's buildings show no Retooling modifier after a few weeks.
2. *No maintenance, day 1*: `pmg_maintenance` shows No Maintenance only; the construction market read-out's demand is the government and private purchases plus the company buildings. Construction Sites, sectors and the panel work as in the default game.
3. *Default game*: switching a PM still applies Retooling (+1000% construction input).

### Free Market Construction off (direct construction)

`free_market_construction_rule` (default enabled) turns the whole market off at game setup for base-game-style construction. Script asks `te_free_market_construction_off` / `_on` (`common/scripted_triggers/te_construction_market_triggers.txt`), which test the **disabled** setting so a save from before the rule keeps the market.

**The Construction Site is the construction sector.** `CONSTRUCTION_CAMP_BUILDING` is a define, so no rule can move it off `te_construction_market_site`. In a direct game the site therefore *is* the Construction Sector: buildable and expandable by the government (`can_build_government` = the rule; `possible` = Urbanization, as vanilla's sector), with tier PMs whose recipes are written out. Being the camp, it gets vanilla's whole treatment: the engine buys its inputs only for the points actually spent, and the AI's construction planning (below) works on it. `building_construction_sector` can't be built in a direct game.

**The rule's PM flags do the switching** (`common/game_rules/extra_game_rules.txt`, the vanilla `disable_<pm>` / `force_<pm>` mechanism of `monument_effects`; `scripting_best_practices.md`, "Locking Production Methods"). No script activates or corrects a PM during play; each setting disables the other's methods (all `is_hidden_when_unavailable`):

| Group (buildings) | Market (rule on) | Direct (rule off) |
|---|---|---|
| `pmg_base_te_construction_market_site` (site) | `pm_te_construction_market_base`: 1 construction good → 1 point | `pm_te_direct_construction_<tier>`, 7 tiers: the Construction Sector tier of the same name (`extra_pms.txt`) with its construction-good output as `country_construction_add` — the same inputs, employment, `state_construction_mult`, mortality and required inputs. Per level: 1 / 2 / 3.5 / 5 / 6 / 10 / 16 points. `ai_selection = most_productive`; the tech gates are the sector's |
| `pmg_construction_automation`, `pmg_construction_principle` (sector and site) | on the sector only in practice: each gated PM's `unlocking_production_methods` lists the 7 sector tiers and the 7 direct tiers, never the market base PM | the same PMs, on the site |
| `pmg_maintenance` (54 building types) | `pm_maintenance` (0.1 construction per level); `pm_no_maintenance`, forced, in the no-maintenance setting | `pm_no_maintenance`, forced |
| `pmg_disney_world`, `pmg_generic_industrial_city`, `pmg_generic_monument_to_industry` | the original PM (consumes the construction good) | `pm_<same>_direct`, forced: the recipe without the good |
| `pmg_principle_engineering_and_logistics` (barracks) | the principle PM (0.2 construction good per level) and its no-effect fallback | `_direct` twins: 0.2 `country_construction_add` per level instead |

**Script left.**
- *Conversion at game start* (`te_direct_construction_convert_sectors`, from `on_game_started_after_lobby`, when the rules are final): every `building_construction_sector` the history placed becomes a site of the same level (capped at 100) on the matching direct tier. It then sets the global `te_direct_construction_converted`, which closes the sector's `can_build_*` — until then they stay open so the history's own `create_building` seeding works whatever the rule.
- *Private share*: `te_direct_construction_law_private_share` restores the economic-system laws' vanilla allocations (25 / 50 / 75 / 35 / 10 %), which `construction_system_law_injections.txt` cancels for the market; keep the two in step. Applied at country setup (`te_direct_construction_country_setup`) and refreshed weekly (`te_direct_construction_on_weekly_pulse`).
- *AI site guard* (`te_direct_construction_keep_ai_sites`, weekly). Play-testing showed AI countries removing every Construction Site they had. No script removes a site in a direct game, so this is the AI downsizing them, and script can't steer that. The site stays `downsizeable` for players, so the guard works after the fact. Each week every state records its site's level and tier (state variables `te_dc_site_level` / `te_dc_site_tier`, recorded for players too, so a player's own downsizing is never undone). An AI country then gets back any levels it lost since the last pulse. A site that is still there is raised with `create_building`, so it keeps its workers (the engine's documented "larger of the two levels"). If it comes out above the record (the disputed "adds levels" reading), it is rebuilt at exactly the record. A rebuilt or re-created site is moved back to its recorded tier. The guard skips an AI country `in_default`, whose record follows it down, and one without Urbanization (the site's `possible`). The AI can still add levels and sites and choose tiers.
- *Base construction* (no script). The disabled setting applies `te_direct_construction_base_modifier` ("Base Construction", `country_construction_add = 5`) to every country, player and AI, with `apply_modifier = all:<modifier>` (vanilla `game_rules.md`). It is always on and needs no refresh. A country with no sites (the AI in default, a player who downsized everything, a country before Urbanization) can therefore still build. The value is five wooden site levels' worth, small beside a working construction sector. Its points carry no wages. Whether they draw on the sites' material purchases (the engine buys the camp's inputs per point spent) is unverified.
- *Market placement is off*: `te_construction_market_state_on_start` / `_on_end`, `te_construction_market_country_setup`'s capital site and `te_construction_market_on_border_changes` only act in market games.
- *Construction Cost Scaling*: `construction_cost_scaling_direct` (`country_construction_goods_cost_mult`, vanilla's lever on construction-material cost), same curve, same multiplicative adjustment.
- *Construction panel*: `te_direct_construction_section` shows construction per week (`modifier:country_construction_add`) and the law share; `te_construction_market_rule_on_sgui` picks the section and hides every purchase handler. The vanilla "no construction sector" prompt offers the site instead of the sector.

**Why the AI can run it.** Every piece the base game's AI uses is present in its vanilla shape: the camp is the buildable, government-funded building whose PMs carry `country_construction_add` (`ai_value = 500` in `00_modifier_types.txt`) and goods inputs, as vanilla's sector does. So the engine's construction planning applies unchanged: `MONEY_SPENDING_CONSTRUCTION_CRITICAL_THRESHOLD` / `_EXCESSIVE_THRESHOLD` (actual-to-wanted construction), `GOVERNMENT_BUILDING_STATE_POP_CONSTRUCTION_SECTOR_IMPORTANCE_*` (first level in populous states), `GOVERNMENT_BUILDING_NO_AVAILABLE_WORKFORCE_FACTOR` (staffing), and the debt pauses. The site's `ai_value` is the market-mode sector's formula in direct games and 0 in market games. Tier choice is `most_productive` over the same shape of PMs as vanilla's `pmg_base_building_construction_sector`. None of this has been watched in game yet; see the play-test list.

**Deliberate differences from the base game and from the market-mode sector.**
- *Downsizing is allowed in both modes.* A direct game needs it: a site's wages are paid whether or not its points are used, so overbuilding must be reversible. In a direct game the AI's downsizing is undone at the next pulse by the AI site guard (above), except in default. In a market game it lets the player or the AI remove a site; `te_construction_market_ensure_site` puts back the last one, so the worst case is about two weeks without construction (a week to be re-placed, a week to hire and be sized).
- *Base construction.* Direct games give every country a flat 5 construction points a week (above).
- *Building-group properties.* `te_construction_market_bg` has no economy of scale (like vanilla's sector), no infrastructure use (vanilla 2/level, the market sector 0.1) and no urbanization (vanilla 5), and is hidden from the outliner.
- *Buffs that name the sector.* Throughput aimed at `building_construction_sector` or `bg_construction` (banking-event booms, `we_se_astronaut_industry`) doesn't reach the site, and `company_construction_power_bloc`, whose `possible` needs a level-5 sector, can't form.
- *Market-mode sites list two empty groups.* The site carries the automation and principle groups for direct games; on a market site their methods are unavailable (they need a sector or direct tier), so it shows No Construction Automation and No Effect.
- *Company buildings pay nothing* for the construction they consumed; the twins drop the input rather than price it in materials.
- *A converted site starts empty.* The sector's workers are released when it is removed; the site hires them back at its hiring rate of 1.0, so a direct game's construction may start a week late.
- *Saves from the first version of this rule* (#394, weekly capacity script) aren't migrated. Start a new direct game.

**Play-test list.**
1. *Market game (the default), new game and a pre-rule save.* Day 1: the capital has a Construction Site on Basic Construction Market, and states that start construction get one. Construction Sites can't be queued (the build menu may list them as unavailable). No building offers No Maintenance or a `_direct` method. Construction behaves as before this change. Downsize the only site: a new capital site appears at the next weekly pulse, and construction resumes the pulse after. **AI:** watch for AI countries downsizing their sites; a country that does it repeatedly would keep losing construction, and would need a further guard.
2. *Direct game, day 1.* No Construction Sector anywhere; a Construction Site of the same level on the same tier stands where each was. Sites show the seven tiers (the unresearched ones hidden), with automation and the principle group. `pmg_maintenance` shows No Maintenance only. The panel's construction per week matches the sites' levels × tier points (plus base construction). The private share matches the law.
3. *Direct game, build.* Queue a new site: it starts on a researched tier (which one the engine picks is unverified; any researched tier is acceptable). Expand one, then downsize it: its wages drop with it.
4. *Direct game, AI (observer, 10–20 years, watch 3–4 AIs of different size).* (a) Countries without a site build one once they have Urbanization; populous states get the first levels. (a2) No AI country outside default ends up without sites: levels an AI downsizes are back at the next weekly pulse, at the same tier. Check that a site that loses a level comes back at exactly its old level (not above it), and that the restored level rehires. Watch whether an AI downsizes the same site week after week; if it does, the guard is holding against constant pressure and the AI's reason (budget, staffing) needs a look. (b) Levels keep up with the construction queue (the panel's construction per week grows with GDP). (c) Sites move to higher tiers as the techs arrive. (d) Sites stay staffed (occupancy near 100% outside labour shortages). (e) Treasury and debt: no country sits paused on construction debt for long because of site wages or materials.
5. *Direct game, costs.* Construction Cost Scaling shows as Construction Goods Cost on rich countries, and the materials the sites buy follow the points spent.
6. *Direct game, base construction.* From day 1 every country, player and AI, shows Base Construction (+5) in its construction tooltip, and the panel's construction per week includes it. A pre-rule save and a market game don't show it. Downsize every site as a player: construction stays at 5 or more, and new sites can be queued and built.

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

## Dynamic Homeland Progress

- **Parallel per-culture tracks:** each eligible culture gets its own script container and progress bar. All eligible homelands can form or decay simultaneously. A new candidate begins at zero and cannot inherit another culture's progress. Containers are parented to the state, kept in separate creation/removal lists, and removed from the list before destruction.
- **Timing:** the monthly state pulse adds te_homeland_annual_progress units toward 1200; display divides stored units by 12. Base 10 units/month completes in exactly 120 months (10 years). Promote National Values alone makes this 30 months. Existing additive speed modifiers, turmoil/legitimacy multipliers and the 1–95 annual-rate clamp remain.
- **Gates:** homeland changes enabled on the owner (`country_homelands_can_change_bool`, granted by the laws `law_ethnostate`, `law_minority_rights_violent_hostility` and `law_linguistic_purity`, Cultural Unity principle tiers II–V, and the `mass_media` tech; the tile names them via `TE_HOMELAND_UNLOCK_SOURCES`, which `test_homeland_unlock_sources.py` keeps in sync), unified regional ownership, and culture meeting existing primary/homeland/population checks. Creation is inclusive at the formation threshold; removal is strictly below its threshold.
- **Pausing/resetting:** losing the unlock or unified ownership pauses valid progress. A different owner or invalid target (population, primary status, homeland status) clears that track. Progress cannot pass to another owner/culture. A zero removal threshold cannot be met.
- **UI:** always-visible Homeland Dynamics tile, including states with no existing homelands; its contents are conditional. A Creation or Removal section appears only while it has projects or can run here (`te_homeland_<track>_shown`; removal also needs a removal threshold above the base 0%, `te_homeland_removal_threshold_open`), so a state where no primary culture lacks a homeland and no non-primary culture has one shows a single "no culture here can gain or lose homeland status" line (`te_homeland_relevant = 0`) instead of empty sections. Bars exist only for real per-culture projects (percentage, culture, and a warning once a project stops qualifying). An unlock or split-region pause is one tile-level line (`te_homeland_pause_status`), shown only when a track applies; while paused, only tracks with kept progress are listed. A visible section's own line is its population threshold, monthly points, or "starts next month". Threshold numbers (in the blocker lines and the tile tooltip) are hoverable: each shows the clamped threshold the gate tests, a note when the clamp binds, and the modifier's per-source list (`GetDescFor`). Tooltip explains thresholds, rate and pause/reset rules.
- **Files:** homeland_triggers.txt, homeland_effects.txt, homeland_values.txt and homeland_sguis.txt under their respective common/ directories. te_homeland_monthly is wired in extra_on_actions.txt; GUI content lives in te_state_panel_widgets.gui.
- **Save compatibility:** variables initialize on the first eligible monthly pulse; UI reads missing variables as zero. No migration or new game is required.

## State Panel GUI Enhancements

Custom `state_panel_status_item_small` tiles added to `gui/states_panel.gui` for mod-specific state info. Each tile's name is the concept alone; its readings are aligned label/value rows in the tile's `extra_widget`, and the detail is in the tooltip:

| Widget | Icon | Concept | Rows | Tooltip |
|---|---|---|---|---|
| **Homeland Dynamics** | `state_homelands.dds` | `concept_homeland_dynamics` | Creation / removal sections, each shown only when it applies: per-culture progress bars and live status; one pause line, or one line when nothing here can change | Effective thresholds, annual progress, speed modifiers, pause/reset rules and what enables homeland changes (also the hover on the unlock pause line) |
| **Arable Land** | `wheat_farm.dds` | `concept_arable_land` | Total, regional additions, multiplier % | Geographic base, `GetValueWithBreakdownFor('state_arable_land_mult')` |
| **Migration Crowding** | `population.dds` | `concept_migration_crowding` | Population, threshold, ratio (+ a bar to the 10x knee), pull penalty | Curve explanation, urban capacity breakdown |
| **Solar Collector** | `space_elevator.dds` | `concept_solar_collector_array` | Available, generated | Active / reserved / queued |
| **Antimatter Facility** | `power_plant.dds` | `concept_antimatter_facility` | Available, generated | Active / reserved / queued |

- **Widget library: `gui/te_state_panel_widgets.gui`.** `states_panel.gui` is a full-file override re-merged on every vanilla patch, so the mod's own types live there and the override holds only instances.
  - `te_state_stat_row`: a fixed-width label column plus a fixed-width value column with its text anchored right, so a stack of rows ends at one x.
  - `te_state_tile_row` sizes it for a tile's 160 px text column; `te_state_wide_row` drops the icon slot for headers and footers.
  - `te_state_stat_bar`: a 4 px headroom bar, a bare `progressbar` fed by a 0–100 `*_fill_pct` script value that carries its own cap.
- **Tourism card** (`te_state_tourism_card`): a 530 px card between the population block and the status grid.
  - It sits outside the grid because the grid is `wrap_count = 2` over 260 px tiles, and anything that isn't exactly one tile breaks its rows.
  - Output column: base appeal, cities (with world rank). Throughput column: ports, transit, art, parks, monuments. Each capped source has a bar toward its cap; the caps are in the `tourism_fill_*_pct` values at the end of `common/script_values/tourism.txt`.
  - Footer "All modifiers": `State.GetModifier.GetValueWithBreakdownFor('goods_output_tourism_mult')` and `('building_tourism_industry_throughput_add')`. These also carry airports, decrees, pollution, grand monuments and so on, and lag the scripted sources by up to a month.
  - Per-source tooltips `te_state_tourism_*_tt` state each tier schedule.
- **Loc keys:** `TE_STATE_*_STATUS` (tile title), `TE_STATE_*_ROW_*` / `TE_STATE_POINTS_ROW_*` (row labels), `TE_STATE_*_TT` (tooltip) and `te_state_tourism_*` in `localization/english/te_miscellaneous_l_english.yml`.
- **Script values for GUI:** `arable_land_total`, `arable_land_base`, `arable_land_from_modifiers`, `arable_land_mult_pct`, `migration_crowding_pull_pct`, `migration_crowding_threshold_pop`, `migration_crowding_fill_pct`, `te_homeland_annual_progress`, `solar_*`, `antimatter_*` in `common/script_values/extra_script_values.txt`; `tourism_fill_*_pct` in `common/script_values/tourism.txt`.
- **Concepts:** Defined in `common/game_concepts/extra_concepts.txt`, with textures for hoverable tooltip links. The tourism rows label with `concept_tourism_*` and reuse those concept textures as row icons.
- **Pattern:** Use `[concept_X]` for hoverable concept links, `[State.GetModifier.GetValueWithBreakdownFor('modifier_key')]` for modifier breakdowns, and `[State.MakeScope.ScriptValue('sv_name')]` for computed values. A value cell that shows one expression inlines it as `raw_text = "#v [...]#!"`.

## Nuclear Weapons (`je_nuclear_program`)

> See also: `docs/systems/journal_entry_systems.md` for full JE system documentation.

**One entry for the whole nuclear system.** Shown to the player as "Nuclear Weapons"; the key is still `je_nuclear_program` so saves keep it (a new auto-activating key never appears in an older save). Since 2026-09-25 it also carries posture and crises — the separate `je_nuclear_deterrence` entry was folded in to save a journal slot, and its mechanics are described under **Nuclear Deterrence and Crisis Diplomacy** below. Two gates, deliberately different:

- **The entry** is active for anyone it applies to — `possible = nuclear_program_entry_applies` (`nuke_triggers.txt`): a country with a programme, a country holding warheads (whatever its rank), or a party to a nuclear crisis. `is_shown_when_inactive` also shows it, inactive, to a country with the `nuclear_weapons` tech but no standing, whose status line says what it lacks.
- **The programme** — funding, warhead progress, development events — runs only while `nuclear_program_has_programme` holds: the game rule, the `nuclear_weapons` tech, and `nuclear_program_can_run_programme` (Great Power, Major Power + ICBMs, or a programme-aid recipient, and not disarmed). The weekly pulse calls `nuclear_program_weekly_progress` only then, and zeroes funding the week it stops holding, so a demoted power keeps its arsenal, posture and upkeep but stops building and paying for more. **Every "does this country have a programme?" test asks `nuclear_program_has_programme`** — not `has_journal_entry = je_nuclear_program`, and not the existence of the programme's variables, which the entry's `immediate` creates for everyone it activates for (the AI's buttons read them unguarded).

- Native progress bar: progress toward the next warhead.
- 2 funding buttons (increase/decrease), hidden from humans with `is_ai = yes` and kept as the AI's only path into the system. Their `possible` / `effect` bodies live in `nuclear_program_possible_*` and `nuclear_program_effect_*`; `nuclear_program_possible_increase_funding` starts with `nuclear_program_has_programme`.
- Player-facing UI, top to bottom: the **programme panel** (container `_3`, above the bar; only while there is a programme), the native bar, then in container `_4` the **posture** panel (only while armed), the **crisis and reputation** panel, and **delivery and defence plus the nuclear-powers leaderboard** (`widget_je_nuclear_balance`). Full description: `docs/systems/journal_entry_systems.md` → Nuclear Programme Widget and Nuclear Deterrence Widget.
- Diplomatic actions: `nuke_diplo_action`, `tactical_nuke_diplo_action`. These stay diplomatic actions; the widget never launches a strike. Both are gated on the deterrence doctrine and non-use pledges as well as the war laws, and their AI decides through `nd_ai_nuclear_use_justified` — see **Nuclear Deterrence and Crisis Diplomacy** below.
- Treaty articles: `nuclear_disarmament`, `nuclear_program_aid`, `nuclear_program_pause`.
- Events: `nuclear_weapon_events.txt` — nuclear strike response events. `events/te_debug_nuclear_events.txt` is a console-only test harness (`event te_debug_nuclear.1` / `.2`).

**The funding modifier lives on the journal entry, not the country.** The buttons apply `nuclear_weapon_program_funding` in `je:je_nuclear_program` scope with `multiplier = nuclear_weapons_program_current_cost`, so every `has_modifier` / `remove_modifier` for it must use that scope too — in country scope it is a silent no-op. `nuclear_program_refresh_state_effect` is the single site that owns it: it takes the modifier off when `nuclear_weapons_program_funding` reaches 0, deciding from the variable rather than from `has_modifier`, because modifier changes are not visible inside the same effect block and a scripted-effect call is inlined into its caller's.

**Disarmament deactivates the entry** — unless the country is in a nuclear crisis, which keeps it active for the crisis panel. Both `nuclear_program_can_run_programme` and `nd_is_armed` exclude `country_nuclear_disarmament_bool` and the entry has `can_deactivate = yes`, so a `nuclear_disarmament` article or the UN's `un_npt_disarmament_modifier` drops it back to inactive before the weekly pulse can run — which is why the article zeroes the variables itself in `on_entry_into_force`, and why "our programme has been dismantled" is in `status_desc` rather than in the widget.

**Re-activation preserves the arsenal.** `immediate` runs on every activation, so `nuclear_weapon_stockpile` and `nuclear_weapons_program_first_nuke_done` are created only when absent. `nuclear_weapon_program_progress` and `nuclear_weapons_program_funding` are still zeroed unconditionally, deliberately: the progress bar's goal is computed once at activation from `current_value + goal_add_value`, so leftover progress would give a non-zero baseline and a goal above 100, and the bar would read negative once the next warhead wrapped it.

**Civil wars.** A revolution's winner receives the loser's country variables wherever it has none of its own, and none of its modifiers (`scripting_best_practices.md` § "What a Civil War's Winner Inherits"; read from saves 2026-09-25). A nuclear power that loses a revolution therefore passes its whole arsenal and posture to the rebels. The entry is `can_revolution_inherit = no`, so the winner gets a fresh one that auto-activates within two weeks on the inherited arsenal. Its `immediate` keeps the stockpile and zeroes progress toward the next warhead, and its first weekly pulse restores `nuclear_power`, which the merge does not carry. Until then the winner has neither the entry nor the modifier. The rebels hold nothing during the war. No custody split or civil-war event exists yet, and the doctrine gate does not know the enemy is a rebel: Warfighting, or Flexible when losing, permits a strike on rebel-held home provinces.

## Nuclear Deterrence and Crisis Diplomacy (part of `je_nuclear_program`)

> Design and what shipped: `docs/systems/nuclear_crisis_design.md` (**read §0 first**). Panel: `docs/systems/journal_entry_systems.md` → Nuclear Deterrence Widget.

Posture and crises share the **Nuclear Weapons** entry with the programme (above); until 2026-09-25 they had their own, `je_nuclear_deterrence`. Everything here is gated on **holding** warheads (`nd_is_armed`), not on rank, so a demoted power keeps its posture, its upkeep and its accidents, and a paused or unfunded programme cannot shed them; the crisis half also runs for a non-nuclear party to a crisis. Every effect must therefore be a no-op for a country that is in the entry but neither armed nor in a crisis — a great power still building its first warhead. All variables carry the `nd_` prefix; nothing runs without `nuclear_weapons_enabled`.

**Files.** `je_nuclear_program.txt` (the entry and its pulses: programme first, then `nd_weekly_update` / `nd_monthly_update` / `nd_yearly_update`) · `nuclear_deterrence_effects.txt` (posture, capabilities, domestic stance, AI review, incidents, launch dispatch) · `nuclear_crisis_effects.txt` (crisis lifecycle, acts, settlements, outcomes, guarantees) · `nuclear_deterrence_triggers.txt` (doctrine gates, disputes, eligibility, AI judgement) · `nuclear_deterrence_values.txt` (every tuning constant at the top; costs, capability targets, danger, pressure, incident odds, display values) · `nuclear_deterrence_modifiers.txt` · `nuclear_crisis_actions.txt` (diplomatic actions) · `115_nuclear_guarantee.txt` (treaty article) · `nuclear_crisis_on_actions.txt` (`on_diplo_play_back_down`) · `events/nuclear_crisis_events.txt`, `events/nuclear_incident_events.txt` · the widget, its sguis and custom loc · `events/te_debug_deterrence_events.txt` (console harness, `event te_debug_deterrence.1`–`.5`).

**Posture.** Three independent axes — doctrine (`nd_doctrine` 1 no first use … 5 warfighting), readiness (`nd_readiness` 0–3 — 0 is Recessed, from which nothing launches — walking one step every two weeks toward `nd_readiness_target`) and launch authority (`nd_authority` 1–4 — 4 is Automatic Retaliation, which answers a first strike on us in full) — plus two investment steppers (`nd_safeguards`, `nd_hardening`, 0–3). Capabilities (`nd_survivability`, `nd_reliability`, `nd_strain`, `nd_credibility`) move monthly. The AI sets its posture in `nd_ai_review_posture` (every sixth month, and when a crisis opens via the hidden `nuclear_crisis.99`), not through scripted buttons.

**Managed modifiers.** `nd_doctrine_mod_*`, `nd_readiness_mod_*` and `nd_upkeep_cost` live on the entry (`je:je_nuclear_program`) and have one writer, `nd_apply_posture_modifiers`, which decides from tracking variables (`nd_*_mod_on`) because add/remove results are invisible inside the block that ran them. The entry's `immediate` zeroes the trackers and clears `nd_posture_on_merged_entry`; the first weekly pulse then runs `nd_rebuild_posture_modifiers`, which takes every member off, re-applies and sets the marker. That one effect covers both a fresh activation (without relying on `je:` resolving inside `immediate`) and a save made while the modifiers sat on the old `je_nuclear_deterrence`. A country armed while the entry is already active — the usual case, a programme's first warhead — is initialised by `nd_weekly_update` the same week. The upkeep multiplier is `root.var:nd_upkeep_weekly_cached` (the UN buttons' pattern), so **every posture effect runs with the country as ROOT** — posture effects for another country go through a country event.

**Launch gates.** `nd_doctrine_permits_strike = { ENEMY }` is the one doctrine gate, read by both strike actions' `possible` (with a custom tooltip, on top of the unchanged war-law gates), the crisis and incident branches that can end in a deliberate strike, and the AI. `nd_pledge_permits_strike` blocks a strike on a pledge partner. Every launch path also needs `nd_forces_assembled` (not Recessed). A strike on a country we cover — treaty beneficiary, or a direct subject under our **nuclear umbrella** (`nd_under_an_umbrella`, withdrawable with `nd_withdraw_umbrella_action`) — licenses our retaliation under every doctrine (`nd_was_struck_by`). All launches go through `nd_dispatch_strategic_strike` / `nd_dispatch_tactical_strike` and record themselves once with `nd_record_nuclear_use` (pledge breaches, crisis close, proliferation spur, guarantors). Outside a war, a launch branch becomes an intercepted order (`nd_intercepted_launch`), never a strike. `nd_war_law_permits_strategic_strike` / `nd_war_law_permits_tactical_strike` carry the Rules of War gate for the strike actions and the crisis strike options alike.

**Crises.** Opened by `nd_nuclear_warning_action` / `nd_nuclear_ultimatum_action`, or by the target of a recalled peacetime launch through `nuclear_incident.5` option c ("warn them privately"; no dispute test or cooldown); one per country; the record is on the issuer (`nd_crisis_*`), mirrored on the target. `nd_crisis_weekly_tick` (issuer's weekly pulse) revalidates, recomputes danger and the target's `nd_yield_pressure`, fires the deadline and pressure events and expires the crisis. Decision events carry a token (`nd_crisis_event_token`) and re-check it in every option through `nd_crisis_option`. The target's concession is enforced by dispute: `resolve_play_for` (play), −35 war support (war), a ten-year programme freeze, or a two-year readiness lock. `nd_crisis_refresh_figures` is the one writer of the crisis's numbers and stores every part of danger and pressure on both parties; follow-through (`nd_ft_reason`: backed, uncertain or a bluff) is one of the parts. The outcome notice (`nuclear_crisis.6`) applies each side's consequences from a pending record (`nd_crisis_pending_*`), so its tooltip shows them.

**Domestic stance.** `nd_refresh_domestic_stance` is the single site of `nd_posture_approval_*` on interest groups. Classes are by interest-group type (Armed Forces, Industrialists) and Rules of War stance (`nd_ig_class_*`, `nd_stance_*`), with the two fixed classes leaning by their leader's stance (`nd_ig_lean_*`); each group's terms and capped total are stored on the group (`nd_ig_*`, scored by `nd_ig_term_*_value`) and the band is set from that total. Every term but the Industrialists' business concerns is zero until a doctrine has been held six months. The At Home list prints the stored numbers (`nd_home_list_sgui`). Crisis outcomes pay hawks/doves one-off IG modifiers and adjust native lobby appeasement (`nd_lobby_react`); an IG in an anti-opponent lobby is paid through the lobby only.

**Incidents.** One roll per armed country per month (`nd_roll_incident`, two-stage so the inner chance is never fractional), family drawn in `nd_fire_incident`. The fallback family (`nuclear_incident.40`) is always eligible, so the draw is never empty.

**The No-First-Strike Pledge amendment is the law's copy of doctrine 1** (#430). `amendment_no_first_strike` (a rules-of-war amendment, offered by `extra_law_events.32` option a or sponsored in an enactment negotiation) used to be a second, unenforced pledge beside the doctrine. Now: while it is in force (`nd_nfu_amendment_in_force`: on an active law), `nd_weekly_update` holds an armed country's doctrine at 1 through `nd_set_doctrine_1` — whatever brought the amendment in, the law outranking tenure — and `nd_init_posture` seeds 1 for an arsenal built under it. The law made that move, not the government, so the binding puts `nd_doctrine_months` back as it was (tenure-satisfied if it was missing): the two-year lock and the six months before the interest groups judge a doctrine run on from the government's own last change, and a country that repeals the amendment is not then held at No First Use for two years. A human is told through the feed message `nd_doctrine_bound_by_law`. Leaving No First Use while it is in force or attached to the law being enacted (`nd_nfu_amendment_on_file`) is the usual repudiation plus `nd_strike_nfu_amendment`, which removes it from both laws (`every_scope_amendment` + `remove_amendment`, the vanilla shape; vanilla never removes one from a law still being enacted, so a repudiation made then also leaves `nd_nfu_amendment_repudiated`, and if the law passes with the amendment after all, the weekly update strikes it from the passed law instead of binding — the marker is cleared once the amendment is off file) — so the panel and the AI review need no new gate, and the binding never pulls a country back to a doctrine it has repudiated. The AI review leaves doctrine alone while the amendment is on file (the AI never repeals it). Repealing it through the law panel ends the codification without a repudiation; the doctrine stays where it is. The amendment has no `on_activate` / `on_deactivate`: its scope there is unverified, and a removal hook would loop.

**Retaliation from the strike-response events** (#430). `nuclear_weapon_events.1` (options b/c) and `.11` (b/c) strike back through `nuclear_response_strike` / `nuclear_response_response_strike` — not the dispatch path, whose `nuclear_first_strike` books a first strike's infamy, dossier and ICC entries — but they now carry the actions' gates (`nd_retaliation_permitted`: no disarmament, `nd_doctrine_permits_strike`, `nd_pledge_permits_strike`; greyed rather than hidden while the arsenal is there), record the salvo once with `nd_record_nuclear_use`, and weigh the AI's choice with `nd_ai_nuclear_use_justified` (`factor = 0`). Both events are triggered in the struck *state's* scope, so every gate names the retaliator by saved scope — `scope:target_country` in `.1`, `scope:attacking_country` in `.11`.

**Incident launches say so** (#430). `nd_launch_or_intercept` takes `KIND = warning | commander` and saves `scope:nd_incident_launch_<KIND>` on the launcher before dispatching, so the strike events it sets off on the attacker — `nuclear_weapon_events.2`, `.6` and `.17` — replace "our retribution has been swift" with the unconfirmed warning or the cut-off commander — the title, desc, flavor and the options that claim the choice (`.2.a`, `.6.a`, `.17.b`, each split into two mutually exclusive options with identical effects) all read one trigger, `nd_strike_from_incident` / `nd_strike_from_incident_of = { KIND }`. A saved scope, not a variable: it lives exactly as long as the event chain, so it cannot outlast the popups or reach a deliberate launch in a later chain. Within its own chain it rides on through the victim's retaliation (`.1`) to the launcher's answer (`.11`), so `.11`'s options b/c save `scope:nd_deliberate_response` and `nd_strike_from_incident` excludes it — the counter-strike's `.2` keeps the ordinary text.

**The proliferation alert goes through the systems** (#430). `nuclear_weapon_events.18` option a is the crisis system's public ultimatum (`nd_crisis_open PUBLIC = yes`) whenever `nd_can_issue_proliferation_ultimatum` holds (everything `nd_nuclear_ultimatum_action` asks, plus a proliferation dispute), and the AI takes it only when `nd_ai_would_issue_ultimatum` agrees; otherwise a nuclear power gets the old one-off warning as `opt_a_sabre`, "Denounce their programme and rattle the sabre". Option d tables the Non-Proliferation Treaty through the UN's proposer event, `un_events.14`, when `nuclear_program_can_table_npt` holds (`nuke_triggers.txt`: a member, the topic open on the docket, no vote in session, not already offered an item), and lobbies bilaterally (the old −1 progress) otherwise. The offer is made the docket's way — the offer count restarts at 1 and the chooser carries `un_dkt_offered` for 60 days — so `un_events.14`'s pass and refuse options forward the item to other members as for a docket item, never straight back; it fires at once rather than after `un_docket_send_offer`'s day, so the floor is reserved before another country answering the same alert can try. `nuclear_npt_lobbied` (30 days) zeroes an AI's pass and refuse weights in `un_events.14`: an AI that lobbied tables the treaty.

**Cross-system edits.** The strike actions (`nuke.txt`) are doctrine-gated and route the tactical body through `nd_tactical_strike_resolve`; the leaderboard (`update_nuclear_powers_ranking`) ranks and shows public estimates (`nd_display_public_estimate`); rival-stockpile comparisons in the programme's AI weights and in `nuclear_weapon_events.txt` read the rival's `nd_public_estimate`; the nuclear-shadow war-support line in `zz_te_war_support_injections.txt` is lifted by an armed guarantor.

## Banking Cycle (`je_banking_cycle`)

> See also: `docs/systems/journal_entry_systems.md` for full JE system documentation.

- Uses 4 `scripted_progress_bar` instances and 68 scripted buttons (34 `cb_*` — 17 market tools, each an enable/disable pair — 18 `ce_*`, 16 `cw_*`). `test_banking_tool_roster.py` checks every `cb_*` tool is registered everywhere it has to be (see **Policy tools added 2026-09-23** below).
- Requires `stock_exchange` tech.
- All banking buttons already have detailed AI weights. Each enable button's `ai_chance` is *core* terms (the cycle state the tool answers) plus *flavour* / *resource* terms (law, an independent bank, free points), and the latter only count while the matching `banking_ai_core_cb_*` trigger (`banking_policy_triggers.txt`) is true — as unconditional adds they scored a tool 5–25 in a stable phase and the AI parked prudential tools for 40% of the century. Keep a core term and its gate trigger in step.
- Events: `banking_cycle_events.txt` — 77 events covering crises from railway bubbles to derivatives, with command-economy and cooperative-ownership variants.
- **Events that duplicate a dashboard tool, or narrate monetary state, defer to it (#428).** Their draws in `banking_cycle_random_event_effect` ask triggers at the foot of `banking_policy_triggers.txt`, following events 15 and 58 (PR #416). `.31` *Bank Holiday* is drawn only while the dashboard's Bank Holiday could be pressed (`banking_can_enact_cb_bank_holiday` — the button's `possible` whole, points included, because the tool's own modifier holds them), and its option A enacts that tool. `.39` *Quantitative Easing* never fires beside running open-market operations; under the full system it needs OMO's whole gate (a dial at the rate's floor) and option A enacts OMO — a standing policy, with its activation cost, bubble push and inflation pressure, that runs until it is switched off — and under the simplified rule it keeps its bespoke, decaying stimulus. `.34` *Deposit Insurance* is not drawn while a guarantee is in force (`banking_deposit_guarantee_in_force`), and says "after recent banking failures" only after a crash in the last five years (`banking_recent_crash`, a timed variable set where each crash is decided). `.16` *Central Bank Independence* (market branch only) needs a delegated or independent dial under the full system, a national bank under the simplified rule; its option B moves the bank to the Growth mandate through `te_mon_effect_set_mandate`. `.10` / `.110` / `.160` need `scaled_debt > 0.25` and no default, and `.10`'s option C is a *threatened* default — no effect enters the engine's default state. `.55` names a real planned-economy ally (`banking_is_fraternal_aid_donor`). **Wave marks:** `banking_crisis_wave_hit` is every country a contagion wave reached, from the moment it is reached (the cascade dedupe, and the UN docket's loan test through `banking_crisis_wave_reached`); `banking_crisis_wave_crashed` and `banking_crisis_wave_scared` record how its contagion roll came out, seven days later. The Great Depression event reads those two, so a country reached but not yet decided gets the general text and the bystander option.
- **Tuned by simulation.** `scripts/analysis/banking_cycle_sim.py` is a Monte-Carlo port of the monthly loop (reads every number from these files at import); `docs/audits/banking_cycle_simulation.md` is the study behind the 2026-09-22 retune — phase bubble adds ~×3, downturn/stagnation recovery ×3 plus a +0.5 climb, crash severity seeded from `banking_crash_severity_scale_value` (0.55) × bubble, a crash branch below cycle 40, the tools' standing momentum ×0.3 and negative bubble ×0.2 (then, the same day, §10's boom-rescue package: the three leaning tools — buffer, margin, moral suasion — back to ×0.6, frenzy's bubble add 20 → 8, the bubble-inertia curve flattened above 50 to reach +0.45 rather than +1.25 at bubble 100, and +0.2 bubble a month on fiat / digital; a maxed player now pulls back about a quarter to a third of booms and a few percent of frenzies — `--rescue`, `--rescue-entry 88`), the fiscal channel annualised and clamped, the stance clamp's loose side −4 → −2, the growth bias −1.0 → −0.25, players delegated by default, and the AI gates above. Re-run it before retuning any of those; the targets it was tuned to are in the study's §2.
- **The delegated bank (2026-09-25, study §12).** Three changes answer the delegated bank's overshoot: `te_mon_cycle_lean` reads the phase of `te_mon_cycle_outlook` (value + 4.69 × momentum) rather than today's phase; a mandate-run bank cuts 3× as fast while the cycle is below 40 (`te_mon_drift_step_down`, `te_mon_emergency_cuts`; hikes and the manual dial are unchanged); and the growth mandate reacts to inflation above 4% at 1.0, not 0.5. The simulator never saw the overshoot because it had no standing inflation pressure: sweep `--wage-pressure` (labour laws grant +0.2 to +1.4pp) whenever you tune a mandate. Standing pressure still costs price stability a high rate and a near-stagnant cycle (§12 F15); that is a balance question, not a bank-logic one. For independent banks, §13 answers it: `law_central_bank_independence`'s per-National-Bank-level bonus is `country_inflation_anchoring_add` (+0.1pp a level), which `te_mon_pressure_anchoring` subtracts from the net positive wage + price pressure, never past zero (a flat negative pressure made the bank run loose and doubled crashes). It replaced −5% crash chance and −2% random momentum a level. The simulator's `--bank-level N` ports the institution; `--tune pre_anchoring` restores the old bonus.
- Player-facing UI is the **policy dashboard** widget (below); the scripted buttons stay on the JE as the AI's path and as a fallback.
- **Revolutions (2026-09-26, #465).** The entry is `can_revolution_inherit` and cannot deactivate, so its `immediate` runs on the first activation and again on the copy a revolution's winner inherits. That copy arrives after the loser's variables are merged in, with **no modifiers** (`scripting_best_practices.md` § "What a Civil War's Winner Inherits"). So `immediate` seeds `finance_cycle_value` / `finance_cycle_momentum` / `bubble_pressure` (50 / 0 / 0) only when they are absent, and the winner carries on the loser's cycle; before this a win reset a panic to a stable 50 (civil-war audit F6). It zeroes `te_mon_stance_band_applied` unguarded, so next month's swap puts the stance band back (F7), and draws the bars from the variables through `banking_cycle_update_progress_bars`. Every other modifier on the entry is either rebuilt statelessly each month (phase and bubble-inertia modifiers, `financial_cycle_government_fiscal_policy_effect`, `planning_treasury_pool_balance`) or a tool the player switched on, which the winner loses (F8, open). A one-time save migration in `banking_cycle_apply_stance_band` (marker `banking_stance_band_healed`, remove after one release) heals saves in which the band was already lost.

### Policy Dashboard
`gui/journal_entry_widgets/banking_dashboard_widget.gui` renders two custom widgets into the vanilla journal-entry panel (`custom_widget_container_1` and `_2`): a **Current Conditions** readout and an **Active Policies / Available Interventions** list.

**Single source of truth.** Every button's `possible` and `effect` body lives in a named helper — `banking_possible_<button>` in `common/scripted_triggers/banking_policy_triggers.txt`, `banking_effect_<button>` in `common/scripted_effects/banking_policy_effects.txt` — and both the `scripted_button` and the dashboard's scripted GUI call it. `visible`/`possible` on both halves of every enable/disable pair read the `banking_tool_*_active` family in `market_triggers.txt`. **If you add or retune a policy, edit the helper, never the button or the scripted GUI body.**

**Do not move AI logic out of the buttons.** The AI chooses banking policy solely through the `ai_chance` blocks on the JE's `scripted_button` entries (see `common/scripted_buttons/scripted_buttons.md` in vanilla — `ai_chance` is evaluated in country scope). Deleting a `scripted_button = …` line from `je_banking.txt`, or hiding it behind `is_ai`, silently removes that policy from the AI's repertoire. Every dashboard scripted GUI therefore carries `ai_is_valid = { always = no }`.

**One documented exception (monetary policy, spec §6).** The policy-rate dial is *not* a button, so there is no `ai_chance` to bypass: for `is_player = no` countries `te_monetary_update_target` picks the mandate by rule (gold standard → peg defence; at war or `scaled_debt >= 0.5` → growth; otherwise price stability) and runs the same formula the delegated player gets. Precedent: `common/journal_entries/je_covert_warfare.txt`. The rule above still protects every discrete toggle button, and all of them stay. The AI branch carries no gate the player branch lacks (the orphan-gate trap in `scripting_best_practices.md` § "Scripted Button Gating").

**Asking script a yes/no question from `.gui`.** `common/scripted_guis/banking_dashboard_scripted_gui.txt` holds read-only handlers (`banking_dash_system_*`, `banking_dash_phase_*`, `banking_dash_momentum_*`, `banking_dash_bubble_risk_high`, `banking_dash_any_policy_active`) whose only job is to expose an existing scripted trigger to the widget as `[GetScriptedGui('x').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]`. This keeps thresholds (phase bands, economic-system gates) in script instead of duplicating them as numeric comparisons in `.gui`.

**No hand-typed numbers.** Row tooltips quote the button's own `name`/`desc` loc plus `[GetStaticModifier('<mod>').GetDesc]`; the action button's tooltip is `Concatenate( ScriptedGui.IsValidTooltip(…), ScriptedGui.ExecuteTooltip(…) )`, so cost and effect text is generated by the engine from the actual script. Conditions tooltips read the `banking_display_*` script values in `extra_script_values.txt`, which are thin wrappers over the same `modifier:country_*_monthly_add` reads `banking_cycle_advance_variables` uses.

**Layout.** One `banking_dash_policy_row` type, instantiated per policy with blockoverrides (label / cost / enable action / disable action). Category sections collapse through `GetVariableSystem.Toggle('banking_dash_collapsed_<cat>')` — GUI-only state, never written to the save. Rows are fixed-width columns inside `widget` wrappers with eliding text, no absolute positioning.

**Where the tools sit (2026-09-23).** The *Monetary Policy* category is the dial block alone. Open-market operations are the dial's own beyond-the-floor tool, so their row sits directly under *Rate Target*, drawn only under fiat or digital currency (`banking_mon_shows_omo`, reading the declarative `country_can_create_unbacked_money_bool`) and greyed with a reason for everything else that blocks them; the row stays in place while the tool is active, showing Disable. Under `banking_system_simplified`, which has no dial block, OMO keeps a plain fallback row under the header (`banking_dash_omo_fallback_shown`) and the category is drawn for a market economy only (`banking_dash_monetary_shown`). Moral suasion leads *Prudential Regulation*: it leans on a boom, like the buffer and margin requirements (the simulator's `LEANING_TOOLS`). Only the `.gui` rows moved — both scripted buttons and their `ai_chance` are untouched.

### Policy tools added 2026-09-23
Seven tools, designed in `docs/superpowers/specs/2026-09-23-banking-tools-expansion-design.md` and sized with the simulator (`docs/audits/banking_cycle_simulation.md` §11). All are ordinary `cb_*` pairs — helper, button, handler pair, rows, loc, simulator entry — so everything in **Policy Dashboard** above applies.

- **Directed credit sectors** — `cb_directed_credit_heavy_industry`, `_agriculture`, `_armaments`, `_electrification` (Electrification & High Tech, gated on `rural_electrification` by `country_can_use_directed_credit_electrification_bool`). Each is Infrastructure's shape: +10% construction for its building groups, an interest-group line, a little momentum and bubble, 3 points, the same activation cost, and Infrastructure's `country_banking_lock_directed_credit_bool`. `bg_high_tech` sits under `bg_heavy_industry`, so Heavy Industry covers high-tech buildings too.
- **One sector at a time.** `banking_directed_credit_slots_free` (`extra_script_values.txt`) = 1 + `country_directed_credit_sectors_add` − sectors running; every sector's `possible`, Infrastructure's included, requires it above 0 (`banking_dc_sector_cap_tt`). Directed Credit & Development Banks grants `+1`. Step 6b of the monthly pulse sheds the excess after a law change. The sector count is read once into a local variable there, because a `remove_modifier` is invisible to the modifier reads it is built from until the block ends.
- **The AI picks a sector by government, not more often.** All five sectors' enable buttons score `banking_dc_ai_weight` (Infrastructure's pre-expansion `ai_chance`), split among the new sectors that have an affinity (`banking_dc_affinity_*`: Industrialists / Landowners or Rural Folk / Armed Forces or at war / Intelligentsia in government) and could be started (`banking_dc_ai_candidate_*`); with none, Infrastructure takes it all. Total directed-credit weight is therefore unchanged whoever governs — F11 of the simulation study found directed credit to be the AI's riskiest tool. Disable sides copy Infrastructure's F11 weights.
- **Reserve Requirements** (`cb_reserve_requirements`, Prudential) — a leaning tool with no tech: bubble and momentum down, capitalists' pool efficiency −5%, and `country_inflation_pressure_add` −0.5pp (read by the §9.1 pressure sum, so it shows in the dashboard's Price Pressure breakdown). AI: the buffer's weights, +15 while the buffer is still locked, and ×0 while the buffer could be bought instead — the lean before the buffer's tech and a second lean beside it, never a weaker stand-in (simulation study §11).
- **Bank Holiday** (`cb_bank_holiday`, Crisis) — panic or downturn only, no tech. Adds `banking_bank_holiday` to the journal entry **timed, `days = 90`** — the first timed tool modifier in the system; `banking_tool_bank_holiday_active` is `has_modifier`, so the row and the Active Policies entry disappear on expiry, and no "withdrawn" history marker is written then (only on an early Disable). Halves a negative momentum once, and sets the five-year cooldown variable `banking_bank_holiday_cooldown` (`days = 1825`) on the country. Its crash-chance line shields against contagion too, because `banking_contagion_crash_check` multiplies by the same `banking_crash_chance_multiplier_value`.
- **Bail-in Regime** (`cb_bail_in_regime`, Crisis) — `globalization`, 3 points, no treasury cost; half Asset Relief's cycle-value push, bubble down, risk premium +0.1pp, upper-strata radicals on enabling. **Mutually exclusive with Asset Relief** — each `possible` requires the other inactive. No law lock: Unregulated Banking cannot afford 3 points.

### History Charts
`gui/journal_entry_widgets/banking_history_widget.gui` adds a third custom widget (`custom_widget_container_2` - the policy list took `_3`): a collapsed-by-default **History** section with one column chart each for cycle value, momentum and bubble pressure — plus, since monetary phase 1, policy rate and rate paid on debt, since phase 2 headline inflation and since phase 4 the exchange-rate index (see **Monetary Policy (phase 1)**, **(phase 2)** and **(phase 4)**), **seven in total** — with 1 / 5 / 20-year ranges, a key for the two marker pips, and dated policy and crash markers. The policy-rate chart is a `visible`-toggled **pair** rather than one instance: an unsigned 0–12 axis for everyone, and a −3–12 axis with a drawn 0% line for a digital currency, picked by the `banking_mon_is_digital` scripted GUI. Only one is ever drawn (so six charts, seven instances). The inflation chart is a single instance on a −4–12 axis with its own drawn 0% line — every country can deflate, so there is nothing to branch on. The store, the chart type and the marker tooltips are shared infrastructure — see **History Store and Charts** below before touching any of it.

### Monthly Pulse Architecture
The `on_monthly_pulse` calls these scripted effects in order (all in `common/scripted_effects/banking_cycle_effects.txt` unless noted):
0. **Save migration one-shot** (inline in `je_banking.txt`) — strips a leftover `banking_policy_rate_hike` modifier from `je:je_banking_cycle`. Guarded on `has_modifier`, so it is a no-op on every save but the first migrating month. Removal checklist: **Monetary Policy (phase 1)** below.
1. **`banking_cycle_update_fiscal_policy`** — re-applies fiscal policy modifier based on deficit/surplus relative to GDP: `financial_cycle_government_fiscal_policy_effect_size` is 0.1 cycle points a month per 1% of GDP of deficit (so a 10%-of-GDP deficit reaches +1), annualised through `te_mon_deficit_annualise_factor` (weekly flows, yearly `gdp`) and clamped ±1. Until 2026-09-22 it skipped the annualisation and was 1/52 of its comment's claim; the annualised version first shipped at 0.25 (+1 at 4%) and was cut to 0.1 (`banking_cycle_simulation.md` §6 follow-up).
2. **`banking_cycle_advance_variables`** — momentum decay, modifier-driven changes, the monetary-stance push (`te_mon_stance_momentum_add` / `te_mon_stance_bubble_add`, −0.125 and −0.75 per pp of tight stance gap, gap clamped −2…+4 by `te_mon_stance_gap_clamp_loose` / `_tight` — never rendered as a number, per `monetary_policy_design.md` §8), investment pool, random mean-reversion nudge (scaled by `banking_random_nudge_down/up_value`), apply momentum to value, clamp all variables.
3. **`banking_cycle_check_and_execute_crash`** — asymmetric crash probability check based on bubble pressure × phase (a branch per phase band, including one below cycle 40 — without it the weight fell through as raw bubble), scaled by `banking_crash_chance_multiplier_value`; severity is `banking_crash_severity_scale_value` (0.55) × bubble × a 0.5–2.0 roll, so the median crash lands in the 20–40 tier rather than resetting to panic. If crash triggers, fires origin event (.6) and spreads contagion via `banking_cycle_spread_contagion`.
3b. **`te_history_record_banking_samples`** (`common/scripted_effects/te_history_banking_effects.txt`) — writes the month's cycle value, momentum and bubble pressure into the history store (**History Store and Charts**, below). Deliberately placed after the crash check so a crash month's bar shows the post-crash readings beside its crash marker.
4. **`banking_cycle_apply_phase_modifiers`** — removes old phase + bubble-inertia modifiers, applies current ones based on cycle value and economic law type.
4b. **`banking_cycle_apply_stance_band`** — swaps the `banking_stance_band_1..5` JE modifier (the investment-pool side of the monetary stance) when the displayed band changes. Decides from `te_mon_stance_band` vs a stored `te_mon_stance_band_applied`, never from `has_modifier`; band 3 is an empty modifier that is still applied, so the modifier list always names the stance. A stored 0 means "none recorded": the swap then removes all five before adding. `immediate` sets 0 on every activation, including a revolution's inherited copy, which has no modifiers. See **Monetary Policy (phase 1)** below, and `docs/systems/monetary_policy_design.md` §8.
5. **`banking_cycle_update_progress_bars`** — updates the 4 JE progress bars (uses `scope:journal_entry`; the policy-stance bar only once the monetary system's `te_mon_stance_bar_pos` exists). Also called from the entry's `immediate`.
6. **`banking_cycle_cleanup_capital_controls`** — removes capital controls modifier if law/war conditions no longer apply.
6b. **`banking_directed_credit_enforce_cap`** — lifts directed-credit sectors, newest first, while more are running than `banking_directed_credit_slots_free` allows (a law change away from Directed Credit & Development Banks). See **Policy tools added 2026-09-23**.
7. **`banking_cycle_update_ce_pool_balance`** — under `law_command_economy`, recalibrates the `planning_treasury_pool_balance` modifier on the JE so investment-pool net monthly income targets zero (state treasury funds all investment directly). Also called from `ce_invest_pool_inject` / `ce_invest_pool_withdraw` button effects.

### Monetary Policy (phase 1)
The policy-rate dial and the risk-premium stack that replaced the old *Raise Policy Rate* toggle. `docs/systems/monetary_policy_design.md` stays the design authority (phases 4 and 5 — FX, international arrangements — are implemented too: **(phase 4)** and **(phase 5)** below, §0.7 and §0.8) and carries **"Phase 1 as shipped"** (§0.1–§0.3), **"Phase 2 as shipped"** (§0.4) and **"Phase 3 as shipped"** (§0.5), each with its deviations list and its half of the one in-game verification checklist — both phases are implemented but **not yet verified in a running game**. Read this subsection first, then **Monetary Policy (phase 2)** below, which adds to it rather than replacing it.

**Files.**

| File | Holds |
|---|---|
| `common/script_values/te_monetary_script_values.txt` | the **variable contract** (file header), `te_mon_era_base`, the regime range (`te_mon_target_min` / `_max`) and the OMO gate's `te_mon_floor_threshold`, the drift step (`te_mon_drift_speed_factor` / `te_mon_drift_step` / `_threshold` / `_threshold_neg`), `te_mon_access_premium`, `te_mon_standing_floor`, `te_mon_scaled_debt_premium`, `te_mon_cycle_lean`, `te_mon_forecast_error_bound` / `_neg`, and the three stance-channel values |
| `common/scripted_effects/te_monetary_effects.txt` | `te_monetary_monthly_update` and its steps, the yearly GDP-growth snapshot, and the five `te_mon_effect_*` player controls |
| `common/scripted_triggers/te_monetary_triggers.txt` | `te_mon_has_dial`, `te_mon_has_narrow_dial`, `te_mon_is_cbi` / `_is_command` / `_is_state_banking`, `banking_stance_is_tight` / `_loose`, `te_mon_policy_rate_at_floor`, plus the stepper and display gates |
| `common/on_actions/te_monetary_on_actions.txt` | every hook the update is reached from (see below) |
| `common/scripted_effects/te_monetary_civil_war_effects.txt` | `te_monetary_inherit_central_bank` — what a revolution's winner takes over from the loser's central bank (see **Civil wars** below) |
| `common/scripted_guis/te_monetary_sguis.txt` | `banking_mon_control_sgui` (the one interactive handler, ops 0–8 — 7 and 8 are phase 2's monetisation stepper) + six scope-free display handlers |
| `common/customizable_localization/banking_dash_custom_loc.txt` | `te_mon_stance_band_name`, `te_mon_stance_momentum_effect` / `te_mon_stance_bubble_effect` (what the band is worth), `te_mon_delegation_state`, `te_mon_mandate_name`, `te_mon_no_dial_reason` |
| `common/country_ranks/te_monetary_rank_injections.txt`, `common/laws/te_monetary_law_injections.txt`, `common/technology/technologies/te_monetary_tech_injections.txt` | the cancel-INJECTs (eight ranks, `law_laissez_faire`, five finance techs) |
| `common/static_modifiers/extra_modifiers.txt` | `te_monetary_rate_paid`, `banking_stance_band_1..5`, and the `country_loan_interest_rate_add = -0.2` line in `INJECT:base_values` that cancels vanilla's flat base |
| `common/modifier_type_definitions/banking_cycle_modifier_types.txt` | `country_credit_standing_add`, `country_risk_premium_add`, the four **regime-rule** types below, and the one permitted `REPLACE:` — vanilla's `country_loan_interest_rate_add` *type definition* at `decimals = 1` |
| `gui/journal_entry_widgets/banking_dashboard_widget.gui`, `banking_history_widget.gui` | the dial block and the two new charts (the policy-rate one is a `visible`-toggled pair) |
| `events/te_monetary_events.txt` | `te_monetary_internal.1` — a hidden country event that exists only to give the update a country ROOT (see **Engine write path**) |
| `events/te_debug_monetary_events.txt` | console-only `te_debug_monetary.1`–`.7` — the single place hidden state is printed (and, in `.7`'s seed, written), deliberately unreachable from script. `.1` read-out + one-month stepper, `.2`–`.4` the solved interest-multiplier bench, `.5`–`.7` the §19 row 2 harness (pin a manual fiat target, fast-forward 12/60 pulses, set up §10's war case); the file header carries the console sequences and the numbers to expect |

**The variable contract lives in the header of `common/script_values/te_monetary_script_values.txt`** — every `te_mon*` / `te_policy_rate*` / `te_premium_*` / `te_neutral_*` name, its range, which four are hidden, and the rules that bind them (initialise behind `has_variable`; **never** `remove_variable`; no new monetary variable in `je_banking.txt`'s `immediate`, which runs again on the copy a revolution's winner inherits). Read and edit it there; don't restate it.

**The rate stack.** `rate_paid_pts = clamp( policy_rate + structural + cyclical , 0.5 , 60 )`, everything in percentage points (3.5 = 3.5%). The policy rate is the dial's target drifted toward at `te_mon_drift_step` a month — 1/3 pp at the baseline, 2/3 under digital currency; a country with no national bank has no dial and gets `reference_rate + 1` instead. Commodity money is the in-between case (design §0.6, 2026-09-21): **with** a national bank it holds a dial confined to a lopsided band, `centre − 1` to `centre + 3` — five settings, `te_mon_has_narrow_dial`; cheap money is what metal forbids, dear money was always the panic tool — and **without** one it is bankless like any other. The reference rate is `te_mon_era_base` — a **world** quantity, 3.0 / 2.5 / 2.0 by era, evaluated once a month into `global_var:te_mon_era_base_world`, read per country from there, and shown to the player as the dashboard's read-only **World Reference Rate** row.

**Regime rules are declarative modifiers, not law checks in script.** Four `script_only` types in `banking_cycle_modifier_types.txt` carry the rules that used to be `has_law_or_variant` branches inside `te_monetary_effects.txt` and sentences of localization restating them. Each is granted on the law that imposes it, so the law's own tooltip states it and the engine renders the breakdown; each is read by exactly one named script value, and nothing else reads `modifier:` on them.

| Type | Granted by | Read by | Effect |
|---|---|---|---|
| `country_policy_rate_drift_speed_mult` | `law_digital_currency` `+1.0` | `te_mon_drift_speed_factor` → `te_mon_drift_step` | how fast the rate closes on its target; +100% = twice the baseline third of a point a month |
| `country_policy_rate_floor_add` | `law_digital_currency` `-0.03` | `te_mon_target_min` (and `te_mon_floor_threshold` through it) | the lowest rate the regime allows, as a delta from zero |
| `country_credit_standing_floor_add` | `law_central_bank_independence` `-0.0025` | `te_mon_standing_floor` | the structural-premium floor, as a delta from 0.5pp |
| `country_bank_forecast_error_add` | `law_central_bank_independence` `-0.01` | `te_mon_forecast_error_bound` (+ `_neg`) | the bound on `te_neutral_error`, as a delta from ±1.5pp |

The **gold band is gone** (phase 3): reference rate ±2 was a phase-1 *interim* rule standing in for §12's gold flows, and it went when the flows arrived — gold's range is now §5.1's 0–15, what constrains the dial is the reserves, and the one scripted floor left in `te_mon_target_min` is the twelve-month *Defend* clamp (world rate + 4), an event outcome with a clock on it rather than a property of any law. The **regime ceiling** (25, or 15 while `te_mon_is_on_gold`) stays scripted, as does the second world-relative band: commodity money with a bank gets `centre − te_mon_commodity_band_margin_down` (1) to `centre + te_mon_commodity_band_margin_up` (3), floored at 0. That band is the whole of the regime's **rate** discipline — there is still no vault, no flow variable and no convertibility crisis behind it (§0.6 R5) — but since 2026-09-21 it is **not** the whole of its discipline: `te_mon_pressure_commodity_specie` (§0.6 R7, issue #351) charges −2pp of §9.1 inflation pressure per pp of core inflation above the world's beyond the first, clamped at −6, off phase 4's `te_mon_fx_term_inflation`. A rate bound says nothing about the **quantity** of money, and the regime pull only halves a standing pressure sum rather than anchoring the price level, so a commodity country could sit at 4% core with its dial pinned at this ceiling. **The band's `+3` "panic brake" is nominal and the stance gap is real** (issue #352): at 6% headline every setting on the dial reads loose, which is left alone deliberately — a coin economy in an inflation is meant to be nearly powerless, and R7 is what keeps it out of one. `centre` is `var:te_mon_commodity_centre`, the world rate as a whole point, kept by step 0 for every country and re-rounded only when the world rate is 0.75 away (`te_mon_commodity_centre_is_stale`) — so the band needs no epsilon, is always exactly five settings wide, and does not flap when the world rate hovers at x.5. The range is printed live in the Rate Target tooltip from `te_mon_target_min` / `_max`, which remain the single source shared by the monthly clamp and the stepper's `is_valid`.

`country_bank_forecast_error_add` is the one of the four that touches hidden state, and it is safe: §8's rule bars printing `te_neutral_error`, not the *width* of the band it walks inside.

**Two premium tiers.** *Structural* (`country_credit_standing_add`) is what the country **is** — rank, capital-market access, laissez-faire, gold-standard and CBI credibility, state-owned banking's `+0.5pp`, the national-bank institution, the mod's finance techs — floored at `te_mon_standing_floor`, 0.5pp (0.25pp under central bank independence), so standing earned past the floor buys nothing by design. *Cyclical* (`country_risk_premium_add`) is what is **happening** — cycle phase, crash interventions, banking-event outcomes, `declared_bankruptcy`, the debt-load term — added *after* the floor, so it always bites. Both are read back in country scope as `100 × modifier:X`; both are `script_only` and neither is granted from anywhere the monthly update does not read.

**Engine write path.** The update's last step removes and re-adds **one** modifier, `te_monetary_rate_paid` (`country_loan_interest_rate_add = 0.01`, applied with `multiplier = var:te_rate_paid_applied`). Vanilla's flat 20% base is not cancelled by a modifier of the mod's own any more: it is cancelled on the entity that grants it, by `country_loan_interest_rate_add = -0.2` in the mod's `INJECT:base_values` block — the same treatment the ranks and the five finance techs get — so the player reads one interest line instead of a +20% base with a −20% modifier beside it. (That flat-key INJECT is `monetary_policy_design.md` §17 check 2, **confirmed to sum** in game on 2026-09-20 — no "Base Value" line on the day-one interest tooltip; §0.3 item 1b.) A country that has not pulsed therefore borrows at **0%**, which the owner has confirmed in game is harmless — a non-positive total simply displays 0.0%. `te_rate_paid_applied` **equals** `te_rate_paid_pts`; it is a separate variable only so the step can tell whether the rate has moved enough to be worth re-applying. (It used to carry a script compensation for vanilla's five finance techs; those are now cancelled engine-side by `te_monetary_tech_injections.txt`, so no vanilla interest source survives for the write to net against. A save made before that change carries up to 2.0pp per researched finance tech too much, and the first pulse after loading corrects the whole gap at once.) A month whose change is under 0.05 skips the re-apply.

**`multiplier =` is resolved against ROOT — the entry points are not interchangeable.** `add_modifier`'s multiplier slot reads ROOT, not the scope the effect runs in, and the engine logs nothing when ROOT is wrong. `on_game_started` has **no** root scope and the six release/uprising hooks leave the **parent** in ROOT, so calling the update from either directly wrote a multiplier of 1.0 (every country in the world paying 1% for a whole campaign) or the parent's rate onto a released tag. Both families now dispatch `te_monetary_internal.1`, a hidden country event whose ROOT is the country it fires on; it runs the **whole** update, so each entry point still causes exactly one call and nothing is double-pulsed. `on_monthly_pulse_country` and `on_country_formed` declare "Expected Scope: country" in the engine's own `docs/on_actions.log` and call the effect directly. Step 9 sets `te_rate_paid_rooted` only when `root ?= this` confirms the write had a country ROOT, and re-applies when the marker is absent — so a country carrying a root-less write, including one loaded from an older save, is repaired on its first monthly pulse. It is the one monetary variable deliberately **not** initialised: its absence is the signal. Write-up: `scripting_best_practices.md` § "`add_modifier { multiplier = var:X }` Resolves Against ROOT".

**Single owner, and it is not idempotent.** `te_monetary_monthly_update` is the only writer of `te_policy_rate`, `te_rate_paid_pts` and the interest modifier (one exception: the end of a revolution, **Civil wars** below). It advances the drift by a third of a point and draws two random walks **per call**, so calling it twice in a month drifts twice as fast and ages the hidden state twice as quickly. Call it only from `common/on_actions/te_monetary_on_actions.txt` — `on_monthly_pulse_country`, `on_game_started`, `on_country_released_as_{independent,own_subject,overlord_subject,company_subject}`, `on_revolution_start`, `on_secession_start`, `on_country_formed` (plus `on_monthly_pulse` for the world reference rate and `on_yearly_pulse_country` for the growth term) — **never** from an event, a scripted button, a scripted GUI or a journal entry's pulse. Anything that needs the rate to reflect a change it just made writes the input and lets the next pulse pick it up. On the six release/uprising hooks ROOT is the *parent* (vanilla `00_code_on_actions.txt:3634`, `:5143`, `:5510`; the engine declares all six "Expected Scope: none") and only `scope:target`, the new tag, is updated — by dispatching `te_monetary_internal.1` to it, not by calling the effect inside the scope block, because the multiplier would otherwise read the parent's variable. The parent already pulses monthly, and a second call in the same month would drift it an extra third of a point and re-draw both walks. `on_country_formed` is the exception where ROOT *is* the new tag, so it calls directly.

**Civil wars: the winner continues the nation** (owner ruling 2026-09-26, #462). The rebels get a full monetary state at `on_revolution_start` so they can price their loans, and a revolution's winner keeps its *own* value of every variable it already held (`scripting_best_practices.md` § "What a Civil War's Winner Inherits") — so a rebel win used to replace the nation's central bank with the rebels' fresh one (the German save: vault 111.5M → 2.8M, 54.6 % hyperinflation → 5.1 %, the player's mandate replaced). `on_civil_war_won` now runs `te_monetary_on_civil_war_won`, which does **not** call the update: when the shared parent pointer `te_cw_parent` (set on the rebels at `on_revolution_start`, contract at the foot of `te_monetary_on_actions.txt`) names a different object that is no longer alive, `te_monetary_inherit_central_bank` copies the loser's bank onto the winner — the vaults and hot money **added**, the integrated state (policy rate, inflation and its walks, the sticky band, FX, the peg, every clock, the lender-of-last-resort record, the yearly caches) and the player's choices (target, delegation, mandate, monetisation level, bloc-currency adoption) **taken from the loser**, the arrangements taken and flagged for re-discovery, and third countries' pointers to the loser repointed at the winner. **No `_applied` tracker is copied**: the winner's describe the winner's own modifiers, which the next pulse swaps to the copied state (copying one without its modifier is audit F7's bug). The price basket is re-seeded, and the timed `te_mon_peg_suspension` / `te_mon_peg_credibility_lost` / `te_mon_lolr_reneged` are re-added from their month counters. It is the one writer of `te_policy_rate` outside the update, and advances nothing. It rests on an unobserved engine fact — that the dead-but-undeleted loser can be read through a stored scope variable at that hook — so every read is behind `?=`, and each win logs `TE_CW_PROBE monetary` lines to `debug.log`. `test_monetary_civil_war.py` pins the classification. A loyalist win and a secession need nothing: the original keeps its own values, and a seceder is a new nation.

**No step has a second entry point.** The pulse family calling the whole update is the complete list. Step 9, `te_monetary_apply_interest_modifiers`, is the only step that even could be called alone — it recomputes the applied value, compares, and re-adds the modifier, without drifting the rate or drawing a walk — and it was, from `on_acquired_technology`, while vanilla's five finance techs were compensated in script and their −2pp landed a month ahead of the compensation. Cancelling those techs engine-side removed the reason, and the hook and its registration in `extra_on_actions.txt` came out with it. Don't reintroduce a second entry point without a reason of the same kind.

**Hidden state.** `te_neutral_rate`, `te_neutral_error`, `te_neutral_walk` and `te_mon_stance_gap` are never printed in any tooltip, loc string or visible modifier. The player's only window is the stance **band name**, and the band is computed from the bank's *estimate* (`gap − error`), so the true neutral rate cannot be recovered by stepping the dial and watching the band flip. Each band *does* state its own order of magnitude — `te_mon_stance_momentum_effect` / `te_mon_stance_bubble_effect` say "roughly 0.1 to 0.25 off Momentum a month" and so on, derived from the band thresholds times `−0.125` / `−0.75` and hedged because the band is the estimate while the push is the true gap. Hard-coded prose, so **if §21's two rates or the five band thresholds are retuned, those ten loc keys move with them** (the derivation table is in `banking_dash_custom_loc.txt` above the blocks). Consequence for script: `banking_stance_is_tight` / `_loose` read that hidden gap and are therefore **`ai_chance`-only** — putting either in a `possible` / `is_valid` / `custom_tooltip` would render the gap into a player tooltip. The eight surviving uses are all `ai_chance` weights in `timeline_extended_scripted_buttons.txt`.

**Never print `bubble_pressure` to a decimal, on any surface.** The stance reaches the banking cycle as `te_mon_stance_bubble_add` = `−0.75 × te_mon_stance_gap_clamped`, and — unlike momentum and cycle value, which `banking_cycle_advance_variables`' `random_list` nudges — bubble gets **no random term**. `banking_display_bubble_monthly_add` is exactly `modifier:country_bubble_pressure_monthly_add`, i.e. the modifier-driven part *without* the stance push, so Δ`bubble_pressure` minus the displayed monthly add is the stance push alone. Two readings a month apart therefore recover the hidden stance gap, and with it r\* — exactly wherever the gap is inside the −2…+4 clamp and bubble is off its own 0/100 bounds, which covers the entire stance-band range. Every surface today bands it (the dashboard band, title-only history rows, the graphical vanilla bar), which is what keeps the hidden-state rule above true; this is now load-bearing, not cosmetic. Any future tooltip, chart or debug surface that wants a bubble figure must band it, or give `bubble_pressure` a random term first.

**Cancel-INJECTs rest on confirmed INJECT summing.** Three files cancel a vanilla interest source with its exact inverse: `te_monetary_rank_injections.txt` (eight ranks) and `te_monetary_law_injections.txt` (`law_laissez_faire`) cancel `country_loan_interest_rate_mult` and re-express the contribution on `country_credit_standing_add`; `te_monetary_tech_injections.txt` cancels the flat `country_loan_interest_rate_add = -0.02` on the five vanilla finance techs, whose real contribution lives in `te_mon_access_premium` instead. All three only work if a `modifier = { }` inside an `INJECT:` **sums** with the vanilla entity's own block, which the owner read in game for all three entity types — techs and ranks on 2026-09-19, `law_laissez_faire` on 2026-09-20. If INJECT is last-wins, each file is wrong twice over — the cancel *adds* to vanilla's value, and the injected block wipes the rest of the entity's modifier (for the techs, that is `country_minting_mult = 0.1`, which is what the in-game check reads). The reads are recorded in `monetary_policy_design.md` §0.3 item 1 and `scripting_best_practices.md` § INJECT; each file stays deliberately isolated so that if a future patch changes the merge rule, the fallback (restate the entity as a `REPLACE:`) is still a one-file fix.

**Save-migration window (one release).** The `banking_policy_rate_hike` static modifier stays *defined* only so a save made while the deleted tool was active can be cleaned up. `common/scripted_effects/legacy_modifier_cleanup.txt` opens with a dated `PENDING REMOVAL` block listing the four artefacts — the static modifier, its two loc keys, the JE one-shot, and the line in `legacy_je_modifier_cleanup_effect` — that must come out **together**. Removing any subset early either strands pre-deletion saves at −2 intervention points or leaves a `remove_modifier` naming an undefined modifier.

**Open market operations, rewired.** `banking_open_market_ops` no longer touches interest at all (the dial owns the rate). Two gates now sit on it, and `banking_possible_cb_open_market_ops` reports them one at a time.

*Regime.* The tool is **fiat and digital currency only** (§0.1 ruling, 2026-09-20): buying bonds with money the state simply creates is exactly what a promise to redeem in metal forbids, so commodity money, the gold standard and crypto are shut out at any rate — the gold standard's own version of the move is suspending convertibility, which is phase 3 (§12.3). The gate is the declarative bool `country_can_create_unbacked_money_bool` (registered in `common/modifier_type_definitions/banking_cycle_modifier_types.txt`, granted in the `modifier = { }` blocks of `law_fiat_currency` and `law_digital_currency`), so both laws advertise "Enables Open-Market Operations" on their own tooltip rather than the rule living only in a trigger file. A regime that fails it gets `banking_omo_unbacked_money_tt` and nothing else.

*Floor.* For the two regimes that pass, the rate must sit at its regime **floor** — `te_mon_policy_rate_at_floor`, i.e. at or under `te_mon_floor_threshold` = `te_mon_target_min + 0.01`: `0.01` under fiat and `-2.99` under digital, the shipped §0 digital ruling, derived from `country_policy_rate_floor_add` rather than restated. The old `max = 0` in that value existed only to keep a gold standard's band floor (≈1pp) from counting as the floor; the regime gate does that job now, and gold never reaches the value. That branch is wrapped in a `trigger_if` on the regime bool so a gold-standard player is not also shown a red line about a fiat floor that could never have applied. It remains the balance-sheet tool of last resort rather than an everyday easing lever.

Its `country_bubble_pressure_monthly_add` went 0.8 → **1.5**: buying assets with the rate already at zero is how speculative excess builds. Its `ai_chance` was retuned around the floor gate (panic 70, downturn 45, bubble-risk-high −30) and its old "don't act while the rate hike is on" weight is gone as unreachable; the regime gate needs no AI weight of its own, because `possible` blocks the button outright. Phase 2 added the missing half of §11's AI rule — a `+40` deflation weight reading `te_inflation` against `te_mon_band_edge_deflation`, a symmetric `−35` above the comfort band, and a high-inflation weight on the *disable* side — and a `banking_omo_inflation_cost_tt` line naming the +1.0pp of inflation pressure the tool carries while active. **Known gap:** nothing removes an already-active `banking_open_market_ops` when a country switches fiat → gold. The law-change hook in `extra_on_actions.txt` only clears market tools on the way *into* a command or cooperative economy.

### Monetary Policy (phase 2)
Inflation, and everything that reads it. Spec: `monetary_policy_design.md` §9–§14, whose **§0.4 "Phase 2 as shipped"** carries the rulings, the deferred list, the known roughnesses and in-game checklist items 15–35. Phase 1's architecture is unchanged and still binds — the variable contract, the single-owner rule, the ROOT-resolved multiplier rule, the hidden-state rule — so read **Monetary Policy (phase 1)** above first. Like phase 1, **none of this has been seen in a running game.**

**New files.**

| File | Holds |
|---|---|
| `events/te_inflation_events.txt` | `te_inflation.1` "Not Worth the Paper" — the §9.2 hyperinflation crisis. Three options: currency reform (reset to 5% + investment-pool wipe + radicals + a ten-year risk premium), dollarise (−75% minting, no dial and no monetisation **until the country enacts a monetary law again** — the P9 exit, which clears the flag and pays the new-currency price; **or until it enters a command economy**, which clears the flag for free, because an administered currency is not a market re-founding), ride it out (default; 24-month cooldown) |
| `common/laws/te_monetary_wage_pressure_injections.txt` | ten `INJECT:`ed `country_wage_pressure_add` blocks on the vanilla labour and welfare laws (§9.4). `law_universal_basic_income` is mod-owned, so its +0.5 went into its own `modifier = { }` block in `extra_laws.txt` instead |

**Files phase 2 extended** — all already in the phase-1 table above, except the last three: `te_monetary_script_values.txt` (the §21 constants, the nine pressure terms, the §9.3 basket, the mandate reaction terms, two new premium terms, two dashboard display values), `te_monetary_effects.txt` (steps 1b / 6 / 6c / 6d / 8b, three new player controls and the shared `te_mon_effect_new_currency`), `te_monetary_triggers.txt` (`te_mon_has_inflation`, `te_mon_is_metallic`, `te_mon_can_monetise`, `te_mon_is_dollarised`, the monetisation stepper bounds), `extra_modifiers.txt` (six band modifiers plus five more), `banking_cycle_modifier_types.txt` (the two pressure types), `banking_dash_custom_loc.txt` (band name, band cost, monetise condition, the dollarised `no_dial` branch), `extra_on_actions.txt` (`te_banking_law_change_cleanup` also forces the monetisation level to 0 and runs **both** dollarisation exits — see the bands paragraph below), `te_history_banking_effects.txt` and both `.gui` widgets, `events/te_debug_monetary_events.txt` (`.5`–`.7`, the §19 row 2 harness) — plus **`common/static_modifiers/law_enactment_modifiers.txt`** (two unscaled `monpol_currency_*_pressure` companions), **`events/extra_law_events.txt`** (six application sites; event 40 retitled) and **`ideology_modifications.py` → `common/ideologies/modified.txt`** (generator input → output; never hand-edit the output — `docs/auto_generated_files.md`).

**The monthly update's new steps.** `te_monetary_monthly_update` now runs, in exactly this order: 0 init · 1 regime code · **1b `te_monetary_update_monetisation`** · 2 target + 3 drift (or 4, the derived rate, for a country with no dial) · 5 premium · **6 `te_monetary_update_inflation`** — internally **6a** the §9.3 basket and **6b** the inflation loop · **6c `te_monetary_apply_inflation_band`** · **6d `te_monetary_apply_wage_dividend`** · 7 rate paid · 8 neutral rate + stance · **8b `te_monetary_apply_stance_politics`** · 9 write the interest modifier. The five new steps are lettered rather than renumbering §16.2's list; the effect's own ORDER header states the same sequence and the reason for each placement. Step 6 is the engine:

```
pressure  = −0.4×stance_gap + phase + bubble + deficit + monetisation + QE
            + 100×(country_inflation_pressure_add + country_wage_pressure_add)
            + wage spiral + noise + regime pull
            + gold flow (gold standard) / price-specie (commodity money)
core     += 0.10 × (expected + pressure − core)
headline  = core + cost_push                  (§9.3 basket, k = 0.3, clamped ±6)
expected += α × ((1−c_eff)·headline + c_eff·anchor − expected)
```

`anchor` is `te_mon_inflation_anchor` — 2, or **0 under metallic money**, where expectations are pinned to 0 outright rather than blended — and `c_eff = c × max(0, 1 − |headline − anchor|/10)`. The rate stack reads all three figures and each one goes exactly one place: **core** feeds the mandates (a delegated bank looks through a supply shock), **headline** the real rate, the rate paid and the bands, **expected** the lenders' floor `max(policy, era_base + expected)` and §7.6's unanchored premium. Step 6 reads **last month's** stance gap, and step 5 last month's expectations (ruling P5); every affected site says so in a comment, and they all have to move together if the step order changes.

**Hidden state gained four members.** On top of phase 1's four: **`te_inflation_core`**, **`te_inflation_noise`** (a mean-reverting ±0.75pp walk that exists only so the pressure sum cannot be inverted back to the stance gap — ruling P7), **`te_cost_push`** and **the pressure sum itself**, every `te_mon_pressure_*` term included. Cost-push is **hidden in practice — never display it**: with cost-push shown, core becomes recoverable (headline is displayed and is their sum) and the P7 inversion opens. Nothing but `te_debug_monetary.1` prints it today. Displayed exactly, by contract: headline, expected, the five band edges, the monetisation level, and the two *player-chosen* pressure modifier types. `te_debug_monetary.1` is the one surface allowed to print the hidden values, and `.5`'s pin and `.7`'s seed are the only console *writers* of them.

**Three scaled-modifier sites now, not one.** Phase 1's rule — `add_modifier { multiplier = var:X }` resolves against ROOT, so it may only be issued from inside the monthly update, behind `root ?= this`, with a persistent `_applied` variable — has three users: step 9's `te_monetary_rate_paid`, step 1b's `te_monetisation_minting` and step 6d's `te_mon_real_wage_dividend`. All three share the remove-compare-re-add shape. Only step 9 keeps a `_rooted` repair marker, because a silent fallback to ×1 there still looks like a plausible interest rate; for the other two ×1 is one pound of minting a week or a rounding error of expectations, so they simply skip the re-add when ROOT is wrong and try again next pulse.

**Monetisation (§11).** A 0–3 stepper gated on `te_mon_can_monetise` (fiat or digital currency, a national bank, **not** CBI, not command economy, not dollarised). Each level is `country_minting_add` worth 1% of annual GDP a year — `te_mon_monetisation_gdp_share × gdp ÷ te_mon_weeks_per_year`, re-applied nearly every pulse because `gdp` moves, which is the whole reason §11 chose a GDP-scaled `_add` over `country_minting_mult` — bought with +2.5pp of inflation pressure and +0.5pp of cyclical premium per level. `te_monetisation_level` has **five** writers, as the variable contract's header says: the two stepper effects, step 1b (eligibility, plus the AI rule — escalate to 1 or 2 at war with `scaled_debt ≥ 0.5`, step back one a month otherwise), the law-change cleanup, and the §9.2 crisis's **currency-reform** option, which zeroes it because a reform that leaves the press running is not a reform. (The dollarise option needs no equivalent: `te_mon_can_monetise` reads false for a dollarised country, so step 1b zeroes it on the next pulse.) The console harness — all three of `te_debug_monetary.7`'s writing options: seed (level 0), war (level 3) and peace (level 0) — is a sixth writer and the contract's documented console-only exception. **`te_mon_weeks_per_year` and `te_mon_deficit_annualise_factor` are both 52 and deliberately separate constants**: the first is a fact about `country_minting_add`, the second a hypothesis about budget-flow units that §0.4 checklist 15 may flip to 1.

**The bands (§9.2).** Six `te_inflation_band_*` country modifiers, deflation through hyper, plus `te_mon_dollarised_modifier` as a **seventh state of the same family**. One bookkeeping variable — `te_inflation_band_applied`, 0 none / 1–6 band / 7 dollarised — drives the swap, never `has_modifier`, because add and remove results are invisible inside the block that issues them; one owner doing one swap is also what makes the −0.8 + −0.75 minting stack unreachable rather than merely brief. **Clearing `te_mon_dollarised` is what releases state 7**, on the next pulse — nothing removes that modifier by hand — so `te_banking_law_change_cleanup` runs *two* exits as one `if`/`else_if`: entering a command economy (tested first, free — an administered currency is not a market re-founding), and enacting any `lawgroup_monetary_policy` law (which pays `te_mon_effect_new_currency`). Before the command exit existed, a dollarised country that went planned kept `te_inflation_band_applied = 7` and its −75% minting for the rest of the campaign. Comfort is an empty modifier that is still applied, on `banking_stance_band_3`'s precedent. Every field is monotone from comfort to hyper, and the whole ladder is reproduced as a comment above the modifiers so a retune reads the column rather than the row. **The edges are hysteresised** (final-review finding I2): step 6b tests `te_mon_band_test_*`, which sits `te_mon_band_hysteresis` (0.25pp) on the far side of each edge *from wherever the country already is*, reading last month's `te_inflation_band` for the direction — so the live boundary is a quarter point above the nominal edge for a country climbing towards it and a quarter point below for one falling towards it, and a headline resting on 3% stops swapping the modifier, the dividend and the dashboard row every other month. The **hyper** edge is deliberately un-hysteresised on the way up, so the §9.2 crisis still fires at exactly 50. **Two fields are journal-entry-gated** by construction (`country_finance_momentum_monthly_add`, `country_bubble_pressure_monthly_add` — `banking_cycle_advance_variables` consumes them): a bankless country in deflation takes the rate rise and the politics but no momentum drag.

**Wage pressure and the real-wage dividend (§9.4).** Labour and welfare laws grant `country_wage_pressure_add`, a type of its own precisely so the dividend can tell a labour law from a devaluation (ruling P11); step 6 sums it with `country_inflation_pressure_add`. Above the *High* band edge the **positive** half of wage pressure is counted a second time — the wage-price spiral — while inside the **comfort band only**, and never for a command economy or a dollarised country, the same positive half instead pays `te_mon_real_wage_dividend`: financial momentum plus a *negative* `country_sol_expectations_lower_offset_add`. That key rather than `state_lower_strata_standard_of_living_add` because **standard of living is an integer and fractional SoL adds are inert** — see `scripting_best_practices.md` § "Standard of Living Is an INTEGER", and note the same section's warning that an expectations offset is a *standing* pressure that is never priced in, which is why it is sized smaller than the SoL change it replaced.

**Creditor-versus-debtor politics (§13).** Step 8b counts months on the **displayed** stance band (ruling P8 — keying on the true gap would print a bit of r\*): ±1 a month, capped at ±11, zeroed on a reversal, walked back toward 0 in the middle band. At ±6 it swaps in `te_mon_stance_politics_tight` or `_loose`, five IG-approval rows each, with the same applied-variable bookkeeping as the bands. These stack deliberately with the bands' own IG rows: the bands key on the price *level*, the politics on the rate the bank is holding against it. The regime laws' IG stances are generator input in `ideology_modifications.py`; the delivered net-stance table per IG is in `monetary_policy_design.md` §13.

**Dashboard and history.** Six new rows in the Monetary Policy block, between Risk Premium and Policy Stance: Inflation, Expected Inflation, Price Band, Wage Pressure, Inflationary Pressure, Monetise Deficit. All six sit inside the display-ready gate and **outside** the has-dial gate, so a no-dial or command-economy country reads every one of them. The Price Band tooltip builds its edge ladder from the five `te_mon_band_edge_*` script values and quotes the band modifier's **own `_desc`**, so retuning a band cannot leave the tooltip lying. Ops 7 and 8 on `banking_mon_control_sgui` drive the monetisation stepper; a country that may not monetise still sees the row, with greyed buttons and one cause line from `te_mon_monetise_condition`. History gains a `mon_inflation` sample and the sixth chart (core and noise are explicitly never sampled).

### Monetary Policy (phase 3)
The world rate, gold flows and the peg. Spec: `monetary_policy_design.md` §12 (and §6 for peg defence), whose **§0.5 "Phase 3 as shipped"** carries rulings Q1–Q13, owner decisions H–K (H, I and K since decided and implemented), the deferred list, the roughnesses and in-game checklist items 36–47. Phases 1 and 2's architecture is unchanged and still binds; read those subsections first. **None of this has been seen in a running game.**

**Files.** New: `events/te_peg_events.txt` (`te_peg.1`, the convertibility crisis). Extended: `te_monetary_effects.txt` (`te_monetary_refresh_world_rate`, step 0's world-rate cache and eight new variables, step 2's peg-defence branch, step 4, and the new **step 10 `te_monetary_update_gold`**), `te_monetary_script_values.txt` (the whole phase-3 block at the foot, `te_mon_target_min` / `_max`, `te_mon_pressure_gold_flow` in the pressure sum, the contract header), `te_monetary_triggers.txt` (`te_mon_is_on_gold`, `te_mon_peg_is_suspended`, `te_mon_peg_is_defending`, `te_mon_has_gold_flows`, `te_mon_peg_under_pressure`, `te_mon_is_on_peg_defence`, `te_mon_rate_is_discretionary`), `te_monetary_on_actions.txt`, `te_monetary_sguis.txt` (`banking_mon_shows_gold`, `banking_mon_world_rate_ready`), `banking_dash_custom_loc.txt` (`te_mon_peg_state`), `extra_modifiers.txt` (four timed `te_mon_peg_*` modifiers), the dashboard widget (four rows), `events/te_debug_monetary_events.txt` (`.8`, the §19 row 3 harness). **Removed:** `banking_cycle_events.12` "Gold Standard Pressure", its draw in `banking_cycle_effects.txt` and its loc — a random draw saying gold was leaving, replaced by gold leaving.

**Two world figures now, and they are not interchangeable.** `global_var:te_mon_era_base_world` (the *World Reference Rate*, 3.0 / 2.5 / 2.0 by era) is still the base of the hidden neutral rate, the lenders' floor in step 7 and every seed. `global_var:te_world_rate` (the *World Rate*) is phase 3's: the **real** rate — `te_policy_rate − te_inflation_expected` — of the great powers whose rate is **discretionary** (`te_mon_rate_is_discretionary`: a dial that is neither **narrow** nor on peg defence — a commodity band's midpoint *is* the world rate, so averaging it would be as circular as averaging a peg defender), GDP-weighted through two accumulator globals, clamped −2…10, and equal to the reference rate whenever nobody qualifies — which is the whole of 1836. It is read in exactly three places: a no-dial country's derived rate (step 4), the peg-defence formula (step 2) and the gold gap (step 10). Discretionary-only is what stops it being circular; do not add a consumer that also feeds it. **And nobody faces a world rate that contains itself** (owner decision H): the refresh records each member's exact share on the country (`te_mon_world_own_num` / `_den` — the one pair of monetary country variables written outside the monthly update, zeroed by the same refresh when a country leaves the average), and step 0 subtracts it, so a lone discretionary great power faces the reference rate rather than its own rate and has a gap like anyone else. Both are refreshed from the global `on_monthly_pulse` (reference first — the world rate falls back on it) and each country reads a per-pulse copy (`te_mon_era_base_now`, `te_mon_world_rate_now`) because the order of the global and country pulses is unknown.

**"On gold" is one trigger.** `te_mon_is_on_gold` = `law_gold_standard` **and not** `te_mon_peg_is_suspended`. The metallic anchor (`te_mon_is_metallic`), peg defence, gold flows, the 0–15 ceiling and the mandate button all go through it, so §12.3's "suspend convertibility — acts as fiat for five years without the law change" is a month counter (`te_peg_suspended_months`) and nothing else, on the dollarisation precedent. A raw `has_law_or_variant = law_type:law_gold_standard` in a monetary file is right only where the *law* is meant: the regime code, `te_mon_has_dial`, the dashboard's gold-rows gate and step 10's "the law is gone, clear the clocks" reset. A suspended country gets fiat's range, anchor, credibility and mandates — **not** OMO or monetisation, which stay gated on the fiat/digital laws.

**Step 10, `te_monetary_update_gold` — the bank's gold, not the treasury's.** For `te_mon_has_gold_flows` countries (on gold, with a dial): `gap = clamp(policy − world, ±5)`, `flow = gap × 0.002 × gdp` a month, moving **`te_bank_gold`**, the central bank's own vault — a stock measured against `0.2 × gdp` (vanilla's base reserve factor — deliberately **not** the engine's `gold_reserves_limit`, which `institution_national_bank`'s own `country_gold_reserve_limit_mult` inflates, so investing in the bank would thin its reserve), seeded without touching the treasury at `max(scaled_gold_reserves, 0.5)` of that limit the first pulse a country has gold flows, and un-seeded when the gold *law* goes. The first version used `add_treasury` (as §12.2 specifies); the owner replaced it after the first playtest, because flows changed the treasury with nothing in the budget to explain it, a rich treasury made the peg unbreakable, and four rulings existed only to stop a player spending borrowed gold. **Nothing about the flows touches the treasury now.** Inflows are **hot money** (`te_gold_hot_money`): they stop at the vault's limit; when the gap is ≤ 0 the balance leaves first, at twice the ordinary speed and never slower than a 0.5pp gap would give; and **it pays the policy rate** (`te_gold_carry`, monthly) — charged to the budget weekly through the scaled expense modifier **`te_mon_gold_carry_expense`**, the **fourth scaled-modifier site**, on step 6d's exact remove-compare-re-add shape behind `root ?= this` with `te_gold_carry_applied` as its never-removed multiplier variable. Under pressure (`te_mon_peg_under_pressure`: the **vault** under a tenth of its limit — the treasury's health is no longer in it) outflows stop and **`te_peg_confidence`** moves instead (−3 per pp of negative gap, −2 in a recession, −2 at `scaled_debt ≥ 0.5`, +2 otherwise; a hot-money exit that cannot be paid counts double); out of pressure it heals +1 a month while the gap is ≥ 0 and no borrowed gold is pending, and otherwise holds. At ≤ 20 it dispatches `te_peg.1` behind a 24-month cooldown it sets itself — the step 6c shape. **The fiscal link is one-way recapitalisation:** `te_mon_effect_recapitalise_bank` (op 13, gated by `te_mon_bank_can_recapitalise` — cash in hand, never on credit) moves a tenth of the limit from treasury to vault, and step 10 has the AI do the same a step a month when its vault is under a quarter and its treasury over half full. `te_bank_gold` therefore has three documented outside writers beside step 10: that effect, its silent AI twin, and `te_peg.1`'s devalue option. A country that stops being on gold altogether sends its borrowed gold home out of the vault (a suspension *freezes* it instead). The flow reaches inflation a month later as `te_mon_pressure_gold_flow`, 0.5pp per 1% of GDP a year. Step 10 also ticks the three clocks after everything that reads them. **Country monthly pulses are staggered** (Britain's falls around the 13th), so none of this happens on the 1st.

**Peg defence is `world + 0.5 × shortfall`, rounded up to a tenth.** `te_mon_peg_shortfall_pp` is 2 with an empty **bank vault**, falling to 0 at half its limit (treasury debt is no longer in it). The branch in step 2 carries its **own** hysteresis — move whenever the target is below the formula, take the next **tenth** up, come down only when more than 0.35 above (a whole point until the first playtest, where Britain's quarter-full vault turned a formula of 3.46 into a target of 4) — and then hands the shared round-to-nearest rule the target it has just settled, because a peg defender parked 0.75 *under* the world rate bleeds gold by construction.

**The crisis, `te_peg.1`.** *Defend* (default): `te_peg_defend_months = 12`, which `te_mon_target_min` turns into a floor of `ceiling(world + 4)` for manual and delegated targets alike; confidence +40. *Suspend*: the 60-month counter, `te_mon_peg_suspension` (+2pp cyclical premium, 1825 days) and `te_mon_peg_credibility_lost` (cancels the gold law's −1pp credit standing, 3650 days); convertibility resumes at confidence 50. *Devalue*: confidence 50, the **vault** revalued by 15% of its limit (the treasury gets nothing), **the exchange-rate index set to 88** and walking back to par over 60 months (phase 4 — same ±15% peak and impulse as the `te_mon_peg_devalued` timed modifier it replaced, which stays defined for old saves), `te_mon_peg_devaluation_pressure` (+3pp of inflation pressure decaying over two — pressure, not expectations, because gold re-pins expectations at 0 every pulse), and the old Devalue button's +1 infamy / −3 great-power relations. Like `te_inflation.1` it writes inputs and state, never the rate, and **must never call the monthly update**. It is the variable contract's phase-3 documented outside writer (`te_peg_confidence` and the two clocks).

**The modifiers live on the journal entry when there is one.** Following `scripting_best_practices.md` § "Journal Entry Scoped Modifiers", the system's *managed* modifiers — the inflation-band family (six bands + `te_mon_dollarised_modifier`), the two §13 stance-politics modifiers, `te_mon_real_wage_dividend`, `te_monetisation_minting`, `te_mon_gold_carry_expense` and `te_monetary_rate_paid` — sit on `je_banking_cycle` for a country that holds it and on the country otherwise, because the update runs for every tag and most have no banking entry. **Step 0b, `te_monetary_settle_modifier_home`**, runs first in every pulse: when `te_mon_mod_home` no longer matches `has_journal_entry`, it strips all sixteen (the thirteen above plus phase 4's `te_fx_weak`, `te_fx_strong` and `te_capital_controls_fatigue`) from both places and zeroes the five `_applied` variables so each step re-applies into the new home on the same pulse; a *canary* (an entry holding no member of the band family while `te_inflation_band_applied` says one is there) catches an entry that was lost and re-created with the home unchanged. **Every add, remove and `has_modifier` on a managed modifier goes through `te_mon_mod_add` / `_add_scaled` / `_remove` / `_strip` and the trigger `te_mon_mod_has` — never touch one directly.** On the entry a scaled modifier uses `multiplier = root.var:X` (the JE-scope rule); on the country it keeps the bare `var:X` form read in game since phase 1. **`te_monetary_rate_paid` joined the managed set on 2026-09-20** at the owner's request, so it is now on the entry too — it was the one deliberate exception, and the HOME mechanism turned out to answer three of the four reasons for it (a country with no entry keeps it on the country, which covers "universal" and "rule-off-safe"; the `te_rate_paid_rooted` marker gates *whether* step 9 rewrites, never *where*). The fourth — that it is the line the budget's interest tooltip names — is a display question script cannot settle; if the budget breakdown drops the line, revert the three call sites in step 9 and the strip in step 0b. **Still not managed, deliberately:** the timed crisis modifiers (`te_mon_currency_reform_premium`, `te_mon_peg_*`) stay where their event put them, since an entry that vanishes mid-clock would take the remaining years with it. The "three scaled-modifier sites" above are four with the carry, and all four are now home-aware.

**The bars are at the top, and there are four.** `banking_policy_stance_bar` (double-sided, −2 very tight … +2 very loose, fed from `te_mon_stance_bar_pos` = 3 − the displayed band, never the gap) sits between momentum and bubble pressure. The dashboard's conditions widget draws the entry's scripted bars from `JournalEntry.GetScriptedProgressBars` with vanilla's markup; vanilla's own copy at the bottom of the panel is hidden for this entry by **`gui/journal_entry.gui`, a one-line override of the vanilla panel** whose bar block now also requires `Not( JournalEntry.HasCustomWidget('custom_widget_container_7') )` — `je_banking.txt` puts a zero-sized marker widget there. It is on the vanilla-patch re-merge list like every other GUI override; the diff to vanilla is that one `visible` line and its comment.

**The target is no longer always an integer.** The stepper's buttons take `click_modifiers`: click a point (ops 0 / 1), **ctrl-click a tenth** (9 / 10), **shift-click to `te_mon_target_min` / `_max`** (11 / 12); all six share the two `is_valid` branches and clamp like the whole-point step. The three ordinary mandates still round to an integer, peg defence rounds to a tenth, and a manual target is whatever was set — so anything that prints the target uses one decimal.

**Nothing in phase 3 is hidden state.** The world rate, the gap, the flow, the hot-money balance and confidence are all built from displayed figures and carry no r\*, so the dashboard prints them exactly: a **World Rate** row under the reference row, and — for a gold-law country with a dial, suspended or not — **Bank's Gold Reserve**, **Gap to World Rate**, **Gold Flow**, **Borrowed Gold**, **Interest on It**, **Peg Confidence** and a **Recapitalise the Bank** button with a word from `te_mon_peg_state`. `te_debug_monetary.8` prints the globals and stages §19 row 3's exit criteria: its option a adds 2pp to the world rate through `global_var:te_world_rate_debug_offset`, the one debug hook in production code.

### Monetary Policy (phase 4)

Exchange rates and the trilemma. Spec: `monetary_policy_design.md` §15; what shipped, the rulings and the in-game checklist: §0.7. Files: `common/script_values/te_monetary_fx_script_values.txt` (every §21 constant is a named value there), `common/scripted_effects/te_monetary_fx_effects.txt`, four triggers at the foot of `te_monetary_triggers.txt`, three static modifiers at the foot of `extra_modifiers.txt`.

**`te_fx_index` is a real exchange rate, 100 = par, 50–150.** Nobody sets it. Every month (**step 5b**, `te_monetary_update_fx`, after the premium it reads and before the cost-push that reads it): `te_fx_shock` decays ×11/12 → `te_mon_fx_target_value` = 100 + **carry** (4 × clamp(own real rate − world rate, ±5) × `te_mon_controls_damp`) − **distrust** (2 × clamp(own inflation − world inflation, ±10)) − **flight** (1.5 × max(0, cyclical premium)) + shock → `te_fx_shadow` closes 1/12 of the gap → the **index by regime**: `te_mon_fx_floats` (not metal, not command) ⇒ index = shadow; metal ⇒ **par**, or while `te_fx_devalued_months > 0` a walk from 88 back to par at 1/30 a month; command economy ⇒ par and no shadow. Then `te_mon_overvaluation = max(0, index − shadow)`, imported inflation, the three-year average, and the capital-controls counter. Each term is its own script value because the dashboard tooltip and `te_debug_monetary.9` list them.

**Two deliberate departures from the spec's letter (§0.7 F1, F2).** A country **without a dial earns no carry** — its derived rate is world + expected + the 1pp bankless spread, which would park every bankless floater four points strong for ever, the FX twin of the standing-tight penalty §8 refuses. And the **inflation each currency is judged on** (`te_mon_fx_inflation_read`) is *expected* inflation for everyone except metal, which is read on **realised core** (Q12 pins metallic expectations at 0) — and `global_var:te_world_inflation` averages that same read per great power, so an all-metal world that inflates together on a gold rush is compared like with like.

**World inflation** is the world rate's sibling: `te_monetary_refresh_world_inflation` on the global pulse, GDP-weighted over *all* non-command great powers (inflation is not circular, so no discretionary filter), own share recorded on the member (`te_mon_world_infl_own_num` / `_den`) and subtracted in step 0 into `te_mon_world_inflation_now`. Fallback 0.

**One phase-4 term does §9.1's work too.** `te_mon_fx_term_inflation` — the *distrust* half of the exchange-rate target — is also the input to `te_mon_pressure_commodity_specie`, the commodity-money price-specie channel added 2026-09-21 (design §0.6 R7, issue #351). It is read **live** and normalised back out of `te_mon_fx_inflation_weight`, so the exchange-rate weight stays a phase-4 tuning number and a balance pass on it cannot silently retune the discipline; the *rate* half is excluded on `te_mon_fx_overvaluation_for_peg`'s precedent. That closes the §15.6 bullet about commodity money's display-only overvaluation — see the range paragraph under **Monetary Policy (phase 1)**.

**Consequences.** `te_fx_weak` / `te_fx_strong` — **two fixed-sign scaled modifiers** (design §17 check 8 on negative multipliers is still open), ±1.25% `state_export_advantage_mult` / `state_import_advantage_mult` per index point, so index 80 / 120 reproduces the deleted buttons' ±25%. `te_mon_premium_fx` adds +0.05pp of cyclical premium per point below par and **reads last month's index on purpose** (step 5 runs before 5b; the lag is what breaks the premium ↔ FX loop inside a tick — do not "fix" it). **Imported inflation is a change term**: `0.15 × (te_fx_avg − index) × openness`, where `te_fx_avg` is a 1/36 moving average and openness is ×0.6 / ×1.0 / ×1.5 by `market_trade_reliance` (< 0.1 / … / > 0.3); it is added **inside** the `te_cost_push` value block so it shares the ±6pp clamp and the mandates look through it, and every site that zeroes cost-push zeroes `te_fx_imported` too (currency reform re-seeds the average). On a **gold peg**, overvaluation is the fifth confidence term in step 10: −1 per 2 points beyond 5, × `controls_damp`, independent of the vault, and an overvalued peg does not earn the +1 heal. It is judged on `te_mon_fx_overvaluation_for_peg`, which takes the carry term's *negative* contribution back out — a low rate under gold is already priced by the vault (§12.2), so only inflation and a distressed treasury drain a peg this way (§0.7 F4).

**Capital controls are the trilemma's third corner.** `te_mon_controls_damp` is 0.25 while `banking_capital_controls_out` is active and is read at exactly three sites: the carry term, `te_mon_gold_gap_value` (after its clamp, both signs — and through `te_gold_flow_gap`, the confidence drain), and the overvaluation drain. It does **not** touch the distrust or flight terms. The price is `te_capital_controls_fatigue`, scaled by `te_capital_controls_months ÷ 12` (0–5): −1 Industrialists and Petite Bourgeoisie and −2% investment-pool efficiency per peacetime year; the counter is **frozen** while `te_mon_in_external_crisis` (war, downturn/panic, peg confidence ≤ 40, hyperinflation) and decays 3 a month once lifted — freeze wins over decay. The modifier itself lost its old +0.05 pool *bonus* and gained Trade Unions +1. The same crisis trigger drives both buttons' `ai_chance`.

**Step 9b, `te_monetary_apply_fx_modifiers`**, is the one refresh site for all three scaled modifiers. They are *managed* (JE-homed when there is an entry; `te_monetary_settle_modifier_home` strips them on a change of home), re-applied only when the multiplier moves by half a point (a twelfth of a step for fatigue) or the modifier has gone missing, and removed rather than applied at zero.

**Events write `te_fx_shock`, never the index** (`te_mon_effect_fx_shock = { POINTS = N }`, always inside a `custom_tooltip` since a variable write draws none). A shock decays as fast as the index adjusts, so it **delivers 38% of nominal**, peaking eleven months out: −26 is a ten-point move, ±13 is five, and the ±40 clamp caps any event near fifteen. Re-pointed sites: `banking_cycle_events.58` managed devaluation (−26 — dormant since 58 was confined to the simplified rule, where there is no exchange rate; see the banking events list in `journal_entry_systems.md`), the five `banking_event_fx_defense` options (+13), the three `monpol_currency_devaluation` law-event options (−13), and the crash option *Suspend convertibility* (−13, replacing its modifier's −10% export line). The two documented index writers are `te_mon_effect_fx_devalue_peg` (§12.3 Devalue) and the save migration.

**Deleted:** `cb_fx_devaluation` / `cb_fx_support` and their disable pair, effects, `possible` triggers, `banking_tool_*_active`, dashboard sguis and GUI rows, history marker rows, `fx_support_activation_cost`, the two tech-gate bools (also out of `scripts/generators/add_tech_modifiers.py`), the law lock `country_banking_lock_fx_devaluation_bool`, and ~18 loc keys. **Save migration:** both static modifiers stay defined for one release; `te_monetary_init_fx_variables` seeds a holder's index at **80 / 120** (what ±0.25 was in index points — not a shock, which would land 38%) and strips them. Retirement checklist: `legacy_modifier_cleanup.txt`.

**Dashboard, history, debug.** An EXCHANGE RATE sub-block (index, exact; trade edge + imported inflation, or overvaluation under a peg), a seventh history chart (`mon_fx`, the §20 risk 9 loop detector), and `te_debug_monetary.9`, which prints every FX figure and stages §19 row 4's exit criteria (level shock −20, event shock −26, controls counter to 60).

### Monetary Policy (phase 5)

**Treaty eligibility / AI update (2026-09-23).** Peggers must retain a compatible
currency: fiat/digital accept any eligible anchor; commodity/gold require a
commodity or convertible-gold anchor. Crypto, dollarisation, command economies,
boards and common-currency adopters cannot take treaty pegs. Both peg articles
check this at signing, maintenance and discovery. Support remains currency-neutral,
but providers/receivers must retain a national bank, stay solvent and remain
outside command economies; receivership debtors must also remain non-command.
Discovery filters invalid support before assigning roles or charging costs and
settles swap balances through the existing role-end path. AI proposal evaluation
is quartered for all five articles; swap/guarantee demand now depends on external
crisis / debt >= 50%, and voluntary pegs carry more baseline reluctance. See
`monetary_policy_design.md` "Treaty eligibility and AI tuning" for the values.

International monetary arrangements. Spec: `monetary_policy_design.md` §15A; what shipped, the rulings (G1–G16) and the in-game checklist (P5-1…18): §0.8. **Not seen in a running game, and built on a phase 4 that has not been either.** Files: `common/script_values/te_monetary_arrangement_script_values.txt` (constants + the phase-5 variable contract) and `te_monetary_union_script_values.txt` (5b), the matching `scripted_triggers/` and `scripted_effects/` pairs, `common/treaty_articles/110_currency_peg.txt` / `111_swap_line.txt` / `112_lender_of_last_resort.txt`, `principle_group_monetary_union` (five principles, five script-only `power_bloc_*_bool` markers), `events/te_monetary_arrangement_events.txt` (`te_lolr.1`, its ward notice `te_lolr.2`, `te_union.1`), `te_peg.2` in `te_peg_events.txt`, `te_monetary_internal.2`, and twelve static modifiers at the foot of `extra_modifiers.txt`.

**The anchored state is the spine.** `te_mon_anchor` (a **scope** variable — the `te_basket_market_owner` contract: cannot hold 0, read as `var:te_mon_anchor = { … }` behind `has_variable`, may be absent) plus `te_mon_anchor_kind`: **1** treaty peg, **2** bloc currency, **3** currency board; highest wins. An anchored country has **no dial** (`te_mon_has_dial` gained `NOT = { te_mon_is_anchored = yes }`), **imports the rate** (third branch of `te_monetary_set_derived_rate`: anchor's rate + spread 0.5 / 0 / 0.25, *no* expected-inflation term — G13), **takes the anchor's `te_fx_index`** (first branch of step 5b's index-by-regime, less a kind-1 `te_mon_peg_parity_offset`) while its own formula runs on as `te_fx_shadow`, cannot monetise or run OMO, and **imports credibility** (`te_mon_credibility_c` = max(own, 0.8 × anchor's); `te_mon_inflation_anchor` = the anchor's target — both were split into `_own` + the consumer-facing name). It **keeps its own inflation, neutral rate, stance gap and cycle**: the three hidden-state gates in the monthly update read `te_mon_has_stance` (dial **or** anchored), not `te_mon_has_dial` (G1). `te_mon_overvaluation` is the one pressure gauge all three kinds read.

**`te_mon_is_anchored` reads STORED state only — never add a validity test to it.** Validity is "the anchor has a dial", and `te_mon_has_dial` asks `te_mon_is_anchored` of the anchor, so the two would call each other down the chain. **Step 1c** (`te_monetary_update_anchor`, before 1b and 2) keeps the stored pair checked and copies the anchor's rate / index / own-c / own-target into `te_mon_anchor_rate` / `_fx_index` / `_c` / `_target`, so every later read — script values, the dashboard — is a local `var:`, never a cross-country chain. "The anchor must hold a dial" (`te_mon_can_be_anchor`) is also what makes chains and cycles unconstructible.

**Detection is three-way, and the discovery is idempotent.** `te_monetary_discover_arrangements` decides (kind, anchor) by precedence, the swap-line / guarantee roles, and what this country pays for what it extends; only a *change* writes anything (`te_monetary_anchor_changed`: joining snaps the index to the anchor's and re-seeds `te_fx_avg`; leaving snaps to the shadow and does **not** re-seed — that jump is the devaluation, G5). It runs (1) **monthly in step 1c, but only for flagged countries** (`te_mon_arr_scan = 1`: any role at all — G2), (2) from **hooks** — the three articles' `on_entry_into_force` / `on_withdrawal`, `on_become_subject` — which dispatch **`te_monetary_internal.2`** a day later, and (3) **yearly for everybody**. It needs **ROOT = the country** (its treaty walk tests `source_country = root`, its cost terms read `root.var:`), which is why hooks dispatch an event. **Never dispatch `te_monetary_internal.1` for this: that is the non-idempotent monthly update.** `te_mon_effect_union_exit` = `_exit_costs` + one discovery; the discovery calls only the `_costs` leaf, so nothing recurses.

**Every premium term goes through managed scaled modifiers, never a treaty's modifier block** (G8): `te_mon_arrangement_recipient` (−cyclical), `_provider` (+cyclical) and `_standing` (−structural), refreshed in **step 9b** (`te_monetary_apply_arrangement_modifiers`) with phase 4's `te_monetary_apply_fx_one` recipe, so step 5 sees them a month late like any modifier-borne term. **Provider cost = recipient benefit × clamp(recipient GDP ÷ provider GDP, 0, 1)** — evaluated in the recipient's scope against `root.var:te_mon_work_gdp`.

**5a — three directed articles.** `currency_peg` (pegger → anchor): kind 1, structural −0.5pp; the anchor is a *reserve currency* (−0.1pp per 5% of world GDP pegged to it, cap −0.5 — `te_monetary_refresh_anchored_gdp` on the global pulse; **boards excluded**, G7). `swap_line`: recipient −1pp cyclical, **+2 peg confidence a month** (gold pegs and treaty pegs alike — `te_mon_backstop_confidence`), hot-money exit ×1 in a panic, and in `te_mon_in_external_crisis` the provider pays the recipient 0.1% of recipient GDP a month (G6). `lender_of_last_resort`: the ward's §7.6 debt-load premium halved, imported crashes × 0.8 (`te_mon_has_effective_backstop`), and **on the ward's default** (`on_country_default`) `te_lolr.1` on the guarantor — *honour* (5% of ward GDP) or *renege* (`te_mon_lolr_suspended_months` = 60: every other ward's benefit is off). Same-draft / existing-treaty checks are in **`can_ratify`**; every AI score line carries `desc =`. **Tech gates are staggered over three eras** (owner decision 2026-09-21, replacing `central_banking` on all three): `currency_peg` at `international_exchange_standards`, `swap_line` at `macroeconomics`, `lender_of_last_resort` at `intergovernmental_organizations`. A kind-1 pegger runs `te_peg_confidence` on overvaluation against its anchor (`te_monetary_update_anchor_peg`, step 10 — §15.2's drain and Q10's heal-holds, unchanged) and gets **`te_peg.2`**: *Defend* (capital controls forced for 12 months via `te_mon_capital_controls_in_force`, which replaced the tool test inside `te_mon_controls_damp` and the fatigue counter — G15), *Break the peg* (withdraws from the whole **treaty** — G14), *Re-peg lower* (parity offset += half the overvaluation — G4).

**5c — currency boards are rule-based.** `te_mon_is_board_subject` is the OR-list of vanilla's `autonomy_level = 1` types (puppet, vassal, colony, crown land — **re-derive on every vanilla bump**, `vanilla_patch_runbook.md` § 6b); such a subject is kind 3 on its *direct* overlord whenever the overlord holds a dial. Three managed modifiers from `te_monetary_apply_board_modifiers`: `te_mon_board_subject` (`country_minting_mult = −0.5`), `te_mon_board_seigniorage` (the overlord's half as a scaled flat `country_minting_add`, re-summed **yearly** — a gold-colony lever, a rounding error otherwise), and `te_mon_board_wrong_stance` (+0.15 liberty desire after six consecutive months with the **displayed** band at 1 or 5 — never the true gap). No exit penalty.

**5b — the bloc's common currency.** Principles carry **markers, not mechanics**; script reads the tier through `has_principle` (G10). Tier 1 = half a swap line from the leader for every member; tier 2 = members **may adopt** (`te_mon_union_member`, behind `te_mon_union_can_adopt`: fiat / digital + bank, inflation within 3pp of the leader's, `scaled_debt < 0.5`, no board) → kind 2 on the leader, +5% export **and** import advantage (`state_trade_advantage_mult` does not exist — G9); tier 3 = the leader is lender of last resort to adopters; **tier 4** (2026-09-21) = a banking union over every adopter (−0.25 crash chance and random momentum, +1 intervention in reserve, the shared-currency contagion channel damped by −6 of its +10; 0.25pp of provider premium per adopter for the leader); **tier 5** = a reserve currency (the leader's standing cap −0.5 → −1.0pp and seigniorage on the world's balances; adopters +0.10 trade advantage and −0.25pp of standing; cohesion per member +2). **No peg to break, so the premium is the valve**: `te_mon_premium_union_overvaluation`, +0.1pp per point beyond 5 (halved at tier 3+, never zeroed at any tier), in step 5 off last month's index. **Every tier gate lists every higher tier** — `te_mon_bloc_union_tier_2_plus` is what keeps an adopter anchored, so a gate that stops short force-exits every adopter, with the full penalty, the month the bloc upgrades (§0.11 ruling T1). **Pressure** is a leader toggle costing 50 influence per holdout (`te_mon_union_pressure`); a pressed holdout loses the cooperation benefit (never a premium), has the debt criterion waived and is put **The Question** (`te_union.1`) when an integer signature changes — pressed + 2 × criteria met + 4 × tier — with a five-year floor; refusing costs the leader 5% cohesion and gives the holdout +250 leverage resistance for ten years, refreshed not stacked. **AI never sees the event**: it resolves on `te_mon_union_adopt_score`, and the leader's dashboard shows holdouts and how many would refuse. A member with no common currency left to be in has **exited**, with the costs — including when the *leader* lost its dial (a known roughness). A shared currency is a contagion channel in `banking_cycle_effects.txt` (`te_mon_shares_currency_with`).

**Deleted:** `cb_fx_swap_lines` and its disable pair, effects, `possible` trigger, `banking_tool_fx_swap_lines_active`, dashboard sguis and GUI rows, history marker rows, the tech-gate bool (also out of `add_tech_modifiers.py`), the law lock, 11 loc keys. `banking_fx_swap_lines` stays defined for one release; `te_monetary_init_arrangement_variables` strips it every pulse; checklist in `legacy_modifier_cleanup.txt`.

**Dashboard, debug.** An INTERNATIONAL ARRANGEMENTS sub-block, hidden unless the country holds a role: *Monetary Anchor* (names the anchor through `Var('te_mon_anchor').GetCountry.GetName`, only ever inside a custom-loc branch guarded by `te_mon_is_anchored`), a treaty pegger's *Peg Confidence* + meter, *Backstops* (received / extended), *Monetary Union* with four single-purpose scripted GUIs (adopt, leave, press, stop pressing). `te_mon_no_dial_reason` has three anchored branches above the bank test. `te_debug_monetary.10` prints everything and pins a **treaty-less debug anchor** (`te_mon_debug_anchor_on` — nothing in play sets it).

### Monetary Policy (phase 6)

Leverage, coercion and exploit hardening — what a review of the shipped 5a articles found missing or gameable. Spec: `monetary_policy_design.md` §15B (the review) and §15C (the plan, with the owner's thirteen rulings in §15C.5); **what shipped and where it departs from the plan: §0.10, deviations P1–P13, checklist P6-1…13.** Built 2026-09-21 in one change, on top of a phase 5 that has never run in a game either. New files: `common/treaty_articles/113_imposed_currency_peg.txt`, `114_debt_receivership.txt`, `te_debug_monetary.11`. Everything else is edits to the phase-5 files.

**6a — the swap line is a loan.** `te_mon_swap_drawn` (recipient scope, money, never removed) accumulates the crisis draw and is paid back out of the crisis at the same 0.1% of GDP a month, interest-free; the balance stops at `te_mon_swap_line_limit` = **2% of recipient GDP**; and when the recipient role ends with a balance outstanding the discovery settles it **in one lump** (`te_mon_effect_swap_settle`, run *before* the role is re-derived, while `te_mon_swap_provider` still names the lender). `111_swap_line.txt`'s `can_ratify` gained **one provider per recipient** (112's rule, ruling H1), which is what makes that stored provider unambiguous. **The draw reads `te_mon_in_financial_crisis`, not `te_mon_in_external_crisis`** (ruling H2): the two are now one definition plus a war leg (`external = OR { is_at_war, financial }`), and only the draw takes the narrow one — capital-controls forgiveness keeps the wide one. A war is the one leg a player can switch on and sustain at will.

**6a — the guarantee remembers.** `te_mon_lolr_calls` (0–5) counts what a **ward** has cost whoever stood behind it, so it survives a change of guarantor; `te_mon_lolr_call_forget` (120 months, re-armed on every call, decremented in step 1c's clocks) forgets one call per ten quiet years. Four sites read it: the honour cost (5% × (1 + 0.5n), cap 15%), the relief share (0.5 / 0.35 / 0.2 / **0** — the moral-hazard loop closes on the third default), `te_lolr.1`'s odds (Honour 10 − 3n : Renege 2 + 2n, saturating at 1:8) and the ward's own cooldown (60 × (1 + n) months). **One convention, stated at the increment:** `te_monetary_on_country_default` increments *first*, so anything pricing **this** call reads `te_mon_lolr_calls_prior` (= calls − 1) and anything pricing the **ongoing** relationship reads the counter (§0.10 P2). Both backstop articles' provider score gained `te_ai_backstop_repeat_defaulter` (−20 × calls) and `te_ai_backstop_drawn` (−20 if the counterparty still owes on any line).

**6a — what was deliberately *not* built.** The anchor's per-pegger `country_prestige_mult = 0.02` **stays as shipped** (ruling H5): no managed prestige term, and §17 check 24 reads the stacking in-game instead. And there is **no scripted AI withdrawal** (ruling H6): the two new score terms are the whole implementation, and §15C.1's yearly walk on `is_equal_exchange_for` stays unwritten until §17 check 22 says the engine's own AI does not act on a re-scored in-force treaty. All three friendly articles gained `non_fulfillment = { consequences = withdraw }` on war or expelled diplomats — **withdraw, not freeze**, because §17 check 15 is unanswered and a peg between belligerents should end (ruling H7).

**6b — leverage, one line each.** `country_treaty_leverage_generation_add` goes on the **dominated** party's modifier block — the engine generates the leverage *against* the country carrying the modifier, not by it (vanilla `guarantee_independence` puts it on the guaranteed party, `foreign_investment_rights` / `trade_privilege` / `host_power_bloc_embassy` on the party granting the concession). Phase 6 shipped all five monetary articles on the strong side, which inverted every one of them; corrected 2026-09-21. So: **200** on `currency_peg`'s `source_modifier` (the pegger is the source), **150** on `swap_line`'s and **300** on `lender_of_last_resort`'s `target_modifier` (the recipient and the ward are the targets), **400** on `imposed_currency_peg`'s and **500** on `debt_receivership`'s `source_modifier` (the coerced pegger and the debtor are the sources). Flat, not scaled, and that is safe for two engine reasons: the modifier generates leverage only while the dominant country **leads a power bloc**, and leverage is generated **per pair** out of the target's own pool — so an anchor with ten peggers has leverage on ten countries, which is orbit-building, not a stack on one.

**6c — two hostile articles.** `imposed_currency_peg` (source = the pegger, who concedes; target = the anchor, who imposes — 103's direction convention, which is the friendly peg's already): kind 1 exactly as under 110, with **spread 1.0** (`te_mon_anchor_spread_peg_imposed`), **no `te_mon_peg_standing_cut`** (the −0.5pp is the market's reward for a *chosen* discipline), −10 legitimacy, 400 leverage, **no prestige line**, and **`te_peg.2`'s Break option closed to it** — its way out is the treaty UI, which is what the war goal answers. `debt_receivership` (source = the debtor, target = the receiver): the guarantee's relief, paid for with `te_mon_receivership_take` = **0.1% of debtor GDP a month**, −10 legitimacy, 500 leverage, and **no `te_lolr.1` on the debtor's default** — a receiver is a creditor, not a guarantor. It **ends itself** twelve months after the debtor holds `scaled_debt < 0.25` out of default (step 1c counts into `te_mon_receivership_clear_months`; 114's `non_fulfillment` reads it). **No hostile swap line** (ruling C3): forcing a country to lend is not a thing history did.

**6c — the two rules that matter when touching this.** (1) **Both pretexts are `in_default` only** (ruling C4) and are tested **twice**: symmetrically in `possible` (which runs before the direction is fixed, so `scope:source_country` is not a handle there) and directionally in `can_ratify`, which carries the tooltip — `treaty_articles_reference.md`'s own rule. (2) **Every site that walks for a peg article now tests both types**, `OR = { has_type = currency_peg has_type = imposed_currency_peg }`: `te_mon_has_peg_article`, `te_mon_has_valid_peg_article`, the discovery's kind-1 branch, `te_mon_effect_anchor_peg_break`, and 110's *already pegged* `can_ratify`. `te_mon_is_imposed_pegger` is a **live treaty walk**, not a stored flag — which article put a country in the anchored state is a property of the treaty (§0.10 P8). 113 excludes 110 and 114 excludes 112, declared in both files each way.

**Debug.** `te_debug_monetary.11` (console-only, like `.10`) prints the swap balance, the ward's record and the coercion state, and gives four levers: pin / release a **treaty-less debug swap line** (`te_mon_debug_swap_on`, honoured by the discovery through `te_mon_has_swap_line_role`), force one month of financial crisis (`te_inflation_band = 6`, which the next pulse overwrites), and cycle `te_mon_lolr_calls` 0 → 1 → 2 → 3 → 0.

### The `banking_system_simplified` game rule

`banking_system_rule` has **three** settings, not two (`common/game_rules/extra_game_rules.txt`).
`banking_system_simplified` keeps this whole section down to **Monetary Policy (phase 1)** and
switches phases 1–5 off. The player still gets the cycle, its crashes, the prudential /
command / cooperative tools, the financial-regulation laws and the history charts; they get no
policy-rate dial, no inflation, no exchange rate, and no pegs, swap lines, guarantees or shared
currency. Interest is still country-specific — the world reference rate plus the risk premium —
they simply do not steer it.

**One trigger does all of it: `te_mon_full_system`** (`common/scripted_triggers/te_monetary_triggers.txt`,
`has_game_rule = banking_system_enabled`, scope-free). `te_banking_system_on`
(`banking_policy_triggers.txt`) is its counterpart for the *cycle*: true for enabled **and**
simplified, and what the journal entry and the history store ask.

**What the rule reaches:**

| Site | Behaviour when `te_mon_full_system = no` |
|---|---|
| `te_mon_has_dial` | false for every country — one line, and every consumer (steps 2/4, the dashboard block, the OMO gate, the conditions' stance row, the union principles' `ai_weight`) falls to its no-dial side |
| `te_monetary_monthly_update` | steps 0, 0b, 1, 4, 5, 7 and 9 only. 1b, 1c, 5b, 6, 6c, 6d, 8, 8b, 9b and 10 are skipped, so their variables keep step 0's neutral seeds (`te_inflation` 0, `te_fx_index` par, `te_mon_anchor_kind` 0, `te_mon_stance_gap` 0) and every downstream read gets a sane answer rather than a missing variable |
| `te_monetary_set_derived_rate` | the **bankless spread is conditional**: normally every country here is bankless, but with the dial off a country that built a national bank would otherwise be charged 1pp for not having one |
| `te_monetary_refresh_world_rate` | short-circuits to the era base — with no dial anywhere the accumulator would reach its own `else` after two ~200-country scans |
| on-action hooks | the phase-4 world-inflation refresh, the phase-5 anchored-GDP scan, the yearly arrangement scan, `on_become_subject` and the `on_country_default` guarantee call are all skipped |
| `banking_possible_cb_open_market_ops` | drops the regime and rate-floor conditions — OMO reverts to its pre-phase-1 gate (unlock bool, 4 points, law lock). The `on_law_enacted` auto-switch-off is gated to match |
| `cb_capital_controls_outflow` (+ disable) | `ai_chance` falls back to the pre-phase-1 cycle rule; the external-crisis rule reads its neutral inputs and would never fire |
| `te_mon_effect_fx_shock_tt` | the wrapper the ten event options call: no shock **and no tooltip line**, so no option promises a currency move that cannot happen |
| treaty articles 110–112, `principle_monetary_union_1..5` | `visible = no` |
| dashboard / history GUI | the Monetary Policy readout block is hidden; open-market operations fall back to a plain row under the same header, drawn for a market economy only (moral suasion now lives in Prudential Regulation); the inflation and exchange-rate charts are hidden and not sampled |

**`banking_system_disabled` takes the same path through the monetary layer** — `te_mon_full_system`
is false for it too, and it always should have been: with the journal entry gone there was no UI
for the dial, the bands or the hyperinflation chain, but the whole simulation still ran behind it.

**Known roughness.** Five script-only modifier types are granted from `modifier = { }` blocks
that take no trigger, so they still render on law tooltips under the simplified rule with
nothing consuming them: `country_wage_pressure_add`, `country_policy_rate_drift_speed_mult`,
`country_policy_rate_floor_add`, `country_bank_forecast_error_add`,
`country_inflation_pressure_add`. See `monetary_policy_design.md` §0.9.

**What the rule deliberately does *not* reach.** The cancel-`INJECT`s (`base_values`' flat 20%,
the six rank multipliers, laissez-faire, the five finance techs — §16.1) are file-level merges no
game rule can switch off, so the passive rate stack runs under all three settings. Switching it
off as well would leave every country borrowing at 0%.

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

Directed Credit & Development Banks also grants `country_directed_credit_sectors_add = 1` — a second directed-credit sector at once (see **Policy tools added 2026-09-23**).

(`state_capitalists_investment_pool_efficiency_mult` is a vanilla per-pop modifier; Prudential is the only banking law that uses it. CBI gets the opposite signal at scale through `institution_national_bank` (+5%/level for capitalists in National Bank states).)

**Script values** (in `extra_script_values.txt`):
- `banking_random_nudge_down_value` — base -1, scaled by `(1 + country_banking_random_momentum_mult)`. Used in the random nudge step.
- `banking_random_nudge_up_value` — base +1, scaled the same way.
- `banking_crash_chance_multiplier_value` — base 1.0, adds `country_banking_crash_chance_mult`, clamped to min 0. Multiplied into crash weight.

**To add banking volatility/crash modifiers from other sources** (technologies, PMs, etc.), simply add `country_banking_random_momentum_mult = 0.1` or `country_banking_crash_chance_mult = -0.15` to the modifier block.

**Per-tool law gating.** Most `cb_*` buttons are tier-unlocked by `country_banking_intervention_max_add` (a threshold per button — see the `possible` blocks in `timeline_extended_scripted_buttons.txt`). On top of the tier gate, every banking law publishes its tool restrictions via `country_banking_lock_<tool>_bool` modifiers (defined in `banking_cycle_modifier_types.txt`). The lock entries appear as red "Locks: …" lines in the law's modifier-block tooltip, and each `cb_*` button gates on a `custom_tooltip { modifier:country_banking_lock_<tool>_bool = no }` check that surfaces the reason as "Tool not available under your current banking law" when the button is greyed. To add a new law-based restriction: add `country_banking_lock_<tool>_bool = yes` to the law's modifier block — no edits to scripted_buttons needed. Crisis-only tools (`cb_emergency_liquidity_program`) remain available regardless of law as Bagehot-style lender-of-last-resort. `cb_capital_controls_outflow` has a war override (`is_at_war = yes` bypasses the lock).

**Toggle costs.** Each `cb_*` button has friction on toggle to discourage rapid cycling, calibrated to its real-world parallel: monetary tools (OMO, asset relief, directed credit, e-liquidity, export credit) cost treasury via `banking_*_activation_cost` script values scaled to GDP; political tools (countercyclical buffer, raise margin requirements, deposit guarantee) generate radicals/loyalists via `banking_small_radicals_value` and `banking_medium_radicals_value` (banking-specific equivalents of vanilla `small_radicals`/`medium_radicals`, defined in `extra_script_values.txt` to allow tuning banking-button friction independently of global event balance); capital controls cost infamy and -2/-3 relations with great-power trade partners. Moral suasion is the lone exception — speeches have no real-world toggle cost.

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
| `gui/journal_entry_widgets/banking_history_widget.gui` | the three banking charts, wired to `custom_widget_container_2` of `je_banking_cycle` |

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

Sharing one container between all of a month's metrics is what makes the store affordable: 240 containers per tracked country covers *every* series rather than 240 per series, and a month's markers land on the same container as its readings, so the chart never has to search for them. A metric that was not recorded in a month simply has no `te_hist_v_<METRIC>` variable there — that is how the charts tell **missing data from a genuine zero**, and why a country that drops out of eligibility leaves a visible gap rather than a run of zeroes.

`te_history_month_index` is stateless: the same arithmetic on the current date, identical for every country and for the global series. Nothing has to be seeded on an existing save, two pulses in one month resolve to the same container, and there is no counter that can drift.

### Caps and eligibility

- **Cap:** `te_history_sample_cap = 240` — twenty years of monthly samples, defined once (also written as the literal `241` in both pruners). One sample is added per month and `te_history_prune_samples` evicts exactly one when the list goes over, using `ordered_in_list { position = 0 order_by = te_history_sample_order }` so the oldest goes regardless of how the engine orders the list. `te_history_sample_order` **negates** the month index, because Jomini's `ordered_*` iterators sort descending — ordering by the raw index would put the *newest* sample at position 0 and the pruner would destroy the container it had just created. (`un_resolution_age_order` negates for the same reason.) The evicted container is `destroy_container`ed after `remove_list_variable`, never before, so the list never holds a dead reference.
- **Re-sorting after eviction:** `remove_list_variable` fills the removed slot with the list's *last* element instead of shifting, so one eviction moves the newest sample to the front of the list — and the chart draws raw `GetList` order. Confirmed from a 1865 save: every store at the cap held `[the newest k months][the oldest 240 - k]`, one break, while every store still under the cap was chronological. `te_history_prune_samples` therefore calls **`te_history_sort_samples`** after each eviction, which rebuilds the list oldest-first. It builds the sorted copy into `te_hist_tmp` and clears `te_hist` only once that copy is provably complete (`count >= 240`, exact because the pruner runs at precisely the cap) — clearing first would strand 240 containers no list points at. `te_history_sort_global_samples` does the same for the global series. Check any save with `python3 scripts/analysis/check_save_history_order.py`. **A store that stops recording keeps whatever order it froze in** — the re-sort only runs on an eviction, and a country that has dropped out of eligibility never evicts again. That is unreachable rather than broken: the charts live on that country's own journal entry, and the first month it records again puts the list over the cap, which evicts, which sorts. The checker labels those `frozen` and does not fail on them.
- **Eligibility:** `te_history_country_is_tracked` = `is_player = yes` OR `country_rank >= rank_value:major_power`. Identical for AI and human countries. `unrecognized_major_power` (rank_value 5) is deliberately out — those countries are numerous and rarely run the charted systems.
- **Dropping out:** a country that falls below the bar stops sampling and **keeps** its stored history; nothing prunes it early. It is bounded at 240 containers and dies with the country, so stale history costs at most one country's worth of samples. Re-entry resumes recording and the gap renders empty.
- **System gating:** a series also gates on its own system. `te_history_record_banking_samples` requires `te_banking_system_on = yes` and `has_journal_entry = je_banking_cycle`, so a country with banking switched off records no banking metrics at all. Under `banking_system_simplified` the three cycle series and the two rate series are still sampled; `mon_inflation` and `mon_fx` are not (they would flatline), and their two charts are hidden on the same trigger.

### Markers

`te_history_record_marker = { MARK = <key> }` sets `te_hist_mk_<key>` on the month's container and bumps `te_hist_mk`. The banking markers are recorded at the single shared site each policy already has — the `banking_effect_<button>` helpers, which both the AI's journal-entry buttons and the dashboard call — plus `banking_cycle_check_and_execute_crash` (`crash`) and `banking_contagion_crash_check` (`crash_contagion`).

The tooltip is built in script, not in `.gui`: `te_history_marker_tooltip` is a `scope = country` scripted GUI with `saved_scopes = { te_hist_sample }` whose effect is nothing but `custom_tooltip` lines, rendered from loc with `[GetScriptedGui('te_history_marker_tooltip').ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'te_hist_sample', ScriptContainer.MakeScope ).End )]`. Its policy branches quote the dashboard's existing `banking_dash_tt_<button>` keys, so a marker shows the policy's real name, description and `[GetStaticModifier(…).GetDesc]` effect list — **no number is retyped**, and retuning a policy updates its marker text automatically. `is_valid`/`ai_is_valid` are `always = no`, so neither a player nor the AI can ever execute it.

### Opening the GUI never writes state

Every recording helper body is wrapped in `hidden_effect`. That matters because the `banking_effect_<button>` helpers are also rendered as button tooltips; during a tooltip render the engine resolves scope links but never creates containers, so an unwrapped call would both spray text into the policy tooltip and read a scope that was never set. The chart itself has no effect at all: the only click targets are the collapse header and the three range buttons, and both write GUI-variable-system values that never reach the save.

### The chart

`plotline` cannot be used. Its `plotpoints` property only accepts the output of `GetTrendPlotPoints` / `GetTrendPlotPointsNormalized` / `GetDynTrendPlotPoints`, all of which take an engine-side `DataTrend`; no global function in the 1.14 data-type docs returns a `DataTrend`, and no `DataTrend` exists for a mod variable. So the chart is one vertical `progressbar` per stored month, over `datamodel = "[JournalEntry.GetCountry.MakeScope.GetList('te_hist')]"`.

- **Width.** The plot is a fixed-width `hbox`; each item is `size = { 0 84 }` + `layoutpolicy_horizontal = expanding` and no maximum width, so the *visible* bars divide the width between them (vanilla's `levels_progressbar` idiom). Switching to 1 year widens the bars instead of leaving 228 empty slots. At the 20-year end the 480px plot is split 240 ways — 2px a bar, so the series reads as a shape, not as countable months. An out-of-range item pays for its `visible` test and nothing below it, so the short ranges stay as cheap as they were before the cap doubled.
- **480 is not a round number, it is a divisible one.** Bar widths are integer pixels, and whatever the division leaves over the layout hands to the last item, i.e. to the newest month. 480 divides all three full-store bar counts exactly (240 / 60 / 12 → 2 / 8 / 40px), so no range leaves a remainder. The plot was 484px until #366, which is 4px over in all three cases: the newest month drew 6px against every other month's 2px on the 20-year view, three times as wide as its neighbour, and 12px against 8px on the 5-year one. Changing the plot width or adding a range means re-checking that `plot_width % bar_count == 0` for every range.
- **Ranges.** `GetVariableSystem` holds `te_hist_range` = `1`, `5` or `20`; unset means 20 years, which is the whole store, so the default view needs no per-bar test to pass. Each bar's `visible` compares `te_history_month_index` (now) minus its own `te_hist_i` against 12 / 60.
- **Signed series.** `te_history_bar_signed` stacks two half-height bars around a zero axis. The lower one uses vanilla's `double_direction_progressbar` "REVERSE HACK": swap `progresstexture` and `noprogresstexture` and give the bar a `min .. 0` range, so the coloured part is drawn from the far end and hangs down from the axis. Both halves clamp their value with `Max_CFixedPoint`/`Min_CFixedPoint`, so a positive month draws nothing below the axis and vice versa.
- **Two signed series deliberately do *not* use it** — the digital-currency policy-rate chart (−3…12) and the inflation chart (−4…12). `te_history_bar_signed` splits the plot 50/50 whatever its two ranges are, so on an asymmetric range a −2% month draws taller than a +2% one: a scale discontinuity at exactly the line those charts exist to watch. Both instead use `te_history_bar_unsigned` over **one linear span** with a manually drawn 0% line (a `zero_axis` blockoverride positioned from the plot margin plus the zero fraction of the plot height), and one colour above and below it — `te_history_bar_signed`'s green/red split would say deflation is the opposite of a problem. The offsets (23px and 27px) cannot be checked from the files; both are on the in-game checklist. If a new series is signed and its range is asymmetric, copy the inflation chart, not the momentum one.
- **Banded colour.** One chart does not use `te_history_bar_unsigned`: the banking cycle-value column is `te_history_bar_cycle_phase` (declared in `banking_history_widget.gui`, its only consumer), which draws the month in the colour of the phase its reading falls in. A progressbar's `color` *can* be an expression, but the only way to produce a `CVector4f` is `Select_CVector4f` over two colours that already exist as engine getters, and there is no `CVector4f` literal to nest into it — so the six colours are six progressbars in the same slot, each `visible` only inside its band, over one shared dark cover. Bands are the phase ladder from `banking_cycle_effects.txt` (10 / 25 / 40 / 60 / 75 / 88); the RGB values are vanilla's named text colours from `gui/textformatting.gui`, so a bar is literally the colour the phase's name is printed in.
- **Marker key.** `te_history_marker_legend` (in `te_history_chart.gui`) is a two-row key for the pips: the `information.dds` pip, drawn on any month with a marker, and the `warning.dds` pip, drawn on a crash. The crash row is a `block` with a default body, so a series that never records a crash overrides `"crash_marker"` to nothing.
- **Empty state.** `IsDataModelEmpty` on the same list shows "nothing recorded yet" — what an existing save sees until its first monthly pulse. `te_hist_since` prints the oldest retained sample's date.
- **Collapsed by default.** The section header toggles a GUI flag named for the *open* state (the inverse of the dashboard's collapsed flags), so a player who never opens it never pays for the bars.

### How to add a series

1. **Sample it.** From the system's own monthly pulse, in country scope:
   `te_history_record_sample = { METRIC = res_stock VALUE = var:st_res_stock_grain }`
   Wrap it in the system's own gate (game rule + journal entry) the way `te_history_record_banking_samples` does. For a world-level series use `te_history_record_global_sample` instead; it writes to the global list and needs no eligibility trigger.
2. **Chart it.** Instantiate `te_history_chart` with blockoverrides for `chart_title`, `chart_legend`, `bar_tooltip` and `bar_body`. Use `te_history_bar_unsigned` for a one-sided metric (override `values` with `min`/`max`/`value` and `color`), `te_history_bar_signed` plus a `zero_axis` override for a signed one whose range is **symmetric** — for an asymmetric signed range use `te_history_bar_unsigned` over the whole span with a drawn zero line instead (see the two exceptions under **The chart** above). The bar body's `visible` must be `[ScriptContainer.HasVariable( 'te_hist_v_<METRIC>' )]` so months without that metric stay empty.
3. **Localize it.** A title, a legend, a `…_row` line and a tooltip key modelled on `te_hist_tt_bank_value` — the tooltip key is where the date line and the marker block are composed.
4. **Mark it, if the series has turning points.** `te_history_record_marker = { MARK = <key> }` at the single site the event already has, plus one branch in `te_history_marker_tooltip`.
5. **If it has no markers of its own, hide the pips.** Markers live on the month's shared sample container, so every chart of a country's store draws every system's pips (the banking policy "i" and crash "!" icons). A series whose tooltip does not explain them should add `blockoverride "marker_pips" {}` to its `te_history_chart` instance. The UN authority, global-warming and colonial charts do; the banking and cultural-hegemony charts, which record and explain their own markers, do not.

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
- **Scripted Buttons:** `common/scripted_buttons/space_race_buttons.txt` — Safe/Ambitious approach, funding increase/decrease. 32 buttons (4 × 8 entries), all carrying `is_ai = yes` so the vanilla grid is hidden from humans; each delegates its `visible` / `possible` / `effect` to a shared `$MILESTONE$`-parameterized helper.
- **Journal-entry widget:** `gui/journal_entry_widgets/space_race_widget.gui` — one milestone panel instanced on all nine entries; handlers in `common/scripted_guis/space_race_sguis.txt`, branching text in `common/customizable_localization/space_race_custom_loc.txt`. Full description: `docs/systems/journal_entry_systems.md` → Space Race → Milestone Panel.
- **Debug console:** `events/te_debug_space_race_events.txt` + `common/scripted_effects/te_debug_space_race_effects.txt` — `event te_debug_space_race.1` reaches every panel state. Option j fires one real setback event through the themed dispatcher (most advanced running milestone); option k has the two most prestigious other powers both report Suborbital Flight, to check that two notifications inside the 14-day delay give two correct popups.
- **Scripted Effects:** `common/scripted_effects/space_race_effects.txt` — milestone completion, failure, cleanup, colony establishment (`sr_establish_colony_effect`), stage advancement (`sr_check_colony_stage_effect`)
- **Scripted Triggers:** `common/scripted_triggers/space_race_triggers.txt` — has_space_program, is_pursuing, can_start, failure_cooldown
- **On Actions:** `common/on_actions/space_race_on_actions.txt` — yearly random events for all in-progress and cross-system events; the monthly country pulse (inactive-milestone cleanup, entry-modifier backstop, failure cooldown); `on_civil_war_won` (a revolution's winner gets its country rewards back)
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
- **Approach Choice:** Safe vs Ambitious, per entry. The base monthly setback risk is a per-milestone script value — `sr_base_risk_<m>`, 5 for suborbital rising to 10 for solar colonization — and `sr_risk_pct_<m>` applies `country_space_race_risk_mult` to it (Safe contributes -0.5, Ambitious nothing). **The monthly roll and the widget's "Setback risk" line read the same script value**, so they cannot disagree; `sr_risk_shown_<m>` is the same figure with a zero while the cooldown is running. There is no longer a `sr_base_risk` proxy variable or a `RISK =` parameter — a number copied into a variable one statement before it is rolled is readable by nothing else, which is why the risk could not be shown at all before.
- **Funding Levels:** 0 to `sr_max_funding_level` (base 3, increased by `country_space_race_max_funding_add` modifier from techs like `reusable_rocketry` +1, `space_colonization` +2). Each level costs innovation (-15/level via `sr_space_program_cost` consolidated modifier). Funding and approach are **per-JE** — you can fund moon landing heavily with safe approach while running a cheap ambitious probe.
- **Per-JE Cost:** each active milestone's journal entry carries `sr_space_program_cost` with `multiplier = sr_<m>_cost` (that milestone's funding level + approach overhead: safe=1, ambitious=2, times an era factor from 1x for suborbital to 12x for the interstellar probe). Re-posted by `sr_recalculate_cost` whenever funding or approach changes. A single consolidated `sr_total_space_cost` script value used to exist for this and is gone — nothing read it after the per-JE split.
- **Failure:** Reduces the failed milestone's progress (×0.75 for ambitious, ×0.85 for safe) and, in most options, a flat amount on top; ambitious failures add a 6-month cooldown (`sr_mission_failure_effect`) and decaying negative modifiers. All of it is applied by the failure event's chosen option, not in the pulse. Cooldown is global (decremented once via `on_monthly_pulse_country`, not per-JE). Does NOT permanently block — just wastes time.
- **Known behaviour — the cooldown shields, it does not pause.** The cooldown check sits *below* the `change_variable = { name = sr_progress_<m> add = sr_progress }` line (`space_race_effects.txt:25`), so a programme inside its cooldown accrues progress at full rate with zero chance of a setback. The widget displays this as "shielded" rather than inventing a pause. Not changed; recorded so it can be judged deliberately.
- **Known behaviour — no approach means a flat drift.** With neither `sr_safe_<m>` nor `sr_ambitious_<m>` set the pulse adds `sr_progress_drift` (0.5), not `sr_progress`. The widget quotes the drift rate in that state (`sr_pace_rate_<m>`) so the number on screen is the number being added.
- **Failure events know which milestone failed.** The pulse calls `sr_fire_ambitious_failure_event = { MILESTONE = <m> }` / `sr_fire_safe_setback_event = { MILESTONE = <m> }`, which first `save_scope_as = sr_setback_<m>`. Saved scopes travel with `trigger_event`, so that marker is how the pool picks a theme (`.13` only for a probe, `.14/.17/.71` only for Moon base / Mars / colonization, `.15` only for the Moon landing, …; shared triggers `sr_setback_is_deep_space_probe` / `sr_setback_is_crewed_outpost`) and how every option's helper — progress loss, `sr_boost_setback_milestone`, `sr_temporary_safety_review_effect`, `sr_clear_failed_milestone_flags` — finds its one milestone. Two journal entries failing in the same month cannot mix: each entry's pulse is its own script run. **Never dispatch twice in one script run** (the second event would carry both markers); `te_debug_sr_fire_setback` picks one milestone for that reason. A failure event with no marker at all (open in a save from before the marker existed, or fired from the console) falls back to the old behaviour: the first helper an option runs calls `sr_resolve_setback_markers`, which marks every milestone whose `sr_failed_<m>` is raised.
- **Failure Flags:** `sr_failed_<milestone>` is still raised by the pulse — it is the "setback not yet answered" bookkeeping — and each option clears the flag of its own milestone. Nothing reads it to decide *which* milestone an effect applies to any more.
- **"A more cautious approach"** (`.10.b`, `.15.c`) switches the failed milestone to the safe approach through `sr_switch_setback_milestone_to_safe` → `sr_effect_safe`, the journal-entry button's own body, so the approach flags, the approach modifiers (risk and speed), the cost and the widget status follow (`sr_mission_failure_effect` re-derives the status after starting the cooldown, via `sr_refresh_milestone_statuses`). For solar colonization only while it is running, as the panel's own controls are.
- **Completion texts** (`.1/.3/.6/.7/.8`, and the flavour of `.3/.7`) claim a world first only under `has_variable = sr_was_first_<m>`; otherwise a `_later` variant ("…joins the nations that have…"). The rewards already split first from later (`sr_apply_milestone_reward_base`).
- **Achievement notifications (`.20`).** `sr_notify_milestone_achievement` adds the achiever's capital to a per-milestone *list* on every receiver (`sr_notify_achievers_<m>`) and queues one `.20`; each popup takes exactly one entry (`sr_take_milestone_notice_base`, an `else_if` chain) — the world first's entry before any other, since the list has no reliable order — and reads "world first" from the achiever's own `sr_was_first_<m>`. Two completions inside the 14-day delay — different milestones, or the same milestone by two countries — give two popups, each naming its own achiever, and option b's relations go to that achiever.
- **Programme loss (`.76`).** A lowered space-programme production method, or a lost / demolished building, fails every milestone its tier was carrying, and the journal entries notice on their own 4-day update schedule. Each `on_fail` calls `sr_report_program_loss = { MILESTONE = <m> }`: it records the milestone and only the first queues `.76`, five days out, so one change gives one report whose option tooltip lists the closed programmes. The text is read at fire time: building still there → a refit (a choice, the original "Program Discontinued" text); building gone → "The Silent Gantry", an involuntary loss.
- **Solar colonization "running".** Its journal entry stays open, frozen, while `pm_solar_colonization` is switched off (and after the last colony). `sr_solar_colonization_running` (active + production method on + not completed; also the gate of its four controls) is what events `.35/.44/.48/.49/.50/.53/.55` and `sr_boost_active_milestones` read, so no event narrates or moves a frozen programme. `.35` ("keep the settlements supplied") also needs a real colony (`sr_has_space_colony`).
- **Foreign powers in the text are real.** `.26` ("When Politics Reaches Orbit") names a space power our relations with have really soured (`sr_is_estranged_space_power`: rivalry either way, or relations at cold or worse) and is only in the safe pool while one exists. `.52` (joint orbital station) needs another UN member that has reached orbit (`sr_is_station_partner`), names it, and is worded as our own space agency's proposal rather than a claim about what that country did.
- **Moon Landing Site:** Special event (space_race_events.5) offers Shackleton Crater (high risk, science windfall) vs Equatorial Plain (low risk, modest rewards).
- **Interstellar Probe:** Launches a probe to Alpha Centauri. On completion, spawns a passive `je_space_race_interstellar_results` JE that ticks 1/month for 132 months (~11 years) using a separate `sr_interstellar_transit_progress` variable (not shared `sr_milestone_progress`). When complete, fires event 60 (Interstellar Probe Data Received) which randomly selects one of 30 possible discoveries across 4 categories:
  - **Category I: Dead Worlds & Data** (40% chance, 8 results) — Barren worlds, asteroid maps, stellar remnants. Grants `sr_probe_dead_worlds_data` (modest prestige/research/innovation).
  - **Category II: Astrophysical Wonders** (30%, 7 results) — Ringed terrestrials, global oceans, runaway greenhouses. Grants `sr_probe_astro_wonders_data` (good prestige/research/innovation/cultural pull).
  - **Category III: Biological Discovery** (20%, 9 results) — Atmospheric biosignatures, alien vegetation, exotic biochemistry. Grants `sr_probe_biological_data` (major prestige/research/innovation/cultural pull).
  - **Category IV: Intelligence & Tech-signatures** (10%, 6 results) — Orbital debris, technogenic gases, artificial light. Grants `sr_probe_intelligence_data` (exceptional prestige/research/innovation/cultural pull).
  - Discovery selection uses two-stage `random_list`: first picks category by weight, then picks specific result uniformly within category. Each result event (601–630) records itself globally on first discovery (`sr_record_probe_result`: `sr_probe_found_<id>` = the discoverer). A later nation drawing the same result gets opening/closing lines that confirm the first finder's discovery, named, instead of "unprecedented data"; the rewards are the same (none is a first-discovery reward). Result events use triggered_desc blocks for the confirmation variant and the result-specific description.
- **Solar System Colonization (Repeatable):** Each completion establishes one colony at a random unclaimed location in the current stage. Colonies are tracked via global variables (`sr_colony_*`), making them first-come-first-served across all nations. Stage advances when all locations in a stage are claimed. Goals increase per stage (100/120/140/160/200). JE only sets `sr_completed_solar_colonization` after all 34 colonies across 5 stages are claimed.
  - **Stage 1:** Mars (5) + Asteroids (5) = 10 colonies
  - **Stage 2:** Jupiter system (6) + Venus clouds (1) = 7 colonies
  - **Stage 3:** Mercury (1) + Saturn moons (5) = 6 colonies
  - **Stage 4:** Uranus moons (4) + Neptune moons (2) = 6 colonies
  - **Stage 5:** Kuiper Belt/Oort Cloud (5) = 5 colonies
- **Late-Game Economic Rewards:** Interstellar Probe grants one of 4 category-specific modifiers (see Interstellar Probe above), all colonies complete grants `sr_solar_system_trade`.
- **Progress Sources:** Base rate + Aerospace Industry levels + Space Elevator + Extraplanetary Base + UN Space Partnership + SpaceX company + funding + tech bonuses.
- **A revolution's winner continues the programme** (`docs/audits/civil_war_inheritance_audit.md` F5, #464). The winner inherits the loser's variables but none of its modifiers, and every entry it inherits active runs `immediate` again. So:
  - **`immediate` only creates what is missing.** Progress and funding are guarded with `has_variable`, so a milestone at 90 % stays at 90 %. That is safe for the native progress bar because an inherited record keeps the loser's bar: start date, baseline and goal are copied, not evaluated again (the German-revolution saves' `je_global_warming`: baseline 0.1 and goal 4.0 on the winner with the anomaly at 1.18). For a same-record re-activation inside a month (before the monthly cleanup clears the progress), `goal_add_value` subtracts the progress so the goal stays at `sr_<m>_goal`. Solar colonization's bar restarts at every colony, so it keeps progress only while it holds a colony (it cannot deactivate then); a colony-less programme still restarts, and a finished one is not re-opened. `je_space_race_interstellar_results` keeps its transit months the same way.
  - **Choice events are asked once per milestone** (`sr_<m>_choice_made`, checked in `immediate` and in the event's `trigger`). Before, a re-activation or an inherited entry asked again and could leave two answers and two modifiers.
  - **Every reward is rebuilt from a variable.** Milestone rewards (`sr_first_<m>` / `sr_<m>`) from `sr_completed_<m>` / `sr_was_first_<m>`, and the probe result (`sr_probe_*_data`, recorded as `<modifier>_held` by `sr_grant_probe_data`), come back at `on_civil_war_won`. Entry modifiers come back from each entry's `immediate` (`sr_sync_<m>_entry`) and, as a backstop, the monthly country pulse (`sr_sync_space_race_entries`): the approach modifier from `sr_safe_<m>` / `sr_ambitious_<m>` (and a stale one with no approach selected is removed), the choice modifier from the choice variable, the 68 colony specialisations from `<modifier>_held` (`sr_grant_colony_modifier`), and `sr_solar_system_trade` from `sr_completed_solar_colonization`. The monthly pulse also records a probe result or colony modifier granted before the record existed, so old saves migrate themselves. A loyalist winner still holds every modifier, so all of it is a no-op there. Timed modifiers (the completion events' themed rewards, failure penalties, the safety review) are not restored.

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
| `sr_failed_<m>` | Per-JE "setback not yet answered" flag (set in the pulse, cleared by the failure event's option). Which milestone an event acts on comes from `scope:sr_setback_<m>`, not from this flag |
| `sr_interstellar_transit_progress` | Interstellar probe transit progress (passive JE, not per-JE) |
| `sr_<m>_last_status` | Widget display state, 0-4. Single derivation site: `sr_set_milestone_status_base`. Absent when the milestone is not running. |
| `sr_<m>_setbacks` | Lifetime setback count for that milestone, shown by the widget. Incremented in `sr_count_setback_base`. |
| `sr_failure_cooldown` | Global months until failure can occur again (decremented once/month via on_action) |
| `sr_progress_boost` | **Proxy variable** — set before calling `sr_boost_active_milestones` (every running milestone) or `sr_boost_setback_milestone` (the failed one) |
| `sr_notify_achievers_<m>` | **Variable list** on each receiver: capitals of achievers whose `.20` popup is still pending, one entry per completion |
| `sr_program_lost_<m>` / `sr_program_loss_report_queued` | A milestone closed by a lost/lowered launch complex, waiting for the single `.76` report |
| `sr_moon_site_shackleton/equatorial/tranquility/far_side` | Moon landing site choice |
| `sr_orbital_*`, `sr_probe_target_*`, `sr_moon_base_*`, `sr_mars_direct/orbital_first/robotic` | The other milestones' choice-event answers; each drives an `sr_choice_*` modifier on the running entry, rebuilt from it by `sr_sync_<m>_entry` |
| `<modifier>_held` | The reward modifier `<modifier>` was granted: `sr_probe_*_data_held` (country), `sr_colony_*_held` (solar colonization entry). Rebuilt from after a revolution |
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
| `sr_probe_found_<601–630>` | The country whose interstellar probe first returned that result |
| `sr_colony_*` (34 variables) | Individual colony claimed flags (e.g. `sr_colony_valles_marineris`, `sr_colony_europa`, `sr_colony_sedna`) |

### Important Notes
- **`building_space_program` is a monument** (`expandable = no`, single level). DO NOT check `level >= 3` etc. on it — use `building_aerospace_industry` for level-scaled bonuses instead.
- **Colony modifiers are JE-scoped.** All 68 colony modifiers and `sr_solar_system_trade` are applied to `je:je_space_race_solar_colonization`, not to the country directly. The colonization JE stays alive indefinitely while colonies exist (passive mode with hidden buttons when all 34 colonies are claimed). This means colony modifier effects still apply to the country, but display in the JE panel. Grant one only through `sr_grant_colony_modifier`, which also records it as `<modifier>_held`: a revolution's winner inherits the entry with no modifiers, and `sr_sync_solar_colonization_entry` rebuilds them from those records.
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
  hops to the monument's `state`) → `monument_events.2`, a **`state_event` with
  `placement = ROOT`** so the ceremony is placed on the state that built the monument rather
  than the capital. ROOT is that state, so `activate_production_method` targets it directly and
  every country-level gate goes through `owner`. Its `immediate` saves `scope:monument_state`
  purely so the loc can name the state. Recurring flavour events 3–10 are still country events,
  dispatched from `monument_events_on_action` on `on_monthly_pulse_country`.
- **Re-ask guard.** The ceremony's `trigger` requires a monument in the state still on
  `pm_monument_undedicated`. `has_building` alone would re-open the question every time an
  existing monument gained a level.
- **Option gating: hide vs tilt.** An option `trigger` *hides* the row and is reserved for
  dedications a country has no business offering — state atheism (religious), `law_industry_banned`
  (industrial), and the four technology gates. Everything else stays visible and is steered by
  `ai_chance` instead. The civic dedication is never hidden: one `pm_monument_civic` is offered
  under three mutually exclusive wordings — "to the republic", "to the Crown", "to the nation" —
  partitioned by `monument_government_is_republican` / `monument_government_is_crowned` in
  `common/scripted_triggers/monument_triggers.txt`. The third skin is written as `NOT` of both,
  so a governance principle added later still gets a civic dedication rather than losing the option.
- **Option tooltips are hand-written.** Each option wraps its `activate_production_method` in a
  `custom_tooltip` whose `monument_events.2.*.tt` string spells out that dedication's modifiers,
  because there is no `GetProductionMethod('key')` global promote to render a PM's effects in loc
  (see `docs/guides/event_creation_guide.md`). Modifier *names* come from `$modifier_key$`
  substitution so they follow renames; the *numbers* are hand-kept in sync with
  `grand_monument_pms.txt`, which carries a TOOLTIP MIRROR header comment saying so.
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
| `amendment_national_champion_exemption` | `extra_law_events.29` option e (option a remains the permanent variant) | 48 / 120 | `extra_law_events.85` |
| `amendment_corporate_data_exemption` | `extra_law_events.31` option e (option a remains the permanent variant) | 12 / 36 | `extra_law_events.86` |

The `has_amendment` guards on events 29/31/58 make the permanent and temporary variants mutually exclusive within one enactment. The expiry events re-derive `sunset_law` from `active_law:<lawgroup>` and `industrialists_ig` in `immediate`, and are not in any checkpoint pool. Deferred from issue #278: a financial-regulation phase-in (the three laws' penalties are structurally different — numeric, none, boolean lock) and a wartime rules-of-war clause (no per-country war-start on-action; would need a timeout on an already-active law).

## On-Actions Reference

The mod uses 23 on-action files under `common/on_actions/`. These wire mod logic into engine hooks — either **pulse-based** (fires periodically for all relevant scopes) or **immediate** (fires the instant a specific game event occurs).

### File Index

| File | Purpose | Hook Type |
|------|---------|-----------|
| `extra_on_actions.txt` | Central hub: pulse wiring, dynamic modifiers, immediate triggers, company cleanup | Mixed |
| `te_construction_market_on_actions.txt` | Construction-market site re-placement on diplomatic/territorial and building-lifecycle changes, plus its yearly heartbeat | Mixed |
| `headlines.txt` | "World first" tech notifications (`on_acquired_technology`) | Immediate |
| `law_events_on_actions.txt` | Law enactment checkpoint events (advance/debate/stall) | Immediate |
| `amendment_on_actions.txt` | Temporary-amendment expiry follow-up events (`on_amendment_timeout`) | Immediate |
| `langreform_events_on_actions.txt` | Language reform yearly random events | Pulse |
| `minor_events_on_actions.txt` | Miscellaneous yearly random events | Pulse |
| `repeatable_events_on_actions.txt` | Generic repeatable yearly events | Pulse |
| `social_tensions_on_actions.txt` | Social/political tension yearly events | Pulse |
| `space_race_on_actions.txt` | Space race in-progress and cross-system yearly events | Pulse |
| `te_monetary_on_actions.txt` | Monetary policy: world reference rate and (phase 3) the world rate, the monthly country update, the yearly growth snapshot, the country-creation hooks (see **Monetary Policy (phase 1)**), and — phase 5 — the anchored-GDP refresh on the global pulse, the yearly arrangement scan + seigniorage re-sum, `on_country_default` (the guarantee is called) and `on_become_subject` (currency boards) | Mixed |
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
- `te_homeland_monthly` — dynamic homeland progress (monthly state pulse)
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
- Also used by the construction market (`te_construction_market_on_actions.txt`) to remove a finished state's construction site.

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

**`on_country_formed`** (Root = the new country), **`on_country_released_as_{independent,own_subject,overlord_subject,company_subject}`, `on_revolution_start`, `on_secession_start`** (scope:target = the released or uprising country):
- `agdiff_backfill_on_country_formed` / `agdiff_backfill_on_released_country` — give the new country, or the rebels, every agricultural-diffusion modifier whose world-first has already fired (`agdiff_backfill_diffusion_for_country`, stateless). The broadcast only reaches countries that exist at the time, and a revolution's winner inherits no modifier from the loser.

**`on_civil_war_won`** (Root = the winner):
- `agdiff_on_civil_war_won` — the backfill again, plus what is left of a lost `agdiff_first_mover_prestige` (from `agdiff_first_mover_month`, recorded with the title; not restored for titles won before that variable existed), and re-points `first_<tech>_country` from the dead loser to the winner.

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
2. **Player Interaction:** the **Colonial Stability widget** (`gui/journal_entry_widgets/colonial_empire_widget.gui`) is the human surface — conditions, the three programmes, the three decolonization decisions, and two history charts. The 9 scripted buttons behind it carry `is_ai = yes` and are the **AI's** only path in; both surfaces call the same `colonial_empire_possible_*` / `colonial_empire_effect_*` helpers. Full reference: `journal_entry_systems.md` § Colonial Stability Widget.
3. **Events:** 21 events fire from `decolonization_events_on_action` (monthly pulse), covering colonial negotiations, crackdowns, releases, GP stance choices, post-independence transitions, and the Suez Crisis model. `decolonization_events.400` / `.401` are the confirmation popups the three decisions open — each previews candidates and offers a "Reconsider" option, so nothing is released by pressing a button.

### Files

| File | Purpose |
|---|---|
| `common/journal_entries/je_colonial_empire.txt` | JE definition, bar, widget mounts, monthly pulse, outcomes |
| `common/scripted_progress_bars/extra_progress_bars.txt` | `colonial_stability_bar`; its `monthly_progress` consumes the 21 leaf script values plus the monthly cap |
| `common/script_values/colonial_empire_values.txt` | Colony counts, `colonial_stability_term_*` leaves, `colonial_stability_drift_*` groups, cost and display values |
| `common/scripted_triggers/colonial_empire_triggers.txt` | Macro-regions, `is_overseas_colonial_state`, the 9 `colonial_empire_possible_*` button gates |
| `common/scripted_buttons/colonial_empire_buttons.txt` | 9 AI-only JE buttons; `possible` / `effect` delegate to the shared helpers |
| `common/scripted_effects/decolonization.txt` | `form_decolonized_country`, JE cleanup, the 9 `colonial_empire_effect_*` button actions |
| `common/scripted_effects/colonial_empire_display_effects.txt` | `colonial_empire_refresh_display` — the single site deriving all widget display state |
| `common/scripted_guis/colonial_empire_sguis.txt` | 5 handlers backing the widget (2 guards, 1 text renderer, 2 op-coded actions) |
| `common/customizable_localization/colonial_empire_custom_loc.txt` | Band names, status line and phase-modifier line, keyed on `var:colonial_empire_tier` |
| `common/scripted_effects/te_history_colonial_effects.txt` | `te_history_record_colonial_samples` — the two chart series |
| `common/scripted_effects/colonial_collapse_effects.txt` | AI country absorption for tiny post-colonial remnants |
| `common/laws/colonial_empire_law_injections.txt` | Per-law colonial-stability and programme-effectiveness contributions |
| `common/modifier_type_definitions/colonial_empire_modifier_types.txt` | The four `country_colonial_*` aggregate modifier types |
| `common/on_actions/extra_on_actions.txt` | `decolonization_events_on_action` wiring |
| `events/decolonization_events.txt` | All 21 decolonization events plus the `.400` / `.401` confirmations |
| `events/te_debug_colonial_empire_events.txt` | Console harness: `event te_debug_colonial_empire.1` / `.2` |
| `common/static_modifiers/extra_modifiers.txt` | 40+ decolonization modifiers |

### Stability Bar Formula (`colonial_stability_bar.monthly_progress`)

**This table is the formula.** Every term is a named leaf script value in `common/script_values/colonial_empire_values.txt` (country scope), and the bar's `monthly_progress` is nothing but 21 unconditional `add = { desc = "<tooltip key>" value = owner.<leaf> }` lines, plus a 22nd, last line for the monthly cap (below). Each leaf returns 0 when its gate is false. The widget and the history charts read the **same** leaves through the nine `colonial_stability_drift_*` group sums, so there is exactly one place each number lives.

To retune a term, change only its leaf. To add one: add a leaf, add it to its group, add one `add` line to the bar with a `desc` key, and add a row here.

| Leaf (`colonial_stability_term_…`) | Group | Gate | Value | Tooltip key |
|---|---|---|---|---|
| `_base` | base | — | **-0.5** | `colonial_base_drift_tt` |
| `_laws` | laws | — | `modifier:country_colonial_stability_drift_add` | `colonial_law_aggregate_tt` |
| `_ig_landowners` | igs | Landowners powerful | **+0.3** | `colonial_ig_landowners_strong_tt` |
| `_ig_armed_forces` | igs | Armed Forces powerful | **+0.2** | `colonial_ig_armed_forces_strong_tt` |
| `_ig_intelligentsia` | igs | Intelligentsia powerful | **-0.4** | `colonial_ig_intelligentsia_strong_tt` |
| `_ig_unions` | igs | Trade Unions powerful | **-0.3** | `colonial_ig_unions_strong_tt` |
| `_overreach` | overreach | `colonial_overreach_ratio > 0` | ratio × **-0.4** | `colonial_overreach_tt` |
| `_gp_rank` | rank | great power | **+0.3** | `colonial_gp_rank_bonus_tt` |
| `_non_gp` | rank | not a great power | **-0.5** | `colonial_non_gp_penalty_tt` |
| `_gp_condemnation` | gp | — (0 with no condemners) | `colonial_gp_condemnation_weight` × **-0.6** | `colonial_gp_condemnation_tt` |
| `_gp_high_pressure` | gp | condemners' prestige share ≥ 1/3 | **-1.0** | `colonial_gp_high_pressure_tt` |
| `_gp_extreme_pressure` | gp | condemners' prestige share ≥ 2/3 | **-2.0** | `colonial_gp_extreme_pressure_tt` |
| `_gp_support` | gp | — (0 with no supporters) | `colonial_gp_support_weight` × **+0.3** | `colonial_gp_support_tt` |
| `_garrison` | policies | Garrison active | `modifier:country_colonial_garrison_effectiveness_add` | `colonial_garrison_aggregate_tt` |
| `_assim` | policies | Assimilation active | `modifier:country_colonial_assim_effectiveness_add` | `colonial_assim_aggregate_tt` |
| `_invest` | policies | Investment active | `modifier:country_colonial_invest_effectiveness_add` | `colonial_invest_aggregate_tt` |
| `_low_acceptance` | acceptance | low-acceptance colonies > 0 | count × **-0.4** | `colonial_low_acceptance_tt` |
| `_high_acceptance` | acceptance | high-acceptance colonies > 0 | count × **+0.5** | `colonial_high_acceptance_tt` |
| `_war` | domestic | at war | **-0.5** | `colonial_war_penalty_tt` |
| `_revolution` | domestic | revolution | **-1.0** | `colonial_revolution_penalty_tt` |
| `_turmoil` | domestic | `country_turmoil > 0.05` | turmoil × **-2.0** | `colonial_turmoil_penalty_tt` |
| `_cap` (**last line**) | — (not in a group) | sum outside ±`colonial_stability_drift_cap` | clamp(sum, ±1.667) − sum | `colonial_drift_cap_tt` |

**Great-power terms scale with relative prestige.** Each condemning or supporting great power is weighted by its prestige divided by the empire's (floored at 1), clamped to **[0.25, 2.0]** — `colonial_gp_condemnation_weight` / `colonial_gp_support_weight` sum those weights. A peer great power therefore contributes the table's figure (-0.6 / +0.3), one with double the empire's prestige or more contributes twice that, and one with a quarter or less contributes a quarter. Net effect: the most prestigious empires shrug off condemnation from lesser powers, while small colonial holders (Portugal, Belgium, the Netherlands) feel superpower condemnation at up to -1.2/month each.

**The two escalations fire on prestige share, not head count.** `colonial_gp_condemner_prestige_share` is the condemners' combined prestige divided by `colonial_gp_prestige_pool` — the prestige of every great power *plus the empire itself*, counted even when it is not a great power. At **≥ 1/3** `_gp_high_pressure` applies a flat -1.0; at **≥ 2/3** `_gp_extreme_pressure` adds a further -2.0 (both apply, -3.0 total). Because the empire sits in the pool, a dominant empire is hard to isolate, while a minor one reaches the thresholds as soon as a few big powers condemn it. The pool is great powers rather than world prestige on purpose: condemners are a subset of the great powers that excludes the empire, and great powers together hold well under all of world prestige, so a two-thirds world share would practically never fire. `colonial_empire_refresh_display` snapshots the share into `colonial_empire_condemner_share` for the widget's International Pressure section. The event and button AI weights keyed on `colonial_gp_condemners_count >= N` are unchanged — they count powers, not pressure.

**Monthly cap, applied last.** However large the sum of the 21 terms, the bar moves at most **±`colonial_stability_drift_cap` = 1.667** a month (100 ÷ 60), so crossing the whole bar takes at least five years either way. The cap acts on the *total*, after everything is summed — not on any one term — so a sudden spike (a superpower condemning a tiny colony) cannot empty the bar in months, but a big enough sum still outweighs the empire's programmes and it has to change the inputs (win the great power over, integrate or release colonies) to turn the trend. The bar applies it as the `_cap` row: `colonial_stability_drift_total` (capped) minus `colonial_stability_drift_uncapped`, which is 0 inside the cap, so the hover shows how much the cap absorbed. `colonial_stability_drift_total` is now the capped figure everywhere it is read (the `colonial_empire_d_total` snapshot and the signed history chart, rescaled to ±2); the widget's headline is `colonial_stability_drift_total_display` and its breakdown ends with `colonial_stability_drift_cap_display`. The cap leaf evaluates the uncapped sum twice, i.e. every leaf about three times a month — acceptable at monthly cadence.

**Contributions that are not rows above** reach the bar through `country_colonial_stability_drift_add` (the `_laws` leaf) and surface inside that line's own `GetValueWithBreakdownFor` breakdown: every contributing law (Colonial Affairs, Minority Rights, Citizenship, Distribution of Power, Free Speech, Internal Security), the era techs (`globalization` **-1.5**/mo, `knowledge_economy` **-0.75**/mo), and the timed `colonial_stability_positive_event` / `_negative_event` modifiers. Programme effectiveness likewise aggregates a `base_values` baseline plus per-law contributions.

**Reading it in game:** hovering the bar shows all 21 terms and the cap with their current values — `GetPeriodicProgressBreakdown`, generated by the engine from the `desc` keys above. The widget shows the nine group sums, the cap row and the projected (capped) total.

**Design intent:** A typical GP with 5 colonies nets roughly -0.5 to -1.0/month even with programmes active. Only great powers with few, well-integrated colonies and little GP condemnation can stabilize. The era techs make holding colonies nearly impossible late.

### Events (1-21)

Events 1-15 handle the core colonial cycle: negotiations, crackdowns, releases, GP stances, cultural identity, post-independence economics, nationalization.

**Post-Independence Events (16-21):**
- **Event 16 "The Partition Question"** — New nations near neighbors with shared heritage can demand unification (claims+tension), propose federation (truces+goodwill), or accept borders (stability).
- **Event 17 "Whose Country Is This?"** — Border disputes between two recently-formed nations. Options: press claims, seek mediation, accept borders.
- **Event 18 "The Strongman's Promise"** — Political instability in new nations. Options: military coup (authority+SoL loss), democratic transition (legitimacy), one-party state (authority+research).
- **Event 19 "The Crisis" (Suez model)** — GP reacts when a former colony nationalizes assets. Options: military intervention (infamy 15, **triggers Event 20** for all other GPs), economic sanctions (infamy 5), accept outcome. This is the flagship "interactive" GP event.
- **Event 20 "Gunboats in the Harbor"** — Other GPs respond to military intervention. Options: condemn (+moral authority, relations penalties to intervener), support intervention, stay neutral. **Not in on_actions** — triggered directly by Event 19 option A.
- **Event 21 "The Non-Aligned Path"** — New nations choose between competing superpowers or non-alignment.

**Choices made by the other party (2026-09, event-agency work, #427):**
- **Former colonies choose first.** The overlord's pool slots that used to fire `.5` (closer ties) and `.6` (reparations) now fire precursors on the former colony: **`.60`** (propose ties) and **`.61`** (demand reparations). The overlord hears only if the colony asked.
  - Lockout variables on the overlord replace the old cooldowns: `decol_ties_overture_cd` and `decol_reparations_demand_cd`.
  - Reparations are a real transfer. The claim is fixed at demand time: 10 % of the payer's yearly revenue, capped at 10 % of the claimant's GDP (`decol_reparations_value`).
- **Truces need consent.** `.16.b` (federation) and `.17.c` (border) ask the neighbour first, through **`.62`** / **`.63`**, instead of imposing a 60-month truce on it.
- **Pressure comes from real stances.** `.2`'s pressuring power is picked only from great powers carrying `gp_anti_colonial_stance`. The General Assembly flavour appears only once the decolonization UN regime exists.
- **`.20` names the real intervener and victim,** saved by `.19.A`, instead of re-picking them.
- **Only colonial subjects count.** `.1`/`.2`/`.3`/`.8`/`.11` iterate `is_qualifying_colonial_subject` only.
- **`.206`'s "by decision" epilogue** needs a chosen release. `decol_record_chosen_release` counts them (`decol_chosen_releases`); otherwise a neutral variant shows.

**Former colonies, colonial wars and notices (2026-09, #430):**
- **Every freed colony is a former colony.** `decol_mark_former_colony` (`decolonization.txt`) sets `var:former_overlord` (untimed) and `recently_decolonized` (7300 days), the shapes the vanilla release actions set in `te_construction_market_on_released_*`. `apply_decolonization_path` calls it for every country `form_decolonized_country` creates, and so do the `make_independent` options `.1.c`, `.1.d_neo`, `.3.a` and `.3.c`. What this makes reachable is the precursors `.60` / `.61` and, through them, `.5` / `.6`. The post-independence events (`.7`, `.15`, `.16`, `.17`, `.18`, `.21`) also require `je_colonial_empire` on the former colony itself, which a freed colony almost never holds, and `.19` needs `.15`'s nationalization modifier. So those stay out of reach for any freed colony, including one released by the vanilla actions. That gate predates the helper; whether it should read the decolonization rule instead is an open question.
- **`.51` (Conscription Crisis) fires only in a colonial war.** The trigger is `decol_fighting_colonial_war` (`colonial_empire_triggers.txt`), used by both the event and its pool entry. It is true when the country is at war and one of these holds: the colonial crackdown is running, an enemy is its own qualifying colonial subject, or an enemy is a secessionist people sharing no heritage with it. Other wars still drain the bar through `colonial_stability_term_war`.
- **`.50`'s City-and-sterling text is Britain's** (`c:GBR ?= this`). Every other empire gets a generic treasury text, since the mod models no per-country currency.
- **Notices name the colonial power.** `.1`, `.2`, `.3` and `.11` save it as `scope:decol_colonial_power` for their `notification_*` loc. A message reads only `notification_<msg>_name/_desc/_tooltip`, never a bare key. `.2.c` frees no one, so it posts its own `colonial_neocolonial_reforms_notice`; `colonial_neocolonial_terms_notice` is for the options that grant independence (`.1.d_neo`, `.3.c`).

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

- **Purpose:** Freezes the source country's nuclear weapons program, halting progress toward nuclear capability while keeping its stockpile and progress. `nuclear_disarmament` is the harsher sibling, which also destroys both.
- **Article type:** Directed (source = concession-maker whose program is frozen, target = requestor, who pays the maintenance). The article is listed under the frozen country's articles. Both nuclear articles had the restriction on `target_modifier` until 2026-09-24. See `docs/guides/scripting_best_practices.md` § "Directed Treaty Articles: the SOURCE Concedes".
- **Mechanism:** `source_modifier = { country_nuclear_program_pause_bool = yes }` lasts as long as the treaty. `on_entry_into_force` zeroes `nuclear_weapons_program_funding`, the `je_nuclear_program` weekly pulse keeps it at zero, and `nuclear_program_possible_increase_funding` refuses to raise it.
- **Gates:** `possible` / `can_ratify` call `nuclear_program_can_be_paused` (`nuke_triggers.txt`; `nuclear_disarmament` uses `nuclear_program_can_be_disarmed`). The source must have researched `nuclear_weapons`, must not already be frozen or disarmed, and must not be receiving `nuclear_program_aid`. `nuclear_program_aid` refuses a frozen or disarmed recipient, and neither article can share a draft with aid to the same country.
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

**After a revolution.** A revolution's winner gets fresh records of every finished journal entry (`scripting_best_practices.md` § "What a Civil War's Winner Inherits"). For Human Augmentation and Mental Health, `possible` is tech-only and the end conditions are laws, so a finished debate would re-activate on the winner. It would then end again at once and replay its outcome event, or, after a timeout, run another twenty years. Both set a resolved variable (`human_augmentation_resolved`, `mental_health_crisis_resolved`) in `on_complete`, `on_fail` and `on_timeout`, and their `is_shown_when_inactive` / `possible` require its absence. Their 10-year outcome modifiers are not rebuilt on the winner; civil rights' are (`journal_entry_systems.md` § Civil Rights). Digital Rights and Post-Scarcity have no such guard yet. Their completion is blocked while the target law holds, but on a winner a failed Digital Rights entry re-arms and fails again at once, and a timed-out entry of either starts a new timer.

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
- **Model events (17–20):**

  | Event | Fired by | Audience | Choices |
  |---|---|---|---|
  | 17 Our Model Abroad | yearly pool | the hegemon, when its model holds ≥ `ch_model_abroad_min_share` (40%) of world culture across ≥ 3 countries | **Champion it:** `ch_model_champion` (+10% prestige, −25 influence, and `ch_model_champion_mult_bonus` +0.25 on the baseline multiplier) plus −15 relations with every ≥ 5% cultural power running another model. **Lead by example:** `ch_model_exemplar` (+10 legitimacy, decaying). |
  | 18 Rival Models | yearly pool | a trailing country, when #1 and #2 export different models (#2 ≥ 10%) | The pull is cultural, not a campaign, so no power loses relations over it; the desc names a power's campaign only when it holds `ch_model_champion` (.17 A; granted to #1, but it outlasts a fall to #2). Lean to either power: +15 relations with it, `ch_cultural_exchange`, and a 30-month weak spike toward *that* power's model (saved as `cultural_hegemon`). **Stand apart:** `ch_non_aligned_stance` (+5 legitimacy). |
  | 19 The Model Falters | `ch_fire_model_change_events`, when rank 1's model code changes between rebuilds | every country still running the old model | **Hold course:** `ch_model_orphaned` (−10 legitimacy, decaying) and +3 approval for IGs in government. **Adapt:** +15 relations with the new leader and a spike toward its model. |
  | 20 Domino | `ch_fire_model_change_events`, when a neighbour's census moves onto rank 1's model (`ch_switched_to_hegemon_model`) | its neighbours running something else, by state adjacency | **Contain:** `ch_ideological_cordon` (−50 authority) and −15 relations with the switcher. **Let it travel:** +10 relations and a spike toward the hegemon's model. |

  The switcher reaches event 20 in a dated `var:ch_domino_source`.
- **Change detection.** Events 19 and 20 compare two rebuilds, and the census pair is overwritten at every rebuild, so a yearly random pick would miss about half of them. They are fired straight from the rebuild instead. Change detection reads the census pair `var:ch_model_census` / `var:ch_model_census_prev`, written only by `ch_add_country_to_model_totals`, and `global_var:ch_rank_1_ideology_prev`. It never reads `var:ch_model`, because the pressure effect rewrites that whenever it re-classifies a hegemon between rebuilds. `global_var:ch_rank_2_ideology` caches the runner-up's model for event 18.
- **Test console:** `te_debug_ch.1` G stages event 17 with us as rank 1. H stages events 18–20 with us as a follower. Each staged event appears only if the save meets its trigger.

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
- **So do most event modifiers.** The country modifiers of events `.1`–`.16` go on `je:je_cultural_hegemony`, and so an event's cooldown guard must read them there: `NOT = { je:je_cultural_hegemony ?= { has_modifier = X } }`. The political-model events keep theirs on the country (`.17` `ch_model_champion` / `ch_model_exemplar`, `.18.c` `ch_non_aligned_stance`, `.19` `ch_model_orphaned`, `.20` `ch_ideological_cordon`), and the `*_ig` modifiers sit on interest groups. `legacy_je_modifier_cleanup_effect` strips a country-level copy of every modifier the JE migration moved, each month. Until #430 two events still granted one of those to the country, and the cleanup stripped it at the next pulse:
  - `.9.a`'s `ch_soft_power_dividend`, a reward, which now lasts its `long_modifier_time`;
  - `.6.b`'s `ch_brain_drain_remittances`, a cost (−5% research speed). Its one-month penalty is now the intended five-year decaying one, which makes accepting the brain drain costlier: a balance change.
  The guards in `.1`, `.3`, `.5`, `.10`–`.13` and `.16` read the country too, so they never fired (`.16`'s `ch_hegemonic_law_adopted` / `_resistance` were always JE-only, so they are not in the cleanup list).

---

## Game Rules

Fourteen mod systems can be toggled on/off at game setup via `common/game_rules/extra_game_rules.txt`.

| Rule | Flag (enabled) | Default | Systems Gated |
|---|---|---|---|
| `custom_religions_allowed_rule` | `custom_religions_allowed` | **disabled** | Custom religion events, JE visibility |
| `banking_system_rule` | `banking_system_enabled` | enabled | Banking cycle, crash contagion. **Three settings, not two** — see below |
| `global_warming_rule` | `global_warming_enabled` | enabled | CO₂ tracking, GW modifiers |
| `world_war_rule` | `world_war_enabled` | **disabled** | World war escalation, related JEs |
| `cultural_hegemony_rule` | `cultural_hegemony_enabled` | enabled | Cultural pull calculation, hegemony JE, hegemony on-action |
| `covert_warfare_rule` | `covert_warfare_enabled` | enabled | Covert operations command-centre JE (`je_covert_warfare`), all 13 covert diplomatic actions |
| `heir_education_rule` | `heir_education_enabled` | **disabled** | Heir education JE and focus modifiers; aptitude traits for rulers and heirs |
| `united_nations_rule` | `united_nations_enabled` | enabled | UN JE, vote events, international institutions |
| `nuclear_weapons_rule` | `nuclear_weapons_enabled` | enabled | Nuclear program JE, nuclear strike events, disarmament treaty |
| `decolonization_rule` | `decolonization_enabled` | enabled | Decolonization events and colonial collapse absorption |
| `space_race_rule` | `space_race_enabled` | enabled | Space race JE, satellite/moon/interplanetary events |
| `social_movements_rule` | `social_movements_enabled` | enabled | 8 social movement JEs and associated events |
| `universal_aptitude_traits_rule` | `universal_aptitude_traits_enabled` | **disabled** | Assigns admin/diplo/military aptitude traits to ALL adult characters instead of only rulers and heirs — works with Heir Education off too. With both rules off, no aptitude traits at all |
| `free_market_construction_rule` | `free_market_construction_enabled` | enabled | The construction market (§ Construction as a Market Good); `_no_retooling` = the market without the retooling surcharge, `_no_maintenance` = the market without construction maintenance (§ Market settings without retooling or maintenance); disabled = base-game-style direct construction (§ Free Market Construction off). Read through `te_free_market_construction_on` / `_off`, which test the *disabled* flag so a save from before the rule keeps the market, and `te_pm_retooling_waived` |

**`banking_system_rule` has three settings.** `banking_system_enabled`, `banking_system_simplified`
and `banking_system_disabled`. The middle one keeps the Banking Cycle journal entry — the cycle,
its crashes, the prudential and command/cooperative tools, the financial-regulation laws — and
switches off the monetary-policy layer built on top of it (`monetary_policy_design.md`
phases 1–5): no policy-rate dial, no inflation, no exchange rate, no pegs / swap lines /
guarantees / shared currency. Two scripted triggers tell the halves apart, and **nothing reads
the rule directly any more**:

| Trigger | File | True for | Asked by |
|---|---|---|---|
| `te_banking_system_on` | `common/scripted_triggers/banking_policy_triggers.txt` | enabled **and** simplified | the journal entry's `is_shown_when_inactive`, the banking history series |
| `te_mon_full_system` | `common/scripted_triggers/te_monetary_triggers.txt` | enabled only | every step of the monetary layer (see § Banking Cycle → Monetary Policy) |

Both read only a game rule, so they work from any scope — country, journal entry, treaty
article, power-bloc principle, GUI.

**Gating pattern:** Each rule sets a flag checked via `has_game_rule = <flag>`:
- **Journal entries:** `is_shown_when_inactive = { has_game_rule = X_enabled }`
- **On-actions:** Early `return = yes` if `NOT = { has_game_rule = X_enabled }`
- **Diplomatic actions:** `potential = { has_game_rule = X_enabled ... }`
- **Trait assignment (aptitude):** `limit = { te_aptitude_traits_enabled = yes  OR = { has_game_rule = universal_aptitude_traits_enabled  has_role_of_type = ruler  has_role_of_type = heir } }`

**Localization:** Rule names, option labels, and descriptions in `te_game_rules_l_english.yml`. Each rule has 5 keys: `rule_X_rule`, `setting_X_enabled`, `setting_X_enabled_desc`, `setting_X_disabled`, `setting_X_disabled_desc` — 7 for `banking_system_rule`, which adds `setting_banking_system_simplified` and its `_desc`, and 9 for `free_market_construction_rule`, which adds `setting_free_market_construction_no_retooling` and `_no_maintenance` with their `_desc`.

**Game Concepts:** Both cultural hegemony and information warfare have detailed concept tooltips (8 concepts total) in `te_concepts_l_english.yml` with cross-linked `[concept_X]` references. Concepts: `concept_cultural_hegemony_system`, `concept_cultural_pull`, `concept_cultural_pull_components`, `concept_foreign_cultural_benchmark`, `concept_information_warfare_system`, `concept_digital_sovereignty`, `concept_cyber_operations`, `concept_cyber_detection`.

---

## Covert Warfare System

> Supersedes the earlier *Information Warfare (Cyber Power)* design (`je_information_warfare`, `cyber_*` diplomatic actions, Digital Sovereignty), which was removed from the mod in `45cd7d8`. Nothing from that design remains in script.

**Purpose:** Adds an espionage/covert operations layer to the Cold War+ era. Countries can run covert operations against rivals (election interference, sabotage, espionage, etc.) using pact-based diplomatic actions. Operations consume operation slots, cost GDP-scaled expenses, and carry detection risk.

**Gate:** `has_game_rule = covert_warfare_enabled` + `has_technology_researched = television`.

### Key Files
| File | Purpose |
|---|---|
| `common/diplomatic_actions/covert_operations.txt` | 13 diplomatic actions (11 peacetime, 2 wartime) |
| `common/journal_entries/je_covert_warfare.txt` | Command center JE: IC display, slots, funding, detection; wires the operations widget |
| `gui/journal_entry_widgets/covert_operations_widget.gui` | Three JE widgets: `widget_je_covert_command_centre` (capacity, slots, funding ladder + stepper, detection factors, defence, last exposure), `widget_je_covert_operations` (one row per running operation) and `widget_je_covert_networks` (one row per per-target network, 2026-09 covert slice 4, with what a strong network reports on its target, slice 7) |
| `common/scripted_guis/covert_warfare_sguis.txt` | Widget handlers: the funding stepper, the ladder tooltip builder, four `is_shown`-only questions, thirteen per-type stand-down handlers, the per-row priority stepper (`covert_priority_up_sgui` / `_down_sgui`, 2026-09 covert slice 3) |
| `common/customizable_localization/covert_warfare_custom_loc.txt` | Funding level name, what that level is doing, the decrease warning, the exposed-operation name, the Tradecraft tier name and last-reason line |
| `events/te_debug_covert_events.txt`, `common/scripted_effects/te_debug_covert_effects.txt` | Console harness: `event te_debug_covert.1` / `.2` / `.3` (Tradecraft) / `.4` (slice-6 operations) / `.5` (network intelligence) |
| `common/script_values/covert_warfare_script_values.txt` | All script values: IC, slots, costs, detection, display |
| `common/static_modifiers/extra_modifiers.txt` | `covert_operation_funding_cost`, `intelligence_capacity_defense`, `iw_domestic_defense`, `iw_tradecraft_bonus`, operation effect modifiers |
| `common/scripted_effects/covert_warfare_effects.txt` | Operation containers (create/destroy/monthly sync), per-target networks (`covert_nets_sync`, `covert_net_create` / `_gain` / `_loss`, and slice 7's `covert_net_refresh_intel`), duration aging, phase-based effects, election confidence |
| `common/scripted_triggers/covert_warfare_triggers.txt` | Pact-type check, target validity, per-type cap, phase triggers, the four `covert_code_tier_*` exposure-tier triggers, `covert_exposure_is_costless` (war-tier-caught-during-the-war), the slice-6 target predicates (`covert_target_ahead_in_space`, `covert_net_weaker_than`) |
| `common/scripted_triggers/nuke_triggers.txt` | `nuclear_program_is_proliferating` (nuclear programme sabotage's launch gate), `nuclear_program_is_standing` (its maintain condition) |
| `common/scripted_buttons/covert_warfare_scripted_buttons.txt` | `iw_increase_funding_button`, `iw_decrease_funding_button` — hidden from humans (`visible = { is_ai = yes }`); the widget's stepper calls the same helpers |
| `common/on_actions/covert_warfare_on_actions.txt` | Election confidence on `on_election_campaign_end` |
| `events/covert_warfare_events.txt` | Detection event, diplomatic incidents |

### System Architecture
- **Operations as Pacts:** Each operation type is a togglable diplomatic action (like `increase_relations`). Effects applied monthly via JE `on_monthly_pulse`.
- **Operation state as script containers (1.13.10+):** Each running operation is one container tagged `iw_op` + `iw_op_<TYPE>`, parented to the operator country, holding `iw_target` (country), `iw_duration` (months), and JE display values (`iw_target_capital`, `iw_detect`, `iw_tgt_ic`, `iw_tgt_td`). The operator lists them in its `iw_ops` variable list, and every loop walks that list instead of `every_container`. Pacts remain the source of truth: `accept_effect` calls `covert_op_start`, `manual_break_effect`/`auto_break_effect` call `covert_op_end`, the detection event's `covert_op_burn` removes the pact and container together, and `covert_ops_sync_all` runs at the top of the monthly pulse to create containers for pacts that lack one (month 0) and destroy containers whose pact is gone. Saves made before containers keep their pacts, which restart at month 0; their old `iw_*_<type>_<n>` slot variables are left inert (clearing them would log "used but never set" warnings on every load).
- **Per-type cap:** `covert_ops_type_below_cap` compares the live pact count against `covert_ops_max_per_type` (1, +1 `mainframe_computers`, +1 `cyber_warfare`, +1 at Veteran Tradecraft — slice 5). That script value is the only place the cap lives; storage has no per-type limit.
- **Phases:** `covert_op_is_established` (`covert_op_effective_duration >= 6`) and `covert_op_is_fully_operational` (`>= 12`), where the effective duration is `iw_duration` plus the whole-month head start the target's network gave the operation at creation (`iw_net_head_start`, slice 4; missing reads as 0), evaluated on the container — the only place those two thresholds live. `covert_op_refresh_phase` projects them onto `iw_phase` (1/2/3) and `iw_phase_months_left` for display, from the tail of `covert_ops_age_all_durations` (immediately after the monthly `+1`, so they are never a month stale) and once from `covert_op_create`. Target-side effects use each operation's own phase; self-side effects use the operation with the largest phase × priority product (see **Priority** below).
- **Priority (2026-09, covert slice 3):** each container carries `iw_priority`, 1–3 (missing reads as 1); written by `covert_op_create` and backfilled by `covert_op_sync` before `covert_op_refresh_detection` runs, so an old-save container never reaches detection scaling without one. Priority multiplies what an operation does, what it costs and how exposed it is:

  | priority | effect × | upkeep weight | raw detection | reached by |
  |---|---|---|---|---|
  | 1 | 1 | 1 | +0 | default; every new and every pre-slice-3 operation |
  | 2 | 1.35 | 1.6 | +2 points | stepper, or AI when rivalled with the target |
  | 3 | 1.6 | 2.4 | +4 points | stepper, or a great-power AI at war with the target |

  Effect multiplies the phase multiplier (establishing = 1, fully operational = `covert_op_phase_full_mult` = 2 — the literal `multiplier = 2` this slice retired), so the six live multipliers are 1 / 1.35 / 1.6 establishing and 2 / 2.7 / 3.2 fully operational; preparatory stays at no effect whatever the priority. Every apply site goes through `covert_op_add_scaled_modifier`, which branches phase × priority onto six **constant** script values `covert_op_mult_p{2,3}_pri{1,2,3}` — constant because `add_modifier`'s `multiplier` is re-evaluated against ROOT on later ticks, so a value that reads the operation's container cannot be one. Self-side modifiers now come from the operation with the largest `covert_op_effect_mult` (phase × priority, 0 while preparatory) via `ordered_in_list … position = 0` in `covert_op_apply_self_effect`, not merely the best phase as before. Military espionage's conditional tech spread (`covert_military_espionage`) uses the same choice among only the operations whose target has researched more technologies than we have (`covert_op_target_ahead_in_tech`), and is removed as soon as none qualifies. Until 2026-09 it tested one saved target, whichever operation came last in `iw_ops`. Destabilization's movement pressure rides on its one country modifier, `covert_destabilization_resist` (+20 % activism and +20 % attraction at base, reaching every movement from the country as vanilla's home-affairs institution modifiers do); until 2026-09-25 the same totals were split across a second country modifier and a per-movement one, now retired (PENDING REMOVAL in `legacy_modifier_cleanup.txt`). Ideological subversion's movement pressure (`ch_apply_hegemon_movement_pressure`) scales by priority only, through the establishing-phase column `covert_op_mult_p2_pri{1,2,3}` at every phase — it was already phase-flat, so this slice didn't add a phase axis to it. The election-interference confidence hit (`covert_op_election_confidence_effect`, `-0.05`/`-0.1` by phase) is **not** priority-scaled: it is evaluated from the target's side over every attacker's operation with a literal `add_electoral_confidence`, unlike the operation's own `covert_election_interference` modifier, which is scaled normally.

  The row stepper is two fail-closed scripted GUIs (`covert_priority_up_sgui` / `covert_priority_down_sgui`), each taking the row's container as the saved scope `iw_op` (`AddScope('iw_op', ScriptContainer.MakeScope)`) — an engine link with no vanilla precedent, unproven at the time of writing; both handlers gate on `covert_priority_op_is_ours` (`exists`, `iw_op` tag, membership of the country's own `iw_ops`) so the worst case if the link fails is a permanently greyed stepper, never a change to the wrong operation. **Named contingency, do not build unless the in-game check fails:** replace the two handlers with per-type handlers in the stand-down shape (18 handlers, one per type per direction). **When a step takes hold:** detection moves on the click (the step re-runs the sync, which re-stages every operation's detection figure); raising priority also raises upkeep on the click; the effect modifiers follow only at the next monthly pulse, because re-applying them per click would re-roll infrastructure sabotage's `random_scope_state` pick onto a fresh target state every time. Upkeep is charged at the **higher** of the current priority and the priority the running effects were applied at — `covert_ops_apply_all_phase_effects` snapshots `iw_priority` into the container's `iw_priority_applied` before applying and calls `covert_refresh_priority_cost` after, which weights each operation through `covert_op_charged_priority_at_least` — so lowering priority lowers upkeep only once the effects have followed. Without that, raising to 3 just before the pulse and lowering the day after would buy a month of ×1.6 effect for a day of 2.4-share upkeep.

  Doc and console-harness detail: `journal_entry_systems.md` § Covert Warfare → Command Centre; `docs/superpowers/plans/2026-09-22-covert-per-op-priority.md` § Stepper.

  AI rule: `covert_ai_manage_priorities`, run for every `is_player = no` country before `covert_ops_sync_all` in the monthly pulse, sets a per-operation wanted level — 1 in default or bankruptcy, 3 for a great power at war with the target, 2 against a rival, else 1 — and steps `iw_priority` toward it at most twice per direction per month through the same `covert_possible_priority_up`/`_down` gates the stepper uses.
- **JE display:** `status_desc` is down to the five-tier intelligence-standing verdict plus the empty-state pointer. Everything else is in `widget_je_covert_command_centre` (`custom_widget_container_1`); per-operation rows are `widget_je_covert_operations` (`custom_widget_container_2`), whose datamodel is `JournalEntry.GetCountry.MakeScope.GetList('iw_ops')`; per-target network rows are `widget_je_covert_networks` (`custom_widget_container_3`, below the buttons, over `GetList('iw_nets')`). Full breakdown, op table and editing rules: `journal_entry_systems.md` § Covert Warfare → Command Centre.
- **Intelligence Capacity (IC):** Base 5 (from `INJECT:base_values`) + rank bonus (GP +10, Major +5 from `INJECT:country_ranks`) + literacy component (`literacy_rate × intelligence_capacity_literacy_max`, i.e. × 50) + GDP component (`gdp / global_gdp × 100`, capped at `intelligence_capacity_gdp_max` = 25) + modifiers (`country_intelligence_capacity_add`), the whole sum then scaled by `1 + country_intelligence_capacity_mult`.
- **Operation Slots:** Single modifier-driven value: `modifier:country_covert_operation_slot_add`. Base 1 (`INJECT:base_values`) + rank bonus (GP +2, Major +1) + tech modifiers (`mainframe_computers`, `computer_networks`, `cyber_warfare`, `quantum_computing`, +1 each). Capped at 10.
- **Funding:** **6 levels**, 0 – `iw_funding_level_max` (= 5): 0 Dormant, 1 Operational, 2 Professional (named Tradecraft before slice 5), 3 Covert Network, 4 Black Budget, 5 Deep State. **Level 0 does not idle operations, it ends them** — every covert action's `requirement_to_maintain` demands `iw_funding_level >= 1`, so dropping to 0 lapses every running pact (which is why the AI's own funding branch floors at 1 while it has operations, and why the widget's decrease control warns before the step). Cumulative detection reduction and counterintelligence IC by level: L2 −3 % / +5, L3 −8 % / +10, L4 −13 % / +15, L5 −19 % / +20, applied through the `iw_funding_defense` static modifier scaled by `covert_ops_funding_ci_mult` (= level − 1). The widget reads these from `covert_funding_detect_reduction_at_N` / `covert_funding_ci_ic_at_N`, which are sums of the Section 1 constants rather than a second copy of the numbers.
- **Cost:** `country_expenses_add` with GDP-scaled multiplier: `(Σ priority weights + 1) × funding_level × covert_operations_cost_scale` (`gdp × 0.00005`). The sum is `iw_priority_cost_sum`, refreshed by `covert_refresh_priority_cost` from `covert_op_create`, `covert_op_destroy`, the tail of `covert_ops_sync_all`, every priority step (`covert_apply_priority_change`), and the end of `covert_ops_apply_all_phase_effects`; it falls back to the pact count (`covert_operations_active`, the pre-slice-3 formula) for a save loaded before the first refresh. Each operation contributes 1 / 1.6 / 2.4 depending on its own priority — or rather the higher of its current priority and the one its running effects were applied at (`iw_priority_applied`), so raising charges more on the click while lowering charges less only from the next pulse, when the effects follow (the pulse re-refreshes the sum after applying; see **Priority** above) — example: three operations at priority 1 cost 4 units; raising one to priority 3 costs 5.4 units, +35 % total upkeep for +60 % on that one operation's effect, the diminishing return that keeps "everything at 3" from being the answer. The `+1` ensures a base maintenance cost even with 0 active operations (you pay for defensive IC benefits like counterintelligence). Cost modifier applies whenever `iw_funding_level >= 1`, regardless of active op count.
- **Detection:** each running operation carries its own monthly chance, `iw_detect` = `(base 10 − funding stealth − network cover + target counterintelligence penalty + (priority − 1) × covert_op_priority_detect_add) × (1 − covert efficiency, floored at 0.2) × covert_ops_detection_multi_op_scale` (scale default 1) — the priority term (2026-09, covert slice 3) adds raw points before efficiency, so a busier operation is more exposed but better tradecraft still hides most of it: at base 10 % with no efficiency, priority 1/2/3 reads 10/12/14 %, and at the late-game efficiency floor (0.2) the +4 raw points becomes +0.8. The priority is staged per operation onto the operator as `iw_priority_staging` by `covert_op_refresh_detection` (from `PREV.var:iw_priority` on the container — reading `scope:iw_op.var:iw_priority` directly isn't valid) before `covert_operation_detection_chance` is computed, then removed, clamped to a max of 50 % and a floor of `covert_ops_detection_floor` = 0.1 % (2026-09, covert slice 2) — reachable at high funding against a target with no counterintelligence, an "almost with impunity" but never "safe" floor; the operation row shows the chance to one decimal (`|1`, not `|0`) so that 0.1 % doesn't render as "0%" and read as safe — refreshed by `covert_ops_sync_all` at the top of the pulse. `covert_ops_roll_detection_all` (last in the pulse) rolls every operation against `covert_op_roll_chance` (= `iw_detect` directly — the multi-op scale is already folded in above, so the widget row and the roll agree by construction), collects the successes in a temporary list and burns **at most one** per month, chosen at random among them, by firing `covert_warfare.1` with the container in `scope:iw_burned_op`. With N equal operations at c each, P(any burn) = 1 − (1 − c)^N: 10 % → 19 % at two, 27 % at three. The event reads the container only in `immediate` (target → `scope:detected_by_country`, `iw_type_code` → ROOT `iw_burned_type_code`, `iw_phase` → ROOT `iw_burned_phase`, plus a derived `iw_burned_at_war` from a `has_war_with` check — see **Graduated exposure blowback** below) and branches on the type code in `after`; the options' blowback values read all three copied variables. `covert_burned_type_name` names the operation and `covert_burned_tier_name` names its tier in the text. The target penalty is `((target IC + target type defense) / attacker IC − 1) × 15`, capped at +20. Funding stealth is the cumulative reduction listed above.
- **Graduated exposure blowback (2026-09, covert slice 2):** what a detection costs is a function of the burned operation's **exposure tier** and **phase**, not a flat number.
  - **Tier table:** which code lands in which tier lives in exactly one place, the four `covert_code_tier_mild` / `_moderate` / `_severe` / `_war` triggers in `covert_warfare_triggers.txt` — each is an `OR` of `var:$VAR$ = <code>` guarded by `has_variable = $VAR$`. Two consumers genuinely branch through these triggers rather than re-listing codes: the infamy/relations base script values (`covert_exposure_infamy_base` / `covert_exposure_relations_base`) and the two custom-loc tier-name blocks (`covert_burned_tier_name`, `covert_last_exposed_tier_name`). Two other places are **not** trigger-driven, for different reasons: `covert_exposure_phase_mult` switches on `iw_burned_phase`, an axis orthogonal to the type code — it is a universal, type-agnostic formula applied identically to every operation, so it has nothing to do with the tier table at all; each action's pre-launch tier note, by contrast, is a hand-picked `$iw_exposure_tier_<tier>_note$` loc substitution baked directly into that action's fixed `_desc` string in `localization/english/te_concepts_l_english.yml`, with no trigger evaluated for it — a new type needs one chosen by hand to match its tier. (For everything else a new operation type touches, see **Adding an operation type** below — this bullet is only about the tier lookup.) Today's split: mild = {4 industrial espionage, 5 military espionage, 11 space programme espionage, 12 cultivate assets} — "everyone spies"; moderate = {0 election interference, 1 financial subversion, 6 influence campaign} — meddling in how the target governs itself; severe = {7 ideological subversion, 8 destabilization, 9 regime change, 10 nuclear programme sabotage} — attacking the state itself, the tier third parties hear about; war = {2 infrastructure sabotage, 3 comms disruption} — usable once conflict with the target is already underway, whether an active war or the diplomatic play that precedes one.
  - **Adding an operation type** touches every one of the following by hand — each is still edited separately, which is why this system repeatedly grew a site nobody remembered until `test_covert_op_registry.py` began checking them all against one table: the diplomatic action itself, a new `covert_<type>_action` block in `covert_operations.txt`; the tier trigger, adding the code to exactly one of the four `covert_code_tier_*` triggers above; `is_covert_operation_pact`'s `OR` (one line per type) of `is_diplomatic_action_type = covert_<type>_action` (`covert_warfare_triggers.txt`), which `covert_operations_active` and other pact-identity checks read; `covert_ops_sync_all`'s `covert_op_sync = { TYPE = ... ACTION = ... DEFENSE_MOD = ... CODE = ... }` row (`covert_warfare_effects.txt`) — this is what actually creates the operation's container and stamps its type code, so missing it means no container exists at all: no detection, no tier lookup, nothing runs; the type's own block in `covert_ops_apply_all_phase_effects` (same file) applying its actual gameplay modifiers; `covert_warfare.1`'s `after` `if`/`else_if` chain (`events/covert_warfare_events.txt`) resolving the type name and action key to burn a detected operation; `covert_burned_type_name` and `covert_last_exposed_type_name` (`covert_warfare_custom_loc.txt` — a *different* pair from the tier-name blocks above, easy to conflate by name; miss these and the operation renders as "unknown" in the very event this section describes); the pre-launch tier note baked into the new action's own `_desc` (above); a new stand-down handler in `covert_warfare_sguis.txt` (one per type); the operations widget's own per-type block in `gui/journal_entry_widgets/covert_operations_widget.gui` — a `visible`/`text` pair for the row's display line and a matching stand-down-button block, each gated on `ScriptContainer.HasTag('iw_op_<type>')`, or the new type shows a blank row and no way to stand it down; a static modifier for the type's actual effect (`static_modifiers/extra_modifiers.txt`); the action's **launch preview** in its `accept_effect` — the header `covert_op_preview_header_tt`, a `show_as_tooltip` rendering each country-scoped modifier the pulse applies (self ones at the root, target ones under `scope:target_country`) with no `multiplier` and no duration, then a `covert_<type>_extra_tt` line for whatever the engine cannot list there (`script_only` fields, modifiers on movements or states, conditional parts), and `covert_op_self_effect_note_tt` if the type has a self effect — pinned by `test_covert_launch_preview.py`, which derives what to expect from `covert_ops_apply_all_phase_effects` and checks the stated numbers against the modifiers; and the new action's own loc — name, description, cancel/launch/notification strings, pact-in-progress text, and its `iw_op_name_<type>` (feeds the pair above) and `je_iw_op_row_<type>` (feeds the widget row) keys. Two more: the lens icon `gfx/interface/icons/lens_toolbar_icons/covert_<type>_action.dds` (auto-loaded for any action without `show_in_lens = no`; a missing one is a `VFSOpen` error every session) and the three `country_covert_defense_*_add_desc` strings that list the operations each axis covers. (`covert_warfare.2`, the defender's event, no longer needs a per-type line: since #430 it keys on the exposure record `covert_op_burn` writes for every code.) **`test_covert_op_registry.py` is the executable form of this list** (2026-09, covert slice 6): add the type's `OPS` row first, and the failures name every site still missing.
  - **Base cost by tier** (`covert_exposure_infamy_base` / `covert_exposure_relations_base`, `covert_warfare_script_values.txt`): mild +1 infamy / −10 relations, moderate +2 / −20, severe +4 / −40. An unrecognised code reads as moderate. The war tier no longer has a single flat cost (see the next bullet).
  - **Wartime operations during a diplomatic play (2026-09, covert slice 2, Task 8):** `covert_infrastructure_sabotage_action` and `covert_comms_disruption_action` can now be launched and kept running while `is_diplomatic_play_enemy_of = scope:target_country` holds, not only once `has_war_with = scope:target_country` is already true — an intelligence service starts laying groundwork once a play against the target is under way, not only after the shooting starts. All three gates (`possible`, `requirement_to_maintain`, the AI's `will_propose`) accept either condition via `OR`; the blanket `is_at_war = yes` clause is gone (redundant once the gate names the target, and it would have blocked the play case). If the play resolves without war, `requirement_to_maintain` fails and the operation stands down — the intended fiction. The shared tooltip key is `iw_at_war_or_play_tt`.
  - **War tier's blowback now turns on *when* the operation was caught, not just that it is the war tier** (2026-09, covert slice 2, Task 8): the war can begin between the burn firing (`covert_warfare.1`) and the player clicking an option, so `immediate` copies `has_war_with = scope:detected_by_country` onto the operator as `iw_burned_at_war`, alongside the existing `iw_burned_type_code` / `iw_burned_phase` copies (same reason: event loc and the options, which fire up to `duration` days later, cannot reach the container). `covert_exposure_is_costless` (`covert_warfare_triggers.txt`) is the one place that reads it: true when the burned type is war-tier **and** `iw_burned_at_war = 1`. **Caught once the war has started: nothing at all** — `covert_exposure_infamy_war` is now 0, and both options skip `change_infamy` and `change_relations` outright when `covert_exposure_is_costless = yes`, so neither renders as "+0"/"-0". **Caught during the run-up, before the war has started: the worst look there is** — sabotage before the shooting reads as manufacturing the war, so it is charged `covert_exposure_infamy_war_prewar` = 4 (the severe tier's infamy) and `covert_exposure_relations_war_prewar` = −20 (the moderate tier's relations), named as their own constants so this case can be retuned without moving either tier it borrows its magnitude from. Third parties are still keyed to the severe *tier* only (`covert_code_tier_severe`), not to the costless question — pre-war sabotage's international reaction is carried entirely by its infamy. All three copied variables (`iw_burned_type_code`, `iw_burned_phase`, `iw_burned_at_war`) are cleared in `after`, unconditionally (outside the `exists = scope:detected_by_country` guard), so a burn whose target has vanished doesn't leave them stuck.
  - **Phase factor** (`covert_exposure_phase_mult`, read from `iw_burned_phase` copied onto the operator alongside the type code): preparatory ×0.5, establishing ×1, fully operational ×1.5. A missing phase reads as establishing.
  - **Option split** (`covert_warfare.1`'s two options, both available regardless of tier): **Acknowledge** pays the full tier×phase infamy (capped at `covert_exposure_infamy_max` = 25) and half the relations hit (`covert_exposure_acknowledge_relations_mult` = 0.5). **Deny** pays half the infamy (`covert_exposure_deny_infamy_mult` = 0.5) but the full relations hit, and separately grants the target `covert_op_heightened_vigilance_modifier` (+5 to all three `country_covert_defense_*_add` types) — denying it makes the target dig in. Values are anchored to the old flat costs at the moderate tier's establishing phase: **Acknowledge** (2 infamy / −10 relations) lands close to the old flat 2 infamy / −15 relations; **Deny** (1 infamy / −20 relations) is a materially softer relations hit than the old flat 1 infamy / −30, not "about the same."
  - **Severe tier's third-party effect** (`covert_exposure_third_party_blowback`, fired from *both* options whenever `covert_code_tier_severe = { VAR = iw_burned_type_code }`): every country that is neither the operator nor the target, and is either in the same power bloc as the target (guarded by `is_in_power_bloc = yes` so two blocless countries don't read as being in "the same" bloc) or has a treaty alliance with the target, loses `covert_exposure_third_party_relations` = −10 relations with the operator and gets a `covert_severe_exposure_notice` feed notification. A `custom_tooltip` wraps the `every_country` loop so the option preview actually shows the spray instead of reading as a no-op.

### Per-Target Networks (2026-09, covert slice 4)
- **What:** every country an operator has run operations against gets a persistent network, 0 – `covert_net_max` (100), that outlives the operations. One script container per (operator, target), tagged `iw_net`, parented to the operator, listed in the operator's `iw_nets`; vars `iw_target`, `iw_target_capital`, `iw_net_strength`, `iw_net_ops`, `iw_net_trend` (1 growing / 2 decaying / 0 holding at max), `iw_net_head_start_offer`. Type-agnostic: adding an operation type adds no network site.
- **Monthly pass:** `covert_nets_sync`, called **only** from the JE pulse, between `covert_ops_sync_all` and `covert_ops_age_all_durations` — never from `covert_ops_sync_all` itself, which also runs on every funding and priority click and would grow networks per click. It (1) creates a network for any operation target without one, (2) counts operations per network by zeroing `iw_net_ops` and walking `iw_ops` once, (3) grows each network with ≥ 1 operation by `covert_net_gain_base` × (1 + 0.5 × (ops − 1), ops counted to 3) × `covert_net_gain_scale` (1 below 50, falling to 0.1 at 100 — the `un_standing_gain_scale` shape), or decays it by `covert_net_decay_base` = 1.5 a month (halved at funding ≥ `covert_net_maintain_funding_level` = 3 — there is deliberately no "maintain presence" pact; funding is the paid lever and the AI already manages it), and (4) reaps networks whose target is no longer alive (`is_country_alive`) or that sit at 0 with no operations. A network is also created by `covert_op_create`, so the row appears the day the first operation starts.
- **Consumers:** (a) **head start** — `covert_op_create` copies the network's `iw_net_head_start_offer` (`covert_net_head_start_value` = strength × 0.05, rounded, capped at 5) onto the new operation as `iw_net_head_start`, fixed for its life; the phase triggers and `covert_op_refresh_phase` measure `covert_op_effective_duration`. The cap is under 6, so the preparatory phase is never skipped: a full network puts a new operation one month from establishing. (b) **cover** — `covert_op_refresh_detection` stages the target network's strength on the operator as `iw_net_strength_staging` (0 without one), and `covert_operation_detection_chance` subtracts `covert_net_detect_reduction` = strength × 0.05 raw points (−5 at full) after the funding terms and before efficiency. The staging happens inside `covert_ops_sync_all`, before the monthly network pass, so detection uses last month's strength — a one-month lag, accepted. (c) **burn** — `covert_op_burn` takes `covert_net_burn_loss` = 25 off the target's network (unscaled — about a year of single-operation rebuilding).
- **Lookup rule:** every "network for target X" lookup does its work **inside** the `random_in_list` (`limit = { var:iw_target ?= X }`), never through a saved scope afterwards. Several run inside loops, where an unmatched pick would leave the previous iteration's network in a saved scope, and several sit on paths the engine also walks to render tooltips (the steppers' `covert_refresh_funding_state`, `covert_warfare.1`'s `after`), where a saved scope may be unset. `iw_net_head_start_offer` is restated by `covert_net_clamp` after every strength write, so a burn shrinks the head start a same-day relaunch gets.
- **Projection** (months from 0): strength 25 in 12.5 / 8.3 / 6.3 months with 1 / 2 / 3 operations; 50 in 25 / 16.7 / 12.5; 75 in 42 / 28 / 21; 90 in 65 / 44 / 33. Decay from 50 with no operations: 33 months (67 at funding ≥ 3).
- **Console:** `event te_debug_covert.2` options i (every network to full strength) and j (one network pass now).

### Network intelligence (2026-09, covert slice 7)
- **What:** a network strong enough reports on the service it has penetrated — display only, nothing in script reads the report back. Tier 1 (strength ≥ `covert_net_intel_tier_1_strength`, 50): the target's intelligence capacity and technology count, each printed beside our own. Tier 2 (≥ `covert_net_intel_tier_2_strength`, 75): also how many covert operations the target is running against us. With one operation a network reaches tier 1 in ~25 months and tier 2 in ~42; cultivate assets alone in ~17 / ~28.
- **The defender rule's one exception:** nothing else tells a country about hostile operations it has not caught (`covert_op_burn`'s header). The tier-2 count is that exception on purpose — it is earned by holding a strong network inside the other service, not given to the defender — and it says how many, never which operations or what they do.
- **Tier code:** `covert_net_intel_tier_value` (network scope) is the only place the two thresholds are compared; `covert_net_clamp` writes it to `iw_net_intel_tier` (0 / 1 / 2) after every strength write, beside the head-start offer, so a burn that drops a network below 75 or 50 hides that part of the report the same day. `covert_net_create` seeds 0. The widget reads only the code.
- **Report:** `covert_net_refresh_intel` (network scope, needs `scope:iw_net_operator`), called from `covert_nets_sync` step 3 straight after the strength write and from the console harness — never from a tooltip-walked path, because it uses saved scopes. At tier ≥ 1 it writes `iw_net_intel_ic` (the target's `intelligence_capacity_total`) and `iw_net_intel_techs` (`techs_researched`); at tier 2, `iw_net_intel_ops`, counted by accumulation over the target's covert pacts with `first_country` = target and `second_country` = us. Pacts, not the target's `iw_ops`: the containers only sync while the target's own journal entry is active. Every phase counts. Below a tier its values stay stored but hidden. Strength only rises in the monthly pass (or the harness), which refreshes right after, so a tier is never shown with values that were not written at it. Our own figures are live (`intelligence_capacity_total`, `covert_techs_researched_display`); theirs are last month's report.
- **Network row, not operation row:** the spec said "operation/network row". The report sits on the network row because the network outlives its operations. The operation row's detection line already printed the target's capacity (`iw_tgt_ic`) as a detection input before this slice, and still does, but only while an operation is running there.
- **Old saves:** a network from before this slice has no `iw_net_intel_tier` until its first monthly pass; every report line is gated on `ScriptContainer.HasVariable('iw_net_intel_tier')`, so for that month the row shows none.
- **Console:** `event te_debug_covert.5` — a: every network to 50; b: to 80; c: every network's target starts cultivate assets against us (target funding floored at 1) and the reports refresh, so a tier-2 row's count goes up by one. `te_debug_covert.2` option i (strength 100) now refreshes the report too.

### Tradecraft — agency experience (2026-09, covert slice 5)
- **What:** one country variable on the operator, `iw_tradecraft`, 0 – `covert_tradecraft_max` (100), seeded 0 by `covert_tradecraft_init` (from the JE's `immediate` and again at the top of every monthly pass, because `immediate` does not re-run for an entry already active in a loaded save). Its **only writers** are `covert_tradecraft_gain` / `covert_tradecraft_loss` (`covert_warfare_effects.txt` § TRADECRAFT), both no-ops while the variable is missing and both written with `set_variable = { value = { value = var:… add = … } }` + `clamp_variable` rather than `change_variable` (which does not reliably resolve a script-value operand). `iw_tradecraft_last_reason` records why it last moved: 1 operations maturing; 20 / 21 / 22 / 23 a mild / moderate / severe / wartime operation burned; 24 idle decay.
- **Gain:** `covert_tradecraft_monthly`, called **only** from the JE pulse, right after `covert_ops_age_all_durations` (never from `covert_ops_sync_all` / `covert_refresh_funding_state`, which run on every stepper click). Each operation at establishing or better counts 1 and each still preparatory counts `covert_tradecraft_prep_gain_fraction` (0.5); the total, capped at `covert_tradecraft_ops_counted` (4), is `iw_tradecraft_ops` (shown in the tooltip), times `covert_tradecraft_gain_per_op` (1), scaled by `covert_tradecraft_gain_scale` = (100 − x) / 50 clamped [0.1, 1], the UN-standing shape. **Decay:** `covert_tradecraft_decay` (0.25) a month while `covert_operations_active < 1`.
- **Loss:** `covert_tradecraft_burn_loss`, called from `covert_warfare.1`'s `after` inside the same `exists = scope:detected_by_country` guard as `covert_op_burn`, and **before** `iw_burned_type_code` is removed (it branches on that variable through the `covert_code_tier_*` triggers): mild 3, moderate 6 (also any unrecognised code), severe 9, war 3 — unscaled. Both options' `covert_op_burned_tt` print the amount through `covert_tradecraft_burn_loss_value`. Standing an operation down costs nothing.
- **Balance:** detection rolls from month 0 and a burned operation is relaunched preparatory; the spec's closed form ignored both, and with preparatory operations earning nothing one moderate op at 10 % per-op detection averaged ~31. Preparatory operations therefore earn half (`covert_tradecraft_prep_gain_fraction`). Simulated long-run averages (600 months; network head start 0 / 5) and median months to Established: at 10 % one moderate op 57 / 69 (131 / 81 months), two 62 / 72 (62 / 39), four 67 / 74 (31 / 18), one severe 25 / 44 (208 / 138); at 5 % one moderate op 82 / 85 (62 / 51); at 2 %, 94 / 95. 10 % is funding 1 with no covert efficiency. Table: `covert_warfare_script_values.txt` § TRADECRAFT.
- **Tiers** (`covert_tradecraft_tier_1` … `_4`, the only place the floors are compared; `covert_tradecraft_tier` counts them 0–4): **Untested** < 20 ≤ **Fledgling** < 40 ≤ **Established** < 60 ≤ **Seasoned** < 80 ≤ **Veteran**. Names are loc only (`iw_tradecraft_tier_name_0..4`, via the `covert_tradecraft_tier_name` custom loc). The spec's fifth name, "Storied", was dropped: its unlock lines bind Established = 40, Seasoned = 60, Veteran = 80.
- **Bonuses:** `iw_tradecraft_bonus` (`country_intelligence_capacity_mult` +0.05) on `je:je_covert_warfare` with `multiplier = covert_tradecraft_bonus_mult` (= tier, via `owner = { }`), refreshed only by `covert_tradecraft_refresh_bonus` at the end of the monthly pass — +20 % capacity at Veteran. Networks grow ×(1 + `covert_tradecraft_net_gain_per_tier` 0.15 × tier), ×1.6 at Veteran: `covert_nets_sync` stages `iw_tc_net_mult_staging` on the operator and each network copies it into `iw_net_tc_mult` just before `covert_net_tick_gain` reads it (nominal gain, before `covert_net_gain_scale`). Networks tick earlier in the pulse than Tradecraft, so they grow at **last month's** tier.
- **Unlocks** (one trigger each, so each gate is one `custom_tooltip`; none ever ends something already running): `covert_tradecraft_unlocks_priority_3` (Established) — the step *to* priority 3 in `covert_possible_priority_up`, so it binds the row stepper and `covert_ai_manage_priorities` alike; an operation already at 3 stays there and stepping down is never gated. `covert_tradecraft_unlocks_severe_ops` (Seasoned) — read by regime change's and nuclear programme sabotage's `possible` (slice 6): launching only, so a running one survives the score falling. `covert_tradecraft_unlocks_extra_per_type` (Veteran) — +1 in `covert_ops_max_per_type`, which only gates launching.
- **Limitation:** Tradecraft accrues only while the journal entry is active (its pulse is the only clock) — the same limitation the detection roll has.
- **Console:** `event te_debug_covert.3` — set 45 (Established), set 85 (Veteran), one monthly pass now.
- **Naming:** funding level 2 used to be called "Tradecraft"; it is now **Professional**, so the word means only this score.

### New operations (2026-09, covert slice 6)
- **Regime change** (`covert_regime_change_action`, code 9, severe, ideological defence): needs a rivalry (launch and maintain), a non-subject target and **Seasoned** Tradecraft (launch only). Target modifier `covert_regime_change`: coup resistance −1 (script-only — named in the modifier's description, not listed in its tooltip), legitimacy −5, movement radicalism +5 %, all × phase × priority (up to ×3.2). Once fully operational, `je:je_ip4_coup ?= { add_progress = { value = covert_regime_change_coup_push … } }` (+5 a month) — no DLC gate: coups are base game. The coup bar moves weekly by commander strength − coup resistance, so each point of resistance removed is ~+4.3 progress a month; against a legitimacy-50 government a fully operational priority-1 operation adds ~+18 a month (table: `docs/superpowers/plans/2026-09-23-covert-new-operations.md`).
- **Nuclear programme sabotage** (`covert_nuclear_sabotage_action`, code 10, severe, military defence): target must satisfy `nuclear_program_is_proliferating` (funded, running, not paused or disarming — a stockpiling nuclear power qualifies) and **Seasoned** Tradecraft to launch; it is maintained on `nuclear_program_is_standing` instead (the programme exists and is not paused by treaty or disarmed — funding is not read), so a target stepping its funding to 0 for a week cannot end the operation for free. Target modifier `covert_nuclear_sabotage`: `country_nuclear_program_progress_mult −0.25` × phase × priority — progress ×0.75 … ×0.2, never zero.
- **Space programme espionage** (`covert_space_espionage_action`, code 11, mild, economic defence): target must have completed a milestone we have not (`covert_target_ahead_in_space`, over all eight; milestone completion is public). Self modifier `covert_space_espionage` (+10 % milestone progress, −10 % risk, × phase × priority, from the strongest such operation); target marker `covert_space_espionage_detected` (authority −3, like the other espionage markers).
- **Cultivate assets** (`covert_cultivate_assets_action`, code 12, mild, ideological defence): **no effect on the target or the operator**. `covert_nets_sync` flags the network it feeds (`iw_net_cultivating`), and `covert_net_tick_gain` multiplies that network's growth by `covert_net_cultivate_mult` (1.5; stacks with the extra-operation factor and Tradecraft) — alone against a target, strength 50 in ~17 months and 75 in ~28 (25 and 42 for any other operation). Always counts towards Tradecraft at the preparatory fraction. **Priority is fixed at 1**: `covert_possible_priority_up` refuses it (binding the AI too) and its widget row hides the stepper and the phase and priority lines behind one line of its own. A burn still reaches the defender through `covert_op_burn`'s exposure record, like every other type's. The AI proposes it against a rival or an antagonised country where its network is below `covert_cultivate_ai_net_ceiling` (50), more keenly where it already runs another operation.
- **Console:** `event te_debug_covert.4` — plant all four (fully operational; rivalry declared for regime change; nuclear and space only if a qualifying target exists) and set Tradecraft to Seasoned.

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
- **AI Funding Management:** The JE monthly pulse sets `iw_funding_level` outright for every `is_player = no` country — this, not a button, is the AI's path into funding. Branches, in order: in default or bankrupt → 1 if it has operations (dropping to 0 would lapse them all and waste the setup), else 0; otherwise, if major power or above **and** (rivalled or at war) → at war: `iw_funding_level_max` for a great power, else 3; at peace: 3 for a great power (whether or not it already runs 3+ operations), else 1; otherwise 1 if it has any operation running, else 0. A human's level comes from the widget's stepper and is never overwritten.
- **AI Priority Management (2026-09, covert slice 3):** `covert_ai_manage_priorities`, run for every `is_player = no` country immediately before `covert_ops_sync_all` in the monthly pulse (so the sync sees the new priorities the same tick). In default or bankrupt, the wanted level is 1 (never raises while the treasury is in that state); otherwise a great power at war with the operation's own target wants 3, a country with a rivalry pact against the target wants 2, and everything else wants 1. Each operation's `iw_priority` steps toward its wanted level at most twice per direction per month, through the same `covert_possible_priority_up`/`_down` gates the human stepper uses, so slice 5's Tradecraft requirement for priority 3 binds the AI too.
- **Wartime ops:** Higher eval chance (0.05), no rank requirement, `in_default = no` guard only. `propose_score` 15, +10 rivalry pact with the target, +5 GP, +5 when `is_losing_war_against = { ENEMY = scope:target_country }` (battlefield read from `common/scripted_triggers/nuke_triggers.txt`; see § War Support Feeds).
- **Slice-6 operations (2026-09):** regime change — rivalry plus an antagonistic or domineering attitude, major power or above; score 5, +5 great power, +8 aggressive ruler; evaluation 0.02. Nuclear programme sabotage — target proliferating, we are a nuclear power or a great power, and rival or antagonistic; score 5, +10 when the target's programme is at 75 % or more, +5 great power. Space programme espionage — target ahead in space and we are pursuing a milestone; score 10, +5 great power. Cultivate assets — rival or antagonistic, and our network there below `covert_cultivate_ai_net_ceiling` (50); score 5, +5 when we already run another operation there; evaluation 0.05. **The AI will rarely launch the two severe operations:** `possible` binds it, so it needs Seasoned Tradecraft, and one moderate operation at 10 % detection averages 57.

### Cancellation Conditions
- **All 11 peacetime ops** (election interference, financial subversion, industrial espionage, military espionage, influence campaign, ideological subversion, destabilization, and slice 6's regime change, nuclear programme sabotage, space programme espionage and cultivate assets) have truce checks in both `possible` and `requirement_to_maintain`, so they auto-cancel if a truce with the target begins. None of them has a war guard (the actions say "Allowed during war"): a war with the target does not end them.
- **Slice-6 operations also lapse** when their own condition goes: regime change when the rivalry ends; nuclear programme sabotage when the target's programme is paused by treaty, given up or gone (`nuclear_program_is_standing` — not when its funding merely drops to 0); space programme espionage once the target is no longer ahead; cultivate assets when the target becomes decentralized.
- **Wartime ops** (infrastructure sabotage, communications disruption) require active war with the target **or** a diplomatic play against them under way (2026-09, covert slice 2, Task 8 — see § Graduated exposure blowback); they auto-cancel once neither holds, e.g. the play resolves without war, or peace is achieved.
- **Script value scope:** All covert warfare SVs use `owner = {}` wrapping to access country-scope data from JE scope (the `on_monthly_pulse` context). This is required because the JE monthly pulse runs in journal entry scope, not country scope.
- **Stand down:** `covert_effect_stand_down` (called only from the widget's thirteen `covert_stand_down_<type>_sgui` handlers) ends one operation on demand: `remove_diplomatic_pact` plus `covert_op_destroy`. That reaches the same end state as a manual break in the diplomacy outliner, whose `manual_break_effect` is `covert_op_end` → the same `covert_op_destroy`; the effect's `any_in_list` guard makes it idempotent, so it is correct whether or not `remove_diplomatic_pact` also fires the break hook. No infamy and no relations hit — those belong to being caught, not to calling an operation off.

### Known Behaviours (not bugs to fix in passing)
- **Detection was a single country-level roll until 2026-09 (covert slice 1).** It rolled once against the worst target's intelligence capacity combined with an arbitrary target's type defence, then burned a *random* operation, and the `random_list { 1 = { add = c } 99 }` form made the odds (1 + c) / (100 + c) rather than c %. It now rolls per operation (see **Detection** above). Two script values from the old roll's display layer, plus the unused `covert_ops_detected_infamy` constant, were deletion candidates and have since been deleted (`covert_detection_chance_display`, `covert_detection_target_ic_display`, `covert_ops_detected_infamy`) — none remain anywhere in the mod. `covert_detection_base_display`, `covert_detection_efficiency_pct_display` and `covert_ops_funding_detection_reduction_display` are a different set: they feed the JE's detection-factors tooltip (`je_iw_detection_factors` in `te_journal_entries_l_english.yml`) and remain live. `covert_detection_efficiency_reduction` is the one old-roll value still defined and unreferenced (`covert_warfare_script_values.txt`) — remaining deletion candidate for a later slice.
- **Losing a slot deactivates the entry but does not stop the operations.** The JE's `possible` gate wants one slot above the rank baseline; no `requirement_to_maintain` checks slots, so operations already running continue (and stay visible in the outliner) while the journal entry and both widgets disappear.
- **`covert_warfare.2` keyed infrastructure sabotage on its state modifier until 2026-09 (covert slice 6)**, so a burned sabotage operation never reached the defender; slice 6 keyed it on the country-scope `covert_infra_sabotage_morale`.
- **`covert_warfare.2` never reached the defender of an operation burned during preparation until #430 (2026-09-25).** Its trigger listed the modifier each type leaves on its target, and those are applied only from the establishing phase. It now keys on the exposure record `covert_op_burn` writes for every burn (`iw_last_exposed_type`, with `iw_last_exposed_phase` for the text), and it names a burn stopped in preparation as one that never took effect. Its option b, **Retaliate in kind**, used to take 3 infamy off the defender and retaliate against nobody: it now seeds the defender's own network inside the perpetrator (`covert_retaliation_seed_network`, `covert_net_retaliation_seed` = 25, the size of the burn's own network loss), open to a country whose covert journal entry is active. The infamy relief is option c, **Make the evidence public**.

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

## Legacy narrative event integration

Law-enactment bank runs (`extra_law_events.2` / `.38`) now apply a small
confidence shock (-5 cycle, -1 momentum) when the banking JE exists, including
simplified banking. With banking disabled they remain enactment flavor.
`finreg_banking_stability` retains its company-throughput benefit and also
reduces banking crash probability by 10% of base; deposit guarantees in `.62`
share that protection.

The discretionary bailout (`banking_cycle_events.45`) requires a non-defaulting
donor at cycle 40+ and a non-hostile, diplomatically relevant trading partner
in downturn/panic with an active banking JE. The partner is asked first: the
donor's banking pulse picks it with the same gate and sends it
`banking_cycle_events.68` ("appeal to [donor]?", −5% prestige for asking), and
only its appeal option sends `.45` to the donor; whatever the donor answers
reaches the partner as `.69`, naming the sum. Rescue options transfer equal treasury amounts (the donor's
old weekly expense multiplied by duration / 14, approximating its former
linearly decaying total) and grant temporary banking stability to the recipient.
This is a grant, not a new swap-line or lender-of-last-resort treaty. The latter
continues to use its own default-driven event. Protected recipients cannot draw
another discretionary bailout while the stability modifier lasts.

`international_relations_events.6` and `.7` are disabled-system fallbacks only.
Enabled covert warfare owns detection and exposure; enabled space race owns
milestone celebrations. The first-colony charter story (`society_technology_events.18`)
is dispatched seven days after a country's first tracked colony, after its
location-specialization event. Governance (`.19`) requires a tracked colony and
the charter story to have fired. Both retain their building-based flavor gates
when space race is disabled; enabled-system governance no longer needs an
unrelated space-elevator building or era-12 technology (colonization begins in
era 11). The monthly first-colony draw backfills existing saves, with a short
pending flag preventing it from racing the delayed establishment event.
