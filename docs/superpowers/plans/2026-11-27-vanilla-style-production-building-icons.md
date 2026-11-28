# Vanilla-style Production Building Icons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the mod's 39 production buildings icons in vanilla's two-layer look: a FLUX backdrop in vanilla's camera and measured grade, with the good's icon (or the mine's own ore) in vanilla's place and size, inside vanilla's frame. Repaint the 7 mod goods icons they show.

**Architecture:** There are four code changes in the existing icon pipeline:
- a registry category `production_building` (mode `framed_good`) and a part category `building_foreground` in `icon_prompts.py`;
- the regrade and layer compositor in `icon_render.py`;
- `generate_icons.py` resolving each entry's foreground layers and treating them as inputs to compose and write;
- then render and review rounds, each gated on the owner's picks.

**Tech Stack:** Python 3.12, numpy, Pillow, FLUX.1-schnell via diffusers (render only, in `.venv-img`), unittest/pytest.

**Spec:** `docs/superpowers/specs/2026-11-27-vanilla-style-production-building-icons-design.md`. The spike it rests on is in `~/flux_runs/building_icons_vanilla_spike_1127/` (`proto.py` holds every measured constant below).

## Global Constraints

- The good's canvas is scaled to **0.62** of the icon's side and centred at **(0.67, 0.67)**, with no outline.
- The drop shadow is offset **(−3, 4)**, blur **5**, opacity **0.6** at 256 px (scale with size).
- Vanilla backdrop target: CIELAB mean **(34.6, 3.6, 10.5)**, sd **(20.0, 7.2, 10.3)**. Measure it at runtime from the vanilla folder; these are the expected values.
- The radial falloff ratio is clipped to **0.45–1.25**, over **14** bins of radius 0–1.42. The softening blur is **0.7** px.
- Vanilla's interior is `alpha > 128` eroded by `MinFilter(19)`. A good is masked out of vanilla's statistics after dilating it with `MaxFilter(9)`.
- `BACKDROP_STYLE` is exactly: `"high-angle oblique close-up looking down onto {subject}, the roofs run diagonally across the frame and fill it edge to edge, no sky, no horizon, detailed 3D rendered miniature model as in a strategy game's city view, dim dusk light, deep soft shadows, muted desaturated grey and brown palette"`.
- `BUILDING_STYLE`, the `building` category's other entries and `gm_picture` must not change.
- A part is scaled by its alpha bounding box: its larger side is **0.56** of the icon's side (0.62 × vanilla goods' median span of 0.90).
- Render only with VRAM gated: two readings under **3000 MiB**, 30 s apart, and one FLUX job at a time. Run renders in `~/src/vic3te-icon-batch6` with `env -u PYTHONPATH`, `FLUX_MODEL_DIR=$HOME/models/FLUX.1-schnell` and `HF_HUB_OFFLINE=1`.
- DDS stays uncompressed in vanilla's format (the existing `write`).
- No game launch: one in-game look goes on a play-test list. The PR body's player-guide line is "below the guide's level of detail".
- Owner review: sheets with picks boxed in gold, each sent with SendUserFile (`display: render`) as it is made. Don't self-merge the PR.

## Review Focus

1. **A goods key with no texture** in mod or vanilla goods: `check()` must report it as `bad_entry`, not crash at compose. Test in Task 1.
2. **A building listed in both `building` and `production_building`:** `check()` reports `bad_entry`. Test in Task 1.
3. **A repainted good after its buildings were written:** the buildings' manifest record must change, so `write` rewrites them. Test in Task 4.
4. **A black or near-uniform backdrop render:** the regrade must return finite pixels, with no NaN from a zero sd or an empty radial bin. Test in Task 2.
5. **An existing DDS that `write` trusts** because `written.json` has no record under the new category's name (the moved buildings and re-picked goods): the procedure deletes those DDS before `write`, and the task checks `git status` shows every one rewritten. Verification steps in Tasks 6 and 8.

---

### Task 1: Registry: the two categories, goods textures, foreground validation, the moved entries

**Files:**
- Modify: `scripts/image_pipeline/icon_prompts.py`:
  - after `STATUE_STYLE`, about line 254: `BACKDROP_STYLE`;
  - `CATEGORIES`: `production_building`, `building_foreground`;
  - `ICONS["building"]`, about lines 1009–1200: remove the 39 keys;
  - new `ICONS["production_building"]` and `ICONS["building_foreground"]`;
  - `check()`, about line 4473;
  - a new `good_texture()`.
- Test: `test_icon_pipeline.py` (new class `ProductionBuildingRegistryTests`)

