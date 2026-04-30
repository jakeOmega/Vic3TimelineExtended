#!/usr/bin/env python3
"""
create_event_video.py - Generate a panning BK2 video from a still image.

Produces a 1700×1200 video at 30 fps with a slow Ken Burns (pan/zoom) effect,
suitable for Victoria 3 event_image video blocks.

Pipeline:
  1. Pillow generates frames with a slow pan/zoom over the source image.
  2. imageio + imageio-ffmpeg assembles frames into an uncompressed AVI.
  3. Open RAD Video Tools GUI → select the AVI → click "Bink it!" → BK2.

Requires:
  - Pillow              (pip install Pillow)
  - imageio + ffmpeg    (pip install imageio imageio-ffmpeg)
  For .bk2 output (manual GUI step):
  - RAD Video Tools     (free: https://www.radgametools.com/bnkdown.htm)

Usage:
    python create_event_video.py input.png                       # -> input.avi
    python create_event_video.py photo.jpg -o my_event           # explicit stem
    python create_event_video.py img.png --duration 10           # 10 seconds
    python create_event_video.py img.png --pan left_to_right     # pan direction
    python create_event_video.py img.png --pan zoom_in           # zoom effect

Pan modes:
    ken_burns       Gentle drift right + zoom-in (default, cinematic)
    left_to_right   Horizontal pan left to right
    right_to_left   Horizontal pan right to left
    zoom_in         Slow push-in (zoom toward center)
    zoom_out        Slow pull-out (zoom away from center)

Victoria 3 event video specs (vanilla reference):
    Resolution  1700 × 1200
    FPS         30
    Duration    ~10 seconds (300 frames)
    Audio       None
    Format      Bink Video 2 (.bk2)

The resulting .bk2 should be placed under gfx/event_pictures/ and referenced
via `event_image = { video = "my_event" }` (stem only, no extension/path).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# ── constants ────────────────────────────────────────────────────────────
EVENT_WIDTH = 1700
EVENT_HEIGHT = 1200
EVENT_ASPECT = EVENT_WIDTH / EVENT_HEIGHT

DEFAULT_FPS = 30
DEFAULT_DURATION = 10  # seconds - matches vanilla (300 frames)
DEFAULT_MARGIN = 0.15  # 15% extra on each side for panning headroom

SCRIPT_DIR = Path(__file__).resolve().parent

RAD_TOOLS_SEARCH_PATHS = [
    Path(r"C:\Program Files (x86)\RADVideo"),
    Path(r"C:\Program Files\RADVideo"),
    Path(r"C:\Program Files (x86)\RAD Video Tools"),
    Path(r"C:\Program Files\RAD Video Tools"),
]
# The free RAD Video Tools distribution only includes a GUI - the command-line
# Bink encoder ("bink2.exe") is part of the paid SDK and not normally available.
# radvideo64.exe IS the GUI; binkplay/smackplw are just players (not encoders).
RAD_GUI_NAMES = ["radvideo64.exe", "radvideo32.exe"]

PAN_MODES = ["ken_burns", "left_to_right", "right_to_left", "zoom_in", "zoom_out"]


# ── math helpers ─────────────────────────────────────────────────────────

def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation from *a* to *b* at fraction *t*."""
    return a + (b - a) * t


def ease_in_out(t: float) -> float:
    """Smoothstep easing: slow start, fast middle, slow end."""
    return t * t * (3.0 - 2.0 * t)


# ── dependency management ────────────────────────────────────────────────

def ensure_deps() -> None:
    """Auto-install required Python packages if missing."""
    missing: list[str] = []

    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        missing.append("Pillow")

    try:
        import imageio  # noqa: F401
    except ImportError:
        missing.append("imageio")

    try:
        import imageio_ffmpeg  # noqa: F401
    except ImportError:
        missing.append("imageio-ffmpeg")

    try:
        import numpy  # noqa: F401
    except ImportError:
        missing.append("numpy")

    if missing:
        print(f"Installing: {', '.join(missing)} ...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *missing],
            stdout=subprocess.DEVNULL,
        )


# ── image helpers ────────────────────────────────────────────────────────

