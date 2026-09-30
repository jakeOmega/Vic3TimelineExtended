# Strategic Reserve GUI: Icons

The Strategic Reserve panel (`gui/journal_entry_widgets/strategic_reserve_widget.gui`, restyled to `docs/guides/gui_style_guide.md` in September 2026) draws six icons. The overview's hub icon is the hub building's own. The other five are the panel's own: they were vanilla placeholders through the style-guide pass, and PR #586 replaced them. They live in `gfx/interface/icons/st_res_icons/`.

**Where each is set.** Every icon is a literal `texture = "…"` line in `strategic_reserve_widget.gui`. No script reads the paths. `IconsTest` in `test_strategic_reserve_layout.py` holds each status to its file, holds the policy icon to its file, and fails on any of the old placeholders coming back.

**Remaking one.** The art comes from the icon pipeline (`scripts/image_pipeline/`). Change the entry there, re-render, review, then write the file at the same path. The GUI needs no edit unless a file name changes.

## Overview: the hub

| Where | Shows | File |
|---|---|---|
| Hub cell (`te_st_res_overview_panel`), 36 px, drawn twice: dimmed underneath, lit on top while the hub is fully staffed | the hub building's own icon | `gfx/interface/icons/building_icons/building_strategic_reserve_hub.dds` |

## Inventory rows: status

One emblem for the set: an open wooden supply crate. The state is a mark in the colour of the status word, so the four read as one family. Each is 24 px in the 30 px cell after the fill bar, in `te_st_res_good_row`, and each has one `visible` on one value of `st_res_<good>_disp_status`, so exactly one is drawn. The status word and its reason are on the cell's hover.

| Code | State | Shows | File |
|---|---|---|---|
| 0 | Idle | the open crate with a flat yellow bar across its front: the stock is held, nothing moving | `status_idle.dds` |
| 1 | Storing | the open crate with a bold green arrow pointing down into it: goods going in | `status_storing.dds` |
| 2 | Withdrawing | the open crate with a bold orange arrow rising out of it: goods coming out | `status_withdrawing.dds` |
| 3 | Blocked | the open crate with a red-and-white striped barrier across its front: the lane cannot move (full, empty with a release set, or the hub understaffed) | `status_blocked.dds` |

The list asked for a closed crate for Idle. The art keeps the one open crate for all four, so only the mark changes between states.

## Inventory rows: policy

| Where | Shows | File |
|---|---|---|
| Policy icon (`te_st_res_good_row`, the two `icon` widgets in the 30 px cell after the status icon), 24 px. Drawn at alpha 0.25 on Manual, and again at full colour on top while a reserve policy runs the good | a brass centrifugal governor: two weighted ball arms on a spindle, "regulates itself" | `policy_automated.dds` |

One file serves both states: the dimmed state is the same texture at 25% alpha, the panel's lit/dimmed convention (style rule 4).

## The Market panel's Reserve tab

The tab's label, "Reserve" (`gui/market_panel.gui`, the sixth slot), starts with the Storing crate, `status_storing.dds`, as the text icon `te_tab_strategic_reserve` in `gui/zzz_extra_goods_texticons.gui` (25 px, the goods icons' size and offset): goods going into store, which is what the reserve is for. It is the inventory's own file, so no new art. It is in the label, not in the strip's `*_button_icon` block, because at six tabs an icon beside the centred name would cover its first letters (`gui_modding_guide.md` gotcha #31). `MarketTabTest` in `test_strategic_reserve_layout.py` holds the text icon to its file.

## Interface chrome

The fill bar's markers use vanilla's `gfx/interface/progressbar/progressbar_marker.dds`, the marker the UN authority bar uses. It is chrome rather than an icon, and stays.
