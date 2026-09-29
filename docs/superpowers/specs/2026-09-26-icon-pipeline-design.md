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

**Shared by design — not placeholders.** Vanilla shares these too: state traits (`resources_ore.dds`), diplomatic plays (`unification.dds` for every unify/leadership play), ship modifications, company `basic_*` icons, ship types, static modifier icons, PM-group textures, building backgrounds, message textures. Mod `gui/` references to `gfx/interface/icons/` are UI glyphs (warning, checkmark, filter icons), also fine. Journal entry icons were on this list until 2026-09-28: vanilla shares its generic `event_*.dds` across ~150 entries, but the mod's 26 shared five icons between them (nine on the gears), and the owner asked for their own (see "Journal entries").

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

**Priority:** techs, treaty articles, decrees, institutions, principles, ideologies, mobilization options, IG traits, diplomatic actions, then buildings once their allowlist entries are triaged. The second batch (2026-09-28) followed the owner's own order; see its section below.

## Runtime (RTX 3080 10 GB, 39 GB RAM, WSL2)

- **Offload:** `enable_model_cpu_offload` runs out of memory, because the transformer is 24 GB in bf16. `enable_sequential_cpu_offload` works: ~30 s per 1024² image once warm, 2–4 min for the first.
- **Other CPU work slows it down:** sequential offload streams the 24 GB transformer through the CPU on every step, so FLUX needs the CPU and memory bandwidth as much as the GPU. On 2026-09-28 another session's heavy CPU job pushed a render to ~300 s per step (normal is 8–16). Its main thread sat at 100%, the GPU at 1%, with no page faults and no disk reads. Restarted once that job had eased, it ran at 55 s per image. If the warm `s/it` figures are far above 20, look for a competing job before anything else. `py-spy` can't attach to a running process here (`ptrace_scope` is 1), but `py-spy record -- <command>` can profile one it starts.
- **Queueing a second render:** a `while pgrep -f "<pattern>"` wait inside `bash -c` matches its own command line and never ends. Chain the renders with `&&` in one command instead.
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

## Building slice (2026-09-27)

**Triage.** 316 mod-added buildings borrowed an icon on 2026-09-27. The owner chose the first batch:

| Group | Count | Borrowed | Decision |
|---|---|---|---|
| Wonders | 34 | generic vanilla art: dams on `building_railway`, towers on `urban_center` | generate: vanilla gives each monument its own icon, and FLUX knows the landmarks |
| System buildings | 11 | Grand Monument, Settlement Authority, SR Hub and Silo, UN HQ and Power Bloc HQ on `building_government_administration`; Military Base, Youth Centers, three sci-fi power buildings | generate |
| Industry variants | 9 | eight synthetics-plant variants and the radio industry on **goods** icons, which have no frame | generate 8; Synthetic Clothes keeps vanilla's synthetics plant |
| Mines | 14 | the five vanilla mine icons | generate, each ore named by colour and form |
| Construction Site | 1 | `construction_camp` | keep |
| Company buildings | 247 | 190 on their company's logo, by design (`docs/vanilla/vanilla_company_buildings_reference.md`); 45 `building_generic_*` on `skyscraper.dds`; 12 on `basic_*` company icons | out of scope for this batch |

Two company-logo problems turned up and belong to a logo pass, not this one: 76 of the mod's own company logos are the `gen_placeholder_company_icons.py` "PLACEHOLDER" card, which the flagship building shows too, and five flagships sit on another company's logo (DuPont on Pfizer's, Shell on ASML's, IG Farben on SAP's, JSR on Fanuc's, Sibur on Gazprom's; `/duplicate-images` flags them).

**Layout.** The prototype's `framed` style is unchanged: the render fills the frame lifted from vanilla, so the cutout rules for white surfaces and glows don't apply. Subjects follow vanilla's two building layouts. Monuments are the landmark alone. Industrial buildings put the plant behind and its product large in the foreground (vanilla's iron mine has an ingot, its synthetics plant two vials), which is what tells fourteen mines apart at 256 px.

**Wiring.** Building icons are read only from `icon =` (`BuildingType.GetIcon` in `building_browser_panel.gui`); there is no second lookup like the lens toolbar. 28 of the targets are `REPLACE_OR_CREATE:` definitions in `extra_buildings.txt`, so `wire` and `--validate` now match that prefix and capture the bare key. `REPLACE:` and `INJECT:` still don't match: they change a vanilla building, whose own art stays.

