#!/usr/bin/env python3
"""
workshop_composites.py - Steam Workshop images that are not screenshots.

Built from the mod's own files in the style of workshop_screenshots.py (its header band,
palette, fonts and export), for two places on the Workshop page:

  carousel_*  the screenshot carousel, about 2,200 px wide like the annotated screenshots
  desc_*      images embedded in the description with [img]URL[/img]. Steam's workshop.css
              caps a description image at 630 px wide (`.workshopItemDescription img
              { max-width: 630px; }`, read 2026-11-13), so these are drawn 1260 px wide, sharp on
              high-DPI screens, and --preview writes each at 630 to judge them as players will.

The figures on the images (technologies by era, laws, law groups, events, wonders,
megaprojects, state pictures) are counted from the mod files when the images are drawn
(mod_counts), so a re-render is always current. Two are not counted: the monuments standing
in 1836 and the buried sites, which come from the player guide (02-timeline.md, MONUMENTS and
BURIED below). test_workshop_composites.py also checks the published screenshots' figures in
workshop_screenshot_specs.py against mod_counts.

Owner's choices (2026-11-13): one state-picture image on the carousel, "look how things affect
the image", saying where the picture shows (the state panel) and with one base-game picture so
players recognize what the mod's replace. The pictures are AI-generated, and the rule against
spotlighting AI art on the store page has this one exception, for the state pictures.

Usage:
    python3 scripts/image_pipeline/workshop_composites.py [name ...] [--preview]
    python3 scripts/image_pipeline/workshop_composites.py --list
    python3 scripts/image_pipeline/workshop_composites.py --counts

Output goes to build/workshop_composites/ (gitignored). The pictures are the committed
gfx/state_pictures/*.dds, as players see them; a sparse checkout without gfx/ can point
--pictures at a full checkout's folder. The base game's picture and the fonts (EB Garamond)
come from the game install (path_constants.base_game_path), or from --vanilla-pictures and
--fonts. Needs Pillow (the project .venv has it).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

MOD_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import workshop_screenshots as ws  # noqa: E402

DEFAULT_OUT = MOD_ROOT / "build" / "workshop_composites"
ASPECT = 500 / 1020  # a state picture's height over its width
DW = 1260  # a description image's width: twice the 630 px Steam shows
DU = 0.72  # header text scale for a description image
DIM = (196, 182, 156)
PANEL_RGB = (22, 26, 30)

# Not counted from the files: the player guide's figures (02-timeline.md), which the guide keeps
# in step with the Grand Monuments script.
MONUMENTS = 93
BURIED = 50

# Set by main(); the tests replace them.
PICTURES: Path = MOD_ROOT / "gfx" / "state_pictures"
VANILLA_PICTURES: Path | None = None


# ---------------------------------------------------------------- counts from the mod files

TOP_KEY = re.compile(r"^([A-Za-z_][\w.-]*)\s*=\s*\{", re.M)  # keys may hold a hyphen: e-commerce


def _entries(pattern: str, root: Path) -> dict[str, str]:
    """Top-level `key = {` entries of the files matching pattern, as key -> body text.

    Directive entries (INJECT:, REPLACE_OR_CREATE:, ...) are left out: they change an entry
    defined elsewhere, or are counted on their own (megaprojects)."""
    out = {}
    for f in sorted(root.glob(pattern)):
        text = re.sub(r"#[^\n]*", "", f.read_text(encoding="utf-8-sig"))
        found = list(TOP_KEY.finditer(text))
        for i, m in enumerate(found):
            end = found[i + 1].start() if i + 1 < len(found) else len(text)
            out[m.group(1)] = text[m.end():end]
    return out


def _vanilla(kind: str, root: Path) -> set[str]:
    return set(json.loads((root / "vanilla_parsed" / "common" / f"{kind}.json").read_text(encoding="utf-8")))


def _state_pictures(root: Path) -> int:
    """The mod's state pictures, from git's index so a checkout without gfx/ counts them too."""
    try:
        out = subprocess.run(["git", "ls-files", "gfx/state_pictures/te_*.dds"], cwd=root,
                             capture_output=True, text=True, check=True).stdout
        return len(out.split())
    except (OSError, subprocess.CalledProcessError):
        return len(list((root / "gfx" / "state_pictures").glob("te_*.dds")))


def mod_counts(root: Path = MOD_ROOT) -> dict:
    """The figures the Workshop images give, counted from the mod files."""
    techs = {k: b for k, b in _entries("common/technology/technologies/*.txt", root).items()
             if k not in _vanilla("technologies", root)}
    by_era: dict[int, int] = {}
    for body in techs.values():
        m = re.search(r"\bera\s*=\s*era_(\d+)", body)
        if m:
            by_era[int(m.group(1))] = by_era.get(int(m.group(1)), 0) + 1
    vanilla_groups = _vanilla("law_groups", root)
    laws = {k: b for k, b in _entries("common/laws/*.txt", root).items() if k not in _vanilla("laws", root)}
    in_base_groups = sum(1 for b in laws.values()
                         if (m := re.search(r"\bgroup\s*=\s*(\w+)", b)) and m.group(1) in vanilla_groups)
    law_groups = [k for k in _entries("common/law_groups/*.txt", root) if k not in vanilla_groups]
    wonders = sum(1 for b in _entries("common/buildings/08_zz_te_wonders.txt", root).values()
                  if re.search(r"\bbuilding_group\s*=\s*bg_monuments\b", b))
    megaprojects = len(re.findall(r"^REPLACE_OR_CREATE:building_\w+_construction_site\s*=", "\n".join(
        f.read_text(encoding="utf-8-sig") for f in sorted((root / "common" / "buildings").glob("*.txt"))), re.M))
    events = 0
    for f in sorted((root / "events").rglob("*.txt")):
        if "debug" in f.name:
            continue
        for body in _entries(str(f.relative_to(root)), root).values():
            if not re.search(r"^\thidden\s*=\s*yes", body, re.M):
                events += 1
    return dict(techs=len(techs), techs_by_era=dict(sorted(by_era.items())), laws=len(laws),
                laws_in_base_groups=in_base_groups, law_groups=len(law_groups), events=events,
                wonders=wonders, megaprojects=megaprojects, pictures=_state_pictures(root))


# ---------------------------------------------------------------- drawing helpers

F = ws.font
GOLD, GOLD_HI, CREAM, COLUMN = ws.GOLD, ws.GOLD_HI, ws.CREAM, ws.COLUMN


def pic(key: str) -> Image.Image:
    """A state picture by its key; `van:<name>` is the base game's."""
    if key.startswith("van:"):
        return Image.open(VANILLA_PICTURES / f"{key[4:]}.dds").convert("RGB")
    return Image.open(PICTURES / f"te_{key}.dds").convert("RGB")


