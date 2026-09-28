# Icon pipeline: FLUX-generated UI icons for placeholder entities — design

Status: **production pipeline started with technologies** (`scripts/image_pipeline/generate_icons.py`, registry `icon_prompts.py`, shared code `icon_render.py`, DDS writer `icon_dds.py`). The prototype sample sheet is `icon_samples.py`. Other categories follow the order under Production design.

## Goal

Extend the event-image pipeline (`generate_event_images.py`, FLUX.1-schnell) to the mod's UI icons. Many mod-added techs, treaty articles, buildings, decrees and other entities point at a vanilla icon that belongs to something else. The new icons have to sit beside vanilla's without looking out of place.

## Inventory (2026-09-26)

Mod-added entities (key not in vanilla) whose icon path resolves only to a vanilla file:

**Needs new art** — vanilla gives each entity its own icon:

| Category | Entities | Notes |
|---|---|---|
| Technologies | 170 | 135 on `invention_icons/mass_communication.dds` |
| Buildings | 300 | 205 distinct files; 50 on `skyscraper.dds`, 12 on `building_government_administration.dds`. Some reuse may be deliberate, see the allowlist below |
| Power bloc principles | 15 groups | 75 tiers on 5 vanilla icons, 8 groups on `food_standardization`. The first count, 42, included 22 vanilla groups that gained tiers 4–5 and the 5 `sacred_civics_N_mod` variants; those share their group's icon as vanilla does. Their tier frames were the real gap: `gen_principle_tier_frames.py` added frames IV and V |
| Ideologies | ~9 | 33 borrow, but 24 are `ideology_custom_religion_*` variants on their base ideology's icon, as vanilla's variants are (`papal_paternalistic` → `paternalistic.dds`). Two looks: IG ideologies gold on a crimson disc, leader ideologies silver on teal (`ideology_leader/`) |
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

None of the files holding a placeholder reference are generator-owned, so rewriting the references is a plain text edit. One caveat: `common/buildings/company_buildings.txt` (45 building icon references) was bootstrapped by `gen_vanilla_company_buildings.py`. It is hand-editable now, but re-running that generator would put the old icons back.

**Totals.** The table first summed to 665 icons, or 683 with the 18 law icons. A later recount of principles (42 → 15) and ideologies (33 → ~9) takes about 51 off. The building row will shrink once its allowlist entries are triaged. A recount on 2026-09-27 matched apart from content added since (31 treaty articles, 316 buildings).

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
| `institution_icons` | 256² | tan/bronze sculpted object |
| `law_icons` | mostly 302² (69 of 132); also 256² and 300² | tan/bronze sculpted object |
| `ig_trait_icons` | 124×162 | card with a coloured frame |

All are **uncompressed 32-bit RGBA with a full mip chain**, except mobilization options (DXT5). They are not BC7, so `gen_pm_icons.convert_to_dds` (BC7) can't be reused as-is. Block compression needs sides that are multiples of 4: 100, 208, 220 and 256 are (vanilla already ships mobilization options as DXT5 at 208²). Decrees (158), principles (210), IG traits (124×162) and laws (302) are not, so BC7 at those sizes would fail CI's `check_dds_dimensions.py`.

## Prototype findings

`icon_samples.py` renders a few samples per category and a sheet placing each candidate after the current placeholder and three vanilla neighbours, at native size.

Each row: current placeholder | three vanilla neighbours ‖ two generated candidates.

- Third pass (2026-09-27, current prompts): [`assets/2026-09-27-icon-pipeline-pass3.jpg`](assets/2026-09-27-icon-pipeline-pass3.jpg). Identical to the second pass except the basic-income row: the seeds are fixed, so the same prompt redraws the same picture.
- Second pass: [`assets/2026-09-26-icon-pipeline-pass2.jpg`](assets/2026-09-26-icon-pipeline-pass2.jpg)
- First pass (photographic, before the style fix): [`assets/2026-09-26-icon-pipeline-pass1.jpg`](assets/2026-09-26-icon-pipeline-pass1.jpg)

