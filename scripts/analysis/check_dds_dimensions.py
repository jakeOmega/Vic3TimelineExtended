"""CI check: block-compressed DDS textures must have multiple-of-4 dimensions.

BC/DXT compression works on 4x4 texel blocks. A DXT1/3/5 or BC4-BC7 texture whose
width or height is not a multiple of 4 has a partial trailing block; DirectX and
the Clausewitz texture loader disagree about how to pad it, which shows up in-game
as a smeared or truncated edge on the icon. Uncompressed (RGBA) DDS files are
unaffected and are not checked.

The scan reads only the 128-byte DDS header (plus the 20-byte DX10 extension when
`fourCC == 'DX10'`), so it is cheap even over the whole 1000-file texture tree and
needs no image library.

Usage:
    python3 scripts/analysis/check_dds_dimensions.py [root_or_file ...]
    python3 scripts/analysis/check_dds_dimensions.py --list       # print every BC texture
    python3 scripts/analysis/check_dds_dimensions.py --repo-root=DIR --allowlist=FILE

With no positional argument it scans `gfx/` under the repo root. Known offenders
listed in `scripts/analysis/dds_dimension_allowlist.txt` are reported but do not
fail the run; that file is expected to empty out as #246 lands. Exits 1 when an
unlisted violation is found.
"""

from __future__ import annotations

import os
import struct
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALLOWLIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "dds_dimension_allowlist.txt")

DDS_MAGIC = b"DDS "
HEADER_SIZE = 128  # magic (4) + DDS_HEADER (124)

# fourCC values that mean "BC-compressed, 4x4 blocks".
BLOCK_COMPRESSED_FOURCC = {
    b"DXT1", b"DXT2", b"DXT3", b"DXT4", b"DXT5",
    b"ATI1", b"ATI2", b"BC4U", b"BC4S", b"BC5U", b"BC5S",
}

# DXGI_FORMAT values for BC1-BC7 (from dxgiformat.h), used when fourCC == 'DX10'.
BLOCK_COMPRESSED_DXGI = (
    set(range(70, 85))    # BC1_TYPELESS(70) .. BC5_SNORM(84)
    | set(range(94, 100))  # BC6H_TYPELESS(94) .. BC7_UNORM_SRGB(99)
)

DXGI_NAMES = {
    70: "BC1", 71: "BC1", 72: "BC1",
    73: "BC2", 74: "BC2", 75: "BC2",
    76: "BC3", 77: "BC3", 78: "BC3",
    79: "BC4", 80: "BC4", 81: "BC4",
    82: "BC5", 83: "BC5", 84: "BC5",
    94: "BC6H", 95: "BC6H", 96: "BC6H",
    97: "BC7", 98: "BC7", 99: "BC7",
}


class DdsHeaderError(ValueError):
    """The file is not a DDS we can read a header from."""


def parse_dds_header(data: bytes) -> dict:
    """Return {'width', 'height', 'format', 'block_compressed'} for DDS bytes.

    Raises DdsHeaderError when the magic or header size is wrong.
    """
    if len(data) < HEADER_SIZE:
        raise DdsHeaderError(f"file is {len(data)} bytes, shorter than a DDS header")
    if data[:4] != DDS_MAGIC:
        raise DdsHeaderError("missing 'DDS ' magic")

    header_size = struct.unpack_from("<I", data, 4)[0]
    if header_size != 124:
        raise DdsHeaderError(f"DDS_HEADER dwSize is {header_size}, expected 124")

    height = struct.unpack_from("<I", data, 12)[0]
    width = struct.unpack_from("<I", data, 16)[0]
    fourcc = data[84:88]

    if fourcc == b"DX10":
        if len(data) < HEADER_SIZE + 20:
            raise DdsHeaderError("DX10 header announced but truncated")
        dxgi = struct.unpack_from("<I", data, HEADER_SIZE)[0]
        name = DXGI_NAMES.get(dxgi, f"DXGI_{dxgi}")
        return {
            "width": width,
            "height": height,
            "format": f"DX10/{name}",
            "block_compressed": dxgi in BLOCK_COMPRESSED_DXGI,
        }

    if fourcc in BLOCK_COMPRESSED_FOURCC:
        return {
            "width": width,
            "height": height,
            "format": fourcc.decode("ascii"),
            "block_compressed": True,
        }

    printable = fourcc.decode("ascii", "replace").strip("\x00") or "uncompressed"
    return {
        "width": width,
        "height": height,
        "format": printable,
        "block_compressed": False,
    }


