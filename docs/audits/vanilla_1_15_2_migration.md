# Vanilla 1.15.2 migration record (2026-11-19)

The mod's last migrated version was 1.15.1. Hotfix 1.15.2 "Ivan-Chai" came out on 2026-11-19 and changed 560 of
the files the vanilla mirror tracks (559 modified, 1 added; mirror commit `95c5f73a`, on `0c6481e3` for 1.15.1).
This is what the hotfix did to the mod, what was changed, and what is left for the owner. Method:
`docs/guides/vanilla_patch_runbook.md`, in one sitting, with both versions in the mirror: the GUI overrides were
3-way merged on their exact base and every `REPLACE:`/`INJECT:` target was diffed between the two commits
(`vanilla_patch_diff.py targets 0c6481e3 95c5f73a`, whose replay on 1.15.0 → 1.15.1 reproduced that record).

The hotfix's largest pieces are a Single-Party State rework (the law now names a dominant party, through a new
event, `single_party_state.8`, and one amendment per party), regime change moved from a define to a per-group
threshold, every flavored company tied to its home state being incorporated, new Russian content (Tsar points
decrees for subjects, Bolsheviks), the naval mission picker and a rebalance of the early troop ship's and the
frigate's modules.

## What changed under the mod, and what was done

| Finding | Evidence | Done |
|---|---|---|
| Vanilla dropped the law group field `affected_by_regime_change` and the define `NDiplomacy\|WAR_GOAL_REGIME_CHANGE_MIN_LAW_PROGRESSIVENESS_DIFFERENCE` (50). Each group now carries `regime_change_min_progressiveness_difference`: a regime change imposes the holder's law in that group only when the two laws' progressiveness differs by at least that much, and never in a group without it. The mod set the old field on 19 groups (Judiciary, Monetary Policy, Privacy Rights, Bodily Autonomy, Frontier AI Control and 14 more) | `vanilla_patch_diff.py parsed --mod-uses`: the one removed field the mod still set; `targets`: the removed define | All 19 carry `regime_change_min_progressiveness_difference = 50`, the old define's value, so each group is imposed as before. `test_judiciary.py` checks the new field |
| `REPLACE:law_official_nationality` restated 1.15.1's primary-culture acceptance of 50; 1.15.2 gives 100, as every other citizenship law has | Target sweep | Ported |
| `REPLACE:mobilization_option_first_aid` and `_field_hospitals` held vanilla's recovery, 0.20 and 0.40; vanilla halved both | Target sweep | Ported: 0.10 and 0.20. Medevac Helicopters, the mod's third tier, stays at 0.80 (owner call 1) |
| `REPLACE:company_basic_electrics` and `REPLACE:company_construction_power_bloc` restated their `possible` in `ai_will_do`. 1.15.2's AI picks a company with no `ai_construction_targets` only once it can form it (`companies.md`), and vanilla's 26 such companies say `always = yes` | Target sweep | Ported. With `possible` needing five levels, the mod's three-level `ai_will_do` never added anything |
| `REPLACE:ideology_vanguardist` (Bolsheviks journal entry opens it) and `REPLACE:ideology_egalitarian_modern` (caste, Edo and education stances added, labor rights dropped) | Target sweep: both generator-owned | `apply_ideologies.py` regenerated them. `heir_ed_country_allows_ideology_vanguardist`, a copy of Vanguardist's `country_trigger` that keeps an heir's education roll off an ideology the country can't have, takes the Bolsheviks branch (`test_heir_education_ideologies.py`) |
| Vanilla's eleven parties gained a +1000 join weight for the dominant party's groups under the new Single-Party State amendments | Target sweep: the eleven party `INJECT`s | `gen_party_join_weights.py` restated them from 1.15.2 |
| Vanilla changed seven GUI files the mod overrides by path, and three that its type redefinitions copy | § 5 at-risk loop | See GUI |
| Engine reference docs and catalogs were 1.15.1's | `test_texture_reference_audit` wants the asset catalog's version to match the snapshot's | `vanilla_parsed/` rebuilt; `docs/engine/` rendered from the 1.15.2 dump; the effect/trigger catalog (+13, −4), its context list (+11, −2) and the asset catalog (+13 road textures, nothing removed) rebuilt; 3 loc accessors folded, 2 pruned; the culture-merge reads rescanned (only the version moved) |
| `supported_game_version` 1.15.1 | The launcher's version warning | `.metadata/metadata.json` → 1.15.2 |

