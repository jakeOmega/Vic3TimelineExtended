#!/usr/bin/env python3
"""
gen_principle_tier_frames.py - Tier IV and V frames for power bloc principles.

Vanilla ships three tier frames (principle_tier_1/2/3.dds: bronze, silver and
gold, with a 4-, 5- and 6-sided inset and the numeral in two corners). The mod
gives every principle group tiers 4 and 5, and those used the tier III frame,
numeral and all. This builds the two missing frames from vanilla's tier III,
so they keep its band, corner scrollwork and plate texture:

  1. clear the III from both corner plates (each row interpolated between
     the clean plate on either side);
  2. reshape the inset: a radial remap about the centre moves the hexagon's
     rim onto a heptagon (IV) or octagon (V), carrying the rim's bevel and
     the plate texture with it, and fades back to identity before the band;
  3. recolour: the metal is gradient-mapped over its luminance to the tier's
     material, and the map background and inset plate take a light tint of
     it, as vanilla's tiers do;
  4. stamp IV or V in the vanilla numeral style (Georgia Bold, thickened;
     dark fill and a light outline).

The game draws PowerBlocPrinciple.GetBackground, the principle's own
`background =`, under its icon at 100x100 (power_bloc_panel.gui,
principle_icon_with_bg), so nothing loads these by key.

    .venv/bin/python scripts/image_pipeline/gen_principle_tier_frames.py --sheet /tmp/tiers.png
    .venv/bin/python scripts/image_pipeline/gen_principle_tier_frames.py --write --wire

--write needs the game install (it reads vanilla's tier III frame). --wire
needs nothing: it points the `background =` line of every tier-4 and tier-5
principle (by its place in its group's `levels`) at the new frames.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:  # CI has no Pillow; tiers_by_principle and wire don't need it
    Image = ImageDraw = ImageFilter = ImageFont = None

SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(MOD_ROOT))

FOLDER = "gfx/interface/icons/principles_icons"
FRAME = {t: f"{FOLDER}/principle_tier_{t}.dds" for t in (1, 2, 3, 4, 5)}
DEFAULT_MATERIALS = {4: "sapphire", 5: "amethyst"}

# ── geometry of vanilla's principle_tier_3.dds (208x208) ─────────────────

CENTRE = (103.5, 103.5)
# Tier III's inset: a hexagon with points left and right, 150 wide, 146 tall
# at the rim's centre line.
HEXAGON = np.array([(75, 0), (37.5, 73), (-37.5, 73), (-75, 0), (-37.5, -73), (37.5, -73)], float)
# Corner plates: the numeral's box, and the clean plate columns either side.
PLATES = (
    dict(x0=158, x1=199, y0=9, y1=38, left=(154, 157), right=(200, 202), centre=(179.0, 23.5)),
    dict(x0=8, x1=48, y0=170, y1=201, left=(4, 7), right=(49, 52), centre=(28.5, 185.5)),
)
NUMERAL = {4: "IV", 5: "V"}
NUMERAL_CAP_PX = 25     # vanilla's III is 25-26 px tall
NUMERAL_OUTLINE_PX = 2
NUMERAL_BOLD_PX = 1.2   # Georgia Bold is a little lighter than vanilla's glyphs
FONTS = (
    "/mnt/c/Windows/Fonts/georgiab.ttf",
    "C:/Windows/Fonts/georgiab.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Georgia_Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",  # fallback: heavier, less bracketed
)


def regular_polygon(sides: int, start_deg: float, half_w: float, half_h: float) -> np.ndarray:
    """A regular polygon (image coordinates, y down) fitted to the given half-extents."""
    ang = np.radians(start_deg + np.arange(sides) * 360.0 / sides)
    v = np.stack([np.cos(ang), np.sin(ang)], 1)
    lo, hi = v.min(0), v.max(0)
    return (v - (lo + hi) / 2) / ((hi - lo) / 2) * np.array([half_w, half_h])


# 4, 5, 6 sides for I-III; IV and V continue it. Odd counts point up, as the
# pentagon does; the octagon is flat-topped, as the hexagon is.
INSET = {
    4: regular_polygon(7, -90, 73.0, 71.5),
    5: regular_polygon(8, 22.5, 74.0, 73.0),
}


def _ramp(shadow, dark, mid, light, pale):
    return [(0.0, (8, 8, 10)), (0.2, shadow), (0.42, dark), (0.6, mid), (0.74, light), (0.86, pale), (1.0, (255, 255, 255))]


# name -> (metal ramp over luminance, background/plate tint, background tint strength,
#          numeral fill, numeral outline)
MATERIALS = {
    "sapphire": (_ramp((10, 18, 48), (26, 52, 118), (52, 100, 186), (122, 166, 226), (200, 222, 248)),
                 (84, 100, 132), 0.55, (12, 20, 50), (206, 222, 248)),
    "amethyst": (_ramp((30, 10, 46), (74, 32, 112), (126, 70, 176), (184, 142, 222), (230, 212, 248)),
                 (104, 92, 128), 0.55, (34, 12, 52), (232, 216, 250)),
    "platinum": (_ramp((40, 42, 46), (105, 108, 114), (168, 170, 174), (214, 215, 216), (240, 240, 238)),
                 (128, 130, 134), 0.55, (26, 28, 34), (238, 238, 234)),
    "diamond": (_ramp((18, 40, 50), (70, 120, 138), (136, 196, 212), (196, 234, 244), (236, 252, 255)),
                (100, 124, 132), 0.55, (14, 36, 48), (226, 248, 255)),
    "emerald": (_ramp((6, 34, 20), (18, 88, 56), (38, 150, 98), (112, 204, 158), (206, 244, 224)),
                (80, 108, 92), 0.5, (8, 36, 22), (212, 244, 226)),
    "ruby": (_ramp((44, 6, 14), (110, 18, 36), (172, 38, 60), (220, 104, 120), (246, 196, 200)),
             (128, 84, 92), 0.5, (48, 8, 18), (248, 212, 216)),
}
RIM_HALF_PX = 3.5
PLATE_TINT = 0.85


# ── image steps ──────────────────────────────────────────────────────────

def _smooth(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def _hsv(a):
    h = np.asarray(Image.fromarray(a[..., :3]).convert("HSV"), float)
    return h[..., 0] * 360 / 255, h[..., 1] / 255, h[..., 2] / 255


def _luminance(a):
    return (a[..., :3].astype(float) / 255) @ np.array([0.299, 0.587, 0.114])


def _ray_radius(poly, theta):
    """Distance from the centre to the polygon's boundary along each angle."""
    d = np.stack([np.cos(theta), np.sin(theta)], -1)
    best = np.full(theta.shape, np.inf)
    for i in range(len(poly)):
        p, e = poly[i], poly[(i + 1) % len(poly)] - poly[i]
        det = -d[..., 0] * e[1] + d[..., 1] * e[0]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (-p[0] * e[1] + p[1] * e[0]) / det
            s = (d[..., 0] * p[1] - d[..., 1] * p[0]) / det
        ok = (np.abs(det) > 1e-9) & (s >= -1e-9) & (s <= 1 + 1e-9) & (t > 0)
        best = np.where(ok & (t < best), t, best)
    return best


