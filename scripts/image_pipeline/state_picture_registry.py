"""The state pictures: one entry per banner picture, its conditions and its prompt.

The banner at the top of the state panel is the highest-weight entry of the
`textures` list of the state's prevailing terrain (common/terrain). Each entry
here is one picture, `gfx/state_pictures/te_<key>.dds` (1020 x 500), and says
when it applies. `scripts/generators/gen_state_pictures.py` writes
`common/terrain/te_state_pictures_generated.txt` from the entries whose `seed`
is set (a picked, committed picture); an entry with `seed: None` is planned art
and wires nothing. DRAFTS holds the prompts of the waves whose conditions aren't
designed yet. The design, the axes and the full planned set:
docs/superpowers/specs/2026-11-10-state-pictures-design.md.

Fields:
  terrain  the vanilla terrain keys whose list the picture joins
  tech     the owner's technology that unlocks it (a live check in the weight)
  rung     its place on its family's technology ladder, 1-9: among the pictures
           that apply, a higher rung beats everything but a condition
  region   a family of REGION_GROUPS (city, farm or forest), or None for any region; a
           group's fallback family also shows in the states of no family, as vanilla's
           European city picture and its generic farmland do
  scale    optional key of SCALES: a major port, a colliery (a building's level)
  over     optional True: the picture takes over another family's terrain (an oil
           field on farmland) and outranks every rung of that terrain's own pictures
  size     a key of SIZES, or None for any size (the family's middle picture,
           which stays the fallback for the sizes not painted yet)
  where    optional extra state triggers, one a line
  effect   the animated overlay, required by the engine; a vanilla entity
  seed     the picked render, or None
  crop     optional (left, top, right, bottom) on the 1536 x 752 render, to drop a
           signature or a stray object at an edge; close to 2.04 : 1
  smudge   optional list of (left, top, right, bottom) boxes on the render, blurred
           before the crop: a lettered sign where a crop can't reach
  prompt   the subject; STYLE is appended

Writing a prompt: a picture stands for every state of its region, so it must not
read as one city. A generic building draws the most famous one of its kind ("a
domed civic building" drew the United States Capitol in a European street four
times out of four). Describe a landmark by features that belong to the region and
to no one building, or leave it out; shop fronts draw lettered signs, so ask for
plain awnings. PROMPT_AVOID lists those two and the words likely to do the same,
and test_state_pictures.py fails on a prompt that uses one. The design's section
10 has the review checks.

The renders are made outside the repo (FLUX.1-schnell at 1536 x 752, seeds
1000 + seed as the icon pipeline's are); a pick is converted with
scripts/image_pipeline/convert_state_picture.py, which crops it, gives it a
painted look and compresses it.
"""

# The look goes first: CLIP reads only the first 77 tokens of a prompt, and its pooled embedding
# carries the look. With the style after the subject the renders came out flat and poster-like.
STYLE = (
    "A digital matte painting for a grand strategy game, loosely hand-painted with textured brush "
    "strokes, rich light and deep shadows, a dramatic cloudy sky, soft atmospheric haze in the "
    "distance, cinematic wide composition"
)
TAIL = ", no text, no writing, no lettering on signs, no watermark, no signature"

# Words a prompt must not use. Two are from the pilot's renders: shop fronts came out with
# lettered signs, and "a domed civic building" drew the United States Capitol. The rest are
# precautions of the same kind, not yet seen: signs, banners and posters invite lettering, a flag
# a real country's, a skyline a known one.
PROMPT_AVOID = (
    "shop", "shops", "shopfront", "shopfronts", "sign", "signs", "signboard", "signboards", "neon",
    "billboard", "billboards", "banner", "banners", "flag", "flags", "poster", "posters", "skyline",
    "shopping", "filling station", "motel", "diner",
    "civic", "capitol",
)

# Region families of the city pictures: (state triggers, any one of which puts a state in the
# family; the family's digit in the weight). Vanilla's seven city families by vanilla's own
# triggers, with three changes (design section 5): Latin American is the whole
# geographic_region_latin_america, which adds Mexico and the Caribbean to the five regions of
# vanilla's is_subtropic_farmland; North American is new and takes Australia and New Zealand; and
# the digits rank the families where two overlap (in 1.15: Japan lies inside East Asia, and
# Baluchistan, Pashtunistan and Quetta are in both India and the Middle East).
REGIONS = {
    "european": (["is_in_geographic_region = geographic_region_europe"], 1),
    "north_american": ([
        "is_in_geographic_region = geographic_region_north_america",
        "is_in_geographic_region = geographic_region_australasia",
    ], 2),
    "latin_american": (["is_in_geographic_region = geographic_region_latin_america"], 3),
    "african": (["is_in_geographic_region = geographic_region_africa"], 4),
    "south_asian": (["is_in_geographic_region = geographic_region_india"], 5),
    "middle_eastern": ([
        "is_in_geographic_region = geographic_region_middle_east",
        "is_in_geographic_region = geographic_region_central_asia_old",
    ], 6),
    "east_asian": ([
        "is_in_geographic_region = geographic_region_east_asia",
        "is_in_geographic_region = geographic_region_south_east_asia",
    ], 7),
    "japanese": (["is_in_geographic_region = geographic_region_japan"], 8),
}
# The family whose pictures also show in the states of no family (in 1.15: Tibet and the
# Himalayas, and the Pacific islands), as vanilla's European city picture does.
FALLBACK_REGION = "european"
# (the family that wins, the family it overlaps). A rung outranks a family's digit, so the winner
# needs its own picture wherever the other has one: an East Asian picture of rung 2 wired without
# the Japanese one would show in Tokyo over Japan's rung 1. The test holds a wave to that.
REGION_OVERLAPS = (("japanese", "east_asian"), ("middle_eastern", "south_asian"))

# Farmland families: vanilla's four, by vanilla's own scripted triggers. They don't overlap (1.15:
# 157 Arabic states, which is the Middle East and most of Africa; 68 Asian; 61 subtropic, which is
# Latin America; 390 generic, India and Oceania among them). The generic family is the states of
# no other, as in vanilla.
FARM_REGIONS = {
    "farm_generic": ([], 1),
    "farm_arabic": (["is_arabic_farmland = yes"], 2),
    "farm_asian": (["is_asian_farmland = yes"], 3),
    "farm_subtropic": (["is_subtropic_farmland = yes"], 4),
}
# Forestry: the tropical picture, where the forest is rainforest. No fallback: the conifer picture
# has no region and stands everywhere else.
FOREST_REGIONS = {
    "forest_tropical": ([
        "is_in_geographic_region = geographic_region_south_east_asia",
        "is_in_geographic_region = geographic_region_equatorial_africa",
        "is_in_geographic_region = geographic_region_west_africa",
        "is_in_geographic_region = geographic_region_central_america",
        "is_in_geographic_region = geographic_region_gran_colombia",
        "is_in_geographic_region = geographic_region_brazil",
        "is_jungle_hills = yes",
    ], 1),
}
# Every region family by its group; a group's fallback family also takes the states of no family.
REGION_GROUPS = {"city": REGIONS, "farm": FARM_REGIONS, "forest": FOREST_REGIONS}
GROUP_FALLBACK = {"city": FALLBACK_REGION, "farm": "farm_generic"}


def region_group(region: str) -> str:
    return next(group for group, families in REGION_GROUPS.items() if region in families)


def region_digit(region: str) -> int:
    return REGION_GROUPS[region_group(region)][region][1]


# Scales: the larger or the special kind of a worked-land picture, in the size place of the weight
# (a picture has a size or a scale, never both). A major port is a Port's level, read live:
# provisional, from a 1940 save, where 44 of 405 port states have a Port of 20 or more (in 1836
# the largest is Guangdong's, 15). A colliery is the yearly pass's tag (te_sp_coal: coal is the
# larger part of the state's mines; common/scripted_effects/te_state_picture_effects.txt).
PORT_MAJOR_LEVEL = 20
SCALES = {
    "major_port": ([f"any_scope_building = {{ is_building_type = building_port level >= {PORT_MAJOR_LEVEL} }}"], 2),
    "colliery": (["has_variable = te_sp_coal"], 1),
}

# City sizes, from the yearly pass's state variable te_sp_size (1 town, 2 city,
# 3 metropolis, 4 megacity; common/scripted_effects/te_state_picture_effects.txt).
# (trigger lines, the size's digit in the weight)
SIZES = {
    "town": (["has_variable = te_sp_size", "var:te_sp_size <= 1"], 1),
    "metropolis": (["has_variable = te_sp_size", "var:te_sp_size >= 3"], 3),
    "megacity": (["has_variable = te_sp_size", "var:te_sp_size >= 4"], 4),
}

# The weight is a number in place value, so the most specific picture that
# applies wins and nothing ties: rung, then size, then a named region. The
# design reserves the places between and above for prosperity, character and
# conditions. Vanilla's own weights are 1 and 2, so any picture here that
# applies outranks vanilla's.
W_RUNG = 100000
W_SIZE = 10
W_REGION = 1  # times the family's digit, 1 to 8
# A picture that takes over another family's terrain (an oil field on farmland) outranks every
# rung of that terrain's own pictures: "over" in its entry.
W_OVER = 10000000

