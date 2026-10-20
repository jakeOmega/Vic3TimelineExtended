# Economy Growth Sim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable yearly economy sim of one Victoria 3 country, read from the mod's own files and calibrated against the owner's France → EU playthrough. It lets the owner tune growth between the two failure modes in issue #1034.

**Architecture:** Four modules in `scripts/analysis/`:
- `econ_save_series.py` turns 1.14.5 binary saves into a small calibration dataset.
- `econ_sim_data.py` reads every mod number the model uses: cost curve, cost tiers, PM ladders, caps.
- `econ_growth_sim.py` is the model, its diagnostics and the CLI.
- `econ_sim_scenarios.py` builds the four country types from the dataset; `econ_sim_calibrate.py` fits the free parameters.

Tests live at the repo root like the rest of the suite.

**Tech Stack:** Python 3.11/3.12, standard library only (no numpy). `mod_state.ModState` with the committed `vanilla_parsed/`. The save readers reuse `scripts/analysis/save_world_report.py` and `save_country_probe.py`.

**Spec:** `docs/superpowers/archive/specs/2026-10-17-economy-growth-sim-design.md`. Read it before any task; section numbers below (§) refer to it.

## Global Constraints

- Runs on Python 3.11 and 3.12: no f-string that reuses its own quote inside braces (PEP 701). Standard library only.
- Tests need neither Victoria 3 nor the owner's saves. They use synthesized bytes, the committed dataset, and `vanilla_parsed/`. Never import `mod_state_server`; build `ModState` directly (Task 4).
- Every mod number comes from the mod or vanilla files at load time. A missing or renamed key raises `KeyError` naming it, and a non-numeric value raises `ValueError`. No silent literal fallback.
- No changes under `common/`, `events/`, `gui/` or `localization/`. This issue changes no script (§3).
- Saves: copy a save into the session scratchpad before reading it. Never write into `/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/save games/`. Read saves with `python3 -I`.
- Lint: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/ruff check .` clean. Run tests with that checkout's `.venv/bin/python` (the worktree has no venv).
- Commits: stage by path (never `git commit -a`), and end each message with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01XkFYoVP3ujWZ6ALPWqHzE7
  ```
- Speed: loading ModData takes ≤ 3 s; one run 1867–2050 takes ≤ 1 s; the first sweep (6 curves × 4 types) takes ≤ 60 s.
- Player guide: no player-facing change. The PR body says so.

## Review Focus

1. **A save from another game version, or a text save, in the series.** The extractor skips it with a one-line reason and carries on. It neither crashes nor decodes garbage. Tested in Task 1 and Task 2.
2. **A country id missing from a later save** (annexed, or dead after a revolution). Its record is absent, not an exception, and the scenario builder ends that country's series there. Tested in Task 2 and Task 8.
3. **A trend ring buffer that hasn't wrapped yet** (an early save) as well as a wrapped one. Both come out chronological, newest last. Tested in Task 1.
4. **Extreme lever values in a sweep**: curve cap 0, GDP per capita 0, fill rate 0, payback 0, a crew-only tier with no per-level staff. All record fields stay finite, with no ZeroDivisionError. Tested in Task 5 and Task 6.
5. **An era before a ladder's first PM or past its last.** `base_at` returns the first or last PM, and automation stops at the top tier. Tested in Task 4.

---

### Task 1: Fixed-point country record from a binary save

**Files:**
- Create: `scripts/analysis/econ_save_series.py`
- Test: `test_econ_save_series.py`

**Interfaces:**
- Consumes: `save_country_probe.country_headers(blob) -> [(offset, id, tag, flags)]`.
- Produces:
  - `FX_SCALE = 100_000`
  - `class UnsupportedSave(Exception)`
  - `fx_tokens(b: bytes, i: int, end: int)`, which yields `(offset, kind, value)`. It lifts `~/src/vic3te-save-analysis-2026-10-17/scripts/tok.py` unchanged: 0x0167 comes back as kind `"fx"`, raw i64.
  - `fx_parse_block(b: bytes, start: int) -> tuple[list, int]` (also from tok.py).
  - `unwrap_ring(values: list[float], index: int, count: int) -> list[float]`, chronological with the newest last.
  - `save_version(path: Path) -> str` and `check_supported(path: Path) -> None`. The check raises `UnsupportedSave` unless the save is binary (header not `SAV0100`; `save_world_report.is_text_save` is False) and its meta version starts with `"1.14.5"`.
  - `country_record(blob: bytes, offset: int) -> dict`, with the keys listed below.

