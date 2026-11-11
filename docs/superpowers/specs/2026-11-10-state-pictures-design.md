# State pictures by technology, city size and prosperity — design

Drafted 2026-11-10 with the owner. The banner at the top of the state panel shows one of vanilla's 35
paintings (a city, a port, a mine, farmland, a landscape), chosen by the state's terrain and region. They are
all nineteenth-century scenes. This design replaces them, once a country reaches the technologies of era 6
and later, with pictures that follow the owner's technology, the size of the city, how well its people live
and, where the mod has the figures, what kind of place it is. It lists the whole intended set (about 360
pictures, painted in waves) so that no early picture is wasted, and describes the pilot of four that ships
with it. There is no separate plan for the pilot; each later wave gets its own pull request.

System doc (as built): `docs/systems/mod_systems/state_pictures.md`. Play-test list:
`docs/testing/state-pictures-playtest.md`.

## 1. The owner's calls (2026-11-10)

1. **From era 6 on.** Vanilla's pictures stay until a picture's technology is researched.
2. **Gated on particular technologies, the owner's, not on eras.** A city changes with Modern Urban Planning,
   a farm with the Green Revolution. Each family of pictures has its own ladder of technologies (§ 4).
3. **More granular than vanilla:** by city size, by standard of living and by demographic data where the mod
   has it.
