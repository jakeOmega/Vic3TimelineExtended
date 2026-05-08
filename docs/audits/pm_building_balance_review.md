# PM/Building Balance Review

## Scope and method

Scope (PMs):
- `extra_pms.txt` — 480 PMs
- `unique_pms.txt` — 331 PMs (company-specific PMs)
- `strategic_reserve_pms.txt`, `resettlement_pms.txt`,
  `te_construction_market_pms.txt` — 16 PMs (no cost comments —
  modifier-only PMs by design)

**Total: 827 mod-side PMs.**

Method: a one-off auditor (`scripts/analysis/pm_balance_audit.py`)
parses the auto-generated cost-comment block that `pm_costs.py` emits
in front of every PM and tabulates profit, margin %, and wage breakeven.
Outliers are flagged as `HIGH-PROFIT` (margin > 100%), `DEEP-LOSS`
(margin < -50%), `HIGH-WAGE` (wage breakeven > 0.30 — see metric
gloss below), `LOW-WAGE` (margin > 0 but breakeven < 0.01), or
`THROUGHPUT` (modifier-only PM with zero goods output and at least
one non-goods modifier line). THROUGHPUT PMs are excluded from the
outlier table and from the median margin to keep the noise out —
they're correct-by-design rather than broken. PMs that need to
override the auto-detection can add a `# AUDIT: throughput-pm`
comment in their body.

**`wage_breakeven` is the per-worker £/week wage at which the PM's
profit reaches zero**, computed as `profit / employment` in
`pm_costs.py:163`. Higher values mean the PM has more wage headroom —
the building can afford higher pop wages before going underwater. It
is *not* a share of revenue going to wages.

Buildings (rough scope):
- `extra_buildings.txt`, `te_construction_market_site.txt`,
  `strategic_reserve.txt`, `wonders.txt`, `company_buildings.txt`,
  `resettlement.txt`.
- Building-level metrics (construction cost, max workforce) require
  the mod_state_server to compute properly.

**Mod design philosophy reminder (from user):** Era 6+ PMs *should* be
better than vanilla peers (vanilla only goes through era 5). Outlier
flagging here is **within-mod relative**, not vs vanilla.

---

## Themes

### Theme 1: `extra_pms.txt` margin distribution is bimodal

Not a smooth distribution: 480 PMs in `extra_pms.txt`, 331 in
`unique_pms.txt`, fall into clear buckets.

| Bucket | Count (extra_pms) | Count (unique_pms) |
|---|---|---|
| OK (margin in normal range) | 55 | 108 |
| THROUGHPUT (modifier-only) | 136 | 0 |
| DEEP-LOSS (real loss, margin < -50%) | 5 | 0 |
| HIGH-PROFIT (margin > 100%) | 90 | 128 |
| HIGH-WAGE (breakeven > 0.30) | 121 | 48 |
| LOW-WAGE (margin > 0, breakeven < 0.01) | 20 | 2 |
| NO-COSTS (no input/output to compute) | 53 | 45 |

The 136 modifier-only PMs in `extra_pms.txt` (research, comms,
throughput multipliers) are auto-classified as `THROUGHPUT`. They
consume inputs to produce a `country_modifiers` / `building_modifiers`
block payload (e.g. `country_weekly_innovation_add`) and are
correct-by-design — the audit just couldn't see modifier value before
the tagging existed. Examples: `pm_national_labs`,
`pm_ai_assisted_research`, `pm_internet_communications`.

**T1 (resolved):** the 136 throughput false-positives are filtered out
of the outlier table. The 5 remaining `DEEP-LOSS` rows in
`extra_pms.txt` are real losses worth eyeballing — see Theme 5.

### Theme 2: HIGH-PROFIT outliers — resolved

Single biggest outliers:

| PM | margin | profit | status |
|---|---|---|---|
| `pm_solar_receiver` | 285,614% | 29,989,500 | metric artifact (input ≈ 0) |
| `pm_space_elevator` | 854% | 179,036,000 | wonder-tier, hosted on `building_space_elevator` (`construction_cost_canal` = 5000 → matches output magnitude) |
| `pm_base_building_hydro_power` | 650% | 19,500 | hosted on `building_hydro_plant`: `construction_cost_very_high`, `has_max_level = yes`, `possible = { on_river = yes }`. Slot- and terrain-limited — intentional |
| `pm_diesel_pump_building_tech_metals_mine` | 500% | 4,000 | sits in `pmg_mining_equipment_building_tech_metals_mine` (different group from earth-mover PMs); margin earned by offsetting heavier inputs in the substitution chain |

`pm_solar_receiver` at 285,614% is a divide-by-near-zero metric break
(sunlight is a free input), not a balance bug. The other named
outliers all sit on buildings that are either wonder-tier construction
cost, slot-capped, level-capped, or terrain-restricted, so the
generous PM margin is bounded by build constraints elsewhere.