def prepare_canvas(
    img: "Image.Image",
    margin: float = DEFAULT_MARGIN,
) -> "Image.Image":
    """Resize *img* to a canvas larger than 1700×1200, providing panning room.

    Uses "cover" scaling: the image fills the canvas completely, cropping
    the excess dimension.
    """
    from PIL import Image as PILImage

    canvas_w = int(EVENT_WIDTH * (1 + 2 * margin))
    canvas_h = int(EVENT_HEIGHT * (1 + 2 * margin))

    w, h = img.size
    src_aspect = w / h
    canvas_aspect = canvas_w / canvas_h

    # Cover mode - scale to fill, then center-crop
    if src_aspect > canvas_aspect:
        new_h = canvas_h
        new_w = round(new_h * src_aspect)
    else:
        new_w = canvas_w
        new_h = round(new_w / src_aspect)

    img = img.resize((new_w, new_h), PILImage.LANCZOS)

    left = (new_w - canvas_w) // 2
    top = (new_h - canvas_h) // 2
    return img.crop((left, top, left + canvas_w, top + canvas_h))


def generate_frame(
    canvas: "Image.Image",
    t: float,
    pan_mode: str,
) -> "Image.Image":
    """Return a single 1700×1200 frame at normalised time *t* ∈ [0, 1]."""
    from PIL import Image as PILImage

    cw, ch = canvas.size
    t_s = ease_in_out(t)  # smoothed time

    if pan_mode == "ken_burns":
        zoom = lerp(1.10, 1.00, t_s)
        drift = lerp(-0.03, 0.03, t_s) * cw
        crop_w = EVENT_WIDTH * zoom
        crop_h = EVENT_HEIGHT * zoom
        cx = cw / 2 + drift
        cy = ch / 2

    elif pan_mode == "left_to_right":
        crop_w = float(EVENT_WIDTH)
        crop_h = float(EVENT_HEIGHT)
        margin_x = cw - EVENT_WIDTH
        cx = EVENT_WIDTH / 2 + margin_x * t_s
        cy = ch / 2

    elif pan_mode == "right_to_left":
        crop_w = float(EVENT_WIDTH)
        crop_h = float(EVENT_HEIGHT)
        margin_x = cw - EVENT_WIDTH
        cx = EVENT_WIDTH / 2 + margin_x * (1.0 - t_s)
        cy = ch / 2

    elif pan_mode == "zoom_in":
        zoom = lerp(1.25, 1.00, t_s)
        crop_w = EVENT_WIDTH * zoom
        crop_h = EVENT_HEIGHT * zoom
        cx = cw / 2
        cy = ch / 2

    elif pan_mode == "zoom_out":
        zoom = lerp(1.00, 1.25, t_s)
        crop_w = EVENT_WIDTH * zoom
        crop_h = EVENT_HEIGHT * zoom
        cx = cw / 2
        cy = ch / 2

    else:
        raise ValueError(f"Unknown pan mode: {pan_mode}")

    # Compute crop box and clamp to canvas bounds
    left = max(0, int(cx - crop_w / 2))
    top = max(0, int(cy - crop_h / 2))
    right = min(cw, int(cx + crop_w / 2))
    bottom = min(ch, int(cy + crop_h / 2))

    frame = canvas.crop((left, top, right, bottom))
    return frame.resize((EVENT_WIDTH, EVENT_HEIGHT), PILImage.LANCZOS)


# ── video assembly ───────────────────────────────────────────────────────

def assemble_video(
    canvas: "Image.Image",
    output_avi: Path,
    fps: int,
    duration: float,
    pan_mode: str,
) -> None:
    """Generate panning frames and write to uncompressed AVI via imageio + ffmpeg.

    Uses rawvideo BGR24 - large file, but guaranteed compatible with RAD Video
    Tools which is picky about AVI codecs.
    """
    import imageio.v2 as imageio
    import numpy as np

    num_frames = int(fps * duration)
    est_bytes = EVENT_WIDTH * EVENT_HEIGHT * 3 * num_frames
    est_mb = est_bytes / (1024 * 1024)
    print(f"  Generating {num_frames} frames ({duration}s @ {fps} fps, mode={pan_mode}) ...")
    print(f"  Estimated AVI size: ~{est_mb:.0f} MB (uncompressed, RAD-compatible)")

    writer = imageio.get_writer(
        str(output_avi),
        fps=fps,
        format="FFMPEG",
        codec="rawvideo",
        output_params=["-pix_fmt", "bgr24"],
    )

    try:
        for i in range(num_frames):
            t = i / max(num_frames - 1, 1)
            frame = generate_frame(canvas, t, pan_mode)
            writer.append_data(np.asarray(frame))
            if (i + 1) % fps == 0 or i == num_frames - 1:
                pct = 100 * (i + 1) / num_frames
                print(f"    {i + 1}/{num_frames} ({pct:.0f}%)", end="\r")
    finally:
        writer.close()

    size_mb = output_avi.stat().st_size / (1024 * 1024)
    print(f"\n  ✓ {output_avi}  ({size_mb:.1f} MB)")


# ── BK2 conversion ──────────────────────────────────────────────────────

