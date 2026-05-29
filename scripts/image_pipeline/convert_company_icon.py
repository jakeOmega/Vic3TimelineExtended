#!/usr/bin/env python3
"""
convert_company_icon.py - Convert source logos to Victoria 3 company-icon DDS.

Produces a 256×256 BC7 DDS suitable for use in `icon = "..."` on a
company_type. Source images are fit-within (preserve aspect ratio, centered
on a transparent canvas) rather than center-cropped, so non-square logos
(banner-shape, portrait-shape) don't get clipped.

Requires:
  - Pillow      (pip install Pillow)
  - texconv.exe (auto-downloaded by convert_event_image.py's helper)

Usage:
    # Single file, infer output name (input.png -> ./input.dds)
    python convert_company_icon.py Sibur.png

    # Single file, explicit output (typical mod-folder destination)
    python convert_company_icon.py Sibur.png \\
        -o gfx/interface/icons/company_icons/historical_company_icons/russian_sibur.dds

    # Batch convert a directory into a `converted/` subfolder
    python convert_company_icon.py "/mnt/c/path/to/companies/"
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from glob import glob
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from convert_event_image import ensure_texconv  # noqa: E402

ICON_SIZE = 256
VERBOSE = True


def fit_to_square(img):
    """Return *img* fit within ICON_SIZE×ICON_SIZE, centered on a transparent canvas."""
    from PIL import Image  # noqa: local import

    img = img.convert("RGBA")
    w, h = img.size
    scale = min(ICON_SIZE / w, ICON_SIZE / h)
    new_w, new_h = max(1, round(w * scale)), max(1, round(h * scale))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    canvas.paste(resized, ((ICON_SIZE - new_w) // 2, (ICON_SIZE - new_h) // 2), resized)
    return canvas


def _winpath(p: Path) -> str:
    """texconv.exe is a Windows binary — paths must be Windows-style when invoked from WSL."""
    try:
        return subprocess.check_output(["wslpath", "-w", str(p)], text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return str(p)


def convert(input_path: Path, output_path: Path, texconv: Path) -> Path:
    from PIL import Image  # noqa: local import

    img = Image.open(input_path)
    fitted = fit_to_square(img)
    if VERBOSE:
        print(f"  Fit {img.size[0]}×{img.size[1]} -> {ICON_SIZE}×{ICON_SIZE} (centered, transparent padding)")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_png = Path(tmpdir) / "temp_input.png"
        fitted.save(tmp_png, format="PNG")
        out_dir = output_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(texconv),
            "-f", "BC7_UNORM_SRGB",
            "-y",
            "-srgb",
            "-o", _winpath(out_dir),
            _winpath(tmp_png),
        ]
        if VERBOSE:
            print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  texconv stderr: {result.stderr}")
            raise RuntimeError(f"texconv failed (exit {result.returncode})")

        produced = out_dir / "temp_input.dds"
        if not produced.exists():
            raise RuntimeError("texconv did not produce temp_input.dds as expected.")
        if output_path.exists():
            output_path.unlink()
        produced.rename(output_path)

    if VERBOSE:
        print(f"  ✓ {output_path}  ({output_path.stat().st_size:,} bytes)")
    return output_path


def main() -> None:
    p = argparse.ArgumentParser(description="Convert source logos to Vic3 company-icon DDS (256×256 BC7).")
    p.add_argument("inputs", nargs="+", help="Input image file(s) or directory. Supports glob patterns.")
    p.add_argument("-o", "--output", help="Output .dds path (single input only).")
    p.add_argument("-q", "--quiet", action="store_true")
    args = p.parse_args()

    global VERBOSE
    VERBOSE = not args.quiet

    SUPPORTED = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tga", ".webp"}
    raw: list[Path] = []
    for pattern in args.inputs:
        expanded = glob(pattern)
        if expanded:
            raw.extend(Path(f) for f in expanded)
        else:
            raw.append(Path(pattern))
    files: list[Path] = []
    for p_ in raw:
        if p_.is_dir():
            for child in sorted(p_.iterdir()):
                if child.is_file() and child.suffix.lower() in SUPPORTED:
                    files.append(child)
        else:
            files.append(p_)

    if args.output and len(files) > 1:
        print("Error: -o/--output requires exactly one input.", file=sys.stderr)
        sys.exit(2)

    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])

    texconv = ensure_texconv()
    for f in files:
        if not f.is_file():
            print(f"Warning: {f} not found, skipping.")
            continue
        if VERBOSE:
            print(f"Converting {f} ...")
        if args.output:
            out = Path(args.output)
        else:
            out_dir = f.parent / "converted"
            out_dir.mkdir(parents=True, exist_ok=True)
            out = out_dir / f.with_suffix(".dds").name
        convert(f, out, texconv)


if __name__ == "__main__":
    main()
