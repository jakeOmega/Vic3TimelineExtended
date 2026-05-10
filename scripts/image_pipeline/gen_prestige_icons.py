"""Generate "shiny" prestige variants for each prestige_good_* entry.

For every entry in `common/prestige_goods/extra_prestige_goods.txt`, reads the
source icon (mod gfx if present, else base-game gfx), applies a uniform
"shiny halo" treatment (warm radial glow + gentle gold tint + corner sparkles),
and writes the result to `gfx/interface/icons/goods_icons/prestige/<stem>.dds`
as uncompressed RGBA8888 DDS. Texture lines in the prestige-goods file are
rewritten in place to point at the new path.

Idempotent: outputs are skipped when the file already exists. Pass --force (or
set the kwarg in `regenerate`) to overwrite, e.g. after a vanilla icon update.
Re-running on a clean tree is a fast no-op.

Run standalone:
    python3 scripts/image_pipeline/gen_prestige_icons.py [--force]
Or via the module API used by mod_state_server.POST_LOAD_GENERATORS:
    from scripts.image_pipeline import gen_prestige_icons
    gen_prestige_icons.regenerate(mod_state)
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from path_constants import base_game_path, mod_path  # noqa: E402

PRESTIGE_FILE = Path(mod_path) / "common" / "prestige_goods" / "extra_prestige_goods.txt"
OUTPUT_DIR = Path(mod_path) / "gfx" / "interface" / "icons" / "goods_icons" / "prestige"
SOURCE_DIRS = (
    Path(mod_path) / "gfx" / "interface" / "icons" / "goods_icons",
    Path(base_game_path) / "game" / "gfx" / "interface" / "icons" / "goods_icons",
)
TEXTURE_PATH_PREFIX = "gfx/interface/icons/goods_icons/"
PRESTIGE_REL_PREFIX = TEXTURE_PATH_PREFIX + "prestige/"


# --------------------------------------------------------------------------- #
# Image treatment                                                             #
# --------------------------------------------------------------------------- #


def _radial_gradient(w: int, h: int, inner: tuple[int, int, int, int], outer: tuple[int, int, int, int]) -> Image.Image:
    """Elliptical gradient: t=0 at center, t=1 on the ellipse inscribed in the
    canvas (tangent to edge midpoints), clamped to 1 in the corners. Pair with
    `outer = (..., 0)` to fade to transparent inside the bounding box, leaving
    an oval halo with fully transparent corners — required so prestige icons
    don't show a square boundary against UI backgrounds."""
    cy, cx = h / 2, w / 2
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    nx = (xx - cx) / cx
    ny = (yy - cy) / cy
    t = np.clip(np.sqrt(nx * nx + ny * ny), 0.0, 1.0)[..., None]
    inner_a = np.array(inner, dtype=np.float32)
    outer_a = np.array(outer, dtype=np.float32)
    out = inner_a * (1 - t) + outer_a * t
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


def _four_point_star(d: int, color: tuple[int, int, int, int] = (255, 245, 180, 255)) -> Image.Image:
    img = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = d / 2
    arm = d * 0.48
    waist = d * 0.07
    draw.polygon([(cx, cy - arm), (cx + waist, cy), (cx, cy + arm), (cx - waist, cy)], fill=color)
    draw.polygon([(cx - arm, cy), (cx, cy - waist), (cx + arm, cy), (cx, cy + waist)], fill=color)
    draw.ellipse([cx - waist * 1.4, cy - waist * 1.4, cx + waist * 1.4, cy + waist * 1.4], fill=color)
    return img.filter(ImageFilter.GaussianBlur(radius=d * 0.04))


def _gold_tint(img: Image.Image, strength: float) -> Image.Image:
    """Mix warm gold over RGB while preserving original alpha."""
    overlay = Image.new("RGBA", img.size, (255, 200, 90, int(255 * strength)))
    base = img.copy()
    base.alpha_composite(overlay)
    r, g, b, _ = base.split()
    return Image.merge("RGBA", (r, g, b, img.split()[3]))


def _boost(img: Image.Image, sat: float, brightness: float) -> Image.Image:
    rgb = img.convert("RGB")
    rgb = ImageEnhance.Color(rgb).enhance(sat)
    rgb = ImageEnhance.Brightness(rgb).enhance(brightness)
    r, g, b = rgb.split()
    return Image.merge("RGBA", (r, g, b, img.split()[3]))


