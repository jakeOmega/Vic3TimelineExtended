# Vanilla 1.13 known bugs (not the mod's responsibility)

When triaging mod error-log entries, these vanilla 1.13 bugs surface even with the mod loaded but are pre-existing in vanilla itself. Verify any matching entry against vanilla source before spending time fixing.

Each entry: error text, vanilla file path with line, root cause, frequency observed in our 1.13 testing.

## Script errors observed

### `common/ai_strategies/00_default_strategy.txt:5065` — invalid `region` event target

```
Error: Event target link 'region' returned an invalid object
```

The `strategic_region_scores` block does `any_scope_state = { region = scope:region }` but `scope:region` is unset in some evaluation contexts. Vanilla bug. **818 occurrences** in a ~10-year observer-mode session.

### `common/scripted_buttons/ryukyu_rivalry_buttons.txt:131, 142, 153, 517` — invalid `this` comparison

```
Error: Invalid right side during comparison 'this'
```

Lines like `c:CHI ?= this` evaluate `this` in scopes where it's not a country. Vanilla bug. **72 occurrences** in observer-mode.

### `common/journal_entries/04_indian_famines.txt:25`, `common/journal_entries/03_afghanistan.txt:397-414`, `common/journal_entries/00_alaska.txt:137`, `common/company_types/00_companies_asia.txt:353`, `common/company_types/00_companies_mp1.txt:1346`, `common/company_types/00_companies_americas.txt:342`, `common/company_types/00_companies_soi.txt:415` — invalid `region` event target