## Engine surface

The game binary changed, and no Modding-Digests dump existed on the day, so the owner took a mods-off
`script_docs` dump (pinned at `~/src/vic3-engine-docs/1.15.2/docs`; automating that is #1907). Before it arrived,
the removed half was checked against the binary: every 1.15.1 effect, trigger and event target, apart from the
generated iterators, is a string in the new `victoria3.exe`. The dump agrees (`vanilla_patch_diff.py docs
--mod-uses --show-changed`): nothing removed from effects, triggers, event targets or modifiers.

- **Added**: the effect `conclude_journal_entry` (ends an entry with the outcome whose `effect_header` matches);
  the triggers `can_regime_change`, `has_naval_mission_without_area` and `is_character_interaction_available`;
  the modifier type `country_can_conscript_protected_subsistence_employment_bool`; the on-action
  `sps_law_checkpoint_cancellation`.
- **Removed**: the on-actions `on_diplo_play_subject_released` and `_overlord`, which the mod never used.
- **Changed meaning, same name.** `unit_recovery_rate_add` now also turns a share of a unit's casualties into
  Demoralized soldiers, on top of cutting the share killed outright. With it vanilla cut every recovery and kill
  rate it changed: First Aid and Field Hospitals by half, Panicked Retreat 0.25 to 0.15, Chemical Weapons' kill
  rate 0.3 to 0.2 and its recovery penalty −0.2 to −0.1 (owner call 1). `renege_treaty_ports_with` now leaves the
  port provinces with the foreign power as ordinary territory, where it returned them to the host; the mod doesn't
  call it. `on_law_checkpoint_success` now has a country scope; the mod doesn't hook it.
  `country_ship_type_early_troop_ship_construction_efficiency_add` and its troop ship twin were renamed in loc
  only.

## GUI

Vanilla changed 24 GUI files, seven of which the mod overrides by path. All seven were 3-way merged on 1.15.1
(`git merge-file`, BOM and CR stripped) and proved: the non-blank changed lines of `diff(1.15.1, mod)` equal
those of `diff(1.15.2, result)`.

| Override | Conflicts | What the mod's copy now takes from vanilla |
|---|---|---|
| `construction_panel.gui` | 0 | The supply ship decommission and retrofit buttons' text, sizes and tooltip placement |
| `market_panel.gui` | 0 | The goods list's sort buttons with tooltips, and empty imports and exports boxes |
| `military_formation_panel.gui` | 0 | A fleet's naval mission summary and its edit tooltip, replacing the "edit sea regions" button |
| `panel_military.gui` | 0 | The mobilization widget centred horizontally |
| `power_bloc_panel.gui` | 0 | The count of invitable countries drawn as plain text |
| `right_click_menu.gui` | 0 | A menu that picks the naval mission type for the selected fleets; a world market hub's trade capacity in the state menu |
| `states_panel.gui` | 1, resolved by hand | A building row's expansion-level text, the trade center's go-to button, a cultural community's local acceptance difference |

- **The one conflict**: the mod hides a building's earnings figure while it is subsidized, and vanilla reordered
  that textbox's attributes. The result is the mod's `visible` with vanilla's attributes.
- **Gates.** Every line vanilla added was read against the mod's `visible` and `enabled` lines around it: none
  sits inside a block the mod gates, apart from the textbox above, where vanilla's lines are its own attributes.
- **Dropped names.** Five GUI data functions left vanilla's GUI (`BattleParticipant.IsWarLeader`,
  `MapListOption.GetNavalMissionData`, `MilitaryFormation.CanEditMissionSeaRegions`,
  `MilitaryFormation.OnEditMissionSeaRegionsClicked`, `State.GetWorldMarketHubAccessDesc`, the last now called from
  loc), and one type (`naval_mission_map_list_panel`). After the merges no mod GUI file names any of them, nor any
  of the six English loc keys vanilla removed that the old copies used (`CHANGE_REGION`, the three
  `EDIT_NAVAL_MISSION_SEA_REGIONS_*`, two `MARKET_WORLD_MARKET_HUB_*`). No template was removed.