def paste_framed(base, im, x, y, w):
    """Paste a picture w wide at (x, y), in a thin gold frame like the game's."""
    h = round(w * ASPECT)
    base.paste(im.resize((w, h), Image.LANCZOS), (x, y))
    d = ImageDraw.Draw(base)
    d.rectangle([x - 4, y - 4, x + w + 3, y + h + 3], outline=(0, 0, 0), width=3)
    d.rectangle([x - 2, y - 2, x + w + 1, y + h + 1], outline=GOLD, width=2)
    return h


def wrap(text, fnt, width):
    return ws.wrap(ImageDraw.Draw(Image.new("RGB", (4, 4))), text, fnt, width)


def text_block(d, x, y, lines, fnt, fill, lh, anchor="ma"):
    for line in lines:
        d.text((x, y), line, font=fnt, fill=fill, anchor=anchor)
        y += lh
    return y


def caption_under(d, cx, y, title, body, width, tsize, bsize):
    """A picture's caption, centered under it: a gold title and a cream line."""
    tf, bf = F("SemiBold", tsize), F("Medium", bsize)
    y = text_block(d, cx, y, wrap(title, tf, width), tf, GOLD_HI, tsize * 1.1)
    if body:
        y = text_block(d, cx, y + bsize * 0.15, wrap(body, bf, width), bf, CREAM, bsize * 1.18)
    return y


