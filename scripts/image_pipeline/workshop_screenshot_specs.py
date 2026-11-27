"""
workshop_screenshot_specs.py - What workshop_screenshots.py draws on each screenshot.

One entry per image, keyed by its output name. Coordinates are pixels of the
original screenshot (before `scale`); y grows downward.

Image keys:
    src            the screenshot's file name in --src
    title          the header's big line: the system's name
    subtitle       its one-line pitch, under the title
    u              text scale (1.0 suits a ~2000 px wide shot; check the 640 px preview)
    scale          resize the screenshot first (the 2941 px laws shot uses 0.68)
    crop           (x0, y0, x1, y1) to crop the screenshot first
    column         width of a caption column added at the right
    margin         blank canvas added at each side, so a narrow panel shot is wide enough
                   for its header without a caption column
    column_region  (x0, y0, x1, y1): stack the captions over an empty part of the shot instead
    gap            space between stacked captions (default 26, times u)
    callouts       list of callouts, below; may be empty (the header alone). Two or more
                   captions are numbered top to bottom when rendered; a lone one has no number
    stats          list of headline cards: at, w, big, lines, big_size, line_size
    brand          the small corner label (default "Timeline Extended"; None hides it)

Callout keys:
    box            (x0, y0, x1, y1): frame this, with its number at a corner
    pt             (x, y): point an arrow here instead of framing anything
    title, body    the caption. The title is required: a frame with no caption says nothing
                   (owner, 2026-11-13: "I don't think the frames without the annotations
                   make sense")
    pad            frame padding (default 6)
    badge_at       the frame corner for the number: tl (default), tr, bl, br
    badge          False hides the frame's number
    at, w          place the caption on the shot at (x, y), w wide, with an arrow
    y              pin a column caption's top
    arrow          draw an arrow from the caption (default: only for `at` captions)
    from, to       arrow ends: l r t b tl tr bl br, on the caption and the target

When a callout earns its place (owner, 2026-11-13: "sometimes the image speaks for
itself and the annotations are more noise than anything"):
    none   for a shot of one thing: a map, an event, a list, a chart, or a small panel
           whose own text explains it
    cut    a caption that repeats the image's header or a tooltip in the shot
    few    on a dense panel, and only on what the system is mainly about. Take the
           header's own terms where its subtitle lists them: 01 (tourism, climate,
           wealth), 05 (a census by age and sex: the census and the pyramid), 07 (hold,
           release or lose: stability and the colony list). Otherwise take the panel's
           top-level parts: 06's two lists, 08's sub-tabs.
Never caption a side panel while a main one goes unmarked. A first cut of 05 skipped the
pyramid as self-evident and captioned Causes of Death and Family Policy, and the owner
asked why those two: "some of this feels arbitrary". "Obvious" is a reason to drop an
image's captions altogether, not to skip its centerpiece and caption around it.
Where the shot has an empty part, stack the captions over it (column_region): an added
column with two captions in it is mostly blank. A narrow panel shot with no captions
takes a margin, not a column. A lone caption has no number, so give it an arrow.
A frame never stands without a caption: 01 was tried with its four frames alone, and
the owner's answer is quoted under the callout keys.

Counts in the text were recounted from the mod files on 2026-11-26: 191 technologies
in eras VI to XIII; 166 laws, 16 of them in base-game groups (the first count, 165,
missed law_post-scarcity, whose key has a hyphen), and 39 new law groups; 1,058
visible events outside the debug files; 93 landmarks seeded in 1836 (gm_seed_landmark,
gm_landmark_effects.txt) and 50 buried sites (gm_arch_seed_site); 90 Map Room maps
(the te_jmap_pick_* scripted GUIs: 29 on 2026-11-06, the classes by count and by share and Nuclear Reach
since); 34 history charts (te_popup's chart_* values). workshop_composites.mod_counts()
counts the technologies, laws, law groups and events, and test_workshop_composites.py
checks the figures here against it; recount the others before reusing one.
"""

IMAGE_KEYS = {"src", "title", "subtitle", "u", "scale", "crop", "column", "margin",
              "column_region", "gap", "callouts", "stats", "brand"}
CALLOUT_KEYS = {"box", "pt", "title", "body", "pad", "badge_at", "badge", "at", "w", "y",
                "arrow", "from", "to"}
STAT_KEYS = {"at", "w", "big", "lines", "big_size", "line_size"}
SIDES = {"l", "r", "t", "b", "tl", "tr", "bl", "br"}


