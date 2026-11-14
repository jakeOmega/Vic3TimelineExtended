# Mod Known Noise

Mod-side cosmetic log entries that are filtered from triage for cleanliness, but **tracked** in `docs/audits/open_issues.md` so they remain actionable. These are NOT vanilla bugs — they're mod issues we've chosen not to fix yet (zero functional impact, requires asset work or deeper investigation).

The registry parser at `game_log_reader.py` reads this file alongside `vanilla_known_bugs.md`. Entries here are tagged with `kind=mod_low_priority` and require a `- tracked: \`docs/audits/open_issues.md#anchor\`` cross-reference that the parser validates against the actual `open_issues.md` headings.

To audit "what's currently swept under the rug":

```
curl -s "http://localhost:8950/logs/<family>?vanilla_bugs=show&mod_noise=only" | \
  jq '.entries[] | {title: .vanilla_bug_ref.title, tracked: .vanilla_bug_ref.tracked_issue, msg: .message}'
```

The query parameter is `?mod_noise=hide|only|show` (parallel to `?vanilla_bugs=`). For a fully-clean triage view: `?vanilla_bugs=hide&mod_noise=hide`.

## Format

Same as `vanilla_known_bugs.md` — `### \`anchor\` — title` heading, optional `- source: \`<token>\``, mandatory `- tracked: \`docs/audits/open_issues.md#anchor\``, optional `- reviewed: helper anchor, signature cannot match a mod call (<why>)`, optional `- stack: vanilla only`, fenced code block of signature substrings (message text, never a bare file path: the loader warns on a path-only line, #873). The helper-anchor check covers this file too.

The `#anchor` must be the **GitHub** slug of the target `### ` heading in `open_issues.md`: lowercase, delete every character that is not a word char / hyphen / space (so `_` survives but `.`, `:`, backticks and parens vanish outright — they are *not* turned into dashes), then space → `-`; repeated headings get a `-N` suffix. Line-number fragments like `#L8` do **not** resolve on GitHub. `POST /validate/registries` re-checks every anchor in milliseconds.

## Entries

### `harvest_condition_graphics.cpp:52` — missing sound-entity states for mod market harvest conditions
- source: `harvest_condition_graphics.cpp:52`
- tracked: `docs/audits/open_issues.md#l7-mod-harvest-condition-sound-entity-states-missing`

```
Couldn't find any animation state for harvest condition type
```

Mod adds `bull_market` / `bear_market` / `market_downturn` / `financial_panic` as harvest condition types in `common/harvest_condition_types/extra_harvest_condition_types.txt` for banking-cycle visualization. Vanilla `harvest_condition_sound_entity` has no matching states. Functional impact: silent — engine just doesn't play a sound. Fix recipe in `docs/audits/open_issues.md#l7-mod-harvest-condition-sound-entity-states-missing`.

### `pdx_gui_factory.cpp:628` — `gui/tooltip.gui:328 - Could not find template 'vertical_scrollbar'`
- source: `pdx_gui_factory.cpp:628`
- tracked: `docs/audits/open_issues.md#l8-mod-tooltipgui-vertical-scrollbar-template-warning`

```
Could not find template 'vertical_scrollbar'
```

Mod's scrollable `FancyTooltipWidgetType` uses `scrollbar_vertical = { using = vertical_scrollbar }` — the same exact pattern vanilla uses successfully (vanilla `block_windows` and `building_browser_panel` files do the same and don't error). Likely parse-time false-positive resolved in pass-2; scrollable tooltip rendering works in-game. Tracked at `docs/audits/open_issues.md#l8-mod-tooltipgui-vertical-scrollbar-template-warning` until a way to silence it surfaces.

### `gfx_dds_loader.cpp:442` — historical-company icon DDS dimensions not multiple of 4
- source: `gfx_dds_loader.cpp:442`
- tracked: `docs/audits/open_issues.md#l9-mod-dds-dimensions-historical-company-icons`

```
Block compressed texture 'gfx/interface/icons/company_icons/historical_company_icons/japanese_toyota.dds'
Block compressed texture 'gfx/interface/icons/company_icons/historical_company_icons/korean_samsung.dds'
Block compressed texture 'gfx/interface/icons/company_icons/historical_company_icons/american_google.dds'
Block compressed texture 'gfx/interface/icons/company_icons/historical_company_icons/russian_rosatom.dds'
```