# Sparkle positions in normalized (fx, fy, fs) — fraction of canvas. Symmetric
# around the center subject so the eye never "loses" the icon's shape.
SPARKLE_POSITIONS = (
    (0.16, 0.18, 0.10),
    (0.84, 0.22, 0.08),
    (0.82, 0.78, 0.06),
    (0.20, 0.85, 0.06),
)


def _rounded_corner_mask(w: int, h: int, corner_radius: float, antialias: float = 1.5) -> np.ndarray:
    """Float32 (h, w) alpha multiplier in [0, 1] for a rounded rectangle inscribed
    in (0,0)–(w,h). Mask is 1 along straight edges and inside; transitions to 0
    at the rounded-corner arcs, with `antialias` pixels of soft falloff. Used to
    kill any 1-px artifacts at the rectangular corners — both from the halo and
    from source icons (e.g. automobiles, consumer_appliances) whose own pixels
    extend right up to the bounding rectangle."""
    r = max(corner_radius, 0.0)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    # Snap each pixel to the corner-arc center it's nearest to (or to itself if
    # it's in the straight-edge interior). Distance from (x,y) to that snap
    # point is the radial distance into the corner region.
    cx = np.clip(xx, r, max(r, w - 1 - r))
    cy = np.clip(yy, r, max(r, h - 1 - r))
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    return np.clip((r - d) / max(antialias, 1e-3), 0.0, 1.0)