**Review (2026-09-27).** 67 icons, first render at 2 seeds; the owner accepted the first 34 wonder picks unchanged. Of the rest, 18 needed another render:

- **A product in front of a plant must have no fixed size.** Heaps of ore, grain or crates sit fine at building scale. A walkie-talkie, a jar, bottles or a chrome bar come out as big as the building, and photographic beside vanilla's painted scenes. The owner's rule: drop them (nine subjects).
- **The painted look has to be asked for in the subject** (", loosely hand-painted with visible brush strokes"); changing the category's style would re-render every approved icon. It also brings painters' signatures and white canvas edges into the corners. The frame covers the bottom few percent, so check the composed icon, not the raw render, before retouching.
- **The picture has to say what the building does.** A carbon-capture plant drawn as a power station "looks more like an emitter". FLUX adds chimneys to anything called a plant or given columns, whatever the prompt says against them; a low hall "whose whole front is a wall of big round black fans" came out clean.
- **FLUX won't count sides or draw an L.** Eight Pentagon renders came out octagonal, and LIGO's arms parallel, crossed, single or tripled, whatever the subject said. Image-to-image from a drawn sketch does not help: FLUX.1-schnell either returns a flat sketch unchanged or loses its shape (the starting noise level is `floor(steps × strength) / steps`, and the jump comes between 0.69 and 0.75). What worked was **repairing a good render geometrically, then repainting it lightly**. For the Pentagon: mark the octagon's eight roof corners, fit a homography from a regular octagon to them, warp radially on that ground plane into a regular pentagon (concentric rings stay concentric), then run image-to-image at strength 0.5–0.56 with 32 steps to blend the seams (0.62 wrote lettering on a facade). For LIGO, whose 4 km arms have to read as 4 km: take a render with one arm receding to the horizon, read it as flat ground under a pitched camera (horizon row, focal length), rotate each half of the ground ±45° about the corner and project it back, so the arm becomes a right-angled V with a level horizon, then polish at strength 0.5. Shearing the image instead narrows the V or smears it. The result is installed as a new seed's raw with a matching `.prompt.txt`; the committed DDS is the only record.
- **Wonders mostly came right first time**, as FLUX knows the landmarks. The misses were a monument read as a rocket (Aswan's lotus tower), a detector hall read as a pit (LHC), a floating disc (Kenyatta), and lettering on a podium, plinth or slab (Sydney, Statue of Unity, LIGO), retouched or avoided.

## Second batch: the smaller categories (2026-09-28)

The owner's order: mobilization options, ideologies, decrees, the four remaining laws, institutions, IG traits, the combined-arms character traits, harvest conditions and the one power bloc identity. Each category renders while the previous one is reviewed. `~/flux_runs/run_cat.sh <log> <category> <seeds> <keys...>` queues one category's render and compose.

Every category below is read only from its entity's icon field; the engine has no second lookup like the lens bar. The GUI functions are `MobilizationOption.GetTexture`, `Ideology.GetTexture`, `Decree.GetTexture`, `Law.GetTexture` (amendments show their parent's icon), `Institution.GetIcon`, `InterestGroupTrait.GetTexture`, `CharacterTrait.GetTexture`, `HarvestConditionType.GetIcon` and `PowerBlocIdentity.GetIcon`.

| Category | Count | Layout | Notes |
|---|---|---|---|
| Mobilization options | 27 | `emboss`, with a colour gradient | 14 were on `machinegunners.dds` |
| Ideologies | 3 IG, 6 leader | `emboss_medallion` | `leader_ideology` is a second category (silver on teal, `ideology_leader/`); the 24 `custom_religion_*` variants keep their base icon, as vanilla's do |
| Decrees | 15 | `medallion`, with the disc colour set and the two-point grade | 13 were on `road_maintenance` |
| Laws | 4 | `tinted` (new) | penal labor camps, private military contractors, littoral defense, auxiliary fleet |
| Institutions | 17 | `tinted` | `icon`; the `background_texture` strips came later (below) |
| IG traits | 15 | `card` (new), one category per approval slot | the traditionalist trio is the Devout IG's own set and stays |
| Character traits | 6 | `card` | the combined-arms traits are `type = condition`: the condition card, turned gold |
| Harvest conditions | 3 | `framed` | the round rim lifts like the building frame |
| Power bloc identity | 1 | `cutout` | Diplomatic Framework |

