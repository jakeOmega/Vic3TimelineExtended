---
name: add-formable-country
description: Add one or more new formable countries to the Vic3TimelineExtended mod, with optional government-flavored dynamic names. Use whenever the user mentions adding a "formable", "unification", "nation formation", "pan-X union", "Greater Y", or wants a new tag that other countries can form into (Pan-African Union, Intermarium, Greater India, etc.) — even if they don't say the word "formable". Also triggers when the user wants to convert an existing minor formable into a major one (candidacy + leadership/unification plays), or wants to add government-conditional dynamic names to a tag.
---

# Add a formable country

## When to use

The user wants the mod to support forming a new country tag — by states-control (minor formation) or candidacy + diplomatic plays (major formation, like vanilla Germany / Italy / Yugoslavia). They may also want each variant of the formed country to display a different name based on government type (republic / communist / fascist / monarchy / theocracy / technocracy), like how vanilla USA becomes "United Syndicates of America" under communism.

This skill is a workflow, not a script — every formable involves judgment calls (cultures, capital, geography, name flavor) that need user input or grounded research. Drive the workflow; don't try to one-shot a full file dump.

## Decisions to make first (ask the user, don't guess)

Before touching any files, lock these decisions for each country. Use `AskUserQuestion` with 1–4 questions if any are ambiguous.

1. **Tag** (3 letters). Verify it's unused: `grep -rE "^TAG = " "$(python3 -c 'from path_constants import base_game_path; print(base_game_path)')/game/common/country_definitions/" /home/jakef/src/Vic3TimelineExtended/common/country_definitions/`. Vanilla uses ISO-ish codes; pick something semantic (AFU = African Union, INM = Intermarium).
2. **Minor or major formation.** Major = competing candidates among same-culture great powers, leadership/unification diplomatic plays (rich gameplay, lots of files). Minor = whoever directly controls enough required states forms it (lightweight). Default to major when there are realistically multiple cultural candidates (continental / pan-X formables); minor when one country is the obvious unifier.
3. **Tier**: principality → kingdom → empire → hegemony. Match the scope.
4. **Primary cultures.** Verify each exists: `grep -E "^<culture>\s*=" "$(python3 -c 'from path_constants import base_game_path; print(base_game_path)')/game/common/cultures/00_cultures.txt"`. Watch for vanilla quirks: `british` (not `english`), `berber` (not `amazigh`), `panjabi` (not `punjabi`), `oriya` (not `oria`), `telegu` (not `telugu`), `byelorussian` (not `belarusian`).
5. **Capital state.** Pick the historical/cultural capital. Verify with `grep -nE "^STATE_X = \{" "$(python3 -c 'from path_constants import base_game_path; print(base_game_path)')/game/map_data/state_regions/"*.txt`.
6. **Geographic anchor**: a vanilla `geographic_region_*` (preferred), an explicit state list, or a new mod-side region. Vanilla regions to know: `geographic_region_europe`, `geographic_region_africa`, `geographic_region_subsaharan_africa`, `geographic_region_north_america`, `geographic_region_india`, `geographic_region_south_east_asia`, `geographic_region_yugoslavia`, `geographic_region_greater_germany`, `geographic_region_scandinavia`. Full list: `grep -hE "^geographic_region_[a-z_]+ = \{" "$(python3 -c 'from path_constants import base_game_path; print(base_game_path)')/game/common/geographic_regions/"01_*.txt 02_*.txt 03_*.txt 04_*.txt | sort -u`.
7. **Tech gate.** Era-6 mod tech `decolonization` (`era_6.txt:785`) for Cold-War / decolonization-era formables. Vanilla `pan-nationalism` / `nationalism` for earlier ones. Stack both for hegemony-tier modern formables.
8. **Dynamic-name flavor.** Per government type: republic default, communist, fascist, monarchy, theocracy, technocracy — and any 2nd-axis flavor (ruler culture, `was_formed_from = X`). The Intermarium "Promethean Empire" under fascism, AU "Solomonic African Empire" with Ethiopian-led monarchy, UNA "Empire of the Americas" with Mexican-led monarchy are good models. Keep names grounded in real history/political projects — never campy.

