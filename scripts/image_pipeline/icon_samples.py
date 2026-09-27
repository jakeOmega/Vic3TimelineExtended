#!/usr/bin/env python3
"""icon_samples.py - prototype: FLUX-generated UI icons in vanilla's per-category style.

Experiment for extending the event-image pipeline to the mod's icon placeholders
(techs on `mass_communication.dds`, treaty articles on `offer_embassy.dds`,
buildings on `skyscraper.dds`, decrees on `decree_road_maintenance.dds`, ...).

Three stages:

  embed    Encode every prompt with FLUX's text encoders, save the embeddings,
           free the encoders. Keeps peak RAM at ~one model, not T5 + transformer.
           Skips a prompt whose saved embedding was made from the same text.
  generate Load the FLUX transformer ONCE and render every sample x seed
           (`generate_event_images.py` reloads the 24 GB model per image).
           Each render gets a `<name>.prompt.txt` beside it; a render is redone
           when that text differs from the current prompt, so editing a subject
           or a style re-renders just what it affects. An embedding made from an
           older prompt is an error (rerun `embed`). Neither stage loads a model
           when everything is up to date.
  compose  Fit each raw render into its category's vanilla layout:
             cutout    - background removed (rembg), trimmed, padded, graded
             framed    - full-bleed scene inside the frame lifted from vanilla
             medallion - cutout on a disc, under the ring lifted from vanilla
           then write a comparison sheet next to vanilla neighbours.

Frames are not hand-drawn: `vanilla_template()` takes the per-pixel median of
every vanilla icon in the category's folder. The frame is the part that never
changes, so it survives the median intact while the artwork averages to mud.

Needs the optional image stack (torch, diffusers, rembg + plain onnxruntime;
rembg[gpu]'s onnxruntime-gpu wants CUDA 13 libs and falls back to CPU anyway).
Writes PNGs only; no DDS, no reference rewriting. Never downloads weights:
`FLUX_MODEL_DIR` must name a local snapshot (or the HF cache must hold one).

    FLUX_MODEL_DIR=<local FLUX.1-schnell snapshot on ext4> HF_HUB_OFFLINE=1 \
    VIC3_BASE_GAME=<game install> \
    .venv-img/bin/python scripts/image_pipeline/icon_samples.py --out DIR \
        [--stage embed|generate|compose] [--seeds N] [--offload sequential] [--only CAT[/KEY] ...]

On a 10 GB card use `--offload sequential` (model offload OOMs on the 24 GB
transformer): ~30 s/image warm, 2-4 min for the first. `embed` reloads T5 and
takes ~5 min per process, so embed the whole batch once. Unset PYTHONPATH if a
ROS or other install leaks packages into the venv.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

MODEL = os.environ.get("FLUX_MODEL_DIR", "black-forest-labs/FLUX.1-schnell")
GEN_SIZE = 1024

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

CATEGORIES = {
    "technology": dict(
        folder="invention_icons", size=256, mode="cutout", fill=0.92,
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


def vanilla_icons_dir() -> Path:
    from path_constants import base_game_path
    return Path(base_game_path) / "game" / "gfx" / "interface" / "icons"


def slug(cat: str, key: str, seed: int) -> str:
    return f"{cat}__{key}__s{seed}"


def prompt_for(cat: str, subject: str) -> str:
    return CATEGORIES[cat]["style"].format(subject=subject) + ", no text, no writing, no letters"


def load_pipe(**components):
    """FluxPipeline from local files only.

    A bare hub id with an unset or stale HF_HOME would otherwise start a 32 GB
    download (see the spec's runtime notes).
    """
    import torch
    from diffusers import FluxPipeline
    try:
        return FluxPipeline.from_pretrained(MODEL, local_files_only=True,
                                            torch_dtype=torch.bfloat16, **components)
    except OSError as e:
        raise SystemExit(f"FLUX weights not found locally ({MODEL}). Point FLUX_MODEL_DIR at a "
                         f"local FLUX.1-schnell snapshot; this script never downloads.\n{e}")


# ── stage 1: embed ───────────────────────────────────────────────────────

def stage_embed(out: Path) -> None:
    import torch

    emb_dir = out / "embeds"
    emb_dir.mkdir(parents=True, exist_ok=True)
    todo = []
    for cat, key, _placeholder, subject in selected():
        prompt = prompt_for(cat, subject)
        dest = emb_dir / f"{cat}__{key}.pt"
        if dest.exists() and torch.load(dest)["prompt"] == prompt:
            continue
        todo.append((cat, key, prompt))
    if not todo:
        print("embed: every embedding is up to date")
        return
    pipe = load_pipe(transformer=None, vae=None)
    pipe.enable_model_cpu_offload()
    for cat, key, prompt in todo:
        with torch.no_grad():
            pe, pooled, _ids = pipe.encode_prompt(prompt=prompt, prompt_2=None, max_sequence_length=256)
        torch.save({"prompt_embeds": pe.cpu(), "pooled": pooled.cpu(), "prompt": prompt},
                   emb_dir / f"{cat}__{key}.pt")
        print(f"embedded {cat}/{key}")
    del pipe
    gc.collect()


# ── stage 2: generate ────────────────────────────────────────────────────

def stage_generate(out: Path, seeds: int, offload: str) -> None:
    import time

    import torch

    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    todo = []
    for cat, key, _placeholder, subject in selected():
        prompt = prompt_for(cat, subject)
        emb_path = out / "embeds" / f"{cat}__{key}.pt"
        if not emb_path.exists():
            raise SystemExit(f"no embedding for {cat}/{key}: run --stage embed first")
        emb = torch.load(emb_path)
        if emb["prompt"] != prompt:
            raise SystemExit(f"the embedding for {cat}/{key} was made from an older prompt: "
                             "rerun --stage embed")
        for seed in range(seeds):
            dest = raw / f"{slug(cat, key, seed)}.png"
            note = dest.with_suffix(".prompt.txt")
            if dest.exists() and note.exists() and note.read_text(encoding="utf-8") == prompt:
                continue
            todo.append((emb, seed, dest, note, prompt))
    if not todo:
        print("generate: every render is up to date")
        return

    t0 = time.time()
    pipe = load_pipe(text_encoder=None, text_encoder_2=None, tokenizer=None, tokenizer_2=None)
    if offload == "sequential":
        pipe.enable_sequential_cpu_offload()
    else:
        pipe.enable_model_cpu_offload()
    print(f"loaded transformer in {time.time() - t0:.0f}s ({offload} offload)")
    for emb, seed, dest, note, prompt in todo:
        t1 = time.time()
        image = pipe(
            prompt_embeds=emb["prompt_embeds"].to("cuda"),
            pooled_prompt_embeds=emb["pooled"].to("cuda"),
            guidance_scale=0.0, num_inference_steps=4, max_sequence_length=256,
            width=GEN_SIZE, height=GEN_SIZE,
            generator=torch.Generator("cpu").manual_seed(1000 + seed),
        ).images[0]
        image.save(dest)
        note.write_text(prompt, encoding="utf-8")
        print(f"  {dest.name}  {time.time() - t1:.0f}s")


# ── stage 3: compose ─────────────────────────────────────────────────────

def load_rgba(p: Path) -> Image.Image:
    return Image.open(p).convert("RGBA")


def vanilla_template(folder: str, size: int) -> tuple[np.ndarray, np.ndarray]:
    """Per-pixel median and colour spread over every same-size vanilla icon in folder."""
    stack = []
    for f in sorted((vanilla_icons_dir() / folder).glob("*.dds")):
        try:
            im = load_rgba(f)
        except Exception:
            continue
        if im.size == (size, size):
            stack.append(np.asarray(im, dtype=np.float32))
    if not stack:
        raise SystemExit(f"no {size}x{size} .dds in {vanilla_icons_dir() / folder}: "
                         "check VIC3_BASE_GAME")
    a = np.stack(stack)
    return np.median(a, axis=0), a[..., :3].std(axis=0).mean(-1)


def category_grade_target(folder: str) -> tuple[float, float]:
    """Median saturation / value of opaque pixels across the vanilla folder (HSV, 0..1)."""
    sats, vals = [], []
    for f in sorted((vanilla_icons_dir() / folder).glob("*.dds"))[:80]:
        try:
            im = load_rgba(f)
        except Exception:
            continue
        a = np.asarray(im)
        hsv = np.asarray(im.convert("RGB").convert("HSV"), dtype=np.float32) / 255
        m = a[..., 3] > 200
        if m.sum() > 50:
            sats.append(np.median(hsv[..., 1][m]))
            vals.append(np.median(hsv[..., 2][m]))
    return float(np.median(sats)), float(np.median(vals))


def grade(im: Image.Image, target: tuple[float, float], strength: float = 0.7) -> Image.Image:
    """Pull median saturation/value of the opaque part toward the vanilla folder's."""
    a = np.asarray(im)
    alpha = a[..., 3]
    hsv = np.asarray(im.convert("RGB").convert("HSV"), dtype=np.float32) / 255
    m = alpha > 200
    if m.sum() < 50:
        return im
    s_ratio = (target[0] / max(np.median(hsv[..., 1][m]), 1e-3)) ** strength
    v_ratio = (target[1] / max(np.median(hsv[..., 2][m]), 1e-3)) ** strength
    hsv[..., 1] = np.clip(hsv[..., 1] * s_ratio, 0, 1)
    hsv[..., 2] = np.clip(hsv[..., 2] * v_ratio, 0, 1)
    rgb = Image.fromarray((hsv * 255).astype(np.uint8), "HSV").convert("RGB")
    out = rgb.convert("RGBA")
    out.putalpha(Image.fromarray(alpha))
    return out


def resize_premultiplied(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    """LANCZOS resize without the dark/white fringe straight-alpha resizing leaves."""
    a = np.asarray(im, dtype=np.float32) / 255
    pm = a.copy()
    pm[..., :3] *= pm[..., 3:4]
    chans = [Image.fromarray((pm[..., i] * 255).astype(np.uint8)).resize(size, Image.LANCZOS)
             for i in range(4)]
    r = np.stack([np.asarray(c, dtype=np.float32) / 255 for c in chans], -1)
    al = r[..., 3:4]
    r[..., :3] = np.where(al > 1e-3, r[..., :3] / np.maximum(al, 1e-3), 0)
    return Image.fromarray((np.clip(r, 0, 1) * 255).astype(np.uint8), "RGBA")


_REMBG = None


def cut_out(im: Image.Image) -> Image.Image:
    global _REMBG
    from rembg import new_session, remove
    if _REMBG is None:
        _REMBG = new_session(os.environ.get("REMBG_MODEL", "isnet-general-use"))
    return remove(im, session=_REMBG)


def fit_square(obj: Image.Image, size: int, fill: float) -> Image.Image:
    """Trim to the opaque bbox, pad to a square where the object spans `fill` of the side."""
    bbox = obj.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    if bbox:
        obj = obj.crop(bbox)
    side = int(max(obj.size) / fill)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(obj, ((side - obj.width) // 2, (side - obj.height) // 2))
    return resize_premultiplied(canvas, (size, size))


def drop_shadow(im: Image.Image, offset: int, blur: float, opacity: float) -> Image.Image:
    alpha = im.getchannel("A")
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(alpha.point(lambda v: int(v * opacity)))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    base = Image.new("RGBA", im.size, (0, 0, 0, 0))
    base.alpha_composite(sh, (offset, offset))
    base.alpha_composite(im)
    return base


def compose_cutout(raw: Image.Image, spec: dict, target) -> Image.Image:
    icon = fit_square(cut_out(raw), spec["size"], spec["fill"])
    icon = grade(icon, target)
    return drop_shadow(icon, max(1, spec["size"] // 100), spec["size"] / 90, 0.45)


def compose_framed(raw: Image.Image, spec: dict, tmpl) -> Image.Image:
    med, std = tmpl
    size = spec["size"]
    scene = resize_premultiplied(raw.convert("RGBA"), (size, size))
    alpha = med[..., 3]
    # The frame = opaque pixels within a few px of the silhouette edge (their
    # colour is identical across vanilla, so std is low there).
    edge = Image.fromarray((alpha > 128).astype(np.uint8) * 255).filter(ImageFilter.MinFilter(19))
    inner = np.asarray(edge, dtype=np.float32) / 255
    inner = np.asarray(Image.fromarray((inner * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)),
                       dtype=np.float32) / 255
    sc = np.asarray(scene, dtype=np.float32)
    out = med.copy()
    out[..., :3] = sc[..., :3] * inner[..., None] + med[..., :3] * (1 - inner[..., None])
    out[..., 3] = alpha
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


def embossed(raw: Image.Image, spec: dict, size: int) -> Image.Image:
    """FLUX silhouette -> the PM/law pipeline's metallic emboss, at `size`."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gen_pm_icons import apply_metallic_style
    lum = np.asarray(raw.convert("L").resize((size * 2, size * 2), Image.LANCZOS), dtype=np.float64) / 255
    mask = np.clip(((1 - lum) - 0.35) / 0.3, 0, 1)
    ys, xs = np.nonzero(mask > 0.5)
    if len(xs):
        mask = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = mask.shape
    side = int(max(h, w) / spec["fill"])
    canvas = np.zeros((side, side))
    canvas[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = mask
    m = np.asarray(Image.fromarray((canvas * 255).astype(np.uint8)).resize((size, size), Image.LANCZOS),
                   dtype=np.float64) / 255
    return Image.fromarray(apply_metallic_style(m, spec["color"]), "RGBA")


def compose_medallion(raw: Image.Image, spec: dict, tmpl, target, obj: Image.Image | None = None) -> Image.Image:
    med, std = tmpl
    size = spec["size"]
    c = (size - 1) / 2
    yy, xx = np.mgrid[0:size, 0:size]
    r = np.hypot(xx - c, yy - c)
    alpha = med[..., 3]
    radius = r[alpha > 128].max()
    # The ring is identical on every vanilla icon, so it starts where the
    # colour spread across the folder collapses (decree r=68/79, ideology 87/110).
    ring_in = next((rr for rr in np.arange(radius * 0.6, radius, 0.5)
                    if std[(r >= rr) & (r < rr + 1)].mean() < 30), radius - size * 0.055)
    # Disc background: radial gradient between the median's colour a little
    # inside the ring and a lifted centre (vanilla discs are lit from the middle).
    band = (r > ring_in - 12) & (r < ring_in - 6) & (alpha > 200)
    edge_col = np.median(med[..., :3][band], axis=0)
    centre_col = np.clip(edge_col * spec.get("centre_lift", 2.1), 0, 255)
    t = np.clip(r / ring_in, 0, 1)[..., None]
    bg = centre_col * (1 - t) + edge_col * t
    base = np.dstack([bg, alpha]).astype(np.uint8)
    icon = Image.fromarray(base, "RGBA")
    if obj is None:
        obj = grade(fit_square(cut_out(raw), size, 1.0), target)
    inner = int(size * spec["fill"])
    obj = resize_premultiplied(obj, (inner, inner))
    icon.alpha_composite(drop_shadow(obj, 2, 2.5, 0.5), ((size - inner) // 2, (size - inner) // 2 + 2))
    # Ring on top, from the median.
    ring = np.clip((r - ring_in + 1) / 2, 0, 1) * (alpha / 255)
    arr = np.asarray(icon, dtype=np.float32)
    arr[..., :3] = med[..., :3] * ring[..., None] + arr[..., :3] * (1 - ring[..., None])
    arr[..., 3] = alpha
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def stage_compose(out: Path, seeds: int) -> None:
    final = out / "final"
    final.mkdir(parents=True, exist_ok=True)
    tmpls, targets = {}, {}
    rows = []
    for cat, key, placeholder, _subject in SAMPLES:
        spec = CATEGORIES[cat]
        if spec["mode"] in ("framed", "medallion", "emboss_medallion") and cat not in tmpls:
            tmpls[cat] = vanilla_template(spec["folder"], spec["size"])
        if spec["mode"] in ("cutout", "medallion") and cat not in targets:
            # A medallion's opaque pixels are mostly its dark disc: grade the
            # object against a folder of bare objects instead.
            targets[cat] = category_grade_target(spec.get("grade_folder", spec["folder"]))
        made = []
        for seed in range(seeds):
            src = out / "raw" / f"{slug(cat, key, seed)}.png"
            if not src.exists():
                continue
            raw = Image.open(src).convert("RGB")
            if spec["mode"] == "cutout":
                icon = compose_cutout(raw, spec, targets[cat])
            elif spec["mode"] == "framed":
                icon = compose_framed(raw, spec, tmpls[cat])
            elif spec["mode"] == "emboss":
                icon = embossed(raw, spec, spec["size"])
            elif spec["mode"] == "emboss_medallion":
                icon = compose_medallion(raw, spec, tmpls[cat], None,
                                         obj=embossed(raw, dict(spec, fill=0.95), spec["size"]))
            else:
                icon = compose_medallion(raw, spec, tmpls[cat], targets[cat])
            dest = final / f"{slug(cat, key, seed)}.png"
            icon.save(dest)
            made.append(dest)
        rows.append((cat, key, placeholder, made))
    contact_sheet(out, rows)


def contact_sheet(out: Path, rows) -> None:
    """Row per sample: [current placeholder | 3 vanilla neighbours || candidates], at native size."""
    vdir = vanilla_icons_dir()
    cell = 270
    ncols = 1 + 3 + max((len(m) for *_, m in rows), default=0)
    sheet = Image.new("RGBA", (220 + cell * ncols, cell * len(rows)), (33, 34, 40, 255))
    d = ImageDraw.Draw(sheet)
    rng = np.random.default_rng(7)
    for i, (cat, key, placeholder, made) in enumerate(rows):
        y = i * cell
        d.text((6, y + 8), f"{cat}\n{key}", fill=(235, 235, 235, 255))
        d.text((6, y + cell - 40), "placeholder | vanilla x3 ||\ncandidates (native px)", fill=(150, 150, 150, 255))
        folder = CATEGORIES[cat]["folder"]
        pool = [p for p in sorted((vdir / folder).glob("*.dds")) if p.name != Path(placeholder).name]
        neighbours = [pool[j] for j in rng.choice(len(pool), 3, replace=False)]
        tiles = [vdir / placeholder] + neighbours + list(made)
        for j, p in enumerate(tiles):
            try:
                im = load_rgba(p)
            except Exception:
                continue
            x = 220 + j * cell + (cell - im.width) // 2
            sheet.alpha_composite(im, (x, y + (cell - im.height) // 2))
            if j == 4:
                d.line([(220 + 4 * cell - 3, y + 10), (220 + 4 * cell - 3, y + cell - 10)],
                       fill=(200, 170, 90, 255), width=2)
    sheet.save(out / "contact_sheet.png")
    print(f"wrote {out / 'contact_sheet.png'}")


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
