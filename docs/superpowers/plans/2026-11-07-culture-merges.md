# Culture Merges Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a country that holds most of a set of closely related cultures, treats them as equals and has the right technology merge them into one national culture over about two decades, ending in a worldwide switch.

**Architecture:** A Python config lists every merge (result, parts, tiers, waits). A post-load regenerator turns it into the result cultures, their loc, and per-merge dispatch script: triggers, effects, one journal entry and start button per merge. The dispatch calls a small set of hand-written, parameterized helpers that run a yearly census, gate each part, convert pops and switch parts. Merge state lives in global and country variables, so it survives a revolution.

**Tech Stack:** Paradox Clausewitz script (Victoria 3 1.15), Python 3.11/3.12 generator and `unittest` tests, `organize_loc.py`, the mod's offline audits.

**Spec:** `docs/superpowers/specs/2026-11-07-culture-merges-design.md` (read it first; this plan argues from it).

## Global Constraints

- Work in a sparse worktree (`CLAUDE.md` § "Parallel checkouts"), branch `culture-merges` from `origin/main`. Never `POST /reload` the main checkout's server; reload-check on a second server started from the worktree on port 8951.
- Brace files: tab indentation, exactly one UTF-8 BOM. Generated files must pass `scripts/format_paradox_tabs.py --check`.
- Loc and docs are American English; bold is `#b X#!`, never `[b]`.
- New result culture ids start `cm_` (`cm_german`, `cm_east_slavic`). Another mod (Syncretic Cultures) defines `german`, and a duplicate culture key is dropped.
- Merge state is kept in **variables**, never modifiers or variable lists (revolution inheritance).
- No `REPLACE:` of vanilla content. Changes to vanilla entries go through `INJECT:` only.
- Game rule `culture_merges_rule`: settings `culture_merges_enabled` (default) and `culture_merges_disabled`. Gate trigger `te_cm_system_enabled = { NOT = { has_game_rule = culture_merges_disabled } }`.
- Numbers fixed by the spec (owner): hold **0.60** of each part; subjects and bloc members convert at **half** the starter's rate; pace about **20 years** for a developed country, about **40** for a slow one; switch at **2/3** result share in the part's homeland states; vanilla-entry wait capped at **20 years**.
- Numbers this plan fixes (designer's calls, tune later): accepted means `acceptance_status_4` (60); very high means `acceptance_status_5` (80). A meaningful share is 0.10 of the sphere's holdings. The tier-1b counter is 30 years and the tier-2 counter 50 years.
- **One hysteresis convention:** a gate first opens, and reopens, at its spec value, and closes only past a looser one.

  | Gate | Opens and reopens at | Closes past |
  |---|---|---|
  | Hold | 0.60 | below 0.50 |
  | Acceptance (accepted) | 60 | below 55 |
  | Acceptance (very high) | 80 | below 75 |
  | SoL gap | below 3 | above 4 |
- Tier techs: tier 1 `pan-nationalism`; tier 1b `mass_media`; tier 2 `television` (this plan's pick for the spec's "later media technology").
- Python must also run on 3.11: no f-string that reuses its own quote inside braces. Every test file ends with exactly one `if __name__ == "__main__": unittest.main()`.
- Commits: thematic, stage by path (never `git add -a`), end with the session's `Co-Authored-By` lines.

### Names (every task uses these)

Tiers are numbers in script: `1` = tier 1, `2` = tier 1b, `3` = tier 2. `<m>` is a merge key, `<c>` a culture id, `<r>` a result culture id, `<i>` the merge's index (1-based, config order).

| Kind | Name | Scope / meaning |
|---|---|---|
| global var | `te_cm_state_<m>` | 0 or missing idle, 1 running, 2 complete |
| global var | `te_cm_starter_<m>` | the running merge's starting country |
| global var | `te_cm_home_<c>` | the culture's pops living in its homeland states, at the last census (world pops if it has no homeland state) |
| global var | `te_cm_in_<c>` | index of the running merge this culture has joined |
| global var | `te_cm_joined_<m>_<c>` | 1 once the part has joined merge `<m>` |
| global var | `te_cm_dom_<m>_<c>` | result share of result + part pops in `<c>`'s homeland states |
| global var | `te_cm_switched_<c>` | the result culture (a culture scope) `<c>` switched into |
| global var | `te_cm_census_lock` | timed lock, 330 days |
| country var | `te_cm_held_<m>_<c>` | the sphere's share of `te_cm_home_<c>`, counting only pops in the culture's homeland states (0–1) |
| country var | `te_cm_ok_<m>_<c>` | 1/0: hold and acceptance gates pass, with hysteresis |
| country var | `te_cm_sol_<m>_<c>` | the part's pop-weighted average SoL across the sphere |
| country var | `te_cm_sol_ok_<m>` | 1/0: the SoL gap gate, with hysteresis |
| country var | `te_cm_years_<m>_<c>` | the tier-1b/tier-2 years-together counter |
| country var | `te_cm_wait_years_<m>` | years the merge has qualified while waiting for a vanilla entry |
| country var | `te_cm_paused_<m>_<c>` | 1 while this converting country fails acceptance locally |
| modifier | `country_culture_merge_speed_mult` | registered country modifier, percent |

A country's **sphere** is the country itself, its subjects at any depth (`every_subject_or_below`), and, if `is_power_bloc_leader = yes`, the members of its bloc (`power_bloc = { every_power_bloc_member = { … } }`). The bloc list includes the leader itself.

## Review Focus

1. **The starter disappears mid-merge** (annexed, revolution won by the other side, released into a subject). The merge should go back to idle and keep its joined parts, dominance and counters, so another qualifying country can pick it up. A tag change through formation keeps the same country, so it is not a disappearance. Test: `test_starter_loss_returns_merge_to_idle` (Task 5).
2. **A culture in two merges** (Yankee in American and Anglophone; Slovene in Yugoslav and Pan-Slavic). It should join only one running merge. A merge's result can't be a part elsewhere until that merge is complete. Test: `test_overlapping_parts_are_exclusive` (Task 4).
3. **Empty homeland states.** A part whose homeland states hold no result or part pops makes the dominance denominator 0. Expected: no division by zero, and the part is not dominant unless it has no pops anywhere, in which case it switches. Test: `test_dominance_value_guards_zero` (Task 6).
4. **A country formed or released after a switch** from a definition that lists only parts (Bavaria released from Germany). It should get the result as primary the same day (`on_country_formed`) or within a month. Test: `test_primary_refresh_is_wired` (Task 6).
5. **The rule turned off in a running game.** Every pulse stops, and every merge entry concludes through its hidden invalid outcome. Test: `test_every_entry_point_checks_the_rule` (Task 5).

---

### Task 0: Worktree and spec

- [ ] **Step 1:** Create the sparse worktree: `git worktree add --no-checkout -b culture-merges ../Vic3TimelineExtended-cm origin/main && cd ../Vic3TimelineExtended-cm && git sparse-checkout set --no-cone '/*' '!/gfx/' && git checkout culture-merges`.
- [ ] **Step 2:** Move the untracked spec and this plan from the main checkout (`docs/superpowers/specs/2026-11-07-culture-merges-design.md`, `docs/superpowers/plans/2026-11-07-culture-merges.md`) into the worktree at the same paths, and delete them from the main checkout.
- [ ] **Step 3:** Commit both: `git add docs/superpowers/specs/2026-11-07-culture-merges-design.md docs/superpowers/plans/2026-11-07-culture-merges.md && git commit -m "Culture merges: design and implementation plan"`.

Use the main checkout's venv throughout: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python`.

### Task 1: The merge config

**Files:**
- Create: `scripts/generators/culture_merges_config.py`
- Test: `test_culture_merges_config.py`

**Interfaces:**
- Produces:
  - Frozen dataclasses:
    - `Part(cultures: tuple[str, ...], tier: int | None = None, wait_for: tuple[str, ...] = ())`. `cultures` holds the alternatives filling one slot, usually one id. `tier` is None to derive it.
    - `NewCulture(name: str, color: tuple[int, int, int])`.
    - `Merge(key: str, result: str, new: NewCulture | None, core: tuple[Part, ...], optional: tuple[Part, ...] = (), components: tuple[str, ...] = (), skip_if_dlc: str | None = None)`.
  - `MERGES: tuple[Merge, ...]`.
  - `merge_by_key(key: str) -> Merge`.
  - `derive_tier(merge: Merge, culture: str, cultures: dict) -> int`.
  - `validate(cultures: dict) -> list[str]`.
  - `cultures` is the parsed `Cultures` dict: id → `{"heritage", "language", …}`. Trait groups come from `Discrimination Traits`, passed in the same dict under the key `"__traits__"`.

Roster: Appendix A's "Include" rows, plus Pan-Slavic, Pan-Turkic, Pan-Malay and East African.
- **Order core parts largest first.** The first core part supplies the new culture's heritage, language, religion and graphics (Task 2).
- **Absorb merges** list the result as their first core part. A slot culture equal to the merge's result is held and acceptance-tested only: it is never joined, converted, measured for dominance or switched. A merge is complete when every joined core culture other than the result has switched.
- **French:** core `french`, `wallonian`, `Part(("occitan",), tier=1)`; optional `Part(("catalan",))`.
- **American:** core `yankee`, `dixie`; optional `afro_american`. `dixie` waits for `je_acw_reincorporate` and `afro_american` for `je_acw_equality`.
- **Anglophone:** core `british`, `Part(("yankee", "cm_american"))`; optional `anglo_canadian`, `australian`, `scottish`, `dixie`, `afro_american`.
- **East Slavic:** result `cm_east_slavic`, name "East Slavic". `ukrainian` waits for `je_ukraine_cultural_renaissance` and `byelorussian` for `je_belarus_cultural_renaissance`. No part waits for `je_russification`.
- **Brazilian:** `skip_if_dlc="rp1_content"`.
- **Latin:** `components=("french", "italian")`. Core `french`, `cm_italian`, `spanish`, `portuguese`; optional `romanian`, `platinean`, `argentine`, `uruguayan`, `chilean`.

`derive_tier` measures against the merge's core parts. It returns:
- the override, if one is set;
- `1` for a part sharing a language with a core part that also shares its heritage;
- `2` for a shared language with no core part of the same heritage;
- `3` for a shared language group only.

A `cm_` result counts as having its merge's first core part's traits.

`validate` errors on:
- a culture absent from vanilla that is not some merge's `cm_` result;
- a `cm_` result that vanilla already defines;
- the same culture in two slots of one merge;
- a part with no language group in common with any core part (cross-family);
- a component that isn't a merge key;
- a tier-3 merge without components.

- [ ] **Step 1: Write the failing tests** in `test_culture_merges_config.py`. Load vanilla cultures and traits the way `test_automation_policy.py:140` loads buildings (`ModState` over `vanilla_parsed.load()`, types `{"Cultures": "cultures", "Discrimination Traits": "discrimination_traits"}`).
  - `test_validate_is_clean`: `self.assertEqual(cfg.validate(cultures), [])`.
  - `test_german_parts`: `[p.cultures for p in m.core] == [("north_german",), ("south_german",)]` and the optional parts are `alemannic`, `east_german`.
  - `test_tiers`:
    - `derive_tier(french, "occitan") == 1`
    - `derive_tier(french, "catalan") == 3`
    - `derive_tier(american, "afro_american") == 2`
    - `derive_tier(american, "dixie") == 1`
  - `test_brazil_skips_with_dlc`: `merge_by_key("brazilian").skip_if_dlc == "rp1_content"`.
  - `test_no_wait_on_russification`: no `wait_for` anywhere contains `je_russification`.
  - `test_cross_family_part_rejected`: validate a copy of `MERGES` plus `Merge("x", "british", None, (Part(("british",)), Part(("welsh",))))` and assert an error naming `welsh`.
  - `test_skipped_merges_absent`: no merge key in `{"pan_germanic", "pan_bantu"}`.
  - `test_overlapping_parts_are_exclusive`: every culture appears in at most one slot per merge, and every `cm_` id used as a part is some merge's result.
- [ ] **Step 2:** Run `.venv/bin/python -m pytest test_culture_merges_config.py -q`. Expected: fails, because the module doesn't exist yet.
- [ ] **Step 3:** Implement `scripts/generators/culture_merges_config.py` with the dataclasses, the roster and the three functions.
- [ ] **Step 4:** Run the tests again. Expected: all pass.
- [ ] **Step 5:** Commit: `git add scripts/generators/culture_merges_config.py test_culture_merges_config.py && git commit -m "Culture merges: merge roster config with tier derivation and validation"`.

### Task 2: Generator, part 1: result cultures, traits, loc

**Files:**
- Create: `scripts/generators/gen_culture_merges.py`.
- Create (generated):
  - `common/cultures/te_merged_cultures.txt`
  - `common/discrimination_traits/te_merged_culture_traits.txt`
  - `localization/english/te_culture_merges_generated_l_english.yml`
- Modify:
  - `organize_loc.py`: `CATEGORIES`, `GENERATED_CATEGORIES`, a `categorize_key` rule, and a `CULTURE_MERGE_RESULT_KEYS` tuple beside `CITY_STATE_LOC_KEYS`.
  - `mod_state_server.py`: a `POST_LOAD_REGENERATORS` entry, before `organize_loc`.
  - The roster docs: `CLAUDE.md` (the regenerator count and bullet), `docs/guides/python_tools.md`, `docs/auto_generated_files.md` (one row per output).
  - `scripts/nightly_audit_select.py`: add the outputs to `EXCLUDED_REGISTRY_GLOBS`.
- Test: `test_gen_culture_merges.py`.

**Interfaces:**
- Consumes: Task 1's `MERGES`, `derive_tier`.
- Produces:
  - `plan_outputs(root: Path = ROOT) -> dict[Path, str]`. Later tasks add outputs to it.
  - `regenerate(mod_state=None, *, root: Path = ROOT, dry_run: bool = False) -> dict`, which returns `{"changed": bool, "changed_files": list[str]}`.
  - `main(argv=None) -> int`, with `--check` and `--dry-run`.
  - Model the module on `gen_seabed_basins.py`: write on change, `utf-8-sig`, and the header `# AUTO-GENERATED by scripts/generators/gen_culture_merges.py - do not edit manually.`
  - Read vanilla through `vanilla_parsed` the way `gen_covert_tech_theft.py`'s `load_state()` does.
  - Render loc through `organize_loc._render_loc_file([(section_label("CULTURE_MERGES_GENERATED"), {...})])`.

Each new result culture takes from the **first core part**:
- `heritage`, `language`, `religion`, `graphics`, `ethnicities`, `obsessions`;
- the name lists, merged: every core and optional part's lists in config order, without duplicates.

Its `color` comes from the config. Tier-3 results (`components` non-empty) get two new traits instead:
- `language_cm_<m>`, whose `trait_group` is the language group the parts share;
- `heritage_cm_<m>`, whose `trait_group` is the shared heritage group, or the first core part's group if the parts share none.

Loc gives each `cm_` culture, and each new trait, `0 "<NewCulture.name>"`.

`organize_loc.categorize_key` returns `"CULTURE_MERGES_GENERATED"` for these keys, placed before the `je_` rule:
- a key in `CULTURE_MERGE_RESULT_KEYS`, which holds the `cm_` ids and the new trait keys;
- a key starting `te_cmg_` or `je_te_cm_`.

It returns `"MISCELLANEOUS"` for a key starting `te_cm_`, placed before the `_add`/`_mult` rule.

- [ ] **Step 1: Write the failing tests** in `test_gen_culture_merges.py`:
  - `test_the_committed_files_are_current`: `self.assertFalse(gen.regenerate(dry_run=True)["changed"], "run python3 scripts/generators/gen_culture_merges.py")`.
  - `test_one_bom`: every output's bytes start with `b"\xef\xbb\xbf"` and `[3:]` doesn't.
  - `test_german_culture`: parse `te_merged_cultures.txt` with `ParadoxFileParser`. `cm_german` has `heritage = heritage_germanic` and `language = language_germanophone`, and its `male_common_first_names` includes every name in vanilla `north_german`'s.
  - `test_latin_traits`: `language_cm_latin` exists in the traits file with `trait_group = language_group_romance`.
  - `test_result_keys_in_sync`: `set(organize_loc.CULTURE_MERGE_RESULT_KEYS) == gen.result_loc_keys()` and `organize_loc.categorize_key("cm_german") == "CULTURE_MERGES_GENERATED"`.
  - `test_every_new_culture_has_loc`: each `cm_` id is a key in the generated loc file.
- [ ] **Step 2:** Run `.venv/bin/python -m pytest test_gen_culture_merges.py -q`. Expected: fails on the import.
- [ ] **Step 3:** Implement the generator (`result_loc_keys() -> set[str]` included) and the `organize_loc` changes, then run `python3 scripts/generators/gen_culture_merges.py`.
- [ ] **Step 4:** Run the new tests plus `test_nightly_audit_select.py`, `test_organize_loc*.py` and `scripts/analysis/check_post_load_rosters.py`. Then run `python3 organize_loc.py --check`, `scripts/analysis/check_localization_files.py` and `scripts/format_paradox_tabs.py --check common/cultures/te_merged_cultures.txt common/discrimination_traits/te_merged_culture_traits.txt`. Expected: all clean.
- [ ] **Step 5:** Commit the generator, its outputs, `organize_loc.py`, `mod_state_server.py`, the roster docs, `scripts/nightly_audit_select.py` and the test: "Culture merges: generator for the merged cultures, their traits and loc".

### Task 3: Rule, values, speed modifier

**Files:**
- Modify: `common/game_rules/extra_game_rules.txt`; `localization/english/te_game_rules_l_english.yml` (`rule_culture_merges_rule`, `setting_culture_merges_enabled`/`_desc`, `setting_culture_merges_disabled`/`_desc`); `common/institutions/extra_institutions.txt` (`institution_ministry_of_culture` gains `country_culture_merge_speed_mult = 0.10`, per level by the engine).
- Create:
  - `common/scripted_triggers/te_culture_merge_triggers.txt`: `te_cm_system_enabled`, `te_cm_tier_tech = { TIER = n }`, `te_cm_in_sphere` (country scope, against `scope:te_cm_starter`).
  - `common/script_values/te_culture_merge_values.txt`: every number in Global Constraints as a named value, plus the rate.
  - `common/modifier_type_definitions/te_culture_merge_modifier_types.txt`: `country_culture_merge_speed_mult = { color = good percent = yes decimals = 0 }`.
  - `common/laws/te_culture_merge_law_injections.txt`: `INJECT:law_public_schools`, modifier +0.25.
  - `common/technology/technologies/te_culture_merge_tech_injections.txt`: `radio` +0.15, `film` +0.10, `mass_propaganda` +0.15.
  - Loc: `country_culture_merge_speed_mult`/`_desc` in `te_modifiers_l_english.yml`.
- Test: `test_culture_merge_values.py`.

**Interfaces:**
- Produces:
  - **Triggers:**
    - `te_cm_system_enabled`.
    - `te_cm_tier_tech = { TIER = n }`: `has_technology_researched` of `pan-nationalism`, `mass_media` or `television` for tier 1, 2 or 3.
    - `te_cm_in_sphere` (country scope): `this = scope:te_cm_starter`, or `is_subject_of = scope:te_cm_starter`, or the starter leads a power bloc this country is in.
  - **Threshold values:**
    - `te_cm_hold_open = 0.60`, `te_cm_hold_close = 0.50`
    - `te_cm_accept_open = acceptance_status_4`, `te_cm_accept_close = 55`, `te_cm_accept_high_open = acceptance_status_5`, `te_cm_accept_high_close = 75`
    - `te_cm_sol_gap_close = 4`, `te_cm_sol_gap_open = 3`
    - `te_cm_meaningful_share = 0.10`, `te_cm_switch_share = 0.667`
    - `te_cm_years_tier2 = 30`, `te_cm_years_tier3 = 50`, `te_cm_wait_cap_years = 20`, `te_cm_sphere_rate_factor = 0.5`
  - **Rate:** `te_cm_pop_rate` (pop scope; reads `scope:te_cm_part` and `scope:te_cm_starter`). It returns this year's conversion fraction, 0–1:
    - `te_cm_base_rate`
    - × literacy factor (`te_cm_literacy_base + literacy_rate`)
    - × urbanization factor (`1 + te_cm_urban_weight × state.total_urbanization`)
    - × `(1 + owner.modifier:country_culture_merge_speed_mult)`
    - × 0.1 if `pop_is_discriminated = yes`
    - × 2 if the pop's state region isn't a homeland of `scope:te_cm_part`
    - × `te_cm_sphere_rate_factor` if `owner != scope:te_cm_starter`
    - `max = 0.5`.

- [ ] **Step 1: Write the failing tests** in `test_culture_merge_values.py`:
  - **Values match the spec:** read the values file with `ParadoxFileParser` and assert:
    - `te_cm_hold_open == 0.60` and `te_cm_switch_share == 0.667`
    - `te_cm_hold_close < te_cm_hold_open`, `te_cm_accept_close < te_cm_accept_open`, `te_cm_accept_high_close < te_cm_accept_high_open`
    - `te_cm_sol_gap_open < te_cm_sol_gap_close`
    - `te_cm_sphere_rate_factor == 0.5`
    - `te_cm_wait_cap_years == 20`
  - **Rule polarity** (`test_rule_polarity`): the trigger body is exactly `NOT = { has_game_rule = culture_merges_disabled }`, and the rule's default is `culture_merges_enabled`.
  - **Pace model** (`test_pace_targets`): mirror `te_cm_pop_rate` in Python, reading its coefficients from the values file. With remaining share `(1 - f) ** n` and the switch at `n = ln(1 - 0.667) / ln(1 - f)`, assert:
    - developed profile (literacy 0.8, urbanization 0.4, public schools, ministry level 3, radio and film researched, pops in their homeland, starter): `n` within 17–23 years;
    - slow profile (literacy 0.3, urbanization 0.1, no grants): `n` within 35–45 years;
    - a bloc-member pop takes about 2× the developed profile's years.
- [ ] **Step 2:** Run the tests. Expected: they fail.
- [ ] **Step 3:** Write the files, then tune `te_cm_base_rate`, `te_cm_literacy_base` and `te_cm_urban_weight` until the pace test passes.
- [ ] **Step 4:** Run the tests plus `.venv/bin/python modifier_visibility_audit.py --strict` and `loc_coverage_audit.py --strict`. Expected: they pass.
- [ ] **Step 5:** Commit: "Culture merges: game rule, thresholds, conversion rate and its speed modifier".

### Task 4: Census and part gates

**Files:**
- Create: `common/scripted_effects/te_culture_merge_effects.txt` (census helpers); `common/on_actions/te_culture_merge_on_actions.txt` (`on_yearly_pulse_country = { on_actions = { te_cm_yearly_on_action } }`).
- Modify: `scripts/generators/gen_culture_merges.py`, adding `common/scripted_effects/te_culture_merges_generated_effects.txt` and `common/scripted_triggers/te_culture_merges_generated_triggers.txt`.
- Test: `test_culture_merge_census.py`.

**Interfaces:**
- Consumes: Task 3's values and `te_cm_in_sphere`.
- Produces:
  - **Hand-written helpers:**
    - `te_cm_census_culture = { CULTURE = c }`. Any scope. Sets `te_cm_home_<c>`: the `total_size` of pops with `culture = cu:<c>` over `cu:<c> = { every_scope_homeland_state = { … } }`. If the culture has no homeland state, it sums the world instead, iterating only countries passing `culture_percent_country = { target = cu:<c> value > 0 }`. Every share in this system is taken over homeland states (owner, 2026-11-07); diaspora pops convert at the switch but don't weigh on the gates.
    - `te_cm_census_part = { MERGE = m CULTURE = c TIER = n }`. Country scope, the candidate.
      - Sets `te_cm_held_<m>_<c>` (sphere pops in the culture's homeland states ÷ `te_cm_home_<c>`) and `te_cm_sol_<m>_<c>`.
      - Sets `te_cm_ok_<m>_<c>` with hysteresis:
        - it opens at hold ≥ `te_cm_hold_open` and acceptance ≥ `te_cm_accept_open`;
        - it closes below `te_cm_hold_close`, or when acceptance falls under `te_cm_accept_close`;
        - for tier 2 the acceptance thresholds are `te_cm_accept_high_open` / `te_cm_accept_high_close` instead;
        - acceptance is tested in every sphere country holding at least `te_cm_meaningful_share` of the sphere's pops of `<c>` in its homeland states.
      - For TIER 2 and 3, adds 1 a year to `te_cm_years_<m>_<c>` while the gate is on; it never decreases.
  - **Generated, per merge:**
    - `te_cmg_<m>_is_candidate` (country): `te_cm_system_enabled`; a core culture is primary; `te_cm_tier_tech` for the highest tier among the core slots (Anglophone's core is tier 2); `te_cm_state_<m>` < 2; and `NOT = { has_dlc_feature = <skip> }` when the merge is skipped with that DLC.
    - `te_cmg_census_<m>`: for every candidate country, `te_cm_census_part` per culture in every slot.
    - `te_cmg_<m>_core_ok` (country): every core slot has an alternative with `te_cm_ok_<m>_<c> = 1` that is available. Available means not `te_cm_in_<c>` for another merge's index, and, for a `cm_` id, its merge complete.
    - `te_cmg_<m>_<c>_can_join` (country), one per slot culture:
      - `te_cm_ok_<m>_<c> = 1`, available, and not yet `te_cm_joined_<m>_<c>`;
      - `te_cm_tier_tech` for its own tier;
      - for tier 2: `te_cm_years_<m>_<c>` ≥ `te_cm_years_tier2`; for tier 3: ≥ `te_cm_years_tier3`.
    - SoL gap, at the end of `te_cmg_census_<m>`: the largest minus the smallest `te_cm_sol_<m>_<c>` over the core cultures and the joined ones sets `te_cm_sol_ok_<m>` on the candidate. It closes above `te_cm_sol_gap_close` and opens below `te_cm_sol_gap_open`.
  - **Generated, global:** `te_cmg_census_all`, which runs inside `te_cm_yearly_on_action` behind `te_cm_census_lock` (the CH lock pattern, `days = 330`).
    - It runs `te_cm_census_culture` for every culture of a merge that is censused, then each `te_cmg_census_<m>`.
    - A merge is censused when it is idle with a candidate, or running or complete with its starter alive and some slot culture neither switched nor absent (`any_country = { culture_percent_country = { target = cu:<c> value > 0 } }` false). A complete merge keeps its census so late parts can still join.

- [ ] **Step 1: Write the failing tests** in `test_culture_merge_census.py`:
  - `test_census_is_locked`: the yearly on_action sets `te_cm_census_lock` with `days = 330` and tests `NOT = { has_global_variable = te_cm_census_lock }` before the census.
  - `test_census_runs_only_when_needed`: every `te_cmg_census_<m>` call sits under a limit that is either `any_country = { te_cmg_<m>_is_candidate = yes }` with the merge idle, or the merge running or complete with `exists = global_var:te_cm_starter_<m>`.
  - `test_sol_gate_has_hysteresis`: the generated SoL gap block reads both `te_cm_sol_gap_close` and `te_cm_sol_gap_open`.
  - `test_census_walks_homeland_states`: `te_cm_census_culture` iterates `every_scope_homeland_state`, and its world fallback has a `culture_percent_country` limit before `every_scope_pop`.
  - `test_counters_are_variables`: no `add_modifier` and no `add_to_variable_list` in the culture merge script files.
  - `test_every_generated_call_matches_its_helper`: run `script_argument_audit` on the new files and assert no findings.
- [ ] **Step 2:** Run the tests. Expected: they fail.
- [ ] **Step 3:** Implement the helpers and extend the generator. Regenerate.
- [ ] **Step 4:** Run the tests, then `.venv/bin/python script_argument_audit.py --strict`, `iterator_limit_audit.py --strict` and `empty_effect_audit.py --strict`. Expected: they pass.
- [ ] **Step 5:** Commit: "Culture merges: yearly census and per-part gates".

### Task 5: Starting a merge: journal entries, buttons, AI

**Files:**
- Modify:
  - `scripts/generators/gen_culture_merges.py`, adding:
    - `common/journal_entries/te_culture_merges_generated.txt`
    - `common/scripted_buttons/te_culture_merges_generated_buttons.txt`
    - `common/scripted_progress_bars/te_culture_merges_generated_bars.txt`
    - `common/script_values/te_culture_merges_generated_values.txt`
    - the merge entries' loc
  - `common/scripted_effects/te_culture_merge_effects.txt`, adding `te_cm_start_merge`, `te_cm_join_part` and `te_cm_release_starter`.
  - The hand-written loc for the shared phrases (`te_cm_*`, in `te_miscellaneous_l_english.yml` per Task 2's rule).
- Test: `test_culture_merge_entries.py`.

**Interfaces:**
- Consumes: Task 4's `te_cmg_<m>_is_candidate` and `te_cmg_<m>_core_ok`, plus the census variables.
- Produces:
  - **Start helpers:**
    - `te_cm_start_merge = { MERGE = m RESULT = r INDEX = i }` (country). Sets `te_cm_state_<m> = 1` and `te_cm_starter_<m> = this`, then `add_primary_culture = cu:<r>`.
    - `te_cm_join_part = { MERGE = m CULTURE = c INDEX = i }`. Sets `te_cm_joined_<m>_<c>` and `te_cm_in_<c> = <i>`.
    - `te_cm_release_starter = { MERGE = m }`. Sets the state back to 0 and removes `te_cm_starter_<m>`. Joined parts, dominance and counters stay.
  - **`te_cmg_<m>_can_start`** (country) requires:
    - `is_candidate`, `core_ok`, and `te_cm_sol_ok_<m> = 1`;
    - for each component: `te_cm_state_<comp> = 2`. Whether the component's result is held in this sphere is already the core slot's hold test, so no primary is required: an Italy that ran its own merge inside France's bloc still counts;
    - for each wait-listed vanilla entry on a core part: `NOT = { has_journal_entry = <je> }`, or `te_cm_wait_years_<m>` ≥ `te_cm_wait_cap_years`. The census adds a year to `te_cm_wait_years_<m>` while the merge qualifies in every other way.
  - **Button `te_cmg_start_<m>_button`:**
    - `visible`: the merge is idle;
    - `possible`: `te_cmg_<m>_can_start`, with each condition in its own `custom_tooltip`;
    - `effect`: `te_cm_start_merge`, then `te_cm_join_part` for every slot culture other than the result passing `te_cmg_<m>_<c>_can_join` and not waiting on a vanilla entry;
    - `ai_chance = { value = 100 }`.
  - **Late joining:** the census, for a running or complete merge, calls `te_cm_join_part` on the starter for every slot culture that passes `te_cmg_<m>_<c>_can_join` and isn't waiting.
  - **Journal entry `je_te_cm_<m>`**, modelled on `je_colonial_empire.txt`:
    - `group = je_group_internal_affairs`, `activation_description = { always = yes }`;
    - `disable_evaluation = { NOT = { te_cm_system_enabled = yes } }`, the form Grand Monuments uses with the same polarity (`je_grand_monuments.txt`);
    - `is_shown_when_inactive`: `te_cm_system_enabled = yes` written as its own conjunct, then `te_cmg_<m>_is_candidate`. Read `test_journal_entry_shape.py`'s `disable_evaluation` check first; it looks for the rule gate among the conjuncts;
    - `possible`: `te_cmg_<m>_can_start`, or the merge running or complete with `this = global_var:te_cm_starter_<m>`. So the inactive entry lists the real conditions, and it goes active exactly when a merge can begin;
    - `can_deactivate = no`;
    - `scripted_button = te_cmg_start_<m>_button`, `scripted_progress_bar = te_cmg_<m>_bar`;
    - `status_desc`: one triggered desc per state (idle with the first failing condition, running with the lowest core dominance and the starter's rate, complete);
    - a complete outcome when `te_cm_state_<m> = 2`;
    - a hidden invalid outcome when the rule is off, or when the merge is running with another starter;
    - `can_revolution_inherit = yes`.
  - **Progress value `te_cmg_<m>_progress`:** the lowest `te_cm_dom_<m>_<c>` over joined core parts, ÷ `te_cm_switch_share`, capped at 1.
  - **Starter loss:** the yearly on_action calls `te_cm_release_starter` for every running merge whose `global_var:te_cm_starter_<m>` no longer exists. Losing the result as a primary culture is not a release: whether formation replaces primaries is unverified, and Task 6's formation hook re-adds it.

- [ ] **Step 1: Write the failing tests** in `test_culture_merge_entries.py`:
  - `test_entry_shape`: run `test_journal_entry_shape`'s checks over the generated file (import its checker) with no findings.
  - `test_every_entry_has_a_button_and_bar`: one `je_te_cm_<m>`, one button and one bar per merge in `MERGES`.
  - `test_ai_presses_the_button`: every button has `ai_chance` with `value = 100`.
  - `test_starter_loss_returns_merge_to_idle`: the yearly on_action contains `te_cm_release_starter` under a limit testing `exists = global_var:te_cm_starter_<m>` negated.
  - `test_every_entry_point_checks_the_rule`: every on_action in `te_culture_merge_on_actions.txt` and every button `possible` tests `te_cm_system_enabled`.
  - `test_waits_are_capped`: each wait-listed entry appears in `te_cmg_<m>_can_start` OR'd with `te_cm_wait_cap_years`.
  - `test_colonial_holders_cannot_start`: `te_cmg_indonesian_is_candidate` requires a core culture to be primary (it contains `country_has_primary_culture = cu:javan` among an `OR`).
- [ ] **Step 2:** Run the tests. Expected: they fail.
- [ ] **Step 3:** Implement. Regenerate.
- [ ] **Step 4:** Run the tests, then `test_journal_entry_shape.py`, `test_add_journal_entry_guard.py` and `.venv/bin/python je_immediate_reset_audit.py --strict`, `button_reason_audit.py --strict`, `loc_coverage_audit.py --strict`, `long_tooltip_audit.py --strict`. Expected: all pass.
- [ ] **Step 5:** Commit: "Culture merges: a journal entry, start button and progress bar per merge".

### Task 6: Conversion, the switch, primaries and homelands

**Files:**
- Modify:
  - `common/scripted_effects/te_culture_merge_effects.txt`, adding `te_cm_convert_part`, `te_cm_census_dominance`, `te_cm_switch_part` and `te_cm_monthly_switched_culture`.
  - `common/on_actions/te_culture_merge_on_actions.txt`, adding `on_monthly_pulse_country` and `on_country_formed`.
  - The generator, adding `te_cmg_yearly_country`, `te_cmg_dominance_all`, `te_cmg_monthly_country` and `te_cmg_is_switched_part`.
  - `common/scripted_triggers/homeland_triggers.txt`: `te_homeland_removal_candidate` gains `NOT = { te_cmg_switched_part_kept = yes }`.
  - `common/scripted_effects/homeland_effects.txt`: where `te_homeland_removal_monthly_effect` completes (`remove_homeland = scope:…`), call `te_cmg_remove_switched_part_homelands` on the same `state_region` with the removed culture saved as `scope:te_cm_removed_culture`.
  - `common/script_values/te_culture_merge_values.txt`, adding the dominance sums.
- Test: `test_culture_merge_switch.py`. Also update `test_homeland_progress.py` if its interpreter rejects the new trigger.

**Interfaces:**
- Consumes: Tasks 3–5.
- Produces:
  - **`te_cm_convert_part = { MERGE = m CULTURE = c RESULT = r }`.** Country scope, a converting sphere country. It saves `scope:te_cm_part` and `scope:te_cm_starter`. On the first conversion in this country it adds `<r>` as a primary culture.
    - It skips the country while `te_cm_paused_<m>_<c> = 1`. The pause is set when the country holds a meaningful share of `<c>` and its acceptance falls under `te_cm_accept_close`, and cleared at `te_cm_accept_open`.
    - It skips a country with no pops of `<c>` (`culture_percent_country … value > 0` false).
    - Otherwise: `every_scope_pop = { limit = { culture = cu:<c> } change_pop_culture = { target = cu:<r> value = te_cm_pop_rate } }`.
  - **`te_cmg_yearly_country`** (country): for each running or complete merge where this country is `te_cm_in_sphere` of the starter, `te_cm_convert_part` for each joined, unswitched culture.
    - **The whole merge stalls** while the starter fails `te_cmg_<m>_core_ok` or `te_cm_sol_ok_<m>`.
    - **A single culture stalls** while its `te_cm_ok_<m>_<c>` is 0.
  - **`te_cmg_dominance_all`** (generated, run at the end of the census) calls `te_cm_census_dominance` for every joined, unswitched culture, then `te_cm_switch_part` for each at or over `te_cm_switch_share`.
  - **`te_cm_census_dominance = { MERGE = m CULTURE = c RESULT = r }`.** Sets `te_cm_dom_<m>_<c>` = result pops ÷ (result + part pops) over `cu:<c> = { every_scope_homeland_state … }`. With a zero denominator it sets 1 if the culture is absent from the world (the same `any_country` test), else 0. It runs in the census for every joined culture of a running merge.
  - **`te_cm_switch_part = { MERGE = m CULTURE = c RESULT = r }`.** Fires when `te_cm_dom_<m>_<c>` ≥ `te_cm_switch_share`. It:
    1. converts every pop of `<c>` in every country with `value = 1`;
    2. on `cu:<c> = { every_scope_homeland_state }`, adds the `<r>` homeland on its `state_region` where missing, and keeps `<c>`'s;
    3. sets `te_cm_switched_<c> = cu:<r>` and removes `te_cm_in_<c>`;
    4. once every joined core culture has switched, sets `te_cm_state_<m> = 2`.
  - **`te_cm_monthly_switched_culture = { CULTURE = c }`** (country). It adds `global_var:te_cm_switched_<c>` as primary where `<c>` is primary and the result isn't. It also converts any reappeared `<c>` pops, behind the `culture_percent_country` prefilter.
  - **`te_cmg_monthly_country`** calls `te_cm_monthly_switched_culture` for every culture with `te_cm_switched_<c>` set.
  - **`te_cmg_formed_country`** (generated) runs from `on_country_formed`. It calls `te_cmg_monthly_country`, then, for every running or complete merge whose starter's sphere includes the formed country and where it has already converted, adds the result as primary if it's missing.
  - **`te_cmg_is_switched_part`** (culture scope): an OR over `this = cu:<c>` together with `has_global_variable = te_cm_switched_<c>`.
  - **`te_cmg_switched_part_kept`** (culture scope, ROOT = the state, as in `te_homeland_removal_candidate`): an OR over `this = cu:<c>`, `has_global_variable = te_cm_switched_<c>`, and `ROOT.state_region = { is_homeland = global_var:te_cm_switched_<c> }`. A switched part's homeland is kept only while its successor's homeland is there too (owner, 2026-11-07).
  - **`te_cmg_remove_switched_part_homelands`** (state_region scope): for every culture `<c>` with `global_var:te_cm_switched_<c> = scope:te_cm_removed_culture` and a homeland here, `remove_homeland = cu:<c>`.

- [ ] **Step 1: Write the failing tests** in `test_culture_merge_switch.py`:
  - `test_conversion_uses_the_rate_value`: `change_pop_culture` in `te_cm_convert_part` uses `value = te_cm_pop_rate`, and only the switch uses `value = 1`.
  - `test_switch_keeps_part_homeland`: `te_cm_switch_part` has `add_homeland` and no `remove_homeland`.
  - `test_homeland_removal_skips_kept_parts_only`: `te_homeland_removal_candidate` contains `te_cmg_switched_part_kept = yes` inside a `NOT`, and the generated `te_cmg_switched_part_kept` tests `is_homeland = global_var:te_cm_switched_<c>` for every switched-capable culture.
  - `test_part_homeland_follows_its_successor`: `te_homeland_removal_monthly_effect` calls `te_cmg_remove_switched_part_homelands` right after its `remove_homeland`.
  - `test_dominance_value_guards_zero`: the dominance helper branches on a zero denominator before dividing.
  - `test_primary_refresh_is_wired`: the on_actions file wires `on_monthly_pulse_country` to `te_cmg_monthly_country` and `on_country_formed` to `te_cmg_formed_country`.
  - `test_result_never_converts_into_itself`: no generated call to `te_cm_join_part`, `te_cm_convert_part`, `te_cm_census_dominance` or `te_cm_switch_part` passes `CULTURE` equal to that merge's `RESULT` (French, Han and the other absorb merges).
  - `test_first_conversion_adds_primary`: `te_cm_convert_part` contains `add_primary_culture = cu:$RESULT$` under a `NOT = { country_has_primary_culture = cu:$RESULT$ }` limit.
- [ ] **Step 2:** Run the tests. Expected: they fail.
- [ ] **Step 3:** Implement. Regenerate.
- [ ] **Step 4:** Run the tests and `test_homeland_progress.py`, then `.venv/bin/python script_argument_audit.py --strict`, `prev_scope_audit.py --strict`, `silent_variable_audit.py --strict` and `change_variable_clamp_audit.py --strict`. Expected: they pass.
- [ ] **Step 5:** Commit: "Culture merges: yearly conversion, per-part switch, primary and homeland upkeep".

### Task 7: Russification's injected outcome

**Files:**
- Create: `common/journal_entries/te_vanilla_russification_merge.txt`. It holds `INJECT:je_russification = { outcome = { … } }`, carrying a `# REVIEWED 2026-11-07:` note on the opener that names the spec section.
- Modify: `common/scripted_triggers/te_culture_merge_triggers.txt`, adding `te_cm_russification_state_ok` (state) and `te_cm_russification_complete` (country). Modify `common/script_values/te_culture_merge_values.txt`, adding `te_cm_russian_or_east_slavic_share` (state).
- Test: `test_culture_merge_russification.py`.

**Interfaces:**
- **`te_cm_russian_or_east_slavic_share`:** the pops of `russian` or `cm_east_slavic` in the state, ÷ all pops in the state. Floor the denominator at 1.
- **`te_cm_russification_complete`:** vanilla's success-outcome trigger, copied from `08_russification.txt`, with its `culture_percent_state target = cu:russian` test replaced by `te_cm_russification_state_ok`, which is `te_cm_russian_or_east_slavic_share >= je_russification_state_russian_culture_min`.
- **The injected outcome:** trigger `te_cm_russification_complete = yes`. Its effect, headers, color and `event_outcome_effect_desc` blocks are copied from vanilla's success outcome. The effect also sets `global_var:te_cm_russification_injected_fired`.
- **The map highlight is not overridden.** That's a cosmetic gap, noted in the system doc.

- [ ] **Step 1: Write the failing tests** in `test_culture_merge_russification.py`:
  - `test_outcome_mirrors_vanilla`: the injected outcome's `effect` equals vanilla's success effect, read from `vanilla_parsed/common/journal_entries.json` (`je_russification`, which the snapshot holds), apart from the added `set_global_variable`. It runs in CI.
  - `test_counts_east_slavic`: `te_cm_russian_or_east_slavic_share` names both `cu:russian` and `cu:cm_east_slavic`.
  - `test_no_replace`: the file contains `INJECT:je_russification` and no `REPLACE:`.
- [ ] **Step 2:** Run the tests. Expected: they fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the tests, then `.venv/bin/python duplicate_key_audit.py --strict` and `loc_coverage_audit.py --strict`. Expected: they pass.
- [ ] **Step 5:** Commit: "Culture merges: count East Slavic in Russification's completion through an injected outcome".

### Task 8: Debug events, self-checks, play-test list

**Files:**
- Create:
  - `events/te_debug_cm_events.txt` (namespace `te_debug_cm`)
  - `common/scripted_effects/te_culture_merge_selfcheck_effects.txt`
  - `common/on_actions/te_culture_merge_selfcheck_on_actions.txt` (TEMPORARY header naming the play-test rows and "delete after the 1.3.x play-test")
  - `docs/testing/culture-merges-playtest.md`
- Modify: `te_events_l_english.yml`, via `organize_loc`.
- Test: `test_culture_merge_selfchecks.py`.

**Interfaces:**
- **`te_debug_cm.1`** is a console menu. Its opener line carries `# REVIEWED 2026-11-07: console-only test event (event te_debug_cm.1); never fired by script on purpose`, plus an `event_image`. Options:
  - A: run `te_cmg_census_all` now, ignoring the lock;
  - B: run `te_cmg_yearly_country` for ROOT;
  - C: run `te_cmg_dominance_all`, then switch every joined part at or over the threshold;
  - D: `debug_log` every `te_cm_*` variable of ROOT's merges.
- **Self-checks.** Each logs `TE_SELF_CHECK OK|BROKEN <name>` once a game, with numbers, and skips degenerate inputs:
  - `cm_conversion_merges_pops`: in the first converting state, the result pops after a pulse are ≤ the result pops before plus the number of buildings with part pops.
  - `cm_formation_keeps_primary`: on `on_country_formed`, for a country flagged a month earlier as having a result primary, the result is still primary before the refresh runs. BROKEN means formation replaces primaries; the monthly refresh is the fallback, already in place.
  - `cm_acceptance_scale`: at the first census with a candidate, the candidate's average acceptance of its own primary core culture is ≥ `acceptance_status_4`.
  - `cm_russification_outcome`: OK when `te_cm_russification_injected_fired` is set. BROKEN when `te_cm_russification_complete` has held for two monthly checks while `je_russification` stays active. Fallback: add `je_russification` to East Slavic's `wait_for` in the config.
- **The play-test doc** has:
  - a Self-checks table (`| Line | Means | Fallback if BROKEN |`);
  - checks for the entry's layout, a full German merge in an observer game, a switch reaching a foreign-held homeland, and Bavaria released after the switch;
  - a check that a kept part homeland with no pops shows nothing but its listing in the state panel;
  - the census cost: a late-game year tick with the rule on vs off.

- [ ] **Step 1: Write the failing tests** in `test_culture_merge_selfchecks.py`:
  - `test_selfchecks_log_once`: each self-check name appears in an `OK` and a `BROKEN` `debug_log`, under a `NOT = { has_global_variable = … }` once-guard.
  - `test_playtest_doc_lists_every_selfcheck`: each name appears in the play-test doc's table.
- [ ] **Step 2:** Run the tests. Expected: they fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the tests, then `.venv/bin/python orphaned_event_audit.py --strict` and `event_image_audit.py --strict`, and `python3 organize_loc.py --check`. Expected: they pass.
- [ ] **Step 5:** Commit: "Culture merges: console menu, self-checks and play-test list".

### Task 9: Mod content keyed on parts

**Files:**
- Modify: wherever a mod file lists a part culture for flavor or logic. Recon from the spec found:
  - `common/parties/populist_party.txt`, `green_party.txt`, `technocratic_party.txt`, `zz_te_party_join_weights.txt`
  - `common/company_types/extra_companies_flavored.txt`
  - `common/dynamic_country_names/te_formable_countries.txt`
  - `common/scripted_effects/gm_effects.txt` with `common/customizable_localization/gm_custom_loc.txt`
  - `common/scripted_triggers/te_fptp_triggers.txt`
  - `common/ideologies/` (through `ideology_modifications.py` for the generated file)
- Test: `test_culture_merge_mod_refs.py`.

**Interfaces:**
- Consumes: the generator's `result_loc_keys()`, and a new `parts_of(result: str) -> set[str]` in `culture_merges_config.py`.

- [ ] **Step 1: Write the failing test** `test_every_part_test_names_its_result`. In each listed file, every culture test naming a part culture (`culture = cu:<c>`, `country_has_primary_culture = cu:<c>`, `has_pop_culture = <c>`, list entries) sits in an `OR`/list that also names that part's result. Exceptions carry `# REVIEWED YYYY-MM-DD (culture_merge_ref): rationale`. Country definitions are exempt (§7: kept homelands cover them).
- [ ] **Step 2:** Run the test. Expected: it fails, listing the gaps.
- [ ] **Step 3:** Add each result beside its parts. Where a result shouldn't inherit the flavor, mark the line `REVIEWED`. For `common/ideologies/modified.txt`, edit `ideology_modifications.py` and run `scripts/generators/regen_ideologies_offline.py`.
- [ ] **Step 4:** Run the test, plus `test_apply_ideologies.py` and `.venv/bin/python duplicate_key_audit.py --strict`. Expected: they pass.
- [ ] **Step 5:** Commit: "Culture merges: mod flavor keyed on a part also names its result".

Vanilla content keyed on parts is listed, not patched, in Task 10's Compatibility section. Run the scan from the spec's Appendix A method and name what goes dark after a switch.

### Task 10: System doc, lessons, game-rule docs

**Files:**
- Create: `docs/systems/mod_systems/culture_merges.md`, with these `##` sections in order:
  - Culture Merges System
  - Config and Generator
  - Census and Gates
  - Conversion
  - The Switch
  - Compatibility
- Modify:
  - `docs/systems/mod_systems.md`: a row in the pops group, whose last column lists those six headings joined by `<br>`.
  - `docs/systems/mod_systems/game_rules.md`: a table row, and the system count.
  - `docs/guides/scripting_best_practices.md`. Add three short bullets in the sections they belong to:
    - an injected 1.15 outcome as the INJECT-only way to widen a vanilla journal entry's completion;
    - zero-pop homelands, and why the switch keeps them;
    - why result culture ids carry a prefix.
- Test: `test_mod_systems_index.py` (existing).

- [ ] **Step 1:** Write the doc and the edits.
- [ ] **Step 2:** Run `.venv/bin/python -m pytest test_mod_systems_index.py -q`. Expected: it passes.
- [ ] **Step 3:** Commit: "Culture merges: system reference and lessons".

### Task 11: Player guide

**Files:**
- Modify:
  - `docs/player_guide/08-states.md`: add `## Culture merges` after `## Cultural acceptance and minorities`, matching the depth of `## Dynamic homelands`. Cover:
    - what a merge does;
    - the conditions to start, by tier;
    - the pace and what speeds it;
    - the switch;
    - one table of merges with their parts, in a compact form. The full roster goes in appendix 20 if it is longer than about 12 rows.
  - `docs/player_guide/01-introduction.md`: chapter 08's "Covers" cell, and the game-rule count.
  - `docs/player_guide/17-reference.md`: a row in "When each system appears", and the journal entries at a glance.
  - `docs/player_guide/20-appendix-reference-lists.md`, if the roster moves there.
  - `Vic3TimelineExtended_Player_Guide.pdf`, rebuilt.

- [ ] **Step 1:** Write the section, following `docs/player_guide/STYLE.md`.
- [ ] **Step 2:** Run `python3 scripts/analysis/check_player_guide_style.py --strict` and `python3 scripts/analysis/check_loc_spelling.py --check`. Expected: both clean.
- [ ] **Step 3:** Run `.venv/bin/python scripts/build_player_guide.py`, then `scripts/build_player_guide.py --check`. Expected: the check passes.
- [ ] **Step 4:** Commit the chapter files and the PDF together: "Player guide: culture merges".

### Task 12: Full gate and PR

- [ ] **Step 1:** Run `python3 scripts/generators/gen_culture_merges.py`, then `python3 organize_loc.py`. Expected: neither changes anything (`git status` clean).
- [ ] **Step 2:** From the worktree, with the dummy `VIC3_*` env vars from `CLAUDE.md`, run:
  - `.venv/bin/python -m pytest -n auto test_*.py`
  - `<main>/.venv/bin/ruff check .`
  - `scripts/format_paradox_tabs.py --check` on every changed `.txt`
  - `scripts/analysis/check_localization_files.py`
  - `organize_loc.py --check`
  - `scripts/analysis/check_loc_spelling.py --check`
  - `scripts/analysis/check_post_load_rosters.py`
  - every audit CI runs, in its CI mode

  Expected: all green. Then run the f-string scan from `CLAUDE.md` on the new Python. Expected: no hits.
- [ ] **Step 3:** Start a server from the worktree on port 8951, run `POST /reload?mod_only=true&audits_only=true`, and read `warnings` and `parse_failures`. Expected: none from the new files.
- [ ] **Step 4:** Push, and open a PR to `main` with `gh pr create --base main`. The body includes:
  - the "Player guide" line naming 08, 01, 17 (and 20 if used);
  - the designer's calls list from the spec;
  - the self-checks;
  - the play-test doc.

  Do not merge it; the owner reviews.