PICTURES = {
    "urban_european_1": {
        "terrain": ["urban"],
        "tech": "art_deco_architecture",
        "rung": 1,
        "region": "european",
        "size": None,
        "effect": "vfx_entity_ui_state_urban_european",
        "seed": 3,
        "crop": (0, 60, 1410, 751),
        "prompt": (
            "A European city street in the early 1930s: five-storey stone apartment buildings "
            "with plain striped awnings framing both sides, an electric tram on rails in the "
            "middle distance under overhead wires, a few rounded 1930s automobiles, pedestrians "
            "in coats and hats on the pavements, iron street lamps, a baroque church with a green "
            "copper dome and twin bell towers hazy at the end of the street"
        ),
    },
    "urban_european_1_metropolis": {
        "terrain": ["urban"],
        "tech": "art_deco_architecture",
        "rung": 1,
        "region": "european",
        "size": "metropolis",
        "effect": "vfx_entity_ui_state_urban_european",
        "seed": 3,
        "crop": (146, 60, 1390, 670),
        "prompt": (
            "The center of a great European metropolis in the 1930s seen along a wide "
            "boulevard: tall stone and art deco office buildings and department stores of ten "
            "to fifteen storeys stepping back into haze, dense traffic of 1930s automobiles "
            "and double-deck buses, trams, crowds on broad pavements, an iron railway viaduct "
            "crossing the street in the distance, chimney smoke drifting over the roofs"
        ),
    },
    "docks_1": {
        "terrain": ["docks"],
        "tech": "modern_tools",
        "rung": 1,
        "region": None,
        "size": None,
        # the docks terrain also prevails in any one-province state, port or not, where vanilla
        # shows its dry plain: the port picture asks for a port, as vanilla's does
        "where": ["has_building = building_port"],
        "effect": "vfx_entity_ui_state_docks",
        "seed": 3,
        "crop": (0, 0, 1510, 740),
        "smudge": [(1066, 526, 1102, 562)],
        "prompt": (
            "A large seaport in the 1930s: a black-hulled ocean liner with two funnels moored "
            "at a concrete quay, a row of tall steel dockside cranes on rails, brick "
            "warehouses, railway wagons, stacked crates and barrels in the foreground, a "
            "tugboat on grey-green water, steam and smoke drifting"
        ),
    },
    "mining_1": {
        "terrain": ["mining"],
        "tech": "modern_tools",
        "rung": 1,
        "region": None,
        "size": None,
        "effect": "vfx_entity_ui_state_mining",
        "seed": 3,
        "prompt": (
            "A large open-pit mine in the 1930s in a dry hilly landscape: terraced benches cut "
            "into the earth, a huge dragline excavator with a long lattice boom at work, a "
            "steam shovel loading ore wagons behind a small locomotive, heavy dump trucks on "
            "a dirt haul road, dark spoil heaps, dust in the air, hazy hills behind"
        ),
    },
}

# --- The city tier of the core grid (design section 9, wave 2): the middle picture of each
# region family on each rung of the city ladder. Planned art until an entry has a seed.

CITY_LADDER = {
    1: ("art_deco_architecture", "in the early 1930s"),
    2: ("modern_urban_planning", "around 1960"),
    3: ("computer_aided_design", "around 1990"),
    4: ("advanced_structural_engineering", "in the 2030s"),
    5: ("vactrains", "in the late twenty-first century"),
}

# Vanilla's overlay for the family's own city picture (North American shares the European one).
CITY_EFFECT = {
    "european": "vfx_entity_ui_state_urban_european",
    "north_american": "vfx_entity_ui_state_urban_european",
    "latin_american": "vfx_entity_ui_state_urban_latin_american",
    "african": "vfx_entity_ui_state_urban_african",
    "south_asian": "vfx_entity_ui_state_urban_arabic",
    "middle_eastern": "vfx_entity_ui_state_urban_arabic",
    "east_asian": "vfx_entity_ui_state_urban_asian",
    "japanese": "vfx_entity_ui_state_urban_asian",
}

# One landmark a family, at the end of the street on every rung, so a state's banner reads as the
# same place later while the street around it changes. Each is a kind of building many cities of
# the region have, described by features that fit no one of them (see "Writing a prompt").
CITY_LANDMARK = {
    "european": "a baroque church with a green copper dome and twin bell towers",
    "north_american": "a red sandstone courthouse with a square clock tower",
    "latin_american": "a white colonial church with two bell towers on a small plaza",
    "african": "a whitewashed market hall with a long arcade and a small clock turret",
    "south_asian": "a red sandstone clock tower with small domed kiosks at its corners",
    "middle_eastern": "a sand-colored stone mosque with a single dome and one slender minaret",
    "east_asian": "a many-tiered octagonal brick pagoda",
    "japanese": "a white-walled castle keep with grey tiled roofs on a stone base",
}

# The last rung is era 12 (general AI, nanofabrication, orbital industry, the vactrain), and the
# owner asked that it look it (2026-11-10: "the far future could look more futuristic, given the
# technologies in the last couple eras"). Its streets lead with the megastructures, flying craft and
# robots, keep the family's old quarter and landmark small beneath them, and end with this.
CITY_FAR_FUTURE_SKY = ", a spacecraft climbing on a thin white trail in the far sky"

