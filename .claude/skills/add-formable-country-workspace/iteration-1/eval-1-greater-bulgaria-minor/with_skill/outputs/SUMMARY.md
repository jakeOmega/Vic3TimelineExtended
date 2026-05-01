# Greater Bulgaria — implementation summary

## Decisions

- **Tag**: `GBL`. Rejected `BUL` because vanilla owns it (`game/common/country_definitions/00_countries.txt:BUL`, `tier = kingdom`, `cultures = { bulgarian }`, `capital = STATE_BULGARIA`). `GBL` is unused in both vanilla `country_definitions/` and the mod's `common/country_definitions/te_formable_countries.txt` (verified by grep).
- **Tier**: `kingdom` (per spec).
- **Primary culture**: `bulgarian`. Verified in vanilla `game/common/cultures/00_cultures.txt`.
- **Formation type**: minor (per spec) — no diplomatic plays, no candidacy.
- **Tech gate**: `nationalism` (vanilla, era-4) — used in both `ai_will_do` and `possible`. Matches vanilla `ITA`/`GER` `ai_will_do` style.
- **Required states fraction**: `1.0` (100%, per spec — San Stefano-line claim).
- **Color**: `0 145 80` (green, in Bulgarian flag tradition; spaced away from AFU `0 130 70`).

## Verified vanilla references

- Culture `bulgarian = {` exists in `game/common/cultures/00_cultures.txt`.
- `STATE_BULGARIA` at `game/map_data/state_regions/01_south_europe.txt:820` (mod mirror at line 830). Contains Sofia / Danube traits.
- `STATE_MACEDONIA` at `game/map_data/state_regions/01_south_europe.txt:1113`.
- `STATE_EASTERN_THRACE` at `game/map_data/state_regions/01_south_europe.txt:721`.
- Formation template: vanilla `IDN` in `game/common/country_formation/00_formable_countries.txt` (explicit state list + `required_states_fraction` + simple `possible`).
- Dynamic-name template: vanilla `USA` at `game/common/dynamic_country_names/00_dynamic_country_names.txt:2785` (default-republic guard with `NOT = { coa_def_communist_flag_trigger = yes }` and `NOT = { coa_def_technocracy_flag_trigger = yes }`).
- Government triggers from `game/common/scripted_triggers/00_coa_triggers.txt`.

## Deviations from spec

1. **`STATE_NORTHERN_BULGARIA` and `STATE_SOUTHERN_BULGARIA` do not exist** in vanilla or the mod. Vanilla uses a single unified `STATE_BULGARIA` for the Bulgarian heartland. Verified by grep against both vanilla and mod `map_data/state_regions/`. Substituted `STATE_BULGARIA`. Required states are therefore `{ STATE_BULGARIA, STATE_MACEDONIA, STATE_EASTERN_THRACE }` (3, not 4). Consistent with CLAUDE.md's "State name pitfalls" guidance.
2. **Capital**: spec said "Sofia → STATE_NORTHERN_BULGARIA". Since that state doesn't exist, capital is `STATE_BULGARIA` (the vanilla state containing Sofia).

## Files produced

- `outputs/common/country_definitions/te_formable_countries.delta.txt` — `GBL` tag block (BOM, tab-indented).
- `outputs/common/country_formation/te_formable_countries.delta.txt` — minor-formation rule for `GBL` (BOM, tab-indented).
- `outputs/common/dynamic_country_names/te_formable_countries.delta.txt` — four `dynamic_country_name` blocks: republic default, communist, fascist, monarchy (BOM, tab-indented).
- `outputs/localization/english/te_formable_countries_l_english.delta.yml` — six loc keys (tag + adjective + four dynamic-name keys; one-space-indented; BOM; no `l_english:` header).
- `outputs/organize_loc_diff.txt` — snippet adding `"GBL"` and `"GBL_ADJ"` to `organize_loc.py`'s FORMABLE_COUNTRIES rule.
