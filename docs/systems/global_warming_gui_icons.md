# Global Warming GUI: Icons

The Global Warming panels' overview and policy rows draw 17 icons of their own, plus a pie pair. They were placeholders during the style-guide pass, and PR #586 painted them. All of them live in `gfx/interface/icons/gw_icons/`. Two marks stay vanilla by design: the in-force check and Treaty-Bound.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/global_warming_widget.gui`, chosen by a display value or a scripted GUI:
- the overview's cells and pies are in `te_gw_overview_panel`;
- the policy icons are in the `row_icon` blockoverride of each `gw_policy_row` in `te_gw_sec_policies`.

No script reads the paths. Two tests guard them:
- `GwIconsTest` in `test_global_warming_layout.py` holds each tier code, role, policy and pie to its file.
- `IconsDocTest` fails when a texture in the widget is missing from this page.

**Remaking one.** The icons come from the icon pipeline (`scripts/image_pipeline/`, spec `docs/superpowers/specs/2026-09-26-icon-pipeline-design.md`):
- The painted parts are the `gw` and `gw_part` categories in `icon_prompts.py`.
- The tier and role states are the `gw_state` category: the thermometer is drawn by `_gw_tier`, and the roles are the crate part with a crown mark or a grey tint.
- Each entry's `now` field names the vanilla placeholder the icon replaced.

To change one, change its entry, re-render, review, then `write`. The pie fills are `PANEL_PIES` in `scripts/image_pipeline/gen_ch_model_pie_textures.py`. The GUI needs no edit unless a file name changes.

## Overview: warming tier

One drawn thermometer on a drawn disc with a gold rim, one per `gw_disp_tier_code`, at 36 px with the tier's coloured word beneath. The list asked for a glass thermometer on a disc warming in colour. #586 drew both parts, so that only the column and the colour change between tiers.

| Code | Tier | Shows | File |
|---|---|---|---|
| 0 | Negligible | the red column at the bulb, on a blue-green disc | `tier_negligible.dds` |
| 1 | Slight | the column a fifth up, yellow-green disc | `tier_slight.dds` |
| 2 | Moderate | two fifths up, yellow disc | `tier_moderate.dds` |
| 3 | Significant | three fifths up, orange disc | `tier_significant.dds` |
| 4 | Severe | four fifths up, red-orange disc | `tier_severe.dds` |
| 5 | Catastrophic | the column full, deep red disc | `tier_catastrophic.dds` |
| 6 | Apocalyptic | the column burst through the top, the glass cracked, on a dark red disc | `tier_apocalyptic.dds` |

## Overview: the other cells

36 px, a word beneath each.

| Cell | Shown when | Shows | File |
|---|---|---|---|
| Market Leader | we lead our market | a wooden crate of goods with a gold crown on it | `role_leader.dds` |
| Market Member | we don't | the same crate, grey, no crown | `role_member.dds` |
| Penalty | always | a tile of cracked, parched earth under a red down arrow | `penalty.dds` |
| Treaty-Bound | an Enforce Emissions Reduction treaty binds us | the treaty article's own icon (vanilla mark, kept) | `gfx/interface/icons/diplomatic_treaties_articles_icons/enforce_emissions_reduction.dds` |

## Mitigation Policies: one icon per row

26 px, at full colour while the policy is in force and 25% opacity while it is not (by design; the dimming is the state).

| Policy | Shows | File |
|---|---|---|
| Carbon Tax | a red-brick factory smokestack, a large gold coin leaning at its base | `policy_carbon_tax.dds` |
| Renewable Investment | a tilted blue solar panel with a grey wind turbine behind it | `policy_renewable_investment.dds` |
| Emission Standards | a red-brick smokestack with a round gauge on its side, the needle in the green | `policy_emission_standards.dds` |
| Climate Adaptation | a grey stone sea wall with a deep blue wave breaking against it | `policy_climate_adaptation.dds` |
| Reforestation Subsidies | a young sapling planted in a mound of earth | `policy_reforestation.dds` |
| Public Transit | a green electric tram, front view, its pantograph on top | `policy_public_transit.dds` |
| Fossil-Fuel Divestment | a black oil barrel, a gold coin flying up and away from it (the list's red arrow was left out) | `policy_fossil_fuel_divestment.dds` |
| Green Building Codes | a small red-brick building front with a bright green leaf on its wall | `policy_green_building_codes.dds` |

Beside the name, a 20 px check shows while the policy is in force (play-test round 3; it replaced the "Active"/"Inactive" word) and nothing shows while it is not. It is vanilla's `gfx/interface/icons/generic_icons/green_checkmark.dds`, kept.

## Fossil Transition: one icon per programme row

No new art (#660). Each retirement programme row shows its building's own vanilla icon, lit while the programme runs and dimmed while it does not, in the `row_icon` blockoverride of each `rt_programme_row` in `te_gw_sec_transition`. `GwIconsTest` holds each row to its file. If the icon pipeline later paints a "retiring" variant, the subject is the building's icon with a red closure mark.

| Programme | Shows | File |
|---|---|---|
| Coal mines | vanilla Coal Mine | `gfx/interface/icons/building_icons/coal_mine.dds` |
| Oil rigs | vanilla Oil Rig | `gfx/interface/icons/building_icons/oil_rig.dds` |
| Power plants | vanilla Power Plant | `gfx/interface/icons/building_icons/power_plant.dds` |

The same 20 px check as the policy rows shows while a programme runs.

## Top Emitters: the row marks

No new art. Each row starts with the leader's flag, vanilla's `tiny_flag` widget (a widget, not a texture: its name on hover, the country on click). A 20 px treaty mark shows while an Enforce Emissions Reduction treaty binds the leader; it is the Treaty-Bound cell's vanilla icon above, `gfx/interface/icons/diplomatic_treaties_articles_icons/enforce_emissions_reduction.dds`. Our own market's row says "Our market" in words.

## Overview: the temperature bar

No art. Play-test round 3 replaced the vanilla eye marker with drawn layers:
- The projection is a translucent stretch coloured by whether the change is good or bad. Warming uses vanilla `bad_progressbar_horizontal`'s red at 40%; cooling uses `green_progressbar_horizontal`'s green at 50%.
- The next tier's threshold is a 3 × 24 px line of `gfx/interface/backgrounds/white.dds` tinted cream (`color = { 0.96 0.90 0.72 0.95 }`).

The layer spec is in `te_gw_overview_panel`'s comment.

## Overview: pies

Each pie is a stacked `progresspie` pair over the UN's grey disc (`gfx/interface/icons/un_icons/pie_rest.dds`, `#8c8474`), inside vanilla's `round_frame_dec.dds`. #586 moved both fills to the nearest lighter step that clears the dataviz validator against that grey (`gen_ch_model_pie_textures.py`'s docstring has the figures). `gfx/interface/icons/un_icons/pie_members.dds` is only `te_gw_ov_pie`'s default fill, which both instances override.

| Pie | Fill | Colour | File |
|---|---|---|---|
| Our Share (of world emissions) | an antialiased disc (frame 2; frame 1 transparent) | `#e0661a`, orange | `pie_share.dds` |
| Emissions Cut | the same | `#4fb85a`, green | `pie_cut.dds` |
