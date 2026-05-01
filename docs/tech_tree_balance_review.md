# Tech Tree Balance Review (Eras 6–9)

## Scope and method

Scope: 115 mod-side techs across eras 6–9 (37 + 26 + 24 + 28).

Method: a one-off auditor (`scripts/analysis/tech_balance_audit.py`)
parses each tech's `modifier = { }` block, sums absolute modifier
values, and flags within-era outliers (top 15% sum-abs as STRONG;
zero-modifier techs as WEAK\*).

**Big caveat the metric carries:** sum-abs treats a `+1` flat add the
same as a `+1.0` multiplicative — so a tech with one `country_authority_add = 100`
gets an outsized score next to a tech with `country_innovation_mult = 0.10`.
The auditor surfaces candidates worth inspecting; it does not
resolve balance by itself. Cross-reference against:
- What the tech `unlocks_*` in `unlocking_*` clauses elsewhere.
- Buildings / decrees / PMs / combat-units gated by it
  (`/technology-effects/<tech>` once the mod-state-server is up).
- The actual modifier types in its block (an `_add` of 100 on a
  bureaucracy modifier means very different things to the player than
  100 on `country_authority_add`).

A `WEAK*` flag now means **zero modifier-block effects AND zero
unlocks** — the audit's "I can't see anything in this tech" verdict.
Techs with empty modifier blocks but a non-empty unlock set get a
new `UNLOCK-ONLY` flag instead, with a per-tech breakdown showing
what they actually gate. This was T3's central question: is each
WEAK\* tech utility-tier, stack-tier, or genuinely empty? The
auditor now answers it directly.