4. **Prosperity needs a careful definition.** The owner's question: is it the absolute standard of living
   or a relative one? Amenities fit the first; litter in the street may fit the second. § 6 is this
   design's answer, two axes. Asked on the pilot what "relative" should be measured against, the owner
   answered "prosperity being relative makes sense to me". That settles § 6's relative measure as written
   (a state's standard of living against what its own people expect). The owner's words don't name the
   measure or the absolute axis; that the answer covers both as § 6 has them is this design's reading.
5. **Housing-block cities follow the Command Economy law,** not a region.
6. **Ambitious set, in waves.** It can be cut back; § 9 gives the order of cuts.
7. **The painted look stands** ("I like the style"): the converter's filter of § 10 is the look of the whole
   set. On the pilot's picks, with the replacement European city: "I'm fine with the pick".
8. **A picture stands for a whole region.** "The images are supposed to reflect the overall region": "on the
   small end, think Rhode Island, on the large end, Alaska or Texas". "A mining or oil drilling region makes
   sense, but does a power plant region make sense?" It doesn't: the mod's power plants are city buildings
   built where the demand is, and no region reads as a power station. The power-landscape family (six
   pictures and a ladder of its own) was cut on this rule. Pylons, turbines and cooling towers stay where
   they are part of another picture's landscape. The test for any picture: would a traveler crossing the
   state call this what the place is like, or is it one site in it? Five more groups failed it and were
   cut the same day (15 pictures): naval bases, offshore oil platforms, spaceports, financial districts
   and government quarters, each one installation or one district of a city. Ports, mines, onshore oil,
   farms, forestry, the heavy-industry city, the resort and the conditions of a region's cities passed.
9. **An oil state is one where oil is a major part of the economy,** not one with many rigs. "If more than,
   say, 10% of state GDP is from oil, it is an oil state", so that a Texas with "a megalopolis with
   factories, urban centers, etc. so that oil is just 3% of state GDP" isn't shown as one; the measure can be
   stored yearly ("can't we store it as a variable yearly or something?"). § 5's oil and coal tags follow
   it. Script can't read one building's share of GDP, so the share is of the state's building levels: that
   stand-in, its 5% and the rule for a colliery are this design's.
10. **The region and worked-land calls stand** ("Sounds good!"): Australia and New Zealand with North
    America, Mexico and the Caribbean with Latin America, Middle Eastern over South Asian where they
    overlap, India's farmland generic, an oil field taking over farmland and pasture. The harbor replacing
    the pilot's liner quay in lesser ports is "fine - a new game is going to be way less developed than the
    world by the time we get to the new eras". The flooded coast stays unwired until the warming system has
    local effects ("we can wire it up later"). Natural terrain on Modern Urban Planning, smog from 150 of
    255 and ruins from one half devastation stand until a test game says otherwise.
11. **The plantation and cleared-land pictures stay though they may never show** ("let's leave them for
    now"). Nothing in vanilla 1.15's files makes a province either terrain: plantation buildings set no
    terrain manipulator and none creates cleared land (`docs/guides/scripting_best_practices.md`, § "State
    pictures"). The six pictures are wired and harmless; giving plantations the manipulator would show
    them and would also change the map, which is a separate decision.

## 2. What the engine does (read in game, 2026-11-10)

`State.GetBestTexture` picks the state's prevailing terrain (`common/terrain`: `urban`, `docks`, `mining`,
`forestry`, the farmland types, the natural ones), then the highest-weight entry of that terrain's `textures`
list. A probe on `urban` settled the rest (`docs/guides/scripting_best_practices.md` § "State pictures"):

- An `INJECT:` adds entries to a terrain's list, so no vanilla terrain is restated.
- A weight's `scope:state = { }` takes ordinary state triggers: the owner's technology and a building-level
  comparison both worked.
- Every entry needs an `effect` (the animated overlay). One without it is an error, and its state shows the
  plains picture.
- The picture can't be logged (`GetBestTexture` prints empty in `debug_log`).

The same picture shows in the state tooltip, pop details, the invasion and battle panels and the strategic
region panel. The mod does not change which terrain prevails: vanilla's mine weighting counts only coal, iron,
lead, sulfur and gold mines, and that stays as it is in this design.

Read in game the same evening, from the owner's look at Home Counties as a metropolis: a weight reads a
state variable, and a BC7-compressed picture shows sharp. The third question, how a vanilla overlay sits on
a new painting, got its answer too: the European city overlay's smoke was "in the wrong place" (§ 10,
Overlays).

## 3. How a picture is chosen

Each picture names the terrain lists it joins and its conditions on the axes below. A condition left open
("any region", "any size") makes the picture a fallback for everything not painted yet. Among the pictures
whose conditions hold, the weight picks the most specific, in this order of precedence:

| Place | Axis | Values | Read from |
|---|---|---|---|
| 1 | Condition | devastated, nuclear aftermath, flooded | the state, live |
| 2 | Takeover | an oil field, on the open land it stands on | the yearly pass |
| 3 | Technology rung | 1 up to 9 on the family's ladder | the owner's technology, live |
| 4 | Character or function | housing blocks, smog; boomtown, declining, divided, heavy industry, resort | the owner's law and the state region's pollution, live; the yearly pass for the rest |
| 5 | Upkeep | run-down | the yearly pass |
| 6 | Means | poor, affluent | the yearly pass |
| 7 | Size, or scale | town, metropolis, megacity; a major port, a colliery | the yearly pass; for a major port a building's level, live |
| 8 | Region | a family of the picture's group: eight for cities, four for farmland, one for forestry | geography, live |

So the right technology beats the right size, and a devastated city beats everything. The weight is a number
in place value (a takeover 10,000,000, and a condition its digit × 1,000,000 on top of that; rung × 100,000;
a character its digit × 10,000; size or scale × 10; a named region its family's digit; 1,000 and 100 are
reserved for upkeep and means), which also keeps two pictures from tying. Vanilla's weights are 1 and 2, so
any mod picture that applies wins. Conditions and takeovers share the place above the rung without meeting:
a condition is a city picture and a takeover stands on open land. That keeps the largest weight (13,400,000
so far) under 16,777,216, the last whole number a 32-bit float holds exactly, in case the engine keeps a
weight in one; a test holds the places apart and under that ceiling.

A **takeover** is a picture with no terrain of its own. Vanilla has no oil-field terrain, so an oil state
shows the plain, desert or farmland the rigs stand on. The oil pictures join those terrains' lists and
outrank every rung there, so that a later farm technology doesn't put the wheat back over the derricks. A
**scale** is the worked-land counterpart of a city's size: the larger or the special kind of a picture
(§ 5).

**The yearly pass.** The engine may evaluate a weight every frame, so a weight reads only the owner's
technology, vanilla's region triggers and a few state variables. A yearly state pulse computes those
variables (`te_sp_*`), with a margin so a state sitting on a threshold doesn't change picture every year. A
picture can lag a change by up to a year; a technology shows at once.

## 4. Technology ladders

One ladder a family. A rung's picture shows what its technology puts in the street or the field.

| Family | Rung 1 | Rung 2 | Rung 3 | Rung 4 | Rung 5 |
|---|---|---|---|---|---|
| City | Art Deco Architecture (era 6): trams, early motor cars, stone and deco fronts | Modern Urban Planning (7): concrete and glass slabs, wide roads, mass motoring | Computer-Aided Design (8): curtain-wall towers, expressways | Advanced Structural Engineering (10): supertall towers, electric traffic | Vactrains (12): transit tubes, arcologies |
| Port | Modern Tools (6): liners, steel cranes on rails | Containerization (8): gantries, stacked boxes | Supply Chain Management (9): the automated terminal | Autonomous Vehicles (11): crewless ships and yards | |
| Mine | Modern Tools (6): draglines, the open pit | Industrial Robotics (8): giant haul trucks, sorting plants | Internet of Things (10): remote-run pits | | |
| Oil field | Modern Chemical Processes (6): derrick fields | Integrated Circuits (7): directional rigs, a small refinery | Hydraulic Fracturing (9): pad wells | | |
| Farmland, plantation, ranch | Rural Electrification (6): tractors, power lines | Green Revolution (7): combines, silos, irrigation | Microprocessor (8): center pivots, large machines | Autonomous Vehicles (11): crewless harvesters | Synthetic Biology (11): designed crops, glasshouse towers |
| Forestry | Modern Tools (6): chainsaws, log trucks | Industrial Robotics (8): harvesters, managed stands | | | |

The city ladder's rungs also carry the skyline pictures: a metropolis needs Modern Skyscrapers as well from
rung 1, and a megacity exists from rung 3. The housing-block city needs Prefabricated Construction (the
technology of Prefabricated Tower Blocks public housing) and the Command Economy law. A ladder can gain a rung later
without touching the pictures already painted.

Considered and left out: gating a port, mine or farm on the state's own production method. It would keep a
backward colony on its old picture, but the owner's call is technology, and one rule for every family is
easier to read. It can be added to a family as one more condition if the play-test wants it.

## 5. Regions and city size

**Regions** are vanilla's seven city families (European, Latin American, East Asian, Japanese, South Asian,
Middle Eastern and Central Asian, African), plus North American, which vanilla folds into European. Farmland
keeps vanilla's four families (generic, Arabic, Asian, subtropic); forestry has a tropical picture beside
the conifer one. Ports, mines, oil fields, plantations, pasture and cleared land are painted once for every
region. The farmland and forestry families are under "Worked land" below.

