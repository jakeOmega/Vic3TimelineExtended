# Vanilla 1.15 preparation (2026-10-22, updated 2026-10-30)

Vanilla 1.15 was due on 2026-10-22 and slipped to **2026-11-05**. This doc reads what is known about it against the mod: what to check the day the patch ships, what has to change before the mod loads and works, which new features are worth building, and where 1.15 overlaps the mod without needing a change. The general bump procedure is still `docs/guides/vanilla_patch_runbook.md`; this doc covers only what is specific to 1.15. After the migration, turn it into the migration record, as `vanilla_1_14_5_migration.md` was.

Sources, in the order they arrived:
- **Paradox's pre-release modding notes** (pasted by the owner 2026-10-22): journal entry outcomes, map modes, scaling modifiers, styled bars, interface messages, `list_scopes`, regional exile pools, glossary, `play_music_cue`, regnal numbers. §§ 1–5 were first written from these.
- **The 1.15.0 Modding-Digest** (`<vic3_modding_digests_path>/1.15.0/`, published 2026-10-29): `changes_breaking.md`, `changes_features.md`, the `types/*.md` readmes, and the full 1.15 engine dumps in `docs/` (`effects.log`, `triggers.log`, `modifiers.log`, `event_targets.log`, `on_actions.log`, `custom_localization.log`). § 0 diffs those against 1.14.5's. Two caveats: the digest is a diff against **1.13.11**, so its breaking-change list mixes 1.14 items the mod already migrated with new ones; and its `docs/data_types_*.txt` are byte-identical to 1.14.5's, though `changes_data_types.md` lists new types (`JournalEntryOutcome`, `ConcludedJournalEntry`, `ScalingModifier`), so **GUI data functions are still unchecked** (C4). Its game-file diff (`changes_files.md`) is "TBD, added on release day".
- **Paradox's release changelog** (pasted by the owner 2026-10-30). It is cumulative too: war support 0–100, war goals enforced mid-war with mirror goals, the infamy rework, AI regional objectives, strait and piracy grievances, `tax_income`/`weeks_until_bankruptcy`/`gdp_owned_by`, `on_won_war` and kin, `is_independent_and_not_being_subjugated` and the war-support script commands all shipped in 1.14.x, and the mod migrated to them (`vanilla_1_14_5_migration.md`, the runbook's rename table). This doc covers only what is new against 1.14.5, checked name by name against `vanilla_parsed/` and the 1.14.5 engine catalogs.

**Nothing here has been checked against 1.15 game files**, which nobody outside Paradox has yet. Statements about 1.15 come from the notes, the changelog and the digest's engine dumps and readmes; anything that needs the files is a release-day check (§ 2). Statements about the mod were first read from `main` at `e5b54f1` and re-checked, with the 2026-10-30 additions, at `e3c0f5d`.

## 0. Engine surface, 1.14.5 → 1.15 (from the digests)

The runbook § 3 diff, run on the 1.14.5-openbeta and 1.15.0 digests' `docs/` on 2026-10-30:

| Kind | Removed | Added |
|---|---|---|
| Effects | none | 13 named (`add_decree`, `remove_decree`, `replace_decree`, `enact_law`, `add_power_bloc_mandate`, `change_power_bloc_name`, `destroy_power_bloc`, `leave_power_bloc`, `leave_plays_supporting`, `establish_cossack_host`, `remove_cossack_host`, `play_music_cue`, `send_interface_message`) plus the iterators generated for 33 new geographic regions (`central_russia`, `congress_poland`, `transcaucasia`, 15 `rcw_*` civil-war zones, …), none of which collides with the mod's seven `geographic_region_*` keys |
| Triggers | `has_war_goal_at_risk_of_being_dropped` (no mod use) | 26 named, among them `cold_effect`, `in_north_hemisphere`, `in_south_hemisphere`, `in_tropics`, `has_building_levels_in_state_region`, `num_building_assets_of_type`, `has_regional_exile_pool_access`, `is_in_regional_exile_pool`, `war_is_in_stalemate`, `enemy_pressure`, `blockaded_gdp_share`, `has_military_reach`, `is_interest_group_pool_full`, `current_career_length` |
| Event targets | none | 11, among them `global_average_gdp_per_capita`, `color`, `home_state`, `military_formation`, `military_reach`, `piracy_grievance_against` |
| On-actions | **`on_journal_entry_completed`, `on_journal_entry_failed`** (no mod use) | `on_journal_entry_concluded`, `on_power_bloc_formed`, `on_character_returned_from_exile`, and Russian/regional pulses |
| Modifier types | six culture modifiers for `north_caucasian` and `siberian` (no mod use) | 200, among them copper's goods and tariff keys, Cossack Hosts' building group, the ten new laws' enactment keys, `country_disallow_army_creation_bool`, `country_disallow_military_ship_construction_bool`, `state_disallow_barracks_construction_bool`, birth rate by acceptance status and by strata, `country_overlord_law_enactment_success_add`, `country_interest_tier_*_trade_advantage_mult`, `country_power_bloc_formation_mandates_add`, `interest_group_ideology_*_leader_chance_mult` |

None of the removed names appears in the mod. The added modifier keys also name the new content that § 1 has to account for:

- **Cultures** `north_caucasian` and `siberian` are gone, split into `abkhazian`, `caucasian_turk`, `chukchi`, `crimean_tatar`, `dagestani`, `evenki` and `ossetian`.
- **Ten laws**: `law_caesaropapism`, `law_communal_administration`, `law_extraordinary_commission`, `law_internal_colonization`, `law_labour_suffrage`, `law_military_bureaucrats`, `law_official_nationality`, `law_okhrana`, `law_revolutionary_guard`, `law_third_section`.
- **Ideologies**: every 1.14.5 character ideology but `ideology_child` gets an `interest_group_ideology_<x>_leader_chance_mult`, except `ideology_social_democrat` and `ideology_communist`; instead there are `state_socialist` and `communist_leader`, which 1.14.5 lacks. So `ideology_social_democrat` is very likely renamed `ideology_state_socialist` (the changelog: "Renamed the Social Democrat ideology to State Socialist"), and the communist leader ideology probably `ideology_communist_leader`.
- **A good and buildings**: `copper` (`building_copper_mine`), `building_cossack_host` (group `bg_cossack_host`), five monuments (`building_winter_palace`, `building_grand_kremlin_palace`, `building_saint_isaacs_cathedral`, `building_kizhi_pogost`, `building_cathedral_of_christ_the_savior`).
- **Cavalry**: offense modifiers for `cuirassiers`, `dragoons`, `hussars` and `lancers`; the four types themselves already exist in 1.14.5.
- **Movements**: `movement_anti_communist` (the White Movement) and `movement_cossack`.

The digest's breaking-change list, new against 1.14.5: journal entry outcomes, JE group illustrations, styled progress bars, mobilization option group backgrounds, objective illustrations, the East Asian gene, changed state regions, and `|q` quote escaping in loc. Its three "(1.14)" items (ship type AI values, subject type `re_establish_war_goal`, war goal `mirrored_wargoal`) loaded clean on 1.14.5.

## 1. Summary

Rows above *New features* have to be done for the mod to load and work on 1.15; rows below it are new features (§ 4). Where 1.15 overlaps the mod without needing a change is § 6.

