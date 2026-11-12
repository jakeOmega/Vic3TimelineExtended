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
    for each of your states: `size=` (1 town, 2 city, 3 metropolis, 4 megacity, 0 no walk yet), `city_people=`,
    the largest-city figure it came from, and `oil=` and `coal=` (1 where the state is tagged oil country or a
    colliery).
  - `event te_debug_state_picture.2` makes your capital read as a metropolis whatever its people, so the metropolis
    painting and a weight's read of the variable can be checked without a city over the floor. The next pass (yearly,
    or `.1`) puts the size back.
- **Logs.** `debug.log` for `TE_SELF_CHECK` and `TE_STATE_PICTURE debug:`, `error.log` for `terrain.cpp`.

## Self-checks

| Line | Says | Fallback if BROKEN |
|---|---|---|
| `TE_SELF_CHECK OK state_picture_oil` | once a game: the first state the yearly pass tagged oil country, with `oil_levels=` (its Oil Rig levels, 10 or more) no larger than `all_levels=` (all its levels but subsistence) and at least a twentieth of it. The line also carries `mine_levels=` and `coal_levels=`: where the state has coal, `mine_levels` should be at least `coal_levels`; 0 beside coal means the mining group test misses the mod's mines and every state with 10 coal levels reads as a colliery | The walk takes `level` for a building's levels inside `every_scope_building` and its locals for sums that outlive the walk. BROKEN means one doesn't: read the oil field off the rigs' level in the weight (`any_scope_building = { is_building_type = building_oil_rig level >= 40 }`), which gives up the share |
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
every state at once and logs each of your states' `oil=` and `coal=` tags.

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
| **Overlays on worked land.** Watch one of each for a few seconds. These overlays were judged from the textures they name, not seen: the mine's has two cloud puffs and a toxic mist (vanilla's painting has two chimneys: do the puffs hang where no chimney is?), forestry's and pasture's drifting motes (do they read as snow over a rainforest?), the farmlands' and the arid plain's a glow (is it a sunbeam, or a light fixed to a spot?). | Ambient effects that could sit on any painting. | An effect tied to a spot in vanilla's painting: add that overlay to `PLACED_OVERLAYS` in the registry and give its pictures `NEUTRAL_OVERLAY`, as the European and Asian city overlays were. |
| **One-province states.** Open several: a slice of a split region that holds only the port or the city hub, an island, a treaty port. Note each one's banner beside its buildings. | Unknown. Seen 2026-11-11: Singapore (one province, the port hub of Malaya, Urban Center 405, Port 50, no farm) showed the Asian rice farmland of its owner's rung. | A city or port state that shows farmland or bare land: the engine's terrain for the province, not the weights. The remedy is a city takeover (the oil field's pattern), which is the owner's call. |
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
| **Overlays on natural terrain.** Watch a plain, a hill and a mountain road for a few seconds. Vanilla's overlays for these carry blowing grass (plains, American plains, arid mountains, hills) and a glow (hills, arid plain, American desert), judged from their texture names only. | Grass and light that sit on the land, not on the asphalt. | Grass waving across a motorway: add the overlay to `PLACED_OVERLAYS` and give the picture `NEUTRAL_OVERLAY`. |
| **Lettering and flags.** Look closely at the vehicles, the factory fronts and the ruins. | Nothing that reads as writing, no real flag. | A `smudge` box in `WAVE6_PICKS` or `WAVE7_PICKS`, and reconvert. |

## A great city on any terrain (2026-11-11)

The engine held Singapore, a metropolis of one province with no farm, to be rice farmland. Every city
picture is now also in the list of every other land terrain, for a metropolis or larger. The entries are
written one line each, in 22 terrains, two of which (`river`, `snow`) the mod had not injected into before.

| Check | Expect | If it fails |
|---|---|---|
| **Load.** Start the game with the mod and read `error.log`. | No `terrain.cpp` line ("Terrain effect is missing") and no non-existing-entry line for `river` or `snow`. | An error on a one-line entry: write the takeover entries in the long form (`gen_state_pictures.py`, `render`). A missing terrain: take it out of `CITY_TAKEOVER_TERRAINS`. |
| **Singapore.** The owner's save `singapore_1900_02_13`, the state of Singapore. | A city picture of the East Asian family on the Computer-Aided Design rung (or a character's, if the state is tagged), not the rice fields. | Still the rice fields: the state's terrain is one the list misses, or the entry didn't load (the row above). |
| **A smaller city keeps its land.** The same save: Singapore's states in Guangdong and North Sumatra (cities, not metropolises). | The harbor, as before. | A city picture: the size condition isn't first or isn't read. |
| **A forced metropolis.** In a farm or forest state that is your capital, `event te_debug_state_picture.2`. | The city picture until the next yearly pass, then the land again. | |
| **A metropolis in oil country.** A metropolis whose state is tagged oil and shows open land. | The city, not the derricks. | The derricks: 11,000,000 doesn't outrank 10,000,000 plus the rung. |
| **Ruins on any terrain.** A devastated metropolis whose state shows land. | The ruins. | The intact city: the condition's entry in that terrain. |
| **A great port, a great mining state.** A metropolis whose banner was the major port (the docks terrain prevails), and one whose banner was the pit or the colliery. | The city now, in both. These are calls the owner can reverse: take `docks` or `mining` out of `CITY_TAKEOVER_TERRAINS`. | |
| **Cost.** Open and close state panels quickly in a late game, on a state of farmland. | No stutter: about 70 more weights are read there, each failing on its first line unless the state is a metropolis. | A hitch that the old build doesn't have: thin the takeover to the regional streets. |

