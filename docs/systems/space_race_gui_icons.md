# Space Race GUI: Icons

The Space Race panels' overview (the GUI style guide pass, September 2026) draws 25 icons of its own, including three pie layers and nine for the kinds of world in Our Colonies. They were vanilla or borrowed placeholders in the first rounds of the pass (`gui_style_guide.md` rule 10), and PR #586 replaced them. All of them live in `gfx/interface/icons/space_race_icons/`. The programme row's seven single-state icons are the journal-entry icons painted in PR #571 (`gfx/interface/icons/event_icons/je_space_race_<m>.dds`), used as they are.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/space_race_widget.gui`, in the type named below, and the states are chosen by a display value's code. No script reads the paths. `SpaceRaceIconsTest` in `test_space_race_layout.py` holds each state to its file. It also fails on any placeholder left in the widget, and, once #586's files are in the repo, on any path that does not exist.

**Remaking one.** The icons come from the icon pipeline (`scripts/image_pipeline/`). Their registry entries are the `space_part` (the one rocket), `space` (the first, the first-to-finish mark, the stage, the nine colony kinds) and `space_state` (the five states, the risk, the four interstellar states) categories in `icon_prompts.py`. Each entry's `now` field names the placeholder it replaced. The pies are plain discs from `scripts/image_pipeline/gen_ch_model_pie_textures.py`. Change the entry, re-render, review, then `write`. The GUI needs no edit unless a file name changes.

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

## Our Colonies: the kind of world

One icon for each of nine kinds of world, not one for each of the 34 worlds or 68 specializations. It shows at 24 px, left of the specialization's name, in `te_sr_colony_row`, which takes the file from a `colony_icon` block override on each of the 68 rows. A row shows the icon of the kind its world belongs to, so a world's two specializations share one. `ColoniesTest` holds every row to its kind.

| Kind | Worlds | Shows | File |
|---|---|---|---|
| Mars | Valles Marineris, Olympus Mons, Hellas, Utopia, Arcadia | a rust-red planet with canyon scars and a pale polar cap | `colony_mars.dds` |
| Asteroid | Ceres, Vesta, Psyche, Pallas, Hygiea | a lumpy, cratered grey-brown rock | `colony_asteroid.dds` |
| Jovian moon | Io, Europa, Ganymede, Callisto, Himalia, Amalthea | a cratered moon before a banded orange gas giant | `colony_jovian.dds` |
| Venus | Venus | a yellow-ochre planet in swirling cloud | `colony_venus.dds` |
| Mercury | Mercury | a small cratered planet, bright on one side | `colony_mercury.dds` |
| Saturnian moon | Titan, Enceladus, Rhea, Mimas, Iapetus | a hazy orange moon before a tan ring | `colony_saturnian.dds` |
| Uranian moon | Titania, Oberon, Miranda, Ariel | an icy grey-blue moon with a steep cyan ring behind | `colony_uranian.dds` |
| Neptunian moon | Triton, Proteus | a pink-and-blue moon streaked with geyser plumes | `colony_neptunian.dds` |
| Dwarf planet | Pluto, Eris, Makemake, Haumea, Sedna | a tan-and-brown dwarf planet with a pale heart patch and a tiny moon | `colony_dwarf.dds` |

The kinds group worlds by the body they orbit. Each falls inside one stage (Mars and the asteroids in stage 1, the Jovian moons and Venus in 2, Mercury and the Saturnian moons in 3, the Uranian and Neptunian moons in 4, the dwarf planets in 5), so no kind's icon sits under two stage headings. A world that is mostly white or pale loses its body in the cut-out, so Venus and the dwarf planet are drawn in colour. The modifiers' own icons (`icon =` on the 68 `sr_colony_*` static modifiers) are not these: they are the shared lightbulb and coins glyphs that say what kind of effect it is.

## Kept as they are

The pie's frame (`gfx/interface/backgrounds/round_frame_dec.dds`) is vanilla's decoration, used as vanilla uses it. So are the Rivals rows' band marker (`gfx/interface/progressbar/progressbar_marker.dds`) and the transparent track under it (`generic_icons/transparent.dds`), drawn as the UN's authority bar draws them. The rows have no icons of their own.
