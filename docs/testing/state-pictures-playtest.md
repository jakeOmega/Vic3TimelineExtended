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
| `TE_SELF_CHECK OK state_picture_oil` | once a game: the first state the yearly pass tagged oil country, with `oil_levels=` (its Oil Rig levels, 10 or more) no larger than `all_levels=` (all its levels but subsistence) and at least a twentieth of it | The walk takes `level` for a building's levels inside `every_scope_building` and its locals for sums that outlive the walk. BROKEN means one doesn't: read the oil field off the rigs' level in the weight (`any_scope_building = { is_building_type = building_oil_rig level >= 40 }`), which gives up the share |
| `TE_SELF_CHECK OK state_picture_size` | once a game: the first state the yearly pass stored at metropolis or larger, with `city_people=` (its largest city) no larger than `state_people=` (the state) | The pass takes `te_dg_urban` for a head count on `state_population`'s scale. BROKEN means it isn't: rescale the floors in `te_state_picture_values.txt` by the two figures' ratio, or read the size from `state_population` and `te_dg_urban_share` instead |

## The pilot (2026-11-10)

Four pictures. The engine facts under them were read in game the same day
(`docs/guides/scripting_best_practices.md` § "State pictures"); the three below were not.

| Check | Expect | If it fails |
|---|---|---|
| ~~A compressed picture. After the two technologies, open Home Counties, a British port state (one whose banner was the steamship) and a mining state (one whose banner was the pit head).~~ | Seen 2026-11-10 (owner, Home Counties): the compressed painting shows sharp. | |
| ~~A weight reading a state variable. A year after the technology (the pass is yearly), compare Home Counties with a smaller European city state such as Brandenburg or Austria.~~ | Seen 2026-11-10 (owner): after `event te_debug_state_picture.2` Home Counties showed the metropolis painting. | |
| ~~Vanilla's overlays on new paintings. Watch each of the four banners for a few seconds.~~ | Seen 2026-11-10 (owner): the European city overlay's smoke was in the wrong place on the metropolis. Fixed: the European, North American, East Asian and Japanese city pictures now take the port's birds-and-mist overlay (the registry's `NEUTRAL_OVERLAY`). The port and mine banners are still to watch. | |
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
| **Overlays on the new families.** Watch a city of each family for a few seconds. | Birds and drifting mist on the European, North American, East Asian and Japanese streets; leaves, mist, dust or heat shimmer on the Latin American, African, South Asian and Middle Eastern ones. Nothing that belongs to a spot in vanilla's painting (a plume from no chimney, surf on dry land). | A misplaced effect: set that family's `CITY_EFFECT` to `NEUTRAL_OVERLAY` in the registry. |
| **Lettering.** Look closely at each painting once. | Nothing that reads as writing. Signs in the renders were cropped or blurred before the filter. | A legible word: add a `smudge` box for it in `CITY_PICKS` and reconvert. |

## Wave 3: worked land (2026-11-10)

Forty-six paintings of ports, mines, oil fields, farmland, plantations, pasture, forestry and cleared land.
The technologies, by ladder: ports `modern_tools`, `containerization`, `supply_chain_management`,
`autonomous_vehicles`; mines and forestry `modern_tools`, `robotics`, and mines `internet_of_things`; oil
`modern_chemical_processes`, `integrated_circuits`, `hydraulic_fracturing`; farmland, plantation and
pasture `rural_electrification`, `green_revolution`, `microprocessor`, `autonomous_vehicles`, and farmland
`synthetic_biology`.

