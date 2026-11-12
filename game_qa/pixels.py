"""Reading the helper's own screenshots, to tell whether a part of the screen changed.

`decode_png` reads what `win_helper.encode_png` writes (8-bit RGB, no interlace, every row unfiltered) and
nothing else: the harness compares its own shots, it is not an image library. `changed` answers one question,
for `enter-game` (#1598): did the country-select screen's side panel change after the country click, which it
does when a country is selected and does not when a window covers the click.
"""

from __future__ import annotations

import struct
import zlib

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
