#!/usr/bin/env python3
"""
gen_batch_pm_icons.py - Generate category icons for all placeholder production methods.

Creates ~18 silhouette shapes Ã— 6 tier colors, assigns each PM to a category,
generates metallic embossed DDS icons, and updates PM texture references.

Usage:
    python gen_batch_pm_icons.py                  # Generate icons + update PM files
    python gen_batch_pm_icons.py --preview         # Only generate PNGs in preview/ dir
    python gen_batch_pm_icons.py --dry-run         # Show PMâ†’icon mapping without generating
    python gen_batch_pm_icons.py --icons-only      # Generate DDS icons but don't update PM files
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from gen_pm_icons import (
    apply_metallic_style,
    convert_to_dds,
    find_texconv,
    load_silhouette,
    parse_color,
    OUTPUT_DIR,
)

# â”€â”€ Constants â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
S = 512       # Silhouette canvas size
C = S // 2    # Center (256)
R = 186       # Usable radius
W = (255, 255, 255, 255)   # White fill for shapes

# Color by PM group type (matches vanilla conventions)
GROUP_TYPE_COLORS = {
    "primary":    "gold",    # base/primary PM group (slot 0)
    "secondary":  "purple",  # 2nd processing/variant group
    "automation": "green",   # automation/mechanization
    "special":    "blue",    # power bloc, branding, ownership, maintenance
}

# All placeholder texture filenames that need replacement
PLACEHOLDER_SET = {"base1.dds", "base2.dds", "base3.dds", "base4.dds", "base5.dds", "base6.dds", "transparent.dds"}
# Pattern matching previously-generated wrong icons (cat_{shape}_t{tier}.dds)
CAT_REGEN_PATTERN = re.compile(r"cat_\w+_[tp]\d+\.dds")

PM_DIR = SCRIPT_DIR / "common" / "production_methods"


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# SHAPE DRAWING FUNCTIONS
# Each returns a 512Ã—512 RGBA image: white solid shape on transparent bg.
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _new() -> Image.Image:
    return Image.new("RGBA", (S, S), (0, 0, 0, 0))


def _d(img: Image.Image) -> ImageDraw.ImageDraw:
    return ImageDraw.Draw(img)


def draw_factory() -> Image.Image:
    """Factory building with chimney â€” company PMs."""
    img = _new(); d = _d(img)
    # Main building body
    d.rectangle([90, 255, 375, 442], fill=W)
    # Sloped roof
    d.polygon([(90, 255), (140, 175), (325, 175), (375, 255)], fill=W)
    # Chimney stack
    d.rectangle([305, 80, 365, 175], fill=W)
    # Chimney cap
    d.rectangle([295, 68, 375, 88], fill=W)
    return img


def draw_gear() -> Image.Image:
    """Gear wheel â€” manufacturing, assembly, mechanical."""
    img = _new(); d = _d(img)
    # Central body circle
    r_body = 135
    d.ellipse([C - r_body, C - r_body, C + r_body, C + r_body], fill=W)
    # 8 teeth as rotated rectangles
    for i in range(8):
        a = 2 * math.pi * i / 8
        tcx = C + 155 * math.cos(a)
        tcy = C + 155 * math.sin(a)
        hw, hh = 28, 30
        ca, sa = math.cos(a), math.sin(a)
        corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        pts = [(tcx + x * ca - y * sa, tcy + x * sa + y * ca) for x, y in corners]
        d.polygon(pts, fill=W)
    # Center hole
    r_hole = 40
    arr = np.array(img)
    y, x = np.ogrid[:S, :S]
    arr[((x - C) ** 2 + (y - C) ** 2) < r_hole ** 2] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_shield() -> Image.Image:
    """Shield/badge â€” military, weapons."""
    img = _new(); d = _d(img)
    # Classic heater shield
    pts = [
        (C, 70),          # top center
        (C + 170, 110),   # top right
        (C + 165, 280),   # mid right
        (C + 80, 380),    # lower right
        (C, 442),         # bottom point
        (C - 80, 380),    # lower left
        (C - 165, 280),   # mid left
        (C - 170, 110),   # top left
    ]
    d.polygon(pts, fill=W)
    return img


def draw_bolt() -> Image.Image:
    """Lightning bolt â€” power, energy, electricity."""
    img = _new(); d = _d(img)
    # Z-shaped thick bolt
    pts = [
        (170, 70),    # top-left
        (360, 70),    # top-right
        (275, 237),   # center-right from top diagonal
        (360, 237),   # jog right
        (360, 275),   # center-right bottom
        (275, 442),   # bottom-right
        (150, 442),   # bottom-left
        (235, 275),   # center-left from bottom diagonal
        (150, 275),   # jog left
        (150, 237),   # center-left top
    ]
    d.polygon(pts, fill=W)
    return img


def draw_chip() -> Image.Image:
    """Microchip â€” computing, electronics, processors."""
    img = _new(); d = _d(img)
    # Central IC body
    body = 120
    d.rectangle([C - body, C - body, C + body, C + body], fill=W)
    # Pins on each side (4 pins per side)
    pin_w, pin_h = 16, 36
    for side in range(4):
        for j in range(4):
            offset = -75 + j * 50
            if side == 0:    # top
                d.rectangle([C + offset - pin_w, C - body - pin_h,
                             C + offset + pin_w, C - body + 4], fill=W)
            elif side == 1:  # right
                d.rectangle([C + body - 4, C + offset - pin_w,
                             C + body + pin_h, C + offset + pin_w], fill=W)
            elif side == 2:  # bottom
                d.rectangle([C + offset - pin_w, C + body - 4,
                             C + offset + pin_w, C + body + pin_h], fill=W)
            elif side == 3:  # left
                d.rectangle([C - body - pin_h, C + offset - pin_w,
                             C - body + 4, C + offset + pin_w], fill=W)
    return img


def draw_rocket() -> Image.Image:
    """Rocket â€” space technology, aerospace."""
    img = _new(); d = _d(img)
    # Main body (tall rectangle with rounded top)
    bw = 60  # half-width of body
    d.rectangle([C - bw, 150, C + bw, 380], fill=W)
    # Nose cone (triangle)
    d.polygon([(C - bw, 150), (C, 70), (C + bw, 150)], fill=W)
    # Left fin
    d.polygon([(C - bw, 340), (C - bw - 60, 442), (C - bw, 442)], fill=W)
    # Right fin
    d.polygon([(C + bw, 340), (C + bw + 60, 442), (C + bw, 442)], fill=W)
    # Bottom plate
    d.rectangle([C - bw - 10, 415, C + bw + 10, 442], fill=W)
    return img


def draw_antenna() -> Image.Image:
    """Radio/broadcast tower â€” communications."""
    img = _new(); d = _d(img)
    # Tower body (tall triangle)
    d.polygon([(C, 70), (C + 120, 442), (C - 120, 442)], fill=W)
    # Horizontal crossbars
    for y_pos in [190, 280, 360]:
        frac = (y_pos - 70) / (442 - 70)
        hw = int(120 * frac)
        bar_h = 14
        d.rectangle([C - hw - 20, y_pos - bar_h, C + hw + 20, y_pos + bar_h], fill=W)
    # Top antenna nub
    d.ellipse([C - 18, 55, C + 18, 85], fill=W)
    return img


def draw_diamond() -> Image.Image:
    """Diamond/rhombus â€” mining, extraction."""
    img = _new(); d = _d(img)
    # Rotated square (diamond)
    pts = [
        (C, 70),       # top
        (C + R, C),    # right
        (C, 442),      # bottom
        (C - R, C),    # left
    ]
    d.polygon(pts, fill=W)
    return img


def draw_leaf() -> Image.Image:
    """Leaf shape â€” environment, emissions, nature."""
    img = _new(); d = _d(img)
    # Leaf as a pointed ellipse (egg shape via polygon)
    n = 60
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        # Leaf shape: wider at top, pointed at bottom
        rx = 130
        ry = 180
        # Apply taper: narrower towards bottom (t=Ï€)
        taper = 0.3 + 0.7 * (1 + math.cos(t)) / 2  # 1.0 at top, 0.3 at bottom
        x = rx * math.sin(t) * taper
        y = -ry * math.cos(t)
        pts.append((C + x, C + y))
    d.polygon(pts, fill=W)
    # Stem at bottom
    d.line([(C, C + 170), (C + 15, C + R + 10)], fill=W, width=16)
    return img


def draw_wheat() -> Image.Image:
    """Wheat/grain stalk â€” agriculture, farming."""
    img = _new(); d = _d(img)
    # Vertical stalk
    d.line([(C, 442), (C, 130)], fill=W, width=16)
    # Grain kernels (pairs of ellipses at angles)
    for j, y_pos in enumerate([140, 190, 240, 290]):
        for side in [-1, 1]:
            angle = side * 0.5  # slight angle
            kw, kh = 30, 22
            kx = C + side * 40
            ky = y_pos
            d.ellipse([kx - kw, ky - kh, kx + kw, ky + kh], fill=W)
    # Top kernel
    d.ellipse([C - 25, 100, C + 25, 155], fill=W)
    return img


def draw_flask() -> Image.Image:
    """Erlenmeyer flask â€” chemistry, science, materials."""
    img = _new(); d = _d(img)
    # Flask body (wide triangle bottom)
    d.polygon([
        (C - 30, 160),   # neck left
        (C - 160, 442),  # base left
        (C + 160, 442),  # base right
        (C + 30, 160),   # neck right
    ], fill=W)
    # Neck (rectangle)
    d.rectangle([C - 30, 80, C + 30, 170], fill=W)
    # Rim (wider at top)
    d.rectangle([C - 45, 70, C + 45, 90], fill=W)
    return img


def draw_building() -> Image.Image:
    """Tall building/skyscraper â€” construction, HQ, infrastructure."""
    img = _new(); d = _d(img)
    # Main tower
    d.rectangle([C - 80, 100, C + 80, 442], fill=W)
    # Stepped top
    d.rectangle([C - 55, 80, C + 55, 110], fill=W)
    d.rectangle([C - 30, 60, C + 30, 90], fill=W)
    # Antenna
    d.rectangle([C - 6, 30, C + 6, 65], fill=W)
    # Side wing left
    d.rectangle([C - 140, 260, C - 75, 442], fill=W)
    # Side wing right
    d.rectangle([C + 75, 300, C + 140, 442], fill=W)
    return img


def draw_cube() -> Image.Image:
    """3D cube â€” trade, goods, commerce, logistics."""
    img = _new(); d = _d(img)
    # Isometric cube
    # Top face
    d.polygon([
        (C, 90),           # top
        (C + 160, 170),    # right
        (C, 250),          # center
        (C - 160, 170),    # left
    ], fill=W)
    # Left face (slightly darker would be nice but we're doing solid white)
    d.polygon([
        (C - 160, 170),    # top-left
        (C, 250),          # top-right
        (C, 430),          # bottom-right
        (C - 160, 350),    # bottom-left
    ], fill=W)
    # Right face
    d.polygon([
        (C, 250),          # top-left
        (C + 160, 170),    # top-right
        (C + 160, 350),    # bottom-right
        (C, 430),          # bottom-left
    ], fill=W)
    return img


def draw_train() -> Image.Image:
    """Train/locomotive â€” rail transport, logistics."""
    img = _new(); d = _d(img)
    # Body (rectangle)
    d.rectangle([100, 150, 412, 370], fill=W)
    # Roof (slight arc approximated as trapezoid)
    d.polygon([(110, 150), (130, 115), (400, 115), (412, 150)], fill=W)
    # Smokestack
    d.rectangle([140, 75, 190, 120], fill=W)
    d.rectangle([130, 65, 200, 82], fill=W)
    # Front cow-catcher
    d.polygon([(412, 320), (442, 370), (412, 370)], fill=W)
    # Wheels (3 circles)
    for wx in [160, 260, 360]:
        wr = 38
        d.ellipse([wx - wr, 370, wx + wr, 370 + wr * 2], fill=W)
    # Track line
    d.rectangle([70, 436, 442, 448], fill=W)
    return img


def draw_ship() -> Image.Image:
    """Ship hull â€” naval, shipbuilding, maritime."""
    img = _new(); d = _d(img)
    # Hull (curved bottom polygon)
    d.polygon([
        (80, 250),         # deck left
        (432, 250),        # deck right
        (380, 400),        # hull right
        (C, 442),          # keel
        (132, 400),        # hull left
    ], fill=W)
    # Superstructure
    d.rectangle([140, 170, 360, 255], fill=W)
    # Bridge
    d.rectangle([200, 120, 300, 175], fill=W)
    # Mast
    d.rectangle([C - 5, 70, C + 5, 125], fill=W)
    return img


def draw_car() -> Image.Image:
    """Car profile â€” automobiles, motor vehicles."""
    img = _new(); d = _d(img)
    # Body (lower rectangle)
    d.rectangle([80, 260, 432, 370], fill=W)
    # Cabin (upper trapezoid)
    d.polygon([(160, 260), (200, 170), (350, 170), (380, 260)], fill=W)
    # Two wheels
    for wx in [165, 355]:
        wr = 45
        d.ellipse([wx - wr, 345, wx + wr, 345 + wr * 2], fill=W)
    # Connect wheels with underbody
    d.rectangle([80, 370, 432, 395], fill=W)
    return img


def draw_film() -> Image.Image:
    """Film strip â€” media, entertainment, content."""
    img = _new(); d = _d(img)
    # Film strip body (tall rectangle)
    d.rectangle([130, 70, 382, 442], fill=W)
    # Sprocket holes (cut out from sides)
    arr = np.array(img)
    hole_h, hole_w = 25, 22
    for y_pos in range(90, 432, 50):
        # Left sprocket
        arr[y_pos:y_pos + hole_h, 138:138 + hole_w] = [0, 0, 0, 0]
        # Right sprocket
        arr[382 - hole_w:382, y_pos:y_pos + hole_h] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_star() -> Image.Image:
    """Five-pointed star â€” wonders, megastructures, special."""
    img = _new(); d = _d(img)
    pts = []
    for i in range(10):
        angle = math.pi * i / 5 - math.pi / 2
        r = R if i % 2 == 0 else R * 0.42
        pts.append((C + r * math.cos(angle), C + r * math.sin(angle)))
    d.polygon(pts, fill=W)
    return img


def draw_drill() -> Image.Image:
    """Drill bit â€” drilling, oil extraction."""
    img = _new(); d = _d(img)
    # Drill bit (pointed cone going down)
    d.polygon([
        (C - 70, 100),    # top-left
        (C + 70, 100),    # top-right
        (C + 50, 200),    # taper right
        (C + 8, 420),     # point right
        (C, 442),         # tip
        (C - 8, 420),     # point left
        (C - 50, 200),    # taper left
    ], fill=W)
    # Chuck (wide part at top)
    d.rectangle([C - 90, 70, C + 90, 110], fill=W)
    # Spiral grooves - just horizontal lines for texture
    arr = np.array(img)
    for y_pos in range(150, 400, 40):
        frac = (y_pos - 100) / (442 - 100)
        hw = int(70 * (1 - frac * 0.8))
        if hw > 5:
            arr[y_pos:y_pos + 6, C - hw:C + hw] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_atom() -> Image.Image:
    """Atom symbol â€” science, research, biotech."""
    img = _new(); d = _d(img)
    # Central nucleus
    d.ellipse([C - 40, C - 40, C + 40, C + 40], fill=W)
    # Three orbital ellipses (drawn as thick lines on rotated paths)
    for angle_deg in [0, 60, 120]:
        a = math.radians(angle_deg)
        # Draw elliptical orbit as polygon of points
        pts = []
        n = 80
        rx, ry = 175, 55  # ellipse radii
        for i in range(n):
            t = 2 * math.pi * i / n
            ex = rx * math.cos(t)
            ey = ry * math.sin(t)
            # Rotate
            x = ex * math.cos(a) - ey * math.sin(a)
            y = ex * math.sin(a) + ey * math.cos(a)
            pts.append((C + x, C + y))
        # Draw as thick outline by drawing two ellipses (outer and inner)
        # and subtracting inner from outer
        for thickness_sign in [1, -1]:
            offset = 10 * thickness_sign
            inner_pts = []
            for i in range(n):
                t = 2 * math.pi * i / n
                ex = (rx + offset) * math.cos(t)
                ey = (ry + offset) * math.sin(t)
                x = ex * math.cos(a) - ey * math.sin(a)
                y = ex * math.sin(a) + ey * math.cos(a)
                inner_pts.append((C + x, C + y))

        # Simpler: draw the orbit as a thick line using individual segments
        for i in range(n):
            t1 = 2 * math.pi * i / n
            t2 = 2 * math.pi * (i + 1) / n
            x1 = C + (rx * math.cos(t1) * math.cos(a) - ry * math.sin(t1) * math.sin(a))
            y1 = C + (rx * math.cos(t1) * math.sin(a) + ry * math.sin(t1) * math.cos(a))
            x2 = C + (rx * math.cos(t2) * math.cos(a) - ry * math.sin(t2) * math.sin(a))
            y2 = C + (rx * math.cos(t2) * math.sin(a) + ry * math.sin(t2) * math.cos(a))
            d.line([(x1, y1), (x2, y2)], fill=W, width=20)

    return img


def draw_bottle() -> Image.Image:
    """Bottle â€” food processing, beverages."""
    img = _new(); d = _d(img)
    # Body (wide bottom)
    d.rounded_rectangle([C - 100, 230, C + 100, 442], radius=20, fill=W)
    # Shoulder taper
    d.polygon([
        (C - 100, 240),   # body left
        (C - 35, 170),    # neck left
        (C + 35, 170),    # neck right
        (C + 100, 240),   # body right
    ], fill=W)
    # Neck
    d.rectangle([C - 35, 100, C + 35, 180], fill=W)
    # Cap
    d.rectangle([C - 42, 70, C + 42, 108], fill=W)
    return img


def draw_suitcase() -> Image.Image:
    """Suitcase â€” tourism, parks, travel."""
    img = _new(); d = _d(img)
    # Main body
    d.rounded_rectangle([90, 170, 422, 420], radius=20, fill=W)
    # Handle
    d.rounded_rectangle([200, 100, 312, 180], radius=15, fill=W)
    # Handle inner cutout
    arr = np.array(img)
    arr[120:162, 222:290] = [0, 0, 0, 0]
    # Belt/strap line
    arr[285:300, 100:412] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_plane() -> Image.Image:
    """Aircraft â€” aviation, aerospace."""
    img = _new(); d = _d(img)
    # Fuselage (horizontal body)
    d.rectangle([80, C - 25, 432, C + 25], fill=W)
    # Nose cone
    d.polygon([(432, C - 25), (460, C), (432, C + 25)], fill=W)
    # Wings (swept)
    d.polygon([
        (200, C - 25),    # wing root front
        (160, C - 25),    # wing root back
        (100, C - 170),   # wingtip
        (160, C - 140),   # wingtip inner
    ], fill=W)
    d.polygon([
        (200, C + 25),
        (160, C + 25),
        (100, C + 170),
        (160, C + 140),
    ], fill=W)
    # Tail fins
    d.polygon([(90, C - 25), (70, C - 90), (110, C - 25)], fill=W)
    d.polygon([(90, C + 25), (70, C + 90), (110, C + 25)], fill=W)
    return img


def draw_cloth() -> Image.Image:
    """Thread spool/bobbin â€” textiles, clothing, packaging."""
    img = _new(); d = _d(img)
    # Spool flanges (top and bottom)
    d.ellipse([C - 150, 65, C + 150, 175], fill=W)
    d.ellipse([C - 150, 340, C + 150, 450], fill=W)
    # Core barrel
    d.rectangle([C - 80, 110, C + 80, 400], fill=W)
    # Center hole (cut out)
    arr = np.array(img)
    y, x = np.ogrid[:S, :S]
    hole = ((x - C) ** 2) / 40 ** 2 + ((y - C) ** 2) / 60 ** 2 < 1
    arr[hole] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_wrench() -> Image.Image:
    """Wrench â€” maintenance, tooling, repair."""
    img = _new(); d = _d(img)
    # Handle (diagonal bar)
    hw = 25
    # Diagonal from bottom-left to upper-right
    pts = [
        (C - 120 - hw, 442),
        (C - 120 + hw, 442),
        (C + 80 + hw, 140),
        (C + 80 - hw, 140),
    ]
    d.polygon(pts, fill=W)
    # Jaw (open end at top-right) - U shape
    d.ellipse([C + 40, 70, C + 180, 210], fill=W)
    # Cut out jaw opening
    arr = np.array(img)
    y, x = np.ogrid[:S, :S]
    jaw_hole = ((x - (C + 110)) ** 2 + (y - 90) ** 2) < 45 ** 2
    arr[jaw_hole] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_robot() -> Image.Image:
    """Robot/hexagonal nut â€” robotics, automation, AI systems."""
    img = _new(); d = _d(img)
    # Hexagonal nut shape
    pts = []
    for i in range(6):
        angle = math.pi * i / 3 - math.pi / 6
        pts.append((C + R * math.cos(angle), C + R * math.sin(angle)))
    d.polygon(pts, fill=W)
    # Center hole
    r_hole = 65
    arr = np.array(img)
    y, x = np.ogrid[:S, :S]
    arr[((x - C) ** 2 + (y - C) ** 2) < r_hole ** 2] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_globe() -> Image.Image:
    """Globe with arrow â€” trade, tourism, international."""
    img = _new(); d = _d(img)
    # Circle
    r = 160
    d.ellipse([C - r, C - r, C + r, C + r], fill=W)
    # Arrow wrapping around (simplified as a chevron above the globe)
    d.polygon([
        (C + 80, C - r - 30),   # arrow tip
        (C + 180, C - r + 30),  # right
        (C + 80, C - r + 10),   # notch
        (C - 20, C - r + 30),   # left
    ], fill=W)
    return img


# â”€â”€ Shape registry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SHAPES: dict[str, callable] = {
    "factory":  draw_factory,
    "gear":     draw_gear,
    "shield":   draw_shield,
    "bolt":     draw_bolt,
    "chip":     draw_chip,
    "rocket":   draw_rocket,
    "antenna":  draw_antenna,
    "diamond":  draw_diamond,
    "leaf":     draw_leaf,
    "wheat":    draw_wheat,
    "flask":    draw_flask,
    "building": draw_building,
    "cube":     draw_cube,
    "train":    draw_train,
    "ship":     draw_ship,
    "car":      draw_car,
    "film":     draw_film,
    "star":     draw_star,
    "drill":    draw_drill,
    "atom":     draw_atom,
    "bottle":   draw_bottle,
    "suitcase": draw_suitcase,
    "plane":    draw_plane,
    "cloth":    draw_cloth,
    "wrench":   draw_wrench,
    "robot":    draw_robot,
    "globe":    draw_globe,
}


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PM CATEGORIZATION
# Rules are checked in order; first match wins.
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# Regex patterns â†’ category name (checked in priority order)
CATEGORY_RULES: list[tuple[str, str]] = [
    # â”€â”€ Maintenance/special â”€â”€
    (r"^pm_maintenance$", "wrench"),

    # â”€â”€ Space megastructures â”€â”€
    (r"solar_collector|solar_receiver|orbital_battlestation|antimatter_facility|mind_upload_nexus", "star"),

    # â”€â”€ Wonders â”€â”€
    (r"^pm_wonder_", "star"),

    # â”€â”€ Space/rockets â”€â”€
    (r"rocket|earth_orbit|moon_mission|mars_mission|solar_exploration|interstellar_mission|"
     r"ssto|spaceport|spacex|roscosmos|orbital_fab|microgravity|orbital_nano|"
     r"antimatter_engine|no_rockets", "rocket"),

    # â”€â”€ Aviation â”€â”€
    (r"aeroplane|airport|aerodrome|aerospace_production|bae_samlesbury", "plane"),

    # â”€â”€ Military/weapons â”€â”€
    (r"cartridge|rifle|explosive|artillery|armor(?!ed)|munition|fuze|shell(?!_)|"
     r"projector|warhead|small_arms|ordnance|arsenal|proving_ground|military_research|"
     r"military_ship|active_protection|smart_fuze|networked_munition|swarm_coordinated|"
     r"swarm_release|programmable_matter_artillery|programmable_munition", "shield"),

    # â”€â”€ Mining/extraction â”€â”€
    (r"mine(?!r)|mining|colliery|excavation|continuous_miner|ore_sorting|geophysical|"
     r"assay_office|smelter|concentrat|lkab_kiruna|ocp_khouribga|kaiping_tangshan|"
     r"mokta_el_hadid|bengal_coal|kirgizian_copper", "diamond"),

    # â”€â”€ Drilling/oil â”€â”€
    (r"drill(?:ing)?_rig|fracking|offshore_rig|oil_field|oil_depot|pipeline|tank_farm|"
     r"catalytic_cracking|synthetic_oil|boryslaw|masjed_soleyman|maracaibo|ploiesti|"
     r"tampico_refinery|abadan_refinery|nioc_|west_ural_oil|turkish_petroleum|"
     r"galician_boryslaw|romanian_star|caribbean_petroleum|nederlandse_petroleum|"
     r"anglo_persian|petroleum", "drill"),

    # â”€â”€ Power/energy â”€â”€
    (r"power_(?:manual|centralized|integrated|hub)|renewable_power|tokamak|fusion_power|"
     r"inertial_fusion|compact_modular_fusion|space_power|power_station|"
     r"distributed_control|smart_systems|streetlight|led_street|sodium_street|"
     r"ai_managed_power_plant|ingolstadt_power|calcutta_electric|electricidad_caracas|"
     r"eea_dock_sud|norsk_hydro|nuclear_power", "bolt"),

    # â”€â”€ Computing/electronics â”€â”€
    (r"punchcard|transistor|integrated_circuit|microprocessor|cleanroom|"
     r"multicore|neuromorphic|self_improving_ai|academic_computing|"
     r"personal_electronics|smart_phone|virtual_reality|computer_aided|"
     r"machine_learning|ai_managed_fab|intel_ronler|tsmc_fab|asml_|nvidia_|"
     r"data_fortress|generic_electronics|generic_data|quantum_dot|"
     r"micro_?processor|ai_optimized_operations", "chip"),

    # â”€â”€ Communications â”€â”€
    (r"teletype|telegraph|twisted_pair|vhf_and_uhf|satellite_comm|fiber_optic|"
     r"internet_comm|quantum_comm|neural_lace_comm|integrated_optical|"
     r"local_network|bandwidth|ericsson_telefonplan|nokia_cable|"
     r"verizon_building|philips_eindhoven|cochlear_global|blackberry_rim|"
     r"huawei_ox_horn", "antenna"),

    # â”€â”€ Robotics/AI/automation â”€â”€
    (r"^pm_(?:robots|smart_robots|nanobot|nanorobot|self_replicating|drone_delivery|"
     r"robotic_service|generic_robotics|autonomous_network|boston_dynamics|fanuc_forest|"
     r"advanced_self_replicating|ai_governance|artificial_personalit)", "robot"),

    # â”€â”€ Agriculture â”€â”€
    (r"farming|rice_farm|crop|harvest|orchard|potatoes|precision_agri|improved_crop|"
     r"fig_orchard|grain|cotton(?:_gin|_depot|_combine)|tea(?:_estate|_warehouse)|"
     r"sugar|plantation|granary|apple_orchard|citrus|natural_nurturing|"
     r"oriental_dev_kunsan|ralli_odessa|bunge_born|moscow_irrigation|"
     r"lee_wilson|perskhlopok|persshelk|opium_ghazipur|"
     r"generic_granary|generic_cold_storage", "wheat"),

    # â”€â”€ Fishing â”€â”€
    (r"purse_seine|fishing|fish_market|generic_fish", "wheat"),

    # â”€â”€ Chemistry/materials â”€â”€
    (r"polyester|polyisoprene|injection_molding|blow_molding|bioplastic|"
     r"polymerization|ziegler_natta|neodymium_catalyz|styrene_butadiene|"
     r"nylon|elastomeric|bioengineered_rubber|advanced_material_fiber|"
     r"continuous_processing|flow_chemistry|electroenzymatic|"
     r"ai_optimized_synthesis|cellulosic|generic_chem|"
     r"food_additive|high_fructose|programmable_sweet|"
     r"basf_ludwigshafen|chr_hansen|pfizer_rd|roche_tower", "flask"),

    # â”€â”€ Food/beverages â”€â”€
    (r"wine|liquor|beer|brew|distill|vodka|bodega|vintner|tobacco|"
     r"robotic_food|programmable_food|cold_storage|frigor|slaughter|"
     r"meat|bakery|dairy|cheese|flour|"
     r"guinness|san_miguel|bacardi|pedro_domecq|douro_wine|"
     r"argentinian_wine|rod[iÃ­]guez_arguelles|imperial_tobacco|"
     r"sunhwaguk|tobacco_regie|united_tobacco|generic_vintner|"
     r"klanicko_|gavrilovic_|sansinena_|allatini_|elso_budapesti|"
     r"gran_azucarera", "bottle"),

    # â”€â”€ Environment/emissions â”€â”€
    (r"emission|effluent|filtration|scrub|ventilation|tailings|waste_fiber|"
     r"settling_pond|closed_loop(?:_synth|_recycl)|green_assembly|"
     r"predictive_maintenance|fume|environmental|no_emission|no_effluent|"
     r"no_facility_emission|no_glassworks_fume|no_precision_environ|"
     r"no_synthesis_scrub|no_tailings", "leaf"),

    # â”€â”€ Textiles/clothing â”€â”€
    (r"textile|cloth|fabric|silk(?:_exchange|_mill|_reeling|_house)|"
     r"cotton_mill|wool|loom|weaving|spinning|dye|garment|fashion|"
     r"microfiber|performance_textile|programmable_matter_cloth|"
     r"programmable_fiber|flexible_packaging|self.healing_packaging|"
     r"customized_clothing|generic_textile|generic_silk|"
     r"bombay_dyeing|coats_ferguslie|dmc_mulhouse|espana_industrial|"
     r"getzner_bludenz|madura_mills|mantero_como|misr_mahalla|"
     r"morozov_orekhovo|nam_dinh|pernambuco|sherkate_eslamiya|"
     r"sherkat_shemali|portalis_lyon|afghan_nassaji|"
     r"jiangnan_nanjing|worth_rue|ai_managed_textile", "cloth"),

    # â”€â”€ Shipbuilding/naval â”€â”€
    (r"shipbuild|dockyard|shipyard|sailing_ship|dry_dock|fleet_terminal|"
     r"cruise_ship|generic_dry_dock|aker_oslo|anglo_sicilian|"
     r"ap_moller|cramp_philadelphia|estaleiro_maua|fcm_la_seyne|"
     r"foochow_mawei|gotaverken|john_brown_clydebank|schichau_elbing|"
     r"secn_ferrol|stt_haskoy|wadia_bombay|advanced_metamaterial|"
     r"modular_shipbuilding|robotic_ship_assembly|steam_paddleboat", "ship"),

    # â”€â”€ Rail/transport/logistics â”€â”€
    (r"traffic_control|passenger_carriage|bullet_train|containerized|"
     r"maglev|autonomous_train|container_port|global_port|"
     r"rail_nexus|logistics_hub|partial_bulk|multimodal_transit|"
     r"automated_loading|drone_delivery|railway|railroad|"
     r"orient_express|prussian_railway|great_indian_railway|"
     r"egyptian_rail|cordoba_railway|cfr_bucharest|sao_paulo_railway|"
     r"mav_budapest|tashkent_railroad|ethiopian_railway|iranian_state_railway|"
     r"mantetsu_dalian|hanseong_jeongi|generic_rail|suez_company|"
     r"panama_company", "train"),

    # â”€â”€ Automotive/road â”€â”€
    (r"automobile|motor_industry|motor_works|electric_car|highway|"
     r"hydrogen_fuel_cell|fusion_battery_motor|fusion_battery_vehicle|"
     r"graphene_electric_motor|diesel_electric_ferr|"
     r"no_water_personal_transport|generic_motor|"
     r"hispano_suiza|volkswagen|ursus_warsaw|massey_harris", "car"),

    # â”€â”€ Tourism/parks â”€â”€
    (r"tourism|mass_tourism|jet_age_tourism|modern_tourism|space_tourism|"
     r"national_park|national_forest|national_wildlife|"
     r"disney_world|universal_studios", "suitcase"),

    # â”€â”€ Media/entertainment â”€â”€
    (r"sound_film|television|broadcast|video_game|digital_stream|"
     r"digital_creation|version_control_and_dist|state_directed_media|"
     r"influencer|content_creator|fully_automated_content|"
     r"generic_media|netflix_|nintendo_|sony_pictures|"
     r"paradox_kvarnholmen|ricordi_galleria", "film"),

    # â”€â”€ Trade/commerce â”€â”€
    (r"electronic_brokerage|digital_trading|automated_trading|e.commerce|"
     r"shopping_mall|department_store|remote_work|trade_center_trade_quantity|"
     r"generic_export|generic_colonial|generic_financial|generic_resource_depository|"
     r"web_one|amazon_fulfillment|shopify_fulfillment|alibaba_cainiao|"
     r"eic_trading_house|mitsui_trading|john_holt_lagos|de_beers_sorting|"
     r"hbc_york_factory|rac_sitka|lanfang_pontianak|"
     r"ong_lung_sheng|ynchausti_manila|sassoon_bombay|"
     r"united_fruit|mozambique_company|ccci_leopoldville|"
     r"peruvian_amazon|b_grimm_bangkok|steel_brothers_syriam", "cube"),

    # â”€â”€ Construction/buildings â”€â”€
    (r"reinforced_concrete|tower_crane|prefab|nanomaterial_build|"
     r"3d_printed_build|no_construction_autom|advanced_construction|"
     r"generic_exhibition|generic_monument|generic_proving", "building"),

    # â”€â”€ Science/research/biotech â”€â”€
    (r"ai_assisted_research|assisted_postnatal|communal_child|"
     r"ectogenesis|eugenics|behavioral_condition|cloning_vat|"
     r"bioelectronic|neurostimulation|neural_lace_telepath|"
     r"ai_mediated_mind|automated_lab|national_lab|"
     r"generic_materials_lab|generic_rd_complex|generic_corporate_univ|"
     r"biotech_dye|quantum_dot_pigment|programmable_paper|"
     r"openai_research|infosys_mysore|hp_labs|sap_headquarters", "atom"),

    # â”€â”€ Paper â”€â”€
    (r"kraft_pulp|calendered|self_growing_paper", "flask"),

    # â”€â”€ HQ/power bloc â”€â”€
    (r"hq_cultural|hq_diplomatic|hq_ideological|hq_military_treaty|"
     r"hq_religious|hq_sovereign|hq_trade_league|"
     r"generic_hq_skyscraper|generic_industrial_city|generic_industrial_zone|"
     r"un_headquarters", "building"),

    # â”€â”€ AM fabrication â”€â”€
    (r"am_fabrication|3d_printed_porcelain", "gear"),

    # â”€â”€ Specific company headquarters â†’ building â”€â”€
    (r"apple_park|googleplex|microsoft_redmond|samsung_digital|"
     r"siemens_erlangen|softbank_vision|tencent_seafront|gazprom_lakhta|"
     r"oracle_cloud|petrobras_cenpes|rosatom_mayak|"
     r"bytedance_data|catl_giga|ikea_almhult|eni_palazzo", "building"),

    # â”€â”€ Semiconductor/space companies â”€â”€
    (r"spacex_starbase|roscosmos_vostochny", "rocket"),

    # â”€â”€ Porcelain/glass â”€â”€
    (r"porcelain|glass_works|kiln|pottery|jingdezhen|kinkozan|meissen|"
     r"moser_karlsbad", "flask"),

    # â”€â”€ Wood/furniture/paper â”€â”€
    (r"debarker|chipper|skidder|forwarder|lumber|timber|furniture|"
     r"programmable_matter_furniture|maple_tottenham|"
     r"bombay_burmah|kablin_zarate|klein_galician|thonet_bystrice", "gear"),

    # â”€â”€  Religion/social â”€â”€
    (r"decentralized_religious|secular_society|youth_cadre|voluntary_daycare", "building"),

    # â”€â”€ Specific company PMs â†’ factory (catch-all for named companies) â”€â”€
    (r"(?:_works|_mill[s]?|_factory|_plant|_foundry|_steelworks|_ironworks|"
     r"_arsenal|_armory|_furnace|_smelter|_dockyard|_shipyard|_colliery|"
     r"_laboratory|_station|_terminal|_workshop|_bakery|_warehouse|"
     r"_distillery|_brewery|_refinery|_depot|_wharf|_pier|_concentrator|"
     r"_estate|_trading_house|_trading_post|_slaughterhouse|_meatworks|"
     r"_proving_ground|_campus|_institute|_center|_munition)", "factory"),

    # â”€â”€ Assembly/manufacturing generics â”€â”€
    (r"manual_assembly|manual_production|manual_batch|"
     r"automated_assembly|robotic_assembly|ai_managed_building|"
     r"advanced_assembly|intelligent_manufacturing|self_optimizing|"
     r"industrial_robotics|robotic_assembly_handling|"
     r"generic_machine_shop|generic_industrial|"
     r"advanced_process_control|advanced_workflow|"
     r"networked_control|automated_chemical|"
     r"generic_foundry|generic_ordnance|schneider_le_creusot", "gear"),

    # â”€â”€ Fusion battery appliances, etc â”€â”€
    (r"fusion_battery_appliance", "bolt"),

    # â”€â”€ Fallback: everything else â†’ gear â”€â”€
]

# Compiled rules
_COMPILED_RULES = [(re.compile(pat, re.IGNORECASE), cat) for pat, cat in CATEGORY_RULES]


def categorize_pm(pm_name: str, source_file: str) -> str:
    """Determine the icon category for a PM based on its name and source file."""
    # Check rules in order
    for pattern, category in _COMPILED_RULES:
        if pattern.search(pm_name):
            return category

    # Fallback: if in unique_pms.txt, likely a company PM
    if source_file == "unique_pms.txt":
        return "factory"

    # Final fallback
    return "gear"


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PM GROUP TYPE CLASSIFICATION (from mod state server)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

import json
import urllib.request


def classify_pmg_type(pmg_id: str, slot_idx: int, total_slots: int) -> str:
    """Classify a PM group into a type for color assignment.

    Returns one of: primary, secondary, automation, special
    """
    pmg_lower = pmg_id.lower()

    # Explicit automation groups
    if any(kw in pmg_lower for kw in [
        "automation", "mechanization", "mechanisation",
        "steam_automation", "train_automation",
    ]):
        return "automation"

    # Power bloc / special groups
    if any(kw in pmg_lower for kw in [
        "power_bloc", "ownership", "branding", "company",
        "hq_type", "special", "maintenance", "tailings",
        "facility_emission", "effluent", "emission_standard",
        "fume", "ventilation", "wastewater",
    ]):
        return "special"

    # Slot 0 is always primary
    if slot_idx == 0:
        return "primary"

    # Slot 1 is typically secondary
    if slot_idx == 1:
        return "secondary"

    # Middle slots (after slot 1 and before last) are automation-like
    if slot_idx >= 2 and slot_idx < total_slots - 1:
        return "automation"

    # Last slot is usually special/maintenance
    if slot_idx == total_slots - 1 and total_slots > 2:
        return "special"

    return "secondary"


def build_pm_group_map() -> tuple[dict[str, str], list[list[str]]]:
    """Query mod state server to map each PM to its group type, and return group membership.

    Returns:
        pm_type_map: {pm_id: group_type}  (e.g. "primary", "secondary", "automation", "special")
        pm_groups:   list of [pm_id, ...] lists, one per PM group across all buildings
    """
    try:
        data = json.loads(
            urllib.request.urlopen(
                "http://127.0.0.1:8950/buildings?detail=true"
            ).read()
        )
    except Exception as e:
        print(f"WARNING: Could not reach mod state server: {e}")
        print("  All PMs will default to 'primary' (gold) color.")
        return {}, []

    pm_type_map: dict[str, str] = {}
    pm_groups: list[list[str]] = []

    for building in data:
        pmgs = building.get("pm_groups", [])
        total_slots = len(pmgs)
        for slot_idx, pmg in enumerate(pmgs):
            pmg_id = pmg["id"]
            group_type = classify_pmg_type(pmg_id, slot_idx, total_slots)
            pms = pmg.get("production_methods", [])
            group_pm_ids = []
            for pm in pms:
                pm_id = pm["id"]
                pm_type_map[pm_id] = group_type
                group_pm_ids.append(pm_id)
            pm_groups.append(group_pm_ids)

    return pm_type_map, pm_groups


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PM FILE PARSING
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def find_placeholder_pms() -> dict[str, tuple[str, str]]:
    """Find all PMs using placeholder or previously-generated wrong icons.

    Detects both original placeholders (base1-6.dds, transparent.dds) and
    previously-generated cat_*_t*.dds patterns that need regeneration.

    Returns: {pm_name: (source_filename, matched_texture)}
    """
    results = {}

    for fname in os.listdir(PM_DIR):
        if not fname.endswith(".txt"):
            continue
        fpath = PM_DIR / fname
        with open(fpath, "r", encoding="utf-8-sig") as f:
            content = f.read()

        current_pm = None
        brace_depth = 0
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            # Track top-level PM blocks
            if brace_depth == 0:
                if "=" in stripped and "{" in stripped:
                    name = stripped.split("=")[0].strip()
                    if name.startswith(("pm_", "GMO_")):
                        current_pm = name
                        brace_depth += stripped.count("{") - stripped.count("}")
                        continue
                # Handle single-line non-PM definitions or blank lines
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth < 0:
                    brace_depth = 0
                continue

            if current_pm:
                brace_depth += stripped.count("{") - stripped.count("}")
                if "texture" in stripped:
                    # Check original placeholders
                    for ph in PLACEHOLDER_SET:
                        if ph in stripped:
                            results[current_pm] = (fname, ph)
                            break
                    else:
                        # Check previously-generated cat_*_t*.dds
                        m = CAT_REGEN_PATTERN.search(stripped)
                        if m:
                            results[current_pm] = (fname, m.group())
                if brace_depth <= 0:
                    current_pm = None
                    brace_depth = 0
            else:
                # Non-PM block - still track depth
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth <= 0:
                    brace_depth = 0

    return results


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ICON GENERATION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def draw_pips_on_icon(icon: Image.Image, pip_count: int, base_color: tuple[int, int, int]) -> Image.Image:
    """Overlay metallic-looking pip dots on a finished 104×104 icon.

    Pips are rendered directly at final size for maximum visibility.
    """
    if pip_count <= 0:
        return icon

    img = icon.copy()
    d = ImageDraw.Draw(img)

    pip_r = 4        # radius in final pixels
    pip_gap = 11     # center-to-center spacing
    pip_y = 96       # y position (near bottom of 104px icon)

    total_w = (pip_count - 1) * pip_gap
    center_x = 52    # center of 104px
    start_x = center_x - total_w // 2

    # Draw pips as colored circles with slight highlight
    r, g, b = base_color
    # Lighter highlight color
    lr = min(255, int(r * 1.4))
    lg = min(255, int(g * 1.4))
    lb = min(255, int(b * 1.4))
    # Darker outline
    dr = int(r * 0.4)
    dg = int(g * 0.4)
    db = int(b * 0.4)

    for i in range(pip_count):
        cx = start_x + i * pip_gap
        cy = pip_y
        # Dark outline
        d.ellipse([cx - pip_r - 1, cy - pip_r - 1, cx + pip_r + 1, cy + pip_r + 1],
                   fill=(dr, dg, db, 255))
        # Main pip
        d.ellipse([cx - pip_r, cy - pip_r, cx + pip_r, cy + pip_r],
                   fill=(r, g, b, 255))
        # Highlight (upper-left quarter)
        d.ellipse([cx - pip_r + 1, cy - pip_r, cx + 1, cy],
                   fill=(lr, lg, lb, 255))

    return img


def generate_silhouette(shape_name: str, out_path: Path) -> None:
    """Generate and save a silhouette PNG."""
    draw_fn = SHAPES[shape_name]
    img = draw_fn()
    img.save(out_path, format="PNG")


def icon_key(category: str, color: str, pips: int) -> str:
    """Generate the icon filename key."""
    return f"cat_{category}_{color}_p{pips}"


def generate_all_icons(
    pm_map: dict[str, tuple[str, str, str, str, int]],
    preview_only: bool = False,
) -> dict[str, Path]:
    """Generate all needed category x color x pips DDS icons.

    pm_map: {pm_name: (source_file, placeholder, category, color, pips)}

    Returns: {icon_key_str: dds_path}
    """
    # Determine unique (category, color, pips) combos needed
    needed: set[tuple[str, str, int]] = set()
    for pm_name, (_, _, category, color, pips) in pm_map.items():
        needed.add((category, color, pips))

    print(f"Need to generate {len(needed)} unique icons "
          f"across {len(set(c for c, _, _ in needed))} categories")

    # Find texconv
    texconv = None
    if not preview_only:
        texconv = find_texconv()
        if texconv is None:
            sys.path.insert(0, str(SCRIPT_DIR))
            from convert_event_image import ensure_texconv
            texconv = ensure_texconv()
        print(f"Using texconv: {texconv}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    preview_dir = SCRIPT_DIR / "preview_pm_icons"

    if preview_only:
        preview_dir.mkdir(exist_ok=True)

    icon_paths = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Generate base silhouette PNGs (one per category)
        silhouettes = {}
        categories_needed = set(c for c, _, _ in needed)
        for cat in sorted(categories_needed):
            sil_path = tmpdir / f"sil_{cat}.png"
            generate_silhouette(cat, sil_path)
            silhouettes[cat] = sil_path

        print(f"  Generated {len(silhouettes)} base silhouettes")

        # For each unique (category, color, pips) combo, generate icon
        for cat, color, pips in sorted(needed):
            key = icon_key(cat, color, pips)

            # Load silhouette (no pips at this stage)
            sil_path = silhouettes[cat]

            # Apply metallic style
            styled_path = tmpdir / f"{key}.png"
            sil_data = load_silhouette(str(sil_path), 104)
            color_rgb = parse_color(color)
            styled_arr = apply_metallic_style(sil_data, color_rgb)
            styled = Image.fromarray(styled_arr)

            # Add pips on top of the finished icon
            if pips > 0:
                styled = draw_pips_on_icon(styled, pips, color_rgb)
            styled.save(styled_path, format="PNG")

            if preview_only:
                # Save preview PNG
                preview_path = preview_dir / f"{key}.png"
                styled.save(preview_path, format="PNG")
                icon_paths[key] = preview_path
            else:
                # Convert to DDS
                dds_path = OUTPUT_DIR / f"{key}.dds"
                convert_to_dds(styled_path, dds_path, texconv=texconv)
                icon_paths[key] = dds_path

        print(f"  Generated {len(icon_paths)} icon files")

    return icon_paths


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PM FILE UPDATING
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def update_pm_files(
    pm_icons: dict[str, str],
    dry_run: bool = False,
) -> int:
    """Update PM texture references in .txt files.

    pm_icons: {pm_name: icon_filename} e.g. {"pm_foo": "cat_gear_gold_p0.dds"}

    Returns: count of PMs updated.
    """
    updates_by_file: dict[str, list[tuple[str, str]]] = defaultdict(list)

    # Find which PMs are in which files by re-scanning
    for fname in os.listdir(PM_DIR):
        if not fname.endswith(".txt"):
            continue
        fpath = PM_DIR / fname
        with open(fpath, "r", encoding="utf-8-sig") as f:
            content = f.read()

        current_pm = None
        brace_depth = 0
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if brace_depth == 0:
                if "=" in stripped and "{" in stripped:
                    name = stripped.split("=")[0].strip()
                    if name.startswith(("pm_", "GMO_")) and name in pm_icons:
                        current_pm = name
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth < 0:
                    brace_depth = 0
                continue
            if current_pm:
                brace_depth += stripped.count("{") - stripped.count("}")
                if "texture" in stripped:
                    updates_by_file[fname].append((current_pm, pm_icons[current_pm]))
                if brace_depth <= 0:
                    current_pm = None
                    brace_depth = 0
            else:
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth <= 0:
                    brace_depth = 0

    total = sum(len(v) for v in updates_by_file.values())
    if dry_run:
        for fname, updates in sorted(updates_by_file.items()):
            print(f"\n{fname}: {len(updates)} PMs to update")
            for pm_name, icon_file in updates[:5]:
                print(f"  {pm_name} -> {icon_file}")
            if len(updates) > 5:
                print(f"  ... and {len(updates) - 5} more")
        print(f"\nTotal: {total} PMs would be updated")
        return total

    # Apply updates via regex replacement on texture lines
    updated = 0
    for fname, updates in updates_by_file.items():
        fpath = PM_DIR / fname
        with open(fpath, "r", encoding="utf-8-sig") as f:
            content = f.read()

        # Build a map of PM names to new texture filenames
        pm_to_tex = {pm_name: tex_file for pm_name, tex_file in updates}

        lines = content.split("\n")
        new_lines = []
        current_pm = None
        brace_depth = 0

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("#"):
                new_lines.append(line)
                continue

            if brace_depth == 0:
                if "=" in stripped and "{" in stripped:
                    name = stripped.split("=")[0].strip()
                    if name.startswith(("pm_", "GMO_")) and name in pm_to_tex:
                        current_pm = name
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth < 0:
                    brace_depth = 0
                new_lines.append(line)
                continue

            if current_pm:
                brace_depth += stripped.count("{") - stripped.count("}")
                if "texture" in stripped:
                    new_tex = f"gfx/interface/icons/production_method_icons/{pm_to_tex[current_pm]}"
                    # Replace the texture path
                    line = re.sub(
                        r'texture\s*=\s*"[^"]*"',
                        f'texture = "{new_tex}"',
                        line,
                    )
                    updated += 1
                if brace_depth <= 0:
                    current_pm = None
                    brace_depth = 0
            else:
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth <= 0:
                    brace_depth = 0

            new_lines.append(line)

        # Write back with BOM
        new_content = "\n".join(new_lines)
        utf8bom = "\ufeff"
        if not new_content.startswith(utf8bom):
            new_content = utf8bom + new_content
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"  Updated {len(updates)} PMs in {fname}")

    return updated


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# MAIN
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def main():
    parser = argparse.ArgumentParser(description="Generate PM icons by group type")
    parser.add_argument("--preview", action="store_true",
                        help="Only generate preview PNGs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show PM->icon mapping without generating")
    parser.add_argument("--icons-only", action="store_true",
                        help="Generate DDS but don't update PM files")
    args = parser.parse_args()

    # 1. Find placeholder PMs
    print("Scanning for placeholder PMs...")
    placeholder_pms = find_placeholder_pms()
    print(f"Found {len(placeholder_pms)} PMs needing icons")

    if not placeholder_pms:
        print("No placeholder PMs found!")
        return

    # 2. Get PM group type data from mod state server
    print("\nQuerying mod state server for PM group types...")
    pm_type_map, pm_groups = build_pm_group_map()
    print(f"  Mapped {len(pm_type_map)} PMs to group types, {len(pm_groups)} PM groups")

    # 3. Determine category and color for each placeholder PM (pips assigned later)
    pm_cat_color: dict[str, tuple[str, str, str]] = {}  # pm_name -> (source_file, category, color)
    from collections import Counter
    color_counts = Counter()
    category_counts = Counter()

    for pm_name, (source_file, placeholder) in placeholder_pms.items():
        category = categorize_pm(pm_name, source_file)
        category_counts[category] += 1

        group_type = pm_type_map.get(pm_name, "primary")
        color = GROUP_TYPE_COLORS.get(group_type, "gold")
        color_counts[color] += 1

        pm_cat_color[pm_name] = (source_file, category, color)

    # 4. Assign pips per PM group: among PMs that share the same (category, color)
    #    within a group, if there's only one → 0 pips; if N → 1..N pips.
    pm_pips: dict[str, int] = {}  # pm_name -> pip count

    for group_pm_ids in pm_groups:
        # Only consider PMs that are in our placeholder set
        relevant = [pm_id for pm_id in group_pm_ids if pm_id in pm_cat_color]
        if not relevant:
            continue

        # Group by (category, color)
        by_icon: dict[tuple[str, str], list[str]] = defaultdict(list)
        for pm_id in relevant:
            _, cat, col = pm_cat_color[pm_id]
            by_icon[(cat, col)].append(pm_id)

        for (cat, col), pm_ids in by_icon.items():
            if len(pm_ids) == 1:
                pm_pips[pm_ids[0]] = 0
            else:
                for i, pm_id in enumerate(pm_ids):
                    pm_pips[pm_id] = i + 1  # 1-indexed pips

    # PMs not found in any group get 0 pips
    for pm_name in pm_cat_color:
        if pm_name not in pm_pips:
            pm_pips[pm_name] = 0

    # 5. Build final PM map
    pm_map: dict[str, tuple[str, str, str, str, int]] = {}
    for pm_name, (source_file, category, color) in pm_cat_color.items():
        pips = pm_pips[pm_name]
        pm_map[pm_name] = (source_file, placeholder_pms[pm_name][1], category, color, pips)

    print(f"\nGroup type distribution:")
    for color, count in color_counts.most_common():
        print(f"  {color:8s}: {count}")
    print(f"\nCategory distribution (top 10):")
    for cat, count in category_counts.most_common(10):
        print(f"  {cat:12s}: {count}")

    # 6. Dry run: just show the mapping
    if args.dry_run:
        print("\n--- DRY RUN ---")
        for pm_name, (src, _, cat, color, pips) in sorted(pm_map.items()):
            key = icon_key(cat, color, pips)
            print(f"  {pm_name:55s} -> {key}.dds  (from {src})")  
        unique_icons = len(set(icon_key(c, col, p) for _, (_, _, c, col, p) in pm_map.items()))
        print(f"\nTotal: {len(pm_map)} PMs -> {unique_icons} unique icons")
        return

    # 7. Generate icons
    print("\nGenerating icons...")
    icon_paths = generate_all_icons(pm_map, preview_only=args.preview)

    if args.preview:
        print(f"\nPreview PNGs saved to preview_pm_icons/")
        return

    if args.icons_only:
        print(f"\nDDS icons generated. Skipping PM file updates.")
        return

    # 8. Update PM files
    print("\nUpdating PM texture references...")
    pm_icons = {}
    for pm_name, (_, _, category, color, pips) in pm_map.items():
        pm_icons[pm_name] = f"{icon_key(category, color, pips)}.dds"

    count = update_pm_files(pm_icons)
    print(f"\nDone! Updated {count} of {len(pm_map)} PM texture references.")

    # 9. Clean up unused DDS files in the icon directory
    used_dds = set(pm_icons.values())
    removed = 0
    for f in OUTPUT_DIR.iterdir():
        if f.name.startswith("cat_") and f.suffix == ".dds":
            if f.name not in used_dds:
                f.unlink()
                removed += 1
    if removed:
        print(f"Cleaned up {removed} unused DDS files.")


if __name__ == "__main__":
    main()
