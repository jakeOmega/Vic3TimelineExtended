# Vanilla 1.15.1 migration record (2026-11-11)

The mod's last migrated version was 1.15.0. Hotfix 1.15.1 "Ivan-Chai" came out on 2026-11-11 and changed 419 of
the files the vanilla mirror tracks (416 modified, 3 added; mirror commit `0c6481e3`, on `6552517a` for 1.15.0).
This is what the hotfix did to the mod, what was changed, and what is left for the owner. Method:
`docs/guides/vanilla_patch_runbook.md`, in one sitting. It is the first bump where the mirror held both versions, so
the GUI overrides were 3-way merged on their exact base and every `REPLACE:`/`INJECT:` target was diffed between the
two commits.

The engine surface barely moved: one new trigger (`num_building_assets_of_group`), two new modifier types
(`country_cannot_decrease_autonomy_bool`, `state_disable_disband_prestige_penalty_bool`), two new custom loc entries,
nothing removed or renamed (`vanilla_patch_diff.py docs` between the two dumps). No vanilla entity was removed, and
the mod sets no field vanilla dropped (`vanilla_patch_diff.py parsed --mod-uses`).

## What changed under the mod, and what was done

| Finding | Evidence | Done |
|---|---|---|
| `REPLACE:da_stake_colonial_claim` restated vanilla's old infamy. 1.15.1 charges half the state's `state_infamy_value` (the claim itself ignored), where it charged 5 scaled by population and clamped to 5–20 | Target sweep: the one changed `REPLACE:` diplomatic action | Rebuilt as vanilla 1.15.1 plus the mod's renounced-claims tooltip (3-way merge, no conflict; the only lines that differ from vanilla's are the header and that tooltip) |
| `REPLACE:pm_telephones` held vanilla's 1.15.0 inputs. Vanilla's copper pass moved it from iron 10, copper 30, tools 10 to iron 20, copper 15, tools 15 | Target sweep | Ported. Input cost is unchanged at base prices (2,800) |
| `REPLACE:pm_arc_welded_buildings` and its Construction Site twin run vanilla's inputs at 0.4. Vanilla went from tools 30, copper 10 to tools 35, copper 5 | Target sweep; `test_construction_tiers` keeps the twin equal | Ported at the mod's scale: tools 12 to 14, copper 4 to 2. Input cost unchanged (4,165) |
| Vanilla put copper on 8 more states and raised it on most others: 84 states and 609 levels became 92 and 770 | `map_data/state_regions/`, all 16 files | `resources.py` regenerated the mod's copies. Vanilla's figure is the discovered part of a state's endowment, so discovered copper is 770 (was 609) and undiscovered 10,066 (was 10,105); seven states the mod gave no copper now have vanilla's |
| 8 new loc accessors, one of them type-changing: `MilitaryFormation.GetSupplyHub` returns a state | `fold_vanilla_loc_accessors.py --dry-run`; the digest's data types | Typed by hand in `localization_accessor_audit.py`, the other seven folded |
| Vanilla's secession play now tests Polish as a primary culture (`subject_join_initiator_trigger`: a subject with the Congress Poland entry may not join a Polish secession while the Whites are strong) | `culture_merge_primary_reads.py --write`: one new row | Classified under `je_congress_poland` in `culture_merge_primary_ledger.py`; the generated culture-merge script did not move |
| `supported_game_version` 1.15.0 | The launcher's version warning | `.metadata/metadata.json` → 1.15.1 |
| Engine reference docs and catalogs were 1.15.0's | Headers; `test_texture_reference_audit` wants the catalog's version to match the snapshot's | `vanilla_parsed/` rebuilt; `docs/engine/` rendered from the 1.15.1 dump; the effect/trigger catalog (+5 names), its context list and the asset catalog (+3 paths) rebuilt; `zz_te_party_join_weights.txt` restated from 1.15.1 (header only) |
| `test_frontier_ai_control` failed on a machine with the game: `gen_law_consistency.load_vanilla()` returns `None` there ("parse the game files") and the test indexed it | The full suite run with the real game paths; CI's dummy paths never reach it | The test passes `None` through, as `parse_laws` expects. Not from this patch |

## GUI

Vanilla changed 21 GUI files, nine of which the mod overrides by path. All nine were 3-way merged on 1.15.0
(`git merge-file`, BOM and CR stripped) and proved: the changed lines of `diff(1.15.0, mod)` equal those of
`diff(1.15.1, result)`, apart from the headers' version and the one fix below.

