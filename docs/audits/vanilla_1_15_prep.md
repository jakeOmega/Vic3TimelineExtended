# Vanilla 1.15 preparation (2026-10-22)

Vanilla 1.15 was due on 2026-10-22 and slipped to **2026-11-05**. Paradox has published modding notes for it; the owner pasted them on 2026-10-22. This doc reads those notes against the mod: what to check the day the patch ships, what has to change before the mod loads and works, and which new features are worth building. The general bump procedure is still `docs/guides/vanilla_patch_runbook.md`; this doc covers only what is specific to 1.15. After the migration, turn it into the migration record, as `vanilla_1_14_5_migration.md` was.

**Nothing here has been checked against 1.15 files.** Every statement about 1.15 behaviour comes from the notes and is a hypothesis until § 2's checks run. Every statement about the mod was read from `main` at `e5b54f1`.

## 1. Summary

| 1.15 change | What it does to the mod | Size | When |
|---|---|---|---|
| Journal entry outcomes replace `complete`/`on_complete`, `fail`/`on_fail`, `invalid`/`on_invalid`, `on_timeout` | **Breaks loading.** 25 of the mod's 28 entries and its 5 `REPLACE:` copies of vanilla entries use the old blocks | 58 outcomes, 45 of them in mod entries; 45 new `conclusion_desc` loc keys | Converter written before Nov 5; run on release day (§ 3.1) |
| Five vanilla journal entries the mod copies with `REPLACE:` | Vanilla rewrites them to outcomes; the mod's 1.14.5 copies would undo that and use dead syntax | 5 entries in 3 files; 1 test file | Release day (§ 3.2) |
| `double_sided_*` progress bar presets removed | **Breaks** the two banking tug-of-war bars; the `default_*` presets on the other six may go too | 8 bars | Release day (§ 3.3) |
| Journal entry panel reworked (outcomes, styled bars, map mode) | **Breaks silently.** `gui/journal_entry.gui` is a full copy of the 1.14 panel and calls the completion, failure and timeout tooltips and the bar-preset tests; `gui/te_system_tab_widgets.gui` copies the bar renderer | 2 GUI files; 28 widget files depend on the panel's containers | Release day (§ 3.4) |
| New syntax in the tooling's inputs | Audits read `complete`/`on_complete` etc. by name; some go blind, some flag false positives once entries use outcomes | See § 3.5 | Dual-shape support can land before Nov 5 |
| Journal entry map modes | **New.** Unblocks the six Demographics maps, the three Cartographic Survey maps (whose hijack is switched off) and the UN map | See § 4.1 | First feature after the migration |
| Journal entry scaling modifiers | **New.** About 137 modifiers re-added with a `multiplier` on a pulse could become declarations, and button-toggled policies could survive a revolution | See § 4.2 | After the migration |
| More than two outcomes per entry | **New.** Civil Rights and the Colonial Empire each already pick between eight endings inside `on_complete`/`on_fail`; the Space Race picks first vs. later | See § 4.3 | After the migration |
| Styled progress bars, script-value min/max | **New.** Native tug-of-war bars with a marker and end icons | See § 4.4 | After the migration |
| `send_interface_message` | **New.** The mod defines 294 message types; 79 are posted from one site, and 166 more are tech headlines posted through one effect | See § 4.5 | Low effort, any time after |
| `list_scopes` / `show_trigger_per_scope` on `any_*` triggers | **New.** Tooltips that name which states or countries are missing | See § 4.6 | Any time after |
| Regional exile pools | **New.** Fits the ICC's convictions, a deposed religious leader, Penal Labor Camps | See § 4.7 | Optional |
| Glossary | **New.** Few candidates; the mod's concepts are almost all mechanics | See § 4.8 | Optional |
| `play_music_cue` | **New.** Vanilla cues only, unless the mod ships music | See § 4.9 | Optional |
| Regnal numbers | Nothing to change: all 12 mod government types are non-hereditary | See § 4.10 | Check only |

## 2. Release-day checks

Run these before converting anything. Each is a question the notes don't answer and the conversion or a feature depends on. Record each answer here, with the file and line it came from.

Vanilla ships a reference `.md` beside several of the new databases: `common/scripted_progress_bars/scripted_progress_bars.md`, `common/regional_exile_pools/regional_exile_pools.md`, `common/glossary/glossary.md`, and `country_definitions.md`. Read those first, then vanilla's own converted journal entries (`common/journal_entries/*.txt`) and the new `gui/journal_entry.gui`.

**C1. Does the old syntax still load?** Launch 1.15 with the mod unconverted and read `debug.log` (log-triage skill) for `Unexpected token` on `complete`, `on_complete`, `fail`, `on_fail`, `invalid`, `on_invalid`, `on_timeout`, the four `custom_*_header` fields, the `event_outcome_*` fields and `double_sided_gold`. If vanilla kept a compatibility path, § 3.1 can be done carefully rather than on the day; if not, every mod journal entry is broken until it's done.

