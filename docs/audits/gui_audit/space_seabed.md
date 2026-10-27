# Space Race / Solar Colonization, Orbital Debris & Seabed Licences — GUI & localization audit

> Part of the 2026-10-27 GUI and localization audit; the index, the cross-cutting findings and the owner questions are in [`../gui_localization_audit.md`](../gui_localization_audit.md). Line numbers are as of the audit and drift as files change; search by key or type name. "Quick fixes" below means the loc-only edits this PR applied.

Slice: the nine `je_space_race_*` entries and the Timeline Extended window's Space Race tab
(`gui/journal_entry_widgets/space_race_widget.gui`, the generated `sr_sites_generated_rows.gui` /
`sr_fleets_generated_rows.gui`, `gui/sr_launch_window_widgets.gui`, `te_orbital_debris_widget.gui`), and the
Seabed tab (`gui/te_seabed_widgets.gui`). Read-only; all line numbers are as of this audit. Generated GUI is
`scripts/generators/gen_solar_sites.py` (sites, settlers, colony fleets, modules, queue, autonomy, free colonies)
and `scripts/generators/gen_space_fleets.py` (fleets, locations, defences); changes to those rows are proposed
against the generators.

## Top priorities

- **SPC-1 — about 470 greyed buttons never say why.** Every per-colony and per-fleet button (Target, Priority,
  module +, Clear, queue up/remove, Abandon, Supply, Go, Merge, Detach, Land, Embark, Posture, Seize/Destroy),
  plus Settlers +/−, Launch, Auto and the five build-mix buttons, render `ExecuteTooltip` alone, so the
  `is_valid` reasons the scripted GUIs already write (`sr_fl_refitting_tt`, `sr_fl_short_tt`,
  `sr_mod_cannot_queue_tt`…) never show. Fix it in the two generators' button helpers. Rule 6.
- **SPC-2 — the Defences and Spaceport module tooltips are wrong.** They say "Space fleets are not in the
  game yet". Fleets have shipped (Full Colonies). Four keys, all loc-only (Quick fixes). This is the owner's
  own example tooltip.
