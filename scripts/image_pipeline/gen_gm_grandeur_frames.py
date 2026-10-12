#!/usr/bin/env python3
"""
gen_gm_grandeur_frames.py - the Grand Monument pictures' grandeur frames.

Each monument's picture (gm_pictures/<skin>__<form>.dds, the gm_picture type in
grand_monuments_widget.gui) is a building-icon diorama: a full-bleed scene
inside the frame band of vanilla's building icons, which icon_render.compose_framed
lifts as the edge of the folder's median icon. These overlays recolour that band
by the monument's grandeur step (spec 2026-10-11 §3.5; gm_disp_frame_tier):

  tier 1  bronze                       (grandeur 5-14)
  tier 2  bronze, silver inner band   (15-34)
  tier 3  silver, gold inner band     (35-74)
  tier 4  gold                         (75-154)
  tier 5  gold, four gem studs         (155+)

The band is the baked frame widened by a few pixels (BAND) so the metal still
reads at 96 px; its shading is vanilla's frame luminance where the baked frame
is, mixed with a drawn bevel profile across the whole band. Each metal is a
three-stop gradient map over that luminance. Tier 0 draws no overlay.

    .venv-img/bin/python scripts/image_pipeline/gen_gm_grandeur_frames.py --sheet /tmp/frames.png
    .venv-img/bin/python scripts/image_pipeline/gen_gm_grandeur_frames.py --write

Both need the game install (VIC3_BASE_GAME): the band comes from vanilla's
building icons.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

SIZE = 256
BAKED = 9.5   # compose_framed's frame: MinFilter(19), 9 px in from the silhouette edge
BAND = 13.0   # the overlay: 3.5 px wider, so the metal reads at 96 px
SPLIT = 6.5   # two-metal tiers: the inner metal runs from here to BAND (half the band; a thinner line
              # vanished at 96 px)
OUT_DIR = MOD_ROOT / "gfx/interface/icons/gm_pictures/frames"

# shadow, mid, highlight
METALS = {
    "bronze": ((58, 34, 17), (152, 96, 48), (236, 186, 124)),
    "silver": ((66, 68, 74), (166, 169, 177), (244, 245, 248)),
    "gold": ((88, 58, 10), (204, 158, 44), (255, 232, 142)),
}
# tier -> (outer metal, inner-line metal, gems)
TIERS = {1: ("bronze", "bronze", False), 2: ("bronze", "silver", False), 3: ("silver", "gold", False),
         4: ("gold", "gold", False), 5: ("gold", "gold", True)}
GEM = ((70, 0, 12), (190, 20, 40), (255, 150, 160))  # a ruby: shadow, body, highlight


def band_geometry(template_alpha: np.ndarray) -> np.ndarray:
    """Distance in px from the silhouette's edge, inside it (0 outside)."""
    return ndimage.distance_transform_edt(template_alpha > 128)


def shading(dist: np.ndarray, med_rgb: np.ndarray) -> np.ndarray:
    """0..1 luminance across the band: a drawn bevel (a ridge near the outer
    edge, a groove, a ridge, a dark inner lip) mixed with vanilla's own frame
    shading where the baked frame is."""
    profile = (0.55 + 0.35 * np.exp(-((dist - 2.5) / 1.6) ** 2)
               - 0.30 * np.exp(-((dist - 6.0) / 1.4) ** 2)
               + 0.30 * np.exp(-((dist - 9.0) / 1.3) ** 2)
               - 0.35 * np.exp(-((dist - 12.3) / 0.9) ** 2))
    lum = med_rgb.mean(axis=-1) / 255.0
    inside = (dist > 0) & (dist <= BAKED)
    vals = lum[inside]
    norm = np.zeros_like(lum)
    if vals.size:
        lo, hi = np.percentile(vals, 5), np.percentile(vals, 95)
        norm = np.clip((lum - lo) / max(hi - lo, 1e-3), 0, 1)
    mix = np.where(inside, 0.55 * profile + 0.45 * norm, profile)
    return np.clip(mix, 0, 1)


def gradient_map(lum: np.ndarray, stops) -> np.ndarray:
    shadow, mid, high = (np.array(s, dtype=np.float32) for s in stops)
    lo = np.clip(lum * 2, 0, 1)[..., None]
    hi = np.clip(lum * 2 - 1, 0, 1)[..., None]
    return np.where(lum[..., None] < 0.5, shadow + (mid - shadow) * lo, mid + (high - mid) * hi)