def body_canvas(w, h):
    return Image.new("RGB", (w, h), COLUMN)


def with_band(spec, body):
    """The body under the annotator's header band."""
    cv = ws.Canvas(spec, body)
    cv.band()
    return cv.finish()


# ---------------------------------------------------------------- the carousel image

# One European city, so the rows read as one place. The size and wealth rows are the 1990s
# city; the technology row takes the 1960s rather than repeat that picture.
TECH_ROW = [
    ("van:urban_european", "1836", "the base game's picture"),
    ("urban_european_1", "1930s", "Art Deco Architecture"),
    ("urban_european_2", "1960s", "Modern Urban Planning"),
    ("urban_european_5", "Far Future", "Vactrains"),
]
SIZE_ROW = [  # te_sp_size's floors: te_state_picture_values.txt
    ("urban_european_3_town", "Town", "largest city under 100,000"),
    ("urban_european_3", "City", "100,000 people or more"),
    ("urban_european_3_metropolis", "Metropolis", "a million or more"),
    ("urban_european_3_megacity", "Megacity", "ten million or more"),
]
WEALTH_ROW = [
    ("urban_european_3_poor", "Poor Street", "living standards under the era's norm"),
    ("urban_european_3_affluent", "Affluent Street", "living standards well above it"),
    ("urban_european_3_rundown", "Run-Down Street", "people expect more than they have"),
]
BECOME_ROW = [
    ("docks_3", "Major Port", "a port of level 20 or more"),
    ("resort_2", "Resort", "a tourism industry of its own"),
    ("smog_2", "City in Smog", "heavy pollution in the region"),
    ("nuclear_strike_early", "After a Nuclear Strike", "struck by a nuclear weapon"),
]


def carousel_state_pictures(counts):
    cols, pw, gx, m = 4, 500, 30, 46
    ph = round(pw * ASPECT)
    head, cap, gy = 66, 112, 26
    rows = [("By the owner's technology", TECH_ROW),
            ("By the size of the largest city", SIZE_ROW),
            ("By how its people live", WEALTH_ROW),
            ("By what the state has become", BECOME_ROW)]
    W = 2 * m + cols * pw + (cols - 1) * gx
    H = m + len(rows) * (head + ph + cap) + (len(rows) - 1) * gy + m - 10
    body = body_canvas(W, H)
    d = ImageDraw.Draw(body)
    hf = F("SemiBold", 40)
    for r, (heading, items) in enumerate(rows):
        y = m + r * (head + ph + cap + gy)
        d.text((m, y + head - 22), heading, font=hf, fill=GOLD, anchor="ls")
        tw = d.textlength(heading, font=hf)
        d.line([(m + tw + 24, y + head - 34), (W - m, y + head - 34)], fill=(110, 86, 52), width=2)
        for i, (key, title, line) in enumerate(items):
            x = m + i * (pw + gx)
            paste_framed(body, pic(key), x, y + head, pw)
            caption_under(d, x + pw / 2, y + head + ph + 16, title, line, pw - 16, 42, 30)
        if len(items) == 3:  # the wealth row's free slot: where the picture shows
            x, yb = m + 3 * (pw + gx), y + head
            d.rounded_rectangle([x, yb - 4, x + pw, yb + ph + cap - 20], radius=12, fill=PANEL_RGB,
                                outline=GOLD, width=3)
            tf, bf = F("SemiBold", 40), F("Medium", 31)
            ty = yb + 24
            d.text((x + pw / 2, ty), "In the state panel", font=tf, fill=GOLD_HI, anchor="ma")
            ty += 60
            for para in [f"{counts['pictures']} new pictures, cities in eight regional styles.",
                         "Each state is read once a year, and its picture follows the result.",
                         "Hover it to see why it shows."]:
                ty = text_block(d, x + pw / 2, ty, wrap(para, bf, pw - 50), bf, CREAM, 38) + 14
    spec = dict(title="State Pictures",
                subtitle="the picture at the top of each state panel changes with the state", u=1.0)
    return with_band(spec, body)


# ---------------------------------------------------------------- description images (1260 px)