# Vehicles: a date in the sentence ("around 1960") doesn't date the cars, which come out as the
# 2000s' unless the vehicles themselves carry a decade ("rounded 1950s cars"). The 1960 streets
# whose cars had one rendered in period; the two that didn't (European, Japanese) had modern
# cars in all four candidates and were reworded.
# {(region, rung): the street, without its date and landmark}. "{when}" is the rung's date.
CITY_STREETS = {
    ("european", 2): (
        "A European city avenue {when}: plain concrete and glass slab office blocks of eight to "
        "twelve storeys rising beside older five-storey stone apartment buildings, a wide asphalt "
        "road of small rounded 1950s cars, a rounded 1950s single-deck bus and a streamlined tram "
        "under overhead wires, pedestrians in raincoats and hats, tall lamp posts"
    ),
    ("european", 3): (
        "A European city avenue {when}: mirrored curtain-wall office towers of twenty storeys "
        "behind a row of restored stone apartment buildings, a paved pedestrian zone with young "
        "trees and plain parasols, boxy 1980s cars and an articulated bus on a multi-lane road, a "
        "concrete flyover crossing in the middle distance"
    ),
    ("european", 4): (
        "A European city avenue {when}: slender glass and timber towers with planted terraces "
        "behind restored stone apartment buildings, a sleek low-floor tram on a grassed track, "
        "smooth electric cars, many cyclists on a wide cycle lane, mature street trees, solar "
        "panels on the roofs"
    ),
    ("european", 5): (
        "A far-future European city {when}: colossal smooth white arcology towers a kilometre "
        "high, joined by sky bridges and wrapped in hanging gardens, rising behind preserved "
        "old stone apartment buildings, flying passenger craft crossing between the towers, a "
        "transparent vacuum-train tube on slender pylons, humanoid robots and people strolling "
        "a car-free street of trees, small pod vehicles"
    ),
    ("north_american", 1): (
        "A North American city main street {when}: brick and limestone commercial buildings of "
        "four to ten storeys with iron fire escapes and plain striped awnings, wooden water tanks "
        "on the rooftops, a streetcar on rails under overhead wires, boxy 1930s automobiles parked "
        "at the kerb, wooden utility poles, pedestrians in hats and overcoats"
    ),
    ("north_american", 2): (
        "A North American city main street {when}: flat-roofed glass and steel office slabs of "
        "fifteen storeys beside older brick blocks with fire escapes, a very wide street of long "
        "finned automobiles and a silver bus, open parking lots, traffic lights hung over the "
        "road, an elevated concrete freeway crossing in the middle distance"
    ),
    ("north_american", 3): (
        "A North American downtown street {when}: a cluster of dark glass curtain-wall office "
        "towers of thirty storeys above a multi-storey concrete parking garage and a few old brick "
        "blocks, a wide one-way street of boxy sedans, pickup trucks and a city bus, a freeway "
        "interchange on concrete stilts in the middle distance"
    ),
    ("north_american", 4): (
        "A North American downtown street {when}: tapering glass towers with sky gardens above "
        "converted old brick blocks, a light-rail train running down the planted median, electric "
        "pickup trucks and small driverless shuttles, a row of street trees and a cycle lane where "
        "a traffic lane was, solar arrays on the rooftops"
    ),
    ("north_american", 5): (
        "A far-future North American city {when}: a wall of kilometre-high stepped arcology "
        "towers with forested setbacks and landing decks, swarms of small flying craft between "
        "them, a transparent vacuum-train tube on tall pylons along the line of a former "
        "freeway, old brick blocks kept as a historic district, humanoid robots and people on a "
        "car-free street of trees, small pod vehicles"
    ),
    ("latin_american", 1): (
        "A Latin American city street {when}: two- and three-storey colonial houses in ochre, "
        "pink and white with wrought-iron balconies and red tile roofs, a few new art deco "
        "fronts, a small electric tram, 1930s automobiles and a mule cart, palm trees, people in "
        "white suits and straw hats, green hills behind"
    ),
    ("latin_american", 2): (
        "A Latin American city avenue {when}: white modernist concrete apartment blocks raised on "
        "columns with sun-screen grilles beside old colonial houses with red tile roofs, a wide "
        "avenue with a median of palm trees, rounded 1950s cars and brightly painted buses, "
        "people in light summer clothes, green hills behind"
    ),
    ("latin_american", 3): (
        "A Latin American city avenue {when}: concrete and glass towers of twenty storeys above "
        "old colonial fronts, dense traffic of small hatchbacks, minibuses and motorcycles, a "
        "tangle of overhead cables, street vendors under plain parasols, a hillside covered in "
        "small brick houses in the distance"
    ),
    ("latin_american", 4): (
        "A Latin American city avenue {when}: glass towers with green terraces above colonial "
        "fronts restored in bright colors, cable-car gondolas crossing high above the street "
        "toward a hillside of houses, long electric articulated buses in their own lane, palm "
        "trees, cyclists and walkers"
    ),
    ("latin_american", 5): (
        "A far-future Latin American city {when}: gigantic terraced arcology towers overgrown "
        "with tropical gardens and waterfalls rising a kilometre from the valley, flying "
        "passenger craft between them, a transparent vacuum-train tube crossing on white "
        "pylons, preserved colonial houses with red tile roofs, humanoid robots and people on a "
        "car-free street of palms, small pod vehicles, green hills behind"
    ),
    ("african", 1): (
        "A city street in colonial-era Africa {when}: whitewashed two-storey arcaded buildings "
        "with verandas and corrugated iron roofs, a busy open-air market under plain cloth "
        "awnings, bicycles, a few 1930s trucks and motor cars, people in flowing robes and in "
        "light suits, palm and acacia trees, red earth at the roadside"
    ),
    ("african", 2): (
        "An African city avenue {when}: new white concrete modernist office blocks of six to ten "
        "storeys with sun-screen facades beside older arcaded buildings, a wide paved avenue "
        "lined with red-blossomed flame trees, rounded 1950s cars, minibuses and many bicycles, "
        "crowds in bright printed cloth"
    ),
    ("african", 3): (
        "An African city avenue {when}: weathered concrete office towers of fifteen to twenty "
        "storeys, a crowded street of minibus taxis, motorcycles and hand carts, market stalls "
        "under plain parasols along the pavement, a tangle of power lines, crowds in bright "
        "printed cloth, red dust in the air"
    ),
    ("african", 4): (
        "An African city avenue {when}: new glass towers and construction cranes above older "
        "concrete blocks, a sleek light-rail train on an elevated viaduct, electric motorcycle "
        "taxis and buses, market stalls shaded by solar-panel canopies, flame trees, crowds in "
        "bright printed cloth"
    ),
    ("african", 5): (
        "A far-future African city {when}: soaring kilometre-high arcology towers of pale "
        "concrete and glass patterned like woven cloth and hung with gardens, flying passenger "
        "craft between them, a transparent vacuum-train tube on slender pylons, a car-free "
        "market street of acacia trees and bright stalls, humanoid robots carrying goods among "
        "the crowd, small pod vehicles"
    ),
    ("south_asian", 1): (
        "A South Asian city bazaar street {when}: three-storey buildings with carved wooden "
        "balconies over arcades and plain cloth awnings, an electric tram, bullock carts, hand-"
        "pulled rickshaws and a few 1930s motor cars, a dense crowd in white cotton, turbans and "
        "bright saris, a spreading banyan tree"
    ),
    ("south_asian", 2): (
        "A South Asian city street {when}: plain concrete blocks of four to six storeys and one "
        "modernist office building beside older houses with carved balconies, rounded 1950s cars, "
        "crowded buses, cycle rickshaws and a great many bicycles, overhead wires, a dense crowd "
        "in white cotton and bright saris"
    ),
    ("south_asian", 3): (
        "A South Asian city street {when}: concrete apartment and office blocks of ten storeys "
        "streaked by monsoon rain, three-wheeled auto rickshaws, motor scooters and crowded buses "
        "filling the road, a tangle of overhead cables, stalls under plain parasols, a dense "
        "crowd in bright clothes"
    ),
    ("south_asian", 4): (
        "A South Asian city street {when}: a sleek metro train on a concrete viaduct running "
        "above the middle of the street, glass office towers behind older concrete blocks, "
        "electric auto rickshaws and scooters, shade trees, stalls under plain parasols, a dense "
        "crowd in bright clothes"
    ),
    ("south_asian", 5): (
        "A far-future South Asian city {when}: immense kilometre-high arcology towers faced "
        "with carved stone lattice and hanging gardens rising above a preserved old bazaar "
        "quarter, swarms of small flying craft, a transparent vacuum-train tube on tall pylons, "
        "a car-free street of banyan trees and bright stalls, humanoid robots among a dense "
        "crowd, small pod vehicles"
    ),
    ("middle_eastern", 1): (
        "A Middle Eastern city street {when}: flat-roofed stone and plaster buildings of two and "
        "three storeys with wooden lattice bay windows, the arched entrance of a covered bazaar "
        "under plain cloth awnings, donkey carts, a few 1930s motor cars and a small bus, men in "
        "robes and in suits, date palms, dry hills behind"
    ),
    ("middle_eastern", 2): (
        "A Middle Eastern city boulevard {when}: new concrete apartment blocks of six storeys "
        "with deep balconies and plain awnings, a wide boulevard with a median of date palms, "
        "rounded 1950s cars and buses, the flat roofs of the old quarter behind, construction "
        "cranes, dry hills in the haze"
    ),
    ("middle_eastern", 3): (
        "A Middle Eastern city boulevard {when}: concrete and glass towers of twenty storeys "
        "above sand-colored apartment blocks with satellite dishes on their flat roofs, a multi-"
        "lane boulevard lined with date palms, boxy sedans, pickup trucks and buses, heat haze "
        "over dry hills"
    ),
    ("middle_eastern", 4): (
        "A Middle Eastern city boulevard {when}: tall glass towers wrapped in geometric lattice "
        "sun screens, a pedestrian street shaded by white fabric canopies, a driverless tram, "
        "smooth electric cars, rows of date palms, fields of solar panels on the dry hills "
        "behind"
    ),
    ("middle_eastern", 5): (
        "A far-future Middle Eastern city {when}: vast sand-colored arcology towers a kilometre "
        "high with shaded courtyards, wind towers and hanging gardens, flying passenger craft "
        "between them, a transparent vacuum-train tube on slender pylons, a car-free street of "
        "date palms and water channels, humanoid robots and people in robes, small pod vehicles"
    ),
    ("east_asian", 1): (
        "An East Asian city street {when}: two- and three-storey arcaded row houses with grey "
        "tiled roofs and plain cloth awnings, a few stone-fronted Western-style bank buildings, "
        "hand-pulled rickshaws, bicycles, an electric tram and a few 1930s motor cars, people in "
        "long gowns and in Western suits"
    ),
    ("east_asian", 2): (
        "An East Asian city avenue {when}: plain brick and concrete blocks of four to six storeys "
        "along a wide avenue with rows of plane trees, a great many bicycles, a few trucks and "
        "buses and a trolleybus under overhead wires, people in plain work clothes, factory "
        "chimneys in the distance"
    ),
    ("east_asian", 3): (
        "An East Asian city avenue {when}: white-tiled concrete towers of twenty storeys and "
        "construction cranes above the last rows of old tiled-roof houses, an elevated expressway "
        "crossing the street, streams of bicycles and motor scooters among buses and boxy taxis"
    ),
    ("east_asian", 4): (
        "An East Asian city avenue {when}: a dense forest of glass towers, elevated expressways "
        "and footbridges stacked above the street, a sleek high-speed train on a viaduct in the "
        "middle distance, electric scooters and cars, rows of ginkgo trees"
    ),
    ("east_asian", 5): (
        "A far-future East Asian city {when}: colossal kilometre-high arcology towers with "
        "sweeping tiled eaves and hanging gardens rising in ranks into the haze, streams of "
        "small flying craft between them, a transparent vacuum-train tube on tall pylons, a "
        "car-free street of ginkgo trees, humanoid robots and people, small pod vehicles"
    ),
    ("japanese", 1): (
        "A Japanese city street {when}: two-storey wooden town houses with grey tiled roofs and "
        "plain indigo door curtains, a few modern brick and concrete buildings of five storeys, "
        "an electric tram, bicycles, a rickshaw and a few 1930s motor cars, people in kimono and "
        "in Western suits and hats, wooden utility poles strung with many wires"
    ),
    ("japanese", 2): (
        "A Japanese city street {when}: plain concrete office buildings of six to nine storeys "
        "among the last tiled wooden houses, a street of small three-wheeled 1950s trucks, tiny "
        "rounded 1950s cars, a tram and rounded 1950s buses, utility poles strung with dense "
        "wires, a blunt-nosed express train on an elevated concrete viaduct in the middle distance"
    ),
    ("japanese", 3): (
        "A Japanese city street {when}: tile-clad and glass office towers of twenty to thirty "
        "storeys, two elevated expressways stacked above the street, compact boxy cars and taxis, "
        "office workers with umbrellas on narrow pavements, utility poles and wires, a monorail "
        "on a single concrete beam in the middle distance"
    ),
    ("japanese", 4): (
        "A Japanese city street {when}: slender glass towers with timber lattice facades and "
        "rooftop gardens, a long-nosed magnetic levitation train on a high viaduct in the middle "
        "distance, small electric cars and delivery robots, a narrow lane of low tiled houses "
        "kept between the towers, maple trees"
    ),
    ("japanese", 5): (
        "A far-future Japanese city {when}: immense kilometre-high timber-latticed arcology "
        "towers with tiled eaves and terraced gardens of pine and maple, small flying craft "
        "between them, a transparent vacuum-train tube on slender pylons, a car-free street of "
        "low tiled houses kept at the towers' feet, humanoid robots and people, small pod "
        "vehicles"
    ),
}

