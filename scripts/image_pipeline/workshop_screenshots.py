#!/usr/bin/env python3
"""
workshop_screenshots.py - Annotate in-game screenshots for the Steam Workshop page.

Each image gets a header (the system's name, large and centered, with a
one-line pitch under it). Where the shot needs pointing at, it also gets gold
frames on the features it shows, a few short captions, or a stat card with a
headline count. Then it is saved as a JPEG under Steam's 2 MB limit. The text
and coordinates of each image live in workshop_screenshot_specs.py (format in
its docstring).

Owner preferences (2026-11-06):
- The header is read first; the callouts come second.
- Callouts are numbered top to bottom by where their target sits, and a
  caption column stacks them in that order. Rendering sorts them; specs don't.
- Overview shots (the tech tree, the laws list, events) lead with a headline
  count, not per-item callouts.
- Never highlight art: the event pictures are AI-generated.
- Counts come from the mod files, not the Workshop description.

And on 2026-11-13, of the first set (two to five callouts on twelve of the
thirteen images): "A few are fine, but sometimes the image speaks for itself
and the annotations are more noise than anything. The header and styling are
good though." So a callout stays only where its caption says something the
shot doesn't (workshop_screenshot_specs.py gives the test), an image may have
none, and a lone caption carries no number.

Usage:
    python3 scripts/image_pipeline/workshop_screenshots.py --src <screenshot dir>
    python3 scripts/image_pipeline/workshop_screenshots.py --src <dir> 04_united_nations --preview
    python3 scripts/image_pipeline/workshop_screenshots.py --list

--src is the folder holding the original screenshots, under the file names the
specs give (Windows' "Screenshot <date> <time>.png"). The screenshots aren't
committed; the 2026-11-06 set is in the owner's Pictures folder. Output goes to
build/workshop_screenshots/ (gitignored). --preview also writes each image at
640 px wide, about the size the Workshop carousel shows: check it there.

The fonts are the game's own EB Garamond (SIL OFL), read from the install
(path_constants.base_game_path), or from --fonts. Needs Pillow (the project
.venv has it).
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

MOD_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from workshop_screenshot_specs import SPECS, validate  # noqa: E402

DEFAULT_OUT = MOD_ROOT / "build" / "workshop_screenshots"
SIZE_LIMIT = 1_900_000  # bytes; Steam takes 2 MB, kept with a margin
MAX_WIDTH = 2560
SS = 2  # the overlay is drawn at twice the size and scaled down, for smooth edges

# Palette taken from the game's own panels.
BAND_TOP = (88, 28, 38)
BAND_BOT = (48, 15, 22)
GOLD = (226, 186, 104)
GOLD_HI = (255, 214, 120)
CREAM = (242, 232, 210)
PANEL = (22, 26, 30, 235)
COLUMN = (27, 31, 35)

# None falls back to Pillow's default font (the tests, which have no game install).
FONT_DIR: Path | None = None


def font(weight: str, size: float):
    if FONT_DIR is None:
        return ImageFont.load_default(size=max(1, int(size)))
    return ImageFont.truetype(str(FONT_DIR / f"EBGaramond-{weight}.ttf"), max(1, int(size)))


def wrap(draw, text, fnt, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def anchor_on_box(box, side):
    x0, y0, x1, y1 = box
    return {
        "l": (x0, (y0 + y1) / 2), "r": (x1, (y0 + y1) / 2),
        "t": ((x0 + x1) / 2, y0), "b": ((x0 + x1) / 2, y1),
        "tl": (x0, y0), "tr": (x1, y0), "bl": (x0, y1), "br": (x1, y1),
    }[side]


def reading_order(callouts):
    """Callouts sorted top to bottom (then left to right) by their target."""
    def key(co):
        t = co.get("box") or co.get("pt")
        return (t[1], t[0])
    return sorted(callouts, key=key)


class Canvas:
    """The screenshot on a canvas with the header above it and an optional caption column."""

    def __init__(self, spec, shot: Image.Image):
        self.spec = spec
        im = shot.convert("RGB")
        if "crop" in spec:
            im = im.crop(spec["crop"])
        self.k = spec.get("scale", 1.0)  # spec coordinates are source pixels
        if self.k != 1.0:
            im = im.resize((round(im.width * self.k), round(im.height * self.k)), Image.LANCZOS)
        self.u = spec.get("u", 1.0)  # text scale
        self.measure = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        self.head = self.header_layout()
        self.band_h = round(self.head["h"])
        self.col_w = round(spec.get("column", 0))
        self.margin = round(spec.get("margin", 0))  # blank canvas at each side of a narrow shot
        self.W, self.H = im.width + 2 * self.margin + self.col_w, im.height + self.band_h
        self.ox, self.oy = self.margin, self.band_h
        self.base = Image.new("RGB", (self.W, self.H), COLUMN)
        self.base.paste(im, (self.ox, self.oy))
        self.ov = Image.new("RGBA", (self.W * SS, self.H * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.ov)

    def c(self, x, y):
        """Source-screenshot pixels to canvas pixels."""
        return (self.ox + x * self.k, self.oy + y * self.k)

    @staticmethod
    def s(v):
        return v * SS

    def header_layout(self):
        """Spacing from the fonts' cap heights and descenders, so the rule never cuts a 'g'."""
        u, m = self.u, self.measure
        tf, sf = font("SemiBold", 100 * u), font("Italic", 50 * u)
        t_cap = -m.textbbox((0, 0), "H", font=tf, anchor="ls")[1]
        t_desc = m.textbbox((0, 0), "gpy", font=tf, anchor="ls")[3]
        s_cap = -m.textbbox((0, 0), "H", font=sf, anchor="ls")[1]
        s_desc = m.textbbox((0, 0), "gpy", font=sf, anchor="ls")[3]
        tb = 34 * u + t_cap            # title baseline
        oy = tb + t_desc + 14 * u      # the ornament, clear of descenders
        sb = oy + 18 * u + s_cap       # subtitle baseline
        h = sb + s_desc + 22 * u + 8   # and the bottom rules
        if not self.spec.get("subtitle"):
            h = tb + t_desc + 30 * u + 8
        return dict(tf=tf, sf=sf, tb=tb, oy=oy, sb=sb, h=h)

    def band(self):
        """The header: the system's name large and centered, its one-line pitch under it."""
        d = ImageDraw.Draw(self.base)
        bh, W, u = self.band_h, self.W, self.u
        for y in range(bh):
            t = y / max(1, bh - 1)
            d.line([(0, y), (W, y)], fill=tuple(round(BAND_TOP[i] * (1 - t) + BAND_BOT[i] * t) for i in range(3)))
        d.line([(0, round(9 * u)), (W, round(9 * u))], fill=(150, 110, 70), width=1)
        d.line([(0, bh - 6), (W, bh - 6)], fill=GOLD, width=3)
        d.line([(0, bh - 2), (W, bh - 2)], fill=(20, 8, 10), width=3)
        title, sub = self.spec["title"], self.spec.get("subtitle", "")
        hd = self.head
        tf, sf, tb, oy, sb = hd["tf"], hd["sf"], hd["tb"], hd["oy"], hd["sb"]
        cx = W / 2
        tw = d.textlength(title, font=tf)
        sw = d.textlength(sub, font=sf) if sub else 0
        shadow = Image.new("L", (W, bh), 0)
        sd = ImageDraw.Draw(shadow)
        sd.text((cx + 3 * u, tb + 5 * u), title, font=tf, fill=200, anchor="ms")
        if sub:
            sd.text((cx + 2 * u, sb + 3 * u), sub, font=sf, fill=150, anchor="ms")
        shadow = shadow.filter(ImageFilter.GaussianBlur(6 * u))
        band = self.base.crop((0, 0, W, bh))
        band.paste((10, 3, 5), (0, 0), shadow)
        self.base.paste(band, (0, 0))
        d = ImageDraw.Draw(self.base)
        d.text((cx, tb), title, font=tf, fill=(250, 238, 212), anchor="ms")
        if sub:
            half, r = min(max(tw, sw) * 0.5, 340 * u), 7 * u
            lw = max(1, round(2 * u))
            d.line([(cx - half, oy), (cx - r - 10 * u, oy)], fill=GOLD, width=lw)
            d.line([(cx + r + 10 * u, oy), (cx + half, oy)], fill=GOLD, width=lw)
            d.polygon([(cx, oy - r), (cx + r, oy), (cx, oy + r), (cx - r, oy)], fill=GOLD)
            d.text((cx, sb), sub, font=sf, fill=(238, 206, 146), anchor="ms")
        brand = self.spec.get("brand", "Timeline Extended")
        if brand:
            bf = font("Medium", 28 * u)
            if cx + max(tw, sw) / 2 + 40 * u < W - 30 * u - d.textlength(brand, font=bf):
                d.text((W - 30 * u, sb), brand, font=bf, fill=(196, 156, 108), anchor="rs")

    def frame(self, box, pad=6):
        x0, y0 = self.c(box[0], box[1])
        x1, y1 = self.c(box[2], box[3])
        xy = [self.s(x0 - pad), self.s(y0 - pad), self.s(x1 + pad), self.s(y1 + pad)]
        self.d.rounded_rectangle(xy, radius=self.s(10), outline=(0, 0, 0, 170), width=self.s(9))
        self.d.rounded_rectangle(xy, radius=self.s(10), outline=GOLD_HI + (255,), width=self.s(4))

    def badge(self, x, y, n):
        u, s = self.u, self.s
        r = 25 * u
        x = min(max(x, r + 5), self.W - r - 5)  # keep the whole badge on the canvas
        y = min(max(y, self.oy + r + 5), self.H - r - 5)
        self.d.ellipse([s(x - r - 3), s(y - r - 3), s(x + r + 3), s(y + r + 3)], fill=(0, 0, 0, 200))
        self.d.ellipse([s(x - r), s(y - r), s(x + r), s(y + r)], fill=(120, 30, 40, 255),
                       outline=GOLD_HI + (255,), width=round(s(3)))
        self.d.text((s(x), s(y + 1 * u)), str(n), font=font("Bold", s(34 * u)), fill=CREAM, anchor="mm")

    def caption_size(self, title, body, width, numbered=True):
        """Wrapped title and body lines and the box height; a number takes 14 u of the width."""
        u = self.u
        pad = 20 * u
        if numbered:
            width -= 14 * u
        tl = wrap(self.measure, title, font("Bold", 44 * u), width - 2 * pad)
        bl = wrap(self.measure, body, font("Medium", 36 * u), width - 2 * pad) if body else []
        h = pad * 2 + len(tl) * 50 * u + (8 * u if bl else 0) + len(bl) * 42 * u
        return tl, bl, h

    def caption(self, x, y, width, title, body, n=None):
        """A caption box, with its number on the left edge when it has one."""
        u, s = self.u, self.s
        shift = 14 * u if n is not None else 0
        tl, bl, h = self.caption_size(title, body, width, numbered=n is not None)
        pad = 20 * u
        self.d.rounded_rectangle([s(x + 4), s(y + 5), s(x + width + 4), s(y + h + 5)], radius=s(12), fill=(0, 0, 0, 110))
        self.d.rounded_rectangle([s(x), s(y), s(x + width), s(y + h)], radius=s(12), fill=PANEL,
                                 outline=GOLD + (255,), width=s(3))
        if n is not None:
            self.badge(x, y + pad + 25 * u, n)
        tx, ty = x + pad + shift, y + pad
        for line in tl:
            self.d.text((s(tx), s(ty)), line, font=font("Bold", s(44 * u)), fill=GOLD_HI + (255,))
            ty += 50 * u
        if bl:
            ty += 8 * u
        for line in bl:
            self.d.text((s(tx), s(ty)), line, font=font("Medium", s(36 * u)), fill=CREAM + (255,))
            ty += 42 * u

    def stat(self, at, w, big, lines=(), big_size=76, line_size=38):
        """A headline card: one big line and a few smaller ones, centered."""
        u, s = self.u, self.s
        x, y = self.c(*at)
        w = w * u
        bf, lf = font("SemiBold", big_size * u), font("Medium", line_size * u)
        pad = 26 * u
        bl = wrap(self.measure, big, bf, w - 2 * pad)
        ll = [wrap(self.measure, t, lf, w - 2 * pad) for t in lines]
        h = (2 * pad + len(bl) * big_size * 1.08 * u + (14 * u if lines else 0)
             + sum(len(g) for g in ll) * line_size * 1.2 * u + max(0, len(ll) - 1) * 8 * u)
        self.d.rounded_rectangle([s(x + 5), s(y + 6), s(x + w + 5), s(y + h + 6)], radius=s(14), fill=(0, 0, 0, 120))
        self.d.rounded_rectangle([s(x), s(y), s(x + w), s(y + h)], radius=s(14), fill=PANEL,
                                 outline=GOLD + (255,), width=s(3))
        self.d.rounded_rectangle([s(x + 8 * u), s(y + 8 * u), s(x + w - 8 * u), s(y + h - 8 * u)],
                                 radius=s(9), outline=GOLD + (110,), width=s(1))
        ty = y + pad
        for line in bl:
            self.d.text((s(x + w / 2), s(ty)), line, font=font("SemiBold", s(big_size * u)),
                        fill=GOLD_HI + (255,), anchor="ma")
            ty += big_size * 1.08 * u
        ty += 14 * u
        for group in ll:
            for line in group:
                self.d.text((s(x + w / 2), s(ty)), line, font=font("Medium", s(line_size * u)),
                            fill=CREAM + (255,), anchor="ma")
                ty += line_size * 1.2 * u
            ty += 8 * u

    def arrow(self, p0, p1):
        u, s = self.u, self.s
        (x0, y0), (x1, y1) = p0, p1
        ang = math.atan2(y1 - y0, x1 - x0)
        hl, hw = 30 * u, 17 * u
        bx, by = x1 - hl * math.cos(ang), y1 - hl * math.sin(ang)
        self.d.line([s(x0), s(y0), s(bx), s(by)], fill=(0, 0, 0, 190), width=round(s(11 * u)))
        self.d.line([s(x0), s(y0), s(bx), s(by)], fill=GOLD_HI + (255,), width=round(s(5 * u)))
        px, py = -math.sin(ang), math.cos(ang)
        pts = [(x1, y1), (bx + px * hw, by + py * hw), (bx - px * hw, by - py * hw)]
        cx, cy = sum(p[0] for p in pts) / 3, sum(p[1] for p in pts) / 3
        outline = [(x + (x - cx) * 0.25, y + (y - cy) * 0.25) for x, y in pts]
        self.d.polygon([(s(a), s(b)) for a, b in outline], fill=(0, 0, 0, 200))
        self.d.polygon([(s(a), s(b)) for a, b in pts], fill=GOLD_HI + (255,))

    def finish(self):
        ov = self.ov.resize((self.W, self.H), Image.LANCZOS)
        out = self.base.convert("RGBA")
        out.alpha_composite(ov)
        return out.convert("RGB")


