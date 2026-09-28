#!/usr/bin/env python3
"""icon_render.py - FLUX rendering and vanilla-style composing for UI icons.

Shared by icon_samples.py (the prototype sheet) and generate_icons.py (the
production pipeline). Nothing here knows about a particular entity list.

  embed()    Encode prompts with FLUX's text encoders, one process, cached per
             name: a name whose saved embedding came from the same prompt is
             skipped, and T5 is not loaded when nothing needs encoding.
  render()   Load the FLUX transformer once and render (name, prompt, seed)
             jobs. Each render gets a `<name>__s<seed>.prompt.txt` beside it and
             is redone when that differs, so editing a subject re-renders only
             what it changes; an embedding made from an older prompt is an error.
  Composer   Fits a raw render into its category's vanilla layout:
               cutout           background removed (rembg), trimmed, padded, graded
               framed           full-bleed scene inside the frame lifted from vanilla
               medallion        cutout on a disc, under the ring lifted from vanilla
               emboss           FLUX silhouette -> the PM pipeline's metallic emboss
               emboss_medallion that emboss on the disc and ring
               plinth           cutout standing on the slab lifted from vanilla
               tinted           cutout recast in its folder's one metal (laws, institutions)
  review_sheet()  Row per entity: [current icon | 3 vanilla neighbours || candidates].

Frames are not hand-drawn: `vanilla_template()` takes the per-pixel median of
every vanilla icon in the category's folder. The frame is the part that never
changes, so it survives the median intact while the artwork averages to mud.
The composer therefore needs the game install (VIC3_BASE_GAME).

Needs the optional image stack (torch, diffusers, rembg + plain onnxruntime) in
.venv-img; see docs/guides/python_tools.md. Never downloads weights:
FLUX_MODEL_DIR must name a local FLUX.1-schnell snapshot. On the 10 GB 3080 use
sequential offload (~30 s per 1024² image warm).
"""
from __future__ import annotations

import gc
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # path_constants
from icon_dds import resize_premultiplied  # noqa: E402

MODEL = os.environ.get("FLUX_MODEL_DIR", "black-forest-labs/FLUX.1-schnell")
GEN_SIZE = 1024


def vanilla_icons_dir() -> Path:
    from path_constants import base_game_path
    return Path(base_game_path) / "game" / "gfx" / "interface" / "icons"


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


# ── embed and render ─────────────────────────────────────────────────────

def embed(prompts: dict[str, str], emb_dir: Path) -> None:
    """Encode `prompts` ({name: prompt}) to emb_dir/<name>.pt, skipping current ones."""
    import torch

    emb_dir.mkdir(parents=True, exist_ok=True)
    todo = {n: p for n, p in prompts.items()
            if not ((emb_dir / f"{n}.pt").exists() and torch.load(emb_dir / f"{n}.pt")["prompt"] == p)}
    if not todo:
        print(f"embed: all {len(prompts)} embeddings are up to date")
        return
    pipe = load_pipe(transformer=None, vae=None)
    pipe.enable_model_cpu_offload()
    for name, prompt in todo.items():
        with torch.no_grad():
            pe, pooled, _ids = pipe.encode_prompt(prompt=prompt, prompt_2=None, max_sequence_length=256)
        torch.save({"prompt_embeds": pe.cpu(), "pooled": pooled.cpu(), "prompt": prompt},
                   emb_dir / f"{name}.pt")
        print(f"embedded {name}")
    del pipe
    gc.collect()


def raw_path(raw_dir: Path, name: str, seed: int) -> Path:
    return raw_dir / f"{name}__s{seed}.png"


