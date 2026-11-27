# Vanilla-style production building icons: design

2026-11-27. Status: draft for the owner's approval. The builder check is done.

## Why

A player wrote: "I would really like the production buildings and technology icons to have a visual style closer to vanilla or Tech and Rex. I've consistently felt a sense of visual disconnect." The owner thinks the technology icons are already fine, but agrees the building icons differ from vanilla's. Vanilla's are a stylized, blurry or abstract picture of the building with the produced good in the lower right. Ours are one bright scene of the whole site.

Success means that a production building added by the mod, seen in the building browser beside vanilla's, reads as part of the same set.

## What vanilla does (measured 2026-11-27)

Vanilla's production building icons have two layers inside the frame. The measurements come from the spike's `fit.py`, which matched each good's icon inside its building icon by masked least squares.

- **The good** is the good's own `goods_icons/<good>.dds`, pasted unchanged: on steel mills the difference is 0.04 RMS. Across the 13 clean fits, its 256 px canvas is scaled to a median 0.62 of the icon's side (range 0.54–0.66) and centred at about (0.67, 0.67) of the width and height. Vanilla adds no outline.
- **The backdrop** is a tight, high-angle crop of the game's own 3D building. Roof lines run diagonally, and there is no sky, no horizon, no people and no lettering. The pixels outside the good are dark and warm: CIELAB L\* mean 34.6 (sd 20.0), a\* 3.6 (sd 7.2), b\* 10.5 (sd 10.3). Brightness falls to about 0.7 of the centre's at the corners (`proto.radial`). The backdrop is slightly soft, and there is a darker patch behind the good.
- **The frame** is vanilla's bronze rim, which the pipeline already lifts (`icon_render.vanilla_template("building_icons", 256)`).
- **Buildings that share a good:** vanilla's grain farms each show their own crop (rye ears, a maize cob, millet heads, rice stalks) rather than the grain icon. Only the wheat and subsistence farms show the grain icon itself. The gold mine and gold fields share the gold bars and differ only in the backdrop. Vanilla also reuses one factory backdrop across steel, glass, paper, textiles and arms, so the good is what tells them apart.
- **Sizes:** the game draws building icons at 115, 70, 40 and 28–30 px. A design has to read at 70 px and should hold at 40 px.

## The spike (2026-11-27)

Seven buildings were each made five ways, sheeted beside their vanilla neighbours, and ranked blind by a Fable reviewer. The reviewer saw only the pictures, with the order shuffled in each row, and none of the methods. Everything is kept in `~/flux_runs/building_icons_vanilla_spike_1127/`:

- `proto.py`: the compositor, with the vanilla statistics, the regrade and the good layer;
- `m2_render.py`: the FLUX backdrop prompt;
- `symbol.py`, `hybrid.py`: the mine-marker trials;
- the sheets, `blind/` and the answer key `keys/k.json`.

| Method | Blind rank (1 = best fit; lithium, bauxite, electronics, software, robotics, nuclear, synthetic oil) | Verdict |
|---|---|---|
| **M2: new FLUX backdrop, regraded, plus the good** | 3, 1, 4, 1, 1, 1, 1 | Chosen. It has vanilla's camera. It lost where lithium read as a greenhouse and the electronics render kept a horizon. |
| M1: today's art regraded or zoomed, plus the good | best of these 2 in lithium and electronics; 2–5 elsewhere | Good only where the old art was already seen from above. Eye-level and interior shots fail. |
| M3b: a vanilla backdrop with the good swapped | 2–4 | A perfect style match, but every icon twins a vanilla one, and five of the seven fills left a ghost of the old good. Rejected. |
| M3a: a crop of a vanilla backdrop, enlarged | 4–5 | Reads as an upscaling error. Rejected. |
| Today's icons | 6 in every row | |

For mines that share a good, the owner proposed a one- or two-letter element symbol (Cr, Al) in the top left. It read well at 70 px in plain gold Garamond. The reviewer still found every lettered style foreign, since no vanilla icon carries lettering, and suggested the mine's own ore. Following the farms' precedent, **the owner chose the mine's own ore (2026-11-27)**, and noted the layer can be revisited later. The bar-on-ore hybrid was mocked up too (`hybrid.png`). Its weakness is that a grey bar on dark grey chromite tells apart only by texture.

The reviewer's fixes for the winning look:

