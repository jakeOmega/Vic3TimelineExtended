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
| **Grand Monuments, a level's worth.** The Grand Monuments tab with no construction site, then the journal entry. | Under the Monument Policy line, one centred line: "A level built now adds 5.000 Grandeur (5 in 1836)" in 1836, a smaller figure later; its hover explains the rate. Once a site stands, Awaiting Dedication opens on its row. | Two lines, or cut short: the textbox under `gm_je_ov_policy` in `te_gm_overview_panel`. |
| **Tax Code bill footer.** Budget > Tax Code with a bill under debate, while its support rises past the passage share. | Pass, Force Through and Withdraw centred; once support holds, Pass and Withdraw centred. | The two rows' `visible` (`te_tax_show_pass_support_sgui`). |
| **Passed bills' goods.** A passed bill that taxes or exempts a whole row of goods. | 13 icons to a row beside the label, inside the column. | `LABELLED_GOODS_ICONS_PER_ROW` in `gen_tax_code.py`. |
| **Global Warming row 2.** Join or leave an Enforce Emissions Reduction treaty, and switch the Market panel's Climate tab to another market. | The market cell under the tier cell, the treaty cell beside it when it shows. | |
| **Cultural Hegemony row 2.** A new game, the panel open across the first monthly recount. | The leaders' label and three slots from the start, filled at the recount; the row doesn't move. | |

## Older panels (the sweep of 2026-10-28)

The same drift, in panels that predate #1202 and #1215: a centred row or panel sized by what shows, so it was centred at
its first width and ran past its column when a cell appeared. Each now keeps one width (an ungated slot for a cell that
comes and goes, two rows with fixed contents, or a fixed width). The layout tests pin each
(`test_cultural_hegemony_layout.py`, `test_covert_layout.py`, `test_space_race_layout.py`, `test_nuclear_layout.py`,
`test_banking_layout.py`). As above, change the state with the panel open, then close and reopen it.

| Check | Expect | If it fails |
|---|---|---|
| **Cultural Hegemony row 1.** A new game, the entry or the Society panel's Hegemony tab open across the first monthly recount (`event te_debug_ch.1`, F, recounts now); later, while the Foreign Cultural Benchmark comes and goes. | Tier, rank, model and benchmark in one row inside the column, the same width throughout: before the recount the tier at the left with gaps where the rest will be, and a gap at the right while there is no benchmark. | The slots of row 1 (`cultural_hegemony_widget.gui`). If the empty benchmark slot reads as a hole, split the row in two with fixed contents (with and without the benchmark). |
| **Covert row 1.** `event te_debug_covert.7`, A (catch every foreign operation against us), with the panel open. | Standing, Funding, Tradecraft and the catch centred inside the column; with no recent catch, a gap where it goes. | The catch's slot (`covert_operations_widget.gui`, row 1). |
| **Covert slot strip.** Change the funding level with the panel open, so the number of slots changes. | The slots fill a fixed 318 strip from its left, under the centred label, and nothing moves past the column. | The strip's `minimumsize = { 318 -1 }`. If slots from the left read as off-centre under the label, a strip that is centred and still can't drift needs all ten places drawn, the ones the country lacks as faint outlines. |
| **Space Race row 1.** Solar Colonization's overview open; switch its production method off (Idle) and back on. | Idle with the stage cell, centred; running, the state, the setback risk and the stage, across the column. Nothing past the edge. | The two rows' `visible` (`space_race_widget.gui`). A third cell missing from one row means the repeated `block "sr_third_cells"` didn't take the override in both. |
| **Nuclear Powers.** The panel open as the world's first warhead is built (`event te_debug_nuclear.1`, A), through the first monthly ranking. | The column heads at the left of a 480 panel from the start; the rows fill in under them without the panel moving. | `minimumsize = { 480 -1 }` on `nuclear_program_powers_head` (`nuclear_program_widget.gui`), its 6 margins counted; if the panel is 12 wider than its rows, they aren't, and 468 is the figure. |
| **Nuclear reputation.** Our Record after a crisis ends (`event te_debug_deterrence.4`), before and after the first pledge. | The panel as wide as the sections around it, whichever lines show. | `minimumsize = { 512 -1 }` on the reputation section's `nd_panel` (`nuclear_deterrence_widget.gui`). It counts the panel's 10 margins, as `te_banking_mon_readout`'s 500 does; if the panel comes out 20 wider than the sections, it doesn't here, and 492 is the figure. |
| **Banking mandates.** Monetary Policy with mandates by choice; enact a gold standard, or leave one, with the panel open. | Inflation Targeting and Dual Mandate above Growth and Peg Defence, centred; off gold, Growth under Inflation Targeting with a gap beside it. | `minimumsize = { 456 -1 }` on the second row (`banking_dashboard_widget.gui`). |

## Underlines removed (2026-10-30)

`gui_style_guide.md` rule 3 now follows vanilla: a hoverable word in running text is underlined, a hover's label or
figure is not. The Space Race lost its underlines in #1258 (its checks are in `space-race-playtest.md`); every other
mod panel lost its `default_format = "#tooltippable"` and the `label_format`, `row_format`, `cell_format` and
`name_format` blocks that toggled it, and the loc labels written `#tooltippable Word#!` were unwrapped. No color had
been moved into loc for those underlines outside the Space Race. `test_gui_underlines.py` holds the panels to the rule.

| Check | Expect | If it fails |
|---|---|---|
| **No labels underlined.** Open each system panel: Banking, Cultural Hegemony, Covert, Colonial Empire, Demographics, Global Warming, Grand Monuments, Nuclear, Seabed, Strategic Reserve, Tax Code, the UN, the Nation tab; the state view's tiles, the construction market rows, the Market panel's trade partners, the Budget breakdown. | No row label, figure, cell or column head is underlined; each still shows its hover. | An underline left: the textbox's type or its loc. |
| **Underlines that stay.** The UN proposal rows' "None" and "No Case", an agency's "Its terms", a Grand Monument's signature name, the homeland tile's two thresholds, a taxation law's "Tax effects", the Banking notes' "Banking Cycle", any concept link. | Underlined, each opening its own tooltip. | A nested form unwrapped by mistake: the key's `#tooltippable;tooltip:` or `#tooltippable #tooltip:` markup. |
| **Colors without underlines.** Colonial Empire's red table cells, Banking's phase words (green Expansion, red Panic), the UN chamber's "Firmly for" and "firmly against" counts. | Each keeps its color. | A cream value: its color was the underline's; put it back inline in the loc. |
| **Subheadings.** Grand Monuments' Interest Group Approval and Monument Policy; the Tax Code review's Taxed Goods, Agricultural Relief, Regional Relief and Revenue Estimate. | In the heading style, as before, with no underline. | |
| **The Tax Code's estimate note.** Budget > Tax Code with a bill under debate, the line above Interest Groups' cards. | The note's own style (`te_tax_note`'s `#lore`), as the panel's other notes; "Estimate out of date:" still red. | It was plain cream, underlined; if the lore color drowns the red, give the line a `default_format` of its own. |
