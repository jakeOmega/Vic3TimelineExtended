#!/usr/bin/env python3
"""Draw the Space Fleets cards' and Locations' pictograms (space_race_widget.gui,
te_sr_fleet_row and te_sr_location_cell).

The fleet cards (owner, 2026-11-14) show a fleet's ship roles, postures and
orders as icons, and Locations a location's status. These are the first set: flat line pictograms, drawn here
rather than rendered, so the layout can be judged in game with art of its own
(gui_style_guide.md rule 10). Painted replacements go through the icon
pipeline (icon_prompts.py, category `space`) under the same file names; the
subjects are in docs/systems/space_race_gui_icons.md, "Space Fleets: the fleet
cards". Once a file is painted, drop its entry here.

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
GOLD = (210, 176, 106, 255)    # the fleet's emblem
GREY = (170, 162, 143, 255)    # another power's fleets (Locations)
RED = (226, 104, 92, 255)      # a status that is bad for us (Locations)
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

    def ring(self, cx, cy, rx, ry=None, start=0.0, end=360.0):
        """An ellipse's outline, or an arc of it (degrees, clockwise from east)."""
        ry = rx if ry is None else ry
        steps = max(8, int(abs(end - start) / 4))
        pts = [(cx + rx * math.cos(math.radians(start + (end - start) * i / steps)),
                cy + ry * math.sin(math.radians(start + (end - start) * i / steps)))
               for i in range(steps + 1)]
        self.line(*pts)

    def dot(self, cx, cy, r):
        x, y = self._px((cx, cy))
        self.draw.ellipse((x - r * UNIT, y - r * UNIT, x + r * UNIT, y + r * UNIT), fill=self.color)

    def image(self) -> Image.Image:
        return icon_dds.resize_premultiplied(self.im, (SIZE, SIZE))


def fleet(c):          # the emblem: a shield with two chevrons
    c.line((12, 3), (20, 6.5), (20, 13), (17.5, 18), (12, 21.5), (6.5, 18), (4, 13), (4, 6.5), closed=True)
    c.line((8, 12.5), (12, 9), (16, 12.5))
    c.line((8, 16.5), (12, 13), (16, 16.5))


def fleet_other(c):    # another power's: the shield, bare
    c.line((12, 3), (20, 6.5), (20, 13), (17.5, 18), (12, 21.5), (6.5, 18), (4, 13), (4, 6.5), closed=True)
    c.line((8, 12), (16, 12))


def role_war(c):       # a hull with a bridge
    c.line((3, 14), (7, 10), (17, 10), (21, 13), (17, 16), (5, 16), closed=True)
    c.line((10, 10), (10, 6.5), (14, 6.5), (14, 10))


def role_rapid(c):     # a dart
    c.line((3, 12), (20, 5), (15.5, 12), (20, 19), closed=True)


def role_siege(c):     # a low hull under one long gun
    c.line((4, 17), (15, 17), (19, 14), (4, 14), closed=True)
    c.line((8, 14), (8, 9.5), (21, 9.5))
    c.line((8, 11.7), (12, 11.7))


def role_carrier(c):   # a flat deck, a craft lifting off it
    c.line((2, 13), (22, 13), (19, 17), (5, 17), closed=True)
    c.line((6, 13), (6, 10), (10, 10), (10, 13))
    c.line((14, 9), (16, 7), (18, 9))


def role_tender(c):    # a tank on a boom
    c.ring(6.5, 12.5, 3.5, 3.5, 90, 270)
    c.ring(13.5, 12.5, 3.5, 3.5, -90, 90)
    c.line((6.5, 9), (13.5, 9))
    c.line((6.5, 16), (13.5, 16))
    c.line((8.5, 9), (8.5, 16))
    c.line((11.5, 9), (11.5, 16))
    c.line((17, 12.5), (21, 12.5))


def posture_station(c):   # a world, a ship on its orbit
    c.dot(12, 12, 3.2)
    c.ring(12, 12, 8.5)
    c.dot(18, 6, 2.2)


def posture_standoff(c):  # a world, a screen held off it
    c.dot(6.5, 12, 3.2)
    c.ring(5, 12, 12, 9.5, -52, 52)
    c.line((20, 10), (22, 12), (20, 14))


def posture_closein(c):   # four arrows closing on a world
    c.dot(12, 12, 3.2)
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        tip = (12 + dx * 6.2, 12 + dy * 6.2)
        c.line((12 + dx * 10.3, 12 + dy * 10.3), tip)
        c.line((tip[0] + dx * 2 - dy * 2, tip[1] + dy * 2 - dx * 2), tip,
               (tip[0] + dx * 2 + dy * 2, tip[1] + dy * 2 + dx * 2))


def posture_interdict(c):  # a barred lane
    c.ring(12, 12, 7.5)
    c.line((6.7, 17.3), (17.3, 6.7))
    c.line((1.5, 12), (3.5, 12))
    c.line((20.5, 12), (22.5, 12))


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
    "fleet": (fleet, GOLD),
    "role_war": (role_war, CREAM), "role_rapid": (role_rapid, CREAM), "role_siege": (role_siege, CREAM),
    "role_carrier": (role_carrier, CREAM), "role_tender": (role_tender, CREAM),
    "posture_station": (posture_station, CREAM), "posture_standoff": (posture_standoff, CREAM),
    "posture_closein": (posture_closein, CREAM), "posture_interdict": (posture_interdict, CREAM),
    "order_go": (order_go, CREAM), "order_transfer": (order_transfer, CREAM), "order_land": (order_land, CREAM),
    "order_embark": (order_embark, CREAM), "order_seize": (order_seize, CREAM), "order_destroy": (order_destroy, CREAM),
    "track_ship": (track_ship, CREAM),
    # Locations: the others' caption, and the statuses that are bad for us in
    # red (ours wear the posture's own cream sign).
    "fleet_other": (fleet_other, GREY),
    "status_battle": (order_destroy, RED), "status_blockaded": (posture_standoff, RED),
    "status_interdicted": (posture_interdict, RED),
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
