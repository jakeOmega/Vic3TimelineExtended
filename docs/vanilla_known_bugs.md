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

### `common/ideologies/01_character_ideologies.txt:1781`, `:3365` — IG-scope triggers called in character scope

```
Error: ig_approval trigger [ Wrong scope for trigger: character, expected interest_group ]
Error: is_in_government trigger [ Wrong scope for trigger: character, expected interest_group ]
```

Vanilla character-ideology blocks call IG-scope triggers (`ig_approval`, `is_in_government`) in character scope, where they don't resolve. Vanilla bug across multiple ideologies. Surfaces in mod's auto-generated `common/ideologies/modified.txt` because `apply_ideologies.py` faithfully replays the vanilla content (so the error references both the vanilla source and the regenerated copy). Will go away when vanilla fixes it — do not patch around it in `ideology_modifications.py`.

## Expected mod-override noise

These warnings are emitted by the engine when this mod intentionally overrides vanilla content via the `localization/english/replace/` convention. They're not bugs — they're the engine reporting that an override is happening — but they dominate triage and should be filtered. Registered here so the autoflag system tags them as known noise.

### `localization/english/replace/*.yml` — intentional vanilla loc overrides

```
'localization/english/replace/
```

Mod overrides hundreds of vanilla loc keys via the `replace/` directory convention. Files include `timeline_extended_override_l_english.yml` (goods, laws, concepts, modifiers, buildings, ships, companies, …), `headlines_overrides_l_english.yml` (notification text), `LARP_interfaces_l_english.yml` (radicals/loyalists/GDP tooltips), and similar. The engine emits a "Key X defined in multiple files" warning for each. Expected — not actionable. The signature substring matches any path under `localization/english/replace/`.

## How to triage a new error-log entry

1. Note the file path and line number from the error.
2. If the path begins with `common/...` and the file does NOT exist in this mod repo, it's a vanilla file. Check `<vanilla_source_repo_path>/game/<path>` (typically `~/src/vic3/game/...`) to see if vanilla has the same buggy line.
3. If yes: it's a vanilla bug — record it here and skip.
4. If the file exists in the mod, it may still be a vanilla content via auto-generation (e.g. `common/ideologies/modified.txt`); read the first lines for `# AUTO-GENERATED` header and check the upstream source (`<vanilla_source_repo_path>/game/...`, typically `~/src/vic3/game/...`).

## Reporting

For each entry above, the mod team has the option to file a Paradox bug report. Suggested title format: `[1.13] <file>:<line> — <one-line cause>`.