Same root cause as the AI strategy bug: `region` event target is invalid in the JE / company-type evaluation scope (typically when iterating across pseudo-states or substates that don't carry a strategic region). **40+ occurrences total across these definitions.**

### `common/on_actions/00_on_actions_monthly.txt:145` — invalid country/strategic-region

```
Error: has_strategic_region_interest_tier trigger [ Invalid Country or StrategicRegion! ]
```

The `colonial_claims_check` on-action has `has_strategic_region_interest_tier = { strategic_region = root.region ... }` where `root.region` is sometimes invalid. Vanilla bug. **10 occurrences.**

### `common/script_values/command_values.txt:373` — `naval_battle_size` produces type-none and Div/0

```
Value of wrong type in 'common/script_values/command_values.txt:373'. Got value of type 'none'
Div/0 near common/script_values/command_values.txt:373
```

The `naval_battle_size` script value reads `scope:military_formation.num_ships_not_in_battle` and later divides by it; in some evaluation contexts the formation/ship count is unset, producing a none-typed value and a divide-by-zero. Vanilla bug. **136 occurrences (124 type-none + 12 div/0)** in a single 1.13 mod session.

### `common/naval_battle_conditions/00_naval_battle_conditions.txt:210, 263` — `fixed_range` in non-random context

```
range directive used, but no randomization is available! Might be in a trigger rather than effect.
```

Multiple naval conditions use `intensity = { fixed_range = { min = X max = Y } }` (line 210 = `naval_condition_squall`/similar, line 263 = a later condition). The engine evaluates these in a context it doesn't consider randomized. Vanilla bug, same root cause across all `fixed_range` uses in this file. **9+ occurrences per session.**

### `common/treaty_articles/05_transfer_money.txt:149` — Div/0 in `inherent_accept_score`

```
Div/0 near common/treaty_articles/05_transfer_money.txt:149
```

Vanilla's `inherent_accept_score` script value contains `divide = scope:article.input_quantity` calls gated by `if = { limit = { exists = scope:article.input_quantity } }`, but the engine evaluates the full script-value tree before applying the `if` gate (same family as the `command_values.txt:373` bug above). Mod also adds `divide = gdp` tier blocks in the same script value, which may amplify the count when source/target country has near-zero GDP. Reports the line of the containing `inherent_accept_score = { ... }` block, not the actual divide line. **160 occurrences** in a single 1.13 mod session.

### `events/iberia_events/ip4_coup_events.txt:562` — Div/0 in `add_radicals` divisor

```
Div/0 near events/iberia_events/ip4_coup_events.txt:562
```

The Spanish-coup (`ip4`) golpista-radicalisation block computes `add_radicals = { value = { add = scope:golpista_general.num_units_share divide = owner.army_size } }` and `owner.army_size` is 0 in some evaluation contexts (e.g. owner has no standing army at coup-resolution time). Vanilla bug. **6 occurrences** in a single 1.13 mod session.

### `common/dynamic_country_names/00_dynamic_country_names.txt:832` — `owns_entire_state_region` in country_definition scope

```
Error: owns_entire_state_region trigger [ Wrong scope for trigger: country_definition, expected country ]
```

Dynamic-country-name `trigger` blocks evaluate in `country_definition` scope, but the entry around line 832 (Centrocaspian Dictatorship and similar) calls `owns_entire_state_region`, which requires `country` scope. Vanilla bug — should be wrapped in a `country = { ... }` accessor or use a country_definition-compatible alternative.

### `common/on_actions/00_on_actions_yearly.txt:559` — `c:JAP`/`c:CHI` compared without `exists` guard

```
Error: Event target link 'c' returned an unset scope
Error: Invalid left side during comparison 'c'
```

The Ryukyu-rivalry `coin_toss` trigger does `c:CHI = this` / `c:JAP = this` without first checking `exists = c:CHI` / `exists = c:JAP`. When either tag isn't on the map (released, formed, or yet-to-spawn), the engine logs both errors. Vanilla bug.

### `common/journal_entries/07_hokkaido.txt:24` — `s:STATE_HOKKAIDO.region_state:JAP` unset

```
Error: Failed to scope to country by tag 'JAP'
Error: Event target link 'region_state' returned an unset scope
```

The Hokkaido JE's `possible` block reaches `s:STATE_HOKKAIDO.region_state:JAP` without checking whether `c:JAP` exists or owns any part of Hokkaido. When JAP isn't on the map (released, replaced by another tag, or absent in scenario start), the trigger fails. Vanilla bug.

### `common/journal_entries/00_communism.txt`, `events/communism.txt`, `events/election_events/*.txt` — `leader = { ... }` without `has_leader` guard

Affected vanilla files (all share the same root cause):
- `common/journal_entries/00_communism.txt:185`
- `events/communism.txt:526`
- `events/psychology_events.txt:26`
- `events/pm_events.txt:313`
- `events/election_events/election_liberal_events.txt:219`
- `events/election_events/election_contextual_events.txt:243`
- `events/election_events/election_neutral_events.txt:31`
- `events/election_events/election_conservative_events.txt`
- `events/election_events/election_moderate_events.txt`
- `events/election_events/election_generic_events.txt`
- `events/election_events/election_other_parties_events.txt`
- `events/election_events/communist_fascist_election_events.txt`

```
Error: Could not get leader of interest group
Error: Event target link 'leader' returned an unset scope
```

`je_vanguard`, the related communism-event option, and most election-event branches iterate `any_interest_group = { leader = { ... } }` without first checking `has_leader = yes`. Marginal IGs and IGs in newly-formed or recently-released countries can lack a leader for several months. Vanilla pattern across multiple content systems — affects every country running these JEs/events while an IG is leaderless.

### `common/treaty_articles/18_acquire_monopoly_for_company.txt` — `Event target link 'type' returned an invalid object`

```
Error: Event target link 'type' returned an invalid object
```

Vanilla acquire-monopoly-for-company article references `scope:article.input_building_type` (and chained `type` lookups) in trigger contexts where the article scope hasn't bound the building_type yet. Surfaces when the article appears in a treaty draft before the input_building_type is selected. **57+ occurrences** in a single 1.13 mod session.

### `common/war_goal_types/03_conquer_state.txt:156-185` — `has_strategic_region_interest_tier` invalid country/region

```
Error: has_strategic_region_interest_tier trigger [ Invalid Country or StrategicRegion! ]
```

The `conquer_state` AI evaluation block calls `has_strategic_region_interest_tier` in scopes where either the country or strategic region argument doesn't resolve. Same family as `00_on_actions_monthly.txt:145`. Vanilla bug. **6+ occurrences per session.**

### `common/scripted_triggers/wonder_triggers.txt:65` — scope-dependent loc inside any-trigger

```
state_this_equal: Scope dependent values in localization inside an any trigger; consider using a custom_tooltip
```

Vanilla wonder trigger uses scope-dependent localization tokens inside an any-trigger context, which the engine warns about every iteration. **2500+ occurrences per session** in observer-mode. Cosmetic warning only.

### `common/on_actions/00_code_on_actions.txt:7300-7400` — intentional vanilla `debug_log` calls

Plain English messages emitted by intentional vanilla `debug_log = "..."` calls in election / party / revolution on-actions. Substring patterns that catch every variant:

```
Election Campaign
Party Created
Party Disbanded
Coalition Created
Coalition Disbanded
Society Created
Society Disbanded
```

Examples seen in the wild: `Election Campaign Started`, `Election Campaign Ended`, `Conservative Party Created`, `Revolutionary Coalition Disbanded`, `Fascist Party Created`, `Patriotic Party Created/Disbanded`, `Faith Party Created`, `Anarchist Society Disbanded`, `Agrarian Party Created/Disbanded`, `Free Trade Party Created/Disbanded`, `Communist Party Created`, `Christian Party Disbanded`, `Clerical Party Created`. These are debug telemetry, not errors. Recognize and skip — they dominate `mod_only=true` triage during election cycles because the categorizer can't distinguish intentional `debug_log` from real errors.

### `common/defines/00_defines.txt`, `common/defines/00_ai.txt` — define macro not specified warnings

```
defined in 'common/defines/
Maybe a define macro is missing
```

Vanilla defines that reference macros which aren't always set. Cosmetic warning during startup. Confirmed examples include `CIVIL_WAR_UPRISING_STATE_EXCESSIVE_ARMY_FRACTION`, `BUILDING_MAX_PROFIT_TO_PAUSE_HIRES`, `WORLD_MARKET_MONOPOLY_MIN_SHARE`, `HIGH_POP_THRESHOLD`, `ROLE_RULER`, `MIN_COMBAT_UNITS_FOR_MULTIPLE_COMMANDERS_*`, `RETIRE_COMMANDER_INTERACTION_KEY`, `COMMANDER_DESIRED_RANK_DISPARITY_*`, plus others — vanilla emits one entry per macro per startup.

### `common/laws/00_distribution_of_power.txt:1` — `set_only_legal_party_from_ig` + `remove_ruling_interest_group` on invalid IG

```
Error: set_only_legal_party_from_ig effect [ Invalid target interestgroup ]
Error: remove_ruling_interest_group effect [ InterestGroup is insurrectionary ]
```

Vanilla `law_single_party_state` (and adjacent governance laws) call `set_only_legal_party_from_ig` and `remove_ruling_interest_group` in `on_activate` blocks without guarding against insurrectionary or absent IGs. Same family as `00_victoria_ip4_scripted_effects.txt:449`. Vanilla bug.

### `gui/block_windows.gui:650` — malformed item desc

```
gui/block_windows.gui:650 - Malformed item desc '', item descriptions can only contain a single child and no properties
```

Vanilla GUI script for blocked-windows panel has a malformed item desc (empty string). Visual-only — single occurrence per session.

### `gfx/map/spline_network/military_route_graphics/02_railroad_vehicles.txt:7` — invalid `market` event target

```
Error: Event target link 'market' returned an invalid object
```

Vanilla railroad-vehicle graphics definition reads `market` in a scope where it's not bound. Surfaces in routine map-rendering ticks. Vanilla bug.

### `common/scripted_effects/00_victoria_ip4_scripted_effects.txt:449` — bad-state checks on coup IGs

```
Error: abandon_revolution effect [ InterestGroup's country doesn't have a valid growing revolution ]
Error: remove_ruling_interest_group effect [ InterestGroup is insurrectionary ]
```

Iberia DLC (IP4) coup-resolution scripted effects call `abandon_revolution` / `remove_ruling_interest_group` on IGs whose state doesn't match the effect's preconditions (no growing revolution to abandon, IG already insurrectionary). Vanilla bug — the effects should be guarded but aren't.

### `common/scripted_effects/00_lobby_effects.txt` — `change_appeasement` rejects `appeasement_relations_decreased`

```
Error: change_appeasement effect [ Appeasement change failed, check that 'appeasement_relations_decreased' is a valid appeasement reason
```

Vanilla `00_diplomatic_catalysts.txt` (lines 285, 292) passes `FACTOR = appeasement_relations_decreased` to a scripted effect that maps it onto `change_appeasement = { factor = $FACTOR$ }`. The engine reports `appeasement_relations_decreased` is not a valid appeasement *reason*, suggesting the field name should be `reason` rather than `factor` (or the vanilla token was renamed). Vanilla bug — single-occurrence so far, low priority.

### `common/ideologies/01_character_ideologies.txt:1781`, `:3365`, `:8438`, `:8671` — wrong-scope triggers in character/IG scope

```
Error: ig_approval trigger [ Wrong scope for trigger: character, expected interest_group ]
Error: is_in_government trigger [ Wrong scope for trigger: character, expected interest_group ]
Error: any_diplomatically_relevant_country trigger [ Wrong scope for trigger: character, expected country ]
Error: any_diplomatically_relevant_country trigger [ Wrong scope for trigger: interest_group, expected country ]
```

Vanilla character-ideology blocks call IG-scope or country-scope triggers (`ig_approval`, `is_in_government`, `any_diplomatically_relevant_country`) without the right enclosing scope. Vanilla bug across multiple ideologies (e.g. integralist `lawmaker_ideology` and `non_loyalist_political_strength` at `:8438`/`:8671` forget the `owner ?= { ... }` wrap that vanilla applies correctly at `:4705`/`:4941` for the same trigger). Surfaces in mod's auto-generated `common/ideologies/modified.txt` because `apply_ideologies.py` faithfully replays the vanilla content (so the error references both the vanilla source and the regenerated copy). Will go away when vanilla fixes it — do not patch around it in `ideology_modifications.py`.

### `events/iberia_events/ip4_coup_events.txt:401` — `capital` effect in character scope

```
capital effect [ Wrong scope for effect: character, expected country ]
ip4_coup_events.txt:401
```

Vanilla IP4 coup-resolution event calls `capital = ...` on a character scope where it expects country scope. Single-line bug. Skip.

### `events/movement_events.txt:815`/`:820` — `Undefined event target 'relevant_state'` cascading into wrong-scope effects

```
movement_events.txt:815
movement_events.txt:820
Undefined event target 'relevant_state'
```

Vanilla political-movement event references `event_target:relevant_state` where it's not bound in the immediate scope; cascade emits "unset scope" + `add_loyalists_in_state` / `add_modifier` "Wrong scope for effect: none". Single root cause, three log lines — recognize as one vanilla bug, not three.

### `events/agitators_events/coup_events.txt:983`/`:984` — `Undefined event target 'legacy_of_democracy_state'` cascading into wrong-scope effects

```
coup_events.txt:983
coup_events.txt:984
Undefined event target 'legacy_of_democracy_state'
```

Same pattern as `movement_events.txt:815`. Vanilla coup-event references an unbound event target; cascades into `add_radicals_in_state` / `add_modifier` "Wrong scope for effect: none". One vanilla bug, three log lines.

### `events/ig_suppression_events.txt:1016` — `Event target link 'scope' returned an invalid object`

```
ig_suppression_events.txt:1016
Event target link 'scope' returned an invalid object
```

Vanilla IG-suppression event accesses a saved scope that has been invalidated by the time the option fires. Vanilla bug. Skip.

### `common/treaty_articles/31_ship_transfer.txt:54` — `Event target link 'scope' returned an invalid object`

```
31_ship_transfer.txt:54
```

Vanilla ship-transfer treaty article references a scope that's invalidated during certain treaty-evaluation paths. High repeat count under treaty-heavy gameplay. Vanilla bug. Skip.

### `events/agitators_events/land_ownership_law_events.txt:945`/`:946` — `Undefined event target 'farmer_wealth_concentration_state_scope'` cascading into wrong-scope effects

```
land_ownership_law_events.txt:945
land_ownership_law_events.txt:946
Undefined event target 'farmer_wealth_concentration_state_scope'
```

Same pattern as `movement_events.txt:815` and `coup_events.txt:983`. Vanilla `land_ownership_law_events.7` option `c` references an unbound `scope:farmer_wealth_concentration_state_scope`; cascades into "unset scope" + `add_radicals_in_state` "Wrong scope for effect: none". One vanilla bug, three log lines.

### `events/slave_revolts.txt:38` — `Could not get leader of interest group` in revolt-synthesized country

```
slave_revolts.txt:38
Could not get leader of interest group
Event target link 'leader' returned an unset scope
```

Vanilla slave/peasant-revolt event walks `every_interest_group` and reads `leader` on each, but revolt-synthesized countries (e.g. "Indian Peasant Revolt") have IGs with no leader set yet. Six IG names per occurrence (`Armed Forces`, `Anglican Church`, `Industrialists`, `Landowners`, `Petite Bourgeoisie`, …) — recognize as one vanilla bug per revolt, not six. Skip.

### `events/india_events/princely_states.txt:61` — `change_relations` same-country self-loop

```
princely_states.txt:61
change_relations effect [ Trying to change relations between the same country
```

Vanilla princely-states event has `change_relations` between two scope refs that resolve to the same country (commonly seen with Oudh). Vanilla bug; the event is missing a `NOT = { this = scope:other }` guard. Skip.

### `events/royal_wedding.txt:351` — `remove_character_role` on character without that role

```
royal_wedding.txt:351
remove_character_role effect [ Attempting to remove role that character does not have
```

Vanilla royal-wedding event removes a role that the chosen wedding character doesn't carry. Vanilla bug; should be wrapped in `has_role = X` limit. Skip.

### `events/peoples_springtime.txt:693, 1111, 1112, 1124` — multiple revolution/variable errors

```
peoples_springtime.txt:693
peoples_springtime.txt:1111
peoples_springtime.txt:1112
peoples_springtime.txt:1124
abandon_revolution effect [ InterestGroup's country doesn't have a valid growing revolution
add_ruling_interest_group effect [ InterestGroup is insurrectionary
remove_ruling_interest_group effect [ InterestGroup is insurrectionary
Failed to fetch variable for 'springtime_timer_var' due to not being set
Event target link 'var' returned an unset scope
Invalid left side during comparison 'var'
```

Vanilla 1848-Springtime event chain has multiple flaws: `abandon_revolution` is called without checking the country still has a growing revolution; `add_ruling_interest_group` / `remove_ruling_interest_group` are called on insurrectionary IGs (not legal); and `springtime_timer_var` is read before it's been set in some branches. All vanilla bugs across the same 1848-Springtime event tree. Skip.

### `common/on_actions/00_on_actions_monthly.txt:206` — `retire_character` on already-dead character

```
00_on_actions_monthly.txt:206
retire_character effect [ Character is already dead
```

Vanilla character-aging on-action calls `retire_character` without a `is_alive = yes` guard. Vanilla bug. Skip.

### `events/japan_events/ep2_shogunate_events.txt:726`, `events/soi_events/00_lobbies_events_03.txt:503`, `events/psychology_events.txt:136`, `events/brazil/pedro_brazil_events.txt:1042` — `ruler = { ... }` without `has_ruler` guard

```
ep2_shogunate_events.txt:726
00_lobbies_events_03.txt:503
psychology_events.txt:136
pedro_brazil_events.txt:1042
Event target link 'ruler' returned an invalid object
```

Vanilla event triggers read `ruler = { ... }` properties without an outer `has_ruler = yes` guard. Throws when the country has no ruler (vacant throne, revolt-synthesized country, regency edge cases). Same root cause across all four files; recognize as one vanilla pattern, not four. Likely more files share this — match the message `Event target link 'ruler' returned an invalid object` for any new occurrence.

### `common/scripted_effects/00_victoria_ep2_scripted_effects.txt:1177` (called from `common/journal_entries/07_iwakura_mission.txt`) — `var:current_expedition_location_var` unset

```
00_victoria_ep2_scripted_effects.txt:1177
07_iwakura_mission.txt
Event target link 'var' returned an invalid object
Could not get country from scope!
```

Vanilla Iwakura-mission scripted effect reads `var:current_expedition_location_var.techs_researched` without checking the variable is set. When the expedition location var is unset (expedition not yet dispatched / cleared), the chain throws "var invalid" + "Could not get country from scope". Same family as the unset-event-target cascade. Vanilla bug. Skip.

### `events/agitators_events/agitators_law_events.txt:921` — `Undefined event target 'supporting_ig'` cascading into wrong-scope effects

```
agitators_law_events.txt:921
Undefined event target 'supporting_ig'
```

Same pattern as `movement_events.txt:815`, `coup_events.txt:983`, and `land_ownership_law_events.txt:945`. Vanilla `agitators_law_events.9` option `b` references an unbound `scope:supporting_ig`; cascades into "unset scope" + `add_modifier` "Wrong scope for effect: none". One vanilla bug, three log lines.

### `events/agitators_events/revolution_events_01.txt:1291` — `Event target link 'home_country' returned an invalid object`

```
revolution_events_01.txt:1291
Event target link 'home_country' returned an invalid object
```

Vanilla revolution event reads `home_country` on a scope where it isn't always set (typically when the referenced character has no recorded home_country). Engine logs the failure and skips the dependent effect. No mod-side fix.

### `common/scripted_effects/00_government_type_change_effects.txt:19, 20` (called from `common/government_types/05_council_republics.txt`) — `get_ruler_for` unset cascading into `set_character_as_ruler` wrong-scope

```
00_government_type_change_effects.txt:19
00_government_type_change_effects.txt:20
05_council_republics.txt
Event target link 'get_ruler_for' returned an unset scope
set_character_as_ruler effect [ Wrong scope for effect: none, expected character ]
```

Vanilla council-republics government-type transition tries to install a ruler via `scope:country.get_ruler_for = ...` when the country has no eligible ruler character; the second error is the classic cascade from the first (the now-`none` scope passed into `set_character_as_ruler`). One vanilla bug, two log lines.

### `events/iberia_events/ip4_anarchism_events.txt:610` — `Event target link 'civil_war_origin_country' returned an invalid object`

```
ip4_anarchism_events.txt:610
Event target link 'civil_war_origin_country' returned an invalid object
```

Vanilla anarchism event reads `civil_war_origin_country` on a scope where the saved scope is unset (typically when fired outside a civil-war revolt-spawned context). Engine logs the failure and skips the dependent effect; can fire hundreds of times per game tick if the calling iterator is broad. Same shape as `revolution_events_01.txt:1291` (`home_country` invalid). No mod-side fix.

### `events/iberia_events/regency_events.txt:114-120` — `Undefined event target 'ig_candidate_1'` cascading into wrong-scope effects/triggers

```
regency_events.txt:114
regency_events.txt:115
regency_events.txt:116
regency_events.txt:120
Undefined event target 'ig_candidate_1'
Event target link 'scope' returned an unset scope
set_character_as_ruler effect [ Wrong scope for effect: none, expected character ]
set_variable effect [ This scope doesn't support variables. Scope: empty ]
is_immortal trigger [ Wrong scope for trigger: none, expected character ]
```

Iberian regency event references `scope:ig_candidate_1` without ensuring the saved scope was established earlier in the chain. Cascades into multiple wrong-scope effects/triggers downstream — same shape as `movement_events.txt:815` and `agitators_law_events.txt:921`. One root cause, five log lines.

## Expected mod-override noise

These warnings are emitted by the engine when this mod intentionally overrides vanilla content via the `localization/english/replace/` convention. They're not bugs — they're the engine reporting that an override is happening — but they dominate triage and should be filtered. Registered here so the autoflag system tags them as known noise.

### `localization/english/replace/*.yml` — intentional vanilla loc overrides

```
'localization/english/replace/
```

Mod overrides hundreds of vanilla loc keys via the `replace/` directory convention. Files include `timeline_extended_override_l_english.yml` (goods, laws, concepts, modifiers, buildings, ships, companies, …), `headlines_overrides_l_english.yml` (notification text), `LARP_interfaces_l_english.yml` (radicals/loyalists/GDP tooltips), and similar. The engine emits a "Key X defined in multiple files" warning for each. Expected — not actionable. The signature substring matches any path under `localization/english/replace/`.

### `00_code_on_actions.txt:7362`/`:7370` — vanilla intentional party-creation/disband debug_log calls

```
00_code_on_actions.txt:7362
00_code_on_actions.txt:7370
```

Vanilla `00_code_on_actions.txt` contains `debug_log = "<Phrase> Created"` (line 7362) and `debug_log = "<Phrase> Disbanded"` (line 7370) calls that fire on every political party creation/disband. They dominate `debug.log` mod-only triage during election cycles (one entry per party event, deduped to ~10–50 distinct phrases per session). Always skip — these are vanilla-intentional and not fixable from the mod. The signature matches both line numbers via the source file basename + line ref.

### `gui/companies_panel.gui:1` — vanilla GUI parse warnings

```
gui/companies_panel.gui:1
```

Vanilla `companies_panel.gui` line 1 emits `using '' is outside of all descriptions` and `Could not find template ''` warnings. The line is just a comment header, so this is the engine getting confused by something earlier in load order. Vanilla file, not in mod, not actionable.

### `gui/00_GDPPP_graph_tooltips.gui` and `gui/00_GDPPP_politics_panel_types.gui` — workshop mod (GDP-per-province) GUI overrides

```
gui/00_GDPPP_
```

Workshop mod 3190466673 ("GDP Growth Rate Improved" / GDPPP) registers GUI templates that collide with vanilla, emitting `Template 'X' already registered` and `Type 'X' already registered` warnings. Third-party mod, not ours — skip. Both basenames are also in `EXTERNAL_MOD_SOURCE_FILES` so error/debug triage drops them via the lower-level filter; the registry entry exists so they're tagged in gui.log too (where `include_external` defaults to `true`).

## Engine noise (source-anchored)

These entries are filtered via the `- source: \`<cpp_file:line>\`` registry mechanism. The parser indexes them by `entry.source` (the cpp emit point reported by the engine) instead of script-file basename, so messages that have no `entry.files` still get tagged. Each entry's signature substring narrows the filter to the specific message — different errors from the same cpp:line still surface.

### `building_manager.cpp:1792` — vanilla auto-charter duplicate building seeding
- source: `building_manager.cpp:1792`

```
Tried to create building of Type building_company_basic_
```

Vanilla company-charter auto-creation tries to create the same `building_company_basic_<good>` building twice on save-restore (or initial seeding). Engine skips the second create and logs informationally. Not a mod bug.

### `game_telemetry.cpp:451` — vanilla telemetry "Unknown tooltip type"
- source: `game_telemetry.cpp:451`

```
Unknown tooltip type
```

Vanilla analytics/telemetry message, not an error. Not actionable.

### `pdx_font.cpp:88` — informational font-load messages
- source: `pdx_font.cpp:88`

```
Loading Font File
```

Informational engine logging during font loading (~56 entries per session). Not errors. Anchor + signature ensures only literal font-load info is hidden — any genuine `pdx_font.cpp:88` error with a different message would still surface.

### `defines.cpp:230` — Jomini engine-shared `00_audio_persistent_objects.txt` define warnings
- source: `defines.cpp:230`

```
Define 'name' defined in 'common/defines/00_audio_persistent_objects.txt' not specified. Maybe a define macro is missing
Define 'scope' defined in 'common/defines/00_audio_persistent_objects.txt' not specified. Maybe a define macro is missing
```

The referenced file lives at `<install>/jomini/common/defines/00_audio_persistent_objects.txt` (Jomini engine-shared, not in the Victoria 3 `game/` tree), and the `'name'` / `'scope'` defines it declares are placeholder slots that the engine never resolves a macro for. Pure engine noise on every load — not vanilla-game and not mod-modifiable.

### `virtualfilesystem.cpp:388` — VFS "Done enumerating" trace for `gfx/frontend/interface/frontend/startscreen.dds`
- source: `virtualfilesystem.cpp:388`

```
Done enumerating 'gfx/frontend/interface/frontend/startscreen.dds'
```

Informational VFS trace line (mis-tagged as `missing_file` by the categorizer because the wording overlaps with missing-file phrasing). The file exists in vanilla `<install>/gfx/frontend/...`. Not actionable. The companion `:420` "Starting pre-enumerating" line is registered separately below — different source token, same root cause.

### `virtualfilesystem.cpp:420` — VFS "Starting pre-enumerating" trace for `gfx/frontend/interface/frontend/startscreen.dds`
- source: `virtualfilesystem.cpp:420`

```
Starting pre-enumerating 'gfx/frontend/interface/frontend/startscreen.dds'
```

Companion to the `:388` entry above — same VFS pre-enumeration cycle, same harmless trace, different cpp emit point.

### `pdx_persistent_reader.cpp:268` — save-game scan key-reference and province-reference parse warnings
- source: `pdx_persistent_reader.cpp:268`

```
Failed to read key reference: : , near line:
Invalid read of province reference, no string & no number
```

The persistent reader scans every file under the saves directory at startup and emits this warning for entries whose key/value layout doesn't fit the expected schema (legacy save formats, partially-written autosaves, third-party tools' artifacts). The `entry.files` field is empty for the bare-line variants and references `save games/*.v3` for the named ones. The "Invalid read of province reference" variant fires from the same source for unset province-id fields encountered during the same save scan. Non-actionable from script — categorized as `script_parse_error` purely on the wording, but no mod (or vanilla) `.txt` is involved. ~1100/session in this user's setup; volume scales with how many save files exist on disk.

