# Space Race GUI: Icons

The Space Race panels' overview (the GUI style guide pass, September 2026) draws 16 icons of its own, including three pie layers. They were vanilla or borrowed placeholders in the first rounds of the pass (`gui_style_guide.md` rule 10), and PR #586 replaced them. All of them live in `gfx/interface/icons/space_race_icons/`. The programme row's seven single-state icons are the journal-entry icons painted in PR #571 (`gfx/interface/icons/event_icons/je_space_race_<m>.dds`), used as they are.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/space_race_widget.gui`, in the type named below, and the states are chosen by a display value's code. No script reads the paths. `SpaceRaceIconsTest` in `test_space_race_layout.py` holds each state to its file. It also fails on any placeholder left in the widget, and, once #586's files are in the repo, on any path that does not exist.

**Remaking one.** The icons come from the icon pipeline (`scripts/image_pipeline/`). Their registry entries are the `space_part` (the one rocket), `space` (the first, the first-to-finish mark, the stage) and `space_state` (the five states, the risk, the four interstellar states) categories in `icon_prompts.py`. Each entry's `now` field names the placeholder it replaced. The pies are plain discs from `scripts/image_pipeline/gen_ch_model_pie_textures.py`. Change the entry, re-render, review, then `write`. The GUI needs no edit unless a file name changes.

**The rule for the set** is the UN's (`un_gui_icons.md`): simple and easy to recognize at 32–40 px. The five state icons and the risk share one emblem, a silver rocket with red fins, and differ by what surrounds it.

## Overview: the milestone's state

Shown at 36 px, one at a time, chosen by `sr_disp_status_<m>` (and Idle by the scripted GUI's `is_shown`). Set in `te_sr_overview_milestone`.

| State | Shows | File |
|---|---|---|
| Idle (colonization not running) | the rocket, greyed | `state_idle.dds` |
| Standard (where every milestone starts) | the rocket rising on a short flame | `state_standard.dds` |
| Safe (the word carries the weekly cost) | the rocket on its pad inside a blue shield | `state_safe.dds` |
| Ambitious (the word carries the weekly cost) | the rocket climbing at a slant on a long flame | `state_ambitious.dds` |
| Shielded (post-setback review) | the rocket under a glass dome, vanilla's clock at its foot | `state_shielded.dds` |

The list asked for an empty launch gantry for Idle; at 36 px the gantries were thin lattices, so Idle is the rocket greyed. It also asked for a white rocket, which loses its body in the cut-out, so the rocket is silver.

## Overview: risk, the first, the stage

| Cell | Shows | File |
|---|---|---|
| Setback risk (lit while a roll is made, 25% otherwise) | the rocket cracked, under vanilla's warning mark | `risk.dds` |
| The first: open (lit) / claimed (25%) | a gold pennant on a staff, planted on a grey crater rim | `first.dds` |
| Colonization's stage | a rust-red ringed planet, a small domed settlement on its upper edge | `stage.dds` |

The risk icon was to be a cracked nozzle; the nozzle alone is a speck at 36 px, so the whole rocket is cracked. The First cell is set in `te_sr_ov_first`, the stage in the solar colonization overview root. The 25% fades are by design: they are the icon's "off" state, not a placeholder.

## Programme row: the first-to-finish mark

| Mark | Shows | File |
|---|---|---|
| We were first (18 px, top right of the entry's icon) | a bold gold pennant on a short staff | `first_mark.dds` |

Set in `te_sr_ov_prog_cell` and `te_sr_ov_prog_cell_interstellar`.

## Programme row: the interstellar icon, four states

The Interstellar Probe and Interstellar Probe: Awaiting Data share one 44 px icon in the programme row (owner's play-test, round 3). Each state is its own icon with its own texture and tooltip (`je_space_race_widget_prog_interstellar_<n>`), shown by one test on `sr_disp_prog_interstellar`, so only one ever shows. The art carries the state, so none is faded. Set in `te_sr_ov_prog_cell_interstellar`.

| Code | State | Shows | File |
|---|---|---|---|
| 0 | Not begun (or another power finished it first) | the #571 probe icon, greyed | `interstellar_not_begun.dds` |
| 1 | Under way | the probe icon, a brass wrench at its corner | `interstellar_under_way.dds` |
| 2 | Launched, awaiting data | the #571 radio-dish icon, vanilla's clock at its corner | `interstellar_awaiting_data.dds` |
| 3 | Data received | the dish icon, vanilla's green check at its corner | `interstellar_data_received.dds` |

The list asked for four new drawings. The art builds them on the #571 journal icons instead, so the row keeps the Space Race's painted disc.

## Colonization: the worlds pie

Three stacked `progresspie` layers in `te_sr_ov_pie` (the recipe in `gui_modding_guide.md`, "Pie charts of script-held data"), each a 256×128 texture drawn as frame 2 of 128. Plain discs from `gen_ch_model_pie_textures.py`, checked for colour-blind contrast on every pair.

| Layer | Colour | File |
|---|---|---|
| The unclaimed rest (the disc) | muted grey `#8c8474` | `pie_unclaimed.dds` |
| Worlds claimed by anyone | rust red `#cf4a2a` | `pie_claimed.dds` |
| Ours, on top | bright gold `#ecc043` | `pie_ours.dds` |

## Kept as they are

The pie's frame (`gfx/interface/backgrounds/round_frame_dec.dds`) is vanilla's decoration, used as vanilla uses it.
