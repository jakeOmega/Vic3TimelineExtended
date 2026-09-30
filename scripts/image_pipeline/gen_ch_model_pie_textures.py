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

The UN overview's member-share pies use a pair of their own in the same
format (`UN_PIES`, written to gfx/interface/icons/un_icons/): members in UN
blue over the rest in a muted grey. Validated the same way against the dark
panel: dE 16.8 normal and 16.9 protan; the grey fails only the chroma floor,
as intended for the part that is not the subject.

The system panels' pies (the style pass, `PANEL_PIES`) follow the UN's: a
fill over the same muted grey. The colours their icon lists proposed failed
the validator's normal-vision floor against that grey (dE 12-13; the GW green's
deutan dE was 5.4), so each is the nearest lighter step that clears it:
Cultural Hegemony's share #d89a2b (dE 16.1 normal, 14.0 protan), Global
Warming's share #e0661a (15.6, 10.0) and cut #4fb85a (17.5, 10.2). They sit
above the categorical lightness band on purpose: a single subject over the
rest, not one of several equal slices. List 2's three-slice pies (Colonial
Empire, Space Race) were checked on every pair, the wrap-around included.

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
UN_OUTPUT_DIR = Path(mod_path) / "gfx" / "interface" / "icons" / "un_icons"
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

# The UN overview's pie: the fill (members' share) and the disc under it.
UN_PIES: tuple[tuple[str, str], ...] = (
    ("pie_members", "#5b92e5"),
    ("pie_rest", "#8c8474"),
)

# The system panels' pies (docs/systems/<system>_gui_icons.md): path under
# gfx/interface/, and colour. Each fill is validated against the grey rest.
PANEL_PIES: tuple[tuple[str, str], ...] = (
    ("journal_entry_widgets/ch_model_pie/ch_share_fill.dds", "#d89a2b"),
    ("journal_entry_widgets/ch_model_pie/ch_share_rest.dds", "#8c8474"),
    ("icons/gw_icons/pie_share.dds", "#e0661a"),
    ("icons/gw_icons/pie_cut.dds", "#4fb85a"),
    # List 2 (provisional). Colonial Empire: condemners over supporters over
    # the rest, three slices side by side, so every pair was checked
    # (`--pairs all`: worst dE 8.1 deutan, 15.6 normal).
    ("icons/colonial_empire_icons/pie_condemners.dds", "#dd4a3a"),
    ("icons/colonial_empire_icons/pie_supporters.dds", "#4cbc9a"),
    ("icons/colonial_empire_icons/pie_rest.dds", "#8c8474"),
    # Space Race: ours over everyone's claims over the unclaimed rest
    # (worst dE 8.7 deutan, 16.2 normal).
    ("icons/space_race_icons/pie_unclaimed.dds", "#8c8474"),
    ("icons/space_race_icons/pie_claimed.dds", "#cf4a2a"),
    ("icons/space_race_icons/pie_ours.dds", "#ecc043"),
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
    jobs = [(OUTPUT_DIR / f"ch_pie_{model}.dds", colour) for model, colour in MODELS]
    jobs += [(UN_OUTPUT_DIR / f"{key}.dds", colour) for key, colour in UN_PIES]
    jobs += [(Path(mod_path) / "gfx" / "interface" / rel, colour) for rel, colour in PANEL_PIES]
    for out, colour in jobs:
        write_dds(render(colour), out)
        print(f"wrote {out.relative_to(mod_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
