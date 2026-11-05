# Legislated Tax Code — GUI & localization audit

> Part of the 2026-10-27 GUI and localization audit; the index, the cross-cutting findings and the owner questions are in [`../gui_localization_audit.md`](../gui_localization_audit.md). Line numbers are as of the audit and drift as files change; search by key or type name. "Quick fixes" below means the loc-only edits this PR applied.

Slice: `je_tax_code` and the Budget panel's Tax Code tab (both hosts compose the same types from
`gui/journal_entry_widgets/te_tax_*_widget.gui`), the light code's panels, the scripted-GUI handlers
and command tooltips they render, and `te_tax_l_english.yml` / `te_tax_generated_l_english.yml`.
Read-only audit; every claim below was checked against the markup and loc at the line given.

**Status:** every finding is done in the GUI audit wave of 2026-10-27 (branch `wave/gui-tax`); each finding's Status line says how, and where the build departs from the proposal.

## Top priorities

- **The overview doesn't answer "what needs me now?"** It lists version, last change, snapshot date and
  one month per item, but not whether the bill can pass, whether a promise is failing, whether the
  draft is blocked, or whether a group has an offer waiting. Rebuild it as Banking-style two-up cells
  with a status word per process (TAX-1).
- **The bill's actions sit below every interest-group card.** Pass / Revise / Withdraw / Force Through
  come after up to eight cards of eight lines each, far from the Conditions table that decides them. Move
  the button row under the conditions, and give the Budget tab a pinned bill footer like the draft's
  (TAX-2). Merge the duplicated committed-share bar and row (TAX-5), and slim the cards (TAX-6).
- **A blocked draft's fix is hidden.** Introduce is greyed by "Accept each such change first", but the
  Accept buttons live only inside the collapsed Review. The player guide even says the workbench row is
  marked (TAX-3).
- **What the draft does to revenue is the last thing in a collapsed section, written as sentences.**
  Put a net figure in the pinned draft summary and make the estimate a table (TAX-4).
- **Information the code holds but never shows.** The enacted taxed goods appear only as a count. The
  enacted regional-relief states aren't listed. A passed bill's relief changes appear nowhere. Rates'
  "since" dates exist as views but aren't drawn. The greyed native Budget controls don't say why
  (TAX-11, TAX-12, TAX-20).
- **Boilerplate repeated on every row and button**, much of it restating engine-rendered modifier lines
  or the How-it-works text: 30 loc-only Quick fixes (TAX-7 to TAX-10, TAX-16, TAX-23).
- **The whole UI is a step below house type size** (14/12 OpenSans where rule 3 asks 17/16/20, with no
  panel font templates) (TAX-15).

## Findings

### TAX-1. Overview lists metadata, not the actionable state of each process
- **Status (wave, 2026-10-27):** Done. Banking's cells (`te_banking_ov_cell` as it is; the words and figures are `te_tax_ov_word`/`_fig`): Tax Code (version; next change, and on hover what it is, the last change and the snapshot), Draft Reform (None, Blocked, Too soon, Ready, Open), the bill (Month has come, Can pass, Short of support, Debating, Blocked; the share, or the offers waiting while short) and Passed Bills (Awaiting, Held) while either exists, Promises (failing, binding; the next due date) while one is made. The light code: Taxation Law and Tax Level. New generated views `te_tax_view_offers_open`, `_obl_failing`, `_obl_next_due`, `_dr_rebase_count`, and the custom loc `te_tax_ov_next_what`. Words name the state, without a "what needs you" lead-in.
- **Category:** spread-out/redundant, hidden info, style
- **Where:** `gui/journal_entry_widgets/te_tax_overview_widget.gui:211-354` (`te_tax_overview_panel`). Loc:
  `te_tax_ov_title` (`te_tax_l_english.yml:344`), `te_tax_ov_last_change*` (319-321), `te_tax_ov_next_change*`
  (322-325), `te_tax_ov_snapshot*` (339-343), `te_tax_ov_bill_value` (311), `te_tax_ov_obligations_value` (328)
- **Now:** a column of 14-pt "Label: value" rows: "Tax Code, Version 7" / "Last Change: 1839.4" / "Next
  Change: 1840.1" / "Economy Snapshot: 1839.11" / "Bill, Revision 2: From 1840.3, 12 days left" /
  "Passed Bill: From 1840.1, awaiting" / "Promises: 1 binding, 0 pending".
  - Four of the seven rows are bookkeeping: the version, the last change, the snapshot month and the
    revision number.
  - The rows that decide an action carry no status:
    - the Bill row doesn't say whether the bill can pass (committed share against the threshold,
      conditions unmet, offers waiting);
    - the Promises row doesn't flag a failing promise (that shows only in the Promises section as
      `te_tax_obl_st_failing_<n>`, "#R Failing#! 1 of 2 months");
    - the Draft row doesn't flag a blocked draft (moved baseline, TAX-3; `te_tax_sum_due_soon`);
    - "Next Change" names a month but not what happens then (a bill commencing, or which tax expires).
