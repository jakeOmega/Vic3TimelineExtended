# Transport goods (#1050) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `transportation` becomes all movement inside a state (pops and industry), `merchant_marine` becomes shipping between markets, railways and ports supply infrastructure per level, and the AI stops subsidizing railways and ports.

**Architecture:** A one-off Python script holds the classification table and rewrites the production methods. A test imports the same table and checks the live files, so the construction fallback (§ 2) flips both with one flag. The building, AI, prestige-good, loc and docs changes are hand edits.

**Tech Stack:** Paradox script (`common/`), Python 3.11/3.12 (`unittest`), the mod state server (worktree copy on :8951) for `pm_costs` comments and the audits.

**Spec:** `docs/superpowers/archive/specs/2026-10-21-transport-goods-design.md`

## Global Constraints

- Converted quantities × 50/30 (merchant marine base 50, transportation base 30), rounded to the nearest 0.5.
- Merchant marine consumers after the change: Trade Centre methods only (vanilla's four plus the mod's `pm_trade_center_trade_quantity_advanced_1`–`_4`).
- Prestige goods stay on `merchant_marine`. Every company that lists one keeps a roster building that makes it.
- No `PRICE_RANGE` / `BUY_SELL_DIFF_AT_MAX_FACTOR` change. No level caps on ports or railways. Railway `should_auto_expand` stays vanilla's.
- Generated files are never hand-edited: `# Price:` comments come from `pm_costs`, emissions lines from `gen_carbon_capture_pms` (worktree `POST /reload`).
- A rewritten `.txt` keeps exactly one UTF-8 BOM.

## Review Focus

