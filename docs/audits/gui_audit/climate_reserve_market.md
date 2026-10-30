# Climate, Strategic Reserve and Market panel additions — GUI & localization audit

> Part of the 2026-10-27 GUI and localization audit; the index, the cross-cutting findings and the owner questions are in [`../gui_localization_audit.md`](../gui_localization_audit.md). Line numbers are as of the audit and drift as files change; search by key or type name. "Quick fixes" below means the loc-only edits this PR applied.

Slice: Global Warming (`je_global_warming`, Market panel Climate tab), Strategic Reserve (`je_strategic_reserve`,
Market panel Reserve tab), and the mod's other Market panel additions (Top Trade Partners table and partner
tooltips/charts, the Trade tab's All Goods tariff rows). Read-only audit, 2026-10-27.

## Top priorities

- **Policy tooltips, adopt and repeal (GW-1, GW-2, GW-5; quick).** Strip the "Applies to your own country.
  Available at 0.5 °C…" boilerplate the Adopt hover already ticks, cut Tariffs' paragraph to its figures, and stop
  hand-writing repeal texts: three of the ten are wrong about their own modifier (Green Building Codes "construction
  savings", Public Transit "quality-of-life", Divestment "restoring output") and others leave lines out. Best: "Ends:" + the same
  `GetStaticModifier(...).GetDesc` the adopt shows; Quick fixes carry corrected prose as the fallback.
- **Hidden costs and effects (GW-4, GW-3).** Renewable Investment's 0.5%-of-GDP running cost renders nowhere before
  adopting (the cost apply sits inside the `custom_tooltip`); the radicalism effect of eight policies shows on none of
  their rows — a `script_only` modifier type would make the engine print it.
- **Strategic Reserve rows (SR-1, SR-2, SR-3; medium).** The − / ■ / + controls have no rate beside them; the
  17-line row-wide hover repeats the overview, status icon and expanded figures and pops over the expanded lines; the
  policy icon never says which policy. Make the controls a stepper with the value, give each cell its own short
  hover, and name the policy on the icon.
- **Stale market-era wording (GW-6, GW-7, GW-9; quick).** Another market's Climate tab calls the leader's national
  policies "the market's"; emissions tooltips and the emissions concept still describe market-leader cuts and
  market-only accounting; two concepts omit the 4 °C threshold.
- **Slot lists to datamodels (GW-11, MKT-1; medium).** Top Emitters (5 slots + a five-way ladder) and Top Trade
  Partners (5 × 47-line rows over 15 rank variables) are the pattern the Demographics States table replaced; both
  already have the ordered pass that would fill a list.
- **Trade tab coherence (MKT-2, MKT-3).** Partner charts sum units across goods with no unit shown, the table is
  yearly at base prices, its hover weekly at market prices, and the Exports-by-Value hover prices at base while its
  slice uses market; all the additions' labels are hard-coded English `raw_text` the translation memories can't reach.
- **Presets as tables (SR-4; quick).** The four preset hovers are eight settings written as a sentence; as
  "Label: value" lines in the stepper rows' order they can be read against the settings below them.

## Findings

### Global Warming

### GW-1. Policy tooltips: the "Applies to your own country. Available at 0.5 °C…" boilerplate (and Carbon Removal Support)
- **Status:** done (2026-10-27 wave). The audit's loc fix was the substance; the wave checked every policy description now ends at its modifier and spelled the row "Subsidize Reforestation" to match Carbon Removal's flavor line.
- **Category:** over-explaining / style
- **Where:** loc `GW_CARBON_TAX_DESC` (`te_miscellaneous_l_english.yml:375`), `GW_RENEWABLE_INVESTMENT_DESC` (`:411`),
  `GW_EMISSION_STANDARDS_DESC` (`:379`), `GW_PUBLIC_TRANSIT_DESC` (`:390`), `GW_GREEN_BUILDING_CODES_DESC` (`:388`),
  `GW_FOSSIL_FUEL_DIVESTMENT_DESC` (`:382`), `GW_REFORESTATION_DESC` (`te_concepts_l_english.yml:128`). Rendered twice:
  as the row name's tooltip (`gui/journal_entry_widgets/global_warming_widget.gui:909-1105`, `row_label` tooltip) and,
  through `gw_effect_*`'s `custom_tooltip` (`common/scripted_effects/global_warming_effects.txt:11-163`), as the Adopt
  button's ExecuteTooltip, right under `IsValidTooltip`.
- **Now:** five siblings end "Applies to your own country. Available at 0.5 °C of global warming with
  [technology]."; Reforestation ends "Available to all nations once global warming reaches mild levels." ("mild" is not
  one of the tier names: 0.5 °C is "Moderate"); Divestment "Available to all nations once warming reaches #v 1.0°C#!"
  (no space before °C, unlike the others); Climate Adaptation has no such line. On the Adopt button the line sits
  directly under the ticked/crossed "Global warming has reached 0.5°C" and "[tech] researched" conditions
  (`gw_possible_*`, `common/scripted_triggers/global_warming_triggers.txt:141-400`), so it is said twice in one
  tooltip. "Applies to your own country" restates the "National" subheading the row sits under (`gw_pol_sub_national`).