def validate(spec: dict) -> list[str]:
    """Problems with one image's spec; empty when it is well-formed."""
    out = [f"unknown key {k!r}" for k in spec.keys() - IMAGE_KEYS]
    for k in ("src", "title"):
        if not spec.get(k):
            out.append(f"missing {k!r}")
    placed_in_column = False
    for i, co in enumerate(spec.get("callouts", []), 1):
        where = f"callout {i} ({co.get('title', '?')})"
        out += [f"{where}: unknown key {k!r}" for k in co.keys() - CALLOUT_KEYS]
        if ("box" in co) == ("pt" in co):
            out.append(f"{where}: needs exactly one of 'box' or 'pt'")
        if "box" in co:
            x0, y0, x1, y1 = co["box"]
            if not (x0 < x1 and y0 < y1):
                out.append(f"{where}: box {co['box']} is not (x0, y0, x1, y1)")
        if not co.get("title"):
            out.append(f"{where}: missing 'title' (a frame always has a caption)")
        for k in ("from", "to", "badge_at"):
            if k in co and co[k] not in SIDES:
                out.append(f"{where}: {k} {co[k]!r} is not one of {sorted(SIDES)}")
        if "at" not in co:
            placed_in_column = True
    if placed_in_column and not spec.get("column") and "column_region" not in spec:
        out.append("a callout has no 'at' but the image has no 'column' or 'column_region'")
    for st in spec.get("stats", []):
        out += [f"stat: unknown key {k!r}" for k in st.keys() - STAT_KEYS]
    return out


SPECS = {}

# The sources are game_qa's Workshop recipes (scripts/image_pipeline/guide_shots.py, the ws_* shots, taken
# 2026-11-26 on copies of the owner's 1964 and 2050 games at 3840x2160, UI scale 1.5), named as the recipe names
# them. A full-screen window is 2454 pixels wide: `scale` 0.8 brings it to the width the 2026-11-06 set was drawn at.

# The one shot where pointing is the point: a mostly base-game panel with the mod's
# blocks in it. The three captions are the subtitle's three (tourism, wealth, climate).
SPECS['01_state_panel'] = dict(
    src='ws_01_state_panel.png', u=0.95, column=700,
    title='State Panels', subtitle='tourism, climate and wealth in every state',
    callouts=[
        dict(box=(22, 1573, 827, 1866), title='Tourism',
             body='Output and throughput by source, each with a bar toward its cap'),
        dict(box=(36, 1064, 415, 1191), title='Dynastic Wealth',
             body="The state's score, heading for its target, and the property effects it brings"),
        dict(box=(436, 887, 822, 1167), pad=4, title='Local Climate',
             body='Heat, winter, sun, water and malaria; Comfort weighs on migration'),
    ])

# The tooltip in the shot gives the cause; only the stripes need saying. The rule is the
# player guide's (01-introduction.md): at least half as many deaths as the leading cause.
SPECS['02_leading_cause_map'] = dict(
    src='ws_02_leading_cause_map.png', scale=0.85, u=0.8,
    title='Leading Cause of Death', subtitle='one of 90 maps in the Map Room',
    callouts=[
        dict(pt=(300, 1450), at=(560, 1080), w=760,
             title='Stripes: a close second',
             body='At least half as many deaths as the leader',
             **{'from': 'bl'}),
    ])

SPECS['03_map_room'] = dict(
    src='ws_03_map_room.png', scale=0.8, u=1.0,
    title='The Map Room', subtitle='90 world maps, one click each',
    callouts=[])

# Kept at four: the owner called this one "great" (2026-11-06), and each caption gives
# a rule (the veto, what builds a case) that the panel's headings don't.
SPECS['04_united_nations'] = dict(
    src='ws_04_united_nations.png', scale=0.8, u=1.15, column=640,
    title='The United Nations', subtitle='resolutions, vetoes, missions and dues',
    callouts=[
        dict(box=(845, 150, 1610, 630), title='Why authority moves',
             body='Eight pillars set the target that UN Authority drifts toward'),
        dict(box=(95, 875, 690, 1000), title='Security Council',
             body='Five permanent seats, each with a veto over binding resolutions'),
        dict(box=(40, 425, 400, 530), title='The case against you',
             body='Infamy, aggression and defiance build the case for a condemnation or sanctions'),
        dict(box=(845, 1165, 1610, 1775), title='Missions in the field',
             body='Send a contingent to peacekeeping, aid and stabilization missions'),
    ])

# The subtitle's two: the census and the pyramid. The captions lie over the greyed laws
# of Family Policy, the panel's quietest part in 1964.
SPECS['05_demographics'] = dict(
    src='ws_05_demographics.png', scale=0.8, u=1.0, gap=20,
    column_region=(1680, 860, 2420, 1290),
    title='Demographics', subtitle='a census by age and sex in every state',
    callouts=[
        dict(box=(30, 80, 780, 580), title='The census',
             body='Births, deaths, life expectancy, fertility and migration'),
        dict(box=(845, 90, 1610, 1040), title='Population pyramid',
             body='Men and women by age, with an outline twenty years ahead'),
    ])

