# Banking + Budget panel (Banking / Breakdown tabs) + top bar — GUI & localization audit

> Part of the 2026-10-27 GUI and localization audit; the index, the cross-cutting findings and the owner questions are in [`../gui_localization_audit.md`](../gui_localization_audit.md). Line numbers are as of the audit and drift as files change; search by key or type name. "Quick fixes" below means the loc-only edits this PR applied.

Scope read: `banking_layout_widget.gui`, `banking_dashboard_widget.gui` (all sections; the overview only for context, not relitigated), `banking_history_widget.gui`, the Banking and Breakdown parts of `budget_panel.gui`, `te_budget_breakdown.gui`, `te_budget_generated_charts.gui` + `scripts/generators/gen_budget_breakdown.py`, `topbar.gui` mod blocks, `je_banking.txt`, `te_monetary_sguis.txt`, `banking_dashboard_scripted_gui.txt`, `te_history_scripted_gui.txt`, `banking_policy_effects.txt`, `banking_policy_triggers.txt`, `banking_external_effects.txt`, and every loc key those render (~480 `banking_dash_*` keys, `banking_mon_*`, `banking_nonmod_*`, `CB_/CE_/CW_*`, `te_hist_*`, `te_budget_*`, the banking concepts). Line numbers are `te_miscellaneous_l_english.yml` unless another file is named.

## Top priorities

- **The Monetary Policy section's row tooltips are essays (BNK-1, BNK-2).** 19 row tooltips run 900–3,850 characters; most open with a verbatim copy of the label's own concept and then teach mechanics. The Budget tab's read-only readout (`banking_dash_ro_*_tt`) already says the same things in 300–900. Cut each row tooltip to reading + live breakdown, and move the rule tables into How Banking Works (which has no Prices, Exchange Rate, Gold or Arrangements topic today). Give each mandate button its own tooltip: today three of the four share one generic line, so the only place to learn what Growth does is the 3,849-character Mandate row tooltip.
- **The five "external" tools show raw trigger internals when their Enable button is greyed (BNK-3).** `banking_possible_cb_{restrict,sterilize}_inflows / foreign_borrowing_limits / fx_surrender / emergency_import_financing` test scripted triggers and script values with no `custom_tooltip` (`te_mon_in_financial_crisis`, `banking_external_export_share > 0`, `te_mon_gold_inflow_room > 0` …). Every older tool wraps each condition in a phrased condition line.
- **History bar tooltips (BNK-4).** A marker month prints the *whole current* intervention tooltip for each tool switched on or off, including "Requires" and today's live readings. Five of those keys read `JournalEntry.GetCountry…`, which the repo's own comment (`te_monetary_script_values.txt:1594`) says does not resolve in that script context. Print one name line per marker instead. The cycle charts' bars also print a bare "Cycle Value" with no reading.
- **Prose where engine-rendered lines belong (BNK-5, BNK-6).** Six intervention descriptions restate the not-a-modifier lines and Requires lines printed just below them (quick fixes below). The not-a-modifier lines themselves, the monetisation step and the mandate-change price are prose that `script_only` modifier fields would render as coloured, bulleted lines.
- **Breakdown tab tooltips (BNK-17, BNK-18, BNK-19).** One generic tooltip on 29 rows talks about *other* rows. Each institution row repeats seven pool-level figures and a formula. Every source row ends in the same boilerplate sentence. All three are generator changes.
- **JE text duplicates the overview, and the budget text is wrong (BNK-7, BNK-8).** The JE's `progress_desc` ("Free Intervention Points: X/Y") repeats the overview's Budget cell with a different denominator: it leaves out the banking-union point. The budget tooltip and concept both credit "economic-system laws", which grant nothing.

## Findings