- **Buildings — good on the first try.** A painted diorama prompt, fitted inside the frame lifted from vanilla.
- **Mobilization options, ideologies — good.** FLUX draws a black silhouette and `gen_pm_icons.apply_metallic_style` embosses it, onto the vanilla disc and ring for ideologies. The same route would give the 15 identical ministry-law icons distinct shapes.
- **Techs, treaty articles, decrees — good after one revision.** The first pass came out as product photography with garbled text. The prompt has to name the medium: "stylized hand-painted video game icon, painterly digital art with visible brush strokes … blank unmarked surfaces". 100 px categories need "one compact bold object group filling the frame", or the art shrinks to specks. Several subject phrases were rewritten in the same pass, so credit both changes.
- **Still weak.** The diplomatic-action plinth renders detached from its figure. One transistor seed still shows a "2254" label. The second pass's basic-income notes were green with a portrait oval and read as US dollars; asking for "plain cream-and-brown paper banknotes" fixed it in the third pass. Principles, IG-trait cards and institutions were not tried.

**Frames are lifted from vanilla, not drawn.** `vanilla_template()` takes the per-pixel median of every same-size icon in the folder. The frame is identical on every icon, so it survives the median while the artwork averages to mud. The medallion ring starts where the colour spread across the folder collapses: decree r≈68 of 79, ideology r≈87 of 110. A fixed fraction sampled the wrong band on ideologies and turned the disc salmon. So the compose step needs the game install, like the raw-vanilla regenerators.

## Production design

1. **Work list: `/duplicate-images`.**
   - Add Treaty Articles, Diplomatic Actions, Power Bloc Principles (clustered per principle group), Institutions, Ideologies, Mobilization Options, IG traits and Character Traits to its strict types.
   - Triage `common/_meta/duplicate_image_allowlist.yml` first. 83 entries still carry the placeholder reason "existing reuse - verify intent". One of them hides the 13 decrees on `decree_road_maintenance.dds`. The `mass_communication.dds` tech cluster is flagged today only because its entry's entity list went stale. An entry that is really a placeholder comes off the allowlist and onto the work list.
   - The pipeline reads the list through `ModState` directly, not HTTP.
2. **Prompt registry.** `icon_prompts.py`, next to `event_image_prompts.py`:
   - `CATEGORIES` per category: folder, size, layout, style template, DDS format, output folder.
   - `ICONS`: entity key → subject phrase, plus the accepted seed once reviewed, so reruns are deterministic.
   - About 665 subject phrases (683 with laws), fewer after the building triage. Draft them from each entity's loc name and `_desc` (buildings have no `_desc`; wonders are real landmarks FLUX knows), then review.
3. **Renderer.** Generalise `generate_event_images.py`'s phases rather than adding a third orchestrator. Its `gen_image.py` can't be used as it stands: it reloads the model per image, uses model offload (out of memory on the 3080) and passes a bare hub id (a 32 GB download). #533's event pictures were made with a one-process batch instead.
   - Embed every prompt in one process and cache the embeddings, since T5 takes ~5 min to load per process.
   - Render in a second process that loads the transformer once. The event pipeline currently reloads the 24 GB model per image and would benefit from the same fix.
   - Skip an output only when it was made from the current prompt. The prototype writes a `.prompt.txt` beside each render and redoes it when the prompt changes; skipping on "file exists" alone would keep the old picture after a prompt edit. The event pipeline has that gap, which is why #502's redraw recipe deletes the old PNG by hand.
4. **Compose.** The prototype has five layouts: `cutout` (rembg `isnet-general-use`), `framed`, `medallion`, `emboss` and `emboss_medallion`. Still to build: an IG-trait card layout (frame colour per trait), principles, institutions (a monochrome bronze tint over a cutout is the first thing to try), and a plinth for diplomatic actions (likely lifted from vanilla like the frames, rather than prompted).
5. **DDS writer.** texconv via WSL interop, `-f B8G8R8A8_UNORM -m 0` (uncompressed + mips, matching vanilla).
   - Budget: a 256² uncompressed icon with mips is ~350 KB. At each folder's vanilla size, the 683 icons add ~212 MB to a 1.8 GB `gfx/`, 105 MB of it buildings.
   - BC7 works wherever the side is a multiple of 4: everything except decrees, principles, IG traits and laws. That brings the total to ~70 MB (a 256² icon drops to ~88 KB), at some quality cost. Owner call.