**T2 (resolved):** the named HIGH-PROFIT outliers are intentional or
metric artifacts. The previously-listed `pm_base_building_space_power`
row was unused and has been removed from the mod.

### Theme 3: `unique_pms.txt` (company PMs) skews systemically high — resolved

| File | Median margin | High-profit count |
|---|---|---|
| `extra_pms.txt` | 61.3% | 90/480 (19%) |
| `unique_pms.txt` | 91.3% | 128/331 (39%) |

Company-specific PMs (Toyota Kaikan Plant, Samsung Digital City, etc.)
are designed as flagship rewards. The 39% HIGH-PROFIT rate is
intentional: unique PMs are restricted to one per building type and
gate behind expensive-to-build company buildings. The high margin
compensates for the construction-cost gate, not a balance bug.
**T3 (resolved).**

### Theme 4: HIGH-WAGE PMs — wage headroom, not labor cost

121 PMs in `extra_pms.txt` have wage_breakeven > 0.30, meaning each PM
can support pop wages of ≥0.30 £/worker/week before the building's
profit hits zero. This is *generous wage headroom*, which is healthy
for SoL — not a labor-cost concern. The flag is worth a look only if
a PM lands the headroom in an early-era building where pop wages are
unlikely to climb that high in normal play, or where the PM's headroom
is so large it dominates pop SoL on its own (e.g. `pm_drone_delivery_systems`
at 6.95, `pm_advanced_self_replicating_assemblers` at 95.0,
`pm_robotic_service_providers` at 775.0).

The genuinely concerning bucket is the **20 LOW-WAGE PMs** in
`extra_pms.txt` (margin > 0, wage_breakeven < 0.01). These break even
only when pop wages stay near zero — workers are economically
squeezed even though the building turns a profit.

**T4 (reframed):** the open question is whether the 20 LOW-WAGE PMs
cluster in a particular building type (intended labor-squeezing
sweatshop, e.g. early subsistence/colonial PMs?), or whether they
leak into PMs where workers should reasonably benefit from output.

### Theme 5: Five real DEEP-LOSS PMs — earth-movers need rebalance

After throughput auto-classification filters out the 136 modifier-only
false positives, only 5 PMs in `extra_pms.txt` remain `DEEP-LOSS`. All
sit in the `pm_large_scale_earth_movers_*_mine` family at -50.6% to
-55.6% margin, in the `pmg_steam_automation_*_mine` PM group:

| pm_id | margin% | wage_be |
|---|---|---|
| `pm_large_scale_earth_movers_iron_mine` | -50.6 | 0.160 |
| `pm_large_scale_earth_movers_lead_mine` | -50.6 | 0.160 |
| `pm_large_scale_earth_movers_sulfur_mine` | -50.6 | 0.160 |
| `pm_large_scale_earth_movers_gold_mine` | -50.6 | 0.160 |
| `pm_large_scale_earth_movers_coal_mine` | -55.6 | 0.180 |

These are substitution PMs in the `pmg_steam_automation_*_mine`
chain — they replace the previous tier (`pm_dragline_excavators_*`)
and add net input cost in exchange for reduced labor. The "loss" the
auditor reports is the per-PM delta the substitution adds, not the
building's net economics; the building is still net profitable when
pop wages clear the wage_breakeven (0.16–0.18 £/worker/week — well
under typical mid-game wages).

The rebalance signal is not the negative profit per se, but that
earth-movers (era 7) is the *locally-worst* substitution tier in the
chain — wage_breakeven climbs from dragline (0.07) → earth-movers
(0.16) → geophysical (0.15) → ore-sorting (0.10) → laser (0.00).
Era 7 is a regression off era-6 dragline, then era-8 ore-sorting
recovers. Earth-movers should sit between dragline and ore-sorting
on the cost-per-displaced-worker curve; today it overshoots both.

**Note:** `pm_diesel_pump_*` and `pm_condensing_engine_pump_*` are in
`pmg_mining_equipment_*`, not the steam-automation family. Their
HIGH-PROFIT flag is unrelated to the earth-mover issue.

**T5 (resolved):** the auditor supports two ways of marking a PM as
throughput-only:
1. **Auto-detection** (default): zero `Total output cost` + at least
   one non-`goods_input/output_*` line inside a modifier block.
2. **Explicit override**: place a `# AUDIT: throughput-pm` comment
   anywhere in the PM body. Useful for edge-case PMs that produce a
   trivial output but exist primarily for their modifier.

### Theme 6: Era progression sanity — iron-mining PM family

Iron-mining PMs across the three upgrade chains, ordered by unlocking
tech era:

