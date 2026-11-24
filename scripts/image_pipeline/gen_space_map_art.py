#!/usr/bin/env python3
"""Draw the Solar System tab's map: its backdrop and its site markers
(space_race_widget.gui, te_sr_system_map and te_sr_map_pip).

The map (owner, 2026-11-23: "some kind of schematic view of the solar system")
is a diagram, so its art is drawn here rather than rendered, as the fleet
cards' order signs are (gen_space_fleet_pictograms.py):

- `map_backdrop.dds`: the Sun at the left edge and the nine locations' orbits
  round it, the two belts as bands of specks. The orbits pass through the
  centres of the map's nine columns, so `COLUMN_X0`, `COLUMN_W` and `ROW_Y`
  here are the layout gen_solar_sites.py's map blocks and the widget's sizes
  follow (test_space_race_map.py holds the three to each other).
- `map_pip_*.dds`: one site's state at 14 px (ours, another power's when its
  holder isn't known to us, unclaimed, free, occupied, ruined) and
  `map_target.dds`, the ring round our colony fleets' target.

The backdrop is drawn at 4x and downsampled to twice the widget's size in GUI
units (the panels are read at a UI scale of up to 1.5 on a 4K screen); a
marker on a 24-unit grid at 8x, downsampled to 64 px. Both are written as
vanilla's uncompressed DDS (icon_dds.py). Deterministic: a second run writes
the same bytes.

Run standalone (numpy and Pillow, no game):
    .venv/bin/python scripts/image_pipeline/gen_space_map_art.py [--check] [--sheet PNG]
"""

from __future__ import annotations

import argparse
import io
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from PIL import Image, ImageDraw

    import icon_dds
except ImportError:  # the layout below is read without Pillow (test_space_race_map.py; CI has none)
    Image = ImageDraw = icon_dds = None

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("gfx/interface/icons/space_race_icons")

# --- The map's layout, in GUI units (te_sr_system_map) ---------------------
MAP_W, MAP_H = 480, 148
COLUMN_X0 = 28                 # the first column's left edge; the Sun fills what is left of it
COLUMN_W = 50                  # nine columns: 28 + 9 x 50 = 478
COLUMNS = 9
ROW_Y = 21                     # the centre line of the locations' icons
SUN = (4, ROW_Y)               # the Sun's centre, just inside the left edge
BELTS = (3, 8)                 # the asteroid belt and the Kuiper belt: specks, not a line

CREAM = (233, 226, 207)        # the panel's text
GOLD = (240, 196, 60)          # ours, as the overview's Sites pie
RED = (214, 78, 50)            # another power's, as the pie
TEAL = (92, 196, 176)          # free
GREY = (150, 148, 140)
DARK = (22, 24, 30)


def column_centre(i: int) -> float:
    return COLUMN_X0 + COLUMN_W * i + COLUMN_W / 2


def backdrop() -> Image.Image:
    px, ss = 2, 4                                   # 2 px a unit in the file, drawn 4x that
    k = px * ss
    im = Image.new("RGBA", (MAP_W * k, MAP_H * k), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    rng = random.Random(20261123)
    sx, sy = SUN[0] * k, SUN[1] * k

    # A few stars, faint, kept clear of nothing in particular: the icons cover what they cover.
    for _ in range(90):
        x, y = rng.uniform(0, MAP_W) * k, rng.uniform(0, MAP_H) * k
        r = rng.choice((0.25, 0.25, 0.35, 0.5)) * k
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(*CREAM, rng.randrange(28, 70)))

    # The orbits, each through its column's centre on the icons' line.
    for i in range(COLUMNS):
        radius = (column_centre(i) - SUN[0]) * k
        if i in BELTS:
            # Specks spread evenly down the map's height, scattered about the orbit.
            for _ in range(340):
                y = rng.uniform(0, MAP_H) * k
                rr = radius + rng.gauss(0, 2.4) * k
                reach = rr * rr - (y - sy) ** 2
                if reach <= 0:
                    continue
                x = sx + math.sqrt(reach)
                if 0 <= x < im.width:
                    r = rng.choice((0.3, 0.4, 0.55)) * k
                    draw.ellipse((x - r, y - r, x + r, y + r), fill=(*CREAM, rng.randrange(60, 120)))
        else:
            w = max(1, round(0.5 * k))
            draw.ellipse((sx - radius, sy - radius, sx + radius, sy + radius), outline=(*CREAM, 92), width=w)

    # The Sun: a glow, then its disc.
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    for step in range(40, 0, -1):
        r = (6 + step * 0.55) * k
        gdraw.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(255, 190, 70, round(5 + (40 - step) * 1.1)))
    im = Image.alpha_composite(im, glow)
    draw = ImageDraw.Draw(im)
    r = 9 * k
    draw.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(255, 214, 110, 255))
    r = 6.5 * k
    draw.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(255, 236, 170, 255))
    return icon_dds.resize_premultiplied(im, (MAP_W * px, MAP_H * px))


