# PM/Building Balance Review

## Scope and method

Scope (PMs):
- `extra_pms.txt` — 465 PMs
- `unique_pms.txt` — 327 PMs (company-specific PMs)
- `strategic_reserve_pms.txt`, `resettlement_pms.txt`,
  `fmc_construction.txt` — 16 PMs (no cost comments — these are
  modifier-only PMs by design)

**Total: 808 mod-side PMs.**

Method: a one-off auditor (`scripts/analysis/pm_balance_audit.py`)
parses the auto-generated cost-comment block that `pm_costs.py` emits
in front of every PM and tabulates profit, margin %, and wage breakeven.
Outliers are flagged as `HIGH-PROFIT` (margin > 100%), `DEEP-LOSS`
(margin < -50%), `HIGH-WAGE` (wage breakeven > 0.30), `LOW-WAGE`
(margin > 0 but breakeven < 0.01), or `THROUGHPUT` (modifier-only PM
with zero goods output and at least one non-goods modifier line).
THROUGHPUT PMs are excluded from the outlier table and from the median
margin to keep the noise out — they're correct-by-design rather than
broken. PMs that need to override the auto-detection can add a
`# AUDIT: throughput-pm` comment in their body.

Buildings (rough scope):
- `extra_buildings.txt`, `fmc_construction.txt`, `strategic_reserve.txt`,
  `wonders.txt`, `company_buildings.txt`, `resettlement.txt`.
- Building-level metrics (construction cost, max workforce) require the
  mod_state_server to compute properly; this doc focuses on PM-level
  data which is parsable directly from comments.

**Mod design philosophy reminder (from user):** Era 6+ PMs *should* be
better than vanilla peers (vanilla only goes through era 5). Outlier
flagging here is **within-mod relative**, not vs vanilla.

---

## Themes

### Theme 1: `extra_pms.txt` margin distribution is bimodal

Not a smooth distribution: 808 PMs fall into clear buckets (re-run
post throughput tagging).

| Bucket | Count (extra_pms) | Count (unique_pms) |
|---|---|---|
| OK (margin in normal range) | 55 | 106 |
| THROUGHPUT (modifier-only) | 134 | 0 |
| DEEP-LOSS (real loss, margin < -50%) | 5 | 0 |
| HIGH-PROFIT (margin > 100%) | 86 | 128 |
| HIGH-WAGE (breakeven > 0.30) | 121 | 48 |
| LOW-WAGE | 19 | 0 |
| NO-COSTS (no input/output to compute) | 45 | 45 |

The 134 modifier-only PMs in `extra_pms.txt` (research, comms,
throughput multipliers) are now auto-classified as `THROUGHPUT`. They
consume inputs to produce a `country_modifiers` / `building_modifiers`
block payload (e.g. `country_weekly_innovation_add`) and are
correct-by-design — the audit just couldn't see modifier value before
the tagging existed. Examples: `pm_national_labs`,
`pm_ai_assisted_research`, `pm_internet_communications`.

**T1 (resolved):** the 134 throughput false-positives are now
filtered out of the outlier table. The 5 remaining `DEEP-LOSS` rows in
`extra_pms.txt` are real losses worth eyeballing — see Theme 5.

### Theme 2: A handful of HIGH-PROFIT outliers are extreme

Single biggest outliers:

| PM | margin | profit | likely explanation |
|---|---|---|---|
| `pm_solar_receiver` | 285,614% | 29,989,500 | Likely zero/near-zero input + huge `electricity` output — solar input free |
| `pm_space_elevator` | 854% | 179,036,000 | Wonder-tier output |
| `pm_base_building_hydro_power` | 650% | 19,500 | Free water → power conversion |
| `pm_base_building_space_power` | 650% | 234,000 | Likely intended for orbital wonder tier |

`pm_solar_receiver` at 285,614% is almost certainly a divide-by-near-zero:
inputs ≈ 0 (sunlight is free) → margin denominator collapses. This isn't
a balance bug, but the metric breaks for self-powered PMs. **The other
HIGH-PROFIT outliers in the 200–800% range are worth inspecting** —
they may genuinely be too generous, or they may be intended for very
expensive wonder buildings whose construction cost balances the
outsized profit.

### Theme 3: `unique_pms.txt` (company PMs) skews systemically high

| File | Median margin | High-profit count |
|---|---|---|
| `extra_pms.txt` | 32.5% | 86/465 (18%) |
| `unique_pms.txt` | 91.3% | 128/327 (39%) |

Company-specific PMs (Toyota Kaikan Plant, Samsung Digital City, etc.)
are designed as flagship rewards, so a higher median is expected. But
**128 of 327 (39%) flagged HIGH-PROFIT** suggests the calibration may
be too generous. **Open question (T3):** is the 39% intended? A 200%-margin
unique PM is harder to justify than a 200%-margin generic late-game PM
because companies are picked by AI/player as a strategic choice — high
margins compound that decision.

### Theme 4: HIGH-WAGE PMs concentrate in `extra_pms.txt`

121 PMs in `extra_pms.txt` have wage_breakeven > 0.30, meaning >30% of
revenue must go to wages before the PM breaks even. This is fine in
moderation (some PMs are inherently labor-intensive: services,
research, healthcare). But 121 out of 465 (26%) is a lot. **Open
question (T4):** are these clustering in service/research buildings
(intended) or scattered into industrial PMs (concerning)? Need to
group by parent building.