Block-compressed (BC1/BC3) DDS textures need multiple-of-4 width and height; these four mod-side historical-company icons fail that constraint and emit edge-artifact warnings once per file at load. Visual-only — engine still loads the texture. Fix requires re-export through the image pipeline; tracked at `docs/audits/open_issues.md#l9-mod-dds-dimensions-historical-company-icons`.

### `jomini_effect.cpp:1135` — variables set for localization tooltip read flagged unused
- source: `jomini_effect.cpp:1135`
- source: `jomini_effect.cpp:1140`
- tracked: `docs/audits/open_issues.md#l10-mod-loc-only-variables-flagged-unused`

```
is set but is never used. Note that use in localization doesn't count
```

Mod uses `set_global_variable` to expose values (cultural-hegemony per-rank breakdowns, nuclear stockpile per-rank) to tooltip text via `GetGlobalVariable('…')` in `localization/english/te_concepts_l_english.yml`. The engine explicitly notes loc reads don't count as uses, so each variable emits an "unused" warning at load. By-design; rearchitecting all loc tooltips to use script values instead would be a large refactor with no functional gain. Tracked at `docs/audits/open_issues.md#l10-mod-loc-only-variables-flagged-unused`.

### `jomini_custom_text.h:91` — banking-cycle JE title custom-loc scope-validation burst
- source: `jomini_custom_text.h:91`
- tracked: `docs/audits/open_issues.md#l11-banking-cycle-je-title-custom-loc-scope-validation-burst`

```
not valid for 'te_banking_cycle_title'
```

