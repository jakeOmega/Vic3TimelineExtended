#!/usr/bin/env python3
"""
convert_event_image.py - Convert images to Victoria 3 event-image DDS format.

Produces a 1700×1200 BC7-compressed DDS suitable for use in event_image blocks.
Requires:
  - Pillow          (pip install Pillow)
  - texconv.exe     (auto-downloaded from Microsoft DirectXTex on first run)

Usage:
    python convert_event_image.py input.png                 # -> input.dds
    python convert_event_image.py photo.jpg -o my_event.dds # explicit output
    python convert_event_image.py *.png                     # batch convert
    python convert_event_image.py img.png --format BC3      # use DXT5 instead
    python convert_event_image.py img.png --no-resize       # skip resize/crop

The resulting .dds should be placed under gfx/event_pictures/ in the mod and
referenced via `event_image = { texture = "gfx/event_pictures/my_event.dds" }`.
"""

from __future__ import annotations

import argparse
import io
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from glob import glob
from pathlib import Path
from urllib.request import urlopen

# ── constants ────────────────────────────────────────────────────────────
EVENT_WIDTH = 1700
EVENT_HEIGHT = 1200
ASPECT = EVENT_WIDTH / EVENT_HEIGHT  # ~1.4167

TEXCONV_URL = (
    "https://github.com/microsoft/DirectXTex/releases/latest/download/"
    "texconv.exe"
)

SCRIPT_DIR = Path(__file__).resolve().parent
TEXCONV_LOCAL = SCRIPT_DIR / "texconv.exe"

# Set to True/False in `main()` based on CLI flag
VERBOSE = True


# ── helpers ──────────────────────────────────────────────────────────────

def find_texconv() -> Path | None:
    """Return path to texconv.exe if available."""
    # 1. Check next to script
    if TEXCONV_LOCAL.is_file():
        return TEXCONV_LOCAL
    # 2. Check PATH
    found = shutil.which("texconv") or shutil.which("texconv.exe")
    if found:
        return Path(found)
    return None


def download_texconv() -> Path:
    """Download texconv.exe from Microsoft DirectXTex releases."""
    if VERBOSE:
        print(f"Downloading texconv.exe from {TEXCONV_URL} ...")
    try:
        with urlopen(TEXCONV_URL) as resp:
            data = resp.read()
        TEXCONV_LOCAL.write_bytes(data)
        if VERBOSE:
            print(f"  Saved to {TEXCONV_LOCAL}")
        return TEXCONV_LOCAL
    except Exception:
        # The latest release may ship a .zip instead of a bare .exe.
        # Try the zip URL as fallback.
        zip_url = TEXCONV_URL.replace("texconv.exe", "texconv.zip")
        if VERBOSE:
            print(f"  Direct download failed, trying {zip_url} ...")
        with urlopen(zip_url) as resp:
            data = resp.read()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                if name.lower().endswith("texconv.exe"):
                    with zf.open(name) as src:
                        TEXCONV_LOCAL.write_bytes(src.read())
                    if VERBOSE:
                        print(f"  Extracted to {TEXCONV_LOCAL}")
                    return TEXCONV_LOCAL
        raise RuntimeError("Could not find texconv.exe in downloaded archive.")


def ensure_texconv() -> Path:
    """Find or download texconv.exe."""
    path = find_texconv()
    if path:
        return path
    return download_texconv()


def resize_and_crop(img: "Image.Image") -> "Image.Image":
    """Resize & center-crop *img* to EVENT_WIDTH × EVENT_HEIGHT."""
    from PIL import Image  # noqa: local import

    w, h = img.size
    src_aspect = w / h

    if src_aspect > ASPECT:
        # Source is wider - fit height, crop sides
        new_h = EVENT_HEIGHT
        new_w = round(new_h * src_aspect)
    else:
        # Source is taller - fit width, crop top/bottom
        new_w = EVENT_WIDTH
        new_h = round(new_w / src_aspect)

    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Center crop
    left = (new_w - EVENT_WIDTH) // 2
    top = (new_h - EVENT_HEIGHT) // 2
    img = img.crop((left, top, left + EVENT_WIDTH, top + EVENT_HEIGHT))
    return img