# --- The markers, on a 24-unit grid ------------------------------------------
SIZE, SCALE = 64, 8
UNIT = SIZE * SCALE / 24


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def _disc(draw, r, fill, cx=12.0, cy=12.0):
    draw.ellipse(((cx - r) * UNIT, (cy - r) * UNIT, (cx + r) * UNIT, (cy + r) * UNIT), fill=fill)


def _ring(draw, r, width, color, cx=12.0, cy=12.0):
    draw.ellipse(((cx - r) * UNIT, (cy - r) * UNIT, (cx + r) * UNIT, (cy + r) * UNIT),
                 outline=color, width=max(1, round(width * UNIT)))


def _stroke(draw, a, b, width, color):
    w = max(1, round(width * UNIT))
    pa, pb = (a[0] * UNIT, a[1] * UNIT), (b[0] * UNIT, b[1] * UNIT)
    draw.line((pa, pb), fill=color, width=w)
    for x, y in (pa, pb):
        draw.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=color)


def _solid(color):
    def drawing(draw):
        _disc(draw, 10.6, (*DARK, 215))           # a dark rim, so a marker reads on an orbit or a speck
        _disc(draw, 8.8, (*color, 255))
        _disc(draw, 5.2, (*[min(255, c + 26) for c in color], 255), cx=10.6, cy=10.4)   # a small highlight
    return drawing


def pip_unclaimed(draw):
    _disc(draw, 10.6, (*DARK, 150))
    _ring(draw, 8.8, 2.3, (*CREAM, 215))


def pip_occupied(draw):                            # another's marines hold it: the red marker, barred
    _solid(RED)(draw)
    _stroke(draw, (7.2, 12), (16.8, 12), 3.0, (*CREAM, 255))


def pip_ruined(draw):
    _disc(draw, 10.6, (*DARK, 150))
    _stroke(draw, (6.5, 6.5), (17.5, 17.5), 2.8, (*GREY, 255))
    _stroke(draw, (17.5, 6.5), (6.5, 17.5), 2.8, (*GREY, 255))


def target(draw):                                  # a ring in four arcs round the marker
    box = (1.0 * UNIT, 1.0 * UNIT, 23.0 * UNIT, 23.0 * UNIT)
    w = max(1, round(2.2 * UNIT))
    for start in (20, 110, 200, 290):
        draw.arc(box, start, start + 50, fill=(*GOLD, 255), width=w)


# file stem: drawing
MARKERS = {
    "map_pip_ours": _solid(GOLD), "map_pip_other": _solid(RED), "map_pip_free": _solid(TEAL),
    "map_pip_unclaimed": pip_unclaimed, "map_pip_occupied": pip_occupied, "map_pip_ruined": pip_ruined,
    "map_target": target,
}
STEMS = ("map_backdrop", *MARKERS)


def render(stem: str) -> Image.Image:
    if stem == "map_backdrop":
        return backdrop()
    im, draw = _canvas()
    MARKERS[stem](draw)
    return icon_dds.resize_premultiplied(im, (SIZE, SIZE))


def dds_bytes(stem: str) -> bytes:
    """The file's bytes, in icon_dds.write_dds's layout (it takes a path)."""
    im = render(stem).convert("RGBA")
    sizes = icon_dds.mip_sizes(*im.size)
    out = io.BytesIO()
    out.write(icon_dds.header(im.width, im.height, len(sizes)))
    for size in sizes:
        level = im if size == im.size else icon_dds.resize_premultiplied(im, size)
        out.write(level.tobytes("raw", "BGRA"))
    return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit 1 if a file is missing or stale; write nothing")
    parser.add_argument("--sheet", metavar="PNG", help="also write the set on the panel's dark ground")
    parser.add_argument("--out", metavar="DIR", help="write under DIR instead of the repository (a preview mod folder)")
    args = parser.parse_args()
    root = Path(args.out) if args.out else ROOT
    stale = []
    for stem in STEMS:
        target_path = root / OUT_DIR / f"{stem}.dds"
        data = dds_bytes(stem)
        if not target_path.exists() or target_path.read_bytes() != data:
            stale.append(str(OUT_DIR / f"{stem}.dds"))
            if not args.check:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(data)
    if args.sheet:
        back = render("map_backdrop")
        sheet = Image.new("RGBA", (back.width + 16, back.height + 96), (29, 31, 38, 255))
        sheet.alpha_composite(back, (8, 8))
        for i, stem in enumerate(MARKERS):
            sheet.alpha_composite(render(stem), (8 + i * 72, back.height + 20))
        sheet.save(args.sheet)
    for path in stale:
        print(("stale: " if args.check else "wrote: ") + path)
    if not stale:
        print("space map art: current")
    return int(args.check and bool(stale))


if __name__ == "__main__":
    raise SystemExit(main())
