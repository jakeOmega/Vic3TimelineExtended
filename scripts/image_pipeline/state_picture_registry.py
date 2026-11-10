"""The state pictures: one entry per banner picture, its conditions and its prompt.

The banner at the top of the state panel is the highest-weight entry of the
`textures` list of the state's prevailing terrain (common/terrain). Each entry
here is one picture, `gfx/state_pictures/te_<key>.dds` (1020 x 500), and says
when it applies. `scripts/generators/gen_state_pictures.py` writes
`common/terrain/te_state_pictures_generated.txt` from the entries whose `seed`
is set (a picked, committed picture); an entry with `seed: None` is planned art
and wires nothing. The design, the axes and the full planned set:
docs/superpowers/specs/2026-11-10-state-pictures-design.md.

Fields:
  terrain  the vanilla terrain keys whose list the picture joins
  tech     the owner's technology that unlocks it (a live check in the weight)
  rung     its place on its family's technology ladder, 1-9: among the pictures
           that apply, a higher rung beats everything but a condition
  region   a key of REGIONS, or None for any region; FALLBACK_REGION's pictures also
           show in the states of no family, as vanilla's European city picture does
  size     a key of SIZES, or None for any size (the family's middle picture,
           which stays the fallback for the sizes not painted yet)
  where    optional extra state triggers, one a line
  effect   the animated overlay, required by the engine; a vanilla entity
  seed     the picked render, or None
  crop     optional (left, top, right, bottom) on the 1536 x 752 render, to drop a
           signature or a stray object at an edge; close to 2.04 : 1
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
        "seed": 1,
        "crop": (43, 0, 1493, 711),
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

# {(region, rung): the street, without its date and landmark}. "{when}" is the rung's date.
CITY_STREETS = {
    ("european", 2): (
        "A European city avenue {when}: plain concrete and glass slab office blocks of eight to "
        "twelve storeys rising beside older five-storey stone apartment buildings, a wide asphalt "
        "road full of small rounded cars, a single-deck bus and a streamlined tram under overhead "
        "wires, pedestrians in raincoats, tall modern lamp posts"
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
        "A European city {when}: enormous terraced arcology buildings covered in hanging gardens "
        "rising behind preserved old stone apartment buildings, a transparent vacuum-train tube "
        "on slender white pylons curving above a car-free street of trees and strolling people, "
        "small rounded pod vehicles"
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
        "A North American city {when}: vast stepped arcology towers with forested setbacks rising "
        "over a grid of old brick blocks kept as a historic district, a transparent vacuum-train "
        "tube on tall pylons following the line of a former freeway, a car-free street of trees, "
        "walkers and small pod vehicles"
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
        "A Latin American city {when}: huge terraced arcology buildings overgrown with tropical "
        "gardens rising behind preserved colonial houses with red tile roofs, a transparent "
        "vacuum-train tube on white pylons crossing the valley, a car-free street of palms, "
        "walkers and small pod vehicles, green hills behind"
    ),
    ("african", 1): (
        "A city street in colonial-era Africa {when}: whitewashed two-storey arcaded buildings "
        "with verandas and corrugated iron roofs, a busy open-air market under plain cloth "
        "awnings, bicycles, a few 1930s lorries and motor cars, people in flowing robes and in "
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
        "An African city {when}: great terraced arcology buildings of pale concrete and glass "
        "patterned like woven cloth and hung with gardens, a transparent vacuum-train tube on "
        "slender pylons above a car-free market street of acacia trees, bright stalls, walkers "
        "and small pod vehicles"
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
        "A South Asian city {when}: immense terraced arcology buildings with carved stone "
        "screens and hanging gardens rising above an old bazaar quarter, a transparent vacuum-"
        "train tube on tall pylons, a car-free street of banyan trees, bright stalls, a dense "
        "crowd and small pod vehicles"
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
        "A Middle Eastern city {when}: vast sand-colored terraced arcology buildings with shaded "
        "courtyards, wind towers and hanging gardens, a transparent vacuum-train tube on slender "
        "pylons crossing above a car-free street of date palms, water channels, walkers and "
        "small pod vehicles"
    ),
    ("east_asian", 1): (
        "An East Asian city street {when}: two- and three-storey arcaded row houses with grey "
        "tiled roofs and plain cloth awnings, a few stone-fronted Western-style bank buildings, "
        "hand-pulled rickshaws, bicycles, an electric tram and a few 1930s motor cars, people in "
        "long gowns and in Western suits"
    ),
    ("east_asian", 2): (
        "An East Asian city avenue {when}: plain brick and concrete blocks of four to six storeys "
        "along a wide avenue with rows of plane trees, a great many bicycles, a few lorries and "
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
        "An East Asian city {when}: colossal terraced arcology towers with sweeping tiled eaves "
        "and hanging gardens rising in ranks into the haze, a transparent vacuum-train tube on "
        "tall pylons, a car-free street of ginkgo trees, walkers and small pod vehicles"
    ),
    ("japanese", 1): (
        "A Japanese city street {when}: two-storey wooden town houses with grey tiled roofs and "
        "plain indigo door curtains, a few modern brick and concrete buildings of five storeys, "
        "an electric tram, bicycles, a rickshaw and a few 1930s motor cars, people in kimono and "
        "in Western suits and hats, wooden utility poles strung with many wires"
    ),
    ("japanese", 2): (
        "A Japanese city street {when}: plain concrete office buildings of six to nine storeys "
        "among the last tiled wooden houses, a street crowded with small three-wheeled trucks, "
        "compact cars, trams and buses, utility poles strung with dense wires, a blunt-nosed "
        "express train on an elevated concrete viaduct in the middle distance"
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
        "A Japanese city {when}: immense timber-latticed arcology towers with tiled eaves and "
        "terraced gardens of pine and maple, a transparent vacuum-train tube on slender pylons, "
        "a car-free street of low tiled houses kept at the towers' feet, walkers and small pod "
        "vehicles"
    ),
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
        "prompt": f"{_street.format(when=_when)}, {CITY_LANDMARK[_region]} hazy at the end of the street",
    }


def full_prompt(key: str) -> str:
    return f"{STYLE}. {PICTURES[key]['prompt']}{TAIL}"


def weight(key: str) -> int:
    p = PICTURES[key]
    w = W_RUNG * p["rung"]
    if p["size"]:
        w += W_SIZE * SIZES[p["size"]][1]
    if p["region"]:
        w += W_REGION * REGIONS[p["region"]][1]
    return w


def region_conditions(region: str) -> list:
    """The state triggers of a region family, one a line, nested lines tab-indented."""
    lines = REGIONS[region][0]
    if region != FALLBACK_REGION:
        return list(lines) if len(lines) == 1 else ["OR = {", *("\t" + line for line in lines), "}"]
    # the states of no family, in the form vanilla's own fallback entry uses
    others = [line.replace("is_in_geographic_region", "is_not_in_geographic_region")
              for key, (other, _digit) in REGIONS.items() if key != region for line in other]
    return ["OR = {", *("\t" + line for line in lines),
            "\tAND = {", *("\t\t" + line for line in others), "\t}", "}"]


def wired() -> dict:
    """The pictures with a picked render: the ones the terrain file lists."""
    return {k: p for k, p in PICTURES.items() if p["seed"] is not None}