# The picked render of each city picture, with the boxes that drop or blur its lettering. Seed 2
# often leaves a dark strip of 9 to 25 pixels along the bottom of a render; its picks crop it off
# (the converter refuses a picture with one).
CITY_PICKS = {
    "urban_european_2": {"seed": 3, "smudge": [(8, 534, 62, 580), (1340, 630, 1408, 676)]},
    "urban_european_3": {"seed": 3},
    "urban_european_4": {"seed": 3},
    "urban_north_american_1": {"seed": 0, "crop": (30, 0, 1480, 711),
                               "smudge": [(1290, 480, 1335, 530), (760, 238, 786, 262)]},
    "urban_north_american_2": {"seed": 1},
    "urban_north_american_3": {"seed": 1, "crop": (160, 0, 1536, 675), "smudge": [(430, 558, 530, 582)]},
    "urban_north_american_4": {"seed": 0},
    "urban_latin_american_1": {"seed": 2, "crop": (30, 0, 1507, 724)},
    "urban_latin_american_2": {"seed": 0},
    "urban_latin_american_3": {"seed": 0, "crop": (0, 15, 1490, 745), "smudge": [(1285, 440, 1356, 536)]},
    "urban_latin_american_4": {"seed": 2},
    "urban_african_1": {"seed": 0},
    "urban_african_2": {"seed": 0, "smudge": [(308, 158, 356, 184), (52, 488, 108, 506)]},
    "urban_african_3": {"seed": 2, "crop": (30, 0, 1507, 724)},
    "urban_african_4": {"seed": 2, "crop": (30, 0, 1507, 724)},
    "urban_south_asian_1": {"seed": 2, "crop": (30, 0, 1507, 724)},
    "urban_south_asian_2": {"seed": 3},
    "urban_south_asian_3": {"seed": 3},
    "urban_south_asian_4": {"seed": 3, "crop": (0, 15, 1476, 739)},
    "urban_middle_eastern_1": {"seed": 1},
    "urban_middle_eastern_2": {"seed": 1},
    "urban_middle_eastern_3": {"seed": 3},
    "urban_middle_eastern_4": {"seed": 0, "crop": (50, 14, 1536, 742)},
    "urban_east_asian_1": {"seed": 1, "smudge": [(1250, 480, 1312, 528), (1432, 458, 1522, 490),
                                                 (1128, 472, 1178, 520), (1445, 625, 1502, 697)]},
    "urban_east_asian_2": {"seed": 2, "crop": (30, 0, 1507, 724)},
    "urban_east_asian_3": {"seed": 0},
    "urban_east_asian_4": {"seed": 0, "crop": (30, 0, 1458, 700)},
    "urban_japanese_1": {"seed": 3, "smudge": [(1212, 470, 1258, 605), (652, 500, 672, 560), (955, 490, 982, 560)]},
    "urban_japanese_2": {"seed": 2, "crop": (30, 0, 1507, 724)},
    "urban_japanese_3": {"seed": 2, "crop": (30, 0, 1507, 724)},
    "urban_japanese_4": {"seed": 0},
    # the last rung, from the second set of renders (the bolder prompts)
    "urban_european_5": {"seed": 0},
    "urban_north_american_5": {"seed": 0, "smudge": [(40, 446, 150, 468)]},
    "urban_latin_american_5": {"seed": 0},
    "urban_african_5": {"seed": 3, "crop": (110, 0, 1536, 698)},  # drops a big wheel's arc at the left edge
    "urban_south_asian_5": {"seed": 0},
    "urban_middle_eastern_5": {"seed": 3},
    "urban_east_asian_5": {"seed": 0},
    "urban_japanese_5": {"seed": 3},
}

for (_region, _rung), _street in CITY_STREETS.items():
    _tech, _when = CITY_LADDER[_rung]
    PICTURES[f"urban_{_region}_{_rung}"] = {
        "terrain": ["urban"],
        "tech": _tech,
        "rung": _rung,
        "region": _region,
        "size": None,
        "effect": CITY_EFFECT[_region],
        "seed": None,
        **CITY_PICKS.get(f"urban_{_region}_{_rung}", {}),
        "prompt": (f"{_street.format(when=_when)}, {CITY_LANDMARK[_region]} hazy at the end of the street"
                   + (CITY_FAR_FUTURE_SKY if _rung == 5 else "")),
    }

# --- Drafts for the later waves (design section 9). A draft is a prompt with the technology
# and rung it belongs to and, in plain words, when it should show. It is not in PICTURES, so it
# wires nothing and takes no place in the weights; its conditions and its place in the weight are
# settled when its wave is built, and the entry moves to PICTURES then. full_prompt() reads both,
# so a draft can be rendered and reviewed before that.
#   family   the group it is reviewed with
#   terrain  the vanilla terrains whose lists it is meant to join
#   like     vanilla's picture of the same subject, for the review sheet
#   shows    when it should show, beyond its technology (plain words, not script)

WHEN = {  # a technology's date in a prompt, by its era
    "modern_tools": "in the 1930s", "modern_chemical_processes": "in the 1930s",
    "rural_electrification": "in the 1930s",
    "integrated_circuits": "around 1960", "green_revolution": "around 1960",
    "containerization": "around 1980", "robotics": "around 1980", "microprocessor": "around 1980",
    "supply_chain_management": "around 2000", "hydraulic_fracturing": "around 2000",
    "internet_of_things": "in the 2020s",
    "autonomous_vehicles": "in the 2040s", "synthetic_biology": "in the 2040s",
    **{tech: when for tech, when in CITY_LADDER.values()},
}

FARMLAND = ["farmland_rye", "farmland_rice", "farmland_millet", "farmland_wheat", "farmland_maize"]
# Oil fields have no terrain of their own: the engine picks a state's terrain before any picture
# is weighed, so their pictures join the lists of the land they stand on.
OPEN_LAND = ["plains", "desert", "savanna", "tundra", "hills", *FARMLAND, "pasture"]


def _draft(family, terrain, like, tech, rung, shows, prompt):
    return {"family": family, "terrain": terrain, "like": like, "tech": tech, "rung": rung,
            "shows": shows, "prompt": prompt.format(when=WHEN[tech])}


