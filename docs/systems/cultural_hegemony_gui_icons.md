# Cultural Hegemony GUI: Placeholder Icons

The overview at the top of the Cultural Hegemony panels draws three kinds of art that are placeholders today (`gui_style_guide.md` rule 10). The overview is `te_ch_overview_panel` in `gui/journal_entry_widgets/cultural_hegemony_widget.gui`, shown in the journal entry and in the Society panel's Hegemony tab. This file lists each placeholder, what the final art should show and where it should go, as `un_gui_icons.md` did for the UN before its set was made.

**Where each is set.** Every one is a literal `texture = "…"` line in `cultural_hegemony_widget.gui`, chosen by a display value's code (`ch_disp_tier_code`) or a scripted GUI (`ch_benchmark_sgui`). No script reads the paths. `PlaceholderTest` in `test_cultural_hegemony_layout.py` holds each current path to this file and to the proposed one, so swapping in the final art is a path change in the `.gui` and in the test's `PLACEHOLDERS`, and a row moved here from the placeholder tables to the finished one.

**The rule for the set** is the UN's: simple and easy to recognize at 36 px. One bold object per icon; states of one thing share an emblem and differ by a mark, a metal or a size. The icons would come from the icon pipeline (`scripts/image_pipeline/`, as the UN set did), the pie pair from `scripts/image_pipeline/gen_ch_model_pie_textures.py`.

## Overview: influence tier

Codes 0–5 are `ch_tier` (written only by `ch_set_display_state`). Shown at 36 px in the first cell of the overview's first row, the tier's short name beneath it. **Placeholder now:** the journal entry's own icon, `gfx/interface/icons/event_icons/je_cultural_hegemony.dds`, for all six, so only the word changes.

One emblem, a laurel wreath around a lyre, that grows and takes a richer metal as the tier climbs:

| Code | Tier | Final art shows | Proposed path |
|---|---|---|---|
| 0 | Negligible | a single grey laurel sprig, two leaves, no lyre | `gfx/interface/icons/ch_icons/tier_negligible.dds` |
| 1 | Minor | a small bronze laurel sprig beside a plain wooden lyre | `gfx/interface/icons/ch_icons/tier_minor.dds` |
| 2 | Moderate | a bronze half wreath around a bronze lyre | `gfx/interface/icons/ch_icons/tier_moderate.dds` |
| 3 | Significant | a full bronze laurel wreath around a bronze lyre | `gfx/interface/icons/ch_icons/tier_significant.dds` |
| 4 | Major Power | a full silver laurel wreath around a silver lyre | `gfx/interface/icons/ch_icons/tier_major.dds` |
| 5 | Hegemon | a full gold laurel wreath around a gold lyre, with short gold rays behind it | `gfx/interface/icons/ch_icons/tier_hegemon.dds` |

## Overview: Foreign Cultural Benchmark

Shown at 36 px, only while the country carries `cultural_hegemony_foreign_benchmark` (the legitimacy penalty for trailing the leading cultural power), the red word "Benchmark" beneath it. **Placeholder now:** vanilla's warning mark, `gfx/interface/icons/generic_icons/warning.dds`.

| Final art shows | Proposed path |
|---|---|
| a small grey sceptre in the shadow of a large gold laurel wreath, a red downward arrow beside the sceptre | `gfx/interface/icons/ch_icons/benchmark.dds` |

## Overview: our cultural share (pie pair)

Our share of global cultural influence as a framed pie, 62 px inside `round_frame_dec.dds`, drawn as two stacked `progresspie`s: a full disc for the rest of the world and our share on top. **Placeholder now:** two of the political-models pie's own slice textures, the Mixed / Other grey as the rest and the Liberal gold as our share. The overview's pie therefore shares its colours with two slices of the models pie further down the panel, which is the reason to replace them.

Both in the pie format (`gui_modding_guide.md`, "Pie charts of script-held data"): frame 1 fully transparent, frame 2 an antialiased disc. Add them to `gen_ch_model_pie_textures.py` the way it writes `UN_PIES`, and validate the pair against the dark panel as it validated the UN's.

| Layer | Placeholder now | Final art shows | Proposed path |
|---|---|---|---|
| Our share (fill) | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_liberal.dds` | a disc in the amber of the share history chart's bars (`color = { 0.78 0.60 0.30 }`, about `#c79a4d`) | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_share_fill.dds` |
| The rest (disc) | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_other.dds` | a disc in a muted warm grey, as the UN's `pie_rest` | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_share_rest.dds` |

## Not placeholders

- **The exported model's disc.** The overview shows the leading power's political model as that model's slice texture from the models pie (`ch_pie_<model>.dds`, frame 2), so the colour matches the pie and its legend. That is by design. A drawn emblem per model would be a new set of fifteen, not a swap.
- **The trend arrows** are vanilla's `trend_up` / `trend_down` / `trend_nochange`, as the UN's pillar rows use them.
- **World rank** is a number, with no icon.
