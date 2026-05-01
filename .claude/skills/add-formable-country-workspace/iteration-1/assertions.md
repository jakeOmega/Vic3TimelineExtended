# Grading assertions for iteration-1

These check that the subagent produced complete, validated output. Each assertion is binary pass/fail.

## Eval 1 — Greater Bulgaria (minor formation)

| # | Assertion | How to verify |
|---|---|---|
| 1.1 | tag is unused in vanilla and mod | grep the chosen tag in `common/country_definitions/` |
| 1.2 | country_definitions delta defines tag with tier=kingdom, capital=STATE_NORTHERN_BULGARIA, cultures includes bulgarian | read the delta |
| 1.3 | bulgarian culture exists in vanilla `common/cultures/00_cultures.txt` | grep |
| 1.4 | All four required states (NORTHERN_BULGARIA, SOUTHERN_BULGARIA, MACEDONIA, EASTERN_THRACE) exist in vanilla map_data | grep |
| 1.5 | country_formation entry uses `states = { … }` (NOT `geographic_region`), `required_states_fraction = 1.0` (or 1), `possible` requires `nationalism` | read |
| 1.6 | country_formation has NO `is_major_formation`, `unification_play`, `leadership_play`, `max_num_formation_candidates`, `can_be_formation_candidate` (this is a minor formation) | read |
| 1.7 | dynamic_country_names provides 4 entries: republic default, monarchy, communist, fascist | read |
| 1.8 | each dynamic_country_name has `is_main_tag_only = yes` and a `coa_def_*_flag_trigger` | read |
| 1.9 | republic default trigger excludes communist with `NOT = { coa_def_communist_flag_trigger = yes }` | read |
| 1.10 | localization file has TAG, TAG_ADJ, and one key per dyn_c_X name and adjective referenced | grep + cross-check |
| 1.11 | organize_loc_diff snippet adds the new tag and `_ADJ` to the FORMABLE_COUNTRIES key set | read |
| 1.12 | brace-based files start with UTF-8 BOM (or a line comment that effectively serves as one) | hexdump -C first byte |

## Eval 2 — Pan-Slavic Union (major formation)

| # | Assertion | How to verify |
|---|---|---|
| 2.1 | tag PSU is unused in vanilla and mod | grep |
| 2.2 | country_definitions defines PSU with tier=hegemony, capital=STATE_MOSCOW, cultures = all 10 Slavic | read |
| 2.3 | each of the 10 cultures exists in vanilla `common/cultures/00_cultures.txt` (note: byelorussian — vanilla uses this not "belarusian") | grep |
| 2.4 | country_formation has `is_major_formation = yes`, `unification_play = dp_unify_pan_slavic_union`, `leadership_play = dp_leadership_pan_slavic_union`, `max_num_formation_candidates = 3`, `can_be_formation_candidate` requiring rank ≥ major_power | read |
| 2.5 | country_formation `possible` requires both `pan-nationalism` and `decolonization` | read |
| 2.6 | dp_unify_pan_slavic_union exists with `war_goal = unification`, vanilla unification.dds icon, `possible` requires decolonization | read |
| 2.7 | dp_leadership_pan_slavic_union exists with `war_goal = unification_leadership`, `mirror_war_goal = yes` | read |
| 2.8 | dynamic_country_names has all 7 expected variants: default republic, communist, fascist, generic monarchy, Russian-led monarchy (priority 5+), theocracy with orthodox state-religion gate, technocracy | read |
| 2.9 | Russian-led monarchy entry uses `was_formed_from = RUS` OR `ruler ?= { has_culture = cu:russian }` and priority 5+ | read |
| 2.10 | each dynamic name has `is_main_tag_only = yes` | read |
| 2.11 | republic default trigger excludes communist + technocracy | read |
| 2.12 | localization has all dp_*, dyn_c_*, PSU, PSU_ADJ keys | grep + cross-check |
| 2.13 | dp_*_tooltip and dp_*_desc keys ALSO present (vanilla convention) | grep |
| 2.14 | organize_loc_diff adds PSU and PSU_ADJ to the registered tag set | read |
| 2.15 | brace-based files have UTF-8 BOM | hexdump |

## Cross-eval

| # | Assertion | How to verify |
|---|---|---|
| X.1 | SUMMARY.md exists and explains key decisions | read |
| X.2 | Subagent cited at least one vanilla file:line reference per file produced | read SUMMARY |
| X.3 | No scope creep — output is just what was asked, no extra files / extra cultures / extra dynamic names | read |