DRAFTS = {
    # ---- Wave 3: worked land ------------------------------------------------------------------
    # Ports. docks_1 (the pilot) is the major port of rung 1.
    "docks_harbor_1": _draft(
        "port", ["docks"], "docks", "modern_tools", 1, "a Port below the major port's level",
        "A small fishing and coasting harbor {when}: a stone breakwater and a short quay, steam "
        "trawlers and wooden fishing boats, a small coastal steamer unloading under a single hand "
        "crane, nets drying on poles, stacked fish crates, low stone warehouses and cottages "
        "behind, gulls, a small white lighthouse at the end of the breakwater"),
    "docks_harbor_2": _draft(
        "port", ["docks"], "docks", "containerization", 2, "a Port below the major port's level",
        "A small harbor {when}: steel trawlers and a small coastal freighter at a concrete quay, "
        "a mobile crane on tyres, a few plain steel shipping containers stacked two high, a cold-"
        "store shed, round fuel tanks, trucks, a breakwater with a small white lighthouse, gulls"),
    "docks_harbor_3": _draft(
        "port", ["docks"], "docks", "supply_chain_management", 3, "a Port below the major port's level",
        "A small harbor {when}: a roll-on roll-off ferry with its bow ramp down and trucks "
        "driving off, a marina of white yachts, a few steel trawlers, one harbor crane, a low "
        "glass terminal building, plain steel containers in a small stack, a breakwater with a "
        "small white lighthouse"),
    "docks_harbor_4": _draft(
        "port", ["docks"], "docks", "autonomous_vehicles", 4, "a Port below the major port's level",
        "A futuristic small harbor {when}: sleek white autonomous cargo vessels with smooth "
        "windowless hulls, no masts and no wheelhouse, gliding to a quay, a hydrofoil passenger "
        "ferry riding above the water, a slender white robotic crane arm, curved harbor sheds "
        "roofed in dark solar glass, small cargo drones overhead, rows of seaweed-farm buoys in "
        "the bay, white offshore wind turbines on the horizon, a breakwater with a small white "
        "lighthouse"),
    "docks_2": _draft(
        "port", ["docks"], "docks", "containerization", 2, "a major Port",
        "A large container port {when}: a container ship stacked with plain unmarked steel boxes "
        "in rust red, blue and green at a long concrete quay, tall gantry cranes lifting boxes, "
        "straddle carriers, long rows of stacked containers, railway tracks and trucks, an oil "
        "tanker waiting offshore, haze over the water"),
    "docks_3": _draft(
        "port", ["docks"], "docks", "supply_chain_management", 3, "a major Port",
        "A vast container terminal {when}: two enormous container ships under a long row of giant "
        "gantry cranes, unmanned stacking cranes straddling endless blocks of plain colored steel "
        "boxes, driverless carriers on marked lanes, double-stacked container trains, warehouses "
        "reaching to the horizon"),
    "docks_4": _draft(
        "port", ["docks"], "docks", "autonomous_vehicles", 4, "a major Port",
        "A futuristic automated container port {when}: a huge low cargo ship stacked high with "
        "plain colored steel boxes, with no bridge and no funnel and four tall rigid white wing "
        "sails standing along its deck, rows of slender white robotic gantry cranes with no cabs "
        "lifting boxes, flat driverless electric carriers in convoy, cargo drones overhead, long "
        "blocks of stacked steel boxes, no people anywhere, offshore wind turbines on the horizon"),

    # Mines. mining_1 (the pilot) is the open pit of rung 1.
    "mining_2": _draft(
        "mine", ["mining"], "mining", "robotics", 2, "",
        "A huge open-pit mine {when}: terraced benches spiralling down into the earth, giant "
        "yellow haul trucks with wheels taller than a man, electric rope shovels, a concrete "
        "crushing and sorting plant fed by long covered conveyors, grey spoil heaps, dust in the "
        "air, hazy hills behind"),
    "mining_3": _draft(
        "mine", ["mining"], "mining", "internet_of_things", 3, "",
        "A remote-run open-pit mine {when}: a convoy of huge driverless haul trucks with no cabs "
        "on the haul road, autonomous drill rigs on the benches, sensor masts and antenna towers "
        "on the rim, a low white control building beside a field of solar panels, covered "
        "conveyors, no people in sight"),
    "mining_deep_1": _draft(
        "mine", ["mining"], "mining", "modern_tools", 1, "coal mines are the larger part of the state's mines",
        "A coal mining town {when}: steel headframes with spoked winding wheels over the shafts, "
        "brick engine houses, tall chimneys pouring smoke, conical black slag heaps, long rows of "
        "loaded coal wagons, terraces of miners' houses under a sooty sky"),
    "mining_deep_2": _draft(
        "mine", ["mining"], "mining", "robotics", 2, "coal mines are the larger part of the state's mines",
        "A modern colliery {when}: square concrete winding towers, a coal washing plant with "
        "covered conveyors running between its buildings, a long coal train loading under a "
        "bunker, half-grassed slag heaps, the cooling towers of a power station in the haze"),
    "mining_deep_3": _draft(
        "mine", ["mining"], "mining", "internet_of_things", 3, "coal mines are the larger part of the state's mines",
        "A deep mine {when}: one sleek enclosed shaft tower, an electric freight train loading "
        "automatically under a silo, old spoil heaps reclaimed with young trees and fields of "
        "solar panels, sensor masts, a few workers in bright jackets"),

    # Oil fields. No terrain of their own.
    "oil_1": _draft(
        "oil", OPEN_LAND, "plains_arid", "modern_chemical_processes", 1, "Oil Rigs dominate the state",
        "An oil field {when}: a forest of wooden and steel lattice derricks crowded across a "
        "dusty plain, nodding pumpjacks, riveted storage tanks, pipelines on trestles, a gas "
        "flare, tank wagons on a rail siding, pools of black mud, workers' shacks, dark smoke"),
    "oil_2": _draft(
        "oil", OPEN_LAND, "plains_arid", "integrated_circuits", 2, "Oil Rigs dominate the state",
        "An oil field {when}: tall steel drilling rigs spaced across a dry plain, rows of "
        "pumpjacks, silver spherical and cylindrical tanks, a small refinery with distillation "
        "columns and a burning flare stack, pipelines running to the horizon, tanker trucks"),
    "oil_3": _draft(
        "oil", OPEN_LAND, "plains_arid", "hydraulic_fracturing", 3, "Oil Rigs dominate the state",
        "A shale oil field {when}: square gravel well pads dotted across a rolling plain, each "
        "with a slim drilling rig, ranks of pump trucks and water tanks, pumpjacks, small gas "
        "flares, a grid of dirt roads and a buried pipeline's scar running to the horizon"),

    # Farmland: vanilla's four families.
    "farmland_generic_1": _draft(
        "farm", FARMLAND, "farmland_generic", "rural_electrification", 1, "vanilla's generic farmland family",
        "Temperate farmland {when}: a patchwork of wheat fields and hedgerows, a small grey "
        "tractor pulling a reaper-binder while a team of horses works the next field, a "
        "farmstead with a barn, a new line of wooden electricity poles along the lane, "
        "haystacks, a wind pump, a village steeple far off"),
    "farmland_generic_2": _draft(
        "farm", FARMLAND, "farmland_generic", "green_revolution", 2, "vanilla's generic farmland family",
        "Temperate farmland {when}: broad hedgeless fields of golden wheat, a row of red combine "
        "harvesters unloading into trucks, tall cylindrical grain silos beside the farmstead, "
        "irrigation sprinklers on a green field, a small biplane spraying low over the crop"),
    "farmland_generic_3": _draft(
        "farm", FARMLAND, "farmland_generic", "microprocessor", 3, "vanilla's generic farmland family",
        "Temperate farmland {when}: enormous fields to the horizon, huge articulated tractors "
        "drawing wide implements, a long center-pivot irrigation arm on wheels, clusters of big "
        "steel grain bins, long low livestock sheds, a line of pylons crossing the land"),
    "farmland_generic_4": _draft(
        "farm", FARMLAND, "farmland_generic", "autonomous_vehicles", 4, "vanilla's generic farmland family",
        "Temperate farmland {when}: cabless autonomous harvesters and swarms of small field "
        "robots working strips of different crops, drones overhead, tall wind turbines, solar "
        "panels raised over a field of vegetables, a small barn with a mast of antennas"),
    "farmland_arabic_1": _draft(
        "farm", FARMLAND, "farmland_arabic", "rural_electrification", 1, "vanilla's Arabic farmland family (the Middle East and most of Africa)",
        "Irrigated farmland in a hot dry country {when}: small plots of wheat and cotton between "
        "mud-walled water channels, date palms, a diesel pump house beside an old wooden water "
        "wheel, an early tractor and a pair of oxen ploughing, a flat-roofed mud-brick village, "
        "donkeys, bare hills behind"),
    "farmland_arabic_2": _draft(
        "farm", FARMLAND, "farmland_arabic", "green_revolution", 2, "vanilla's Arabic farmland family (the Middle East and most of Africa)",
        "Irrigated farmland in a hot dry country {when}: long straight concrete canals with "
        "sluice gates, large green fields of cotton and wheat against tawny desert, tractors, "
        "sprinklers, a village with a concrete water tower and grain silos, groves of date palms"),
    "farmland_arabic_3": _draft(
        "farm", FARMLAND, "farmland_arabic", "microprocessor", 3, "vanilla's Arabic farmland family (the Middle East and most of Africa)",
        "Desert farmland {when} seen from a rise: great green circles of center-pivot fields on "
        "tawny sand, long rows of plastic greenhouses, date palms planted in grids, pump "
        "stations and pipelines, trucks on a straight road, bare hills in the heat haze"),
    "farmland_arabic_4": _draft(
        "farm", FARMLAND, "farmland_arabic", "autonomous_vehicles", 4, "vanilla's Arabic farmland family (the Middle East and most of Africa)",
        "Desert farmland {when}: canals roofed with solar panels, drip-irrigated fields tended "
        "by cabless autonomous tractors, white shade-net houses, a desalination plant with "
        "pipelines, groves of date palms, drones overhead, bare hills in the heat haze"),
    "farmland_asian_1": _draft(
        "farm", FARMLAND, "farmland_asian", "rural_electrification", 1, "vanilla's Asian farmland family",
        "Rice paddies {when}: flooded fields between narrow earth dikes, farmers in conical hats "
        "transplanting seedlings by hand, water buffalo, a small diesel pump, a new line of "
        "electricity poles along a dike, a village of tiled and thatched roofs in a bamboo grove, "
        "misty hills"),
    "farmland_asian_2": _draft(
        "farm", FARMLAND, "farmland_asian", "green_revolution", 2, "vanilla's Asian farmland family",
        "Rice paddies {when}: wide regular fields of bright green rice, farmers in conical hats "
        "behind two-wheeled walking tractors, concrete irrigation canals with sluice gates, "
        "threshing machines on a drying yard, a village of tin and tile roofs, misty hills"),
    "farmland_asian_3": _draft(
        "farm", FARMLAND, "farmland_asian", "microprocessor", 3, "vanilla's Asian farmland family",
        "Rice paddies {when}: small rice combine harvesters and mechanical transplanters at work "
        "in regular fields, concrete-lined canals, rows of plastic greenhouses, fish ponds, a "
        "village of concrete houses, a line of pylons, misty hills"),
    "farmland_asian_4": _draft(
        "farm", FARMLAND, "farmland_asian", "autonomous_vehicles", 4, "vanilla's Asian farmland family",
        "Rice paddies {when}: drones flying in formation low over bright green fields, small "
        "autonomous transplanters with no drivers, solar panels floating on a pond, a glass "
        "vertical-farm building beside a neat village, misty hills"),
    "farmland_subtropic_1": _draft(
        "farm", FARMLAND, "farmland_subtropic", "rural_electrification", 1, "vanilla's subtropic farmland family (Latin America)",
        "Farmland in the Latin American tropics {when}: fields of maize and sugar cane on red "
        "earth, a whitewashed estate house with red tile roofs, ox carts and one early tractor, "
        "workers in straw hats, palm trees, a new line of electricity poles, green mountains"),
    "farmland_subtropic_2": _draft(
        "farm", FARMLAND, "farmland_subtropic", "green_revolution", 2, "vanilla's subtropic farmland family (Latin America)",
        "Farmland in the Latin American tropics {when}: wide fields of maize and soybeans newly "
        "cut from the forest, tractors, a small plane spraying, round grain silos, trucks on a "
        "red dirt road, a whitewashed estate house, green mountains"),
    "farmland_subtropic_3": _draft(
        "farm", FARMLAND, "farmland_subtropic", "microprocessor", 3, "vanilla's subtropic farmland family (Latin America)",
        "Farmland in the Latin American tropics {when}: immense soybean fields to the horizon, a "
        "line of green combine harvesters working abreast in a cloud of dust, grain trucks "
        "alongside, tall silos, strips of remaining forest, a red dirt road"),
    "farmland_subtropic_4": _draft(
        "farm", FARMLAND, "farmland_subtropic", "autonomous_vehicles", 4, "vanilla's subtropic farmland family (Latin America)",
        "Farmland in the Latin American tropics {when}: cabless autonomous harvesters working "
        "abreast, drones overhead, belts of replanted trees between the fields, solar panels "
        "beside tall silos, a red dirt road, green mountains"),
    "farmland_5": _draft(
        "farm", FARMLAND, "farmland_generic", "synthetic_biology", 5, "any farmland",
        "Farmland {when}: tall glass vertical-farm towers glowing violet among fields of "
        "engineered crops in blue-green and deep purple, rows of steel bioreactor tanks, a few "
        "autonomous machines, broad belts of restored woodland and meadow"),

    # Plantations and ranches, on the farm ladder.
    "plantation_1": _draft(
        "farm", ["plantation"], "plantation", "rural_electrification", 1, "",
        "A tropical plantation {when}: long rows of banana plants and coffee bushes on red "
        "earth, a planter's bungalow with a wide veranda, a processing shed with a chimney, a "
        "narrow-gauge railway with loaded wagons, workers carrying baskets, palm trees"),
    "plantation_2": _draft(
        "farm", ["plantation"], "plantation", "green_revolution", 2, "",
        "A tropical plantation {when}: straight rows of banana plants to the horizon, a small "
        "plane spraying low, tractors with trailers of green fruit, a packing plant under "
        "corrugated roofs, trucks, rows of workers' houses, palm trees"),
    "plantation_3": _draft(
        "farm", ["plantation"], "plantation", "microprocessor", 3, "",
        "A tropical plantation {when}: endless regular rows of oil palms over low hills, a "
        "palm-oil mill with a smoking stack and round tanks, trucks heaped with red fruit "
        "bunches, straight red dirt roads, a wall of rainforest at the edge"),
    "plantation_4": _draft(
        "farm", ["plantation"], "plantation", "autonomous_vehicles", 4, "",
        "A tropical plantation {when}: robotic harvesters with long arms working among rows of "
        "oil palms grown under taller shade trees, drones overhead, a clean white mill with "
        "solar roofs, electric trucks, a broad belt of rainforest kept at the edge"),
    "pasture_1": _draft(
        "farm", ["pasture"], "pasture", "rural_electrification", 1, "",
        "Ranch land {when}: wide fenced pasture with a herd of cattle, riders on horseback, a "
        "wind pump and a round water tank, wooden corrals, a ranch house and barn with a new "
        "electricity line, one pickup truck, dust, distant hills"),
    "pasture_2": _draft(
        "farm", ["pasture"], "pasture", "green_revolution", 2, "",
        "Ranch land {when}: cattle in fenced paddocks and long feeding pens, cattle trucks at a "
        "loading ramp, tractors stacking hay bales, feed silos, an irrigated green field of "
        "fodder beside dry pasture, a wind pump, distant hills"),
    "pasture_3": _draft(
        "farm", ["pasture"], "pasture", "microprocessor", 3, "",
        "Ranch land {when}: a vast feedlot of thousands of cattle in square pens, a feed mill "
        "with tall towers, feed trucks, a helicopter mustering a herd on the open range "
        "beyond, a center-pivot field of green fodder, distant hills"),
    "pasture_4": _draft(
        "farm", ["pasture"], "pasture", "autonomous_vehicles", 4, "",
        "Ranch land {when}: cattle wearing small solar collars grazing open pasture with no "
        "fences, drones herding them, a driverless feed wagon, tall wind turbines and fields of "
        "solar panels on the range, a low ranch house, distant hills"),

    # Forestry and cleared land.
    "forestry_1": _draft(
        "forest", ["forestry"], "forestry", "modern_tools", 1, "",
        "A logging camp in a conifer forest {when}: lumberjacks with early chainsaws and axes "
        "among huge felled trunks, a crawler tractor dragging logs, a loaded log truck, a river "
        "full of floating logs, a sawmill with a tall smoking burner, stumps, misty mountains"),
    "forestry_2": _draft(
        "forest", ["forestry"], "forestry", "robotics", 2, "",
        "A managed forest {when}: a wheeled harvesting machine with a felling arm stripping a "
        "trunk, a forwarder stacked with logs, even blocks of planted spruce, a cleared strip "
        "replanted with seedlings, log trucks on a gravel road, the steam plume of a pulp mill "
        "far off"),
    "forestry_tropical_1": _draft(
        "forest", ["forestry"], "forestry", "modern_tools", 1, "a jungle state",
        "Tropical logging {when}: giant buttressed hardwood trunks felled in rainforest, a "
        "crawler tractor and teams of men hauling logs to a muddy river, rafts of logs afloat, "
        "a sawmill on stilts with a tin roof, smoke, a wall of jungle behind"),
    "forestry_tropical_2": _draft(
        "forest", ["forestry"], "forestry", "robotics", 2, "a jungle state",
        "Tropical logging {when}: a red earth road cut through rainforest, yellow bulldozers and "
        "skidders, trucks each carrying three huge logs, a log yard, a cleared hillside with "
        "smoke rising, a wall of jungle behind"),
    "cleared_land_1": _draft(
        "forest", ["cleared_land"], "cleared_land", "modern_tools", 1, "",
        "Newly cleared land {when}: a field of tree stumps, piles of brush burning, settlers' "
        "wooden cabins, a tractor pulling out a stump with a chain, the first fenced fields, "
        "stacks of sawn timber, the dark edge of the forest behind"),
    "cleared_land_2": _draft(
        "forest", ["cleared_land"], "cleared_land", "robotics", 2, "",
        "Newly cleared land {when}: forest pushed down by bulldozers into long burning windrows, "
        "a new straight gravel road, cattle grazing among charred stumps, a prefabricated "
        "farmhouse, the standing wall of forest behind"),

    # ---- Wave 6: character, function and condition pictures of cities (design section 7) --------
    # For any region, so none names a region's buildings. Each is on a rung of the city ladder.
    # A picture stands for a whole region (design section 1), so the pictures of one site or one
    # district were cut: naval bases, offshore platforms, spaceports, financial districts and
    # government quarters.
    "housing_blocks_2": _draft(
        "character", ["urban"], "urban_european", "modern_urban_planning", 2, "Command Economy and Prefabricated Construction",
        "A planned city district {when}: long identical five-storey prefabricated concrete "
        "apartment blocks in parallel rows, a wide empty avenue with a few small rounded 1950s cars, trams and "
        "a queue at a tram stop, a bare square with one large bronze statue of a worker, tower "
        "cranes raising more blocks, a factory's chimneys behind"),
    "housing_blocks_3": _draft(
        "character", ["urban"], "urban_european", "computer_aided_design", 3, "Command Economy and Prefabricated Construction",
        "A planned city district {when}: ranks of identical sixteen-storey grey concrete panel "
        "tower blocks to the horizon, weathered and stained, a broad avenue with trolleybuses and boxy 1980s cars, heating pipes on trestles crossing a muddy yard, playgrounds between the "
        "blocks, washing on the balconies"),
    "housing_blocks_4": _draft(
        "character", ["urban"], "urban_european", "advanced_structural_engineering", 4, "Command Economy and Prefabricated Construction",
        "A planned city district {when}: endless identical thirty-storey modular apartment "
        "towers in a strict grid, each with the same balconies, a broad avenue of identical "
        "electric buses, an elevated railway, a vast paved square with a single monumental "
        "sculpture, few trees, cameras on tall poles"),
    "boomtown_1": _draft(
        "character", ["urban"], "urban_european", "art_deco_architecture", 1, "the state's people have grown fast for several years",
        "A fast-growing city {when}: steel frames of new buildings rising everywhere behind "
        "wooden scaffolding, derrick cranes, a street half paved and half mud, 1920s trucks of bricks and timber, crowds of newly arrived workers with suitcases, raw new brick blocks beside "
        "tents and shacks, smoke and dust"),
    "boomtown_2": _draft(
        "character", ["urban"], "urban_european", "modern_urban_planning", 2, "the state's people have grown fast for several years",
        "A fast-growing city {when}: a dozen tower cranes over half-built concrete apartment "
        "blocks, a new road being laid by bulldozers and steamrollers, 1950s cement trucks, prefabricated "
        "panels stacked on site, families moving in with furniture on handcarts, fields at the "
        "edge already staked out"),
    "boomtown_3": _draft(
        "character", ["urban"], "urban_european", "computer_aided_design", 3, "the state's people have grown fast for several years",
        "A fast-growing city {when}: a forest of tower cranes over unfinished glass and concrete "
        "towers wrapped in green netting, a new flyover on bare columns, excavators in deep pits, "
        "streams of workers in hard hats, the last old low houses being pulled down, dust haze"),
    "boomtown_4": _draft(
        "character", ["urban"], "urban_european", "advanced_structural_engineering", 4, "the state's people have grown fast for several years",
        "A fast-growing city {when}: slender towers rising under robotic climbing cranes, whole "
        "prefabricated floors lifted into place, a new elevated railway on fresh concrete piers, "
        "driverless construction machines, raw earth and young trees, a row of finished towers "
        "gleaming behind"),
    "declining_1": _draft(
        "character", ["urban"], "urban_european", "art_deco_architecture", 1, "the state's people are falling",
        "A declining industrial city {when}: a silent factory with cold chimneys and broken "
        "windows, a long queue of men in caps and worn coats outside a soup kitchen, shuttered "
        "fronts, an empty tram, weeds between the cobbles, a few thin children, a grey sky"),
    "declining_2": _draft(
        "character", ["urban"], "urban_european", "modern_urban_planning", 2, "the state's people are falling",
        "A declining industrial city {when}: closed mills with boarded windows along a canal, "
        "rows of emptied brick houses, some half demolished, a rusting gasholder, a few old rounded 1950s cars, "
        "an empty bus, a lone figure on the pavement, washing in one yard, a grey sky"),
    "declining_3": _draft(
        "character", ["urban"], "urban_european", "computer_aided_design", 3, "the state's people are falling",
        "A declining industrial city {when}: a vast abandoned steelworks rusting behind a chain-"
        "link fence, empty lots where houses stood, boarded-up brick buildings, a cracked road "
        "with one old boxy 1980s car, leaning utility poles, saplings growing from a roof, a grey sky"),
    "declining_4": _draft(
        "character", ["urban"], "urban_european", "advanced_structural_engineering", 4, "the state's people are falling",
        "A shrinking city {when}: empty glass office towers with dark windows and missing panels, "
        "a deserted street of blank shuttered fronts, grass growing through a wide "
        "road, a single driverless bus, an abandoned elevated railway, young woodland taking a "
        "whole district back"),
    "divided_2": _draft(
        "character", ["urban"], "urban_latin_american", "modern_urban_planning", 2, "a large city with high inequality",
        "A divided city {when}: white modern apartment blocks and villas with gardens and "
        "swimming pools behind high walls on a hill, and below them a dense hillside of shacks "
        "of scrap wood and tin, mud lanes, washing lines, children, a few big finned 1950s cars on the "
        "boulevard between"),
    "divided_3": _draft(
        "character", ["urban"], "urban_latin_american", "computer_aided_design", 3, "a large city with high inequality",
        "A divided city {when}: gleaming glass towers and a walled compound of luxury flats with "
        "a tennis court, pressed against a sea of bare brick and corrugated-iron shanties "
        "crowding up to the wall, tangled wires, water tanks on roofs, a helicopter above the "
        "towers"),
    "divided_4": _draft(
        "character", ["urban"], "urban_latin_american", "advanced_structural_engineering", 4, "a large city with high inequality",
        "A divided city {when}: slender luxury towers with sky gardens and private landing pads "
        "behind a high security wall, and outside it dense self-built brick housing stacked five "
        "storeys high over narrow lanes, solar panels and water tanks on every roof, drones over "
        "the wall"),
    "smog_1": _draft(
        "character", ["urban"], "urban_european", "art_deco_architecture", 1, "heavy pollution",
        "A city under coal smoke {when}: a street of soot-blackened brick buildings dim at "
        "midday, a thousand chimneys pouring smoke into a yellow-brown fog, a tram with its lamps "
        "lit, hunched pedestrians with scarves over their mouths, gas lamps glowing, factory "
        "stacks fading into the murk"),
    "smog_2": _draft(
        "character", ["urban"], "urban_european", "modern_urban_planning", 2, "heavy pollution",
        "A city under smog {when}: a wide avenue of rounded 1950s cars and buses with headlamps lit in a brown haze "
        "at midday, concrete blocks fading to silhouettes within a few streets, a power station's "
        "stacks pouring smoke, soot-streaked walls, pedestrians holding handkerchiefs to their "
        "faces, a dull orange sun"),
    "smog_3": _draft(
        "character", ["urban"], "urban_european", "computer_aided_design", 3, "heavy pollution",
        "A city under smog {when}: glass towers reduced to grey ghosts in thick yellow haze, a "
        "jammed multi-lane expressway of boxy 1980s cars and trucks trailing exhaust, pedestrians and "
        "cyclists in white face masks, a dull red sun, chimneys and cooling towers faint at the "
        "edge of sight"),
    "smog_4": _draft(
        "character", ["urban"], "urban_european", "advanced_structural_engineering", 4, "heavy pollution",
        "A city under smog {when}: supertall towers vanishing into a brown haze a few floors up, "
        "electric traffic crawling below, every pedestrian in a filter mask, tall air-cleaning "
        "towers in a square, the windows of the blocks sealed, a dull red sun"),
    "industry_1": _draft(
        "function", ["urban"], "urban_european", "art_deco_architecture", 1, "most building levels are heavy industry",
        "A heavy-industry city {when}: blast furnaces and a great steelworks glowing orange "
        "beside rows of workers' brick houses, dozens of smoking chimneys, gasholders, cranes "
        "over a canal of coal barges, a goods train crossing an iron bridge, a red-lit smoky sky"),
    "industry_2": _draft(
        "function", ["urban"], "urban_european", "modern_urban_planning", 2, "most building levels are heavy industry",
        "A heavy-industry city {when}: a vast integrated steelworks and chemical plant of "
        "towers, pipes and spherical tanks along a river, cooling towers steaming, long concrete "
        "factory halls with saw-tooth roofs, workers streaming out at a gate on bicycles, blocks "
        "of flats behind"),
    "industry_3": _draft(
        "function", ["urban"], "urban_european", "computer_aided_design", 3, "most building levels are heavy industry",
        "A heavy-industry city {when}: an enormous refinery and petrochemical complex of silver "
        "columns, flare stacks and pipe racks beside a car plant's long white halls, a yard of thousands of new boxy 1980s cars, freight trains, a motorway of trucks, tower blocks in the haze"),
    "resort_1": _draft(
        "function", ["urban"], "urban_european", "art_deco_architecture", 1, "tourism dominates",
        "A seaside resort {when}: a curving promenade with white art deco hotels and a domed "
        "pavilion on an iron pier, striped bathing tents and deck chairs on the beach, holiday "
        "crowds in summer whites, open 1920s motor cars, palm trees in tubs, sailing boats on a bright "
        "sea"),
    "resort_2": _draft(
        "function", ["urban"], "urban_european", "modern_urban_planning", 2, "tourism dominates",
        "A beach resort {when}: a row of white concrete hotel slabs of twelve storeys with "
        "balconies along a sandy bay, plain striped parasols in ranks, swimming pools, a coast "
        "road of small rounded 1950s cars and coaches, a jet airliner low overhead, palm trees, a bright sea"),
    "resort_4": _draft(
        "function", ["urban"], "urban_european", "advanced_structural_engineering", 4, "tourism dominates",
        "A beach resort {when}: terraced hotel towers stepped like hillsides and covered in "
        "gardens, lagoon pools, an artificial island with villas, sleek electric ferries and a "
        "white cruise ship, crowds on a palm-lined boardwalk, a bright sea"),
    "devastated_early": _draft(
        "condition", ["urban"], "urban_european", "art_deco_architecture", 1, "heavy devastation, on the first two rungs",
        "A city ruined by war {when}: roofless brick and stone buildings with empty window "
        "holes, streets choked with rubble, a burnt-out tram on twisted rails, craters, smoke "
        "rising from several fires, a few people pulling a handcart of belongings, a broken "
        "bridge"),
    "devastated_late": _draft(
        "condition", ["urban"], "urban_european", "computer_aided_design", 3, "heavy devastation, from the third rung",
        "A city ruined by war {when}: concrete tower blocks with whole faces sheared away and "
        "floors hanging, a collapsed flyover, burnt-out boxy 1980s cars and buses, shattered glass towers, "
        "smoke columns, craters in a wide road, a few people picking through the rubble"),
    "nuclear_strike_early": _draft(
        "condition", ["urban"], "urban_european", "modern_urban_planning", 2, "a nuclear strike on the state, on the first three rungs",
        "A city after an atomic bomb {when}: a flat grey plain of ash and rubble to the horizon, "
        "a few twisted steel frames and scorched concrete shells standing, charred tree trunks, "
        "a melted tram, drifting smoke under a dark yellow sky, no living thing in sight"),
    "nuclear_strike_late": _draft(
        "condition", ["urban"], "urban_european", "advanced_structural_engineering", 4, "a nuclear strike on the state, from the fourth rung",
        "A city after a nuclear strike {when}: the stumps of supertall towers snapped off and "
        "blackened, a field of fused glass and rubble to the horizon, a collapsed elevated "
        "railway, drifting ash under a dark yellow sky, no living thing in sight"),
    "flooded_coast_4": _draft(
        "condition", ["urban"], "urban_european", "advanced_structural_engineering", 4, "the warming system's sea-level stage, in a coastal state",
        "A coastal city flooded by the risen sea {when}: streets turned to canals of brown water "
        "between office blocks, small boats and rafts, sandbag walls, a half-drowned bus, people "
        "on rooftops and footbridges of planks, a new concrete sea wall being built by cranes"),
    "flooded_coast_5": _draft(
        "condition", ["urban"], "urban_european", "vactrains", 5, "the warming system's sea-level stage, in a coastal state",
        "A far-future coastal city drowned by the risen sea {when}: the lower floors of old towers standing "
        "abandoned in open water, green with weed, and behind a great curved sea wall a new city of kilometre-high garden towers on raised ground, flying craft between them, boats crossing between, sea birds"),

    # ---- Wave 7: natural terrain in the motor age (optional) ------------------------------------
    "mountains_road": _draft(
        "nature", ["mountain"], "mountains", "modern_urban_planning", 1, "vanilla's generic mountains",
        "High mountains {when}: a motorway carried on tall concrete viaducts along a valley side "
        "and into a tunnel mouth, small rounded 1950s cars and trucks, a cable car climbing to a station on a "
        "ridge, a line of pylons over a pass, dark pine forest, snowy peaks"),
    "mountains_northamerica_road": _draft(
        "nature", ["mountain"], "mountains_northamerica", "modern_urban_planning", 1, "the Americas",
        "Rocky mountains {when}: a two-lane highway winding beside a rushing river, a very long "
        "freight train on the far bank, a steel truss bridge, big 1950s trucks and finned cars, pylons striding up a "
        "valley, pine forest, bare grey peaks with snow"),
    "mountains_arid_road": _draft(
        "nature", ["mountain"], "mountains_arid", "modern_urban_planning", 1, "an arid region",
        "Bare arid mountains {when}: a paved road climbing in switchbacks across a dry rocky "
        "slope, a convoy of 1950s trucks, a line of pylons crossing a ridge, a small roadside "
        "settlement of flat roofs by a green patch of trees, sharp brown peaks in the haze"),
    "hills_road": _draft(
        "nature", ["hills"], "hills", "modern_urban_planning", 1, "vanilla's generic hills",
        "Rolling green hills {when}: a new motorway curving through a deep cutting and over a "
        "long bridge, small rounded 1950s cars and trucks, a line of pylons, a tall lattice radio mast on the "
        "highest summit, hedged pastures with sheep, a village in a fold of the land"),
    "hills_jungle_road": _draft(
        "nature", ["hills"], "hills_jungle", "modern_urban_planning", 1, "jungle hills",
        "Jungle-covered hills {when}: a paved road cut into a steep green hillside, a concrete "
        "bridge over a river gorge, loaded 1950s trucks and a bus, a landslide scar of red earth, a "
        "line of pylons, low cloud caught in the trees"),
    "hills_subtropic_road": _draft(
        "nature", ["hills"], "hills_subtropic", "modern_urban_planning", 1, "Latin America",
        "Green subtropical hills {when}: a winding paved highway with brightly painted 1950s buses and trucks, terraced coffee bushes on the slopes, a small white town with red tile roofs on "
        "a ridge, a line of pylons, banana plants, mist in the valleys"),
    "plains_road": _draft(
        "nature", ["plains"], "plains", "modern_urban_planning", 1, "vanilla's generic plains",
        "A wide green plain {when}: a new motorway running straight to the horizon with a "
        "cloverleaf junction, small rounded 1950s cars and trucks, an electric railway alongside, rows of "
        "pylons, large fields, a river with poplars, a distant town with a water tower"),
    "plains_northamerica_road": _draft(
        "nature", ["plains"], "plains_northamerica", "modern_urban_planning", 1, "the Americas",
        "Open prairie {when}: an arrow-straight four-lane highway to the horizon, big 1950s trucks and finned cars, a "
        "freight train a mile long on a parallel track, a tall white grain elevator beside the "
        "rails, a row of pylons, wind in the grass, an enormous sky"),
    "plains_arid_road": _draft(
        "nature", ["plains"], "plains_arid", "modern_urban_planning", 1, "an arid region",
        "A dry plain of thorn scrub {when}: a straight tarred road with a convoy of 1950s trucks "
        "trailing dust, a line of pylons, a railway with a diesel train, a roadside settlement "
        "of tin roofs under a few trees, flat-topped hills on the horizon"),
    "desert_road": _draft(
        "nature", ["desert"], "desert", "modern_urban_planning", 1, "outside the Americas",
        "A sand desert {when}: a black asphalt highway running between dunes, a convoy of 1950s trucks, a steel pipeline beside the road, a line of pylons, a small pumping station "
        "with silver tanks, a few camels, heat haze"),
    "desert_northamerica_road": _draft(
        "nature", ["desert"], "desert_northamerica", "modern_urban_planning", 1, "the Americas",
        "A red rock desert {when}: a two-lane highway running straight across sagebrush flats "
        "toward red sandstone cliffs, a few long finned 1950s cars and a big truck, a line of wooden utility "
        "poles, a lone wind pump and water tank beside a cattle grid, tall cactus, heat haze"),
    "tundra_pipeline": _draft(
        "nature", ["tundra"], "tundra", "integrated_circuits", 1, "",
        "Open tundra {when}: a silver pipeline on steel stilts zigzagging to the horizon, a "
        "gravel service road with a 1950s truck, a small pumping station of metal sheds, a herd of "
        "reindeer crossing under the pipe, patches of snow, low bare hills"),
    "forest_road": _draft(
        "nature", ["forest"], "forest", "modern_urban_planning", 1, "",
        "A great conifer forest {when}: a two-lane asphalt road running through tall dark "
        "trees, a 1950s log truck, a line of pylons in a cleared strip, a wooden fire-watch tower on "
        "a rise, a lake between the trees, misty ridges"),
    "jungle_road": _draft(
        "nature", ["jungle"], "jungle", "modern_urban_planning", 1, "",
        "Dense rainforest {when}: a long steel and concrete bridge carrying a highway across a "
        "wide brown river, 1950s trucks and a bus, a tall lattice mast above the canopy, a river boat, "
        "a small landing of tin roofs, low cloud over the trees"),
    "wetland_road": _draft(
        "nature", ["wetland"], "wetland", "modern_urban_planning", 1, "",
        "A broad marsh {when}: a road on a low concrete causeway crossing reed beds and open "
        "water, a few rounded 1950s cars and a truck, a line of pylons on concrete footings, a pumping station "
        "on a dike, white egrets, a flat-bottomed boat"),
}


