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

### `pdx_gui_factory.cpp:628` — `gui/tooltip.gui:293 - Could not find template 'vertical_scrollbar'`
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
- tracked: `docs/audits/open_issues.md#l14-gui-injected-event-targets-flagged-never-set`

```
Event target 'base_market' is used but is never set
```

A `.gui` (or a loc string) that sets a scope with `AddScope('<name>', …)` for a script value to read as `scope:<name>` sets it where the parse-time validator cannot look, so the validator reports `Event target '<name>' is used but is never set` once per launch. The market-panel trade charts' `base_market` (`gui/market_panel.gui`, read in `common/script_values/gui_chart_script_values.txt`) was the first; the Strategic Reserve's `sr_rival` and the budget panel's rows (`gui/te_budget_generated_charts.gui`, read in `common/script_values/te_budget_generated_values.txt`, about 420 names) followed. They all work in game. The signature above is only the first name. The rest are tagged by `tag_gui_injected_scopes` in `game_log_reader.py`, which collects every `AddScope('<name>'` in the mod's `gui/` and English loc and tags exactly those names, so a never-set name that nothing sets still surfaces. Tracked at `docs/audits/open_issues.md#l14-gui-injected-event-targets-flagged-never-set`.

### `power_bloc_principle.cpp:139` — vanilla principles orphaned by REPLACE:principle_group
- source: `power_bloc_principle.cpp:139`
- tracked: `docs/audits/open_issues.md#l15-vanilla-principles-orphaned-by-replaceprinciple_group-overrides`

```
Principle principle_sacred_civics_
```

`REPLACE:principle_group_sacred_civics` swaps the vanilla group's members for the mod's `principle_sacred_civics_N_mod` variants; the vanilla `principle_sacred_civics_N` entries stay in the database groupless and log once each per launch. Group-less principles are unpickable → harmless. Tracked at `docs/audits/open_issues.md#l15-vanilla-principles-orphaned-by-replaceprinciple_group-overrides`.

### `country_law_manager.cpp:464` — deliberate historical law seeds lacking unlock tech (1.13.9 validation)
- source: `country_law_manager.cpp:464`
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
retain law Intrusive Surveillance System
retain law Total War
retain law State Secrets
retain law Penal Labor Camps
retain law Constitutional Review
```

Vanilla 1.13.9 added load-time validation of active laws against `unlocking_technologies`. Two by-design mod cases (details at `docs/audits/open_issues.md#l16-historical-law-seeding-vs-unlocking_technologies-retention-warnings-1139`): deliberate historical seeds in `common/history/extra_history.txt` (Gold Standard, Kriegsministerium, the USA's Constitutional Review, …), and init-order transients for the four lawgroups whose menu-ordered first law is tech-gated (Intrusive Surveillance / Total War / State Secrets / Penal Labor Camps, first in `lawgroup_criminal_justice` since #520; 146 countries at the 2026-10-10 start) — the engine assigns first-in-group before `extra_history.txt` GLOBAL replaces them with the tech-free baselines, so final state is correct. Signatures enumerate these known laws ONLY, so a new law name appearing in this warning class still surfaces in triage. Tracked at `docs/audits/open_issues.md#l16-historical-law-seeding-vs-unlocking_technologies-retention-warnings-1139`.

### `jomini_eventmanager.cpp:376` — console-only debug test events reported orphaned
- source: `jomini_eventmanager.cpp:376`
- tracked: `docs/audits/open_issues.md#l23-console-only-debug-test-events-logged-as-orphaned-by-design`

```
Event te_debug_
Event te_tax_debug.
```

The `te_debug_<system>.1` test consoles in `events/te_debug_*_events.txt` are fired by hand with `event te_debug_<x>.1`. Nothing in script fires them, so each is logged as orphaned at load (ch, colonial_empire, covert, gw, nuclear, space_race, un as of 2026-09-19). The tax code's console (`te_tax_debug.1`–`.8`, `events/te_tax_debug_events.txt`) takes the other word order, so it has a signature of its own. By design. The signature is the `te_debug_` prefix only, not `is orphaned`, because signatures match if ANY line matches: an `is orphaned` line would also hide a real mod event that lost its trigger. A new console needs no change here. Tracked at `docs/audits/open_issues.md#l23-console-only-debug-test-events-logged-as-orphaned-by-design`.