### `journal_entry_manager.cpp:370` — revolt-spawned countries duplicate every parent JE
- source: `journal_entry_manager.cpp:370`

```
already has a journal entry of type
```

When a revolt secession spawns a new secondary-formation country (e.g. "Swedish Liberal Revolt", "Indori Peasant Revolt", "Khairpuri Communist Revolt"), the engine seeds it with journal entries inherited from the parent country, then immediately re-runs JE-seeding on-actions that try to add the same entries again. The manager emits one warning per duplicate. Volume scales with how many JEs the parent country has — mod content (`je_banking_cycle`, `je_covert_warfare`, `je_global_warming`, etc.) appears alongside vanilla JEs (`je_sale_of_alaska`, `je_german_unification`, …) in the duplicate list, because both sets are valid on the parent. **The mod does not mass-add JEs via `on_country_creation` or any other revolt-related on-action** — verified by grepping `common/on_actions/`. Vanilla revolt creation is the source. Cosmetic — the engine de-duplicates and keeps the existing JE.

### `jomini_script_system.cpp:247` — invalid `religion` event-target in cross-religion comparisons

```
common/script_values/01_power_bloc_values.txt:56
common/script_values/modified.txt:52
common/coat_of_arms/template_lists/coa_templates.txt:141
common/character_interactions/00_character_interactions.txt:297
```

