# Vanilla-panel additions and other journal entries — GUI & localization audit

> Part of the 2026-10-27 GUI and localization audit; the index, the cross-cutting findings and the owner questions are in [`../gui_localization_audit.md`](../gui_localization_audit.md). Line numbers are as of the audit and drift as files change; search by key or type name. "Quick fixes" below means the loc-only edits this PR applied.

## Top priorities

- **State Collapse never says what it does** (JE-1): when its 52-week bar fills, every state loses its
  barracks, ports, railways, universities and government administration and every institution is
  abolished, and the entry's only text is an encyclopedia definition. Reason rewrite is a quick fix; add a
  status that lists the consequence and a legible goal line.
- **Hidden decision inputs in three entries** (JE-3, JE-4, JE-2): World War's ideological tension, which
  gates the status and every button, is printed nowhere and its greyed buttons show raw `has_variable` /
  script-value lines; Civil Rights' endings depend on per-policy months nobody can see; Create New
  Religion's Proclaim button hides conversions and exiles inside a `custom_tooltip`, and its ~140 buttons
  print their sentence twice.
- **Construction Market section** (VAN-1, VAN-2, VAN-3): an always-open intro paragraph, the explainer
  written twice (How-it-works and the concept), six read-out sentences that should be a label/value table,
  and the same three rules in five or six tooltips.
- **State-view tile hovers that teach instead of break down** (VAN-5, VAN-6, VAN-9, VAN-11): Migration
  Crowding's curve lesson, Homeland's eight paragraphs and three units for one rate, the UN tile's 90-word
  sentence, the tourism headers' inlined concept text. Most are quick fixes below.
- **Duplicated button text in vanilla-grid entries** (JE-5, JE-2b, JE-3d): button descs that restate the
  IG-approval and modifier lines the engine prints beside them, and stop buttons whose desc and effect line
  are the same sentence.
- **Row hovers in the state tiles are invisible** (VAN-10): grid, seabed and wealth rows carry their own
  detailed hovers with no `#tooltippable` underline.

Scope notes. The building panels (`building_details_panel.gui`, `building_browser_panel.gui`,
`states_panel_buildings.gui`, `production_methods.gui`, `goods_state_panel.gui`), `politics_panel_*.gui`,
`power_bloc_formation_panel.gui`, `principle_selection_window.gui`, `military_formation_panel.gui`,
`journal_entry.gui`, `00_te_law_effects.gui` and `right_click_menu.gui` (outside the Tax Code blocks) carry
only layout fixes (PM strips that scroll past four/five groups, the hidden `pmg_maintenance*` groups in the
condensed strips, the bars-on-top marker, the tax-law hover) or vanilla debug items; none adds player text
worth changing. The treaty panels add one quantity box ("warheads", covered in the Nuclear findings). The mod's text
in vanilla panels lives in the state view's tiles and cards, the construction panel's market section and the
power bloc's locked principle slots, so Part 1 is mostly those. Resource-transition buttons are AI-only
(`is_ai = yes`), so nothing in them renders for a player.

## Findings

### VAN-1. Construction Market: an always-open intro paragraph, and the explainer written twice
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** over-explaining / spread-out/redundant
- **Where:** `gui/construction_panel.gui:1006-1014` (intro textbox under the section header), `:1297-1328`
  (How-it-works toggle); loc `TE_CM_SECTION_INTRO` (`te_miscellaneous_l_english.yml:955`),
  `TE_CM_HOW_IT_WORKS` (`:946`), `TE_CM_HOW_IT_WORKS_BODY` (`:947`), `concept_te_construction_market_desc`
  (`te_concepts_l_english.yml:918`)
