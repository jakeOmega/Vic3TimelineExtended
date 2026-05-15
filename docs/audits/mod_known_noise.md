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

Same as `vanilla_known_bugs.md` — `### \`anchor\` — title` heading, optional `- source: \`<token>\``, mandatory `- tracked: \`docs/audits/open_issues.md#anchor\``, fenced code block of signature substrings.

## Entries

### `harvest_condition_graphics.cpp:52` — missing sound-entity states for mod market harvest conditions
- source: `harvest_condition_graphics.cpp:52`
- tracked: `docs/audits/open_issues.md#l7-mod-harvest-condition-sound-entity-states-missing`

```
Couldn't find any animation state for harvest condition type
```

Mod adds `bull_market` / `bear_market` / `market_downturn` / `financial_panic` as harvest condition types in `common/harvest_condition_types/extra_harvest_condition_types.txt` for banking-cycle visualization. Vanilla `harvest_condition_sound_entity` has no matching states. Functional impact: silent — engine just doesn't play a sound. Fix recipe in `docs/audits/open_issues.md#L7`.

### `pdx_gui_factory.cpp:628` — `gui/tooltip.gui:231 - Could not find template 'vertical_scrollbar'`
- source: `pdx_gui_factory.cpp:628`
- tracked: `docs/audits/open_issues.md#l8-mod-tooltip-gui-vertical-scrollbar-template-warning`

```
Could not find template 'vertical_scrollbar'
```

Mod's scrollable `FancyTooltipWidgetType` uses `scrollbar_vertical = { using = vertical_scrollbar }` — the same exact pattern vanilla uses successfully (vanilla `block_windows` and `building_browser_panel` files do the same and don't error). Likely parse-time false-positive resolved in pass-2; scrollable tooltip rendering works in-game. Tracked at `docs/audits/open_issues.md#L8` until a way to silence it surfaces.

### `gfx_dds_loader.cpp:442` — historical-company icon DDS dimensions not multiple of 4
- source: `gfx_dds_loader.cpp:442`
- tracked: `docs/audits/open_issues.md#l9-mod-dds-dimensions-historical-company-icons`

```
gfx/interface/icons/company_icons/historical_company_icons/japanese_toyota.dds
gfx/interface/icons/company_icons/historical_company_icons/korean_samsung.dds
gfx/interface/icons/company_icons/historical_company_icons/american_google.dds
gfx/interface/icons/company_icons/historical_company_icons/russian_rosatom.dds
```

Block-compressed (BC1/BC3) DDS textures need multiple-of-4 width and height; these four mod-side historical-company icons fail that constraint and emit edge-artifact warnings once per file at load. Visual-only — engine still loads the texture. Fix requires re-export through the image pipeline; tracked at `docs/audits/open_issues.md#L9`.

### `jomini_effect.cpp:1135` — variables set for localization tooltip read flagged unused
- source: `jomini_effect.cpp:1135`
- tracked: `docs/audits/open_issues.md#l10-mod-loc-only-variables-flagged-unused`

```
is set but is never used. Note that use in localization doesn't count
```

Mod uses `set_global_variable` to expose values (cultural-hegemony per-rank breakdowns, nuclear stockpile per-rank) to tooltip text via `GetGlobalVariable('…')` in `localization/english/te_concepts_l_english.yml`. The engine explicitly notes loc reads don't count as uses, so each variable emits an "unused" warning at load. By-design; rearchitecting all loc tooltips to use script values instead would be a large refactor with no functional gain. Tracked at `docs/audits/open_issues.md#L10`.
