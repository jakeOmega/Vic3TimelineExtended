# Global Warming GUI: Icons

The Global Warming panels' overview and policy rows draw 20 icons and two pie fills. All of them are placeholders for now (style guide rule 10), textures the mod already ships or already uses elsewhere, so the layout could be judged in game before the art exists. This page lists each one: where it is set, what the final art should show, and where it should go. The model is [`un_gui_icons.md`](un_gui_icons.md), which records the UN's finished set.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/global_warming_widget.gui`: the overview's cells and pies in `te_gw_overview_panel`, the policy icons in the `row_icon` blockoverride of each `gw_policy_row` in `te_gw_sec_policies`. No script reads the paths. Swapping one in is one path change. `IconsDocTest` in `test_global_warming_layout.py` fails when a texture in the widget is missing from this page.

**Proposed home.** `gfx/interface/icons/gw_icons/`, made with the icon pipeline (`scripts/image_pipeline/`, spec `docs/superpowers/specs/2026-09-26-icon-pipeline-design.md`) under a new `gw_*` registry category, as the UN's were. The UN's rule for the set applies: simple and easy to recognize at 26–36 px, one bold object each, and the states of one thing share an emblem.

## Overview: warming tier

One icon per `gw_disp_tier_code`, 36 px, the tier's coloured word beneath. All seven use the journal entry's own icon for now.

| Code | Tier | Placeholder | Final art | Proposed path |
|---|---|---|---|---|
| 0 | Negligible | `gfx/interface/icons/event_icons/je_global_warming.dds` | a glass thermometer on a pale blue-green disc, the red column at the bulb | `gw_icons/tier_negligible.dds` |
| 1 | Slight | (same) | the thermometer, column a fifth up, the disc warming to yellow-green | `gw_icons/tier_slight.dds` |
| 2 | Moderate | (same) | column two fifths up, yellow disc | `gw_icons/tier_moderate.dds` |
| 3 | Significant | (same) | column three fifths up, orange disc | `gw_icons/tier_significant.dds` |
| 4 | Severe | (same) | column four fifths up, red-orange disc | `gw_icons/tier_severe.dds` |
| 5 | Catastrophic | (same) | column full, deep red disc | `gw_icons/tier_catastrophic.dds` |
| 6 | Apocalyptic | (same) | column burst through the top, the glass cracked, a dark red disc | `gw_icons/tier_apocalyptic.dds` |

## Overview: the other cells

36 px, a word beneath each.

| Cell | Shown when | Placeholder | Final art | Proposed path |
|---|---|---|---|---|
| Market Leader | we lead our market | `gfx/interface/icons/state_status_icons/state_market_capital_icon.dds` | vanilla's market-capital mark may stay; otherwise a gold crown over a small crate of goods | `gw_icons/role_leader.dds` |
| Market Member | we don't | `gfx/interface/icons/generic_icons/world_market.dds` | the same crate without the crown, grey | `gw_icons/role_member.dds` |
| Penalty | always | `gfx/interface/icons/generic_icons/warning.dds` | a tile of cracked, parched earth under a red down arrow | `gw_icons/penalty.dds` |
| Treaty-Bound | an Enforce Emissions Reduction treaty binds us | `gfx/interface/icons/diplomatic_treaties_articles_icons/enforce_emissions_reduction.dds` | the treaty article's own icon, which may stay | (none) |

## Mitigation Policies: one icon per row

26 px, at full colour while the policy is in force and 25% opacity while it is not.

| Policy | Placeholder | Final art | Proposed path |
|---|---|---|---|
| Carbon Tax | `gfx/interface/icons/trade_icons/consumption_tax.dds` | a factory smokestack with a gold coin in front of it | `gw_icons/policy_carbon_tax.dds` |
| Renewable Investment | `gfx/interface/icons/building_icons/renewable_plant.dds` | a white wind turbine beside a blue solar panel | `gw_icons/policy_renewable_investment.dds` |
| Emission Standards | `gfx/interface/icons/decree/decree_pollution_control.dds` | a smokestack with a gauge on it, the needle in the green | `gw_icons/policy_emission_standards.dds` |
| Climate Adaptation | `gfx/interface/icons/state_status_icons/state_infrastructure.dds` | a stone sea wall holding back a wave | `gw_icons/policy_climate_adaptation.dds` |
| Reforestation | `gfx/interface/icons/decree/decree_greenest_grass_campaign.dds` | a young tree planted in a mound of earth | `gw_icons/policy_reforestation.dds` |
| Public Transit | `gfx/interface/icons/goods_icons/transportation.dds` | a green tram, front view | `gw_icons/policy_public_transit.dds` |
| Fossil-Fuel Divestment | `gfx/interface/icons/generic_icons/money.dds` | a black oil barrel with a gold coin leaving it on a red arrow | `gw_icons/policy_fossil_fuel_divestment.dds` |
| Green Building Codes | `gfx/interface/icons/production_method_icons/cat_building_green_p1.dds` | a building front with a green leaf on it | `gw_icons/policy_green_building_codes.dds` |

## Overview: pies

Each pie is a stacked `progresspie` pair over the UN's grey disc (`gfx/interface/icons/un_icons/pie_rest.dds`, which can stay), inside vanilla's `round_frame_dec.dds`. The fills borrow two of Cultural Hegemony's political-model pie textures for their colours. The final fills are two more entries in `scripts/image_pipeline/gen_ch_model_pie_textures.py`, beside `UN_PIES`, in the same colours unless the owner prefers others. `gfx/interface/icons/un_icons/pie_members.dds` is only `te_gw_ov_pie`'s default fill, which both instances override.

| Pie | Placeholder fill | Colour | Proposed path |
|---|---|---|---|
| Our Share (of world emissions) | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_corporatist.dds` | `#c56c21`, a burnt orange | `gw_icons/pie_share.dds` |
| Emissions Cut | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_developmentalist_junta.dds` | `#4ea253`, green | `gw_icons/pie_cut.dds` |
| (disc under both) | `gfx/interface/icons/un_icons/pie_rest.dds` | `#8c8474`, muted grey | may stay |
| (type default, overridden) | `gfx/interface/icons/un_icons/pie_members.dds` | — | — |
