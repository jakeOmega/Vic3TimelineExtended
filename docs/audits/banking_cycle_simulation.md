# Banking cycle simulation — distribution study, tuning recommendations, and the retune that shipped

**Date:** 2026-09-22 (study in the morning; the retune in §3 and the AI, fiscal and delegation changes in §5–§8 were written into the mod the same day).
**Tool:** `scripts/analysis/banking_cycle_sim.py` (Monte Carlo; numbers read from the mod files at import, control flow hand-ported).
**Reproduce:**

```
.venv/bin/python scripts/analysis/banking_cycle_sim.py --self-test
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 400 --years 100 --points 0,1,2,3,5,8                   # the mod as it stands
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 400 --years 100 --points 0,1,2,3,5,8 --tune pre_retune # approximately, as it stood before
```

**Reading order.** §1–§2 are the study of the system *as it stood on the morning of 2026-09-22* ("shipped" in
those sections means that state). §3 is the retune it proposed and the subset that was written into the mod.
§5–§8 are the second pass: what the growth mandate actually buys, the fiscal channel, the AI's tool weights,
and the final matrix of #371. §10 is the follow-up that lets a maxed player pull back a boom (and occasionally a
frenzy), with `--rescue` and the refreshed matrix. Every table states which script it measured.

---

## 1. What was simulated

The coupled loop of `je_banking_cycle`'s monthly pulse and `te_monetary_monthly_update`, one country at a
time, 100 years, 400 runs per cell. The matrix is **currency law × who steers the dial × intervention-point
budget**:

| axis | values |
|---|---|
| currency law | `law_commodity_money`, `law_gold_standard`, `law_fiat_currency`, `law_digital_currency` |
| dial | *nothing* (player never touches it — the target stays at its seeded whole point), *price stability* (mandate 1), *growth* (mandate 2), *peg defence* (mandate 3) |
| intervention points | 0, 1, 2, 3, 5, 8 — `banking_law_base_points_value` grants 1/3/4/5/7 by financial-regulation law, +1 for a national bank, so a real country holds 2/4/5/6/8 |

**Peg defence is a gold cell only.** `te_monetary_update_target` rewrites mandate 3 to price stability off
gold, so the other three cells would be byte-identical to their price-stability twins; they are dropped
rather than reported as separate results.

**0 points means the dashboard tools are never used and no crash-softening option is affordable** — every
`banking_crash_intervention_*` modifier costs 1–4 points for a year. So the 0-point column *is* the
"player does nothing at all" arm, and the higher columns are "player (or AI) uses the interventions".

### Fidelity

Control flow is hand-ported; every constant is read out of `common/script_values/`,
`common/static_modifiers/`, `common/laws/` and the buttons' own `ai_chance` blocks at import time, so the
simulation tracks a retune of those files without being edited. A renamed constant raises at startup rather
than silently falling back to a literal.

Three cycle-side checks were run against hand computation and all matched exactly: the crash weight at a
known state (frenzy, bubble 70 → w = 19.25, p = 16.14 %), one full `banking_cycle_advance_variables` month,
and the mean-reversion nudge's empirical probability at cycle 100 (16.7 %).

The monetary half is checked against the only oracle in the repo — the expected numbers in
`events/te_debug_monetary_events.txt`'s `.5`–`.7` header. `--self-test` runs sequence 1 (fiat, national
bank, not independent, delegation off, target 5, π = core = expected = 2, r\* = 3) and confirms the tuple
`(policy, π, expected, gap) = (5, 2.00, 2.00, 0.00)` reproduces over twelve months, as the header says it
must. It also runs sequence 3 and confirms the documented instability of a pinned manual target.

**Two engine semantics that change the answer:**

1. A `random_list` entry's probability is `w / (w + other weights)`, not `w / 100` — standard Clausewitz,
   but easy to lose. The crash check is `0 = { modifier = {…} }` against `100 = {}`, so `p = w / (w + 100)`.
2. Inside a `random_list` entry's `modifier` block, `value =` **replaces** the entry's literal weight; only
   `add =` accumulates onto it — checked against vanilla, which does the same
   (`game/common/scripted_effects/04_neg_event_options_scripted_effects.txt`,
   `5 = { modifier = { value = neg_option_7_modifier } }`). So the mean-reversion nudge's
   `25 = { modifier = { value = var:finance_cycle_value subtract = 50 divide = 5 } }` carries weight
   `(v−50)/5`, not `25 + (v−50)/5` — the literal 25s are dead, and the nudge can never fire at cycle 50.

**Deliberately out of scope (stated so the numbers are read correctly):**

- The 77 random events in `banking_cycle_events.txt`. They are most of the system's content, but each is a
  player *choice*. `--event-channel` adds a crude aggregate stand-in; it costs roughly **+2 crashes per
  century** and lowers mean severity, so the headline table slightly understates crash frequency.
- Contagion, crisis waves and the Great Depression chain — a single-country sim cannot model them.
- The FX index (held at par), monetisation, and the phase-5 arrangements.
- `ce_*` / `cw_*` tools: command economy and cooperative ownership are a different *economic* law.

**Sensitivities** (250 runs, all 26 mode cells, mean delta vs baseline):

| variant | crashes/century | severity | recession months |
|---|---|---|---|
| monetary pulse before the cycle pulse instead of after | −0.17 | −0.02 | −0.09 |
| AI clicks buttons 4× less often | +0.82 | +2.56 | +1.41 |
| AI clicks buttons 4× more often | −0.83 | −6.33 | −1.36 |
| aggregate stand-in for the random events | +2.15 | −10.44 | +1.40 |
| cycle phase allowed to move GDP growth | −0.07 | −0.13 | +0.97 |

The one-month stance-gap lag is genuinely harmless, which vindicates §16.3's decision to tolerate it. The
AI's click cadence is the largest single assumption on the intervention arms — it moves their crash rate by
3–4× — but never changes the *direction* of any conclusion.

---

## 2. What the shipped system does

Target band, from the owner's reading of 19th-century history: **5–15 crashes per century for commodity
money or the gold standard at 0–3 intervention points**, with well-managed fiat/digital a little rarer and
mismanaged fiat/digital worse.

Shipped, at 0 points: **commodity 5.1, gold 5.8** — the bottom of the band. At 3 points: **2.1 and 2.5**.
At 8 points: **0.4 and 0.6**. Nine findings, in rough order of how much they matter.

### F1 — Two intervention points cut the crash rate in half, and the whole budget curve is upside down

The system's headline lever is not the currency law and not the mandate — it is the point budget. Going
0 → 8 points cuts crashes by 5–40× at every currency law and every mandate. A fully-tooled country under
price stability sees **0.0–0.3 crashes per century**: the system stops existing.

The cause is not the tools' bubble suppression. It is their **momentum** term. Momentum decays ×0.9 a
month, so a *standing* `country_finance_momentum_monthly_add` of `x` converges on `x / 0.1 = 10x` cycle
points per month. The dashboard tools carry ±0.15 to ±0.35 there — worth ±1.5 to ±3.5 cycle points a month
— against the phase modifiers' own ±0.05 to ±0.2 (±0.5 to ±2). One 2-point tool is three times the entire
expansion-phase restoring force.