**Interfaces:**
- Produces:
  - `BACKDROP_STYLE: str`
  - `CATEGORIES["production_building"] = dict(folder="building_icons", size=256, mode="framed_good", entity_dir="common/buildings", field="icon", style=BACKDROP_STYLE, neighbours="building_icons")`
  - `CATEGORIES["building_foreground"] = dict(folder="goods_icons", size=256, mode="cutout", fill=0.90, grade_strength=0.4, part=True, gui=(), style="{subject}, one chunky readable object, " + PAINTED)`
  - A `production_building` entry: `{"subject": str, "seed": None | int, "foreground": [{"good": <goods key>} | {"part": "building_foreground/<key>"}, ...]}`. Each layer may carry `"scale": float` and `"at": (x, y)`.
  - `good_texture(good: str, mod_root: str | None = None) -> str | None`: the good's `texture` path (`gfx/...dds`). The mod's `common/goods/*.txt` wins, then `vanilla_parsed/common/goods.json`; `None` if neither defines the good.

- [ ] **Step 1: Write the failing tests**

```python
class ProductionBuildingRegistryTests(unittest.TestCase):
    def test_categories(self):
        spec = ip.CATEGORIES["production_building"]
        self.assertEqual((spec["folder"], spec["size"], spec["mode"], spec["field"]), ("building_icons", 256, "framed_good", "icon"))
        self.assertTrue(spec["style"].startswith("high-angle oblique close-up looking down onto {subject}"))
        self.assertTrue(ip.CATEGORIES["building_foreground"]["part"])
        self.assertEqual(ip.CATEGORIES["building"]["style"], ip.BUILDING_STYLE)   # untouched

    def test_good_texture_mod_first_then_vanilla(self):
        self.assertEqual(ip.good_texture("digital_assets"), "gfx/interface/icons/goods_icons/software.dds")  # mod good
        self.assertEqual(ip.good_texture("radios"), "gfx/interface/icons/goods_icons/radios.dds")            # vanilla
        self.assertIsNone(ip.good_texture("no_such_good"))

    def test_scope(self):
        pb = ip.ICONS["production_building"]
        self.assertEqual(len(pb), 39)
        self.assertFalse(set(pb) & set(ip.ICONS["building"]))
        self.assertIn("building_synthetics_plant_silk", pb)
        self.assertNotIn("building_solar_receiver", pb)
        for key, e in pb.items():
            self.assertTrue(e["foreground"], key)

    def test_check_flags_bad_foregrounds_and_duplicates(self):
        saved = ip.ICONS
        try:
            ip.ICONS = {
                "building": {"building_twice": {"subject": "a hall", "seed": None}},
                "building_foreground": {"ore_ok": {"subject": "a heap of red ore", "seed": None}},
                "production_building": {
                    "building_ok": {"subject": "roofs", "seed": None, "foreground": [{"good": "radios"}]},
                    "building_part_ok": {"subject": "a pit", "seed": None, "foreground": [{"part": "building_foreground/ore_ok"}]},
                    "building_no_good": {"subject": "roofs", "seed": None, "foreground": [{"good": "no_such_good"}]},
                    "building_no_part": {"subject": "roofs", "seed": None, "foreground": [{"part": "building_foreground/gone"}]},
                    "building_empty": {"subject": "roofs", "seed": None, "foreground": []},
                    "building_twice": {"subject": "roofs", "seed": None, "foreground": [{"good": "radios"}]},
                }}
            d = tempfile.mkdtemp()
            bdir = Path(d) / "common" / "buildings"; bdir.mkdir(parents=True)
            keys = set(ip.ICONS["production_building"]) | set(ip.ICONS["building"])
            (bdir / "b.txt").write_text("".join(f"{k} = {{\n}}\n" for k in keys), encoding="utf-8-sig")
            r = ip.check(d, on_disk=set())
        finally:
            ip.ICONS = saved
        self.assertEqual(sorted(k for c, k in r["bad_entry"] if c == "production_building"),
                         ["building_empty", "building_no_good", "building_no_part", "building_twice"])
```

`good_texture` with `mod_root=d` must still find vanilla goods (radios) through `vanilla_parsed/`. That's the repo's copy, not `d`'s.

- [ ] **Step 2: Run them and confirm they fail**

Run: `.venv/bin/python -m pytest test_icon_pipeline.py -q -k ProductionBuildingRegistry`
Expected: FAIL (`KeyError: 'production_building'`).

- [ ] **Step 3: Implement the registry pieces**
  - Write `good_texture` with the same top-level-block regex `check()` uses. Match `texture = "..."` inside the good's block. Read the vanilla file as `json.load(...)[good][1]["texture"][1].strip('"')`.
  - In `check()`:
    - a production entry with an empty `foreground`, a `good` that `good_texture` can't resolve, or a `part` naming no entry of a `part` category is `bad_entry`;
    - so is any key that appears in more than one category sharing an `(entity_dir, field)` (report it under each category after the first);
    - put the foreground check beside `_marks_ok`.

- [ ] **Step 4: Move the 39 entries**

