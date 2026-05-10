#!/usr/bin/env python3
"""gen_law_icons.py - Generate law icons in vanilla Victoria 3 style.

Creates programmatic silhouette shapes for each law group/category, applies
the vanilla metallic embossed styling (same pipeline as gen_pm_icons.py),
and generates 256×256 DDS icons placed in gfx/interface/icons/law_icons/.

Idempotent: re-running only generates DDS files that don't already exist on disk.

Usage:
    python gen_law_icons.py                   # Generate missing DDS icons only
    python gen_law_icons.py --update-files     # Also update icon references in law .txt files
    python gen_law_icons.py --force             # Regenerate all icons even if DDS exists
    python gen_law_icons.py --preview           # Only generate PNGs in preview/ dir
    python gen_law_icons.py --dry-run           # Show law->icon mapping without generating
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
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

from gen_pm_icons import (
    apply_metallic_style,
    convert_to_dds,
    find_texconv,
    load_silhouette,
    parse_color,
)

# ── paths ────────────────────────────────────────────────────────────────
OUTPUT_DIR = REPO_ROOT / "gfx" / "interface" / "icons" / "law_icons"
LAW_DIR = REPO_ROOT / "common" / "laws"
ICON_SIZE = 256  # vanilla law icons are 256×256 or 302×302; 256 is the newer standard.

# ── silhouette canvas ────────────────────────────────────────────────────
S = 512        # drawing canvas size
C = S // 2     # center
R = 200        # usable radius (larger fill for law icons)
W = (255, 255, 255, 255)   # white fill


# ── color presets for law groups (warm gold like vanilla) ─────────────────
# Vanilla law icons have a uniform warm gold tone with median pixel ≈(186,148,115).
# Our metallic pipeline multiplies base color by ~0.70 illumination, so we need
# brighter base values.  Two shades: standard gold and a slightly dimmer variant
# for "no_ministry" / disabled laws — both clearly read as the same golden family.
LAW_COLORS: dict[str, tuple[int, int, int]] = {
    "gold":        (255, 215, 165),   # standard warm gold matching vanilla
    "dark_gold":   (235, 195, 150),   # slightly dimmer gold for "no_X" laws
}


def _new() -> Image.Image:
    return Image.new("RGBA", (S, S), (0, 0, 0, 0))


def _d(img: Image.Image) -> ImageDraw.ImageDraw:
    return ImageDraw.Draw(img)


# ═══════════════════════════════════════════════════════════════════════════
# SHAPE DRAWING FUNCTIONS
# Each returns a 512×512 RGBA image: white solid shape on transparent bg.
# ═══════════════════════════════════════════════════════════════════════════

def draw_scroll() -> Image.Image:
    """Scroll/document — inheritance, IP, legal traditions."""
    img = _new(); d = _d(img)
    # Main parchment body
    d.rectangle([130, 100, 382, 420], fill=W)
    # Top curl (ellipse)
    d.ellipse([110, 70, 402, 140], fill=W)
    # Bottom curl
    d.ellipse([110, 390, 402, 460], fill=W)
    # Text lines (cut out) for visual interest
    arr = np.array(img)
    for y_pos in range(175, 380, 35):
        arr[y_pos:y_pos + 8, 170:355] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_scales() -> Image.Image:
    """Scales of justice — criminal justice, restorative justice."""
    img = _new(); d = _d(img)
    # Central pillar
    d.rectangle([C - 10, 100, C + 10, 440], fill=W)
    # Base
    d.polygon([(C - 100, 420), (C + 100, 420), (C + 80, 450), (C - 80, 450)], fill=W)
    # Crossbar
    d.rectangle([80, 100, 432, 118], fill=W)
    # Left pan (triangle + bowl)
    d.line([(120, 118), (120, 280)], fill=W, width=8)
    d.arc([50, 250, 190, 340], 0, 180, fill=W, width=12)
    d.chord([50, 250, 190, 340], 0, 180, fill=W)
    # Right pan
    d.line([(392, 118), (392, 240)], fill=W, width=8)
    d.arc([322, 210, 462, 300], 0, 180, fill=W, width=12)
    d.chord([322, 210, 462, 300], 0, 180, fill=W)
    return img


def draw_shield_cross() -> Image.Image:
    """Shield with cross — war rules, humanitarian, military law."""
    img = _new(); d = _d(img)
    # Shield outline
    pts = [
        (C, 60),
        (C + 180, 100),
        (C + 175, 290),
        (C + 90, 400),
        (C, 460),
        (C - 90, 400),
        (C - 175, 290),
        (C - 180, 100),
    ]
    d.polygon(pts, fill=W)
    # Cross cutout
    arr = np.array(img)
    arr[200:270, C - 100:C + 100] = [0, 0, 0, 0]  # horizontal bar
    arr[140:350, C - 25:C + 25] = [0, 0, 0, 0]     # vertical bar
    return Image.fromarray(arr)


def draw_eye() -> Image.Image:
    """Eye — surveillance, privacy, transparency."""
    img = _new(); d = _d(img)
    # Eye shape using curved arcs for almond shape
    # Upper lid arc
    d.chord([40, C - 220, 472, C + 100], 200, 340, fill=W)
    # Lower lid arc
    d.chord([40, C - 100, 472, C + 220], 20, 160, fill=W)
    # Iris (circle)
    iris_r = 75
    d.ellipse([C - iris_r, C - iris_r, C + iris_r, C + iris_r], fill=W)
    # Pupil (cutout)
    arr = np.array(img)
    y, x = np.ogrid[:S, :S]
    pupil = ((x - C) ** 2 + (y - C) ** 2) < 32 ** 2
    arr[pupil] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_coin_stack() -> Image.Image:
    """Stack of coins — currency, banking, financial."""
    img = _new(); d = _d(img)
    # Stack of 5 coins with visible edges
    coin_h = 45
    for i, y_top in enumerate([320, 255, 190, 125, 70]):
        # Coin side (visible part between top face and next coin's top)
        d.rectangle([C - 110, y_top + 15, C + 110, y_top + coin_h], fill=W)
        # Top face ellipse
        d.ellipse([C - 110, y_top, C + 110, y_top + 35], fill=W)
    # Bottom face of lowest coin
    d.ellipse([C - 110, 320 + coin_h - 15, C + 110, 320 + coin_h + 20], fill=W)
    # Add separation lines between coins (cutout thin dark bands)
    arr = np.array(img)
    for y_top in [255, 190, 125, 70]:
        # Dark line at bottom edge of each coin (just above next one)
        arr[y_top + coin_h - 2:y_top + coin_h + 2, C - 105:C + 105] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_bank() -> Image.Image:
    """Classical bank building with columns — banking, national bank."""
    img = _new(); d = _d(img)
    # Triangular pediment
    d.polygon([(80, 180), (C, 60), (432, 180)], fill=W)
    # Entablature
    d.rectangle([80, 170, 432, 200], fill=W)
    # Four columns
    for cx in [130, 210, 302, 382]:
        d.rectangle([cx - 18, 200, cx + 18, 400], fill=W)
    # Base/steps
    d.rectangle([70, 390, 442, 420], fill=W)
    d.rectangle([60, 415, 452, 445], fill=W)
    return img


def draw_people() -> Image.Image:
    """Group of people — minority rights, protected class, demographics."""
    img = _new(); d = _d(img)
    # Three figures (head + body silhouettes)
    for cx, scale in [(C, 1.0), (C - 120, 0.85), (C + 120, 0.85)]:
        head_r = int(40 * scale)
        head_y = int(150 * scale + (1 - scale) * 60)
        # Head
        d.ellipse([cx - head_r, head_y - head_r, cx + head_r, head_y + head_r], fill=W)
        # Body (trapezoid)
        bw_top = int(45 * scale)
        bw_bot = int(80 * scale)
        body_top = head_y + head_r + 5
        body_bot = int(440 - (1 - scale) * 30)
        d.polygon([
            (cx - bw_top, body_top),
            (cx + bw_top, body_top),
            (cx + bw_bot, body_bot),
            (cx - bw_bot, body_bot),
        ], fill=W)
    return img


def draw_lightbulb() -> Image.Image:
    """Light bulb — IP, innovation, open source."""
    img = _new(); d = _d(img)
    # Bulb (circle top)
    bulb_r = 120
    bulb_cy = 190
    d.ellipse([C - bulb_r, bulb_cy - bulb_r, C + bulb_r, bulb_cy + bulb_r], fill=W)
    # Neck taper
    d.polygon([
        (C - 70, bulb_cy + 90),
        (C + 70, bulb_cy + 90),
        (C + 45, 380),
        (C - 45, 380),
    ], fill=W)
    # Screw base
    for y_pos in range(380, 435, 18):
        d.rectangle([C - 50, y_pos, C + 50, y_pos + 12], fill=W)
    # Bottom tip
    d.polygon([(C - 30, 432), (C, 460), (C + 30, 432)], fill=W)
    return img


def draw_gavel() -> Image.Image:
    """Gavel — criminal justice, legal system."""
    img = _new(); d = _d(img)
    # Gavel head (large rotated rectangle at top)
    a = math.radians(-25)
    hw, hh = 110, 40
    gcx, gcy = C + 10, 140
    corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    pts = [(gcx + x * math.cos(a) - y * math.sin(a),
            gcy + x * math.sin(a) + y * math.cos(a)) for x, y in corners]
    d.polygon(pts, fill=W)
    # Bands at ends of gavel head
    for end_sign in [-1, 1]:
        ex = gcx + end_sign * (hw - 15) * math.cos(a)
        ey = gcy + end_sign * (hw - 15) * math.sin(a)
        band_pts = []
        for bx, by in [(-20, -hh - 5), (20, -hh - 5), (20, hh + 5), (-20, hh + 5)]:
            band_pts.append((ex + bx * math.cos(a) - by * math.sin(a),
                           ey + bx * math.sin(a) + by * math.cos(a)))
        d.polygon(band_pts, fill=W)
    # Handle (thick line going down)
    d.line([(gcx - 5, gcy + 40), (C - 30, 380)], fill=W, width=28)
    # Sound block (rounded rectangle at bottom)
    d.rounded_rectangle([100, 370, 400, 430], radius=8, fill=W)
    # Sound block top bevel
    d.rectangle([110, 365, 390, 378], fill=W)
    return img


def draw_lock() -> Image.Image:
    """Padlock — privacy, data protection."""
    img = _new(); d = _d(img)
    # Lock body (rounded rectangle)
    d.rounded_rectangle([C - 110, 220, C + 110, 440], radius=15, fill=W)
    # Shackle (U-shape at top)
    d.arc([C - 80, 80, C + 80, 260], 180, 0, fill=W, width=30)
    # With proper thick shackle
    d.rectangle([C - 80, 160, C - 50, 240], fill=W)
    d.rectangle([C + 50, 160, C + 80, 240], fill=W)
    d.ellipse([C - 80, 80, C + 80, 250], outline=W)
    # Filled arc for shackle
    for r in range(65, 81):
        d.arc([C - r, 90, C + r, 90 + 2 * r], 180, 0, fill=W, width=3)
    # Keyhole cutout
    arr = np.array(img)
    y, x = np.ogrid[:S, :S]
    keyhole_circle = ((x - C) ** 2 + (y - 310) ** 2) < 22 ** 2
    arr[keyhole_circle] = [0, 0, 0, 0]
    arr[310:370, C - 8:C + 8] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_globe_lines() -> Image.Image:
    """Globe with meridians — government transparency, open government."""
    img = _new(); d = _d(img)
    r = 180
    # Main circle
    d.ellipse([C - r, C - r, C + r, C + r], fill=W)
    # Cut out meridian lines and equator for visual detail
    arr = np.array(img)
    # Horizontal lines
    for y_off in [-90, 0, 90]:
        arr[C + y_off - 3:C + y_off + 3, C - r + 15:C + r - 15] = [0, 0, 0, 0]
    # Vertical elliptical meridians (cutout)
    for x_off in [-60, 0, 60]:
        for yy in range(C - r + 20, C + r - 20):
            # Elliptical curve
            frac = (yy - C) / r
            ew = int(abs(x_off) * math.sqrt(max(0, 1 - frac * frac)))
            cx = C + x_off
            if ew > 0:
                arr[yy, cx - 2:cx + 2] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_sword_crossed() -> Image.Image:
    """Crossed swords — total war, war crimes."""
    img = _new(); d = _d(img)
    # Two diagonal swords
    for angle_offset in [-35, 35]:
        a = math.radians(angle_offset)
        # Blade
        points = []
        blade_len = 300
        blade_w = 16
        cx, cy = C, C + 20
        tip_x = cx + blade_len * math.sin(a)
        tip_y = cy - blade_len * math.cos(a)
        perp_x = blade_w * math.cos(a)
        perp_y = blade_w * math.sin(a)
        d.polygon([
            (cx - perp_x, cy - perp_y),
            (tip_x, tip_y),
            (cx + perp_x, cy + perp_y),
        ], fill=W)
        # Guard (crossbar)
        guard_len = 50
        gx = cx - 30 * math.sin(a)
        gy = cy + 30 * math.cos(a)
        d.line([
            (gx - guard_len * math.cos(a), gy - guard_len * math.sin(a)),
            (gx + guard_len * math.cos(a), gy + guard_len * math.sin(a)),
        ], fill=W, width=14)
        # Handle
        hx = cx - 80 * math.sin(a)
        hy = cy + 80 * math.cos(a)
        d.line([(gx, gy), (hx, hy)], fill=W, width=20)
    return img


def draw_family() -> Image.Image:
    """Family (adult + child figures) — family policy, natalism."""
    img = _new(); d = _d(img)
    # Left adult figure
    acx = C - 90
    d.ellipse([acx - 35, 80, acx + 35, 150], fill=W)
    d.polygon([(acx - 50, 160), (acx + 50, 160),
               (acx + 70, 440), (acx - 70, 440)], fill=W)
    # Right adult figure
    acx2 = C + 90
    d.ellipse([acx2 - 35, 80, acx2 + 35, 150], fill=W)
    d.polygon([(acx2 - 50, 160), (acx2 + 50, 160),
               (acx2 + 70, 440), (acx2 - 70, 440)], fill=W)
    # Child figure (center, clearly visible)
    ccx = C
    d.ellipse([ccx - 28, 180, ccx + 28, 236], fill=W)
    d.polygon([(ccx - 38, 244), (ccx + 38, 244),
               (ccx + 55, 440), (ccx - 55, 440)], fill=W)
    return img


def draw_dna() -> Image.Image:
    """DNA helix — genetics, eugenics, heredity."""
    img = _new(); d = _d(img)
    # Double helix drawn as two sinusoidal curves with cross-rungs
    n = 200
    amplitude = 90
    for strand in [0, 1]:
        phase = strand * math.pi
        pts = []
        for i in range(n):
            t = i / (n - 1)
            y = 60 + t * 392
            x = C + amplitude * math.sin(2 * math.pi * 2.5 * t + phase)
            pts.append((x, y))
        # Draw as thick connected lines
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=W, width=22)
    # Cross-rungs
    for i in range(8):
        t = (i + 0.5) / 8
        y = int(60 + t * 392)
        x1 = C + amplitude * math.sin(2 * math.pi * 2.5 * t)
        x2 = C + amplitude * math.sin(2 * math.pi * 2.5 * t + math.pi)
        d.line([(x1, y), (x2, y)], fill=W, width=10)
    return img


def draw_circuit_board() -> Image.Image:
    """Circuit board pattern — internet, digital policy, algorithmic governance."""
    img = _new(); d = _d(img)
    # Central processor
    d.rectangle([C - 60, C - 60, C + 60, C + 60], fill=W)
    # Circuit traces radiating out
    traces = [
        # Horizontal
        [(C + 60, C - 30), (C + 160, C - 30), (C + 160, C - 80), (C + 200, C - 80)],
        [(C + 60, C + 30), (C + 140, C + 30), (C + 140, C + 100), (C + 200, C + 100)],
        [(C - 60, C - 30), (C - 160, C - 30), (C - 160, C - 80), (C - 200, C - 80)],
        [(C - 60, C + 30), (C - 140, C + 30), (C - 140, C + 100), (C - 200, C + 100)],
        # Vertical
        [(C - 30, C - 60), (C - 30, C - 140), (C - 80, C - 140), (C - 80, C - 200)],
        [(C + 30, C - 60), (C + 30, C - 140), (C + 80, C - 140), (C + 80, C - 200)],
        [(C - 30, C + 60), (C - 30, C + 140), (C - 80, C + 140), (C - 80, C + 200)],
        [(C + 30, C + 60), (C + 30, C + 140), (C + 80, C + 140), (C + 80, C + 200)],
    ]
    for trace in traces:
        d.line(trace, fill=W, width=12)
    # Nodes at endpoints
    for trace in traces:
        ex, ey = trace[-1]
        d.ellipse([ex - 12, ey - 12, ex + 12, ey + 12], fill=W)
    return img


def draw_pillar() -> Image.Image:
    """Classical column/pillar — government structure, federalism, constitutional."""
    img = _new(); d = _d(img)
    # Capital
    d.rectangle([C - 90, 70, C + 90, 100], fill=W)
    d.polygon([(C - 70, 100), (C - 55, 115), (C + 55, 115), (C + 70, 100)], fill=W)
    # Shaft with fluting
    d.rectangle([C - 55, 115, C + 55, 400], fill=W)
    # Flutes (cutout lines)
    arr = np.array(img)
    for x_off in [-35, -15, 5, 25]:
        arr[130:390, C + x_off:C + x_off + 5] = [0, 0, 0, 0]
    img = Image.fromarray(arr)
    d = _d(img)
    # Base
    d.rectangle([C - 75, 395, C + 75, 415], fill=W)
    d.rectangle([C - 90, 410, C + 90, 440], fill=W)
    return img


def draw_ballot_box() -> Image.Image:
    """Ballot box — campaign finance, elections, direct democracy."""
    img = _new(); d = _d(img)
    # Box body
    d.rounded_rectangle([100, 220, 412, 445], radius=10, fill=W)
    # Lid (slightly wider)
    d.rounded_rectangle([90, 195, 422, 230], radius=6, fill=W)
    # Ballot paper sticking out of slot (envelope shape)
    d.polygon([
        (C - 55, 200),
        (C - 50, 80),
        (C, 55),
        (C + 50, 80),
        (C + 55, 200),
    ], fill=W)
    # Slot cutout
    arr = np.array(img)
    arr[205:215, C - 50:C + 50] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_building_ministry() -> Image.Image:
    """Government building — ministries."""
    img = _new(); d = _d(img)
    # Central dome
    d.ellipse([C - 80, 60, C + 80, 180], fill=W)
    # Main body
    d.rectangle([100, 150, 412, 400], fill=W)
    # Door
    d.arc([C - 40, 320, C + 40, 410], 180, 0, fill=W, width=60)
    d.chord([C - 40, 320, C + 40, 410], 180, 0, fill=W)
    # Window columns
    for wx in [140, 200, 312, 372]:
        d.rectangle([wx - 12, 200, wx + 12, 280], fill=W)
    # Base
    d.rectangle([85, 395, 427, 420], fill=W)
    d.rectangle([75, 415, 437, 445], fill=W)
    # Flagpole
    d.rectangle([C - 3, 30, C + 3, 65], fill=W)
    d.rectangle([C + 3, 30, C + 30, 50], fill=W)
    # Cut out door
    arr = np.array(img)
    y, x = np.ogrid[:S, :S]
    door_mask = ((x - C) ** 2 / 35 ** 2 + (y - 370) ** 2 / 30 ** 2) < 1
    door_mask &= (y > 360)
    arr[door_mask] = [0, 0, 0, 0]
    arr[360:400, C - 30:C + 30] = [0, 0, 0, 0]
    # Cut out windows
    for wx in [140, 200, 312, 372]:
        arr[210:270, wx - 8:wx + 8] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_no_building() -> Image.Image:
    """Crossed-out building — no ministry."""
    img = draw_building_ministry()
    d = _d(img)
    # Red circle-slash (drawn as white on the silhouette)
    r = 210
    d.arc([C - r, C - r, C + r, C + r], 0, 360, fill=W, width=20)
    # Diagonal slash
    a = math.radians(-45)
    d.line([
        (C + r * math.cos(a), C + r * math.sin(a)),
        (C - r * math.cos(a), C - r * math.sin(a)),
    ], fill=W, width=20)
    return img


def draw_speech_bubble() -> Image.Image:
    """Speech bubble — language policy."""
    img = _new(); d = _d(img)
    # Main bubble (rounded rectangle)
    d.rounded_rectangle([80, 80, 432, 340], radius=50, fill=W)
    # Tail/pointer
    d.polygon([(150, 330), (200, 340), (130, 440)], fill=W)
    # Text lines (cutout)
    arr = np.array(img)
    for y_pos in range(150, 300, 40):
        arr[y_pos:y_pos + 10, 140:380] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_handshake() -> Image.Image:
    """Handshake — trust busting, freedom of contract, economic regulation."""
    img = _new(); d = _d(img)
    # Two arms coming from bottom-left and bottom-right, clasping in center
    # Left arm (from bottom-left to center)
    d.polygon([
        (40, 440),   # bottom-left cuff bottom
        (40, 340),   # bottom-left cuff top
        (130, 250),  # forearm
        (200, 200),  # wrist
        (270, 190),  # hand top
        (310, 220),  # fingertips right
        (280, 270),  # hand bottom
        (200, 290),  # wrist bottom
        (130, 350),  # forearm bottom
    ], fill=W)
    # Right arm (from bottom-right to center)
    d.polygon([
        (472, 440),  # bottom-right cuff bottom
        (472, 340),  # bottom-right cuff top
        (382, 250),  # forearm
        (312, 200),  # wrist
        (242, 190),  # hand top
        (202, 220),  # fingertips left
        (232, 270),  # hand bottom
        (312, 290),  # wrist bottom
        (382, 350),  # forearm bottom
    ], fill=W)
    # Clasp area (merged center)
    d.ellipse([215, 175, 297, 260], fill=W)
    # Left thumb bump
    d.ellipse([285, 175, 330, 215], fill=W)
    # Right thumb bump
    d.ellipse([182, 175, 227, 215], fill=W)
    return img


def draw_gear_law() -> Image.Image:
    """Gear with wrench — economic systems, regulated utilities."""
    img = _new(); d = _d(img)
    # Large gear
    r_body = 140
    d.ellipse([C - r_body, C - r_body, C + r_body, C + r_body], fill=W)
    # Teeth
    for i in range(10):
        a = 2 * math.pi * i / 10
        tcx = C + 160 * math.cos(a)
        tcy = C + 160 * math.sin(a)
        hw, hh = 22, 26
        ca, sa = math.cos(a), math.sin(a)
        corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        pts = [(tcx + x * ca - y * sa, tcy + x * sa + y * ca) for x, y in corners]
        d.polygon(pts, fill=W)
    # Center hole
    arr = np.array(img)
    y, x = np.ogrid[:S, :S]
    arr[((x - C) ** 2 + (y - C) ** 2) < 45 ** 2] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_robot_head() -> Image.Image:
    """Robot head — augmentation, transhumanism."""
    img = _new(); d = _d(img)
    # Head shape (rounded rectangle)
    d.rounded_rectangle([C - 110, 80, C + 110, 340], radius=40, fill=W)
    # Neck
    d.rectangle([C - 50, 330, C + 50, 420], fill=W)
    # Shoulder bar
    d.rectangle([C - 130, 410, C + 130, 450], fill=W)
    # Eyes (cutout)
    arr = np.array(img)
    # Left eye
    arr[170:220, C - 70:C - 20] = [0, 0, 0, 0]
    # Right eye
    arr[170:220, C + 20:C + 70] = [0, 0, 0, 0]
    # Mouth (horizontal line)
    arr[265:285, C - 60:C + 60] = [0, 0, 0, 0]
    # Antenna
    img = Image.fromarray(arr)
    d = _d(img)
    d.rectangle([C - 4, 40, C + 4, 85], fill=W)
    d.ellipse([C - 14, 25, C + 14, 55], fill=W)
    return img


def draw_wifi() -> Image.Image:
    """WiFi/signal symbol — internet policy, net neutrality."""
    img = _new(); d = _d(img)
    # Concentric arcs
    for r, width in [(180, 30), (130, 28), (80, 26)]:
        d.arc([C - r, C - r + 60, C + r, C + r + 60], 225, 315, fill=W, width=width)
    # Center dot
    d.ellipse([C - 22, C + 38, C + 22, C + 82], fill=W)
    return img


def draw_crown() -> Image.Image:
    """Crown — neocameralism, feudal."""
    img = _new(); d = _d(img)
    # Crown base
    d.rectangle([110, 280, 402, 380], fill=W)
    # Crown rim (decorative band)
    d.rectangle([100, 370, 412, 410], fill=W)
    # Crown points
    d.polygon([
        (110, 280),
        (110, 130),
        (170, 220),
        (C, 100),
        (342, 220),
        (402, 130),
        (402, 280),
    ], fill=W)
    # Jewels (cutout circles)
    arr = np.array(img)
    y, x = np.ogrid[:S, :S]
    for jx, jy in [(C, 310), (C - 80, 310), (C + 80, 310)]:
        arr[((x - jx) ** 2 + (y - jy) ** 2) < 15 ** 2] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_chains() -> Image.Image:
    """Broken chains — active persecution, oppression."""
    img = _new(); d = _d(img)
    # Left chain links
    for y_pos in [120, 200, 280]:
        # Vertical oval link
        d.ellipse([C - 160, y_pos, C - 80, y_pos + 90], outline=W, width=20)
    # Right chain links (offset, broken away)
    for y_pos in [140, 220, 300]:
        d.ellipse([C + 80, y_pos, C + 160, y_pos + 90], outline=W, width=20)
    # Break marks (jagged)
    d.polygon([
        (C - 30, 200),
        (C - 10, 230),
        (C + 10, 210),
        (C + 30, 250),
        (C + 10, 260),
        (C - 10, 240),
        (C - 30, 270),
    ], fill=W)
    return img


def draw_umbrella() -> Image.Image:
    """Umbrella — social protection, welfare."""
    img = _new(); d = _d(img)
    # Canopy (half-circle)
    d.chord([80, 60, 432, 360], 180, 0, fill=W)
    # Scalloped edge
    for cx in [130, 200, 270, 340, 400]:
        d.chord([cx - 50, 240, cx + 50, 360], 0, 180, fill=(0, 0, 0, 0))
    # Handle
    d.rectangle([C - 6, 200, C + 6, 410], fill=W)
    # Curved handle bottom
    d.arc([C - 30, 390, C + 30, 450], 0, 180, fill=W, width=12)
    return img


def draw_atom_law() -> Image.Image:
    """Atom — nuclear, science-based laws."""
    img = _new(); d = _d(img)
    # Central nucleus
    d.ellipse([C - 45, C - 45, C + 45, C + 45], fill=W)
    # Three orbital ellipses
    for angle_deg in [0, 60, 120]:
        a = math.radians(angle_deg)
        rx, ry = 185, 60
        n = 80
        for i in range(n):
            t1 = 2 * math.pi * i / n
            t2 = 2 * math.pi * (i + 1) / n
            x1 = C + (rx * math.cos(t1) * math.cos(a) - ry * math.sin(t1) * math.sin(a))
            y1 = C + (rx * math.cos(t1) * math.sin(a) + ry * math.sin(t1) * math.cos(a))
            x2 = C + (rx * math.cos(t2) * math.cos(a) - ry * math.sin(t2) * math.sin(a))
            y2 = C + (rx * math.cos(t2) * math.sin(a) + ry * math.sin(t2) * math.cos(a))
            d.line([(x1, y1), (x2, y2)], fill=W, width=20)
    return img


def draw_dove() -> Image.Image:
    """Dove/peace — humanitarian regulations, limited war."""
    img = _new(); d = _d(img)
    # Body (oval)
    d.ellipse([C - 80, C - 30, C + 80, C + 80], fill=W)
    # Head (circle, upper right)
    d.ellipse([C + 30, C - 90, C + 120, C], fill=W)
    # Beak
    d.polygon([(C + 120, C - 50), (C + 170, C - 40), (C + 120, C - 30)], fill=W)
    # Wing (swept up)
    d.polygon([
        (C - 40, C),
        (C - 180, C - 120),
        (C - 100, C - 50),
        (C - 160, C - 180),
        (C - 30, C - 60),
        (C + 20, C - 30),
    ], fill=W)
    # Tail
    d.polygon([
        (C - 80, C + 20),
        (C - 180, C - 20),
        (C - 160, C + 30),
        (C - 80, C + 50),
    ], fill=W)
    # Olive branch (simple)
    d.line([(C + 140, C - 20), (C + 100, C + 40)], fill=W, width=6)
    d.ellipse([C + 130, C - 10, C + 160, C + 10], fill=W)
    return img


# ═══════════════════════════════════════════════════════════════════════════
# BESPOKE PER-LAW SHAPE VARIANTS
# Each variant shares thematic DNA with its base shape (so a banking law still
# reads as banking) but adds a distinguishing element so laws within the same
# law group render visually distinct icons. Pattern: call the base draw
# function, draw the differentiator on top, return.
# ═══════════════════════════════════════════════════════════════════════════

# ── Banking / financial regulation ───────────────────────────────────────
def draw_bank_open() -> Image.Image:
    """Bank without pediment — free mutual / open banking."""
    img = _new(); d = _d(img)
    # Entablature only (no triangular pediment)
    d.rectangle([80, 130, 432, 170], fill=W)
    # Four columns
    for cx in [130, 210, 302, 382]:
        d.rectangle([cx - 18, 170, cx + 18, 400], fill=W)
    # Base/steps
    d.rectangle([70, 390, 442, 420], fill=W)
    d.rectangle([60, 415, 452, 445], fill=W)
    return img


def draw_bank_columns_paired() -> Image.Image:
    """Bank with paired columns — universal banking."""
    img = _new(); d = _d(img)
    d.polygon([(80, 180), (C, 60), (432, 180)], fill=W)
    d.rectangle([80, 170, 432, 200], fill=W)
    # Two pairs of columns (coupled)
    for cx in [140, 180, 324, 364]:
        d.rectangle([cx - 16, 200, cx + 16, 400], fill=W)
    d.rectangle([70, 390, 442, 420], fill=W)
    d.rectangle([60, 415, 452, 445], fill=W)
    return img


def draw_bank_narrow() -> Image.Image:
    """Bank with single tall column — prudential narrow banking."""
    img = _new(); d = _d(img)
    d.polygon([(150, 180), (C, 60), (362, 180)], fill=W)
    d.rectangle([150, 170, 362, 200], fill=W)
    # Single thick central column
    d.rectangle([C - 40, 200, C + 40, 400], fill=W)
    d.rectangle([100, 390, 412, 420], fill=W)
    d.rectangle([85, 415, 427, 445], fill=W)
    return img


def draw_bank_arrow_up() -> Image.Image:
    """Bank with upward arrow rising above the pediment.

    The arrow head extends well above the pediment apex (y≈60) so its
    silhouette is unambiguous; the shaft inside the pediment is cut as a
    transparent slot so it embosses as a visible groove rather than vanishing
    into the white pediment fill.
    """
    img = draw_bank()
    d = _d(img)
    # Arrow head clearly above the pediment
    d.polygon([(C, 0), (C - 60, 65), (C - 22, 65),
               (C - 22, 100), (C + 22, 100), (C + 22, 65),
               (C + 60, 65)], fill=W)
    # Shaft cutout through the pediment
    arr = np.array(img)
    arr[100:170, C - 14:C + 14] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_bank_shield() -> Image.Image:
    """Bank with shield in front — central bank independence."""
    img = draw_bank()
    d = _d(img)
    # Shield silhouette in front of columns
    pts = [(C, 220), (C + 70, 240), (C + 65, 360),
           (C, 410), (C - 65, 360), (C - 70, 240)]
    d.polygon(pts, fill=W)
    # Border ring (cutout) so the shield reads as separate from the bank body
    arr = np.array(img)
    y, x = np.ogrid[:S, :S]
    inner = (((x - C) / 50) ** 2 + ((y - 320) / 70) ** 2) < 1
    arr[inner] = [0, 0, 0, 0]
    return Image.fromarray(arr)


# ── Human augmentation ───────────────────────────────────────────────────
def draw_robot_head_purity() -> Image.Image:
    """Robot head with bar across — human purity (rejection of augmentation)."""
    img = draw_robot_head()
    d = _d(img)
    # Diagonal bar across head signaling rejection
    a = math.radians(-30)
    cx, cy = C, 210
    half = 150
    perp = 18
    pts = [
        (cx - half * math.cos(a) - perp * math.sin(a),
         cy - half * math.sin(a) + perp * math.cos(a)),
        (cx + half * math.cos(a) - perp * math.sin(a),
         cy + half * math.sin(a) + perp * math.cos(a)),
        (cx + half * math.cos(a) + perp * math.sin(a),
         cy + half * math.sin(a) - perp * math.cos(a)),
        (cx - half * math.cos(a) + perp * math.sin(a),
         cy - half * math.sin(a) - perp * math.cos(a)),
    ]
    d.polygon(pts, fill=W)
    return img


def draw_robot_head_medical() -> Image.Image:
    """Robot head with medical-cross cutout on forehead — medical augmentation only.

    The cross is rendered as a TRANSPARENT cutout (not white fill) so the
    metallic styling can read its inner edges as embossed detail; a
    white-on-white overlay would visually merge into the head silhouette.
    """
    img = draw_robot_head()
    arr = np.array(img)
    # Cut a circular badge area on the forehead (transparent disc)
    y, x = np.ogrid[:S, :S]
    badge_mask = ((x - C) ** 2 + (y - 130) ** 2) < 38 ** 2
    arr[badge_mask] = [0, 0, 0, 0]
    img = Image.fromarray(arr)
    d = _d(img)
    # Now draw the medical plus inside the cleared disc — the white pixels
    # have visible boundaries against the transparent ring around them.
    d.rectangle([C - 22, 122, C + 22, 138], fill=W)
    d.rectangle([C - 8, 105, C + 8, 156], fill=W)
    return img


def draw_robot_head_regulated() -> Image.Image:
    """Robot head inside a frame — regulated augmentation market."""
    img = draw_robot_head()
    d = _d(img)
    # Frame around the head
    for off in range(0, 14, 4):
        d.rectangle([C - 130 - off, 60 - off, C + 130 + off, 360 + off],
                    outline=W, width=4)
    return img


def draw_robot_head_mandatory() -> Image.Image:
    """Robot head with extra antennae — mandatory augmentation (state-driven)."""
    img = draw_robot_head()
    d = _d(img)
    # Extra side antennae
    d.rectangle([C - 90, 50, C - 82, 90], fill=W)
    d.ellipse([C - 100, 30, C - 72, 60], fill=W)
    d.rectangle([C + 82, 50, C + 90, 90], fill=W)
    d.ellipse([C + 72, 30, C + 100, 60], fill=W)
    # Rivet rows on shoulder bar to signal industrial/forced
    arr = np.array(img)
    for rx in [C - 95, C - 50, C, C + 50, C + 95]:
        arr[420:432, rx - 5:rx + 5] = [0, 0, 0, 0]
    return Image.fromarray(arr)


# ── Language policy ──────────────────────────────────────────────────────
def draw_speech_bubble_pair() -> Image.Image:
    """Two overlapping speech bubbles — multilingual federalism."""
    img = _new(); d = _d(img)
    # Back bubble
    d.rounded_rectangle([40, 60, 360, 300], radius=45, fill=W)
    d.polygon([(110, 290), (160, 300), (90, 380)], fill=W)
    # Erase a clean gap so the front bubble reads as separate
    arr = np.array(img)
    cutout_img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cutout_img)
    cd.rounded_rectangle([170, 180, 480, 420], radius=45, fill=(255, 0, 0, 255))
    cutout_arr = np.array(cutout_img)
    border_mask = (cutout_arr[..., 3] > 0)
    # Subtract a 12px border around the front bubble from the back bubble
    from PIL import ImageFilter
    cutout_filled = cutout_img.filter(ImageFilter.MaxFilter(13))
    cutout_arr2 = np.array(cutout_filled)
    arr[(cutout_arr2[..., 3] > 0) & (border_mask == False)] = [0, 0, 0, 0]
    img = Image.fromarray(arr)
    d = _d(img)
    # Front bubble
    d.rounded_rectangle([170, 180, 480, 420], radius=45, fill=W)
    d.polygon([(380, 405), (440, 415), (470, 460)], fill=W)
    return img


def draw_speech_bubble_pure() -> Image.Image:
    """Speech bubble with thick clean border, no text — linguistic purity."""
    img = _new(); d = _d(img)
    # Outer rounded border
    d.rounded_rectangle([60, 70, 452, 350], radius=55, fill=W)
    # Inner cutout (creates a thick ring)
    arr = np.array(img)
    inner_img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    inner_d = ImageDraw.Draw(inner_img)
    inner_d.rounded_rectangle([90, 100, 422, 320], radius=40, fill=(255, 0, 0, 255))
    inner_arr = np.array(inner_img)
    arr[inner_arr[..., 3] > 0] = [0, 0, 0, 0]
    img = Image.fromarray(arr)
    d = _d(img)
    # Tail
    d.polygon([(150, 340), (200, 350), (130, 450)], fill=W)
    # Single uppercase "I" inside (purity / single language)
    d.rectangle([C - 14, 145, C + 14, 275], fill=W)
    d.rectangle([C - 50, 140, C + 50, 158], fill=W)
    d.rectangle([C - 50, 262, C + 50, 280], fill=W)
    return img


def draw_speech_bubble_hammer() -> Image.Image:
    """Speech bubble over a hammer — state-led language reform."""
    img = _new(); d = _d(img)
    # Bubble (smaller, top half)
    d.rounded_rectangle([90, 50, 422, 250], radius=45, fill=W)
    d.polygon([(150, 240), (200, 250), (130, 320)], fill=W)
    # Hammer below
    # Hammer head
    d.rectangle([C - 100, 320, C + 100, 380], fill=W)
    d.polygon([(C + 100, 320), (C + 140, 340),
               (C + 140, 360), (C + 100, 380)], fill=W)
    # Handle
    d.rectangle([C - 12, 380, C + 12, 460], fill=W)
    return img


def draw_speech_bubble_globe() -> Image.Image:
    """Speech bubble with globe lines — ubiquitous translation."""
    img = _new(); d = _d(img)
    d.rounded_rectangle([80, 80, 432, 340], radius=50, fill=W)
    d.polygon([(150, 330), (200, 340), (130, 440)], fill=W)
    # Global meridian curves (cutout)
    arr = np.array(img)
    # Equator
    arr[210 - 4:210 + 4, 110:402] = [0, 0, 0, 0]
    # Vertical meridian curves
    for x_off in [-90, 0, 90]:
        for yy in range(110, 320):
            frac = (yy - 210) / 130
            ew = int(abs(x_off) * math.sqrt(max(0, 1 - frac * frac))) if x_off else 0
            cx = C + x_off
            if x_off == 0 or ew > 0:
                arr[yy, cx - 3:cx + 3] = [0, 0, 0, 0]
    return Image.fromarray(arr)


# ── Intellectual property ────────────────────────────────────────────────
def draw_lightbulb_open() -> Image.Image:
    """Lightbulb with open ring above — creative commons."""
    img = draw_lightbulb()
    d = _d(img)
    # Open ring/halo above bulb
    d.arc([C - 75, 30, C + 75, 110], 0, 360, fill=W, width=14)
    # Break in ring
    arr = np.array(img)
    arr[60:80, C - 18:C + 18] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_lightbulb_locked() -> Image.Image:
    """Lightbulb with a padlock cutout on the bulb — strict IP."""
    img = draw_lightbulb()
    arr = np.array(img)
    # Cut a padlock-shaped transparent area on the bulb body so the lock
    # reads as embossed detail rather than merging into the silhouette.
    # Lock body cutout
    arr[200:280, C - 45:C + 45] = [0, 0, 0, 0]
    # Shackle cutout (thin arc)
    y, x = np.ogrid[:S, :S]
    outer = ((x - C) ** 2 + (y - 200) ** 2) < 38 ** 2
    inner = ((x - C) ** 2 + (y - 200) ** 2) < 26 ** 2
    arr[outer & ~inner & (y < 215)] = [0, 0, 0, 0]
    img = Image.fromarray(arr)
    d = _d(img)
    # Now redraw the lock as solid shapes within the cleared zone
    d.rounded_rectangle([C - 38, 210, C + 38, 272], radius=7, fill=W)
    # Shackle
    d.arc([C - 28, 175, C + 28, 230], 180, 0, fill=W, width=10)
    return img


def draw_lightbulb_branched() -> Image.Image:
    """Lightbulb with branching filaments — open source innovation."""
    img = draw_lightbulb()
    d = _d(img)
    # Branching lines radiating from center inside bulb (cutouts)
    arr = np.array(img)
    cx, cy = C, 190
    for angle_deg in [0, 60, 120, 180, 240, 300]:
        a = math.radians(angle_deg)
        for r in range(20, 95):
            x = int(cx + r * math.cos(a))
            y = int(cy + r * math.sin(a))
            if 0 <= x < S and 0 <= y < S:
                arr[y - 3:y + 4, x - 3:x + 4] = [0, 0, 0, 0]
    return Image.fromarray(arr)


# ── Genetics ─────────────────────────────────────────────────────────────
def draw_dna_corporate() -> Image.Image:
    """DNA helix inside a frame — corporate genetic licensing."""
    img = draw_dna()
    d = _d(img)
    # Rectangular frame
    for off in range(0, 14, 4):
        d.rectangle([100 - off, 50 - off, 412 + off, 460 + off],
                    outline=W, width=4)
    return img


def draw_dna_open() -> Image.Image:
    """DNA helix with branching arrows — open source genetics."""
    img = draw_dna()
    d = _d(img)
    # Two outward arrows at right side
    for ax_y in [180, 330]:
        d.polygon([(420, ax_y), (470, ax_y - 30),
                   (450, ax_y), (470, ax_y + 30)], fill=W)
    # Two outward arrows at left side
    for ax_y in [180, 330]:
        d.polygon([(92, ax_y), (42, ax_y - 30),
                   (62, ax_y), (42, ax_y + 30)], fill=W)
    return img


def draw_dna_state() -> Image.Image:
    """DNA helix with banner/star — state eugenics program."""
    img = draw_dna()
    d = _d(img)
    # Star above
    pts = []
    cx, cy, r = C, 65, 40
    for i in range(10):
        rr = r if i % 2 == 0 else r // 2
        a = math.pi / 2 + math.pi * i / 5
        pts.append((cx + rr * math.cos(a), cy - rr * math.sin(a)))
    d.polygon(pts, fill=W)
    return img


# ── Family ───────────────────────────────────────────────────────────────
def draw_family_natal() -> Image.Image:
    """Family with upward arrow — pro-natalist."""
    img = draw_family()
    d = _d(img)
    # Up-arrow on the right side
    d.polygon([(440, 200), (410, 250), (425, 250),
               (425, 380), (455, 380),
               (455, 250), (470, 250)], fill=W)
    return img


def draw_family_planned() -> Image.Image:
    """Family with calendar grid — state-sponsored family planning."""
    img = draw_family()
    d = _d(img)
    # Calendar/grid overlay in upper-right
    grid_left, grid_top = 360, 60
    grid_right, grid_bot = 470, 170
    d.rectangle([grid_left, grid_top, grid_right, grid_bot], outline=W, width=6)
    # Grid lines
    arr = np.array(img)
    for x in [grid_left + 27, grid_left + 55, grid_left + 82]:
        arr[grid_top + 6:grid_bot - 6, x - 2:x + 2] = arr[grid_top + 6:grid_bot - 6, grid_left + 1:grid_left + 5]
    # Use draw lines instead — simpler:
    img = Image.fromarray(arr)
    d = _d(img)
    for x in [grid_left + 27, grid_left + 55, grid_left + 82]:
        d.line([(x, grid_top + 6), (x, grid_bot - 6)], fill=W, width=4)
    for y in [grid_top + 27, grid_top + 55, grid_top + 82]:
        d.line([(grid_left + 6, y), (grid_right - 6, y)], fill=W, width=4)
    return img


def draw_family_controlled() -> Image.Image:
    """Family with downward arrow — population control."""
    img = draw_family()
    d = _d(img)
    # Down-arrow on the right side
    d.polygon([(425, 200), (425, 320), (410, 320),
               (440, 380), (470, 320), (455, 320),
               (455, 200)], fill=W)
    return img


# ── Inheritance ──────────────────────────────────────────────────────────
def draw_scroll_split() -> Image.Image:
    """Scroll torn into pieces — partible inheritance."""
    img = _new(); d = _d(img)
    # Left half of scroll
    d.rectangle([130, 100, 240, 420], fill=W)
    d.ellipse([110, 70, 260, 140], fill=W)
    d.ellipse([110, 390, 260, 460], fill=W)
    # Right half of scroll, slightly offset
    d.rectangle([280, 100, 390, 420], fill=W)
    d.ellipse([260, 70, 410, 140], fill=W)
    d.ellipse([260, 390, 410, 460], fill=W)
    # Jagged tear line cuts both halves where they meet
    arr = np.array(img)
    arr[160:380, 240:280] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_scroll_equal() -> Image.Image:
    """Scroll with three equal seal-circle CUTOUTS — equal inheritance.

    The cutouts read as three identical signatures/seals on the parchment,
    visually communicating equal division — and they're transparent so the
    metallic styling embosses each one as a distinct circular recess.
    """
    img = draw_scroll()
    arr = np.array(img)
    y, x = np.ogrid[:S, :S]
    for cx in [C - 90, C, C + 90]:
        mask = ((x - cx) ** 2 + (y - 350) ** 2) < 22 ** 2
        arr[mask] = [0, 0, 0, 0]
    return Image.fromarray(arr)


# ── Monetary policy ──────────────────────────────────────────────────────
def draw_coin_stack_paper() -> Image.Image:
    """Paper note above a small coin stack — fiat currency.

    The note sits ABOVE the coins (no overlap), so neither silhouette
    swallows the other. A horizontal denomination band CUTOUT and a wide
    rectangular outline make the note visually distinct from a plain coin.
    """
    img = _new(); d = _d(img)
    # Paper note (top half), tilted slightly
    note_pts = [(50, 50), (430, 30), (440, 200), (60, 230)]
    d.polygon(note_pts, fill=W)
    # Inner outline cutout (so the note reads as a banknote, not a tile)
    arr = np.array(img)
    inner_img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    inner_d = ImageDraw.Draw(inner_img)
    inner_d.polygon([(85, 75), (405, 60), (415, 175), (95, 200)],
                    fill=(255, 0, 0, 255))
    inner_arr = np.array(inner_img)
    arr[inner_arr[..., 3] > 0] = [0, 0, 0, 0]
    img = Image.fromarray(arr)
    d = _d(img)
    # Re-fill the inner area but leave a "$" stripe cutout
    d.polygon([(85, 75), (405, 60), (415, 175), (95, 200)], fill=W)
    arr = np.array(img)
    arr[110:140, 130:370] = [0, 0, 0, 0]  # denomination band
    img = Image.fromarray(arr)
    d = _d(img)
    # Coin stack in lower half (no overlap with note)
    coin_h = 40
    for y_top in [380, 330, 280]:
        d.rectangle([C - 90, y_top + 12, C + 90, y_top + coin_h], fill=W)
        d.ellipse([C - 90, y_top, C + 90, y_top + 30], fill=W)
    d.ellipse([C - 90, 380 + coin_h - 15, C + 90, 380 + coin_h + 18], fill=W)
    return img


def draw_coin_stack_digital() -> Image.Image:
    """Coin stack with circuit traces — digital currency."""
    img = draw_coin_stack()
    d = _d(img)
    # Circuit traces flanking the stack
    for side in [-1, 1]:
        bx = C + side * 180
        d.line([(bx, 100), (bx, 400)], fill=W, width=10)
        for ty in [140, 220, 300, 380]:
            inner_x = C + side * 130
            d.line([(bx, ty), (inner_x, ty)], fill=W, width=10)
            d.ellipse([inner_x - 12, ty - 12, inner_x + 12, ty + 12], fill=W)
    return img


# ── State power ──────────────────────────────────────────────────────────
def draw_pillar_three() -> Image.Image:
    """Three side-by-side pillars — federal system."""
    img = _new(); d = _d(img)
    for cx in [C - 130, C, C + 130]:
        # Capital
        d.rectangle([cx - 50, 130, cx + 50, 155], fill=W)
        d.polygon([(cx - 38, 155), (cx - 28, 168), (cx + 28, 168), (cx + 38, 155)], fill=W)
        # Shaft
        d.rectangle([cx - 28, 168, cx + 28, 380], fill=W)
        # Base
        d.rectangle([cx - 40, 378, cx + 40, 395], fill=W)
        d.rectangle([cx - 50, 393, cx + 50, 415], fill=W)
    # Common platform
    d.rectangle([60, 415, 452, 445], fill=W)
    return img


def draw_pillar_branched() -> Image.Image:
    """Pillars cascading down in size — devolution (delegated power)."""
    img = _new(); d = _d(img)
    # Big central pillar
    cx = C
    d.rectangle([cx - 50, 80, cx + 50, 105], fill=W)
    d.polygon([(cx - 38, 105), (cx - 28, 118), (cx + 28, 118), (cx + 38, 105)], fill=W)
    d.rectangle([cx - 30, 118, cx + 30, 280], fill=W)
    d.rectangle([cx - 45, 278, cx + 45, 300], fill=W)
    # Two cascaded smaller pillars
    for sx in [C - 130, C + 130]:
        d.rectangle([sx - 32, 230, sx + 32, 250], fill=W)
        d.rectangle([sx - 18, 250, sx + 18, 380], fill=W)
        d.rectangle([sx - 30, 378, sx + 30, 395], fill=W)
    # Connecting bar from main to children
    d.rectangle([C - 145, 280, C + 145, 296], fill=W)
    # Common platform
    d.rectangle([60, 415, 452, 445], fill=W)
    return img


# ── Electoral finance ────────────────────────────────────────────────────
def draw_ballot_box_capped() -> Image.Image:
    """Ballot box with banded cap and lock cutout — donation limits."""
    img = draw_ballot_box()
    arr = np.array(img)
    # Cut a horizontal band across the upper section of the box body — reads
    # as a reinforced cap line and produces visible embossed detail.
    arr[245:265, 110:402] = [0, 0, 0, 0]
    # Cut a small lock cutout on the box body just below the band
    arr[280:340, C - 26:C + 26] = [0, 0, 0, 0]
    img = Image.fromarray(arr)
    d = _d(img)
    # Re-draw a small lock body inside the cutout so it embosses cleanly.
    d.rounded_rectangle([C - 22, 290, C + 22, 332], radius=5, fill=W)
    # Shackle
    d.arc([C - 14, 274, C + 14, 304], 180, 0, fill=W, width=6)
    return img


def draw_ballot_box_public() -> Image.Image:
    """Ballot box raised on a colonnaded plinth — publicly funded elections.

    The plinth EXTENDS BELOW the existing box base into otherwise transparent
    canvas, giving the silhouette a unique outline. A star CUTOUT on the box
    body adds further differentiation without merging into the silhouette.
    """
    img = draw_ballot_box()
    d = _d(img)
    # Wide entablature underneath the existing box
    d.rectangle([50, 450, 462, 472], fill=W)
    # Three columns extending below the entablature (visible against the
    # transparent background since they sit beyond the existing silhouette).
    for cx in [100, 256, 412]:
        d.rectangle([cx - 16, 472, cx + 16, 500], fill=W)
    # Star cutout on the box body
    pts = []
    sx, sy, r = C, 360, 32
    for i in range(10):
        rr = r if i % 2 == 0 else r // 2
        a = math.pi / 2 + math.pi * i / 5
        pts.append((sx + rr * math.cos(a), sy - rr * math.sin(a)))
    cutout_img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cutout_img)
    cd.polygon(pts, fill=(255, 0, 0, 255))
    arr = np.array(img)
    cutout_arr = np.array(cutout_img)
    arr[cutout_arr[..., 3] > 0] = [0, 0, 0, 0]
    return Image.fromarray(arr)


# ── Internet ─────────────────────────────────────────────────────────────
def draw_wifi_state() -> Image.Image:
    """WiFi with shield over it — state-controlled internet."""
    img = draw_wifi()
    d = _d(img)
    # Shield silhouette overlaying the wifi center
    pts = [(C, 320), (C + 60, 340), (C + 55, 420),
           (C, 460), (C - 55, 420), (C - 60, 340)]
    d.polygon(pts, fill=W)
    return img


def draw_wifi_neutral() -> Image.Image:
    """WiFi with equal-sign — net neutrality."""
    img = draw_wifi()
    d = _d(img)
    # Equal sign below the wifi
    d.rectangle([C - 80, 400, C + 80, 420], fill=W)
    d.rectangle([C - 80, 440, C + 80, 460], fill=W)
    return img


# ── Rules of war ─────────────────────────────────────────────────────────
def draw_dove_shield() -> Image.Image:
    """Dove with shield — humanitarian regulations."""
    img = draw_dove()
    d = _d(img)
    # Shield in lower-left
    pts = [(120, 350), (170, 360), (165, 430),
           (120, 460), (75, 430), (70, 360)]
    d.polygon(pts, fill=W)
    return img


def draw_dove_split() -> Image.Image:
    """Dove with crossed sword below — limited war."""
    img = draw_dove()
    d = _d(img)
    # Single sword below
    a = math.radians(20)
    cx, cy = C, 380
    blade_len, blade_w = 140, 10
    tip_x = cx + blade_len * math.sin(a)
    tip_y = cy - blade_len * math.cos(a)
    perp_x = blade_w * math.cos(a)
    perp_y = blade_w * math.sin(a)
    d.polygon([
        (cx - perp_x, cy - perp_y),
        (tip_x, tip_y),
        (cx + perp_x, cy + perp_y),
    ], fill=W)
    # Guard
    gx = cx - 25 * math.sin(a)
    gy = cy + 25 * math.cos(a)
    d.line([
        (gx - 35 * math.cos(a), gy - 35 * math.sin(a)),
        (gx + 35 * math.cos(a), gy + 35 * math.sin(a)),
    ], fill=W, width=10)
    # Handle
    hx = cx - 70 * math.sin(a)
    hy = cy + 70 * math.cos(a)
    d.line([(gx, gy), (hx, hy)], fill=W, width=14)
    return img


# ── Right to information ─────────────────────────────────────────────────
def draw_globe_lines_open() -> Image.Image:
    """Globe with open lock — open government."""
    img = draw_globe_lines()
    d = _d(img)
    # Small open lock in lower-right
    d.rounded_rectangle([380, 340, 460, 420], radius=8, fill=W)
    # Open shackle (only one side connected)
    d.arc([390, 295, 450, 355], 180, 0, fill=W, width=10)
    # Erase the right side of the shackle to make it look "open"
    arr = np.array(img)
    arr[295:340, 440:455] = [0, 0, 0, 0]
    return Image.fromarray(arr)


# ── Antitrust / economic systems ─────────────────────────────────────────
def draw_handshake_break() -> Image.Image:
    """Handshake with a clean vertical fissure between the clasping hands.

    The cutout is constrained to the clasp region only (not the forearms) so
    the silhouette still reads as two arms reaching toward each other but
    failing to meet — the iconography of trust-busting.
    """
    img = draw_handshake()
    arr = np.array(img)
    # Narrow vertical fissure restricted to the clasp area (y≈170 to 280) only.
    arr[160:290, C - 10:C + 10] = [0, 0, 0, 0]
    img = Image.fromarray(arr)
    d = _d(img)
    # Tiny hammer head above the fissure to signal the bust
    d.rectangle([C - 50, 90, C + 50, 130], fill=W)
    d.polygon([(C + 50, 90), (C + 80, 105), (C + 80, 115), (C + 50, 130)], fill=W)
    # Hammer handle dropping down toward the break
    d.rectangle([C - 8, 130, C + 8, 165], fill=W)
    return img


def draw_gear_law_state() -> Image.Image:
    """Gear with state star at center — dirigisme."""
    img = draw_gear_law()
    d = _d(img)
    # Star at center (replacing the cutout circle visually)
    pts = []
    cx, cy, r = C, C, 60
    for i in range(10):
        rr = r if i % 2 == 0 else r // 2
        a = math.pi / 2 + math.pi * i / 5
        pts.append((cx + rr * math.cos(a), cy - rr * math.sin(a)))
    d.polygon(pts, fill=W)
    return img


def draw_gear_law_collective() -> Image.Image:
    """Two interlocking gears — command-cooperative economy."""
    img = _new(); d = _d(img)
    # Smaller pair of interlocking gears
    for cx, cy, r_body, n_teeth in [(C - 70, C - 30, 95, 8), (C + 80, C + 50, 80, 7)]:
        d.ellipse([cx - r_body, cy - r_body, cx + r_body, cy + r_body], fill=W)
        for i in range(n_teeth):
            a = 2 * math.pi * i / n_teeth
            tcx = cx + (r_body + 18) * math.cos(a)
            tcy = cy + (r_body + 18) * math.sin(a)
            hw, hh = 18, 22
            ca, sa = math.cos(a), math.sin(a)
            corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
            pts = [(tcx + x * ca - y * sa, tcy + x * sa + y * ca) for x, y in corners]
            d.polygon(pts, fill=W)
    # Center holes
    arr = np.array(img)
    y, x = np.ogrid[:S, :S]
    arr[((x - (C - 70)) ** 2 + (y - (C - 30)) ** 2) < 28 ** 2] = [0, 0, 0, 0]
    arr[((x - (C + 80)) ** 2 + (y - (C + 50)) ** 2) < 24 ** 2] = [0, 0, 0, 0]
    return Image.fromarray(arr)


# ── Criminal justice ─────────────────────────────────────────────────────
def draw_scales_circle() -> Image.Image:
    """Scales with circular arrow around — rehabilitation (cycle of restoration)."""
    img = draw_scales()
    d = _d(img)
    # Outer circle arrow
    d.arc([C - 220, C - 220, C + 220, C + 220], 30, 330, fill=W, width=16)
    # Arrow head at top
    d.polygon([(C + 190, C - 100), (C + 230, C - 60),
               (C + 170, C - 50)], fill=W)
    return img


# ── Privacy ──────────────────────────────────────────────────────────────
def draw_lock_strong() -> Image.Image:
    """Lock with shield ring — strong privacy rights."""
    img = draw_lock()
    d = _d(img)
    # Shield outline behind lock
    pts = [(C, 60), (C + 175, 110), (C + 170, 290),
           (C, 460), (C - 170, 290), (C - 175, 110)]
    d.polygon(pts, outline=W, width=18)
    return img


# ── Welfare ──────────────────────────────────────────────────────────────
def draw_umbrella_abundance() -> Image.Image:
    """Umbrella with abundance dots — post-scarcity."""
    img = draw_umbrella()
    d = _d(img)
    # Abundance dots scattered around the umbrella canopy
    for cx, cy in [(60, 80), (130, 50), (220, 30), (310, 30),
                   (400, 50), (470, 80), (40, 200), (480, 200)]:
        d.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=W)
    return img


# ── Ministry variants (pro-labor vs pro-capital ministries of labor) ────
def draw_building_ministry_labor() -> Image.Image:
    """Ministry building with crossed hammer + wrench — pro-labor ministry of labor."""
    img = draw_building_ministry()
    d = _d(img)
    # Crossed hammer + wrench in pediment area (above the dome)
    # Wrench (diagonal /) — simplified bar with circle head
    d.line([(C - 60, 30), (C + 60, 90)], fill=W, width=18)
    d.ellipse([C - 80, 18, C - 50, 48], fill=W)
    # Hammer (diagonal \) — bar with rectangular head
    d.line([(C + 60, 30), (C - 60, 90)], fill=W, width=18)
    d.rectangle([C + 50, 18, C + 90, 48], fill=W)
    return img


def draw_building_ministry_capital() -> Image.Image:
    """Ministry building with coin stack — pro-capital ministry of labor."""
    img = draw_building_ministry()
    d = _d(img)
    # Small coin stack on top of the dome
    for y_top in [70, 50, 30]:
        d.rectangle([C - 50, y_top + 8, C + 50, y_top + 24], fill=W)
        d.ellipse([C - 50, y_top, C + 50, y_top + 18], fill=W)
    return img


# ── Minority rights (4-stance bespoke shapes on top of existing people/chains) ──
def draw_people_separated() -> Image.Image:
    """People separated by a vertical bar — discrimination."""
    img = draw_people()
    d = _d(img)
    # Vertical bar separating left figure from the rest
    d.rectangle([C - 75, 80, C - 65, 440], fill=W)
    # Cut a clear gap behind the bar
    arr = np.array(img)
    arr[80:440, C - 65:C - 55] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def draw_people_shielded() -> Image.Image:
    """People inside a shield — protection."""
    img = draw_people()
    d = _d(img)
    # Shield outline embracing the people figures
    pts = [(C, 50), (C + 200, 90), (C + 195, 290),
           (C + 100, 410), (C, 460),
           (C - 100, 410), (C - 195, 290), (C - 200, 90)]
    d.polygon(pts, outline=W, width=18)
    return img


def draw_people_raised() -> Image.Image:
    """People with a star above — affirmative action / uplift."""
    img = draw_people()
    d = _d(img)
    # Star above
    pts = []
    cx, cy, r = C, 50, 38
    for i in range(10):
        rr = r if i % 2 == 0 else r // 2
        a = math.pi / 2 + math.pi * i / 5
        pts.append((cx + rr * math.cos(a), cy - rr * math.sin(a)))
    d.polygon(pts, fill=W)
    # Two upward-extending arms (pull the upper torso into a "raised" silhouette)
    d.polygon([(C - 35, 175), (C - 70, 100), (C - 50, 95),
               (C - 15, 170)], fill=W)
    d.polygon([(C + 35, 175), (C + 70, 100), (C + 50, 95),
               (C + 15, 170)], fill=W)
    return img


# ═══════════════════════════════════════════════════════════════════════════
# BADGE GLYPHS (composited with a base shape via compose_silhouette)
# Used only where bespoke shape design is genuinely thin (currently: LGBTQ
# rights tier ladder on top of `people`). Each glyph is drawn in roughly the
# lower-right ~140×140 region of the 512 canvas so it overlays cleanly.
# ═══════════════════════════════════════════════════════════════════════════

# Anchor point for badges — high above the base shape's body, so the dots
# extend the silhouette into otherwise empty canvas (no merging with base).
_BADGE_CY = 30

# Per-badge dot positions (cx coordinates). Each badge also defines a list of
# (cx, cy, r) tuples used by `compose_silhouette` to clear a transparent
# halo around each dot before drawing it — the halo separates the dot from
# any nearby base-shape pixels (e.g. a head that extends to y≈80).
_BADGE_DOT_LAYOUTS: dict[str, list[tuple[int, int, int]]] = {
    "dot_one":   [(C, _BADGE_CY, 26)],
    "dot_two":   [(C - 40, _BADGE_CY, 24), (C + 40, _BADGE_CY, 24)],
    "dot_three": [(C - 70, _BADGE_CY, 22), (C, _BADGE_CY, 22), (C + 70, _BADGE_CY, 22)],
}


def _draw_dots(layout: list[tuple[int, int, int]]) -> Image.Image:
    img = _new(); d = _d(img)
    for cx, cy, r in layout:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=W)
    return img


def draw_badge_dot_one() -> Image.Image:
    """Single dot — tier 1 of a ladder."""
    return _draw_dots(_BADGE_DOT_LAYOUTS["dot_one"])


def draw_badge_dot_two() -> Image.Image:
    """Two dots — tier 2 of a ladder."""
    return _draw_dots(_BADGE_DOT_LAYOUTS["dot_two"])


def draw_badge_dot_three() -> Image.Image:
    """Three dots — tier 3 of a ladder."""
    return _draw_dots(_BADGE_DOT_LAYOUTS["dot_three"])


# ═══════════════════════════════════════════════════════════════════════════
# SHAPE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

SHAPES: dict[str, callable] = {
    # ── base shapes ─────────────────────────────────────────────────────
    "scroll":           draw_scroll,
    "scales":           draw_scales,
    "shield_cross":     draw_shield_cross,
    "eye":              draw_eye,
    "coin_stack":       draw_coin_stack,
    "bank":             draw_bank,
    "people":           draw_people,
    "lightbulb":        draw_lightbulb,
    "gavel":            draw_gavel,
    "lock":             draw_lock,
    "globe_lines":      draw_globe_lines,
    "sword_crossed":    draw_sword_crossed,
    "family":           draw_family,
    "dna":              draw_dna,
    "circuit_board":    draw_circuit_board,
    "pillar":           draw_pillar,
    "ballot_box":       draw_ballot_box,
    "building_ministry": draw_building_ministry,
    "no_building":      draw_no_building,
    "speech_bubble":    draw_speech_bubble,
    "handshake":        draw_handshake,
    "gear_law":         draw_gear_law,
    "robot_head":       draw_robot_head,
    "wifi":             draw_wifi,
    "crown":            draw_crown,
    "chains":           draw_chains,
    "umbrella":         draw_umbrella,
    "atom_law":         draw_atom_law,
    "dove":             draw_dove,
    # ── bespoke per-law variants (within-group differentiation) ─────────
    "bank_open":               draw_bank_open,
    "bank_columns_paired":     draw_bank_columns_paired,
    "bank_narrow":             draw_bank_narrow,
    "bank_arrow_up":           draw_bank_arrow_up,
    "bank_shield":             draw_bank_shield,
    "robot_head_purity":       draw_robot_head_purity,
    "robot_head_medical":      draw_robot_head_medical,
    "robot_head_regulated":    draw_robot_head_regulated,
    "robot_head_mandatory":    draw_robot_head_mandatory,
    "speech_bubble_pair":      draw_speech_bubble_pair,
    "speech_bubble_pure":      draw_speech_bubble_pure,
    "speech_bubble_hammer":    draw_speech_bubble_hammer,
    "speech_bubble_globe":     draw_speech_bubble_globe,
    "lightbulb_open":          draw_lightbulb_open,
    "lightbulb_locked":        draw_lightbulb_locked,
    "lightbulb_branched":      draw_lightbulb_branched,
    "dna_corporate":           draw_dna_corporate,
    "dna_open":                draw_dna_open,
    "dna_state":               draw_dna_state,
    "family_natal":            draw_family_natal,
    "family_planned":          draw_family_planned,
    "family_controlled":       draw_family_controlled,
    "scroll_split":            draw_scroll_split,
    "scroll_equal":            draw_scroll_equal,
    "coin_stack_paper":        draw_coin_stack_paper,
    "coin_stack_digital":      draw_coin_stack_digital,
    "pillar_three":            draw_pillar_three,
    "pillar_branched":         draw_pillar_branched,
    "ballot_box_capped":       draw_ballot_box_capped,
    "ballot_box_public":       draw_ballot_box_public,
    "wifi_state":              draw_wifi_state,
    "wifi_neutral":            draw_wifi_neutral,
    "dove_shield":             draw_dove_shield,
    "dove_split":              draw_dove_split,
    "globe_lines_open":        draw_globe_lines_open,
    "handshake_break":         draw_handshake_break,
    "gear_law_state":          draw_gear_law_state,
    "gear_law_collective":     draw_gear_law_collective,
    "scales_circle":           draw_scales_circle,
    "lock_strong":             draw_lock_strong,
    "umbrella_abundance":      draw_umbrella_abundance,
    "people_separated":        draw_people_separated,
    "people_shielded":         draw_people_shielded,
    "people_raised":           draw_people_raised,
    "building_ministry_labor":   draw_building_ministry_labor,
    "building_ministry_capital": draw_building_ministry_capital,
}


# Badge glyphs composited on top of a base shape. None means "no badge".
BADGES: dict[str, callable] = {
    "dot_one":   draw_badge_dot_one,
    "dot_two":   draw_badge_dot_two,
    "dot_three": draw_badge_dot_three,
}


def compose_silhouette(shape_name: str, badge_name: str | None) -> Image.Image:
    """Render a base shape and optionally composite a badge glyph on top.

    To prevent badge dots from visually merging into the base silhouette
    (which happens whenever white-on-white pixels overlap), we first clear a
    transparent halo around each dot's footprint, then alpha-composite the
    badge. The metallic-styling pipeline reads the cleared halo as an inner
    edge and embosses each dot as a distinct raised feature.
    """
    base = SHAPES[shape_name]()
    if badge_name is None:
        return base

    layout = _BADGE_DOT_LAYOUTS.get(badge_name)
    if layout:
        arr = np.array(base)
        y, x = np.ogrid[:S, :S]
        for cx, cy, r in layout:
            halo = (r + 12) ** 2
            mask = ((x - cx) ** 2 + (y - cy) ** 2) < halo
            arr[mask] = [0, 0, 0, 0]
        base = Image.fromarray(arr)

    badge = BADGES[badge_name]()
    return Image.alpha_composite(base, badge)


# ═══════════════════════════════════════════════════════════════════════════
# LAW → ICON MAPPING
# Maps each law_key to (shape, color, badge_or_none). Within a law group every
# law must render a unique (shape, color, badge) triple — enforced by
# audit_within_group_uniqueness() at run time.
# ═══════════════════════════════════════════════════════════════════════════

LAW_ICON_MAP: dict[str, tuple[str, str, str | None]] = {
    # ── Welfare & Social Systems ──
    "law_universal_basic_income":         ("umbrella",            "gold",      None),
    "law_post-scarcity":                  ("umbrella_abundance",  "gold",      None),

    # ── Privacy & Surveillance ──
    "law_intrusive_surveillance":         ("eye",                 "gold",      None),
    "law_minimal_privacy_protection":     ("lock",                "dark_gold", None),
    "law_moderate_data_privacy":          ("lock",                "gold",      None),
    "law_strong_privacy_rights":          ("lock_strong",         "gold",      None),

    # ── Inheritance ──
    "law_primogeniture":                  ("scroll",              "gold",      None),
    "law_partible":                       ("scroll_split",        "gold",      None),
    "law_equal_inheritance":              ("scroll_equal",        "gold",      None),
    "law_non_inheritable_usage_rights":   ("scroll",              "dark_gold", None),

    # ── War & Warfare ──
    "law_total_war":                      ("sword_crossed",       "gold",      None),
    "law_traditional_rules_of_war":       ("shield_cross",        "gold",      None),
    "law_war_crimes_forbidden":           ("dove",                "gold",      None),
    "law_humanitarian_regulations":       ("dove_shield",         "gold",      None),
    "law_limited_war":                    ("dove_split",          "gold",      None),

    # ── Intellectual Property ──
    "law_no_ip_protection":               ("lightbulb",           "dark_gold", None),
    "law_creative_commons":               ("lightbulb_open",      "gold",      None),
    "law_traditional_ip_protection":      ("lightbulb",           "gold",      None),
    "law_strict_ip_protection":           ("lightbulb_locked",    "gold",      None),
    "law_open_source_innovation":         ("lightbulb_branched",  "gold",      None),

    # ── Currency & Currency Systems ──
    "law_commodity_money":                ("coin_stack",          "dark_gold", None),
    "law_gold_standard":                  ("coin_stack",          "gold",      None),
    "law_fiat_currency":                  ("coin_stack_paper",    "gold",      None),
    "law_digital_currency":               ("coin_stack_digital",  "gold",      None),
    "law_decentralized_cryptocurrency":   ("circuit_board",       "gold",      None),

    # ── Government Information & Transparency ──
    "law_state_secrets":                  ("eye",                 "dark_gold", None),
    "law_informal_government_secrecy":    ("eye",                 "gold",      None),
    "law_freedom_of_information":         ("globe_lines",         "gold",      None),
    "law_open_government":                ("globe_lines_open",    "gold",      None),

    # ── Criminal Justice ──
    "law_punishment_focused_criminal_justice":     ("gavel",          "gold", None),
    "law_restorative_justice":                     ("scales",         "gold", None),
    "law_rehabilitation_focused_criminal_justice": ("scales_circle",  "gold", None),

    # ── LGBTQ Rights (5-tier ladder) — bespoke shape only at the extremes,
    # dot-badge ladder distinguishes the 3 mid-tiers that share `people`.
    "law_active_persecution":             ("chains",              "gold",      None),
    "law_legal_limbo":                    ("people",              "dark_gold", None),
    "law_basic_protections":              ("people",              "gold",      "dot_one"),
    "law_comprehensive_rights":           ("people",              "gold",      "dot_two"),
    "law_full_equality_and_protection":   ("people",              "gold",      "dot_three"),

    # ── Minority Rights (sub-laws) ──
    "law_minority_rights_violent_hostility":     ("chains",         "gold",      None),
    "law_minority_rights_ghettoization":         ("chains",         "dark_gold", None),
    "law_minority_rights_cultural_assimilation": ("people",         "dark_gold", None),
    "law_minority_rights_discrimination":        ("people_separated", "gold",   None),
    "law_minority_rights_indifference":          ("people",         "gold",      None),
    "law_minority_rights_protection":            ("people_shielded", "gold",     None),
    "law_minority_rights_affirmative_action":    ("people_raised",  "gold",      None),

    # ── Human Augmentation ──
    "law_no_augmentation":                ("robot_head",             "dark_gold", None),
    "law_unrestricted_augmentation":      ("robot_head",             "gold",      None),
    "law_human_purity":                   ("robot_head_purity",      "gold",      None),
    "law_medical_augmentation_only":      ("robot_head_medical",     "gold",      None),
    "law_regulated_augmentation_market":  ("robot_head_regulated",   "gold",      None),
    "law_mandatory_augmentation":         ("robot_head_mandatory",   "gold",      None),

    # ── Government Structure & Federalism ──
    "law_feudal_contracts":               ("crown",               "dark_gold", None),
    "law_unitary_state":                  ("pillar",              "gold",      None),
    "law_federal_system":                 ("pillar_three",        "gold",      None),
    "law_devolution":                     ("pillar_branched",     "gold",      None),

    # ── Campaign Finance ──
    "law_no_campaign_finance_laws":       ("ballot_box",          "dark_gold", None),
    "law_unregulated_donations":          ("ballot_box",          "gold",      None),
    "law_donation_limits":                ("ballot_box_capped",   "gold",      None),
    "law_publicly_funded_elections":      ("ballot_box_public",   "gold",      None),

    # ── Family & Population Policy ──
    "law_traditional_family_structure":   ("family",              "gold",      None),
    "law_pro_natalist_subsidies":         ("family_natal",        "gold",      None),
    "law_state_sponsored_family_planning": ("family_planned",     "gold",      None),
    "law_population_control_measures":    ("family_controlled",   "gold",      None),
    "law_communal_child_rearing":         ("family",              "dark_gold", None),

    # ── Banking & Financial Regulation ──
    "law_unregulated_banking":               ("bank",                  "dark_gold", None),
    "law_free_mutual_banking":               ("bank_open",             "gold",      None),
    "law_universal_banking_light_prudence":  ("bank_columns_paired",   "gold",      None),
    "law_prudential_narrow_banking":         ("bank_narrow",           "gold",      None),
    "law_directed_credit_development_banks": ("bank_arrow_up",         "gold",      None),
    "law_central_bank_independence":         ("bank_shield",           "gold",      None),

    # ── Internet & Digital Policy ──
    "law_no_internet_policy":             ("wifi",                "dark_gold", None),
    "law_unregulated_internet":           ("wifi",                "gold",      None),
    "law_state_controlled_internet":      ("wifi_state",          "gold",      None),
    "law_net_neutrality":                 ("wifi_neutral",        "gold",      None),

    # ── Genetics & Heredity ──
    "law_traditional_heredity":           ("dna",                 "gold",      None),
    "law_ban_on_genetic_modification":    ("dna",                 "dark_gold", None),
    "law_corporate_genetic_licensing":    ("dna_corporate",       "gold",      None),
    "law_open_source_genetics":           ("dna_open",            "gold",      None),
    "law_state_eugenics_program":         ("dna_state",           "gold",      None),

    # ── Language Policy ──
    "law_local_vernacular":               ("speech_bubble",        "dark_gold", None),
    "law_civic_monolingualism":           ("speech_bubble",        "gold",      None),
    "law_multilingual_federalism":        ("speech_bubble_pair",   "gold",      None),
    "law_linguistic_purity":              ("speech_bubble_pure",   "gold",      None),
    "law_state_led_language_reform":      ("speech_bubble_hammer", "gold",      None),
    "law_ubiquitous_translation":         ("speech_bubble_globe",  "gold",      None),

    # ── Economic Systems & Trade ──
    "law_guilds_chartered_monopolies":    ("gear_law",             "dark_gold", None),
    "law_freedom_of_contract":            ("handshake",            "gold",      None),
    "law_trust_busting":                  ("handshake_break",      "gold",      None),
    "law_regulated_utilities":            ("gear_law",             "gold",      None),
    "law_dirigisme":                      ("gear_law_state",       "gold",      None),
    "law_command_cooperative_economy":    ("gear_law_collective",  "gold",      None),

    # ── Advanced Political Systems ──
    "law_protected_class":                ("people",              "gold",      None),
    "law_neocameralism":                  ("crown",               "gold",      None),
    "law_direct_democracy":               ("ballot_box",          "gold",      None),
    "law_neocolonialism":                 ("globe_lines",         "gold",      None),
    "law_algorithmic_governance":         ("circuit_board",       "gold",      None),

    # ── Ministries (active) ──
    "law_ministry_of_foreign_affairs":             ("building_ministry", "gold", None),
    "law_ministry_of_war":                         ("building_ministry", "gold", None),
    "law_ministry_of_commerce":                    ("building_ministry", "gold", None),
    "law_national_bank":                           ("building_ministry", "gold", None),
    "law_ministry_of_culture":                     ("building_ministry", "gold", None),
    "law_pro_labor_ministry_of_labor":             ("building_ministry_labor",   "gold", None),
    "law_pro_capital_ministry_of_labor":           ("building_ministry_capital", "gold", None),
    "law_ministry_of_the_environment":             ("building_ministry", "gold", None),
    "law_ministry_of_intelligence_and_security":   ("building_ministry", "gold", None),
    "law_ministry_of_refugee_affairs":             ("building_ministry", "gold", None),
    "law_ministry_of_propaganda":                  ("building_ministry", "gold", None),
    "law_ministry_of_science":                     ("building_ministry", "gold", None),
    "law_ministry_of_thought_control":             ("building_ministry", "gold", None),
    "law_ministry_of_consumer_protection":         ("building_ministry", "gold", None),
    "law_ministry_of_urban_planning":              ("building_ministry", "gold", None),
    "law_ministry_of_religion":                    ("building_ministry", "gold", None),
    "law_ministry_of_international_aid":           ("building_ministry", "gold", None),

    # ── Ministries (no ministry) ──
    "law_no_ministry_of_foreign_affairs":           ("no_building", "dark_gold", None),
    "law_no_ministry_of_war":                       ("no_building", "dark_gold", None),
    "law_no_ministry_of_commerce":                  ("no_building", "dark_gold", None),
    "law_no_national_bank":                         ("no_building", "dark_gold", None),
    "law_no_ministry_of_culture":                   ("no_building", "dark_gold", None),
    "law_no_ministry_of_labor":                     ("no_building", "dark_gold", None),
    "law_no_ministry_of_the_environment":           ("no_building", "dark_gold", None),
    "law_no_ministry_of_intelligence_and_security": ("no_building", "dark_gold", None),
    "law_no_ministry_of_refugee_affairs":           ("no_building", "dark_gold", None),
    "law_no_ministry_of_propaganda":                ("no_building", "dark_gold", None),
    "law_no_ministry_of_science":                   ("no_building", "dark_gold", None),
    "law_no_ministry_of_thought_control":           ("no_building", "dark_gold", None),
    "law_no_ministry_of_consumer_protection":       ("no_building", "dark_gold", None),
    "law_no_ministry_of_urban_planning":            ("no_building", "dark_gold", None),
    "law_no_ministry_of_religion":                  ("no_building", "dark_gold", None),
    "law_no_ministry_of_international_aid":         ("no_building", "dark_gold", None),
}


# ═══════════════════════════════════════════════════════════════════════════
# LAW FILE PARSING
# ═══════════════════════════════════════════════════════════════════════════

def find_laws_needing_icons() -> dict[str, tuple[str, str]]:
    """Find all laws in LAW_ICON_MAP and their current icon reference.

    Returns: {law_name: (source_filename, current_icon)}
    """
    results = {}

    for fname in os.listdir(LAW_DIR):
        if not fname.endswith(".txt"):
            continue
        fpath = LAW_DIR / fname
        with open(fpath, "r", encoding="utf-8-sig") as f:
            content = f.read()

        current_law = None
        brace_depth = 0
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            if brace_depth == 0:
                if "=" in stripped and "{" in stripped:
                    name = stripped.split("=")[0].strip()
                    if name.startswith("law_") and name in LAW_ICON_MAP:
                        current_law = name
                        brace_depth = stripped.count("{") - stripped.count("}")
                        continue
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth < 0:
                    brace_depth = 0
                continue

            if current_law:
                brace_depth += stripped.count("{") - stripped.count("}")
                m = re.search(r'icon\s*=\s*"([^"]*)"', stripped)
                if m:
                    results[current_law] = (fname, m.group(1))
                if brace_depth <= 0:
                    current_law = None
                    brace_depth = 0
            else:
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth <= 0:
                    brace_depth = 0

    return results


def build_law_to_group_map() -> dict[str, str]:
    """Parse mod + vanilla law files to build a `law_name -> lawgroup_*` map.

    Used by `audit_within_group_uniqueness()` to verify that no two laws in the
    same group resolve to the same icon. Vanilla is included so a vanilla group
    that contains a mod-overridden law is correctly attributed.
    """
    law_to_group: dict[str, str] = {}

    def _scan_dir(law_dir: Path, fill_only_missing: bool) -> None:
        if not law_dir.is_dir():
            return
        for fpath in sorted(law_dir.glob("*.txt")):
            try:
                content = fpath.read_text(encoding="utf-8-sig")
            except OSError:
                continue
            # Walk top-level law blocks, capturing the `group = lawgroup_X`
            # field within each. Nested blocks (triggers, modifiers) are
            # skipped via brace tracking.
            i = 0
            text = content
            while True:
                m = re.search(r"^(law_[\w\-]+)\s*=\s*\{", text[i:], re.MULTILINE)
                if not m:
                    break
                name = m.group(1)
                start = i + m.end()
                depth = 1
                j = start
                while j < len(text) and depth > 0:
                    if text[j] == "{":
                        depth += 1
                    elif text[j] == "}":
                        depth -= 1
                    j += 1
                body = text[start:j]
                gm = re.search(r"^\s*group\s*=\s*(lawgroup_\w+)", body, re.MULTILINE)
                if gm and (not fill_only_missing or name not in law_to_group):
                    law_to_group[name] = gm.group(1)
                i = j

    # Mod first (authoritative); then fall back to vanilla for any laws the
    # mod doesn't override.
    _scan_dir(LAW_DIR, fill_only_missing=False)
    try:
        from path_constants import base_game_path  # type: ignore
        vanilla_law_dir = Path(base_game_path) / "game" / "common" / "laws"
        _scan_dir(vanilla_law_dir, fill_only_missing=True)
    except Exception:
        pass  # path_constants not available on this machine — skip vanilla scan

    return law_to_group


def audit_within_group_uniqueness(
    allow_collisions: bool = False,
) -> int:
    """Verify every law in a given law group renders a unique icon triple.

    Returns the number of within-group collisions found. If any are found and
    `allow_collisions` is False, exits with a non-zero status code.
    """
    law_to_group = build_law_to_group_map()
    by_group: dict[str, list[tuple[str, tuple[str, str, str | None]]]] = defaultdict(list)
    unmapped_laws: list[str] = []
    for law, triple in LAW_ICON_MAP.items():
        group = law_to_group.get(law)
        if group is None:
            unmapped_laws.append(law)
            continue
        by_group[group].append((law, triple))

    collisions = 0
    for group, items in sorted(by_group.items()):
        seen: dict[tuple[str, str, str | None], list[str]] = defaultdict(list)
        for law, triple in items:
            seen[triple].append(law)
        dupes = {k: v for k, v in seen.items() if len(v) > 1}
        if not dupes:
            continue
        for triple, laws in dupes.items():
            collisions += len(laws)
            shape, color, badge = triple
            badge_str = badge if badge else "—"
            print(f"  COLLISION in {group}: ({shape}, {color}, {badge_str}) shared by {len(laws)} laws:")
            for law in laws:
                print(f"      {law}")

    if unmapped_laws:
        print(f"\n  NOTE: {len(unmapped_laws)} law(s) in LAW_ICON_MAP have no resolved group "
              f"(neither mod nor vanilla); skipping audit for them:")
        for law in unmapped_laws:
            print(f"      {law}")

    print(f"\nAudit: {collisions} within-group collision(s) across {len(by_group)} group(s).")

    if collisions and not allow_collisions:
        print("\nERROR: within-group icon collisions detected. "
              "Re-run with --allow-collisions to bypass during dev iteration.")
        sys.exit(1)
    return collisions


# ═══════════════════════════════════════════════════════════════════════════
# ICON GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def icon_filename(law_name: str) -> str:
    """Generate the icon filename for a law (strip 'law_' prefix)."""
    return law_name.removeprefix("law_")


def generate_silhouette(
    shape_name: str,
    out_path: Path,
    badge_name: str | None = None,
) -> None:
    """Generate and save a (possibly composited) silhouette PNG."""
    img = compose_silhouette(shape_name, badge_name)
    img.save(out_path, format="PNG")


def _silhouette_key(shape: str, badge: str | None) -> str:
    """Filename-safe key for a (shape, badge) silhouette."""
    return shape if badge is None else f"{shape}__{badge}"


def generate_all_icons(
    preview_only: bool = False,
    force: bool = False,
) -> dict[str, Path]:
    """Generate all needed law icon DDS files.

    Returns: {law_name: dds_path}
    """
    # Determine unique (shape, color, badge) combos needed
    needed_combos: set[tuple[str, str, str | None]] = set()
    for law_name, (shape, color, badge) in LAW_ICON_MAP.items():
        needed_combos.add((shape, color, badge))

    # Determine which individual law icons need generation
    laws_to_generate = list(LAW_ICON_MAP.keys())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not force and not preview_only:
        already_exist = []
        for law_name in laws_to_generate:
            dds_path = OUTPUT_DIR / f"{icon_filename(law_name)}.dds"
            if dds_path.exists():
                already_exist.append(law_name)
        skipped = len(already_exist)
        for name in already_exist:
            laws_to_generate.remove(name)
        if skipped:
            print(f"Skipping {skipped} icons already on disk (use --force to regenerate)")

    if not laws_to_generate:
        print("All icons up to date, nothing to generate.")
        return {}

    print(f"Need to generate {len(laws_to_generate)} law icons "
          f"across {len(needed_combos)} unique (shape, color, badge) combos")

    # Find texconv
    texconv = None
    if not preview_only:
        texconv = find_texconv()
        if texconv is None:
            from convert_event_image import ensure_texconv
            texconv = ensure_texconv()
        print(f"Using texconv: {texconv}")

    preview_dir = SCRIPT_DIR / "preview_law_icons"
    if preview_only:
        preview_dir.mkdir(exist_ok=True)

    icon_paths = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Generate composite silhouette PNGs (one per (shape, badge) pair).
        sil_pairs: set[tuple[str, str | None]] = {(s, b) for s, _, b in needed_combos}
        silhouettes: dict[tuple[str, str | None], Path] = {}
        for shape_name, badge_name in sorted(sil_pairs, key=lambda p: (p[0], p[1] or "")):
            sil_path = tmpdir / f"sil_{_silhouette_key(shape_name, badge_name)}.png"
            generate_silhouette(shape_name, sil_path, badge_name=badge_name)
            silhouettes[(shape_name, badge_name)] = sil_path

        print(f"  Generated {len(silhouettes)} base silhouettes")

        # Cache styled results for (shape, color, badge) combos
        styled_cache: dict[tuple[str, str, str | None], np.ndarray] = {}

        for law_name in sorted(laws_to_generate):
            shape, color, badge = LAW_ICON_MAP[law_name]
            fname = icon_filename(law_name)

            cache_key = (shape, color, badge)
            if cache_key not in styled_cache:
                sil_path = silhouettes[(shape, badge)]
                sil_data = load_silhouette(str(sil_path), ICON_SIZE)
                color_rgb = LAW_COLORS[color]
                styled_arr = apply_metallic_style(sil_data, color_rgb)
                styled_cache[cache_key] = styled_arr

            styled_arr = styled_cache[cache_key]
            styled = Image.fromarray(styled_arr)

            if preview_only:
                preview_path = preview_dir / f"{fname}.png"
                styled.save(preview_path, format="PNG")
                icon_paths[law_name] = preview_path
            else:
                png_path = tmpdir / f"{fname}.png"
                styled.save(png_path, format="PNG")
                dds_path = OUTPUT_DIR / f"{fname}.dds"
                convert_to_dds(png_path, dds_path, texconv=texconv)
                icon_paths[law_name] = dds_path

        print(f"  Generated {len(icon_paths)} icon files")

    return icon_paths


# ═══════════════════════════════════════════════════════════════════════════
# LAW FILE UPDATING
# ═══════════════════════════════════════════════════════════════════════════

def update_law_files(dry_run: bool = False) -> int:
    """Update icon references in law .txt files.

    Returns: count of laws updated.
    """
    updates_by_file: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for fname in os.listdir(LAW_DIR):
        if not fname.endswith(".txt"):
            continue
        fpath = LAW_DIR / fname
        with open(fpath, "r", encoding="utf-8-sig") as f:
            content = f.read()

        current_law = None
        brace_depth = 0
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if brace_depth == 0:
                if "=" in stripped and "{" in stripped:
                    name = stripped.split("=")[0].strip()
                    if name.startswith("law_") and name in LAW_ICON_MAP:
                        current_law = name
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth < 0:
                    brace_depth = 0
                continue
            if current_law:
                brace_depth += stripped.count("{") - stripped.count("}")
                if re.search(r'icon\s*=', stripped):
                    new_icon = icon_filename(current_law)
                    updates_by_file[fname].append((current_law, new_icon))
                if brace_depth <= 0:
                    current_law = None
                    brace_depth = 0
            else:
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth <= 0:
                    brace_depth = 0

    total = sum(len(v) for v in updates_by_file.values())
    if dry_run:
        for fname, updates in sorted(updates_by_file.items()):
            print(f"\n{fname}: {len(updates)} laws to update")
            for law_name, icon_file in updates[:10]:
                print(f"  {law_name} -> {icon_file}.dds")
            if len(updates) > 10:
                print(f"  ... and {len(updates) - 10} more")
        print(f"\nTotal: {total} laws would be updated")
        return total

    updated = 0
    for fname, updates in updates_by_file.items():
        fpath = LAW_DIR / fname
        with open(fpath, "r", encoding="utf-8-sig") as f:
            content = f.read()

        law_to_icon = {law_name: icon_file for law_name, icon_file in updates}

        lines = content.split("\n")
        new_lines = []
        current_law = None
        brace_depth = 0

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("#"):
                new_lines.append(line)
                continue

            if brace_depth == 0:
                if "=" in stripped and "{" in stripped:
                    name = stripped.split("=")[0].strip()
                    if name.startswith("law_") and name in law_to_icon:
                        current_law = name
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth < 0:
                    brace_depth = 0
                new_lines.append(line)
                continue

            if current_law:
                brace_depth += stripped.count("{") - stripped.count("}")
                if re.search(r'icon\s*=', stripped):
                    new_icon_path = f"gfx/interface/icons/law_icons/{law_to_icon[current_law]}.dds"
                    line = re.sub(
                        r'icon\s*=\s*"[^"]*"',
                        f'icon = "{new_icon_path}"',
                        line,
                    )
                    updated += 1
                if brace_depth <= 0:
                    current_law = None
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

        print(f"  Updated {len(updates)} laws in {fname}")

    return updated


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate law icons in vanilla Victoria 3 style.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--update-files", action="store_true",
                        help="Also update icon references in law .txt files")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate all icons even if DDS exists")
    parser.add_argument("--preview", action="store_true",
                        help="Only generate PNGs in preview_law_icons/ dir")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show law->icon mapping without generating")
    parser.add_argument("--allow-collisions", action="store_true",
                        help="Continue even if within-group icon collisions exist "
                             "(default: hard-fail).")

    args = parser.parse_args()

    # Validate all laws in map have valid shapes / colors / badges
    for law_name, triple in LAW_ICON_MAP.items():
        shape, color, badge = triple
        if shape not in SHAPES:
            print(f"ERROR: Unknown shape '{shape}' for {law_name}")
            sys.exit(1)
        if color not in LAW_COLORS:
            print(f"ERROR: Unknown color '{color}' for {law_name}")
            sys.exit(1)
        if badge is not None and badge not in BADGES:
            print(f"ERROR: Unknown badge '{badge}' for {law_name}")
            sys.exit(1)

    # Hard-fail by default on within-group icon collisions; --allow-collisions
    # downgrades to a warning for forward dev iteration.
    audit_within_group_uniqueness(allow_collisions=args.allow_collisions)

    if args.dry_run:
        # Show mapping
        print(f"\nLaw icon mapping ({len(LAW_ICON_MAP)} laws):\n")
        by_shape = defaultdict(list)
        for law_name, (shape, color, badge) in sorted(LAW_ICON_MAP.items()):
            by_shape[shape].append((law_name, color, badge))

        for shape, laws in sorted(by_shape.items()):
            print(f"{shape} ({len(laws)} laws):")
            for law_name, color, badge in laws:
                badge_str = f", badge={badge}" if badge else ""
                print(f"  {law_name} -> {icon_filename(law_name)}.dds ({color}{badge_str})")
            print()

        # Check which laws exist in files
        existing = find_laws_needing_icons()
        missing = set(LAW_ICON_MAP.keys()) - set(existing.keys())
        if missing:
            print(f"\nWARNING: {len(missing)} laws in map not found in law files:")
            for m in sorted(missing):
                print(f"  {m}")

        # Also check for files to update
        if args.update_files:
            update_law_files(dry_run=True)
        return

    # Generate icons
    icon_paths = generate_all_icons(
        preview_only=args.preview,
        force=args.force,
    )

    if icon_paths:
        print(f"\nGenerated {len(icon_paths)} icons")
        if args.preview:
            print("Preview PNGs saved to preview_law_icons/")

    # Update law files
    if args.update_files and not args.preview:
        print("\nUpdating law file icon references...")
        count = update_law_files()
        print(f"Updated {count} icon references")

    print("\nDone!")


if __name__ == "__main__":
    main()
