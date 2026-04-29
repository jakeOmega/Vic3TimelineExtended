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