The unlock annotation comes from the shared `tech_unlocks_lib`
(also feeding the mod state server's `/tech-unlocks` endpoint) and
the annotator registry — PM unlocks pick up their balance flag
(`HIGH-PROFIT` / `THROUGHPUT` / etc.) from `pm_balance_lib` so the
"4 PMs (3 OK, 1 HIGH-PROFIT)" rollup works out of the box.

---

## Themes

### Theme 1: Modifier inflation across eras

The within-era median sum-abs is non-monotonic in mid-mod, but the
ceiling (range max) climbs steadily, and **mod modifier density sits
1–2 orders of magnitude above vanilla's**:

| Era | Median sum-abs | Range max | Source |
|---|---|---|---|
| era_1 | 0.05 | 62.00 | vanilla |
| era_2 | 0.10 | 31.20 | vanilla |
| era_3 | 0.05 | 31.05 | vanilla |
| era_4 | 0.00 | 31.00 | vanilla |
| era_5 | 0.05 | 26.30 | vanilla |
| era_6 | 3.10 | 101.25 | mod |
| era_7 | 1.60 | 110.10 | mod |
| era_8 | 15.00 | 101.15 | mod |
| era_9 | 19.27 | 155.10 | mod |

(Pull fresh figures with `.venv/bin/python scripts/analysis/tech_balance_audit.py --include-vanilla`.)

**T1 (resolved):** vanilla does *not* inflate — its median per era
hovers around 0.0–0.1 across all 5 eras and its peak caps near 30
(except `urbanization` at 62). The mod's era_6 starts ~30× vanilla's
era_5 median and the gap grows from there. The doubling-per-era story
is mod-specific, not vanilla mimicry. Whether that's intended power
inflation or modifier creep is still an open call, but the comparison
makes clear the mod has *introduced* the inflation rather than
inheriting it.

The era_6 → era_7 drop (3.10 → 1.60 median) is partly an artifact of
decolonization moving from era_7 to era_6 (per the decolonization
review's #1 followup); the era_7 cohort lost its biggest-modifier
tech without picking up a replacement.

### Theme 2: A small number of techs dwarf the rest within each era

The top STRONG outlier in each era carries 5×–35× the era's median
modifier value:

- **era_6**: `intergovernmental_organizations` (101.25) and
  `rural_electrification` (100.85) are 33× the era median (3.10).
  `decolonization` (53.60) joins this cohort after its move from era_7.
- **era_7**: `tactical_nuclear_weapons` (110.10) is 69× the median (1.60).
- **era_8**: `precision_guided_munitions` (101.15) is 7× the median.
- **era_9**: `network_centric_warfare` (155.10) and
  `unmanned_aerial_vehicles` (151.40) are 8× the median.

These outliers are likely real but they need inspection — many of them
may be using big flat-add modifiers (authority/bureaucracy/construction)
that the metric over-weights. **Open question (T2):** are the topline
ones actually overpowered in play, or are they correctly weighty
"keystone" techs that just look big to the auditor?

### Theme 3: Empty modifier blocks resolve as utility-tier (not stack-tier)

Eight era_6 techs and three era_7 techs have **no modifier block**.
With the unlock annotation now wired in, every one resolves cleanly
into the `UNLOCK-ONLY` flag plus a concrete payload:

| Tech | Era | Unlocks |
|---|---|---|
| `isoprene` | era_6 | 1 building (synthetic_rubber) |
| `bombing_aircraft` | era_6 | 1 combat unit · 1 law |
| `modern_materials` | era_6 | 1 building · 9 PMs (4 HIGH-PROFIT, 3 HIGH-WAGE, 1 OK, 1 LOW-WAGE) |
| `modern_tools` | era_6 | 1 building · 8 PMs (6 OK, 1 HIGH-PROFIT, 1 HIGH-WAGE) |
| `motorized_artillery` | era_6 | 1 combat unit |
| `semiautomatic_rifle` | era_6 | 2 PMs (1 HIGH-WAGE, 1 HIGH-PROFIT) |
| `aluminum_mass_production` | era_6 | 1 building · 1 PM (1 HIGH-WAGE) |
| `modern_management_techniques` | era_6 | 6 PMs (4 THROUGHPUT, 1 HIGH-PROFIT, 1 HIGH-WAGE) |
| `advanced_military_aircraft` | era_7 | 1 mob option · 1 PM (1 HIGH-PROFIT) |
| `pollution_control` | era_7 | 1 building · 1 decree · 1 law · 7 PMs (5 THROUGHPUT, 2 NO-COSTS) |
| `advanced_submarine_technology` | era_7 | 1 PM (1 HIGH-WAGE) · 1 ship type |

**T3 (resolved):** every one of the 11 originally-WEAK\* techs has a
real unlock payload. Most are utility-tier (one or two PMs / one
building), with a few multi-system entries — `modern_materials` (1
building + 9 PMs), `modern_tools` (1 building + 8 PMs), and
`pollution_control` (10 entities across 4 types) being the heaviest.
There are zero genuinely empty techs in the early mod tree.

> **Audit gotcha caught while resolving T3:** the inverted-index
> walker initially missed Clausewitz merge-directive prefixes
> (`INJECT:`, `REPLACE:`, `REPLACE_OR_CREATE:`) — the regex's
> identifier class didn't allow `:`, so any entity declared as
> e.g. `REPLACE_OR_CREATE:building_synthetics_plant_rubber` fell
> out of the walk and its `unlocking_technologies` block was
> silently skipped. Fix: `tech_unlocks_lib.iter_top_level_blocks`
> now strips the prefix and yields the underlying entity id.
> Regression test: `test_tech_unlocks_lib.test_clausewitz_merge_directive_prefixes`.
> Across the mod, ~250 directive-prefixed entities had been
> hidden from the index; the fix grew the unlock total from
> ~395 to 646 entries. The doc's Theme-3 table reflects the
> post-fix counts.

The fact that the 11-tech list includes 0 stack-tier outliers means
the early mod tree's WEAK\* footprint is **less concerning than the
original audit suggested** — the WEAK\* category was conflating
three distinct shapes (utility-tier with unlocks, multi-system
keystone with unlocks, and genuinely empty) that the new flag
separates.

**Vanilla comparison:** vanilla era_1–5 has *18–20 UNLOCK-ONLY techs
per era* (out of 24–41), suggesting vanilla relies more heavily on
unlocks and less on modifier blocks than the mod's late-era tech
design does. The mod's era_6+ inverts that pattern — keeping its
era_6 cohort of 7 UNLOCK-ONLY techs as a deliberate continuation of
the vanilla style, then leaning into modifier-heavy techs from era_7
on. Worth a sanity-check: are the era_8+ unlock-only PMs (e.g.
`integrated_circuits` 6 PMs, `advanced_assembly_lines` 7 PMs) carrying
their weight without modifier block backing?

### Theme 4: Society category gets the heaviest modifier blocks

Across all four eras, the highest-`modifier_count` techs are mostly
society-category:

- `decolonization` (era_6): 10 modifiers, sum 53.60
- `television_broadcasting` (era_7): 9 modifiers, sum 54.35
- `pop_culture` (era_8): 7 modifiers, sum 55.20

By contrast, military techs tend to have fewer modifiers but higher
per-modifier magnitudes (offense / defense / morale numbers can be
chunky).

**Open question (T4):** intentional? Society techs may legitimately
need to express many different small effects to model "civil rights /
welfare / TV changes everything a little"; military techs naturally
concentrate into a few big buffs. But it's worth confirming this is
deliberate vs. unevenness across authors/eras.

### Theme 5: Era 9 production techs cluster around 100+ sum-abs

Five era_9 techs all hit 100+: `world_wide_web` (105),
`digital_telecommunications` (104.05), `cloud_computing` (103),
`digital_entertainment` (103), `network_centric_warfare` (155.10).

Many of these likely have `country_innovation_mult = 1.0` or similar
flat huge-add bureaucracy modifiers driving the score. **Open
question (T5):** are these genuinely 5× as powerful as a typical
era_9 tech, or are they hitting the metric because of one or two
big-number modifiers in their block?

---

## Outlier table — flagged subset

(Produced by the auditor. Not exhaustive; OK-flagged techs not shown.
Re-run `.venv/bin/python scripts/analysis/tech_balance_audit.py` for
fresh data.)

| id | era | cat | n_mod | sum_abs | flag |
|---|---|---|---|---|---|
| `intergovernmental_organizations` | era_6 | society | 3 | 101.25 | STRONG |
| `rural_electrification` | era_6 | society | 4 | 100.85 | STRONG |
| `public_works_programs` | era_6 | society | 5 | 66.10 | STRONG |
| `nuclear_weapons` | era_6 | military | 6 | 61.90 | STRONG |
| `decolonization` | era_6 | society | 10 | 53.60 | STRONG |
| `combined_arms` | era_6 | military | 2 | 51.00 | STRONG |
| `fluorescent_lamps` | era_6 | production | 2 | 30.20 | STRONG |
| `isoprene` | era_6 | production | 0 | 0.00 | WEAK\* |
| `bombing_aircraft` | era_6 | military | 0 | 0.00 | WEAK\* |
| `modern_materials` | era_6 | production | 0 | 0.00 | WEAK\* |
| `modern_tools` | era_6 | production | 0 | 0.00 | WEAK\* |
| `motorized_artillery` | era_6 | military | 0 | 0.00 | WEAK\* |
| `semiautomatic_rifle` | era_6 | military | 0 | 0.00 | WEAK\* |
| `aluminum_mass_production` | era_6 | production | 0 | 0.00 | WEAK\* |
| `modern_management_techniques` | era_6 | society | 0 | 0.00 | WEAK\* |
| `tactical_nuclear_weapons` | era_7 | military | 4 | 110.10 | STRONG |
| `mainframe_computers` | era_7 | production | 6 | 57.05 | STRONG |
| `television_broadcasting` | era_7 | society | 9 | 54.35 | STRONG |
| `advanced_military_aircraft` | era_7 | military | 0 | 0.00 | WEAK\* |
| `advanced_submarine_technology` | era_7 | military | 0 | 0.00 | WEAK\* |
| `precision_guided_munitions` | era_8 | military | 5 | 101.15 | STRONG |
| `computer_networks` | era_8 | production | 6 | 57.50 | STRONG |
| `pop_culture` | era_8 | society | 7 | 55.20 | STRONG |
| `personal_computers` | era_8 | production | 3 | 55.00 | STRONG |
| `advanced_materials_armor` | era_8 | military | 0 | 0.00 | WEAK\* |
| `integrated_circuits` | era_8 | production | 0 | 0.00 | WEAK\* |
| `advanced_assembly_lines` | era_8 | production | 0 | 0.00 | WEAK\* |
| `computer_aided_design` | era_8 | production | 0 | 0.00 | WEAK\* |
| `network_centric_warfare` | era_9 | military | 4 | 155.10 | STRONG |
| `unmanned_aerial_vehicles` | era_9 | military | 5 | 151.40 | STRONG |
| `world_wide_web` | era_9 | production | 5 | 105.00 | STRONG |
| `digital_telecommunications` | era_9 | production | 4 | 104.05 | STRONG |
| `cloud_computing` | era_9 | production | 2 | 103.00 | STRONG |
| `digital_entertainment` | era_9 | society | 4 | 103.00 | STRONG |
| `virtual_reality` | era_9 | society | 0 | 0.00 | WEAK\* |

---

## Open questions for the back-and-forth phase

1. **T1 (modifier inflation curve):** is the era_6 → era_9 doubling-per-era
   power curve intended, or accidental?
2. **T2 (top-tier outliers):** are
   `network_centric_warfare`, `unmanned_aerial_vehicles`,
   `tactical_nuclear_weapons`, `intergovernmental_organizations` etc.
   actually too strong in play, or are they the keystone techs they
   appear to be?
3. ~~**T3 (unlock-only techs)**~~ (resolved): each ex-WEAK\* tech is now
   classified as `UNLOCK-ONLY` with a concrete unlock breakdown — see
   Theme 3 for the per-tech table. **Zero** techs are genuinely
   empty after the directive-prefix bug fix.
4. **T4 (society category density):** intentional that society techs
   carry many small modifiers vs military techs concentrating into
   fewer big ones?
5. **T5 (era_9 100+ cluster):** is the cluster of 5 era_9 techs at
   100+ sum-abs justified, or are some inflating from individual
   too-large modifiers?
6. **Cross-era specific concerns:** `decolonization` at 10 modifiers
   stacked is unusual; worth specifically reviewing.
7. ~~**Vanilla baseline**~~ (resolved): the auditor now accepts
   `--include-vanilla` and pulls vanilla era_1–5 techs as a baseline.
   Vanilla medians stay near zero across all five eras (max 0.10) and
   the heaviest vanilla tech (`urbanization`, era_1) hits 62 — half of
   what mod era_6's heaviest hits. Mod has introduced the modifier
   inflation, not inherited it from vanilla.

---

## Recommended follow-up workflow

1. Read this doc; pick which themes / specific techs to drill into.
2. For each tech we want to inspect: open `common/technology/technologies/era_X.txt`
   and check both the modifier block AND the surrounding tech's
   place in the unlocking chain.
3. For unlock-only techs: use `mod_state_server /technology-effects/<id>`
   (or grep `unlocking_technologies = { <id> }` across `common/`) to
   see what they actually unlock.
4. Decide which to retune; that's a separate implementation task.
