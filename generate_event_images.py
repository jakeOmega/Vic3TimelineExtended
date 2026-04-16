#!/usr/bin/env python3
"""
generate_event_images.py - Three-phase pipeline for event image generation.

Phase 1 (generate): Call gen_image.py for each image -> generated_images/*.png
Phase 2 (convert):  Call convert_event_image.py     -> gfx/event_pictures/*.dds
Phase 3 (update):   Update event files with new texture references

Each phase skips already-completed work, making the script safe to re-run.
If it fails partway through, re-run with --phase to resume from that phase.

Usage:
    python generate_event_images.py                    # All three phases
    python generate_event_images.py --phase generate   # Phase 1 only
    python generate_event_images.py --phase convert    # Phase 2 only
    python generate_event_images.py --phase update     # Phase 3 only
    python generate_event_images.py --dry-run          # Preview what would be done
    python generate_event_images.py --only KEY1 KEY2   # Process specific images only
    python generate_event_images.py --list              # List all image keys

Note: Phase 1 calls gen_image.py as a subprocess for each image. The FLUX model
(~34GB) is loaded each time, so generating all ~317 images will take many hours.
Consider using --only to generate in batches, or running overnight.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

MOD_ROOT = Path(__file__).resolve().parent
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
    gen_script = MOD_ROOT / "gen_image.py"

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
            print(f"  Re-run to continue from where you left off.")
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
    convert_script = MOD_ROOT / "convert_event_image.py"

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
            print(f"  Re-run with --phase convert to continue.")
            sys.exit(1)

    print(f"\n  Summary: {converted} converted, {skipped} skipped, "
          f"{missing} missing PNG, {failed} failed")


# =========================================================================
# Phase 3: Update event files
# =========================================================================

def _build_event_to_texture(images: dict) -> dict[str, str]:
    """Build mapping: event_id -> texture path string."""
    mapping = {}
    for name, img in images.items():
        texture = f"gfx/event_pictures/{name}.dds"
        for event_id in img["events"]:
            mapping[event_id] = texture
    return mapping


def _update_event_file(filepath: Path, event_to_texture: dict,
                       dry_run: bool = False) -> int:
    """Update event_image references in a single event file.

    Returns the number of events updated.
    """
    raw = filepath.read_bytes()
    has_bom = raw[:3] == b'\xef\xbb\xbf'
    content = raw.decode("utf-8-sig")
    lines = content.split('\n')

    result = []
    current_event = None
    skip_until_balanced = False
    image_brace_surplus = 0
    changes = 0

    for line in lines:
        stripped = line.strip()

        # Track event definition start (top-level: "namespace.id = {")
        m = re.match(r'^(\w+\.\d+)\s*=\s*\{', stripped)
        if m and current_event is None:
            current_event = m.group(1)

        # If we're skipping lines from a multi-line event_image block
        if skip_until_balanced:
            image_brace_surplus += stripped.count('{') - stripped.count('}')
            if image_brace_surplus <= 0:
                skip_until_balanced = False
            # Don't append this line (it's part of the old event_image block)
            continue

        # Check for event_image line inside a mapped event
        if (current_event
                and current_event in event_to_texture
                and re.match(r'\s*event_image\s*=\s*\{', stripped)):
            indent = line[:len(line) - len(line.lstrip())]
            new_texture = event_to_texture[current_event]
            replacement = f'{indent}event_image = {{ texture = "{new_texture}" }}'
            result.append(replacement)
            changes += 1

            # Check if this is a multi-line block (more { than })
            opens = stripped.count('{')
            closes = stripped.count('}')
            if opens > closes:
                skip_until_balanced = True
                image_brace_surplus = opens - closes
            continue

        # Track when we leave an event definition
        # Simple heuristic: a line starting with "}" at column 0 ends the event
        if current_event and stripped == '}' and not line[0:1].isspace():
            current_event = None

        result.append(line)

    if changes > 0 and not dry_run:
        new_content = '\n'.join(result)
        encoded = new_content.encode('utf-8')
        if has_bom:
            encoded = b'\xef\xbb\xbf' + encoded
        filepath.write_bytes(encoded)

    return changes


def phase_update(images: dict, dry_run: bool = False) -> None:
    """Update event files with new texture references."""
    print(f"\n{'=' * 60}")
    print("PHASE 3: Update event files")
    print(f"{'=' * 60}")

    event_to_texture = _build_event_to_texture(images)
    total_changes = 0

    for txt in sorted(EVENTS_DIR.glob("*.txt")):
        changes = _update_event_file(txt, event_to_texture, dry_run=dry_run)
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