# --- Wave 3: worked land. A draft becomes a picture here once it has a picked render: its
# prompt, technology, rung and terrains come from its draft, its overlay is vanilla's for the
# picture it is like, and this table adds what decides between it and its neighbors.
_HAS_PORT = ["has_building = building_port"]
_OIL_FIELD = ["has_variable = te_sp_oil"]  # the yearly pass's tag: oil is a major part of the state's economy
WAVE3_WIRING = {
    # a harbor is any Port; the major port asks for the level (the pilot's docks_1 is rung 1's)
    **{f"docks_harbor_{n}": {"where": _HAS_PORT} for n in (1, 2, 3, 4)},
    **{f"docks_{n}": {"where": _HAS_PORT, "scale": "major_port"} for n in (2, 3, 4)},
    # the open pit is any mining state; the colliery asks for the coal mines' level
    **{f"mining_{n}": {} for n in (2, 3)},
    **{f"mining_deep_{n}": {"scale": "colliery"} for n in (1, 2, 3)},
    # an oil field takes over the land it stands on
    **{f"oil_{n}": {"where": _OIL_FIELD, "over": True} for n in (1, 2, 3)},
    **{f"farmland_{family}_{n}": {"region": f"farm_{family}"}
       for family in ("generic", "arabic", "asian", "subtropic") for n in (1, 2, 3, 4)},
    "farmland_5": {},
    **{f"plantation_{n}": {} for n in (1, 2, 3, 4)},
    **{f"pasture_{n}": {} for n in (1, 2, 3, 4)},
    **{f"forestry_{n}": {} for n in (1, 2)},
    **{f"forestry_tropical_{n}": {"region": "forest_tropical"} for n in (1, 2)},
    **{f"cleared_land_{n}": {} for n in (1, 2)},
}
# A rung outranks a scale or a region, so the plain and the special picture of a rung are wired
# together: a harbor of rung 2 wired without the major port of rung 2 would show in a great port
# over the major port of rung 1. The test holds each tuple to all or none.
WIRED_TOGETHER = (
    *((f"docks_harbor_{n}", f"docks_{n}") for n in (1, 2, 3, 4)),
    *((f"mining_{n}", f"mining_deep_{n}") for n in (1, 2, 3)),
    *((f"forestry_{n}", f"forestry_tropical_{n}") for n in (1, 2)),
)

