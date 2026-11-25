# Assimilation Cultures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A pop no longer assimilates into a culture of another heritage group by the engine; one yearly scripted pass does that work under a three-setting game rule, through 584 generated hybrid cultures, and the Bodily Autonomy laws open the heritage step.

**Architecture:** One define switches the engine's assimilation across heritage groups off for every game. A config-driven generator writes the hybrid cultures, their traits, the nine entries the engine expects of each, their names and one dispatch ladder. A hand-written pass (effects, triggers, values, one on_action) converts pops once a year per country and branches on the rule. Two script-only modifier types put the laws' part on their tooltips.

**Tech Stack:** Paradox script (Victoria 3 1.15.2), Python 3.11/3.12 generators and `unittest` tests run under pytest, `organize_loc.py`, `scripts/preflight.py`.

**Spec:** `docs/superpowers/specs/2026-11-25-assimilation-cultures-design.md`. Read it first: this plan argues from it and does not repeat its reasons.

**Who does what** (the owner's instruction): the coordinating session writes the script of Tasks 4, 5 and 6 itself. Tasks 1 to 3, the tests of Task 5 and Task 7 go to Opus subagents, one task each, and the coordinator reads what each returns against the script before relying on it. Each subagent writes its report to a file under the scratch folder before returning.

**Where:** worktree `/home/jakef/src/te-worktrees/assimilation-cultures`, branch `feature/assimilation-cultures` (sparse: no `gfx/` textures). It has no `.venv`; use `PY=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python`. No `POST /reload` from a worktree: run generators and audits by their CLIs.

## Global Constraints

- Culture keys are `hc_<language>_<group>`: the vanilla trait keys less `language_` and `heritage_group_` (`hc_anglophone_african`, `hc_cm_latin_south_asian`). Script names are `te_hc_*`; generated script names `te_hcg_*`.
- The roster is 64 languages and 584 cultures. A pair is left out only where the group is the one heritage group every culture of that language has.
- The system's script names no vanilla culture: traits, `hc_` cultures and saved scopes only. The one literal is the sentinel `cu:hc_anglophone_african`.
- Every `cu:hc_*` read sits behind `exists = cu:<that culture>` or behind the local `te_hc_has_targets`, which only such a guard sets.
- The rule is read through `te_hc_mode_hybrid` and `te_hc_mode_none` only; each is a positive `has_game_rule` test. Neither true means Unrestricted. Every setting named in a `has_game_rule` is defined (`test_has_game_rule_targets.py`).
- Rule key `assimilation_cultures_rule`; settings `assimilation_cultures_hybrid`, `assimilation_cultures_unrestricted` (the default), `assimilation_cultures_none`. Display: "Assimilation Across Heritages"; "Hybrid Cultures", "Unrestricted", "None".
- Engine figures the pass restates, each a named script value: monthly rate 0.002, 12 months, fervor effect 0.0075 a point (the mod's define), homeland factor 0.75, yearly cap 0.5.
- Law lines: `country_cross_heritage_assimilation_add` 0.5 on Licensed Modification, 1 on Morphological Freedom, Clade Citizenship and Prescribed Form, none on Natural Form; `country_cross_heritage_assimilation_blocked_bool = yes` on `law_ethnostate`.
- Never hand-edit a generated file. Tabs in script; exactly one UTF-8 BOM on every `.txt` and loc `.yml`; American English; after loc changes run `python3 organize_loc.py` and commit all it changes.
- In-game text follows `docs/guides/loc_style_guide.md` (the `event-text` skill). Names are spliced from loc keys, never spelled, except the config's override words.
- Commit by path, never `git commit -a`. Push only at Task 8. The PR targets `main` and is not self-merged.

## Review Focus

1. **A game begun before the cultures existed, whatever its rule reads**: it must convert as Unrestricted and never name a hybrid. Pinned in Task 4 (the mode triggers) and Task 3 (every ladder branch guarded).
2. **A temporary scope left over from the previous state or country** (the host, a target hybrid): the pass must not act on it. Pinned in Task 5: `te_hc_has_host` and `te_hc_has_targets` are set to 0 at the top of every state's pass and only read after.
3. **Assimilation modifiers summing below −100%** (Clade Citizenship's −300% in a country with +100%): the rate is 0, never negative. Pinned in Task 5's value tests.
4. **A country with primary cultures of two heritage groups** (Paraguay: Platinean and Guarani): a European pop is not taken, and an African pop takes the language of the state's majority primary culture. Pinned in Task 5's outcome table.
5. **A state where no primary culture lives** (a newly incorporated colony): the host is the capital's, and an unincorporated state is never walked. Pinned in Task 5's shape tests.

---

### Task 1: Culture renderers that take culture keys

**Files:**
- Modify: `scripts/generators/gen_culture_merges.py` (the block from `_token` to `static_modifier_loc`, lines 500 to 660)
- Test: `test_gen_culture_merges.py`

**Interfaces:**
- Produces, all in `gen_culture_merges`:
  - `render_culture_block(key: str, comment: str, color: tuple[int, int, int], fields: dict) -> str`: one culture definition; `fields` as `Built.fields`.
  - `render_static_modifiers_for(cultures: list[str], header: str) -> str`
  - `render_modifier_types_for(cultures: list[str], header: str, static_file: str) -> str` (`static_file` is the file name its comment cites)
  - `static_modifier_loc_for(cultures: list[str]) -> dict[str, str]`
  - public aliases `culture_fields`, `single`, `name_list`, `ethnicities`, `token` for `_fields`, `_single`, `_list`, `_ethnicities`, `_token`.
- The existing `render_culture`, `render_static_modifiers`, `render_modifier_types` and `static_modifier_loc` keep their signatures and call the new functions.

- [ ] **Step 1: Write the failing tests** in `test_gen_culture_merges.py`, class `KeyedRenderersTest`:

```python
def test_keyed_static_modifiers_match_the_plan_form(self):
    plan = gen.build_plan(gen.load_vanilla())
    keys = [entry.merge.result for entry in plan]
    self.assertEqual(gen.render_static_modifiers_for(keys, gen.HEADER), gen.render_static_modifiers(plan))
    self.assertEqual(gen.render_modifier_types_for(keys, gen.HEADER, gen.STATIC_MODIFIERS_OUT.name), gen.render_modifier_types(plan))
    self.assertEqual(gen.static_modifier_loc_for(keys), gen.static_modifier_loc(plan))

def test_a_culture_block_is_the_merge_form_without_its_comment(self):
    entry = gen.build_plan(gen.load_vanilla())[0]
    block = gen.render_culture_block(entry.merge.result, "# x", entry.merge.new.color, entry.fields)
    self.assertEqual(block.split("\n", 1)[1], gen.render_culture(entry).split("\n", 1)[1])
```

- [ ] **Step 2: Run** `$PY -m pytest test_gen_culture_merges.py -q -k KeyedRenderers`. Expected: FAIL, `AttributeError: render_static_modifiers_for`.
- [ ] **Step 3: Add the five functions and aliases**; turn the four existing renderers into calls of them.
- [ ] **Step 4: Run** `$PY -m pytest test_gen_culture_merges.py -q` (PASS) and `$PY scripts/generators/gen_culture_merges.py --check`. Expected: `culture merges: current`, exit 0. A stale file means the refactor changed output: fix the refactor, not the file.
- [ ] **Step 5: Commit** `scripts/generators/gen_culture_merges.py test_gen_culture_merges.py`.

### Task 2: The roster

**Files:**
- Create: `scripts/generators/assimilation_cultures_config.py`
- Create: `scripts/analysis/assimilation_cultures_roster.py`
- Test: `test_assimilation_cultures_config.py`

**Interfaces:**
- Consumes: `gen_culture_merges.load_vanilla() -> dict` (cultures by id, traits under `culture_merges_config.TRAITS_KEY`) and `gen_culture_merges.build_plan(cultures) -> list[Built]` (`Built.merge.result`, `Built.traits` with `.key`, `.kind`, `.group`, `Built.fields`).
- Produces, in `assimilation_cultures_config`:

```python
@dataclass(frozen=True)
class Language:
    key: str                 # trait key less "language_": "anglophone", "cm_latin"
    names_from: str          # culture whose name lists and religion the hybrids take
    word: str | None = None  # the hybrids' word for the language where vanilla's sounds bad

@dataclass(frozen=True)
class Group:
    key: str                 # group key less "heritage_group_": "african"
    heritage: str            # the heritage trait its hybrids carry
    looks_from: str          # culture whose ethnicities and graphics they take
    word: str | None = None

@dataclass(frozen=True)
class Pair:
    language: Language
    group: Group
    culture: str             # "hc_<language.key>_<group.key>"

COUNTED: tuple[Language, ...]   # 39
HAND: tuple[Language, ...]      # 20
GROUPS: tuple[Group, ...]       # 10
SENTINEL = "hc_anglophone_african"
def merge_languages(plan) -> tuple[Language, ...]             # one per Trait of kind "language"; names_from = that merge's result
def languages(plan) -> tuple[Language, ...]                   # COUNTED + HAND + merge_languages(plan)
def language_groups(language, cultures, plan) -> frozenset[str]  # heritage group keys of every culture speaking it, cm_ results included
def pairs(cultures, plan) -> tuple[Pair, ...]
def minted_heritages() -> tuple[tuple[str, str], ...]         # (trait key, group key) for every Group whose heritage starts "heritage_hc_"
def validate(cultures, plan) -> None                          # ValueError on any broken row
```

**The data.** `COUNTED`, key then `names_from`:
anglophone british; arabic maghrebi; berber berber; dutch dutch; east_slavic russian; eastern_romance romanian; francophone french; fulani fulbe; gaelic irish; germanophone north_german; hakka hakka; hausa hausa; hindustani hindustani; hispanophone spanish; hungarian hungarian; italian north_italian; japanese japanese; jurchenic manchu; korean korean; lusophone portuguese; magadhan bengali; malay javan; mandarin han; min min; northwestern_indic panjabi; occitano_romance occitan; oghuz turkish; pahari nepali; persian persian; scandinavian swedish; siamese thai; south_central telegu; southern_indic marathi; tamil_tulu tamil; tibetan tibetan; vietic vietnamese; west_slavic polish; western_indic rajput; yue yue.

`HAND`: greek greek; south_slavic serb; philippinic visayan; amharic amhara; burmic burmese; galla oromo; tigrinya tigray; somali somali; lacustrine_bantu lacustrine_bantu; equatorial_bantu equatorial_bantu; nguni nguni; swahili swahili; yoruba yoruba; quechuan quechua; guarani guarani; siouan siouan; akan akan; malagasy malagasy; mande mande; manding bambara.

`word` overrides (the owner reads every name in the PR; these are the starting list): jurchenic "Manchu"; oghuz "Turkic"; eastern_romance "Romanian"; vietic "Vietnamese"; siamese "Thai"; burmic "Burmese"; philippinic "Filipino"; galla "Oromo"; yue "Cantonese"; magadhan "Bengali"; south_central "Telugu"; tamil_tulu "Tamil"; pahari "Nepali"; southern_indic "Marathi"; northwestern_indic "Punjabi"; occitano_romance "Occitan"; quechuan "Quechua"; lacustrine_bantu "Great Lakes Bantu". No group has one.

`GROUPS`, key, heritage, `looks_from`: african `heritage_african_diaspora` hausa; central_asian `heritage_hc_central_asian` uzbek; east_asian `heritage_hc_east_asian` han; european `heritage_hc_european` north_german; indigenous_american `heritage_hc_indigenous_american` quechua; indigenous_oceanic `heritage_hc_indigenous_oceanic` melanesian; middle_eastern `heritage_hc_middle_eastern` maghrebi; north_asian `heritage_hc_north_asian` manchu; south_asian `heritage_hc_south_asian` bengali; southeast_asian `heritage_hc_southeast_asian` javan. (`looks_from` is the group's largest 1836 culture with one plain ethnicity; Turkish, the largest Middle Eastern one, mixes two.) No Promethean row.

`scripts/analysis/assimilation_cultures_roster.py` reproduces the counted list on a machine with the game: it reads `path_constants.base_game_path`'s `common/history/pops` and `common/country_definitions`, ranks languages by people ruled and by speakers, prints the union of the two top-30 lists with each language's largest culture, and exits 1 with a diff when that union is not `COUNTED`'s keys. It is not in CI.

- [ ] **Step 1: Write the failing tests** (`test_assimilation_cultures_config.py`, loading `cultures = gen.load_vanilla()` and `plan = gen.build_plan(cultures)` once):

```python
def test_the_roster_is_64_languages_and_584_cultures(self):
    self.assertEqual((len(cfg.COUNTED), len(cfg.HAND), len(cfg.merge_languages(plan))), (39, 20, 5))
    self.assertEqual(len(cfg.pairs(cultures, plan)), 584)

def test_a_pair_is_left_out_only_for_a_languages_one_group(self):
    made = {(p.language.key, p.group.key) for p in cfg.pairs(cultures, plan)}
    for language in cfg.languages(plan):
        own = cfg.language_groups(language, cultures, plan)
        for group in cfg.GROUPS:
            self.assertEqual((language.key, group.key) in made, not (own == {group.key}), (language.key, group.key))

def test_the_flagship_pairs_exist(self):
    keys = {p.culture for p in cfg.pairs(cultures, plan)}
    self.assertLessEqual({cfg.SENTINEL, "hc_anglophone_european", "hc_guarani_african", "hc_cm_latin_south_asian"}, keys)
    self.assertNotIn("hc_germanophone_european", keys)
    self.assertNotIn("hc_cm_latin_european", keys)

def test_every_reference_culture_fits_its_row(self):   # names_from speaks the language; looks_from is in the group
def test_no_hybrid_key_is_a_vanilla_or_merge_culture(self):
def test_no_promethean_group_and_ten_groups(self):
def test_only_the_african_group_reuses_a_vanilla_heritage(self):
def test_validate_rejects(self):   # a language vanilla lacks; names_from of another language; a duplicate key; a word holding a quote mark
```

- [ ] **Step 2: Run** `$PY -m pytest test_assimilation_cultures_config.py -q`. Expected: FAIL, no module `assimilation_cultures_config`.
- [ ] **Step 3: Write the config and the analysis script.**
- [ ] **Step 4: Run** the tests (PASS), then `python3 scripts/analysis/assimilation_cultures_roster.py` on this machine. Expected: exit 0. If a `names_from` above is not the language's largest culture in its output, keep the plan's value and say so in the report.
- [ ] **Step 5: Commit** the three files.

### Task 3: The generator and its registration

**Files:**
- Create: `scripts/generators/gen_assimilation_cultures.py`
- Create (generated): `common/cultures/te_hybrid_cultures.txt`, `common/discrimination_traits/te_hybrid_culture_traits.txt`, `common/static_modifiers/te_hybrid_culture_static_modifiers.txt`, `common/modifier_type_definitions/te_hybrid_culture_modifier_types.txt`, `common/scripted_effects/te_hybrid_cultures_generated_effects.txt`, `localization/english/te_hybrid_cultures_generated_l_english.yml`
- Modify: `server/post_load.py` (after `gen_culture_merges`, before `organize_loc`), `organize_loc.py` (a category `HYBRID_CULTURES_GENERATED` and its rule, beside `CULTURE_MERGES_GENERATED`'s), `docs/auto_generated_files.md` (six rows), `docs/guides/python_tools.md` (the regenerator roster), `scripts/nightly_audit_select.py` (the generated effects file, beside the `te_culture_merges_generated_*` lines)
- Delete: `scripts/generators/assimilation_cultures.py`; its row at `README.md:304`; `pop_culture_conversion_propotion_script_value` in `common/script_values/extra_script_values.txt`
- Test: `test_gen_assimilation_cultures.py`

**Interfaces:**
- Consumes: Task 1's functions; Task 2's `pairs`, `languages`, `minted_heritages`, `SENTINEL`.
- Produces:
  - `regenerate(mod_state=None, *, root=ROOT, dry_run=False) -> dict` with `changed` and `changed_files`, and a CLI with `--check` and `--dry-run`, as `gen_culture_merges` has.
  - `plan_outputs(root) -> dict[Path, str]`, one entry per generated file.
  - The scripted effect **`te_hcg_save_targets`** (state scope). It reads `scope:te_hc_host` (a culture). For the first roster language whose trait the host has (`scope:te_hc_host = { has_discrimination_trait = language_<key> }`) and whose first hybrid exists (`exists = cu:<that culture>`), it saves each of that language's hybrids as the temporary scope `te_hc_t_<group key>` and sets the local variable `te_hc_has_targets` to 1. One `if`, then `else_if`s, in roster order. It sets nothing otherwise.

**What each culture holds:** `language = language_<key>`; `heritage = <group.heritage>`; `religion`, `name_format` where present and every list in `gen_culture_merges.NAME_LISTS` from `names_from` (for a merge language, from that `Built.fields`); `graphics` and `ethnicities` from `looks_from`; `traditions = { }`; no obsessions, taboos or `assimilation_rate`; `color` the channel mean of the two reference cultures' colors as 0 to 255 integers (raise on a color form the reader does not know). A minted heritage trait is `{ type = heritage trait_group = heritage_group_<key> }`.

**Loc:** `hc_<l>_<g>` is `"<language part> <group part>"`, each part the override word or the spliced key (`$language_anglophone$ $heritage_group_african$`; `Turkic $heritage_group_european$`). `heritage_hc_<g>` is `"$heritage_group_<g>$ Diaspora"`. The six static modifiers' names come from `static_modifier_loc_for`. The `organize_loc` rule takes keys starting `hc_` or `heritage_hc_` ahead of the `_add`/`_mult` rule.

- [ ] **Step 1: Write the failing tests** (`test_gen_assimilation_cultures.py`):

```python
def test_one_culture_per_pair_with_its_two_traits(self):          # parse CULTURES_OUT's text with ParadoxFileParser; 584 keys; language and heritage per pair
def test_each_culture_has_the_nine_entries_the_engine_expects(self):   # gen_culture_merges.culture_static_modifier_keys / culture_modifier_types, all present
def test_nine_heritage_traits_are_minted_in_their_vanilla_groups(self):
def test_the_ladder_has_a_branch_per_language_in_roster_order(self):    # 64 branches
def test_a_branch_saves_every_hybrid_of_its_language_and_no_other(self):
def test_every_branch_is_guarded_by_exists_on_its_first_hybrid(self):   # Review Focus 1
def test_the_generated_script_names_no_culture_but_hc(self):            # every `cu:` token starts `cu:hc_`
def test_names_are_spliced_or_an_override_word(self):                   # no language's or group's vanilla display name is spelled
def test_colors_are_valid_and_differ_within_a_language(self):
def test_the_outputs_are_current(self):                                 # regenerate(dry_run=True)["changed"] is False
def test_organize_loc_files_every_generated_key_in_its_category(self):
def test_the_old_generator_and_its_value_are_gone(self):
```

- [ ] **Step 2: Run** `$PY -m pytest test_gen_assimilation_cultures.py -q`. Expected: FAIL, no module.
- [ ] **Step 3: Write the generator; run it** (`$PY scripts/generators/gen_assimilation_cultures.py`), then `python3 organize_loc.py`, then the generator's `--check` (exit 0: `organize_loc` must leave its loc file as written).
- [ ] **Step 4: Register and delete** as listed under Files.
- [ ] **Step 5: Run** `$PY -m pytest test_gen_assimilation_cultures.py test_assimilation_cultures_config.py test_gen_culture_merges.py test_culture_merge_mod_refs.py test_loc_coverage_audit.py -q`, `$PY scripts/analysis/check_post_load_rosters.py`, and `$PY scripts/preflight.py --only audits`. Expected: all pass. A `loc_coverage_audit` or `modifier_field_audit` flag on an `hc_` culture's modifier type means the audit knows only the `cm_` family: extend its culture list to read the mod's `common/cultures/`, with a test.
- [ ] **Step 6: Commit** the generator, its outputs, the registrations and deletions, by path.

### Task 4: The define, the rule, the two modifier types and the law lines

**Files:**
- Modify: `common/defines/extra_defines.txt:85`, `common/game_rules/extra_game_rules.txt` (append), `common/laws/te_bodily_autonomy_laws.txt` (four `modifier` blocks and the header comment), `common/laws/modified.txt` (`REPLACE:law_ethnostate`'s `modifier` block), `localization/english/te_game_rules_l_english.yml`, the modifier loc (`organize_loc` places the keys), `README.md` (the rules table)
- Create: `common/scripted_triggers/te_assimilation_culture_triggers.txt`, `common/modifier_type_definitions/te_assimilation_culture_modifier_types.txt`
- Test: `test_assimilation_cultures_rule.py`

**Interfaces:**
- Produces:
  - `te_hc_mode_hybrid = { has_game_rule = assimilation_cultures_hybrid exists = cu:hc_anglophone_african }` and `te_hc_mode_none = { has_game_rule = assimilation_cultures_none }` (any scope).
  - `country_cross_heritage_assimilation_add` (`percent = yes`, `decimals = 0`, `color = neutral`, `script_only = yes`) and `country_cross_heritage_assimilation_blocked_bool` (`boolean = yes`, `color = neutral`, `script_only = yes`).
  - Loc keys: `rule_assimilation_cultures_rule`; `setting_assimilation_cultures_<hybrid|unrestricted|none>` and each `_desc`; both modifier types and each `_desc`.

- [ ] **Step 1: Write the failing tests:**

```python
def test_the_define_requires_the_heritage_group(self):     # an uncommented `ALLOW_ASSIMILATION_REQUIRE_HERITAGE_GROUP = yes` in NPops; no ALLOW_ASSIMILATION_ACROSS_HERITAGES anywhere
def test_the_rule_has_three_settings_and_defaults_to_unrestricted(self):
def test_each_mode_trigger_is_a_positive_test_of_its_own_setting(self):   # no NOT; hybrid also asks exists = cu:<cfg.SENTINEL>
def test_no_other_file_reads_the_rule(self):                # `has_game_rule = assimilation_cultures_` appears only in te_assimilation_culture_triggers.txt
def test_the_law_lines(self):                               # {licensed: 0.5, morphological_freedom: 1, clade: 1, prescribed: 1}; natural form has no modifier block
def test_ancestral_citizenship_blocks_the_crossing(self):
def test_both_modifier_types_are_script_only_and_named(self):
```

- [ ] **Step 2: Run** `$PY -m pytest test_assimilation_cultures_rule.py -q`. Expected: FAIL.
- [ ] **Step 3: Write the script and the loc.** The setting descriptions say what the setting does and what a mid-game change does, inside `test_game_rule_desc_length.py`'s four lines. The `_add` type's description says it acts only under Hybrid Cultures and None. Update the Bodily Autonomy file's header for the new line.
- [ ] **Step 4: Run** `python3 organize_loc.py`, then `$PY -m pytest test_assimilation_cultures_rule.py test_game_rule_desc_length.py test_has_game_rule_targets.py test_rule_unlock_settings.py test_law_desc_length.py -q` and `$PY scripts/preflight.py --only audits`. Expected: pass.
- [ ] **Step 5: Commit** by path.

### Task 5: The pass

**Files:**
- Create: `common/on_actions/te_assimilation_culture_on_actions.txt`, `common/scripted_effects/te_assimilation_culture_effects.txt`, `common/script_values/te_assimilation_culture_values.txt`
- Modify: `common/scripted_triggers/te_assimilation_culture_triggers.txt`
- Test: `test_assimilation_cultures_values.py`, `test_assimilation_cultures_pass.py` (written by a subagent from this task's tables and the spec, without the script in front of it; the coordinator then runs them against the script and settles each disagreement by the spec)

**Interfaces:**
- Consumes: `te_hcg_save_targets` (Task 3); `te_hc_mode_hybrid`, `te_hc_mode_none`, the two modifier types (Task 4).
- Produces:
  - on_action `te_hc_yearly_on_action` on `on_yearly_pulse_country`, whose effect is `te_hc_yearly_country = yes`.
  - Effects: `te_hc_yearly_country` (country), `te_hc_state_pass` (state), `te_hc_pick_host` (state), `te_hc_find_locals` (state), `te_hc_convert_pop` (pop); helpers with arguments, each a single token: `te_hc_weigh_primary = { STATE OUT FLAG }` (culture), `te_hc_keep_local = { G }` (culture), `te_hc_language_step = { G }` (pop), `G` a heritage group key less `heritage_group_`; `te_hc_find_capital_host`, `te_hc_reset_locals`.
  - Triggers: `te_hc_state_has_other_group` (state), `te_hc_pop_taken` (pop), `te_hc_pop_status_allowed` (pop), `te_hc_speaks_host` (pop), `te_hc_culture_lives_in = { STATE }` (culture).
  - Values: `te_hc_monthly_rate = 0.002`, `te_hc_months = 12`, `te_hc_fervor_effect = 0.0075`, `te_hc_homeland_factor = 0.75`, `te_hc_rate_cap = 0.5`; `te_hc_pop_rate`, `te_hc_status_mult`, `te_hc_pop_size_floor` and `te_hc_one_person` (pop); `te_hc_cross_share` (country); and the two fractions a `change_pop_culture` is given, `te_hc_pop_step` (the rate) and `te_hc_pop_cross_step` (the rate times the owner's `te_hc_cross_share`), each floored at `te_hc_one_person` where above 0 and capped at 1 (review, 2026-11-25; until then `te_hc_small_pop = 50`, below which a pop converted whole).
  - Local variables, set in `te_hc_yearly_country` unless noted: `te_hc_mode` (1 Hybrid Cultures, 2 Unrestricted, 3 None), `te_hc_cross` (`te_hc_cross_share`), `te_hc_blocked` (1 when the bool reads yes), `te_hc_can` (0 where nothing can convert this year: mode 2 under a block, mode 3 under a block or with `te_hc_cross` 0; no state is walked then); per state `te_hc_has_host`, `te_hc_has_targets` and the ten `te_hc_has_local_<group>` (0 none, 1 shares a homeland with a primary culture, 2 its homeland is this state); per pop `te_hc_done` (1 once it took the language step).
  - Temporary scopes: `te_hc_owner`, `te_hc_state`, `te_hc_host`, `te_hc_capital_host`, `te_hc_l_<group>`, and Task 3's `te_hc_t_<group>`.

**The rules the script implements** (spec § The pass):

- `te_hc_yearly_country` does nothing for a country with no state. It walks the incorporated states (`is_incorporated = yes`) that pass `te_hc_state_has_other_group`: `any_scope_culture` with `NOT = { shares_heritage_trait_group_with_any_primary_culture = <owner> }`.
- `te_hc_state_pass` first sets `te_hc_has_host` and `te_hc_has_targets` to 0, then picks the host, then, under mode 1, calls `te_hcg_save_targets` and `te_hc_find_locals`, then walks the pops that pass `te_hc_pop_taken`.
- `te_hc_pick_host`: the owner's primary culture with the most people in the state. With one primary culture present, that one, with no pop walk. With several, each is counted by one pop walk (`total_size` into a local) and the largest kept. With none in the state, the capital's host by the same rule, worked out at most once per country per pass and kept in the temporary scope `te_hc_capital_host`; with none in the capital either, any primary culture.
- `te_hc_pop_taken`: the culture shares no heritage group with any primary culture of the owner; the state is not a homeland of the culture, or carries `state_allow_assimilation_in_homeland_bool`; `te_hc_pop_status_allowed`.
- `te_hc_pop_status_allowed`: the owner's `country_allow_assimilation_<status>_bool` for the pop's status, by `pop_acceptance` against vanilla's `acceptance_status_2` to `_5` (20, 40, 60, 80): `violent_hostility`, `cultural_erasure`, `open_prejudice`, `second_rate_citizen`, `full_acceptance`.
- `te_hc_pop_rate` = `te_hc_monthly_rate` × `te_hc_months` × max(0, 1 + `state.modifier:state_assimilation_mult`) × max(0, 1 + the owner's `country_assimilation_<status>_mult`) × (1 − `pop_radical_fraction`) × max(0, 1 − `te_hc_fervor_effect` × the culture's `culture_current_fervor`) × `te_hc_homeland_factor` in a homeland of the culture; 0 to `te_hc_rate_cap`.
- Where its fraction is above 0 at least one person converts (`te_hc_one_person`, the engine's `MIN_ASSIMILATION` once a year); a pop converts whole only when it is one person; a rate of 0 converts nobody, and `change_pop_culture` is not called (review, 2026-11-25).
- **The outcome table.** `speaks` is `te_hc_speaks_host` (`shares_language_trait_with_culture = scope:te_hc_host`); `slave` is `is_pop_type = slaves`.

| `te_hc_mode` | speaks | targets | Becomes | Fraction (`te_hc_pop_step` for rate, `te_hc_pop_cross_step` for rate × `te_hc_cross`) | Not when |
|---|---|---|---|---|---|
| 1 | no | any, local > 0 | `scope:te_hc_l_<the pop's heritage group>` | rate | never |
| 1 | no | 1, local 0 | `scope:te_hc_t_<the pop's heritage group>` | rate | never |
| 1 | no | 0, local 0 | `scope:te_hc_host` | rate × `te_hc_cross` | blocked, slave, `te_hc_cross` = 0 |
| 1 | yes | any | `scope:te_hc_host` | rate × `te_hc_cross` | blocked, slave, `te_hc_cross` = 0 |
| 2 | any | any | `scope:te_hc_host` | rate | blocked, slave |
| 3 | any | any | `scope:te_hc_host` | rate × `te_hc_cross` | blocked, slave, `te_hc_cross` = 0 |

Nothing converts while `te_hc_has_host` is 0. "local" is the local variable `te_hc_has_local_<group>` for the pop's heritage group.

- **The local culture** (spec § The pass, step 4). Under mode 1, after the host is picked, `te_hc_find_locals` (state scope) sets the ten locals `te_hc_has_local_<group>` to 0, then walks the owner's cultures (`every_scope_culture` on the country, which lists the cultures with people there) and, for each that shares no heritage group with any primary culture of the owner, speaks the host's language (`shares_language_trait_with_culture = scope:te_hc_host`) and belongs here, saves it as `te_hc_l_<its group>` and sets that group's local to 1. It belongs here when this state is one of its homelands, or the owner holds a state that is a homeland of both it and one of the owner's primary cultures. A culture whose homeland this state is replaces one saved before it for the same group; otherwise the first found is kept. The cheap trait tests come before the walk of the owner's states.

- [ ] **Step 1: The value tests** (`test_assimilation_cultures_values.py`; a Python twin `pop_rate(state_mult, status_mult=0, radicals=0, fervor=0, homeland=False)` built from the numbers the test reads out of the values file):

```python
def test_the_engine_figures(self):      # 0.002, 12, 0.0075, 0.75, 0.5 as bare `name = N` lines
def test_the_spec_rates(self):
    self.assertAlmostEqual(pop_rate(0), 0.024)
    self.assertAlmostEqual(pop_rate(1.0), 0.048)
    self.assertAlmostEqual(pop_rate(6.9), 0.1896)
    self.assertAlmostEqual(pop_rate(6.9 - 1), 0.1656)      # Morphological Freedom
    self.assertAlmostEqual(pop_rate(6.9 + 2), 0.2376)      # Prescribed Form
def test_a_sum_below_minus_one_gives_zero(self):            # pop_rate(1.0 - 3) == 0; Review Focus 3
def test_the_cap(self):                                     # pop_rate(40) == 0.5
def test_radicals_fervor_and_homeland(self):                # pop_rate(0, radicals=0.5) == 0.012; fervor=100 -> 0.006; homeland -> 0.018
def test_the_script_value_has_each_factor_and_both_clamps(self):   # the parsed te_hc_pop_rate block
def test_the_figures_match_the_defines(self):   # 0.0075 against the mod's CULTURAL_FERVOR_ASSIMILATIOM_EFFECT line, always; 0.002 and 0.75 against
                                                # vanilla's ASSIMILATION_RATE and ASSIMILATION_IN_HOMELAND_MULT, skipped where the game is not installed
```

- [ ] **Step 2: The pass tests** (`test_assimilation_cultures_pass.py`). An interpreter over the parsed `te_hc_convert_pop` (the `OpNode` / `parse_ops` pattern of `test_culture_merge_census.py`: `if`, `else_if`, `else`, `limit` over stubbed triggers and `local_var:` comparisons) run for every row of the outcome table crossed with blocked, slave and `te_hc_cross` in {0, 0.5, 1}; each asserts the target scope and the fraction's multiplier, or that nothing converts. And these shape tests:

```python
def test_the_pulse_is_the_yearly_country_one(self):
def test_the_pass_runs_under_every_setting(self):                 # te_hc_yearly_country has no rule test around its state walk
def test_host_and_target_flags_are_reset_before_anything_reads_them(self):   # Review Focus 2
def test_nothing_converts_without_a_host(self):
def test_the_taken_test_is_by_heritage_group_against_every_primary_culture(self):   # Review Focus 4
def test_a_pop_in_its_homeland_is_taken_only_with_the_state_bool(self):
def test_the_status_ladder_covers_five_statuses_at_vanillas_thresholds(self):
def test_a_state_without_a_primary_culture_takes_the_capitals_host(self):   # Review Focus 5
def test_only_incorporated_states_are_walked(self):                        # Review Focus 5
def test_a_small_pop_converts_whole_and_a_zero_rate_converts_nobody(self):   # te_hc_pop_step and te_hc_pop_cross_step
def test_a_local_culture_needs_people_language_group_and_a_shared_homeland(self):   # this state its homeland, or an owned state a homeland of it and of a primary culture
def test_local_flags_are_reset_in_every_state(self):                # Review Focus 2
def test_the_local_search_names_no_culture(self):
def test_the_pass_names_no_culture(self):                         # no `cu:` in the three hand-written files but the sentinel in the triggers file
def test_no_world_iterator(self):                                 # no every_state / any_state / every_country in the pass
```

- [ ] **Step 3: Run both files.** Expected: FAIL, the script files do not exist.
- [ ] **Step 4: Write the script** (the coordinator), each helper under a comment header that gives its scope, what it reads and what it sets.
- [ ] **Step 5: Run** both test files, `python3 scripts/format_paradox_tabs.py` on the new files, and `$PY scripts/preflight.py --only audits`. Expected: pass. For each effect, trigger or modifier read not already used in the mod, run `python3 scripts/lessons.py <name>` first.
- [ ] **Step 6: Commit** by path.

### Task 6: The self-checks and the play-test list

**Files:**
- Create: `common/scripted_effects/te_assimilation_culture_selfcheck_effects.txt`, `docs/testing/assimilation-cultures-playtest.md`
- Modify: `common/on_actions/te_assimilation_culture_on_actions.txt`, `common/scripted_effects/te_assimilation_culture_effects.txt` (one one-line hook)
- Test: `test_assimilation_cultures_selfchecks.py`

**Interfaces:**
- Produces two once-a-game lines, each behind a latch global `te_hc_chk_<name>_done`, in the form of `te_culture_merge_selfcheck_effects.txt` (values copied to globals and printed with `GetGlobalVariable`):

| Name | Hook | OK | Not judged (no line) |
|---|---|---|---|
| `hc_define_blocks` | the global monthly pulse, from 30 days into a game | at least one pop that shares a heritage group with a primary culture of its owner has `has_ongoing_assimilation`, at least one pop that shares none passes `te_hc_pop_taken` (`candidates`), and no pop that shares none has `has_ongoing_assimilation` | while no pop of the first kind is assimilating or there is no candidate; three pulses, then `NOT_JUDGED` |
| `hc_rate_inputs` | `te_hc_convert_pop`, a taken pop | from pop scope, `state.modifier:state_assimilation_mult` equals the owner's own sum of it (a state with no line of its own) where that is not 0, and the owner's `country_allow_assimilation_full_acceptance_bool` reads yes; BROKEN where the state's read is 0 or the switch doesn't read yes | an owner whose own sum is 0; a state with lines of its own (another pop is tried, 200 at most, then `NOT_JUDGED`) |

- [ ] **Step 1: Write the failing tests:** each name has an OK and a BROKEN `debug_log` line carrying its numbers; each sits behind its latch and sets it; each has the guard in its last column; the hooks are one call each; no check reads a variable before `has_variable`.
- [ ] **Step 2: Run** `$PY -m pytest test_assimilation_cultures_selfchecks.py -q`. Expected: FAIL.
- [ ] **Step 3: Write the checks and the play-test list.** The list has a Self-checks table (each line, what it means, the spec's fallback) and the rows of spec § Unverified, plus: whether the engine assimilates in an unincorporated state at all; the engine's `country_assimilation_delta_threshold_add`; a rule change mid-game in each direction; a 1.3.x save loaded on the build; Paraguay's first decade (Review Focus 4).
- [ ] **Step 4: Run** the tests and `$PY scripts/preflight.py --only audits`. Expected: pass.
- [ ] **Step 5: Commit** by path.

### Task 7: Docs and the player guide

**Files:**
- Create: `docs/systems/mod_systems/assimilation_cultures.md`
- Modify: `docs/systems/mod_systems.md` (index row and section list), `docs/systems/mod_systems/game_rules.md`, `docs/systems/mod_systems/social_movements.md` (the law table), `docs/systems/mod_systems/culture_merges.md` (one cross-reference under Compatibility), `docs/guides/scripting_best_practices.md` (three lessons), `docs/player_guide/01-introduction.md` (the rules table), `docs/player_guide/08-states.md` (a section after "Cultural acceptance and minorities"), `docs/player_guide/07-social-movements.md` (the laws' new line), `docs/player_guide/*.pdf` (rebuilt)

**Interfaces:**
- Consumes: the script as built. Every name and figure is read from it, not from this plan.

- [ ] **Step 1: The system doc**, in the form of `culture_merges.md`: what it is; the define; the cultures and the roster; the pass, with the outcome table; the rule's three settings, old saves and mid-game changes; the laws; Culture Merges; what Unrestricted gets wrong; the self-checks; the tests. Then the index row.
- [ ] **Step 2: The lessons**, each a `##` section whose heading states the rule: the heritage defines of 1.12 and what their comment says of the target; assimilation by acceptance status is a pair of country modifiers per status; `shares_heritage_trait_group_with_any_primary_culture` and its kin for a pop's heritage against a country.
- [ ] **Step 3: The player guide**, at the depth of its neighbors (`docs/player_guide/STYLE.md`): the rule's row; one section on heritage in assimilation, the three settings and what the Bodily Autonomy laws and Ancestral Citizenship do; the laws' line where their effects are given.
- [ ] **Step 4: Run** `$PY scripts/build_player_guide.py`, then `$PY -m pytest test_mod_systems_index.py -q` and `$PY scripts/preflight.py --only docs`. Expected: pass, the PDF rebuilt.
- [ ] **Step 5: Commit** the chapters and the PDF together, the other docs by path.

### Task 8: The gate and the pull request

- [ ] **Step 1: An independent review of the pass.** A fresh reviewer gets the spec, the three hand-written script files and the generated ladder, and is asked to break them: a pop converted to the wrong culture, a conversion under a law that forbids it, a read of an unset scope, a walk that runs more often than the plan says. Fix what holds; answer what does not.
- [ ] **Step 2: Run** `$PY scripts/preflight.py`. Expected: every check green. Reproduce a failure with `--only <check id>`.
- [ ] **Step 3: Write the PR body** to a file: what the system does; the owner's decisions, by date; the list of all 584 names for the read-through; the self-checks and the play-test list; "Player guide: 01-introduction, 07-social-movements, 08-states"; the attribution lines.
- [ ] **Step 4: Push and open the PR** against `main`. Do not merge it.
