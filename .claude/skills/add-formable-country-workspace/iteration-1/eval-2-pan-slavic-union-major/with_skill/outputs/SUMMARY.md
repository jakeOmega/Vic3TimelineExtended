# Pan-Slavic Union (PSU) — Major Formable

## Decisions

- **Tag**: `PSU` — verified unused via `grep -rE "^PSU = "` against vanilla `country_definitions/` and the mod (no results).
- **Tier**: `hegemony` (matches the mod's other continental majors AFU/EUN/UNA).
- **Capital**: `STATE_MOSCOW` — verified at vanilla `map_data/state_regions/15_russia.txt:285`.
- **Cultures**: all 10 Slavic cultures, each verified in vanilla `common/cultures/00_cultures.txt`:
  - East Slavic: russian, ukrainian, byelorussian (vanilla form, not "belarusian").
  - West Slavic: polish, czech, slovak.
  - South Slavic: serb, croat, slovene, bulgarian.
- **Tech gate**: `decolonization` (era_6 mod tech, era_6.txt:785) + `pan-nationalism` (vanilla 30_society.txt:1180) — stacked, matching the mod's AFU/EUN pattern.
- **Major-formation block**: `is_major_formation = yes`, `unification_play = dp_unify_pan_slavic_union`, `leadership_play = dp_leadership_pan_slavic_union`, `max_num_formation_candidates = 3`, `can_be_formation_candidate = { country_rank >= rank_value:major_power }`.

## Geographic-region choice

Defined a custom `geographic_region_pan_slavic` rather than using vanilla `geographic_region_europe`.

- **Trade-off**: more files to ship; the region can drift from vanilla map renames in successor patches.
- **Why custom won**: vanilla `geographic_region_europe` includes the British Isles, Iberia, France, Germany, Italy, and Scandinavia — none of which are Slavic. With `required_states_fraction = 0.5`, the candidate would have to control half of those, which is thematically wrong. The mod's existing `geographic_region_intermarium` makes the same trade-off for the same reason.
- The custom region covers 60 states: Russian core, Belarus, Ukraine, Polish core, Czech/Slovak (Bohemia, Moravia, Slovakia, Ruthenia), Yugoslav core (Slovenia–Macedonia), Bulgaria.

## States verified

All states named in `geographic_region_pan_slavic` come from listing the vanilla state-region files: `map_data/state_regions/02_east_europe.txt`, `01_south_europe.txt`, `15_russia.txt`. Bulgaria-relevant states (`STATE_BULGARIA`, `STATE_NORTHERN_THRACE`) verified at `01_south_europe.txt:801,820`.

## Dynamic names — design

Seven entries grounded in real history / political tradition:

| Government | Name | Trigger | Priority |
|---|---|---|---|
| Republic (default) | Pan-Slavic Federation | republic AND NOT communist AND NOT technocracy | 0 |
| Communist | Union of Soviet Socialist Republics | communist | 0 |
| Fascist | Slavic Imperium | fascist | 0 |
| Russian-led monarchy (2nd axis) | Empire of All the Russias | monarchy AND (was_formed_from = RUS OR ruler.has_culture = cu:russian) | **5** |
| Generic monarchy | Slavic Empire | monarchy | 0 |
| Theocracy + Orthodox state religion | Orthodox Slavic Patriarchate | theocracy AND state_religion = rel:orthodox | **5** |
| Technocracy | Pan-Slavic Technate | technocracy | 0 |

Notes:
- "Empire of All the Russias" is the historical Romanov imperial title (Imperator Vserossiyskiy); fits the Russian-led axis.
- "Slavic Imperium" mirrors the mod's existing AFU/EUN/UNA fascist naming convention (`*_imperium`).
- "Orthodox Slavic Patriarchate" is gated extra-narrow on state religion so it correctly fires only for an Orthodox theocracy.

## Vanilla examples cited

- `game/common/country_formation/00_major_formables.txt` — Germany block (canonical major-formation; quoted in `references/vanilla_examples.md` lines 11-56).
- `game/common/diplomatic_plays/00_diplomatic_plays.txt:839+` — `dp_unify_germany` / `dp_leadership_germany` (template for the dp pair).
- `game/common/dynamic_country_names/00_dynamic_country_names.txt:2785` — USA dynamic-name block (default-republic + multi-government with NOT-communist / NOT-technocracy guard).
- `game/common/cultures/00_cultures.txt` — all 10 culture verifications.
- `game/map_data/state_regions/15_russia.txt:285` — STATE_MOSCOW.

## Files produced

- `outputs/common/country_definitions/te_formable_countries.delta.txt`
- `outputs/common/country_formation/te_formable_countries.delta.txt`
- `outputs/common/dynamic_country_names/te_formable_countries.delta.txt`
- `outputs/common/diplomatic_plays/te_unification_plays.delta.txt`
- `outputs/common/geographic_regions/te_formable_regions.delta.txt`
- `outputs/localization/english/te_formable_countries_l_english.delta.yml`
- `outputs/organize_loc_diff.txt`
- `outputs/SUMMARY.md` (this file)