# The picked render of each wave 3 picture, with its crop and smudge boxes.
WAVE3_PICKS = {
    "docks_harbor_1": {"seed": 1, "smudge": [(880, 548, 1010, 568)]},
    "docks_harbor_2": {"seed": 0, "smudge": [(1300, 448, 1536, 472), (880, 560, 915, 590)]},
    "docks_harbor_3": {"seed": 0, "smudge": [(440, 462, 500, 488), (298, 388, 326, 412), (1150, 428, 1450, 450),
                                             (1380, 512, 1435, 534), (0, 626, 40, 650)]},
    "docks_harbor_4": {"seed": 1},
    "docks_2": {"seed": 0, "smudge": [(1110, 640, 1165, 672), (355, 398, 410, 418)]},
    "docks_3": {"seed": 3},
    "docks_4": {"seed": 3, "smudge": [(140, 458, 200, 480)]},
    "mining_2": {"seed": 1},
    "mining_3": {"seed": 3},
    "mining_deep_1": {"seed": 1},
    "mining_deep_2": {"seed": 3},
    "mining_deep_3": {"seed": 0, "smudge": [(672, 432, 694, 450)]},
    "oil_1": {"seed": 0},
    "oil_2": {"seed": 0},
    "oil_3": {"seed": 1},
    "farmland_generic_1": {"seed": 3},
    "farmland_generic_2": {"seed": 1, "smudge": [(1455, 718, 1536, 752)]},
    "farmland_generic_3": {"seed": 0, "smudge": [(375, 460, 480, 482)]},
    "farmland_generic_4": {"seed": 0},
    "farmland_arabic_1": {"seed": 0},
    "farmland_arabic_2": {"seed": 0},
    "farmland_arabic_3": {"seed": 1, "smudge": [(495, 526, 520, 546)]},
    "farmland_arabic_4": {"seed": 1},
    "farmland_asian_1": {"seed": 3},
    "farmland_asian_2": {"seed": 0},
    "farmland_asian_3": {"seed": 0},
    "farmland_asian_4": {"seed": 1},
    "farmland_subtropic_1": {"seed": 3},
    "farmland_subtropic_2": {"seed": 1},
    "farmland_subtropic_3": {"seed": 1},
    "farmland_subtropic_4": {"seed": 3, "smudge": [(742, 608, 782, 648)]},
    "farmland_5": {"seed": 1},
    "plantation_1": {"seed": 1},
    "plantation_2": {"seed": 0},
    "plantation_3": {"seed": 0},
    "plantation_4": {"seed": 3},
    "pasture_1": {"seed": 0},
    "pasture_2": {"seed": 1},
    "pasture_3": {"seed": 3},
    "pasture_4": {"seed": 0},
    "forestry_1": {"seed": 0},
    "forestry_2": {"seed": 1},
    "forestry_tropical_1": {"seed": 0, "smudge": [(1200, 448, 1450, 482)]},
    "forestry_tropical_2": {"seed": 0, "smudge": [(700, 486, 800, 504)]},
    "cleared_land_1": {"seed": 0},
    "cleared_land_2": {"seed": 3},
}