| PM | group | era | margin% | wage_be |
|---|---|---|---|---|
| `pm_dragline_excavators_iron_mine` | steam_automation | 6 | -42.0 | 0.07 |
| `pm_high_pressure_hydraulic_pump_building_iron_mine` | mining_equipment | 6 | 77.8 | 0.40 |
| `pm_ammonium_nitrate_building_iron_mine` | explosives | 6 | 39.1 | 0.90 |
| `pm_large_scale_earth_movers_iron_mine` | steam_automation | 7 | **-50.6** | 0.16 |
| `pm_continuous_miners_building_iron_mine` | mining_equipment | 7 | 55.9 | 0.55 |
| `pm_geophysical_survey_techniques_iron_mine` | steam_automation | 8 | -32.2 | 0.15 |
| `pm_ore_sorting_and_separation_technology_iron_mine` | steam_automation | 8 | -20.0 | 0.10 |
| `pm_smart_miners_building_iron_mine` | mining_equipment | 10 | 76.9 | 1.88 |
| `pm_laser_excavation_technology_iron_mine` | steam_automation | 11 | 0.5 | 0.00 |
| `pm_metamaterial_explosives_building_iron_mine` | explosives | 11 | 86.0 | 14.80 |

The mining-equipment chain (output-boosting, additive) shows clean
era-over-era progression: wage headroom 0.40 → 0.55 → 1.88 across eras
6/7/10. Output also climbs 4.8K → 9.2K → 26K. Same direction for the
explosives chain (0.90 → 14.80 across eras 6 → 11), though the
metamaterial explosives jump is the family's largest and worth a
sanity check given its narrow employment base (250 workers).

The steam-automation substitution chain shows healthy decay in
cost-per-displaced-worker once you skip era 7: 0.07 → 0.15 → 0.10 →
0.00 across eras 6, 8, 8, 11. **Era 7 (earth-movers, 0.16) is the
local outlier in an otherwise monotone chain** — the rebalance hook
called out in Theme 5.

### Theme 7: Building-level audit (HIGH-PROFIT and DEEP-LOSS hosts)

Spot-check of the buildings hosting the named outliers, sourced from
`/raw/Buildings/<id>` on `mod_state_server`:

- **`building_space_elevator`** — `required_construction =
  construction_cost_canal` (5000 base, the highest tier in the game).
  Hosting a 179M-profit wonder PM is consistent with the construction
  cost: the PM only pays back after a campaign-spanning build.
- **`building_solar_receiver`** — `required_construction =
  construction_cost_medium` (400) with `bg_megastructure_capped_private`
  group, custom slot gate (`solar_receiver_slots_remaining > 0`), and
  `can_build_private = always = no`. Cheap to construct but slot- and
  ownership-gated. The 285K% margin is a metric artifact (input ≈ 0);
  per-level absolute profit is bounded by the slot cap.
- **`building_hydro_plant`** — `required_construction =
  construction_cost_very_high` (800), `has_max_level = yes`,
  `possible = { on_river = yes }`. Triple-gated (cost, level, terrain),
  so the 650% PM margin can't scale uncapped. Intentional.
- **`building_iron_mine`** / `building_coal_mine` /
  `building_lead_mine` / `building_sulfur_mine` /
  `building_gold_mine` — all `required_construction =
  construction_cost_medium` (400), no slot or terrain gating beyond the
  vanilla mine deposit. The DEEP-LOSS earth-mover PMs sit on plain
  industrial mines, so the rebalance impact is visible to the player
  during normal play (unlike the HIGH-PROFIT wonder PMs, which gate
  behind 5000-unit construction).

No new flags emerged from the building-level pass; the check confirms
that HIGH-PROFIT outliers all live on construction-, slot-, or
terrain-capped buildings, while the DEEP-LOSS earth-movers sit on
unconstrained industrial mines and therefore *do* warrant the
rebalance Theme 5 calls for.

---

## Outlier table — top extremes (subset)

Selected extreme outliers; full list available by re-running
`pm_balance_audit.py`.

### Top 5 HIGH-PROFIT (intentional or metric artifact)

| pm_id | file | profit | margin% | wage_be |
|---|---|---|---|---|
| `pm_solar_receiver` | extra_pms | 29.99M | 285,614 | 0.000 |
| `pm_space_elevator` | extra_pms | 179.04M | 854 | 0.000 |
| `pm_base_building_hydro_power` | extra_pms | 19,500 | 650 | 3.550 |
| `pm_magnetic_drive_trawlers` | extra_pms | 7,550 | 521 | 2.160 |
| `pm_diesel_pump_building_tech_metals_mine` | extra_pms | 4,000 | 500 | 0.800 |