The keys are in the spec's scope table.
- Each gets `"seed": None`, a backdrop subject and its `foreground`:
  - mines, the ocean and space mines, the direct air capture plant and the drinks plant: `{"part": "building_foreground/<name>"}`;
  - every other building: `{"good": <goods key>}`. The goods keys are the economy keys: `radios`, `consumer_appliances`, `electronic_components`, `digital_assets`, `robotics`, `advanced_materials`, `aeroplanes`, `oil`, `rubber`, `wood`, `sugar`, `opium`, `meat`, `fruit`, `silk`, `grain`, `electricity`, `tourism`.
- Subjects say what is seen from above in at most 25 words, without the camera words.
  - Reuse the spike's seven verbatim from `~/flux_runs/building_icons_vanilla_spike_1127/m2_render.py` `SUBJ`.
  - The direct air capture plant: "a low industrial hall whose whole roof is rows of big round black fans, with squat pellet reactor towers beside it".
- Add the 17 `building_foreground` entries (15 ores from the spec's proposal table, plus `dac_pellets` and `bottled_drink`), each `"seed": None`. Ore subjects follow the table: "a heap of rough rust-red earthy bauxite lumps", and so on. Use `"a heap of pale grey chalky round pellets"` and `"a single label-free glass bottle of dark drink with a plain metal cap"`.
- Leave a comment over `production_building` naming the spec.

- [ ] **Step 5: Run the registry tests and the existing suite file**

Run: `.venv/bin/python -m pytest test_icon_pipeline.py -q`
Expected: all pass, including `test_registry_matches_the_mod`, which has no `missing_dds` because the moved entries are unreviewed, and `test_gm_picture_category`.

- [ ] **Step 6: Commit**

```bash
git add scripts/image_pipeline/icon_prompts.py test_icon_pipeline.py
git commit -m "Icon registry: production buildings in vanilla's two-layer look, and their ores"
```

---

### Task 2: Vanilla backdrop statistics and the regrade

**Files:**
- Modify: `scripts/image_pipeline/icon_render.py`, beside `vanilla_template`, about line 296
- Test: `test_icon_pipeline.py` (new class `BackdropRegradeTests`, Pillow-gated like `StripTests`)

**Interfaces:**
- Produces:
  - `rgb_to_lab(rgb: np.ndarray) -> np.ndarray` and `lab_to_rgb(lab: np.ndarray) -> np.ndarray`. They map sRGB floats 0–1 to CIELAB (D65) and back, in numpy only: `.venv` has no scikit-image.
  - `GOOD_FITS: dict[str, tuple[str, float, int, int]]`: the 13 clean fits, building → (good, scale, x, y), copied from `proto.FITS`.
  - `interior_mask(tmpl_alpha: np.ndarray, erode: int = 19) -> np.ndarray[bool]`.
  - `backdrop_stats_from(images: list[tuple[np.ndarray, np.ndarray]], interior: np.ndarray) -> dict`. Each image is `(rgb float HxWx3, good_mask bool HxW)`. It returns `{"mean": (3,), "std": (3,), "profile": (14,)}`: the per-image means and sds averaged, and the median of each image's radial L profile normalized by its first four bins.
  - `backdrop_stats(folder: str = "building_icons", size: int = 256) -> dict`: reads the vanilla icons and goods in `GOOD_FITS`, masks each good with `MaxFilter(9)`, and calls `backdrop_stats_from`. Cache it per process.
  - `regrade_backdrop(raw: Image.Image, stats: dict, interior: np.ndarray, size: int, strength: float = 1.0, blur: float = 0.7, bias: tuple = (0.0, 0.0, 0.0)) -> Image.Image`. It does the Reinhard transfer to `stats["mean"] + bias` and `stats["std"]`, applies the radial ratio (clipped 0.45–1.25) and the blur, and returns RGB at `size`.

- [ ] **Step 1: Write the failing tests**

```python
    def test_lab_round_trip_and_anchors(self):
        rgb = np.random.default_rng(0).random((8, 8, 3))
        self.assertLess(np.abs(self.r.lab_to_rgb(self.r.rgb_to_lab(rgb)) - rgb).max(), 1e-4)
        white = self.r.rgb_to_lab(np.ones((1, 1, 3)))[0, 0]
        np.testing.assert_allclose(white, (100, 0, 0), atol=0.05)
        self.assertAlmostEqual(self.r.rgb_to_lab(np.full((1, 1, 3), 119 / 255))[0, 0, 0], 50.0, delta=0.5)

    def test_regrade_matches_the_target_mean(self):
        interior = np.ones((256, 256), bool)
        stats = {"mean": np.array([34.6, 3.6, 10.5]), "std": np.array([20.0, 7.2, 10.3]), "profile": np.ones(14)}
        raw = Image.fromarray(np.random.default_rng(1).integers(120, 255, (512, 512, 3), dtype=np.uint8))
        out = np.asarray(self.r.regrade_backdrop(raw, stats, interior, 256, blur=0)) / 255
        lab = self.r.rgb_to_lab(out)
        np.testing.assert_allclose(lab.reshape(-1, 3).mean(0), stats["mean"], atol=2.0)

    def test_falloff_darkens_corners(self):
        interior = np.ones((256, 256), bool)
        prof = np.r_[np.ones(7), np.linspace(0.95, 0.7, 7)]
        stats = {"mean": np.array([40.0, 0, 0]), "std": np.array([10.0, 2, 2]), "profile": prof}
        raw = Image.fromarray(np.random.default_rng(2).integers(80, 160, (256, 256, 3), dtype=np.uint8))
        out = np.asarray(self.r.regrade_backdrop(raw, stats, interior, 256, blur=0)).astype(float)
        self.assertLess(out[:24, :24].mean(), 0.85 * out[116:140, 116:140].mean())

    def test_black_render_stays_finite(self):
        interior = np.ones((64, 64), bool)
        stats = {"mean": np.array([34.6, 3.6, 10.5]), "std": np.array([20.0, 7.2, 10.3]), "profile": np.ones(14)}
        with np.errstate(invalid="raise", divide="raise"):              # a NaN or a divide by zero raises
            out = np.asarray(self.r.regrade_backdrop(Image.new("RGB", (64, 64)), stats, interior, 64))
        self.assertEqual(out.shape, (64, 64, 3))

    def test_stats_from_ignore_the_good(self):
        rgb = np.full((64, 64, 3), 0.2); rgb[32:, 32:] = 1.0              # bright "good" in the lower right
        mask = np.zeros((64, 64), bool); mask[32:, 32:] = True
        s = self.r.backdrop_stats_from([(rgb, mask)], np.ones((64, 64), bool))
        self.assertAlmostEqual(s["mean"][0], self.r.rgb_to_lab(np.full((1, 1, 3), 0.2))[0, 0, 0], delta=0.1)
```

- [ ] **Step 2: Run them and confirm they fail**

Run: `.venv/bin/python -m pytest test_icon_pipeline.py -q -k BackdropRegrade`
Expected: FAIL (`AttributeError: ... rgb_to_lab`).

- [ ] **Step 3: Implement the functions**
  - Take the formulas and order of operations from `proto.regrade` / `proto.vanilla_stats`.
  - Guard each sd with `+ 1e-6`, and an empty radial bin with ratio 1.0.
  - Build the radial bins as the spike does: `R = hypot` of the normalized offsets from the centre, `np.linspace(0, 1.42, 15)` edges.

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `.venv/bin/python -m pytest test_icon_pipeline.py -q -k BackdropRegrade`
Expected: PASS.

- [ ] **Step 5: Check against the game install**

Run: `env -u PYTHONPATH ~/src/vic3te-icon-batch6/.venv-img/bin/python -c "import sys; sys.path.insert(0,'scripts/image_pipeline'); import icon_render as r; s=r.backdrop_stats(); print(s['mean'].round(1), s['std'].round(1))"`
Expected: `[34.6 3.6 10.5] [20. 7.2 10.3]`, give or take 0.2.

- [ ] **Step 6: Commit**

```bash
git add scripts/image_pipeline/icon_render.py test_icon_pipeline.py
git commit -m "Icon render: vanilla building backdrops' measured grade, and the regrade toward it"
```

---

### Task 3: The `framed_good` layout: foreground layers, the dark patch, grit, the frame

**Files:**
- Modify: `scripts/image_pipeline/icon_render.py` (near `compose_framed`, about line 505; `Composer`, about line 1836)
- Test: `test_icon_pipeline.py` (new class `FramedGoodTests`)

**Interfaces:**
- Consumes: `regrade_backdrop`, `backdrop_stats`, `interior_mask` (Task 2); `vanilla_template`, `compose_framed`'s frame blend, `drop_shadow` or an equivalent, and `resize_premultiplied` (existing).
- Produces:
  - `GOOD_SCALE = 0.62`, `GOOD_AT = (0.67, 0.67)`, `PART_SPAN = 0.56`, `SHADOW = (-3, 4, 5, 0.6)`, all at 256 px.
  - `foreground_layer(im: Image.Image, size: int, kind: str, scale: float | None = None, at: tuple | None = None) -> Image.Image`:
    - an RGBA canvas `size`×`size` holding the layer and its shadow;
    - `kind == "good"`: the whole canvas is scaled to `scale or GOOD_SCALE`;
    - `kind == "part"`: cropped to its alpha bbox, larger side scaled to `scale or PART_SPAN`;
    - centred at `at or GOOD_AT`.
  - `compose_framed_good(raw: Image.Image, spec: dict, tmpl: tuple, stats: dict, layers: list[tuple[Image.Image, dict]]) -> Image.Image`. Each layer is `(image, {"kind": "good"|"part", "scale"?, "at"?})`, drawn in order. The steps:
    1. `regrade_backdrop(raw, stats, interior, size, bias=spec.get("bias", (0, 0, 0)))`;
    2. the dark patch: `spec.get("patch", 0.0)` is the share of brightness removed under the union of the layers' alpha, dilated by `size // 16` and blurred by `size // 12`;
    3. grit: `spec.get("grit", 0.0)` is the sd of a fixed-seed (`default_rng(0)`) luminance noise, in 0–255 units, added to the backdrop only;
    4. the layers;
    5. the frame blended as `compose_framed` does, so the output alpha is the template's.
  - `Composer.compose(raw, cat, spec, backdrop=None, layers=None)`: mode `"framed_good"` caches `self._tmpl[cat]` (`vanilla_template`) and `self._stats[cat]` (`backdrop_stats(spec["folder"], spec["size"])`). It raises `ValueError` when `layers is None`.

- [ ] **Step 1: Write the failing tests**

```python
class FramedGoodTests(unittest.TestCase):
    def setUp(self):
        import icon_render
        self.r = icon_render
        a = np.zeros((256, 256, 4), np.float32); a[8:248, 8:248] = (60, 50, 40, 255)  # stand-in frame
        self.tmpl = (a, np.zeros_like(a))
        self.stats = {"mean": np.array([34.6, 3.6, 10.5]), "std": np.array([20.0, 7.2, 10.3]), "profile": np.ones(14)}
        self.raw = Image.fromarray(np.random.default_rng(3).integers(60, 200, (512, 512, 3), dtype=np.uint8))
        g = Image.new("RGBA", (256, 256), (0, 0, 0, 0)); g.paste((220, 30, 30, 255), (40, 40, 216, 216))
        self.good = g

    def compose(self, **spec):
        return np.asarray(self.r.compose_framed_good(self.raw, dict({"size": 256}, **spec), self.tmpl, self.stats,
                                                     [(self.good, {"kind": "good"})])).astype(int)

    def test_good_sits_at_vanillas_place(self):
        out = self.compose()
        cx, cy = int(0.67 * 256), int(0.67 * 256)
        self.assertGreater(out[cy, cx, 0], out[cy, cx, 2] + 100)            # red good at (0.67, 0.67)
        self.assertGreater(np.abs(out[40, 40, :3] - (220, 30, 30)).sum(), 100)  # upper left is backdrop, not good
        self.assertTrue((out[..., 3] == self.tmpl[0][..., 3]).all())        # frame alpha unchanged

    def test_good_canvas_scale(self):
        canvas = np.asarray(self.r.foreground_layer(self.good, 256, "good"))
        xs = np.where(canvas[..., 0].max(0) > 200)[0]
        # the red square is 176/256 of its canvas; the canvas is 0.62 of the icon
        self.assertAlmostEqual((xs.max() - xs.min() + 1) / 256, 176 / 256 * 0.62, delta=0.02)

    def test_part_scaled_by_its_bbox(self):
        canvas = np.asarray(self.r.foreground_layer(self.good, 256, "part"))
        xs = np.where(canvas[..., 0].max(0) > 200)[0]
        self.assertAlmostEqual((xs.max() - xs.min() + 1) / 256, 0.56, delta=0.02)

    def test_patch_darkens_around_the_good_only(self):
        plain, patched = self.compose(), self.compose(patch=0.4)
        ring = (int(0.67 * 256) - 62, int(0.67 * 256))                      # just outside the good's left edge
        self.assertLess(patched[ring][:3].sum(), plain[ring][:3].sum())
        self.assertEqual(patched[30, 30][:3].tolist(), plain[30, 30][:3].tolist())

    def test_grit_is_deterministic_and_adds_texture(self):
        a, b, plain = self.compose(grit=6.0), self.compose(grit=6.0), self.compose()
        self.assertTrue((a == b).all())
        self.assertGreater(np.abs(np.diff(a[20:80, 20:80, 1], axis=1)).mean(),
                           np.abs(np.diff(plain[20:80, 20:80, 1], axis=1)).mean())

    def test_composer_needs_layers(self):
        c = self.r.Composer()
        c._tmpl["production_building"], c._stats["production_building"] = self.tmpl, self.stats
        with self.assertRaises(ValueError):
            c.compose(self.raw, "production_building", ip.CATEGORIES["production_building"])
```

- [ ] **Step 2: Run them and confirm they fail**

Run: `.venv/bin/python -m pytest test_icon_pipeline.py -q -k FramedGood`
Expected: FAIL (`AttributeError: ... compose_framed_good`).

- [ ] **Step 3: Implement `foreground_layer`, `compose_framed_good` and the Composer branch**
  - The patch's dilate and blur radii scale with `size`.
  - Grit is added to the regraded backdrop before the layers, so the foreground stays clean.
  - Add `self._stats = {}` to `Composer.__init__`.

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `.venv/bin/python -m pytest test_icon_pipeline.py -q -k "FramedGood or BackdropRegrade or Backed"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/image_pipeline/icon_render.py test_icon_pipeline.py
git commit -m "Icon render: the framed_good layout, a good or part over a regraded backdrop in vanilla's place"
```

---

### Task 4: Driver: resolve foreground layers, recompose and rewrite when they change

**Files:**
- Modify: `scripts/image_pipeline/generate_icons.py`:
  - `_compose_one`, about line 397;
  - `Finals.get`, about line 437;
  - `stage_compose`, about line 509;
  - `stage_write`'s `part_seeds` and `want_for`, about lines 619–645;
  - the module docstring.
- Test: `test_icon_pipeline.py` (new class `ForegroundDriverTests`)

**Interfaces:**
- Consumes: `good_texture` (Task 1); `Composer.compose(..., layers=)` (Task 3).
- Produces:
  - `foreground_refs(e: dict) -> list[tuple[str, dict]]`: `("good", layer)` or `("part", layer)` per layer, in order.
  - `good_icon_file(good: str, game: Path) -> Path`: `MOD_ROOT / good_texture(good)` if that file exists, else `game / good_texture(good)`.
  - `foreground_fingerprint(e: dict, game: Path) -> list`: per layer, `["good", good, sha1(file bytes)[:12], scale, at]` or `["part", ref, part_seed, entry_prompt(part)]`.
  - `Finals.layers(e: dict) -> list[tuple[Image.Image, dict]]`: a part uses its pick, or its first rendered seed while under review. It raises `SystemExit` naming the part when that part has no render.
  - `_compose_one(..., deps: tuple[Path, ...] = ())`: a final is kept only if it is newer than the raw, the backdrop raw and every dep.
  - `want_for` appends `foreground_fingerprint(e, game)` for a `production_building` entry.
  - `part_seeds` includes foreground parts, so `write` skips a building until its parts are picked.

- [ ] **Step 1: Write the failing tests**

```python
class ForegroundDriverTests(unittest.TestCase):
    def test_fingerprint_follows_the_goods_file(self):
        d = Path(tempfile.mkdtemp())
        f = d / "gfx/interface/icons/goods_icons/radios.dds"; f.parent.mkdir(parents=True); f.write_bytes(b"one")
        saved = gi.MOD_ROOT
        try:
            gi.MOD_ROOT = d                                                  # the mod's copy wins
            e = {"subject": "roofs", "seed": 0, "foreground": [{"good": "radios"}]}
            before = gi.foreground_fingerprint(e, Path("/nonexistent"))
            f.write_bytes(b"two")
            self.assertNotEqual(before, gi.foreground_fingerprint(e, Path("/nonexistent")))
        finally:
            gi.MOD_ROOT = saved

    def test_fingerprint_follows_the_parts_pick(self):
        saved = ip.ICONS["building_foreground"].get("_t")
        try:
            ip.ICONS["building_foreground"]["_t"] = {"subject": "a heap of red ore", "seed": 0}
            e = {"subject": "a pit", "seed": 0, "foreground": [{"part": "building_foreground/_t"}]}
            a = gi.foreground_fingerprint(e, Path("/nonexistent"))
            ip.ICONS["building_foreground"]["_t"]["seed"] = 1
            self.assertNotEqual(a, gi.foreground_fingerprint(e, Path("/nonexistent")))
        finally:
            ip.ICONS["building_foreground"].pop("_t")
            if saved is not None:
                ip.ICONS["building_foreground"]["_t"] = saved

    def test_compose_one_recomposes_when_a_dep_is_newer(self):
        d = Path(tempfile.mkdtemp()); raw, final, dep = d / "r.png", d / "f.png", d / "g.dds"
        Image.new("RGB", (4, 4)).save(raw); Image.new("RGBA", (4, 4)).save(final); dep.write_bytes(b"x")
        os.utime(raw, (1, 1)); os.utime(final, (2, 2)); os.utime(dep, (3, 3))
        calls = []
        class C:
            def compose(self, *a, **k):
                calls.append(k.get("layers")); return Image.new("RGBA", (4, 4))
        gi._compose_one(C(), "production_building", raw, final, deps=(dep,), layers=[])
        self.assertEqual(calls, [[]])                                       # recomposed, layers passed through
        gi._compose_one(C(), "production_building", raw, final, deps=(dep,), layers=[])
        self.assertEqual(calls, [[]])                                       # now the final is newest: kept
```

`_compose_one` passes `layers` through to `composer.compose` only when it isn't `None`, so the other modes' calls are unchanged.

- [ ] **Step 2: Run them and confirm they fail**

Run: `.venv/bin/python -m pytest test_icon_pipeline.py -q -k ForegroundDriver`
Expected: FAIL (`AttributeError: ... foreground_fingerprint`).

- [ ] **Step 3: Implement the driver changes**
  - `Finals.get`: for a category whose mode is `framed_good`, pass `layers=self.layers(e)` and the deps (good files, part finals).
  - `stage_compose` uses `Finals.get` for that mode, so the layers resolve in one place.
  - Document `framed_good` and `foreground` in the module docstring's stage list. Document the `foreground` field in `icon_prompts.py`'s docstring.

- [ ] **Step 4: Run the whole pipeline test file**

Run: `.venv/bin/python -m pytest test_icon_pipeline.py -q` and `.venv/bin/ruff check scripts/image_pipeline test_icon_pipeline.py`
Expected: all pass; ruff clean.

- [ ] **Step 5: Commit and push the branch**

```bash
git add scripts/image_pipeline/generate_icons.py scripts/image_pipeline/icon_prompts.py test_icon_pipeline.py
git commit -m "Icon pipeline: a production building's good or ore is an input to its compose and write"
git push -u origin icons-vanilla-production-buildings
```

`icon_prompts.py` carries the unrelated Conditionality `_v2` line: stage it out with `git add -p` (or apply `~/flux_runs/conditionality_variant_20261127.patch` in reverse, commit, and re-apply it).

---

### Task 5: Pilot: the repainted goods and four industries, with the grade fixes tuned

**Files:**
- Modify: `scripts/image_pipeline/icon_prompts.py`:
  - the `good` entries `consumer_appliances`, `electronic_components`, `software`, `robot`, `tourism`, `opium`;
  - a new `buckyball` entry (`"now": f"{_GI}/goods_icons/buckyball.dds"`);
  - the `production_building` spec's `bias`, `patch` and `grit`.
- Off-repo: `~/flux_runs/production_icons_1127/` (gate script, sheets, picks JSON)

- [ ] **Step 1: Rewrite the goods subjects**
  - Set each to `"seed": None`. The current subject's object stays, now "seen at an angle from slightly above", in muted colours, with no flat face to the viewer. For example: "a dark green circuit board seen at an angle from slightly above, holding a black microchip, round capacitors and striped resistors".
  - `opium` keeps its subject and `seed: 3`, unless the pilot sheet shows it out of place.
  - `buckyball`: "a dark graphite-grey carbon buckyball molecule model of round atoms on short thick rods, seen from slightly above".

- [ ] **Step 2: Render in one gated job**
  - Use `~/flux_runs/tools/render_batch.py` with 3 seeds for `good` (`--only` the 7 keys) and 3 seeds for `production_building` (`--only building_robotics_industry,building_software_industry,building_aerospace_industry,building_nuclear_plant`).
  - Copy the gate from `~/flux_runs/building_icons_vanilla_spike_1127/m2_gated.sh` and run it in the background.
  - Expected: 33 raws in `generated_images/icons/raw/`, about 20 min once the GPU is free.

- [ ] **Step 3: Tune `bias`, `patch` and `grit` on one sheet**
  - Show each pilot building at bias `(0,0,0)` / `(-4,0,2)` / `(-8,1,4)`, patch `0` / `0.25` / `0.4`, and grit `0` / `4`. Use goods seed 0, beside its three vanilla neighbours, at 128, 70 and 40 px.
  - Pick the set that sits closest to the neighbours. Its interior Lab mean should be within 3 L\* of vanilla's 34.6.
  - Write the values into the spec.

- [ ] **Step 4: Make and send the pilot sheet, then stop for the owner**
  - Rows: the 7 goods (now | vanilla goods neighbours || seeds), and the 4 buildings (now | vanilla neighbours || seeds composed over each goods candidate).
  - Box my picks in gold, add a game-size strip, and send it with SendUserFile. Wait for the owner's picks and comments before Task 6.

---

### Task 6: Goods: write the owner's picks

**Files:**
- Modify: `scripts/image_pipeline/icon_prompts.py` (the goods' seeds), `gfx/interface/icons/goods_icons/*.dds`

- [ ] **Step 1: Record the picks** with `~/flux_runs/tools/set_seed.py <worktree> good/<key>=<seed>`. Re-render any rejected good and repeat Task 5 step 4 for it alone.

- [ ] **Step 2: Delete the DDS of every re-picked good, then write**
  - `write` trusts a DDS with no record in `written.json`.
  - Run: `rm gfx/interface/icons/goods_icons/{consumer_appliances,electronic_components,software,robot,tourism,buckyball}.dds`, plus `opium.dds` if it was re-picked.
  - Then: `env -u PYTHONPATH .venv-img/bin/python scripts/image_pipeline/generate_icons.py --stage write --category good`.
  - Expected: `git status --short gfx/interface/icons/goods_icons` lists each re-picked file as modified, none deleted.

- [ ] **Step 3: Validate and grep for pins**
  - Run: `python3 scripts/image_pipeline/generate_icons.py --validate` and `git grep -n "goods_icons/\(software\|robot\|buckyball\|tourism\|consumer_appliances\|electronic_components\|opium\)" -- 'test_*.py'`.
  - Expected: validate clean; any test that pins a goods path still passes (`.venv/bin/python -m pytest <those files> -q`).

- [ ] **Step 4: Commit**

```bash
git add scripts/image_pipeline/icon_prompts.py gfx/interface/icons/goods_icons/
git commit -m "Goods icons: seven mod goods repainted at an angle in muted colours, as vanilla's"
```

---

### Task 7: The parts: ores, pellets and the bottle

**Files:**
- Modify: `scripts/image_pipeline/icon_prompts.py` (`building_foreground` subjects and seeds)

- [ ] **Step 1: Render** all 17 `building_foreground` entries at 3 seeds in one gated job. Expected: 51 raws.

- [ ] **Step 2: Sheet and self-check**
  - Make one sheet per part: seeds cut out, at 2x and at game size.
  - Make one sheet of the fifteen mines' candidate heaps, each composed over a regraded spike backdrop (`~/flux_runs/building_icons_vanilla_spike_1127/out/` or the mine's current art via `proto.m1_current`), side by side at 70 and 40 px.
  - Check:
    - the cut-out kept the object whole;
    - no lettering on the bottle;
    - pellets aren't white;
    - the fifteen tell apart at 70 px. Re-render the dark ores that merge, with a stronger accent colour.

- [ ] **Step 3: Send the sheets and stop for the owner;** record the picks with `set_seed.py building_foreground/<key>=<seed>`.

- [ ] **Step 4: Commit** the seeds: `git add scripts/image_pipeline/icon_prompts.py && git commit -m "Icon registry: the mines' ores and two other foregrounds, picked"`.

---

### Task 8: The 39 backdrops: render, review, write, wire

**Files:**
- Modify: `scripts/image_pipeline/icon_prompts.py` (backdrop seeds), `gfx/interface/icons/building_icons/<39 keys>.dds`

- [ ] **Step 1: Render** the 35 not yet rendered at 3 seeds in one gated job, then run `--stage compose --category production_building`. Expected: 117 raws, 117 finals.

- [ ] **Step 2: Self-check every candidate**
  - Zoom the bottom 300 rows of each raw for watermarks.
  - Re-render any seed with sky, a horizon, lettering, signs, people or insignia, or one that doesn't say what the building does. A carbon-capture hall with chimneys reads as an emitter.

- [ ] **Step 3: Send the review sheets and stop for the owner**
  - Use `--stage sheet --category production_building`, with picks boxed in gold, plus a game-size strip.
  - Add one sheet of the four clean power plants side by side at 70 and 40 px, the twin check.
  - Record the picks with `set_seed.py production_building/<key>=<seed>`.

- [ ] **Step 4: Delete the 39 old DDS, then write and wire**
  - Run: delete `gfx/interface/icons/building_icons/<key>.dds` for each `production_building` key. Then `--stage write --category production_building`, then `--stage wire --category production_building --dry-run`.
  - Expected:
    - `git status --short gfx/interface/icons/building_icons` lists 39 modified files and none deleted;
    - the dry run reports no icon line changing (the paths are unchanged), except `building_synthetics_plant_silk`, which moves from `synthetics_plants.dds` to its own file. Then run wire without `--dry-run`.

- [ ] **Step 5: Validate, grep for pins, run the tests**
  - Run: `python3 scripts/image_pipeline/generate_icons.py --validate`; `git grep -n "building_icons/building_\(<any of the 39>\)\|synthetics_plants.dds" -- 'test_*.py'` and run those files; `.venv/bin/python -m pytest test_icon_pipeline.py test_placeholder_icons.py -q`.
  - Expected: clean and passing.

- [ ] **Step 6: Commit**

```bash
git add scripts/image_pipeline/icon_prompts.py gfx/interface/icons/building_icons/ common/buildings/
git commit -m "Building icons: 39 production buildings in vanilla's look, a painted plant behind the good or its ore"
```

---

### Task 9: Docs, play-test line, PR

**Files:**
- Modify:
  - `docs/guides/python_tools.md`: the `generate_icons.py` row; one sentence on `framed_good`, `foreground` and the rebuild-on-good-change rule;
  - the spec's status line: "built in PR #N".
- Create: `docs/testing/production-building-icons-playtest.md`, with one check: the building browser's industry and mining tabs, mod buildings beside vanilla's at 70 px. Also look at the market panel's repainted goods.

- [ ] **Step 1: Write the docs above,** and add any lesson the rounds taught (a FLUX subject rule) to `icon_prompts.py`'s docstring list.

- [ ] **Step 2: Run the quick preflight**
  - Run: `.venv/bin/python scripts/preflight.py --quick`
  - Expected: green. On a `gui_reference_audit --strict` failure from the game install (#1271), judge by CI's dummy-path run.

- [ ] **Step 3: Commit, push, open the PR**
  - The body has:
    - a before/after sheet of all 39 at 70 px;
    - the "Player guide: below the guide's level of detail" line;
    - "Closes" for any issue filed for the player's feedback.
  - End the body with the attribution lines. Don't merge; the owner does.