for _key, _pick in WAVE3_PICKS.items():
    _draft_entry = DRAFTS.pop(_key)
    _wiring = WAVE3_WIRING[_key]
    PICTURES[_key] = {
        "terrain": _draft_entry["terrain"],
        "tech": _draft_entry["tech"],
        "rung": _draft_entry["rung"],
        "region": _wiring.get("region"),
        "size": None,
        **{k: v for k, v in _wiring.items() if k != "region"},
        "effect": f"vfx_entity_ui_state_{_draft_entry['like']}",
        "prompt": _draft_entry["prompt"],
        **_pick,
    }
if "docks_harbor_1" in PICTURES:
    PICTURES["docks_1"]["scale"] = "major_port"  # the pilot's port is rung 1's major port


def full_prompt(key: str) -> str:
    entry = PICTURES[key] if key in PICTURES else DRAFTS[key]
    return f"{STYLE}. {entry['prompt']}{TAIL}"


def weight(key: str) -> int:
    p = PICTURES[key]
    w = W_RUNG * p["rung"]
    if p["size"]:
        w += W_SIZE * SIZES[p["size"]][1]
    if p.get("scale"):
        w += W_SIZE * SCALES[p["scale"]][1]
    if p["region"]:
        w += W_REGION * region_digit(p["region"])
    if p.get("over"):
        w += W_OVER
    return w


def _negated(line: str) -> str:
    if line.startswith("is_in_geographic_region"):
        return line.replace("is_in_geographic_region", "is_not_in_geographic_region", 1)
    assert line.endswith(" = yes"), line
    return line[:-len("yes")] + "no"


def region_conditions(region: str) -> list:
    """The state triggers of a region family, one a line, nested lines tab-indented."""
    group = region_group(region)
    lines = REGION_GROUPS[group][region][0]
    if region != GROUP_FALLBACK.get(group):
        return list(lines) if len(lines) == 1 else ["OR = {", *("\t" + line for line in lines), "}"]
    # the states of no family, in the form vanilla's own fallback entry uses
    others = [_negated(line) for key, (other, _digit) in REGION_GROUPS[group].items() if key != region
              for line in other]
    if not lines:
        return others
    return ["OR = {", *("\t" + line for line in lines),
            "\tAND = {", *("\t\t" + line for line in others), "\t}", "}"]


def wired() -> dict:
    """The pictures with a picked render: the ones the terrain file lists."""
    return {k: p for k, p in PICTURES.items() if p["seed"] is not None}