- **Proposed:** Banking's grid (style guide rule 4, `te_banking_ov_cell` in `banking_dashboard_widget.gui:448`),
  two cells to a row, each with an icon, a caption, a word and a figure, and the breakdown on hover:
  - **Code**: word "Version 7"; figure "Next: 1840.1". The hover gives what the next change is, the last
    change, and the snapshot date (moved here from its own row, see TAX-18).
  - **Draft**: word "None" / "Open" / "#R Blocked#!". Figure "From 1840.6 · 3 changes" or "2 changes to
    accept". Blocked is true when `te_tax_show_draft_rebase_sgui`, `te_tax_show_draft_due_soon_sgui` or the
    Traditionalism line fails. The hover is the Introduce button's `IsValidTooltip`.
  - **Bill**: word "Debating" / "#G Ready to pass#!" / "#R Short of support#!" / "#R Month passed#!". Figure
    "38% of >50% · 12 days". Ready is all six `te_tax_show_pass_*_sgui` shown; Short is
    `te_tax_show_pass_support_sgui` not shown. The hover lists the six conditions with Met/Not met (the
    same gates the Conditions table uses) and "Offers waiting: N". N needs one generated view,
    `te_tax_view_offers_open`, counting `te_tax_disp_ig_offer > 0`.
  - **Passed Bills**: word "Awaiting" / "#R Held#!"; figure "From 1840.1" (the second slot as "+1" with
    its own hover).
  - **Promises**: word "2 binding" / "#R 1 failing#!"; figure "Next deadline 1842.1". This needs a
    generated `te_tax_view_obl_failing`, the count of slots with `te_tax_view_o<n>_fails > 0`, beside the
    existing `te_tax_view_obl_binding` and `_pending`.
  - Drop the revision number from the overview (it stays in the Bill Under Debate section) and the
    Economy Snapshot row (TAX-18).
  - Light code: the same grid with two cells, Taxation Law, and Tax Level with "Set by: Wage Tax" as the
    figure (`te_tax_light_overview_rows`).
- **Effort:** large (new overview type, two small generated views, a status gate per process)
- **Confidence:** high on the gap, medium on the exact cell set

### TAX-2. Pass / Revise / Withdraw / Force Through sit below every interest-group card
- **Status (wave, 2026-10-27):** Done. The buttons sit under the Conditions table; `te_tax_bill_summary` is pinned in the Budget tab's `fixed_bottom` while a bill is under debate and no draft is open.
- **Category:** spread-out/redundant
- **Where:** `te_tax_politics_widget.gui:501-580` (Conditions for Passage), `:598` (IG card datamodel),
  `:605-657` (the button row, Force Through, Move to Next Month); Budget tab `gui/budget_panel.gui:1735-1762`
  (`fixed_bottom` holds only `te_tax_draft_summary`)
- **Now:** inside Bill Under Debate the order is: the bar, the six condition rows, two notes, then one card
  per interest group, then the Pass row. Each card has a header, six reason rows, an offer line and a
  revenue line, so eight groups add about 60 lines. A player who sees "Met" on every condition must
  scroll past all of them to reach Pass. On the Budget tab, a draft gets a pinned footer with Introduce
  ("so Review, Discard and Introduce stay on screen", budget_panel.gui:1736), but a bill under debate
  gets nothing.
- **Proposed:**
  1. Move the Pass | Revise from Draft | Withdraw row, Force Through and Move to Next Month to directly
     under the Conditions table, before the "Interest Groups" subheader. A group's Accept stays on its card.
  2. Add a `te_tax_bill_summary` type to the Budget tab's `fixed_bottom`, shown while
     `te_tax_show_bill_sgui` holds and `te_tax_show_draft_sgui` does not (otherwise the draft summary stays).
     It holds one row, "Committed: 38% / >50% · 12 days left" with the conditions' hover, and Pass /
     Force Through / Withdraw. Both buttons already run from `GetPlayer` handlers, so they work in
     `fixed_bottom`.
- **Effort:** medium
- **Confidence:** high

### TAX-3. "Changed Since Drafted" and its Accept buttons are only in the collapsed Review
- **Status (wave, 2026-10-27):** Done, the second option: Changed Since Drafted moved from the review to the top of the workbench, open while it applies, and the draft summary counts the changes to accept (red). The player guide's sentence now says where. No mark in the instrument rows: the block at the top carries the Accepts.
- **Category:** hidden info
- **Where:** `te_tax_review_widget.gui:231-380` (`te_tax_review_section`, collapsed by `te_tax_review_open`;
  rebase block at 262-380). Loc `te_tax_tt_draft_baseline` (`te_tax_l_english.yml:571`),
  `te_tax_rv_rebase_*` (482-490). Draft summary `te_tax_workbench_widget.gui:1220-1318`. Player guide
  `docs/player_guide/05-tax-code.md:208-210`.
- **Now:** when a passed bill or an outside change moves a provision the draft changed, Introduce and
  Revise grey out with "No provision the draft changes has been altered since the draft changed it.
  Accept each such change first." That tooltip doesn't say where to accept. The only Accept buttons are
  in Review the Draft, which starts collapsed. Neither the pinned draft summary nor the workbench row
  shows anything. The player guide says "the draft's row is marked Changed Since Drafted", which the GUI
  doesn't do.
- **Proposed:** while `te_tax_show_draft_rebase_sgui` holds:
  - Mark the workbench row: a red "!" in the row's Change cell, its hover `te_tax_rv_rebase_<key>`, plus
    an Accept button (the same `te_tax_cmd_draft_rebase_sgui` op).
  - Or move the "Changed Since Drafted" block out of the Review into the top of the workbench panel,
    always open while it applies (rule 7: content for one state is a subsection shown in that state).
  - In the draft summary, add a red row "Changes to accept: N", with the count from the seven
    `te_tax_view_dr_*_rebase` views.

  The loc-only stopgap is in Quick fixes (`te_tax_tt_draft_baseline` names where to accept). If the
  rows get marked, the player guide sentence becomes true; otherwise it needs correcting.
- **Effort:** medium
- **Confidence:** high

### TAX-4. Revenue: no figure in the summary, and the estimate is written as sentences
- **Status (wave, 2026-10-27):** Done. The summary's Revenue row (an `Add_CFixedPoint` sum of the four lines' changes; a range while Poll is shared, "in part" when a changed line has no base, "Not estimated" before the first snapshot) and the review's estimate as a table (`te_tax_estimate_row`).
- **Category:** spread-out/redundant, list (table as text)
- **Where:** `te_tax_review_widget.gui:842-928` (Revenue Estimate, the last block of the collapsed
  Review). Loc `te_tax_est_income`/`_dividends`/`_poll`/`_poll_range`/`_consumption` (`te_tax_l_english.yml:65-75`).
  Draft summary `te_tax_workbench_widget.gui:1220-1318`.
