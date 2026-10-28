# Rows that drifted out of their panels, and doubled flags: play-test list

The play-test of 2026-10-28 found controls running out of the UN panel, two flags beside every country name in several
tables, and the trade-partner legends running past their boxes, all from the GUI audit's follow-up (#1215). The fixes
passed the offline gate only: the layout tests (`test_un_widths.py`, `test_gui_flag_names.py`,
`test_grand_monuments_layout.py`, `test_tax_code_layout.py`, `test_cultural_hegemony_layout.py`,
`test_market_trade_partners.py`), the GUI lint and the audits. What only the game can show is below. In-game checks
don't gate a merge (CLAUDE.md, "In-game checks"); work through these the next time the game is up.

The cause, and the two cures, are `gui_modding_guide.md` gotchas #43 and #44.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main` once merged).
- **The UN.** `event te_debug_un.1` founds the UN and seats the great and major powers, and can have another member
  table a condemnation (`events/te_debug_un_events.txt`). Play a great power.
- **Watch it change with the panel open.** The drift showed when a button appeared after the panel was first drawn, so
  each check below changes the state while the panel stays open, then closes and reopens it.

## Checks

| Check | Expect | If it fails |
|---|---|---|
| **Champion / Undermine.** UN panel, Why Authority Is Moving, as a great-power member. Press Champion the Order, then Stop Championing. | Two buttons, 236 each, centred under the champions' list; Stop Championing takes Champion's place, Undermine stays put. Nothing past the panel's edge. | A row off-centre or past the edge: `un_act_row` / `un_act_slot` (`un_chamber_widget.gui`) didn't hold their size; read `gui.log` for the type. |
| **Programs and Conventions.** Join UN Peacekeeping, Human rights champions and Arms control, then Leave. | Join and Leave in the same place, inside the table, beside "No" / "Yes". | The 106 slot (`un_act_slot` with `slot_size`) is the place to look. |
| **Dues, food reserve, development fund.** Withhold dues and pay them; pledge grain and withdraw; Fund Development, then Raise and Reduce. | Each pair takes turns in one centred slot; Reduce, Raise and Defund keep their places, a gap where one is ruled out. | As above. |
| **Membership controls.** Overview, before the founding, outside the UN and as a member; press Leave, then Cancel. | Found (or Convene), Join or Leave under the membership cell, inside its column; Leave's Confirm and Cancel stacked there. | The Found / Join slot or the Leave stack: `un_overview_widget.gui`. |
| **The ballot.** A resolution in session, before and after voting, as a permanent member on a binding topic; press Veto, then Cancel. | For and Against centred; Veto under For, then Confirm under For and Cancel under Against. | The ballot block's `minimumsize = { 476 -1 }` (`un_layout_widget.gui`). |
| **One flag per country.** UN Delegations, Covert Agent Networks, an operation card, Known Operations, the Cultural Hegemony leaderboard, the Banking balance sheet. | The framed flag, then the name with no small flag before it; the name still underlined and hoverable. | `GetNameNoFlag` didn't keep the link: try `GetNameNoFormatting` with the row's own hover. |
| **Covert country names.** Agent Networks with a long name (United States of America, Austria-Hungary). | One line for most names now that the small flag is gone; a very long name wraps inside the 120 column. | Widen the Country column from Ops (40 → 30). |
| **Trade-partner legends.** Market panel, Trade tab, Export and Import Partners. | Flag and figure inside the legend box; the headings' hover says the figures are units a week. | |
| **Top Trade Partners hover.** Hover a row of the table. | Its lines wrap inside the tooltip's frame. | |
| **Grand Monuments, Rename.** Our Monuments: Name It, type a name, then Clear Name. | Rename and Name It centred; with a typed name, Rename, Name It and Clear Name centred, inside the panel. | The two rows' `visible` (`gm_state_has_typed_name`). |
| **Tax Code bill footer.** Budget > Tax Code with a bill under debate, while its support rises past the passage share. | Pass, Force Through and Withdraw centred; once support holds, Pass and Withdraw centred. | The two rows' `visible` (`te_tax_show_pass_support_sgui`). |
| **Passed bills' goods.** A passed bill that taxes or exempts a whole row of goods. | 13 icons to a row beside the label, inside the column. | `LABELLED_GOODS_ICONS_PER_ROW` in `gen_tax_code.py`. |
| **Global Warming row 2.** Join or leave an Enforce Emissions Reduction treaty, and switch the Market panel's Climate tab to another market. | The market cell under the tier cell, the treaty cell beside it when it shows. | |
| **Cultural Hegemony row 2.** A new game, the panel open across the first monthly recount. | The leaders' label and three slots from the start, filled at the recount; the row doesn't move. | |