def apply_shiny_halo(base: Image.Image) -> Image.Image:
    """Treatment A — warm oval halo + gold tint + 4 corner sparkles + rounded-
    corner alpha mask. The halo is bounded to an ellipse inscribed in the
    canvas; a small rounded-rect mask is applied to the final alpha so every
    output has fully transparent corners regardless of source content."""
    base = base.convert("RGBA")
    w, h = base.size
    glow = _radial_gradient(w, h, (255, 220, 130, 140), (255, 200, 90, 0))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.alpha_composite(glow)
    canvas.alpha_composite(_boost(_gold_tint(base, strength=0.14), sat=1.12, brightness=1.04))
    side = max(w, h)
    for fx, fy, fs in SPARKLE_POSITIONS:
        d = max(8, int(side * fs))
        star = _four_point_star(d)
        canvas.alpha_composite(star, (int(fx * w) - d // 2, int(fy * h) - d // 2))
    # Rounded-rect alpha clamp: ~4% of the shorter side, kills corner artifacts.
    radius = max(3.0, 0.04 * min(w, h))
    mask = _rounded_corner_mask(w, h, corner_radius=radius)
    arr = np.asarray(canvas, dtype=np.float32).copy()
    arr[..., 3] = arr[..., 3] * mask
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


# --------------------------------------------------------------------------- #
# Uncompressed RGBA8888 DDS encoder                                           #
# --------------------------------------------------------------------------- #


def _build_dds_header(w: int, h: int) -> bytes:
    DDSD_FLAGS = 0x00000001 | 0x00000002 | 0x00000004 | 0x00000008 | 0x00001000  # caps|h|w|pitch|pf
    DDPF_FLAGS = 0x00000001 | 0x00000040  # alphapixels|rgb
    DDSCAPS_TEXTURE = 0x00001000
    parts = [
        b"DDS ",
        struct.pack("<I", 124),
        struct.pack("<I", DDSD_FLAGS),
        struct.pack("<I", h),
        struct.pack("<I", w),
        struct.pack("<I", w * 4),  # pitch
        struct.pack("<I", 0),      # depth
        struct.pack("<I", 0),      # mipMapCount
        b"\x00" * 44,              # 11 reserved DWORDs
        struct.pack("<I", 32),     # pf size
        struct.pack("<I", DDPF_FLAGS),
        b"\x00" * 4,               # fourCC
        struct.pack("<I", 32),     # rgbBitCount
        struct.pack("<I", 0x00FF0000),  # R mask
        struct.pack("<I", 0x0000FF00),  # G mask
        struct.pack("<I", 0x000000FF),  # B mask
        struct.pack("<I", 0xFF000000),  # A mask
        struct.pack("<I", DDSCAPS_TEXTURE),
        b"\x00" * 12,              # caps2/3/4
        b"\x00" * 4,               # reserved2
    ]
    header = b"".join(parts)
    assert len(header) == 128
    return header


def write_dds_rgba(img: Image.Image, path: Path) -> None:
    img = img.convert("RGBA")
    arr = np.asarray(img, dtype=np.uint8)            # (h, w, 4) RGBA
    bgra = arr[..., [2, 1, 0, 3]].tobytes()          # encoder expects BGRA bytes (= ARGB DWORD LE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(_build_dds_header(img.width, img.height))
        f.write(bgra)


# --------------------------------------------------------------------------- #
# Prestige-goods file IO                                                      #
# --------------------------------------------------------------------------- #

_TEXTURE_RE = re.compile(r'(?P<lead>\s*texture\s*=\s*")(?P<path>[^"]+)(?P<tail>")(?P<rest>.*)$')
_BASE_GOOD_RE = re.compile(r"\s*base_good\s*=\s*([A-Za-z0-9_]+)")


@dataclass
class TextureRewrite:
    line_no: int
    old_path: str
    new_path: str


def parse_textures(text: str) -> tuple[list[TextureRewrite], dict[str, str]]:
    """Return (rewrites, source_to_stem_map). source_to_stem_map keys are the
    *source* texture paths (after stripping any 'prestige/' prefix from a
    previous run); values are the desired output filename (the stem)."""
    rewrites: list[TextureRewrite] = []
    sources: dict[str, str] = {}
    for i, raw in enumerate(text.splitlines()):
        m = _TEXTURE_RE.match(raw)
        if not m:
            continue
        old = m.group("path")
        if not old.startswith(TEXTURE_PATH_PREFIX):
            # Foreign path — leave alone, don't touch it.
            continue
        # Strip prestige/ prefix if this entry was already rewritten by a prior run.
        rel = old[len(TEXTURE_PATH_PREFIX):]
        if rel.startswith("prestige/"):
            stem_part = rel[len("prestige/"):]
        else:
            stem_part = rel
        if not stem_part.endswith(".dds"):
            continue
        source_rel = TEXTURE_PATH_PREFIX + stem_part
        new = PRESTIGE_REL_PREFIX + stem_part
        rewrites.append(TextureRewrite(line_no=i, old_path=old, new_path=new))
        sources[source_rel] = stem_part
    return rewrites, sources


def rewrite_textures(text: str, rewrites: list[TextureRewrite]) -> str:
    if not rewrites:
        return text
    lines = text.splitlines(keepends=True)
    by_line = {r.line_no: r for r in rewrites}
    for i, raw in enumerate(lines):
        r = by_line.get(i)
        if not r or r.old_path == r.new_path:
            continue
        lines[i] = raw.replace(f'"{r.old_path}"', f'"{r.new_path}"', 1)
    return "".join(lines)


def find_source(rel_path: str) -> Path | None:
    """Resolve a `gfx/interface/icons/goods_icons/<x>.dds` reference to an actual
    file on disk. Mod gfx wins over vanilla."""
    stem = rel_path[len(TEXTURE_PATH_PREFIX):]
    for d in SOURCE_DIRS:
        p = d / stem
        if p.is_file():
            return p
    return None


# --------------------------------------------------------------------------- #
# Pipeline                                                                    #
# --------------------------------------------------------------------------- #


@dataclass
class Summary:
    generated: int = 0
    skipped_existing: int = 0
    missing_sources: list[str] = field(default_factory=list)
    rewrote_file: bool = False

    def to_dict(self) -> dict:
        return {
            "generated": self.generated,
            "skipped_existing": self.skipped_existing,
            "missing_sources": list(self.missing_sources),
            "rewrote_file": self.rewrote_file,
        }


def generate_one(source: Path, output: Path, *, force: bool) -> bool:
    """Returns True if the file was (re)generated, False if it already existed."""
    if output.exists() and not force:
        return False
    img = Image.open(source).convert("RGBA")
    out = apply_shiny_halo(img)
    write_dds_rgba(out, output)
    return True


def run(*, force: bool = False) -> Summary:
    summary = Summary()
    text = PRESTIGE_FILE.read_text(encoding="utf-8")
    rewrites, sources = parse_textures(text)
    for source_rel, stem in sources.items():
        src = find_source(source_rel)
        if src is None:
            summary.missing_sources.append(source_rel)
            continue
        out_path = OUTPUT_DIR / stem
        if generate_one(src, out_path, force=force):
            summary.generated += 1
        else:
            summary.skipped_existing += 1
    new_text = rewrite_textures(text, rewrites)
    if new_text != text:
        PRESTIGE_FILE.write_text(new_text, encoding="utf-8")
        summary.rewrote_file = True
    return summary


def regenerate(_mod_state, *, force: bool = False) -> dict:
    """Entrypoint matching mod_state_server.POST_LOAD_GENERATORS convention."""
    return run(force=force).to_dict()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="Regenerate every output, even if the file already exists.")
    args = parser.parse_args()
    print(run(force=args.force).to_dict())
