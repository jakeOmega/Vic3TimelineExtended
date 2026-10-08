#!/usr/bin/env python3
"""
gen_placeholder_company_icons.py - Generate CLEARLY-LABELED placeholder company
icons for newly-added flavored companies / company-unique buildings.

These are deliberate stand-ins, NOT real logos: each renders the company name on
an industry-tinted field with a bold "PLACEHOLDER" banner so it is unmistakable
in-game that art is still pending. Output is a 256×256 BC7 DDS produced via the
shared convert_company_icon.convert() pipeline (texconv.exe).

Usage:
    .venv/bin/python scripts/image_pipeline/gen_placeholder_company_icons.py
    .venv/bin/python scripts/image_pipeline/gen_placeholder_company_icons.py \
        --only american_genentech chinese_bgi --uncompressed

--only regenerates just the named stems, leaving the other icons untouched.
--uncompressed writes uncompressed BGRA via icon_dds.write_dds instead of BC7
through texconv.exe, for machines that cannot run the Windows binary (a Linux
container); the files are about four times larger.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from convert_company_icon import convert, ensure_texconv  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parent.parent
ICON_DIR = REPO_ROOT / "gfx/interface/icons/company_icons/historical_company_icons"
SIZE = 256

# (output_stem, display label, industry tint RGB). Empty: the icon pipeline's company_logo
# category replaced all eighteen cards on 2026-10-07 (icon batch 3, #813), and
# a rerun would write the cards back over the art. Add a stem here only for a
# new company still waiting for its logo.
ICONS: list[tuple[str, str, tuple[int, int, int]]] = []


def _font(size: int):
    """A truetype font if available, else the (scalable) bitmap default."""
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


def _draw_centered(draw, text, font, cy, fill, w):
    bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center", spacing=4)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.multiline_text(
        ((w - tw) / 2 - bbox[0], cy - th / 2 - bbox[1]),
        text, font=font, fill=fill, align="center", spacing=4,
    )


def make_placeholder(label: str, tint: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), tint + (255,))
    draw = ImageDraw.Draw(img)
    # Dashed border to read as "draft".
    for i in range(0, SIZE, 16):
        draw.rectangle([i, 6, i + 8, 12], fill=(255, 255, 255, 230))
        draw.rectangle([i, SIZE - 12, i + 8, SIZE - 6], fill=(255, 255, 255, 230))
    # Company name (upper half).
    _draw_centered(draw, label, _font(34), 86, (255, 255, 255, 255), SIZE)
    # PLACEHOLDER banner (lower half) on a contrasting bar.
    draw.rectangle([0, 150, SIZE, 206], fill=(0, 0, 0, 170))
    _draw_centered(draw, "PLACEHOLDER", _font(28), 178, (255, 210, 70, 255), SIZE)
    _draw_centered(draw, "art pending", _font(18), 224, (235, 235, 235, 255), SIZE)
    return img


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--only", nargs="+", metavar="STEM", help="regenerate only these output stems")
    p.add_argument("--uncompressed", action="store_true",
                   help="write uncompressed BGRA (icon_dds) instead of BC7 via texconv.exe")
    args = p.parse_args()
    icons = ICONS
    if args.only:
        unknown = set(args.only) - {stem for stem, _, _ in ICONS}
        if unknown:
            p.error(f"unknown stem(s): {', '.join(sorted(unknown))}")
        icons = [icon for icon in ICONS if icon[0] in args.only]
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    if args.uncompressed:
        from icon_dds import write_dds
        for stem, label, tint in icons:
            out = ICON_DIR / f"{stem}.dds"
            write_dds(make_placeholder(label, tint), out)
            print(f"  -> {out.relative_to(REPO_ROOT)}")
        print(f"Done: {len(icons)} placeholder icons.")
        return
    texconv = ensure_texconv()
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        for stem, label, tint in icons:
            png = Path(tmp) / f"{stem}.png"
            make_placeholder(label, tint).save(png, format="PNG")
            out = ICON_DIR / f"{stem}.dds"
            convert(png, out, texconv)
            print(f"  -> {out.relative_to(REPO_ROOT)}")
    print(f"Done: {len(icons)} placeholder icons.")


if __name__ == "__main__":
    main()
