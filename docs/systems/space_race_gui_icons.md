# Space Race GUI: Placeholder Icons

The Space Race panels' overview (the GUI style guide pass, September 2026) draws a handful of icons of its own. All of them are vanilla or borrowed placeholders for now, so the layout can be judged in game before the art exists (`gui_style_guide.md` rule 10). The programme row's seven single-state icons are not placeholders: they are the journal-entry icons painted in PR #571 (`gfx/interface/icons/event_icons/je_space_race_<m>.dds`). Its interstellar icon, which has four states, borrows two of them for now (below).

**Where each is set.** Every placeholder is a literal `texture = "…"` line in `gui/journal_entry_widgets/space_race_widget.gui`, in the type named below. No script reads the paths, so swapping one in is one path change. The proposed paths are new files under `gfx/interface/icons/space_race_icons/`.

**The rule for the set** is the UN's (`un_gui_icons.md`): simple and easy to recognize at 32–40 px. The five state icons share one emblem, a rocket on its pad, and differ by what surrounds it.

## Overview: the milestone's state

Shown at 36 px, one at a time, chosen by `sr_disp_status_<m>` (and Idle by the scripted GUI's `is_shown`). Set in `te_sr_overview_milestone`.

| State | Placeholder | What the final art should show | Proposed file |
|---|---|---|---|
| Idle (colonization not running) | `generic_icons/inactive_building.dds` | an empty launch gantry, grey, no rocket | `state_idle.dds` |
| Standard (where every milestone starts) | `commander_order_icons/move.dds` | a white rocket rising on a steady yellow flame, no mark | `state_standard.dds` |
| Safe (the word carries the weekly cost) | `commander_order_icons/defend.dds` | a white rocket on its pad inside a blue shield outline | `state_safe.dds` |
| Ambitious (the word carries the weekly cost) | `military_icons/navy_icons/speed_navy.dds` | a white rocket climbing steeply on a long orange flame | `state_ambitious.dds` |
| Shielded (post-setback review) | `generic_icons/clock.dds` | a white rocket under a pale blue dome, a small clock face on the dome | `state_shielded.dds` |

## Overview: risk, the first, the stage

| Cell | Placeholder | What the final art should show | Proposed file |
|---|---|---|---|
| Setback risk (lit while a roll is made, 25% otherwise) | `generic_icons/warning.dds` | a rocket nozzle with a crack, an amber warning mark over it | `risk.dds` |
| The first: open (lit) / claimed (25%) | `event_icons/waving_flag.dds` | a gold pennant planted on a grey crater rim | `first.dds` |
| Colonization's stage | `state_status_icons/colonizable.dds` | a ringed planet with a small domed settlement on its limb | `stage.dds` |

The First cell is set in `te_sr_ov_first`, the stage in the solar colonization overview root.

## Programme row: the first-to-finish mark

| Mark | Placeholder | What the final art should show | Proposed file |
|---|---|---|---|
| We were first (18 px, top right of the entry's icon) | `event_icons/waving_flag.dds` | a small gold pennant on a staff, readable at 18 px | `first_mark.dds` |

Set in `te_sr_ov_prog_cell` and `te_sr_ov_prog_cell_interstellar`.

## Programme row: the interstellar icon, four states

The Interstellar Probe and Interstellar Probe: Awaiting Data share one 44 px icon in the programme row (owner's play-test, round 3). Each state is its own icon with its own texture and tooltip (`je_space_race_widget_prog_interstellar_<n>`), shown by one test on `sr_disp_prog_interstellar`, so only one ever shows. The placeholders are the two PR #571 journal icons at different opacities; the final art gives each state its own drawing, so the `alpha` lines go when it lands. Set in `te_sr_ov_prog_cell_interstellar`.

| State | Placeholder | What the final art should show | Proposed file |
|---|---|---|---|
| 0: not begun (or another power finished it first) | `event_icons/je_space_race_interstellar_probe.dds` at 25% | the probe as a grey outline on a dark star field, unlit | `interstellar_not_begun.dds` |
| 1: under way | `event_icons/je_space_race_interstellar_probe.dds` at 60% | the probe on its assembly cradle, half its panels fitted, amber work lights | `interstellar_under_way.dds` |
| 2: launched, awaiting data | `event_icons/je_space_race_interstellar_results.dds` at 60% | the probe small against the stars, a dotted line back to a quiet radio dish | `interstellar_awaiting_data.dds` |
| 3: data received | `event_icons/je_space_race_interstellar_results.dds` | a radio dish lit by a bright signal arc from a distant star | `interstellar_data_received.dds` |

## Colonization: the worlds pie

Three stacked `progresspie` layers in `te_sr_ov_pie` (the recipe in `gui_modding_guide.md`, "Pie charts of script-held data"). The placeholders are the UN's and Cultural Hegemony's pie textures. The final ones are plain discs, so they come from `scripts/image_pipeline/gen_ch_model_pie_textures.py` (a new `SR_PIES` tuple beside `UN_PIES`), not the icon pipeline.

| Layer | Placeholder | Final colour | Proposed file |
|---|---|---|---|
| The unclaimed rest (the disc) | `un_icons/pie_rest.dds` (grey `#8c8474`) | the same muted grey | `pie_unclaimed.dds` |
| Worlds claimed by anyone | `journal_entry_widgets/ch_model_pie/ch_pie_corporatist.dds` (orange `#c56c21`) | a rust red for other powers' claims | `pie_claimed.dds` |
| Ours, on top | `un_icons/pie_members.dds` (blue `#5b92e5`) | a bright gold | `pie_ours.dds` |