### Theme 5: Five real DEEP-LOSS PMs to investigate

After throughput auto-classification filters out the 134 modifier-only
false positives, only 5 PMs in `extra_pms.txt` remain `DEEP-LOSS`. All
sit in the `pm_large_scale_earth_movers_*_mine` family at -50.6% to
-55.6% margin:

| pm_id | margin% | wage_be |
|---|---|---|
| `pm_large_scale_earth_movers_iron_mine` | -50.6 | 0.160 |
| `pm_large_scale_earth_movers_lead_mine` | -50.6 | 0.160 |
| `pm_large_scale_earth_movers_sulfur_mine` | -50.6 | 0.160 |
| `pm_large_scale_earth_movers_gold_mine` | -50.6 | 0.160 |
| `pm_large_scale_earth_movers_coal_mine` | -55.6 | 0.180 |

These are upgrade PMs — they substitute heavier inputs (electricity /
fuel) for labor in the existing mining buildings. A negative margin
on the upgrade tier is plausible if the building's total output and
employment scaling compensate, but it's worth a sanity-check pass:
either the input mix is too costly or the output volume scaling on
the parent buildings isn't keeping up. The same diesel/condensing
upgrade PMs (`pm_diesel_pump_*`, `pm_condensing_engine_pump_*`) are
flagged HIGH-PROFIT in the same family, which suggests the
electricity-fed earth-mover variant was scaled separately and never
re-balanced.

**T5 (resolved):** the auditor now supports two ways of marking a PM
as throughput-only:
1. **Auto-detection** (default): zero `Total output cost` + at least
   one non-`goods_input/output_*` line inside a modifier block.
2. **Explicit override**: place a `# AUDIT: throughput-pm` comment
   anywhere in the PM body. Useful for edge-case PMs that produce a
   trivial output but exist primarily for their modifier.

---

## Outlier table — top extremes (subset)

Selected extreme outliers; full list available by re-running
`pm_balance_audit.py`.

### Top 5 HIGH-PROFIT (likely intentional, worth inspection)

| pm_id | file | profit | margin% | wage_be |
|---|---|---|---|---|
| `pm_solar_receiver` | extra_pms | 29.99M | 285,614 | 0.000 |
| `pm_space_elevator` | extra_pms | 179.04M | 854 | 0.000 |
| `pm_base_building_hydro_power` | extra_pms | 19,500 | 650 | 3.550 |
| `pm_base_building_space_power` | extra_pms | 234,000 | 650 | 234.000 |
| `pm_diesel_pump_building_tech_metals_mine` | extra_pms | 4,000 | 500 | 0.800 |

### Top 5 HIGH-WAGE (wage_be > 1.0; high labor share)

| pm_id | wage_be |
|---|---|
| `pm_drone_delivery_systems` | 6.950 |
| `pm_quantum_dot_pigments` | 1.650 |
| `pm_advanced_material_fibers` | 1.400 |
| `pm_electrified_rotary_drilling_rigs` | 1.150 |
| `pm_diesel_pump_building_tech_metals_mine` | 0.800 |

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

1. ~~**T1**~~ (resolved): throughput PMs are now auto-classified;
   the 5 remaining DEEP-LOSS rows are real and listed in Theme 5.
2. **T2**: Are the 200–800% margin HIGH-PROFIT outliers (excluding
   `pm_solar_receiver`'s metric artifact) properly compensated by
   construction cost on their parent buildings?
3. **T3**: Is the 39% HIGH-PROFIT rate in `unique_pms.txt` intended?
   Should company PMs be reined in toward, e.g., a 60% target median?
4. **T4**: Are the 121 HIGH-WAGE PMs clustering into intended labor-heavy
   buildings (universities, hospitals, research) or leaking into
   industrial PMs?
5. ~~**T5**~~ (resolved): tagging convention implemented. Auto-detect
   covers the typical case; `# AUDIT: throughput-pm` is the manual
   override.
6. **Era progression sanity**: pick a PM family (e.g. iron-mining PMs
   across eras 4–9) and look at era-over-era profit improvement.
   Does it match the era-over-era tech progression curve from Task 12?
7. **Building-level audit**: this doc only covers PMs, not buildings.
   A building-level pass needs `mod_state_server` running to compute
   construction cost vs typical PM profit ratios.

---

## Recommended follow-up workflow

1. Run `.venv/bin/python scripts/analysis/pm_balance_audit.py` for
   fresh data after any PM edit.
2. To investigate a specific PM family, grep its parent building's
   `production_method_groups` and trace the PMs in that group:
   ```
   grep -n "pmg_iron_mining" common/buildings/extra_buildings.txt
   ```
3. For a building-level view, start the mod state server
   (`.venv/bin/python mod_state_server.py`) and use `/buildings` and
   `/raw/Building/<id>` endpoints.
4. Use `pm_balance.py --inputs goods:N --outputs goods:N --profit X` for
   precise per-PM what-if analysis.

---

## Caveats

- **Margin is goods-only.** PMs that exist for their modifier effects
  (research, comms, throughput) appear "broken" in this audit but are
  by-design. ~150 PMs fall into this bucket.
- **Profit is denominated in pre-modifier prices.** Post-tech price
  shifts and market-condition adjustments aren't reflected.
- **Wage breakeven** is a labor-cost ratio, not an absolute wage value.
  High wage_be means the PM only pays out if pop wages stay low; useful
  signal but not the whole picture.
