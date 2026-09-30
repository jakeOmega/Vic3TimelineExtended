# Strategic Reserve GUI: Icons

The Strategic Reserve panel (`gui/journal_entry_widgets/strategic_reserve_widget.gui`, restyled to `docs/guides/gui_style_guide.md` in September 2026) draws six icons of its own. One is final art and five are vanilla placeholders, per style rule 10. This list is what to replace, and with what.

**Where each is set.** Each is a literal `texture = "…"` line in `strategic_reserve_widget.gui`. No script reads the paths. Swapping a placeholder is one path change per `texture` line listed below.

## Final

| Where | Shows | File |
|---|---|---|
| Overview, hub cell (`te_st_res_overview_panel`), 36 px, twice: dimmed underneath, lit on top while the hub is fully staffed | the hub building's own icon | `gfx/interface/icons/building_icons/building_strategic_reserve_hub.dds` |

The bar markers use vanilla's `gfx/interface/progressbar/progressbar_marker.dds`, the marker the UN authority bar uses. It is interface chrome rather than an icon, and stays.

## Placeholders

| Where | Placeholder | Final art should show (icon-pipeline subject) | Proposed path |
|---|---|---|---|
| Inventory row, policy icon (`te_st_res_good_row`, the two `icon` widgets in the 30 px cell after the status icon), 24 px. Drawn at alpha 0.25 on Manual, and again at full colour on top while a reserve policy runs the good | vanilla's `gfx/interface/production_methods/auto_expand.dds`, the building auto-expand toggle | A brass centrifugal governor: two weighted arms on a spindle, flat and bold, in the gold of vanilla's goods icons, readable at 24 px. It says "regulates itself". One file serves both states, since the dimmed state is the same texture at low alpha. | `gfx/interface/icons/st_res_icons/policy_automated.dds` |


The icon must stay legible at alpha 0.25, so the silhouette matters more than detail.

### Status icons (round 3, 2026-09-30)

The owner asked for the status column as icons. The four share the 30 px cell after the fill bar in `te_st_res_good_row`, each at 24 px with its own `visible` on one value of `st_res_<good>_disp_status`, so exactly one is drawn. The status word (coloured as below) and its reason are on the cell's hover. One emblem for the set, a small supply crate, with the state shown by a mark in the word's colour, so the four read as one family.

| State (code) | Placeholder | Final art should show (icon-pipeline subject) | Proposed path |
|---|---|---|---|
| Idle (0) | vanilla's `gfx/interface/icons/generic_icons/trend_nochange.dds` | A closed wooden supply crate with a flat yellow bar across its front: the stock is held, nothing moving. | `gfx/interface/icons/st_res_icons/status_idle.dds` |
| Storing (1) | vanilla's `gfx/interface/icons/generic_icons/trend_up.dds` | The same crate with a bold green arrow pointing down into its open top: goods going in. | `gfx/interface/icons/st_res_icons/status_storing.dds` |
| Withdrawing (2) | vanilla's `gfx/interface/icons/generic_icons/trend_down.dds` | The same crate with a bold orange arrow rising out of its open top: goods coming out. | `gfx/interface/icons/st_res_icons/status_withdrawing.dds` |
| Blocked (3) | vanilla's `gfx/interface/icons/generic_icons/warning.dds` | The same crate with a red barrier bar across it: the lane cannot move (full, empty, or the hub understaffed). | `gfx/interface/icons/st_res_icons/status_blocked.dds` |

The placeholders are the trend arrows the UN pillars use and vanilla's warning mark, so they read as up, down, level and stop until the art exists.
