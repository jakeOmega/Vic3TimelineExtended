# Colonial Empire GUI: Icons

The Colonial Empire overview (`te_ce_overview_panel` in `gui/journal_entry_widgets/colonial_empire_widget.gui`) draws ten icons and a two-slice pie with its legend, and the eligible-territories list under Why Stability Is Moving (`te_ce_territory_row`) one more. All of them are **placeholders**: vanilla textures, or textures of other systems, that another `.gui` of this mod already uses, so the layout could be judged in game before the art exists (style rule 10, `docs/guides/gui_style_guide.md`). This page lists each one for the icon pipeline. `docs/systems/un_gui_icons.md` records how the UN's set went from placeholders to finished art.

**Where each is set.** Every icon is a literal `texture = "…"` line in `te_ce_overview_panel` or `te_ce_territory_row`, chosen by a display value's code (`colonial_empire_disp_tier`, `colonial_empire_disp_pressure_level`, a territory's `colonial_territory_disp_colony`) or by a programme's scope-free handler (`colonial_empire_active_*_sgui`). No script reads the paths. Swapping one in is one path change; when the art lands, add a test that holds each code to its file, as `UnIconsTest` does for the UN.

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

## Overview: the great-power pie

Great-power prestige (ours included) as a stacked `progresspie` in vanilla's `round_frame_dec.dds`: the condemning powers' share (`colonial_empire_disp_condemner_share`) and, in its own colour, the supporting powers' share (the supporters' layer fills to `colonial_empire_disp_pressure_cum`, the sum, under the condemners'). The legend beside it uses the same two textures as swatches. The textures are frame 1 transparent, frame 2 the colour (`gui_modding_guide.md`, "Pie charts of script-held data"); `scripts/image_pipeline/gen_ch_model_pie_textures.py` writes both kinds.

| Layer | Placeholder now | Final | Proposed path |
|---|---|---|---|
| The condemners' share (the top fill, and its swatch) | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_communist.dds` (Cultural Hegemony's red, `#c44039`) | a red of its own, generated beside the UN's pair | `…/pie_condemners.dds` |
| The supporters' share (the lower fill, and its swatch) | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_developmentalist_junta.dds` (Cultural Hegemony's green, `#4ea253`) | a green of its own | `…/pie_supporters.dds` |
| The rest (the disc under both) | `gfx/interface/icons/un_icons/pie_rest.dds` (the UN's muted grey) | can stay the UN's disc, or a copy of it | `…/pie_rest.dds` |

## Why Stability Is Moving: the eligible territories

The first cell of each row in the collapsed Eligible Territories list, 22 px: lit while the territory counts as a colony (it meets the indigenous-population or the living-standards test), dimmed to 25% while it does not. Picked by `colonial_territory_disp_colony` on the stored state (added in play-test round 3, 2026-09-30).

| Code | State | Placeholder now | Final art should show | Proposed path |
|---|---|---|---|---|
| 1 | Counted as a colony | `gfx/interface/icons/state_status_icons/colony.dds` (vanilla's colony status icon, full colour) | a colonial flag planted on a small overseas coast, full colour | `…/territory_colony.dds` |
| 0 | Not counted as a colony | the same file at 25% opacity | the same art; the widget dims it | `…/territory_colony.dds` |

## Overview: the stability bar needs no art

The bar (play-test round 3) is built from vanilla's own bar types: `default_progressbar_horizontal` for the frame and the solid fill, `green_progressbar_horizontal` at 40% for the stretch while stability rises (good), `bad_progressbar_horizontal` at 50% for the stretch while it falls (bad), and the next band's edge as a 3 × 24 px line of `gfx/interface/backgrounds/white.dds` tinted cream (`color = { 0.96 0.90 0.72 0.95 }`). None is a placeholder. The pillar bars under Why Stability Is Moving are vanilla's `double_direction_progressbar`, red to the left and green to the right, and need no art either.
