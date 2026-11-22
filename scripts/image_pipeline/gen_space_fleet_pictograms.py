#!/usr/bin/env python3
"""Draw the Space Fleets cards' order signs and transit marker (space_race_widget.gui,
te_sr_fleet_row).

The fleet cards (owner, 2026-11-14) show a fleet's orders as signs left of
their words, and a ship marker on the track of a fleet in transit. These seven
are flat line pictograms, drawn here rather than rendered: an order reads best
as a sign (an arrow, a flag planted, a burst), and the marker must read at 18 px
on a bar. The cards' other icons (the emblems, the ship roles, the postures) and
Locations' statuses were drawn here too at first, so the layout could be judged
in game (gui_style_guide.md rule 10); they are painted now, through the icon
pipeline (icon_prompts.py, categories `space` and `space_state`) under the same
file names. docs/systems/space_race_gui_icons.md, "Space Fleets: the fleet
cards", lists both sets.

Each icon is drawn on a 24-unit grid at 8x, downsampled to 64 px and written
as vanilla's uncompressed DDS (icon_dds.py). Deterministic: a second run
writes the same bytes.

Run standalone (numpy and Pillow, no game):
    .venv/bin/python scripts/image_pipeline/gen_space_fleet_pictograms.py [--check]
"""

from __future__ import annotations

import argparse
import io
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import icon_dds  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("gfx/interface/icons/space_race_icons")
SIZE = 64
SCALE = 8                      # drawn at 24 x 8 x (64 / 24) = 512 px, then downsampled
UNIT = SIZE * SCALE / 24
CREAM = (233, 226, 207, 255)   # the panel's text
WIDTH = 1.9                    # stroke, in grid units


class Canvas:
    def __init__(self, color=CREAM, width=WIDTH):
        self.im = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.im)
        self.color = color
        self.width = width

    def _px(self, p):
        return (p[0] * UNIT, p[1] * UNIT)

    def line(self, *points, closed=False):
        """A polyline with round joins and caps."""
        pts = [self._px(p) for p in points]
        if closed:
            pts.append(pts[0])
        w = max(1, round(self.width * UNIT))
        self.draw.line(pts, fill=self.color, width=w, joint="curve")
        r = w / 2
        for x, y in pts:
            self.draw.ellipse((x - r, y - r, x + r, y + r), fill=self.color)

    def fill(self, *points):
        self.draw.polygon([self._px(p) for p in points], fill=self.color)

    def dot(self, cx, cy, r):
        x, y = self._px((cx, cy))
        self.draw.ellipse((x - r * UNIT, y - r * UNIT, x + r * UNIT, y + r * UNIT), fill=self.color)

    def image(self) -> Image.Image:
        return icon_dds.resize_premultiplied(self.im, (SIZE, SIZE))


def order_go(c):
    c.line((4, 12), (20, 12))
    c.line((14, 6), (20, 12), (14, 18))


def order_transfer(c):
    c.line((4, 9), (19, 9))
    c.line((15, 5), (19, 9), (15, 13))
    c.line((20, 16), (5, 16))
    c.line((9, 12), (5, 16), (9, 20))


def order_land(c):
    c.line((12, 3), (12, 15))
    c.line((7, 10), (12, 15), (17, 10))
    c.line((5, 20), (19, 20))


def order_embark(c):
    c.line((12, 16), (12, 4))
    c.line((7, 9), (12, 4), (17, 9))
    c.line((5, 20), (19, 20))


def order_seize(c):    # a flag planted
    c.line((6, 21), (6, 4))
    c.line((6, 5), (18, 5), (15, 9), (18, 13), (6, 13))


def order_destroy(c):  # a burst
    for k in range(8):
        a = math.radians(45 * k)
        inner, outer = (4.0, 9.5) if k % 2 == 0 else (4.0, 7.0)
        c.line((12 + inner * math.cos(a), 12 + inner * math.sin(a)),
               (12 + outer * math.cos(a), 12 + outer * math.sin(a)))
    c.dot(12, 12, 1.6)


def track_ship(c):     # the transit track's marker, filled so it reads at 16 px
    c.fill((3, 4), (21, 12), (3, 20), (7.5, 12))
    c.line((3, 4), (21, 12), (3, 20), (7.5, 12), closed=True)


# file stem: (drawing, color)
ICONS = {
    "order_go": (order_go, CREAM), "order_transfer": (order_transfer, CREAM), "order_land": (order_land, CREAM),
    "order_embark": (order_embark, CREAM), "order_seize": (order_seize, CREAM), "order_destroy": (order_destroy, CREAM),
    "track_ship": (track_ship, CREAM),
}


def render(stem: str) -> Image.Image:
    drawing, color = ICONS[stem]
    canvas = Canvas(color=color, width=1.5 if stem == "track_ship" else WIDTH)
    drawing(canvas)
    return canvas.image()


def dds_bytes(stem: str) -> bytes:
    """The file's bytes, through icon_dds.write_dds (it takes a path)."""
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
    parser.add_argument("--sheet", metavar="PNG", help="also write a contact sheet of the set on the panel's dark ground")
    args = parser.parse_args()
    stale = []
    for stem in ICONS:
        target = ROOT / OUT_DIR / f"{stem}.dds"
        data = dds_bytes(stem)
        if not target.exists() or target.read_bytes() != data:
            stale.append(str(OUT_DIR / f"{stem}.dds"))
            if not args.check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
    if args.sheet:
        sheet = Image.new("RGBA", (len(ICONS) * 72 + 8, 80), (29, 31, 38, 255))
        for i, stem in enumerate(ICONS):
            sheet.alpha_composite(render(stem), (8 + i * 72, 8))
        sheet.save(args.sheet)
    for path in stale:
        print(("stale: " if args.check else "wrote: ") + path)
    if not stale:
        print("space fleet pictograms: current")
    return int(args.check and bool(stale))


if __name__ == "__main__":
    raise SystemExit(main())