The Banking Cycle JE name varies by economic law via `[GetPlayer.GetCustom('te_banking_cycle_title')]` (a `type = country` custom loc). The title renders correctly, but the engine emits `Object of type 'country' is not valid for 'te_banking_cycle_title'` in a ~83-write burst per panel render (error.log only). No visual or gameplay effect — only a brief synchronous-write hitch on panel open. User opted to keep the dynamic title; candidate fix (match the JE render context's scope chain instead of `GetPlayer`) deferred. Tracked at `docs/audits/open_issues.md#l11-banking-cycle-je-title-custom-loc-scope-validation-burst`.

### `modifier_type_definition_database.cpp:43` — script-only mod modifier types have no engine-code consumer
- source: `modifier_type_definition_database.cpp:43`
- tracked: `docs/audits/open_issues.md#l12-script-only-modifier-types-emit-defined-in-script-but-not-in-code-by-design`

```
is defined in script but not in code
```

~120 mod-defined modifier types (covert_warfare, space_race, banking, strategic-reserve, ~50 `*_pb_principles_bool`, etc.) each emit this once at load. Verified benign (2026-05-24): same construct as vanilla's `03_modifier_types_script_only.txt`; recognized by `/modifier-search`, pass `modifier_visibility_audit`, applied via static_modifiers/techs, and read via `modifier:X` in script values. The warning only means no engine *code* reads them — correct for script-side custom modifiers. Unfixable without deleting the systems. Tracked at `docs/audits/open_issues.md#l12-script-only-modifier-types-emit-defined-in-script-but-not-in-code-by-design`.

### `jomini_eventmanager.cpp:440` — intentional vanilla-event override duplicate-ID notice
- source: `jomini_eventmanager.cpp:440`
- tracked: `docs/audits/open_issues.md#l13-mod-event-override-duplicate-event-id-notices`

```
Duplicated event ID 'formation.17' found
```

`events/te_formation_overrides.txt` deliberately redefines vanilla `formation.17`. The engine keeps `Previous` (the mod file) and rejects `New` (vanilla), so the override works; the notice is by-design. Signature pinned to the specific event ID so a *different* duplicated-ID collision still surfaces in triage. Tracked at `docs/audits/open_issues.md#l13-mod-event-override-duplicate-event-id-notices`.

### `jomini_effect.cpp:1139` — GUI-injected scopes flagged never-set
- source: `jomini_effect.cpp:1139`
- source: `jomini_effect.cpp:1144`
- tracked: `docs/audits/open_issues.md#l14-gui-injected-event-targets-flagged-never-set`

```
Event target 'base_market' is used but is never set
```

A `.gui` (or a loc string) that sets a scope with `AddScope('<name>', …)` for a script value to read as `scope:<name>` sets it where the parse-time validator cannot look, so the validator reports `Event target '<name>' is used but is never set` once per launch. The market-panel trade charts' `base_market` (`gui/market_panel.gui`, read in `common/script_values/gui_chart_script_values.txt`) was the first; the Strategic Reserve's `sr_rival` and the budget panel's rows (`gui/te_budget_generated_charts.gui`, read in `common/script_values/te_budget_generated_values.txt`, about 420 names) followed. They all work in game. The signature above is only the first name. The rest are tagged by `tag_gui_injected_scopes` in `game_log_reader.py`, which collects every `AddScope('<name>'` in the mod's `gui/` and English loc and tags exactly those names, so a never-set name that nothing sets still surfaces. Tracked at `docs/audits/open_issues.md#l14-gui-injected-event-targets-flagged-never-set`.

### `power_bloc_principle.cpp:139` — vanilla principles orphaned by REPLACE:principle_group
- source: `power_bloc_principle.cpp:139`
- source: `power_bloc_principle.cpp:138`
- tracked: `docs/audits/open_issues.md#l15-vanilla-principles-orphaned-by-replaceprinciple_group-overrides`

```
Principle principle_sacred_civics_
```

`REPLACE:principle_group_sacred_civics` swaps the vanilla group's members for the mod's `principle_sacred_civics_N_mod` variants; the vanilla `principle_sacred_civics_N` entries stay in the database groupless and log once each per launch. Group-less principles are unpickable → harmless. Tracked at `docs/audits/open_issues.md#l15-vanilla-principles-orphaned-by-replaceprinciple_group-overrides`.

### `country_law_manager.cpp:464` — deliberate historical law seeds lacking unlock tech (1.13.9 validation)
- source: `country_law_manager.cpp:474`
- source: `country_law_manager.cpp:464`
- source: `country_law_manager.cpp:462`
- tracked: `docs/audits/open_issues.md#l16-historical-law-seeding-vs-unlocking_technologies-retention-warnings-1139`

```
retain law Ministry of War Established
retain law National Bank Established
retain law Gold Standard
retain law Free & Mutual Banking
retain law Universal Banking (Light Prudence)
retain law Civic Monolingualism
retain law Multilingual Federalism
retain law Traditional IP Protection
retain law Colonial Slavery
retain law Legal Limbo
retain law Constitutional Review
retain law State-Led Language Reform
retain law Freedom of Contract
retain law Elected Bureaucrats
```

Vanilla 1.13.9 added load-time validation of active laws against `unlocking_technologies`. Two by-design mod cases (details at `docs/audits/open_issues.md#l16-historical-law-seeding-vs-unlocking_technologies-retention-warnings-1139`): deliberate historical seeds in `common/history/extra_history.txt` (Gold Standard, Kriegsministerium, the USA's Constitutional Review, Greece's and Serbia's State-Led Language Reform, …), and, since #1408 stopped the law sweep running mid-history, seeds the first monthly sweep replaces (Freedom of Contract, vanilla's Elected Bureaucrats). The lines for Intrusive Surveillance, Total War, State Secrets, Penal Labor Camps and Violent Hostility are not here: they were decentralized nations holding each group's first law for the whole game, not a transient, and are fixed (2026-11-05), so they should be gone and show if they return. Signatures enumerate these known laws ONLY, so a new law name appearing in this warning class still surfaces in triage. Tracked at `docs/audits/open_issues.md#l16-historical-law-seeding-vs-unlocking_technologies-retention-warnings-1139`.

### `jomini_eventmanager.cpp:376` — console-only debug test events reported orphaned
- source: `jomini_eventmanager.cpp:376`
- tracked: `docs/audits/open_issues.md#l23-console-only-debug-test-events-logged-as-orphaned-by-design`

```
Event te_debug_
Event te_tax_debug.
```

The `te_debug_<system>.1` test consoles in `events/te_debug_*_events.txt` are fired by hand with `event te_debug_<x>.1`. Nothing in script fires them, so each is logged as orphaned at load (ch, colonial_empire, covert, gw, nuclear, space_race, un as of 2026-09-19). The tax code's console (`te_tax_debug.1`–`.8`, `events/te_tax_debug_events.txt`) takes the other word order, so it has a signature of its own. By design. The signature is the `te_debug_` prefix only, not `is orphaned`, because signatures match if ANY line matches: an `is orphaned` line would also hide a real mod event that lost its trigger. A new console needs no change here. Tracked at `docs/audits/open_issues.md#l23-console-only-debug-test-events-logged-as-orphaned-by-design`.

### `event.cpp:358` — Grand Monuments v2 load-time notices
- source: `event.cpp:358`
- source: `event.cpp:410`
- source: `event.cpp:425`
- source: `jomini_effect.cpp:1139`
- source: `jomini_effect.cpp:1144`
- tracked: `docs/audits/open_issues.md#l26-grand-monuments-v2-load-time-notices`

```
No default option in event monument_events.11.
Flag 'leader' is used but is never set
```

Two lines once per launch. The skin choice has no `default_option` by design, and `flag:leader` is set as `flag:$DEDICATION$`, which the validator cannot see. Each signature names its own event or flag, so another event without a default or another never-set flag still shows up.

### `common/treaty_articles/31_ship_transfer.txt:58` — vanilla ship transfer's reciprocal check reads the mod's mutual articles
- tracked: `docs/audits/open_issues.md#l27-ship-transfer-reciprocal-check-reads-mod-mutual-articles`
- stack: vanilla only

```
Can only get target_country of directed article options.
Event target link 'target_country' returned an unset scope
Invalid left side during comparison 'target_country'
```

Vanilla's reciprocal-article check skips its own two mutual articles but not the mod's four, so a draft holding one logs these three lines; the check's outcome is still correct. Anchored on the vanilla article, with no mod frame in its stack, so the two generic lines can't hide a mod treaty's error. Tracked at `docs/audits/open_issues.md#l27-ship-transfer-reciprocal-check-reads-mod-mutual-articles`.

### `country.cpp:9608` — a construction queue with no construction to spend on it (unattributed)
- source: `country.cpp:9608`
- source: `country.cpp:9594`
- source: `country.cpp:9794`
- source: `country.cpp:9780`
- tracked: `docs/audits/open_issues.md#l28-zero-construction-speed-with-a-queued-project-unattributed`

```
The total construction speed is zero
```

The engine's estimate of a country's queue length divides by its construction speed, and logs this when that speed is zero. It names no country and no script, so the cause isn't known. 2026-10-24: 3,208 lines over three and a half hours of play, steady at 20 to 40 a minute from about half an hour after the launch, a third of every `error.log`; the 2026-10-11 observer runs logged it at `:9594` ("queues"), so it predates that day's builds. Vanilla 1.15 moved both lines, to `:9794` ("queue") and `:9780` ("queues"): 720 lines in the 2026-11-05/06 sessions, untagged until the two anchors were added. 2026-11-12 (1.15.1, a 1932–1939 game): about 1,000 an hour, all at `:9780`, so not grown. Tracked at `docs/audits/open_issues.md#l28-zero-construction-speed-with-a-queued-project-unattributed`.

### `common/decrees/extra_decrees.txt` — the engine checks a decree's country_trigger with no country
- tracked: `docs/audits/open_issues.md#l29-a-decrees-country_trigger-checked-with-no-country`

```
untyped trigger [ Scoped object of type 'country' is not valid (Country  (4294967295))
```

The engine re-checks each decree's `country_trigger` weekly (vanilla's decree file header: it "should invalidate the Decree on a weekly basis if found invalid"), and now and then it does so with the null country. Vanilla's own decrees log the same message in the same second, and the `<unknown>:0` untyped-trigger entry in the vanilla registry tags those; its `- stack: vanilla only` leaves this file's lines visible. Medical Outreach's trigger logged once on 2026-10-25. Script can't guard a root that is invalid before the block runs. Tracked at `docs/audits/open_issues.md#l29-a-decrees-country_trigger-checked-with-no-country`.