Vanilla uses the pattern `religion = scope:X.religion` unguarded — `power_bloc_leverage_gain` (`01_power_bloc_values.txt:56`), the coat-of-arms religion-match template (`coa_templates.txt:141`), and the character "Convert" interaction (`00_character_interactions.txt:297`). When the right-hand scope evaluates to a country lacking a state religion (e.g. revolt-synthesized countries during their creation window), the engine emits `Event target link 'religion' returned an invalid object`. The mod's `common/script_values/modified.txt` is an override of `01_power_bloc_values.txt` carrying the same line; same noise re-emerges under the mod filename. Mod's own treaty article `common/treaty_articles/106_religious_mission_rights.txt` was hardened with `exists = scope:target_country` / `exists = scope:source_country` guards (2026-05-10), so it is no longer in this list. Cosmetic — comparisons that fail simply don't fire their accept-score branch.

### `common/war_goal_types/00_annex_country.txt:93, :114, :148, :155` — invalid country/strategic-region scope

```
common/war_goal_types/00_annex_country.txt:93
common/war_goal_types/00_annex_country.txt:114
common/war_goal_types/00_annex_country.txt:148
common/war_goal_types/00_annex_country.txt:155
```

Parallel to the existing `03_conquer_state.txt:156-185` entry. `00_annex_country.txt` uses `scope:target_country` and `has_strategic_region_interest_tier` triggers without `exists = scope:target_country` guards; when the play-evaluation runs against an unset target (`Country  (4294967295)`), the cascade fires "Scoped object of type 'country' is not valid". Cosmetic — the trigger short-circuits to false.

