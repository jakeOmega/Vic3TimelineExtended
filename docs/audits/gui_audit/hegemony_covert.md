# Cultural Hegemony and Covert Warfare — GUI & localization audit

> Part of the 2026-10-27 GUI and localization audit; the index, the cross-cutting findings and the owner questions are in [`../gui_localization_audit.md`](../gui_localization_audit.md). Line numbers are as of the audit and drift as files change; search by key or type name. "Quick fixes" below means the loc-only edits this PR applied.

Scope: `gui/journal_entry_widgets/cultural_hegemony_widget.gui` (both hosts: `je_cultural_hegemony` and the Society
panel's Hegemony tab, `gui/culture_panel.gui:914-964`, which composes the same three types), `cultural_hegemony_sguis.txt`,
the CH triggers/effects/script values its tooltips call; `gui/journal_entry_widgets/covert_operations_widget.gui`,
the Military panel's Covert tab (`gui/panel_military.gui`), `covert_warfare_sguis.txt`, `je_covert_warfare.txt` and
the covert scripted effects/values; and every loc key they render.

Note on Cultural Hegemony: the style guide says it got its tab before the rules were written and the owner was happy
with it, so it "only needs bringing in line when reworked for other reasons". Each CH finding says whether the change
would **bring it in line** with a written rule or merely **differ** from today's accepted layout. Several are plain
bugs or stale text (CH-1, CH-3, CH-6, CH-7, the stale half of CH-5) and are worth doing regardless.

## Top priorities

- **Bugs a player hits today:** a negative Standard of Living pull is hidden from the breakdown and would print green, and the rank factor on that component is said nowhere (CH-1); the Pull Multiplier sits under the Raw Score it is already in (CH-3); the covert row buttons' tooltips root on `JournalEntry` inside a datamodel row, where the mod's own notes say it doesn't exist, so a greyed Stand down or priority button may not say why (COV-9a, quick fix).
- **Covert: show what a running operation does, as modifier lines** (COV-1): the row title has no tooltip at all, and the defender's hovers are prose; `GetStaticModifier('covert_<type>').GetDesc` plus the existing `_extra_tt` lines.
- **Covert: one launch decision, one place** (COV-2, COV-12): put our network/head start and the added upkeep into the diplomatic action's tooltip, cut its 100-word phase paragraph to one line plus a concept, and give operation rows the target's flag so the tab leads to the country.
- **Cultural Hegemony: the Top Cultural Powers board as a one-line table** (CH-2): flag · name · share · signed change · model swatch, halving the section that stands between the overview and the programmes (the panel's only actions), without reversing the owner's board-first order. Add a programmes cell to the overview (CH-9).
- **Hidden thresholds and sources:** the influence-tier thresholds (CH-5), the funding cap's sources (CH-4) and the next intelligence standing (COV-8) appear nowhere a player looks; COV-6 replaces the Tradecraft bar's retired eye marker with threshold lines.
- **Names:** one name per thing: tiers (CH-5), operations (COV-3, up to three names each), model short/full names (CH-12); plus the stale or contradictory text in Quick fixes (CH-6, CH-7, COV-10).


## Findings — Cultural Hegemony

### CH-1. A negative Standard of Living contribution is hidden from "Where Our Pull Comes From"
- **Status:** fixed in this PR (op 3 shows the row for either sign; the value is signed and sign-coloured). The rank-factor line in the row hover (medium) remains.
- **Category:** hidden info (bug)
- **Where:** `common/scripted_guis/cultural_hegemony_sguis.txt` `ch_show_sgui` op 3 (`has_variable = ch_sol` / `var:ch_sol > 0`); `gui/journal_entry_widgets/cultural_hegemony_widget.gui:1414-1432` (SoL `ch_bar_row`); loc `je_ch_widget_bd_sol_value` (`te_journal_entries_l_english.yml:103`)
- **Now:** `var:ch_sol` is `cultural_pull_from_sol` (`cultural_hegemony_effects.txt:22`), which is clamped to `cultural_pull_sol_min` (−5) .. +20 and so goes negative for any country below the world-average SoL. The row is shown only when it is **> 0**, so a country that is *losing* pull to a low standard of living sees no line at all, while the Raw Score below still includes the loss: the visible lines then don't add up to the total. The row was built for negatives (the bar's comment "the one component that can be either sign", `ch_disp_bar_sol_neg`, and `test_cultural_hegemony_layout.py` budgets a "-5.0" value), and the value key is hard-coded green: `"#G [...cultural_pull_from_sol_display|1]#!"`, so a negative figure would also read green.
- **Also hidden:** `cultural_pull_from_sol` is the only component scaled by country rank (`cultural_hegemony_script_values.txt:346-360`: great power ×1, major ×0.5, minor ×0.25, any other rank ×0). Neither the row's hover (`je_ch_widget_bd_sol_tt`: "Our standard of living: X against a world average of Y") nor `concept_ch_sol_desc` says so, so a minor power 12 points above the average sees "3.0" and an unrecognised one sees no row at all.
- **Proposed:** op 3 → `NOT = { var:ch_sol = 0 }` (keep `has_variable`). Value colour by sign: either the signed, sign-coloured format the art-multiplier row already uses (`|+=1`, as in `je_ch_widget_bd_art_mult_value`), or a `SelectLocalization( GreaterThanOrEqualTo_CFixedPoint( …ScriptValue('cultural_pull_from_sol_display'), '(CFixedPoint)0' ), '…_pos', '…_neg' )` pair with `#G`/`#R`. The How text "Lines that add nothing are left out" then stays true.
- The rank factor goes into `concept_ch_sol_desc` (quick fix below) and, as a line "Counted at ×0.5 for a major power" from a new `ch_sol_rank_factor` script value, into `je_ch_widget_bd_sol_tt`.
- **Effort:** quick (one trigger line + loc); the hover line is medium
- **Confidence:** high

### CH-2. The Top Cultural Powers board is ten copy-pasted two-line prose rows; make it a one-line table
- **Category:** list (+ spread-out: it pushes the programmes, the only actions, far down)
- **Where:** `cultural_hegemony_widget.gui:1557-1746` (`te_ch_sec_board`, ten `ch_board_row` instances, ops 1-10); `ch_board_row_sgui` / `ch_board_detail_sgui` / `ch_board_is_us_sgui`; loc `ch_board_row_1..10` (`te_miscellaneous_l_english.yml:1952-1961`), `je_ch_board_row_hint_tt` (`te_journal_entries_l_english.yml:20`)
- **Now:** each row is an `ExecuteTooltip` string: `#v 1.#! France — #v 23.4%#! (+1.2)\nModel: #v Liberal / Progressive Democratic#!`. Ten countries take twenty lines. What the bracketed figure is gets explained in every row's hover (`je_ch_board_row_hint_tt`, appended ten times) and in How (`je_ch_how_board`), but nowhere on screen: there is no column head. The board is the first live section (owner, 2026-09-29), so the Cultural Programmes section — the panel's only actions — starts ~25 lines below the overview.
- **Proposed:** one row per country in fixed columns, with column heads that carry their own hover (Demographics' `te_demog_state_head` pattern): `▶ | # | flag | Country | Share | Change | Model`. Change is signed (`|+1`, as now) with a trend arrow, and the head's hover "since the last recount" replacing the ten appended hints; Model is the model's pie swatch (the overview's `ch_pie_<model>.dds` frame 2, 14 px) with the short name (`je_ch_ov_model_<m>`) and `ch_model_<m>_tt` on hover — the same pairing the models legend already uses. Two routes:
  1. *Keep ten fixed rows (smaller change).* `ch_leaders_display_write` already stores the top three as capitals (`ch_leader_seat_1..3`) and the overview reads them through the proven `Var('ch_leader_seat_N').GetState.GetCountry` chain (gotcha #11(a)). Extend it to ten seats; each row's flag is the vanilla `flag` widget (name on hover, click opens the country, for free), the name `…GetState.GetCountry.GetName`, and the share/change/model columns `ch_disp_rank_<N>_score` / `_delta` / model code script values. Drops the per-row `ExecuteTooltip` string and its two-line layout.
  2. *Datamodel (the Demographics shape).* At the recount (`ch_yearly_global_update`, which already orders the ranks), build a global list of the top ten capitals on a store container, with score/delta/model code set as variables on each capital state; `datamodel = "[GetGlobalVariable('ch_board_store').GetList('ch_board')]"` (proven as a datamodel, gotcha #37), row `datacontext = "[Scope.GetState]"`, flag from `State.GetCountry`. The State→Country step inside a datamodel row is unverified (gotcha #15): ship it with a `TE_SELF_CHECK` line or fall back to route 1.
  Either way the board halves in height, which brings the programmes up without reversing the owner's board-first order. Keep "Our Rank: N of M" under the table when outside the top ten.
- **Effort:** large (script list/seat writes + section rewrite). `test_cultural_hegemony_layout.py` `test_the_boards_bracket_is_one_hover_away` pins ten `je_ch_board_row_hint_tt` and needs rewriting with it.
- **Confidence:** medium (route 1 high; route 2 rests on an unverified accessor)
- **In line or differ:** brings it in line with rule 5 ("several related figures form a table") and rule 3 (Label/hover); the board-first order is kept.

### CH-3. The Pull Multiplier row sits *below* the Raw Score it is already part of
- **Category:** style / confusing structure
- **Where:** `cultural_hegemony_widget.gui:1530-1550` (divider, Raw Score row, then Pull Multiplier row); loc `je_ch_widget_bd_mult_tt` (`te_journal_entries_l_english.yml:93`), `je_ch_widget_bd_mult_value` (:94)
- **Now:** `cultural_pull_raw` (`cultural_hegemony_script_values.txt:511-528`) is the sum of the components **× (1 + multiplier)**, and How says so ("Their sum, raised by the Pull Multiplier, is our Raw Score"). The panel prints Raw Score first and the multiplier after it, whose tooltip says "Raises the sum of the lines above by this much" — the lines above now include the Raw Score itself. The value reads `#G 25%` with no sign, while the art-multiplier subrow beside it reads `+25%` (`|+=0`).
- **Proposed:** put the Pull Multiplier row after the last component and before the divider, then Raw Score alone under the rule as the total. Value `[…ch_pull_mult_pct_display|+=0]%` (as `je_ch_widget_bd_art_mult_value`). Tooltip: `"#title [Concept('concept_ch_modifier_bonus','Pull Multiplier')]#!\nRaises the sum of the components above by this much; the result is our [concept_cultural_pull_raw_score]."`
- **Effort:** medium (GUI reorder of two rows + loc)
- **Confidence:** high
- **In line or differ:** in line (rule 5, parts of a total, then the total).

### CH-4. Where the funding cap comes from is shown nowhere
- **Category:** hidden info
- **Where:** `cultural_hegemony_widget.gui:1184-1195` (the "3 / 5" value cell, no tooltip); loc `je_ch_widget_funding_value`, `CH_PROGRAM_FUNDING_NOT_MAX` (`te_miscellaneous_l_english.yml:237`), `je_ch_how_programmes` (`te_journal_entries_l_english.yml:25`)
- **Now:** the cap is `modifier:country_cultural_program_max_funding_add`: +1 per investment level of the Ministry of Culture institution (`common/institutions/extra_institutions.txt:71`) and +1 from each of two era-6 technologies (`era_6.txt:345`, `:459`). A new Ministry shows "Programme Funding 0 / 0", the + greys with "Funding is not already at maximum (0).", and neither the row, the How text nor any concept says how to raise it. The modifier's own desc ("Increases the maximum funding level available for state-backed cultural programs in the Cultural Hegemony journal entry") is only seen on the institution.
- **Proposed:** a tooltip on the value cell, new key `je_ch_widget_funding_value_tt`: `"#title Funding Level#!\nMaximum: #v [JournalEntry.GetCountry.MakeScope.ScriptValue('ch_program_funding_cap_display')|0]#!\nEach level of investment in the [GetInstitutionType('institution_ministry_of_culture').GetName] raises it by one, as do two late technologies."` (or name the techs). Add the same clause to `je_ch_how_programmes`. (`CH_PROGRAM_FUNDING_NOT_MAX` matches Covert's `iw_funding_not_max_tt` word for word, so leave it.)
- **Effort:** medium (new key + one `tooltip =` line)
- **Confidence:** high
- **In line or differ:** in line (rule 3, the reason behind a value goes in its tooltip; rule 6).

### CH-5. Influence tier: three names per tier, a clash with vanilla's "Major Power", no thresholds anywhere
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** style + hidden info
- **Where:** overview cell `cultural_hegemony_widget.gui:626-684`; loc `je_ch_ov_tier_0..5` (`te_journal_entries_l_english.yml:58-63`), `je_ch_ov_tier_tt` (:64), `ch_tier_*` (`te_concepts_l_english.yml:571-576`), `concept_ch_influence_tier_desc` (`te_concepts_l_english.yml:743`)
- **Now:** the same tier is "Major Power" (overview word), "#G Major Cultural Power#!" (tooltip line from `ch_tier_text`) and "Major" (concept's ladder); top tier "Hegemon" / "#G CULTURAL HEGEMON#!" (all caps) / "Cultural Hegemon". "Major Power" is also vanilla's name for a country rank, which the CH system itself reads (`cultural_pull_from_sol` scales by `rank_value:major_power`). The thresholds (2 / 5 / 10 / 15 / 25 % share, `ch_set_display_state`, `cultural_hegemony_effects.txt:112-139`) appear in no tooltip, concept or How text, so "how far to the next tier" — the one actionable question about a tier — has no answer. The concept also says the tier "sets the wording of the … journal entry", which is stale (the entry has no status text while active).
- **Proposed:** quick fixes below: `je_ch_ov_tier_4` → "Major"; `ch_tier_hegemon` → "#G Cultural Hegemon#!"; concept desc with the ladder and thresholds. Optionally (medium) a last line in `je_ch_ov_tier_tt`, "Next: #v Significant#! at #v 10%#!", from a new `ch_disp_next_tier_threshold` script value and a `GetCustom` name.
- **Effort:** quick (loc) / medium (next-tier line)
- **Confidence:** high
- **In line or differ:** in line (rule 3: one name per term; nothing a returning player needs is hidden).

### CH-6. Three concept descriptions still describe a "parenthetical" the panel no longer has
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** over-explaining (stale)
- **Where:** `concept_ch_art_production_desc`, `concept_ch_prestige_desc`, `concept_ch_sol_desc` (`te_concepts_l_english.yml:739`, `:754`, `:756`)
- **Now:** "The parenthetical shows (your production / world production)." etc. The old status text printed "(x / y)"; the breakdown now draws a bar and a value, and each row's hover prints "Our share …: X of Y" / "Our prestige: X of Y worldwide" / "Our standard of living: X against a world average of Y". The concepts also switch to "you/your" while every panel line says "we/our" (e.g. "early on you're limited by volume").
- **Proposed:** delete the "The parenthetical shows …" sentence from each (quick fixes below). The second-person voice is mod-wide in older concepts; mention only.
- **Effort:** quick
- **Confidence:** high

### CH-7. The board's hover says "yearly recount"; everything else says about twice a year
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** style (contradiction)
- **Where:** `ch_board_detail_1..10` (`te_miscellaneous_l_english.yml:1942-1951`), last line `#lore As of the last yearly recount.#!`
- **Now:** the recount runs at the yearly pulse **and** whenever the 180-day lock (`ch_ldr_lock`, `cultural_hegemony_effects.txt:720`) has lapsed, and after every war (`ch_war_end_recalc_on_action`); How, the share tooltip and `concept_cultural_pull_share_desc` all say "about twice a year and after every war". The hover also lists only four of the nine components (art, prestige, SoL, tech) above the Raw Score, so the lines never add up to it.
- **Proposed:** "#lore As of the last recount.#!" (quick fixes, ten keys). For the sum, either add the remaining non-zero snapshots or title the block "Largest Components" (needs the snapshot writes in `ch_yearly_global_update`; medium).
- **Effort:** quick (wording) / medium (complete breakdown)
- **Confidence:** high

### CH-8. Live overview tooltips re-teach what the concept and How already say
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** over-explaining
- **Where:** `je_ch_ov_share_tt` (`te_journal_entries_l_english.yml:57`), `je_ch_ov_leaders_tt` (:37), `je_ch_widget_models_pie_tt` (:117)
- **Now:** the share tooltip's title is `[concept_cultural_pull_share]`, then the next line restates that concept's definition ("Our raw Cultural Pull as a percentage of every country's raw pull added together"), and the closing `#lore` paragraph restates `je_ch_how_share` ("Other countries' pull is recounted about twice a year…, so the share can step…") and the concept's last sentence. The leaders tooltip ends "Hover a flag for the country, and click it to open the country." — how every vanilla flag behaves. The models pie tooltip ends with the exported-model push, which is the overview model cell's tooltip, `concept_ch_exported_model_desc` and `je_ch_how_models`.
- **Proposed:** quick fixes below: the share tooltip keeps title + "Since Last Month" + "Raw Score: X of a world total of Y"; the leaders tooltip keeps its first sentence; the pie tooltip keeps its first two sentences.
- **Effort:** quick
- **Confidence:** high (share, leaders), medium (pie)

### CH-9. The overview has no actionable reading; programme state lives two sections down
- **Category:** spread-out
- **Where:** `te_ch_overview_panel` (`cultural_hegemony_widget.gui:595-1107`) vs `te_ch_sec_programmes` (:1117)
- **Now:** the overview shows tier, rank, exported model, benchmark, share and the three leading flags — all readings, no actions. What the player can change (funding N/M, which of the four programmes run, whether an Enable is available) is only in the Programmes section, below the ten-row board. The three leader flags also repeat the board's first three rows directly underneath.
- **Proposed:** replace (or add beside) the leaders block a "Programmes" cell in the overview's icon-and-word shape: icon, word "2 of 4 Running", figure "Funding 3 / 5"; its hover lists the four programmes with Running/Idle (the existing `ch_policy_status_*` keys) and the funding cost. Backed by `ch_prog_count` (already computed in `ch_set_display_state`). Moving the Programmes section above the board would also do it, but that **reverses the owner's 2026-09-29 board-first decision** — prefer the cell, plus CH-2's halving of the board.
- **Effort:** medium
- **Confidence:** medium
- **In line or differ:** in line (rule 1/4: the overview answers "what needs attention"); the leaders block is an accepted design, so dropping it merely differs.

### CH-10. Programme-condition lines read as complaints next to a tick
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** style
- **Where:** `CH_MEDIA_BLOCKED_BY_PROTECTIONISM`, `CH_PROTECTIONISM_BLOCKED_BY_GLOBAL_MEDIA` (`te_miscellaneous_l_english.yml:235`, `:239`), used in `ch_possible_global_media_campaign` / `ch_possible_cultural_protectionism` (`cultural_hegemony_triggers.txt:94`, `:114`)
- **Now:** the triggers file says the clauses are "phrased as CONDITIONS, not complaints, because IsValidTooltip renders each of them with a tick or a cross", but these two read "Cannot launch a Global Media Campaign while Cultural Protectionism is in effect." — so a satisfied gate shows a green tick beside "Cannot launch…". Siblings read "Requires Ministry of Culture." / "We have 150 Influence available".
- **Proposed:** quick fixes below ("Cultural Protectionism is not in effect" / "No Global Media Campaign is running").
- **Effort:** quick
- **Confidence:** high

### CH-11. The funding tooltip is prose where its siblings are "Label: value"
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** style
- **Where:** `ch_policy_funding_step_tt` (`te_miscellaneous_l_english.yml:2021`), shown on the "Programme Funding" label and, through `custom_tooltip`, on both stepper buttons
- **Now:** "Each funding step adds: [modifier lines] and costs, per step, @money! X/week. At its current level the programme costs @money! Y/week." — the modifier lines are engine-rendered (good), but the costs are a run-on sentence, and "the programme" is wrong (funding is not one of the four programmes). The Outreach row's tooltip already uses "Cost: … /week".
- **Proposed:** quick fix below: "Cost per Step: …/week" and "Cost Now: …/week" as two lines.
- **Effort:** quick
- **Confidence:** high

### CH-12. Two colour keys for the same fifteen models, under different names
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** style / redundant
- **Where:** models legend `cultural_hegemony_widget.gui:1960-2145` (short names `je_ch_ov_model_*`, ≥0.5% only, with share) vs the history legend :2467-2542 (full names `ch_model_*`, all fifteen, two columns); loc `ch_model_hist_note` (`te_miscellaneous_l_english.yml:1993`)
- **Now:** one swatch is "Mixed" in one section and "Mixed / Other" two sections down ("Theocratic" / "Theocratic / Religious", "Absolutist" / "Absolutist Monarchist", "Military Junta" / "Conservative Military Junta"). The chart's note also carries implementation notes a player can't act on: "Old saves begin collecting after the update. Up to 100 annual snapshots are retained."
- **Proposed:** the history legend uses the short names with `ch_model_<m>_tt` on hover, as the models legend does (three columns of five fit 456 px at the medium font: "Constitutional" is the longest at ~14 chars ≈ 133 px). Note text: quick fix below.
- **Effort:** medium (legend) / quick (note)
- **Confidence:** medium
- **In line or differ:** in line (one name per thing, rule 3); the two-legend layout itself is accepted.

### CH-13. "Program" and "Programme" for the same things (spelling, mentioned once)
- **Category:** style (low)
- **Where:** modifier names `ch_cultural_program_funding` "Cultural Program Funding", `ch_cultural_program_funding_cost` "Cultural Program Cost", `ch_cultural_institutes_program` "Cultural Institutes Program" (`te_miscellaneous_l_english.yml:1964-1966`), `country_cultural_program_max_funding_add` "Cultural Program Maximum Funding Level" (`te_modifiers_l_english.yml:58`); vs the panel's "Programme Funding", "Cultural Programmes" and How's "programme". `ch_world_exposition_desc` has "centers".
- **Proposed:** align the four modifier names on "Programme" (the panel's spelling; `docs/player_guide/` uses both, "Cultural Programmes" and "Cultural programs"); the modifier list on the journal entry then matches the panel. Low priority; not put in Quick fixes because it is a mod-wide spelling call.
- **Effort:** quick
- **Confidence:** medium

### CH-14. Duplicate model explanation between How and the concept
- **Category:** over-explaining (How-section duplication only)
- **Where:** `je_ch_how_models` (`te_journal_entries_l_english.yml:24`) vs `concept_ch_exported_model_desc` (`te_concepts_l_english.yml:740`); `je_ch_widget_models_legend` (:115) vs `je_ch_widget_models_pie_tt` (:117)
- **Now:** the How paragraph repeats the concept's two sentences word for word ("the political movements matching it grow more active and attract more pops. The push is nothing while the model's share of world culture is small, and grows with it"), and the How legend note repeats the pie tooltip's "Slices run clockwise from the top in the order listed".
- **Proposed:** How keeps the paragraph (it is the learning place) and the pie tooltip drops its push sentence (CH-8). If the owner wants How shorter, cut `je_ch_how_models` to its first sentence plus "; the overview shows the current model and its push", since the term is a concept one hover away. `HOW_KEYS` in `test_cultural_hegemony_layout.py` only checks placement, not text.
- **Effort:** quick
- **Confidence:** medium

### CH-15. Type sizes predate the 17 / 20 / 16 ladder
- **Category:** style
- **Where:** every textbox in `cultural_hegemony_widget.gui`: rows, values and notes `fontsize_medium` (14, the tooltip face), the overview's words and the history legend `fontsize_small` (12), programme names and the funding label `fontsize_large` (20)
- **Now:** rule 3 (Workshop feedback 2026-10-13, owner 2026-10-17): rows, values, buttons and notes 17, subheadings 20, overview 16, "nothing a player reads to decide something is smaller", in panel templates (`banking_dash_fontsize_row` / `_heading` / `_overview`, Demographics' `te_demog_fontsize_*`). The CH rows are 14 and the overview 12.
- **Proposed:** add `ch_fontsize_row` (17), `ch_fontsize_heading` (20), `ch_fontsize_overview` (16, `tooltip_font`) at the head of the file and use them; then re-run `test_cultural_hegemony_layout.py`'s `LabelBudgetTest` (its `UNITS` would need the 17-point figure) and widen the 176/164/60 breakdown columns or shorten labels where it fails.
- **Effort:** medium
- **Confidence:** high (that it differs); medium (that the owner wants CH touched for this alone)
- **In line or differ:** in line with rule 3; the guide's CH exemption applies, so schedule it with any other CH rework.

## Findings — Covert Warfare

How the panel lists things today, for orientation: running operations, agent networks and known foreign operations
are already **datamodel rows** over script-container lists (`iw_ops`, `iw_nets`, `iw_known_ops`), and the funding
levels are a table (`covert_levels_row`). So the "should be a list" criterion is mostly met; the findings below are
about what each row shows, the launch path, and tooltips.

### COV-1. A running operation never says what it is doing; the caught-operation hovers are prose, not modifiers
- **Category:** hidden info + style (prose vs modifiers)
- **Where:** `covert_operations_widget.gui:598-669` (`widget_je_covert_operation_text`, eighteen instances, **no tooltip**); `:1065-1149` (`widget_je_covert_known_op_name`, tooltip `iw_op_exposed_desc_<type>`, `te_concepts_l_english.yml:1709-1726`)
- **Now:** after launch, nothing in the panel shows an operation's effect on its target: the row has its title, phase, detection risk and (espionage only) technology stolen. The effects appear once, at base strength, in the diplomatic action's launch preview. On the defending side, a watched operation's name hovers prose: "Jamming of military command and control. While it runs, its target's units fight with less offense and defense." — not the modifier lines the engine would print from the `covert_comms_disruption` static modifier the pulse applies.
- **Proposed:** give the row title a tooltip per type, `je_iw_op_row_<type>_tt`: `"#bold $iw_op_name_<type>$#!\nAt base strength, on [ScriptContainer.MakeScope.Var('iw_target_capital').GetState.GetCountry.GetName]:\n[GetStaticModifier('covert_<type>').GetDesc]$covert_<type>_extra_tt$\nNow: phase #G ×N#!, priority #G ×M#!"` (the `_extra_tt` lines already exist for the parts the engine cannot list, `test_covert_launch_preview.py` STATED). Rewrite `iw_op_exposed_desc_<type>` as one flavour sentence + the same `GetStaticModifier(...).GetDesc`. Both tooltips sit in datamodel items, so read only `ScriptContainer`/`GetPlayer`/globals (gotcha #24; `GetStaticModifier` is a global promote).
- **Effort:** medium (18 + 17 loc keys, one `tooltip =` per instance; the phase/priority multipliers need two container reads)
- **Confidence:** high (the gap); medium (that each `covert_<type>` modifier renders as cleanly as in the launch preview)

### COV-2. Deciding a launch needs four places; the launch tooltip has none of the target-specific numbers
- **Category:** spread-out
- **Where:** launch: `common/diplomatic_actions/covert_operations.txt` (e.g. `covert_election_interference_action` `accept_effect`, :96-118), loc `covert_op_phase_warning_tt`, `covert_op_detection_warning_tt` (`te_miscellaneous_l_english.yml:2347-2349`); panel: overview slots row, Operations' Detection Risk block, Agent Networks rows (`je_iw_net_row_benefit` "Head start for a new operation")
- **Now:** operations are launched from the target's diplomatic actions. Its tooltip lists the requirements (ticks), the effects at base strength, a 100-word phase paragraph and a generic warning ("Each month your agents are active, there is a chance they are discovered…"). What decides *whether and where* to launch is elsewhere: free slots and funding (Covert overview), our network in that country and its head start (Agent Networks, the third section), the shared detection factors (Operations), the extra upkeep the operation adds (shown nowhere: the Funding Levels table prices the operations already running) and the target's counterintelligence (only after launch, on the row's hover). So the path is summary → Agent Networks → Diplomacy panel → country → action, holding numbers in one's head.
- **Proposed:** (1) In each action's `accept_effect`, replace `covert_op_detection_warning_tt` with a short launch summary computed for `scope:target_country`: "Our network there: #v S#! (head start #v N#! months)" (a `covert_launch_net_line` printed from an `every_in_list = { variable = iw_nets limit = { var:iw_target = scope:target_country } … }` inside the tooltip, or "none") and "Upkeep: +@money! X/week at priority 1" (a `covert_operation_cost_with_one_more` script value). Keep the target's counterintelligence hidden before launch if that is intended. (2) Shorten `covert_op_phase_warning_tt` to "Preparatory for 6 months (no effect), then Establishing; Fully Operational from month 12 (#G ×N#!)." and move the rest (priority, exposure growth) to a concept `concept_operation_phase` that How and the row's phase line can share. Its hard-coded "six months" / "month 6" / "month 12" also break the widget's own rule that the 6/12 thresholds live only in script (`covert_operations_widget.gui:55-58`): read them from script values. (3) Panel side, see COV-12: give operation rows the target's flag, so a click opens the country where the actions are, as network rows already do.
- **Effort:** medium (2) / large (1)
- **Confidence:** medium (whether a tooltip-time `every_in_list` over our own list renders inside a diplomatic action's `accept_effect` needs one in-game check)

### COV-3. Each operation has up to three names
- **Category:** style
- **Where:** diplomatic actions `covert_<type>_action` (`te_miscellaneous_l_english.yml:2246-2387`); panel rows `je_iw_op_row_<type>` (`te_journal_entries_l_english.yml:509-540`); `iw_op_name_<type>` (`te_miscellaneous_l_english.yml:4584-4601`, used by the Known rows, events and custom loc); How / concepts
- **Now:**

  | type | Diplomacy action | our row | Known row / events |
  |---|---|---|---|
  | comms_disruption | Communications Disruption | Comms Disruption | Communications Disruption |
  | cultivate_assets | Cultivate Assets | Cultivating Assets | Asset Cultivation |
  | incite_autonomy | Incite Colonial Autonomy | Colonial Agitation | Colonial Agitation |
  | nuclear_sabotage | Nuclear Programme Sabotage | Nuclear Sabotage | Nuclear Programme Sabotage |
  | sabotage_colony | Sabotage Colony | Colony Sabotage | Colony Sabotage |
  | secure_material | Secure Loose Material | Securing Loose Material | Loose Material Search |
  | space_espionage | Space Programme Espionage | Space Espionage | Space Programme Espionage |
  | survey_defences | Survey Colony Defences | Colony Defences Survey | Colony Defences Survey |
  | counterintel_support | Counterintelligence Support | Supporting Counterintelligence | Counterintelligence Support |

  A player who launches "Incite Colonial Autonomy" finds "Colonial Agitation" on the Covert tab; How's Tradecraft text mixes "Nuclear Programme Sabotage" with "Sabotage Colony".
- **Proposed:** one name per type (owner's pick; the action's, minus "Covert: ", is the one the player chose from). Make the row titles splice it, `"#R $iw_op_name_comms_disruption$#! vs [...]"` (see COV-4 on the colour), so the row and the Known row cannot drift; align `iw_op_name_<type>` and the action names. The row title textbox is `multiline`, so a longer name wraps rather than elides.
- **Effort:** quick (loc), but a naming decision
- **Confidence:** high

### COV-4. Row titles are coloured red / yellow / green by an unstated rule that the exposure tiers contradict
- **Category:** style / hidden info
- **Where:** `je_iw_op_row_<type>` (`te_journal_entries_l_english.yml:509-540`); exposure tiers in the action descriptions (`$iw_exposure_tier_<tier>_note$`, `te_miscellaneous_l_english.yml:4558-4564`)
- **Now:** espionage and friendly operations are `#G`, meddling `#Y`, attacks `#R`. Nothing explains the colours, the house rule is "green is good for the player and red is bad", and they don't follow the exposure tier the player actually pays: Ideological Subversion is `#Y` but its exposure is *severe*; Comms Disruption and Infrastructure Sabotage are `#R` but their tier is *wartime* (costless once at war).
- **Proposed:** plain titles, plus one row line "Exposure: Routine Espionage / Interference / Attack on a Government / Wartime Sabotage" with the existing `iw_exposure_tier_<tier>_note` as its hover. It needs the tier on the container (a code the sync already knows from `covert_code_tier_*`) or four detail lines gated by tag sets.
- **Effort:** medium
- **Confidence:** medium

### COV-5. An operation's detection risk is a sentence, not the breakdown the shared block promises
- **Category:** list (table) / style
- **Where:** `je_iw_op_row_detection_tt` (`te_journal_entries_l_english.yml:517`); the shared block `covert_operations_widget.gui:1816-1848` (`je_iw_detection_base` / `_funding` / `_efficiency`, :420-425)
- **Now:** the shared block lists Base risk "10% a month", Funding Stealth "−8%" and Efficiency Factor "−25%". Each row then hovers "Our IC 45 against their 30, plus 5 defence… Funding, our network there, priority and our efficiency set the rest." — so the parts that differ per operation (network, priority) are never given a number. "−8%" is also percentage *points* (`concept_funding_stealth_desc`) while "−25%" is relative, and they print identically.
- **Proposed:** a table hover per row, "label: value": Base 10% · Their counterintelligence +X · Our network there −Y · Funding Stealth −Z · Priority +W · Efficiency ×(1−E) · **Detection Risk N% a month**. The monthly roll already writes `iw_detect`, `iw_tgt_ic`, `iw_tgt_td` on the container (`covert_warfare_effects.txt:247-252`); write the other terms beside them. Print Stealth as "−8 points" in the shared block (the priority hovers already say "+N points").
- **Effort:** medium
- **Confidence:** high

### COV-6. The Tradecraft bar uses the eye-shaped marker the guide retired, and its "→" means something else
- **Category:** style
- **Where:** `covert_operations_widget.gui:1680-1755`; loc `je_iw_tradecraft_line` (`te_journal_entries_l_english.yml:570`); `test_covert_layout.py:69` (texture allow-list)
- **Now:** the next tier's floor is drawn with `gfx/interface/progressbar/progressbar_marker.dds`, which rule 5 (play-test) dropped as ambiguous: "A fixed threshold on the bar is a thin vertical line with its own hover." The headline "42 → 60" uses the arrow the rule reserves for where a value is heading ("62 → 68 (+0.4/mo)"), but 60 is the next tier's floor. The Capacity bar above it has the standing floors (20/40/60/80% of the world's best) but draws none, so the standing icon and the bar don't connect.
- **Proposed:** thin 2 px lines at each Tradecraft tier floor (hover: "Seasoned at 60: Regime Change, …") and at each standing floor on the Capacity bar (hover: "Hardened from 60%"); headline "42 · next 60" (or the tier word). Drop `progressbar_marker.dds` from the test's allow-list.
- **Effort:** medium
- **Confidence:** high

### COV-7. The Tradecraft hover is How-it-works, and drops one tier's unlocks
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** over-explaining + inconsistency
- **Where:** `je_iw_tradecraft_tooltip` (`te_journal_entries_l_english.yml:571`) vs `je_iw_how_tradecraft` (:477) and `concept_tradecraft_desc` (`te_concepts_l_english.yml:939`)
- **Now:** the overview bar's hover is the rulebook: gains per operation, the cap on operations counted, losses per exposure category, decay, the tier modifiers, the unlock ladder. How and the concept say most of it again (and How ends "Hover Tradecraft in the overview for this month's figures"). Its Unlocks line lists nothing for Seasoned, where How and the concept give "Regime Change, Nuclear Programme Sabotage and Sabotage Colony", and leaves only Fledgling unbolded.
- **Proposed:** now: the Unlocks fix (Quick fixes). Then split: the bar's hover keeps the live reading (score, tier, "this month +N from M operations", the last change, the next tier and what it unlocks); the per-category loss figures move into `je_iw_how_tradecraft`, which then holds the whole rulebook once.
- **Effort:** quick (unlocks line) / medium (split)
- **Confidence:** high

### COV-8. The standing verdicts have no figure, no next threshold, and one shouts
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** hidden info / style
- **Where:** `je_iw_status_fortress` … `_vulnerable` (`te_journal_entries_l_english.yml:564-568`), the overview's first icon
- **Now:** five prose verdicts. Fortress alone is all caps with the country's name ("#bold INTELLIGENCE FORTRESS.#! #G France's counterintelligence…"). None says what the standing is measured on or how far the next one is; the floors (20/40/60/80% of the world's best) are only in How, and our percentage only in the capacity bar's hover.
- **Proposed:** quick fixes below: each verdict gains "[Intelligence Capacity]: 62% of the world's best; Hardened from 60%" from the same script values `je_iw_capacity_total` and `je_iw_how_standing` read, and Fortress is written like its siblings.
- **Effort:** quick
- **Confidence:** high

### COV-9. Row-button tooltips: the root they read may not exist there, and guard checks show as ticks
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** hidden info + over-explaining
- **Where:** `je_iw_stand_down_tooltip`, `je_iw_priority_step_up_tooltip`, `je_iw_priority_step_down_tooltip` (`te_journal_entries_l_english.yml:556-563`); guards `iw_stand_down_target_known_tt`, `iw_stand_down_op_matches_tt`, `iw_priority_op_known_tt`, `iw_priority_op_ours_tt`, `iw_expose_known_exists_tt`, `iw_expose_known_ours_tt` (`te_miscellaneous_l_english.yml:4553-4616`) in `covert_possible_stand_down` / `covert_priority_op_is_ours` (`covert_warfare_triggers.txt:212-253`) and `covert_expose_known_sgui`
- **Now:** (a) these three buttons sit inside a datamodel item, and their tooltips root on `JournalEntry.GetCountry.MakeScope`. The widget's own header (:69-72) and `docs/systems/journal_entry_systems.md` (Expose) say a tooltip there has no `JournalEntry` (gotcha #24), which is why the Expose button and the priority *label* hovers read `GetPlayer`. If so, the IsValid/Execute half of these tooltips silently fails, and a greyed Stand down or priority button doesn't say why (rule 6). (b) When they do render, every hover opens with ticked implementation guards — "The target of this operation can be identified", "This operation is one of ours and is still running", "The operation on this row can be identified", "We are watching this operation" — and `iw_priority_3_needs_tradecraft_tt` is ticked on every 1→2 step.
- **Proposed:** (a) root the three tooltips on `GetPlayer.MakeScope`, as Expose does (Quick fixes; harmless if the context does exist), and add the three keys to `test_covert_layout.py`'s `test_row_tooltips_need_no_journal_entry`. (b) Print each guard only when it fails, the pattern `covert_possible_priority_up` already uses for Cultivate Assets: `trigger_if = { limit = { NOT = { <guard> } } custom_tooltip = { text = <key> always = no } }`, and gate the priority-3 line on the step that reaches 3.
- **Effort:** quick (a) / medium (b, script)
- **Confidence:** medium (a: the context loss is the mod's documented belief, not observed for these keys); high (b)

### COV-10. Tooltips that repeat How, and one that points at a panel that no longer exists
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** over-explaining / stale
- **Where:** `je_iw_stand_down_tooltip` (:563), `je_iw_known_row_tt` (:486), `iw_increase_funding_effect_tt` (`te_miscellaneous_l_english.yml:4580`)
- **Now:** Stand down restates `je_iw_how_ops` ("that is the price of being caught, not of calling off") and says "the slot is freed" right above the effect line that says it again. The Known row hover restates `je_iw_how_watching`'s growth rules and adds "hover its name" (the name is underlined). The funding-up hover says "Higher funding buys better tradecraft… The ladder in the command centre lists what every level gives": the ladder became the Funding Levels table in round 3 (`test_covert_layout.py` checks it is gone), it sits directly under the stepper, "command centre" is the journal entry, and funding does not raise [Tradecraft] at all.
- **Proposed:** Quick fixes below.
- **Effort:** quick
- **Confidence:** high

### COV-11. "Funding is zero" is said in three places; the running state line explains
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** redundant / over-explaining
- **Where:** overview funding cell (dormant icon + `je_iw_ov_funding_tt`), Operations card `je_iw_funding_dormant_banner` (`te_journal_entries_l_english.yml:455`), Funding section `je_iw_funding_state` → `iw_funding_state_*` (`te_miscellaneous_l_english.yml:4574-4577`)
- **Now:** at zero the player reads "Unfunded" in the overview hover, the banner above the operations and the Funding section's first line. While running, the Funding section says "Operations are active. Each runs at its own phase strength and carries its own detection risk."
- **Proposed:** keep the overview cell and the Operations banner (rule 6, said once above the rows it affects); let the Funding section's state line show only for "ready" (funded, nothing running) where it says something new, or drop it; trim the running line (Quick fixes).
- **Effort:** quick (loc) / quick GUI gate
- **Confidence:** medium

### COV-12. Operation rows lack the target's flag; network rows spend two lines saying "nothing yet"
- **Category:** style / list compactness
- **Where:** `widget_je_covert_operation_row` (`covert_operations_widget.gui:481-885`) vs `widget_je_covert_network_row` (:1211-1349) and `widget_je_covert_known_row` (:920-1202); loc `je_iw_net_row_intel_none`, `je_iw_net_row_intel_ops_locked` (`te_journal_entries_l_english.yml:494-496`)
- **Now:** network and known-operation rows open with the vanilla `flag` widget (name on hover, click opens the country; rule 4); operation rows name the target only in text, so they can't take the player to the country whose diplomatic actions run them. A network row is six to eight lines; at low strength two of them are "Their service: nothing yet" and "Their operations against us: not yet known".
- **Proposed:** add the flag to the operation row (same `iw_target_capital` chain, gated on the variable as the network row does), between the operation icon and the title. Fold the two report lines into one "Report: none until strength 50" / "Report: service only" / full, with the report on hover. A further step (differs from the round-3 layout, so owner call): network rows as one-line table rows — flag · strength bar + trend · operations there · head start · report icon.
- **Effort:** medium
- **Confidence:** high (flag), medium (folding)

### COV-13. Launch-tooltip wording out of step with the panel
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** style
- **Where:** `covert_op_detection_warning_tt`, `iw_has_available_slot_tt`, `iw_funding_not_zero_tt` (`te_miscellaneous_l_english.yml:2347`, `:4578`, `:4573`); `concept_target_defenses` "Target's Defenses" (`te_concepts_l_english.yml:910`) vs the panel's "defence"; `iw_op_exposed_desc_comms_disruption` "offense and defense"
- **Now:** "@warning! Detection Risk: Each month your agents are active…" (plain text and second person, where the panel uses the concept and "we"); "Has an available Covert Operation slot" (the concept is Operation Slots); "Funding level must be at least 1 to launch operations" (a requirement, shown with a tick; also reused as a pact's maintenance condition). The detection hover renders `[Concept('concept_target_defenses', 'defence')]`, whose own title reads "Target's Defenses".
- **Proposed:** Quick fixes for the three keys. American spellings in the covert concepts (Defenses, offense, Destabilization) are mod-wide; mention only.
- **Effort:** quick
- **Confidence:** high

### COV-14. Type sizes predate the 17 / 20 / 16 ladder
- **Category:** style
- **Where:** `covert_operations_widget.gui`: rows and values `fontsize_medium` (14), overview words, the priority label and value and the Stand down label `fontsize_small` (12)
- **Now:** rule 3 asks 17 for rows, values, buttons and notes and 16 for the overview, in panel templates; "nothing a player reads to decide something is smaller". Stand down and the priority stepper, the row's only controls, are the smallest text in the panel.
- **Proposed:** `covert_fontsize_row` / `_heading` / `_overview` templates as Banking's; re-budget with `test_covert_layout.py`'s `UNITS`/`FIXED_CELLS` (which already measure every cell) and widen the 80/140 stepper and button cells.
- **Effort:** medium
- **Confidence:** high

## Applied in this PR

39 loc-only edits from this slice were applied (text rewritten in place, keys unchanged). The pre-edit text is in git history; the finding each serves is named above. Keys:

`CH_MEDIA_BLOCKED_BY_PROTECTIONISM`, `CH_PROTECTIONISM_BLOCKED_BY_GLOBAL_MEDIA`, `ch_board_detail_1`, `ch_board_detail_10`, `ch_board_detail_2`, `ch_board_detail_3`, `ch_board_detail_4`, `ch_board_detail_5`, `ch_board_detail_6`, `ch_board_detail_7`, `ch_board_detail_8`, `ch_board_detail_9`, `ch_model_hist_note`, `ch_policy_funding_step_tt`, `ch_tier_hegemon`, `concept_ch_art_production_desc`, `concept_ch_influence_tier_desc`, `concept_ch_prestige_desc`, `concept_ch_sol_desc`, `covert_op_detection_warning_tt`, `iw_decrease_funding_effect_tt`, `iw_funding_not_zero_tt`, `iw_funding_state_running`, `iw_has_available_slot_tt`, `iw_increase_funding_effect_tt`, `je_ch_ov_leaders_tt`, `je_ch_ov_share_tt`, `je_ch_ov_tier_4`, `je_ch_widget_models_pie_tt`, `je_iw_known_row_tt`, `je_iw_priority_step_down_tooltip`, `je_iw_priority_step_up_tooltip`, `je_iw_stand_down_tooltip`, `je_iw_status_defended`, `je_iw_status_exposed`, `je_iw_status_fortress`, `je_iw_status_hardened`, `je_iw_status_vulnerable`, `je_iw_tradecraft_tooltip`