def stack_column(cv, spec, col):
    """Place column captions near their targets' height, in order, without overlaps."""
    u = cv.u
    gap = spec.get("gap", 26) * u
    top, bottom = cv.oy + 24 * u, cv.H - 24 * u
    if "column_region" in spec:
        top = cv.c(0, spec["column_region"][1])[1]
        bottom = cv.c(0, spec["column_region"][3])[1]
    for it in col:
        co = it["co"]
        if "y" in co:
            it["pos"][1] = cv.c(0, co["y"])[1]
        else:
            it["pos"][1] = (it["tgt"][1] + it["tgt"][3]) / 2 - it["h"] / 2
    y = top
    for it in col:  # forward: no overlap
        it["pos"][1] = max(it["pos"][1], y)
        y = it["pos"][1] + it["h"] + gap
    y = bottom
    for it in reversed(col):  # backward: stay inside the column
        it["pos"][1] = min(it["pos"][1], y - it["h"])
        y = it["pos"][1] - gap
    if col[0]["pos"][1] < top:  # too tall for the column: spread evenly
        g = (bottom - top - sum(it["h"] for it in col)) / max(1, len(col) - 1)
        y = top
        for it in col:
            it["pos"][1] = y
            y += it["h"] + g


def render(spec, shot: Image.Image) -> Image.Image:
    cv = Canvas(spec, shot)
    cv.band()
    u = cv.u
    callouts = reading_order(spec.get("callouts", []))
    # A callout without a title is a bare frame. Captions are numbered only when
    # there are two or more of them: a lone "1" points at nothing else.
    numbered = sum(1 for co in callouts if co.get("title")) > 1
    items, n = [], 0
    for co in callouts:
        if not co.get("title"):
            items.append(dict(co=co, n=None, bare=True))
            continue
        n += 1
        if "box" in co:
            x0, y0 = cv.c(co["box"][0], co["box"][1])
            x1, y1 = cv.c(co["box"][2], co["box"][3])
            p = co.get("pad", 6)
            tgt = (x0 - p, y0 - p, x1 + p, y1 + p)
        else:
            x, y = cv.c(*co["pt"])
            tgt = (x, y, x, y)
        if "at" in co:  # a caption placed on the screenshot itself, in source pixels
            width = co.get("w", 520) * u
            pos = list(cv.c(*co["at"]))
        elif "column_region" in spec:  # a column laid over an empty part of the screenshot
            rx0, _ = cv.c(*spec["column_region"][:2])
            rx1, _ = cv.c(*spec["column_region"][2:])
            width = rx1 - rx0 - 14 * u
            pos = [rx0 + 14 * u, None]
        else:  # the column added to the right of the screenshot
            width = cv.col_w - 2 * round(28 * u) - 14 * u
            pos = [cv.W - cv.col_w + 42 * u, None]
        h = cv.caption_size(co["title"], co.get("body", ""), width, numbered)[2]
        items.append(dict(co=co, n=n if numbered else None, bare=False,
                          tgt=tgt, width=width, pos=pos, h=h))

    captioned = [it for it in items if not it["bare"]]
    col = [it for it in captioned if it["pos"][1] is None]
    if col:
        stack_column(cv, spec, col)

    for it in items:
        if "box" in it["co"]:
            cv.frame(it["co"]["box"], pad=it["co"].get("pad", 6))
    for it in captioned:
        co, tgt = it["co"], it["tgt"]
        if co.get("arrow", "at" in co):
            x, y = it["pos"]
            cb = (x, y, x + it["width"], y + it["h"])
            fs = co.get("from", "r" if "at" in co else "l")
            ts = co.get("to", "r" if fs == "l" else "l")
            p1 = anchor_on_box(tgt, ts) if "box" in co else (tgt[0], tgt[1])
            cv.arrow(anchor_on_box(cb, fs), p1)
    for it in captioned:
        cv.caption(*it["pos"], it["width"], it["co"]["title"], it["co"].get("body", ""), it["n"])
    for it in captioned:
        if "box" in it["co"] and it["co"].get("badge", True) and it["n"] is not None:
            cv.badge(*anchor_on_box(it["tgt"], it["co"].get("badge_at", "tl")), it["n"])
    for st in spec.get("stats", []):
        cv.stat(**st)
    return cv.finish()


