# Grand Monuments GUI: Placeholder Icons

The Monuments journal entry's overview and its monument rows draw five status icons. All five are vanilla placeholders, chosen so the layout can be judged in game before the art exists (`gui_style_guide.md` rule 10). This page lists them for the icon pipeline.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/grand_monuments_widget.gui`: the overview's cells (`te_gm_overview_panel`, one `gm_ov_cell` per status), the Hard Times line under them, and a monument row's status (`gm_monument_row`, one `gm_row_status` per `gm_status_code`). A status uses the same texture in both places. No script reads the paths. `IconsTest` in `test_grand_monuments_layout.py` holds each code to its path in its `ICONS` table and fails if the widget uses a texture the table doesn't list.

**Swapping one in.** Render it, write it to the proposed path, then change the path in the widget and in `ICONS`. The overview dims a cell to 25% opacity while its count is zero, so each icon must still read when faded, like the UN's agencies.

**Style.** Shown at 36 px (Hard Times at 32), beside the UN's overview icons, so the same rule applies: one bold object, easy to recognise at that size (`un_gui_icons.md`). The four statuses are states of one monument, so they could share an emblem (a small column on a plinth) and differ by a mark, the way the UN's membership icons share the wreath.

| Status (code) | Where | Placeholder now | Final art should show (icon-pipeline subject) | Proposed path |
|---|---|---|---|---|
| Undedicated (1) | overview cell; row status | `gfx/interface/icons/generic_icons/undecided_icon.dds` | a plain stone monument on a plinth, bare, with an empty panel where a dedication would be carved | `gfx/interface/icons/gm_icons/status_undedicated.dds` |
| Stands (2) | overview cell; row status | `gfx/interface/icons/generic_icons/green_checkmark.dds` | the same monument in bright stone with a gold laurel wreath hung on its face | `gfx/interface/icons/gm_icons/status_stands.dds` |
| Heritage (3) | overview cell; row status | `gfx/interface/icons/generic_icons/maybe_icon.dds` | the same monument, weathered and mossy, behind a low bronze railing | `gfx/interface/icons/gm_icons/status_heritage.dds` |
| Contested (4) | overview cell; row status | `gfx/interface/icons/generic_icons/disapproval_icon.dds` | the same monument with a thick rope thrown around its top and a crack down its face | `gfx/interface/icons/gm_icons/status_contested.dds` |
| Hard Times | its own line under the overview's cells, over the red phrase, only while it holds | `gfx/interface/icons/generic_icons/warning.dds` | an empty wooden alms bowl beside a stonemason's idle chisel and mallet | `gfx/interface/icons/gm_icons/hard_times.dds` |

"Unsettled", the brief state between a change of government and the month's check, shares code 2 and so shows the Stands icon with its own word beneath.
