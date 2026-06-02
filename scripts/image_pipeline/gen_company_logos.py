#!/usr/bin/env python3
"""
gen_company_logos.py — generate flat emblem logos for fictional mod companies.

The mod's 58 historical companies use real sourced brand marks; its fictional
(sci-fi) companies fell back to generic basic_*.dds icons (issue #152). Real-world
company logos are often very simple/stylized, so a clean flat emblem — a distinct
geometric mark in a brand colour with a bold monogram — reads convincingly as a
corporate logo and is fully reproducible from this config.

Each logo is rendered at 4× then downscaled (LANCZOS) for crisp anti-aliased edges,
on a transparent canvas (the company panel composites it like the real logos).

Outputs PNGs to scripts/image_pipeline/company_logos_generated/ plus a contact
sheet. Pass --dds to also emit 256×256 BC7 DDS via convert_company_icon.py into
gfx/interface/icons/company_icons/historical_company_icons/.

Usage:
    .venv/bin/python scripts/image_pipeline/gen_company_logos.py            # PNGs + contact sheet
    .venv/bin/python scripts/image_pipeline/gen_company_logos.py --dds      # also wire DDS into gfx/
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parent.parent
OUT_DIR = SCRIPT_DIR / "company_logos_generated"
GFX_DIR = REPO / "gfx/interface/icons/company_icons/historical_company_icons"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

SS = 4               # supersample factor
SIZE = 256
S = SIZE * SS        # working canvas


# company key -> spec. dds_name is the file the company_type icon points to.
SPECS = {
    "company_axiom_space": dict(
        dds_name="scifi_axiom_space", shape="ring", color=(27, 111, 179),
        accent=(120, 200, 240), mono="A", theme="orbit"),
    "company_neurovault": dict(
        dds_name="scifi_neurovault", shape="hexagon", color=(123, 63, 228),
        accent=(200, 170, 255), mono="N", theme="nodes"),
    "company_tycho_manufacturing": dict(
        dds_name="scifi_tycho_manufacturing", shape="gear", color=(214, 108, 28),
        accent=(255, 200, 130), mono="T", theme=None),
    "company_tessier_ashpool": dict(
        dds_name="scifi_tessier_ashpool", shape="shield", color=(20, 28, 48),
        accent=(201, 162, 39), mono="TA", theme="gold_rule"),
    "company_hanka_precision": dict(
        dds_name="scifi_hanka_precision", shape="circle", color=(192, 48, 58),
        accent=(255, 255, 255), mono="H", theme="crosshair"),
    "company_yoyodyne_propulsion": dict(
        dds_name="scifi_yoyodyne_propulsion", shape="chevron", color=(19, 128, 134),
        accent=(170, 230, 230), mono="Y", theme=None),
    "company_rekal": dict(
        dds_name="scifi_rekal", shape="rounded_square", color=(33, 150, 214),
        accent=(190, 235, 255), mono="R", theme="rings"),
}

WHITE = (255, 255, 255, 255)


def _font(px):
    return ImageFont.truetype(FONT_BOLD, px)


def _poly_regular(cx, cy, r, n, rot=0.0):
    return [(cx + r * math.cos(rot + 2 * math.pi * i / n),
             cy + r * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)]


def _draw_mono(d, text, color, box, font_frac=0.5):
    cx, cy = S / 2, S / 2
    fpx = int(S * font_frac / max(1, len(text) ** 0.5))
    font = _font(fpx)
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    d.text((cx - (r + l) / 2, cy - (b + t) / 2), text, font=font, fill=color)


def render(spec) -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = S / 2, S / 2
    R = S * 0.42
    col = spec["color"] + (255,)
    acc = spec["accent"] + (255,)
    shape = spec["shape"]
    theme = spec.get("theme")

    if shape == "circle":
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=col)
    elif shape == "ring":
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=col)
        hole = R * 0.46
        d.ellipse([cx - hole, cy - hole, cx + hole, cy + hole], fill=(0, 0, 0, 0))
    elif shape == "rounded_square":
        rad = R * 0.42
        d.rounded_rectangle([cx - R, cy - R, cx + R, cy + R], radius=rad, fill=col)
    elif shape == "hexagon":
        d.polygon(_poly_regular(cx, cy, R, 6, rot=-math.pi / 2), fill=col)
    elif shape == "diamond":
        d.polygon(_poly_regular(cx, cy, R, 4, rot=-math.pi / 2), fill=col)
    elif shape == "shield":
        w = R * 0.92
        top = cy - R
        pts = [(cx - w, top), (cx + w, top), (cx + w, cy + R * 0.15),
               (cx, cy + R), (cx - w, cy + R * 0.15)]
        d.polygon(pts, fill=col)
    elif shape == "chevron":
        # upward thrust block
        d.polygon([(cx, cy - R), (cx + R, cy + R * 0.55), (cx + R * 0.45, cy + R * 0.55),
                   (cx, cy - R * 0.1), (cx - R * 0.45, cy + R * 0.55),
                   (cx - R, cy + R * 0.55)], fill=col)
    elif shape == "gear":
        teeth = 12
        outer, inner = R, R * 0.82
        pts = []
        for i in range(teeth * 2):
            rr = outer if i % 2 == 0 else inner
            a = math.pi * i / teeth - math.pi / 2
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=col)
        hub = R * 0.30
        d.ellipse([cx - hub, cy - hub, cx + hub, cy + hub], fill=(0, 0, 0, 0))

    # thematic accents
    if theme == "orbit":
        lw = int(S * 0.018)
        bb = R * 1.18
        d.arc([cx - bb, cy - bb * 0.62, cx + bb, cy + bb * 0.62], 200, 20, fill=acc, width=lw)
        dot = R * 0.10
        d.ellipse([cx + bb - dot, cy - dot, cx + bb + dot, cy + dot], fill=acc)
    elif theme == "nodes":
        for v in _poly_regular(cx, cy, R * 0.66, 6, rot=-math.pi / 2):
            dr = R * 0.085
            d.ellipse([v[0] - dr, v[1] - dr, v[0] + dr, v[1] + dr], fill=acc)
    elif theme == "crosshair":
        lw = int(S * 0.02)
        for a in (0, 90, 180, 270):
            x2 = cx + R * 1.02 * math.cos(math.radians(a))
            y2 = cy + R * 1.02 * math.sin(math.radians(a))
            x1 = cx + R * 0.55 * math.cos(math.radians(a))
            y1 = cy + R * 0.55 * math.sin(math.radians(a))
            d.line([x1, y1, x2, y2], fill=acc, width=lw)
    elif theme == "rings":
        lw = int(S * 0.016)
        for rr in (R * 0.74, R * 0.86):
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=acc, width=lw)
    elif theme == "gold_rule":
        lw = int(S * 0.022)
        d.line([cx - R * 0.55, cy + R * 0.45, cx + R * 0.55, cy + R * 0.45], fill=acc, width=lw)

    # monogram
    mono_col = acc if shape == "shield" else WHITE
    _draw_mono(d, spec["mono"], mono_col, None,
               font_frac=0.62 if len(spec["mono"]) == 1 else 0.46)

    return img.resize((SIZE, SIZE), Image.LANCZOS)


def contact_sheet(images: dict) -> Image.Image:
    cols = 4
    rows = math.ceil(len(images) / cols)
    pad, cell = 16, SIZE
    label_h = 22
    W = cols * (cell + pad) + pad
    H = rows * (cell + label_h + pad) + pad
    sheet = Image.new("RGBA", (W, H), (245, 245, 248, 255))
    d = ImageDraw.Draw(sheet)
    f = _font(16)
    for i, (name, im) in enumerate(images.items()):
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad)
        y = pad + r * (cell + label_h + pad)
        # checker so transparency is visible
        chk = Image.new("RGBA", (cell, cell), (220, 220, 224, 255))
        cd = ImageDraw.Draw(chk)
        for yy in range(0, cell, 16):
            for xx in range(0, cell, 16):
                if (xx // 16 + yy // 16) % 2:
                    cd.rectangle([xx, yy, xx + 16, yy + 16], fill=(235, 235, 240, 255))
        chk.alpha_composite(im)
        sheet.paste(chk, (x, y))
        short = name.replace("company_", "")
        d.text((x, y + cell + 3), short, font=f, fill=(30, 30, 30))
    return sheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dds", action="store_true", help="also emit BC7 DDS into gfx/ via convert_company_icon.py")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    images = {}
    for name, spec in SPECS.items():
        im = render(spec)
        png = OUT_DIR / f"{spec['dds_name']}.png"
        im.save(png)
        images[name] = im
        print(f"  rendered {png.name}")

    sheet = contact_sheet(images)
    sheet_path = OUT_DIR / "_contact_sheet.png"
    sheet.convert("RGB").save(sheet_path)
    print(f"\nContact sheet: {sheet_path}")

    if args.dds:
        conv = SCRIPT_DIR / "convert_company_icon.py"
        for name, spec in SPECS.items():
            png = OUT_DIR / f"{spec['dds_name']}.png"
            out = GFX_DIR / f"{spec['dds_name']}.dds"
            print(f"\nConverting {spec['dds_name']} -> {out}")
            subprocess.run([sys.executable, str(conv), str(png), "-o", str(out)], check=True)


if __name__ == "__main__":
    main()
