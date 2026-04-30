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
(margin > 0 but breakeven < 0.01).

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

Not a smooth distribution: 808 PMs fall into clear buckets.

| Bucket | Count (extra_pms) | Count (unique_pms) |
|---|---|---|
| OK (margin in normal range) | 55 | 106 |
| DEEP-LOSS (margin < -50%) | 139 | 0 |
| HIGH-PROFIT (margin > 100%) | 86 | 128 |
| HIGH-WAGE (breakeven > 0.30) | 121 | 48 |
| LOW-WAGE | 19 | 0 |
| NO-COSTS (no input/output to compute) | 45 | 45 |

**Almost all of `extra_pms.txt`'s "DEEP-LOSS" PMs are -100% margin** —
these are inputs-only or throughput-only PMs whose value is in the
modifier block, not in goods produced. The auditor cannot see modifier
contribution, so flags them as broken when they're correct-by-design.
Examples: `pm_national_labs`, `pm_ai_assisted_research`,
`pm_internet_communications`. These are research / communications PMs
that consume inputs to produce a modifier (e.g. `country_innovation_mult`
or building throughput).

**Open question (T1):** which DEEP-LOSS PMs in the table are actually
broken (cost vs throughput out of whack) vs intended throughput-only
PMs? A second-pass audit would need to parse the modifier block too,
not just goods costs.

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

### Theme 5: Throughput-only / modifier-only PMs at -100% margin

The 139 DEEP-LOSS rows are dominated by PMs at exactly -100% margin
with negative-or-zero wage breakeven values like `-2.5`, `-5.6`,
`-40.0`. These mean: the PM has inputs but no goods output (or
trivially small output). They exist purely to apply a modifier (often
a research speed boost, communications system buff, or building
throughput multiplier).

Examples:
- `pm_national_labs`, `pm_academic_computing`, `pm_ai_assisted_research`
  — research-system PMs.
- `pm_internet_communications`, `pm_teletype_communications` — comms.
- `pm_continuous_bleaching`, `pm_programmable_paper`, etc. — late-era
  throughput upgrades.

These are not bugs — they're how the mod represents "researcher
salaries" or "throughput infrastructure" — but the auditor flags them
all the same.

**Open question (T5):** is there a tagging convention to mark a PM as
"deliberately negative goods balance, evaluate on modifier contribution"?
If not, future audits will keep flagging these. A `# AUDIT: throughput`
comment in the source would let the audit script skip them.

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

### DEEP-LOSS — first 5 entries (representative pattern)

These are throughput/research PMs at -100%, expected to deliver value
through modifier blocks the auditor doesn't see:

| pm_id | wage_be |
|---|---|
| `pm_large_scale_earth_movers_iron_mine` | 0.160 |
| `pm_national_labs` | -2.500 |
| `pm_academic_computing` | -5.330 |
| `pm_ai_assisted_research` | -11.000 |
| `pm_internet_communications` | -40.000 |

---

## Open questions for back-and-forth

1. **T1**: Which DEEP-LOSS PMs are intentionally throughput-only vs
   actually broken? Is there a way to tag them?
2. **T2**: Are the 200–800% margin HIGH-PROFIT outliers (excluding
   `pm_solar_receiver`'s metric artifact) properly compensated by
   construction cost on their parent buildings?
3. **T3**: Is the 39% HIGH-PROFIT rate in `unique_pms.txt` intended?
   Should company PMs be reined in toward, e.g., a 60% target median?
4. **T4**: Are the 121 HIGH-WAGE PMs clustering into intended labor-heavy
   buildings (universities, hospitals, research) or leaking into
   industrial PMs?
5. **T5**: Add a tagging convention (`# AUDIT: throughput-pm`) for
   modifier-only PMs so the audit script can flag them as
   "intentional negative balance".
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