def convert_image(
    input_path: Path,
    output_path: Path | None,
    texconv: Path,
    fmt: str = "BC7_UNORM_SRGB",
    do_resize: bool = True,
) -> Path:
    """Convert a single image to event-image DDS.

    Returns the path to the produced .dds.
    """
    from PIL import Image  # noqa: local import

    img = Image.open(input_path).convert("RGBA")

    if do_resize:
        img = resize_and_crop(img)
        if VERBOSE:
            print(f"  Resized to {img.size[0]}×{img.size[1]}")

    # Write intermediate PNG to a temp dir (texconv reads it)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_png = Path(tmpdir) / "temp_input.png"
        img.save(tmp_png, format="PNG")

        # Determine output location
        if output_path is None:
            output_path = input_path.with_suffix(".dds")
        out_dir = output_path.parent
        out_name = output_path.stem

        # Run texconv
        cmd = [
            str(texconv),
            "-f", fmt,
            "-y",               # overwrite
            "-srgb",            # sRGB color space
            "-o", str(out_dir),
            str(tmp_png),
        ]
        if VERBOSE:
            print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  texconv stderr: {result.stderr}")
            raise RuntimeError(f"texconv failed (exit {result.returncode})")

        # texconv outputs to out_dir/temp_input.dds - move/replace to target
        produced = out_dir / "temp_input.dds"
        if not produced.exists():
            raise RuntimeError("texconv did not produce temp_input.dds as expected.")

        try:
            # Use replace() to atomically overwrite existing target if present
            produced.replace(output_path)
        except Exception:
            # Fallback: remove target if it exists and rename
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            produced.rename(output_path)

    if VERBOSE:
        print(f"  ✓ {output_path}  ({output_path.stat().st_size:,} bytes)")
    return output_path


# ── CLI ──────────────────────────────────────────────────────────────────

FORMAT_MAP = {
    "BC7": "BC7_UNORM_SRGB",
    "BC3": "BC3_UNORM_SRGB",
    "DXT5": "BC3_UNORM_SRGB",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Convert images to Victoria 3 event-image DDS (1700×1200, BC7).",
    )
    p.add_argument(
        "inputs",
        nargs="+",
        help="Input image file(s). Supports glob patterns on Windows.",
    )
    p.add_argument(
        "-o", "--output",
        default=None,
        help="Output .dds path (only valid with a single input).",
    )
    p.add_argument(
        "--format",
        choices=["BC7", "BC3", "DXT5"],
        default="BC7",
        help="DDS compression format (default: BC7).",
    )
    p.add_argument(
        "--no-resize",
        action="store_true",
        help="Skip resize/crop - use input dimensions as-is.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output files instead of skipping them.",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Set global verbosity according to CLI
    global VERBOSE
    VERBOSE = bool(args.verbose)

    # Expand globs on Windows (cmd.exe doesn't expand them)
    # Expand globs on Windows (cmd.exe doesn't expand them). Also support
    # passing a directory: collect supported image files and convert them
    # into a `converted` subfolder inside that directory.
    SUPPORTED_EXTS = {'.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.tga', '.gif', '.webp'}
    raw_paths: list[Path] = []
    for pattern in args.inputs:
        expanded = glob(pattern)
        if expanded:
            raw_paths.extend(Path(f) for f in expanded)
        else:
            raw_paths.append(Path(pattern))

    files: list[Path] = []
    for p in raw_paths:
        if p.is_dir():
            for child in sorted(p.iterdir()):
                if child.is_file() and child.suffix.lower() in SUPPORTED_EXTS:
                    files.append(child)
        elif p.is_file():
            files.append(p)
        else:
            # keep non-existent paths for the existing warning later
            files.append(p)

    if len(files) > 1 and args.output:
        print("Error: -o/--output can only be used with a single input file.")
        sys.exit(1)

    # Ensure dependencies
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("Pillow is not installed. Installing ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        from PIL import Image  # noqa: F401

    texconv = ensure_texconv()
    fmt = FORMAT_MAP[args.format]

    for f in files:
        if not f.is_file():
            if VERBOSE:
                print(f"Warning: {f} not found, skipping.")
            continue
        if VERBOSE:
            print(f"Converting {f} ...")

        # Determine per-file output. If a single explicit output was passed
        # it was already validated above. Otherwise place outputs into a
        # `converted` subfolder next to the input file.
        if args.output:
            out = Path(args.output)
        else:
            out_dir = f.parent / "converted"
            out_dir.mkdir(parents=True, exist_ok=True)
            out = out_dir / f.with_suffix('.dds').name

        # Skip if output already exists unless --force was passed
        if out.exists() and not args.force:
            if VERBOSE:
                print(f"Skipping {f} -> {out} (already exists). Use --force to overwrite.")
            continue

        convert_image(f, out, texconv, fmt=fmt, do_resize=not args.no_resize)


if __name__ == "__main__":
    main()
