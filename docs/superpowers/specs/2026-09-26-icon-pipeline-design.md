# Icon pipeline: FLUX-generated UI icons for placeholder entities — design

Status: **prototype** (`scripts/image_pipeline/icon_samples.py`); the production pipeline below is not built yet.

## Goal

Extend the event-image pipeline (`generate_event_images.py`, FLUX.1-schnell) to the mod's UI icons. Many mod-added techs, treaty articles, buildings, decrees and other entities point at a vanilla icon that belongs to something else. The new icons have to sit beside vanilla's without looking out of place.

## Inventory (2026-09-26)

Mod-added entities (key not in vanilla) whose icon path resolves only to a vanilla file:

**Needs new art** — vanilla gives each entity its own icon:

| Category | Entities | Notes |
|---|---|---|
| Technologies | 170 | 135 on `invention_icons/mass_communication.dds` |
| Buildings | 300 | 205 distinct files; 50 on `skyscraper.dds`, 12 on `building_government_administration.dds`. Some reuse may be deliberate, see the allowlist below |
| Power bloc principles | 42 groups | 124 tiers; vanilla uses one icon per group, not per tier |
| Ideologies | 33 | 21 files |
| Treaty articles | 30 | 18 on `offer_embassy.dds` |
| Mobilization options | 27 | 14 on `machinegunners.dds` |
| IG traits | 18 | |
| Institutions | 17 | vanilla has 8 icons |
| Decrees | 15 | 13 on `decree_road_maintenance.dds` |
| Diplomatic actions | 7 | |
| Character traits | 6 | |
| PMs | 100 | already covered by `gen_batch_pm_icons.py` |
| Laws | 3 + 15 | 3 borrowed; 15 ministry laws whose mod-generated icons are byte-identical (`/duplicate-images`, `kind: content`) |

**Shared by design — not placeholders.** Vanilla shares these too: JE icons (generic `event_*.dds`), state traits (`resources_ore.dds`), diplomatic plays (`unification.dds` for every unify/leadership play), ship modifications, company `basic_*` icons, ship types, static modifier icons, PM-group textures, building backgrounds, message textures. Mod `gui/` references to `gfx/interface/icons/` are UI glyphs (warning, checkmark, filter icons), also fine.

None of the files holding a placeholder reference are generator-owned, so rewriting the references is a plain text edit.

## Vanilla icon formats

| Folder | Size | Look |
|---|---|---|
| `invention_icons` (techs) | 256² | painted object, transparent background |
| `building_icons` | 256² | painted aerial scene inside a rounded gold frame |
| `diplomatic_treaties_articles_icons` | 100² | painted object group, one accent colour |
| `diplomatic_action_icons` | 100² | painted object, often on a small green plinth |
| `decree` | 158² | object on a dark teal disc under a gold ring |
| `ideology_icons` | 220² | embossed gold symbol on a crimson disc under a gold ring |
| `mobilization_options` | 208² | embossed rust-orange silhouette |
| `principles_icons` | 210² | mixed: painted objects, some framed tiles |
| `institution_icons` / `law_icons` | 256² | tan/bronze sculpted object |
| `ig_trait_icons` | 124×162 | card with a coloured frame |

All are **uncompressed 32-bit RGBA with a full mip chain**, except mobilization options (DXT5). They are not BC7, so `gen_pm_icons.convert_to_dds` (BC7) can't be reused as-is. Also, 100/158/210/220 are not multiples of 4, so BC7 at those sizes would fail CI's `check_dds_dimensions.py`.

## Prototype findings

`icon_samples.py` renders a few samples per category and a sheet placing each candidate after the current placeholder and three vanilla neighbours, at native size.

Each row: current placeholder | three vanilla neighbours ‖ two generated candidates.

- Second pass (current prompts): [`assets/2026-09-26-icon-pipeline-pass2.jpg`](assets/2026-09-26-icon-pipeline-pass2.jpg)
- First pass (photographic, before the style fix): [`assets/2026-09-26-icon-pipeline-pass1.jpg`](assets/2026-09-26-icon-pipeline-pass1.jpg)

- **Buildings — good on the first try.** A painted diorama prompt, fitted inside the frame lifted from vanilla.
- **Mobilization options, ideologies — good.** FLUX draws a black silhouette and `gen_pm_icons.apply_metallic_style` embosses it, onto the vanilla disc and ring for ideologies. The same route would give the 15 identical ministry-law icons distinct shapes.
- **Techs, treaty articles, decrees — good after one revision.** The first pass came out as product photography with garbled text. The prompt has to name the medium: "stylized hand-painted video game icon, painterly digital art with visible brush strokes … blank unmarked surfaces". 100 px categories need "one compact bold object group filling the frame", or the art shrinks to specks. Several subject phrases were rewritten in the same pass, so credit both changes.
- **Still weak.** The diplomatic-action plinth renders detached from its figure. One transistor seed still shows a "2254" label. Principles, IG-trait cards and institutions were not tried.