def _polar(shape):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(float)
    dx, dy = xx - CENTRE[0], yy - CENTRE[1]
    return np.hypot(dx, dy), np.arctan2(dy, dx)


def _bilinear(img, sx, sy):
    h, w = img.shape[:2]
    sx, sy = np.clip(sx, 0, w - 1.001), np.clip(sy, 0, h - 1.001)
    x0, y0 = np.floor(sx).astype(int), np.floor(sy).astype(int)
    fx, fy = (sx - x0)[..., None], (sy - y0)[..., None]
    f = img.astype(float)
    out = (f[y0, x0] * (1 - fx) * (1 - fy) + f[y0, x0 + 1] * fx * (1 - fy)
           + f[y0 + 1, x0] * (1 - fx) * fy + f[y0 + 1, x0 + 1] * fx * fy)
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def clear_plates(a):
    out = a.copy().astype(float)
    for p in PLATES:
        xl, xr = sum(p["left"]) / 2, sum(p["right"]) / 2
        for y in range(p["y0"], p["y1"] + 1):
            left = a[y, p["left"][0]:p["left"][1] + 1, :3].astype(float).mean(0)
            right = a[y, p["right"][0]:p["right"][1] + 1, :3].astype(float).mean(0)
            for x in range(p["x0"], p["x1"] + 1):
                t = (x - xl) / (xr - xl)
                out[y, x, :3] = left * (1 - t) + right * t
    return out.astype(np.uint8)


def reshape_inset(a, poly, inner_margin=5.0, band=7.0):
    """Move tier III's hexagon rim onto `poly`; identity past the rim plus a fade band."""
    rho, th = _polar(a.shape)
    new_r, old_r = _ray_radius(poly, th), _ray_radius(HEXAGON, th)
    k = old_r / new_r
    lo = new_r + inner_margin
    hi = np.maximum(new_r, old_r) + inner_margin + band
    src = np.where(rho <= lo, rho * k,
                   np.where(rho >= hi, rho, k * lo + (rho - lo) / (hi - lo) * (hi - k * lo)))
    return _bilinear(a, CENTRE[0] + src * np.cos(th), CENTRE[1] + src * np.sin(th))


