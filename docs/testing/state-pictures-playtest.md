# State pictures play-test checklist

What the next play-test should look at in the state panel's banner pictures
(`common/terrain/te_state_pictures_generated.txt`, `docs/systems/mod_systems/state_pictures.md`). In-game checks do
not gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and
adds what only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck through
with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The banner at the top of a state's panel. The picture can't be logged, so these are looks, not
  log reads. Nothing shows before its technology: in a new game, `research art_deco_architecture` and
  `research modern_tools` in the console as the country that owns the state (`tag GBR`).
- **No waiting a year.** The size a picture follows is stored by a yearly pass. From the console:
  - `event te_debug_state_picture.1` runs the pass at once in every state and logs a `TE_STATE_PICTURE debug:` line
    for each of your states: `size=` (1 town, 2 city, 3 metropolis, 4 megacity, 0 no walk yet) and `city_people=`,
    the largest-city figure it came from.
  - `event te_debug_state_picture.2` makes your capital read as a metropolis whatever its people, so the metropolis
    painting and a weight's read of the variable can be checked without a city over the floor. The next pass (yearly,
    or `.1`) puts the size back.
- **Logs.** `debug.log` for `TE_SELF_CHECK` and `TE_STATE_PICTURE debug:`, `error.log` for `terrain.cpp`.

## Self-checks

| Line | Says | Fallback if BROKEN |
|---|---|---|
| `TE_SELF_CHECK OK state_picture_size` | once a game: the first state the yearly pass stored at metropolis or larger, with `city_people=` (its largest city) no larger than `state_people=` (the state) | The pass takes `te_dg_urban` for a head count on `state_population`'s scale. BROKEN means it isn't: rescale the floors in `te_state_picture_values.txt` by the two figures' ratio, or read the size from `state_population` and `te_dg_urban_share` instead |

## The pilot (2026-11-10)

Four pictures. The engine facts under them were read in game the same day
(`docs/guides/scripting_best_practices.md` § "State pictures"); the three below were not.

| Check | Expect | If it fails |
|---|---|---|
| **A compressed picture.** After the two technologies, open Home Counties, a British port state (one whose banner was the steamship) and a mining state (one whose banner was the pit head). | The new city, port and mine paintings, sharp, with no blocky edges or color banding beside vanilla's uncompressed ones. | A blank or garbled banner: BC7 isn't accepted there. Re-export uncompressed (texconv `-f B8G8R8A8_UNORM_SRGB`, 2.7 MB each) in `convert_state_picture.py`. |
| **A weight reading a state variable.** After the technology and `event te_debug_state_picture.2` as Great Britain (or a year later, if Home Counties' `city_people=` clears 1,000,000), compare Home Counties with a smaller European city state such as Brandenburg or Austria. | Home Counties shows the metropolis painting, the smaller state the city painting. The line's `city_people=` is the figure the size came from. | Both show the city painting though `TE_SELF_CHECK OK state_picture_size` is in `debug.log`: a weight can't read `var:`. Put the size's own test in the weight (`te_state_picture_city_people >= te_state_picture_k_metropolis` under `scope:state`), which gives up the margin that keeps a size from flickering. |
| **Vanilla's overlays on new paintings.** Watch each of the four banners for a few seconds. | Birds, mist and drifting smoke that sit plausibly on the painting. | Smoke rising from the middle of the street or a similar mismatch: change that picture's `effect` in the registry to the port's overlay (birds, light rays, mist), or define an empty entity for it (the mod has no entity files yet, so that needs its own look). |
| **Before the technology.** A new game, any state. | Vanilla's picture, as before the mod. | A mod painting in 1836: a weight applies without its technology. |
| **Outside Europe.** After the technologies, a city state in Asia or the Americas. | Vanilla's city picture: the pilot's city paintings are European only. The port and mine paintings show everywhere. | |
| **The other panels.** Hover a state for its tooltip; open a pop's details. | The same new painting, cropped as vanilla's is. | |
| **The size floors.** In a game past 1920, note which states read metropolis. | Roughly the world's great cities. | Too many or too few: the floors in `te_state_picture_values.txt` are provisional, and the spec's wave 2 sets them from an observer game. |