| Override | Conflicts | What the mod's copy now takes from vanilla |
|---|---|---|
| `building_details_panel.gui` | 0 | A second go-to button on a world market hub's state, opening the market panel filtered to that hub |
| `journal_entry.gui` | 0 | Historical outcomes in their own conditions box; scripted bars closer together, the script-styled bar 16 px narrower |
| `market_panel.gui` | 3, rebuilt by hand | The Trade tab's trade-capacity boxes (the country capacity line is gone) and world market hub filter; vanilla's charts moved below the filters and read the selected hub |
| `military_formation_panel.gui` | 0 | Status icons (repairing, naval invasion, embarking, mission); the fleets' Auto-replace lost ships checkbox; `text_position` became `text_margin` |
| `panel_military.gui` | 0 | The mobilization widget's footer: a stats row, then a full-width Mobilize button |
| `power_bloc_formation_panel.gui` | 0 | The "mandates lost to cap" warning is gone |
| `right_click_menu.gui` | 0 | A world market hub filter menu and a hub entry in the state menu |
| `treaty_draft_panel.gui` | 0 | Law-commitment label sizing |
| `treaty_panel.gui` | 0 | The binding-period box with an overridable tooltip; a law commitment's icon opens the law group |

- **The market panel** is vanilla 1.15.1 plus the mod's blocks. The six-slot tab strip, the Climate and Reserve
  tabs and the All Goods tariff rows merged cleanly. The mod's three Trade-tab blocks (charts by value, partner
  charts, Top Trade Partners) go in unchanged directly after vanilla's charts, so they sit below the filters where
  they sat above. Vanilla's Monthly Price Report stays out, as before. `MARKET_COUNTRY_TRADE_CAPACITY`, the one
  removed loc key the mod used, went with vanilla's rewrite.
- **A clean merge that was wrong, fixed.** The mod showed the formation panel's settings section for armies only.
  1.15.1 put the fleet checkbox Auto-replace lost ships inside it, where no player would have seen it: no conflict,
  and the proof passed. The section now shows for armies and for the local player's fleets, and the borrow and
  lending heading and list carry `MilitaryFormation.IsArmy`. The lesson is in the runbook's § 5.
- **Dropped names.** Six GUI data functions are gone (`Market.GetCountryTradeCapacity` and its `Balance`, `Desc`
  and `Usage`, `MilitaryFormation.GetDistanceToHomePortFormatted`, `PowerBlocFormation.GetMandatesLostToCap`), with
  14 tokens and 8 English loc keys; after the merges no mod file names any of them. No type or template was
  removed, and the mod redefines none of the 32 that changed. Vanilla's own `military_panel_formations.gui` and
  `popups.gui` now pass `text_margin` and `binding_period_tooltip` into types the mod overrides, so those two
  overrides could not have been left on 1.15.0.
- **Fixtures.** `test_fixtures/vanilla_gui/country_panel.gui` and `custom_tooltip.gui` are 1.15.1's.
  `gen_nation_tab.py` and `gen_law_effects_gui.py` rerun to the same output: vanilla's edits fall outside what they
  copy.
- **`te_bulk_tariff_widgets.gui`**: the All Goods rows follow the goods rows' background, which vanilla moved from
  `entry_bg_simple` to `entry_bg_fancy_dark` at 0.6 alpha. Cosmetic.
- **Not ported:** `te_system_tab_widgets.gui` copies the script-styled bar renderer at its own widths, so vanilla's
  16 px trim doesn't apply. `texticons.gui` and `goods_texticons.gui` were reformatted (one new icon,
  `admiral_defeated`); the mod's 15 goods text icons need nothing.