**Silhouettes.** The first mobilization renders showed two failures of the plain silhouette prompt. Outline-only parts (an envelope, a coiled cord) embossed to hairlines, and a locomotive ran off the canvas, which the emboss cut square. The shared `SILHOUETTE` style now asks for thick chunky shapes with a few bold white cut-outs, no outlines, and the whole object inside a wide margin. The emboss bevels every edge, so a subject still has to avoid thin parts: a beam, an antenna, radio waves. Wide objects in side view come out thin, because the fit is to the longer side; a cargo plane climbing at an angle fills more of the icon than one seen level.

**Colour is fitted, not picked.** Vanilla's copper, gold and silver shift in hue from top to bottom, not just in brightness. Mobilization copper runs pinkish (181,128,106) to orange-brown (148,73,38). `embossed()` takes an optional `color_bottom` and blends a render in each colour row by row; the style is linear in its colour, so that is exact. The two colours are fitted by rendering a few candidates, measuring the median of the top and bottom quarters of the shape, scaling each colour by target over measured, and repeating until it settles (three or four rounds). The emboss's lighting has a median of about 0.6, so a fitted channel can exceed 255; the style multiplies before it clips. The same fit set the ideology gold and silver, and the IG-trait and character-trait pictograms (one colour pair per card colour, since vanilla tints the pictogram towards its card).

**Fit the size to vanilla too.** Ideology symbols at `fill` 0.60 spanned 123 of 220 px; vanilla's median is 156, so `fill` is 0.75.

**A median disc can be wrong.** The decree disc, sampled from the folder median just inside the ring, came out grey-green (69,89,84) where vanilla's is near-black teal (28,42,42). Decree objects crowd that band, so the median there is part object. A medallion category can now set `disc = (centre, edge)`. Decrees use colours measured on vanilla's bare disc pixels.

**`tinted`: one metal, from vanilla.** Vanilla law and institution icons are painted objects in a single tan-bronze palette. `tone_ramp()` reads the folder's luminance distribution and its median colour at each luminance. `compose_tinted()` cuts the render out, matches its luminance to that distribution percentile for percentile, and maps each pixel through the ramp. Shading and brush strokes survive while every hue goes. Institutions take the ramp from `law_icons`, because `institution_icons` also holds the dark disc the GUI draws them over.

**`card`: a blank card lifted from vanilla.** IG traits (124×162) and character traits (240×320) are cards whose frame colour carries meaning: the approval slot (gold loyal, green happy, rust unhappy) or the trait type (pink condition, grey skill, blue personality). Frame colours are sampled 3 px inside the card's left edge at mid-height. `card_template()` works from the folder's cards with that frame colour. On each card a pixel is bare unless it lies within 3 px of dark (pictograms have light highlights and edges), except the card's own vines: pixels in the top or bottom band that are dark on at least 90% of cards.
- Outside a central ellipse, a pixel is the median over the cards on which it is bare, which keeps the frame, corner ornaments and edge shadow.
- Inside it, the Gaussian-weighted average of every bare observation on every card (normalized convolution): a smooth gradient in the card's colours, like vanilla's middles, which the new pictogram mostly covers.

Three earlier versions failed:
- A median over bare cards in the middle kept ghosts of the pictograms, plus fragments along the bottom that read as text.
- Biharmonic inpainting of the cleanest card overshot into white, blue and black blobs.
- Filling from the plain median pulled the pictograms' dark in.

The pictogram's `fill` is (width, height) of the card. Vanilla's span about 0.8 × 0.7; the first try at 0.7 × 0.6 looked small.

**What FLUX added unasked** (see also the registry docstring):
- A subject naming a device wrote its name: "radio jammer" drew JAMMER.
- A camera came with a brand ("Catear").
- Gold coins came with $ signs, and a customs gate's posts with numbered plates.
- A laser turret read as a camera or a searchlight until it fired a beam at a target.
- A landing craft read as a ferry, a flight simulator as a lunar lander, a parachute as vanilla's hot-air balloon, and a night-vision helmet seen from the front as a face.