### BNK-1. Monetary Policy row tooltips: definitions duplicated from the label's concept, mechanics taught in live tooltips
- **Category:** over-explaining / spread-out
- **Where:** `gui/journal_entry_widgets/banking_dashboard_widget.gui:2096-2966` (te_banking_sec_monetary). Loc by length: `banking_dash_mon_mandate_tt` 3,849 (1570), `_pegconf_tt` 2,438 (1597), `_paid_tt` 2,071 (1585), `_fx_effect_tt` 1,918 (1544), `_union_tt` 1,794 (1646), `_goldflow_tt` 1,639 (1555), `_fx_tt` 1,609 (1552), `_expected_tt` 1,606 (1536), `_anchor_tt` 1,528 (1501), `_worldrate_tt` 1,463 (1663), `_backstops_tt` 1,445 (1510), `_premium_tt` 1,349 (1602), `_rate_tt` 1,273 (1617), `_inflation_tt` 1,199 (1563), `_anchorpeg_tt` 1,050 (1506), `_delegation_tt` 994 (1533), `_bankgold_tt` 959 (1518), `_target_tt` 950 (1633), `_standing_tt` 939 (1624).
- **Now:** Every row's label is already a concept (`test_banking_layout.test_row_labels_are_concepts`), so hovering the word shows the definition. The row tooltip then repeats that definition word for word before its own content. Pairs that match verbatim or near-verbatim: `_expected_tt` / `concept_banking_expected_inflation_desc`, `_inflation_tt` / `concept_banking_inflation_desc`, `_world_tt` / `concept_banking_reference_rate_desc`, `_worldrate_tt` / `concept_banking_world_rate_desc`, `_standing_tt` / `concept_banking_credit_standing_desc`, `_premium_tt` / `concept_banking_risk_premium_desc`, `_bankgold_tt` / `concept_banking_bank_gold_desc`, `_goldflow_tt` / `concept_banking_gold_flow_desc`, `_monetise_tt` / `concept_banking_monetisation_desc`, `_delegation_tt` / `concept_banking_delegation_desc`, `_mandate_tt` / `concept_banking_mandate_desc`, `_target_tt` / `concept_banking_rate_target_desc`, `_fx_tt` / `concept_banking_exchange_rate_desc`, `_anchor_tt` / `concept_banking_monetary_anchor_desc`, `_union_tt` / `concept_banking_monetary_union_desc`. After that come rule tables in prose: peg confidence's monthly ±3/−2/+2 ladder; union tiers, adoption and exit terms; three ways to be anchored; swap-line repayment and lender-of-last-resort decay; all four mandates' behaviour. There is advice too ("#lore A government that intends to inflate away a war debt should not want that law.#!"). How Banking Works (`banking_layout_widget.gui:34-132`) covers the cycle, crashes, budget, rate and borrowing, but has no topic for Prices, the Exchange Rate, Gold and the Peg, Arrangements or the Mandates. So the hardest mechanics live only in live tooltips, and the How section's "What Borrowing Costs" (`banking_dash_how_borrowing`, 1446) duplicates `concept_banking_rate_paid_desc` instead.
- **Proposed:** One shape for every monetary row tooltip: `#header <Name>#!`, one line saying what the figure is *now* (or nothing, since the concept is one hover away), `$TOOLTIP_DELIMITER$`, then the live breakdown (`GetValueWithBreakdownFor`, the computed terms with their figures). The model is already shipped: the readout's `banking_dash_ro_rate_tt`, `_ro_mandate_tt`, `_ro_pegconf_tt`, `_ro_anchorpeg_tt`, `_ro_fx_tt`, `_ro_anchor_tt` (1750-1768), each 250–900 characters. Move the rule tables into How Banking Works as new subsections under the monetary-layer gate (`banking_layout_widget.gui:104`):
  - **Prices:** where expected inflation lands, the band ladder, the wage spiral.
  - **The Exchange Rate:** trade and price effects, overvaluation.
  - **Gold and the Peg:** vault, gap, hot money, the peg-confidence ladder.
  - **International Arrangements:** anchors, union tiers, backstops.
  - **The Mandates:** see BNK-2.

  Keep the per-row live figures exactly as now (the rows' `ScriptValue`/`Var` lines are the useful part). Rough budget: no row tooltip over ~600 characters of static prose.
- **Tests to carry:** `test_monetary_bank_qe.py:598-611` pins mandate and delegation sentences (move the assertions to the new keys). `test_monetary_rate_reach.py:304-317` pins the drift figures in `_rate_tt`/`_target_tt` (keep those; they are live data). `test_monetary_fx_confidence.py:67` pins "not won by deflating" in `_fx_tt`.
- **Effort:** large (a loc rewrite over ~20 keys, five new How subsections, three tests updated)
- **Confidence:** high

### BNK-2. The mandate buttons don't say what their mandate does
- **Where:** `banking_dashboard_widget.gui:2367-2418` (the 2×2 mandate grid); `common/scripted_guis/te_monetary_sguis.txt:324-338`; loc `banking_mon_mandate_set_tt` (1856), `banking_mon_mandate_peg_set_tt` (1855), `banking_dash_mon_mandate_tt` (1570)
- **Now:** Inflation Targeting (op 14), Dual Mandate (op 4) and Growth (op 5) all pass `TT = banking_mon_mandate_set_tt`: "Changes the rule your central bank follows, from the next monthly update. The mandate is then fixed for a year, and a looser rule than the bank runs now raises expected inflation and the risk premium for a while." Only Peg Defence has its own line. The effect's own header (`te_monetary_effects.txt:3768`) says "$TT$ exists because each mandate's button says what that rule does". So to compare rules the player reads the 3,849-character row tooltip. Action and information are split.
- **Proposed:** Four keys, `banking_mon_mandate_set_inflation_tt`, `_dual_tt`, `_growth_tt` and the existing `_peg_set_tt`. Each holds that mandate's paragraph from `banking_dash_mon_mandate_tt` (its "answers for prices alone…" etc. text, cut to two sentences), then the shared cost line. Pass them at `te_monetary_sguis.txt:324/328/338`. Then cut the row tooltip to "#header Mandate#!\nThe rule a delegated or independent bank follows. Now: [JournalEntry.GetCountry.GetCustom('te_mon_mandate_name')]." plus the "Changing it" and "By law" lines. The "Out of room" asset-purchase paragraph goes to How Banking Works → The Mandates; `concept_banking_asset_purchases_desc` already says half of it. The readout's `banking_dash_ro_mandate_tt` (1759) is the right length for the row.
- **Effort:** medium (four loc keys, three script parameter swaps; the `test_monetary_bank_qe.py:598` assertions move to the new key)
- **Confidence:** high

### BNK-3. Five external tools: the greyed Enable tooltip prints raw trigger internals
- **Category:** hidden info / style
- **Where:** `common/scripted_triggers/banking_policy_triggers.txt:1177-1269` (`banking_external_available`, `banking_external_eligible_*`, `banking_possible_cb_restrict_inflows / sterilize_inflows / foreign_borrowing_limits / fx_surrender / emergency_import_financing`), rendered by `banking_dash_action_button`'s `IsValidTooltip` (`banking_dashboard_widget.gui:222`)
- **Now:** These conditions are bare: `banking_external_available = yes` (it expands to `te_mon_full_system`, `banking_is_market_economy`, `te_banking_cycle_running`), `te_mon_has_dial = yes`, `te_mon_has_gold_flows = yes`, `banking_tool_*_active = no`, `banking_external_export_share > 0`, `te_mon_gold_inflow_room > 0` and `te_mon_in_financial_crisis = yes`. The last expands to `has_variable = finance_cycle_value`, `var:te_peg_confidence <= 40` and more. None has loc, so a greyed button lists internal names and variable comparisons. Every older tool (`banking_possible_cb_open_market_ops`, `…_moral_suasion`, :138-205) wraps each test in a `custom_tooltip` phrased as a condition. That is the style `te_monetary_sguis.txt:65-70` documents.
- **Proposed:** Wrap each test in a `custom_tooltip` with a short condition key. Examples: "Your economy runs on markets, with the full monetary system", "Your currency is on a convertible gold standard with a national bank" (`banking_mon_tt_recap_has_flows` already says this), "Your country exports something", "The bank's gold reserve has room", "A financial crisis is under way: a downturn, a panic, a run on your peg or hyperinflation", "Your treasury can pay this month's cost". Drop `banking_tool_*_active = no`: the row is hidden while the tool is active.
- **Effort:** medium (script and loc, about 8 new condition keys)
- **Confidence:** medium-high. The rendering of bare scripted triggers in `IsValidTooltip` is engine behaviour, so check one greyed button in game.

### BNK-4. History chart tooltips: full current tool tooltips per marker (five with broken accessors); cycle bars show no reading
- **Category:** over-explaining / hidden info / possible bug
- **Where:** `common/scripted_guis/te_history_scripted_gui.txt:45-435` (`custom_tooltip = te_hist_mk_enabled` + `custom_tooltip = banking_dash_tt_<tool>`, 76 branches); loc `te_hist_tt_bank_value_row` / `_momentum_row` / `_bubble_row` (7955-7959); `banking_history_widget.gui:246-366`
- **Now (a):** Hovering a bar from a month when a tool changed prints "Policy adopted this month:" and then the tool's entire dashboard tooltip: header, description, **"Requires: At least N free points"** (today's condition, not that month's), the modifier list, the not-a-modifier lines and, for five tools, **live figures from today** (`Held in peacetime for`, `Current FX debt protection`, `Monthly treasury cost`, …). A month with three changes stacks three such tooltips. Five of those keys, `banking_dash_tt_cb_{capital_controls_outflow, emergency_import_financing, foreign_borrowing_limits, fx_surrender, sterilize_inflows}`, read `JournalEntry.GetCountry.MakeScope.ScriptValue(…)`. The comment at `common/script_values/te_monetary_script_values.txt:1594-1600` says that in this history `custom_tooltip` context "a GUI ScriptValue accessor would not resolve and would log a data-system error every render". It is the reason the OMO figure is written out in words.
- **Now (b):** `te_hist_tt_bank_value_row:0 "$te_hist_chart_bank_value_title$"` (and the momentum and bubble rows) print the series name and nothing else, so the bar tooltip reads "1871.3 / Cycle Value". That is deliberate (the cycle readings are banded, not published), but it looks like a missing value.
- **Proposed (a):** Each branch prints one line: `custom_tooltip = te_hist_mk_enabled` followed by `custom_tooltip = CB_OPEN_MARKET_OPS` (the name key), or one new key per kind, e.g. `"#G Adopted:#! $CB_OPEN_MARKET_OPS$"`. The policy's effects are on its dashboard row. This also clears the five broken accessors. It reverses an implementer note ("so the marker tooltip shows the policy's real name, description and … effect list"), not an owner decision.
- **Proposed (b):** Print that month's band word: phase for Cycle Value (the bar's colour already shows it), and the band word for momentum and bubble pressure. Use a customizable localization over `ScriptContainer.MakeScope`, the scope `te_hist_tt_markers` already passes, or record the band code as its own `te_hist_v_*` at sampling time and switch on it with `SelectLocalization`. If neither is wanted, at least drop the bare title line.
- **Effort:** (a) medium (a mechanical script edit across 76 branches); (b) medium
- **Confidence:** (a) high on the over-explaining, medium on the broken accessors (from the repo's own documented rule, not seen in game); (b) medium

### BNK-5. Intervention descriptions restate the lines printed under them; Open-Market Operations states its requirement and its inflation cost twice
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** over-explaining / style
- **Where:** `CB_STERILIZE_INFLOWS_DESC` (155), `CB_RESTRICT_INFLOWS_DESC` (154), `CB_FX_SURRENDER_DESC` (147), `CB_FOREIGN_BORROWING_LIMITS_DESC` (146), `CB_EMERGENCY_IMPORT_FINANCING_DESC` (140), `CB_CAPITAL_CONTROLS_OUT_DESC` (83), `CB_OPEN_MARKET_OPS_DESC` (150), `banking_omo_inflation_cost_tt` (1898), `banking_omo_rate_floor_tt` (1899), `banking_omo_unbacked_money_tt` (1900); spliced by `banking_dash_tt_cb_*` (1792-1813)
- **Now:** The five tools added in the external pass have descriptions in a spec voice that list the same figures as their `banking_nonmod_*_tt` lines a few lines lower in the same tooltip. Compare "Costs 0.05% of annual GDP on activation and each month, rising to 0.10% after 12 funded months…" with `banking_nonmod_emergency_import_financing_tt`'s "costs 0.05% of annual GDP from the treasury, rising to 0.10% after 12 funded months". Their siblings use one or two flavour sentences and leave the effects to the engine lines. The OMO tooltip says "only a fiat or digital currency… only once the policy rate has run out of room" in the description and again in two Requires lines. It says "+1 point of price pressure" in `banking_nonmod_open_market_ops_tt` and again in `banking_omo_inflation_cost_tt` ("pushes inflation up by about 1%…").
- **Proposed:** Flavour descriptions that keep only what no line below says (Quick fixes 7, 9-14). OMO: cut the requirement sentence from the description, and cut the restated figure from `banking_omo_inflation_cost_tt` (Quick fix 8). The two OMO Requires lines are also IsValidTooltip conditions (`banking_policy_triggers.txt:159-166`), so a condition-length form reads better beside its tick. For example, `banking_omo_rate_floor_tt`: "Your policy rate has no room left to fall: zero under a fiat currency, lower under a digital one. While there is room, a cut does the same job more cheaply." That one is left out of Quick fixes because it drops some flavour. When applying, update two developer comments: `extra_modifiers.txt:1086-1088` ("the button's description does") and `te_monetary_script_values.txt:1594` ("two loc strings").
- **Effort:** quick
- **Confidence:** high

### BNK-6. Effect prose where engine modifier lines are preferred
- **Category:** style
- **Where:** `banking_nonmod_*_tt` (1883-1897), spliced into `banking_dash_tt_cb_*` and printed by `custom_tooltip` in `banking_policy_effects.txt`; `banking_mon_monetise_step_tt` (1857, the Monetise Deficit ± buttons); `banking_mon_mandate_set_tt` (1856) and the "Changing it" paragraph of `banking_dash_mon_mandate_tt` (the price of a looser mandate); `banking_bank_holiday_radicals_tt` (1329)
- **Now:** Paragraphs carry modifier-shaped effects. `banking_mon_monetise_step_tt`, for example: "Every step is worth about 1% of a year's economic output in newly minted money… about 2.5% on inflation… and 0.5% on everything you borrow". The mandate cost reads "For each step looser, expected inflation rises by 0.5 points and the risk premium by 0.5 points, fading over two years". The not-a-modifier lines read "Each month: three quarters of the price pressure from gold coming in is offset…". The tool's static modifier sits right above them as a coloured, bulleted list.
- **Proposed:** In the order of preference (a static modifier's `GetDesc`, then a visible `add_modifier`, then a `script_only` type):
  - **Monetisation step:** a display-only static modifier `te_mon_monetisation_step` with `country_inflation_pressure_add = 2.5`, `country_risk_premium_add = 0.005` (both types exist) and a `script_only` minting-share field. The tooltip becomes "Each step, while it runs:\n[GetStaticModifier('te_mon_monetisation_step').GetDesc]\n#lore Takes effect at the next monthly update.#!". It renders in `ExecuteTooltip`, since `GetStaticModifier` needs no GUI root.
  - **Mandate cost:** the same, as "On choosing a looser rule:" `[GetStaticModifier('te_mon_mandate_loosen_cost').GetDesc]`.
  - **External tools:** `script_only` fields on their own static modifiers, e.g. `country_te_mon_inflow_sterilised_mult = 0.75`, `country_te_mon_inflow_halved_mult`, `country_te_mon_rate_gap_damp_mult = -0.75`, `country_te_mon_reserve_purchase_gdp_add = 0.0005`, `country_te_mon_tool_cost_gdp_add = 0.0001`. Loc them in `te_modifiers_l_english.yml`. They then print inside "While active:" with signs and colours, and the `banking_nonmod_*` lines shrink to the conditions no modifier can say ("Lifted automatically when the crisis ends…").

  Script that reads the figures can read the modifier back (`modifier:country_te_…`), so text and effect cannot drift. `test_banking_external_tools.NonModifierTooltipTest` would move from loc text to modifier values.
- **Effort:** medium (new modifier types, about 4 display modifiers, loc, test updates)
- **Confidence:** medium (the direction matches the owner's stated preference; each figure's exact modifier form is a design call)

### BNK-7. The JE's progress line repeats the overview's Budget cell, with a different total, and shows while dormant
- **Category:** spread-out/redundant
- **Where:** `common/journal_entries/je_banking.txt:241-256` (`progress_desc`); loc `banking_cycle_progress_desc` / `_command` / `_coop` (`te_concepts_l_english.yml:408-410`); drawn by `gui/journal_entry.gui:821` whatever the `progressbar = no`
- **Now:** "Free Intervention Points: [free, with breakdown]/[ScriptValue('banking_law_base_points_value')]". The overview's Budget cell shows "N used / M free", where M is out of `banking_display_points_total`, which includes the banking union's +1 (`extra_script_values.txt:3356-3367`, `te_mon_union_banking_union`). With a banking union the JE line reads e.g. "8/7". It also shows for a dormant entry, where the overview hides the budget on purpose ("Row 2 waits too: its budget is for the tools", `banking_dashboard_widget.gui:717`). Style rule 1 says the status text must not repeat the overview, and the JE's comment at :258 says the status text was removed for that reason. The progress line survived.
- **Proposed:** Delete the `progress_desc` block. Keep its one unique content, the per-grant/per-tool breakdown, by appending `\n$TOOLTIP_DELIMITER$\n[JournalEntry.GetCountry.GetModifier.GetValueWithBreakdownFor('country_banking_intervention_max_add')]` to `banking_dash_budget_free_tt` (1380). Then fix `te_budget_banking_open_journal_tt` (6603), "which adds the entry's description and status text", to "which adds the entry's description".
- **Effort:** quick (script and loc)
- **Confidence:** high

### BNK-8. Budget tooltip and concept credit "economic-system laws" with points they don't grant
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** other (accuracy)
- **Where:** `banking_dash_budget_tt` (1382), `concept_banking_intervention_budget_desc` (`te_concepts_l_english.yml:715`)
- **Now:** "Your banking, monetary and economic-system laws set how large the budget is." Only the seven Financial Regulation laws, `law_national_bank` (`extra_laws.txt:2873-3028, 3664`) and the bloc banking union grant `country_banking_intervention_max_add`. How Banking Works gets it right: `banking_dash_how_budget` (1447), "Your [concept_financial_regulation] law sets most of the budget, and a national bank and a power bloc's banking union add a point each."
- **Proposed:** Quick fixes 1-2.
- **Effort:** quick
- **Confidence:** high

### BNK-9. The rate-drift rule is stated in three tooltips and two concepts
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** over-explaining / redundant
- **Where:** `banking_dash_mon_rate_tt` (1617), `banking_dash_mon_target_tt` (1633), `banking_mon_step_tt` (1859, the ± buttons' ExecuteTooltip), `concept_banking_policy_rate_desc` and `concept_banking_rate_target_desc`
- **Now:** The rate and target rows each give "each month the rate closes X% of … whichever is less, and never less than Y of a point" with live figures (both pinned by `test_monetary_rate_reach.py:304`). The step button adds a third, static version: "at least a third of a point a month, two thirds under Digital Currency… a sixth of the distance…".
- **Proposed:** Keep the live figures on the Target row only, and give the Policy Rate row one sentence pointing to it. That needs a test edit, so it is a finding. The button keeps the click modifiers and drops the drift arithmetic (Quick fix 5).
- **Effort:** quick (button) / medium (the row, with its test)
- **Confidence:** high

### BNK-10. The top bar's phase tooltip says "The bar shows…" and "(see below)"
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** style / context
- **Where:** `banking_dash_top_phase_tt` (1791) splices `banking_dash_phase_tt_body` (1727); the type is at `banking_dashboard_widget.gui:1135-1195` and the instance at `gui/topbar.gui:601`
- **Now:** In the top bar there is no bar and nothing below: "The bar shows roughly where in the phase you are…" and "Pushed each month by: Current momentum (see below)". `test_topbar_banking.py:294` pins the splice, not the body's words.
- **Proposed:** Make the body context-free (Quick fix 6). It names the bar and makes momentum a concept link, so it also reads right in the overview cell.
- **Effort:** quick
- **Confidence:** high

### BNK-11. Active Policies: in-force tools named as orders, no time left on timed tools, OMO listed twice
- **Category:** style / hidden info / redundant
- **Where:** `banking_dashboard_widget.gui:1205-1969` (te_banking_sec_active); OMO also at :2430 (under the rate target); names `CB_BANK_HOLIDAY` "Declare a Bank Holiday", `CB_RESERVE_REQUIREMENTS` "Raise Reserve Requirements", `CB_RAISE_MARGIN_REQ`, `CB_EXPAND_DEPOSIT_GUARANTEE`, `CB_RESTRICT_INFLOWS`, `CB_STERILIZE_INFLOWS`, `banking_dash_name_cb_foreign_borrowing_limits` "Limit Foreign Borrowing"
- **Now:** The list of what is in force reads "Declare a Bank Holiday [Disable]" and "Raise Reserve Requirements [Disable]". There is already a precedent for an active-row name: `banking_dash_name_active_cb_directed_credit_*` ("Credit to Agriculture"). A Bank Holiday runs `days = 90` (`banking_policy_effects.txt:303`), and the 90-day reopen bonus depends on staying shut the full term, but the row never shows days left. A running OMO appears twice, here and under the rate target, each with a Disable button.
- **Proposed:**
  - **Names:** `banking_dash_name_active_*` keys for the verb-named tools, using the modifier names where they exist ("Bank Holiday", "Raised Reserve Requirements", "Raised Margin Requirements", "Expanded Deposit Guarantee", "Speculative Inflow Limits", "Inflow Sterilisation", "Foreign Borrowing Limits"), wired the way the directed-credit rows are. `WidthBudgetTest` covers widths.
  - **Bank Holiday:** "N days left", from a `te_banking_holiday_end` date variable or a days-left variable kept by the weekly pulse that already runs, either as the row's cost cell for that row or as a second line.
  - **OMO:** leave it in both places (the Monetary Policy copy sits beside the rate it acts on), or hide the Active Policies copy while `banking_mon_shows_omo` holds. Low priority.
- **Effort:** quick (names) / medium (days left)
- **Confidence:** medium-high

### BNK-12. Available Interventions: "no points free" is said 40 times, never once above the rows
- **Category:** style (rule 6)
- **Where:** `banking_dashboard_widget.gui:3174-3209` (the heading and the dormant note); `banking_dash_budget_free_tt` (1380)
- **Now:** At 0 points free every Enable button is greyed, and each tooltip says why. The section says it once only in the dormant case (`banking_dash_dormant_tools_note`).
- **Proposed:** A second note under the heading, the dormant note's shape: `visible = "[And( GetScriptedGui('banking_dash_cycle_running').IsShown(…), LessThanOrEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('banking_display_points_free'), '(CFixedPoint)0' ) )]"`, text `banking_dash_no_points_note`: "#lore No points free: disable an active policy to switch another on.#!". The overview's Budget cell is far above a scrolled list, so this puts summary and action together.
- **Effort:** medium (GUI and one key)
- **Confidence:** medium-high

### BNK-13. Lists: Monetary Union holdouts and Backstops are counts and sums, not lists
- **Category:** list
- **Where:** `banking_dash_mon_union_value` → `banking_dash_mon_union_state_leader` / `_pressing` (1639-1641): "your currency — N holdouts (M would refuse)". `banking_dash_mon_backstops_value` (1512): "−X received, +Y extended". Rows at `banking_dashboard_widget.gui:2668-2696`.
- **Now:** A bloc leader deciding whether to Press for Convergence sees how many members hold out, not which, or which would refuse. A country with several monetary treaties sees summed premium points, not which partner backs it or whom it backs. The 1,445-character Backstops tooltip explains the rules instead.
- **Proposed:**
  - **Union:** under the Monetary Union row, a datamodel over `[JournalEntry.GetCountry.GetPowerBloc.GetMembers]` (vanilla's `PowerBloc.GetMembers`, `gui/power_bloc_panel.gui:1839`), one row per member: flag, name, and a status word from a `type = country` custom loc evaluated on the member (adopted / holding out / would refuse / outside). The Demographics state-row shape fits, but needs no script list. Shown for the leader only.
  - **Backstops:** a variable list `te_mon_arr_partners` (each partner country, with role and points) built in the monthly arrangement discovery that already computes `te_mon_arr_recipient_pts` / `_provider_pts`, drawn as rows of flag, name, "swap line received −1.0" and so on.

  Both let the tooltips drop most of their prose (BNK-1).
- **Effort:** large (union: a GUI datamodel and one custom loc; backstops: a new script list too)
- **Confidence:** medium (check `GetPowerBloc` from a JE datacontext in game)

### BNK-14. Monthly treasury payments of three tools appear nowhere in the Budget panel
- **Category:** hidden info
- **Where:** `common/scripted_effects/banking_external_effects.txt:24-60` (`add_treasury = banking_external_sterilization_payment`, `banking_external_import_payment`, `banking_external_surrender_payment`); Breakdown source tooltip `te_budget_chart_source_expense_banking_tt`
- **Now:** Sterilize Capital Inflows, Emergency Import Financing and FX Surrender take money from the treasury every month with `add_treasury`. That never reaches the weekly budget, so neither the Overview nor the Breakdown's Banking row shows it. The Breakdown says outright that "One-time treasury payments … are excluded". The only place the cost shows is the tool's own tooltip ("Monthly treasury cost: £X").
- **Proposed:** Best: charge them as a weekly `country_expenses_add` static modifier refreshed monthly with `multiplier = <cost>` (the dynamic-modifier pattern), and add those modifiers to `SOURCES["expense"]["banking"]`, so the Overview and the Breakdown both show them. That is a gameplay change, so check the economics. Lighter: a `CARVE_OUTS`-style extra line on the Banking source tooltip, "Paid monthly from the treasury, outside the weekly budget: £X", reading a sum script value.
- **Effort:** medium-large (modifier route) / medium (tooltip route)
- **Confidence:** high on the gap, medium on the fix

### BNK-15. One thing, several names
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** style
- **Where:** labels, concepts and tooltip headers across the section
- **Now:**
  - "Price Pressure" (row label, `banking_dash_mon_pressure_label`, and `banking_dash_mon_purchases_tt`'s "the Price Pressure list") vs "Inflationary Pressure" (`concept_banking_price_pressure`, the `country_inflation_pressure_add` header, and every `[concept_banking_price_pressure]` in the not-a-modifier lines).
  - "Wage Pressure" vs "Wage Pressure on Prices" (`country_wage_pressure_add`).
  - "Bank's Gold" (concept) vs "Bank's Gold Reserve" (`banking_dash_mon_bankgold_tt` header).
  - "World Rate Gap" (label) vs "Gap to World Rate" (`banking_dash_mon_goldgap_tt` header; the label was renamed per the comment at :78, the header was not).
  - "Reference Rate" (label) vs "World Reference Rate" (concept and header) beside "World Rate". Two near-synonyms side by side.
  - "Banking Cycle" (concept) vs "financial cycle" (all prose, the dormant notes) vs "Boom & Bust Cycle" (JE title) vs "Banking Cycle Value" (bar) vs "Cycle Value" (chart).
  - "Banking Momentum" (concept) vs "Momentum" vs "Cycle Momentum" (`te_hist_chart_bank_momentum_title`).
  - "Counter-cyclical Buffer" vs "Countercyclical Capital Buffer" (modifier) vs "Enable Counter-cyclical Buffer".
  - Points: "free Banking Intervention Points" (`BANKING_POINTS_N`, not bold) vs "free planning budget points" / "council mandate points" (`PLANNING_POINTS_N` / `COUNCIL_POINTS_N`, figure in `#bold`) vs the overview's "Budget"/"Intervention Budget", whose concept says "banking interventions" even under a command economy.
  - Spelling: "Sterilize", "stabilize", "grayed" next to "Recapitalise", "Monetise", "Mobilisation", "Defence".
- **Proposed:** Pick one name per thing and use it in label, concept, header and prose. Suggestions:
  - "Price Pressure" for the concept, the modifier name and the header.
  - Headers that match labels: "World Rate Gap" (Quick fix 4), "Bank's Gold".
  - Make the two rates' names differ by more than one word: the label "Reference Rate" against the concept "World Reference Rate", beside "World Rate", reads as one figure twice. For example, name the concept "Reference Rate" and keep "World Rate".
  - "Banking Cycle" everywhere a concept fits, "financial cycle" only in flavour.
  - Point lines in one form, e.g. "At least #bold 2#! free intervention points". A command-economy variant of the Budget caption (customizable localization on the economy, as `te_banking_cycle_title` does).
  - British spelling throughout (one pass; low priority).
- **Effort:** quick (most are loc) / medium (the concept-name changes touch loc in other slices)
- **Confidence:** high (that they differ); the chosen names are suggestions

### BNK-16. The JE's description paragraph is a how-to, shown under the panel in the JE only
- **Category:** over-explaining
- **Where:** `je_banking_cycle_reason_market` (`te_journal_entries_l_english.yml:18`), via `te_banking_cycle_reason` (`common/customizable_localization/zzz_extra_custom_loc.txt:25`), rendered open at `gui/journal_entry.gui:749` below the widgets; `je_banking_cycle_desc` (:14) says the same in one line
- **Now:** About 690 characters: "Steer the cycle with the policy rate, macroprudential tightening, targeted bailouts, and open-market operations; [concept_fx_swap_lines] are arranged… Apply measured regulatory tightening and liquidity drains… Expect political trade-offs…" That is strategy advice in a live, always-open block, below How Banking Works. The command and cooperative variants (:16-17) are shorter but the same kind.
- **Proposed:** One framing sentence per economy, e.g. "In a Market Economy the [concept_banking_cycle] is a liquidity and sentiment gauge: [concept_banking_momentum] is investor-driven growth, [concept_bubble_pressure] is overvaluation. [concept_fx_swap_lines] are arranged with another country by treaty." The tool advice is already in each tool's tooltip and in How Banking Works.
- **Effort:** quick
- **Confidence:** medium (flavour is the owner's call)

### BNK-17. Breakdown: one generic tooltip on 29 rows describes other rows
- **Category:** over-explaining / hidden info
- **Where:** `scripts/generators/gen_budget_breakdown.py:377-383` (the default `tooltip = "te_budget_chart_row_tt"`) and `:148` (its text); output `gui/te_budget_generated_charts.gui` (29 uses); loc `te_budget_chart_row_tt` (`te_budget_l_english.yml:93`)
- **Now:** Income Tax, Poll Tax, Tariffs, Minting, Welfare, Subsidies, Interest, Construction Goods and the rest all show: "Weekly amount and share of positive amounts. Other Civil Buildings excludes the administration costs allocated to institutions and General Administration, and the Space Program… Other Income and Other Expenses reconcile…". It says nothing about the row hovered. Meanwhile vanilla's Overview gives each of these rows a tooltip with a graph, through templates the mod's `budget_panel.gui` already uses: `tax_income_tooltip_with_graph`, `tax_poll_tooltip_with_graph`, `tariffs_tooltip_with_graph`, `minting_tooltip_with_graph`, `welfare_payments_expense_tooltip_with_graph`, `interest_expense_tooltip_with_graph`, … (30 of them).
- **Proposed:**
  - In `chart()`, map each vanilla leaf to its vanilla template. Add a `TOOLTIP_TEMPLATES` dict next to `INCOME`/`EXPENSE` and emit `using = <template>` on the row instead of `tooltip = …`. Because they read `GetPlayer` they work under `TopScope`.
  - Give `civil`, `other`, `additional` and `military_adjustment` their own one-line keys, e.g. `te_budget_chart_civil_tt`: "Wages and goods of universities, ports and other civil buildings. Government Administration is split among your institutions above, and the Space Program is under Programme Costs."
  - Delete `row_tt`.
- **Effort:** medium (generator and a regeneration; check in game that a template on a flowcontainer row renders, since vanilla puts it on a textbox, and move it to the amount textbox if not)
- **Confidence:** medium-high

### BNK-18. Breakdown: each institution row repeats seven pool-level figures and a formula
- **Category:** over-explaining / redundant
- **Where:** `gen_budget_breakdown.py:505-517`; loc `te_budget_chart_institution_*_tt` (24 keys, `te_budget_l_english.yml:57-80`)
- **Now:** Every institution's tooltip lists Current level, Administration cost, Bureaucracy produced, Institution bureaucracy use, Institution pool and Total institution levels, all the same in every row except the level, then "Allocated cost", then the formula "Administration cost × institution bureaucracy use ÷ bureaucracy produced, capped…; then institution pool × current level ÷ total institution levels."
- **Proposed:** Institution row: "#b $institution_x$#!\nLevel [level] of [total levels] institution levels: @money![allocated] of the @money![pool] institution pool." Put the pool figures (administration cost, bureaucracy produced, institution use, pool) once on the **Administration** group row's tooltip, which today is the generic `group_tt`. The formula stays in How the Breakdown Works, which already states it in prose.
- **Effort:** medium (generator)
- **Confidence:** high

### BNK-19. Breakdown: the same mechanics sentence on every source, group, arrow and pie
- **Category:** over-explaining
- **Where:** `gen_budget_breakdown.py:147` (`pie_tt`), `:158` (`expand_tt`), `:160` (`group_tt`), `:497-503` (every `te_budget_chart_source_*_tt`)
- **Now:**
  - **Source rows:** each ends "\n\nCurrent applied sources, including temporary charges, their multipliers and any decay. One-time treasury payments and non-monetary costs are excluded from the weekly budget." That is boilerplate on 15 rows, already in How ("One-time treasury payments and non-monetary resource costs are outside the weekly budget").
  - **Group rows:** `group_tt` (9 rows) explains denominators ("Shares count positive component amounts; refunds remain signed, so expansion never changes the denominator. A zero net group can still contain costs and refunds.").
  - **Arrow and pie:** `expand_tt` and `pie_tt` restate how collapsed groups make slices.
- **Proposed:**
  - Source tooltip: "#b Banking#!\nWeekly amount: …\n$TOOLTIP_DELIMITER$\n[GetDescFor…]", with no trailing paragraph and no blank lines.
  - `group_tt`: "Includes the indented rows below it."
  - `expand_tt`: "Show or hide the rows inside."
  - `pie_tt`: "Each colour matches a row below. Expand a group to split its slice."
  - The denominator and refund rules stay in How (they are there).
- **Effort:** quick (generator strings and a regeneration)
- **Confidence:** high

### BNK-20. Breakdown: "How the Breakdown Works" is one text block, smaller than the house type, and mixes UI help with accounting
- **Category:** style (How-it-works structure) / over-explaining
- **Where:** `gui/te_budget_breakdown.gui:53-74`; `te_budget_chart_how_text` (generator `:150`); `te_budget_chart_materials_tt` (`:159`); rows at `te_budget_breakdown.gui:17-38`
- **Now:**
  - **One block:** a single `fontsize_medium` (14, the tooltip face) textbox with four `#b` pseudo-headings. The last paragraph (~1,100 characters) runs from "Groups start collapsed. Click the arrow…" through Army/Navy wage derivation, logistics centres, palette repetition and zero-share adjustments.
  - **Duplication:** `materials_tt` repeats part of that paragraph word for word.
  - **Type size:** every Breakdown row (labels, amounts, shares) is `fontsize_medium` too. The guide's ladder is "Rows, values, buttons and notes are 17, subheadings 20; nothing a player reads to decide something is smaller" (rule 3). Banking's How uses `banking_dash_subheader` + `banking_dash_note` at 20/17.
- **Proposed:**
  - **Split** into subheaded notes: Administration; Military (Wages, Materials and Support, Other Military Costs); Journal Systems; Reading the Charts. Use Banking's types or a `te_budget_how_subheader`/`_note` pair, which needs a list of keys in the generator's `LOCALIZATION`.
  - **Cut** "Click the arrow…", "Rows are ordered from largest…" and "Category colors stay fixed…": the UI shows all three.
  - **`materials_tt`:** "Branch goods, plus the upkeep of logistics centres and naval fortifications. Navy also includes warship construction and maintenance."
  - **Type size:** move rows to the 17 serif (`banking_dash_fontsize_row` is global, or the Breakdown gets its own template). Widen the label column first: at 8.5 units/char, 271 holds about 30 characters, and "Ministry of Intelligence and Security" wraps (`multiline = yes` already).
- **Effort:** medium (generator, GUI, regeneration; `test_budget_breakdown.py` does not pin `how_text`)
- **Confidence:** medium-high (type size: medium; the Breakdown postdates the 2026-10-13/17 passes, which named Banking's panels)

### BNK-21. Breakdown mirror line in every cost modifier: shorter label
- **Category:** style
- **Where:** `gen_budget_breakdown.py:487`; loc `country_te_budget_expense_*_add` (`te_budget_l_english.yml:7-46`)
- **Now:** Every banking event charge's modifier tooltip shows its amount twice: "Government Expenses +£X" and "Counted in the Budget Breakdown under Banking +£X". That is a documented trade-off (`docs/systems/budget_breakdown.md` §"Journal systems"). The second line is long.
- **Proposed:** A tag-like name, "Breakdown: Banking", which keeps the `_desc` ("Not a second charge…"). `test_budget_breakdown.py:485` pins the current wording.
- **Effort:** quick (generator and test)
- **Confidence:** medium (low priority)

## Applied in this PR

14 loc-only edits from this slice were applied (text rewritten in place, keys unchanged). The pre-edit text is in git history; the finding each serves is named above. Keys:

`CB_CAPITAL_CONTROLS_OUT_DESC`, `CB_EMERGENCY_IMPORT_FINANCING_DESC`, `CB_FOREIGN_BORROWING_LIMITS_DESC`, `CB_FX_SURRENDER_DESC`, `CB_OPEN_MARKET_OPS_DESC`, `CB_RESTRICT_INFLOWS_DESC`, `CB_STERILIZE_INFLOWS_DESC`, `banking_dash_budget_free_tt`, `banking_dash_budget_tt`, `banking_dash_mon_goldgap_tt`, `banking_dash_phase_tt_body`, `banking_mon_step_tt`, `banking_omo_inflation_cost_tt`, `concept_banking_intervention_budget_desc`
