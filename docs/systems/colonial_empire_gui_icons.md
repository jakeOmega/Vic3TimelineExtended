# Colonial Empire GUI: Icons

The Colonial Empire overview (`te_ce_overview_panel` in `gui/journal_entry_widgets/colonial_empire_widget.gui`) draws ten icons of its own and a three-disc pie with its legend. The eligible-territories list under Why Stability Is Moving (`te_ce_territory_row`) draws one more. They were vanilla placeholders, or other systems' textures, through the style pass's play-test rounds, and PR #586 replaced them. All of them live in `gfx/interface/icons/colonial_empire_icons/`.

**Where each is set.** Every icon is a literal `texture = "…"` line in `te_ce_overview_panel`, `te_ce_ov_pie` or `te_ce_territory_row`. What picks one is a display value's code (`colonial_empire_disp_tier`, `colonial_empire_disp_pressure_level`, a territory's `colonial_territory_disp_colony`) or a programme's scope-free handler (`colonial_empire_active_*_sgui`). No script reads the paths. `ColonialIconsTest` in `test_colonial_empire_layout.py` holds each code to its file and fails on any placeholder left in the widget.

**Remaking one.** The icons come from the icon pipeline (`scripts/image_pipeline/`). Their registry entries are the `colonial_part`, `colonial` and `colonial_state` categories in `icon_prompts.py`, and each entry's `now` field names the placeholder it replaced. The pie discs come from `gen_ch_model_pie_textures.py`. Change the entry, re-render, review, then `write`. The GUI needs no edit unless a file name changes.

**The rule for the set** is the UN's: simple and easy to recognise at 36 px. The states of one thing share an emblem and differ by a mark or a colour. The five bands share one globe, and the two alerts share one flag.

## Overview: the stability band

One globe of the Earth on a small stand. A drawn tie crosses it from the home coast to the overseas coast, and the tie's state is the band. Shown at 36 px, the band's name beneath. Picked by `colonial_empire_disp_tier`.

| Code | Band | Shows | File |
|---|---|---|---|
| 5 | Solidified | the globe, a thick gold tie across it | `gfx/interface/icons/colonial_empire_icons/band_solidified.dds` |
| 4 | Stable | the globe, a thin gold tie | `gfx/interface/icons/colonial_empire_icons/band_stable.dds` |
| 3 | Strained | the globe, the tie pulled taut and straight, amber | `gfx/interface/icons/colonial_empire_icons/band_strained.dds` |
| 2 | Crumbling | the globe, the tie red and cracked | `gfx/interface/icons/colonial_empire_icons/band_crumbling.dds` |
| 1 | Collapsing | the globe, the red tie broken in two | `gfx/interface/icons/colonial_empire_icons/band_collapsing.dds` |

The list asked for the coasts joined by a gold band, then a line, then a taut, cracked and broken line, with the overseas coast in a new flag's colour at Collapsing. The art draws the tie in those five states but gives the coast no new colour: the tie alone carries the state.

## Overview: great-power pressure

One small orange flag on a bare grey rock, on a coloured disc. Shown beside the pie while an escalation applies, 36 px, its word beneath. Picked by `colonial_empire_disp_pressure_level`.

| Code | State | Shows | File |
|---|---|---|---|
| 1 | Diplomatic isolation | the lone flag on its rock, on amber | `gfx/interface/icons/colonial_empire_icons/alert_isolation.dds` |
| 2 | International consensus | the same flag, smaller, on red, eight white arrows closing in from all sides | `gfx/interface/icons/colonial_empire_icons/alert_consensus.dds` |

The list asked for the flag inside a ring of turned-away figures, and for a round table of great-power flags with hands raised against one. Figures would be specks at 36 px, and the table rendered as a brown disc with specks, so both alerts use the lone flag, and the arrows carry the consensus.

## Overview: the programmes

A row of three, 36 px, at full colour while the programme runs and 25% opacity while it does not. The fade is the design: one file per programme.

| Programme | Shows | File |
|---|---|---|
| Colonial Development Investment | a steel railway bridge span under construction over a river, a small yellow crane on it | `gfx/interface/icons/colonial_empire_icons/programme_invest.dds` |
| Military Garrison | a squat sandstone fort gatehouse with crenellations and a small dark red pennant | `gfx/interface/icons/colonial_empire_icons/programme_garrison.dds` |
| Cultural Assimilation Programme | a small red wooden schoolhouse with a bell tower, an open book on its steps | `gfx/interface/icons/colonial_empire_icons/programme_assimilation.dds` |

The list asked for the fort's gate with a sentry. At 36 px a sentry is a speck, so the gatehouse has only its pennant.

## Overview: the great-power pie

Great-power prestige (ours included) as a stacked `progresspie` in vanilla's `round_frame_dec.dds`. The condemning powers' share is on top (`colonial_empire_disp_condemner_share`). Under it, in its own colour, the supporting powers' share: the supporters' layer fills to `colonial_empire_disp_pressure_cum`, the sum of both. The disc under both is the rest. The legend beside the pie uses the condemners' and supporters' textures as swatches. Each texture is 256 × 128: frame 1 is transparent and frame 2 is the colour (`gui_modding_guide.md`, "Pie charts of script-held data"). `scripts/image_pipeline/gen_ch_model_pie_textures.py` writes all three.

| Layer | Colour | File |
|---|---|---|
| The condemners' share (the top fill, and its swatch) | red, `#dd4a3a` | `gfx/interface/icons/colonial_empire_icons/pie_condemners.dds` |
| The supporters' share (the lower fill, and its swatch) | teal green, `#4cbc9a` | `gfx/interface/icons/colonial_empire_icons/pie_supporters.dds` |
| The rest (the disc under both) | warm grey, `#8c8474` | `gfx/interface/icons/colonial_empire_icons/pie_rest.dds` |

The placeholders were Cultural Hegemony's communist red and developmentalist-junta green, over the UN's grey disc. No loc text or legend line names a colour, so nothing else moved with them.

## Why Stability Is Moving: the eligible territories

The first cell of each row in the collapsed Eligible Territories list, 22 px. It is lit while the territory counts as a colony (it meets the indigenous-population or the living-standards test) and dimmed to 25% by the widget while it does not. Picked by `colonial_territory_disp_colony` on the stored state.

| Code | State | Shows | File |
|---|---|---|---|
| 1 | Counted as a colony | a small orange flag planted on a green tropical island with one palm tree and a strip of beach, full colour | `gfx/interface/icons/colonial_empire_icons/territory_colony.dds` |
| 0 | Not counted as a colony | the same file at 25% opacity | `gfx/interface/icons/colonial_empire_icons/territory_colony.dds` |

## What stays vanilla

The stability bar is vanilla's own bar types:
- `default_progressbar_horizontal` for the frame and the solid fill;
- `green_progressbar_horizontal` at 40% for the stretch while stability rises (good);
- `bad_progressbar_horizontal` at 50% for the stretch while it falls (bad);
- a 3 × 24 px line of `gfx/interface/backgrounds/white.dds`, tinted cream (`color = { 0.96 0.90 0.72 0.95 }`), at the next band's edge.

The pillar bars under Why Stability Is Moving are vanilla's `double_direction_progressbar`, red to the left and green to the right. The trend arrows (`trend_up`, `trend_down`, `trend_nochange`) and the pie's round frame are vanilla's too. None of these is a placeholder.