The city families use vanilla's own region triggers, with three changes. They are this design's calls, each
one line in the registry's `REGIONS`, and the state counts are from 1.15's region files:

| Family | States | Trigger | Against vanilla |
|---|---|---|---|
| European | 217 | `geographic_region_europe` (Russia west of Siberia included), and every state of no family | the same; the states of no family are Tibet and the Himalayas (5) and the Pacific islands (11) |
| North American | 71 | `geographic_region_north_america`, `geographic_region_australasia` | new. Vanilla shows these the European picture. Australia and New Zealand (9) join because a grid of brick blocks and glass towers is nearer Sydney than a stone boulevard is |
| Latin American | 83 | `geographic_region_latin_america` | vanilla's `is_subtropic_farmland` holds 61 of these and leaves out Mexico and the Caribbean (22), which it shows the European picture; it lists Central America three times, so the gap reads as an oversight |
| African | 93 | `geographic_region_africa` | the same. It includes North Africa: Cairo is in this family, not the Middle Eastern |
| South Asian | 28 | `geographic_region_india` | the same |
| Middle Eastern | 69 | `geographic_region_middle_east`, `geographic_region_central_asia_old` | the same |
| East Asian | 102 | `geographic_region_east_asia`, `geographic_region_south_east_asia` (Siberia included) | the same |
| Japanese | 12 | `geographic_region_japan` | the same |