- darker and warmer backdrops, a dark patch behind the good, some grit (the FLUX backdrops are smoother than vanilla's), and no sky or horizon;
- the mod's goods icons repainted: the circuit board, floppy disks and robot arm read as flat, front-on, saturated stickers beside vanilla's muted three-quarter views;
- no lettering, signs or figures. These were in today's art, which M2 replaces.

## Owner decisions so far (2026-11-27)

- **The method:** M2 backdrops with the good's own icon in vanilla's place. The owner leaned this way after seeing the spike sheets, which included the industry composites (a robot arm, floppy disks, an oil can, the electricity coil). The blind review agreed.
- **Large products:** the 2026-09-27 rule (a product with a fixed real-world size looks "sorta silly" as big as the building) applied to products painted into the scene. It doesn't apply to this layout. Here the good is vanilla's own crisp layer over a dimmed backdrop, which is how the owner described vanilla's icons.
- **Mines** show their own ore. The layer can be revisited later.
- **The synthetic drinks plant** shows a label-free bottle of drink.
- **The goods repaint** is in scope.

## Goals

1. Each in-scope building icon is a FLUX backdrop in vanilla's camera and grade, with its foreground in vanilla's place and size, inside vanilla's frame.
2. A mine shows its own ore. Any building with no good of its own shows the foreground named in the scope table.
3. The mod's goods icons that appear on these buildings are repainted to vanilla's goods look. The repaint also reaches the market and goods panels.
4. It is pipeline-native: entries in `icon_prompts.py`, rendered, composed, sheeted, written and wired by `generate_icons.py`. When a good's icon changes, its buildings are re-composed and rewritten.
5. The foreground is a list of layers, so revisiting the ore choice (for example a bar on its ore) is a registry edit.

## Non-goals

- Technology icons (owner: already fine).
- Wonders, system buildings, megastructures (Solar Receiver, Antimatter Engine), colony sites, company buildings, infrastructure, and the Grand Monument pictures. These keep the framed diorama. `gm_picture` shares `BUILDING_STYLE`, which must not change.
- Vanilla buildings' own icons, and the mod's buildings that keep a fitting vanilla icon.
- The player guide's text. Icons are below its level of detail. Guide and Workshop screenshots that show old icons are left for the next screenshot pass.

## Anti-goals

A result fails, even if it technically works, if:

- an icon twins a vanilla building's icon (a reused vanilla backdrop, or a vanilla good on a backdrop that could be vanilla's);
- an icon carries lettering, signs, insignia, people or a watermark;
- an icon shows sky or a horizon, or is bright and saturated next to its neighbours;
- a foreground reads as a flat sticker;
- two mines can't be told apart at 70 px.

## Scope

There are 39 buildings. The foreground column is the decided default. Entries marked *call* are mine; check them.