A new game with `research` shows the technology side only: building levels are 1836's, where no state has
a Port of level 20 (Guangdong's is 15), Lancashire and Yorkshire have Coal Mines of 25 and 20, and none has
an Oil Rig. So these rows want a save from the 1930s on. The oil and coal tags are stored by the yearly
pass: after loading, wait a year, or run `event te_debug_state_picture.1`, which runs the whole pass in
every state at once.

| Check | Expect | If it fails |
|---|---|---|
| **An oil field takes over.** A save with oil. After Modern Chemical Processes and a year, open a plain, desert or farm state where Oil Rigs are a twentieth or more of the building levels (in the 1940 save, 24 states). | The derrick field, not the land. It stays through later farm technologies. | The land's picture: a weight of 10,000,000 doesn't outrank, or the `INJECT` into that terrain didn't take (`error.log`, `terrain.cpp`). |
| **Oil beside a great economy.** The state with the most Oil Rigs in a late save, if it also holds a great city and its factories (the owner's Texas). | Its own picture, not the oil field: rigs are a few percent of its levels. | The oil field: the share isn't what the tag reads. An oil field where oil is a sideline, or none where it plainly is the economy: the 5% is off; it is provisional. |
| **Harbor and major port.** After Modern Tools, as the owner of each: a port state whose Port is under level 20 (in a new game, every one; a banner that was the steamship), and in a later save one of 20 or more. | The fishing harbor in the first, the liner quay in the second. On the later rungs: a ferry harbor and a container terminal. The pilot showed the liner quay in every port state; it now needs the level. | Both the same: the scale isn't read. In a late save, too many or too few major ports: the level is provisional. |
| **Pit and colliery.** After Modern Tools and a year, a state whose banner is the pit head and whose mines are mostly other than coal, and one where Coal Mines are half or more of the mine levels and at least 10 (Lancashire or Yorkshire in a new game, if the mining picture prevails there). | The open pit; the colliery with its winding wheel and spoil heaps. | The open pit in coal country: the tag isn't stored (`debug.log`, `TE_SELF_CHECK state_picture_oil` says whether the walk reads) or a weight can't read it. |
| **The farm families.** After Rural Electrification: a farm state in France or the Midwest, in Egypt, in South China, in Brazil, and in India. | Wheat with a tractor and horses; irrigated plots with date palms; rice paddies; red earth and maize; India the wheat picture (it is generic in vanilla too). | A wheat field on the Nile: the family's vanilla trigger doesn't hold in the mod's entry, or the generic family's "none of the others" doesn't. |
| **The fifth farm rung.** After Synthetic Biology, any farm state. | One picture for every family: purple and gold fields under glowing growth towers. | A family's fourth picture still showing: the rung isn't outranking the region digit. |
| **Tropical forestry.** After Modern Tools, a logging state in Sweden or Canada and one in Borneo or the Congo. | Conifers and a sawmill; a river landing under rainforest. | Conifers in the Congo: the family's region list. |
| **Pasture.** After Rural Electrification, a ranching state. | The new painting, the same everywhere. | |
| **Plantation and cleared land, if they occur at all.** Note whether any state's banner is ever vanilla's plantation or its field of stumps, before or after the technologies. | Probably never: nothing in vanilla's files makes a province either terrain (spec § 1, item 11). If one does show, the new painting after Rural Electrification (plantation) or Modern Tools (cleared land). | Seen in game: strike this row's doubt and note the state, so the lesson in `scripting_best_practices.md` can be corrected. |
| **Overlays on worked land.** Watch one of each for a few seconds. | Vanilla's birds and mist for that terrain. The oil field carries the arid plain's. | A mismatch: the picture's overlay is its draft's `like` in the registry. |
| **Lettering.** Look closely at the ports and the trucks. | Nothing that reads as writing. | A legible word: add a `smudge` box in `WAVE3_PICKS` and reconvert. |

## Waves 6 and 7: special cities and natural terrain (2026-11-10)

Eleven city paintings a weight reads live (housing blocks, smog, ruins, a nuclear strike) and fifteen of
natural terrain with a road, pylons or a pipeline in it. Technologies: the city ladder's for the first;
`modern_urban_planning` for natural terrain, and `integrated_circuits` for the tundra.

| Check | Expect | If it fails |
|---|---|---|
| **Natural terrain.** After Modern Urban Planning, a state whose banner is a mountain, hill, plain, desert, forest, jungle or marsh, in Europe, in the Americas and in Africa or the Middle East. | The same landscape with a motorway or a highway in it, in the family vanilla showed: the Alps and the Rockies differ, the green plain and the dry one differ. | Vanilla's painting still showing: that family's trigger. The wrong family's painting: the fallback's "none of the others". |
| **Savanna.** After Modern Urban Planning, a savanna state outside Africa and the Middle East, if there is one, and one inside. | The dry plain with its road in both, as vanilla shows its dry plain in both. | Vanilla's in the first: the picture's `any_region` isn't dropping its region there. |
| **Tundra.** After Integrated Circuits, a tundra state (northern Siberia, northern Canada). | The pipeline on stilts. | |
| **An oil field still takes over.** A plain or desert state with an Oil Rig of level 10, after both technologies. | The oil field, not the road. | The road: the takeover isn't outranking rung 1 there. |
| **Housing blocks.** As a country with Command Economy (`tag` to one, or enact it), after Prefabricated Construction and Modern Urban Planning, any city state. | Ranks of identical prefab blocks, whatever the region. Change the law and the region's own street returns. On Art Deco alone, or after Vactrains, the region's street. | The region's street under Command Economy: the owner's law isn't read in a weight. |
| **Smog.** A city state whose pollution reads 150 or more (the pollution map mode at or near its darkest), after Art Deco Architecture. | The city under a brown haze, in the rung's period. | Smog nowhere in a late game: 150 is too high; everywhere: too low. The figure is provisional. |
| **Ruins.** A city state with devastation of half or more (a long battle in it), after Art Deco Architecture. | A ruined street; from Computer-Aided Design, ruined tower blocks. It clears as devastation decays. | |
| **A nuclear strike.** Strike a city state whose owner has Modern Urban Planning. | The ash plain while the aftermath modifier lasts, then the ruins while devastation is still half or more, then the city. A strike on an owner without the technology shows the ruins. | The city's own street during the aftermath: `has_modifier` on the state isn't read in a weight, or the strike's modifier is on another scope. |
| **Housing blocks and smog together.** A Command Economy city with heavy pollution. | The housing blocks (the higher digit). | |
| **Lettering and flags.** Look closely at the vehicles, the factory fronts and the ruins. | Nothing that reads as writing, no real flag. | A `smudge` box in `WAVE6_PICKS` or `WAVE7_PICKS`, and reconvert. |