6. **Reference rewrite.** Replace the `icon =` / `texture =` line inside each entity block, handling `INJECT:`/`REPLACE:` blocks. Generalise `generate_event_images.py` phase 3 or `gen_batch_pm_icons.update_pm_files`.
7. **Review loop.** A contact sheet per batch beside vanilla neighbours (the prototype's `contact_sheet()`). Rejects get a new seed or an edited subject. Reject real currency, flags, lettering and recognisable faces: FLUX adds them unasked (`docs/guides/event_creation_guide.md`, from #502's review).
8. **Docs.** Rows in `docs/auto_generated_files.md` for each new output folder; the script table in `docs/guides/python_tools.md`.

**Priority:** techs, treaty articles, decrees, institutions, principles, ideologies, mobilization options, IG traits, diplomatic actions, then buildings once their allowlist entries are triaged.

## Runtime (RTX 3080 10 GB, 39 GB RAM, WSL2)

- **Offload:** `enable_model_cpu_offload` runs out of memory, because the transformer is 24 GB in bf16. `enable_sequential_cpu_offload` works: ~30 s per 1024² image once warm, 2–4 min for the first.
- **Embedding:** ~5 min per process (T5 reload) from the first copy; 15 s on 2026-09-27 with the weights in `~/models/FLUX.1-schnell` and still in the page cache from the copy. Peak RSS 6.4 GB.
- **Full run:** 683 icons × 2 seeds ≈ 11 h GPU, more than a night. Render one seed first (~5.7 h), then second seeds for the rejects only.
- **NF4:** `bitsandbytes` is installed in `.venv-img` but a 4-bit transformer is **untested**. If it fits in VRAM it would avoid the offload streaming.
- **Weights:** keep them on ext4, outside the session scratchpad, which a reboot clears. The copy now lives at `~/models/FLUX.1-schnell`. Copying the 32 GB snapshot off `/mnt/c` took 7 min; streaming it from drvfs on every run would pay that each time. Point `FLUX_MODEL_DIR` at the copy.
- **Stale cache path:** the shell sets `HF_HOME=/mnt/e/hf-cache`, which doesn't exist, so any bare `from_pretrained("black-forest-labs/FLUX.1-schnell")` would start a 32 GB download there.
- **rembg:** `rembg[gpu]` pulls an `onnxruntime-gpu` that wants CUDA 13 libraries and falls back to CPU. Plain `onnxruntime` is enough (~1–2 s per image).
- **Environment:** the image stack lives in `.venv-img` (gitignored), separate from `.venv`, since `requirements.txt` keeps torch/diffusers commented out.

## Decisions (owner, 2026-09-27)

- **DDS format: uncompressed**, vanilla parity (~212 MB for everything). `icon_dds.py` writes it in Python; its header matches vanilla's byte for byte apart from the NVTT tool signature.
- **Diplomatic-action plinth: lift it from vanilla** like the frames. Drop it if that proves hard.
- **Buildings: most borrowings are placeholders, but a fair number can share a common icon.** Generate only for the real placeholders, and not all 300 at first. Triage when buildings come up.

## Technology slice (2026-09-27)

The first production category, end to end:

