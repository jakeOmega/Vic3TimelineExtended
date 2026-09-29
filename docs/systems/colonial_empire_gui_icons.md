# Colonial Empire GUI: Icons

The Colonial Empire overview (`te_ce_overview_panel` in `gui/journal_entry_widgets/colonial_empire_widget.gui`) draws ten icons and a pie. All of them are **placeholders**: vanilla textures, or textures of other systems, that another `.gui` of this mod already uses, so the layout could be judged in game before the art exists (style rule 10, `docs/guides/gui_style_guide.md`). This page lists each one for the icon pipeline. `docs/systems/un_gui_icons.md` records how the UN's set went from placeholders to finished art.

**Where each is set.** Every icon is a literal `texture = "…"` line in `te_ce_overview_panel`, chosen by a display value's code (`colonial_empire_disp_tier`, `colonial_empire_disp_pressure_level`) or by a programme's scope-free handler (`colonial_empire_active_*_sgui`). No script reads the paths. Swapping one in is one path change; when the art lands, add a test that holds each code to its file, as `UnIconsTest` does for the UN.

**The rule for the set** is the UN's: simple and easy to recognise at 36 px. One bold object each; the states of one thing share an emblem and differ by a mark or a colour.

## Overview: the stability band

Shown at 36 px, the band's name beneath. One per band, picked by `colonial_empire_disp_tier`.

| Code | Band | Placeholder now | Final art should show | Proposed path |
|---|---|---|---|---|
| 5 | Solidified | `gfx/interface/icons/state_status_icons/state_homelands.dds` | a small globe with an overseas coast joined to the home coast by a gold band, full colour | `gfx/interface/icons/colonial_empire_icons/band_solidified.dds` |
| 4 | Stable | `gfx/interface/icons/state_status_icons/incorporated_state.dds` | the same globe, the coasts joined by a thinner gold line | `…/band_stable.dds` |
| 3 | Strained | `gfx/interface/icons/generic_icons/warning.dds` | the same globe, the line between the coasts pulled taut and amber | `…/band_strained.dds` |
| 2 | Crumbling | `gfx/interface/icons/state_status_icons/has_turmoil.dds` | the same globe, the line cracked and red | `…/band_crumbling.dds` |
| 1 | Collapsing | `gfx/interface/icons/war_goals/independence.dds` | the same globe, the line broken in two, the overseas coast in a new flag's colour | `…/band_collapsing.dds` |

## Overview: great-power pressure

The alert beside the pie while an escalation applies, 36 px, its word beneath. Picked by `colonial_empire_disp_pressure_level`.

| Code | State | Placeholder now | Final art should show | Proposed path |
|---|---|---|---|---|
| 1 | Diplomatic isolation | `gfx/interface/icons/generic_icons/disapproval_icon.dds` | a lone colonial flag on a pole inside a ring of turned-away figures, amber | `…/alert_isolation.dds` |
| 2 | International consensus | `gfx/interface/icons/generic_icons/red_cross.dds` | a round table of great-power flags with raised hands against one flag, red | `…/alert_consensus.dds` |

## Overview: the programmes

A row of three, 36 px, at full colour while the programme runs and 25% opacity while it does not.

| Programme | Placeholder now | Final art should show | Proposed path |
|---|---|---|---|
| Colonial Development Investment | `gfx/interface/icons/building_icons/building_browser_filter_icons/filter_icons_development.dds` | a railway bridge under construction over a tropical river, a crane beside it | `…/programme_invest.dds` |
| Military Garrison | `gfx/interface/icons/generic_icons/battalions.dds` | a colonial fort's gate with a sentry and a flag | `…/programme_garrison.dds` |
| Cultural Assimilation Programme | `gfx/interface/population/pop_culture.dds` | a schoolhouse with an open primer on its steps | `…/programme_assimilation.dds` |

## Overview: the condemners' pie

The condemning great powers' share of great-power prestige (`colonial_empire_disp_condemner_share`), a stacked `progresspie` in vanilla's `round_frame_dec.dds`. The textures are frame 1 transparent, frame 2 the colour (`gui_modding_guide.md`, "Pie charts of script-held data"); `scripts/image_pipeline/gen_ch_model_pie_textures.py` writes both kinds.

| Layer | Placeholder now | Final | Proposed path |
|---|---|---|---|
| The condemners' share (the fill) | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_communist.dds` (Cultural Hegemony's red, `#c44039`) | a red of its own, generated beside the UN's pair | `…/pie_condemners.dds` |
| The rest (the disc under it) | `gfx/interface/icons/un_icons/pie_rest.dds` (the UN's muted grey) | can stay the UN's disc, or a copy of it | `…/pie_rest.dds` |