**Retouching, second batch.** Three small tools live in `~/flux_runs/tools/`. Each keeps the untouched raw in `~/flux_runs/originals/`, and after a retouch the DDS is deleted and written again.
- **`fill_white_holes.py`.** FLUX sometimes draws a silhouette part as white inside a black outline (an envelope, a toaster, a capsule window, a tank's front plate), and the emboss cuts it out. The tool fills each enclosed white region after shrinking it by `--groove` px, so the part turns solid and keeps an engraved line where its outline was. `--min-area` spares wheel rings and slots. `--close` bridges small outline gaps. A region open to the background on a whole side is not enclosed: fill that polygon by hand.
- **`inpaint_boxes.py`.** Paints out hull numbers, emblems, truck lettering and painters' signatures, filling each box biharmonically from a margin. Keep the margin off neighbouring surfaces, or white background or dark trim bleeds in.
- **Mirroring.** Promote Tourism's camera had a second lens ring drawn over the first. Where the ring crossed the lens, the lens's own mirror image about its centre restored it; elsewhere, the leather was mirrored from the other side of the symmetric camera body. Soft-edged masks hide the seams, and the mask must cover the old ring's rim or a ghost of it shows.
- **Stray specks in a silhouette.** Dark connected parts under 1% of the largest one can be whitened in the raw (Fire Support).

**Pairs share a symbol.** An ideology held by both an IG and a leader (Multiculturalist, Anti-Colonialist) uses one subject in both categories. The same prompt and seed render the same picture, so the two looks match.

### In-game review (2026-09-28)

The owner compared the merged batch (#561) with vanilla in game and asked for four changes.
- **Institutions were too big.** Vanilla's objects span 0.68–0.80 of the side (median 0.775), and `institution_icon_bg`, the disc the panel draws them over, spans 0.80. At `fill` 0.9 ours spilled past the disc. They are now at 0.78. Laws were left alone (vanilla 0.877, ours 0.9). This is the second category sized by eye and then corrected (ideology symbols were the first): measure vanilla's opaque bounding boxes before choosing `fill`.
- **Decrees were dull.** The FLUX renders are more vivid than vanilla: Tax Breaks' cut-out had a median saturation of 0.70 and value of 0.93. The old grade scaled every tone by the same factor to hit one median (from `invention_icons`), so it pulled the highlights down with everything else. `grade="spread"` measures vanilla's decree objects on their disc (pixels inside the ring more than 45 RGB from the disc colour). It then moves the 50th and 90th percentiles of saturation and value toward theirs, along a piecewise-linear curve through (0,0) and (1,1), at strength 0.8 with gains capped at 1.6. The table gives medians of per-icon values; the target itself is pooled over all of vanilla's object pixels (V p90 0.91), so it reads a little higher:

  | | S p50 | S p90 | V p50 | V p90 |
  |---|---|---|---|---|
  | vanilla | 0.40 | 0.62 | 0.65 | 0.88 |
  | before | 0.36 | 0.46 | 0.57 | 0.71 |
  | after | 0.44 | 0.68 | 0.65 | 0.91 |
- **The spread grade needs detail at the top.** The Diplomatic Framework's parchment rendered clipped near white (V p50 0.98, p90 0.99), and the old grade flattened it to one beige at V 0.51. Stretching that clipped range made it blotchy, so the category takes the plain grade at `grade_strength` 0.5 instead of 0.7. Mean luminance went from 103 to 125; vanilla's identities range from 71 to 115.
- **The pink card said "bad trait".** Vanilla's condition card marks bad traits (alcoholic, cancer). The combined-arms traits keep the condition template but turn it with `recolor = (45, 1.4)`: hue +45°, saturation ×1.4, a gold no vanilla type uses. The pictogram's fitted tint turns with the card.

**Compose keeps a final that is newer than its raw.** A layout or spec change therefore recomposes nothing. Move the category's `final/<category>__*` files aside, compose, then delete the DDS files and `write`.

### Institution strips (2026-09-28)

After #561 the owner asked for the institutions' `background_texture` strips too. Those were the last borrowed art on institutions: all 17 had been on vanilla's seven, 7 of them on `schools.dds`. Category `institution_strip`, layout `strip`.

**What the panel shows.** A strip is 3500×220, but `politics_panel_institutions.gui` draws it with `fittype = centercrop` into a box 600 px wide by the row's height: it starts 70 px into the 520 px row and runs 150 px past its right edge, where the panel clips it. At a row height of 150–200 px, only about x 1300–2000 of the strip shows. `institution_image_mask.dds` (`Corneredstretched`, `alphamultiply`) fades it in from the left and draws the middle at about half opacity (alpha ~122). Vanilla paints its figures in that band and fills the rest with a dim, blurred continuation. The geometry comes from the GUI file, not from the game; the in-game check confirms it.

**The layout.**
- **Render.** FLUX renders at 1792×448 (4:1, `gen_size`), which scales to 880×220 and is centred at x 1700 (`STRIP_CENTRE`).
- **Sides.** The rest of the strip is the scene mirrored outward, blended to a blur (σ 3×14 px) over 60 px and dimmed by up to 40%. The sides only show on a short row, as vanilla's do.
- **Grade.** The scene takes the two-point grade toward vanilla's strips, measured in the visible band (`strip_grade_target`).
- **Review sheet.** `strip_sheet()` shows each candidate as the panel would, roughly: the 600-px box at a row height of 180, the nine-sliced mask, clipped at 450 px. The whole strip sits underneath. Judge picks there: lettering under the left fade doesn't show.

**Framing.** The first style asked for a "wide cinematic composition, the figures seen from the waist up". It drew a symmetric room with two small officers posing at the viewer, and a map table set with dozens of markers. Vanilla's strips are candid close-ups, figures cropped at the chest and busy with something. The style now asks for exactly that ("candid close-up, the figures large and cropped at the chest in the middle of the frame, seen from the side busy at their work"). Subjects follow the event-picture rules: period props, no signs, no flags, and each scene set in its institution's era.

**What FLUX lettered anyway:**
- Grain sacks (International Aid).
- A framed certificate on a studio wall (Propaganda).
- A sign on a tent (Refugee Affairs).
- A maker's plate on a machine (Science).

Each pick keeps its lettering at an edge the panel crops or fades.

**Format.** The strips are block-compressed, BC7_UNORM_SRGB, through texconv (`convert_event_image.convert_image`, as event pictures are): 1.03 MB with 12 mips, against 4.1 MB for vanilla's uncompressed ones. The round trip averages 0.28/255 of error. The sRGB type is carried over from event pictures; vanilla's strips are untyped BGRA. If the panel samples them brighter or darker than the sheet shows, try `BC7_UNORM` without `-srgb`. A category opts in with `dds_format`, and `root` puts it outside `gfx/interface/icons/`. `texconv.exe` is gitignored: copy it from a checkout that has one or let `ensure_texconv()` download it.

**Runtime.** Renders take 27–38 s. One stalled for 10 minutes on a single CPU core with the transformer in RAM and nothing on the GPU; a rerun took 34 s. If a render takes minutes, kill it and rerun.

## Journal entries (2026-09-28)

After the institution strips the owner asked for the journal entries' icons. 26 of the mod's 27 entries were on borrowed art (the nine Space Race milestones on vanilla's gears, three on the newspaper, three on the portrait bust, two on the flag, two on a building icon). `je_nuclear_program` keeps its hand-made `mushroom_cloud.dds` (1024 px, uncompressed, no mips, 4 MB: the outlier in the folder), and `je_unite_the_nations` is a vanilla entry the mod `REPLACE:`s, which `wire` does not match.

**What the game draws.** `JournalEntry.GetIcon` is read in three places and there is no second lookup like the lens bar's: the journal list (`journal.gui`, 40 px), the entry panel (`journal_entry.gui`, 100 px) and the entry's tooltip. The panel draws the icon at 100 px over `round_frame_dec.dds` at 120 px. That frame is an opaque dark disc (about 26,20,21) with a gold ring at 0.75–0.84 of its radius, out to a flourish. A square icon covers the ring and leaves only the flourish at the sides (the Strategic Reserve's building art did), while a disc smaller than the ring leaves the ring showing, as vanilla's cut-out icons do. `panel_preview()` draws the frame from the game's own texture, so a sheet shows what the panel will.

**Layout.** Vanilla's 17 `event_icons/*.dds` are painted single objects on transparency, 150 px (two are 148), uncompressed with 8 mips. Measured: objects span 0.79–0.98 of the side (median 0.89), median saturation 0.45 and value 0.57. Category `journal_entry` is the existing `cutout` layout at `size=150, fill=0.89`, written to `event_icons/<je_key>.dds` beside vanilla's names (the keys are unique `je_*`).

**The Space Race backdrop (`backed`).** The nine milestones are one family, so category `journal_entry_space` lays each craft over one shared painted disc.
- **The disc.** `compose_backdrop` crops a full-bleed scene to a soft-edged disc of 0.86 of the canvas (inside the frame's ring), darkens its rim with a gentle vignette and draws a thin steel-blue edge so a dark disc reads on the dark panel. It is not graded toward the folder's saturation and value: a night sky lifted to vanilla's brightness stops being one. Craft take the folder's grade as any cutout does.
- **The subject.** It renders on white and is cut out as usual; space comes only from the backdrop, at `fill=0.66` so the disc shows around it. Putting stars in a subject would give rembg a starfield to cut through.
- **Where the backdrop lives.** It is `backdrop=dict(prompt, seeds, seed)` on the category, not an `ICONS` entry (`check()` would call it an unknown entity). `--stage render --only _backdrop` renders its candidates on their own, so it can be picked first; the sheet stage draws each candidate bare and under four sample craft. Composed finals live in `final/<category>_bd<seed>/`, so a new pick never reuses stale ones, and `write` refuses until the seed is picked and records the backdrop's seed and prompt in the manifest, so a new pick rewrites all nine DDS files. `--validate` flags a backdrop with no prompt, a bad seed, or an accepted icon over an unpicked one.
- **The pick.** Four candidates: a flat nebula with a bright horizon, a calm one with a hint of planet, a nebula with a bright star, and a star field with a planet limb rising at the lower right. The last (s3) is the default: the limb reads as Earth at both 100 and 40 px, and it is the only one that gives the family a place. s1, the calmest, is the alternative if the limb competes with a craft.

**What review found (the 26 picks are proposed, not yet owner-reviewed).** Each row of the sheets shows the current icon, my pick in a gold box and the other seeds, all drawn as the panel draws them (100 px in the frame, and 40 px). `~/flux_runs/for_owner/journal_plain_N.png`, `journal_space_N.png` and `journal_space_backdrops.png`.
- **Canvas-edge crops.** Two first choices had a straight vertical edge where FLUX had run out of canvas (the bull of banking s0, a crate of strategic reserve s0). The cut-out keeps the edge; the tell is a flat side on an object that should curve.
- **Lettering on devices.** A blade (covert s1), the palm plate of a robotic hand (human augmentation s1) and a module face (its s2, "TEB") all carried glyphs. Two more seeds gave a clean hand (s3). Mars s0's rock also had small snowflake-like white specks.
- **Painted cast shadows.** FLUX paints a shadow on its white ground, and the cut-out keeps it as an opaque grey wedge (Mars s2, beside the rock). The fix is in the raw: whiten the low-saturation pixels in that corner (the original is kept, and the registry says so).
- **The folder grade on grey objects.** `grade` scales saturation by (target / median)^strength, which is ~9x at 0.7 for a near-grey object: the orbital satellite's silver sphere came out copper. The space category sets `grade_strength=0.4`; nothing else in the nine changes visibly. The plain category keeps 0.7, at which its picks were judged.
- **Subjects that changed after the first sheet.** Moon base: three identical round windows read as staring eyes, so it became one lit dome with a hatch. Mars: a box lander on legs read as a television, so it became a cone-shaped capsule. Orbital: both seeds were bronze, so it got four.
- **Meaning at a glance.** A thermometer standing in an ice block reads as cold (global warming s1); the separate cube (s0) reads as melting. A pith helmet drawn hollow side up reads as an empty hood (colonial s1).

**Still open.** The owner's review of the picks and the backdrop. The in-game check: whether the gold ring of the round frame shows around the Space Race discs as the preview says, and the 40 px list. The Strategic Reserve player-guide screenshot (`docs/player_guide/images/strategic_reserve.png`) shows the old building icon in its header and needs retaking in game; no other guide screenshot includes a journal icon.

## UN GUI icons (2026-09-28)

The UN GUI pass (#567, `docs/systems/un_gui_placeholder_icons.md`) draws 43 new icons with vanilla placeholders: membership states, authority tiers, the crisis alert and the Security Council's vacant seat in the overview, the eleven agencies, and the eighteen resolution topics in the session strip. Plus the pie pair. None belongs to a game entity; each is a `texture =` line in a `.gui` file.

**GUI-hosted categories.** A category with `gui` in its spec has no `entity_dir`. Each entry names the placeholder it replaces (`now`, shown as "current" on the sheet), its key is the file name the doc proposes, and its DDS goes to `un_icons/`, a folder vanilla lacks. So `grade_folder` and `neighbours` point at `alert_icons`, the nearest painted folder. `check()` never calls such a key unknown, and `wire` prints a reminder instead of editing: the `.gui` is edited by hand on the GUI branch.

**Legibility decides the layout.** These show at 32–40 px. At 32 px vanilla's own painted alert icons are blobs, and only the flat marks (check, cross, plus, the warning "!") still read. The owner's rule for the set: lean strongly toward simple, easy-to-recognize options. So:
- **Membership, the crisis alert and the vacant seat are derived icons.** They are one FLUX emblem (a gold laurel wreath around a blue globe), picked once, under marks. Colour means the membership's benefits apply, and grey means they do not; the mark names the state. Member: a green check. Permanent member: the check plus a drawn gold star. Can join: grey with a green plus. Cannot join: grey with a red cross. Suspended with the seat carried by the overlord: colour with a pause mark. Suspended: grey with a pause mark. No UN: faint grey with no mark. Crisis: colour with vanilla's warning. The vacant seat is UN-blue cloth with the emblem as a pale watermark, 3:2 like a flag.
- **Vanilla's `paused.dds` is gold bars with no ground.** On a gold emblem at 32 px it read as ingots, so the pause mark is drawn: amber bars on a small dark badge. Every mark gets a dark outline so it reads over the icon and the panel.
- **The agencies and the topics that are no agency's share one drawn disc** (`draw_disc`): UN-blue enamel under a gold rim, the same under every symbol, where a FLUX backdrop would vary. It is a `backed` category whose `backdrop` is `drawn` (colours) rather than rendered. Symbols are warm or light for contrast with the blue.
- **A convention topic is its agency's icon under a scroll badge** (a `part`). Ten topics cost one render. The doc's extras for two of them (a broken missile under the atom, a thermometer by the leaf) were dropped, since FLUX will not break things and a second object is noise at 40 px.
- **Condemnation and expulsion carry a vanilla mark too.** A sword with the red cross; the permanent member's gold star with vanilla's red down arrow.
- **Tiers stay plain cut-outs.** A broken stump, two columns, three under a lintel, a silver portico, a gold temple front: the silhouette and the metal carry the climb. `grade_strength=0.4` keeps the silver from turning copper.

**Derived entries** (`"from": "<cat>/<key>"`) have no render of their own. The base is the source's composed icon, then an optional `tint` (`grey`, `faint`), then an optional `layout` (`flag` with a `size`), then `marks`. A mark is `{"icon": <vanilla .dds>}`, `{"part": "<cat>/<key>"}` or `{"draw": "star"|"pause"}`, with `at` (its centre, as shares of the side) and `scale`. The sheet shows one candidate per candidate of the source, so picking the emblem is done among the seven membership icons. `write` writes a derived icon once its source and every part it uses are picked, and records the recipe in the manifest, so an edited mark rewrites it. A `part` category (the emblem, the scroll badge) is reviewed like any other and never written.

**Pies.** `gen_ch_model_pie_textures.py` writes `un_icons/pie_members.dds` (UN blue, `#5b92e5`) and `pie_rest.dds` (grey, `#8c8474`) in the Cultural Hegemony pie's format. Checked with the dataviz validator against the dark panel: ΔE 16.8 normal and 16.9 protan, and both clear 3:1 contrast. The grey fails only the chroma floor, as intended for the part that is not the subject.

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