def read_header(path: str) -> dict:
    with open(path, "rb") as fh:
        data = fh.read(HEADER_SIZE + 20)
    return parse_dds_header(data)


def iter_dds_files(roots: list[str]) -> list[str]:
    found: list[str] = []
    for root in roots:
        if os.path.isdir(root):
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in sorted(filenames):
                    if name.lower().endswith(".dds"):
                        found.append(os.path.join(dirpath, name))
        elif root.lower().endswith(".dds"):
            found.append(root)
    return sorted(set(found))


def load_allowlist(path: str = ALLOWLIST_PATH) -> set[str]:
    """Repo-relative paths of known offenders, one per line; `#` comments allowed."""
    if not os.path.exists(path):
        return set()
    entries = set()
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if line:
                entries.add(line.replace("\\", "/"))
    return entries


def scan(roots: list[str], repo_root: str = REPO_ROOT,
         allowlist: set[str] | None = None) -> dict:
    """Scan `roots`, returning violations / allowed / unreadable / counts."""
    violations: list[dict] = []
    allowed: list[dict] = []
    unreadable: list[tuple[str, str]] = []
    if allowlist is None:
        allowlist = load_allowlist()
    compressed = 0

    for path in iter_dds_files(roots):
        rel = os.path.relpath(path, repo_root).replace("\\", "/")
        try:
            info = read_header(path)
        except (DdsHeaderError, OSError) as exc:
            unreadable.append((rel, str(exc)))
            continue
        if not info["block_compressed"]:
            continue
        compressed += 1
        if info["width"] % 4 == 0 and info["height"] % 4 == 0:
            continue
        record = {"path": rel, **info}
        (allowed if rel in allowlist else violations).append(record)

    return {
        "violations": violations,
        "allowed": allowed,
        "unreadable": unreadable,
        "block_compressed_scanned": compressed,
        "stale_allowlist": sorted(
            allowlist - {r["path"] for r in allowed} - {r["path"] for r in violations}
        ),
    }


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    list_all = "--list" in args
    if list_all:
        args.remove("--list")
    repo_root = REPO_ROOT
    allowlist_path = ALLOWLIST_PATH
    for arg in list(args):
        if arg.startswith("--repo-root="):
            # Only affects how paths are displayed / matched against the allowlist;
            # useful when scanning a gfx/ tree that lives outside this checkout.
            repo_root = arg.split("=", 1)[1]
            args.remove(arg)
        elif arg.startswith("--allowlist="):
            allowlist_path = arg.split("=", 1)[1]
            args.remove(arg)
    roots = args or [os.path.join(repo_root, "gfx")]

    if list_all:
        for path in iter_dds_files(roots):
            try:
                info = read_header(path)
            except (DdsHeaderError, OSError) as exc:
                print(f"{path}: unreadable ({exc})")
                continue
            if info["block_compressed"]:
                print(f"{info['format']:>10} {info['width']}x{info['height']} {path}")
        return 0

    result = scan(roots, repo_root=repo_root,
                  allowlist=load_allowlist(allowlist_path))

    for rel, reason in result["unreadable"]:
        print(f"{rel}: unreadable DDS header ({reason})", file=sys.stderr)

    for record in result["allowed"]:
        print(f"{record['path']}: {record['format']} {record['width']}x"
              f"{record['height']} — known offender, allowlisted (see #246)")

    for record in result["violations"]:
        print(f"{record['path']}:1: {record['format']} texture is "
              f"{record['width']}x{record['height']} — block-compressed textures "
              f"need both dimensions to be a multiple of 4", file=sys.stderr)

    for rel in result["stale_allowlist"]:
        print(f"{rel}: listed in dds_dimension_allowlist.txt but no longer violates "
              f"(or no longer exists) — drop the line", file=sys.stderr)

    print(f"Scanned {result['block_compressed_scanned']} block-compressed DDS "
          f"texture(s); {len(result['violations'])} violation(s), "
          f"{len(result['allowed'])} allowlisted.")

    failed = bool(result["violations"] or result["unreadable"] or result["stale_allowlist"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