def render(jobs: list[tuple[str, str, int]], emb_dir: Path, raw_dir: Path,
           offload: str = "sequential", size: tuple[int, int] = (GEN_SIZE, GEN_SIZE)) -> None:
    """Render (name, prompt, seed) jobs to raw_dir/<name>__s<seed>.png, skipping current ones."""
    import time

    import torch

    raw_dir.mkdir(parents=True, exist_ok=True)
    todo, embeds = [], {}
    for name, prompt, seed in jobs:
        dest = raw_path(raw_dir, name, seed)
        note = dest.with_suffix(".prompt.txt")
        if dest.exists() and note.exists() and note.read_text(encoding="utf-8") == prompt:
            continue
        if name not in embeds:
            emb_path = emb_dir / f"{name}.pt"
            if not emb_path.exists():
                raise SystemExit(f"no embedding for {name}: embed first")
            embeds[name] = torch.load(emb_path)
            if embeds[name]["prompt"] != prompt:
                raise SystemExit(f"the embedding for {name} was made from an older prompt: embed again")
        todo.append((embeds[name], seed, dest, note, prompt))
    if not todo:
        print(f"render: all {len(jobs)} renders are up to date")
        return

    t0 = time.time()
    pipe = load_pipe(text_encoder=None, text_encoder_2=None, tokenizer=None, tokenizer_2=None)
    if offload == "sequential":
        pipe.enable_sequential_cpu_offload()
    else:
        pipe.enable_model_cpu_offload()
    print(f"loaded transformer in {time.time() - t0:.0f}s ({offload} offload); {len(todo)} to render")
    for i, (emb, seed, dest, note, prompt) in enumerate(todo, 1):
        t1 = time.time()
        image = pipe(
            prompt_embeds=emb["prompt_embeds"].to("cuda"),
            pooled_prompt_embeds=emb["pooled"].to("cuda"),
            guidance_scale=0.0, num_inference_steps=4, max_sequence_length=256,
            width=size[0], height=size[1],
            generator=torch.Generator("cpu").manual_seed(1000 + seed),
        ).images[0]
        image.save(dest)
        note.write_text(prompt, encoding="utf-8")
        print(f"  [{i}/{len(todo)}] {dest.name}  {time.time() - t1:.0f}s", flush=True)


# ── compose ──────────────────────────────────────────────────────────────

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
    top = apply_metallic_style(m, spec["color"])
    if "color_bottom" not in spec:
        return Image.fromarray(top, "RGBA")
    # Vanilla's copper shifts hue down the shape, pinkish at the top to
    # orange-brown at the bottom, not just darker. The style is linear in its
    # colour, so blending a render in each colour row by row over the shape's
    # height gives that gradient.
    bottom = apply_metallic_style(m, spec["color_bottom"])
    rows = np.nonzero((m > 0.5).any(axis=1))[0]
    t = np.zeros((size, 1, 1))
    if len(rows):
        t[:, 0, 0] = np.clip((np.arange(size) - rows[0]) / max(rows[-1] - rows[0], 1), 0, 1)
    out = top.astype(np.float64) * (1 - t) + bottom.astype(np.float64) * t
    out[..., 3] = top[..., 3]
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8), "RGBA")


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


