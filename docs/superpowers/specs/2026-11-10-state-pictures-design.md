# State pictures by technology, city size and prosperity — design

Drafted 2026-11-10 with the owner. The banner at the top of the state panel shows one of vanilla's 35
paintings (a city, a port, a mine, farmland, a landscape), chosen by the state's terrain and region. They are
all nineteenth-century scenes. This design replaces them, once a country reaches the technologies of era 6
and later, with pictures that follow the owner's technology, the size of the city, how well its people live
and, where the mod has the figures, what kind of place it is. It lists the whole intended set (about 380
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

Still unread, and on the play-test list: a weight reading a state variable, a BC7-compressed picture, and
how a vanilla overlay sits on a new painting.

## 3. How a picture is chosen

Each picture names the terrain lists it joins and its conditions on the axes below. A condition left open
("any region", "any size") makes the picture a fallback for everything not painted yet. Among the pictures
whose conditions hold, the weight picks the most specific, in this order of precedence:

| Place | Axis | Values | Read from |
|---|---|---|---|
| 1 | Condition | devastated, nuclear aftermath, flooded | the state, live |
| 2 | Technology rung | 1 up to 9 on the family's ladder | the owner's technology, live |
| 3 | Character or function | boomtown, declining, divided, smog, housing blocks; financial center, industry, spaceport, resort, government quarter | the yearly pass |
| 4 | Upkeep | run-down | the yearly pass |
| 5 | Means | poor, affluent | the yearly pass |
| 6 | Size | town, metropolis, megacity | the yearly pass |
| 7 | Region | one of eight families | geography, live |

So the right technology beats the right size, and a devastated city beats everything. The weight is a number
in place value (rung × 100,000, size × 10, a named region 1; the places between are reserved), which also
keeps two pictures from tying. Vanilla's weights are 1 and 2, so any mod picture that applies wins.

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
| Oil field | Modern Chemical Processes (6): derrick fields | Integrated Circuits (7): directional rigs, offshore platforms | Hydraulic Fracturing (9): pad wells | | |
| Farmland, plantation, ranch | Rural Electrification (6): tractors, power lines | Green Revolution (7): combines, silos, irrigation | Microprocessor (8): center pivots, large machines | Autonomous Vehicles (11): crewless harvesters | Synthetic Biology (11): designed crops, glasshouse towers |
| Forestry | Modern Tools (6): chainsaws, log trucks | Industrial Robotics (8): harvesters, managed stands | | | |
| Energy landscape | Modern Tools (6): the coal station, the dam (added with wave 3's drafts; a proposal) | Nuclear Energy (7): the plant | Clean Energy Technologies (9): wind and solar fields | Fusion Power (11) | |

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
keeps vanilla's four families (generic, Arabic, Asian, subtropic). Ports, mines, forestry and energy are
painted once for every region.

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

Pictures for any region unless noted, on the city rungs where they fit. One character or function at most;
the pass picks the first that holds, in the order below.

| Picture | Shows when | Signal |
|---|---|---|
| Housing blocks | Command Economy and Prefabricated Construction | the owner's law and technology |
| Boomtown, cranes everywhere | the state's people have grown fast for several years | `te_dg_walk_pop` against the year before |
| Declining city, empty works | the state's people are falling | the same |
| Divided city, shacks under towers | a large city with high inequality | `te_dg_gini` |
| Smog city | heavy pollution | `pollution_generation` |
| Financial center | a high Financial District | building level |
| Heavy-industry city | most levels are heavy industry | building levels |
| Spaceport | a launch site | the Space Race site buildings |
| Resort | tourism dominates | the tourism buildings |
| Government quarter | the national capital, at metropolis size | `is_capital` |

Conditions outrank everything and are painted for two or three spans of the city ladder: a devastated city
(`devastation`), a city after a nuclear strike (the nuclear system's strike marker) and a flooded coast (the
warming system's sea-level stage). The last two need a marker their systems don't keep on the state yet;
each gets one when its picture is painted.

## 8. The set

| Group | Pictures | Contents |
|---|---|---|
| Core city grid | 120 | 8 regions × 5 rungs × town, city, metropolis |
| Megacities | 24 | 8 regions × rungs 3 to 5 |
| Means | 80 | a poor and an affluent picture a region a rung |
| Upkeep | 40 | a run-down picture a region a rung |
| Character | about 20 | § 7's first five, on the rungs where they fit |
| Function | about 15 | § 7's last five |
| Conditions | about 6 | |
| Ports | about 13 | a small harbor and a major port a rung, a naval base |
| Mines and oil | about 12 | |
| Farmland, plantation, ranch | about 24 | four farm families × four rung groups, plus plantation and ranch |
| Forestry and cleared land | about 6 | |
| Energy landscapes | about 6 | joins the farmland and natural lists for states dominated by power buildings |
| Natural terrain | about 15 | optional late variants: a highway through the mountains, a pipeline in the tundra |

About 380 pictures. At BC7 (0.7 MB each) that is about 270 MB of `gfx/`; in vanilla's uncompressed format it
would be over 1 GB.

## 9. Waves

1. **Pilot (4), this pull request.** § 11.
2. **Calibration, then the city tier of the core grid (40).** An observer game's figures (largest-city
   people, `average_sol` and the expectations gap by year and by rung) fix the floors of §§ 5 and 6. Then 8
   regions × 5 rungs of the middle picture. After this wave every city past rung 1 has a picture of its
   time, and these stay the fallback for every size and level of prosperity. The 39 prompts beside the
   pilot's are in the registry (`CITY_STREETS`), unrendered: the renders wait on the owner's look at the
   pilot in game, which may change how a picture is composed for the panel.
3. **Worked land (about 60):** ports, mines and oil, farmland, forestry, energy. Its 58 prompts are drafted
   in the registry's `DRAFTS`, outside the wired list: each has its technology and, in plain words, when it
   should show, and none has a condition or a place in the weight yet. What this wave still has to design:
   the Port level that divides a harbor from a major port; what stands for a naval base now that 1.15 has
   no Naval Base building; when coal makes a mine a colliery; and how an oil field or a power landscape
   takes over the picture of the land it stands on (they have no terrain of their own, § 12), which needs a
   place in the weight above the rung.
4. **Town, metropolis, megacity (104).**
5. **Means and upkeep (120),** with their part of the yearly pass.
6. **Character, function, conditions (about 40),** with theirs. Its 39 prompts are drafted in `DRAFTS`
   (18 character, 15 function, 6 condition), for any region and on the rungs where each fits.
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
- **Overlays.** Every entry reuses a vanilla overlay whose content suits any painting of its kind: the port
  one (birds, light rays, mist), the mine one (clouds, mist), the European city one (birds, mist, two
  smokes). A mod-defined empty overlay is the fallback if a vanilla one sits badly; the mod has no entity
  files yet, so that is unread.
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

- § 5's three changes to vanilla's city families: Australia and New Zealand with North America, Mexico and
  the Caribbean with Latin America, and Middle Eastern over South Asian on the north-west frontier. Also
  whether Tibet and the Pacific islands should leave the European fallback for a family.
- The floors of §§ 5 and 6, until wave 2's observer game.
- Whether the city ladder should split at era 9 (a "global city" rung on Globalization) once rung 3's
  pictures exist.
- Whether the energy landscape pictures need their own prevailing-terrain rule, since the engine picks the
  terrain before any picture is weighed.
