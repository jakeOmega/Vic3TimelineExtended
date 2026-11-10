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
  region   a key of REGIONS, or None for any region
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
plain awnings. The design's section 10 has the review checks.

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

# Region families: the state triggers vanilla's own city pictures use.
REGIONS = {
    "european": ["is_in_geographic_region = geographic_region_europe"],
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
W_REGION = 1

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


def full_prompt(key: str) -> str:
    return f"{STYLE}. {PICTURES[key]['prompt']}{TAIL}"


def weight(key: str) -> int:
    p = PICTURES[key]
    w = W_RUNG * p["rung"]
    if p["size"]:
        w += W_SIZE * SIZES[p["size"]][1]
    if p["region"]:
        w += W_REGION
    return w


def wired() -> dict:
    """The pictures with a picked render: the ones the terrain file lists."""
    return {k: p for k, p in PICTURES.items() if p["seed"] is not None}