def plinth_template(folder: str, size: int) -> tuple[np.ndarray, int, int]:
    """The stone slab vanilla's diplomatic-action figures stand on, lifted by median.

    Most icons in diplomatic_action_icons stand their figure on the same
    octagonal slab: a green top face over a golden-stone base. Taking the
    per-pixel median over the icons whose slab sits in the common place keeps
    the slab and blurs the figures. On the top face, where every figure
    stands, each pixel instead takes the median over only the icons in which it
    is still green (no figure covers it there), which recovers the bare marble
    and its rim. Returns (slab RGBA, top-face first row, top-face centre row).
    """
    k = size / 100
    stack = []
    for f in sorted((vanilla_icons_dir() / folder).glob("*.dds")):
        try:
            im = load_rgba(f)
        except Exception:
            continue
        if im.size != (size, size):
            continue
        a = np.asarray(im).astype(int)
        top, base = a[int(82 * k), int(20 * k)], a[int(92 * k), int(25 * k)]
        if (top[3] > 200 and top[1] > top[0] + 30 and top[1] > top[2] + 20
                and base[3] > 200 and base[:3].sum() < 260):
            stack.append(a.astype(np.float32))
    if len(stack) < 5:
        raise SystemExit(f"only {len(stack)} slab icons found in {vanilla_icons_dir() / folder}: "
                         "check VIC3_BASE_GAME")
    arr = np.stack(stack)
    med = np.median(arr, axis=0)
    # Where a pixel is still green in an icon, no figure covers it there. Its
    # median over just those icons is the bare slab, texture and rim included.
    bare = (arr[..., 3] > 200) & (arr[..., 1] > arr[..., 0] + 15) & (arr[..., 1] > arr[..., 2])
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            bare_med = np.nanmedian(np.where(bare[..., None], arr, np.nan), axis=0)
    # A figure's own green parts (arrows, hills) are green in one or two icons;
    # the slab is bare in many.
    bare_med[bare.sum(axis=0) < max(3, len(stack) // 4)] = np.nan

    def green(px):
        return px[..., 3] > 200 and px[1] > px[0] + 15 and px[1] > px[2]

    # Probe a quarter of the way in, clear of the octagon's cut corners.
    probe = int(25 * k)
    rows = [y for y in range(int(55 * k), size) if green(med[y, probe])]
    if not rows:
        raise SystemExit("no slab top face found in the median")
    y0, y1 = rows[0], rows[-1]
    slab = med.copy()
    slab[:y0, :, 3] = 0
    for y in range(y0, y1 + 1):
        cols = [x for x in range(size) if not np.isnan(bare_med[y, x, 0])]
        if cols:
            a, b = min(cols), max(cols)
            for x in range(a, b + 1):
                if not np.isnan(bare_med[y, x, 0]):
                    slab[y, x] = bare_med[y, x]
                else:  # covered in every icon: borrow the nearest bare neighbour
                    near = min(cols, key=lambda c: abs(c - x))
                    slab[y, x] = bare_med[y, near]
    return slab, y0, (y0 + y1) // 2


def compose_plinth(raw: Image.Image, spec: dict, tmpl, target) -> Image.Image:
    """Cut the figure out and stand it on the slab lifted from vanilla."""
    slab, y0, face = tmpl
    size = spec["size"]
    obj = cut_out(raw)
    bbox = obj.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    if bbox:
        obj = obj.crop(bbox)
    max_w, max_h = size * spec["fill"], face + size * 0.03 - size * 0.04
    scale = min(max_w / obj.width, max_h / obj.height)
    obj = resize_premultiplied(obj, (max(1, round(obj.width * scale)), max(1, round(obj.height * scale))))
    obj = grade(obj, target)
    icon = Image.fromarray(np.clip(slab, 0, 255).astype(np.uint8), "RGBA")
    # A soft contact shadow where the figure meets the top face.
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    w = obj.width * 0.75
    ImageDraw.Draw(shadow).ellipse(
        (size / 2 - w / 2, face - size * 0.025, size / 2 + w / 2, face + size * 0.035), fill=(0, 0, 0, 110))
    icon.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(size / 60)))
    bottom = round(face + size * 0.03)
    icon.alpha_composite(obj, ((size - obj.width) // 2, bottom - obj.height))
    return icon


LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)


def tone_ramp(folder: str) -> tuple[np.ndarray, np.ndarray]:
    """The tones of a folder whose icons are all one metal (laws, institutions).

    Returns (the 0..100th percentiles of its opaque pixels' luminance, a
    256 x 3 table of the median colour at each luminance). Luminances too rare
    to measure take the colour interpolated from their neighbours.
    """
    samples = []
    for f in sorted((vanilla_icons_dir() / folder).glob("*.dds")):
        try:
            a = np.asarray(load_rgba(f), dtype=np.float32)
        except Exception:
            continue
        px = a[..., :3][a[..., 3] > 200]
        samples.append(px[::max(1, len(px) // 4000)])
    if not samples:
        raise SystemExit(f"no .dds in {vanilla_icons_dir() / folder}: check VIC3_BASE_GAME")
    rgb = np.concatenate(samples)
    lum = rgb @ LUMA
    idx = np.clip(np.rint(lum), 0, 255).astype(int)
    lut = np.full((256, 3), np.nan, dtype=np.float32)
    for v in range(256):
        sel = rgb[idx == v]
        if len(sel) >= 20:
            lut[v] = np.median(sel, axis=0)
    known = np.nonzero(~np.isnan(lut[:, 0]))[0]
    for ch in range(3):
        lut[:, ch] = np.interp(np.arange(256), known, lut[known, ch])
    lut = np.stack([np.convolve(np.pad(lut[:, ch], 3, mode="edge"), np.ones(7) / 7, "valid")
                    for ch in range(3)], axis=1)
    return np.percentile(lum, np.arange(101)), lut


def compose_tinted(raw: Image.Image, spec: dict, ramp) -> Image.Image:
    """A painted object recast in its folder's single metal.

    Vanilla's law and institution icons are painted objects in one tan-bronze
    palette. The cutout's luminance is matched to the folder's distribution
    (percentile for percentile), then each pixel takes the folder's colour
    at that luminance, so shadows, highlights and brush strokes survive while
    every hue goes.
    """
    quantiles, lut = ramp
    obj = fit_square(cut_out(raw), spec["size"], spec["fill"])
    a = np.asarray(obj, dtype=np.float32)
    lum = a[..., :3] @ LUMA
    opaque = a[..., 3] > 200
    if opaque.sum() < 50:
        return obj
    ours = np.percentile(lum[opaque], np.arange(101)) + np.arange(101) * 1e-3  # strictly increasing
    matched = np.interp(np.interp(lum, ours, np.arange(101)), np.arange(101), quantiles)
    rgb = lut[np.clip(np.rint(matched), 0, 255).astype(int)]
    out = Image.fromarray(np.clip(np.dstack([rgb, a[..., 3]]), 0, 255).astype(np.uint8), "RGBA")
    return drop_shadow(out, max(1, spec["size"] // 128), spec["size"] / 100, 0.35)


class Composer:
    """Compose raw renders per category, caching each category's vanilla template."""

    def __init__(self) -> None:
        self._tmpl: dict[str, tuple] = {}
        self._target: dict[str, tuple] = {}

    def compose(self, raw: Image.Image, cat: str, spec: dict) -> Image.Image:
        mode = spec["mode"]
        if mode in ("framed", "medallion", "emboss_medallion") and cat not in self._tmpl:
            self._tmpl[cat] = vanilla_template(spec["folder"], spec["size"])
        if mode == "plinth" and cat not in self._tmpl:
            self._tmpl[cat] = plinth_template(spec["folder"], spec["size"])
        if mode in ("cutout", "medallion", "plinth") and cat not in self._target:
            # A medallion's opaque pixels are mostly its dark disc: grade the
            # object against a folder of bare objects instead.
            self._target[cat] = category_grade_target(spec.get("grade_folder", spec["folder"]))
        if mode == "tinted" and cat not in self._tmpl:
            self._tmpl[cat] = tone_ramp(spec.get("ramp_folder", spec["folder"]))
        raw = raw.convert("RGB")
        if mode == "tinted":
            return compose_tinted(raw, spec, self._tmpl[cat])
        if mode == "cutout":
            return compose_cutout(raw, spec, self._target[cat])
        if mode == "framed":
            return compose_framed(raw, spec, self._tmpl[cat])
        if mode == "emboss":
            return embossed(raw, spec, spec["size"])
        if mode == "plinth":
            return compose_plinth(raw, spec, self._tmpl[cat], self._target[cat])
        if mode == "emboss_medallion":
            return compose_medallion(raw, spec, self._tmpl[cat], None,
                                     obj=embossed(raw, dict(spec, fill=0.95), spec["size"]))
        return compose_medallion(raw, spec, self._tmpl[cat], self._target[cat])


def review_sheet(rows: list, folder: str, out: Path) -> None:
    """Row per entity: [current icon | 3 vanilla neighbours || candidates], at native size.

    rows: (label, current icon path, [(caption, candidate image or path), ...]).
    The neighbours are drawn from the vanilla folder at random (fixed seed).
    """
    pool = sorted((vanilla_icons_dir() / folder).glob("*.dds"))
    cell = 270
    ncols = 4 + max((len(c) for *_, c in rows), default=0)
    sheet = Image.new("RGBA", (240 + cell * ncols, cell * len(rows)), (33, 34, 40, 255))
    d = ImageDraw.Draw(sheet)
    rng = np.random.default_rng(7)
    for i, (label, current, candidates) in enumerate(rows):
        y = i * cell
        d.text((6, y + 8), label, fill=(235, 235, 235, 255))
        d.text((6, y + cell - 40), "current | vanilla x3 ||\ncandidates (native px)", fill=(150, 150, 150, 255))
        others = [p for p in pool if p.name != Path(current).name]
        tiles = [("", current)] + [("", others[j]) for j in rng.choice(len(others), 3, replace=False)]
        tiles += list(candidates)
        for j, (caption, src) in enumerate(tiles):
            try:
                im = src if isinstance(src, Image.Image) else load_rgba(Path(src))
            except Exception:
                continue
            x = 240 + j * cell + (cell - im.width) // 2
            sheet.alpha_composite(im.convert("RGBA"), (x, y + (cell - im.height) // 2))
            if caption:
                d.text((240 + j * cell + 6, y + 6), caption, fill=(220, 200, 140, 255))
        d.line([(240 + 4 * cell - 3, y + 10), (240 + 4 * cell - 3, y + cell - 10)],
               fill=(200, 170, 90, 255), width=2)
    sheet.save(out)
    print(f"wrote {out}")