Two pairs overlap, so each family has its own digit in the weight and the higher one wins: Japanese over
East Asian (Japan lies inside East Asia, and vanilla ranks it the same way), and Middle Eastern over South
Asian for Baluchistan, Pashtunistan and Quetta, which vanilla leaves a tie. Until a family's picture on a
rung is painted, its states keep the family's earlier picture or vanilla's; the European picture doesn't
stand in for a named family. The overlaps are the exception, because a rung outranks a family's digit: an
East Asian picture of rung 2 wired alone would show in Tokyo over Japan's rung 1. So the two families of an
overlap are wired together on a rung (the registry's `REGION_OVERLAPS`, held by a test).

**City size** is the number of people in the state's largest city: the Demographics walk's urban people
(`te_dg_urban`, written every year whatever the Demographics rule) times the metropolitan share (`te_dg_mt`;
where the census keeps none, the base share of 40%).

| Size | Largest city | Notes |
|---|---|---|
| Town | under 100,000 | |
| City | 100,000 and over | the family's middle picture, tagged "any size" |
| Metropolis | 1,000,000 and over | |
| Megacity | 10,000,000 and over | pictures from city rung 3 |

A size is left only a tenth below its floor. The floors are provisional: § 9 sets them against an observer
game before the size pictures are painted in number.

**Worked land** (wave 3). The registry's `FARM_REGIONS`, `FOREST_REGIONS` and `SCALES`.

| Family or scale | States | Trigger | Notes |
|---|---|---|---|
| Arabic farmland | 157 | vanilla's `is_arabic_farmland` | the Middle East and most of Africa: irrigated plots, date palms, later center pivots in the desert |
| Asian farmland | 68 | vanilla's `is_asian_farmland` | rice paddies |
| Subtropic farmland | 61 | vanilla's `is_subtropic_farmland` | Latin America: red earth, maize and cane |
| Generic farmland | 390 | none of the three | wheat country, and every state of no other family. India and Oceania are here, as in vanilla |
| Tropical forestry | | South-East Asia, Equatorial and West Africa, Central America, Gran Colombia, Brazil, and vanilla's `is_jungle_hills` | rainforest logging; the conifer picture stands everywhere else |
| Major port | 44 of 405 port states in a 1940 save | a Port of level 20 or more, read live | below it, the harbor picture: fishing boats, a ferry, a small quay |
| Colliery | 44 of 139 coal states | the pass's `te_sp_coal`: Coal Mines are half or more of the state's mine levels, and 10 levels or more | otherwise the open pit |
| Oil field | 24 of 109 oil states | the pass's `te_sp_oil`: Oil Rigs are 5% or more of the state's building levels, and 10 levels or more | takes over open land (plains, desert, savanna, tundra, hills, the five farmlands, pasture), not a city, port, mine or forest |

The three farm families don't overlap, so their digits only keep the weights apart.

**What a state's worked land is known for** is a share, not a count (the owner's call, § 1 item 9). The
yearly pass walks the state's buildings once, subsistence buildings left out, and tags the state:

- *Oil country* (`te_sp_oil`) while Oil Rigs hold 5% or more of its building levels and at least 10. A
  building's share of the state's GDP can't be read in script; levels are the stand-in, and since an oil rig
  earns more a level than most buildings, 5% of levels is taken for about a tenth of GDP. In a 1940 save
  the state with the most rigs, 100 levels among 4,499, holds 2% and stays a city or a plain; 24 of the 109
  states with oil pass, among them every one where rigs are a tenth of the levels.
- *A colliery* (`te_sp_coal`) while Coal Mines hold half or more of its mine levels (`bg_mining`) and at
  least 10.

