# GUI icons wanted: the system-panel style pass

This is every icon the system-panel style pass (PRs #573–#583) draws with placeholder art today. It gathers each system's own icon list, `docs/systems/<system>_gui_icons.md` on that system's PR branch, verbatim. Those files stay the source of truth: when a system's icons change, its own file changes.

- **List 1: final.** Banking, Cultural Hegemony, Covert Warfare, Global Warming, Grand Monuments and Strategic Reserve. Their play-test round 3 is finished, so these lists should not change.
- **List 2: provisional.** Nuclear Weapons, Colonial Empire and Space Race are still in round 3, and their round-2 lists are below. Round 3 is expected to add these rows:
  - Space Race: four Interstellar Probe states (not begun, in progress, launched and awaiting data, done), replacing today's separate probe and awaiting-data icons.
  - Nuclear and Colonial: their projection bars need no art.

  A second list with the final rows for these three will follow.

**How the UN set was made, and the rules that carry over** (`docs/systems/un_gui_icons.md` on main):
- It used the icon pipeline, `scripts/image_pipeline/`, with its spec at `docs/superpowers/specs/2026-09-26-icon-pipeline-design.md` and its registry categories in `icon_prompts.py`.
- Each icon must be simple and easy to recognize at 32–40 px: one bold object.
- The states of one thing share an emblem and differ by a mark: vanilla's check, cross, plus or warning "!", or a drawn mark.
- An icon the panel dims (lit/dimmed pairs, drawn at 25% opacity) must still read when faded.

**Where to work.** The GUI code that draws these placeholders is on the PR branches, not on `main` yet. `claude/gui-style-integration` carries all of them.
- Painting the art needs only the lists: write each file to its proposed path.
- Swapping a placeholder for its art is one `texture` path change in the widget, plus the matching path in that system's layout test. Each list names the test that holds its paths.

| System | PR | Branch head | Section |
|---|---|---|---|
| Banking | #573 | `131700fb` | List 1 |
| Cultural Hegemony | #579 | `17343f26` | List 1 |
| Covert Warfare | #581 | `fbb2fcb7` | List 1 |
| Global Warming | #575 | `6696f069` | List 1 |
| Grand Monuments | #574 | `c538619c` | List 1 |
| Strategic Reserve | #576 | `831baac1` | List 1 |
| Nuclear Weapons | #577 | `5929f991` | List 2 |
| Colonial Empire | #578 | `1d56ee5a` | List 2 |
| Space Race | #580 | `0ce42e76` | List 2 |

---

## List 1: final


### Banking (#573, `docs/systems/banking_gui_icons.md` at `131700fb`)

The banking overview (`te_banking_overview_panel`, at the top of the Banking Cycle journal entry and of the Budget panel's Banking tab) draws its readings as icons, each with a caption and its word beside it. There are 32 icon slots: one per state of six readings, plus a crash-risk badge. Since play-test round 3, the tool rows draw one more, beside each tool's point cost. All of them are placeholders (style guide rule 10): textures the mod already uses elsewhere, mostly vanilla's timed-modifier icons, chosen so the layout could be judged in game before the art exists. The owner's first play-test (2026-09-29) asked for them, starting with the inflation band. This page lists each one: where it is set, what the final art should show, and where it should go. The model is [`un_gui_icons.md`](un_gui_icons.md), which records how the UN's set went from placeholders to finished art.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/banking_dashboard_widget.gui`, inside `te_banking_overview_panel`. No script reads the paths. Each icon is picked by one of two things. The cycle phase uses the `banking_dash_phase_*` scripted GUI that also picks its coloured word. The other readings use a display code, `banking_disp_<reading>_band_code` in `common/script_values/banking_overview_display_values.txt`, which repeats its band word's customizable-localization tests, so icon and word cannot disagree. Swapping one in is one path change. `IconsDocTest` in `test_banking_layout.py` holds each row below to its code; `BandCodeTest` holds each code to its word.

**Proposed home.** `gfx/interface/icons/banking_icons/`, made with the icon pipeline (`scripts/image_pipeline/`, spec `docs/superpowers/specs/2026-09-26-icon-pipeline-design.md`) under a new `banking_*` registry category, as the UN's were.

**The rule for the set** is the UN's. Icons must be simple and easy to recognize at 32 px, one bold object each. The states of one reading share an emblem and differ by a mark or a colour. The pairs across the cycle mirror each other: Panic and Frenzy, Downturn and Boom, Stagnation and Expansion.

#### Overview row 1: cycle phase

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

#### Overview row 1: momentum

32 px, the band word beside it. Code: `banking_disp_momentum_band_code`. The arrows are vanilla's and can stay. The double arrows mark the two bands the old table tagged "(overheating)" and "(contracting)".

| Code | Band | Placeholder | Final art | Proposed path |
|---|---|---|---|---|
| 1 | Collapsing | `gfx/interface/icons/generic_icons/down_down.dds` | vanilla's double down arrow, may stay | (none) |
| 2 | Falling | `gfx/interface/icons/generic_icons/trend_down.dds` | vanilla's down arrow, may stay | (none) |
| 3 | Steady | `gfx/interface/icons/generic_icons/trend_nochange.dds` | vanilla's level arrow, may stay | (none) |
| 4 | Rising | `gfx/interface/icons/generic_icons/trend_up.dds` | vanilla's up arrow, may stay | (none) |
| 5 | Surging | `gfx/interface/icons/generic_icons/trend_upup.dds` | vanilla's double up arrow, may stay | (none) |

#### Overview row 1: bubble pressure

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

#### Overview row 2: policy stance

32 px, the band word beside it, only for a country with a dial once the monetary layer has reported. Code: `banking_disp_stance_band_code`.

| Code | Band | Placeholder | Final art | Proposed path |
|---|---|---|---|---|
| 1 | Very Loose | `gfx/interface/icons/timed_modifier_icons/modifier_fire_positive.dds` | a brass valve wheel spun wide open, a gush of coins from the pipe | `banking_icons/stance_very_loose.dds` |
| 2 | Loose | `gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds` | the valve half open, a steady stream of coins | `banking_icons/stance_loose.dds` |
| 3 | Neutral | `gfx/interface/icons/generic_icons/money.dds` | the valve at its middle mark, a trickle | `banking_icons/stance_neutral.dds` |
| 4 | Tight | `gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds` | the valve nearly shut, a few drops | `banking_icons/stance_tight.dds` |
| 5 | Very Tight | `gfx/interface/icons/timed_modifier_icons/modifier_documents_negative.dds` | the valve shut, a padlock on the wheel | `banking_icons/stance_very_tight.dds` |

#### Overview row 2: inflation (the price band)

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

#### Overview row 2: intervention budget

32 px, "N free" beside it. One icon, always shown.

| Cell | Placeholder | Final art | Proposed path |
|---|---|---|---|
| budget | `gfx/interface/icons/diplomatic_treaties_articles_icons/bankroll_treaties.dds` | a small stack of gold counters, one set aside | `banking_icons/budget.dds` |

#### Tool rows: point cost

18 px, before the points a tool holds while it is enabled, in every row of Active Policies, Available Interventions and the open-market operations row (play-test round 3 replaced the "At least 2 free Banking Intervention Points" column with it; the full line is in the row's tooltip under Requires). Set once, in `banking_dash_policy_row`'s `cost_icon` block; the two investment-pool transfers, which cost GDP rather than points, override it empty. It is the same budget emblem as the overview's Budget cell, so the two should stay one picture.

| Cell | Placeholder | Final art | Proposed path |
|---|---|---|---|
| cost | `gfx/interface/icons/diplomatic_treaties_articles_icons/bankroll_treaties.dds` | the budget's stack of gold counters at 18 px, reduced to three counters so it reads that small | `banking_icons/budget.dds` (the Budget cell's, at its small size) |


### Cultural Hegemony (#579, `docs/systems/cultural_hegemony_gui_icons.md` at `17343f26`)

The overview at the top of the Cultural Hegemony panels draws three kinds of art that are placeholders today (`gui_style_guide.md` rule 10). The overview is `te_ch_overview_panel` in `gui/journal_entry_widgets/cultural_hegemony_widget.gui`, shown in the journal entry and in the Society panel's Hegemony tab. This file lists each placeholder, what the final art should show and where it should go, as `un_gui_icons.md` did for the UN before its set was made.

**Where each is set.** Every one is a literal `texture = "…"` line in `cultural_hegemony_widget.gui`, chosen by a display value's code (`ch_disp_tier_code`) or a scripted GUI (`ch_benchmark_sgui`). No script reads the paths. `PlaceholderTest` in `test_cultural_hegemony_layout.py` holds each current path to this file and to the proposed one, so swapping in the final art is a path change in the `.gui` and in the test's `PLACEHOLDERS`, and a row moved here from the placeholder tables to the finished one.

**The rule for the set** is the UN's: simple and easy to recognize at 36 px. One bold object per icon; states of one thing share an emblem and differ by a mark, a metal or a size. The icons would come from the icon pipeline (`scripts/image_pipeline/`, as the UN set did), the pie pair from `scripts/image_pipeline/gen_ch_model_pie_textures.py`.

#### Overview: influence tier

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

#### Overview: Foreign Cultural Benchmark

Shown at 36 px, only while the country carries `cultural_hegemony_foreign_benchmark` (the legitimacy penalty for trailing the leading cultural power), the red word "Benchmark" beneath it. **Placeholder now:** vanilla's warning mark, `gfx/interface/icons/generic_icons/warning.dds`.

| Final art shows | Proposed path |
|---|---|
| a small grey sceptre in the shadow of a large gold laurel wreath, a red downward arrow beside the sceptre | `gfx/interface/icons/ch_icons/benchmark.dds` |

#### Overview: our cultural share (pie pair)

Our share of global cultural influence as a framed pie, 62 px inside `round_frame_dec.dds`, drawn as two stacked `progresspie`s: a full disc for the rest of the world and our share on top. **Placeholder now:** two of the political-models pie's own slice textures, the Mixed / Other grey as the rest and the Liberal gold as our share. The overview's pie therefore shares its colours with two slices of the models pie further down the panel, which is the reason to replace them.

Both in the pie format (`gui_modding_guide.md`, "Pie charts of script-held data"): frame 1 fully transparent, frame 2 an antialiased disc. Add them to `gen_ch_model_pie_textures.py` the way it writes `UN_PIES`, and validate the pair against the dark panel as it validated the UN's.

| Layer | Placeholder now | Final art shows | Proposed path |
|---|---|---|---|
| Our share (fill) | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_liberal.dds` | a disc in the amber of the share history chart's bars (`color = { 0.78 0.60 0.30 }`, about `#c79a4d`) | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_share_fill.dds` |
| The rest (disc) | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_other.dds` | a disc in a muted warm grey, as the UN's `pie_rest` | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_share_rest.dds` |

#### Not placeholders

- **The exported model's disc.** The overview shows the leading power's political model as that model's slice texture from the models pie (`ch_pie_<model>.dds`, frame 2), so the colour matches the pie and its legend. That is by design. A drawn emblem per model would be a new set of fifteen, not a swap.
- **The trend arrows** are vanilla's `trend_up` / `trend_down` / `trend_nochange`, as the UN's pillar rows use them.
- **World rank** is a number, with no icon.
- **The leading powers** are vanilla's `flag` widget, drawn from the capitals the viewer holds (`ch_leader_seat_1..3`), as the UN overview draws its Security Council.


### Covert Warfare (#581, `docs/systems/covert_gui_icons.md` at `fbb2fcb7`)

The Covert Warfare journal entry's overview draws fourteen icons of its own. All of them are vanilla placeholders or the entry's own icon, chosen so the layout can be judged in game before the art exists (`gui_style_guide.md` rule 10). This page lists them for the icon pipeline.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/covert_operations_widget.gui`: the overview's first row (`te_covert_overview_panel`, one `covert_ov_icon_label` per standing code, two for funding, one per Tradecraft tier, one for a recent catch) and the slot icon (`covert_ov_slot`, drawn ten times). No script reads the paths. `IconsTest` in `test_covert_layout.py` holds each placeholder to the path this page lists and fails if the overview uses a texture it doesn't know.

**Swapping one in.** Render it, write it to the proposed path, then change the path in the widget and in `test_covert_layout.py`'s `STANDING_ICONS` / `TRADECRAFT_ICONS` / `OTHER_ICONS`. The slot icon is drawn at 25% opacity while the slot is free, so it must still read when faded, like the UN's agencies.

**Style.** Shown at 36 px (the slot at 26 px), beside the UN's overview icons, so the same rule applies: one bold object, easy to recognise at that size (`un_gui_icons.md`). The five standings are states of one thing, so they share an emblem, a round steel shield with a closed eye on it, and differ by its state, the way the UN's membership icons share the wreath. The five Tradecraft tiers are one agent's rise, so they share an emblem too: a black fedora on a leather dossier, with a gold chevron under it per tier.

| Icon (code) | Where | Placeholder now | Final art should show (icon-pipeline subject) | Proposed path |
|---|---|---|---|---|
| Standing: Fortress (4) | overview, first row | `gfx/interface/icons/generic_icons/green_checkmark.dds` | a round steel shield with a closed eye embossed on it, whole and polished, with a gold rim | `gfx/interface/icons/covert_icons/standing_fortress.dds` |
| Standing: Hardened (3) | overview, first row | `gfx/interface/icons/generic_icons/approval_icon.dds` | the same shield, whole, with a plain silver rim | `gfx/interface/icons/covert_icons/standing_hardened.dds` |
| Standing: Defended (2) | overview, first row | `gfx/interface/icons/generic_icons/undecided_icon.dds` | the same shield in dull iron, dented, the eye still closed | `gfx/interface/icons/covert_icons/standing_defended.dds` |
| Standing: Exposed (1) | overview, first row | `gfx/interface/icons/generic_icons/disapproval_icon.dds` | the same shield cracked across, the eye half open | `gfx/interface/icons/covert_icons/standing_exposed.dds` |
| Standing: Vulnerable (0) | overview, first row | `gfx/interface/icons/generic_icons/red_cross.dds` | the same shield split in two, the eye wide open | `gfx/interface/icons/covert_icons/standing_vulnerable.dds` |
| Funding, level 0 (Dormant) | overview, first row | `gfx/interface/icons/generic_icons/warning.dds` | an open, empty manila envelope with a torn red "classified" band, grey | `gfx/interface/icons/covert_icons/funding_dormant.dds` |
| Funding, levels 1-5 | overview, first row | `gfx/interface/icons/generic_icons/gdp.dds` | a sealed manila envelope with a red "classified" band and a thick stack of banknotes showing at its edge | `gfx/interface/icons/covert_icons/funding.dds` |
| Tradecraft: Untested (0) | overview, first row | `gfx/interface/icons/generic_icons/maybe_icon.dds` | a black fedora resting on a closed leather dossier, no chevron | `gfx/interface/icons/covert_icons/tradecraft_0.dds` |
| Tradecraft: Fledgling (1) | overview, first row | `gfx/interface/icons/generic_icons/population.dds` | the same fedora and dossier, one gold chevron beneath | `gfx/interface/icons/covert_icons/tradecraft_1.dds` |
| Tradecraft: Established (2) | overview, first row | `gfx/interface/politics_view/institution_level_icon.dds` | the same, two gold chevrons | `gfx/interface/icons/covert_icons/tradecraft_2.dds` |
| Tradecraft: Seasoned (3) | overview, first row | `gfx/interface/icons/formation_order_icons/upgrade.dds` | the same, three gold chevrons | `gfx/interface/icons/covert_icons/tradecraft_3.dds` |
| Tradecraft: Veteran (4) | overview, first row | `gfx/interface/icons/generic_icons/most_senior_front_commander.dds` | the same, four gold chevrons and a gold band on the hat | `gfx/interface/icons/covert_icons/tradecraft_4.dds` |
| Spy Caught (while a catch from the last ten years stands) | overview, first row | `gfx/interface/icons/military_icons/navy_icons/detection_navy.dds` | a trench-coated silhouette caught in the white beam of a searchlight | `gfx/interface/icons/covert_icons/spy_caught.dds` |
| Operation slot (lit in use, faded free) | overview, second row, ten times | `gfx/interface/icons/event_icons/je_covert_warfare.dds` | a plain manila case file with a photograph paper-clipped to its cover | `gfx/interface/icons/covert_icons/operation_slot.dds` |

Not placeholders: each operation row's icon is that operation's own diplomatic-action icon (`gfx/interface/icons/diplomatic_action_icons/covert_<type>_action.dds`), and the trend arrows and bar markers are vanilla's (`trend_up` / `trend_down` / `trend_nochange`, `progressbar_marker`), as in the UN's panels.

The Tradecraft icon is picked by `covert_tradecraft_tier` (owner, round 2: one icon per tier), as the standing icon is by `covert_disp_standing_code`.

Each network row leads with its target's flag, vanilla's `flag` widget; that is not a placeholder either.


### Global Warming (#575, `docs/systems/global_warming_gui_icons.md` at `6696f069`)

The Global Warming panels' overview and policy rows draw 21 icons and two pie fills. All of them are placeholders for now (style guide rule 10), textures the mod already ships or already uses elsewhere, so the layout could be judged in game before the art exists. This page lists each one: where it is set, what the final art should show, and where it should go. The model is [`un_gui_icons.md`](un_gui_icons.md), which records the UN's finished set.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/global_warming_widget.gui`: the overview's cells and pies in `te_gw_overview_panel`, the policy icons in the `row_icon` blockoverride of each `gw_policy_row` in `te_gw_sec_policies`. No script reads the paths. Swapping one in is one path change. `IconsDocTest` in `test_global_warming_layout.py` fails when a texture in the widget is missing from this page.

**Proposed home.** `gfx/interface/icons/gw_icons/`, made with the icon pipeline (`scripts/image_pipeline/`, spec `docs/superpowers/specs/2026-09-26-icon-pipeline-design.md`) under a new `gw_*` registry category, as the UN's were. The UN's rule for the set applies: simple and easy to recognize at 26–36 px, one bold object each, and the states of one thing share an emblem.

#### Overview: warming tier

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

#### Overview: the other cells

36 px, a word beneath each.

| Cell | Shown when | Placeholder | Final art | Proposed path |
|---|---|---|---|---|
| Market Leader | we lead our market | `gfx/interface/icons/state_status_icons/state_market_capital_icon.dds` | vanilla's market-capital mark may stay; otherwise a gold crown over a small crate of goods | `gw_icons/role_leader.dds` |
| Market Member | we don't | `gfx/interface/icons/generic_icons/world_market.dds` | the same crate without the crown, grey | `gw_icons/role_member.dds` |
| Penalty | always | `gfx/interface/icons/generic_icons/warning.dds` | a tile of cracked, parched earth under a red down arrow | `gw_icons/penalty.dds` |
| Treaty-Bound | an Enforce Emissions Reduction treaty binds us | `gfx/interface/icons/diplomatic_treaties_articles_icons/enforce_emissions_reduction.dds` | the treaty article's own icon, which may stay | (none) |

#### Mitigation Policies: one icon per row

26 px, at full colour while the policy is in force and 25% opacity while it is not. Beside the name, a 20 px check shows while the policy is in force (play-test round 3; it replaced the "Active"/"Inactive" word) and nothing shows while it is not.

| State | Placeholder | Final art | Proposed path |
|---|---|---|---|
| In force (the check) | `gfx/interface/icons/generic_icons/green_checkmark.dds` | vanilla's green check may stay; otherwise a small green check on a dark disc, legible at 20 px | `gw_icons/policy_in_force.dds` |
| Not in force | (nothing drawn) | none needed | — |


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

#### Overview: the temperature bar

No art. Play-test round 3 replaced the vanilla eye marker with drawn layers: the projection as a translucent stretch coloured by whether the change is good or bad (warming: vanilla `bad_progressbar_horizontal`'s red at 40%; cooling: `green_progressbar_horizontal`'s green at 50%) and the next tier's threshold as a 3 × 24 px line of `gfx/interface/backgrounds/white.dds` tinted cream (`color = { 0.96 0.90 0.72 0.95 }`). The layer spec is in `te_gw_overview_panel`'s comment.

#### Overview: pies

Each pie is a stacked `progresspie` pair over the UN's grey disc (`gfx/interface/icons/un_icons/pie_rest.dds`, which can stay), inside vanilla's `round_frame_dec.dds`. The fills borrow two of Cultural Hegemony's political-model pie textures for their colours. The final fills are two more entries in `scripts/image_pipeline/gen_ch_model_pie_textures.py`, beside `UN_PIES`, in the same colours unless the owner prefers others. `gfx/interface/icons/un_icons/pie_members.dds` is only `te_gw_ov_pie`'s default fill, which both instances override.

| Pie | Placeholder fill | Colour | Proposed path |
|---|---|---|---|
| Our Share (of world emissions) | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_corporatist.dds` | `#c56c21`, a burnt orange | `gw_icons/pie_share.dds` |
| Emissions Cut | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_developmentalist_junta.dds` | `#4ea253`, green | `gw_icons/pie_cut.dds` |
| (disc under both) | `gfx/interface/icons/un_icons/pie_rest.dds` | `#8c8474`, muted grey | may stay |
| (type default, overridden) | `gfx/interface/icons/un_icons/pie_members.dds` | — | — |


### Grand Monuments (#574, `docs/systems/grand_monuments_gui_icons.md` at `c538619c`)

The Monuments journal entry's overview and its monument rows draw five status icons. All five are vanilla placeholders, chosen so the layout can be judged in game before the art exists (`gui_style_guide.md` rule 10). This page lists them for the icon pipeline.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/grand_monuments_widget.gui`: the overview's cells (`te_gm_overview_panel`, one `gm_ov_cell` per status), the Hard Times line under them, and a monument row's status (`gm_monument_row`, one `gm_row_status` per `gm_status_code`). A status uses the same texture in both places. No script reads the paths. `IconsTest` in `test_grand_monuments_layout.py` holds each code to its path in its `ICONS` table and fails if the widget uses a texture the table doesn't list.

**Swapping one in.** Render it, write it to the proposed path, then change the path in the widget and in `ICONS`. The overview dims a cell to 25% opacity while its count is zero, so each icon must still read when faded, like the UN's agencies.

**Style.** Shown at 36 px (Hard Times at 32), beside the UN's overview icons, so the same rule applies: one bold object, easy to recognise at that size (`un_gui_icons.md`). The four statuses are states of one monument, so they could share an emblem (a small column on a plinth) and differ by a mark, the way the UN's membership icons share the wreath.

| Status (code) | Where | Placeholder now | Final art should show (icon-pipeline subject) | Proposed path |
|---|---|---|---|---|
| Undedicated (1) | overview cell; row status | `gfx/interface/icons/generic_icons/undecided_icon.dds` | a plain stone monument on a plinth, bare, with an empty panel where a dedication would be carved | `gfx/interface/icons/gm_icons/status_undedicated.dds` |
| Upheld (2) | overview cell; row status | `gfx/interface/icons/generic_icons/green_checkmark.dds` | the same monument in bright stone with a gold laurel wreath hung on its face | `gfx/interface/icons/gm_icons/status_upheld.dds` |
| Heritage (3) | overview cell; row status | `gfx/interface/icons/generic_icons/maybe_icon.dds` | the same monument, weathered and mossy, behind a low bronze railing | `gfx/interface/icons/gm_icons/status_heritage.dds` |
| Contested (4) | overview cell; row status | `gfx/interface/icons/generic_icons/disapproval_icon.dds` | the same monument with a thick rope thrown around its top and a crack down its face | `gfx/interface/icons/gm_icons/status_contested.dds` |
| Hard Times | its own line under the overview's cells, over the red phrase, only while it holds | `gfx/interface/icons/generic_icons/warning.dds` | an empty wooden alms bowl beside a stonemason's idle chisel and mallet | `gfx/interface/icons/gm_icons/hard_times.dds` |

"Unsettled", the brief state between a change of government and the month's check, shares code 2 and so shows the Upheld icon with its own word beneath.


### Strategic Reserve (#576, `docs/systems/strategic_reserve_gui_icons.md` at `831baac1`)

The Strategic Reserve panel (`gui/journal_entry_widgets/strategic_reserve_widget.gui`, restyled to `docs/guides/gui_style_guide.md` in September 2026) draws six icons of its own. One is final art and five are vanilla placeholders, per style rule 10. This list is what to replace, and with what.

**Where each is set.** Each is a literal `texture = "…"` line in `strategic_reserve_widget.gui`. No script reads the paths. Swapping a placeholder is one path change per `texture` line listed below.

#### Final

| Where | Shows | File |
|---|---|---|
| Overview, hub cell (`te_st_res_overview_panel`), 36 px, twice: dimmed underneath, lit on top while the hub is fully staffed | the hub building's own icon | `gfx/interface/icons/building_icons/building_strategic_reserve_hub.dds` |

The bar markers use vanilla's `gfx/interface/progressbar/progressbar_marker.dds`, the marker the UN authority bar uses. It is interface chrome rather than an icon, and stays.

#### Placeholders

| Where | Placeholder | Final art should show (icon-pipeline subject) | Proposed path |
|---|---|---|---|
| Inventory row, policy icon (`te_st_res_good_row`, the two `icon` widgets in the 30 px cell after the status icon), 24 px. Drawn at alpha 0.25 on Manual, and again at full colour on top while a reserve policy runs the good | vanilla's `gfx/interface/production_methods/auto_expand.dds`, the building auto-expand toggle | A brass centrifugal governor: two weighted arms on a spindle, flat and bold, in the gold of vanilla's goods icons, readable at 24 px. It says "regulates itself". One file serves both states, since the dimmed state is the same texture at low alpha. | `gfx/interface/icons/st_res_icons/policy_automated.dds` |


The icon must stay legible at alpha 0.25, so the silhouette matters more than detail.

##### Status icons (round 3, 2026-09-30)

The owner asked for the status column as icons. The four share the 30 px cell after the fill bar in `te_st_res_good_row`, each at 24 px with its own `visible` on one value of `st_res_<good>_disp_status`, so exactly one is drawn. The status word (coloured as below) and its reason are on the cell's hover. One emblem for the set, a small supply crate, with the state shown by a mark in the word's colour, so the four read as one family.

| State (code) | Placeholder | Final art should show (icon-pipeline subject) | Proposed path |
|---|---|---|---|
| Idle (0) | vanilla's `gfx/interface/icons/generic_icons/trend_nochange.dds` | A closed wooden supply crate with a flat yellow bar across its front: the stock is held, nothing moving. | `gfx/interface/icons/st_res_icons/status_idle.dds` |
| Storing (1) | vanilla's `gfx/interface/icons/generic_icons/trend_up.dds` | The same crate with a bold green arrow pointing down into its open top: goods going in. | `gfx/interface/icons/st_res_icons/status_storing.dds` |
| Withdrawing (2) | vanilla's `gfx/interface/icons/generic_icons/trend_down.dds` | The same crate with a bold orange arrow rising out of its open top: goods coming out. | `gfx/interface/icons/st_res_icons/status_withdrawing.dds` |
| Blocked (3) | vanilla's `gfx/interface/icons/generic_icons/warning.dds` | The same crate with a red barrier bar across it: the lane cannot move (full, empty, or the hub understaffed). | `gfx/interface/icons/st_res_icons/status_blocked.dds` |

The placeholders are the trend arrows the UN pillars use and vanilla's warning mark, so they read as up, down, level and stop until the art exists.


---

## List 2: provisional (round 3 in progress)


### Nuclear Weapons (#577, `docs/systems/nuclear_gui_icons.md` at `5929f991`)

The overview at the top of the Nuclear Weapons journal entry (`je_nuclear_program`) draws 24 icons: one per state of the programme and of the posture, plus the warheads and crisis cells. All of them are placeholders: textures the mod or vanilla already uses elsewhere, chosen so the layout can be judged in game before the art exists (style guide rule 10). This page lists every one, what the final art should show and a proposed path, as `un_gui_icons.md` did for the UN before PR #572 replaced its placeholders.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/nuclear_overview_widget.gui`, one icon widget per state, picked by a display value's code (`EqualTo_CFixedPoint( …ScriptValue('<code value>'), '(CFixedPoint)N' )`). No script reads the paths, so swapping one in is one path change. `OverviewTest` in `test_nuclear_layout.py` checks that each code draws exactly one icon and that every texture in the overview is listed on this page.

**The rule for the set** (from the UN's): simple and easy to recognize at 36 px. The states of one thing share an emblem and differ by a mark. Proposed home: `gfx/interface/icons/nuclear_icons/`.

#### Row 1: the programme

Code: `nuclear_program_display_state` (`common/script_values/extra_script_values.txt`), in the order of the status line's programme sentence (`nuclear_program_status_line`). The cell's hover is that sentence.

| Code | State | Placeholder now | Final art should show | Proposed file |
|---|---|---|---|---|
| 0 | Unfunded | `gfx/interface/icons/generic_icons/paused.dds` | a steel warhead casing on a cradle, grey, under a drawn pause mark | `programme_unfunded.dds` |
| 1 | Developing (first device) | `gfx/interface/icons/invention_icons/nuclear_weapons.dds` | the warhead casing with an open inspection panel and a brass wrench beside it | `programme_developing.dds` |
| 2 | Producing (series production) | `gfx/interface/icons/event_icons/mushroom_cloud.dds` | three identical steel warheads standing in a row | `programme_producing.dds` |
| 3 | Frozen (pause treaty) | `gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_program_pause.dds` | the warhead casing behind a blue ribbon with a wax treaty seal | `programme_frozen.dds` |
| 4 | At ceiling | `gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_arms_limitation.dds` | a row of warheads under a flat gold bar at their tips | `programme_at_ceiling.dds` |
| 5 | Dismantling | `gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_disarmament.dds` | the warhead casing split in two halves, a wrench between them | `programme_dismantling.dds` |
| 6 | No programme | `gfx/interface/icons/invention_icons/nuclear_weapons.dds` (30% opacity) | the warhead casing, faint grey, no mark | `programme_none.dds` |
| 7 | Renounced | `gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_disarmament.dds` | a white dove over a broken warhead casing | `programme_renounced.dds` |
| 8 | Disarmed (settlement or NPT) | `gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_disarmament.dds` (30% opacity) | the warhead casing, grey, under vanilla's red cross | `programme_disarmed.dds` |

#### Row 1: warheads and the crisis

| Cell | Shown | Placeholder now | Final art should show | Proposed file |
|---|---|---|---|---|
| Warheads | always | `gfx/interface/icons/invention_icons/guided_missiles.dds` | a single steel warhead, nose up, with a small radiation trefoil | `warheads.dds` |
| Crisis | while in one | `gfx/interface/icons/diplomatic_action_icons/nd_nuclear_ultimatum_action.dds` | the warhead under vanilla's warning mark, on a red disc | `crisis.dds` |

The credibility cell is a meter, not an icon.

#### Row 2: the posture (while armed)

Codes: `nd_display_doctrine_code`, `nd_display_readiness_code`, `nd_display_authority_code` (`common/script_values/nuclear_deterrence_values.txt`), falling back as the name blocks in `nuclear_deterrence_custom_loc.txt` do. Each cell's hover is the posture row's own tooltip.

| Axis | Code | State | Placeholder now | Final art should show | Proposed file |
|---|---|---|---|---|---|
| Doctrine | 1 | No First Use | `gfx/interface/icons/diplomatic_treaties_articles_icons/crisis_resolution.dds` | a warhead inside a closed gold shield | `doctrine_nfu.dds` |
| Doctrine | 2 | Existential Deterrence | `gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_guarantee.dds` | a warhead behind a stone wall, nose up | `doctrine_existential.dds` |
| Doctrine | 3 | Flexible First Use | `gfx/interface/icons/diplomatic_action_icons/nd_nuclear_warning_action.dds` | a warhead tilted forward on a half-drawn shield | `doctrine_flexible.dds` |
| Doctrine | 4 | Nuclear Compellence | `gfx/interface/icons/diplomatic_action_icons/nd_nuclear_ultimatum_action.dds` | a warhead pointing right past a raised gauntlet | `doctrine_compellence.dds` |
| Doctrine | 5 | Nuclear Warfighting | `gfx/interface/icons/invention_icons/tactical_nuclear_weapons.dds` | a warhead crossed with a sword | `doctrine_warfighting.dds` |
| Readiness | 0 | Recessed | `gfx/interface/buttons/button_icons/lock.dds` | a warhead in a locked steel crate | `readiness_recessed.dds` |
| Readiness | 1 | Routine | `gfx/interface/icons/commander_order_icons/standby.dds` | a missile lying flat on its launcher, green lamp | `readiness_routine.dds` |
| Readiness | 2 | Heightened | `gfx/interface/icons/generic_icons/warning.dds` | the missile raised halfway, amber lamp | `readiness_heightened.dds` |
| Readiness | 3 | High Alert | `gfx/interface/icons/generic_icons/mobilize_icon_single.dds` | the missile upright on its launcher, red lamp | `readiness_high_alert.dds` |
| Launch authority | 1 | Central Authorization | `gfx/interface/icons/generic_icons/government_building_icon.dds` | a single brass key in a government seal | `authority_central.dds` |
| Launch authority | 2 | Conditional Delegation | `gfx/interface/icons/generic_icons/most_senior_front_commander.dds` | the brass key handed from a gloved hand to an officer's | `authority_delegation.dds` |
| Launch authority | 3 | Launch on Warning | `gfx/interface/icons/lens_toolbar_icons/nd_nuclear_warning_action.dds` | a radar dish with the brass key under it | `authority_on_warning.dds` |
| Launch authority | 4 | Automatic Retaliation | `gfx/interface/icons/generic_icons/observer_mode_icon.dds` | a grey machine cabinet with the brass key turned in it, red lamp | `authority_automatic.dds` |

#### Row 3: the nuclear taboo

No placeholder: the bar and its target marker are vanilla's (`progressbar_marker.dds`, as the UN overview's authority bar uses), and the trend arrow is vanilla's `trend_up` / `trend_down` / `trend_nochange`, picked by `nd_disp_taboo_trend`.


### Colonial Empire (#578, `docs/systems/colonial_empire_gui_icons.md` at `1d56ee5a`)

The Colonial Empire overview (`te_ce_overview_panel` in `gui/journal_entry_widgets/colonial_empire_widget.gui`) draws ten icons and a two-slice pie with its legend. All of them are **placeholders**: vanilla textures, or textures of other systems, that another `.gui` of this mod already uses, so the layout could be judged in game before the art exists (style rule 10, `docs/guides/gui_style_guide.md`). This page lists each one for the icon pipeline. `docs/systems/un_gui_icons.md` records how the UN's set went from placeholders to finished art.

**Where each is set.** Every icon is a literal `texture = "…"` line in `te_ce_overview_panel`, chosen by a display value's code (`colonial_empire_disp_tier`, `colonial_empire_disp_pressure_level`) or by a programme's scope-free handler (`colonial_empire_active_*_sgui`). No script reads the paths. Swapping one in is one path change; when the art lands, add a test that holds each code to its file, as `UnIconsTest` does for the UN.

**The rule for the set** is the UN's: simple and easy to recognise at 36 px. One bold object each; the states of one thing share an emblem and differ by a mark or a colour.

#### Overview: the stability band

Shown at 36 px, the band's name beneath. One per band, picked by `colonial_empire_disp_tier`.

| Code | Band | Placeholder now | Final art should show | Proposed path |
|---|---|---|---|---|
| 5 | Solidified | `gfx/interface/icons/state_status_icons/state_homelands.dds` | a small globe with an overseas coast joined to the home coast by a gold band, full colour | `gfx/interface/icons/colonial_empire_icons/band_solidified.dds` |
| 4 | Stable | `gfx/interface/icons/state_status_icons/incorporated_state.dds` | the same globe, the coasts joined by a thinner gold line | `…/band_stable.dds` |
| 3 | Strained | `gfx/interface/icons/generic_icons/warning.dds` | the same globe, the line between the coasts pulled taut and amber | `…/band_strained.dds` |
| 2 | Crumbling | `gfx/interface/icons/state_status_icons/has_turmoil.dds` | the same globe, the line cracked and red | `…/band_crumbling.dds` |
| 1 | Collapsing | `gfx/interface/icons/war_goals/independence.dds` | the same globe, the line broken in two, the overseas coast in a new flag's colour | `…/band_collapsing.dds` |

#### Overview: great-power pressure

The alert beside the pie while an escalation applies, 36 px, its word beneath. Picked by `colonial_empire_disp_pressure_level`.

| Code | State | Placeholder now | Final art should show | Proposed path |
|---|---|---|---|---|
| 1 | Diplomatic isolation | `gfx/interface/icons/generic_icons/disapproval_icon.dds` | a lone colonial flag on a pole inside a ring of turned-away figures, amber | `…/alert_isolation.dds` |
| 2 | International consensus | `gfx/interface/icons/generic_icons/red_cross.dds` | a round table of great-power flags with raised hands against one flag, red | `…/alert_consensus.dds` |

#### Overview: the programmes

A row of three, 36 px, at full colour while the programme runs and 25% opacity while it does not.

| Programme | Placeholder now | Final art should show | Proposed path |
|---|---|---|---|
| Colonial Development Investment | `gfx/interface/icons/building_icons/building_browser_filter_icons/filter_icons_development.dds` | a railway bridge under construction over a tropical river, a crane beside it | `…/programme_invest.dds` |
| Military Garrison | `gfx/interface/icons/generic_icons/battalions.dds` | a colonial fort's gate with a sentry and a flag | `…/programme_garrison.dds` |
| Cultural Assimilation Programme | `gfx/interface/population/pop_culture.dds` | a schoolhouse with an open primer on its steps | `…/programme_assimilation.dds` |

#### Overview: the great-power pie

Great-power prestige (ours included) as a stacked `progresspie` in vanilla's `round_frame_dec.dds`: the condemning powers' share (`colonial_empire_disp_condemner_share`) and, in its own colour, the supporting powers' share (the supporters' layer fills to `colonial_empire_disp_pressure_cum`, the sum, under the condemners'). The legend beside it uses the same two textures as swatches. The textures are frame 1 transparent, frame 2 the colour (`gui_modding_guide.md`, "Pie charts of script-held data"); `scripts/image_pipeline/gen_ch_model_pie_textures.py` writes both kinds.

| Layer | Placeholder now | Final | Proposed path |
|---|---|---|---|
| The condemners' share (the top fill, and its swatch) | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_communist.dds` (Cultural Hegemony's red, `#c44039`) | a red of its own, generated beside the UN's pair | `…/pie_condemners.dds` |
| The supporters' share (the lower fill, and its swatch) | `gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_developmentalist_junta.dds` (Cultural Hegemony's green, `#4ea253`) | a green of its own | `…/pie_supporters.dds` |
| The rest (the disc under both) | `gfx/interface/icons/un_icons/pie_rest.dds` (the UN's muted grey) | can stay the UN's disc, or a copy of it | `…/pie_rest.dds` |


### Space Race (#580, `docs/systems/space_race_gui_icons.md` at `0ce42e76`)

The Space Race panels' overview (the GUI style guide pass, September 2026) draws a handful of icons of its own. All of them are vanilla or borrowed placeholders for now, so the layout can be judged in game before the art exists (`gui_style_guide.md` rule 10). The programme row's seven single-state icons are not placeholders: they are the journal-entry icons painted in PR #571 (`gfx/interface/icons/event_icons/je_space_race_<m>.dds`). Its interstellar icon, which has four states, borrows two of them for now (below).

**Where each is set.** Every placeholder is a literal `texture = "…"` line in `gui/journal_entry_widgets/space_race_widget.gui`, in the type named below. No script reads the paths, so swapping one in is one path change. The proposed paths are new files under `gfx/interface/icons/space_race_icons/`.

**The rule for the set** is the UN's (`un_gui_icons.md`): simple and easy to recognize at 32–40 px. The five state icons share one emblem, a rocket on its pad, and differ by what surrounds it.

#### Overview: the milestone's state

Shown at 36 px, one at a time, chosen by `sr_disp_status_<m>` (and Idle by the scripted GUI's `is_shown`). Set in `te_sr_overview_milestone`.

| State | Placeholder | What the final art should show | Proposed file |
|---|---|---|---|
| Idle (colonization not running) | `generic_icons/inactive_building.dds` | an empty launch gantry, grey, no rocket | `state_idle.dds` |
| Standard (where every milestone starts) | `commander_order_icons/move.dds` | a white rocket rising on a steady yellow flame, no mark | `state_standard.dds` |
| Safe (the word carries the weekly cost) | `commander_order_icons/defend.dds` | a white rocket on its pad inside a blue shield outline | `state_safe.dds` |
| Ambitious (the word carries the weekly cost) | `military_icons/navy_icons/speed_navy.dds` | a white rocket climbing steeply on a long orange flame | `state_ambitious.dds` |
| Shielded (post-setback review) | `generic_icons/clock.dds` | a white rocket under a pale blue dome, a small clock face on the dome | `state_shielded.dds` |

#### Overview: risk, the first, the stage

| Cell | Placeholder | What the final art should show | Proposed file |
|---|---|---|---|
| Setback risk (lit while a roll is made, 25% otherwise) | `generic_icons/warning.dds` | a rocket nozzle with a crack, an amber warning mark over it | `risk.dds` |
| The first: open (lit) / claimed (25%) | `event_icons/waving_flag.dds` | a gold pennant planted on a grey crater rim | `first.dds` |
| Colonization's stage | `state_status_icons/colonizable.dds` | a ringed planet with a small domed settlement on its limb | `stage.dds` |

The First cell is set in `te_sr_ov_first`, the stage in the solar colonization overview root.

#### Programme row: the first-to-finish mark

| Mark | Placeholder | What the final art should show | Proposed file |
|---|---|---|---|
| We were first (18 px, top right of the entry's icon) | `event_icons/waving_flag.dds` | a small gold pennant on a staff, readable at 18 px | `first_mark.dds` |

Set in `te_sr_ov_prog_cell` and `te_sr_ov_prog_cell_interstellar`.

#### Programme row: the interstellar icon, four states

The Interstellar Probe and Interstellar Probe: Awaiting Data share one 44 px icon in the programme row (owner's play-test, round 3). Each state is its own icon with its own texture and tooltip (`je_space_race_widget_prog_interstellar_<n>`), shown by one test on `sr_disp_prog_interstellar`, so only one ever shows. The placeholders are the two PR #571 journal icons at different opacities; the final art gives each state its own drawing, so the `alpha` lines go when it lands. Set in `te_sr_ov_prog_cell_interstellar`.

| State | Placeholder | What the final art should show | Proposed file |
|---|---|---|---|
| 0: not begun (or another power finished it first) | `event_icons/je_space_race_interstellar_probe.dds` at 25% | the probe as a grey outline on a dark star field, unlit | `interstellar_not_begun.dds` |
| 1: under way | `event_icons/je_space_race_interstellar_probe.dds` at 60% | the probe on its assembly cradle, half its panels fitted, amber work lights | `interstellar_under_way.dds` |
| 2: launched, awaiting data | `event_icons/je_space_race_interstellar_results.dds` at 60% | the probe small against the stars, a dotted line back to a quiet radio dish | `interstellar_awaiting_data.dds` |
| 3: data received | `event_icons/je_space_race_interstellar_results.dds` | a radio dish lit by a bright signal arc from a distant star | `interstellar_data_received.dds` |

#### Colonization: the worlds pie

Three stacked `progresspie` layers in `te_sr_ov_pie` (the recipe in `gui_modding_guide.md`, "Pie charts of script-held data"). The placeholders are the UN's and Cultural Hegemony's pie textures. The final ones are plain discs, so they come from `scripts/image_pipeline/gen_ch_model_pie_textures.py` (a new `SR_PIES` tuple beside `UN_PIES`), not the icon pipeline.

| Layer | Placeholder | Final colour | Proposed file |
|---|---|---|---|
| The unclaimed rest (the disc) | `un_icons/pie_rest.dds` (grey `#8c8474`) | the same muted grey | `pie_unclaimed.dds` |
| Worlds claimed by anyone | `journal_entry_widgets/ch_model_pie/ch_pie_corporatist.dds` (orange `#c56c21`) | a rust red for other powers' claims | `pie_claimed.dds` |
| Ours, on top | `un_icons/pie_members.dds` (blue `#5b92e5`) | a bright gold | `pie_ours.dds` |