That also produces a **non-monotonic budget curve**. Instrumented phase occupancy for `gold`/*nothing*:

| budget | crashes/century | expansion % | boom % | bubble p90 |
|---|---|---|---|---|
| 0 pt | 8.1 | 11.7 | 3.4 | 31 |
| 1 pt | 5.9 | 9.2 | 2.4 | 22 |
| **2 pt** | **4.0** | **6.8** | **1.8** | **13** |
| 3 pt | 11.5 | 18.5 | 5.7 | 50 |
| 5 pt | 10.2 | 19.1 | 5.2 | 52 |

At exactly 2 points the only affordable tools are `banking_countercyclical_capital_buffer` and
`banking_raise_margin_requirements`, both of which carry −0.15 standing momentum; the country is held out
of the expansion band entirely. At 3 points `banking_directed_credit_infrastructure` (3 pts, +0.15
momentum, +0.3 bubble) becomes affordable and the cycle runs *hot*. **Two intervention points is the safest
budget in the game and three is among the most dangerous** — the opposite of the intent, and invisible
without a simulation.

### F2 — Almost every crash is a depression

`crash_severity` is seeded from `bubble_pressure` and the crash *probability* is also proportional to
`bubble_pressure`, so crashes only fire when the bubble is large and severity then starts from that same
large number. Instrumented over 300 simulated centuries of `gold`/*nothing* at 0 points:

| severity tier | share | what it does |
|---|---|---|
| systemic ≥ 80 | 43 % | cycle → 5, momentum → −5 |
| panic 60–80 | 24 % | cycle → 10, momentum → −4 |
| crash 40–60 | 22 % | cycle → 20 |
| downturn 20–40 | 9 % | cycle → 30 |
| correction < 20 | 2 % | cycle → 40 |

Two thirds of crashes drop the country into the panic band. Combined with a slow climb out (F3), the
passive arms show a **median longest slump of 187–241 months** — a twenty-year depression in the median
century. Historically the ratio is nearly inverted: many corrections, a few real depressions.

### F3 — The cycle is structurally depressive, and that is why crashes are rare

Mean cycle value under the shipped system is **36–48** in every low-intervention arm, not 50. Crashes reset
downward only, and the climb back is slow: momentum equilibrium is `add / 0.1`, so downturn (+0.1) climbs
at 1.0 cycle points a month and stagnation (+0.05) at 0.5. Getting from a post-crash 10 back to 40 takes
about 45 months.

Measured, the median climb from a crash back to cycle 40 is **22–31 months** — the arithmetic above gives
~45 for a panic-tier reset specifically, and the median crash is milder than that. So a single crash is not
the problem; the twenty-year slumps in F2 come from crashes landing on top of each other while the cycle is
still climbing.

The consequence is counter-intuitive and important for tuning: **crash frequency at low intervention is
limited by how long the bubble takes to rebuild, not by the per-month crash probability.** Raising the four
per-phase crash multipliers by 2–4× moved the 0-point crash rate from 5.0 to only 5.7, while sharply
raising it at high budgets. The system spends only 11–18 % of months in expansion or boom, which is where
bubble is generated at all. To get more crashes you must let the cycle spend more time hot, not make
crashes likelier.

### F4 — The crash check has no branch below cycle 40

```paradox
else_if = { limit = { var:finance_cycle_value >= 40 } subtract = 75  multiply = 0.02 }
# nothing below 40
```

The `if/else_if` chain in `banking_cycle_check_and_execute_crash` covers ≥88, ≥75, ≥60 and ≥40. Below 40
the weight falls through as **raw `bubble_pressure`**. At cycle 39 with bubble 50 that is
`p = 50/150 = 33 % a month`; at cycle 41 the same state gives `(50−75) → 0`. A two-point move in cycle
value swings the monthly crash probability from zero to a third.

It is reachable: a country falling fast out of boom crosses 40 in one month still carrying its bubble.
**20 % of price-stability crashes fire from the stagnation band** because of it.

### F5 — A player who never touches the dial under fiat or digital currency gets a different game

| | crashes/century | mean inflation | months in frenzy |
|---|---|---|---|
| `commodity` / nothing | 5.1 | −0.1 % | 1.2 % |
| `gold` / nothing | 5.8 | 0.0 % | 1.4 % |
| `fiat` / nothing | **49.6** | **22 %** | **13 %** |
| `digital` / nothing | **49.6** | **22 %** | **13 %** |

Two mechanisms. **The first is designed and documented; the second is not.**

1. **Inflation has no fixed point under fiat — and the mod knows.**
   `te_mon_pressure_regime_pull` subtracts core inflation only for a metallic, dollarised or crypto regime.
   For fiat and digital the only anchor is expectations, and `te_mon_credibility_eff` reaches zero once
   `|π − 2| ≥ te_mon_deanchor_span` (10), after which expected inflation chases realised and
   `core = pressure + expected` has no solution while pressure is positive. Inflation rises roughly
   **0.6 pp a year, without limit**.

   `events/te_debug_monetary_events.txt`'s sequence-3 header states this outright: *"With the de-anchoring
   `c_eff` that shipped there is NO fixed point under a held real stance once `P > 2.5 × c` … a boom phase
   alone (+0.8) clears it. A pinned manual target under standing pressure is therefore EXPECTED to drift
   away."* The header's own acceptance test is that it should be *"a slow climb the player has many chances
   to answer, not a runaway"* — and it is: `--self-test` reproduces 16.6 % after twenty pinned years in a
   boom. **This finding is not that the drift exists. It is what the drift does to the cycle.**

2. **The stance clamp saturates, and that is what produces the crashes.**
   `te_mon_stance_gap_clamped` bounds the gap at ±4. A frozen 3 % rate against 20 % inflation sits at −4
   *for ever*, so the cycle takes the maximum loose-money push (+0.5 momentum, +3 bubble) every single
   month — a boom-bust every 2.1 years. The inflation drift is meant to be answerable at leisure; the cycle
   consequence is not gradual at all, because the channel between them saturates within a few years and
   then stops distinguishing "somewhat loose" from "catastrophically loose".

   This is the half worth fixing, and it is isolable: narrowing only the **loose** side of the clamp from
   −4 to −2 takes the passive fiat arm from 49.6 to 35.0 crashes per century and leaves **every managed
   cell unchanged**, because a steered dial almost never reaches the clamp.

The escape hatch never opens either: `te_mon_band_edge_hyper` is **50**, and the drift parks around 22 %,
just inside band 5, so `te_inflation.1` (currency reform / dollarisation) fires about **0.8 times per
century**. Meanwhile `te_mon_band_edge_very_high` is 20 — exactly where the drift sits — so the country
carries `te_inflation_band_very_high` more or less permanently. Whatever the intended arc for an
unmanaged fiat currency, "parked one band below the crisis that would resolve it, for eighty years" is
unlikely to be it.

Fixing the inflation half alone does **not** fix the crash half. With a real-balance pull strong enough to
hold mean inflation at 5.7 %, the crash rate stayed at 47–48 per century, because a 3 % rate against 5.7 %
inflation still pins the stance gap past −4.

### F6 — The currency law barely touches the cycle

At the same mandate and budget the four currency laws land within ~30 % of each other on every cycle metric.
The only law-level grant the cycle reads is `country_banking_random_momentum_mult` (gold −0.1, digital
+0.5), and it scales the mean-reversion nudge — a term that is zero at cycle 50 and fires at most 16.7 % of
months (see §1, semantic 2). It is very nearly inert.

This is arguably correct by design: the currency law's job is the rate band and the price level, and it
does that (commodity money sits pinned at its band floor 24–61 % of months). But if the laws are meant to
*feel* different in the cycle panel, the lever has to be something the cycle actually reads.

### F7 — The growth mandate is four times as dangerous as price stability

19.9 vs 5.7 crashes per century on gold at 0 points; 17.8 vs 4.5 on fiat. `te_mon_mandate_growth_bias` runs
the rate a standing **−1.0 pp** loose, which through the stance channel is worth +0.125 momentum and
+0.75 bubble a month, permanently. A deliberate penalty is right; 4× is beyond the intended band.

### F8 — The fiscal channel is dormant by a factor of ~52 (verify in game)

```paradox
financial_cycle_government_fiscal_policy_effect_size = {
    value = total_expenses  subtract = income
    divide = { value = gdp min = 1 }
    multiply = 100          # no annualisation
}
te_mon_deficit_pct_value = {
    value = total_expenses  subtract = income
    multiply = te_mon_deficit_annualise_factor   # 52
    divide = { value = gdp min = 1 }
    multiply = 100
}
```

Both compute "the deficit as a percent of GDP" from the same weekly `total_expenses − income`, and they
differ by 52×. Only one can be right. If `gdp` is the annual figure — which the monetary value assumes — a
3 %-of-GDP deficit yields **0.058** cycle points a month, not the "1 point" the fiscal value's own comment
claims. That comment also records an earlier 5× patch made because the channel was observed "effectively
dormant", which is consistent with the real factor being 52 and the patch having treated a symptom.

Not fixed here because it needs one in-game observation to settle. `debug_log` both values on a country
with a known deficit and compare.

### F9 — Minor

- **Peg defence is worse than price stability on gold** (8.0 vs 5.7 crashes/century at 0 points) and holds
  the rate at a flat 2.70 %. The mandate ignores the domestic cycle by design, so it gives up the cycle
  lean that price stability uses to lean against a bubble. That is a coherent trade, but it is currently a
  strict downgrade for anyone not actually worried about reserves.
- **The commodity growth mandate leaves the dial inert 57–61 % of the time**, pinned at the band floor
  (price stability: 24–30 %). This is the mechanical half of the already-documented issue #352.

---

## 3. A retune, measured — and what shipped

Every change below was applied in the simulator and re-measured with the `--tune` keys, as the full
thirteen-key preset and before the AI, fiscal and delegation changes of §6–§8 — so the right-hand column of
the tables in *this* section is the morning's measurement, not the mod as it stands. The mod files now carry
the **shipped** column; a plain run reproduces §8's tables, and `--tune pre_retune` approximately restores
the left-hand column here.

| key | change | file | shipped 2026-09-22? |
|---|---|---|---|
| `below40` | add the missing `else = { subtract = 90  multiply = 0.01 }` branch under cycle 40 | `banking_cycle_effects.txt`, `banking_cycle_check_and_execute_crash` | **yes** |
| `sev_scale` | seed `crash_severity` from `0.55 ×` bubble pressure, not `1.0 ×` | same effect; the constant is `banking_crash_severity_scale_value` in `extra_script_values.txt`, and `banking_contagion_crash_check` seeds from it too | **yes** |
| `crash_mult` | the four per-phase crash multipliers `×1.2` | same effect | no — near zero in the ablation |
| `phase_bubble` | `country_bubble_pressure_monthly_add` on expansion/boom/frenzy `×2.8` | `extra_modifiers.txt` | **yes**, rounded: 1→**3**, 1.5→**4**, 7→**20**; `_cmd` 0.5/1.2/6.8→1.5/3.5/19, `_coop` 0.8/1.5/5.7→2.5/4/16 |
| `tool_bubble` | the ten `cb_*` tools' **negative** bubble adds `×0.2` | `extra_modifiers.txt` | **yes**: buffer −2.5→**−0.5**, margin −2.0→**−0.4**, deposit −1.0→**−0.2**, capital controls −0.6→**−0.1**, moral suasion and asset relief −0.3→**−0.05** |
| `tool_momentum` | the ten `cb_*` tools' momentum adds `×0.3` | `extra_modifiers.txt` | **yes**, rounded to two places: OMO 0.35→**0.1**, e-liquidity 0.25→**0.08**, buffer/margin −0.15→**−0.05**, directed/export 0.15→**0.05**, deposit 0.1→**0.03**, moral suasion −0.05→**−0.02**, capital controls 0.05→**0.02** |
| `stance_bubble` | `te_mon_stance_bubble_add` multiply −0.75 → −0.45 | `te_monetary_script_values.txt` | no — near zero in the ablation |
| `gap_clamp_loose` | `te_mon_stance_gap_clamped`'s **loose** bound −4 → **−2** (tight side unchanged) | `te_monetary_script_values.txt`, now the named `te_mon_stance_gap_clamp_loose` / `_tight` | **yes** — note the clamp is shared with `te_mon_pressure_stance`, so loose money's inflation pressure is also capped at +0.8pp instead of +1.6pp (modelled: the passive-fiat arm's mean inflation falls 22 % → 19 % in §8) |
| `recovery` | `country_finance_momentum_monthly_add` on downturn 0.1→**0.3** and stagnation 0.05→**0.15** | `extra_modifiers.txt` (and the `_cmd`/`_coop` variants) | **yes** |
| `climb` | add `country_finance_value_monthly_add = 0.5` to the downturn and stagnation phase modifiers | `extra_modifiers.txt` (and the variants; the owner's own `+1` on panic is mirrored to `_cmd`/`_coop`) | **yes** |
| `growth_bias` | `te_mon_mandate_growth_bias` −1.0 → **−0.25** | `te_monetary_script_values.txt` | **yes** — §5 measures the alternatives |
| `hyper_edge` | `te_mon_band_edge_hyper` 50 → 25 | `te_monetary_script_values.txt` | no — the drift it would resolve is documented as intended, and §8 ships the agency fix instead |
| `fiat_pull` | a non-metallic branch in `te_mon_pressure_regime_pull` | `te_monetary_script_values.txt` | no — contradicts the documented fiat design (no regime pull); same reason |

`sev_scale`, `tool_bubble`, `tool_momentum` and `growth_bias` are pure retunings. `below40` is a bug fix.
The sim's hard-coded control flow was updated to match the script, so the "recommended" preset is gone: the
mod *is* the recommendation now, and `--tune pre_retune` is the A/B.

**A feel tension worth one sentence.** The buffer's bubble line is now −0.5 (−1.0 since §10) against a frenzy's +20, and the
tooltip prints the modifier's real values, so a player reading the tool in a frenzy will see it as nearly
inert there. That is the intended reading — the prudential tools lean against a boom, they do not cancel it —
but it is a change of texture from the old −2.5.

`recovery` and `climb` are the largest *feel* change here, so the number is worth seeing before adopting
them: the median climb from a crash back to cycle 40 goes from **22–31 months to 14–18**, and the median
worst slump in a century from **15–241 months to 17–88**. Recessions become shorter and more frequent
rather than rarer and longer, which is the historical shape but is a real change of texture.

### Result — shipped → retuned, 400 runs × 100 years per cell

#### Crashes per century

| cell | 0 pt | 1 pt | 2 pt | 3 pt | 5 pt | 8 pt |
|---|---|---|---|---|---|---|
| `commodity` / nothing | 4.9 → **7.0** | 3.3 → **6.4** | 1.1 → **5.4** | 2.1 → **8.8** | 1.0 → **7.8** | 0.6 → **7.9** |
| `commodity` / price | 5.4 → **8.3** | 3.8 → **7.5** | 0.6 → **6.1** | 1.0 → **10.0** | 0.3 → **8.6** | 0.1 → **8.7** |
| `commodity` / growth | 14.7 → **13.3** | 11.8 → **11.2** | 4.5 → **10.2** | 4.7 → **13.6** | 2.3 → **13.2** | 1.1 → **13.3** |
| `gold` / nothing | 5.8 → **8.3** | 3.9 → **7.4** | 1.6 → **6.4** | 2.5 → **9.8** | 1.0 → **9.0** | 0.6 → **9.2** |
| `gold` / price | 5.8 → **8.3** | 3.7 → **6.7** | 1.1 → **5.8** | 1.7 → **9.5** | 0.6 → **8.0** | 0.3 → **8.0** |
| `gold` / growth | 19.6 → **14.3** | 16.7 → **13.1** | 8.0 → **12.5** | 7.1 → **15.9** | 4.6 → **14.8** | 2.0 → **13.8** |
| `gold` / peg | 8.0 → **11.4** | 5.6 → **10.4** | 2.0 → **9.1** | 3.4 → **13.0** | 1.5 → **12.4** | 0.8 → **12.4** |
| `fiat` / nothing | 49.4 → **35.1** | 47.5 → **34.6** | 47.4 → **34.3** | 46.6 → **34.8** | 39.3 → **34.8** | 40.1 → **35.1** |
| `fiat` / price | 4.6 → **8.8** | 2.3 → **7.7** | 0.3 → **6.0** | 0.6 → **10.5** | 0.3 → **8.0** | 0.1 → **8.1** |
| `fiat` / growth | 17.8 → **15.8** | 14.2 → **14.5** | 4.2 → **12.9** | 4.8 → **16.1** | 2.3 → **14.5** | 1.0 → **14.9** |
| `digital` / nothing | 50.2 → **35.3** | 48.4 → **34.8** | 48.1 → **34.4** | 46.5 → **34.8** | 37.0 → **34.5** | 36.0 → **34.6** |
| `digital` / price | 4.0 → **8.1** | 1.9 → **7.5** | 0.3 → **5.1** | 0.5 → **8.9** | 0.2 → **7.6** | 0.0 → **6.7** |
| `digital` / growth | 16.3 → **15.0** | 12.8 → **13.7** | 3.8 → **12.3** | 4.1 → **15.7** | 1.9 → **15.1** | 0.8 → **14.1** |

#### Share of crashes that drop the cycle into panic (value 5 or 10), %

| cell | 0 pt | 1 pt | 2 pt | 3 pt | 5 pt | 8 pt |
|---|---|---|---|---|---|---|
| `commodity` / nothing | 65 → **24** | 64 → **25** | 58 → **25** | 53 → **25** | 48 → **24** | 45 → **25** |
| `commodity` / price | 58 → **25** | 61 → **26** | 44 → **24** | 36 → **25** | 29 → **26** | 29 → **24** |
| `commodity` / growth | 66 → **24** | 66 → **25** | 56 → **25** | 51 → **24** | 43 → **24** | 41 → **23** |
| `gold` / nothing | 66 → **25** | 66 → **24** | 59 → **25** | 54 → **25** | 48 → **25** | 49 → **24** |
| `gold` / price | 48 → **25** | 47 → **26** | 40 → **24** | 35 → **24** | 33 → **24** | 29 → **23** |
| `gold` / growth | 61 → **24** | 61 → **24** | 52 → **24** | 52 → **24** | 44 → **23** | 40 → **23** |
| `gold` / peg | 67 → **24** | 65 → **26** | 60 → **25** | 54 → **25** | 52 → **25** | 46 → **23** |
| `fiat` / nothing | 60 → **23** | 59 → **21** | 57 → **22** | 56 → **21** | 52 → **22** | 50 → **22** |
| `fiat` / price | 51 → **25** | 43 → **25** | 22 → **24** | 19 → **25** | 20 → **25** | 4 → **24** |
| `fiat` / growth | 61 → **23** | 62 → **24** | 52 → **24** | 50 → **24** | 41 → **23** | 35 → **23** |
| `digital` / nothing | 60 → **23** | 59 → **22** | 57 → **22** | 56 → **22** | 52 → **22** | 51 → **22** |
| `digital` / price | 50 → **24** | 42 → **27** | 21 → **25** | 21 → **25** | 15 → **25** | 10 → **26** |
| `digital` / growth | 63 → **24** | 64 → **24** | 54 → **26** | 46 → **23** | 40 → **25** | 34 → **25** |

#### Months spent in panic or downturn, %

| cell | 0 pt | 1 pt | 2 pt | 3 pt | 5 pt | 8 pt |
|---|---|---|---|---|---|---|
| `commodity` / nothing | 33 → **11** | 36 → **12** | 27 → **10** | 19 → **11** | 14 → **9** | 11 → **8** |
| `commodity` / price | 14 → **8** | 15 → **8** | 9 → **6** | 7 → **9** | 4 → **7** | 4 → **6** |
| `commodity` / growth | 23 → **10** | 19 → **9** | 8 → **8** | 8 → **10** | 5 → **9** | 2 → **6** |
| `gold` / nothing | 30 → **11** | 33 → **11** | 24 → **9** | 17 → **10** | 13 → **10** | 9 → **7** |
| `gold` / price | 25 → **10** | 26 → **10** | 18 → **8** | 15 → **10** | 12 → **8** | 8 → **6** |
| `gold` / growth | 23 → **10** | 21 → **10** | 9 → **8** | 9 → **11** | 5 → **9** | 2 → **6** |
| `gold` / peg | 24 → **11** | 24 → **11** | 16 → **8** | 13 → **11** | 8 → **10** | 6 → **6** |
| `fiat` / nothing | 33 → **19** | 32 → **18** | 29 → **17** | 29 → **17** | 23 → **16** | 19 → **10** |
| `fiat` / price | 9 → **8** | 8 → **7** | 7 → **5** | 7 → **9** | 5 → **7** | 4 → **5** |
| `fiat` / growth | 20 → **10** | 17 → **10** | 6 → **8** | 6 → **10** | 4 → **9** | 2 → **6** |
| `digital` / nothing | 33 → **18** | 31 → **17** | 29 → **16** | 28 → **16** | 21 → **15** | 17 → **9** |
| `digital` / price | 6 → **6** | 6 → **6** | 5 → **4** | 5 → **6** | 3 → **5** | 3 → **3** |
| `digital` / growth | 16 → **9** | 13 → **8** | 4 → **7** | 5 → **9** | 3 → **8** | 1 → **5** |

#### Median months from a crash back to cycle ≥ 40

| cell | 0 pt | 1 pt | 2 pt | 3 pt | 5 pt | 8 pt |
|---|---|---|---|---|---|---|
| `commodity` / nothing | 30 → **17** | 30 → **17** | 23 → **16** | 22 → **16** | 19 → **16** | 17 → **14** |
| `commodity` / price | 26 → **17** | 26 → **18** | 22 → **17** | 20 → **17** | 17 → **17** | 17 → **15** |
| `commodity` / growth | 24 → **15** | 24 → **15** | 20 → **15** | 19 → **15** | 17 → **15** | 15 → **13** |
| `gold` / nothing | 31 → **17** | 31 → **17** | 23 → **16** | 22 → **16** | 20 → **16** | 18 → **14** |
| `gold` / price | 22 → **17** | 22 → **18** | 19 → **17** | 19 → **18** | 17 → **17** | 16 → **15** |
| `gold` / growth | 19 → **14** | 19 → **15** | 17 → **14** | 17 → **15** | 16 → **14** | 14 → **13** |
| `gold` / peg | 30 → **16** | 30 → **16** | 23 → **16** | 22 → **16** | 19 → **15** | 17 → **13** |
| `fiat` / nothing | 14 → **12** | 14 → **12** | 13 → **12** | 13 → **12** | 13 → **11** | 11 → **10** |
| `fiat` / price | 22 → **18** | 21 → **18** | 17 → **18** | 17 → **18** | 12 → **17** | 0 → **16** |
| `fiat` / growth | 20 → **15** | 20 → **15** | 18 → **14** | 18 → **15** | 16 → **14** | 15 → **13** |
| `digital` / nothing | 13 → **11** | 13 → **11** | 12 → **11** | 12 → **11** | 12 → **11** | 11 → **10** |
| `digital` / price | 18 → **15** | 17 → **15** | 14 → **15** | 12 → **15** | 13 → **15** | 0 → **14** |
| `digital` / growth | 17 → **14** | 18 → **14** | 16 → **13** | 15 → **13** | 14 → **13** | 13 → **12** |

#### Median longest unbroken run below cycle 40, months

| cell | 0 pt | 1 pt | 2 pt | 3 pt | 5 pt | 8 pt |
|---|---|---|---|---|---|---|
| `commodity` / nothing | 206 → **80** | 240 → **88** | 161 → **87** | 104 → **67** | 104 → **67** | 82 → **62** |
| `commodity` / price | 92 → **40** | 130 → **40** | 85 → **40** | 55 → **35** | 45 → **34** | 40 → **29** |
| `commodity` / growth | 59 → **35** | 68 → **38** | 60 → **34** | 46 → **33** | 33 → **30** | 32 → **25** |
| `gold` / nothing | 189 → **70** | 227 → **78** | 147 → **72** | 94 → **56** | 94 → **56** | 73 → **45** |
| `gold` / price | 86 → **52** | 116 → **56** | 78 → **55** | 60 → **46** | 58 → **44** | 48 → **42** |
| `gold` / growth | 43 → **34** | 50 → **37** | 44 → **34** | 41 → **29** | 30 → **29** | 27 → **27** |
| `gold` / peg | 120 → **44** | 144 → **49** | 110 → **46** | 74 → **42** | 63 → **37** | 55 → **33** |
| `fiat` / nothing | 18 → **19** | 18 → **19** | 17 → **19** | 17 → **19** | 17 → **19** | 16 → **17** |
| `fiat` / price | 73 → **30** | 97 → **31** | 80 → **30** | 50 → **28** | 42 → **28** | 36 → **26** |
| `fiat` / growth | 32 → **23** | 49 → **23** | 50 → **23** | 37 → **22** | 29 → **22** | 28 → **20** |
| `digital` / nothing | 18 → **19** | 18 → **19** | 17 → **18** | 17 → **18** | 17 → **18** | 16 → **17** |
| `digital` / price | 62 → **24** | 82 → **26** | 70 → **28** | 46 → **23** | 37 → **22** | 35 → **20** |
| `digital` / growth | 30 → **21** | 44 → **21** | 44 → **21** | 35 → **20** | 28 → **19** | 26 → **18** |

### Does it hit the target?

| target | shipped | retuned |
|---|---|---|
| commodity / gold / peg, 0–3 pt: 5–15 crashes per century | 0.6 – 8.0 | **5.4 – 13.0** ✓ |
| fiat / digital well managed: a little rarer still | 0.0 – 4.5 | **5.1 – 9.9**, and the lowest cells in the table ✓ |
| fiat / digital mismanaged: worse than metallic | 36.9 – 49.6 (a different game) | **34.4 – 35.4** (still pathological — §4) |
| growth mandate: inside the band, not far above it | 0.7 – 19.9 (4× price stability) | **11.7 – 16.2** (1.6× price stability) ✓ |
| most crashes should be corrections, not depressions | 17 – 66 % land in panic | **22 – 27 %** ✓ |
| budget curve should not invert | 2 pt is the safest budget in the game | much flatter, but **a residual 2-pt dip remains** — see below |
| depressions of a few years, not twenty | median worst slump 15 – 241 months | **17 – 88 months** ✓ |

Across every metallic and well-managed-fiat cell at every budget the retuned crash rate spans **5.1 – 10.5
per century** — a factor of two — against the shipped **0.0 – 5.8**, which is an unbounded ratio because
several cells are flat zero.

**The residual 2-point dip is honest to report.** `tool_momentum` closes most of it (the ablation below
isolates that as its only job) but not all: the 2-pt cell still runs about 0.7× the mean of its 0-pt and
3-pt neighbours. Two intervention points still buys one purely contractionary tool and nothing else. If
that bothers you, the targeted fix is to move `banking_countercyclical_capital_buffer` or
`banking_raise_margin_requirements` to 3 points, or to give the 1–2 point tier one mildly expansionary
option; both are outside what this study measured.

### Which of the thirteen changes actually matter

Leave-one-out: each row is the full retune with that one key removed, 250 runs × 100 years,
budgets 0 / 2 / 3. Compare each row to the first.

| knob removed | metallic crashes/century | depression % | growth crashes | passive fiat | 2-pt dip ratio |
|---|---|---|---|---|---|
| *(full retune)* | 7.7 | 24 | 13.9 | 34.8 | 0.68 |
| `sev_scale` | 7.8 | **77** | 15.0 | 33.6 | 0.73 |
| `phase_bubble` | **4.5** | 14 | **8.7** | 29.9 | 0.59 |
| `growth_bias` | 7.7 | 24 | **21.2** | 34.8 | 0.68 |
| `gap_clamp_loose` | 7.8 | 24 | 14.2 | **48.1** | 0.68 |
| `tool_bubble` | **5.9** | 22 | 10.9 | 32.5 | 0.51 |
| `tool_momentum` | 7.5 | 24 | 13.0 | 33.7 | **0.47** |
| `recovery` | 6.8 | 24 | 12.6 | 32.1 | 0.71 |
| `stance_bubble` | 8.1 | 25 | 14.7 | 36.6 | 0.73 |
| `climb` | 8.2 | 24 | 14.3 | 34.4 | 0.77 |
| `below40` | 8.0 | 24 | 14.1 | 34.9 | 0.68 |
| `crash_mult` | 7.6 | 25 | 13.7 | 34.1 | 0.68 |
| `fiat_pull` | 7.7 | 24 | 13.3 | 33.3 | 0.68 |
| `hyper_edge` | 7.7 | 24 | 13.9 | 34.8 | 0.68 |

Each knob has exactly one job and does it:

- **`sev_scale` alone does the severity work** — without it, depression share goes straight back to 77 %.
  If you make one change, make this one.
- **`phase_bubble` is the frequency lever.** Without it the metallic band falls to 4.5. This was the
  surprise: the cycle is bubble-rebuild-limited (F3), so letting bubble accumulate faster is what raises
  crash frequency — raising the crash *probability* (`crash_mult`) does almost nothing.
- **`tool_bubble` + `tool_momentum` are the intervention nerf**, and `tool_momentum` is specifically what
  flattens the budget curve.
- **`gap_clamp_loose` is the passive-fiat fix and nothing else** (48.1 → 34.8, no other column moves).
- **`growth_bias` is the growth-mandate fix and nothing else** (21.2 → 13.9).
- **`recovery` and `climb`** shorten slumps; `recovery` also contributes ~1 crash/century by keeping the
  cycle out of the cold phases.
- **`below40`, `crash_mult`, `hyper_edge`, `fiat_pull` are near-zero on these metrics.** `below40` is a bug
  fix — keep it for correctness, not magnitude. `hyper_edge` and `fiat_pull` target the *inflation level*
  of the passive fiat arm, which this ablation does not measure; `fiat_pull` halves it (22 % → 12 %) and
  with `hyper_edge` together it reaches 5.7 %.

**A seven-key subset** — `sev_scale`, `phase_bubble`, `tool_bubble`, `tool_momentum`, `gap_clamp_loose`,
`growth_bias`, `recovery` — reproduces essentially the whole result. Add `below40` because it is a bug.

**Untested:** the `_cmd` and `_coop` phase-modifier variants. The simulation only runs a market economy, so
`phase_bubble`, `recovery` and `climb` were never measured against command economy or cooperative
ownership. Scale those variants in proportion if you want them to track, but treat it as unverified.

---

## 4. Two things the retune does not fix

**The passive fiat/digital arm is still 35 crashes per century.** *(Update, same day: the first bullet
below shipped — `te_monetary_init_variables` now seeds `te_mon_delegated = 1`, see §8.)* Narrowing the loose-side stance clamp
(`gap_clamp_loose`) is what took it from 49 to 35, and tightening further keeps helping (−2 → 35, −1.5 →
30) at no cost to any managed cell, because a steered dial almost never reaches the clamp. But no amount of
tuning makes "leave the dial at 3 % for a century under fiat" a reasonable outcome, because it is not a
reasonable *action*. The real fix is agency, not balance:

- **Initialise `te_mon_delegated` to 1 for players as well as the AI**, so "do nothing" means "delegated to
  price stability" — which lands squarely in the healthy band — and un-delegating is the deliberate act. A
  player who wants the dial takes it; a player who never opens the dashboard gets a competent central bank.
- Failing that, surface a standing alert while `te_mon_stance_band` has been 1 (very loose) for, say, a
  year. The band is already computed every month and is already player-visible, so this is a display rule
  rather than new state.

Either of those removes most of the reason to tune this arm at all.

**`fiat_pull` is a design addition, and there is an alternative.** The clean argument for it is that a
runaway with no fixed point is a modelling artefact, not a design choice — the shipped script gives every
*other* regime a pull toward its anchor and fiat none. The alternative, if a new pressure term is
unwelcome, is to leave inflation unbounded and instead lower `te_mon_band_edge_hyper` far enough (≈15–20)
that `te_inflation.1`'s currency reform actually fires and the country exits the trap on its own. That was
measured too: it fixes the inflation level but *not* the crash rate, because the stance clamp is the crash
driver. `gap_clamp_loose` is doing the load-bearing work either way.

---

## 5. Does the growth mandate actually buy growth?

The crash count alone cannot answer that, so the simulator now sums the economic modifier fields every
phase, tool, band and crash-intervention modifier carries (`State.payoff`: manufacturing throughput,
services output, the capitalists' investment-pool contribution, the risk premium, and the inflation bands'
pool-efficiency, SoL and tax-waste lines) and reports their time-weighted means — what the cycle *did* to
the economy over the century, not just how often it broke. 200 runs × 100 years per cell.

| script | currency | pts | crashes/century, price → growth | manufacturing throughput pp | services % | capitalists' pool pp | inflation % | months above the comfort band % |
|---|---|---|---|---|---|---|---|---|
| before | gold | 0 | 5.4 → 19.8 | −3.17 → −1.07 | −5.2 → +1.9 | −2.31 → −0.88 | 0.0 → 0.3 | 1 → 0 |
| before | gold | 3 | 1.6 → 7.7 | −1.58 → +1.00 | −0.8 → +7.6 | −0.73 → +1.28 | 0.1 → 0.4 | 1 → 0 |
| before | gold | 8 | 0.3 → 1.8 | −0.82 → +1.86 | +1.2 → +9.9 | −0.06 → +1.85 | 0.1 → 0.4 | 1 → 0 |
| before | fiat | 0 | 4.7 → 17.8 | −1.04 → −0.54 | +0.6 → +3.5 | +0.05 → −0.35 | 2.4 → 4.1 | 25 → 72 |
| before | fiat | 3 | 0.7 → 4.5 | −0.62 → +0.71 | +1.8 → +6.2 | +0.42 → +1.16 | 2.4 → 4.1 | 25 → 70 |
| before | fiat | 8 | 0.1 → 1.1 | −0.28 → +1.42 | +2.6 → +8.2 | +0.49 → +1.57 | 2.4 → 4.2 | 25 → 74 |
| retuned (§3) | gold | 0 | 7.9 → 14.7 | −1.61 → −0.53 | −1.5 → +2.1 | −0.46 → +0.29 | 0.1 → 0.2 | 1 → 0 |
| retuned (§3) | gold | 3 | 9.4 → 16.3 | −1.02 → −0.19 | +0.4 → +3.3 | −0.22 → +0.32 | 0.1 → 0.3 | 1 → 0 |
| retuned (§3) | gold | 8 | 7.9 → 14.2 | −0.57 → +0.33 | +1.4 → +4.6 | +0.14 → +0.72 | 0.1 → 0.2 | 1 → 0 |
| retuned (§3) | fiat | 0 | 8.6 → 14.0 | −0.79 → −0.24 | +0.8 → +2.8 | −0.01 → +0.40 | 2.3 → 3.2 | 25 → 51 |
| retuned (§3) | fiat | 3 | 9.3 → 15.0 | −0.36 → +0.06 | +2.2 → +4.0 | +0.12 → +0.41 | 2.3 → 3.2 | 23 → 50 |
| retuned (§3) | fiat | 8 | 7.0 → 14.4 | +0.01 → +0.65 | +3.0 → +5.7 | +0.32 → +0.79 | 2.3 → 3.4 | 23 → 56 |

**Yes — it did before, and it still does.** In every cell growth beats price stability on throughput,
services and the investment pool. Before the retune it did so at 4× the crashes (and at 0 points a *gold*
country on growth was paying nearly twice the depression share, F2); after it, at 1.6–1.9× the crashes, for
about +1.0 pp of manufacturing throughput, +3.5 % services and +0.7 pp of pool contribution, and — under
fiat — twice the months spent above the comfort band (51 % vs 25 %), which is the elevated band's SoL
offset and IG approval costs that the payoff columns do not price. That is a trade with a real price on
both sides, which is what §6 of the design asks for.

**The cycle is a net drag under price stability.** Every price-stability cell has a *negative* mean
throughput: the phase modifiers are symmetric (±5/10/15 %, with panic at −20 %) but the cycle's mean value is
44–48, not 50, because crashes only reset downward and the climb back is slow. The retune halves the drag
(gold, 0 pt: −3.2 → −1.6 pp; at 8 pt −0.8 → −0.6) and the fiscal channel in §6 halves it again, but it is
still there. If a "neutral" cycle is wanted the lever is the phase table's asymmetry (panic −20 % vs frenzy
+15 %), which nothing here touched.

### Where to set the growth bias

| bias | gold, 0 pt: crashes price / growth | gold throughput pp price / growth | fiat, 0 pt: crashes price / growth | fiat growth inflation % | fiat growth months above comfort % |
|---|---|---|---|---|---|
| −1.0 (was) | 7.9 / 22.8 | −1.61 / −0.12 | 8.6 / 21.5 | 4.1 | 71 |
| −0.5 | 7.9 / 17.8 | −1.61 / −0.38 | 8.6 / 17.3 | 3.5 | 60 |
| **−0.25 (shipped)** | 7.9 / 14.7 | −1.61 / −0.53 | 8.6 / 14.0 | 3.2 | 51 |
| 0.0 | 7.9 / 12.4 | −1.61 / −0.78 | 8.6 / 12.7 | 3.0 | 47 |

The design (§6) says growth "runs 1pp warm — equilibrium inflation ≈ 3 %". At −1.0 the measured
equilibrium was **4.1 %**; −0.25 is what lands at the 3 % the design describes, keeps the growth mandate
at 1.7–1.9× price stability's crash rate, and still pays. Even at 0.0 the mandate is looser than price
stability, because the `cycle_lean/2` term and the higher inflation reaction threshold remain.

---

## 6. The fiscal channel (F8), resolved

`docs/engine/event_targets_summary.txt` settles the units: `income` is *weekly*, `gdp` is *yearly*, so
`financial_cycle_government_fiscal_policy_effect_size` was dividing a weekly flow by an annual stock and
delivering 1/52 of what its comment claimed. It now annualises through the same
`te_mon_deficit_annualise_factor` the monetary deficit term uses (one hypothesis constant, so if a running
game ever shows the flows to be annual both channels flip together). The question was then what the
magnitude should be; the old comment's "1 point a month per 1 % of GDP" was measured along with smaller
sizes. Retune of §3 applied throughout; cells are crashes/century · mean cycle value · months in frenzy % ·
throughput pp.

| cycle points a month per 1 % of GDP of deficit | gold / price / 0 pt | fiat / price / 3 pt | gold / nothing / 0 pt | fiat / growth / 5 pt |
|---|---|---|---|---|
| 0.019 (as it stood: not annualised) | 7.9 · 44.4 · 1.5 · −1.61 | 9.3 · 48.4 · 1.3 · −0.36 | 8.4 · 44.7 · 1.7 · −1.60 | 14.0 · 50.4 · 2.7 · +0.21 |
| **0.1 (shipped since the follow-up below, clamped ±1)** | 8.6 · 45.1 · 1.6 · −1.40 | 10.3 · 49.2 · 1.5 · −0.16 | 9.5 · 45.9 · 2.0 · −1.23 | 14.6 · 51.0 · 2.7 · +0.37 |
| 0.25 (first shipped, clamped ±1) | 10.9 · 47.0 · 2.1 · −0.88 | 11.8 · 50.4 · 1.7 · +0.14 | 11.9 · 47.3 · 2.6 · −0.90 | 17.7 · 52.6 · 3.6 · +0.74 |
| 0.5 | 13.6 · 49.1 · 2.7 · −0.31 | 14.9 · 52.5 · 2.7 · +0.68 | 16.3 · 50.1 · 3.6 · −0.10 | 20.3 · 54.3 · 4.5 · +1.23 |
| 1.0 (the old comment's intent) | 20.2 · 53.1 · 5.1 · +0.82 | 20.9 · 55.6 · 4.8 · +1.54 | 24.6 · 54.1 · 7.0 · +1.10 | 26.1 · 57.1 · 7.2 · +2.06 |

The old intent would have run every country hot on the simulator's modest 1.5 %-of-GDP peacetime deficit
alone — a mean cycle in the mid-50s and 20–26 crashes a century. **0.25 a month per 1 % of GDP, clamped
to ±1**, is what shipped: a 4 % wartime deficit pushes the cycle a full point a month (about one phase
modifier's worth), a surplus cools it the same way, and the clamp stops a 10 %-of-GDP borrowing spree from
pinning the cycle in frenzy by itself. It adds about three crashes a century and lifts the mean cycle two
points. Its cost is stub-dependent: the deficit process in the sim is invented (mean 1.5 %, ×3 at war), and
a player who runs large deficits will feel this channel far more than the AI does. **Still unverified in a
running game:** the units reading is the engine catalogue's, not an observation — the monetary debug
read-out (`te_mon_deficit_pct`) settles both channels at once.

**Follow-up (2026-09-22): cut to 0.1.** At 0.25 an ordinary 4 % wartime deficit was worth a full phase
modifier on its own, which the owner judged too strong; the constant is now 0.1 a month per 1 % of GDP, so
it takes a 10 %-of-GDP deficit to reach the +1 clamp. A/B against 0.25 (`--tune fiscal_scale=2.5`), 400 runs ×
100 years, same columns:

| | gold / price / 0 pt | fiat / price / 3 pt | gold / nothing / 0 pt | fiat / growth / 5 pt |
|---|---|---|---|---|
| 0.25 | 10.6 · 47.2 · 1.6 · −0.80 | 8.0 · 51.6 · 0.6 · +0.65 | 12.0 · 47.4 · 2.4 · −0.87 | 14.7 · 54.0 · 2.7 · +1.31 |
| **0.1** | 9.0 · 45.9 · 1.3 · −1.19 | 6.8 · 50.2 · 0.4 · +0.31 | 9.5 · 45.8 · 1.8 · −1.27 | 13.3 · 52.4 · 2.1 · +0.91 |

About 1–2.5 fewer crashes a century and a mean cycle ~1.5 points cooler; throughput gives back ~0.4 pp.
(These rows differ from the table above because §10's boom-rescue package landed in between.)

---

## 7. Are the AI's tool weights right?

Three answers, from three experiments. All under the §3 retune, 200 runs × 100 years per cell,
price-stability mandate unless stated.

### F10 — Law-flavour and budget terms fired with no cycle reason, and that was the 2-point dip

Every enable button's `ai_chance` is a sum of *core* terms (the cycle state the tool answers), *flavour*
terms (the financial-regulation law, an independent bank, a companion tool) and *resource* terms (how many
points are free). The flavour and resource terms were **unconditional adds on a base of 0**, so in a stable
phase with no cycle reason at all a universal-banking AI scored the buffer 20, margin requirements 20,
moral suasion 20 and capital controls 10 — and clicked them. Instrumented: the AI parked prudential tools
for ~40 % of the century, which is exactly what made two points the safest budget in the game (F1).

The simulator's `--tune ai_gate` gates the flavour/resource terms on a core term being positive. The shipped
script does the same through one `banking_ai_core_cb_*` trigger per button (`banking_policy_triggers.txt`),
so the gate and the core terms can be read side by side. Crashes/century at 0 / 1 / 2 / 3 / 5 / 8 points:

| variant | gold / price | fiat / price | gold / growth | tools held at 8 pt |
|---|---|---|---|---|
| before the retune | 5.4 / 3.8 / 1.1 / 1.6 / 0.8 / 0.3 | 4.7 / 2.3 / 0.4 / 0.7 / 0.3 / 0.1 | 19.8 / 16.6 / 9.0 / 7.7 / 4.7 / 1.8 | 2.33 |
| retune, ungated AI | 7.9 / 7.5 / **6.8** / 9.4 / 8.4 / 7.9 | 8.6 / 7.3 / **5.5** / 9.3 / 7.5 / 7.0 | 14.7 / 13.8 / 13.9 / 16.3 / 16.4 / 14.2 | 2.29 |
| … AI clicks 4× more often | 7.9 / 7.9 / 6.2 / 9.1 / 7.9 / 8.1 | 8.6 / 6.9 / 5.2 / 8.8 / 6.9 / 6.4 | 14.7 / 14.7 / 13.3 / 16.1 / 15.8 / 14.4 | 2.40 |
| … AI clicks 4× less often | 7.9 / 7.4 / 7.0 / 9.2 / 8.6 / 8.8 | 8.6 / 7.4 / 5.2 / 9.0 / 8.7 / 8.1 | 14.7 / 14.2 / 14.1 / 15.1 / 15.3 / 15.3 | 2.13 |
| **retune, gated AI** | 7.9 / 8.2 / 8.6 / 10.1 / 9.8 / 9.7 | 8.6 / 7.2 / 7.9 / 9.7 / 9.2 / 9.1 | 14.7 / 15.0 / 14.9 / 16.1 / 16.5 / 15.7 | 1.32 |
| … AI clicks 4× more often | 7.9 / 8.1 / 7.8 / 9.4 / 8.8 / 8.8 | 8.6 / 8.1 / 6.8 / 9.2 / 8.5 / 7.9 | 14.7 / 14.7 / 14.2 / 15.1 / 16.1 / 15.4 | 1.31 |
| … AI clicks 4× less often | 7.9 / 8.3 / 8.6 / 10.1 / 10.4 / 9.8 | 8.6 / 7.7 / 7.3 / 10.1 / 9.4 / 9.7 | 14.7 / 14.2 / 14.4 / 15.4 / 16.6 / 16.1 | 1.32 |

The residual 2-point dip §3 left open (0.7× its neighbours) is gone with the gate, the AI holds about half
as many tools, and the result holds across a 16× range of click cadence — the study's largest assumption.
Capital controls drop to zero use under the full system, which is right: with no external crisis there is
nothing for them to defend, and before the gate a universal-banking AI at 3–5 points toggled them through
the resource terms alone.

### F11 — Directed credit was the AI's one harmful tool

Leave-one-out over the ten tools (crashes/century · throughput pp; "notools" keeps the crash event's
options but never clicks a dashboard tool):

| AI pool | gold/price 3 pt | gold/price 5 pt | gold/price 8 pt | fiat/price 3 pt | fiat/price 5 pt | fiat/price 8 pt |
|---|---|---|---|---|---|---|
| all ten | 9.4 · −1.02 | 8.4 · −0.97 | 7.9 · −0.57 | 9.3 · −0.36 | 7.5 · −0.27 | 7.0 · +0.01 |
| no dashboard tools | 7.9 · −1.31 | 7.5 · −1.37 | 8.0 · −1.28 | 7.4 · −0.51 | 6.6 · −0.60 | 6.9 · −0.54 |
| without moral suasion | 11.1 · −0.93 | 8.5 · −0.89 | 8.7 · −0.39 | 11.6 · −0.27 | 7.3 · −0.32 | 7.5 · +0.11 |
| without the buffer | 9.8 · −1.11 | 9.8 · −0.76 | 10.1 · −0.47 | 10.7 · −0.32 | 9.5 · −0.11 | 9.6 · +0.14 |
| without margin requirements | 9.5 · −1.04 | 9.0 · −0.83 | 10.4 · −0.36 | 10.3 · −0.27 | 9.0 · −0.12 | 9.4 · +0.20 |
| without the deposit guarantee | 9.4 · −1.02 | 8.4 · −0.95 | 8.0 · −0.63 | 9.3 · −0.36 | 8.0 · −0.24 | 7.1 · −0.02 |
| **without directed credit** | **6.3** · −1.55 | **6.0** · −1.26 | **5.6** · −1.00 | **4.9** · −0.89 | **4.5** · −0.64 | **3.9** · −0.49 |
| without export credit | 9.6 · −1.16 | 8.4 · −1.01 | 8.6 · −0.52 | 9.6 · −0.39 | 7.5 · −0.28 | 6.8 · −0.04 |
| without capital controls | 9.5 · −1.09 | 8.2 · −1.07 | 8.1 · −0.64 | 9.6 · −0.35 | 7.9 · −0.23 | 7.1 · −0.01 |
| without emergency liquidity | 9.4 · −1.02 | 8.4 · −0.97 | 8.1 · −0.57 | 9.3 · −0.36 | 7.5 · −0.27 | 7.2 · +0.04 |
| without asset relief | 9.4 · −1.02 | 8.3 · −1.00 | 7.4 · −0.66 | 9.3 · −0.36 | 7.6 · −0.27 | 6.6 · −0.05 |

Read across: the prudential tools (buffer, margin, moral suasion) each earn their keep — removing one raises
the crash rate. The AI's tools as a set *raise* the crash rate against no tools while buying throughput, and
**directed credit is 30–45 % of a tooled AI's crashes**. Its enable weights are fine (downturn 40,
stagnation 30) — the problem was the disable side, which only lifted it in boom (35), frenzy (55) or panic
(45), with a token 10 in expansion, so a tool bought in a slump stayed on through the whole recovery and
the expansion after it, carrying +0.5 cycle points a month and +0.3 bubble. Shipped: **+20 in stable
(unless momentum is still falling) and +30 in expansion**, which is what the other expansionary tools'
disable sides already say. Measured on the final stack:

| stack | gold / price, 0 / 2 / 3 / 5 / 8 pt | throughput at 8 pt | fiat / price | gold / growth | fiat / nothing |
|---|---|---|---|---|---|
| retune + AI gate | 7.9 / 8.6 / 10.1 / 9.8 / 9.7 | −0.40 | 8.6 / 7.9 / 9.7 / 9.2 / 9.1 | 14.7 / 14.9 / 16.1 / 16.5 / 15.7 | 36.9 / 37.3 / 37.7 / 38.0 / 39.0 |
| + lift directed credit on recovery | 7.9 / 8.6 / 8.0 / 8.1 / 7.3 | −0.69 | 8.6 / 7.9 / 7.4 / 6.7 / 6.3 | 14.7 / 14.9 / 14.4 / 15.2 / 13.4 | 36.9 / 37.3 / 37.2 / 37.5 / 38.8 |
| **+ fiscal channel annualised (shipped)** | 10.8 / 9.9 / 10.5 / 10.2 / 9.1 | −0.10 | 11.2 / 10.1 / 9.5 / 9.7 / 8.6 | 18.2 / 17.3 / 18.6 / 17.9 / 17.9 | 39.3 / 39.9 / 39.9 / 40.3 / 41.4 |
| + cheaper tools defer to the lender of last resort | 10.8 / 9.9 / 10.5 / 10.2 / 9.0 | −0.10 | 11.2 / 10.1 / 9.5 / 9.7 / 8.5 | 18.2 / 17.3 / 18.6 / 17.9 / 17.7 | 39.3 / 39.9 / 39.9 / 40.3 / 41.4 |

With both AI changes the budget curve is flat (a tooled country crashes about as often as an untooled one)
and the tools buy throughput and shorter recessions, which is the shape the dashboard was designed for.

### F12 — The lender of last resort is priced out by the crash event's own option (not fixed)

`cb_emergency_liquidity_program` costs 6 points and is the strongest panic tool (weight 85), yet the AI
activated it 0.0–0.7 times a century at every budget. It is not the weights: every crash fires
`minor_events_timelineextended.6`, whose softening options leave a `banking_crash_intervention_*` modifier
holding 1–4 points for a year, so an 8-point country enters its panic with 4–6 free and cannot afford the
tool built for the panic. The last row of the table above — cheaper panic tools stand aside while e-liquidity
is affordable and not running — measured as exactly zero, confirming that affordability, not competition, is
the block.

**Shipped (owner's call, same day): the cost is 6 → 4**, so a 6- or 8-point country can still reach it after
a crash option. Measured at 300 runs, real budgets 4 / 6 / 8 (activations a century, gold / price):

| cost | 4 pt | 6 pt | 8 pt | crashes / throughput, 8 pt |
|---|---|---|---|---|
| 6 | 0.0 | 0.0 | 0.3 | 9.7 · −0.01 |
| 5 | 0.0 | 0.1 | 0.3 | 9.6 · −0.05 |
| **4** | 0.6 | 0.6 | 0.7 | 9.9 · −0.01 |
| 3 | 0.7 | 0.7 | 0.8 | 9.8 · −0.01 |

Use stays around one activation a century even at 3, because the tool's core reasons — the panic band, or
a downturn with momentum still at −4 or below — are rare under the retune's milder crashes (widening the
downturn trigger to −3 or −2 changed nothing). That is the intended shape for a lender of last resort; the
price cut only makes sure the budget is not what stops it. No cycle metric moved.

---

## 8. What shipped, and the mod as it now stands

Written into the mod on 2026-09-22, in one PR:

- **§3, the nine-key subset**: the below-40 crash branch, `banking_crash_severity_scale_value` 0.55 (origin
  and contagion), phase bubble ~×3, tools' momentum ×0.3 and negative bubble ×0.2, the stance clamp's loose
  side −2, recovery ×3 plus the +0.5 climb, growth bias −0.25.
- **§6**: the fiscal channel annualised, 0.25 points a month per 1 % of GDP, clamped ±1 (cut to 0.1 the
  same day — §6's follow-up).
- **§7**: the `banking_ai_core_cb_*` gates on every enable button's flavour/resource terms; directed
  credit's disable side lifts it in stable and expansion.
- **§4's first bullet**: `te_monetary_init_variables` seeds `te_mon_delegated = 1`, so a player who never
  opens the dashboard has a bank running price stability and *Take Control* is the deliberate act. The
  toggle, the §14 command-economy clear and the AI's monthly write are untouched; a save that already
  carries the variable keeps it. That makes the "nothing" arm below a deliberate choice rather than the
  default, which is the whole point.
- The simulator's hard-coded control flow updated to match, so a plain run measures the mod as it stands
  and `--tune pre_retune` approximates the morning's script.

### The mod as it now stands — 400 runs × 100 years per cell, no `--tune`

*As of #371. §10 changed the leaning tools, frenzy, the inertia curve and the fiat / digital laws afterwards,
and carries the refreshed numbers. `--tune pre_boom_rescue` reproduces this table exactly.*

Crashes per century at 0 / 1 / 2 / 3 / 5 / 8 points; then the share of crashes that reset into the panic band, the median longest slump, and the mean manufacturing-throughput effect at 0 and 8 points.

| cell | crashes / century | depression % (0 pt) | worst slump, months (0 pt) | throughput pp, 0 → 8 pt |
|---|---|---|---|---|
| `commodity` / nothing | 10.9 / 10.2 / 10.6 / 10.5 / 10.7 / 11.0 | 26 | 67 | -1.17 → +0.09 |
| `commodity` / price | 12.0 / 11.1 / 10.7 / 11.2 / 11.6 / 11.2 | 24 | 35 | -0.32 → +0.56 |
| `commodity` / growth | 17.2 / 16.4 / 15.6 / 15.7 / 16.5 / 16.6 | 25 | 30 | -0.03 → +0.97 |
| `gold` / nothing | 12.1 / 11.7 / 11.9 / 11.8 / 12.4 / 12.3 | 26 | 60 | -0.97 → +0.32 |
| `gold` / price | 11.3 / 10.4 / 10.2 / 10.0 / 9.9 / 9.6 | 26 | 44 | -0.95 → -0.02 |
| `gold` / growth | 18.0 / 17.6 / 17.6 / 18.0 / 17.9 / 17.7 | 24 | 30 | -0.11 → +0.92 |
| `gold` / peg | 16.0 / 15.8 / 16.1 / 15.7 / 16.1 / 16.4 | 25 | 38 | -0.19 → +0.99 |
| `fiat` / nothing | 39.4 / 38.9 / 40.0 / 39.9 / 40.2 / 41.4 | 25 | 19 | +0.17 → +1.65 |
| `fiat` / price | 11.2 / 10.8 / 10.9 / 10.0 / 10.0 / 9.3 | 26 | 29 | -0.31 → +0.48 |
| `fiat` / growth | 18.5 / 17.8 / 17.3 / 17.7 / 17.2 / 17.0 | 24 | 23 | +0.25 → +1.12 |
| `digital` / nothing | 39.9 / 39.5 / 40.3 / 40.3 / 40.5 / 41.3 | 25 | 18 | +0.42 → +1.85 |
| `digital` / price | 10.4 / 9.8 / 9.4 / 8.4 / 8.3 / 7.8 | 26 | 22 | +0.22 → +0.66 |
| `digital` / growth | 17.9 / 17.3 / 17.4 / 16.6 / 16.7 / 16.4 | 24 | 20 | +0.54 → +1.33 |

### Does it hit the target?

| target (§2) | before (§2) | now |
|---|---|---|
| commodity / gold, any dial, 0–3 pt: 5–15 crashes per century | 0.6 – 8.0 | **10.0 – 16.1** ✓ (peg defence is the top of that range) |
| fiat / digital well managed: a little rarer still | 0.0 – 4.5 | **7.8 – 11.2** — the lowest cells in the table ✓ |
| fiat / digital with the dial never touched: worse than metallic | 36.9 – 49.6 | **39.4 – 41.4** — still pathological, but now an opt-in (players start delegated) |
| growth mandate: inside the band or not far above it | 0.7 – 19.9 (4× price stability) | **15.6 – 18.5** (1.5–1.8× price stability), and it buys about +1 pp of throughput (§5) |
| most crashes should be corrections, not depressions | 17 – 66 % land in panic | **23 – 27 %** ✓ |
| the budget curve should not invert | 2 pt the safest budget in the game | 2-pt cell is 0.92–1.03× the mean of its 0- and 3-pt neighbours ✓ |
| depressions of a few years, not twenty | median worst slump 15 – 241 months | **17 – 68 months** ✓ |

**`--tune pre_retune` sanity check** (400 runs; §2's numbers were measured on the real pre-retune script, this preset undoes rounded file values, so it is expected to be close rather than exact):

| cell | §2 (real pre-retune script) | `--tune pre_retune` now |
|---|---|---|
| `commodity` / price / 0 pt | 5.4 | 5.3 |
| `gold` / nothing / 0 pt | 5.8 | 5.8 |
| `gold` / price / 0 pt | 5.4 | 6.0 |
| `gold` / growth / 0 pt | 19.8 | 19.6 |
| `fiat` / price / 0 pt | 4.7 | 4.8 |
| `fiat` / nothing / 0 pt | 49.1 | 49.3 |
| `gold` / price / 2 pt | 1.1 | 1.2 |
| `gold` / price / 8 pt | 0.3 | 0.3 |

---

## 9. Reading the tool

```
--points 0,1,2,3,5,8    the intervention-point budgets to sweep; 0 = tools never used
--only fiat             restrict to one currency law
--fin-law <law>         which financial-regulation law (sets the crash-event option, not the budget)
--tune pre_retune       approximately the script before 2026-09-22; or individual keys, e.g. --tune sev_scale=0.4
--exclude-tool directed comma-separated dashboard tools the AI never clicks ('all' keeps only the crash-event options)
--simplified            score capital controls on the banking_system_simplified fallback branch
--event-channel         crude aggregate stand-in for banking_cycle_events.txt
--pulse-order           which of the two monthly pulses runs first
--no-click-weight       how often the AI clicks a dashboard button (largest single assumption)
--json out.json         the full metric set, including phase occupancy and per-tool usage
--rescue                instead of the matrix: fork every boom entry, measure how often maxed leaning tools pull it back (§10)
--rescue-tools a,b      the tools --rescue switches on (default buffer,margin,moral_suasion — 5 points)
--rescue-delay 3        months into the boom before --rescue acts
--rescue-entry 88       fork at frenzy entries instead of boom entries (default 75)
--tune pre_boom_rescue  the mod as #371 left it, before §10
--self-test             check the monetary port against events/te_debug_monetary_events.txt
```

The exogenous game-state stubs — GDP, growth, deficit, debt, war, goods prices, tech era — are tabulated in
the script's module docstring. They are the first thing to argue with if a number here looks wrong.

---

## 10. Pulling a boom back (2026-09-22, after #371)

**The complaint (owner, after playing #371):** once the cycle moves into boom or frenzy, even a little bubble
pressure means maxed interventions have no chance of pulling it back. It should still usually end in a crash,
but a player who maxes the tools should have a chance.

**Why the century matrix could not see it.** The matrix measures crash *frequency* with the AI's click model
deciding when tools go on. The question here is conditional: *given* a boom has started, what can a player do?
`--rescue` answers that. It forks every run at each month the cycle crosses 75 from below and replays the next
48 months twice, on the same random stream:

- **passive** — no tools; the price-stability mandate keeps steering the dial.
- **maxed** — after a 3-month reaction delay, buffer + margin + moral suasion (5 points) switched on and held,
  and on a dial regime *Take Control* with the rate target at its ceiling. The rate still drifts there at the
  law's speed, so the stance tightens over months, not at once.

An arm is "pulled back" if the cycle falls below 60 before any crash.

**What it found.** An untended boom crashes essentially every time (0.0–1.2 % pulled back, every currency).
That part is right. But the maxed arm on metallic money pulled back only **8 % (gold) and 11 % (commodity)**
of booms, and under 2 % once bubble was past 60. The mechanism: the boom phase adds +4 bubble a month (frenzy
+20). All three leaning tools together drained −0.95 after #371's ×0.2, so bubble kept climbing under maxed
tools. Speculative inertia is a function of bubble (+0.25 momentum at 50, +1.25 at 100, so +2.5 to +12.5 cycle
points a month once it converges). It soon outweighed the tools' combined −0.12 momentum several times over.
Fiat and digital did better (21 % / 34 %) only because a free dial can tighten much harder.

**Levers measured for boom rescue** (price cells, the 5-point toolset, 3-month delay, gold / commodity / fiat /
digital; later rows stack on the one above):

| lever | gold | commodity | fiat | digital |
|---|---|---|---|---|
| as #371 left it | 8.0 | 10.9 | 20.9 | 33.8 |
| leaning tools' bubble ×2 | 13.4 | 18.6 | 26.7 | 38.9 |
| leaning tools' bubble ×3 | 17.7 | 24.4 | 31.9 | 42.9 |
| … + fiat / digital +0.2 bubble a month | 17.7 | 24.4 | 28.6 | 37.7 |
| **… + frenzy +8 and inertia capped at 0.45 (shipped)** | **25.6** | **34.4** | **39.6** | **52.4** |

Also measured and not shipped: the tools' momentum ×2 (about as good as bubble ×2), inertia damped by each
active leaning tool (a new mechanic for a gain the value change mostly delivers), and a crash-chance mult on
the buffer and margin (softens the roll without pulling the cycle down, which is not what was asked). Boom
entries are sampled from untended centuries, so no tool drained bubble during the expansion before them. That
makes these the hard cases, and the table conservative.

### Step 1 — ×3 on the leaning tools, and a bubble add for elastic money

×2 moved well-managed fiat and digital by about a fifth; ×3 roughly halved them at 5–8 points (9.4 → 5.1,
8.1 → 4.5), a different game. Three law-level knobs were measured to take that back on fiat and digital only:

- **`country_banking_crash_chance_mult` +25 / +50 %** — almost no effect on frequency (crash counts are
  bubble-rebuild-limited, as §3 found), but it makes crashes fire earlier and milder, raises the untouched dial
  arm and *lowers* rescue. Wrong knob.
- **`country_banking_random_momentum_mult` +0.5 / +1.0** — *fewer* crashes (a symmetric swing knocks booms
  down as often as it lifts them, and the mean-reversion weight grows with distance from 50). This is part of
  why digital, which already carries +0.5, is the calmest regime. Wrong direction.
- **`country_bubble_pressure_monthly_add` +0.15 / +0.2 / +0.3 / +0.6** — works, and is the thematic fit:
  elastic money feeds speculation, and it acts only through the bubble the tools fight. **+0.2 shipped**: fiat
  with little regulation budget or a passive bank now crashes slightly more than gold, while a managed fiat
  country still crashes least. +0.3 and up overshoot at low budgets.

### Step 2 — frenzy was a wall; a flatter inertia curve opens a door

With ×3 + 0.2, **no maxed player ever escaped a frenzy** (0.0 % in every cell, still under 1 % acting the
month it began). About 90 % of frenzies start with bubble already past 60, median 79 (boom fills it), so frenzy's
own +20 is not what locks it. Speculative inertia is: at bubble 80 the old quadratic added +0.67 momentum a
month, a standing +7 cycle points, and bubble keeps climbing while the rate drifts up. Measured, frenzy
rescue at 3 months / at once:

| variant | gold | commodity | fiat | digital |
|---|---|---|---|---|
| frenzy +20 (as it was) | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.2 / 0.5 |
| frenzy +6 alone | 0.2 / 0.8 | 0.3 / 1.5 | 1.0 / 2.9 | 3.1 / 6.8 |
| frenzy +8, frenzy crash weight 0.35 → 0.18 | 0.2 / 0.4 | 0.2 / 0.5 | 0.4 / 1.4 | 1.6 / 4.2 |
| frenzy +8, inertia top 0.6 | 1.3 / 2.6 | 1.6 / 3.6 | 4.7 / 7.3 | 8.8 / 14.9 |
| **frenzy +8, inertia top 0.45 (shipped)** | **3.0 / 4.3** | **4.1 / 6.7** | **7.4 / 11.3** | **14.8 / 22.5** |

"Inertia top" is the curve's value at bubble 100. Below 50 it is unchanged; above, it is now
`0.25 + 0.005·(x−50) − 0.00002·(x−50)²`, continuous in value and slope at 50: 0.32 at 65, 0.38 at 80, 0.45 at
100 (was 0.39 / 0.67 / 1.25). Frenzy's bubble add 20 → 8 (the `_cmd` / `_coop` variants ×0.4 alike, 7.6 /
6.4). An untended frenzy still crashes essentially always (0–0.9 %). Frenzy is entered less often now (entries
fell by a quarter on gold to a half on digital), so these percentages are over ~740–1,700 entries a cell.

### The rescue study, as shipped — `--rescue --runs 400`, % of entries pulled below 60 before any crash

`--tune pre_boom_rescue` → now. Columns after "maxed" split it by bubble at entry.

**Boom entry, 3-month delay** (`--rescue`):

| cell | passive | maxed | b 20–40 | b 40–60 | b 60+ |
|---|---|---|---|---|---|
| commodity / price | 0.0 → 0.2 | 10.9 → **34.4** | 27 → 50 | 9 → 33 | 0.6 → 24 |
| gold / price | 0.4 → 2.9 | 8.0 → **25.6** | 18 → 36 | 6 → 24 | 1.9 → 20 |
| fiat / price | 0.5 → 1.4 | 20.9 → **39.6** | 42 → 54 | 21 → 40 | 3.0 → 31 |
| digital / price | 1.2 → 4.2 | 33.8 → **52.4** | 72 → 78 | 45 → 59 | 9.9 → 40 |

Acting the month the boom starts (`--rescue-delay 0`): commodity 20 → 52, gold 15 → 41, fiat 30 → 53,
digital 48 → 67.

**Frenzy entry** (`--rescue-entry 88`), 3-month delay / acting at once: commodity 0.0 → 4.1 / 0.0 → 6.7, gold
0.0 → 3.0 / 0.0 → 4.3, fiat 0.0 → 7.4 / 0.0 → 11.3, digital 0.1 → 14.8 / 0.2 → 22.5.

**Target, stated so it can be argued with.** A maxed player on metallic money pulls back about a quarter to a
third of booms, a fifth even from bubble past 60, and a few percent of frenzies; fiat and digital better, as a
regime with a free dial should be. An untended boom still crashes 96–100 % of the time, an untended frenzy
99+ %. Digital is the strongest in a frenzy (15–22 %); its +0.5 random momentum is the knob if that reads as
too strong. The knobs are the three tool lines, frenzy's bubble add and `bubble_inertia_multiplier_script_value`;
`--rescue` (with `--rescue-entry 88`) is the measurement.

### The century matrix after §10 — crashes per century, 400 runs × 100 years, #371 → now

At 0 / 1 / 2 / 3 / 5 / 8 points. `--tune pre_boom_rescue` reproduces the #371 column exactly.

| cell | crashes / century | depression % (0 pt) | worst slump, months (0 pt) | throughput pp, 0 → 8 pt |
|---|---|---|---|---|
| `commodity` / nothing | 10.8 / 10.4 / 9.8 / 8.8 / 9.0 / 8.9 | 26 | 65 | −1.11 → +0.41 |
| `commodity` / price | 11.7 / 11.1 / 9.7 / 8.9 / 7.9 / 7.5 | 24 | 34 | −0.18 → +1.17 |
| `commodity` / growth | 16.8 / 15.9 / 14.1 / 14.6 / 13.7 / 14.3 | 25 | 29 | +0.10 → +1.65 |
| `gold` / nothing | 12.0 / 11.6 / 10.9 / 10.5 / 10.4 / 10.8 | 26 | 58 | −0.87 → +0.79 |
| `gold` / price | 10.6 / 10.0 / 8.5 / 8.0 / 7.2 / 6.9 | 25 | 46 | −0.80 → +0.46 |
| `gold` / growth | 17.9 / 17.8 / 16.9 / 16.4 / 14.7 / 14.1 | 23 | 30 | +0.05 → +1.45 |
| `gold` / peg | 16.0 / 15.5 / 14.9 / 14.0 / 14.4 / 13.8 | 25 | 36 | −0.11 → +1.47 |
| `fiat` / nothing | 39.9 / 39.3 / 39.8 / 39.7 / 39.6 / 40.3 | 24 | 18 | +0.27 → +2.38 |
| `fiat` / price | 11.9 / 11.5 / 8.9 / 8.0 / 6.3 / 6.1 | 25 | 28 | −0.12 → +1.02 |
| `fiat` / growth | 18.9 / 18.7 / 16.8 / 15.5 / 14.7 / 15.0 | 24 | 22 | +0.27 → +1.71 |
| `digital` / nothing | 40.2 / 39.8 / 40.0 / 39.7 / 39.2 / 39.6 | 25 | 18 | +0.50 → +2.54 |
| `digital` / price | 10.8 / 10.2 / 7.9 / 6.3 / 5.3 / 5.0 | 25 | 22 | +0.42 → +1.01 |
| `digital` / growth | 18.6 / 17.0 / 15.9 / 15.1 / 14.0 / 12.6 | 24 | 20 | +0.59 → +1.69 |

Averaged over every cell except the two never-touched fiat / digital dials, #371 → now: crashes a century
13.5 → 12.1 (−10 %), severity 51 → 48, share landing in panic 25 → 22 %, months in recession 9.0 → 7.2 %,
months in frenzy 2.6 → 2.1 %, manufacturing throughput **+0.08 → +0.45 pp**, services +3.9 → +5.0 %.

§8's targets still hold. Metallic at 0–3 points under price stability, an untouched dial or peg defence is
8.0–16.0 (peg at the top, as before). Managed fiat ties gold at 2–3 points (8.9 / 8.0 vs 8.5 / 8.0) and beats it from 5
(6.3 / 6.1 vs 7.2 / 6.9); digital beats both from 2 points. At 0–1 points fiat now crashes a little more than
gold (11.9 / 11.5 vs 10.6 / 10.0): cheap money with no supervisory
budget is the most crash-prone metallic-or-better setup, which is the intended reading. Growth runs 1.4–2.6×
price stability; the top of the range is digital at 3–8 points, where price stability gained most. The budget
curve slopes downward — intervention points now buy something at every step. Throughput is positive on
average but still negative at 0 points for every metallic cell: an unmanaged cycle is still a net drag.

**Fidelity note.** The sim now reads the *currency* law's bubble, momentum, value and crash-chance lines (the
script reads them as country-scope `modifier:` values). The *financial-regulation* law's lines are still not
ported — some are large (`country_banking_crash_chance_mult` up to −0.5, random momentum +0.1 on universal
banking) — so absolute rates in game will differ by law, though no direction above depends on it.

---

## 11. Seven more tools (2026-09-23)

Four directed-credit sectors (heavy industry, agriculture, armaments, electrification & high tech) under a
one-sector cap that the Directed Credit law raises to two, reserve requirements, a bank holiday and a bail-in
regime — design and owner decisions in `docs/superpowers/specs/2026-09-23-banking-tools-expansion-design.md`.
The sim ports all seven: their modifiers through `TOOL_MODIFIER_NAMES`, their `ai_chance` blocks by hand, the
cap (`dc_slots_free`), the holiday's 3-month timer, 60-month cooldown and one-shot momentum halving
(`on_tool_enabled`), the bail-in / asset-relief exclusion, and reserve requirements' −0.5 pp inflation line in
`pressure_total`. The sim has no interest groups, so `--dc-affinity dc_heavy,…` names the sectors whose group
governs; armaments also has one at war. **Like every tool here, all seven are available from 1836** — bail-in's
real gate is era 9, so its share of a century below is much larger than in game.

400 runs × 100 years, every cell, 0 / 2 / 3 / 5 / 8 points; *before* is the sim and script as of #378.

### Directed credit: the split is exact

All five sectors score one weight, `banking_dc_ai_weight` (Infrastructure's pre-expansion `ai_chance`),
divided among the new sectors that have an affinity and could be started; with none, Infrastructure takes it
all. Summed over the grid, directed-credit clicks per century:

| affinity | total | Infrastructure | heavy | agriculture | armaments | electrification |
|---|---|---|---|---|---|---|
| none | 356.7 | 329.9 | 0 | 0 | 26.8 (at war) | 0 |
| heavy industry | 357.2 | 0 | 343.9 | 0 | 13.3 | 0 |
| all four | 356.9 | 0 | 89.2 | 89.1 | 89.6 | 89.0 |

Crash rates with one sector favoured match the no-affinity run to within ±0.5 (noise) in every cell, so F11's finding — directed
credit is the AI's riskiest tool — is not multiplied by four more of it. Leaving the favoured sector out
(`--exclude-tool dc_heavy`) moves the mean by −0.2, Infrastructure's own small harm. Under the Directed Credit law
the second slot is used: at 8 points a heavy-industry government adds Infrastructure about 4 times a century,
and the mean over cells goes 10.7 → 10.2 against the same law before the expansion.

### Reserve requirements: defer to the buffer

First shipped with the buffer's weights and nothing else. The AI then split its leaning clicks between the two —
at fiat / price / 3 points the buffer fell from 9.3 to 5.1 clicks a century and reserve requirements took 5.3 —
and reserve requirements are the weaker lean (−0.9 bubble a month against −1.5). Fiat and digital at 2–3 points
crashed 0.7–1.3 times a century more, and leaving the tool out *lowered* those cells by up to 1.5. Shipped: its
`ai_chance` is ×0 while the buffer could be bought instead, so it is the lean before the buffer's tech and a
second lean beside a running buffer, never a stand-in. After that, it gets 0 clicks at 3 points (the buffer is back
at 8.7–8.8), no cell is better off without it, and leaving it out raises crashes by 0.7 a century on average.

### Bank holiday and bail-in

(These two leave-one-outs, and the sector one above, ran before the reserve-requirements fix; it touches
neither tool's weights.)

- **Bank holiday:** 0.1–0.7 declarations a century (panics are rare), and leaving it out moves no cell by more
  than ±0.4. It is a player's emergency lever more than an AI habit.
- **Bail-in:** at 3 points it is the AI's most-clicked downturn tool, ~10 a century, because asset relief costs
  5 and does not fit. Leaving it out raises crashes by 0.2 a century on average: it crowds out some directed
  credit, which is a net gain. In game the era-9 gate confines this to the last part of a campaign.

### The century matrix — crashes per century, 0 / 2 / 3 / 5 / 8 points, before → shipped

| cell | before | shipped |
|---|---|---|
| `commodity` / nothing | 8.4 / 7.9 / 7.4 / 7.6 / 7.4 | 8.4 / 7.7 / 7.2 / 5.3 / 5.2 |
| `commodity` / price | 9.7 / 8.4 / 7.5 / 6.3 / 6.3 | 9.7 / 8.4 / 6.9 / 5.4 / 4.3 |
| `commodity` / growth | 15.0 / 12.0 / 12.2 / 11.2 / 11.6 | 15.0 / 12.8 / 12.2 / 10.0 / 9.0 |
| `gold` / nothing | 9.5 / 8.9 / 8.8 / 8.8 / 8.7 | 9.5 / 8.9 / 8.3 / 6.4 / 6.1 |
| `gold` / price | 9.0 / 6.9 / 6.5 / 5.8 / 5.8 | 9.0 / 7.1 / 6.4 / 5.6 / 4.6 |
| `gold` / growth | 15.8 / 15.1 / 13.5 / 13.8 / 13.3 | 15.8 / 14.9 / 13.6 / 12.2 / 10.2 |
| `gold` / peg | 13.1 / 12.4 / 11.7 / 11.9 / 12.0 | 13.1 / 12.4 / 11.4 / 8.8 / 8.5 |
| `fiat` / nothing | 38.2 / 38.2 / 38.0 / 37.8 / 38.3 | 38.2 / 38.2 / 37.7 / 37.0 / 36.5 |
| `fiat` / price | 9.9 / 7.9 / 6.8 / 5.2 / 5.0 | 9.9 / 7.6 / 6.2 / 5.1 / 4.2 |
| `fiat` / growth | 17.0 / 14.5 / 14.5 / 13.3 / 12.6 | 17.0 / 14.5 / 13.7 / 12.4 / 11.6 |
| `digital` / nothing | 38.6 / 38.5 / 38.1 / 37.5 / 37.8 | 38.6 / 38.7 / 37.8 / 36.7 / 35.3 |
| `digital` / price | 9.0 / 6.7 / 5.4 / 4.5 / 4.5 | 9.0 / 6.8 / 5.2 / 4.7 / 3.6 |
| `digital` / growth | 16.3 / 14.6 / 13.5 / 12.5 / 11.7 | 16.3 / 14.4 / 13.0 / 11.7 / 9.7 |

0–3 points are unchanged within noise. The change is at 5–8 points, 1–3.5 fewer crashes a century: a big
budget now has a second lean to stack (reserve requirements beside the buffer) and a cheap crisis tool. Averaged
over every cell except the two never-touched fiat / digital dials, 10.1 → 9.4. At 8 points severity 46 → 42, the
share landing in panic 20 → 16 %, months in recession 3.2 → 2.3 %, manufacturing throughput +0.70 → +0.86 pp,
services +5.2 → +5.7 %. At 3 points throughput and services dip slightly (+0.18 → +0.13 pp, +4.0 → +3.7 %): bail-in
takes clicks that directed and export credit used to get.

**§8's targets still hold.** Metallic at 0–3 points under price stability, an untouched dial or peg defence is
6.4–13.1. Managed digital is at or below gold from 2 points and fiat from 3. Growth runs 1.5–2.8× price
stability, the top of that range at 8 points, where price stability gained most. The 2-point cell is 0.92–1.01× the mean of its 0- and 3-point
neighbours on every price cell, inside the 0.92–1.03 band. The budget curve slopes down more steeply at the top,
which §10 already accepted as the intended direction.

### Boom rescue

`--rescue`, maxed arm, % of boom entries pulled below 60 before any crash (gold / commodity / fiat / digital):

| leaning tools held | gold | commodity | fiat | digital |
|---|---|---|---|---|
| buffer + margin + moral suasion (5 pt), before and after | 24.5 | 32.4 | 40.2 | 52.7 |
| + reserve requirements (7 pt) | 33.4 | 41.1 | 46.8 | 56.9 |

A seven-point leaning stack pulls back about a third of metallic booms, the top of §10's "a quarter to a
third", and a little over half of digital ones. That is a real improvement, not booms tamed for free, so the
tool's −0.9 bubble line was left as designed.
