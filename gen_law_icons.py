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
sys.path.insert(0, str(SCRIPT_DIR))

from gen_pm_icons import (
    apply_metallic_style,
    convert_to_dds,
    find_texconv,
    load_silhouette,
    parse_color,
)

# ── paths ────────────────────────────────────────────────────────────────
OUTPUT_DIR = SCRIPT_DIR / "gfx" / "interface" / "icons" / "law_icons"
LAW_DIR = SCRIPT_DIR / "common" / "laws"
ICON_SIZE = 256  # vanilla law icons are 256×256 or 302×302; 256 is the newer standard.

# ── silhouette canvas ────────────────────────────────────────────────────
S = 512        # drawing canvas size
C = S // 2     # center
R = 200        # usable radius (larger fill for law icons)
W = (255, 255, 255, 255)   # white fill


# ── color presets for law groups (warm bronze like vanilla) ──────────────
# Laws use the same warm metallic palette as vanilla:
# main bronze (default), darker bronze for "no_X" laws, tinted for special groups.
LAW_COLORS: dict[str, tuple[int, int, int]] = {
    "bronze":      (175, 145, 110),   # standard warm bronze (vanilla default)
    "dark_bronze": (140, 115,  85),   # darker for "no_ministry" etc.
    "copper":      (180, 120,  90),   # warm copper for active/aggressive laws
    "silver":      (155, 155, 160),   # cool silver for tech/modern laws
    "pale_gold":   (185, 165, 120),   # lighter gold for progressive laws
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
# SHAPE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

SHAPES: dict[str, callable] = {
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
}


# ═══════════════════════════════════════════════════════════════════════════
# LAW → ICON MAPPING
# Maps each law_key to (shape, color).
# ═══════════════════════════════════════════════════════════════════════════

LAW_ICON_MAP: dict[str, tuple[str, str]] = {
    # ── Welfare & Social Systems ──
    "law_universal_basic_income":         ("umbrella",        "pale_gold"),
    "law_post-scarcity":                  ("umbrella",        "silver"),

    # ── Privacy & Surveillance ──
    "law_intrusive_surveillance":         ("eye",             "copper"),
    "law_minimal_privacy_protection":     ("lock",            "dark_bronze"),
    "law_moderate_data_privacy":          ("lock",            "bronze"),
    "law_strong_privacy_rights":          ("lock",            "pale_gold"),

    # ── Inheritance ──
    "law_primogeniture":                  ("scroll",          "bronze"),
    "law_partible":                       ("scroll",          "pale_gold"),
    "law_equal_inheritance":              ("scroll",          "silver"),
    "law_non_inheritable_usage_rights":   ("scroll",          "dark_bronze"),

    # ── War & Warfare ──
    "law_total_war":                      ("sword_crossed",   "copper"),
    "law_traditional_rules_of_war":       ("shield_cross",    "bronze"),
    "law_war_crimes_forbidden":           ("dove",            "pale_gold"),
    "law_humanitarian_regulations":       ("dove",            "silver"),
    "law_limited_war":                    ("dove",            "bronze"),

    # ── Intellectual Property ──
    "law_no_ip_protection":               ("lightbulb",       "dark_bronze"),
    "law_creative_commons":               ("lightbulb",       "pale_gold"),
    "law_traditional_ip_protection":      ("lightbulb",       "bronze"),
    "law_strict_ip_protection":           ("lightbulb",       "copper"),
    "law_open_source_innovation":         ("lightbulb",       "silver"),

    # ── Currency & Currency Systems ──
    "law_commodity_money":                ("coin_stack",       "dark_bronze"),
    "law_gold_standard":                  ("coin_stack",       "bronze"),
    "law_fiat_currency":                  ("coin_stack",       "pale_gold"),
    "law_digital_currency":               ("coin_stack",       "silver"),
    "law_decentralized_cryptocurrency":   ("circuit_board",    "silver"),

    # ── Government Information & Transparency ──
    "law_state_secrets":                  ("eye",              "dark_bronze"),
    "law_informal_government_secrecy":    ("eye",              "bronze"),
    "law_freedom_of_information":         ("globe_lines",      "pale_gold"),
    "law_open_government":                ("globe_lines",      "silver"),

    # ── Criminal Justice ──
    "law_punishment_focused_criminal_justice":    ("gavel",    "copper"),
    "law_restorative_justice":                    ("scales",   "pale_gold"),
    "law_rehabilitation_focused_criminal_justice": ("scales",  "silver"),

    # ── Minority Rights (6-tier) ──
    "law_active_persecution":             ("chains",          "copper"),
    "law_legal_limbo":                    ("people",          "dark_bronze"),
    "law_basic_protections":              ("people",          "bronze"),
    "law_comprehensive_rights":           ("people",          "pale_gold"),
    "law_full_equality_and_protection":   ("people",          "silver"),

    # ── Minority Rights (sub-laws) ──
    "law_minority_rights_violent_hostility":     ("chains",    "copper"),
    "law_minority_rights_ghettoization":         ("chains",    "dark_bronze"),
    "law_minority_rights_cultural_assimilation": ("people",    "dark_bronze"),
    "law_minority_rights_discrimination":        ("people",    "copper"),
    "law_minority_rights_indifference":          ("people",    "bronze"),
    "law_minority_rights_protection":            ("people",    "pale_gold"),
    "law_minority_rights_affirmative_action":    ("people",    "silver"),

    # ── Human Augmentation ──
    "law_no_augmentation":                ("robot_head",      "dark_bronze"),
    "law_unrestricted_augmentation":      ("robot_head",      "copper"),
    "law_human_purity":                   ("robot_head",      "bronze"),
    "law_medical_augmentation_only":      ("robot_head",      "pale_gold"),
    "law_regulated_augmentation_market":  ("robot_head",      "silver"),
    "law_mandatory_augmentation":         ("robot_head",      "silver"),

    # ── Government Structure & Federalism ──
    "law_feudal_contracts":               ("crown",           "dark_bronze"),
    "law_unitary_state":                  ("pillar",          "bronze"),
    "law_federal_system":                 ("pillar",          "pale_gold"),
    "law_devolution":                     ("pillar",          "silver"),

    # ── Campaign Finance ──
    "law_no_campaign_finance_laws":       ("ballot_box",      "dark_bronze"),
    "law_unregulated_donations":          ("ballot_box",      "bronze"),
    "law_donation_limits":                ("ballot_box",      "pale_gold"),
    "law_publicly_funded_elections":      ("ballot_box",      "silver"),

    # ── Family & Population Policy ──
    "law_traditional_family_structure":   ("family",          "bronze"),
    "law_pro_natalist_subsidies":         ("family",          "pale_gold"),
    "law_state_sponsored_family_planning": ("family",         "silver"),
    "law_population_control_measures":    ("family",          "copper"),
    "law_communal_child_rearing":         ("family",          "dark_bronze"),

    # ── Banking & Financial Regulation ──
    "law_unregulated_banking":            ("bank",            "dark_bronze"),
    "law_free_mutual_banking":            ("bank",            "bronze"),
    "law_universal_banking_light_prudence": ("bank",          "pale_gold"),
    "law_prudential_narrow_banking":      ("bank",            "silver"),
    "law_directed_credit_development_banks": ("bank",         "copper"),
    "law_central_bank_independence":      ("bank",            "silver"),

    # ── Internet & Digital Policy ──
    "law_no_internet_policy":             ("wifi",            "dark_bronze"),
    "law_unregulated_internet":           ("wifi",            "bronze"),
    "law_state_controlled_internet":      ("wifi",            "copper"),
    "law_net_neutrality":                 ("wifi",            "pale_gold"),

    # ── Genetics & Heredity ──
    "law_traditional_heredity":           ("dna",             "bronze"),
    "law_ban_on_genetic_modification":    ("dna",             "dark_bronze"),
    "law_corporate_genetic_licensing":    ("dna",             "copper"),
    "law_open_source_genetics":           ("dna",             "pale_gold"),
    "law_state_eugenics_program":         ("dna",             "copper"),

    # ── Language Policy ──
    "law_local_vernacular":               ("speech_bubble",   "dark_bronze"),
    "law_civic_monolingualism":           ("speech_bubble",   "bronze"),
    "law_multilingual_federalism":        ("speech_bubble",   "pale_gold"),
    "law_linguistic_purity":              ("speech_bubble",   "copper"),
    "law_state_led_language_reform":      ("speech_bubble",   "silver"),
    "law_ubiquitous_translation":         ("speech_bubble",   "silver"),

    # ── Economic Systems & Trade ──
    "law_guilds_chartered_monopolies":    ("gear_law",        "dark_bronze"),
    "law_freedom_of_contract":            ("handshake",       "bronze"),
    "law_trust_busting":                  ("handshake",       "pale_gold"),
    "law_regulated_utilities":            ("gear_law",        "pale_gold"),
    "law_dirigisme":                      ("gear_law",        "copper"),
    "law_command_cooperative_economy":    ("gear_law",        "silver"),

    # ── Advanced Political Systems ──
    "law_protected_class":                ("people",          "silver"),
    "law_neocameralism":                  ("crown",           "silver"),
    "law_direct_democracy":               ("ballot_box",      "silver"),
    "law_neocolonialism":                 ("globe_lines",     "copper"),
    "law_algorithmic_governance":         ("circuit_board",    "silver"),

    # ── Ministries (active) ──
    "law_ministry_of_foreign_affairs":             ("building_ministry", "bronze"),
    "law_ministry_of_war":                         ("building_ministry", "copper"),
    "law_ministry_of_commerce":                    ("building_ministry", "pale_gold"),
    "law_national_bank":                           ("building_ministry", "bronze"),
    "law_ministry_of_culture":                     ("building_ministry", "pale_gold"),
    "law_pro_labor_ministry_of_labor":             ("building_ministry", "pale_gold"),
    "law_pro_capital_ministry_of_labor":            ("building_ministry", "copper"),
    "law_ministry_of_the_environment":             ("building_ministry", "pale_gold"),
    "law_ministry_of_intelligence_and_security":   ("building_ministry", "copper"),
    "law_ministry_of_refugee_affairs":             ("building_ministry", "pale_gold"),
    "law_ministry_of_propaganda":                  ("building_ministry", "copper"),
    "law_ministry_of_science":                     ("building_ministry", "silver"),
    "law_ministry_of_thought_control":             ("building_ministry", "copper"),
    "law_ministry_of_consumer_protection":         ("building_ministry", "pale_gold"),
    "law_ministry_of_urban_planning":              ("building_ministry", "silver"),
    "law_ministry_of_religion":                    ("building_ministry", "bronze"),
    "law_ministry_of_international_aid":           ("building_ministry", "pale_gold"),

    # ── Ministries (no ministry) ──
    "law_no_ministry_of_foreign_affairs":           ("no_building", "dark_bronze"),
    "law_no_ministry_of_war":                       ("no_building", "dark_bronze"),
    "law_no_ministry_of_commerce":                  ("no_building", "dark_bronze"),
    "law_no_national_bank":                         ("no_building", "dark_bronze"),
    "law_no_ministry_of_culture":                   ("no_building", "dark_bronze"),
    "law_no_ministry_of_labor":                     ("no_building", "dark_bronze"),
    "law_no_ministry_of_the_environment":           ("no_building", "dark_bronze"),
    "law_no_ministry_of_intelligence_and_security": ("no_building", "dark_bronze"),
    "law_no_ministry_of_refugee_affairs":            ("no_building", "dark_bronze"),
    "law_no_ministry_of_propaganda":                ("no_building", "dark_bronze"),
    "law_no_ministry_of_science":                   ("no_building", "dark_bronze"),
    "law_no_ministry_of_thought_control":           ("no_building", "dark_bronze"),
    "law_no_ministry_of_consumer_protection":       ("no_building", "dark_bronze"),
    "law_no_ministry_of_urban_planning":            ("no_building", "dark_bronze"),
    "law_no_ministry_of_religion":                  ("no_building", "dark_bronze"),
    "law_no_ministry_of_international_aid":         ("no_building", "dark_bronze"),
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


# ═══════════════════════════════════════════════════════════════════════════
# ICON GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def icon_filename(law_name: str) -> str:
    """Generate the icon filename for a law (strip 'law_' prefix)."""
    return law_name.removeprefix("law_")


def generate_silhouette(shape_name: str, out_path: Path) -> None:
    """Generate and save a silhouette PNG."""
    draw_fn = SHAPES[shape_name]
    img = draw_fn()
    img.save(out_path, format="PNG")


def generate_all_icons(
    preview_only: bool = False,
    force: bool = False,
) -> dict[str, Path]:
    """Generate all needed law icon DDS files.

    Returns: {law_name: dds_path}
    """
    # Determine unique (shape, color) combos needed
    needed_combos: set[tuple[str, str]] = set()
    for law_name, (shape, color) in LAW_ICON_MAP.items():
        needed_combos.add((shape, color))

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
          f"across {len(needed_combos)} unique (shape, color) combos")

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

        # Generate base silhouette PNGs (one per shape)
        shapes_needed = set(shape for shape, _ in needed_combos)
        silhouettes = {}
        for shape_name in sorted(shapes_needed):
            sil_path = tmpdir / f"sil_{shape_name}.png"
            generate_silhouette(shape_name, sil_path)
            silhouettes[shape_name] = sil_path

        print(f"  Generated {len(silhouettes)} base silhouettes")

        # Cache styled results for (shape, color) combos to avoid recomputation
        # when multiple laws share the same combo
        styled_cache: dict[tuple[str, str], np.ndarray] = {}

        for law_name in sorted(laws_to_generate):
            shape, color = LAW_ICON_MAP[law_name]
            fname = icon_filename(law_name)

            cache_key = (shape, color)
            if cache_key not in styled_cache:
                sil_path = silhouettes[shape]
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

    args = parser.parse_args()

    # Validate all laws in map have valid shapes
    for law_name, (shape, color) in LAW_ICON_MAP.items():
        if shape not in SHAPES:
            print(f"ERROR: Unknown shape '{shape}' for {law_name}")
            sys.exit(1)
        if color not in LAW_COLORS:
            print(f"ERROR: Unknown color '{color}' for {law_name}")
            sys.exit(1)

    if args.dry_run:
        # Show mapping
        print(f"Law icon mapping ({len(LAW_ICON_MAP)} laws):\n")
        by_shape = defaultdict(list)
        for law_name, (shape, color) in sorted(LAW_ICON_MAP.items()):
            by_shape[shape].append((law_name, color))

        for shape, laws in sorted(by_shape.items()):
            print(f"{shape} ({len(laws)} laws):")
            for law_name, color in laws:
                print(f"  {law_name} -> {icon_filename(law_name)}.dds ({color})")
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