**Verified clean.** No top-level collision between the mod and anything the hotfix added (13 map mode defaults, 8
static modifiers, 2 modifier types, the `favorites` events, a message, 111 loc keys). Of the 8 loc keys vanilla
removed the mod used one, in the market panel (see GUI). Every `define:` the mod reads exists, and the mod overrides no
define vanilla dropped (`MANPOWER_RATIO_REQUIRED_TO_CLEAR_DEFEATED_ADMIRALS`,
`WAR_GOAL_REGIME_CHANGE_MAX_IDEOLOGICAL_OPINION`, `PRODUCTION_METHOD_LOW_POP_FACTOR`) or uses `low_pop_method`, now
`scoring_override = low_pop_method`. The changed `INJECT:` targets take vanilla's additions beside the mod's: the
default AI strategy (new goods stances for radios, telephones and oil, none of which the mod's block names), two
administrative strategies (subsidy values on buildings the mod's blocks don't name), the Armed Forces (a new pop
weight; the mod injects the female-leader chance), `war_support_from_journal_entries` (a guard on the Carlist War
term) and four technologies (`ai_weight` only). The on-actions vanilla edited are ones the mod only adds to. No mod
event redefines an event the hotfix changed. The runbook's § 6b mirrors are untouched: no rank, law, subject type,
scripted rule, power bloc name or principle file changed, and the finance techs and `base_values` kept their
interest lines. `/validate/engine-coverage` lists no vanilla breakage (14 unknowns, all mod script tokens, as on
1.15.0). The full suite passes with the real game paths (13,806 tests), which is where the snapshot-driven
detectors run: the moved engine lines, the `VANILLA FIX` tests, the state-region sync and the install-only texture
checks.

## What reaches the mod without a file of its own changing

- **AI subsidies were reworked.** A strategy's subsidy value is now the most the AI may spend on that building type,
  the AI no longer subsidizes a profitable building or one it doesn't need
  (`NAI|SUBSIDIZE_REMOVE_PROFIT_MARGIN_BUFFER`), vanilla's strategies say `wants_to_have` where they said
  `nice_to_have`, and the default strategy subsidizes shipyards (`should_have`). The mod's
  `te_ai_subsidy_strategies.txt` sets `should_remove` on power plants, railways and ports in every administrative
  strategy (#933, #1050), a value read from the executable's strings and proven in game on 1.14.5. The executable
  still holds it, and nothing more is known offline.
- **Ports and railways no longer start the game subsidized** (`bg_private_infrastructure`: `subsidized = no`, a
  start-of-game default only). This is the direction #1050 wanted.
- **The AI scores production methods differently**: it counts the wages of new jobs as a cost, only the workers
  actually laid off as a saving, the method's output and input multipliers, and labor-saving methods higher in a
  state short of workers (`PRODUCTION_METHOD_EMPLOYMENT_CHANGE_NO_AVAILABLE_LABOR_MULT`). The mod's three stickiness
  defines (`extra_defines.txt`) were sized against 1.14.5's scoring.
- **Regime Change** now imposes a law the target could not otherwise enact, if the imposer holds it, and is closed
  where no law would change. The mod's law groups a regime change carries (Bodily Autonomy among them) follow.
- **`can_secede_during_revolution`** is a new field of a movement's `secession` block, default no; vanilla sets it
  on its religious, cultural minority, nationalist and slave-revolt movements only. The mod's four movements with a
  `secession` block are ideological, like the vanilla ones left at the default, and two of them can never secede.
- **Canals** carry `grievance_mult = 0.5`; the mod defines no strait.
- **Copper** is in less demand in vanilla's own methods (stills, telephones, arc welding) and more plentiful at the
  start (above).

## Owner calls this leaves open (none applied)

1. **The mod's own copper inputs.** Vanilla halved copper in two of the methods it rebalanced and cut the stills.
   The 46 conductor inputs the 1.15 migration moved from lead to copper (motors, telecoms, appliances, electronics,
   robots, aircraft, bandwidth, launch vehicles) were sized on 1.15.0's copper and are unchanged. The two replaced
   methods above follow vanilla because they restate vanilla's inputs; reverting them is five numbers.
2. **`should_remove` on power plants, railways and ports.** If 1.15.1's AI already drops a subsidy from a plant
   that pays its way or isn't needed, the workaround may be redundant, or may now strip subsidies vanilla's new
   logic would rightly keep. It stays as it is until the play-test reads it.
3. **AI stickiness defines** (0.9 / 0.6 / 0.05 against vanilla's 0.95 / 0.75 / 0.1): keep, or re-derive against the
   new scoring.
4. **Shipyards.** Vanilla's AI may now subsidize `building_shipyard`. The mod injects two method groups into it,
   and its company shipyards (Mitsubishi's Nagasaki yard, Aker's, Götaverken's and the rest) are buildings of their
   own that no strategy names.

5. **Monthly Price Report.** Vanilla's report is now a self-contained block at the top of the market panel's
   default tab and no longer competes with the mod's trade charts for a place. It is still left out.
6. **The mod's trade charts and the hub filter.** With a world market hub selected, vanilla's charts show the
   hub's trade and the mod's still show the whole market. Hide the mod's while a hub is selected, or leave them (the
   partner charts can't follow a hub without new script).
7. **Foreign formations.** The settings section shows for any army and for the player's fleets. Vanilla shows
   borrow and lending for another country's formations too; the mod never has.

## In-game checks

Listed in `docs/testing/vanilla-1-15-playtest.md` § "1.15.1 hotfix". None gates the merge.
