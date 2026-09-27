#!/usr/bin/env python3
"""
icon_prompts.py - FLUX prompt registry for the mod's UI icons.

The icon counterpart of event_image_prompts.py. `CATEGORIES` holds what makes
each category look like its vanilla folder (size, layout, style template);
`ICONS` holds, per category, one subject phrase per entity and its review
state. `generate_icons.py` renders, composes, writes and wires from here.

Each ICONS entry is {"subject": <phrase>, "seed": <state>}:
    seed None     not reviewed yet; renders candidates, writes nothing
    seed <int>    this candidate is the icon: its DDS is written and the
                  entity's icon line points at it
    seed "keep"   the borrowed vanilla icon fits; never rendered or rewired
A subject describes one physical object, with its material and colour.
Unnamed colours drift to real-world defaults: "paper banknotes" drew US
dollars. No screens with text, no currency, flags or faces.

Design, inventory and decisions: docs/superpowers/specs/2026-09-26-icon-pipeline-design.md.

Usage:
    python3 icon_prompts.py --validate   # registry vs the mod's files; exit 1 on errors
"""

from __future__ import annotations

KEEP = "keep"

# Style = what makes a category look like its vanilla folder. Subject = the one
# per-entity phrase a human (or an LLM draft from loc) has to write.
# Painterly, not photographic: FLUX.1-schnell drifts to product photography unless
# the prompt names the medium ("hand-painted game icon", brush strokes). Small
# categories (100 px) also need one compact object, or it downsizes to specks.
PAINTED = ("stylized hand-painted video game icon, painterly digital art with visible "
           "brush strokes, soft 3D shading, warm muted palette, blank unmarked surfaces, "
           "three-quarter view from slightly above, centered, isolated on a plain white background")
SILHOUETTE = ("a solid black silhouette of {subject}, simple flat pictogram stencil, "
              "bold clean shapes, no outline, on a plain white background")

# folder/size/mode/fill/style drive rendering and composing. A category that
# `generate_icons.py` produces also names where its entities live
# (`entity_dir`) and the field holding the icon path (`field`); its icons are
# written to gfx/interface/icons/<folder>/<key>.dds.
CATEGORIES = {
    "technology": dict(
        folder="invention_icons", size=256, mode="cutout", fill=0.92,
        entity_dir="common/technology/technologies", field="texture",
        style="{subject}, one chunky readable object, " + PAINTED),
    "treaty_article": dict(
        folder="diplomatic_treaties_articles_icons", size=100, mode="cutout", fill=0.98,
        style=("{subject}, one compact bold object group filling the frame, simple chunky "
               "silhouette, one strong accent color, " + PAINTED)),
    "diplomatic_action": dict(
        folder="diplomatic_action_icons", size=100, mode="cutout", fill=0.98,
        style=("{subject}, a compact miniature statue standing on top of a small square "
               "green marble pedestal, simple chunky silhouette, " + PAINTED)),
    "building": dict(
        folder="building_icons", size=256, mode="framed",
        style=("aerial three-quarter view of {subject}, detailed painted illustration "
               "of a miniature diorama, warm golden afternoon light, muted earthy "
               "palette, surrounding landscape, the building fills the center of the image")),
    "ideology": dict(
        folder="ideology_icons", size=220, mode="emboss_medallion", fill=0.60,
        color=(255, 228, 175), centre_lift=1.25, style=SILHOUETTE),
    "mobilization_option": dict(
        folder="mobilization_options", size=208, mode="emboss", fill=0.86,
        color=(240, 140, 90), style=SILHOUETTE),
    "decree": dict(
        folder="decree", size=158, mode="medallion", fill=0.78, centre_lift=2.1,
        grade_folder="invention_icons",
        style="{subject}, one chunky compact object, bright warm lighting, " + PAINTED),
}


def prompt_for(cat: str, subject: str) -> str:
    return CATEGORIES[cat]["style"].format(subject=subject) + ", no text, no writing, no letters"


def icon_path(cat: str, key: str) -> str:
    """The mod path an accepted icon is written to and wired as."""
    return f"gfx/interface/icons/{CATEGORIES[cat]['folder']}/{key}.dds"


ICONS: dict[str, dict[str, dict]] = {
    "technology": {},
}


def check(mod_root: str | None = None, on_disk: set[str] | None = None) -> dict:
    """Compare ICONS with the mod's entity files.

    Errors:
      unknown     a key with no plain top-level definition in its entity_dir
      bad_entry   an empty subject, or a seed that is not None, an int or "keep"
      missing_dds an accepted seed whose DDS is not committed (or on disk)
    Information:
      states      how many entries are unreviewed / accepted / kept
    `on_disk` defaults to the icon paths git tracks, so it works in a sparse
    worktree.
    """
    import os
    import re
    import subprocess

    mod_root = mod_root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if on_disk is None:
        out = subprocess.run(["git", "-C", mod_root, "ls-files", "--", "gfx/interface/icons"],
                             capture_output=True, text=True, check=True).stdout
        on_disk = set(out.splitlines())
    report: dict = {"unknown": [], "bad_entry": [], "missing_dds": [], "states": {}}
    for cat, entries in ICONS.items():
        spec = CATEGORIES[cat]
        defined: set[str] = set()
        for dirpath, _dirs, files in os.walk(os.path.join(mod_root, spec["entity_dir"])):
            for fname in files:
                if fname.endswith(".txt"):
                    with open(os.path.join(dirpath, fname), encoding="utf-8-sig", errors="replace") as fh:
                        defined |= set(re.findall(r"^([A-Za-z0-9_\-]+)\s*=\s*\{", fh.read(), re.M))
        states = {"unreviewed": 0, "accepted": 0, "kept": 0}
        for key, entry in entries.items():
            if key not in defined:
                report["unknown"].append((cat, key))
            seed = entry.get("seed")
            if not entry.get("subject") or not (seed is None or seed == KEEP
                                                or (isinstance(seed, int) and seed >= 0)):
                report["bad_entry"].append((cat, key))
                continue
            if seed is None:
                states["unreviewed"] += 1
            elif seed == KEEP:
                states["kept"] += 1
            else:
                states["accepted"] += 1
                if icon_path(cat, key) not in on_disk:
                    report["missing_dds"].append((cat, key))
        report["states"][cat] = states
    return report


def validate() -> bool:
    r = check()
    for title in ("unknown", "bad_entry", "missing_dds"):
        if r[title]:
            print(f"{title.upper()} ({len(r[title])}):")
            for cat, key in r[title]:
                print(f"  {cat}/{key}")
    for cat, states in r["states"].items():
        print(f"{cat}: " + ", ".join(f"{n} {s}" for s, n in states.items()))
    errors = len(r["unknown"]) + len(r["bad_entry"]) + len(r["missing_dds"])
    print(f"Errors: {errors}")
    return errors == 0


if __name__ == "__main__":
    import sys

    if "--validate" in sys.argv:
        sys.exit(0 if validate() else 1)
    for cat, entries in ICONS.items():
        print(f"{cat}: {len(entries)} icons")