### `jomini_effect.cpp:1139` — old-save migration cleanup reads variables nothing sets
- source: `jomini_effect.cpp:1139`
- tracked: `docs/audits/open_issues.md#l24-old-save-migration-cleanup-reads-variables-nothing-sets`

```
Variable 'sr_notify_achiever_capital' is used but is never set
Variable 'sr_notify_is_first' is used but is never set
Variable 'sr_notify_suborbital' is used but is never set
Variable 'sr_notify_orbital' is used but is never set
Variable 'sr_notify_moon_landing' is used but is never set
Variable 'sr_notify_probe' is used but is never set
Variable 'sr_notify_moon_base' is used but is never set
Variable 'sr_notify_mars_landing' is used but is never set
Variable 'sr_notify_interstellar_probe' is used but is never set
Variable 'nd_stance_warfighting' is used but is never set
Variable 'nd_stance_professional' is used but is never set
Variable 'nd_stance_dove' is used but is never set
Variable 'nd_stance_business' is used but is never set
Variable 'un_founding_window_active' is used but is never set
Variable 'sr_active_milestone' is used but is never set
Variable 'tp_1_imp_rel' is used but is never set
Variable 'tp_1_exp_rel' is used but is never set
Variable 'tp_2_imp_rel' is used but is never set
Variable 'tp_2_exp_rel' is used but is never set
Variable 'tp_3_imp_rel' is used but is never set
Variable 'tp_3_exp_rel' is used but is never set
Variable 'tp_4_imp_rel' is used but is never set
Variable 'tp_4_exp_rel' is used but is never set
Variable 'tp_5_imp_rel' is used but is never set
Variable 'tp_5_exp_rel' is used but is never set
Variable 'tp_1_tc' is used but is never set
Variable 'tp_1_total' is used but is never set
Variable 'tp_1_gdp_pct' is used but is never set
Variable 'tp_2_tc' is used but is never set
Variable 'tp_2_total' is used but is never set
Variable 'tp_2_gdp_pct' is used but is never set
Variable 'tp_3_tc' is used but is never set
Variable 'tp_3_total' is used but is never set
Variable 'tp_3_gdp_pct' is used but is never set
Variable 'tp_4_tc' is used but is never set
Variable 'tp_4_total' is used but is never set
Variable 'tp_4_gdp_pct' is used but is never set
Variable 'tp_5_tc' is used but is never set
Variable 'tp_5_total' is used but is never set
Variable 'tp_5_gdp_pct' is used but is never set
Variable 'sr_fleet_upkeep_per_building' is used but is never set
Variable 'tp_count' is used but is never set
Variable 'gw_emitter_1' is used but is never set
Variable 'gw_emitter_2' is used but is never set
Variable 'gw_emitter_3' is used but is never set
Variable 'gw_emitter_4' is used but is never set
Variable 'gw_emitter_5' is used but is never set
Variable 'gw_emitters_shown' is used but is never set
Variable 'gw_emitters_own_slot' is used but is never set
Variable 'te_dg_n_lo' is used but is never set
Variable 'te_dg_n_mi' is used but is never set
Variable 'te_dg_n_up' is used but is never set
Variable 'te_dg_y_lo' is used but is never set
Variable 'te_dg_y_mi' is used but is never set
Variable 'te_dg_y_up' is used but is never set
Variable 'gm_com_extended' is used but is never set
Variable 'gm_com_gap_half' is used but is never set
Variable 'gm_promise_ledger' is used but is never set
Variable 'gm_com_cooldown' is used but is never set
Variable 'te_dg_m1840' is used but is never set
Variable 'te_dg_f1840' is used but is never set
Variable 'gm_tr_return_queued' is used but is never set
Variable 'gm_tr_return_relations' is used but is never set
Variable 'te_dg_dc_ontop' is used but is never set
Variable 'sr_rival_interstellar_probe_1' is used but is never set
Variable 'sr_rival_interstellar_probe_2' is used but is never set
Variable 'sr_rival_interstellar_probe_3' is used but is never set
Variable 'sr_rival_interstellar_probe_4' is used but is never set
Variable 'sr_rival_interstellar_probe_5' is used but is never set
Variable 'sr_rival_mars_landing_1' is used but is never set
Variable 'sr_rival_mars_landing_2' is used but is never set
Variable 'sr_rival_mars_landing_3' is used but is never set
Variable 'sr_rival_mars_landing_4' is used but is never set
Variable 'sr_rival_mars_landing_5' is used but is never set
Variable 'sr_rival_moon_base_1' is used but is never set
Variable 'sr_rival_moon_base_2' is used but is never set
Variable 'sr_rival_moon_base_3' is used but is never set
Variable 'sr_rival_moon_base_4' is used but is never set
Variable 'sr_rival_moon_base_5' is used but is never set
Variable 'sr_rival_moon_landing_1' is used but is never set
Variable 'sr_rival_moon_landing_2' is used but is never set
Variable 'sr_rival_moon_landing_3' is used but is never set
Variable 'sr_rival_moon_landing_4' is used but is never set
Variable 'sr_rival_moon_landing_5' is used but is never set
Variable 'sr_rival_orbital_1' is used but is never set
Variable 'sr_rival_orbital_2' is used but is never set
Variable 'sr_rival_orbital_3' is used but is never set
Variable 'sr_rival_orbital_4' is used but is never set
Variable 'sr_rival_orbital_5' is used but is never set
Variable 'sr_rival_probe_1' is used but is never set
Variable 'sr_rival_probe_2' is used but is never set
Variable 'sr_rival_probe_3' is used but is never set
Variable 'sr_rival_probe_4' is used but is never set
Variable 'sr_rival_probe_5' is used but is never set
Variable 'sr_rival_solar_colonization_1' is used but is never set
Variable 'sr_rival_solar_colonization_2' is used but is never set
Variable 'sr_rival_solar_colonization_3' is used but is never set
Variable 'sr_rival_solar_colonization_4' is used but is never set
Variable 'sr_rival_solar_colonization_5' is used but is never set
Variable 'sr_rival_suborbital_1' is used but is never set
Variable 'sr_rival_suborbital_2' is used but is never set
Variable 'sr_rival_suborbital_3' is used but is never set
Variable 'sr_rival_suborbital_4' is used but is never set
Variable 'sr_rival_suborbital_5' is used but is never set
Variable 'sr_rival_total_interstellar_probe' is used but is never set
Variable 'sr_rival_total_mars_landing' is used but is never set
Variable 'sr_rival_total_moon_base' is used but is never set
Variable 'sr_rival_total_moon_landing' is used but is never set
Variable 'sr_rival_total_orbital' is used but is never set
Variable 'sr_rival_total_probe' is used but is never set
Variable 'sr_rival_total_solar_colonization' is used but is never set
Variable 'sr_rival_total_suborbital' is used but is never set
Variable 'sr_power_1' is used but is never set
Variable 'sr_power_2' is used but is never set
Variable 'sr_power_3' is used but is never set
Variable 'sr_power_4' is used but is never set
Variable 'sr_power_5' is used but is never set
Variable 'sr_power_6' is used but is never set
Variable 'sr_power_7' is used but is never set
Variable 'sr_power_8' is used but is never set
Variable 'te_seabed_rank_arctic' is used but is never set
Variable 'te_seabed_rank_atlantic' is used but is never set
Variable 'te_seabed_rank_indian' is used but is never set
Variable 'te_seabed_rank_pacific' is used but is never set
Variable 'te_seabed_rank_southern' is used but is never set
Variable 'te_seabed_rk_arctic_1' is used but is never set
Variable 'te_seabed_rk_arctic_2' is used but is never set
Variable 'te_seabed_rk_arctic_3' is used but is never set
Variable 'te_seabed_rk_arctic_4' is used but is never set
Variable 'te_seabed_rk_arctic_5' is used but is never set
Variable 'te_seabed_rk_arctic_6' is used but is never set
Variable 'te_seabed_rk_atlantic_1' is used but is never set
Variable 'te_seabed_rk_atlantic_2' is used but is never set
Variable 'te_seabed_rk_atlantic_3' is used but is never set
Variable 'te_seabed_rk_atlantic_4' is used but is never set
Variable 'te_seabed_rk_atlantic_5' is used but is never set
Variable 'te_seabed_rk_atlantic_6' is used but is never set
Variable 'te_seabed_rk_indian_1' is used but is never set
Variable 'te_seabed_rk_indian_2' is used but is never set
Variable 'te_seabed_rk_indian_3' is used but is never set
Variable 'te_seabed_rk_indian_4' is used but is never set
Variable 'te_seabed_rk_indian_5' is used but is never set
Variable 'te_seabed_rk_indian_6' is used but is never set
Variable 'te_seabed_rk_more_arctic' is used but is never set
Variable 'te_seabed_rk_more_atlantic' is used but is never set
Variable 'te_seabed_rk_more_indian' is used but is never set
Variable 'te_seabed_rk_more_pacific' is used but is never set
Variable 'te_seabed_rk_more_southern' is used but is never set
Variable 'te_seabed_rk_pacific_1' is used but is never set
Variable 'te_seabed_rk_pacific_2' is used but is never set
Variable 'te_seabed_rk_pacific_3' is used but is never set
Variable 'te_seabed_rk_pacific_4' is used but is never set
Variable 'te_seabed_rk_pacific_5' is used but is never set
Variable 'te_seabed_rk_pacific_6' is used but is never set
Variable 'te_seabed_rk_southern_1' is used but is never set
Variable 'te_seabed_rk_southern_2' is used but is never set
Variable 'te_seabed_rk_southern_3' is used but is never set
Variable 'te_seabed_rk_southern_4' is used but is never set
Variable 'te_seabed_rk_southern_5' is used but is never set
Variable 'te_seabed_rk_southern_6' is used but is never set
Variable 'te_seabed_rkcap_arctic_1' is used but is never set
Variable 'te_seabed_rkcap_arctic_2' is used but is never set
Variable 'te_seabed_rkcap_arctic_3' is used but is never set
Variable 'te_seabed_rkcap_arctic_4' is used but is never set
Variable 'te_seabed_rkcap_arctic_5' is used but is never set
Variable 'te_seabed_rkcap_arctic_6' is used but is never set
Variable 'te_seabed_rkcap_atlantic_1' is used but is never set
Variable 'te_seabed_rkcap_atlantic_2' is used but is never set
Variable 'te_seabed_rkcap_atlantic_3' is used but is never set
Variable 'te_seabed_rkcap_atlantic_4' is used but is never set
Variable 'te_seabed_rkcap_atlantic_5' is used but is never set
Variable 'te_seabed_rkcap_atlantic_6' is used but is never set
Variable 'te_seabed_rkcap_count_arctic' is used but is never set
Variable 'te_seabed_rkcap_count_atlantic' is used but is never set
Variable 'te_seabed_rkcap_count_indian' is used but is never set
Variable 'te_seabed_rkcap_count_pacific' is used but is never set
Variable 'te_seabed_rkcap_count_southern' is used but is never set
Variable 'te_seabed_rkcap_indian_1' is used but is never set
Variable 'te_seabed_rkcap_indian_2' is used but is never set
Variable 'te_seabed_rkcap_indian_3' is used but is never set
Variable 'te_seabed_rkcap_indian_4' is used but is never set
Variable 'te_seabed_rkcap_indian_5' is used but is never set
Variable 'te_seabed_rkcap_indian_6' is used but is never set
Variable 'te_seabed_rkcap_pacific_1' is used but is never set
Variable 'te_seabed_rkcap_pacific_2' is used but is never set
Variable 'te_seabed_rkcap_pacific_3' is used but is never set
Variable 'te_seabed_rkcap_pacific_4' is used but is never set
Variable 'te_seabed_rkcap_pacific_5' is used but is never set
Variable 'te_seabed_rkcap_pacific_6' is used but is never set
Variable 'te_seabed_rkcap_southern_1' is used but is never set
Variable 'te_seabed_rkcap_southern_2' is used but is never set
Variable 'te_seabed_rkcap_southern_3' is used but is never set
Variable 'te_seabed_rkcap_southern_4' is used but is never set
Variable 'te_seabed_rkcap_southern_5' is used but is never set
Variable 'te_seabed_rkcap_southern_6' is used but is never set
Variable 'sr_moon_base_industrial' is used but is never set
Variable 'sr_moon_base_military' is used but is never set
Variable 'sr_failure_cooldown' is used but is never set
Flag 'mothballed' is used but is never set
Flag 'standard' is used but is never set
```