A tag is kept until its figure falls a tenth under the floor, as a size is. A major port stays a count: a
great port is one by its size, whatever else the state does. All four figures are provisional and sit in
`te_state_picture_values.txt` (the port's level in the registry). The oil caps in `map_data/state_regions`
bound what can ever pass: 150 states have oil, half of them a cap of 20 or less.

**Natural terrain** (wave 7) keeps vanilla's own families, by the triggers vanilla's entries use (the
registry's `LAND_REGIONS`, `DESERT_REGIONS`, `HILL_REGIONS`). None overlap in 1.15's region files.

| Terrain | Families | Notes |
|---|---|---|
| Plains, mountains | American (`geographic_region_americas`: 145 states, South America included), arid (`is_arid_region`: 162, Africa, the Middle East and Oceania), generic (neither) | |
| Savanna | none: the arid plain's picture in every state | as vanilla, which has no savanna picture. The registry's `any_region` lists a terrain a picture joins without its region |
| Desert | American, generic | |
| Hills | jungle (`is_jungle_hills`: Indochina and South China), subtropic (`is_subtropic_farmland`: Latin America), generic | |
| Tundra, forest, jungle, wetland | one picture each | |

A rung outranks a scale or a region, so the plain and the special picture of a rung are wired together (the
registry's `WIRED_TOGETHER`, held by a test, as `REGION_OVERLAPS` is for cities): a rung 2 harbor wired
alone would show in a great port over rung 1's major port.

## 6. Prosperity: means and upkeep

Two axes, because they draw different things.

**Means** is the absolute standard of living: the state's `average_sol`. It decides what the place can
afford, so it draws amenities and build quality: how many motor cars, shop fronts and street lighting, paved
or dirt streets, parks, the housing stock (shacks and tenements, or villas and glass). Three levels: poor,
ordinary, affluent. The floors are fixed numbers for each rung, since an affluent street of 1930 and one of
2030 are different pictures; they are not relative to the world of the day. § 9 sets them from an observer
game, so that roughly a fifth of the city states of countries on a rung sit in each extreme.

**Upkeep** is relative: `average_sol` minus `average_expected_sol`, the game's own measure of whether people
have what they expect. It decides how the place is kept, so it draws neglect: litter, shuttered shops,
broken windows, peeling paint, queues and idle crowds. Two levels: ordinary and run-down, run-down when the
standard of living sits a set margin under expectations. Under the mod's Standard of Living Expectations
system, expectations lag a fall and rise with a richer world, so a rich city in decline reads run-down while
a poor one that never had more doesn't. That is the split the owner asked for: a poor but content town is
drawn modest and tidy, a wealthy but aggrieved one prosperous and neglected.

When both apply, upkeep takes precedence: the run-down picture is painted at ordinary means and stands for
all three. A run-down picture at each level of means is a later refinement, not in the set below.

## 7. Character, function and conditions

Pictures for any region unless noted, on the city rungs where they fit. Where two hold, the first in the
order below shows (each has its own digit in the character place of the weight).

| Picture | Shows when | Signal | Read |
|---|---|---|---|
| Housing blocks | Command Economy and Prefabricated Construction | the owner's law and technology | live |
| Boomtown, cranes everywhere | the state's people have grown fast for several years | `te_dg_walk_pop` against the year before | the yearly pass |
| Declining city, empty works | the state's people are falling | the same | the yearly pass |
| Divided city, shacks under towers | a large city with high inequality | `te_dg_gini` | the yearly pass |
| Smog city | heavy pollution | the state region's `pollution_amount` at 150 or more of 255 (vanilla's pollution map mode is at full color from 153) | live |
| Heavy-industry city | most levels are heavy industry | building levels | the yearly pass |
| Resort | tourism dominates | the tourism buildings | the yearly pass |

A character sits under the rung, so it is painted on each rung where it fits: a smog city of 1960 gives way
to the city of 1990 unless 1990's smog city is painted too. After the last painted rung the region's own
picture returns.

Conditions outrank every rung and are painted for two spans of the city ladder each:

| Picture | Shows when | Signal |
|---|---|---|
| A city after a nuclear strike | the state carries the strategic or the tactical strike's aftermath | `nuclear_strike_aftermath`, `tactical_nuke_aftermath` (state modifiers that decay) |
| A devastated city | devastation of one half or more | `devastation >= 0.5` (in 1.15 only battles raise it, and a nuclear strike sets it to the full) |
| A flooded coast | not wired | the warming system's coastal flooding is a modifier on the country, from an event, which would flood every coastal city the country has. The picture waits for a marker on the state |

A struck city shows the strike while the aftermath lasts, then the ruins while its devastation is still
high, then its own picture again.

## 8. The set

| Group | Pictures | Contents |
|---|---|---|
| Core city grid | 120 | 8 regions × 5 rungs × town, city, metropolis |
| Megacities | 24 | 8 regions × rungs 3 to 5 |
| Means | 80 | a poor and an affluent picture a region a rung |
| Upkeep | 40 | a run-down picture a region a rung |
| Character | about 20 | § 7's first five, on the rungs where they fit |
| Function | about 6 | § 7's last two |
| Conditions | about 6 | |
| Ports | 8 | a small harbor and a major port a rung |
| Mines and oil | 9 | open pits, collieries, onshore oil fields |
| Farmland, plantation, ranch | 25 | four farm families × four rungs, one designed-crop picture for all, plantation and ranch × four |
| Forestry and cleared land | 6 | conifer and tropical forestry, cleared land, × two rungs |
| Natural terrain | about 15 | optional late variants: a highway through the mountains, a pipeline in the tundra |

About 360 pictures. At BC7 (0.7 MB each) that is about 250 MB of `gfx/`; in vanilla's uncompressed format it
would be over 1 GB.

## 9. Waves

1. **Pilot (4), this pull request.** § 11.
2. **Calibration, then the city tier of the core grid (40).** An observer game's figures (largest-city
   people, `average_sol` and the expectations gap by year and by rung) fix the floors of §§ 5 and 6. Then 8
   regions × 5 rungs of the middle picture. After this wave every city past rung 1 has a picture of its
   time, and these stay the fallback for every size and level of prosperity. **Painted and wired 2026-11-10:** all 39 beside the pilot's, picked from four candidates each (the last
   rung from a second set, below). The calibration game is still to run, so the size floors stay
   provisional; the city tier doesn't read them.