| Building | Makes | Foreground |
|---|---|---|
| **Mines** (all share a vanilla good or tech metals) | | the mine's own ore, a `building_foreground` part (ores below) |
| bauxite, manganese, chromium, specialty alloy metals | iron | own ore |
| nickel–cobalt | iron 60%, tech metals 40% | own ore |
| precious and minor base metals | lead, copper | own ore |
| lithium, rare earth metals, platinum group metals | tech metals | own ore |
| graphite | coal | own ore |
| phosphate, potash, industrial mineral (salt) | sulfur (the sulfur mine's methods) | own ore |
| ocean mine | iron, copper, tech metals | polymetallic nodules (*call*) |
| space mine | iron, tech metals, copper | a chunk of metallic asteroid ore (*call*) |
| **Industries** | | the good's icon |
| electrics industry (radio) | radios | vanilla `radios` |
| electrics industry (appliances) | consumer appliances | repainted mod good |
| electronic components and semiconductor industry | electronic components | repainted mod good |
| software industry | digital assets (`software.dds`) | repainted mod good |
| robotics industry | robotics (`robot.dds`) | repainted mod good |
| advanced material fabricator | advanced materials (`buckyball.dds`) | repainted mod good; a new `good` entry, since its icon predates the pipeline |
| aerospace industry | aeroplanes | vanilla `aeroplanes` |
| **Synthetics plants** | | the good's icon |
| oil, rubber, wood, sugar, meat, fruit, silk | that good | vanilla good. Silk now borrows vanilla's synthetics plant icon; it joins (*call*). |
| opium | opium (loc "Drugs") | the mod's own `goods_icons/opium.dds`: mortar, pestle, pills and a poppy head. It overrides vanilla's path, so it is in the repaint review. |
| biomass | grain | vanilla `grain` |
| drinks | coffee, tea, wine | a label-free glass bottle of drink, a `building_foreground` part (owner, 2026-11-27). Vanilla's `wine` (a bottle with grapes) reads as a vineyard, and `liquor` carries "VODKA". FLUX writes on labels, so zoom the picks. |
| `building_synthetics_plant_coal` (a direct air capture plant; no good) | nothing | a heap of pale grey chalky calcium carbonate pellets, what the Carbon Engineering process yields (*call*; a `building_foreground` part). Not white: parts render on white, and the cut-out loses white surfaces. The backdrop must not look like an emitter: a low hall with a wall of fans. |
| **Clean power** (nuclear, fusion, renewable, hydro) | electricity | vanilla `electricity`. The backdrop tells them apart, as with the gold mine and gold fields (*call*). If two of them twin at 70 px, raise it at review. |
| **Tourism** (tourism industry, space resort) | tourism | repainted mod good |

**Goods to repaint (7):** `consumer_appliances`, `electronic_components`, `software`, `robot`, `tourism`, `opium`, and the new `buckyball` entry. A current icon that already fits beside vanilla's goods keeps its seed (`opium` may). Each is a `good` entry in `icon_prompts.py`, with its subject rewritten to name a three-quarter view from slightly above, muted colours and an angled object, for example the board seen at an angle and not face-on. `tech_metals` (the lavender fringe the reviewer saw) no longer appears on any building; it is a follow-up.

**Proposed ores** (for the first render; review decides). The bar is that the fifteen heaps tell apart at 70 px, so dark ores need a distinct form or accent:

| Mine | Ore |
|---|---|
| bauxite | rust-red earthy lumps |
| manganese | sooty black lumps with pink rhodochrosite crystals |
| chromium | black chromite with a brown metallic sheen |
| specialty alloy metals | dark wolframite blades with bright grey molybdenite flakes |
| nickel–cobalt | apple-green garnierite |
| precious and minor base metals | silvery galena cubes with blue azurite |
| lithium | pale pink and white spodumene crystals |
| rare earth metals | honey-brown monazite |
| platinum group metals | grey nuggets in dark rock |
| graphite | black flakes with a lead-grey shine |
| phosphate | cream-tan pebbles |
| potash | orange-pink sylvite |
| salt | white cubic halite |
| ocean mine | knobbly black nodules |
| space mine | pitted iron-nickel chunk |

## Design

### Compose mode `framed_good` (icon_render.py)

The steps follow the spike's `proto.compose` and `regrade`:

1. **Backdrop.** Resize the FLUX raw to 256 px (premultiplied). Regrade it with a Reinhard transfer in CIELAB to the vanilla backdrop statistics, then apply vanilla's radial falloff (the ratio of vanilla's normalized profile to the render's own, clipped to 0.45–1.25) and soften it with a 0.7 px blur.
   - The statistics are measured at runtime from the vanilla folder, as `vanilla_template` is: the clean-fit buildings, inside the frame, with the good masked out. Cache them per process.
   - The fit table (building, good, scale, x, y) is data. The 13 clean fits from `fit.py` can be listed in code, or refitted when the cache is built.
2. **The reviewer's fixes,** as category spec settings tuned on one sheet against vanilla neighbours:
   - a darkness and warmth bias on the transfer target;
   - a soft dark patch behind the foreground. Measure vanilla's luminance in a ring around the good against the rest of the backdrop.
   - grit, either fine luminance noise or high-pass texture sampled from vanilla backdrops.
3. **Foreground layers,** in order. A good's layer is its goods DDS canvas: the mod's file if it exists, else vanilla's, read from the good's `texture` in `common/goods`. It is scaled to 0.62 of the side and centred at (0.67, 0.67), with a drop shadow (offset (−3, 4), blur 5, opacity 0.6 at 256 px) and no outline.
   - A part's layer is its composed final, placed by the same canvas rule.
   - A part's opaque share differs from a good's: the ore heaps filled less. So scale a part by its alpha bounding box to vanilla goods' median bounding box.
   - A layer may carry its own `scale` and `at`, for a later hybrid.
4. **Frame,** as `compose_framed` blends it.

### Registry (icon_prompts.py)

- **A new category, `production_building`:** folder `building_icons`, size 256, mode `framed_good`, `entity_dir` `common/buildings`, field `icon`, and style `BACKDROP_STYLE` (below). The 39 entries move out of `building` into it.
  - Each entry is `{"subject": <what is seen from above>, "seed": None, "foreground": [{"good": "<goods key>"} | {"part": "building_foreground/<key>"}, ...]}`.
  - A new category is used, not per-entry overrides, because the ~110 other `building` entries and `gm_picture` keep `BUILDING_STYLE` and `framed`, and their accepted prompts must not change, since an edited prompt re-renders.
  - `--validate` and `test_registry_matches_the_mod` must accept two categories over `common/buildings`. A building in both is an error.
- **A `building_foreground` part category** (ores, the air-capture plant's pellets, the drinks plant's bottle): the `good` category's layout (cutout, fill 0.90, `PAINTED`, graded toward `goods_icons`). It is reviewed, never written.
- **`BACKDROP_STYLE`**, from the spike: `"high-angle oblique close-up looking down onto {subject}, the roofs run diagonally across the frame and fill it edge to edge, no sky, no horizon, detailed 3D rendered miniature model as in a strategy game's city view, dim dusk light, deep soft shadows, muted desaturated grey and brown palette"`.
  - CLIP truncates it at 77 tokens: the spike lost the palette clause on every prompt. T5 still sees the whole prompt, and the regrade sets the palette anyway, but keep the camera words first and the subjects short.
  - A subject describes what is seen from above (roofs, ponds, pits, plant), not a facade.

### Dependencies (generate_icons.py)

- A `production_building` final depends on its raw and on each foreground layer: the good's DDS bytes, or the part's pick and its final.
- `compose`'s newer-than check and `written.json` must count those layers, so a repainted good, or a re-picked ore, recomposes and rewrites the building.
- Work order:
  1. the goods;
  2. a pilot sheet, sent to the owner before the rest is rendered: four industries (robotics, software, aerospace, nuclear) with their repainted goods on M2 backdrops and the grade fixes (*call*);
  3. the parts;
  4. the buildings.

### Review

- Sheets: the existing stage (now | 3 vanilla neighbours || candidates), plus a game-size row (70 and 40 px) and one sheet of all fifteen mines side by side at 70 and 40 px. These follow the owner's sheet preferences: picks boxed in gold, and each sheet sent as it is made.
- Pick rules:
  - re-render a seed that shows sky, a horizon, lettering, signs, people or insignia;
  - zoom the bottom 300 rows of every raw for watermarks;
  - zoom the picks for lettering.

## Constraints

- **GPU:** a running Victoria 3 holds about 9.4 GB of the 10 GB.
  - Renders gate on two readings under 3 GB, one FLUX job at a time (the spike's `m2_gated.sh`). A render takes about 30 s once warm.
  - Expect about 180 renders at 3 seeds (39 backdrops, 17 parts, 7 goods), about 1.5 hours.
- **Where the work runs:** `.venv-img` lives in the image worktree `~/src/vic3te-icon-batch6` (run it with `env -u PYTHONPATH`, and export `FLUX_MODEL_DIR` and `HF_HUB_OFFLINE=1`). Raws and finals live in that worktree's `generated_images/icons/`.
- **Output and checks:** DDS stays uncompressed in vanilla's format (the existing `write`). CI runs `test_icon_pipeline.py` and `--validate`. Before pushing a replacement, grep `test_*.py` for each building's key, since a system test can pin an icon.
- **No game launch needed.** One look at the building browser in game goes on the play-test list; in-game checks don't gate.
- **The PR body's player-guide line:** "below the guide's level of detail".

## Left to the builder

- The grade fixes' values: darkness, warmth, the dark patch and grit.
- How a part is scaled to match a good.
- How `written.json` records the layers.
- Each backdrop subject, and the ore subjects past the proposals.
- How to split the work into PRs.

## Calls made in this document (owner to check)

- Ocean mine: nodules. Space mine: an asteroid ore chunk.
- The silk synthetics plant joins.
- The direct air capture plant shows pale grey calcium carbonate pellets.
- The opium plant shows the mod's Drugs icon, which joins the repaint review.
- A pilot sheet of four industries goes to the owner before the full render.
- The clean power plants keep the electricity good, and their backdrops tell them apart.
- `tech_metals`' fringe is a follow-up.
- Megastructures are out of scope.
- The ore proposals.