`sr_clear_legacy_milestone_notice` and `sr_cleanup_inactive_space_race_milestones` (`space_race_effects.txt`), `nd_refresh_domestic_stance` (`nuclear_deterrence_effects.txt`), the UN dissolution sweep (`un_ladder_effects.txt`) and the trading-partners refresh (`trade_partner_effects.txt`, the Imp%/Exp% columns' old `tp_<n>_imp_rel` / `tp_<n>_exp_rel`) and the demographics Gini store (`te_demog_gini_band_store` in `te_demog_generated_effects.txt`, written by gen_demographics.py: the six strata sums `te_dg_<n|y>_<lo|mi|up>` from before the wealth bands, #854), the Grand Monument opportunity's record (`gm_com_clear` and the first-sight sweep in `gm_commission_effects.txt`: v2's `gm_com_extended` and `gm_com_gap_half`, and `gm_promise_ledger` and `gm_com_cooldown`, retired by #915) and the demographics census (`te_demog_effects.txt`: the 18-40 sums `te_dg_m1840` / `te_dg_f1840`, which a census from before phase 2 step 4, #942, kept instead of the fighting-age pool), the trophy pass (`gm_trophy_effects.txt`: the queued returns `gm_tr_return_queued` / `gm_tr_return_relations`, which #1058 stopped setting), the census's cause-of-death store (`te_demog_cause_deaths_old_clear` in `te_demog_effects.txt`: the deaths-on-top slice `te_dg_dc_ontop`, retired by #1099) and the monument policy (`gm_policy_migrate` and `gm_policy_is` in `gm_policy_effects.txt` / `gm_policy_triggers.txt`: the Mothballed and Standard policies' `flag:mothballed` and `flag:standard`, retired by #1121) remove variables an older save may still hold and nothing sets any more; the census also reads the old sums once, for the war dead's window, and the policy reads the two old flags as the default. #1215's list rewrites (audits SPC-9 and SEA-3, 2026-10-27) added two more: the Space Race's Rivals and Space Powers snapshots (sr_clear_rival_slots and sr_powers_clear in space_race_effects.txt: the slots `sr_rival_<milestone>_<1-5>`, the counts `sr_rival_total_<milestone>` and the eight `sr_power_<n>`) and the seabed claimants' ranking (te_seabed_rank_clear, te_seabed_rank_list and te_seabed_rank_seat_clear in te_global_commons_seabed_effects.txt: the global seats `te_seabed_rk_<basin>_<1-6>` and `te_seabed_rk_more_<basin>`, each country's `te_seabed_rank_<basin>`, and the players' `te_seabed_rkcap_<basin>_<1-6>` and `te_seabed_rkcap_count_<basin>`), 131 names in all, registered 2026-10-29. The retired Moon Base (#1238) added two on 2026-10-30 (#1243): its purpose choices `sr_moon_base_industrial` and `sr_moon_base_military`, which the old-save migration (`sr_lunar_migrate_country` in sr_sites_generated.txt, written by gen_solar_sites.py) reads to give a country that finished the Moon Base the lunar site its purpose names, as do the retired entry's panel, purpose trigger and modifier sync for a copy that lingers in an old save. The third purpose, `sr_moon_base_scientific`, is not logged, because the Space Race's debug console sets it. The retired post-setback cooldown (#1274, 2026-10-31) added one: `sr_failure_cooldown`, which the Space Race's monthly pulse (`space_race_on_action` in `space_race_on_actions.txt`) removes from an older save, until the strip goes after 2026-12-31. The validator reports each read once per launch. The signatures name all 197 variables and both flags, so a new never-set variable or flag is not hidden. Tracked at `docs/audits/open_issues.md#l24-old-save-migration-cleanup-reads-variables-nothing-sets`.

### `jomini_eventmanager.cpp:376` — `un_vote.5` kept for events queued in older saves
- source: `jomini_eventmanager.cpp:376`
- tracked: `docs/audits/open_issues.md#l25-un_vote5-kept-for-events-queued-in-older-saves`

```
Event un_vote.5 is orphaned
```

`un_vote.5` (`events/un_vote_events.txt`) used to dispatch the AI ballots. Since the late ballots (#531) nothing queues it, but an older save can still hold one queued, so the event stays and now only refreshes the leans. The engine logs it as orphaned at load, once per launch. The signature names this one event, so a real mod event that loses its trigger still shows up. Tracked at `docs/audits/open_issues.md#l25-un_vote5-kept-for-events-queued-in-older-saves`.

### `event.cpp:358` — Grand Monuments v2 load-time notices
- source: `event.cpp:358`
- source: `jomini_effect.cpp:1139`
- tracked: `docs/audits/open_issues.md#l26-grand-monuments-v2-load-time-notices`

```
No default option in event monument_events.11.
Flag 'leader' is used but is never set
Flag 'memorial' is used but is never set
```

Three lines once per launch. The skin choice has no `default_option` by design, `flag:leader` is set as `flag:$DEDICATION$`, which the validator cannot see, and `flag:memorial` is read only to name a Memorial-form monument or commission from a save older than #909, which retired that form. Each signature names its own event or flag, so another event without a default or another never-set flag still shows up.

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
- tracked: `docs/audits/open_issues.md#l28-zero-construction-speed-with-a-queued-project-unattributed`

```
The total construction speed is zero
```

The engine's estimate of a country's queue length divides by its construction speed, and logs this when that speed is zero. It names no country and no script, so the cause isn't known. 2026-10-24: 3,208 lines over three and a half hours of play, steady at 20 to 40 a minute from about half an hour after the launch, a third of every `error.log`; the 2026-10-11 observer runs logged it at `:9594` ("queues"), so it predates that day's builds. Tracked at `docs/audits/open_issues.md#l28-zero-construction-speed-with-a-queued-project-unattributed`.

### `common/decrees/extra_decrees.txt` — the engine checks a decree's country_trigger with no country
- tracked: `docs/audits/open_issues.md#l29-a-decrees-country_trigger-checked-with-no-country`

```
untyped trigger [ Scoped object of type 'country' is not valid (Country  (4294967295))
```

The engine re-checks each decree's `country_trigger` weekly (vanilla's decree file header: it "should invalidate the Decree on a weekly basis if found invalid"), and now and then it does so with the null country. Vanilla's own decrees log the same message in the same second, and the `<unknown>:0` untyped-trigger entry in the vanilla registry tags those; its `- stack: vanilla only` leaves this file's lines visible. Medical Outreach's trigger logged once on 2026-10-25. Script can't guard a root that is invalid before the block runs. Tracked at `docs/audits/open_issues.md#l29-a-decrees-country_trigger-checked-with-no-country`.
