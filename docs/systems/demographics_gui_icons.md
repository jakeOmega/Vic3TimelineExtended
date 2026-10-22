# Demographics GUI: Icons

The Demographics tab's overview and the state subtab's draw eight icon cells each, two to a row, the way Banking's overview does (issue #1029; `gui_style_guide.md` rule 4). The History section marks its census years with three pips. The Leading Cause of Death cell and the Famine pip have their own icons (2026-10-22); the other nine are vanilla placeholders for now, chosen to read at their size. Rule 10 asks for this list: what each icon stands for, what the final art should show and where it goes. The pie's slice colours and the trend arrows are not placeholders (below).

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/te_demographics_widgets.gui`: the cells in `te_demog_overview` (the country) and `te_state_demog_overview` (a state), each in its cell's `icon` block, and the pips in `te_demog_hist_pips` and its key, `te_demog_hist_pip_legend`. No script reads the paths. Each cell has one icon, but for the Leading Cause of Death, whose `icon_layers` block draws the leading cause's own icon over the same spot once deaths by cause are counted (below); the trend arrow beside a reading changes too, picked by a `te_demog_trend_*` code. `IconsTest` in `test_demographics_layout.py` holds each row below to the markup, both overviews alike, and fails on a cell, cause or pip whose texture the doc doesn't list.

**Replacing one.** Make the icon through the icon pipeline (`scripts/image_pipeline/`, spec `docs/superpowers/archive/specs/2026-09-26-icon-pipeline-design.md`) in `icon_prompts.py`'s `demog` category (`demog_pip` for a pip, embossed in one colour), with the entry's `now` field naming the placeholder below. Write it to the file named here, change the texture line in both overviews (or the pip type and its key), and put that file in the row's Icon column. `IconsTest` reads the tables, so the test follows the doc.

**The rule for the set** is the UN's and Banking's: simple and easy to recognize at the size drawn, one bold object each. The cells are 44 px inside a 52 px box. The pips are 9–10 px, where only a flat mark in one colour reads, so they want a disc or a glyph rather than a picture.

## Overview cells

44 px, in reading order (left, right; then down). Each cell is the same on both hosts.

An Icon that is its row's File is final; any other is a vanilla placeholder.

| Cell | Icon | Final art | File |
|---|---|---|---|
| Natural Change | `gfx/interface/icons/generic_icons/population.dds` | a cradle and a gravestone on a balance beam | `gfx/interface/icons/demographics_icons/ov_natural_change.dds` |
| Net Migration | `gfx/interface/icons/state_status_icons/mass_migration_target.dds` | a figure with a bundle on a stick, walking past a two-way arrow | `gfx/interface/icons/demographics_icons/ov_migration.dds` |
| Life Expectancy | `gfx/interface/icons/diplomatic_treaties_articles_icons/healthcare_aid.dds` | an hourglass with a green heart in its upper bulb | `gfx/interface/icons/demographics_icons/ov_life_expectancy.dds` |
| Leading Cause of Death | `gfx/interface/icons/demographics_icons/ov_leading_cause.dds` | a plain grey headstone with red flowers at its foot, until deaths by cause are first counted; then the leading cause's icon (below) | `gfx/interface/icons/demographics_icons/ov_leading_cause.dds` |
| Fertility | `gfx/interface/icons/decree/decree_natalism_initiative.dds` | a wooden cradle with a blanket | `gfx/interface/icons/demographics_icons/ov_fertility.dds` |
| Median Age | `gfx/interface/icons/generic_icons/clock.dds` | a walking cane crossed with a child's rattle | `gfx/interface/icons/demographics_icons/ov_median_age.dds` |
| Working Age | `gfx/interface/icons/institution_icons/institution_ministry_of_labor.dds` | a hammer and a briefcase, crossed | `gfx/interface/icons/demographics_icons/ov_working_age.dds` |
| Gini Coefficient | `gfx/interface/icons/generic_icons/money.dds` | three stacks of gold coins, one tall and two short | `gfx/interface/icons/demographics_icons/ov_gini.dds` |

### The leading cause's icons

Once deaths by cause are counted (the cell's ready scripted GUI, `te_demog_dc_ready_sgui` or `te_demog_state_dc_sgui`), the Leading Cause cell hides the headstone and draws the icon of `te_dg_dc_lead`'s cause, 44 px. The codes are the pie's slices; 6, the deaths added on top, is gone since 2026-10-22, and a save that still holds it shows War, as the reading's text does. The pie's legend keeps its colour swatches: they key the slices.

| Code | Cause | Art | File |
|---|---|---|---|
| 1 | Infection, Hunger | a green germ | `gfx/interface/icons/demographics_icons/cause_infection.dds` |
| 2 | Chronic Illness | a red anatomical heart | `gfx/interface/icons/demographics_icons/cause_chronic.dds` |
| 3 | Accidents, Violence | a yellow warning triangle | `gfx/interface/icons/demographics_icons/cause_external.dds` |
| 4 | Work | a miner's yellow hard hat with its lamp | `gfx/interface/icons/demographics_icons/cause_work.dds` |
| 5 | Childbirth | a pair of pink knitted baby booties | `gfx/interface/icons/demographics_icons/cause_maternal.dds` |
| 7 | Killed by Events | a mushroom cloud over flames | `gfx/interface/icons/demographics_icons/cause_killed.dds` |
| 8 | War, Devastation | a steel helmet and a rifle on a grave mound | `gfx/interface/icons/demographics_icons/cause_war.dds` |

## History pips

Drawn over a census year's bars in every History chart, top to bottom, and again in the key under the charts.

| Pip | Icon | Size | Final art | File |
|---|---|---|---|---|
| War | `gfx/interface/icons/generic_icons/battalions.dds` | 10 px | two crossed swords, red, flat | `gfx/interface/icons/demographics_icons/pip_war.dds` |
| Famine | `gfx/interface/icons/demographics_icons/pip_famine.dds` | 10 px | an empty bowl, amber, flat | `gfx/interface/icons/demographics_icons/pip_famine.dds` |
| Demographic event | `gfx/interface/icons/generic_icons/information.dds` | 9 px | a blue disc with a white dot | `gfx/interface/icons/demographics_icons/pip_event.dds` |

## Not placeholders

- **The pie's slices**, `gfx/interface/icons/demographics_icons/pie_<cause>.dds`, are flat colour textures from `scripts/image_pipeline/gen_ch_model_pie_textures.py` (frame 1 transparent, frame 2 the colour). The eight colours are the dark categorical eight in order, which pass `validate_palette.js` against the panel's dark surface, adjacent pairs and the wrap-around alike: infection and hunger `#3987e5`, chronic illness and old age `#d95926`, accidents and violence `#199e70`, work `#c98500`, childbirth `#d55181`, added on top `#008300`, killed by events `#9085e9`, war `#e66767`. A colour changes in the generator's list, then a rerun; `PieTest` holds the slice order and the legend's swatches to it.
- **The trend arrows** are vanilla's (`trend_up.dds`, `trend_down.dds`, `trend_nochange.dds`, and the politics view's `summary_arrow_down.dds` for the coloured pair), as Banking keeps them.