- **Now:** every visit to the construction panel opens with a four-line paragraph ("Construction is a
  tradeable good. Construction Sector buildings produce it and sell it on the market, and Construction Sites
  turn what is bought into the construction points that the queues below spend. Set how much the government
  buys, or spends, each week; private investors buy …"), above the controls. Below them, the collapsed
  "How does the construction market work?" holds five numbered paragraphs (Supply, Your purchase, Private
  purchase, Delivery, Shortages). The concept `concept_te_construction_market`, which the intro links, holds
  the same five topics again (Supply, Purchase, Delivery, Maintenance, Price) at similar length.
- **Proposed:** (1) Cut the intro to the sentence that says what the controls do, plus the concept link
  (Quick fixes has the text; or drop the textbox, since the header and the mode buttons already say it).
  (2) Keep one explainer. Either make the collapsed body a pointer to the concept, or (better, since the
  panel is where players look) keep the body and shorten the concept to its first paragraph plus "The
  construction panel's How the Construction Market Works has the detail." (3) Rename the toggle to the
  house form, "How the Construction Market Works" (style guide rule 1, "How X Works"); in Quick fixes.
- **Effort:** quick (rename, intro) / medium (merging the two explainers)
- **Confidence:** high

### VAN-2. Construction Market read-out: six sentences that should be a label/value table
- **Category:** style / list
- **Where:** `gui/construction_panel.gui:1230-1293` (LIVE READ-OUT, six left-aligned multiline textboxes);
  loc `TE_CM_STAT_GOVERNMENT` (`:960`), `TE_CM_STAT_BUDGET` (`:956`), `TE_CM_STAT_BUDGET_STEP` (`:957`),
  `TE_CM_STAT_PRIVATE` (`:970`), `TE_CM_STAT_PRICE` (`:968`), `TE_CM_STAT_MARKET` (`:965`)
- **Now (figures illustrative):** "Government buys: 12.0 per week, ~@24.1K from the treasury (capped at what the queue can use)",
  "Your budget buys: 13.5 per week at today's price", "Still moving toward it: about 50% of the gap closes
  each week", "Private investors buy: 30.0 per week (71% of construction goes to private projects)",
  "Price: @1,004 per construction point", "Your market: 40.0 on sale, 44.0 wanted (shortage)". Each is a
  sentence of different length, so the figures sit at different x positions and wrap at the panel edge.
- **Proposed:** a two-column table (rule 5): label left in a fixed column, value right-aligned, one figure
  per row, the qualifier as hover or as a coloured word:
  `Government | 12.0/wk (@24.1K)` · `Budget buys | 13.5/wk` (budget mode only) · `Closing | 50%/wk`
  (while stepping) · `Private | 30.0/wk (71%)` · `Price | @1,004` · `Market | 40.0 / 44.0 #R Short#!`.
  Each row keeps its current tooltip. The `te_state_stat_row` type in `gui/te_state_panel_widgets.gui`
  already does exactly this (label column + right-anchored value column) and can be reused with wider
  `label_size`/`value_size` blockoverrides. Put the "(capped at what the queue can use)" note as a `#R`
  "Capped" word whose hover is `TE_CM_STAT_GOVERNMENT_TT`.
- **Effort:** medium (GUI rows + split each stat key into a label and a value key)
- **Confidence:** high

### VAN-3. Construction Market tooltips: the same three rules restated in five or six tooltips
- **Category:** spread-out/redundant / over-explaining
- **Where:** loc `TE_CM_PURCHASE_TT` (`:953`), `TE_CM_BUDGET_PURCHASE_TT` (`:944`), `TE_CM_MODE_BUDGET_TT`
  (`:950`), `TE_CM_STAT_BUDGET_TT` (`:959`), `TE_CM_STAT_BUDGET_STEP_TT` (`:958`), `TE_CM_STAT_GOVERNMENT_TT`
  (`:964`), `TE_CM_HOW_IT_WORKS_BODY` (`:947`)
- **Now:** "Only what the government queue can use this week is actually bought …" appears in
  `TE_CM_PURCHASE_TT`, `TE_CM_BUDGET_PURCHASE_TT`, `TE_CM_STAT_BUDGET_TT`, `TE_CM_STAT_GOVERNMENT_TT` (as
  "The purchase in force is the smaller of the first two") and How-it-works. "A raise takes a few weeks to
  feed through; a cut takes hold faster" (the phase-in) appears in `TE_CM_BUDGET_PURCHASE_TT`,
  `TE_CM_MODE_BUDGET_TT` (a full paragraph on why), `TE_CM_STAT_BUDGET_STEP_TT` (another full paragraph on
  why) and How-it-works. "AI countries choose their own purchase from their income, reserves and debt" sits
  in both purchase tooltips, though no player acts on it.
- **Proposed:** give each rule one home and a short reference elsewhere. Phase-in: keep the explanation in
  `TE_CM_STAT_BUDGET_STEP_TT` (it appears exactly while stepping) and cut it from `TE_CM_MODE_BUDGET_TT`
  to one sentence ("A raise is phased in over a few weeks; a cut takes hold faster.") and from
  `TE_CM_BUDGET_PURCHASE_TT` entirely. Queue cap: keep it in `TE_CM_STAT_GOVERNMENT_TT` (which shows the
  two numbers) and in the stepper tooltips drop it. Drop the AI sentence from both purchase tooltips
  (How-it-works can keep it). A new concept, `concept_te_construction_queue_cap` ("Queue cap"), would let
  every one of them say "capped at the [concept_te_construction_queue_cap]".
- **Effort:** quick (text cuts) to medium (concept)
- **Confidence:** high

### VAN-4. Direct Construction section: an always-open paragraph that ends with a developer note
- **Category:** over-explaining / other
- **Where:** `gui/construction_panel.gui:1356-1364`; loc `TE_DC_SECTION_INTRO` (`te_miscellaneous_l_english.yml:973`)
- **Now:** with the Free Market Construction rule off, the panel opens with a five-sentence paragraph ("The
  Free Market Construction game rule is off, so construction works as in the base game. Your Construction
  Site buildings are your construction sector: build, expand and downsize them like any government
  building. Each level provides … To build faster, add levels or switch to a better production method.")
  and then, in bold, "#b Construction Sites must currently be built from the state view.#! This is a
  technical limitation that is being worked on."
- **Proposed:** one line, the actionable part kept: "Construction comes from your $te_construction_market_site$
  buildings; build them from a state's view." The mechanics already sit in `TE_DC_STAT_CAPACITY_TT` (the
  per-method figures and materials) and `concept_te_construction_market_desc`'s last paragraph. A
  roadmap note ("being worked on") is not player text; if the limitation stands, state it as a fact.
  Check in game first whether the limitation still holds (the "No Construction Sector" widget at
  `:1465-1508` offers the Site from this panel already).
- **Effort:** quick
- **Confidence:** medium (the "state view only" claim needs a play-test check)

### VAN-5. Migration Crowding tile: the hover is a lesson in the curve, and repeats the tile
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** over-explaining
- **Where:** `gui/states_panel.gui:2242-2311` (tile); loc `TE_STATE_CROWDING_TT` (`te_miscellaneous_l_english.yml:1019`),
  `concept_migration_crowding_desc` (`te_concepts_l_english.yml:843`)
- **Now:** the tile already shows Population, Threshold, Ratio (with a bar) and Pull Penalty. Its hover
  repeats Population, Crowding Threshold and Migration Pull Penalty, then gives the threshold formula with
  this state's terms (useful), then "0% is the floor where crowding starts. 100% is the 10x density knee …",
  "#bold How the curve works:#! From the floor up to the 10x knee, crowding scales as 4.5 × r² …", three
  example penalties, and a sentence listing every source of Urban Engineering and density.
- **Proposed:** keep the hover to the reading's breakdown: header, the threshold formula with this state's
  three terms, and the ratio line. Move "How the curve works" and the examples into
  `concept_migration_crowding_desc` (which already says the ramp is quadratic then linear, so it only needs
  the 4.5 × r² / 9r − 4.5 figures and the three examples), and let the tile name `[concept_migration_crowding]`
  (it does: `TE_STATE_CROWDING_STATUS`). Drop the three repeated lines at the top. The list of what raises the
  threshold ("from the early urban technologies, $urbanization$ to $elevator$ … national parks, forests and
  wildlife refuges lower it") is the breakdown `GetValueWithBreakdownFor('state_migration_crowding_density_mult')`
  already prints on hover; cut it.
- **Effort:** quick (loc), the concept edit included; both keys are in Quick fixes
- **Confidence:** high

### VAN-6. Homeland Dynamics tile: rules in prose, rate units that disagree, and a tile that is always there
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** over-explaining / style / spread-out
- **Where:** `gui/states_panel.gui:2156-2169`, `gui/te_state_panel_widgets.gui:985-1165`; loc `TE_STATE_HOMELAND_TT`
  (`te_miscellaneous_l_english.yml:1042`), `TE_HOMELAND_TRACK_ACTIVE` (`:1004`), `TE_HOMELAND_REMOVAL_TRACK_ACTIVE`
  (`:1002`), `TE_HOMELAND_NOTHING_TO_CHANGE` (`:992`), `concept_homeland_dynamics_desc` (`te_concepts_l_english.yml:825`)
- **Now:** (a) The tile's rows say "+0.83 points/month" (`te_homeland_monthly_points`), its hover says
  "Base Rate: 10 percentage points per year. Modified Rate: 10.00 points per year. Removal Rate: …", and the
  project bars read in %. Three units for one rate. (b) The hover is eight paragraphs: independent progress
  "without random rolls", the creation and removal thresholds (both already on the tile's Blocked lines with
  their own hovers), the rates, "Turmoil of 25% / 50% multiplies progress by 1.25 / 1.5. Legitimacy below 25
  halves progress; legitimacy of 75 or more multiplies it by 1.25." as a sentence, then the region-owner and
  unlock rules and what resets progress. (c) The tile is shown on every state of every country ("always
  visible, including before unlock", `states_panel.gui:2156`), so most states carry a tile that reads "No
  culture here can gain or lose homeland status." or "Paused: needs a law, principle or technology …".
- **Proposed:** (a) one unit, "% a year", everywhere: the bar is a %, and the monthly pulse adds
  `te_homeland_annual_progress` to a 1,200-point counter (`homeland_effects.txt:63`, `extra_on_actions.txt:3666`),
  so the annual figure is exactly the bar's % a year. The two track keys are in Quick fixes; the hover's Rate
  lines then say "% a year" too. (b) Cut the hover to a table: `Rate: +10% a year`, `Removal Rate: …`, `Change Speed:
  <breakdown>`, then the multipliers as a list ("• [concept_turmoil] 25%+: ×1.25 / 50%+: ×1.5", "• [concept_legitimacy]
  under 25: ×0.5 / 75+: ×1.25"), then the unlock list. The "how it works" sentences (independent progress,
  no random rolls, resets) go in `concept_homeland_dynamics_desc`, which the tile title already links.
  (c) Hide the tile when `te_homeland_relevant = 0` (nothing can change here); keep it for the paused
  cases, which are actionable. That reverses the "always visible" comment, which cites no owner decision,
  but check with the owner.
- **Effort:** quick (loc, a/b) / medium (c, one `visible`)
- **Confidence:** high (a, b), medium (c)

### VAN-7. Solar Collector / Antimatter tiles: country-wide figures repeated in every state, and again on hover
- **Category:** spread-out/redundant
- **Where:** `gui/states_panel.gui:2313-2389`; loc `TE_STATE_SOLAR_TT` (`:1062`), `TE_STATE_ANTIMATTER_TT` (`:1008`),
  `TE_STATE_POINTS_ROW_AVAILABLE`/`_GENERATED` (`:1043-1044`)
- **Now:** both tiles are gated on the **owner's** total (`State.GetOwner.MakeScope.ScriptValue('solar_total_generated_points') > 0`)
  and show the owner's Available and Generated, so every state of a country with one Solar Collector carries
  the same tile with the same two numbers. The hover restates both ("Total Generated", "Net Available") and
  adds two more, starting with an empty line after the header (`#!\n\n`).
- **Proposed:** the slots are a country-wide pool (`modifier:country_solar_receiver_max_level_add`,
  `common/script_values/extra_script_values.txt:2843`), so the figure answers "can I still build a receiver
  anywhere", not anything about this state. Either show the tile only in states that hold a Solar Collector /
  Antimatter Facility or a receiver/sub-building (where the player is looking at that chain), or move the
  reading to where the decision is made: the receiver's build tooltip or the Space Race tab's overview. In
  either case keep the hover to the two lines the tile lacks (Active Structures, Reserved) plus the one-line
  rule, and drop the blank line after the header. Side note: `solar_total_generated_points` and its siblings
  iterate every state's buildings, and the tile reads them in `visible`, two rows and the hover on every
  frame the state panel is open (`scripting_best_practices.md`, "evaluated on every frame"); a state gate
  read from a monthly-stored variable would also remove that cost.
- **Effort:** medium (a gate or a move)
- **Confidence:** medium (that the tile is redundant per state is certain; where the figure belongs is a design call)

### VAN-8. Seabed Licences tile: a five-basin table written as text, in every coastal state
- **Category:** list / spread-out/redundant
- **Where:** `gui/states_panel.gui:2390-2492`; loc `TE_STATE_SEABED_TT` (`:1059`)
- **Now:** the hover prints, for each of five basins, "Pacific: 3, 1; 12 of 40 (weight 4.2)" — four
  unlabelled numbers per line, decoded by a legend in brackets above ("Our licences and unused claims (and
  the world's licences in use, of the pool)") — then a `#lore` paragraph with the weight formula. The figures
  are the country's and the world's, not this state's, and they repeat on every coastal state. The Seabed tab
  (`gui/te_seabed_widgets.gui`) has a basins table already.
- **Proposed:** keep the tile's hover to this state and its basin (the row hovers already do that well) plus
  one country line ("Across the country: 7 in use of 9, 2 from other basins") and "Every basin: the Seabed
  tab of the Timeline Extended window." (rule 9, send players to the tab). Drop the five basin lines and the
  formula paragraph, which `TE_STATE_SEABED_ROW_WEIGHT_TT` gives for this state. `test_seabed_loc.py` checks
  `TE_STATE_SEABED*` keys exist and render; re-run it.
- **Effort:** quick (loc)
- **Confidence:** medium (overlaps the Seabed tab's findings; the tile is a vanilla-panel insertion)

### VAN-9. UN Mission tile: every kind's success rule in one sentence, though the state has one kind
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** over-explaining / list
- **Where:** `gui/states_panel.gui:2640-2716`; loc `TE_STATE_UN_MISSION_TT` (`:1066`)
- **Now:** the last paragraph is one 90-word sentence: "A peacekeeping mission succeeds after two years of
  peace for this country; an aid mission after at least six months, once …; a stabilisation mission once the
  collapse is over …; an electoral observer mission when an election campaign here ends. A mission fails if
  …", for all four kinds, whatever the kind in this state.
- **Proposed:** show only this mission's rule, by kind, as two lines "Succeeds: …" / "Fails: …"
  (`AddLocalizationIf` on `un_state_mission_type`, as `TE_STATE_UN_ROW_KIND_VALUE` already does), each kind's
  concept carrying the others. New keys `TE_STATE_UN_SUCCESS_<KIND>` / `TE_STATE_UN_FAIL_<KIND>`. Until then, Quick fixes has the same text as a bulleted list.
- **Effort:** quick-medium (new loc keys, no GUI)
- **Confidence:** high

### VAN-10. State tiles' per-row hovers are not marked hoverable
- **Category:** hidden info
- **Where:** `gui/te_state_panel_widgets.gui:27-82` (`te_state_stat_row`'s label/value textboxes have no
  `default_format = "#tooltippable"`); rows with their own `row_tooltip`: the Power Grid tile's seven rows
  (`states_panel.gui:2517-2640`), the Seabed tile's four (`:2419-2490`), Wealth Concentration's score row
  (`te_state_panel_widgets.gui:1186-1198`), the tourism card's meters.
- **Now:** each of these rows has a detailed hover of its own (`TE_STATE_GRID_ROW_CABLES_TT` lists the
  stations a cable joins; `TE_STATE_SEABED_ROW_WEIGHT_TT` is the state's weight breakdown), but the row looks
  like plain text, and the tile has a hover of its own, so a player who hovers the tile once and sees its
  text has no cue that the rows hold different text.
- **Proposed:** add a `block "label_format" { default_format = "#tooltippable" }` to `te_state_stat_row`'s
  label textbox, overridden in the rows that carry `row_tooltip` (or always on when `row_tooltip` is set), so
  rows with their own hover are underlined (rule 3, "Hoverable text is underlined").
- **Effort:** medium (GUI tweak)
- **Confidence:** high

### VAN-11. Tourism card: headers inline their concept's description, and two tooltip pairs repeat each other
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** over-explaining / list
- **Where:** `gui/te_state_panel_widgets.gui:265-522`; loc `te_state_tourism_output_tt` (`:8530`),
  `te_state_tourism_throughput_tt` (`:8535`), `te_state_tourism_output_applied_tt` (`:8529`),
  `te_state_tourism_throughput_applied_tt` (`:8534`), `te_state_tourism_monuments_tt` (`:8528`)
- **Now:** (a) the two column headers' hovers print `$concept_tourism_output_desc$` in full, under a header
  whose label is already `[concept_tourism_output]`, then the same two boilerplate sentences each ("It is
  applied to the state as a modifier and refreshed each month. The bar under each source shows how close it
  is to its maximum."). (b) The two footer hovers end with the same sentence ("The sources above are
  re-applied each month, so a change there shows up here after the next monthly update."). (c) The Monuments
  hover lists eight wonders and their bonuses in one sentence.
- **Proposed:** (a) header hovers: "#bold [concept_tourism_output]#!\nThe sources below: #v +X%#!. Each bar
  shows how near its source is to its maximum." — the concept is one hover away on the label. (b) say "as
  last applied, monthly" once in each footer hover and drop the closing sentence. (c) a bullet list — quick
  fix below. `test_tourism_heritage.py` pins "monument" being present in `te_state_tourism_output_applied_tt`
  and `concept_tourism_output_desc` and absent from the throughput texts; the proposals keep both.
- **Effort:** quick
- **Confidence:** high

### VAN-12. Arable Land tile hover: repeats the rows, then explains the split-state accounting
- **Category:** over-explaining
- **Where:** `gui/states_panel.gui:2171-2216`; loc `TE_STATE_ARABLE_TT` (`:1013`)
- **Now:** the tile shows Total, Regional and Multiplier; the hover shows Total, Geographic Base, Regional
  Additions and Multiplier, then "Agricultural technologies and other arable-land effects expand arable land
  beyond the geographic base. In split states, the regional additions line sums same-owner additions across
  the whole state region so migration crowding thresholds stay accurate."
- **Proposed:** keep the four figure lines (the Base line is the one the tile lacks) and drop the closing
  paragraph; the second sentence is an implementation note.
- **Effort:** quick
- **Confidence:** high

### VAN-13. Power bloc: the locked principle slots are a model; one small inconsistency
- **Category:** other (positive) / style
- **Where:** `gui/power_bloc_panel.gui:1546-1735`; loc `te_pb_locked_slot_3_tt`…`_8_tt`,
  `te_pb_locked_slot_sources_tt` (`te_miscellaneous_l_english.yml:8266-8272`), sgui
  `te_pb_principle_slot_sources_sgui` (`common/scripted_guis/te_power_bloc_sguis.txt`)
- **Now:** a locked slot's hover says what opens it and renders the sources as a ticked/crossed checklist via
  `IsValidTooltip`, which is exactly rule 6. The Remove button's hover (`te_pb_remove_principle_tt`) is one
  line and names the cost (mandates not refunded). Only nit: `te_pb_locked_slot_sources_tt` restates the rank
  and member count ("It is ranked #3 with 7 members") that the checklist's two rank lines then test.
- **Proposed:** none needed; optionally drop the "It is ranked …" sentence. Use this pattern as the reference
  for the journal-entry button reasons in Part 2 (JE-3).
- **Effort:** quick
- **Confidence:** high

### JE-1. State Collapse: the entry never says what the collapse does, and frames it as a goal
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** hidden info / over-explaining
- **Where:** `common/journal_entries/timeline_extended_journal_entries.txt:1-81` (`je_state_collapse`);
  loc `je_state_collapse_reason` (`te_journal_entries_l_english.yml:1335`), `je_state_collapse_desc` (`:1334`);
  effects `state_collapse_remove_infrastructure` / `reset_all_institutions_and_ministries`
  (`common/scripted_effects/extra_effects.txt:1270-1309`)
- **Now:** the panel's text is an encyclopedia definition: "State Collapse is the failure of a state to
  provide basic services and security to its citizens. This can be caused by a variety of factors, including
  corruption, conflict, and natural disasters. State Collapse can lead to widespread suffering, displacement,
  and violence." There is no status text. The bar fills over 52 weeks (`current_value` / `goal_add_value`),
  and the goal tooltip prints the raw trigger `ROOT.var:state_collapse_progress >= 52`, so the bar reads as
  progress toward something to achieve. When it fills, every state loses its Barracks, Naval Administration,
  Naval Fortification, Naval Logistics Center, Military Base, Port, Railway, University and Government
  Administration, every institution and ministry is abolished, and the country takes Failed State. None of
  this is said anywhere a player can read before it happens; nor that raising the average standard of living
  above 4 ends the entry (`possible = average_sol < 4`, `can_deactivate = yes`).
- **Proposed:** (1) rewrite the reason to say the trigger, the consequence and the way out (quick fix
  below). (2) Add a `status_desc` that lists the consequence as engine lines:
  `"When the bar fills:\n• every state loses …\n• every institution and ministry is abolished\n[GetStaticModifier('failed_state_modifier').GetDesc]"`.
  (3) Wrap `complete` in `custom_tooltip = { text = je_state_collapse_complete_tt … }` ("52 weeks in a row
  with an average [concept_sol] below #v 4#!: the state collapses"), so the goal line is legible.
  `test_state_collapse.py` pins the gates and the modifier refresh, not the loc.
- **Effort:** quick (reason) / medium (status_desc, custom tooltip)
- **Confidence:** high

### JE-2. Create New Religion: the Proclaim button hides everything it does, and the builder has no "where am I"
- **Category:** hidden info / style
- **Where:** `common/journal_entries/timeline_extended_journal_entries.txt:83-280`;
  `common/scripted_buttons/timeline_extended_scripted_buttons.txt:965-5880` (the select/deselect, back/next
  and `create_new_religion` buttons); loc `CREATE_NEW_RELIGION_DESC` (`te_miscellaneous_l_english.yml:285`),
  `SELECT_*`/`DESELECT_*` (`te_religion_l_english.yml`, `te_concepts_l_english.yml:93-170`),
  `je_create_new_religion_reason` (`te_journal_entries_l_english.yml:363`)
- **Now:** (a) `create_new_religion`'s whole effect sits inside `custom_tooltip = { text = CREATE_NEW_RELIGION_DESC … }`,
  so its tooltip is "Finalize the creation of the new religion." — twice (the button prints its `desc`, then
  the effect's custom tooltip, which is the same key). Hidden behind it: every Devout character is exiled,
  the state religion, ruler and heir convert, the Devout are renamed and their ideologies replaced, 20% of
  the capital and 10% of every other incorporated state convert. (b) Every one of the ~140 select/deselect
  buttons does the same: `desc = X` and `custom_tooltip = { text = X … }`, so each tooltip prints its
  sentence twice. (c) A greyed trait button lists its reasons as raw variables: `var:selected_traits < 3`,
  four `has_variable = custom_religion_ideology_*_selected` lines and five `has_variable = custom_religion_trait_*_selected`
  lines (e.g. `select_trait_traditionalist_loyal`, `:2553-2590`), which render as variable names. (d) The
  four steps (`current_stage` 1-4: three doctrines, three Devout traits, a name, a tradition) are shown only
  by which buttons appear; nothing says "Step 2 of 4: choose three traits (1 chosen)". (e) The reason says
  "This will require significant resources and effort", but the button has no cost (`possible = always`);
  its real costs are the conversions and the exiled Devout leaders. (f) Trait buttons write their modifier
  by hand, `"\n\n #b $state_birth_rate_mult$: #!#g +2.5%#!"` (with a stray leading space), rather than
  rendering it.
- **Proposed:** (a) take the Proclaim effect out of the `custom_tooltip`; keep only the scope-saving
  `if`s hidden (`hidden_effect`), so the engine lists the conversions, the exile, the IG and religion changes.
  (b) drop the `custom_tooltip` wrappers in the select/deselect/back/next buttons (the `desc` already says
  it), or use `hidden_effect`. (c) wrap the trait buttons' `possible` in two custom tooltips:
  "Three traits already chosen" and "Needs a doctrine of the same school ($ideology_…$)" (one key per school).
  (d) a `status_desc` keyed on `current_stage`: `"#bold Step [ROOT.GetCountry.MakeScope.Var('current_stage').GetValue|0] of 4:#! Choose three doctrines (#v [… 'selected_idelogies' …|0]#!/3 chosen)"`
  and its siblings. (e) quick fix below. (f) low priority; if the IG trait has no loc accessor for its
  modifier, at least drop the leading space so the line aligns.
- **Effort:** quick (e) / medium (a-d, script and loc)
- **Confidence:** high (a-c, e), medium (that `desc` + effect custom tooltip print twice is the vanilla
  button tooltip's behaviour as `civil_rights_buttons.txt`'s header documents it)

### JE-3. World War: the number that drives everything is never shown, and greyed buttons print raw script
- **Category:** hidden info / style
- **Where:** `common/journal_entries/world_war_je.txt:43-130` (`status_desc`); `common/scripted_buttons/world_war_buttons.txt`
  (`possible` blocks of `ww_rearm_button`, `ww_appease_button`, `ww_total_war_economy_button`,
  `ww_war_propaganda_button`, `ww_wartime_rationing_button`); loc `je_world_war_status_*`
  (`te_journal_entries_l_english.yml:2581-2589`), `je_world_war_ideology_*` (`:2575-2579`),
  `WW_REARM_POSSIBLE_TT`, `WW_TOTAL_WAR_POSSIBLE_TT`, `WW_PROPAGANDA_POSSIBLE_TT`, `WW_APPEASE_BUTTON_DESC`
  (`te_miscellaneous_l_english.yml:1215-1248`)
- **Now:** (a) the status switches on `ww_ideological_tension` (30 rising, 50 high, 70 crisis) and the
  buttons unlock at 20, 30 and 40, but no text prints the tension; the status lines are flavour ("#Y HIGH
  TENSION:#! The ideological divide deepens. Military buildups accelerate."). (b) `possible` blocks put bare
  `ww_ideological_tension >= 30` and `has_variable = ww_active_phase` in the greyed tooltip, which renders
  the script names (`scripting_best_practices.md`: a bare script-value comparison "explains nothing in a
  tooltip"). Meanwhile the custom tooltips claim conditions they don't wrap: `WW_REARM_POSSIBLE_TT` "Must have
  researched Combined Arms with ideological tensions above 30%" wraps only the tech check, so the tension
  condition appears twice, once raw. `WW_PROPAGANDA_POSSIBLE_TT` writes "Mass Media" by hand. (c) "Our
  Ideology:" colours Communist and Fascist `#R` and Democratic `#G`, a moral palette, not the house rule
  (green good for the player, red bad); a fascist player reads their own ideology in red. (d) button descs
  restate the modifier lines the engine prints beside them ("Increases military effectiveness and prestige
  but raises costs and generates unrest among workers"; "Only available for democratic nations", which the
  greyed reason says too).
- **Proposed:** (a) add a scripted progress bar, `ww_tension_bar` (0-100), set monthly from
  `ww_ideological_tension` like `civil_rights_support_bar`, so the entry shows a bar with the thresholds; or,
  smaller, a second status line `"\n#bold Ideological Tension:#! #v [ROOT.GetCountry.MakeScope.ScriptValue('ww_ideological_tension')|0]%#!"`
  (the JE-status root is `ROOT.GetCountry`, gui guide gotcha #20). (b) move each threshold and variable check
  inside a custom tooltip whose text says exactly that condition: "Ideological tension of #v 30%#! or more
  (now #v X%#!)", "During a world war we are fighting in", and keep the tech line separate
  (`[GetTechnology('mass_media').GetName]`). Model: the power bloc's slot checklist (VAN-13). (c) drop the
  colours from `je_world_war_ideology_*` (quick fix below). (d) cut each desc to its flavour sentence; the
  modifier and IG approval lines already render.
- **Effort:** quick (c, d) / medium (a, b)
- **Confidence:** high (a, c, d), medium-high (b: how the engine prints `has_variable` is from memory, not a screenshot)

### JE-4. Civil Rights: the endings depend on months nobody can see
- **Category:** hidden info
- **Where:** `common/journal_entries/je_civil_rights.txt:91-128` (`status_desc`), `:152-191` (`on_complete`
  dispatch on `cr_*_months`), `:256-320` (the monthly counters); loc `je_civil_rights_status_*`
  (`te_journal_entries_l_english.yml:147-151`), `cr_btn_*_ending_tt` (`te_miscellaneous_l_english.yml:2395-2417`)
- **Now:** each policy button's tooltip states its ending rule well ("a win is The Movement Carries the Day if
  this ran longest of the pro-movement policies, and over 18 months"), but the months each policy has run
  (`cr_grassroots_months` … `cr_segregationist_months`) are shown nowhere, so "ran longest" and "over 18
  months" cannot be checked. The status text is five flavour paragraphs by support tier ("Sit-ins and chapter
  networks are spreading. Sympathetic editorials …"), which the bar already conveys.
- **Proposed:** keep one flavour sentence per tier and add the policy months as a list in the status:
  `"\n#bold Months run:#! Grassroots #v X#! · Federal #v Y#! · Gradualist #v Z#! · Cooptation #v W#! · Crackdown #v V#! · Segregationist #v U#!"`
  (each `[ROOT.GetCountry.MakeScope.Var('cr_grassroots_months').GetValue|0]`; a `$je_civil_rights_months_line$`
  splice in each tier key), plus "#bold Ending if won now:#!" through a small customizable localization that
  mirrors `on_complete`'s dispatch (the `cr_btn_ending_*` keys already exist with hovers). Naming nit: the
  button "Encourage Grassroots Organizing" sets "Grassroots Organizing"; "Federal Civil Rights Protection" is
  "Federal Protection" in the bar's breakdown and "Suspend Federal Protection" to stop; pick one name per
  policy. `test_civil_rights_buttons.py` pins the button tooltip keys and figures, not the status.
- **Effort:** medium (status loc + one custom loc)
- **Confidence:** high

### JE-5. Heir Education: a manual in the description, button text that repeats the engine's lines, one hidden cost
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** over-explaining / spread-out/redundant / hidden info
- **Where:** `common/journal_entries/je_heir_education.txt`; `common/scripted_buttons/heir_education_buttons.txt`;
  loc `je_heir_education_reason` (`te_journal_entries_l_english.yml:397`), `HE_ENABLE_*_DESC` /
  `HE_DISABLE_*_DESC` / `*_EFFECT_TT` (`te_miscellaneous_l_english.yml:424-461`); modifier
  `heir_education_innovation_cost` (`common/static_modifiers/heir_education_modifiers.txt:4`)
- **Now:** (a) the reason is four bold-labelled paragraphs of rules (Trait Focuses / Ideology / Faction /
  Completion). (b) Every enable button's desc ends "The #bold Industrialists#! approve; the #bold Armed
  Forces#! see it as neglecting martial preparation.\n\n#R Costs 100 Authority while active.#!", while its
  effect already prints the IG approval modifiers (`heir_education_admin_ig_reaction`) and the
  `heir_ed_trait_focus_active` modifier (`country_authority_cost_add = 100`): each fact appears twice, once
  hand-typed with hard-coded IG names. (c) The five ideology/faction stop buttons print one sentence twice:
  `HE_DISABLE_CONSERVATIVE_DESC` and `HE_DISABLE_CONSERVATIVE_EFFECT_TT` are both "Dismiss the conservative
  tutors." (same for progressive, radical, moderate, regressive; near-identical for the three skill focuses).
  (d) Each skill advance applies `heir_education_innovation_cost` (−10% weekly innovation for 30 days,
  `heir_ed_gain_admin` etc. in `heir_education_effects.txt:61-74`), which no button mentions.
- **Proposed:** (a) a short bulleted reason (quick fix below). (b) cut each enable desc to its first
  sentence(s), what the focus trains and which traits it can yield, and drop the IG and authority paragraphs;
  list the possible ideologies as a bullet list. (c) make the stop buttons' effect line say what the desc
  doesn't: "Progress made so far is kept." (quick fix below; verified: the stop effects remove only the focus
  variable and the modifier). (d) add to each skill focus's enable effect a visible line naming the
  innovation cost, ideally by rendering the modifier: `custom_tooltip = heir_ed_innovation_cost_tt` with
  `"Each advance: [GetStaticModifier('heir_education_innovation_cost').GetDesc] for 30 days"`.
- **Effort:** quick (a, c) / medium (b, d)
- **Confidence:** high

### JE-6. The four "debate" entries: status lines restate the law, and don't say what is still missing
- **Category:** hidden info / style
- **Where:** `je_digital_rights.txt`, `je_post_scarcity.txt`, `je_mental_health.txt`, `je_human_augmentation.txt`
  (`status_desc` blocks); loc `te_journal_entries_l_english.yml:6-10` (augmentation), `:371-373` (digital
  rights), `:575-576` (mental health), `:655-657` (post-scarcity)
- **Now:** each status is a coloured sentence naming the current law plus a flavour clause ("#G
  Rehabilitation-focused justice is in place,#! but comprehensive mental health infrastructure is still
  needed."). For Mental Health the real remaining requirement, Social Security investment level 4
  (`complete`, `je_mental_health.txt`), is never named in its status. Post-Scarcity's three statuses are a
  path (UBI law → Post-Scarcity Economy tech → Post-Scarcity law) but say "the full transition … remains
  distant" rather than the next step. The augmentation statuses restate each law's description. The
  vanilla goal tooltip does list `complete`'s triggers, so the information is one hover away, but the status
  (the one line shown open) spends its space on restating the law.
- **Proposed:** make each status "Now: <law>. Next: <what completes it>", e.g. Mental Health rehab:
  `"#G Rehabilitation-focused justice is in place.#! Next: raise [concept_institution] $institution_social_security$ to level #v 4#!."`;
  Post-Scarcity early: "Next: enact $law_universal_basic_income$." and ubi: "Next: research
  [GetTechnology('post-scarcity_economy').GetName]." The colour convention also wobbles: digital rights
  colours "minimal privacy" `#Y` and "moderate" `#G` though neither completes the entry.
- **Effort:** quick-medium (loc only, but new splices to check in game)
- **Confidence:** medium

### JE-7. Human Augmentation's reason links the power-bloc concept by mistake
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** style / other
- **Where:** loc `je_human_augmentation_reason` (`te_journal_entries_l_english.yml:404`)
- **Now:** "The divide between enhanced and natural citizens threatens social [concept_power_bloc_cohesion]."
  The concept renders "Cohesion" and its hover explains a power bloc's cohesion, which has nothing to do
  with this entry.
- **Proposed:** plain "social cohesion" (quick fix below).
- **Effort:** quick
- **Confidence:** high

### JE-8. Mental Health's fail condition reads in days, and `_desc` keys shadow `_reason`
- **Category:** other
- **Where:** `common/journal_entries/je_mental_health.txt:84-96` `fail` (`scope:journal_entry.journal_entry_age >= 3650`); every mod JE's
  `je_*_desc` key (e.g. `je_mental_health_crisis_desc`, `te_journal_entries_l_english.yml:573`)
- **Now:** (a) the fail tooltip will print the raw age comparison (3650, days) beside the law check; the rule
  is "a punitive justice law after the entry's tenth year". (b) The mod writes a `je_*_desc` for every entry,
  which vanilla never does (1 of 459 vanilla entries has one), and the panel renders `_reason`
  (`journal_entry.gui:749`, `JournalEntry.GetReason`). Several `_desc` keys say the same as `_reason` in other
  words (`je_mental_health_crisis_desc` / `_reason`, `je_post_scarcity_desc` / `_reason`), and some carry the
  actionable line the reason lacks (`je_human_augmentation_desc`: "Set the legal status of mechanical and
  biotechnological enhancement of the human body.").
- **Proposed:** (a) `custom_tooltip = { text = je_mental_health_fail_tt … }` ("Holding $law_punishment_focused_criminal_justice$
  or $law_penal_labor_camps$ after the entry's tenth year"). (b) check in game where `_desc` renders (if
  anywhere); if nowhere, move each entry's actionable `_desc` line into its `_reason` and stop requiring
  `_desc` in `loc_coverage_audit.py:96-101`.
- **Effort:** medium
- **Confidence:** low-medium (rendering not seen in game)

### JE-9. Tax-code overrides of vanilla entries: three goal lines that can never be met under the rule
- **Category:** other (noise)
- **Where:** `common/journal_entries/te_tax_vanilla_je_overrides.txt:36-55` (and the same block in
  `je_imperialism_of_promise`, `je_portugal_regeneration`)
- **Now:** under the tax code rule the `trigger_if` branch's OR keeps vanilla's three taxation-law lines
  (`has_law_or_variant = law_type:law_per_capita_based_taxation` …) beside the three "counts as" lines, but
  every country's taxation law is then `law_te_tax_code`, so the goal tooltip shows three permanently
  unmet options before the three that matter.
- **Proposed:** drop the three vanilla law lines from the `te_tax_code_full = yes` branch (the `trigger_else`
  keeps them for the rule-off case). `test_tax_code_bypass.py` compares each entry with vanilla only outside
  `complete`, so it should not object; run it.
- **Effort:** quick (script)
- **Confidence:** medium (assumes `te_tax_code_full` implies the code law, as the file header says)

## Applied in this PR

27 loc-only edits from this slice were applied (text rewritten in place, keys unchanged). The pre-edit text is in git history; the finding each serves is named above. Keys:

`HE_DISABLE_ADMIN_FOCUS_EFFECT_TT`, `HE_DISABLE_CONSERVATIVE_EFFECT_TT`, `HE_DISABLE_DIPLO_FOCUS_EFFECT_TT`, `HE_DISABLE_MILITARY_FOCUS_EFFECT_TT`, `HE_DISABLE_MODERATE_EFFECT_TT`, `HE_DISABLE_PROGRESSIVE_EFFECT_TT`, `HE_DISABLE_RADICAL_EFFECT_TT`, `HE_DISABLE_REGRESSIVE_EFFECT_TT`, `TE_CM_HOW_IT_WORKS`, `TE_CM_SECTION_INTRO`, `TE_HOMELAND_REMOVAL_TRACK_ACTIVE`, `TE_HOMELAND_TRACK_ACTIVE`, `TE_STATE_CROWDING_TT`, `TE_STATE_UN_MISSION_TT`, `concept_migration_crowding_desc`, `je_create_new_religion_reason`, `je_heir_education_reason`, `je_human_augmentation_reason`, `je_state_collapse_reason`, `je_world_war_ideology_communist`, `je_world_war_ideology_democratic`, `je_world_war_ideology_fascist`, `te_state_tourism_monuments_tt`, `te_state_tourism_output_applied_tt`, `te_state_tourism_output_tt`, `te_state_tourism_throughput_applied_tt`, `te_state_tourism_throughput_tt`
