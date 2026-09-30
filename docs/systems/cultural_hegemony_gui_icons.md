# Cultural Hegemony GUI: Icons

The overview at the top of the Cultural Hegemony panels has seven icons of its own and a pie pair. The overview is `te_ch_overview_panel` in `gui/journal_entry_widgets/cultural_hegemony_widget.gui`, shown in the journal entry and in the Society panel's Hegemony tab.

During the style-guide pass these were vanilla placeholders: the entry's own icon for all six tiers, vanilla's warning mark, and two of the models pie's slice textures. PR #586 replaced them. The icons are in `gfx/interface/icons/ch_icons/`. The pie pair is beside the models pie in `gfx/interface/journal_entry_widgets/ch_model_pie/`.

**Where each is set.** Every one is a literal `texture = "…"` line in `cultural_hegemony_widget.gui`, chosen by a display value's code (`ch_disp_tier_code`) or by a scripted GUI (`ch_benchmark_sgui`). No script reads the paths. `ChIconsTest` in `test_cultural_hegemony_layout.py` holds each code to its file and fails on any placeholder left in the overview.

**Remaking one.** The icons come from the icon pipeline (`scripts/image_pipeline/`). The pie pair comes from `scripts/image_pipeline/gen_ch_model_pie_textures.py` (`PANEL_PIES`). Change the entry, re-render, review, then write. The GUI needs no edit unless a file name changes.

**The rule for the set** is the UN's: simple and easy to recognize at 36 px. The tiers share one emblem, a lyre in a laurel wreath, which grows and takes a richer metal as the tier climbs.

## Overview: influence tier

Codes 0–5 are `ch_tier`, which only `ch_set_display_state` writes. The icon is shown at 36 px in the first cell of the overview's first row, with the tier's short name beneath it.

| Code | Tier | Shows | File |
|---|---|---|---|
| 0 | Negligible | a single laurel sprig, greyed, no lyre | `tier_negligible.dds` |
| 1 | Minor | a plain wooden lyre, a small laurel sprig at its foot | `tier_minor.dds` |
| 2 | Moderate | a bronze lyre, a laurel branch along one side | `tier_moderate.dds` |
| 3 | Significant | a bronze lyre in a full bronze laurel wreath | `tier_significant.dds` |
| 4 | Major Power | a silver lyre in a full silver laurel wreath | `tier_major.dds` |
| 5 | Hegemon | a gold lyre in a full gold laurel wreath, drawn gold rays behind it | `tier_hegemon.dds` |

Two icons were finished by hand after the render:
- The negligible sprig is greyed, because the icon model drew it green in every seed.
- The hegemon's rays are drawn, because no seed drew them.

## Overview: Foreign Cultural Benchmark

The icon is shown at 36 px only while the country carries `cultural_hegemony_foreign_benchmark`, the legitimacy penalty for trailing the leading cultural power. The red word "Benchmark" sits beneath it.

| Shows | File |
|---|---|
| a grey sceptre inside a gold laurel wreath, a red downward arrow beside it | `benchmark.dds` |

## Overview: our cultural share (pie pair)

Our share of global cultural influence is a framed pie, 62 px inside `round_frame_dec.dds`. It is drawn as two stacked `progresspie`s: a full disc for the rest of the world, with our share on top.

Both textures use the pie format (`gui_modding_guide.md`, "Pie charts of script-held data"): frame 1 fully transparent, frame 2 an antialiased disc. The colours pass the dataviz validator against the dark panel. The share history chart's bars use the same amber.

| Layer | Shows | File |
|---|---|---|
| Our share (fill) | an amber disc, `#d89a2b`. The proposed `#c79a4d` failed the validator's normal-vision floor against the grey. | `ch_share_fill.dds` |
| The rest (disc) | a muted warm grey disc, `#8c8474`, the same grey as the UN's `pie_rest` | `ch_share_rest.dds` |

## Not from the icon pipeline

- **The exported model's disc.** The overview shows the leading power's political model as that model's slice texture from the models pie (`ch_pie_<model>.dds`, frame 2), so the colour matches the pie and its legend.
- **The trend arrows** are vanilla's `trend_up` / `trend_down` / `trend_nochange`, as the UN's pillar rows use them.
- **World rank** is a number, with no icon.
- **The leading powers** are vanilla's `flag` widget, drawn from the capitals the viewer holds (`ch_leader_seat_1..3`), as the UN overview draws its Security Council.