- **Now:** "About ¤12.3K a week with this bill, against ¤10.1K under existing law: ¤+2.2K", one wrapped
  sentence per Budget line, in a 312-wide cell, at the end of a section that starts collapsed. The
  pinned draft summary shows "Changes: Taxes 2, goods 0, relief 1", the bill class and Takes Effect,
  but not what the reform does to the budget.
- **Proposed:**
  1. Add a draft-summary row "Revenue: ¤+2.2K a week" (green/red by sign). It is the sum of the four
     `Multiply_CFixedPoint( <Budget getter>, te_tax_view_est_<line>_delta )` terms already in the loc,
     and the hover is the four per-line rows. While `te_tax_view_est_poll_shared` = 1, show the `_lo`
     to `_hi` range. With no base or no snapshot, show "Not estimated", its hover `te_tax_est_none` or
     `te_tax_est_nobase`.
  2. In the Review, make the estimate a table with four fixed-width columns (Budget line | Existing law
     | With bill | Change, coloured) and one row per line. The poll range takes "¤x–¤y" in each cell.
     The "Static estimate at today's economy…" line becomes the table head's hover.
- **Effort:** medium
- **Confidence:** medium (the sum needs an `Add_CFixedPoint` chain in GUI or a summed view value; both have
  precedents in this mod)

