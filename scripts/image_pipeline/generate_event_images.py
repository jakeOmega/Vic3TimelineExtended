#!/usr/bin/env python3
"""
generate_event_images.py - Three-phase pipeline for event image generation.

Phase 1 (generate): Call gen_image.py for each image -> generated_images/*.png
Phase 2 (convert):  Call convert_event_image.py     -> gfx/event_pictures/*.dds
Phase 3 (update):   Update event files with new texture references

Each phase skips already-completed work, making the script safe to re-run.
If it fails partway through, re-run with --phase to resume from that phase.

An image whose .dds already exists is never regenerated (phase 1) or
reconverted (phase 2); to redo one, delete its .dds first. Phase 3 only wires
images whose .dds exists, so a registry entry can name its events before the
picture is generated (a "pending" image), and those events keep their current
art until the file lands. Phase 3 also leaves alone events that already show
the right texture and events with conditional art (several event_image blocks,
or one with a trigger), which a single texture line would flatten.

Usage:
    python generate_event_images.py                    # All three phases
    python generate_event_images.py --phase generate   # Phase 1 only
    python generate_event_images.py --phase convert    # Phase 2 only
    python generate_event_images.py --phase update     # Phase 3 only
    python generate_event_images.py --dry-run          # Preview what would be done
    python generate_event_images.py --only KEY1 KEY2   # Process specific images only
    python generate_event_images.py --list              # List all image keys

Note: Phase 1 calls gen_image.py as a subprocess for each image. The FLUX model
(~34GB) is loaded each time, so each image takes minutes. Use --only to
generate the pending images in batches; `python event_image_prompts.py
--validate` lists them.

Review every new picture before wiring it: run `--phase generate` and
`--phase convert`, look at the results (`contact_sheet.py KEY1 KEY2 ...`
renders a labelled grid), delete and regenerate any bad ones, then run
`--phase update`. FLUX drifts toward real flags, landmarks and politicians'
faces even when the prompt names none.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from event_image_inventory import pictures_on_disk

SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = Path(__file__).resolve().parents[2]
GEN_DIR = MOD_ROOT / "generated_images"
GFX_DIR = MOD_ROOT / "gfx" / "event_pictures"
EVENTS_DIR = MOD_ROOT / "events"

# Generation dimensions: ~1.42:1 aspect ratio close to 1700:1200 target.
# Both must be multiples of 16 for FLUX.
GEN_WIDTH = 1024
GEN_HEIGHT = 720


def load_images() -> dict:
    """Import the IMAGES dict from event_image_prompts.py."""
    from event_image_prompts import IMAGES
    return IMAGES


# =========================================================================
# Phase 1: Generate PNGs
# =========================================================================

def phase_generate(images: dict, dry_run: bool = False) -> None:
    """Generate PNG images by calling gen_image.py for each entry."""
    print(f"\n{'=' * 60}")
    print("PHASE 1: Generate PNGs")
    print(f"{'=' * 60}")

    GEN_DIR.mkdir(exist_ok=True)
    gen_script = SCRIPT_DIR / "gen_image.py"

    total = len(images)
    skipped = 0
    generated = 0
    failed = 0

    for i, (name, img) in enumerate(images.items(), 1):
        out = GEN_DIR / f"{name}.png"

        if out.exists():
            print(f"  [{i}/{total}] SKIP (exists): {name}.png")
            skipped += 1
            continue
        if (GFX_DIR / f"{name}.dds").exists():
            print(f"  [{i}/{total}] SKIP (dds exists): {name}.dds")
            skipped += 1
            continue

        prompt = img["prompt"]
        style = img.get("style", "realistic")

        if dry_run:
            print(f"  [{i}/{total}] WOULD GENERATE: {name}.png")
            print(f"           prompt: {prompt[:80]}...")
            continue

        print(f"  [{i}/{total}] GENERATING: {name}.png")
        cmd = [
            sys.executable, str(gen_script),
            "-d", prompt,
            "-s", style,
            "-o", str(out),
            "--width", str(GEN_WIDTH),
            "--height", str(GEN_HEIGHT),
        ]

        try:
            subprocess.run(cmd, check=True)
            generated += 1
            print(f"           OK: {out.name}")
        except subprocess.CalledProcessError as e:
            failed += 1
            print(f"           FAILED (exit {e.returncode}): {name}")
        except KeyboardInterrupt:
            print(f"\n  Interrupted after {generated} generated, {skipped} skipped.")
            print("  Re-run to continue from where you left off.")
            sys.exit(1)

    print(f"\n  Summary: {generated} generated, {skipped} skipped, {failed} failed")


# =========================================================================
# Phase 2: Convert PNGs to DDS
# =========================================================================

def phase_convert(images: dict, dry_run: bool = False) -> None:
    """Convert generated PNGs to DDS using convert_event_image.py."""
    print(f"\n{'=' * 60}")
    print("PHASE 2: Convert PNGs to DDS")
    print(f"{'=' * 60}")

    GFX_DIR.mkdir(parents=True, exist_ok=True)
    convert_script = SCRIPT_DIR / "convert_event_image.py"

    total = len(images)
    skipped = 0
    converted = 0
    failed = 0
    missing = 0

    for i, name in enumerate(images, 1):
        png = GEN_DIR / f"{name}.png"
        dds = GFX_DIR / f"{name}.dds"

        if dds.exists():
            print(f"  [{i}/{total}] SKIP (exists): {name}.dds")
            skipped += 1
            continue

        if not png.exists():
            print(f"  [{i}/{total}] SKIP (no PNG): {name}.png")
            missing += 1
            continue

        if dry_run:
            print(f"  [{i}/{total}] WOULD CONVERT: {name}.png -> {name}.dds")
            continue

        print(f"  [{i}/{total}] CONVERTING: {name}.png -> {name}.dds")
        cmd = [
            sys.executable, str(convert_script),
            str(png),
            "-o", str(dds),
            "-v",
        ]

        try:
            subprocess.run(cmd, check=True)
            converted += 1
        except subprocess.CalledProcessError as e:
            failed += 1
            print(f"           FAILED (exit {e.returncode}): {name}")
        except KeyboardInterrupt:
            print(f"\n  Interrupted after {converted} converted.")
            print("  Re-run with --phase convert to continue.")
            sys.exit(1)

    print(f"\n  Summary: {converted} converted, {skipped} skipped, "
          f"{missing} missing PNG, {failed} failed")


# =========================================================================
# Phase 3: Update event files
# =========================================================================

_EVENT_DEF_RE = re.compile(r'^(\w+\.\d+)\s*=\s*\{')
_IMAGE_OPEN_RE = re.compile(r'event_image\s*=\s*\{')
_TEXTURE_RE = re.compile(r'\btexture\s*=\s*"([^"]+)"')
_TRIGGER_RE = re.compile(r'\btrigger\s*=')


def _build_event_to_texture(images: dict,
                            on_disk: set[str]) -> tuple[dict[str, str], list[str]]:
    """Map event_id -> texture path for the images whose .dds exists.

    Returns (mapping, pending): pending names the images that list events but
    have no .dds yet. Their events are left alone rather than pointed at a
    missing file, which the engine would render as a magenta blob, silently.
    """
    mapping: dict[str, str] = {}
    pending: list[str] = []
    for name, img in images.items():
        if name not in on_disk:
            if img["events"]:
                pending.append(name)
            continue
        texture = f"gfx/event_pictures/{name}.dds"
        for event_id in img["events"]:
            mapping[event_id] = texture
    return mapping, pending


def _event_image_counts(lines: list[str]) -> dict[str, int]:
    """Count the event_image blocks inside each top-level event."""
    counts: dict[str, int] = {}
    current = None
    for line in lines:
        stripped = line.strip()
        m = _EVENT_DEF_RE.match(stripped)
        if m and current is None:
            current = m.group(1)
        if current and _IMAGE_OPEN_RE.match(stripped):
            counts[current] = counts.get(current, 0) + 1
        if current and stripped == '}' and not line[0:1].isspace():
            current = None
    return counts


def _update_event_file(filepath: Path, event_to_texture: dict,
                       dry_run: bool = False) -> tuple[int, list[str]]:
    """Point the mapped events in one file at their textures.

    Returns (events changed, events skipped because their art is conditional).
    An event that already shows its texture is left byte-for-byte as it is.
    """
    raw = filepath.read_bytes()
    has_bom = raw[:3] == b'\xef\xbb\xbf'
    content = raw.decode("utf-8-sig")
    lines = content.split('\n')
    counts = _event_image_counts(lines)

    result: list[str] = []
    current_event = None
    block: list[str] | None = None  # lines of the event_image block being read
    surplus = 0
    changes = 0
    skipped: list[str] = []

    def flush() -> int:
        text = '\n'.join(block)
        target = event_to_texture[current_event]
        if counts.get(current_event, 0) > 1 or _TRIGGER_RE.search(text):
            if current_event not in skipped:
                skipped.append(current_event)
            result.extend(block)
            return 0
        found = _TEXTURE_RE.search(text)
        if found and found.group(1) == target:
            result.extend(block)
            return 0
        indent = block[0][:len(block[0]) - len(block[0].lstrip())]
        result.append(f'{indent}event_image = {{ texture = "{target}" }}')
        return 1

    for line in lines:
        stripped = line.strip()

        if block is not None:
            block.append(line)
            surplus += stripped.count('{') - stripped.count('}')
            if surplus <= 0:
                changes += flush()
                block = None
            continue

        m = _EVENT_DEF_RE.match(stripped)
        if m and current_event is None:
            current_event = m.group(1)

        if current_event in event_to_texture and _IMAGE_OPEN_RE.match(stripped):
            block = [line]
            surplus = stripped.count('{') - stripped.count('}')
            if surplus <= 0:
                changes += flush()
                block = None
            continue

        # Simple heuristic: a line starting with "}" at column 0 ends the event
        if current_event and stripped == '}' and not line[0:1].isspace():
            current_event = None

        result.append(line)

    if changes > 0 and not dry_run:
        encoded = '\n'.join(result).encode('utf-8')
        if has_bom:
            encoded = b'\xef\xbb\xbf' + encoded
        filepath.write_bytes(encoded)

    return changes, skipped


def phase_update(images: dict, dry_run: bool = False) -> None:
    """Update event files with new texture references."""
    print(f"\n{'=' * 60}")
    print("PHASE 3: Update event files")
    print(f"{'=' * 60}")

    event_to_texture, pending = _build_event_to_texture(
        images, pictures_on_disk(str(GFX_DIR)))
    if pending:
        print(f"  PENDING (no .dds yet, events left as they are): "
              f"{', '.join(sorted(pending))}")
    total_changes = 0

    for txt in sorted(EVENTS_DIR.rglob("*.txt")):
        changes, skipped = _update_event_file(txt, event_to_texture, dry_run=dry_run)
        for eid in skipped:
            print(f"  SKIP (conditional art): {eid} in {txt.name}")
        if changes > 0:
            verb = "WOULD UPDATE" if dry_run else "UPDATED"
            print(f"  {verb}: {txt.name} ({changes} events)")
            total_changes += changes

    print(f"\n  Summary: {total_changes} event references "
          f"{'would be ' if dry_run else ''}updated")


# =========================================================================
# CLI
# =========================================================================

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate, convert, and wire event images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--phase",
        choices=["generate", "convert", "update"],
        default=None,
        help="Run only a specific phase (default: all three).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be done without making changes.",
    )
    p.add_argument(
        "--only",
        nargs="+",
        metavar="KEY",
        help="Process only these image keys (from event_image_prompts.py).",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="List all image keys and exit.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    all_images = load_images()

    if args.list:
        for name in sorted(all_images):
            n_events = len(all_images[name]["events"])
            print(f"  {name}  ({n_events} events)")
        print(f"\n  Total: {len(all_images)} images")
        return

    # Filter to --only keys if specified
    if args.only:
        unknown = [k for k in args.only if k not in all_images]
        if unknown:
            print(f"Error: unknown image keys: {', '.join(unknown)}")
            sys.exit(1)
        images = {k: all_images[k] for k in args.only}
        print(f"Processing {len(images)} of {len(all_images)} images")
    else:
        images = all_images

    phases = {
        "generate": phase_generate,
        "convert": phase_convert,
        "update": phase_update,
    }

    if args.phase:
        phases[args.phase](images, dry_run=args.dry_run)
    else:
        for phase_fn in phases.values():
            phase_fn(images, dry_run=args.dry_run)

    if not args.dry_run:
        print(f"\n{'=' * 60}")
        print("Done!")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