- **SPC-3 — solar colonization has no concepts.** Fleets, ship roles, drives, launch windows, modules,
  autonomy, free colonies, blockade/interdiction and integrity are explained inline, often several times (each
  of the five build-mix buttons lists all five roles' stats; the drives table appears twice). The fix is a
  concept family, nested the way the owner described: Defences → `[concept_sr_space_fleet]` →
  `[concept_sr_ship_role]` → `[concept_sr_space_command]`.
- **SPC-4 — seven live colony sections open with a paragraph of explanation** (`te_sr_note` in Settlers,
  Autonomy, Modules, Space Command, Fleets, Colony Defences and Solar System). How the Space Race Works has no
  colonization topics at all. The fix: move the paragraphs into a collapsed "How Solar Colonization Works" and
  extend `HowItWorksTest` to the colony sections.
- **SPC-5 / SPC-6 — one colony's facts are spread over six sections, and the overview flags none of them.**
  The same world appears in Our Colonies, Solar System, Settlers, Colony Modules, Colony Autonomy and Colony
  Defences. Nothing at the top says which colony needs attention: autonomy ≥ 75, under assault, blockaded,
  module queue empty, a hostile fleet inbound. The fix: a second overview row of alert cells, and one Colonies
  table with a view switch.
- **SPC-7 — the colonization action path is long.** The next fleet's destination is in Colony Fleets, but
  Target sits in the Solar System list, which is collapsed by default and is the last section. A world's row
  gives no hover on what it offers or how long the trip takes.
- **SEA-1 / SEA-2 — the Seabed overview's Policy and Regime hovers re-teach all three options.** That
  duplicates How Seabed Licences Work. The policy buttons describe their effects in prose, where Global
  Warming's policy rows use engine-rendered modifier lines.

## Findings

### SPC-1. Greyed buttons in every colony, fleet and Space Command row hide their reason
- **Category:** hidden info
- **Where:** generator helpers `scripts/generators/gen_space_fleets.py:1490` (`_button`: `tooltip = _op(sgui, "ExecuteTooltip", n)`) and `gen_solar_sites.py:2402, 2418, 2668, 2686, 2711, 2717, 2743, 2747` (`_sgui_call(..., "ExecuteTooltip", site)`); counts in the output: `sr_sites_generated_rows.gui` 379 `enabled =` / 0 `IsValidTooltip`, `sr_fleets_generated_rows.gui` 81 / 0. Hand-written: `space_race_widget.gui:2985-3037` (Emigration −/+), `:4618-4649` (Launch, Auto on/off), `:4661-4710` (build mix ×5).
- **Now:** a greyed Go shows only `sr_fl_go_tt` ("The fleet leaves for its destination…"). It never shows "The fleet is refitting" (`sr_fl_refitting_tt`), "Nothing leaves Earth: it is blockaded…" (`sr_fl_earth_barred_tt`) or "The leg can't leave this month…" (`sr_fl_short_tt`). Those clauses already sit in `sr_fleet_go_sgui`'s `is_valid` (`common/scripted_guis/sr_fleet_sguis.txt:59-72`). A greyed module "+" shows "Queue one more level…" without saying the queue is full or the slots are used. A greyed Emigration "−" hides "Emigration is already off." (`sr_emig_at_lowest_tt`). Mission Control's own buttons (`:901-971`) and the Seabed buttons (`te_seabed_widgets.gui:154, 174`) already use the right recipe.
- **Proposed:** in both generators, make the button helper emit `tooltip = "[Concatenate( GetScriptedGui('<sgui>').IsValidTooltip( <scope> ), Concatenate( Localize( 'te_tt_break' ), GetScriptedGui('<sgui>').ExecuteTooltip( <scope> ) ) )]"` (gotcha #16). The pick and target buttons keep their leg/intel hovers; add the reason in front of those too. Hand-edit the 10 buttons in `space_race_widget.gui` the same way. Before exposing them, reword the `is_valid` texts as requirements, because `IsValidTooltip` prints every clause with a tick or a cross (gotcha #16). Many were written as failure messages, since nobody saw them:
  - `sr_fl_refitting_tt` "The fleet is refitting." wraps `NOT = { … refitting }`, so a fleet that can go would show a tick beside "The fleet is refitting";
  - likewise `sr_fl_short_tt`, `sr_fl_earth_barred_tt`, `sr_fl_not_at_location_tt`, `sr_fl_no_partner_tt`, `sr_fl_no_detach_tt`, `sr_fl_no_land_tt`, `sr_fl_no_embark_tt` and `sr_fl_no_target_tt`;
  - `sr_reserve_empty_tt`, `sr_launch_site_lost_tt` and `sr_reserve_no_slot_tt`;
  - `sr_emig_at_lowest_tt` / `_at_highest_tt` ("Emigration is already off.") and `sr_mod_nothing_queued_tt`.
  
  Phrase each as the requirement, as the UN chamber's are ("This is not the mandate already in force"): "The fleet is not refitting", "Something is queued at this colony". Six colony sguis have `is_valid` blocks of bare scripted triggers with no `custom_tooltip`: `sr_colony_target_sgui`, `sr_colony_priority_sgui`, `sr_colony_abandon_sgui`, `sr_free_supply_sgui` and the two queue sguis (`common/scripted_guis/sr_colony_sguis.txt`). Wrap those clauses too, or `IsValidTooltip` prints the triggers' raw names. Then split `sr_mod_cannot_queue_tt` (`te_miscellaneous_l_english.yml:6071`): it is one sentence naming five conditions ("We hold this colony, its founding specialization is chosen, the queue has a free place (of 20), and the module has room…"). Make it one `custom_tooltip` per condition in `sr_mod_scope_can_queue`, so the failing one gets the cross.
- **Effort:** medium (two generator helpers and a rerun, 10 hand edits, about 16 loc rewordings, one trigger split)
- **Confidence:** high

### SPC-2. Defences and Spaceport tooltips still say fleets are not in the game
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** other (stale/wrong text), over-explaining
- **Where:** loc `je_space_race_widget_mod_def_tt` (`te_journal_entries_l_english.yml:1092`), `je_space_race_widget_mod_port_tt` (`:1094`), shown on every Colony Modules "Def"/"Port" level cell (`sr_sites_generated_rows.gui`, e.g. the Venus row's `mod_def_level`) and on the column heads (`space_race_widget.gui:3751, 3759`); `sr_mod_queue_def_tt` / `sr_mod_queue_port_tt` (`te_miscellaneous_l_english.yml:6074, 6076`), the "+" buttons' effect.
- **Now:** "Will be what an enemy fleet closing on the colony has to beat. Space fleets are not in the game yet, so Defences do nothing for now." Under Full Colonies, Defences fire (`je_space_race_widget_def_level_tt`: "Each fires 15 strength at factor 1.5…") and Spaceports dock fleets (`sr_fl_month_at`; integrity regains `sr_integrity_regain_port` = 10 against 5, `sr_fleet_values.txt:158-159`). The player guide already states it correctly (`docs/player_guide/16-space.md:610-611`).
- **Proposed:** the Quick fixes table rewrites all four to say what each does under Full Colonies and that it does nothing under Simple Colonies, matching the guide's wording. Longer term, SPC-3's concepts let the module tooltip shrink to one line: "Fire on enemy [concept_sr_space_fleet]s closing in on the colony."
- **Effort:** quick
- **Confidence:** high

### SPC-3. No concepts for solar colonization; the same rules are explained inline, often twice
- **Category:** over-explaining, style
- **Where:** `common/game_concepts/extra_concepts.txt:72-78` (only `concept_space_race`, `_space_milestone`, `_solar_colonization`, `_sr_approach`, `_sr_funding`, `_sr_setback_risk`; plus `concept_orbital_debris`). Inline teaching:
  - `sr_sc_mix_step_tt` (`te_miscellaneous_l_english.yml:6134`) is every build-mix button's tooltip. Every one lists all five roles' fire, supply and special rules, and none says which role it steps.
  - `sr_fl_posture_tt` (`:6015`) lists all four postures on the posture button.
  - The drives table appears twice: `je_space_race_widget_cf_drive_tt` (`te_journal_entries_l_english.yml:829`, transit times) and `je_space_race_widget_fl_drive_tt` (`:1019`, km/s).
  - Launch windows are explained in `je_space_race_widget_windows_header_tt` (`:1332`) and again in every stage profile (`je_space_race_solar_colonization_status_stage1..5`, `:789-793`).
  - Blockade and interdiction are explained in `je_space_race_widget_loc_blockaded_tt` / `loc_interdicted_tt` (`:1071, 1081`), and the Colony Defences status words point at the same keys.
  - Autonomy: `autonomy_note` (`:820`), `autonomy_figure_tt` (`:817`) and `autonomy_drift_tt` (`:816`).
  - The free colony: `ss_free_tt` (`:1310`) and the Free Colonies rows.
- **Now:** a player hovering "Siege 2" reads a five-bullet table of every role. "Fleets", "drive", "window", "integrity" and "autonomy" carry no hover anywhere outside the row they sit in.
- **Proposed:** add a concept family (names in `te_miscellaneous`, `_desc` in `te_concepts`), each desc short and nesting the next:
  - `concept_sr_colony_module` (Module): specializations I/II share four levels, and Habitat, Spaceport and Defences share the slots; built by `[concept_sr_module_fabrication]`; needs crews (`[concept_sr_crew]`).
  - `concept_sr_space_fleet` (Space Fleet): built by `[concept_sr_space_command]`, made of `[concept_sr_ship_role]`s, flies on a `[concept_sr_drive]`, needs supply and propellant, docks at Earth or a Spaceport. Full Colonies only.
  - `concept_sr_ship_role` (Ship Role): the five roles in one short list. Optionally one concept per role (`concept_sr_role_warship`…), so the mix button reads "Siege ships: weight 2 → 3. [concept_sr_role_siege]".
  - `concept_sr_space_command` (Space Command): the building, its build rate by production method, the build mix and the reserve.
  - `concept_sr_drive` (Drive): the four drives with transit times and km/s, replacing both `cf_drive_tt` and `fl_drive_tt` bodies.
  - `concept_sr_launch_window` (Launch Window): the text of `windows_header_tt`. The stage profiles then say only "Mars: every 26 months".
  - `concept_sr_colony_autonomy`, `concept_sr_free_colony`, `concept_sr_blockade` (with interdiction), `concept_sr_colony_integrity`, `concept_sr_marines`.
  
  Then the tooltips become one line plus the concept: mod_def_tt → "Fire on enemy [concept_sr_space_fleet]s closing in on the colony", fleet column heads → `[concept_sr_drive]`, Space Command note → its concept. `sr_sc_mix_sgui` would need a per-op `custom_tooltip` (`sr_sc_mix_step_<role>_tt`) to name its role.
- **Effort:** medium (about 12 concepts and their loc, about 15 tooltip rewrites, one sgui split)
- **Confidence:** high (the gap); medium (exact concept set)

### SPC-4. Explanatory paragraphs open seven live colony sections; How the Space Race Works covers none of colonization
- **Category:** over-explaining, style (rule 1, rule 7)
- **Where:** `te_sr_note` at the head of Solar System (`space_race_widget.gui:2681`, `je_space_race_widget_solar_system_note` `:1305`), Settlers (`:2965`, `settlers_note` `:1299`, plus `settlers_crews_note`/`agi_note` `:3058-3065`), Colony Autonomy (`:3336`, `autonomy_note` `:820`), Colony Modules (`:3794`, `modules_note` `:1106`), Space Command (`:4563`, `sc_note` `:1270`), Fleets (`:4745`, `space_fleets_note` `:1308`) and Colony Defences (`:4979`, `defences_note` `:928`). The How section (`te_sr_sec_how`, `:5694`) has eight subsections: approach, funding, setbacks, first, rivals, programme, powers, orbit.
- **Now:** a returning player with Full Colonies scrolls past seven paragraphs, for example "Pick a fleet's destination, then Go. A fleet travels at its drive's pace, spending propellant, and can't be stopped on the way…", before each section's rows. `test_space_race_layout.py:461` (`HowItWorksTest`) forbids `te_sr_note` only in `te_sr_sec_control`, `te_sr_sec_rivals` and the overviews. The colony sections arrived later and were never added to it.
- **Proposed:** a collapsed "How Solar Colonization Works" (its own flag `sr_panel_how_colonies_open`), mounted after the colonization status sections and shown only while `je_space_race_solar_colonization` is active. Subsections: Colony Fleets & Targets, Launch Windows, Settlers & Crews, Modules, Autonomy & Free Colonies, Space Command & Fleets, Defences & Seizure. Move the seven notes' text there; with SPC-3 most of it becomes the concept descs. Keep in the live sections only what is state, not rule: `sc_blockaded_note`, `sc_site_lost_note`, the destination line, the "empty" lines. Add the colony section types to `HowItWorksTest`'s list.
- **Effort:** medium (one new section type, loc moves, test update)
- **Confidence:** high

### SPC-5. A colony's facts are spread over six sections; the colony name appears six times
- **Category:** spread-out/redundant
- **Where:** `te_sr_solar_colonization_status` (`space_race_widget.gui:7129-7137`) stacks, for the same world:
  - Our Colonies (`:1329`, 68 hand-copied specialization rows, `:1375-2421`);
  - Solar System (`:2655`, holder);
  - Settlers (`:2939`: people / room / crews / priority);
  - Colony Modules (`:3768`: staffing, I/II/Hab/Port/Def, queue);
  - Colony Autonomy (`:3310`: autonomy, drift, status, Abandon);
  - Colony Defences (`:4953`: Defences, integrity, marines, status).
- **Now:** to decide whether to add Defences to a restless, under-crewed colony, the player reads Autonomy (autonomy 78), Settlers (crews), Modules (slots) and Defences (integrity): four sections, each with its own header and note. Our Colonies duplicates what the Modules I/II cells' hovers already show (the same `je_space_race_widget_colony_<world>_<spec>_tt` keys) and the Solar System "Ours" rows.
- **Proposed:** one Colonies section. Keep a single generated row per held world (icon, name, a status icon), with a small view switch above the rows. The switch is a `GetVariableSystem` value `sr_colony_view` = people | modules | autonomy | defences, a strip of four short buttons, rule 6 "said once above the rows". The row's right-hand columns follow the view: today's Settlers, Modules, Autonomy and Defences cells. The section-level figures (emigration stepper, fabrication, shipments, upkeep, Extraplanetary Base room, free-colony trade, the queue) sit under the switch for their view. The colony name's hover gives what Our Colonies gives now (its specializations' `GetStaticModifier(...).GetDesc` at their levels). Our Colonies is then dropped; the generator already writes every per-site row, so this is one row type with four column sets, not new script. If a switch is too much, the minimum is folding Our Colonies into the name hover of the Modules rows and dropping the 1,100-line hand-copied section.
- **Effort:** large (GUI restructure, generator change, `test_space_race_layout.py` / `test_space_race_labels.py` updates)
- **Confidence:** medium (on the design; high that the spread is real)

### SPC-6. The colonization overview shows the programme, not what needs attention
- **Category:** spread-out/redundant (summary → action)
- **Where:** `te_sr_solar_colonization_overview` (`space_race_widget.gui:6943`): state, risk, stage, Next Colony bar, Staged in Orbit, worlds pie, programme row.
- **Now:** everything a player acts on is several sections down or arrives only by event. Examples: a colony at autonomy ≥ 75 demanding self-government; one under assault, blockaded or occupied; Earth blockaded or the launch site lost (red notes inside Space Command, `:4567-4574`); a hostile fleet inbound (only `space_race_events.100`, `sr_disp_fl_alert_months`); the module queue empty while fabrication stocks points; the next launch window (Mission Control's Next Windows).
- **Proposed:** under Simple/Full Colonies, a second overview row in the Banking cell shape (`te_banking_ov_cell`: icon, caption, word, one figure, breakdown on hover), two to a row:
  - **Colonies:** held N / 34, the word Calm / Restless / Breaking away from the highest autonomy; the hover lists colonies at ≥ 75.
  - **Defence** (Full): Calm / Under assault / Blockaded / Occupied, with the count; the hover lists them, plus any hostile fleet inbound and its months.
  - **Modules:** queue N, word Idle when the queue is empty and the stock is full.
  - **Next window:** body and months, or "Any month" with a torch drive.
  
  Script: max-autonomy and assaulted/blockaded counts can be built in the existing monthly display refresh (`sr_sites_refresh_snapshot`); the rest exist as `sr_disp_*` values. Earth blockaded / site lost become the Defence cell's red word instead of notes.
- **Effort:** medium-large (overview row type, about four aggregate script values, loc)
- **Confidence:** medium

### SPC-7. Target sits far from the destination it changes; world rows give no hover on what a world offers
- **Category:** spread-out/redundant, hidden info
- **Where:** Colony Fleets' destination lines (`space_race_widget.gui:2773-2784`, `je_space_race_widget_cf_destination_target/auto/auto_contested`, `te_journal_entries_l_english.yml:825-827`: "…Pick one with Target in the Solar System list"). Solar System is collapsed by default (`sr_panel_solar_system_open`, `:2668-2679`) and is the last of nine colony sections (`:7137`). `te_sr_site_row` (`:2444`): `site_name` (`:2464-2472`) has no tooltip. Next Windows is script-concatenated text in Mission Control (`gui/sr_launch_window_widgets.gui:38-55`, `sr_launch_windows_sgui`).
- **Now:** to retarget, a player reads "Our next colony fleet goes to Ceres… Clear it there", scrolls past six sections, opens Solar System and finds the row. Hovering a world's name shows nothing: no stage, no specializations offered, no transit by our drive, no next window. Those come only after founding, or from Next Windows in a different section. The destination lines are live state, but they are drawn in the `#lore` note style (rule 7).
- **Proposed:**
  - (a) Put Solar System directly under Colony Fleets, open by default but filtered by default to the current stage plus ours, with "show all 34" as the toggle. Or move the Target buttons into a "Reachable worlds" list inside Colony Fleets.
  - (b) Turn the destination into a value row, "Next fleet: **Ceres** (our target) [Clear]" or "Next fleet: chosen at launch", with Clear beside it (rule 6), and "Drive: Chemical" as a value row with `[concept_sr_drive]`.
  - (c) Have `gen_solar_sites.py` emit a per-world name tooltip `je_space_race_widget_ss_site_<key>_tt`: stage, the two specializations' `GetStaticModifier('sr_colony_<key>_<spec>').GetDesc`, transit months by our drive (the `sr_fleet_legs_generated.txt` values), next window.
  - (d) Optionally put each location's next window on its Solar System subheader ("Mars — window in 14 months"), so Next Windows and the Target buttons stop being two lists of the same worlds.
- **Effort:** medium (reorder and filter; generator tooltips; small loc)
- **Confidence:** high (the hidden hover and the distance); medium (the exact layout)

### SPC-8. The Space Race tab buries our milestone under the other powers, and shows debris and rivals twice
- **Category:** spread-out/redundant
- **Where:** `gui/te_systems_window.gui:362-372` (Space Powers, then Orbit, then the milestone blocks). `te_sr_sec_powers` (`space_race_widget.gui:5472`, up to 9 rows of 50) and `te_sr_sec_rivals` (`:1127`) both appear in the tab. `te_sr_debris_row` sits in both `te_sr_sec_orbit` (`:5647`) and every milestone's Mission Control (`:998`).
- **Now:** opening the tab, the player first sees up to nine power rows and five Orbit rows, then the overview and Mission Control of the milestone they are running: the summary they act on is a screen down. With two milestones running, the debris line appears three times. A rival appears both in Space Powers (its furthest milestone's band) and in Rivals (this milestone's band). The two often show the same figure, and `je_space_race_widget_how_powers` (`:1058`) says it is "the same band as the Rivals list".
- **Proposed:**
  - Order the tab as milestone blocks first (each with its overview, as in the journal), then Space Powers and Orbit, then How. Space Powers is new (#1147, 2026-10-25, "not yet seen in game") with no owner placement decision recorded.
  - In the tab, drop the per-milestone Rivals (it stays in the journal), or keep only its "the first" information, which the overview already carries. Space Powers is the fuller list.
  - Give `te_sr_sec_control` a `block "sr_debris"` around `te_sr_debris_row`, overridden empty by the tab's milestone instances, so the tab shows debris once, in Orbit.
- **Effort:** medium (reorder, two blockoverrides, `test_te_systems_window.py` / `test_space_race_layout.py`)
- **Confidence:** medium

### SPC-9. Rivals (5 slots) and Space Powers (8 slots) are fixed rows with "+N more" on hover; a list would show everyone
- **Category:** list
- **Where:** `te_sr_sec_rivals` rows `:1155-1269` (`sr_rival_<m>_1..5`, per milestone ×8 in `te_sr_<m>_status`); `te_sr_sec_powers` rows `:5518-5605` (`sr_power_1..8`); "+N more" via `sr_rivals_sgui` / `sr_powers_sgui` ExecuteTooltip.
- **Now:** these were fixed slots because `.gui` "has no verified way to list countries" (header comment, `:66-67`, gotcha #15). Since then a datamodel of **states** from a script list has been proven: Demographics' `GetList('te_dg_states_top')` with `datacontext = "[Scope.GetState]"`. `State.GetCountry` from a stored capital is the proven route these rows already use (`Var('sr_power_1').GetState`).
- **Proposed:** have `sr_powers_refresh` and `sr_rivals_estimate_refresh` (`space_race_effects.txt`) also build a variable list of the powers' capital states in order (`sr_powers_list`, `sr_rivals_list_<m>`). Draw Space Powers as `datamodel = "[GetPlayer.MakeScope.GetList('sr_powers_list')]"` with items `datacontext = "[Scope.GetState]"`, reusing `te_sr_power_row`. Drop "+N more", or cap the list with `DataModelSubSpan` and keep it. Mind gotcha #24: an item's tooltip loses `JournalEntry`, so Rivals' row tooltips must read `GetPlayer` (fine: the panel is player-only). Play-test item: one self-check row, as for the other new accessors.
- **Effort:** large (script lists in two refreshes, GUI rewrite of two sections, tests)
- **Confidence:** medium (the accessor chain is new in this combination)

### SPC-10. The rival and power estimate hovers repeat a four-sentence explanation in nine keys
- **Category:** over-explaining
- **Where:** `je_space_race_widget_rival_tt_<m>` ×8 (`te_journal_entries_l_english.yml:1249-1256`), `je_space_race_widget_power_est_tt` (`:1151`), `je_space_race_widget_how_rivals` (`:1060`).
- **Now:** "#bold An estimate, not a report.#! From what X has announced, its programme stands between 34% and 84% of the goal (the marker: 59%). The band is ±25% of the goal, and the true figure is always inside it; where in the band the marker sits is drawn again once a year. An intelligence network in the country narrows the band: ±10% at strength 50, ±5% at 75." The band is already drawn on the row and its range printed beside it.
- **Proposed:** a concept `concept_sr_estimate` ("Programme Estimate") holding the band rules (±25%, the yearly redraw, the network narrowing). Each tooltip becomes "#header [State.GetCountry.GetName]#!\n[concept_sr_estimate]: #v 34%–84%#! of the goal (marker 59%)", with the current band width only when a network narrows it. `test_space_race_rivals.py:247-258` (`TooltipTest`) pins "estimate", "intelligence network" and `sr_disp_rival_band` in each `rival_tt`; update it to look for the concept.
- **Effort:** medium (new concept, nine loc edits, one test)
- **Confidence:** high

### SPC-11. The Space Race panel is off the house type ladder (rows 14, cells and the overview 12)
- **Category:** style (rule 3)
- **Where:** `space_race_widget.gui` uses `fontsize_medium` (14) ×56 and `fontsize_small` (12) ×73: `te_sr_text` / `te_sr_value_row` / `te_sr_note` (`:128-220`, rows 14); `te_sr_ov_icon_label` (`:269`, overview words 12); `te_sr_action_button` (`:237`, 12); every fleet, location and module column and every row button (12). The generated rows follow the types.
- **Now:** Seabed (`te_seabed_fontsize_*`, `te_seabed_widgets.gui:22-32`), Banking, Demographics and the Nation tab use rows 17, headings 20 and overview 16. The colony sections were written after the 2026-10-17 rule. Fleet and module figures a player decides on are at 12.
- **Proposed:** add `te_sr_fontsize_row/heading/overview` templates at the head of the file (17/20/16, the OpenSans overview as Seabed's) and point the types at them. Re-budget widths: the dense fleet (`:3943`) and module (`:3378`) rows will not fit 480 at 17. Shorten labels and move a column to hover (rule 3's order) before shrinking; `test_space_race_labels.py` measures each cell and follows template sizes if it reads them as `test_banking_layout.py` does. A larger pass, but the space panel is the one large system still at 12/14.
- **Effort:** large (widths across the panel and generators)
- **Confidence:** high (the inconsistency); medium (that every table can fit at 17 without SPC-5)

### SPC-12. Labels and column heads with a hover are not marked hoverable
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** hidden info (rule 3)
- **Where:** `te_sr_value_row`'s label (`space_race_widget.gui:202-210`) has no `#tooltippable`. Rows carrying a `tooltip` include: Estimate (`:988`), Settlers a month, People off Earth (`:3041, 3050`), Free colony trade (`:3340`), the four Colony Modules rows (`:3798-3825`), the four Space Command rows (`:4576-4605`) and the four Orbit rows (`:5649-5676`). The column heads with a hover: Crew, I, II, Hab, Port, Def (`:3713-3760`), Strength, Drive, km/s, Supply, Marines (`:3891-3929`), Others, Inbound (`:4277-4291`).
- **Now:** nothing tells the player that "Estimate", "Upkeep" or "km/s" open a breakdown. Siblings in the same panel do mark it inline ("#tooltippable Staged in Orbit#!", "#tooltippable Next Windows#!").
- **Proposed:** wrap each of those labels in `#tooltippable …#!` (Quick fixes; 29 keys, each used once, on a row or head that carries a tooltip). The width tests strip format codes (`test_space_race_labels.py:260`). Labels on rows without a hover (Setbacks So Far, Colonies Held, Fleets in flight, Where, Location, Ours, Status) stay plain. The cleaner long-term form is a `row_label_format` block in `te_sr_value_row` set to `#tooltippable` by rows with a tooltip.
- **Effort:** quick
- **Confidence:** high

### SPC-13. Stage names differ between the panel, the stage profile and the concept; the concept lists stages that don't exist
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** style (naming), other (stale)
- **Where:** `je_space_race_widget_colonies_stage_1..5` (`te_journal_entries_l_english.yml:843-847`: "Stage 1: Mars & Asteroids", "Stage 2: Jupiter System & Venus"…) against `je_space_race_solar_colonization_status_stage1..5` (`:789-793`, the overview Stage hover and Mission Profile: "Stage 1: Inner Solar System", "Stage 2: Gas Giant Frontier", "Stage 3: Mid-System Expansion", "Stage 4: Ice Giant Frontier"). `concept_solar_colonization_desc` (`te_concepts_l_english.yml:892`) gives five stages that match neither: "near-Earth asteroids and Lagrange points, Mars and lunar settlements, outer planet moons, dwarf planets and distant bodies, and multi-generation colonies". The real stages are in `gen_solar_sites.SITES` (`scripts/generators/gen_solar_sites.py:106-139`).
- **Proposed:** the Quick fixes table gives the profile headings the panel's names and rewrites the concept from the table. `concept_space_race_desc` (`:896`) is also stale: it gives only "a Safe or Ambitious approach" (no Standard, no `[concept_sr_approach]`), skips the Deep-Space Probe, and doesn't mention setbacks. `concept_space_milestone_desc` (`:894`) says each milestone needs "sufficient space program funding to complete", but funding speeds the pace, which never drops below 0.5 a month (`je_space_race_widget_pace_tt`). Both are rewritten in the table.
- **Effort:** quick
- **Confidence:** high

### SPC-14. Mission Profile restates the approach the overview shows; "Approach" means two things
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** spread-out/redundant, style (naming)
- **Where:** `je_space_race_<m>_status_{default,safe,ambitious}` ×21 (`te_journal_entries_l_english.yml:670-808`), read through `sr_<m>_profile` custom loc (`common/customizable_localization/space_race_custom_loc.txt`) into Mission Control's Mission Profile (`space_race_widget.gui:1020`); the moon-landing site profiles `je_space_race_moon_landing_status_{equatorial,far_side,shackleton,tranquility}` (`:737-741`).
- **Now:** under Safe, the overview's state cell reads "Safe −120/wk", the Approach buttons grey Safe, and Mission Profile opens "#bold Approach:#! Safe\n#bold Status:#! …". The landing-site profiles use "#bold Approach:#!" for the landing plan ("Methodical survey and landing at a well-mapped equatorial site"), which collides with `[concept_sr_approach]` (Standard/Safe/Ambitious). The Mars strategies use "#bold Strategy:#!" for the same job.
- **Proposed:** drop the "#bold Approach:#! X\n#bold Status:#! " prefix from the 21 approach profiles, leaving the flavour line, and drop the "#bold Approach:#! " label from the four landing-site profiles (Quick fixes). These keys are read only by the profile custom loc (grep: `space_race_custom_loc.txt` alone), and the approach stays visible in the overview and on the buttons.
- **Effort:** quick
- **Confidence:** medium-high (it trims flavour the owner may like; nothing is lost)

### SPC-15. Every colony row's autonomy drift hover shows the generic table, not that colony's terms
- **Category:** hidden info
- **Where:** `te_sr_autonomy_row` drift cell (`space_race_widget.gui:3128-3142`), `tooltip = "je_space_race_widget_autonomy_drift_tt"` (`te_journal_entries_l_english.yml:816`), the same key on every row; the figure is per site (`sr_disp_site_aut_drift_<key>`).
- **Now:** hovering "+0.35" on Ceres shows "• the pull of home: -0.25 • its people: +0.05 a 10,000 • its distance … • a charter: -0.4". That is every possible term with its rate, not which apply to Ceres or how much each adds now.
- **Proposed:** have `gen_solar_sites.py` emit a per-site `je_space_race_widget_autonomy_drift_tt_<key>`: the colony's actual terms, each line shown with `AddLocalizationIf` only when it applies, with its value from per-site script values. Most can be written from the `sr_aut_*` constants and the site's people, transit, contact, charter and garrison flags. Move the generic table into `concept_sr_colony_autonomy` (SPC-3).
- **Effort:** medium (generator, per-site values)
- **Confidence:** medium

### SPC-16. "Fleets" names two different things; the same icon marks colony and war fleets
- **Category:** style (naming)
- **Where:** section headers "Colony Fleets" (`je_space_race_widget_fleets_header`, `te_journal_entries_l_english.yml:1034`) and "Fleets" (`space_race_widget.gui:4729`, `je_space_race_widget_space_fleets_header` `:1307`), and the Space Command row "Fleets" (`sc_strength_label` `:1279`). The inbound cells of Solar System (colony fleets, `:2597`) and Locations (warships, `:4400`) both use `je_space_race_solar_colonization.dds`. `je_space_race_widget_loc_inbound_tt` (`:1080`) says only "fleets".
- **Now:** "Staged in Orbit: 1.4 fleets", "Fleets in flight 2 of 6", "Fleets" and "Fleets 120/160" sit within a few sections of each other.
- **Proposed:** name the warship section "Space Fleets" and the Space Command row "Fleet strength". Give Locations' inbound cell a military icon (placeholder per rule 10). Make the two concepts (`concept_sr_colony_fleet`, `concept_sr_space_fleet`) the hover on each word.
- **Effort:** quick (loc) + medium (icon)
- **Confidence:** medium

### SPC-17. How the Space Race Works restates the concepts it links
- **Category:** over-explaining (duplication within How)
- **Where:** `je_space_race_widget_how_approach` (`te_journal_entries_l_english.yml:1053`) against `concept_sr_approach_desc` (`te_concepts_l_english.yml:898`), near verbatim; `how_funding` (`:1055`) against `concept_sr_funding_desc` (`:900`); the lit/half-lit/faint legend in `ov_programme_tt` (`:1130`), `how_programme` (`:1059`) and `how_powers` (`:1058`).
- **Proposed:** keep How as the long form but cut the repeated sentences from one side: let the concepts be the definitions and How the cross-milestone rules ("every running milestone moves at the same pace…"). Give the programme legend one home (the programme header's hover) and have How refer to it. Low priority; `test_space_race_layout.py:67-71` pins only that the How keys exist.
- **Effort:** quick-medium (loc)
- **Confidence:** medium

### SPC-18. Orbit's strike hovers teach the action's rules inline
- **Category:** over-explaining
- **Where:** `te_orbit_strike_tt_ready` (`te_miscellaneous_l_english.yml:8261`: "A hostile diplomatic action against a country we are at war with, taken from the Diplomacy panel. It disrupts their orbital network, costs us infamy, relations and case strength at the UN…"), `te_orbit_satellites_tt_exposed` ("Any country at war with us that has Guided Missiles and a Space Program can strike them…"), both repeating `je_space_race_widget_how_orbit` (`te_journal_entries_l_english.yml:1057`).
- **Proposed:** a `concept_asat_strike` ("Anti-Satellite Strike") carrying the rules. The hovers become the state plus the concept: "Ready: [concept_asat_strike] from the Diplomacy panel against:" then the target list; "Intact. Exposed to an [concept_asat_strike] by any enemy with Guided Missiles." The debris row (`te_debris_row`, already `[concept_orbital_debris]`) is a good model.
- **Effort:** medium (concept + 2-3 loc)
- **Confidence:** medium

### SPC-19. Our Colonies is 1,100 hand-copied lines the generator could own
- **Category:** other (maintainability), list
- **Where:** `te_sr_sec_colonies` (`space_race_widget.gui:1329-2423`): 68 `te_sr_colony_row` instances written by hand, each gated on `sr_disp_colony_<world>_<spec>`. Every other per-world list is generated from `gen_solar_sites.SITES`.
- **Proposed:** if SPC-5 keeps the section, move its rows into `sr_sites_generated_rows.gui` (`te_sr_colony_rows`) from `SITES[*].specs`, as the other per-world rows are. The player sees no change; a new world or specialization can then no longer go missing from the panel.
- **Effort:** medium
- **Confidence:** high (low player impact)

### SEA-1. The overview's Policy and Regime hovers teach every option instead of ours
- **Category:** over-explaining, spread-out/redundant
- **Where:** `te_seabed_ov_policy_tt` (`te_miscellaneous_l_english.yml:8435`, overview cell `te_seabed_widgets.gui:583`), `te_seabed_ov_regime_tt` (`:8441`, cell `:607`); duplicated by `te_seabed_how_policy` (`:8376`), `te_seabed_how_regime` (`:8378`) and the three `te_seabed_policy_effect_<n>_tt` (`:8451-8453`).
- **Now:** the Policy cell's hover explains all three policies' weight factors, when weight counts, the influence held, the five-year lock and its two exceptions (seven sentences). The three buttons under it and How say the same. The Regime hover defines Open, Regulated and Scramble in full, including the poorer-parties reservation and the royalty rate, whichever regime is in force.
- **Proposed:** the cells answer "what is ours and what does it do to us now":
  - Policy: "#b [policy name]#!: claim weight ×0.5, holds #R 12#! [concept_influence]. Next change from #v 1987#!", plus the exceptions only when one applies.
  - Regime: the current regime's one line ("Regulated: half of each pool is reserved for poorer parties; we pay royalties of 2%, about $1.2k a mine"), plus a new `[concept_seabed_regime]` whose desc holds the three definitions now in `ov_regime_tt` / `how_regime`.
  
  How keeps its subsections. One home per definition.
- **Effort:** medium (concept + loc; the per-regime lines can use `SelectLocalization` on `te_seabed_regime_name`-style values)
- **Confidence:** high

### SEA-2. Seabed policies describe their effects in prose, not modifier lines
- **Category:** style
- **Where:** `te_seabed_policy_<1..3>_sgui` (`common/scripted_guis/te_global_commons_seabed_sguis.txt:12-58`), each wrapping `te_seabed_set_policy` in `custom_tooltip = { text = te_seabed_policy_effect_<n>_tt … }`; loc `:8451-8453` ("our claim weight ×0.5, and no influence held").
- **Now:** the button hovers are sentences with inline figures. The influence cost is a real modifier (`te_seabed_policy_sponsor_cost` / `_unilateral_cost`, `country_influence_cost_add`, `common/static_modifiers/te_global_commons_seabed_modifiers.txt:38-46`), but it is applied with a multiplier and hidden behind the custom tooltip. Global Warming's policy rows (the house model) print a flavour line plus `[GetStaticModifier('…').GetDesc]`.
- **Proposed:** register `script_only` modifier types for what the policy does, e.g. `country_seabed_claim_weight_mult` and `country_seabed_naval_weight_mult` (loc in `te_modifiers_l_english.yml`, `common/modifier_type_definitions/`). Define one display static modifier per policy (`te_seabed_policy_survey_display`: weight −50%; `_sponsor_display`: claims protected …; `_unilateral_display`: weight, naval ×2, relations), then make each effect tooltip "Adopt #b Sponsor Contractors#!:\n[GetStaticModifier('te_seabed_policy_sponsor_display').GetDesc]\nHolds #R N#! [concept_influence] now. Locks the policy for #v 5#! years." The weight factor stays script-read; the modifier is display and does not need to drive it.
- **Effort:** medium (modifier types, three static modifiers, loc)
- **Confidence:** medium

### SEA-3. The claimant rows are sentences under a table of columns
- **Category:** list, style
- **Where:** `te_seabed_rival_row` / `te_seabed_rival_us` (`te_seabed_widgets.gui:379-434`), six fixed rows per basin ×5 (`:790-873` for the Pacific), text from `te_seabed_rival_row_sgui` (`te_seabed_rival_row_<basin>`, `te_miscellaneous_l_english.yml:8478`), and "and N other claimants" (`te_seabed_rivals_more_<basin>`).
- **Now:** "France: 12 mines · 3 claims · 14% of the weight", wrapping on long names, under a basin header row whose columns are Free / Pool / Weight / +1 licence. "Us: …" sits in the same prose.
- **Proposed:** give claimant rows fixed columns aligned under the basin table: flag + name (elided, full name on the flag's hover), Mines, Claims, Weight %, with Relinquish/Claim Again in our row's last cell. The figures can stay script-printed per cell (one `ExecuteTooltip` per cell, or three `custom_tooltip_no_bullet` keys per op). Later, the SPC-9 pattern (a list of capital states as a datamodel) would replace the six slots and "and N other claimants".
- **Effort:** medium (row layout, loc split); large with the datamodel
- **Confidence:** medium

### SEA-4. Basin names read "in the Indian" / "in the Southern"
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** style
- **Where:** `te_seabed_build_in_head_indian/_southern` (`te_miscellaneous_l_english.yml:8323, 8325`), `te_seabed_build_in_none_indian/_southern` (`:8333, 8335`), `te_seabed_next_tt_indian/_southern` (`:8408, 8410`), `te_seabed_weight_tt_indian/_southern` (`:8512, 8514`). Outside this slice, the state panel's `TE_STATE_SEABED_WEIGHT_NONE` (`:1060`, "in the Southern while…").
- **Proposed:** "the Indian Ocean", "the Southern Ocean" in running text; the table keeps the one-word names. Quick fixes table.
- **Effort:** quick
- **Confidence:** high

### SEA-5. The +1 licence caveat is repeated in five basin hovers
- **Category:** over-explaining
- **Where:** `te_seabed_next_tt_<basin>` ×5 (`te_miscellaneous_l_english.yml:8406-8410`) all end "Enough, all else equal; often more than needed."; the column head's `te_seabed_col_next_tt` (`:8348`) says it at length ("The figure is enough, often more than needed: the sharing's rounding can hand the licence over sooner."), and `test_seabed_loc.py:55-57` pins "enough" there.
- **Proposed:** keep the caveat on the column head only (rule 6: said once). Cut the per-basin sentence, or shorten it to "(enough; often more than needed)". Low priority; listed so the cut isn't made on the pinned head key.
- **Effort:** quick
- **Confidence:** medium

### SEA-6. The Pool column head restates the legend under the table
- **Category:** spread-out/redundant
- **Where:** `te_seabed_col_pool_tt` (`te_miscellaneous_l_english.yml:8350`) lists "our built mines, our queued mines (lighter), our unused claims, rivals' mines, and the rest (dark)…". The five legend chips under the table (`te_seabed_widgets.gui:1654-1739`) name the same layers, and every basin's bar hover (`te_seabed_pool_tt_<basin>`) gives the counts.
- **Proposed:** shorten the head's hover to what the legend lacks: "The basin's whole pool; colours as in the legend below. Rivals' unused claims and the shares waiting for countries without $abyssal_plain_mining$ are divided again at every sharing, so a buildup could win them. Rivals' figures are as of the last sharing." Low priority.
- **Effort:** quick
- **Confidence:** medium

### Notes (checked, no finding)
- The Seabed tab follows the house style closely: six-box overview, type ladder templates, Concatenated reasons on its buttons, How collapsed. Its claimant lists start collapsed against rule 1 ("live list open"), but the comment (`te_seabed_widgets.gui:691-694`) records why ("five open lists would push the rest off the panel"). That is a reasoned exception.
- The journal entries' `status_desc` show only while inactive (`je_space_race.txt:118-128`), per rule 1. The overview does not repeat them.
- Colony specialization hovers use `GetStaticModifier(...).GetDesc` throughout (`je_space_race_widget_colony_*_tt`), and emigration, off-world population and module upkeep render their modifiers. These are good models.
- `te_debris_row_tt` prints the scaled debris effects as prose numbers because the multiplier varies; acceptable. The row label is already `[concept_orbital_debris]`.
- American spelling (low priority, once): "Ganymede Command Center" (`sr_colony_ganymede_command`, `te_miscellaneous_l_english.yml:5882`) and "Fortune favors the bold" (`je_space_race_suborbital_status_ambitious`, `te_journal_entries_l_english.yml:806`). Otherwise the slice keeps "licence", "Defences" and "programme"; "Space Program" is the building's name.

## Applied in this PR

73 loc-only edits from this slice were applied (text rewritten in place, keys unchanged). The pre-edit text is in git history; the finding each serves is named above. Keys:

`concept_solar_colonization_desc`, `concept_space_milestone_desc`, `concept_space_race_desc`, `je_space_race_interstellar_probe_status_ambitious`, `je_space_race_interstellar_probe_status_default`, `je_space_race_interstellar_probe_status_safe`, `je_space_race_mars_landing_status_ambitious`, `je_space_race_mars_landing_status_default`, `je_space_race_mars_landing_status_safe`, `je_space_race_moon_base_status_ambitious`, `je_space_race_moon_base_status_default`, `je_space_race_moon_base_status_safe`, `je_space_race_moon_landing_status_ambitious`, `je_space_race_moon_landing_status_default`, `je_space_race_moon_landing_status_equatorial`, `je_space_race_moon_landing_status_far_side`, `je_space_race_moon_landing_status_safe`, `je_space_race_moon_landing_status_shackleton`, `je_space_race_moon_landing_status_tranquility`, `je_space_race_orbital_status_ambitious`, `je_space_race_orbital_status_default`, `je_space_race_orbital_status_safe`, `je_space_race_probe_status_ambitious`, `je_space_race_probe_status_default`, `je_space_race_probe_status_safe`, `je_space_race_solar_colonization_status_stage1`, `je_space_race_solar_colonization_status_stage2`, `je_space_race_solar_colonization_status_stage3`, `je_space_race_solar_colonization_status_stage4`, `je_space_race_suborbital_status_ambitious`, `je_space_race_suborbital_status_default`, `je_space_race_suborbital_status_safe`, `je_space_race_widget_ebase_label`, `je_space_race_widget_emig_month_label`, `je_space_race_widget_eta_label`, `je_space_race_widget_fab_label`, `je_space_race_widget_fl_col_drive`, `je_space_race_widget_fl_col_dv`, `je_space_race_widget_fl_col_marines`, `je_space_race_widget_fl_col_strength`, `je_space_race_widget_fl_col_supply`, `je_space_race_widget_free_trade_label`, `je_space_race_widget_loc_col_inbound`, `je_space_race_widget_loc_col_others`, `je_space_race_widget_mod_def_tt`, `je_space_race_widget_mod_port_tt`, `je_space_race_widget_mod_upkeep_label`, `je_space_race_widget_modules_col_a`, `je_space_race_widget_modules_col_b`, `je_space_race_widget_modules_col_def`, `je_space_race_widget_modules_col_hab`, `je_space_race_widget_modules_col_port`, `je_space_race_widget_modules_col_staffing`, `je_space_race_widget_offworld_label`, `je_space_race_widget_orbit_moratorium_label`, `je_space_race_widget_orbit_satellites_label`, `je_space_race_widget_orbit_strike_label`, `je_space_race_widget_orbit_strikes_label`, `je_space_race_widget_sc_rate_label`, `je_space_race_widget_sc_reserve_label`, `je_space_race_widget_sc_strength_label`, `je_space_race_widget_sc_upkeep_label`, `je_space_race_widget_shipments_label`, `sr_mod_queue_def_tt`, `sr_mod_queue_port_tt`, `te_seabed_build_in_head_indian`, `te_seabed_build_in_head_southern`, `te_seabed_build_in_none_indian`, `te_seabed_build_in_none_southern`, `te_seabed_next_tt_indian`, `te_seabed_next_tt_southern`, `te_seabed_weight_tt_indian`, `te_seabed_weight_tt_southern`