**Frames are lifted from vanilla, not drawn.** `vanilla_template()` takes the per-pixel median of every same-size icon in the folder. The frame is identical on every icon, so it survives the median while the artwork averages to mud. The medallion ring starts where the colour spread across the folder collapses: decree r≈68 of 79, ideology r≈87 of 110. A fixed fraction sampled the wrong band on ideologies and turned the disc salmon. So the compose step needs the game install, like the raw-vanilla regenerators.

## Production design

1. **Work list: `/duplicate-images`.**
   - Add Treaty Articles, Diplomatic Actions, Power Bloc Principles (clustered per principle group), Institutions, Ideologies, Mobilization Options, IG traits and Character Traits to its strict types.
   - Triage `common/_meta/duplicate_image_allowlist.yml` first. 83 entries still carry the placeholder reason "existing reuse - verify intent". One of them hides the 13 decrees on `decree_road_maintenance.dds`. The `mass_communication.dds` tech cluster is flagged today only because its entry's entity list went stale. An entry that is really a placeholder comes off the allowlist and onto the work list.
   - The pipeline reads the list through `ModState` directly, not HTTP.
2. **Prompt registry.** `icon_prompts.py`, next to `event_image_prompts.py`:
   - `CATEGORIES` per category: folder, size, layout, style template, DDS format, output folder.
   - `ICONS`: entity key → subject phrase, plus the accepted seed once reviewed, so reruns are deterministic.
   - About 520 subject phrases. Draft them from each entity's loc name and `_desc` (buildings have no `_desc`; wonders are real landmarks FLUX knows), then review.
3. **Renderer.** Generalise `generate_event_images.py`'s phases rather than adding a third orchestrator:
   - Embed every prompt in one process and cache the embeddings, since T5 takes ~5 min to load per process.
   - Render in a second process that loads the transformer once. The event pipeline currently reloads the 24 GB model per image and would benefit from the same fix.
   - Skip anything whose output already exists.
4. **Compose.** The prototype has five layouts: `cutout` (rembg `isnet-general-use`), `framed`, `medallion`, `emboss` and `emboss_medallion`. Still to build: an IG-trait card layout (frame colour per trait), principles, institutions (a monochrome bronze tint over a cutout is the first thing to try), and a plinth for diplomatic actions (likely lifted from vanilla like the frames, rather than prompted).
5. **DDS writer.** texconv via WSL interop, `-f B8G8R8A8_UNORM -m 0` (uncompressed + mips, matching vanilla).
   - Budget: a 256² uncompressed icon with mips is ~350 KB, so ~520 icons add roughly 100–180 MB to a 1.8 GB `gfx/`.
   - BC7 is possible for 256² folders only (~88 KB each), at some quality cost. Owner call.
6. **Reference rewrite.** Replace the `icon =` / `texture =` line inside each entity block, handling `INJECT:`/`REPLACE:` blocks. Generalise `generate_event_images.py` phase 3 or `gen_batch_pm_icons.update_pm_files`.
7. **Review loop.** A contact sheet per batch beside vanilla neighbours (the prototype's `contact_sheet()`). Rejects get a new seed or an edited subject.
8. **Docs.** Rows in `docs/auto_generated_files.md` for each new output folder; the script table in `docs/guides/python_tools.md`.

**Priority:** techs, treaty articles, decrees, institutions, principles, ideologies, mobilization options, IG traits, diplomatic actions, then buildings once their allowlist entries are triaged.

## Runtime (RTX 3080 10 GB, 39 GB RAM, WSL2)

- **Offload:** `enable_model_cpu_offload` runs out of memory, because the transformer is 24 GB in bf16. `enable_sequential_cpu_offload` works: ~30 s per 1024² image once warm, 2–4 min for the first.
- **Embedding:** ~5 min per process (T5 reload); peak RSS 6.4 GB.
- **Full run:** ~520 icons × 2 seeds ≈ 8–9 h GPU, i.e. an overnight run plus re-rolls.
- **NF4:** `bitsandbytes` is installed in `.venv-img` but a 4-bit transformer is **untested**. If it fits in VRAM it would avoid the offload streaming.
- **Weights:** keep them on ext4. Copying the 32 GB snapshot off `/mnt/c` took 7 min; streaming it from drvfs on every run would pay that each time. Point `FLUX_MODEL_DIR` at the copy.
- **Stale cache path:** the shell sets `HF_HOME=/mnt/e/hf-cache`, which doesn't exist, so any bare `from_pretrained("black-forest-labs/FLUX.1-schnell")` would start a 32 GB download there.
- **rembg:** `rembg[gpu]` pulls an `onnxruntime-gpu` that wants CUDA 13 libraries and falls back to CPU. Plain `onnxruntime` is enough (~1–2 s per image).
- **Environment:** the image stack lives in `.venv-img` (gitignored), separate from `.venv`, since `requirements.txt` keeps torch/diffusers commented out.

## Open questions

- Uncompressed (vanilla parity, ~100–180 MB) or BC7 where the size allows?
- Diplomatic-action plinth: lifted from vanilla, or dropped?
- Buildings: which of the 300 borrowings are deliberate (a company building reusing its industry's icon) and should stay allowlisted?