### `common/journal_entries/00_east_indies.txt:7`, `:12`, `00_opium_wars.txt:7`, `01_ryukyu_rivalry.txt:16`, `02_acre_dispute.txt:8`, `00_german_unification.txt:12` — `c:XXX` unset-scope cascade

```
common/journal_entries/00_east_indies.txt
common/journal_entries/00_german_unification.txt
common/journal_entries/00_opium_wars.txt
common/journal_entries/01_ryukyu_rivalry.txt
common/journal_entries/02_acre_dispute.txt
```

Parallel to the existing `common/on_actions/00_on_actions_yearly.txt:559` entry — vanilla JE definitions reference country tags via `c:XXX` (e.g. `c:GBR`, `c:NDL`, `c:JAP`, `c:CHI`) at the top-level `possible` or `scope` block without `exists = c:XXX` guards. When the referenced country doesn't exist in the world (e.g. has been annexed or never spawned), the engine emits the paired "Event target link 'c' returned an unset scope" + "Invalid left side during comparison 'c'" cascade on the same line. Cosmetic — JE simply doesn't activate.

### `events/secession_situations.txt:418` — `Could not get leader of interest group 'Industrialists'` in revolt-synthesized country

```
Could not get leader of interest group 'Industrialists' in country
events/secession_situations.txt:418
```