### `jomini_effect.cpp:1144` — culture merges: absorb results' generic gate reads flagged never-set
- source: `jomini_effect.cpp:1144`
- tracked: `docs/audits/open_issues.md#l30-culture-merges-absorb-results-generic-gate-reads-flagged-never-set`

```
Variable 'te_cm_home_r_brazilian' is used but is never set
Variable 'te_cm_home_r_dutch' is used but is never set
Variable 'te_cm_home_r_finnish' is used but is never set
Variable 'te_cm_home_r_han' is used but is never set
Variable 'te_cm_home_r_hindustani' is used but is never set
Variable 'te_cm_home_r_hungarian' is used but is never set
Variable 'te_cm_home_r_japanese' is used but is never set
Variable 'te_cm_home_r_persian' is used but is never set
Variable 'te_cm_joined_brazilian_brazilian' is used but is never set
Variable 'te_cm_joined_british_british' is used but is never set
Variable 'te_cm_joined_chinese_han' is used but is never set
Variable 'te_cm_joined_dutch_dutch' is used but is never set
Variable 'te_cm_joined_filipino_filipino' is used but is never set
Variable 'te_cm_joined_finnish_finnish' is used but is never set
Variable 'te_cm_joined_french_french' is used but is never set
Variable 'te_cm_joined_hindustani_hindustani' is used but is never set
Variable 'te_cm_joined_hungarian_hungarian' is used but is never set
Variable 'te_cm_joined_japanese_japanese' is used but is never set
Variable 'te_cm_joined_persian_persian' is used but is never set
Variable 'te_cm_switched_brazilian' is used but is never set
Variable 'te_cm_switched_dutch' is used but is never set
Variable 'te_cm_switched_finnish' is used but is never set
Variable 'te_cm_switched_han' is used but is never set
Variable 'te_cm_switched_hindustani' is used but is never set
Variable 'te_cm_switched_hungarian' is used but is never set
Variable 'te_cm_switched_japanese' is used but is never set
Variable 'te_cm_switched_persian' is used but is never set
Variable 'te_cm_wait_years_anglophone' is used but is never set
```

