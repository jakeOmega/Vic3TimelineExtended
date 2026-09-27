#!/usr/bin/env python3
"""
contact_sheet.py - Render event pictures side by side, labelled, to one PNG.

A prompt in event_image_prompts.py records what was asked for, not what FLUX
drew: some pictures carry real national flags, landmarks or a politician's
likeness that the prompt never mentioned. Look before reusing a picture on a
new event, and review freshly generated ones before `--phase update` wires them.

Usage:
    python3 contact_sheet.py un_assembly bank_run_crowd -o /tmp/sheet.png
    python3 contact_sheet.py --event nuclear_crisis.20 nuclear_crisis.21
    python3 contact_sheet.py generated_images/new_image.png

Arguments are picture names (stems under gfx/event_pictures), paths to image
files, or with --event, event IDs whose current texture is shown. A picture
missing from disk is read from git's HEAD, so this works in a sparse worktree
that leaves gfx/ unchecked-out. Needs Pillow with BC7 support for the .dds
files (Pillow >= 9; the project .venv does not install it, system python3
usually has it). Then open the PNG, or read it with an agent's image-viewing
tool.
"""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
from pathlib import Path

MOD_ROOT = Path(__file__).resolve().parents[2]
GFX_DIR = MOD_ROOT / "gfx" / "event_pictures"
THUMB_W, THUMB_H, LABEL_H = 400, 282, 22


def resolve(arg: str) -> tuple[str, Path]:
    p = Path(arg)
    if p.suffix and p.exists():
        return p.stem, p
    return arg, GFX_DIR / f"{arg}.dds"


def open_picture(path: Path):
    """Open an image file, or its committed blob when gfx/ is not checked out."""
    from PIL import Image
    if path.is_file():
        return Image.open(path)
    if not path.name:
        return None
    try:
        rel = path.resolve().relative_to(MOD_ROOT).as_posix()
    except ValueError:
        return None
    blob = subprocess.run(["git", "-C", str(MOD_ROOT), "cat-file", "blob", f"HEAD:{rel}"],
                          capture_output=True)
    if blob.returncode != 0:
        return None
    return Image.open(io.BytesIO(blob.stdout))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("items", nargs="+", help="picture names, image paths, or event IDs")
    ap.add_argument("--event", action="store_true", help="items are event IDs")
    ap.add_argument("-o", "--output", default="contact_sheet.png")
    ap.add_argument("--cols", type=int, default=4)
    args = ap.parse_args()

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow is not installed for this interpreter; try system python3.")
        return 1

    entries: list[tuple[str, Path]] = []
    if args.event:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import event_image_inventory as inv
        arts = inv.load(str(MOD_ROOT))
        for eid in args.items:
            art = arts.get(eid)
            pic = art.picture if art else None
            label = f"{eid}: {pic or (art.kind if art else 'no such event')}"
            entries.append((label, GFX_DIR / f"{pic}.dds" if pic else Path("")))
    else:
        entries = [resolve(a) for a in args.items]

    cols = max(1, min(args.cols, len(entries)))
    rows = (len(entries) + cols - 1) // cols
    sheet = Image.new("RGB", (THUMB_W * cols, (THUMB_H + LABEL_H) * rows), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    missing = 0
    for i, (label, path) in enumerate(entries):
        x, y = (i % cols) * THUMB_W, (i // cols) * (THUMB_H + LABEL_H)
        draw.text((x + 4, y + 2), label[:44], fill="black", font=font)
        im = open_picture(path)
        if im is not None:
            sheet.paste(im.convert("RGB").resize((THUMB_W, THUMB_H)), (x, y + LABEL_H))
        else:
            missing += 1
            draw.text((x + 12, y + LABEL_H + 12), "(no picture file)", fill="red", font=font)
    sheet.save(args.output)
    print(f"Wrote {args.output} ({len(entries)} pictures, {missing} missing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
