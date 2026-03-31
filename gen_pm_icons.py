#!/usr/bin/env python3
"""
gen_pm_icons.py - Generate production method icons in vanilla Victoria 3 style.

Takes a silhouette image (black shape on white/transparent background) and
applies the vanilla metallic embossed styling with configurable color tint.

Usage:
    python gen_pm_icons.py <input_image> <output_name> [--color COLOR] [--size SIZE]

    input_image:  Path to a silhouette PNG (black shape on white/transparent)
    output_name:  Output filename without extension (e.g. "my_pm_icon")
    --color:      Color preset: gold, red, green, purple, blue, teal, orange, grey
                  Or a custom hex color like "#8B4513" (default: gold)
    --size:       Output size in pixels: 104 or 208 (default: 104)
    --no-outline: Skip the dark outline pass

Examples:
    python gen_pm_icons.py silhouettes/rocket.png rocket_engines --color purple --size 208
    python gen_pm_icons.py silhouettes/gear.png advanced_gears --color gold
    python gen_pm_icons.py silhouettes/atom.png nuclear_fission --color blue

Batch mode:
    python gen_pm_icons.py --batch batch_config.json

    Where batch_config.json is:
    [
        {"input": "silhouettes/rocket.png", "output": "rocket_engines", "color": "purple"},
        {"input": "silhouettes/gear.png",   "output": "advanced_gears", "color": "gold"}
    ]

The output DDS is placed in gfx/interface/icons/production_method_icons/.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

# ── paths ────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "gfx" / "interface" / "icons" / "production_method_icons"

# ── color presets (matched from vanilla icon analysis) ───────────────────
# These are the *mid-tone* base colors.  The emboss pipeline generates
# lighter highlights and darker shadows around these values.
COLOR_PRESETS: dict[str, tuple[int, int, int]] = {
    "gold":    (170, 147, 107),   # warm brass/gold  (vanilla default)
    "red":     (168,  84,  78),   # military red
    "green":   (110, 140,  82),   # industrial olive-green
    "purple":  (152, 108, 158),   # innovation purple
    "blue":    ( 90, 130, 175),   # cool blue
    "teal":    ( 85, 155, 145),   # teal/cyan
    "orange":  (180, 120,  65),   # warm orange
    "grey":    (130, 130, 135),   # neutral steel grey
}

# ── lighting parameters ──────────────────────────────────────────────────
LIGHT_DIR = np.array([-0.6, -0.6, 0.6])   # upper-left, slightly forward
LIGHT_DIR = LIGHT_DIR / np.linalg.norm(LIGHT_DIR)

AMBIENT = 0.35          # base ambient light level
DIFFUSE_STRENGTH = 0.55 # Lambertian diffuse
SPEC_STRENGTH = 0.25    # specular highlight
SPEC_POWER = 12.0       # specular exponent (tightness)

BEVEL_DEPTH = 3.5       # how far the distance field extends inward
OUTLINE_WIDTH = 2       # dark outline in pixels
NOISE_AMOUNT = 0.06     # grain texture intensity
EDGE_DARKEN = 0.7       # how much darker the outermost edge pixels are


def parse_color(color_str: str) -> tuple[int, int, int]:
    """Parse a color preset name or hex code."""
    color_str = color_str.lower().strip()
    if color_str in COLOR_PRESETS:
        return COLOR_PRESETS[color_str]
    # Try hex
    c = color_str.lstrip("#")
    if len(c) == 6:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    raise ValueError(f"Unknown color: {color_str!r}. Use a preset ({', '.join(COLOR_PRESETS)}) or hex (#RRGGBB).")


def load_silhouette(path: Path, target_size: int) -> np.ndarray:
    """Load an input image and extract a binary silhouette mask.

    Returns a float array (size, size) in [0, 1] where 1 = shape interior.
    The image is resized to target_size with padding to preserve aspect ratio.
    """
    img = Image.open(path).convert("RGBA")

    # Determine the shape mask: if the image has meaningful alpha, use it;
    # otherwise threshold luminance (black = shape)
    arr = np.array(img)
    alpha = arr[:, :, 3]

    if alpha.min() < 200:
        # Alpha-based: shape is wherever alpha > 50%
        raw_mask = alpha.astype(np.float64) / 255.0
    else:
        # Luminance-based: dark pixels = shape
        lum = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2])
        raw_mask = 1.0 - (lum / 255.0)

    # Resize to fit within target_size with some padding (85% fill)
    mask_img = Image.fromarray((raw_mask * 255).astype(np.uint8), mode="L")
    h, w = raw_mask.shape
    fill = int(target_size * 0.85)
    scale = fill / max(h, w)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    mask_img = mask_img.resize((new_w, new_h), Image.LANCZOS)

    # Center on target canvas
    canvas = Image.new("L", (target_size, target_size), 0)
    ox = (target_size - new_w) // 2
    oy = (target_size - new_h) // 2
    canvas.paste(mask_img, (ox, oy))

    result = np.array(canvas).astype(np.float64) / 255.0

    # Slight threshold to clean up anti-aliasing fuzz
    result = np.clip((result - 0.15) / 0.85, 0, 1)
    return result


def compute_distance_field(mask: np.ndarray) -> np.ndarray:
    """Compute an approximate distance field from the mask edges.

    Returns float (H, W) where 0 = edge, positive = interior depth.
    """
    from scipy.ndimage import distance_transform_edt

    binary = (mask > 0.5).astype(np.float64)
    dist = distance_transform_edt(binary)
    return dist


def compute_normals(heightmap: np.ndarray) -> np.ndarray:
    """Compute surface normals from a heightmap using Sobel filters.

    Returns (H, W, 3) float array of unit normals.
    """
    from scipy.ndimage import sobel

    # Gradient in x and y
    dx = sobel(heightmap, axis=1, mode="constant")
    dy = sobel(heightmap, axis=0, mode="constant")

    # Normal = (-dx, -dy, 1), normalized
    normals = np.zeros((*heightmap.shape, 3), dtype=np.float64)
    normals[:, :, 0] = -dx
    normals[:, :, 1] = -dy
    normals[:, :, 2] = 1.0

    length = np.sqrt(np.sum(normals ** 2, axis=2, keepdims=True))
    length = np.maximum(length, 1e-8)
    normals /= length

    return normals


def apply_metallic_style(
    mask: np.ndarray,
    base_color: tuple[int, int, int],
    add_outline: bool = True,
) -> np.ndarray:
    """Apply the vanilla metallic embossed style to a silhouette mask.

    Args:
        mask:       float (H, W) in [0, 1], 1 = shape
        base_color: (R, G, B) mid-tone color
        add_outline: whether to add a dark outline

    Returns:
        RGBA uint8 array (H, W, 4)
    """
    H, W = mask.shape

    # ── 1. Distance field & heightmap ──
    dist = compute_distance_field(mask)
    # Clamp distance to bevel depth, normalize to [0, 1]
    height = np.clip(dist / BEVEL_DEPTH, 0, 1)

    # ── 2. Surface normals ──
    normals = compute_normals(height)

    # ── 3. Lighting calculation ──
    # Lambertian diffuse
    n_dot_l = np.sum(normals * LIGHT_DIR[np.newaxis, np.newaxis, :], axis=2)
    diffuse = np.clip(n_dot_l, 0, 1)

    # Blinn-Phong specular
    view_dir = np.array([0.0, 0.0, 1.0])
    half_vec = LIGHT_DIR + view_dir
    half_vec = half_vec / np.linalg.norm(half_vec)
    n_dot_h = np.sum(normals * half_vec[np.newaxis, np.newaxis, :], axis=2)
    specular = np.clip(n_dot_h, 0, 1) ** SPEC_POWER

    # Combined illumination
    illum = AMBIENT + DIFFUSE_STRENGTH * diffuse + SPEC_STRENGTH * specular

    # ── 4. Edge darkening (outline-adjacent pixels are darker) ──
    edge_factor = np.clip(dist / 4.0, 0, 1)
    edge_factor = EDGE_DARKEN + (1.0 - EDGE_DARKEN) * edge_factor
    illum *= edge_factor

    # ── 5. Subtle top-to-bottom gradient (simulates environment reflection) ──
    y_grad = np.linspace(1.05, 0.90, H)[:, np.newaxis] * np.ones((1, W))
    illum *= y_grad

    # ── 6. Noise/grain texture ──
    rng = np.random.default_rng(42)
    noise = 1.0 + (rng.standard_normal((H, W)) * NOISE_AMOUNT)
    illum *= noise

    # Clamp
    illum = np.clip(illum, 0, 1.5)

    # ── 7. Apply color ──
    r, g, b = base_color
    rgb = np.zeros((H, W, 3), dtype=np.float64)
    rgb[:, :, 0] = r * illum
    rgb[:, :, 1] = g * illum
    rgb[:, :, 2] = b * illum
    rgb = np.clip(rgb, 0, 255)

    # ── 8. Dark outline ──
    if add_outline:
        # Dilate the mask, then the outline is dilated - original
        from scipy.ndimage import binary_dilation

        binary_mask = mask > 0.5
        struct = np.ones((OUTLINE_WIDTH * 2 + 1, OUTLINE_WIDTH * 2 + 1))
        dilated = binary_dilation(binary_mask, structure=struct)
        outline_mask = dilated & ~binary_mask

        # Dark outline color (very dark version of base)
        outline_r = max(0, r // 5 - 10)
        outline_g = max(0, g // 5 - 10)
        outline_b = max(0, b // 5 - 10)
        rgb[outline_mask, 0] = outline_r
        rgb[outline_mask, 1] = outline_g
        rgb[outline_mask, 2] = outline_b

    # ── 9. Build RGBA output ──
    result = np.zeros((H, W, 4), dtype=np.uint8)
    result[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)

    # Alpha: shape + outline, with anti-aliased edges
    shape_alpha = np.clip(mask * 2.0, 0, 1)  # sharpen edges slightly
    if add_outline:
        outline_alpha = dilated.astype(np.float64)
        combined_alpha = np.maximum(shape_alpha, outline_alpha * 0.95)
    else:
        combined_alpha = shape_alpha
    result[:, :, 3] = (combined_alpha * 255).astype(np.uint8)

    return result


def find_texconv() -> Path | None:
    """Find texconv.exe."""
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

    produced = dds_path.parent / (png_path.stem + ".dds")
    if produced != dds_path:
        if dds_path.exists():
            dds_path.unlink()
        produced.rename(dds_path)


def generate_pm_icon(
    input_path: Path,
    output_name: str,
    color: tuple[int, int, int],
    size: int,
    add_outline: bool,
    texconv: Path,
) -> Path:
    """Generate a single PM icon from a silhouette.

    Returns the path to the output DDS file.
    """
    # Load and process silhouette
    mask = load_silhouette(input_path, size)

    # Apply metallic style
    result = apply_metallic_style(mask, color, add_outline)

    # Save as PNG then convert to DDS
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    png_path = OUTPUT_DIR / f"{output_name}.png"
    dds_path = OUTPUT_DIR / f"{output_name}.dds"

    Image.fromarray(result).save(png_path, format="PNG")
    convert_to_dds(png_path, dds_path, texconv)
    png_path.unlink()

    return dds_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate PM icons in vanilla Victoria 3 style from silhouettes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Color presets: {', '.join(COLOR_PRESETS.keys())}",
    )
    parser.add_argument("input", nargs="?", help="Input silhouette image path")
    parser.add_argument("output", nargs="?", help="Output name (without .dds)")
    parser.add_argument("--color", default="gold", help="Color preset or hex (#RRGGBB)")
    parser.add_argument("--size", type=int, default=104, choices=[104, 208], help="Icon size")
    parser.add_argument("--no-outline", action="store_true", help="Skip dark outline")
    parser.add_argument("--batch", help="Path to batch config JSON file")
    parser.add_argument("--keep-png", action="store_true", help="Keep intermediate PNG files")

    args = parser.parse_args()

    # Find texconv
    texconv = find_texconv()
    if texconv is None:
        sys.path.insert(0, str(SCRIPT_DIR))
        from convert_event_image import ensure_texconv
        texconv = ensure_texconv()
    print(f"Using texconv: {texconv}")

    if args.batch:
        # Batch mode
        batch_path = Path(args.batch)
        with open(batch_path) as f:
            items = json.load(f)

        print(f"Batch processing {len(items)} icons...")
        for item in items:
            input_path = Path(item["input"])
            if not input_path.is_absolute():
                input_path = SCRIPT_DIR / input_path
            output_name = item["output"]
            color = parse_color(item.get("color", "gold"))
            size = item.get("size", 104)
            outline = not item.get("no_outline", False)

            print(f"  {output_name} ({input_path.name}, {color})...")
            dds = generate_pm_icon(input_path, output_name, color, size, outline, texconv)
            print(f"    -> {dds.name} ({dds.stat().st_size:,} bytes)")

    elif args.input and args.output:
        # Single icon mode
        input_path = Path(args.input)
        if not input_path.is_absolute():
            input_path = SCRIPT_DIR / input_path
        color = parse_color(args.color)
        outline = not args.no_outline

        print(f"Generating {args.output} from {input_path.name}...")
        print(f"  Color: {color}, Size: {args.size}x{args.size}, Outline: {outline}")
        dds = generate_pm_icon(input_path, args.output, color, args.size, outline, texconv)
        print(f"  -> {dds.name} ({dds.stat().st_size:,} bytes)")

    else:
        parser.print_help()
        sys.exit(1)

    print("Done!")


if __name__ == "__main__":
    main()