**`country_record` keys.** Tokens are from `~/src/vic3te-save-analysis-2026-10-17/series_probe/token_map.md`, which this task copies into the module docstring.
- `tag`
- From `pop_statistics`, raw counts: `population` (the sum of the 3 strata), `workforce`, `salaried`, `subsisting`, `unemployed`, and `workforce_by_profession` (15 names in the token map's order).
- `gdp_weekly`: the 0x3f16 ring, unwrapped and divided by FX_SCALE. Also `gdp` (newest) and `gdp_week_index`.
- `base_wage`, `average_productivity`, `investment_pool`, `pool_spend_weekly` (0x33c7), and `investment_by_type` ({building type: weekly £}), all divided by FX_SCALE.
- `points_weekly` {government, private}: the sum of 0x2e77 `construction_speed` over each queue's elements.
- `active_projects` and `queued_projects` {government, private}: elements with a speed, and all elements.
- `per_project_cap`: the max 0x59a1 over active elements, or None.
- `states`: the 0x09cd list.
- `variables` {`prior_construction_scaling`, `te_mon_gdp_last_year`}: via `save_country_probe.read_variables`, None when absent.

- [ ] **Step 1: Write the failing tests**

```python
class TestTokens(unittest.TestCase):
    def test_fx_value_is_fixed_point(self):
        blob = _block(4, [_kv(0x3171, [_kv(0x56C3, _fx(123456789))])])
        rec = S.country_record(blob, 0)
        self.assertAlmostEqual(rec["investment_pool"], 1234.56789)

    def test_ring_unwrapped(self):
        self.assertEqual(S.unwrap_ring([5, 6, 3, 4], index=6, count=4), [3, 4, 5, 6])

    def test_ring_not_wrapped(self):
        self.assertEqual(S.unwrap_ring([1, 2, 3], index=3, count=5214), [1, 2, 3])

    def test_country_record_fields(self):
        blob = _synthetic_country()   # pop_statistics, budget, a 3-sample gdp ring, two queues
        rec = S.country_record(blob, 0)
        self.assertEqual(rec["workforce"], rec["salaried"] + rec["subsisting"] + rec["unemployed"])
        self.assertEqual(rec["points_weekly"], {"government": 40.0, "private": 35.0})
        self.assertEqual(rec["active_projects"], {"government": 1, "private": 1})
        self.assertEqual(rec["queued_projects"], {"government": 2, "private": 1})
        self.assertEqual(rec["per_project_cap"], 40.0)
        self.assertEqual(rec["gdp_weekly"][-1], rec["gdp"])

    def test_text_save_unsupported(self):
        p = _tmp_file(b"SAV0100" + b"0" * 17 + b"meta_data={")
        with self.assertRaises(S.UnsupportedSave):
            S.check_supported(p)

    def test_old_version_unsupported(self):
        p = _tmp_binary_save(version="1.13.9")
        with self.assertRaises(S.UnsupportedSave):
            S.check_supported(p)
```

The helpers build binary tokens: `_tok(t)` (u16 LE), `_fx(v)` (0x0167 + i64), `_u32`, `_kv(key, value_or_list)` (key `=` value, or key `= { … }`), and `_block(country_id, items)`, which is u32 id `= { … }` at offset 0. `_tmp_binary_save` writes a 24-byte `SAV0105…` header plus a zip with `meta` (`version="<v>"` in text) and an empty `gamestate`.

- [ ] **Step 2: Run them and see them fail**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_econ_save_series -v`
Expected: `ModuleNotFoundError: econ_save_series`.

- [ ] **Step 3: Implement the module**

The decode follows `series_probe/econ_probe.py` (`get`, `dense`, `ring`), with fx divided by FX_SCALE everywhere except the pop_statistics counts. `save_version` reads the version from the meta: the `meta` zip entry for SAV0105, and the bytes between the header and the zip for SAV0103.

- [ ] **Step 4: Run them and see them pass**

Same command. Expected: all OK.

- [ ] **Step 5: Commit**

```bash
git add scripts/analysis/econ_save_series.py test_econ_save_series.py
git commit -m "Econ sim (#1034): fixed-point country record from binary saves"
```

### Task 2: Per-state slice, techs, laws and the extract CLI

**Files:**
- Modify: `scripts/analysis/econ_save_series.py`
- Test: `test_econ_save_series.py`

**Interfaces:**
- Consumes: Task 1; `save_world_report.World(path)` (`.source.blob`, `.source.techs(warnings)`, `.source.buildings(warnings)`, `.date`); `save_country_probe.law_records(blob)`.
- Produces:
  - `pops_by_state(blob: bytes, states: set[int]) -> dict[int, dict]`, giving per state `{population, workforce, peasants, employed, unemployed, wages_weekly, welfare_weekly}`. Pop tokens come from `~/src/vic3te-save-analysis-2026-10-17/scripts/pops.py`: type 0x00e1, workforce 0x2fd5, dependents 0x573a, employed 0x573b, location 0x2819, and the weekly budget 0x4eed (slot 0 wages, slot 3 welfare, both /1e5). Peasants = the workforce of pops of type `peasants`. For other pops, employed = Σ emp, unemployed = Σ (wf − emp), wages_weekly = Σ slot 0 and welfare_weekly = Σ slot 3.
  - `buildings_in(blob: bytes, states: set[int]) -> list[dict]`, giving `{type, levels, state, staffing, employees, goods_sales, goods_cost, pms}`. Tokens come from `scripts/buildings.py` in the same folder: staffing 0x32ed /1e5, employees 0x5607 raw, goods_sales 0x5606 /1e5, goods_cost 0x2d15 /1e5.
  - `extract(path: Path, country_ids: list[int], core: dict[int, set[int]] | None = None) -> dict`, giving:
    ```
    {"save", "date", "version",
     "countries": {id: country_record + {"acquired_techs": [..], "land_law": str|None}},
     "core": {id: {"states": {...pops_by_state...}, "buildings": [...]}},
     "world": {"gdp": Σ newest gdp, "population": Σ population}}
    ```
    The world sums run over every country block.
  - `main(argv) -> int`, the CLI: `econ_save_series.py SAVE... --country-id N [--country-id M ...] [--core-from SAVE] --out FILE.json`. The `--core-from` save fixes each country's core as its state list in that save. An unsupported save prints `skip <name>: <reason>` and is left out. A country id absent from a save is left out of that save's `countries`.

- [ ] **Step 1: Write the failing tests**

```python
    def test_missing_country_is_absent(self):
        out = S.extract_from_blob(_blob_with_countries([4]), "1900.1.1", country_ids=[4, 99])
        self.assertIn(4, out["countries"])
        self.assertNotIn(99, out["countries"])

    def test_pops_by_state_peasants_and_unemployed(self):
        blob = _pops([("peasants", 1000, 0, 7), ("laborers", 500, 300, 7), ("laborers", 200, 200, 8)])
        got = S.pops_by_state(blob, {7})
        self.assertEqual(got[7]["peasants"], 1000)
        self.assertEqual(got[7]["employed"], 300)
        self.assertEqual(got[7]["unemployed"], 200)
        self.assertNotIn(8, got)

    def test_cli_skips_unsupported(self):
        rc, out = _run_cli([_tmp_file(b"SAV0100" + b"0" * 17 + b"meta_data={")], "--country-id", "4")
        self.assertEqual(rc, 0)
        self.assertIn("skip", out)
```

`extract_from_blob(blob, date, country_ids, core=None)` is the testable core of `extract`. `extract` calls it after `World(path)`.

- [ ] **Step 2: Run them and see them fail**

Same command. Expected: AttributeError on `extract_from_blob`.

- [ ] **Step 3: Implement** `pops_by_state`, `buildings_in`, `extract_from_blob`, `extract` and `main`. The land law is the `lawgroup_land_reform` entry of `law_records` for the country.

- [ ] **Step 4: Run them and see them pass**

- [ ] **Step 5: Commit**

```bash
git add scripts/analysis/econ_save_series.py test_econ_save_series.py
git commit -m "Econ sim (#1034): per-state slice, techs, laws, extract CLI"
```

### Task 3: Extract the calibration dataset

**Files:**
- Create: `scripts/analysis/econ_series_c480d386.json`
- Create: `docs/systems/economy_growth_sim.md` (the § Data section only, filled out in Task 9)

**Interfaces:**
- Consumes: Task 2's CLI.
- Produces: the dataset `econ_series_c480d386.json`:
  ```
  {"playthrough": "c480d386",
   "countries": {"<id>": {"tag_by_date": {date: tag},
                           "gdp_yearly": {year: £/yr},
                           "points": [{date, country record minus gdp_weekly,
                                       "core": {population, workforce, peasants, employed, unemployed,
                                                wage_per_worker, welfare_per_unemployed,
                                                buildings_by_type: {type: {levels, staffing, employees, goods_sales, goods_cost,
                                                                           pms: {pm: levels}}}},
                                       "whole": {same keys as core, over all the country's states}}]}},
   "world": [{date, gdp, population}],
   "core_states": {"<id>": [state ids]}}
  ```
  Here `gdp_yearly` is the mean of each calendar year's weekly samples, merged across saves, with later saves winning on overlap. The slices are built as follows:
  - `wage_per_worker` = Σ wages_weekly / Σ employed, over non-peasant pops;
  - `welfare_per_unemployed` = Σ welfare_weekly / Σ unemployed (0 when there are none);
  - `whole` is the same slice over the country's own `states` at that save. Run `--core-from` once per country so each gets both slices; GBR and CHI use `whole` only.

- [ ] **Step 1: Copy the series** into `<scratchpad>/econ_saves/`. These are every save whose `save_world_report.World(path)` playthrough is `c480d386`: `french republic_1867`, `french commune_*` (binary only), `france_1986`, `france_1990`, and `european union_*`. List them first with `~/src/vic3te-save-analysis-2026-10-17/series_probe/save_inventory.py`.

- [ ] **Step 2: Find the country ids.** For France the id is 4. For Great Britain and China, take the ids whose tag is `GBR` and `CHI` in the 1867 save (`save_country_probe.country_headers`). Confirm the names by grepping `localization/` and vanilla loc for `GBR:` and `CHI:`; don't guess from the tags.

- [ ] **Step 3: Run the extractor.**

```bash
/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -I scripts/analysis/econ_save_series.py <scratch>/econ_saves/*.v3 \
  --country-id 4 --country-id <GBR> --country-id <CHI> \
  --core-from "<scratch>/econ_saves/french republic_1867_08_16.v3" --out <scratch>/raw_series.json
```

Expected: a `skip` line for each text save, and no traceback.

- [ ] **Step 4: Build the dataset** from the raw series with a short script in the scratchpad: the yearly GDP merge, PMs collapsed to `{pm: levels}` per building type, dates sorted. Write it to `scripts/analysis/econ_series_c480d386.json`. Expected size: under 2 MB.

- [ ] **Step 5: Verify against the probe numbers.**
  - FRA 1917.10.2: population 91.07M (±0.1%), workforce 45.55M, subsisting 10.87M, unemployed 6.00M, points per week 1,954 (±1).
  - EUN 1998.12.29: population 1,198.0M, subsisting 208.3M, unemployed 94.1M, points 22,614.
  - FRA 1917 `whole.wage_per_worker` ≈ £0.092 (the probe's pop scan).
  - For each save, the core slice's workforce is ≤ the country's, and `whole`'s workforce is within 1% of `pop_statistics`.

  Record any miss and fix the extractor before going on.

- [ ] **Step 6: Reconcile the 1998 penalty** (§7 step 1). For each point, compute the raw curve, clamp((gdp/population − 1)/99 × 10, 0, 10), and compare it with `prior_construction_scaling`. Write a table to the scratchpad. In § Data of `docs/systems/economy_growth_sim.md`, write the cause in one paragraph: other `goods_input_construction_mult` sources (read the save's country modifiers with `save_country_probe.read_modifiers`), a population definition that differs, or a defect in the adjusted multiplier. If it's a defect in the mod, stop and report it to the controller; it is a bug for the owner, not something this plan fixes.

- [ ] **Step 7: Commit**

```bash
git add scripts/analysis/econ_series_c480d386.json docs/systems/economy_growth_sim.md
git commit -m "Econ sim (#1034): calibration series from the c480d386 playthrough"
```

### Task 4: Mod numbers and sector ladders

**Files:**
- Create: `scripts/analysis/econ_sim_data.py`
- Test: `test_econ_sim_data.py`

**Interfaces:**
- Produces:
  - `load_mod_state(repo: Path = REPO) -> ModState`. It loads `vanilla_parsed` plus the mod's `Buildings`, `PM Groups`, `PMs`, `Goods`, `Technologies`, `Script Values`, `Building Groups` and `Modifiers`, as in `ModState(base, mod, vanilla_data=vanilla_parsed.load(...).data)`, with base paths under `/nonexistent`. About 2 s.
  - `val(x)` unwraps the parser's `('=', v)` pairs.
  - `@dataclass(frozen=True) CurveConstants(reference, floor_ratio, ceiling_ratio, max_mult)`.
  - `@dataclass(frozen=True) ModNumbers`, with these fields:
    - `curve: CurveConstants`
    - `cost_tiers: dict[str, float]`
    - `retool_mult: float` (`pm_retooling`'s `goods_input_construction_mult`)
    - `retool_weeks: int` (`RETOOLING_WEEKS` in `common/defines/extra_defines.txt`)
    - `prices: dict[str, float]` (good → `cost`)
    - `base_project_cap: float` and `base_eos_cap: float` (from `base_values`)
    - `project_cap_steps: tuple[tuple[int, str, float], ...]` and `eos_cap_steps`, as (era, tech, add) sorted by era
    - `tech_era: dict[str, int]`
  - `read_numbers(ms) -> ModNumbers`
  - `@dataclass(frozen=True) PMFigures`, with these fields:
    - `pm`, `era` (the max era of its unlocking techs, 0 if none);
    - `employment` (Σ `building_employment_*_add` in `level_scaled`, per level);
    - `crew` (Σ the same in `unscaled`, per building);
    - `goods_in` and `goods_out` (£ a week a level at base prices, from `workforce_scaled` `goods_input_*_add` and `goods_output_*_add`);
    - `construction_out` (`goods_output_construction_add`, per level);
    - property `va = goods_out − goods_in`.
  - `pm_figures(ms, numbers, pm: str) -> PMFigures`
  - `SECTOR_BUILDINGS: dict[str, tuple[str, str, str | None]]` (sector → building, base group, automation group). Exact values:
    ```
    farming        building_wheat_farm  pmg_base_building_wheat_farm  pmg_harvesting_process_building_wheat_farm
    mining         building_coal_mine   pmg_mining_equipment_building_coal_mine  pmg_steam_automation_building_coal_mine
    light          building_food_industry  pmg_base_building_food_industry  pmg_automation_building_food_industry
    heavy          building_steel_mill  pmg_steelmaking_process  pmg_automation_building_steel_mill
    hightech       building_electronic_components_and_semiconductor_industry  pmg_base_building_electronic_components  pmg_automation_building_electronic_components
    infrastructure building_railway     pmg_base_building_railway  None
    construction   building_construction_sector  pmg_base_building_construction_sector  pmg_construction_automation
    services       building_urban_center  pmg_amenities  None
    ```
  - `@dataclass(frozen=True) Ladder(sector, building, maintenance, base: tuple[PMFigures, ...], automation: tuple[PMFigures, ...])`. `automation[0]` is the group's first PM, the "none" tier. Maintenance is the per-level `goods_input_construction_add` of the building's maintenance PM: the first PM of any group named `pmg_maintenance*` that isn't `pm_no_maintenance` or `pm_maintenance_traditional`; 0 if none.
  - `ladder(ms, numbers, sector: str) -> Ladder`
  - `base_at(ladder, era: float) -> PMFigures`: the last base PM with `era <= era`, else the first.
  - `breakeven(tier: PMFigures) -> float | None` = `(tier.goods_in - tier.goods_out) / -tier.employment`. It is None when `tier.employment >= 0`.
  - `GROUP_SECTOR`: an ordered mapping. The first group in a building's chain (its own group, then parents) found in it decides the sector:
    ```
    bg_construction, te_construction_market_bg -> construction
    bg_service, bg_urban_facilities           -> services
    bg_high_tech                              -> hightech
    bg_heavy_industry                         -> heavy
    bg_light_industry, bg_manufacturing       -> light
    bg_agriculture, bg_plantations, bg_ranching -> farming
    bg_extraction                             -> mining
    bg_infrastructure, bg_power               -> infrastructure
    ```
    A type starting `building_subsistence` maps to `peasants`; anything else maps to `other`.
  - `sector_of(ms, building_type: str) -> str`
  - `sector_cost_points(ms, numbers, buildings_by_type: dict[str, dict]) -> dict[str, float]`: per sector, the level-weighted mean `required_construction` (through `cost_tiers`) over the given building types.
  - `@dataclass(frozen=True) ModData(numbers: ModNumbers, ladders: dict[str, Ladder], ms: ModState)` and `load_mod_data(repo=REPO) -> ModData`.

- [ ] **Step 1: Write the failing tests**

```python
class TestNumbers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.md = D.load_mod_data()
        cls.n = cls.md.numbers

    def test_curve_constants(self):
        self.assertEqual(self.n.curve, D.CurveConstants(1.0, 1.0, 100.0, 10.0))

    def test_cost_tiers(self):
        t = self.n.cost_tiers
        self.assertEqual([t[k] for k in ("construction_cost_very_low", "construction_cost_low", "construction_cost_medium",
                                         "construction_cost_high", "construction_cost_very_high", "construction_cost_super_high",
                                         "construction_cost_mega_high", "construction_cost_extreme")],
                         [100, 200, 400, 600, 800, 2000, 5000, 10000])

    def test_retooling_and_caps(self):
        self.assertEqual((self.n.retool_mult, self.n.retool_weeks), (10.0, 260))
        self.assertEqual((self.n.base_project_cap, self.n.base_eos_cap), (10.0, 20.0))
        self.assertIn((12, "molecular_assemblers", 200.0), self.n.project_cap_steps)
        self.assertIn((6, "fluorescent_lamps", 30.0), self.n.eos_cap_steps)
        self.assertEqual(self.n.prices["construction"], 1000.0)
        self.assertEqual(self.n.tech_era["steam_donkey"], 3)

class TestLadders(unittest.TestCase):
    def test_steam_donkey_breakeven(self):          # engines 1 x 60 + coal -3 x 30 over 1,000 laborers
        tier = D.pm_figures(MS, N, "pm_steam_donkey_building_coal_mine")
        self.assertAlmostEqual(D.breakeven(tier), 0.15)

    def test_dragline_breakeven(self):              # (345 - 180) / 2000
        self.assertAlmostEqual(D.breakeven(D.pm_figures(MS, N, "pm_dragline_excavators_coal_mine")), 0.0825)

    def test_crew_only_tier_has_no_breakeven(self):
        self.assertIsNone(D.breakeven(D.PMFigures("x", 12, 0.0, 1000.0, 10.0, 0.0, 0.0)))

    def test_base_at_bounds(self):                  # Review Focus 5
        lad = D.ladder(MS, N, "mining")
        self.assertEqual(D.base_at(lad, 0).pm, lad.base[0].pm)
        self.assertEqual(D.base_at(lad, 99).pm, lad.base[-1].pm)

    def test_sector_of(self):
        cases = {"building_wheat_farm": "farming", "building_coal_mine": "mining", "building_food_industry": "light",
                 "building_steel_mill": "heavy", "building_electronic_components_and_semiconductor_industry": "hightech",
                 "building_railway": "infrastructure", "building_power_plant": "infrastructure",
                 "building_construction_sector": "construction", "building_urban_center": "services",
                 "building_subsistence_farms": "peasants", "building_government_administration": "other"}
        for b, s in cases.items():
            self.assertEqual(D.sector_of(MS, b), s, b)

    def test_construction_ladder_reads_goods_per_level(self):
        lad = D.ladder(MS, N, "construction")
        self.assertEqual([t.construction_out for t in lad.base][:2], [1.0, 2.0])
        self.assertEqual(lad.base[0].employment, 6000.0)

    def test_maintenance_rates(self):
        self.assertEqual(D.ladder(MS, N, "heavy").maintenance, 0.1)
        self.assertEqual(D.ladder(MS, N, "infrastructure").maintenance, 0.15)
        self.assertEqual(D.ladder(MS, N, "mining").maintenance, 0.05)
```

`MS` and `N` are module-level, loaded once in `setUpModule`.

- [ ] **Step 2: Run them and see them fail** (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `econ_sim_data.py`.** Script values may be stored as strings or `{ value = n }` blocks; accept both and raise `ValueError` for anything else.

- [ ] **Step 4: Run them and see them pass.** Then time `load_mod_data()`; expected ≤ 3 s.

- [ ] **Step 5: Commit**

```bash
git add scripts/analysis/econ_sim_data.py test_econ_sim_data.py
git commit -m "Econ sim (#1034): mod numbers and sector ladders"
```

### Task 5: Cost curve, point price and construction purchase

**Files:**
- Create: `scripts/analysis/econ_growth_sim.py`
- Test: `test_econ_growth_sim.py`

**Interfaces:**
- Consumes: `ModNumbers`, `CurveConstants` (Task 4).
- Produces:
  - `@dataclass Params`. Every field can be overridden by name (Task 8). The defaults:
    - curve: `curve="linear"`, `curve_cap=None`, `other_construction_mult=0.0`, `construction_good_price=0.93`;
    - investment: `private_invest_share=0.13`, `gov_invest_share=0.05`, `queue_per_state=1.0`;
    - labour: `fill_rate=0.5`, `wage_floor=0.05`, `wage_step=1.0`, `wage_decay=0.2`, `vacancy_target=0.02`, `slack_target=0.03`, `subsistence_income=0.02`, `payback_years=10.0`;
    - output: `price_level=1.0`, `services_jobs_per_gdp=0.0`, `demand_gdp_ratio=0.3`;
    - population: `g_max=0.025`, `g_min=-0.005`, `g_slope=0.004`, `workforce_share=0.5`;
    - diagnostics: `mode1_slack=0.01`, `mode2_slack=0.10`, `rich_gdppc=5.0`, `labour_bind_vacancy=0.05`;
    - the mod-side levers of spec §8, as multipliers on what Task 4 reads, all neutral by default. Task 6 applies them:
      - `cost_points_mult=1.0` scales `sc.cost_points`;
      - `project_cap_mult=1.0` scales the per-project cap;
      - `construction_labour_mult=1.0` scales workers per point;
      - `late_employment_mult=1.0` scales `employment` of base and automation PMs with era ≥ 8;
      - `eos_cap_mult=1.0` scales the economy-of-scale cap;
      - `maintenance_mult=1.0` scales m_s;
      - `retool_charge_mult=1.0` scales the retooling charge;
      - `era_shift_years=0.0` evaluates `era_at(year − era_shift_years)`.
  - `CURVES = ("linear", "capped", "log", "sqrt", "world", "none")`
  - `cost_mult(p: Params, c: CurveConstants, gdppc: float, world_gdppc: float | None = None) -> float`, which is X. Let f = reference·floor_ratio and g = reference·ceiling_ratio. The shapes:
    - linear: `clamp((gdppc − f)/(g − f) · max_mult, 0, max_mult)`;
    - capped: linear with `max_mult` replaced by `curve_cap`;
    - log: `max_mult · ln(gdppc/f)/ln(g/f)`, clamped (0 for gdppc ≤ f);
    - sqrt: `max_mult · sqrt((gdppc − f)/(g − f))`, clamped;
    - world: linear on `ratio = gdppc/world_gdppc` in place of `gdppc/reference`;
    - none: 0.
  - `point_price(p: Params, base_price: float, x: float) -> float` = `base_price · construction_good_price · (1+x) · (1+other_construction_mult)`
  - `points_bought(spend_per_year: float, price: float, cap_per_year: float) -> tuple[float, bool]`, which returns (points, cap_bound).

- [ ] **Step 1: Write the failing tests**

```python
C = D.CurveConstants(1.0, 1.0, 100.0, 10.0)

class TestCurve(unittest.TestCase):
    def test_linear(self):
        p = G.Params()
        for gdppc, x in ((0, 0), (1, 0), (25, 24 / 99 * 10), (100, 10), (1000, 10)):
            self.assertAlmostEqual(G.cost_mult(p, C, gdppc), x)

    def test_shapes(self):
        self.assertAlmostEqual(G.cost_mult(G.Params(curve="log"), C, 10), 5.0)
        self.assertAlmostEqual(G.cost_mult(G.Params(curve="sqrt"), C, 25.75), 5.0)
        self.assertAlmostEqual(G.cost_mult(G.Params(curve="capped", curve_cap=3), C, 100), 3.0)
        self.assertAlmostEqual(G.cost_mult(G.Params(curve="capped", curve_cap=3), C, 25), 24 / 99 * 10)
        self.assertAlmostEqual(G.cost_mult(G.Params(curve="world"), C, 10, world_gdppc=5), 10 / 99)
        self.assertEqual(G.cost_mult(G.Params(curve="none"), C, 50), 0.0)

    def test_extremes_finite(self):                 # Review Focus 4
        for kw in ({"curve": "capped", "curve_cap": 0}, {"curve": "log"}, {"curve": "world"}):
            for gdppc in (0.0, 1e-12, 1e9):
                self.assertTrue(math.isfinite(G.cost_mult(G.Params(**kw), C, gdppc, world_gdppc=0.0)))

    def test_point_price_matches_saves(self):       # spec 4.1: FRA 1917 GBP 1,584; EUN 1998 GBP 4,925
        self.assertAlmostEqual(G.point_price(G.Params(construction_good_price=0.95), 1000, 0.666), 1582.7, places=1)
        self.assertAlmostEqual(G.point_price(G.Params(construction_good_price=0.91), 1000, 4.409), 4922.2, places=1)

    def test_cap_binds(self):
        self.assertEqual(G.points_bought(1e9, 1000, 5000), (5000, True))
        self.assertEqual(G.points_bought(1e6, 1000, 5000), (1000, False))
```

A world GDP per capita of 0 or None makes the world curve fall back to 0.

- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run them and see them pass.**
- [ ] **Step 5: Commit** (`git add scripts/analysis/econ_growth_sim.py test_econ_growth_sim.py`; message `Econ sim (#1034): cost curve shapes and construction purchase`).

### Task 6: The yearly step

**Files:**
- Modify: `scripts/analysis/econ_growth_sim.py`
- Create: `scripts/analysis/econ_sim_scenarios.py` (the `Scenario` dataclass only; the builders come in Task 8)
- Test: `test_econ_growth_sim.py`

**Interfaces:**
- Consumes: Task 4 (`ModData`, `Ladder`, `base_at`, `breakeven`) and Task 5.
- Produces:
  - In `econ_sim_scenarios.py`: `@dataclass(frozen=True) Scenario`, with these fields:
    - identity and timing: `name`, `kind` ("player" | "ai"), `series` (the dataset series it was built from: "FRA", "GBR", "CHI" or "union"; "" for toys), `start_year`, `end_year`;
    - people: `population`, `peasants`, `unemployed`, `subsistence_capacity`;
    - the start economy: `employed_level`, `employed_demand`, `gdp` (annual), `points_week`, `wage_start: float | None = None`;
    - territory and stock: `n_states`, `levels: dict[str, float]`;
    - per-sector calibration: `k_emp: dict[str, float]`, `k_va: dict[str, float]`, `cost_points: dict[str, float]`. A sector with no buildings at the start defaults `k_emp` and `k_va` to 1.0.
    - schedules: `era_points: tuple[tuple[int, float], ...]`, `land_floor: tuple[tuple[int, float], ...]`, `welfare: tuple[tuple[int, float], ...]` (welfare per unemployed worker, £/week, nominal), `alloc: tuple[tuple[int, dict[str, float]], ...]`, `world_gdppc: tuple[tuple[int, float], ...]`;
    - behaviour and events: `automation_lag_years: float`, `rich_from_year: int | None`, `annexations: tuple[tuple[int, dict], ...]`.

    Its methods: `era_at(year)` (linear interpolation, held flat past either end), `land_floor_at(year)`, `welfare_at(year)` and `alloc_at(year)` (piecewise constant from each point on), and `world_gdppc_at(year)` (linear).
  - `initial_state(sc, md, p)` takes people and the start economy straight from the scenario. The wage is `sc.wage_start / p.price_level` (the observed nominal wage in base-price terms), or `p.wage_floor` when None. Each sector starts at tier 0.
  - In `econ_growth_sim.py`:
    - `@dataclass SectorState(levels: float, auto_tier: int = 0, retool_left: float = 0.0, ready_since: float | None = None)`
    - `@dataclass State(year, population, workforce, peasants, unemployed, employed_level, employed_demand, wage, gdp, points_week, sectors: dict[str, SectorState])`
    - `@dataclass YearRecord`, with these fields:
      - the year: `year`, `era`;
      - people: `population`, `workforce`, `peasants`, `unemployed`, `employed`;
      - jobs: `jobs_level`, `jobs_demand`, `vacancies`;
      - money: `wage`, `gdp`, `gdppc`, `x`, `spend`, `points`;
      - which constraint bound: `money_bound`, `cap_bound`, `labour_bound`;
      - the economy's state: `auto_tiers: dict[str, int]` and `levels: dict[str, float]`.
    - `initial_state(sc: Scenario, md: ModData, p: Params) -> State`
    - `step(state: State, sc: Scenario, md: ModData, p: Params) -> YearRecord`, which advances `state` one year.
    - `run(sc: Scenario, md: ModData, p: Params) -> list[YearRecord]`

**Two simplifications against the spec.**
- Service jobs follow GDP directly (step 5), so the spec's services price (§5.6) and its "demand" constraint (§5.4) are folded into `services_jobs_per_gdp`; neither is modelled separately.
- `ModData.ms` may be None. The toy data in the tests has no ModState.

Say both in the doc's § Limits (Task 10).

**The step.** This is the algorithm the signature leaves open (spec §5.3). Level-bound sectors are `farming`, `mining`, `light`, `heavy`, `hightech`, `infrastructure` and `other`. `services` and `construction` are demand-bound. `other` has no ladder: its staff and VA per level are its `k_emp` and `k_va` alone, and it never automates. Let m_s be the sector's maintenance rate and x the cost multiplier (§5.3, step 3); pb = `md.numbers.prices["construction"] · p.construction_good_price`.

1. **Annexations.** Apply this year's annexations: add `population`, `peasants`, `unemployed` and `levels` from the event dict.
2. **Era.** `era = sc.era_at(year)`.
3. **Per sector.** Fix `b = base_at(ladder, era)` and `tiers = ladder.automation[1 : auto_tier + 1]`. Then:
   - `emp_lvl = k_emp · (b.employment + Σ t.employment)`;
   - `crew = Σ t.crew · sc.n_states` (one building per state);
   - `va_lvl = k_va · (b.va + Σ t.va) − m_s · pb · (1+x_prev)(1+other)`, where x_prev is last year's x (0 in the first year).
4. **Economy of scale.** `eos_s = 0.01 · min(max(levels_s/n_states − 1, 0), base_eos_cap + Σ steps with era ≤ era)` for every level-bound sector except `infrastructure`, which gets 0 (its group has no EoS, spec §4.3).
5. **Jobs.** `jobs_level = Σ levels_s · emp_lvl_s + crews`. Demand-bound jobs come from last year:
   - `jobs_services = p.services_jobs_per_gdp · gdp_level_prev / p.price_level`;
   - `jobs_construction = points_week_prev · wpp`, where `wpp = base_at(construction).employment / base_at(construction).construction_out`.
6. **Shedding.** If `employed_level > jobs_level`, move the excess to `unemployed`. Do the same for demand-bound jobs.
7. **Hiring.** `open = (jobs_level − employed_level) + (jobs_demand − employed_demand)`, clipped at 0. Hire `h = p.fill_rate · open`, drawn first from the unemployed. Then draw from peasants above `sc.land_floor_at(year) · sc.peasants` (the start peasants), and only while `wage ≥ 1.1 · p.subsistence_income`. Split `h` between level-bound and demand-bound jobs in proportion to their open jobs.
8. **GDP.** Staffed levels are `employed_level_s / emp_lvl_s` (if `emp_lvl_s > 0`), split across sectors in proportion to their jobs, else the sector's levels if its crew is staffed. Then:
   - `gdp_level = 52 · p.price_level · Σ staffed_s · va_lvl_s · (1 + eos_s)`, less this year's retooling charges;
   - `gdp = gdp_level · (1 + p.demand_gdp_ratio)`;
   - `gdppc = gdp / population`;
   - `x = cost_mult(p, curve, gdppc, sc.world_gdppc_at(year))`.
9. **Construction.**
   - `spend = (p.private_invest_share + p.gov_invest_share) · gdp`;
   - `cap = (base_project_cap + Σ steps ≤ era) · 52 · p.queue_per_state · n_states`;
   - `points, cap_bound = points_bought(spend, point_price(...), cap)`.

   New levels go to sector s as `points · alloc_at(year)[s] / sc.cost_points[s]` at the end of the year. Allocation to `services` and `construction` is dropped; neither is built.
10. **Automation.** For each sector with a next tier t of era ≤ era, with `retool_left == 0` and a non-None breakeven:
    - `gain = (wage − breakeven(t)) · (−t.employment) · 52 · p.payback_years`;
    - `charge = m_s · numbers.retool_mult · pb · (1+x)(1+other) · numbers.retool_weeks`.

    If `gain ≥ charge`, a player adopts now: `auto_tier += 1` and `retool_left = retool_weeks/52`. An AI country sets `ready_since` (if unset) and adopts once `year − ready_since ≥ sc.automation_lag_years`. A year in which the condition fails resets `ready_since` to None. Adopt at most one tier per sector a year. `retool_left` counts down by 1 a year, and during it the sector pays `charge/retool_left_start` a year.
11. **Wages.** `vac = (jobs_level − employed_level)/jobs_level`, or 0 when there are no jobs.
    - If `vac > p.vacancy_target`, then `wage *= 1 + p.wage_step · (vac − p.vacancy_target)`, capped at `0.75 · Σ va / Σ employed` over level-bound sectors (the 0.25 margin, §4.2).
    - Else, if `(peasants + unemployed)/workforce > p.slack_target`, then `wage = p.wage_floor + (wage − p.wage_floor)(1 − p.wage_decay)`.
    - The wage never goes below `p.wage_floor`.
12. **Population.**
    - `g = clamp(p.g_max − p.g_slope · ln(max(gdppc, 1e-9)/curve.reference), p.g_min, p.g_max)`;
    - `population *= 1 + g`;
    - `workforce = population · p.workforce_share`.

    Split a rise in workforce over peasants and the unemployed in proportion to the current peasant share. A fall comes out of the unemployed first, then peasants, then employed. Peasants above `sc.subsistence_capacity` move to the unemployed.

    **Return to subsistence.** Welfare is pop income, not a building wage floor; the engine's wage target discounts it (§4.2). So it enters the model only here. While `sc.welfare_at(year) / p.price_level < 1.3 · p.subsistence_income` and peasants are below `sc.subsistence_capacity`, `p.return_rate` (new Params field, default 0.1) of the unemployed go back to subsistence each year. Subsistence takes only the unemployed, at a 30% premium (§4.2). Under UBI the welfare exceeds that, so nobody returns.
13. **Flags.**
    - `labour_bound = vac > p.labour_bind_vacancy`;
    - `money_bound = not cap_bound and not labour_bound`.

    Record the year.

- [ ] **Step 1: Write the failing tests.** They use a toy `ModData` built in the test from literal `Ladder`/`PMFigures`, with no ModState, plus a toy `Scenario`.

```python
class TestStep(unittest.TestCase):
    def test_workforce_conserved(self):
        for rec in G.run(toy_scenario(), TOY, G.Params()):
            self.assertAlmostEqual(rec.peasants + rec.unemployed + rec.employed, rec.workforce, delta=1e-6 * rec.workforce)

    def test_no_negative_stocks(self):
        for rec in G.run(toy_scenario(), TOY, G.Params()):
            self.assertTrue(min(rec.peasants, rec.unemployed, rec.employed, rec.wage) >= 0)

    def test_peasant_floor_holds(self):
        sc = toy_scenario(land_floor=((1867, 0.5),), levels={"light": 1e6})
        start = sc.peasants
        self.assertTrue(all(r.peasants >= 0.5 * start - 1e-6 for r in G.run(sc, TOY, G.Params(fill_rate=1.0))))

    def test_wage_at_floor_with_slack(self):
        recs = G.run(toy_scenario(peasants=9e6, levels={"light": 10}), TOY, G.Params(private_invest_share=0, gov_invest_share=0))
        self.assertTrue(all(abs(r.wage - G.Params().wage_floor) < 1e-12 for r in recs))

    def test_wage_rises_when_short_and_respects_margin(self):
        recs = G.run(toy_scenario(population=2e5, peasants=0, levels={"light": 1000}), TOY, G.Params())
        self.assertGreater(recs[-1].wage, recs[0].wage)
        self.assertTrue(all(r.labour_bound for r in recs[1:]))

    def test_ai_lags_player(self):
        first = lambda kind: next(r.year for r in G.run(toy_scenario(kind=kind, automation_lag_years=5, wage_start=1.0), TOY, G.Params())
                                  if r.auto_tiers["light"] > 0)
        self.assertEqual(first("ai") - first("player"), 5)

    def test_cap_bound_flag(self):
        recs = G.run(toy_scenario(), TOY, G.Params(private_invest_share=0.9, queue_per_state=0.001))
        self.assertTrue(any(r.cap_bound for r in recs))

    def test_extremes_finite(self):                 # Review Focus 4
        for kw in ({"fill_rate": 0}, {"payback_years": 0}, {"curve": "capped", "curve_cap": 0}):
            for r in G.run(toy_scenario(), TOY_WITH_CREW_TIER, G.Params(**kw)):
                self.assertTrue(all(math.isfinite(v) for v in (r.gdp, r.gdppc, r.wage, r.points, r.x)))

    def test_levers_apply(self):
        base = G.run(toy_scenario(), TOY, G.Params())[-1].levels["light"]
        dear = G.run(toy_scenario(), TOY, G.Params(cost_points_mult=2.0))[-1].levels["light"]
        self.assertLess(dear, base)
        eras = {r.year: r.era for r in G.run(toy_scenario(era_points=((1867, 1.0), (1900, 5.0))), TOY, G.Params(era_shift_years=10))}
        self.assertAlmostEqual(eras[1890], 1 + 4 * 13 / 33)              # era_at(1880)

    def test_run_speed(self):
        t = time.perf_counter(); G.run(toy_scenario(end_year=2050), TOY, G.Params())
        self.assertLess(time.perf_counter() - t, 1.0)
```

`toy_scenario(**overrides)` returns a 1867–1900 `Scenario`: one light sector, 1,000 states, wage start 0.05, kind "player". Add a test that a welfare above 1.3× subsistence income keeps every unemployed worker out of subsistence, and that a welfare of 0 lets them return.

- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement `SectorState`, `State`, `YearRecord`, `initial_state`, `step` and `run`.**
- [ ] **Step 4: Run them and see them pass.**
- [ ] **Step 5: Commit** (`Econ sim (#1034): the yearly step`).

### Task 7: Diagnostics and the summary row

**Files:**
- Modify: `scripts/analysis/econ_growth_sim.py`
- Test: `test_econ_growth_sim.py`

**Interfaces:**
- Consumes: Task 6.
- Produces:
  - `classify(r: YearRecord, sc: Scenario, p: Params) -> str`, one of `"mode1"`, `"mode2"` or `"ok"` (spec §5.5). Let `slack = (peasants + unemployed)/workforce`.
    - mode1: `slack < p.mode1_slack and r.labour_bound`.
    - mode2: `slack > p.mode2_slack`, and `r.wage <= p.wage_floor · 1.000001`, and the country is rich: `r.gdppc ≥ p.rich_gdppc`, or `sc.rich_from_year` is set and `r.year ≥ sc.rich_from_year`.
  - `turn_year(records, md, sc) -> int | None`: the first year the wage reaches tier 1's breakeven (`ladder.automation[1]`) in sectors that together hold ≥ half that year's level-bound jobs.
  - `takeoff_year(records) -> int | None`: the first year t with `share(t) − share(t+5) ≥ 0.05`, where `share = peasants/workforce`.
  - `first_year_below(records, share: float, after: int | None = None) -> int | None`
  - `@dataclass Summary`, with these fields:
    - which run: `setting`, `scenario`;
    - the turn and peasants: `turn_year`, `peasants_below_5pct`;
    - slack at three dates: `slack_1950`, `slack_2000`, `slack_2045`;
    - years per mode: `mode1_years`, `mode2_years`;
    - years per binding constraint: `money_years`, `cap_years`, `labour_years`;
    - the end state: `gdppc_2045`;
    - catch-up: `takeoff_year`, `takeoff_to_10pct`, `takeoff_growth_ratio`.
  - `summarize(records, sc, md, p, setting: str, reference: list[YearRecord] | None = None) -> Summary`. Here `takeoff_growth_ratio` is the mean yearly gdppc growth over `[takeoff, takeoff+20]` divided by the reference run's over the same years, or None without a reference or a take-off.

- [ ] **Step 1: Write the failing tests**

```python
    def test_classify(self):
        sc, p = toy_scenario(rich_from_year=1920), G.Params()
        self.assertEqual(G.classify(rec(year=1950, peasants=0, unemployed=0.005, labour_bound=True), sc, p), "mode1")
        self.assertEqual(G.classify(rec(year=1950, peasants=0.2, wage=p.wage_floor), sc, p), "mode2")
        self.assertEqual(G.classify(rec(year=1900, peasants=0.2, wage=p.wage_floor, gdppc=1.0), sc, p), "ok")
        self.assertEqual(G.classify(rec(year=1950, peasants=0.2, wage=2 * p.wage_floor), sc, p), "ok")

    def test_takeoff_and_years_to_10pct(self):
        pct = [60] * 10 + [60 - 2 * i for i in range(1, 26)] + [8] * 5     # whole percents: exact floats
        recs = [rec(year=1900 + i, peasants=s / 100) for i, s in enumerate(pct)]
        self.assertEqual(G.takeoff_year(recs), 1907)                     # 0.60 - 0.54 >= 0.05
        self.assertEqual(G.first_year_below(recs, 0.10, after=1907), 1935)   # strictly below 0.10

    def test_turn_year_uses_tier_one(self):
        recs = [rec(year=1870 + i, wage=0.05 + 0.01 * i, jobs_level=1.0) for i in range(30)]
        self.assertEqual(G.turn_year(recs, TOY, toy_scenario()), 1870 + 10)   # toy tier-1 breakeven 0.15
```

`rec(**kw)` builds a `YearRecord` with workforce 1 and neutral defaults.

- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run them and see them pass.**
- [ ] **Step 5: Commit** (`Econ sim (#1034): mode classification, turn year, catch-up summary`).

### Task 8: Scenarios, calibration and the hindcast

**Files:**
- Modify: `scripts/analysis/econ_sim_scenarios.py`
- Create: `scripts/analysis/econ_sim_calibrate.py`
- Create: `scripts/analysis/econ_sim_params.json` (fitted, committed)
- Test: `test_econ_growth_sim.py` (class `TestScenarios`)

**Interfaces:**
- Consumes: the dataset (Task 3), `ModData`/`sector_of`/`sector_cost_points` (Task 4), and `run`/`Params` (Tasks 5–6).
- Produces:
  - `DATASET = Path(__file__).with_name("econ_series_c480d386.json")` and `load_dataset(path=DATASET) -> dict`.
  - `SCENARIOS = ("player_rich", "player_poor", "ai_rich", "ai_poor", "player_union")`. `player_union` is the whole-union check, not one of the four types.
  - `scenario(name: str, dataset: dict, md: ModData) -> Scenario`. Every type starts from the dataset's earliest point (1867).
    The dataset is keyed by series (ledger ruling R16). A series follows a fixed set of 1867 states; each point has a `slice` over those states and the `owner` country's fields (owner-level `points_weekly` and `pool_spend_weekly` already scaled to the slice's population).
    - **player_rich**: series "FRA", `rich_from_year=1920`.
    - **player_union**: series "union" (country 4's own states at each point). Its annexations are the states in a point's `per_state` that weren't in the previous point's. Each adds its `[population, workforce, peasants, unemployed, levels]` at that point's year. Its levels are spread over sectors in the union's sector shares at that point. Also `rich_from_year=1920`.
    - **ai_rich**: series "GBR", `kind="ai"`, `rich_from_year=1920`.
    - **ai_poor**: series "CHI", `kind="ai"`, `rich_from_year=None`.
    - **player_poor**: series "CHI"'s 1867 start, with player_rich's `era_points` and `alloc`, `kind="player"`, `rich_from_year=None`.

    `end_year` is 2050 if the series runs to the dataset's last save date, else its own last point's year (Review Focus 2: the extractor stops a GBR or CHI series once the player owns it or it splits).

    The fields (slice = the point's `slice`, owner = the point's `owner`):
    - `levels`: the start slice's levels by `sector_of`.
    - `k_emp[s]`: observed employees per staffed level in the start slice (Σ employees / Σ staffing), divided by the ladder's start-era `emp_lvl`. For `other`, which has no ladder, `k_emp` is the observed figure itself.
    - `k_va[s]`: observed VA per staffed level, Σ (goods_sales − goods_cost) / Σ staffing ÷ 52, divided by the ladder's start-era VA. The save's figures are yearly; check against one building's weekly sales in the 1949 text save before trusting the ÷ 52. For `other`, it is the observed figure itself.
    - the start economy:
      - `employed_level` and `employed_demand`: the start slice's employees in level-bound and demand-bound sectors;
      - `gdp`: owner `gdppc` × slice population (yearly terms, as `country_gdp_per_capita` reads it);
      - `points_week`: the sum of owner `points_weekly`;
      - `wage_start`: slice `wage_per_worker`.
    - `welfare`: per point, slice `welfare_per_unemployed`.
    - `cost_points`: `sector_cost_points` over the latest slice's buildings. Every level-bound sector it leaves out takes its representative building's own `required_construction` tier (ledger R14).
    - `era_points`: per point, the highest era e at which the owner holds ≥ 50% of `tech_era`'s era-e techs.
    - `alloc`: per point, owner `investment_by_type` summed by sector and normalised.
    - `land_floor`: per point, 0.5 when owner `land_law` is `law_serfdom` or `law_manorialism`, else 0.
    - `n_states`: the series' state count (`core_states`, or the start `per_state` for union).
    - `subsistence_capacity`: 1.5 × the start peasants.
    - `world_gdppc`: per point, `world.gdp / world.population`.
    - `automation_lag_years`: 0 for players, 5 for the AI.
  - In `econ_sim_calibrate.py`. The rules are shared: players and the AI differ only in behaviour (spec §6).
    - `STRUCTURAL = ("fill_rate", "wage_step", "wage_decay", "vacancy_target", "wage_floor", "return_rate", "price_level", "services_jobs_per_gdp", "demand_gdp_ratio", "g_max", "g_slope", "workforce_share", "construction_good_price")`. Fitted on player_rich only, then shared by every scenario.
    - `BEHAVIOUR = ("private_invest_share", "gov_invest_share", "queue_per_state")`. Fitted per scenario with the structural values held, plus `automation_lag_years` for the AI scenarios. Make `automation_lag_years` a Params field that overrides the scenario's when set.
    - `targets(sc, dataset) -> list[dict]`: per point after the start, `{year, peasant_share, unemployed_share, gdppc, population, points_week, wage}`, from the point's slice (people, wage) and owner (`gdppc`, scaled `points_weekly`).
    - `loss(records, targets, p) -> float` = Σ over targets of the squared error in peasant share, unemployed share, ln gdppc, ln population, ln points per week, and ln(sim wage · `p.price_level`) against ln observed wage. Weight 1 each. Interpolate the records to the target year.
    - `fit(sc, dataset, md, p0: Params, names, rounds=4) -> Params`: coordinate descent. Each round tries each name at ×{0.5, 0.8, 1.25, 2.0} of its value and keeps any that lowers the loss.
    - `check(dataset, md, params_path=PARAMS) -> list[str]`: the hindcast bands (below), returning one line per miss. An empty list is a pass.
    - `main(argv)`, with two forms:
      - `econ_sim_calibrate.py fit [--scenario ...] --out scripts/analysis/econ_sim_params.json` writes `{"structural": {...}, "behaviour": {scenario: {...}}}` and prints each scenario's loss and a target-versus-sim table;
      - `econ_sim_calibrate.py check` prints the misses and exits 1 if there are any.
  - In `econ_growth_sim.py`: `params_for(scenario: str, path=PARAMS) -> Params`. It applies the structural values, then the scenario's behaviour values, over the defaults. player_poor and player_union take player_rich's behaviour.

**The hindcast is a manual check, not a unit test** (my call; the owner can overrule at plan review). It runs on live mod values, so in CI any PR that retunes a PM, a cost tier or a cap tech could turn it red. It runs as `econ_sim_calibrate.py check`, documented in `python_tools.md`, after a mod change worth re-checking. The unit tests keep only what code changes can break.

**The hindcast bands for `check`** (spec §7 step 3; bands from §3 goal 4 and the owner's factor of 2). At every target of player_rich, a miss is any of:
- peasant share or unemployed share off by more than 0.10 (0.15 for ai_rich and ai_poor);
- population or GDP per capita outside ×[0.5, 2];
- the wage outside ×[0.5, 2].

For player_union, the check is the last point's peasant share, within 0.10.

- [ ] **Step 1: Write the failing tests.** These are the CI part: they check the code, not the fit.

```python
class TestScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.md, cls.ds = D.load_mod_data(), SC.load_dataset()

    def test_scenarios_build_and_run_finite(self):
        for name in SC.SCENARIOS:
            sc = SC.scenario(name, self.ds, self.md)
            self.assertEqual(sc.start_year, 1867, name)
            last = G.run(sc, self.md, G.params_for(name))[-1]
            self.assertTrue(all(math.isfinite(v) for v in (last.gdp, last.wage, last.points, last.peasants)), name)

    def test_start_matches_dataset(self):
        sc = SC.scenario("player_rich", self.ds, self.md)
        first = self.ds["series"]["FRA"]["points"][0]["slice"]
        self.assertAlmostEqual(sc.peasants, first["peasants"], delta=1)
        self.assertAlmostEqual(sc.wage_start, first["wage_per_worker"])

    def test_series_end_where_country_ends(self):     # Review Focus 2
        last_save_year = max(int(p["date"][:4]) for c in self.ds["series"].values() for p in c["points"])
        for name in ("ai_rich", "ai_poor"):
            sc = SC.scenario(name, self.ds, self.md)
            own_last = max(int(p["date"][:4]) for p in self.ds["series"][sc.series]["points"])
            self.assertEqual(sc.end_year, 2050 if own_last == last_save_year else own_last)

    def test_structural_params_shared(self):
        ps = {n: G.params_for(n) for n in SC.SCENARIOS}
        for name in CAL.STRUCTURAL:
            self.assertEqual(len({getattr(p, name) for p in ps.values()}), 1, name)

    def test_check_reports_a_miss(self):
        md, ds = self.md, self.ds
        bad = Path(self.enterContext(tempfile.TemporaryDirectory())) / "p.json"
        bad.write_text(json.dumps({"structural": {"price_level": 100.0}, "behaviour": {}}))
        self.assertTrue(CAL.check(ds, md, params_path=bad))
```

- [ ] **Step 2: Run them and see them fail** (`ModuleNotFoundError` for the calibrate module, or AttributeError for `scenario`).

- [ ] **Step 3: Implement the scenario builders, `econ_sim_calibrate.py` and `params_for`, then fit.**

```bash
/home/jakef/src/Vic3TimelineExtended/.venv/bin/python scripts/analysis/econ_sim_calibrate.py fit \
  --scenario player_rich --scenario ai_rich --scenario ai_poor --out scripts/analysis/econ_sim_params.json
```

Expected: a target-versus-sim table per scenario, with the loss falling each round. Structural values are fitted on player_rich first, then each scenario's behaviour values.

- [ ] **Step 4: Run the tests and the check.**

```bash
/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_econ_growth_sim 2> /tmp/u.txt; grep -E '^(Ran |OK|FAILED)' /tmp/u.txt
/home/jakef/src/Vic3TimelineExtended/.venv/bin/python scripts/analysis/econ_sim_calibrate.py check
```

Expected: `OK`, and `check` exits 0. If `check` reports misses after fitting, don't widen a band. Report to the controller which target and year miss, and by how much. The miss is a finding about the model, for the owner, and decides whether the model needs another mechanism.

- [ ] **Step 5: Commit**

```bash
git add scripts/analysis/econ_sim_scenarios.py scripts/analysis/econ_sim_calibrate.py scripts/analysis/econ_sim_params.json test_econ_growth_sim.py scripts/analysis/econ_growth_sim.py
git commit -m "Econ sim (#1034): scenarios from the playthrough, calibration and hindcast check"
```

### Task 9: CLI, sweep and the first sweep

**Files:**
- Modify: `scripts/analysis/econ_growth_sim.py`
- Modify: `docs/systems/economy_growth_sim.md`
- Test: `test_econ_growth_sim.py`

**Interfaces:**
- Consumes: Tasks 5–8.
- Produces:
  - `parse_sets(items: list[str]) -> dict[str, object]`. It takes `name=value` and coerces to the field's type. An unknown name raises `SystemExit` with the list of valid names.
  - `parse_curve(spec: str) -> dict`. `"capped:3"` gives `{"curve": "capped", "curve_cap": 3.0}`, `"log"` gives `{"curve": "log"}`, and an unknown shape raises `SystemExit`.
  - `sweep(curves: list[str], scenarios: list[str], md, dataset, sets: dict) -> list[Summary]`. Each scenario's player_rich run with the same curve is its `reference`.
  - `render_table(rows: list[Summary]) -> str`: markdown with the spec §9 columns plus the three catch-up columns. A None shows as `—`.
  - `main(argv) -> int`, with two subcommands:
    - `run --scenario NAME [--set k=v ...] [--curve SPEC] [--end YEAR] [--csv PATH]` prints the summary and writes the yearly CSV;
    - `sweep [--scenarios a,b] [--curves linear,capped:3,log,sqrt,world,none] [--set k=v ...]` prints the table.

- [ ] **Step 1: Write the failing tests**

```python
    def test_parse_sets_rejects_unknown(self):
        with self.assertRaises(SystemExit):
            G.parse_sets(["no_such_param=1"])

    def test_parse_sets_coerces(self):
        self.assertEqual(G.parse_sets(["fill_rate=0.3", "curve=log"]), {"fill_rate": 0.3, "curve": "log"})

    def test_cli_run_and_sweep(self):
        out = subprocess.run([sys.executable, "scripts/analysis/econ_growth_sim.py", "sweep",
                              "--scenarios", "player_rich", "--curves", "linear,none"],
                             capture_output=True, text=True, cwd=ROOT, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("| linear |", out.stdout)
        self.assertIn("| none |", out.stdout)
```

- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run them and see them pass.** Then time the full first sweep:

```bash
time /home/jakef/src/Vic3TimelineExtended/.venv/bin/python scripts/analysis/econ_growth_sim.py sweep \
  --scenarios player_rich,player_poor,ai_rich,ai_poor --curves linear,capped:3,log,sqrt,world,none
```

Expected: a 24-row table in ≤ 60 s.

- [ ] **Step 5: Write the first sweep into `docs/systems/economy_growth_sim.md`** (§ First sweep). Include the table, and under it a short read with one paragraph per point:
  - which shapes put player_rich's turn in 1860–1920 and its peasants under 5% by about 1950;
  - which keep poor-type catch-up on the tiger shape (§2): take-off to 10% in about 35 years, at several times the rich growth rate;
  - which put any type into mode 1;
  - which constraint binds when no shape helps. Name the lever that would help there (cap ladder, cost tiers, construction labour), per spec §5.4.

  Then add one AI cross-check paragraph (spec §7 step 4):
  - ai_rich's era at 1972, 1988 and 2015 against the observer runs' leaders (202, 219 and 245 techs; convert with `tech_era`);
  - its GDP per capita and penalty extrapolated to 2062 against `Baseline.v3`'s rich AI (18–27; +170–260%).

  The read reports; it doesn't pick. The owner picks.

- [ ] **Step 6: Commit** (`Econ sim (#1034): CLI, sweep, first cost-curve sweep`).

### Task 10: Docs, doc fixes and the PR

**Files:**
- Modify: `docs/systems/economy_growth_sim.md` (complete it)
- Modify: `docs/guides/python_tools.md` (two entries: `econ_save_series.py`; `econ_growth_sim.py` with `econ_sim_calibrate.py fit` and `check`, saying to run `check` after a mod change that touches PMs, cost tiers or construction techs)
- Modify: `docs/README.md` (one index line)
- Modify: `docs/vanilla/vanilla_economy_reference.md`: the four fixes in spec §11 at :109, :233, :347 and :417. Re-check the line numbers first.
- Modify: `docs/vanilla/vanilla_pops_reference.md:277,284` (proportional hiring is a 0.1 gap in fill ratio).
- Outside the repo: `/home/jakef/.claude/projects/-home-jakef-src-Vic3TimelineExtended/memory/observer_baselines/README.md`. Its `current_gdp` note becomes: frozen at 1949, use the GDP ring or `te_mon_gdp_last_year`.

**`docs/systems/economy_growth_sim.md` sections:**
- What it is for (the two modes, the targets);
- How to run it (run, sweep, `--set`, `--curve`);
- The model (state, the step in brief, demand-bound sectors);
- Data and calibration (the dataset, the 1998 penalty reconciliation, fitted params, the hindcast table);
- First sweep (from Task 9);
- Limits:
  - base prices;
  - one representative building per sector;
  - a fixed world path;
  - a fitted wage rule;
  - other PM groups (explosives, secondary crops) ignored;
  - the late-births bug in the series.

- [ ] **Step 1: Write the docs and fixes.** Keep each fix to the sentence that was wrong.
- [ ] **Step 2: Run the checks.**

```bash
/home/jakef/src/Vic3TimelineExtended/.venv/bin/ruff check .
/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_econ_save_series test_econ_sim_data test_econ_growth_sim 2> /tmp/u.txt; grep -E '^(Ran |OK|FAILED)' /tmp/u.txt
grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" scripts/analysis/econ_*.py
```

Expected: ruff clean, `OK`, no f-string hits.

- [ ] **Step 3: Commit** (`Econ sim (#1034): docs, doc fixes`).
- [ ] **Step 4: Push and open the PR against `main`.** The body goes in a file first, `<scratch>/pr_body.md`. It covers:
  - what the tool is;
  - the first sweep table and its read;
  - the calls made (spec §12);
  - `Closes #1034.`;
  - `Player guide: no player-facing change`;
  - the attribution footer.

  Don't merge; the owner reviews.

```bash
git push -u origin econ-growth-sim-1034
gh pr create --base main --title "Economy growth sim: a tuning tool for growth and labour scarcity (#1034)" --body-file <scratch>/pr_body.md
```
