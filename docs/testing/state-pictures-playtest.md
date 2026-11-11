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
- **Logs.** `debug.log` for `TE_SELF_CHECK`, `error.log` for `terrain.cpp`.

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
| **A weight reading a state variable.** A year after the technology (the pass is yearly), compare Home Counties with a smaller European city state such as Brandenburg or Austria. | Home Counties shows the metropolis painting, the smaller state the city painting. The line's `city_people=` is the figure the size came from. | Both show the city painting though `TE_SELF_CHECK OK state_picture_size` is in `debug.log`: a weight can't read `var:`. Put the size's own test in the weight (`te_state_picture_city_people >= te_state_picture_k_metropolis` under `scope:state`), which gives up the margin that keeps a size from flickering. |
| **Vanilla's overlays on new paintings.** Watch each of the four banners for a few seconds. | Birds, mist and drifting smoke that sit plausibly on the painting. | Smoke rising from the middle of the street or a similar mismatch: change that picture's `effect` in the registry to the port's overlay (birds, light rays, mist), or define an empty entity for it (the mod has no entity files yet, so that needs its own look). |
| **Before the technology.** A new game, any state. | Vanilla's picture, as before the mod. | A mod painting in 1836: a weight applies without its technology. |
| **Outside Europe.** After the technologies, a city state in Asia or the Americas. | Vanilla's city picture: the pilot's city paintings are European only. The port and mine paintings show everywhere. (Since the wave 2 registry, the European paintings also show in the states of no region family, as vanilla's European picture does: Tibet and the Pacific islands.) | A European painting in Tokyo, New York or Mexico City: the fallback's `is_not_in_geographic_region` lines in `te_state_pictures_generated.txt` don't hold in a weight. |
| **The other panels.** Hover a state for its tooltip; open a pop's details. | The same new painting, cropped as vanilla's is. | |
| **The size floors.** In a game past 1920, note which states read metropolis. | Roughly the world's great cities. | Too many or too few: the floors in `te_state_picture_values.txt` are provisional, and the spec's wave 2 sets them from an observer game. |

## Wave 2: the city tier (2026-11-10)

Thirty-nine more city paintings: eight region families on the five rungs of the city ladder. `research` each rung's
technology as the state's owner: `art_deco_architecture`, `modern_urban_planning`, `computer_aided_design`,
`advanced_structural_engineering`, `vactrains`.

| Check | Expect | If it fails |
|---|---|---|
| **A family's ladder.** As one country with a city state, research the five technologies in order and reopen the state after each. | The street changes with each: 1930s, about 1960, about 1990, the 2030s, the far future, with the same kind of landmark at its end. A later technology outranks an earlier one. | An earlier painting after a later technology: the rung isn't the weight's leading place. |
| **The eight families.** After Art Deco Architecture (`tag` to each owner): London, New York, Rio de Janeiro or Mexico City, Lagos or Cairo, Bombay, Constantinople or Tehran, Beijing, Tokyo. | European, North American, Latin American, African, South Asian, Middle Eastern, East Asian, Japanese. Sydney shows the North American street; Mexico City the Latin American (vanilla shows it the European). | A European street in one of the others: the family's region trigger doesn't hold, or the fallback's `is_not_in_geographic_region` lines don't. |
| **The overlaps.** Tokyo, and Quetta or Peshawar. | Tokyo the Japanese street, never the East Asian; Quetta the Middle Eastern, not the South Asian. | The other one: the family digits aren't deciding. |
| **No family.** Lhasa, or a Pacific island, where the city terrain prevails at all. | The European street, as vanilla's European picture shows there. | |
| **Overlays on the new families.** Watch a city of each family for a few seconds. | Vanilla's birds, mist and smoke for that family, sitting plausibly. | A mismatch: change the family's `CITY_EFFECT` in the registry. |
| **Lettering.** Look closely at each painting once. | Nothing that reads as writing. Signs in the renders were cropped or blurred before the filter. | A legible word: add a `smudge` box for it in `CITY_PICKS` and reconvert. |

## Wave 3: worked land (2026-11-10)

Forty-six paintings of ports, mines, oil fields, farmland, plantations, pasture, forestry and cleared land.
The technologies, by ladder: ports `modern_tools`, `containerization`, `supply_chain_management`,
`autonomous_vehicles`; mines and forestry `modern_tools`, `robotics`, and mines `internet_of_things`; oil
`modern_chemical_processes`, `integrated_circuits`, `hydraulic_fracturing`; farmland, plantation and
pasture `rural_electrification`, `green_revolution`, `microprocessor`, `autonomous_vehicles`, and farmland
`synthetic_biology`.

A new game with `research` shows the technology side only: building levels are 1836's, where one state has
a Port of level 10 (Guangdong, 15), two have Coal Mines of level 10 (Lancashire 25, Yorkshire 20) and none
has an Oil Rig. The rows that need a level say how to get one; a save from the 1930s on is the easier way.

| Check | Expect | If it fails |
|---|---|---|
| **An oil field takes over.** A save with oil, or a new game where a state whose banner is a plain, a desert or farmland has been given an Oil Rig of level 10 (build it, or raise it in the console). After Modern Chemical Processes, open that state. | The derrick field, not the land. It stays through later farm technologies. Below level 10, the land. | The land's picture: a weight of 10,000,000 doesn't outrank, or the `INJECT` into that terrain didn't take (`error.log`, `terrain.cpp`). |
| **Too many oil fields.** In a game past 1950, look at farm states with a modest oil industry. | Wheat or rice, where oil is a sideline. | Derricks over a farm state: the level of 10 is too low, or the test needs to be a share of the state's levels (spec § 5), stored by the yearly pass. |
| **Harbor and major port.** After Modern Tools, as the owner of each: a port state whose Port is under level 10 (in a new game, every one but Guangdong; a banner that was the steamship), and Guangdong. | The fishing harbor in the first, the liner quay in Guangdong. On the later rungs: a ferry harbor and a container terminal. The pilot showed the liner quay in every port state; it now needs the level. | Both the same: the scale isn't read. In a late save, too many or too few major ports: the level is provisional. |
| **Pit and colliery.** After Modern Tools, a state whose banner is the pit head and whose Coal Mines are under level 10 or absent, and Lancashire or Yorkshire if the mining picture prevails there. | The open pit; the colliery with its winding wheel and spoil heaps. | |
| **The farm families.** After Rural Electrification: a farm state in France or the Midwest, in Egypt, in South China, in Brazil, and in India. | Wheat with a tractor and horses; irrigated plots with date palms; rice paddies; red earth and maize; India the wheat picture (it is generic in vanilla too). | A wheat field on the Nile: the family's vanilla trigger doesn't hold in the mod's entry, or the generic family's "none of the others" doesn't. |
| **The fifth farm rung.** After Synthetic Biology, any farm state. | One picture for every family: purple and gold fields under glowing growth towers. | A family's fourth picture still showing: the rung isn't outranking the region digit. |
| **Tropical forestry.** After Modern Tools, a logging state in Sweden or Canada and one in Borneo or the Congo. | Conifers and a sawmill; a river landing under rainforest. | Conifers in the Congo: the family's region list. |
| **Plantation, pasture, cleared land.** After Rural Electrification (Modern Tools for cleared land), a state of each. | The new painting, the same everywhere. | |
| **Overlays on worked land.** Watch one of each for a few seconds. | Vanilla's birds and mist for that terrain. The oil field carries the arid plain's. | A mismatch: the picture's overlay is its draft's `like` in the registry. |
| **Lettering.** Look closely at the ports and the trucks. | Nothing that reads as writing. | A legible word: add a `smudge` box in `WAVE3_PICKS` and reconvert. |
