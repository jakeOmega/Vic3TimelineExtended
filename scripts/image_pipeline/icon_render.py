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
                                (grade="spread": graded at two percentiles to the folder's objects)
               emboss           FLUX silhouette -> the PM pipeline's metallic emboss
               emboss_medallion that emboss on the disc and ring
               plinth           cutout standing on the slab lifted from vanilla
               tinted           cutout recast in its folder's one metal (laws, institutions)
               card             dark pictogram on a blank card lifted from vanilla (IG and
                                character traits; `recolor` turns it to a colour vanilla lacks)
               strip            wide painted scene centred on an institution's 3500x220 strip
               backed           cutout over a shared disc: the category's own `backdrop`, rendered
                                like an icon (Space Race journal entries) or drawn (draw_disc; the
                                UN's agencies and topics)
  tint() / apply_marks() / flag_layout()
                  Derived icons: another entry's icon, greyed or faded, with vanilla's
                  marks, a drawn star or a registry part drawn over it, or laid out as
                  a bare flag (the UN's membership icons, badged topics, vacant seat).
  strip_sheet()   The strip category's review sheet: each strip as the panel shows it.
  review_sheet()  Row per entity: [current icon | 3 vanilla neighbours || candidates].
  panel_preview() Journal icons as the panel draws them: 100 px in the round frame, and 40 px.
  backdrop_sheet() The backed category's backdrop candidates, each under a few sample icons.

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


SPREAD_PCT = (50, 90)
DISC_DIST = 45  # an object pixel is at least this far (RGB) from its disc's colour


def _object_mask(rgb: np.ndarray, disc) -> np.ndarray:
    return np.linalg.norm(rgb - np.mean(np.asarray(disc, dtype=np.float32), axis=0), axis=-1) > DISC_DIST


def medallion_object_target(folder: str, disc) -> dict:
    """The 50th and 90th percentiles of saturation and value of vanilla's objects on their disc.

    Object pixels are those inside the ring that stand apart from the disc
    colour. A median alone missed vanilla decrees' highlights: graded to it,
    ours matched in the middle but topped out at a value of 0.71 against 0.88.
    """
    s, v = [], []
    for f in sorted((vanilla_icons_dir() / folder).glob("*.dds")):
        try:
            im = load_rgba(f)
        except Exception:
            continue
        n = im.size[0]
        yy, xx = np.mgrid[0:n, 0:n]
        inside = np.hypot(xx - (n - 1) / 2, yy - (n - 1) / 2) < 0.4 * n
        m = inside & _object_mask(np.asarray(im, dtype=np.float32)[..., :3], disc)
        hsv = np.asarray(im.convert("RGB").convert("HSV"), dtype=np.float32) / 255
        s.append(hsv[..., 1][m])
        v.append(hsv[..., 2][m])
    if not s:
        raise SystemExit(f"no .dds in {vanilla_icons_dir() / folder}: check VIC3_BASE_GAME")
    return {1: np.percentile(np.concatenate(s), SPREAD_PCT), 2: np.percentile(np.concatenate(v), SPREAD_PCT)}


def grade_spread(im: Image.Image, target: dict, disc=None, strength: float = 0.8,
                 max_gain: float = 1.6) -> Image.Image:
    """Pull the 50th and 90th percentiles of saturation and value toward `target`.

    Each channel goes through a piecewise-linear curve from (0, 0) through the
    two moved percentiles to (1, 1), so contrast can grow as well as the
    middle. With a `disc`, percentiles are taken over the pixels that
    `medallion_object_target` would count, so both sides are measured alike;
    without one, over every opaque pixel. Gains are capped: a near-grey
    object's saturation is mostly noise hue.
    """
    a = np.asarray(im)
    alpha = a[..., 3]
    m = alpha > 200
    if disc is not None:
        m &= _object_mask(a[..., :3].astype(np.float32), disc)
    if m.sum() < 50:
        return im
    hsv = np.asarray(im.convert("RGB").convert("HSV"), dtype=np.float32) / 255
    for ch, t in target.items():
        own = np.percentile(hsv[..., ch][m], SPREAD_PCT)
        want = own * np.clip((t / np.maximum(own, 1e-3)) ** strength, 1 / max_gain, max_gain)
        xp, fp = [0.0], [0.0]
        for o, w in zip(own, np.minimum(want, 0.995)):
            if o > xp[-1] + 1e-3 and w > fp[-1] and o < 0.999:
                xp.append(float(o))
                fp.append(float(w))
        hsv[..., ch] = np.interp(hsv[..., ch], xp + [1.0], fp + [1.0])
    rgb = Image.fromarray(np.clip(hsv * 255 + 0.5, 0, 255).astype(np.uint8), "HSV").convert("RGB")
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


def cut(raw: Image.Image, spec: dict) -> Image.Image:
    """cut_out, then with `solid` in the spec, the holes it left inside the object filled back in.

    rembg can take a flat panel inside an object for background: it cut the
    front boards out of the sanctions crate, leaving the disc showing
    through. `solid` makes every transparent region the object encloses
    opaque again, in the raw render's colours. Only for objects with no
    real holes: an anchor's ring or a wreath's gaps would be filled too.
    """
    obj = cut_out(raw)
    if not spec.get("solid"):
        return obj
    from scipy.ndimage import binary_fill_holes
    alpha = np.asarray(obj.getchannel("A"))
    holes = binary_fill_holes(alpha > 128) & (alpha <= 128)
    out = np.asarray(obj.convert("RGBA")).copy()
    out[holes, :3] = np.asarray(raw.convert("RGB"))[holes]
    out[holes, 3] = 255
    return Image.fromarray(out, "RGBA")


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
    icon = fit_square(cut(raw, spec), spec["size"], spec["fill"])
    icon = grade(icon, target, spec.get("grade_strength", 0.7))
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


BACKDROP_RIM = (150, 165, 195)  # thin steel-blue edge so a dark disc reads on the dark panel


def compose_backdrop(raw: Image.Image, spec: dict) -> Image.Image:
    """A full-bleed painted scene as the soft-edged disc the `backed` layout sits on.

    The journal panel draws its icon at 100 px over a 120 px round frame
    whose gold ring starts at 0.9 of the icon's width, so the disc is
    `disc_fill` of the canvas (0.86 by default), just inside it; a square
    would cover the ring and poke out of the frame. A gentle
    vignette darkens the rim, which keeps contrast for the object in front,
    and the edge gets a thin light line. The scene is not graded toward the
    folder's saturation and value: a night sky lifted to vanilla's brightness
    stops being one.
    """
    size = spec["size"]
    disc_fill = spec.get("disc_fill", 0.86)
    scene = np.asarray(resize_premultiplied(raw.convert("RGBA"), (size, size)), dtype=np.float32)
    ss = 4
    pad = size * ss * (1 - disc_fill) / 2
    mask = Image.new("L", (size * ss, size * ss), 0)
    ImageDraw.Draw(mask).ellipse([pad, pad, size * ss - 1 - pad, size * ss - 1 - pad], fill=255)
    alpha = np.asarray(mask.resize((size, size), Image.LANCZOS), dtype=np.float32) / 255
    c = (size - 1) / 2
    yy, xx = np.mgrid[0:size, 0:size]
    radius = size * disc_fill / 2
    r_px = np.hypot(xx - c, yy - c)
    scene[..., :3] *= (1 - 0.35 * np.clip((r_px / radius - 0.55) / 0.45, 0, 1) ** 2)[..., None]
    rim_w = max(1.5, size / 75)
    rim = np.clip(1 - np.abs((radius - r_px) - rim_w / 2) / (rim_w / 2), 0, 1) * spec.get("rim", 0.5)
    scene[..., :3] = scene[..., :3] * (1 - rim[..., None]) + np.array(BACKDROP_RIM, dtype=np.float32) * rim[..., None]
    scene[..., 3] = alpha * 255
    return Image.fromarray(np.clip(scene, 0, 255).astype(np.uint8), "RGBA")


def compose_backed(raw: Image.Image, spec: dict, target, backdrop: Image.Image) -> Image.Image:
    """The graded cut-out subject, smaller than a plain cutout, over the shared disc."""
    size = spec["size"]
    subject = grade(fit_square(cut(raw, spec), size, spec["fill"]), target, spec.get("grade_strength", 0.7))
    icon = backdrop.copy()
    icon.alpha_composite(drop_shadow(subject, max(1, size // 100), size / 90, 0.45))
    return icon


def draw_disc(size: int, drawn: dict) -> Image.Image:
    """A flat enamel disc under a metal rim, drawn rather than rendered (the UN's agency and topic icons).

    A painted FLUX disc varies from render to render; a set that has to read
    as one family at 36 px wants the same disc under every symbol. `drawn`
    gives the enamel's `centre` and `edge` colours (a radial gradient lit from
    a little above centre), the rim's `rim_light` (top) and `rim_dark`
    (bottom) colours, and optionally `fill` (the disc's share of the side,
    0.96) and `rim` (the rim's width as a share of the side, 0.07). A thin
    dark line outside the rim keeps a pale rim readable on a pale panel.
    """
    fill, rim_w = drawn.get("fill", 0.96), drawn.get("rim", 0.07) * size
    c = (size - 1) / 2
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.hypot(xx - c, yy - c)
    radius = size * fill / 2
    # Enamel: a radial gradient whose light spot sits a little above centre.
    lit = np.hypot(xx - c, yy - c + size * 0.12) / radius
    t = np.clip(lit / 1.1, 0, 1)[..., None]
    rgb = np.array(drawn["centre"], np.float32) * (1 - t) + np.array(drawn["edge"], np.float32) * t
    # Rim: a vertical metal gradient, with a soft shadow cast inward onto the enamel.
    ring_in = radius - rim_w
    shade = np.clip((ring_in - r) / (size * 0.05), 0, 1)[..., None]
    rgb *= 0.72 + 0.28 * shade
    v = np.clip((yy - (c - radius)) / (2 * radius), 0, 1)[..., None]
    metal = np.array(drawn["rim_light"], np.float32) * (1 - v) + np.array(drawn["rim_dark"], np.float32) * v
    # A bright bevel line along the rim's middle catches the light.
    bevel = np.clip(1 - np.abs(r - (ring_in + rim_w * 0.45)) / (rim_w * 0.25), 0, 1)[..., None] * (1 - v) * 0.35
    metal = metal * (1 - bevel) + 255 * bevel
    in_ring = np.clip(r - ring_in + 0.5, 0, 1)[..., None]
    rgb = rgb * (1 - in_ring) + metal * in_ring
    edge = np.clip(r - (radius - 1.5) + 0.5, 0, 1)[..., None]
    rgb = rgb * (1 - edge * 0.75) + np.array((25, 20, 15), np.float32) * edge * 0.75
    alpha = np.clip(radius - r + 0.5, 0, 1) * 255
    return Image.fromarray(np.clip(np.dstack([rgb, alpha]), 0, 255).astype(np.uint8), "RGBA")


# ── derived icons: tints, marks and layouts over an accepted icon ────────
#
# A derived registry entry has no render of its own: it takes another entry's
# composed icon ("from"), optionally tints it and lays it out differently,
# then draws marks over it (vanilla's own check and cross, a drawn star, or a
# registry part such as the UN's scroll badge). The UN's membership icons are
# one emblem under seven marks; its convention topics are the agency icon
# under a scroll.

# Metal tints: the icon's light and shade mapped onto a metal's ramp (dark,
# mid, light), so one rendered emblem can be stone, gilded, silver or iron and
# keep its exact shape (the banking phases' gilded bank, the covert shields).
METAL_RAMPS = {
    "gold": ((62, 38, 8), (205, 150, 48), (255, 238, 165)),
    "silver": ((30, 34, 42), (124, 132, 146), (222, 228, 238)),
    "iron": ((26, 24, 22), (96, 92, 86), (178, 172, 162)),
}
TINTS = ("grey", "faint", "moss") + tuple(METAL_RAMPS)


def _ramp(lum: np.ndarray, ramp) -> np.ndarray:
    """lum (0-255) through a three-stop colour ramp."""
    t = np.clip(lum / 255, 0, 1)
    dark, mid, light = (np.array(c, np.float32) for c in ramp)
    lo = dark + (mid - dark) * np.clip(t * 2, 0, 1)
    return np.where(t < 0.5, lo, mid + (light - mid) * np.clip(t * 2 - 1, 0, 1))


def tint(im: Image.Image, how: str | None) -> Image.Image:
    """`grey`: the icon as greyed stone. `faint`: grey, and half transparent.
    `gold`, `silver`, `iron`: the icon in that metal. `moss`: weathered, its
    shadows gone green."""
    if not how:
        return im
    if how not in TINTS:
        raise ValueError(f"unknown tint {how!r}")
    a = np.asarray(im.convert("RGBA"), dtype=np.float32)
    lum = (a[..., :3] @ LUMA)[..., None]
    if how in METAL_RAMPS:
        # Stretch the icon's own range first, so a pale stone still reaches the metal's darks.
        opaque = a[..., 3] > 128
        lo, hi = (np.percentile(lum[opaque], (2, 98)) if opaque.any() else (0, 255))
        a[..., :3] = _ramp((lum - lo) / max(hi - lo, 1) * 255, METAL_RAMPS[how])
    elif how == "moss":
        # Aged stone: greyer and darker, the shadows and recesses gone moss
        # green (patches of noise read as camouflage paint).
        stone = a[..., :3] * 0.55 + lum * 0.3
        green = lum * np.array((0.5, 0.82, 0.32), np.float32) + np.array((10, 26, 4), np.float32)
        w = np.clip((170 - lum) / 150, 0, 0.85)
        a[..., :3] = stone * (1 - w) + green * w
    else:
        lum = lum * 0.85 + 12
        a[..., :3] = lum * np.array((1.0, 0.97, 0.92), np.float32)
        if how == "faint":
            a[..., 3] *= 0.45
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def place(im: Image.Image, scale: float, at: tuple[float, float]) -> Image.Image:
    """`im` shrunk to `scale` of its side and centred at `at` (shares) on a clear canvas of its size."""
    w, h = im.size
    small = resize_premultiplied(im, (max(1, round(w * scale)), max(1, round(h * scale))))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    paste(out, small, round(at[0] * w - small.width / 2), round(at[1] * h - small.height / 2))
    return out


def turn(im: Image.Image, deg: float) -> Image.Image:
    """`im` rotated `deg` about its centre (counter-clockwise), refitted to its own size (a warhead laid pointing right)."""
    rot = im.convert("RGBA").rotate(deg, resample=Image.BICUBIC, expand=True)
    bbox = rot.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    if bbox:
        rot = rot.crop(bbox)
    k = min(im.width / rot.width, im.height / rot.height, 1.0) * 0.96
    rot = resize_premultiplied(rot, (max(1, round(rot.width * k)), max(1, round(rot.height * k))))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    paste(out, rot, (im.width - rot.width) // 2, (im.height - rot.height) // 2)
    return out


def paste(canvas: Image.Image, im: Image.Image, x: int, y: int) -> None:
    """alpha_composite `im` at (x, y), clipped to `canvas` (Pillow refuses a negative corner)."""
    l, t = max(0, -x), max(0, -y)
    r, b = min(im.width, canvas.width - x), min(im.height, canvas.height - y)
    if r > l and b > t:
        canvas.alpha_composite(im.crop((l, t, r, b)), (x + l, y + t))


def _crack_path(w: int, h: int, seed: int = 3) -> list[tuple[float, float]]:
    """A jagged line from the top edge to the bottom, a little off centre."""
    rng = np.random.default_rng(seed)
    n = 7
    ys = np.linspace(0, h, n)
    xs = w * (0.54 + np.cumsum(rng.uniform(-0.09, 0.09, n)) * 0.8)
    xs[0] = w * 0.58
    return list(zip(xs.tolist(), ys.tolist()))


def damage(im: Image.Image, how: str | None, tilt_deg: float = 0) -> Image.Image:
    """`crack`: a dark jagged crack down the object. `split`: the object broken
    in two along that line, the halves leaning apart. FLUX will not break
    things on request, so the break is drawn. `tilt_deg` leans the whole
    object (a monument being pulled over)."""
    if how not in (None, "crack", "split"):
        raise ValueError(f"unknown damage {how!r}")
    im = im.convert("RGBA")
    if how:
        w, h = im.size
        ss = 4
        path = [(x * ss, y * ss) for x, y in _crack_path(w, h)]
        if how == "crack":
            line = Image.new("L", (w * ss, h * ss), 0)
            ImageDraw.Draw(line).line(path, fill=255, width=max(2, w * ss // 26), joint="curve")
            line = line.resize((w, h), Image.LANCZOS)
            glint = Image.new("L", (w * ss, h * ss), 0)
            ImageDraw.Draw(glint).line([(x + ss * 2, y) for x, y in path], fill=255, width=max(1, w * ss // 90))
            glint = glint.resize((w, h), Image.LANCZOS)
            a = np.asarray(im, np.float32).copy()
            k = (np.asarray(line, np.float32) / 255)[..., None]
            g = (np.asarray(glint, np.float32) / 255)[..., None] * 0.5
            a[..., :3] = a[..., :3] * (1 - k) + np.array((18, 14, 12), np.float32) * k
            a[..., :3] = a[..., :3] * (1 - g) + 235 * g
            im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
        else:
            # Shrunk first, so the halves leaning apart stay on the canvas.
            im = place(im, 0.84, (0.5, 0.54))
            left = Image.new("L", (w * ss, h * ss), 0)
            ImageDraw.Draw(left).polygon([(0, 0)] + path + [(0, h * ss)], fill=255)
            left = np.asarray(left.resize((w, h), Image.LANCZOS), np.float32) / 255
            a = np.asarray(im, np.float32)
            halves = []
            for k in (left, 1 - left):
                part = a.copy()
                part[..., 3] *= k
                halves.append(Image.fromarray(part.astype(np.uint8), "RGBA"))
            out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            gap = w * 0.035
            for part, sign in zip(halves, (-1, 1)):
                part = part.rotate(-sign * 5, resample=Image.BICUBIC, center=(w * 0.56, h * 0.96))
                paste(out, part, round(sign * gap), 0)
            im = out
    if tilt_deg:
        im = im.rotate(tilt_deg, resample=Image.BICUBIC, center=(im.width / 2, im.height * 0.92))
    return im


def star(size: int, fill=(250, 214, 110), shade=(190, 130, 30)) -> Image.Image:
    """A five-pointed gold star with a dark outline, `size` px square."""
    ss = 4
    n = size * ss
    c = n / 2
    pts = []
    for i in range(10):
        rad = (n * 0.48) if i % 2 == 0 else (n * 0.2)
        ang = -np.pi / 2 + i * np.pi / 5
        pts.append((c + rad * np.cos(ang), c + n * 0.03 + rad * np.sin(ang)))
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    t = np.linspace(0, 1, n, dtype=np.float32)[:, None, None]
    rgb = np.array(fill, np.float32) * (1 - t) + np.array(shade, np.float32) * t
    im = Image.fromarray(np.dstack([np.broadcast_to(rgb, (n, n, 3)), np.asarray(mask)]).astype(np.uint8), "RGBA")
    return resize_premultiplied(outlined(im, ss * max(1, size // 40)), (size, size))


def pause(size: int, bars=(250, 190, 70), badge=(38, 36, 42)) -> Image.Image:
    """Amber pause bars on a small dark badge, `size` px square.

    Vanilla's paused.dds is gold bars with no ground, which vanish into a
    gold emblem at 32 px and read as ingots.
    """
    ss = 4
    n = size * ss
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([n * 0.02, n * 0.02, n * 0.98, n * 0.98], fill=badge + (255,))
    d.ellipse([n * 0.02, n * 0.02, n * 0.98, n * 0.98], outline=(15, 13, 12, 255), width=max(1, n // 30))
    for x0 in (0.29, 0.56):
        d.rounded_rectangle([n * x0, n * 0.26, n * (x0 + 0.15), n * 0.74], radius=n * 0.03, fill=bars + (255,))
    return resize_premultiplied(im, (size, size))


# The drawn marks' colours, as (top, bottom) of a vertical gradient.
MARK_COLOURS = {
    "red": ((235, 80, 62), (150, 28, 22)),
    "green": ((130, 222, 95), (38, 125, 40)),
    "blue": ((120, 182, 250), (35, 85, 178)),
    "yellow": ((252, 230, 95), (196, 150, 25)),
    "amber": ((250, 190, 70), (186, 112, 22)),
    "orange": ((250, 150, 60), (186, 78, 18)),
    "white": ((250, 248, 242), (188, 184, 176)),
    "gold": ((250, 214, 110), (190, 130, 30)),
}


def _gradient_fill(mask: Image.Image, colour: str) -> Image.Image:
    top, bottom = MARK_COLOURS[colour]
    n_h, n_w = mask.height, mask.width
    t = np.linspace(0, 1, n_h, dtype=np.float32)[:, None, None]
    rgb = np.array(top, np.float32) * (1 - t) + np.array(bottom, np.float32) * t
    return Image.fromarray(np.dstack([np.broadcast_to(rgb, (n_h, n_w, 3)), np.asarray(mask)]).astype(np.uint8),
                           "RGBA")


def _shape_mark(size: int, polys: list, colour: str, rects: list = ()) -> Image.Image:
    """Polygons and rounded rectangles in shares of the side, filled with `colour`, outlined."""
    ss = 4
    n = size * ss
    mask = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(mask)
    for poly in polys:
        d.polygon([(x * n, y * n) for x, y in poly], fill=255)
    for x0, y0, x1, y1 in rects:
        d.rounded_rectangle([x0 * n, y0 * n, x1 * n, y1 * n], radius=(y1 - y0) * n * 0.3, fill=255)
    return resize_premultiplied(outlined(_gradient_fill(mask, colour), ss * max(1, size // 40)), (size, size))


def arrow(size: int, direction: str = "down", colour: str = "red", double: bool = False) -> Image.Image:
    """A thick arrow, up or down, in one of MARK_COLOURS; `double` stacks two heads (vanilla's upup/downdown)."""
    if double:
        polys = [[(0.1, 0.3), (0.9, 0.3), (0.5, 0.64)], [(0.1, 0.58), (0.9, 0.58), (0.5, 0.97)],
                 [(0.35, 0.03), (0.65, 0.03), (0.65, 0.34), (0.35, 0.34)]]
    else:
        polys = [[(0.34, 0.04), (0.66, 0.04), (0.66, 0.5), (0.92, 0.5), (0.5, 0.96), (0.08, 0.5), (0.34, 0.5)]]
    if direction in ("up", "left"):
        polys = [[(x, 1 - y) for x, y in poly] for poly in polys]
    if direction in ("left", "right"):
        polys = [[(y, x) for x, y in poly] for poly in polys]
    return _shape_mark(size, polys, colour)


def arrow_down(size: int) -> Image.Image:
    """A thick red arrow pointing down, `size` px square: loss, as vanilla's alerts draw it.

    Vanilla's generic trend_down.dds is an orange-gold triangle, which merges
    with a gold object under it.
    """
    return arrow(size, "down", "red")


def bar(size: int, colour: str = "white") -> Image.Image:
    """A thick level bar across the box: steady, held."""
    return _shape_mark(size, [], colour, rects=[(0.05, 0.37, 0.95, 0.63)])


def chevrons(size: int, count: int, colour: str = "gold", patch: bool = False) -> Image.Image:
    """`count` rank chevrons stacked, pointing up, centred in the box; `patch`
    sets them on a dark cloth patch, as rank insignia are, so they read over a
    ground of their own colour."""
    if patch:
        ss = 4
        n = size * ss
        im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([n * 0.08, n * 0.02, n * 0.92, n * 0.98], radius=n * 0.16,
                                             fill=(34, 38, 52, 255), outline=(12, 12, 16, 255), width=max(3, n // 30))
        im = resize_premultiplied(im, (size, size))
        inner = chevrons(round(size * 0.8), count, colour)
        im.alpha_composite(inner, ((size - inner.width) // 2, (size - inner.height) // 2))
        return im
    t, rise = 0.14, 0.17
    step = min(0.22, (0.9 - rise - t) / max(count - 1, 1))   # inside the box, outline and all
    total = rise + t + (count - 1) * step
    y0 = (1 - total) / 2
    polys = []
    for i in range(count):
        y = y0 + i * step
        polys.append([(0.06, y + rise), (0.5, y), (0.94, y + rise), (0.94, y + rise + t), (0.5, y + t),
                      (0.06, y + rise + t)])
    return _shape_mark(size, polys, colour)


def barrier(size: int) -> Image.Image:
    """A red-and-white striped barrier bar: the way is shut."""
    ss = 4
    n = size * ss
    y0, y1 = 0.34 * n, 0.66 * n
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0.04 * n, y0, 0.96 * n, y1], radius=(y1 - y0) * 0.25, fill=255)
    im = _gradient_fill(mask, "red")
    stripes = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(stripes)
    w = n * 0.11
    for k in range(-2, 8):
        x = n * 0.08 + k * 2 * w
        d.polygon([(x, y1), (x + w, y1), (x + w + (y1 - y0), y0), (x + (y1 - y0), y0)], fill=255)
    white = _gradient_fill(Image.fromarray(np.minimum(np.asarray(stripes), np.asarray(mask))), "white")
    im.alpha_composite(white)
    return resize_premultiplied(outlined(im, ss * max(1, size // 40)), (size, size))


def bubble(size: int, rim: str = "white", cracked: bool = False) -> Image.Image:
    """A soap bubble `size` px across: a clear film with a coloured rim and a
    bright highlight. Drawn, since a render's transparent film would not
    survive the cut-out. `cracked` draws a split across it, about to burst."""
    ss = 4
    n = size * ss
    c = (n - 1) / 2
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    r = np.hypot(xx - c, yy - c) / (n * 0.48)
    inside = np.clip((1 - r) * n * 0.02, 0, 1)
    rim_rgb = np.array(MARK_COLOURS[rim][0], np.float32)
    # The film: faintly iridescent, clearer in the middle.
    ang = np.arctan2(yy - c, xx - c)
    film = np.stack([205 + 50 * np.cos(ang), 215 + 40 * np.cos(ang + 2.1), 235 + 20 * np.cos(ang + 4.2)], -1)
    film_a = 0.1 + 0.45 * np.clip(r, 0, 1) ** 4
    # The rim carries the band's colour, so it has to be thick enough to read at 32 px.
    ring = np.clip((1 - np.abs(r - 0.9) / 0.1) * 1.6, 0, 1)
    rgb = film * (1 - ring[..., None]) + rim_rgb * ring[..., None]
    a = np.maximum(film_a, ring * 0.95) * inside
    # The outline keeps the edge on any ground.
    edge = np.clip(1 - np.abs(r - 1.0) / 0.025, 0, 1) * 0.7
    rgb = rgb * (1 - edge[..., None]) + np.array((20, 16, 14), np.float32) * edge[..., None]
    a = np.maximum(a, edge)
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.clip(a * 255, 0, 255)]).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(im)
    d.arc([n * 0.17, n * 0.17, n * 0.83, n * 0.83], 200, 250, fill=(255, 255, 255, 230), width=max(2, n // 18))
    d.ellipse([n * 0.66, n * 0.26, n * 0.74, n * 0.34], fill=(255, 255, 255, 200))
    if cracked:
        pts = [(0.3, 0.12), (0.42, 0.3), (0.36, 0.42), (0.52, 0.56), (0.46, 0.7), (0.62, 0.88)]
        d.line([(x * n, y * n) for x, y in pts], fill=(20, 16, 14, 255), width=max(3, n // 22), joint="curve")
        d.line([(x * n + n * 0.012, y * n) for x, y in pts], fill=tuple(rim_rgb.astype(int).tolist()) + (255,),
               width=max(1, n // 50))
    return resize_premultiplied(im, (size, size))


def thermometer(size: int, level: float, burst: bool = False) -> Image.Image:
    """A glass thermometer `size` px tall, its red column `level` (0-1) up the
    tube. `burst`: the column through the top and the glass cracked. Drawn, so
    the seven warming tiers differ only by the column."""
    ss = 4
    n = size * ss
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    dark, glass, red = (32, 26, 24, 255), (222, 230, 238, 255), (232, 52, 40, 255)
    tx0, tx1, ty0, ty1 = 0.39 * n, 0.61 * n, 0.07 * n, 0.74 * n
    bc, br = (0.5 * n, 0.8 * n), 0.155 * n
    ow = max(3, n // 26)
    d.rounded_rectangle([tx0 - ow, ty0 - ow, tx1 + ow, ty1], radius=(tx1 - tx0) / 2 + ow, fill=dark)
    d.ellipse([bc[0] - br - ow, bc[1] - br - ow, bc[0] + br + ow, bc[1] + br + ow], fill=dark)
    d.rounded_rectangle([tx0, ty0, tx1, ty1], radius=(tx1 - tx0) / 2, fill=glass)
    d.ellipse([bc[0] - br, bc[1] - br, bc[0] + br, bc[1] + br], fill=red)
    # The column: from the bulb up to `level` of the tube.
    cx0, cx1 = 0.455 * n, 0.545 * n
    top_y = ty1 - (ty1 - ty0 - 0.03 * n) * min(max(level, 0), 1)
    if burst:
        top_y = ty0
    d.rectangle([cx0, top_y, cx1, bc[1]], fill=red)
    d.ellipse([cx0, top_y - (cx1 - cx0) / 2, cx1, top_y + (cx1 - cx0) / 2], fill=red)
    d.ellipse([bc[0] - br * 0.45, bc[1] - br * 0.6, bc[0] - br * 0.05, bc[1] - br * 0.2], fill=(255, 150, 130, 255))
    # Ticks, and a highlight down the glass.
    for k in range(1, 6):
        y = ty1 - (ty1 - ty0) * k / 6
        d.line([(tx1 - 0.05 * n, y), (tx1 - 0.005 * n, y)], fill=(90, 90, 96, 255), width=max(2, n // 70))
    d.line([(tx0 + 0.035 * n, ty0 + 0.06 * n), (tx0 + 0.035 * n, ty1 - 0.04 * n)], fill=(255, 255, 255, 235),
           width=max(2, n // 40))
    if burst:
        # Red bursting out of the top, and cracks through the glass.
        cx, cy = 0.5 * n, ty0 + 0.02 * n
        spikes = []
        for i in range(16):
            ang = i * 2 * np.pi / 16
            rad = (0.17 if i % 2 == 0 else 0.07) * n
            spikes.append((cx + rad * np.cos(ang) * 1.3, cy + rad * np.sin(ang) * 0.9))
        d.polygon(spikes, fill=(250, 190, 60, 255), outline=dark, width=max(3, n // 50))
        d.ellipse([cx - 0.06 * n, cy - 0.05 * n, cx + 0.06 * n, cy + 0.05 * n], fill=red)
        for pts in (((0.4, 0.2), (0.47, 0.28), (0.43, 0.36), (0.5, 0.44)), ((0.6, 0.3), (0.53, 0.38), (0.58, 0.46))):
            d.line([(x * n, y * n) for x, y in pts], fill=dark, width=max(2, n // 45), joint="curve")
    return resize_premultiplied(im, (size, size))


def disc(size: int, colour: str = "red") -> Image.Image:
    """A round enamel badge in one of MARK_COLOURS, lit from above: an alert's ground, or a lamp."""
    ss = 4
    n = size * ss
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).ellipse([n * 0.04, n * 0.04, n * 0.96, n * 0.96], fill=255)
    im = _gradient_fill(mask, colour)
    glint = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    ImageDraw.Draw(glint).ellipse([n * 0.26, n * 0.14, n * 0.5, n * 0.32], fill=(255, 255, 255, 120))
    im.alpha_composite(glint.filter(ImageFilter.GaussianBlur(n * 0.02)))
    return resize_premultiplied(outlined(im, ss * max(1, size // 40)), (size, size))


def shield_outline(size: int, colour: str = "blue") -> Image.Image:
    """A heater shield's thick outline, open inside, so what it guards shows through."""
    ss = 4
    n = size * ss
    pts = [(0.1, 0.06), (0.9, 0.06), (0.9, 0.46), (0.78, 0.72), (0.5, 0.96), (0.22, 0.72), (0.1, 0.46)]
    outer = Image.new("L", (n, n), 0)
    ImageDraw.Draw(outer).polygon([(x * n, y * n) for x, y in pts], fill=255)
    inner = outer.filter(ImageFilter.MinFilter(2 * (n // 14) + 1))
    ring = Image.fromarray(np.asarray(outer) - np.minimum(np.asarray(outer), np.asarray(inner)))
    return resize_premultiplied(outlined(_gradient_fill(ring, colour), ss * max(1, size // 40)), (size, size))


def dome(size: int) -> Image.Image:
    """A clear pale-blue half dome with a rim and a highlight: something kept under cover."""
    ss = 4
    n = size * ss
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    box = [n * 0.04, n * 0.08, n * 0.96, n * 1.9]
    d.pieslice(box, 180, 360, fill=(170, 215, 245, 80))
    d.arc(box, 180, 360, fill=(20, 16, 14, 220), width=max(4, n // 30))
    d.arc(box, 180, 360, fill=(190, 230, 255, 255), width=max(2, n // 60))
    d.arc([n * 0.14, n * 0.18, n * 0.86, n * 1.8], 205, 250, fill=(255, 255, 255, 220), width=max(3, n // 28))
    d.rounded_rectangle([n * 0.02, n * 0.92, n * 0.98, n * 0.99], radius=n * 0.02, fill=(120, 130, 140, 255),
                        outline=(20, 16, 14, 255), width=max(2, n // 80))
    return resize_premultiplied(im, (size, size))


def link(size: int, colour: str = "gold", width: float = 0.09, state: str = "whole") -> Image.Image:
    """An arc from the lower left to the upper right: a tie between two coasts.

    `width` is its thickness (share of the side); `state` "whole", "taut"
    (straight), "cracked" (a dark break across it) or "broken" (a gap).
    """
    ss = 4
    n = size * ss
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    a, b = (0.12, 0.8), (0.88, 0.2)
    if state == "taut":
        pts = [a, b]
    else:
        t = np.linspace(0, 1, 24)
        mid = (0.36, 0.3)   # the arc bows up and left, over the globe's face
        pts = list(zip(((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * mid[0] + t ** 2 * b[0]).tolist(),
                       ((1 - t) ** 2 * a[1] + 2 * (1 - t) * t * mid[1] + t ** 2 * b[1]).tolist()))
    xy = [(x * n, y * n) for x, y in pts]
    w = max(2, round(width * n))
    mask = Image.new("L", (n, n), 0)
    md = ImageDraw.Draw(mask)
    md.line(xy, fill=255, width=w, joint="curve")
    for x, y in (xy[0], xy[-1]):
        md.ellipse([x - w * 0.9, y - w * 0.9, x + w * 0.9, y + w * 0.9], fill=255)
    if state == "broken":
        cx, cy = xy[len(xy) // 2]
        md.ellipse([cx - w * 1.6, cy - w * 1.6, cx + w * 1.6, cy + w * 1.6], fill=0)
    im = _gradient_fill(mask, colour)
    if state == "cracked":
        cx, cy = xy[len(xy) // 2]
        ImageDraw.Draw(im).line([(cx - w, cy - w * 1.2), (cx + w * 0.3, cy - w * 0.1), (cx - w * 0.2, cy + w * 0.3),
                                 (cx + w, cy + w * 1.2)], fill=(20, 16, 14, 255), width=max(2, w // 3))
    return resize_premultiplied(outlined(im, ss * max(1, size // 40)), (size, size))


def rays(size: int, count: int = 16, colour: str = "gold") -> Image.Image:
    """A starburst of thick pointed rays, drawn under an emblem to crown it (the Hegemon tier)."""
    ss = 4
    n = size * ss
    c = n / 2
    pts = []
    for i in range(count * 2):
        ang = -np.pi / 2 + i * np.pi / count
        rad = n * (0.49 if i % 2 == 0 else 0.3)
        pts.append((c + rad * np.cos(ang), c + rad * np.sin(ang)))
    mask = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(mask)
    d.polygon(pts, fill=255)
    # Only the points: the middle stays clear, so an emblem's gaps show the panel, not gold.
    d.ellipse([c - n * 0.34, c - n * 0.34, c + n * 0.34, c + n * 0.34], fill=0)
    return resize_premultiplied(outlined(_gradient_fill(mask, colour), ss * max(1, size // 50)), (size, size))


# Drawn marks by name; each takes the box size and the mark's own settings.
DRAWN = {
    "star": lambda box, m: star(box),
    "pause": lambda box, m: pause(box),
    "arrow_down": lambda box, m: arrow_down(box),
    "arrow": lambda box, m: arrow(box, m.get("dir", "down"), m.get("colour", "red"), m.get("double", False)),
    "bar": lambda box, m: bar(box, m.get("colour", "white")),
    "chevrons": lambda box, m: chevrons(box, m.get("count", 1), m.get("colour", "gold"), m.get("patch", False)),
    "barrier": lambda box, m: barrier(box),
    "bubble": lambda box, m: bubble(box, m.get("colour", "white"), m.get("cracked", False)),
    "thermometer": lambda box, m: thermometer(box, m.get("level", 0), m.get("burst", False)),
    "disc": lambda box, m: disc(box, m.get("colour", "red")),
    "shield": lambda box, m: shield_outline(box, m.get("colour", "blue")),
    "dome": lambda box, m: dome(box),
    "rays": lambda box, m: rays(box, m.get("count", 16), m.get("colour", "gold")),
    "link": lambda box, m: link(box, m.get("colour", "gold"), m.get("width", 0.09), m.get("state", "whole")),
}


def outlined(im: Image.Image, width: int, colour=(20, 16, 12), opacity: float = 0.85) -> Image.Image:
    """`im` over a dark outline `width` px wide, so a mark reads on any ground."""
    alpha = im.getchannel("A").filter(ImageFilter.MaxFilter(2 * width + 1))
    base = Image.new("RGBA", im.size, colour + (0,))
    base.putalpha(alpha.point(lambda v: int(v * opacity)))
    base.alpha_composite(im)
    return base


def apply_marks(icon: Image.Image, marks: list[dict], load) -> Image.Image:
    """Draw each mark over `icon`.

    A mark is {"icon": <vanilla path>} or {"part": "<cat>/<key>"} or
    {"draw": <a DRAWN name>, ...its settings}, placed with "at" (its centre, as
    shares of the width and height; default the lower right, (0.72, 0.72)) and
    "scale" (its larger side as a share of the icon's side; default 0.55).
    "under": True draws it beneath the icon instead (a bubble the coins rest
    against). `load(mark)` returns the mark's image for the first two kinds.
    Each gets a dark outline so it reads over the icon and the panel alike.
    """
    icon = icon.copy()
    side = min(icon.size)
    for mark in marks:
        box = max(1, round(side * mark.get("scale", 0.55)))
        if "draw" in mark:
            im = DRAWN[mark["draw"]](box, mark)
        else:
            im = load(mark).convert("RGBA")
            bbox = im.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
            if bbox:
                im = im.crop(bbox)
            k = box / max(im.size)
            im = resize_premultiplied(im, (max(1, round(im.width * k)), max(1, round(im.height * k))))
            if mark.get("tint"):
                im = tint(im, mark["tint"])
            if mark.get("outline", True):
                im = outlined(im, max(1, side // 50))
        if mark.get("rotate"):
            im = im.rotate(mark["rotate"], resample=Image.BICUBIC, expand=True)
        cx, cy = mark.get("at", (0.72, 0.72))
        x, y = round(cx * icon.width - im.width / 2), round(cy * icon.height - im.height / 2)
        if mark.get("under"):
            below = Image.new("RGBA", icon.size, (0, 0, 0, 0))
            paste(below, im, x, y)
            below.alpha_composite(icon)
            icon = below
        else:
            paste(icon, im, x, y)
    return icon


def flag_layout(im: Image.Image, size: tuple[int, int], cloth=(128, 172, 214)) -> Image.Image:
    """A bare flag: `cloth` with the icon as a faint pale watermark (the vacant seat).

    The watermark keeps the icon's own light and shade, lifted toward white,
    so a wreath still shows its leaves; its bare silhouette would be a blob.
    """
    w, h = size
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    xx = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    # A soft diagonal light so the cloth is not a flat swatch.
    rgb = np.array(cloth, np.float32) * (1.08 - 0.16 * (0.6 * yy + 0.4 * xx))
    rgb = np.broadcast_to(rgb, (h, w, 3)).copy()
    mark_h = round(h * 0.78)
    k = mark_h / im.height
    mark = np.asarray(resize_premultiplied(im, (max(1, round(im.width * k)), mark_h)), np.float32)
    x0, y0 = (w - mark.shape[1]) // 2, (h - mark.shape[0]) // 2
    region = rgb[y0:y0 + mark.shape[0], x0:x0 + mark.shape[1]]
    lum = (mark[..., :3] @ LUMA)[..., None]
    pale = 150 + lum * 0.45  # the icon's shading, in pale tones
    a = mark[..., 3:4] / 255 * 0.55
    region[:] = region * (1 - a) + np.clip(pale, 0, 255) * a
    border = max(1, round(h / 44))
    frame = np.zeros((h, w), bool)
    frame[:border], frame[-border:], frame[:, :border], frame[:, -border:] = True, True, True, True
    rgb[frame] = rgb[frame] * 0.35 + np.array((20, 24, 30), np.float32) * 0.65
    alpha = np.full((h, w, 1), 255, np.float32)
    return Image.fromarray(np.clip(np.concatenate([rgb, alpha], -1), 0, 255).astype(np.uint8), "RGBA")


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
    # A folder whose objects crowd the band lightens the median there (decrees
    # came out grey-green); such a category names vanilla's disc colours.
    if "disc" in spec:
        centre_col, edge_col = (np.array(c, dtype=np.float32) for c in spec["disc"])
    t = np.clip(r / ring_in, 0, 1)[..., None]
    bg = centre_col * (1 - t) + edge_col * t
    base = np.dstack([bg, alpha]).astype(np.uint8)
    icon = Image.fromarray(base, "RGBA")
    if obj is None:
        obj = fit_square(cut(raw, spec), size, 1.0)
        obj = grade_spread(obj, target, spec["disc"]) if spec.get("grade") == "spread" else grade(obj, target)
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
    obj = cut(raw, spec)
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
    obj = fit_square(cut(raw, spec), spec["size"], spec["fill"])
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


def card_template(folder: str, size: tuple[int, int], frame: tuple[int, int, int]) -> np.ndarray:
    """The blank card vanilla's IG traits are drawn on, in one approval slot's frame colour.

    Built from the folder's cards whose frame matches `frame`. A pixel is
    bare on a card unless it lies within 3 px of dark (a pictogram has light
    highlights and edges), except the card's own vines: pixels in the top or
    bottom band that are dark on nearly every card.
    - Outside a central ellipse, each pixel is the median over the cards on
      which it is bare (the plain median where it is bare on all of them),
      which keeps the frame, corner ornaments and edge shadow.
    - Inside it, the Gaussian-weighted average of every bare observation on
      every card (normalized convolution), a smooth gradient in the card's own
      colours like vanilla's middles, which the new pictogram mostly covers.
    Earlier tries left artefacts: a median over bare cards in the middle kept
    ghosts of their pictograms and fragments along the bottom that read as
    text; biharmonic inpainting overshot into white, blue and black blobs;
    filling from the plain median pulled the pictograms' dark in.
    """
    import warnings

    from scipy.ndimage import binary_dilation, gaussian_filter

    w, h = size
    stack = []
    for f in sorted((vanilla_icons_dir() / folder).glob("*.dds")):
        try:
            a = np.asarray(load_rgba(f), dtype=np.float32)
        except Exception:
            continue
        if a.shape[:2] != (h, w):
            continue
        xs = np.nonzero(a[h // 2, :, 3] > 200)[0]
        if len(xs) and np.abs(a[h // 2, xs.min() + 3, :3] - frame).max() < 30:
            stack.append(a)
    if len(stack) < 3:
        raise SystemExit(f"only {len(stack)} cards with frame {frame} in {vanilla_icons_dir() / folder}: "
                         "check VIC3_BASE_GAME")
    arr = np.stack(stack)
    dark = (arr[..., :3] @ LUMA) < 120
    band = np.zeros((h, w), bool)
    band[:round(h * 0.2)] = band[round(h * 0.75):] = True
    ornament = band & (dark.mean(axis=0) > 0.9)
    bare = ~np.stack([binary_dilation(d & ~ornament, iterations=3) for d in dark])
    count = bare.sum(axis=0)
    card = np.median(arr, axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        bare_med = np.nanmedian(np.where(bare[..., None], arr, np.nan), axis=0)
    some = (count > 0) & (count < len(stack))
    card[some] = bare_med[some]
    sigma = w / 8
    total = (arr[..., :3] * bare[..., None]).sum(axis=0)
    den = gaussian_filter(count.astype(np.float32), sigma)
    fill = np.stack([gaussian_filter(total[..., c], sigma) / np.maximum(den, 1e-6) for c in range(3)], axis=-1)
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - w / 2) / (w * 0.38), (yy - h * 0.5) / (h * 0.445))
    weight = np.clip((1.05 - r) * 5, 0, 1)
    # A small dark blob left inside the frame, where pictograms crowd a corner
    # on most cards (the green card's bottom right), takes the fill too.
    from scipy.ndimage import label
    inside = np.zeros((h, w), bool)
    inside[round(h * 0.08):round(h * 0.92), round(w * 0.1):round(w * 0.9)] = True
    blobs, n = label(((card[..., :3] @ LUMA) < 90) & inside & (weight < 1))
    sizes = np.bincount(blobs.ravel())
    small = np.isin(blobs, [i for i in range(1, n + 1) if sizes[i] < w * h / 300])
    weight = np.maximum(weight, gaussian_filter(small.astype(np.float32), 1.5) * 3)
    weight = np.clip(weight, 0, 1)[..., None]
    card[..., :3] = card[..., :3] * (1 - weight) + fill * weight
    return card


def recolor_card(card: np.ndarray, deg: float, sat: float) -> np.ndarray:
    """A card template with every hue turned by `deg` and saturation scaled by `sat`.

    For a card colour vanilla has no cards in: the ornaments and shading of a
    lifted template carry over.
    """
    out = card.copy()
    hsv = np.asarray(Image.fromarray(np.clip(card[..., :3] + 0.5, 0, 255).astype(np.uint8), "RGB").convert("HSV"),
                     dtype=np.float32)
    hsv[..., 0] = (hsv[..., 0] + deg / 360 * 256) % 256
    hsv[..., 1] = np.clip(hsv[..., 1] * sat, 0, 255)
    out[..., :3] = np.asarray(Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB"), dtype=np.float32)
    return out


def recolor_rgb(c, deg: float, sat: float) -> tuple[float, float, float]:
    """recolor_card for one colour (channels above 255 allowed, as in emboss colours)."""
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    return tuple(x * 255 for x in colorsys.hsv_to_rgb((h + deg / 360) % 1, min(1.0, s * sat), v))


def compose_card(raw: Image.Image, spec: dict, card: np.ndarray) -> Image.Image:
    """The dark embossed pictogram, centred on the slot's card."""
    h, w = card.shape[:2]
    obj = embossed(raw, dict(spec, fill=0.98), 2 * h)
    bbox = obj.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    if bbox:
        obj = obj.crop(bbox)
    scale = min(w * spec["fill"][0] / obj.width, h * spec["fill"][1] / obj.height)
    obj = resize_premultiplied(obj, (max(1, round(obj.width * scale)), max(1, round(obj.height * scale))))
    icon = Image.fromarray(np.clip(card, 0, 255).astype(np.uint8), "RGBA")
    icon.alpha_composite(obj, ((w - obj.width) // 2, round(h * 0.49 - obj.height / 2)))
    return icon


def vanilla_folder(spec: dict) -> Path:
    """The vanilla folder a category's files live in (`root` defaults to gfx/interface/icons)."""
    return vanilla_icons_dir().parents[2] / spec.get("root", "gfx/interface/icons") / spec["folder"]


# Institution strips (Institution.GetBackground, politics_panel_institutions.gui)
# are 3500x220, but the panel centre-crops each to its row: a box from 70 px
# into the row to 150 px past its right edge, where the panel clips it, scaled
# to the row's height. About x 1300-2000 of the strip shows, drawn at roughly
# half opacity through institution_image_mask.dds. Vanilla paints its figures
# there and fills the rest with a dim, blurred continuation.
STRIP_BAND = (1300, 2000)
STRIP_CENTRE = 1700


def strip_grade_target(folder: Path) -> dict:
    """50th and 90th percentiles of saturation and value in the band of vanilla's strips that shows."""
    s, v = [], []
    for f in sorted(folder.glob("*.dds")):
        if "mask" in f.stem:
            continue
        try:
            im = load_rgba(f).crop((STRIP_BAND[0], 0, STRIP_BAND[1], 220))
        except Exception:
            continue
        hsv = np.asarray(im.convert("RGB").convert("HSV"), dtype=np.float32).reshape(-1, 3) / 255
        s.append(hsv[:, 1])
        v.append(hsv[:, 2])
    if not s:
        raise SystemExit(f"no strips in {folder}: check VIC3_BASE_GAME")
    return {1: np.percentile(np.concatenate(s), SPREAD_PCT), 2: np.percentile(np.concatenate(v), SPREAD_PCT)}


def compose_strip(raw: Image.Image, spec: dict, target) -> Image.Image:
    """A wide render centred on the strip, the sides its mirror image, blurred and dimmed.

    The sides only show on a short row, as in vanilla. Mirroring keeps them
    continuous with the scene's edge; they blend from sharp to blurred over
    60 px and darken with distance.
    """
    from scipy.ndimage import gaussian_filter

    W, H = spec["size"]
    scene = raw.convert("RGBA").resize((round(raw.width * H / raw.height), H), Image.LANCZOS)
    scene = grade_spread(scene, target, strength=spec.get("grade_strength", 0.8))
    w = scene.width
    x0 = max(0, min(W - w, round(STRIP_CENTRE - w / 2)))
    a = np.asarray(scene.convert("RGB"), dtype=np.float32)
    wide = np.pad(a, ((0, 0), (x0, W - x0 - w), (0, 0)), mode="symmetric")
    soft = gaussian_filter(wide, sigma=(3, 14, 0))
    x = np.arange(W)
    d = np.maximum(np.maximum(x0 - x, x - (x0 + w - 1)), 0).astype(np.float32)
    t = np.clip(d / 60, 0, 1)[None, :, None]
    out = (wide * (1 - t) + soft * t) * (1 - 0.4 * np.clip(d / 900, 0, 1))[None, :, None]
    return Image.fromarray(np.dstack([np.clip(out + 0.5, 0, 255), np.full((H, W), 255.0)]).astype(np.uint8), "RGBA")


def _nine_slice(m: Image.Image, size: tuple[int, int], borders: tuple[int, int, int, int],
                density: float) -> Image.Image:
    """`spriteType = Corneredstretched`: fixed borders (texels / density), stretched middle."""
    W, H = m.size
    w, h = size
    L, T, R, B = borders
    xs_src, ys_src = (0, L, W - R, W), (0, T, H - B, H)
    xs = (0, round(L / density), w - round(R / density), w)
    ys = (0, round(T / density), h - round(B / density), h)
    out = Image.new(m.mode, size)
    for i in range(3):
        for j in range(3):
            src = (xs_src[i], ys_src[j], xs_src[i + 1], ys_src[j + 1])
            dst = (xs[i], ys[j], xs[i + 1], ys[j + 1])
            if src[2] > src[0] and src[3] > src[1] and dst[2] > dst[0] and dst[3] > dst[1]:
                out.paste(m.crop(src).resize((dst[2] - dst[0], dst[3] - dst[1]), Image.BILINEAR), dst[:2])
    return out


def strip_in_panel(strip: Image.Image, mask: Image.Image, row_h: int = 180) -> Image.Image:
    """Roughly what the institution panel shows of a strip: the review sheet's view of it.

    The box is 600 px wide (70 px into the 520 px row to 150 px past it) and
    row_h tall; the panel clips it at the row's edge, 450 px in.
    """
    bw = 600
    scale = max(bw / strip.width, row_h / strip.height)
    cw, ch = bw / scale, row_h / scale
    left, top = (strip.width - cw) / 2, (strip.height - ch) / 2
    view = strip.convert("RGB").resize((bw, row_h), Image.LANCZOS, box=(left, top, left + cw, top + ch))
    alpha = _nine_slice(mask.getchannel("A"), (bw, row_h), (150, 0, 50, 50), 2)
    panel = Image.new("RGB", (bw, row_h), (38, 41, 46))
    panel.paste(view, (0, 0), alpha)
    return panel.crop((0, 0, 450, row_h))


def strip_sheet(rows: list, mask_path: Path, out: Path) -> None:
    """Row per entity: [current | candidates], each as the panel shows it over the whole strip."""
    mask = load_rgba(mask_path)
    tile_w, view_h, full_h, gap = 450, 180, 28, 12
    n = max(1 + len(c) for _, _, c in rows)
    row_h = 22 + view_h + full_h + gap
    sheet = Image.new("RGB", (n * (tile_w + gap), len(rows) * row_h), (24, 26, 30))
    d = ImageDraw.Draw(sheet)
    for r, (label, current, cands) in enumerate(rows):
        y = r * row_h
        for j, (caption, src) in enumerate([("now", current)] + cands):
            x = j * (tile_w + gap)
            try:
                strip = load_rgba(src)
            except Exception:
                continue
            d.text((x + 4, y + 4), f"{label.splitlines()[0]}  {caption}" if j == 0 else caption,
                   fill=(220, 200, 140) if j else (200, 200, 200))
            sheet.paste(strip_in_panel(strip, mask, view_h), (x, y + 22))
            sheet.paste(strip.convert("RGB").resize((tile_w, full_h), Image.LANCZOS), (x, y + 22 + view_h))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


class Composer:
    """Compose raw renders per category, caching each category's vanilla template."""

    def __init__(self) -> None:
        self._tmpl: dict[str, tuple] = {}
        self._target: dict[str, tuple] = {}

    def compose(self, raw: Image.Image, cat: str, spec: dict, backdrop: Image.Image | None = None) -> Image.Image:
        mode = spec["mode"]
        if mode in ("framed", "medallion", "emboss_medallion") and cat not in self._tmpl:
            self._tmpl[cat] = vanilla_template(spec["folder"], spec["size"])
        if mode == "plinth" and cat not in self._tmpl:
            self._tmpl[cat] = plinth_template(spec["folder"], spec["size"])
        if mode in ("cutout", "backed", "medallion", "plinth") and cat not in self._target:
            # A medallion's opaque pixels are mostly its dark disc: grade the
            # object against a folder of bare objects instead.
            self._target[cat] = (medallion_object_target(spec["folder"], spec["disc"]) if spec.get("grade") == "spread"
                                 else category_grade_target(spec.get("grade_folder", spec["folder"])))
        if mode == "strip" and cat not in self._target:
            self._target[cat] = strip_grade_target(vanilla_folder(spec))
        if mode == "tinted" and cat not in self._tmpl:
            self._tmpl[cat] = tone_ramp(spec.get("ramp_folder", spec["folder"]))
        if mode == "card" and cat not in self._tmpl:
            self._tmpl[cat] = card_template(spec["folder"], spec["card_size"], spec["frame"])
            if "recolor" in spec:
                self._tmpl[cat] = recolor_card(self._tmpl[cat], *spec["recolor"])
        if mode == "card" and "recolor" in spec:
            # The pictogram's tint turns with its card.
            spec = dict(spec, **{k: recolor_rgb(spec[k], *spec["recolor"])
                                 for k in ("color", "color_bottom") if k in spec})
        raw = raw.convert("RGB")
        if mode == "strip":
            return compose_strip(raw, spec, self._target[cat])
        if mode == "tinted":
            return compose_tinted(raw, spec, self._tmpl[cat])
        if mode == "card":
            return compose_card(raw, spec, self._tmpl[cat])
        if mode == "cutout":
            return compose_cutout(raw, spec, self._target[cat])
        if mode == "backed":
            if backdrop is None:
                raise ValueError(f"{cat}: the backed layout needs its composed backdrop")
            return compose_backed(raw, spec, self._target[cat], backdrop)
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


def panel_preview(rows: list, out: Path) -> None:
    """Journal icons as the game draws them, one row per entity.

    The panel puts the icon at 100 px inside vanilla's 120 px round frame
    (gui/journal_entry.gui), and the journal list shows it alone at 40 px. Each
    candidate gets both, on the panel's dark ground, at 2x so they can be judged.
    rows: (label, [(caption, candidate image), ...]).
    """
    frame = load_rgba(vanilla_icons_dir().parent / "backgrounds" / "round_frame_dec.dds")
    frame = resize_premultiplied(frame, (120, 120))
    ground = (33, 34, 40, 255)
    cell_w, cell_h, label_w = 250, 130, 220
    ncols = max((len(c) for _, c in rows), default=0)
    sheet = Image.new("RGBA", (label_w + cell_w * ncols, cell_h * len(rows)), ground)
    d = ImageDraw.Draw(sheet)
    for i, (label, candidates) in enumerate(rows):
        y = i * cell_h
        d.text((6, y + 8), label, fill=(235, 235, 235, 255))
        for j, (caption, im) in enumerate(candidates):
            x = label_w + j * cell_w
            tile = Image.new("RGBA", (cell_w, cell_h), ground)
            tile.alpha_composite(frame, (5, 5))
            im = im.convert("RGBA")
            tile.alpha_composite(resize_premultiplied(im, (100, 100)), (15, 15))
            tile.alpha_composite(resize_premultiplied(im, (40, 40)), (140, 45))
            d.text((x + 150, y + 96), caption, fill=(220, 200, 140, 255))
            sheet.alpha_composite(tile, (x, y))
    sheet.save(out)
    print(f"wrote {out}")


def backdrop_sheet(rows: list, out: Path, scale: int = 2) -> None:
    """The backed category's backdrop candidates, each under sample icons.

    rows: (label, [(caption, image), ...]); the first image is the bare disc,
    the rest are sample subjects composed over it. At `scale` x native.
    """
    size = max((im.width for _, c in rows for _, im in c), default=150) * scale
    ncols = max((len(c) for _, c in rows), default=0)
    sheet = Image.new("RGBA", (120 + (size + 10) * ncols, (size + 10) * len(rows)), (33, 34, 40, 255))
    d = ImageDraw.Draw(sheet)
    for i, (label, images) in enumerate(rows):
        y = i * (size + 10)
        d.text((6, y + 8), label, fill=(235, 235, 235, 255))
        for j, (caption, im) in enumerate(images):
            sheet.alpha_composite(im.convert("RGBA").resize((size, size), Image.LANCZOS), (120 + j * (size + 10), y + 5))
            if caption:
                d.text((124 + j * (size + 10), y + 8), caption, fill=(220, 200, 140, 255))
    sheet.save(out)
    print(f"wrote {out}")