3. **Worked land (46):** ports, mines and oil, farmland, forestry. **Painted and wired 2026-11-10:** all
   46, each picked from four candidates (the two port pictures of the 2040s from a later set, § 10). With the pilot's port and mine that is every
   worked-land picture of § 8. What it designed: the scales and the takeover of § 3, the farmland and
   forestry families of § 5, and the three provisional levels there.
4. **Town, metropolis, megacity (104).**
5. **Means and upkeep (120),** with their part of the yearly pass.
6. **Character, function, conditions (about 30),** with theirs. Its 30 prompts are drafted in `DRAFTS`
   (18 character, 6 function, 6 condition), for any region and on the rungs where each fits.
7. **Natural terrain (about 15).** Its 15 prompts are drafted in `DRAFTS`: each of vanilla's natural
   pictures with the motor age in it (a motorway, pylons, a pipeline), on Modern Urban Planning for want of
   a ladder of its own.

If the set is cut: natural terrain first, then megacities merged into four broad families, then means and
upkeep limited to rungs 2 to 4.

## 10. How it is built

- **One registry,** `scripts/image_pipeline/state_picture_registry.py`: each picture's terrain lists,
  conditions, overlay, prompt and picked seed. An entry without a seed is planned art and wires nothing.
- **A generator,** `scripts/generators/gen_state_pictures.py`, writes
  `common/terrain/te_state_pictures_generated.txt` from the picked entries: one `INJECT:` a terrain.
  `test_state_pictures.py` fails when it is stale, when two pictures of a terrain could tie, when an entry
  lacks an overlay and when a wired picture isn't tracked.