### TAX-5. The committed share is shown twice, one above the other
- **Status (wave, 2026-10-27):** Done. The bar is the first condition row's middle cell, "38% / >50%" beside it; the separate bar row and `te_tax_pol_bar_label` are gone.
- **Category:** spread-out/redundant
- **Where:** `te_tax_politics_widget.gui:383-495` (bar row: `te_tax_pol_bar_label` "Committed", value
  `te_tax_pol_bar_value` "38% / 50%") and `:504-516` (first condition row: `te_tax_pol_support` "Committed
  Clout", `te_tax_pol_support_value` "38%, more than 50% needed", Met/Not met)
- **Now:** two adjacent rows give the same two figures in two forms.
- **Proposed:** make the bar the first condition row. Its label is "Committed Clout" (with
  `te_tax_pol_support_tt`), then the 200-wide bar, the value "38% / >50%", and the Met/Not met mark. The
  bar keeps `te_tax_pol_bar_tt` on its own widget. Delete the separate bar row and
  `te_tax_pol_bar_label`. The condition row's cells (150 + 246 + 68) take the bar in the 246 cell, as
  bar 170 plus value 72.
- **Effort:** medium (GUI only)
- **Confidence:** high

### TAX-6. Interest-group cards: full cards for marginal groups, zero rows, no icon
- **Status (wave, 2026-10-27):** Done, (a) to (d): vanilla's `ig_button` before the name; reasons of 0 hidden; a committed or marginal group shows its line alone, and every group's score hover is the six-reason breakdown, so (d) folds the rows only for the groups no longer to be moved.
- **Category:** spread-out/redundant, style
- **Where:** `te_tax_politics_widget.gui:108-266` (`te_tax_ig_card`). Reason rows `:158-216`; stance `:136-145`
- **Now:** every group with a stance draws a header and six reason rows, Marginal ones included ("too
  little clout to count either way", `te_tax_ig_stance_tt`), and a reason of 0 still prints "+0". There's
  no interest-group icon (rule 4: icons first). The file comment says "the cards' tooltips are static
  text", but gotcha #24 lets a datamodel item's tooltip read the item's own context. `te_tax_ig_trust_tt`,
  on these cards, already reads `GetPlayer.MakeScope.ScriptValue(...)`, and `InterestGroup` is the item's
  context.
- **Proposed:**
  - (a) a Marginal group (`te_tax_disp_ig_stance` = 5) draws only its header line;
  - (b) gate each reason row on its value ≠ 0;
  - (c) put vanilla's interest-group icon (the politics panel's IG icon type) left of the name, which also
    makes the card clickable to the group;
  - (d) optionally, for Committed groups, fold the six reasons into the score's hover as a breakdown
    ("Cost to Members −12 / Views on Taxation +4 …", rule 3).

  (a) and (b) alone remove most of the length. (d) trades against rule 5 ("the parts of a total are
  bars… one row per component"), so it's the owner's call: keep the rows for the groups you still need
  to move, fold them for the rest.
- **Effort:** medium
- **Confidence:** high for (a)-(c), medium for (d)

### TAX-7. Live Bill section: teaching notes and a disclaimer repeated on every card
- **Status (wave, 2026-10-27):** Done. `te_tax_pol_groups_note` removed (its thresholds are on the stance hover); the estimate note stays.
- **Category:** over-explaining
- **Where:** `te_tax_politics_widget.gui:583-592` (`te_tax_pol_groups_note`, `te_tax_pol_est_note`); card
  revenue line `:240-252`. Loc `te_tax_pol_groups_note` (`te_tax_l_english.yml:414`), `te_tax_ig_offer_est_*`
  (163-171)
- **Now:** two `#lore` notes sit in the live section. "Each group weighs the bill every month. One that
  scores 20 or more commits…, one at −40 or below draws a red line. A revision releases every commitment."
  This is in How it works (`te_tax_how_passage`), in `te_tax_ov_bill_tt` and in `te_tax_tt_cmd_revise`.
  The second note is the estimate disclaimer. Then every offer's revenue line ends ", a static estimate
  at today's economy", which the note above already says once (rule 6: say it once above the rows).
- **Proposed:** drop the suffix from the seven offer lines (Quick fixes). Move the thresholds into the
  stance hover (Quick fixes, `te_tax_ig_stance_tt`), then delete `te_tax_pol_groups_note` from the GUI (a
  medium GUI change). Keep `te_tax_pol_est_note`, the one line above the rows;
  `test_tax_code_estimates.py:399-405` pins its markup.
- **Effort:** quick (loc) + medium (remove one note)
- **Confidence:** high

### TAX-8. The offer's hover is a six-sentence paragraph that duplicates How it works
- **Status (wave, 2026-10-27):** Done in #1202 (loc); no GUI part was proposed.
- **Category:** over-explaining
- **Where:** `te_tax_politics_widget.gui:232-233` (offer line tooltip). Loc `te_tax_ig_offer_tt` (`te_tax_l_english.yml:175`)
  vs `te_tax_how_passage_offers` (130)
- **Now:** "What the group asks for its support. A change to the bill only softens what the bill raises or
  adds; a group the bill hurts some other way asks for a promise. A persuadable group commits if you
  accept; an opposed one, or one at its red line, only opposes the bill less. Accepting any offer makes a
  new revision… A promise binds only if the bill passes." The "commits / opposes less" sentence repeats
  the offer line itself (`te_tax_ig_offer_commits`/`_lifts`/`_less`, chosen by the group's stance). The
  "softens / promise" sentence is in `te_tax_how_passage_offers`.
- **Proposed:** see Quick fixes. It keeps the consequence the player must weigh (a concession can cost
  another group's commitment) and the anti-farming limits.
- **Effort:** quick
- **Confidence:** high

### TAX-9. Command tooltips restate the modifier lines the engine prints under them
- **Status (wave, 2026-10-27):** Done in #1202 (loc); in the wave the passed-bill line's hover (`te_tax_rv_passed_tt`) words the supersession rule for the bill under review only.
- **Category:** over-explaining, style (prefer engine-rendered modifiers)
- **Where:** `te_tax_tt_cmd_pass` (`te_tax_l_english.yml:559`; effect `te_tax_bill_effects.txt:561-573`,
  whose `te_tax_gen_oppose_approval` adds visible `ig_approval_effect` modifiers);
  `te_tax_tt_cmd_force_through` (554; `te_tax_offer_effects.txt:206-246`, two visible `add_modifier`s);
  `te_tax_tt_cmd_obl_renegotiate` (556; `te_tax_obligation_effects.txt:519-533`, a visible
  `te_tax_obl_renegotiated_modifier`); `te_tax_ov_package_awaiting_tt` (333)
- **Now:**
  - Pass says "Interest groups that opposed it disapprove for six months." above the per-group approval
    lines the engine prints. The effect's comment says it keeps those lines on purpose ("keeps the
    per-group disapproval lines in the Pass button's tooltip").
  - Force Through says "groups that opposed it disapprove as they would. The override's own cost and
    consequences follow", then the two `forced_law_through_event*` modifiers render.
  - Renegotiate says "it costs that group's trust" twice and "the group disapproves, though less than
    for a broken promise" above the −2 approval modifier.
  - The supersession rule ("A bill passed after it that takes effect no later replaces whatever the two
    change in common") is in four places: `te_tax_ov_package_awaiting_tt`, `te_tax_rv_passed_tt`,
    `te_tax_tt_cmd_pass` and `te_tax_how_commencement`.
- **Proposed:** keep only what script writes silently: Judicial Independence −10 (`te_jud_spend` is a
  bare `change_variable`), trust −1, the scheduling rule where it acts. Values are in Quick fixes. When
  the button is greyed, its outer `if = { limit = { te_tax_can_* } }` renders nothing, so no text is lost
  in that state either.
- **Effort:** quick
- **Confidence:** high (Pass, Force), high (Renegotiate)

### TAX-10. Click instructions repeated on every row's hover, under an intro that already says them
- **Status (wave, 2026-10-27):** Done in #1202 (loc): the intros carry the clicks, the Law head's hover the starting rate.
- **Category:** over-explaining (rule 6: what is true of every row is said once, above the rows)
- **Where:** workbench intro `te_tax_workbench_widget.gui:652` (`te_tax_wb_intro`, `te_tax_l_english.yml:685`)
  and the seven row hovers `te_tax_wb_row_{wage,div,land,head,cons,agrel,regrel}_tt` (710-716). Light:
  `te_tax_light_widget.gui:153` (`te_tax_lt_intro`, 218) and `te_tax_lt_row_*_tt` (231-235).
- **Now:** the intro says "Click − or + for one step, shift-click for zero or the highest rate, right-click
  to leave the tax as it is". Each row's label hover appends "Click − or + to move it 1%, shift-click to
  set it to zero or its highest rate, right-click either to leave it as existing law has it". In the
  light panel, `te_tax_lt_intro` doesn't give the clicks at all, while all five rows do.
- **Proposed:** the intros carry the clicks once; each row's hover keeps the tax's own description and its
  step size (the only row-specific fact). For regional relief, the hover keeps that right-click also
  restores the named states. The intro's first sentence ("Each tax starts at the rate existing law will
  have…") is the Law column head's hover, `te_tax_wb_col_law_tt`. Values in Quick fixes.
- **Effort:** quick
- **Confidence:** high

### TAX-11. Greyed vanilla Budget controls don't say why
- **Status (wave, 2026-10-27):** Done. A greyed control's tooltip starts with the code's line (`te_tax_tt_native_locked_level`/`_goods`/`_tariff`): the five tax levels, the "+" and the 14 tariff items in `budget_panel.gui`, the goods panel's toggle (`goods_panel.gui`, marked hunk) and the four right-click Tax/Untax items (`right_click_menu.gui`). The add-consumption-tax menu's items are unchanged: the greyed "+" never opens it. `test_tax_code_layout.TabStripTest` now counts the gates in `enabled` and in tooltips apart.
- **Category:** hidden info
- **Where:** `gui/budget_panel.gui:2225-2380` (tax-level buttons: `enabled` ANDs `te_tax_native_controls_sgui`;
  tooltip stays `[GetPlayer.GetTaxLevelDescVeryLow]` etc.), `:403-408` (consumption-tax "+": tooltip
  `TAX_GOODS`), `:1915-2200` (per-good tariff `set_level_bar` items: vanilla's desc). Same gate in
  `gui/add_consumption_tax_menu.gui:18`, `gui/goods_panel.gui:1674`, `gui/right_click_menu.gui:13187-13366`.
- **Now:** under the code these buttons are greyed, but the hover shows vanilla's description, so the
  player can't tell that the Tax Code tab owns them. The Market panel's All Goods rows
  (`te_bulk_tariff_widgets.gui`) do say why, through their scripted GUI's refusal line. The light code's
  reason is only in How it works (`te_tax_lt_how_native`).
- **Proposed:** a loc key `te_tax_tt_native_locked`, "Set by the [concept_tax_code]: change it on the Tax
  Code tab." (light: "Set by your tax rates on the Tax Code tab."). Put it first in each gated tooltip,
  e.g. `tooltip = "[Concatenate( SelectLocalization( GetScriptedGui('te_tax_native_controls_sgui').IsValid(…),
  'te_tax_empty', 'te_tax_tt_native_locked_br' ), GetPlayer.GetTaxLevelDescVeryLow )]"`. Do budget_panel.gui
  first. `goods_panel.gui` and `right_click_menu.gui` are pinned full-file overrides
  (`test_tax_code_bypass.py`), so a change there must update that test's expectations.
- **Effort:** medium
- **Confidence:** high

### TAX-12. Held data never drawn: taxed goods, enacted relief states, a passed bill's relief
- **Status (wave, 2026-10-27):** Done. (a) The enacted goods as icon rows by category (generated `te_tax_en_goods_icons`), and each passed bill's taxed and exempted goods (`te_tax_pk_goods_icons_<s>`, views `te_tax_view_p<s>_g_<good>`); (b) the enacted relief states under Regional Relief; (c) `te_tax_view_p<s>_<relief>_on`/`_pct`, relief lines and states in Passed Bills and in the review's relief timelines.
- **Category:** hidden info, list
- **Where:** Enacted Code `te_tax_overview_widget.gui:449-476`; Passed Bills `te_tax_politics_widget.gui:674-920`
  (slot rows cover wage, div, land, head, cons, goods, customs only); loc `te_tax_en_goods_value` (40),
  `te_tax_en_regrel_tt` (47), `te_tax_pk_a_goods` (355)
- **Now:**
  - **Taxed goods:** the Enacted Code gives only a count, "Taxed Goods: 12", and its hover doesn't list
    them. In the tab, the goods are named only in the draft's Goods Catalog (collapsed, and only with a
    draft open). `te_tax_view_en_g_<good>` exists for all 39 goods (`te_tax_generated_values.txt:481…`)
    and no GUI reads it. A passed bill reads "3 goods taxed or exempted from 1840.4", without saying which.
  - **Enacted relief states:** "Regional Relief: 25%". Its hover says "the named states, at most
    three" but no row lists them, though the list `te_tax_en_relief_states` exists. The workbench lists
    the draft's in exactly this way (`te_tax_workbench_widget.gui:922-937`).
  - **A passed bill's relief:** a bill that changes relief shows nothing about it in Passed Bills, the
    overview or the Review's Existing Law line. The slots store `te_tax_p<s>_agrel`, `_regrel` and
    `te_tax_p<s>_relief_states`, but no `te_tax_view_p<s>_agrel/regrel` exists.
- **Proposed:**
  - (a) Under the Taxed Goods row, an icon row of the enacted goods. `gen_tax_code.py` emits 39 goods
    icons, each `visible` on `te_tax_view_en_g_<good>` = 1, with the good's name on hover. On the
    Budget host, vanilla's `BudgetPanel.AccessTaxedGoods` datamodel (`budget_panel.gui:378-381`) would do
    the same, but the generated row works in both hosts. Do the same per passed bill, from its
    `te_tax_p<s>_g_*` fields.
  - (b) Under Regional Relief, a datamodel over `GetPlayer.MakeScope.GetList('te_tax_en_relief_states')`,
    with `datacontext = "[Scope.GetState]"` and `te_tax_wb_relief_state_name`, as the draft's list.
  - (c) Generate `te_tax_view_p<s>_agrel_pct`/`_regrel_pct`/`_on`. Add Agricultural Relief and Regional
    Relief lines to each Passed Bill slot and to the Review's relief Existing Law timeline (with a
    `te_tax_p<s>_relief_states` list under regional relief).
- **Effort:** medium (generator for a and c; GUI for b)
- **Confidence:** high

### TAX-13. Goods Catalog is 39 ungrouped rows in key order, with no icons
- **Status (wave, 2026-10-27):** Done. Grouped by the customs catalog's four categories, staples in `staple_order()`, each good's icon in its row; one Goods Catalog toggle kept.
- **Category:** list, style
- **Where:** generated `te_tax_generated_rows.gui:16-719` (`te_tax_wb_goods_rows`) from
  `scripts/generators/gen_tax_code.py` (`consumption_catalog()`); compare the customs editor's grouping,
  `te_tax_workbench_widget.gui:1036-1081`
- **Now:** aeroplanes, automobiles, clippers, clothes… in alphabetical key order, as text only. The
  interest groups weigh staples most (`te_tax_rv_goods_benefit`, `te_tax_ig_mat_tt`), and the customs
  editor beside it groups the same goods as Staples / Industrial Goods / Luxuries / Military Goods.
- **Proposed:** have the generator group the catalog by the same four categories (the customs catalog's
  `te_tax_wb_cu_cat_*` headings), staples first in `staple_order()`. Put the good's icon in a 24-px cell
  before the name (the name cell 170 → 146). Collapse each category separately, or keep the one
  "Goods Catalog" toggle.
- **Effort:** medium (generator)
- **Confidence:** high

### TAX-14. Section order puts the long editing workbench above the bill under debate
- **Status (wave, 2026-10-27):** Done (owner, 2026-10-27): Bill Under Debate, Passed Bills, Promises, Enacted Code, Draft Reform, Review; `STATUS` updated.
- **Category:** spread-out/redundant
- **Where:** `te_tax_layout_widget.gui:41-57` (`te_tax_status_sections`); pinned by `test_tax_code_layout.py:67-68,362`
  (`STATUS` list)
- **Now:** the order is Enacted Code → Draft Reform (five accordions open by default) → Review → Bill Under
  Debate → Passed Bills → Promises. While a revision is drafted, the bill's debate, conditions and
  offers sit below the whole workbench, and a held bill or failing promise sits further down still.
- **Proposed:** the monitoring sections first, the editor last: Bill Under Debate → Passed Bills →
  Promises → Enacted Code → Draft Reform → Review. Each monitoring section hides itself when empty, so a
  quiet code still opens on the Enacted Code. Update `STATUS` in the test.
- **Effort:** medium
- **Confidence:** medium (reorders the pinned design order; owner sign-off)

### TAX-15. The whole UI is set a step below the house type ladder
- **Status (wave, 2026-10-27):** Done. `te_tax_fontsize_row` (17), `_heading` (20), `_overview` (16) at the head of the overview file, every textbox and labelled button through them, the cells re-budgeted; `test_tax_code_layout.WidthBudgetTest` holds every fixed cell to its longest text. "Revise from Draft" became "Revise Bill", as the summary's button already read, to fit.
- **Category:** style
- **Where:** all `te_tax_*_widget.gui`: 60 × `fontsize_medium` (14, OpenSans) for rows, values, notes
  and live text; 8 × `fontsize_small` (12) for the column heads ("Law", "Draft", "Change", "Range", "Rate",
  "Step", "Imports", "Exports"); `fontsize_large` only for subheadings. No panel font templates.
- **Now:** rule 3 (Steam feedback 2026-10-13, owner 2026-10-17) asks for rows, values, buttons and notes
  at 17, subheadings at 20 and the overview at 16, with "nothing a player reads to decide something
  smaller". No comment in the tax files records an exception.
- **Proposed:** add `te_tax_fontsize_row` (17), `_heading` (20), `_overview` (16) and `_note` templates at
  the head of `te_tax_overview_widget.gui`, and route every textbox through them. Re-budget the cells,
  which were sized at "7 px a character" for the medium font (`te_tax_value_row` 190/282,
  `te_tax_instrument_row` 146/70/70/80, the IG card 216/64/120/72). Two-up overview cells (TAX-1) and
  shorter labels (TAX-10) recover room. Consider a width test like `test_banking_layout.py`'s
  `WidthBudgetTest`.
- **Effort:** large (every row; width re-budget)
- **Confidence:** high on the deviation

### TAX-16. The same thing named differently across panel, tooltip and button
- **Status (wave, 2026-10-27):** Done. "Drop" in the held line (and the test), "takes effect" in every tooltip that said commence, "Trust" on the card and in the guide, "Dates" for the workbench's Commencement group, "agricultural relief" in the offers.
- **Category:** style
- **Where / Now:**
  - Button "Drop" (`te_tax_pk_release`, `te_tax_l_english.yml:391`), but the passed bill's line says
    "#R held: conflict, will not commence; release it#!" in ten keys (`te_tax_pk_[ab]_<key>_conflict`,
    347…387). `test_tax_code_sguis.py:526` pins "release it", so it isn't a Quick fix: change the test to
    "drop it".
  - "Takes effect" vs "commence": labels say "Takes Effect" (`te_tax_pol_due`, `te_tax_sum_due`,
    `te_tax_wb_due`), but the subsection over that row is "Commencement" (`te_tax_wb_sub_dates`), and
    tooltips mix "commences", "commencement month" and "waiting to commence" (`te_tax_tt_cmd_pass`,
    `_introduce`, `_package_reschedule`, `te_tax_tt_pass_slot`, `te_tax_tt_package_held`,
    `te_tax_tt_pass_due`). Pick "takes effect" as the verb and link `[concept_tax_commencement]` where
    the term is needed.
  - The card reason "Kept Promises" (`te_tax_ig_trust`) is the group's *trust*, which broken and
    renegotiated promises also lower. Its own hover, How it works and `te_tax_how_promises_outcomes` all
    call it trust. Rename it "Trust", and update `docs/player_guide/05-tax-code.md:287,371`, which quote
    the label.
  - `concept_tax_code_desc` says "the wage, dividend, rural and head taxes", but the tax is "Rural
    Assessment" everywhere else (Quick fixes).
  - Agricultural relief is "Agricultural Relief" in the panel, "Agricultural Tax Relief 25%" as a
    modifier and "agricultural wage relief" in offers (`te_tax_offer_agrel`); low priority.
- **Effort:** quick (loc) for most; test/guide edits for the first and third
- **Confidence:** high

### TAX-17. Review: static mechanics lines in the live entries
- **Status (wave, 2026-10-27):** Done. `te_tax_rv_unchanged` dropped; who benefits (and the goods' forgone tax) is on the provision's name; the agricultural and regional Forgoes lines stay. Tests updated.
- **Category:** over-explaining
- **Where:** `te_tax_review_widget.gui:257` (`te_tax_rv_unchanged`, "Present collections remain unchanged
  until commencement.", the first line of every review); `:638-655`, `:726-744`, `:823-841` ("Benefits" /
  "Forgoes" lines). Loc `te_tax_rv_goods_benefit` (467), `te_tax_rv_goods_forgoes` (469),
  `te_tax_rv_agrel_benefit` (443), `te_tax_rv_regrel_benefit` (492)
- **Now:** each changed relief and the goods block get two lines of fixed explanation. "Workers in
  agricultural buildings, on their wage tax only." "Pops who buy a good the bill stops taxing pay less…
  Staples weigh most…". These are the same every time, and the agrel one restates `te_tax_en_agrel_tt`.
  Only the "Forgoes" lines for agricultural and regional relief carry figures.
- **Proposed:** move the fixed "Benefits" text and `te_tax_rv_goods_forgoes` onto the hover of the
  provision's name (the `#title` line), and keep the "Forgoes" lines that carry numbers. Drop
  `te_tax_rv_unchanged`: How it works and the Review's own "With This Bill" hover say a draft changes
  nothing until it takes effect. Pinned: `test_tax_code_sguis.py:537-538` (`te_tax_rv_unchanged` text
  and markup) and `test_tax_code_goods_relief.py:595-600` (the six keys exist; the review names
  beneficiaries, the capability-ledger wording, which a hover still satisfies).
- **Effort:** medium (GUI + test updates)
- **Confidence:** medium

### TAX-18. The overview's Economy Snapshot row, and its developer-facing hover
- **Status (wave, 2026-10-27):** Done. The row is gone; the Code cell's hover dates the snapshot with net fixed and total income and GDP, and the unclassified aggregate is shown nowhere. Test updated.
- **Category:** over-explaining, other
- **Where:** `te_tax_overview_widget.gui:270-280`; loc `te_tax_ov_snapshot_value_tt` (`te_tax_l_english.yml:343`)
- **Now:** an always-shown overview row for the month the estimates were measured against. Its hover lists
  "Domestic tax aggregate (unclassified)" and ends "…what it counts is not established, so the estimates
  do not use it": an engine-research note in player UI, showing a figure the player is told not to use.
- **Proposed:** remove the row from the overview. The Revenue Estimate and the offers note already date
  the snapshot (`te_tax_est_static`, `te_tax_pol_est_note`), and TAX-1's Code cell can carry it on hover.
  Drop the aggregate line and its caveat from the hover, keeping net fixed income, net total income and
  GDP. Pinned: `test_tax_code_estimates.py` (`test_the_overview_dates_the_snapshot_and_labels_the_aggregate`
  wants some key to read `te_tax_view_snap_tax_income` and the overview to name `te_tax_ov_snapshot`),
  so update the test with it.
- **Effort:** medium (GUI + test)
- **Confidence:** high

### TAX-19. The estimate's assumptions are written out twice; make them one concept
- **Status (wave, 2026-10-27):** Done. `concept_tax_static_estimate` holds the assumptions once; the header, the offers note and their hovers link it. Test moved to the concept.
- **Category:** over-explaining
- **Where:** `te_tax_est_header_tt` (`te_tax_l_english.yml:70`, three paragraphs) and `te_tax_pol_est_tt` (411)
  share a pinned sentence (`test_tax_code_estimates.py:406-411`)
- **Now:** two long hovers restate the static-estimate assumptions (receipts scaled by rate, pops and prices
  held, pass-through, the Poll split, a lag) in slightly different words.
- **Proposed:** a concept `concept_tax_static_estimate` ("Static Estimate"; desc = the assumptions, once).
  The Revenue Estimate header and the offers note link it ("[concept_tax_static_estimate] at today's
  economy, against the snapshot of 1839.11"). Each hover keeps only what is specific to it (for offers:
  "one step of the tax"). Move the pinned sentence's assertion to the concept's `_desc`.
- **Effort:** medium (new concept + test update)
- **Confidence:** medium

### TAX-20. The Enacted Code doesn't show since when a rate holds
- **Status (wave, 2026-10-27):** Done. "In force since" on each rate's hover.
- **Category:** hidden info
- **Where:** `te_tax_overview_widget.gui:142-177` (`te_tax_rate_row`: name, rate, expiry), `:383-447`; views
  `te_tax_view_en_<key>_since_y/_mo` (generated, unused by any GUI); player guide `05-tax-code.md:178-179`
  ("Enacted Code lists every rate in force, when it came into force…")
- **Now:** no "since" anywhere in the panel, although the views exist and the player guide says it's shown.
- **Proposed:** put "In force since #v Y.M#!" on the rate cell's hover (a new key per tax, reading the
  `_since_y`/`_since_mo` views) and leave the row's layout alone. Or correct the guide.
- **Effort:** medium (five small loc keys + `tooltip` on the rate cell)
- **Confidence:** high

### TAX-21. History rows say what kind of thing happened, not what changed
- **Status (wave, 2026-10-27):** Done, the proposal's step: a row that changed the code shows the version it made, and a kept, broken or renegotiated promise names its group (`te_tax_history_push_promise` records it in `_inst`). Summaries of what each entry changed would need more fields per ring entry and are not built.
- **Category:** hidden info
- **Where:** `te_tax_overview_widget.gui:487-589` (eight hand-unrolled rows); `te_tax_hist_kind_*`
  (`te_tax_l_english.yml:87-117`); ring fields `te_tax_h<n>_kind/_inst/_slot/_version` (schema doc)
- **Now:** "A bill passed." "A passed bill took effect." "A promise to an interest group was kept." The
  rows don't say which taxes or which group. The ring stores `_version` and `_slot`, but no row prints
  either.
- **Proposed:** low priority (a collapsed past list). Cheapest step: print the version ("→ v8") and, for
  promise outcomes, record the group in `_inst` and name it through the custom loc. A full summary per
  entry would mean storing more per ring entry (large).
- **Effort:** medium (version, group) / large (summaries)
- **Confidence:** medium

### TAX-22. A promise's "what" cell can elide
- **Status (wave, 2026-10-27):** Done. The promise's what and state wrap; the group cell is 172.
- **Category:** hidden info (elided text)
- **Where:** `te_tax_politics_widget.gui:294-305` (`obl_what`, 308 wide, `elide = right`, fontsize_medium);
  loc `te_tax_obl_mode_maintain` + `te_tax_obl_what_wages_very_high`
- **Now:** "Maintain: Military Wages at Very High or lower" runs to about 46 characters, roughly 320 px at
  the 7 px a character the file budgets with, which ends in "…". "Maintain: Fixed income above fixed
  expenses" (43) is borderline.
- **Proposed:** `multiline = yes` on the cell (rule 3: let a long value wrap), or shorten the military
  wages wording to "Military Wages ≤ Very High".
- **Effort:** quick (GUI)
- **Confidence:** medium (width estimated, not measured)

### TAX-23. Light code: one sentence said three times; reaction text on every step button
- **Status (wave, 2026-10-27):** Done. `te_tax_lt_tt_react_<key>` (generator) reads "Paid most by …"; How the Light Tax Code Works keeps the one fade wording.
- **Category:** over-explaining, style
- **Where:** `te_tax_lt_intro` (218), `te_tax_lt_ov_title_tt` (230), `je_tax_code_reason_light` (12),
  `te_tax_lt_how_rates` (212); generated `te_tax_lt_tt_react_<key>` (`te_tax_generated_l_english.yml:386-390`,
  from `gen_tax_code.py`), rendered by `te_tax_light_cmd_step` on both buttons of all five rows; compare
  `te_tax_lt_how_groups` (207)
- **Now:** "Within that range you set each rate… a change applies at once" appears in the intro, the title
  hover, the JE reason and How it works. Every − and + hover ends "Each interest group reacts by how much
  of this tax its members pay and by its views on taxation; a reaction that pleases a group counts half.
  Reactions fade over about six months." How it works says they "fade by about a third each month", the
  same fact in two forms.
- **Proposed:** the intro becomes the click line (Quick fixes). Trim `te_tax_lt_tt_react_<key>` in the
  generator to "Paid most by X, Y, Z." (the decision-relevant part), and keep the mechanics in How it
  works with one fade wording. No test pins the generated text (`test_tax_code_light.py:701` only
  names the key family).
- **Effort:** quick (loc) + quick (generator string)
- **Confidence:** high

### TAX-24. The interest-group view modifiers explain both codes in one description
- **Status (wave, 2026-10-27):** Done, the one-sentence form: a modifier's description reads no data, so the `SelectLocalization` variant was not used.
- **Category:** style
- **Where:** `te_tax_ig_view_<ig>_{m1,m2,p1,p2}_desc` (`te_tax_generated_l_english.yml:323-330…`, generated)
- **Now:** "Under the legislated tax code: this group's stance on the taxation law the enacted code comes
  closest to… Under the light tax code: how far below the tax level the taxes its members pay are set."
  This shows in the vanilla IG approval breakdown, where a player only ever has one of the two codes.
- **Proposed:** in `gen_tax_code.py`, emit the desc as a `SelectLocalization` on `te_tax_show_light_sgui`
  between two keys, if modifier descs evaluate data functions in that tooltip. If not, one sentence that
  fits both: "How this group judges the tax code: the taxation law it comes closest to, or how far below
  the tax level its members' taxes are set." `test_tax_code_generated.py`, `_light.py` and `_offers.py` reference the
  keys but don't pin the desc text.
- **Effort:** quick-medium (generator)
- **Confidence:** medium

### TAX-25. Force Through is drawn, greyed, when the bill can pass on its own
- **Status (wave, 2026-10-27):** Done. Force Through shows only while committed clout is short (also in the bill footer).
- **Category:** other
- **Where:** `te_tax_politics_widget.gui:637-649`
- **Now:** a full-width Force Through button sits under Pass whenever a bill is open. With a majority
  committed it's greyed with "The bill lacks the committed support to pass on its own" failing, which
  is noise right under an enabled Pass.
- **Proposed:** `visible = "[Not( GetScriptedGui('te_tax_show_pass_support_sgui').IsShown(…) )]"`, the form
  Move to Next Month already uses. Its hover still lists the other conditions when it shows.
- **Effort:** quick (GUI)
- **Confidence:** medium (the owner may want the option always visible)

### TAX-26. Customs levels are words where vanilla uses tariff icons
- **Status (wave, 2026-10-27):** Done. Vanilla's tariff icons per level (generator), the word on hover; the level cells shrank from 88 to 30.
- **Category:** style (rule 4)
- **Where:** generated `te_tax_cu_level_text` cells (`te_tax_generated_rows.gui:1179…`), loc `te_tax_cu_lv_*` (28-34)
- **Now:** "Low tariff", "High subsidy" in 88-px text cells. The Market panel and the vanilla `set_level_bar`
  show the same seven levels as `gfx/interface/icons/trade_icons/*_tariffs.dds` / `*_subventions.dds`.
- **Proposed:** in the generator, an icon per level (the same visible gates) with the word on hover,
  matching the Market panel. It also frees width for TAX-15's larger type.
- **Effort:** medium (generator)
- **Confidence:** medium

## Applied in this PR

30 loc-only edits from this slice were applied (text rewritten in place, keys unchanged). The pre-edit text is in git history; the finding each serves is named above. Keys:

`concept_tax_code_desc`, `te_tax_ig_offer_est_cons`, `te_tax_ig_offer_est_div`, `te_tax_ig_offer_est_head`, `te_tax_ig_offer_est_head_shared`, `te_tax_ig_offer_est_land`, `te_tax_ig_offer_est_land_shared`, `te_tax_ig_offer_est_wage`, `te_tax_ig_offer_tt`, `te_tax_ig_stance_tt`, `te_tax_lt_intro`, `te_tax_lt_row_cons_tt`, `te_tax_lt_row_div_tt`, `te_tax_lt_row_head_tt`, `te_tax_lt_row_land_tt`, `te_tax_lt_row_wage_tt`, `te_tax_ov_package_awaiting_tt`, `te_tax_tt_cmd_force_through`, `te_tax_tt_cmd_obl_renegotiate`, `te_tax_tt_cmd_pass`, `te_tax_tt_draft_baseline`, `te_tax_wb_intro`, `te_tax_wb_none`, `te_tax_wb_row_agrel_tt`, `te_tax_wb_row_cons_tt`, `te_tax_wb_row_div_tt`, `te_tax_wb_row_head_tt`, `te_tax_wb_row_land_tt`, `te_tax_wb_row_regrel_tt`, `te_tax_wb_row_wage_tt`
