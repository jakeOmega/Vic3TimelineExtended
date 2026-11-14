#!/usr/bin/env python3
"""
reframe_event_image.py - Move an event picture's subject into the half the
player sees, without rendering the picture again.

The event window lays its text panel over the right half of a picture
(docs/guides/event_creation_guide.md), so the subject belongs on the left.
Two edits get it there:

  --mirror      Flip the picture left to right. For a subject on the right.
                Not for a picture with lettering, a flag or emblem, a map or
                a coastline anyone would know, a clock face or a written page:
                they read wrong reversed.
  --shift F     Extend the picture on the right and crop the same width off
                the left, so everything moves left by the fraction F of the
                width (0.2 moves a centered subject to 30%). The extension is
                the picture's right edge reflected. F is capped at 0.45 so
                the reflection always lies under the text panel, where the
                window fades the picture out. What is lost is the leftmost F
                of the picture: look at it first.

Both may be given; the mirror is applied first. The size does not change.

Usage:
    python3 reframe_event_image.py mars_dusty_landing --shift 0.2
    python3 reframe_event_image.py orbital_earth_view --mirror -o /tmp/o.png
    python3 reframe_event_image.py NAME --shift 0.2 -o gfx/event_pictures/NAME.dds

The argument is a picture name (a stem under gfx/event_pictures, read from
git's HEAD when gfx/ is not checked out) or a path to an image file. The
default output is generated_images/reframed/NAME.png. Look at it as the window
shows it (`contact_sheet.py --window generated_images/reframed/NAME.png`),
then write the texture by naming a .dds output: that goes through
convert_event_image.py and needs texconv and a checkout that has gfx/.
Needs Pillow (system python3 usually has it; see contact_sheet.py).

The tool reads the texture in the checkout, so run it once per picture: a
second --mirror undoes the first and a second --shift adds to it. Record the
edit on the picture's entry in event_image_prompts.py ("reframed": "mirror" or
"shift 0.2"); a render from the entry's prompt would undo it.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import contact_sheet  # noqa: E402

# The reflected extension starts at 1 - F of the width. Keeping F under the
# covered share (1 - contact_sheet.PANEL_LEFT, about 0.49) keeps the seam and
# everything right of it beneath the text panel.
MAX_SHIFT = 0.45


def mirror(im):
    """*im* flipped left to right."""
    from PIL import ImageOps
    return ImageOps.mirror(im)


def shift_left(im, fraction: float):
    """*im* with its content moved left by *fraction* of the width.

    The leftmost strip is dropped and the right is filled with the mirror
    image of the strip that now ends the picture. Same size as *im*.
    """
    from PIL import Image, ImageOps
    if not 0 < fraction <= MAX_SHIFT:
        raise ValueError(f"shift must be over 0 and at most {MAX_SHIFT}, got {fraction}")
    w, h = im.size
    dx = round(w * fraction)
    out = Image.new(im.mode, (w, h))
    out.paste(im.crop((dx, 0, w, h)), (0, 0))
    out.paste(ImageOps.mirror(im.crop((w - dx, 0, w, h))), (w - dx, 0))
    return out


def reframe(im, do_mirror: bool = False, shift: float = 0.0):
    if do_mirror:
        im = mirror(im)
    if shift:
        im = shift_left(im, shift)
    return im


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("picture", help="picture name or image path")
    ap.add_argument("--mirror", action="store_true", help="flip left to right")
    ap.add_argument("--shift", type=float, default=0.0, metavar="F",
                    help=f"move the content left by this fraction of the width (at most {MAX_SHIFT})")
    ap.add_argument("-o", "--output", help="a .png, or a .dds to write the texture")
    args = ap.parse_args()
    if not args.mirror and not args.shift:
        ap.error("give --mirror, --shift F, or both")

    try:
        import PIL  # noqa: F401
    except ImportError:
        print("Pillow is not installed for this interpreter; try system python3.")
        return 1

    name, path = contact_sheet.resolve(args.picture)
    im = contact_sheet.open_picture(path)
    if im is None:
        print(f"No picture file for {args.picture} (looked at {path} and in git's HEAD).")
        return 1
    try:
        out_im = reframe(im.convert("RGB"), args.mirror, args.shift)
    except ValueError as e:
        print(e)
        return 1

    out = Path(args.output) if args.output else MOD_ROOT / "generated_images" / "reframed" / f"{name}.png"
    if out.suffix.lower() == ".dds":
        if not out.parent.is_dir():
            print(f"{out.parent} does not exist (a sparse worktree leaves gfx/ out): "
                  "write the texture from a full checkout.")
            return 1
        import convert_event_image as conv
        texconv = conv.ensure_texconv()
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / f"{name}.png"
            out_im.save(png)
            conv.convert_image(png, out, texconv)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out_im.save(out)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