def _metal_mask(a):
    """Tier III's gold: hue 18-62 degrees, plus its pale yellow-green highlights."""
    h, s, v = _hsv(a)
    gold = _smooth(h, 18, 26) * (1 - _smooth(h, 52, 62))
    highlight = _smooth(h, 18, 26) * (1 - _smooth(h, 68, 78)) * _smooth(v, 0.62, 0.72)
    return np.maximum(gold, highlight) * _smooth(s, 0.22, 0.38) * _smooth(v, 0.22, 0.34)


def recolour(a, poly, material):
    ramp, tint, tint_amount, _, _ = MATERIALS[material]
    rho, th = _polar(a.shape)
    d = rho - _ray_radius(poly, th)  # radial distance to the rim's centre line
    plate = 1 - _smooth(d, -RIM_HALF_PX - 1.5, -RIM_HALF_PX + 0.5)
    rim = 1 - _smooth(np.abs(d), RIM_HALF_PX - 0.5, RIM_HALF_PX + 1.0)
    _, _, v = _hsv(a)
    metal = np.maximum(_metal_mask(a) * (1 - plate), rim * _smooth(v, 0.12, 0.25))[..., None]
    plate = (plate * (1 - rim))[..., None]

    lum = _luminance(a)
    pos = np.array([p for p, _ in ramp])
    cols = np.array([c for _, c in ramp], float)
    mapped = np.stack([np.interp(lum, pos, cols[:, i]) for i in range(3)], -1)
    rgb = a[..., :3].astype(float) * (1 - metal) + mapped * metal

    t = np.array(tint, float)
    t /= t @ np.array([0.299, 0.587, 0.114])  # unit luminance, so tinting keeps brightness
    tinted = np.clip((lum * 255)[..., None] * t, 0, 255)
    w = (1 - metal) * (tint_amount * (1 - plate) + PLATE_TINT * plate) * _smooth(lum, 0.08, 0.2)[..., None]
    out = a.copy()
    out[..., :3] = np.clip(rgb * (1 - w) + tinted * w + 0.5, 0, 255).astype(np.uint8)
    return out


def _font_path() -> str:
    for p in FONTS:
        if Path(p).is_file():
            if "georgia" not in p.lower():
                print(f"warning: Georgia Bold not found, numerals drawn in {p}; "
                      "they will not match the committed frames", file=sys.stderr)
            return p
    raise SystemExit("No numeral font found; see FONTS in gen_principle_tier_frames.py")


def numeral(text, fill, outline, ss=8):
    """The numeral in vanilla's style: dark fill, light outline, darker toward the base."""
    path = _font_path()
    probe = ImageFont.truetype(path, 200)
    b = probe.getbbox("I")
    font = ImageFont.truetype(path, round(200 * NUMERAL_CAP_PX * ss / (b[3] - b[1])))
    box = font.getbbox(text)
    mask = Image.new("L", (box[2] - box[0] + 4, box[3] - box[1] + 4), 0)
    ImageDraw.Draw(mask).text((2 - box[0], 2 - box[1]), text, font=font, fill=255)
    mask = mask.crop(mask.getbbox()).filter(ImageFilter.MaxFilter(round(NUMERAL_BOLD_PX * ss) | 1))
    pad = (NUMERAL_OUTLINE_PX + 2) * ss
    big = Image.new("L", (mask.width + 2 * pad, mask.height + 2 * pad), 0)
    big.paste(mask, (pad, pad))
    ring = big.filter(ImageFilter.MaxFilter(NUMERAL_OUTLINE_PX * ss + 1))
    w, h = big.width // ss, big.height // ss
    glyph = np.asarray(big.crop((0, 0, w * ss, h * ss)).resize((w, h), Image.BOX), float)[..., None] / 255
    alpha = np.asarray(ring.crop((0, 0, w * ss, h * ss)).resize((w, h), Image.BOX), float) / 255
    shade = np.linspace(1.15, 0.85, h)[:, None, None]
    rgb = np.array(outline, float) * (1 - glyph) + np.clip(np.array(fill, float) * shade, 0, 255) * glyph
    return Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")