def corner_points(dist: np.ndarray, at: float) -> list[tuple[int, int]]:
    """Where each corner's diagonal crosses the band at depth `at`."""
    n = dist.shape[0]
    pts = []
    for sx, sy in ((0, 0), (n - 1, 0), (0, n - 1), (n - 1, n - 1)):
        dx, dy = (1 if sx == 0 else -1), (1 if sy == 0 else -1)
        for k in range(n // 2):
            x, y = sx + dx * k, sy + dy * k
            if dist[y, x] >= at:
                pts.append((x, y))
                break
    return pts


def draw_gem(rgb: np.ndarray, alpha: np.ndarray, cx: int, cy: int, r: float = 7.5) -> None:
    yy, xx = np.mgrid[0:rgb.shape[0], 0:rgb.shape[1]]
    d = np.hypot(xx - cx, yy - cy)
    inside = d <= r
    # dome shading lit from the top left, a dark rim and a specular dot
    lx, ly = (xx - cx) / r, (yy - cy) / r
    lum = np.clip(0.55 - 0.35 * (lx + ly) / 1.4 + 0.25 * (1 - (d / r) ** 2), 0, 1)
    col = gradient_map(lum, GEM)
    rim = inside & (d > r - 1.3)
    col[rim] = np.array(METALS["gold"][0], dtype=np.float32)
    spec = np.hypot(xx - (cx - r * 0.35), yy - (cy - r * 0.35)) <= r * 0.22
    col[spec & inside] = np.array((255, 245, 245), dtype=np.float32)
    rgb[inside] = col[inside]
    alpha[inside] = 1.0


def build(tier: int, med: np.ndarray, dist: np.ndarray) -> Image.Image:
    outer, inner, gems = TIERS[tier]
    lum = shading(dist, med[..., :3])
    rgb = np.where((dist > SPLIT)[..., None], gradient_map(lum, METALS[inner]), gradient_map(lum, METALS[outer]))
    # the band, its inner edge anti-aliased over 1.5 px
    alpha = np.clip((BAND - dist) / 1.5 + 0.5, 0, 1) * (dist > 0)
    alpha = alpha * np.clip(med[..., 3] / 255.0 * 1.0, 0, 1)
    if gems:
        for cx, cy in corner_points(dist, (BAND + 1) / 2):
            draw_gem(rgb, alpha, cx, cy)
    out = np.dstack([np.clip(rgb, 0, 255), np.clip(alpha * 255, 0, 255)]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def frames() -> dict[int, Image.Image]:
    from icon_render import vanilla_template
    med, _std = vanilla_template("building_icons", SIZE)
    dist = band_geometry(med[..., 3])
    return {tier: build(tier, med, dist) for tier in TIERS}


def sheet(path: Path, made: dict[int, Image.Image]) -> None:
    pics = MOD_ROOT / "gfx/interface/icons/gm_pictures"
    from icon_render import load_rgba
    samples = [load_rgba(pics / f"{k}.dds") for k in ("generic__column", "faith_catholic__faith",
                                                      "heritage_chinese__pagoda")]
    cell, small = SIZE + 10, 96
    img = Image.new("RGB", (cell * 6, len(samples) * (cell + small + 20) + 30), (36, 34, 31))
    d = ImageDraw.Draw(img)
    for c, tier in enumerate([0] + sorted(made)):
        d.text((c * cell + 6, 8), "plain" if tier == 0 else f"tier {tier}", fill=(240, 230, 200))
        for r, pic in enumerate(samples):
            im = pic.copy()
            if tier:
                im.alpha_composite(made[tier])
            y = 30 + r * (cell + small + 20)
            img.paste(im, (c * cell, y), im)
            sm = im.resize((small, small), Image.LANCZOS)
            img.paste(sm, (c * cell + (SIZE - small) // 2, y + SIZE + 10), sm)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sheet", type=Path, help="preview over sample pictures at 256 and 96 px")
    ap.add_argument("--write", action="store_true", help=f"write {OUT_DIR.relative_to(MOD_ROOT)}/frame_tier_<n>.dds")
    args = ap.parse_args()
    if not (args.sheet or args.write):
        ap.error("nothing to do: pass --sheet and/or --write")
    made = frames()
    if args.sheet:
        sheet(args.sheet, made)
        print(f"wrote {args.sheet}")
    if args.write:
        from icon_dds import write_dds
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for tier, im in made.items():
            write_dds(im, OUT_DIR / f"frame_tier_{tier}.dds")
        print(f"wrote {len(made)} frames to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