Twenty-eight lines once per launch, from the culture merges (#1509). Eleven merges absorb their parts into an existing culture (Hungarian, Han, Japanese ...), and that culture is the merge's first core slot, held and acceptance-tested but never joined, converted or switched (see the culture merges system file). The generator writes its slot's triggers and the census helper's call like any other part's, so its joined, switched and result-pop reads name variables nothing sets; Anglophone's wait counter is read by its optional parts' waits and only a core wait adds to it, as documented. The reads sit behind `has_global_variable` or `?=` and read false, as they should. Each signature names its own variable, so a new never-set culture-merge name still shows. The 2026-11-08 triage removed the other 129 such names (results no wider merge takes, and the console dump). Tracked at `docs/audits/open_issues.md#l30-culture-merges-absorb-results-generic-gate-reads-flagged-never-set`.

### `gamedatabase.h:378` — culture merges: the restated vanilla trigger drops vanilla's copy
- source: `gamedatabase.h:378`
- source: `gamedatabase.h:394`
- tracked: `docs/audits/open_issues.md#l31-culture-merges-the-restated-vanilla-trigger-logs-a-duplicated-key`

```
Duplicated key has_indian_primary_culture will not be created from file: common/scripted_triggers/00_scripted_triggers.txt
```

One line per launch, and it is the override working: `00_a_te_culture_merge_vanilla_triggers.txt` sorts before vanilla's file, the first bare definition of a scripted trigger wins, and the engine names the copy it dropped, vanilla's. The signature names vanilla's file on purpose: a line naming the mod's file means the mod's copy lost, and that one must not be filtered.

### `gamedatabase.h:394` — Base Construction Capacity: the one-setting copy drops vanilla's rule
- source: `gamedatabase.h:394`
- tracked: `docs/audits/open_issues.md#l32-base-construction-capacity-the-one-setting-copy-logs-a-duplicated-key`

```
Duplicated key free_construction will not be created from file: common/game_rules/00_game_rules.txt
```

One line per launch, and it is the copy working: `00_a_te_free_construction.txt` sorts before vanilla's file and `game_rules` keeps the first bare definition (read 2026-11-13, #1768). The signature names vanilla's file on purpose: a line naming the mod's file means the mod's copy lost, and that one must not be filtered.
