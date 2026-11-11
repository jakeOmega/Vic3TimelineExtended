#!/usr/bin/env python3
"""Convert a picked render to a state picture: gfx/state_pictures/te_<key>.dds.

    python3 scripts/image_pipeline/convert_state_picture.py <key>=<png> [<key>=<png> ...]

The entry's `smudge` boxes are blurred first (a lettered sign in the middle of
the picture, where a crop can't reach). The render is then cropped to the entry's
`crop` box (to drop a signature or a stray object at an edge), fitted to 1530 x 750, run through a Kuwahara filter
and scaled to 1020 x 500. The filter gives each pixel the mean of whichever of
its four quadrant windows varies least: flat dabs of color with kept edges, like
a loaded brush; a fifth of the unfiltered picture is blended back. FLUX's renders are closer to a photograph than vanilla's
paintings are, and this brings them beside them.

Vanilla's state pictures are 1020 x 500 with a full mip chain, uncompressed
(2.7 MB each). These are BC7 with mips (about 0.7 MB): both sides are multiples
of 4, which block compression needs (scripts/analysis/check_dds_dimensions.py).
Needs Pillow, numpy and texconv.exe, as convert_event_image.py does (it finds or
downloads texconv).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from convert_event_image import _exe_path, ensure_texconv  # noqa: E402

WIDTH, HEIGHT = 1020, 500
WORK_SCALE = 1.5    # the filter runs at 1530 x 750, so its dabs stay small in the picture
PAINT_RADIUS = 3    # the Kuwahara window's reach, in work pixels; 8 smears windows and wires away
PAINT_BLEND = 0.8   # the filtered share; alone, the filter leaves blocky edges in clouds
REPO = Path(__file__).resolve().parent.parent.parent
OUT_DIR = REPO / "gfx" / "state_pictures"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state_picture_registry as registry  # noqa: E402


def fit(img, width, height):
    """Scale to cover width x height, then center-crop."""
    from PIL import Image

    w, h = img.size
    scale = max(width / w, height / h)
    nw, nh = max(width, round(w * scale)), max(height, round(h * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - width) // 2, (nh - height) // 2
    return img.crop((left, top, left + width, top + height))


def _window_mean(a, r, dy, dx):
    """The mean of the (r+1) x (r+1) window reaching from each pixel toward (dy, dx)."""
    import numpy as np

    pad = np.pad(a, ((r, r), (r, r)) + ((0, 0),) * (a.ndim - 2), mode="edge").astype(np.float64)
    s = np.cumsum(np.cumsum(pad, axis=0), axis=1)
    s = np.pad(s, ((1, 0), (1, 0)) + ((0, 0),) * (a.ndim - 2))
    h, w = a.shape[:2]
    y0 = 0 if dy < 0 else r
    x0 = 0 if dx < 0 else r
    y1, x1 = y0 + r + 1, x0 + r + 1
    total = (s[y1:y1 + h, x1:x1 + w] - s[y0:y0 + h, x1:x1 + w]
             - s[y1:y1 + h, x0:x0 + w] + s[y0:y0 + h, x0:x0 + w])
    return total / ((r + 1) ** 2)


def kuwahara(img, radius=PAINT_RADIUS):
    import numpy as np
    from PIL import Image

    a = np.asarray(img.convert("RGB"), dtype=np.float64)
    lum = a.mean(axis=2)
    best = np.full(lum.shape, np.inf)
    out = np.zeros_like(a)
    for dy in (-1, 1):
        for dx in (-1, 1):
            mean = _window_mean(lum, radius, dy, dx)
            var = _window_mean(lum * lum, radius, dy, dx) - mean * mean
            pick = var < best
            best = np.where(pick, var, best)
            out[pick] = _window_mean(a, radius, dy, dx)[pick]
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))


def smudge(img, boxes):
    """Blur each (left, top, right, bottom) box until its lettering is a dab of paint.

    The blur's reach follows the box's shorter side, so a sign keeps its place and its
    colors and loses its strokes; the edge of the box is feathered into the picture.
    """
    from PIL import Image, ImageDraw, ImageFilter

    for left, top, right, bottom in boxes:
        reach = max(4, min(right - left, bottom - top) // 3)
        pad = 2 * reach
        area = (max(0, left - pad), max(0, top - pad), min(img.width, right + pad), min(img.height, bottom + pad))
        patch = img.crop(area)
        blurred = patch.filter(ImageFilter.GaussianBlur(reach))
        mask = Image.new("L", patch.size, 0)
        ImageDraw.Draw(mask).rectangle((left - area[0], top - area[1], right - area[0], bottom - area[1]), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(max(2, reach // 2)))
        img.paste(Image.composite(blurred, patch, mask), area[:2])
    return img


def dark_edge(img, rows=3, floor=12):
    """'top' or 'bottom' if the picture's outermost rows are near black (a letterbox strip some
    renders carry), else None."""
    import numpy as np

    lum = np.asarray(img.convert("L"), dtype=float).mean(axis=1)
    if lum[-rows:].mean() < floor:
        return "bottom"
    if lum[:rows].mean() < floor:
        return "top"
    return None


def paint(source: Path, key: str):
    """The picture as it is committed, before compression: a 1020 x 500 RGB image."""
    from PIL import Image

    img = Image.open(source).convert("RGB")
    img = smudge(img, registry.PICTURES[key].get("smudge", []))
    crop = registry.PICTURES[key].get("crop")
    if crop:
        img = img.crop(crop)
    edge = dark_edge(img)
    if edge:
        raise ValueError(f"{key}: a dark strip along the {edge} of the render; give the entry a crop that drops it")
    img = fit(img, round(WIDTH * WORK_SCALE), round(HEIGHT * WORK_SCALE))
    img = Image.blend(img, kuwahara(img), PAINT_BLEND)
    return img.resize((WIDTH, HEIGHT), Image.LANCZOS)


def convert(key: str, source: Path, texconv: Path) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"te_{key}.dds"
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / f"te_{key}.png"
        paint(source, key).convert("RGBA").save(png, format="PNG")
        cmd = [str(texconv), "-f", "BC7_UNORM_SRGB", "-srgb", "-m", "0", "-y",
               "-o", _exe_path(OUT_DIR), _exe_path(png)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not out.exists():
            raise RuntimeError(f"texconv failed for {key}: {result.stdout}{result.stderr}")
    print(f"{out.relative_to(REPO)}  ({out.stat().st_size:,} bytes)")
    return out


def main() -> int:
    pairs = [a.split("=", 1) for a in sys.argv[1:]]
    if not pairs or any(len(p) != 2 for p in pairs):
        print(__doc__)
        return 2
    texconv = ensure_texconv()
    for key, source in pairs:
        convert(key, Path(source).expanduser(), texconv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