- **Fixtures.** `test_fixtures/vanilla_gui/country_panel.gui`, `custom_tooltip.gui` and `map_list_panel.gui` are
  1.15.2's. `gen_nation_tab.py` follows vanilla to `Country.GetMaxConscriptBattalions` for a decentralized
  country's potential battalions (`CalcConscriptableBattalions` remains, and the mod's other uses match
  vanilla's); `gen_build_list_columns.py` takes the trade center column's new number format;
  `gen_law_effects_gui.py` reran to the same output.

**Verified clean.** No mod entry collides with anything the hotfix added (39 entries, 4 events, 144 English loc
keys). Of the 8 entries vanilla removed, the mod used none (`installed_regime`, `calculate_communism_progress`,
`calculate_populism_progress`, two subject-release on-actions and their messages, a map mode). The mod sets and
reads no define vanilla removed or changed (`NAI|COMPANY_TYPE_FORMABLE_MULTIPLE_FREE_SLOTS_FACTOR` and the regime
change one above). The changed `INJECT:` targets take vanilla's additions beside the mod's: the political
strategies' new `max_regressiveness` terms for Factory Councils (the mod restates only `change_law_chance` and
`revolution_aversion`), the default strategy's Ecumenical Question term and subject valuation, `should_auto_expand`
on ports and trade centers, a Tsar points guard on Promote National Values, a homeland fallback in two cultural
renaissance map colors, Factory Councils at progressiveness 125 (was 75) and Corporatized Unions at 30 (was 25)
under the mod's wage-pressure injections, Single-Party State's dominant-party rework under its four mod
`INJECT`s, and 121 companies' home-state and `ai_will_do` changes under the mod's extension and unique-building
`INJECT`s, which set neither field. The mod's own flavored companies gate on production rank, not a home state.
The on-actions vanilla edited are ones the mod only adds to. No mod event redefines a vanilla event. The § 6b
mirrors hold: no rank, finance tech, `base_values` line, health, child or women's rights law, scripted rule, power
bloc name or principle file changed; the subject types lost only `breaks_if_subject_not_protected`, so the
`autonomy_level = 1` list (puppet, vassal, colony, crown land) stands. Ship types and modules changed only for the
ship of the line, monitor, frigate and early troop ship, none of them a mod analogue. The maps, regions and every
other § 4 generator came out unchanged.

## Owner calls this leaves open (none applied)

1. **The mod's recovery rates.** Recovery now also demoralizes, and vanilla cut its own sources (see Engine
   surface). The mod's were sized on the old meaning: Medevac Helicopters 0.80 (its ladder was First Aid 0.20,
   Field Hospitals 0.40, Medevac 0.80; halving it to 0.40 keeps the ladder), Bioenhanced Soldiers 0.5, Humanitarian
   Regulations 0.1, Fortified Bastion 0.05 and Impregnable Fortress 0.1, and the Healthcare principles' 0.05 and
   Food Standardization V's 0.1. None was changed.
2. **The mod's parties under Single-Party State.** 1.15.2's dominant-party event offers vanilla's eleven parties
   only, the amendments and join weights exist for them only, and the event can't be `INJECT`ed. With only the
   Technocratic, Green or Populist Party in government it may show no option at all. #1908 lays out three ways
   to close it.
3. **Regime change thresholds for the mod's economy groups.** Vanilla imposes its economic system and trade policy
   at a 25 difference and labour associations at 75; the mod's six economy groups (Intellectual Property,
   Monetary Policy, Right to Information, Financial Regulation, Genetic Rights, Antitrust) keep the old 50.

## In-game checks

Listed in `docs/testing/vanilla-1-15-playtest.md` § "1.15.2 hotfix". None gates the merge.
