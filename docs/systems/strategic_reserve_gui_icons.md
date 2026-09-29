# Strategic Reserve GUI: Icons

The Strategic Reserve panel (`gui/journal_entry_widgets/strategic_reserve_widget.gui`, restyled to `docs/guides/gui_style_guide.md` in September 2026) draws two icons of its own. One is final art and one is a vanilla placeholder, per style rule 10. This list is what to replace, and with what.

**Where each is set.** Each is a literal `texture = "…"` line in `strategic_reserve_widget.gui`. No script reads the paths. Swapping a placeholder is one path change per `texture` line listed below.

## Final

| Where | Shows | File |
|---|---|---|
| Overview, hub cell (`te_st_res_overview_panel`), 36 px, twice: dimmed underneath, lit on top while the hub is fully staffed | the hub building's own icon | `gfx/interface/icons/building_icons/building_strategic_reserve_hub.dds` |

The bar markers use vanilla's `gfx/interface/progressbar/progressbar_marker.dds`, the marker the UN authority bar uses. It is interface chrome rather than an icon, and stays.

## Placeholders

| Where | Placeholder | Final art should show (icon-pipeline subject) | Proposed path |
|---|---|---|---|
| Inventory row, policy icon (`te_st_res_good_row`, the two `icon` widgets in the 26 px cell after the status), 24 px. Drawn at alpha 0.25 on Manual, and again at full colour on top while a reserve policy runs the good | vanilla's `gfx/interface/production_methods/auto_expand.dds`, the building auto-expand toggle | A brass centrifugal governor: two weighted arms on a spindle, flat and bold, in the gold of vanilla's goods icons, readable at 24 px. It says "regulates itself". One file serves both states, since the dimmed state is the same texture at low alpha. | `gfx/interface/icons/st_res_icons/policy_automated.dds` |

The icon must stay legible at alpha 0.25, so the silhouette matters more than detail.