# The panel's two lists. Monument policy and the opportunities were left out: a judgment.
# The captions lie over the interest groups' approval, at the foot of the first column.
SPECS['06_grand_monuments'] = dict(
    src='ws_06_grand_monuments.png', scale=0.8, u=0.9, gap=14,
    column_region=(30, 1330, 790, 1770),
    title='Grand Monuments', subtitle='93 landmarks stand in 1836, and 50 more lie buried',
    callouts=[
        dict(box=(845, 160, 1610, 610), title='Your monuments',
             body='Raise more to your crown, faith or nation; grandeur grows with age'),
        dict(box=(1670, 160, 2420, 720), title='Carry off trophies',
             body="A rival's treasures add to your grandeur; their homeland wants them back"),
    ])

# The subtitle's terms: stability is what holds or loses them, the list is where you
# release them. Turkey in 1964, the copy's one empire with colonies; cut under Why
# Stability Is Moving, and the captions stacked in the empty space beside it.
SPECS['07_colonial_empire'] = dict(
    src='ws_07_colonial_empire.png', crop=(0, 0, 2454, 1500), scale=0.8, u=0.9, gap=30,
    column_region=(1000, 1040, 2400, 1460),
    title='Colonial Empire', subtitle='hold your colonies, release them, or lose them',
    callouts=[
        dict(box=(30, 80, 770, 500), title='Colonial stability',
             body='Programs prop it up; condemnation by great powers drags it down'),
        dict(box=(30, 600, 770, 790), title='Your colonies',
             body='Living standard and GDP of each, with a Release button'),
    ])

# The Space Race full screen on Solar System Colonization, the 2043 game's running stage: the program's
# flags, the colonies and Space Command. The fleets' own card is left unframed: its picture is art.
SPECS['08_space_race'] = dict(
    src='ws_08_space_race.png', scale=0.8, u=0.9, gap=14,
    column_region=(20, 1120, 770, 1778),
    title='The Space Race', subtitle='from suborbital flight to an interstellar probe',
    callouts=[
        dict(box=(80, 980, 720, 1090), title='Eight milestones',
             body='A flag marks each one your country reached first'),
        dict(box=(850, 90, 1610, 1775), pad=3, title='Colonize the solar system',
             body='Race rivals for 40 sites, from the Moon outward'),
        dict(box=(1676, 380, 2420, 820), title='Space fleets',
             body='Station, blockade and interdict; land marines to seize a colony'),
    ])

SPECS['09_laws'] = dict(
    src='ws_09_laws.png', scale=0.55, u=1.05,
    title='166 New Laws', subtitle='and 39 new law groups',
    callouts=[])

SPECS['10_technology'] = dict(
    src='ws_10_technology.png', scale=0.6, u=1.0,
    title='Eight New Eras', subtitle='from the interwar years to a speculative future',
    callouts=[],
    stats=[dict(at=(30, 40), w=1100, big='191 new technologies', big_size=64, line_size=38,
                lines=['in eras VI to XIII,', 'from Radar and Television',
                       'to Terraforming and Mind Backups'])],
)

SPECS['11_banking'] = dict(
    src='ws_11_banking.png', scale=0.8, u=0.85,
    title='Boom & Bust Cycle', subtitle='34 history charts, each opens full size',
    callouts=[])

SPECS['12_construction_market'] = dict(
    src='ws_12_construction_market.png', crop=(0, 24, 854, 777), u=0.75, margin=300,
    title='Construction Market', subtitle="based on TOGFan's mod",
    callouts=[])

# No callouts, and none on the picture: never highlight art (it is AI-generated).
SPECS['13_nuclear_event'] = dict(
    src='ws_13_event.png', u=1.0,
    title='Over 1,000 New Events', subtitle='nuclear crises, elections, the space race',
    callouts=[])

# Candidates for the carousel (owner, 2026-11-26: "Retake 13 + offer candidates"): windows the 2026-11-06 set
# predates. No callouts on either picture's art.
SPECS['c1_colonies'] = dict(
    src='ws_c1_colonies.png', u=1.0,
    title='Colonize the Solar System', subtitle='terraform Mars, mine the asteroids, defend every site',
    callouts=[])

SPECS['c2_fleets'] = dict(
    src='ws_c2_fleets.png', u=1.0,
    title='Space Fleets', subtitle='warships, carriers and marines between the planets',
    callouts=[])