- **The yearly pass,** `te_state_picture_refresh` on `on_yearly_pulse_state`
  (`common/scripted_effects/te_state_picture_effects.txt`). The pilot stores the size, `te_sp_size`; later
  waves add means, upkeep and character the same way.
- **Overlays.** Every entry reuses a vanilla overlay, and only one whose effects aren't placed for
  vanilla's own painting. Vanilla's European city overlay has two smoke plumes over its painting's chimneys
  and its Asian one two lines of surf on its shore; on the pilot's metropolis the smoke rose from mid-air
  (the owner, in game). So the European, North American, East Asian and Japanese city pictures take the
  port's overlay (birds and drifting mist, the registry's `NEUTRAL_OVERLAY`), and a test keeps the two
  placed ones (`PLACED_OVERLAYS`) off every picture. The other families' overlays are leaves, mist, dust
  and shimmer and stay. A mod-defined overlay of its own (smoke where a painting has chimneys) is possible
  later; the mod has no entity files yet.
- **Pictures.** FLUX.1-schnell at 1536 × 752, with the style ahead of the subject in the prompt (the text
  encoder that sets the look reads only the first 77 tokens). The pick is converted by
  `scripts/image_pipeline/convert_state_picture.py`: cropped where an edge carries a signature or a stray
  object, passed through a Kuwahara filter (flat dabs of color with kept edges, which brings a
  near-photographic render beside vanilla's brushwork) and compressed to 1020 × 500 BC7 with mips,
  `gfx/state_pictures/te_<key>.dds`. The painting has to sit beside vanilla's: loose brush, haze, no
  lettering, the subject across the middle, because the panel lays a shadow on the top, a fade on the bottom
  and the flag bottom left, and a second widget shows the picture at 260 × 145. Where vanilla has a picture
  of the same subject, the new one keeps its composition (the street with the dome at its end, the ship at
  the quay), so a state's banner reads as the same place later.
- **What the first wave taught** (2026-11-10, 196 renders for 39 pictures):
  - *Vehicles need their own decade.* "A street around 1960" dates the buildings and leaves the cars in
    the 2000s. "Rounded 1950s cars", "boxy 1980s cars" render in period. The two 1960 streets without it
    had modern cars in all four candidates and were reworded and rerun.
  - *The far future has to be asked for by name.* The last rung's first prompts ("terraced arcology
    buildings, a vacuum-train tube") came out as a present-day street with one odd building; the owner:
    "the far future could look more futuristic, given the technologies in the last couple eras". Leading
    with "a far-future city", kilometre-high towers, flying craft, humanoid robots and a spacecraft's
    trail gave megastructures in every candidate, with the family's landmark still in place.
  - *The landmark carries.* The same kind of building closed the street on all five rungs of every
    family, without naming a real one.
  - *Lettering comes in small.* About a third of candidates carry a sign or a plate. A crop drops one at
    an edge; for one in the middle the registry's `smudge` boxes blur it to a dab before the filter.
    At 1020 x 500 after the filter nothing in the picked set reads as writing.
  - *One seed leaves a dark strip* of 9 to 25 pixels along the bottom of about half its renders; the
    converter refuses a picture with one, and the picks crop it.
  - *Budget:* 28 s a render held. Ten of the 39 pictures were rendered twice: the eight of the last rung
    for the bolder prompt and the two 1960 streets for their cars. The other 29 were picked from their
    first four candidates.
- **What the worked-land wave taught** (2026-11-10, 196 renders for 46 pictures):
  - *A landscape is easier than a street,* up to the present day. Naming the machines of the time in the
    prompt (the tractor, the combine, the well pad) put 44 sets in period at the first try.
  - *The future again has to be asked for by name.* The two port pictures of the 2040s ("crewless electric
    cargo boats", "robotic cranes") came out as a harbor of today with wind turbines behind it, older in
    look than their own rung before. They were reworded to lead with "a futuristic harbor" and
    rendered again. The words for the future matter as much: "sleek white hulls" turned the container
    ships into cruise liners, and the major port took a third set that names what the ship lacks ("no
    bridge and no funnel") and carries ("four tall rigid white wing sails").
  - *Lettering moves to the machines.* Fields carry none, but hulls, truck doors, a tractor's hood and a
    mill's name board do, and a painter's signature turned up in a bottom corner of four candidates. Twelve picks
    carry `smudge` boxes. One candidate flew a real national flag: rejected like a landmark.
  - *The dark strip* was on 6 of this wave's 46 renders of that seed; none was picked.
  - *Later rungs of a ladder drift toward one look* (drones, wind turbines, solar panels on every roof).
    It reads as its time, but the farm families' fourth rungs are closer to one another than their first.
- **Review.** As for icons: a sheet a batch with vanilla's picture beside the candidates and the pick marked,
  every pick zoomed for lettering, signatures and broken anatomy.
- **One landmark a family.** Vanilla's city pictures close the street with a building. Each family keeps one
  through all five rungs (the registry's `CITY_LANDMARK`: the European church, a North American courthouse
  with a clock tower, a Japanese castle keep, and so on), so the street changes around a fixed point and a
  state's banner reads as the same place a century on. The renders won't repeat the building exactly; the
  kind and the place in the frame are what carry over.
- **No recognizable landmarks.** A picture stands for every state of its region, so it must not read as one
  city. A generic description of a building draws the most famous building of that kind: the pilot's "a
  domed civic building at the end of the street" drew the United States Capitol in all four candidates, in
  the picture meant for London, Paris and Berlin (owner, 2026-11-10). So a prompt describes a landmark by
  features that belong to the region and to no one building ("a baroque church with a green copper dome and
  twin bell towers"), or leaves it out, and never asks for a civic building, tower, bridge, palace or
  skyline without them. Review checks every pick for a silhouette a player would name: the Capitol, the
  Eiffel Tower, Big Ben, a famous bridge, a known skyline. The risk grows with the metropolis and megacity
  pictures, whose subject is a skyline. A candidate that reads as a real place is rejected like one with
  lettering. The registry's `PROMPT_AVOID` holds the two words the pilot learned this from (shop, civic)
  and others likely to do the same (sign, banner, flag, skyline, …), and `test_state_pictures.py` fails on
  a prompt that uses one.

## 11. The pilot

Four pictures, wired:

| Picture | Terrain | Shows when |
|---|---|---|
| European city, rung 1 | `urban` | Art Deco Architecture, in Europe |
| European metropolis, rung 1 | `urban` | the same, and the largest city holds 1,000,000 people or more |
| Port, rung 1 | `docks` | Modern Tools, and the state has a Port |
| Mine, rung 1 | `mining` | Modern Tools |

The metropolis picture doesn't ask for Modern Skyscrapers yet (§ 4); the ladder's second condition comes
with wave 4. What the pilot is for, beyond the four pictures: the registry, generator and tests the later
waves fill in; the yearly pass and the first variable a weight reads; a compressed picture; and vanilla's
overlays on new paintings. Those three engine questions are on the play-test list with their fallbacks
(direct checks in the weight, the uncompressed format, an empty overlay).

## 12. Open questions

- Whether Tibet and the Pacific islands should leave the European fallback for a family.
- The floors of §§ 5 and 6, until wave 2's observer game. The same game can check § 5's four worked-land
  figures (the port's level, oil's share, coal's share, the least levels) against more than one save.
- Whether oil's share of levels tracks its share of GDP closely enough. If a building's earnings turn out
  to read as a value, the pass can weigh the levels by them.
- The regions that count as tropical for forestry.
- The flooded coast waits for the warming system to have local effects (the owner: "we can wire it up
  later"); its two pictures are painted and unwired.
- Whether the city ladder should split at era 9 (a "global city" rung on Globalization) once rung 3's
  pictures exist.