## The pass's city tags (2026-11-11)

Eighteen more city paintings for any region: boomtown, declining, divided, heavy industry, resort. All
read tags the yearly pass stores, so load a save from the 1930s on, research the city ladder as the
owner and run `event te_debug_state_picture.1` (or wait a year; growth needs several).

| Check | Expect | If it fails |
|---|---|---|
| **Heavy industry.** A city state where heavy industry is a quarter of the building levels. | Furnaces and chimneys in the rung's period, not the region's street. | The street: the tag isn't stored (the walk's `bg_heavy_industry` test), or 25% is too high for your games. |
| **Resort.** A state with a large Tourism Industry (2% of its levels, 10 or more). | A beach resort. It is a seaside picture whatever the state: an inland resort state will show a beach. | A beach in a state where tourism is a sideline: raise the share. An inland beach that grates: the picture wants a coast condition. |
| **Boomtown and declining.** After several game years, compare a fast-growing city state (heavy immigration) with one losing people. | Cranes and half-built blocks in the first; shut works and empty streets in the second. Neither after a single year's jump or a conquest. | Boomtowns everywhere, or none: the 3% and −1% are provisional. A boomtown right after a border change: the province check. |
| **Divided.** A metropolis with very high inequality (Gini 0.85 on the Demographics map mode). | Shacks under towers behind a wall. | Most metropolises divided: raise the floor. |
| **Two at once.** A smog-bound boomtown; a declining heavy-industry city. | The boomtown; the declining city (the higher digit). | |
| **The debug event's line.** `event te_debug_state_picture.1`, then `debug.log`. | Each of your states' lines ends with `character=` (6 boomtown, 5 declining, 4 divided, 2 heavy industry, 1 resort, 0 none) and `growth=` (the smoothed yearly rate, in percent). | |
| **Lettering.** Trucks, hoardings, the airliners over the resorts. | Nothing that reads as writing. | A `smudge` box in `WAVE6_PICKS`, and reconvert. |

## Prosperity tags (2026-11-11)

The size and prosperity variants (below) read these. The pass stores them whether or not a variant is
painted, so they can be checked from the log.

| Check | Expect | If it fails |
|---|---|---|
| **The reads.** After Art Deco Architecture, `event te_debug_state_picture.1` as any country, then `debug.log`. | Each of your states' lines ends with `means=` (1 poor, 2 ordinary, 3 affluent), `rundown=` (0 or 1), `sol=` (the state's standard of living, as its panel shows) and `short=` (how far that sits under what its people expect). | `sol=0` everywhere or a load error naming `average_sol` or `average_expected_sol`: a state doesn't read one of them in a script value. Use the Demographics walk's `te_dg_sol` for the first and the owner's figure for the second. |
| **The floors.** In a save, compare `sol=` with `means=` for states of an owner on each city rung. | Poor under 12, 14, 18, 26, 35 by rung; affluent from 20, 22, 28, 36, 45. | |
| **How many are run-down.** In a late save, count `rundown=1`. | A minority: states that have lost ground. | Most states of a welfare state run-down: the laws' floor under expectations is what `short=` is measuring. Raise the margin (2), or take the owner's floor out of the figure. |

## Size and prosperity variants (2026-11-11)

Each regional street has a town, a metropolis and (from rung 3) a megacity, and a poor, an affluent and a
run-down street, on every rung. A variant that has no painting yet falls back: a megacity to the
metropolis, everything else to the region's street of that rung. Load a late save, play as an owner with
states of several sizes, and run `event te_debug_state_picture.1` so every state has its tags.

| Check | Expect | If it fails |
|---|---|---|
| **Size.** Compare the banner of a state whose largest city is under 100,000 people, one over 1,000,000 and one over 10,000,000, in one region and on one rung. | A quiet main street; a city center from above; a city to the horizon. Each with the region's landmark, in the rung's period. | The street in all three: `size=` in the debug line, then the entry's first condition. |
| **Poor and affluent.** A state with `means=1` and one with `means=3` in the debug line. | A shabby lane with washing and carts; a clean boulevard with a fountain. | |
| **Run-down.** A state with `rundown=1`. | Neglect, not poverty: boarded windows, litter, a wreck, people standing idle. It shows over poor and affluent. | A run-down picture in states that are doing well: the margin (2 points under expectations) is too tight; the "How many are run-down" row above. |
| **Prosperity outranks size.** A poor or an affluent metropolis or megacity; a poor small town. | The poor or affluent street, not the skyline or the small town: prosperity's place in the weight (100 and 1,000) is above size's (10). This is a call the owner can reverse by swapping the places. | A megacity that never shows its megacity picture because most great cities are poor, affluent or run-down by the floors: raise the floors, or put size above means. |
| **The time on the last two rungs.** A poor, an affluent and a run-down state of an owner with rung 4, then rung 5. | Rung 4: supertall glass towers behind the street, electric vehicles. Rung 5: white futuristic towers, flying craft, pods or robots. | A street that reads as the 1950s: note the key; its prompt wants the time moved further forward. |
| **A great city on other terrain.** A poor or run-down metropolis whose state the engine holds to be farmland. | The poor or run-down city picture (the variants of a great city take over as the streets do). | The farmland: the variant's takeover entries. |
| **No real city.** Look at each metropolis and megacity for a tower or a skyline you could name. | None. The North American ones are the most likely to fail. | Tell which picture; it is repicked, or unwired so that its fallback (above this table) shows. |
| **Lettering and flags.** Bus fronts, awnings, tower tops, the bottom corners. | Nothing that reads as writing, no real flag. | A `smudge` box in `VARIANT_PICKS`, and reconvert. |
