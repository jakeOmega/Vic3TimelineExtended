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

### `common/journal_entries/04_indian_famines.txt:25` and `common/journal_entries/03_afghanistan.txt:397-414` — invalid `region` event target

Same root cause as the AI strategy bug: `region` event target is invalid in the JE evaluation scope. **40+ occurrences total.**

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

### `common/on_actions/headlines_on_actions.txt:953` — `has_interest_marker_in_region` PostValidate fails

```
PostValidate of trigger 'has_interest_marker_in_region' returned false at common/on_actions/headlines_on_actions.txt:953
```

Vanilla headlines on-action reaches into a scope where `has_interest_marker_in_region` cannot resolve. **17 occurrences** in a single session. Same family as the strategic-region scope bugs above.

### `common/on_actions/headlines_tech_on_actions.txt:718` — `has_technology_researched` PostValidate fails

```
PostValidate of trigger 'has_technology_researched' returned false at common/on_actions/headlines_tech_on_actions.txt:718
```

Vanilla tech-headlines on-action evaluates `has_technology_researched` in a non-country scope (likely a target-pop / character context) where the trigger can't resolve. Vanilla bug.

### `common/ideologies/01_character_ideologies.txt:1781` — `ig_approval` in wrong scope

```
Error: ig_approval trigger [ Wrong scope for trigger: character, expected interest_group ]
```

The "less likely among more progressive IG's if they're angry and socialism is researched" block evaluates `ig_approval < 0` in character scope but the trigger requires interest_group scope. Vanilla bug. Surfaces in mod's auto-generated `common/ideologies/modified.txt` because `apply_ideologies.py` faithfully replays the vanilla content. Will go away when vanilla fixes it — do not patch around it in `ideology_modifications.py`.

## How to triage a new error-log entry

1. Note the file path and line number from the error.
2. If the path begins with `common/...` and the file does NOT exist in `/home/jakef/src/Vic3TimelineExtended/`, it's a vanilla file. Check `/home/jakef/src/vic3/game/<path>` to see if vanilla has the same buggy line.
3. If yes: it's a vanilla bug — record it here and skip.
4. If the file exists in the mod, it may still be a vanilla content via auto-generation (e.g. `common/ideologies/modified.txt`); read the first lines for `# AUTO-GENERATED` header and check the upstream source (`/home/jakef/src/vic3/game/...`).

## Reporting

For each entry above, the mod team has the option to file a Paradox bug report. Suggested title format: `[1.13] <file>:<line> — <one-line cause>`.
