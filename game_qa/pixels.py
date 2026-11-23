"""Reading the helper's own screenshots, to tell whether a part of the screen changed.

`decode_png` reads what `win_helper.encode_png` writes (8-bit RGB, no interlace, every row unfiltered) and
nothing else: the harness compares its own shots, it is not an image library. `changed` answers one question,
for `enter-game` (#1598): did the country-select screen's side panel change after the country click, which it
does when a country is selected and does not when a window covers the click. `scaled_up` and `encode_png` make
`profiler-roots`' crop (#1701): a part of a shot, each pixel repeated, so that its small text can be read.
`backdrop_box` and `cut` make `gui-show`'s: the panel drawn over the preview's magenta backdrop.
"""

from __future__ import annotations

import struct
import zlib

from game_qa import win_helper

_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class PixelsError(Exception):
    """A file that is not one of the helper's PNGs, or a region with nothing in it."""


def decode_png(data: bytes) -> tuple[int, int, bytes]:
    """(width, height, RGB bytes) of a PNG written by `win_helper.encode_png`."""
    if not data.startswith(_SIGNATURE):
        raise PixelsError("not a PNG")
    pos, width, height, packed = len(_SIGNATURE), 0, 0, b""
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            if len(body) != 13:
                raise PixelsError("a cut-short image header")
            width, height, depth, colour, _compression, _filter, interlace = struct.unpack(">IIBBBBB", body)
            if (depth, colour, interlace) != (8, 2, 0):
                raise PixelsError("not an 8-bit RGB PNG without interlace")
        elif kind == b"IDAT":
            packed += body
        elif kind == b"IEND":
            break
    if width < 1 or height < 1:
        raise PixelsError("no image header")
    try:
        raw = zlib.decompress(packed)
    except zlib.error as error:
        raise PixelsError(f"the image data cannot be read ({error})") from error
    stride = width * 3
    if len(raw) != (stride + 1) * height:
        raise PixelsError("the image data is not the size its header gives")
    rows = []
    for y in range(height):
        start = y * (stride + 1)
        if raw[start] != 0:
            raise PixelsError("a filtered row: not one of the helper's own PNGs")
        rows.append(raw[start + 1:start + 1 + stride])
    return width, height, b"".join(rows)


def region(image: tuple[int, int, bytes], box: tuple[float, float, float, float]) -> tuple[int, int, bytes]:
    """The part of an image inside `box` (left, top, right, bottom, each a fraction of the image's size)."""
    width, height, rgb = image
    left, top, right, bottom = (int(width * box[0]), int(height * box[1]), int(width * box[2]), int(height * box[3]))
    if right <= left or bottom <= top:
        raise PixelsError("the region is empty in a %dx%d image" % (width, height))
    rows = [rgb[(y * width + left) * 3:(y * width + right) * 3] for y in range(top, bottom)]
    return right - left, bottom - top, b"".join(rows)


def _is_backdrop(rgb: bytes, offset: int, colour: tuple[int, int, int], tolerance: int) -> bool:
    return all(abs(rgb[offset + i] - colour[i]) <= tolerance for i in range(3))


