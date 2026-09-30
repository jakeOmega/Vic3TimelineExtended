# Banking GUI: Icons

The banking overview (`te_banking_overview_panel`, at the top of the Banking Cycle journal entry and of the Budget panel's Banking tab) draws its readings as icons, each with a caption and its word beside it. There are 32 icon slots: one per state of six readings, plus a crash-risk badge. Since play-test round 3, the tool rows draw one more, beside each tool's point cost. All of them are placeholders (style guide rule 10): textures the mod already uses elsewhere, mostly vanilla's timed-modifier icons, chosen so the layout could be judged in game before the art exists. The owner's first play-test (2026-09-29) asked for them, starting with the inflation band. This page lists each one: where it is set, what the final art should show, and where it should go. The model is [`un_gui_icons.md`](un_gui_icons.md), which records how the UN's set went from placeholders to finished art.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/banking_dashboard_widget.gui`, inside `te_banking_overview_panel`. No script reads the paths. Each icon is picked by one of two things. The cycle phase uses the `banking_dash_phase_*` scripted GUI that also picks its coloured word. The other readings use a display code, `banking_disp_<reading>_band_code` in `common/script_values/banking_overview_display_values.txt`, which repeats its band word's customizable-localization tests, so icon and word cannot disagree. Swapping one in is one path change. `IconsDocTest` in `test_banking_layout.py` holds each row below to its code; `BandCodeTest` holds each code to its word.

**Proposed home.** `gfx/interface/icons/banking_icons/`, made with the icon pipeline (`scripts/image_pipeline/`, spec `docs/superpowers/specs/2026-09-26-icon-pipeline-design.md`) under a new `banking_*` registry category, as the UN's were.

**The rule for the set** is the UN's. Icons must be simple and easy to recognize at 32 px, one bold object each. The states of one reading share an emblem and differ by a mark or a colour. The pairs across the cycle mirror each other: Panic and Frenzy, Downturn and Boom, Stagnation and Expansion.

## Overview row 1: cycle phase

32 px, the phase's coloured word beside it. Picked by `banking_dash_phase_<phase>`.

| Phase | Placeholder | Final art | Proposed path |
|---|---|---|---|
| panic | `gfx/interface/icons/timed_modifier_icons/modifier_fire_negative.dds` | a bank's columned front with a crowd-dark doorway and a red down arrow crashing through its steps | `banking_icons/phase_panic.dds` |
| downturn | `gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds` | the bank front, a short red down arrow beside it | `banking_icons/phase_downturn.dds` |
| stagnation | `gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds` | the bank front, greyed, a flat amber line beside it | `banking_icons/phase_stagnation.dds` |
| stable | `gfx/interface/icons/event_icons/je_banking_cycle.dds` | the bank front in plain stone, a level white line beside it | `banking_icons/phase_stable.dds` |
| expansion | `gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds` | the bank front, a short green up arrow beside it | `banking_icons/phase_expansion.dds` |
| boom | `gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds` | the bank front, gilded, a tall blue up arrow beside it | `banking_icons/phase_boom.dds` |
| frenzy | `gfx/interface/icons/timed_modifier_icons/modifier_fire_positive.dds` | the gilded bank front, a red arrow shooting off the top, coins spilling from it | `banking_icons/phase_frenzy.dds` |

## Overview row 1: momentum

32 px, the band word beside it. Code: `banking_disp_momentum_band_code`. The arrows are vanilla's and can stay. The double arrows mark the two bands the old table tagged "(overheating)" and "(contracting)".

| Code | Band | Placeholder | Final art | Proposed path |
|---|---|---|---|---|
| 1 | Collapsing | `gfx/interface/icons/generic_icons/down_down.dds` | vanilla's double down arrow, may stay | (none) |
| 2 | Falling | `gfx/interface/icons/generic_icons/trend_down.dds` | vanilla's down arrow, may stay | (none) |
| 3 | Steady | `gfx/interface/icons/generic_icons/trend_nochange.dds` | vanilla's level arrow, may stay | (none) |
| 4 | Rising | `gfx/interface/icons/generic_icons/trend_up.dds` | vanilla's up arrow, may stay | (none) |
| 5 | Surging | `gfx/interface/icons/generic_icons/trend_upup.dds` | vanilla's double up arrow, may stay | (none) |

## Overview row 1: bubble pressure

32 px, the band word beside it. Code: `banking_disp_bubble_band_code`.

| Code | Band | Placeholder | Final art | Proposed path |
|---|---|---|---|---|
| 1 | Low | `gfx/interface/icons/generic_icons/green_checkmark.dds` | a small soap bubble resting on a stack of coins, green rim | `banking_icons/bubble_low.dds` |
| 2 | Building | `gfx/interface/icons/generic_icons/maybe_icon.dds` | the bubble half again as large over the coins, white rim | `banking_icons/bubble_building.dds` |
| 3 | Elevated | `gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds` | the bubble twice as large, yellow rim | `banking_icons/bubble_elevated.dds` |
| 4 | High | `gfx/interface/icons/timed_modifier_icons/modifier_fire_negative.dds` | the bubble dwarfing the coins, gold rim, a thin spot catching the light | `banking_icons/bubble_high.dds` |
| 5 | Severe | `gfx/interface/icons/generic_icons/red_cross.dds` | the bubble stretched to bursting, red rim, a crack across it | `banking_icons/bubble_severe.dds` |

**Crash-risk badge.** 16 px, over the bubble icon's top-right corner, while `banking_dash_bubble_risk_high` holds: the cycle is at the top of its range, or booming with momentum surging. The badge carries the old row's "(crash risk)" tag, and its tooltip says why.

| Badge | Placeholder | Final art | Proposed path |
|---|---|---|---|
| crash risk | `gfx/interface/icons/generic_icons/warning.dds` | vanilla's warning mark may stay; otherwise a red lightning bolt | (none) |

## Overview row 2: policy stance

32 px, the band word beside it, only for a country with a dial once the monetary layer has reported. Code: `banking_disp_stance_band_code`.

| Code | Band | Placeholder | Final art | Proposed path |
|---|---|---|---|---|
| 1 | Very Loose | `gfx/interface/icons/timed_modifier_icons/modifier_fire_positive.dds` | a brass valve wheel spun wide open, a gush of coins from the pipe | `banking_icons/stance_very_loose.dds` |
| 2 | Loose | `gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds` | the valve half open, a steady stream of coins | `banking_icons/stance_loose.dds` |
| 3 | Neutral | `gfx/interface/icons/generic_icons/money.dds` | the valve at its middle mark, a trickle | `banking_icons/stance_neutral.dds` |
| 4 | Tight | `gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds` | the valve nearly shut, a few drops | `banking_icons/stance_tight.dds` |
| 5 | Very Tight | `gfx/interface/icons/timed_modifier_icons/modifier_documents_negative.dds` | the valve shut, a padlock on the wheel | `banking_icons/stance_very_tight.dds` |

## Overview row 2: inflation (the price band)

32 px, the band word beside it, only while the monetary layer is on and has reported. Code: `banking_disp_price_band_code`. Where a band modifier has an icon of its own, the placeholder is that icon (`te_inflation_band_*` in `extra_modifiers.txt`), apart from Elevated and Hyperinflation, which borrow an icon so they read differently from their neighbours.

| Code | Band | Placeholder | Final art | Proposed path |
|---|---|---|---|---|
| 1 | Deflation | `gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds` | a price tag, a blue down arrow on it | `banking_icons/price_deflation.dds` |
| 2 | Stable prices | `gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds` | the price tag, a green level line on it | `banking_icons/price_stable.dds` |
| 3 | Elevated | `gfx/interface/icons/generic_icons/warning.dds` | the price tag, a yellow up arrow | `banking_icons/price_elevated.dds` |
| 4 | High | `gfx/interface/icons/timed_modifier_icons/modifier_fire_negative.dds` | the price tag, an orange double up arrow | `banking_icons/price_high.dds` |
| 5 | Very high | `gfx/interface/icons/timed_modifier_icons/modifier_fire_negative.dds` | the price tag catching fire at one corner | `banking_icons/price_very_high.dds` |
| 6 | Hyperinflation | `gfx/interface/icons/generic_icons/red_cross.dds` | a wheelbarrow heaped with banknotes | `banking_icons/price_hyper.dds` |
| 7 | Foreign money | `gfx/interface/icons/generic_icons/world_market.dds` | the price tag with a foreign coin pinned to it | `banking_icons/price_dollarised.dds` |
| 8 | Set by plan | `gfx/interface/icons/generic_icons/government_building_icon.dds` | the price tag stamped with an official seal | `banking_icons/price_planned.dds` |

## Overview row 2: intervention budget

32 px, "N free" beside it. One icon, always shown.

| Cell | Placeholder | Final art | Proposed path |
|---|---|---|---|
| budget | `gfx/interface/icons/diplomatic_treaties_articles_icons/bankroll_treaties.dds` | a small stack of gold counters, one set aside | `banking_icons/budget.dds` |

## Tool rows: point cost

18 px, before the points a tool holds while it is enabled, in every row of Active Policies, Available Interventions and the open-market operations row (play-test round 3 replaced the "At least 2 free Banking Intervention Points" column with it; the full line is in the row's tooltip under Requires). Set once, in `banking_dash_policy_row`'s `cost_icon` block; the two investment-pool transfers, which cost GDP rather than points, override it empty. It is the same budget emblem as the overview's Budget cell, so the two should stay one picture.

| Cell | Placeholder | Final art | Proposed path |
|---|---|---|---|
| cost | `gfx/interface/icons/diplomatic_treaties_articles_icons/bankroll_treaties.dds` | the budget's stack of gold counters at 18 px, reduced to three counters so it reads that small | `banking_icons/budget.dds` (the Budget cell's, at its small size) |
