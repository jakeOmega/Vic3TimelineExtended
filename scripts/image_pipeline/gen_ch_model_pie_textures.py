"""Generate the Cultural Hegemony political-model pie-chart textures.

The journal entry's "Political models" section draws its pie as fifteen stacked
`progresspie` widgets, one per model, each filled to that model's cumulative
share. A progresspie paints frame 1 of its texture as the unfilled background
and frame 2 as the fill, and vanilla colours a pie by baking the colour into
frame 2 (sidebar_progress.dds / sidebar_progress_red.dds) rather than tinting
it, so each model gets its own texture:

    frame 1 (left half)   fully transparent, so lower layers show through
    frame 2 (right half)  an antialiased disc in the model's colour

Written to gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_<model>.dds
as uncompressed RGBA8888 DDS. The same textures serve as the legend swatches.

The colours were chosen with the dataviz skill's palette validator against the
dark journal-entry panel, and the ORDER is the pie's clockwise slice order
(`MODELS` below, mirrored in cultural_hegemony_script_values.txt): every pair of
neighbouring slices, including the wrap-around, clears CVD dE 8 and
normal-vision dE 15. "Other" is grey on purpose. Fifteen categories are too
many for colour alone, so the legend's names and percentages carry identity.

Run standalone (numpy only; no Pillow needed):
    .venv/bin/python scripts/image_pipeline/gen_ch_model_pie_textures.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from path_constants import mod_path  # noqa: E402

OUTPUT_DIR = Path(mod_path) / "gfx" / "interface" / "journal_entry_widgets" / "ch_model_pie"
FRAME = 128  # pixels per frame side; the texture is 2 * FRAME wide

# Clockwise slice order, starting at 12 o'clock.
MODELS: tuple[tuple[str, str], ...] = (
    ("republican", "#4b9bcf"),
    ("corporatist", "#c56c21"),
    ("anarchist", "#9b3876"),
    ("other", "#7c7a74"),
    ("royalist_absolutist", "#6849ab"),
    ("technocratic", "#009b95"),
    ("religious", "#897311"),
    ("socialist", "#d46e80"),
    ("military_junta", "#556e1c"),
    ("royalist_constitutional", "#927ccd"),
    ("communist", "#c44039"),
    ("liberal", "#b68b16"),
    ("reactionary", "#2460a8"),
    ("developmentalist_junta", "#4ea253"),
    ("fascist", "#8e4c2c"),
)


def _dds_header(w: int, h: int) -> bytes:
    """Uncompressed 32-bit BGRA DDS header (same layout as gen_prestige_icons)."""
    flags = 0x1 | 0x2 | 0x4 | 0x8 | 0x1000  # caps | height | width | pitch | pixelformat
    return b"".join((
        b"DDS ",
        struct.pack("<7I", 124, flags, h, w, w * 4, 0, 0),
        b"\x00" * 44,
        struct.pack("<2I", 32, 0x1 | 0x40),  # pixel format: alpha | rgb
        b"\x00" * 4,
        struct.pack("<5I", 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000),
        struct.pack("<I", 0x1000),  # caps: texture
        b"\x00" * 16,
    ))


def _disc_alpha(size: int) -> np.ndarray:
    """Coverage of a disc filling the frame, antialiased over one pixel."""
    centre = (size - 1) / 2
    radius = size / 2 - 1
    ys, xs = np.mgrid[0:size, 0:size]
    dist = np.hypot(xs - centre, ys - centre)
    return np.clip(radius - dist + 0.5, 0.0, 1.0)


def render(colour: str) -> np.ndarray:
    """(FRAME, 2 * FRAME, 4) RGBA: transparent frame 1, coloured disc in frame 2."""
    rgb = [int(colour[i:i + 2], 16) for i in (1, 3, 5)]
    img = np.zeros((FRAME, 2 * FRAME, 4), dtype=np.uint8)
    img[:, FRAME:, 0:3] = rgb
    img[:, FRAME:, 3] = np.round(_disc_alpha(FRAME) * 255).astype(np.uint8)
    return img


def write_dds(img: np.ndarray, path: Path) -> None:
    h, w = img.shape[:2]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_dds_header(w, h) + img[..., [2, 1, 0, 3]].tobytes())


def main() -> int:
    for model, colour in MODELS:
        out = OUTPUT_DIR / f"ch_pie_{model}.dds"
        write_dds(render(colour), out)
        print(f"wrote {out.relative_to(mod_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