If any decision is genuinely flexible, present 2–3 options to the user; don't silently pick.

## File layout

All paths relative to `/home/jakef/src/Vic3TimelineExtended/`. The mod's existing convention is `te_*.txt` (sorts after vanilla `00_*.txt` so mod entries override on tag-key collision).

| File | Required for | What goes in |
|---|---|---|
| `common/country_definitions/te_formable_countries.txt` | new tags only | tag, color, country_type=recognized, tier, cultures, capital. **Skip for BHT/IDN/etc. that already exist in vanilla** — vanilla's definition stays. |
| `common/country_formation/te_formable_countries.txt` | every formable | formation rule per tag. To convert a vanilla minor formable to major: re-declare the tag here with `is_major_formation = yes` etc. — last-wins overrides vanilla. |
| `common/dynamic_country_names/te_formable_countries.txt` | if you want gov-flavored names | one block per tag, multiple `dynamic_country_name = { … }` entries inside. |
| `common/diplomatic_plays/te_unification_plays.txt` | major formations only | one `dp_unify_X` + one `dp_leadership_X` per major. Reuse vanilla `gfx/interface/icons/war_goals/unification.dds`. |
| `common/geographic_regions/te_formable_regions.txt` | only if no vanilla region fits | new `geographic_region_*` definitions. |
| `localization/english/te_formable_countries_l_english.yml` | every formable | tag display name + adjective + every `dyn_c_*` and `dp_*` key referenced. |

This file is rebuilt by `python organize_loc.py` (which auto-runs on every `POST /reload`). Make sure `organize_loc.py`'s `categorize_key` routes your new tag's loc keys to `FORMABLE_COUNTRIES` — the mod already routes `dyn_c_*`, `dp_unify_*`, `dp_leadership_*`, and the registered tag/adjective set `{AFU, INM, EAF, EUN, UNA, *_ADJ}`. Add new tags to that set when you introduce them, otherwise their `TAG:` and `TAG_ADJ:` keys land in MISCELLANEOUS or CONCEPTS.

## Country formation DSL (essentials)

```
TAG = {
    # exactly one of these:
    use_culture_states = yes        # = every state with a homeland of one of the tag's primary cultures
    states = { STATE_A STATE_B … }
    geographic_region = geographic_region_X

    is_major_formation = yes        # major formation only
    unification_play = dp_unify_X   # major formation only
    leadership_play = dp_leadership_X  # major formation only

    required_states_fraction = 0.5  # 0.0–1.0

    ai_will_do = { has_technology_researched = decolonization }

    possible = {
        has_technology_researched = decolonization
        # additional triggers
    }

    # major formation only:
    max_num_formation_candidates = 3
    can_be_formation_candidate = {
        country_rank >= rank_value:major_power   # or minor_power for low-GP regions
    }
}
```

Reference: `references/vanilla_examples.md` quotes the canonical Germany / Italy / Scandinavia / Andes major formations and a few minor ones (Poland, Arabia) verbatim.

## Dynamic-name DSL

```
TAG = {
    dynamic_country_name = {
        name = dyn_c_some_loc_key       # name shown in UI
        adjective = TAG_ADJ             # or dyn_c_some_adj_loc_key

        is_main_tag_only = yes          # default: no — almost always set yes here
        priority = 0                    # higher wins on multi-match; ties → first in file

        trigger = {                     # country scope
            coa_def_<X>_flag_trigger = yes
            # additional conditions
        }
    }
    # repeat for every government variant
}
```

Available government triggers (canonical, no-registration scripted triggers in vanilla `00_coa_triggers.txt`):
- `coa_def_republic_flag_trigger` — any republic (corporate state, presidential, parliamentary, council). Council-republic also matches communist.
- `coa_def_communist_flag_trigger` — `law_council_republic`.
- `coa_def_fascist_flag_trigger` — oligarchy/dictatorship/fascist-social-monarchy with fascist leader/ideology.
- `coa_def_monarchy_flag_trigger` — any monarchy law variant.
- `coa_def_absolute_monarchy_flag_trigger` / `coa_def_undemocratic_monarchy_flag_trigger` — narrower monarchy variants.
- `coa_def_theocracy_flag_trigger` — `law_theocracy`.
- `coa_def_technocracy_flag_trigger` — `law_technocracy`.
- `coa_def_dictatorship_flag_trigger`, `coa_def_anarchy_flag_trigger`, `coa_def_nihilist_flag_trigger`, `coa_def_corporate_state_flag_trigger`.