1. **A BOM in front of the first PM in `extra_pms.txt`.** The script must still find `pm_dragline_excavators_coal_mine`, and write exactly one BOM back (test 1.1).
2. **A method with both inputs** (`pm_department_stores` and four other urban centre methods): the converted amount adds to the existing `goods_input_transportation_add` line rather than writing a second key (test 1.2).
3. **The construction fallback rerun** (`--construction-good merchant_marine`) must leave the tree passing its own test (test 1.3).
4. **A port that INJECTs and REPLACEs the same vanilla PM** (`pm_industrial_port`, `pm_modern_port`): infrastructure must appear once, under `level_scaled` (test 2.1, plus the worktree reload's `generators_wrote_files`).
5. **A company whose roster no longer makes merchant marine** (SAP, Shopify): `prestige_good_roster_audit --strict` stays clean (Task 3).

---

### Task 1: Conversion script, classification test, PM rewrite

**Files:**
- Create: `scripts/generators/convert_transport_goods.py`
- Create: `test_transport_goods.py`
- Modify: `common/production_methods/extra_pms.txt`, `te_construction_market_pms.txt`, `unique_pms.txt`

**Interfaces:**
- Produces: `KEEP_MM_INPUT: frozenset[str]` (the Trade Centre PMs), `CONSTRUCTION_PMS: frozenset[str]` (the six `pm_*_buildings` construction sector methods, the four sector-tooling methods `pm_3d_printed_buildings`, `pm_computer_aided_design`, `pm_prefabricated_building_components`, `pm_tower_cranes`, and the six `pm_te_direct_construction_*`), `MM_OUTPUT_TO_TRANSPORTATION: frozenset[str]` (railway base methods, the five highway methods, `pm_generic_logistics_hub`, `pm_generic_rail_nexus`, `pm_alibaba_cainiao_park`, `pm_amazon_fulfillment_center`, `pm_shopify_fulfillment_hub`, `pm_volkswagen_autostadt`), `convert(text: str, construction_good: str = "transportation") -> str`, `main(argv)`.
- `construction_good="merchant_marine"` converts the construction methods' `transportation` input back (× 30/50) and leaves the rest alone.

- [ ] **1.1** Test `test_bom_and_first_pm`: `convert()` on `"﻿pm_a = {\n\tbuilding_modifiers = {\n\t\tworkforce_scaled = {\n\t\t\tgoods_input_merchant_marine_add = 3\n"...` returns text starting with exactly one `﻿` and `goods_input_transportation_add = 5`.
- [ ] **1.2** Test `test_merges_into_existing_input`: a block with `goods_input_merchant_marine_add = 0.5` and `goods_input_transportation_add = 3` comes back with one `goods_input_transportation_add = 4` (3 + 0.83 → 3.83 → 4) and no merchant marine line.
- [ ] **1.3** Test `test_construction_round_trip`: converting a construction method to transportation and back with `construction_good="merchant_marine"` returns its original quantity.
- [ ] **1.4** Live-file tests (read the three PM files, `utf-8-sig`):
  - `test_no_stray_mm_consumers`: every PM block with `goods_input_merchant_marine_add` is in `KEEP_MM_INPUT` (or in `CONSTRUCTION_PMS` when the module's `CONSTRUCTION_GOOD` constant says `merchant_marine`).
  - `test_converted_producers`: no PM in `MM_OUTPUT_TO_TRANSPORTATION` outputs merchant marine.
  - `test_single_bom`: each file starts with exactly one BOM.
- [ ] **1.5** Run `python3 test_transport_goods.py`: the unit tests (1.1–1.3) fail on the missing module.
- [ ] **1.6** Write the script. It finds each PM block by brace depth on the BOM-stripped text, rewrites only `goods_(input|output)_merchant_marine_add` lines in the classified PMs, drops their trailing `# Price` comment (pm_costs restores it), and keeps tabs.
- [ ] **1.7** Run it on the three files. `git diff --stat` shows only those three. Run `python3 test_transport_goods.py`: all pass.
- [ ] **1.8** Commit.

### Task 2: The four buildings

**Files:** `common/production_methods/extra_pms.txt` (railway, port, highway PMs), `common/production_method_groups/extra_pm_groups.txt:1373-1391`, `test_transport_goods.py`

- [ ] **2.1** Test `test_infrastructure_per_level`: in every railway method (base and passenger groups) and every port base method, `state_infrastructure_add` sits under `state_modifiers > level_scaled` and never under `workforce_scaled`.
- [ ] **2.2** Move railway infrastructure (including `pm_bullet_trains` 5 and `pm_maglev_trains` 10) and the mod's port infrastructure (`pm_container_ports` 15, `pm_global_ports` 30, `pm_magnetic_drive_ports` 50) to `level_scaled`, same amounts.
- [ ] **2.3** Add `REPLACE:pm_basic_port`, `REPLACE:pm_industrial_port`, `REPLACE:pm_modern_port` before the mod's port methods. Restate vanilla's bodies (`11_private_infrastructure.txt:15-90`) with infrastructure 3/4/5 under `level_scaled`. An INJECT can't remove vanilla's `workforce_scaled` line.
- [ ] **2.4** Passenger tiers: bring input cost at base prices to about 40–45% of output value for `pm_double-decker_passenger_carriages`, `pm_bullet_trains`, `pm_maglev_trains` and all five port passenger tiers. Outputs are unchanged.
- [ ] **2.5** `pmg_water_personal_transport` keeps `most_productive`: with modest inputs a flooded tier loses little, while each switch costs retooling (up to 43% of India's bill). Rewrite the comment to say so.
- [ ] **2.6** Highways: the script's conversion already turned their merchant marine into transportation. Airports are unchanged, since transportation is already the larger part.
- [ ] **2.7** Worktree `POST /reload` (port 8951). Check `warnings` and `generators_wrote_files`, then that no port PM ends up carrying infrastructure twice. Run the tests and commit together with the regenerated comments.

### Task 3: AI subsidies, prestige goods, Amazon

**Files:** `common/ai_strategies/te_power_plant_subsidy_strategies.txt` → `te_ai_subsidy_strategies.txt`, `test_power_plant_subsidy_strategies.py` → `test_ai_subsidy_strategies.py`, `edited_default_strategy.txt:325`, `docs/testing/ai-economy-playtest.md:58`, `common/company_types/` (SAP, Shopify)

- [ ] **3.1** Test: each of the seven INJECTs sets `building_power_plant`, `building_railway` and `building_port` to `should_remove`. Run it and see it fail.
- [ ] **3.2** `git mv` both files, add the two keys to every INJECT, and extend the header with #1050. Fix the references to the file name.
- [ ] **3.3** Drop `prestige_good_integrated_logistics` from SAP and Shopify. Both keep Generic Software, and neither roster makes merchant marine any more. Amazon keeps its `goods_production_rank(g:merchant_marine)` gate (its prestige good and roster port are on merchant marine).
- [ ] **3.4** `python3 prestige_good_roster_audit.py --strict` is clean and the test passes. Commit.

### Task 4: Loc, docs, player guide, play-test list

- [ ] **4.1** Loc:
  - Delete the two goods-name overrides (`timeline_extended_override_l_english.yml:23,26`), so vanilla's "Merchant Marine" and "Transportation" show.
  - Add `pmg_passenger_trains:0 "Rolling Stock"`.
  - Rename the water group to "Passenger Ships" and its none method to "No Passenger Ships".
  - Run `organize_loc.py`.
- [ ] **4.2** `docs/systems/mod_systems.md` § "Bulk Transportation (Merchant Marine relocalization)" rewritten as the transport model, keeping the Trade Centre seeding paragraph. `docs/vanilla/vanilla_economy_reference.md` § 17.1 link updated.
- [ ] **4.3** Player guide:
  - `01-introduction.md:184`
  - `02-timeline.md` (lines 203, 233-239, 431)
  - `03-economy.md` (line 10; lines 342-359; § "Bulk Transportation and freight" rewritten as "Transportation and shipping", including the construction-hub note from spec § 10)
  - `15-climate.md:279`
  - `17-reference.md` (lines 17, 67)

  Then the style lint and a PDF rebuild.
- [ ] **4.4** Add the spec § 7 observer checklist to `docs/testing/ai-economy-playtest.md`.
- [ ] **4.5** Commit.

### Task 5: Gate and PR

- [ ] **5.1** Run the targeted tests, `ruff`, the tab check, `organize_loc --check`, `check_localization_files.py`, the player guide `--check` and the `--strict` audits that read PMs or companies (`prestige_good_roster`, `pm_employment`, `loc_coverage`). Check the worktree reload's `warnings`.
- [ ] **5.2** Run one whole-branch review subagent (script and docs).
- [ ] **5.3** Push and open the PR against `main`. Its body lists the classification, each builder's call, a Player guide line and `Closes #1050`.