def find_rad_gui() -> Path | None:
    """Locate the RAD Video Tools GUI (radvideo64.exe or radvideo32.exe)."""
    for base in RAD_TOOLS_SEARCH_PATHS:
        for name in RAD_GUI_NAMES:
            candidate = base / name
            if candidate.is_file():
                return candidate

    for name in RAD_GUI_NAMES:
        found = shutil.which(name)
        if found:
            return Path(found)

    return None


def convert_to_bk2(avi_path: Path, bk2_path: Path) -> bool:
    """Open RAD Video Tools GUI for manual AVI → BK2 conversion.

    The free RAD Video Tools distribution does not include a command-line Bink
    encoder - only the GUI (radvideo64.exe) which has a "Bink it!" button.
    We launch the GUI pointed at the AVI's directory so the user can select
    the file and encode it interactively.
    """
    gui = find_rad_gui()

    print()
    if gui:
        print(f"  Opening RAD Video Tools GUI ...")
        print(f"  In the GUI:")
        print(f"    1. Navigate to: {avi_path.parent}")
        print(f"    2. Select: {avi_path.name}")
        print(f"    3. Click 'Bink it!'")
        print(f"    4. In the Bink compression dialog, click 'Bink' to compress.")
        print(f"    5. Output will be: {bk2_path}")
        print()

        # Launch the GUI - it accepts a directory path as argument
        try:
            subprocess.Popen(
                [str(gui), str(avi_path.parent)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"  ✓ RAD Video Tools launched.")
        except OSError as e:
            print(f"  ⚠ Could not launch GUI: {e}")
            print(f"    Open manually: {gui}")
    else:
        print("  ⚠ RAD Video Tools not found.")
        print("    Download (free): https://www.radgametools.com/bnkdown.htm")
        print()
        print(f"  After installing, to convert to BK2:")
        print(f"    1. Open RAD Video Tools (radvideo64.exe)")
        print(f"    2. Navigate to: {avi_path.parent}")
        print(f"    3. Select: {avi_path.name}")
        print(f"    4. Click 'Bink it!'")
        print(f"    5. In the Bink compression dialog, click 'Bink' to compress.")

    return False


# ── CLI ──────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Generate a panning event video from a still image for Victoria 3. "
            "Outputs an intermediate AVI (and optionally converts to .bk2)."
        ),
    )
    p.add_argument("input", help="Input image file (PNG, JPG, etc.).")
    p.add_argument(
        "-o", "--output",
        default=None,
        help="Output filename stem (without extension). Defaults to input stem.",
    )
    p.add_argument(
        "--duration",
        type=float,
        default=DEFAULT_DURATION,
        help=f"Video duration in seconds (default: {DEFAULT_DURATION}).",
    )
    p.add_argument(
        "--fps",
        type=int,
        default=DEFAULT_FPS,
        help=f"Frames per second (default: {DEFAULT_FPS}).",
    )
    p.add_argument(
        "--pan",
        choices=PAN_MODES,
        default="ken_burns",
        help="Pan/zoom mode (default: ken_burns).",
    )
    p.add_argument(
        "--margin",
        type=float,
        default=DEFAULT_MARGIN,
        help=f"Panning headroom as fraction of frame size (default: {DEFAULT_MARGIN}).",
    )
    p.add_argument(
        "--no-bk2",
        action="store_true",
        help="Only produce AVI, skip BK2 conversion attempt.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"Error: {input_path} not found.")
        sys.exit(1)

    stem = args.output if args.output else input_path.stem
    output_dir = input_path.parent
    avi_path = output_dir / f"{stem}.avi"
    bk2_path = output_dir / f"{stem}.bk2"

    # ── ensure dependencies ──────────────────────────────────────────
    ensure_deps()
    from PIL import Image

    # ── load and prepare canvas ──────────────────────────────────────
    print(f"Loading {input_path} ...")
    img = Image.open(input_path).convert("RGB")
    print(f"  Source: {img.size[0]}×{img.size[1]}")

    canvas = prepare_canvas(img, margin=args.margin)
    print(f"  Canvas: {canvas.size[0]}×{canvas.size[1]} ({args.margin:.0%} margin)")

    # ── generate video ───────────────────────────────────────────────
    assemble_video(canvas, avi_path, args.fps, args.duration, args.pan)

    # ── convert to BK2 ──────────────────────────────────────────────
    if not args.no_bk2:
        convert_to_bk2(avi_path, bk2_path)

    # ── usage hint ───────────────────────────────────────────────────
    print()
    print(f"Place the .bk2 in gfx/event_pictures/ and reference as:")
    print(f'  event_image = {{ video = "{stem}" }}')


if __name__ == "__main__":
    main()