**Default-entry trick** (mirrors vanilla USA): the republic default needs `NOT = { coa_def_communist_flag_trigger = yes }` and `NOT = { coa_def_technocracy_flag_trigger = yes }` to avoid double-matching against more-specific entries. Even though council-republic/technocracy aren't strictly republic-OR'd, the explicit NOTs prevent ambiguous overlaps.

**2nd-axis flavor** (priority 5+): combine the gov trigger with `was_formed_from = TAG` (which country formed this; e.g. INM-from-Hungary → Crown of Saint Stephen) or `ruler ?= { has_culture = cu:X }` (AU-with-Amhara-ruler → Solomonic African Empire). Higher priority wins on match.

If no entry matches, the engine falls back to the tag's own loc key (e.g. `AFU:0 "African Union"`), so always ship a `TAG:` and `TAG_ADJ:` loc.

Reference: `references/dynamic_name_patterns.md` has the full vanilla USA block plus a worked Intermarium example.

## Diplomatic plays for major formations

Two thin entries per major formation. Reuse vanilla `unification.dds` icon unless you have a custom one:

```
dp_unify_<name> = {
    war_goal = unification
    requires_interest_marker = no
    blocked_by_diplomatic_status = no
    add_infamy_for_starting_initiator_wargoals = no
    texture = "gfx/interface/icons/war_goals/unification.dds"
    selectable_in_lens = { always = no }
    possible = {
        NOT = { exists = c:TAG }
        NOT = { is_country_type = decentralized }
        has_technology_researched = decolonization
    }
    on_weekly_pulse = {} on_war_begins = {} on_war_end = {}
}

dp_leadership_<name> = {
    war_goal = unification_leadership
    requires_interest_marker = no
    mirror_war_goal = yes
    texture = "gfx/interface/icons/war_goals/unification.dds"
    selectable_in_lens = { always = no }
    possible = { has_technology_researched = decolonization }
    on_weekly_pulse = {} on_war_begins = {} on_war_end = {}
}
```

Each play needs five loc keys: `<name>:0`, `<name>_tooltip:0`, `<name>_desc:0`, plus for leadership `<name>_tooltip_desc:0`. Vanilla `dp_unify_germany` / `dp_leadership_germany` are good templates; copy and rename.

## Localization conventions

- Indent each entry with one leading space, format `key:0 "Value"`.
- Adjective for short tags: `TAG_ADJ:0 "Adjective"`.
- Long flavored names: `dyn_c_<snake_case>:0` and matching `dyn_c_<snake_case>_adj:0`.
- Don't hand-edit `te_formable_countries_l_english.yml` after `organize_loc.py` runs — it sorts alphabetically. Add keys in the file then re-run organize_loc.

## Standard workflow (do these in order)

