"""icon_dds.py - write UI icons as uncompressed DDS, the way vanilla ships them.

Vanilla's icon folders (invention_icons, decree, ideology_icons, ...) hold
uncompressed 32-bit BGRA with a full mip chain and a legacy 124-byte header,
no DX10 extension. This writes the same layout from a Pillow RGBA image, with
no texconv and no GPU, so it runs anywhere the tests do.

Mips are resized from the full image with premultiplied alpha, so a
transparent background never bleeds a dark or white fringe into the edges.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
from PIL import Image

# Header flags, as in a vanilla invention icon (checked against
# invention_icons/mass_communication.dds; only its NVTT signature in the
# reserved words differs).
DDSD_CAPS, DDSD_HEIGHT, DDSD_WIDTH, DDSD_PITCH = 0x1, 0x2, 0x4, 0x8
DDSD_PIXELFORMAT, DDSD_MIPMAPCOUNT = 0x1000, 0x20000
DDPF_ALPHAPIXELS, DDPF_RGB = 0x1, 0x40
DDSCAPS_COMPLEX, DDSCAPS_TEXTURE, DDSCAPS_MIPMAP = 0x8, 0x1000, 0x400000
MASKS = (0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)  # R, G, B, A in BGRA order


def resize_premultiplied(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    """LANCZOS resize without the dark/white fringe straight-alpha resizing leaves."""
    a = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255
    pm = a.copy()
    pm[..., :3] *= pm[..., 3:4]
    chans = [Image.fromarray((pm[..., i] * 255).astype(np.uint8)).resize(size, Image.LANCZOS)
             for i in range(4)]
    r = np.stack([np.asarray(c, dtype=np.float32) / 255 for c in chans], -1)
    al = r[..., 3:4]
    r[..., :3] = np.where(al > 1e-3, r[..., :3] / np.maximum(al, 1e-3), 0)
    return Image.fromarray((np.clip(r, 0, 1) * 255).astype(np.uint8), "RGBA")


def mip_sizes(width: int, height: int) -> list[tuple[int, int]]:
    """Every level down to 1x1, halving (and flooring) each side."""
    sizes = [(width, height)]
    while sizes[-1] != (1, 1):
        w, h = sizes[-1]
        sizes.append((max(1, w // 2), max(1, h // 2)))
    return sizes


def header(width: int, height: int, mips: int) -> bytes:
    flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PITCH | DDSD_PIXELFORMAT | DDSD_MIPMAPCOUNT
    pixel_format = struct.pack("<2I4s5I", 32, DDPF_RGB | DDPF_ALPHAPIXELS, b"\0\0\0\0", 32, *MASKS)
    caps = struct.pack("<4I", DDSCAPS_COMPLEX | DDSCAPS_TEXTURE | DDSCAPS_MIPMAP, 0, 0, 0)
    body = (struct.pack("<7I", 124, flags, height, width, width * 4, 0, mips)
            + b"\0" * 44 + pixel_format + caps + b"\0" * 4)
    assert len(body) == 124
    return b"DDS " + body


def write_dds(im: Image.Image, path: Path) -> None:
    """Write `im` as uncompressed BGRA8 with a full mip chain."""
    im = im.convert("RGBA")
    sizes = mip_sizes(*im.size)
    data = [header(im.width, im.height, len(sizes))]
    for size in sizes:
        level = im if size == im.size else resize_premultiplied(im, size)
        data.append(np.asarray(level)[..., [2, 1, 0, 3]].tobytes())  # RGBA -> BGRA
    Path(path).write_bytes(b"".join(data))
