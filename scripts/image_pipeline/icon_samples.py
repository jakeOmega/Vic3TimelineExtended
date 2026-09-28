#!/usr/bin/env python3
"""icon_samples.py - prototype: FLUX-generated UI icons in vanilla's per-category style.

Renders a few samples per category and a sheet placing each candidate after the
current placeholder and three vanilla neighbours. The rendering and composing
live in icon_render.py and the category styles in icon_prompts.py, which the
production pipeline (generate_icons.py) shares; this script only picks the
samples. Writes PNGs only.

  embed    encode every sample's prompt (cached per prompt)
  generate render every sample x seed with the transformer loaded once
  compose  fit each render into its category's vanilla layout, then the sheet

    FLUX_MODEL_DIR=<local FLUX.1-schnell snapshot on ext4> HF_HUB_OFFLINE=1 \
    VIC3_BASE_GAME=<game install> \
    .venv-img/bin/python scripts/image_pipeline/icon_samples.py --out DIR \
        [--stage embed|generate|compose] [--seeds N] [--offload sequential] [--only CAT[/KEY] ...]

Unset PYTHONPATH if a ROS or other install leaks packages into the venv.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from icon_prompts import CATEGORIES, prompt_for  # noqa: E402
from icon_render import Composer, embed, raw_path, render, review_sheet, vanilla_icons_dir  # noqa: E402

SAMPLES = [
    # (category, entity key, current placeholder, subject)
    ("technology", "transistors", "invention_icons/mass_communication.dds",
     "a single large vintage transistor with a black casing and three metal legs"),
    ("technology", "universal_basic_income", "invention_icons/mass_communication.dds",
     # "paper banknotes" alone came back as US dollars; name a colour.
     "an open hand holding a neat stack of plain cream-and-brown paper banknotes and a few coins"),
    ("technology", "space_elevator", "invention_icons/mass_communication.dds",
     "a miniature model of a space elevator: a slender lattice tether tower with a "
     "climber pod, on a round stone base"),
    ("treaty_article", "nuclear_disarmament", "diplomatic_treaties_articles_icons/offer_embassy.dds",
     "a nuclear missile warhead cracked open, with a large steel wrench resting across it"),
    ("treaty_article", "intelligence_sharing_pact", "diplomatic_treaties_articles_icons/offer_embassy.dds",
     "a manila dossier folder sealed with red wax, a brass magnifying glass lying on top"),
    ("diplomatic_action", "voluntary_union", "diplomatic_action_icons/force_become_subject.dds",
     "two hands clasped in a handshake"),
    ("building", "building_generic_spaceport", "building_icons/skyscraper.dds",
     "a spaceport with a rocket standing on its launch pad, gantry tower, hangars and a control tower"),
    ("building", "building_wonder_petronas_towers", "building_icons/skyscraper.dds",
     "the Petronas Twin Towers skyscrapers of Kuala Lumpur joined by their skybridge"),
    ("ideology", "ideology_environmentalists", "ig_icons/rural_folk.dds",
     "a leafy oak tree with spreading branches"),
    ("mobilization_option", "mobilization_option_robotic_assistance", "mobilization_options/luxurious_supplies.dds",
     "an industrial robotic arm with a gripper claw"),
    ("decree", "decree_pollution_control", "decree/decree_road_maintenance.dds",
     "a squat brick factory chimney capped with a big round green air filter"),
]

ONLY: set[str] = set()


def selected():
    """SAMPLES narrowed by --only (category or category/key)."""
    return [s for s in SAMPLES if not ONLY or s[0] in ONLY or f"{s[0]}/{s[1]}" in ONLY]


def name(cat: str, key: str) -> str:
    return f"{cat}__{key}"


def stage_embed(out: Path) -> None:
    embed({name(cat, key): prompt_for(cat, subject) for cat, key, _p, subject in selected()},
          out / "embeds")


def stage_generate(out: Path, seeds: int, offload: str) -> None:
    render([(name(cat, key), prompt_for(cat, subject), seed)
            for cat, key, _p, subject in selected() for seed in range(seeds)],
           out / "embeds", out / "raw", offload)


def stage_compose(out: Path, seeds: int) -> None:
    final = out / "final"
    final.mkdir(parents=True, exist_ok=True)
    composer = Composer()
    by_folder: dict[str, list] = {}
    for cat, key, placeholder, _subject in SAMPLES:
        spec = CATEGORIES[cat]
        made = []
        for seed in range(seeds):
            src = raw_path(out / "raw", name(cat, key), seed)
            if not src.exists():
                continue
            icon = composer.compose(Image.open(src), cat, spec)
            icon.save(final / src.name)
            made.append((f"s{seed}", icon))
        by_folder.setdefault(spec["folder"], []).append(
            (f"{cat}\n{key}", vanilla_icons_dir() / placeholder, made))
    for folder, rows in by_folder.items():
        review_sheet(rows, folder, out / f"contact_sheet_{folder}.png")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--stage", choices=["embed", "generate", "compose", "all"], default="all")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--only", nargs="*", default=[], help="category or category/key (embed + generate)")
    ap.add_argument("--offload", choices=["model", "sequential"], default="model")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    ONLY.update(args.only)
    (args.out / "samples.json").write_text(json.dumps(SAMPLES, indent=1))
    if args.stage in ("embed", "all"):
        stage_embed(args.out)
    if args.stage in ("generate", "all"):
        stage_generate(args.out, args.seeds, args.offload)
    if args.stage in ("compose", "all"):
        stage_compose(args.out, args.seeds)


if __name__ == "__main__":
    main()
