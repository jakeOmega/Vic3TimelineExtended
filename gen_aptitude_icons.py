#!/usr/bin/env python3
"""
gen_aptitude_icons.py - Generate ruler aptitude trait icons for Vic3TimelineExtended.

Produces 15 DDS icons (5 tiers × 3 categories):
  - Tier 1 (terrible):     ↓↓  two down arrows
  - Tier 2 (poor):         ↓   one down arrow
  - Tier 3 (average):      —   dash
  - Tier 4 (skilled):      ↑   one up arrow
  - Tier 5 (exceptional):  ↑↑  two up arrows

Category tints: Admin=blue, Diplomacy=green, Military=red.
Center glow effect, brighter for higher tiers.

Uses the border/frame from vanilla trait icons and texconv for DDS conversion.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ── paths ────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
VANILLA_TRAITS = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3"
    r"\game\gfx\interface\icons\character_trait_icons"
)
OUTPUT_DIR = SCRIPT_DIR / "gfx" / "interface" / "icons" / "character_trait_icons"

# Icons to compare for border extraction
REFERENCE_ICONS = [
    "ambitious.dds", "reserved.dds", "cruel.dds", "brave.dds",
    "meticulous.dds", "charismatic.dds", "wrathful.dds", "arrogant.dds",
    "direct.dds", "tactful.dds", "imposing.dds", "cautious.dds",
]

# ── icon dimensions ──────────────────────────────────────────────────────
W, H = 240, 320

# ── category colors (R, G, B) ───────────────────────────────────────────
COLORS = {
    "admin":    (80, 140, 230),   # blue
    "diplo":    (80, 200, 120),   # green
    "military": (220, 80, 80),    # red
}

# ── tier config ──────────────────────────────────────────────────────────
# (tier_index, symbol_text, glow_strength)
TIERS = [
    (1, "terrible",     "↓↓", 0.0),
    (2, "poor",         "↓",  0.15),
    (3, "average",      "—",  0.30),
    (4, "skilled",      "↑",  0.55),
    (5, "exceptional",  "↑↑", 0.85),
]

# ── trait key -> output filename mapping ─────────────────────────────────
TRAIT_MAP = {
    ("admin", 1): "ruler_terrible_administrator",
    ("admin", 2): "ruler_poor_administrator",
    ("admin", 3): "ruler_average_administrator",
    ("admin", 4): "ruler_skilled_administrator",
    ("admin", 5): "ruler_exceptional_administrator",
    ("diplo", 1): "ruler_terrible_diplomat",
    ("diplo", 2): "ruler_poor_diplomat",
    ("diplo", 3): "ruler_average_diplomat",
    ("diplo", 4): "ruler_skilled_diplomat",
    ("diplo", 5): "ruler_exceptional_diplomat",
    ("military", 1): "ruler_terrible_commander",
    ("military", 2): "ruler_poor_commander",
    ("military", 3): "ruler_average_commander",
    ("military", 4): "ruler_skilled_commander",
    ("military", 5): "ruler_exceptional_commander",
}


def make_content_mask() -> np.ndarray:
    """Content area is the UNION of two rectangles (inclusive pixel coords).

    Rect 1: top-left (40, 14)  bottom-right (199, 302)  [x, y]
    Rect 2: top-left (21, 30)  bottom-right (218, 285)

    Everything inside EITHER rectangle = content (will be replaced).
    Everything outside BOTH = frame (kept from vanilla).
    """
    mask = np.zeros((H, W), dtype=bool)
    # Rect 1: x in [40, 199], y in [14, 302]
    mask[14:303, 40:200] = True
    # Rect 2: x in [21, 218], y in [30, 285]
    mask[30:286, 21:219] = True
    return mask


def extract_border(content_mask: np.ndarray) -> np.ndarray:
    """Extract frame pixels from a vanilla trait icon.

    All content-area pixels (inside the union rectangle) are zeroed out
    (fully transparent) so only the decorative frame remains.
    """
    for name in REFERENCE_ICONS:
        path = VANILLA_TRAITS / name
        if path.exists():
            arr = np.array(Image.open(path).convert("RGBA"))
            border = arr.copy()
            border[content_mask] = [0, 0, 0, 0]
            return border
    raise RuntimeError("No reference icons found in " + str(VANILLA_TRAITS))


def find_font(size: int) -> ImageFont.FreeTypeFont:
    """Find a suitable font for drawing arrow symbols."""
    # Try several fonts that render arrows well
    candidates = [
        "seguisym.ttf",   # Segoe UI Symbol - good arrows
        "segoeui.ttf",    # Segoe UI
        "arial.ttf",
        "calibri.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue

    # Fallback: default font (won't be great but works)
    return ImageFont.load_default()


def create_glow(w: int, h: int, cx: int, cy: int, strength: float) -> np.ndarray:
    """Create a radial glow mask centered at (cx, cy).

    Returns float array (H, W) in [0, 1].
    """
    y, x = np.ogrid[:h, :w]
    # Elliptical distance normalized to 0-1
    dx = (x - cx) / (w * 0.4)
    dy = (y - cy) / (h * 0.4)
    dist = np.sqrt(dx ** 2 + dy ** 2)
    glow = np.clip(1.0 - dist, 0, 1) ** 1.5  # soft falloff
    return glow * strength


def generate_icon(
    border: np.ndarray,
    content_mask: np.ndarray,
    category: str,
    tier: int,
    symbol: str,
    glow_strength: float,
) -> Image.Image:
    """Generate a single aptitude trait icon."""
    r, g, b = COLORS[category]

    # ── 1. Create the content fill ──
    # Dark base with category tint
    content = np.zeros((H, W, 4), dtype=np.uint8)

    # Dark tinted background for content area
    bg_r = int(r * 0.15)
    bg_g = int(g * 0.15)
    bg_b = int(b * 0.15)
    content[content_mask] = [bg_r, bg_g, bg_b, 255]

    # ── 2. Apply center glow ──
    cx, cy = W // 2, H // 2
    glow = create_glow(W, H, cx, cy, glow_strength)

    # Add glow as lightening of the background
    content_f = content.astype(np.float64)
    for ch, base_c in enumerate([r, g, b]):
        channel = content_f[:, :, ch]
        # Blend toward the category color based on glow
        channel[content_mask] += glow[content_mask] * (base_c - channel[content_mask]) * 0.7
        # Also add some white for brightness
        channel[content_mask] += glow[content_mask] * (255 - channel[content_mask]) * 0.3
        content_f[:, :, ch] = channel

    content = np.clip(content_f, 0, 255).astype(np.uint8)

    # ── 3. Draw the arrow symbol ──
    content_img = Image.fromarray(content)
    draw = ImageDraw.Draw(content_img)

    # Find good font size - arrows should be prominent
    if len(symbol) == 2:
        font_size = 90
    else:
        font_size = 110

    font = find_font(font_size)

    # Measure text
    bbox = draw.textbbox((0, 0), symbol, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Center the symbol in the union content area.
    # Content union bounds: x in [21,218], y in [14,302]
    # Union center: cx=119, cy=158
    cx_content = (21 + 218) // 2   # 119
    cy_content = (14 + 302) // 2   # 158
    tx = cx_content - (bbox[0] + bbox[2]) // 2
    ty = cy_content - (bbox[1] + bbox[3]) // 2

    # Draw drop shadow
    shadow_color = (0, 0, 0, 180)
    draw.text((tx + 2, ty + 2), symbol, fill=shadow_color, font=font)

    # Draw black stroke — 8 surrounding offsets at 1 px
    black = (0, 0, 0, 230)
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            if ox == 0 and oy == 0:
                continue
            draw.text((tx + ox, ty + oy), symbol, fill=black, font=font)

    # Draw the symbol in silver
    symbol_color = (210, 210, 220, 255)
    draw.text((tx, ty), symbol, fill=symbol_color, font=font)

    # Metallic shine: vertical cosine-banding highlight over the symbol
    sym_top = ty + bbox[1]
    sym_bot = ty + bbox[3]
    sym_height = max(sym_bot - sym_top, 1)

    # Render symbol as a white alpha mask
    shine_mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shine_mask).text((tx, ty), symbol, fill=255, font=font)
    shine_arr = np.array(shine_mask).astype(np.float64) / 255.0

    # Vertical gradient: 2.5 cosine cycles → bright/dark/bright/dark banding
    ys = np.arange(H, dtype=np.float64)
    t = (ys - sym_top) / sym_height          # 0..1 over the symbol height
    grad_1d = 0.55 + 0.45 * np.cos(t * np.pi * 2.5)
    grad_2d = np.clip(grad_1d, 0.0, 1.0)[:, np.newaxis] * np.ones((1, W))

    # White highlight layer, masked to symbol shape with gradient strength
    shine_alpha = (shine_arr * grad_2d * 180.0).astype(np.uint8)
    shine_layer = np.zeros((H, W, 4), dtype=np.uint8)
    shine_layer[:, :, :3] = 255
    shine_layer[:, :, 3] = shine_alpha
    content_img = Image.alpha_composite(content_img, Image.fromarray(shine_layer))

    # Slight outer glow on the symbol - draw it slightly larger behind
    # (We'll just draw it blurred)
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_color = (r, g, b, 120)
    glow_draw.text((tx, ty), symbol, fill=glow_color, font=font)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=4))

    # Composite glow behind symbol
    content_arr = np.array(content_img)
    glow_arr = np.array(glow_layer)

    # Alpha composite the glow
    for ch in range(3):
        ga = glow_arr[:, :, 3].astype(np.float64) / 255.0
        ca = content_arr[:, :, 3].astype(np.float64) / 255.0
        # Only apply glow where content mask is True
        mask = content_mask & (ga > 0.01)
        blended = (glow_arr[:, :, ch].astype(np.float64) * ga +
                   content_arr[:, :, ch].astype(np.float64) * (1 - ga * 0.3))
        content_arr[:, :, ch][mask] = np.clip(blended[mask], 0, 255).astype(np.uint8)

    # ── 4. Composite border on top ──
    result = content_arr.copy()

    # Overlay border pixels (they have alpha for blending)
    border_alpha = border[:, :, 3].astype(np.float64) / 255.0
    for ch in range(3):
        result[:, :, ch] = np.clip(
            border[:, :, ch] * border_alpha +
            result[:, :, ch] * (1 - border_alpha),
            0, 255,
        ).astype(np.uint8)
    # Alpha: max of border and content
    result[:, :, 3] = np.maximum(border[:, :, 3], content_arr[:, :, 3])

    return Image.fromarray(result)


def find_texconv() -> Path | None:
    """Find texconv.exe (from convert_event_image.py's location or PATH)."""
    local = SCRIPT_DIR / "texconv.exe"
    if local.is_file():
        return local
    found = shutil.which("texconv") or shutil.which("texconv.exe")
    if found:
        return Path(found)
    return None


def convert_to_dds(png_path: Path, dds_path: Path, texconv: Path) -> None:
    """Convert a PNG to BC7 DDS using texconv."""
    cmd = [
        str(texconv),
        "-f", "BC7_UNORM_SRGB",
        "-y",
        "-srgb",
        "-o", str(dds_path.parent),
        str(png_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  texconv error: {result.stderr}")
        raise RuntimeError(f"texconv failed for {png_path}")

    # texconv outputs with the input's stem name
    produced = dds_path.parent / (png_path.stem + ".dds")
    if produced != dds_path:
        if dds_path.exists():
            dds_path.unlink()
        produced.rename(dds_path)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Building content mask from rectangle definitions...")
    content_mask = make_content_mask()
    print("Extracting border frame from vanilla trait icon...")
    border = extract_border(content_mask)

    texconv = find_texconv()
    if texconv is None:
        # Try to download via the existing helper
        sys.path.insert(0, str(SCRIPT_DIR))
        from convert_event_image import ensure_texconv
        texconv = ensure_texconv()

    print(f"Using texconv: {texconv}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    for category in ["admin", "diplo", "military"]:
        for tier_idx, tier_name, symbol, glow in TIERS:
            trait_key = TRAIT_MAP[(category, tier_idx)]
            print(f"  Generating {trait_key} ({symbol})...")

            icon = generate_icon(border, content_mask, category, tier_idx, symbol, glow)

            # Save intermediate PNG
            png_path = OUTPUT_DIR / f"{trait_key}.png"
            icon.save(png_path, format="PNG")

            # Convert to DDS
            dds_path = OUTPUT_DIR / f"{trait_key}.dds"
            convert_to_dds(png_path, dds_path, texconv)
            print(f"    -> {dds_path.name} ({dds_path.stat().st_size:,} bytes)")

            # Clean up PNG
            png_path.unlink()

    print()
    print(f"Done! Generated 15 icons in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