AGES = [TECH_ROW[0], TECH_ROW[1], TECH_ROW[2], ("urban_european_3", "1990s", ""),
        ("urban_european_4", "Near Future", ""), TECH_ROW[3]]
HERO = dict(title="Timeline Extended", subtitle="Victoria 3 past 1936, into the modern age and beyond",
            u=0.86, brand=None)


def desc_hero_ages(counts):
    """The title over one city in six ages, from the base game's 1836 picture on."""
    n, h = len(AGES), 420
    sw = DW // n
    body = body_canvas(DW, h)
    for i, (key, _when, _line) in enumerate(AGES):
        im = pic(key)
        im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
        cx = im.width // 2 + (0 if i else -40)  # the base game's building sits left of center
        body.paste(im.crop((cx - sw // 2, 0, cx - sw // 2 + sw, h)), (i * sw, 0))
    fade = Image.new("L", (DW, h), 0)  # a dark fade under the labels
    fd = ImageDraw.Draw(fade)
    for y in range(h - 130, h):
        fd.line([(0, y), (DW, y)], fill=round(225 * (y - (h - 130)) / 130))
    body.paste((14, 12, 14), (0, 0), fade)
    d = ImageDraw.Draw(body)
    for i in range(1, n):
        d.line([(i * sw, 0), (i * sw, h)], fill=(10, 8, 10), width=4)
        d.line([(i * sw + 2, 0), (i * sw + 2, h)], fill=GOLD, width=1)
    lf = F("SemiBold", 36)
    for i, (_key, when, _line) in enumerate(AGES):
        d.text((i * sw + sw / 2, h - 26), when, font=lf, fill=GOLD_HI, anchor="ms")
    d.line([(0, h - 3), (DW, h - 3)], fill=GOLD, width=3)
    return with_band(HERO, body)


WORDS = {n: w for n, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}
ROMAN = {6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII", 13: "XIII"}


def desc_hero_eras(counts):
    """The same title over a ribbon of the new eras: a hero with no picture in it."""
    h, m, gap = 214, 40, 16
    eras = sorted(counts["techs_by_era"])
    n = len(eras)
    bw = (DW - 2 * m - (n - 1) * gap) / n
    body = body_canvas(DW, h)
    d = ImageDraw.Draw(body)
    nf, lf = F("SemiBold", 58), F("Medium", 32)
    centers = []
    for i, era in enumerate(eras):
        x = m + i * (bw + gap)
        d.rounded_rectangle([x, 30, x + bw, 132], radius=10, fill=PANEL_RGB, outline=GOLD, width=2)
        d.text((x + bw / 2, 102), ROMAN[era], font=nf, fill=GOLD_HI, anchor="ms")
        centers.append(x + bw / 2)
        if i < n - 1:
            ax = x + bw + gap / 2
            d.polygon([(ax - 5, 74), (ax + 5, 81), (ax - 5, 88)], fill=GOLD)
    marks = [(0, "1919", "ms"), (eras.index(10), "the present day", "ms"), (n - 1, "a speculative future", "rs")]
    for idx, label, anchor in marks:
        d.line([(centers[idx], 140), (centers[idx], 156)], fill=GOLD, width=2)
        d.text((centers[idx] if anchor == "ms" else DW - m, 190), label, font=lf, fill=CREAM, anchor=anchor)
    return with_band(HERO, body)


def desc_at_a_glance(counts):
    glance = [
        (f"{counts['techs']}", "technologies", f"in {WORDS.get(len(counts['techs_by_era']), len(counts['techs_by_era']))} new eras"),
        (f"{counts['laws']}", "laws", f"and {counts['law_groups']} new law groups"),
        (f"{counts['events'] // 100 * 100:,}+", "events", "across the new systems"),
        (f"{len(SYSTEMS)}", "new systems", "from banking to the space race"),
        (f"{counts['wonders']}", "wonders", f"and {counts['megaprojects']} megaprojects"),
        (f"{MONUMENTS}", "monuments", f"standing in 1836, and {BURIED} buried sites"),
    ]
    cols, m, g, th = 3, 34, 22, 272
    tw = (DW - 2 * m - (cols - 1) * g) / cols
    rows = (len(glance) + cols - 1) // cols
    body = body_canvas(DW, 2 * m + rows * th + (rows - 1) * g)
    d = ImageDraw.Draw(body)
    bf, lf, sf = F("SemiBold", 92), F("SemiBold", 40), F("Medium", 29)
    for i, (big, label, line) in enumerate(glance):
        r, c = divmod(i, cols)
        x, y = m + c * (tw + g), m + r * (th + g)
        d.rounded_rectangle([x + 4, y + 5, x + tw + 4, y + th + 5], radius=14, fill=(8, 9, 11))
        d.rounded_rectangle([x, y, x + tw, y + th], radius=14, fill=PANEL_RGB, outline=GOLD, width=3)
        d.rounded_rectangle([x + 8, y + 8, x + tw - 8, y + th - 8], radius=9, outline=(120, 98, 62), width=1)
        d.text((x + tw / 2, y + 108), big, font=bf, fill=GOLD_HI, anchor="ms")
        d.text((x + tw / 2, y + 156), label, font=lf, fill=CREAM, anchor="ms")
        text_block(d, x + tw / 2, y + 176, wrap(line, sf, tw - 44), sf, DIM, 34)
    return with_band(dict(title="At a Glance", u=DU, brand=None), body)


# The player guide's era table (02-timeline.md): period and theme; the counts come from the files.
ERAS = {
    6: ("1919–1945", "Synthetics, appliances, aviation, radar, rockets and the atomic bomb"),
    7: ("1946–1967", "Transistors, nuclear power, jets, the Green Revolution, missiles and satellites"),
    8: ("1968–1987", "Computer networks, robotics, containerization, pharmaceuticals, stealth"),
    9: ("1988–2012", "The internet, renewable energy, biotechnology, globalization, drones"),
    10: ("The present day", "Machine learning, electric vehicles, reusable rockets, hypersonic weapons"),
    11: ("The near future", "AI agents, fusion power, deep-sea and asteroid mining, genetic engineering"),
    12: ("The medium-term future", "General AI, nanofabrication, orbital industry, space colonization"),
    13: ("The speculative future", "Molecular assemblers, antimatter, the space elevator, mind uploading"),
}


def desc_eras(counts):
    by_era = counts["techs_by_era"]
    m, rh, g = 30, 104, 10
    body = body_canvas(DW, 2 * m + len(by_era) * rh + (len(by_era) - 1) * g)
    d = ImageDraw.Draw(body)
    nf, pf, cf, tf = F("SemiBold", 56), F("SemiBold", 34), F("Medium", 26), F("Medium", 30)
    for i, (era, n) in enumerate(by_era.items()):
        period, theme = ERAS[era]
        y = m + i * (rh + g)
        d.rounded_rectangle([m, y, DW - m, y + rh], radius=10, fill=PANEL_RGB,
                            outline=GOLD if era < 10 else (150, 120, 190), width=2)
        d.text((m + 80, y + rh / 2 + 20), ROMAN[era], font=nf, fill=GOLD_HI, anchor="ms")
        d.line([(m + 160, y + 16), (m + 160, y + rh - 16)], fill=(110, 86, 52), width=2)
        d.text((m + 186, y + 44), period, font=pf, fill=CREAM, anchor="ls")
        d.text((m + 186, y + 82), f"{n} technologies", font=cf, fill=DIM, anchor="ls")
        lines = wrap(theme, tf, DW - 2 * m - 590 - 40)
        ty = y + rh / 2 - (len(lines) - 1) * 18 + 10
        for line in lines:
            d.text((m + 590, ty), line, font=tf, fill=CREAM, anchor="ls")
            ty += 36
    spec = dict(title=f"{str(WORDS.get(len(by_era), len(by_era))).capitalize()} New Eras",
                subtitle=f"{counts['techs']} technologies, from the interwar years to a speculative future",
                u=DU, brand=None)
    return with_band(spec, body)


# The Workshop description's own words for each system (docs/audits/steam_workshop_description.md),
# cut to fit a card.
SYSTEMS = [
    ("Banking and Monetary Policy", "Booms, bubbles, crashes and contagion. Set interest rates, manage inflation and gold, peg or unite currencies."),
    ("Space Race", "From suborbital flight to solar-system colonies. Launch in real orbital windows; send colony fleets and warships."),
    ("Global Warming", "Track temperatures and emitters. Tax carbon, build renewables and carbon capture, and bind rivals by treaty."),
    ("Demographics", "A census by age and sex in every state sets births, deaths and the workforce. Set the pension age and family policy."),
    ("United Nations", "Resolutions, Security Council vetoes, agencies, sanctions, peacekeeping and a court. Its authority sets their weight."),
    ("Global Commons", "License deep-sea mines in five ocean basins; protect, lease or blockade claims; negotiate the Law of the Sea."),
    ("Nuclear Weapons", "Build a deterrent, set doctrine and readiness, and face proliferation crises under a shifting nuclear taboo."),
    ("Decolonization", "Investment, garrisons and assimilation set colonial stability. Hand over by agreement, or fight for independence."),
    ("Covert Warfare", "Intelligence networks, election interference, financial subversion, sabotage and cyber operations."),
    ("Cultural Hegemony", "Compete for cultural influence through prestige, art, technology and monuments; attract migrants and tourists."),
    ("Modern Military", "Combined-arms bonuses for mixed units, with aviation, missiles, drones and modern ships."),
    ("Social Movements", "Civil rights, feminism, LGBTQ+ rights, environmentalism, digital rights and more, each with its event chains."),
    ("Free Market Construction", "Construction is a traded good that governments and investors buy. Based on TOGFan's mod."),
    ("Power Grids", "Transfer stations share electricity between states; interconnectors join grids across seas and borders."),
    ("Courts and Judiciary", "Six court laws. Independent courts can strike down laws you force through: comply, defy or pack them."),
    ("Grand Monuments and Archaeology", f"Raise monuments to your regime or faith. {MONUMENTS} landmarks stand in 1836, to keep or carry off; {BURIED} buried sites wait to be dug."),
    ("Legislated Tax Code", "Experimental. Pass tax bills, win votes with concessions and offer relief, while AI governments legislate their own."),
    ("Healthcare and Biotechnology", "Pops demand healthcare, met by pharmaceuticals, biotech companies and new laws."),
    ("Internal Resettlement", "Settle sparse regions through Settlement Authorities, by voluntary or coercive programs, or retreat from damage."),
]
SYSTEM_IMAGES = [(0, 6), (6, 12), (12, len(SYSTEMS))]  # the first carries the heading


def system_cards(items, title):
    """Cards two to a row; an odd last card spans the row. No title: a continuation, no band."""
    cols, m, g = 2, 30, 20
    cw = (DW - 2 * m - g) / cols
    bf = F("Medium", 30)
    laid, y = [], m
    for i in range(0, len(items), cols):
        row = items[i:i + cols]
        w = cw if len(row) == cols else DW - 2 * m
        cards = [(name, wrap(line, bf, w - 56)) for name, line in row]
        rh = max(30 + 48 + 10 + len(lines) * 38 + 26 for _, lines in cards)
        laid.append((cards, w, y, rh))
        y += rh + g
    body = body_canvas(DW, y - g + m)
    d = ImageDraw.Draw(body)
    for cards, w, y, rh in laid:
        for c, (name, lines) in enumerate(cards):
            x = m + c * (cw + g)
            d.rounded_rectangle([x, y, x + w, y + rh], radius=12, fill=PANEL_RGB, outline=GOLD, width=2)
            size = 40  # shrink a long name to fit its card
            while d.textlength(name, font=F("SemiBold", size)) > w - 56 and size > 30:
                size -= 1
            d.text((x + 28, y + 30 + (40 - size) * 0.6), name, font=F("SemiBold", size), fill=GOLD_HI, anchor="la")
            text_block(d, x + 28, y + 30 + 48 + 10, lines, bf, CREAM, 38, anchor="la")
    return with_band(dict(title=title, u=DU, brand=None), body) if title else body


def desc_systems(counts):
    return [system_cards(SYSTEMS[a:b], "New Systems" if i == 0 else None)
            for i, (a, b) in enumerate(SYSTEM_IMAGES)]


def desc_section(counts, title="Technology, Laws and Society"):
    """A section heading as an image. It costs characters rather than saving them."""
    cv = ws.Canvas(dict(title=title, u=DU, brand=None), body_canvas(DW, 1))
    cv.band()
    return cv.finish().crop((0, 0, DW, cv.band_h))


# name -> (builder, is a description image); a builder returns an image or a list of them
BUILDERS = {
    "carousel_state_pictures": (carousel_state_pictures, False),
    "desc_hero_ages": (desc_hero_ages, True),
    "desc_hero_eras": (desc_hero_eras, True),
    "desc_at_a_glance": (desc_at_a_glance, True),
    "desc_eras": (desc_eras, True),
    "desc_systems": (desc_systems, True),
    "desc_section": (desc_section, True),
}


def render(name, counts):
    """The images of one builder as (file stem, image) pairs."""
    builder, _desc = BUILDERS[name]
    out = builder(counts)
    if isinstance(out, list):
        return [(f"{name}_{i}", im) for i, im in enumerate(out, 1)]
    return [(name, out)]


def main(argv=None) -> int:
    global PICTURES, VANILLA_PICTURES
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help="images to draw (default: all)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help=f"output folder (default: {DEFAULT_OUT.relative_to(MOD_ROOT)})")
    ap.add_argument("--pictures", type=Path, default=PICTURES, help="the mod's gfx/state_pictures folder")
    ap.add_argument("--vanilla-pictures", type=Path, help="the base game's gfx/state_pictures (default: the install's)")
    ap.add_argument("--fonts", type=Path, help="folder with EBGaramond-*.ttf (default: the game install's)")
    ap.add_argument("--preview", action="store_true",
                    help="also write each at the size Steam shows it: 630 px (description) or 640 (carousel)")
    ap.add_argument("--list", action="store_true", help="list the images")
    ap.add_argument("--counts", action="store_true", help="print the figures counted from the mod files")
    args = ap.parse_args(argv)

    if args.list:
        for name, (_b, desc) in BUILDERS.items():
            print(f"{name}: {'description' if desc else 'carousel'}")
        return 0
    counts = mod_counts()
    if args.counts:
        print(json.dumps(dict(counts, monuments=MONUMENTS, buried=BURIED, systems=len(SYSTEMS)), indent=1))
        return 0
    unknown = [n for n in args.names if n not in BUILDERS]
    if unknown:
        ap.error("no such image: " + ", ".join(unknown) + " (see --list)")
    missing = sorted(set(ERAS) ^ set(counts["techs_by_era"]))
    if missing:
        print(f"eras without a row in ERAS, or rows without an era: {missing}", file=sys.stderr)
        return 1
    sys.path.insert(0, str(MOD_ROOT))
    from path_constants import base_game_path  # lazy: --list, --counts and the tests need no game
    ws.FONT_DIR = args.fonts or ws.game_font_dir()
    if not (ws.FONT_DIR / "EBGaramond-SemiBold.ttf").is_file():
        print(f"EB Garamond not found in {ws.FONT_DIR}; pass --fonts", file=sys.stderr)
        return 1
    PICTURES = args.pictures
    VANILLA_PICTURES = args.vanilla_pictures or Path(base_game_path) / "game" / "gfx" / "state_pictures"
    if not (PICTURES / "te_urban_european_1.dds").is_file():
        print(f"no state pictures in {PICTURES}; pass --pictures (a sparse checkout has no gfx/)", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    for name in args.names or list(BUILDERS):
        desc = BUILDERS[name][1]
        for stem, img in render(name, counts):
            path = args.out / f"{stem}.jpg"
            q, size = ws.export(img, path)
            if args.preview:
                w = 630 if desc else 640
                img.resize((w, round(img.height * w / img.width)), Image.LANCZOS).save(
                    args.out / f"{stem}_{w}.jpg", quality=90)
            print(f"{stem}: {img.width}x{img.height}, quality {q}, {size / 1e6:.2f} MB -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