1. **Lock decisions** with `AskUserQuestion` for ambiguous fields (tier? major or minor? scope of cultures?).
2. **Verify cultures + states + tags** with grep against vanilla and mod (commands in "Decisions" above).
3. **Write tag definition** in `common/country_definitions/te_formable_countries.txt` (skip for vanilla tags).
4. **Write geographic region** if needed in `common/geographic_regions/te_formable_regions.txt`.
5. **Write diplomatic plays** in `common/diplomatic_plays/te_unification_plays.txt` (major only).
6. **Write country formation** in `common/country_formation/te_formable_countries.txt`.
7. **Write dynamic names** in `common/dynamic_country_names/te_formable_countries.txt`.
8. **Update `organize_loc.py`** if introducing new tag prefixes — add the tag and its `_ADJ` to the `FORMABLE_COUNTRIES` routing rule.
9. **Add localization** to `localization/english/te_formable_countries_l_english.yml`. Run `python organize_loc.py` (it'll re-sort; verify the new keys land in the formable file).
10. **Validate**:
    - `curl -s http://localhost:8950/status` (start server with `.venv/bin/python mod_state_server.py` if not running; warmup ~60–110s).
    - `curl -X POST http://localhost:8950/reload` to pick up the new files.
    - `curl -s http://localhost:8950/validate/engine-coverage` — expect 0 unknown / 0 suspicious modifiers.
    - `curl -s http://localhost:8950/localize/<tag>` and `/localize/<dyn_c_key>` — confirm roundtrips.
    - `curl -s 'http://localhost:8950/raw/Diplomatic%20Plays/dp_unify_<name>'` — confirm it parses.
    - `curl -s "http://localhost:8950/logs/debug?summary=true&dedupe=true&mod_only=true"` — only matters after the user re-launches Vic3 (logs are runtime, not parse-time). Watch for `script_parse_error`, `Duplicated key`, `Unknown trigger type`. Ignore stale entries from prior sessions.

## Known gotchas

- **Vanilla tag overrides**: re-declaring a vanilla tag (e.g. `BHT`, `IDN`) in `common/country_formation/te_*.txt` overrides vanilla cleanly because the engine merges per-tag and last-write wins. This is **not** a top-level entity collision — those only happen for things like culture/good/modifier names declared at the top level. If you see a `Duplicated key X` in debug.log for a country_formation tag, switch to `REPLACE:TAG = { … }` directive prefix.
- **`on_country_formed` extends, doesn't replace**: Vic3 merges `on_xxx` definitions across files. The mod already extends it in `common/on_actions/fmc_on_actions.txt:143`. To wire a custom flavor event for a new tag, add an `if/else_if` clause inside that block — vanilla's giant if-chain runs in parallel.
- **Generic `formation.17` auto-fires** for new tags not on its NOR-list (`events/misc_unifications.txt:1042`). For MVP, leave it — you only need a custom event for richer flavor.
- **Subjects and the tag**: `is_main_tag_only = yes` on dynamic names means subjects with the same tag don't use these names. Vanilla BHT has a priority-1 "Dominion of India" entry gated on `is_subject = yes`; mod entries should be priority 0 to fall through.
- **Loc key routing**: any new prefix you introduce that doesn't match a `categorize_key` rule lands in MISCELLANEOUS. The 5 `dp_*_tooltip` keys for unification plays land in UNUSED unless `organize_loc.py` learns about implicit diplomatic-play keys (mod ships `te_unused_l_english.yml` so they still load — but they're harder to find). Optional improvement: add a `find_diplomatic_play_keys` function modeled on `find_diplo_action_keys`.
- **State name pitfalls**: vanilla doesn't have `STATE_RWANDA`, `STATE_BUGANDA`, `STATE_BURUNDI`, `STATE_LIVONIA` — they're folded into `STATE_KAZEMBE`, `STATE_UGANDA`, `STATE_RIGA`/`STATE_COURLAND`. Always grep before using.

## Output expectations

When invoked, this skill should produce a **complete, validated** set of files for the requested formable(s). The user shouldn't need to fill in blanks. Specifically:

- All cultures verified to exist in vanilla.
- All states verified to exist in vanilla.
- All loc keys present in `te_formable_countries_l_english.yml`.
- `organize_loc.py` runs clean and routes the new keys correctly.
- `mod_state_server` reloads clean; `/validate/engine-coverage` reports 0 unknown / 0 suspicious modifiers attributable to the new content.

If any verification step fails, fix it before reporting done. Don't claim success on partial work.

## Reference files

- `references/vanilla_examples.md` — Canonical formation entries (GER, ITA, SCA, FND, YUG major; POL, ARA, IDN minor) and full USA dynamic-name block, quoted verbatim with file paths and line numbers for re-verification.
- `references/dynamic_name_patterns.md` — Worked example (Intermarium) showing every government variant and 2nd-axis flavor, plus the `coa_def_*_flag_trigger` table.
- `references/loc_routing.md` — Exact `categorize_key` extension snippet to drop into `organize_loc.py` when introducing new tags.