**C2. How vanilla converted its own entries.** Read a dozen converted vanilla entries for:
- the order of outcomes: success first or failure first, and where the hidden invalid outcome goes;
- where the old `custom_completion_header` / `custom_failure_header` / `custom_on_completion_header` / `custom_on_failure_header` went (presumably `header` / `effect_header`; seven Space Race entries set all four, and an eighth sets the two completion ones);
- where `event_outcome_completed_desc`, `event_outcome_failed_desc`, `event_outcome_timeout_desc`, `event_outcome_completed_effect_desc` and `event_outcome_failed_effect_desc` went (presumably into each outcome's `event_outcome_desc` / `event_outcome_effect_desc`; the Space Race has 22, the tax code's vanilla copies 6);
- whether `event_outcome_activated_effect_desc` still exists at entry level (the notes don't mention it; the UN entry uses it 5 times, `je_united_nations.txt:557-589`);
- whether `je_standard_completion_header`, `je_standard_failure_header`, `je_standard_on_completion_header` and `je_standard_on_failure_header` exist as loc keys;
- what vanilla wrote for `conclusion_desc` (length and voice), since the mod needs 45;
- what an entry with **no** outcomes looks like in the panel. Five mod entries never conclude (`complete = { always = no }`: Covert Warfare, Cultural Hegemony, Global Warming, Nuclear Program, United Nations).

**C3. Precedence.** When two outcome triggers become true on the same tick, which wins: declaration order, or something else? The Space Race can complete and fail together, and so can the four social-movement entries that have complete, fail and timeout. Find 1.14's order and keep it.

**C4. The panel's data functions.** In vanilla's new `gui/journal_entry.gui`:
- Are `JournalEntry.GetCompletionTooltip`, `GetFailureTooltip`, `GetOnCompleteTooltip`, `GetOnFailTooltip`, `GetTimeoutTooltip`, `GetOnTimeoutTooltip`, `CanComplete` and `CanTimeOut` gone? The mod's copy calls all of them. GUI errors aren't logged, so a removed function shows only as a blank section.
- What datamodel lists the outcomes, and which functions draw an outcome's header, colour, trigger tooltip and effect tooltip?
- Do `custom_widget_container_1` … `_7` and `custom_widget_container_je_icon` still exist, in the same places? The mod's 28 widget files under `gui/journal_entry_widgets/` mount into them, and a missing container hides the widget with no error.
- How does the panel turn the map mode on: automatically, or with an `onshow`/data function that another panel could call too (C6)?

**C5. Progress bars.** In `scripted_progress_bars.md`:
- Are `default_green` and `default_bad` gone with `double_sided_*`? Six mod bars use them.
- Which fields reproduce `double_sided_gold` (two mod bars)?
- Which data functions replaced `ScriptedProgressBar.IsDoubleSidedGold`, `IsDoubleSidedBad`, `IsDoubleSidedSpain`, `IsDoubleSidedRyukyu`, `IsDefault`, `IsDefaultGreen` and `IsDefaultBad`? `gui/journal_entry.gui` and `gui/te_system_tab_widgets.gui` branch on them.
- In which scope does a script-value `min_value` / `max_value` run (the owner, or the journal entry)? Can it read the owner's variables?

**C6. Map modes.** Everything § 4.1 depends on:
- Which scopes `map_color` and `map_tooltip` can reach besides the state root: the journal entry's owner, the viewing player, `scope:journal_entry`, scopes saved on the entry? A map of *the player's* data (their covert targets, their colonies) needs the owner; a world map (temperature, GDP per capita) needs only the state.
- Whether `map_color` takes `if`/`else` or only the three forms in the notes. One map per entry means a selector (§ 4.1) has to switch either the colours or the factor.
- When it's evaluated: each frame, on opening, daily? Mod maps must read cached variables, never walk pops.
- Whether it shows while the entry is **inactive** but shown (`is_shown_when_inactive`).
- Whether only the journal entry panel triggers it, or also a vanilla panel tab that shows the entry's content through `GetPlayerJournalEntry`. Banking, Cultural Hegemony, the UN, Climate, the Strategic Reserve, Nuclear, Covert Warfare and Demographics live in such tabs (`budget_panel`, `culture_panel`, `diplomatic_overview`, `market_panel`, `panel_military`, `pops_overview`, `states_panel`), and the Space Race, Grand Monuments, the Colonial Empire and the Seabed in the Timeline Extended window. If only the journal panel paints the map, a player using those tabs never sees it.
- How water, wasteland, unowned and decentralized states are drawn, and whether there's a legend.

**C7. Scaling modifiers.** Everything § 4.2 depends on:
- Scope of `value`: owning country or journal entry? The mod's `je_multiplier_scope_audit` exists because a `je:` modifier's stored multiplier is evaluated in journal-entry scope, where country-only reads return `none`.
- How often `value` is re-evaluated.
- Whether one entry can carry several, and whether the same modifier can sit in both `modifiers_while_active` and `scaling_modifiers_while_active`.
- Whether a value of 0 hides the modifier from the panel and the country's modifier list, or shows a row of zeros. § 4.2's policy switches depend on 0 hiding it.
- Whether a negative value works.
- Whether `modifier:X` reads see it the same day.
- Whether a revolution's winner gets it back with the inherited entry. Test with the civil-war harness (`docs/audits/civil_war_inheritance_audit.md`; `scripts/analysis/save_country_probe.py --diff`).

**C8. `send_interface_message`.** Who sees it (only the scoped country? does it no-op for the AI?), whether `title`/`desc` take saved scopes (`[SCOPE.sCountry('x').GetName]`), whether it reaches the message log as well as the toast, and whether a player can mute it. Message types can be muted in the message settings, and the mod's 289 types rely on that.

**C9. Regional exile pools.** What `has_access = { always = no }` does (a pool nobody can invite from, which is what a prison is); whether `years`/`months` run while the home country no longer exists; whether a character in a regional pool still counts for vanilla's exile checks and the agitator pool.

**C10. `list_scopes`.** Whether it survives inside `custom_tooltip = { text = … <triggers> }`. The mod wraps many player-facing conditions that way, which would hide the list.

**C11. Names.** Open the mod's GUI overrides that show character names (`Character.GetFullNameNoFormatting` ×10, `GetFullName` ×2) and check a monarch reads "Edward VII" once, not twice and not without the numeral. Check the Heir Education panel, which shows heirs.

**C12. Glossary links.** How loc links a glossary entry (`[glossary_x]`? a `Glossary(…)` function?), and whether `concept_reference_audit` then flags it as a missing concept.

**C13. The rest of the patch.** These notes cover only the new modding features. The runbook still applies in full: Modding-Digests `1.15.0/changes_breaking.md` and `changes_script_docs.md` (§ 3), the modifier-type-definition diff, the at-risk GUI loop (§ 5), the `REPLACE:`/`INJECT:` sweep, the vanilla constants the mod mirrors (§ 6b), and old-save repairs to retire at "vanilla 1.15" (§ 6a: `test_old_save_repairs.py` names them once `vanilla_parsed/` is rebuilt).

**C14. Saves.** Load a 1.14.5 save with active and concluded mod entries on 1.15 with the converted mod. Do concluded entries stay concluded and active ones keep their bars? Most systems keep their state in variables (`sr_completed_*`, `civil_rights_resolved`, `colonial_empire_completed`), which should hold either way; vanilla's entry records are the unknown.

## 3. What has to change

### 3.1 Mod journal entries to outcomes

The conversion is mechanical, and should be done by one script so the 25 entries that use the old blocks come out the same way. Write it before Nov 5 as a one-shot under `scripts/generators/` with a test over the current files, review its dry-run output, and run it on release day once C1–C3 confirm the shape. Redesigns (§ 4.3) are a separate step after it: convert first, so the diff of each redesign is readable.

The mapping, pending C2:

| Old | New outcome |
|---|---|
| `complete = { T }` + `on_complete = { E }` | `outcome = { header = je_standard_completion_header effect_header = je_standard_on_completion_header conclusion_desc = <je>_completed_desc color = "gold_positive" trigger = { T } effect = { E } }` |
| `fail = { T }` + `on_fail = { E }` | the same with `je_standard_failure_header`, `je_standard_on_failure_header`, `<je>_failed_desc`, `color = "blue_negative"` |
| `invalid = { T }` + `on_invalid = { E }` | `outcome = { flags = { hidden invalid_outcome } conclusion_desc = <je>_invalid_desc trigger = { T } effect = { E } }` |
| `timeout = N` + `on_timeout = { E }` | `timeout = N` stays; `outcome = { flags = { timeout } header = … effect_header = … conclusion_desc = <je>_timeout_desc effect = { E } }`, with no trigger |
| `complete = { always = no }` | dropped: the entry has no outcomes. Covert Warfare, Cultural Hegemony, Global Warming, the UN, and Nuclear Program, whose `on_complete` (`je_nuclear_program.txt:178`) can never run and goes too |
| `custom_completion_header` etc. | the matching outcome's `header` / `effect_header` (C2) |
| `event_outcome_*_desc`, `event_outcome_*_effect_desc` | the matching outcome's `event_outcome_desc` / `event_outcome_effect_desc` (C2) |

What each entry becomes (H = hidden invalid outcome, T = timeout outcome):

| File | Entry | Outcomes |
|---|---|---|
| `je_civil_rights.txt` | `je_civil_rights` | complete, fail, H (with effect) |
| `je_colonial_empire.txt` | `je_colonial_empire` | complete, fail |
| `je_digital_rights.txt` | `je_digital_rights` | complete, fail, H, T (5475 days) |
| `je_grand_monuments.txt` | `je_grand_monuments` | H |
| `je_heir_education.txt` | `je_heir_education` | complete, H (with effect), T (6570 days) |
| `je_human_augmentation.txt` | `je_human_augmentation` | complete, fail, H, T (7300 days) |
| `je_mental_health.txt` | `je_mental_health_crisis` | complete, fail, H, T (7300 days) |
| `je_post_scarcity.txt` | `je_post_scarcity` | complete, fail, H, T (10950 days) |
| `je_space_race.txt` | suborbital, orbital, moon landing, probe, moon base, Mars landing, interstellar probe | complete, fail (×7) |
| `je_space_race.txt` | `je_space_race_interstellar_results` | complete |
| `je_space_race.txt` | `je_space_race_solar_colonization` | fail (its `complete` is `always = no`, so its `on_complete` can't run and goes) |
| `timeline_extended_journal_entries.txt` | `je_state_collapse`, `je_create_new_religion` | complete (no effect) |
| `world_war_je.txt` | `je_world_war` | complete, fail |
| `je_banking.txt`, `je_strategic_reserve.txt`, `je_tax_code.txt` | three entries | none today; nothing to convert |
| `je_covert_warfare.txt`, `je_cultural_hegemony.txt`, `je_global_warming.txt`, `je_nuclear_program.txt`, `je_united_nations.txt` | five entries | none (`always = no` dropped) |

That is 45 outcomes in mod entries (38 shown, 7 hidden), each needing a `conclusion_desc` key. The text is the flavour shown on a concluded entry, so it can be drafted before Nov 5 and dropped in with the converter. Put the keys beside each entry's existing `_desc`/`_reason` keys and run `organize_loc.py`, which files by key shape: check where it puts `_completed_desc`, `_failed_desc`, `_timeout_desc` and `_invalid_desc` before writing 45 of them.

After converting: `format_paradox_tabs.py` on every touched file, the full suite, every `--strict` audit, `POST /reload` and its `warnings`, then the in-game check that every entry's panel opens, lists its outcomes and runs each effect. Use the debug harnesses that force an ending where they exist. The tests that cut old blocks out by name (§ 3.5) are rewritten in the same change.

### 3.2 The five vanilla journal entries the mod replaces

`REPLACE:` restates a whole entry, so each copy holds vanilla 1.14.5's text in the old syntax. Each has to be rebuilt as vanilla 1.15's entry plus the mod's own lines, not converted from the old copy:

| Entry | File | The mod's lines | Where they go in 1.15 |
|---|---|---|---|
| `je_great_reforms_bureaucratic` | `te_tax_vanilla_je_overrides.txt` | the tax code's `trigger_if` in `complete` | the success outcome's `trigger` |
| `je_imperialism_of_promise` | same | same | same |
| `je_portugal_regeneration` | same | same | same |
| `je_opium` | `te_vanilla_opium.txt` | three `game_date` checks; `on_fail` setting `opium_je_done` | `possible`/`is_shown_when_inactive`, the failure outcome's `trigger` and `effect` |
| `je_unite_the_nations` | `te_vanilla_turtle_island.txt` | three `te_is_north_american_capable_union` checks, one in `invalid` | the hidden invalid outcome's `trigger` |

`test_tax_code_bypass.py` (around line 784) compares each tax entry with `vanilla_parsed/` everywhere but `complete`, and checks the taxation OR inside `complete`. Both tests key on `complete` and need rewriting for the success outcome's `trigger`. The opium and Turtle Island headers say "re-diff on every Vic3 patch" and have no test; consider giving them one like the tax code's.

### 3.3 Scripted progress bars

| Bar | File | Preset |
|---|---|---|
| `banking_cycle_momentum_bar` | `extra_progress_bars.txt:12` | `double_sided_gold` (−5…5) |
| `banking_policy_stance_bar` | `extra_progress_bars.txt:29` | `double_sided_gold` (−2…2) |
| `banking_cycle_value_bar` | `extra_progress_bars.txt:1` | `default_green` |
| `banking_bubble_pressure_bar` | `extra_progress_bars.txt:41` | `default_bad` |
| `colonial_stability_bar` | `extra_progress_bars.txt:52` | `default_green` |
| `civil_rights_support_bar` | `extra_progress_bars.txt:229` | `default_green` |
| `heir_education_progress_bar` | `heir_education_progress_bars.txt:1` | `default_green` |
| `un_authority_bar` | `un_progress_bars.txt:1` | `default_green` |

The two double-sided bars need the new fields (textures, `marker = yes`) however C5 answers. The other six change only if the `default_*` presets went too.

### 3.4 GUI

- **`gui/journal_entry.gui`** is a full copy of vanilla's 1.14 panel (its first line still reads `# COPY-PASTED FOR NOW`). The mod's own change is small: the bars-on-top marker (`custom_widget_container_7`) hides the scripted-bar block (`:249-251`) and the goal bar (`:675-677`) for an entry that draws its own. Rebuild it as vanilla 1.15's file plus those two hunks, the runbook § 5 way ("the vanilla file with the mod's own hunks re-applied"), not as a 3-way merge: 1.15 rewrites the parts the copy depends on, and a merge would keep stale 1.14 sections. If 1.15 lets an entry hide its own goal bar or style it, check whether the override can go altogether.
- **`gui/te_system_tab_widgets.gui`** copies vanilla's bar renderer into `te_je_scripted_bars` (`:15`, branching on `IsDefaultBad`, `IsDefaultGreen`, `IsDoubleSidedGold` at `:26/44/63`) and the goal bar into `te_je_goal_bar` (`:136`). Re-copy both from vanilla 1.15's renderer. Users: `banking_dashboard_widget.gui`, `un_overview_widget.gui`, `panel_military.gui`.
- **Widget mounts.** If C4 finds a container renamed or moved, every `widget = { … container = "custom_widget_container_N" }` in `common/journal_entries/` follows, and so does the container table in `gui_modding_guide.md` § journal-entry widgets.
- **The other 26 same-path overrides** go through runbook § 5 as usual. 1.15 is a major release, so expect most of them at risk.
- `scripts/analysis/check_gui_lint.py` warns on markup no mod `.gui` has used before. The rebuilt panel will use new 1.15 functions, so expect warnings there that are correct.

### 3.5 Python tooling

From a read of the tools on 2026-10-22. None of the 29 CI audits looks a completion block up by name in a way that fails once entries use outcomes. The job that goes red on conversion day is the **unittest suite**. Most of the work below can land before Nov 5 if each tool accepts both shapes.

**Breaks:**

| Where | Why | Fix |
|---|---|---|
| `test_tax_code_bypass.py:783-819` | Reads `vanilla_parsed/…/journal_entries.json`'s `complete` and diffs the rest of each entry | Fails with a `KeyError` as soon as `vanilla_parsed/` is rebuilt on 1.15, before the mod changes at all. Rewrite against the success outcome (§ 3.2) |
| `test_civil_rights_inheritance.py:77,82,133,141,422`, `test_civil_rights_buttons.py:161`, `test_colonial_empire_layout.py:619,666`, `test_covert_tradecraft.py:191`, `test_grand_monument_registry.py:842,2351`, `test_launch_windows.py:533` | Cut `on_complete`, `on_fail`, `on_invalid`, `on_timeout`, `invalid` or `complete = {` out of an entry by name | Fail once the entries are converted. Each needs a helper that finds an outcome by its flags or header. A shared one in a test utility beats seven copies |
| `effect_trigger_validity_audit.py` (not in CI; feeds `POST /reload` warnings and `GET /scripted-helpers/unresolved`) | Checks every left-hand key against the frozen catalog `docs/engine/effect_trigger_valid_keys.txt` plus per-root extras. `outcome`, `conclusion_desc`, `effect_header`, `effect_all_involved`, `event_outcome_desc`, `event_outcome_effect_desc`, `map_color`, `map_color_second`, `map_tooltip`, `lerp`, `min_color`, `max_color`, `scaling_modifiers_while_active`, the new bar fields, `send_interface_message`, `play_music_cue`, `exile_pool`, `list_scopes`, `show_trigger_per_scope` and the two exile triggers are in neither | Every one is reported as an unresolved helper call. Re-bootstrap the catalog from the 1.15 engine docs (runbook § 4) and add the entry and bar fields to the roots' extras |
| `localization_accessor_audit.py` (not in CI) | Character accessors come from fixed tables and `event_targets_summary.txt` | `GetRegnalNumber` / `GetRegnalNumeral` flag as invalid until `fold_vanilla_loc_accessors.py` runs on 1.15 (runbook § 4) |

**Goes blind** (keeps passing, stops checking something):

- `effect_trigger_validity_audit.py:134-142` hard-codes `complete`, `fail`, `invalid`, the four `on_*` blocks, the four `custom_*_header` fields and the `event_outcome_*_effect_desc` fields as valid in journal entries, and `:196` hard-codes `default_green`, `default_bad` and `double_sided_gold` for bars. A leftover old field or preset never flags, even after a re-bootstrap. This is the class of bug the audit exists to catch (#295). Remove them from the extras when the mod no longer uses them.
- `script_loc_reference_audit.py:39-55` checks `header`, `title` and `desc` (so an outcome's `header` and an interface message's title and desc), but not `effect_header` or `conclusion_desc`. Add both, or a missing `conclusion_desc` passes `--strict`.
- `event_context_audit.py:314-327` doesn't list `outcome`, `effect_all_involved`, `event_outcome_effect_desc`, `map_tooltip` or `send_interface_message` as control keys, so it counts each as a scope switch. A `trigger_event` inside `map_tooltip` (which never runs) would count as a real dispatch, and one wrapped in `send_interface_message` inside an option could go from chosen to unchosen and raise `unchosen_self_action`. `/event-dispatch` in `mod_state_server.py` shares the labels.
- `concept_reference_audit.py:61` only matches `[concept_…]`, so `[glossary_x]` passes unchecked, while `Concept('glossary_x', …)` and `check_gui_lint.py:254-256` would call it an unregistered concept (C12).
- `scripts/analysis/vanilla_patch_diff.py` will show every vanilla entry as changed (the schema moved), and `--mod-uses` greps only removed entity and doc-section names, so it won't point at the mod's old blocks. The counts are 23 `on_complete`, 19 `on_fail`, 6 `on_timeout` and 2 `on_invalid` blocks.
- `test_tax_code_layout.py:461` asserts the tax code entry has no completion blocks, and `test_strategic_reserve_lifecycle.py:60-61` asserts it has no `invalid`; neither would notice an `outcome`.

**Should learn the new features:**

- `mod_state.VANILLA_COMMON_DIRS` (`mod_state.py:114-171`), the mod-side directory map in `mod_state_server.py:136-196` and `vanilla_parsed.py`: add `glossary` and `regional_exile_pools`, so lookups, loc coverage and the patch diff see them. Vanilla's `scripted_progress_bars` aren't snapshotted either.
- `loc_coverage_audit.py`: a Glossary category (`glossary_x`, `glossary_x_desc`), an exile-pool one (the pool's name), and a structural check that every outcome has `conclusion_desc` and every non-hidden one `header` and `effect_header`. No tool checks that today. `LOC_KEY_FAMILIES["Journal Entries"]` (`mod_state_server.py:216`, pinned by `test_mod_state_server_endpoints.py:138-143`) gains the outcome keys.
- `je_multiplier_scope_audit.py` scans `add_modifier` multipliers under `je:` links only. If § 4.2 moves modifiers into `scaling_modifiers_while_active`, it must scan that `value` in whatever scope C7 finds.
- `paradox_file_parser.py` merges same-named fields on `INJECT:`, so `INJECT:je_x = { outcome = { … } }` would merge into vanilla's outcome instead of adding one. Latent: the mod only `REPLACE:`s entries today. How the engine itself treats an injected `outcome` is a question for C2.
- `test_un_state_mirror.py:110` `DISPLAY_ONLY_BLOCKS` gains `event_outcome_effect_desc` and `map_tooltip`; `iterator_limit_audit.py`'s `ITERATOR_PROPERTY_KEYS` gains `list_scopes` and `show_trigger_per_scope`; `/placeholder-icons` (`mod_state_server.py:3184-3211`) learns the bar textures and end icons.

**Unaffected:** `orphaned_event_audit` (a text scan of every `ns.N` token, so an event fired from an outcome still counts), `je_immediate_reset_audit`, `empty_effect_audit`, `silent_variable_audit`, `script_argument_audit`, `prev_scope_audit`, `duplicate_key_audit`, `any_limit_audit`, `gui_reference_audit`, `gen_event_inventory.py`, `organize_loc.py`, and the `/journal-entries` endpoint, which returns the raw entry. No generator writes journal entry completion blocks.

`CLAUDE.md` lists 28 CI audits; `ci.yml` runs 29 (`je_multiplier_scope_audit --strict` is the one missing from the list).

### 3.6 Docs, guide and metadata

- `.metadata/metadata.json`: `supported_game_version` → 1.15.x.
- `docs/guides/vanilla_patch_runbook.md`: add the outcome conversion to the rename table (old blocks → outcome) and to the symptoms cheat sheet (`Unexpected token: on_complete`).
- `CLAUDE.md` and `docs/guides/scripting_best_practices.md`: wherever they name `complete`, `on_complete`, `fail`, `on_fail`, `on_timeout` or `invalid` (the civil-war rules talk about "completed entries"), and the dynamic-modifier pattern once § 4.2 is decided.
- `docs/systems/journal_entry_systems.md` (CRLF: edit with `Edit` or `sed`, not a Python rewrite): each entry's "Outcomes", "Resolution" or "Never Completes" section.
- `docs/guides/gui_modding_guide.md` (CRLF too): gotchas #14, #17, #21 and #33 cite `journal_entry.gui` line numbers; the widget container table.
- `docs/vanilla/CLAUDE.md` and the reference primers where they describe journal entries.
- Player guide: no mechanic changes from the conversion alone, but the panel looks different. Check the chapters that describe how an entry ends (`07-social-movements.md`, `12-decolonization.md`, `16-space.md`, `18-appendix-social-movements.md`) and any screenshot of a journal entry panel under `images/`.

## 4. Features worth building

Ranked by value to the mod. None should start before § 3 is done and C6–C10 are answered.

### 4.1 Journal entry map modes

The mod has designed maps it couldn't build. Its one mechanism, the Cartographic Survey, overwrites each state's Migration Attraction so vanilla's map mode paints the mod's metric. It has been switched off since it was written, because state-scope `migration_pull` returns the country's value and the map comes out flat (`common/decisions/extra_decisions.txt:95-111`). The Demographics spec's six maps (`docs/superpowers/specs/2026-10-08-demographics-design.md:1101-1104`) and the UN's map (`docs/systems/un_redesign_design.md:2076`, `:3565`) wait on it. A journal entry map paints from script directly, so all of them become buildable, depending on C6.

Candidates, best first. "Per state" data is kept on the state; "per country" data paints every state of a country the same, which still makes a world comparison map.

| Map | Data the mod already keeps | Host entry |
|---|---|---|
| **Demographics**: median age, fertility, life expectancy, Gini, Wealth Concentration, metropolitan share; also migration rate and dependency ratio | Per state, written once a year by the census walk: `te_dg_median`, `te_dg_tfr`, `te_dg_e0` (`te_demog_effects.txt`), `te_dg_gini` (`te_demog_generated_effects.txt:6578`), `te_dg_wc` (`te_demog_wealth_effects.txt`, set under every rule), `te_dg_mt` (`te_demog_metro_effects.txt:35`), `te_dg_mig_rate`, `te_dg_dependency`; the primate city is marked by `te_dg_primate_of` | **None.** Demographics is a game rule shown in the Population panel and the state panel. It needs an entry of its own (only under the rule) or a tab that can trigger the map (C6). The spec's blocker changes from "no per-state source" to "no host entry" |
| **United Nations**: missions and food relief, members striped | Per state: `un_msn_here` (the mission, tagged peacekeeping, aid, stabilisation or electoral) and `un_msn_power` (`un_mission_effects.txt:1023-1052`), `un_fr_relief_power` (`un_economy_effects.txt:673-686`). Per country: `un_member_modifier_on` (`un_state_effects.txt:204`), `un_standing`, the sanctions modifier | `je_united_nations` |
| **Nuclear**: who holds weapons, where strikes and accidents fell | Per country: `nuclear_weapon_stockpile`. Per state: the decaying `nuclear_strike_aftermath` modifier and `nuclear_strike_killed_population` (`extra_effects.txt:494-502`), `nd_weapons_accident_contamination` | `je_nuclear_program` |
| **Global Warming**: emissions, climate policy | Per country: the January market snapshot `owner.gw_market_emis_raw` (the survey's own source) and the policy modifiers on the entry. The per-state `gw_state_greenhouse_gas_emissions` walks every pop twice (`household_emissions_values.txt:36-48`), so it's too costly for a map. There is no per-state climate damage | `je_global_warming` |
| **Colonial Empire**: which colonies could be released | Per state: `is_decolonization_eligible_state` (`colonial_empire_triggers.txt:399`), `is_overseas_colonial_state`, `colonial_assimilation_disruption_modifier` | `je_colonial_empire` |
| **Banking**: the cycle and monetary regimes | Per country: `finance_cycle_value` 0–100, `te_mon_regime`, the currency union and board modifiers | `je_banking_cycle` (every country holds it) |
| **Cultural Hegemony**: influence tiers, exported models | Per country: `ch_tier` 0–5, `ch_model` 1–15 (named colours suit it) | `je_cultural_hegemony` |
| **Grand Monuments**: grandeur | Per state: `gm_state_grandeur`, the `gm_local_*` modifiers | `je_grand_monuments` (only while the country owns a monument) |
| **Tourism, GDP per capita**: the survey's other two metrics | Per state: the tourism script values (`base_tourism_appeal_value`, a branch over about 700 states; `total_tourism_output_bonus_percent`), the engine's `gdp_per_capita` | None obvious; could share the Demographics host's selector |
| **Covert Warfare**: the player's networks abroad | Per target, but stored on the operator (`iw_net_strength` in the `iw_nets` containers, `covert_warfare_effects.txt:683`), so it needs the owner in scope | `je_covert_warfare`, only if C6 gives the owner |

Not worth a map today: the Strategic Reserve (only the hub's state), the Space Race (launch sites are per celestial body), Civil Rights (low-acceptance states are a live pop walk, with nothing cached), the Seabed (sea, and no entry).

Design notes for whichever is built first:
- **One map per entry.** Demographics alone wants six metrics, so a selector is needed: a variable on the owner set by a scripted GUI button, read by `map_color`'s factor, if C6 shows `map_color` can reach the owner. If it can't, one entry per metric is the fallback, and too many entries for Demographics.
- **Cheap reads only.** Read a stored variable or modifier, never walk pops, until C6 says how often the map is evaluated (`docs/audits/late_game_performance.md`).
- **Fixed scales.** Normalise the `lerp` factor to 0–1 against fixed bounds (life expectancy 20–85), not this year's world range, so a colour means the same thing in 1850 and 1950. Clamp it.
- **The tooltip carries the number.** `map_tooltip` with `custom_tooltip_no_bullet` naming the state's value and, for a striped map, what the stripe means. The loc rules and audits apply as they do to any loc.
- **Retire the survey** once one map works: `te_map_mode_script_values.txt`, `te_map_modes_effects.txt`, `te_map_modes_triggers.txt`, `te_map_mode_modifiers.txt`, `events/te_map_modes_events.txt`, the decision at `extra_decisions.txt:319` with its disabled-comment block, and their loc.
- **The player guide** gains a line where each system's chapter describes its panel.

### 4.2 Scaling modifiers

Two different uses, both depending on C7.

**Replacing the pulse re-adds.** Today a scaled modifier is removed and re-added with a `multiplier` on a pulse (CLAUDE.md's dynamic-modifier pattern), and a missed removal stacks it. `je_global_warming.txt:156-168` is the shape: each month it removes `global_warming` and re-adds it with `multiplier = temperature_anomaly_display`, or removes it below 0.01. As `scaling_modifiers_while_active = { modifier = global_warming value = temperature_anomaly_display }` it needs no pulse and no removal, can't stack, and has one refresh site by construction. A 2026-10-22 sweep found about 245 untimed `add_modifier`-with-`multiplier` sites, of which roughly 137 modifier keys sit on a country that holds the system's entry:

| System (entry) | Modifiers | Revolution repair today |
|---|---|---|
| United Nations (`je_united_nations`) | 47: membership benefits, dues, contributor and patron grants, mission service cost, mandate war support, seabed royalty, Antarctic station upkeep, 15 conventions × `un_convention_multiplier`, 17 `un_regime_*` × `un_enforcement`, 3 embargo and sanctions modifiers | Yes: the `<modifier>_on` mirrors (`un_state_effects.txt`) |
| Grand Monuments (`je_grand_monuments`) | 34: `gm_add_national` ×33 (`gm_effects.txt:1092-1129`), `gm_arch_diversion` | No |
| Tax code, Light setting (`je_tax_code`) | 21 generated `te_tax_light_relief_*` / `te_tax_light_react_*` | No; the entry is documented as display-only and stateless (`je_tax_code.txt:15-18`), so converting changes that contract |
| Banking (`je_banking_cycle`) | 14: fiscal policy effect, six `bubble_inertia_*`, `planning_treasury_pool_balance`, `te_monetary_rate_paid`, `te_monetisation_minting`, `te_mon_real_wage_dividend`, `te_fx_weak`, `te_fx_strong`, `te_capital_controls_fatigue` | Yes: `te_monetary_inherit_central_bank` |
| Covert Warfare | 5: `intelligence_capacity_defense`, `iw_domestic_defense`, `iw_funding_defense`, `covert_operation_funding_cost` (refreshed in two places, `je_covert_warfare.txt:188-227` and `covert_warfare_effects.txt:2575-2587`), `iw_tradecraft_bonus` | No |
| Cultural Hegemony | 4: `cultural_hegemony_effect`, `cultural_hegemony_foreign_benchmark`, `ch_cultural_program_funding` and its cost | No |
| Colonial Empire | 4: three programmes at a literal ×0.333/0.667 (value = level ÷ 3) and the expense line (`decolonization.txt:1210-1257`) | Yes: `decol_sync_programmes` |
| Nuclear | 3: `nuclear_weapon_program_funding`, `nd_upkeep_cost`, `nd_taboo_possession_cost` | Yes: a tracker reset |
| Global Warming | 2: `global_warming`, `renewable_investment_cost_modifier` | No |
| Space Race | 2 per milestone entry: `sr_space_program_cost`, `sr_funding_progress` | Yes: `sr_cost_modifiers_missing` |
| Strategic Reserve | 1: `st_res_sell_profit_modifier` | No |

Not candidates: anything on a state, building or interest group (UN mission and relief state modifiers, `gm_local_*`, tourism, crowding, the inheritance and Demographics state lines, the reserve's building flows, IG sovereignty modifiers), and country modifiers with no entry behind them (construction cost, judiciary, inheritance, Standard of Living expectations, orbital debris, `sr_commercial_space_dividend`, which outlives the race).

Convert with care:
- `planning_treasury_pool_balance` subtracts its own previous contribution (`scripting_best_practices.md`, the `add_modifier` visibility gotcha). Re-evaluated continuously, it could feed back on itself.
- The FX modifiers re-add only when the gap moves past a step (`te_monetary_fx_effects.txt:355-367`). A continuous value loses that dead band unless the value is rounded to the step.
- Tiered sets (`bubble_inertia_moderate/high/extreme`, with and without `_coop`) choose *which* modifier by threshold. They become one scaling modifier each, at 0 when out of band, or stay as they are.
- A modifier that is only sometimes on needs `value = 0` when off, which works only if 0 hides it (C7).
- The value's scope (C7) decides whether the existing JE-safe script values (`*_for_je`, `root.var:`) carry over, and `je_multiplier_scope_audit` must follow (§ 3.5).

**Policies that survive a revolution.** A revolution's winner keeps the loser's variables but none of its modifiers (`docs/audits/civil_war_inheritance_audit.md`). Every button-toggled policy kept only as a modifier on an entry is lost; that is finding F8, still open for the banking tools, the climate policies, the Cultural Hegemony programmes and the World War modifiers (fixed for the UN by #461 and the Colonial Empire by #508 with mirror variables and a repair hook). With `scaling_modifiers_while_active = { modifier = X value = <0 or 1 from var:X_on> }`, the variable is the only state and the modifier follows it. A winner who inherits the variable and the entry gets the policy back, with no repair code, and the UN's and the Colonial Empire's repair hooks could be deleted. Flat modifiers that are toggled this way on entries today: banking about 62, Cultural Hegemony 32, the UN 21, Global Warming 10, World War 9, Nuclear doctrine 7, Civil Rights' 5 phases, the Colonial Empire's 5 tiers. This is the change with the most code to delete, so test C7's revolution question with the civil-war harness before converting anything.

### 4.3 More outcomes than complete and fail

Several entries already choose between endings inside one `on_complete` or `on_fail`, so the player can't see the endings, or what leads to each, until one fires. With outcomes, each ending is a line in the panel with its own trigger, effect and colour, read in declaration order (C3).

- **Civil Rights** (`journal_entry_systems.md` § Path-dependent resolution): four successes (Federal Mandate, Grassroots Triumph, Negotiated Settlement, Coopted Reform) and four failures (oppressive aftermath, token reform, gradualist stagnation, lost momentum), dispatched on which months-tracker led for 18 months (`movement_events_te.220-.223`, `.100`, `.230-.232`). Eight visible outcomes, ordered most specific first, with the fall-throughs (`.200`, `.232`) last.
- **Colonial Empire** (`journal_entry_systems.md` § Outcomes): six successes (Imperial Federation Act, Civilizing Mission Compact, Iron Fist Holds, Commonwealth Path, Quiet Assimilation, The Empire Endures), collapse, and the voluntary end. The voluntary end (bar above 0, no colonies left) is a separate ending already.
- **The Space Race milestones**: "first" and "subsequent" completions are one `complete` with two `event_outcome_completed_effect_desc` blocks (orbital: `je_space_race.txt:315-334`), and `sr_complete_*_effect` decides which reward applies. Two outcomes (first, later) and the setback make the reward visible before it happens. The `historical` flag could mark the outcome that happened (first in orbit: USSR; first on the Moon: USA), if the flag does nothing else.
- **World War** (`world_war_je.txt:152-193`): completion and failure both clear the same variables; any further endings (negotiated peace vs. total victory) would be new design, not conversion.

### 4.4 Progress bars

- **Tug-of-war bars** (`marker = yes`, an icon at each end): `banking_cycle_momentum_bar` (−5…5) and `banking_policy_stance_bar` (−2…2), which § 3.3 has to redo anyway; `banking_cycle_value_bar` (panic at 0, frenzy at 100, stable at 50); `civil_rights_support_bar` (fails at 0, completes at 100); `colonial_stability_bar` (fails at 0, five bands). The UN chamber's yes/no vote bar is drawn by the widget from `un_disp_res_yes_frac` / `un_disp_res_not_no_frac`, and could become a scripted bar.
- **A real maximum instead of a percentage.** `je_space_race_solar_colonization` shows `sr_progress_solar_colonization_percent` (progress ÷ the stage's goal × 100, `space_race_values.txt:406-424`) against `goal_add_value = 100` (`je_space_race.txt:1369-1374`). That is the journal goal bar, not a scripted bar, so it changes only if the goal bar also takes script values. The widgets' own bars normalise to 0–1 by hand (`sr_disp_progress_frac_*`, `gw_disp_*_frac`, `colonial_empire_disp_bar_high_frac`).
- **The banking bars are clamped by hand** to stop "clamping to min" log spam (`banking_cycle_effects.txt:2880-2927`). A script-value min/max doesn't remove that need by itself: the clamp is on the variable the bar shows.
- **The widgets that draw their own bars** do so because 1.14's presets couldn't show what they needed. Once C5 shows what the new fields can do, check whether any widget bar can become a scripted bar the panel draws natively, which would also reduce what the bars-on-top marker (§ 3.4) has to hide.

The goal pinning in Global Warming and the Space Race milestones (`goal_add_value = TARGET − current`) is intended (`scripting_best_practices.md`), not a workaround to remove.

### 4.5 `send_interface_message`

The mod defines 294 message types in `common/messages/`. 166 are tech headlines, posted through one effect (`headlines_tech_announce_effect`, `common/scripted_effects/headlines_effects.txt:20`). Of the rest, 79 are posted by name from a single site, and five more are posted through a parameter (`$NOTICE$`, `rt_$KEY$_retired_notice`, `te_seabed_basin_full_notice_$B$`, `te_seabed_new_claimant_notice_$B$`, `wonder_construction_complete_$WONDER$`).

What converting gains: no message definition, a custom icon, and effects in the same block. What it may lose: a message type can be muted or turned into a popup in the player's message settings, which an interface message may not allow (C8). So keep types for recurring notices a player may want to silence (seabed claims, banking, the UN), and convert one-offs.

The better target is events that exist only to notify. About 95 visible events have a single option, and about 28 of those do nothing in it, or only show a `custom_tooltip`:

1. **Double notices.** `nuclear_weapon_events.3, .4, .5, .7, .8, .12, .13, .14` (`events/nuclear_weapon_events.txt:414` onward) each post a notification in `immediate` and *also* pop up an event whose only option does nothing. One of the two should go.
2. `nuclear_weapon_events.15`, `.16`, the foreign escalation notices.
3. `un_ceasefire.2, .4, .5` and `un_referendum.2, .3, .4`: the option is a `custom_tooltip` only.
4. `irredentism.9` (commented as the AI path's stand-in for the engine's third-party notice), `.10`, `.11`; `un_mandate.1`, `.2`; `banking_debt_events.3`, `.4` (commented "a notice").
5. `nuclear_loose.5, .7, .8, .9`, broadcast to every human player.
6. `nuclear_custody.3, .4, .8, .12`: a single option plus an `after` cleanup (`nd_custody_clear_arrival`), which the message's effect block would carry.
7. `resettlement.9`, `monument_events.28`, `space_race_events.77`, `nuclear_taboo.20` (pays a reward), `te_lolr.2`.

Keep as events: the outcome events (`movement_events_te.2xx`, `decolonization_events.200-301`), `formation_te.1/.2`, `un_vote.2`, and anything with an image and a choice worth reading. Each conversion is a judgement call: an event the player has learned to recognise by its picture carries something a toast doesn't.

### 4.6 `list_scopes` and `show_trigger_per_scope`

Few sites: the mod's player-facing conditions are mostly variables and `custom_tooltip` lines, not counted lists, and no trigger uses `count = all` or `percent`.

1. **Forming the United Nations of Earth** (`common/country_formation/te_formable_countries.txt:154`, `:164`): `une_formation_supermajority` (`formable_gating_triggers.txt:272-282`, at most one great power outside the bloc), `une_formation_bloc_aligned`, `une_formation_no_internal_rivalry` and the bloc-unanimity branch of `une_formation_world_order`. Listing the great powers that fail tells the player whom to bring in. The best case.
2. **Turtle Island** (`te_vanilla_turtle_island.txt:82-85`, five homeland states): vanilla's condition; take whatever 1.15's vanilla entry does.
3. **The seven covert diplomatic actions** (`covert_operations.txt`, via `covert_ops_type_below_cap`), wrapped in `custom_tooltip`, so C10 decides.
4. **The Imperial Federation decisions** (`extra_decisions.txt:140`, `:206`) test `colonial_state_count >= 4`, a script value. Rewritten as `any_scope_state = { is_overseas_colonial_state = yes count >= 4 }`, the tooltip could name the colonies.

New content with "all of these" conditions should use it from the start.

### 4.7 Regional exile pools

The mod exiles a character in two places, both into the global pool, where other countries can invite them:

- `events/un_events.txt:3809`: the International Criminal Court convicts a leader (`scope:un_icc_accused = { exile_character = yes }`). A pool nobody can reach, with a sentence (`years = N`), reads as detention in The Hague, and the character comes home after serving it. Depends on C9.
- `common/scripted_buttons/timeline_extended_scripted_buttons.txt:5628`: founding a custom religion exiles the Devout leader. A pool only co-religionist countries can reach fits.

Two systems could use a pool they don't have today:

- **Penal Labor Camps** (`law_penal_labor_camps`, `mod_systems.md` § Penal Labor Camps): a pool for agitators the law sends away, which only the country itself can reach, with a term.
- **Covert warfare**: a defector or a burned agent going to the country that ran the operation, through a pool only that country (or its bloc) can reach.

Each pool needs its loc key (the tab name in the Invite Exile screen) and a `has_regional_exile_pool_access` check wherever the mod looks for an exile.

### 4.8 Glossary

The glossary is for setting vocabulary, not mechanics, and the mod's 196 game concepts are almost all mechanics (banking, the UN, covert warfare). Plain-text terms that would fit, from a sample search of English loc: Kessler syndrome (7 lines; the mechanic is `concept_orbital_debris`), Non-Aligned Movement (5), Realpolitik (3), *zaibatsu* (2), *dirigisme* (2). Worth a rule more than a project: a new historical or setting term in event text becomes a glossary entry, not a concept. `scripts/analysis/concept_term_audit.py` could learn glossary names once the link syntax is known (C12).

### 4.9 `play_music_cue`

It plays an existing cue, and the mod ships no music (no `music/` folder), so this means picking vanilla cues for a handful of moments: the first nuclear detonation, the Moon landing, a world war breaking out, a climate tipping point. Low value; do it with an event pass, not on its own.

### 4.10 Regnal numbers

Nothing to change. The mod's 12 government types (`common/government_types/timeline_extended_governments.txt`) are all parliamentary, presidential or dictatorial, so none numbers its rulers, and a formable the mod adds starts its own numbering. Heirs in the Heir Education panel should gain their numeral without edits (C11).

## 5. Order of work

Before Nov 5:
1. Write the journal entry converter (§ 3.1) and its test; review its dry-run output.
2. Draft the 45 `conclusion_desc` texts.
3. Teach the tooling both shapes (§ 3.5), so audits pass before and after the conversion and the release-day diff is script only. This can merge to `main` before Nov 5.
4. Make sure the vanilla clone holds 1.14.5 (runbook § 0), for the GUI rebuilds and `REPLACE:` re-bases.
5. Run `scripts/snapshot_balance.py` (runbook § 1).

On release day, on a `vanilla-1.15` branch:
1. Runbook §§ 2–4: digests, `vanilla_parsed.py build`, the engine-doc refresh, generators, the effect/trigger catalog re-bootstrap.
2. C1–C5, recorded here.
3. The converter (§ 3.1), the five vanilla entries (§ 3.2), the bars (§ 3.3), the GUI rebuilds (§ 3.4), the remaining runbook steps.
4. Every check green; `POST /reload` with no new warnings; in game, every mod journal entry opens, shows its outcomes and bars, and its widgets mount.
5. Merge once the mod loads on 1.15. Players on 1.14.5 can't load outcome syntax, so the merge goes with the patch, not ahead of it.

After the migration: C6–C10, then § 4 in order.