### Top 5 highest wage headroom (wage_be > 1.0; abundant SoL bandwidth)

These are the PMs with the most pop-wage room. The flag does not
indicate a problem on its own — only worth attention if the headroom
sits in a building / era where wages will not realistically climb to
absorb it.

| pm_id | wage_be |
|---|---|
| `pm_robotic_service_providers` | 775.000 |
| `pm_artificial_personalities` | 106.000 |
| `pm_advanced_self_replicating_assemblers` | 95.000 |
| `pm_self_replicating_assemblers` | 46.330 |
| `pm_self_improving_AI_systems` | 34.640 |

### DEEP-LOSS — all real losses after throughput filtering

The remaining DEEP-LOSS entries are now genuine — throughput PMs are
auto-tagged and excluded:

| pm_id | margin% | wage_be |
|---|---|---|
| `pm_large_scale_earth_movers_iron_mine` | -50.6 | 0.160 |
| `pm_large_scale_earth_movers_lead_mine` | -50.6 | 0.160 |
| `pm_large_scale_earth_movers_sulfur_mine` | -50.6 | 0.160 |
| `pm_large_scale_earth_movers_gold_mine` | -50.6 | 0.160 |
| `pm_large_scale_earth_movers_coal_mine` | -55.6 | 0.180 |

---

## Open questions for back-and-forth

1. ~~**T1**~~ (resolved): throughput PMs are auto-classified;
   the 5 remaining DEEP-LOSS rows are real and listed in Theme 5.
2. ~~**T2**~~ (resolved): the named HIGH-PROFIT outliers are bounded
   by construction-cost / slot / terrain gates on their host
   buildings. `pm_base_building_space_power` was unused and removed.
3. ~~**T3**~~ (resolved): the 39% HIGH-PROFIT rate in
   `unique_pms.txt` is intentional — unique PMs are 1-per-building-type
   and gate behind expensive company buildings.
4. **T4 (reframed)**: do the 20 LOW-WAGE PMs in `extra_pms.txt`
   cluster into intended labor-squeezing buildings (early subsistence/
   colonial PMs?) or leak into PMs where workers should benefit from
   output? List available by re-running the audit and filtering to
   `LOW-WAGE`.
5. ~~**T5**~~ (resolved): tagging convention implemented. Auto-detect
   covers the typical case; `# AUDIT: throughput-pm` is the manual
   override.
6. ~~**T6**~~ (results inline above): era progression in the
   iron-mining family is monotone for output-boosting chains; the
   steam-automation substitution chain regresses at era 7
   (earth-movers) — see Theme 5.
7. ~~**T7**~~ (results inline above): HIGH-PROFIT outliers all sit on
   construction-/slot-/terrain-capped buildings; DEEP-LOSS
   earth-movers sit on unconstrained mines — confirms the rebalance
   priority.

---

## Recommended follow-up workflow

1. Run `.venv/bin/python scripts/analysis/pm_balance_audit.py` for
   fresh data after any PM edit.
2. For the earth-mover rebalance, target `pmg_steam_automation_*_mine`
   only (the pump PMs in `pmg_mining_equipment_*` are healthy):
   ```
   grep -n "pmg_steam_automation_" common/production_method_groups/extra_pm_groups.txt
   ```
3. To investigate a specific PM family, grep its parent building's
   `production_method_groups` and trace the PMs in that group:
   ```
   grep -n "pmg_iron_mining\|pmg_steam_automation" common/buildings/extra_buildings.txt
   ```
4. For a building-level view, start the mod state server
   (`.venv/bin/python mod_state_server.py`) and use `/buildings` and
   `/raw/Buildings/<id>` endpoints.
5. Use `pm_balance.py --inputs goods:N --outputs goods:N --profit X` for
   precise per-PM what-if analysis.

---

## Caveats

- **Margin is goods-only.** PMs that exist for their modifier effects
  (research, comms, throughput) appear "broken" in this audit but are
  by-design. ~150 PMs fall into this bucket and are auto-tagged as
  THROUGHPUT.
- **Profit is denominated in pre-modifier prices.** Post-tech price
  shifts and market-condition adjustments aren't reflected.
- **Wage breakeven is a per-worker £/week wage**, not a percentage.
  It's the wage at which the PM's profit hits zero
  (`profit / employment`, `pm_costs.py:163`). High wage_be = generous
  pop-wage headroom (healthy for SoL); low wage_be = the PM only pays
  out if pop wages stay low (workers economically squeezed).
- **Substitution PMs report a delta, not building economics.** The
  `pmg_steam_automation_*_mine` chain (earth-movers etc.) substitutes
  inputs for labor; the audit's "loss" is the per-PM delta the
  substitution adds, not the building's net economics. The
  wage_breakeven captures the actual sign change.
