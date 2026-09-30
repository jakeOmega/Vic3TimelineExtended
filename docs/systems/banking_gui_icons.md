# Banking GUI: Icons

The banking overview (`te_banking_overview_panel`, at the top of the Banking Cycle journal entry and of the Budget panel's Banking tab) draws its readings as icons, each with a caption and its word beside it. The tool rows draw one more icon, beside each tool's point cost. The icons started as placeholders in the style-guide pass: vanilla timed-modifier and generic icons, requested by the owner's first play-test (2026-09-29). PR #586 replaced them with 26 icons of the mod's own, all in `gfx/interface/icons/banking_icons/`. The momentum arrows and the crash-risk badge stay vanilla's, as the list allowed.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/banking_dashboard_widget.gui`. The cycle's three readings have a type each, `te_banking_phase_icons`, `te_banking_momentum_icons` and `te_banking_bubble_icons`, with the crash-risk badge in `te_banking_crash_risk_badge`. The overview's cells draw them at 32 px, and the top bar draws the phase at 32 px and momentum and bubble pressure at 26 px (`te_banking_topbar_readings`, instanced by `gui/topbar.gui`), so the two show the same art. The stance, price-band and budget icons are in `te_banking_overview_panel` itself, and the cost icon in `banking_dash_policy_row`'s `cost_icon` block. No script reads the paths. Two things pick an icon:
- The cycle phase uses the `banking_dash_phase_*` scripted GUI that also picks its coloured word.
- The other readings use a display code, `banking_disp_<reading>_band_code` in `common/script_values/banking_overview_display_values.txt`. Each code repeats its band word's customizable-localization tests, so the icon and the word cannot disagree.

`BankingIconsTest` in `test_banking_layout.py` holds each code to its file and fails on any placeholder left. `IconsDocTest` holds each row below to the code. `BandCodeTest` holds each code to its word.

**Remaking one.** The icons come from the icon pipeline (`scripts/image_pipeline/`, spec `docs/superpowers/specs/2026-09-26-icon-pipeline-design.md`), under the banking categories of `icon_prompts.py` that PR #586 added. Change the entry, re-render, review, then `write`. The GUI needs no edit unless a file name changes.

**The rule for the set** is the UN's: simple and easy to recognize at 32 px, one bold object each, with the states of one reading sharing an emblem and differing by a mark or a colour. The phases are one bank front, and the bubble bands one stack of coins inside a bubble. The stances are one tap. The price bands are one price tag. The pairs across the cycle mirror each other: Panic and Frenzy, Downturn and Boom, Stagnation and Expansion.

## Overview row 1: cycle phase

One emblem, a columned bank front, with a mark beside it. 32 px, the phase's coloured word beside it. Picked by `banking_dash_phase_<phase>`.

| Phase | Shows | File |
|---|---|---|
| panic | the bank front, a red double down arrow beside it | `gfx/interface/icons/banking_icons/phase_panic.dds` |
| downturn | the bank front, a red down arrow | `gfx/interface/icons/banking_icons/phase_downturn.dds` |
| stagnation | the bank front in grey stone, a flat amber bar | `gfx/interface/icons/banking_icons/phase_stagnation.dds` |
| stable | the bank front in plain stone, a level white bar | `gfx/interface/icons/banking_icons/phase_stable.dds` |
| expansion | the bank front, a green up arrow | `gfx/interface/icons/banking_icons/phase_expansion.dds` |
| boom | the bank front gilded, a blue up arrow | `gfx/interface/icons/banking_icons/phase_boom.dds` |
| frenzy | the gilded bank front, two gold coins at its foot, a red double up arrow | `gfx/interface/icons/banking_icons/phase_frenzy.dds` |

The list asked for Panic as a crowd-dark doorway with an arrow crashing through the steps, and for Frenzy's coins spilling from its arrow. At 32 px the doorway and steps were specks, so Panic got the double down arrow, the mirror of Frenzy's; Frenzy's coins lie at the bank's foot.

## Overview row 1: momentum

Vanilla's arrows, kept. 32 px, the band word beside it. Code: `banking_disp_momentum_band_code`. The double arrows mark the two bands the old table tagged "(overheating)" and "(contracting)".

| Code | Band | Shows | File |
|---|---|---|---|
| 1 | Collapsing | vanilla's double down arrow | `gfx/interface/icons/generic_icons/down_down.dds` |
| 2 | Falling | vanilla's down arrow | `gfx/interface/icons/generic_icons/trend_down.dds` |
| 3 | Steady | vanilla's level arrow | `gfx/interface/icons/generic_icons/trend_nochange.dds` |
| 4 | Rising | vanilla's up arrow | `gfx/interface/icons/generic_icons/trend_up.dds` |
| 5 | Surging | vanilla's double up arrow | `gfx/interface/icons/generic_icons/trend_upup.dds` |

## Overview row 1: bubble pressure

One emblem, a stack of gold coins inside a bubble that grows band by band, its rim changing colour. 32 px, the band word beside it. Code: `banking_disp_bubble_band_code`.

| Code | Band | Shows | File |
|---|---|---|---|
| 1 | Low | a small bubble round the coins, green rim | `gfx/interface/icons/banking_icons/bubble_low.dds` |
| 2 | Building | the bubble larger, white rim | `gfx/interface/icons/banking_icons/bubble_building.dds` |
| 3 | Elevated | larger again, yellow rim | `gfx/interface/icons/banking_icons/bubble_elevated.dds` |
| 4 | High | larger again, gold rim | `gfx/interface/icons/banking_icons/bubble_high.dds` |
| 5 | Severe | the largest bubble, red rim, a drawn crack across it | `gfx/interface/icons/banking_icons/bubble_severe.dds` |

The list asked for the bubble resting on a coin stack. A small bubble on a tall stack read as a light bulb at 32 px, so the coins went inside. Severe was to be stretched to bursting, which the renderer would not draw, so the crack is drawn.

**Crash-risk badge.** 16 px, over the bubble icon's top-right corner, while `banking_dash_bubble_risk_high` holds: the cycle is at the top of its range, or booming with momentum surging. The badge carries the old row's "(crash risk)" tag, and its tooltip says why.

| Badge | Shows | File |
|---|---|---|
| crash risk | vanilla's warning mark, kept | `gfx/interface/icons/generic_icons/warning.dds` |

## Overview row 2: policy stance

One emblem, a brass tap with a red handwheel; the coins falling from it count the stance. 32 px, the band word beside it, only for a country with a dial once the monetary layer has reported. Code: `banking_disp_stance_band_code`.

| Code | Band | Shows | File |
|---|---|---|---|
| 1 | Very Loose | the tap, four coins falling | `gfx/interface/icons/banking_icons/stance_very_loose.dds` |
| 2 | Loose | three coins | `gfx/interface/icons/banking_icons/stance_loose.dds` |
| 3 | Neutral | two coins | `gfx/interface/icons/banking_icons/stance_neutral.dds` |
| 4 | Tight | one coin | `gfx/interface/icons/banking_icons/stance_tight.dds` |
| 5 | Very Tight | no coins, a padlock on the handwheel | `gfx/interface/icons/banking_icons/stance_very_tight.dds` |

The list asked for a valve wheel at five angles. A wheel's angle does not read at 32 px, and the coin count does.

## Overview row 2: inflation (the price band)

One emblem, a paper price tag on a string, with a mark on it. 32 px, the band word beside it, only while the monetary layer is on and has reported. Code: `banking_disp_price_band_code`.

| Code | Band | Shows | File |
|---|---|---|---|
| 1 | Deflation | the tag, a blue down arrow | `gfx/interface/icons/banking_icons/price_deflation.dds` |
| 2 | Stable prices | the tag, a green level bar | `gfx/interface/icons/banking_icons/price_stable.dds` |
| 3 | Elevated | the tag, a yellow up arrow | `gfx/interface/icons/banking_icons/price_elevated.dds` |
| 4 | High | the tag, an orange double up arrow | `gfx/interface/icons/banking_icons/price_high.dds` |
| 5 | Very high | the tag, a flame beside it | `gfx/interface/icons/banking_icons/price_very_high.dds` |
| 6 | Hyperinflation | a wheelbarrow heaped with banknotes | `gfx/interface/icons/banking_icons/price_hyper.dds` |
| 7 | Foreign money | the tag with a foreign silver coin on it | `gfx/interface/icons/banking_icons/price_dollarised.dds` |
| 8 | Set by plan | the tag stamped with a red wax seal | `gfx/interface/icons/banking_icons/price_planned.dds` |

The list asked for the tag catching fire at one corner. The renderer would not set part of an object alight, so the flame is a separate part beside it.

## Overview row 2: intervention budget; tool rows: point cost

A short stack of gold tokens with one set aside. One picture in two places: 32 px in the overview's Budget cell, with "N free" beside it, and 18 px before the points in every row of Active Policies, Available Interventions and the open-market operations row. Play-test round 3 put the cost there, in place of the "At least 2 free Banking Intervention Points" column. The full line is in the row's tooltip, under Requires. The two investment-pool transfers cost GDP rather than points, so they override the `cost_icon` block empty.

| Cell | Shows | File |
|---|---|---|
| budget | a short stack of gold tokens, one aside | `gfx/interface/icons/banking_icons/budget.dds` |
| cost | the same picture at 18 px | `gfx/interface/icons/banking_icons/budget.dds` |
