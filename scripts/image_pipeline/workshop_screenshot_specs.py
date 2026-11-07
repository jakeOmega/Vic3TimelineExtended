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
    column_region  (x0, y0, x1, y1): stack the captions over an empty part of the shot instead
    gap            space between stacked captions (default 26, times u)
    callouts       list of callouts, below; numbered top to bottom when rendered
    stats          list of headline cards: at, w, big, lines, big_size, line_size
    brand          the small corner label (default "Timeline Extended"; None hides it)

Callout keys:
    box            (x0, y0, x1, y1): frame this, with its number at a corner
    pt             (x, y): point an arrow here instead of framing anything
    title, body    the caption
    pad            frame padding (default 6)
    badge_at       the frame corner for the number: tl (default), tr, bl, br
    badge          False hides the frame's number
    at, w          place the caption on the shot at (x, y), w wide, with an arrow
    y              pin a column caption's top
    arrow          draw an arrow from the caption (default: only for `at` captions)
    from, to       arrow ends: l r t b tl tr bl br, on the caption and the target

Counts in the text were taken from the mod files on 2026-11-06: 191
technologies in eras VI to XIII; 165 laws, 15 of them in base-game groups, and
39 new law groups; about 1,035 visible events outside the debug files; 93
standing monuments and 50 buried sites (player guide 02-timeline.md); 29 Map
Room maps; 34 history charts. Recount before reusing a figure.
"""

IMAGE_KEYS = {"src", "title", "subtitle", "u", "scale", "crop", "column", "column_region",
              "gap", "callouts", "stats", "brand"}
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
    if not spec.get("callouts") and not spec.get("stats"):
        out.append("no callouts and no stats")
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
            out.append(f"{where}: missing 'title'")
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

SPECS['01_state_panel'] = dict(
    src='Screenshot 2026-11-06 140931.png', u=0.95, column=700,
    title='State Panels', subtitle='tourism, climate and wealth in every state',
    callouts=[
        dict(box=(18, 325, 652, 568), title='Tourism',
             body='Output and throughput by source, each with a bar toward its cap'),
        dict(box=(343, 943, 652, 1068), title='Arable Land',
             body='What technology and regional effects add to the land'),
        dict(box=(20, 1083, 330, 1240), title='Dynastic Wealth',
             body="The state's score, heading for its target, and the property effects it brings"),
        dict(box=(343, 1083, 652, 1326), pad=4, title='Local Climate',
             body='Heat, winter, sun, water and malaria; Comfort weighs on migration'),
    ])

SPECS['02_leading_cause_map'] = dict(
    src='Screenshot 2026-11-06 140822.png', u=0.8,
    title='Leading Cause of Death', subtitle='one of 29 maps in the Map Room',
    callouts=[
        dict(box=(450, 612, 996, 772), pad=3, at=(560, 175), w=500,
             title='Colored by cause',
             body='Each state takes the color of what killed most of its people',
             **{'from': 'b', 'to': 't'}),
        dict(pt=(480, 830), at=(630, 776), w=760,
             title='Stripes: a close second',
             body='Another cause with half the deaths or more',
             **{'from': 'l'}),
    ])

SPECS['03_map_room'] = dict(
    src='Screenshot 2026-11-06 134136.png', u=1.0,
    title='The Map Room', subtitle='29 world maps, one click each',
    callouts=[
        dict(box=(50, 316, 602, 762), at=(720, 450), w=560,
             title='29 world maps',
             body='The economy, the climate, the census, and a map for each system',
             **{'from': 'l', 'to': 'r'}),
        dict(box=(1155, 970, 1502, 1083), pad=3, at=(686, 790), w=360,
             title='Hover any state',
             body="for its figure: Hawaii's Base Appeal is +100%",
             **{'from': 'r', 'to': 'tl'}),
    ])

SPECS['04_united_nations'] = dict(
    src='Screenshot 2026-11-06 134035.png', u=1.15, column=640,
    title='The United Nations', subtitle='resolutions, vetoes, missions and dues',
    callouts=[
        dict(box=(660, 138, 1272, 532), title='Why authority moves',
             body='Eight pillars set the target that UN Authority drifts toward'),
        dict(box=(72, 738, 538, 814), title='Security Council',
             body='Five permanent seats, each with a veto over binding resolutions'),
        dict(box=(660, 948, 1272, 1268), title='Missions in the field',
             body='Send a contingent to peacekeeping, aid and stabilization missions'),
        dict(box=(1322, 445, 1932, 852), title='The case against you',
             body='Infamy, aggression and defiance build the case for a condemnation or sanctions'),
    ])

SPECS['05_demographics'] = dict(
    src='Screenshot 2026-11-06 134003.png', u=1.15, column=640,
    title='Demographics', subtitle='a census by age and sex in every state',
    callouts=[
        dict(box=(18, 85, 628, 470), title='The census',
             body='Births, deaths, life expectancy, fertility and migration'),
        dict(box=(678, 132, 1290, 790), title='Population pyramid',
             body='Men and women by age, with an outline twenty years ahead'),
        dict(box=(1338, 132, 1950, 428), title='Causes of death',
             body='Infection, chronic illness, accidents, work, childbirth and war'),
        dict(box=(1338, 455, 1950, 1046), title='Family policy',
             body='The measures your family law allows, each with its cost'),
        dict(box=(18, 690, 628, 1312), title='Wealth and inheritance',
             body='What each law adds to the Dynastic Wealth target'),
    ])

SPECS['06_grand_monuments'] = dict(
    src='Screenshot 2026-11-06 133913.png', u=0.9, gap=14,
    column_region=(716, 424, 1300, 1132),
    title='Grand Monuments', subtitle='93 landmarks stand in 1836, and 50 more lie buried',
    callouts=[
        dict(box=(698, 205, 1308, 402), title='Your monuments',
             body='Raise more to your crown, faith or nation; grandeur grows with age'),
        dict(box=(1358, 240, 1965, 905), arrow=True, title='Carry off trophies',
             body="A rival's treasures add to your grandeur; their homeland wants them back",
             **{'from': 'r', 'to': 'l'}),
        dict(box=(38, 475, 648, 600), arrow=True, title='Monument policy',
             body='Tourism, legitimacy, culture or education', **{'from': 'l', 'to': 'r'}),
        dict(box=(38, 1000, 648, 1138), pad=3, arrow=True, title='Opportunities',
             body='Interest groups ask for monuments of their own', **{'from': 'l', 'to': 'r'}),
    ])

SPECS['07_colonial_empire'] = dict(
    src='Screenshot 2026-11-06 133839.png', u=0.9, gap=30,
    column_region=(18, 180, 410, 960),
    title='Colonial Empire', subtitle='hold your colonies, release them, or lose them',
    callouts=[
        dict(box=(428, 110, 2040, 156), pad=4, title='Every system, one window',
             body='Each system has a tab in the Timeline Extended window'),
        dict(box=(426, 217, 935, 502), title='Colonial stability',
             body='Programs prop it up; condemnation by great powers drags it down'),
        dict(box=(1471, 392, 2071, 732), pad=3, at=(1505, 752), w=575,
             title='Hover for the full cost',
             body="Each program's upkeep and effects, level by level",
             **{'from': 't', 'to': 'b'}),
        dict(box=(426, 522, 935, 868), title='Your colonies',
             body='Living standard and GDP of each, with a Release button'),
    ])

SPECS['08_space_race'] = dict(
    src='Screenshot 2026-11-06 152026.png', u=0.95, gap=18,
    column_region=(1362, 462, 1975, 1432),
    title='The Space Race', subtitle='from suborbital flight to an interstellar probe',
    callouts=[
        dict(box=(85, 240, 612, 326), title='Eight milestones',
             body='A flag marks each one your country reached first'),
        dict(box=(40, 398, 640, 444), title='Standard, Safe or Ambitious',
             body='Trade speed against the risk of a setback'),
        dict(box=(40, 885, 650, 1442), pad=3, title='Colonize the solar system',
             body='Race rivals for 40 sites, from the Moon outward'),
        dict(box=(700, 592, 1310, 818), title='Space fleets',
             body='Station, blockade and interdict; land marines to seize a colony'),
        dict(box=(1360, 285, 1972, 442), title='Orbit',
             body='Debris, satellites and anti-satellite strikes'),
    ])

SPECS['09_laws'] = dict(
    src='Screenshot 2026-11-06 170524.png', scale=0.68, u=1.05, column=720, gap=22,
    title='165 New Laws', subtitle='and 39 new law groups',
    callouts=[
        dict(box=(15, 658, 953, 881), title='New technology',
             body='Internet, frontier AI, genetic rights, automation'),
        dict(box=(15, 890, 953, 1527), title='Ministries',
             body='Science, intelligence, the environment and more'),
        dict(box=(1000, 890, 1936, 997), title='Amendments',
             body="Attach amendments to the mod's laws"),
        dict(box=(1983, 425, 2920, 765), title='Rights and society',
             body='LGBTQ+ rights to human augmentation'),
    ])

SPECS['10_technology'] = dict(
    src='Screenshot 2026-11-06 170438.png', u=1.0,
    title='Eight New Eras', subtitle='from the interwar years to a speculative future',
    callouts=[],
    stats=[dict(at=(24, 960), w=660, big='191 new technologies', big_size=64, line_size=38,
                lines=['in eras VI to XIII,', 'from Radar and Television',
                       'to Terraforming and Mind Backups'])],
)

SPECS['11_banking'] = dict(
    src='Screenshot 2026-11-06 170342.png', u=0.85, gap=14,
    column_region=(240, 410, 900, 800),
    title='Boom & Bust Cycle', subtitle='34 history charts, each opens full size',
    callouts=[
        dict(box=(15, 89, 597, 302), pad=4, arrow=True, title='The cycle at a glance',
             body='Cycle value, momentum, policy stance, bubble', **{'from': 't', 'to': 'b'}),
        dict(box=(985, 390, 1328, 412), pad=6, arrow=True, title='Markers flag policies and crashes',
             body='Hover a bar for what happened that month', **{'from': 'tr', 'to': 'bl'}),
        dict(box=(906, 532, 1680, 801), pad=4, badge_at='tr', title='Every month, colored by phase',
             body='From Panic and Downturn to Boom and Frenzy'),
    ])

SPECS['12_construction_market'] = dict(
    src='Screenshot 2026-11-06 170858.png', u=0.75, column=600,
    title='Construction Market', subtitle="based on TOGFan's mod",
    callouts=[
        dict(box=(85, 322, 572, 360), pad=4, title='Fix the amount or the budget',
             body='Buy a set number of points, or spend a set sum each week'),
        dict(box=(22, 458, 642, 592), pad=3, title='A market for construction',
             body='The state and private investors buy points; demand drives the price'),
    ])

SPECS['13_nuclear_event'] = dict(
    src='Screenshot 2026-11-06 170716.png', u=1.0, column=600,
    title='Over 1,000 New Events', subtitle='nuclear crises, elections, the space race',
    callouts=[
        dict(box=(735, 138, 1322, 298), title='Nuclear crises',
             body='Threats, alerts and stand-downs between armed powers'),
        dict(box=(740, 792, 1314, 954), title='Every choice costs',
             body='Raise the alert, offer a stand-down, or back down'),
    ])