def backdrop_box(image: tuple[int, int, bytes], colour: tuple[int, int, int] = (255, 0, 255), tolerance: int = 40,
                 run: int = 3, gap: int = 0) -> tuple[int, int, int, int]:
    """The pixel box (left, top, right, bottom; right and bottom exclusive) of what is drawn around the image's
    centre on a backdrop of `colour`: from the centre, along its row and its column, each edge is where the first
    run of `run` backdrop pixels begins (a stray one inside the panel ends nothing), or the image's edge. With a
    `gap`, the box then grows to take in whatever is drawn within `gap` pixels outside an edge, again from what it
    took in, until nothing is (live 2026-11-23, a type drawn spilling out of its panel). A pixel is backdrop when
    each channel is within `tolerance` of `colour`. PixelsError when the centre itself is backdrop."""
    width, height, rgb = image
    cx, cy = width // 2, height // 2

    def backdrop(x: int, y: int) -> bool:
        return _is_backdrop(rgb, (y * width + x) * 3, colour, tolerance)

    if backdrop(cx, cy):
        raise PixelsError("nothing drawn at the centre of the %dx%d shot: the panel is not there" % (width, height))

    def reach(start: int, step: int, limit: int, at) -> int:
        """The last drawn position from `start` going by `step`: the one before the first run of `run` backdrop
        pixels (a run cut short by the image's edge counts), or the edge."""
        pos = start
        while 0 <= pos + step < limit:
            ahead = [p for p in (pos + step * k for k in range(1, run + 1)) if 0 <= p < limit]
            if all(at(p) for p in ahead):
                return pos
            pos += step
        return pos

    left = reach(cx, -1, width, lambda x: backdrop(x, cy))
    right = reach(cx, 1, width, lambda x: backdrop(x, cy)) + 1
    top = reach(cy, -1, height, lambda y: backdrop(cx, y))
    bottom = reach(cy, 1, height, lambda y: backdrop(cx, y)) + 1
    if gap <= 0:
        return left, top, right, bottom
    exact = bytes(colour) * width                   # a stretch that is all backdrop, exactly, is passed at C speed

    def drawn_in_row(y: int, x0: int, x1: int) -> bool:
        x0, x1 = max(0, x0), min(width, x1)
        if x1 <= x0 or rgb[(y * width + x0) * 3:(y * width + x1) * 3] == exact[:(x1 - x0) * 3]:
            return False
        return any(not backdrop(x, y) for x in range(x0, x1))

    def drawn_in_column(x: int, y0: int, y1: int) -> bool:
        return any(not backdrop(x, y) for y in range(max(0, y0), min(height, y1)))

    while True:
        before = (left, top, right, bottom)
        for y in range(min(height, bottom + gap) - 1, bottom - 1, -1):       # below: the furthest drawn row
            if drawn_in_row(y, left - gap, right + gap):
                bottom = y + 1
                break
        for y in range(max(0, top - gap), top):                             # above
            if drawn_in_row(y, left - gap, right + gap):
                top = y
                break
        for x in range(min(width, right + gap) - 1, right - 1, -1):          # right
            if drawn_in_column(x, top, bottom):
                right = x + 1
                break
        for x in range(max(0, left - gap), left):                           # left
            if drawn_in_column(x, top, bottom):
                left = x
                break
        if (left, top, right, bottom) == before:
            return left, top, right, bottom


def cut(image: tuple[int, int, bytes], box: tuple[int, int, int, int]) -> tuple[int, int, bytes]:
    """The pixels inside a pixel box (left, top, right, bottom; right and bottom exclusive)."""
    width, height, rgb = image
    left, top, right, bottom = (max(0, box[0]), max(0, box[1]), min(width, box[2]), min(height, box[3]))
    if right <= left or bottom <= top:
        raise PixelsError("the box %s is empty in a %dx%d image" % (list(box), width, height))
    rows = [rgb[(y * width + left) * 3:(y * width + right) * 3] for y in range(top, bottom)]
    return right - left, bottom - top, b"".join(rows)


def changed(before: tuple[int, int, bytes], after: tuple[int, int, bytes], tolerance: int = 24) -> float:
    """The share of pixels that differ by more than `tolerance` in any channel between two images of one size
    (1.0 when the sizes differ: the window itself changed)."""
    if before[:2] != after[:2]:
        return 1.0
    a, b = before[2], after[2]
    if a == b:
        return 0.0
    count = 0
    for i in range(0, len(a), 3):
        if (abs(a[i] - b[i]) > tolerance or abs(a[i + 1] - b[i + 1]) > tolerance
                or abs(a[i + 2] - b[i + 2]) > tolerance):
            count += 1
    return count / (len(a) // 3)


def scaled_up(image: tuple[int, int, bytes], factor: int) -> tuple[int, int, bytes]:
    """`image` with each pixel repeated `factor` times across and down (nearest neighbour: no pixel is made up)."""
    width, height, rgb = image
    if isinstance(factor, bool) or not isinstance(factor, int) or factor < 1:
        raise PixelsError("the factor is a whole number of at least 1, not %r" % (factor,))
    stride = width * 3
    if width < 1 or height < 1 or len(rgb) != stride * height:
        raise PixelsError("%d bytes is not a %dx%d RGB image" % (len(rgb), width, height))
    rows = []
    for y in range(height):
        row = rgb[y * stride:(y + 1) * stride]
        wide = bytearray(stride * factor)
        for copy in range(factor):
            for channel in range(3):
                wide[3 * copy + channel::3 * factor] = row[channel::3]
        rows.append(bytes(wide) * factor)
    return width * factor, height * factor, b"".join(rows)


def encode_png(image: tuple[int, int, bytes]) -> bytes:
    """A PNG of `image`, as the helper writes its shots (`win_helper.encode_png`), so `decode_png` reads it back."""
    width, height, rgb = image
    return win_helper.encode_png(width, height, rgb)