Parallel to the existing `events/slave_revolts.txt:38` entry. Vanilla secession event reads the Industrialists IG leader on a freshly-synthesized revolt country before its IGs have been populated with characters. Casts as a `leader returned an unset scope` cascade on the same line. Cosmetic — null leader is handled gracefully downstream.

### `jomini_mapobject_manager.cpp:3509` — invalid camera index 0
- source: `jomini_mapobject_manager.cpp:3509`

```
CMapObjectManager::GetVisibleObjects: invalid camera index 0 requested
```

Engine graphics noise emitted during early frame setup. No mod or vanilla script involvement.

### `pdx_assert.cpp:637` — "The null hierarchy will never have social classes"
- source: `pdx_assert.cpp:637`

```
The null hierarchy will never have social classes associated with it
```

Engine-internal assertion fired during pop-strata setup when an empty hierarchy is queried. `pdx_assert.cpp:637` is shared with several other distinct assertions (the `building_company_basic_*` duplicate-building entries above, the Mobilize-Army entry below) — the signature substring is what disambiguates this one. Cosmetic.

### `pdx_assert.cpp:637` — "Mobilize Army Commmand given an invalid army"
- source: `pdx_assert.cpp:637`

```
Mobilize Army Commmand given an invalid army
```

Engine assertion (note the typo `Commmand` is in vanilla's source string — match it verbatim) fired when the AI sends a Mobilize Army command targeting an army that has since been disbanded or merged. Cosmetic.

### `pdx_online_telemetry.cpp:25` — engine telemetry dump on graphics-settings init
- source: `pdx_online_telemetry.cpp:25`

```
[telemetry]
```

Informational dump of resolved graphics settings (quality, shadowmap_resolution, texture_quality, anti_aliasing, scale, …). Fires once per launch as the engine pushes settings to its telemetry sink. Not an error — the categorizer tags it `other` because there's no script context to classify against.

### `pdx_json_settings.cpp:425` — settings-write skip notice on shutdown
- source: `pdx_json_settings.cpp:425`

```
[SPdxJsonSettingsIO]
```

Informational `Category:"X" Setting:"Y" won't be written` lines emitted as the engine reconciles in-memory settings against disk on shutdown — entries marked transient are intentionally skipped. Not an error.

### `player.cpp:153` — `DeleteAllPlayers` shutdown trace
- source: `player.cpp:153`

```
CJominiPlayers:::DeleteAllPlayers
```

Engine shutdown trace logging the player cleanup count. Not an error.

> **Mod-side cosmetic noise lives in `docs/audits/mod_known_noise.md`** — those entries aren't vanilla bugs, they're mod issues filtered for triage cleanliness but tracked in `open_issues.md` so they remain actionable. Filter via `?mod_noise=hide|only|show` (parallel to `?vanilla_bugs=`). For a fully clean view: `?vanilla_bugs=hide&mod_noise=hide`.

## How to triage a new error-log entry

1. Note the file path and line number from the error.
2. If the path begins with `common/...` and the file does NOT exist in this mod repo, it's a vanilla file. Check `<vanilla_source_repo_path>/game/<path>` (typically `~/src/vic3/game/...`) to see if vanilla has the same buggy line.
3. If yes: it's a vanilla bug — record it here and skip.
4. If the file exists in the mod, it may still be a vanilla content via auto-generation (e.g. `common/ideologies/modified.txt`); read the first lines for `# AUTO-GENERATED` header and check the upstream source (`<vanilla_source_repo_path>/game/...`, typically `~/src/vic3/game/...`).

## Reporting

For each entry above, the mod team has the option to file a Paradox bug report. Suggested title format: `[1.13] <file>:<line> — <one-line cause>`.