1. `icon_prompts.ICONS["technology"]`: 170 subjects, drafted from each tech's name and description, one physical object each, with material and colour named.
2. `generate_icons.py --stage render --seeds 2`, then `--stage compose` and `--stage sheet`: review sheets of 20.
3. Record the chosen seed per tech in the registry (`"keep"` leaves the borrowed vanilla icon in place). 35 techs borrow a vanilla icon other than the newspapers, and some of those may fit.
4. `--stage write` (DDS to `gfx/interface/icons/invention_icons/<key>.dds`), then `--stage wire` (rewrites the tech's `texture =` line), then an in-game check.

The owner approved all 170 subjects and asked for era 6 first (37 techs) before rendering the rest.

## Diplomatic slice (2026-09-27)

- **Treaty articles** (31: 18 on `offer_embassy`, the rest on law or event icons). They use the prototype's 100² `cutout` style unchanged, with `field = icon` in `common/treaty_articles/`. `wire` drops the `# Placeholder Icon` comment on the lines it rewrites.
- **Diplomatic actions** (7) have a new `plinth` layout. The slab is lifted from vanilla, per the owner's call. `icon_render.plinth_template()` takes the median over the 16 vanilla icons whose green-topped stone slab sits in the common place. On the top face, where every figure stands, each pixel takes the median over only the icons in which it is still green, which recovers the bare marble and its rim. A pixel must be bare in a quarter of the icons, so a figure's own green parts don't count. The figure is cut out, stood on the top face and given a contact shadow. The prompt no longer asks FLUX for a pedestal.
- **Reuse** (`"use": <path>`): four actions have a better vanilla icon than the one they borrowed. Withdraw Nuclear Umbrella gets `guarantee_independence_obligation` (the crossed-out guarantee), Colonial Culture Change gets `change_culture`, and the two cultural-force actions get the `force_culture` crest. `wire` points them there, with nothing rendered.

## Review lessons (2026-09-27)

About 250 icons were generated in one session: era 6 techs, all treaty articles and all diplomatic actions. The owner reviewed every batch on annotated sheets and changed about one pick in eight.

- **Roughly one subject in five needed a second render, and a few needed three.** The failures repeat, so the rules for writing subjects are in `icon_prompts.py`'s docstring:
  - real insignia on vehicles;
  - words that get written out as text;
  - white surfaces lost to the cutout;
  - things FLUX won't break or fold;
  - gallows-like shapes;
  - double pedestals.
- **Two candidates were enough when the subject was right.** When the idea is right but both renders are weak, `--seeds 4` adds two more.
- **The owner's preferences:**
  - the clearer silhouette at 100 px over the more detailed one;
  - context that locates the object (a convoy on water, not on land);
  - complete sets (a full round table of chairs).
- **Small flaws on an otherwise good candidate can be retouched instead of rerolled.** A painter's signature on the background, or lettering on a flat surface, is removed in the raw render. Fill each marked pixel by interpolating between the clean pixels on either side of it in the same row, then delete the DDS and run `write` again (a retouch leaves the pick unchanged, so it must be forced); `compose` redoes any render newer than its composed file. The edited raw is in gitignored `generated_images/`, so the committed DDS is the only record. This was done for `laser_technology` ("SK" on the casing) and `satellite_communications` (a signature).
- **Check how the engine finds a category's icon before wiring it.** Diplomatic actions have two icons: `texture =` for the country menu, and `lens_toolbar_icons/<key>.dds`, loaded by key, for the lens bar. #535 wired only the first, and the lens bar kept its placeholders until the follow-up made `write` keep the lens copy. `scripting_best_practices.md` already documented this. Search it for the category before building the next one: decrees, institutions and principles may have their own second lookups.
- **Three more tools came out of the session:**
  - the `"use"` state, for a better vanilla icon;
  - insertion of a missing icon line, since the covert operations had none;
  - review sheets at 2× for 100 px categories.

### Eras 8–12 (#540)

The 104 remaining techs were done one era at a time: the owner reviewed era N while era N+1 rendered. Their review changed or rerolled about one pick in six, more than the one in eight above. The new FLUX defaults found are in the registry's docstring.

The retouching went beyond the row fill:
- **Near an object's edge, fill each row from one side only.** Interpolating toward the far side pulls in the white background or a shadow; a fill that stops a few pixels short of the edge, then a light vertical blur, left no streaks.
- **Inpaint lettering on shaded surfaces.** Where the surface under the letters is a gradient (a sun's rings, sand, a wheel hub), mask only the letter pixels and fill them with biharmonic inpainting (`skimage.restoration.inpaint_biharmonic`). Letters are the pixels well off the box's background, estimated by inpainting the whole box from its margin.
- **Some flaws are in the cutout, not the render, so fix the composed icon.** White highlights on glass came out as holes, and a glow as grey blobs. Fill enclosed alpha holes, or clear the blobs, in `final/<name>.png`, then delete the DDS and run `write`. `write` reuses a composed file that is newer than its raw.
- **A hand repaint is sometimes quicker than a reroll.** A laser turret's beam, a pale rod that read as a missile, was erased and redrawn as a glowing line.