- **Proposed:** each GW_*_DESC = one flavour line + `[GetStaticModifier('…').GetDesc]`, nothing after it. Nothing is
  lost: the warming gate is said once above the rows while it holds (`gw_pol_waiting`), each condition is ticked on the
  Adopt hover, and How Global Warming Works lists every policy's technology (`gw_how_policies_2`). Exact values in
  Quick fixes. Carbon Removal Support (`GW_CARBON_REMOVAL_DESC`, the owner's example of the problem) was fixed in this PR, in exactly this form (flavour line + modifier, no boilerplate); the siblings now differ from it by
  the boilerplate (and Tariffs by GW-2's paragraph). Its new flavour line spells "Subsidize" where the row beside it reads "Subsidise
  Reforestation" (`GW_REFORESTATION`); low priority.
- **Effort:** quick
- **Confidence:** high

### GW-2. Fossil-Fuel Tariffs' tooltip is a paragraph in front of its own modifier lines
- **Status:** done. The audit's loc fix was the whole finding; checked in the 2026-10-27 wave.
- **Category:** over-explaining / style
- **Where:** loc `GW_FOSSIL_FUEL_TARIFFS_DESC` (`te_miscellaneous_l_english.yml:385`); row at
  `global_warming_widget.gui:902-921`.
- **Now:** five sentences ("Raise coal and oil import and export tariffs in your market: +2.5 percentage points at
  Low, +5 at High and +10 at Maximum. Only the market leader can adopt or repeal this policy. Native tariff levels stay
  as chosen, including under legislated customs; None still collects no tariffs. The surcharge also applies to traded
  synthetic coal and oil. It grants no automatic emissions reduction."), then the modifier list, whose own lines
  ("Maximum Coal Import Tariff Rate +10%", desc "The collected rate scales with the selected tariff level",
  `te_modifiers_l_english.yml:28-29`) already say the scaling. The 2.5/5/10 explanation is also in `gw_how_policies_1`
  and `concept_climate_policy_desc` (three copies).
- **Proposed:** two sentences, keeping the figures a leader plans around; the leader-only rule is the Adopt/Repeal
  condition "We lead our own market" (`gw_cond_leads_market`) and the line `gw_pol_set_by_leader` above the row for a
  member. Exact value in Quick fixes. Keep the 2.5/5/10 figures in this tooltip and in the definition
  (`concept_climate_policy_desc`), and drop them from How (`gw_how_policies_1`, Quick fixes), which then names the
  split and nests the concept.
- **Effort:** quick
- **Confidence:** high

### GW-3. Policies move Environmental Movement radicalism: How now says so, the policy rows still don't
- **Status:** done (2026-10-27 wave). A `script_only` modifier type, `country_environmental_movement_radicalism_add`, sits on each policy's static modifier (−10%, Carbon Removal Support −5%), so every row's modifier list prints it; the movement's radicalism factor reads its sum as one line, "Climate policies in force", in place of eight `has_modifier` branches. The "could adopt but hasn't" +10% lines stay as they were.
- **Category:** hidden info / style
- **Where:** `common/political_movements/new_ideological_movements.txt:~255-345` (`additional_radicalism_factors` of
  `movement_environmental`); loc `gw_how_policies_2` (as changed in this PR), `GW_REMOVE_CARBON_REMOVAL_DESC`
  (`te_miscellaneous_l_english.yml:393`).
- **Now:** Carbon Tax, Renewable Investment, Climate Adaptation, Emission Standards, Reforestation, Public Transit and
  Divestment each take 10 points off the movement's radicalism while in force (`POLICY_ACTIVE_*`) and add 10 while
  adoptable but not adopted (`POLICY_POSSIBLE_*`); Carbon Removal takes 5 off and adds nothing; Green Building Codes and
  Tariffs do neither. How now says (this PR) "Most national policies calm the Environmental Movement while in force and
  stir it while you could adopt them but haven't", without sizes or which ones; no policy's own tooltip shows it.
  `GW_REMOVE_CARBON_REMOVAL_DESC` still ends "removes the Environmental Movement satisfaction bonus" for a line its adopt
  tooltip no longer mentions.
- **Proposed:** the modifier-line route the owner prefers: a `script_only` country type, e.g.
  `country_environmental_movement_radicalism_add` (`common/modifier_type_definitions/global_warming_modifier_types.txt`,
  loc "Environmental Movement Radicalism" in `te_modifiers_l_english.yml`), carried by each policy's static modifier at
  −0.10 (Carbon Removal −0.05) and read by the movement's factor (`owner.modifier:…`) in place of the eight
  `has_modifier` branches. Each policy's existing `[GetStaticModifier(...).GetDesc]` then prints the line by itself,
  and the repeal texts (GW-5) follow. The "+10 while adoptable" half stays script and stays described in How. Until
  then, drop the stale clause from `GW_REMOVE_CARBON_REMOVAL_DESC` (Quick fixes).
- **Effort:** medium (quick for the repeal clause)
- **Confidence:** high (the effect is real and unshown per policy); medium on the movement-scope `modifier:` read

### GW-4. Renewable Investment's money cost is invisible before adopting (hidden info)
- **Status:** done (2026-10-27 wave). `gw_renewable_investment_cost_apply` runs outside the policy's `custom_tooltip`, so the Adopt hover prints the running cost's modifier line (`test_country_climate_policies.py`).
- **Category:** hidden info
- **Where:** `gw_effect_renewable_investment` (`global_warming_effects.txt:25-31`) runs
  `gw_renewable_investment_cost_apply` *inside* the `custom_tooltip`, so the cost modifier
  (`renewable_investment_cost_modifier`, 0.5% of GDP a year, `common/script_values/global_warming_cost_values.txt:21`)
  never renders; loc `GW_RENEWABLE_INVESTMENT_DESC` and `GW_REMOVE_RENEWABLE_INVESTMENT_DESC` don't mention it, nor does
  How (`gw_how_policies_2`: "Most cost [concept_authority]").
- **Now:** a player learns the policy costs half a percent of GDP a year only from the Budget Breakdown after adopting.
- **Proposed:** quick: name the cost in the flavour line (Quick fixes). Better: move
  `gw_renewable_investment_cost_apply = yes` out of the `custom_tooltip` in `gw_effect_renewable_investment`, so the
  engine prints the scaled "Renewable Investment: Running Cost" line (its loc already exists,
  `te_miscellaneous_l_english.yml:5615`); check in game that the `remove_modifier_if_exists_effect` it opens with
  prints nothing for a country that has no copy. `test_country_climate_policies.py:177-179` pins that the apply sits in
  the adopt `custom_tooltip`, so the test changes with it.
- **Effort:** quick (loc) / medium (effect + test)
- **Confidence:** high

### GW-5. Repeal tooltips are prose that has drifted from the modifiers; render the modifier instead
- **Status:** done (2026-10-27 wave). Every repeal text is "Ends:" and the same `[GetStaticModifier('<policy>_modifier').GetDesc]` the adopt shows (the owner accepted that the lines keep their adopt colors); Renewable Investment's also names its running cost.
- **Category:** style / hidden info (wrong info)
- **Where:** loc `GW_REMOVE_*_DESC` (`te_miscellaneous_l_english.yml:392-410`), shown by the Repeal button's
  ExecuteTooltip (`gw_effect_remove_*`, `global_warming_effects.txt:18-163`).
- **Now:** prose summaries, several wrong against `common/static_modifiers/extra_modifiers.txt:1386-1475`:
  - `GW_REMOVE_GREEN_BUILDING_CODES_DESC` "ending the construction savings and electricity benefits": the modifier
    *raises* construction input (+5%), and its biggest line (household emissions −60%) is not mentioned.
  - `GW_REMOVE_PUBLIC_TRANSIT_DESC` "losing the quality-of-life and construction savings": no standard-of-living line
    exists; transportation output, oil input and automobile-infrastructure lines are not mentioned.
  - `GW_REMOVE_FOSSIL_FUEL_DIVESTMENT_DESC` "restoring coal and oil output": the modifier has no output line (it raises
    oil-extraction tax and cuts coal/oil input).
  - `GW_REMOVE_CLIMATE_ADAPTATION_DESC` mentions only the authority, not the mortality and SoL it gives up; "program"
    where `GW_REMOVE_RENEWABLE_INVESTMENT_DESC` says "programme".
  - `GW_REMOVE_CARBON_REMOVAL_DESC` ends on an Environmental Movement "satisfaction bonus" that its adopt tooltip no
    longer mentions since this PR (GW-3).
- **Proposed:** the repeal text as a header plus the same modifier the adopt shows, so it can't drift:
  `GW_REMOVE_CARBON_TAX_DESC:0 "Ends:\n[GetStaticModifier('carbon_tax_modifier').GetDesc]"` (same for the other eight,
  each with its own modifier; Renewable Investment adds "and its running cost of half a percent of GDP a year"). The
  data expression is the adopt key's, rendered in the same `custom_tooltip` context. Caveat for the owner: the lines
  keep the colours of adopting (a −10% coal output reads red although ending it is good), so the header must say
  "Ends" plainly; vanilla has no inverted-colour form. If the owner rejects that, the Quick fixes table corrects the
  wrong prose instead (rows marked GW-5).
- **Effort:** quick
- **Confidence:** high that the prose is wrong; medium that the owner takes the colour trade-off

### GW-6. Stale "market" framing on another market's Climate tab
- **Status:** done. The audit's loc fix was the whole finding; checked in the 2026-10-27 wave.
- **Category:** hidden info (misleading) / style
- **Where:** loc `te_market_gw_foreign_intro` (`te_miscellaneous_l_english.yml:8037`), `te_market_tab_global_warming_tt`
  (`:8046`), `gw_btn_not_ours_tt` (`:4356`); shown by `gui/market_panel.gui:1528-1531`, the tab strip `:184`, and every
  greyed Adopt/Repeal on another market (`global_warming_widget.gui:222,234`).
- **Now:** "Its emissions and policies below are the market's, and only its leader can change them." / "On another
  market, that market's emissions and policies" / "[leader] leads this market and sets these policies". Since policies
  went national (`gw_cond_role_tt_ours`: "Every country controls its own nine national climate policies"), nine of the
  ten rows shown are the leader's own country's policies, not the market's. The tab tooltip also says "the markets
  emitting most", but Top Emitters ranks countries (`gw_how_emissions_1`: "the Top Emitters list ranks countries
  individually").
- **Proposed:** reword all three (Quick fixes); `[Country.GetName]` stays in both keys `test_global_warming_layout.py`
  checks for it (`:991`, `:1007`).
- **Effort:** quick
- **Confidence:** high

### GW-7. Stale market-era wording in emissions tooltips and How
- **Status:** done. The audit's loc fix was the whole finding; checked in the 2026-10-27 wave.
- **Category:** hidden info (misleading)
- **Where:** loc `gw_cond_emis_tt_ours` / `_theirs` (`te_miscellaneous_l_english.yml:4358-4359`),
  `concept_greenhouse_gas_emissions_desc` (`te_concepts_l_english.yml:819`), `gw_how_policies_1` (`:4401`).
- **Now:** `gw_cond_emis_tt_*` lore: "Emissions are a property of a market, not of one member: the figure is stored on
  the market leader and every member reads the same number." Each country now has its own annual and cumulative
  figure (Top Emitters' columns), and the market row is the sum of its members (`gw_how_emissions_1`); "stored on the
  market leader" is implementation. The concept: "reduce industrial emissions before the market leader's policy cut"
  (now each country's own cut) and "Annual net market emissions accumulate globally". `gw_how_policies_1` ends
  "Household policies and carbon removal affect your own country", which reads as if the others did not (all nine
  national ones do).
- **Proposed:** `gw_cond_emis_tt_*` lore → "#lore The sum of its members' own emissions, which Top Emitters lists
  country by country. Updated each January.#!" The concept: "…reduce industrial emissions before the country's own
  policy cut; Direct Air Capture subtracts atmospheric removal afterward. … Each country's annual net emissions
  accumulate globally and determine [concept_temperature_anomaly]." `gw_how_policies_1`: drop its last sentence and the
  tariff mechanics it repeats from `GW_FOSSIL_FUEL_TARIFFS_DESC` (keep "Only Fossil-Fuel Tariffs belongs to the market
  leader"). Values in Quick fixes.
- **Effort:** quick
- **Confidence:** high

### GW-8. The penalty tooltip says the same thing twice, and the overview shows the anomaly twice
- **Status:** done (2026-10-27 wave). The overview's Warming Penalty cell shows the modifier's standard-of-living and mortality lines at today's scale (`gw_disp_penalty_sol`, `gw_disp_penalty_mortality_pct`), its hover the whole modifier, so the anomaly is printed once, on the temperature line.
- **Category:** over-explaining / redundant
- **Where:** loc `gw_cond_penalty_tt` (`te_miscellaneous_l_english.yml:4364`), `gw_ov_penalty_label` (`:4414`); cell at
  `global_warming_widget.gui:559-568`.
- **Now:** "The penalties below are applied to this country every month, with every value multiplied by the current
  temperature anomaly. At the scale shown, multiply each line by that figure." The cell reads "Penalty ×1.61" while the
  row below reads "1.61 → 1.81 °C": `gw_warming_penalty_scale_display` *is* `temperature_anomaly_display`
  (`common/script_values/global_warming_values.txt:158-160`), so the overview prints one number twice.
- **Proposed:** quick: one sentence with the figure (Quick fixes). Larger, optional: give the cell a figure the player
  doesn't already have, e.g. the scaled standard-of-living line ("SoL −1.6") with the full list on hover; that needs a
  display script value (`global_warming`'s `state_standard_of_living_add` × anomaly) and is a GUI change.
- **Effort:** quick / medium
- **Confidence:** high (quick part); medium (figure swap)

### GW-9. The same rules repeated across concept, How, overview and row tooltips
- **Status:** done. The audit fixed the concepts' thresholds and the roster; the 2026-10-27 wave added `concept_emissions_reduction_treaty`, holding the treaty's rules once, and cut the five treaty texts to one line each nesting it.
- **Category:** redundant / over-explaining
- **Where:**
  - The treaty's rules in five places: `gw_pol_treaty` (`te_concepts_l_english.yml:1565`), `gw_ov_treaty_tt_ours` /
    `_theirs` (`te_miscellaneous_l_english.yml:4437-4438`), `gw_te_treaty_tt` (`:4462`), `gw_how_policies_3` (`:4403`),
    plus `gw_te_row_tt`'s lore.
  - The tier ladder in four: `gw_how_warming_2`, `gw_ov_tier_tt`, `je_global_warming_reason_climate`, and the two
    concepts (`concept_temperature_anomaly_desc`, `concept_global_warming_system_desc`), which list thresholds "0.5°C,
    1°C, 2°C and 3°C" where How says "0.5, 1, 2, 3 and 4 °C"; the concepts are the stale ones (a 4 °C event exists).
  - The policy roster in three: `concept_climate_policy_desc` (`te_concepts_l_english.yml:760`), `gw_how_policies_1`,
    `je_global_warming_reason_climate`.
- **Proposed:** a concept for the treaty, `concept_emissions_reduction_treaty` ("Enforce Emissions Reduction"), whose
  `_desc` holds the rules once (what it locks, what stays voluntary, the throughput/Industrialists penalties, the
  authority waiver, the freeze); the five texts become one line each with `[concept_emissions_reduction_treaty]`
  (e.g. `gw_te_treaty_tt`: "[State.GetCountry.GetName] is bound by an [concept_emissions_reduction_treaty]."). Make
  `concept_climate_policy_desc` the policy roster and have `gw_how_policies_1` nest it rather than restate it (Quick
  fixes). Correct the two concepts' threshold lists to include 4 °C (`events/environmentalism_events.txt:1506`, "Event
  22: Four Degrees"; Quick fixes), then nest `concept_temperature_anomaly` where a tooltip needs the ladder.
- **Effort:** medium (new concept + loc)
- **Confidence:** medium-high

### GW-10. The journal entry's reason text is an always-open explanation at the foot of the panel
- **Status:** done. The audit's loc fix was the whole finding; checked in the 2026-10-27 wave.
- **Category:** over-explaining / redundant
- **Where:** loc `je_global_warming_reason_climate` (`te_journal_entries_l_english.yml:378`), rendered by
  `gui/journal_entry.gui:749` below every widget.
- **Now:** three paragraphs: flavour, then the tier ladder and the nine/one policy split (both in How, GW-9), then
  "#lore The climate dashboard above carries the current readings…".
- **Proposed:** keep the first paragraph only (Quick fixes). The progress line `je_global_warming_progress` ("Global
  Temperature: 1.61 °C - Moderate") also repeats the overview inside the panel; it earns its place in the journal list,
  so leave it.
- **Effort:** quick
- **Confidence:** high

### GW-11. Top Emitters is five copy-pasted slots; a datamodel over a list would do it
- **Status:** done (2026-10-27 wave). The monthly refresh builds `gw_te_top` (`ordered_country`, `max = 5`), one `gw_emitter_row` draws per item through a datamodel with `datacontext = "[Scope.GetState]"`, "Our country" is `State.GetCountry.IsLocalPlayer`, and "+N more" lists the next 25. The slot variables are dropped from older saves. `TE_SELF_CHECK gw_top_emitters_list` checks the list once a game (`docs/testing/global-warming-playtest.md`).
- **Category:** list
- **Where:** `global_warming_widget.gui:1471-1525` (five `gw_emitter_row` instances reading
  `Var('gw_emitter_1')`…`Var('gw_emitter_5')`, each with its own `gw_disp_emitters_own_slot = N` test for the "Our
  country" mark); filled by `gw_top_emitters_refresh` / `gw_top_emitter_slot`
  (`global_warming_effects.txt:353-462`, a five-way ladder of `has_variable` checks to count the shown rows).
- **Now:** works, but it is exactly the pattern the owner wants replaced, and the "+N more" hover
  (`gw_top_emitters_sgui`, `global_warming_sguis.txt:522-536`) lists *every* emitter from the top, so it repeats the
  five rows above it and can run to 200 lines.
- **Proposed:** in the same monthly refresh, `clear_variable_list = gw_te_top` then
  `ordered_country = { limit = { gw_is_ranked_emitter = yes } order_by = gw_disp_own_emis max = 5
  check_range_bounds = no  capital ?= { … add_to_variable_list = { name = gw_te_top target = THIS } } }` on the viewer
  (the Demographics States table's shape, `te_dg_states_top`); one `gw_emitter_row` in a
  `datamodel = "[JournalEntry.GetCountry.MakeScope.GetList('gw_te_top')]"` with `datacontext = "[Scope.GetState]"`; the
  "Our country" mark becomes `visible = "[State.GetCountry.IsLocalPlayer]"`, which also retires
  `gw_emitters_own_slot`. The header shows on `Not( IsDataModelEmpty(...) )`. For "+N more", either cap the hover's
  `ordered_country` (e.g. `max = 25`, then "and N more") or start it at position 5. `test_global_warming_layout.py:1125`
  pins the `Var('gw_emitter_1')` datacontext and `test_gw_top_emitters.py` the slot effect; both change.
- **Effort:** medium
- **Confidence:** high

### GW-12. Two pairs of policy rows share an icon
- **Status:** done with placeholder art (2026-10-27 wave). Tariffs and Carbon Removal Support have rows of their own in `global_warming_gui_icons.md` with the proposed subjects; until the art exists they show existing textures that differ from their neighbors (vanilla's maximum-tariffs trade icon, the Carbon Capture and Storage invention icon). Icon batch 7 (2026-10-30, #1249) painted the two `policy_*.dds` files, so no placeholder is left.
- **Category:** style
- **Where:** `global_warming_widget.gui:905` (Fossil-Fuel Tariffs uses `policy_fossil_fuel_divestment.dds`) and `:1038`
  (Carbon Removal Support uses `policy_renewable_investment.dds`); `docs/systems/global_warming_gui_icons.md:56` (and
  Tariffs has no row in that table at all).
- **Now:** the icon is the row's in-force indicator (lit/dimmed); Tariffs and Divestment, and Carbon Removal and
  Renewable Investment, look identical at a glance.
- **Proposed:** two new icon subjects in the icons doc as placeholders (style rule 10), e.g. Tariffs "a customs
  barrier arm lowered across a coal wagon"; Carbon Removal "a grey intake tower drawing a blue CO₂ stream down into the
  ground". `GwIconsTest.test_every_policy_has_its_own_file` (`test_global_warming_layout.py:645-650`) maps the two
  rows to the shared files and its total (`7 + 2 + 1 + 8 + 2`) counts eight policy files; both change.
- **Effort:** medium (art)
- **Confidence:** high

### GW-13. Cooling is printed blue, not green
- **Status:** done. The audit's loc fix was the whole finding; checked in the 2026-10-27 wave.
- **Category:** style (colour convention)
- **Where:** loc `gw_trend_prefix_cooling` (`te_miscellaneous_l_english.yml:4471`, "#B -"), used by `gw_ov_temp_projected`
  and `gw_cond_trend_value` (the headline and "Warming Last Year").
- **Now:** a falling temperature prints in blue; the style guide's convention (rule 5, and the bar right beside it) is
  "Warming is red; cooling is green".
- **Proposed:** "#G -" (Quick fixes).
- **Effort:** quick
- **Confidence:** medium-high (blue may have been a "cold" metaphor; the guide says green)

### GW-14. Live tooltips teach accounting that belongs in How
- **Status:** done (2026-10-27 wave). The synthetic-fuel booking moved to `gw_how_emissions_1`, the capture hovers and the Cumulative heading lost their accounting and save notes, and the row's lore nests the treaty concept; the tests moved with the text.
- **Category:** over-explaining
- **Where:** loc `gw_emis_capture_tt_ours` / `_theirs` (`te_miscellaneous_l_english.yml:4379-4380`), `gw_te_head_cum_tt`
  (`:4449`), `gw_te_row_tt` (`:4461`).
- **Now:** the Carbon Captured row's hover is three paragraphs, the second on how synthetic-fuel credits are booked
  across markets. The Cumulative heading's hover ends "#lore Existing saves start counting at the next January; previous
  market totals cannot be divided retrospectively. Revolutions inherit the country's total.#!" (save-migration notes in
  a player tooltip). The emitter row's lore "Bind this country to reduce its own emissions, whether it leads its market
  or belongs to another country's market." names no treaty.
- **Proposed:** move the synthetic-fuel booking into `gw_how_emissions_1` (append: "Synthetic-fuel credits count in
  the market that makes the fuel and its burning in the market that uses it, so a market exporting synthetic fuel can
  report negative emissions.") and leave the capture hover as "Carbon taken out of the air each year by this market's
  Carbon Conversion Works using Direct Air Capture, already subtracted from our market's figure.\n\n#lore Source
  capture and synthetic-fuel credits count in industrial emissions instead (How Global Warming Works). Updated each
  January.#!". `test_household_emissions.py:240-242` requires both capture keys to contain "Exporting synthetic
  fuels", so the test moves to `gw_how_emissions_1` with the text; not in Quick fixes for that reason. Cut the
  save-migration lore from `gw_te_head_cum_tt` to
  "#lore Updated each January. A revolution's winner keeps the total.#!" — `test_gw_top_emitters.py:103-105` pins the
  phrases "next January" and "Market joins", so that one needs the test changed and is not in Quick fixes. Reword the
  row lore with the treaty concept of GW-9 ("An [concept_emissions_reduction_treaty] can bind it whether or not it
  leads its market.").
- **Effort:** quick (capture) / medium (cumulative, with the test)
- **Confidence:** high

### GW-15. Type sizes predate the 2026-10-17 ladder
- **Status:** done (2026-10-27 wave). `gw_fontsize_row` (17), `gw_fontsize_heading` (20) and `gw_fontsize_overview` (16) set every text, and the width tests read the sizes from the templates.
- **Category:** style
- **Where:** `global_warming_widget.gui`: `gw_value_row` cells `fontsize_medium` (`:183,192`), `gw_note`
  `fontsize_medium` (`:149`), overview cell words `fontsize_small` (`:358`), Top Emitters values `fontsize_medium` and
  headings `fontsize_small` (`:1256,1324,1348`).
- **Now:** the overview's words are 12 and the tables 14 (OpenSans), against rule 3's "rows, values, buttons and notes
  17, subheadings 20, the overview 16; nothing a player reads to decide something is smaller".
- **Proposed:** panel templates as Banking has (`banking_dash_fontsize_row` 17, `_heading` 20, `_overview` 16 with
  `tooltip_font`, `banking_dashboard_widget.gui:50-61`), `gw_fontsize_row` / `_overview`, then re-check the width budget
  (`test_global_warming_layout.py` `UNITS`/`WidthBudget`): the 340/120 value row and the 110-wide overview cells will
  need the guide's elision ladder. Banking and Cultural Hegemony are grandfathered by the guide; this panel is not.
- **Effort:** medium
- **Confidence:** medium (the owner may accept the current sizes until a rework)

### GW-16. Minor
- **Status:** done (2026-10-27 wave): the in-force conditions are `hidden_trigger`s, `gw_cond_role_tt_theirs` names the leader, the degree spacing matches. Adoption Around the World: no change, the owner's 2026-09-29 decision.
- **Category:** style / tidiness
- **Where / Now / Proposed:**
  - Every Adopt and Repeal tooltip opens with a condition that is always ticked, because the control is only drawn in
    that state: "The policy is not already in force" / "The policy is currently in force" (`gw_cond_not_in_force`,
    `gw_cond_in_force`, first clause of every `gw_possible_*`). The AI buttons need the check; the widget could use
    sguis whose `is_valid` drops it (or wrap it in a `hidden_trigger` there). Effort medium, confidence medium.
  - `gw_cond_role_tt_ours` and `gw_cond_role_tt_theirs` are word for word identical (`:4366-4367`); either make
    `_theirs` name the leader ("[Country.GetName] leads this market and sets its fossil-fuel tariffs…") or drop the
    switch (the OUR_KEYS test, `test_global_warming_layout.py:701`, expects the switch to stay).
  - "Adoption Around the World" repeats the ten policy names directly under the ten policy rows
    (`global_warming_widget.gui:1149-1228`). Folding the count into each row's name hover would save ten rows, but
    the table was kept open by the owner (2026-09-29) — reversing that is the owner's call. Low priority.
  - Degree spacing: "#v 0.5°C#!" in `gw_cond_warming_mild` / `_moderate` and `GW_FOSSIL_FUEL_DIVESTMENT_DESC` vs
    "0.5 °C" elsewhere. Spelling: "program" (`GW_REMOVE_CLIMATE_ADAPTATION_DESC`) vs "programme"; Strategic Reserve's
    "grayed" (`je_strategic_reserve_how_presets`, `st_res_policy_panel_preset_header_tt`) vs Global Warming's "greyed".

### Strategic Reserve

### SR-1. A collapsed row has rate buttons but no rate
- **Status:** done (2026-10-27 wave). The rate setting sits between the decrease and increase buttons, then stop.
- **Category:** spread-out / hidden info
- **Where:** `gui/journal_entry_widgets/strategic_reserve_widget.gui:772-965` (the table line: name 170, Stock bar 150,
  status 30, policy 30, decrease / stop / increase 3 × 26; 486 of 496).
- **Now:** the player presses − / ■ / + without seeing the number they change. The rate shows only in the expanded
  figures ("Rate Setting", `st_res_row_<good>_flow`) or in the row-wide hover (SR-2). The buttons' tooltips
  (`st_res_row_decrease_tooltip` etc.) give the step, not the current or resulting rate.
- **Proposed:** make the three controls the Policy Settings' stepper idiom: `[−] +1.2K [+] [■]`, a 48-wide value cell
  between the minus and plus buttons (`[JournalEntry.GetCountry.MakeScope.Var('st_res_<good>_rate').GetValue|+K]`,
  coloured by sign, hover "per week"), paid for by narrowing the Stock bar 150 → 102 (its markers and fill stay
  readable). The value needs a per-good blockoverride (`row_rate_short`), one new loc key per good
  (`st_res_row_<good>_rate_short`), and the add-strategic-reserve-good skill's file list gains it.
  `test_strategic_reserve_layout.py` pins the name cell (150) and the width budget; add the new cell to
  `DYNAMIC_CELLS` with "-10K".
- **Effort:** medium
- **Confidence:** high

### SR-2. The row-wide hover repeats everything, and pops over the expanded figures
- **Status:** done (2026-10-27 wave). The row hover is gone; each cell has its own (stock, status, policy, rate), and the expanded Rate Setting and Decay labels carry the active rate and the decay breakdown.
- **Category:** redundant / over-explaining
- **Where:** `tooltip = "st_res_row_<good>_tooltip"` on each `te_st_res_good_row` instance's *root*
  (`strategic_reserve_widget.gui:1253` and the seven siblings), i.e. over the table line *and* the expanded figures,
  chart and settings; loc `st_res_row_grain_tooltip` (`te_miscellaneous_l_english.yml:6442`) and its seven siblings.
- **Now:** 17 lines: stored, rate setting, active rate, last week, decay rate, weekly decay, the hub's flow cap and
  staffing (both in the overview), status and reason (the status icon's own hover), policy and its reason, price,
  averaged price, ramp, last review price (the expanded figures), then "#italic Click the good's name to expand this
  row…". Hovering an expanded "Stored" or "Decay" line, which has no hover of its own, brings up this whole block
  repeating the line under the cursor.
- **Proposed:** drop the root tooltip. Give the Stock cell its own short hover (stored / capacity, and what the two
  markers mean: today they are explained only in the Stock column heading's hover), keep the status and policy icons'
  hovers (SR-3), and give the expanded "Rate Setting" line the one figure that exists nowhere else, Active
  (`st_res_<good>_actual_rate`, rate plus decay replacement), plus "Decay" its breakdown
  (`GetValueWithBreakdownFor('country_st_res_<good>_decay_add')`, today only in this tooltip). The "Price signal at the
  last review" line goes (it duplicates "averaged" once a week).
- **Effort:** medium (GUI on 8 instances, loc per good)
- **Confidence:** high

### SR-3. The policy icon doesn't say which policy
- **Status:** done (2026-10-27 wave): the per-good hover the proposal names (`st_res_row_<good>_auto_tooltip`). The "better still" icon per policy needs four new textures; left as an art need.
- **Category:** hidden info
- **Where:** `strategic_reserve_widget.gui:914-934`, `tooltip = "st_res_row_auto_tooltip"` (`te_miscellaneous_l_english.yml:6420`).
- **Now:** one generic hover for every good and state: "Lit while an automated policy sets this good's rate each week;
  dimmed while you set it by hand. Click to show or hide this good's policy settings." Whether grain is on Buy When
  Cheap or Stockpile, and whether it is buying or paused, needs the row expanded.
- **Proposed:** a per-good hover reusing the keys the expanded figures already render: a new
  `st_res_row_<good>_auto_tooltip` = "#bold [concept_st_res_policy]:#! $st_res_row_<good>_policy$\n
  $st_res_row_<good>_policy_reason$\n#italic Click to show or hide its settings.#!" via a `row_auto_tooltip`
  blockoverride. Better still (rule 4, icons first): one icon per policy (Buy When Cheap, Release When Expensive,
  Stabilize, Stockpile; dimmed crate for Manual), as the status column already does with four icons on
  `st_res_<good>_disp_policy`'s code.
- **Effort:** medium
- **Confidence:** high

### SR-4. Preset tooltips are tables written as sentences
- **Status:** done. The audit's loc fix was the whole finding; checked in the 2026-10-27 wave.
- **Category:** list / style
- **Where:** loc `st_res_preset_conservative_tooltip`, `_standard_`, `_aggressive_`, `_stockpile_tooltip`
  (`te_miscellaneous_l_english.yml:6369-6376`), `st_res_policy_panel_preset_header_tt` (`:6341`); the preset row at
  `strategic_reserve_widget.gui:550-586`, directly above the eight settings steppers they fill.
- **Now:** "buy below -5%, release above +10%, moving up to N% of capacity a week and spending up to M% of weekly GDP,
  using the whole capacity. Flow and budget keep up with your capacity and GDP until you set them by hand. Acts on a
  2-week price average with a 5-point response ramp." The sentence about flow and budget is repeated in all four.
- **Proposed:** "Label: value" lines in the order and words of the stepper rows below (Buy below, Release above,
  Maximum weekly flow, Weekly purchase budget, Price memory, Response ramp), so a player can read a preset against the
  current settings; the shared facts (protected 0% / target 100% of capacity, flow and budget following capacity and
  GDP) said once in the Presets heading's hover. Exact values in Quick fixes (five rows). Values verified against
  `st_res_apply_preset_*_base` (`common/scripted_effects/st_res_effects.txt:~1100-1130`).
- **Effort:** quick
- **Confidence:** high

### SR-5. One action, two words; one cap, four names
- **Status:** done (2026-10-27 wave): "Releasing" everywhere a player reads the status, and the flow cap's names nest the concept.
- **Category:** style
- **Where:** status word `st_res_mode_withdrawing` "#O Withdrawing#!" (`:6301`), `je_strategic_reserve_how_status`,
  `je_strategic_reserve_inv_col_status_tt`, `st_res_reason_cap_withdraw`, `concept_st_res_rate_setting_desc`
  ("negative values withdraw"), `je_strategic_reserve_desc` — versus "Release When Expensive",
  `st_res_policy_reason_releasing` "#O Releasing#!", `je_strategic_reserve_how_rates` ("a negative one releases").
  The cap: `concept_st_res_flow_cap` "Flow Cap"; "Hub flow cap" (row tooltip); "Hub Flow Cap"
  (`concept_st_res_active_rate_desc`); "the weekly [concept_throughput] cap" (`st_res_rate_adjustment_possible`,
  `:6377`, the condition on every + / − button); "Max rate" (`je_strategic_reserve_desc`).
- **Now:** a good can read "Withdrawing" on its status icon and "Releasing" in its policy line at the same time; the
  rate buttons' condition links to the vanilla Throughput concept instead of the Flow Cap concept the overview uses.
- **Proposed:** "Releasing" everywhere (the status icon file can keep its name); the player guide's status table
  (`docs/player_guide/03-economy.md:607`) changes with it, so not a quick fix. `st_res_rate_adjustment_possible` →
  "Stays within the [concept_st_res_flow_cap] and the stockpile's remaining room" (Quick fixes), and the concept's
  name inside other text as `[concept_st_res_flow_cap]` rather than "Hub flow cap".
- **Effort:** quick (condition) / medium (rename with guide)
- **Confidence:** high

### SR-6. Concept descriptions read like design notes
- **Status:** done. The audit's loc fix was the whole finding; checked in the 2026-10-27 wave.
- **Category:** over-explaining / style
- **Where:** loc `concept_st_res_rate_setting_desc` (`te_concepts_l_english.yml:906`), `concept_st_res_active_rate_desc`
  (`:902`).
- **Now:** "Player-configured signed weekly intake rate … Adjusted via the +/− buttons in steps controlled by the shared
  Adjustment Step (1, 10, 100, 1000, or 10000). The setting is preserved across weekly ticks until … it auto-clamps to
  the remaining amount and then to zero — the hub will not exceed physical capacity." The Active concept carries a
  worked example ("Storing at +1/week with 0.4 weekly decay means…") and names "the Hub Flow Cap" in plain text.
  Both restate `je_strategic_reserve_how_rates` / `_how_decay`.
- **Proposed:** short definitions that nest the neighbouring concepts (`[concept_st_res_adjustment_step]`,
  `[concept_st_res_flow_cap]`), leaving the mechanics to How (Quick fixes).
- **Effort:** quick
- **Confidence:** high

### SR-7. Rate-button hovers: filler, and no before/after
- **Status:** done (2026-10-27 wave). Each rate button's hover opens with the setting before and after the click, through the base effects' `custom_tooltip` and `ExecuteTooltip`.
- **Category:** over-explaining / hidden info
- **Where:** loc `st_res_row_decrease_tooltip`, `st_res_row_increase_tooltip`, `st_res_row_stop_tooltip`
  (`te_miscellaneous_l_english.yml:6422,6443,6471`).
- **Now:** "Lower this good's reserve rate setting by the current adjustment step (100). Negative rates release stock
  from the reserve onto the market. Other goods are not affected." The sign convention is in the Rate Setting concept;
  "Other goods are not affected" restates the row. None of the three says what the rate will be.
- **Proposed:** quick: trim and nest the two concepts (Quick fixes). Medium: append
  `ScriptedGui.ExecuteTooltip(...)`, with a `custom_tooltip` in `st_res_decrease_rate_base` / `_increase_` / `_stop_`
  (`common/scripted_effects/st_res_effects.txt:~880-918`) reading "Rate: +100 → +200 a week" from two small script
  values (the rate, and the rate ∓ the step). Today the bases only `change_variable`, which renders nothing in a
  tooltip; this is the house form of gotcha #16.
- **Effort:** quick / medium
- **Confidence:** high (quick); medium (effect text)

### SR-8. The entry's reason text repeats How at the foot of the panel
- **Status:** done. The audit's loc fix covered the reason text; the 2026-10-27 wave trimmed `je_strategic_reserve_desc` the same way and dropped its live "Max rate" figure, which the overview's Hub cell carries.
- **Category:** over-explaining / redundant
- **Where:** loc `je_strategic_reserve_reason` (`te_journal_entries_l_english.yml:1375`), rendered below every widget
  (`gui/journal_entry.gui:749`); `je_strategic_reserve_desc` (`:1337`) is a second paragraph of the same, with a live
  "Max rate" figure.
- **Now:** "Positive reserve rates make the hub buy… negative rates make it release… Stored goods decay slowly, so a
  large reserve is not free." — How's Rates and Decay, always open.
- **Proposed:** one line of flavour (Quick fixes). If `_desc` is shown anywhere a player reads (the journal list's
  hover), trim it the same way and drop the live figure, which the overview's Flow Cap cell already carries (low
  confidence on where `_desc` renders).
- **Effort:** quick
- **Confidence:** high (reason), low (desc)

### SR-9. The overview has no "what needs attention" and only half the money
- **Status:** done (2026-10-27 wave). Four of Banking's cells: Hub (with the flow cap), Blocked (goods full or empty with a release set, listed on hover), Purchases (an estimate at today's prices), Sales Income.
- **Category:** spread-out
- **Where:** `te_st_res_overview_panel` (`strategic_reserve_widget.gui:306-378`): Hub, Flow Cap, Sales Income.
- **Now:** a returning player can't tell from the top whether any good is Blocked or full, or what the reserve is
  spending: Sales Income is gross, and its own hover and How say purchases are elsewhere (the Budget panel's Goods
  for Government Buildings).
- **Proposed:** a second row of two-up cells in Banking's shape (`te_banking_ov_cell`): "Blocked: 2 goods" (icon:
  the blocked crate; hover lists them — a count `st_res_disp_blocked_count` summing `st_res_<good>_disp_status = 3`, and
  a `custom_tooltip` list from a read-only sgui), and "Purchases: £1.2K/wk" beside Sales Income, from a new
  `st_res_total_purchase_cost` (sum over goods of `max(actual_rate, 0) × st_res_<good>_unit_price`), so the two money
  figures sit together (rule 5, "related figures sit together").
- **Effort:** large (new values, cells, sgui)
- **Confidence:** medium

### SR-10. Policy Settings are set in the smallest type, and the selected policy looks unavailable
- **Status:** done (2026-10-27 wave). `st_res_fontsize_row` (17) and `st_res_fontsize_heading` (20), with width tests; the policy and preset in force are drawn in vanilla's selected-tab look (`is_shown` false for the op in force, fail-open when `scope:op` is absent; a play-test item).
- **Category:** style
- **Where:** `widget_je_st_res_policy_panel` / `widget_je_st_res_policy_stepper` / `widget_je_st_res_policy_choice`
  (`strategic_reserve_widget.gui:387-733`): every label, value and button `fontsize_small` (12); rows
  `fontsize_medium` (14).
- **Now:** the eight settings a player decides with are the panel's smallest text (rule 3: rows, values, buttons 17;
  "nothing a player reads to decide something is smaller"). The policy and preset in force are shown by greying their
  own button (`is_valid` "This is not already the active policy"), which reads as "unavailable", and nothing else in
  the panel names the policy in force.
- **Proposed:** panel font templates as in GW-15, sized from the longest label (the width budget test,
  `test_strategic_reserve_layout.py:470-556`, follows the template). Head the selector "Policy: Stabilize Prices"
  (`st_res_policy_panel_policy_header` with the good's `policy_text`), and mark the selected button with vanilla's
  selected-tab look rather than the disabled one.
- **Effort:** medium
- **Confidence:** medium

### SR-11. Minor
- **Status:** done (2026-10-27 wave): the no-hub status line keeps only the action, the Status heading's hover is cut to what the column shows (How keeps the explanation, not the reverse as proposed, since explanations belong in How), and "lane" is gone from the panel's text.
- The no-hub status line (`je_strategic_reserve_status_no_hub`) and the overview's No Hub cell hover
  (`je_strategic_reserve_ov_hub_none_tt`) say the same thing while the active entry waits for a new hub (play-test rule:
  status text must not repeat the overview). Keeping the visible line is defensible (it is the one action); low.
- The Status column heading's hover (`je_strategic_reserve_inv_col_status_tt`) and How's Status note
  (`je_strategic_reserve_how_status`) are near-copies; How could say "Each icon's hover gives its reason" and stop.
- "Lane" (`st_res_reason_idle`, `je_strategic_reserve_desc`, `st_res_row_stop_tooltip`) is a term the panel never
  defines; "good" reads the same.

### Market panel: Trade tab additions

### MKT-1. Top Trade Partners is five copy-pasted rows over fifteen rank variables
- **Status:** done (2026-10-27 wave). `update_market_trade_partners` builds `te_tp_top_markets` (five, largest first), the table is one datamodel row reading each partner's figures live, and the fifteen rank variables and `tp_count` are dropped from older saves. A play-test item (`docs/testing/market-trade-partners-playtest.md`).
- **Category:** list
- **Where:** `gui/market_panel.gui:598-892` (Row 1 … Row 5, each reading `Var('tp_N_tc')`, `tp_N_total`,
  `tp_N_gdp_pct`); `common/scripted_effects/trade_partner_effects.txt:31-136` (`store_trade_partner_data`, a five-way
  `var:tp_idx` ladder and 25 `remove_variable` lines).
- **Now:** fixed five; adding a sixth or a "show more" means another 47-line copy.
- **Proposed:** in the same `ordered_market` pass, `add_to_variable_list = { name = te_tp_top_markets target = THIS }`
  on the owner (the partner charts' lists, `te_tp_import_markets` / `te_tp_export_markets`, are built the same way 30
  lines below), and one row in a `datamodel = "[MarketPanel.GetMarket.GetOwner.MakeScope.GetList('te_tp_top_markets')]"`.
  The row reads `Scope.GetMarket.GetOwner` as the charts do, and its two figures through
  `GuiScope.SetRoot( MarketPanel.GetMarket.GetOwner.MakeScope ).AddScope( 'tp_partner_country',
  Scope.GetMarket.GetOwner.MakeScope ).ScriptValue('gui_tp_annual_trade')` (and `gui_tp_trade_pct_gdp`), which already
  take `scope:tp_partner_country`. The rank variables and their clean-up go.
- **Effort:** medium
- **Confidence:** medium-high (the GuiScope pattern is the charts'; the two values need a test in game)

### MKT-2. Three measures of trade on one tab, two of them unlabelled
- **Status:** done. The audit fixed the price; the 2026-10-27 wave labelled the partner charts "units/wk" and opens the partner hover with the table's yearly figure. The play-test of 2026-10-28 found "units/wk" running past vanilla's `compact_chart` legend slot, so the unit moved to the headings' hovers ("The figure beside each flag is units a week").
- **Category:** style / hidden info
- **Where:** `market_panel.gui:476-596` (Export / Import Partners charts), `:598-892` (table), `:375-466` (Exports /
  Imports by Value), `gui/te_trade_partner_tooltips.gui:38-45`.
- **Now:**
  - The partner charts size each slice by `market_exports(target)` / `market_imports`, which the engine documents as
    "total units" (`docs/engine/triggers_parsed.txt:9125`): tonnes of grain and engines added together, printed with no
    unit ("[flag] 12,345"). The charts above and the table below are money.
  - The table's Trade / yr is yearly at base prices; the hover on it is weekly at market prices (it says so, "Per
    week, at current market prices", but the two never reconcile and the hover has no total line).
  - "Exports by Value" sizes slices at market price but its hover values them at base price
    (`Goods.GetBasePrice`, `:397`); "Imports by Value"'s hover uses market price (`:439`).
- **Proposed:** label the partner charts' figure ("[flag] 12,345 units/wk", and a heading hover: "Partners ranked by
  the units of all goods traded each week; see Top Trade Partners for value"). A weekly market-price total per pair
  can't be summed in the GUI, so let the partner hover open with the table's own figure instead ("£1.2M a year at base
  prices; per good below, per week at market prices"), which ties the two together. Make the Exports by Value hover
  use `Goods.GetMarketPrice`, as its slice and the Imports chart do.
- **Effort:** quick (the price bug, a GUI one-token edit) / medium (labels, new loc)
- **Confidence:** high (the inconsistency); medium (best wording)

### MKT-3. The additions' text is hard-coded English
- **Status:** done (2026-10-27 wave). The additions' English is in loc keys (`te_market_*`, `te_market_tp_tt_*`), `test_market_trade_partners.py` keeps it there.
- **Category:** style / other (localization)
- **Where:** `raw_text` in `market_panel.gui:393,435,505,556,613,627,635,644` ("Exports by Value", "Imports by Value",
  "Export Partners", "Import Partners", "Top Trade Partners", "Market", "Trade / yr", "% of GDP"), the "units" in
  `:397,439`, and `te_trade_partner_tooltips.gui:44,52,82` ("Per week, at current market prices", "Imported from
  them:", "Exported to them:").
- **Now:** these never pass through loc: the German and Spanish translation memories (`i18n/`) can't reach them, and
  `organize_loc` / the loc audits can't see them. Vanilla's neighbouring charts use keys (`IMPORTS`).
- **Proposed:** move each to a key in `te_miscellaneous_l_english.yml` (`te_market_tp_title`, `te_market_tp_col_market`,
  … `te_tp_tt_per_week`) and use `text =` with `tooltip`s unchanged; the column headings can then carry concepts
  (`[concept_gdp]` in "% of GDP").
- **Effort:** medium (GUI + about 12 keys)
- **Confidence:** high

### MKT-4. The table hides its best hover and uses an off-ladder size
- **Status:** done (2026-10-27 wave). The trade figure carries the goods breakdown hover and is underlined; the table's text is `te_tp_fontsize_row` (17) with a width test.
- **Category:** hidden info / style
- **Where:** `market_panel.gui:681-692` (the Trade / yr cell carries the per-good breakdown,
  `RegularTooltip_TE_TradePartnerGoods`, with no underline); `:694-702` (every "% of GDP" cell repeats the column
  heading's `TP_GDP_TOOLTIP`); `fontsize = 13` on every cell (`:631-703`).
- **Now:** the only way to learn the figure is hoverable is the column heading's hover ("Hover a figure for the goods
  behind it", `TP_TRADE_TOOLTIP`). Fontsize 13 sits between vanilla's 12 and 14 and below the panel's goods rows.
- **Proposed:** `default_format = "#tooltippable"` on the Trade / yr value (then drop "Hover a figure…" from
  `TP_TRADE_TOOLTIP`); give the % of GDP cell a per-row hover ("£X a year, Y% of [owner]'s GDP") or none; use a named
  font (`fontsize_medium`, or vanilla's row default) instead of 13.
- **Effort:** quick-medium
- **Confidence:** medium-high

### MKT-5. All Goods tariffs: the cooldown has no end date, and the label's hover is unmarked
- **Status:** done (2026-10-27 wave). While a row waits, its hover says about how many days are left (`te_bulk_tariff_cd_days_left_<dir>`), and the label is `#tooltippable`.
- **Category:** hidden info
- **Where:** `gui/te_bulk_tariff_widgets.gui:56-80` (label textbox has a tooltip but no `#tooltippable`);
  `common/scripted_triggers/te_bulk_tariff_triggers.txt:22-38`; loc `te_bulk_tariff_req_ready_import` / `_export`
  (`te_miscellaneous_l_english.yml:6636-6637`).
- **Now:** after a change the whole row greys for three months and the failing condition reads "Imports were not set
  for all Goods in the last 3 months, or were set this week" with no date; the "All Goods" label's explanation is only
  found by chance.
- **Proposed:** store the date the cooldown ends (a `te_bulk_tariff_cd_<dir>_until` variable set beside the timed one,
  or a months-left value) and say it in the condition ("Can be set again from 3 March 1902"); underline the label
  (`default_format = "#tooltippable"`).
- **Effort:** medium (script) / quick (underline, GUI)
- **Confidence:** medium (whether a date can be stored and printed is to check; a weeks-left counter on the monthly
  pulse is the fallback)

## Applied in this PR

40 loc-only edits from this slice were applied (text rewritten in place, keys unchanged). The pre-edit text is in git history; the finding each serves is named above. Keys:

`GW_CARBON_TAX_DESC`, `GW_CLIMATE_ADAPTATION_DESC`, `GW_EMISSION_STANDARDS_DESC`, `GW_FOSSIL_FUEL_DIVESTMENT_DESC`, `GW_FOSSIL_FUEL_TARIFFS_DESC`, `GW_GREEN_BUILDING_CODES_DESC`, `GW_PUBLIC_TRANSIT_DESC`, `GW_REFORESTATION_DESC`, `GW_REMOVE_CARBON_REMOVAL_DESC`, `GW_REMOVE_CLIMATE_ADAPTATION_DESC`, `GW_REMOVE_FOSSIL_FUEL_DIVESTMENT_DESC`, `GW_REMOVE_GREEN_BUILDING_CODES_DESC`, `GW_REMOVE_PUBLIC_TRANSIT_DESC`, `GW_REMOVE_RENEWABLE_INVESTMENT_DESC`, `GW_RENEWABLE_INVESTMENT_DESC`, `concept_global_warming_system_desc`, `concept_greenhouse_gas_emissions_desc`, `concept_st_res_active_rate_desc`, `concept_st_res_rate_setting_desc`, `concept_temperature_anomaly_desc`, `gw_btn_not_ours_tt`, `gw_cond_emis_tt_ours`, `gw_cond_emis_tt_theirs`, `gw_cond_penalty_tt`, `gw_how_policies_1`, `gw_how_policies_2`, `gw_trend_prefix_cooling`, `je_global_warming_reason_climate`, `je_strategic_reserve_reason`, `st_res_policy_panel_preset_header_tt`, `st_res_preset_aggressive_tooltip`, `st_res_preset_conservative_tooltip`, `st_res_preset_standard_tooltip`, `st_res_preset_stockpile_tooltip`, `st_res_rate_adjustment_possible`, `st_res_row_decrease_tooltip`, `st_res_row_increase_tooltip`, `st_res_row_stop_tooltip`, `te_market_gw_foreign_intro`, `te_market_tab_global_warming_tt`