def export(img: Image.Image, path: Path, limit: int = SIZE_LIMIT):
    """Save as a JPEG under the limit, stepping the quality down if it must."""
    if img.width > MAX_WIDTH:
        img = img.resize((MAX_WIDTH, round(img.height * MAX_WIDTH / img.width)), Image.LANCZOS)
    for q in (92, 90, 88, 86, 84, 82, 80):
        img.save(path, "JPEG", quality=q, subsampling=0, optimize=True, progressive=True)
        if path.stat().st_size < limit:
            return q, path.stat().st_size
    raise RuntimeError(f"{path} is still over {limit} bytes at quality 80")


def game_font_dir() -> Path:
    from path_constants import base_game_path  # lazy: --list and the tests need no game
    return Path(base_game_path) / "game" / "fonts" / "EBGaramond"


def main(argv=None) -> int:
    global FONT_DIR
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help="specs to render (default: all)")
    ap.add_argument("--src", type=Path, help="folder holding the original screenshots")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output folder (default: {DEFAULT_OUT.relative_to(MOD_ROOT)})")
    ap.add_argument("--fonts", type=Path, help="folder with EBGaramond-*.ttf (default: the game install's)")
    ap.add_argument("--preview", action="store_true", help="also write <name>_640.jpg, the carousel's size")
    ap.add_argument("--list", action="store_true", help="list the specs and the screenshot each needs")
    args = ap.parse_args(argv)

    if args.list:
        for name, spec in SPECS.items():
            print(f"{name}: {spec['src']}")
        return 0
    unknown = [n for n in args.names if n not in SPECS]
    if unknown:
        ap.error("no such spec: " + ", ".join(unknown) + " (see --list)")
    if args.src is None:
        ap.error("--src is required: the folder holding the original screenshots")
    problems = [f"{n}: {p}" for n, spec in SPECS.items() for p in validate(spec)]
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    sys.path.insert(0, str(MOD_ROOT))
    FONT_DIR = args.fonts or game_font_dir()
    if not (FONT_DIR / "EBGaramond-SemiBold.ttf").is_file():
        print(f"EB Garamond not found in {FONT_DIR}; pass --fonts", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    for name in args.names or list(SPECS):
        spec = SPECS[name]
        src = args.src / spec["src"]
        if not src.is_file():
            print(f"{name}: missing screenshot {src}", file=sys.stderr)
            return 1
        img = render(spec, Image.open(src))
        out = args.out / f"{name}.jpg"
        q, size = export(img, out)
        if args.preview:
            img.resize((640, round(img.height * 640 / img.width)), Image.LANCZOS).save(
                args.out / f"{name}_640.jpg", quality=90)
        print(f"{name}: {img.width}x{img.height}, quality {q}, {size / 1e6:.2f} MB -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