def build(tier: int, material: str, tier3: np.ndarray) -> np.ndarray:
    a = clear_plates(tier3)
    a = reshape_inset(a, INSET[tier])
    a = recolour(a, INSET[tier], material)
    _, _, _, fill, outline = MATERIALS[material]
    glyph = numeral(NUMERAL[tier], fill, outline)
    im = Image.fromarray(a, "RGBA")
    for p in PLATES:
        cx, cy = p["centre"]
        im.alpha_composite(glyph, (round(cx - glyph.width / 2), round(cy - glyph.height / 2)))
    return np.array(im)


# ── references ───────────────────────────────────────────────────────────

_BLOCK_RE = re.compile(r"^((?:INJECT|REPLACE|TRY_INJECT|TRY_REPLACE|INJECT_OR_CREATE|REPLACE_OR_CREATE):)?(\w+)\s*=\s*\{", re.M)


def tiers_by_principle(root: Path = MOD_ROOT) -> dict[str, int]:
    """principle key -> tier, from each group's `levels` list in the mod.

    An INJECT: block appends to a vanilla group's three levels; any other block
    defines the whole list.
    """
    tiers: dict[str, int] = {}
    for path in sorted((root / "common/power_bloc_principle_groups").glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig")
        for m in _BLOCK_RE.finditer(text):
            offset = 3 if (m.group(1) or "").startswith(("INJECT", "TRY_INJECT")) else 0
            depth, i = 1, m.end()
            while depth and i < len(text):
                depth += {"{": 1, "}": -1}.get(text[i], 0)
                i += 1
            body = re.sub(r"#[^\n]*", "", text[m.end():i])
            lv = re.search(r"\blevels\s*=\s*\{([^}]*)\}", body)
            if lv:
                for n, key in enumerate(lv.group(1).split(), 1):
                    tiers[key] = offset + n
    return tiers


def wire(dry_run: bool) -> list[str]:
    from generate_icons import rewrite_icon_refs  # noqa: PLC0415

    targets = {k: FRAME[t] for k, t in tiers_by_principle().items() if t in (4, 5)}
    changed: list[str] = []
    for path in sorted((MOD_ROOT / "common/power_bloc_principles").glob("*.txt")):
        changed += rewrite_icon_refs(path, "background", targets, dry_run=dry_run)
    return changed


# ── CLI ──────────────────────────────────────────────────────────────────

def _vanilla_tier(t: int) -> np.ndarray:
    import path_constants  # noqa: PLC0415

    return np.array(Image.open(Path(path_constants.base_game_path) / "game" / FRAME[t]).convert("RGBA"))


def sheet(frames: dict[int, np.ndarray], out: Path) -> None:
    """Tiers I-V at the game's 100 px, then IV and V at 2x."""
    row = [_vanilla_tier(t) for t in (1, 2, 3)] + [frames[4], frames[5]]
    s = Image.new("RGBA", (5 * 108 + 2 * 218 + 20, 226), (32, 32, 32, 255))
    for i, f in enumerate(row):
        s.alpha_composite(Image.fromarray(f).resize((100, 100), Image.LANCZOS), (10 + i * 108, 10))
    for i, t in enumerate((4, 5)):
        s.alpha_composite(Image.fromarray(frames[t]).resize((208, 208), Image.LANCZOS), (10 + 5 * 108 + 10 + i * 218, 10))
    s.save(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier4", default=DEFAULT_MATERIALS[4], choices=sorted(MATERIALS))
    ap.add_argument("--tier5", default=DEFAULT_MATERIALS[5], choices=sorted(MATERIALS))
    ap.add_argument("--sheet", type=Path, help="write a review sheet (tiers I-V) to this PNG")
    ap.add_argument("--write", action="store_true", help=f"write {FRAME[4]} and {FRAME[5]}")
    ap.add_argument("--wire", action="store_true", help="point tier-4/5 principles' background at them")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.sheet or args.write:
        tier3 = _vanilla_tier(3)
        frames = {4: build(4, args.tier4, tier3), 5: build(5, args.tier5, tier3)}
        if args.sheet:
            sheet(frames, args.sheet)
            print(f"sheet: {args.sheet}")
        if args.write and not args.dry_run:
            from icon_dds import write_dds  # noqa: PLC0415

            for t, f in frames.items():
                (MOD_ROOT / FRAME[t]).parent.mkdir(parents=True, exist_ok=True)
                write_dds(Image.fromarray(f, "RGBA"), MOD_ROOT / FRAME[t])
                print(f"wrote {FRAME[t]}")
    if args.wire:
        changed = wire(args.dry_run)
        print(f"{'would point' if args.dry_run else 'pointed'} {len(changed)} principles at the tier IV/V frames")


if __name__ == "__main__":
    main()