| 1.15 change | What it does to the mod | Size | When |
|---|---|---|---|
| State regions renamed, split, merged and re-provinced; new cold fields | **Likely crashes or breaks Russia.** `map_data/state_regions/` is a full 1.14.5 copy of all 17 vanilla files, so it keeps the old keys and provinces and strips every state's cold values | 17 files (`resources.py`), 5 hand-written sites, 6 generators | First step on release day (§ 3.7) |
| Vanilla adds `law_communal_administration` and `building_copper_mine` (with a `copper` good) | **Key collisions.** The mod defines both; its law is dropped as a duplicate, and its lead-producing copper mine replaces vanilla's, leaving copper with no producer | 1 law (64 references), 1 building, 64 lead-consuming methods | Owner decision before Nov 5 (§ 3.8) |
| Ideology and party rework (Social Democrat → State Socialist, a `communist_leader`, Patriotic/Militarist split, Trade Unions' stances) | **Rolled back silently.** 142 whole-ideology `REPLACE`s, 11 restated party join weights and the law consistency walk restate 1.14.5; 24 hand-written references to the two probably renamed ideologies, and First Past the Post's party list | Regenerate 3 files on the install; ~25 hand edits | Release day (§ 3.8) |
| Ten new laws in law groups the mod extends | **CI fails** on a 1.15 snapshot (`ideology_lawgroup_audit`, about 78 blocks; a First Past the Post test); machine rule's lock and the voting-law lists miss them | ~78 stances, 3 petition lists, per-law `INJECT`s | Release day (§ 3.8) |
| Journal entry groups need `illustration`; mobilization option groups need `background` | **Required fields.** The mod's 3 groups and its `training` group have neither | 2 illustrations (one group is unused), 1 background | Art before Nov 5 (§ 3.9) |
| Loc functions need `\|q` on a quoted `$key$` | **Errors.** 261 references in 13 loc files, one generator and both translation memories | Mechanical | **Can land now**: `\|q` already works on 1.14.5 (§ 3.10) |
| Defines 1.15 rebalances (assimilation, incoherence, devastation) | **Silent.** The mod pins the typo'd assimilation key and `INCOHERENCE_FACTOR`, which may undo vanilla's fixes | 6 keys to re-read | Release day (§ 3.11) |
| The 1.15.0 digest is out | **A hazard now.** A server cold start on a machine without a pinned docs snapshot re-renders `docs/engine/` from 1.15 while the game is 1.14.5 | 1 guard in `mod_state_server.py` | Before Nov 5 (§ 3.11) |
| Journal entry outcomes replace `complete`/`on_complete`, `fail`/`on_fail`, `invalid`/`on_invalid`, `on_timeout` | **Breaks loading.** 25 of the mod's 28 entries and its 5 `REPLACE:` copies of vanilla entries use the old blocks | 58 outcomes, 45 of them in mod entries; 45 new `conclusion_desc` loc keys | Converter written before Nov 5; run on release day (§ 3.1) |
| Five vanilla journal entries the mod copies with `REPLACE:` | Vanilla rewrites them to outcomes; the mod's 1.14.5 copies would undo that and use dead syntax | 5 entries in 3 files; 1 test file | Release day (§ 3.2) |
| `double_sided_*` progress bar presets removed | **Breaks** the two banking tug-of-war bars. `default`, `default_green` and `default_bad` stay, so the other six are fine (C5) | 2 bars | Release day (§ 3.3) |
| Journal entry panel reworked (outcomes, styled bars, map mode) | **Breaks silently.** `gui/journal_entry.gui` is a full copy of the 1.14 panel and calls the completion, failure and timeout tooltips and the bar-preset tests; `gui/te_system_tab_widgets.gui` copies the bar renderer | 2 GUI files; 28 widget files depend on the panel's containers | Release day (§ 3.4) |
| New syntax in the tooling's inputs | Audits read `complete`/`on_complete` etc. by name; some go blind, some flag false positives once entries use outcomes, and `effect_trigger_validity_audit --strict` (now in CI) fails on the converted entries | See § 3.5 | Dual-shape support can land before Nov 5 |
| *New features* | | | |
| Journal entry map modes | **New.** Unblocks the six Demographics maps, the three Cartographic Survey maps (whose hijack is switched off) and the UN map | See § 4.1 | First feature after the migration |
| Journal entry scaling modifiers | **New.** About 137 modifiers re-added with a `multiplier` on a pulse could become declarations, and button-toggled policies could survive a revolution | See § 4.2 | After the migration |
| More than two outcomes per entry | **New.** Civil Rights and the Colonial Empire each already pick between eight endings inside `on_complete`/`on_fail`; the Space Race picks first vs. later | See § 4.3 | After the migration |
| Styled progress bars, script-value min/max | **New.** Native tug-of-war bars with a marker and end icons | See § 4.4 | After the migration |
| `send_interface_message` | **New.** The mod defines 294 message types; 79 are posted from one site, and 166 more are tech headlines posted through one effect | See § 4.5 | Low effort, any time after |
| `list_scopes` / `show_trigger_per_scope` on `any_*` triggers | **New.** Tooltips that name which states or countries are missing | See § 4.6 | Any time after |
| Regional exile pools | **New.** Fits a deposed religious leader and Penal Labor Camps; an inaccessible "prison" pool is emptied quarterly (C9) | See § 4.7 | Optional |
| Glossary | **New.** Few candidates; the mod's concepts are almost all mechanics | See § 4.8 | Optional |
| `play_music_cue` | **New.** Vanilla cues only, unless the mod ships music | See § 4.9 | Optional |
| Regnal numbers | Nothing to change: all 12 mod government types are non-hereditary | See § 4.10 | Check only |
| Smaller modding additions: `progress_condition`, `disable_evaluation`, scripted button `cost`/`tags`/`autocomplete`/`icon`, `fire_only_once`, `enact_law`, the disallow-army/warship/barracks modifiers, treaty article `is_one_time`/`can_propose`/`show_in_lens`, power bloc effects | **New.** Mostly small wins in specific systems | See § 4.11 | Any time after |

## 2. Release-day checks

Run these before converting anything. Each is a question the notes don't answer and the conversion or a feature depends on. Record each answer here, with the file and line it came from. **Answered (digest)** marks what the 1.15.0 digest's readmes (`types/journal_entries.md`, `types/scripted_progress_bars.md`, `types/regional_exile_pools.md`, `types/glossary.md`, `types/country_definitions.md`, `types/scripted_buttons.md`) settled on 2026-10-30; confirm those against the shipped files, which carry the same readmes beside their databases.

**What to pull from the 1.15 install on release day**, in one pass (none of it is in the digest):
1. `game/common/journal_entries/*.txt` and `common/journal_entry_groups/` (C2, C3, § 3.2, the illustration paths of C15).
2. `game/gui/journal_entry.gui`, the journal panel's other `.gui` files, and every vanilla `.gui` the mod overrides (C4, § 3.4). The digest's `data_types_*.txt` are stale, so the GUI data functions come only from these files or a fresh `script_docs` dump (runbook § 0).
3. `game/map_data/state_regions/*.txt` and the province map (C16): every renamed, split, merged or re-provinced state.
4. `game/common/laws/`, `law_groups/`, `ideologies/`, `interest_groups/`, `parties/`, `political_movements/` (C17), and `common/goods/`, `buildings/`, `production_methods/`, `company_types/`, `cultures/` for the new content § 3.8 lists.
5. `game/common/defines/00_defines.txt` (C18).
6. A mod-free `script_docs` dump if the digest's dumps turn out to predate a hotfix (runbook § 0), and `vanilla_parsed.py build` on the install (runbook § 2).

**C1. Does the old syntax still load?** Launch 1.15 with the mod unconverted and read `debug.log` (log-triage skill) for `Unexpected token` on `complete`, `on_complete`, `fail`, `on_fail`, `invalid`, `on_invalid`, `on_timeout`, the four `custom_*_header` fields, the `event_outcome_*` fields and `double_sided_gold`. If vanilla kept a compatibility path, § 3.1 can be done carefully rather than on the day; if not, every mod journal entry is broken until it's done.

**C2. How vanilla converted its own entries.** Read a dozen converted vanilla entries for:
- the order of outcomes: success first or failure first, and where the hidden invalid outcome goes;
- where the old `custom_completion_header` / `custom_failure_header` / `custom_on_completion_header` / `custom_on_failure_header` went (presumably `header` / `effect_header`; seven Space Race entries set all four, and an eighth sets the two completion ones);
- where `event_outcome_completed_desc`, `event_outcome_failed_desc`, `event_outcome_timeout_desc`, `event_outcome_completed_effect_desc` and `event_outcome_failed_effect_desc` went (presumably into each outcome's `event_outcome_desc` / `event_outcome_effect_desc`; the Space Race has 22, the tax code's vanilla copies 6);
- whether `event_outcome_activated_effect_desc` still exists at entry level (the notes don't mention it; the UN entry uses it 5 times, `je_united_nations.txt:557-589`). **Answered (digest): it stays**, beside `event_outcome_activated_desc`;
- whether `je_standard_completion_header`, `je_standard_failure_header`, `je_standard_on_completion_header` and `je_standard_on_failure_header` exist as loc keys. **Answered (digest): yes**, the readme names all four as "the standard look", and `je_standard_completion_conclusion_desc` / `je_standard_failure_conclusion_desc` as stock conclusion texts;
- what vanilla wrote for `conclusion_desc` (length and voice), since the mod needs 45;
- what an entry with **no** outcomes looks like in the panel. Five mod entries never conclude (`complete = { always = no }`: Covert Warfare, Cultural Hegemony, Global Warming, Nuclear Program, United Nations). The readme allows it ("Zero or more outcomes").

Also settled by the readme: `conclusion_desc` is required on every outcome, `header` and `effect_header` on every non-hidden one; a `timeout` needs an outcome with `flags = { timeout }` and no `trigger`; at most one timeout and one `invalid_outcome`, which must also be `hidden`; flags `fails_subgoal` and `historical` exist. A concluded entry is listed in a new concluded tab under its name **localised with no scope**, so an entry whose name reads scoped data needs a static `<key>_concluded` loc key (§ 3.1). Custom widgets show only while the entry is active; a concluded entry's page shows its name and the outcome's `conclusion_desc`.

**C3. Precedence.** When two outcome triggers become true on the same tick, which wins: declaration order, or something else? (The readme says only that outcomes are *presented* in declaration order.) The Space Race can complete and fail together, and so can the four social-movement entries that have complete, fail and timeout. Find 1.14's order and keep it.

**C4. The panel's data functions.** In vanilla's new `gui/journal_entry.gui`:
- Are `JournalEntry.GetCompletionTooltip`, `GetFailureTooltip`, `GetOnCompleteTooltip`, `GetOnFailTooltip`, `GetTimeoutTooltip`, `GetOnTimeoutTooltip`, `CanComplete` and `CanTimeOut` gone? The mod's copy calls all of them. GUI errors aren't logged, so a removed function shows only as a blank section.
- What datamodel lists the outcomes, and which functions draw an outcome's header, colour, trigger tooltip and effect tooltip?
- Do `custom_widget_container_1` … `_7` and `custom_widget_container_je_icon` still exist, in the same places? The mod's 28 widget files under `gui/journal_entry_widgets/` mount into them, and a missing container hides the widget with no error. **Partly answered (digest):** the readme lists all eight in the old order (icon; 1; timeout; status; 2; buttons; 3; scripted bars; 4; description; 5; involved countries; 6; progress, outcomes and timeout; 7). Confirm the names in the shipped `.gui`.
- How does the panel turn the map mode on: automatically, or with an `onshow`/data function that another panel could call too (C6)?

**C5. Progress bars.** In `scripted_progress_bars.md`:
- Are `default_green` and `default_bad` gone with `double_sided_*`? Six mod bars use them. **Answered (digest): no.** `default`, `default_green` and `default_bad` are the three ready-made looks left; every other bar needs the new fields.
- Which fields reproduce `double_sided_gold` (two mod bars)? **Answered (digest):** `progress_texture`, `background_texture`, `glow_texture`, `glow_line_texture` (matching `progressbar_<colour>*.dds` sets), optional `color` tint, `marker = yes` for a "between two poles" bar, and `left_icon` / `right_icon` (journal panel only). Vanilla's own example is a −40…40 bar with `marker = yes`.
- Which data functions replaced `ScriptedProgressBar.IsDoubleSidedGold`, `IsDoubleSidedBad`, `IsDoubleSidedSpain`, `IsDoubleSidedRyukyu`, `IsDefault`, `IsDefaultGreen` and `IsDefaultBad`? `gui/journal_entry.gui` and `gui/te_system_tab_widgets.gui` branch on them.
- In which scope does a script-value `min_value` / `max_value` run (the owner, or the journal entry)? Can it read the owner's variables? **Partly answered (digest):** "evaluated in the journal entry's scope whenever the bar is clamped or shown". Whether `root` there is the entry or its owner is still to test.
- New, optional: `progress_condition` inside `weekly_progress`/`monthly_progress`/`yearly_progress` works like `if` but lists the factor, ticked or unticked, in the panel's new Advance and Retreat lists (§ 4.11).

**C6. Map modes.** Everything § 4.1 depends on:
- Which scopes `map_color` and `map_tooltip` can reach besides the state root: the journal entry's owner, the viewing player, `scope:journal_entry`, scopes saved on the entry? A map of *the player's* data (their covert targets, their colonies) needs the owner; a world map (temperature, GDP per capita) needs only the state.
- Whether `map_color` takes `if`/`else` or only the three forms in the notes. One map per entry means a selector (§ 4.1) has to switch either the colours or the factor.
- When it's evaluated: each frame, on opening, daily? Mod maps must read cached variables, never walk pops.
- Whether it shows while the entry is **inactive** but shown (`is_shown_when_inactive`).
- Whether only the journal entry panel triggers it, or also a vanilla panel tab that shows the entry's content through `GetPlayerJournalEntry`. Banking, Cultural Hegemony, the UN, Climate, the Strategic Reserve, Nuclear, Covert Warfare and Demographics live in such tabs (`budget_panel`, `culture_panel`, `diplomatic_overview`, `market_panel`, `panel_military`, `pops_overview`, `states_panel`), and the Space Race, Grand Monuments, the Colonial Empire and the Seabed in the Timeline Extended window. If only the journal panel paints the map, a player using those tabs never sees it.
- How water, wasteland, unowned and decentralized states are drawn, and whether there's a legend.

**C7. Scaling modifiers.** Everything § 4.2 depends on:
- Scope of `value`: owning country or journal entry? The mod's `je_multiplier_scope_audit` exists because a `je:` modifier's stored multiplier is evaluated in journal-entry scope, where country-only reads return `none`. **Answered (digest):** "value root = same as the Journal Entry scope (owning country or no scope)", so country reads should work; vanilla's own example reads `scope:journal_entry.scripted_bar_progress(…)`. Test one country-only read anyway.
- How often `value` is re-evaluated. **Answered (digest):** "on its update frequency", and the effects follow it. The rate itself is still unknown.
- Whether one entry can carry several (the readme says "zero or more blocks"), and whether the same modifier can sit in both `modifiers_while_active` and `scaling_modifiers_while_active`.
- Whether a value of 0 hides the modifier from the panel and the country's modifier list, or shows a row of zeros. § 4.2's policy switches depend on 0 hiding it.
- Whether a negative value works.
- Whether `modifier:X` reads see it the same day.
- Whether a revolution's winner gets it back with the inherited entry. Test with the civil-war harness (`docs/audits/civil_war_inheritance_audit.md`; `scripts/analysis/save_country_probe.py --diff`).

**C8. `send_interface_message`.** The 1.15 `effects.log` gives `title` (localised against the current scope), optional `desc` and `icon`, and any number of effects run in the current scope; supported scopes "none". Still open: who sees it (only the scoped country? does it no-op for the AI?), whether `title`/`desc` take saved scopes (`[SCOPE.sCountry('x').GetName]`), whether it reaches the message log as well as the toast, and whether a player can mute it. Message types can be muted in the message settings, and the mod's 289 types rely on that.

**C9. Regional exile pools.** What `has_access = { always = no }` does (a pool nobody can invite from, which is what a prison is). **Answered (digest), and it rules the prison out:** a pool nobody can access is checked quarterly and its exiles move to the global pool, **losing their return date**. A pool needs at least one country that passes `has_access`, and that country can invite from it. The effect is `exile_character = { exile_pool = <key> months/years = <int> }`; the duration needs `exile_pool`. Still open: whether `years`/`months` run while the home country no longer exists; whether a character in a regional pool still counts for vanilla's exile checks and the agitator pool.

**C10. `list_scopes`.** Whether it survives inside `custom_tooltip = { text = … <triggers> }`. The mod wraps many player-facing conditions that way, which would hide the list.

**C11. Names.** **Partly answered (digest):** only hereditary governments and those with `uses_regnal_numbers = yes` number their rulers, numbers come only from `regnal_numbers` in `common/country_definitions`, and numbering doesn't carry across a tag change, so § 4.10 stands. Still check: open the mod's GUI overrides that show character names (`Character.GetFullNameNoFormatting` ×10, `GetFullName` ×2) and check a monarch reads "Edward VII" once, not twice and not without the numeral. Check the Heir Education panel, which shows heirs.

**C12. Glossary links.** How loc links a glossary entry (`[glossary_x]`? a `Glossary(…)` function?), and whether `concept_reference_audit` then flags it as a missing concept. **Answered (digest):** both: `[glossary_x]` and `[Glossary('glossary_x','text')]`. Keys must start with `glossary_` and need `<key>` and `<key>_desc` loc; optional `icon` and `shown_in_encyclopedia`. The new global `ConceptByKey(…)` exists too. Still check what `concept_reference_audit` and `check_gui_lint.py` do with them (§ 3.5).

**C13. The rest of the patch.** The runbook still applies in full: Modding-Digests `1.15.0/changes_breaking.md` and `changes_script_docs.md` (§ 3), the modifier-type-definition diff, the at-risk GUI loop (§ 5), the `REPLACE:`/`INJECT:` sweep, the vanilla constants the mod mirrors (§ 6b), and old-save repairs to retire at "vanilla 1.15" (§ 6a: `test_old_save_repairs.py` names them once `vanilla_parsed/` is rebuilt).

**C14. Saves.** Load a 1.14.5 save with active and concluded mod entries on 1.15 with the converted mod. Do concluded entries stay concluded and active ones keep their bars? Most systems keep their state in variables (`sr_completed_*`, `civil_rights_resolved`, `colonial_empire_completed`), which should hold either way; vanilla's entry records are the unknown.

Added 2026-10-30, from the changelog and digest:

**C15. Art fields.** What vanilla's own journal entry groups set for `illustration` and `themed`, so the mod's two live groups can borrow a vanilla path as a placeholder until art exists (§ 3.9); whether a mobilization option group still reads `icon` beside the new `background`; that the six vanilla JE groups and six vanilla mobilization groups the mod uses still exist (`je_group_russia_great_reformer` above all).

**C16. State regions.** The 1.15 list of state keys from `map_data/state_regions/`: the three renames, which of `STATE_CHUKOTKA` / `STATE_KAMCHATKA` survives the merge, whether any of the 17 file names changed (`resources.py` keeps a stale copy), and whether Kazakh states the mod's deposits name (`STATE_URALSK`, `STATE_SYRDARYA`) were redrawn. Then whether `INJECT:STATE_X = { resource = { … } }` works on state regions (§ 3.7), and the two strategic regions the mod `REPLACE`s.

**C17. The new politics content.** For each of the ten new laws: its `group`, its `parent` (a variant?), its `unlocking_laws`/`disallowing_laws`, and whether it has an expected-SoL line. Vanilla's `law_communal_administration` and its Bourgeois Specialists amendment in full (§ 3.8). The ideology keys: is `ideology_social_democrat` now `ideology_state_socialist`, is `ideology_communist` now `ideology_communist_leader` (or both kept), and what are the Militarist, Tsarist, Disciplinarian and Militant keys and which interest groups hold them. The party key for the "Socialist Party". Whether the Nomenklatura is a renamed Intelligentsia or a ninth IG type. `building_copper_mine` and the `copper` good in full, which vanilla methods and buildings take copper, and the copper rows of the ten companies; `bg_cossack_host`'s parent group. Whether the six citizenship laws, `amendment_tradition_of_free_elections`, `formation.17`, `00_buy_packages.txt`, `13_construction.txt` and the mod's 52 `REPLACE`d production methods changed in vanilla.

**C18. Defines.** Diff vanilla's `00_defines.txt` and `00_ai.txt` against 1.14.5 for the mod's 56 overridden keys, starting with the six in § 3.11, and look for `define macro is missing` in `debug.log`.

**C19. First-launch log.** Before converting anything, one launch of 1.15 with the mod as it stands answers several questions at once (log-triage skill): `Duplicated key` lines (the communal administration law, the copper mine's modifier type); `Unexpected token` lines (C1) and invalid-scope lines (the old state keys, § 3.7); the `|q` loc errors (§ 3.10); and a `TE_MONUMENTS:` or `TE_SELF_CHECK … nd_trade_` line, which shows how 1.15 treats `$ARG$` inside a quoted string (§ 3.11). Launch with the generators off (`VIC3_SKIP_POST_LOAD_GENERATORS=1`) so nothing is rewritten before the log is read.

**C20. Behaviour to test in game.** Renegotiate a treaty holding a Demilitarized Zone and count the state's `demilitarized_zone_state_modifier` (and whether the old article's withdrawal effect ran first) (§ 4.11). `fire_only_once`: per country or per scope, saved, inherited by a revolution's winner, marked on trigger or on fire. `enact_law`: does it respect `can_enact`, fire `on_law_activated`, and cope with an enactment already running in the group. `progress_condition`: how a factor of 0 and a factor read from a named script value show. And grep vanilla 1.15 `common/` for users of `is_one_time`, `show_in_lens`, `disable_evaluation` and the new birth-rate modifiers (§ 6).

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

That is 45 outcomes in mod entries (38 shown, 7 hidden), each needing a `conclusion_desc` key. No `<key>_concluded` names are needed: the only mod entry whose name reads scoped data is the banking entry, which never concludes. The text is the flavour shown on a concluded entry, so it can be drafted before Nov 5 and dropped in with the converter. Put the keys beside each entry's existing `_desc`/`_reason` keys and run `organize_loc.py`, which files by key shape: check where it puts `_completed_desc`, `_failed_desc`, `_timeout_desc` and `_invalid_desc` before writing 45 of them.

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

The two double-sided bars need the new fields (`progress_texture`, `background_texture`, the two glow textures, `marker = yes`, optionally `left_icon`/`right_icon`). The other six keep `default_green` and `default_bad`, which 1.15 keeps (C5).

### 3.4 GUI

- **`gui/journal_entry.gui`** is a full copy of vanilla's 1.14 panel (its first line still reads `# COPY-PASTED FOR NOW`). The mod's own change is small: the bars-on-top marker (`custom_widget_container_7`) hides the scripted-bar block (`:249-251`) and the goal bar (`:675-677`) for an entry that draws its own. Rebuild it as vanilla 1.15's file plus those two hunks, the runbook § 5 way ("the vanilla file with the mod's own hunks re-applied"), not as a 3-way merge: 1.15 rewrites the parts the copy depends on, and a merge would keep stale 1.14 sections. If 1.15 lets an entry hide its own goal bar or style it, check whether the override can go altogether.
- **`gui/te_system_tab_widgets.gui`** copies vanilla's bar renderer into `te_je_scripted_bars` (`:15`, branching on `IsDefaultBad`, `IsDefaultGreen`, `IsDoubleSidedGold` at `:26/44/63`) and the goal bar into `te_je_goal_bar` (`:136`). Re-copy both from vanilla 1.15's renderer. Users: `banking_dashboard_widget.gui`, `un_overview_widget.gui`, `panel_military.gui`.
- **Widget mounts.** If C4 finds a container renamed or moved, every `widget = { … container = "custom_widget_container_N" }` in `common/journal_entries/` follows, and so does the container table in `gui_modding_guide.md` § journal-entry widgets.
- **The other 26 same-path overrides** go through runbook § 5 as usual. 1.15 is a major release, so expect most of them at risk. The changelog's UI items point at these, beyond the journal panel:

  | 1.15 UI change | Mod file | Risk |
  |---|---|---|
  | The law panel shows how a law's effects differ from the current one | `00_te_law_effects.gui` (generated by `gen_law_effects_gui.py` from 1.14.5 fixtures in `test_fixtures/vanilla_gui/`; redefines `politics_panel_change_law`, `selected_or_enacting_law_content`, `FancyTooltip_Law*`) | High: refresh the fixtures from 1.15 and rerun the generator |
  | Per-state Unrealized Taxes list in the budget panel | `budget_panel.gui` (full copy, "COPY-PASTED FOR NOW") | High: the list never shows until rebuilt |
  | Building employment tooltips (hiring, unable, unwilling, downsizing; workers who left) | `states_panel.gui` (full copy; hiring icons at `:5559-5577`), `building_details_panel.gui` (full copy), `states_panel_buildings.gui`, `goods_state_panel.gui` | High |
  | Long journal entry and event option tooltips nest their overflow | `tooltip.gui`, which redefines vanilla's base `TooltipWidgetType` and `FancyTooltipWidgetType` (width 600 against 550) | High if the nesting lives in the base types: it would be off everywhere |
  | Mobilization option groups with backgrounds | `military_formation_panel.gui` (1.14.5 rebuild; deviation 1 lays the groups out in one column) | Medium: the deviation fights the illustrated layout |
  | The treaty-article lens | `right_click_menu.gui` (treaty-input hunks), `treaty_draft_panel.gui`, `treaty_panel.gui` | Possible |
  | Several hubs and cold in the market view | `market_panel.gui` (full copy) | Possible |
  | Russian content in the politics panel | `politics_panel_overview.gui`; `00_te_country_panel_information.gui` (from a 1.14.5 fixture) | Possible |
- `scripts/analysis/check_gui_lint.py` warns on markup no mod `.gui` has used before. The rebuilt panel will use new 1.15 functions, so expect warnings there that are correct.

### 3.5 Python tooling

From a read of the tools on 2026-10-22, re-checked on 2026-10-30 at `e3c0f5d`. CI now runs 37 audits, and two that joined since change the picture. **`effect_trigger_validity_audit --strict` is in CI** (#1142), so the conversion turns CI red there as well as in the unittest suite, unless the same PR re-bootstraps the catalog from 1.15 (runbook § 4, which needs the install) or gives the journal entry root the outcome keys (below). **`texture_reference_audit --strict`** (#1182) checks that each entity declares the art its type needs, so its registry should learn the fields 1.15 makes mandatory (§ 3.9). The rest of the 2026-10-22 reading stands: no other audit looks a completion block up by name in a way that fails, and most of the work below can land before Nov 5 if each tool accepts both shapes.

**Breaks:**

| Where | Why | Fix |
|---|---|---|
| `test_tax_code_bypass.py:783-819` | Reads `vanilla_parsed/…/journal_entries.json`'s `complete` and diffs the rest of each entry | Fails with a `KeyError` as soon as `vanilla_parsed/` is rebuilt on 1.15, before the mod changes at all. Rewrite against the success outcome (§ 3.2) |
| `test_civil_rights_inheritance.py:77,82,133,141,422`, `test_civil_rights_buttons.py:161`, `test_colonial_empire_layout.py:619,666`, `test_covert_tradecraft.py:191`, `test_grand_monument_registry.py:842,2351`, `test_launch_windows.py:533` | Cut `on_complete`, `on_fail`, `on_invalid`, `on_timeout`, `invalid` or `complete = {` out of an entry by name | Fail once the entries are converted. Each needs a helper that finds an outcome by its flags or header. A shared one in a test utility beats seven copies |
| `effect_trigger_validity_audit.py` (**in CI with `--strict`** since #1142; also feeds `POST /reload` warnings and `GET /scripted-helpers/unresolved`) | Checks every left-hand key against the frozen catalog `docs/engine/effect_trigger_valid_keys.txt` plus per-root extras. `outcome`, `conclusion_desc`, `effect_header`, `effect_all_involved`, `event_outcome_desc`, `event_outcome_effect_desc`, `map_color`, `map_color_second`, `map_tooltip`, `lerp`, `min_color`, `max_color`, `scaling_modifiers_while_active`, the new bar fields, `send_interface_message`, `play_music_cue`, `exile_pool`, `list_scopes`, `show_trigger_per_scope` and the two exile triggers are in neither | Every one is reported as an unresolved helper call. Re-bootstrap the catalog from the 1.15 engine docs (runbook § 4) and add the entry and bar fields to the roots' extras |
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

`effect_trigger_validity_audit`'s journal entry root also lists `complete`, `fail` and `invalid` in `trigger_blocks` (`effect_trigger_validity_audit.py:183`), which is how the context check (#1142) knows their contents are triggers. An outcome's `trigger` must join that set, and its `effect`, `effect_all_involved` and `event_outcome_effect_desc` must read as effect context, or the context check flags every converted entry. A bar's new `progress_condition` (§ 4.11) needs the same: a place in the progress bar root's extras (`:240`), with its `limit` read as an `if`'s.

The roster count the 2026-10-22 note gave (28 listed, 29 run) is stale: `CLAUDE.md` and `ci.yml` now agree on 37.

### 3.6 Docs, guide and metadata

- `.metadata/metadata.json`: `supported_game_version` → 1.15.x.
- `docs/guides/vanilla_patch_runbook.md`: add the outcome conversion to the rename table (old blocks → outcome) and to the symptoms cheat sheet (`Unexpected token: on_complete`).
- `CLAUDE.md` and `docs/guides/scripting_best_practices.md`: wherever they name `complete`, `on_complete`, `fail`, `on_fail`, `on_timeout` or `invalid` (the civil-war rules talk about "completed entries"), and the dynamic-modifier pattern once § 4.2 is decided.
- `docs/systems/journal_entry_systems.md` (CRLF: edit with `Edit` or `sed`, not a Python rewrite): each entry's "Outcomes", "Resolution" or "Never Completes" section.
- `docs/guides/gui_modding_guide.md` (CRLF too): gotchas #14, #17, #21 and #33 cite `journal_entry.gui` line numbers; the widget container table.
- `docs/vanilla/CLAUDE.md` and the reference primers where they describe journal entries.
- Player guide: no mechanic changes from the conversion alone, but the panel looks different. Check the chapters that describe how an entry ends (`07-social-movements.md`, `12-decolonization.md`, `16-space.md`, `18-appendix-social-movements.md`) and any screenshot of a journal entry panel under `images/`.
- Player guide, for the 2026-10-30 items: the copper decision (`02-timeline.md:258` names "Copper … → Conductive and Base Metals"; `03-economy.md:95`, `:815-817`); whatever becomes of the mod's Communal Administration law (`06-politics.md`); `06-politics.md:644` if `INCOHERENCE_FACTOR` changes; a line in the climate chapter that warming doesn't move 1.15's cold (§ 6). Rebuild the PDF with each.
- `docs/guides/vanilla_patch_runbook.md`'s rename table: add each rename C16 and C17 confirm (the three states, the ideologies, the party, `on_journal_entry_completed`/`_failed` → `on_journal_entry_concluded`).
- `docs/guides/scripting_best_practices.md`: the power bloc claims at `:3999` and `:4001` (§ 4.11), the quoted-argument rule at `:1902` once C19 shows 1.15's behaviour, the saved-scope multiplier bullets at `:479` and `:481`, and that marginal interest groups' halved traits (`:223`) hold from 1.15. `docs/vanilla/vanilla_politics_reference.md:275` says the same about marginal groups.
- The "last verified" banners of the `docs/vanilla/` primers: economy (copper, hubs, hiring), politics (the new laws, ideologies, movements, the Nomenklatura), states (cold, Cossack Hosts, Unrealized Taxes), pops (assimilation, the birth-rate lines), colonization (Internal Colonisation), and `docs/vanilla/CLAUDE.md`. `docs/vanilla/vanilla_known_bugs.md:148` names `je_vanguard`, which 1.15 replaces.

### 3.7 State regions and the map

**This is the largest item, and the one most likely to crash the load.** `map_data/state_regions/` holds all 17 of vanilla's state-region files under vanilla's own names (`00_west_europe.txt` … `15_russia.txt`, `99_seas.txt`), and each replaces vanilla's file whole. They are 1.14.5 copies written by `resources.py`, which copies vanilla's files and adds the mod's `resource = { … }` blocks (`deposits_config.json`, 138 states) and state traits (`state_trait_config.json`, 23 states). There is nothing else under `map_data/` (no `provinces.png`, `default.map` or `adjacencies.csv`), and no `replace_paths`.

What 1.15 changes underneath them (digest, `changes_breaking.md` § Changed State Regions, and the changelog):
- **Renamed:** `STATE_TARTARIA` → `STATE_SARATOV`, `STATE_KAUNAS` → `STATE_LITHUANIA`, `STATE_GALICH` → `STATE_VOLOGDA`.
- **Added:** `STATE_TULA` (split from 1.14.5's `STATE_ORYOL`, whose display name is "Tula"), `STATE_KOSTROMA` (from `STATE_YAROSLAVL` and `STATE_NIZHNY_NOVGOROD`), and `STATE_CHUKOTKA`. 1.14.5 already has `STATE_CHUKOTKA` *and* `STATE_KAMCHATKA`, and the changelog says the two merged, so which key survives is a release-day question (C16).
- **Provinces:** "a lot of provinces were changed or added": Russian lakes removed, northern Kazakhstan redrawn.
- **Cold:** a new `min_cold_effect` / `max_cold_effect` pair on every state region, land and sea. The digest's example is `STATE_ORLEANS`, so the values cover the world. The mod's copies have none (0 of 781 regions).

On 1.15 the mod's map would still define the three old keys (`09_central_asia.txt:135`, `15_russia.txt:74`, `:574`), lack the five new ones, keep the old province lists of ORYOL (`15_russia.txt:379`), YAROSLAVL (`:998`), NIZHNY_NOVGOROD (`:1015`), CHUKOTKA and KAMCHATKA (`14_siberia.txt:143`, `:171`), and strip the cold values from every state on Earth, silently. New province colours would belong to no state, and vanilla's 1.15 state history, strategic regions and on-actions would name states the mod's map lacks.

**Fix:** re-run `resources.py` on the 1.15 install before anything else (it needs the game files; the server skips it without them). It is a pass-through copy, so it picks up the new keys, provinces and cold fields; it inserts its blocks before `naval_exit_id` or the closing brace, which the new fields don't disturb. Two gaps to fix in it first:
- It never deletes a file, so a vanilla file 1.15 renames or drops would leave a stale copy behind.
- It ignores a config key that matches no state without a word (`process_state_block` does `mapping.get(state_name)`). No deposit or trait key is a renamed state today, but `STATE_URALSK` and `STATE_SYRDARYA` sit in the redrawn steppe; make it warn.

Worth testing once the patch is out: whether state regions take `INJECT:STATE_X = { resource = { … } }`. If they do, the mod could ship deltas for about 150 states instead of 17 whole files, and this class of breakage would end. (`resources.py` still carries a commented-out `REPLACE:` line.)

`common/strategic_regions/zzz_modified_strategic_regions.txt` `REPLACE`s `region_canada` and `region_pacific_coast` only; diff both against 1.15.

**References to the affected keys.** Each of the eight (TARTARIA, KAUNAS, GALICH, ORYOL, YAROSLAVL, NIZHNY_NOVGOROD, KAMCHATKA, CHUKOTKA) has 31–40 hits in 11–17 files, none in `events/`, `gui/`, history, loc keys or the player guide, and no file names the new keys yet.

Hand-written, to edit:

| Site | Ref | Change |
|---|---|---|
| `common/geographic_regions/te_formable_regions.txt:56` | KAUNAS, in `geographic_region_intermarium` | → `STATE_LITHUANIA` |
| `common/geographic_regions/te_formable_regions.txt:186` | TARTARIA, in `geographic_region_dar_al_islam` | → `STATE_SARATOV` |
| `common/script_values/tourism.txt:2035`, `:2127`, `:2535` | TARTARIA 45, GALICH 50, KAUNAS 60 in `base_tourism_appeal_value` | rename; a state the list misses falls to the `else` of 20 (`:2686`) |
| `common/script_values/tourism.txt:2647`, `:2583`, `:2587`, `:2019`, `:2075` | ORYOL 40, YAROSLAVL 70, NIZHNY_NOVGOROD 70, CHUKOTKA 30, KAMCHATKA 85 | add TULA and KOSTROMA; fix the merged Chukotka/Kamchatka entry |
| `scripts/analysis/demographics_params.py:418` | KAUNAS in `_THE_GRADIENT` | rename, then rerun `gen_demographics.py` (writes `te_demog_generated_values.txt:1637`) |

Generated, to rerun after `resources.py` (owner; whether it needs the install):

| File | Generator | Install? |
|---|---|---|
| `common/scripted_effects/te_region_area_generated.txt` | `scripts/generators/gen_region_area.py` (reads `provinces.png`; bump `VERSION`) | yes |
| `common/geographic_regions/te_formable_regions_generated.txt` | `scripts/generators/gen_formable_regions.py` (vanilla strategic regions) | yes |
| `scripts/analysis/demographics_state_adjacency.json`, `demographics_strategic_regions.json` | `demographics_adjacency.py --refresh`, `demographics_regions.py --refresh` (harness only) | yes |
| `common/scripted_effects/te_demog_capital_generated.txt` | `scripts/generators/gen_planned_capital.py` (`test_demographics_place.py` fails once `map_data` moves) | no |
| `common/power_bloc_names/te_capital_power_bloc_names_generated.txt` and its loc | `scripts/generators/gen_capital_bloc_names.py` (`test_power_bloc_names.py --check`), plus German and Spanish entries in `i18n/*/tm/te_power_bloc_names_generated.json` for the new states | no |
| `common/scripted_effects/te_seabed_basins_generated.txt` | `gen_seabed_basins` (post-load; `test_seabed_basins.py:21` pins 106 sea regions) | no |

Until they are rerun, each `s:STATE_TARTARIA`/`KAUNAS`/`GALICH` line is an invalid scope at load and its branch does nothing, and the new states get no area, Planned Capital branch, seabed basin or bloc name. The runbook's § 4 generator list lacks `gen_planned_capital.py`, `demographics_adjacency.py --refresh`, the `gen_demographics.py` input and these hand-written lists; add them in the migration.

Unaffected unless 1.15 renames more: the company requirements on MOSCOW, INGRIA and TOBOLSK (`extra_companies_flavored.txt`), the Grand Monuments landmarks and tourism heritage rows, `wonders.txt:302`, and the strait pairs in `colonial_geography_triggers.txt:34-104` (ALAND, CRIMEA, KUBAN, UUSIMAA), which want a look against 1.15's `strait_definitions`.

**Cultures.** `north_caucasian` and `siberian` are gone (§ 0). The mod names neither anywhere (script, loc, Python, JSON), all 48 cultures and 23 religions it names still have 1.15 modifiers, and it ships no pop or state history, so the Synod of Polotsk's pop religions don't touch it. Only `vanilla_parsed/` and the generated `docs/engine/` reports mention the old two, and both are rebuilt in the migration.

### 3.8 New vanilla content the mod collides with or restates

The 1.15 names come from `modifiers.log` (§ 0); how each new law, building or ideology is built (its group, `parent`, methods) is unknown until the files ship (C17).

**Two key collisions, live on the first 1.15 launch.** Each needs an owner decision before Nov 5.

1. **`law_communal_administration`.** The mod defines it bare (`common/laws/extra_laws.txt:4618`, `lawgroup_bureaucracy`: local assemblies and recallable delegates, unlocked by Council Republic, Anarchy or Collective Governance, progressiveness 75), and 1.15 adds a vanilla law with the same key and much the same idea (Clerks in place of Bureaucrats, with a Bourgeois Specialists amendment). Vanilla's file sorts first, so the engine drops the mod's copy as a `Duplicated key`. The mod's other pieces would then hang off vanilla's law: `pm_recallable_delegates` and `INJECT:pm_professional_bureaucrats` (`extra_pms.txt:5028`, `:5046`), the consistency cascade (`extra_law_consistency_generated.txt:2034-2377`), 49 ideology stances (41 in `ideology_modifications.py`, 8 in `extra_ideologies.txt`), `amendment_petition_triggers.txt:121` and the loc (`te_laws_l_english.yml:35-36`). ModState may let the mod's copy win, so the server and the engine would disagree. Options: **adopt vanilla's** and move the mod's method, cascade position and stances onto it with `INJECT`; or **rename the mod's** (with an old-save swap) and keep both.
2. **`building_copper_mine` and the new `copper` good.** The mod has modelled copper as lead: `REPLACE_OR_CREATE:building_copper_mine` (`common/buildings/extra_buildings.txt:1400`) runs the lead mine's method groups, so it outputs lead (renamed "Conductive and Base Metals", `replace/timeline_extended_override_l_english.yml:22`), unlocked by `rural_electrification`. On 1.15 it replaces vanilla's whole new mine, so vanilla's copper has no producer and every vanilla copper input starves. Attached to it: 24 `"Copper"` deposits (`deposits_config.json` via `resources.py`, which would merge into vanilla's copper deposits or duplicate them), `state_trait_copperbelt` and `state_trait_atacama_copper_belt` (`te_mining_traits.txt:30`, `:54`), a hand registration of `building_copper_mine_throughput_add` that 1.15 now registers too (`mod_entity_modifier_types.txt:916`), a same-path icon, `company_vale`, `company_bhp_group` and `INJECT:company_basic_metal_mining` rosters, `test_maintenance_tiers.py:27`, and the player guide (`02-timeline.md:258`, `03-economy.md:95`, `:815-817`). 64 mod methods consume lead (vanilla 1.14.5 has 6), about 40 of them wiring and electronics (`pm_twisted_pair_copper_cables`, `extra_pms.txt:8198`, transistors, the bandwidth tiers, motors). **Recommended: adopt vanilla's copper.** Drop the mine override or rebase it on vanilla's 1.15 mine plus the mod's maintenance and carbon-capture groups, move the electrical lead inputs to copper (keep lead in munitions and glass), point `building_sumitomo_besshi_mine` (`unique_pms.txt:11108`, lead and steel today) and `building_kirgizian_copper_smelter` (`:7351`, iron and coal) at copper, rerun `pm_costs`, and give copper a guide row. This is the patch's biggest design call.

**Copper's other required edits:**
- `REPLACE:company_basic_electrics` (`extra_companies_generic.txt:183`) drops vanilla 1.15's copper mine from that company, as it already drops vanilla's iron mine and rubber extension. The other eight companies that gain a copper mine are only `INJECT`ed with appended lists, so vanilla's addition survives; the three with fixed requirements (Sudamericana de Vapores, A.P. Møller, Škoda) are `INJECT`ed without `possible`.
- `common/scripted_effects/te_bulk_tariff_effects.txt` lists every customs good by hand (lead at `:87`); `test_bulk_tariffs` fails on a 1.15 snapshot until copper joins, and `gen_tax_code.py` (which reads `vanilla_parsed/common/goods.json`) wants a rerun that adds copper to the customs schedule and `te_tax_generated_rows.gui`.
- The three vanilla production methods the mod `REPLACE`s in the electrical chain (`pm_telephones`, `pm_radios`, `pm_electric_trains` at `extra_pms.txt:8169`, `:8396`, `:13938`) and `REPLACE:building_electrics_industry` (`extra_buildings.txt:376`) would drop any copper input 1.15 adds there; diff them, and the mod's other 49 `REPLACE`d methods, against 1.15.
- Dynamic and fine: `pm_costs`, the emissions generators, the Strategic Reserve roster (8 fixed goods), the banking basket.

**Vanilla entities the mod restates whole, which would roll 1.15 back.** Each is regenerated from the 1.15 files, not edited:
- **142 ideologies**: `common/ideologies/modified.txt` holds 142 `REPLACE:`s (and 16 `INJECT:`s) of whole 1.14.5 vanilla ideologies plus the mod's stances, written by `apply_ideologies.py`. Until rerun on the 1.15 install, they put back 1.14.5's Trade Unions stances (including on Council Republic), undo the Patriotic/Militarist split and the reworked Communist and Labour movement ideologies, and give no stance on any new law. Do **not** use `scripts/generators/regen_ideologies_offline.py` here: it replays the committed 1.14.5 bodies and would lock the rollback in. After the rerun, check the mod's `ideology_modifications.py` edits don't override a stance 1.15 changed on purpose.
- **11 parties' `join_weight`**: `common/parties/zz_te_party_join_weights.txt` (`gen_party_join_weights.py`, needs the install) restates 1.14.5's; the `INJECT` replaces the whole field.
- **The law consistency walk**: `extra_law_consistency_generated.txt:1594-1611` evicts Command Economy unless the country holds one of 1.14.5's six unlocking laws, so a Council Republic, which 1.15 allows Command Economy, loses it monthly. `gen_law_consistency` needs only the rebuilt snapshot.
- **Citizenship**: `common/laws/modified.txt:77-536` `REPLACE`s all six citizenship laws; nothing diffs them against vanilla.
- **Full-file overrides**: `common/buy_packages/00_buy_packages.txt` (`pop_needs_curves.py`) and `common/production_method_groups/13_construction.txt`.
- **`REPLACE:amendment_tradition_of_free_elections`**, which drops anything 1.15 adds to its `allowed_laws`, and the verbatim `formation.17`.

**Probable renames** (§ 0; confirm with C17). Of 1.14.5's 48 character ideologies, every one but `ideology_child` gets a 1.15 `interest_group_ideology_<x>_leader_chance_mult` except `ideology_social_democrat` and `ideology_communist`, and two keys with no 1.14.5 ideology appear: `state_socialist` and `communist_leader`.
- `ideology_social_democrat` (→ `ideology_state_socialist`?): 37 references in 11 files, 11 of them hand-written (`extra_amendments.txt:705` `would_sponsor`; `cultural_hegemony_triggers.txt:248`; `te_inheritance_triggers.txt:62`; the three mod parties `green_party.txt:150`, `populist_party.txt:284`, `technocratic_party.txt:233`; `heir_education_effects.txt:441`, `:458` `set_ideology` and its gate `heir_education_triggers.txt:49`; two `ch_model_*_tt` loc lines), plus `REPLACE:ideology_social_democrat` (`modified.txt:2613`), 24 generated join-weight lines and `ideology_modifications.py:1339`.
- `ideology_communist` (→ `ideology_communist_leader`?): 13 hand-written references (`irredentism_events.txt:632`, `:644`; `modern_election_events.txt:1265`; `irredentism_triggers.txt:131`; `cultural_hegemony_triggers.txt:210`, `:244`; the three mod parties; `irredentism_values.txt:100`; `heir_education_effects.txt:443` and its gate), plus `REPLACE:ideology_communist` (`modified.txt:6027`) and 18 join-weight lines.
- `social_democrat_party` (the changelog's "Socialist Party"): First Past the Post hard-codes the eleven parties (`te_fptp_triggers.txt:58-75`, `te_fptp_effects.txt:71-146`), and `test_first_past_the_post` pins them. If the key changes, `INJECT:social_democrat_party` (join weights) targets nothing.
- `test_apply_ideologies.test_replaces_touch_a_vanilla_block` fails on a 1.15 snapshot without `ideology_social_democrat`.

**The ten new laws in law groups the mod extends.** None of the other nine keys appears in the mod. Likely groups: Labour Suffrage in distribution of power; Military Bureaucrats (and Communal Administration) in bureaucracy; Revolutionary Guard in army model; Extraordinary Commission, Okhrana and Third Section in internal security (the last two probably Russian variants, `parent = law_secret_police`, like `law_shinsengumi`); Caesaropapism in church and state (probably a variant of `law_state_religion`); Official Nationality in citizenship or church and state; Internal Colonisation in colonization. On a 1.15 snapshot:
- **`ideology_lawgroup_audit --strict` (CI) fails**: about 78 blocks miss the new non-variant laws (50 in `extra_ideologies.txt`'s 32 ideologies, plus 15 bureaucracy and 13 army model blocks the mod adds to vanilla ones). The rule also runs backwards: a new vanilla ideology (State Socialist, Militarist, Tsarist, Disciplinarian, Militant) with a block in a group the mod extended must name the mod's laws there. Stances go in `ideology_modifications.py`, then `apply_ideologies.py` with the install.
- **`test_first_past_the_post.test_petition_names_every_voting_law` fails**: `te_ap_enacting_in_distribution_of_power` (`amendment_petition_triggers.txt:151`) lacks Labour Suffrage. Its bureaucracy and citizenship siblings (`:114`, `:45`) have no test but the same gap.
- **Machine rule's lock**: Automated Bureaucracy's "only valid law" rule (`mod_systems.md:1708`) relies on every human-staffed bureaucracy law listing `law_algorithmic_governance` in `disallowing_laws`; new vanilla bureaucracy laws won't, and their methods may need adding to `INJECT:pm_professional_bureaucrats`'s.
- **Lists of voting and repression laws**: Over 30 mod files enumerate `law_universal_suffrage` (59 plain `has_law`, 19 `has_law_or_variant`, 33 list entries). Covert election interference, for one, requires a landed, wealth, census or universal law (`covert_operations.txt:146-149`, `:200-203`), so a Labour Suffrage country could never be targeted. `un_regime_human_rights_violator` (`un_regime_triggers.txt:59`) lists repression laws and should take the Extraordinary Commission. If Okhrana, Third Section or Caesaropapism are variants, the 12 plain `has_law = law_type:law_secret_police` and 26 plain `law_state_religion` reads miss them.
- **The mod's per-law `INJECT`s**: it gives each law in these groups its own modifiers (Legislative Override Capacity, cultural pull, tourism, intelligence capacity, SoL expectations, judiciary, colonial terms: 8 bureaucracy, 13 internal security, 41 distribution of power, 14 church and state, 3 colonization `INJECT`s). The new laws get none until added.
- `gen_law_consistency` picks the new laws up from the rebuilt snapshot (its group order list already has every group).

**IG rosters.** The "Nomenklatura Interest Group" is probably the Intelligentsia renamed, not a ninth type: 1.15's `modifiers.log` has exactly the eight `interest_group_ig_*_pol_str_mult` types and no "nomenklatura" string. If it is a ninth type after all (C17), the eight-group rosters need it: `gen_tax_code.py:269-296` (`IGS`, `EXPOSURE`), `ig_feminism.py:215-245`, `gm_values.txt`, `heir_education_effects.txt:545-676`, `heir_education_buttons.txt:571`, the approval tables in `extra_modifiers.txt` (around `:8030-8367`) and `demographics_params.py:267-270`.

**Smaller items:**
- Armed Forces ideology lists miss a new Militarist or Tsarist: `un_regime_triggers.txt:184-185`, `ai_strategies/edited_default_strategy.txt:173-179`. The mod's Armed Forces stances sit on `ideology_patriotic` (`ideology_modifications.py:989`).
- Cossack Hosts (`bg_cossack_host`) need a class in the Demographics workplace lists (`te_demog_triggers.txt:59-87`, `gen_demographics.py`'s rural groups) and `resettlement_pop_urban_worker` (`resettlement_triggers.txt:140-150`), unless 1.15 parents the group under a subsistence or agriculture group.
- Vanilla JEs the changelog replaced or made global (`je_vanguard`, `je_communist_welfare`, `je_5_year_plan`, `je_anarchy`, the Caucasian War, Steppe, Canada, Australia and Hungry Forties entries, `je_great_game_control`): the mod names none (only `docs/vanilla/vanilla_known_bugs.md:148` mentions `je_vanguard`).
- No other collision: the mod's 513 buildings, its goods, events, effects, triggers, on-actions, custom loc and regions match nothing new. The four "new" cavalry types already exist in 1.14.5 (only their offense modifiers are new). The mod has no `c:POL` content, its one `c:RUS` block is a history block of mod laws, and the `STATE_GEORGIA` hits are the US state, so the new Georgia formable doesn't collide.

### 3.9 Art the 1.15 schema makes mandatory

| Field | Mod entities that lack it | Fix |
|---|---|---|
| Journal entry group `illustration` (1108×200 `.dds`; optional `themed = yes`), used in each member entry's header | All three groups in `common/journal_entry_groups/timeline_extended_je_groups.txt`: `je_group_soft_power` (`je_cultural_hegemony`), `je_group_covert_warfare` (`je_covert_warfare`) and `je_group_environment`, which **no entry uses** (`mod_systems.md:109` says so too) | Two illustrations, or vanilla's own paths as placeholders (C15). Delete `je_group_environment` with its loc (`te_journal_entries_l_english.yml:447`) and translation entries rather than draw art for it |
| Mobilization option group `background` (780×224) | `training` (`common/mobilization_option_groups/extra_mobilization_groups.txt:1`), used by six mod options (`extra_mobilization_options.txt:1325`, `:1370`, `:1415`, `:1467`, `:1519`, `:1578`) | One background. Check whether `icon` is still read: the digest's example has none |
| Objective `illustration` (1108×300) | none: the mod defines no objectives | — |
| `gene_asian_east` in character DNA | none: the mod has no DNA, templates or ethnicities, and its 42 `create_character` calls (space-race events) pass no `dna` | — |

The mod's other 31 entries use six vanilla groups (`je_group_foreign_affairs` ×15, `je_group_internal_affairs` ×12, `je_group_technology`, `je_group_russia_great_reformer`, `je_group_british_india`, `je_group_historical_content`) and get vanilla's art. Check those keys survive 1.15; `je_group_russia_great_reformer` (the tax code's `REPLACE:je_great_reforms_bureaucratic`) is the one at risk, given the Russia rework. Likewise the six vanilla mobilization groups the mod's options use (`supplies`, `supplements`, `transport`, `reconnaissance`, `special_weapons`, `medic_support`).

Each new texture goes through the usual checks: block-compressed dimensions a multiple of 4 (1108×200, 1108×300 and 780×224 all are; `check_dds_dimensions.py`), and `texture_reference_audit`, whose `DECLARED_FIELDS` registry (`texture_reference_audit.py:260`) should gain `journal_entry_groups: illustration`, `mobilization_option_groups: background` and `objectives: illustration` with the 1.15 snapshot, so it catches the next group that lacks one.

### 3.10 Loc: `|q` in function arguments

A loc function whose string argument holds a `$key$` reference now needs it escaped, `[Concept('concept_province','$concept_provinces|q$')]`, and errors otherwise. The mod has **261 such references on 180 lines in 13 files** (none in `.gui` files, none escaped yet): `Concept` 257, `ConcatIfNeitherEmpty` 3, `GetRawTextTooltipTag` 1. The heaviest files are `te_power_bloc_unlocks_l_english.yml` (146), `te_miscellaneous_l_english.yml` (53) and `replace/timeline_extended_override_l_english.yml` (15). Every argument is a lone `'$ref$'`, so `'\$([A-Za-z0-9_.\-]+)\$'` → `'$\1|q$'` catches exactly the 261 (read and write `utf-8-sig`); don't use a line grep for quoted text, which pairs prose apostrophes with argument quotes and matches 472 lines.

**This can land before Nov 5**: vanilla 1.14.5 already writes `|q` 35 times, twice inside `Concept` (`COASTAL_BUILDING_MARKER_SUBHEADER_BLOCKADE`). It must change together with:
- `gen_pb_principle_unlock_descs.py:52-60`, a post-load regenerator that writes 102 of the 146 power bloc references; a hand edit would be reverted on the next `/reload`.
- The German and Spanish translation memories (`i18n/{german,spanish}/tm/*.json`, about 254 references each, in both the `en` and the translated field). Adding `|q` counts as a minor change (`translate_loc.py:234`), so the deploy would keep the old, unescaped translation and non-English games would hit the error. Rewrite both fields, and the unescaped examples in `i18n/*/BRIEF.md:53-57`.
- `loc_render_audit.py:131`, whose `\$([A-Za-z0-9_.]+)\$` doesn't match `$x|q$`, so it would stop checking these references. Allow `(?:\|[^$]*)?`, as `organize_loc.py:907` does.
- The vanilla keys copied into `replace/timeline_extended_override_l_english.yml` (`concept_harvest_condition_desc`, `CAN_EXPAND_BUILDING_TOOLTIP`, `EXPANSION_PROFIT_IMPACT`, the locked principle slot tooltips, …): re-sync them to 1.15's text. `CAN_EXPAND_BUILDING_TOOLTIP` has already drifted from 1.14.5's.

`decolonization_war_effects.txt:605`'s `GetVariable('decol_iw_talks_$N$')` is a script argument inside a quoted string, not a loc reference; § 3.11 covers it.

### 3.11 Script semantics and defines

**Documentation that changed for names the mod uses** (doc bodies diffed between the two digests, ignoring "Value Type" lines and the regional iterators' garbage bodies): nothing the mod writes stops working.
- `create_dynamic_country` now takes `color = random` or a colour list, and no longer needs an origin country. The mod's 12 calls (`decolonization.txt:455-728`) still work; their 12-branch hue `random_list` could become `color = random`.
- `exile_character` gained the block form for regional pools (§ 4.7); the mod's 2 `= yes` uses still work.
- `pop_type_percent_country` takes `target`/`value` now; the mod has no use. `primary_cultures_percent_state`/`_country` already take the target country in 1.14.5, which the mod passes. `has_employee_slots_filled` appears only in comments. `is_coastal`, `has_any_strait_province`, `add_journal_entry`, `post_notification` and `activate_law` are unchanged.
- The six `market_*` triggers accept `goods = …`, `on_country_formed`'s scope is now `country` (what the mod already assumes), and the `religion` and `modifier` event targets gained inputs. Nothing to do.
- 106 `goods_output_*` modifier types moved to a `goods_output` mask. The mod uses 93 of them; only the rendered engine docs change (a new "By Mask" group).

**"Fixed script arguments being substituted inside quoted strings."** The mod's exposure is 45 `$ARG$` tokens on 20 lines in 12 scripted-effect helpers (`gm_landmark_effects.txt`, `gm_trophy_effects.txt`, `nuclear_crisis_effects.txt`, `gm_commission_effects.txt`, `gm_monument_effects.txt`, `sr_colony_module_effects.txt`, `decolonization_war_effects.txt`, `te_debug_tax_effects.txt`), and **every one is a `debug_log` string**; none is in a `text`, `desc`, name, flag, tooltip or GUI. `scripting_best_practices.md:1902` already records that 1.14.5 substitutes inside quotes but garbles it (`"(kind $KIND$)"` logged `(kind1$)`), so the likeliest reading is that 1.15 makes it correct. Two readings to tell apart in the first 1.15 `debug.log` (C19):
- *Substitution now correct:* the lines print properly, and `decol_iw_end_talks`'s `GetVariable('decol_iw_talks_$N$')` (`decolonization_war_effects.txt:605`) starts reading the variable it names. The best-practices rule and the `sr_window_log_copy` workaround (`sr_launch_window_effects.txt:322-330`) could then be relaxed.
- *No substitution inside quotes:* the lines log a literal `$KEY$`, and if the engine also stops counting a quoted `$X$` as a parameter, `gm_debug_log_landmark_pm` (KEY only at `gm_landmark_effects.txt:384`) and `te_tp_observe_controls` (KIND only at `te_debug_tax_effects.txt:300`, called from `te_monetary_arrangement_effects.txt:966` and `banking_policy_effects.txt:120`) log `failed for unknown arguments` at every load. `script_helper_index.PARAM_RE` (`script_helper_index.py:35`) would then disagree with the engine.

Either way, the 20 lines break the house rule today and print garbled `TE_SELF_CHECK` names (`nd_trade_$CODE$`); fixing them (branch on the argument, or copy it into a variable first) is worth doing before Nov 5, with an offline check for `$X$` inside `debug_log` strings so it doesn't recur.

**Fixed engine bugs the mod tunes around** (none needs retiring on the day):

| 1.15 fix | Mod exposure | Action |
|---|---|---|
| Kill-rate modifiers were counted twice in battles | 29 `unit_kill_rate_add` uses: 19 mod combat unit types (0.08–0.5, `extra_combat_units.txt`), 4 laws, 3 battle conditions, 2 static modifiers, 1 PM | Every source now hits half as hard. If vanilla rescales its own units (1.14.5: cannon 0.1, shrapnel 0.3, chemical weapons 0.5), mirror the ratio; take `scripts/snapshot_balance.py` first (runbook § 1) |
| Timed modifiers and scaled effects took wrong values when the scale read a saved scope | 2 timed modifiers in the population transfer (`extra_effects.txt:1535`, `:1555`, `multiplier = scope:source_country.var:…`); the guard at `extra_treaty_articles.txt:2518-2530`; `scripting_best_practices.md:479`, `:481` | Check the decay reads right on 1.15, then correct the doc bullets |
| Halved trait effects of marginal interest groups now apply | `scripting_best_practices.md:223` and `vanilla_politics_reference.md:275` already assert the halving | Say it holds from 1.15 only. The Demographics self-check already skips marginal groups |
| `military_formation_interest_gain_mult` "now applies from any source" | `extra_institutions.txt:35`: +0.1 per institution level, up to +90% at the mod's investment cap of 9 | Probably goes live on 1.15; check and re-tune |
| `has_employee_slots_filled` compared its operands in the wrong order | Comments only (`te_construction_market_sector_placement_values.txt:45-50`, `:68`), which blame something else; the `occupancy` workaround keeps working | Correct the comment |
| IGs opposed to a law refuse to negotiate when it would fail without them, or at 0% | 200 `would_sponsor` lines in the mod's amendments | Negotiated sponsorship of mod amendments may get rarer; every amendment keeps its scripted way in, so none goes dead |
| Ideologies now show stances for law variants; invisible laws drop out of the list | `ideology_lawgroup_audit.py:10-36` treats `variant_stance` as unread in game | The 1.15 panel may settle that open question; look |

Negative `random_list` weights, the pause on a missing popup, 0% reform chance and the neutral-approval display: no mod exposure.

**Defines (C18).** The mod overrides 56 keys in `common/defines/extra_defines.txt` (and one in `te_construction_market_defines.txt`). We can't see 1.15's, so re-read these against vanilla's new `00_defines.txt`, highest risk first:
1. **`CULTURAL_FERVOR_ASSIMILATIOM_EFFECT` (`:69`)**, which copies vanilla's misspelt key. "We fixed the assimilation defines this time" may mean the key is renamed, which would leave the mod's 0.0075 silently dead (the engine logs only `define macro is missing`). Re-read `ALLOW_ASSIMILATION_IN_HOMELANDS` (`:60`) and the cultural-community acceptance deltas (`:63-64`) with it.
2. **`INCOHERENCE_FACTOR = 2` (`:36`).** The changelog halves the legitimacy cost of ideological incoherence; if vanilla did it through this define, the mod's copy cancels it. The player guide states the cost (`06-politics.md:644`).
3. **The three devastation rates (`:52-54`).** 1.15 moves devastation to battles with recovery after the last one; the mod's rates may now mean something else or point the wrong way.
4. **`NUM_WEALTH_LEVELS = 200` (`:58`, vanilla 99)** against the slower SoL radicalisation: a per-level rate tuned for 99 levels is doubled on 200. `gen_demographics.py:932` asserts on it.
5. **The pop growth and mortality curve (`:126-147`)** against the higher crop-failure lethality, and the starvation constants Demographics mirrors (runbook § 6b).
6. **AI production-method stickiness (`:30-32`)**, which `test_deep_sea_rebalance.py:61` and `test_emissions_control_ai_value.py:57` pin against vanilla's 0.75.

A quick catch-all on the day: grep `debug.log` for `define macro is missing` against all 56 keys. Naval combat, infamy, war support and unit disbanding have no mod defines.

**Engine-doc tooling: a hazard now, before the patch.** With the 1.15.0 digest published, a server cold start on any machine without a pinned `vanilla_snapshot_docs_path` switches to the 1.15 engine docs while the game is still 1.14.5:
- `path_constants._derive_digest_docs_path()` picks the highest all-numeric digest folder (`_semver_key` skips the `-openbeta` ones, #332). Until 2026-10-29 that was 1.13.11, which the render guard refused as older than 1.14.5; now it is 1.15.0, and every cold start fast-forwards the clone first.
- `_engine_docs_render_blockers` (`mod_state_server.py:3851`) blocks only an *older* source, so the reload re-renders the committed `docs/engine/` files from 1.15 (about +3,300/−880 lines over 10 files in a dry run). The `[VERSION MISMATCH]` notice is a log line only.
- `prev_scope_audit`, `localization_accessor_audit`, `je_multiplier_scope_audit` and `empty_effect_audit` would then judge 1.14.5 script by 1.15's names, so 1.15-only names (`enact_law`, `add_decree`, `in_tropics`, `cold_effect`) would validate while the game rejects them. No name the mod uses disappears.
- The owner's machine appears to pin a 1.14.5 snapshot (a 2026-10-02 plan in `docs/superpowers/plans/` names one); cloud sessions and fresh machines don't. **Fix before Nov 5:** block (or loudly warn on) a render whose source is newer than `vanilla_parsed/manifest.json`'s `game_version`, and until then set `VIC3_VANILLA_DOCS_SNAPSHOT` to a 1.14.5 folder. On the day, the reverse: point it at 1.15.0 (or let it follow the digest) only after `vanilla_parsed.py build` on the 1.15 install.
- `effect_trigger_validity_audit.py bootstrap` has no dry run, and **without a game install it shrinks the catalog** to the summary names (it harvests vanilla's left-hand keys from the game files). Never run it in a game-less container. `bootstrap-context` reads only `vanilla_snapshot_docs_path` and fails when it is unset, so it never follows the digest; point it at 1.15 by hand. `fold_vanilla_loc_accessors.py` needs the 1.15 loc, since the digest's data types are stale.

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
- The value's scope (C7) decides whether the existing JE-safe script values (`*_for_je`, `root.var:`) carry over, and `je_multiplier_scope_audit` must follow (§ 3.5). The digest's readme puts the value's root on the owning country, unlike a `je:` modifier's stored multiplier, so they should; one country-only read in game confirms it.

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

- `events/un_events.txt:3809`: the International Criminal Court convicts a leader (`scope:un_icc_accused = { exile_character = yes }`). The first idea was a pool nobody can reach, with a sentence (`years = N`), read as detention in The Hague. **C9 rules that out:** a pool no country can access is emptied into the global pool each quarter and its exiles lose their return date. A pool needs at least one country that passes `has_access`, and that country can invite from it, so detention would have to be a pool only the UN headquarters' host can reach, which then holds the right to invite the convict. Read vanilla's Siberian pool (the readme's example key is `siberian_exile_pool`) for how 1.15 frames a pool its owner controls.
- `common/scripted_buttons/timeline_extended_scripted_buttons.txt:5628`: founding a custom religion exiles the Devout leader. A pool only co-religionist countries can reach fits.

Two systems could use a pool they don't have today:

- **Penal Labor Camps** (`law_penal_labor_camps`, `mod_systems.md` § Penal Labor Camps): a pool for agitators the law sends away, which only the country itself can reach, with a term. This is the Siberian exile pool's own shape, so it survives C9: the country passes `has_access` while it exists.
- **Covert warfare**: a defector or a burned agent going to the country that ran the operation, through a pool only that country (or its bloc) can reach.

Each pool needs its loc key (the tab name in the Invite Exile screen) and a `has_regional_exile_pool_access` check wherever the mod looks for an exile.

### 4.8 Glossary

The glossary is for setting vocabulary, not mechanics, and the mod's 196 game concepts are almost all mechanics (banking, the UN, covert warfare). Plain-text terms that would fit, from a sample search of English loc: Kessler syndrome (7 lines; the mechanic is `concept_orbital_debris`), Non-Aligned Movement (5), Realpolitik (3), *zaibatsu* (2), *dirigisme* (2). Vanilla 1.15 ships `glossary_zaibatsu` itself (one of the 20 entries `changes_data_types.md` lists), so the mod's two lines can link it, `[glossary_zaibatsu]`, with no definition of their own. Worth a rule more than a project: a new historical or setting term in event text becomes a glossary entry, not a concept. `scripts/analysis/concept_term_audit.py` could learn glossary names now the link syntax is known (C12: `[glossary_x]` or `[Glossary('glossary_x','text')]`).

### 4.9 `play_music_cue`

It plays an existing cue, and the mod ships no music (no `music/` folder), so this means picking vanilla cues for a handful of moments: the first nuclear detonation, the Moon landing, a world war breaking out, a climate tipping point. Low value; do it with an event pass, not on its own.

### 4.10 Regnal numbers

Nothing to change. The mod's 12 government types (`common/government_types/timeline_extended_governments.txt`) are all parliamentary, presidential or dictatorial, so none numbers its rulers, and a formable the mod adds starts its own numbering. Heirs in the Heir Education panel should gain their numeral without edits (C11).

### 4.11 Smaller modding additions

From the 1.15 engine dumps and readmes (§ 0), checked against the mod. Ranked; the ones with no good candidate are listed so nobody looks again.

- **Treaty articles.** Three new things, all from `types/treaty_articles.md`:
  - **Renegotiation re-runs `on_entry_into_force`.** An article *with* `can_be_renegotiated`, or one newly added, now runs its entry effect again when a renegotiated treaty enters into force, with `scope:is_renegotiation` set. Four mod articles add a state modifier there with no guard, and a same-name `add_modifier` stacks: Demilitarized Zone (`107_dmz_and_disarmament.txt:72` → `te_demilitarized_zone_state_apply`, `treaty_article_effects.txt:224`), Minority Protection (`102_minority_protection.txt:93`), Free Port (`103_free_port_concession.txt:85`) and Religious Mission (`106_religious_mission_rights.txt:109`). A renegotiated DMZ could carry the modifier twice (−200% conscription). Intelligence Sharing (`extra_treaty_articles.txt:1680`) would charge its +1 infamy again. Guard each with `exists = scope:is_renegotiation`, or make the apply effects remove before adding, which is safe on 1.14.5 too. Check whether 1.14.5 already does this, and whether the old article's withdrawal effect runs first (C20).
  - **`is_one_time`** (the AI withdraws once the binding period ends from a treaty that mainly gave it one-off articles): Disband Company, Seize Company, Return Cultural Property, Surrender Monument and the population transfer pay upkeep for a one-off effect.
  - **`can_propose`** (checked on the whole treaty when proposed, not when the article is added to a draft): fits the three articles that need something else in the same treaty, `science_aid_2`, joint military exercises and the nuclear guarantee. **`show_in_lens`** (the new treaty-article lens): 31 mod articles without required inputs qualify.
- **The disallow modifiers fit the peace terms.** Forced Disarmament (`107_dmz_and_disarmament.txt:308`) dismantles military buildings once but spares shipyards, so nothing stops the country rebuilding a fleet; `country_disallow_military_ship_construction_bool` closes that and still allows supply ships. The DMZ's state modifier (`extra_modifiers.txt:5354`) expresses "no army here" as −100% conscription and a −1000 barracks cap; `state_disallow_barracks_construction_bool` says it in one readable tooltip line. Update the rows in `09-diplomacy.md:90-91` with either. `country_disallow_army_creation_bool` has no obvious user (a UN arms embargo, perhaps).
- **`progress_condition`** (§ 2 C5): `civil_rights_support_bar` (`extra_progress_bars.txt:233`) has 13 `if`-wrapped factors that convert one for one, and the panel would tick off each, so the player sees what is left. The colonial stability bar is a weak case: its gates sit in named script values on purpose, and a factor read from a named value is counted but not listed. Only 2 of the 8 bars have monthly progress at all. Needs the rebuilt `journal_entry.gui` (§ 3.4).
- **Power bloc effects** (`add_power_bloc_mandate`, `change_power_bloc_name`, `destroy_power_bloc`, `leave_power_bloc`, `on_power_bloc_formed`): they make `scripting_best_practices.md:3999` and `:4001` and the comment at `extra_on_actions.txt:3556` wrong once 1.15 ships (each says no such effect exists, true of 1.14.5); correct them in the migration. Uses are small: the debug fast-mandate toggle, a possible refund on the principle remove button (`te_power_bloc_sguis.txt:9`; the guide says there is none, `09-diplomacy.md:319`). The monthly UN bloc-vacuum check gains little from the on-action.
- **`enact_law`** (a successful enactment, with `on_enact`, movement loyalists and IG approval): of the mod's 647 `activate_law` lines, about 635 must stay (458 in the generated consistency walk, 96 history, 19 save repairs, cascades, setup, debug). Six events stand for a real political decision and could use it: `cultural_hegemony.16.a`, `extra_law_events.36.b`, `decolonization_events.75.a`/`.c`, `te_judiciary_events.5.a`, `te_peg.3.b`. Test first whether it respects `can_enact` and an enactment already running in the group (C20).
- **`disable_evaluation`** (drops an inactive entry for good for a country that can never qualify): about 24 mod entries are gated on a game rule, plus the retired Moon Base. A game rule never changes mid-game, so it is the safe kind of identity check. Never use `is_country_type = decentralized` there: the mod turns decentralized countries into recognized ones (`decolonization.txt:465-561`).
- **Scripted button `cost`, `tags`, `autocomplete`, `icon`.** Of 376 buttons, 194 are AI-only and most player-visible ones (141) are the custom-religion builder, while players use scripted-GUI copies in the widgets. `tags` could in principle replace about 150 of those copies, but buttons bind when the entry activates (`st_res_scripted_gui.txt:5049`), so not yet. No candidate for `cost` or `autocomplete`. `cost` and `icon` render only in the rebuilt `journal_entry.gui`.
- **`fire_only_once` / `fire_only_once_globally`**: low value. 36 events guard themselves with a never-removed country variable (23 society-technology, 7 judiciary, 6 others), 32 of which nothing else reads. Converting them would re-fire all 32 in 1.14.5 saves, and probably for a revolution's winner, which inherits variables but likely not a fire record (the mod's "the winner continues the nation" rule). Keep the variables; use the flag for new one-shots. Never use `_globally` on the 11 Global Warming threshold events, which go to every country under one global flag.
- **New triggers and event targets**: `in_tropics` fits `environmentalism_events.14` (tropical disease, which can fire anywhere today) and a regional variant of the uniform `global_warming` modifier; there are no hand-made latitude lists to replace. Vanilla's `global_average_gdp_per_capita` makes the mod's `global_gdp_per_capita` (`extra_script_values.txt:1588`) redundant, and it has no reader anyway: delete it. The interest group leader-chance modifiers are a gentler alternative to the `set_ideology` leader flips in the environmentalism events. `cold_effect`: see § 6.
- **Birth rate by stratum and acceptance status**: no workaround in the mod to retire; § 6 covers the Demographics side.
- **No candidate**: `add_decree`/`remove_decree`/`replace_decree` (15 mod decrees, all lapse through their `state_trigger`); `hidden = yes` on modifier types (the mod keeps script-only types visible on purpose, and `hidden_modifier_audit` is about tooltips); institutions' `dynamic_name`; character roles' `can_be_interest_group_leader` and `character_background` (the mod defines no roles); AI regional objectives' `country_target`/`state_target` (none defined, but the mod's `REPLACE` in `te_stake_colonial_claim.txt:267`, `:304`, `:338` calls vanilla's `ai_is_regional_objective_state`, so take vanilla's version in the re-diff); strait `grievance_mult`; weighted music and loading screens (the mod ships neither); objectives' `associated_journal_entries`; the overlord-law, interest-tier and socialist-hostility modifiers (design options only).

## 5. Order of work

Before Nov 5 (each can merge to `main` ahead of the patch, because it works on 1.14.5 too):
1. **Guard the engine-doc render** (§ 3.11): refuse, or warn loudly on, a render whose source is newer than `vanilla_parsed/`'s `game_version`. Until it lands, pin `VIC3_VANILLA_DOCS_SNAPSHOT` to a 1.14.5 folder on any machine that starts the server.
2. **The `|q` conversion** (§ 3.10): the loc files, `gen_pb_principle_unlock_descs.py`, both translation memories and `loc_render_audit.py` together.
3. **The two owner decisions** (§ 3.8): `law_communal_administration` (adopt vanilla's or rename the mod's) and copper (adopt vanilla's, recommended). Both shape the release-day work.
4. **Art** (§ 3.9): two journal entry group illustrations (1108×200) and one mobilization group background (780×224); delete `je_group_environment`.
5. **`resources.py`** (§ 3.7): delete stale state-region files, and warn on a config key that matches no state.
6. **The 20 `debug_log` lines with `$ARG$` inside quotes** (§ 3.11), and the renegotiation guards on the four treaty articles (§ 4.11), which are correct on 1.14.5 either way.
7. Write the journal entry converter (§ 3.1) and its test; review its dry-run output.
8. Draft the 45 `conclusion_desc` texts.
9. Teach the tooling both shapes (§ 3.5), so audits pass before and after the conversion and the release-day diff is script only; give `effect_trigger_validity_audit`'s journal entry root the outcome keys and contexts.
10. Make sure the vanilla clone holds 1.14.5 (runbook § 0), for the GUI rebuilds and `REPLACE:` re-bases.
11. Run `scripts/snapshot_balance.py` (runbook § 1).

On release day, on a `vanilla-1.15` branch, on the machine with the game:
1. C19's first launch, with the generators off, and read `debug.log`.
2. Runbook §§ 2–4: digests, `vanilla_parsed.py build`, the engine-doc refresh (now from 1.15 on purpose), the catalog re-bootstraps. **`resources.py` first among the generators** (§ 3.7), after C16 has updated `deposits_config.json` and `state_trait_config.json`; then the map generators (`gen_planned_capital`, `gen_capital_bloc_names` and its translation entries, `gen_region_area`, `gen_formable_regions`, `demographics_regions`/`demographics_adjacency --refresh`), and the hand edits to `te_formable_regions.txt`, `tourism.txt` and `demographics_params.py`.
3. `apply_ideologies.py` (not the offline replay), `gen_party_join_weights.py`, `gen_law_consistency`, `gen_tax_code.py`, `pop_needs_curves.py`, `ig_feminism.py` (§ 3.8), then the copper and Communal Administration work as decided.
4. C1–C5 and C15–C18, recorded here.
5. The converter (§ 3.1), the five vanilla entries (§ 3.2), the bars (§ 3.3), the GUI rebuilds (§ 3.4), the new-law stances and lists (§ 3.8), the defines (§ 3.11), the remaining runbook steps.
6. Every check green; `POST /reload` with no new warnings; in game, every mod journal entry opens, shows its outcomes and bars, and its widgets mount; Russia loads with the new states.
7. Merge once the mod loads on 1.15. Players on 1.14.5 can't load outcome syntax or the new state keys, so the merge goes with the patch, not ahead of it.

After the migration: C6–C10 and C20, then § 4 in order, then § 6's decisions.

## 6. Where 1.15 overlaps the mod without needing a change

Systems, rebalances and UI that touch the mod's design. None blocks the load; each is a decision or a check for after the migration. Ranked by value.

**Copper as a Strategic Reserve good.** Once § 3.8's copper decision is made, copper is a natural stockpile good, and the `add-strategic-reserve-good` skill's mult-axis gap doesn't apply (vanilla registers `goods_input_copper_mult` and `goods_output_copper_mult`). Power-grid transfer stations and the generation buildings (renewable, hydro, nuclear, fusion) are the natural copper sinks.

**Demographics.**
- 1.15 adds birth-rate modifier types per stratum and per acceptance status. Under the Full rule the census sets births from its own model, absorbing the engine's law, technology and institution birth lines (`te_demog_engine_line_injections.txt`) and netting out only literacy and mild starvation per pop. A per-stratum or per-acceptance line that vanilla 1.15 *content* uses would apply on top, unmodelled, and the yearly residual would book the extra births as migrants. On release day, grep vanilla for users of the new types; absorb any, and add rows to runbook § 6b.
- "Crop failures more lethal" may move the starvation values the census mirrors (`starvation_penalty`, `severe_starvation_penalty`, `FOOD_SECURITY_*`; runbook § 6b) and compounds with Global Warming's harvest multipliers (drought and flood +0.25, heatwave and wildfire +0.5 per unit).
- **Up to four world market hubs per market area.** `te_demog_mt_t_gateway` adds `te_demog_k_mt_hub = 30` to each hub state (`te_demog_metro_values.txt:80-86`), calibrated on one hub per area, so more states' metro targets rise. The self-check `metro_world_market_hub` (`te_demog_metro_effects.txt:93-160`) passes only if hubs ≤ countries; a 2026-10-25 game already had 234 hubs, so 1.15 could raise a false BROKEN. Re-derive both. The three financial harvest conditions that count hubs as eligible (`financial_panic`, `market_downturn`, `bull_market`, `extra_harvest_condition_types.txt:16`, `:83`, `:134`) will fire more often.

**Cold and Global Warming.** 1.15's cold is fixed per state region; the only script hook is the read-only `cold_effect` trigger, with no effect or modifier to move it. Global Warming can't thaw anything, so leave it alone and say in the climate chapter that warming doesn't change winter sea ice. `global_warming`'s frost and hailstorm relief (`extra_modifiers.txt:1379-1381`) is unaffected. The mod's wide `PRICE_RANGE = 0.999` may let a frozen market's prices swing further each winter than vanilla's; watch Russia, Scandinavia and Canada in the first observer run.

**Combat and navy rebalances.**
- Kill rate was counted twice before 1.15 (§ 3.11): the mod's kill rates were tuned on doubled values, so battle deaths, and the war deaths the census books, roughly halve. Decide whether to scale the mod's up.
- Naval combat and ship stats are rebalanced and warship modules need more goods. Each mod ship's `ship_power_projection_add` comes from its vanilla analogue (`extra_ship_types.txt` header), and its crit, vulnerability and screening values and the 116 modules' goods are anchored to vanilla's: re-derive them (runbook § 7). `snapshot_balance.py` doesn't capture module goods.
- `military_formation_interest_gain_mult` now applies from any source (§ 3.11).
- Disbanding units costs prestige; no mod script disbands units.

**Economy rebalances.** Buildings hire and set wages more conservatively, so staffed-to-function buildings ramp more slowly: the Strategic Reserve hub's staff on relocation, the Settlement Authority, barracks training counts, the Space Program. Rerun the AI-economy observer (`docs/testing/ai-economy-playtest.md`); expect the economy growth sim's calibration (`docs/systems/economy_growth_sim.md`) to be stale. SoL radicalization is slower, which softens the mod's raised expectations (welfare floors, UBI +10, `sol_expectations_vanilla_injections.txt`); review the half-life and floors. A new 1.15 law with an expected-SoL line goes unconverted by those injections.

**Politics.**
- **The new laws beside the mod's own groups** (design, not conversion): the Extraordinary Commission, Okhrana and Third Section beside the Ministry of Intelligence and Security, `law_intrusive_surveillance` and the Ministry of Thought Control (they stack); Official Nationality beside Language Policy (`law_linguistic_purity`, `law_civic_monolingualism`); Caesaropapism beside the Ministry of Religion; Internal Colonisation beside `law_neocolonialism`, the Colonial Empire and Resettlement. Opportunity: give the secret-police laws (and vanilla's Secret Police) counter-intelligence in Covert Warfare, whose defense comes only from the ministry laws today (`extra_laws.txt:424-489`).
- **Reform or Revolution and the socialist catalysts**: once their triggers can be read, the mod's own left-wing laws (Collective Governance, Communal Administration, Command Cooperative Economy, State-Owned Banking, Universal Basic Income) could feed them. Cultural Hegemony's political-model classifier uses `has_law_or_variant` and should cope.
- **Russian content.** The mod has no court, favorite or ukase content. Heir Education runs for Russia; check vanilla's heir decrees (`unlocked_by_heir`) don't fight its trait resolution. Russian literature's `country_rlit_cultural_prestige_add` could count toward Cultural Hegemony.
- **The Siberian exile pool**: read its `has_access` before designing the mod's pools (§ 4.7).
- **Cossack Hosts and the Settlement Authority's Military Colonies** are the same historical idea in Russia (`mod_systems.md:2706` onward). Keep both; optionally, Military Colonies could `establish_cossack_host` where allowed. The mod's `add_arable_land` conversion (`extra_script_values.txt:1487-1512`) enlarges the land the Hosts' 20% reserve applies to.
- The Populist Party's orange (`populist_party.txt:6`, `{255 140 0}`) will sit beside the Free Trade Party's new orange.
- The Intermarium formable now starts with Poland a Russian crown land.

**Monuments.** Moscow gets two Kremlins: the Grand Monuments heritage landmark (`landmark_moscow_kremlin`, `gm_custom_loc.txt:761`) and vanilla's `building_grand_kremlin_palace`. Decide whether the landmark yields where vanilla's wonder stands. The five new wonders get tourism's default +10% (`tourism.txt:2859-2872`); the Winter Palace and Kizhi Pogost stood in 1836, and the heritage rows already move Ingria's and Moscow's points for "St Petersburg's palaces" and "the Kremlin" (`tourism_heritage_moves.csv:22`, `:39`), so add them to the heritage inputs or those states count twice.

**UI.**
- **Unrealized Taxes** (a per-state list in the budget panel; the state tooltip shows them): nothing in the mod duplicates it. The Tax Code's Regional Relief (`state_tax_collection_mult` −0.25/−0.5) will show there as uncollected tax, so add a line to the relief tooltip and the tax chapter. Only visible once `budget_panel.gui` is rebuilt (§ 3.4).
- **State Infamy map mode** shows vanilla's `state_infamy_value`, so the mod's goals that charge their own figures will disagree with it: `te_force_become_subject` and `te_un_mandate_restore_state`'s fallback, items 1–2 of `vanilla_1_14_5_migration.md`'s open infamy list. Finishing those fixes the visible part. **State Value** may make § 4.1's GDP-per-capita map unnecessary.
- **The journal panel**: themed groups (a themed Space Race group for the nine milestone entries; finally a use for `je_group_environment`, with Global Warming); entry tooltips now list active modifiers, so the UN (566 `je:je_united_nations` references), Banking (213) and Global Warming (130) entries will have long ones. Check them in game.
- **Long tooltips now nest their overflow** (journal entries, event options). `long_tooltip_audit` is unaffected: it enforces the house style on the mod's own `.gui` tooltips, not an overflow workaround. But `tooltip.gui` redefines vanilla's base tooltip types (§ 3.4), and would switch the nesting off everywhere if it lives there.

**Already shipped in 1.14.x, and migrated**: war support 0–100 and its script commands, war goals enforced mid-war and mirror war goals, the infamy rework and its game rule, AI regional objectives, ship `ai_ship_category`, strait and piracy grievances and `grievance_mult`, subject `re_establish_war_goal`, `tax_income`, `weeks_until_bankruptcy`, `gdp_owned_by`, `on_won_war` and kin. See `vanilla_1_14_5_migration.md` and the runbook's rename table.
